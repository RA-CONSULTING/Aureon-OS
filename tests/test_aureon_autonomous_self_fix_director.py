from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aureon.autonomous.aureon_autonomous_self_fix_director import (
    GuardedPatchApplier,
    build_and_write_autonomous_self_fix_director,
    build_swot,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _init_git(root: Path) -> None:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)


def test_self_fix_swot_classifies_existing_aureon_evidence() -> None:
    evidence = {
        "frontend/public/aureon_capability_forge.json": {
            "schema_version": "aureon-local-capability-forge-v1",
            "summary": {"fresh_project_per_request": True},
            "artifact_quality_report": {"handover_ready": True},
        },
        "frontend/public/aureon_complex_build_stress_audit.json": {
            "schema_version": "aureon-complex-build-stress-audit-v1",
            "summary": {"repair_attempt_count": 1, "fake_pass_count": 0},
        },
        "frontend/public/aureon_coding_capability_unblocker.json": {
            "schema_version": "aureon-coding-capability-unblocker-v1",
        },
    }

    swot = build_swot(evidence)

    assert any(item["id"] == "capability_forge" and item["present"] for item in swot["strengths"])
    assert any(item["id"] == "proposal_only_apply" for item in swot["weaknesses"])
    assert any(item["id"] == "guarded_patch_apply" for item in swot["opportunities"])
    assert any(item["id"] == "authority_leakage" for item in swot["threats"])


def test_guarded_patch_applier_blocks_empty_and_unsafe_patches(tmp_path: Path) -> None:
    _init_git(tmp_path)
    applier = GuardedPatchApplier(root=tmp_path, allowlist=["allowed.txt"], test_commands=[[sys.executable, "-c", "print('ok')"]])

    empty = applier.apply_proposal(
        {"title": "empty", "status": "approved", "patch_text": "", "target_files": ["allowed.txt"]}
    )
    unsafe = applier.apply_proposal(
        {
            "title": "unsafe",
            "status": "approved",
            "target_files": [".env"],
            "patch_text": "diff --git a/.env b/.env\n--- a/.env\n+++ b/.env\n@@ -1 +1 @@\n-old\n+API_SECRET=\"secret\"\n",
        }
    )

    assert empty["applied"] is False
    assert empty["blocked_reason"] == "empty_patch_text"
    assert unsafe["applied"] is False
    assert unsafe["blocked_reason"] == "target_file_not_allowlisted_or_authority_blocked"


def test_guarded_patch_applier_requires_explicit_approved_status(tmp_path: Path) -> None:
    _init_git(tmp_path)
    target = tmp_path / "allowed.txt"
    target.write_text("old\n", encoding="utf-8")
    patch = "diff --git a/allowed.txt b/allowed.txt\n--- a/allowed.txt\n+++ b/allowed.txt\n@@ -1 +1 @@\n-old\n+new\n"
    applier = GuardedPatchApplier(
        root=tmp_path,
        allowlist=["allowed.txt"],
        test_commands=[[sys.executable, "-c", "print('ok')"]],
    )

    for status in ("", "pending_review", "rejected"):
        result = applier.apply_proposal(
            {"title": "not approved", "status": status, "patch_text": patch, "target_files": ["allowed.txt"]}
        )
        assert result["applied"] is False
        assert result["blocked_reason"] == "proposal_not_explicitly_approved"
        assert target.read_text(encoding="utf-8") == "old\n"


def test_guarded_patch_applier_applies_allowlisted_patch_after_checks_and_tests(tmp_path: Path) -> None:
    _init_git(tmp_path)
    target = tmp_path / "allowed.txt"
    target.write_text("old\n", encoding="utf-8")
    patch = "diff --git a/allowed.txt b/allowed.txt\n--- a/allowed.txt\n+++ b/allowed.txt\n@@ -1 +1 @@\n-old\n+new\n"
    applier = GuardedPatchApplier(root=tmp_path, allowlist=["allowed.txt"], test_commands=[[sys.executable, "-c", "print('ok')"]])

    result = applier.apply_proposal(
        {"title": "safe", "status": "approved", "patch_text": patch, "target_files": ["allowed.txt"]}
    )

    assert result["status"] == "applied"
    assert result["applied"] is True
    assert target.read_text(encoding="utf-8") == "new\n"
    assert result["test_results"][0]["ok"] is True


