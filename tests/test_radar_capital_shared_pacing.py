"""Phi-Radar / ORCA Capital client shares the main client's session, pacing and 429 backoff.

Assertions count real (mocked) HTTP calls made through ``requests``, recorded
by the fakes below, never log or error lines. No network is used. The radar
client and the main client must count against one Capital budget.
Published limits: https://open-api.capital.com/ ("Rate limits").
"""

from __future__ import annotations

import logging
import os
import stat
import time

import pytest

from aureon.exchanges import capital_client as main_cc
from aureon.exchanges import capital_shared_state as shared
import aureon_radar.capital_client as radar_cc


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
    for module in (main_cc, radar_cc):
        module._SHARED_SESSION.clear()
        module._SHARED_SESSION.update(dict(_DEFAULT_SHARED))
        cache = getattr(module, "_SHARED_MARKET_CACHE", None)
        if cache is not None:
            cache.update({"markets": [], "market_index": {}, "market_cache_time": 0.0})
    shared._LOCAL_STATE.clear()


@pytest.fixture
def capital_env(tmp_path, monkeypatch):
    log_path = str(tmp_path / "http_calls.log")
    monkeypatch.setenv("CAPITAL_SESSION_CACHE_PATH", str(tmp_path / "capital_session_cache.json"))
    monkeypatch.setenv("CAPITAL_API_KEY", "unit-test-key")
    monkeypatch.setenv("CAPITAL_IDENTIFIER", "unit-test-id")
    monkeypatch.setenv("CAPITAL_PASSWORD", "unit-test-pw")
    monkeypatch.setenv("CAPITAL_DEMO", "1")
    monkeypatch.setenv("CAPITAL_SESSION_KEEPALIVE", "0")
    # Official kill-switch: these tests measure the shared Capital pacer, not
    # the local organ budget (0.34/s on Capital hosts), which would stall them.
    monkeypatch.setenv("AUREON_RATE_BUDGET_ENABLED", "0")
    monkeypatch.delenv("CAPITAL_MAX_REQUESTS_PER_SEC", raising=False)
    monkeypatch.delenv("CAPITAL_SESSION_IDLE_REFRESH_S", raising=False)
    _reset_process_memory()

    state = {
        "get_status": 200,
        "get_headers": {},
        "post_status": 200,
        "post_headers": None,
        "payload": {"accounts": []},
    }

    def fake_post(url, json=None, headers=None, timeout=None):
        assert url.endswith("/session")
        _record(log_path, "POST")
        time.sleep(0.05)
        if state["post_status"] != 200:
            return _Resp(state["post_status"], state["post_headers"])
        n = len(_calls(log_path, "POST"))
        return _Resp(
            200,
            {"CST": f"cst-{n}-SECRET-VALUE", "X-SECURITY-TOKEN": f"xst-{n}-SECRET-VALUE"},
        )

    def fake_request(method, url, headers=None, params=None, json=None, timeout=None):
        _record(log_path, method)
        if url.endswith("/ping"):
            _record(log_path, "PING")
        status = state["get_status"]
        if callable(status):
            status = status()
        payload = state["payload"]
        if callable(payload):
            payload = payload(method, url)
        return _Resp(status, state["get_headers"] if status == 429 else {}, payload)

    # Patch both clients and the requests module they imported.
    for module in (main_cc, radar_cc):
        monkeypatch.setattr(module.requests, "post", fake_post)
        monkeypatch.setattr(module.requests, "request", fake_request)
    yield {"log": log_path, "state": state, "tmp": tmp_path}
    _reset_process_memory()


def test_radar_and_main_clients_share_one_login(capital_env):
    main_client = main_cc.CapitalClient()
    radar_client = radar_cc.CapitalClient()
    assert main_client._request("GET", "/accounts").status_code == 200
    assert radar_client._request("GET", "/accounts").status_code == 200
    # A second radar instance must reuse the same shared session too.
    other_radar = radar_cc.CapitalClient()
    assert other_radar._request("GET", "/accounts").status_code == 200
    assert len(_calls(capital_env["log"], "POST")) == 1
    assert len(_calls(capital_env["log"], "GET")) == 3
    cache = capital_env["tmp"] / "capital_session_cache.json"
    assert cache.exists()
    assert stat.S_IMODE(os.stat(cache).st_mode) == 0o600
    # Both clients hashed the same account into one bucket.
    assert main_client._shared_key_name() == radar_client._shared_key_name()


def test_radar_requests_are_paced(capital_env):
    client = radar_cc.CapitalClient()
    times = []
    for _ in range(12):
        assert client._request("GET", "/accounts").status_code == 200
        times.append(time.time())
    gets = _calls(capital_env["log"], "GET")
    assert len(gets) == 12
    assert gets[-1] - gets[0] >= 0.9  # 12 reads at the default 8/s cannot be instant
    for i, start in enumerate(gets):
        in_window = [t for t in gets[i:] if t - start < 1.0]
        assert len(in_window) <= 10, (len(in_window), start)


