"""Decide whether a launcher may start live mode.

Live mode starts only when both of these are true:

* the stage 11 go-live gate reports clear, and
* the operator set ``AUREON_OPERATOR_ALLOW_LIVE`` for this run.

The stage 11 gate is ``scripts/bootstrap/go_live_stage11_gate.py`` when that
file is in the checkout. It must print a JSON object with ``go_live_clear``
true and exit 0. When the file is absent, the ``go_live_clear`` field in
``reports/measured/go_live_receipt5_deployment.json`` is the gate. A missing
or false field is not clear. Setting the operator flag does not override a
gate that is not clear. This module does not set ``go_live_clear`` and does
not place an order.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path

OPERATOR_FLAG = "AUREON_OPERATOR_ALLOW_LIVE"
SESSION_ENV = "AUREON_OPERATOR_TEST_SESSION"
APPROVAL_REFERENCE = "Gary Leckey, 9 Nov 2026 18:47 GMT, in-room approval to test live and paper trading"
SESSION_OWNER = "Lrya"
PUBLIC_PIN = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
_TRUE = frozenset({"1", "true", "yes", "on"})
_STAGE11 = Path("scripts/bootstrap/go_live_stage11_gate.py")
_RECEIPT = Path("reports/measured/go_live_receipt5_deployment.json")
_SESSION_RECORD = Path("state/operator_test_session.json")
_SESSION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
LIQUIDATION_SCRIPTS = (
    "aureon/trading/emergency_sell_all.py",
    "aureon/trading/manual_sell.py",
    "aureon/trading/convert_to_usdt.py",
)


def repo_root() -> Path:
    """Checkout that contains this module."""

    return Path(__file__).resolve().parents[2]


def operator_flag_set(env: Mapping[str, str]) -> bool:
    """True when the operator set the flag to an explicit true value."""

    return str(env.get(OPERATOR_FLAG, "")).strip().lower() in _TRUE


def gate_reports_clear(root: Path) -> tuple[bool, str]:
    """Whether the stage 11 gate, or the recorded ``go_live_clear`` field, is clear."""

    script = Path(root) / _STAGE11
    if script.is_file():
        return _script_clear(script, Path(root))
    return _field_clear(Path(root))


def _script_clear(script: Path, root: Path) -> tuple[bool, str]:
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        payload = None
    if completed.returncode == 0 and isinstance(payload, dict) and payload.get("go_live_clear") is True:
        return True, "the stage 11 go-live gate reports clear"
    if isinstance(payload, dict) and payload.get("reason"):
        detail = str(payload["reason"])
    elif isinstance(payload, dict):
        detail = "go_live_clear is not true"
    else:
        detail = "no JSON report"
    return False, f"the stage 11 go-live gate does not report clear ({detail})"


def _field_clear(root: Path) -> tuple[bool, str]:
    path = root / _RECEIPT
    if not path.is_file():
        return (
            False,
            "the stage 11 go-live gate is not in this checkout and go_live_clear is not recorded",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False, "go_live_clear could not be read"
    if isinstance(payload, dict) and payload.get("go_live_clear") is True:
        return True, "go_live_clear is true"
    return False, "the stage 11 go-live gate is not in this checkout; go_live_clear is false"


def _parse_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _now(now: datetime | None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def session_stamp(session_id: str) -> str:
    """Stamp carried on every session log, order record, and receipt."""

    return f"operator_test_session={session_id}, go_live_clear=false"


def active_test_session(
    root: Path,
    env: Mapping[str, str],
    now: datetime | None = None,
) -> dict[str, str] | None:
    """Return the validated session, or None when the operator did not arm one.

    A missing, malformed, expired, or unapproved record is not a session.
    This reads the record. It does not write it, does not write receipt 5,
    and does not set ``go_live_clear``.
    """

    if str(env.get(SESSION_ENV, "")).strip().lower() not in _TRUE:
        return None
    path = Path(root) / _SESSION_RECORD
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("go_live_clear") is True:
        return None
    if "pin" in payload and payload.get("pin") != PUBLIC_PIN:
        return None
    approval = payload.get("approval_reference")
    if not isinstance(approval, str) or approval != APPROVAL_REFERENCE:
        return None
    if payload.get("owner") != SESSION_OWNER:
        return None
    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or _SESSION_ID.fullmatch(session_id) is None:
        return None
    start = _parse_time(payload.get("starts_at"))
    expires = _parse_time(payload.get("expires_at"))
    if start is None or expires is None or expires <= start:
        return None
    current = _now(now)
    if current < start or current >= expires:
        return None
    return {
        "approval_reference": approval,
        "owner": SESSION_OWNER,
        "session_id": session_id,
    }


def decide(root: Path, env: Mapping[str, str], now: datetime | None = None) -> tuple[str, str]:
    """Return ``live`` or ``guarded``, and the sentence a launcher prints.

    Without a valid operator test session, live still requires the stage 11
    gate to report clear and ``AUREON_OPERATOR_ALLOW_LIVE``. A valid session
    is a separate route. It does not set ``go_live_clear``.
    """

    session = active_test_session(root, env, now=now)
    if session is not None:
        stamp = session_stamp(session["session_id"])
        return (
            "live",
            "operator test session "
            f"{session['session_id']} is active. {stamp}. "
            "go_live_clear stays false. This is not go-live evidence.",
        )
    clear, gate_reason = gate_reports_clear(root)
    flagged = operator_flag_set(env)
    if clear and flagged:
        return "live", f"{gate_reason}; {OPERATOR_FLAG} is set"
    parts: list[str] = []
    if not clear:
        parts.append(gate_reason)
    if flagged:
        parts.append(f"setting {OPERATOR_FLAG} does not override the gate")
    else:
        parts.append(f"{OPERATOR_FLAG} is not set for this run")
    return "guarded", "; ".join(parts)


def launcher_risk_gate(reading: Mapping[str, object]) -> str:
    """Shared launcher risk gate. HOLD blocks the order.

    Guarded mode and an operator test session both call this function.
    EXECUTE is the only pass. Anything else, including a missing action, is HOLD.
    """

    action = str(reading.get("action") or reading.get("math_action") or "HOLD").strip().upper()
    if action == "EXECUTE":
        return "EXECUTE"
    return "HOLD"


def risk_gate_functions() -> tuple[object, ...]:
    """The gate functions the launcher order path invokes. Looked up on each call."""

    return (launcher_risk_gate,)


def apply_launcher_risk_gates(reading: Mapping[str, object]) -> tuple[list[str], list[str]]:
    """Call every launcher risk gate. The names are the functions that ran."""

    names: list[str] = []
    results: list[str] = []
    for gate in risk_gate_functions():
        names.append(gate.__name__)
        results.append(str(gate(reading)))
    return names, results


def evaluate_launcher_order(
    root: Path,
    env: Mapping[str, str],
    reading: Mapping[str, object],
    now: datetime | None = None,
) -> dict[str, object]:
    """Launcher order path. A session and guarded mode use the same risk gates.

    This logs the decision. It does not place an exchange order, does not write
    receipt 5, and does not set ``go_live_clear``.
    """

    mode, reason = decide(root, env, now=now)
    session = active_test_session(root, env, now=now)
    names, results = apply_launcher_risk_gates(reading)
    held = "HOLD" in results
    record: dict[str, object] = {
        "admitted": mode == "live" and not held,
        "blocked": mode != "live" or held,
        "gates_called": names,
        "go_live_clear": False,
        "mode": mode,
        "orders_placed": False,
        "reason": reason,
        "risk_gates": results,
    }
    if held:
        record["block_reason"] = "risk gate HOLD"
    if session is not None:
        record["operator_test_session"] = session["session_id"]
        record["stamp"] = session_stamp(session["session_id"])
        record["go_live_clear"] = False
        record["log"] = record["stamp"]
    return record


def accepts_go_live_evidence(record: Mapping[str, object]) -> bool:
    """Session output is never go-live evidence, even if a copy claims otherwise."""

    try:
        blob = json.dumps(record, default=str)
    except (TypeError, ValueError):
        blob = str(record)
    if "operator_test_session=" in blob or "operator_test_session" in record:
        return False
    return record.get("go_live_clear") is True


def main() -> int:
    """Print why, and exit 0 only when live mode may start."""

    root = repo_root()
    mode, reason = decide(root, os.environ)
    session = active_test_session(root, os.environ)
    if mode == "live":
        print(f"live mode allowed: {reason}")
        if session is not None:
            print(session_stamp(session["session_id"]))
            print("go_live_clear stays false. This session is not go-live evidence.")
        return 0
    print(f"refuses live mode: {reason}")
    print("Booting the guarded stack with AUREON_LIVE_TRADING=0 and guarded mode. No real orders.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
