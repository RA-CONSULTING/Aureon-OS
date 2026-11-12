"""Shared market-data feed: one poller per exchange, one locked snapshot.

Capital, Binance, Kraken and Alpaca quotes are written into ONE snapshot
file under the repo's gitignored ``state/`` directory. The Queen, the
metacognition monitor and :mod:`aureon.data_feeds.unified_market_cache`
read that file through :func:`read_snapshot` / :func:`fresh_quotes`
instead of each calling the exchanges themselves. Reading never makes a
network call.

Read-only by construction:

* This module imports no exchange client, order, trade or execution code.
  It talks HTTP through ``requests.get`` only, and every request passes
  :func:`_assert_read_only` first (GET only, market-data hosts only, order
  paths refused).
* Binance and Kraken use public endpoints with no key.
* Alpaca crypto quotes come from the market-data host. Crypto data does not
  need a key; if ``ALPACA_API_KEY``/``ALPACA_SECRET_KEY`` are set they are
  sent to ``data.alpaca.markets`` only, which raises the data rate limit.
  They never go to the trading host.
* Capital has no public market data. The feed does not log in to Capital.
  It reads the quote cache already written by
  ``aureon/exchanges/capital_market_monitor.py`` (``CAPITAL_MONITOR_CACHE_PATH``,
  default ``ws_cache/capital_monitor.json``), so it adds zero Capital
  requests. A ``reader`` callable can be injected instead.
  TODO(#319): once the shared Capital pacer from PR #319 is on main, inject
  a reader here that goes through that pacer from the process that owns the
  Capital session. Do not open a second Capital session from this module.

Rate limits used for the default intervals (each poller makes one request
per cycle):

* Binance ``GET /api/v3/ticker/24hr`` with 1-20 ``symbols`` costs weight 2
  against the 6,000 REQUEST_WEIGHT per minute per IP limit (Binance spot
  REST API docs). Every 2 s = 60 weight/min.
* Kraken public endpoints: about 1 call/s sustained, the same budget as the
  public bucket in ``aureon/exchanges/kraken_client.py`` (rate=1.0). Every
  2 s = 0.5 call/s.
* Alpaca: 200 requests/min per key (Alpaca docs; ``alpaca_client.py``
  "Alpaca's 200/min limit"). Every 3 s = 20/min.
* Capital: local file read every 5 s, no HTTP.

A venue that fails, is rate limited, or is older than its ``max_age_s`` is
reported as ``error``, ``stale`` or ``missing``. Its quotes are not handed
out as fresh, and no value is ever filled in from a clock, a default or a
previous run.
"""
from __future__ import annotations

import argparse
import contextlib
import errno
import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

import requests

try:  # POSIX
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - Windows
    fcntl = None  # type: ignore
try:  # Windows
    import msvcrt  # type: ignore
except ImportError:
    msvcrt = None  # type: ignore

logger = logging.getLogger(__name__)

SCHEMA = "aureon.shared_market_feed.v1"
VENUES = ("capital", "binance", "kraken", "alpaca")
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SNAPSHOT_PATH = _REPO_ROOT / "state" / "shared_market_feed.json"
DEFAULT_CAPITAL_MONITOR_PATH = Path("ws_cache") / "capital_monitor.json"

BINANCE_URL = "https://api.binance.com/api/v3/ticker/24hr"
KRAKEN_URL = "https://api.kraken.com/0/public/Ticker"
ALPACA_DATA_URL = "https://data.alpaca.markets/v1beta3/crypto/us/latest/quotes"

# base symbol -> venue pair
BINANCE_PAIRS = {"BTC": "BTCUSDT", "ETH": "ETHUSDT", "SOL": "SOLUSDT", "XRP": "XRPUSDT", "DOGE": "DOGEUSDT"}
# Kraken returns these canonical keys for the pairs requested.
KRAKEN_PAIRS = {"BTC": "XXBTZUSD", "ETH": "XETHZUSD", "SOL": "SOLUSD", "XRP": "XXRPZUSD", "DOGE": "XDGUSD"}
ALPACA_PAIRS = {"BTC": "BTC/USD", "ETH": "ETH/USD", "SOL": "SOL/USD", "XRP": "XRP/USD", "DOGE": "DOGE/USD"}

