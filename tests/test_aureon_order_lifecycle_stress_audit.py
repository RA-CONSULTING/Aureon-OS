from __future__ import annotations

import json

from aureon.autonomous.aureon_order_lifecycle_stress_audit import (
    SANDBOX_PAPER_REQUIREMENTS,
    VENUE_REQUIREMENTS,
    build_and_write_order_lifecycle_stress_audit,
    build_order_lifecycle_stress_audit,
    validate_sandbox_probe_config,
)


def test_order_lifecycle_stress_audit_certifies_required_scenarios(tmp_path):
    report = build_order_lifecycle_stress_audit(root=tmp_path)
    summary = report["summary"]
    requirement_ids = {row["id"] for row in VENUE_REQUIREMENTS}
    covered = {
        requirement
        for case in report["cases"]
        for requirement in case.get("covered_requirements", [])
    }

    assert report["status"] == "order_lifecycle_stress_certified"
    assert report["ok"] is True
    assert summary["passed_count"] == summary["case_count"]
    assert summary["covered_requirement_count"] == summary["requirement_count"]
    assert summary["capital_gold_path_certified"] is True
    assert summary["duplicate_route_blocked"] is True
    assert summary["restart_recovery_certified"] is True
    assert summary["recovered_exit_certified"] is True
    assert summary["recovered_exit_outcome_recorded"] is True
    assert summary["recovered_close_ack_waiting_absence_held"] is True
    assert summary["recovered_exit_stale_proof_blocked"] is True
    assert summary["multi_venue_recovery_certified"] is True
    assert summary["close_verification_enforced"] is True
    assert summary["partial_fill_certified"] is True
    assert summary["stale_broker_proof_blocked"] is True
    assert summary["failure_state_mapping_certified"] is True
    assert summary["broker_requirement_matrix_complete"] is True
    assert summary["no_live_mutation"] is True
    assert summary["no_ui_mutation_controls"] is True
    assert summary["mock_broker_certified"] is True
    assert summary["sandbox_paper_certified"] is True
    assert summary["sandbox_paper_passed_count"] == summary["sandbox_paper_case_count"]
    assert summary["sandbox_paper_covered_requirement_count"] == summary["sandbox_paper_requirement_count"]
    assert summary["sandbox_environment_guard_passed"] is True
    assert summary["sandbox_no_production_order_endpoints"] is True
    assert report["proof_tiers"]["mock_broker"]["status"] == "order_lifecycle_stress_certified"
    assert report["proof_tiers"]["sandbox_paper"]["status"] == "sandbox_paper_certified"
    assert requirement_ids <= covered
    assert {"capital", "alpaca", "binance", "kraken", "all"} <= set(summary["broker_requirement_matrix_by_venue"])

    case_ids = {case["id"] for case in report["cases"]}
    assert "multi_venue_open_order_recovery" in case_ids
    assert "stale_broker_proof_held" in case_ids
    assert "recovered_position_exit_to_outcome" in case_ids
    assert "recovered_close_ack_waiting_absence" in case_ids
    assert "recovered_stale_close_proof_held" in case_ids

    sandbox_case_ids = {case["id"] for case in report["sandbox_paper_cases"]}
    assert "sandbox_capital_demo_gold_start_to_close" in sandbox_case_ids
    assert "sandbox_alpaca_paper_status_and_duplicate_route" in sandbox_case_ids
    assert "sandbox_binance_test_order_timeout_unknown" in sandbox_case_ids
    assert "sandbox_kraken_validate_openorders_recovery" in sandbox_case_ids


