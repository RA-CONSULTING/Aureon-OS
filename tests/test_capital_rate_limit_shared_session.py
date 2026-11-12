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
    chain._refresh_portfolio_after_trade()
    assert _Portfolio.reads == 1
