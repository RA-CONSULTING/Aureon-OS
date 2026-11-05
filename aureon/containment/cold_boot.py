"""Cold boot a contained process and write the stage-7 receipt.

The contained process is a new ``python -I`` started by ``unshare``.
The process that runs this module is the measurer. It is not inside the
network namespace. Its one outbound TCP handshake to ``1.1.1.1:443`` is
the control, reads zero bytes, and is labelled as outside containment.

No order is placed. No market series is fetched. The public pin is not
written.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureon.containment.native import (
    PIN,
    STARTED_FROM,
    ContainmentRefused,
    ContainmentUnavailable,
    authorize_network_allow,
    prepare_launch,
)

_PROBE = Path(__file__).with_name("_child_probe.py")
_ROOT = Path(__file__).resolve().parents[2]
_UNREACHABLE = {errno.ENETUNREACH, errno.ENETDOWN, errno.EHOSTUNREACH}
_SOURCE_FILES = (
    "aureon/containment/__init__.py",
    "aureon/containment/__main__.py",
    "aureon/containment/_child_probe.py",
    "aureon/containment/_child_wrapper.py",
    "aureon/containment/cold_boot.py",
    "aureon/containment/native.py",
)
_UNCHANGED_FILES = (
    "README.md",
    "mcp/aureon_public/guard_loader.py",
    "mcp/aureon_public/pin_blob.py",
    "mcp/aureon_public/sweep_guard.py",
    "scripts/linux/install-linux.sh",
)
_ALLOW_PROBE = (
    "import json, os, sys\n"
    "sys.stdout.write(json.dumps({\n"
    '    "connect_attempted": False,\n'
    '    "euid": os.geteuid(),\n'
    '    "net_ns": os.readlink("/proc/self/ns/net"),\n'
    "}))\n"
)

_HOLDS = (
    {
        "id": 2,
        "item": "exact target-source measurement and immutable release provenance",
        "status": "HOLD",
    },
    {
        "id": 3,
        "item": "durable HNC evidence with an external monotonic head anchor",
        "status": "HOLD",
    },
    {
        "id": 4,
        "item": "complete source-boundary census closure",
        "status": "HOLD",
    },
    {
        "id": 5,
        "item": "authenticated deployment receipt and provider-side read-back",
        "status": "HOLD",
    },
)


def repo_root() -> Path:
    return _ROOT


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_hashes(root: Path, names: tuple[str, ...]) -> dict[str, str]:
    return {name: _sha256(root / name) for name in names}


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


def _tcp_control(host: str, port: int, timeout: float) -> dict[str, Any]:
    started = time.perf_counter()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout)
        sock.connect((host, port))
    except OSError as exc:
        result: dict[str, Any] = {
            "ok": False,
            "errno": exc.errno,
            "error": errno.errorcode.get(exc.errno, type(exc).__name__),
        }
    else:
        result = {"ok": True, "errno": None, "error": None}
    finally:
        sock.close()
    result.update(
        {
            "host": host,
            "port": port,
            "bytes_read": 0,
            "application_payload": "none",
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
            "tag": "measured",
            "where": "measurer, outside the contained network namespace",
        }
    )
    return result


def _decode(data: bytes | None, limit: int = 800) -> str:
    if not data:
        return ""
    return data.decode("utf-8", "replace")[:limit]


def _run(prepared: Any, timeout: float) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            list(prepared.argv),
            cwd=prepared.sidecar.parent,
            env=dict(prepared.env),
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "started": False,
            "error": "timeout",
            "stderr": _decode(exc.stderr if isinstance(exc.stderr, bytes) else None),
            "stdout": _decode(exc.stdout if isinstance(exc.stdout, bytes) else None),
        }
    except OSError as exc:
        return {"started": False, "error": type(exc).__name__, "errno": exc.errno}
    status: dict[str, Any] | None = None
    if prepared.status_path.is_file():
        try:
            status = json.loads(prepared.status_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            status = {"unreadable": True}
    stdout = completed.stdout.decode("utf-8", "replace").strip()
    probe: dict[str, Any] | None = None
    if stdout:
        try:
            probe = json.loads(stdout)
        except json.JSONDecodeError:
            probe = None
    return {
        "started": probe is not None and completed.returncode == 0,
        "returncode": completed.returncode,
        "argv": list(prepared.argv),
        "deny_network": prepared.deny_network,
        "drop_caps": prepared.drop_caps,
        "grant_id": prepared.grant_id,
        "child_env_names": sorted(prepared.env),
        "wrapper": status,
        "probe": probe,
        "stdout_prefix": stdout[:240],
        "stderr": _decode(completed.stderr),
    }


def _payload(root: Path, *, attempt_lo_up: bool) -> list[str]:
    argv = [
        sys.executable,
        "-I",
        str(_PROBE.resolve()),
        "--marker",
        str(root / "docs" / "runbooks" / "GO_LIVE_HARDENING.md"),
    ]
    if attempt_lo_up:
        argv.append("--attempt-lo-up")
    return argv


def _errno_blocked(probe: dict[str, Any] | None) -> str | None:
    if not isinstance(probe, dict):
        return "probe json missing"
    if probe.get("ok") is True:
        return "connect succeeded"
    err = probe.get("errno")
    if err not in _UNREACHABLE:
        return f"errno {err} is not a no-route failure"
    return None


def judge_default(child: dict[str, Any], parent_net_ns: str) -> dict[str, Any]:
    """Fail closed. Missing evidence is not a pass."""

    failures: list[str] = []
    probe = child.get("probe") if isinstance(child.get("probe"), dict) else None
    if not child.get("started") or probe is None:
        failures.append("contained process did not return a probe")
        return {"verdict": "fail", "allowed_at_default": "unproven", "failures": failures}
    if probe.get("socket_monkeypatch") is not False:
        failures.append("probe claims a socket monkeypatch")
    if probe.get("socket_module") != "socket":
        failures.append("socket.socket is not the stdlib class")
    if probe.get("net_ns") == parent_net_ns or not str(probe.get("net_ns", "")).startswith("net:"):
        failures.append("child network namespace is not a new net namespace")
    if probe.get("interfaces_proc_net_dev") != ["lo"]:
        failures.append("/proc/net/dev is not lo only")
    if probe.get("default_route_ifaces"):
        failures.append("a default route is present before any admin")
    lo_before = probe.get("lo_before") if isinstance(probe.get("lo_before"), dict) else {}
    if lo_before.get("up") is not False:
        failures.append("lo was up at process start")
    probes = probe.get("probes") if isinstance(probe.get("probes"), dict) else {}
    for name in (
        "tcp_1.1.1.1_443",
        "tcp_127.0.0.1_9",
        "udp_8.8.8.8_53",
        "libc_connect_1.1.1.1_443",
        "tcp_1.1.1.1_443_after_socket_reload",
    ):
        reason = _errno_blocked(probes.get(name) if isinstance(probes.get(name), dict) else None)
        if reason:
            failures.append(f"{name}: {reason}")
    v6 = probes.get("tcp6_2001:4860:4860::8888_53")
    if isinstance(v6, dict) and v6.get("ok") is True:
        failures.append("ipv6 connect succeeded")
    raw = probes.get("raw_icmp_create")
    if isinstance(raw, dict) and raw.get("ok") is True:
        failures.append("raw icmp socket opened after capability drop")
    caps = probe.get("caps") if isinstance(probe.get("caps"), dict) else {}
    if caps.get("CapEff") != "0000000000000000":
        failures.append("effective capabilities were not zero after exec")
    attempt = probe.get("lo_up_attempt") if isinstance(probe.get("lo_up_attempt"), dict) else {}
    if attempt.get("errno") != errno.EPERM:
        failures.append("loopback admin was not EPERM after capability drop")
    wrapper = child.get("wrapper") if isinstance(child.get("wrapper"), dict) else {}
    remount = wrapper.get("sysfs_remount") if isinstance(wrapper.get("sysfs_remount"), dict) else {}
    if remount.get("ok") is not True:
        failures.append("sysfs was not remounted in the contained mount namespace")
    sysfs = probe.get("sysfs_net")
    if sysfs != ["lo"]:
        failures.append("/sys/class/net after remount is not lo only")
    allowed = "none" if not failures else "unproven"
    return {
        "verdict": "pass" if not failures else "fail",
        "allowed_at_default": allowed,
        "failures": failures,
    }


def _gap_notes(gap: dict[str, Any]) -> list[dict[str, str]]:
    probe = gap.get("probe") if isinstance(gap.get("probe"), dict) else None
    if not gap.get("started") or probe is None:
        return [
            {
                "tag": "measured",
                "statement": (
                    "The pre-drop gap process did not return a probe. "
                    "Whether mapped root can bring lo up was not measured."
                ),
            }
        ]
    notes: list[dict[str, str]] = []
    attempt = probe.get("lo_up_attempt") if isinstance(probe.get("lo_up_attempt"), dict) else {}
    after = probe.get("after_lo_up") if isinstance(probe.get("after_lo_up"), dict) else {}
    local = after.get("tcp_127.0.0.1_9") if isinstance(after.get("tcp_127.0.0.1_9"), dict) else {}
    external = after.get("tcp_1.1.1.1_443") if isinstance(after.get("tcp_1.1.1.1_443"), dict) else {}
    if attempt.get("ok") is True and local.get("errno") == errno.ECONNREFUSED and external.get("ok") is not True:
        notes.append(
            {
                "tag": "measured",
                "statement": (
                    "Before capability drop, mapped root set lo up. "
                    "127.0.0.1 then returned ECONNREFUSED. "
                    "1.1.1.1 stayed unreachable. The default payload drops "
                    "capabilities first, and that same ioctl returns EPERM."
                ),
            }
        )
    else:
        notes.append(
            {
                "tag": "measured",
                "statement": (
                    "The pre-drop loopback admin did not match the expected "
                    f"shape (attempt ok={attempt.get('ok')}, "
                    f"localhost errno={local.get('errno')}, "
                    f"external ok={external.get('ok')})."
                ),
            }
        )
    raw = (probe.get("probes") or {}).get("raw_icmp_create") if isinstance(probe.get("probes"), dict) else None
    if isinstance(raw, dict):
        notes.append(
            {
                "tag": "measured",
                "statement": (
                    "Before capability drop, creating an ICMP raw socket "
                    f"returned ok={raw.get('ok')} errno={raw.get('errno')} "
                    f"error={raw.get('error')}. No datagram was sent."
                ),
            }
        )
    return notes


def _static_gaps(default: dict[str, Any]) -> list[dict[str, str]]:
    probe = default.get("probe") if isinstance(default.get("probe"), dict) else {}
    wrapper = default.get("wrapper") if isinstance(default.get("wrapper"), dict) else {}
    gaps = [
        {
            "tag": "measured",
            "statement": (
                "The contained process is a new python -I. It does not import "
                "aureon and does not assign socket.socket. "
                f"socket module at start: {probe.get('socket_module')}."
            ),
        },
        {
            "tag": "cited",
            "statement": (
                "mcp/aureon_public/sweep_guard.py replaces socket.socket "
                "in-process during a sweep. That is not a network namespace. "
                "This stage does not change that file or the public pin "
                f"{PIN}."
            ),
        },
        {
            "tag": "inferred",
            "statement": (
                "No seccomp filter and no landlock are installed. A kernel "
                "flaw in user or network namespaces is outside this receipt."
            ),
        },
        {
            "tag": "inferred",
            "statement": (
                "Mapped root in a new user namespace is not treated as "
                "CAP_NET_ADMIN on the parent network namespace. This receipt "
                "does not flip a host interface to test that."
            ),
        },
    ]
    before = wrapper.get("sysfs_before")
    after = probe.get("sysfs_net")
    if isinstance(before, list) and before != ["lo"] and after == ["lo"]:
        gaps.append(
            {
                "tag": "measured",
                "statement": (
                    "Before the sysfs remount, /sys/class/net listed "
                    + ", ".join(before)
                    + ". After remount it listed lo only. /proc/net/dev is "
                    "the namespace device list and listed lo."
                ),
            }
        )
    marker = probe.get("marker") if isinstance(probe.get("marker"), dict) else {}
    passwd = probe.get("etc_passwd") if isinstance(probe.get("etc_passwd"), dict) else {}
    if marker.get("readable") is True or passwd.get("readable") is True:
        gaps.append(
            {
                "tag": "measured",
                "statement": (
                    "Filesystem isolation is not this receipt. "
                    f"The go-live runbook was readable={marker.get('readable')} "
                    f"and /etc/passwd was readable={passwd.get('readable')}. "
                    "Contents were not recorded."
                ),
            }
        )
    gaps.append(
        {
            "tag": "cited",
            "statement": (
                "Receipts 2, 3, 4, and 5 remain HOLD. The orange "
                "release-boundary badge is unchanged. scripts/linux/install-linux.sh "
                "still execs the isolated bootstrap and does not start this cold boot. "
                "No live Aureon instance is claimed. The system is not claimed alive."
            ),
        }
    )
    gaps.append(
        {
            "tag": "measured",
            "statement": (
                "issued_at on the allow-path audit is this machine's UTC clock. "
                "It is not an external monotonic head."
            ),
        }
    )
    return gaps


def measure(root: Path | None = None, *, timeout: float = 20) -> dict[str, Any]:
    """Run the cold boot and return the receipt. Does not write it."""

    root = (root or repo_root()).resolve()
    started = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    parent_net_ns = os.readlink("/proc/self/ns/net")
    host = _tcp_control("1.1.1.1", 443, 2.0)
    with tempfile.TemporaryDirectory(prefix="aureon-containment-") as directory:
        work = Path(directory)
        default_dir = work / "default"
        gap_dir = work / "gap"
        allow_dir = work / "allow"
        try:
            default_prepared = prepare_launch(
                default_dir,
                _payload(root, attempt_lo_up=True),
            )
            default = _run(default_prepared, timeout)
        except ContainmentUnavailable as exc:
            default = {"started": False, "error": str(exc)}
        except ContainmentRefused as exc:
            default = {"started": False, "error": str(exc)}
        try:
            gap_prepared = prepare_launch(
                gap_dir,
                _payload(root, attempt_lo_up=True),
                drop_caps=False,
            )
            gap = _run(gap_prepared, timeout)
        except (ContainmentUnavailable, ContainmentRefused) as exc:
            gap = {"started": False, "error": str(exc)}
        allow_script = allow_dir / "allow_ns_probe.py"
        allow_dir.mkdir(parents=True, exist_ok=True)
        allow_script.write_text(_ALLOW_PROBE, encoding="utf-8")
        grant = authorize_network_allow(
            "stage 7 receipt shows this grant shares the parent net namespace",
            "stage7-receipt",
            issued_at=started,
        )
        try:
            allow_prepared = prepare_launch(
                allow_dir / "launch",
                [sys.executable, "-I", str(allow_script.resolve())],
                grant=grant,
            )
            allow = _run(allow_prepared, timeout)
        except (ContainmentUnavailable, ContainmentRefused) as exc:
            allow = {"started": False, "error": str(exc)}
        default_argv = list(default.get("argv") or [])
    if sys.platform != "linux":
        judged = {"verdict": "skip", "allowed_at_default": "unproven", "failures": ["not linux"]}
    elif not default.get("started") and default.get("error"):
        judged = {
            "verdict": "skip",
            "allowed_at_default": "unproven",
            "failures": [str(default.get("error"))],
        }
    elif not default.get("started"):
        judged = {
            "verdict": "skip" if default.get("probe") is None else "fail",
            "allowed_at_default": "unproven",
            "failures": ["contained process did not start"],
        }
    else:
        judged = judge_default(default, parent_net_ns)
    allow_probe = allow.get("probe") if isinstance(allow.get("probe"), dict) else {}
    allow_same = bool(allow_probe.get("net_ns")) and allow_probe.get("net_ns") == parent_net_ns
    finished = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    receipt: dict[str, Any] = {
        "schema": "aureon.measured.native-process-containment.v1",
        "stage": 7,
        "receipt": 1,
        "title": "native process containment with a zero-network default",
        "verdict": judged["verdict"],
        "allowed_at_default": judged["allowed_at_default"],
        "failures": judged["failures"],
        "tags": {
            "cold_boot": "measured" if default.get("started") else "skip",
            "zero_network_default": "measured" if judged["verdict"] == "pass" else judged["verdict"],
            "localhost_at_default": "measured" if judged["verdict"] == "pass" else judged["verdict"],
            "capability_drop": "measured" if default.get("started") else "skip",
            "loopback_admin_before_capability_drop": "measured" if gap.get("started") else "skip",
            "public_mcp_sweep_guard": "cited",
            "allow_path_not_taken_for_default": "measured",
            "allow_path_shares_parent_netns": "measured" if allow.get("started") else "skip",
            "release_boundary": "cited",
            "system_alive": "not claimed",
        },
        "pin": PIN,
        "pin_changed": False,
        "require_pin_changed": False,
        "started_from": STARTED_FROM,
        "git_head_at_measurement": _git_head(root),
        "worktree_dirty_at_measurement": _worktree_dirty(root),
        "measurement_note": (
            "source_sha256 binds the containment sources in this worktree. "
            "git_head_at_measurement is HEAD when the command ran. "
            "The commit that adds this file is not a second measurement. "
            "The UTC stamps are this machine's clock, not receipt 3."
        ),
        "source_sha256": _file_hashes(root, _SOURCE_FILES),
        "unchanged_sha256": _file_hashes(root, _UNCHANGED_FILES),
        "live_trading": False,
        "orders_placed": False,
        "market_data_fetched": False,
        "release_boundary": "HOLD",
        "orange_badge": "unchanged",
        "cold_boot_command": "python -m aureon.containment.cold_boot",
        "cold_boot_argv_has_net": "--net" in default_argv,
        "cold_boot_argv": default_argv,
        "parent_net_ns": parent_net_ns,
        "child_net_ns": (default.get("probe") or {}).get("net_ns") if isinstance(default.get("probe"), dict) else None,
        "host_control": host,
        "default_child": _public_child(default),
        "gap_before_capability_drop": _public_child(gap),
        "allow_path": {
            "taken_for_default_boot": False,
            "entry": "aureon.containment.native.authorize_network_allow",
            "effect": "omits unshare --net and shares the parent network namespace",
            "environment_variable_cannot_select_it": True,
            "probe_connect_attempted": allow_probe.get("connect_attempted", None),
            "probe_net_ns_equals_parent": allow_same,
            "probe_started": bool(allow.get("started")),
            "grant_id": grant.grant_id,
            "audit": dict(grant.audit),
            "argv_omits_net": "--net" not in list(allow.get("argv") or []),
        },
        "gaps": [*_gap_notes(gap), *_static_gaps(default)],
        "holds_remaining": list(_HOLDS),
        "started_at": started,
        "finished_at": finished,
        "kernel": " ".join(os.uname()),
        "python": sys.version.split()[0],
    }
    return receipt


def _public_child(child: dict[str, Any]) -> dict[str, Any]:
    """Drop nothing functional; cap the stderr so the receipt stays a record."""

    probe = child.get("probe")
    return {
        "started": bool(child.get("started")),
        "returncode": child.get("returncode"),
        "error": child.get("error"),
        "deny_network": child.get("deny_network"),
        "drop_caps": child.get("drop_caps"),
        "grant_id": child.get("grant_id"),
        "child_env_names": child.get("child_env_names"),
        "wrapper": child.get("wrapper"),
        "probe": probe,
        "stderr": child.get("stderr") or "",
    }


def render_markdown(receipt: dict[str, Any]) -> str:
    """One page. Figures are copied from the receipt, not recomputed."""

    default = receipt.get("default_child") or {}
    probe = default.get("probe") or {}
    probes = probe.get("probes") or {}
    external = probes.get("tcp_1.1.1.1_443") or {}
    local = probes.get("tcp_127.0.0.1_9") or {}
    libc = probes.get("libc_connect_1.1.1.1_443") or {}
    udp = probes.get("udp_8.8.8.8_53") or {}
    ipv6 = probes.get("tcp6_2001:4860:4860::8888_53") or {}
    raw = probes.get("raw_icmp_create") or {}
    reloaded = probes.get("tcp_1.1.1.1_443_after_socket_reload") or {}
    host = receipt.get("host_control") or {}
    lines = [
        "# Native process containment — receipt 1",
        "",
        "Stage 7 only. This is a measured cold boot. It is not a claim that a live Aureon instance exists, and it is not a claim that the system is alive.",
        "",
        f"Verdict: **{receipt.get('verdict')}**. Allowed at default: **{receipt.get('allowed_at_default')}**.",
        f"Release boundary: **{receipt.get('release_boundary')}**. Orange badge: {receipt.get('orange_badge')}.",
        f"Public pin: `{receipt.get('pin')}` (changed: {receipt.get('pin_changed')}).",
        "Live trading: false. Orders placed: false. Market data fetched: false.",
        "",
        "## Cold boot",
        "",
        "```bash",
        str(receipt.get("cold_boot_command")),
        "```",
        "",
        f"Command included `unshare --net`: **{receipt.get('cold_boot_argv_has_net')}** (measured).",
        f"Parent net namespace `{receipt.get('parent_net_ns')}`, child `{receipt.get('child_net_ns')}` (measured).",
        "",
        "## Zero-network default",
        "",
        (
            f"Measurer control, outside the namespace: TCP {host.get('host')}:{host.get('port')} "
            f"ok={host.get('ok')} errno={host.get('errno')} error={host.get('error')} "
            f"bytes_read={host.get('bytes_read')} (measured). No application payload was read."
        ),
        (
            f"Contained TCP 1.1.1.1:443 ok={external.get('ok')} errno={external.get('errno')} "
            f"error={external.get('error')} (measured)."
        ),
        (
            f"Contained libc connect to 1.1.1.1:443 ok={libc.get('ok')} errno={libc.get('errno')} "
            f"error={libc.get('error')} (measured)."
        ),
        (
            f"Contained UDP 8.8.8.8:53 ok={udp.get('ok')} errno={udp.get('errno')} "
            f"error={udp.get('error')} (measured). Payload was one NUL byte, not a DNS query."
        ),
        (
            f"Contained TCP 2001:4860:4860::8888:53 ok={ipv6.get('ok')} errno={ipv6.get('errno')} "
            f"error={ipv6.get('error')} (measured)."
        ),
        (
            f"Contained TCP 1.1.1.1:443 after importlib.reload(socket) ok={reloaded.get('ok')} "
            f"errno={reloaded.get('errno')} error={reloaded.get('error')} (measured)."
        ),
        (
            f"Contained ICMP raw socket create ok={raw.get('ok')} errno={raw.get('errno')} "
            f"error={raw.get('error')} (measured). No datagram was sent."
        ),
        (
            f"Contained TCP 127.0.0.1:9 ok={local.get('ok')} errno={local.get('errno')} "
            f"error={local.get('error')} (measured). Default allow is `{receipt.get('allowed_at_default')}`."
        ),
        f"`/proc/net/dev` interfaces: {probe.get('interfaces_proc_net_dev')} (measured).",
        f"lo flags before admin: {probe.get('lo_before')} (measured).",
        f"Effective caps after exec: {(probe.get('caps') or {}).get('CapEff')} (measured).",
        "",
        "## What remains allowed",
        "",
        "At process start, with capabilities already dropped: none. Localhost is not up. There is no default route.",
        "The explicit allow path was not used for this cold boot. A separate probe passed a grant, did not connect, and "
        f"shared the parent net namespace: {((receipt.get('allow_path') or {}).get('probe_net_ns_equals_parent'))} (measured).",
        "",
        "## Gaps",
        "",
    ]
    for gap in receipt.get("gaps") or []:
        lines.append(f"- ({gap.get('tag')}) {gap.get('statement')}")
    lines.extend(
        [
            "",
            "## Still HOLD",
            "",
        ]
    )
    for item in receipt.get("holds_remaining") or []:
        lines.append(f"- Receipt {item.get('id')}: {item.get('item')} — {item.get('status')}")
    lines.extend(
        [
            "",
            f"Started from `{receipt.get('started_from')}`. Git HEAD at measurement: `{receipt.get('git_head_at_measurement')}`.",
            str(receipt.get("measurement_note")),
            "",
        ]
    )
    return "\n".join(lines)


def write_receipt(receipt: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    tmp_json = json_path.with_suffix(json_path.suffix + ".tmp")
    tmp_md = md_path.with_suffix(md_path.suffix + ".tmp")
    tmp_json.write_text(text, encoding="utf-8")
    tmp_md.write_text(render_markdown(receipt), encoding="utf-8")
    os.replace(tmp_json, json_path)
    os.replace(tmp_md, md_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cold-boot native containment receipt. Does not place orders.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="print the receipt JSON and do not write reports/measured",
    )
    parser.add_argument("--receipt-json", type=Path, default=None)
    parser.add_argument("--receipt-md", type=Path, default=None)
    args = parser.parse_args(argv)
    receipt = measure(repo_root())
    if args.no_write:
        sys.stdout.write(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    else:
        json_path = args.receipt_json or (repo_root() / "reports" / "measured" / "native_process_containment.json")
        md_path = args.receipt_md or (repo_root() / "reports" / "measured" / "native_process_containment.md")
        write_receipt(receipt, json_path, md_path)
        sys.stdout.write(
            f"{receipt['verdict']} allowed={receipt['allowed_at_default']} {json_path}\n"
        )
    return {"pass": 0, "skip": 2, "fail": 1}.get(str(receipt["verdict"]), 1)


if __name__ == "__main__":
    raise SystemExit(main())
