"""Shared public-data fetch helpers for the global energy flow analyzers.

All network access goes through aureon_fusion.api_communion (the courteous,
throttled, budgeted public-data layer). Stale cached bodies are NEVER passed
through as live values — every helper returns None (fail-closed) when the only
available body is marked ``stale: true``, so no consumer can mistake cached
data for fresh telemetry.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

# aureon_fusion lives one directory above aureon_radar/
_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

try:
    from aureon_fusion.api_communion import get_json
except ImportError:  # pragma: no cover - environment misconfiguration
    get_json = None

# TTLs per upstream source (seconds) — conservative, rate-limit friendly
BINANCE_TTL_S = 30
YAHOO_TTL_S = 90
COINGECKO_TTL_S = 60

# Yahoo Finance universe for cross-asset context (symbol -> Yahoo ticker)
YAHOO_MAP: Dict[str, str] = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "AUDUSD": "AUDUSD=X",
    "US500": "^GSPC",
    "NAS100": "^NDX",
    "US30": "^DJI",
    "VIX": "^VIX",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "OIL_CRUDE": "CL=F",
    "NATURAL_GAS": "NG=F",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
}

_YAHOO_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def _is_stale(body: Any) -> bool:
    return isinstance(body, dict) and body.get("stale") is True


def _unwrap(body: Any) -> Any:
    """Unwrap a stale-marker wrapper; callers must have checked _is_stale first."""
    if isinstance(body, dict) and "body" in body and body.get("source") == "stale_cache":
        return body["body"]
    return body


def fetch_json_live(url: str, ttl_s: float, timeout: float = 8.0,
                    headers: Optional[dict] = None) -> Optional[Any]:
    """Fetch JSON via communion. Returns None when unavailable or stale-only.

    Never returns a stale body: communion marks stale payloads with
    ``stale: true`` and we drop them here (fail-closed, no fake freshness).
    """
    if get_json is None:
        return None
    try:
        body = get_json(url, ttl_s=ttl_s, timeout=timeout, headers=headers)
    except Exception:
        return None
    if body is None or _is_stale(body):
        return None
    return body


def fetch_binance_24h_tickers() -> Optional[List[Dict[str, Any]]]:
    """All Binance USDT spot 24h tickers in ONE public call (weight 40, cached).

    Returns a list of raw ticker dicts, or None when unavailable/stale.
    """
    body = fetch_json_live(
        "https://api.binance.com/api/v3/ticker/24hr", ttl_s=BINANCE_TTL_S, timeout=10.0
    )
    if not isinstance(body, list):
        return None
    return body


def binance_tickers_to_changes(tickers: List[Dict[str, Any]],
                               quote: str = "USDT",
                               min_quote_volume: float = 5_000_000.0
                               ) -> Dict[str, Dict[str, float]]:
    """Reduce raw 24h tickers to {BASE: {change_pct, price, quote_volume}}.

    Only liquid pairs (quote volume >= min_quote_volume) are kept, so illiquid
    noise never shows up as a "mover".
    """
    out: Dict[str, Dict[str, float]] = {}
    for t in tickers:
        symbol = t.get("symbol", "")
        if not symbol.endswith(quote):
            continue
        base = symbol[: -len(quote)]
        try:
            qv = float(t.get("quoteVolume", 0.0))
            price = float(t.get("lastPrice", 0.0))
            chg = float(t.get("priceChangePercent", 0.0))
        except (TypeError, ValueError):
            continue
        if qv < min_quote_volume or price <= 0:
            continue
        out[base] = {"change_pct": chg, "price": price, "quote_volume": qv}
    return out


def fetch_yahoo_change_pct(symbol: str) -> Optional[Dict[str, float]]:
    """24h change % for a forex/index/commodity/stock symbol via Yahoo chart.

    Returns {change_pct, price} or None when unavailable/stale.
    """
    yahoo_sym = YAHOO_MAP.get(symbol)
    if not yahoo_sym:
        return None
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{quote(yahoo_sym)}?interval=1d&range=5d"
    )
    body = fetch_json_live(url, ttl_s=YAHOO_TTL_S, timeout=8.0, headers=_YAHOO_UA)
    if not isinstance(body, dict):
        return None
    try:
        result = body.get("chart", {}).get("result", [{}])[0]
        meta = result.get("meta", {})
        price = meta.get("regularMarketPrice")
        prev_close = meta.get("previousClose") or meta.get("chartPreviousClose")
        if price is None or not prev_close:
            # Fall back to last two daily closes in the payload
            closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            closes = [c for c in closes if c is not None]
            if len(closes) >= 2:
                price, prev_close = closes[-1], closes[-2]
        price = float(price)
        prev_close = float(prev_close)
        if price <= 0 or prev_close <= 0:
            return None
        return {"change_pct": (price - prev_close) / prev_close * 100.0, "price": price}
    except (TypeError, ValueError, IndexError, KeyError, AttributeError):
        return None


def fetch_binance_recent_trades(symbol: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
    """Recent public trades for one Binance spot symbol (no auth needed)."""
    body = fetch_json_live(
        f"https://api.binance.com/api/v3/trades?symbol={symbol}&limit={limit}",
        ttl_s=BINANCE_TTL_S, timeout=8.0,
    )
    if not isinstance(body, list):
        return None
    return body


def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 48) -> Optional[List[List[Any]]]:
    """Recent public OHLCV klines for one Binance spot symbol (no auth needed)."""
    body = fetch_json_live(
        f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}",
        ttl_s=BINANCE_TTL_S, timeout=8.0,
    )
    if not isinstance(body, list):
        return None
    return body


def now_ts() -> float:
    return time.time()
