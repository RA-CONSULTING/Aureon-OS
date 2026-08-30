from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

pytest.importorskip(
    "reportlab",
    reason="these suites assert rendered PDF artifacts; reportlab is the renderer",
)

from Kings_Accounting_Suite.tools import end_user_accounting_automation as automation


def test_end_user_accounting_automation_wraps_raw_data_to_requirement_coverage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    raw = tmp_path / "client_raw"
    raw.mkdir()
    (raw / "revolut.csv").write_text("Date,Description,Amount\n2024-05-01,Sale,100.00\n", encoding="utf-8")

    def fake_workflow(**kwargs):
        out = tmp_path / "out"
        out.mkdir()
        for rel in ("handoff/01_raw_evidence", "handoff/04_companies_house", "handoff/05_hmrc_corporation_tax"):
            folder = out / rel
            folder.mkdir(parents=True)
            (folder / "fixture.txt").write_text("fixture", encoding="utf-8")
        return {
            "status": "completed",
            "manifest_path": str(out / "workflow.json"),
            "summary_path": str(out / "workflow.md"),
            "raw_data_manifest": {"summary": {"file_count": 1, "transaction_source_count": 1}},
            "full_accounts_result": {
                "manifest": {
                    "source_data_inventory": {
                        "combined_bank_data": {
                            "transaction_source_count": 1,
                            "csv_source_count": 1,
                            "unique_rows_in_period": 1,
                        }
                    },
                    "outputs": {
                        "accounts_pack_pdf": {"path": str(out / "accounts.pdf"), "exists": True},
                        "management_accounts": {"path": str(out / "management.xlsx"), "exists": True},
                        "general_ledger": {"path": str(out / "ledger.xlsx"), "exists": True},
                        "trial_balance": {"path": str(out / "trial.xlsx"), "exists": True},
                    },
                    "statutory_filing_pack": {
                        "outputs": {
                            "companies_house_accounts_pdf": {"path": str(out / "ch_accounts.pdf"), "exists": True},
                            "ct600_manual_entry_json": {"path": str(out / "ct600_manual_entry.json"), "exists": True},
                            "hmrc_ct600_draft_json": {"path": str(out / "ct600.json"), "exists": True},
                            "hmrc_tax_computation_pdf": {"path": str(out / "tax.pdf"), "exists": True},
                            "data_truth_checklist_pdf": {"path": str(out / "truth.pdf"), "exists": True},
                            "math_stress_test_pdf": {"path": str(out / "stress.pdf"), "exists": True},
                            "payer_provenance_pdf": {"path": str(out / "payer_provenance.pdf"), "exists": True},
                            "payer_provenance_json": {"path": str(out / "payer_provenance.json"), "exists": True},
                            "payer_provenance_csv": {"path": str(out / "payer_provenance.csv"), "exists": True},
                            "cis_vat_tax_basis_assurance_pdf": {"path": str(out / "cis_vat.pdf"), "exists": True},
                            "ixbrl_readiness_note": {"path": str(out / "ixbrl.md"), "exists": True},
                            "confirmation_statement_readiness_markdown": {"path": str(out / "cs01.md"), "exists": True},
                            "filing_checklist": {"path": str(out / "checklist.md"), "exists": True},
                            "government_requirements_matrix_markdown": {"path": str(out / "requirements.md"), "exists": True},
                            "audit_exemption_statement_markdown": {"path": str(out / "audit_exemption.md"), "exists": True},
                            "ct600_box_map_markdown": {"path": str(out / "ct600_box_map.md"), "exists": True},
                            "supplementary_pages_review_json": {"path": str(out / "supplementary.json"), "exists": True},
                            "confirmation_statement_readiness_json": {"path": str(out / "confirmation.json"), "exists": True},
                            "confirmation_statement_readiness_markdown": {"path": str(out / "confirmation.md"), "exists": True},
                            "accounts_readable_for_ixbrl_html": {"path": str(out / "accounts_ixbrl.html"), "exists": True},
                            "computation_readable_for_ixbrl_html": {"path": str(out / "computation_ixbrl.html"), "exists": True},
                            "ixbrl_readiness_note": {"path": str(out / "ixbrl.md"), "exists": True},
                        }
                    },
                }
            },
            "human_filing_handoff_pack": {
                "status": "completed",
                "output_dir": str(out / "handoff"),
                "outputs": {"manifest": str(out / "handoff.json"), "start_here": str(out / "START_HERE.md")},
            },
            "accounting_evidence_authoring": {
                "summary": {"draft_count": 3, "generated_document_count": 2},
                "outputs": {"accounting_evidence_requests_csv": str(out / "evidence.csv")},
            },
            "uk_accounting_requirements_brain": {
                "summary": {
                    "requirement_count": 8,
                    "question_count": 66,
                    "unresolved_question_count": 30,
                    "question_domain_counts": {"company_identity": 8, "tax_ct600": 7},
                },
                "outputs": {
                    "uk_accounting_requirements_brain_markdown": str(out / "brain.md"),
                    "expanded_accounting_self_questions_pdf": str(out / "21.pdf"),
                    "expanded_accounting_self_questions_json": str(out / "21.json"),
                    "expanded_accounting_self_questions_csv": str(out / "21.csv"),
                    "missing_data_and_evidence_action_plan_pdf": str(out / "22.pdf"),
                    "missing_data_and_evidence_action_plan_json": str(out / "22.json"),
                    "missing_data_and_evidence_action_plan_csv": str(out / "22.csv"),
                    "risk_and_contradiction_register_pdf": str(out / "23.pdf"),
                    "risk_and_contradiction_register_json": str(out / "23.json"),
                    "risk_and_contradiction_register_csv": str(out / "23.csv"),
                },
            },
        }

    monkeypatch.setattr(automation, "run_autonomous_full_accounts_workflow", fake_workflow)
    def fake_readiness_file_check(check_id, label, path_value, folder_hint, *, required_tokens=(), json_required=False):
        path = Path(str(path_value or (tmp_path / "out" / f"{check_id}.txt")))
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".json":
            path.write_text("{}", encoding="utf-8")
        else:
            path.write_text("fixture content", encoding="utf-8")
        return {
            "id": check_id,
            "label": label,
            "status": "passed",
            "path": str(path),
            "folder_hint": folder_hint,
            "bytes": path.stat().st_size,
            "evidence": "fixture passed",
            "next_action": "Use this artifact in the manual filing workflow.",
        }

    monkeypatch.setattr(automation, "readiness_file_check", fake_readiness_file_check)

    manifest = automation.run_end_user_accounting_automation(
        repo_root=tmp_path,
        company_name="Example Ltd",
        company_number="NI000001",
        period_start="2024-05-01",
        period_end="2025-04-30",
        as_of=date(2026, 5, 9),
        raw_data_roots=[raw],
        include_default_roots=False,
        no_fetch=True,
        enable_cognitive_review=False,
    )

    coverage = {item["id"]: item for item in manifest["requirement_coverage"]}
    assert manifest["schema_version"] == "end-user-accounting-automation-v1"
    assert manifest["status"] == "completed"
    assert coverage["raw_data_intake"]["status"] == "final_ready_manual_upload_required"
    assert coverage["raw_data_swarm_wave_scan"]["status"] == "final_ready_manual_upload_required"
    assert coverage["all_source_file_readability"]["status"] == "final_ready_manual_upload_required"
    assert coverage["no_data_skipped_source_closure"]["status"] == "final_ready_manual_upload_required"
    assert coverage["final_filing_ready_folder_audit"]["status"] == "final_ready_manual_upload_required"
    assert coverage["internal_logic_chain_checklist"]["status"] == "final_ready_manual_upload_required"
    assert coverage["end_user_confirmation_feed"]["status"] == "final_ready_manual_upload_required"
    assert coverage["companies_house_annual_accounts"]["status"] == "final_ready_manual_upload_required"
    assert coverage["hmrc_company_tax_return"]["status"] == "final_ready_manual_upload_required"
    assert coverage["expanded_uk_accounting_self_questioning"]["status"] == "final_ready_manual_upload_required"
    assert coverage["official_filing_and_payment"]["status"] == "manual_required"
    assert manifest["safe_boundaries"]["official_hmrc_submission"] == "manual_only"
    assert Path(manifest["outputs"]["end_user_automation_manifest"]).exists()
    assert Path(manifest["outputs"]["swarm_raw_data_wave_scan_json"]).exists()
    assert Path(manifest["outputs"]["all_source_file_readability_audit_json"]).exists()
    assert Path(manifest["outputs"]["all_source_file_readability_audit_pdf"]).exists()
    assert Path(manifest["outputs"]["no_data_skipped_source_closure_audit_json"]).exists()
    assert Path(manifest["outputs"]["no_data_skipped_source_closure_audit_pdf"]).exists()
    assert Path(manifest["outputs"]["final_filing_readiness_audit_json"]).exists()
    assert Path(manifest["outputs"]["final_filing_readiness_audit_pdf"]).exists()
    assert manifest["final_filing_readiness_audit"]["status"] == "final_ready_manual_upload_required"
    assert Path(manifest["outputs"]["internal_logic_chain_checklist_markdown"]).exists()
    assert Path(manifest["outputs"]["end_user_confirmation_markdown"]).exists()
    assert Path(manifest["outputs"]["read_me_first_folder_pdf"]).exists()
    assert Path(manifest["outputs"]["full_accounts_pdf_index"]).exists()
    assert Path(manifest["outputs"]["end_user_confirmation_pdf"]).exists()
    assert "data_truth_checklist_pdf" in manifest["outputs"]
    assert "math_stress_test_pdf" in manifest["outputs"]
    assert "expanded_accounting_self_questions_pdf" in manifest["outputs"]
    assert "missing_data_and_evidence_action_plan_pdf" in manifest["outputs"]
    assert "risk_and_contradiction_register_pdf" in manifest["outputs"]
    assert manifest["swarm_raw_data_wave_scan"]["benchmark"]["files_scanned"] == 1
    assert manifest["end_user_confirmation"]["what_aureon_confirmed"]
    start_here = Path(manifest["outputs"]["end_user_start_here"]).read_text(encoding="utf-8")
    assert "Raw data in -> accounts pack out." in start_here
    assert "Swarm Wave Scan" in start_here
    assert "No HMRC return was submitted." in start_here
    assert "manually upload" in start_here
