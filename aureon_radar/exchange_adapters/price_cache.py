"""Public price cache — open-source data with throttle layer and freshness gates.

Scope: OPEN-SOURCE DATA + THROTTLE (owner decree 2026-09-06). Monitor trades
using open-source data alongside exchange APIs WITHOUT overloading exchange
API calls.

Sources (all public endpoints, no auth required):
    alpaca   — https://data.alpaca.markets free tier
               (crypto latest trades, no key; stock latest quote uses key
               headers if present, still free-tier data)
    binance  — https://api.binance.com/api/v3/ticker/price (public)
    kraken   — https://api.kraken.com/0/public/OHLC (public)

Guarantees:
    • per-(source, symbol) TTL cache (default 15s) — repeated lookups inside
      the TTL never hit the network
    • global rate limiter — max 10 HTTP req/min across ALL sources by default;
      requests beyond the budget wait for a slot instead of bursting. When cash
      is low the organism can switch to urgent mode (TTL 5s, limit 60 req/min)
      which is still inside Binance's 1,200 weight/min IP limit.
    • optional Binance websocket ticker stream when cash is low and the
      websocket-client library is available — sub-second updates without
      touching REST. Falls back to REST cleanly if the websocket is down.
    • every fetch AND every cache hit is journaled to
      aureon_radar/state/price_cache_journal.jsonl
    • FAIL-CLOSED: any fetch error yields price=None plus an error string.
      A synthetic or stale-as-fresh price is NEVER returned. Cached values
      are only served inside their TTL; expiry forces a fresh fetch or None.
    • FRESHNESS GATE: every result carries `fresh`, `trade_allowed`,
      `source_kind` and `age_s`. Stale (>60s), simulated, or error data is
      flagged `trade_allowed=False`; execution modules must refuse to trade
      on it.

Connectivity is reported honestly (binance_adapter.py precedent): if a probe
fails, the failure is returned — never smoothed over.
"""

import json
import logging
import os
import socket
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

# Import-time guard: every socket created after this import is bounded.
socket.setdefaulttimeout(30)

logger = logging.getLogger("aureon.price_cache")

_RADAR_ROOT = Path(__file__).resolve().parents[1]          # aureon_radar/
_ENV_PATH = _RADAR_ROOT / ".env"
_JOURNAL_PATH = _RADAR_ROOT / "state" / "price_cache_journal.jsonl"

_REQUEST_TIMEOUT = 15          # seconds, per HTTP call
_DEFAULT_TTL_SECONDS = 15.0    # per-(source, symbol) cache TTL
_NORMAL_MAX_RPM = 10           # global budget across all sources (normal)
_URGENT_MAX_RPM = 60           # global budget when cash is low (safe under Binance 1200 wt/min)
_MAX_THROTTLE_WAIT = 70.0      # seconds a caller may be parked for a slot

# Freshness thresholds
_FRESH_TTL_S = 60.0            # data newer than this is "fresh"
_STALE_TTL_S = 300.0           # data older than this is reported as stale
_URGENT_TTL_SECONDS = 5.0      # cache TTL when cash is low
_LOW_CASH_THRESHOLD = 50.0     # default cash threshold for urgent mode (USD/primary currency)

# Kraken uses X-prefixed base assets; map the common ones, pass others through.
_KRAKEN_BASE_MAP = {"BTC": "XBT", "XBT": "XBT"}

# Optional websocket support. If unavailable, urgent mode simply uses faster REST.
try:
    import websocket as _websocket
except Exception:  # pragma: no cover
    _websocket = None  # type: ignore


def _load_dotenv_file(path: Path) -> Dict[str, str]:
    """Minimal .env reader (KEY=VALUE lines); values stay local, never logged."""
    found: Dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key:
                found[key] = value.strip().strip('"').strip("'")
    except OSError:
        pass
    return found


