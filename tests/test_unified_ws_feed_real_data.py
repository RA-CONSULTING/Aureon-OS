"""Regression tests for the unified feed's real-data provenance boundary.

All numeric payloads in this module are explicitly labeled provider-shape test
fixtures.  Production code must never generate equivalent observations.
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from aureon.data_feeds.unified_ws_feed import (
    NormalizedTick,
    UnifiedWSFeed,
    parse_binance_tick,
    parse_capital_tick,
    parse_coinbase_tick,
    parse_coingecko_tick,
    parse_kraken_tick,
)


RECEIVED_AT_FIXTURE = 1_700_000_001.0
SOURCE_TIME_MS_FIXTURE = 1_700_000_000_000


def _binance_payload_fixture(**updates: Any) -> dict[str, Any]:
    payload = {
        "s": "BTCUSDT",
        "b": "49999.0",
        "a": "50001.0",
        "c": "50000.0",
        "v": "125.5",
        "P": "1.25",
        "E": SOURCE_TIME_MS_FIXTURE,
    }
    payload.update(updates)
    return payload


@pytest.mark.parametrize("missing", ["s", "b", "a", "c"])
def test_binance_required_quote_fields_must_be_observed(missing: str) -> None:
    payload = _binance_payload_fixture()
    payload.pop(missing)

    assert parse_binance_tick(payload, received_at=RECEIVED_AT_FIXTURE) is None


def test_binance_tick_keeps_provider_and_receipt_clocks_separate() -> None:
    tick = parse_binance_tick(
        _binance_payload_fixture(),
        received_at=RECEIVED_AT_FIXTURE,
    )

    assert tick is not None
    assert tick.source_timestamp == 1_700_000_000.0
    assert tick.received_at == RECEIVED_AT_FIXTURE
    assert tick.timestamp == tick.source_timestamp
    assert tick.is_source_fresh(now=1_700_000_030.0)
    assert not tick.is_source_fresh(now=1_700_000_061.0)
    assert tick.to_dict()["generated_values"] is False


def test_missing_provider_timestamp_is_not_replaced_with_receipt_time() -> None:
    payload = _binance_payload_fixture()
    payload.pop("E")

    tick = parse_binance_tick(payload, received_at=RECEIVED_AT_FIXTURE)

    assert tick is not None
    assert tick.source_timestamp is None
    assert tick.timestamp is None
    assert tick.received_at == RECEIVED_AT_FIXTURE
    assert tick.to_dict()["source_timestamp"] is None
    assert not tick.is_source_fresh(now=RECEIVED_AT_FIXTURE)


def test_missing_provider_volume_stays_unknown() -> None:
    payload = _binance_payload_fixture()
    payload.pop("v")

    tick = parse_binance_tick(payload, received_at=RECEIVED_AT_FIXTURE)

    assert tick is not None
    assert tick.volume_24h is None


def test_invalid_or_crossed_quotes_are_not_emitted() -> None:
    assert parse_binance_tick(
        _binance_payload_fixture(b="0"),
        received_at=RECEIVED_AT_FIXTURE,
    ) is None
    assert parse_binance_tick(
        _binance_payload_fixture(b="50002", a="50001"),
        received_at=RECEIVED_AT_FIXTURE,
    ) is None


def test_kraken_parser_requires_bid_ask_and_last_but_does_not_invent_time() -> None:
    ticker_fixture = {
        "b": ["50000.0", "1", "1"],
        "a": ["50002.0", "1", "1"],
        "c": ["50001.0", "1"],
        "v": ["12.0", "24.0"],
    }

    tick = parse_kraken_tick(
        ticker_fixture,
        "XBT/USD",
        received_at=RECEIVED_AT_FIXTURE,
    )

    assert tick is not None
    assert tick.source_timestamp is None
    assert tick.volume_24h == 24.0
    assert not tick.is_source_fresh(now=RECEIVED_AT_FIXTURE)
    assert parse_kraken_tick(
        {**ticker_fixture, "b": []},
        "XBT/USD",
        received_at=RECEIVED_AT_FIXTURE,
    ) is None


def test_coinbase_and_capital_parsers_reject_incomplete_quotes() -> None:
    coinbase_fixture = {
        "product_id": "ETH-USD",
        "best_bid": "2999.0",
        "best_ask": "3001.0",
        "price": "3000.0",
        "timestamp": "2023-11-14T22:13:20Z",
    }
    capital_fixture = {
        "epic": "AAPLUSD",
        "bid": "199.9",
        "offer": "200.1",
        "mid": "200.0",
        "timestamp": SOURCE_TIME_MS_FIXTURE,
    }

    assert parse_coinbase_tick(
        coinbase_fixture,
        received_at=RECEIVED_AT_FIXTURE,
    ) is not None
    assert parse_coinbase_tick(
        {key: value for key, value in coinbase_fixture.items() if key != "best_ask"},
        received_at=RECEIVED_AT_FIXTURE,
    ) is None
    assert parse_capital_tick(
        capital_fixture,
        received_at=RECEIVED_AT_FIXTURE,
    ) is not None
    assert parse_capital_tick(
        {key: value for key, value in capital_fixture.items() if key != "mid"},
        received_at=RECEIVED_AT_FIXTURE,
    ) is None


def test_coingecko_simple_price_does_not_become_an_approximated_quote() -> None:
    simple_price_fixture = {
        "usd": 50_000.0,
        "usd_24h_change": 1.25,
        "last_updated_at": 1_700_000_000,
    }

    assert parse_coingecko_tick(
        "bitcoin",
        simple_price_fixture,
        received_at=RECEIVED_AT_FIXTURE,
    ) is None


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    def inject_tick(self, tick: NormalizedTick) -> None:
        self.calls.append(tick)

    def add_or_update_node(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


def _isolated_feed() -> tuple[UnifiedWSFeed, _Recorder, _Recorder]:
    feed = object.__new__(UnifiedWSFeed)
    hft = _Recorder()
    harmonic = _Recorder()
    feed.ticks = {}
    feed.hft_engine = hft
    feed.harmonic_field = harmonic
    feed.callbacks = []
    feed.thought_bus = None
    return feed, hft, harmonic


def _tick_fixture(*, source_timestamp: float | None, volume_24h: float | None) -> NormalizedTick:
    received_at = time.time()
    return NormalizedTick(
        symbol="BTC/USDT",
        exchange="binance",
        bid=49_999.0,
        ask=50_001.0,
        last=50_000.0,
        volume_24h=volume_24h,
        source_timestamp=source_timestamp,
        received_at=received_at,
        raw_symbol="BTCUSDT",
    )


def test_harmonic_ingestion_skips_unknown_time_or_volume() -> None:
    feed, hft, harmonic = _isolated_feed()
    now = time.time()

    feed._emit(_tick_fixture(source_timestamp=now, volume_24h=None))
    feed._emit(_tick_fixture(source_timestamp=None, volume_24h=2_500.0))

    assert hft.calls == []
    assert harmonic.calls == []


def test_harmonic_ingestion_uses_only_observed_volume_equation() -> None:
    feed, hft, harmonic = _isolated_feed()
    tick = _tick_fixture(source_timestamp=time.time(), volume_24h=2_500.0)

    feed._emit(tick)

    assert hft.calls == [tick]
    assert len(harmonic.calls) == 1
    assert harmonic.calls[0]["quantity"] == 2.5


def test_observed_zero_volume_remains_zero_not_one() -> None:
    feed, _, harmonic = _isolated_feed()
    tick = _tick_fixture(source_timestamp=time.time(), volume_24h=0.0)

    feed._emit(tick)

    assert harmonic.calls[0]["quantity"] == 0.0


def test_best_tick_excludes_unknown_or_stale_source_time() -> None:
    feed, _, _ = _isolated_feed()
    now = time.time()
    unknown = _tick_fixture(source_timestamp=None, volume_24h=1.0)
    stale = _tick_fixture(source_timestamp=now - 120.0, volume_24h=1.0)
    fresh = _tick_fixture(source_timestamp=now, volume_24h=1.0)
    feed.ticks = {"unknown": unknown, "stale": stale, "fresh": fresh}

    assert feed.get_best_tick("BTC/USDT") is fresh
    feed.ticks = {"unknown": unknown, "stale": stale}
    assert feed.get_best_tick("BTC/USDT") is None
