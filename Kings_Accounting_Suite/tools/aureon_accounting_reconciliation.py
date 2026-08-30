"""Build Aureon's privacy-minimised accounting and compliance work queue.

The report is derived from private evidence receipts and secret-free control
statuses. It is not a journal, filing instruction, tax conclusion, or approval.
Every workstream defaults closed: no posting or external compliance action is
authorised by this module.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from Kings_Accounting_Suite.tools.quickbooks_accounting_integration import payload_sha256

EVIDENCE_SCHEMA = "aureon-evidence-observation-v1"
REPORT_SCHEMA = "aureon-accounting-reconciliation-v1"


class ReconciliationError(RuntimeError):
    """The source evidence cannot produce a trustworthy work queue."""


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconciliationError(f"Unreadable reconciliation source: {path}") from exc
    if not isinstance(value, dict):
        raise ReconciliationError(f"Reconciliation source must be an object: {path}")
    return value


def load_evidence_receipts(root: str | Path) -> list[dict[str, Any]]:
    directory = Path(root)
    receipts: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("*.json")):
        receipt = _read_json_object(path)
        if receipt.get("schema_version") != EVIDENCE_SCHEMA:
            raise ReconciliationError(f"Unsupported evidence receipt schema: {path}")
        observed_payload = receipt.get("observed_payload")
        if not isinstance(observed_payload, dict):
            raise ReconciliationError(f"Evidence observation payload must be an object: {path}")
        source_system = str(receipt.get("source_system", "")).strip()
        observation_type = str(receipt.get("observation_type", "")).strip()
        if not source_system or not observation_type:
            raise ReconciliationError(f"Evidence source and observation type are required: {path}")
        receipts.append(
            {
                "source_system": source_system,
                "observation_type": observation_type,
                "observed_payload": observed_payload,
                "receipt_sha256": payload_sha256(receipt),
                "observed_payload_sha256": payload_sha256(observed_payload),
            }
        )
    return receipts


def _latest_payload(receipts: Sequence[Mapping[str, Any]], observation_type: str) -> dict[str, Any]:
    matches = [
        item.get("observed_payload")
        for item in receipts
        if item.get("observation_type") == observation_type
        and isinstance(item.get("observed_payload"), Mapping)
    ]
    return dict(matches[-1]) if matches else {}


def _workstream(
    workstream_id: str,
    *,
    state: str,
    priority: str,
    evidence_types: Sequence[str],
    next_action: str,
) -> dict[str, Any]:
    return {
        "id": workstream_id,
        "state": state,
        "priority": priority,
        "evidence_types": list(evidence_types),
        "next_action": next_action,
        "posting_authorised": False,
        "quickbooks_projection_authorised": False,
        "external_compliance_action_authorised": False,
    }


def build_reconciliation_report(
    receipts: Sequence[Mapping[str, Any]],
    *,
    quickbooks_status: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    receipt_types = {str(item.get("observation_type", "")) for item in receipts}
    accountant = _latest_payload(receipts, "accountant_status_review")
    confirmation = _latest_payload(receipts, "confirmation_statement_receipt")
    confirmation_acceptance = _latest_payload(receipts, "confirmation_statement_acceptance")
    company_register = _latest_payload(receipts, "company_register_status")
    identity_verification = _latest_payload(receipts, "identity_verification_status")
    cis = _latest_payload(receipts, "cis_deductions_suffered_statement")
    cis_refund_claim = _latest_payload(receipts, "cis_refund_claim_receipt")
    qbo_subscription = _latest_payload(receipts, "subscription_payment_scheduled")
    qbo_bank_consent = _latest_payload(receipts, "bank_feed_consent_observed")
    bank = _latest_payload(receipts, "mixed_use_bank_evidence")
    xero = _latest_payload(receipts, "access_recovery")
    intuit = _latest_payload(receipts, "sandbox_creation_gate")
    grants = _latest_payload(receipts, "grant_accounting_boundary")
    qbo_api = dict((quickbooks_status or {}).get("api") or {})
    qbo_production = dict((quickbooks_status or {}).get("production_readiness") or {})
    qbo_live_company = dict(qbo_production.get("live_company_evidence") or {})
    company_info_verified = qbo_api.get("company_info_readback") == "verified"

    workstreams = [
        _workstream(
            "legal_entity_cross_match",
            state=(
                "companies_house_and_qbo_companyinfo_verified"
                if company_register.get("legal_entity_match") is True
                and company_register.get("company_status") == "active"
                and company_info_verified
                else "companies_house_and_qbo_billing_identity_observed_companyinfo_pending"
                if company_register.get("legal_entity_match") is True
                and company_register.get("company_status") == "active"
                and qbo_subscription.get("legal_name_match_observed") is True
                else
                "companies_house_identity_verified_qbo_api_cross_match_pending"
                if company_register.get("legal_entity_match") is True
                and company_register.get("company_status") == "active"
                else "legal_identity_known_qbo_api_cross_match_pending"
            ),
            priority="high",
            evidence_types=(
                (["company_register_status"] if company_register else [])
                + (["subscription_payment_scheduled"] if qbo_subscription else [])
                + (["sandbox_creation_gate"] if intuit else [])
            ),
            next_action="Read QBO CompanyInfo and match the Aureon legal entity before any projection.",
        ),
        _workstream(
            "quickbooks_api",
            state=(
                "live_api_readback_verified"
                if company_info_verified
                else "live_company_observed_production_app_and_oauth_gated"
                if qbo_live_company.get("observed") is True
                or qbo_subscription.get("live_company_observed") is True
                else "sandbox_creation_provider_blocked"
                if intuit.get("sandbox_creation_result") == "provider_error"
                else "oauth_and_companyinfo_readback_required"
            ),
            priority="high",
            evidence_types=(
                (["sandbox_creation_gate"] if intuit else [])
                + (["subscription_payment_scheduled"] if qbo_subscription else [])
                + (["bank_feed_consent_observed"] if qbo_bank_consent else [])
            ),
            next_action=(
                "Monitor the read-only production connection and keep projections owner-approved and read-back verified."
                if company_info_verified
                else "Complete the Intuit production app assessment, HTTPS endpoints, production credentials, OAuth, and read-only CompanyInfo snapshot."
                if qbo_live_company.get("observed") is True or qbo_subscription
                else "Restore Intuit sandbox creation, complete OAuth, then run the read-only snapshot."
            ),
        ),
        _workstream(
            "statutory_accounts",
            state=(
                "current_provider_register_verified"
                if company_register.get("accounts_current_on_register") is True
                else (
                    "provisional_evidence_present_live_registry_readback_required"
                    if accountant.get("statutory_accounts") == "appeared_up_to_date"
                    else "current_filing_state_unverified"
                )
            ),
            priority="high",
            evidence_types=(
                (["accountant_status_review"] if accountant else [])
                + (["company_register_status"] if company_register else [])
            ),
            next_action=(
                "Monitor the next accounts period and preserve the accepted filing receipt and source pack."
                if company_register.get("accounts_current_on_register") is True
                else "Read the current Companies House filing history and bind the accepted filing receipt."
            ),
        ),
        _workstream(
            "confirmation_statement",
            state=(
                "accepted_and_public_register_verified"
                if confirmation_acceptance.get("provider_state") == "accepted"
                and confirmation_acceptance.get("provider_acceptance_observed") is True
                and company_register.get("confirmation_statement_current_on_register") is True
                else (
                    "accepted_provider_verified"
                    if confirmation_acceptance.get("provider_state") == "accepted"
                    and confirmation_acceptance.get("provider_acceptance_observed") is True
                    else (
                        "submitted_received_acceptance_pending"
                        if confirmation.get("provider_state") == "submission_received_acceptance_pending"
                        else "provider_state_unverified"
                    )
                )
            ),
            priority="high",
            evidence_types=(
                ["confirmation_statement_receipt", "confirmation_statement_acceptance"]
                if confirmation_acceptance
                else (["confirmation_statement_receipt"] if confirmation else [])
            )
            + (["company_register_status"] if company_register else []),
            next_action=(
                "Monitor the next statement date and retain the accepted filing evidence."
                if company_register.get("confirmation_statement_current_on_register") is True
                else "Bind the accepted filing to the current Companies House history and capture the next due date."
                if confirmation_acceptance
                else "Wait for and bind the Companies House acceptance or rejection email."
            ),
        ),
        _workstream(
            "companies_house_identity_verification",
            state=(
                "psc_due_date_passed_completion_unverified"
                if identity_verification.get("psc_due_date_passed") is True
                and identity_verification.get("identity_verification_completion_observed") is False
                else "identity_verification_state_unverified"
            ),
            priority="critical",
            evidence_types=["identity_verification_status"] if identity_verification else [],
            next_action=(
                "Owner must complete or prove PSC identity verification through the official Companies House route; never persist the personal code."
                if identity_verification
                else "Obtain current director and PSC identity-verification status from Companies House."
            ),
        ),
        _workstream(
            "corporation_tax",
            state=(
                "urgent_outstanding_returns_and_penalties_resolution_required"
                if accountant.get("corporation_tax_returns")
                == "outstanding_or_penalty_indications_require_resolution"
                else "hmrc_live_state_unverified"
            ),
            priority="critical",
            evidence_types=["accountant_status_review"] if accountant else [],
            next_action="Obtain live HMRC periods, liabilities, penalties, and filed-return receipts with the accountant.",
        ),
        _workstream(
            "vat",
            state="registration_and_return_state_unverified",
            priority="high",
            evidence_types=[],
            next_action="Obtain live HMRC VAT registration and return-period evidence before enabling VAT.",
        ),
        _workstream(
            "paye",
            state=(
                "application_evidence_present_reference_unverified"
                if accountant.get("paye_reference") == "not_observed"
                else "paye_state_unverified"
            ),
            priority="high",
            evidence_types=["accountant_status_review"] if accountant else [],
            next_action="Obtain the PAYE reference and live HMRC scheme state; do not infer registration from an application.",
        ),
        _workstream(
            "cis_contractor_returns",
            state=(
                "contractor_obligation_unresolved"
                if accountant.get("cis_contractor_filing_obligation") == "unresolved"
                else "contractor_obligation_unverified"
            ),
            priority="critical",
            evidence_types=["accountant_status_review", "cis_deductions_suffered_statement"]
            if accountant or cis
            else [],
            next_action="Owner and accountant must confirm whether Aureon employed subcontractors and owes CIS returns.",
        ),
        _workstream(
            "cis_deductions_suffered",
            state=(
                "deduction_and_refund_claim_evidence_present_outcome_reconciliation_required"
                if cis.get("cis_deductions_suffered_evidenced") is True
                and cis_refund_claim.get("claim_submission_observed") is True
                and cis_refund_claim.get("refund_paid_or_settled_observed") is False
                else "evidence_present_amount_and_bank_match_required"
                if cis.get("cis_deductions_suffered_evidenced") is True
                else "deductions_suffered_unverified"
            ),
            priority="high",
            evidence_types=(
                (["cis_deductions_suffered_statement"] if cis else [])
                + (["cis_refund_claim_receipt"] if cis_refund_claim else [])
            ),
            next_action=(
                "Obtain the HMRC claim outcome or payment evidence, match it to the bank, and reconcile the underlying deductions."
                if cis_refund_claim
                else "Match statement amounts to invoices and bank receipts, then obtain accounting approval."
            ),
        ),
        _workstream(
            "banking",
            state=(
                "mixed_use_qbo_bank_consent_observed_import_and_classification_required"
                if bank.get("mixed_use_review_required") is True
                and qbo_bank_consent.get("transaction_import_readback_verified") is False
                else "mixed_use_owner_accountant_classification_required"
                if bank.get("mixed_use_review_required") is True
                else "entity_owned_accounts_and_processors_unverified"
            ),
            priority="critical",
            evidence_types=(
                (["mixed_use_bank_evidence"] if bank else [])
                + (["bank_feed_consent_observed"] if qbo_bank_consent else [])
            ),
            next_action=(
                "Read back the imported bank feed, classify ownership, separate personal activity, and reconcile every transaction to Aureon evidence."
                if qbo_bank_consent
                else "Separate personal and company activity and confirm every entity-owned bank and processor account."
            ),
        ),
        _workstream(
            "xero_migration",
            state=(
                "access_recovered_ledger_export_required"
                if xero.get("login_notice_observed") is True
                and xero.get("ledger_completeness_verified") is False
                else "organisation_and_ledger_state_unverified"
            ),
            priority="high",
            evidence_types=["access_recovery"] if xero else [],
            next_action="Open the correct Xero organisation and export chart, trial balance, journals, contacts, invoices, bills, and tax settings.",
        ),
        _workstream(
            "grants",
            state=(
                "no_award_or_funding_recognition_trigger_observed"
                if grants.get("award_confirmed_true_records") == 0
                and grants.get("funding_received_true_records") == 0
                else "award_and_funding_evidence_requires_review"
            ),
            priority="high",
            evidence_types=["grant_accounting_boundary"] if grants else [],
            next_action="Reconcile the grant-ledger count mismatch and recognise nothing until award terms or cash receipts are verified.",
        ),
        _workstream(
            "research_and_development_tax",
            state="project_cost_evidence_and_accountant_tax_review_required",
            priority="high",
            evidence_types=["grant_accounting_boundary"] if grants else [],
            next_action="Build project-by-project eligible cost evidence; accountant reviews any R&D tax claim before filing.",
        ),
    ]

    evidence_index: dict[str, list[dict[str, str]]] = {}
    for item in receipts:
        observation_type = str(item.get("observation_type", ""))
        evidence_index.setdefault(observation_type, []).append(
            {
                "source_system": str(item.get("source_system", "")),
                "receipt_sha256": str(item.get("receipt_sha256", "")),
                "observed_payload_sha256": str(item.get("observed_payload_sha256", "")),
            }
        )

    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "generated_at": _iso_now(),
        "authority": {
            "canonical_system": "aureon_os",
            "quickbooks_role": "downstream_projection_and_readback",
            "report_role": "derived_work_queue_not_ledger_or_filing_instruction",
            "postings_authorised": 0,
            "external_compliance_actions_authorised": 0,
        },
        "inputs": {
            "evidence_receipt_count": len(receipts),
            "evidence_observation_types": sorted(receipt_types),
            "quickbooks_status_sha256": str((quickbooks_status or {}).get("status_sha256", "")),
            "quickbooks_connection_state": str((quickbooks_status or {}).get("connection_state", "")),
            "quickbooks_company_info_readback": str(qbo_api.get("company_info_readback", "not_verified")),
        },
        "workstreams": workstreams,
        "summary": {
            "workstream_count": len(workstreams),
            "critical_workstream_count": sum(item["priority"] == "critical" for item in workstreams),
            "posting_authorised_count": sum(item["posting_authorised"] for item in workstreams),
            "quickbooks_projection_authorised_count": sum(
                item["quickbooks_projection_authorised"] for item in workstreams
            ),
            "external_compliance_action_authorised_count": sum(
                item["external_compliance_action_authorised"] for item in workstreams
            ),
        },
        "evidence_index": dict(sorted(evidence_index.items())),
    }
    report["report_sha256"] = payload_sha256(report)
    return report


def write_reconciliation_report(report: Mapping[str, Any], output: str | Path) -> Path:
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=destination.parent,
        prefix=f".{destination.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        json.dump(dict(report), handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, destination)
    return destination


def _default_suite_path(*parts: str) -> Path:
    return Path(__file__).resolve().parents[1].joinpath(*parts)


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate",))
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=_default_suite_path("output", "accounting_control", "evidence_observations"),
    )
    parser.add_argument(
        "--quickbooks-status",
        type=Path,
        default=_default_suite_path("output", "quickbooks", "status.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_default_suite_path("output", "accounting_control", "reconciliation_status.json"),
    )
    args = parser.parse_args()
    receipts = load_evidence_receipts(args.evidence_dir)
    quickbooks_status = _read_json_object(args.quickbooks_status) if args.quickbooks_status.exists() else {}
    report = build_reconciliation_report(receipts, quickbooks_status=quickbooks_status)
    destination = write_reconciliation_report(report, args.output)
    print(
        json.dumps(
            {
                "generated": True,
                "output": str(destination),
                "report_sha256": report["report_sha256"],
                "workstream_count": report["summary"]["workstream_count"],
                "posting_authorised_count": report["summary"]["posting_authorised_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
