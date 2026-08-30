import json
import os
import subprocess
import sys
from pathlib import Path

from aureon.autonomous import aureon_capability_growth_loop as growth_loop
from aureon.autonomous.aureon_capability_growth_loop import (
    BenchmarkCheck,
    author_improvement_skills,
    build_capability_growth_loop,
    collect_domain_capabilities,
    default_benchmark_commands,
    detect_capability_gaps,
    render_markdown,
    run_benchmark_checks,
    write_report,
)


def _seed_audits(root: Path) -> None:
    audits = root / "docs" / "audits"
    audits.mkdir(parents=True)
    (root / "aureon").mkdir(exist_ok=True)
    (root / "scripts").mkdir(exist_ok=True)
    (audits / "aureon_repo_self_catalog.json").write_text(
        json.dumps(
            {
                "status": "catalog_complete_with_attention_items",
                "summary": {
                    "cataloged_file_count": 42,
                    "subsystem_count": 8,
                    "secret_metadata_only_count": 2,
                    "coverage_policy": "all project files labelled",
                    "truncated": False,
                },
            }
        ),
        encoding="utf-8",
    )
    (audits / "mind_wiring_audit.json").write_text(
        json.dumps({"counts": {"wired": 10, "partial": 0, "broken": 0, "unknown": 0}}),
        encoding="utf-8",
    )
    proofs = [
        {
            "id": "repo_organization",
            "status": "working",
            "summary": "ok",
            "systems": ["RepoWideOrganizationAudit"],
        },
        {"id": "goal_routing", "status": "working", "summary": "ok", "systems": ["GoalCapabilityMap"]},
        {
            "id": "trading_brain",
            "status": "working_safe_simulation",
            "summary": "safe sim",
            "systems": ["UnifiedMarginBrain"],
        },
        {
            "id": "accounting_brain",
            "status": "working_with_attention",
            "summary": "manual filing",
            "systems": ["AccountingContextBridge"],
        },
        {"id": "research_vault", "status": "working", "summary": "ok", "systems": ["ResearchCorpusIndex"]},
        {
            "id": "llm_capability",
            "status": "working_with_attention",
            "summary": "fallback",
            "systems": ["AureonHybridAdapter"],
        },
        {"id": "operator_surfaces", "status": "working", "summary": "ok", "systems": ["dashboard"]},
        {"id": "ignition", "status": "working", "summary": "ok", "systems": ["scripts/aureon_ignition.py"]},
    ]
    (audits / "aureon_system_readiness_audit.json").write_text(
        json.dumps(
            {
                "status": "working_with_attention_items",
                "summary": {"real_orders_allowed": False},
                "proofs": proofs,
            }
        ),
        encoding="utf-8",
    )


def test_collect_domains_and_detect_gaps(tmp_path):
    _seed_audits(tmp_path)

    domains = collect_domain_capabilities(tmp_path)
    gaps = detect_capability_gaps(domains)

    ids = {domain.id for domain in domains}
    assert "repo_self_catalog" in ids
    assert "code_architect_skill_authoring" in ids
    assert "public_website_design" in ids
    assert "accounting_compliance" in ids
    assert any(gap.domain == "accounting_compliance" for gap in gaps)
    assert any(gap.route == "capability_growth_loop" for gap in gaps)


def test_collect_domains_activates_the_audit_boundary_before_goal_map_import(tmp_path, monkeypatch):
    _seed_audits(tmp_path)
    monkeypatch.delenv("AUREON_AUDIT_MODE", raising=False)
    monkeypatch.delenv("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", raising=False)

    collect_domain_capabilities(tmp_path)

    assert os.environ["AUREON_AUDIT_MODE"] == "1"
    assert os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] == "1"


def test_growth_loop_module_import_is_passive_without_audit_environment():
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.pop("AUREON_AUDIT_MODE", None)
    env.pop("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", None)
    env["AUREON_ACTIVATE_ON_IMPORT"] = "0"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import aureon.autonomous.aureon_capability_growth_loop; print('growth-loop-imported')",
        ],
        cwd=repo_root,
        env=env,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "growth-loop-imported"
    runtime_signatures = ("WhaleSonar", "Timeline Oracle", "Mycelium", "exchange")
    assert not any(signature in result.stderr for signature in runtime_signatures)


def test_author_improvement_skills_writes_validated_skill_library(tmp_path):
    _seed_audits(tmp_path)
    gaps = detect_capability_gaps(collect_domain_capabilities(tmp_path))[:2]

    authored = author_improvement_skills(tmp_path, gaps, limit=2)

    assert authored
    assert all(item.validation_ok for item in authored)
    assert all(item.registered for item in authored)
    library_path = tmp_path / "state" / "capability_growth_skills" / "skill_library.json"
    assert library_path.exists()
    data = json.loads(library_path.read_text(encoding="utf-8"))
    assert data["count"] >= 1


