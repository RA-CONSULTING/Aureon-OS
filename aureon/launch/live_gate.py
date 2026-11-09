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
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

OPERATOR_FLAG = "AUREON_OPERATOR_ALLOW_LIVE"
_TRUE = frozenset({"1", "true", "yes", "on"})
_STAGE11 = Path("scripts/bootstrap/go_live_stage11_gate.py")
_RECEIPT = Path("reports/measured/go_live_receipt5_deployment.json")


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


def decide(root: Path, env: Mapping[str, str]) -> tuple[str, str]:
    """Return ``live`` or ``guarded``, and the sentence a launcher prints."""

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


def main() -> int:
    """Print why, and exit 0 only when live mode may start."""

    mode, reason = decide(repo_root(), os.environ)
    if mode == "live":
        print(f"live mode allowed: {reason}")
        return 0
    print(f"refuses live mode: {reason}")
    print("Booting the guarded stack with AUREON_LIVE_TRADING=0 and guarded mode. " "No real orders.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
