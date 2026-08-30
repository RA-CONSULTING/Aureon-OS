from __future__ import annotations

from datetime import date
from pathlib import Path

from Kings_Accounting_Suite.tools import autonomous_full_accounts_workflow as workflow


class FakeBus:
    def __init__(self):
        self.events = []

    def publish(self, topic, payload=None, source=""):
        self.events.append({"topic": topic, "payload": payload or {}, "source": source})


def test_autonomous_full_accounts_workflow_coordinates_raw_data_and_agents(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AUREON_OBSIDIAN_VAULT_PATH", str(tmp_path / "vault"))
    raw = tmp_path / "client_raw"
    raw.mkdir()
    (raw / "Statement_06_Apr_2024_05_Apr_2025.csv").write_text(
        "Date,Description,Amount,Balance\n2024-05-03,Client receipt,100.00,100.00\n",
        encoding="utf-8",
    )

    def fake_build_full_company_accounts(**kwargs):
        return {
            "status": "completed",
            "exit_code": 0,
            "manifest": {
                "accounts_build": {"status": "completed"},
                "source_data_inventory": {
                    "combined_bank_data": {
                        "transaction_source_count": 1,
                        "csv_source_count": 1,
                        "unique_rows_in_period": 1,
                        "combined_csv_path": str(raw / "combined.csv"),
                    }
                },
                "outputs": {"accounts_pack_pdf": {"path": str(raw / "pack.pdf"), "exists": True}},
                "statutory_filing_pack": {
                    "outputs": {
                        "hmrc_ct600_draft_json": {"path": str(raw / "ct600.json"), "exists": True},
                        "ct600_manual_entry_json": {"path": str(raw / "ct600_manual_entry.json"), "exists": True},
                        "filing_checklist": {"path": str(raw / "checklist.md"), "exists": True},
                    }
                },
            },
            "audit_json": str(raw / "audit.json"),
            "audit_markdown": str(raw / "audit.md"),
        }

    monkeypatch.setattr(workflow, "build_full_company_accounts", fake_build_full_company_accounts)
    monkeypatch.setattr(workflow, "build_goal_map", lambda *args, **kwargs: {"recommended_routes": [{"route": "accounting"}]})
    monkeypatch.setattr(
        workflow,
        "run_handoff_pack",
        lambda *args, **kwargs: {
            "status": "completed",
            "output_dir": str(raw / "handoff"),
            "readiness": {"ready_for_manual_review": True, "ready_for_manual_upload": True, "manual_inputs_required_count": 3},
            "accounting_evidence_authoring": {
                "status": "completed",
                "summary": {"draft_count": 4, "generated_document_count": 4, "petty_cash_withdrawal_count": 1},
                "outputs": {
                    "accounting_evidence_authoring_manifest": str(raw / "handoff" / "evidence.json"),
                    "accounting_evidence_requests_csv": str(raw / "handoff" / "evidence.csv"),
                },
            },
            "uk_accounting_requirements_brain": {
                "status": "ready_for_manual_review",
                "summary": {"requirement_count": 7, "question_count": 8, "unresolved_question_count": 3},
                "figures": {"turnover_over_vat_threshold": True},
            },
            "outputs": {
                "manifest": str(raw / "handoff" / "filing_handoff_manifest.json"),
                "start_here": str(raw / "handoff" / "START_HERE.md"),
            },
        },
    )
    monkeypatch.setattr(
        workflow,
        "run_cognitive_accounting_review",
        lambda *args, **kwargs: {
            "status": "completed",
            "answer_source": "fake",
            "summary": "reviewed",
            "note_path": "autonomy/cycles/fake.md",
            "actions": [],
            "errors": [],
        },
    )
    bus = FakeBus()

    manifest = workflow.run_autonomous_full_accounts_workflow(
        repo_root=tmp_path,
        company_name="Example Ltd",
        company_number="NI000001",
        period_start="2024-05-01",
        period_end="2025-04-30",
        as_of=date(2026, 5, 9),
        raw_data_roots=[raw],
        include_default_roots=False,
        no_fetch=True,
        thought_bus=bus,
    )

    assert manifest["status"] == "completed"
    assert manifest["raw_data_manifest"]["summary"]["file_count"] == 1
    assert manifest["vault_memory"]["status"] == "written"
    assert manifest["human_filing_handoff_pack"]["readiness"]["ready_for_manual_review"] is True
    assert manifest["human_filing_handoff_pack"]["readiness"]["ready_for_manual_upload"] is True
    assert manifest["accounting_evidence_authoring"]["summary"]["draft_count"] == 4
    assert manifest["uk_accounting_requirements_brain"]["summary"]["question_count"] == 8
    assert manifest["cognitive_review"]["status"] == "completed"
    assert manifest["cognitive_review"]["answer_source"] == "fake"
    assert all(task["status"] == "completed" for task in manifest["agent_tasks"])
    assert any(task["agent"] == "human_filing_handoff_agent" for task in manifest["agent_tasks"])
    assert any(task["agent"] == "evidence_authoring_agent" for task in manifest["agent_tasks"])
    assert any(task["agent"] == "uk_requirements_brain_agent" for task in manifest["agent_tasks"])
    assert Path(manifest["manifest_path"]).exists()
    assert (tmp_path / "vault" / "accounting" / "workflows" / "NI000001_2024-05-01_to_2025-04-30.md").exists()
    assert any(event["topic"] == "accounting.raw_data.ingested" for event in bus.events)
    assert any(event["topic"] == "accounting.vault.memory.written" for event in bus.events)
    assert any(event["topic"] == "accounting.autonomous.accounts.completed" for event in bus.events)
