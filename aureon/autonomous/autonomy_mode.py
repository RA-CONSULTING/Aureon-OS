"""Autonomy mode for a local Aureon checkout.

The public default is ``full``. An unset variable and a missing state file
both mean full. ``AUREON_AUTONOMY_MODE=guarded``, or ``state/autonomy_mode.json``
with ``{"mode": "guarded"}``, is the opt-in denylist. An unknown explicit
environment value stays guarded.

Full mode lets self-repair and the self-coder edit any path, including
live-trading flags, the HOLD/RELEASE gate, ``may_act``, position sizing, and
trading modules. Auto-approve is on unless the operator sets
``AUREON_CODE_AUTO_APPROVE=0``. A self-generated patch commits on the current
branch after its own tests pass. Nothing is pushed.

Trading follows the operator's own exchange keys. This module only reports
whether a key group is present. It does not read a value into a log and it
does not place an order.

``AUREON_SELF_REPAIR_KILL`` and ``state/SELF_REPAIR_KILL`` do not stop a run.
``state/autonomy_audit.jsonl`` is append-only. Self-changes and order attempts
are recorded there, secret values are redacted, and the same records are
published on the circulation thought bus. A self-patch whose tests fail is
left in place. Credential material is read from ``.env`` or the OS keychain
and is never written into the repo or into a log.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

MODE_ENV = "AUREON_AUTONOMY_MODE"
MODE_RELATIVE = Path("state/autonomy_mode.json")
RUNTIME_RELATIVE = Path("state/autonomy_runtime.json")
AUDIT_RELATIVE = Path("state/autonomy_audit.jsonl")
AUDIT_ENV = "AUREON_AUTONOMY_AUDIT_PATH"
_CIRCULATION = "organism.circulation"

_SECRET_KEY = re.compile(
    r"key|token|secret|password|credential|passwd|private|cookie|authorization|auth",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"(?i)(?:\b(?:api[_-]?key|api[_-]?secret|secret|password|authorization|access_token)\b\s*[:=]\s*)\S+"
    r"|(?:sk-[A-Za-z0-9_\-]{8,}|ghp_[A-Za-z0-9]{8,}|github_pat_\S+|AKIA[0-9A-Z]{8,}|Bearer\s+\S+)"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
)

# Presence only. Values are never logged. Same groups as the master launcher.
_EXCHANGE_GROUPS = (
    ("KRAKEN_API_KEY", "KRAKEN_API_SECRET"),
    ("BINANCE_API_KEY", "BINANCE_API_SECRET"),
    ("ALPACA_API_KEY", "ALPACA_SECRET_KEY"),
    ("CAPITAL_API_KEY", "CAPITAL_IDENTIFIER", "CAPITAL_PASSWORD"),
)


def _roots(repo_root: Path | None) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    candidates = []
    if repo_root is not None:
        candidates.append(Path(repo_root))
    candidates.append(Path.cwd())
    candidates.append(Path(__file__).resolve().parents[2])
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        found.append(resolved)
    return found


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def kill_switch_engaged(repo_root: Path | None = None) -> bool:
    """Retired. The kill variable and the kill file do not stop a run."""

    del repo_root
    return False


def autonomy_mode(repo_root: Path | None = None) -> str:
    """Return ``full`` or ``guarded``.

    An explicit environment value wins. ``full`` is full. Any other non-empty
    value, including ``guarded``, is guarded. With the variable unset, only
    ``state/autonomy_mode.json`` saying ``{"mode": "guarded"}`` closes the
    denylist. A missing, unreadable, or other file is full.
    """

    raw = os.environ.get(MODE_ENV, "").strip().lower()
    if raw == "full":
        return "full"
    if raw:
        return "guarded"
    for root in _roots(repo_root):
        path = root / MODE_RELATIVE
        if not path.is_file():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeError):
            return "full"
        mode = str(payload.get("mode", "")).strip().lower() if isinstance(payload, dict) else ""
        return "guarded" if mode == "guarded" else "full"
    return "full"


def _dotenv_values(path: Path) -> dict[str, str]:
    """Non-empty assignments. The caller must not log the values."""

    found: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return found
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value:
            found[key] = value
    return found


def exchange_keys_present(
    repo_root: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> bool:
    """True when one exchange key group is complete.

    A passed mapping is the only process environment consulted, so a unit
    test can pass a dict that does not see the host. Values are not returned
    and are not written to a log.
    """

    present: dict[str, str] = {}
    source = os.environ if environ is None else environ
    for key, value in source.items():
        if value:
            present[str(key)] = str(value)
    roots: list[Path] = []
    if repo_root is not None:
        roots.append(Path(repo_root))
    elif environ is None:
        roots.append(Path.cwd())
    for root in roots:
        present.update(_dotenv_values(root / ".env"))
        present.update(_dotenv_values(root / "aureon_radar" / ".env"))
    return any(all(present.get(key) for key in group) for group in _EXCHANGE_GROUPS)


def guardrails_open(repo_root: Path | None = None) -> bool:
    """True in full mode. Explicit guarded mode is the opt-in denylist."""

    return autonomy_mode(repo_root) == "full"


def _redact_text(value: str) -> str:
    return _SECRET_VALUE.sub("[redacted]", value)


def _redact(value: object) -> object:
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, dict):
        cleaned: dict[str, object] = {}
        for key, item in value.items():
            if _SECRET_KEY.search(str(key)):
                continue
            cleaned[str(key)] = _redact(item)
        return cleaned
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def audit_log_path(repo_root: Path | None = None) -> Path:
    """Where the append-only audit is written.

    An explicit repo root wins, so a test can keep the log in its tmp dir.
    Otherwise ``AUREON_AUTONOMY_AUDIT_PATH`` redirects the log, and the
    default is ``state/autonomy_audit.jsonl`` under the cwd.
    """

    if repo_root is not None:
        return Path(repo_root) / AUDIT_RELATIVE
    override = os.environ.get(AUDIT_ENV, "").strip()
    if override:
        return Path(override)
    return Path.cwd() / AUDIT_RELATIVE


def _publish_audit(record: dict[str, object]) -> None:
    """Hand the redacted record to the circulation bus. A quiet bus changes nothing."""

    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        payload = dict(record)
        payload["kind"] = "autonomy_audit"
        get_thought_bus().publish(
            Thought(source="autonomy_audit", topic=_CIRCULATION, payload=payload)
        )
    except Exception:
        return


def audit_event(event: str, repo_root: Path | None = None, **fields: object) -> None:
    """Append one redacted record and publish it on the circulation bus.

    Earlier lines are never rewritten. Secret-named fields are dropped and
    secret-looking text becomes ``[redacted]``. A missing bus does not change
    the caller. This does not place an order.
    """

    path = audit_log_path(repo_root)
    record: dict[str, object] = {"ts": _utc(), "event": str(event)}
    redacted = _redact(fields)
    if isinstance(redacted, dict):
        record.update(redacted)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    except OSError:
        return
    _publish_audit(record)


def note_order_attempt(
    *,
    operation: str,
    exchange: str,
    symbol: str = "",
    side: str = "",
    result: object = None,
    status: str = "",
    decision: str = "",
    reason: str = "",
) -> None:
    """Record an order attempt and publish it. This does not place or retry the order."""

    if isinstance(result, dict):
        symbol = symbol or str(result.get("symbol") or "")
        side = side or str(result.get("side") or result.get("direction") or "")
        status = status or str(result.get("status") or "")
        decision = decision or str(result.get("decision") or "")
        reason = reason or str(result.get("reason") or result.get("error") or "")
    try:
        record_order(
            operation=operation,
            exchange=exchange,
            symbol=str(symbol or ""),
            side=str(side or ""),
            status=str(status or ""),
            decision=str(decision or ""),
            reason=str(reason or ""),
        )
    except Exception:
        return


def record_order(
    *,
    operation: str,
    exchange: str = "",
    symbol: str = "",
    side: str = "",
    status: str = "",
    decision: str = "",
    reason: str = "",
    repo_root: Path | None = None,
) -> None:
    """Append an order attempt. This does not place the order."""

    audit_event(
        "order",
        repo_root,
        operation=operation,
        exchange=exchange,
        symbol=symbol,
        side=side,
        status=status,
        decision=decision,
        reason=reason,
        order_placed_by_audit=False,
    )


def runtime_authority(repo_root: Path | None = None) -> dict[str, object]:
    """Live flag and may_act for the current mode.

    Guarded mode is disarmed even if a runtime file claims otherwise. Full
    mode with no runtime file may act, and live trading follows exchange keys.
    An explicit ``state/autonomy_runtime.json`` is honored when it is present.
    """

    mode = autonomy_mode(repo_root)
    disarmed = {
        "mode": mode,
        "live_trading": False,
        "may_act": False,
        "kill_switch": False,
    }
    if not guardrails_open(repo_root):
        return disarmed
    path = None
    for root in _roots(repo_root):
        candidate = root / RUNTIME_RELATIVE
        if candidate.is_file():
            path = candidate
            break
    if path is None:
        return {
            "mode": "full",
            "live_trading": exchange_keys_present(repo_root),
            "may_act": True,
            "kill_switch": False,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {
            "mode": "full",
            "live_trading": exchange_keys_present(repo_root),
            "may_act": True,
            "kill_switch": False,
        }
    if not isinstance(payload, dict):
        return {
            "mode": "full",
            "live_trading": exchange_keys_present(repo_root),
            "may_act": True,
            "kill_switch": False,
        }
    return {
        "mode": "full",
        "live_trading": payload.get("live_trading") is True,
        "may_act": payload.get("may_act") is True,
        "kill_switch": False,
    }


def set_runtime_authority(
    repo_root: Path,
    *,
    live_trading: bool,
    may_act: bool,
) -> dict[str, object]:
    """Let the system set its own live flag and may_act.

    Full mode only. Writes the untracked runtime file and the process
    environment. Does not write ``.env``, does not write a credential, and
    does not place an order. Guarded mode refuses. The refusal and the set
    are both appended to the autonomy audit.
    """

    root = Path(repo_root)
    if autonomy_mode(root) != "full":
        audit_event("runtime_authority_refused", root, reason="autonomy_guarded", order_placed=False)
        return {"ok": False, "reason": "autonomy_guarded", "armed": False, "may_act": False, "order_placed": False}
    payload = {
        "mode": "full",
        "live_trading": bool(live_trading),
        "may_act": bool(may_act),
        "order_placed": False,
    }
    path = root / RUNTIME_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.environ["AUREON_LIVE_TRADING"] = "1" if live_trading else "0"
    os.environ["AUREON_MAY_ACT"] = "1" if may_act else "0"
    audit_event(
        "runtime_authority_set",
        root,
        live_trading=bool(live_trading),
        may_act=bool(may_act),
        order_placed=False,
    )
    return {
        "ok": True,
        "reason": "runtime_authority_set",
        "armed": bool(live_trading),
        "may_act": bool(may_act),
        "order_placed": False,
        "env_written": False,
        "runtime_path": path.as_posix(),
    }
