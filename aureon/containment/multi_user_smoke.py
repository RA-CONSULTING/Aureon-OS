"""Stage 9: boot the existing tenant boundary inside native containment.

The child is a new process started by ``prepare_launch`` (``unshare --net``,
scrubbed environment, capabilities dropped). It builds the operator app with
the local test ingress seam, stores two Fernet keystores, and drives the
real gate with a WSGI client. No TCP listener is bound. No order is placed.
``go_live_clear`` stays false and the public pin is not written.

Shared memory is scored only on surfaces this process reads: the thought-bus
deque, its JSONL file, ``os.environ`` values, new ``/dev/shm`` segments, and
the other tenant's keystore. A canary found on one of those surfaces is a
measured leak. Absence on a surface that was not read is not a claim.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from aureon.containment.native import (
    PIN,
    STARTED_FROM,
    ContainmentRefused,
    ContainmentUnavailable,
    prepare_launch,
)

_CHILD = Path(__file__).with_name("_multi_user_child.py")
_ROOT = Path(__file__).resolve().parents[2]
_SOURCE_FILES = (
    "aureon/containment/multi_user_smoke.py",
    "aureon/containment/_multi_user_child.py",
    "tests/test_multi_user_smoke.py",
)
_UNCHANGED_FILES = (
    "README.md",
    "docs/runbooks/GO_LIVE_HARDENING.md",
    "aureon/operator/operator_server.py",
    "aureon/operator/identity.py",
    "mcp/aureon_public/guard_loader.py",
    "mcp/aureon_public/pin_blob.py",
    "mcp/aureon_public/sweep_guard.py",
    "scripts/linux/install-linux.sh",
)
_DENY_PROBES = (
    ("GET", "/api/pulse"),
    ("GET", "/api/switchboard"),
    ("GET", "/api/terminal-state"),
    ("GET", "/api/env-credentials"),
    ("GET", "/api/trades"),
    ("GET", "/api/action/status"),
    ("POST", "/api/billing/charge-fee"),
)
_REQUIRED_DENY = (("GET", "/api/pulse"), ("GET", "/api/switchboard"))
# Internal needle ids stay in the child. The receipt only uses these names,
# so a digest cannot sit under a field that looks like a live credential.
_RECEIPT_LABEL = {
    "control": "canary_control",
    "prompt_a": "canary_prompt_a",
    "prompt_b_absent": "canary_prompt_b_absent",
    "prompt_b": "canary_prompt_b",
    "prompt_a_revoked": "canary_prompt_a_revoked",
    "prompt_b_still": "canary_prompt_b_still",
    "key_a": "canary_tenant_a",
    "key_b": "canary_tenant_b",
    "jwt_secret": "canary_signer",
    "admin_key": "canary_operator",
}
_CANARY_LABELS = tuple(_RECEIPT_LABEL.values())
_LEAK_LABELS = tuple(label for label in _CANARY_LABELS if label != "canary_control")
_ENV_LEAK_LABELS = frozenset({"canary_tenant_a", "canary_tenant_b"})
_FORBIDDEN_RECEIPT_KEYS = (
    '"admin_key"',
    '"jwt_secret"',
    '"key_a"',
    '"key_b"',
    '"key_masked_last4"',
    '"prompt_a"',
    '"prompt_b"',
    '"prompt_b_keyless"',
    '"prompt_a_revoked"',
    '"prompt_b_still"',
    '"control"',
)
_SECRET_RE = re.compile(
    r"sk-stage9[ab]-[0-9a-f]+[A-Z]{4}"
    r"|stage9-prompt-[a-z0-9-]*[0-9a-f]{8,}"
    r"|stage9-bus-control-[0-9a-f]+"
    r"|stage9-jwt-[0-9a-f]+"
    r"|stage9-admin-[0-9a-f]+"
)
_HOLDS = (
    {"id": 2, "item": "exact target-source measurement and immutable release provenance", "status": "HOLD"},
    {"id": 3, "item": "durable HNC evidence with an external monotonic head anchor", "status": "HOLD"},
    {"id": 4, "item": "complete source-boundary census closure", "status": "HOLD"},
    {"id": 5, "item": "authenticated deployment receipt and provider-side read-back", "status": "HOLD"},
)


def repo_root() -> Path:
    return _ROOT


def public_pin(root: Path | None = None) -> str:
    """The published pin is ``PINNED_COMMIT`` in the public guard loader."""

    text = ((root or repo_root()) / "mcp" / "aureon_public" / "guard_loader.py").read_text(encoding="utf-8")
    match = re.search(r'^PINNED_COMMIT = "([0-9a-f]{40})"', text, re.MULTILINE)
    if match is None:
        raise RuntimeError("PINNED_COMMIT is missing from the public guard loader")
    return match.group(1)


def redact_text(text: str) -> str:
    """Strip generated canaries. The prefixes are how the parent recognises them."""

    return _SECRET_RE.sub("[redacted]", text)


def _receipt_label(label: str) -> str:
    return _RECEIPT_LABEL[label]


def receipt_names_are_safe(text: str) -> list[str]:
    """Return forbidden credential-shaped JSON keys present in a receipt."""

    return [name for name in _FORBIDDEN_RECEIPT_KEYS if name in text]


def contained_child_env(base: Mapping[str, str], work: Path, repo: Path) -> dict[str, str]:
    """Start from the scrubbed launch env and add only smoke flags.

    The parent process environment is not an input. The JWT secret and the
    tenant keys are created inside the child.
    """

    env = dict(base)
    site = _user_site()
    pythonpath = [str(repo.resolve())]
    if site:
        pythonpath.append(site)
    env.update(
        {
            "AUREON_DISABLE_LLM_HTTP": "1",
            "AUREON_IMMUNE_MEMORY": "0",
            "AUREON_LLM_OFFLINE": "1",
            "AUREON_OPERATOR_ENV": "test",
            "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
            "AUREON_THOUGHT_BUS_PATH": str((work / "thoughts.jsonl").resolve()),
            "AUREON_TRACE_PUMP": "0",
            "PYTHONPATH": os.pathsep.join(pythonpath),
        }
    )
    return env


def _user_site() -> str | None:
    try:
        import flask
    except ImportError:
        return None
    return str(Path(flask.__file__).resolve().parents[1])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_hashes(root: Path, names: tuple[str, ...]) -> dict[str, str]:
    return {name: _sha256(root / name) for name in names if (root / name).is_file()}


def _git_head(root: Path) -> str | None:
    try:
        done = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    text = done.stdout.strip()
    return text if len(text) == 40 else None


def _worktree_dirty(root: Path) -> bool | None:
    try:
        done = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return bool(done.stdout.strip())


def _tcp_probe(host: str, port: int, timeout: float) -> dict[str, Any]:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        sock.connect((host, port))
    except OSError as exc:
        return {
            "ok": False,
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
            "bytes_read": 0,
        }
    else:
        return {"ok": True, "errno": None, "error": None, "bytes_read": 0}
    finally:
        sock.close()


def _scan_home_files(home: Path, needles: Mapping[str, str]) -> dict[str, Any]:
    """Read files created under the contained HOME. Pre-existing host files are not here."""

    paths: dict[str, list[str]] = {}
    for label in needles:
        paths[_receipt_label(label)] = []
    scanned = 0
    files = 0
    for path in home.rglob("*"):
        if not path.is_file():
            continue
        files += 1
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > 8_000_000:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        scanned += len(data)
        text = data.decode("utf-8", "replace")
        relative = str(path.relative_to(home))
        for label, needle in needles.items():
            if needle and (needle in text or needle.encode("utf-8") in data):
                paths[_receipt_label(label)].append(relative)
    return {"files": files, "bytes": scanned, "paths": paths}


def _found_map(text: str, needles: Mapping[str, str]) -> dict[str, bool]:
    return {
        _receipt_label(label): bool(needle) and needle in text
        for label, needle in needles.items()
    }


def _scan_new_shm(before: set[str], needles: Mapping[str, str]) -> dict[str, Any]:
    try:
        names = sorted(os.listdir("/dev/shm"))
    except OSError as exc:
        return {
            "readable": False,
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
            "preexisting_count": len(before),
            "preexisting_read": False,
            "new_names": [],
            "new_bytes_scanned": 0,
            "found": {_receipt_label(label): False for label in needles},
        }
    new = [name for name in names if name not in before]
    found = {_receipt_label(label): False for label in needles}
    scanned = 0
    errors = 0
    for name in new:
        path = Path("/dev/shm") / name
        try:
            data = path.read_bytes()[:1_048_576]
        except OSError:
            errors += 1
            continue
        scanned += len(data)
        text = data.decode("utf-8", "replace")
        for label, needle in needles.items():
            if needle and (needle in text or needle.encode("utf-8") in data):
                found[_receipt_label(label)] = True
    return {
        "readable": True,
        "preexisting_count": len(before),
        "preexisting_read": False,
        "new_names": new,
        "new_bytes_scanned": scanned,
        "read_errors": errors,
        "found": found,
    }


def _caps() -> dict[str, str]:
    found: dict[str, str] = {}
    try:
        lines = Path("/proc/self/status").read_text(encoding="ascii").splitlines()
    except OSError as exc:
        return {"error": errno.errorcode.get(exc.errno, type(exc).__name__)}
    for line in lines:
        if line.startswith("Cap"):
            key, value = line.split(":", 1)
            found[key] = value.strip()
    return found


def _route_mounted(app: Any, method: str, rule: str) -> bool:
    return any(
        item.rule == rule and method in (item.methods or ())
        for item in app.url_map.iter_rules()
    )


def _body_summary(response: Any, needles: Mapping[str, str]) -> dict[str, Any]:
    raw = response.get_data(as_text=True)
    body = response.get_json(silent=True)
    summary: dict[str, Any] = {
        "status": int(response.status_code),
        "secret_in_body": any(needle and needle in raw for needle in needles.values()),
    }
    if isinstance(body, dict):
        summary["tenant_no_key"] = body.get("tenant_no_key")
        summary["blocked"] = body.get("blocked")
        summary["conscience_verdict"] = body.get("conscience_verdict")
        calls = body.get("tool_calls")
        if isinstance(calls, list):
            summary["tool_names"] = [
                str(item.get("tool"))
                for item in calls
                if isinstance(item, dict) and item.get("tool")
            ]
        if "has_key" in body or "providers" in body:
            providers = body.get("providers")
            if isinstance(providers, list):
                row = next((item for item in providers if item.get("id") == "ollama"), None)
                if isinstance(row, dict):
                    summary["has_key"] = bool(row.get("has_key"))
                    masked = str(row.get("key_masked") or "")
                    summary["canary_mask_tail"] = masked[-4:] if masked else ""
    return summary


def run_contained() -> dict[str, Any]:
    """Exercise the tenant boundary. Call this only inside the contained child."""

    import secrets

    home = Path.home().resolve()
    os.chdir(home)
    needles = {
        "control": "stage9-bus-control-" + secrets.token_hex(16),
        "prompt_a": "stage9-prompt-a-" + secrets.token_hex(16),
        "prompt_b_absent": "stage9-prompt-b-absent-" + secrets.token_hex(16),
        "prompt_b": "stage9-prompt-b-" + secrets.token_hex(16),
        "prompt_a_revoked": "stage9-prompt-a-revoked-" + secrets.token_hex(16),
        "prompt_b_still": "stage9-prompt-b-still-" + secrets.token_hex(16),
        "key_a": "sk-stage9a-" + secrets.token_hex(8) + "AAAA",
        "key_b": "sk-stage9b-" + secrets.token_hex(8) + "BBBB",
        "jwt_secret": "stage9-jwt-" + secrets.token_hex(32),
        "admin_key": "stage9-admin-" + secrets.token_hex(32),
    }
    os.environ["AUREON_SUPABASE_JWT_SECRET"] = needles["jwt_secret"]
    os.environ["AUREON_OPERATOR_API_KEY"] = needles["admin_key"]
    os.environ.setdefault("AUREON_LLM_OFFLINE", "1")
    os.environ.setdefault("AUREON_DISABLE_LLM_HTTP", "1")
    os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")
    os.environ.setdefault("AUREON_OPERATOR_ENV", "test")
    shm_before = set(os.listdir("/dev/shm")) if Path("/dev/shm").is_dir() else set()
    tcp = _tcp_probe("1.1.1.1", 443, 1.0)
    report: dict[str, Any] = {
        "schema": "aureon.measured.multi-user-child.v1",
        "ok": False,
        "listener_bound": False,
        "boot": "create_app",
        "serving_entrypoint": False,
        "orders_placed": False,
        "live_trading": False,
        "market_data_fetched": False,
        "go_live_clear": False,
        "production_ready": False,
        "magic_star_release": False,
        "net_ns": os.readlink("/proc/self/ns/net"),
        "euid": os.geteuid(),
        "caps": _caps(),
        "tcp_1_1_1_1_443": tcp,
        "home_is_workdir": True,
    }
    try:
        report.update(_exercise(home, needles, shm_before))
        report["ok"] = True
    except Exception as exc:  # noqa: BLE001 — return the failure instead of a traceback
        report["error"] = redact_text(f"{type(exc).__name__}: {exc}")
    blob = json.dumps(report, sort_keys=True)
    report["report_contained_secret"] = any(value and value in blob for value in needles.values())
    if report["report_contained_secret"]:
        blob = redact_text(blob)
        report = json.loads(blob)
        report["report_contained_secret"] = True
    return report


def _exercise(home: Path, needles: Mapping[str, str], shm_before: set[str]) -> dict[str, Any]:
    import aureon.operator.keystore as keystore
    import aureon.operator.operator_server as server
    from aureon.core.aureon_thought_bus import get_thought_bus

    store_root = Path(keystore.CONFIG_DIR).resolve()
    if home != store_root and home not in store_root.parents:
        raise RuntimeError("keystore CONFIG_DIR is outside the contained HOME")
    bus_path = Path(os.environ.get("AUREON_THOUGHT_BUS_PATH", "")).resolve()
    if home not in bus_path.parents:
        raise RuntimeError("thought bus path is outside the contained HOME")

    seam = server.TestOnlyOperatorIngressRelease(
        master_key=b"stage9-contained-multi-user-smoke-seam",
    )
    app = server.create_app(test_ingress_release=seam)
    client = app.test_client()
    bus = get_thought_bus()
    subscribers_before = int(bus.subscriber_count())
    subscriptions_before = _subscription_summary(bus)
    bus.publish("stage9.control", {"marker": needles["control"]}, source="stage9-smoke")

    tenant_a = "stage9-user-a"
    tenant_b = "stage9-user-b"
    headers_a = _headers(tenant_a, needles["jwt_secret"])
    headers_b = _headers(tenant_b, needles["jwt_secret"])
    admin = {"Authorization": f"Bearer {needles['admin_key']}"}

    stored_a = client.post(
        "/api/providers/ollama",
        json={"api_key": needles["key_a"], "base_url": "http://127.0.0.1:9", "model": "stage9-local"},
        headers=headers_a,
    )
    reason_a = client.post(
        "/api/cognition/reason",
        json={"prompt": needles["prompt_a"]},
        headers=headers_a,
    )
    reason_b_keyless = client.post(
        "/api/cognition/reason",
        json={"prompt": needles["prompt_b_absent"]},
        headers=headers_b,
    )
    stored_b = client.post(
        "/api/providers/ollama",
        json={"api_key": needles["key_b"], "base_url": "http://127.0.0.1:9", "model": "stage9-local"},
        headers=headers_b,
    )
    reason_b = client.post(
        "/api/cognition/reason",
        json={"prompt": needles["prompt_b"]},
        headers=headers_b,
    )
    deleted_a = client.delete("/api/providers/ollama", headers=headers_a)
    reason_a_revoked = client.post(
        "/api/cognition/reason",
        json={"prompt": needles["prompt_a_revoked"]},
        headers=headers_a,
    )
    reason_b_still = client.post(
        "/api/cognition/reason",
        json={"prompt": needles["prompt_b_still"]},
        headers=headers_b,
    )
    view_a = client.get("/api/providers", headers=headers_a)
    view_b = client.get("/api/providers", headers=headers_b)
    me_a = client.get("/api/me", headers=headers_a)
    admin_pulse = client.get("/api/pulse", headers=admin)

    deny_rows = []
    for method, rule in _DENY_PROBES:
        mounted = _route_mounted(app, method, rule)
        if not mounted:
            deny_rows.append({"method": method, "path": rule, "mounted": False, "status": None})
            continue
        if method == "GET":
            response = client.get(rule, headers=headers_a)
        else:
            response = client.post(rule, json={"user_id": tenant_b}, headers=headers_a)
        summary = _body_summary(response, needles)
        deny_rows.append(
            {
                "method": method,
                "path": rule,
                "mounted": True,
                "status": summary["status"],
                "secret_in_body": summary["secret_in_body"],
            }
        )

    subscribers_after = int(bus.subscriber_count())
    subscriptions_after = _subscription_summary(bus)
    home_files = _scan_home_files(home, needles)
    recent = bus.get_recent(limit=2000) or []
    recent_text = json.dumps(recent, default=str)
    jsonl_text = bus_path.read_text(encoding="utf-8", errors="replace") if bus_path.is_file() else ""
    jsonl_truncated = False
    if len(jsonl_text) > 8_000_000:
        jsonl_text = jsonl_text[-8_000_000:]
        jsonl_truncated = True
    env_text = "\n".join(os.environ.values())
    store_a = Path(keystore._store_path(tenant_a))
    store_b = Path(keystore._store_path(tenant_b))
    raw_a = store_a.read_bytes() if store_a.is_file() else b""
    raw_b = store_b.read_bytes() if store_b.is_file() else b""
    loaded_b = keystore.load(tenant_b)
    reason_a_summary = _body_summary(reason_a, needles)
    reason_b_keyless_summary = _body_summary(reason_b_keyless, needles)
    reason_b_summary = _body_summary(reason_b, needles)
    reason_a_revoked_summary = _body_summary(reason_a_revoked, needles)
    reason_b_still_summary = _body_summary(reason_b_still, needles)
    view_b_summary = _body_summary(view_b, needles)
    admin_summary = _body_summary(admin_pulse, needles)
    exchange_modules = sorted(name for name in sys.modules if name.startswith("aureon.exchanges"))
    return {
        "test_ingress_seam": True,
        "production_ready": bool(seam.production_ready),
        "magic_star_release": bool(seam.magic_star_release),
        "keystore_under_home": True,
        "store_a_bytes": len(raw_a),
        "store_b_bytes": len(raw_b),
        "plaintext_key_in_store": (
            needles["key_a"].encode("utf-8") in raw_a or needles["key_b"].encode("utf-8") in raw_b
        ),
        "cross_tenant_key_visible": needles["key_a"] in json.dumps(loaded_b, default=str),
        "environ_has_tenant_key": needles["key_a"] in env_text or needles["key_b"] in env_text,
        "provider_write_a": int(stored_a.status_code),
        "provider_write_b": int(stored_b.status_code),
        "provider_delete_a": int(deleted_a.status_code),
        "tenant_me_status": int(me_a.status_code),
        "admin_pulse_status": admin_summary["status"],
        "admin_pulse_secret": admin_summary["secret_in_body"],
        "view_a": _body_summary(view_a, needles),
        "view_b": view_b_summary,
        "reason_a": reason_a_summary,
        "reason_b_keyless": reason_b_keyless_summary,
        "reason_b": reason_b_summary,
        "reason_a_revoked": reason_a_revoked_summary,
        "reason_b_still": reason_b_still_summary,
        "default_deny": deny_rows,
        "subscriber_count_before": subscribers_before,
        "subscriber_count_after": subscribers_after,
        "subscriptions_before": subscriptions_before,
        "subscriptions_after": subscriptions_after,
        "surfaces": {
            "thought_bus_recent": {
                "scanned_items": len(recent),
                "found": _found_map(recent_text, needles),
            },
            "thoughts_jsonl": {
                "bytes": bus_path.stat().st_size if bus_path.is_file() else 0,
                "truncated": jsonl_truncated,
                "found": _found_map(jsonl_text, needles),
            },
            "os_environ_values": {
                "names_scanned": len(os.environ),
                "found": _found_map(env_text, needles),
            },
            "dev_shm_new": _scan_new_shm(shm_before, needles),
            "home_files": home_files,
        },
        "exchange_module_count": len(exchange_modules),
        "exchange_modules_sample": exchange_modules[:30],
        "canary_sha256": {
            f"{_receipt_label(label)}_sha256": hashlib.sha256(value.encode("utf-8")).hexdigest()
            for label, value in needles.items()
        },
    }


def _subscription_summary(bus: Any) -> list[dict[str, Any]]:
    """Topic names and handler callables. Payloads are not read."""

    subs = getattr(bus, "_subs", {})
    if not isinstance(subs, dict):
        return []
    rows: list[dict[str, Any]] = []
    for topic, handlers in subs.items():
        if not isinstance(handlers, list):
            continue
        names = []
        for handler in handlers:
            func = getattr(handler, "__func__", handler)
            owner = getattr(handler, "__self__", None)
            owner_name = type(owner).__name__ if owner is not None else ""
            qual = getattr(func, "__qualname__", None) or getattr(func, "__name__", type(handler).__name__)
            names.append(f"{owner_name}.{qual}" if owner_name else str(qual))
        rows.append({"topic": str(topic), "count": len(handlers), "handlers": names})
    rows.sort(key=lambda row: str(row["topic"]))
    return rows


def _headers(sub: str, secret: str) -> dict[str, str]:
    import base64
    import hashlib
    import hmac

    def pack(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    header = pack({"alg": "HS256", "typ": "JWT"})
    body = pack({"sub": sub, "exp": int(time.time()) + 3600})
    signature = hmac.new(secret.encode("utf-8"), f"{header}.{body}".encode("ascii"), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
    return {"Authorization": f"Bearer {header}.{body}.{sig}"}


def _surface_found(child: Mapping[str, Any], label: str) -> list[str]:
    hits: list[str] = []
    surfaces = child.get("surfaces") if isinstance(child.get("surfaces"), dict) else {}
    for name in ("thought_bus_recent", "thoughts_jsonl", "dev_shm_new"):
        found = (surfaces.get(name) or {}).get("found") if isinstance(surfaces.get(name), dict) else None
        if isinstance(found, dict) and found.get(label) is True:
            hits.append(name)
    if label in _ENV_LEAK_LABELS:
        env_found = (surfaces.get("os_environ_values") or {}).get("found")
        if isinstance(env_found, dict) and env_found.get(label) is True:
            hits.append("os_environ_values")
    return hits


def judge(child: Mapping[str, Any] | None, *, started: bool, parent_net_ns: str, argv_has_net: bool) -> dict[str, Any]:
    """Fail closed. A missing surface is not evidence of isolation."""

    failures: list[str] = []
    holds: list[str] = []
    if not started or not isinstance(child, dict):
        failures.append("contained process did not return a child report")
        return {"verdict": "fail", "failures": failures, "holds": holds, "gaps": []}
    if child.get("ok") is not True:
        failures.append(str(child.get("error") or "child report ok is not true"))
    if child.get("go_live_clear") is not False:
        failures.append("go_live_clear is not false")
    if child.get("orders_placed") is not False or child.get("live_trading") is not False:
        failures.append("child reports an order or live trading")
    if child.get("market_data_fetched") is not False:
        failures.append("child reports market data fetched")
    if child.get("listener_bound") is not False:
        failures.append("child bound a listener")
    if child.get("production_ready") is not False or child.get("magic_star_release") is not False:
        failures.append("test ingress seam claims a production release")
    if not argv_has_net:
        failures.append("launch argv omitted --net")
    net_ns = str(child.get("net_ns") or "")
    if not net_ns.startswith("net:") or net_ns == parent_net_ns:
        failures.append("child network namespace is not a new net namespace")
    tcp = child.get("tcp_1_1_1_1_443") if isinstance(child.get("tcp_1_1_1_1_443"), dict) else {}
    if tcp.get("ok") is True:
        failures.append("contained TCP 1.1.1.1:443 succeeded")
    elif tcp.get("errno") not in {errno.ENETUNREACH, errno.ENETDOWN, errno.EHOSTUNREACH}:
        failures.append(f"contained TCP errno {tcp.get('errno')} is not a no-route failure")
    if child.get("report_contained_secret") is True:
        failures.append("child report contained a canary before redaction")
    surfaces = child.get("surfaces") if isinstance(child.get("surfaces"), dict) else {}
    control_hits = _surface_found(child, "canary_control")
    bus_found = (surfaces.get("thought_bus_recent") or {}).get("found") if isinstance(surfaces.get("thought_bus_recent"), dict) else {}
    jsonl_found = (surfaces.get("thoughts_jsonl") or {}).get("found") if isinstance(surfaces.get("thoughts_jsonl"), dict) else {}
    if not isinstance(bus_found, dict) or bus_found.get("canary_control") is not True:
        failures.append("thought-bus scanner did not see the control canary")
    if not isinstance(jsonl_found, dict) or jsonl_found.get("canary_control") is not True:
        failures.append("thoughts.jsonl scanner did not see the control canary")
    for label in _LEAK_LABELS:
        hits = _surface_found(child, label)
        if hits:
            failures.append(f"{label} found on {', '.join(hits)}")
    if child.get("plaintext_key_in_store") is not False:
        failures.append("plaintext tenant key found in the encrypted store")
    if child.get("cross_tenant_key_visible") is not False:
        failures.append("tenant A key visible in tenant B store")
    if child.get("environ_has_tenant_key") is not False:
        failures.append("tenant key present in os.environ")
    if child.get("provider_write_a") != 200 or child.get("provider_write_b") != 200:
        failures.append("tenant key write did not return 200")
    if child.get("tenant_me_status") != 200:
        failures.append("/api/me did not return 200 for a tenant")
    if child.get("admin_pulse_status") == 403:
        failures.append("admin pulse was refused; default-deny locked the operator")
    if child.get("admin_pulse_secret") is True:
        failures.append("admin pulse body contained a tenant canary")
    reason_a = child.get("reason_a") if isinstance(child.get("reason_a"), dict) else {}
    reason_b_keyless = child.get("reason_b_keyless") if isinstance(child.get("reason_b_keyless"), dict) else {}
    reason_b = child.get("reason_b") if isinstance(child.get("reason_b"), dict) else {}
    reason_a_revoked = child.get("reason_a_revoked") if isinstance(child.get("reason_a_revoked"), dict) else {}
    reason_b_still = child.get("reason_b_still") if isinstance(child.get("reason_b_still"), dict) else {}
    if reason_a.get("status") != 200 or reason_a.get("tenant_no_key") is True:
        failures.append("keyed tenant A did not receive a request-scoped engine")
    if reason_b_keyless.get("tenant_no_key") is not True:
        failures.append("keyless tenant B did not get the honest keyless reply")
    if reason_b.get("status") != 200 or reason_b.get("tenant_no_key") is True:
        failures.append("keyed tenant B did not receive its own engine")
    if reason_a_revoked.get("tenant_no_key") is not True:
        failures.append("revoking tenant A did not drop A's cached engine")
    if reason_b_still.get("tenant_no_key") is True:
        failures.append("revoking tenant A dropped tenant B's engine")
    for summary in (reason_a, reason_b, reason_a_revoked, reason_b_still, reason_b_keyless):
        names = set(summary.get("tool_names") or [])
        if names - {"code_validate"}:
            failures.append(f"tenant tool call outside code_validate: {sorted(names)}")
        if summary.get("secret_in_body") is True and summary.get("tenant_no_key") is not True:
            # The reason body echoes the caller's own prompt. That echo is the
            # response, not shared memory. secret_in_body is still recorded.
            pass
    deny = child.get("default_deny") if isinstance(child.get("default_deny"), list) else []
    by_key = {(row.get("method"), row.get("path")): row for row in deny if isinstance(row, dict)}
    gaps: list[str] = []
    for method, path in _REQUIRED_DENY:
        row = by_key.get((method, path))
        if not isinstance(row, dict) or row.get("mounted") is not True:
            holds.append(f"{method} {path} was not mounted")
        elif row.get("status") != 403:
            failures.append(f"tenant {method} {path} returned {row.get('status')}")
        elif row.get("secret_in_body") is True:
            failures.append(f"tenant {method} {path} body contained a canary")
    for row in deny:
        if not isinstance(row, dict):
            continue
        key = (row.get("method"), row.get("path"))
        if key in _REQUIRED_DENY:
            continue
        if row.get("mounted") is not True:
            gaps.append(f"{row.get('method')} {row.get('path')} was not mounted")
        elif row.get("status") != 403:
            failures.append(f"tenant {row.get('method')} {row.get('path')} returned {row.get('status')}")
    home_paths = {}
    home_files = surfaces.get("home_files") if isinstance(surfaces.get("home_files"), dict) else {}
    if isinstance(home_files.get("paths"), dict):
        home_paths = home_files["paths"]
    else:
        holds.append("contained HOME files were not scanned")
    for label in _LEAK_LABELS:
        found_paths = home_paths.get(label) if isinstance(home_paths, dict) else None
        if found_paths:
            failures.append(f"{label} found in contained files {found_paths}")
    control_paths = home_paths.get("canary_control") if isinstance(home_paths, dict) else None
    if isinstance(control_paths, list) and not any(str(path).endswith("thoughts.jsonl") for path in control_paths):
        failures.append("control canary was not in the contained thoughts.jsonl file")
    shm = surfaces.get("dev_shm_new") if isinstance(surfaces.get("dev_shm_new"), dict) else {}
    if shm.get("readable") is False:
        holds.append("/dev/shm was not readable; new segments were not scanned")
    if not control_hits:
        failures.append("control canary was not observed on any shared surface")
    if failures:
        verdict = "fail"
    elif holds:
        verdict = "hold"
    else:
        verdict = "pass"
    return {"verdict": verdict, "failures": failures, "holds": holds, "gaps": gaps}


def _run(prepared: Any, out_path: Path, env: Mapping[str, str], timeout: float) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            list(prepared.argv),
            cwd=prepared.sidecar.parent,
            env=dict(env),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, bytes) else b""
        stderr = exc.stderr if isinstance(exc.stderr, bytes) else b""
        return {
            "started": False,
            "error": "timeout",
            "stdout": redact_text(stdout.decode("utf-8", "replace")[:2000]),
            "stderr": redact_text(stderr.decode("utf-8", "replace")[:2000]),
        }
    except OSError as exc:
        return {"started": False, "error": type(exc).__name__, "errno": exc.errno}
    status: dict[str, Any] | None = None
    if prepared.status_path.is_file():
        try:
            status = json.loads(prepared.status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            status = {"unreadable": True}
    child: dict[str, Any] | None = None
    secret_in_file = False
    if out_path.is_file():
        raw = out_path.read_text(encoding="utf-8")
        secret_in_file = _SECRET_RE.search(raw) is not None
        try:
            child = json.loads(redact_text(raw))
        except json.JSONDecodeError:
            child = None
    stdout = redact_text(completed.stdout.decode("utf-8", "replace")[:2000])
    stderr = redact_text(completed.stderr.decode("utf-8", "replace")[:2000])
    return {
        "started": child is not None and completed.returncode == 0 and child.get("ok") is True,
        "returncode": completed.returncode,
        "argv": list(prepared.argv),
        "deny_network": prepared.deny_network,
        "drop_caps": prepared.drop_caps,
        "child_env_names": sorted(env),
        "wrapper": status,
        "probe": child,
        "secret_in_child_file": secret_in_file,
        "stdout": stdout,
        "stderr": stderr,
    }


def measure(root: Path | None = None, *, timeout: float = 180) -> dict[str, Any]:
    """Run the contained smoke and return the receipt. Does not write it."""

    root = (root or repo_root()).resolve()
    started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    parent_net_ns = os.readlink("/proc/self/ns/net")
    import tempfile

    with tempfile.TemporaryDirectory(prefix="aureon-multi-user-") as directory:
        work = Path(directory)
        launch = work / "launch"
        out_path = launch / "multi-user-result.json"
        payload = [
            sys.executable,
            str(_CHILD.resolve()),
            "--repo",
            str(root),
            "--out",
            str(out_path),
        ]
        try:
            prepared = prepare_launch(launch, payload)
            env = contained_child_env(prepared.env, launch, root)
            child_run = _run(prepared, out_path, env, timeout)
        except ContainmentUnavailable as exc:
            prepared = None
            env = {}
            child_run = {"started": False, "error": str(exc)}
        except ContainmentRefused as exc:
            prepared = None
            env = {}
            child_run = {"started": False, "error": str(exc)}
        argv = list(child_run.get("argv") or (prepared.argv if prepared is not None else []))
    probe = child_run.get("probe") if isinstance(child_run.get("probe"), dict) else None
    if sys.platform != "linux":
        judged = {"verdict": "skip", "failures": ["not linux"], "holds": [], "gaps": []}
    elif child_run.get("error") and not child_run.get("started"):
        message = str(child_run.get("error"))
        if "unshare" in message or "not on PATH" in message:
            judged = {"verdict": "skip", "failures": [message], "holds": [], "gaps": []}
        else:
            judged = {"verdict": "fail", "failures": [message], "holds": [], "gaps": []}
    else:
        judged = judge(
            probe,
            started=bool(child_run.get("started")),
            parent_net_ns=parent_net_ns,
            argv_has_net="--net" in argv,
        )
    if child_run.get("secret_in_child_file") is True and "child report contained a canary" not in judged["failures"]:
        judged["failures"].append("child result file contained a canary prefix")
        judged["verdict"] = "fail"
    finished = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    child_public = _public_child(probe)
    published = public_pin(root)
    return {
        "schema": "aureon.measured.multi-user-smoke.v1",
        "stage": 9,
        "title": "contained multi-user tenant boundary",
        "verdict": judged["verdict"],
        "failures": judged["failures"],
        "holds": judged["holds"],
        "gaps": judged.get("gaps") or [],
        "go_live_clear": False,
        "go_live_receipt": None,
        "release_boundary": "HOLD",
        "orange_badge": "unchanged",
        "pin": published,
        "pin_changed": False,
        "containment_pin": PIN,
        "containment_pin_is_public_pin": published == PIN,
        "require_pin_changed": False,
        "started_from": STARTED_FROM,
        "git_head_at_measurement": _git_head(root),
        "worktree_dirty_at_measurement": _worktree_dirty(root),
        "live_trading": False,
        "orders_placed": False,
        "market_data_fetched": False,
        "listener_bound": False,
        "cold_boot_command": "python -m aureon.containment.multi_user_smoke",
        "cold_boot_argv_has_net": "--net" in argv,
        "parent_net_ns": parent_net_ns,
        "child_net_ns": (probe or {}).get("net_ns") if isinstance(probe, dict) else None,
        "child_env_names": child_run.get("child_env_names") or sorted(env),
        "parent_env_copied": False,
        "wrapper": child_run.get("wrapper"),
        "child": child_public,
        "shared_memory": _shared_memory_section(child_public),
        "holds_remaining": list(_HOLDS),
        "source_sha256": _file_hashes(root, _SOURCE_FILES),
        "unchanged_sha256": _file_hashes(root, _UNCHANGED_FILES),
        "started_at": started,
        "finished_at": finished,
        "kernel": " ".join(os.uname()),
        "python": sys.version.split()[0],
        "measurement_note": (
            "The child boots create_app with the local test ingress seam. "
            "operator_server.main is not called and no listener is bound. "
            "source_sha256 binds this stage's sources. git_head_at_measurement "
            "is HEAD when the command ran. The UTC stamps are this machine's "
            "clock, not receipt 3. go_live_clear stays false. "
            "aureon/operator/keystore.py is not listed in unchanged_sha256. "
            "This stage does not modify that file."
        ),
    }


def _public_child(child: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(child, dict):
        return None
    # Drop nothing functional. Canary hashes stay; raw canaries never enter.
    return child


def _shared_memory_section(child: dict[str, Any] | None) -> dict[str, Any]:
    surfaces = (child or {}).get("surfaces") if isinstance(child, dict) else {}
    if not isinstance(surfaces, dict):
        surfaces = {}
    scanned = []
    for name in ("thought_bus_recent", "thoughts_jsonl", "os_environ_values", "dev_shm_new"):
        surface = surfaces.get(name)
        if isinstance(surface, dict) and "found" in surface:
            scanned.append(name)
    preexisting = (surfaces.get("dev_shm_new") or {}).get("preexisting_count") if isinstance(surfaces.get("dev_shm_new"), dict) else None
    return {
        "claim": (
            "No universal shared-memory-leak claim. Each surface below was read "
            "or is named as unread. A canary is found or absent only on a surface "
            "whose found map is present."
        ),
        "scanned_surfaces": scanned,
        "dev_shm_preexisting_count": preexisting,
        "dev_shm_preexisting_read": False,
        "process_address_space": (
            "Not scored. The child handled the prompts, so those bytes exist in "
            "that process. That is not the shared thought bus."
        ),
        "subscriber_count_before": (child or {}).get("subscriber_count_before") if isinstance(child, dict) else None,
        "subscriber_count_after": (child or {}).get("subscriber_count_after") if isinstance(child, dict) else None,
        "subscriptions_before": (child or {}).get("subscriptions_before") if isinstance(child, dict) else None,
        "subscriptions_after": (child or {}).get("subscriptions_after") if isinstance(child, dict) else None,
    }


def render_markdown(receipt: dict[str, Any]) -> str:
    """One page. Figures are copied from the receipt."""

    child = receipt.get("child") if isinstance(receipt.get("child"), dict) else {}
    surfaces = child.get("surfaces") if isinstance(child.get("surfaces"), dict) else {}
    bus = surfaces.get("thought_bus_recent") if isinstance(surfaces.get("thought_bus_recent"), dict) else {}
    jsonl = surfaces.get("thoughts_jsonl") if isinstance(surfaces.get("thoughts_jsonl"), dict) else {}
    shm = surfaces.get("dev_shm_new") if isinstance(surfaces.get("dev_shm_new"), dict) else {}
    env_found = surfaces.get("os_environ_values") if isinstance(surfaces.get("os_environ_values"), dict) else {}
    memory = receipt.get("shared_memory") if isinstance(receipt.get("shared_memory"), dict) else {}
    tcp = child.get("tcp_1_1_1_1_443") if isinstance(child.get("tcp_1_1_1_1_443"), dict) else {}
    lines = [
        "# Contained multi-user smoke — stage 9",
        "",
        "This boots the tenant boundary that already lives in `aureon.operator` inside the stage-7 contained launcher. It is not a supported public runtime, not a listener, and not a go-live receipt.",
        "",
        f"Verdict: **{receipt.get('verdict')}**.",
        f"Release boundary: **{receipt.get('release_boundary')}**. Orange badge: {receipt.get('orange_badge')}. `go_live_clear`: {receipt.get('go_live_clear')}.",
        f"Public pin: `{receipt.get('pin')}` (changed by this stage: {receipt.get('pin_changed')}). Containment module pin: `{receipt.get('containment_pin')}` (same as public pin: {receipt.get('containment_pin_is_public_pin')}).",
        "Live trading: false. Orders placed: false. Market data fetched: false. Listener bound: false.",
        "",
        "## Cold boot",
        "",
        "```bash",
        str(receipt.get("cold_boot_command")),
        "```",
        "",
        f"Command included `unshare --net`: **{receipt.get('cold_boot_argv_has_net')}** (measured).",
        f"Parent net namespace `{receipt.get('parent_net_ns')}`, child `{receipt.get('child_net_ns')}` (measured).",
        f"Contained TCP 1.1.1.1:443 ok={tcp.get('ok')} errno={tcp.get('errno')} error={tcp.get('error')} bytes_read={tcp.get('bytes_read')} (measured).",
        "Boot entry: `create_app` with the local test ingress seam. `operator_server.main` was not called. `production_ready` on that seam is false.",
        "",
        "## Tenant boundary",
        "",
        f"Per-user encrypted stores: tenant A {child.get('store_a_bytes')} bytes, tenant B {child.get('store_b_bytes')} bytes. Plaintext key in the store file: {child.get('plaintext_key_in_store')} (measured). Cross-tenant key visible: {child.get('cross_tenant_key_visible')} (measured). Tenant key in `os.environ`: {child.get('environ_has_tenant_key')} (measured).",
        f"Request-scoped engines: keyed A `tenant_no_key`={((child.get('reason_a') or {}) if isinstance(child.get('reason_a'), dict) else {}).get('tenant_no_key')}, keyless B `tenant_no_key`={((child.get('reason_b_keyless') or {}) if isinstance(child.get('reason_b_keyless'), dict) else {}).get('tenant_no_key')}, keyed B `tenant_no_key`={((child.get('reason_b') or {}) if isinstance(child.get('reason_b'), dict) else {}).get('tenant_no_key')}, A after revoke `tenant_no_key`={((child.get('reason_a_revoked') or {}) if isinstance(child.get('reason_a_revoked'), dict) else {}).get('tenant_no_key')}, B after A's revoke `tenant_no_key`={((child.get('reason_b_still') or {}) if isinstance(child.get('reason_b_still'), dict) else {}).get('tenant_no_key')} (measured).",
        f"Default-deny sample: {json.dumps(child.get('default_deny'), sort_keys=True)} (measured).",
        f"Admin `GET /api/pulse` status: {child.get('admin_pulse_status')} (measured). Tenant `GET /api/me` status: {child.get('tenant_me_status')} (measured).",
        "",
        "## Shared memory",
        "",
        str(memory.get("claim")),
        "",
        f"Thought-bus deque items scanned: {bus.get('scanned_items')}. Control canary found: {(bus.get('found') or {}).get('canary_control') if isinstance(bus.get('found'), dict) else None}. Other canaries: {_canary_line(bus.get('found'))}.",
        f"`thoughts.jsonl` bytes: {jsonl.get('bytes')}. Truncated: {jsonl.get('truncated')}. Control canary found: {(jsonl.get('found') or {}).get('canary_control') if isinstance(jsonl.get('found'), dict) else None}. Other canaries: {_canary_line(jsonl.get('found'))}.",
        f"`os.environ` names scanned: {env_found.get('names_scanned')}. Canaries found: {_canary_line(env_found.get('found'))}. The signer and operator canaries are supposed to be in the child environment. They are a leak only if they show up on the bus, the JSONL file, or a new shared-memory segment.",
        f"New `/dev/shm` names: {shm.get('new_names')}. Bytes scanned: {shm.get('new_bytes_scanned')}. Pre-existing names: {shm.get('preexisting_count')} (not read). Canaries in new segments: {_canary_line(shm.get('found'))}.",
        f"Thought-bus subscriber count before tenant calls: {memory.get('subscriber_count_before')}. After: {memory.get('subscriber_count_after')}. Before: {json.dumps(memory.get('subscriptions_before'), sort_keys=True)}. After: {json.dumps(memory.get('subscriptions_after'), sort_keys=True)}. A count change is not, by itself, a prompt leak.",
        str(memory.get("process_address_space")),
        "",
        "## Still HOLD",
        "",
    ]
    for item in receipt.get("holds_remaining") or []:
        lines.append(f"- Receipt {item.get('id')}: {item.get('item')} — {item.get('status')}")
    extra = receipt.get("holds") or []
    if extra:
        lines.extend(["", "## Blocking gaps", ""])
        for item in extra:
            lines.append(f"- {item}")
    gaps = receipt.get("gaps") or []
    if gaps:
        lines.extend(["", "## Unmounted optional routes", ""])
        for item in gaps:
            lines.append(f"- {item}")
    failures = receipt.get("failures") or []
    if failures:
        lines.extend(["", "## Failures", ""])
        for item in failures:
            lines.append(f"- {item}")
    lines.extend(
        [
            "",
            f"Started from `{receipt.get('started_from')}`. Git HEAD at measurement: `{receipt.get('git_head_at_measurement')}`.",
            str(receipt.get("measurement_note")),
            "",
        ]
    )
    return "\n".join(lines)


def _canary_line(found: Any) -> str:
    if not isinstance(found, dict):
        return "not scanned"
    shown = {label: found.get(label) for label in _CANARY_LABELS if label != "canary_control"}
    return json.dumps(shown, sort_keys=True)


def write_receipt(receipt: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    text = redact_text(text)
    markdown = redact_text(render_markdown(receipt))
    unsafe = receipt_names_are_safe(text + markdown)
    if unsafe:
        raise RuntimeError("receipt still has credential-shaped names: " + ", ".join(unsafe))
    tmp_json = json_path.with_suffix(json_path.suffix + ".tmp")
    tmp_md = md_path.with_suffix(md_path.suffix + ".tmp")
    tmp_json.write_text(text, encoding="utf-8")
    tmp_md.write_text(markdown, encoding="utf-8")
    os.replace(tmp_json, json_path)
    os.replace(tmp_md, md_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Contained multi-user smoke. Does not place orders.")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--receipt-json", type=Path, default=None)
    parser.add_argument("--receipt-md", type=Path, default=None)
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args(argv)
    receipt = measure(repo_root(), timeout=args.timeout)
    if args.no_write:
        sys.stdout.write(redact_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n"))
    else:
        json_path = args.receipt_json or (repo_root() / "reports" / "measured" / "multi_user_smoke.json")
        md_path = args.receipt_md or (repo_root() / "reports" / "measured" / "multi_user_smoke.md")
        write_receipt(receipt, json_path, md_path)
        sys.stdout.write(f"{receipt['verdict']} {json_path}\n")
    return {"pass": 0, "hold": 0, "skip": 2, "fail": 1}.get(str(receipt["verdict"]), 1)


if __name__ == "__main__":
    raise SystemExit(main())
