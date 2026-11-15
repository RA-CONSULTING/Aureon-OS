"""The hive mind reads Enigma's direction from the key get_guidance() returns.

``EnigmaIntegration.get_guidance()`` returns its direction under ``'signal'``
(BUY, SELL or HOLD) and has no ``'action'`` key. ``dream_of_winning`` used to
read ``'action'``, so its Enigma signal always fell back to HOLD and scored a
flat 0.5 whatever Enigma said. #359 fixed the same bug in the labyrinth scan.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from aureon.utils.aureon_queen_hive_mind import QueenHiveMind
from aureon.wisdom.aureon_enigma_integration import EnigmaIntegration

REPO = Path(__file__).resolve().parents[1]
KIMI = "imports/Kimi_Agent_Aureon_20260408/aureon-trading-main-snapshot/aureon"

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


class _FixedGuidance:
    def __init__(self, guidance: dict) -> None:
        self.guidance = guidance

    def get_guidance(self) -> dict:
        return dict(self.guidance)


def _real_guidance(nexus_signal: float) -> dict:
    """Run the real get_guidance() with one fixed layer and every other layer off."""

    enigma = object.__new__(EnigmaIntegration)
    for name in _LAYERS:
        setattr(enigma, name, None)
    enigma.probability_nexus = _FixedNexus(nexus_signal)
    return enigma.get_guidance()


def _dream_with(enigma) -> dict:
    """Run the real dream_of_winning() with only the Enigma signal wired."""

    queen = object.__new__(QueenHiveMind)
    # dream_of_winning reads these two without a hasattr guard.
    queen.temporal_biometric_link = None
    queen.location_tracker = None
    queen.enigma = enigma
    return queen.dream_of_winning({"symbol": "BTC/USD", "action": "BUY"})


@pytest.mark.parametrize(
    ("nexus_signal", "signal"),
    [(0.8, "BUY"), (-0.8, "SELL"), (0.1, "HOLD")],
)
def test_dream_scores_enigma_from_real_guidance_signal(nexus_signal, signal) -> None:
    guidance = _real_guidance(nexus_signal)
    assert "action" not in guidance
    assert guidance["signal"] == signal
    confidence = guidance["confidence"]

    metrics = _dream_with(_FixedGuidance(guidance))["metrics"]
    intel = metrics["enigma_intelligence"]

    assert intel["action"] == signal
    if signal == "BUY":
        assert confidence > 0
        assert metrics["enigma_score"] == pytest.approx(0.5 + confidence * 0.2)
        assert metrics["enigma_score"] > 0.5
    elif signal == "SELL":
        assert confidence > 0
        assert metrics["enigma_score"] == pytest.approx(0.4 - confidence * 0.2)
        assert metrics["enigma_score"] < 0.4
    else:
        assert metrics["enigma_score"] == 0.5
    assert intel["score"] == metrics["enigma_score"]


def test_dream_does_not_read_a_stray_action_key() -> None:
    metrics = _dream_with(_FixedGuidance({"action": "BUY", "confidence": 1.0}))["metrics"]
    assert metrics["enigma_intelligence"]["action"] == "HOLD"
    assert metrics["enigma_score"] == 0.5


def _guidance_reads(path: Path) -> list[tuple[str, int, str]]:
    """Every string key read from a name bound to a ``...get_guidance()`` result.

    Returns ``(function, line, key)`` for ``name.get('key', ...)`` and
    ``name['key']``, plus ``(function, line, '<call:fn>')`` when the name is
    passed straight to a function.
    """

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[tuple[str, int, str]] = []
    for func in ast.walk(tree):
        if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        bound = set()
        for node in ast.walk(func):
            if isinstance(node, ast.Assign) and any(
                isinstance(c, ast.Call)
                and isinstance(c.func, ast.Attribute)
                and c.func.attr == "get_guidance"
                for c in ast.walk(node.value)
            ):
                bound.update(t.id for t in node.targets if isinstance(t, ast.Name))
        if not bound:
            continue
        for node in ast.walk(func):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in bound
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                found.append((func.name, node.lineno, node.args[0].value))
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id in bound
                and isinstance(node.slice, ast.Constant)
            ):
                found.append((func.name, node.lineno, node.slice.value))
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and any(isinstance(a, ast.Name) and a.id in bound for a in node.args)
            ):
                found.append((func.name, node.lineno, f"<call:{node.func.id}>"))
    return found


@pytest.mark.parametrize(
    "relpath",
    [
        "aureon/utils/aureon_queen_hive_mind.py",
        "Kings_Accounting_Suite/aureon_systems/aureon_queen_hive_mind.py",
        f"{KIMI}/utils/aureon_queen_hive_mind.py",
        f"{KIMI}/trading/micro_profit_labyrinth.py",
    ],
    ids=["hive_mind", "kings_hive_mind", "kimi_hive_mind", "kimi_labyrinth"],
)
def test_copies_read_signal_not_action_from_get_guidance(relpath) -> None:
    reads = _guidance_reads(REPO / relpath)
    keys = {key for _, _, key in reads}
    assert "signal" in keys, reads
    assert "action" not in keys, reads


def test_labyrinth_scan_scores_guidance_with_the_shared_helper() -> None:
    reads = _guidance_reads(REPO / "aureon/trading/micro_profit_labyrinth.py")
    scan = [(line, key) for func, line, key in reads if func == "_find_asset_opportunities"]
    assert "<call:enigma_guidance_base_score>" in {key for _, key in scan}, scan
    assert "action" not in {key for _, key in scan}, scan
