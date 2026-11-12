"""Capital.com pacing: one shared login, spaced logins, <10 req/s, shared 429 backoff.

Every assertion counts real (mocked) HTTP calls made through ``requests``,
recorded by the fakes below, never log or error lines. No network is used.
Published limits: https://open-api.capital.com/ ("Rate limits").
"""

from __future__ import annotations

import logging
import multiprocessing as mp
import os
import re
import stat
import time

import pytest

from aureon.exchanges import capital_client as cc

_DEFAULT_SHARED = {
    "cst": None,
    "x_security_token": None,
    "session_start_time": 0.0,
    "demo_mode": None,
    "rate_limit_until": 0.0,
    "init_error": "",
}


class _Resp:
    def __init__(self, status_code=200, headers=None, payload=None):
        self.status_code = status_code
        self.headers = dict(headers or {})
        self._payload = payload if payload is not None else {}
        self.text = "{}" if status_code != 429 else '{"errorCode":"error.too-many.requests"}'

    def json(self):
        return dict(self._payload)


def _record(log_path: str, kind: str) -> None:
    fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, f"{kind} {time.time():.6f} {os.getpid()}\n".encode())
    finally:
        os.close(fd)


def _calls(log_path: str, kind: str):
    if not os.path.exists(log_path):
        return []
    out = []
    with open(log_path, encoding="utf-8") as handle:
        for line in handle:
            parts = line.split()
            if parts and parts[0] == kind:
                out.append(float(parts[1]))
    return sorted(out)


def _reset_process_memory():
    cc._SHARED_SESSION.clear()
    cc._SHARED_SESSION.update(dict(_DEFAULT_SHARED))
    shared = getattr(cc, "_cap_shared", None)
    if shared is not None:
        shared._LOCAL_STATE.clear()


@pytest.fixture
def capital_env(tmp_path, monkeypatch):
    log_path = str(tmp_path / "http_calls.log")
    monkeypatch.setenv("CAPITAL_SESSION_CACHE_PATH", str(tmp_path / "capital_session_cache.json"))
    monkeypatch.setenv("CAPITAL_API_KEY", "unit-test-key")
    monkeypatch.setenv("CAPITAL_IDENTIFIER", "unit-test-id")
    monkeypatch.setenv("CAPITAL_PASSWORD", "unit-test-pw")
    monkeypatch.setenv("CAPITAL_DEMO", "1")
    monkeypatch.setenv("CAPITAL_SESSION_KEEPALIVE", "0")  # tests call keep_alive_if_idle directly
    monkeypatch.delenv("CAPITAL_MAX_REQUESTS_PER_SEC", raising=False)
    monkeypatch.delenv("CAPITAL_SESSION_IDLE_REFRESH_S", raising=False)
    _reset_process_memory()

    state = {"get_status": 200, "get_headers": {}, "post_status": 200, "post_headers": None,
             "dead_cst": None, "login_no": 0}

    def fake_post(url, json=None, headers=None, timeout=None):
        assert url.endswith("/session")
        _record(log_path, "POST")
        time.sleep(0.2)  # login latency, so concurrent processes overlap
        if state["post_status"] != 200:
            return _Resp(state["post_status"], state["post_headers"])
        n = len(_calls(log_path, "POST"))
        return _Resp(200, {"CST": f"cst-{n}-SECRET-VALUE", "X-SECURITY-TOKEN": f"xst-{n}-SECRET-VALUE"})

    def fake_request(method, url, headers=None, params=None, json=None, timeout=None):
        _record(log_path, method)
        if url.endswith("/ping"):
            _record(log_path, "PING")
        if state["dead_cst"] and (headers or {}).get("CST") == state["dead_cst"]:
            return _Resp(401, {})
        status = state["get_status"]
        if callable(status):
            status = status()
        return _Resp(status, state["get_headers"] if status == 429 else {}, {"accounts": []})

    monkeypatch.setattr(cc.requests, "post", fake_post)
    monkeypatch.setattr(cc.requests, "request", fake_request)
    yield {"log": log_path, "state": state, "tmp": tmp_path}
    _reset_process_memory()


def _run_processes(target, count, *args):
    ctx = mp.get_context("fork")
    procs = [ctx.Process(target=target, args=args) for _ in range(count)]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join(60)
        assert proc.exitcode == 0, proc.exitcode


