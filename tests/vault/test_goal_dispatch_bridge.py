"""Fail-closed tests for GoalDispatchBridge."""

from __future__ import annotations

from enum import Enum, auto
from typing import Any

import pytest

from aureon.vault.voice import goal_dispatch_bridge as bridge_module
from aureon.vault.voice.goal_dispatch_bridge import (
    GoalDispatchBridge,
    get_goal_dispatch_bridge,
    reset_goal_dispatch_bridge,
)


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held goal bridge touched an effect owner")


def test_constructor_is_inert_and_reports_zero_activity() -> None:
    bridge = GoalDispatchBridge(
        thought_bus=_Trap(),
        conscience=_Trap(),
        goal_engine=_Trap(),
        vault=_Trap(),
    )
    assert bridge.stats() == {
        "status": "HOLD",
        "reason_code": "production_magic_star_release_unavailable",
        "production_ready": False,
        "effect_enabled": False,
        "dispatched": 0,
        "vetoed": 0,
        "abandoned": 0,
        "has_engine": True,
        "has_conscience": True,
        "subscribed": False,
    }


def test_start_and_intake_hold_before_subscription_dedup_or_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "aureon.vault.voice.goal_dispatch_bridge.threading.Thread",
        lambda *_args, **_kwargs: pytest.fail("goal bridge must not create a thread"),
    )
    bridge = GoalDispatchBridge(
        thought_bus=_Trap(),
        conscience=_Trap(),
        goal_engine=_Trap(),
        vault=_Trap(),
    )
    with pytest.raises(RuntimeError, match="goal_dispatch_bridge_hold"):
        bridge.start()
    with pytest.raises(RuntimeError, match="goal_dispatch_bridge_hold"):
        bridge._on_submit_request(_Trap())
    assert bridge._dispatched == set()
    assert bridge.stats()["subscribed"] is False


@pytest.mark.parametrize(
    "call_name",
    ["dispatch", "engine", "abandon", "unavailable", "publish"],
)
def test_direct_effect_helpers_are_held(call_name: str) -> None:
    bridge = GoalDispatchBridge(
        thought_bus=_Trap(),
        conscience=_Trap(),
        goal_engine=_Trap(),
    )
    calls = {
        "dispatch": lambda: bridge._dispatch("g", "goal", {}, {}),
        "engine": lambda: bridge._run_engine_submit("g", "goal"),
        "abandon": lambda: bridge._publish_abandoned("g", "reason"),
        "unavailable": lambda: bridge._publish_dispatch_unavailable("g", "goal"),
        "publish": lambda: bridge._publish("topic", {"x": 1}),
    }
    with pytest.raises(RuntimeError, match="goal_dispatch_bridge_hold"):
        calls[call_name]()
    assert bridge.stats()["dispatched"] == 0
    assert bridge.stats()["vetoed"] == 0
    assert bridge.stats()["abandoned"] == 0


def test_context_building_is_pure_and_bounded() -> None:
    class Vault:
        current_symbolic_life_score = 1.7

    bridge = GoalDispatchBridge(vault=Vault())
    context = bridge._build_context({
        "goal_id": "g",
        "proposed_by_persona": "engineer",
        "urgency": 0.8,
        "parameters": {"risk": 0.2, "leverage": 2, "ignored": "x"},
    })
    assert context == {
        "persona": "engineer",
        "goal_id": "g",
        "urgency": 0.8,
        "symbolic_life_score": 1.0,
        "risk": 0.2,
        "leverage": 2,
    }


def test_verdict_and_reason_helpers_are_pure() -> None:
    class Verdict(Enum):
        VETO = auto()

    class Whisper:
        verdict = Verdict.VETO
        message = "stop"
        why_it_matters = "unsafe"

    assert GoalDispatchBridge._verdict_label(Whisper()) == "VETO"
    assert GoalDispatchBridge._whisper_reason(Whisper()) == "stop | unsafe"


def test_singleton_getter_is_held_and_reset_is_inert() -> None:
    reset_goal_dispatch_bridge()
    assert bridge_module._singleton is None
    with pytest.raises(RuntimeError, match="goal_dispatch_bridge_hold"):
        get_goal_dispatch_bridge(
            thought_bus=_Trap(),
            conscience=_Trap(),
            goal_engine=_Trap(),
        )
    assert bridge_module._singleton is None
    reset_goal_dispatch_bridge()
