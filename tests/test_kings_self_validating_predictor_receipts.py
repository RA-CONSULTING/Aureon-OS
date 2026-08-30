from __future__ import annotations

import dataclasses
import importlib.util
import math
import os
import sys
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
TARGET = (
    ROOT
    / "Kings_Accounting_Suite"
    / "aureon_systems"
    / "self_validating_predictor.py"
)
MODULE_NAME = "kings_self_validating_predictor_receipt_test"
LIVE_BEFORE_IMPORT = os.environ.get("LIVE")
SPEC = importlib.util.spec_from_file_location(MODULE_NAME, TARGET)
assert SPEC is not None and SPEC.loader is not None
predictor_module = importlib.util.module_from_spec(SPEC)
sys.modules[MODULE_NAME] = predictor_module
SPEC.loader.exec_module(predictor_module)


def _assert_numeric_free(value: Any) -> None:
    if dataclasses.is_dataclass(value):
        _assert_numeric_free(dataclasses.asdict(value))
    elif isinstance(value, Mapping):
        for item in value.values():
            _assert_numeric_free(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            _assert_numeric_free(item)
    else:
        assert isinstance(value, bool) or not isinstance(value, (int, float))


def _receipt(
    receipt_id: str,
    provider: str,
    receipt_type: str,
    source_timestamp: float,
    received_at: float,
    **values: Any,
) -> dict[str, Any]:
    return {
        "receipt_id": receipt_id,
        "provider": provider,
        "provider_receipt_type": receipt_type,
        "symbol": "BTCUSDC",
        "source_timestamp": source_timestamp,
        "received_at": received_at,
        "data_status": "complete",
        "truth_status": "real_observed",
        "generated_values": False,
        **values,
    }


def _authorized_inputs() -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    evidence = _receipt(
        "evidence-1",
        "binance",
        "market-evidence",
        970.0,
        970.5,
        evidence_complete=True,
        eligible_for_prediction=True,
        eligible_for_action=True,
    )
    prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    markets = [
        _receipt(
            f"market-{index}",
            "binance",
            "ticker",
            971.0 + index,
            971.5 + index,
            evidence_receipt_id=evidence["receipt_id"],
            eligible_for_prediction=True,
            eligible_for_action=True,
            price=price,
        )
        for index, price in enumerate(prices)
    ]
    hnc = _receipt(
        "hnc-1",
        "aureon-hnc",
        "hnc-authorization",
        977.0,
        977.5,
        truth_status="derived_from_real_observed",
        market_provider="binance",
        market_receipt_id=markets[-1]["receipt_id"],
        evidence_receipt_id=evidence["receipt_id"],
        eligible_for_prediction=True,
        eligible_for_action=True,
        approved=True,
    )
    auris = _receipt(
        "auris-1",
        "aureon-auris",
        "auris-authorization",
        978.0,
        978.5,
        truth_status="verified",
        market_provider="binance",
        market_receipt_id=markets[-1]["receipt_id"],
        evidence_receipt_id=evidence["receipt_id"],
        hnc_receipt_id=hnc["receipt_id"],
        eligible_for_prediction=True,
        eligible_for_action=True,
        approved=True,
    )
    return evidence, markets, hnc, auris


def _collect_authorized_baseline():
    evidence, markets, hnc, auris = _authorized_inputs()
    queued = list(markets)
    sleeps: list[float] = []

    def reader(platform: str, symbol: str) -> Mapping[str, Any]:
        assert platform == "binance"
        assert symbol == "BTCUSDC"
        return queued.pop(0)

    predictor = predictor_module.SelfValidatingPredictor(
        market_reader=reader,
        sleeper=sleeps.append,
    )
    baseline = predictor.collect_baseline(
        "binance",
        "BTCUSDC",
        3,
        evidence_receipt=evidence,
        observed_at=1000.0,
    )
    assert isinstance(baseline, predictor_module.BaselineObservation)
    assert not queued
    assert sleeps == [0.5] * 5
    return predictor, baseline, evidence, hnc, auris


def test_import_and_default_constructor_are_inert_and_fail_closed() -> None:
    assert os.environ.get("LIVE") == LIVE_BEFORE_IMPORT
    source = TARGET.read_text(encoding="utf-8")
    assert "get_binance_client" not in source
    assert "get_kraken_client" not in source
    assert "os.environ" not in source
    assert "datetime.now" not in source
    assert ".get('lastPrice', 0)" not in source
    assert '.get("lastPrice", 0)' not in source

    predictor = predictor_module.SelfValidatingPredictor()
    refusal = predictor.collect_baseline(
        "binance",
        "BTCUSDC",
        evidence_receipt=None,
        observed_at=1000.0,
    )

    assert not refusal
    assert refusal.reason == "market_reader_missing"
    _assert_numeric_free(refusal)
    assert predictor.predictions == []
    assert predictor.total_predictions == 0
    assert predictor.correct_predictions == 0
    assert predictor.running_accuracy is None


@pytest.mark.parametrize(
    "change",
    [
        ("hnc", None),
        ("hnc_source_timestamp", 900.0),
        ("auris_generated_values", True),
        ("market_symbol", "ETHUSDC"),
        ("auris_hnc_receipt_id", "wrong-hnc"),
    ],
)
def test_incomplete_stale_generated_or_unlinked_chains_do_not_emit_or_learn(
    change: tuple[str, Any],
) -> None:
    predictor, baseline, evidence, hnc, auris = _collect_authorized_baseline()
    hnc = dict(hnc)
    auris = dict(auris)
    receipts = [dict(receipt) for receipt in baseline.market_receipts]

    field, value = change
    if field == "hnc":
        hnc_value = value
    else:
        hnc_value = hnc
        if field == "hnc_source_timestamp":
            hnc["source_timestamp"] = value
        elif field == "auris_generated_values":
            auris["generated_values"] = value
        elif field == "market_symbol":
            receipts[-1]["symbol"] = value
        elif field == "auris_hnc_receipt_id":
            auris["hnc_receipt_id"] = value

    refusal = predictor.generate_prediction(
        "binance",
        "BTCUSDC",
        baseline.prices,
        baseline.momentum,
        baseline.frequency,
        market_receipts=receipts,
        evidence_receipt=evidence,
        hnc_receipt=hnc_value,
        auris_receipt=auris,
        observed_at=1000.0,
        horizon_seconds=4.0,
    )

    assert not refusal
    _assert_numeric_free(refusal)
    assert predictor.predictions == []
    assert predictor.total_predictions == 0
    assert predictor.accuracy_window == predictor_module.deque(maxlen=20)


def test_accepted_equations_are_unchanged_and_only_linked_outcome_learns() -> None:
    predictor, baseline, evidence, hnc, auris = _collect_authorized_baseline()
    prediction = predictor.generate_prediction(
        "binance",
        "BTCUSDC",
        baseline.prices,
        baseline.momentum,
        baseline.frequency,
        market_receipts=baseline.market_receipts,
        evidence_receipt=evidence,
        hnc_receipt=hnc,
        auris_receipt=auris,
        observed_at=1000.0,
        horizon_seconds=4.0,
    )
    assert isinstance(prediction, predictor_module.Prediction)

    recent = baseline.prices[-5:]
    price_trend = np.polyfit(range(len(recent)), recent, 1)[0]
    momentum_strength = abs(baseline.momentum) * 10
    if abs(baseline.frequency - predictor_module.FREQ_MAP["LOVE"]) < 30:
        freq_boost = 0.02
    elif abs(baseline.frequency - predictor_module.FREQ_MAP["NATURAL"]) < 15:
        freq_boost = 0.01
    elif abs(baseline.frequency - predictor_module.FREQ_MAP["DISTORTION"]) < 10:
        freq_boost = -0.02
    else:
        freq_boost = 0
    expected_change = (
        baseline.momentum * 0.5
        + (price_trend / baseline.prices[-1]) * 100 * 30 * 0.3
        + freq_boost
    )
    expected_change = max(-0.5, min(0.5, expected_change))
    expected_consistency = 1.0 - min(
        1.0, np.std(recent) / np.mean(recent) * 100
    )
    expected_confidence = min(
        0.9, expected_consistency * 0.5 + momentum_strength * 0.3 + 0.2
    )

    assert prediction.predicted_change_pct == pytest.approx(expected_change)
    assert prediction.predicted_price == pytest.approx(
        baseline.prices[-1] * (1 + expected_change / 100)
    )
    assert prediction.confidence == pytest.approx(expected_confidence)
    assert prediction.timestamp == auris["source_timestamp"]
    assert prediction.source_timestamp == auris["source_timestamp"]
    assert prediction.market_receipt_id == baseline.market_receipts[-1]["receipt_id"]
    assert prediction.evidence_receipt_id == evidence["receipt_id"]
    assert prediction.hnc_receipt_id == hnc["receipt_id"]
    assert prediction.auris_receipt_id == auris["receipt_id"]
    assert prediction.eligible_for_action is True
    assert prediction.eligible_for_learning is False
    assert predictor.predictions == []

    bad_outcome = _receipt(
        "outcome-bad",
        "binance",
        "prediction-outcome",
        982.0,
        982.5,
        prediction_receipt_id="wrong-prediction",
        evidence_receipt_id=evidence["receipt_id"],
        eligible_for_learning=True,
        price=106.0,
    )
    refusal = predictor.validate_prediction(
        prediction,
        outcome_receipt=bad_outcome,
        observed_at=1005.0,
    )
    assert not refusal
    _assert_numeric_free(refusal)
    assert prediction.actual_price is None
    assert prediction.actual_change_pct is None
    assert prediction.validated is False
    assert predictor.predictions == []
    assert predictor.total_predictions == 0

    outcome = dict(bad_outcome)
    outcome["receipt_id"] = "outcome-good"
    outcome["prediction_receipt_id"] = prediction.receipt_id
    validated = predictor.validate_prediction(
        prediction,
        outcome_receipt=outcome,
        observed_at=1005.0,
    )
    assert validated is prediction
    expected_actual_change = (
        (106.0 - prediction.baseline_price) / prediction.baseline_price
    ) * 100
    expected_error = abs(expected_actual_change - prediction.predicted_change_pct)
    expected_magnitude = max(
        0,
        1 - (expected_error / abs(prediction.predicted_change_pct)),
    )
    assert prediction.actual_price == 106.0
    assert prediction.actual_change_pct == pytest.approx(expected_actual_change)
    assert prediction.actual_direction == "UP"
    assert prediction.direction_correct is (
        prediction.predicted_direction == "UP"
    )
    assert prediction.magnitude_accuracy == pytest.approx(expected_magnitude)
    assert prediction.eligible_for_learning is True
    assert prediction.validated is True
    assert predictor.predictions == [prediction]
    assert predictor.total_predictions == 1
    assert predictor.correct_predictions == int(prediction.direction_correct)

    duplicate = predictor.validate_prediction(
        prediction,
        outcome_receipt=outcome,
        observed_at=1005.0,
    )
    assert not duplicate
    assert duplicate.reason == "prediction_already_validated"
    assert predictor.predictions == [prediction]
    assert predictor.total_predictions == 1


def test_outcome_must_be_fresh_real_and_explicitly_learning_eligible() -> None:
    predictor, baseline, evidence, hnc, auris = _collect_authorized_baseline()
    prediction = predictor.generate_prediction(
        "binance",
        "BTCUSDC",
        baseline.prices,
        baseline.momentum,
        baseline.frequency,
        market_receipts=baseline.market_receipts,
        evidence_receipt=evidence,
        hnc_receipt=hnc,
        auris_receipt=auris,
        observed_at=1000.0,
        horizon_seconds=4.0,
    )
    assert isinstance(prediction, predictor_module.Prediction)

    outcome = _receipt(
        "outcome-ineligible",
        "binance",
        "prediction-outcome",
        982.0,
        982.5,
        prediction_receipt_id=prediction.receipt_id,
        evidence_receipt_id=evidence["receipt_id"],
        eligible_for_learning=False,
        price=106.0,
    )
    refusal = predictor.validate_prediction(
        prediction,
        outcome_receipt=outcome,
        observed_at=1005.0,
    )
    assert not refusal
    assert refusal.reason == "receipt_not_learning_eligible"
    assert prediction.validated is False
    assert predictor.predictions == []
