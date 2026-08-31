from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Generator

import pytest

from aureon.autonomous import aureon_internal_self_coder as self_coder_module
from aureon.autonomous.aureon_agent_company_brain_fabric import (
    canonical_agent_company_brain_topology,
)
from aureon.autonomous.aureon_internal_coding_workforce import ResolvedBrain
from aureon.autonomous.aureon_internal_patch_loop import PRE_APPLY_COUNCIL_ROLES
from aureon.autonomous.aureon_internal_self_coder import (
    DEFAULT_EVIDENCE_PATH,
    DEFAULT_LEDGER_PATH,
    InternalSelfCoderHold,
    _digest,
    _parse_selection,
    _write_evidence,
    discover_clean_python_candidates,
    record_senior_proposal_review,
    record_senior_release_review,
)
from aureon.autonomous.aureon_internal_self_coder import (
    run_autonomous_self_coding as _run_autonomous_self_coding,
)
from aureon.autonomous.aureon_internal_work_ledger import DurableInternalWorkLedger
from aureon.autonomous.aureon_safe_code_control import SafeCodeControl
from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk
from tests.aureon_ten_nine_one_fixtures import build_test_thought_path


def run_autonomous_self_coding(*args, **kwargs):
    kwargs.setdefault("thought_path", build_test_thought_path())
    return _run_autonomous_self_coding(*args, **kwargs)


class SelfCoderAdapter(LLMAdapter):
    def __init__(
        self,
        lane: str,
        *,
        selected: str = "aureon/scheduler.py",
        invalid_selection_once: bool = False,
    ) -> None:
        self.lane = lane
        self.selected = selected
        self.invalid_selection_once = invalid_selection_once
        self.selection_calls = 0
        self.calls: list[str] = []

    def prompt(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> LLMResponse:
        del system, tools, max_tokens, temperature, kwargs
        prompt = str(messages[-1]["content"]).split("Original prompt:\n", 1)[-1]
        self.calls.append(prompt)
        if "Candidate digest:" in prompt and '"target_path"' in prompt:
            self.selection_calls += 1
            if self.invalid_selection_once and self.selection_calls == 1:
                text = "I select the scheduler file."
            else:
                text = json.dumps({"target_path": self.selected, "reason": "It owns the scheduler behavior."})
        elif prompt.startswith("AUTHOR ONE UNIFIED DIFF ONLY."):
            text = (
                "--- a/aureon/scheduler.py\n"
                "+++ b/aureon/scheduler.py\n"
                "@@ -1,2 +1,2 @@\n"
                " def interval():\n"
                "-    return 1\n"
                "+    return 2\n"
            )
        elif "PRE-APPLY COUNCIL." in prompt and "Reply ACCEPT or HOLD" in prompt:
            text = f"ACCEPT bounded {self.lane} pre-apply review"
        else:
            text = f"bounded {self.lane} decision"
        return LLMResponse(text=text, model=f"{self.lane}-model")

    def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs,
    ) -> Generator[StreamChunk, None, None]:
        del messages, system, tools, max_tokens, temperature, kwargs
        yield StreamChunk(text="done", done=True)


class SelfCoderResolver:
    def __init__(
        self,
        *,
        selected: str = "aureon/scheduler.py",
        invalid_selection_once: bool = False,
    ) -> None:
        self.selected = selected
        self.invalid_selection_once = invalid_selection_once
        self.adapters: dict[str, SelfCoderAdapter] = {}

    def resolve(self, lane: str) -> ResolvedBrain:
        return self.resolve_for(lane, nerve_id=f"lane:{lane}")

    def resolve_for(self, lane: str, *, nerve_id: str) -> ResolvedBrain:
        adapter = self.adapters.setdefault(
            lane,
            SelfCoderAdapter(
                lane,
                selected=self.selected,
                invalid_selection_once=self.invalid_selection_once,
            ),
        )
        return ResolvedBrain(
            adapter=adapter,
            lane=lane,
            model=f"ollama-{lane}",
            source="live_probe_passed:hnc_active:self-coder-test",
            endpoint_reachable=True,
            working=True,
            catalog_size=5,
            catalog_refreshed_at=1_787_000_000.0,
            endpoint_authority_digest="c" * 64,
            routing_receipt_id="ollama:hnc-route:" + hashlib.sha256(nerve_id.encode()).hexdigest(),
            hnc_receipt_id="hnc:live_field:test",
            hnc_gamma=0.9,
            hnc_coherence_band="active",
            provider_mode="ollama_cloud_primary",
        )


