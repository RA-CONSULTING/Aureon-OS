from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous.aureon_artifact_quality_gate import build_artifact_quality_report
from aureon.autonomous.aureon_capability_forge import build_and_write_capability_forge, classify_task_family
from aureon.core.goal_execution_engine import GoalExecutionEngine


def _fake_expression_context(*args, **kwargs):
    return {
        "schema_features": ["aureon_code_expression_context_v1"],
        "ok": True,
        "voice_summary": "Aureon local capability forge recorded safe code evidence.",
        "runtime_summary": "capability forge state translated",
        "redaction_applied": False,
    }


def test_capability_forge_classifies_core_task_families() -> None:
    assert classify_task_family("make a 10 second video of a dog")["primary_family"] == "video"
    assert classify_task_family("draw a logo and graphic design")["task_family"] == "image_graphic_design"
    assert classify_task_family("write code for a Python module and run tests")["task_family"] == "coding"
    assert classify_task_family("build a React UI dashboard panel")["primary_family"] == "ui"
    assert classify_task_family("write a PDF document report")["task_family"] == "document"
    assert classify_task_family("open the browser and run a Playwright smoke test")["primary_family"] == "browser_qa"


def test_capability_forge_local_only_reference_patterns_and_no_external_calls(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )

    report = build_and_write_capability_forge(
        "Aureon must research how AI systems do coding jobs, build a local coding forge, "
        "publish proof, and keep cloud providers reference-only.",
        root=tmp_path,
    )

    assert report["provider_policy"] == "local_only_v1"
    assert report["external_api_calls"] == []
    assert report["summary"]["external_api_call_count"] == 0
    assert report["summary"]["safe_code_route_recorded"] is True
    assert report["approval_state"]["state"] == "pending_user_review_after_apply"
    assert all(item["external_api_call_allowed"] is False for item in report["reference_patterns"])
    assert (tmp_path / "frontend" / "public" / "aureon_capability_forge.json").exists()


def test_capability_forge_video_job_produces_quality_gated_public_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "aureon").mkdir()

    report = build_and_write_capability_forge(
        "Make a 1 second video of a dog running across the screen, show it in the UI, "
        "and do not hand it over unless the browser-playable preview passes.",
        root=tmp_path,
    )

    quality = report["artifact_quality_report"]
    manifest = report["artifact_manifest"]
    assert report["task_family"] == "video"
    assert report["handover_ready"] is True
    assert quality["handover_ready"] is True
    assert quality["score"] >= 0.8
    assert manifest["public_url"].endswith((".webm", ".gif"))
    assert manifest["preview_url"].endswith("_preview.html")
    assert Path(manifest["asset_path"]).exists()
    assert Path(manifest["preview_path"]).exists()
    assert (tmp_path / "frontend" / "public" / "aureon_artifact_quality_report.json").exists()


def test_artifact_quality_gate_blocks_unplayable_video_without_preview(tmp_path: Path) -> None:
    bad_video = tmp_path / "frontend" / "public" / "aureon_visual_artifacts" / "bad.mp4"
    bad_video.parent.mkdir(parents=True, exist_ok=True)
    bad_video.write_bytes(b"not a playable video")

    report = build_artifact_quality_report(
        {
            "kind": "video",
            "asset_path": str(bad_video),
            "source_asset_path": str(bad_video),
            "public_url": "/aureon_visual_artifacts/bad.mp4",
            "preview_url": "",
            "preview_path": "",
            "duration_seconds": 10,
        },
        prompt="make a 10 second video",
        task_family="video",
        root=tmp_path,
    )

    assert report["handover_ready"] is False
    assert report["status"] == "artifact_quality_blocked"
    snag_ids = {item["id"] for item in report["snags"]}
    assert "artifact_playable_or_renderable_format" in snag_ids
    assert "artifact_preview_page_present" in snag_ids


