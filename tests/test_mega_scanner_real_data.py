from __future__ import annotations

import asyncio
import math
import time
from collections import defaultdict
from pathlib import Path

from aureon.scanners import mega_scanner as mega
from scripts.validation.validate_real_data_contract import scan_text_file


def _scanner() -> mega.MegaScanner:
    scanner = object.__new__(mega.MegaScanner)
    scanner.kraken = None
    scanner.binance = None
    scanner.alpaca = None
    scanner.prices = {}
    scanner.volumes = {}
    scanner.changes_24h = {}
    scanner.momentum = defaultdict(float)
    scanner.market_records = {}
    scanner.no_data_by_exchange = {}
    scanner.all_assets = set()
    scanner.exchange_pairs = {
        "kraken": set(),
        "binance": set(),
        "alpaca": set(),
    }
    scanner.opportunities = []
    scanner.last_analysis_status = mega._no_data("scanner", "not_scanned")
    scanner.scan_count = 0
    scanner.last_scan = None
    return scanner


def _assert_numeric_free_no_data(receipt: dict) -> None:
    assert receipt["status"] == "no_data"
    assert receipt["data_status"] == "no_data"
    assert receipt["truth_status"] == "no_data"
    assert receipt["eligible_for_ranking"] is False
    assert receipt["eligible_for_action"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False
    assert all(
        not isinstance(value, (int, float)) or isinstance(value, bool)
        for value in receipt.values()
    )


def _binance_ticker(now: float, **updates) -> dict:
    ticker = {
        "symbol": "BTCUSDT",
        "lastPrice": "101.5",
        "quoteVolume": "2500000",
        "priceChangePercent": "4.25",
        "closeTime": int(now * 1000),
    }
    ticker.update(updates)
    return ticker


def test_only_complete_fresh_binance_receipts_reach_ranking() -> None:
    now = time.time()
    scanner = _scanner()
    payload = [
        _binance_ticker(now),
        _binance_ticker(
            now,
            symbol="ETHUSDT",
            lastPrice="2050",
            quoteVolume="1750000",
            priceChangePercent="-3.5",
        ),
    ]

    summary = scanner._ingest_binance_payload(payload, received_at=now)
    assert summary["status"] == "live"
    assert summary["pairs"] == 2
    assert len(scanner.market_records) == 2
    assert all(record["receipt_id"] for record in scanner.market_records.values())
    assert all(record["generated_values"] is False for record in scanner.market_records.values())

    analysis = asyncio.run(scanner.analyze_opportunities())
    assert analysis["status"] == "live"
    assert [item["type"] for item in scanner.opportunities] == [
        "TOP_GAINER",
        "TOP_LOSER",
    ]
    assert all(
        abs(item["source_timestamp"] - now) <= 0.001
        for item in scanner.opportunities
    )
    assert all(item["eligible_for_action"] is True for item in scanner.opportunities)
    assert all(item["eligible_for_accounting"] is False for item in scanner.opportunities)


def test_stale_generated_incomplete_and_nonfinite_inputs_are_no_data() -> None:
    now = time.time()
    invalid_payloads = [
        [_binance_ticker(now, lastPrice=None)],
        [_binance_ticker(now, quoteVolume=math.nan)],
        [_binance_ticker(now - mega.MAX_MARKET_DATA_AGE_SECONDS - 1)],
        [_binance_ticker(now, generated_values=True)],
        [_binance_ticker(now, closeTime=None)],
    ]
    for payload in invalid_payloads:
        scanner = _scanner()
        result = scanner._ingest_binance_payload(payload, received_at=now)
        _assert_numeric_free_no_data(result)
        assert scanner.market_records == {}
        analysis = asyncio.run(scanner.analyze_opportunities())
        _assert_numeric_free_no_data(analysis)
        assert scanner.opportunities == []

    scanner = _scanner()
    scanner._ingest_binance_payload([_binance_ticker(now)], received_at=now)
    assert scanner.market_records
    denied_refresh = scanner._ingest_binance_payload(
        [_binance_ticker(now, lastPrice=None)],
        received_at=now,
    )
    _assert_numeric_free_no_data(denied_refresh)
    assert scanner.market_records == {}
    assert scanner.prices == {}
    assert scanner.opportunities == []


def test_kraken_and_alpaca_require_complete_receipt_evidence() -> None:
    now = time.time()
    scanner = _scanner()
    kraken_payload = {
        "error": [],
        "result": {
            "XXBTZUSD": {
                "c": ["101.0", "1"],
                "v": ["100", "250"],
                "o": "97.0",
            }
        },
    }
    result = scanner._ingest_kraken_payload(
        kraken_payload,
        source_timestamp=now,
        received_at=now,
        receipt_id="kraken-provider-receipt",
    )
    assert result["status"] == "live"
    record = scanner.market_records["kraken:BTC"]
    assert record["receipt_id"].startswith("kraken-provider-receipt:")
    assert record["source_timestamp"] == now

    unproven = _scanner()._ingest_kraken_payload(
        kraken_payload,
        source_timestamp=None,
        received_at=now,
    )
    _assert_numeric_free_no_data(unproven)

    alpaca = _scanner()
    incomplete_position = [{"symbol": "BTCUSD", "current_price": "101"}]
    _assert_numeric_free_no_data(
        alpaca._ingest_alpaca_positions(incomplete_position)
    )
    assert alpaca.market_records == {}

    complete_position = [{
        "symbol": "BTCUSD",
        "current_price": "101",
        "quote_volume": "500000",
        "change_24h": "1.5",
        "source_id": "alpaca:position_market_receipt",
        "source_timestamp": now,
        "received_at": now,
        "receipt_id": "alpaca-provider-receipt",
        "generated_values": False,
    }]
    proven = alpaca._ingest_alpaca_positions(complete_position)
    assert proven["status"] == "live"
    assert alpaca.market_records["alpaca:BTC"]["eligible_for_ranking"] is True


def test_exact_hardened_validator_is_clean() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / "aureon" / "scanners" / "mega_scanner.py"
    assert scan_text_file(target, root) == []