def _child_login_and_read(reads: int):
    _reset_process_memory()  # a fresh launcher process has no in-memory session
    client = cc.CapitalClient()
    for _ in range(reads):
        client._request("GET", "/accounts")
    os._exit(0)


def test_many_processes_and_instances_make_exactly_one_login(capital_env):
    _run_processes(_child_login_and_read, 4, 1)
    # plus more instances in this process
    for _ in range(3):
        cc.CapitalClient()._request("GET", "/accounts")
    assert len(_calls(capital_env["log"], "POST")) == 1
    assert len(_calls(capital_env["log"], "GET")) == 7


def test_relogins_are_spaced_at_least_one_second(capital_env):
    responses = iter([401, 200])
    capital_env["state"]["get_status"] = lambda: next(responses, 200)
    client = cc.CapitalClient()
    client._request("GET", "/accounts")  # 401 -> re-login -> retry
    posts = _calls(capital_env["log"], "POST")
    assert len(posts) == 2
    assert posts[1] - posts[0] >= 1.0


def test_burst_of_account_reads_stays_under_ten_per_second(capital_env):
    _run_processes(_child_login_and_read, 3, 10)
    gets = _calls(capital_env["log"], "GET")
    assert len(gets) == 30
    for i, start in enumerate(gets):
        in_window = [t for t in gets[i:] if t - start < 1.0]
        assert len(in_window) <= 10, (len(in_window), start)


def _child_one_read():
    _reset_process_memory()
    client = cc.CapitalClient()
    client._request("GET", "/accounts")
    os._exit(0)


def test_429_retry_after_backs_off_every_process(capital_env):
    state = capital_env["state"]
    state["get_status"] = 429
    state["get_headers"] = {"Retry-After": "2"}
    _run_processes(_child_one_read, 1)  # gets the 429
    assert len(_calls(capital_env["log"], "GET")) == 1

    state["get_status"] = 200
    _run_processes(_child_one_read, 2)  # other processes must not call
    other = cc.CapitalClient()
    resp = other._request("GET", "/accounts")
    assert resp.status_code in (429, 503)  # refused locally, nothing sent
    assert len(_calls(capital_env["log"], "GET")) == 1

    time.sleep(2.6)  # Retry-After (2 s) honoured with <=0.25 s jitter, not the 600 s default
    assert other._request("GET", "/accounts").status_code == 200
    assert len(_calls(capital_env["log"], "GET")) == 2


def test_login_429_log_matches_real_wait_and_hides_tokens(capital_env, caplog):
    capital_env["state"]["post_status"] = 429
    with caplog.at_level(logging.WARNING):
        client = cc.CapitalClient()
    text = caplog.text
    assert "5 minutes" not in text
    waits = [int(n) for n in re.findall(r"backing off for (\d+) seconds", text)]
    assert waits and all(600 <= n <= 660 for n in waits), waits  # 600 s + jitter
    assert "login attempt" in text.lower()
    assert client._rate_limit_until - time.time() > 590


def test_cache_file_is_private_and_tokens_never_logged(capital_env, caplog):
    with caplog.at_level(logging.DEBUG):
        client = cc.CapitalClient()
        client._request("GET", "/accounts")
    assert "SECRET-VALUE" not in caplog.text
    cache = capital_env["tmp"] / "capital_session_cache.json"
    assert cache.exists()
    assert stat.S_IMODE(os.stat(cache).st_mode) == 0o600


def _age_shared_session(seconds: float) -> None:
    from aureon.exchanges import capital_shared_state as shared

    key = shared.account_key("unit-test-key", True)
    with shared.locked_state(key) as bucket:
        bucket["last_used_at"] = time.time() - seconds
        bucket["session_start_time"] = time.time() - seconds


def _child_keepalive():
    _reset_process_memory()
    cc.CapitalClient().keep_alive_if_idle()
    os._exit(0)


def test_quiet_session_gets_one_shared_ping_and_no_login(capital_env):
    cc.CapitalClient()._request("GET", "/accounts")
    assert len(_calls(capital_env["log"], "POST")) == 1
    _age_shared_session(545)  # quiet ~9 minutes (simulated clock)
    _run_processes(_child_keepalive, 3)
    for _ in range(2):
        cc.CapitalClient().keep_alive_if_idle()
    assert len(_calls(capital_env["log"], "PING")) == 1
    assert len(_calls(capital_env["log"], "POST")) == 1  # no re-login for idleness
    # and the next request still uses the same session without logging in
    client = cc.CapitalClient()
    assert client._request("GET", "/accounts").status_code == 200
    assert len(_calls(capital_env["log"], "POST")) == 1


