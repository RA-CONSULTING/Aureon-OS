"""The cognitive planner must not invent or reuse Λ(t)."""

from __future__ import annotations

from aureon.queen.queen_cognitive_action_planner import (
    QueenCognitiveActionPlanner,
    lambda_phase_for,
    published_lambda,
)


def _planner() -> QueenCognitiveActionPlanner:
    return QueenCognitiveActionPlanner()


def test_planner_lambda_starts_unread():
    planner = _planner()
    assert planner._last_lambda_t is None
    assert planner._last_lambda_phase == "no reading"


def test_missing_lambda_does_not_carry_the_previous_reading():
    planner = _planner()
    planner._on_source_law("ics.source_law.cognition", {"lambda_t": 1.25, "coherence_gamma": 0.4})
    assert planner._last_lambda_t == 1.25
    planner._on_source_law("ics.source_law.cognition", {"coherence_gamma": 0.9})
    assert planner._last_lambda_t is None
    assert planner._last_lambda_phase == "no reading"
    assert published_lambda({"coherence_gamma": 0.9}) is None


def test_real_zero_lambda_survives():
    planner = _planner()
    planner._on_source_law("ics.source_law.cognition", {"lambda_t": 0.0})
    assert planner._last_lambda_t == 0.0
    assert planner._last_lambda_t is not None
    assert planner._last_lambda_phase == "TRANSITION"
    assert lambda_phase_for(0.0) == "TRANSITION"
    assert lambda_phase_for(None) == "no reading"


def test_non_reading_lambda_does_not_drive_a_phase():
    planner = _planner()
    planner._on_source_law("ics.source_law.cognition", {"lambda_t": True})
    assert planner._last_lambda_t is None
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
