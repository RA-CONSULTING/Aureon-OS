from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import Any, Generator

import pytest

from aureon.autonomous.aureon_internal_coding_workforce import (
    INTERNAL_BRAIN_MAX_TOKENS,
    PROCESS_BRAIN_BINDINGS,
    ROLE_BRAIN_LANES,
    SENIOR_OVERSIGHT_ID,
    BrainPassport,
    OllamaSwitchboardBrainResolver,
    ResolvedBrain,
    WorkforceHold,
    _accept_hold_verdict,
    validate_brain_passport,
    validate_work_receipt,
)
from aureon.autonomous.aureon_internal_coding_workforce import (
    provision_internal_coding_workforce as _provision_internal_coding_workforce,
)
from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    TenNineOneHold,
    TenNineOneThoughtPath,
)
from aureon.autonomous.aureon_truth_gated_ten_nine_one import (
    TruthGatedTenNineOneThoughtPath,
)
from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk
from tests.aureon_ten_nine_one_fixtures import (
    NOW,
    TestEvidenceResolver,
    TestPropagator,
    TestTruthGate,
    build_test_thought_path,
)


def provision_internal_coding_workforce(*args, **kwargs):
    kwargs.setdefault("thought_path", build_test_thought_path())
    return _provision_internal_coding_workforce(*args, **kwargs)


class FakeAdapter(LLMAdapter):
    def __init__(self, lane: str) -> None:
        self.lane = lane
        self.calls = 0

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
        self.calls += 1
        return LLMResponse(
            text=f"{self.lane}-decision-{self.calls}:{messages[-1]['content']}",
            model=f"{self.lane}-model",
        )

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


class FakeResolver:
    def __init__(self, *, ready: bool = True, raise_for: str = "") -> None:
        self.ready = ready
        self.raise_for = raise_for
        self.adapters: dict[str, FakeAdapter] = {}
        self.calls: list[str] = []

    def resolve(self, lane: str) -> ResolvedBrain:
        return self.resolve_for(lane, nerve_id=f"lane:{lane}")

    def resolve_for(self, lane: str, *, nerve_id: str) -> ResolvedBrain:
        self.calls.append(nerve_id)
        if lane == self.raise_for:
            raise RuntimeError("resolver unavailable")
        adapter = self.adapters.setdefault(lane, FakeAdapter(lane))
        return ResolvedBrain(
            adapter=adapter,
            lane=lane,
            model=f"ollama-{lane}",
            source="live_probe_passed:hnc_active:fake_catalog"
            if self.ready
            else "configured_fallback_catalog_unavailable",
            endpoint_reachable=self.ready,
            working=self.ready,
            catalog_size=5,
            catalog_refreshed_at=1_787_000_000.0,
            endpoint_authority_digest="a" * 64,
            routing_receipt_id=(
                "ollama:hnc-route:" + hashlib.sha256(nerve_id.encode()).hexdigest()
                if self.ready
                else ""
            ),
            hnc_receipt_id="hnc:live_field:test" if self.ready else "",
            hnc_gamma=0.9 if self.ready else None,
            hnc_coherence_band="active" if self.ready else "",
            provider_mode="ollama_cloud_primary" if self.ready else "",
        )


def test_every_agent_and_process_receives_a_unique_proven_brain_passport() -> None:
    resolver = FakeResolver()
    workforce = provision_internal_coding_workforce(resolver)
    report = workforce.report()

    assert report["status"] == "no_data"
    assert report["ready"] is False
    assert report["brain_fabric_ready"] is True
    assert report["truth_gate_enforced"] is True
    assert report["thought_path_mode"] == "truth_gated_10_9_1"
    assert report["agent_brain_count"] == len(ROLE_BRAIN_LANES) == 9
    assert report["process_brain_count"] == len(PROCESS_BRAIN_BINDINGS) == 9
    assert report["unready_agents"] == []
    assert report["unready_processes"] == []
    assert report["cloud_fallback_used"] is False
    assert report["codex_implementation_allowed"] is False
    passports = report["passports"]
    assert len({item["receipt_id"] for item in passports}) == 18
    assert all(item["brain_ready"] for item in passports)
    assert all(item["action_eligible"] is False for item in passports)
    assert len(resolver.calls) == len(ROLE_BRAIN_LANES) + len(PROCESS_BRAIN_BINDINGS)
    assert len(resolver.calls) == len(set(resolver.calls))
    assert set(workforce.agents) == set(ROLE_BRAIN_LANES)
    assert set(workforce.process_brains) == set(PROCESS_BRAIN_BINDINGS)
    assert all(agent.config.tools_enabled is False for agent in workforce.agents.values())
    assert all(
        agent.config.max_tokens == INTERNAL_BRAIN_MAX_TOKENS
        for agent in (*workforce.agents.values(), *workforce.process_brains.values())
    )
    assert all(len(agent.tools) == 0 for agent in workforce.process_brains.values())


