from __future__ import annotations

import csv
import json
from pathlib import Path
from decimal import Decimal

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

from Kings_Accounting_Suite.tools import generate_statutory_filing_pack as statutory  # noqa: E402


def test_build_figures_includes_cis_suffered_before_bank_receipt() -> None:
    figures = statutory.build_figures(
        [
            {"Date": "2025-03-05", "Description": "GROVE BUILDERS LTD GROVE BUILDERS LTD", "Amount": "476.64"},
            {"Date": "2025-03-06", "Description": "GitHub subscription", "Amount": "-20.00"},
        ]
    )

    assert figures.raw_bank_turnover == Decimal("476.64")
    assert figures.turnover == Decimal("600.00")
    assert figures.cis_deduction_suffered_total == Decimal("119.16")
    assert figures.cis_citb_levy_total == Decimal("4.20")
    assert figures.expenses == Decimal("24.20")
    assert figures.profit_before_tax == Decimal("575.80")
    assert figures.corporation_tax == Decimal("109.40")
    assert figures.corporation_tax_after_cis_credit == Decimal("109.40")
    assert figures.cis_credit_surplus_or_refund_review == Decimal("119.16")
    assert figures.cis_limited_company_claim_route == "monthly_payroll_eps_or_refund_review_not_ct600"


def test_corporation_tax_uses_marginal_relief_between_small_and_main_rates() -> None:
    tax, effective_rate = statutory.corporation_tax_for_profit(Decimal("67345.10"))

    assert tax == Decimal("14096.45")
    assert effective_rate == Decimal("0.2093")


def test_ct_financial_year_split_reconciles_actual_transaction_slices() -> None:
    tax, effective_rate = statutory.corporation_tax_for_profit(Decimal("1150.00"))
    figures = statutory.FilingFigures(
        turnover=Decimal("1200.00"),
        expenses=Decimal("50.00"),
        profit_before_tax=Decimal("1150.00"),
        taxable_profit=Decimal("1150.00"),
        corporation_tax_rate=effective_rate,
        corporation_tax=tax,
        profit_after_tax=Decimal("931.50"),
        bank_net_assets=Decimal("1150.00"),
        net_assets=Decimal("931.50"),
        raw_bank_turnover=Decimal("1200.00"),
        raw_bank_expenses=Decimal("50.00"),
        vat_taxable_turnover_estimate=Decimal("1200.00"),
    )
    enrichment = {
        "transactions": [
            {
                "date": "2025-03-31",
                "amount": "1000.00",
                "cis_scope": "not_cis_income",
                "final_ledger_account": "sales_turnover",
                "cis_gross_income": "0.00",
                "cis_net_banked": "0.00",
                "cis_deduction_suffered": "0.00",
                "cis_citb_levy": "0.00",
                "vat_taxable_turnover": "1000.00",
            },
            {
                "date": "2025-04-01",
                "amount": "200.00",
                "cis_scope": "not_cis_income",
                "final_ledger_account": "sales_turnover",
                "cis_gross_income": "0.00",
                "cis_net_banked": "0.00",
                "cis_deduction_suffered": "0.00",
                "cis_citb_levy": "0.00",
                "vat_taxable_turnover": "200.00",
            },
            {
                "date": "2025-04-02",
                "amount": "-50.00",
                "cis_scope": "not_cis_income",
                "final_ledger_account": "software_and_subscriptions",
                "cis_gross_income": "0.00",
                "cis_net_banked": "0.00",
                "cis_deduction_suffered": "0.00",
                "cis_citb_levy": "0.00",
                "vat_taxable_turnover": "0.00",
            },
        ]
    }

    split = statutory.build_ct_financial_year_split(
        period_start="2024-05-01",
        period_end="2025-04-30",
        figures=figures,
        enrichment=enrichment,
    )

    assert [item["label"] for item in split["slices"]] == ["FY2024", "FY2025"]
    assert split["slices"][0]["date_start"] == "2024-05-01"
    assert split["slices"][0]["date_end"] == "2025-03-31"
    assert split["slices"][0]["turnover"] == "1000.00"
    assert split["slices"][0]["taxable_profit_support"] == "1000.00"
    assert split["slices"][1]["date_start"] == "2025-04-01"
    assert split["slices"][1]["date_end"] == "2025-04-30"
    assert split["slices"][1]["turnover"] == "200.00"
    assert split["slices"][1]["expenses"] == "50.00"
    assert split["slices"][1]["taxable_profit_support"] == "150.00"
    assert split["reconciliation"]["status"] == "reconciled"
    assert split["slice_totals"]["turnover"] == "1200.00"
    assert split["slice_totals"]["corporation_tax_allocated_from_whole_period"] == "218.50"


