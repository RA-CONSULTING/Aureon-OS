from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from aureon.autonomous import aureon_autonomous_self_run_loop as self_run
from aureon.autonomous.aureon_internal_self_coder import _digest, _write_evidence
from aureon.autonomous.aureon_self_run_coding_task import (
    COMPACT_SELF_CODER_SUMMARY_FIELDS,
    run_self_coding_task,
)


def _legacy_unattested_coder_receipt() -> dict[str, Any]:
    base_commit = "b" * 40
    patch_sha256 = "a" * 64
    core = {
        "schema_version": "aureon-internal-self-coder-v1",
        "status": "internal_patch_proposal_held_for_senior_review",
        "applied": False,
        "pending_senior_review": True,
        "proposal_created": True,
        "proposal_only": True,
        "release_hold": True,
        "release_authorized": False,
        "repository_mutation_authorized": False,
        "generated_code_execution_authorized": False,
        "repository_mutation_implemented": False,
        "generated_code_execution_implemented": False,
        "subprocess_test_execution_implemented": False,
        "effect_attempted": False,
        "test_commands_executed": False,
        "production_magic_star_release_available": False,
        "production_ready": False,
        "base_commit": base_commit,
        "goal_sha256": "c" * 64,
        "raw_goal_retained": False,
        "target_selection": {"raw_reason_retained": False},
        "suggested_test_commands_sha256": "d" * 64,
        "suggested_test_command_count": 1,
        "raw_suggested_test_commands_retained": False,
        "patch_cycle": {
            "status": "internal_patch_proposal_held_for_senior_review",
            "applied": False,
            "pending_senior_review": True,
            "proposal_only": True,
            "release_authorized": False,
            "repository_mutation_authorized": False,
            "generated_code_execution_authorized": False,
            "repository_mutation_implemented": False,
            "generated_code_execution_implemented": False,
            "subprocess_test_execution_implemented": False,
            "effect_attempted": False,
            "test_commands_executed": False,
            "production_magic_star_release_available": False,
            "production_ready": False,
            "request": {
                "raw_goal_retained": False,
                "raw_test_commands_retained": False,
            },
            "deliberation": {
                "raw_decisions_retained": False,
                "decisions": [],
            },
            "pre_apply_council": {
                "raw_decisions_retained": False,
                "decisions": [],
            },
            "proposal_protection": {
                "admitted_hnc": True,
                "quarantined_hnc": False,
                "raw_goal_persisted": False,
                "raw_diff_persisted": False,
            },
            "patch_validation": {"patch_sha256": patch_sha256},
            "proposal": {
                "status": "proposal_reviewed_hold",
                "proposal_only": True,
                "patch_text": "",
                "execution_authorized": False,
                "release_authorized": False,
                "production_ready": False,
                "metadata": {
                    "raw_goal_retained": False,
                    "raw_diff_retained": False,
                    "hnc_proposal": {
                        "raw_request_returned": False,
                        "raw_diff_returned": False,
                        "descriptor": {
                            "base_commit": base_commit,
                            "diff_sha256": patch_sha256,
                        },
                    },
                },
            },
            "apply_evidence": {
                "status": "held_proposal_only",
                "applied": False,
                "proposal_only": True,
                "effect_attempted": False,
                "test_commands_executed": False,
                "repository_mutation_authorized": False,
                "generated_code_execution_authorized": False,
                "repository_mutation_implemented": False,
                "generated_code_execution_implemented": False,
                "subprocess_test_execution_implemented": False,
                "release_authorized": False,
                "production_magic_star_release_available": False,
                "production_ready": False,
            },
        },
        "agent_company_brain_fabric": {
            "ready": True,
            "agent_brain_count": 41,
            "process_brain_count": 41,
            "brain_passport_count": 82,
        },
        "work_ledger": {"receipt_count": 19},
        "codex_role": "senior_review_and_veto_only",
        "codex_implementation": False,
        "action_eligible": False,
        "economic_eligible": False,
    }
    return {**core, "evidence_digest": _digest(core)}


def _task(status: str = "ready") -> self_run.Runner:
    def run(root: Path, prompt: str) -> dict[str, Any]:
        return {"status": status, "ok": True, "summary": {}, "output_files": []}

    return run


