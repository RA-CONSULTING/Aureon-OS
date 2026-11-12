"""Shared market feed: one poller per venue, one locked snapshot, many readers.

Offline. Every HTTP call goes through a recorder patched onto
``requests.sessions.Session.request``; nothing reaches the network. Keys are
fake. The tests count real (mocked) calls per exchange and prove readers add
none, that stale or failed venues are reported as such, that the snapshot is
locked, and that nothing touches an order endpoint or imports order code.
"""
from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import threading
import time
import types
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pytest
import requests

from aureon.data_feeds import shared_market_feed as feed

REPO_ROOT = Path(__file__).resolve().parents[1]

ORDER_ENDPOINT_PATTERNS = [
    (None, re.compile(r"/positions(/|$|\?)")),          # Capital /positions POST/PUT/DELETE
    (None, re.compile(r"/workingorders")),               # Capital working orders
    (None, re.compile(r"/confirms/")),                   # Capital deal confirms
    (None, re.compile(r"/session(/|$|\?)")),             # Capital login
    (None, re.compile(r"/v2/orders")),                   # Alpaca orders
    (None, re.compile(r"/v2/positions")),                # Alpaca close position
    (None, re.compile(r"/api/v3/order")),                # Binance order / order/test / orderList
    (None, re.compile(r"/sapi/")),                       # Binance margin/wallet
    (None, re.compile(r"/0/private/")),                  # Kraken AddOrder, CancelOrder, Balance...
    (None, re.compile(r"(?i)addorder|cancelorder|editorder|cancelall")),
]


def _now_ms() -> int:
    return int(time.time() * 1000)


def _payload_for(host: str):
    now = time.time()
    if host == "api.binance.com":
        rows = []
        for base, pair in feed.BINANCE_PAIRS.items():
            rows.append({
                "symbol": pair, "lastPrice": "100.5", "bidPrice": "100.4", "askPrice": "100.6",
                "priceChangePercent": "-1.25", "quoteVolume": "123456.0", "closeTime": _now_ms(),
            })
        rows[0].update(lastPrice="65000.0", bidPrice="64999.0", askPrice="65001.0")
        return rows
    if host == "api.kraken.com":
        return {"error": [], "result": {
            pair: {"a": ["101.0", "1", "1.000"], "b": ["100.0", "1", "1.000"],
                   "c": ["100.5", "0.1"], "v": ["10.0", "20.0"]}
            for pair in feed.KRAKEN_PAIRS.values()}}
    if host == "data.alpaca.markets":
        t = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f") + "123Z"
        return {"quotes": {pair: {"bp": 100.0, "ap": 101.0, "bs": 1, "as": 1, "t": t}
                           for pair in feed.ALPACA_PAIRS.values()}}
    raise AssertionError(f"unexpected host {host}")


class Recorder:
    def __init__(self):
        self.calls = []
        self.lock = threading.Lock()
        self.fail_hosts = set()
        self.status = {}
        self.retry_after = {}

    def __call__(self, session, method, url, params=None, headers=None, **kwargs):
        full = requests.Request(method, url, params=params).prepare().url
        host = urlparse(full).hostname
        with self.lock:
            self.calls.append({"method": method.upper(), "url": full, "host": host,
                               "headers": dict(headers or {})})
        if host in self.fail_hosts:
            raise requests.ConnectionError("network blocked in test")
        resp = requests.models.Response()
        resp.status_code = self.status.get(host, 200)
        resp.url = full
        if host in self.retry_after:
            resp.headers["Retry-After"] = str(self.retry_after[host])
        resp._content = json.dumps(_payload_for(host) if resp.status_code == 200 else {"code": -1003}).encode()
        return resp

    def count(self, host=None):
        with self.lock:
            return sum(1 for c in self.calls if host is None or c["host"] == host)

    def per_exchange(self):
        return {
            "binance": self.count("api.binance.com"),
            "kraken": self.count("api.kraken.com"),
            "alpaca": self.count("data.alpaca.markets"),
            "capital": sum(1 for c in self.calls if "capital" in (c["host"] or "")),
        }


