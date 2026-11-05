"""Scoring helpers for the evidence harness.

These are comparison tools. They are not HNC, Auris, or QGITA formulas.
Wilson intervals are for binomial rates. Hanley-McNeil intervals are the
normal approximation for a Mann-Whitney AUROC. Neither is a detector.
"""

from __future__ import annotations

import math

_Z95 = 1.959963984540054


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


def wilson_interval(successes: int, total: int, z: float = _Z95) -> list[float] | None:
    """95% Wilson score interval for a binomial proportion."""

    if total <= 0:
        return None
    phat = successes / total
    z2 = z * z
    denom = 1.0 + z2 / total
    center = (phat + z2 / (2.0 * total)) / denom
    margin = z * math.sqrt((phat * (1.0 - phat) / total) + z2 / (4.0 * total * total)) / denom
    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    if low < 1e-12:
        low = 0.0
    if high > 1.0 - 1e-12:
        high = 1.0
    return [low, high]


def auroc_interval(auc: float | None, n_positive: int, n_negative: int, z: float = _Z95) -> list[float] | None:
    """Hanley-McNeil normal interval. It collapses when the AUROC is 0 or 1."""

    if auc is None or n_positive < 2 or n_negative < 2:
        return None
    if auc <= 0.0 or auc >= 1.0:
        return [auc, auc]
    q1 = auc / (2.0 - auc)
    q2 = 2.0 * auc * auc / (1.0 + auc)
    variance = (
        auc * (1.0 - auc)
        + (n_positive - 1) * (q1 - auc * auc)
        + (n_negative - 1) * (q2 - auc * auc)
    ) / (n_positive * n_negative)
    if variance < 0.0:
        variance = 0.0
    margin = z * math.sqrt(variance)
    return [max(0.0, auc - margin), min(1.0, auc + margin)]


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
        "precision_ci95": wilson_interval(true_positive, true_positive + false_positive),
        "recall_ci95": wilson_interval(true_positive, true_positive + false_negative),
        "false_alarm_ci95": wilson_interval(false_positive, false_positive + true_negative),
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
