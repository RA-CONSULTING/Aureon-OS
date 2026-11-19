"""get_guidance() skips non-numeric layer values and names them in skipped_layers.

``EnhancedProbabilityNexus.get_signal()`` returns ``make_predictions()[0]`` (a
dict) or ``None``, never a number. ``get_guidance()`` put that value straight
into its signal list and multiplied it, so it raised ``TypeError`` (see
/workspace/enigma_layer_audit_20261113.md, Layer 2).

These tests cover the crash only. They make no claim that any layer carries
real data, and they don't map a prediction dict to a number.
"""

from __future__ import annotations

import importlib

import pytest

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


@pytest.fixture
def enigma_module(tmp_path, monkeypatch):
    """Import from a scratch cwd; importing and building the module writes files there."""

    monkeypatch.chdir(tmp_path)
    return importlib.import_module("aureon.wisdom.aureon_enigma_integration")


class _Nexus:
    def __init__(self, value) -> None:
        self.value = value

    def get_signal(self):
        return self.value


class _Fusion:
    def __init__(self, value) -> None:
        self.value = value

    def get_state(self) -> dict:
        return {"signal": self.value}


def _bare(enigma_module, **layers):
    """A bare EnigmaIntegration with every layer off except the ones given."""

    enigma = object.__new__(enigma_module.EnigmaIntegration)
    for name in _LAYERS:
        setattr(enigma, name, None)
    for name, value in layers.items():
        setattr(enigma, name, value)
    return enigma


@pytest.mark.parametrize(
    "raw",
    [None, {"signal": "BUY", "confidence": 0.9}, "BUY", float("nan"), True],
    ids=["none", "prediction-dict", "string", "nan", "bool"],
)
def test_non_numeric_nexus_value_is_skipped_not_mixed(enigma_module, raw) -> None:
    guidance = _bare(enigma_module, probability_nexus=_Nexus(raw)).get_guidance()

    assert guidance["skipped_layers"] == ["probability_nexus"]
    assert guidance["active_layers"] == 0
    assert guidance["raw_signal"] == 0
    assert guidance["signal"] == "HOLD"


def test_numeric_layers_still_mix_beside_a_skipped_one(enigma_module) -> None:
    guidance = _bare(
        enigma_module,
        harmonic_fusion=_Fusion(0.5),
        probability_nexus=_Nexus(None),
    ).get_guidance()

    assert guidance["skipped_layers"] == ["probability_nexus"]
    assert guidance["active_layers"] == 1
    assert guidance["raw_signal"] == pytest.approx(0.5)
    assert guidance["signal"] == "BUY"


def test_all_numeric_layers_skip_nothing(enigma_module) -> None:
    guidance = _bare(
        enigma_module,
        harmonic_fusion=_Fusion(-0.4),
        probability_nexus=_Nexus(-0.4),
    ).get_guidance()

    assert guidance["skipped_layers"] == []
    assert guidance["active_layers"] == 2
    assert guidance["signal"] == "SELL"


def test_default_build_get_guidance_does_not_raise(enigma_module) -> None:
    guidance = enigma_module.EnigmaIntegration().get_guidance()

    assert guidance["signal"] in {"BUY", "SELL", "HOLD"}
    assert isinstance(guidance["skipped_layers"], list)