def _git(root: Path, *args: str) -> None:
    completed = None
    transient_windows_git_errors = (
        "Permission denied",
        "unable to write file",
        "failed to insert into database",
        "index.lock",
    )
    for attempt in range(10):
        completed = subprocess.run(["git", *args], cwd=root, check=False, capture_output=True, text=True)
        if completed.returncode == 0:
            return
        if not any(marker in completed.stderr for marker in transient_windows_git_errors):
            break
        time.sleep(0.05 * (attempt + 1))
    assert completed is not None
    raise subprocess.CalledProcessError(
        completed.returncode,
        completed.args,
        output=completed.stdout,
        stderr=completed.stderr,
    )


def _repo(root: Path) -> None:
    (root / "aureon").mkdir()
    (root / "tests").mkdir()
    (root / "aureon" / "__init__.py").write_text("", encoding="utf-8")
    (root / "aureon" / "scheduler.py").write_text("def interval():\n    return 1\n", encoding="utf-8")
    (root / "aureon" / "other.py").write_text("def unrelated():\n    return 0\n", encoding="utf-8")
    (root / "tests" / "test_scheduler.py").write_text(
        "from aureon.scheduler import interval\n\ndef test_interval():\n    assert interval() == 2\n",
        encoding="utf-8",
    )
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "aureon-test@example.invalid")
    _git(root, "config", "user.name", "Aureon Test")
    _git(root, "add", "aureon", "tests")
    _git(root, "commit", "-qm", "fixture")


def test_aureon_selects_authors_holds_and_persists_receipts(tmp_path: Path, monkeypatch) -> None:
    _repo(tmp_path)
    monkeypatch.setattr(SafeCodeControl, "_attach_expression_context", lambda self, proposal: None)

    result = run_autonomous_self_coding(
        root=tmp_path,
        goal="Improve the scheduler interval behavior and prove it.",
        resolver=SelfCoderResolver(),
    )

    assert result["applied"] is False
    assert result["pending_senior_review"] is True
    assert result["proposal_only"] is True
    assert result["release_hold"] is True
    assert result["release_authorized"] is False
    assert result["repository_mutation_authorized"] is False
    assert result["generated_code_execution_authorized"] is False
    assert result["repository_mutation_implemented"] is False
    assert result["generated_code_execution_implemented"] is False
    assert result["subprocess_test_execution_implemented"] is False
    assert result["effect_attempted"] is False
    assert result["test_commands_executed"] is False
    assert result["production_ready"] is False
    assert result["target_selection"]["target_path"] == "aureon/scheduler.py"
    assert result["target_selection"]["selection_work_receipt_id"].startswith("work:")
    assert result["work_ledger"]["receipt_count"] == 100
    assert result["work_ledger"]["ten_nine_one_internal_count"] == 100
    assert result["work_ledger"]["ten_nine_one_complete"] is True
    assert result["patch_cycle"]["workforce_report"]["internal_work_units"] == 100
    assert result["patch_cycle"]["workforce_report"]["ten_nine_one_work_units"] == 100
    assert result["patch_cycle"]["workforce_report"]["ten_nine_one_complete"] is True
    assert result["patch_cycle"]["pre_apply_council"]["decision_count"] == 16
    assert result["patch_cycle"]["pre_apply_council"]["accepted"] is True
    assert result["patch_cycle"]["workforce_report"]["senior_oversight_units"] == 0
    assert result["agent_company_brain_fabric"]["ready"] is True
    assert result["agent_company_brain_fabric"]["agent_brain_count"] == 41
    assert result["agent_company_brain_fabric"]["process_brain_count"] == 41
    assert result["agent_company_brain_fabric"]["brain_passport_count"] == 82
    assert result["agent_company_brain_fabric"]["tools_enabled"] is False
    assert result["codex_implementation"] is False
    assert (tmp_path / "aureon" / "scheduler.py").read_text(encoding="utf-8") == (
        "def interval():\n    return 1\n"
    )
    assert result["patch_cycle"]["apply_evidence"]["effect_attempted"] is False
    assert result["patch_cycle"]["production_magic_star_release_available"] is False
    assert result["patch_cycle"]["proposal"]["status"] == "proposal_reviewed_hold"
    assert (tmp_path / "state" / "aureon_internal_coding_work_ledger.json").is_file()
    assert (tmp_path / "state" / "aureon_internal_self_coder_last_run.json").is_file()


