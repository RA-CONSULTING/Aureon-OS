"""The cognitive planner takes Λ(t) from the canonical HNC field, or none."""

from __future__ import annotations

import time
from types import SimpleNamespace

from aureon.queen.queen_cognitive_action_planner import (
    QueenCognitiveActionPlanner,
    lambda_phase_for,
    published_lambda,
)


def _planner() -> QueenCognitiveActionPlanner:
    return QueenCognitiveActionPlanner()


def _field(**overrides):
    values = {
        "available": True,
        "freshness_status": "fresh",
        "lambda_t": 1.25,
        "coherence_gamma": 0.4,
        "source_timestamp": time.time(),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_planner_lambda_and_coherence_start_unread():
    planner = _planner()
    assert planner._last_lambda_t is None
    assert planner._last_lambda_ts is None
    assert planner._last_lambda_phase == "no reading"
    assert planner._last_coherence is None
    assert planner._last_coherence_ts is None
    assert planner._last_urgency is None


def test_source_law_reads_the_canonical_field(monkeypatch):
    monkeypatch.setattr(
        "aureon.core.hnc_field.read_canonical_field",
        lambda bus=None: _field(lambda_t=0.0, coherence_gamma=0.0),
    )
    planner = _planner()
    planner._on_source_law("ics.source_law.cognition", {"action": "HOLD"})
    assert planner._last_lambda_t == 0.0
    assert planner._last_lambda_t is not None
    assert planner._last_coherence == 0.0
    assert planner._last_lambda_phase == "TRANSITION"


def test_missing_field_does_not_carry_the_previous_reading():
    planner = _planner()
    planner._adopt_canonical_field(_field(lambda_t=1.25, coherence_gamma=0.4))
    assert planner._last_lambda_t == 1.25
    planner._adopt_canonical_field(
        _field(available=False, freshness_status=None, lambda_t=None, source_timestamp=None)
    )
    assert planner._last_lambda_t is None
    assert planner._last_coherence is None
    assert planner._last_lambda_phase == "no reading"
    assert published_lambda({"coherence_gamma": 0.9}) is None


def test_stale_field_is_no_reading():
    planner = _planner()
    planner._adopt_canonical_field(_field(source_timestamp=time.time() - 301))
    assert planner._last_lambda_t is None
    assert planner._last_coherence is None


def test_stored_reading_expires():
    planner = _planner()
    planner._last_lambda_t = 1.0
    planner._last_lambda_ts = time.time() - 10_000
    planner._last_coherence = 0.2
    planner._last_coherence_ts = time.time() - 10_000
    planner._expire_hnc()
    assert planner._last_lambda_t is None
    assert planner._last_coherence is None
    assert planner._last_lambda_phase == "no reading"


def test_real_zero_lambda_survives():
    planner = _planner()
    planner._adopt_canonical_field(_field(lambda_t=0.0, coherence_gamma=0.0))
    assert planner._last_lambda_t == 0.0
    assert planner._last_coherence == 0.0
    assert planner._last_lambda_phase == "TRANSITION"
    assert lambda_phase_for(0.0) == "TRANSITION"
    assert lambda_phase_for(None) == "no reading"


def test_non_reading_lambda_does_not_drive_a_phase():
    planner = _planner()
    planner._adopt_canonical_field(_field(lambda_t=True, coherence_gamma=True))
    assert planner._last_lambda_t is None
    assert planner._last_coherence is None
    assert planner._last_lambda_phase == "no reading"
    text = planner._ask_ollama(
        ollama=None,
        dialogues=[],
        insights=[],
        mood="UNKNOWN",
        urgency=0.0,
        coherence=0.0,
        consciousness="DORMANT",
        lambda_phase="no reading",
        lambda_t=None,
    )
    assert text == ""


def test_metacognition_does_not_reuse_coherence():
    planner = _planner()
    planner._last_coherence = 0.8
    planner._last_coherence_ts = time.time()
    planner._last_urgency = 0.7
    planner._on_metacognition(
        "queen.metacognition.internal_dialogue",
        {"text": "hello"},
    )
    assert planner._last_coherence is None
    assert planner._last_urgency is None
    planner._on_metacognition(
        "queen.metacognition.internal_dialogue",
        {"text": "hello", "coherence": 0.0, "urgency": 0.0},
    )
    assert planner._last_coherence == 0.0
    assert planner._last_urgency == 0.0
    planner._on_metacognition(
        "queen.metacognition.internal_dialogue",
        {"text": "hello", "coherence": True, "urgency": float("nan")},
    )
    assert planner._last_coherence is None
    assert planner._last_urgency is None


def test_none_lambda_skips_the_proposal(monkeypatch):
    calls = []

    class Mind:
        def submit_action_proposal(self, **kwargs):
            calls.append(kwargs)
            return {"receipt_id": "r1"}

    monkeypatch.setattr(
        "aureon.queen.queen_mind.get_canonical_queen_mind",
        lambda: Mind(),
    )
    planner = _planner()
    planner._dialogues.append("a thought")
    planner._last_lambda_t = None
    planner._last_coherence = 0.4
    planner._last_coherence_ts = time.time()
    planner._synthesise_and_submit()
    assert calls == []


def test_real_zero_lambda_still_submits(monkeypatch):
    calls = []

    class Mind:
        def submit_action_proposal(self, **kwargs):
            calls.append(kwargs)
            return {"receipt_id": "r1"}

    monkeypatch.setattr(
        "aureon.queen.queen_mind.get_canonical_queen_mind",
        lambda: Mind(),
    )
    planner = _planner()
    planner._dialogues.append("a thought")
    now = time.time()
    planner._last_lambda_t = 0.0
    planner._last_lambda_ts = now
    planner._last_coherence = 0.0
    planner._last_coherence_ts = now
    planner._synthesise_and_submit()
    assert len(calls) == 1
    assert calls[0]["proposal"]["lambda_t"] != "no reading"
    assert "0.0" in calls[0]["proposal"]["lambda_t"]
