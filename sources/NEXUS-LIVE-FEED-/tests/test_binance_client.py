import json
from dataclasses import dataclass

import pytest

from scripts.binance_trading_bot import (
    BinanceAPIError,
    BinanceRESTClient,
    TradingConfig,
)


class DummyHTTPError(RuntimeError):
    pass


@dataclass
class DummyResponse:
    status_code: int
    payload: object

    def json(self):
        if self.payload is None:
            raise ValueError("no json")
        return self.payload

    @property
    def text(self) -> str:
        return json.dumps(self.payload)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise DummyHTTPError(f"HTTP {self.status_code}")


def _client() -> BinanceRESTClient:
    return BinanceRESTClient(TradingConfig())


def test_parse_response_plain_success():
    client = _client()
    response = DummyResponse(200, {"price": "123.45"})
    payload = client._parse_response(response)  # type: ignore[arg-type]
    assert payload == {"price": "123.45"}
    assert client.last_rate_limits is None


def test_parse_response_wrapped_success():
    client = _client()
    wrapper = {
        "id": "abc",
        "status": 200,
        "result": {"price": "42.0"},
        "rateLimits": [{"limit": 50}],
    }
    response = DummyResponse(200, wrapper)
    payload = client._parse_response(response)  # type: ignore[arg-type]
    assert payload == {"price": "42.0"}
    assert client.last_rate_limits == wrapper["rateLimits"]


def test_parse_response_wrapped_error():
    client = _client()
    wrapper = {
        "id": "err",
        "status": 400,
        "error": {"code": -2010, "msg": "Insufficient balance"},
    }
    response = DummyResponse(400, wrapper)
    with pytest.raises(BinanceAPIError) as exc:
        client._parse_response(response)  # type: ignore[arg-type]
    assert exc.value.status == 400
    assert "insufficient balance" in str(exc.value).lower()


def test_parse_response_http_error_payload():
    client = _client()
    payload = {"code": -1102, "msg": "Bad symbol"}
    response = DummyResponse(400, payload)
    with pytest.raises(BinanceAPIError) as exc:
        client._parse_response(response)  # type: ignore[arg-type]
    assert exc.value.status == 400
    assert "bad symbol" in str(exc.value).lower()


def test_get_price_handles_wrapper(monkeypatch):
    client = _client()
    response = DummyResponse(
        200,
        {"status": 200, "result": {"price": "100.50"}},
    )

    def fake_get(*_args, **_kwargs):
        return response

    monkeypatch.setattr("scripts.binance_trading_bot.requests", type("R", (), {"get": staticmethod(fake_get)}))
    price = client.get_price()
    assert price == pytest.approx(100.50)


def test_get_price_missing_field(monkeypatch):
    client = _client()
    response = DummyResponse(200, {"status": 200, "result": {}})

    def fake_get(*_args, **_kwargs):
        return response

    monkeypatch.setattr("scripts.binance_trading_bot.requests", type("R", (), {"get": staticmethod(fake_get)}))
    with pytest.raises(BinanceAPIError):
        client.get_price()