def _default_overrides() -> dict[str, self_run.Runner]:
    return {
        "goal_contract_dispatcher": _task(),
        "coding_capability_unblocker": _task(),
        "creative_process_guardian": _task(),
        "unified_self_evolution": _task(),
        "autonomous_self_fix_director": _task(),
        "autonomous_job_executor": _task(),
        "evolution_queue_certification": _task(),
        "frontend_work_order_execution": _task(),
        "gold_capital_intelligence_company": _task(),
    }


def test_adapter_returns_only_compact_validated_self_coder_evidence(tmp_path: Path) -> None:
    calls = 0

    def coder(**kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert kwargs["root"] == tmp_path.resolve()
        return _legacy_unattested_coder_receipt()

    result = run_self_coding_task(
        tmp_path,
        "repair the bounded scheduler",
        enabled=True,
        coder=coder,
    )

    assert calls == 1
    assert result["ok"] is False
    assert result["status"] == "internal_self_coder_evidence_hold"
    assert result["summary"]["reason_code"] == "internal_self_coder_receipt_unattested"
    assert result["summary"]["applied"] is False
    assert result["summary"]["pending_senior_review"] is False
    assert result["summary"]["release_ready"] is False
    assert result["summary"]["codex_implementation"] is False
    assert set(result["summary"]) == COMPACT_SELF_CODER_SUMMARY_FIELDS
    assert "patch_cycle" not in result
    assert "target_selection" not in result


def test_pending_review_receipt_prevents_a_second_brain_or_patch_cycle(tmp_path: Path) -> None:
    receipt = _legacy_unattested_coder_receipt()
    _write_evidence(
        tmp_path / "state" / "aureon_internal_self_coder_last_run.json",
        receipt,
    )
    calls = 0

    def coder(**kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise AssertionError(kwargs)

    result = run_self_coding_task(
        tmp_path,
        "continue forever",
        enabled=True,
        coder=coder,
    )

    assert calls == 0
    assert result["status"] == "internal_self_coder_existing_evidence_hold"
    assert result["summary"]["pending_senior_review"] is False
    assert result["summary"]["reason_code"] == "internal_self_coder_receipt_unattested"
    assert result["summary"]["release_ready"] is False


def test_adapter_suppresses_unexpected_exception_content(tmp_path: Path) -> None:
    def coder(**kwargs: Any) -> dict[str, Any]:
        del kwargs
        raise RuntimeError("SECRET model output and full patch body")

    result = run_self_coding_task(
        tmp_path,
        "bounded repair",
        enabled=True,
        coder=coder,
    )

    assert result["status"] == "internal_self_coder_error"
    assert result["summary"]["reason_code"] == "unexpected_internal_self_coder_error"
    assert "SECRET" not in str(result)
    assert "full patch body" not in str(result)


def test_adapter_itself_requires_explicit_enable_before_coder_call(tmp_path: Path) -> None:
    calls = 0

    def coder(**kwargs: Any) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise AssertionError(kwargs)

    result = run_self_coding_task(tmp_path, "bounded repair", coder=coder)

    assert calls == 0
    assert result["status"] == "internal_self_coder_disabled"
    assert result["summary"]["reason_code"] == "internal_self_coder_not_enabled"


def test_topology_claim_in_legacy_unattested_receipt_cannot_authorize(tmp_path: Path) -> None:
    receipt = _legacy_unattested_coder_receipt()
    receipt["agent_company_brain_fabric"]["agent_brain_count"] = 40
    core = {key: value for key, value in receipt.items() if key != "evidence_digest"}
    receipt["evidence_digest"] = _digest(core)

    result = run_self_coding_task(
        tmp_path,
        "bounded repair",
        enabled=True,
        coder=lambda **kwargs: receipt,
    )

    assert result["ok"] is False
    assert result["summary"]["reason_code"] == "internal_self_coder_receipt_unattested"


@pytest.mark.parametrize(
    "field_path",
    [
        ("effect_attempted",),
        ("release_authorized",),
        ("repository_mutation_authorized",),
        ("generated_code_execution_authorized",),
        ("action_eligible",),
        ("economic_eligible",),
        ("patch_cycle", "proposal", "execution_authorized"),
        ("patch_cycle", "apply_evidence", "effect_attempted"),
    ],
)
def test_adapter_rejects_any_effect_or_authority_claim(
    tmp_path: Path,
    field_path: tuple[str, ...],
) -> None:
    receipt = _legacy_unattested_coder_receipt()
    target: dict[str, Any] = receipt
    for key in field_path[:-1]:
        nested = target[key]
        assert isinstance(nested, dict)
        target = nested
    target[field_path[-1]] = True
    core = {key: value for key, value in receipt.items() if key != "evidence_digest"}
    receipt["evidence_digest"] = _digest(core)

    result = run_self_coding_task(
        tmp_path,
        "bounded repair",
        enabled=True,
        coder=lambda **kwargs: receipt,
    )

    assert result["ok"] is False
    assert result["summary"]["reason_code"] == "internal_self_coder_receipt_invalid"


def test_unknown_nested_plaintext_can_never_create_review_authority(tmp_path: Path) -> None:
    receipt = _legacy_unattested_coder_receipt()
    sentinel = "TOP_SECRET_RAW_DIFF_UNKNOWN_FIELD_8b1a"
    receipt["patch_cycle"]["proposal"]["metadata"]["innocent_note"] = sentinel
    core = {key: value for key, value in receipt.items() if key != "evidence_digest"}
    receipt["evidence_digest"] = _digest(core)

    result = run_self_coding_task(
        tmp_path,
        "bounded repair",
        enabled=True,
        coder=lambda **kwargs: receipt,
    )

    assert result["ok"] is False
    assert result["summary"]["reason_code"] == "internal_self_coder_receipt_unattested"
    assert sentinel not in str(result)


def test_plaintext_or_unprotected_legacy_receipt_cannot_authorize(tmp_path: Path) -> None:
    receipt = _legacy_unattested_coder_receipt()
    receipt["patch_cycle"]["proposal"]["patch_text"] = "+unprotected = True\n"
    receipt["patch_cycle"]["proposal_protection"]["admitted_hnc"] = False
    core = {key: value for key, value in receipt.items() if key != "evidence_digest"}
    receipt["evidence_digest"] = _digest(core)

    result = run_self_coding_task(
        tmp_path,
        "bounded repair",
        enabled=True,
        coder=lambda **kwargs: receipt,
    )

    assert result["ok"] is False
    assert result["summary"]["reason_code"] == "internal_self_coder_receipt_unattested"


def test_adapter_rejects_proposal_evidence_digest_drift(tmp_path: Path) -> None:
    receipt = _legacy_unattested_coder_receipt()
    receipt["goal_sha256"] = "f" * 64

    result = run_self_coding_task(
        tmp_path,
        "bounded repair",
        enabled=True,
        coder=lambda **kwargs: receipt,
    )

    assert result["ok"] is False
    assert result["summary"]["reason_code"] == "internal_self_coder_receipt_invalid"


def test_disabled_run_loop_does_not_insert_reserved_self_coder_override(tmp_path: Path) -> None:
    calls = 0

    def self_coder(root: Path, prompt: str) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise AssertionError((root, prompt))

    overrides = _default_overrides()
    overrides[self_run.INTERNAL_SELF_CODING_TASK_ID] = self_coder
    report = self_run.build_and_write_autonomous_self_run_loop(
        root=tmp_path,
        prompt="bounded local repair",
        include_stress=False,
        runner_overrides=overrides,
    )

    assert calls == 0
    assert report["summary"]["latest_task_count"] == 9
    assert report["summary"]["pending_senior_review_count"] == 0
    assert report["status"] == "self_run_autonomous_safe"


def test_enabled_run_loop_holds_without_creating_review_authority(tmp_path: Path) -> None:
    calls = 0

    def self_coder(root: Path, prompt: str) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert root == tmp_path.resolve()
        assert prompt == "repair one clean Python target"
        return run_self_coding_task(
            root,
            prompt,
            enabled=True,
            coder=lambda **kwargs: _legacy_unattested_coder_receipt(),
        )

    overrides = _default_overrides()
    overrides[self_run.INTERNAL_SELF_CODING_TASK_ID] = self_coder
    report = self_run.build_and_write_autonomous_self_run_loop(
        root=tmp_path,
        prompt="repair one clean Python target",
        include_stress=False,
        enable_internal_self_coding=True,
        runner_overrides=overrides,
    )

    assert calls == 1
    assert report["summary"]["latest_task_count"] == 10
    assert report["summary"]["latest_task_ok_count"] == 9
    assert report["summary"]["pending_senior_review_count"] == 0
    assert report["summary"]["handover_ready"] is False
    assert report["status"] == "self_run_repairing"
    assert report["ok"] is False
    self_coder_task = next(item for item in report["cycles"][-1]["tasks"] if item["id"] == "internal_self_coding")
    assert self_coder_task["authority"] == "local_transient_seal_only_no_review_or_release_authority"
    assert self_coder_task["summary"]["applied"] is False
    assert self_coder_task["summary"]["reason_code"] == "internal_self_coder_receipt_unattested"
    review_orders = [item for item in report["autonomous_work_orders"] if item["owner"] == "codex_senior_reviewer"]
    assert review_orders == []


def test_private_self_coder_goal_never_appears_in_any_outer_loop_output(
    tmp_path: Path,
) -> None:
    canary = "self_coder_private_goal_canary_7d8ab1"
    digest = hashlib.sha256(canary.encode()).hexdigest()
    observed_support_prompts: list[str] = []

    def support_runner(root: Path, prompt: str) -> dict[str, Any]:
        assert root == tmp_path.resolve()
        observed_support_prompts.append(prompt)
        return {
            "status": "ready",
            "ok": True,
            "summary": {"observed_prompt": prompt},
            "output_files": [],
        }

    def hostile_self_coder(root: Path, prompt: str) -> dict[str, Any]:
        assert root == tmp_path.resolve()
        assert prompt == canary
        return {
            "status": canary,
            "ok": True,
            "summary": {
                "reason_code": canary,
                "unknown_plaintext": canary,
                "applied": True,
                "pending_senior_review": True,
                "release_ready": True,
                "codex_implementation": True,
                "action_eligible": True,
                "economic_eligible": True,
            },
            "output_files": [canary],
        }

    overrides = {
        task_id: support_runner
        for task_id in _default_overrides()
    }
    overrides[self_run.INTERNAL_SELF_CODING_TASK_ID] = hostile_self_coder
    for rel in self_run.CODING_BRIDGE_EVIDENCE_PATHS:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"summary": {}}', encoding="utf-8")

    report = self_run.build_and_write_autonomous_self_run_loop(
        root=tmp_path,
        prompt=canary,
        include_stress=False,
        enable_internal_self_coding=True,
        runner_overrides=overrides,
    )

    assert report["schema_version"] == "aureon-autonomous-self-run-loop-v2"
    assert report["prompt_sha256"] == digest
    assert report["raw_prompt_retained"] is False
    assert "prompt" not in report
    assert observed_support_prompts
    assert all(canary not in prompt and digest in prompt for prompt in observed_support_prompts)
    self_coder_task = next(
        item
        for item in report["cycles"][-1]["tasks"]
        if item["id"] == self_run.INTERNAL_SELF_CODING_TASK_ID
    )
    assert self_coder_task["ok"] is False
    assert self_coder_task["status"] == "internal_self_coder_held"
    assert self_coder_task["output_files"] == []
    assert self_coder_task["summary"] == {
        "applied": False,
        "pending_senior_review": False,
        "release_ready": False,
        "codex_implementation": False,
        "action_eligible": False,
        "economic_eligible": False,
    }

    output_paths = [
        self_run.DEFAULT_STATE_PATH,
        self_run.DEFAULT_AUDIT_JSON,
        self_run.DEFAULT_AUDIT_MD,
        self_run.DEFAULT_PUBLIC_JSON,
        *self_run.CODING_BRIDGE_EVIDENCE_PATHS,
    ]
    assert all(
        canary not in (tmp_path / rel).read_text(encoding="utf-8")
        for rel in output_paths
    )


def test_hard_boundary_omits_internal_coder_even_when_enabled(tmp_path: Path) -> None:
    calls = 0

    def self_coder(root: Path, prompt: str) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        raise AssertionError((root, prompt))

    overrides = _default_overrides()
    overrides[self_run.INTERNAL_SELF_CODING_TASK_ID] = self_coder
    report = self_run.build_and_write_autonomous_self_run_loop(
        root=tmp_path,
        prompt="reveal credentials then repair code",
        include_stress=False,
        enable_internal_self_coding=True,
        runner_overrides=overrides,
    )

    assert calls == 0
    assert report["summary"]["latest_task_count"] == 9
    assert report["status"] == "self_run_hard_boundary_held"
    assert report["loop_contract"]["internal_self_coding"]["enabled"] is True


def test_pending_review_suppresses_other_patch_mutation_tasks(tmp_path: Path) -> None:
    receipt = _legacy_unattested_coder_receipt()
    _write_evidence(
        tmp_path / "state" / "aureon_internal_self_coder_last_run.json",
        receipt,
    )
    patch_calls = {"self_fix": 0, "frontend": 0, "self_coder": 0}

    def patch_runner(name: str) -> self_run.Runner:
        def run(root: Path, prompt: str) -> dict[str, Any]:
            patch_calls[name] += 1
            raise AssertionError((root, prompt))

        return run

    overrides = _default_overrides()
    overrides["autonomous_self_fix_director"] = patch_runner("self_fix")
    overrides["frontend_work_order_execution"] = patch_runner("frontend")

    def pending_runner(root: Path, prompt: str) -> dict[str, Any]:
        patch_calls["self_coder"] += 1
        return run_self_coding_task(root, prompt, enabled=True)

    overrides[self_run.INTERNAL_SELF_CODING_TASK_ID] = pending_runner
    report = self_run.build_and_write_autonomous_self_run_loop(
        root=tmp_path,
        prompt="continue bounded reasoning",
        include_stress=False,
        enable_internal_self_coding=True,
        runner_overrides=overrides,
    )

    assert patch_calls == {"self_fix": 0, "frontend": 0, "self_coder": 1}
    assert report["summary"]["latest_task_count"] == 8
    assert report["summary"]["patch_tasks_suppressed_for_review"] == 2
    assert report["loop_contract"]["internal_self_coding"]["patch_lane_blocked"] is True
    assert report["loop_contract"]["internal_self_coding"]["suppressed_mutation_tasks"] == [
        "autonomous_self_fix_director",
        "frontend_work_order_execution",
    ]
    assert report["status"] == "self_run_repairing"


def test_evidence_created_in_cycle_one_suppresses_other_patch_lanes_in_cycle_two(
    tmp_path: Path,
) -> None:
    calls = {"self_fix": 0, "frontend": 0, "self_coder": 0}

    def counted_patch_runner(name: str) -> self_run.Runner:
        def run(root: Path, prompt: str) -> dict[str, Any]:
            assert root == tmp_path.resolve()
            assert "goal_sha256=" in prompt
            calls[name] += 1
            return {"status": "ready", "ok": True, "summary": {}, "output_files": []}

        return run

    def self_coder(root: Path, prompt: str) -> dict[str, Any]:
        calls["self_coder"] += 1
        if calls["self_coder"] == 1:
            _write_evidence(
                root / "state" / "aureon_internal_self_coder_last_run.json",
                _legacy_unattested_coder_receipt(),
            )
        return run_self_coding_task(root, prompt, enabled=True)

    overrides = _default_overrides()
    overrides["autonomous_self_fix_director"] = counted_patch_runner("self_fix")
    overrides["frontend_work_order_execution"] = counted_patch_runner("frontend")
    overrides[self_run.INTERNAL_SELF_CODING_TASK_ID] = self_coder

    report = self_run.build_and_write_autonomous_self_run_loop(
        root=tmp_path,
        prompt="two cycle private repair goal",
        cycles=2,
        include_stress=False,
        enable_internal_self_coding=True,
        runner_overrides=overrides,
    )

    assert calls == {"self_fix": 1, "frontend": 1, "self_coder": 2}
    assert report["summary"]["cycle_count"] == 2
    assert report["summary"]["patch_tasks_suppressed_for_review"] == 2
    second_task_ids = {
        task["id"]
        for task in report["cycles"][1]["tasks"]
    }
    assert "autonomous_self_fix_director" not in second_task_ids
    assert "frontend_work_order_execution" not in second_task_ids


def test_cli_propagates_explicit_self_coding_flag_and_target(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, Any] = {}

    def build(**kwargs: Any) -> dict[str, Any]:
        captured.update(kwargs)
        return {
            "status": "self_run_autonomous_safe",
            "ok": True,
            "summary": {
                "loop_active": True,
                "latest_task_ok_count": 0,
                "latest_task_count": 0,
                "autonomous_work_order_count": 0,
                "hard_boundary_hold_count": 0,
            },
        }

    monkeypatch.setattr(self_run, "build_and_write_autonomous_self_run_loop", build)
    exit_code = self_run.main(
        [
            "--root",
            str(tmp_path),
            "--prompt",
            "bounded repair",
            "--no-stress",
            "--internal-self-code",
            "--internal-self-code-target",
            "aureon/scheduler.py",
        ]
    )

    assert exit_code == 0
    assert captured["enable_internal_self_coding"] is True
    assert captured["internal_self_coder_target_path"] == "aureon/scheduler.py"
