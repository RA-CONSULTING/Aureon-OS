"""Scoring helpers for the evidence harness.

These are comparison tools. They are not HNC, Auris, or QGITA formulas.
"""

from __future__ import annotations

import math


def auroc(positive: list[float], negative: list[float]) -> float | None:
    """Mann-Whitney AUROC. Ties count as one half. Higher scores rank as positive."""

    if not positive or not negative:
        return None
    wins = 0.0
    for left in positive:
        for right in negative:
            if left > right:
                wins += 1.0
            elif left == right:
                wins += 0.5
    return wins / (len(positive) * len(negative))


def rates(labels: list[bool], predictions: list[bool]) -> dict[str, float | int | None]:
    if len(labels) != len(predictions):
        raise ValueError("labels and predictions differ in length")
    true_positive = false_positive = true_negative = false_negative = 0
    for label, prediction in zip(labels, predictions, strict=True):
        if label and prediction:
            true_positive += 1
        elif label and not prediction:
            false_negative += 1
        elif prediction:
            false_positive += 1
        else:
            true_negative += 1

    def divide(numerator: int, denominator: int) -> float | None:
        if denominator == 0:
            return None
        return numerator / denominator

    return {
        "tp": true_positive,
        "fp": false_positive,
        "tn": true_negative,
        "fn": false_negative,
        "precision": divide(true_positive, true_positive + false_positive),
        "recall": divide(true_positive, true_positive + false_negative),
        "false_alarm_rate": divide(false_positive, false_positive + true_negative),
    }


def upper_threshold(scores: list[float], tail: float) -> float:
    """Threshold with about `tail` of the calibration scores strictly above it.

    The index is ceil((1 - tail) * n) - 1 on the sorted scores. A positive
    call is score > threshold, so ties at the threshold are not calls.
    """

    if not scores:
        raise ValueError("threshold needs scores")
    if not 0.0 < tail < 1.0:
        raise ValueError("tail must be between 0 and 1")
    ordered = sorted(float(score) for score in scores)
    index = math.ceil((1.0 - tail) * len(ordered)) - 1
    index = min(len(ordered) - 1, max(0, index))
    return ordered[index]


def fraction_above(scores: list[float], threshold: float) -> float:
    if not scores:
        raise ValueError("empty scores")
    return sum(1 for score in scores if score > threshold) / len(scores)
