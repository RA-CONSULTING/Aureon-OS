from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from aureon.autonomous.aureon_coding_agent_skill_base import (
    build_and_write_profile,
    public_website_design_registry_snapshot,
    website_source_rationalisation_readiness,
)
from aureon.core.goal_execution_engine import GoalExecutionEngine
from aureon.inhouse_ai.tool_registry import ToolRegistry

REPO_ROOT = Path(__file__).resolve().parents[1]


def _fake_repo(root: Path) -> None:
    (root / "aureon" / "demo").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "tests").mkdir()
    (root / "frontend" / "src").mkdir(parents=True)
    (root / "aureon" / "demo" / "worker.py").write_text(
        "def run_worker():\n    return 'ok'\n", encoding="utf-8"
    )
    (root / "tests" / "test_worker.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (root / "frontend" / "src" / "App.tsx").write_text(
        'import { AureonWorkOrderExecutionConsole } from "@/components/generated/AureonWorkOrderExecutionConsole";\n'
        "export default function App() {\n"
        "  return (\n"
        "    <main>\n"
        "        <AureonWorkOrderExecutionConsole />\n"
        "    </main>\n"
        "  );\n"
        "}\n",
        encoding="utf-8",
    )


def test_tool_registry_exposes_coder_learning_tools(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    registry = ToolRegistry(include_builtins=True, hnc_coherence_required=False)

    assert {"web_search", "web_fetch", "repo_search", "skill_base_status"}.issubset(set(registry.names()))
    result = json.loads(registry.execute("repo_search", {"pattern": "run_worker", "directory": "aureon"}))
    assert result["hit_count"] == 1


def test_coding_skill_base_import_is_passive_without_audit_environment() -> None:
    environment = os.environ.copy()
    environment.pop("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", None)
    environment.pop("AUREON_AUDIT_MODE", None)

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from aureon.autonomous.aureon_coding_agent_skill_base import "
            "public_website_design_registry_snapshot; print('skill-base-clean-import-ok')",
        ],
        cwd=REPO_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout == "skill-base-clean-import-ok\n"
    assert "Timeline Oracle" not in completed.stderr
    assert "WhaleSonar" not in completed.stderr


def test_registry_snapshot_exposes_static_integrity_without_production_authority() -> None:
    snapshot = public_website_design_registry_snapshot(REPO_ROOT)
    readiness = snapshot["website_runtime_measurement_static_integrity_readiness"]

    assert readiness["static_integrity_validation_available"] is True
    assert readiness["static_integrity_validation_executed"] is False
    assert readiness["measurement_provenance_verification_available"] is False
    assert readiness["production_eligible"] is False
    assert readiness["worker_available"] is False
    assert readiness["artifact_emission_available"] is False
    assert readiness["trusted_static_integrity_execution_path"] == "fresh-isolated-launcher-only"
    assert readiness["imported_api_authoritative"] is False
    assert readiness["deployment_authority"] == "none"


def test_source_rationalisation_readiness_is_metadata_only_and_qa_scoped() -> None:
    readiness = website_source_rationalisation_readiness(REPO_ROOT)

    assert readiness["available"] is True
    assert readiness["state"] == "installed-not-executed"
    assert readiness["discovery_mode"] == "metadata-only-ast-no-import-no-subprocess"
    assert readiness["module_imported"] is False
    assert readiness["launcher_available"] is True
    assert readiness["discovery_subprocess_launched"] is False
    assert readiness["source_sha256"] == readiness["expected_source_sha256"]
    assert readiness["source_hash_matches"] is True
    assert readiness["public_signatures_locked"] is True
    assert readiness["repo_code_imported"] is False
    assert readiness["launcher_sha256"] == readiness["expected_launcher_sha256"]
    assert readiness["launcher_hash_matches"] is True
    assert readiness["launcher_repo_code_imported"] is False
    assert readiness["planning_protocol_available"] is True
    assert readiness["owner_decision_validation_protocol_available"] is True
    assert readiness["planning_executed_during_discovery"] is False
    assert readiness["owner_decision_validation_executed_during_discovery"] is False
    assert readiness["writes_during_discovery"] is False
    assert readiness["missing_symbols"] == []
    assert readiness["allowed_role"] == "PublicWebsiteDesignQA"
    assert readiness["text_worker_authority"] == "none"
    assert readiness["owner_decision_maximum_age_hours"] == 4
    assert readiness["fixed_footprint_thresholds"] == {
        "max_total_bytes": 4_500_000,
        "max_image_bytes": 2_200_000,
        "max_css_bytes": 350_000,
        "max_single_asset_bytes": 500_000,
    }
    assert readiness["autonomous_owner_decision"] is False
    assert readiness["omission_proves_readiness"] is False
    assert readiness["staging_authority"] == "none"
    assert readiness["physical_source_file_removal"] == "none"
    assert readiness["canonical_website_mutation"] == "none"
    assert readiness["candidate_authority"] == "none"
    assert readiness["package_authority"] == "none"
    assert readiness["release_eligible"] is False
    assert readiness["deployment_authority"] == "none"
    assert readiness["credential_access"] == "none"
    assert readiness["network_access"] == "none"


