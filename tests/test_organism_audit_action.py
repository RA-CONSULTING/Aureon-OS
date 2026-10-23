"""Metacognition and self-repair act on repeated failed self-changes."""

from __future__ import annotations

import json

import pytest


@pytest.fixture
def circulation(tmp_path, monkeypatch):
    from aureon.core.organism_circulation import start_organism_circulation, stop_organism_circulation

    monkeypatch.setenv("AUREON_ORGANISM_STATE", str(tmp_path / "organism-state"))
    monkeypatch.setenv("AUREON_ORGANISM_HTTP_PORT", "0")
    monkeypatch.setenv("AUREON_AUTONOMY_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    stop_organism_circulation()
    started = start_organism_circulation(port=0)
    assert started["started"] is True
    try:
        yield tmp_path
    finally:
        stop_organism_circulation()


def test_repeated_failed_self_change_raises_concern_and_deprioritises(circulation, tmp_path) -> None:
    from aureon.autonomous.autonomy_mode import audit_event
    from aureon.core.organism_circulation import (
        deprioritised_targets,
        metacognition_audit_state,
        repair_priority,
    )

    paths = ["aureon/core/healthy.py", "aureon/core/shaky.py", "aureon/core/other.py"]
    before = metacognition_audit_state()
    assert before["audit_concern"] is None
    assert before["audit_confidence"] == 1.0
    assert before["failed_self_changes"] == 0
    assert repair_priority(paths) == paths
    assert deprioritised_targets() == []

    audit_event(
        "self_patch_kept",
        tmp_path,
        path="aureon/core/shaky.py",
        reason="tests_failed",
        rolled_back=False,
    )
    once = metacognition_audit_state()
    assert once["audit_concern"] is None
    assert once["audit_confidence"] == 1.0
    assert once["failed_self_changes"] == 1
    assert deprioritised_targets() == []
    assert repair_priority(paths) == paths

    audit_event(
        "self_patch_kept",
        tmp_path,
        path="aureon/core/shaky.py",
        reason="tests_failed",
        rolled_back=False,
    )
    twice = metacognition_audit_state()
    assert twice["audit_concern"] == "repeated failed self-change on aureon/core/shaky.py"
    assert twice["audit_confidence"] < 1.0
    assert twice["failed_self_changes"] == 2
    assert deprioritised_targets() == ["aureon/core/shaky.py"]
    assert repair_priority(paths) == [
        "aureon/core/healthy.py",
        "aureon/core/other.py",
        "aureon/core/shaky.py",
    ]
    text = (tmp_path / "state" / "autonomy_audit.jsonl").read_text(encoding="utf-8")
    assert "tests_failed" in text
    assert json.loads(text.splitlines()[-1])["rolled_back"] is False


def test_credential_path_is_not_a_repair_target(circulation, tmp_path) -> None:
    from aureon.autonomous.autonomy_mode import audit_event
    from aureon.core.organism_circulation import deprioritised_targets, metacognition_audit_state

    for _ in range(2):
        audit_event("write_refused", tmp_path, path=".env", reason="write_refused", api_secret="super-secret-value")
    state = metacognition_audit_state()
    assert state["audit_concern"] is None
    assert state["failed_self_changes"] == 0
    assert deprioritised_targets() == []
    text = (tmp_path / "state" / "autonomy_audit.jsonl").read_text(encoding="utf-8")
    assert "super-secret-value" not in text
    assert "api_secret" not in text


def test_audit_subscribers_follow_a_replaced_thought_bus(circulation, tmp_path) -> None:
    import aureon.core.aureon_thought_bus as thought_bus
    from aureon.autonomous.autonomy_mode import audit_event
    from aureon.core.aureon_thought_bus import get_thought_bus
    from aureon.core.organism_circulation import consumed_audits, start_organism_circulation

    thought_bus._thought_bus_instance = None
    replacement = get_thought_bus()
    start_organism_circulation(port=0)
    audit_event(
        "repair_reverted",
        tmp_path,
        path="aureon/core/shaky.py",
        reason="retest_failed_change_reverted",
    )
    assert get_thought_bus() is replacement
    consumed = {item["event"] for item in consumed_audits("self_repair")}
    assert "repair_reverted" in consumed
    consumed_meta = {item["event"] for item in consumed_audits("metacognition")}
    assert "repair_reverted" in consumed_meta