def test_statutory_filing_pack_generates_companies_house_and_hmrc_outputs(tmp_path: Path, monkeypatch) -> None:
    fake_kas = tmp_path / "Kings_Accounting_Suite"
    period = fake_kas / "output" / "gateway" / "2024-05-01_to_2025-04-30"
    period.mkdir(parents=True)

    combined_csv = period / "combined_bank_transactions_2024-05-01_to_2025-04-30.csv"
    with combined_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "Date",
                "Description",
                "Amount",
                "Balance",
                "Source Provider",
                "Flow Provider",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "Date": "2024-05-01",
                "Description": "Client income",
                "Amount": "1000.00",
                "Balance": "1000.00",
                "Source Provider": "zempler",
                "Flow Provider": "zempler",
            }
        )
        writer.writerow(
            {
                "Date": "2024-05-02",
                "Description": "Software",
                "Amount": "-100.00",
                "Balance": "900.00",
                "Source Provider": "revolut",
                "Flow Provider": "revolut",
            }
        )

    manifest = {
        "combined_bank_data": {
            "combined_csv_path": str(combined_csv),
            "transaction_source_count": 2,
            "csv_source_count": 1,
            "pdf_source_count": 1,
            "unique_rows_in_period": 2,
            "duplicate_rows_removed": 0,
            "source_accounts": ["business_gbp_monthly", "uploads_statement"],
            "source_provider_summary": {
                "zempler": {"rows": 1, "money_in": "1000.00", "money_out": "0.00", "net": "1000.00"},
                "revolut": {"rows": 1, "money_in": "0.00", "money_out": "-100.00", "net": "-100.00"},
            },
            "flow_provider_summary": {
                "zempler": {"rows": 1, "money_in": "1000.00", "money_out": "0.00", "net": "1000.00"},
                "revolut": {"rows": 1, "money_in": "0.00", "money_out": "-100.00", "net": "-100.00"},
            },
        }
    }
    (period / "period_pack_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(statutory, "KAS_DIR", fake_kas)

    result = statutory.build_pack(
        company_name="EXAMPLE TRADING LTD",
        company_number="00000000",
        period_start="2024-05-01",
        period_end="2025-04-30",
    )

    outputs = result["outputs"]
    assert result["filing_readiness_contract"]["status"] == "final_ready_manual_upload_required"
    assert outputs["companies_house_accounts_final_ready_pdf"]["exists"] is True
    assert outputs["ct600_manual_entry_json"]["exists"] is True
    assert outputs["hmrc_tax_computation_final_ready_markdown"]["exists"] is True
    assert outputs["full_accounts_pack_pdf"]["exists"] is True
    assert outputs["profit_and_loss_detailed_pdf"]["exists"] is True
    assert outputs["expense_breakdown_pdf"]["exists"] is True
    assert outputs["transaction_classification_audit_pdf"]["exists"] is True
    assert outputs["source_reconciliation_pdf"]["exists"] is True
    assert outputs["data_truth_checklist_pdf"]["exists"] is True
    assert outputs["math_stress_test_pdf"]["exists"] is True
    assert outputs["payer_provenance_pdf"]["exists"] is True
    assert outputs["payer_provenance_json"]["exists"] is True
    assert outputs["payer_provenance_csv"]["exists"] is True
    assert outputs["cis_vat_tax_basis_assurance_pdf"]["exists"] is True
    assert outputs["corporation_tax_summary_pdf"]["exists"] is True
    assert outputs["official_template_audit_json"]["exists"] is True
    assert outputs["enriched_transactions_csv"]["exists"] is True
    assert outputs["ct_financial_year_split_json"]["exists"] is True
    assert outputs["ct_financial_year_split_csv"]["exists"] is True
    assert outputs["ct_financial_year_split_markdown"]["exists"] is True
    assert outputs["ct_financial_year_split_pdf"]["exists"] is True
    assert outputs["companies_house_accounts_markdown"]["exists"] is True
    assert outputs["hmrc_ct600_draft_json"]["exists"] is True
    assert outputs["hmrc_tax_computation_markdown"]["exists"] is True
    assert outputs["government_requirements_matrix_json"]["exists"] is True
    assert outputs["directors_report_markdown"]["exists"] is True
    assert outputs["ct600_box_map_markdown"]["exists"] is True
    assert outputs["confirmation_statement_readiness_json"]["exists"] is True
    assert result["figures"]["turnover"] == "1000.00"
    assert result["figures"]["expenses"] == "100.00"
    assert result["figures"]["corporation_tax"] == "171.00"
    matrix = result["government_requirements_matrix"]
    assert matrix["summary"]["requirement_count"] >= 10
    ids = {item["id"] for item in matrix["requirements"]}
    assert "hmrc.company_tax_return.ct600" in ids
    assert "hmrc.company_tax_return.ct_financial_year_split" in ids
    assert "companies_house.annual_accounts.balance_sheet" in ids
    assert "companies_house.confirmation_statement" in ids
    assert result["safety"]["submitted_to_hmrc"] is False
    assert result["safety"]["filed_with_companies_house"] is False
    assert result["accounting_report_enrichment"]["row_count"] == 2
    assert result["accounting_report_enrichment"]["totals"]["reconciles_to_filing_figures"] is True
    assert result["accounting_report_enrichment"]["payer_provenance_summary"]["incoming_rows_total"] == 1
    assert result["accounting_report_enrichment"]["payer_provenance_summary"]["lookup_required_count"] == 1
    assert result["payer_provenance_manifest"]["summary"]["lookup_required_plus_not_required_equals_total"] is True
    template_audit = result["official_template_audit"]
    assert template_audit["status"] == "complete_external_audit_ready"
    ct600 = json.loads(Path(outputs["ct600_manual_entry_json"]["path"]).read_text(encoding="utf-8"))
    assert ct600["schema_version"] == "hmrc-ct600-manual-entry-v1"
    assert "ct_financial_year_split_v1" in ct600["schema_features"]
    assert ct600["status"] == "final_ready_manual_upload_required"
    assert ct600["ct_financial_year_split"]["reconciliation"]["status"] == "reconciled"
    assert ct600["ct600_support"]["manual_classification_review_rows"] >= 0

    split = json.loads(Path(outputs["ct_financial_year_split_json"]["path"]).read_text(encoding="utf-8"))
    assert [item["label"] for item in split["slices"]] == ["FY2024", "FY2025"]
    assert split["slices"][0]["date_start"] == "2024-05-01"
    assert split["slices"][0]["date_end"] == "2025-03-31"
    assert split["slices"][1]["date_start"] == "2025-04-01"
    assert split["slices"][1]["date_end"] == "2025-04-30"
    assert split["whole_period"]["turnover"] == "1000.00"
    assert split["reconciliation"]["status"] == "reconciled"

    pnl_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(outputs["profit_and_loss_detailed_pdf"]["path"]).pages
    )
    assert "Expense Breakdown" in pnl_text
    assert "Software" in pnl_text or "Uncategorised" in pnl_text

    computation_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(outputs["hmrc_tax_computation_final_ready_pdf"]["path"]).pages
    )
    assert "Tax Adjustment" in computation_text
    assert "CT600 Manual Entry Support" in computation_text
    assert "Corporation Tax Financial-Year Split Support" in computation_text

    truth_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(outputs["data_truth_checklist_pdf"]["path"]).pages
    )
    assert "Internal Questions" in truth_text
    assert "Where The Data Is" in truth_text

    payer_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(outputs["payer_provenance_pdf"]["path"]).pages
    )
    assert "No-Missed-Incoming Control" in payer_text
    assert "Incoming Payment Register" in payer_text

    cis_vat_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(outputs["cis_vat_tax_basis_assurance_pdf"]["path"]).pages
    )
    assert "Tax Basis Summary" in cis_vat_text
    assert "CIS Treatment Counts" in cis_vat_text

    stress_text = "\n".join(
        page.extract_text() or ""
        for page in PdfReader(outputs["math_stress_test_pdf"]["path"]).pages
    )
    assert "Arithmetic Stress Tests" in stress_text
    assert "GBP 0.00" in stress_text