DEFAULT_INTERVALS = {"binance": 2.0, "kraken": 2.0, "alpaca": 3.0, "capital": 5.0}
BINANCE_MAX_SYMBOLS_AT_WEIGHT_2 = 20

_ALLOWED_HOSTS = ("api.binance.com", "api.kraken.com", "data.alpaca.markets")
_ORDER_PATH_MARKERS = (
    "/order", "/orders", "/workingorders", "/positions", "/confirms",
    "addorder", "cancelorder", "editorder", "cancelall", "/private/",
    "/sapi/", "/account", "/session",
)


class FeedLockUnavailable(RuntimeError):
    """No file lock primitive (fcntl or msvcrt) works on this platform."""


class FeedLockTimeout(RuntimeError):
    """The snapshot lock was held by someone else for longer than the timeout."""


class ReadOnlyViolation(RuntimeError):
    """A request that is not a market-data GET was about to be sent."""


# ── paths ───────────────────────────────────────────────────────────────────
def snapshot_path(path: Optional[os.PathLike | str] = None) -> Path:
    if path is not None:
        return Path(path)
    env = os.environ.get("AUREON_SHARED_MARKET_FEED_PATH")
    return Path(env) if env else DEFAULT_SNAPSHOT_PATH


def _lock_path(path: Path) -> Path:
    return path.with_name(path.name + ".lock")