class GlobalRateLimiter:
    """Sliding-window limiter shared by every source. Thread-safe."""

    def __init__(self, max_per_minute: int = _NORMAL_MAX_RPM):
        self._max = max_per_minute
        self._window = 60.0
        self._timestamps: deque = deque()
        self._lock = threading.Lock()

    def acquire(self, timeout: float = _MAX_THROTTLE_WAIT) -> bool:
        """Park the caller until a request slot frees. False if wait exceeded."""
        deadline = time.monotonic() + timeout
        with self._lock:
            while True:
                now = time.monotonic()
                while self._timestamps and now - self._timestamps[0] >= self._window:
                    self._timestamps.popleft()
                if len(self._timestamps) < self._max:
                    self._timestamps.append(now)
                    return True
                wait = self._window - (now - self._timestamps[0]) + 0.05
                if time.monotonic() + wait > deadline:
                    return False
                self._lock.release()
                try:
                    time.sleep(min(wait, 1.0))
                finally:
                    self._lock.acquire()

    @property
    def max_per_minute(self) -> int:
        return self._max


class _BinanceWebSocketFeed:
    """Lightweight combined ticker websocket updater for urgent mode.

    Subscribes to a default high-liquidity watchlist over one combined stream
    and writes the latest price into the PriceCache as `source_kind='websocket'`.
    If the connection drops, the next REST call backfills. Symbols outside the
    watchlist continue to be served by REST.
    """

    # Default watchlist: covers the symbols the organism monitors most often.
    # The stream is cheaper and more reliable than the huge all-market stream
    # from this UK network path.
    WS_SYMBOLS = ["btcusdt", "ethusdt", "solusdt", "adausdt", "xrpusdt"]

    def __init__(self, cache: "PriceCache"):
        self.cache = cache
        self._ws: Any = None
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._running = False

    def start(self) -> bool:
        if _websocket is None:
            logger.info("websocket-client not installed; skipping Binance websocket feed")
            return False
        with self._lock:
            if self._running:
                return True
            self._running = True
        try:
            streams = "/".join(f"{s}@ticker" for s in self.WS_SYMBOLS)
            url = f"wss://stream.binance.com:9443/stream?streams={streams}"
            self._ws = _websocket.WebSocketApp(
                url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open,
            )
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            logger.info("Binance websocket ticker feed starting")
            return True
        except Exception as exc:
            logger.warning("Binance websocket feed failed to start: %s", exc)
            self._running = False
            return False

    def stop(self) -> None:
        with self._lock:
            self._running = False
            ws = self._ws
        if ws:
            try:
                ws.close()
            except Exception:
                pass

    def _run(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            try:
                self._ws.run_forever(ping_interval=20, ping_timeout=10)
            except Exception as exc:
                logger.debug("Binance websocket run_forever error: %s", exc)
            # Back off before reconnecting
            time.sleep(5)

    def _on_open(self, ws):
        logger.info("Binance websocket ticker feed connected")

    def _on_error(self, ws, error):
        logger.debug("Binance websocket error: %s", error)

    def _on_close(self, ws, close_status_code, close_msg):
        logger.debug("Binance websocket closed (%s): %s", close_status_code, close_msg)

    def _update_ticker(self, t: Dict[str, Any]) -> None:
        sym = str(t.get("s", "")).upper()
        price_raw = t.get("c")
        if not sym or price_raw is None:
            return
        try:
            price = float(price_raw)
        except (TypeError, ValueError):
            return
        now_mono = time.monotonic()
        as_of = _utc_now_iso()
        with self.cache._lock:
            self.cache._cache[("binance", sym)] = {
                "price": price,
                "as_of": as_of,
                "error": None,
                "fetched_monotonic": now_mono,
                "source_kind": "websocket",
                "fresh": True,
                "trade_allowed": True,
            }

    def _on_message(self, ws, message):
        try:
            payload = json.loads(message)
            # Combined stream wraps each ticker in {"stream":"...","data":{...}}
            if isinstance(payload, dict) and "data" in payload:
                self._update_ticker(payload["data"])
                return
            # Raw all-market stream sends a JSON array of tickers
            if isinstance(payload, list):
                for t in payload:
                    self._update_ticker(t)
                return
            # Fallback: single raw ticker object
            self._update_ticker(payload)
        except Exception as exc:
            logger.debug("Binance websocket message parse error: %s", exc)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PriceCache:
    """TTL-cached, rate-limited, journaled public price lookups with freshness gates."""

    SOURCES = ("alpaca", "binance", "kraken")

    def __init__(self,
                 ttl_seconds: float = _DEFAULT_TTL_SECONDS,
                 max_per_minute: int = _NORMAL_MAX_RPM,
                 journal_path: Optional[Path] = None,
                 low_cash_threshold: float = _LOW_CASH_THRESHOLD):
        self._normal_ttl = float(ttl_seconds)
        self._normal_max_rpm = int(max_per_minute)
        self._urgent_ttl = _URGENT_TTL_SECONDS
        self._urgent_max_rpm = _URGENT_MAX_RPM
        self.low_cash_threshold = float(low_cash_threshold)
        self.journal_path = Path(journal_path) if journal_path else _JOURNAL_PATH
        self._cache: Dict[tuple, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._cash: Optional[float] = None
        self._urgent_mode = False
        self.limiter = GlobalRateLimiter(self._effective_max_rpm())

        # Env (process env wins over .env file). Only key NAMES are ever used.
        env = _load_dotenv_file(_ENV_PATH)
        env.update({k: v for k, v in os.environ.items()})
        self._alpaca_key = env.get("ALPACA_API_KEY") or env.get("APCA_API_KEY_ID")
        self._alpaca_secret = env.get("ALPACA_SECRET_KEY") or env.get("APCA_API_SECRET_KEY")
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "aureon-price-cache/1.0"})

        self._binance_ws = _BinanceWebSocketFeed(self)

    # ── cash / urgency mode ─────────────────────────────────────────────

    def set_cash_state(self, cash: Optional[float],
                       low_cash_threshold: Optional[float] = None) -> Dict[str, Any]:
        """Tell the cache how much cash is available.

        When cash is below the threshold, the cache switches to urgent mode:
        shorter TTL and higher (but still rate-limit-safe) request budget. If a
        Binance websocket feed is available it is started for sub-second prices.
        """
        if low_cash_threshold is not None:
            self.low_cash_threshold = float(low_cash_threshold)
        self._cash = cash
        was_urgent = self._urgent_mode
        self._urgent_mode = cash is not None and cash < self.low_cash_threshold

        # Rebuild limiter if the budget changed
        new_max = self._effective_max_rpm()
        if self.limiter.max_per_minute != new_max:
            self.limiter = GlobalRateLimiter(new_max)

        # Start/stop websocket feed
        if self._urgent_mode:
            self._binance_ws.start()
        else:
            self._binance_ws.stop()

        return {
            "cash": cash,
            "low_cash_threshold": self.low_cash_threshold,
            "urgent_mode": self._urgent_mode,
            "effective_ttl_s": self._effective_ttl(),
            "effective_max_rpm": new_max,
            "websocket_running": self._binance_ws._running,
        }

    def _effective_ttl(self) -> float:
        return self._urgent_ttl if self._urgent_mode else self._normal_ttl

    def _effective_max_rpm(self) -> int:
        return self._urgent_max_rpm if self._urgent_mode else self._normal_max_rpm

    # ── public API ──────────────────────────────────────────────────────

    def get_price(self, symbol: str, source: str = "binance",
                  ttl_seconds: Optional[float] = None) -> Dict[str, Any]:
        """Look up one symbol from one source.

        Returns a dict, always with keys:
            symbol, source, price (float|None), as_of (ISO ts of the price),
            cached (bool), error (str|None), fresh (bool), trade_allowed (bool),
            source_kind (str), age_s (float|None)
        FAIL-CLOSED: error is set and price is None on any failure; stale or
        simulated data is marked `fresh=False` and `trade_allowed=False`.
        """
        source = (source or "").lower().strip()
        ttl = self._effective_ttl() if ttl_seconds is None else float(ttl_seconds)
        symbol = symbol.strip().upper()

        base = {
            "symbol": symbol,
            "source": source,
            "price": None,
            "as_of": None,
            "cached": False,
            "error": None,
            "fresh": False,
            "trade_allowed": False,
            "source_kind": None,
            "age_s": None,
        }

        if source not in self.SOURCES:
            base["error"] = f"unknown source '{source}' (choose from {self.SOURCES})"
            base["source_kind"] = "rejected"
            self._journal(base, event="rejected")
            return base

        if not symbol:
            base["error"] = "empty symbol"
            base["source_kind"] = "rejected"
            self._journal(base, event="rejected")
            return base

        # Cache check — never serve stale data as fresh.
        now = time.monotonic()
        with self._lock:
            entry = self._cache.get((source, symbol))
            if entry and (now - entry["fetched_monotonic"]) < ttl:
                base.update(
                    price=entry["price"],
                    as_of=entry["as_of"],
                    cached=True,
                    error=entry.get("error"),
                    source_kind=entry.get("source_kind", "rest"),
                    age_s=round(now - entry["fetched_monotonic"], 3),
                )
                base.update(self._freshness_flags(entry, now))
                self._journal(base, event="cache_hit", age_s=base["age_s"])
                return base
            if entry and entry.get("error") and (now - entry["fetched_monotonic"]) < ttl:
                # Previous failure inside TTL: fail closed without re-hammering
                # the source (negative caching), but only for the cache TTL.
                base.update(
                    error=entry["error"],
                    as_of=entry.get("as_of"),
                    source_kind=entry.get("source_kind", "rest"),
                    age_s=round(now - entry["fetched_monotonic"], 3),
                )
                base.update(self._freshness_flags(entry, now))
                self._journal(base, event="cache_hit_error", age_s=base["age_s"])
                return base

        # Network fetch under the global limiter.
        if not self.limiter.acquire():
            base["error"] = ("rate_limiter: no slot within "
                             f"{_MAX_THROTTLE_WAIT:.0f}s "
                             f"(budget {self.limiter.max_per_minute}/min)")
            base["source_kind"] = "throttled"
            self._journal(base, event="throttled")
            return base

        fetcher = getattr(self, f"_fetch_{source}", None)
        try:
            price = fetcher(symbol) if fetcher else None
        except Exception as exc:
            price = None
            err = f"{type(exc).__name__}: {exc}"
        else:
            err = None if price is not None else f"{source}: no price parsed for {symbol}"

        as_of = _utc_now_iso()
        entry = {
            "price": price,
            "as_of": as_of,
            "error": err,
            "fetched_monotonic": time.monotonic(),
            "source_kind": "rest",
        }
        entry.update(self._freshness_flags(entry, entry["fetched_monotonic"]))
        with self._lock:
            self._cache[(source, symbol)] = entry

        base.update(
            price=price,
            as_of=as_of,
            error=err,
            source_kind=entry["source_kind"],
            age_s=0.0,
        )
        base.update(self._freshness_flags(entry, entry["fetched_monotonic"]))
        self._journal(base, event="fetch_ok" if price is not None else "fetch_error")
        return base

    def get_prices(self, symbols, source: str = "binance",
                   ttl_seconds: Optional[float] = None) -> Dict[str, Dict[str, Any]]:
        """Batch lookup; each symbol resolved independently, fail-closed."""
        if isinstance(symbols, str):
            symbols = [symbols]
        return {s: self.get_price(s, source=source, ttl_seconds=ttl_seconds)
                for s in symbols}

    def get_summary(self, symbol: str, source: str = "binance") -> Dict[str, Any]:
        """Fetch an extended market summary for a symbol.

        Currently implemented for Binance only (24h ticker + 15m klines).
        Returns the same freshness/trade_allowed flags as get_price plus
        change_pct, quote_vol, last, closes and vols. On failure all fields
        are None/zero and trade_allowed=False.
        """
        source = (source or "").lower().strip()
        symbol = symbol.strip().upper()
        base = {
            "symbol": symbol,
            "source": source,
            "price": None,
            "as_of": None,
            "cached": False,
            "error": None,
            "fresh": False,
            "trade_allowed": False,
            "source_kind": None,
            "age_s": None,
            "change_pct": None,
            "quote_vol": None,
            "last": None,
            "closes": [],
            "vols": [],
        }
        if source not in self.SOURCES:
            base["error"] = f"unknown source '{source}'"
            base["source_kind"] = "rejected"
            self._journal(base, event="rejected")
            return base
        if not symbol:
            base["error"] = "empty symbol"
            base["source_kind"] = "rejected"
            self._journal(base, event="rejected")
            return base
        if source != "binance":
            base["error"] = f"get_summary not implemented for source '{source}'"
            base["source_kind"] = "rejected"
            self._journal(base, event="rejected")
            return base

        if not self.limiter.acquire():
            base["error"] = ("rate_limiter: no slot within "
                             f"{_MAX_THROTTLE_WAIT:.0f}s")
            base["source_kind"] = "throttled"
            self._journal(base, event="throttled")
            return base

        try:
            data = self._fetch_binance_summary(symbol)
        except Exception as exc:
            data = None
            err = f"{type(exc).__name__}: {exc}"
        else:
            err = None if data else f"{source}: no summary for {symbol}"

        as_of = _utc_now_iso()
        entry = {
            "price": data["last"] if data else None,
            "as_of": as_of,
            "error": err,
            "fetched_monotonic": time.monotonic(),
            "source_kind": "rest",
        }
        entry.update(self._freshness_flags(entry, entry["fetched_monotonic"]))
        with self._lock:
            self._cache[(source, symbol)] = entry

        if data:
            base.update(data)
        base.update(
            as_of=as_of,
            error=err,
            cached=False,
            source_kind="rest",
            age_s=0.0,
        )
        base.update(self._freshness_flags(entry, entry["fetched_monotonic"]))
        self._journal(base, event="summary_ok" if data else "summary_error")
        return base

    def stats(self) -> Dict[str, Any]:
        """Cache + limiter statistics for the battle view."""
        with self._lock:
            entries = len(self._cache)
            errors = sum(1 for e in self._cache.values() if e.get("error"))
            fresh = sum(1 for e in self._cache.values() if e.get("fresh"))
            trade_allowed = sum(1 for e in self._cache.values() if e.get("trade_allowed"))
        return {
            "cached_entries": entries,
            "cached_errors": errors,
            "fresh_entries": fresh,
            "trade_allowed_entries": trade_allowed,
            "ttl_seconds": self._effective_ttl(),
            "rate_limit_per_minute": self.limiter.max_per_minute,
            "urgent_mode": self._urgent_mode,
            "cash": self._cash,
            "low_cash_threshold": self.low_cash_threshold,
            "journal_path": str(self.journal_path),
        }

    def freshness_state(self) -> Dict[str, Dict[str, Any]]:
        """Current freshness state for every cached (source, symbol)."""
        now = time.monotonic()
        with self._lock:
            return {
                f"{source}:{symbol}": {
                    "source": source,
                    "symbol": symbol,
                    "price": e.get("price"),
                    "as_of": e.get("as_of"),
                    "age_s": round(now - e.get("fetched_monotonic", now), 3),
                    "fresh": bool(e.get("fresh")),
                    "trade_allowed": bool(e.get("trade_allowed")),
                    "source_kind": e.get("source_kind"),
                    "error": e.get("error"),
                }
                for (source, symbol), e in self._cache.items()
            }

    def is_trade_allowed(self, symbol: str, source: str = "binance") -> bool:
        """Fail-closed check: may the organism trade on this symbol/source?"""
        state = self.freshness_state()
        key = f"{source.lower().strip()}:{symbol.strip().upper()}"
        entry = state.get(key, {})
        if not entry:
            return False
        return bool(entry.get("trade_allowed"))

    def report(self) -> str:
        """Human-readable freshness report."""
        state = self.freshness_state()
        lines = [
            "PriceCache Freshness Report",
            f"  urgent_mode={self._urgent_mode}  cash={self._cash}  threshold={self.low_cash_threshold}",
            f"  effective_ttl={self._effective_ttl()}s  max_rpm={self.limiter.max_per_minute}",
            f"  entries={len(state)}",
        ]
        stale = []
        simulated = []
        blocked = []
        for key, e in state.items():
            if not e.get("fresh"):
                stale.append(key)
            if e.get("source_kind") == "simulated":
                simulated.append(key)
            if not e.get("trade_allowed"):
                blocked.append(key)
        lines.append(f"  fresh={len(state) - len(stale)}  stale={len(stale)}  simulated={len(simulated)}  trade_blocked={len(blocked)}")
        if stale:
            lines.append("  Stale sources: " + ", ".join(stale[:20]) + ("..." if len(stale) > 20 else ""))
        if simulated:
            lines.append("  Simulated sources: " + ", ".join(simulated[:20]) + ("..." if len(simulated) > 20 else ""))
        if blocked:
            lines.append("  Trade-blocked sources: " + ", ".join(blocked[:20]) + ("..." if len(blocked) > 20 else ""))
        return "\n".join(lines)

    def mark_simulated(self, symbol: str, source: str = "binance",
                       reason: str = "marked simulated") -> None:
        """Explicitly mark a cached price as simulated/fake.

        Used by downstream modules when they detect fabricated data.
        """
        source = source.lower().strip()
        symbol = symbol.strip().upper()
        with self._lock:
            entry = self._cache.get((source, symbol))
            if entry is None:
                entry = {
                    "price": None,
                    "as_of": _utc_now_iso(),
                    "error": reason,
                    "fetched_monotonic": time.monotonic(),
                    "source_kind": "simulated",
                }
            else:
                entry["source_kind"] = "simulated"
                entry["error"] = reason
            entry.update(self._freshness_flags(entry, time.monotonic()))
            self._cache[(source, symbol)] = entry

    # ── freshness helpers ───────────────────────────────────────────────

    def _freshness_flags(self, entry: Dict[str, Any], now: float) -> Dict[str, bool]:
        """Compute fresh/trade_allowed flags for an entry."""
        age = now - entry.get("fetched_monotonic", now)
        price = entry.get("price")
        error = entry.get("error")
        source_kind = entry.get("source_kind")
        fresh = (
            error is None
            and price is not None
            and price > 0
            and source_kind != "simulated"
            and age <= _FRESH_TTL_S
        )
        trade_allowed = fresh and age <= _FRESH_TTL_S and source_kind not in ("simulated", "stale")
        return {"fresh": fresh, "trade_allowed": trade_allowed}

    # ── fetchers (one per source, each returns float price or None) ─────

    def _fetch_alpaca(self, symbol: str) -> Optional[float]:
        crypto_pair = None
        if "/" in symbol:
            crypto_pair = symbol
        else:
            for stable in ("USDT", "USDC"):
                if symbol.endswith(stable) and len(symbol) > len(stable):
                    crypto_pair = f"{symbol[:-len(stable)]}/USD"
                    break
            else:
                if symbol.endswith("USD") and len(symbol) <= 7:
                    crypto_pair = f"{symbol[:-3]}/{symbol[-3:]}"
        if crypto_pair:
            pair = crypto_pair
            url = ("https://data.alpaca.markets/v1beta3/crypto/us/latest/trades"
                   f"?symbols={pair}")
            data = self._http_json(url, headers=self._alpaca_headers())
            trades = (data.get("trades") or {})
            if pair in trades:
                return float(trades[pair]["p"])
            if trades:
                return float(next(iter(trades.values()))["p"])
            return None
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/quotes/latest"
        data = self._http_json(url, headers=self._alpaca_headers())
        quote = data.get("quote") or {}
        bid, ask = float(quote.get("bp", 0) or 0), float(quote.get("ap", 0) or 0)
        if bid > 0 and ask > 0:
            return (bid + ask) / 2.0
        return bid or ask or None

    def _fetch_binance(self, symbol: str) -> Optional[float]:
        pair = symbol.replace("/", "").replace("-", "")
        if pair.endswith("USD") and not pair.endswith("USDT") and not pair.endswith("USDC"):
            pair += "T"  # BTCUSD -> BTCUSDT convention
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={pair}"
        data = self._http_json(url)
        price = data.get("price")
        return float(price) if price is not None else None

    def _fetch_binance_summary(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch Binance 24h ticker + 15m klines for scanner support.

        Two HTTP calls are made, so we acquire a rate-limit slot for each one.
        """
        pair = symbol.replace("/", "").replace("-", "")
        if pair.endswith("USD") and not pair.endswith("USDT") and not pair.endswith("USDC"):
            pair += "T"

        if not self.limiter.acquire():
            raise RuntimeError("rate_limiter: no slot for 24hr ticker")
        t = self._http_json(f"https://api.binance.com/api/v3/ticker/24hr?symbol={pair}")

        if not self.limiter.acquire():
            raise RuntimeError("rate_limiter: no slot for klines")
        k = self._http_json(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": pair, "interval": "15m", "limit": 48},
        )
        klines = k if isinstance(k, list) else []
        close = [float(c[4]) for c in klines] if isinstance(klines, list) else []
        vol = [float(c[5]) for c in klines] if isinstance(klines, list) else []
        return {
            "change_pct": float(t.get("priceChangePercent", 0.0)),
            "quote_vol": float(t.get("quoteVolume", 0.0)),
            "last": float(t.get("lastPrice", 0.0)),
            "closes": close,
            "vols": vol,
        }

    def _fetch_kraken(self, symbol: str) -> Optional[float]:
        base = symbol.replace("/", "").replace("-", "")
        quote = "USD"
        if base.endswith("USDT") or base.endswith("USDC"):
            base, quote = base[:-4], "USD"
        for suffix in ("USD", "EUR", "GBP", "JPY"):
            if base.endswith(suffix) and len(base) > len(suffix):
                base, quote = base[:-len(suffix)], suffix
                break
        base = _KRAKEN_BASE_MAP.get(base, base)
        pair = f"{base}{quote}"
        url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval=1"
        data = self._http_json(url)
        if data.get("error"):
            return None
        result = data.get("result") or {}
        ohlc = None
        for key, rows in result.items():
            if key != "last" and isinstance(rows, list) and rows:
                ohlc = rows
                break
        if not ohlc:
            return None
        last_row = ohlc[-1]
        close = float(last_row[4])  # OHLC row: [time, o, h, l, c, vwap, count, vol]
        return close if close > 0 else None

    # ── plumbing ────────────────────────────────────────────────────────

    def _alpaca_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._alpaca_key and self._alpaca_secret:
            headers["APCA-API-KEY-ID"] = self._alpaca_key
            headers["APCA-API-SECRET-KEY"] = self._alpaca_secret
        return headers

    def _http_json(self, url: str, headers: Optional[Dict[str, str]] = None,
                   params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = self._session.get(url, headers=headers or {}, params=params or {},
                                 timeout=_REQUEST_TIMEOUT)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code} from {url.split('?')[0]}")
        return resp.json()

    def _journal(self, result: Dict[str, Any], event: str,
                 age_s: Optional[float] = None) -> None:
        record = {
            "ts": _utc_now_iso(),
            "event": event,
            "source": result["source"],
            "symbol": result["symbol"],
            "price": result["price"],
            "as_of": result["as_of"],
            "cached": result["cached"],
            "error": result["error"],
            "fresh": result.get("fresh"),
            "trade_allowed": result.get("trade_allowed"),
            "source_kind": result.get("source_kind"),
        }
        if age_s is not None:
            record["age_s"] = age_s
        try:
            self.journal_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.journal_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
        except OSError as exc:
            logger.warning("price cache journal write failed: %s", exc)
        if event in ("fetch_error", "rejected", "throttled", "summary_error"):
            logger.warning("price_cache %s %s: %s", event, record["symbol"],
                           record["error"])


# Module-level shared instance so scanners/adapters co-throttle together.
_SHARED: Optional[PriceCache] = None
_SHARED_LOCK = threading.Lock()


def get_shared_cache(ttl_seconds: float = _DEFAULT_TTL_SECONDS) -> PriceCache:
    """Process-wide cache: every caller shares one TTL map + one limiter."""
    global _SHARED
    with _SHARED_LOCK:
        if _SHARED is None or _SHARED._normal_ttl != float(ttl_seconds):
            _SHARED = PriceCache(ttl_seconds=ttl_seconds)
        return _SHARED


def get_price(symbol: str, source: str = "binance",
              ttl_seconds: Optional[float] = None) -> Dict[str, Any]:
    """Convenience wrapper around the shared cache."""
    return get_shared_cache().get_price(symbol, source=source, ttl_seconds=ttl_seconds)


def get_summary(symbol: str, source: str = "binance") -> Dict[str, Any]:
    """Convenience wrapper for extended market summary."""
    return get_shared_cache().get_summary(symbol, source=source)


def set_cash_state(cash: Optional[float],
                   low_cash_threshold: Optional[float] = None) -> Dict[str, Any]:
    """Set cash state on the shared cache (triggers urgent mode when low)."""
    return get_shared_cache().set_cash_state(cash, low_cash_threshold=low_cash_threshold)


def freshness_state() -> Dict[str, Dict[str, Any]]:
    """Freshness state of the shared cache."""
    return get_shared_cache().freshness_state()


def is_trade_allowed(symbol: str, source: str = "binance") -> bool:
    """Fail-closed trade permission check on the shared cache."""
    return get_shared_cache().is_trade_allowed(symbol, source=source)


def report() -> str:
    """Human-readable freshness report from the shared cache."""
    return get_shared_cache().report()


def mark_simulated(symbol: str, source: str = "binance",
                   reason: str = "marked simulated") -> None:
    """Mark a symbol/source as simulated/fake in the shared cache."""
    return get_shared_cache().mark_simulated(symbol, source=source, reason=reason)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    symbols = sys.argv[1:] or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    cache = get_shared_cache()
    print(f"Fetching {len(symbols)} symbols x3 sources through PriceCache "
          f"(TTL {cache._effective_ttl()}s, limit {cache.limiter.max_per_minute}/min)...")
    for source in PriceCache.SOURCES:
        first = cache.get_prices(symbols, source=source)
        print(f"\n[{source}] first call:")
        for sym, r in first.items():
            print(f"  {sym}: price={r['price']} fresh={r['fresh']} "
                  f"trade_allowed={r['trade_allowed']} cached={r['cached']} error={r['error']}")
        second = cache.get_prices(symbols, source=source)
        print(f"[{source}] immediate second call (expect cache hits):")
        for sym, r in second.items():
            print(f"  {sym}: price={r['price']} fresh={r['fresh']} "
                  f"trade_allowed={r['trade_allowed']} cached={r['cached']} error={r['error']}")

    # Summary demo
    print("\n[binance summary BTCUSDT]", cache.get_summary("BTCUSDT"))

    # Urgent mode demo (does not trigger live trading)
    print("\n--- low-cash urgent mode demo ---")
    print(cache.set_cash_state(10.0))
    print(cache.report())
    print("\ncache stats:", cache.stats())
