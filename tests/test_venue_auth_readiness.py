"""Spot-route readiness must follow venue auth, not client construction.

Fake key strings only. The HTTP layer is mocked and a real socket call is a
failure. No orders are placed.
"""

from __future__ import annotations

import importlib.util
import json
import logging
import os
import time
from pathlib import Path

import pytest
import requests

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")

from aureon.exchanges.alpaca_client import AlpacaClient
from aureon.exchanges.binance_client import BinanceClient


ALPACA_AUTH_BODY = json.dumps(
    {"code": 40110000, "message": "request is not authorized"}
)
BINANCE_ACCOUNT_BODY = json.dumps(
    {
        "accountType": "SPOT",
        "canTrade": False,
        "permissions": ["SPOT"],
    }
)


class _BlockedSession:
    """Stand-in that refuses every call until a test installs a scripted one."""

    def __init__(self) -> None:
        self.headers: dict[str, str] = {}
        self.calls: list[str] = []

    def request(self, method, url, **kwargs):
        raise AssertionError(f"network blocked: {method} {url}")

    def get(self, url, **kwargs):
        raise AssertionError(f"network blocked: GET {url}")

    def send(self, *args, **kwargs):
        raise AssertionError("network blocked: session.send")

    def mount(self, *args, **kwargs):
        return None

    def close(self) -> None:
        return None


class _Response:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text
        self.headers: dict[str, str] = {}
        self.ok = 200 <= status_code < 300

    def json(self):
        return json.loads(self.text)


class _ScriptedSession(_BlockedSession):
    def __init__(self, handler) -> None:
        super().__init__()
        self._handler = handler

    def request(self, method, url, **kwargs):
        self.calls.append(f"{method} {url}")
        return self._handler(method, url, **kwargs)

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)


def _block_real_http(monkeypatch) -> None:
    def blocked(*args, **kwargs):
        raise AssertionError("network blocked")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
    monkeypatch.setattr(requests.sessions.Session, "send", blocked)
    monkeypatch.setattr(requests.sessions.Session, "get", blocked)


