from __future__ import annotations

import re
from collections import Counter
from types import SimpleNamespace

import pytest

from aureon.core.goal_execution_engine import GoalExecutionEngine
from aureon.vault.voice.document_artifact_skill import (
    AureonDocumentArtifactSkill,
    count_words,
    extract_target_words,
    extract_topic,
)


class FakeComposer:
    def compose(self, topic: str = "", target_words: int = 300):
        text = (
            f"Aureon is reflecting on {topic}. "
            "It observes, acts, verifies, remembers, and asks the next question. "
        ) * 20
        return SimpleNamespace(
            text=text,
            word_count=count_words(text),
            state_snapshot={
                "gamma": "0.82",
                "psi": "0.71",
                "action": "EXECUTE",
                "n_alive": 9,
            },
        )


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


def test_document_artifact_skill_writes_markdown_pdf_and_evidence(tmp_path):
    # The PDF stage renders through reportlab; without it the skill honestly
    # reports ok=False ("PDF renderer unavailable"), which is the contract —
    # not a bug to paper over. Test the full render only when the dep exists.
    pytest.importorskip("reportlab")
    skill = AureonDocumentArtifactSkill(
        composer=FakeComposer(),
        output_dir=tmp_path,
        evidence_dir=tmp_path,
    )

    result = skill.compose_pdf(
        prompt="Write a 900 word essay on the meaning of life and PDF it",
        topic="the meaning of life",
        target_words=900,
    )

    assert result.ok
    assert result.word_count >= 810
    assert result.pdf_rendered
    assert result.schema_features == [
        "aureon_document_artifact_pdf_v1",
        "humanized_bhoys_voice_v1",
        "whole_knowledge_voice_core_v1",
    ]
    assert result.markdown_path.endswith(".md")
    assert result.pdf_path.endswith(".pdf")
    assert result.evidence_path.endswith(".json")

    # Paths are absolute or rooted from the temporary output directory.
    from pathlib import Path

    assert Path(result.markdown_path).exists()
    assert Path(result.pdf_path).exists()
    assert Path(result.evidence_path).exists()
    evidence = Path(result.evidence_path).read_text(encoding="utf-8")
    assert "whole_knowledge_voice" in evidence
    assert "expression_profile" in evidence

    markdown = Path(result.markdown_path).read_text(encoding="utf-8")
    assert "through the goal/document artifact system" in markdown
    assert "dominant_band" not in markdown
    assert "coherence_gamma" not in markdown
    assert "measured reading" not in markdown
    assert "out of 9 agree" not in markdown
    assert "â" not in markdown
    assert "kitchen-table" in markdown or "Bhoy voice profile" in markdown
    assert markdown.rfind("## Final Synthesis") > markdown.rfind("## Conclusion")
    assert "A human reader does not need a dump" not in markdown

    paragraphs = [
        part.strip()
        for part in markdown.split("\n\n")
        if part.strip() and not part.startswith("#") and count_words(part) > 25
    ]
    assert len(paragraphs) == len(set(paragraphs))

    openings = Counter(
        " ".join(re.findall(r"\b[\w']+\b", paragraph.lower())[:5])
        for paragraph in paragraphs
        if count_words(paragraph) > 25
    )
    assert openings
    assert openings.most_common(1)[0][1] <= 3
    assert markdown.count("The system part of this") == 0
    assert markdown.count("Through a Bhoy's Eyes gives") == 0
