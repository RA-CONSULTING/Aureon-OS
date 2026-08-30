"""Focused guarantees for the read-only public website design capability registry."""

from __future__ import annotations

import builtins
from copy import deepcopy
from pathlib import Path

from aureon.operator import design_capability_registry as registry_module
from aureon.operator.design_capability_registry import (
    DESIGN_COUNCIL_ROLES,
    NON_AUTHORITATIVE_AUTHORITY,
    WEBSITE_OPERATOR_CAPABILITIES,
    discover_design_capability_registry,
    verify_design_capability_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _check(result: dict, identifier: str) -> dict:
    return next(item for item in result["checks"] if item["id"] == identifier)


def test_registry_discovers_current_design_roles_and_operator_capabilities() -> None:
    registry = discover_design_capability_registry(REPO_ROOT)

    assert registry["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert registry["verification"]["passed"] is True
    assert registry["verification"]["release_eligible"] is False
    assert registry["verification"]["deployment_authority"] == "none"
    assert _check(registry["verification"], "candidate-qa-compiler-verification-ingress")["passed"] is True
    assert {row["name"] for row in registry["design_council_roles"]} == set(DESIGN_COUNCIL_ROLES)
    assert {row["id"] for row in registry["website_operator_capabilities"]} == {
        identifier for identifier, _category, _method in WEBSITE_OPERATOR_CAPABILITIES
    }
    assert "design-candidate-control" in {row["id"] for row in registry["sources"]}
    assert "live-surface-reconciliation" in {row["id"] for row in registry["sources"]}
    assert "research-hydration-attribution" in {row["id"] for row in registry["sources"]}
    assert "owner-source-reconciliation" in {row["id"] for row in registry["sources"]}
    assert "website-source-rationalisation" in {row["id"] for row in registry["sources"]}
    assert "website-source-rationalisation-runbook" in {row["id"] for row in registry["sources"]}
    assert {
        "website-runtime-optimisation",
        "website-runtime-optimisation-launcher",
        "website-browser-acceptance-contract",
        "website-runtime-optimisation-runbook",
        "website-runtime-measurement-static-integrity",
        "website-runtime-measurement-static-integrity-launcher",
        "website-runtime-measurement-static-integrity-schema",
    }.issubset({row["id"] for row in registry["sources"]})
    assert "design-candidate-initial-gate" in {row["id"] for row in registry["sources"]}
    assert "design-research-refresh" in {row["id"] for row in registry["sources"]}
    assert "design-research-source-declaration" in {row["id"] for row in registry["sources"]}
    assert "design-stakeholder-feedback" in {row["id"] for row in registry["sources"]}
    assert "design-stakeholder-feedback-declaration" in {row["id"] for row in registry["sources"]}
    assert "design-editorial-asset-provenance" in {row["id"] for row in registry["sources"]}
    assert "design-editorial-asset-provenance-declaration" in {row["id"] for row in registry["sources"]}
    assert "design-editorial-rights-decision-preparation" in {row["id"] for row in registry["sources"]}
    assert "design-editorial-asset-candidate-importer" in {row["id"] for row in registry["sources"]}
    assert "investor-copy-quality-control" in {row["id"] for row in registry["sources"]}
    assert "investor-copy-quality-policy" in {row["id"] for row in registry["sources"]}
    assert "investor-copy-repair-contract" in {row["id"] for row in registry["sources"]}
    assert "investor-copy-governance-application" in {row["id"] for row in registry["sources"]}
    assert "hnc-evidence-control-graph" in {row["id"] for row in registry["sources"]}
    assert "hnc-evidence-control-graph-contract" in {row["id"] for row in registry["sources"]}
    assert "design-evidence-brief" in {row["id"] for row in registry["sources"]}
    assert "staged-design-delivery-runner" in {row["id"] for row in registry["sources"]}
    assert "staged-design-worker-broker" in {row["id"] for row in registry["sources"]}
    assert "design-motion-performance-budget" in {row["id"] for row in registry["sources"]}
    assert "design-motion-performance-budget-runbook" in {row["id"] for row in registry["sources"]}
    assert "design-candidate-test-evidence" in {row["id"] for row in registry["sources"]}
    assert "design-candidate-test-evidence-runbook" in {row["id"] for row in registry["sources"]}
    assert {
        "secure-immutable-artifact",
        "secure-immutable-artifact-runbook",
        "design-candidate-static-qa",
        "design-candidate-static-qa-runbook",
        "design-candidate-test-policy-compiler",
        "design-candidate-test-policy-compiler-runbook",
        "design-candidate-motion-policy-compiler",
        "design-candidate-motion-policy-compiler-runbook",
        "design-candidate-source-closure",
        "staged-design-delivery-v2-schema",
        "staged-design-delivery-v2-runbook",
    }.issubset({row["id"] for row in registry["sources"]})
    assert "design-learning-ledger" in {row["id"] for row in registry["sources"]}
    assert "design-learning-record" in {row["id"] for row in registry["website_operator_capabilities"]}
    assert "live-surface-reconciliation" in {row["id"] for row in registry["website_operator_capabilities"]}
    assert "research-route-layout-attribution" in {
        row["id"] for row in registry["website_operator_capabilities"]
    }
    assert "owner-source-reconciliation" in {row["id"] for row in registry["website_operator_capabilities"]}
    assert all(row["available"] is True for row in registry["sources"])
    assert registry["owner_source_reconciliation_readiness"]["validation_protocol_available"] is True
    rationalisation = registry["website_source_rationalisation_readiness"]
    assert rationalisation == {
        "available": True,
        "installed": True,
        "state": "installed-owner-decision-required",
        "planning_protocol_available": True,
        "decision_validation_protocol_available": True,
        "plan_executed": False,
        "decision_validation_executed": False,
        "discovery_mode": "metadata-only-ast-no-import-no-subprocess",
        "module_imported": False,
        "owner_decision_required": True,
        "autonomous_owner_decision": False,
        "staging_implemented": False,
        "canonical_website_mutation": "none",
        "physical_source_file_removal": "none",
        "candidate_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "max_decision_age_seconds": 4 * 60 * 60,
        "fixed_footprint_limits": {
            "max_total_bytes": 4_500_000,
            "max_image_bytes": 2_200_000,
            "max_css_bytes": 350_000,
            "max_single_asset_bytes": 500_000,
        },
        "source_sha256": registry_module.WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256,
        "expected_source_sha256": (registry_module.WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256),
        "source_hash_matches": True,
        "reviewed_bindings": registry_module.WEBSITE_SOURCE_RATIONALISATION_REVIEWED_BINDINGS,
        "public_signatures_locked": True,
        "repo_code_imported": False,
        "launcher_path": registry_module.WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_PATH,
        "launcher_sha256": registry_module.WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256,
        "expected_launcher_sha256": (registry_module.WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256),
        "launcher_hash_matches": True,
        "launcher_repo_code_imported": False,
        "error": "",
    }
    assert _check(registry["verification"], "website-source-rationalisation-boundary")["passed"] is True
    runtime_optimisation = registry["website_runtime_optimisation_readiness"]
    assert runtime_optimisation["state"] == "installed-reviewed-measurement-provenance-required"
    assert runtime_optimisation["proposal_compilation_protocol_available"] is False
    assert runtime_optimisation["measurement_validation_protocol_available"] is True
    assert (
        runtime_optimisation["measurement_validation_scope"] == "structural-only-no-freshness-or-provenance"
    )
    assert runtime_optimisation["measurement_provenance_verification_available"] is False
    assert runtime_optimisation["production_compilation_blocked"] is True
    assert (
        runtime_optimisation["production_compilation_blocker"]
        == "blocked-reviewed-measurement-provenance-tool-not-installed"
    )
    assert runtime_optimisation["browser_acceptance_contract_available"] is True
    assert runtime_optimisation["measurement_schema_available"] is True
    assert runtime_optimisation["proposal_schema_available"] is True
    assert runtime_optimisation["measurement_schema_hash_matches"] is True
    assert runtime_optimisation["measurement_schema_json_valid"] is True
    assert runtime_optimisation["proposal_schema_hash_matches"] is True
    assert runtime_optimisation["proposal_schema_json_valid"] is True
    assert runtime_optimisation["proposal_compilation_executed"] is False
    assert runtime_optimisation["measurement_validation_executed"] is False
    assert runtime_optimisation["source_selection_required"] is True
    assert runtime_optimisation["autonomous_source_selection"] is False
    assert runtime_optimisation["measurement_evidence_required"] is True
    assert runtime_optimisation["autonomous_measurement_evidence"] is False
    assert runtime_optimisation["transformations_executed"] is False
    assert runtime_optimisation["release_eligible"] is False
    assert runtime_optimisation["deployment_authority"] == "none"
    assert runtime_optimisation["source_hash_matches"] is True
    assert runtime_optimisation["launcher_hash_matches"] is True
    assert runtime_optimisation["acceptance_contract_hash_matches"] is True
    assert runtime_optimisation["acceptance_contract_payload_valid"] is True
    assert _check(registry["verification"], "website-runtime-optimisation-boundary")["passed"] is True
    static_integrity = registry["website_runtime_measurement_static_integrity_readiness"]
    assert static_integrity["available"] is True
    assert static_integrity["state"] == "installed-read-validate-only-production-ineligible"
    assert static_integrity["capability_scope"] == "read-validate-only"
    assert static_integrity["static_integrity_validation_available"] is True
    assert static_integrity["static_integrity_validation_executed"] is False
    assert static_integrity["trusted_static_integrity_execution_path"] == "fresh-isolated-launcher-only"
    assert static_integrity["imported_api_authoritative"] is False
    assert static_integrity["measurement_provenance_verification_available"] is False
    assert static_integrity["production_eligible"] is False
    assert static_integrity["eligible_for_proposal_compilation"] is False
    assert static_integrity["worker_available"] is False
    assert static_integrity["worker_executed"] is False
    assert static_integrity["artifact_emission_available"] is False
    assert static_integrity["artifact_emission_executed"] is False
    assert static_integrity["release_eligible"] is False
    assert static_integrity["deployment_authority"] == "none"
    assert static_integrity["standard_library_only"] is True
    assert static_integrity["forbidden_operational_imports_present"] is False
    assert static_integrity["writer_or_emitter_surface_present"] is False
    assert static_integrity["public_verify_signature_locked"] is True
    assert static_integrity["launcher_isolation_markers_locked"] is True
    assert static_integrity["source_hash_matches"] is True
    assert static_integrity["launcher_hash_matches"] is True
    assert static_integrity["schema_hash_matches"] is True
    assert static_integrity["schema_json_valid"] is True
    assert (
        _check(
            registry["verification"],
            "website-runtime-measurement-static-integrity-boundary",
        )["passed"]
        is True
    )
    assert (
        registry["editorial_rights_decision_preparation_readiness"]["preparation_protocol_available"] is True
    )
    assert registry["investor_copy_repair_readiness"]["source_bound_protocol_available"] is True
    assert registry["investor_copy_governance_readiness"]["simulation_available"] is True
    refresh = registry["design_research_refresh_readiness"]
    assert refresh["current"] is (refresh["state"] == "current")
    assert refresh["planning_signal_available"] is refresh["current"]
    assert refresh["candidate_delivery_ready"] is False
    assert refresh["delivery_authority"] == "none"
    assert refresh["release_eligible"] is False
    assert refresh["deployment_authority"] == "none"
    assert refresh["declaration"]["path"] == ("data/website_operator/design_research_sources.v1.json")
    assert refresh["artwork"] == {"state": "not-cleared", "cleared_for_use": False}
    feedback = registry["stakeholder_feedback_readiness"]
    assert feedback["available"] is True
    assert feedback["installed"] is True
    assert feedback["current"] is (feedback["state"] in {"current", "refresh-due"})
    assert feedback["planning_only"] is True
    assert feedback["planning_signal_available"] is feedback["current"]
    assert feedback["candidate_delivery_ready"] is False
    assert feedback["release_eligible"] is False
    assert feedback["release_authority"] == "none"
    assert feedback["package_authority"] == "none"
    assert feedback["deployment_authority"] == "none"
    assert feedback["raw_correspondence_access"] == "none"
    assert feedback["declaration"]["path"] == ("data/website_operator/design_stakeholder_feedback.v1.json")
    assert feedback["freshness"]["state"] == feedback["state"]
    assert feedback["summary"] == {
        "signal_count": 7,
        "action_requested_count": 5,
        "no_action_count": 1,
    }
    assert len(feedback["signal_capsules_sha256"]) == 64
    assert feedback["response_manifest_required"] is True
    assert {
        "signals",
        "signal_ids",
        "signal_capsules",
        "responses",
        "evidence_snapshot",
    }.isdisjoint(feedback)
    editorial_assets = registry["editorial_asset_provenance_readiness"]
    assert editorial_assets["available"] is True
    assert editorial_assets["installed"] is True
    assert editorial_assets["state"] == "blocked-unapproved-current-use"
    assert isinstance(editorial_assets["integrity_verified"], bool)
    assert editorial_assets["public_use_ready"] is False
    assert editorial_assets["candidate_use_rights_ready"] is False
    assert editorial_assets["candidate_asset_ready"] is False
    assert editorial_assets["candidate_delivery_ready"] is False
    assert editorial_assets["release_eligible"] is False
    assert editorial_assets["package_authority"] == "none"
    assert editorial_assets["deployment_authority"] == "none"
    assert editorial_assets["global_artwork_policy"] == {
        "state": "not-cleared",
        "cleared_for_use": False,
    }
    assert editorial_assets["summary"] == {
        "mapped_asset_count": 6,
        "unmapped_asset_count": 1,
        "currently_referenced_asset_count": 6,
        "unapproved_current_asset_count": 6,
        "current_copy_drift_asset_count": 6,
        "candidate_use_ready_count": 0,
    }
    assert len(editorial_assets["asset_capsules_sha256"]) == 64
    assert len(editorial_assets["route_asset_capsules_sha256"]) == 64
    assert len(editorial_assets["public_coverage_sha256"]) == 64
    assert {
        "assets",
        "asset_ids",
        "source_assets",
        "rights_decisions",
        "evidence_snapshots",
    }.isdisjoint(editorial_assets)
    asset_importer = registry["editorial_asset_importer_readiness"]
    assert asset_importer == {
        "available": True,
        "installed": True,
        "state": "installed-awaiting-approved-asset",
        "import_protocol_available": True,
        "receipt_verification_available": True,
        "candidate_use_rights_ready": False,
        "candidate_asset_ready": False,
        "candidate_import_ready": False,
        "candidate_delivery_ready": False,
        "canonical_website_mutation": "never",
        "binary_read_scope": "content-addressed verified editorial intake only",
        "candidate_write_scope": "exact work-order-declared image targets only",
        "transformations": "none",
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
        "error": "",
    }
    copy_quality = registry["investor_copy_quality_readiness"]
    assert copy_quality["available"] is True
    assert copy_quality["installed"] is True
    assert copy_quality["state"] == "blocked"
    assert isinstance(copy_quality["policy_current"], bool)
    assert copy_quality["copy_ready"] is False
    assert copy_quality["candidate_delivery_ready"] is False
    assert copy_quality["release_eligible"] is False
    assert copy_quality["package_authority"] == "none"
    assert copy_quality["deployment_authority"] == "none"
    assert copy_quality["summary"]["route_count"] == 3
    assert copy_quality["summary"]["finding_count"] == (
        copy_quality["summary"]["blocker_count"] + copy_quality["summary"]["warning_count"]
    )
    assert copy_quality["summary"]["blocker_count"] > 0
    assert "findings" not in copy_quality
    hnc_graph = registry["hnc_evidence_graph_readiness"]
    assert hnc_graph["installed"] is hnc_graph["available"]
    assert hnc_graph["component_bundle_ready"] is hnc_graph["available"]
    assert hnc_graph["candidate_transplant_ready"] is False
    assert hnc_graph["candidate_delivery_ready"] is False
    assert hnc_graph["release_eligible"] is False
    assert hnc_graph["package_authority"] == "none"
    assert hnc_graph["deployment_authority"] == "none"
    if hnc_graph["available"]:
        assert hnc_graph["state"] == "pass"
        assert hnc_graph["claim_ids"] == [
            "hnc-research-framework",
            "aureon-os-evidence-system",
        ]
        assert len(hnc_graph["bundle_sha256"]) == 64
        assert hnc_graph["outputs"]["component.html"]["bytes"] <= 2500
        assert hnc_graph["outputs"]["component.css"]["bytes"] <= 5500
        assert hnc_graph["outputs"]["component.js"]["bytes"] <= 1800
    else:
        assert hnc_graph["state"] == "unavailable"
        assert hnc_graph["error"]
    readiness = registry["design_evidence_brief_readiness"]
    assert readiness["brief_ready"] is (readiness["state"] == "brief-ready")
    assert readiness["planning_pipeline_available"] is readiness["brief_ready"]
    assert readiness["candidate_delivery_ready"] is False
    assert readiness["release_eligible"] is False
    assert readiness["deployment_authority"] == "none"
    if readiness["brief_ready"]:
        assert readiness["research_refresh"]["declaration_path"] == (
            "data/website_operator/design_research_sources.v1.json"
        )
        assert readiness["research_refresh"]["declaration_sha256"] == (
            refresh["declaration"]["sha256"]
        )
        assert readiness["research_refresh"]["passed"] is True
        assert readiness["stakeholder_feedback"]["feedback_id"] == (
            feedback["declaration"]["feedback_id"]
        )
        assert readiness["stakeholder_feedback"]["passed"] is True
        assert readiness["stakeholder_feedback"]["signal_count"] == (
            feedback["summary"]["signal_count"]
        )
    else:
        assert readiness["research_refresh"]["passed"] is False
        assert readiness["stakeholder_feedback"]["passed"] is False
        assert readiness["next_required_stage"]
    assert "signal_ids" not in readiness["stakeholder_feedback"]
    assert "signals" not in readiness["stakeholder_feedback"]
    broker = registry["staged_design_worker_broker_readiness"]
    assert broker["state"] == "installed-not-authorised"
    assert broker["available"] is True
    assert broker["lease_protocol_available"] is True
    assert broker["candidate_delivery_ready"] is False
    assert broker["canonical_website_mutation"] == "never"
    assert broker["release_eligible"] is False
    assert broker["package_authority"] == "none"
    assert broker["deployment_authority"] == "none"
    assert broker["credential_access"] == "none"
    assert broker["receipt_integrity_scope"].startswith("local accidental-drift detection")
    assert broker["max_lease_seconds"] == 900
    motion = registry["motion_performance_budget_readiness"]
    assert motion["available"] is True
    assert motion["installed"] is True
    assert motion["state"] == "installed-not-authorised"
    assert motion["audit_protocol_available"] is True
    assert motion["receipt_replay_available"] is True
    assert motion["audit_executed"] is False
    assert motion["decision_status"] == "not-evaluated"
    assert motion["decision_passed"] is False
    assert motion["eligible_for_next_local_gate"] is False
    assert motion["pass_inferred_from_installation"] is False
    assert "decision.status pass" in motion["pass_requirement"]
    assert "decision.eligible_for_next_local_gate true" in motion["pass_requirement"]
    assert motion["candidate_authority"] == "none"
    assert motion["candidate_validation_authority"] == "none"
    assert motion["promotion_authority"] == "none"
    assert motion["canonical_website_mutation"] == "none"
    assert motion["package_authority"] == "none"
    assert motion["release_authority"] == "none"
    assert motion["release_eligible"] is False
    assert motion["deployment_authority"] == "none"
    assert motion["credential_access"] == "none"
    assert motion["network_access"] == "none"
    candidate_tests = registry["candidate_test_evidence_readiness"]
    assert candidate_tests["available"] is True
    assert candidate_tests["installed"] is True
    assert candidate_tests["state"] == "installed-not-authorised"
    assert candidate_tests["execution_protocol_available"] is True
    assert candidate_tests["structural_verification_available"] is True
    assert candidate_tests["immutable_writer_available"] is True
    assert candidate_tests["reviewed_node_toolchain"] == {
        "protocol_available": True,
        "schema": "aureon.node-toolchain-binding.v1",
        "locator_authority": "reviewed-source-pinned-absolute-path-no-path-fallback",
        "absolute_path_size_sha256_bound": True,
        "ambient_path_fallback_allowed": False,
        "resolved": False,
        "executed": False,
    }
    assert candidate_tests["bounded_process"] == {
        "protocol_available": True,
        "launcher": "subprocess.Popen",
        "shell": False,
        "max_stream_bytes": 2 * 1024 * 1024,
        "retry_authority": "none",
        "executed": False,
    }
    assert candidate_tests["execution_authorised"] is False
    assert candidate_tests["test_suite_executed"] is False
    assert candidate_tests["worker_pass_strings_are_evidence"] is False
    assert candidate_tests["structural_verification_passed"] is False
    assert candidate_tests["origin_attested"] is False
    assert candidate_tests["trusted_orchestration_seal_required"] is True
    assert candidate_tests["evidence_passed"] is False
    assert candidate_tests["pass_inferred_from_installation"] is False
    assert "trusted-orchestration seal" in candidate_tests["pass_requirement"]
    assert "origin_attested false" in candidate_tests["pass_requirement"]
    assert "evidence_passed true" in candidate_tests["pass_requirement"]
    assert candidate_tests["candidate_validation_authority"] == "none"
    assert candidate_tests["promotion_authority"] == "none"
    assert candidate_tests["canonical_website_mutation"] == "none"
    assert candidate_tests["package_authority"] == "none"
    assert candidate_tests["release_authority"] == "none"
    assert candidate_tests["release_eligible"] is False
    assert candidate_tests["deployment_authority"] == "none"
    assert candidate_tests["credential_access"] == "none"
    candidate_qa = registry["candidate_qa_control_plane_readiness"]
    assert candidate_qa["available"] is True
    assert candidate_qa["installed"] is True
    assert candidate_qa["state"] == "installed-not-authorised"
    assert candidate_qa["static_qa_available"] is True
    assert candidate_qa["fixed_test_policy_compiler_available"] is True
    assert candidate_qa["fixed_motion_policy_compiler_available"] is True
    assert candidate_qa["handle_bound_immutable_writer_available"] is True
    assert candidate_qa["v2_runner_available"] is True
    assert candidate_qa["candidate_test_evidence_runtime_available"] is True
    assert candidate_qa["v2_schema_available"] is True
    assert candidate_qa["v2_runbook_available"] is True
    ingress = candidate_qa["compiler_verification_ingress"]
    assert ingress["discovery_mode"] == "metadata-only-no-subprocess"
    assert ingress["discovery_subprocess_launched"] is False
    assert ingress["imported_api"] == {
        "scope": "drift-check-only",
        "motion_read_only_verifier_available": True,
        "test_read_only_verifier_available": True,
        "pre_import_source_authentication": False,
    }
    assert ingress["sealed_direct_file_read_only"] == {
        "protocol_available": True,
        "motion_protocol_available": True,
        "test_protocol_available": True,
        "executed": False,
        "python_flags": ["-I", "-S", "-B"],
        "motion_verify_flag": "--verify-config",
        "test_verify_flag": "--verify-policy",
        "source_closure_helper_available": True,
    }
    assert ingress["runner_delegation"] == {
        "protocol_available": True,
        "required_for_candidate_qa": True,
        "bounded_popen_protocol_available": True,
        "launcher": "subprocess.Popen",
        "shell": False,
        "timeout_seconds": 300,
        "max_aggregate_output_bytes": 64 * 1024,
        "retry_authority": "none",
        "invoked": False,
    }
    assert candidate_qa["execution_order"] == [
        "compile-fixed-motion-config",
        "compile-fixed-test-policy",
        "run-motion-budget-first",
        "run-complete-trusted-test-policy",
        "enter-initial-browser-gate-only-after-qa-verification",
    ]
    assert candidate_qa["execution_order_enforced"] is True
    assert candidate_qa["policy_selection_authority"] == "none"
    assert candidate_qa["threshold_selection_authority"] == "none"
    assert candidate_qa["retry_authority"] == "none"
    assert candidate_qa["qa_execution_authorised"] is False
    assert candidate_qa["qa_executed"] is False
    assert candidate_qa["motion_audit_executed"] is False
    assert candidate_qa["test_suite_executed"] is False
    assert candidate_qa["browser_gate_executed"] is False
    assert candidate_qa["qa_passed"] is False
    assert candidate_qa["pass_inferred_from_installation"] is False
    assert candidate_qa["candidate_creation_authority"] == "none"
    assert candidate_qa["candidate_mutation_authority"] == "none"
    assert candidate_qa["candidate_validation_authority"] == "none"
    assert candidate_qa["canonical_website_mutation"] == "none"
    assert candidate_qa["promotion_authority"] == "none"
    assert candidate_qa["package_authority"] == "none"
    assert candidate_qa["release_authority"] == "none"
    assert candidate_qa["release_eligible"] is False
    assert candidate_qa["deployment_authority"] == "none"
    assert candidate_qa["credential_access"] == "none"


def test_registry_exposes_read_only_owner_rights_and_copy_repair_protocols() -> None:
    owner_source = registry_module.owner_source_reconciliation_readiness(REPO_ROOT)
    assert owner_source["state"] == "installed-owner-decision-required"
    assert owner_source["validation_protocol_available"] is True
    assert owner_source["v1_retain_local_supported"] is True
    assert owner_source["v2_verified_live_backup_supported"] is True
    assert owner_source["owner_decision_required"] is True
    assert owner_source["autonomous_source_selection"] is False
    assert owner_source["candidate_delivery_ready"] is False
    assert owner_source["canonical_website_mutation"] == "none"
    assert owner_source["release_eligible"] is False
    assert owner_source["package_authority"] == "none"
    assert owner_source["deployment_authority"] == "none"
    assert owner_source["credential_access"] == "none"
    assert owner_source["max_decision_age_seconds"] == 4 * 60 * 60
    assert owner_source["source_modes"] == {
        "v1": {
            "schema": "aureon.owner-source-reconciliation-decision.v1",
            "selection": "retain-local-canonical-source",
            "verified_live_backup_selected": False,
        },
        "v2": {
            "schema": "aureon.owner-source-reconciliation-decision.v2",
            "selection": "use-verified-live-backup",
            "verified_live_backup_selected": True,
        },
    }

    rationalisation = registry_module.website_source_rationalisation_readiness(REPO_ROOT)
    assert rationalisation["state"] == "installed-owner-decision-required"
    assert rationalisation["planning_protocol_available"] is True
    assert rationalisation["decision_validation_protocol_available"] is True
    assert rationalisation["plan_executed"] is False
    assert rationalisation["decision_validation_executed"] is False
    assert rationalisation["discovery_mode"] == "metadata-only-ast-no-import-no-subprocess"
    assert rationalisation["module_imported"] is False
    assert rationalisation["owner_decision_required"] is True
    assert rationalisation["autonomous_owner_decision"] is False
    assert rationalisation["staging_implemented"] is False
    assert rationalisation["canonical_website_mutation"] == "none"
    assert rationalisation["physical_source_file_removal"] == "none"
    assert rationalisation["candidate_authority"] == "none"
    assert rationalisation["package_authority"] == "none"
    assert rationalisation["release_eligible"] is False
    assert rationalisation["deployment_authority"] == "none"
    assert rationalisation["credential_access"] == "none"
    assert rationalisation["network_access"] == "none"
    assert rationalisation["max_decision_age_seconds"] == 4 * 60 * 60
    assert rationalisation["source_sha256"] == (
        registry_module.WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256
    )
    assert rationalisation["expected_source_sha256"] == (
        registry_module.WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256
    )
    assert rationalisation["source_hash_matches"] is True
    assert rationalisation["reviewed_bindings"] == (
        registry_module.WEBSITE_SOURCE_RATIONALISATION_REVIEWED_BINDINGS
    )
    assert rationalisation["public_signatures_locked"] is True
    assert rationalisation["repo_code_imported"] is False
    assert rationalisation["launcher_sha256"] == (
        registry_module.WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256
    )
    assert rationalisation["expected_launcher_sha256"] == (
        registry_module.WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256
    )
    assert rationalisation["launcher_hash_matches"] is True
    assert rationalisation["launcher_repo_code_imported"] is False
    rights = registry_module.editorial_rights_decision_preparation_readiness(REPO_ROOT)
    assert rights["state"] == "installed-explicit-human-decision-required"
    assert rights["preparation_protocol_available"] is True
    assert rights["human_decision_input_required"] is True
    assert rights["autonomous_human_decision"] is False
    assert rights["rights_inference"] == "never"
    assert rights["canonical_manifest_mutation"] == "never"
    assert rights["global_artwork_policy_mutation"] == "never"
    assert rights["candidate_use_rights_ready"] is False
    assert rights["candidate_asset_ready"] is False
    assert rights["candidate_delivery_ready"] is False
    assert rights["release_eligible"] is False
    assert rights["package_authority"] == "none"
    assert rights["deployment_authority"] == "none"
    assert rights["credential_access"] == "none"
    assert rights["network_access"] == "none"
    assert rights["connector_access"] == "none"

    copy_repair = registry_module.investor_copy_repair_readiness(REPO_ROOT)
    assert copy_repair["state"] == "installed-awaiting-exact-design-copy-task"
    assert copy_repair["source_bound_protocol_available"] is True
    assert copy_repair["task_preflight_available"] is True
    assert copy_repair["selected_source_preflight_available"] is True
    assert copy_repair["contract_creation_available"] is True
    assert copy_repair["contract_verification_available"] is True
    assert copy_repair["candidate_reaudit_available"] is True
    assert copy_repair["current_contract_ready"] is False
    assert copy_repair["candidate_copy_ready"] is False
    assert copy_repair["candidate_delivery_ready"] is False
    assert copy_repair["canonical_website_mutation"] == "never"
    assert copy_repair["candidate_staging"] == "never"
    assert copy_repair["claim_register_mutation"] == "never"
    assert copy_repair["human_copy_review"] == "required"
    assert copy_repair["human_visual_acceptance"] == "required"
    assert copy_repair["release_eligible"] is False
    assert copy_repair["package_authority"] == "none"
    assert copy_repair["deployment_authority"] == "none"
    assert copy_repair["credential_access"] == "none"
    assert copy_repair["network_access"] == "none"
    assert copy_repair["max_contract_lifetime_seconds"] == 24 * 60 * 60
    assert copy_repair["schemas"] == {
        "preflight": "aureon.design-investor-copy-repair-preflight.v1",
        "contract": "aureon.design-investor-copy-repair.v1",
        "verification": "aureon.design-investor-copy-repair-verification.v1",
        "evaluation": "aureon.design-investor-copy-repair-evaluation.v1",
    }

    governance = registry_module.investor_copy_governance_readiness(REPO_ROOT)
    assert governance["state"] == "installed-exact-owner-decision-required"
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
    assert governance["canonical_governance_paths"] == [
        "data/website_operator/public_claim_evidence_register.v1.json",
        "data/website_operator/design_stakeholder_feedback.v1.json",
        "data/website_operator/investor_site_design_brief.v1.json",
    ]
    assert governance["website_mutation"] == "never"
    assert governance["policy_mutation"] == "never"
    assert governance["candidate_authority"] == "none"
    assert governance["package_authority"] == "none"
    assert governance["release_eligible"] is False
    assert governance["deployment_authority"] == "none"
    assert governance["credential_access"] == "none"
    assert governance["network_access"] == "none"
    assert governance["max_decision_age_seconds"] == 24 * 60 * 60
    assert governance["schemas"] == {
        "decision": "aureon.investor-copy-governance-owner-decision.v1",
        "verification": "aureon.investor-copy-governance-decision-verification.v1",
        "simulation": "aureon.investor-copy-governance-application-plan.v1",
        "application": "aureon.investor-copy-governance-application.v1",
    }


def test_source_rationalisation_readiness_authenticates_ast_without_import(monkeypatch) -> None:
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "aureon.operator.website_source_rationalisation":
            raise AssertionError("registry readiness must not import the operational module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    readiness = registry_module.website_source_rationalisation_readiness(REPO_ROOT)

    assert readiness["available"] is True
    assert readiness["discovery_mode"] == "metadata-only-ast-no-import-no-subprocess"
    assert readiness["module_imported"] is False
    assert readiness["plan_executed"] is False
    assert readiness["decision_validation_executed"] is False


def test_static_integrity_readiness_authenticates_metadata_without_import_or_execution(
    monkeypatch,
) -> None:
    real_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name == "aureon.operator.website_runtime_measurement_provenance":
            raise AssertionError("registry readiness must not import the static-integrity module")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    readiness = registry_module.website_runtime_measurement_static_integrity_readiness(REPO_ROOT)

    assert readiness["available"] is True
    assert readiness["capability_scope"] == "read-validate-only"
    assert readiness["discovery_mode"] == "metadata-only-ast-and-json-no-import-no-subprocess"
    assert readiness["module_imported"] is False
    assert readiness["launcher_module_imported"] is False
    assert readiness["subprocess_launched"] is False
    assert readiness["static_integrity_validation_executed"] is False
    assert readiness["trusted_static_integrity_execution_path"] == "fresh-isolated-launcher-only"
    assert readiness["imported_api_authoritative"] is False
    assert readiness["production_eligible"] is False
    assert readiness["eligible_for_proposal_compilation"] is False
    assert readiness["measurement_provenance_verification_available"] is False
    assert readiness["worker_available"] is False
    assert readiness["artifact_emission_available"] is False


def test_static_integrity_readiness_rejects_unreviewed_source_bytes(tmp_path: Path) -> None:
    for relative in (
        registry_module.WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_PATH,
        registry_module.WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_LAUNCHER_PATH,
        registry_module.WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_SCHEMA_PATH,
    ):
        source = REPO_ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    module_path = tmp_path / registry_module.WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_PATH
    module_path.write_bytes(module_path.read_bytes() + b"\n# unreviewed drift\n")

    readiness = registry_module.website_runtime_measurement_static_integrity_readiness(tmp_path)

    assert readiness["installed"] is True
    assert readiness["available"] is False
    assert readiness["state"] == "protocol-blocked"
    assert readiness["source_hash_matches"] is False
    assert readiness["static_integrity_validation_executed"] is False
    assert readiness["worker_executed"] is False
    assert readiness["artifact_emission_executed"] is False


def test_source_rationalisation_readiness_rejects_unreviewed_import_time_payload(
    tmp_path: Path,
) -> None:
    module_dir = tmp_path / "aureon" / "operator"
    module_dir.mkdir(parents=True)
    launcher_path = tmp_path / registry_module.WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_PATH
    launcher_path.parent.mkdir(parents=True)
    launcher_path.write_bytes(
        (REPO_ROOT / registry_module.WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_PATH).read_bytes()
    )
    sentinel = tmp_path / "import-time-sentinel.txt"
    module_path = module_dir / "website_source_rationalisation.py"
    module_path.write_text(
        "\n".join(
            (
                "from pathlib import Path",
                f"Path({sentinel.as_posix()!r}).write_text('executed', encoding='utf-8')",
                "PLAN_SCHEMA = 'aureon.website-source-rationalisation-plan.v1'",
                "OWNER_DECISION_SCHEMA = 'aureon.website-source-rationalisation-owner-decision.v1'",
                "OWNER_VALIDATION_SCHEMA = 'aureon.website-source-rationalisation-owner-validation.v1'",
                "def create_source_rationalisation_plan(*, run_id=None): pass",
                "def require_source_rationalisation_plan(value): pass",
                "def write_source_rationalisation_plan(plan, output_path): pass",
                "def validate_owner_source_rationalisation_decision(plan_path, decision_path): pass",
                "def require_owner_validation(value): pass",
                "def write_owner_validation(validation, output_path): pass",
            )
        ),
        encoding="utf-8",
    )

    readiness = registry_module.website_source_rationalisation_readiness(tmp_path)

    assert readiness["state"] == "protocol-blocked"
    assert readiness["source_hash_matches"] is False
    assert readiness["available"] is False
    assert readiness["module_imported"] is False
    assert not sentinel.exists()


def test_new_protocol_readiness_never_executes_decisions_contracts_or_reaudits(monkeypatch) -> None:
    from aureon.autonomous import aureon_public_website_design_runner as delivery_runner
    from aureon.operator import design_candidate_motion_policy_compiler as motion_compiler
    from aureon.operator import design_candidate_static_qa as static_qa
    from aureon.operator import design_candidate_test_evidence as test_evidence
    from aureon.operator import design_candidate_test_policy_compiler as test_policy_compiler
    from aureon.operator import design_editorial_asset_provenance as provenance
    from aureon.operator import design_investor_copy_governance as governance
    from aureon.operator import design_investor_copy_repair as repair
    from aureon.operator import design_motion_performance_budget as motion_budget
    from aureon.operator import owner_source_reconciliation as reconciliation
    from aureon.operator import secure_immutable_artifact
    from aureon.operator import website_source_rationalisation as rationalisation

    def prohibited_execution(*_args, **_kwargs):
        raise AssertionError("readiness discovery must not execute an operational control")

    def prohibited_apply(*_args, apply=False, **_kwargs):
        raise AssertionError(f"readiness discovery must not apply an operational control: {apply}")

    monkeypatch.setattr(
        provenance,
        "prepare_editorial_asset_rights_decisions",
        prohibited_execution,
    )
    monkeypatch.setattr(
        reconciliation,
        "validate_owner_source_reconciliation",
        prohibited_execution,
    )
    for name in (
        "create_source_rationalisation_plan",
        "write_source_rationalisation_plan",
        "validate_owner_source_rationalisation_decision",
        "write_owner_validation",
    ):
        monkeypatch.setattr(rationalisation, name, prohibited_execution)
    for name in (
        "preflight_investor_copy_repair_contract",
        "preflight_investor_copy_repair_work_order",
        "create_investor_copy_repair_contract",
        "write_investor_copy_repair_contract",
        "verify_investor_copy_repair_contract",
        "evaluate_investor_copy_repair_candidate",
    ):
        monkeypatch.setattr(repair, name, prohibited_execution)
    monkeypatch.setattr(
        governance,
        "verify_investor_copy_governance_decision",
        prohibited_execution,
    )
    monkeypatch.setattr(
        governance,
        "plan_investor_copy_governance_application",
        prohibited_execution,
    )
    monkeypatch.setattr(
        governance,
        "apply_investor_copy_governance_delta",
        prohibited_apply,
    )
    for name in (
        "snapshot_static_tree",
        "audit_motion_performance_budget",
        "validate_motion_performance_receipt",
    ):
        monkeypatch.setattr(motion_budget, name, prohibited_execution)
    for name in (
        "execute_candidate_test_evidence",
        "validate_candidate_test_evidence_receipt",
        "verify_candidate_test_evidence_receipt",
        "write_candidate_test_evidence_receipt",
    ):
        monkeypatch.setattr(test_evidence, name, prohibited_execution)
    monkeypatch.setattr(static_qa, "audit_candidate_static", prohibited_execution)
    for module, names in (
        (
            motion_compiler,
            (
                "compile_candidate_motion_config",
                "write_compiled_candidate_motion_config",
                "verify_compiled_candidate_motion_config_file",
            ),
        ),
        (
            test_policy_compiler,
            (
                "compile_candidate_test_policy",
                "write_compiled_candidate_test_policy",
                "verify_compiled_candidate_test_policy_file",
            ),
        ),
        (
            delivery_runner,
            (
                "evaluate_delivery_candidate_qa",
                "evaluate_delivery_initial_gate",
            ),
        ),
    ):
        for name in names:
            monkeypatch.setattr(module, name, prohibited_execution)
    monkeypatch.setattr(motion_compiler, "main", prohibited_execution)
    monkeypatch.setattr(test_policy_compiler, "main", prohibited_execution)
    monkeypatch.setattr(
        delivery_runner,
        "_run_sealed_compiler_verification",
        prohibited_execution,
    )
    monkeypatch.setattr(
        delivery_runner,
        "_verify_compiled_candidate_motion_config_file_sealed",
        prohibited_execution,
    )
    monkeypatch.setattr(
        delivery_runner,
        "_verify_compiled_candidate_test_policy_file_sealed",
        prohibited_execution,
    )
    monkeypatch.setattr(delivery_runner.subprocess, "run", prohibited_execution)
    monkeypatch.setattr(delivery_runner.subprocess, "Popen", prohibited_execution)
    monkeypatch.setattr(secure_immutable_artifact, "write_new_file", prohibited_execution)

    assert registry_module.editorial_rights_decision_preparation_readiness(REPO_ROOT)[
        "preparation_protocol_available"
    ]
    assert registry_module.owner_source_reconciliation_readiness(REPO_ROOT)["validation_protocol_available"]
    rationalisation_readiness = registry_module.website_source_rationalisation_readiness(REPO_ROOT)
    assert rationalisation_readiness["state"] == "installed-owner-decision-required"
    assert rationalisation_readiness["plan_executed"] is False
    assert rationalisation_readiness["decision_validation_executed"] is False
    assert rationalisation_readiness["module_imported"] is False
    assert registry_module.investor_copy_repair_readiness(REPO_ROOT)["source_bound_protocol_available"]
    assert registry_module.investor_copy_governance_readiness(REPO_ROOT)["decision_verification_available"]
    motion = registry_module.motion_performance_budget_readiness(REPO_ROOT)
    assert motion["state"] == "installed-not-authorised"
    assert motion["audit_executed"] is False
    assert motion["decision_passed"] is False
    candidate_tests = registry_module.candidate_test_evidence_readiness(REPO_ROOT)
    assert candidate_tests["state"] == "installed-not-authorised"
    assert candidate_tests["reviewed_node_toolchain"]["resolved"] is False
    assert candidate_tests["reviewed_node_toolchain"]["executed"] is False
    assert candidate_tests["bounded_process"]["executed"] is False
    assert candidate_tests["test_suite_executed"] is False
    assert candidate_tests["origin_attested"] is False
    assert candidate_tests["evidence_passed"] is False
    candidate_qa = registry_module.candidate_qa_control_plane_readiness(REPO_ROOT)
    assert candidate_qa["state"] == "installed-not-authorised"
    assert candidate_qa["execution_order_enforced"] is True
    assert candidate_qa["qa_execution_authorised"] is False
    assert candidate_qa["qa_executed"] is False
    assert candidate_qa["qa_passed"] is False
    assert candidate_qa["pass_inferred_from_installation"] is False
    ingress = candidate_qa["compiler_verification_ingress"]
    assert ingress["discovery_subprocess_launched"] is False
    assert ingress["sealed_direct_file_read_only"]["executed"] is False
    assert ingress["runner_delegation"]["invoked"] is False
    assert ingress["runner_delegation"]["bounded_popen_protocol_available"] is True


def test_candidate_qa_readiness_fails_closed_without_runner_sealed_delegation(monkeypatch) -> None:
    from aureon.autonomous import aureon_public_website_design_runner as delivery_runner

    monkeypatch.setattr(
        delivery_runner,
        "_verify_compiled_candidate_motion_config_file_sealed",
        None,
    )

    readiness = registry_module.candidate_qa_control_plane_readiness(REPO_ROOT)

    assert readiness["fixed_motion_policy_compiler_available"] is True
    assert readiness["fixed_test_policy_compiler_available"] is True
    assert readiness["v2_runner_available"] is True
    assert readiness["compiler_verification_ingress"]["runner_delegation"]["protocol_available"] is False
    assert readiness["available"] is False
    assert readiness["state"] == "protocol-blocked"
    assert readiness["execution_order_enforced"] is False


def test_candidate_qa_readiness_fails_closed_without_bounded_runner_popen(monkeypatch) -> None:
    from aureon.autonomous import aureon_public_website_design_runner as delivery_runner

    monkeypatch.setattr(delivery_runner, "_run_bounded_sealed_process", None)

    readiness = registry_module.candidate_qa_control_plane_readiness(REPO_ROOT)
    delegation = readiness["compiler_verification_ingress"]["runner_delegation"]

    assert delegation["bounded_popen_protocol_available"] is False
    assert delegation["protocol_available"] is False
    assert delegation["invoked"] is False
    assert readiness["available"] is False
    assert readiness["execution_order_enforced"] is False


def test_candidate_test_readiness_fails_closed_without_reviewed_node_binding(monkeypatch) -> None:
    from aureon.operator import design_candidate_test_evidence as test_evidence

    monkeypatch.setitem(test_evidence.NODE_TOOLCHAIN_BINDING, "locator_authority", "ambient-path")

    readiness = registry_module.candidate_test_evidence_readiness(REPO_ROOT)

    assert readiness["reviewed_node_toolchain"]["protocol_available"] is False
    assert readiness["reviewed_node_toolchain"]["ambient_path_fallback_allowed"] is False
    assert readiness["available"] is False
    assert readiness["execution_protocol_available"] is False


def test_candidate_qa_readiness_fails_closed_without_source_closure_helper(monkeypatch) -> None:
    from aureon.operator import design_candidate_source_closure as source_closure

    monkeypatch.setattr(source_closure, "verify_source_closure", None)

    readiness = registry_module.candidate_qa_control_plane_readiness(REPO_ROOT)
    ingress = readiness["compiler_verification_ingress"]

    assert ingress["imported_api"]["motion_read_only_verifier_available"] is True
    assert ingress["imported_api"]["test_read_only_verifier_available"] is True
    assert ingress["sealed_direct_file_read_only"]["source_closure_helper_available"] is False
    assert ingress["sealed_direct_file_read_only"]["protocol_available"] is False
    assert readiness["available"] is False
    assert readiness["execution_order_enforced"] is False


def test_harmonic_design_docs_bind_v4_asset_readiness_and_worker_authority() -> None:
    documents = [
        (REPO_ROOT / "skills" / "aureon-harmonic-design-suite" / "SKILL.md").read_text(encoding="utf-8"),
        (
            REPO_ROOT
            / "skills"
            / "aureon-harmonic-design-suite"
            / "references"
            / "harmonic-feedback-contract.md"
        ).read_text(encoding="utf-8"),
        (REPO_ROOT / "docs" / "runbooks" / "WEBSITE_OPERATOR.md").read_text(encoding="utf-8"),
    ]

    for document in documents:
        normalized = " ".join(document.split())
        assert "candidate_use_rights_ready" in normalized
        assert "candidate-assets-ready" in normalized
        assert "structural surface replay" in normalized
        assert "no binary read, write, copy, or import authority" in normalized
        assert "no release authority" in normalized
        assert "v4" in normalized.casefold()


def test_harmonic_design_skill_binds_fixed_v2_candidate_qa_order() -> None:
    document = (REPO_ROOT / "skills" / "aureon-harmonic-design-suite" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    normalized = " ".join(document.split())

    assert "read-only candidate-QA control-plane discovery" in normalized
    assert "fixed motion-config compilation" in normalized
    assert "fixed complete test-policy compilation" in normalized
    assert "one handle-bound attempt claim" in normalized
    assert "motion first" in normalized
    assert "candidate-test evidence second" in normalized
    assert "initial browser gate only from `candidate-qa-verified`" in normalized
    assert "no candidate-creation, candidate-validation, canonical, promotion, package" in normalized
    assert "metadata-only-no-subprocess" in normalized
    assert "imported compiler verifier apis are drift-check-only" in normalized.casefold()
    assert "python -i -s -b" in normalized.casefold()
    assert "runner delegation `invoked: false`" in normalized
    assert "the runner verifies already compiled artifacts and does not compile them" in normalized


def test_harmonic_design_docs_bind_investor_copy_gate_without_release_authority() -> None:
    documents = [
        (REPO_ROOT / "skills" / "aureon-harmonic-design-suite" / "SKILL.md").read_text(encoding="utf-8"),
        (
            REPO_ROOT
            / "skills"
            / "aureon-harmonic-design-suite"
            / "references"
            / "harmonic-feedback-contract.md"
        ).read_text(encoding="utf-8"),
        (
            REPO_ROOT / "skills" / "aureon-harmonic-design-suite" / "references" / "release-authority.md"
        ).read_text(encoding="utf-8"),
        (REPO_ROOT / "docs" / "runbooks" / "WEBSITE_OPERATOR.md").read_text(encoding="utf-8"),
    ]

    for document in documents:
        normalized = " ".join(document.split())
        assert "investor_copy_quality_current" in normalized
        assert "privacy-minimised" in normalized
        assert "no release authority" in normalized
        assert "rerun the exact binding before release packaging" in normalized


def test_design_docs_expose_v1_v2_rights_preparation_and_source_bound_copy_repair() -> None:
    skill = (REPO_ROOT / "skills" / "aureon-harmonic-design-suite" / "SKILL.md").read_text(encoding="utf-8")
    website_runbook = (REPO_ROOT / "docs" / "runbooks" / "WEBSITE_OPERATOR.md").read_text(encoding="utf-8")
    copy_runbook = (REPO_ROOT / "docs" / "runbooks" / "INVESTOR_COPY_REPAIR_CONTRACT.md").read_text(
        encoding="utf-8"
    )
    governance_runbook = (
        REPO_ROOT / "docs" / "runbooks" / "INVESTOR_COPY_GOVERNANCE_APPLICATION.md"
    ).read_text(encoding="utf-8")

    normalized_skill = " ".join(skill.split())
    normalized_website = " ".join(website_runbook.split())
    normalized_copy = " ".join(copy_runbook.split())
    normalized_governance = " ".join(governance_runbook.split())
    assert "v1 retained-local source" in normalized_skill
    assert "v2 exact verified-live-backup source" in normalized_skill
    assert "never makes or infers the human decision" in normalized_skill
    assert "source-bound investor-copy task/work-order preflight" in normalized_skill
    assert "read-only task/policy/claim preflight" in normalized_website
    assert "Protocol availability is not a current contract" in normalized_website
    assert "does not choose the source" in normalized_copy
    assert "Both preflights are read-only" in normalized_copy
    assert "system access" in normalized_governance
    assert "not an approval" in normalized_governance
    assert "does not apply anything" in normalized_governance
    assert "never edits `website/`" in normalized_governance
    assert "grants no candidate, package, release" in normalized_governance


def test_harmonic_design_skill_keeps_new_qa_protocols_non_authoritative() -> None:
    skill = (REPO_ROOT / "skills" / "aureon-harmonic-design-suite" / "SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(skill.split())

    assert "A worker's `passed` string is request bookkeeping, not test evidence." in normalized
    assert "origin_attested: false" in normalized
    assert "trusted orchestration seal" in normalized
    assert "evidence_passed: true" in normalized
    assert "decision.status: pass" in normalized
    assert "decision.eligible_for_next_local_gate: true" in normalized
    assert "installed motion/performance-budget protocol is not a pass" in normalized
    assert "no candidate, promotion, package, release or deployment authority" in normalized


def test_registry_verifier_detects_source_drift_without_granting_release_authority() -> None:
    registry = deepcopy(discover_design_capability_registry(REPO_ROOT))
    registry["sources"][0]["sha256"] = "0" * 64

    result = verify_design_capability_registry(registry, repo_root=REPO_ROOT)

    assert result["passed"] is False
    assert _check(result, "source-freshness")["passed"] is False
    assert result["release_eligible"] is False
    assert result["deployment_authority"] == "none"


def test_registry_verifier_rejects_claimed_deployment_authority() -> None:
    registry = deepcopy(discover_design_capability_registry(REPO_ROOT))
    registry["authority"]["deployment_authority"] = "registry"

    result = verify_design_capability_registry(registry, repo_root=REPO_ROOT)

    assert result["passed"] is False
    assert _check(result, "non-authoritative-boundary")["passed"] is False
    assert result["release_eligible"] is False


def test_registry_verifier_rejects_imported_static_integrity_authority_claim() -> None:
    registry = deepcopy(discover_design_capability_registry(REPO_ROOT))
    registry["website_runtime_measurement_static_integrity_readiness"]["imported_api_authoritative"] = True

    result = verify_design_capability_registry(registry, repo_root=REPO_ROOT)

    assert result["passed"] is False
    assert _check(result, "website-runtime-measurement-static-integrity-boundary")["passed"] is False
    assert result["release_eligible"] is False
    assert result["deployment_authority"] == "none"


def test_registry_verifier_rejects_unsafe_source_path() -> None:
    registry = deepcopy(discover_design_capability_registry(REPO_ROOT))
    registry["sources"][0]["path"] = "../outside.txt"

    result = verify_design_capability_registry(registry, repo_root=REPO_ROOT)

    assert result["passed"] is False
    assert _check(result, "source-freshness")["passed"] is False


def test_brief_blockage_does_not_falsely_break_static_capability_verification(monkeypatch) -> None:
    blocked_readiness = {
        "available": True,
        "state": "brief-blocked",
        "brief_ready": False,
        "planning_pipeline_available": False,
        "candidate_delivery_ready": False,
        "release_eligible": False,
        "deployment_authority": "none",
        "brief": {},
        "next_required_stage": "repair the brief",
        "error": "stale evidence",
    }
    monkeypatch.setattr(
        registry_module,
        "design_evidence_brief_readiness",
        lambda _root: blocked_readiness,
    )

    registry = registry_module.discover_design_capability_registry(REPO_ROOT)

    assert registry["verification"]["passed"] is True
    assert registry["design_evidence_brief_readiness"] == blocked_readiness


def test_importer_readiness_keeps_rights_separate_from_candidate_asset_state(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        registry_module,
        "editorial_asset_provenance_readiness",
        lambda _root: {
            "candidate_use_rights_ready": True,
            "candidate_asset_ready": True,
        },
    )

    readiness = registry_module.editorial_asset_importer_readiness(REPO_ROOT)

    assert readiness["state"] == "installed-rights-ready-awaiting-candidate-import"
    assert readiness["candidate_use_rights_ready"] is True
    assert readiness["candidate_asset_ready"] is False
    assert readiness["candidate_import_ready"] is False
    assert readiness["candidate_delivery_ready"] is False
    assert readiness["release_eligible"] is False
    assert readiness["package_authority"] == "none"
    assert readiness["deployment_authority"] == "none"


def test_provenance_rights_readiness_does_not_claim_candidate_asset_state(
    monkeypatch,
) -> None:
    integrity_check_ids = {
        "canonical-manifest-binding",
        "global-artwork-policy-not-cleared",
        "redacted-evidence-integrity",
        "delivery-rights-separation",
        "asset-byte-and-inventory-integrity",
        "candidate-rights-closure",
    }
    receipt = {
        "passed": True,
        "state": "pass",
        "checks": [{"id": identifier, "passed": True} for identifier in sorted(integrity_check_ids)],
        "manifest": {
            "manifest_id": "editorial-assets",
            "path": "data/website_operator/editorial_asset_provenance.v1.json",
            "sha256": "A" * 64,
        },
        "global_artwork_policy": {
            "state": "not-cleared",
            "cleared_for_use": False,
        },
        "public_coverage": {
            "all_current_references_authorised": True,
            "all_current_copy_bindings_closed": True,
            "coverage_sha256": "B" * 64,
        },
        "summary": {
            "mapped_asset_count": 1,
            "unmapped_asset_count": 0,
            "currently_referenced_asset_count": 1,
            "unapproved_current_asset_count": 0,
            "current_copy_drift_asset_count": 0,
            "candidate_use_ready_count": 1,
        },
        "asset_capsules_sha256": "C" * 64,
        "route_asset_capsules_sha256": "D" * 64,
    }
    monkeypatch.setattr(
        "aureon.operator.design_editorial_asset_provenance.audit_design_editorial_asset_provenance_file",
        lambda *, repo_root: receipt,
    )

    readiness = registry_module.editorial_asset_provenance_readiness(REPO_ROOT)

    assert readiness["candidate_use_rights_ready"] is True
    assert readiness["candidate_asset_ready"] is False
    assert readiness["candidate_delivery_ready"] is False
    assert readiness["release_eligible"] is False
