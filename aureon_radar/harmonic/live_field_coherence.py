"""Live field coherence — the organism's own REAL telemetry (harmonic layer).

Harmonic real-signal module for the hub's SignalFusionEngine. This does NOT
read market data: it reads the organism's own field instruments and converts
them into a bounded [-1, 1] coherence score. Follows the binding conventions
of scanners/live_market_momentum_scanner.py:

  * module-level ``scan(symbol, price)`` — the hub probes this name.
  * returns dict {"direction", "confidence"} or None. Low conviction ->
    None (omitted from fusion). Never force a score.
  * hub symbols mapped via SYMBOL_MAP; anything unmapped returns None.
    The score is symbol-agnostic: the field reading is the same for any
    mapped symbol.
  * REAL values only, never fabricated. Stale or malformed state -> None.

Inputs (all real, file-backed):
  * workspace/schumann_state.json          (mtime < 300s, real_data == true)
      - frequency_hz: Schumann fundamental
      - activity_index: 0..100-ish scalar from the field source
  * aureon_fusion/state/hnc_core_state.json (HNC core coherence)
      - coherence_gamma: organism coherence Γ in [0, 1]
      - inputs.*: any ``*_stale`` flag set true -> None (honest abstain:
        the organism itself declares its inputs stale, so the field
        reading is not trustworthy enough to trade on)

Score mapping (documented design decision):
  dev      = frequency_hz - 7.83            (signed deviation, Hz)
  sign     = +1 if dev >= 0 else -1         (elevated fundamental = excited/
                                            expanding field -> LONG bias;
                                            suppressed = contracted/defensive
                                            field -> SHORT bias)
  mag_base = min(1.0, |dev| / 1.0)          (1 Hz full-scale saturation)
  gamma_w  = 0.4 + 0.6 * clamp(gamma, 0, 1) (HNC coherence modulates gain:
                                            a coherent organism trusts the
                                            field reading, an incoherent one
                                            discounts it toward 40%)
  act_w    = clamp(activity_index / 50, 0, 1) (a quiet baseline field
                                            carries no directional
                                            information -> shrinks to 0)
  score    = sign * mag_base * gamma_w * act_w, clamped to [-1, 1]
  None if |score| < 0.35                    (flat field = honest abstain)

With the fundamental sitting exactly at 7.83 Hz (the common real case),
dev == 0 -> score 0 -> None. That is correct doctrine, not a bug.
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

# ── symbol mapping (same hub-symbol convention as the reference scanner) ────
SYMBOL_MAP = {
    "BTCUSD": "BTCUSD", "BTCUSDT": "BTCUSD", "BTC": "BTCUSD", "XBTUSD": "BTCUSD",
    "ETHUSD": "ETHUSD", "ETHUSDT": "ETHUSD", "ETH": "ETHUSD",
}

_WORKSPACE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))  # workspace root (aureon_radar -> workspace)
_SCHUMANN_PATH = os.path.join(_WORKSPACE, "schumann_state.json")
_HNC_PATH = os.path.join(_WORKSPACE, "aureon_fusion", "state", "hnc_core_state.json")
_SCHUMANN_MAX_AGE = 300.0
_HNC_MAX_AGE = 300.0
_FLOOR = 0.35


def _read_json(path: str, max_age: float) -> Optional[dict]:
    try:
        if time.time() - os.path.getmtime(path) > max_age:
            return None
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else None
    except Exception:
        return None


def _field_reading() -> Optional[dict]:
    sch = _read_json(_SCHUMANN_PATH, _SCHUMANN_MAX_AGE)
    if not sch or sch.get("real_data") is not True:
        return None
    hnc = _read_json(_HNC_PATH, _HNC_MAX_AGE)
    if not hnc:
        return None
    # any real input_stale flag -> the organism itself says its inputs are
    # stale; abstain rather than trade on an untrustworthy field
    inputs = hnc.get("inputs")
    if isinstance(inputs, dict):
        for k, v in inputs.items():
            if k.endswith("_stale") and v is True:
                return None
    try:
        return {
            "hz": float(sch["frequency_hz"]),
            "activity": float(sch.get("activity_index", 0.0)),
            "gamma": float(hnc.get("coherence_gamma", 0.0)),
        }
    except (KeyError, TypeError, ValueError):
        return None


def scan(symbol: str, price: float = 0.0):
    """Hub probe entry — returns dict(direction, confidence) or None."""
    if SYMBOL_MAP.get(str(symbol).upper()) is None:
        return None
    r = _field_reading()
    if r is None:
        return None

    dev = r["hz"] - 7.83
    sign = 1.0 if dev >= 0 else -1.0
    mag = min(1.0, abs(dev) / 1.0)
    gamma_w = 0.4 + 0.6 * max(0.0, min(1.0, r["gamma"]))
    act_w = max(0.0, min(1.0, r["activity"] / 50.0))
    score = max(-1.0, min(1.0, sign * mag * gamma_w * act_w))
    conf = abs(score)
    if conf < _FLOOR:
        return None  # quiet/flat field — omit, don't dilute fusion
    return {
        "direction": "LONG" if score > 0 else "SHORT",
        "confidence": round(conf, 4),
        "source": "schumann+hnc_gamma_telemetry",
    }


if __name__ == "__main__":
    # live self-test: show the real Hz / gamma / activity we read
    for s in ("BTCUSD", "ETHUSD", "EURUSD"):
        print(f"{s}: -> {scan(s)}")
    r = _field_reading()
    if r:
        dev = r["hz"] - 7.83
        raw = (1.0 if dev >= 0 else -1.0) * min(1.0, abs(dev)) \
            * (0.4 + 0.6 * max(0.0, min(1.0, r["gamma"]))) \
            * max(0.0, min(1.0, r["activity"] / 50.0))
        print(f"raw inputs: schumann_hz={r['hz']} dev={dev:+.4f} "
              f"gamma={r['gamma']:.4f} activity={r['activity']} "
              f"-> unclipped score {raw:+.4f}")
    else:
        print("raw inputs: _field_reading() -> None "
              "(stale schumann, stale HNC inputs, or stale-flag abstain)")
