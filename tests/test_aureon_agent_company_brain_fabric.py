from __future__ import annotations

import hashlib
from typing import Any, Generator

import pytest

from aureon.autonomous.aureon_agent_company_brain_fabric import (
    CANONICAL_AGENT_COMPANY_ROLE_COUNT,
    canonical_agent_company_brain_topology,
    company_brain_fabric_report,
    validate_agent_company_brain_topology,
)
from aureon.autonomous.aureon_agent_company_brain_fabric import (
    provision_agent_company_brain_fabric as _provision_agent_company_brain_fabric,
)
from aureon.autonomous.aureon_agent_company_builder import build_agent_company_bill_list
from aureon.autonomous.aureon_internal_coding_workforce import ResolvedBrain, WorkforceHold
from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk
from tests.aureon_ten_nine_one_fixtures import build_test_thought_path


def provision_agent_company_brain_fabric(*args, **kwargs):
    kwargs.setdefault("thought_path", build_test_thought_path())
    return _provision_agent_company_brain_fabric(*args, **kwargs)


class FabricAdapter(LLMAdapter):
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
        **kwargs: Any,
    ) -> LLMResponse:
        del system, tools, max_tokens, temperature, kwargs
        self.calls += 1
        return LLMResponse(text=f"{self.lane}:{self.calls}:{messages[-1]['content']}", model=self.lane)

    def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Generator[StreamChunk, None, None]:
        del messages, system, tools, max_tokens, temperature, kwargs
        yield StreamChunk(text="done", done=True)


class FabricResolver:
    def __init__(self) -> None:
        self.adapters: dict[str, FabricAdapter] = {}
        self.calls: list[str] = []

    def resolve(self, lane: str) -> ResolvedBrain:
        return self.resolve_for(lane, nerve_id=f"lane:{lane}")

    def resolve_for(self, lane: str, *, nerve_id: str) -> ResolvedBrain:
        self.calls.append(nerve_id)
        adapter = self.adapters.setdefault(lane, FabricAdapter(lane))
        return ResolvedBrain(
            adapter=adapter,
            lane=lane,
            model=f"ollama-{lane}",
            source="live_probe_passed:hnc_active:fake_catalog",
            endpoint_reachable=True,
            working=True,
            catalog_size=18,
            catalog_refreshed_at=1_787_000_000.0,
            endpoint_authority_digest="a" * 64,
            routing_receipt_id="ollama:hnc-route:" + hashlib.sha256(nerve_id.encode()).hexdigest(),
            hnc_receipt_id="hnc:live_field:test",
            hnc_gamma=0.9,
            hnc_coherence_band="active",
            provider_mode="ollama_cloud_primary",
        )


def test_canonical_company_topology_pairs_all_41_agents_and_processes() -> None:
    role_lanes, process_bindings = canonical_agent_company_brain_topology()

    assert len(role_lanes) == CANONICAL_AGENT_COMPANY_ROLE_COUNT == 41
    assert len(process_bindings) == 41
    assert {owner for _lane, owner in process_bindings.values()} == set(role_lanes)
    assert all(lane == role_lanes[owner] for lane, owner in process_bindings.values())


def test_company_fabric_provisions_82_verified_non_authoritative_passports() -> None:
    resolver = FabricResolver()
    workforce = provision_agent_company_brain_fabric(resolver)
    report = company_brain_fabric_report(workforce)

    assert report["status"] == "brain_fabric_ready"
    assert report["ready"] is True
    assert report["truth_gate_enforced"] is True
    assert report["agent_brain_count"] == 41
    assert report["process_brain_count"] == 41
    assert report["brain_passport_count"] == 82
    assert report["codex_implementation_allowed"] is False
    assert report["tools_enabled"] is False
    assert report["action_eligible"] is False
    assert report["economic_eligible"] is False
    assert len({item["receipt_id"] for item in report["passports"]}) == 82
    assert len(resolver.calls) == len(set(resolver.calls)) == 82
    assert all(agent.config.tools_enabled is False for agent in workforce.agents.values())
    assert all(len(agent.tools) == 0 for agent in workforce.process_brains.values())


