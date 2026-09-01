"""Control-boundary provenance remains pure while generation is held."""

from __future__ import annotations

import pytest

from aureon.vault.voice.whole_knowledge_voice import (
    ExpressionProfile,
    ExpressionSource,
    VoiceArtifact,
    build_expression_profile,
    compose_voice_artifact,
)


def _assert_control_boundary(value) -> None:
    assert value.content_class == "generated_voice_control_content"
    assert value.operational_eligible is False
    assert value.accounting_eligible is False
    assert value.learning_eligible is False
    assert value.provider_verified is False
    assert value.requires_operator_review is True
    payload = value.to_dict()
    assert payload["forbidden_evidence_uses"] == ["action", "accounting", "learning"]


def test_control_content_dataclasses_remain_bounded_without_generation() -> None:
    source = ExpressionSource("operator_note.txt", "txt", ["human_voice"], 12)
    profile = ExpressionProfile(source_count=1, sources=[source])
    artifact = VoiceArtifact(goal="explain", text="held")
    _assert_control_boundary(source)
    _assert_control_boundary(profile)
    _assert_control_boundary(artifact)


def test_generation_entrypoints_are_release_held() -> None:
    with pytest.raises(RuntimeError, match="whole_knowledge_voice_hold"):
        build_expression_profile()
    with pytest.raises(RuntimeError, match="whole_knowledge_voice_hold"):
        compose_voice_artifact("explain")
