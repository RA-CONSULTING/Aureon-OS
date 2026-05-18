from __future__ import annotations

import json
import sys
from pathlib import Path

from aureon.autonomous.aureon_coding_organism_bridge import (
    get_coding_organism_status,
    submit_coding_prompt,
)
from aureon.core.goal_execution_engine import GoalExecutionEngine


def _fake_expression_context(*args, **kwargs):
    return {
        "schema_features": ["aureon_code_expression_context_v1"],
        "ok": True,
        "voice_summary": "Aureon routed the code goal through its own coding organism.",
        "runtime_summary": "coding organism bridge state translated",
        "redaction_applied": False,
    }


class FakeGoalEngine:
    def submit_goal(self, prompt: str):
        return {
            "goal_id": "goal-test",
            "original_text": prompt,
            "objective": prompt,
            "status": "completed",
            "success_criteria": "route, write proposal, test",
            "steps": [
                {
                    "step_id": "step-1",
                    "title": "Inspect and patch",
                    "intent": "coding_agent_skill_base",
                    "status": "completed",
                    "result": {
                        "target_files": ["aureon/demo.py"],
                        "files_written": ["aureon/demo.py"],
                    },
                    "validation_result": {"valid": True, "changed_files": ["aureon/demo.py"]},
                }
            ],
        }

    def get_status(self):
        return {"goals_submitted": 1, "goals_completed": 1}


class RaisingGoalEngine:
    def submit_goal(self, prompt: str):
        raise AssertionError("goal engine should not run before scope is locked")


def _write_hnc_fixture(root: Path, *, passed: bool = True) -> None:
    hnc = root / "state" / "aureon_hnc_cognitive_proof.json"
    hnc.parent.mkdir(parents=True, exist_ok=True)
    hnc.write_text(
        json.dumps(
            {
                "status": "passing" if passed else "blocked",
                "passed": passed,
                "master_formula": {"passed": passed, "score": 0.91},
                "auris_nodes": {"passed": passed, "coherence": 0.88},
            }
        ),
        encoding="utf-8",
    )
    harmonic = root / "docs" / "audits" / "aureon_harmonic_affect_state.json"
    harmonic.parent.mkdir(parents=True, exist_ok=True)
    harmonic.write_text(
        json.dumps(
            {
                "summary": {"hnc_coherence_score": 0.88, "safety_blocker_count": 0},
                "signals": {
                    "cognitive_trade_summary": {"runtime_stale": False},
                    "organism_summary": {"runtime_feed_status": "online"},
                },
            }
        ),
        encoding="utf-8",
    )


def test_incomplete_prompt_stops_at_scope_questions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    _write_hnc_fixture(tmp_path)

    result = submit_coding_prompt(
        "fix it",
        source="test",
        run_tests=False,
        root=tmp_path,
        goal_engine=RaisingGoalEngine(),
    )

    assert result["ok"] is False
    assert result["status"] == "coding_organism_needs_client_scope"
    assert result["summary"]["scope_status"] == "needs_client_scope"
    assert result["summary"]["scope_locked"] is False
    assert result["summary"]["goal_engine_routed"] is False
    assert result["summary"]["safe_code_proposal_created"] is False
    assert result["goal_route"]["skipped"] is True
    assert result["goal_route"]["skip_reason"] == "scope_of_works_not_locked"
    assert result["client_job"]["client_questions"]
    assert result["client_job"]["handover_status"]["client_visible_product"] is False
    assert result["finished_product_audit"]["status"] == "finished_product_scope_pending"
    assert any(stage["id"] == "scope_of_works" and not stage["ok"] for stage in result["work_journal"]["stages"])
    assert any(stage["id"] == "agent_team_assignment" and not stage["ok"] for stage in result["work_journal"]["stages"])


