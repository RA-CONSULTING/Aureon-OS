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
This module does not write ``state/autonomy_audit.jsonl``. A self-patch whose
tests fail is left in place. Credential material is read from ``.env`` or the
OS keychain and is never written into the repo or into a log.
"""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path

MODE_ENV = "AUREON_AUTONOMY_MODE"
MODE_RELATIVE = Path("state/autonomy_mode.json")
RUNTIME_RELATIVE = Path("state/autonomy_runtime.json")

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


def audit_event(event: str, repo_root: Path | None = None, **fields: object) -> None:
    """Retired. This does not create an autonomy audit log."""

    del event, repo_root, fields


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
    """Retired. This does not place an order and does not write a log."""

    del operation, exchange, symbol, side, status, decision, reason, repo_root


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
    does not place an order. Guarded mode refuses.
    """

    root = Path(repo_root)
    if autonomy_mode(root) != "full":
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
    return {
        "ok": True,
        "reason": "runtime_authority_set",
        "armed": bool(live_trading),
        "may_act": bool(may_act),
        "order_placed": False,
        "env_written": False,
        "runtime_path": path.as_posix(),
    }