def test_run_benchmark_checks_records_pass_and_failure(tmp_path):
    def fake_runner(command, cwd, env, text, capture_output, timeout):
        return subprocess.CompletedProcess(
            args=command,
            returncode=0 if command[-1] == "pass" else 1,
            stdout="ok",
            stderr="bad" if command[-1] != "pass" else "",
        )

    checks = run_benchmark_checks(
        tmp_path,
        [
            ("passing", ["python", "pass"]),
            ("failing", ["python", "fail"]),
        ],
        runner=fake_runner,
    )

    assert checks[0].status == "passed"
    assert checks[1].status == "failed"


def test_default_benchmarks_bind_frozen_design_qa_capabilities() -> None:
    commands = dict(default_benchmark_commands(Path.cwd(), sys.executable))
    focused = commands["focused_public_website_design_tests"]
    compile_command = commands["compile_public_website_design_qa_capabilities"]

    assert "tests/test_design_motion_performance_budget.py" in focused
    assert "tests/test_design_candidate_test_evidence.py" in focused
    assert "tests/test_secure_immutable_artifact.py" in focused
    assert "tests/test_design_candidate_static_qa.py" in focused
    assert "tests/test_design_candidate_motion_policy_compiler.py" in focused
    assert "tests/test_design_candidate_test_policy_compiler.py" in focused
    assert "tests/test_design_candidate_source_closure.py" in focused
    assert "tests/test_public_website_design_runner.py" in focused
    assert "tests/test_website_source_rationalisation.py" in focused
    assert "tests/test_website_runtime_optimisation.py" in focused
    assert "tests/test_website_runtime_measurement_provenance.py" in focused
    assert "aureon/operator/design_motion_performance_budget.py" in compile_command
    assert "aureon/operator/design_candidate_test_evidence.py" in compile_command
    assert "aureon/operator/secure_immutable_artifact.py" in compile_command
    assert "aureon/operator/design_candidate_static_qa.py" in compile_command
    assert "aureon/operator/design_candidate_motion_policy_compiler.py" in compile_command
    assert "aureon/operator/design_candidate_test_policy_compiler.py" in compile_command
    assert "aureon/operator/design_candidate_source_closure.py" in compile_command
    assert "aureon/operator/website_source_rationalisation.py" in compile_command
    assert "tools/run-website-source-rationalisation.py" in compile_command
    assert "aureon/operator/website_runtime_optimisation.py" in compile_command
    assert "tools/run-website-runtime-optimisation.py" in compile_command
    assert "aureon/operator/website_runtime_measurement_provenance.py" in compile_command
    assert "tools/run-website-runtime-measurement-provenance.py" in compile_command
    assert "aureon/autonomous/aureon_public_website_design_runner.py" in compile_command
    assert "aureon/operator/design_capability_registry.py" in compile_command
    assert "tests/test_website_source_rationalisation.py" in compile_command
    assert "tests/test_website_runtime_optimisation.py" in compile_command
    assert "tests/test_website_runtime_measurement_provenance.py" in compile_command


