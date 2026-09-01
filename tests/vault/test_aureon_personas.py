#!/usr/bin/env python3
"""
Tests for the ten Aureon resonant personas.

  - compute_affinity returns finite, non-negative floats
  - each persona dominates under the state configuration it's tuned for
  - _compose_prompt_lines yields at least one line and never invents
    numbers that aren't in the state
  - VOICE_REGISTRY contains all ten new personas after module import
"""

from __future__ import annotations

import math
import os
import re
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.vault.voice.aureon_personas import (  # noqa: E402
    AUREON_PERSONA_REGISTRY,
    ArtistVoice,
    ChildVoice,
    ElderVoice,
    EngineerVoice,
    LeftVoice,
    MysticVoice,
    PainterVoice,
    PhilosopherVoice,
    QuantumPhysicistVoice,
    ResonantPersona,
    RightVoice,
    build_aureon_personas,
)
from aureon.vault.voice.vault_voice import VOICE_REGISTRY  # noqa: E402


class _StubAdapter:
    """Record-only adapter — returns a short canned response so speak() works."""

    def __init__(self):
        self.calls = []

    def prompt(self, messages, system, max_tokens):
        self.calls.append({"messages": messages, "system": system, "max_tokens": max_tokens})

        class _R:
            text = "stub response"
            model = "stub"
            usage = {"total_tokens": 3}

        return _R()


def _base_state(**overrides):
    state = {
        "love_amplitude": 0.5,
        "gratitude_score": 0.5,
        "last_casimir_force": 0.0,
        "last_lambda_t": 0.0,
        "dominant_chakra": "solar",
        "dominant_frequency_hz": 300.0,
        "rally_active": False,
        "vault_size": 50,
        "cortex": {"delta": 0.1, "theta": 0.1, "alpha": 0.1, "beta": 0.1, "gamma": 0.1},
        "consciousness_psi": 0.2,
        "coherence_gamma": 0.2,
        "consciousness_level": "DORMANT",
        "confidence": 0.2,
        "node_readings": {},
        "dj_drop": {},
    }
    state.update(overrides)
    return state


def test_registry_has_ten_personas():
    assert len(AUREON_PERSONA_REGISTRY) == 10
    expected = {
        "painter", "artist", "quantum_physicist", "philosopher", "child",
        "elder", "mystic", "engineer", "left", "right",
    }
    assert set(AUREON_PERSONA_REGISTRY.keys()) == expected


def test_voice_registry_merges_new_personas():
    for name in AUREON_PERSONA_REGISTRY:
        assert name in VOICE_REGISTRY, f"{name} missing from VOICE_REGISTRY"
    assert "queen" in VOICE_REGISTRY  # old personas preserved
    assert "lover" in VOICE_REGISTRY


def test_compute_affinity_is_finite_and_nonnegative():
    state = _base_state()
    personas = build_aureon_personas(adapter=_StubAdapter())
    for name, persona in personas.items():
        assert isinstance(persona, ResonantPersona)
        score = persona.compute_affinity(state)
        assert isinstance(score, float)
        assert math.isfinite(score), f"{name} returned non-finite affinity"
        assert score >= 0.0, f"{name} returned negative affinity {score}"


def _winner(state):
    personas = build_aureon_personas(adapter=_StubAdapter())
    scores = {name: p.compute_affinity(state) for name, p in personas.items()}
    return max(scores.items(), key=lambda kv: kv[1])[0]


def test_mystic_dominates_on_love_and_528hz():
    state = _base_state(
        love_amplitude=0.95,
        gratitude_score=0.9,
        dominant_frequency_hz=528.0,
    )
    assert _winner(state) == "mystic"


def test_engineer_dominates_when_gate_is_clean():
    state = _base_state(
        coherence_gamma=0.96,
        node_readings={"tiger": 0.95},
    )
    assert _winner(state) == "engineer"


def test_artist_dominates_on_drop_energy_and_rally():
    state = _base_state(
        rally_active=True,
        cortex={"delta": 0.1, "theta": 0.1, "alpha": 0.1, "beta": 0.9, "gamma": 0.1},
        dj_drop={"energy": 0.9, "bpm": 128.0},
    )
    assert _winner(state) == "artist"


def test_quantum_physicist_dominates_on_lambda_and_psi():
    state = _base_state(
        last_lambda_t=1.8,
        consciousness_psi=0.9,
    )
    assert _winner(state) == "quantum_physicist"


def test_philosopher_dominates_on_theta_and_dawning():
    state = _base_state(
        cortex={"delta": 0.1, "theta": 0.85, "alpha": 0.1, "beta": 0.1, "gamma": 0.1},
        consciousness_level="DAWNING",
    )
    assert _winner(state) == "philosopher"