def test_source_rationalisation_readiness_rejects_unreviewed_source_drift(
    tmp_path: Path,
) -> None:
    module_path = tmp_path / "aureon" / "operator" / "website_source_rationalisation.py"
    module_path.parent.mkdir(parents=True)
    reviewed_source = (REPO_ROOT / "aureon" / "operator" / "website_source_rationalisation.py").read_text(
        encoding="utf-8"
    )
    module_path.write_text(reviewed_source + "\n# unreviewed drift\n", encoding="utf-8")
    launcher = tmp_path / "tools" / "run-website-source-rationalisation.py"
    launcher.parent.mkdir(parents=True)
    launcher.write_bytes((REPO_ROOT / "tools" / "run-website-source-rationalisation.py").read_bytes())
    runbook = tmp_path / "docs" / "runbooks" / "WEBSITE_SOURCE_RATIONALISATION.md"
    runbook.parent.mkdir(parents=True)
    runbook.write_text("# test fixture\n", encoding="utf-8")

    readiness = website_source_rationalisation_readiness(tmp_path)

    assert readiness["state"] == "needs-repair"
    assert readiness["source_hash_matches"] is False
    assert readiness["launcher_hash_matches"] is True
    assert readiness["planning_protocol_available"] is False
    assert readiness["owner_decision_validation_protocol_available"] is False