def test_aureon_brain_decision_emits_a_valid_internal_work_receipt() -> None:
    workforce = provision_internal_coding_workforce(FakeResolver())

    decision, receipt = workforce.decide(
        subject_type="agent",
        subject_id="Implementation Worker",
        process_id="build_execution",
        prompt="Inspect the failing test and propose the smallest safe code change.",
        stage="implementation",
        work_kind="patch_design",
    )

    assert decision.startswith("coding-decision-1")
    assert receipt.actor_class == "aureon_internal"
    assert receipt.actor_id == "aureon:agent:Implementation Worker"
    assert receipt.brain_passport_id.startswith("brain:")
    assert receipt.thought_path_receipt_id.startswith("thought:10-9-1:truth-gated:")
    assert validate_work_receipt(receipt) is True
    assert len(workforce.thought_path_receipts) == 1
    assert workforce.thought_path_receipts[0]["receipt_id"] == receipt.thought_path_receipt_id
    report = workforce.report()
    assert report["internal_work_units"] == 1
    assert report["ten_nine_one_work_units"] == 1
    assert report["ten_nine_one_complete"] is True
    assert report["senior_oversight_units"] == 0
    assert report["internal_share_ppm"] == 1_000_000
    assert report["ready"] is False
    assert report["senior_oversight_present"] is False


def test_brain_error_response_never_becomes_a_work_receipt() -> None:
    class ErrorAdapter(FakeAdapter):
        def prompt(self, *args, **kwargs) -> LLMResponse:
            del args, kwargs
            self.calls += 1
            return LLMResponse(text="[ERROR] LLM HTTP disabled", stop_reason="error")

    resolver = FakeResolver()
    resolver.adapters["coding"] = ErrorAdapter("coding")
    workforce = provision_internal_coding_workforce(resolver)

    with pytest.raises(WorkforceHold, match="brain_decision_failed"):
        workforce.decide(
            subject_type="agent",
            subject_id="Implementation Worker",
            process_id="build_execution",
            prompt="Author a patch.",
            stage="implementation",
        )

    assert workforce.work_receipts == ()


def test_truth_gate_correction_required_reprompts_once_without_releasing_first_answer() -> None:
    thought_path = build_test_thought_path()
    real_execute = thought_path.execute
    attempts: list[int] = []

    def execute_with_one_correction(*, correction_attempt=0, **kwargs):
        attempts.append(correction_attempt)
        if correction_attempt == 0:
            kwargs["infer"]("organized first attempt")
            raise TenNineOneHold(
                "truth_gate_correction_required:grounding_correction_required"
            )
        return real_execute(correction_attempt=correction_attempt, **kwargs)

    thought_path.execute = execute_with_one_correction
    resolver = FakeResolver()
    workforce = _provision_internal_coding_workforce(
        resolver,
        thought_path=thought_path,
    )

    decision, receipt = workforce.decide(
        subject_type="agent",
        subject_id="Implementation Worker",
        process_id="build_execution",
        prompt="Author a patch.",
        stage="implementation",
    )

    assert attempts == [0, 1]
    assert decision.startswith("coding-decision-2")
    assert resolver.adapters["coding"].calls == 2
    assert validate_work_receipt(receipt) is True
    assert len(workforce.work_receipts) == 1


