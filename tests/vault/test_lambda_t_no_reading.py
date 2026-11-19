"""Missing Lambda(t) is not a flat 0.0. A real 0.0 stays 0.0.

These readers used ``float(getattr(..., 0.0) or 0.0)`` or
``state.get("last_lambda_t", 0.0) or 0.0``. After the gear split, a
missing or None ``last_lambda_t`` means there is no reading. Non-finite
values are not a reading either.
"""

from __future__ import annotations

import json
import math
from types import SimpleNamespace

import pytest

from aureon.harmonic.auris_voice_filter import AurisVoiceFilter as AureonVoiceFilter
from aureon.vault.hnc_deployer import HNCDeployer
from aureon.vault.voice.aureon_personas import QuantumPhysicistVoice
from aureon.vault.voice.choice_gate import ChoiceGate
from aureon.vault.voice.vault_voice import QueenVoice
from aureon_radar.harmonic.auris_voice_filter import (
    AurisVoiceFilter as RadarVoiceFilter,
)

_MISSING = object()

_NO_READING = (
    _MISSING,
    None,
    True,
    False,
    "flat",
    math.nan,
    math.inf,
    -math.inf,
)


class _Vote:
    consensus = "NEUTRAL"
    confidence = 0.2
    agreeing = 1
    total = 9
    lighthouse_cleared = False
    per_node_votes: list = []


class _Auris:
    def vote(self, _vault):
        return _Vote()


def _field_vault(lamb=_MISSING):
    vault = SimpleNamespace(
        love_amplitude=0.2,
        gratitude_score=0.4,
        cortex_snapshot={"gamma": 0.1},
    )
    if lamb is not _MISSING:
        vault.last_lambda_t = lamb
    return vault


def _filter_report(filter_cls, lamb=_MISSING):
    voice_filter = filter_cls(auris=_Auris(), threshold=0.0)
    return voice_filter.filter("Love holds the field.", _field_vault(lamb))


@pytest.mark.parametrize("filter_cls", (AureonVoiceFilter, RadarVoiceFilter))
@pytest.mark.parametrize("lamb", _NO_READING)
def test_voice_filter_missing_lambda_is_not_flat(filter_cls, lamb) -> None:
    report = _filter_report(filter_cls, lamb)
    assert report.field_lambda_t is None
    body = json.loads(json.dumps(report.to_dict()))
    assert body["field"]["lambda_t"] is None


@pytest.mark.parametrize("filter_cls", (AureonVoiceFilter, RadarVoiceFilter))
def test_voice_filter_real_zero_lambda_stays_zero(filter_cls) -> None:
    report = _filter_report(filter_cls, 0.0)
    assert report.field_lambda_t == 0.0
    assert report.field_lambda_t is not None
    body = json.loads(json.dumps(report.to_dict()))
    assert body["field"]["lambda_t"] == 0.0


def _deploy_vault(lamb=_MISSING, *, gamma=0.5, gratitude=0.8):
    vault = SimpleNamespace(
        cortex_snapshot={"gamma": gamma},
        gratitude_score=gratitude,
    )
    if lamb is not _MISSING:
        vault.last_lambda_t = lamb
    return vault


@pytest.mark.parametrize("lamb", _NO_READING)
def test_deployer_missing_lambda_skips_the_count(lamb) -> None:
    decision = HNCDeployer().should_deploy(_deploy_vault(lamb))
    assert decision.lambda_t is None
    assert decision.count == 0
    assert "no reading" in decision.reason
    assert "Λ=0.00" not in decision.reason


def test_deployer_real_zero_lambda_still_sizes_the_spike() -> None:
    decision = HNCDeployer().should_deploy(_deploy_vault(0.0))
    assert decision.lambda_t == 0.0
    assert decision.lambda_t is not None
    assert decision.count == 1
    assert "Λ=0.00" in decision.reason
    assert "no reading" not in decision.reason


def test_deployer_calm_text_names_a_real_zero_and_not_a_gap() -> None:
    zero = HNCDeployer().should_deploy(_deploy_vault(0.0, gamma=0.1))
    gap = HNCDeployer().should_deploy(_deploy_vault(gamma=0.1))
    assert zero.count == 0
    assert zero.lambda_t == 0.0
    assert "Λ=0.00" in zero.reason
    assert gap.lambda_t is None
    assert gap.count == 0
    assert "no reading" in gap.reason
    assert "Λ=0.00" not in gap.reason


