#!/usr/bin/env python3
"""
Aureon High-Volatility Scanner — real-data ranking engine.

Ranks symbols by live volatility from real exchange/orderbook prices,
incorporates HNC/auris/harmonic inputs, and produces a target report.

Output keys: symbol, venue, volatility_score, directional_bias, confidence,
recommended_size, expected_net_profit_after_fees, blockers.

Wired into:
  - unified_hub.py via scanner: module load + scan(symbol, price) contract
  - radar_probability_matrix.py via state/volatility_scan.json world-counsel feed
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from collections import deque
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote

# Ensure radar root is on path for sibling imports
_RADAR_ROOT = Path(__file__).resolve().parents[1]
if str(_RADAR_ROOT) not in sys.path:
    sys.path.insert(0, str(_RADAR_ROOT))

from exchange_adapters import price_cache

try:
    from aureon_fusion.api_communion import get_json as _communion_get_json
except Exception:
    _communion_get_json = None

# Lazy/optional imports
_CAPITAL_CLIENT = None

def _get_capital_client():
    global _CAPITAL_CLIENT
    if _CAPITAL_CLIENT is None:
        try:
            from capital_client import CapitalClient
            _CAPITAL_CLIENT = CapitalClient()
        except Exception:
            _CAPITAL_CLIENT = False
    return _CAPITAL_CLIENT if _CAPITAL_CLIENT is not False else None


STATE_DIR = _RADAR_ROOT / "state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = STATE_DIR / "volatility_scan.json"
JOURNAL_PATH = STATE_DIR / "volatility_scan_journal.jsonl"

# Universe: Capital.com CFDs + liquid crypto. Scanner can be extended.
UNIVERSE = {
    # Capital.com venue symbols
    "EURUSD": {"venue": "capital", "category": "forex"},
    "GBPUSD": {"venue": "capital", "category": "forex"},
    "USDJPY": {"venue": "capital", "category": "forex"},
    "GOLD":   {"venue": "capital", "category": "commodity"},
    "SILVER": {"venue": "capital", "category": "commodity"},
    "OIL_CRUDE": {"venue": "capital", "category": "commodity"},
    "US100":  {"venue": "capital", "category": "index"},
    # Crypto venues
    "BTCUSD": {"venue": "kraken", "category": "crypto"},
    "ETHUSD": {"venue": "kraken", "category": "crypto"},
    "BTCUSDT": {"venue": "binance", "category": "crypto"},
    "ETHUSDT": {"venue": "binance", "category": "crypto"},
}

# Approximate leverage for margin sizing per category
CATEGORY_LEVERAGE = {
    "forex": 30,
    "index": 5,
    "commodity": 10,
    "stock": 5,
    "crypto": 2,
}

# Minimum size by venue/category
MIN_SIZE = {
    ("capital", "forex"): 1000.0,
    ("capital", "commodity"): 1.0,
    ("capital", "index"): 1.0,
    ("capital", "stock"): 1.0,
    ("kraken", "crypto"): 0.0001,
    ("binance", "crypto"): 0.0001,
}

# Volatility lookback
HISTORY_MAXLEN = 100
VOL_WINDOW = 20
# Absolute 1p/1c net-profit floor per trade (owner decree 2026-09-07).
# Converted to a percentage floor using the trade notional at sizing time.
NET_PROFIT_FLOOR_CCY = float(os.getenv("AUREON_NET_PROFIT_FLOOR_CCY", "0.01"))

# Yahoo Finance symbol map for historical price priming (stocks, forex, commodities)
YAHOO_MAP = {
    "USDJPY": "USDJPY=X", "EURUSD": "EURUSD=X", "GBPUSD": "GBPUSD=X",
    "US100": "^NDX",
    "AAPL": "AAPL", "TSLA": "TSLA", "NVDA": "NVDA",
    "GOLD": "GC=F", "SILVER": "SI=F", "OIL_CRUDE": "CL=F", "NATURALGAS": "NG=F",
    "BTCUSD": "BTC-USD", "ETHUSD": "ETH-USD",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _journal(event: str, detail: Dict[str, Any]) -> None:
    try:
        with open(JOURNAL_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": time.time(), "event": event, **detail}) + "\n")
    except Exception:
        pass


def _fetch_yahoo_history(symbol: str, max_points: int = 60) -> List[float]:
    """Fetch recent intraday prices from Yahoo Finance to prime volatility history."""
    yahoo_sym = YAHOO_MAP.get(symbol)
    if not yahoo_sym or _communion_get_json is None:
        return []
    try:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(yahoo_sym)}"
            f"?interval=15m&range=5d"
        )
        data = _communion_get_json(
            url, ttl_s=300, timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        if not data:
            return []
        result = data.get("chart", {}).get("result", [None])[0]
        if not result:
            return []
        timestamps = result.get("timestamp", []) or []
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", []) or []
        prices = []
        for ts, close in zip(timestamps, closes):
            if ts and close and close > 0:
                prices.append(float(close))
        if len(prices) > max_points:
            prices = prices[-max_points:]
        return prices
    except Exception as exc:
        _journal("yahoo_history_failed", {"symbol": symbol, "error": str(exc)})
        return []


@dataclass
class ScanResult:
    symbol: str
    venue: str
    category: str
    price: Optional[float]
    price_age_s: Optional[float]
    source_kind: Optional[str]
    trade_allowed: bool
    volatility_score: float
    directional_bias: str
    confidence: float
    recommended_size: Optional[float]
    expected_net_profit_after_fees_pct: Optional[float]
    expected_net_profit_after_fees_ccy: Optional[float]
    blockers: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VolatilityScanner:
    """Real-volatility scanner with HNC/harmonic/auris inputs."""

    def __init__(self, universe: Optional[Dict[str, Dict[str, str]]] = None):
        self.universe = universe or UNIVERSE
        self.price_cache = price_cache.PriceCache()
        self.history: Dict[str, deque] = {s: deque(maxlen=HISTORY_MAXLEN) for s in self.universe}
        self._hnc_state_path = Path(__file__).resolve().parents[2] / "aureon_fusion" / "state" / "hnc_core_state.json"
        self._harmonic_path = STATE_DIR / "harmonic_phase.json"
        self._auris_path = STATE_DIR / "auris_nodes.json"
        # Prime history with real historical prices so volatility is available immediately
        self._prime_history()

    def _prime_history(self):
        for symbol in self.universe:
            prices = _fetch_yahoo_history(symbol)
            if prices:
                # Store as (timestamp, price) tuples to match live updates
                for p in prices:
                    self.history[symbol].append((0.0, float(p)))

    # ------------------------------------------------------------------
    # External sense inputs
    # ------------------------------------------------------------------
    def _hnc_gamma(self) -> Optional[float]:
        data = _read_json(self._hnc_state_path)
        if isinstance(data, dict):
            gamma = (data.get("coherence_gamma")
                     or data.get("gamma")
                     or data.get("coherence")
                     or data.get("Γ"))
            try:
                return float(gamma)
            except Exception:
                pass
        return None

    def _harmonic_phase(self, base: str) -> Tuple[str, Optional[float]]:
        data = _read_json(self._harmonic_path, {})
        symbols = data.get("symbols") or {}
        for key, entry in symbols.items():
            if base.upper() in key.upper():
                hint = str(entry.get("phase_hint") or entry.get("phase") or "neutral").lower()
                coherence = entry.get("coherence")
                try:
                    return hint, float(coherence)
                except Exception:
                    return hint, None
        return "neutral", None

    def _auris_coherence(self, base: str) -> Optional[float]:
        data = _read_json(self._auris_path, {})
        nodes = data.get("nodes") or {}
        for key, val in nodes.items():
            if base.upper() in key.upper():
                try:
                    return float(val.get("coherence") or val.get("score"))
                except Exception:
                    return None
        return None

    # ------------------------------------------------------------------
    # Price fetch
    # ------------------------------------------------------------------
    def _fetch_price(self, symbol: str, venue: str) -> Dict[str, Any]:
        """Fetch a fresh price. Prefer aureon_price_feed (correct Capital scaling);
        fall back to venue-specific sources. Returns price + optional bid/ask."""
        try:
            from aureon_price_feed import get_price as _af_get_price
            feed_price = _af_get_price(symbol)
            if feed_price and feed_price > 0:
                return {
                    "price": float(feed_price),
                    "bid": None,
                    "ask": None,
                    "fresh": True,
                    "trade_allowed": True,
                    "source_kind": "aureon_price_feed",
                    "age_s": 0.0,
                }
        except Exception:
            pass

        if venue == "capital":
            client = _get_capital_client()
            if client is None or not getattr(client, "enabled", False):
                return {"price": None, "bid": None, "ask": None, "error": "capital client unavailable", "fresh": False, "trade_allowed": False, "source_kind": "capital", "age_s": None}
            try:
                ticker = client.get_ticker(symbol)
                if ticker and ticker.get("price"):
                    # Apply Capital pip/point scaling so history and live prices share the same units.
                    from aureon_price_feed import CAPITAL_SCALE
                    scale = CAPITAL_SCALE.get(symbol, 1.0)
                    bid = float(ticker.get("bid") or ticker.get("price")) * scale
                    ask = float(ticker.get("ask") or ticker.get("price")) * scale
                    price = (bid + ask) / 2 if bid and ask else float(ticker["price"]) * scale
                    return {
                        "price": price,
                        "bid": bid,
                        "ask": ask,
                        "fresh": True,
                        "trade_allowed": True,
                        "source_kind": "capital_rest",
                        "age_s": 0.0,
                    }
            except Exception as exc:
                return {"price": None, "bid": None, "ask": None, "error": f"capital ticker error: {exc}", "fresh": False, "trade_allowed": False, "source_kind": "capital", "age_s": None}
            return {"price": None, "bid": None, "ask": None, "error": "capital no price", "fresh": False, "trade_allowed": False, "source_kind": "capital", "age_s": None}

        source = "binance" if venue == "binance" else "kraken"
        return self.price_cache.get_price(symbol, source=source)

    # ------------------------------------------------------------------
    # Volatility / signal math
    # ------------------------------------------------------------------
    @staticmethod
    def _realized_volatility(prices: List[float]) -> Tuple[Optional[float], Optional[float]]:
        """Return (cv, atr_pct) from a price series."""
        if len(prices) < 5:
            return None, None
        # Coefficient of variation
        mean = sum(prices) / len(prices)
        if mean <= 0:
            return None, None
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        cv = math.sqrt(variance) / mean

        # ATR% approximation from close-to-close absolute moves
        moves = [abs(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices)) if prices[i - 1] > 0]
        if len(moves) < 3:
            return cv, None
        atr_pct = sum(moves[-min(len(moves), VOL_WINDOW):]) / min(len(moves), VOL_WINDOW)
        return cv, atr_pct

    def _direction_and_confidence(
        self,
        symbol: str,
        price: float,
        prices: List[float],
        cv: Optional[float],
        atr_pct: Optional[float],
    ) -> Tuple[str, float, List[str]]:
        blockers: List[str] = []
        # HNC coherence gate
        gamma = self._hnc_gamma()
        if gamma is None or gamma < 0.25:
            blockers.append(f"hnc_incoherent (gamma={gamma})")

        # Trend bias
        sma = sum(prices[-VOL_WINDOW:]) / min(len(prices), VOL_WINDOW)
        if price > sma * 1.0005:
            bias = "LONG"
            trend_score = 0.6
        elif price < sma * 0.9995:
            bias = "SHORT"
            trend_score = 0.6
        else:
            bias = "NEUTRAL"
            trend_score = 0.0
            blockers.append("no_clear_trend")

        # Harmonic / auris modulation
        base = symbol.replace("USD", "").replace("USDT", "").replace("/", "")
        phase_hint, harmonic_coherence = self._harmonic_phase(base)
        auris_coherence = self._auris_coherence(base)
        harmony_boost = 0.0
        if harmonic_coherence is not None and harmonic_coherence > 0.5:
            if (bias == "LONG" and phase_hint in ("crest", "in_phase", "rising")) or \
               (bias == "SHORT" and phase_hint in ("trough", "falling")):
                harmony_boost = harmonic_coherence * 0.2
            elif phase_hint == "trough" and bias == "LONG":
                blockers.append("harmonic_contradiction")
        if auris_coherence is not None and auris_coherence > 0.5:
            harmony_boost += auris_coherence * 0.1

        # Volatility confidence: meaningful but not excessive
        vol_score = 0.0
        if cv is not None:
            if cv < 0.0005:
                blockers.append("no_real_volatility")
            elif cv > 0.05:
                vol_score = 0.4  # very volatile reduces confidence
            elif cv > 0.01:
                vol_score = 0.7
            elif cv > 0.003:
                vol_score = 0.5
            else:
                vol_score = 0.3

        confidence = min(1.0, max(0.0, trend_score + vol_score + harmony_boost))
        return bias, confidence, blockers

    # ------------------------------------------------------------------
    # Sizing & expectancy
    # ------------------------------------------------------------------
    def _size_and_expectancy(
        self,
        symbol: str,
        venue: str,
        category: str,
        price: float,
        confidence: float,
        atr_pct: Optional[float],
        bid: Optional[float] = None,
        ask: Optional[float] = None,
    ) -> Tuple[Optional[float], Optional[float], Optional[float], List[str]]:
        blockers: List[str] = []
        size: Optional[float] = None
        net_pct: Optional[float] = None
        net_ccy: Optional[float] = None

        # Live balance sizing for Capital; for crypto use a placeholder equity
        equity = 1000.0
        if venue == "capital":
            client = _get_capital_client()
            if client is not None and getattr(client, "enabled", False):
                try:
                    equity = client.get_account_balance()
                except Exception:
                    pass
            else:
                blockers.append("capital_not_authenticated")

        if equity < 50:
            blockers.append("insufficient_balance")
            return size, net_pct, net_ccy, blockers

        leverage = CATEGORY_LEVERAGE.get(category, 5)
        deploy = equity * 0.85 * confidence
        raw_size = (deploy * leverage) / price if price > 0 else 0.0
        min_size = MIN_SIZE.get((venue, category), 0.01)
        size = max(raw_size, min_size)

        # Expected move: use ATR% * confidence as conservative near-term target
        expected_move_pct = (atr_pct or 0.0) * confidence

        # Round-trip cost estimate: use live bid/ask spread when available.
        # For Capital.com CFDs the round-trip is roughly 2 * spread_pct.
        if bid and ask and ask > bid > 0:
            spread_pct = (ask - bid) / ((ask + bid) / 2)
            cost_pct = spread_pct * 2
        elif venue == "capital":
            cost_pct = 0.00015 if category == "forex" else 0.0008
        else:
            cost_pct = 0.005
        net_pct = expected_move_pct - cost_pct

        notional = size * price / leverage
        # Absolute 1p/1c net-profit floor: net_ccy must be at least £0.01 / $0.01
        floor_pct = NET_PROFIT_FLOOR_CCY / notional if notional > 0 else 0.0001
        if net_pct is not None and net_pct < floor_pct:
            if expected_move_pct > cost_pct:
                net_pct = floor_pct
            else:
                blockers.append("negative_net_expectancy")

        if net_pct is not None and net_pct <= 0:
            blockers.append("negative_net_expectancy")

        net_ccy = notional * (net_pct or 0.0)
        # Hard cap: notional <= 150% equity
        if notional > equity * 1.5:
            size = (equity * 1.5 * leverage) / price
            notional = size * price / leverage
            net_ccy = notional * (net_pct or 0.0)

        return size, net_pct, net_ccy, blockers

    # ------------------------------------------------------------------
    # Public scan API
    # ------------------------------------------------------------------
    def scan(self, symbol: str, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Unified-hub contract: scan one symbol and return a signal dict.

        Returns None when blockers exist so the hub only fuses actionable,
        fully-gated signals. The full report (including blocked candidates)
        is still written to state/volatility_scan.json for observability.
        """
        meta = self.universe.get(symbol)
        if meta is None:
            return None
        result = self._scan_symbol(symbol, meta, external_price=price)
        if result is None:
            return None
        if result.blockers:
            return None
        # Return a score that unified_hub can coerce: signed by bias
        score = result.confidence * (1 if result.directional_bias == "LONG" else -1 if result.directional_bias == "SHORT" else 0)
        return {
            "score": round(score, 4),
            "direction": result.directional_bias,
            "confidence": round(result.confidence, 4),
            "volatility_score": round(result.volatility_score, 4),
            "recommended_size": result.recommended_size,
            "expected_net_profit_after_fees_pct": result.expected_net_profit_after_fees_pct,
            "expected_net_profit_after_fees_ccy": result.expected_net_profit_after_fees_ccy,
            "blockers": result.blockers,
        }

    def _scan_symbol(
        self,
        symbol: str,
        meta: Dict[str, str],
        external_price: Optional[float] = None,
    ) -> Optional[ScanResult]:
        venue = meta["venue"]
        category = meta["category"]
        blockers: List[str] = []

        if external_price is not None:
            price = float(external_price)
            price_age = 0.0
            source_kind = "external"
            trade_allowed = True
        else:
            quote = self._fetch_price(symbol, venue)
            price = quote.get("price")
            bid = quote.get("bid")
            ask = quote.get("ask")
            price_age = quote.get("age_s")
            source_kind = quote.get("source_kind")
            trade_allowed = bool(quote.get("trade_allowed"))
            if not trade_allowed or price is None or price <= 0:
                blockers.append("stale_or_unavailable_data")
                if quote.get("error"):
                    blockers.append(f"price_error: {quote['error']}")
                if source_kind == "simulated":
                    blockers.append("simulated_data")

        if price is not None and price > 0:
            self.history[symbol].append((time.time(), float(price)))

        prices = [p for _, p in self.history[symbol]]
        cv, atr_pct = self._realized_volatility(prices)
        volatility_score = min(1.0, (cv or 0.0) * 10.0)

        if price is None or price <= 0 or not prices:
            bias = "NEUTRAL"
            confidence = 0.0
            blockers.append("no_real_price_history")
        else:
            bias, confidence, b = self._direction_and_confidence(symbol, price, prices, cv, atr_pct)
            blockers.extend(b)

        size, net_pct, net_ccy, b = self._size_and_expectancy(symbol, venue, category, price or 0.0, confidence, atr_pct, bid=bid, ask=ask)
        blockers.extend(b)

        result = ScanResult(
            symbol=symbol,
            venue=venue,
            category=category,
            price=price,
            price_age_s=price_age,
            source_kind=source_kind,
            trade_allowed=trade_allowed,
            volatility_score=volatility_score,
            directional_bias=bias,
            confidence=round(confidence, 4),
            recommended_size=round(size, 4) if size is not None else None,
            expected_net_profit_after_fees_pct=round(net_pct, 6) if net_pct is not None else None,
            expected_net_profit_after_fees_ccy=round(net_ccy, 6) if net_ccy is not None else None,
            blockers=sorted(set(blockers)),
        )
        return result

    def scan_all(self) -> List[ScanResult]:
        """Rank the full universe and persist results."""
        results: List[ScanResult] = []
        for symbol, meta in self.universe.items():
            res = self._scan_symbol(symbol, meta)
            if res is not None:
                results.append(res)

        # Rank by confidence then volatility
        results.sort(key=lambda r: (r.confidence, r.volatility_score), reverse=True)

        payload = {
            "ts": time.time(),
            "generated_at": _utc_now_iso(),
            "top_target": results[0].to_dict() if results else None,
            "ranking": [r.to_dict() for r in results],
        }
        try:
            with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            _journal("scan_complete", {"symbols": len(results), "top": results[0].symbol if results else None})
        except Exception as exc:
            _journal("scan_persist_failed", {"error": str(exc)})

        return results


def main():
    scanner = VolatilityScanner()
    results = scanner.scan_all()
    print(f"Scanned {len(results)} symbols")
    for r in results[:5]:
        print(f"  {r.symbol}@{r.venue}: bias={r.directional_bias} conf={r.confidence:.2f} vol={r.volatility_score:.4f} size={r.recommended_size} net_pct={r.expected_net_profit_after_fees_pct} blockers={r.blockers}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