def test_full_deliberation_uses_every_agent_and_every_process_brain() -> None:
    resolver = FakeResolver()
    workforce = provision_internal_coding_workforce(resolver)

    deliberation = workforce.deliberate_coding_goal("Repair Aureon's own coding loop safely.")

    assert deliberation["status"] == "complete"
    assert deliberation["active_agent_count"] == 9
    assert deliberation["decision_count"] == 18
    assert {item["role"] for item in deliberation["decisions"]} == set(ROLE_BRAIN_LANES)
    assert {item["process_id"] for item in deliberation["decisions"]} == set(PROCESS_BRAIN_BINDINGS)
    assert all(item["agent_work_receipt_id"].startswith("work:") for item in deliberation["decisions"])
    assert all(item["process_work_receipt_id"].startswith("work:") for item in deliberation["decisions"])
    assert workforce.report()["internal_work_units"] == 18


def test_selected_accept_hold_council_uses_exact_roles_and_paired_processes() -> None:
    class AcceptAdapter(FakeAdapter):
        def prompt(self, *args, **kwargs) -> LLMResponse:
            response = super().prompt(*args, **kwargs)
            return LLMResponse(text=f"ACCEPT {response.text}", model=response.model)

    class AcceptResolver(FakeResolver):
        def __init__(self) -> None:
            super().__init__()
            self.accept_adapters: dict[str, AcceptAdapter] = {}

        def resolve(self, lane: str) -> ResolvedBrain:
            return self.resolve_for(lane, nerve_id=f"lane:{lane}")

        def resolve_for(self, lane: str, *, nerve_id: str) -> ResolvedBrain:
            resolved = super().resolve_for(lane, nerve_id=nerve_id)
            adapter = self.accept_adapters.setdefault(lane, AcceptAdapter(lane))
            return replace(resolved, adapter=adapter)

    workforce = provision_internal_coding_workforce(AcceptResolver())
    council = workforce.deliberate_coding_goal(
        "Review one exact proposal digest.",
        selected_roles=("Test Pilot", "Security Auditor"),
        require_accept=True,
    )

    assert council["decision_mode"] == "accept_hold"
    assert council["accepted"] is True
    assert council["hold_count"] == 0
    assert council["active_agent_count"] == 2
    assert council["decision_count"] == 4
    assert {item["role"] for item in council["decisions"]} == {
        "Test Pilot",
        "Security Auditor",
    }
    assert all(item["agent_verdict"] == "ACCEPT" for item in council["decisions"])
    assert all(item["process_verdict"] == "ACCEPT" for item in council["decisions"])
    assert workforce.report()["internal_work_units"] == 4


def test_selected_council_treats_malformed_verdict_as_hold() -> None:
    workforce = provision_internal_coding_workforce(FakeResolver())

    council = workforce.deliberate_coding_goal(
        "Review one exact proposal digest.",
        selected_roles=("Test Pilot",),
        require_accept=True,
    )

    assert council["accepted"] is False
    assert council["hold_count"] == 1
    assert council["decisions"][0]["agent_verdict"] == "HOLD"
    assert council["decisions"][0]["process_verdict"] == "HOLD"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("ACCEPT reason", "ACCEPT"),
        ("**ACCEPT** reason", "ACCEPT"),
        ("__ACCEPT__: reason", "ACCEPT"),
        ("*HOLD* reason", "HOLD"),
        ("_HOLD_: reason", "HOLD"),
        ("**ACCEPT**extra reason", "HOLD"),
        ("**ACCEPT HOLD** reason", "HOLD"),
        ("approved reason", "HOLD"),
        ("", "HOLD"),
    ],
)
def test_accept_hold_parser_normalizes_only_exact_markdown_emphasis(
    value: str, expected: str
) -> None:
    assert _accept_hold_verdict(value) == expected


