"""Fail-closed tests for MetaCognitionObserver."""

from __future__ import annotations

from typing import Any, Callable

import pytest

from aureon.vault.voice import meta_cognition_observer as meta_module
from aureon.vault.voice.meta_cognition_observer import (
    META_COGNITION_RELEASE_HOLD,
    MetaCognitionObserver,
    ReflectionCard,
    get_meta_cognition_observer,
    reset_meta_cognition_observer,
)


class _Trap:
    def __getattribute__(self, _name: str) -> Any:
        raise AssertionError("release-held meta observer touched an effect owner")


def test_reflection_card_data_contract_remains_pure() -> None:
    card = ReflectionCard(reflection_id="r1", persona="engineer")
    payload = card.to_dict()
    assert payload["reflection_id"] == "r1"
    assert payload["persona"] == "engineer"
    assert META_COGNITION_RELEASE_HOLD.startswith("meta_cognition_observer_hold:")


def test_constructor_is_inert() -> None:
    observer = MetaCognitionObserver(
        thought_bus=_Trap(),
        vault=_Trap(),
        hash_resonance_index=_Trap(),
        queen_metacognition=_Trap(),
    )
    assert observer._subscribed is False
    assert observer._running is False
    assert observer._closer_thread is None
    assert observer.open_window_count == 0
    assert observer.closed_cards == []


def test_start_holds_before_subscription_or_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "aureon.vault.voice.meta_cognition_observer.threading.Thread",
        lambda *_args, **_kwargs: pytest.fail("meta observer must not create a thread"),
    )
    observer = MetaCognitionObserver(thought_bus=_Trap(), vault=_Trap())
    with pytest.raises(RuntimeError, match="meta_cognition_observer_hold"):
        observer.start()
    assert observer._subscribed is False
    assert observer._running is False
    assert observer._closer_thread is None


@pytest.mark.parametrize(
    "factory",
    [
        lambda obs, card: obs._on_thought(_Trap()),
        lambda obs, card: obs._open_window({}),
        lambda obs, card: obs._closer_loop(),
        lambda obs, card: obs._sweep_closed(),
        lambda obs, card: obs.close_expired(),
        lambda obs, card: obs._finalise(_Trap()),
        lambda obs, card: obs._compute_bond(_Trap()),
        lambda obs, card: obs._publish_card(card),
        lambda obs, card: obs._feed_vault(card),
        lambda obs, card: obs._feed_queen_metacognition(card),
    ],
)
def test_direct_runtime_paths_hold_without_opening_or_closing_windows(
    factory: Callable[[MetaCognitionObserver, ReflectionCard], Any],
) -> None:
    observer = MetaCognitionObserver(
        thought_bus=_Trap(), vault=_Trap(),
        hash_resonance_index=_Trap(), queen_metacognition=_Trap(),
    )
    card = ReflectionCard(reflection_id="r1")
    with pytest.raises(RuntimeError, match="meta_cognition_observer_hold"):
        factory(observer, card)
    assert observer.open_window_count == 0
    assert observer.closed_cards == []


def test_singleton_getter_holds_without_creating_singleton() -> None:
    reset_meta_cognition_observer()
    assert meta_module._singleton is None
    with pytest.raises(RuntimeError, match="meta_cognition_observer_hold"):
        get_meta_cognition_observer(_Trap(), _Trap(), _Trap(), _Trap())
    assert meta_module._singleton is None
