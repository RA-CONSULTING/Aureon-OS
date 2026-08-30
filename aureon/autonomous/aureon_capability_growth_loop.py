"""Aureon's safe capability growth loop.

This is the controller for the repeatable cycle the organism needs:

audit -> benchmark -> score domains -> detect gaps -> author improvements
-> queue internal work -> write memory -> repeat.

The loop deliberately stays inside local, safe boundaries. It can generate and
validate new SkillLibrary skills and queue work orders for the organism, but it
does not place trades, submit accounts, pay money, expose secrets, or force a
restart. Code changes to the repo still go through the tested patch/restart
path; learned skills can be stored as validated local capabilities.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Sequence

SCHEMA_VERSION = "aureon-capability-growth-loop-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_capability_growth_loop.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_capability_growth_loop.json")
DEFAULT_STATE_PATH = Path("state/capability_growth_loop.json")
DEFAULT_CONTRACT_STATE = Path("state/capability_growth_contracts.json")
DEFAULT_SKILL_DIR = Path("state/capability_growth_skills")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/capability_growth_loop.md")

SAFE_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_ALLOW_SIM_FALLBACK": "0",
    "AUREON_QUIET_STARTUP": "1",
}

DOMAIN_ORDER = (
    "repo_self_catalog",
    "repo_organization",
    "whole_mind_wiring",
    "goal_contracts",
    "self_questioning_llm_vault",
    "code_architect_skill_authoring",
    "public_website_design",
    "trading_cognition",
    "accounting_compliance",
    "research_vault",
    "hnc_saas_security",
    "operator_surfaces",
    "ignition_runtime",
    "validation_benchmarking",
)


@dataclass
class BenchmarkCheck:
    id: str
    command: list[str]
    status: str
    returncode: int
    duration_s: float
    stdout_tail: str = ""
    stderr_tail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DomainCapability:
    id: str
    name: str
    status: str
    score: float
    systems: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    improvement_hint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CapabilityGap:
    id: str
    domain: str
    title: str
    severity: str
    priority: int
    evidence: list[str]
    proposed_skill_name: str
    proposed_action: str
    route: str
    status: str = "planned"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuthoredImprovement:
    skill_name: str
    domain: str
    status: str
    validation_ok: bool
    registered: bool
    storage_path: str
    code_preview: str
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GrowthIteration:
    index: int
    started_at: str
    status: str
    domains: list[DomainCapability]
    gaps: list[CapabilityGap]
    authored_improvements: list[AuthoredImprovement]
    contract_plan: dict[str, Any]
    benchmark_checks: list[BenchmarkCheck]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "started_at": self.started_at,
            "status": self.status,
            "domains": [item.to_dict() for item in self.domains],
            "gaps": [item.to_dict() for item in self.gaps],
            "authored_improvements": [item.to_dict() for item in self.authored_improvements],
            "contract_plan": dict(self.contract_plan),
            "benchmark_checks": [item.to_dict() for item in self.benchmark_checks],
            "summary": dict(self.summary),
        }


@dataclass
class CapabilityGrowthReport:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    iterations: list[GrowthIteration]
    summary: dict[str, Any]
    safety: dict[str, Any]
    vault_memory: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "iterations": [item.to_dict() for item in self.iterations],
            "summary": dict(self.summary),
            "safety": dict(self.safety),
            "vault_memory": dict(self.vault_memory),
            "notes": list(self.notes),
        }


def repo_root_from(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "aureon").is_dir() and (candidate / "scripts").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def apply_safe_environment() -> dict[str, str]:
    os.environ.update(SAFE_ENV)
    try:
        from aureon.core.aureon_runtime_safety import apply_safe_runtime_environment

        apply_safe_runtime_environment(os.environ)
    except Exception:
        pass
    return {key: os.environ.get(key, "") for key in SAFE_ENV}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(parsed, dict):
            return parsed
        return {
            "error": "JSON root must be an object",
            "path": str(path),
        }
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "path": str(path)}


def status_score(status: str) -> float:
    text = (status or "").lower()
    if "blocked" in text or "missing" in text or "failed" in text:
        return 0.20
    if "safe_simulation" in text:
        return 0.82
    if "attention" in text or "partial" in text:
        return 0.72
    if "working" in text or "complete" in text or "organized" in text or "ready" in text:
        return 1.0
    if text in {"present", "ok", "pass", "passed"}:
        return 1.0
    return 0.50


def _proof(readiness: dict[str, Any], proof_id: str) -> dict[str, Any]:
    for proof in readiness.get("proofs") or []:
        if isinstance(proof, dict) and proof.get("id") == proof_id:
            return proof
    return {}


def _domain_from_proof(
    readiness: dict[str, Any],
    proof_id: str,
    *,
    name: str,
    hint: str,
    systems: list[str] | None = None,
    domain_id: str | None = None,
) -> DomainCapability:
    resolved_id = domain_id or proof_id
    proof = _proof(readiness, proof_id)
    if not proof:
        return DomainCapability(
            id=resolved_id,
            name=name,
            status="missing",
            score=0.20,
            systems=systems or [],
            evidence={"proof_available": False},
            improvement_hint=hint,
        )
    status = proof.get("status") or "unknown"
    return DomainCapability(
        id=resolved_id,
        name=name,
        status=status,
        score=status_score(status),
        systems=proof.get("systems") or systems or [],
        evidence={
            "summary": proof.get("summary"),
            "evidence": proof.get("evidence") or {},
            "safety_boundary": proof.get("safety_boundary"),
        },
        improvement_hint=hint,
    )


def code_architect_capability(root: Path) -> DomainCapability:
    try:
        from aureon.code_architect import CodeArchitect, SkillLibrary

        library = SkillLibrary(storage_dir=root / DEFAULT_SKILL_DIR)
        architect = CodeArchitect(library=library, auto_wire=False)
        status = architect.get_status()
        score = 1.0 if status.get("validator") and status.get("library") else 0.72
        return DomainCapability(
            id="code_architect_skill_authoring",
            name="Code Architect Skill Authoring",
            status="working" if score >= 1.0 else "working_with_attention",
            score=score,
            systems=["CodeArchitect", "SkillLibrary", "SkillValidator", "SkillWriter"],
            evidence={"architect_status": status, "skill_library_path": str(library.library_path)},
            improvement_hint="Generate and validate skills for domain gaps, then promote stable skills into the active library.",
        )
    except Exception as exc:
        return DomainCapability(
            id="code_architect_skill_authoring",
            name="Code Architect Skill Authoring",
            status="blocked_or_missing",
            score=0.20,
            systems=["CodeArchitect", "SkillLibrary", "SkillValidator"],
            evidence={"error": f"{type(exc).__name__}: {exc}"},
            improvement_hint="Repair CodeArchitect imports and SkillLibrary persistence.",
        )


def validation_capability(benchmark_checks: Sequence[BenchmarkCheck]) -> DomainCapability:
    if not benchmark_checks:
        return DomainCapability(
            id="validation_benchmarking",
            name="Validation And Benchmark Loop",
            status="working_with_attention",
            score=0.72,
            systems=["pytest", "compileall", "benchmark reports", "capability growth loop"],
            evidence={"checks_run": 0, "note": "No checks were run in this cycle."},
            improvement_hint="Run safe focused tests and benchmarks in the growth loop, then feed failures back as gaps.",
        )
    failed = [item for item in benchmark_checks if item.status != "passed"]
    return DomainCapability(
        id="validation_benchmarking",
        name="Validation And Benchmark Loop",
        status="working" if not failed else "blocked_or_missing",
        score=1.0 if not failed else 0.20,
        systems=["pytest", "compileall", "benchmark reports", "capability growth loop"],
        evidence={
            "checks_run": len(benchmark_checks),
            "failed_checks": [item.id for item in failed],
        },
        improvement_hint="Convert failed checks into work orders and re-run after fixes.",
    )


def public_website_design_capability(root: Path) -> DomainCapability:
    from aureon.autonomous.aureon_coding_agent_skill_base import (
        website_source_rationalisation_readiness,
    )

    source_rationalisation = website_source_rationalisation_readiness(root)
    required = [
        root / "website",
        root / "aureon" / "operator" / "website_operator.py",
        root / "aureon" / "operator" / "live_surface_reconciliation.py",
        root / "aureon" / "operator" / "owner_source_reconciliation.py",
        root / "aureon" / "operator" / "website_source_rationalisation.py",
        root / "tools" / "run-website-source-rationalisation.py",
        root / "aureon" / "operator" / "website_runtime_optimisation.py",
        root / "tools" / "run-website-runtime-optimisation.py",
        root / "aureon" / "operator" / "website_runtime_measurement_provenance.py",
        root / "tools" / "run-website-runtime-measurement-provenance.py",
        root / "data" / "website_operator" / "browser_acceptance_contract.v1.json",
        root / "tools" / "aureon_research_hydration_attribution.js",
        root / "aureon" / "operator" / "design_capability_registry.py",
        root / "aureon" / "operator" / "design_research_refresh.py",
        root / "aureon" / "operator" / "design_evidence_brief.py",
        root / "aureon" / "operator" / "design_investor_copy_governance.py",
        root / "aureon" / "autonomous" / "aureon_public_website_design_runner.py",
        root / "aureon" / "autonomous" / "aureon_staged_design_worker_broker.py",
        root / "aureon" / "operator" / "design_candidate_control.py",
        root / "aureon" / "operator" / "design_candidate_initial_gate.py",
        root / "aureon" / "operator" / "secure_immutable_artifact.py",
        root / "aureon" / "operator" / "design_candidate_static_qa.py",
        root / "aureon" / "operator" / "design_candidate_motion_policy_compiler.py",
        root / "aureon" / "operator" / "design_candidate_test_policy_compiler.py",
        root / "aureon" / "operator" / "design_candidate_source_closure.py",
        root / "aureon" / "operator" / "design_motion_performance_budget.py",
        root / "aureon" / "operator" / "design_candidate_test_evidence.py",
        root / "aureon" / "operator" / "design_candidate_visual_review.py",
        root / "aureon" / "operator" / "design_learning_ledger.py",
        root / "aureon" / "autonomous" / "aureon_capability_forge.py",
        root / "skills" / "aureon-harmonic-design-suite" / "SKILL.md",
        root / "data" / "website_operator" / "investor_site_design_brief.v1.json",
        root / "data" / "website_operator" / "design_research_sources.v1.json",
        root / "tools" / "aureon_website_visual_qa_v28.js",
        root / "docs" / "runbooks" / "DESIGN_MOTION_PERFORMANCE_BUDGET.md",
        root / "docs" / "runbooks" / "DESIGN_CANDIDATE_TEST_EVIDENCE.md",
        root / "docs" / "runbooks" / "SECURE_IMMUTABLE_ARTIFACT.md",
        root / "docs" / "runbooks" / "DESIGN_CANDIDATE_STATIC_QA.md",
        root / "docs" / "runbooks" / "DESIGN_CANDIDATE_MOTION_POLICY_COMPILER.md",
        root / "docs" / "runbooks" / "DESIGN_CANDIDATE_TEST_POLICY_COMPILER.md",
        root / "docs" / "runbooks" / "WEBSITE_SOURCE_RATIONALISATION.md",
        root / "docs" / "runbooks" / "WEBSITE_RUNTIME_OPTIMISATION.md",
        root / "docs" / "research" / "AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_V2_RUNBOOK.md",
        root
        / "docs"
        / "research"
        / "schemas"
        / "AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_RUNNER_V2.schema.json",
        root
        / "docs"
        / "research"
        / "schemas"
        / "AUREON_WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_V1.schema.json",
        root / "tests" / "test_website_source_rationalisation.py",
        root / "tests" / "test_website_runtime_optimisation.py",
        root / "tests" / "test_website_runtime_measurement_provenance.py",
    ]
    present = [path.relative_to(root).as_posix() for path in required if path.exists()]
    missing = [path.relative_to(root).as_posix() for path in required if not path.exists()]
    receipts = (
        sorted(
            (root / "artifacts" / "website-operator").glob("*-design-cycle-*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        if (root / "artifacts" / "website-operator").is_dir()
        else []
    )
    latest = load_json(receipts[0]) if receipts else {}
    local_gate_pass = bool(latest.get("hard_gates_pass"))
    nexus_score = float((latest.get("design_nexus") or {}).get("score") or 0.0)
    registry_evidence: dict[str, Any] = {
        "available": False,
        "verified": False,
        "schema": "",
        "source_hashes": [],
        "authority": {},
        "release_eligible": False,
        "deployment_authority": "none",
        "design_research_refresh_readiness": {
            "available": False,
            "state": "unavailable",
            "current": False,
            "planning_signal_available": False,
            "candidate_delivery_ready": False,
            "delivery_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "website_runtime_optimisation_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "proposal_compilation_protocol_available": False,
            "measurement_validation_protocol_available": False,
            "measurement_validation_scope": "unavailable",
            "measurement_provenance_verification_available": False,
            "production_compilation_blocked": True,
            "production_compilation_blocker": ("blocked-reviewed-measurement-provenance-tool-not-installed"),
            "browser_acceptance_contract_available": False,
            "measurement_schema_available": False,
            "proposal_schema_available": False,
            "proposal_compilation_executed": False,
            "measurement_validation_executed": False,
            "source_selection_required": True,
            "autonomous_source_selection": False,
            "measurement_evidence_required": True,
            "autonomous_measurement_evidence": False,
            "transformations_executed": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "website_runtime_measurement_static_integrity_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "capability_scope": "read-validate-only",
            "static_integrity_validation_available": False,
            "static_integrity_validation_executed": False,
            "measurement_provenance_verification_available": False,
            "production_eligible": False,
            "eligible_for_proposal_compilation": False,
            "production_compilation_blocked": True,
            "worker_available": False,
            "worker_executed": False,
            "artifact_emission_available": False,
            "artifact_emission_executed": False,
            "trusted_static_integrity_execution_path": "unavailable",
            "imported_api_authoritative": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "design_evidence_brief_readiness": {
            "available": False,
            "brief_ready": False,
            "planning_pipeline_available": False,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "staged_design_worker_broker_readiness": {
            "available": False,
            "state": "unavailable",
            "lease_protocol_available": False,
            "candidate_delivery_ready": False,
            "canonical_website_mutation": "never",
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
        },
        "investor_copy_governance_readiness": {
            "available": False,
            "state": "unavailable",
            "decision_verification_available": False,
            "simulation_available": False,
            "apply_protocol_available": False,
            "implementation_tooling_verified": False,
            "exact_owner_decision_required": True,
            "autonomous_owner_decision": False,
            "broad_access_approval_valid": False,
            "current_owner_decision_present": False,
            "current_apply_authorised": False,
            "current_apply_ready": False,
            "website_mutation": "never",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "motion_performance_budget_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "audit_protocol_available": False,
            "receipt_replay_available": False,
            "audit_executed": False,
            "decision_status": "not-evaluated",
            "decision_passed": False,
            "eligible_for_next_local_gate": False,
            "pass_inferred_from_installation": False,
            "candidate_validation_authority": "none",
            "promotion_authority": "none",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "candidate_test_evidence_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "execution_protocol_available": False,
            "structural_verification_available": False,
            "reviewed_node_toolchain": {
                "protocol_available": False,
                "schema": "aureon.node-toolchain-binding.v1",
                "locator_authority": "reviewed-source-pinned-absolute-path-no-path-fallback",
                "absolute_path_size_sha256_bound": False,
                "ambient_path_fallback_allowed": False,
                "resolved": False,
                "executed": False,
            },
            "bounded_process": {
                "protocol_available": False,
                "launcher": "subprocess.Popen",
                "shell": False,
                "max_stream_bytes": 2 * 1024 * 1024,
                "retry_authority": "none",
                "executed": False,
            },
            "execution_authorised": False,
            "test_suite_executed": False,
            "worker_pass_strings_are_evidence": False,
            "origin_attested": False,
            "trusted_orchestration_seal_required": True,
            "evidence_passed": False,
            "pass_inferred_from_installation": False,
            "candidate_validation_authority": "none",
            "promotion_authority": "none",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "candidate_qa_control_plane_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "static_qa_available": False,
            "fixed_test_policy_compiler_available": False,
            "fixed_motion_policy_compiler_available": False,
            "handle_bound_immutable_writer_available": False,
            "v2_runner_available": False,
            "candidate_test_evidence_runtime_available": False,
            "compiler_verification_ingress": {
                "discovery_mode": "metadata-only-no-subprocess",
                "discovery_subprocess_launched": False,
                "imported_api": {
                    "scope": "drift-check-only",
                    "motion_read_only_verifier_available": False,
                    "test_read_only_verifier_available": False,
                    "pre_import_source_authentication": False,
                },
                "sealed_direct_file_read_only": {
                    "protocol_available": False,
                    "motion_protocol_available": False,
                    "test_protocol_available": False,
                    "executed": False,
                    "python_flags": ["-I", "-S", "-B"],
                    "motion_verify_flag": "--verify-config",
                    "test_verify_flag": "--verify-policy",
                    "source_closure_helper_available": False,
                },
                "runner_delegation": {
                    "protocol_available": False,
                    "required_for_candidate_qa": True,
                    "bounded_popen_protocol_available": False,
                    "launcher": "subprocess.Popen",
                    "shell": False,
                    "timeout_seconds": 300,
                    "max_aggregate_output_bytes": 64 * 1024,
                    "retry_authority": "none",
                    "invoked": False,
                },
            },
            "execution_order_enforced": False,
            "qa_execution_authorised": False,
            "qa_executed": False,
            "qa_passed": False,
            "pass_inferred_from_installation": False,
            "candidate_creation_authority": "none",
            "candidate_mutation_authority": "none",
            "candidate_validation_authority": "none",
            "canonical_website_mutation": "none",
            "promotion_authority": "none",
            "package_authority": "none",
            "release_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "error": "",
    }
    try:
        from aureon.operator.design_capability_registry import discover_design_capability_registry

        registry = discover_design_capability_registry(root)
        verification = registry.get("verification")
        authority = registry.get("authority")
        research_refresh_readiness = registry.get("design_research_refresh_readiness")
        if not isinstance(research_refresh_readiness, dict):
            research_refresh_readiness = registry_evidence["design_research_refresh_readiness"]
        runtime_optimisation_readiness = registry.get("website_runtime_optimisation_readiness")
        if not isinstance(runtime_optimisation_readiness, dict):
            runtime_optimisation_readiness = registry_evidence["website_runtime_optimisation_readiness"]
        runtime_measurement_static_integrity_readiness = registry.get(
            "website_runtime_measurement_static_integrity_readiness"
        )
        if not isinstance(runtime_measurement_static_integrity_readiness, dict):
            runtime_measurement_static_integrity_readiness = registry_evidence[
                "website_runtime_measurement_static_integrity_readiness"
            ]
        brief_readiness = registry.get("design_evidence_brief_readiness")
        if not isinstance(brief_readiness, dict):
            brief_readiness = registry_evidence["design_evidence_brief_readiness"]
        staged_worker_broker_readiness = registry.get("staged_design_worker_broker_readiness")
        if not isinstance(staged_worker_broker_readiness, dict):
            staged_worker_broker_readiness = registry_evidence["staged_design_worker_broker_readiness"]
        investor_copy_governance_readiness = registry.get("investor_copy_governance_readiness")
        if not isinstance(investor_copy_governance_readiness, dict):
            investor_copy_governance_readiness = registry_evidence["investor_copy_governance_readiness"]
        motion_budget_readiness = registry.get("motion_performance_budget_readiness")
        if not isinstance(motion_budget_readiness, dict):
            motion_budget_readiness = registry_evidence["motion_performance_budget_readiness"]
        candidate_test_readiness = registry.get("candidate_test_evidence_readiness")
        if not isinstance(candidate_test_readiness, dict):
            candidate_test_readiness = registry_evidence["candidate_test_evidence_readiness"]
        candidate_qa_readiness = registry.get("candidate_qa_control_plane_readiness")
        if not isinstance(candidate_qa_readiness, dict):
            candidate_qa_readiness = registry_evidence["candidate_qa_control_plane_readiness"]
        registry_verified = (
            isinstance(verification, dict)
            and verification.get("passed") is True
            and verification.get("release_eligible") is False
            and verification.get("deployment_authority") == "none"
            and isinstance(authority, dict)
            and authority.get("release_eligibility") == "always-false"
            and authority.get("deployment_authority") == "none"
            and authority.get("release_authority") == "WebsiteOperator owner gate only"
        )
        source_hashes = [
            {
                "id": item.get("id"),
                "path": item.get("path"),
                "sha256": item.get("sha256"),
            }
            for item in registry.get("sources", [])
            if isinstance(item, dict)
        ]
        registry_evidence.update(
            {
                "available": True,
                "verified": registry_verified,
                "schema": str(registry.get("schema") or ""),
                "source_hashes": source_hashes,
                "authority": authority if isinstance(authority, dict) else {},
                "verification": verification if isinstance(verification, dict) else {},
                "design_research_refresh_readiness": research_refresh_readiness,
                "website_runtime_optimisation_readiness": runtime_optimisation_readiness,
                "website_runtime_measurement_static_integrity_readiness": (
                    runtime_measurement_static_integrity_readiness
                ),
                "design_evidence_brief_readiness": brief_readiness,
                "staged_design_worker_broker_readiness": staged_worker_broker_readiness,
                "investor_copy_governance_readiness": investor_copy_governance_readiness,
                "motion_performance_budget_readiness": motion_budget_readiness,
                "candidate_test_evidence_readiness": candidate_test_readiness,
                "candidate_qa_control_plane_readiness": candidate_qa_readiness,
            }
        )
    except Exception as exc:
        registry_evidence["error"] = f"{type(exc).__name__}: {exc}"

    brief_ready = bool(registry_evidence["design_evidence_brief_readiness"].get("brief_ready"))
    research_refresh_current = bool(registry_evidence["design_research_refresh_readiness"].get("current"))
    runtime_optimisation_protocol_available = bool(
        registry_evidence["website_runtime_optimisation_readiness"].get(
            "proposal_compilation_protocol_available"
        )
        and registry_evidence["website_runtime_optimisation_readiness"].get(
            "measurement_validation_protocol_available"
        )
        and registry_evidence["website_runtime_optimisation_readiness"].get(
            "browser_acceptance_contract_available"
        )
        and registry_evidence["website_runtime_optimisation_readiness"].get("measurement_schema_available")
        and registry_evidence["website_runtime_optimisation_readiness"].get("proposal_schema_available")
        and registry_evidence["website_runtime_optimisation_readiness"].get("transformations_executed")
        is False
    )
    runtime_measurement_static_integrity_available = bool(
        registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
            "static_integrity_validation_available"
        )
        and registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
            "static_integrity_validation_executed"
        )
        is False
        and registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
            "measurement_provenance_verification_available"
        )
        is False
        and registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
            "production_eligible"
        )
        is False
        and registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
            "worker_available"
        )
        is False
        and registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
            "trusted_static_integrity_execution_path"
        )
        == "fresh-isolated-launcher-only"
        and registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
            "imported_api_authoritative"
        )
        is False
    )
    staged_worker_broker_protocol_available = bool(
        registry_evidence["staged_design_worker_broker_readiness"].get("lease_protocol_available")
    )
    investor_copy_governance_verification_available = bool(
        registry_evidence["investor_copy_governance_readiness"].get("decision_verification_available")
    )
    motion_budget_protocol_available = bool(
        registry_evidence["motion_performance_budget_readiness"].get("audit_protocol_available")
    )
    candidate_test_node = registry_evidence["candidate_test_evidence_readiness"].get(
        "reviewed_node_toolchain"
    )
    if not isinstance(candidate_test_node, dict):
        candidate_test_node = {}
    candidate_test_process = registry_evidence["candidate_test_evidence_readiness"].get("bounded_process")
    if not isinstance(candidate_test_process, dict):
        candidate_test_process = {}
    candidate_test_node_available = bool(
        candidate_test_node.get("protocol_available") is True
        and candidate_test_node.get("schema") == "aureon.node-toolchain-binding.v1"
        and candidate_test_node.get("locator_authority")
        == "reviewed-source-pinned-absolute-path-no-path-fallback"
        and candidate_test_node.get("absolute_path_size_sha256_bound") is True
        and candidate_test_node.get("ambient_path_fallback_allowed") is False
        and candidate_test_node.get("resolved") is False
        and candidate_test_node.get("executed") is False
    )
    candidate_test_bounded_popen_available = bool(
        candidate_test_process.get("protocol_available") is True
        and candidate_test_process.get("launcher") == "subprocess.Popen"
        and candidate_test_process.get("shell") is False
        and candidate_test_process.get("max_stream_bytes") == 2 * 1024 * 1024
        and candidate_test_process.get("retry_authority") == "none"
        and candidate_test_process.get("executed") is False
    )
    candidate_test_protocol_available = bool(
        registry_evidence["candidate_test_evidence_readiness"].get("execution_protocol_available")
        and registry_evidence["candidate_test_evidence_readiness"].get("structural_verification_available")
        and candidate_test_node_available
        and candidate_test_bounded_popen_available
    )
    candidate_qa_ingress = registry_evidence["candidate_qa_control_plane_readiness"].get(
        "compiler_verification_ingress"
    )
    if not isinstance(candidate_qa_ingress, dict):
        candidate_qa_ingress = {}
    imported_compiler_api = candidate_qa_ingress.get("imported_api")
    if not isinstance(imported_compiler_api, dict):
        imported_compiler_api = {}
    sealed_compiler_verification = candidate_qa_ingress.get("sealed_direct_file_read_only")
    if not isinstance(sealed_compiler_verification, dict):
        sealed_compiler_verification = {}
    sealed_runner_delegation = candidate_qa_ingress.get("runner_delegation")
    if not isinstance(sealed_runner_delegation, dict):
        sealed_runner_delegation = {}
    imported_compiler_drift_checks_available = bool(
        imported_compiler_api.get("scope") == "drift-check-only"
        and imported_compiler_api.get("motion_read_only_verifier_available")
        and imported_compiler_api.get("test_read_only_verifier_available")
        and imported_compiler_api.get("pre_import_source_authentication") is False
    )
    sealed_compiler_read_only_protocol_available = bool(
        sealed_compiler_verification.get("protocol_available") is True
        and sealed_compiler_verification.get("motion_protocol_available") is True
        and sealed_compiler_verification.get("test_protocol_available") is True
        and sealed_compiler_verification.get("executed") is False
        and sealed_compiler_verification.get("python_flags") == ["-I", "-S", "-B"]
        and sealed_compiler_verification.get("motion_verify_flag") == "--verify-config"
        and sealed_compiler_verification.get("test_verify_flag") == "--verify-policy"
        and sealed_compiler_verification.get("source_closure_helper_available") is True
    )
    sealed_compiler_runner_delegation_available = bool(
        sealed_runner_delegation.get("protocol_available") is True
        and sealed_runner_delegation.get("required_for_candidate_qa") is True
        and sealed_runner_delegation.get("bounded_popen_protocol_available") is True
        and sealed_runner_delegation.get("launcher") == "subprocess.Popen"
        and sealed_runner_delegation.get("shell") is False
        and sealed_runner_delegation.get("timeout_seconds") == 300
        and sealed_runner_delegation.get("max_aggregate_output_bytes") == 64 * 1024
        and sealed_runner_delegation.get("retry_authority") == "none"
        and sealed_runner_delegation.get("invoked") is False
    )
    candidate_qa_control_plane_available = bool(
        registry_evidence["candidate_qa_control_plane_readiness"].get("available")
        and registry_evidence["candidate_qa_control_plane_readiness"].get("state")
        == "installed-not-authorised"
        and registry_evidence["candidate_qa_control_plane_readiness"].get("execution_order_enforced")
        and registry_evidence["candidate_qa_control_plane_readiness"].get(
            "candidate_test_evidence_runtime_available"
        )
        and candidate_qa_ingress.get("discovery_mode") == "metadata-only-no-subprocess"
        and imported_compiler_drift_checks_available
        and sealed_compiler_read_only_protocol_available
        and sealed_compiler_runner_delegation_available
        and candidate_qa_ingress.get("discovery_subprocess_launched") is False
    )
    if not registry_evidence["verified"]:
        score = 0.20
        status = "blocked_or_missing"
    elif local_gate_pass and nexus_score > 0 and brief_ready:
        score = min(1.0, nexus_score / 100.0)
        status = "working"
    elif not missing:
        score = 0.72
        status = "working_with_attention"
    else:
        score = 0.20
        status = "blocked_or_missing"
    return DomainCapability(
        id="public_website_design",
        name="Public Website Design Nexus",
        status=status,
        score=score,
        systems=[
            "WebsiteOperator",
            "LiveSurfaceReconciliation (read-only public HTTPS drift sensing)",
            "OwnerSourceReconciliation (owner decision plus verified backup for observed live drift)",
            "WebsiteSourceRationalisation (proposal-only planning and exact owner-decision validation for PublicWebsiteDesignQA; no discovery execution or staging authority)",
            "WebsiteRuntimeOptimisation (structural declaration validation and test-fixture-only projection arithmetic; production proposal compilation and writing remain blocked)",
            "WebsiteRuntimeMeasurementStaticIntegrity (QA-only fresh isolated-launcher validation of explicit existing artifacts; imported APIs non-authoritative, provenance unverified, production blocked)",
            "ResearchRouteLayoutAttribution (single runtime-only temporal diagnostic)",
            "DesignCapabilityRegistry (read-only)",
            "DesignResearchRefresh (redacted planning freshness; no delivery or release authority)",
            "DesignEvidenceBrief (source-bound planning contract; no candidate or release authority)",
            "PublicWebsiteDesignDeliveryRunner (immutable staged receipts; owner promotion excluded)",
            "StagedDesignWorkerBroker (explicit short-lived lease and text-only staged manifest; no canonical, credential, package, release, or deployment authority)",
            "InvestorCopyGovernance (read-only verify/simulate; exact named-owner gated three-file apply; broad access invalid; no website, package, release, or deployment authority)",
            "AureonCapabilityForge.website_design",
            "GoalExecutionEngine.public_website_design_cycle",
            "Aureon Harmonic Design Suite",
            "DesignCandidateControl (staged V30+ candidates)",
            "DesignCandidateInitialGate (source-bound performance feedback)",
            "DesignMotionPerformanceBudget (installed static evidence protocol; pass requires decision.status pass and eligible_for_next_local_gate true)",
            "DesignCandidateTestEvidence (installed-not-authorised; worker pass strings excluded; trusted orchestration seal plus evidence_passed required)",
            "CandidateQAControlPlane (metadata-only discovery; imported drift checks separated from runner-delegated sealed direct-file read-only verification; no inferred pass)",
            "DesignCandidateVisualReview (staged pre-promotion evidence)",
            "DesignLearningLedger (append-only human-reviewed skill proposal)",
            "public-site browser and dependency-closure gates",
        ],
        evidence={
            "present_surfaces": present,
            "missing_surfaces": missing,
            "latest_design_cycle": str(receipts[0]) if receipts else "",
            "latest_hard_gates_pass": local_gate_pass,
            "latest_design_nexus_score": nexus_score,
            "design_capability_registry": registry_evidence,
            "website_source_rationalisation_readiness": source_rationalisation,
            "source_rationalisation_planning_protocol_available": bool(
                source_rationalisation.get("planning_protocol_available")
            ),
            "source_rationalisation_owner_decision_validation_protocol_available": bool(
                source_rationalisation.get("owner_decision_validation_protocol_available")
            ),
            "source_rationalisation_planning_executed_during_discovery": False,
            "source_rationalisation_validation_executed_during_discovery": False,
            "source_rationalisation_autonomous_owner_decision": False,
            "source_rationalisation_text_worker_authority": "none",
            "source_rationalisation_staging_authority": "none",
            "source_rationalisation_physical_deletion_authority": "none",
            "source_rationalisation_candidate_authority": "none",
            "source_rationalisation_canonical_authority": "none",
            "source_rationalisation_package_authority": "none",
            "source_rationalisation_release_eligible": False,
            "source_rationalisation_deployment_authority": "none",
            "source_rationalisation_credential_access": "none",
            "source_rationalisation_network_access": "none",
            "source_rationalisation_omission_proves_readiness": False,
            "website_runtime_optimisation_readiness": registry_evidence[
                "website_runtime_optimisation_readiness"
            ],
            "runtime_optimisation_protocol_available": runtime_optimisation_protocol_available,
            "runtime_optimisation_measurement_schema_available": bool(
                registry_evidence["website_runtime_optimisation_readiness"].get(
                    "measurement_schema_available"
                )
            ),
            "runtime_optimisation_proposal_schema_available": bool(
                registry_evidence["website_runtime_optimisation_readiness"].get("proposal_schema_available")
            ),
            "runtime_optimisation_measurement_provenance_verified": bool(
                registry_evidence["website_runtime_optimisation_readiness"].get(
                    "measurement_provenance_verification_available"
                )
            ),
            "runtime_optimisation_production_compilation_blocked": bool(
                registry_evidence["website_runtime_optimisation_readiness"].get(
                    "production_compilation_blocked", True
                )
            ),
            "runtime_optimisation_discovery_execution": False,
            "runtime_optimisation_autonomous_source_selection": False,
            "runtime_optimisation_autonomous_measurement_evidence": False,
            "runtime_optimisation_transformations_executed": False,
            "runtime_optimisation_candidate_authority": "none",
            "runtime_optimisation_package_authority": "none",
            "runtime_optimisation_release_eligible": False,
            "runtime_optimisation_deployment_authority": "none",
            "website_runtime_measurement_static_integrity_readiness": registry_evidence[
                "website_runtime_measurement_static_integrity_readiness"
            ],
            "runtime_measurement_static_integrity_available": (
                runtime_measurement_static_integrity_available
            ),
            "runtime_measurement_static_integrity_executed": bool(
                registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
                    "static_integrity_validation_executed"
                )
            ),
            "runtime_measurement_static_integrity_provenance_verified": bool(
                registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
                    "measurement_provenance_verification_available"
                )
            ),
            "runtime_measurement_static_integrity_production_eligible": bool(
                registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
                    "production_eligible"
                )
            ),
            "runtime_measurement_static_integrity_worker_available": bool(
                registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
                    "worker_available"
                )
            ),
            "runtime_measurement_static_integrity_artifact_emission_available": bool(
                registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
                    "artifact_emission_available"
                )
            ),
            "runtime_measurement_static_integrity_execution_path": (
                registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
                    "trusted_static_integrity_execution_path"
                )
                or "unavailable"
            ),
            "runtime_measurement_static_integrity_imported_api_authoritative": bool(
                registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
                    "imported_api_authoritative"
                )
            ),
            "runtime_measurement_static_integrity_proves_producer_execution": False,
            "runtime_measurement_static_integrity_proves_full_decode_or_freshness": False,
            "runtime_measurement_static_integrity_deployment_authority": (
                registry_evidence["website_runtime_measurement_static_integrity_readiness"].get(
                    "deployment_authority"
                )
                or "none"
            ),
            "research_refresh_current": research_refresh_current,
            "brief_ready": brief_ready,
            "planning_pipeline_available": bool(
                registry_evidence["design_evidence_brief_readiness"].get("planning_pipeline_available")
            ),
            "staged_worker_broker_protocol_available": staged_worker_broker_protocol_available,
            "investor_copy_governance_verification_available": (
                investor_copy_governance_verification_available
            ),
            "motion_performance_budget_protocol_available": motion_budget_protocol_available,
            "motion_performance_budget_passed": False,
            "candidate_test_evidence_protocol_available": candidate_test_protocol_available,
            "candidate_test_reviewed_node_toolchain_available": candidate_test_node_available,
            "candidate_test_bounded_popen_available": candidate_test_bounded_popen_available,
            "candidate_test_evidence_origin_attested": False,
            "candidate_test_evidence_passed": False,
            "candidate_qa_control_plane_available": candidate_qa_control_plane_available,
            "imported_compiler_drift_check_apis_available": imported_compiler_drift_checks_available,
            "sealed_compiler_read_only_protocol_available": (sealed_compiler_read_only_protocol_available),
            "sealed_compiler_runner_delegation_available": (sealed_compiler_runner_delegation_available),
            "candidate_qa_discovery_subprocess_launched": bool(
                candidate_qa_ingress.get("discovery_subprocess_launched")
            ),
            "sealed_compiler_read_only_verification_executed": False,
            "sealed_compiler_runner_delegation_invoked": False,
            "candidate_qa_executed": False,
            "candidate_qa_passed": False,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        improvement_hint=(
            "Restore the source-bound design capability registry and its non-authoritative boundary before "
            "planning any local design work; a named human visual reviewer and WebsiteOperator owner gate "
            "remain mandatory."
            if not registry_evidence["verified"]
            else "Refresh or repair the redacted design-research source control and source-bound design-evidence brief before deriving any staged candidate scope; a passing brief remains planning-only, and named human visual review plus the WebsiteOperator owner gate remain mandatory."
            if not brief_ready
            else "Run the source-bound design cycle, close objective council vetoes, refresh official "
            "benchmarks, treat imported compiler APIs as drift checks only, delegate sealed direct-file "
            "read-only replay under python -I -S -B through the V2 runner, and use the one-attempt chain in its enforced "
            "motion-first then trusted-test then browser order, require exact passing receipts rather "
            "than worker pass strings, prove dependency closure, "
            "and keep deployment owner-gated."
        ),
    )


def audit_goal_capability_snapshot(root: Path) -> dict[str, Any]:
    """Build the goal map only after activating this loop's audit boundary.

    The map is part of the wider runtime organism and can wire optional
    observability components at import time.  This loop is explicitly a local,
    no-side-effect audit surface, so importing it must never start or contact a
    runtime component.  Delaying the import until after the safe environment is
    applied preserves the map's normal runtime behaviour while keeping design
    and capability audits passive.
    """
    apply_safe_environment()
    from aureon.autonomous.aureon_goal_capability_map import build_goal_capability_map

    snapshot: dict[str, Any] = build_goal_capability_map(
        repo_root=root,
        current_goal=(
            "test benchmark audit fix capabilities, write improvements, "
            "repeat, self catalog, self enhancement, accounting, trading, research, hardened SaaS security"
        ),
    ).to_dict()
    return snapshot


def collect_domain_capabilities(
    root: Path,
    benchmark_checks: Sequence[BenchmarkCheck] = (),
) -> list[DomainCapability]:
    audits = root / "docs" / "audits"
    readiness = load_json(audits / "aureon_system_readiness_audit.json")
    self_catalog = load_json(audits / "aureon_repo_self_catalog.json")
    mind = load_json(audits / "mind_wiring_audit.json")
    goal_map = audit_goal_capability_snapshot(root)

    catalog_summary = self_catalog.get("summary") or {}
    catalog_files = int(catalog_summary.get("cataloged_file_count") or 0)
    catalog_status = self_catalog.get("status") or "missing"
    mind_counts = mind.get("counts") or {}
    mind_bad = sum(int(mind_counts.get(key) or 0) for key in ("partial", "broken", "unknown"))

    domains = [
        DomainCapability(
            id="repo_self_catalog",
            name="Repo Self-Catalog",
            status=catalog_status if catalog_files else "missing",
            score=1.0 if catalog_files and not (catalog_summary.get("truncated")) else 0.20,
            systems=["AureonRepoSelfCatalog", "Obsidian repo self-catalog note", "per-file LLM context"],
            evidence={
                "cataloged_file_count": catalog_files,
                "subsystem_count": catalog_summary.get("subsystem_count"),
                "secret_metadata_only_count": catalog_summary.get("secret_metadata_only_count"),
                "coverage_policy": catalog_summary.get("coverage_policy"),
            },
            improvement_hint="Regenerate after code/data changes and use labels in self-questioning prompts.",
        ),
        _domain_from_proof(
            readiness,
            "repo_organization",
            name="Repo Organization",
            hint="Clear unstaged/attention ownership items or explicitly preserve them.",
        ),
        DomainCapability(
            id="whole_mind_wiring",
            name="Whole-Mind Wiring",
            status="working" if mind_counts and mind_bad == 0 else "working_with_attention",
            score=1.0 if mind_counts and mind_bad == 0 else 0.72,
            systems=["MindWiringAudit", "organism_spine", "ThoughtBus", "local service probes"],
            evidence={"counts": mind_counts},
            improvement_hint="Route any broken/partial/unknown systems into repair contracts.",
        ),
        _domain_from_proof(
            readiness,
            "goal_routing",
            name="Goal, Skill, Task, And Route Brain",
            hint="Ensure all major goal types map to safe route surfaces.",
            systems=["GoalCapabilityMap", "OrganismContractStack"],
            domain_id="goal_contracts",
        ),
        DomainCapability(
            id="self_questioning_llm_vault",
            name="Self-Questioning LLM And Vault",
            status=_proof(readiness, "llm_capability").get("status") or "missing",
            score=status_score(_proof(readiness, "llm_capability").get("status") or "missing"),
            systems=[
                "SelfQuestioningAI",
                "OllamaBridge",
                "AureonHybridAdapter",
                "ObsidianBridge",
                "repo_self_catalog context",
            ],
            evidence={
                "llm_proof": _proof(readiness, "llm_capability"),
                "research_vault": _proof(readiness, "research_vault"),
                "route_has_self_catalog": "self_catalog" in (goal_map.get("route_surfaces") or {}),
            },
            improvement_hint="Keep local LLM/vault available and feed self-catalog/accounting/trading evidence into prompts.",
        ),
        code_architect_capability(root),
        public_website_design_capability(root),
        _domain_from_proof(
            readiness,
            "trading_brain",
            name="Trading Cognition",
            hint="Improve simulation, sizing, ETA verification, and safety gates before live paths.",
            domain_id="trading_cognition",
        ),
        _domain_from_proof(
            readiness,
            "accounting_brain",
            name="Accounting Compliance",
            hint="Close attention items, evidence gaps, and generated pack validation loops.",
            domain_id="accounting_compliance",
        ),
        _domain_from_proof(
            readiness,
            "research_vault",
            name="Research And Vault Memory",
            hint="Expand corpus retrieval, source linking, and vault ingestion.",
        ),
        _domain_from_proof(
            readiness,
            "hnc_saas_security",
            name="HNC SaaS Security Architect",
            hint="Implement tenant isolation, LLM/tool governance, zero-trust, and release-gate evidence before deployment.",
            systems=["HNCSaaSSecurityArchitect", "OrganismContractStack", "OWASP ASVS", "NIST zero trust"],
        ),
        _domain_from_proof(
            readiness,
            "operator_surfaces",
            name="Operator Surfaces",
            hint="Keep command center, frontend, and local service health checks reachable.",
            domain_id="operator_surfaces",
        ),
        _domain_from_proof(
            readiness,
            "ignition",
            name="Ignition Runtime",
            hint="Keep single boot preflight and safe live profile checks passing.",
            domain_id="ignition_runtime",
        ),
        validation_capability(benchmark_checks),
    ]
    return sorted(domains, key=lambda item: DOMAIN_ORDER.index(item.id) if item.id in DOMAIN_ORDER else 99)


def gap_for_domain(domain: DomainCapability) -> CapabilityGap | None:
    if domain.score >= 0.90 and "attention" not in domain.status.lower():
        return None
    severity = "high" if domain.score < 0.50 else "medium"
    priority = 5 if severity == "high" else 3
    action = (
        f"Run safe audit/benchmark/fix loop for {domain.id}; use {', '.join(domain.systems[:4])}; "
        "write findings to vault and queue re-test."
    )
    return CapabilityGap(
        id=f"gap_{domain.id}",
        domain=domain.id,
        title=f"Improve {domain.name}",
        severity=severity,
        priority=priority,
        evidence=[
            f"status={domain.status}",
            f"score={domain.score:.2f}",
            domain.improvement_hint,
        ],
        proposed_skill_name=f"improve_{domain.id}",
        proposed_action=action,
        route="capability_growth_loop",
    )


def detect_capability_gaps(domains: Sequence[DomainCapability]) -> list[CapabilityGap]:
    gaps = [gap for domain in domains if (gap := gap_for_domain(domain))]
    gaps.sort(key=lambda item: (-item.priority, item.domain))
    return gaps


def safe_skill_code(gap: CapabilityGap) -> str:
    return (
        f"def {gap.proposed_skill_name}(**kwargs):\n"
        f'    """Plan a safe improvement cycle for {gap.domain}."""\n'
        "    return {\n"
        f"        'domain': {gap.domain!r},\n"
        f"        'title': {gap.title!r},\n"
        "        'cycle': ['audit', 'benchmark', 'fix', 'retest', 'write_memory'],\n"
        f"        'proposed_action': {gap.proposed_action!r},\n"
        "        'safety': {\n"
        "            'live_orders': 'blocked',\n"
        "            'official_filing': 'manual_only',\n"
        "            'payments': 'manual_only',\n"
        "            'secrets': 'metadata_only',\n"
        "        },\n"
        "        'input': dict(kwargs),\n"
        "    }\n"
    )


def author_improvement_skills(
    root: Path, gaps: Sequence[CapabilityGap], limit: int = 8
) -> list[AuthoredImprovement]:
    authored: list[AuthoredImprovement] = []
    try:
        from aureon.code_architect import (
            Skill,
            SkillLevel,
            SkillLibrary,
            SkillProposal,
            SkillStatus,
            SkillValidator,
        )
    except Exception as exc:
        return [
            AuthoredImprovement(
                skill_name="code_architect_unavailable",
                domain="code_architect_skill_authoring",
                status="blocked",
                validation_ok=False,
                registered=False,
                storage_path="",
                code_preview="",
                error=f"{type(exc).__name__}: {exc}",
            )
        ]

    library = SkillLibrary(storage_dir=root / DEFAULT_SKILL_DIR)
    validator = SkillValidator(strict_static=True)
    for gap in list(gaps)[: max(0, limit)]:
        code = safe_skill_code(gap)
        proposal = SkillProposal(
            name=gap.proposed_skill_name,
            description=gap.title,
            level=SkillLevel.TASK,
            category="capability_growth",
            code=code,
            entry_function=gap.proposed_skill_name,
            params_schema={"type": "object", "properties": {}},
            dependencies=[],
            observation_sources=[gap.id],
            reasoning="Generated by Aureon capability growth loop from audit/benchmark gap evidence.",
            target="local",
        )
        try:
            static_ok, static_errors = validator.static_check(proposal.code)
            skill = Skill.from_proposal(proposal)
            skill.queen_verdict = "STATIC_SAFE"
            skill.queen_confidence = 0.5
            skill.pillar_alignment_score = 0.5
            skill.pillar_lighthouse = False
            skill.harmonic_signature = {"capability_growth": 1.0}
            skill.status = SkillStatus.VALIDATED if static_ok else SkillStatus.BLOCKED
            if static_ok:
                library.add(skill, persist=False)
            authored.append(
                AuthoredImprovement(
                    skill_name=proposal.name,
                    domain=gap.domain,
                    status=skill.status.value if static_ok else "blocked",
                    validation_ok=bool(static_ok),
                    registered=bool(static_ok),
                    storage_path=str(library.library_path),
                    code_preview=code[:500],
                    error="" if static_ok else f"static_check failed: {static_errors[:3]}",
                )
            )
        except Exception as exc:
            authored.append(
                AuthoredImprovement(
                    skill_name=proposal.name,
                    domain=gap.domain,
                    status="blocked",
                    validation_ok=False,
                    registered=False,
                    storage_path=str(library.library_path),
                    code_preview=code[:500],
                    error=f"{type(exc).__name__}: {exc}",
                )
            )
    if authored:
        library.save()
    return authored


def queue_growth_contracts(
    root: Path,
    gaps: Sequence[CapabilityGap],
    authored: Sequence[AuthoredImprovement],
    *,
    queue_contracts: bool,
) -> dict[str, Any]:
    if not queue_contracts:
        return {"queued_persistently": False, "gap_count": len(gaps), "authored_skill_count": len(authored)}
    try:
        from aureon.core.organism_contracts import OrganismContractStack

        stack = OrganismContractStack(
            state_path=root / DEFAULT_CONTRACT_STATE,
            source="capability_growth_loop",
        )
        workflow = stack.create_goal_workflow(
            "Continuously audit, benchmark, fix, and retest Aureon capabilities across every domain.",
            skills=[item.skill_name for item in authored if item.registered],
            route_surfaces=[
                "capability_growth",
                "self_enhancement",
                "self_catalog",
                "contracts",
                "validation",
            ],
            source="capability_growth_loop",
        )
        authored_by_domain = {item.domain: item.skill_name for item in authored if item.registered}
        gap_work_orders: list[dict[str, Any]] = []
        for gap in gaps:
            wo = stack.enqueue_work_order(
                f"Improve capability domain: {gap.domain}",
                "execute_internal_task",
                queue="organism.capability_growth",
                priority=gap.priority,
                payload={
                    "gap": gap.to_dict(),
                    "recommended_skill": authored_by_domain.get(gap.domain, gap.proposed_skill_name),
                    "cycle": ["audit", "benchmark", "fix", "retest", "write_memory"],
                },
                source="capability_growth_loop",
            )
            gap_work_orders.append(wo.to_dict())
        status = stack.publish_status()
        return {
            "queued_persistently": True,
            "state_path": str(root / DEFAULT_CONTRACT_STATE),
            "workflow": workflow,
            "gap_work_orders": gap_work_orders,
            "status": status,
        }
    except Exception as exc:
        return {"queued_persistently": False, "error": f"{type(exc).__name__}: {exc}"}


def default_benchmark_commands(root: Path, python_exe: str) -> list[tuple[str, list[str]]]:
    return [
        (
            "compile_growth_loop",
            [
                python_exe,
                "-m",
                "compileall",
                "aureon/autonomous/aureon_capability_growth_loop.py",
                "tests/test_capability_growth_loop.py",
            ],
        ),
        (
            "focused_growth_tests",
            [
                python_exe,
                "-m",
                "pytest",
                "tests/test_capability_growth_loop.py",
                "-q",
            ],
        ),
        (
            "focused_public_website_design_tests",
            [
                python_exe,
                "-m",
                "pytest",
                "tests/test_website_operator.py",
                "tests/test_aureon_capability_forge.py",
                "tests/test_coding_agent_skill_base.py",
                "tests/test_design_capability_registry.py",
                "tests/test_design_evidence_brief.py",
                "tests/test_design_agent_capability_integration.py",
                "tests/test_design_motion_performance_budget.py",
                "tests/test_design_candidate_test_evidence.py",
                "tests/test_secure_immutable_artifact.py",
                "tests/test_design_candidate_static_qa.py",
                "tests/test_design_candidate_motion_policy_compiler.py",
                "tests/test_design_candidate_test_policy_compiler.py",
                "tests/test_design_candidate_source_closure.py",
                "tests/test_public_website_design_runner.py",
                "tests/test_website_source_rationalisation.py",
                "tests/test_website_runtime_optimisation.py",
                "tests/test_website_runtime_measurement_provenance.py",
                "-q",
            ],
        ),
        (
            "compile_public_website_design_qa_capabilities",
            [
                python_exe,
                "-m",
                "compileall",
                "aureon/operator/design_motion_performance_budget.py",
                "aureon/operator/design_candidate_test_evidence.py",
                "aureon/operator/secure_immutable_artifact.py",
                "aureon/operator/design_candidate_static_qa.py",
                "aureon/operator/design_candidate_motion_policy_compiler.py",
                "aureon/operator/design_candidate_test_policy_compiler.py",
                "aureon/operator/design_candidate_source_closure.py",
                "aureon/operator/website_source_rationalisation.py",
                "tools/run-website-source-rationalisation.py",
                "aureon/operator/website_runtime_optimisation.py",
                "tools/run-website-runtime-optimisation.py",
                "aureon/operator/website_runtime_measurement_provenance.py",
                "tools/run-website-runtime-measurement-provenance.py",
                "aureon/autonomous/aureon_public_website_design_runner.py",
                "aureon/operator/design_capability_registry.py",
                "aureon/autonomous/aureon_coding_agent_skill_base.py",
                "aureon/autonomous/aureon_capability_forge.py",
                "tests/test_website_source_rationalisation.py",
                "tests/test_website_runtime_optimisation.py",
                "tests/test_website_runtime_measurement_provenance.py",
            ],
        ),
    ]


def run_benchmark_checks(
    root: Path,
    commands: Sequence[tuple[str, list[str]]],
    *,
    timeout_s: int = 120,
    runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> list[BenchmarkCheck]:
    env = os.environ.copy()
    env.update(SAFE_ENV)
    run = runner or subprocess.run
    checks: list[BenchmarkCheck] = []
    for check_id, command in commands:
        start = time.time()
        try:
            completed = run(
                command,
                cwd=str(root),
                env=env,
                text=True,
                capture_output=True,
                timeout=timeout_s,
            )
            duration = time.time() - start
            checks.append(
                BenchmarkCheck(
                    id=check_id,
                    command=list(command),
                    status="passed" if completed.returncode == 0 else "failed",
                    returncode=int(completed.returncode),
                    duration_s=round(duration, 3),
                    stdout_tail=(completed.stdout or "")[-2000:],
                    stderr_tail=(completed.stderr or "")[-2000:],
                )
            )
        except subprocess.TimeoutExpired as exc:
            checks.append(
                BenchmarkCheck(
                    id=check_id,
                    command=list(command),
                    status="timeout",
                    returncode=124,
                    duration_s=round(time.time() - start, 3),
                    stdout_tail=str(exc.stdout or "")[-2000:],
                    stderr_tail=str(exc.stderr or "")[-2000:],
                )
            )
    return checks


def build_iteration(
    root: Path,
    index: int,
    *,
    benchmark_checks: Sequence[BenchmarkCheck] = (),
    author_skills: bool = False,
    queue_contracts: bool = False,
    max_gaps: int = 8,
) -> GrowthIteration:
    started = utc_now()
    domains = collect_domain_capabilities(root, benchmark_checks=benchmark_checks)
    gaps = detect_capability_gaps(domains)[: max(0, max_gaps)]
    authored = author_improvement_skills(root, gaps, limit=max_gaps) if author_skills else []
    contract_plan = queue_growth_contracts(root, gaps, authored, queue_contracts=queue_contracts)
    blocked_domains = [item for item in domains if item.score < 0.50]
    attention_domains = [item for item in domains if item.score < 0.90 or "attention" in item.status.lower()]
    failed_checks = [item for item in benchmark_checks if item.status != "passed"]
    if blocked_domains or failed_checks:
        status = "needs_repair"
    elif attention_domains:
        status = "working_with_growth_items"
    else:
        status = "working_and_expanding"
    summary = {
        "domain_count": len(domains),
        "gap_count": len(gaps),
        "blocked_domain_count": len(blocked_domains),
        "attention_domain_count": len(attention_domains),
        "authored_improvement_count": len(authored),
        "registered_improvement_count": sum(1 for item in authored if item.registered),
        "benchmark_check_count": len(benchmark_checks),
        "failed_benchmark_count": len(failed_checks),
        "mean_score": round(sum(item.score for item in domains) / max(1, len(domains)), 3),
    }
    return GrowthIteration(
        index=index,
        started_at=started,
        status=status,
        domains=domains,
        gaps=gaps,
        authored_improvements=authored,
        contract_plan=contract_plan,
        benchmark_checks=list(benchmark_checks),
        summary=summary,
    )


def build_capability_growth_loop(
    repo_root: Path | None = None,
    *,
    iterations: int = 1,
    run_checks: bool = False,
    author_skills: bool = False,
    queue_contracts: bool = False,
    max_gaps: int = 8,
    python_exe: str | None = None,
) -> CapabilityGrowthReport:
    root = repo_root_from(repo_root)
    safe = apply_safe_environment()
    py = python_exe or sys.executable
    iteration_reports: list[GrowthIteration] = []
    benchmark_checks: list[BenchmarkCheck] = []
    for index in range(1, max(1, iterations) + 1):
        if run_checks:
            benchmark_checks = run_benchmark_checks(root, default_benchmark_commands(root, py))
        iteration_reports.append(
            build_iteration(
                root,
                index,
                benchmark_checks=benchmark_checks,
                author_skills=author_skills,
                queue_contracts=queue_contracts,
                max_gaps=max_gaps,
            )
        )
    latest = iteration_reports[-1]
    blocked = latest.summary.get("blocked_domain_count", 0)
    failed = latest.summary.get("failed_benchmark_count", 0)
    if blocked or failed:
        status = "growth_loop_needs_repair"
    elif latest.summary.get("gap_count", 0):
        status = "growth_loop_working_with_improvement_queue"
    else:
        status = "growth_loop_working_clean"
    vault_path = root / DEFAULT_VAULT_NOTE
    summary = {
        "iteration_count": len(iteration_reports),
        "latest_status": latest.status,
        "latest_gap_count": latest.summary.get("gap_count", 0),
        "latest_mean_score": latest.summary.get("mean_score", 0),
        "latest_registered_improvement_count": latest.summary.get("registered_improvement_count", 0),
        "latest_benchmark_check_count": latest.summary.get("benchmark_check_count", 0),
        "latest_failed_benchmark_count": latest.summary.get("failed_benchmark_count", 0),
        "contract_queue_persisted": bool(latest.contract_plan.get("queued_persistently")),
        "skill_authoring_enabled": bool(author_skills),
    }
    report = CapabilityGrowthReport(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(root),
        status=status,
        iterations=iteration_reports,
        summary=summary,
        safety={
            **safe,
            "live_orders_allowed": False,
            "official_filing_manual_only": True,
            "payments_manual_only": True,
            "repo_code_patch_requires_tests_and_restart_handoff": True,
        },
        vault_memory={
            "status": "planned",
            "note_path": str(vault_path),
            "topic": "capability.growth.ready",
            "cycle": ["audit", "benchmark", "fix", "retest", "write_memory", "repeat"],
        },
        notes=[
            "This is the organism-level improvement loop across trading, accounting, research, cognition, LLM, vault, frontend, and runtime domains.",
            "HNC SaaS security joins the loop as a hardened zero-trust design and release-gate domain, not a promise of literal unhackability.",
            "The loop can author safe SkillLibrary improvements and queue work orders; repo patches still require tests and restart handoff.",
            "Live trading, official filing, payments, and secret exposure are not capabilities granted by this loop.",
        ],
    )
    return report


def render_markdown(report: CapabilityGrowthReport) -> str:
    def esc(value: Any) -> str:
        return str(value).replace("|", "\\|")

    lines: list[str] = []
    lines.append("# Aureon Capability Growth Loop")
    lines.append("")
    lines.append(f"- Generated: `{report.generated_at}`")
    lines.append(f"- Repo: `{report.repo_root}`")
    lines.append(f"- Status: `{report.status}`")
    lines.append(
        "- Safety: audit/simulation/local skill authoring only; no live orders, official filing, payments, or secret exposure"
    )
    lines.append("")
    lines.append("## Loop")
    lines.append("")
    lines.append(
        "`audit -> benchmark -> score domains -> detect gaps -> author improvements -> queue work -> write memory -> repeat`"
    )
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in report.summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    latest = report.iterations[-1]
    lines.append("## Domain Scores")
    lines.append("")
    lines.append("| Domain | Status | Score | Improvement hint |")
    lines.append("| --- | --- | ---: | --- |")
    for domain in latest.domains:
        lines.append(
            f"| {esc(domain.name)} | `{domain.status}` | {domain.score:.2f} | {esc(domain.improvement_hint)} |"
        )
    lines.append("")
    lines.append("## Improvement Queue")
    lines.append("")
    lines.append("| Priority | Gap | Domain | Proposed skill | Route |")
    lines.append("| ---: | --- | --- | --- | --- |")
    for gap in latest.gaps:
        lines.append(
            f"| {gap.priority} | {esc(gap.title)} | `{gap.domain}` | `{gap.proposed_skill_name}` | `{gap.route}` |"
        )
    lines.append("")
    if latest.authored_improvements:
        lines.append("## Authored Improvements")
        lines.append("")
        lines.append("| Skill | Domain | Status | Registered |")
        lines.append("| --- | --- | --- | --- |")
        for item in latest.authored_improvements:
            lines.append(f"| `{item.skill_name}` | `{item.domain}` | `{item.status}` | `{item.registered}` |")
        lines.append("")
    if latest.benchmark_checks:
        lines.append("## Benchmark Checks")
        lines.append("")
        lines.append("| Check | Status | Seconds | Return code |")
        lines.append("| --- | --- | ---: | ---: |")
        for check in latest.benchmark_checks:
            lines.append(f"| `{check.id}` | `{check.status}` | {check.duration_s:.3f} | {check.returncode} |")
        lines.append("")
    lines.append("## Contract Plan")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(latest.contract_plan, indent=2, sort_keys=True, default=str)[:2600])
    lines.append("```")
    lines.append("")
    lines.append("## Vault Memory")
    lines.append("")
    for key, value in report.vault_memory.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def render_vault_note(report: CapabilityGrowthReport) -> str:
    latest = report.iterations[-1]
    lines = [
        "# Aureon Capability Growth Loop",
        "",
        "This note is the compact vault memory for the organism's repeatable improvement loop.",
        "",
        f"- Generated: `{report.generated_at}`",
        f"- Status: `{report.status}`",
        f"- Latest gaps: `{latest.summary.get('gap_count', 0)}`",
        f"- Latest mean score: `{latest.summary.get('mean_score', 0)}`",
        f"- Registered improvements: `{latest.summary.get('registered_improvement_count', 0)}`",
        "- Cycle: `audit -> benchmark -> fix -> retest -> write_memory -> repeat`",
        "",
        "## Current Improvement Focus",
        "",
    ]
    for gap in latest.gaps[:12]:
        lines.append(f"- `{gap.domain}`: {gap.title} via `{gap.proposed_skill_name}`")
    lines.append("")
    lines.append("Use `docs/audits/aureon_capability_growth_loop.json` for full evidence.")
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: CapabilityGrowthReport,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
    state_path: Path = DEFAULT_STATE_PATH,
    *,
    write_vault: bool = True,
) -> tuple[Path, Path, Path, Path | None]:
    root = Path(report.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    st_path = state_path if state_path.is_absolute() else root / state_path
    vault_path: Path | None = None
    if write_vault:
        vault_path = Path(report.vault_memory["note_path"])
        report.vault_memory["status"] = "written"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.parent.mkdir(parents=True, exist_ok=True)
    st_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(report), encoding="utf-8")
    payload = json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str)
    js_path.write_text(payload, encoding="utf-8")
    st_path.write_text(payload, encoding="utf-8")
    if vault_path:
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        vault_path.write_text(render_vault_note(report), encoding="utf-8")
    return md_path, js_path, st_path, vault_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Aureon's safe capability growth loop.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--iterations", type=int, default=1, help="Number of growth iterations.")
    parser.add_argument(
        "--run-checks", action="store_true", help="Run safe focused benchmark/check commands."
    )
    parser.add_argument(
        "--author-skills",
        action="store_true",
        help="Generate validated local SkillLibrary improvement skills.",
    )
    parser.add_argument("--queue-contracts", action="store_true", help="Persist improvement work orders.")
    parser.add_argument("--max-gaps", type=int, default=8, help="Maximum gaps to turn into improvements.")
    parser.add_argument("--python", default="", help="Python executable for check commands.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--state", default=str(DEFAULT_STATE_PATH), help="State JSON path.")
    parser.add_argument("--no-vault", action="store_true", help="Do not write the compact vault note.")
    parser.add_argument("--no-write", action="store_true", help="Print summary only.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    report = build_capability_growth_loop(
        root,
        iterations=args.iterations,
        run_checks=args.run_checks,
        author_skills=args.author_skills,
        queue_contracts=args.queue_contracts,
        max_gaps=args.max_gaps,
        python_exe=args.python or None,
    )
    if args.no_write:
        print(json.dumps({"status": report.status, "summary": report.summary}, indent=2, sort_keys=True))
    else:
        md_path, js_path, state_path, vault_path = write_report(
            report,
            Path(args.markdown),
            Path(args.json),
            Path(args.state),
            write_vault=not args.no_vault,
        )
        print(
            json.dumps(
                {
                    "status": report.status,
                    "markdown": str(md_path),
                    "json": str(js_path),
                    "state": str(state_path),
                    "vault_note": str(vault_path) if vault_path else "",
                    "summary": report.summary,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 2 if report.status == "growth_loop_needs_repair" else 0


if __name__ == "__main__":
    raise SystemExit(main())
