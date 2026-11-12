"""The LOW COHERENCE status band in QueenHiveMind.get_auris_coherence is reachable.

The band is 0.40 <= coherence < 0.60. Below 0.40 is COHERENCE BREAK. The 0.40
floor is a design choice (see PR body), matching other 0.40 floors in the repo.
This changes only the status label; should_trade still needs coherence >= 0.60.
"""
from types import SimpleNamespace

import pytest

from aureon.utils import aureon_queen_hive_mind as qhm


def _status(monkeypatch, value):
    import aureon.core.hnc_field as hnc_field

    monkeypatch.setattr(hnc_field, "reconcile_gamma", lambda g: g)
    stub = SimpleNamespace(
        read_auris_nodes=lambda _md=None: {
            "a": {"value": value, "weight": 1.0, "weighted_value": value}
        }
    )
    return qhm.QueenHiveMind.get_auris_coherence(stub, {})


@pytest.mark.parametrize(
    "value, label",
    [
        (0.95, "HEART COHERENCE"),
        (0.85, "HIGH COHERENCE"),
        (0.65, "MODERATE COHERENCE"),
        (0.60, "MODERATE COHERENCE"),
        (0.50, "LOW COHERENCE"),
        (0.40, "LOW COHERENCE"),
        (0.39, "COHERENCE BREAK"),
        (0.10, "COHERENCE BREAK"),
    ],
)
def test_status_ladder(monkeypatch, value, label):
    coherence, status = _status(monkeypatch, value)
    assert coherence == pytest.approx(value)
    assert label in status