def test_401_triggers_exactly_one_login_across_processes(capital_env):
    cc.CapitalClient()._request("GET", "/accounts")
    assert len(_calls(capital_env["log"], "POST")) == 1
    capital_env["state"]["dead_cst"] = "cst-1-SECRET-VALUE"  # Capital dropped it
    _run_processes(_child_login_and_read, 4, 1)
    assert len(_calls(capital_env["log"], "POST")) == 2


def test_failed_account_reads_are_cached_briefly(capital_env):
    capital_env["state"]["get_status"] = 503
    client = cc.CapitalClient()
    for _ in range(5):
        client.get_account_balance()  # uses cache_ttl=0.0
    assert len(_calls(capital_env["log"], "GET")) == 1


def test_market_walk_fills_shared_cache_and_never_saves_empty(capital_env, monkeypatch):
    disk = capital_env["tmp"] / "markets.json"
    monkeypatch.setattr(cc, "CAPITAL_MARKET_DISK_CACHE_PATH", str(disk))
    cc._SHARED_MARKET_CACHE.update({"markets": [], "market_index": {}, "market_cache_time": 0.0})
    client = cc.CapitalClient()
    monkeypatch.setattr(client, "_request", lambda m, p, **k: _Resp(200, {}, {"markets": [], "nodes": []}))
    assert client.get_all_markets(force_refresh=True) == []
    assert not disk.exists()
    market = {"epic": "AAPL", "instrumentName": "Apple"}
    monkeypatch.setattr(client, "_request", lambda m, p, **k: _Resp(200, {}, {"markets": [market], "nodes": []}))
    assert client.get_all_markets(force_refresh=True) == [market]
    assert cc._SHARED_MARKET_CACHE["markets"] == [market]
    assert disk.exists()
    cc._SHARED_MARKET_CACHE.update({"markets": [], "market_index": {}, "market_cache_time": 0.0})


def test_kill_chain_reuses_cycle_account_read():
    orca = pytest.importorskip("aureon_radar.bots.orca_unified_kill_chain")

    class _Portfolio:
        reads = 0

        def get_quick_summary(self):
            _Portfolio.reads += 1
            return {}

        def get_real_portfolio(self):
            _Portfolio.reads += 1

    chain = orca.UnifiedKillChain.__new__(orca.UnifiedKillChain)
    chain.real_portfolio = _Portfolio()
    chain.refresh_truth()
    chain._refresh_portfolio_after_trade(order_sent=False)
    assert _Portfolio.reads == 1


def _good_caches(capital_env, monkeypatch):
    disk = capital_env["tmp"] / "markets.json"
    monkeypatch.setattr(cc, "CAPITAL_MARKET_DISK_CACHE_PATH", str(disk))
    good = [{"epic": "GOOD", "instrumentName": "Good"}]
    disk.write_text('{"markets": [{"epic": "GOOD"}], "ts": 1}', encoding="utf-8")
    cc._SHARED_MARKET_CACHE.update({"markets": list(good), "market_index": {}, "market_cache_time": 1.0})
    client = cc.CapitalClient()
    client.market_cache = list(good)
    return client, disk, disk.read_text(encoding="utf-8"), good


def _assert_untouched(client, disk, before, good):
    assert cc._SHARED_MARKET_CACHE["markets"] == good
    assert client.market_cache == good
    assert disk.read_text(encoding="utf-8") == before
    cc._SHARED_MARKET_CACHE.update({"markets": [], "market_index": {}, "market_cache_time": 0.0})


@pytest.mark.parametrize("stop", ["429", "error"])
def test_market_walk_that_stops_on_429_or_error_leaves_caches_untouched(capital_env, monkeypatch, stop):
    client, disk, before, good = _good_caches(capital_env, monkeypatch)

    def walk(method, path, **kwargs):
        if stop == "error":
            raise RuntimeError("connection reset mid-walk")
        return _Resp(429, {})

    monkeypatch.setattr(client, "_request", walk)
    client.get_all_markets(force_refresh=True)
    _assert_untouched(client, disk, before, good)


