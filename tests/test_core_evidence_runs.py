"""The evidence bundle matches a fresh in-memory rebuild, except commit_sha."""

from __future__ import annotations

from aureon.evidence.metrics import auroc, fraction_above, rates, upper_threshold
from aureon.evidence.runner import main


def test_auroc_ties_and_order() -> None:
    assert auroc([1.0], [1.0]) == 0.5
    assert auroc([1.0, 2.0], [0.0, 0.0]) == 1.0
    assert auroc([0.0], [1.0, 2.0]) == 0.0
    assert auroc([], [1.0]) is None


def test_threshold_tail_and_rates() -> None:
    scores = [float(index) for index in range(1, 21)]
    threshold = upper_threshold(scores, 0.05)
    assert fraction_above(scores, threshold) <= 0.05
    counted = rates([True, True, False, False], [True, False, True, False])
    assert counted["tp"] == 1
    assert counted["fn"] == 1
    assert counted["fp"] == 1
    assert counted["tn"] == 1
    assert counted["precision"] == 0.5
    assert counted["recall"] == 0.5
    assert counted["false_alarm_rate"] == 0.5


def test_evidence_bundle_matches_committed_bytes() -> None:
    assert main(["--check"]) == 0
