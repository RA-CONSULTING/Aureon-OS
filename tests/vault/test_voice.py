#!/usr/bin/env python3
"""
Fail-closed voice-layer tests.

Prompt composition and choice logic remain pure. Provider calls, vault
mutation, bus publishing, and background execution remain on the production
Magic Star release HOLD.
"""

import os
import sys

import pytest

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.vault import (  # noqa: E402
    AureonSelfFeedbackLoop,
    AureonVault,
    ChoiceGate,
    SelfDialogueEngine,
    ThoughtStreamLoop,
    build_all_voices,
)


PASS = 0
FAIL = 0


def check(condition: bool, msg: str) -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [OK] {msg}")
    else:
        FAIL += 1
        print(f"  [!!] {msg}")


def test_voices_compose_pure_prompts_but_speaking_is_held():
    print("\n[1] Voice prompt composition is pure and speaking is held")
    vault = AureonVault()

    vault.love_amplitude = 0.3
    vault.gratitude_score = 0.5
    vault.last_casimir_force = 0.1
    vault.dominant_chakra = "foundation"
    vault.cortex_snapshot = {
        "delta": 0.3,
        "theta": 0.1,
        "alpha": 0.1,
        "beta": 0.1,
        "gamma": 0.1,
    }

    class BombAdapter:
        def prompt(self, *_args, **_kwargs):
            raise AssertionError("release-held voice must not call a provider")

    voices = build_all_voices(adapter=BombAdapter())
    prompts_1 = {
        name: "\n".join(voice._compose_prompt_lines(voice._extract_slice(vault)))
        for name, voice in voices.items()
    }
    assert prompts_1
    for name, voice in voices.items():
        with pytest.raises(RuntimeError, match="vault_voice_hold"):
            voice.speak(vault)
        check(len(prompts_1[name]) > 20, f"{name} pure prompt is substantial")

    vault.love_amplitude = 0.9
    vault.gratitude_score = 0.85
    vault.last_casimir_force = 5.2
    vault.dominant_chakra = "crown"
    vault.rally_active = True
    vault.cortex_snapshot = {
        "delta": 0.1,
        "theta": 0.1,
        "alpha": 0.4,
        "beta": 0.35,
        "gamma": 0.55,
    }

    prompts_2 = {
        name: "\n".join(voice._compose_prompt_lines(voice._extract_slice(vault)))
        for name, voice in voices.items()
    }

    different_count = sum(
        1
        for name in prompts_1
        if name in prompts_2 and prompts_1[name] != prompts_2[name]
    )
    check(
        different_count >= len(prompts_1) // 2,
        f"at least half the voices' prompts changed with state ({different_count}/{len(prompts_1)})",
    )

    vault.last_lambda_t = 0.87
    queen_prompt = "\n".join(
        voices["queen"]._compose_prompt_lines(voices["queen"]._extract_slice(vault))
    )
    check(
        "0.870" in queen_prompt or "+0.87" in queen_prompt,
        "Queen voice names Lambda(t) from state",
    )

    vault.last_casimir_force = 4.321
    miner_prompt = "\n".join(
        voices["miner"]._compose_prompt_lines(voices["miner"]._extract_slice(vault))
    )
    check(
        "4.321" in miner_prompt,
        "Miner voice names the Casimir drift value from state",
    )


def test_choice_gate():
    print("\n[2] ChoiceGate decides based on vault state")
    vault = AureonVault()
    gate = ChoiceGate(min_interval_s=0.0, urgency_threshold=0.3, background_rate=0.0)

    vault.love_amplitude = 0.2
    vault.gratitude_score = 0.5
    vault.last_casimir_force = 0.05
    vault.cortex_snapshot["gamma"] = 0.05
    quiet = gate.decide(vault)
    check(not quiet.should_speak, f"quiet vault -> silent (urgency={quiet.urgency:.2f})")

    vault.rally_active = True
    rally = gate.decide(vault)
    check(rally.should_speak, f"rally mode -> speak (urgency={rally.urgency:.2f})")
    check(rally.preferred_voice == "council", f"rally prefers council voice (got {rally.preferred_voice})")

    vault.rally_active = False
    vault.cortex_snapshot["gamma"] = 0.8
    gamma = gate.decide(vault)
    check(gamma.should_speak, f"gamma spike -> speak (urgency={gamma.urgency:.2f})")
    check(gamma.preferred_voice == "queen", f"gamma prefers queen (got {gamma.preferred_voice})")

    vault.cortex_snapshot["gamma"] = 0.05
    vault.last_casimir_force = 5.0
    drift = gate.decide(vault)
    check(drift.preferred_voice == "miner", f"drift prefers miner (got {drift.preferred_voice})")

    vault.last_casimir_force = 0.1
    vault.love_amplitude = 0.85
    love = gate.decide(vault)
    check(love.preferred_voice == "lover", f"high love prefers lover (got {love.preferred_voice})")

    gate_rl = ChoiceGate(min_interval_s=10.0, urgency_threshold=0.0, background_rate=1.0)
    vault.rally_active = True
    first = gate_rl.decide(vault)
    second = gate_rl.decide(vault)
    check(first.should_speak, "first call passes rate limit")
    check(not second.should_speak, "second call within interval is suppressed")


