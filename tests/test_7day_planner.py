from __future__ import annotations

from datetime import datetime

import pytest

from aureon.autonomous.aureon_7day_planner import Aureon7DayPlanner


def _make_planner() -> Aureon7DayPlanner:
    planner = Aureon7DayPlanner.__new__(Aureon7DayPlanner)
    planner.matrix = {}
    planner.validation_history = []
    planner.adaptive_weights = {
        "hourly_weight": 1.0,
        "daily_weight": 1.0,
        "symbol_weight": 1.0,
        "validation_count": 0,
        "accuracy_7d": None,
        "accuracy_30d": None,
    }
    return planner


def test_missing_matrix_returns_numeric_free_no_data() -> None:
    recommendation = _make_planner().get_current_recommendation("BTC/USD")

    assert recommendation["action"] == "NO_DATA"
    assert recommendation["confidence"] is None
    assert recommendation["model_accuracy"] is None
    assert recommendation["truth_status"] == "no_data"
    assert recommendation["generated_values"] is False
    assert recommendation["reason"] == "MISSING_TRAINED_PROBABILITY_MATRIX"
    for numeric_field in (
        "hour",
        "day_of_week",
        "hourly_edge",
        "daily_edge",
        "symbol_edge",
        "total_edge",
    ):
        assert numeric_field not in recommendation


def test_complete_matrix_uses_canonical_equation_and_provenance() -> None:
    planner = _make_planner()
    now = datetime.now()
    planner.matrix = {
        "hourly_edge": {str(now.hour): {"edge": 2.0}},
        "daily_edge": {str(now.weekday()): {"edge": 1.0}},
        "symbol_patterns": {
            "BTC/USD": {"hourly_edge": {str(now.hour): {"edge": 1.0}}}
        },
        "_provenance": {
            "source_id": "observed-matrix.json",
            "source_timestamp": "2026-08-10T12:00:00+00:00",
        },
    }

    recommendation = planner.get_current_recommendation("BTC/USD")

    assert recommendation["hourly_edge"] == 2.0
    assert recommendation["daily_edge"] == 1.0
    assert recommendation["symbol_edge"] == 1.0
    assert recommendation["total_edge"] == (
        recommendation["hourly_edge"]
        + recommendation["daily_edge"] * 0.5
        + recommendation["symbol_edge"] * 0.5
    )
    assert recommendation["total_edge"] == 3.0
    assert recommendation["action"] == "BUY"
    assert recommendation["confidence"] == 0.75
    assert recommendation["truth_status"] == "real_derived"
    assert recommendation["source_id"] == "observed-matrix.json"
    assert recommendation["source_timestamp"] == "2026-08-10T12:00:00+00:00"
    assert recommendation["generated_values"] is False
    assert recommendation["model_accuracy"] is None


def test_empty_validation_history_is_numeric_free_no_data() -> None:
    stats = _make_planner().get_validation_stats()

    assert stats["total_validations"] == 0
    assert stats["accuracy"] is None
    assert stats["avg_error_pct"] is None
    assert stats["avg_timing_score"] is None
    assert stats["truth_status"] == "no_data"
    assert stats["generated_values"] is False
    assert stats["reason"] == "NO_VALIDATION_RECEIPTS"


def test_validation_stats_are_derived_from_complete_receipts() -> None:
    planner = _make_planner()
    planner.validation_history = [
        {
            "direction_correct": True,
            "actual_edge": 4.0,
            "predicted_edge": 3.0,
            "timing_score": 0.8,
        },
        {
            "direction_correct": False,
            "actual_edge": -1.0,
            "predicted_edge": 1.0,
            "timing_score": 0.4,
        },
    ]

    stats = planner.get_validation_stats()

    assert stats["total_validations"] == 2
    assert stats["correct_predictions"] == 1
    assert stats["accuracy"] == 0.5
    assert stats["avg_error_pct"] == 1.5
    assert stats["avg_timing_score"] == pytest.approx(0.6)
    assert stats["truth_status"] == "real_derived"
    assert stats["generated_values"] is False
    assert stats["reason"] is None
