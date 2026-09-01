"""Pure goal-proposal tests plus release-HOLD execution tests."""

from __future__ import annotations

from typing import Any

import pytest

from aureon.vault.voice.aureon_personas import (
    ArtistVoice,
    EngineerVoice,
    QuantumPhysicistVoice,
    ResonantPersona,
)
from aureon.vault.voice.persona_action import PersonaAction, PersonaActuator
from aureon.vault.voice.persona_vacuum import PersonaVacuum


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held goal path touched an effect owner")


def test_base_persona_has_no_goal() -> None:
    assert ResonantPersona().propose_goal({}) is None


def test_goal_proposals_are_strict_and_pure() -> None:
    artist = ArtistVoice()
    assert artist.propose_goal({"dj_drop": {"energy": 0.89}, "rally_active": True}) is None
    assert "SVG" in (artist.propose_goal({
        "dj_drop": {"energy": 0.95},
        "rally_active": True,
        "dominant_chakra": "heart",
    }) or "")

    physicist = QuantumPhysicistVoice()
    assert physicist.propose_goal({"last_lambda_t": 1.4, "consciousness_psi": 0.95}) is None
    assert "research note" in (physicist.propose_goal({
        "last_lambda_t": 1.8,
        "consciousness_psi": 0.95,
    }) or "")

    engineer = EngineerVoice()
    assert engineer.propose_goal({
        "coherence_gamma": 0.95,
        "node_readings": {"tiger": 0.9},
    }) is None
    assert "coherence-audit" in (engineer.propose_goal({
        "coherence_gamma": 0.97,
        "node_readings": {"tiger": 0.9},
    }) or "")


def test_goal_submit_action_is_held_before_bus_publication() -> None:
    actuator = PersonaActuator(thought_bus=_Trap())
    action = PersonaAction(
        kind="goal.submit",
        topic="build an audit tool",
        payload={"scope": "local"},
    )
    with pytest.raises(RuntimeError, match="persona_action_hold"):
        actuator.dispatch("engineer", action, {"persona": "engineer"})
    with pytest.raises(RuntimeError, match="persona_action_hold"):
        actuator._handle_goal_submit(action, {"persona": "engineer"})
    assert actuator.history() == []


def test_vacuum_goal_flow_is_held_before_collapse_or_dispatch() -> None:
    persona = EngineerVoice(adapter=_Trap())
    vacuum = PersonaVacuum(
        personas={"engineer": persona},
        thought_bus=_Trap(),
        actuator=PersonaActuator(thought_bus=_Trap()),
    )
    with pytest.raises(RuntimeError, match="persona_vacuum_hold"):
        vacuum.observe(_Trap())
    assert vacuum.collapse_count == 0
    assert vacuum.last_goal_execution is None
