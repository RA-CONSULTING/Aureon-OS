from __future__ import annotations

from pathlib import Path
from typing import Any

from aureon.autonomous import aureon_autonomous_self_run_loop as self_run
from aureon.autonomous.aureon_internal_self_coder import _digest, _write_evidence
from aureon.autonomous.aureon_self_run_coding_task import (
    COMPACT_SELF_CODER_SUMMARY_FIELDS,
    run_self_coding_task,
)


def _valid_coder_receipt() -> dict[str, Any]:
    core = {
        "schema_version": "aureon-internal-self-coder-v1",
        "status": "internal_patch_applied_pending_senior_review",
        "applied": True,
        "pending_senior_review": True,
        "goal": "bounded goal",
        "target_selection": {},
        "test_commands": [],
        "patch_cycle": {},
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
        return _valid_coder_receipt()

    result = run_self_coding_task(
        tmp_path,
        "repair the bounded scheduler",
        enabled=True,
        coder=coder,
    )

    assert calls == 1
    assert result["ok"] is True
    assert result["summary"]["pending_senior_review"] is True
    assert result["summary"]["agent_brain_count"] == 41
    assert result["summary"]["process_brain_count"] == 41
    assert result["summary"]["brain_passport_count"] == 82
    assert result["summary"]["work_receipt_count"] == 19
    assert result["summary"]["codex_implementation"] is False
    assert set(result["summary"]) == COMPACT_SELF_CODER_SUMMARY_FIELDS
    assert "patch_cycle" not in result
    assert "target_selection" not in result


def test_pending_review_receipt_prevents_a_second_brain_or_patch_cycle(tmp_path: Path) -> None:
    receipt = _valid_coder_receipt()
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
    assert result["status"] == "internal_self_coder_pending_senior_review"
    assert result["summary"]["pending_senior_review"] is True
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


def test_adapter_requires_exact_41_41_82_brain_topology(tmp_path: Path) -> None:
    receipt = _valid_coder_receipt()
    receipt["agent_company_brain_fabric"]["agent_brain_count"] = 40

    result = run_self_coding_task(
        tmp_path,
        "bounded repair",
        enabled=True,
        coder=lambda **kwargs: receipt,
    )

    assert result["ok"] is False
    assert result["summary"]["reason_code"] == "internal_self_coder_brain_receipt_invalid"


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


def test_enabled_run_loop_invokes_one_internal_cycle_and_waits_for_senior_review(tmp_path: Path) -> None:
    calls = 0

    def self_coder(root: Path, prompt: str) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert root == tmp_path.resolve()
        assert prompt == "repair one clean Python target"
        receipt = _valid_coder_receipt()
        return {
            "status": receipt["status"],
            "ok": True,
            "summary": {
                "applied": True,
                "pending_senior_review": True,
                "release_ready": False,
                "evidence_digest": receipt["evidence_digest"],
                "codex_implementation": False,
                "action_eligible": False,
                "economic_eligible": False,
            },
            "output_files": ["state/aureon_internal_self_coder_last_run.json"],
        }

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
    assert report["summary"]["latest_task_ok_count"] == 10
    assert report["summary"]["pending_senior_review_count"] == 1
    assert report["summary"]["handover_ready"] is False
    assert report["status"] == "self_run_pending_senior_review"
    assert report["ok"] is False
    review_orders = [item for item in report["autonomous_work_orders"] if item["owner"] == "codex_senior_reviewer"]
    assert len(review_orders) == 1
    assert review_orders[0]["autonomous"] is False


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
    receipt = _valid_coder_receipt()
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
    assert report["status"] == "self_run_pending_senior_review"


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
