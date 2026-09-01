"""Fail-closed tests for the public persona action surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from aureon.vault.voice.persona_action import PersonaAction, PersonaActuator
from aureon.vault.voice.persona_vacuum import PersonaVacuum


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held persona path touched an effect owner")


def _action(kind: str, tmp_path: Path) -> PersonaAction:
    return PersonaAction(
        kind=kind,
        topic="held.topic",
        target=str(tmp_path / "should-not-exist.jsonl"),
        payload={"value": 1},
        reason="safety probe",
        urgency=0.9,
    )


def test_persona_action_to_dict_and_defaults_are_pure() -> None:
    action = PersonaAction(kind="bus.publish")
    assert action.topic == ""
    assert action.payload == {}
    assert action.target == ""
    assert action.reason == ""
    assert action.urgency == 0.5
    assert action.to_dict()["kind"] == "bus.publish"


def test_actuator_construction_only_registers_inert_handlers(tmp_path: Path) -> None:
    actuator = PersonaActuator(
        thought_bus=_Trap(),
        vault=_Trap(),
        file_root=str(tmp_path),
    )
    assert set(actuator._handlers) == {
        "bus.publish",
        "vault.ingest",
        "file.append",
        "skill.request",
        "goal.submit",
    }
    assert actuator.history() == []
    assert actuator.status()["status"] == "HOLD"
    assert actuator.status()["effect_enabled"] is False
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "kind",
    [
        "bus.publish",
        "vault.ingest",
        "file.append",
        "skill.request",
        "goal.submit",
        "unknown.kind",
    ],
)
def test_dispatch_holds_before_handler_bus_vault_or_file(
    kind: str,
    tmp_path: Path,
) -> None:
    actuator = PersonaActuator(
        thought_bus=_Trap(),
        vault=_Trap(),
        file_root=str(tmp_path),
    )
    with pytest.raises(RuntimeError, match="persona_action_hold"):
        actuator.dispatch("engineer", _action(kind, tmp_path), {"persona": "engineer"})
    assert actuator.history() == []
    assert list(tmp_path.iterdir()) == []


def test_dispatch_none_and_custom_handlers_cannot_bypass_hold(tmp_path: Path) -> None:
    calls: list[str] = []
    actuator = PersonaActuator(file_root=str(tmp_path))
    actuator.register("custom", lambda *_args: calls.append("called"))
    with pytest.raises(RuntimeError, match="persona_action_hold"):
        actuator.dispatch("persona", None)
    with pytest.raises(RuntimeError, match="persona_action_hold"):
        actuator.dispatch("persona", _action("custom", tmp_path))
    assert calls == []
    assert actuator.history() == []


@pytest.mark.parametrize(
    "handler_name",
    [
        "_handle_bus_publish",
        "_handle_vault_ingest",
        "_handle_file_append",
        "_handle_skill_request",
        "_handle_goal_submit",
    ],
)
def test_direct_default_handler_calls_are_held(
    handler_name: str,
    tmp_path: Path,
) -> None:
    actuator = PersonaActuator(
        thought_bus=_Trap(),
        vault=_Trap(),
        file_root=str(tmp_path),
    )
    handler = getattr(actuator, handler_name)
    with pytest.raises(RuntimeError, match="persona_action_hold"):
        handler(_action("file.append", tmp_path), {"persona": "engineer"})
    assert list(tmp_path.iterdir()) == []


def test_persona_vacuum_cannot_reach_actuator() -> None:
    vacuum = PersonaVacuum(thought_bus=_Trap(), vault=_Trap())
    before = vacuum.collapse_count
    with pytest.raises(RuntimeError, match="persona_vacuum_hold"):
        vacuum.observe(_Trap())
    assert vacuum.collapse_count == before
    assert vacuum.last_action_execution is None
    assert vacuum.last_goal_execution is None
