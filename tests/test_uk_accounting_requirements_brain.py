from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip(
    "reportlab",
    reason="these suites assert rendered PDF artifacts; reportlab is the renderer",
)

# pypdf is declared in Kings_Accounting_Suite/requirements.txt but not the root install, and
# the runtime imports it lazily (research_corpus_index.py) — so it is genuinely optional.
# Skipping keeps a root-only install collecting instead of erroring on import.
pytest.importorskip("pypdf", reason="pypdf is an optional accounting-suite dependency")

from pypdf import PdfReader  # noqa: E402

from Kings_Accounting_Suite.tools.uk_accounting_requirements_brain import (  # noqa: E402
    QUESTION_SAFE_STATUSES,
    REQUIRED_SELF_QUESTION_DOMAINS,
    build_uk_accounting_requirements_brain,
    write_uk_accounting_brain_artifacts,
)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_uk_accounting_requirements_brain_flags_vat_utr_and_questions(tmp_path: Path) -> None:
    ct600 = write(
        tmp_path / "hmrc_ct600_draft.json",
        json.dumps({"utr": "", "figures": {"turnover": "95000.00"}}),
    )
    artifacts = [
        {"output_key": "raw_data_manifest_json", "exists": True, "destination_path": str(tmp_path / "raw.json")},
        {"output_key": "combined_bank_transactions", "exists": True, "destination_path": str(tmp_path / "combined.csv")},
        {"output_key": "period_manifest", "exists": True, "destination_path": str(tmp_path / "period.json")},
        {"output_key": "full_run_manifest", "exists": True, "destination_path": str(tmp_path / "full.json")},
        {"output_key": "hmrc_ct600_draft_json", "exists": True, "destination_path": str(ct600)},
        {"output_key": "hmrc_tax_computation_markdown", "exists": True, "destination_path": str(tmp_path / "tax.md")},
        {"output_key": "companies_house_accounts_pdf", "exists": True, "destination_path": str(tmp_path / "accounts.pdf")},
        {"output_key": "confirmation_statement_readiness_json", "exists": True, "destination_path": str(tmp_path / "cs01.json")},
    ]
    context = {
        "raw_data_manifest": {"summary": {"file_count": 4, "transaction_source_count": 3}},
        "period_manifest": {
            "combined_bank_data": {
                "transaction_source_count": 3,
                "unique_rows_in_period": 120,
                "source_provider_summary": {"sumup": {"rows": 10}, "zempler": {"rows": 80}},
                "flow_provider_summary": {"revolut": {"rows": 30}},
            }
        },
        "statutory_manifest": {
            "figures": {"turnover": "95000.00", "profit_before_tax": "2000.00", "corporation_tax": "380.00"},
            "outputs": {"hmrc_ct600_draft_json": {"path": str(ct600), "exists": True}},
        },
    }

    brain = build_uk_accounting_requirements_brain(
        company_name="Example Ltd",
        company_number="NI000001",
        period_start="2024-05-01",
        period_end="2025-04-30",
        context=context,
        artifacts=artifacts,
    )

    assert brain["schema_version"] == "uk-accounting-requirements-brain-v1"
    assert brain["summary"]["requirement_count"] >= 7
    assert brain["summary"]["question_count"] >= 60
    assert set(REQUIRED_SELF_QUESTION_DOMAINS).issubset(brain["summary"]["question_domain_counts"])
    assert brain["figures"]["turnover_over_vat_threshold"] is True
    requirement_statuses = {item["id"]: item["status"] for item in brain["requirements"]}
    assert requirement_statuses["uk.hmrc.vat_registration_and_mtd"] == "vat_registration_review_required"
    question_ids = {item["id"] for item in brain["accountant_self_questions"]}
    assert {
        "q.data_scope.all_accounts_present",
        "q.records.evidence_authoring_needed",
        "q.hmrc.utr_present",
        "q.vat.threshold_and_registration",
        "q.hmrc.ct600_ixbrl_ready",
        "q.companies_house.accounts_route",
        "q.companies_house.confirmation_statement",
        "q.tax.adjustments_and_reliefs",
        "q.paye_cis.edge_obligations",
    }.issubset(question_ids)
    for question in brain["accountant_self_questions"]:
        assert question["domain"] in set(REQUIRED_SELF_QUESTION_DOMAINS)
        assert question["status"] in QUESTION_SAFE_STATUSES
        assert question["reviewer_role"]
        assert question["risk_level"]
        assert question["confidence"]
    utr_question = next(item for item in brain["accountant_self_questions"] if item["id"] == "q.hmrc.utr_present")
    assert utr_question["status"] == "needs_secret_manual_input"
    assert "vat_registration_threshold" in brain["official_sources"]

    outputs = write_uk_accounting_brain_artifacts(brain, tmp_path / "handoff")
    assert Path(outputs["uk_accounting_requirements_brain_json"]).exists()
    assert Path(outputs["uk_accounting_requirements_brain_markdown"]).exists()
    assert Path(outputs["accountant_self_questions_markdown"]).exists()
    assert Path(outputs["expanded_accounting_self_questions_json"]).exists()
    assert Path(outputs["expanded_accounting_self_questions_csv"]).exists()
    assert Path(outputs["expanded_accounting_self_questions_pdf"]).exists()
    assert Path(outputs["missing_data_and_evidence_action_plan_pdf"]).exists()
    assert Path(outputs["risk_and_contradiction_register_pdf"]).exists()

    expanded_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(outputs["expanded_accounting_self_questions_pdf"]).pages
    )
    assert "Expanded UK Accounting Self-Questions" in expanded_text
    assert "company_identity" in expanded_text
    assert "tax_ct600" in expanded_text

    missing_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(outputs["missing_data_and_evidence_action_plan_pdf"]).pages
    )
    assert "Autonomous Allocation And Eye-Scan Action Plan" in missing_text
    assert "eye-scan" in missing_text.lower()

    risk_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(outputs["risk_and_contradiction_register_pdf"]).pages
    )
    assert "Risk And Contradiction Register" in risk_text
    assert "HMRC" in risk_text or "tax" in risk_text.lower()