def _alpaca(monkeypatch) -> AlpacaClient:
    monkeypatch.setenv("ALPACA_API_KEY", "fake-alpaca-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "fake-alpaca-secret")
    monkeypatch.setenv("ALPACA_DRY_RUN", "false")
    monkeypatch.setenv("ALPACA_PAPER", "false")
    monkeypatch.delenv("PROMETHEUS_METRICS_PORT", raising=False)
    client = AlpacaClient()
    client._rate_limiter = type(
        "NoWait",
        (),
        {
            "wait_trading": lambda self: None,
            "wait_data": lambda self: None,
            "on_429_error": lambda self: None,
        },
    )()
    client._global_rate_budget = None
    client._account_cache = type(
        "NoCache",
        (),
        {"get": lambda self, key: None, "set": lambda self, key, value, ttl=None: None},
    )()
    return client


def _binance(monkeypatch) -> BinanceClient:
    monkeypatch.setenv("BINANCE_API_KEY", "fake-binance-key")
    monkeypatch.setenv("BINANCE_API_SECRET", "fake-binance-secret")
    monkeypatch.setenv("BINANCE_DRY_RUN", "false")
    monkeypatch.setenv("BINANCE_UK_MODE", "true")
    client = BinanceClient()
    client._rate_limiter = None
    client._time_sync_timestamp = 10**12
    return client


def _trader():
    helper_path = Path(__file__).with_name("test_unified_market_trader.py")
    spec = importlib.util.spec_from_file_location(
        "unified_market_trader_auth_helper", helper_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    trader = module.UnifiedMarketTraderTests()._make_trader()
    trader.capital.status_lines = lambda: ["CAPITAL: session ready"]
    trader.kraken._latest_status_lines = ["KRAKEN: ready"]
    trader._kraken_spot_fast_profit_state = {
        "enabled": False,
        "open_positions": [],
        "closed_positions": [],
        "last_check": {},
    }
    trader.kraken_ready = True
    trader.capital_ready = True
    trader._kraken_tradable_symbols = lambda: {"BTCUSD": "XXBTZUSD"}
    trader._kraken_spot_tradable_symbols = lambda: {"BTCUSD": "XBTUSD"}
    trader._capital_tradable_symbols = lambda: {"BTCUSD": "BTCUSD"}
    trader._alpaca_tradable_symbols = lambda: {"BTCUSD": "BTC/USD"}
    trader._binance_tradable_symbols = lambda: {"BTCUSD": "BTCUSDT"}
    return trader


def _lines(trader) -> list[str]:
    import sys

    lines = list(trader.get_status_lines())
    printed: list[str] = []

    def capture(*args, **kwargs):
        printed.append(" ".join(str(arg) for arg in args))

    module = sys.modules[trader.__class__.__module__]
    original = module._safe_print
    module._safe_print = capture
    try:
        trader.print_status()
    finally:
        module._safe_print = original
    lines.extend(printed)
    return lines


def _route_map(trader) -> dict[tuple[str, str], dict]:
    central_beat = {
        "symbols": {
            "BTCUSD": {
                "strength": 0.9,
                "confidence": 0.88,
                "support_count": 4,
                "side": "BUY",
                "sources": ["kraken", "capital", "alpaca", "binance"],
                "reference_price": 50000.0,
                "change_pct": 1.2,
            }
        }
    }
    order_flow = trader._build_global_order_flow_feed(
        {}, {}, central_beat, {"symbols": {"BTCUSD": 0.9}}
    )
    routes = order_flow["active_order_flow"][0]["execution_routes"]
    return {(route["venue"], route["market_type"]): route for route in routes}


def test_unchecked_alpaca_is_not_spot_route_ready(monkeypatch):
    _block_real_http(monkeypatch)
    alpaca = _alpaca(monkeypatch)
    alpaca.session = _BlockedSession()
    trader = _trader()
    trader.alpaca = alpaca
    trader.alpaca_error = ""
    trader.binance = None

    text = "\n".join(_lines(trader))

    assert "spot_route_ready | ok" not in text
    assert "ALPACA: spot_route_not_ready | alpaca auth unchecked" in text
    assert alpaca.session.calls == []


def test_alpaca_40110000_is_not_ready_and_binance_success_stays_ready(monkeypatch):
    _block_real_http(monkeypatch)
    alpaca = _alpaca(monkeypatch)
    binance = _binance(monkeypatch)

    def alpaca_http(method, url, **kwargs):
        assert kwargs.get("json") in (None, {})
        if str(url).endswith("/v2/account"):
            return _Response(401, ALPACA_AUTH_BODY)
        if "data.alpaca.markets" in str(url):
            return _Response(200, "{}")
        raise AssertionError(f"unexpected alpaca url {url}")

    def binance_http(method, url, **kwargs):
        assert method.upper() == "GET"
        if str(url).endswith("/api/v3/account"):
            return _Response(200, BINANCE_ACCOUNT_BODY)
        raise AssertionError(f"unexpected binance url {url}")

    alpaca.session = _ScriptedSession(alpaca_http)
    binance.session = _ScriptedSession(binance_http)

    account = alpaca.get_account()
    assert account == {}
    binance_account = binance.account()
    assert binance_account["accountType"] == "SPOT"
    assert len(alpaca.session.calls) == 1
    assert len(binance.session.calls) == 1

    trader = _trader()
    trader.alpaca = alpaca
    trader.alpaca_error = ""
    trader.binance = binance
    trader.binance_error = ""
    trader._binance_diag = {
        "network_ok": True,
        "account_ok": True,
        "margin_available": False,
        "uk_mode": True,
        "auth_status": "verified",
        "auth_reason": "ok",
    }

    before_status = (len(alpaca.session.calls), len(binance.session.calls))
    text = "\n".join(_lines(trader))
    assert (len(alpaca.session.calls), len(binance.session.calls)) == before_status

    assert "ALPACA: spot_route_not_ready | alpaca auth rejected 40110000" in text
    assert "spot_route_ready | ok" not in text.split("BINANCE:")[0]
    assert "BINANCE: spot_route_ready" in text
    assert "account_ready=True" in text
    binance_line = next(line for line in text.splitlines() if "BINANCE:" in line and "spot_route" in line)
    assert "| ok" in binance_line
    assert "not_ready" not in binance_line
    assert "40110000" not in binance_line

    preflight = {item["name"]: item for item in trader._build_preflight_report()["items"]}
    assert preflight["alpaca_spot_execution_route"]["ok"] is False
    assert "alpaca auth rejected 40110000" in preflight["alpaca_spot_execution_route"]["detail"]
    assert preflight["binance_spot_margin_execution_route"]["ok"] is True

    routes = _route_map(trader)
    assert routes[("alpaca", "spot")]["ready"] is False
    assert "alpaca auth rejected 40110000" in routes[("alpaca", "spot")]["blockers"]
    assert routes[("binance", "spot")]["ready"] is True
    assert routes[("kraken", "margin")]["ready"] is True
    assert routes[("capital", "cfd")]["ready"] is True

    # A later public-data success must not clear the auth rejection.
    alpaca._request(
        "GET",
        "/v1beta3/crypto/latest/quotes",
        params={"symbols": "BTC/USD"},
        base_url=alpaca.data_url,
        request_type="data",
    )
    text_after_data = "\n".join(trader.get_status_lines())
    assert "alpaca auth rejected 40110000" in text_after_data
    assert "ALPACA: spot_route_ready | ok" not in text_after_data

    def alpaca_ok(method, url, **kwargs):
        if str(url).endswith("/v2/account"):
            return _Response(200, '{"id":"fake-account","status":"ACTIVE"}')
        raise AssertionError(f"unexpected alpaca url {url}")

    alpaca.session = _ScriptedSession(alpaca_ok)
    recovered = alpaca.get_account()
    assert recovered.get("status") == "ACTIVE"
    assert len(alpaca.session.calls) == 1

    text_recovered = "\n".join(trader.get_status_lines())
    assert "ALPACA: spot_route_ready | ok" in text_recovered
    assert "BINANCE: spot_route_ready" in text_recovered
    routes = _route_map(trader)
    assert routes[("alpaca", "spot")]["ready"] is True
    assert routes[("binance", "spot")]["ready"] is True


def test_data_api_403_does_not_reject_a_verified_alpaca_client(monkeypatch):
    _block_real_http(monkeypatch)
    alpaca = _alpaca(monkeypatch)
    alpaca._set_auth_outcome("verified", "ok")
    alpaca.session = _ScriptedSession(
        lambda method, url, **kwargs: _Response(
            403,
            '{"message":"subscription does not permit recent SIP data"}',
        )
    )

    alpaca._request(
        "GET",
        "/v2/stocks/bars",
        params={"symbols": "AAPL", "feed": "sip"},
        base_url=alpaca.data_url,
        request_type="data",
    )

    assert alpaca.session.calls == ["GET https://data.alpaca.markets/v2/stocks/bars"]
    assert alpaca.auth_status == "verified"
    assert alpaca.auth_reason == "ok"
    assert alpaca.auth_verified is True


def test_positions_40110000_rejects_alpaca_without_a_retry(monkeypatch):
    _block_real_http(monkeypatch)
    monkeypatch.setenv("ALPACA_RETRY_COUNT", "5")
    alpaca = _alpaca(monkeypatch)
    assert alpaca.max_retries == 5
    alpaca._set_auth_outcome("verified", "ok")
    alpaca.session = _ScriptedSession(
        lambda method, url, **kwargs: _Response(401, ALPACA_AUTH_BODY)
    )

    result = alpaca._request("GET", "/v2/positions", request_type="trading")

    assert result == {}
    assert alpaca.session.calls == ["GET https://api.alpaca.markets/v2/positions"]
    assert alpaca.auth_status == "rejected"
    assert alpaca.auth_reason == "alpaca auth rejected 40110000"


def test_rejected_alpaca_and_binance_keys_never_submit_or_retry(monkeypatch):
    """A refused key stops before place_market_order and before the retry loop."""

    _block_real_http(monkeypatch)
    monkeypatch.setenv("ALPACA_RETRY_COUNT", "5")
    alpaca = _alpaca(monkeypatch)
    binance = _binance(monkeypatch)
    binance.max_retries = 4
    alpaca.session = _ScriptedSession(
        lambda method, url, **kwargs: _Response(401, ALPACA_AUTH_BODY)
    )
    binance.session = _ScriptedSession(
        lambda method, url, **kwargs: _Response(
            401,
            '{"code":-2015,"msg":"Invalid API-key, IP, or permissions for action."}',
        )
    )

    alpaca._request("GET", "/v2/positions", request_type="trading")
    with pytest.raises(RuntimeError):
        binance.account()

    assert alpaca.session.calls == ["GET https://api.alpaca.markets/v2/positions"]
    assert binance.session.calls == ["GET https://api.binance.com/api/v3/account"]
    assert alpaca.auth_status == "rejected"
    assert binance.auth_status == "rejected"
    assert "40110000" in alpaca.auth_reason
    assert binance.auth_reason.startswith("binance auth rejected")

    alpaca.session = _BlockedSession()
    binance.session = _BlockedSession()
    submits: list[str] = []

    def _refuse_submit(venue):
        def submit(*args, **kwargs):
            submits.append(venue)
            raise AssertionError(f"{venue} order submit")

        return submit

    alpaca.place_market_order = _refuse_submit("alpaca")
    binance.place_market_order = _refuse_submit("binance")
    binance.place_margin_order = _refuse_submit("binance-margin")

    trader = _trader()
    trader.alpaca = alpaca
    trader.binance = binance
    trader.alpaca_error = ""
    trader.binance_error = ""
    trader.kraken_ready = False
    trader.capital_ready = False
    trader._dynamic_intelligence_budget = {"schema_version": 1, "exchanges": {}}
    trader._binance_diag = {
        "network_ok": True,
        "account_ok": False,
        "margin_available": False,
        "uk_mode": True,
    }
    alpaca.get_crypto_orderbook = lambda *args, **kwargs: {}
    alpaca.get_account_balance = lambda: {}
    alpaca.get_positions = lambda: []
    trader._execution_blockers = lambda payload, action_plan: []
    trader._persist_execution_summary = lambda summary: None

    routes = _route_map(trader)
    assert routes[("alpaca", "spot")]["ready"] is False
    assert "alpaca auth rejected 40110000" in routes[("alpaca", "spot")]["blockers"]
    assert routes[("binance", "spot")]["ready"] is False
    assert routes[("binance", "spot")]["blockers"]

    order_flow = trader._build_global_order_flow_feed(
        {},
        {},
        {
            "symbols": {
                "BTCUSD": {
                    "strength": 0.9,
                    "confidence": 0.88,
                    "support_count": 4,
                    "side": "BUY",
                    "sources": ["alpaca", "binance"],
                    "reference_price": 50000.0,
                    "change_pct": 1.2,
                }
            }
        },
        {"symbols": {"BTCUSD": 0.9}},
    )
    summary = trader._execute_runtime_order_actions(
        {
            "shared_order_flow": order_flow,
            "exchange_action_plan": {"order_intent_publish_enabled": True},
            "combined": {"open_positions": 0},
        }
    )

    assert submits == []
    assert summary["submitted_count"] == 0
    assert summary["attempted_count"] == 0
    assert alpaca.session.calls == []
    assert binance.session.calls == []


def test_data_host_40110000_rejects_alpaca_auth(monkeypatch):
    """Alpaca uses 40110000 for a bad key on every host, including the data API."""

    _block_real_http(monkeypatch)
    alpaca = _alpaca(monkeypatch)
    alpaca._set_auth_outcome("verified", "ok", source="account")
    alpaca.session = _ScriptedSession(
        lambda method, url, **kwargs: _Response(403, ALPACA_AUTH_BODY)
    )

    alpaca._request(
        "GET",
        "/v2/stocks/bars",
        params={"symbols": "AAPL"},
        base_url=alpaca.data_url,
        request_type="data",
    )

    assert alpaca.auth_status == "rejected"
    assert alpaca.auth_reason == "alpaca auth rejected 40110000"
    assert alpaca.is_authenticated is False
    assert alpaca.session.calls == ["GET https://data.alpaca.markets/v2/stocks/bars"]


def test_place_order_after_rejection_does_not_submit(monkeypatch):
    _block_real_http(monkeypatch)
    alpaca = _alpaca(monkeypatch)
    alpaca._set_auth_outcome(
        "rejected",
        "alpaca auth rejected 40110000",
        source="trading:/v2/positions",
    )
    alpaca.session = _BlockedSession()

    market = alpaca.place_market_order("AAPL", "buy", quantity=1)
    direct = alpaca.place_order("AAPL", 1, "buy")

    assert alpaca.is_authenticated is False
    assert market["submitted"] is False
    assert market["reason"] == "auth rejected"
    assert direct["submitted"] is False
    assert direct["reason"] == "auth rejected"
    assert alpaca.session.calls == []


def test_mid_tick_position_rejection_stops_the_sell(monkeypatch):
    _block_real_http(monkeypatch)
    alpaca = _alpaca(monkeypatch)
    alpaca._set_auth_outcome("verified", "ok", source="account")
    submits: list[str] = []

    def free_balance(_asset):
        alpaca.auth_status = "rejected"
        alpaca.auth_reason = "alpaca auth rejected 40110000"
        alpaca.is_authenticated = False
        return 1.5

    def refuse_submit(*args, **kwargs):
        submits.append("alpaca")
        raise AssertionError("alpaca order submit")

    alpaca.get_free_balance = free_balance
    alpaca.place_market_order = refuse_submit
    trader = _trader()
    trader.alpaca = alpaca
    trader._runtime_real_orders_allowed = lambda: True
    trader._fresh_route_price_receipt = lambda venue, symbol: {
        "status": "live",
        "data_status": "live",
        "price": 100.0,
        "actionable": True,
    }

    result = trader._execute_alpaca_spot_route("SELL", "BTCUSD", 50.0)

    assert submits == []
    assert result["submitted"] is False
    assert "auth rejected" in str(result.get("reason") or "")


def test_expired_alpaca_verification_is_no_reading(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="aureon.exchanges.alpaca_client")
    _block_real_http(monkeypatch)
    monkeypatch.setenv("AUREON_VENUE_AUTH_TTL_S", "300")
    alpaca = _alpaca(monkeypatch)
    alpaca._set_auth_outcome("verified", "ok", source="trading:/v2/account")
    alpaca.auth_verified_at = time.time() - 301
    alpaca.session = _BlockedSession()
    trader = _trader()
    trader.alpaca = alpaca
    trader.binance = None
    trader._boot_balances = {
        "alpaca": {"alive": True, "error": "", "equity": 25.0, "detail": {}},
    }

    report = trader._alpaca_spot_route_readiness()
    budget = trader._build_dynamic_intelligence_budget({}, {})
    before = len(alpaca.session.calls)
    receipt = alpaca.place_order("AAPL", 1, "buy")

    assert report["ready"] is False
    assert "unverified" in report["reason"]
    assert trader._exchange_connected_for_budget("alpaca") is False
    assert budget["exchanges"]["alpaca"]["connected"] is False
    assert budget["exchanges"]["alpaca"]["role"] == "offline"
    assert "alpaca" not in budget["execution_priority_exchanges"]
    assert "alpaca" not in budget["sensor_priority_exchanges"]
    assert receipt["submitted"] is False
    assert receipt["reason"] == "auth unverified"
    assert len(alpaca.session.calls) == before
    assert any(
        "source=ttl" in record.message and "status=unverified" in record.message
        for record in caplog.records
    )


def test_stale_binance_startup_snapshot_is_no_reading(monkeypatch):
    _block_real_http(monkeypatch)
    monkeypatch.setenv("AUREON_VENUE_AUTH_TTL_S", "300")
    trader = _trader()
    trader.binance = object()
    trader._binance_diag = {
        "network_ok": True,
        "account_ok": True,
        "auth_status": "verified",
        "auth_reason": "ok",
    }
    trader._binance_diag_at = time.time() - 301
    trader._boot_balances = {
        "binance": {"alive": True, "error": "", "equity": 40.0, "detail": {}},
    }

    report = trader._binance_spot_route_readiness()
    budget = trader._build_dynamic_intelligence_budget({}, {})

    assert report["ready"] is False
    assert report["reason"] == "binance auth unverified"
    assert trader._exchange_connected_for_budget("binance") is False
    assert budget["exchanges"]["binance"]["connected"] is False
    assert budget["exchanges"]["binance"]["role"] == "offline"
    assert "binance" not in budget["execution_priority_exchanges"]
    assert "binance" not in budget["sensor_priority_exchanges"]
