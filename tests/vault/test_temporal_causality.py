"""Fail-closed tests for TemporalCausalityLaw."""

from __future__ import annotations

from typing import Any, Callable

import pytest

from aureon.vault.voice import temporal_causality as temporal_module
from aureon.vault.voice.temporal_causality import (
    TEMPORAL_CAUSALITY_RELEASE_HOLD,
    GoalEcho,
    GoalState,
    TemporalCausalityLaw,
    get_temporal_causality_law,
    reset_temporal_causality_law,
)


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held temporal law touched an effect owner")


def test_goal_echo_data_contract_remains_pure() -> None:
    echo = GoalEcho(goal_id="g1", text="review evidence")
    assert echo.state is GoalState.PROPOSED
    assert echo.is_terminal() is False
    assert echo.to_dict()["goal_id"] == "g1"
    echo.state = GoalState.COMPLETED
    assert echo.is_terminal() is True
    assert TEMPORAL_CAUSALITY_RELEASE_HOLD.startswith("temporal_causality_hold:")


def test_constructor_is_inert_and_empty_queries_remain_available() -> None:
    law = TemporalCausalityLaw(thought_bus=_Trap(), vault=_Trap())
    assert law._subscribed is False
    assert law._goals == {}
    assert law._pulse_count == 0
    assert law.active() == []
    assert law.all() == []
    assert law.summary()["total_goals"] == 0


@pytest.mark.parametrize(
    "name",
    ["_on_submit_request", "_on_submitted", "_on_progress", "_on_completed", "_on_abandoned"],
)
def test_start_and_inbound_callbacks_hold_before_owner_access(name: str) -> None:
    law = TemporalCausalityLaw(thought_bus=_Trap(), vault=_Trap())
    with pytest.raises(RuntimeError, match="temporal_causality_hold"):
        getattr(law, name)(_Trap())
    assert law._goals == {}
    assert law._pulse_count == 0


def test_start_holds_before_subscription() -> None:
    law = TemporalCausalityLaw(thought_bus=_Trap(), vault=_Trap())
    with pytest.raises(RuntimeError, match="temporal_causality_hold"):
        law.start()
    assert law._subscribed is False


@pytest.mark.parametrize(
    "factory",
    [
        lambda law, echo: law.track({"goal_id": "g"}),
        lambda law, echo: law.acknowledge("g"),
        lambda law, echo: law.update_progress("g", 0.5),
        lambda law, echo: law.complete("g", "done"),
        lambda law, echo: law.abandon("g", "reason"),
        lambda law, echo: law.pulse(),
        lambda law, echo: law._record_transition(echo, GoalState.COMPLETED, "done"),
        lambda law, echo: law._publish_echo(echo, "goal.echo"),
        lambda law, echo: law._publish_summary({}),
        lambda law, echo: law._feed_vault(echo),
    ],
)
def test_direct_transition_and_effect_paths_hold_without_state_change(
    factory: Callable[[TemporalCausalityLaw, GoalEcho], Any],
) -> None:
    law = TemporalCausalityLaw(thought_bus=_Trap(), vault=_Trap())
    echo = GoalEcho(goal_id="g")
    with pytest.raises(RuntimeError, match="temporal_causality_hold"):
        factory(law, echo)
    assert law._goals == {}
    assert law._pulse_count == 0
    assert echo.state is GoalState.PROPOSED
    assert echo.transitions == []


def test_singleton_getter_holds_without_creating_singleton() -> None:
    reset_temporal_causality_law()
    assert temporal_module._singleton is None
    with pytest.raises(RuntimeError, match="temporal_causality_hold"):
        get_temporal_causality_law(_Trap(), _Trap())
    assert temporal_module._singleton is None
