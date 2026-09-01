"""Downstream code-expression handling of the whole-knowledge HOLD."""

from __future__ import annotations

from pathlib import Path

from aureon.code_architect import Skill, SkillWriter, build_code_expression_context


def test_code_expression_context_reports_voice_hold_without_writing(tmp_path: Path) -> None:
    context = build_code_expression_context(
        "write a safer dashboard adapter",
        evidence={"runtime_state": {"action": "WRITE_CODE"}},
        evidence_dir=tmp_path,
        publish=False,
    )
    assert context["ok"] is False
    assert context["evidence_path"] == ""
    assert any("whole_knowledge_voice_hold" in warning for warning in context["warnings"])
    assert list(tmp_path.iterdir()) == []


def test_skill_writer_carries_held_expression_context_without_publish(tmp_path: Path) -> None:
    writer = SkillWriter(
        expression_evidence_dir=str(tmp_path),
        expression_publish=False,
    )
    proposal = writer.propose_atomic("screenshot", name="capture_screen")
    skill = Skill.from_proposal(proposal)
    assert proposal.expression_context["ok"] is False
    assert any(
        "whole_knowledge_voice_hold" in warning
        for warning in proposal.expression_context["warnings"]
    )
    assert skill.expression_context == proposal.expression_context
    assert list(tmp_path.iterdir()) == []