def test_order_lifecycle_stress_audit_writes_public_artifacts(tmp_path):
    report = build_and_write_order_lifecycle_stress_audit(root=tmp_path)
    public_path = tmp_path / "frontend/public/aureon_order_lifecycle_stress_audit.json"
    state_path = tmp_path / "state/aureon_order_lifecycle_stress_audit_last_run.json"
    audit_path = tmp_path / "docs/audits/aureon_order_lifecycle_stress_audit.json"
    md_path = tmp_path / "docs/audits/aureon_order_lifecycle_stress_audit.md"

    assert report["write_info"]["evidence_writes"]
    assert public_path.exists()
    assert state_path.exists()
    assert audit_path.exists()
    assert md_path.exists()

    public = json.loads(public_path.read_text(encoding="utf-8"))
    assert public["schema_version"] == "aureon-order-lifecycle-stress-audit-v1"
    assert public["summary"]["case_count"] >= 7
    assert public["summary"]["sandbox_paper_certified"] is True
    assert public["sandbox_paper_cases"]
    assert public["manual_boundaries"]


def test_order_lifecycle_stress_audit_flags_missing_requirements(tmp_path):
    report = build_order_lifecycle_stress_audit(
        root=tmp_path,
        cases=[
            {
                "id": "partial",
                "label": "Partial",
                "venue": "capital",
                "passed": True,
                "covered_requirements": ["capital_deal_reference_confirmed"],
            }
        ],
    )

    assert report["status"] == "order_lifecycle_stress_attention"
    assert report["ok"] is False
    assert "order_lifecycle_stress_requirements_missing" in report["blockers"]
    assert "capital_deal_id_attached" in report["missing_requirements"]
    assert report["summary"]["sandbox_paper_certified"] is True


def test_order_lifecycle_stress_requirement_matrix_is_decision_complete(tmp_path):
    required_keys = {
        "id",
        "venue",
        "required_identifiers",
        "status_sources",
        "close_fill_proof",
        "timeout_behavior",
        "recovery_expectation",
    }

    for row in VENUE_REQUIREMENTS:
        assert required_keys <= set(row)
        assert row["required_identifiers"]
        assert row["status_sources"]
        assert row["timeout_behavior"]
        assert row["recovery_expectation"]

    for row in SANDBOX_PAPER_REQUIREMENTS:
        assert {"id", "venue", "requirement", "allowed_environment"} <= set(row)
        assert row["allowed_environment"]


def test_sandbox_probe_config_rejects_production_order_endpoints():
    assert validate_sandbox_probe_config(
        venue="capital",
        endpoint_url="https://api-capital.backend-capital.com/",
        operation="order_submit",
        account_mode="live",
        broker_environment="capital_live",
    )["allowed"] is False
    assert validate_sandbox_probe_config(
        venue="alpaca",
        endpoint_url="https://api.alpaca.markets",
        operation="order_submit",
        account_mode="live",
        broker_environment="alpaca_live",
    )["allowed"] is False
    assert validate_sandbox_probe_config(
        venue="binance",
        endpoint_url="https://api.binance.com/api/v3/order",
        operation="order_submit",
        account_mode="live",
        broker_environment="binance_live",
    )["allowed"] is False
    assert validate_sandbox_probe_config(
        venue="kraken",
        endpoint_url="https://api.kraken.com",
        operation="order_submit",
        account_mode="live",
        broker_environment="kraken_live",
    )["allowed"] is False


def test_sandbox_probe_config_allows_only_safe_sandbox_routes():
    assert validate_sandbox_probe_config(
        venue="capital",
        endpoint_url="https://demo-api-capital.backend-capital.com/",
        operation="order_submit",
        account_mode="demo",
        broker_environment="capital_demo",
    )["allowed"] is True
    assert validate_sandbox_probe_config(
        venue="alpaca",
        endpoint_url="https://paper-api.alpaca.markets",
        operation="order_submit",
        account_mode="paper",
        broker_environment="alpaca_paper",
    )["allowed"] is True
    assert validate_sandbox_probe_config(
        venue="binance",
        endpoint_url="https://api.binance.com/api/v3/order/test",
        operation="order_submit",
        account_mode="test_order",
        broker_environment="binance_order_test",
    )["allowed"] is True
    assert validate_sandbox_probe_config(
        venue="kraken",
        endpoint_url="https://api.kraken.com",
        operation="validate_order",
        account_mode="validate_only",
        broker_environment="kraken_validate_openOrders",
    )["allowed"] is True
