"""Brain bindings for every canonical Aureon agent-company role and process.

The company registry remains the source of role truth.  This module assigns a
reasoning lane and a paired, independently receipted process brain to each
role.  It does not grant tools, filesystem access, deployment authority, or
economic authority.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Dict, Mapping

from aureon.autonomous.aureon_agent_company_builder import AgentCompanyRole, _role_specs
from aureon.autonomous.aureon_internal_coding_workforce import (
    BrainResolver,
    CodingThoughtPath,
    InternalCodingWorkforce,
    WorkforceHold,
    WorkReceipt,
    provision_brain_bound_workforce,
)

SCHEMA_VERSION = "aureon-agent-company-brain-fabric-v1"
CANONICAL_AGENT_COMPANY_ROLE_COUNT = 41
VALID_BRAIN_LANES = frozenset({"coding", "architecture", "self_evolution", "fast", "general"})
REGISTRY_ONLY_AGENT_COMPANY_DEPARTMENTS = frozenset({"public_design"})

_CODING_TERMS = frozenset(
    {"code", "implementation", "file_edit", "react", "typescript", "testing", "build", "safe_patch"}
)
_ARCHITECTURE_TERMS = frozenset(
    {
        "architecture",
        "strategy",
        "security",
        "security_review",
        "risk",
        "guardrails",
        "authority_scoping",
        "compliance_boundary",
        "contract_design",
    }
)
_EVOLUTION_TERMS = frozenset(
    {"incident_response", "recovery", "cleanup_queue", "state_cleanup", "workforce_retirement"}
)
_FAST_TERMS = frozenset(
    {
        "client_intake",
        "queue_management",
        "status",
        "evidence",
        "checklist",
        "classification",
        "repo_search",
    }
)


def brain_lane_for_role(role: AgentCompanyRole) -> str:
    """Choose a deterministic switchboard lane from the canonical role contract."""

    capabilities = {str(item).strip().lower() for item in role.capabilities}
    title = role.title.lower()
    if capabilities & _CODING_TERMS:
        return "coding"
    if capabilities & _ARCHITECTURE_TERMS or any(
        marker in title for marker in ("chief", "architect", "governor", "auditor", "boundary officer")
    ):
        return "architecture"
    if capabilities & _EVOLUTION_TERMS or any(
        marker in title for marker in ("responder", "cleaner", "retirement")
    ):
        return "self_evolution"
    if capabilities & _FAST_TERMS or any(
        marker in title for marker in ("clerk", "broker", "steward", "cartographer")
    ):
        return "fast"
    return "general"


def _canonical_brain_roles() -> list[AgentCompanyRole]:
    """Keep registry-only planning roles outside the executable 41-seat fabric."""

    return [
        role
        for role in _role_specs()
        if role.department not in REGISTRY_ONLY_AGENT_COMPANY_DEPARTMENTS
    ]


def canonical_agent_company_brain_topology() -> tuple[Dict[str, str], Dict[str, tuple[str, str]]]:
    """Return the exact 41-role/41-process topology from the company registry."""

    roles = _canonical_brain_roles()
    if len(roles) != CANONICAL_AGENT_COMPANY_ROLE_COUNT:
        raise WorkforceHold("canonical_agent_company_role_count_mismatch")
    if len({role.role_id for role in roles}) != len(roles) or len({role.title for role in roles}) != len(
        roles
    ):
        raise WorkforceHold("canonical_agent_company_role_identity_duplicate")
    role_lanes = {role.title: brain_lane_for_role(role) for role in roles}
    process_bindings = {
        f"agent_company_role_cycle:{role.role_id}": (role_lanes[role.title], role.title) for role in roles
    }
    validate_agent_company_brain_topology(role_lanes, process_bindings)
    return role_lanes, process_bindings


def validate_agent_company_brain_topology(
    role_lanes: Mapping[str, str], process_bindings: Mapping[str, tuple[str, str]]
) -> None:
    roles = _canonical_brain_roles()
    expected_titles = {role.title for role in roles}
    expected_processes = {f"agent_company_role_cycle:{role.role_id}" for role in roles}
    if set(role_lanes) != expected_titles or set(process_bindings) != expected_processes:
        raise WorkforceHold("agent_company_brain_topology_incomplete")
    owners: set[str] = set()
    for process_id, binding in process_bindings.items():
        if not isinstance(binding, tuple) or len(binding) != 2:
            raise WorkforceHold("agent_company_process_binding_invalid")
        lane, owner = binding
        if lane not in VALID_BRAIN_LANES or role_lanes.get(owner) != lane or owner in owners:
            raise WorkforceHold("agent_company_process_binding_mismatch")
        if not process_id.startswith("agent_company_role_cycle:"):
            raise WorkforceHold("agent_company_process_identity_invalid")
        owners.add(owner)
    if owners != expected_titles:
        raise WorkforceHold("agent_company_role_process_pairing_incomplete")


def provision_agent_company_brain_fabric(
    resolver: BrainResolver | None = None,
    *,
    prior_work_receipts: Sequence[WorkReceipt] = (),
    receipt_sink: Callable[[WorkReceipt], None] | None = None,
    thought_path: CodingThoughtPath | None = None,
) -> InternalCodingWorkforce:
    """Give all canonical agents and paired processes a proven Ollama brain."""

    role_lanes, process_bindings = canonical_agent_company_brain_topology()
    return provision_brain_bound_workforce(
        role_brain_lanes=role_lanes,
        process_brain_bindings=process_bindings,
        resolver=resolver,
        prior_work_receipts=prior_work_receipts,
        receipt_sink=receipt_sink,
        thought_path=thought_path,
    )


def company_brain_fabric_report(workforce: InternalCodingWorkforce) -> Dict[str, Any]:
    """Report topology readiness separately from work/release completion."""

    report = workforce.report()
    expected = CANONICAL_AGENT_COMPANY_ROLE_COUNT
    passport_count = len(report["passports"])
    ready = bool(
        report["brain_fabric_ready"]
        and report["all_brains_hnc_routed"]
        and report["agent_brain_count"] == expected
        and report["process_brain_count"] == expected
        and passport_count == expected * 2
        and report["distinct_hnc_routing_receipt_count"] == expected * 2
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "brain_fabric_ready" if ready else "hold",
        "ready": ready,
        "canonical_role_count": expected,
        "agent_brain_count": report["agent_brain_count"],
        "process_brain_count": report["process_brain_count"],
        "brain_passport_count": passport_count,
        "hnc_routed_brain_count": report["hnc_routed_brain_count"],
        "all_brains_hnc_routed": report["all_brains_hnc_routed"],
        "truth_gate_enforced": report["truth_gate_enforced"],
        "distinct_hnc_routing_receipt_count": report["distinct_hnc_routing_receipt_count"],
        "distinct_cloud_model_count": report["distinct_cloud_model_count"],
        "provider_mode": report["provider_mode"],
        "unready_agents": report["unready_agents"],
        "unready_processes": report["unready_processes"],
        "decision_authority": "aureon_internal",
        "codex_role": "senior_review_and_veto_only",
        "codex_implementation_allowed": False,
        "tools_enabled": False,
        "action_eligible": False,
        "economic_eligible": False,
        "passports": report["passports"],
    }


__all__ = [
    "CANONICAL_AGENT_COMPANY_ROLE_COUNT",
    "REGISTRY_ONLY_AGENT_COMPANY_DEPARTMENTS",
    "SCHEMA_VERSION",
    "VALID_BRAIN_LANES",
    "brain_lane_for_role",
    "canonical_agent_company_brain_topology",
    "company_brain_fabric_report",
    "provision_agent_company_brain_fabric",
    "validate_agent_company_brain_topology",
]