def test_goal_engine_routes_capability_forge_request(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    monkeypatch.chdir(tmp_path)
    (tmp_path / "aureon").mkdir()

    plan = GoalExecutionEngine().submit_goal(
        "Aureon must build the local capability forge quality gate so it does not send half baked cake to the client."
    )

    assert plan.status == "completed"
    assert [step.intent for step in plan.steps] == ["capability_forge"]
    assert plan.steps[0].validation_result["valid"] is True
    payload = plan.steps[0].result["result"]
    assert payload["schema_version"] == "aureon-local-capability-forge-v1"
    assert payload["provider_policy"] == "local_only_v1"
    assert payload["approval_state"]["state"] == "pending_user_review_after_apply"


def test_capability_forge_public_json_has_required_report_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )
    report = build_and_write_capability_forge("Build a UI panel and browser smoke proof for the cockpit.", root=tmp_path)
    public = json.loads((tmp_path / "frontend" / "public" / "aureon_capability_forge.json").read_text(encoding="utf-8"))

    for key in (
        "task_family",
        "director_brief",
        "recruited_crew",
        "local_tools_used",
        "reference_patterns",
        "artifact_manifest",
        "artifact_quality_report",
        "regeneration_attempts",
        "applied_change_evidence",
        "approval_state",
        "handover_ready",
    ):
        assert key in public
        assert key in report


def test_capability_forge_interactive_game_builds_local_playable_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )

    report = build_and_write_capability_forge(
        "Make me a game where a man walks up to a glowing door and tell the end user how to play from the keyboard.",
        root=tmp_path,
    )

    manifest = report["artifact_manifest"]
    quality = report["artifact_quality_report"]
    assert report["handover_ready"] is True
    assert report["summary"]["adaptive_skill_created"] is True
    assert report["adaptive_skill_evidence"]["name"] == "local_html_game_forge"
    assert manifest["kind"] == "html_game"
    assert manifest["public_url"].endswith(".html")
    assert manifest["preview_url"] == manifest["public_url"]
    assert Path(manifest["asset_path"]).exists()
    html = Path(manifest["asset_path"]).read_text(encoding="utf-8")
    assert "Move: Arrow keys or WASD" in html
    assert "Jump: Space" in html
    assert quality["handover_ready"] is True
    assert quality["score"] >= 0.8


def test_capability_forge_space_shooter_prompt_builds_matching_game(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )

    report = build_and_write_capability_forge(
        "Build me an advanced game that I am a space ship shooting enemies.",
        root=tmp_path,
    )

    manifest = report["artifact_manifest"]
    quality = report["artifact_quality_report"]
    html = Path(manifest["asset_path"]).read_text(encoding="utf-8").lower()

    assert report["handover_ready"] is True
    assert manifest["game_kind"] == "space_shooter"
    assert "spaceship enemy shooter" in html
    assert "shoot: space" in html
    assert "enemies" in html
    assert "bullets" in html
    assert "glowing door" not in html
    assert any(check["id"] == "enemy_shooter_loop_present" and check["ok"] for check in quality["checks"])


def test_capability_forge_repeated_game_prompt_creates_unique_project_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )

    prompt = "Build me an advanced game that I am a space ship shooting enemies."
    first = build_and_write_capability_forge(prompt, root=tmp_path)
    second = build_and_write_capability_forge(prompt, root=tmp_path)

    first_manifest = first["artifact_manifest"]
    second_manifest = second["artifact_manifest"]
    assert first["build_id"] != second["build_id"]
    assert first["project_id"] != second["project_id"]
    assert first_manifest["public_url"] != second_manifest["public_url"]
    assert first_manifest["build_id"] == first["build_id"]
    assert second_manifest["build_id"] == second["build_id"]

    for report in (first, second):
        manifest = report["artifact_manifest"]
        quality = report["artifact_quality_report"]
        checks = {check["id"]: check for check in quality["checks"]}
        assert report["summary"]["fresh_project_per_request"] is True
        assert report["uniqueness_contract"]["reuse_allowed_for_handover"] is False
        assert manifest["uniqueness_contract"]["build_id"] == manifest["build_id"]
        assert checks["unique_build_id_present"]["ok"] is True
        assert checks["no_stale_handover_reuse"]["ok"] is True
        assert manifest["build_id"] in manifest["public_url"]
        assert Path(manifest["asset_path"]).exists()


