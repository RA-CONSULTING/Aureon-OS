"""The labyrinth scan reads Enigma's direction from the key get_guidance() returns.

``EnigmaIntegration.get_guidance()`` returns ``'signal'`` (BUY, SELL or HOLD).
The scan used to read ``'action'``, so its base Enigma score was always 0.0.
"""

from __future__ import annotations

import pytest

from aureon.trading.micro_profit_labyrinth import enigma_guidance_base_score
from aureon.wisdom.aureon_enigma_integration import EnigmaIntegration

_LAYERS = (
    "harmonic_fusion",
    "probability_nexus",
    "mycelium",
    "timeline_oracle",
    "thought_bus",
    "dreamer",
    "coherence_system",
    "barons_analyzer",
    "math_angel",
    "harmonic_reality",
    "qgita",
)


class _FixedNexus:
    def __init__(self, value: float) -> None:
        self.value = value

    def get_signal(self) -> float:
        return self.value


def _guidance_from_real_get_guidance(nexus_signal: float) -> dict:
    """Run the real get_guidance() with one fixed layer and every other layer off."""

    enigma = object.__new__(EnigmaIntegration)
    for name in _LAYERS:
        setattr(enigma, name, None)
    enigma.probability_nexus = _FixedNexus(nexus_signal)
    return enigma.get_guidance()


@pytest.mark.parametrize(
    ("nexus_signal", "signal", "direction", "sign"),
    [(0.8, "BUY", "BULLISH", 1), (-0.8, "SELL", "BEARISH", -1), (0.1, "HOLD", "NEUTRAL", 0)],
)
def test_real_guidance_moves_the_base_score(nexus_signal, signal, direction, sign) -> None:
    guidance = _guidance_from_real_get_guidance(nexus_signal)
    assert "action" not in guidance
    assert guidance["signal"] == signal

    score, got_direction = enigma_guidance_base_score(guidance)

    assert got_direction == direction
    if sign > 0:
        assert score == pytest.approx(guidance["confidence"] * 0.3)
        assert score > 0
    elif sign < 0:
        assert score == pytest.approx(-guidance["confidence"] * 0.15)
        assert score < 0
    else:
        assert score == 0.0


@pytest.mark.parametrize(
    ("guidance", "expected"),
    [
        ({"signal": "BUY", "confidence": 0.5}, (0.15, "BULLISH")),
        ({"signal": "SELL", "confidence": 0.4}, (-0.06, "BEARISH")),
        ({"signal": "HOLD", "confidence": 0.9}, (0.0, "NEUTRAL")),
        ({}, (0.0, "NEUTRAL")),
    ],
)
def test_base_score_mapping_is_unchanged(guidance, expected) -> None:
    score, direction = enigma_guidance_base_score(guidance)
    assert score == pytest.approx(expected[0])
    assert direction == expected[1]


def test_a_stray_action_key_is_not_read() -> None:
    assert enigma_guidance_base_score({"action": "BUY", "confidence": 1.0}) == (0.0, "NEUTRAL")
