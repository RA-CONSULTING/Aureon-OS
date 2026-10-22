"""Fee-aware expectancy gate — Aureon radar (organism-controlled).

Gary's decree: before ANY order (shadow or live), the expected move must
exceed the round-trip cost of the trade with a safety margin. This module is
the single enforcement point for that decree.

GATE MATH (all rates are decimal fractions, e.g. 0.011 = 1.1% — the same
convention as VENUE_FEES / STOP_PCT in shadow_executor.py):

- round_trip_cost(venue) = 2 * VENUE_FEES[venue] + 2 * SLIPPAGE_PER_SIDE
  (taker fee paid on entry AND exit, plus 0.05% adverse slippage per side).
  VENUE_FEES is imported from shadow_executor — never duplicated here, so the
  fee table stays a single source of truth. Kraken's real round trip is
  ~0.9%+ (NOT the 0.2% flat fee the upstream compound-kelly trader assumed).

- expected_move_pct(confidence, stop_pct) = confidence * stop_pct.
  CONSERVATISM, deliberately: the engine's protective stop is -2% from entry
  and take-profit +3% (shadow_executor STOP_PCT / TAKE_PROFIT_PCT). A signal
  at confidence 0.55 with a 2% stop is only credited with expecting a
  >= 1.1% move — i.e. we assume the signal captures a confidence-scaled
  FRACTION of the stop distance, never the full TP distance and never more
  than the stop. Any signal that cannot clear costs under this pessimistic
  estimate has no business firing.

- check(...) requires expected_move >= max(MARGIN_SAFETY_MULTIPLIER * cost,
  capture_floor): she must expect 25% profit above round-trip costs AND, per
  the owner decree of 2026-09-06 (state/capture_floor.json), at least a 1.0%
  expected move. The floor is read at call time; a missing/corrupt file
  means the floor is absent and only the cost check applies (prior math).
  At the promotion threshold (conf 0.55, stop 2%): kraken refuses
  (1.10% < 1.25*0.90%), binance allows (1.10% > 1.25*0.20%), alpaca allows —
  but with the floor in force, conf 0.55 credits only 1.10% expected, and
  any venue refuses an expected move below 1.0%.

- kelly_fraction_size(...) is a careful port of the upstream Kelly criterion
  from aureon-os-upstream/aureon/trading/aureon_compound_kelly_trader.py
  (kelly_size). Its flat fee_pct = 0.002 assumption is removed by contract:
  win_pct / loss_pct must be NET percentages supplied by the caller, i.e.
  already adjusted by the venue's real round_trip_cost(venue). The upstream
  clamp (f* in [0.01, 1.0] before the fractional multiplier) is preserved.

The gate is pure math: no network, no side effects, no key material.
price/qty are accepted for reporting and future edge models; the current
conservative decision depends only on (venue, confidence).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

# unified_hub.py loads this file BY PATH via importlib with no package
# context, so the relative import fails there; the bare fallback needs our own
# directory on sys.path (same bootstrap pattern as shadow_binance/shadow_alpaca).
_MODULE_DIR = Path(__file__).resolve().parent
if str(_MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(_MODULE_DIR))

try:
    from .shadow_executor import VENUE_FEES
except ImportError:  # pragma: no cover - direct-script / path-loaded fallback
    from shadow_executor import VENUE_FEES

# Owner capture floor (Gary Leckey, 2026-09-06): minimum profit target per
# trade is 1.0% — see state/capture_floor.json and capture_floor.py. Read at
# call time; an absent/corrupt file means the floor is not in force.
try:
    from .capture_floor import load_capture_floor
except ImportError:  # pragma: no cover - direct-script / path-loaded fallback
    from capture_floor import load_capture_floor

# Adverse slippage per side — same value as shadow_executor.SLIPPAGE, restated
# here so the gate's cost model is self-contained (fee table stays imported).
SLIPPAGE_PER_SIDE = 0.0005     # 0.05% per side, taker realism
MARGIN_SAFETY_MULTIPLIER = 1.25  # require expected >= 1.25 * round-trip cost
DEFAULT_STOP_PCT = 0.02        # matches shadow_executor STOP_PCT magnitude
PROMOTION_CONFIDENCE = 0.55    # matches ShadowArm._PROMOTE_CONF fallback


def round_trip_cost(venue: str) -> float:
    """Entry+exit taker fees plus 0.05% slippage per side, as a fraction.

    Raises KeyError for an unknown venue — check() converts that into a
    fail-closed refused_unknown_venue verdict.
    """
    key = str(venue or "").strip().lower()
    if key not in VENUE_FEES:
        raise KeyError(f"unknown venue {venue!r} (known: {sorted(VENUE_FEES)})")
    return 2.0 * VENUE_FEES[key] + 2.0 * SLIPPAGE_PER_SIDE


def expected_move_pct(confidence: float, stop_pct: float = DEFAULT_STOP_PCT) -> float:
    """Conservative expected move as a decimal fraction: confidence * stop_pct.

    See module docstring for the conservatism rationale — a signal is only
    credited with a confidence-scaled fraction of its stop distance.
    """
    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        conf = 0.0
    try:
        stop = float(stop_pct)
    except (TypeError, ValueError):
        stop = DEFAULT_STOP_PCT
    if conf < 0.0:
        conf = 0.0
    return conf * stop


def _rate(value: Any) -> Optional[float]:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if v == v and abs(v) != float("inf") else None  # NaN/inf guard


def check(venue: str, symbol: Any, side: Any, qty: Any, price: Any,
          confidence: Any) -> Dict[str, Any]:
    """Fee-aware expectancy verdict for one proposed order. Never raises.

    Returns dict with:
      allowed            : bool
      reason             : "allow" | "refused_edge_below_cost" |
                           "refused_below_capture_floor" |
                           "refused_unknown_venue"
      expected_move_pct  : confidence * stop_pct (fraction)
      round_trip_cost_pct: 2*fee + 2*slippage (fraction); None if venue unknown
      margin_pct         : expected - cost (fraction); None if venue unknown

    Owner decree (2026-09-06): the expected move must ALSO clear the capture
    floor from state/capture_floor.json (default 1.0%) — the binding minimum
    is max(1.25 * round_trip_cost, floor). Floor refusals are reported as
    reason="refused_below_capture_floor" with a "below capture floor X%"
    detail so the watch can tell decree refusals from cost/bug refusals.
    A missing/corrupt floor file means the floor is absent (prior behavior).
    """
    key = str(venue or "").strip().lower()
    if key not in VENUE_FEES:
        return {
            "allowed": False,
            "reason": "refused_unknown_venue",
            "venue": key,
            "symbol": str(symbol),
            "expected_move_pct": None,
            "round_trip_cost_pct": None,
            "margin_pct": None,
        }
    conf = _rate(confidence)
    expected = expected_move_pct(conf if conf is not None else 0.0)
    cost = round_trip_cost(key)
    margin = expected - cost
    cost_required = MARGIN_SAFETY_MULTIPLIER * cost
    floor = load_capture_floor()          # None => decree absent, prior math
    required = max(cost_required, floor) if floor is not None else cost_required
    allowed = expected >= required
    if allowed:
        reason = "allow"
        detail = ""
    elif floor is not None and floor >= cost_required and expected < floor:
        reason = "refused_below_capture_floor"
        detail = (f"below capture floor {floor * 100:.1f}% "
                  f"(expected {expected * 100:.2f}% < floor {floor * 100:.2f}%)")
    else:
        reason = "refused_edge_below_cost"
        detail = ""
    return {
        "allowed": allowed,
        "reason": reason,
        "detail": detail,
        "venue": key,
        "symbol": str(symbol),
        "side": str(side),
        "price": _rate(price),
        "confidence": conf,
        "expected_move_pct": expected,
        "round_trip_cost_pct": cost,
        "margin_pct": margin,
        "margin_safety_multiplier": MARGIN_SAFETY_MULTIPLIER,
        "capture_floor_pct": floor,
        "required_move_pct": required,
    }


def kelly_fraction_size(win_prob: float, win_pct: float, loss_pct: float,
                        balance: float, fraction: float = 0.25) -> float:
    """Fractional Kelly position size in balance units.

    Careful port of CompoundKellyTrader.kelly_size from
    aureon-os-upstream/aureon/trading/aureon_compound_kelly_trader.py, with
    the flat fee_pct = 0.002 assumption removed: win_pct and loss_pct must be
    NET percentages (already adjusted by the venue's real round-trip cost —
    see round_trip_cost). Kelly: f* = (b*p - q) / b with b = win/loss, then the
    upstream clamp to [0.01, 1.0] and the fractional multiplier (default 25%
    Kelly). Returns 0.0 when no finite loss is defined (upstream would divide
    by zero).
    """
    p = float(win_prob)
    loss = abs(float(loss_pct))
    if loss <= 0.0:
        return 0.0
    b = float(win_pct) / loss
    q = 1.0 - p
    f_star = (b * p - q) / b
    f_star = max(0.01, min(f_star, 1.0))  # upstream clamp, preserved
    return float(balance) * f_star * float(fraction)


if __name__ == "__main__":
    # Unit-run: gate math at the promotion threshold and above.
    import json

    cases = [
        ("kraken", "XBTUSD", "buy", 0.001, None, 0.55),
        ("binance", "BTCUSDT", "buy", 0.001, None, 0.55),
        ("alpaca", "BTC/USD", "buy", 0.001, None, 0.60),
        ("kraken", "XBTUSD", "buy", 0.001, None, 0.90),
        ("capital", "EURUSD", "buy", 1, None, 0.99),
    ]
    for venue, symbol, side, qty, price, conf in cases:
        verdict = check(venue, symbol, side, qty, price, conf)
        print(json.dumps(verdict, sort_keys=True))
