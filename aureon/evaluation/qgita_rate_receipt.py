"""Measured HOLD receipt for QGITA detection and false-alarm rates.

Counts on a series are not a rate. A rate needs an exogenous signal-present
label and a noise-only label on a held-out trial. This module records the
census of a series and stops when that pair is absent. It does not plant an
impulse and it does not copy a synthetic_planted harness score.
"""

from __future__ import annotations

from typing import Any

from aureon.evidence.qgita import FALSE_ALARM_TAIL

RATES_HOLD_VERDICT = "measured_rates_hold"
MISSING_INGREDIENT = "exogenous signal-present versus noise-only labels on held-out trials"
_LABEL_FIELDS = ("signal_present", "noise_only", "signal_in_noise")
DERIVED_EVENT_COLUMNS = ("L2_event", "is_conjunction", "is_opposition")


def _missing_ingredient(samples: int, label_fields_found: list[str]) -> str:
    if label_fields_found:
        named = ", ".join(label_fields_found)
        return (
            "a non-planted held-out scorer for the label field "
            f"{named}; this receipt does not treat that field as a planted impulse"
        )
    if samples < 2:
        return (
            "at least two samples for a disjoint calibration half and held-out half, and "
            + MISSING_INGREDIENT
        )
    return MISSING_INGREDIENT


def rates_hold_receipt(
    *,
    samples: int,
    field_names: list[str],
    series_kind: str,
    rejected_event_columns: dict[str, int] | None = None,
    paper_outcomes_are_not_signal_labels: bool = False,
) -> dict[str, Any]:
    """Census one series and return a measured HOLD. Rates stay null."""

    names = sorted({str(name) for name in field_names})
    found = [name for name in _LABEL_FIELDS if name in names]
    rejected = {
        str(name): int(count)
        for name, count in sorted((rejected_event_columns or {}).items())
        if int(count) >= 0
    }
    split_possible = samples >= 2
    calibration_slots = samples // 2 if split_possible else 0
    held_out_slots = samples - calibration_slots if split_possible else 0
    missing = _missing_ingredient(samples, found)
    fields = ", ".join(names) if names else "none"
    found_text = ", ".join(found) if found else "none"
    sentences = [
        f"Measured HOLD. The missing ingredient is {missing}.",
        f"This {series_kind} series has {samples} samples.",
    ]
    if split_possible:
        sentences.append(
            f"A disjoint time split would put {calibration_slots} samples in calibration "
            f"and {held_out_slots} in the held-out half. The split was not scored."
        )
    else:
        sentences.append(
            "The series does not have two samples, so a calibration half and a held-out half were not formed."
        )
    sentences.append(f"Fields inspected: {fields}. Signal-present fields found: {found_text}.")
    if paper_outcomes_are_not_signal_labels:
        sentences.append(
            "The paper next-bar close-to-close returns on this pack are trade-outcome labels. "
            "They do not say signal-present versus noise-only, and they were not scored as a detection rate."
        )
    if rejected:
        described = ", ".join(f"{name} ({count} rows marked 1)" for name, count in rejected.items())
        sentences.append(
            f"Event columns on this file were counted and rejected as ground truth: {described}. "
            "A marked row is not a noise-only twin trial, and this file has no generator, "
            "so those flags are not a measured signal-in-noise label."
        )
    sentences.append(
        "The calibration path fits upper_threshold at tail "
        f"{FALSE_ALARM_TAIL} on noise-only scores and scores the held-out half with Wilson intervals. "
        "Noise-only trials: 0. Signal-present trials: 0. "
        "The threshold was not fit. Wilson intervals were not computed. "
        "Seeded shuffles and planted impulses are tagged synthetic_planted and are not written here. "
        "No order was sent. The release boundary stays HOLD."
    )
    reason = " ".join(sentences)
    return {
        "schema": "aureon.qgita.rates-hold.v1",
        "evidence_tag": "measured",
        "verdict": RATES_HOLD_VERDICT,
        "rates_verdict": "HOLD",
        "missing_ingredient": missing,
        "detection_rate": None,
        "detection_rate_ci95": None,
        "false_alarm_rate": None,
        "false_alarm_ci95": None,
        "interval": "Wilson 95% was not computed because the binomial totals are 0",
        "calibration_tail": FALSE_ALARM_TAIL,
        "threshold_fit": False,
        "samples": samples,
        "split_possible": split_possible,
        "calibration_slots": calibration_slots,
        "held_out_slots": held_out_slots,
        "split": (
            "first half by sample order would calibrate; the second half would be held out; "
            "the halves would be disjoint; the split was not scored"
        ),
        "signal_present_trials": 0,
        "noise_only_trials": 0,
        "field_names": names,
        "label_fields_looked_for": list(_LABEL_FIELDS),
        "label_fields_found": found,
        "rejected_event_columns": rejected,
        "planted_rates_copied": False,
        "rates_count_as_market_rate": False,
        "rates_count_as_telemetry": False,
        "orders_placed": False,
        "live_trading": False,
        "release_boundary": "HOLD",
        "reason": reason,
    }


def apply_rates_hold(record: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    """Write the receipt onto a QGITA series record. Counts already on the record stay."""

    record["detection_rate"] = None
    record["detection_rate_ci95"] = None
    record["false_alarm_rate"] = None
    record["false_alarm_ci95"] = None
    record["rates_verdict"] = "HOLD"
    record["rates_reason"] = receipt["reason"]
    record["rates_receipt"] = receipt
    record["verdict"] = RATES_HOLD_VERDICT
    return record
