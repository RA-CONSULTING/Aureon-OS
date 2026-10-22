from __future__ import annotations

import sys
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "requests" not in sys.modules:  # Provide a stub if requests isn't installed.
    requests_stub = types.ModuleType("requests")

    def _unpatched_request(*args, **kwargs):  # pragma: no cover - safety guard
        raise RuntimeError("requests.request was called before being monkeypatched")

    requests_stub.request = _unpatched_request
    sys.modules["requests"] = requests_stub

import scripts.binance_trading_bot as bot  # noqa: E402


class _DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def _capture_request(monkeypatch, payload):
    captured = {}

    def _fake_request(method, url, params=None, headers=None, timeout=None):  # noqa: D401
        captured["method"] = method
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _DummyResponse(payload)

    monkeypatch.setattr(bot.requests, "request", _fake_request)
    monkeypatch.setattr(bot, "_timestamp_ms", lambda: 1700000000000)
    return captured


def _assert_signature(config, params):
    signature = params["signature"]
    unsigned = {k: v for k, v in params.items() if k != "signature"}
    assert signature == bot._hmac_signature(config.api_secret, unsigned)


def test_new_order_payload(monkeypatch):
    captured = _capture_request(monkeypatch, {"status": "ok"})
    config = bot.TradingConfig(api_key="key", api_secret="secret")
    client = bot.BinanceRESTClient(config)

    result = client.new_order(
        symbol="BTCUSDT",
        side="BUY",
        order_type="LIMIT",
        time_in_force="GTC",
        quantity=0.5,
        price=25000.123456,
        new_client_order_id="abc123",
        strategy_id=123456,
        recv_window=5000,
        extra_params={"foo": "bar"},
    )

    assert result == {"status": "ok"}
    assert captured["method"] == "POST"
    assert captured["url"] == f"{config.base_url}/api/v3/order"
    params = captured["params"]
    assert params["symbol"] == "BTCUSDT"
    assert params["quantity"] == "0.5"
    assert params["price"] == "25000.123456"
    assert params["timeInForce"] == "GTC"
    assert params["newClientOrderId"] == "abc123"
    assert params["strategyId"] == "123456"
    assert params["recvWindow"] == "5000"
    assert params["foo"] == "bar"
    assert params["timestamp"] == "1700000000000"
    _assert_signature(config, params)


def test_cancel_order_payload(monkeypatch):
    captured = _capture_request(monkeypatch, {"status": "CANCELED"})
    config = bot.TradingConfig(api_key="key", api_secret="secret")
    client = bot.BinanceRESTClient(config)

    result = client.cancel_order(
        symbol="ETHUSDT",
        order_id=42,
        new_client_order_id="cancel-42",
        cancel_restrictions="ONLY_NEW",
        recv_window=1500.5,
    )

    assert result == {"status": "CANCELED"}
    assert captured["method"] == "DELETE"
    assert captured["url"] == f"{config.base_url}/api/v3/order"
    params = captured["params"]
    assert params["orderId"] == "42"
    assert params["newClientOrderId"] == "cancel-42"
    assert params["cancelRestrictions"] == "ONLY_NEW"
    assert params["recvWindow"] == "1500.5"
    _assert_signature(config, params)


def test_cancel_replace_order_payload(monkeypatch):
    captured = _capture_request(monkeypatch, {"cancelResult": "SUCCESS"})
    config = bot.TradingConfig(api_key="key", api_secret="secret")
    client = bot.BinanceRESTClient(config)

    result = client.cancel_replace_order(
        symbol="BTCUSDT",
        side="SELL",
        order_type="LIMIT",
        cancel_replace_mode="STOP_ON_FAILURE",
        cancel_order_id=99,
        cancel_new_client_order_id="cancel-99",
        new_client_order_id="new-100",
        quantity=0.25,
        price=28000,
        time_in_force="GTC",
        order_rate_limit_exceeded_mode="CANCEL_ONLY",
        recv_window=2500,
    )

    assert result == {"cancelResult": "SUCCESS"}
    params = captured["params"]
    assert params["cancelReplaceMode"] == "STOP_ON_FAILURE"
    assert params["cancelOrderId"] == "99"
    assert params["cancelNewClientOrderId"] == "cancel-99"
    assert params["newClientOrderId"] == "new-100"
    assert params["quantity"] == "0.25"
    assert params["price"] == "28000"
    assert params["timeInForce"] == "GTC"
    assert params["orderRateLimitExceededMode"] == "CANCEL_ONLY"
    assert params["recvWindow"] == "2500"
    _assert_signature(config, params)


def test_new_order_list_oco_prefix(monkeypatch):
    captured = _capture_request(monkeypatch, {"orderListId": 1})
    config = bot.TradingConfig(api_key="key", api_secret="secret")
    client = bot.BinanceRESTClient(config)

    result = client.new_order_list_oco(
        symbol="BTCUSDT",
        side="SELL",
        quantity=1.5,
        above_type="STOP_LOSS_LIMIT",
        below_type="LIMIT_MAKER",
        list_client_order_id="list-123",
        above_options={
            "client_order_id": "above-1",
            "stop_price": 29000,
            "price": 29500,
            "time_in_force": "GTC",
        },
        below_options={
            "client_order_id": "below-1",
            "price": 31000,
            "iceberg_qty": 0.5,
        },
    )

    assert result == {"orderListId": 1}
    params = captured["params"]
    assert params["aboveClientOrderId"] == "above-1"
    assert params["aboveStopPrice"] == "29000"
    assert params["abovePrice"] == "29500"
    assert params["aboveTimeInForce"] == "GTC"
    assert params["belowClientOrderId"] == "below-1"
    assert params["belowPrice"] == "31000"
    assert params["belowIcebergQty"] == "0.5"
    _assert_signature(config, params)


def test_test_new_sor_order_supports_commission(monkeypatch):
    captured = _capture_request(monkeypatch, {})
    config = bot.TradingConfig(api_key="key", api_secret="secret")
    client = bot.BinanceRESTClient(config)

    result = client.test_new_sor_order(
        symbol="BTCUSDT",
        side="BUY",
        order_type="LIMIT",
        quantity=0.1,
        price=31000,
        time_in_force="GTC",
        compute_commission_rates=True,
    )

    assert result == {}
    params = captured["params"]
    assert params["computeCommissionRates"] == "true"
    assert params["quantity"] == "0.1"
    assert params["price"] == "31000"
    assert params["timeInForce"] == "GTC"
    _assert_signature(config, params)
