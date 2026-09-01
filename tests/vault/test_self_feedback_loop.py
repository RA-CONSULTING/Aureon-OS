"""Fail-closed contract for the unreleased self-feedback effect owner."""

from __future__ import annotations

import pytest

from aureon.vault import self_feedback_loop as loop_module
from aureon.vault.self_feedback_loop import AureonSelfFeedbackLoop


def test_default_constructor_is_inert_and_provider_modules_are_not_loaded() -> None:
    loop = AureonSelfFeedbackLoop(base_interval_s=0.01)

    assert loop._running is False
    assert loop._thread is None
    assert loop.voice_engine is None
    assert loop._enhance_enabled is False
    assert loop._enhancer is None
    assert loop.vault._thought_bus is None
    assert loop.vault._subscribed is False
    assert loop.casimir._engine is None
    assert loop.casimir._engine_kind == "stub"
    assert loop.pinger._chirp_bus is None
    assert loop.pinger._thought_bus is None
    assert loop_module.SelfDialogueEngine is None
    assert loop_module.get_self_enhancement_engine is None


@pytest.mark.parametrize(
    "flag",
    [
        "auto_wire_bus",
        "enable_voice",
        "enable_self_enhancement",
        "enable_native_casimir",
        "enable_harmonic_buses",
    ],
)
def test_every_effectful_constructor_option_is_held(flag: str) -> None:
    with pytest.raises(RuntimeError, match="aureon_self_feedback_loop_hold"):
        AureonSelfFeedbackLoop(**{flag: True})


def test_tick_run_and_start_hold_before_vault_bus_coder_or_thread(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loop = AureonSelfFeedbackLoop()
    monkeypatch.setattr(
        loop.vault,
        "ingest",
        lambda *_args, **_kwargs: pytest.fail("HOLD must not ingest"),
    )
    monkeypatch.setattr(
        loop_module.threading,
        "Thread",
        lambda *_args, **_kwargs: pytest.fail("HOLD must not create thread"),
    )
    loop._enhancer = type(
        "GuardedEnhancer",
        (),
        {"enhance_once": lambda _self: pytest.fail("HOLD must not self-code")},
    )()
    loop._enhance_enabled = True

    for effect in (
        loop.tick,
        lambda: loop.run(cycles=1),
        loop.start,
    ):
        with pytest.raises(RuntimeError, match="aureon_self_feedback_loop_hold"):
            effect()

    assert loop._cycle == 0
    assert loop._running is False
    assert loop._thread is None
    assert loop.tick_history == []


def test_singleton_accessor_creates_only_an_inert_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(loop_module, "_loop_instance", None)

    first = loop_module.get_self_feedback_loop()
    second = loop_module.get_self_feedback_loop()

    assert first is second
    assert first.voice_engine is None
    assert first._enhance_enabled is False
    with pytest.raises(RuntimeError, match="aureon_self_feedback_loop_hold"):
        first.tick()
