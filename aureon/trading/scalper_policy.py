"""Pure, side-effect-free target selection for Queen-directed scalper mode."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any


def resolve_scalper_targets(
    queen_signal: Any,
    learned_recommendation: Mapping[str, Any] | None,
) -> tuple[Any, Any, bool]:
    """Return TP, SL and activation without creating runtime or provider state."""
    learned = learned_recommendation or {}
    take_profit = learned.get("suggested_take_profit")
    stop_loss = learned.get("suggested_stop_loss")
    if isinstance(queen_signal, bool):
        return take_profit, stop_loss, False
    try:
        signal = float(queen_signal)
    except (TypeError, ValueError):
        return take_profit, stop_loss, False
    if not math.isfinite(signal) or signal <= 0.8:
        return take_profit, stop_loss, False
    return 0.005, 0.002, True


__all__ = ["resolve_scalper_targets"]
