"""The public voice package advertises every runtime release HOLD."""

from __future__ import annotations

import aureon.vault.voice as voice


def test_runtime_hold_constants_are_public_and_specific() -> None:
    names = [
        "WHOLE_KNOWLEDGE_VOICE_RELEASE_HOLD",
        "BUS_FLIGHT_CHECK_RELEASE_HOLD",
        "SYMBOLIC_LIFE_RELEASE_HOLD",
        "TEMPORAL_CAUSALITY_RELEASE_HOLD",
        "META_COGNITION_RELEASE_HOLD",
        "PERSONA_MINER_RELEASE_HOLD",
        "GOAL_SKILL_ALIGNER_RELEASE_HOLD",
        "LIFE_CONTEXT_RELEASE_HOLD",
        "HASH_RESONANCE_RELEASE_HOLD",
        "VAULT_FEED_AUDIT_RELEASE_HOLD",
    ]
    for name in names:
        assert name in voice.__all__
        value = getattr(voice, name)
        assert value.endswith("production_magic_star_release_unavailable")
        assert value.count(":") == 1
