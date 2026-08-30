from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip(
    "reportlab",
    reason="these suites assert rendered PDF artifacts; reportlab is the renderer",
)

from Kings_Accounting_Suite.tools.accounting_swarm_data_wave_scan import (
    file_readability_record,
    run_accounting_swarm_data_wave_scan,
    write_end_user_confirmation_artifacts,
    write_logic_chain_artifacts,
)


def test_swarm_wave_scan_includes_all_raw_files_and_benchmarks(tmp_path: Path) -> None:
    raw = tmp_path / "client_raw"
    raw.mkdir()
    bank_csv = raw / "Transactions Report MSAGM9YS 20260414.csv"
    bank_csv.write_text(
        "Transaction date,Transaction code,Reference,Amount,Available balance\n"
        "2024-05-03,FPI,Client receipt,250.00,250.00\n",
        encoding="utf-8",
    )
    receipt = raw / "sumup receipt.custom"
    receipt.write_text("sumup payout receipt", encoding="utf-8")
    notes = raw / "director notes.weird"
    notes.write_text("cash expense note", encoding="utf-8")
    skipped = raw / "cache" / "old-generated.txt"
    skipped.parent.mkdir()
    skipped.write_text("generated output that must be recorded as excluded", encoding="utf-8")

    period_dir = tmp_path / "Kings_Accounting_Suite" / "output" / "gateway" / "2024-05-01_to_2025-04-30"
    period_dir.mkdir(parents=True)
    (period_dir / "period_pack_manifest.json").write_text(
        json.dumps(
            {
                "combined_bank_data": {
                    "transaction_source_count": 1,
                    "csv_source_count": 1,
                    "unique_rows_in_period": 1,
                    "duplicate_rows_removed": 0,
                    "combined_csv_path": str(period_dir / "combined.csv"),
                    "csv_sources": [
                        {
                            "path": str(bank_csv),
                            "rows_read": 1,
                            "rows_in_period": 1,
                            "rows_imported": 1,
                            "source_account": "MSAGM9YS",
                            "source_kind": "transaction_report_csv",
                        }
                    ],
                    "pdf_sources": [],
                    "evidence_files": [str(receipt)],
                }
            }
        ),
        encoding="utf-8",
    )

    manifest = run_accounting_swarm_data_wave_scan(
        repo_root=tmp_path,
        company_name="Example Ltd",
        company_number="NI000001",
        period_start="2024-05-01",
        period_end="2025-04-30",
        raw_data_roots=[raw],
        include_default_roots=False,
    )

    by_name = {item["name"]: item for item in manifest["files"]}
    assert manifest["schema_version"] == "accounting-swarm-raw-data-wave-scan-v1"
    assert manifest["status"] == "completed"
    assert manifest["benchmark"]["files_scanned"] == 3
    assert manifest["benchmark"]["files_per_second"] > 0
    assert manifest["source_closure"]["status"] == "closed_no_silent_skips"
    assert manifest["source_closure"]["included_file_count"] == 3
    assert manifest["source_closure"]["excluded_file_count"] == 1
    assert manifest["source_closure"]["unaccounted_file_count"] == 0
    assert by_name[bank_csv.name]["fold_status"] == "folded_transaction_feed"
    assert by_name[bank_csv.name]["file_read_status"] == "readable_csv"
    assert by_name[receipt.name]["file_read_status"] == "readable_text"
    assert by_name[receipt.name]["fold_status"] == "folded_evidence_inventory"
    assert by_name[notes.name]["fold_status"] == "catalogued_for_review"
    assert by_name[notes.name]["supported_by_standard_intake"] is False
    assert by_name[notes.name]["readable_by_aureon"] is True
    assert manifest["file_readability"]["file_count"] == 3
    assert manifest["file_readability"]["readable_file_count"] == 3
    assert manifest["file_readability"]["blocked_file_count"] == 0
    assert manifest["waves"]["phi_swarm_consensus"]["score"] >= 0
    assert manifest["waves"]["phi_swarm_consensus"]["readability_ratio"] == 1.0
    assert any(item["id"] == "swarm_only_attention_queue" for item in manifest["internal_logic_chain_checklist"])
    assert any(item["id"] == "no_silent_source_skips" for item in manifest["internal_logic_chain_checklist"])
    assert any(item["id"] == "read_or_account_for_every_file" for item in manifest["internal_logic_chain_checklist"])
    assert Path(manifest["outputs"]["swarm_raw_data_wave_scan_json"]).exists()
    assert Path(manifest["outputs"]["swarm_raw_data_wave_scan_markdown"]).exists()
    assert Path(manifest["outputs"]["no_data_skipped_source_closure_audit_json"]).exists()
    assert Path(manifest["outputs"]["no_data_skipped_source_closure_audit_csv"]).exists()
    assert Path(manifest["outputs"]["no_data_skipped_source_closure_audit_markdown"]).exists()
    assert Path(manifest["outputs"]["no_data_skipped_source_closure_audit_pdf"]).exists()
    assert Path(manifest["outputs"]["all_source_file_readability_audit_json"]).exists()
    assert Path(manifest["outputs"]["all_source_file_readability_audit_csv"]).exists()
    assert Path(manifest["outputs"]["all_source_file_readability_audit_markdown"]).exists()
    assert Path(manifest["outputs"]["all_source_file_readability_audit_pdf"]).exists()

    logic_paths = write_logic_chain_artifacts(manifest, output_dir=tmp_path / "out")
    confirmation_paths = write_end_user_confirmation_artifacts(manifest, output_dir=tmp_path / "out")
    assert Path(logic_paths["internal_logic_chain_checklist_json"]).exists()
    assert Path(confirmation_paths["end_user_confirmation_markdown"]).read_text(encoding="utf-8").startswith("# End-User Confirmation")


def test_file_readability_records_blocked_binary_with_next_action(tmp_path: Path) -> None:
    binary = tmp_path / "scan.receipt.bin"
    binary.write_bytes(b"\x00\x01\x02\x03")

    record = file_readability_record(binary, tmp_path)

    assert record["readable_by_aureon"] is False
    assert record["status"] == "unsupported_binary_requires_converter"
    assert "converter" in record["autonomous_next_action"].lower()
