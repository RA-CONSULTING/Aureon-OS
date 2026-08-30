from __future__ import annotations

from aureon.monitors.grand_big_wheel_telemetry import (
    collect_live_market_data,
    normalize_quote_receipt,
)


NOW = 1_700_000_000.0


def _live_quote(**overrides):
    quote = {
        "bid": 100.0,
        "ask": 102.0,
        "source_timestamp": NOW - 1.0,
        "data_status": "live",
        "truth_status": "real_derived",
        "generated_values": False,
        "action_eligible": True,
    }
    quote.update(overrides)
    return quote


def test_fresh_two_sided_quote_is_derived_without_absent_values():
    receipt = normalize_quote_receipt("BTC/USD", _live_quote(), now=NOW)

    assert receipt["data_status"] == "live"
    assert receipt["truth_status"] == "real_derived"
    assert receipt["price"] == 101.0
    assert receipt["price_derivation"] == "provider_bid_ask_midpoint"
    assert receipt["volume"] is None
    assert receipt["change_pct"] is None
    assert receipt["generated_values"] is False
    assert receipt["eligible_for_analysis"] is True
    assert receipt["eligible_for_action"] is False


def test_missing_stale_and_one_sided_quotes_are_visible_no_data():
    receipts = [
        normalize_quote_receipt("BTC/USD", None, now=NOW),
        normalize_quote_receipt(
            "ETH/USD",
            _live_quote(source_timestamp=NOW - 61.0),
            now=NOW,
        ),
        normalize_quote_receipt(
            "SOL/USD",
            _live_quote(ask=None),
            now=NOW,
        ),
    ]

    assert all(receipt["data_status"] == "no_data" for receipt in receipts)
    assert all(receipt["truth_status"] == "no_data" for receipt in receipts)
    assert all(receipt["price"] is None for receipt in receipts)
    assert all(receipt["eligible_for_action"] is False for receipt in receipts)
    assert all(receipt["generated_values"] is False for receipt in receipts)


def test_collection_keeps_provider_failures_and_partial_coverage_visible():
    class Client:
        def get_ticker(self, symbol):
            if symbol == "BTC/USD":
                return _live_quote()
            if symbol == "ETH/USD":
                raise RuntimeError("provider unavailable")
            return {}

    report = collect_live_market_data(
        Client(),
        ("BTC/USD", "ETH/USD", "SOL/USD"),
        now=NOW,
    )

    assert report["data_status"] == "live"
    assert report["live_symbol_count"] == 1
    assert report["requested_symbol_count"] == 3
    assert report["quotes"]["BTC/USD"]["data_status"] == "live"
    assert report["quotes"]["ETH/USD"]["data_status"] == "no_data"
    assert report["quotes"]["ETH/USD"]["reason"] == (
        "provider_read_failed:RuntimeError"
    )
    assert report["quotes"]["SOL/USD"]["data_status"] == "no_data"
    assert report["eligible_for_action"] is False
    assert report["generated_values"] is False