def test_429_backoff_is_shared_across_both_clients(capital_env):
    state = capital_env["state"]
    radar = radar_cc.CapitalClient()
    state["get_status"] = 429
    state["get_headers"] = {"Retry-After": "2"}
    assert radar._request("GET", "/accounts").status_code == 429
    assert len(_calls(capital_env["log"], "GET")) == 1

    state["get_status"] = 200
    main = main_cc.CapitalClient()
    resp = main._request("GET", "/accounts")
    assert resp.status_code in (429, 503)  # refused locally, nothing sent
    # Radar too: still inside the shared backoff.
    again = radar._request("GET", "/accounts")
    assert again.status_code in (429, 503)
    assert len(_calls(capital_env["log"], "GET")) == 1

    time.sleep(2.6)  # Retry-After (2 s) honoured with <=0.25 s jitter, not the 600 s default
    assert main._request("GET", "/accounts").status_code == 200
    assert len(_calls(capital_env["log"], "GET")) == 2


def test_radar_orders_refused_when_no_lock_is_available(capital_env, monkeypatch, caplog):
    monkeypatch.setattr(shared, "fcntl", None)
    monkeypatch.setattr(shared, "msvcrt", None, raising=False)
    client = radar_cc.CapitalClient()
    login_posts = len(_calls(capital_env["log"], "POST"))
    assert login_posts == 1  # the login itself is allowed (in-memory fallback)

    with caplog.at_level(logging.ERROR):
        for method, path in (
            ("POST", "/positions"),
            ("PUT", "/positions/deal-1"),
            ("DELETE", "/positions/deal-1"),
        ):
            resp = client._request(method, path, json_body={"epic": "TEST"})
            assert resp.status_code == 503
            assert resp.json()["errorCode"] == "shared_state_unavailable"
    assert shared.ORDERS_REFUSED_LOG in caplog.text
    # No order HTTP went out; the only POST is the login.
    assert len(_calls(capital_env["log"], "POST")) == login_posts
    assert len(_calls(capital_env["log"], "PUT")) == 0
    assert len(_calls(capital_env["log"], "DELETE")) == 0

    # Reads stay allowed and are paced from memory.
    assert client._request("GET", "/accounts").status_code == 200
    assert len(_calls(capital_env["log"], "GET")) == 1


def test_radar_partial_market_walk_is_never_cached(capital_env, monkeypatch):
    disk = capital_env["tmp"] / "markets.json"
    monkeypatch.setattr(radar_cc, "CAPITAL_MARKET_DISK_CACHE_PATH", str(disk))
    good = [{"epic": "GOOD", "instrumentName": "Good"}]
    disk.write_text('{"markets": [{"epic": "GOOD"}], "ts": 1}', encoding="utf-8")
    radar_cc._SHARED_MARKET_CACHE.update(
        {"markets": list(good), "market_index": {}, "market_cache_time": 1.0}
    )
    client = radar_cc.CapitalClient()
    client.market_cache = list(good)
    before = disk.read_text(encoding="utf-8")

    real_time = time.time
    offset = {"s": 0.0}
    monkeypatch.setattr(radar_cc.time, "time", lambda: real_time() + offset["s"])
    fetched = []

    def walk(method, path, **kwargs):
        fetched.append(path)
        offset["s"] = 31.0  # past the 30 s walk cap after the first page
        return _Resp(
            200,
            {},
            {"markets": [{"epic": "PART"}], "nodes": [{"id": "n1"}, {"id": "n2"}]},
        )

    monkeypatch.setattr(client, "_request", walk)
    result = client.get_all_markets(force_refresh=True)
    monkeypatch.setattr(radar_cc.time, "time", real_time)

    # Partial result must not replace the good cache or the disk file.
    assert radar_cc._SHARED_MARKET_CACHE["markets"] == good
    assert client.market_cache == good
    assert disk.read_text(encoding="utf-8") == before
    assert result == good
    assert fetched  # the root page was requested
    radar_cc._SHARED_MARKET_CACHE.update({"markets": [], "market_index": {}, "market_cache_time": 0.0})


def test_radar_incomplete_error_walk_leaves_caches_untouched(capital_env, monkeypatch):
    disk = capital_env["tmp"] / "markets.json"
    monkeypatch.setattr(radar_cc, "CAPITAL_MARKET_DISK_CACHE_PATH", str(disk))
    good = [{"epic": "GOOD", "instrumentName": "Good"}]
    disk.write_text('{"markets": [{"epic": "GOOD"}], "ts": 1}', encoding="utf-8")
    radar_cc._SHARED_MARKET_CACHE.update(
        {"markets": list(good), "market_index": {}, "market_cache_time": 1.0}
    )
    client = radar_cc.CapitalClient()
    client.market_cache = list(good)
    before = disk.read_text(encoding="utf-8")

    def walk(method, path, **kwargs):
        raise RuntimeError("connection reset mid-walk")

    monkeypatch.setattr(client, "_request", walk)
    client.get_all_markets(force_refresh=True)
    assert radar_cc._SHARED_MARKET_CACHE["markets"] == good
    assert client.market_cache == good
    assert disk.read_text(encoding="utf-8") == before
    radar_cc._SHARED_MARKET_CACHE.update({"markets": [], "market_index": {}, "market_cache_time": 0.0})
