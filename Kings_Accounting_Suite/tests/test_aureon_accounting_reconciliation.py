from __future__ import annotations

import json
from pathlib import Path

import pytest

from Kings_Accounting_Suite.tools.aureon_accounting_reconciliation import (
    ReconciliationError,
    build_reconciliation_report,
    load_evidence_receipts,
    write_reconciliation_report,
)


def write_receipt(root: Path, name: str, source: str, kind: str, payload: dict[str, object]) -> None:
    (root / name).write_text(
        json.dumps(
            {
                "schema_version": "aureon-evidence-observation-v1",
                "source_system": source,
                "observation_type": kind,
                "external_reference": f"private-{name}",
                "observed_payload": payload,
            }
        ),
        encoding="utf-8",
    )


def test_reconciliation_report_defaults_closed_and_preserves_boundaries(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    write_receipt(
        evidence,
        "companies.json",
        "companies_house",
        "confirmation_statement_receipt",
        {"provider_state": "submission_received_acceptance_pending"},
    )
    write_receipt(
        evidence,
        "accountant.json",
        "gmail",
        "accountant_status_review",
        {
            "statutory_accounts": "appeared_up_to_date",
            "corporation_tax_returns": "outstanding_or_penalty_indications_require_resolution",
            "paye_reference": "not_observed",
            "cis_contractor_filing_obligation": "unresolved",
        },
    )
    write_receipt(
        evidence,
        "cis.json",
        "google_drive",
        "cis_deductions_suffered_statement",
        {"cis_deductions_suffered_evidenced": True},
    )
    write_receipt(
        evidence,
        "cis-refund.json",
        "hmrc",
        "cis_refund_claim_receipt",
        {
            "claim_submission_observed": True,
            "refund_paid_or_settled_observed": False,
        },
    )
    write_receipt(
        evidence,
        "bank.json",
        "bank_statement",
        "mixed_use_bank_evidence",
        {"mixed_use_review_required": True},
    )
    write_receipt(
        evidence,
        "xero.json",
        "xero",
        "access_recovery",
        {"login_notice_observed": True, "ledger_completeness_verified": False},
    )
    write_receipt(
        evidence,
        "intuit.json",
        "intuit_developer",
        "sandbox_creation_gate",
        {"sandbox_creation_result": "provider_error"},
    )
    write_receipt(
        evidence,
        "grants.json",
        "aureon_grant_ledger",
        "grant_accounting_boundary",
        {"award_confirmed_true_records": 0, "funding_received_true_records": 0},
    )
    write_receipt(
        evidence,
        "identity.json",
        "companies_house",
        "identity_verification_status",
        {"psc_due_date_passed": True, "identity_verification_completion_observed": False},
    )

    receipts = load_evidence_receipts(evidence)
    report = build_reconciliation_report(
        receipts,
        quickbooks_status={
            "status_sha256": "a" * 64,
            "connection_state": "development_app_ready_sandbox_creation_provider_error",
            "api": {"company_info_readback": "not_verified"},
        },
    )
    states = {item["id"]: item["state"] for item in report["workstreams"]}
    assert states["confirmation_statement"] == "submitted_received_acceptance_pending"
    assert states["corporation_tax"] == "urgent_outstanding_returns_and_penalties_resolution_required"
    assert states["grants"] == "no_award_or_funding_recognition_trigger_observed"
    assert states["banking"] == "mixed_use_owner_accountant_classification_required"
    assert states["quickbooks_api"] == "sandbox_creation_provider_blocked"
    assert states["companies_house_identity_verification"] == "psc_due_date_passed_completion_unverified"
    assert (
        states["cis_deductions_suffered"]
        == "deduction_and_refund_claim_evidence_present_outcome_reconciliation_required"
    )
    assert report["summary"]["posting_authorised_count"] == 0
    assert report["summary"]["quickbooks_projection_authorised_count"] == 0
    assert report["summary"]["external_compliance_action_authorised_count"] == 0
    assert len(report["report_sha256"]) == 64

    output = write_reconciliation_report(report, tmp_path / "status.json")
    raw = output.read_text(encoding="utf-8")
    assert "private-companies.json" not in raw


def test_reconciliation_loader_fails_closed_on_unknown_schema(tmp_path: Path) -> None:
    (tmp_path / "bad.json").write_text(json.dumps({"schema_version": "unknown"}), encoding="utf-8")
    with pytest.raises(ReconciliationError, match="Unsupported evidence receipt schema"):
        load_evidence_receipts(tmp_path)


def test_confirmation_acceptance_supersedes_received_pending_state(tmp_path: Path) -> None:
    write_receipt(
        tmp_path,
        "received.json",
        "companies_house",
        "confirmation_statement_receipt",
        {"provider_state": "submission_received_acceptance_pending"},
    )
    write_receipt(
        tmp_path,
        "accepted.json",
        "companies_house",
        "confirmation_statement_acceptance",
        {"provider_state": "accepted", "provider_acceptance_observed": True},
    )
    report = build_reconciliation_report(load_evidence_receipts(tmp_path))
    confirmation = next(item for item in report["workstreams"] if item["id"] == "confirmation_statement")
    assert confirmation["state"] == "accepted_provider_verified"
    assert confirmation["posting_authorised"] is False


def test_live_register_verifies_current_companies_house_workstreams(tmp_path: Path) -> None:
    write_receipt(
        tmp_path,
        "accepted.json",
        "companies_house",
        "confirmation_statement_acceptance",
        {"provider_state": "accepted", "provider_acceptance_observed": True},
    )
    write_receipt(
        tmp_path,
        "register.json",
        "companies_house",
        "company_register_status",
        {
            "legal_entity_match": True,
            "company_status": "active",
            "accounts_current_on_register": True,
            "confirmation_statement_current_on_register": True,
        },
    )
    report = build_reconciliation_report(load_evidence_receipts(tmp_path))
    states = {item["id"]: item["state"] for item in report["workstreams"]}
    assert states["legal_entity_cross_match"] == "companies_house_identity_verified_qbo_api_cross_match_pending"
    assert states["statutory_accounts"] == "current_provider_register_verified"
    assert states["confirmation_statement"] == "accepted_and_public_register_verified"


def test_live_qbo_company_evidence_routes_to_production_without_authorising_posting(
    tmp_path: Path,
) -> None:
    write_receipt(
        tmp_path,
        "subscription.json",
        "quickbooks_online",
        "subscription_payment_scheduled",
        {"live_company_observed": True, "legal_name_match_observed": True},
    )
    write_receipt(
        tmp_path,
        "bank-consent.json",
        "quickbooks_online",
        "bank_feed_consent_observed",
        {"transaction_import_readback_verified": False},
    )
    write_receipt(
        tmp_path,
        "mixed-bank.json",
        "bank_statement",
        "mixed_use_bank_evidence",
        {"mixed_use_review_required": True},
    )
    report = build_reconciliation_report(
        load_evidence_receipts(tmp_path),
        quickbooks_status={
            "api": {"company_info_readback": "not_verified"},
            "production_readiness": {"live_company_evidence": {"observed": True}},
        },
    )
    states = {item["id"]: item["state"] for item in report["workstreams"]}
    assert states["quickbooks_api"] == "live_company_observed_production_app_and_oauth_gated"
    assert (
        states["banking"]
        == "mixed_use_qbo_bank_consent_observed_import_and_classification_required"
    )
    assert report["summary"]["posting_authorised_count"] == 0
    assert report["summary"]["quickbooks_projection_authorised_count"] == 0
