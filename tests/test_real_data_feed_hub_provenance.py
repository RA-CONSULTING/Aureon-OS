from __future__ import annotations

from typing import Any, Dict

from aureon.data_feeds.aureon_real_data_feed_hub import RealDataFeedHub


NOW = 1_800_000_000.0


def _contains_numeric(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    if isinstance(value, (int, float, complex)):
        return True
    if isinstance(value, dict):
        return any(_contains_numeric(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_numeric(item) for item in value)
    return False


def _price_receipt(*, generated_values: bool = False) -> Dict[str, Any]:
    return {
        "symbol": "BTC/USD",
        "base_asset": "BTC",
        "quote_asset": "USD",
        "price": 100.0,
        "price_currency": "USD",
        "data_status": "live",
        "truth_status": "real_observed",
        "source_id": "provider.market:BTC/USD",
        "source_timestamp": NOW - 2.0,
        "received_at": NOW - 1.0,
        "receipt_id": "market-receipt-1",
        "provider_observation": True,
        "generated_values": generated_values,
        "operational_eligible": True,
    }


def _intel_meta(receipt_id: str) -> Dict[str, Any]:
    return {
        "data_status": "live",
        "truth_status": "real_derived",
        "source_id": "intelligence.engine:BTC/USD",
        "source_timestamp": NOW - 1.0,
        "received_at": NOW - 0.5,
        "receipt_id": receipt_id,
        "input_receipt_ids": ["market-receipt-1"],
        "input_provider_observation": True,
        "generated_values": False,
        "operational_eligible": True,
    }


class RecordingBus:
    def __init__(self) -> None:
        self.records = []

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        self.records.append((topic, payload))


class RecordingEngine:
    def __init__(self, output: Dict[str, Any]) -> None:
        self.output = output
        self.calls = []

    def gather_all_intelligence(self, prices: Dict[str, float]) -> Dict[str, Any]:
        self.calls.append(dict(prices))
        return self.output


def test_constructor_is_inert() -> None:
    hub = RealDataFeedHub()

    assert hub.thought_bus is None
    assert hub.intelligence_engine is None
    assert hub.feed_thread is None
    assert hub.running is False
    assert all(
        stream.last_update is None and stream.latest_events == []
        for stream in hub.consolidated_streams.values()
    )
    start_result = hub.start_continuous_feed()
    assert start_result["data_status"] == "no_data"
    assert hub.feed_thread is None
    assert hub.running is False


def test_unstamped_numeric_prices_fail_closed_without_calling_engine() -> None:
    engine = RecordingEngine({})
    bus = RecordingBus()
    hub = RealDataFeedHub(
        thought_bus=bus,
        intelligence_engine=engine,
        clock=lambda: NOW,
    )

    result = hub.gather_and_distribute({"BTC/USD": 100.0})

    assert result["data_status"] == "no_data"
    assert result["truth_status"] == "no_data"
    assert result["generated_values"] is False
    assert result["actionable"] is False
    assert result["accounting_eligible"] is False
    assert result["learning_eligible"] is False
    assert not _contains_numeric(result)
    assert engine.calls == []
    assert bus.records == []


def test_generated_or_stale_price_receipt_is_rejected() -> None:
    engine = RecordingEngine({})
    hub = RealDataFeedHub(
        intelligence_engine=engine,
        clock=lambda: NOW,
    )
    generated = hub.gather_and_distribute(
        {"BTC/USD": _price_receipt(generated_values=True)}
    )
    stale_receipt = _price_receipt()
    stale_receipt["source_timestamp"] = NOW - 121.0
    stale = hub.gather_and_distribute({"BTC/USD": stale_receipt})

    assert generated["data_status"] == "no_data"
    assert stale["data_status"] == "no_data"
    assert not _contains_numeric(generated)
    assert not _contains_numeric(stale)
    assert engine.calls == []


def test_live_whale_event_preserves_lambda_and_stamps_every_publication() -> None:
    whale = {
        **_intel_meta("whale-receipt-1"),
        "symbol": "BTC/USD",
        "action": "buy",
        "side": "BUY",
        "confidence": 0.82,
        "size_usd": 2500.0,
        "coherence": 0.91,
        "lambda_stability": 0.734,
        "validated": True,
        "validators": {"hnc": 0.88, "auris": 0.9},
        "time_horizon_minutes": 20,
    }
    engine = RecordingEngine(
        {
            "bot_profiles": [],
            "whale_predictions": [whale],
            "momentum_opportunities": {},
            "validated_intelligence": [],
        }
    )
    bus = RecordingBus()
    hub = RealDataFeedHub(
        thought_bus=bus,
        intelligence_engine=engine,
        clock=lambda: NOW,
    )

    summary = hub.gather_and_distribute(
        {"BTC/USD": _price_receipt()}
    )

    assert engine.calls == [{"BTC/USD": 100.0}]
    whale_payloads = [
        payload
        for topic, payload in bus.records
        if topic == "intelligence.whale.prediction"
    ]
    assert len(whale_payloads) == 1
    assert whale_payloads[0]["lambda_stability"] == 0.734
    assert summary["data_status"] == "live"
    for _, payload in bus.records:
        assert payload["source_id"]
        assert payload["source_timestamp"] is not None
        assert payload["received_at"] is not None
        assert payload["receipt_id"]
        assert payload["truth_status"] == "real_derived"
        assert payload["freshness_status"] == "fresh"
        assert payload["generated_values"] is False
        assert payload["actionable"] is False
        assert payload["accounting_eligible"] is False
        assert payload["learning_eligible"] is False


def test_intelligence_not_linked_to_price_receipt_is_not_published() -> None:
    whale = {
        **_intel_meta("whale-receipt-2"),
        "symbol": "BTC/USD",
        "action": "buy",
        "side": "BUY",
        "confidence": 0.82,
        "size_usd": 2500.0,
        "coherence": 0.91,
        "lambda_stability": 0.734,
        "validated": True,
        "validators": {"hnc": 0.88},
        "time_horizon_minutes": 20,
    }
    whale["input_receipt_ids"] = ["different-market-receipt"]
    engine = RecordingEngine(
        {
            "bot_profiles": [],
            "whale_predictions": [whale],
            "momentum_opportunities": {},
            "validated_intelligence": [],
        }
    )
    bus = RecordingBus()
    hub = RealDataFeedHub(
        thought_bus=bus,
        intelligence_engine=engine,
        clock=lambda: NOW,
    )

    result = hub.gather_and_distribute(
        {"BTC/USD": _price_receipt()}
    )

    assert result["data_status"] == "no_data"
    assert not _contains_numeric(result)
    assert all(topic == "intelligence.no_data" for topic, _ in bus.records)
    assert hub.consolidated_streams["intelligence"].latest_events == []