# ── locking ─────────────────────────────────────────────────────────────────
@contextlib.contextmanager
def _locked(path: Path, *, exclusive: bool, timeout: float) -> Iterator[None]:
    """Hold an fcntl flock (POSIX) or msvcrt lock (Windows) on ``<path>.lock``."""
    if fcntl is None and msvcrt is None:
        raise FeedLockUnavailable("no fcntl or msvcrt lock available")
    lock = _lock_path(path)
    lock.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock), os.O_RDWR | os.O_CREAT, 0o600)
    deadline = time.monotonic() + max(0.0, timeout)
    try:
        if fcntl is not None:
            flag = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            while True:
                try:
                    fcntl.flock(fd, flag | fcntl.LOCK_NB)
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EAGAIN, errno.EACCES, errno.EWOULDBLOCK):
                        raise
                    if time.monotonic() >= deadline:
                        raise FeedLockTimeout(str(lock)) from exc
                    time.sleep(0.005)
            try:
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
        else:
            # msvcrt has no shared lock; readers take the same byte lock.
            while True:
                try:
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if time.monotonic() >= deadline:
                        raise FeedLockTimeout(str(lock)) from exc
                    time.sleep(0.005)
            try:
                yield
            finally:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    finally:
        os.close(fd)


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _atomic_write(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fd = -1
            json.dump(data, fh, ensure_ascii=False, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        if fd != -1:
            os.close(fd)
        if tmp.exists():
            tmp.unlink()


def write_venue(entry: Dict[str, Any], path: Optional[os.PathLike | str] = None,
                *, lock_timeout: float = 5.0) -> None:
    """Merge one venue entry into the shared snapshot under an exclusive lock.

    Raises FeedLockUnavailable / FeedLockTimeout instead of writing unlocked.
    """
    venue = str(entry.get("venue") or "")
    if venue not in VENUES:
        raise ValueError(f"unknown venue {venue!r}")
    target = snapshot_path(path)
    with _locked(target, exclusive=True, timeout=lock_timeout):
        current = _read_json(target) or {}
        venues = current.get("venues") if isinstance(current.get("venues"), dict) else {}
        venues[venue] = entry
        _atomic_write(target, {"schema": SCHEMA, "updated_at": time.time(), "venues": venues})


# ── reading ─────────────────────────────────────────────────────────────────
def _num(value: Any) -> Optional[float]:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out and out not in (float("inf"), float("-inf")) else None


def _quote_ts(quote: Dict[str, Any], venue_ts: float) -> float:
    ts = _num(quote.get("provider_ts"))
    return ts if ts is not None else venue_ts


def _venue_view(venue: str, entry: Optional[Dict[str, Any]], now: float) -> Dict[str, Any]:
    if not isinstance(entry, dict):
        return {"venue": venue, "state": "missing", "quotes": {}, "age_s": None,
                "fetched_at": None, "source": None, "error": "no_entry"}
    fetched_at = _num(entry.get("fetched_at"))
    max_age = _num(entry.get("max_age_s")) or 0.0
    age = None if fetched_at is None else max(0.0, now - fetched_at)
    view = {
        "venue": venue,
        "source": entry.get("source"),
        "fetched_at": fetched_at,
        "last_ok_at": _num(entry.get("last_ok_at")),
        "age_s": age,
        "max_age_s": max_age,
        "error": entry.get("error"),
        "quotes": {},
        "stale_quotes": [],
    }
    if entry.get("status") != "ok" or fetched_at is None:
        view["state"] = "error" if entry.get("status") == "error" else "missing"
        return view
    if age is None or age > max_age or fetched_at > now + 5.0:
        view["state"] = "stale"
        return view
    view["state"] = "fresh"
    for symbol, quote in (entry.get("quotes") or {}).items():
        if not isinstance(quote, dict):
            continue
        qts = _quote_ts(quote, fetched_at)
        if now - qts > max(max_age, _num(entry.get("quote_max_age_s")) or max_age):
            view["stale_quotes"].append(symbol)
            continue
        view["quotes"][symbol] = dict(quote)
    return view


def read_snapshot(path: Optional[os.PathLike | str] = None, *, now: Optional[float] = None,
                  lock_timeout: float = 2.0) -> Dict[str, Any]:
    """Return every venue with a state of fresh, stale, error or missing.

    Only ``fresh`` venues carry quotes. No network call is made.
    """
    target = snapshot_path(path)
    try:
        with _locked(target, exclusive=False, timeout=lock_timeout):
            raw = _read_json(target)
    except FeedLockUnavailable:
        # Writers refuse without a lock; the file is only ever os.replace()d,
        # so an unlocked read still sees one whole snapshot.
        raw = _read_json(target)
    except FeedLockTimeout:
        raw = None
    ts = time.time() if now is None else now
    venues = (raw or {}).get("venues") if isinstance((raw or {}).get("venues"), dict) else {}
    return {
        "schema": SCHEMA,
        "path": str(target),
        "read_at": ts,
        "file_present": raw is not None,
        "venues": {v: _venue_view(v, venues.get(v), ts) for v in VENUES},
    }


def fresh_quotes(path: Optional[os.PathLike | str] = None, *, now: Optional[float] = None) -> List[Dict[str, Any]]:
    """Flat list of fresh quotes, each tagged with venue and timestamp."""
    snap = read_snapshot(path, now=now)
    rows: List[Dict[str, Any]] = []
    for venue, view in snap["venues"].items():
        if view["state"] != "fresh":
            continue
        for symbol, quote in view["quotes"].items():
            row = dict(quote)
            row.setdefault("base", symbol)
            row["venue"] = venue
            row["venue_source"] = view["source"]
            row["ts"] = _quote_ts(quote, view["fetched_at"])
            rows.append(row)
    return rows


def read_venue_quote(venue: str, base: str, path: Optional[os.PathLike | str] = None) -> Optional[Dict[str, Any]]:
    view = read_snapshot(path)["venues"].get(venue) or {}
    if view.get("state") != "fresh":
        return None
    quote = (view.get("quotes") or {}).get(base.upper())
    if not quote:
        return None
    out = dict(quote)
    out["venue"] = venue
    out["fetched_at"] = view["fetched_at"]
    out["source"] = view["source"]
    return out


def feed_health(path: Optional[os.PathLike | str] = None) -> Dict[str, Dict[str, Any]]:
    snap = read_snapshot(path)
    return {
        v: {k: view.get(k) for k in ("state", "source", "age_s", "max_age_s", "error")}
        | {"quote_count": len(view.get("quotes") or {})}
        for v, view in snap["venues"].items()
    }


# ── HTTP (read-only) ────────────────────────────────────────────────────────
def _assert_read_only(method: str, url: str) -> None:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    lowered = parsed.path.lower()
    if method.upper() != "GET":
        raise ReadOnlyViolation(f"{method} refused: feed is GET-only")
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS:
        raise ReadOnlyViolation(f"host {parsed.hostname!r} is not a market-data host")
    if any(marker in lowered for marker in _ORDER_PATH_MARKERS):
        raise ReadOnlyViolation(f"path {parsed.path!r} is not a market-data path")


class _HttpStatusError(RuntimeError):
    def __init__(self, status: int, retry_after: Optional[float]):
        super().__init__(f"http_{status}")
        self.status = status
        self.retry_after = retry_after


def _http_get_json(url: str, *, params: Optional[Dict[str, Any]] = None,
                   headers: Optional[Dict[str, str]] = None, timeout: float = 8.0) -> Any:
    _assert_read_only("GET", url)
    # Never follow redirects: a 3xx could point the read at a host the
    # read-only guard above never saw, so it is treated as a failed read.
    resp = requests.get(url, params=params, headers=headers or {}, timeout=timeout,
                        allow_redirects=False)
    status = int(getattr(resp, "status_code", 0) or 0)
    if status != 200:
        retry = _num((getattr(resp, "headers", None) or {}).get("Retry-After"))
        raise _HttpStatusError(status, retry)
    return resp.json()


# ── pollers ─────────────────────────────────────────────────────────────────
class VenuePoller:
    venue = ""

    def __init__(self, *, interval_s: Optional[float] = None, max_age_s: Optional[float] = None,
                 path: Optional[os.PathLike | str] = None, lock_timeout: float = 5.0):
        self.interval_s = float(interval_s if interval_s is not None else DEFAULT_INTERVALS[self.venue])
        self.max_age_s = float(max_age_s if max_age_s is not None else self.interval_s * 3 + 2)
        self.path = path
        self.lock_timeout = lock_timeout
        self.backoff_until = 0.0
        self.last_ok_at: Optional[float] = None

    def fetch(self) -> Dict[str, Any]:  # returns {"source", "quotes", optional "fetched_at"}
        raise NotImplementedError

    def poll_once(self) -> Dict[str, Any]:
        now = time.time()
        entry: Dict[str, Any] = {"venue": self.venue, "max_age_s": self.max_age_s, "last_ok_at": self.last_ok_at}
        if now < self.backoff_until:
            entry.update(status="error", error="backoff", fetched_at=None, quotes={},
                         backoff_until=self.backoff_until, source=None)
            write_venue(entry, self.path, lock_timeout=self.lock_timeout)
            return entry
        try:
            got = self.fetch()
        except _HttpStatusError as exc:
            if exc.status in (418, 429):
                self.backoff_until = time.time() + (exc.retry_after if exc.retry_after is not None else 60.0)
                entry["backoff_until"] = self.backoff_until
            entry.update(status="error", error=str(exc), fetched_at=None, quotes={}, source=None)
        except Exception as exc:  # network, parse, missing cache file
            entry.update(status="error", error=f"{type(exc).__name__}: {exc}"[:300],
                         fetched_at=None, quotes={}, source=None)
        else:
            quotes = got.get("quotes") or {}
            if quotes:
                fetched_at = _num(got.get("fetched_at")) or time.time()
                self.last_ok_at = fetched_at
                entry.update(status="ok", error=None, fetched_at=fetched_at, quotes=quotes,
                             source=got.get("source"), last_ok_at=fetched_at)
                if got.get("quote_max_age_s") is not None:
                    entry["quote_max_age_s"] = got["quote_max_age_s"]
            else:
                entry.update(status="error", error="no_quotes", fetched_at=None, quotes={},
                             source=got.get("source"))
        write_venue(entry, self.path, lock_timeout=self.lock_timeout)
        return entry


class BinancePoller(VenuePoller):
    venue = "binance"

    def __init__(self, pairs: Optional[Dict[str, str]] = None, **kw: Any):
        super().__init__(**kw)
        self.pairs = dict(pairs or BINANCE_PAIRS)
        if len(self.pairs) > BINANCE_MAX_SYMBOLS_AT_WEIGHT_2:
            raise ValueError("more than 20 symbols raises /ticker/24hr weight from 2 to 40")

    def fetch(self) -> Dict[str, Any]:
        symbols = json.dumps(list(self.pairs.values()), separators=(",", ":"))
        payload = _http_get_json(BINANCE_URL, params={"symbols": symbols})
        by_pair = {pair: base for base, pair in self.pairs.items()}
        quotes: Dict[str, Any] = {}
        for row in payload if isinstance(payload, list) else []:
            base = by_pair.get(str(row.get("symbol")))
            bid, ask, last = _num(row.get("bidPrice")), _num(row.get("askPrice")), _num(row.get("lastPrice"))
            if not base or not last or last <= 0:
                continue
            quotes[base] = {
                "base": base, "pair": row.get("symbol"), "price": last, "price_basis": "last",
                "bid": bid, "ask": ask, "change_24h_pct": _num(row.get("priceChangePercent")),
                "volume_24h_quote": _num(row.get("quoteVolume")),
                "provider_ts": (_num(row.get("closeTime")) or 0) / 1000.0 or None,
            }
        return {"source": "binance:GET /api/v3/ticker/24hr (public)", "quotes": quotes}


class KrakenPoller(VenuePoller):
    venue = "kraken"

    def __init__(self, pairs: Optional[Dict[str, str]] = None, **kw: Any):
        super().__init__(**kw)
        self.pairs = dict(pairs or KRAKEN_PAIRS)

    def fetch(self) -> Dict[str, Any]:
        payload = _http_get_json(KRAKEN_URL, params={"pair": ",".join(self.pairs.values())})
        if not isinstance(payload, dict) or payload.get("error"):
            raise RuntimeError(f"kraken_error: {payload.get('error') if isinstance(payload, dict) else 'bad payload'}")
        by_pair = {pair: base for base, pair in self.pairs.items()}
        quotes: Dict[str, Any] = {}
        for pair, row in (payload.get("result") or {}).items():
            base = by_pair.get(str(pair))
            if not base or not isinstance(row, dict):
                continue
            last = _num((row.get("c") or [None])[0])
            if not last or last <= 0:
                continue
            quotes[base] = {
                "base": base, "pair": pair, "price": last, "price_basis": "last",
                "bid": _num((row.get("b") or [None])[0]), "ask": _num((row.get("a") or [None])[0]),
                "change_24h_pct": None, "volume_24h_base": _num((row.get("v") or [None, None])[1]),
                "provider_ts": None,
            }
        return {"source": "kraken:GET /0/public/Ticker (public)", "quotes": quotes}


def _alpaca_data_headers() -> Dict[str, str]:
    key = os.environ.get("ALPACA_API_KEY") or os.environ.get("ALPACA_KEY")
    secret = os.environ.get("ALPACA_SECRET_KEY") or os.environ.get("ALPACA_API_SECRET") or os.environ.get("ALPACA_SECRET")
    if key and secret:
        return {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret}
    return {}


def _iso_ts(value: Any) -> Optional[float]:
    if not isinstance(value, str) or not value:
        return None
    text = value.replace("Z", "+00:00")
    if "." in text:  # trim nanoseconds to microseconds for fromisoformat
        head, _, tail = text.partition(".")
        digits = "".join(ch for ch in tail if ch.isdigit())
        zone = tail[len(digits):]
        text = f"{head}.{digits[:6]}{zone}"
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


class AlpacaPoller(VenuePoller):
    venue = "alpaca"

    def __init__(self, pairs: Optional[Dict[str, str]] = None, **kw: Any):
        super().__init__(**kw)
        self.pairs = dict(pairs or ALPACA_PAIRS)

    def fetch(self) -> Dict[str, Any]:
        headers = _alpaca_data_headers()
        payload = _http_get_json(ALPACA_DATA_URL, params={"symbols": ",".join(self.pairs.values())},
                                 headers=headers)
        rows = payload.get("quotes") if isinstance(payload, dict) else None
        by_pair = {pair: base for base, pair in self.pairs.items()}
        quotes: Dict[str, Any] = {}
        for pair, row in (rows or {}).items():
            base = by_pair.get(str(pair))
            if not base or not isinstance(row, dict):
                continue
            bid, ask = _num(row.get("bp")), _num(row.get("ap"))
            if not bid or not ask or bid <= 0 or ask < bid:
                continue
            quotes[base] = {
                "base": base, "pair": pair, "price": (bid + ask) / 2.0, "price_basis": "quote_mid",
                "bid": bid, "ask": ask, "change_24h_pct": None, "provider_ts": _iso_ts(row.get("t")),
            }
        auth = "keyed data read" if headers else "no key"
        return {"source": f"alpaca:GET data.alpaca.markets /v1beta3/crypto/us/latest/quotes ({auth})",
                "quotes": quotes}


class CapitalPoller(VenuePoller):
    """Capital quotes from the existing monitor cache, or from an injected reader.

    TODO(#319): inject ``reader`` backed by the #319 shared pacer once it is
    merged; until then this makes no Capital request at all.
    """

    venue = "capital"

    def __init__(self, reader: Optional[Callable[[], Dict[str, Any]]] = None,
                 monitor_path: Optional[os.PathLike | str] = None, **kw: Any):
        super().__init__(**kw)
        self.reader = reader
        self.monitor_path = Path(monitor_path or os.environ.get("CAPITAL_MONITOR_CACHE_PATH")
                                 or DEFAULT_CAPITAL_MONITOR_PATH)
        self.quote_max_age_s = 300.0  # capital_market_monitor.QUOTE_MAX_AGE_SECONDS

    def fetch(self) -> Dict[str, Any]:
        if self.reader is not None:
            return self.reader()
        payload = _read_json(self.monitor_path)
        if payload is None:
            raise FileNotFoundError(f"capital monitor cache missing: {self.monitor_path}")
        generated_at = _num(payload.get("generated_at"))
        if generated_at is None:
            raise ValueError("capital monitor cache has no generated_at")
        quotes: Dict[str, Any] = {}
        for symbol, row in (payload.get("prices") or {}).items():
            if not isinstance(row, dict) or row.get("generated_values") is not False:
                continue
            price, bid, ask = _num(row.get("price")), _num(row.get("bid")), _num(row.get("ask"))
            ts = _num(row.get("source_timestamp"))
            if not price or price <= 0 or ts is None:
                continue
            base = str(symbol).upper()
            quotes[base] = {
                "base": base, "pair": row.get("epic") or base, "price": price, "price_basis": "provider",
                "bid": bid, "ask": ask, "change_24h_pct": _num(row.get("change_pct")),
                "provider_ts": ts, "quote_source": row.get("source"),
            }
        return {
            "source": f"capital_market_monitor cache ({self.monitor_path}); no Capital request from feed",
            "quotes": quotes,
            "fetched_at": generated_at,  # the monitor's write time, not ours
            "quote_max_age_s": self.quote_max_age_s,
        }


POLLERS = {"binance": BinancePoller, "kraken": KrakenPoller, "alpaca": AlpacaPoller, "capital": CapitalPoller}


def _loop(poller: VenuePoller, stop: threading.Event) -> None:
    while not stop.is_set():
        started = time.monotonic()
        try:
            poller.poll_once()
        except (FeedLockUnavailable, FeedLockTimeout) as exc:
            logger.warning("shared_market_feed %s: snapshot not written, lock problem: %s", poller.venue, exc)
        wait = poller.interval_s - (time.monotonic() - started)
        if poller.backoff_until > time.time():
            wait = max(wait, poller.backoff_until - time.time())
        stop.wait(max(0.05, wait))


def run_feed(venues: Optional[List[str]] = None, *, stop: Optional[threading.Event] = None,
             path: Optional[os.PathLike | str] = None, pollers: Optional[List[VenuePoller]] = None) -> List[threading.Thread]:
    """Start one polling thread per venue. Returns the threads (daemon)."""
    stop = stop or threading.Event()
    active = pollers or [POLLERS[v](path=path) for v in (venues or list(VENUES))]
    threads = []
    for poller in active:
        t = threading.Thread(target=_loop, args=(poller, stop), name=f"shared_feed_{poller.venue}", daemon=True)
        t.start()
        threads.append(t)
    return threads


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Shared read-only market-data feed")
    parser.add_argument("--venues", default=",".join(VENUES))
    parser.add_argument("--path", default=None)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    stop = threading.Event()
    threads = run_feed([v.strip() for v in args.venues.split(",") if v.strip()], stop=stop, path=args.path)
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(1.0)
    except KeyboardInterrupt:
        stop.set()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
