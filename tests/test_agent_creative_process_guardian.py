from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous.aureon_agent_creative_process_guardian import (
    SCHEMA_VERSION,
    build_agent_creative_process_guardian,
    build_and_write_agent_creative_process_guardian,
)
from aureon.core.goal_execution_engine import GoalExecutionEngine


def _seed_repo(root: Path) -> None:
    for path in [
        "aureon/autonomous",
        "aureon/core",
        "aureon/exchanges",
        "aureon/vault/voice",
        "aureon/queen",
        "aureon/code_architect",
        "frontend/src/components/generated",
        "frontend/public",
        "docs/audits",
        "tests",
        "state",
        "Kings_Accounting_Suite/tools",
    ]:
        (root / path).mkdir(parents=True, exist_ok=True)
    for file_path in [
        "aureon/core/goal_execution_engine.py",
        "aureon/core/organism_contracts.py",
        "aureon/autonomous/aureon_goal_capability_map.py",
        "aureon/autonomous/aureon_local_task_queue.py",
        "aureon/autonomous/aureon_safe_code_control.py",
        "aureon/autonomous/aureon_coding_organism_bridge.py",
        "aureon/autonomous/aureon_coding_agent_skill_base.py",
        "aureon/autonomous/aureon_harmonic_affect_state.py",
        "aureon/autonomous/aureon_cognitive_trade_evidence.py",
        "aureon/autonomous/aureon_agent_creative_process_guardian.py",
        "aureon/exchanges/unified_market_trader.py",
        "aureon/queen/queen_code_architect.py",
        "aureon/vault/voice/whole_knowledge_voice.py",
        "frontend/src/components/generated/AureonCodingOrganismConsole.tsx",
        "frontend/src/App.tsx",
        "tests/test_agent_creative_process_guardian.py",
    ]:
        target = root / file_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# seeded\n", encoding="utf-8")


def _seed_mind_sources(root: Path, *, passed: bool = True) -> None:
    hnc = root / "state" / "aureon_hnc_cognitive_proof.json"
    hnc.parent.mkdir(parents=True, exist_ok=True)
    hnc.write_text(
        json.dumps(
            {
                "status": "passing" if passed else "blocked",
                "passed": passed,
                "master_formula": {"passed": passed, "score": 0.93},
                "auris_nodes": {"passed": passed, "coherence": 0.91},
            }
        ),
        encoding="utf-8",
    )
    (root / "state" / "aureon_expression_profile.json").write_text(
        json.dumps({"schema_version": "aureon-expression-profile-v1", "summary": {"source_count": 3}}),
        encoding="utf-8",
    )
    (root / "state" / "aureon_voice_last_run.json").write_text(
        json.dumps({"schema_version": "aureon-voice-v1", "status": "voice_ready"}),
        encoding="utf-8",
    )


def test_creative_process_guardian_binds_all_roles_to_mind_systems(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    _seed_mind_sources(tmp_path)

    report = build_agent_creative_process_guardian(
        root=tmp_path,
        goal="ensure all agents use metacognitive HNC Auris who what where when how act",
    )

    assert report["schema_version"] == SCHEMA_VERSION
    assert report["summary"]["role_count"] >= 30
    assert report["summary"]["metacognitive_ready"] is True
    assert report["summary"]["sensory_ready"] is True
    assert report["summary"]["hnc_auris_ready"] is True
    assert report["summary"]["sentient_style_ready"] is True
    assert report["summary"]["who_what_where_when_how_act_ready"] is True
    assert len(report["creative_process_loop"]) >= 6
    assert len(report["agent_creative_process_map"]) == report["summary"]["role_count"]
    first_role = report["agent_creative_process_map"][0]
    assert all(first_role[key] for key in ["who", "what", "where", "when", "how", "act"])
    assert first_role["mind_bindings"]["hnc_auris_systems"]
    assert first_role["mind_bindings"]["metacognitive_systems"]
    assert first_role["mind_bindings"]["sentience_boundary"].startswith("computational state")
    assert any(check["id"] == "hnc_auris_sources_passing" and check["ok"] for check in report["proof_checklist"])


def test_creative_process_guardian_writes_public_evidence(tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    _seed_mind_sources(tmp_path)

    report = build_and_write_agent_creative_process_guardian(root=tmp_path, goal="publish guardian evidence")
    raw = json.dumps(report, sort_keys=True)

    assert report["ok"] is True
    assert (tmp_path / "state" / "aureon_agent_creative_process_guardian_last_run.json").exists()
    assert (tmp_path / "docs" / "audits" / "aureon_agent_creative_process_guardian.json").exists()
    assert (tmp_path / "docs" / "audits" / "aureon_agent_creative_process_guardian.md").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_agent_creative_process_guardian.json").exists()
    assert "API_SECRET" not in raw
    assert "BEGIN PRIVATE" not in raw


def test_goal_engine_routes_creative_process_guardian(tmp_path: Path, monkeypatch) -> None:
    _seed_repo(tmp_path)
    _seed_mind_sources(tmp_path)
    monkeypatch.chdir(tmp_path)

    plan = GoalExecutionEngine().submit_goal(
        "Aureon entire organism must use metacognitive systems, sensory systems, "
        "HNC, Auris nodes, and sentient systems to establish who what where when how and act for all agents."
    )

    assert plan.status == "completed"
    assert [step.intent for step in plan.steps] == ["agent_creative_process_guardian"]
    assert plan.steps[0].validation_result["valid"] is True