def test_company_role_and_process_make_independent_receipted_decisions() -> None:
    workforce = provision_agent_company_brain_fabric(FabricResolver())
    role_lanes, process_bindings = canonical_agent_company_brain_topology()
    process_id = next(
        process for process, (_lane, owner) in process_bindings.items() if owner == "Code Architect"
    )

    agent_decision, agent_receipt = workforce.decide(
        subject_type="agent",
        subject_id="Code Architect",
        process_id=process_id,
        prompt="Design the smallest safe internal change.",
        stage="architecture",
    )
    process_decision, process_receipt = workforce.decide(
        subject_type="process",
        subject_id=process_id,
        process_id=process_id,
        prompt=f"Independently verify this plan: {agent_decision}",
        stage="architecture",
    )

    assert role_lanes["Code Architect"] == "architecture"
    assert agent_decision != process_decision
    assert agent_receipt.receipt_id != process_receipt.receipt_id
    assert agent_receipt.actor_id == "aureon:agent:Code Architect"
    assert process_receipt.actor_id == f"aureon:process:{process_id}"


def test_company_topology_rejects_missing_or_mismatched_process_brain() -> None:
    role_lanes, process_bindings = canonical_agent_company_brain_topology()
    missing = dict(process_bindings)
    missing.pop(next(iter(missing)))
    with pytest.raises(WorkforceHold, match="topology_incomplete"):
        validate_agent_company_brain_topology(role_lanes, missing)

    mismatched = dict(process_bindings)
    process_id = next(iter(mismatched))
    lane, owner = mismatched[process_id]
    mismatched[process_id] = ("general" if lane != "general" else "fast", owner)
    with pytest.raises(WorkforceHold, match="binding_mismatch"):
        validate_agent_company_brain_topology(role_lanes, mismatched)


def test_company_builder_explicitly_attaches_live_brain_fabric(tmp_path) -> None:
    (tmp_path / "aureon").mkdir()
    report = build_agent_company_bill_list(
        root=tmp_path,
        goal="Give every agent and process a brain.",
        provision_brains=True,
        brain_resolver=FabricResolver(),
        thought_path=build_test_thought_path(),
    )

    assert report["status"] == "agent_company_brain_fabric_ready"
    assert report["summary"]["executable_agents_created"] is True
    assert report["summary"]["agent_brain_count"] == 41
    assert report["summary"]["process_brain_count"] == 41
    assert report["brain_fabric"]["brain_passport_count"] == 82
    assert all(role["brain_binding"]["tools_enabled"] is False for role in report["roles"])
    assert all(agent["tools_enabled"] is False for agent in report["agents"])
    canonical_titles = set(canonical_agent_company_brain_topology()[0])
    roles = {item["title"]: item for item in report["roles"]}
    agents = {item["name"]: item for item in report["agents"]}
    design_titles = {
        title for title, item in roles.items() if item["department"] == "public_design"
    }

    assert len(canonical_titles) == 41
    assert len(design_titles) == 9
    assert report["summary"]["canonical_brain_role_count"] == 41
    assert report["summary"]["registry_only_role_count"] == 9
    assert report["summary"]["provisioned_role_count"] == 41
    assert report["completion_report"]["did_provision_all_agent_and_process_brains"] is False
    assert (
        report["completion_report"]["did_provision_all_canonical_agent_and_process_brains"]
        is True
    )
    assert report["completion_report"]["did_keep_public_design_roles_registry_only"] is True
    assert all(roles[title]["brain_binding"]["provisioned"] for title in canonical_titles)
    assert all(not roles[title]["brain_binding"]["provisioned"] for title in design_titles)
    assert all(not agents[title]["metadata"]["registry_only_v1"] for title in canonical_titles)
    assert all(agents[title]["metadata"]["registry_only_v1"] for title in design_titles)
    assert all(agents[title]["tools_enabled"] is False for title in design_titles)