def test_child_dominates_on_delta_and_small_vault():
    state = _base_state(
        cortex={"delta": 0.95, "theta": 0.05, "alpha": 0.05, "beta": 0.05, "gamma": 0.05},
        vault_size=5,
        rally_active=False,
    )
    assert _winner(state) == "child"


def test_left_dominates_on_falcon_and_beta():
    state = _base_state(
        cortex={"delta": 0.05, "theta": 0.05, "alpha": 0.05, "beta": 0.9, "gamma": 0.05},
        node_readings={"falcon": 0.95},
        confidence=0.9,
    )
    assert _winner(state) == "left"


def test_right_dominates_on_dolphin_and_panda():
    state = _base_state(
        node_readings={"dolphin": 0.95, "panda": 0.95},
        love_amplitude=0.75,
    )
    assert _winner(state) == "right"


def test_painter_dominates_on_heart_chakra_and_gamma():
    state = _base_state(
        dominant_chakra="heart",
        love_amplitude=0.85,
        cortex={"delta": 0.05, "theta": 0.05, "alpha": 0.05, "beta": 0.1, "gamma": 0.9},
    )
    assert _winner(state) == "painter"


def test_elder_dominates_on_theta_plus_high_psi():
    state = _base_state(
        cortex={"delta": 0.05, "theta": 0.85, "alpha": 0.05, "beta": 0.05, "gamma": 0.05},
        consciousness_psi=0.95,
        vault_size=500,
        consciousness_level="",  # keep philosopher's level bonus off
    )
    assert _winner(state) == "elder"


def test_prompt_composition_yields_lines():
    state = _base_state()
    for cls in AUREON_PERSONA_REGISTRY.values():
        persona = cls(adapter=_StubAdapter())
        lines = persona._compose_prompt_lines(state)
        assert isinstance(lines, list) and lines, f"{cls.NAME} produced no lines"
        assert all(isinstance(line, str) and line for line in lines)


def test_prompt_only_uses_numbers_present_in_state():
    """Every numeric substring in the composed prompt must be derivable from state.

    We verify this by confirming the numbers that *do* appear are either
    small formatting artefacts (fixed labels like 528 Hz that come from state)
    or can be matched back to state values within a small tolerance.
    """
    state = _base_state(
        love_amplitude=0.712,
        gratitude_score=0.428,
        last_lambda_t=0.333,
        dominant_frequency_hz=528.0,
        vault_size=42,
        cortex={"delta": 0.11, "theta": 0.22, "alpha": 0.33, "beta": 0.44, "gamma": 0.55},
        consciousness_psi=0.678,
        coherence_gamma=0.852,
        confidence=0.654,
        node_readings={
            "owl": 0.1, "deer": 0.2, "dolphin": 0.3, "tiger": 0.4,
            "hummingbird": 0.5, "cargo_ship": 0.6, "clownfish": 0.7,
            "falcon": 0.8, "panda": 0.9,
        },
        dj_drop={"energy": 0.777, "bpm": 128.5},
    )
    allowed_values = []
    allowed_values.extend([state["love_amplitude"], state["gratitude_score"]])
    allowed_values.extend(state["cortex"].values())
    allowed_values.extend(state["node_readings"].values())
    allowed_values.extend([state["consciousness_psi"], state["coherence_gamma"], state["confidence"]])
    allowed_values.extend([state["last_lambda_t"], state["vault_size"], state["dominant_frequency_hz"]])
    allowed_values.extend([state["dj_drop"]["energy"], state["dj_drop"]["bpm"]])

    num_pat = re.compile(r"[-+]?\d*\.?\d+")
    for cls in AUREON_PERSONA_REGISTRY.values():
        persona = cls(adapter=_StubAdapter())
        lines = persona._compose_prompt_lines(state)
        text = " ".join(lines)
        for token in num_pat.findall(text):
            v = float(token)
            # tolerate the common {x:.2f}/{x:.3f}/{x:.0f} rounding
            assert any(abs(v - float(a)) < 0.02 for a in allowed_values), (
                f"{cls.NAME} emitted {token!r} not present in state"
            )


def test_speak_is_held_before_adapter_call():
    state = _base_state()

    class _Vault:
        pass

    vault = _Vault()
    vault.love_amplitude = state["love_amplitude"]
    vault.gratitude_score = state["gratitude_score"]
    vault.last_casimir_force = state["last_casimir_force"]
    vault.last_lambda_t = state["last_lambda_t"]
    vault.dominant_chakra = state["dominant_chakra"]
    vault.dominant_frequency_hz = state["dominant_frequency_hz"]
    vault.rally_active = state["rally_active"]
    vault.cortex_snapshot = state["cortex"]

    adapter = _StubAdapter()
    persona = MysticVoice(adapter=adapter)
    with pytest.raises(RuntimeError, match="vault_voice_hold"):
        persona.speak(vault)
    assert adapter.calls == []


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