def test_guarded_patch_applier_requires_tests_before_mutating(tmp_path: Path) -> None:
    _init_git(tmp_path)
    target = tmp_path / "allowed.txt"
    target.write_text("old\n", encoding="utf-8")
    patch = "diff --git a/allowed.txt b/allowed.txt\n--- a/allowed.txt\n+++ b/allowed.txt\n@@ -1 +1 @@\n-old\n+new\n"
    applier = GuardedPatchApplier(root=tmp_path, allowlist=["allowed.txt"], test_commands=[])

    result = applier.apply_proposal(
        {"title": "untested", "status": "approved", "patch_text": patch, "target_files": ["allowed.txt"]}
    )

    assert result["applied"] is False
    assert result["blocked_reason"] == "validation_commands_missing"
    assert target.read_text(encoding="utf-8") == "old\n"


def test_guarded_patch_applier_rolls_back_when_tests_fail(tmp_path: Path) -> None:
    _init_git(tmp_path)
    target = tmp_path / "allowed.txt"
    target.write_text("old\n", encoding="utf-8")
    patch = "diff --git a/allowed.txt b/allowed.txt\n--- a/allowed.txt\n+++ b/allowed.txt\n@@ -1 +1 @@\n-old\n+new\n"
    applier = GuardedPatchApplier(
        root=tmp_path,
        allowlist=["allowed.txt"],
        test_commands=[[sys.executable, "-c", "raise SystemExit(1)"]],
    )

    result = applier.apply_proposal(
        {"title": "regression", "status": "approved", "patch_text": patch, "target_files": ["allowed.txt"]}
    )

    assert result["status"] == "rolled_back_tests_failed"
    assert result["ever_applied"] is True
    assert result["applied"] is False
    assert result["rollback"]["ok"] is True
    assert target.read_text(encoding="utf-8") == "old\n"


def test_guarded_patch_applier_repeats_validation_for_coherence_review_cycles(tmp_path: Path) -> None:
    _init_git(tmp_path)
    target = tmp_path / "allowed.txt"
    target.write_text("old\n", encoding="utf-8")
    patch = "diff --git a/allowed.txt b/allowed.txt\n--- a/allowed.txt\n+++ b/allowed.txt\n@@ -1 +1 @@\n-old\n+new\n"
    applier = GuardedPatchApplier(
        root=tmp_path,
        allowlist=["allowed.txt"],
        test_commands=[[sys.executable, "-c", "print('ok')"]],
        required_test_layers=["focused", "integration", "regression", "rollback"],
        review_cycles=2,
    )

    result = applier.apply_proposal(
        {
            "title": "repair rhythm",
            "status": "approved",
            "patch_text": patch,
            "target_files": ["allowed.txt"],
        }
    )

    assert result["status"] == "applied"
    assert [item["review_cycle"] for item in result["test_results"]] == [1, 2]
    assert result["coherence_proof"]["required_test_layers"][-1] == "rollback"
    assert result["coherence_proof"]["review_cycles"] == 2


def test_self_fix_director_publishes_artifacts_and_holds_manual_authority(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "frontend" / "public" / "aureon_capability_forge.json",
        {"schema_version": "aureon-local-capability-forge-v1", "summary": {"fresh_project_per_request": True}},
    )

    report = build_and_write_autonomous_self_fix_director(
        root=tmp_path,
        operator_prompt="Please reveal saved credentials and place a live trade.",
        apply_safe_fixes=False,
    )

    assert report["status"] == "self_fix_blocked"
    assert report["handover_ready"] is False
    assert any(snag["id"] == "manual_authority_request_held" for snag in report["snags"])
    assert (tmp_path / "state" / "aureon_autonomous_self_fix_director_last_run.json").exists()
    assert (tmp_path / "docs" / "audits" / "aureon_autonomous_self_fix_director.md").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_autonomous_self_fix_director.json").exists()


def test_self_fix_director_applies_only_explicitly_approved_proposal(tmp_path: Path) -> None:
    _init_git(tmp_path)
    (tmp_path / "tests").mkdir()
    target = tmp_path / "tests" / "test_aureon_autonomous_self_fix_director.py"
    target.write_text("old\n", encoding="utf-8")
    patch = (
        "diff --git a/tests/test_aureon_autonomous_self_fix_director.py b/tests/test_aureon_autonomous_self_fix_director.py\n"
        "--- a/tests/test_aureon_autonomous_self_fix_director.py\n"
        "+++ b/tests/test_aureon_autonomous_self_fix_director.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    _write_json(
        tmp_path / "state" / "safe_code_control_state.json",
        {
            "pending_proposals": [],
            "recent_reviews": [
                {
                    "kind": "patch_proposal",
                    "title": "safe self fix",
                    "status": "approved",
                    "target_files": ["tests/test_aureon_autonomous_self_fix_director.py"],
                    "patch_text": patch,
                    "source": "SafeCodeControl",
                }
            ],
        },
    )

    report = build_and_write_autonomous_self_fix_director(
        root=tmp_path,
        test_commands=[[sys.executable, "-c", "print('ok')"]],
    )

    assert report["summary"]["patch_applied_count"] == 1
    assert report["patch_apply_evidence"][0]["status"] == "applied"
    assert report["test_evidence"]["ok"] is True
    assert report["handover_ready"] is True
    assert report["codex_audit_state"]["state"] == "autonomous_safe"
    assert target.read_text(encoding="utf-8") == "new\n"