def test_scope_approval_turns_client_answers_into_route_context(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    _write_hnc_fixture(tmp_path)
    captured = {}

    class CapturingGoalEngine(FakeGoalEngine):
        def submit_goal(self, prompt: str):
            captured["prompt"] = prompt
            return super().submit_goal(prompt)

    result = submit_coding_prompt(
        "fix it",
        source="test",
        run_tests=False,
        root=tmp_path,
        goal_engine=CapturingGoalEngine(),
        scope_approved=True,
        base_job_id="coding-job-original",
        scope_answers={
            "goal": "Repair the coding organism scope gate.",
            "deliverables": "Backend evidence, UI panel, and tests.",
            "target_system": "aureon/autonomous/aureon_coding_organism_bridge.py",
            "constraints": "Preserve existing runtime behavior.",
            "acceptance": "Focused tests pass and no blocking snags remain.",
        },
    )

    assert result["ok"] is True
    assert result["summary"]["scope_locked"] is True
    assert result["summary"]["goal_engine_routed"] is True
    assert result["client_job"]["variation_order"]["created"] is True
    assert result["client_job"]["handover_status"]["client_visible_product"] is True
    assert "Client-approved scope answers" in captured["prompt"]
    assert result["finished_product_audit"]["ready_for_client"] is True
    assert result["finished_product_audit"]["handover_status"]["blocking_snag_count"] == 0


def test_submit_coding_prompt_writes_evidence_and_proposal(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    _write_hnc_fixture(tmp_path)

    result = submit_coding_prompt(
        "Aureon should inspect the repo and make the smallest safe code patch.",
        source="test",
        run_tests=False,
        root=tmp_path,
        goal_engine=FakeGoalEngine(),
    )

    assert result["ok"] is True
    assert result["schema_version"] == "aureon-coding-organism-bridge-v1"
    assert result["summary"]["goal_engine_routed"] is True
    assert result["summary"]["safe_code_proposal_created"] is True
    assert result["summary"]["target_file_count"] == 1
    assert result["summary"]["desktop_handoff_created"] is True
    assert result["summary"]["ready_to_run"] is True
    assert result["what"]["target_files"] == ["aureon/demo.py"]
    assert result["act"]["proposal_created"] is True
    assert result["act"]["desktop_handoff_created"] is True
    assert result["desktop_run_flow"]["status"] == "desktop_run_handoff_ready"
    assert result["desktop_run_flow"]["local_desktop_controller"]["dry_run"] is True
    assert result["desktop_run_flow"]["remote_vm_control"]["tool_count"] >= 20
    assert result["finished_product_audit"]["status"] == "finished_product_ready"
    assert result["summary"]["hnc_auris_drift_proof_ok"] is True
    assert "hnc_auris_drift_proof" in [item["id"] for item in result["client_job"]["proof_checklist"]]
    assert result["work_journal"]["schema_version"] == "aureon-coding-work-journal-v1"
    assert result["work_journal"]["status"] == "complete"
    assert result["work_journal"]["stage_count"] >= 8
    journal_ids = {stage["id"] for stage in result["work_journal"]["stages"]}
    assert {"prompt_received", "goal_routed", "code_proposal", "verification", "evidence_published", "finished_product"}.issubset(journal_ids)
    assert "GoalExecutionEngine.submit_goal" in result["how"]["authoring_path"]
    assert "SafeDesktopControl desktop/run handoff" in result["how"]["authoring_path"]

    state = tmp_path / "state" / "aureon_coding_organism_last_run.json"
    audit = tmp_path / "docs" / "audits" / "aureon_coding_organism_bridge.json"
    public = tmp_path / "frontend" / "public" / "aureon_coding_organism_bridge.json"
    md = tmp_path / "docs" / "audits" / "aureon_coding_organism_bridge.md"
    assert state.exists()
    assert audit.exists()
    assert public.exists()
    assert md.exists()

    persisted = json.loads(public.read_text(encoding="utf-8"))
    assert persisted["safe_code_status"]["pending_count"] == 1
    assert persisted["task"]["kind"] == "coding_organism_prompt"
    assert persisted["desktop_run_flow"]["desktop_handoff_action"]["status"] == "pending"


def test_submit_coding_prompt_can_run_focused_test_command(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    _write_hnc_fixture(tmp_path)

    result = submit_coding_prompt(
        "Aureon should run a test after routing this code goal.",
        source="test",
        run_tests=True,
        root=tmp_path,
        goal_engine=FakeGoalEngine(),
        test_commands=[[sys.executable, "-c", "print('coding bridge ok')"]],
    )

    assert result["ok"] is True
    assert result["tests"]["ok"] is True
    assert result["tests"]["command_count"] == 1
    assert "coding bridge ok" in result["tests"]["results"][0]["stdout_tail"]


def test_submit_coding_prompt_visual_artifact_prompt_finishes_cleanly(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "aureon").mkdir()
    _write_hnc_fixture(tmp_path)

    result = submit_coding_prompt(
        "drwaw me a image of a cat and open the file and show me it",
        source="test",
        run_tests=False,
        include_desktop=False,
        root=tmp_path,
        goal_engine=GoalExecutionEngine(),
        scope_approved=True,
        scope_answers={
            "goal": "Create a cat visual artifact from the dashboard prompt.",
            "deliverables": "A public SVG visual artifact, evidence JSON, and handover public URL.",
            "target_system": "frontend/public/aureon_visual_artifacts and frontend/public/aureon_visual_asset_request.json",
            "constraints": "No live trading, payment, filing, credential, or external mutation.",
            "acceptance": "Goal route completes, the SVG exists, and a public URL is written.",
        },
    )

    route_steps = result["goal_route"]["plan"]["steps"]
    assert result["ok"] is True
    assert result["summary"]["goal_route_clean"] is True
    assert result["finished_product_audit"]["ready_for_client"] is True
    assert [step["intent"] for step in route_steps] == ["visual_asset_request"]
    assert not {"open_app", "list_dir"}.intersection({step["intent"] for step in route_steps})
    assert any("aureon_visual_artifacts" in item for item in result["what"]["target_files"])
    assert (tmp_path / "frontend" / "public" / "aureon_visual_asset_request.json").exists()


def test_submit_coding_prompt_visual_artifact_wins_over_coding_ui_words(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "aureon").mkdir()
    _write_hnc_fixture(tmp_path)

    result = submit_coding_prompt(
        "Draw me an image of a dog and open it so I can see the finished artifact in the Aureon UI.",
        source="test",
        run_tests=False,
        include_desktop=False,
        root=tmp_path,
        goal_engine=GoalExecutionEngine(),
        scope_approved=True,
        scope_answers={
            "goal": "Draw me an image of a dog and open it so I can see the finished artifact in the Aureon UI.",
            "deliverables": "A public SVG visual artifact, evidence JSON, and handover public URL.",
            "target_system": "Aureon UI and frontend/public/aureon_visual_artifacts.",
            "constraints": "No live trading, payment, filing, credential, or external mutation.",
            "acceptance": "Goal route completes, the SVG exists, and the UI can show the public URL.",
        },
    )

    route_steps = result["goal_route"]["plan"]["steps"]
    assert result["summary"]["goal_route_clean"] is True
    assert [step["intent"] for step in route_steps] == ["visual_asset_request"]
    assert route_steps[0]["result"]["result"]["public_url"].endswith(".svg")


def test_submit_coding_prompt_video_artifact_survives_scope_wrapper(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "aureon").mkdir()
    _write_hnc_fixture(tmp_path)

    result = submit_coding_prompt(
        "Make a 1 second video of a dog running across the screen and show it in the Aureon UI. "
        "Deliver a playable public video artifact, evidence packet, proof checklist, and no blocking snags.",
        source="test",
        run_tests=False,
        include_desktop=False,
        root=tmp_path,
        goal_engine=GoalExecutionEngine(),
        scope_approved=True,
        scope_answers={
            "goal": "Make a 1 second video of a dog running across the screen and show it in the Aureon UI.",
            "deliverables": "A playable public video artifact, evidence JSON, and handover public URL.",
            "target_system": "Aureon UI, Aureon repository, coding organism bridge, and frontend/public/aureon_visual_artifacts.",
            "constraints": "No live trading, payment, filing, credential, or external mutation.",
            "acceptance": "Goal route completes, the MP4 exists, and the UI can show the public URL.",
        },
    )

    route_steps = result["goal_route"]["plan"]["steps"]
    payload = route_steps[0]["result"]["result"]
    assert result["summary"]["goal_route_clean"] is True
    assert [step["intent"] for step in route_steps] == ["visual_asset_request"]
    assert payload["asset_kind"] == "mp4"
    assert payload["duration_seconds"] == 1
    assert payload["public_url"].endswith(".webm")
    assert payload["preview_url"].endswith("_preview.html")
    assert Path(payload["asset_path"]).exists()


def test_submit_coding_prompt_game_uses_adaptive_forge_not_agentcore(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "aureon").mkdir()
    _write_hnc_fixture(tmp_path)

    result = submit_coding_prompt(
        "Make me a game where a man walks up to a glowing door and tell the end user how to play from the keyboard.",
        source="test",
        run_tests=False,
        include_desktop=False,
        root=tmp_path,
        goal_engine=GoalExecutionEngine(),
        scope_approved=True,
        scope_answers={
            "goal": "Make a playable local game where a man walks up to a glowing door.",
            "deliverables": "Playable HTML game, keyboard instructions, quality proof, and public preview URL.",
            "target_system": "frontend/public/aureon_generated_apps and Aureon coding cockpit artifact preview.",
            "constraints": "Local-only, no live trading, payment, filing, credential, or destructive OS action.",
            "acceptance": "A browser-openable HTML artifact exists, keyboard controls are visible, and no blocking snags remain.",
        },
    )

    route_steps = result["goal_route"]["plan"]["steps"]
    payload = route_steps[0]["result"]["result"]
    manifest = payload["artifact_manifest"]
    assert result["ok"] is True
    assert result["summary"]["goal_route_clean"] is True
    assert [step["intent"] for step in route_steps] == ["capability_forge"]
    assert not {"create_dir", "write_file", "list_dir", "read_file"}.intersection(
        {step["intent"] for step in route_steps}
    )
    assert payload["summary"]["adaptive_skill_created"] is True
    assert payload["adaptive_skill_evidence"]["name"] == "local_html_game_forge"
    assert payload["uniqueness_contract"]["reuse_allowed_for_handover"] is False
    assert result["summary"]["fresh_project_per_request"] is True
    assert result["summary"]["capability_forge_build_id"] == payload["build_id"]
    assert manifest["kind"] == "html_game"
    assert manifest["public_url"].endswith(".html")
    assert result["summary"]["artifact_public_url"] == manifest["public_url"]
    assert manifest["build_id"] in manifest["public_url"]
    assert Path(manifest["asset_path"]).exists()
    assert "aureon_generated_apps" in manifest["public_url"]


def test_submit_coding_prompt_barcode_tool_uses_domain_specific_adaptive_skill(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "aureon").mkdir()
    _write_hnc_fixture(tmp_path)

    result = submit_coding_prompt(
        "Build a local barcode label generator tool for the warehouse team, with run instructions and proof.",
        source="test",
        run_tests=False,
        include_desktop=False,
        root=tmp_path,
        goal_engine=RaisingGoalEngine(),
        scope_approved=True,
        scope_answers={
            "goal": "Build a local barcode label generator tool for the warehouse team.",
            "deliverables": "Adaptive local skill capsule, browser preview, runbook, Python run contract, and proof.",
            "target_system": "frontend/public/aureon_adaptive_skills and Aureon coding cockpit artifact preview.",
            "constraints": "Local-only, no live trading, payment, filing, credential, or destructive OS action.",
            "acceptance": "The skill capsule files exist, preview URL works, and no blocking snags remain.",
        },
    )

    route_steps = result["goal_route"]["plan"]["steps"]
    payload = route_steps[0]["result"]["result"]
    manifest = payload["artifact_manifest"]
    assert result["ok"] is True
    assert [step["intent"] for step in route_steps] == ["capability_forge"]
    assert payload["adaptive_skill_evidence"]["name"] == "barcode_label_generator_skill"
    assert manifest["kind"] == "barcode_label_generator"
    assert "aureon_adaptive_skills" in manifest["public_url"]
    assert Path(manifest["asset_path"]).exists()
    assert Path(manifest["tool_path"]).exists()


def test_submit_coding_prompt_full_stack_routes_to_agent_forge(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "aureon").mkdir()
    _write_hnc_fixture(tmp_path)

    result = submit_coding_prompt(
        "Build a full-stack client task tracker with backend API, frontend dashboard, local data store, and tests.",
        source="test",
        run_tests=False,
        include_desktop=False,
        root=tmp_path,
        goal_engine=RaisingGoalEngine(),
        scope_approved=True,
        scope_answers={
            "goal": "Build a full-stack local client task tracker.",
            "deliverables": "Backend API, frontend UI, local data store, tests, runbook, and preview URL.",
            "target_system": "frontend/public/aureon_full_stack_apps and Aureon coding cockpit artifact preview.",
            "constraints": "Local-only, no live trading, payment, filing, credential, or destructive OS action.",
            "acceptance": "Backend/frontend/test files exist, API contract validates, and handover is quality-gated.",
        },
    )

    route_steps = result["goal_route"]["plan"]["steps"]
    payload = route_steps[0]["result"]["result"]
    manifest = payload["artifact_manifest"]

    assert result["ok"] is True
    assert [step["intent"] for step in route_steps] == ["capability_forge"]
    assert payload["task_family"] == "full_stack"
    assert payload["adaptive_skill_evidence"]["name"] == "local_full_stack_system_forge"
    assert manifest["kind"] == "full_stack_system"
    assert "aureon_full_stack_apps" in manifest["public_url"]
    assert Path(manifest["backend_path"]).exists()
    assert Path(manifest["frontend_path"]).exists()
    assert Path(manifest["test_path"]).exists()
    assert payload["full_stack_system_report"]["validation"]["status"] == "contract_validated"


def test_coding_organism_status_reads_last_run_and_queues(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    _write_hnc_fixture(tmp_path)
    submit_coding_prompt(
        "Aureon should publish coding evidence.",
        source="test",
        run_tests=False,
        root=tmp_path,
        goal_engine=FakeGoalEngine(),
    )

    status = get_coding_organism_status(root=tmp_path)

    assert status["available"] is True
    assert status["status"] == "coding_organism_ready"
    assert status["last_run"]["summary"]["safe_code_proposal_created"] is True
    assert status["last_run"]["summary"]["desktop_handoff_created"] is True
    assert status["safe_code_status"]["pending_count"] == 1
    assert status["task_queue_status"]["recent_completed"]


def test_submit_coding_prompt_can_skip_desktop_handoff(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    _write_hnc_fixture(tmp_path)

    result = submit_coding_prompt(
        "Aureon should route without desktop handoff for this audit-only run.",
        source="test",
        run_tests=False,
        include_desktop=False,
        root=tmp_path,
        goal_engine=FakeGoalEngine(),
    )

    assert result["ok"] is True
    assert result["summary"]["desktop_handoff_created"] is False
    assert result["desktop_run_flow"]["status"] == "desktop_run_handoff_skipped"


def test_hnc_auris_drift_proof_blocks_finished_handover_when_failing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    _write_hnc_fixture(tmp_path, passed=False)

    result = submit_coding_prompt(
        "Aureon should inspect the repo and make the smallest safe code patch.",
        source="test",
        run_tests=False,
        root=tmp_path,
        goal_engine=FakeGoalEngine(),
    )

    assert result["ok"] is False
    assert result["summary"]["hnc_auris_drift_proof_ok"] is False
    assert result["summary"]["blocking_snag_count"] >= 1
    assert result["finished_product_audit"]["ready_for_client"] is False
    proof = {item["id"]: item for item in result["client_job"]["proof_checklist"]}
    assert proof["hnc_auris_drift_proof"]["ok"] is False
    assert "hnc_cognitive_proof_not_passing" in result["hnc_auris_drift_proof"]["blockers"]


def test_goal_engine_routes_coding_work_journal_ui(tmp_path: Path, monkeypatch) -> None:
    files = {
        "aureon/autonomous/aureon_coding_organism_bridge.py": "_build_work_journal\n'aureon-coding-work-journal-v1'\n",
        "frontend/src/components/generated/AureonCodingOrganismConsole.tsx": (
            "AureonCodingOrganismConsole\n"
            "Scope Of Works\n"
            "Work Journal: Prompt To Finished Files\n"
            "journalStages\n"
            "proofChecklist\n"
            "snaggingList\n"
            "HNC/Auris drift proof\n"
            "compactEvidence\n"
            "Local hub endpoint\n"
            "Prompt lane\n"
            "Send To Aureon\n"
            "Desktop And Remote Run Handoff\n"
        ),
        "tests/test_aureon_coding_organism_bridge.py": "work_journal\n'aureon-coding-work-journal-v1'\n",
    }
    for rel_path, content in files.items():
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    plan = GoalExecutionEngine().submit_goal(
        "Aureon must show its work from prompt to finished files in the UI with goal steps, "
        "code proposal, tests, desktop handoff, and completion report."
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == "coding_work_journal_ui"
    assert plan.steps[0].validation_result["valid"] is True


def test_goal_engine_routes_coding_organism_prompt_lane_to_journal_ui(tmp_path: Path, monkeypatch) -> None:
    files = {
        "aureon/autonomous/aureon_coding_organism_bridge.py": "_build_work_journal\n'aureon-coding-work-journal-v1'\n",
        "frontend/src/components/generated/AureonCodingOrganismConsole.tsx": (
            "AureonCodingOrganismConsole\n"
            "Scope Of Works\n"
            "Work Journal: Prompt To Finished Files\n"
            "journalStages\n"
            "proofChecklist\n"
            "snaggingList\n"
            "HNC/Auris drift proof\n"
            "compactEvidence\n"
            "Local hub endpoint\n"
            "Prompt lane\n"
            "Send To Aureon\n"
            "Desktop And Remote Run Handoff\n"
        ),
        "tests/test_aureon_coding_organism_bridge.py": "work_journal\n'aureon-coding-work-journal-v1'\n",
    }
    for rel_path, content in files.items():
        path = tmp_path / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    plan = GoalExecutionEngine().submit_goal(
        "Aureon must improve its coding organism console prompt lane so the UI shows "
        "the local hub endpoint, Send To Aureon, tests, desktop handoff, and files."
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == "coding_work_journal_ui"
    assert plan.steps[0].validation_result["valid"] is True
