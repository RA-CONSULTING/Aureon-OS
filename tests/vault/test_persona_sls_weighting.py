"""Pure SLS-affinity tests plus release-HOLD wiring checks."""

from __future__ import annotations

import random
from typing import Any

import pytest

from aureon.vault.voice.aureon_personas import build_aureon_personas
from aureon.vault.voice.persona_vacuum import PersonaVacuum


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held SLS wiring touched an effect owner")


@pytest.mark.parametrize(
    ("name", "bias"),
    [
        ("engineer", -0.6),
        ("quantum_physicist", -0.6),
        ("left", -0.3),
        ("mystic", 0.6),
        ("painter", 0.6),
        ("elder", 0.3),
        ("right", 0.3),
        ("artist", 0.0),
    ],
)
def test_persona_sls_bias_is_explicit(name: str, bias: float) -> None:
    assert build_aureon_personas()[name].SLS_BIAS == bias


def test_sls_modifier_is_positive_clamped_and_neutral_at_midpoint() -> None:
    personas = build_aureon_personas()
    for persona in personas.values():
        assert persona.sls_affinity_modifier(None) == 1.0
        assert persona.sls_affinity_modifier("invalid") == 1.0
        assert persona.sls_affinity_modifier(0.5) == pytest.approx(1.0)
        assert persona.sls_affinity_modifier(-100.0) > 0.0
        assert persona.sls_affinity_modifier(100.0) > 0.0


def test_low_and_high_sls_shift_structure_and_meaning_scores() -> None:
    personas = build_aureon_personas()
    base = {
        "love_amplitude": 0.7,
        "gratitude_score": 0.7,
        "dominant_frequency_hz": 528.0,
        "last_lambda_t": 0.8,
        "consciousness_psi": 0.7,
        "coherence_gamma": 0.8,
        "confidence": 0.7,
        "cortex": {"theta": 0.5, "beta": 0.5, "gamma": 0.5},
        "node_readings": {"tiger": 0.7, "falcon": 0.7, "dolphin": 0.7, "panda": 0.7},
        "dj_drop": {"energy": 0.5},
        "vault_size": 50,
    }
    low_vacuum = PersonaVacuum(personas=personas, rng=random.Random(1))
    high_vacuum = PersonaVacuum(personas=build_aureon_personas(), rng=random.Random(1))
    _winner_l, _probs_l, low = low_vacuum._sample(dict(base, symbolic_life_score=0.0))
    _winner_h, _probs_h, high = high_vacuum._sample(dict(base, symbolic_life_score=1.0))
    assert low["engineer"] > high["engineer"]
    assert low["quantum_physicist"] > high["quantum_physicist"]
    assert high["mystic"] > low["mystic"]
    assert high["painter"] > low["painter"]
    assert high["artist"] == pytest.approx(low["artist"])


def test_vault_sls_precedence_is_pure() -> None:
    class Vault:
        current_symbolic_life_score = 0.8

    vacuum = PersonaVacuum(personas=build_aureon_personas())
    vacuum._latest_sls = 0.1
    assert vacuum._current_sls(Vault()) == 0.8
    assert vacuum._current_sls(None) == 0.1


def test_symbolic_life_bus_subscription_is_held() -> None:
    vacuum = PersonaVacuum(
        personas=build_aureon_personas(),
        thought_bus=_Trap(),
    )
    with pytest.raises(RuntimeError, match="persona_vacuum_hold"):
        vacuum.start()
    assert vacuum._subscribed is False
