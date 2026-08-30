import copy
import inspect
import json
from dataclasses import asdict

from aureon.strategies import probability_data_collector as collector_module
from aureon.strategies.probability_data_collector import (
    BINANCE_TICKER_SOURCE_ID,
    ProbabilityCollector,
)


NOW = 1_800_000_000.0


class InMemoryBinance:
    def __init__(self, receipts):
        self.receipts = receipts
        self.calls = []

    def get_24h_ticker(self, symbol):
        self.calls.append(symbol)
        return copy.deepcopy(self.receipts[symbol])


def _complete_24h_receipt(symbol="BTCUSDT", close_epoch=NOW - 1.0):
    return {
        "symbol": symbol,
        "priceChange": "10",
        "priceChangePercent": "10",
        "weightedAvgPrice": "105",
        "prevClosePrice": "100",
        "lastPrice": "110",
        "lastQty": "0.5",
        "bidPrice": "109.9",
        "bidQty": "2",
        "askPrice": "110.1",
        "askQty": "3",
        "openPrice": "100",
        "highPrice": "112",
        "lowPrice": "99",
        "volume": "1000",
        "quoteVolume": "105000",
        "openTime": int((close_epoch - 86_400.0) * 1000),
        "closeTime": int(close_epoch * 1000),
        "firstId": 1,
        "lastId": 10,
        "count": 10,
    }


def _market_row(base, *, symbol, source_timestamp, price, open_price):
    row = dict(base)
    row.update(
        {
            "timestamp": ProbabilityCollector._iso_timestamp(source_timestamp),
            "symbol": symbol,
            "price": price,
            "change_pct": ((price - open_price) / open_price) * 100.0,
            "open_price": open_price,
            "high_price": max(price, open_price) + 2.0,
            "low_price": min(price, open_price) - 2.0,
            "bid": price - 0.1,
            "ask": price + 0.1,
            "source_timestamp": source_timestamp,
            "provider_close_time_raw": int(source_timestamp * 1000),
            "received_at": ProbabilityCollector._iso_timestamp(source_timestamp + 1.0),
            "probability_score": None,
            "probability_status": "no_data",
            "probability_truth_status": "no_data",
            "probability_source_id": None,
            "probability_source_timestamp": None,
            "probability_received_at": None,
            "probability_generated_values": False,
            "eligible_for_prediction": False,
            "eligible_for_learning": False,
        }
    )
    return row


def test_collector_requires_provider_provenance_and_proof_gates_learning(tmp_path):
    source = inspect.getsource(collector_module)
    assert "_baton_link" not in source
    assert "BinanceClient.get_ticker =" not in source
    assert "random.random" not in source

    learning_reports = []
    ledger = tmp_path / "probability-observations.jsonl"
    client = InMemoryBinance({"BTCUSDT": _complete_24h_receipt()})
    collector = ProbabilityCollector(
        client,
        output_file=str(ledger),
        symbols=["BTCUSDT"],
        clock=lambda: NOW,
        learning_sink=learning_reports.append,
    )

    collected = collector.collect_snapshot()
    assert client.calls == ["BTCUSDT"]
    assert len(collected) == 1
    observation = collected[0]
    assert observation.source_id == BINANCE_TICKER_SOURCE_ID
    assert observation.source_timestamp == NOW - 1.0
    assert observation.provider_close_time_raw == int((NOW - 1.0) * 1000)
    assert observation.timestamp != observation.received_at
    assert observation.data_status == "live"
    assert observation.truth_status == "real_observed"
    assert observation.generated_values is False
    assert observation.probability_score is None
    assert observation.probability_status == "no_data"
    assert observation.eligible_for_prediction is False
    assert observation.eligible_for_learning is False

    collector.save_data()
    no_prediction_report = collector.validate_predictions()
    assert no_prediction_report["data_status"] == "no_data"
    assert no_prediction_report["eligible_for_learning"] is False
    assert learning_reports == []

    invalid_receipts = []
    missing_field = _complete_24h_receipt()
    missing_field["quoteVolume"] = None
    invalid_receipts.append(missing_field)
    wrong_symbol = _complete_24h_receipt(symbol="ETHUSDT")
    invalid_receipts.append(wrong_symbol)
    stale = _complete_24h_receipt(close_epoch=NOW - 121.0)
    invalid_receipts.append(stale)
    timestamp_laundered = _complete_24h_receipt(close_epoch=NOW)
    invalid_receipts.append(timestamp_laundered)
    nonfinite = _complete_24h_receipt()
    nonfinite["lastPrice"] = "nan"
    invalid_receipts.append(nonfinite)
    generated = _complete_24h_receipt()
    generated["generated_values"] = True
    invalid_receipts.append(generated)

    for receipt in invalid_receipts:
        invalid_collector = ProbabilityCollector(
            InMemoryBinance({"BTCUSDT": receipt}),
            output_file=str(tmp_path / "unused.jsonl"),
            symbols=["BTCUSDT"],
            clock=lambda: NOW,
        )
        assert invalid_collector.collect_snapshot() == []
        assert invalid_collector.data_buffer == []
        assert invalid_collector.last_collection_receipt["data_status"] == "no_data"
        assert invalid_collector.last_collection_receipt["source_timestamp"] is None
        assert invalid_collector.last_collection_receipt["eligible_for_prediction"] is False
        assert invalid_collector.last_collection_receipt["eligible_for_learning"] is False

    base = asdict(observation)
    prediction_timestamp = observation.source_timestamp
    proven_prediction = _market_row(
        base,
        symbol="BTCUSDT",
        source_timestamp=prediction_timestamp,
        price=110.0,
        open_price=100.0,
    )
    proven_prediction.update(
        {
            "probability_score": 0.8,
            "probability_status": "live",
            "probability_truth_status": "real_derived",
            "probability_source_id": "hnc:probability-matrix:receipt-123",
            "probability_source_timestamp": prediction_timestamp,
            "probability_received_at": ProbabilityCollector._iso_timestamp(
                prediction_timestamp + 0.5
            ),
            "probability_generated_values": False,
            "eligible_for_prediction": True,
            "eligible_for_learning": True,
        }
    )
    interleaved_other_symbol = _market_row(
        base,
        symbol="ETHUSDT",
        source_timestamp=prediction_timestamp + 300.0,
        price=50.0,
        open_price=50.0,
    )
    same_symbol_outcome = _market_row(
        base,
        symbol="BTCUSDT",
        source_timestamp=prediction_timestamp + 300.0,
        price=112.0,
        open_price=100.0,
    )
    ledger.write_text(
        "\n".join(
            json.dumps(row)
            for row in (
                proven_prediction,
                interleaved_other_symbol,
                same_symbol_outcome,
            )
        )
        + "\n",
        encoding="utf-8",
    )

    report = collector.validate_predictions()
    assert report["data_status"] == "live"
    assert report["truth_status"] == "real_derived"
    assert report["total_predictions"] == 1
    assert report["correct_predictions"] == 1
    assert report["eligible_for_learning"] is True
    assert report["validated_rows"] == [
        {
            "symbol": "BTCUSDT",
            "prediction_source_timestamp": prediction_timestamp,
            "outcome_source_timestamp": prediction_timestamp + 300.0,
            "actual_horizon_seconds": 300.0,
            "prediction": "UP",
            "outcome": "UP",
            "correct": True,
            "generated_values": False,
        }
    ]
    assert learning_reports == [report]