def test_candidate_discovery_excludes_dirty_and_test_targets(tmp_path: Path) -> None:
    _repo(tmp_path)
    (tmp_path / "aureon" / "scheduler.py").write_text("def interval():\n    return 9\n", encoding="utf-8")

    with pytest.raises(InternalSelfCoderHold, match="no_clean"):
        discover_clean_python_candidates(tmp_path, "scheduler interval")


def test_self_coder_rejects_mutating_git_and_out_of_state_evidence_paths(tmp_path: Path) -> None:
    with pytest.raises(InternalSelfCoderHold, match="read_only_inventory"):
        self_coder_module._git(tmp_path, "apply", "candidate.patch")
    with pytest.raises(InternalSelfCoderHold, match="must_remain_under_repo_state"):
        self_coder_module._bounded_state_path(tmp_path, Path("aureon/scheduler.py"))


def test_explicit_dirty_target_holds_before_any_model_call(tmp_path: Path, monkeypatch) -> None:
    _repo(tmp_path)
    (tmp_path / "aureon" / "scheduler.py").write_text("def interval():\n    return 9\n", encoding="utf-8")
    resolver = SelfCoderResolver()
    monkeypatch.setattr(SafeCodeControl, "_attach_expression_context", lambda self, proposal: None)

    with pytest.raises(InternalSelfCoderHold, match="target_must_be_clean"):
        run_autonomous_self_coding(
            root=tmp_path,
            goal="Improve scheduler interval",
            target_path="aureon/scheduler.py",
            resolver=resolver,
        )

    assert sum(len(adapter.calls) for adapter in resolver.adapters.values()) == 0


def test_architect_cannot_select_unoffered_target(tmp_path: Path, monkeypatch) -> None:
    _repo(tmp_path)
    monkeypatch.setattr(SafeCodeControl, "_attach_expression_context", lambda self, proposal: None)

    with pytest.raises(InternalSelfCoderHold, match="unoffered"):
        run_autonomous_self_coding(
            root=tmp_path,
            goal="Improve scheduler interval",
            resolver=SelfCoderResolver(selected="aureon/other.py"),
        )


def test_explicit_target_uses_no_architecture_selection_receipt(tmp_path: Path, monkeypatch) -> None:
    _repo(tmp_path)
    monkeypatch.setattr(SafeCodeControl, "_attach_expression_context", lambda self, proposal: None)
    marker = tmp_path / "suggested-self-coder-test-executed"
    result = run_autonomous_self_coding(
        root=tmp_path,
        goal="Improve scheduler interval",
        target_path="aureon/scheduler.py",
        test_commands=[
            [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).touch(); raise SystemExit(9)",
            ]
        ],
        resolver=SelfCoderResolver(),
    )

    assert result["applied"] is False
    assert result["target_selection"]["selection_work_receipt_id"] == ""
    assert result["work_ledger"]["receipt_count"] == 99
    assert result["patch_cycle"]["workforce_report"]["internal_work_units"] == 99
    assert result["test_commands_executed"] is False
    assert not marker.exists()