@pytest.mark.parametrize(
    "selected_roles",
    [(), ("Test Pilot", "Test Pilot"), ("Rogue Role",)],
)
def test_selected_council_rejects_empty_duplicate_or_foreign_roles(
    selected_roles: tuple[str, ...],
) -> None:
    workforce = provision_internal_coding_workforce(FakeResolver())

    with pytest.raises(WorkforceHold, match="selected_deliberation_roles_invalid"):
        workforce.deliberate_coding_goal(
            "Review one exact proposal digest.",
            selected_roles=selected_roles,
            require_accept=True,
        )

    assert workforce.work_receipts == ()


def test_exact_99_percent_internal_work_plus_senior_review_clears_contract() -> None:
    workforce = provision_internal_coding_workforce(FakeResolver())
    for index in range(99):
        workforce.decide(
            subject_type="process",
            subject_id="build_execution",
            process_id="build_execution",
            prompt=f"Internal coding decision {index}",
            stage="implementation",
        )
    workforce.record_senior_oversight(
        process_id="client_handover",
        stage="release_acceptance",
        reviewed_input_digest="b" * 64,
        review_output_digest="c" * 64,
    )

    report = workforce.report()
    assert report["ready"] is True
    assert report["status"] == "ready"
    assert report["internal_work_units"] == 99
    assert report["senior_oversight_units"] == 1
    assert report["total_work_units"] == 100
    assert report["internal_share_ppm"] == 990_000
    assert report["minimum_internal_share_ppm"] == 990_000
    assert report["internal_share_passed"] is True
    assert report["decision_authority"] == "aureon_internal"


def test_less_than_99_percent_internal_work_holds() -> None:
    workforce = provision_internal_coding_workforce(FakeResolver())
    for index in range(98):
        workforce.decide(
            subject_type="agent",
            subject_id="Estimator",
            process_id="client_intake",
            prompt=f"Scope decision {index}",
            stage="scope",
        )
    workforce.record_senior_oversight(
        process_id="client_handover",
        stage="release_acceptance",
        reviewed_input_digest="d" * 64,
        review_output_digest="e" * 64,
    )

    report = workforce.report()
    assert report["ready"] is False
    assert report["status"] == "hold"
    assert report["internal_share_ppm"] == 989_898
    assert report["internal_share_passed"] is False


def test_internal_work_after_codex_review_requires_a_new_final_review() -> None:
    workforce = provision_internal_coding_workforce(FakeResolver())
    for index in range(99):
        workforce.decide(
            subject_type="agent",
            subject_id="Estimator",
            process_id="client_intake",
            prompt=f"Decision {index}",
            stage="scope",
        )
    workforce.record_senior_oversight(
        process_id="client_handover",
        stage="release_acceptance",
        reviewed_input_digest="3" * 64,
        review_output_digest="4" * 64,
    )
    assert workforce.report()["ready"] is True

    workforce.decide(
        subject_type="agent",
        subject_id="Archive Librarian",
        process_id="memory_assimilation",
        prompt="Record one more learned result.",
        stage="assimilation",
    )

    report = workforce.report()
    assert report["internal_share_passed"] is True
    assert report["senior_oversight_is_final"] is False
    assert report["ready"] is False


def test_codex_cannot_take_implementation_credit() -> None:
    workforce = provision_internal_coding_workforce(FakeResolver())

    with pytest.raises(WorkforceHold, match="restricted_to_senior_oversight"):
        workforce.record_senior_oversight(
            process_id="build_execution",
            stage="implementation",
            reviewed_input_digest="1" * 64,
            review_output_digest="2" * 64,
        )

    assert workforce.report()["work_receipts"] == []


@pytest.mark.parametrize("failure_mode", ["unreachable", "resolver_exception"])
def test_missing_ollama_brain_fails_closed_without_cloud_fallback(failure_mode: str) -> None:
    resolver = FakeResolver(
        ready=failure_mode != "unreachable",
        raise_for="coding" if failure_mode == "resolver_exception" else "",
    )
    workforce = provision_internal_coding_workforce(resolver)
    report = workforce.report()

    assert report["ready"] is False
    assert report["brain_fabric_ready"] is False
    assert report["cloud_fallback_used"] is False
    assert report["unready_agents"]
    assert report["unready_processes"]
    failed = [item for item in report["passports"] if not item["brain_ready"]]
    assert all(item["status"] == "no_data" for item in failed)
    assert all(item["model"] == "" for item in failed)
    assert all(item["catalog_size"] is None for item in failed)
    with pytest.raises(WorkforceHold):
        workforce.decide(
            subject_type="agent",
            subject_id="Implementation Worker",
            process_id="build_execution",
            prompt="Do the work anyway",
            stage="implementation",
        )


