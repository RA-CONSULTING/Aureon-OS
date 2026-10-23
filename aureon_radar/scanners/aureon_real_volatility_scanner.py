#!/usr/bin/env python3
"""
🌊 AUREON REAL VOLATILITY SCANNER 🌊
====================================
Ranks symbols by real, live-measured volatility using exchange/orderbook data.
NO simulated prices. Data comes from Yahoo Finance (free, public) and Capital.com.

Output per symbol:
  symbol, venue, volatility_score, directional_bias, confidence,
  recommended_size, expected_net_profit_after_fees, blockers

Wired into:
  - unified_hub.py via module-level scan(symbol, price) -> [-1, 1] signal
  - radar_probability_matrix.py via volatility factor
  - state/volatility_scan.json for downstream consumers

Gary Leckey | 2026-09-07 | Real data only
"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote
from urllib.request import Request, urlopen

# UTF-8 / baton link (non-fatal if missing)
try:
    from aureon.core.aureon_baton_link import link_system as _baton_link
    _baton_link(__name__)
except Exception:
    pass

RADAR_ROOT = Path(__file__).resolve().parent.parent
STATE_DIR = RADAR_ROOT / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = STATE_DIR / "volatility_scan.json"
JOURNAL_PATH = STATE_DIR / "volatility_scan.jsonl"

# Symbol universe the radar actually trades
WATCHLIST = [
    "EURUSD", "GBPUSD", "USDJPY",
    "US100",
    "GOLD", "SILVER", "OIL_CRUDE", "NATURALGAS",
    "BTCUSD", "ETHUSD",
    "AAPL", "TSLA", "NVDA",
]

# Yahoo Finance symbol map for historical bars
YAHOO_MAP = {
    "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X", "USDJPY": "USDJPY=X",
    "US100": "^NDX",
    "GOLD": "GC=F", "SILVER": "SI=F", "OIL_CRUDE": "CL=F", "NATURALGAS": "NG=F",
    "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD",
    "AAPL": "AAPL", "TSLA": "TSLA", "NVDA": "NVDA",
}

# Venue mapping
VENUE_MAP = {
    "EURUSD": "capital", "GBPUSD": "capital", "USDJPY": "capital",
    "US100": "capital",
    "GOLD": "capital", "SILVER": "capital", "OIL_CRUDE": "capital", "NATURALGAS": "capital",
    "BTCUSD": "binance", "ETHUSD": "binance",
    "AAPL": "alpaca", "TSLA": "alpaca", "NVDA": "alpaca",
}

# Round-trip cost estimates per venue (taker + spread slippage model)
VENUE_ROUND_TRIP_COST_PCT = {
    "capital": 0.0010,   # ~0.10% CFD spread
    "binance": 0.0010,   # 0.10% taker
    "alpaca": 0.0002,    # commission-free, small spread
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fetch_yahoo_ohlc(symbol: str, interval: str = "1h", range_: str = "5d") -> Optional[List[Tuple[float, float, float, float]]]:
    """Fetch real OHLC bars from Yahoo Finance. Returns list of (open, high, low, close)."""
    yahoo_sym = YAHOO_MAP.get(symbol)
    if not yahoo_sym:
        return None
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(yahoo_sym)}?interval={interval}&range={range_}"
    req = Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    try:
        with urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        result = data.get("chart", {}).get("result", [None])[0]
        if not result:
            return None
        timestamps = result.get("timestamp", [])
        ohlc = result.get("indicators", {}).get("quote", [{}])[0]
        opens = ohlc.get("open", [])
        highs = ohlc.get("high", [])
        lows = ohlc.get("low", [])
        closes = ohlc.get("close", [])
        bars = []
        for i in range(len(timestamps)):
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            if None in (o, h, l, c) or c <= 0:
                continue
            bars.append((float(o), float(h), float(l), float(c)))
        return bars
    except Exception:
        return None


def _true_ranges(bars: List[Tuple[float, float, float, float]]) -> List[float]:
    trs = []
    prev_close = None
    for o, h, l, c in bars:
        if prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = c
    return trs


def _atr(bars: List[Tuple[float, float, float, float]], period: int = 14) -> Optional[float]:
    if len(bars) < period + 1:
        return None
    trs = _true_ranges(bars)
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def _realized_volatility(bars: List[Tuple[float, float, float, float]]) -> Optional[float]:
    """Annualized realized volatility from close-to-close log returns."""
    if len(bars) < 10:
        return None
    closes = [c for _, _, _, c in bars]
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
    if len(returns) < 5:
        return None
    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / len(returns)
    # Annualize assuming hourly bars (252 trading days * 6.5 hours)
    return math.sqrt(var * 252 * 6.5)


def _directional_bias(bars: List[Tuple[float, float, float, float]]) -> str:
    if len(bars) < 5:
        return "NEUTRAL"
    closes = [c for _, _, _, c in bars]
    short = sum(closes[-5:]) / 5
    long = sum(closes[-20:]) / 20 if len(closes) >= 20 else sum(closes) / len(closes)
    if short > long * 1.005:
        return "LONG"
    if short < long * 0.995:
        return "SHORT"
    return "NEUTRAL"


@dataclass
class VolatilityScan:
    symbol: str
    venue: str
    price: float
    volatility_score: float  # 0..1 normalized
    directional_bias: str
    confidence: float
    recommended_size: float
    expected_net_profit_after_fees: float
    blockers: List[str] = field(default_factory=list)
    atr: Optional[float] = None
    realized_vol: Optional[float] = None
    data_source: str = "unknown"
    ts: str = field(default_factory=_utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RealVolatilityScanner:
    """Live, real-data volatility scanner."""

    def __init__(self, watchlist: Optional[List[str]] = None):
        self.watchlist = watchlist or WATCHLIST
        self._last_run: Optional[Dict[str, Any]] = None

    def _get_current_price(self, symbol: str) -> Optional[Tuple[float, str]]:
        """Best-effort live price."""
        try:
            sys_path = str(RADAR_ROOT)
            import sys
            if sys_path not in sys.path:
                sys.path.insert(0, sys_path)
            from aureon_price_feed import get_price
            price = get_price(symbol)
            if price and price > 0:
                return float(price), "aureon_price_feed"
        except Exception:
            pass
        return None

    def scan_symbol(self, symbol: str) -> VolatilityScan:
        blockers = []
        price_info = self._get_current_price(symbol)
        if not price_info:
            blockers.append("no live price")
            return VolatilityScan(
                symbol=symbol,
                venue=VENUE_MAP.get(symbol, "unknown"),
                price=0.0,
                volatility_score=0.0,
                directional_bias="NEUTRAL",
                confidence=0.0,
                recommended_size=0.0,
                expected_net_profit_after_fees=0.0,
                blockers=blockers,
                data_source="none",
            )
        price, source = price_info

        bars = _fetch_yahoo_ohlc(symbol)
        data_source = source
        if bars:
            data_source = f"yahoo+{source}"
        else:
            blockers.append("no historical bars from yahoo")

        atr = _atr(bars) if bars else None
        realized = _realized_volatility(bars) if bars else None

        if atr is None and realized is None:
            blockers.append("insufficient volatility data")
            vol_score = 0.0
        else:
            # Normalize: target ~15% annualized = 0.5 score
            vol_measure = realized if realized is not None else (atr / price * math.sqrt(252 * 6.5) if price > 0 else 0.0)
            vol_score = min(1.0, vol_measure / 0.30)  # 30% annualized -> score 1.0

        bias = _directional_bias(bars) if bars else "NEUTRAL"

        # Confidence is driven by data quality + volatility magnitude
        confidence = 0.5 + 0.5 * vol_score
        if not bars:
            confidence *= 0.3

        # Sizing: tiny-account safe. Use 50% of a notional £75 reference equity,
        # scaled DOWN by volatility so choppy symbols get smaller size.
        reference_equity = float(os.environ.get("VOL_SCAN_REFERENCE_EQUITY", "75"))
        exposure = reference_equity * 0.50 * (1.0 - 0.5 * vol_score)
        if price > 0:
            recommended_size = max(0.01, round(exposure / price, 2))
        else:
            recommended_size = 0.0

        # Venue minimum size floors
        venue = VENUE_MAP.get(symbol, "capital")
        min_size = {"capital": 1.0, "binance": 0.001, "alpaca": 1.0}.get(venue, 0.01)
        recommended_size = max(recommended_size, min_size)

        # Net profit estimate: assume we capture 1x ATR, minus round-trip cost
        cost_pct = VENUE_ROUND_TRIP_COST_PCT.get(venue, 0.001)
        gross_pct = (atr / price) if (atr and price > 0) else 0.001
        net_pct = max(0.0, gross_pct - cost_pct)
        notional = recommended_size * price
        expected_net = notional * net_pct

        # Block if expected net is below 1p/1c after fees
        if expected_net < 0.01:
            blockers.append("expected net profit below 1p/1c after fees")

        return VolatilityScan(
            symbol=symbol,
            venue=venue,
            price=price,
            volatility_score=round(vol_score, 4),
            directional_bias=bias,
            confidence=round(confidence, 4),
            recommended_size=round(recommended_size, 4),
            expected_net_profit_after_fees=round(expected_net, 4),
            blockers=blockers,
            atr=round(atr, 6) if atr else None,
            realized_vol=round(realized, 6) if realized else None,
            data_source=data_source,
        )

    def scan_all(self) -> List[VolatilityScan]:
        results = []
        for symbol in self.watchlist:
            results.append(self.scan_symbol(symbol))
        # Rank by volatility score descending
        results.sort(key=lambda x: x.volatility_score, reverse=True)
        self._last_run = {
            "ts": _utc_now_iso(),
            "symbols": [r.to_dict() for r in results],
        }
        try:
            OUT_PATH.write_text(json.dumps(self._last_run, indent=2))
            with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(self._last_run) + "\n")
        except Exception:
            pass
        return results

    def scan(self, symbol: str, price: Optional[float] = None) -> Optional[float]:
        """Hub-compatible probe: returns a directional score in [-1, 1]."""
        result = self.scan_symbol(symbol)
        if result.blockers and result.volatility_score == 0:
            return None
        magnitude = result.volatility_score * result.confidence
        if result.directional_bias == "LONG":
            return magnitude
        if result.directional_bias == "SHORT":
            return -magnitude
        # High vol but neutral bias → small positive (volatility opportunity)
        return magnitude * 0.2


# Module-level singleton for hub probing
_scanner = RealVolatilityScanner()


def scan(symbol: str, price: Optional[float] = None) -> Optional[float]:
    """Module-level scan function for unified_hub.py probing."""
    return _scanner.scan(symbol, price)


def scan_all(watchlist: Optional[List[str]] = None) -> List[VolatilityScan]:
    """Full scan returning structured volatility records."""
    scanner = RealVolatilityScanner(watchlist=watchlist)
    return scanner.scan_all()


if __name__ == "__main__":
    results = scan_all()
    print(json.dumps([r.to_dict() for r in results], indent=2))