def test_capability_forge_barcode_tool_request_builds_domain_specific_skill(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )

    report = build_and_write_capability_forge(
        "Build a local barcode label generator tool for the warehouse team, with run instructions and proof.",
        root=tmp_path,
    )

    manifest = report["artifact_manifest"]
    quality = report["artifact_quality_report"]
    assert report["handover_ready"] is True
    assert report["summary"]["adaptive_skill_created"] is True
    assert report["adaptive_skill_evidence"]["name"] == "barcode_label_generator_skill"
    assert manifest["kind"] == "barcode_label_generator"
    assert manifest["public_url"].endswith("/index.html")
    assert Path(manifest["asset_path"]).exists()
    assert Path(manifest["tool_path"]).exists()
    assert Path(manifest["runbook_path"]).exists()
    assert quality["handover_ready"] is True
    assert any(check["id"] == "domain_specific_barcode_logic" and check["ok"] for check in quality["checks"])
    tool_text = Path(manifest["tool_path"]).read_text(encoding="utf-8")
    assert "CODE39_PATTERNS" in tool_text
    assert "build_labels" in tool_text


def test_capability_forge_full_stack_prompt_builds_backend_frontend_tests(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )

    report = build_and_write_capability_forge(
        "Build a full-stack client task tracker with a backend API, frontend dashboard, local data store, and tests.",
        root=tmp_path,
    )

    manifest = report["artifact_manifest"]
    full_stack = report["full_stack_system_report"]
    quality = report["artifact_quality_report"]
    crew_roles = {item["role"] for item in report["recruited_crew"]}

    assert report["task_family"] == "full_stack"
    assert report["handover_ready"] is True
    assert report["summary"]["full_stack_system_created"] is True
    assert report["adaptive_skill_evidence"]["name"] == "local_full_stack_system_forge"
    assert manifest["kind"] == "full_stack_system"
    assert manifest["public_url"].endswith("/frontend/index.html")
    assert Path(manifest["backend_path"]).exists()
    assert Path(manifest["frontend_path"]).exists()
    assert Path(manifest["test_path"]).exists()
    assert "API Engineer" in crew_roles
    assert "Frontend Engineer" in crew_roles
    assert "Integration Test Pilot" in crew_roles
    assert full_stack["validation"]["status"] == "contract_validated"
    assert quality["handover_ready"] is True
    assert any(check["id"] == "crud_contract_passes" and check["ok"] for check in quality["checks"])

    backend_text = Path(manifest["backend_path"]).read_text(encoding="utf-8")
    frontend_text = Path(manifest["frontend_path"]).read_text(encoding="utf-8")
    app_text = Path(manifest["project_dir"], "frontend", "app.js").read_text(encoding="utf-8")
    test_text = Path(manifest["test_path"]).read_text(encoding="utf-8")
    assert "def create_item" in backend_text
    assert "app.js" in frontend_text
    assert "api/items" in app_text
    assert "test_health_and_crud_contract" in test_text


def test_capability_forge_repeated_tool_prompt_creates_unique_skill_dirs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )

    prompt = "Build a local barcode label generator tool for the warehouse team, with run instructions and proof."
    first = build_and_write_capability_forge(prompt, root=tmp_path)
    second = build_and_write_capability_forge(prompt, root=tmp_path)

    first_manifest = first["artifact_manifest"]
    second_manifest = second["artifact_manifest"]
    assert first_manifest["kind"] == "barcode_label_generator"
    assert second_manifest["kind"] == "barcode_label_generator"
    assert first_manifest["public_url"] != second_manifest["public_url"]
    assert first_manifest["tool_path"] != second_manifest["tool_path"]
    assert first_manifest["build_id"] != second_manifest["build_id"]
    assert first_manifest["uniqueness_contract"]["reuse_allowed_for_handover"] is False
    assert second_manifest["uniqueness_contract"]["reuse_allowed_for_handover"] is False


def test_capability_forge_generic_finished_tool_blocks_fake_handover(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "aureon.autonomous.aureon_safe_code_control.build_code_expression_context",
        _fake_expression_context,
    )

    report = build_and_write_capability_forge(
        "Build a local quantum spline inventory generator tool with run instructions and proof.",
        root=tmp_path,
    )

    manifest = report["artifact_manifest"]
    quality = report["artifact_quality_report"]
    assert report["handover_ready"] is False
    assert report["approval_state"]["state"] == "blocked_by_quality_gate"
    assert manifest["kind"] == "adaptive_skill_capsule"
    assert quality["handover_ready"] is False
    assert quality["status"] == "artifact_quality_blocked"
    assert any(snag["id"] == "missing_domain_specific_worker" for snag in quality["snags"])
