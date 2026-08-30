"""Fail-closed composition root for Aureon's full live production release.

Operator approval is necessary, but it is not evidence that the runtime is
ready.  This module binds the current source checkout to the twelve-layer
production read-back, the 10 -> 9 -> 1 HNC/Auris field, the economic mutation
census, live configuration, and the configured Ollama brain.  It never places
an order or grants economic authority; it only returns an evidence receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aureon.autonomous.aureon_full_stack_release_gate import (
    DEFAULT_FULL_STACK_EVIDENCE_PATH,
    PRODUCTION_READBACK,
    FullStackReleaseGate,
    FullStackReleaseRequest,
    LocalFullStackEvidenceResolver,
)

SCHEMA_VERSION = "aureon.full-live-release.v1"
DEFAULT_RECEIPT_PATH = Path("state/aureon_full_live_release.json")
ACTIVE_COHERENCE_THRESHOLD = 0.80

_FALSE_FLAGS = {
    "action_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "economic_mutation": False,
    "provider_eligible": False,
    "operational_eligible": False,
    "actionable": False,
    "action_gate_passed": False,
}

_REQUIRED_CREDENTIAL_NAMES = (
    "ALPACA_API_KEY",
    "ALPACA_SECRET_KEY",
    "AUREON_ALLOWED_ORIGINS",
    "AUREON_WORKER_ACCESS_SECRET",
    "BINANCE_API_KEY",
    "BINANCE_API_SECRET",
    "CAPITAL_API_KEY",
    "CAPITAL_IDENTIFIER",
    "CAPITAL_PASSWORD",
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_API_TOKEN",
    "KRAKEN_API_KEY",
    "KRAKEN_API_SECRET",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_URL",
)


@dataclass(frozen=True)
class FullLiveReleaseResult:
    decision: str
    receipt: Mapping[str, Any]


ScopeDigestFn = Callable[[Path], str]
StackProbeFn = Callable[[Path, str, float], Mapping[str, Any]]
EconomicAuditFn = Callable[[Path], Mapping[str, Any]]
FieldProbeFn = Callable[[Path, float], Mapping[str, Any]]
OllamaProbeFn = Callable[[Mapping[str, str]], Mapping[str, Any]]


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Mapping[str, Any] | str | bytes) -> str:
    if isinstance(value, Mapping):
        raw = _canonical_bytes(value)
    elif isinstance(value, str):
        raw = value.encode("utf-8")
    else:
        raw = value
    return hashlib.sha256(raw).hexdigest()


def _receipt(causal: Mapping[str, Any]) -> dict[str, Any]:
    return {**dict(causal), "receipt_id": f"live:release:{_sha256(causal)}"}


def _git(root: Path, *args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError("git_source_scope_unavailable")
    return result.stdout


def compute_source_scope_digest(root: Path) -> str:
    """Bind HEAD plus every tracked change and non-ignored untracked file."""

    resolved = root.resolve()
    head = _git(resolved, "rev-parse", "HEAD").decode("ascii", errors="strict").strip()
    changed = _git(resolved, "diff", "--name-only", "-z", "HEAD").split(b"\0")
    untracked = _git(resolved, "ls-files", "--others", "--exclude-standard", "-z").split(b"\0")
    excluded = {
        DEFAULT_FULL_STACK_EVIDENCE_PATH.as_posix(),
        DEFAULT_RECEIPT_PATH.as_posix(),
    }
    paths = sorted(
        {item.decode("utf-8", errors="strict").replace("\\", "/") for item in (*changed, *untracked) if item}
        - excluded
    )
    material: dict[str, Any] = {
        "schema": "aureon.source-scope.v1",
        "head": head,
        "files": [],
    }
    for relative in paths:
        path = (resolved / Path(relative)).resolve()
        try:
            path.relative_to(resolved)
        except ValueError as exc:
            raise RuntimeError("source_scope_path_escape") from exc
        if path.is_file():
            digest = _sha256(path.read_bytes())
            status = "present"
        else:
            digest = ""
            status = "deleted"
        material["files"].append({"path": relative, "status": status, "sha256": digest})
    return _sha256(material)


def _read_dotenv_names(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return values
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        key = name.strip()
        if not key or not (key[0].isalpha() or key[0] == "_"):
            continue
        if not all(char.isalnum() or char == "_" for char in key):
            continue
        normalized = value.strip()
        if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in "\"'":
            normalized = normalized[1:-1]
        values[key] = normalized
    return values


def merged_runtime_environment(root: Path, environ: Mapping[str, str] | None = None) -> dict[str, str]:
    values = _read_dotenv_names(root / ".env")
    values.update({str(key): str(value) for key, value in (environ or os.environ).items()})
    return values


def _is_true(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _is_false(value: Any) -> bool:
    return str(value or "").strip().lower() in {"0", "false", "no", "off"}


def _credential_probe(environ: Mapping[str, str]) -> dict[str, Any]:
    missing = sorted(name for name in _REQUIRED_CREDENTIAL_NAMES if not str(environ.get(name, "")).strip())
    return {
        "ok": not missing,
        "required_names": list(_REQUIRED_CREDENTIAL_NAMES),
        "present_names": sorted(set(_REQUIRED_CREDENTIAL_NAMES) - set(missing)),
        "missing_names": missing,
    }


def _live_flag_probe(environ: Mapping[str, str]) -> dict[str, Any]:
    required_true = (
        "AUREON_LIVE_TRADING",
        "AUREON_ORDER_INTENT_PUBLISH",
        "AUREON_ORDER_TICKET_REQUIRES_EXECUTOR",
        "AUREON_UNIFIED_ORDER_EXECUTOR",
        "LIVE",
    )
    required_false = (
        "ALPACA_PAPER",
        "AUREON_AUDIT_MODE",
        "AUREON_DISABLE_EXCHANGE_MUTATIONS",
        "AUREON_DISABLE_REAL_ORDERS",
        "AUREON_DRY_RUN",
        "BINANCE_TESTNET",
        "BINANCE_USE_TESTNET",
        "CAPITAL_DEMO",
        "CAPITAL_DEMO_MODE",
        "DRY_RUN",
    )
    failed = [name for name in required_true if not _is_true(environ.get(name))]
    failed.extend(name for name in required_false if not _is_false(environ.get(name)))
    if str(environ.get("CONFIRM_LIVE", "")).strip().lower() != "yes":
        failed.append("CONFIRM_LIVE")
    if environ.get("AUREON_ORDER_AUTHORITY_MODE") != "intent_only_runtime_gated":
        failed.append("AUREON_ORDER_AUTHORITY_MODE")
    return {
        "ok": not failed,
        "failed_names": sorted(set(failed)),
        "policy": "live_true_dry_false_intent_only_runtime_gated",
    }


def probe_full_stack(root: Path, scope_digest: str, now: float) -> dict[str, Any]:
    path = root / DEFAULT_FULL_STACK_EVIDENCE_PATH
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raw = {}
    release_id = raw.get("release_id") if isinstance(raw, Mapping) else None
    if not isinstance(release_id, str) or not release_id.strip():
        release_id = f"release:{scope_digest[:24]}"
    request = FullStackReleaseRequest(
        release_id=release_id,
        environment="production",
        assurance_level=PRODUCTION_READBACK,
        scope_digest=scope_digest,
    )
    gate = FullStackReleaseGate(
        resolver=LocalFullStackEvidenceResolver(root=root),
        now=lambda: now,
    )
    result = gate.evaluate(request)
    return {
        "ok": result.decision == "ACCEPT",
        "decision": result.decision,
        "reason": str(result.receipt.get("reason") or "full_stack_release_hold"),
        "receipt_id": str(result.receipt.get("receipt_id") or ""),
    }


def run_economic_audit(root: Path) -> dict[str, Any]:
    from scripts.validation.audit_economic_mutation_boundaries import audit

    result = audit(
        root=root,
        allowlist_path=root / "scripts" / "validation" / "economic_mutation_allowlist.json",
    )
    return {
        "ok": bool(result.get("inventory_aligned")) and bool(result.get("certified_no_bypass")),
        "inventory_aligned": bool(result.get("inventory_aligned")),
        "certified_no_bypass": bool(result.get("certified_no_bypass")),
        "detected_count": int(result.get("detected_count", 0)),
        "classified_count": int(result.get("classified_count", 0)),
        "blocker_count": int(result.get("blocker_count", 0)),
        "counts_by_classification": dict(result.get("counts_by_classification") or {}),
    }


class _NoThoughtBus:
    @staticmethod
    def recall(topic: str, limit: int = 1) -> list[Any]:
        del topic, limit
        return []


def probe_ten_nine_one_fields(root: Path, now: float) -> dict[str, Any]:
    from aureon.autonomous.aureon_ten_nine_one_thought_path import (
        ACTIVE_COHERENCE_THRESHOLD as PATH_ACTIVE_THRESHOLD,
    )
    from aureon.autonomous.aureon_ten_nine_one_thought_path import (
        LocalHncAurisEvidenceResolver,
        ThoughtPathRequest,
    )
    from aureon.swarm.auris_node_receipts import validate_hnc_evidence, validate_provider_moment

    request = ThoughtPathRequest(
        subject_type="release",
        subject_id="full-live-release",
        process_id="aureon-full-live-preflight",
        stage="production_readback",
        work_kind="full_stack_release",
        prompt_digest=_sha256("aureon-full-live-release"),
        brain_passport_id="brain:full-live-release-preflight",
    )
    resolver = LocalHncAurisEvidenceResolver(bus=_NoThoughtBus(), root=root)
    raw_hnc = resolver.resolve_hnc_evidence(request)
    hnc = validate_hnc_evidence(raw_hnc or {}, now=now)
    raw_auris = resolver.resolve_auris_evidence(
        request,
        answer_digest=request.prompt_digest,
        hnc_receipt_id=hnc["receipt_id"],
    )
    moment = validate_provider_moment(hnc, raw_auris or {}, now=now)
    gamma = (raw_auris or {}).get("coherence_gamma")
    gate_open = (raw_auris or {}).get("gate_open") is True
    gamma_ok = (
        not isinstance(gamma, bool)
        and isinstance(gamma, (int, float))
        and float(gamma) >= PATH_ACTIVE_THRESHOLD
    )
    return {
        "ok": gate_open and gamma_ok,
        "hnc_receipt_id": moment.hnc_receipt_id,
        "auris_receipt_id": moment.auris_receipt_id,
        "provider_moment_digest": moment.provider_moment_digest,
        "provider_receipt_ids": list(moment.provider_receipt_ids),
        "provider_source_timestamp": moment.source_timestamp,
        "auris_gamma": float(gamma) if gamma_ok else None,
        "auris_gate_open": gate_open,
        "active_threshold": ACTIVE_COHERENCE_THRESHOLD,
    }


def probe_ollama(environ: Mapping[str, str]) -> dict[str, Any]:
    base = str(environ.get("AUREON_LLM_BASE_URL") or environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434")
    parsed = urllib.parse.urlparse(base)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not host:
        return {"ok": False, "reason": "valid_ollama_endpoint_required", "model": ""}
    if parsed.scheme == "http" and host not in {"127.0.0.1", "localhost", "::1"}:
        return {"ok": False, "reason": "remote_ollama_requires_https", "model": ""}
    tags_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/api/tags", "", "", ""))
    headers: dict[str, str] = {"Accept": "application/json"}
    token = str(environ.get("OLLAMA_API_KEY") or "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(tags_url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10.0) as response:  # noqa: S310 - validated endpoint
            payload = json.loads(response.read(1_048_576).decode("utf-8"))
    except (OSError, UnicodeError, ValueError, urllib.error.URLError):
        return {"ok": False, "reason": "ollama_health_readback_required", "model": ""}
    names = sorted(
        str(item.get("name") or item.get("model") or "")
        for item in (payload.get("models") if isinstance(payload, Mapping) else []) or []
        if isinstance(item, Mapping) and (item.get("name") or item.get("model"))
    )
    model = str(environ.get("AUREON_LLM_MODEL") or "llama3:latest").strip()
    return {
        "ok": model in names,
        "reason": "ollama_model_ready" if model in names else "configured_ollama_model_required",
        "model": model,
        "available_model_count": len(names),
    }


def evaluate_full_live_release(
    *,
    root: Path,
    environ: Mapping[str, str] | None = None,
    now: float | None = None,
    scope_digest_fn: ScopeDigestFn = compute_source_scope_digest,
    stack_probe_fn: StackProbeFn = probe_full_stack,
    economic_audit_fn: EconomicAuditFn = run_economic_audit,
    field_probe_fn: FieldProbeFn = probe_ten_nine_one_fields,
    ollama_probe_fn: OllamaProbeFn = probe_ollama,
) -> FullLiveReleaseResult:
    resolved = root.resolve()
    current = float(time.time() if now is None else now)
    runtime_env = merged_runtime_environment(resolved, environ)
    failures: list[str] = []

    try:
        scope_digest = scope_digest_fn(resolved)
        source_scope = {"ok": True, "scope_digest": scope_digest}
    except (OSError, RuntimeError, UnicodeError, ValueError):
        scope_digest = "0" * 64
        source_scope = {"ok": False, "scope_digest": scope_digest}
        failures.append("source_scope")

    try:
        full_stack = dict(stack_probe_fn(resolved, scope_digest, current))
    except Exception:  # noqa: BLE001 - dependency failure is a fixed HOLD code
        full_stack = {"ok": False, "decision": "HOLD", "reason": "full_stack_probe_failed", "receipt_id": ""}
    if full_stack.get("ok") is not True:
        failures.append("full_stack_release")

    credentials = _credential_probe(runtime_env)
    if credentials["ok"] is not True:
        failures.append("credentials")

    live_flags = _live_flag_probe(runtime_env)
    if live_flags["ok"] is not True:
        failures.append("live_flags")

    try:
        ollama = dict(ollama_probe_fn(runtime_env))
    except Exception:  # noqa: BLE001 - dependency failure is a fixed HOLD code
        ollama = {"ok": False, "reason": "ollama_probe_failed", "model": ""}
    if ollama.get("ok") is not True:
        failures.append("ollama")

    try:
        fields = dict(field_probe_fn(resolved, current))
    except Exception:  # noqa: BLE001 - no raw provider exception in release receipt
        fields = {
            "ok": False,
            "hnc_receipt_id": "",
            "auris_receipt_id": "",
            "provider_moment_digest": "",
            "provider_receipt_ids": [],
            "provider_source_timestamp": None,
            "auris_gamma": None,
            "auris_gate_open": False,
            "active_threshold": ACTIVE_COHERENCE_THRESHOLD,
        }
    if fields.get("ok") is not True:
        failures.append("ten_nine_one_fields")

    try:
        economic = dict(economic_audit_fn(resolved))
    except Exception:  # noqa: BLE001 - audit failure is a fixed HOLD code
        economic = {
            "ok": False,
            "inventory_aligned": False,
            "certified_no_bypass": False,
            "detected_count": 0,
            "classified_count": 0,
            "blocker_count": 0,
            "counts_by_classification": {},
        }
    if economic.get("ok") is not True:
        failures.append("economic_zero_bypass")

    failed_checks = sorted(set(failures))
    decision = "ACCEPT" if not failed_checks else "HOLD"
    causal = {
        "schema_version": SCHEMA_VERSION,
        "decision": decision,
        "reason": "full_live_release_accepted"
        if decision == "ACCEPT"
        else "complete_live_release_evidence_required",
        "failed_checks": failed_checks,
        "repo_root_digest": _sha256(str(resolved).casefold()),
        "source_scope": source_scope,
        "full_stack_release": full_stack,
        "credentials": credentials,
        "live_flags": live_flags,
        "ollama": ollama,
        "ten_nine_one_fields": fields,
        "economic_zero_bypass": economic,
        "checked_at": current,
        **_FALSE_FLAGS,
    }
    receipt = _receipt(causal)
    return FullLiveReleaseResult(decision=decision, receipt=receipt)


def _atomic_write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        temporary.write_bytes(_canonical_bytes(value) + b"\n")
        os.replace(temporary, path)
        try:
            path.chmod(0o600)
        except OSError:
            pass
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--receipt-path", type=Path)
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    result = evaluate_full_live_release(root=root)
    if not args.no_write:
        receipt_path = args.receipt_path or root / DEFAULT_RECEIPT_PATH
        if not receipt_path.is_absolute():
            receipt_path = root / receipt_path
        _atomic_write(receipt_path.resolve(), result.receipt)
    print(
        json.dumps(
            result.receipt,
            sort_keys=True,
            indent=2 if args.pretty else None,
            separators=None if args.pretty else (",", ":"),
        )
    )
    return 0 if result.decision == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DEFAULT_RECEIPT_PATH",
    "FullLiveReleaseResult",
    "SCHEMA_VERSION",
    "compute_source_scope_digest",
    "evaluate_full_live_release",
    "main",
    "merged_runtime_environment",
    "probe_full_stack",
    "probe_ollama",
    "probe_ten_nine_one_fields",
    "run_economic_audit",
]