def test_public_website_design_discovery_separates_compiler_ingress_without_subprocess(
    monkeypatch,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]

    def prohibited_subprocess(*_args, **_kwargs):
        raise AssertionError("website-design capability discovery must not launch a subprocess")

    monkeypatch.setattr(growth_loop.subprocess, "run", prohibited_subprocess)
    monkeypatch.setattr(growth_loop.subprocess, "Popen", prohibited_subprocess)

    capability = growth_loop.public_website_design_capability(repo_root)
    evidence = capability.evidence

    assert evidence["candidate_qa_control_plane_available"] is True
    assert evidence["imported_compiler_drift_check_apis_available"] is True
    assert evidence["sealed_compiler_read_only_protocol_available"] is True
    assert evidence["sealed_compiler_runner_delegation_available"] is True
    assert evidence["candidate_test_reviewed_node_toolchain_available"] is True
    assert evidence["candidate_test_bounded_popen_available"] is True
    assert evidence["candidate_qa_discovery_subprocess_launched"] is False
    assert evidence["sealed_compiler_read_only_verification_executed"] is False
    assert evidence["sealed_compiler_runner_delegation_invoked"] is False
    assert evidence["source_rationalisation_planning_protocol_available"] is True
    assert evidence["source_rationalisation_owner_decision_validation_protocol_available"] is True
    assert evidence["source_rationalisation_planning_executed_during_discovery"] is False
    assert evidence["source_rationalisation_validation_executed_during_discovery"] is False
    assert evidence["source_rationalisation_autonomous_owner_decision"] is False
    assert evidence["source_rationalisation_text_worker_authority"] == "none"
    assert evidence["source_rationalisation_staging_authority"] == "none"
    assert evidence["source_rationalisation_physical_deletion_authority"] == "none"
    assert evidence["source_rationalisation_candidate_authority"] == "none"
    assert evidence["source_rationalisation_canonical_authority"] == "none"
    assert evidence["source_rationalisation_package_authority"] == "none"
    assert evidence["source_rationalisation_release_eligible"] is False
    assert evidence["source_rationalisation_deployment_authority"] == "none"
    assert evidence["source_rationalisation_credential_access"] == "none"
    assert evidence["source_rationalisation_network_access"] == "none"
    assert evidence["source_rationalisation_omission_proves_readiness"] is False
    assert evidence["runtime_optimisation_protocol_available"] is False
    assert evidence["runtime_optimisation_measurement_schema_available"] is True
    assert evidence["runtime_optimisation_proposal_schema_available"] is True
    assert evidence["runtime_optimisation_measurement_provenance_verified"] is False
    assert evidence["runtime_optimisation_production_compilation_blocked"] is True
    assert evidence["runtime_optimisation_discovery_execution"] is False
    assert evidence["runtime_optimisation_autonomous_source_selection"] is False
    assert evidence["runtime_optimisation_autonomous_measurement_evidence"] is False
    assert evidence["runtime_optimisation_transformations_executed"] is False
    assert evidence["runtime_optimisation_candidate_authority"] == "none"
    assert evidence["runtime_optimisation_package_authority"] == "none"
    assert evidence["runtime_optimisation_release_eligible"] is False
    assert evidence["runtime_optimisation_deployment_authority"] == "none"
    assert evidence["runtime_measurement_static_integrity_available"] is True
    assert evidence["runtime_measurement_static_integrity_executed"] is False
    assert evidence["runtime_measurement_static_integrity_provenance_verified"] is False
    assert evidence["runtime_measurement_static_integrity_production_eligible"] is False
    assert evidence["runtime_measurement_static_integrity_worker_available"] is False
    assert evidence["runtime_measurement_static_integrity_artifact_emission_available"] is False
    assert evidence["runtime_measurement_static_integrity_execution_path"] == "fresh-isolated-launcher-only"
    assert evidence["runtime_measurement_static_integrity_imported_api_authoritative"] is False
    assert evidence["runtime_measurement_static_integrity_proves_producer_execution"] is False
    assert evidence["runtime_measurement_static_integrity_proves_full_decode_or_freshness"] is False
    assert evidence["runtime_measurement_static_integrity_deployment_authority"] == "none"
    assert "aureon/operator/website_source_rationalisation.py" in evidence["present_surfaces"]
    assert "tools/run-website-source-rationalisation.py" in evidence["present_surfaces"]
    assert "docs/runbooks/WEBSITE_SOURCE_RATIONALISATION.md" in evidence["present_surfaces"]
    assert "tests/test_website_source_rationalisation.py" in evidence["present_surfaces"]
    assert "aureon/operator/website_runtime_optimisation.py" in evidence["present_surfaces"]
    assert "tools/run-website-runtime-optimisation.py" in evidence["present_surfaces"]
    assert "aureon/operator/website_runtime_measurement_provenance.py" in evidence["present_surfaces"]
    assert "tools/run-website-runtime-measurement-provenance.py" in evidence["present_surfaces"]
    assert "data/website_operator/browser_acceptance_contract.v1.json" in evidence["present_surfaces"]
    assert "docs/runbooks/WEBSITE_RUNTIME_OPTIMISATION.md" in evidence["present_surfaces"]
    assert "tests/test_website_runtime_optimisation.py" in evidence["present_surfaces"]
    assert (
        "docs/research/schemas/AUREON_WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_V1.schema.json"
        in evidence["present_surfaces"]
    )
    assert "tests/test_website_runtime_measurement_provenance.py" in evidence["present_surfaces"]


def test_build_growth_loop_writes_report_vault_and_contracts(tmp_path):
    _seed_audits(tmp_path)
    report = build_capability_growth_loop(
        tmp_path,
        iterations=1,
        run_checks=False,
        author_skills=True,
        queue_contracts=True,
        max_gaps=3,
    )

    assert report.schema_version == "aureon-capability-growth-loop-v1"
    assert report.summary["iteration_count"] == 1
    assert report.summary["latest_gap_count"] >= 1
    assert report.summary["latest_registered_improvement_count"] >= 1
    assert report.iterations[0].contract_plan["queued_persistently"] is True

    markdown = render_markdown(report)
    assert "Aureon Capability Growth Loop" in markdown
    assert "audit -> benchmark" in markdown

    md_path, json_path, state_path, vault_path = write_report(
        report,
        tmp_path / "growth.md",
        tmp_path / "growth.json",
        tmp_path / "growth_state.json",
    )

    assert md_path.exists()
    assert json_path.exists()
    assert state_path.exists()
    assert vault_path and vault_path.exists()
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["vault_memory"]["status"] == "written"


def test_validation_domain_uses_benchmark_results(tmp_path):
    _seed_audits(tmp_path)
    failed = BenchmarkCheck(
        id="demo_fail",
        command=["python", "-c", "exit(1)"],
        status="failed",
        returncode=1,
        duration_s=0.1,
    )

    report = build_capability_growth_loop(tmp_path, iterations=1, run_checks=False)
    # Build an iteration path directly with the failed check via domain collection.
    domains = collect_domain_capabilities(tmp_path, benchmark_checks=[failed])
    validation = [domain for domain in domains if domain.id == "validation_benchmarking"][0]

    assert report.summary["iteration_count"] == 1
    assert validation.status == "blocked_or_missing"
    assert validation.score == 0.20
