from __future__ import annotations

import argparse
import re
from pathlib import Path

import pytest

from aureon.core.goal_execution_engine import GoalExecutionEngine
from aureon.vault.voice import document_artifact_skill as artifact_module
from aureon.vault.voice.document_artifact_skill import (
    DOCUMENT_ARTIFACT_RELEASE_HOLD,
    AureonDocumentArtifactSkill,
    BhoyVoiceProfile,
    count_words,
    extract_target_words,
    extract_topic,
    preflight,
)


class TrapComposer:
    def __init__(self) -> None:
        self.calls = 0

    def compose(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("composer must not run while release is held")


class TrapBus:
    def __init__(self) -> None:
        self.calls = 0

    def publish(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("thought bus must not publish while release is held")


class TrapRuntime:
    def __init__(self) -> None:
        self.shutdown_calls = 0

    def shutdown(self) -> None:
        self.shutdown_calls += 1
        raise AssertionError("runtime must not shut down through a held surface")


def assert_release_hold(callable_) -> None:
    with pytest.raises(RuntimeError) as exc_info:
        callable_()
    assert str(exc_info.value) == DOCUMENT_ARTIFACT_RELEASE_HOLD


def test_extract_prompt_shape():
    prompt = "Write a 4000 word essay on the meaning of life and PDF it to the Desktop"

    assert extract_target_words(prompt) == 4000
    assert extract_topic(prompt) == "the meaning of life"


def test_goal_engine_routes_essay_pdf_to_document_artifact_intent():
    engine = GoalExecutionEngine()

    plan = engine._decompose_goal(
        "Write a 4000 word essay on the meaning of life and PDF it to the Desktop"
    )

    assert len(plan.steps) == 1
    assert plan.steps[0].intent == "compose_document_pdf"
    assert plan.steps[0].params["target_words"] == 4000
    assert plan.steps[0].params["topic"] == "the meaning of life"
    assert plan.steps[0].params["output_dir"] == "desktop"


def test_construction_and_preflight_are_inert_and_inspectable(monkeypatch):
    def forbidden_path_effect(*args, **kwargs):
        raise AssertionError("construction must not inspect or resolve the filesystem")

    monkeypatch.setattr(Path, "resolve", forbidden_path_effect)
    monkeypatch.setattr(Path, "exists", forbidden_path_effect)
    monkeypatch.setattr(Path, "mkdir", forbidden_path_effect)
    monkeypatch.setattr(Path, "write_text", forbidden_path_effect)

    composer = TrapComposer()
    bus = TrapBus()
    skill = AureonDocumentArtifactSkill(
        composer=composer,
        thought_bus=bus,
        output_dir=Path("lexical-output"),
        evidence_dir=Path("lexical-evidence"),
    )
    default_skill = AureonDocumentArtifactSkill()

    assert skill.output_dir == Path("lexical-output")
    assert skill.evidence_dir == Path("lexical-evidence")
    assert skill.composer is composer
    assert skill.thought_bus is bus
    assert composer.calls == 0
    assert bus.calls == 0
    assert default_skill.output_dir.name == "Desktop"
    assert default_skill.evidence_dir.name == "state"
    assert preflight() == {
        "status": "HOLD",
        "reason_code": "production_magic_star_release_unavailable",
        "production_ready": False,
        "effect_enabled": False,
    }
    assert artifact_module.repo_root() == Path(artifact_module.__file__).parents[3]


def test_pure_markdown_formatting_remains_available_without_filesystem_effects(monkeypatch):
    def forbidden_path_effect(*args, **kwargs):
        raise AssertionError("pure formatting must not touch the filesystem")

    monkeypatch.setattr(Path, "resolve", forbidden_path_effect)
    monkeypatch.setattr(Path, "exists", forbidden_path_effect)
    monkeypatch.setattr(Path, "mkdir", forbidden_path_effect)
    monkeypatch.setattr(Path, "write_text", forbidden_path_effect)

    skill = AureonDocumentArtifactSkill(
        output_dir=Path("lexical-output"),
        evidence_dir=Path("lexical-evidence"),
    )
    markdown = skill._build_markdown(
        title="Aureon Essay: Meaning",
        prompt="Write an essay on meaning",
        topic="meaning",
        target_words=900,
        live_reflection="Memory and tools are available for careful reflection.",
        live_state={"level": "awake", "n_alive": 9, "n_cards": 4, "n_tools": 3},
        voice_profile=BhoyVoiceProfile(),
    )

    assert count_words(markdown) > 500
    assert "## Final Synthesis" in markdown
    assert markdown.rfind("## Final Synthesis") > markdown.rfind("## Conclusion")
    assert "dominant_band" not in markdown
    assert "coherence_gamma" not in markdown
    paragraphs = [
        part.strip()
        for part in markdown.split("\n\n")
        if part.strip() and not part.startswith("#") and count_words(part) > 25
    ]
    assert len(paragraphs) == len(set(paragraphs))
    assert all(re.findall(r"\w+", paragraph) for paragraph in paragraphs)


def test_compose_holds_before_resolve_create_write_render_or_publish(tmp_path, monkeypatch):
    composer = TrapComposer()
    bus = TrapBus()
    skill = AureonDocumentArtifactSkill(
        composer=composer,
        thought_bus=bus,
        output_dir=tmp_path / "output",
        evidence_dir=tmp_path / "evidence",
    )

    def forbidden_path_effect(*args, **kwargs):
        raise AssertionError("compose must hold before filesystem effects")

    monkeypatch.setattr(Path, "resolve", forbidden_path_effect)
    monkeypatch.setattr(Path, "mkdir", forbidden_path_effect)
    monkeypatch.setattr(Path, "write_text", forbidden_path_effect)
    monkeypatch.setattr(skill, "_render_pdf", forbidden_path_effect)
    monkeypatch.setattr(skill, "_publish", forbidden_path_effect)

    assert_release_hold(
        lambda: skill.compose_pdf(
            prompt="Write a 900 word essay and PDF it",
            output_dir=tmp_path / "override",
        )
    )

    assert composer.calls == 0
    assert bus.calls == 0
    assert list(tmp_path.iterdir()) == []


def test_all_direct_runtime_helpers_hold_before_their_effects(monkeypatch):
    composer = TrapComposer()
    bus = TrapBus()
    runtime = TrapRuntime()
    skill = AureonDocumentArtifactSkill(
        composer=composer,
        thought_bus=bus,
        output_dir=Path("lexical-output"),
        evidence_dir=Path("lexical-evidence"),
    )
    skill._owned_runtime = runtime

    def forbidden(*args, **kwargs):
        raise AssertionError("effect helper crossed the release hold")

    monkeypatch.setattr(Path, "resolve", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)
    monkeypatch.setattr(artifact_module, "ZipFile", forbidden)

    calls = [
        lambda: AureonDocumentArtifactSkill.with_integrated_cognitive_system(
            output_dir=Path("ics-output")
        ),
        skill.close,
        lambda: skill._compose_live_reflection(topic="meaning", target_words=300),
        skill._fallback_composer,
        lambda: skill._render_pdf(Path("artifact.pdf"), "Title", "# Title"),
        lambda: skill._publish("document.completed", {"ok": True}),
        lambda: artifact_module.load_bhoy_voice_profile(Path("bhoy-root")),
        lambda: artifact_module._extract_docx_paragraphs(
            Path("source.docx"), max_paragraphs=10
        ),
    ]
    for call in calls:
        assert_release_hold(call)

    assert composer.calls == 0
    assert bus.calls == 0
    assert runtime.shutdown_calls == 0
    assert skill._owned_runtime is runtime


def test_cli_holds_before_argument_parsing_or_output_path_handling(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("CLI crossed the release hold")

    monkeypatch.setattr(argparse, "ArgumentParser", forbidden)
    monkeypatch.setattr(Path, "resolve", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(Path, "write_text", forbidden)

    assert_release_hold(
        lambda: artifact_module.main(
            [
                "--prompt",
                "write an essay",
                "--output-dir",
                "must-not-be-resolved",
            ]
        )
    )
