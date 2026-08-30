#!/usr/bin/env python3
"""
Capital market universe and monitoring cache.

Builds a local symbol universe file plus a lightweight monitored quote cache
using Capital.com metadata and lower-cost public quote sources where possible.
This lets CapitalCFDTrader reuse local snapshots before hitting Capital's API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from aureon.exchanges.capital_client import CapitalClient
from aureon.exchanges.capital_cfd_trader import CAPITAL_UNIVERSE


DEFAULT_UNIVERSE_PATH = Path(os.getenv("CAPITAL_UNIVERSE_CACHE_PATH", "ws_cache/capital_universe.json"))
DEFAULT_MONITOR_PATH = Path(os.getenv("CAPITAL_MONITOR_CACHE_PATH", "ws_cache/capital_monitor.json"))
QUOTE_MAX_AGE_SECONDS = 300.0
FUTURE_SKEW_SECONDS = 5.0

YAHOO_SYMBOL_MAP: Dict[str, str] = {
    "AAPL": "AAPL",
    "TSLA": "TSLA",
    "NVDA": "NVDA",
    "AMZN": "AMZN",
    "MSFT": "MSFT",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "AUDUSD": "AUDUSD=X",
    "USDCAD": "CAD=X",
    "EURGBP": "EURGBP=X",
    "UK100": "^FTSE",
    "US500": "^GSPC",
    "US30": "^DJI",
    "DE40": "^GDAXI",
    "GOLD": "GC=F",
    "SILVER": "SI=F",
    "OIL_CRUDE": "CL=F",
    "NATURALGAS": "NG=F",
}


def _finite_positive(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) and parsed > 0 else None


def _finite_number(value: Any) -> Optional[float]:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _fresh_source_timestamp(value: Any, *, received_at: float) -> Optional[float]:
    source_timestamp = _finite_positive(value)
    if source_timestamp is None:
        return None
    if (
        source_timestamp > received_at + FUTURE_SKEW_SECONDS
        or received_at - source_timestamp > QUOTE_MAX_AGE_SECONDS
    ):
        return None
    return source_timestamp


def _quote_receipt_id(source_id: str, symbol: str, source_timestamp: float,
                      price: float, bid: float, ask: float, change_pct: float) -> str:
    material = "|".join((
        source_id, symbol, f"{source_timestamp:.6f}", f"{price:.12g}",
        f"{bid:.12g}", f"{ask:.12g}", f"{change_pct:.12g}",
    ))
    return "quote-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _fetch_yahoo_quotes(symbols: List[str], timeout: float = 8.0) -> Dict[str, Dict[str, Any]]:
    if not symbols:
        return {}
    url = "https://query1.finance.yahoo.com/v7/finance/quote?symbols=" + urllib.parse.quote(",".join(symbols))
    req = urllib.request.Request(url, headers={"User-Agent": "Aureon-Capital-Monitor/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return {}

    received_at = time.time()
    out: Dict[str, Dict[str, Any]] = {}
    for quote in payload.get("quoteResponse", {}).get("result", []) or []:
        sym = str(quote.get("symbol") or "").upper()
        if not sym:
            continue
        bid = _finite_positive(quote.get("bid"))
        ask = _finite_positive(quote.get("ask"))
        price = _finite_positive(quote.get("regularMarketPrice"))
        change_pct = _finite_number(quote.get("regularMarketChangePercent"))
        source_timestamp = _fresh_source_timestamp(
            quote.get("regularMarketTime"), received_at=received_at,
        )
        if (
            bid is None or ask is None or price is None or change_pct is None
            or ask < bid or source_timestamp is None
        ):
            continue
        source_id = "yahoo.finance.quote"
        out[sym] = {
            "price": price,
            "bid": bid,
            "ask": ask,
            "change_pct": change_pct,
            "market_state": str(quote.get("marketState") or ""),
            "source_id": source_id,
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "receipt_id": _quote_receipt_id(
                source_id, sym, source_timestamp, price, bid, ask, change_pct,
            ),
            "truth_status": "real_observed",
            "generated_values": False,
        }
    return out


def _complete_capital_quote(symbol: str, quote: Any, *, received_at: float) -> Optional[Dict[str, Any]]:
    """Accept only the repaired Capital client's complete provider receipt."""
    if not isinstance(quote, dict):
        return None
    source_id = quote.get("source_id")
    receipt_id = quote.get("receipt_id")
    if (
        not isinstance(source_id, str) or not source_id.strip()
        or not isinstance(receipt_id, str) or not receipt_id.strip()
        or quote.get("truth_status") != "real_observed"
        or quote.get("generated_values") is not False
    ):
        return None
    source_timestamp = _fresh_source_timestamp(
        quote.get("source_timestamp"), received_at=received_at,
    )
    quote_received_at = _finite_positive(quote.get("received_at"))
    price = _finite_positive(quote.get("price"))
    bid = _finite_positive(quote.get("bid"))
    ask = _finite_positive(quote.get("ask"))
    change_pct = _finite_number(quote.get("change_pct"))
    if (
        source_timestamp is None or quote_received_at is None
        or quote_received_at < source_timestamp - FUTURE_SKEW_SECONDS
        or quote_received_at > received_at + FUTURE_SKEW_SECONDS
        or price is None or bid is None or ask is None or ask < bid
        or change_pct is None
    ):
        return None
    return {
        "symbol": symbol,
        "source": "capital",
        "source_id": source_id,
        "source_timestamp": source_timestamp,
        "received_at": quote_received_at,
        "receipt_id": receipt_id,
        "truth_status": "real_observed",
        "generated_values": False,
        "price": price,
        "bid": bid,
        "ask": ask,
        "change_pct": change_pct,
        "epic": str(quote.get("epic") or ""),
        "market_state": str(quote.get("market_status") or ""),
    }