def test_passport_and_work_receipt_are_hash_and_type_strict() -> None:
    workforce = provision_internal_coding_workforce(FakeResolver())
    passport = BrainPassport(**workforce.report()["passports"][0])
    assert validate_brain_passport(passport) is True
    assert validate_brain_passport(replace(passport, endpoint_reachable=1)) is False
    assert validate_brain_passport(replace(passport, receipt_id="brain:" + "0" * 64)) is False

    _, receipt = workforce.decide(
        subject_type="agent",
        subject_id="Test Pilot",
        process_id="internal_review",
        prompt="Review the focused test evidence.",
        stage="verification",
    )
    assert validate_work_receipt(replace(receipt, action_eligible=True)) is False
    assert validate_work_receipt(replace(receipt, actor_id=SENIOR_OVERSIGHT_ID)) is False
    assert validate_work_receipt(replace(receipt, thought_path_receipt_id="")) is False


def test_missing_stage_nine_hnc_makes_zero_ollama_calls() -> None:
    resolver = FakeResolver()
    evidence = TestEvidenceResolver()
    evidence.hnc = {}
    path = TruthGatedTenNineOneThoughtPath(
        resolver=evidence,
        propagator=TestPropagator(),
        truth_gate=TestTruthGate(),
        now=lambda: NOW,
    )
    workforce = _provision_internal_coding_workforce(resolver, thought_path=path)

    with pytest.raises(WorkforceHold, match="stage_9_fresh_canonical_hnc_required"):
        workforce.decide(
            subject_type="agent",
            subject_id="Implementation Worker",
            process_id="build_execution",
            prompt="Do not infer without HNC.",
            stage="implementation",
        )

    assert all(adapter.calls == 0 for adapter in resolver.adapters.values())
    assert workforce.work_receipts == ()
    assert workforce.thought_path_receipts == ()


def test_legacy_ungated_path_holds_before_hnc_or_cloud_inference() -> None:
    resolver = FakeResolver()
    evidence = TestEvidenceResolver()
    path = TenNineOneThoughtPath(
        resolver=evidence,
        propagator=TestPropagator(),
        now=lambda: NOW,
    )
    workforce = _provision_internal_coding_workforce(resolver, thought_path=path)

    with pytest.raises(WorkforceHold, match="truth_gated_10_9_1_path_required"):
        workforce.decide(
            subject_type="agent",
            subject_id="Implementation Worker",
            process_id="build_execution",
            prompt="This legacy path must not reach the cloud brain.",
            stage="implementation",
        )

    assert evidence.hnc_calls == 0
    assert all(adapter.calls == 0 for adapter in resolver.adapters.values())
    assert workforce.report()["brain_fabric_ready"] is False


def test_switchboard_requires_a_successful_live_probe_not_a_named_fallback() -> None:
    class Selection:
        lane = "coding"
        model = "named-but-unproven"
        source = "configured_fallback_catalog_unavailable"
        endpoint_reachable = False
        catalog_size = 0
        catalog_refreshed_at = 0.0

    class Switchboard:
        bridge = type("Bridge", (), {"base_url": "https://ollama.example.invalid"})()

        def compatible_adapter_for(self, lane: str):
            return FakeAdapter(lane), Selection()

    resolved = OllamaSwitchboardBrainResolver(Switchboard()).resolve("coding")
    assert resolved.model == "named-but-unproven"
    assert resolved.working is False

    class Resolver:
        def resolve(self, lane: str) -> ResolvedBrain:
            return replace(resolved, lane=lane)

    report = provision_internal_coding_workforce(Resolver()).report()
    assert report["brain_fabric_ready"] is False
    assert report["cloud_fallback_used"] is False