def test_self_dialogue_engine_is_inert_and_all_effect_entrypoints_hold():
    print("\n[3] SelfDialogueEngine is inert and effect entrypoints hold")
    vault = AureonVault()
    engine = SelfDialogueEngine(vault=vault)
    size_before = len(vault)
    assert engine.voices == {}
    assert engine._thought_bus is None
    for call in (
        engine.converse,
        lambda: engine.respond_to_human("hello"),
        lambda: engine.speak_as("queen"),
        engine._wire_thought_bus,
    ):
        with pytest.raises(RuntimeError, match="self_dialogue_hold"):
            call()
    assert len(vault) == size_before
    assert engine.history == []
    assert engine.get_status()["total_decisions"] == 0


def test_human_response_hold_precedes_provider_vault_and_bus_effects():
    print("\n[4] Human response HOLD precedes providers, vault writes, and bus writes")
    vault = AureonVault()

    class BombVoice:
        def speak(self, *_args, **_kwargs):
            raise AssertionError("provider path reached")

    class BombBus:
        def publish(self, *_args, **_kwargs):
            raise AssertionError("bus path reached")

    engine = SelfDialogueEngine(
        vault=vault,
        voices={"queen": BombVoice()},  # type: ignore[dict-item]
        thought_bus=BombBus(),
        adapter=object(),
    )
    before = len(vault)
    with pytest.raises(RuntimeError, match="self_dialogue_hold"):
        engine.respond_to_human("Do all of you hear me?", voice_name="queen")
    assert len(vault) == before
    assert engine.history == []


def test_thought_stream_loop_never_spawns_or_executes(monkeypatch: pytest.MonkeyPatch):
    print("\n[5] ThoughtStreamLoop never spawns or executes")
    vault = AureonVault()
    monkeypatch.setattr(
        "aureon.vault.voice.thought_stream_loop.threading.Thread",
        lambda *_args, **_kwargs: pytest.fail("release-held stream must not create a thread"),
    )
    stream = ThoughtStreamLoop(vault=vault, base_interval_s=0.001)
    assert stream.engine is None
    for call in (
        stream.start,
        stream._loop,
        stream._tick_once,
        lambda: stream.run_n_cycles(5, sleep_between=False),
    ):
        with pytest.raises(RuntimeError, match="thought_stream_hold"):
            call()
    status = stream.get_status()
    assert status.running is False
    assert status.cycles == 0
    assert status.utterances == 0


def test_self_feedback_loop_voice_integration():
    print("\n[6] Self-feedback voice integration remains on production HOLD")
    with pytest.raises(RuntimeError, match="aureon_self_feedback_loop_hold"):
        AureonSelfFeedbackLoop(base_interval_s=0.01, enable_voice=True)


def main():
    print("=" * 80)
    print("  VAULT VOICE TEST SUITE")
    print("=" * 80)

    test_voices_compose_pure_prompts_but_speaking_is_held()
    test_choice_gate()
    test_self_dialogue_engine_is_inert_and_all_effect_entrypoints_hold()
    test_human_response_hold_precedes_provider_vault_and_bus_effects()
    test_thought_stream_loop_never_spawns_or_executes(pytest.MonkeyPatch())
    test_self_feedback_loop_voice_integration()

    print()
    print("=" * 80)
    print(f"  RESULT: {PASS} passed, {FAIL} failed")
    print("=" * 80)
    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    main()
