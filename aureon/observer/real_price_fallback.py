"""Real-data-only price fallback chain.

When a primary live exchange API returns no prices, production code MUST
NOT substitute hardcoded values. This module provides a single helper that
walks a priority chain of REAL data sources and returns whatever it can
gather. Only after every real source has been tried — and failed — does
the helper return an empty dict, signalling the caller to skip the trade
cycle.

Source priority (configurable via ``AUREON_PRICE_FALLBACK_CHAIN`` env var):

  1. ``unified_cache`` — :func:`aureon.data_feeds.unified_market_cache.get_all_prices`
     reads recent (≤ ``max_age``) ticks written by feeders running in other
     processes. No API call. Fastest path.
  2. ``coingecko_cache`` — disk cache written by
     :mod:`aureon.exchanges.coingecko_price_feeder`. Free, real, possibly
     a few minutes stale.
  3. ``kraken`` — direct :meth:`KrakenClient.get_ticker` per symbol via the
     existing :func:`get_kraken_client` singleton. Real REST call.
  4. ``binance`` — direct :meth:`BinanceClient.get_ticker_price` per symbol.
     Real REST call.
  5. ``coingecko_live`` — direct :func:`fetch_coingecko_prices` REST call
     (rate-limited, 10–30 req/min on free tier). Real REST call.

Each source is tried in order; if it returns at least one price for the
requested symbols, the chain stops and returns. Partial coverage is
acceptable — the caller can decide whether to proceed with whatever
real prices arrived.

The chain NEVER returns hardcoded values. If every source fails, the
helper returns ``{}`` and the caller (master_launcher, queen_hive_mind,
real_data_feed_hub) skips the trade cycle.

Configuration:

  - ``AUREON_PRICE_FALLBACK_CHAIN`` — comma-separated source names in
    priority order. Default
    ``"unified_cache,coingecko_cache,kraken,binance,coingecko_live"``.
  - ``AUREON_PRICE_FALLBACK_MAX_CACHE_AGE_SEC`` — float, default 60.
    Sources that read from disk caches reject ticks older than this.
  - ``AUREON_PRICE_FALLBACK_TIMEOUT_SEC`` — float, default 5. Per-source
    HTTP timeout.

Symbol normalisation: symbols are accepted in any common form
(``BTC``, ``BTC/USD``, ``BTCUSD``, ``XBTUSD``) and emitted as
``BTC/USD`` consistently.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_CHAIN = "unified_cache,coingecko_cache,kraken,binance,coingecko_live"
DEFAULT_MAX_CACHE_AGE_SEC = 60.0
DEFAULT_TIMEOUT_SEC = 5.0
# Keep the same small provider-clock skew tolerated by receipt validators.
MAX_FUTURE_SOURCE_SKEW_SEC = 5.0

# Quote currencies to try when a caller passes a bare base symbol like "BTC".
# Order matters: longer suffixes first so XXBTZUSD strips ZUSD (4 chars), not USD (3).
# We always emit the canonical "BASE/USD" form.
_QUOTES = ("ZUSD", "USDT", "USDC", "USD")

# Kraken rewrites BTC → XBT and prefixes some assets with X/Z. Map both ways.
_KRAKEN_BASE_ALIAS = {
    "BTC": "XBT",
    "DOGE": "XDG",
}

# CoinGecko coin ID lookup for the most common symbols. The full table is
# in coingecko_price_feeder; we mirror only the top tradeables here so the
# helper doesn't pull a 200-entry table for every fallback call.
_COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "BNB": "binancecoin",
    "USDT": "tether",
    "USDC": "usd-coin",
}


def _env_chain() -> List[str]:
    raw = os.environ.get("AUREON_PRICE_FALLBACK_CHAIN", DEFAULT_CHAIN)
    return [s.strip() for s in raw.split(",") if s.strip()]


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "")
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def _normalise_symbol(symbol: str) -> str:
    """Return ``BASE/USD`` form. Strips quote currency suffixes; un-Kraken-ifies."""
    s = symbol.upper().strip().replace(":", "/")
    if "/" in s:
        base, quote = s.split("/", 1)
        return f"{_canonical_base(base)}/USD"
    # No slash: try stripping known quote suffixes (longer suffixes first so
    # XXBTZUSD → XXBT (ZUSD stripped), not XXBTZ (USD stripped)).
    for q in _QUOTES + ("ZEUR", "EUR", "GBP"):
        if s.endswith(q) and len(s) > len(q):
            return f"{_canonical_base(s[:-len(q)])}/USD"
    return f"{_canonical_base(s)}/USD"


def _canonical_base(base: str) -> str:
    base = base.upper().strip()
    # Strip Kraken X/Z prefixes on 4-char codes (e.g. XBT → BT, but XXBT → XBT)
    if len(base) == 4 and base[0] in ("X", "Z"):
        base = base[1:]
    if base == "XBT":
        return "BTC"
    if base == "XDG":
        return "DOGE"
    return base


# ---------------------------------------------------------------------------
# Source: unified market cache (process-local + cross-process via cache files)
# ---------------------------------------------------------------------------

def _src_unified_cache(symbols: List[str], max_age: float) -> Dict[str, float]:
    try:
        from aureon.data_feeds.unified_market_cache import get_all_prices
    except Exception as exc:
        logger.debug("unified_cache unavailable: %s", exc)
        return {}
    try:
        raw = get_all_prices(max_age=max_age) or {}
    except Exception as exc:
        logger.warning("[real-price-fallback] unified_cache fetch failed: %s", exc)
        return {}
    out: Dict[str, float] = {}
    # The unified cache stores keys in many shapes (BTC, BTCUSD, XBTUSD,
    # BTC/USD). Normalise both sides so requested symbols match.
    norm_raw = {_normalise_symbol(k): v for k, v in raw.items() if v}
    if not symbols:
        return norm_raw
    for sym in symbols:
        n = _normalise_symbol(sym)
        if n in norm_raw and norm_raw[n] > 0:
            out[n] = float(norm_raw[n])
    return out


# ---------------------------------------------------------------------------
# Source: CoinGecko disk cache (written by coingecko_price_feeder)
# ---------------------------------------------------------------------------

_COINGECKO_CACHE_PATHS = (
    Path("coingecko_market_cache.json"),
    Path("aureon/data_feeds/coingecko_market_cache.json"),
    Path(__file__).resolve().parent.parent / "data_feeds" / "coingecko_market_cache.json",
)


def _src_coingecko_cache(symbols: List[str], max_age: float) -> Dict[str, float]:
    for p in _COINGECKO_CACHE_PATHS:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text())
        except Exception as exc:
            logger.warning("[real-price-fallback] coingecko_cache %s parse error: %s", p, exc)
            continue
        # Cache provenance must be explicit. Receipt time / file-write time is
        # not a provider source timestamp and must never be promoted into one.
        source_timestamp = data.get("source_timestamp")
        received_at = data.get("received_at")
        if data.get("generated_values") is not False:
            logger.warning(
                "[real-price-fallback] coingecko_cache %s no_data/non_actionable: "
                "generated_values must be false",
                p,
            )
            continue
        try:
            source_ts = float(source_timestamp)
            receipt_ts = float(received_at)
        except (TypeError, ValueError):
            logger.warning(
                "[real-price-fallback] coingecko_cache %s no_data/non_actionable: "
                "source_timestamp and received_at are required",
                p,
            )
            continue
        if not (math.isfinite(source_ts) and source_ts > 0 and math.isfinite(receipt_ts) and receipt_ts > 0):
            logger.warning(
                "[real-price-fallback] coingecko_cache %s no_data/non_actionable: "
                "malformed source or receipt timestamp",
                p,
            )
            continue
        age = time.time() - source_ts
        if age < -MAX_FUTURE_SOURCE_SKEW_SEC or age > max_age:
            logger.warning(
                "[real-price-fallback] coingecko_cache %s no_data/non_actionable: "
                "source timestamp is stale or too far in the future",
                p,
            )
            continue
        out: Dict[str, float] = {}
        for entry in data.get("data", []):
            sym = entry.get("symbol", "").upper()
            price = entry.get("current_price") or entry.get("price")
            if not sym or not price or price <= 0:
                continue
            out[_normalise_symbol(sym)] = float(price)
        # Filter to requested symbols if provided
        if symbols:
            wanted = {_normalise_symbol(s) for s in symbols}
            out = {k: v for k, v in out.items() if k in wanted}
        if out:
            return out
    return {}


# ---------------------------------------------------------------------------
# Source: Kraken direct
# ---------------------------------------------------------------------------

def _src_kraken(symbols: List[str], timeout: float) -> Dict[str, float]:
    if not symbols:
        return {}
    try:
        from aureon.exchanges.kraken_client import get_kraken_client
        kc = get_kraken_client()
    except Exception as exc:
        logger.debug("kraken_client unavailable: %s", exc)
        return {}
    if kc is None:
        return {}
    out: Dict[str, float] = {}
    for sym in symbols:
        n = _normalise_symbol(sym)
        base = n.split("/")[0]
        kraken_base = _KRAKEN_BASE_ALIAS.get(base, base)
        kraken_pair = f"{kraken_base}USD"
        try:
            ticker = kc.get_ticker(kraken_pair)
            if not ticker:
                continue
            price = ticker.get("last") or ticker.get("price") or ticker.get("c")
            if isinstance(price, list):
                price = price[0]
            price_f = float(price) if price else 0.0
            if price_f > 0:
                out[n] = price_f
        except Exception as exc:
            logger.debug("kraken get_ticker(%s) failed: %s", kraken_pair, exc)
    return out


# ---------------------------------------------------------------------------
# Source: Binance direct
# ---------------------------------------------------------------------------

def _src_binance(symbols: List[str], timeout: float) -> Dict[str, float]:
    if not symbols:
        return {}
    try:
        from aureon.exchanges.binance_client import BinanceClient
        bc = BinanceClient()
    except Exception as exc:
        logger.debug("binance_client unavailable: %s", exc)
        return {}
    out: Dict[str, float] = {}
    for sym in symbols:
        n = _normalise_symbol(sym)
        base = n.split("/")[0]
        binance_pair = f"{base}USDT"
        try:
            ticker = bc.get_ticker_price(binance_pair)
            if not ticker:
                continue
            price = ticker.get("price")
            price_f = float(price) if price else 0.0
            if price_f > 0:
                out[n] = price_f
        except Exception as exc:
            logger.debug("binance get_ticker_price(%s) failed: %s", binance_pair, exc)
    return out


# ---------------------------------------------------------------------------
# Source: CoinGecko live REST
# ---------------------------------------------------------------------------

def _src_coingecko_live(symbols: List[str], timeout: float) -> Dict[str, float]:
    if not symbols:
        return {}
    try:
        import requests
    except Exception as exc:
        logger.debug("requests unavailable for coingecko_live: %s", exc)
        return {}
    coin_ids = []
    sym_to_id: Dict[str, str] = {}
    for sym in symbols:
        n = _normalise_symbol(sym)
        base = n.split("/")[0]
        cg_id = _COINGECKO_IDS.get(base)
        if cg_id:
            coin_ids.append(cg_id)
            sym_to_id[cg_id] = n
    if not coin_ids:
        return {}
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(coin_ids[:250]), "vs_currencies": "usd"}
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code != 200:
            logger.warning("[real-price-fallback] coingecko_live returned HTTP %d", resp.status_code)
            return {}
        data = resp.json() or {}
    except Exception as exc:
        logger.warning("[real-price-fallback] coingecko_live fetch failed: %s", exc)
        return {}
    out: Dict[str, float] = {}
    for cg_id, payload in data.items():
        usd = payload.get("usd") if isinstance(payload, dict) else None
        if not usd or usd <= 0:
            continue
        n = sym_to_id.get(cg_id)
        if n:
            out[n] = float(usd)
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

_SOURCES = {
    "unified_cache": _src_unified_cache,
    "coingecko_cache": _src_coingecko_cache,
    "kraken": _src_kraken,
    "binance": _src_binance,
    "coingecko_live": _src_coingecko_live,
}


def get_real_prices_with_fallback(
    symbols: Optional[List[str]] = None,
    *,
    max_cache_age_sec: Optional[float] = None,
    timeout_sec: Optional[float] = None,
    chain: Optional[List[str]] = None,
) -> Tuple[Dict[str, float], List[str]]:
    """Return (prices, sources_used) walking the live-data fallback chain.

    Returns ``({}, [])`` when every configured source returns no prices —
    callers MUST treat that as "no real data, skip the trade cycle". Never
    substitutes hardcoded values.

    Args:
      symbols: List of symbols to fetch (any common form). If ``None``,
        sources that support full-cache reads (``unified_cache``,
        ``coingecko_cache``) return everything they have; per-symbol
        sources (``kraken``, ``binance``, ``coingecko_live``) skip.
      max_cache_age_sec: Reject cached ticks older than this. Default 60s.
      timeout_sec: Per-source HTTP timeout. Default 5s.
      chain: Override the source priority order. Default reads
        ``AUREON_PRICE_FALLBACK_CHAIN`` env var.

    Returns:
      (prices, sources_used) where prices is ``{"BTC/USD": 67234.50, ...}``
      and sources_used is the ordered list of source names that
      contributed at least one price.
    """
    max_age = max_cache_age_sec if max_cache_age_sec is not None else _env_float(
        "AUREON_PRICE_FALLBACK_MAX_CACHE_AGE_SEC", DEFAULT_MAX_CACHE_AGE_SEC
    )
    timeout = timeout_sec if timeout_sec is not None else _env_float(
        "AUREON_PRICE_FALLBACK_TIMEOUT_SEC", DEFAULT_TIMEOUT_SEC
    )
    chain_names = chain if chain is not None else _env_chain()

    accumulated: Dict[str, float] = {}
    sources_used: List[str] = []
    requested = [_normalise_symbol(s) for s in (symbols or [])]
    remaining: Optional[List[str]] = list(requested) if requested else None

    for src_name in chain_names:
        src_fn = _SOURCES.get(src_name)
        if src_fn is None:
            logger.debug("Unknown fallback source %r — skipping", src_name)
            continue
        try:
            if src_name in ("unified_cache", "coingecko_cache"):
                got = src_fn(symbols or [], max_age)
            else:
                # Per-symbol REST sources only fire when we have a target list
                if not remaining and not requested:
                    continue
                got = src_fn(remaining if remaining else [], timeout)
        except Exception as exc:
            logger.warning("[real-price-fallback] %s raised: %s", src_name, exc)
            continue

        new_prices = {k: v for k, v in (got or {}).items() if v and v > 0 and k not in accumulated}
        if new_prices:
            accumulated.update(new_prices)
            sources_used.append(src_name)
            if remaining is not None:
                remaining = [s for s in remaining if s not in accumulated]
            # If we now have everything requested, stop early.
            if requested and all(s in accumulated for s in requested):
                break

    if accumulated:
        logger.info(
            "[real-price-fallback] resolved %d/%d prices via %s",
            len(accumulated),
            len(requested) if requested else len(accumulated),
            "+".join(sources_used),
        )
    else:
        logger.warning(
            "[real-price-fallback] all sources returned no prices "
            "(chain=%s, requested=%d symbols); caller must skip cycle "
            "rather than substitute hardcoded values",
            "+".join(chain_names),
            len(requested),
        )
    return accumulated, sources_used


def get_real_price(
    symbol: str,
    *,
    max_cache_age_sec: Optional[float] = None,
    timeout_sec: Optional[float] = None,
) -> Optional[float]:
    """Fetch a single symbol's price via the live-data fallback chain.

    Returns ``None`` if every real source fails — callers MUST treat
    ``None`` as "no real data, skip this calculation" and never substitute
    a hardcoded price.

    Convenience wrapper around :func:`get_real_prices_with_fallback` for
    sites that need just one symbol's price (e.g. portfolio breakdowns,
    glassnode whale-flow USD valuations, single-asset position sizing).
    """
    prices, _ = get_real_prices_with_fallback(
        symbols=[symbol],
        max_cache_age_sec=max_cache_age_sec,
        timeout_sec=timeout_sec,
    )
    canonical = _normalise_symbol(symbol)
    return prices.get(canonical)
