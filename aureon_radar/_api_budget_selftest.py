#!/usr/bin/env python3
"""API BUDGET DISCIPLINE — one-shot selftest (no real network).

Tests the wiring of GlobalRateBudget into kraken/capital/binance read paths,
the real daily ceiling in api_communion, and Ollama usage accounting.
Run from repo root with PYTHONUTF8=1.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "aureon-os-upstream"
for _p in (str(ROOT), str(UPSTREAM)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Keep live gates closed and budgets enabled for the test run.
os.environ["KRAKEN_DRY_RUN"] = "true"
os.environ["BINANCE_DRY_RUN"] = "true"
os.environ["AUREON_RATE_BUDGET_ENABLED"] = "1"

PASSED = []
FAILED = []


def _ok(name: str):
    PASSED.append(name)
    print(f"  OK {name}")


def _fail(name: str, exc: Exception):
    FAILED.append((name, exc))
    print(f"  FAIL {name}: {exc}")


def test_global_rate_budget_burst():
    from aureon.core.global_rate_budget import GlobalRateBudget, RequestPriority

    budget = GlobalRateBudget(total_rate_per_second=2.0, total_burst=2.0)
    start = time.time()
    for _ in range(4):
        assert budget.wait_for_slot(RequestPriority.QUOTES) is True
    elapsed = time.time() - start
    stats = budget.get_stats()
    assert stats["requests_processed"]["QUOTES"] >= 4, stats
    # 2 burst tokens + 2 more at 2/s => at least ~1s spacing
    assert elapsed >= 0.9, f"budget spacing too fast: {elapsed:.3f}s"
    _ok("global_rate_budget_burst")


def test_kraken_budget_wiring():
    from aureon.core.global_rate_budget import GlobalRateBudget, RequestPriority, wait_for_slot_deferred
    from exchange_adapters.kraken_adapter import KrakenAdapter

    ka = KrakenAdapter()
    ka._rate_budget = GlobalRateBudget(total_rate_per_second=0.5, total_burst=2.0)
    ka._RequestPriority = RequestPriority
    ka._budget_wait = wait_for_slot_deferred

    ticker_payload = {
        "error": [],
        "result": {
            "XXBTZUSD": {
                "c": ["60000.0"],
                "b": ["59990.0"],
                "a": ["60010.0"],
                "v": ["100.0"],
            }
        },
    }

    class FakeResp:
        def __init__(self, body): self._body = json.dumps(body).encode()
        def read(self): return self._body
        def __enter__(self): return self
        def __exit__(self, *a): pass

    with patch("urllib.request.urlopen", return_value=FakeResp(ticker_payload)):
        start = time.time()
        ka.get_ticker("BTC/USD")
        ka.get_ticker("BTC/USD")
        ka.get_ticker("BTC/USD")
        elapsed = time.time() - start

    stats = ka._rate_budget.get_stats()
    assert stats["requests_processed"]["QUOTES"] >= 3, stats
    assert elapsed >= 1.5, f"kraken budget did not throttle: {elapsed:.3f}s"
    _ok("kraken_budget_wiring")


def test_capital_budget_wiring():
    from aureon.core.global_rate_budget import GlobalRateBudget, RequestPriority, wait_for_slot_deferred
    import capital_client as cc

    # Pre-seed a shared session so the constructor does not hit the network.
    cc._SHARED_SESSION.update({
        "cst": "fake-cst",
        "x_security_token": "fake-token",
        "session_start_time": time.time(),
        "demo_mode": False,
        "rate_limit_until": 0.0,
        "init_error": "",
    })
    os.environ["CAPITAL_API_KEY"] = "fake-key"
    os.environ["CAPITAL_IDENTIFIER"] = "fake-id"
    os.environ["CAPITAL_PASSWORD"] = "fake-pass"

    client = cc.CapitalClient()
    client._rate_budget = GlobalRateBudget(total_rate_per_second=2.0, total_burst=2.0)
    client._RequestPriority = RequestPriority
    client._budget_wait = wait_for_slot_deferred

    call_log: list[tuple[str, str]] = []

    def fake_request(method, url, **kwargs):
        path = url.replace(client.base_url, "")
        call_log.append((method.upper(), path))
        return SimpleNamespace(
            status_code=200,
            text="{}",
            headers={},
            json=lambda: {"accounts": [{"accountId": "A1", "balance": {"balance": 1000.0, "available": 900.0}, "preferred": True}]},
        )

    cc.requests.request = fake_request
    try:
        accounts = client.get_accounts(cache_ttl=0)
        assert accounts, accounts
        positions = client.get_positions()
        # /markets search is a quote-path call; exercise it explicitly.
        search = client._request("GET", "/markets", params={"searchTerm": "AAPL"})
        assert search.status_code == 200

        stats = client._rate_budget.get_stats()
        assert stats["requests_processed"]["POSITIONS"] >= 2, stats
        assert stats["requests_processed"]["QUOTES"] >= 1, stats

        # 429 path must notify the budget.
        cc.requests.request = lambda method, url, **kw: SimpleNamespace(
            status_code=429, text="too-many.requests", headers={},
            json=lambda: {"errorCode": "too-many.requests"},
        )
        client._request("GET", "/accounts")
        assert client._rate_budget.get_stats()["active_backoffs"]["POSITIONS"] > 0
    finally:
        cc.requests.request = __import__("requests").request

    _ok("capital_budget_wiring")


def test_binance_budget_wiring():
    from aureon.core.global_rate_budget import GlobalRateBudget, RequestPriority, wait_for_slot_deferred
    import binance_client as bc

    os.environ["BINANCE_DRY_RUN"] = "true"
    client = bc.BinanceClient()
    client._global_rate_budget = GlobalRateBudget(total_rate_per_second=2.0, total_burst=2.0)
    client._RequestPriority = RequestPriority
    client._budget_wait = wait_for_slot_deferred

    def fake_request(method, url, **kwargs):
        class Resp:
            status_code = 200
            text = "{}"
            headers = {}
            def json(self):
                if "/account" in url:
                    return {"balances": []}
                if "/klines" in url:
                    return []
                return {}
        return Resp()

    client.session.request = fake_request
    try:
        client.account()
        client.get_klines("BTCUSDC", interval="1h", limit=1)
        stats = client._global_rate_budget.get_stats()
        assert stats["requests_processed"]["POSITIONS"] >= 1, stats
        assert stats["requests_processed"]["QUOTES"] >= 1, stats
    finally:
        client.session.request = __import__("requests").Session.request

    _ok("binance_budget_wiring")


def test_communion_daily_ceiling():
    from aureon_fusion import api_communion as ac

    ac.clear_all()
    os.environ["AUREON_COMMUNION_DAILY_BUDGET"] = "2"
    host = "budget-test.invalid"
    url = f"https://{host}/data.json"
    ac._write_disk(url, time.time() - 1.0, None, None, {"hello": "world"})

    class FakeResp:
        status_code = 200
        def read(self): return b'{"fresh": true}'
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def getheader(self, name): return None
        @property
        def headers(self): return {}

    live_calls = []
    def fake_urlopen(req, timeout=None):
        live_calls.append(req.full_url)
        return FakeResp()

    ac.urlrequest.urlopen = fake_urlopen
    try:
        r1 = ac.get_json(url, ttl_s=0.0, min_host_interval=0.0)
        r2 = ac.get_json(url, ttl_s=0.0, min_host_interval=0.0)
        r3 = ac.get_json(url, ttl_s=0.0, min_host_interval=0.0)

        assert r1.get("fresh") is True, r1
        assert r2.get("fresh") is True, r2
        assert r3.get("stale") is True, r3
        assert r3.get("budget_reason") == "daily_budget_exhausted", r3
        assert len(live_calls) == 2, live_calls
    finally:
        ac.urlrequest.urlopen = __import__("urllib.request", fromlist=["urlopen"]).urlopen
        ac.clear_all()

    _ok("communion_daily_ceiling")


def test_ollama_usage_accounting():
    from aureon.ollama_config import (
        OllamaDailyBudgetExceeded,
        check_ollama_daily_budget,
        get_ollama_usage,
        record_ollama_call,
        tracked_ollama_call,
    )

    with tempfile.TemporaryDirectory() as tmp:
        usage_path = Path(tmp) / "ollama_usage.json"
        os.environ["AUREON_OLLAMA_USAGE_PATH"] = str(usage_path)
        os.environ["AUREON_OLLAMA_DAILY_CAP"] = "2"

        record_ollama_call("http://localhost:11434", prompt_text="hello", response_text="hi")
        record_ollama_call("https://ollama.com", prompt_text="world", response_text="yes")
        usage = get_ollama_usage()
        assert usage["calls"] == 2, usage
        assert usage["est_tokens"] > 0, usage
        assert usage["by_host"]["localhost"]["calls"] == 1, usage
        assert usage["by_host"]["ollama.com"]["calls"] == 1, usage
        assert usage_path.exists(), "usage file not persisted"

        try:
            check_ollama_daily_budget("http://localhost:11434")
            raise AssertionError("expected OllamaDailyBudgetExceeded")
        except OllamaDailyBudgetExceeded:
            pass

    # Tracked wrapper under a fresh cap.
    with tempfile.TemporaryDirectory() as tmp2:
        usage_path2 = Path(tmp2) / "ollama_usage.json"
        os.environ["AUREON_OLLAMA_USAGE_PATH"] = str(usage_path2)
        os.environ["AUREON_OLLAMA_DAILY_CAP"] = "10"
        result = tracked_ollama_call(
            "http://localhost:11434",
            lambda: {"response": "synthetic"},
            prompt_text="prompt",
        )
        assert result["response"] == "synthetic"
        assert get_ollama_usage()["calls"] >= 1

    _ok("ollama_usage_accounting")


def main():
    print("API BUDGET DISCIPLINE selftest (no real network)")
    print("=" * 60)
    tests = [
        test_global_rate_budget_burst,
        test_kraken_budget_wiring,
        test_capital_budget_wiring,
        test_binance_budget_wiring,
        test_communion_daily_ceiling,
        test_ollama_usage_accounting,
    ]
    for t in tests:
        try:
            t()
        except Exception as exc:
            _fail(t.__name__, exc)

    print("=" * 60)
    print(f"Passed: {len(PASSED)}/{len(tests)}  Failed: {len(FAILED)}")
    if FAILED:
        for name, exc in FAILED:
            print(f"  - {name}: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