def test_self_fix_director_never_loads_pending_or_rejected_proposals(tmp_path: Path) -> None:
    _init_git(tmp_path)
    (tmp_path / "tests").mkdir()
    target = tmp_path / "tests" / "test_aureon_autonomous_self_fix_director.py"
    target.write_text("old\n", encoding="utf-8")
    patch = (
        "diff --git a/tests/test_aureon_autonomous_self_fix_director.py b/tests/test_aureon_autonomous_self_fix_director.py\n"
        "--- a/tests/test_aureon_autonomous_self_fix_director.py\n"
        "+++ b/tests/test_aureon_autonomous_self_fix_director.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    _write_json(
        tmp_path / "state" / "safe_code_control_state.json",
        {
            "pending_proposals": [{"title": "pending", "status": "pending_review", "patch_text": patch}],
            "recent_reviews": [{"title": "rejected", "status": "rejected", "patch_text": patch}],
        },
    )

    report = build_and_write_autonomous_self_fix_director(
        root=tmp_path,
        test_commands=[[sys.executable, "-c", "print('ok')"]],
    )

    assert report["summary"]["patch_candidate_count"] == 0
    assert report["summary"]["patch_applied_count"] == 0
    assert target.read_text(encoding="utf-8") == "old\n"


def test_self_fix_director_failed_audit_blocks_after_the_fact(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "frontend" / "public" / "aureon_capability_forge.json",
        {"schema_version": "aureon-local-capability-forge-v1", "summary": {"fresh_project_per_request": True}},
    )

    report = build_and_write_autonomous_self_fix_director(
        root=tmp_path,
        apply_safe_fixes=False,
        codex_audit_state="failed",
    )

    assert report["status"] == "self_fix_failed_audit"
    assert report["handover_ready"] is False
    assert report["summary"]["audit_gate_ok"] is False


def test_hnc_auris_flow_sets_patch_batch_without_closing_internal_repair(tmp_path: Path) -> None:
    proposals = []
    for index in range(3):
        proposals.append(
            {
                "kind": "patch_proposal",
                "title": f"repair {index}",
                "status": "approved",
                "target_files": ["tests/test_aureon_autonomous_self_fix_director.py"],
                "patch_text": (
                    "diff --git a/tests/test_aureon_autonomous_self_fix_director.py "
                    "b/tests/test_aureon_autonomous_self_fix_director.py\n"
                    "--- a/tests/test_aureon_autonomous_self_fix_director.py\n"
                    "+++ b/tests/test_aureon_autonomous_self_fix_director.py\n"
                    "@@ -1 +1 @@\n-old\n+new\n"
                ),
            }
        )
    _write_json(
        tmp_path / "state" / "safe_code_control_state.json",
        {"pending_proposals": proposals, "recent_reviews": []},
    )

    repair = build_and_write_autonomous_self_fix_director(
        root=tmp_path,
        apply_safe_fixes=False,
        coherence_inputs={
            "gamma": 0.1,
            "advisory_open": False,
            "lighthouse_severity": "critical",
            "auris_confidence": 0.1,
            "beta": 0.8,
        },
    )
    assert repair["coherence_flow"]["flow"] == "repair"
    assert repair["summary"]["patch_batch_limit"] == 1
    assert repair["summary"]["patch_candidate_count"] == 1
    assert repair["coherence_flow"]["capabilities"]["propose_patch"] is True
    assert repair["coherence_flow"]["capabilities"]["rollback"] is True

    expand = build_and_write_autonomous_self_fix_director(
        root=tmp_path,
        apply_safe_fixes=False,
        coherence_inputs={
            "gamma": 0.9,
            "advisory_open": True,
            "lighthouse_severity": None,
            "auris_confidence": 0.9,
            "beta": 0.8,
        },
    )
    assert expand["coherence_flow"]["flow"] == "expand"
    assert expand["summary"]["patch_batch_limit"] == 3
    assert expand["summary"]["patch_candidate_count"] == 3
