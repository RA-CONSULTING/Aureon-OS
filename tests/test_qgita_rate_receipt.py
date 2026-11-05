"""The QGITA rate receipt names the missing label and does not invent a rate."""

from __future__ import annotations

from aureon.evaluation.qgita_rate_receipt import MISSING_INGREDIENT, rates_hold_receipt
from aureon.evidence.qgita import FALSE_ALARM_TAIL


def test_a_long_unlabeled_series_is_a_measured_hold() -> None:
    receipt = rates_hold_receipt(
        samples=168,
        field_names=["close", "open", "high", "low", "volume", "open_time"],
        series_kind="public-market",
        paper_outcomes_are_not_signal_labels=True,
    )
    assert receipt["evidence_tag"] == "measured"
    assert receipt["verdict"] == "measured_rates_hold"
    assert receipt["rates_verdict"] == "HOLD"
    assert receipt["missing_ingredient"] == MISSING_INGREDIENT
    assert receipt["detection_rate"] is None
    assert receipt["false_alarm_rate"] is None
    assert receipt["detection_rate_ci95"] is None
    assert receipt["false_alarm_ci95"] is None
    assert receipt["threshold_fit"] is False
    assert receipt["calibration_tail"] == FALSE_ALARM_TAIL
    assert receipt["split_possible"] is True
    assert receipt["calibration_slots"] == 84
    assert receipt["held_out_slots"] == 84
    assert receipt["signal_present_trials"] == 0
    assert receipt["noise_only_trials"] == 0
    assert receipt["label_fields_found"] == []
    assert receipt["planted_rates_copied"] is False
    assert receipt["rates_count_as_market_rate"] is False
    assert receipt["release_boundary"] == "HOLD"
    assert receipt["orders_placed"] is False
    assert "synthetic_planted" in receipt["reason"]
    assert "paper" in receipt["reason"]
    assert "Wilson" in receipt["reason"]


def test_a_present_label_field_is_not_scored_as_a_planted_impulse() -> None:
    receipt = rates_hold_receipt(
        samples=40,
        field_names=["close", "signal_present"],
        series_kind="public-market",
    )
    assert receipt["detection_rate"] is None
    assert receipt["false_alarm_rate"] is None
    assert receipt["label_fields_found"] == ["signal_present"]
    assert receipt["missing_ingredient"] != MISSING_INGREDIENT
    assert "non-planted held-out scorer" in receipt["missing_ingredient"]
    assert "planted impulse" in receipt["missing_ingredient"]
    assert receipt["planted_rates_copied"] is False


def test_a_short_series_names_the_split_and_the_label() -> None:
    receipt = rates_hold_receipt(samples=1, field_names=[], series_kind="formula")
    assert receipt["split_possible"] is False
    assert receipt["calibration_slots"] == 0
    assert receipt["held_out_slots"] == 0
    assert receipt["detection_rate"] is None
    assert MISSING_INGREDIENT in receipt["missing_ingredient"]
    assert "at least two samples" in receipt["missing_ingredient"]


def test_derived_event_flags_are_counted_and_rejected() -> None:
    receipt = rates_hold_receipt(
        samples=10,
        field_names=["Lambda", "is_conjunction", "is_opposition", "L2_event"],
        series_kind="derived",
        rejected_event_columns={"is_opposition": 2, "is_conjunction": 4, "L2_event": 3},
    )
    assert receipt["missing_ingredient"] == MISSING_INGREDIENT
    assert receipt["rejected_event_columns"]["is_conjunction"] == 4
    assert "not a measured signal-in-noise label" in receipt["reason"]
    assert receipt["detection_rate"] is None
    assert receipt["false_alarm_rate"] is None
    assert receipt["planted_rates_copied"] is False
