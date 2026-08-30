from __future__ import annotations

import time

from aureon.strategies.s5_live_trader import S5LiveTrader, _binance_ticker_receipt


def _ticker(**updates: object) -> dict:
    now_ms = int(time.time() * 1000)
    row = {
        "symbol": "SOLUSDT",
        "lastPrice": "100.0",
        "bidPrice": "99.5",
        "askPrice": "100.5",
        "volume": "10000",
        "priceChangePercent": "2.5",
        "closeTime": now_ms,
        "lastId": 1234,
    }
    row.update(updates)
    return row


def test_binance_receipt_requires_provider_time_id_and_complete_book() -> None:
    now = time.time()
    receipt = _binance_ticker_receipt(_ticker(closeTime=int(now * 1000)), now)
    assert receipt is not None
    assert receipt["truth_status"] == "real_observed"
    assert receipt["generated_values"] is False
    assert receipt["actionable"] is False

    assert _binance_ticker_receipt(_ticker(volume=None), now) is None
    assert _binance_ticker_receipt(_ticker(bidPrice=None), now) is None
    assert _binance_ticker_receipt(_ticker(lastId=None), now) is None
    assert _binance_ticker_receipt(
        _ticker(closeTime=int((now - 31.0) * 1000)),
        now,
    ) is None


def test_default_constructor_is_dry_and_does_not_create_network() -> None:
    trader = S5LiveTrader()
    assert trader.dry_run is True
    assert trader.network is None
    assert trader.running is False
    assert trader.prices == {}
