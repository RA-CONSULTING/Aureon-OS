"""Static safety and coverage contract for the isolated acceptance workflow."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "acceptance-ci.yml"


def test_acceptance_ci_workflow_is_offline_fail_closed_and_complete() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    workflow = yaml.load(source, Loader=yaml.BaseLoader)

    assert isinstance(workflow, dict)
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["concurrency"]["cancel-in-progress"] == "true"
    assert "pull_request_target" not in workflow["on"]

    expected_env = {
        "AUREON_AUDIT_MODE": "1",
        "LIVE": "0",
        "DRY_RUN": "1",
        "AUREON_LIVE_TRADING": "0",
        "AUREON_LLM_OFFLINE": "1",
        "AUREON_DISABLE_LLM_HTTP": "1",
        "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS": "1",
        "BINANCE_DRY_RUN": "true",
        "KRAKEN_DRY_RUN": "true",
        "ALPACA_DRY_RUN": "true",
        "CAPITAL_DEMO": "true",
    }
    assert expected_env.items() <= workflow["env"].items()

    expected_jobs = {
        "workflow-contract",
        "python-critical",
        "hosting-manifests",
        "economic-mutation-boundary",
        "cloudflare-static",
        "supabase-static",
        "frontend",
    }
    assert expected_jobs == set(workflow["jobs"])

    forbidden = (
        "continue-on-error",
        "|| true",
        "--report-only",
        "${{ secrets.",
        "--execute",
        "trade:real",
        "curl ",
        "wget ",
        "docker push",
        "wrangler deploy",
        "supabase functions deploy",
        "doctl ",
        "gh ",
    )
    lowered = source.lower()
    assert all(token not in lowered for token in forbidden)

    allowed_actions = {
        "actions/checkout@v6",
        "actions/setup-python@v6",
        "actions/setup-node@v6",
        "actions/upload-artifact@v7",
    }
    used_actions: set[str] = set()
    artifact_steps: list[dict[str, object]] = []
    for job in workflow["jobs"].values():
        assert int(job["timeout-minutes"]) <= 30
        for step in job["steps"]:
            action = step.get("uses")
            if action:
                used_actions.add(action)
                assert re.fullmatch(r"actions/[a-z-]+@v\d+", action)
                if action == "actions/checkout@v6":
                    assert step["with"]["persist-credentials"] == "false"
                if action == "actions/upload-artifact@v7":
                    artifact_steps.append(step)
    assert used_actions == allowed_actions
    assert artifact_steps
    for step in artifact_steps:
        assert step["if"] == "always()"
        settings = step["with"]
        assert str(settings["path"]).startswith("artifacts/")
        assert str(settings["path"]).endswith(".xml")
        assert settings["include-hidden-files"] == "false"
        assert settings["if-no-files-found"] == "error"
        assert 1 <= int(settings["retention-days"]) <= 7

    required_python_tests = (
        "test_bounded_binance_roundtrip.py",
        "test_binance_client_real_data.py",
        "test_s5_kraken_spot_readiness.py",
        "test_s5_live_execution_receipts.py",
        "test_s5_economic_governance_boundary.py",
        "test_hnc_lambda_history_provenance.py",
        "test_hnc_daemon_sentinel_source.py",
        "test_auris_throne_provenance.py",
        "test_auris_node_receipts.py",
        "test_druidic_council.py",
        "test_celtic_voice_bank.py",
        "test_trusted_druid_voice.py",
        "test_crown_voice.py",
        "test_dual_key_governance.py",
        "test_cognition_governance_gate.py",
        "test_economic_governance_boundary.py",
        "test_legacy_economic_unity.py",
        "test_legacy_unity_composition.py",
        "test_legacy_economic_unity_plan.py",
        "test_unified_exchange_legacy_unity.py",
        "test_unified_exchange_unity_composition.py",
        "test_queen_process_roof.py",
        "test_queen_mind.py",
        "test_canonical_organism_composition.py",
        "test_unified_organism_builder.py",
        "test_queen_layer_canonical_roof.py",
        "test_queen_profit_dashboard_economic_unity.py",
        "test_runtime_governance_voice_suppliers.py",
        "test_workforce_druid_resolver.py",
        "test_durable_contingency_recovery.py",
        "test_kraken_economic_transport_guard.py",
        "test_tool_dispatch_governance.py",
        "test_operator_cognition.py",
        "test_operator_join_organism_lazy_queen.py",
        "test_observability_outbox_contract.py",
        "test_observability_runtime_contract.py",
        "test_operator_observability_contract.py",
        "test_operator_security_fail_closed.py",
        "test_operator_tenant_security.py",
        "test_container_hosting_packaging_contract.py",
        "test_primary_launcher_paths.py",
        "test_voice_runner_paths.py",
        "test_launcher_navigation_source_truth.py",
        "test_frontend_package_scripts.py",
        "test_public_manifest_contract.py",
        "test_pytest_no_skip_shards.py",
        "test_digitalocean_app_spec_fail_closed.py",
        "test_ignition_live_profile.py",
        "test_import_snapshot_quarantine.py",
        "test_legacy_deployment_surfaces_hold.py",
        "test_single_writer_scaling_contract.py",
        "test_economic_mutation_boundary_census.py",
    )
    assert all(name in source for name in required_python_tests)
    assert "--disable-socket" in source

    for command in ("npm run typecheck", "npm run lint", "npm run build"):
        assert command in source
    for spec in (
        "tests/shell-smoke.spec.ts",
        "tests/live-data.spec.ts",
        "tests/capability-forge.spec.ts",
    ):
        assert spec in source

    for manifest in (
        ".do/app.yaml",
        "app.yaml",
        "docker-compose.yml",
        "deploy/supervisord.conf",
        "deploy/cloudflare/aureon_murge_worker/wrangler.jsonc",
        "flameborn/wrangler.jsonc",
        "supabase/config.toml",
        "supabase/functions",
        "supabase/migrations",
    ):
        assert manifest in source
    for cloudflare_contract in (
        "node --check flameborn/workers/index.mjs",
        "node --check deploy/cloudflare/aureon_murge_worker/index.mjs",
        "node --check flameborn/cloudflare-ui/app.js",
        "node --check flameborn/script.js",
        "node --test tests/cloudflare_worker_security_contract.test.mjs",
        "node --test tests/cloudflare_workers_deploy_preflight_contract.test.mjs",
        "npm --prefix flameborn run cf:preflight",
        "AUREON_WORKER_ACCESS_SECRET: ci-only-not-a-secret-0123456789abcdef",
        "AUREON_ALLOWED_ORIGINS: https://acceptance.invalid",
        "bash flameborn/scripts/build_workers_assets.sh",
        "API_PREAUTH_RATE_LIMITER",
        "API_RATE_LIMITER",
        'JSON.stringify(["/api", "/api/*"])',
    ):
        assert cloudflare_contract in source
    assert "scripts/validation/audit_supabase_edge_auth.py" in source
    for contract in (
        "tests/test_supabase_edge_auth_contract.py",
        "tests/test_supabase_live_only_edge_functions.py",
        "tests/test_supabase_legacy_public_rls_migration.py",
        "tests/test_supabase_privileged_function_hardening.py",
    ):
        assert contract in source

    for critical_surface in (
        "aureon/autonomous/aureon_autonomous_self_run_loop.py",
        "aureon/autonomous/aureon_full_stack_release_gate.py",
        "aureon/autonomous/aureon_ten_nine_one_thought_path.py",
        "aureon/autonomous/aureon_truth_gated_ten_nine_one.py",
        "aureon/autonomous/aureon_cloud_brain_composition.py",
        "aureon/autonomous/aureon_agent_company_brain_fabric.py",
        "aureon/autonomous/aureon_internal_coding_workforce.py",
        "aureon/autonomous/aureon_internal_work_ledger.py",
        "aureon/autonomous/aureon_internal_patch_loop.py",
        "aureon/autonomous/aureon_internal_self_coder.py",
        "aureon/autonomous/aureon_self_run_coding_task.py",
        "aureon/governance/celtic_voice_bank.py",
        "aureon/governance/durable_contingency.py",
        "aureon/governance/legacy_economic_unity.py",
        "aureon/governance/legacy_unity_composition.py",
        "aureon/governance/runtime_voice_suppliers.py",
        "aureon/governance/workforce_druid_resolver.py",
        "aureon/governance/qgita_kundalini_truth_gate.py",
        "aureon/governance/trusted_truth_evidence.py",
        "aureon/observability/__init__.py",
        "aureon/observability/outbox.py",
        "aureon/observability/runtime.py",
        "aureon/operator/aureon_operator.py",
        "aureon/operator/metrics.py",
        "aureon/operator/operator_server.py",
        "aureon/trading/unified_exchange_composition.py",
        "aureon/utils/aureon_queen_hive_mind.py",
        "scripts/validation/pytest_no_skip_shards.py",
        "scripts/validation/plan_legacy_economic_unity.py",
        "scripts/validation/audit_external_llm_fallback.py",
        "scripts/validation/audit_aureon_hnc_ollama_coreviewer.py",
    ):
        assert critical_surface in source

    for self_coding_contract in (
        "tests/test_aureon_full_stack_release_gate.py",
        "tests/test_aureon_ten_nine_one_thought_path.py",
        "tests/test_qgita_kundalini_truth_gate.py",
        "tests/test_trusted_truth_evidence.py",
        "tests/test_truth_gated_ten_nine_one.py",
        "tests/test_aureon_cloud_brain_composition.py",
        "tests/test_aureon_agent_company_brain_fabric.py",
        "tests/test_aureon_internal_coding_workforce.py",
        "tests/test_aureon_internal_work_ledger.py",
        "tests/test_aureon_internal_patch_loop.py",
        "tests/test_aureon_internal_self_coder.py",
        "tests/test_aureon_autonomous_self_run_loop.py",
        "tests/test_aureon_self_run_internal_coder_wiring.py",
        "tests/test_external_llm_fallback.py",
        "tests/test_aureon_hnc_ollama_coreviewer.py",
    ):
        assert self_coding_contract in source

    economic_steps = workflow["jobs"]["economic-mutation-boundary"]["steps"]
    census_test_index = next(
        index
        for index, step in enumerate(economic_steps)
        if "test_economic_mutation_boundary_census.py" in step.get("run", "")
    )
    audit_index = next(
        index
        for index, step in enumerate(economic_steps)
        if "audit_economic_mutation_boundaries.py" in step.get("run", "")
    )
    assert census_test_index < audit_index
    assert any(
        "plan_legacy_economic_unity.py --summary-only" in step.get("run", "")
        for step in economic_steps
    )
    assert audit_index == len(economic_steps) - 1
    assert economic_steps[audit_index]["run"] == (
        "python -B scripts/validation/audit_economic_mutation_boundaries.py --compact"
    )
