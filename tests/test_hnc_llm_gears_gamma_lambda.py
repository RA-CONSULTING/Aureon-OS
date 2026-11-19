"""Gamma and Lambda(t) are different inputs to the HNC field gear.

``coherence_gamma`` is the field's [0, 1] score. ``lambda_t`` is the
field's own Lambda(t) when that value is already on the field. The gear
used to copy gamma into the slot named lambda. Gamma stays on the gamma
input. With no Lambda(t) on the field, the lambda slot is None.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.core import hnc_field, hnc_llm_gears
from aureon.vault.auris_metacognition import AurisMetacognition

_OMIT = object()


@pytest.fixture
def captured(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc_trace.jsonl"))
    seen: dict[str, object] = {}
    real_vote = AurisMetacognition.vote

    def spy(self, vault):
        seen["last_lambda_t"] = getattr(vault, "last_lambda_t", "MISSING")
        seen["coherence_gamma"] = getattr(vault, "coherence_gamma", "MISSING")
        result = real_vote(self, vault)
        seen["vote"] = result
        return result

    monkeypatch.setattr(AurisMetacognition, "vote", spy)
    return seen


def _field(monkeypatch, gamma, lambda_t=_OMIT):
    payload: dict[str, object] = {"available": True, "coherence_gamma": gamma}
    if lambda_t is not _OMIT:
        payload["lambda_t"] = lambda_t
    monkeypatch.setattr(
        hnc_field,
        "read_canonical_field",
        lambda bus=None: SimpleNamespace(**payload),
    )


def test_gamma_does_not_land_in_the_lambda_slot(monkeypatch, captured) -> None:
    _field(monkeypatch, 0.42)

    receipt = hnc_llm_gears.turn_gears("salad")

    assert captured["coherence_gamma"] == pytest.approx(0.42)
    assert captured["last_lambda_t"] is None
    field_gear = receipt["gears"][1]
    assert field_gear["coherence_gamma"] == pytest.approx(0.42)
    assert field_gear["coherence"] == pytest.approx(0.42)
    assert field_gear["lambda_t"] is None
    assert "error" not in receipt["gears"][2]


def test_lambda_slot_is_none_when_the_field_has_no_lambda(monkeypatch, captured) -> None:
    _field(monkeypatch, 0.42, None)

    receipt = hnc_llm_gears.turn_gears("salad")

    assert captured["last_lambda_t"] is None
    assert receipt["gears"][1]["lambda_t"] is None
    assert captured["coherence_gamma"] == pytest.approx(0.42)


def test_absent_gamma_does_not_fill_lambda_with_zero(monkeypatch, captured) -> None:
    _field(monkeypatch, None)

    receipt = hnc_llm_gears.turn_gears("salad")

    assert captured["last_lambda_t"] is None
    assert captured["coherence_gamma"] is None
    assert receipt["gears"][1]["lambda_t"] is None
    assert receipt["gears"][1]["coherence"] is None
    assert "error" not in receipt["gears"][2]


def test_published_lambda_stays_out_of_the_gamma_slot(monkeypatch, captured) -> None:
    _field(monkeypatch, 0.2, 1.5)

    receipt = hnc_llm_gears.turn_gears('{"claim_class": "C5"}')

    assert captured["coherence_gamma"] == pytest.approx(0.2)
    assert captured["last_lambda_t"] == pytest.approx(1.5)
    field_gear = receipt["gears"][1]
    assert field_gear["coherence_gamma"] == pytest.approx(0.2)
    assert field_gear["lambda_t"] == pytest.approx(1.5)
    assert field_gear["lambda_t"] != field_gear["coherence_gamma"]


def test_real_zero_gamma_stays_on_the_gamma_slot(monkeypatch, captured) -> None:
    _field(monkeypatch, 0.0)

    receipt = hnc_llm_gears.turn_gears("salad")

    assert captured["coherence_gamma"] == 0.0
    assert captured["coherence_gamma"] is not None
    assert captured["last_lambda_t"] is None
    assert receipt["gears"][1]["coherence_gamma"] == 0.0
    assert receipt["gears"][1]["lambda_t"] is None


def test_real_zero_lambda_is_not_dropped(monkeypatch, captured) -> None:
    _field(monkeypatch, 0.42, 0.0)

    receipt = hnc_llm_gears.turn_gears("salad")

    falcon = next(item for item in captured["vote"].per_node_votes if item.node == "Falcon")
    # A real 0.0 is the flat reading. If that 0.0 were turned into None,
    # Falcon would say "no Λ(t) reading" and this assertion would fail.
    assert "flat" in falcon.reasoning
    assert captured["last_lambda_t"] == 0.0
    assert captured["last_lambda_t"] is not None
    assert captured["coherence_gamma"] == pytest.approx(0.42)
    assert receipt["gears"][1]["lambda_t"] == 0.0


def test_held_gamma_does_not_clear_a_published_lambda(monkeypatch, captured) -> None:
    _field(monkeypatch, float("nan"), 1.5)

    receipt = hnc_llm_gears.turn_gears("salad")

    assert captured["coherence_gamma"] is None
    assert captured["last_lambda_t"] == pytest.approx(1.5)
    assert receipt["gears"][1]["coherence_verdict"] == "HOLD"
    assert receipt["gears"][1]["lambda_t"] == pytest.approx(1.5)


@pytest.mark.parametrize(
    "lambda_t",
    [float("nan"), float("inf"), True, "0.5"],
    ids=["nan", "inf", "bool", "string"],
)
def test_non_numeric_lambda_is_not_a_source(monkeypatch, captured, lambda_t) -> None:
    _field(monkeypatch, 0.42, lambda_t)

    receipt = hnc_llm_gears.turn_gears("salad")

    assert captured["last_lambda_t"] is None
    assert receipt["gears"][1]["lambda_t"] is None
    assert captured["coherence_gamma"] == pytest.approx(0.42)