def _gate_vault(lamb=_MISSING):
    vault = SimpleNamespace(
        love_amplitude=0.2,
        gratitude_score=0.5,
        last_casimir_force=0.05,
        rally_active=False,
        cortex_snapshot={
            "gamma": 0.05,
            "alpha": 0.0,
            "beta": 0.0,
            "theta": 0.0,
            "delta": 0.0,
        },
        dominant_chakra="love",
        pathway_graph={},
    )
    if lamb is not _MISSING:
        vault.last_lambda_t = lamb
    return vault


def _quiet_gate() -> ChoiceGate:
    return ChoiceGate(
        min_interval_s=0.0,
        urgency_threshold=0.99,
        background_rate=0.0,
        rng_seed=1,
    )


@pytest.mark.parametrize("lamb", _NO_READING)
def test_choice_gate_missing_lambda_is_not_a_factor(lamb) -> None:
    decision = _quiet_gate().decide(_gate_vault(lamb))
    assert "lambda_t" not in decision.factors
    assert "no reading" in decision.reasoning
    assert "Λ=0" not in decision.reasoning


def test_choice_gate_real_zero_lambda_is_a_reading() -> None:
    gap = _quiet_gate().decide(_gate_vault())
    zero = _quiet_gate().decide(_gate_vault(0.0))
    assert zero.urgency == gap.urgency
    assert "lambda_t" not in zero.factors
    assert "no reading" not in zero.reasoning
    loud = _quiet_gate().decide(_gate_vault(1.0))
    assert "lambda_t" in loud.factors
    assert "no reading" not in loud.reasoning


def _queen_text(lamb=_MISSING):
    vault = SimpleNamespace(
        love_amplitude=0.2,
        gratitude_score=0.5,
        last_casimir_force=0.0,
        dominant_chakra="love",
        dominant_frequency_hz=528.0,
        rally_active=False,
        cortex_snapshot={},
    )
    if lamb is not _MISSING:
        vault.last_lambda_t = lamb
    voice = QueenVoice()
    state = voice._extract_slice(vault)
    return state["last_lambda_t"], "\n".join(voice._compose_prompt_lines(state))


@pytest.mark.parametrize("lamb", _NO_READING)
def test_queen_missing_lambda_is_not_flat(lamb) -> None:
    stored, text = _queen_text(lamb)
    assert stored is None
    assert "no reading" in text
    assert "+0.000" not in text


def test_queen_real_zero_lambda_is_quoted() -> None:
    stored, text = _queen_text(0.0)
    assert stored == 0.0
    assert stored is not None
    assert "+0.000" in text
    assert "no reading" not in text


def _physicist_state(lamb=_MISSING, **overrides):
    state = {"consciousness_psi": 0.95, "coherence_gamma": 0.2}
    if lamb is not _MISSING:
        state["last_lambda_t"] = lamb
    state.update(overrides)
    return state


@pytest.mark.parametrize("lamb", _NO_READING)
def test_physicist_missing_lambda_is_not_flat(lamb) -> None:
    voice = QuantumPhysicistVoice()
    state = _physicist_state(lamb)
    text = " ".join(voice._compose_prompt_lines(state))
    assert "no reading" in text
    assert "+0.000" not in text
    action = voice.propose_action(state)
    assert action is not None
    assert action.payload["lambda_t"] is None
    assert "no reading" in action.reason
    assert voice.propose_goal(state) is None
    assert math.isfinite(voice.compute_affinity(state))


def test_physicist_real_zero_lambda_stays_zero() -> None:
    voice = QuantumPhysicistVoice()
    state = _physicist_state(0.0)
    text = " ".join(voice._compose_prompt_lines(state))
    assert "+0.000" in text
    assert "no reading" not in text
    action = voice.propose_action(state)
    assert action is not None
    assert action.payload["lambda_t"] == 0.0
    assert action.payload["lambda_t"] is not None
    assert "no reading" not in action.reason
    zero_score = voice.compute_affinity(state)
    gap_score = voice.compute_affinity(_physicist_state())
    one_score = voice.compute_affinity(_physicist_state(1.0))
    assert zero_score == gap_score
    assert one_score == zero_score + 1.5


def test_physicist_published_lambda_still_reaches_the_goal() -> None:
    voice = QuantumPhysicistVoice()
    goal = voice.propose_goal(_physicist_state(1.8))
    assert goal is not None
    assert "1.800" in goal
    assert "no reading" not in goal