def _seed_full_fabric_internal_work(
    root: Path,
    resolver: SelfCoderResolver,
    *,
    total_internal: int,
) -> dict[str, Any]:
    ledger = DurableInternalWorkLedger(root / DEFAULT_LEDGER_PATH)
    workforce = ledger.bind_agent_company_workforce(resolver, thought_path=build_test_thought_path())
    _role_lanes, process_bindings = canonical_agent_company_brain_topology()
    process_by_role = {owner: process_id for process_id, (_lane, owner) in process_bindings.items()}
    baseline_count = total_internal - len(PRE_APPLY_COUNCIL_ROLES) * 2
    assert baseline_count >= 0
    author_process = process_by_role["Implementation Worker"]
    for index in range(baseline_count):
        workforce.decide(
            subject_type="agent",
            subject_id="Implementation Worker",
            process_id=author_process,
            prompt=f"bounded internal work {index}",
            stage="implementation",
        )
    decisions: list[dict[str, Any]] = []
    for role in PRE_APPLY_COUNCIL_ROLES:
        process_id = process_by_role[role]
        _agent_output, agent_receipt = workforce.decide(
            subject_type="agent",
            subject_id=role,
            process_id=process_id,
            prompt="ACCEPT exact digest-bound proposal",
            stage="pre_apply_council",
            work_kind="pre_apply_agent_review",
        )
        _process_output, process_receipt = workforce.decide(
            subject_type="process",
            subject_id=process_id,
            process_id=process_id,
            prompt="ACCEPT independently verified proposal",
            stage="pre_apply_council",
            work_kind="pre_apply_process_review",
        )
        decisions.append(
            {
                "role": role,
                "process_id": process_id,
                "agent_verdict": "ACCEPT",
                "process_verdict": "ACCEPT",
                "agent_work_receipt_id": agent_receipt.receipt_id,
                "process_work_receipt_id": process_receipt.receipt_id,
            }
        )
    assert ledger.status()["receipt_count"] == total_internal
    return {
        "status": "complete",
        "decision_count": len(decisions) * 2,
        "accepted": True,
        "hold_count": 0,
        "acceptance_scope": "proposal_review_only",
        "execution_authorized": False,
        "release_authorized": False,
        "production_ready": False,
        "decisions": decisions,
    }


def _pending_evidence(root: Path, council: dict[str, Any]) -> dict[str, Any]:
    ledger_status = DurableInternalWorkLedger(root / DEFAULT_LEDGER_PATH).status()
    core = {
        "schema_version": "aureon-internal-self-coder-v1",
        "status": "internal_patch_proposal_held_for_senior_review",
        "applied": False,
        "pending_senior_review": True,
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
        "production_ready": False,
        "patch_cycle": {
            "applied": False,
            "release_authorized": False,
            "effect_attempted": False,
            "test_commands_executed": False,
            "repository_mutation_implemented": False,
            "generated_code_execution_implemented": False,
            "subprocess_test_execution_implemented": False,
            "pre_apply_council": council,
            "apply_evidence": {
                "applied": False,
                "effect_attempted": False,
                "test_commands_executed": False,
                "release_authorized": False,
                "repository_mutation_implemented": False,
                "generated_code_execution_implemented": False,
                "subprocess_test_execution_implemented": False,
            },
        },
        "agent_company_brain_fabric": {
            "ready": True,
            "agent_brain_count": 41,
            "process_brain_count": 41,
            "brain_passport_count": 82,
        },
        "work_ledger": ledger_status,
        "codex_role": "senior_review_and_veto_only",
        "codex_implementation": False,
        "action_eligible": False,
        "economic_eligible": False,
    }
    evidence = {**core, "evidence_digest": _digest(core)}
    _write_evidence(root / DEFAULT_EVIDENCE_PATH, evidence)
    return evidence


