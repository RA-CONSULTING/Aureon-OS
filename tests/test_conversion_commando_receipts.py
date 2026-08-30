from __future__ import annotations

import time

import pytest

from aureon.conversion.aureon_conversion_commando import GROWTH_AGGRESSION, PairScanner


def _receipt(*, generated: bool = False, age: float = 0.0) -> dict:
    now = time.time()
    return {
        "symbol": "SOLUSDT",
        "exchange": "binance",
        "price": 100.0,
        "change24h": 2.0,
        "volume": 1_000_000.0,
        "source_id": "binance:SOLUSDT:24h",
        "source_timestamp": now - age,
        "received_at": now,
        "receipt_id": "ticker-1",
        "truth_status": "real_observed",
        "generated_values": generated,
    }


def test_scanner_requires_fresh_same_venue_receipts_and_evicts_stale_targets() -> None:
    scanner = PairScanner()

    assert scanner.scan_all_pairs({"SOLUSDT": _receipt(generated=True)}) == []
    assert scanner.scan_count == 0
    assert scanner.last_no_data["actionable"] is False

    targets = scanner.scan_all_pairs({"SOLUSDT": _receipt()})
    assert len(targets) == 1
    target = targets[0]
    expected = (2.0 * 0.4 * GROWTH_AGGRESSION) + ((6.0 / 10.0) * 0.2)
    assert target["total_score"] == pytest.approx(expected)
    assert target["exchange"] == "binance"
    assert target["receipt_id"] == "ticker-1"
    assert target["actionable"] is False
    assert scanner.scan_count == 1

    assert scanner.scan_all_pairs({"SOLUSDT": _receipt(age=121.0)}) == []
    assert scanner.scored_targets == []
    assert scanner.last_scan_results == []
    assert scanner.scan_count == 1


def test_missing_market_values_are_no_data_not_zero() -> None:
    scanner = PairScanner()
    incomplete = _receipt()
    incomplete.pop("volume")

    assert scanner.scan_all_pairs({"SOLUSDT": incomplete}) == []
    assert scanner.last_no_data["truth_status"] == "no_data"
    assert scanner.total_pairs_scanned == 0
