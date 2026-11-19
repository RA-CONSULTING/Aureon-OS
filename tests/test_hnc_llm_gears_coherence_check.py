"""The HNC field gear sends coherence through the shared assess_coherence check.

``turn_gears()`` used to pass ``field.coherence_gamma`` straight to Auris as
``last_lambda_t`` with ``float()``. A NaN, an infinity, a bool or a value
outside [0, 1] became a Lambda reading. ``assess_coherence`` is the one check
the brain and the plumber use, and it holds those values.
"""

from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from aureon.core import hnc_field, hnc_llm_gears
from aureon.vault import auris_metacognition


@pytest.fixture
def captured(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc_trace.jsonl"))
    seen: dict[str, object] = {}
    real_vote = auris_metacognition.AurisMetacognition.vote

    def spy(self, vault):
        seen["last_lambda_t"] = vault.last_lambda_t
        return real_vote(self, vault)

    monkeypatch.setattr(auris_metacognition.AurisMetacognition, "vote", spy)
    return seen


def _field(monkeypatch, value):
    monkeypatch.setattr(
        hnc_field,
        "read_canonical_field",
        lambda bus=None: SimpleNamespace(available=True, coherence_gamma=value),
    )


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), 1.7, -0.2, True, "0.5"],
    ids=["nan", "inf", "above-one", "negative", "bool", "string"],
)
def test_out_of_range_coherence_is_held_not_voted(monkeypatch, captured, value) -> None:
    _field(monkeypatch, value)

    receipt = hnc_llm_gears.turn_gears("salad")

    assert not math.isnan(captured["last_lambda_t"])
    assert captured["last_lambda_t"] == 0.0
    field_gear = receipt["gears"][1]
    assert field_gear["coherence"] is None
    assert field_gear["coherence_verdict"] == "HOLD"


def test_accepted_coherence_reaches_auris(monkeypatch, captured) -> None:
    _field(monkeypatch, 0.42)

    receipt = hnc_llm_gears.turn_gears('{"claim_class": "C5"}')

    field_gear = receipt["gears"][1]
    assert field_gear["coherence"] == pytest.approx(0.42)
    assert field_gear["coherence_verdict"] == "ACCEPTED"
    assert captured["last_lambda_t"] == pytest.approx(0.42)


def test_no_field_reading_is_held(monkeypatch, captured) -> None:
    _field(monkeypatch, None)

    receipt = hnc_llm_gears.turn_gears("salad")

    assert captured["last_lambda_t"] == 0.0
    assert receipt["gears"][1]["coherence"] is None