@pytest.fixture
def rec(monkeypatch, tmp_path):
    r = Recorder()
    monkeypatch.setattr(requests.sessions.Session, "request",
                        lambda self, method, url, **kw: r(self, method, url, **kw))
    monkeypatch.setenv("AUREON_SHARED_MARKET_FEED_PATH", str(tmp_path / "state" / "shared_market_feed.json"))
    for name in ("ALPACA_API_KEY", "ALPACA_KEY", "ALPACA_SECRET_KEY", "ALPACA_API_SECRET", "ALPACA_SECRET"):
        monkeypatch.delenv(name, raising=False)
    return r


def _capital_monitor(tmp_path, *, age_s=0.0, symbols=("US500", "EURUSD")):
    now = time.time() - age_s
    path = tmp_path / "capital_monitor.json"
    path.write_text(json.dumps({
        "generated_at": now, "source": "capital_market_monitor.quotes", "generated_values": False,
        "prices": {s: {"symbol": s, "source": "capital", "price": 10.5, "bid": 10.4, "ask": 10.6,
                       "change_pct": 0.3, "epic": s, "source_timestamp": now,
                       "generated_values": False} for s in symbols},
    }), encoding="utf-8")
    return path


def _pollers(tmp_path, **kw):
    return [feed.BinancePoller(**kw), feed.KrakenPoller(**kw), feed.AlpacaPoller(**kw),
            feed.CapitalPoller(monitor_path=_capital_monitor(tmp_path), **kw)]


# ── call counts ─────────────────────────────────────────────────────────────
def test_one_cycle_calls_each_exchange_exactly_once(rec, tmp_path):
    for p in _pollers(tmp_path):
        p.poll_once()
    assert rec.per_exchange() == {"binance": 1, "kraken": 1, "alpaca": 1, "capital": 0}
    snap = feed.read_snapshot()
    assert {v: snap["venues"][v]["state"] for v in feed.VENUES} == {
        "capital": "fresh", "binance": "fresh", "kraken": "fresh", "alpaca": "fresh"}
    assert snap["venues"]["binance"]["quotes"]["BTC"]["price"] == 65000.0
    assert snap["venues"]["capital"]["quotes"]["US500"]["quote_source"] == "capital"
    for v in feed.VENUES:
        assert snap["venues"][v]["source"]
        assert snap["venues"][v]["fetched_at"] is not None
        assert snap["venues"][v]["age_s"] is not None