def _build_universe_payload(client: CapitalClient) -> Dict[str, Any]:
    universe_rows: List[Dict[str, Any]] = []
    for symbol, cfg in CAPITAL_UNIVERSE.items():
        resolved: Dict[str, Any] = {}
        try:
            resolved = client._resolve_market(symbol) or {}  # type: ignore[attr-defined]
        except Exception:
            resolved = {}
        yahoo_symbol = YAHOO_SYMBOL_MAP.get(symbol, "")
        universe_rows.append({
            "symbol": symbol,
            "asset_class": cfg.get("class", "unknown"),
            "epic": str(resolved.get("epic") or ""),
            "instrument_name": str(resolved.get("instrumentName") or resolved.get("symbol") or ""),
            "yahoo_symbol": yahoo_symbol,
            "config": dict(cfg),
        })
    return {
        "generated_at": time.time(),
        "source": "capital_market_monitor.universe",
        "symbols": universe_rows,
    }


def _build_monitor_payload(client: CapitalClient, universe_payload: Dict[str, Any]) -> Dict[str, Any]:
    capital_symbols = [row["symbol"] for row in universe_payload.get("symbols", [])]
    yahoo_symbols = [row["yahoo_symbol"] for row in universe_payload.get("symbols", []) if row.get("yahoo_symbol")]
    yahoo_quotes = _fetch_yahoo_quotes(yahoo_symbols)

    received_at = time.time()
    prices: Dict[str, Dict[str, Any]] = {}
    for row in universe_payload.get("symbols", []):
        symbol = str(row.get("symbol") or "").upper()
        yahoo_symbol = str(row.get("yahoo_symbol") or "").upper()
        q = yahoo_quotes.get(yahoo_symbol, {})
        if q:
            prices[symbol] = {
                "symbol": symbol,
                "source": "yahoo",
                "price": q["price"],
                "bid": q["bid"],
                "ask": q["ask"],
                "change_pct": q["change_pct"],
                "epic": str(row.get("epic") or ""),
                "market_state": str(q.get("market_state") or ""),
                "source_id": q["source_id"],
                "source_timestamp": q["source_timestamp"],
                "received_at": q["received_at"],
                "receipt_id": q["receipt_id"],
                "truth_status": "real_observed",
                "generated_values": False,
            }

    # Backfill any missing symbols directly from Capital.
    missing = [sym for sym in capital_symbols if sym not in prices]
    if missing and getattr(client, "enabled", False):
        try:
            capital_quotes = client.get_tickers_for_symbols(missing)
        except Exception:
            capital_quotes = {}
        for symbol, q in capital_quotes.items():
            normalized = _complete_capital_quote(
                str(symbol).upper(), q, received_at=received_at,
            )
            if normalized is None:
                continue
            prices[normalized["symbol"]] = normalized

    return {
        # This is solely the local cache write/receipt time, never a provider time.
        "generated_at": received_at,
        "source": "capital_market_monitor.quotes",
        "status": "real_observed" if prices else "no_data",
        "truth_status": "real_observed" if prices else "no_data",
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "count": len(prices),
        "prices": prices,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Capital universe and monitor cache")
    parser.add_argument("--universe-out", default=str(DEFAULT_UNIVERSE_PATH))
    parser.add_argument("--monitor-out", default=str(DEFAULT_MONITOR_PATH))
    parser.add_argument("--interval-s", type=float, default=float(os.getenv("CAPITAL_MONITOR_INTERVAL_S", "15")))
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    client = CapitalClient()
    universe_path = Path(args.universe_out)
    monitor_path = Path(args.monitor_out)

    while True:
        universe_payload = _build_universe_payload(client)
        monitor_payload = _build_monitor_payload(client, universe_payload)
        _atomic_write_json(universe_path, universe_payload)
        _atomic_write_json(monitor_path, monitor_payload)
        print(
            f"Wrote Capital universe ({len(universe_payload.get('symbols', []))}) "
            f"and monitor cache ({monitor_payload.get('count', 0)})"
        )
        if args.once:
            return 0
        time.sleep(max(1.0, float(args.interval_s)))


if __name__ == "__main__":
    raise SystemExit(main())
