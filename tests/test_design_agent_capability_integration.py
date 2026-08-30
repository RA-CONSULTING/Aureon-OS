"""Focused integration guarantees for the non-authoritative design-agent path."""

from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous import aureon_capability_forge as capability_forge
from aureon.autonomous.aureon_capability_growth_loop import public_website_design_capability
from aureon.autonomous.aureon_coding_agent_skill_base import (
    coder_agent_roles,
    public_website_design_registry_snapshot,
    public_website_design_skill_stack,
)
from aureon.operator.website_operator import WebsiteOperator

REPO_ROOT = Path(__file__).resolve().parents[1]


def _verified_registry() -> dict:
    return {
        "available": True,
        "verified": True,
        "release_eligible": False,
        "deployment_authority": "none",
        "human_visual_acceptance": "required for material brand changes",
        "owner_release_boundary": "WebsiteOperator owner gate only",
        "schema": "aureon.design-capability-registry.v1",
        "authority": {
            "release_eligibility": "always-false",
            "deployment_authority": "none",
            "release_authority": "WebsiteOperator owner gate only",
        },
        "sources": [
            {
                "id": "coding-agent-skill-base",
                "path": "aureon/autonomous/aureon_coding_agent_skill_base.py",
                "sha256": "A" * 64,
            }
        ],
        "owner_source_reconciliation_readiness": {
            "available": True,
            "installed": True,
            "state": "installed-owner-decision-required",
            "validation_protocol_available": True,
            "v1_retain_local_supported": True,
            "v2_verified_live_backup_supported": True,
            "owner_decision_required": True,
            "autonomous_source_selection": False,
            "candidate_delivery_ready": False,
            "canonical_website_mutation": "none",
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
        },
        "design_research_refresh_readiness": {
            "available": True,
            "state": "current",
            "current": True,
            "planning_signal_available": True,
            "candidate_delivery_ready": False,
            "delivery_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
            "declaration": {
                "path": "data/website_operator/design_research_sources.v1.json",
                "sha256": "B" * 64,
            },
            "artwork": {"state": "not-cleared", "cleared_for_use": False},
        },
        "stakeholder_feedback_readiness": {
            "available": True,
            "installed": True,
            "state": "current",
            "current": True,
            "planning_only": True,
            "planning_signal_available": True,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "release_authority": "none",
            "package_authority": "none",
            "deployment_authority": "none",
            "raw_correspondence_access": "none",
            "declaration": {
                "feedback_id": "investor-site-signals-20260730",
                "path": "data/website_operator/design_stakeholder_feedback.v1.json",
                "sha256": "C" * 64,
            },
            "freshness": {
                "state": "current",
                "issued_at": "2026-07-29T23:45:00Z",
                "refresh_by": "2026-08-13T23:59:59Z",
            },
            "signal_capsules_sha256": "D" * 64,
            "summary": {
                "signal_count": 7,
                "action_requested_count": 5,
                "no_action_count": 1,
            },
            "response_manifest_required": True,
        },
        "editorial_rights_decision_preparation_readiness": {
            "available": True,
            "installed": True,
            "state": "installed-explicit-human-decision-required",
            "preparation_protocol_available": True,
            "human_decision_input_required": True,
            "autonomous_human_decision": False,
            "rights_inference": "never",
            "canonical_manifest_mutation": "never",
            "global_artwork_policy_mutation": "never",
            "candidate_use_rights_ready": False,
            "candidate_asset_ready": False,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
            "network_access": "none",
            "connector_access": "none",
        },
        "investor_copy_repair_readiness": {
            "available": True,
            "installed": True,
            "state": "installed-awaiting-exact-design-copy-task",
            "source_bound_protocol_available": True,
            "task_preflight_available": True,
            "selected_source_preflight_available": True,
            "contract_creation_available": True,
            "contract_verification_available": True,
            "candidate_reaudit_available": True,
            "current_contract_ready": False,
            "candidate_copy_ready": False,
            "candidate_delivery_ready": False,
            "canonical_website_mutation": "never",
            "candidate_staging": "never",
            "claim_register_mutation": "never",
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
            "network_access": "none",
        },
        "investor_copy_governance_readiness": {
            "available": True,
            "installed": True,
            "state": "installed-exact-owner-decision-required",
            "decision_verification_available": True,
            "simulation_available": True,
            "apply_protocol_available": True,
            "implementation_tooling_verified": True,
            "exact_owner_decision_required": True,
            "autonomous_owner_decision": False,
            "broad_access_approval_valid": False,
            "current_owner_decision_present": False,
            "current_apply_authorised": False,
            "current_apply_ready": False,
            "website_mutation": "never",
            "policy_mutation": "never",
            "candidate_authority": "none",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
            "credential_access": "none",
            "network_access": "none",
        },
        "design_evidence_brief_readiness": {
            "available": True,
            "state": "brief-ready",
            "brief_ready": True,
            "planning_pipeline_available": True,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "motion_performance_budget_readiness": {
            "available": True,
            "installed": True,
            "state": "installed-not-authorised",
            "audit_protocol_available": True,
            "receipt_replay_available": True,
            "audit_executed": False,
            "decision_status": "not-evaluated",
            "decision_passed": False,
            "eligible_for_next_local_gate": False,
            "pass_inferred_from_installation": False,
            "candidate_authority": "none",
            "candidate_validation_authority": "none",
            "promotion_authority": "none",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "candidate_test_evidence_readiness": {
            "available": True,
            "installed": True,
            "state": "installed-not-authorised",
            "execution_protocol_available": True,
            "structural_verification_available": True,
            "immutable_writer_available": True,
            "reviewed_node_toolchain": {
                "protocol_available": True,
                "schema": "aureon.node-toolchain-binding.v1",
                "locator_authority": "reviewed-source-pinned-absolute-path-no-path-fallback",
                "absolute_path_size_sha256_bound": True,
                "ambient_path_fallback_allowed": False,
                "resolved": False,
                "executed": False,
            },
            "bounded_process": {
                "protocol_available": True,
                "launcher": "subprocess.Popen",
                "shell": False,
                "max_stream_bytes": 2 * 1024 * 1024,
                "retry_authority": "none",
                "executed": False,
            },
            "execution_authorised": False,
            "test_suite_executed": False,
            "worker_pass_strings_are_evidence": False,
            "structural_verification_passed": False,
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
            "available": True,
            "installed": True,
            "state": "installed-not-authorised",
            "static_qa_available": True,
            "fixed_test_policy_compiler_available": True,
            "fixed_motion_policy_compiler_available": True,
            "handle_bound_immutable_writer_available": True,
            "v2_runner_available": True,
            "candidate_test_evidence_runtime_available": True,
            "execution_order_enforced": True,
            "execution_order": [
                "compile-fixed-motion-config",
                "compile-fixed-test-policy",
                "run-motion-budget-first",
                "run-complete-trusted-test-policy",
                "enter-initial-browser-gate-only-after-qa-verification",
            ],
            "compiler_verification_ingress": {
                "discovery_mode": "metadata-only-no-subprocess",
                "discovery_subprocess_launched": False,
                "imported_api": {
                    "scope": "drift-check-only",
                    "motion_read_only_verifier_available": True,
                    "test_read_only_verifier_available": True,
                    "pre_import_source_authentication": False,
                },
                "sealed_direct_file_read_only": {
                    "protocol_available": True,
                    "motion_protocol_available": True,
                    "test_protocol_available": True,
                    "executed": False,
                    "python_flags": ["-I", "-S", "-B"],
                    "motion_verify_flag": "--verify-config",
                    "test_verify_flag": "--verify-policy",
                    "source_closure_helper_available": True,
                },
                "runner_delegation": {
                    "protocol_available": True,
                    "required_for_candidate_qa": True,
                    "bounded_popen_protocol_available": True,
                    "launcher": "subprocess.Popen",
                    "shell": False,
                    "timeout_seconds": 300,
                    "max_aggregate_output_bytes": 64 * 1024,
                    "retry_authority": "none",
                    "invoked": False,
                },
            },
            "qa_execution_authorised": False,
            "qa_executed": False,
            "qa_passed": False,
        },
        "verification": {
            "passed": True,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "error": "",
    }


def test_coding_agent_registry_snapshot_is_source_bound_and_non_authoritative() -> None:
    snapshot = public_website_design_registry_snapshot(REPO_ROOT)

    assert snapshot["available"] is True
    assert snapshot["verified"] is True
    assert snapshot["sources"]
    assert snapshot["release_eligible"] is False
    assert snapshot["deployment_authority"] == "none"
    assert snapshot["owner_release_boundary"] == "WebsiteOperator owner gate only"
    owner_source = snapshot["owner_source_reconciliation_readiness"]
    assert owner_source["validation_protocol_available"] is True
    assert owner_source["v1_retain_local_supported"] is True
    assert owner_source["v2_verified_live_backup_supported"] is True
    assert owner_source["owner_decision_required"] is True
    assert owner_source["autonomous_source_selection"] is False
    assert owner_source["candidate_delivery_ready"] is False
    assert owner_source["deployment_authority"] == "none"
    refresh = snapshot["design_research_refresh_readiness"]
    assert refresh["current"] is True
    assert refresh["candidate_delivery_ready"] is False
    assert refresh["delivery_authority"] == "none"
    assert refresh["release_eligible"] is False
    assert refresh["deployment_authority"] == "none"
    feedback = snapshot["stakeholder_feedback_readiness"]
    assert feedback["installed"] is True
    assert feedback["current"] is True
    assert feedback["planning_only"] is True
    assert feedback["planning_signal_available"] is True
    assert feedback["candidate_delivery_ready"] is False
    assert feedback["release_eligible"] is False
    assert feedback["release_authority"] == "none"
    assert feedback["package_authority"] == "none"
    assert feedback["deployment_authority"] == "none"
    assert feedback["raw_correspondence_access"] == "none"
    assert "signals" not in feedback
    assert "signal_capsules" not in feedback
    rights_preparation = snapshot["editorial_rights_decision_preparation_readiness"]
    assert rights_preparation["preparation_protocol_available"] is True
    assert rights_preparation["human_decision_input_required"] is True
    assert rights_preparation["autonomous_human_decision"] is False
    assert rights_preparation["rights_inference"] == "never"
    assert rights_preparation["candidate_use_rights_ready"] is False
    assert rights_preparation["candidate_delivery_ready"] is False
    assert rights_preparation["release_eligible"] is False
    assert rights_preparation["deployment_authority"] == "none"
    editorial_assets = snapshot["editorial_asset_provenance_readiness"]
    assert editorial_assets["installed"] is True
    assert editorial_assets["integrity_verified"] is True
    assert editorial_assets["public_use_ready"] is False
    assert editorial_assets["candidate_use_rights_ready"] is False
    assert editorial_assets["candidate_asset_ready"] is False
    assert editorial_assets["candidate_delivery_ready"] is False
    assert editorial_assets["release_eligible"] is False
    assert editorial_assets["package_authority"] == "none"
    assert editorial_assets["deployment_authority"] == "none"
    assert "assets" not in editorial_assets
    asset_importer = snapshot["editorial_asset_importer_readiness"]
    assert asset_importer["installed"] is True
    assert asset_importer["import_protocol_available"] is True
    assert asset_importer["receipt_verification_available"] is True
    assert asset_importer["candidate_use_rights_ready"] is False
    assert asset_importer["candidate_asset_ready"] is False
    assert asset_importer["candidate_import_ready"] is False
    assert asset_importer["candidate_delivery_ready"] is False
    assert asset_importer["canonical_website_mutation"] == "never"
    assert asset_importer["release_eligible"] is False
    assert asset_importer["package_authority"] == "none"
    assert asset_importer["deployment_authority"] == "none"
    copy_quality = snapshot["investor_copy_quality_readiness"]
    assert copy_quality["installed"] is True
    assert copy_quality["policy_current"] is True
    assert copy_quality["copy_ready"] is False
    assert copy_quality["candidate_delivery_ready"] is False
    assert copy_quality["release_eligible"] is False
    assert "findings" not in copy_quality
    copy_repair = snapshot["investor_copy_repair_readiness"]
    assert copy_repair["source_bound_protocol_available"] is True
    assert copy_repair["task_preflight_available"] is True
    assert copy_repair["selected_source_preflight_available"] is True
    assert copy_repair["contract_verification_available"] is True
    assert copy_repair["candidate_reaudit_available"] is True
    assert copy_repair["current_contract_ready"] is False
    assert copy_repair["candidate_copy_ready"] is False
    assert copy_repair["candidate_delivery_ready"] is False
    assert copy_repair["release_eligible"] is False
    assert copy_repair["deployment_authority"] == "none"
    copy_governance = snapshot["investor_copy_governance_readiness"]
    assert copy_governance["decision_verification_available"] is True
    assert copy_governance["simulation_available"] is True
    assert copy_governance["apply_protocol_available"] is True
    assert copy_governance["implementation_tooling_verified"] is True
    assert copy_governance["exact_owner_decision_required"] is True
    assert copy_governance["autonomous_owner_decision"] is False
    assert copy_governance["broad_access_approval_valid"] is False
    assert copy_governance["current_owner_decision_present"] is False
    assert copy_governance["current_apply_authorised"] is False
    assert copy_governance["current_apply_ready"] is False
    assert copy_governance["website_mutation"] == "never"
    assert copy_governance["policy_mutation"] == "never"
    assert copy_governance["package_authority"] == "none"
    assert copy_governance["release_eligible"] is False
    assert copy_governance["deployment_authority"] == "none"
    hnc_graph = snapshot["hnc_evidence_graph_readiness"]
    assert hnc_graph["installed"] is True
    assert hnc_graph["component_bundle_ready"] is True
    assert hnc_graph["candidate_transplant_ready"] is False
    assert hnc_graph["candidate_delivery_ready"] is False
    assert hnc_graph["release_eligible"] is False
    readiness = snapshot["design_evidence_brief_readiness"]
    assert readiness["brief_ready"] is True
    assert readiness["planning_pipeline_available"] is True
    assert readiness["candidate_delivery_ready"] is False
    assert readiness["release_eligible"] is False
    assert readiness["deployment_authority"] == "none"
    assert readiness["stakeholder_feedback"]["signal_count"] == feedback["summary"]["signal_count"]
    assert "signal_ids" not in readiness["stakeholder_feedback"]
    motion = snapshot["motion_performance_budget_readiness"]
    assert motion["state"] == "installed-not-authorised"
    assert motion["audit_protocol_available"] is True
    assert motion["audit_executed"] is False
    assert motion["decision_passed"] is False
    assert motion["eligible_for_next_local_gate"] is False
    assert motion["candidate_validation_authority"] == "none"
    assert motion["promotion_authority"] == "none"
    assert motion["package_authority"] == "none"
    assert motion["release_eligible"] is False
    assert motion["deployment_authority"] == "none"
    candidate_tests = snapshot["candidate_test_evidence_readiness"]
    assert candidate_tests["state"] == "installed-not-authorised"
    assert candidate_tests["execution_protocol_available"] is True
    assert candidate_tests["reviewed_node_toolchain"]["protocol_available"] is True
    assert candidate_tests["reviewed_node_toolchain"]["ambient_path_fallback_allowed"] is False
    assert candidate_tests["reviewed_node_toolchain"]["resolved"] is False
    assert candidate_tests["bounded_process"]["protocol_available"] is True
    assert candidate_tests["bounded_process"]["launcher"] == "subprocess.Popen"
    assert candidate_tests["bounded_process"]["shell"] is False
    assert candidate_tests["bounded_process"]["executed"] is False
    assert candidate_tests["execution_authorised"] is False
    assert candidate_tests["test_suite_executed"] is False
    assert candidate_tests["worker_pass_strings_are_evidence"] is False
    assert candidate_tests["origin_attested"] is False
    assert candidate_tests["trusted_orchestration_seal_required"] is True
    assert candidate_tests["evidence_passed"] is False
    assert candidate_tests["candidate_validation_authority"] == "none"
    assert candidate_tests["promotion_authority"] == "none"
    assert candidate_tests["package_authority"] == "none"
    assert candidate_tests["release_eligible"] is False
    assert candidate_tests["deployment_authority"] == "none"
    candidate_qa = snapshot["candidate_qa_control_plane_readiness"]
    assert candidate_qa["available"] is True
    ingress = candidate_qa["compiler_verification_ingress"]
    assert ingress["discovery_mode"] == "metadata-only-no-subprocess"
    assert ingress["discovery_subprocess_launched"] is False
    assert ingress["imported_api"]["scope"] == "drift-check-only"
    assert ingress["imported_api"]["pre_import_source_authentication"] is False
    assert ingress["sealed_direct_file_read_only"]["protocol_available"] is True
    assert ingress["sealed_direct_file_read_only"]["executed"] is False
    assert ingress["sealed_direct_file_read_only"]["source_closure_helper_available"] is True
    assert ingress["runner_delegation"]["protocol_available"] is True
    assert ingress["runner_delegation"]["bounded_popen_protocol_available"] is True
    assert ingress["runner_delegation"]["launcher"] == "subprocess.Popen"
    assert ingress["runner_delegation"]["shell"] is False
    assert ingress["runner_delegation"]["retry_authority"] == "none"
    assert ingress["runner_delegation"]["invoked"] is False


def test_coding_skill_stack_binds_privacy_safe_stakeholder_response_closure() -> None:
    stack = public_website_design_skill_stack()

    assert {
        "audit_stakeholder_feedback",
        "validate_owner_source_reconciliation",
        "audit_editorial_asset_provenance",
        "prepare_editorial_asset_rights_decisions",
        "import_verified_editorial_assets_to_staged_candidate",
        "verify_editorial_asset_candidate_import",
        "audit_investor_copy_quality",
        "preflight_investor_copy_repair_contract",
        "preflight_investor_copy_repair_work_order",
        "verify_investor_copy_repair_contract",
        "evaluate_investor_copy_repair_candidate",
        "verify_investor_copy_governance_decision",
        "simulate_investor_copy_governance_application",
        "apply_exact_owner_approved_investor_copy_governance_delta",
        "build_source_neutral_hnc_evidence_graph",
        "audit_motion_performance_budget",
        "replay_motion_performance_budget_receipt",
        "execute_hash_bound_candidate_test_suite",
        "verify_candidate_test_evidence_receipt",
        "inspect_candidate_compiler_verification_ingress",
        "delegate_sealed_read_only_compiler_verification_to_runner",
        "bind_route_feedback_capsules",
        "validate_feedback_response_manifest",
    }.issubset(stack["levels"]["L0_atomic"])
    assert "translate_stakeholder_signals" in stack["levels"]["L1_compound"]
    assert "Stakeholder Insight & Privacy Editor" in stack["levels"]["L4_role"]
    assert "no raw correspondence" in stack["authority"]["design_stakeholder_feedback"]
    assert "broad system-access approval is invalid" in stack["authority"]["investor_copy_governance"]
    assert "no website, policy, candidate, package" in stack["authority"]["investor_copy_governance"]
    assert "decision.status pass" in stack["authority"]["motion_performance_budget"]
    assert "eligible_for_next_local_gate true" in stack["authority"]["motion_performance_budget"]
    assert "worker pass strings are not evidence" in stack["authority"]["candidate_test_evidence"]
    assert "origin_attested false" in stack["authority"]["candidate_test_evidence"]
    assert "evidence_passed true" in stack["authority"]["candidate_test_evidence"]
    assert "drift-check-only" in stack["authority"]["candidate_qa_compiler_verification_ingress"]
    assert "python -I -S -B" in stack["authority"]["candidate_qa_compiler_verification_ingress"]

    worker = next(role for role in coder_agent_roles() if role.name == "PublicWebsiteDesignWorker")
    assert "privacy-safe stakeholder-feedback declaration SHA-256" in worker.evidence_required
    assert "route stakeholder-signal capsule SHA-256" in worker.evidence_required
    assert "complete stakeholder response-manifest SHA-256" in worker.evidence_required
    assert "read raw correspondence" in worker.safety_boundary
    assert "only as the broker-sealed" in worker.safety_boundary
    assert "turn a submitted `passed` string into evidence" in worker.safety_boundary
    qa = next(role for role in coder_agent_roles() if role.name == "PublicWebsiteDesignQA")
    assert "cannot create or edit an owner decision" in qa.safety_boundary
    assert "governance apply" in qa.safety_boundary
    assert "origin attestation" in qa.safety_boundary
    assert "trusted orchestration seal plus evidence_passed true" in qa.safety_boundary
    assert "aureon/operator/design_candidate_source_closure.py" in qa.reads
    assert "Imported compiler verification is drift-check-only" in qa.safety_boundary
    assert "discovery itself launches no subprocess" in qa.safety_boundary


def test_website_design_artifact_requires_registry_before_operator_work(
    tmp_path: Path,
    monkeypatch,
) -> None:
    blocked_registry = _verified_registry()
    blocked_registry["verified"] = False
    blocked_registry["verification"]["passed"] = False
    blocked_registry["error"] = "registered source drift"
    monkeypatch.setattr(
        capability_forge,
        "_design_capability_registry_preflight",
        lambda _root: blocked_registry,
    )

    def should_not_run(cls, **_kwargs):
        raise AssertionError("WebsiteOperator must not run before registry verification")

    monkeypatch.setattr(WebsiteOperator, "from_paths", classmethod(should_not_run))

    artifact = capability_forge._website_design_artifact("Redesign the public website.", tmp_path)

    assert artifact["ok"] is False
    assert artifact["design_cycle"] == {}
    assert artifact["artifact_quality_report"]["handover_ready"] is False
    assert artifact["artifact_quality_report"]["release_eligible"] is False
    assert artifact["artifact_quality_report"]["deployment_authority"] == "none"
    assert artifact["candidate_control"]["available"] is False
    assert artifact["candidate_control"]["canonical_website_mutation"] == "never"
    assert artifact["candidate_control"]["brief_readiness"]["candidate_delivery_ready"] is False
    runner = artifact["candidate_control"]["delivery_runner"]
    assert runner["invoked"] is False
    assert runner["candidate_qa_discovery_subprocess_launched"] is False
    assert runner["sealed_compiler_read_only_delegation_available"] is True
    assert runner["sealed_compiler_read_only_delegation_invoked"] is False
    assert runner["candidate_creation"].startswith("none;")
    assert runner["promotion_authority"] == "none"
    assert runner["deployment_authority"] == "none"
    motion = artifact["candidate_control"]["motion_performance_budget"]
    assert motion["state"] == "installed-not-authorised"
    assert motion["invoked"] is False
    assert motion["audit_executed"] is False
    assert motion["decision_passed"] is False
    assert motion["eligible_for_next_local_gate"] is False
    assert motion["candidate_validation_authority"] == "none"
    assert motion["promotion_authority"] == "none"
    assert motion["package_authority"] == "none"
    assert motion["release_eligible"] is False
    assert motion["deployment_authority"] == "none"
    candidate_tests = artifact["candidate_control"]["candidate_test_evidence"]
    assert candidate_tests["state"] == "installed-not-authorised"
    assert candidate_tests["invoked"] is False
    assert candidate_tests["execution_authorised"] is False
    assert candidate_tests["test_suite_executed"] is False
    assert candidate_tests["worker_pass_strings_are_evidence"] is False
    assert candidate_tests["origin_attested"] is False
    assert candidate_tests["trusted_orchestration_seal_required"] is True
    assert candidate_tests["evidence_passed"] is False
    assert candidate_tests["candidate_validation_authority"] == "none"
    assert candidate_tests["promotion_authority"] == "none"
    assert candidate_tests["package_authority"] == "none"
    assert candidate_tests["release_eligible"] is False
    assert candidate_tests["deployment_authority"] == "none"
    assert artifact["output_files"] == []


def test_website_design_artifact_keeps_human_and_owner_release_gates_after_local_proof(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        capability_forge,
        "_design_capability_registry_preflight",
        lambda _root: _verified_registry(),
    )

    class FakeOperator:
        def __init__(self, root: Path) -> None:
            self.root = root

        def design_cycle(self, *, goal: str, run_external: bool) -> Path:
            assert goal == "Redesign the public website."
            assert run_external is False
            receipt = self.root / "artifacts" / "website-operator" / "design-cycle.json"
            receipt.parent.mkdir(parents=True, exist_ok=True)
            receipt.write_text(
                json.dumps(
                    {
                        "hard_gates": [{"id": "local_design_gate", "passed": True, "evidence": "ok"}],
                        "hard_gates_pass": True,
                        "design_nexus": {"score": 96.0, "minimum_score": 85.0},
                        "iteration": 1,
                        "state": "ready-for-human-review",
                    }
                ),
                encoding="utf-8",
            )
            return receipt

    def fake_from_paths(cls, *, repo_root: Path) -> FakeOperator:
        return FakeOperator(repo_root)

    monkeypatch.setattr(WebsiteOperator, "from_paths", classmethod(fake_from_paths))

    artifact = capability_forge._website_design_artifact("Redesign the public website.", tmp_path)
    quality = artifact["artifact_quality_report"]

    assert artifact["ok"] is True
    assert quality["handover_ready"] is True
    assert quality["release_eligible"] is False
    assert quality["deployment_authority"] == "none"
    assert "Named human visual acceptance" in quality["next_required_gate"]
    assert "WebsiteOperator owner gate" in quality["next_required_gate"]
    assert artifact["design_capability_registry"]["verified"] is True
    assert artifact["candidate_control"]["available"] is True
    assert artifact["candidate_control"]["release_eligible"] is False
    assert artifact["candidate_control"]["deployment_authority"] == "none"
    brief_readiness = artifact["candidate_control"]["brief_readiness"]
    assert brief_readiness["brief_ready"] is True
    assert brief_readiness["planning_pipeline_available"] is True
    assert brief_readiness["candidate_delivery_ready"] is False
    assert brief_readiness["candidate_creation"].startswith("none;")
    runner = artifact["candidate_control"]["delivery_runner"]
    assert runner["module"] == "aureon.autonomous.aureon_public_website_design_runner"
    assert runner["available"] is True
    assert runner["invoked"] is False
    assert runner["candidate_creation"].startswith("none;")
    assert runner["candidate_staged"] is False
    assert runner["canonical_website_mutation"] == "never"
    assert runner["promotion_authority"] == "none"
    assert runner["terminal_boundary"] == "awaiting-owner-promotion"
    assert runner["release_eligible"] is False
    assert runner["deployment_authority"] == "none"
    motion = artifact["candidate_control"]["motion_performance_budget"]
    assert motion["available"] is True
    assert motion["state"] == "installed-not-authorised"
    assert motion["invoked"] is False
    assert motion["decision_status"] == "not-evaluated"
    assert motion["decision_passed"] is False
    assert motion["eligible_for_next_local_gate"] is False
    assert "decision.status pass" in motion["pass_requirement"]
    assert "decision.eligible_for_next_local_gate true" in motion["pass_requirement"]
    candidate_tests = artifact["candidate_control"]["candidate_test_evidence"]
    assert candidate_tests["available"] is True
    assert candidate_tests["reviewed_node_toolchain_available"] is True
    assert candidate_tests["reviewed_node_ambient_path_fallback_allowed"] is False
    assert candidate_tests["reviewed_node_resolved"] is False
    assert candidate_tests["bounded_popen_protocol_available"] is True
    assert candidate_tests["bounded_popen_shell"] is False
    assert candidate_tests["bounded_popen_executed"] is False
    assert candidate_tests["state"] == "installed-not-authorised"
    assert candidate_tests["invoked"] is False
    assert candidate_tests["worker_pass_strings_are_evidence"] is False
    assert candidate_tests["origin_attested"] is False
    assert candidate_tests["trusted_orchestration_seal_required"] is True
    assert candidate_tests["evidence_passed"] is False
    assert "trusted orchestration seal" in candidate_tests["pass_requirement"]
    assert "origin_attested false" in candidate_tests["pass_requirement"]
    assert "evidence_passed true" in candidate_tests["pass_requirement"]
    candidate_qa = artifact["candidate_control"]["candidate_qa_control_plane"]
    assert candidate_qa["available"] is True
    assert candidate_qa["discovery_subprocess_launched"] is False
    assert candidate_qa["imported_compiler_drift_check_apis_available"] is True
    assert candidate_qa["imported_compiler_pre_import_source_authentication"] is False
    assert candidate_qa["sealed_direct_file_read_only_protocol_available"] is True
    assert candidate_qa["sealed_direct_file_read_only_verification_executed"] is False
    assert candidate_qa["runner_delegation_available"] is True
    assert candidate_qa["runner_bounded_popen_protocol_available"] is True
    assert candidate_qa["runner_bounded_popen_shell"] is False
    assert candidate_qa["runner_bounded_popen_timeout_seconds"] == 300
    assert candidate_qa["runner_bounded_popen_max_aggregate_output_bytes"] == 64 * 1024
    assert candidate_qa["runner_bounded_popen_retry_authority"] == "none"
    assert candidate_qa["runner_delegation_invoked"] is False
    assert "exact-path source-bound work order" in artifact["candidate_control"]["next_action"]
    assert artifact["candidate_control"]["initial_gate"]["module"] == (
        "aureon.operator.design_candidate_initial_gate"
    )
    assert artifact["candidate_control"]["research_route_attribution"]["module"] == (
        "tools/aureon_research_hydration_attribution.js"
    )
    assert artifact["candidate_control"]["research_route_attribution"]["deployment_authority"] == "none"
    assert artifact["candidate_control"]["owner_source_reconciliation"]["module"] == (
        "aureon.operator.owner_source_reconciliation"
    )
    assert artifact["candidate_control"]["owner_source_reconciliation"]["deployment_authority"] == "none"
    assert artifact["candidate_control"]["initial_gate"]["release_eligible"] is False
    assert any(check["id"] == "source_bound_design_capability_registry" for check in quality["checks"])


def test_growth_planning_records_non_authoritative_registry_evidence() -> None:
    capability = public_website_design_capability(REPO_ROOT)
    registry = capability.evidence["design_capability_registry"]

    assert registry["available"] is True
    assert registry["verified"] is True
    assert registry["source_hashes"]
    refresh = registry["design_research_refresh_readiness"]
    assert refresh["current"] is True
    assert refresh["planning_signal_available"] is True
    assert refresh["candidate_delivery_ready"] is False
    assert refresh["delivery_authority"] == "none"
    assert refresh["release_eligible"] is False
    assert refresh["deployment_authority"] == "none"
    readiness = registry["design_evidence_brief_readiness"]
    assert readiness["brief_ready"] is True
    assert readiness["planning_pipeline_available"] is True
    assert readiness["candidate_delivery_ready"] is False
    broker = registry["staged_design_worker_broker_readiness"]
    assert broker["available"] is True
    assert broker["lease_protocol_available"] is True
    assert broker["candidate_delivery_ready"] is False
    assert broker["canonical_website_mutation"] == "never"
    assert broker["release_eligible"] is False
    assert broker["package_authority"] == "none"
    assert broker["deployment_authority"] == "none"
    assert broker["credential_access"] == "none"
    governance = registry["investor_copy_governance_readiness"]
    assert governance["decision_verification_available"] is True
    assert governance["simulation_available"] is True
    assert governance["apply_protocol_available"] is True
    assert governance["implementation_tooling_verified"] is True
    assert governance["exact_owner_decision_required"] is True
    assert governance["autonomous_owner_decision"] is False
    assert governance["broad_access_approval_valid"] is False
    assert governance["current_owner_decision_present"] is False
    assert governance["current_apply_authorised"] is False
    assert governance["current_apply_ready"] is False
    assert governance["website_mutation"] == "never"
    assert governance["package_authority"] == "none"
    assert governance["release_eligible"] is False
    assert governance["deployment_authority"] == "none"
    motion = registry["motion_performance_budget_readiness"]
    assert motion["state"] == "installed-not-authorised"
    assert motion["audit_protocol_available"] is True
    assert motion["audit_executed"] is False
    assert motion["decision_passed"] is False
    assert motion["eligible_for_next_local_gate"] is False
    assert motion["candidate_validation_authority"] == "none"
    assert motion["promotion_authority"] == "none"
    assert motion["package_authority"] == "none"
    assert motion["release_eligible"] is False
    assert motion["deployment_authority"] == "none"
    candidate_tests = registry["candidate_test_evidence_readiness"]
    assert candidate_tests["state"] == "installed-not-authorised"
    assert candidate_tests["execution_protocol_available"] is True
    assert candidate_tests["reviewed_node_toolchain"]["protocol_available"] is True
    assert candidate_tests["reviewed_node_toolchain"]["ambient_path_fallback_allowed"] is False
    assert candidate_tests["bounded_process"]["protocol_available"] is True
    assert candidate_tests["bounded_process"]["shell"] is False
    assert candidate_tests["execution_authorised"] is False
    assert candidate_tests["test_suite_executed"] is False
    assert candidate_tests["worker_pass_strings_are_evidence"] is False
    assert candidate_tests["origin_attested"] is False
    assert candidate_tests["trusted_orchestration_seal_required"] is True
    assert candidate_tests["evidence_passed"] is False
    assert candidate_tests["candidate_validation_authority"] == "none"
    assert candidate_tests["promotion_authority"] == "none"
    assert candidate_tests["package_authority"] == "none"
    assert candidate_tests["release_eligible"] is False
    assert candidate_tests["deployment_authority"] == "none"
    candidate_qa = registry["candidate_qa_control_plane_readiness"]
    ingress = candidate_qa["compiler_verification_ingress"]
    assert candidate_qa["available"] is True
    assert ingress["discovery_subprocess_launched"] is False
    assert ingress["imported_api"]["scope"] == "drift-check-only"
    assert ingress["sealed_direct_file_read_only"]["protocol_available"] is True
    assert ingress["sealed_direct_file_read_only"]["executed"] is False
    assert ingress["runner_delegation"]["protocol_available"] is True
    assert ingress["runner_delegation"]["bounded_popen_protocol_available"] is True
    assert ingress["runner_delegation"]["shell"] is False
    assert ingress["runner_delegation"]["invoked"] is False
    assert capability.evidence["brief_ready"] is True
    assert capability.evidence["research_refresh_current"] is True
    assert capability.evidence["planning_pipeline_available"] is True
    assert capability.evidence["staged_worker_broker_protocol_available"] is True
    assert capability.evidence["investor_copy_governance_verification_available"] is True
    assert capability.evidence["motion_performance_budget_protocol_available"] is True
    assert capability.evidence["motion_performance_budget_passed"] is False
    assert capability.evidence["candidate_test_evidence_protocol_available"] is True
    assert capability.evidence["candidate_test_evidence_origin_attested"] is False
    assert capability.evidence["candidate_test_evidence_passed"] is False
    assert capability.evidence["candidate_qa_control_plane_available"] is True
    assert capability.evidence["imported_compiler_drift_check_apis_available"] is True
    assert capability.evidence["sealed_compiler_read_only_protocol_available"] is True
    assert capability.evidence["sealed_compiler_runner_delegation_available"] is True
    assert capability.evidence["candidate_test_reviewed_node_toolchain_available"] is True
    assert capability.evidence["candidate_test_bounded_popen_available"] is True
    assert capability.evidence["candidate_qa_discovery_subprocess_launched"] is False
    assert capability.evidence["sealed_compiler_read_only_verification_executed"] is False
    assert capability.evidence["sealed_compiler_runner_delegation_invoked"] is False
    assert capability.evidence["candidate_delivery_ready"] is False
    assert capability.evidence["release_eligible"] is False
    assert capability.evidence["deployment_authority"] == "none"
    assert "DesignCandidateControl (staged V30+ candidates)" in capability.systems
    assert "DesignCandidateInitialGate (source-bound performance feedback)" in capability.systems
    assert any(system.startswith("DesignMotionPerformanceBudget") for system in capability.systems)
    assert any(system.startswith("DesignCandidateTestEvidence") for system in capability.systems)
    assert "ResearchRouteLayoutAttribution (single runtime-only temporal diagnostic)" in capability.systems
    assert "DesignLearningLedger (append-only human-reviewed skill proposal)" in capability.systems
    assert "LiveSurfaceReconciliation (read-only public HTTPS drift sensing)" in capability.systems
    assert (
        "OwnerSourceReconciliation (owner decision plus verified backup for observed live drift)"
        in capability.systems
    )
    assert (
        "DesignEvidenceBrief (source-bound planning contract; no candidate or release authority)"
        in capability.systems
    )
    assert (
        "DesignResearchRefresh (redacted planning freshness; no delivery or release authority)"
        in capability.systems
    )
    assert (
        "PublicWebsiteDesignDeliveryRunner (immutable staged receipts; owner promotion excluded)"
        in capability.systems
    )
    assert (
        "StagedDesignWorkerBroker (explicit short-lived lease and text-only staged manifest; no canonical, credential, package, release, or deployment authority)"
        in capability.systems
    )
    assert (
        "InvestorCopyGovernance (read-only verify/simulate; exact named-owner gated three-file apply; broad access invalid; no website, package, release, or deployment authority)"
        in capability.systems
    )
    assert "aureon/operator/live_surface_reconciliation.py" in capability.evidence["present_surfaces"]
    assert "aureon/operator/owner_source_reconciliation.py" in capability.evidence["present_surfaces"]
    assert "tools/aureon_research_hydration_attribution.js" in capability.evidence["present_surfaces"]
    assert "aureon/operator/design_candidate_initial_gate.py" in capability.evidence["present_surfaces"]
    assert "aureon/operator/design_motion_performance_budget.py" in capability.evidence["present_surfaces"]
    assert "aureon/operator/design_candidate_test_evidence.py" in capability.evidence["present_surfaces"]
    assert "aureon/operator/design_candidate_source_closure.py" in capability.evidence["present_surfaces"]
    assert "docs/runbooks/DESIGN_MOTION_PERFORMANCE_BUDGET.md" in capability.evidence["present_surfaces"]
    assert "docs/runbooks/DESIGN_CANDIDATE_TEST_EVIDENCE.md" in capability.evidence["present_surfaces"]
    assert "aureon/operator/design_learning_ledger.py" in capability.evidence["present_surfaces"]
    assert "aureon/operator/design_evidence_brief.py" in capability.evidence["present_surfaces"]
    assert "aureon/operator/design_research_refresh.py" in capability.evidence["present_surfaces"]
    assert "aureon/operator/design_investor_copy_governance.py" in capability.evidence["present_surfaces"]
    assert (
        "data/website_operator/investor_site_design_brief.v1.json" in capability.evidence["present_surfaces"]
    )
    assert "data/website_operator/design_research_sources.v1.json" in capability.evidence["present_surfaces"]
    assert (
        "aureon/autonomous/aureon_public_website_design_runner.py" in capability.evidence["present_surfaces"]
    )
    assert (
        "aureon/autonomous/aureon_staged_design_worker_broker.py" in capability.evidence["present_surfaces"]
    )
