"""Fail-closed tests for the package-exported bus flight observer."""

from __future__ import annotations

from typing import Any

import pytest

from aureon.vault.voice import bus_flight_check as flight_module
from aureon.vault.voice.bus_flight_check import (
    BUS_FLIGHT_CHECK_RELEASE_HOLD,
    BusFlightCheck,
    get_bus_flight_check,
    reset_bus_flight_check,
)


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held flight check touched an effect owner")


def test_constructor_is_inert() -> None:
    check = BusFlightCheck(_Trap())
    assert check.thought_bus is not None
    assert check._subscribed is False
    assert check._running is False
    assert check._thread is None
    assert dict(check._activity) == {}


def test_start_and_watcher_hold_before_subscription_or_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "aureon.vault.voice.bus_flight_check.threading.Thread",
        lambda *_args, **_kwargs: pytest.fail("flight check must not create a thread"),
    )
    check = BusFlightCheck(_Trap())
    with pytest.raises(RuntimeError, match="bus_flight_check_hold"):
        check.start()
    with pytest.raises(RuntimeError, match="bus_flight_check_hold"):
        check.start_watching()
    assert check._subscribed is False
    assert check._running is False
    assert check._thread is None


@pytest.mark.parametrize("entrypoint", ["callback", "loop", "publish"])
def test_direct_runtime_entrypoints_are_held(entrypoint: str) -> None:
    check = BusFlightCheck(_Trap())
    calls = {
        "callback": lambda: check._on_any_thought(_Trap()),
        "loop": check._watch_loop,
        "publish": lambda: check._publish_pulse({}),
    }
    with pytest.raises(RuntimeError, match="bus_flight_check_hold"):
        calls[entrypoint]()
    assert dict(check._activity) == {}


def test_singleton_getter_holds_without_creating_singleton() -> None:
    reset_bus_flight_check()
    assert flight_module._singleton is None
    with pytest.raises(RuntimeError, match="bus_flight_check_hold"):
        get_bus_flight_check(_Trap())
    assert flight_module._singleton is None


def test_topic_matching_remains_pure() -> None:
    assert BUS_FLIGHT_CHECK_RELEASE_HOLD.endswith(
        "production_magic_star_release_unavailable"
    )
    assert BusFlightCheck._matches("goal.completed", "goal.*") is True
    assert BusFlightCheck._matches("goal.completed", "persona.*") is False