def test_partial_market_walk_is_never_cached_or_saved(capital_env, monkeypatch):
    # Root answers with some markets and more nodes to visit, then the walk is
    # cut short (time cap); the partial result must not replace the good cache.
    client, disk, before, good = _good_caches(capital_env, monkeypatch)
    real_time = time.time
    offset = {"s": 0.0}
    monkeypatch.setattr(cc.time, "time", lambda: real_time() + offset["s"])

    def walk(method, path, **kwargs):
        offset["s"] = 31.0  # past the 30 s walk cap after the first page
        return _Resp(200, {}, {"markets": [{"epic": "PART"}], "nodes": [{"id": "n1"}, {"id": "n2"}]})

    monkeypatch.setattr(client, "_request", walk)
    client.get_all_markets(force_refresh=True)
    monkeypatch.setattr(cc.time, "time", real_time)
    _assert_untouched(client, disk, before, good)


class _Reads:
    def __init__(self):
        self.reads = 0

    def get_quick_summary(self):
        self.reads += 1
        return {}

    def get_real_portfolio(self):
        self.reads += 1


class _Binance:
    def __init__(self, outcome):
        self.outcome = outcome
        self.sent = 0

    def get_free_balance(self, asset):
        return 100.0

    def place_market_order(self, symbol, side, qty):
        self.sent += 1
        if self.outcome == "raise":
            raise RuntimeError("connection reset after send")
        return {"status": self.outcome}


class _Kraken:
    dry_run = False
    last_balance_source = "live"

    def get_balance(self):
        return {"USD": 100.0}

    def place_market_order(self, pair, side, qty):
        return {"status": "FILLED", "executedQty": qty}


def _chain_after_truth(orca, binance=None, kraken=None):
    chain = orca.UnifiedKillChain.__new__(orca.UnifiedKillChain)
    chain.real_portfolio = _Reads()
    chain.wins_executed = []
    chain.binance = binance
    chain.kraken = kraken
    chain.refresh_truth()  # truth is fresh (<30 s)
    assert chain.real_portfolio.reads == 1
    return chain


@pytest.mark.parametrize("outcome", ["FILLED", "REJECTED", "raise"])
def test_kill_chain_reads_fresh_after_any_order_send(outcome, tmp_path, monkeypatch):
    orca = pytest.importorskip("aureon_radar.bots.orca_unified_kill_chain")
    monkeypatch.chdir(tmp_path)
    binance = _Binance(outcome)
    chain = _chain_after_truth(orca, binance=binance)
    chain._execute_trade({"exchange": "binance", "symbol": "BTCUSDT", "price": 10.0})
    assert binance.sent == 1
    assert chain.real_portfolio.reads == 2  # fresh read despite truth < 30 s old


def test_kill_chain_reads_fresh_after_partial_arbitrage(tmp_path, monkeypatch):
    orca = pytest.importorskip("aureon_radar.bots.orca_unified_kill_chain")
    monkeypatch.chdir(tmp_path)
    chain = _chain_after_truth(orca, binance=_Binance("REJECTED"), kraken=_Kraken())
    result = chain._execute_trade({
        "exchange": "arbitrage", "symbol": "BTC/USD", "buy_exchange": "kraken",
        "sell_exchange": "binance", "kraken_price": 10.0, "binance_price": 11.0,
    })
    assert result["status"] == "PARTIAL"
    assert chain.real_portfolio.reads == 2


def test_kill_chain_reuses_truth_when_nothing_was_sent(tmp_path, monkeypatch):
    orca = pytest.importorskip("aureon_radar.bots.orca_unified_kill_chain")
    monkeypatch.chdir(tmp_path)
    binance = _Binance("FILLED")
    chain = _chain_after_truth(orca, binance=binance)
    result = chain._execute_trade({"exchange": "binance", "symbol": "BTCUSDT", "price": 0})
    assert result["status"] == "NO_PRICE"
    assert binance.sent == 0
    assert chain.real_portfolio.reads == 1  # reused this cycle's read


# --- fail-closed when the shared lock/file is unavailable (Charlie, Buzz) ---

def _shared():
    from aureon.exchanges import capital_shared_state as shared

    return shared