def test_many_concurrent_readers_cause_zero_exchange_calls(rec, tmp_path, monkeypatch):
    from aureon.data_feeds import unified_market_cache as cache_mod

    for name in ("WS_PRICE_CACHE_PATH", "BINANCE_CACHE_PATH", "UNIFIED_CACHE_PATH", "KRAKEN_CACHE_PATH"):
        monkeypatch.setattr(cache_mod, name, str(tmp_path / f"{name}.json"))
    monkeypatch.setattr(cache_mod, "BINANCE_CACHE_PATHS", [str(tmp_path / "WS_PRICE_CACHE_PATH.json")])
    monkeypatch.setattr(cache_mod, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(cache_mod.UnifiedMarketCache, "_instance", None)
    monkeypatch.setattr(cache_mod, "_cache_instance", None)

    for p in _pollers(tmp_path):
        p.poll_once()
    before = rec.per_exchange()
    errors = []

    def reader(i):
        try:
            for _ in range(40):
                snap = feed.read_snapshot()
                assert snap["venues"]["kraken"]["state"] == "fresh"
                assert feed.fresh_quotes()
                assert feed.read_venue_quote("alpaca", "ETH")["bid"] == 100.0
                feed.feed_health()
                cache = cache_mod.UnifiedMarketCache()
                cache._last_file_read = 0.0
                assert cache.get_price("BTC", max_age=60) == 65000.0
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(repr(exc))

    threads = [threading.Thread(target=reader, args=(i,)) for i in range(32)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert not errors, errors[:3]
    assert rec.per_exchange() == before == {"binance": 1, "kraken": 1, "alpaca": 1, "capital": 0}


def test_feed_loop_polls_each_exchange_at_its_interval(rec, tmp_path):
    stop = threading.Event()
    pollers = _pollers(tmp_path, interval_s=0.25)
    threads = feed.run_feed(pollers=pollers, stop=stop)
    time.sleep(1.1)
    stop.set()
    for t in threads:
        t.join(5)
    counts = rec.per_exchange()
    # 1.1 s at one call per 0.25 s: at most 5 calls each, at least 2.
    for venue in ("binance", "kraken", "alpaca"):
        assert 2 <= counts[venue] <= 5, counts
    assert counts["capital"] == 0


# ── stale / missing / error ─────────────────────────────────────────────────
def test_stale_venue_is_reported_stale_and_not_served(rec, tmp_path, monkeypatch):
    for p in _pollers(tmp_path):
        p.poll_once()
    later = time.time() + 120.0
    snap = feed.read_snapshot(now=later)
    for v in ("binance", "kraken", "alpaca"):
        assert snap["venues"][v]["state"] == "stale"
        assert snap["venues"][v]["quotes"] == {}
        assert snap["venues"][v]["age_s"] >= 119
    assert feed.fresh_quotes(now=later) == []


def test_capital_monitor_age_is_kept_not_restamped(rec, tmp_path):
    p = feed.CapitalPoller(monitor_path=_capital_monitor(tmp_path, age_s=600))
    p.poll_once()
    view = feed.read_snapshot()["venues"]["capital"]
    assert view["state"] == "stale"
    assert view["age_s"] >= 599
    assert view["quotes"] == {}
    assert rec.count() == 0


def test_missing_capital_cache_is_error_with_no_numbers(rec, tmp_path):
    feed.CapitalPoller(monitor_path=tmp_path / "nope.json").poll_once()
    view = feed.read_snapshot()["venues"]["capital"]
    assert view["state"] == "error"
    assert "capital monitor cache missing" in view["error"]
    assert view["quotes"] == {} and view["fetched_at"] is None
    assert rec.count() == 0


def test_missing_file_reports_every_venue_missing(rec):
    snap = feed.read_snapshot()
    assert snap["file_present"] is False
    assert {v["state"] for v in snap["venues"].values()} == {"missing"}


def test_failed_fetch_replaces_old_quotes_with_error(rec, tmp_path):
    k = feed.KrakenPoller()
    k.poll_once()
    assert feed.read_snapshot()["venues"]["kraken"]["state"] == "fresh"
    rec.fail_hosts.add("api.kraken.com")
    k.poll_once()
    view = feed.read_snapshot()["venues"]["kraken"]
    assert view["state"] == "error" and view["quotes"] == {}
    assert view["last_ok_at"] is not None
    assert "ConnectionError" in view["error"]


def test_429_honours_retry_after_and_sends_nothing_during_backoff(rec):
    rec.status["api.binance.com"] = 429
    rec.retry_after["api.binance.com"] = 30
    b = feed.BinancePoller()
    b.poll_once()
    assert rec.count("api.binance.com") == 1
    assert b.backoff_until >= time.time() + 28
    for _ in range(5):
        b.poll_once()
    assert rec.count("api.binance.com") == 1
    view = feed.read_snapshot()["venues"]["binance"]
    assert view["state"] == "error" and view["quotes"] == {}


# ── lock ────────────────────────────────────────────────────────────────────
def test_snapshot_and_lock_are_0600_and_atomic(rec, tmp_path):
    feed.KrakenPoller().poll_once()
    path = feed.snapshot_path()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(Path(str(path) + ".lock").stat().st_mode) == 0o600
    assert not list(path.parent.glob("*.tmp"))


def test_concurrent_writers_never_lose_a_venue(tmp_path):
    path = tmp_path / "snap.json"
    errors = []

    def writer(venue):
        try:
            for i in range(25):
                feed.write_venue({"venue": venue, "status": "ok", "fetched_at": time.time(),
                                  "max_age_s": 60, "quotes": {"X": {"price": i + 1}}, "source": venue},
                                 path)
                snap = json.loads(path.read_text())
                assert venue in snap["venues"]
        except Exception as exc:  # pragma: no cover
            errors.append(repr(exc))

    threads = [threading.Thread(target=writer, args=(v,)) for v in feed.VENUES for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(60)
    assert not errors, errors[:3]
    snap = json.loads(path.read_text())
    assert set(snap["venues"]) == set(feed.VENUES)


def test_writer_waits_for_held_lock_then_times_out_without_writing(tmp_path):
    import fcntl

    path = tmp_path / "snap.json"
    feed.write_venue({"venue": "kraken", "status": "ok", "fetched_at": time.time(), "max_age_s": 9,
                      "quotes": {}, "source": "k"}, path)
    before = path.read_bytes()
    fd = os.open(str(path) + ".lock", os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        with pytest.raises(feed.FeedLockTimeout):
            feed.write_venue({"venue": "binance", "status": "ok", "fetched_at": time.time(),
                              "max_age_s": 9, "quotes": {}, "source": "b"}, path, lock_timeout=0.2)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    assert path.read_bytes() == before


def test_no_lock_primitive_refuses_to_write(tmp_path, monkeypatch):
    monkeypatch.setattr(feed, "fcntl", None)
    monkeypatch.setattr(feed, "msvcrt", None)
    path = tmp_path / "snap.json"
    with pytest.raises(feed.FeedLockUnavailable):
        feed.write_venue({"venue": "kraken", "status": "ok", "fetched_at": time.time(),
                          "max_age_s": 9, "quotes": {}, "source": "k"}, path)
    assert not path.exists()


def test_windows_msvcrt_lock_is_used_when_fcntl_is_missing(tmp_path, monkeypatch):
    calls = []
    fake = types.SimpleNamespace(LK_NBLCK=2, LK_UNLCK=0,
                                 locking=lambda fd, mode, n: calls.append((mode, n)))
    monkeypatch.setattr(feed, "fcntl", None)
    monkeypatch.setattr(feed, "msvcrt", fake)
    path = tmp_path / "snap.json"
    feed.write_venue({"venue": "alpaca", "status": "ok", "fetched_at": time.time(),
                      "max_age_s": 9, "quotes": {}, "source": "a"}, path)
    assert calls == [(2, 1), (0, 1)]
    assert "alpaca" in json.loads(path.read_text())["venues"]


# ── read-only: no order code, no order endpoint ─────────────────────────────
FORBIDDEN_MODULE = re.compile(
    r"(order|trade|trading|trader|execution|executor|kill_chain|orca|"
    r"aureon\.exchanges|capital_client|alpaca_client|binance_client|kraken_client|"
    r"aureon\.governance\.economic)", re.I)


def test_feed_import_loads_no_order_trade_or_execution_module():
    code = (
        "import sys, json\n"
        "import aureon.data_feeds.shared_market_feed as f\n"
        "f.BinancePoller(); f.KrakenPoller(); f.AlpacaPoller(); f.CapitalPoller()\n"
        "print(json.dumps(sorted(sys.modules)))\n"
    )
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ.get("HOME", "/tmp"),
           "PYTHONPATH": os.pathsep.join([str(REPO_ROOT)] + [p for p in sys.path if p.endswith("sully_deps")])}
    out = subprocess.run([sys.executable, "-c", code], cwd=str(REPO_ROOT), env=env,
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    modules = json.loads(out.stdout.strip().splitlines()[-1])
    assert "aureon.data_feeds.shared_market_feed" in modules
    bad = [m for m in modules if FORBIDDEN_MODULE.search(m)]
    assert bad == []


def test_no_recorded_request_hits_an_order_endpoint(rec, tmp_path, monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "FAKE_TEST_KEY_ID")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "FAKE_TEST_SECRET")
    for _ in range(3):
        for p in _pollers(tmp_path):
            p.poll_once()
    stop = threading.Event()
    threads = feed.run_feed(pollers=_pollers(tmp_path, interval_s=0.1), stop=stop)
    time.sleep(0.5)
    stop.set()
    for t in threads:
        t.join(5)
    assert rec.count() >= 12
    for call in rec.calls:
        assert call["method"] == "GET", call
        assert call["host"] in ("api.binance.com", "api.kraken.com", "data.alpaca.markets"), call
        for _method, pattern in ORDER_ENDPOINT_PATTERNS:
            assert not pattern.search(call["url"]), call["url"]
        if call["host"] in ("api.binance.com", "api.kraken.com"):
            assert not any(h.lower().startswith(("x-mbx", "api-key", "api-sign", "apca"))
                           for h in call["headers"]), call
        else:
            assert call["headers"].get("APCA-API-KEY-ID") == "FAKE_TEST_KEY_ID"


@pytest.mark.parametrize("method,url", [
    ("POST", "https://api-capital.backend-capital.com/api/v1/positions"),
    ("DELETE", "https://api-capital.backend-capital.com/api/v1/positions/abc"),
    ("GET", "https://api-capital.backend-capital.com/api/v1/markets"),
    ("POST", "https://api.binance.com/api/v3/order"),
    ("GET", "https://api.binance.com/api/v3/order"),
    ("POST", "https://api.kraken.com/0/private/AddOrder"),
    ("GET", "https://api.kraken.com/0/private/Balance"),
    ("POST", "https://paper-api.alpaca.markets/v2/orders"),
    ("GET", "https://data.alpaca.markets/v2/orders"),
    ("POST", "https://data.alpaca.markets/v1beta3/crypto/us/latest/quotes"),
])
def test_read_only_guard_refuses_order_and_non_data_requests(method, url):
    with pytest.raises(feed.ReadOnlyViolation):
        feed._assert_read_only(method, url)


# ── readers wired ───────────────────────────────────────────────────────────
def test_unified_cache_serves_only_complete_fresh_feed_quotes(rec, tmp_path, monkeypatch):
    from aureon.data_feeds import unified_market_cache as cache_mod

    for name in ("WS_PRICE_CACHE_PATH", "BINANCE_CACHE_PATH", "UNIFIED_CACHE_PATH", "KRAKEN_CACHE_PATH"):
        monkeypatch.setattr(cache_mod, name, str(tmp_path / f"{name}.json"))
    monkeypatch.setattr(cache_mod, "BINANCE_CACHE_PATHS", [str(tmp_path / "WS_PRICE_CACHE_PATH.json")])
    monkeypatch.setattr(cache_mod, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(cache_mod.UnifiedMarketCache, "_instance", None)
    monkeypatch.setattr(cache_mod, "_cache_instance", None)

    feed.KrakenPoller().poll_once()   # no 24h change/quote volume -> not folded
    cache = cache_mod.get_market_cache()
    cache._last_file_read = 0.0
    assert cache.get_ticker("BTC", max_age=60) is None
    assert cache.get_source_health()["shared_feed:kraken"]["state"] == "fresh"

    feed.BinancePoller().poll_once()
    cache._last_file_read = 0.0
    t = cache.get_ticker("BTC", max_age=60)
    assert t is not None and t.source == "shared_feed:binance" and t.price == 65000.0
    assert t.change_24h == -1.25 and t.bid == 64999.0
    assert rec.per_exchange() == {"binance": 1, "kraken": 1, "alpaca": 0, "capital": 0}


def test_queen_market_awareness_reads_feed_without_calling_binance(rec, tmp_path):
    from aureon.queen.queen_market_awareness import QueenMarketAwareness

    feed.BinancePoller().poll_once()
    assert rec.count() == 1
    q = object.__new__(QueenMarketAwareness)
    q.btc_reference_prices = {"jan_2026_high": 108000}
    data = q._fetch_btc_data()
    assert data["source"] == "shared_feed:binance"
    assert data["price"] == 65000.0 and data["change_24h"] == -1.25
    assert rec.count() == 1


def test_metacognition_monitor_sees_feed_freshness(rec, tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    monkeypatch.setenv("AUREON_METACOG_LAMBDA_PATH", str(tmp_path / "metacog_lambda.json"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc_trace.jsonl"))
    from aureon.core.metacognition_monitor import MetacognitionMonitor

    _r, signals, _d, _c = MetacognitionMonitor()._gather()
    assert signals["market_feed"]["truth_status"] == "no_data"
    assert set(signals["market_feed"]["venues"].values()) == {"missing"}

    feed.BinancePoller().poll_once()
    feed.KrakenPoller().poll_once()
    _r, signals, _d, _c = MetacognitionMonitor()._gather()
    sig = signals["market_feed"]
    assert sig["truth_status"] == "live" and sig["value"] == 0.5
    assert sig["venues"] == {"capital": "missing", "binance": "fresh", "kraken": "fresh", "alpaca": "missing"}
    assert rec.per_exchange() == {"binance": 1, "kraken": 1, "alpaca": 0, "capital": 0}
