"""Live market momentum scanner — REAL market data via PriceCache freshness gate.

Reference implementation for the real-signal layer. Every other real-signal
module must follow these binding conventions:

  * expose a module-level ``scan(symbol, price)`` — the hub probes this name
    first and coerces the result (see SignalFusionEngine._coerce_score).
  * return either a float in [-1, 1] or a dict
    {"direction": "LONG"|"SHORT"|"NEUTRAL", "confidence": 0..1}.
    A NEUTRAL/low-conviction result returns None upstream and is omitted
    from fusion — never force a direction to fake participation.
  * map hub symbols via SYMBOL_MAP; anything unmapped returns None.
  * REAL data only. All reads route through ``exchange_adapters.price_cache``
    so freshness is enforced centrally. If the cache reports
    ``trade_allowed=False`` (stale, simulated, error, or rate-limited) this
    scanner returns None instead of fabricating a signal.
  * hard timeout <=5s per call. A scanner must never stall the hub's 5s
    extraction deadline.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Optional

# Allow running this scanner directly as a module.
_RADAR_ROOT = Path(__file__).resolve().parents[1]
if str(_RADAR_ROOT) not in sys.path:
    sys.path.insert(0, str(_RADAR_ROOT))

from exchange_adapters import price_cache

# ── symbol mapping (hub symbol -> Binance public symbol) ────────────────────
SYMBOL_MAP = {
    "BTCUSD": "BTCUSDT", "BTCUSDT": "BTCUSDT", "BTC": "BTCUSDT", "XBTUSD": "BTCUSDT",
    "ETHUSD": "ETHUSDT", "ETHUSDT": "ETHUSDT", "ETH": "ETHUSDT",
}

_TIMEOUT = 4.0


def _ema(values, period: int) -> float:
    if len(values) < period:
        return values[-1] if values else 0.0
    k = 2.0 / (period + 1)
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def scan(symbol: str, price: float = 0.0):
    """Hub probe entry — returns dict(direction, confidence) or None."""
    bsym = SYMBOL_MAP.get(str(symbol).upper())
    if bsym is None:
        return None

    # Fetch the extended summary through the freshness-gated cache.
    summary = price_cache.get_summary(bsym, source="binance")

    # Fail closed if the data is not trade-grade fresh.
    if not summary.get("trade_allowed"):
        return None
    if not summary.get("closes"):
        return None

    d = summary

    # 1) 24h momentum, saturating: ±3% -> ±0.55
    m_mom = math.tanh(d["change_pct"] / 3.0) * 0.55

    # 2) 15m trend: EMA12 vs EMA36 cross, bounded ±0.30
    ema_fast = _ema(d["closes"], 12)
    ema_slow = _ema(d["closes"], 36)
    denom = ema_slow if ema_slow else 1.0
    cross = (ema_fast - ema_slow) / denom
    m_trend = max(-0.30, min(0.30, cross * 25.0))

    # 3) volume confirmation: recent 8-bar vol vs 48-bar avg, bounded ±0.15
    if d["vols"] and len(d["vols"]) >= 16:
        recent = sum(d["vols"][-8:]) / 8.0
        base = sum(d["vols"]) / len(d["vols"]) or 1.0
        vr = recent / base
        sign = 1.0 if (m_mom + m_trend) >= 0 else -1.0
        m_vol = sign * min(0.15, max(0.0, (vr - 1.0) * 0.15))
    else:
        m_vol = 0.0

    score = max(-1.0, min(1.0, m_mom + m_trend + m_vol))
    conf = abs(score)
    if conf < 0.35:
        return None  # no real conviction — omit, don't dilute fusion
    return {
        "direction": "LONG" if score > 0 else "SHORT",
        "confidence": round(conf, 4),
        "source": "binance_public_24h+15m",
        "data_source": "price_cache",
        "fresh": bool(summary.get("fresh")),
        "source_kind": summary.get("source_kind"),
        "trade_allowed": True,
    }


if __name__ == "__main__":
    for s in ("BTCUSD", "ETHUSD", "EURUSD"):
        print(s, scan(s))
