from __future__ import annotations

import ast
import json
from pathlib import Path

from aureon.analytics.visualize_market_patterns import (
    APIBufferMonitor,
    _normalise_snapshots,
    _price_status,
    visualize_patterns,
)


NOW = 2_000_000_000.0


def _row(price: float, source_timestamp: float, **updates):
    row = {
        "price": price,
        "truth_status": "real_observed",
        "source_id": "binance:/api/v3/ticker/price",
        "source_timestamp": source_timestamp,
        "received_at": source_timestamp + 0.2,
        "generated_values": False,
    }
    row.update(updates)
    return row


def test_snapshot_gate_keeps_only_fresh_proven_provider_rows():
    payload = {
        "binance": {
            "BTCUSDC": [
                _row(61_000.0, NOW - 20),
                _row(61_100.0, NOW - 10),
                _row(99_999.0, NOW - 5, generated_values=True),
                _row(1.0, NOW - 2_000),
                {"p": 45_000.0, "t": NOW - 1},
            ]
        }
    }

    result = _normalise_snapshots(payload, received_at=NOW)

    rows = result["binance"]["BTCUSDC"]
    assert [row["p"] for row in rows] == [61_000.0, 61_100.0]
    assert all(row["generated_values"] is False for row in rows)
    assert all(row["t"] == row["source_timestamp"] for row in rows)


def test_price_status_does_not_substitute_missing_or_stale_values():
    missing = _price_status(
        {"symbol": "BTCUSDC", "closeTime": NOW * 1000},
        platform="binance",
        expected_symbol="BTCUSDC",
        source_id="binance:/api/v3/ticker/24hr",
        received_at=NOW,
    )
    stale = _price_status(
        {"symbol": "BTCUSDC", "lastPrice": "61000", "closeTime": (NOW - 600) * 1000},
        platform="binance",
        expected_symbol="BTCUSDC",
        source_id="binance:/api/v3/ticker/24hr",
        received_at=NOW,
    )

    assert missing["truth_status"] == "no_data"
    assert "price" not in missing
    assert stale["truth_status"] == "no_data"
    assert stale["source_timestamp"] is None


class _Binance:
    def get_24h_ticker(self, symbol):
        return {"symbol": symbol, "lastPrice": "61000", "closeTime": NOW * 1000}


class _Kraken:
    def get_24h_ticker(self, symbol):
        return {"symbol": symbol, "lastPrice": "61010"}


class _Alpaca:
    def get_clock(self):
        return {"timestamp": "2033-05-18T03:33:20Z", "is_open": True}


class _Accounts(list):
    truth_status = "real_observed"
    source_timestamp = NOW


class _Capital:
    def get_accounts(self, *, cache_ttl):
        assert cache_ttl == 0.0
        return _Accounts([{"accountId": "provider-account"}])


def test_explicit_provider_probe_requires_receipts_and_never_uses_constructor_status():
    monitor = APIBufferMonitor(
        clients={
            "binance": _Binance(),
            "kraken": _Kraken(),
            "alpaca": _Alpaca(),
            "capital": _Capital(),
        },
        now_fn=lambda: NOW,
    )

    result = monitor.test_all_apis()

    assert result["binance"]["truth_status"] == "real_observed"
    assert result["binance"]["price"] == 61_000.0
    assert result["kraken"]["truth_status"] == "no_data"
    assert "price" not in result["kraken"]
    assert result["alpaca"]["market_open"] is True
    assert result["capital"]["truth_status"] == "real_observed"
    assert all(receipt["generated_values"] is False for receipt in result.values())


def test_unproven_file_returns_no_data_without_rendering(tmp_path):
    input_path = tmp_path / "legacy.json"
    input_path.write_text(
        json.dumps({"binance": {"BTCUSDC": [{"t": NOW, "p": 61_000.0}]}}),
        encoding="utf-8",
    )

    result = visualize_patterns(str(input_path), output_dir=str(tmp_path))

    assert result["truth_status"] == "no_data"
    assert result["reason"] == "no_fresh_proven_provider_snapshots"
    assert not (tmp_path / "market_pattern_analysis.png").exists()
    assert not (tmp_path / "market_pattern_analysis.svg").exists()


def test_module_imports_are_inert_and_provider_clients_are_lazy():
    source_path = Path(__file__).parents[1] / "aureon" / "analytics" / "visualize_market_patterns.py"
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert "_baton_link" not in source
    top_level_provider_imports = [
        node
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
        and str(node.module or "").startswith("aureon.exchanges")
    ]
    assert top_level_provider_imports == []