def test_exact_senior_proposal_review_records_99_to_1_contract_and_keeps_hold(
    tmp_path: Path,
) -> None:
    resolver = SelfCoderResolver()
    council = _seed_full_fabric_internal_work(
        tmp_path,
        resolver,
        total_internal=99,
    )
    pending = _pending_evidence(tmp_path, council)

    reviewed = record_senior_proposal_review(
        root=tmp_path,
        review_output_digest="d" * 64,
        resolver=resolver,
        thought_path=build_test_thought_path(),
    )

    assert reviewed["pending_senior_review"] is False
    assert reviewed["status"] == "internal_patch_senior_proposal_review_recorded_release_hold"
    assert reviewed["applied"] is False
    assert reviewed["proposal_only"] is True
    assert reviewed["release_hold"] is True
    assert reviewed["release_authorized"] is False
    assert reviewed["repository_mutation_authorized"] is False
    assert reviewed["production_magic_star_release_available"] is False
    assert reviewed["reviewed_evidence_digest"] == pending["evidence_digest"]
    assert reviewed["workforce_proposal_review_report"]["ready"] is True
    assert reviewed["workforce_proposal_review_report"]["internal_work_units"] == 99
    assert reviewed["workforce_proposal_review_report"]["senior_oversight_units"] == 1
    assert reviewed["workforce_proposal_review_report"]["internal_share_ppm"] == 990_000
    assert reviewed["workforce_proposal_review_report"]["production_release_authorized"] is False
    assert "full_stack_release_receipt" not in reviewed


def test_legacy_release_review_entrypoint_is_disabled_without_calling_gate(tmp_path: Path) -> None:
    resolver = SelfCoderResolver()
    council = _seed_full_fabric_internal_work(
        tmp_path,
        resolver,
        total_internal=99,
    )
    _pending_evidence(tmp_path, council)
    ledger = DurableInternalWorkLedger(tmp_path / DEFAULT_LEDGER_PATH)
    before = ledger.status()

    class TripwireGate:
        calls = 0

        def require_accept(self, _request):
            self.calls += 1
            raise AssertionError("release gate must not be called")

    gate = TripwireGate()

    with pytest.raises(InternalSelfCoderHold, match="release_review_entrypoint_disabled"):
        record_senior_release_review(
            root=tmp_path,
            review_output_digest="f" * 64,
            resolver=resolver,
            full_stack_gate=gate,
            thought_path=build_test_thought_path(),
        )

    assert gate.calls == 0
    assert ledger.status() == before


def test_senior_review_is_held_before_lifetime_ratio_is_available(tmp_path: Path) -> None:
    resolver = SelfCoderResolver()
    ledger = DurableInternalWorkLedger(tmp_path / DEFAULT_LEDGER_PATH)
    council = _seed_full_fabric_internal_work(
        tmp_path,
        resolver,
        total_internal=20,
    )
    _pending_evidence(tmp_path, council)

    with pytest.raises(InternalSelfCoderHold, match="99_percent"):
        record_senior_proposal_review(
            root=tmp_path,
            review_output_digest="e" * 64,
            resolver=resolver,
            thought_path=build_test_thought_path(),
        )

    assert ledger.status()["receipt_count"] == 20


def test_architecture_selection_accepts_one_wrapped_object_but_not_two() -> None:
    parsed = _parse_selection(
        'Selection follows:\n```json\n{"target_path":"aureon/scheduler.py","reason":"bounded"}\n```'
    )
    assert parsed == {"target_path": "aureon/scheduler.py", "reason": "bounded"}

    with pytest.raises(InternalSelfCoderHold, match="json_invalid"):
        _parse_selection(
            '{"target_path":"aureon/scheduler.py","reason":"one"} '
            '{"target_path":"aureon/other.py","reason":"two"}'
        )


def test_architecture_gets_one_bounded_json_repair_attempt(tmp_path: Path, monkeypatch) -> None:
    _repo(tmp_path)
    monkeypatch.setattr(SafeCodeControl, "_attach_expression_context", lambda self, proposal: None)
    result = run_autonomous_self_coding(
        root=tmp_path,
        goal="Improve scheduler interval",
        resolver=SelfCoderResolver(invalid_selection_once=True),
    )

    assert result["applied"] is False
    assert len(result["target_selection"]["selection_work_receipt_ids"]) == 2
    assert result["work_ledger"]["receipt_count"] == 101
