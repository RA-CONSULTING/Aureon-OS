"""A held field reading is not a Lambda zero.

``assess_coherence`` already refuses NaN, inf, bools, and values outside
[0, 1]. The gear used to hand Auris ``last_lambda_t = 0.0`` for every
refusal, the same input as an accepted 0.0. A refusal is no reading:
``None`` reaches Auris. An accepted gamma of 0.0 stays on the gamma
input and does not fill the lambda slot when the field has no ``lambda_t``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.core import hnc_field, hnc_llm_gears
from aureon.vault.auris_metacognition import AurisMetacognition


@pytest.fixture
def captured(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc_trace.jsonl"))
    seen: dict[str, object] = {}
    real_vote = AurisMetacognition.vote

    def spy(self, vault):
        seen["last_lambda_t"] = vault.last_lambda_t
        result = real_vote(self, vault)
        seen["vote"] = result
        seen["falcon"] = next(item for item in result.per_node_votes if item.node == "Falcon")
        return result

    monkeypatch.setattr(AurisMetacognition, "vote", spy)
    return seen


def _field(monkeypatch, value):
    monkeypatch.setattr(
        hnc_field,
        "read_canonical_field",
        lambda bus=None: SimpleNamespace(available=True, coherence_gamma=value),
    )


def test_rejected_reading_reaches_auris_as_none(monkeypatch, captured) -> None:
    _field(monkeypatch, float("nan"))

    receipt = hnc_llm_gears.turn_gears("salad")

    assert captured["last_lambda_t"] is None
    auris = receipt["gears"][2]
    assert auris["turned"] is True
    assert "error" not in auris
    assert auris["total"] == 9
    assert captured["falcon"].reasoning != "Λ(t)=0.000 — flat"


def test_absent_reading_reaches_auris_as_none(monkeypatch, captured) -> None:
    _field(monkeypatch, None)

    receipt = hnc_llm_gears.turn_gears("salad")

    assert captured["last_lambda_t"] is None
    assert "error" not in receipt["gears"][2]
    assert captured["falcon"].reasoning != "Λ(t)=0.000 — flat"


def test_real_zero_reading_stays_zero(monkeypatch, captured) -> None:
    _field(monkeypatch, 0.0)

    receipt = hnc_llm_gears.turn_gears("salad")

    field_gear = receipt["gears"][1]
    assert field_gear["coherence"] == 0.0
    assert field_gear["coherence_verdict"] == "ACCEPTED"
    assert captured["last_lambda_t"] is None
    assert field_gear.get("lambda_t") is None


def test_vault_without_last_lambda_t_defaults_to_zero() -> None:
    auris = AurisMetacognition()
    vault = SimpleNamespace()
    assert not hasattr(vault, "last_lambda_t")

    falcon = auris._falcon(vault)
    explicit_zero = auris._falcon(SimpleNamespace(last_lambda_t=0.0))

    assert falcon.verdict == "NEUTRAL"
    assert falcon.reasoning == "Λ(t)=0.000 — flat"
    assert falcon.reasoning == explicit_zero.reasoning

    vote = auris.vote(vault)
    node = next(item for item in vote.per_node_votes if item.node == "Falcon")
    assert node.verdict == falcon.verdict
    assert node.reasoning == falcon.reasoning


def test_falcon_does_not_crash_or_read_none_as_zero() -> None:
    auris = AurisMetacognition()
    missing = auris._falcon(SimpleNamespace(last_lambda_t=None))
    zero = auris._falcon(SimpleNamespace(last_lambda_t=0.0))

    assert missing.verdict == "NEUTRAL"
    assert "0.000" not in missing.reasoning
    assert "flat" not in missing.reasoning
    assert missing.reasoning != zero.reasoning
    assert "flat" in zero.reasoning

    vote = auris.vote(SimpleNamespace(last_lambda_t=None))
    assert vote.total == 9
    falcon = next(item for item in vote.per_node_votes if item.node == "Falcon")
    assert falcon.reasoning == missing.reasoning
