import time

from aureon.analytics.aureon_whale_onchain_tracker import (
    WhaleExchangeTracker,
    get_exchange_tracker,
)


class _Bus:
    def __init__(self):
        self.records = []

    def publish(self, thought):
        self.records.append(thought)


def _receipt(now):
    return {
        "source_id": "kraken",
        "source_timestamp": now - 2.0,
        "received_at": now - 1.0,
        "receipt_id": "ticker-1",
        "truth_status": "real_observed",
        "generated_values": False,
        "price": 100.0,
    }


def test_tracker_is_inert_until_explicitly_configured_and_receipts_gate_publication():
    assert get_exchange_tracker() is None
    bus = _Bus()
    tracker = WhaleExchangeTracker(threshold_usd=100.0, thought_bus=bus)
    assert tracker.start() is False

    blocked = tracker._emit_whale_event(
        "kraken", "BTC", 2.0, "trade", "large_trade", {"price": 100.0}
    )
    assert blocked["status"] == "no_data"
    assert bus.records == []

    emitted = tracker._emit_whale_event(
        "kraken", "BTC", 2.0, "trade", "large_trade", _receipt(time.time())
    )
    assert emitted["status"] == "real_derived"
    assert len(bus.records) == 1
    payload = bus.records[0].payload
    assert payload["truth_status"] == "real_derived"
    assert payload["generated_values"] is False
    assert payload["eligible_for_action"] is False
    assert payload["eligible_for_accounting"] is False
    assert payload["eligible_for_learning"] is False
    assert "detected_at" not in payload