def _fresh_key(name):
    return _shared().account_key(f"probe-{name}-{time.time()}", True)


def test_write_failure_keeps_backoff_in_memory_and_refuses_orders(capital_env, monkeypatch, caplog):
    shared = _shared()

    def broken_write(path, data):
        raise OSError("disk full")

    monkeypatch.setattr(shared, "_write_file", broken_write)
    key = _fresh_key("backoff")
    shared.record_backoff(key, 600)
    assert shared.backoff_remaining(key) > 599  # not 0 s
    assert shared.acquire_request_slot(key, is_order=True) == "backoff"

    key = _fresh_key("orders")
    with caplog.at_level(logging.ERROR):
        granted = [shared.acquire_request_slot(key, is_order=True) for _ in range(5)]
    assert granted == ["shared_state_unavailable"] * 5
    assert shared.ORDERS_REFUSED_LOG in caplog.text

    # reads may continue, paced from memory (8/s; never over Capital's 10 in any second)
    times = []
    for _ in range(12):
        assert shared.acquire_request_slot(key) is None
        times.append(time.time())
    assert times[-1] - times[0] >= 0.9  # 12 reads at 8/s cannot be instant
    for i, start in enumerate(times):
        assert len([t for t in times[i:] if t - start < 1.0]) <= 10


def test_no_lock_mechanism_refuses_orders_with_clear_log(capital_env, monkeypatch, caplog):
    shared = _shared()
    monkeypatch.setattr(shared, "fcntl", None)
    monkeypatch.setattr(shared, "msvcrt", None, raising=False)
    key = _fresh_key("nolock")
    with caplog.at_level(logging.ERROR):
        assert shared.acquire_request_slot(key, is_order=True) == "shared_state_unavailable"
    assert "capital orders refused: shared lock unavailable" in caplog.text
    assert shared.acquire_request_slot(key) is None  # reads still allowed
    shared.record_backoff(key, 600)
    assert shared.backoff_remaining(key) > 599


def test_windows_msvcrt_lock_is_used_and_orders_allowed(capital_env, monkeypatch):
    import fcntl as real_fcntl

    shared = _shared()
    calls = []

    class FakeMsvcrt:
        LK_UNLCK, LK_LOCK = 0, 1

        @staticmethod
        def locking(fd, mode, nbytes):
            calls.append((mode, nbytes))
            real_fcntl.flock(fd, real_fcntl.LOCK_EX if mode == 1 else real_fcntl.LOCK_UN)

    monkeypatch.setattr(shared, "fcntl", None)
    monkeypatch.setattr(shared, "msvcrt", FakeMsvcrt, raising=False)
    key = _fresh_key("win")
    assert shared.acquire_request_slot(key, is_order=True) is None
    assert shared.shared_state_ok()
    assert (1, 1) in calls and (0, 1) in calls
    assert (capital_env["tmp"] / "capital_session_cache.json").exists()


def _child_orders(key, log_path):
    shared = _shared()
    for _ in range(3):
        assert shared.acquire_request_slot(key, is_order=True) is None
    os._exit(0)


def test_order_slots_are_spaced_across_processes(capital_env, monkeypatch):
    shared = _shared()
    log_path = capital_env["log"]
    real_remember = shared._remember_enforced

    def spy(key, bucket):  # runs under the cross-process lock, at grant time
        if bucket.get("last_order_at"):
            fd = os.open(log_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
            os.write(fd, f"ORDER {bucket['last_order_at']:.6f}\n".encode())
            os.close(fd)
        real_remember(key, bucket)

    monkeypatch.setattr(shared, "_remember_enforced", spy)
    key = _fresh_key("pace")
    _run_processes(_child_orders, 3, key, log_path)
    orders = sorted(set(_calls(log_path, "ORDER")))
    assert len(orders) == 9
    gaps = [b - a for a, b in zip(orders, orders[1:])]
    assert min(gaps) >= 0.15, gaps


def test_429_log_reports_shared_deadline(capital_env, caplog):
    state = capital_env["state"]
    client = cc.CapitalClient()
    state["get_status"] = 429
    state["get_headers"] = {"Retry-After": "30"}
    with caplog.at_level(logging.WARNING):
        client._request("GET", "/accounts")
    assert re.search(r"shared backoff until \d\d:\d\d:\d\d UTC \(\d+ s remaining\)", caplog.text)