def test_coding_agent_skill_base_writes_profile_and_mount(tmp_path: Path) -> None:
    _fake_repo(tmp_path)

    result = build_and_write_profile("Teach Aureon coder agents and skills", root=tmp_path, online=False)
    app_text = (tmp_path / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")

    assert result["schema_version"] == "aureon-coding-agent-skill-base-v2"
    assert result["summary"]["coder_agent_count"] >= 5
    assert result["summary"]["coding_logic_rule_count"] >= 6
    assert result["summary"]["web_tools_ready"] is True
    assert result["summary"]["public_website_design_skill_count"] >= 20
    assert result["write_info"]["writer"] == "bounded-local-writer"
    design_stack = result["public_website_design_skill_stack"]
    assert design_stack["goal_intent"] == "public_website_design_cycle"
    assert design_stack["capability_family"] == "website_design"
    assert design_stack["authority"]["deployment"] == "WebsiteOperator owner gate only"
    assert "verify_dependency_closure" in design_stack["levels"]["L0_atomic"]
    assert "bind_owner_source_reconciliation" in design_stack["levels"]["L0_atomic"]
    assert "validate_owner_source_reconciliation" in design_stack["levels"]["L0_atomic"]
    assert "plan_website_source_rationalisation" in design_stack["levels"]["L0_atomic"]
    assert "validate_website_source_rationalisation_owner_decision" in design_stack["levels"]["L0_atomic"]
    assert "validate_runtime_optimisation_measurement_evidence" in design_stack["levels"]["L0_atomic"]
    assert "validate_runtime_optimisation_static_integrity" in design_stack["levels"]["L0_atomic"]
    assert "compile_runtime_optimisation_proposal" not in design_stack["levels"]["L0_atomic"]
    assert "audit_design_research_refresh" in design_stack["levels"]["L0_atomic"]
    assert "audit_editorial_asset_provenance" in design_stack["levels"]["L0_atomic"]
    assert "prepare_editorial_asset_rights_decisions" in design_stack["levels"]["L0_atomic"]
    assert "import_verified_editorial_assets_to_staged_candidate" in design_stack["levels"]["L0_atomic"]
    assert "verify_editorial_asset_candidate_import" in design_stack["levels"]["L0_atomic"]
    assert "audit_investor_copy_quality" in design_stack["levels"]["L0_atomic"]
    assert "preflight_investor_copy_repair_contract" in design_stack["levels"]["L0_atomic"]
    assert "preflight_investor_copy_repair_work_order" in design_stack["levels"]["L0_atomic"]
    assert "verify_investor_copy_repair_contract" in design_stack["levels"]["L0_atomic"]
    assert "evaluate_investor_copy_repair_candidate" in design_stack["levels"]["L0_atomic"]
    assert "verify_investor_copy_governance_decision" in design_stack["levels"]["L0_atomic"]
    assert "simulate_investor_copy_governance_application" in design_stack["levels"]["L0_atomic"]
    assert "apply_exact_owner_approved_investor_copy_governance_delta" in design_stack["levels"]["L0_atomic"]
    assert "build_source_neutral_hnc_evidence_graph" in design_stack["levels"]["L0_atomic"]
    assert "audit_design_evidence_brief" in design_stack["levels"]["L0_atomic"]
    assert "create_brief_bound_delivery_job" in design_stack["levels"]["L0_atomic"]
    assert "issue_staged_design_worker_lease" in design_stack["levels"]["L0_atomic"]
    assert "submit_staged_design_worker_delivery" in design_stack["levels"]["L0_atomic"]
    assert "advance_staged_delivery_receipt" in design_stack["levels"]["L0_atomic"]
    assert "create_reconciled_source_bound_work_order" in design_stack["levels"]["L0_atomic"]
    assert "stage_candidate_tree" in design_stack["levels"]["L0_atomic"]
    assert "evaluate_candidate_initial_gate" in design_stack["levels"]["L0_atomic"]
    assert "inspect_candidate_qa_control_plane_readiness" in design_stack["levels"]["L0_atomic"]
    assert "inspect_candidate_compiler_verification_ingress" in design_stack["levels"]["L0_atomic"]
    assert "audit_candidate_static_qa" in design_stack["levels"]["L0_atomic"]
    assert "compile_fixed_candidate_motion_config" in design_stack["levels"]["L0_atomic"]
    assert "verify_fixed_candidate_motion_config" in design_stack["levels"]["L0_atomic"]
    assert "compile_fixed_candidate_test_policy" in design_stack["levels"]["L0_atomic"]
    assert "verify_fixed_candidate_test_policy" in design_stack["levels"]["L0_atomic"]
    assert "delegate_sealed_read_only_compiler_verification_to_runner" in design_stack["levels"]["L0_atomic"]
    assert "claim_one_shot_candidate_qa_attempt" in design_stack["levels"]["L0_atomic"]
    assert "evaluate_candidate_qa_motion_first" in design_stack["levels"]["L0_atomic"]
    assert "audit_motion_performance_budget" in design_stack["levels"]["L0_atomic"]
    assert "replay_motion_performance_budget_receipt" in design_stack["levels"]["L0_atomic"]
    assert "execute_hash_bound_candidate_test_suite" in design_stack["levels"]["L0_atomic"]
    assert "verify_candidate_test_evidence_receipt" in design_stack["levels"]["L0_atomic"]
    assert "attribute_research_route_layout" in design_stack["levels"]["L0_atomic"]
    assert "staged_candidate_change_control" in design_stack["levels"]["L3_workflow"]
    assert "staged-candidate-only" in design_stack["authority"]["local_website_mutation"]
    assert "source-bound focused browser decision" in design_stack["authority"]["candidate_initial_gate"]
    assert "owner-supplied" in design_stack["authority"]["owner_source_reconciliation"]
    assert "v1 decision" in design_stack["authority"]["owner_source_reconciliation"]
    assert "v2 decision" in design_stack["authority"]["owner_source_reconciliation"]
    assert "never makes or infers" in design_stack["authority"]["editorial_rights_decision_preparation"]
    assert "runtime-only" in design_stack["authority"]["research_route_attribution"]
    assert "not-cleared artwork" in design_stack["authority"]["design_research_refresh"]
    assert "global artwork remains not-cleared" in design_stack["authority"]["editorial_asset_provenance"]
    assert (
        "trusted content-addressed WebP import"
        in design_stack["authority"]["editorial_asset_candidate_importer"]
    )
    assert "hard-coded traction" in design_stack["authority"]["investor_copy_quality"]
    assert "source-bound contract" in design_stack["authority"]["investor_copy_repair"]
    assert "no source selection" in design_stack["authority"]["investor_copy_repair"]
    assert "shadow simulation are read-only" in design_stack["authority"]["investor_copy_governance"]
    assert "broad system-access approval is invalid" in design_stack["authority"]["investor_copy_governance"]
    assert (
        "no website, policy, candidate, package, release"
        in design_stack["authority"]["investor_copy_governance"]
    )
    assert "zero binary or network requests" in design_stack["authority"]["hnc_evidence_graph"]
    assert "planning input only" in design_stack["authority"]["design_evidence_brief"]
    assert "awaiting-owner-promotion" in design_stack["authority"]["staged_delivery_runner"]
    assert "short-lived lease" in design_stack["authority"]["staged_worker_broker"]
    assert "decision.status pass" in design_stack["authority"]["motion_performance_budget"]
    assert "eligible_for_next_local_gate true" in design_stack["authority"]["motion_performance_budget"]
    assert "worker pass strings are not evidence" in design_stack["authority"]["candidate_test_evidence"]
    assert "origin_attested false" in design_stack["authority"]["candidate_test_evidence"]
    assert "trusted orchestration seal" in design_stack["authority"]["candidate_test_evidence"]
    assert "evidence_passed true" in design_stack["authority"]["candidate_test_evidence"]
    assert "installed-not-authorised" in design_stack["authority"]["candidate_qa_control_plane"]
    assert "motion first" in design_stack["authority"]["candidate_qa_control_plane"]
    assert (
        "initial browser gate only from candidate-qa-verified"
        in (design_stack["authority"]["candidate_qa_control_plane"])
    )
    compiler_ingress = design_stack["authority"]["candidate_qa_compiler_verification_ingress"]
    assert "metadata-only discovery launches no subprocess" in compiler_ingress
    assert "imported read-only verifier APIs are drift-check-only" in compiler_ingress
    assert "python -I -S -B" in compiler_ingress
    assert "delegated only by the V2 delivery runner" in compiler_ingress
    assert design_stack["candidate_qa_gate_order"] == [
        "compile-fixed-motion-config",
        "compile-fixed-test-policy",
        "run-motion-budget-first",
        "run-complete-trusted-test-policy",
        "enter-initial-browser-gate-only-after-qa-verification",
    ]
    assert design_stack["authority"]["candidate_staging"].startswith("artifacts/website-candidates/")
    assert design_stack["role_capability_grants"]["PublicWebsiteDesignQA"] == [
        "plan_website_source_rationalisation",
        "validate_website_source_rationalisation_owner_decision",
        "validate_runtime_optimisation_measurement_evidence",
        "validate_runtime_optimisation_static_integrity",
    ]
    assert design_stack["role_capability_grants"]["PublicWebsiteDesignWorker"] == []
    source_rationalisation_authority = design_stack["authority"]["website_source_rationalisation"]
    assert "PublicWebsiteDesignQA alone" in source_rationalisation_authority
    assert "at most four hours" in source_rationalisation_authority
    assert "Discovery executes neither operation" in source_rationalisation_authority
    assert "omission does not prove readiness" in source_rationalisation_authority
    assert "PublicWebsiteDesignWorker receives no capability" in source_rationalisation_authority
    runtime_optimisation_authority = design_stack["authority"]["website_runtime_optimisation"]
    assert "structural-only" in runtime_optimisation_authority
    assert "Production proposal compilation and writing are hard-blocked" in runtime_optimisation_authority
    assert "QA therefore receives no compile grant" in runtime_optimisation_authority
    assert "not-executed" in runtime_optimisation_authority
    assert "blocked-not-run" in runtime_optimisation_authority
    assert "PublicWebsiteDesignWorker receives no capability" in runtime_optimisation_authority
    static_integrity_authority = design_stack["authority"]["website_runtime_measurement_static_integrity"]
    assert "provenance-unverified and production-blocked" in static_integrity_authority
    assert "producer execution" in static_integrity_authority
    assert "full media decode" in static_integrity_authority
    assert "creates no artifact" in static_integrity_authority
    assert "fresh hash-authenticated python -I -S -B launcher" in static_integrity_authority
    assert "imported APIs are non-authoritative" in static_integrity_authority
    assert "PublicWebsiteDesignWorker receives no capability" in static_integrity_authority
    coder_names = {agent["name"] for agent in result["coder_agents"]}
    assert {"PublicWebsiteDesignWorker", "PublicWebsiteDesignQA"}.issubset(coder_names)
    website_worker = next(
        agent for agent in result["coder_agents"] if agent["name"] == "PublicWebsiteDesignWorker"
    )
    assert "data/website_operator/investor_site_design_brief.v1.json" in website_worker["reads"]
    assert "data/website_operator/design_research_sources.v1.json" in website_worker["reads"]
    assert "data/website_operator/editorial_asset_provenance.v1.json" in website_worker["reads"]
    assert "data/website_operator/investor_copy_quality_policy.v1.json" in website_worker["reads"]
    assert "data/website_operator/hnc_evidence_graph.v1.json" in website_worker["reads"]
    assert "aureon/autonomous/aureon_staged_design_worker_broker.py" in website_worker["reads"]
    assert "aureon/operator/design_editorial_asset_candidate_importer.py" not in website_worker["reads"]
    assert "aureon/operator/website_source_rationalisation.py" not in website_worker["reads"]
    assert "tools/run-website-source-rationalisation.py" not in website_worker["reads"]
    assert "docs/runbooks/WEBSITE_SOURCE_RATIONALISATION.md" not in website_worker["reads"]
    assert "aureon/operator/website_runtime_optimisation.py" not in website_worker["reads"]
    assert "tools/run-website-runtime-optimisation.py" not in website_worker["reads"]
    assert "aureon/operator/website_runtime_measurement_provenance.py" not in website_worker["reads"]
    assert "tools/run-website-runtime-measurement-provenance.py" not in website_worker["reads"]
    assert "docs/runbooks/WEBSITE_RUNTIME_OPTIMISATION.md" not in website_worker["reads"]
    assert all("source-rationalisation" not in tool for tool in website_worker["tools"])
    website_qa = next(agent for agent in result["coder_agents"] if agent["name"] == "PublicWebsiteDesignQA")
    assert "aureon/operator/design_editorial_asset_candidate_importer.py" in website_qa["reads"]
    assert "aureon/operator/design_investor_copy_governance.py" in website_qa["reads"]
    assert "aureon/operator/design_motion_performance_budget.py" in website_qa["reads"]
    assert "aureon/operator/design_candidate_test_evidence.py" in website_qa["reads"]
    assert "aureon/operator/secure_immutable_artifact.py" in website_qa["reads"]
    assert "aureon/operator/design_candidate_static_qa.py" in website_qa["reads"]
    assert "aureon/operator/design_candidate_motion_policy_compiler.py" in website_qa["reads"]
    assert "aureon/operator/design_candidate_test_policy_compiler.py" in website_qa["reads"]
    assert "aureon/operator/design_candidate_source_closure.py" in website_qa["reads"]
    assert "aureon/autonomous/aureon_public_website_design_runner.py" in website_qa["reads"]
    assert "aureon/operator/website_source_rationalisation.py" in website_qa["reads"]
    assert "tools/run-website-source-rationalisation.py" in website_qa["reads"]
    assert "docs/runbooks/WEBSITE_SOURCE_RATIONALISATION.md" in website_qa["reads"]
    assert "aureon/operator/website_runtime_optimisation.py" in website_qa["reads"]
    assert "tools/run-website-runtime-optimisation.py" in website_qa["reads"]
    assert "aureon/operator/website_runtime_measurement_provenance.py" in website_qa["reads"]
    assert "tools/run-website-runtime-measurement-provenance.py" in website_qa["reads"]
    assert "data/website_operator/browser_acceptance_contract.v1.json" in website_qa["reads"]
    assert (
        "docs/research/schemas/AUREON_WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_V1.schema.json"
        in website_qa["reads"]
    )
    assert "docs/runbooks/WEBSITE_RUNTIME_OPTIMISATION.md" in website_qa["reads"]
    assert "tests/test_website_runtime_measurement_provenance.py" in website_qa["reads"]
    assert "trusted candidate-test evidence control" in website_qa["tools"]
    assert "deterministic motion/performance budget control" in website_qa["tools"]
    assert "read-only candidate QA control-plane readiness" in website_qa["tools"]
    assert "imported compiler read-only drift-check APIs (not sealed ingress)" in website_qa["tools"]
    assert "runner-delegated sealed direct-file compiler verification" in website_qa["tools"]
    assert "V2 one-attempt candidate-QA runner" in website_qa["tools"]
    assert "website source-rationalisation planning protocol" in website_qa["tools"]
    assert "website source-rationalisation owner-decision validation protocol" in website_qa["tools"]
    assert (
        "website runtime-optimisation structural validator with production compilation blocked"
        in website_qa["tools"]
    )
    assert (
        "fresh isolated-launcher runtime measurement static-integrity validator with provenance unverified and production blocked"
        in website_qa["tools"]
    )
    assert any("decision.status pass" in item for item in website_qa["evidence_required"])
    assert any("origin_attested false" in item for item in website_qa["evidence_required"])
    assert any("exact threshold-set hash" in item for item in website_qa["evidence_required"])
    assert any("complete ordered command-id hash" in item for item in website_qa["evidence_required"])
    assert any("python -I -S -B" in item for item in website_qa["evidence_required"])
    assert any("candidate-qa-verified" in item for item in website_qa["evidence_required"])
    assert any(
        "proposal-only source-rationalisation plan" in item for item in website_qa["evidence_required"]
    )
    assert any("maximum four-hour window" in item for item in website_qa["evidence_required"])
    assert "cannot select or relax" in website_qa["safety_boundary"]
    assert "cannot infer a pass" in website_qa["safety_boundary"]
    assert "Imported compiler verification is drift-check-only" in website_qa["safety_boundary"]
    assert "discovery itself launches no subprocess" in website_qa["safety_boundary"]
    assert "cannot create or edit an owner decision" in website_qa["safety_boundary"]
    assert "cannot" in website_qa["safety_boundary"]
    assert "governance apply" in website_qa["safety_boundary"]
    assert "Source-rationalisation discovery is metadata-only" in website_qa["safety_boundary"]
    assert "The text worker has no source-rationalisation capability" in website_qa["safety_boundary"]
    assert "lease id" in website_worker["evidence_required"]
    assert "built-in manifest-patch applier" in website_worker["tools"]
    assert any("pass strings are not evidence" in item for item in website_worker["evidence_required"])
    assert "turn a submitted `passed` string into evidence" in website_worker["safety_boundary"]
    assert "design-evidence brief SHA-256" in website_worker["evidence_required"]
    assert "redacted design-research declaration SHA-256" in website_worker["evidence_required"]
    assert result["summary"]["public_website_design_research_refresh_current"] is False
    assert (
        result["summary"]["public_website_design_source_rationalisation_planning_protocol_available"] is False
    )
    assert (
        result["summary"][
            "public_website_design_source_rationalisation_owner_decision_validation_protocol_available"
        ]
        is False
    )
    assert (
        result["summary"]["public_website_design_source_rationalisation_discovery_planning_executed"] is False
    )
    assert (
        result["summary"]["public_website_design_source_rationalisation_discovery_validation_executed"]
        is False
    )
    assert (
        result["summary"]["public_website_design_source_rationalisation_autonomous_owner_decision"] is False
    )
    assert (
        result["summary"]["public_website_design_source_rationalisation_omission_proves_readiness"] is False
    )
    assert result["summary"]["public_website_design_source_rationalisation_text_worker_authority"] == "none"
    assert (
        result["summary"]["public_website_design_runtime_optimisation_proposal_protocol_available"] is False
    )
    assert (
        result["summary"]["public_website_design_runtime_optimisation_measurement_validation_available"]
        is False
    )
    assert result["summary"]["public_website_design_runtime_optimisation_browser_contract_available"] is False
    assert (
        result["summary"]["public_website_design_runtime_optimisation_measurement_schema_available"] is False
    )
    assert result["summary"]["public_website_design_runtime_optimisation_proposal_schema_available"] is False
    assert (
        result["summary"]["public_website_design_runtime_optimisation_measurement_provenance_verified"]
        is False
    )
    assert (
        result["summary"]["public_website_design_runtime_optimisation_production_compilation_blocked"] is True
    )
    assert result["summary"]["public_website_design_runtime_optimisation_discovery_executed"] is False
    assert (
        result["summary"]["public_website_design_runtime_optimisation_autonomous_source_selection"] is False
    )
    assert (
        result["summary"]["public_website_design_runtime_optimisation_autonomous_measurement_evidence"]
        is False
    )
    assert result["summary"]["public_website_design_runtime_measurement_static_integrity_available"] is False
    assert result["summary"]["public_website_design_runtime_measurement_static_integrity_executed"] is False
    assert (
        result["summary"]["public_website_design_runtime_measurement_static_integrity_production_eligible"]
        is False
    )
    assert (
        result["summary"]["public_website_design_runtime_measurement_static_integrity_worker_available"]
        is False
    )
    assert (
        result["summary"]["public_website_design_runtime_measurement_static_integrity_execution_path"]
        == "unavailable"
    )
    assert (
        result["summary"][
            "public_website_design_runtime_measurement_static_integrity_imported_api_authoritative"
        ]
        is False
    )
    assert result["summary"]["public_website_design_owner_source_validation_protocol_available"] is False
    assert result["summary"]["public_website_design_owner_source_v1_retain_local_supported"] is False
    assert result["summary"]["public_website_design_owner_source_v2_verified_live_backup_supported"] is False
    assert result["summary"]["public_website_design_autonomous_source_selection"] is False
    assert result["summary"]["public_website_design_editorial_asset_integrity_verified"] is False
    assert result["summary"]["public_website_design_editorial_asset_public_use_ready"] is False
    assert result["summary"]["public_website_design_editorial_rights_preparation_protocol_available"] is False
    assert result["summary"]["public_website_design_autonomous_human_rights_decision"] is False
    assert result["summary"]["public_website_design_editorial_import_protocol_available"] is False
    assert result["summary"]["public_website_design_editorial_import_ready"] is False
    assert result["summary"]["public_website_design_investor_copy_ready"] is False
    assert result["summary"]["public_website_design_investor_copy_repair_protocol_available"] is False
    assert (
        result["summary"]["public_website_design_investor_copy_repair_candidate_reaudit_available"] is False
    )
    assert result["summary"]["public_website_design_investor_copy_repair_current_contract_ready"] is False
    assert result["summary"]["public_website_design_investor_copy_governance_verification_available"] is False
    assert result["summary"]["public_website_design_investor_copy_governance_simulation_available"] is False
    assert (
        result["summary"]["public_website_design_investor_copy_governance_apply_protocol_available"] is False
    )
    assert (
        result["summary"]["public_website_design_investor_copy_governance_implementation_tooling_verified"]
        is False
    )
    assert (
        result["summary"]["public_website_design_investor_copy_governance_current_owner_decision_present"]
        is False
    )
    assert (
        result["summary"]["public_website_design_investor_copy_governance_current_apply_authorised"] is False
    )
    assert result["summary"]["public_website_design_investor_copy_governance_current_apply_ready"] is False
    assert (
        result["summary"]["public_website_design_investor_copy_governance_broad_access_approval_valid"]
        is False
    )
    assert result["summary"]["public_website_design_hnc_graph_bundle_ready"] is False
    assert result["summary"]["public_website_design_hnc_graph_candidate_transplant_ready"] is False
    assert result["summary"]["public_website_design_brief_ready"] is False
    assert result["summary"]["public_website_design_planning_pipeline_available"] is False
    assert result["summary"]["public_website_design_worker_broker_protocol_available"] is False
    assert result["summary"]["public_website_design_motion_budget_protocol_available"] is False
    assert result["summary"]["public_website_design_motion_budget_passed"] is False
    assert result["summary"]["public_website_design_candidate_test_protocol_available"] is False
    assert (
        result["summary"]["public_website_design_candidate_test_reviewed_node_toolchain_available"] is False
    )
    assert result["summary"]["public_website_design_candidate_test_bounded_popen_available"] is False
    assert result["summary"]["public_website_design_candidate_test_origin_attested"] is False
    assert result["summary"]["public_website_design_candidate_test_evidence_passed"] is False
    assert result["summary"]["public_website_design_candidate_qa_control_plane_available"] is False
    assert result["summary"]["public_website_design_imported_compiler_drift_check_apis_available"] is False
    assert result["summary"]["public_website_design_sealed_compiler_read_only_protocol_available"] is False
    assert result["summary"]["public_website_design_sealed_compiler_runner_delegation_available"] is False
    assert result["summary"]["public_website_design_candidate_qa_discovery_subprocess_launched"] is False
    assert result["summary"]["public_website_design_candidate_qa_executed"] is False
    assert result["summary"]["public_website_design_candidate_qa_passed"] is False
    assert result["summary"]["public_website_design_candidate_delivery_ready"] is False
    assert result["safety"]["public_website_design_worker_pass_strings_are_evidence"] is False
    assert result["safety"]["public_website_design_motion_budget_pass_inferred_from_installation"] is False
    assert result["safety"]["public_website_design_candidate_test_pass_inferred_from_installation"] is False
    assert result["safety"]["public_website_design_candidate_test_origin_attested"] is False
    assert (
        result["safety"]["public_website_design_candidate_test_trusted_orchestration_seal_required"] is True
    )
    assert result["safety"]["public_website_design_candidate_qa_control_plane_execution_authorised"] is False
    assert result["safety"]["public_website_design_candidate_qa_pass_inferred_from_installation"] is False
    assert (
        result["safety"]["public_website_design_candidate_qa_policy_or_threshold_selection_authority"]
        is False
    )
    assert (
        result["safety"]["public_website_design_imported_compiler_pre_import_source_authentication"] is False
    )
    assert (
        result["safety"]["public_website_design_direct_compiler_verifier_agent_execution_authorised"] is False
    )
    assert result["safety"]["public_website_design_candidate_qa_discovery_launches_subprocess"] is False
    assert result["safety"]["public_website_design_qa_candidate_or_promotion_authority"] is False
    assert result["safety"]["public_website_design_qa_package_or_deploy_authority"] is False
    assert (
        result["safety"]["public_website_design_source_rationalisation_discovery_executes_planning"] is False
    )
    assert (
        result["safety"]["public_website_design_source_rationalisation_discovery_executes_validation"]
        is False
    )
    assert result["safety"]["public_website_design_source_rationalisation_autonomous_owner_decision"] is False
    assert result["safety"]["public_website_design_source_rationalisation_text_worker_authority"] is False
    assert result["safety"]["public_website_design_source_rationalisation_staging_authority"] is False
    assert result["safety"]["public_website_design_source_rationalisation_deletion_authority"] is False
    assert (
        result["safety"]["public_website_design_source_rationalisation_candidate_or_canonical_authority"]
        is False
    )
    assert (
        result["safety"]["public_website_design_source_rationalisation_package_release_or_deploy_authority"]
        is False
    )
    assert (
        result["safety"]["public_website_design_source_rationalisation_credential_or_network_authority"]
        is False
    )
    assert result["safety"]["public_website_design_source_rationalisation_omission_proves_readiness"] is False
    assert (
        result["safety"]["public_website_design_runtime_optimisation_discovery_executes_compilation"] is False
    )
    assert (
        result["safety"]["public_website_design_runtime_optimisation_discovery_validates_measurement"]
        is False
    )
    assert result["safety"]["public_website_design_runtime_optimisation_encoding_or_css_execution"] is False
    assert (
        result["safety"]["public_website_design_runtime_optimisation_projection_is_acceptance_evidence"]
        is False
    )
    assert (
        result["safety"][
            "public_website_design_runtime_measurement_static_integrity_proves_producer_execution"
        ]
        is False
    )
    assert (
        result["safety"][
            "public_website_design_runtime_measurement_static_integrity_proves_full_decode_or_freshness"
        ]
        is False
    )
    assert (
        result["safety"]["public_website_design_runtime_measurement_static_integrity_production_authority"]
        is False
    )
    assert (
        result["safety"]["public_website_design_runtime_measurement_static_integrity_worker_access"] is False
    )
    assert (
        result["safety"][
            "public_website_design_runtime_measurement_static_integrity_imported_api_authoritative"
        ]
        is False
    )
    assert (
        result["safety"][
            "public_website_design_runtime_measurement_static_integrity_fresh_isolated_launcher_required"
        ]
        is True
    )
    logic_map = result["coding_logic_map"]
    assert logic_map["status"] == "who_what_where_when_how_ready"
    assert any(rule["id"] == "public_website.design_logic" for rule in logic_map["rules"])
    source_rationalisation_rule = next(
        rule for rule in logic_map["rules"] if rule["id"] == "public_website.source_rationalisation_logic"
    )
    assert source_rationalisation_rule["who"] == ["PublicWebsiteDesignQA"]
    assert any(
        "PublicWebsiteDesignWorker receives neither" in item for item in source_rationalisation_rule["how"]
    )
    runtime_optimisation_rule = next(
        rule
        for rule in logic_map["rules"]
        if rule["id"] == "public_website.runtime_optimisation_proposal_logic"
    )
    assert runtime_optimisation_rule["who"] == ["PublicWebsiteDesignQA"]
    assert any("never select a latest file" in item for item in runtime_optimisation_rule["how"])
    assert "PublicWebsiteDesignWorker receives no access" in runtime_optimisation_rule["safety_boundary"]
    static_integrity_rule = next(
        rule
        for rule in logic_map["rules"]
        if rule["id"] == "public_website.runtime_measurement_static_integrity_logic"
    )
    assert static_integrity_rule["who"] == ["PublicWebsiteDesignQA"]
    assert any("provenance-unverified" in item for item in static_integrity_rule["how"])
    assert any("python -I -S -B" in item for item in static_integrity_rule["how"])
    assert any("imported API call as authoritative" in item for item in static_integrity_rule["how"])
    assert "full media decode" in static_integrity_rule["safety_boundary"]
    assert "PublicWebsiteDesignWorker receives no access" in static_integrity_rule["safety_boundary"]
    assert {"who:", "what:", "where:", "when:", "how:"}.issubset(
        {item.split()[0] for item in logic_map["decision_loop"]}
    )
    assert "frontend/src/App.tsx" in logic_map["file_area_index"]
    assert (tmp_path / "frontend" / "public" / "aureon_coding_agent_skill_base.json").exists()
    assert (
        tmp_path / "frontend" / "src" / "components" / "generated" / "AureonCodingAgentSkillBaseConsole.tsx"
    ).exists()
    assert "AureonCodingAgentSkillBaseConsole" in app_text
    assert "Who What Where When How" in (
        tmp_path / "frontend" / "src" / "components" / "generated" / "AureonCodingAgentSkillBaseConsole.tsx"
    ).read_text(encoding="utf-8")
    assert "logicMap.status" in (
        tmp_path / "frontend" / "src" / "components" / "generated" / "AureonCodingAgentSkillBaseConsole.tsx"
    ).read_text(encoding="utf-8")


def test_goal_engine_routes_coder_skill_goal(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    engine = GoalExecutionEngine()
    plan = engine.submit_goal(
        "Aureon must teach its coder agents the coding skill base and learning workflow."
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == "coding_agent_skill_base"
    assert plan.steps[0].validation_result["valid"] is True
    evidence = json.loads(
        (tmp_path / "state" / "aureon_coding_agent_skill_base_last_run.json").read_text(encoding="utf-8")
    )
    assert evidence["write_info"]["writer"] == "bounded-local-writer"
    assert evidence["coding_logic_map"]["status"] == "who_what_where_when_how_ready"


def test_goal_engine_routes_coding_desktop_handoff_goal(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    engine = GoalExecutionEngine()
    plan = engine.submit_goal(
        "Aureon must connect the remote desktop run handoff to the coding organism "
        "so the user prompt becomes a finished product audit."
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == "coding_agent_skill_base"
    assert plan.steps[0].validation_result["valid"] is True


def test_goal_engine_routes_code_builder_terminal_goal(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    engine = GoalExecutionEngine()
    plan = engine.submit_goal(
        "Connect Aureon coding systems, inspect the repo, propose the smallest safe patch, "
        "and run focused tests so the code builder terminal works."
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == "coding_agent_skill_base"
    assert plan.steps[0].validation_result["valid"] is True


def test_goal_engine_routes_visual_asset_prompt_without_agentcore(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    engine = GoalExecutionEngine()
    plan = engine.submit_goal("drwaw me a image of a cat and open the file and show me it")

    assert plan.status == "completed"
    assert [step.intent for step in plan.steps] == ["visual_asset_request"]
    assert plan.steps[0].validation_result["valid"] is True
    payload = plan.steps[0].result["result"]
    assert payload["status"] == "visual_asset_ready"
    assert payload["public_url"].startswith("/aureon_visual_artifacts/")
    assert Path(payload["asset_path"]).exists()
    assert "cat" in payload["subject"]


def test_goal_engine_routes_video_artifact_prompt_without_agentcore(tmp_path: Path, monkeypatch) -> None:
    # mp4 rendering runs through OpenCV's VideoWriter; without cv2 the plan
    # honestly fails rather than fabricating a video file.
    import pytest
    pytest.importorskip("cv2")
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    engine = GoalExecutionEngine()
    plan = engine.submit_goal("make a 1 second video of a dog and show me the finished file")

    assert plan.status == "completed"
    assert [step.intent for step in plan.steps] == ["visual_asset_request"]
    assert plan.steps[0].validation_result["valid"] is True
    payload = plan.steps[0].result["result"]
    assert payload["status"] == "visual_asset_ready"
    assert payload["asset_kind"] == "mp4"
    assert payload["duration_seconds"] == 1
    assert payload["public_url"].endswith(".webm")
    assert payload["preview_url"].endswith("_preview.html")
    assert Path(payload["asset_path"]).exists()


def test_goal_engine_routes_operational_ui_before_generic_coding_scope(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    prompt = (
        "Aureon must build a read-only operational UI status card for the last public artifact URL, "
        "media kind, proof status, and snag count. Target the frontend generated operational console, "
        "preserve all safety gates, run tests or build proof, and hand over only when ready.\n\n"
        "Client-approved scope answers:\n"
        "- deliverables: Repo changes or reports, code proposal, focused tests, proof checklist, snagging result, and client handover.\n"
        "- target_system: Aureon repository, coding organism bridge, generated console evidence, and target files named by the prompt.\n"
        "- acceptance: Goal route is clean, focused tests pass or are explicitly skipped, HNC/Auris proof is recorded, and blocking snags are zero."
    )
    plan = GoalExecutionEngine()._decompose_goal(prompt)

    assert [step.intent for step in plan.steps] == ["self_author_operational_ui"]
