"""Fail-closed tests for SymbolicLifeBridge."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from aureon.vault.voice.symbolic_life_bridge import (
    SYMBOLIC_LIFE_RELEASE_HOLD,
    SymbolicLifeBridge,
)


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held symbolic bridge touched an effect owner")


def test_constructor_does_not_import_or_build_default_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        SymbolicLifeBridge,
        "_build_lambda_engine",
        staticmethod(lambda: pytest.fail("constructor must not build LambdaEngine")),
    )
    monkeypatch.setattr(
        SymbolicLifeBridge,
        "_import_reading_cls",
        staticmethod(lambda: pytest.fail("constructor must not import reading type")),
    )
    bridge = SymbolicLifeBridge(thought_bus=_Trap(), vault=_Trap(), interval_s=0.1)
    assert bridge._lambda_engine is None
    assert bridge._SubsystemReading is None
    assert bridge._subscribed is False
    assert bridge._running is False
    assert bridge._thread is None
    assert bridge.pulse_count == 0


def test_start_holds_before_subscription_or_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "aureon.vault.voice.symbolic_life_bridge.threading.Thread",
        lambda *_args, **_kwargs: pytest.fail("symbolic bridge must not create a thread"),
    )
    bridge = SymbolicLifeBridge(
        thought_bus=_Trap(), vault=_Trap(), lambda_engine=_Trap(), interval_s=0.1
    )
    with pytest.raises(RuntimeError, match="symbolic_life_bridge_hold"):
        bridge.start()
    assert bridge._subscribed is False
    assert bridge._running is False


@pytest.mark.parametrize(
    "name",
    [
        "_on_persona_collapse",
        "_on_persona_thought",
        "_on_goal_request",
        "_on_life_event",
        "_on_peer_state",
        "_on_conversation_turn",
        "_on_goal_echo_summary",
        "_on_goal_echo_orphaned",
    ],
)
def test_callbacks_hold_before_reading_input_or_mutating_state(name: str) -> None:
    bridge = SymbolicLifeBridge(lambda_engine=_Trap())
    before = bridge.rolling_summary()
    with pytest.raises(RuntimeError, match="symbolic_life_bridge_hold"):
        getattr(bridge, name)(_Trap())
    assert bridge.rolling_summary() == before


@pytest.mark.parametrize("name", ["readings", "pulse", "publish", "loop", "engine", "type"])
def test_direct_execution_paths_are_held(name: str) -> None:
    bridge = SymbolicLifeBridge(thought_bus=_Trap(), vault=_Trap(), lambda_engine=_Trap())
    calls = {
        "readings": bridge._build_readings,
        "pulse": bridge.pulse,
        "publish": lambda: bridge._publish_pulse(_Trap(), []),
        "loop": bridge._loop,
        "engine": bridge._build_lambda_engine,
        "type": bridge._import_reading_cls,
    }
    with pytest.raises(RuntimeError, match="symbolic_life_bridge_hold"):
        calls[name]()
    assert bridge.pulse_count == 0
    assert bridge.last_state is None


def test_payload_translation_remains_pure() -> None:
    state = SimpleNamespace(symbolic_life_score=0.5, lambda_t=1.0)
    payload = SymbolicLifeBridge._state_to_payload(state, [])
    assert payload["symbolic_life_score"] == 0.5
    assert SYMBOLIC_LIFE_RELEASE_HOLD.startswith("symbolic_life_bridge_hold:")
