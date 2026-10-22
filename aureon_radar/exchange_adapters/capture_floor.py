"""Owner capture floor — Aureon radar (organism-controlled).

Decree record: aureon_radar/state/capture_floor.json
    {"min_gain_pct": 1.0, "ts", "source": "owner decree 2026-09-06 (Gary
     Leckey) — capture 1% gain floor per trade"}

Owner decree (Gary Leckey, 2026-09-06): the MINIMUM profit target per trade
is 1.0% — trades with an expected gain below 1% are refused, and positions
take profit at >= 1% gain. This is a FLOOR ON AMBITION, not a weakening of
safety: the expectancy gate's fee math (expected >= 1.25x round-trip cost),
the capital gate, and conscience all stay exactly as they were. The floor
only ever RAISES a target or refuses a trade; it never lowers anything.

FAIL-CLOSED CONTRACT: the decree file is read at CALL TIME. A missing,
unreadable, or corrupt file means the floor is ABSENT — every caller keeps
its prior behavior exactly. Degraded state is logged ONCE per process
(not per call) so a broken file cannot spam the watch.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

RADAR_ROOT = Path(__file__).resolve().parents[1]
FLOOR_PATH = RADAR_ROOT / "state" / "capture_floor.json"

_warned = False


def _warn_once(message: str) -> None:
    global _warned
    if not _warned:
        _warned = True
        logger.warning("capture floor: %s", message)


def load_capture_floor(path: Optional[Path] = None) -> Optional[float]:
    """Floor as a decimal fraction (0.01 == 1.0%), read at call time.

    Returns None when the decree file is missing/corrupt/invalid — the
    floor is then absent and callers must behave as before the decree.
    Never raises.
    """
    p = Path(path) if path is not None else FLOOR_PATH
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        value = float(raw["min_gain_pct"])
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"min_gain_pct must be a positive number, got {value!r}")
    except Exception as exc:
        _warn_once(f"decree file {p} missing/corrupt ({exc}) — floor absent, "
                   f"prior behavior preserved")
        return None
    return value / 100.0


def apply_floor_to_target(direction: str, entry_price: float,
                          target_price: float,
                          floor: Optional[float] = None) -> float:
    """Clamp a take-profit target UPWARD to the capture floor.

    LONG/BUY:  target >= entry * (1 + floor)
    SHORT/SELL: target <= entry * (1 - floor)

    `floor` is a fraction (0.01 == 1.0%); None (or an absent decree file)
    returns the target unchanged. Upward-only: a target already beyond the
    floor is never pulled back.
    """
    if floor is None:
        return target_price
    try:
        entry = float(entry_price)
        target = float(target_price)
    except (TypeError, ValueError):
        return target_price
    if entry <= 0.0:
        return target_price
    side = str(direction or "").strip().upper()
    if side in ("LONG", "BUY"):
        return max(target, entry * (1.0 + floor))
    if side in ("SHORT", "SELL"):
        return min(target, entry * (1.0 - floor))
    return target_price


def apply_floor_to_tp_pct(computed_tp_pct: float,
                          floor: Optional[float] = None) -> float:
    """Clamp a take-profit PERCENT (fraction) upward to the floor.

    None floor (absent decree) returns the computed value unchanged.
    """
    if floor is None:
        return computed_tp_pct
    try:
        computed = float(computed_tp_pct)
    except (TypeError, ValueError):
        return computed_tp_pct
    return max(computed, floor)
