from __future__ import annotations

import copy
import os
from datetime import datetime, timezone

import pytest

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")

from aureon.scanners import aureon_alpaca_stock_scanner as scanner_module


NOW = 1_800_000_000.0


def _provider_time(seconds: float) -> str:
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _complete_snapshot() -> dict:
    return {
        "latestTrade": {
            "p": "110.00",
            "s": "25",
            "t": _provider_time(NOW - 2.0),
            "generated_values": False,
        },
        "latestQuote": {
            "bp": "109.90",
            "ap": "110.10",
            "bs": "100",
            "as": "120",
            "t": _provider_time(NOW - 1.0),
            "generated_values": False,
        },
        "dailyBar": {
            "o": "100.00",
            "h": "112.00",
            "l": "99.00",
            "c": "110.00",
            "v": "1000000",
            "t": _provider_time(NOW - 3600.0),
            "generated_values": False,
        },
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
    }


class InMemoryAlpaca:
    def __init__(self, snapshots: dict[str, dict]):
        self.snapshots = snapshots
        self.snapshot_calls = 0

    def get_stock_snapshots(self, symbols):
        self.snapshot_calls += 1
        return {
            symbol: copy.deepcopy(self.snapshots[symbol])
            for symbol in symbols
            if symbol in self.snapshots
        }

    def get_tradable_stock_symbols(self):
        return list(self.snapshots)


def _scanner(monkeypatch, snapshots: dict[str, dict]):
    monkeypatch.setattr(scanner_module, "THOUGHT_BUS_AVAILABLE", False)
    monkeypatch.setattr(scanner_module, "CHIRP_BUS_AVAILABLE", False)
    return scanner_module.AlpacaStockScanner(
        alpaca_client=InMemoryAlpaca(snapshots),
        clock=lambda: NOW,
        quote_max_age_seconds=60.0,
        bar_max_age_seconds=7200.0,
    )


def test_complete_fresh_snapshot_produces_provenanced_opportunity(monkeypatch):
    scanner = _scanner(monkeypatch, {"AAPL": _complete_snapshot()})

    opportunities = scanner.scan_stocks(
        symbols=["AAPL"],
        min_volume=1.0,
        min_price=1.0,
        max_price=1000.0,
    )

    assert len(opportunities) == 1
    opportunity = opportunities[0]
    assert opportunity.symbol == "AAPL"
    assert opportunity.price == 110.0
    assert opportunity.bid == 109.9
    assert opportunity.ask == 110.1
    assert opportunity.timestamp == NOW - 2.0
    assert opportunity.source_timestamp == NOW - 2.0
    assert opportunity.quote_source_timestamp == NOW - 1.0
    assert opportunity.trade_source_timestamp == NOW - 2.0
    assert opportunity.bar_source_timestamp == NOW - 3600.0
    assert isinstance(opportunity.received_at, str)
    assert opportunity.received_at != opportunity.source_timestamp
    assert opportunity.data_status == "live"
    assert opportunity.truth_status == "real_derived"
    assert opportunity.generated_values is False
    assert opportunity.eligible_for_action is True
    assert scanner.last_scan_receipt["data_status"] == "live"
    assert scanner.last_scan_receipt["generated_values"] is False


@pytest.mark.parametrize(
    "case",
    [
        "missing_timestamp",
        "stale_quote",
        "crossed_book",
        "invalid_ohlcv",
        "non_finite_volume",
        "generated",
    ],
)
def test_incomplete_stale_or_generated_snapshot_is_numeric_free_no_data(monkeypatch, case):
    snapshot = _complete_snapshot()
    if case == "missing_timestamp":
        snapshot["latestTrade"].pop("t")
    elif case == "stale_quote":
        snapshot["latestQuote"]["t"] = _provider_time(NOW - 61.0)
    elif case == "crossed_book":
        snapshot["latestQuote"]["bp"] = "111.00"
    elif case == "invalid_ohlcv":
        snapshot["dailyBar"]["h"] = "98.00"
    elif case == "non_finite_volume":
        snapshot["dailyBar"]["v"] = "nan"
    elif case == "generated":
        snapshot["generated_values"] = True

    scanner = _scanner(monkeypatch, {"AAPL": snapshot})
    opportunities = scanner.scan_stocks(symbols=["AAPL"], min_volume=1.0)

    assert opportunities == []
    assert scanner.price_history == {}
    assert scanner.volume_history == {}
    receipt = scanner.last_scan_receipt
    assert receipt["data_status"] == "no_data"
    assert receipt["truth_status"] == "no_data"
    assert receipt["source_timestamp"] is None
    assert receipt["generated_values"] is False
    assert receipt["eligible_for_ranking"] is False
    assert receipt["eligible_for_action"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False
    assert not {"price", "bid", "ask", "volume", "change_pct"}.intersection(receipt)


def test_bulk_volume_filter_has_no_unverified_symbol_fallback(monkeypatch):
    scanner = _scanner(monkeypatch, {})
    symbols = [f"S{index:03d}" for index in range(501)]

    opportunities = scanner.scan_stocks(symbols=symbols, min_volume=1.0)

    assert opportunities == []
    assert scanner.alpaca.snapshot_calls == 1
    assert scanner.last_scan_receipt["data_status"] == "no_data"
    assert scanner.last_scan_receipt["reason"] == "fresh_complete_volume_snapshots_required"
