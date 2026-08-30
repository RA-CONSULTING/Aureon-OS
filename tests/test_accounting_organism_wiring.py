from pathlib import Path

from aureon.core.aureon_organism_spine import build_organism_manifest
from aureon.core.integrated_cognitive_system import IntegratedCognitiveSystem
from aureon.queen.accounting_context_bridge import AccountingContextBridge
from aureon.queen.meaning_resolver import MeaningResolver

REPO_ROOT = Path(__file__).resolve().parents[1]


class FakeVault:
    def __init__(self):
        self.cards = []

    def ingest(self, topic, payload, category=None):
        self.cards.append({"topic": topic, "payload": payload, "category": category})
        return self.cards[-1]


class FakeBus:
    def __init__(self):
        self.events = []

    def publish(self, topic, payload=None, source=""):
        self.events.append({"topic": topic, "payload": payload or {}, "source": source})


class FakeAccountingBridge:
    def __init__(self):
        self.ingests = 0
        self.builds = 0
        self.statutory_builds = 0
        self.autonomous_builds = 0

    def status(self, force=False):
        return {
            "available": True,
            "company_number": "00000000",
            "company_name": "EXAMPLE TRADING LTD",
            "company_status": "Active - Active proposal to strike off",
            "period_start": "2024-05-01",
            "period_end": "2025-04-30",
            "generated_at": "2026-05-08T17:27:46+00:00",
            "accounts_build_status": "completed",
            "overdue_count": 3,
            "bank_evidence_complete": True,
            "manual_filing_required": True,
            "missing_outputs": [],
            "outputs": {
                "accounts_pack_pdf": {"path": "pack.pdf", "exists": True},
                "hmrc_ct600_draft_json": {"path": "ct600.json", "exists": True},
            },
            "statutory_filing_pack": {
                "generated_at": "2026-05-08T17:30:00+00:00",
                "figures": {
                    "turnover": "100.00",
                    "expenses": "90.00",
                    "profit_before_tax": "10.00",
                    "corporation_tax": "1.90",
                },
                "outputs": {
                    "companies_house_accounts_pdf": {"path": "accounts.pdf", "exists": True},
                    "hmrc_ct600_draft_json": {"path": "ct600.json", "exists": True},
                    "hmrc_tax_computation_pdf": {"path": "tax.pdf", "exists": True},
                    "ixbrl_readiness_note": {"path": "ixbrl.md", "exists": True},
                    "filing_checklist": {"path": "checklist.md", "exists": True},
                },
            },
            "accounting_readiness": self.validate_accounting_readiness(),
            "raw_data_manifest": {
                "summary": {
                    "file_count": 9,
                    "transaction_source_count": 3,
                    "evidence_only_count": 6,
                    "provider_counts": {"revolut": 1, "zempler": 1, "sumup": 1},
                }
            },
            "autonomous_workflow": {
                "status": "completed",
                "agent_tasks": [
                    {"agent": "raw_data_intake_agent", "status": "completed"},
                    {"agent": "human_filing_handoff_agent", "status": "completed"},
                ],
                "vault_memory": {"status": "written", "note_path": "accounting/workflows/test.md"},
                "cognitive_review": {
                    "status": "completed",
                    "answer_source": "fake",
                    "note_path": "autonomy/cycles/test.md",
                },
                "human_filing_handoff_pack": {
                    "status": "completed",
                    "output_dir": "handoff",
                    "readiness": {"ready_for_manual_review": True, "manual_inputs_required_count": 9},
                    "accounting_evidence_authoring": {
                        "status": "completed",
                        "summary": {"draft_count": 4, "generated_document_count": 4, "petty_cash_withdrawal_count": 1},
                        "outputs": {"accounting_evidence_authoring_manifest": "evidence.json"},
                    },
                    "uk_accounting_requirements_brain": {
                        "status": "ready_for_manual_review",
                        "summary": {"requirement_count": 7, "question_count": 8, "unresolved_question_count": 3},
                        "figures": {"turnover_over_vat_threshold": True, "vat_registration_threshold": "90000.00"},
                    },
                },
                "uk_accounting_requirements_brain": {
                    "status": "ready_for_manual_review",
                    "summary": {"requirement_count": 7, "question_count": 8, "unresolved_question_count": 3},
                    "figures": {"turnover_over_vat_threshold": True, "vat_registration_threshold": "90000.00"},
                },
                "accounting_evidence_authoring": {
                    "status": "completed",
                    "summary": {"draft_count": 4, "generated_document_count": 4, "petty_cash_withdrawal_count": 1},
                    "outputs": {"accounting_evidence_authoring_manifest": "evidence.json"},
                },
            },
            "human_filing_handoff_pack": {
                "status": "completed",
                "output_dir": "handoff",
                "readiness": {"ready_for_manual_review": True, "manual_inputs_required_count": 9},
                "accounting_evidence_authoring": {
                    "status": "completed",
                    "summary": {"draft_count": 4, "generated_document_count": 4, "petty_cash_withdrawal_count": 1},
                    "outputs": {"accounting_evidence_authoring_manifest": "evidence.json"},
                },
                "uk_accounting_requirements_brain": {
                    "status": "ready_for_manual_review",
                    "summary": {"requirement_count": 7, "question_count": 8, "unresolved_question_count": 3},
                    "figures": {"turnover_over_vat_threshold": True, "vat_registration_threshold": "90000.00"},
                },
            },
            "uk_accounting_requirements_brain": {
                "status": "ready_for_manual_review",
                "summary": {"requirement_count": 7, "question_count": 8, "unresolved_question_count": 3},
                "figures": {"turnover_over_vat_threshold": True, "vat_registration_threshold": "90000.00"},
            },
            "accounting_evidence_authoring": {
                "status": "completed",
                "summary": {"draft_count": 4, "generated_document_count": 4, "petty_cash_withdrawal_count": 1},
                "outputs": {"accounting_evidence_authoring_manifest": "evidence.json"},
            },
            "combined_bank_data": {
                "csv_source_count": 4,
                "transaction_source_count": 6,
                "unique_rows_in_period": 22,
                "duplicate_rows_removed": 44,
            },
            "accounting_system_registry": {
                "module_count": 32,
                "artifact_count": 30,
                "runnable_tool_count": 12,
                "domain_counts": {"gateway_orchestration": 2, "ledger_double_entry": 2},
            },
            "quickbooks": {
                "connection_state": "qbo_ui_connected_api_pending",
                "api": {"oauth": "not_verified", "company_info_readback": "not_verified"},
                "bank_feed": {
                    "connected": True,
                    "provider": "Zempler Bank (UK)",
                    "pending_transaction_count": 911,
                    "ownership_status": "mixed_use_owner_accountant_review_required",
                    "aureon_posted_transaction_count": 0,
                    "bulk_posting_allowed": False,
                },
                "chart_of_accounts": {"account_count": 58, "staged_changes_applied": False},
                "controls": {"quickbooks_mutations": "disabled"},
            },
            "aureon_accounting_control": {
                "authority": {
                    "canonical_system": "aureon_os",
                    "quickbooks_role": "downstream_projection_and_readback",
                    "quickbooks_may_create_or_mutate_canonical_entries": False,
                },
                "journal": {
                    "integrity_verified": True,
                    "entry_count": 4,
                    "approved_entry_count": 3,
                },
                "quickbooks_projection": {
                    "queued_count": 2,
                    "readback_verified_count": 1,
                    "outstanding_readback_count": 1,
                    "observation_task_count": 911,
                },
            },
            "accounting_reconciliation": {
                "summary": {
                    "workstream_count": 13,
                    "critical_workstream_count": 3,
                    "posting_authorised_count": 0,
                    "quickbooks_projection_authorised_count": 0,
                    "external_compliance_action_authorised_count": 0,
                },
                "workstreams": [
                    {
                        "id": "corporation_tax",
                        "state": "urgent_resolution_required",
                        "priority": "critical",
                        "next_action": "Obtain live HMRC periods with the accountant.",
                    }
                ],
            },
        }

    def load_context(self):
        return {
            "schema_version": "accounting-context-v2",
            "company": {
                "company_number": "00000000",
                "company_name": "EXAMPLE TRADING LTD",
                "company_status": "Active - Active proposal to strike off",
            },
            "full_run": {
                "period_start": "2024-05-01",
                "period_end": "2025-04-30",
                "accounts_build_status": "completed",
            },
            "deadlines": {"overdue_count": 3},
            "safety": {"manual_filing_required": True},
            "combined_bank_data": {"csv_source_count": 4, "unique_rows_in_period": 22},
            "accounting_system_registry": {"module_count": 32, "domain_counts": {"ledger_double_entry": 2}},
            "accounting_evidence_authoring": {
                "status": "completed",
                "summary": {"draft_count": 4, "generated_document_count": 4, "petty_cash_withdrawal_count": 1},
                "outputs": {"accounting_evidence_authoring_manifest": "evidence.json"},
            },
            "uk_accounting_requirements_brain": {
                "status": "ready_for_manual_review",
                "summary": {"requirement_count": 7, "question_count": 8, "unresolved_question_count": 3},
                "figures": {"turnover_over_vat_threshold": True, "vat_registration_threshold": "90000.00"},
            },
            "prompt_lines": ["Manual filing required; draft accounts only."],
        }

    def render_for_prompt(self, context, max_chars=760):
        return "Accounting context: Manual filing required; draft accounts only."

    def ingest_to_vault(self, vault, force=False):
        self.ingests += 1
        if vault is not None:
            vault.ingest("accounting.context.summary", {"ok": True}, category="accounting_summary")
        return 1

    def publish_status(self, bus, topic="accounting.status"):
        st = self.status()
        if bus is not None:
            bus.publish(topic, st, source="fake_accounting")
        return st

    def validate_accounting_readiness(self, context=None, force=False):
        return {
            "schema_version": "accounting-readiness-v1",
            "ready": True,
            "ready_for": "draft_accounts_and_manual_filing_review",
            "required_failures": [],
            "optional_failures": [],
            "checks": [
                {"name": "combined_bank_data", "ok": True, "required": True, "detail": "ok"},
                {"name": "statutory_output:hmrc_ct600_draft_json", "ok": True, "required": True, "detail": "ct600.json"},
            ],
            "bank_sources": 6,
            "unique_bank_rows": 22,
            "statutory_outputs": 5,
            "raw_file_count": 9,
            "manual_filing_required": True,
        }

    def run_full_accounts(self, no_fetch=True):
        self.builds += 1
        return {
            "status": "completed",
            "exit_code": 0,
            "summary": self.status(),
            "safety": {"manual_filing_required": True},
        }

    def run_statutory_filing_pack(self):
        self.statutory_builds += 1
        return {
            "status": "completed",
            "exit_code": 0,
            "summary": self.status(),
            "readiness": self.validate_accounting_readiness(),
            "safety": {"manual_filing_required": True},
        }

    def run_autonomous_full_accounts(self, **kwargs):
        self.autonomous_builds += 1
        return {
            "status": "completed",
            "exit_code": 0,
            "summary": self.status(),
            "readiness": self.validate_accounting_readiness(),
            "safety": {"manual_filing_required": True},
        }


def test_accounting_context_bridge_loads_generated_artifacts_and_publishes_status():
    bridge = AccountingContextBridge(repo_root=REPO_ROOT)
    context = bridge.load_context(force=True)

    assert context["schema_version"] == "accounting-context-v2"
    assert context["company"]["company_number"] == "00000000"
    assert context["full_run"]["accounts_build_status"] in {"completed", "unknown"}
    assert context["safety"]["submits_to_companies_house"] is False
    assert context["safety"]["submits_to_hmrc"] is False
    assert context["safety"]["manual_filing_required"] is True
    combined = context["combined_bank_data"]
    if combined.get("csv_source_count") is not None:
        # counts only exist when the personal statement corpus / generated
        # period manifest is present on this machine
        assert combined["csv_source_count"] >= 0
    assert context["accounting_system_registry"]["module_count"] >= 25
    vault_memory = context["accounting_vault_memory"]
    vault_available = bool(vault_memory["index_exists"] or vault_memory["workflow_count"])
    assert context["accounting_system_registry"]["nonstandard_surfaces"]["accounting_vault_memory"] is vault_available
    assert vault_memory["status"] == ("ready" if vault_available else "missing")
    readiness = bridge.validate_accounting_readiness(context)
    # Full readiness requires the operator's personal statement corpus and the
    # generated final-ready outputs, which are deliberately not committed. The
    # honest contract without them is ready=False with the data-dependent
    # checks named — never a pretend "ready".
    corpus_present = REPO_ROOT.joinpath("uploads").exists() or REPO_ROOT.joinpath("bussiness accounts").exists()
    if corpus_present:
        assert readiness["ready"] is True
    else:
        assert readiness["ready"] is False
        failing = {item["name"] for item in readiness["checks"] if not item.get("ok")}
        assert "combined_bank_data" in failing  # named, not silent
    assert readiness["manual_filing_required"] is True
    assert any(item["name"] == "sumup_sales_flow" for item in readiness["checks"])
    assert any(item["name"] == "accounting_vault_memory" for item in readiness["checks"])
    assert context["statutory_filing_pack"]["schema_version"] == "statutory-filing-pack-v1"

    rendered = bridge.render_for_prompt(context, max_chars=1400)
    assert "Accounting context" in rendered
    assert "manual" in rendered.lower()
    assert "Accounting tools unified" in rendered
    assert "Accounting vault memory" in rendered

    vault = FakeVault()
    assert bridge.ingest_to_vault(vault, force=True) >= 1
    assert any(card["topic"] == "accounting.context.summary" for card in vault.cards)
    assert any(card["topic"] == "accounting.vault.memory.ready" for card in vault.cards)

    bus = FakeBus()
    status = bridge.publish_status(bus)
    assert status["manual_filing_required"] is True
    assert bus.events[-1]["topic"] == "accounting.status"


def test_accounting_context_bridge_reads_aureon_canonical_journal_status(tmp_path: Path):
    status_path = (
        tmp_path
        / "Kings_Accounting_Suite"
        / "output"
        / "accounting_control"
        / "status.json"
    )
    status_path.parent.mkdir(parents=True)
    status_path.write_text(
        """{
  "schema_version": "aureon-accounting-control-status-v1",
  "authority": {
    "canonical_system": "aureon_os",
    "quickbooks_role": "downstream_projection_and_readback",
    "quickbooks_may_create_or_mutate_canonical_entries": false
  },
  "journal": {
    "integrity_verified": true,
    "entry_count": 7,
    "approved_entry_count": 5
  },
  "quickbooks_projection": {
    "queued_count": 3,
    "readback_verified_count": 2,
    "outstanding_readback_count": 1,
    "observation_task_count": 4
  }
}
""",
        encoding="utf-8",
    )
    (status_path.parent / "reconciliation_status.json").write_text(
        """{
  "schema_version": "aureon-accounting-reconciliation-v1",
  "summary": {
    "workstream_count": 13,
    "critical_workstream_count": 3,
    "posting_authorised_count": 0,
    "external_compliance_action_authorised_count": 0
  },
  "workstreams": [
    {"id": "corporation_tax", "priority": "critical", "state": "resolution_required"}
  ]
}
""",
        encoding="utf-8",
    )
    bridge = AccountingContextBridge(repo_root=tmp_path, company_number="00000000")

    context = bridge.load_context(force=True)
    control = context["aureon_accounting_control"]
    assert control["authority"]["canonical_system"] == "aureon_os"
    assert control["journal"]["entry_count"] == 7
    assert control["quickbooks_projection"]["outstanding_readback_count"] == 1
    assert context["accounting_reconciliation"]["summary"]["workstream_count"] == 13
    readiness = bridge.validate_accounting_readiness(context)
    canonical_check = next(
        check for check in readiness["checks"] if check["name"] == "aureon_canonical_accounting_journal"
    )
    assert canonical_check["ok"] is True
    reconciliation_check = next(
        check for check in readiness["checks"] if check["name"] == "aureon_accounting_reconciliation"
    )
    assert reconciliation_check["ok"] is True
    assert "Aureon canonical journal:" in bridge.render_for_prompt(context, max_chars=10000)
    assert "Aureon accounting reconciliation:" in bridge.render_for_prompt(context, max_chars=10000)


def test_meaning_resolver_injects_accounting_context_for_tax_questions():
    fake = FakeAccountingBridge()
    resolver = MeaningResolver(accounting_bridge=fake)
    resolver._wired = True

    block = resolver.resolve("What do the company accounts and HMRC tax filings need?")

    assert block.accounting is not None
    assert block.accounting_text
    assert "accounting" in block.sources_consulted
    facts = block.to_fact_dict()
    assert facts["accounting"]["company_number"] == "00000000"
    assert facts["accounting"]["manual_filing_required"] is True


def test_integrated_cognitive_system_accounts_commands_use_safe_bridge():
    ics = IntegratedCognitiveSystem()
    ics.accounting_context = FakeAccountingBridge()
    ics.vault = FakeVault()
    ics.thought_bus = FakeBus()

    status = ics.process_user_input("/accounts status")
    assert "ACCOUNTING STATUS" in status
    assert "Manual filing required: True" in status
    assert "Accounting tools: 32 modules/tools" in status
    assert "Human filing handoff:" in status
    assert "Evidence authoring:" in status
    assert "UK accounting requirements brain:" in status
    assert "Accounting mind:" in status
    assert "QuickBooks:" in status
    assert "Aureon journal:" in status
    assert "Reconciliation:" in status

    reconciliation = ics.process_user_input("/accounts reconciliation")
    assert "AUREON ACCOUNTING RECONCILIATION" in reconciliation
    assert "corporation_tax: urgent_resolution_required" in reconciliation
    assert "postings_authorised=0" in reconciliation

    quickbooks = ics.process_user_input("/accounts quickbooks")
    assert "QUICKBOOKS CONTROL PLANE" in quickbooks
    assert "pending=911" in quickbooks
    assert "bulk_allowed=False" in quickbooks
    assert "Aureon journal: integrity=True entries=4 approved=3" in quickbooks
    assert "Projection queue: queued=2 readback=1 outstanding=1 observations=911" in quickbooks

    tools = ics.process_user_input("/accounts tools")
    assert "ACCOUNTING TOOL REGISTRY" in tools
    assert "ledger_double_entry" in tools

    ingest = ics.process_user_input("/accounts ingest")
    assert "ingested into vault" in ingest
    assert ics.accounting_context.ingests >= 1

    raw = ics.process_user_input("/accounts raw")
    assert "ACCOUNTING RAW DATA INTAKE" in raw
    assert "Files:   9" in raw

    readiness = ics.process_user_input("/accounts readiness")
    assert "ACCOUNTING READINESS" in readiness
    assert "Ready: True" in readiness
    assert any(event["topic"] == "accounting.readiness" for event in ics.thought_bus.events)

    requirements = ics.process_user_input("/accounts requirements")
    assert "UK ACCOUNTING REQUIREMENTS BRAIN" in requirements
    assert "Accountant self-questions: 8" in requirements

    evidence = ics.process_user_input("/accounts evidence")
    assert "ACCOUNTING EVIDENCE AUTHORING" in evidence
    assert "Evidence requests: 4" in evidence

    filing = ics.process_user_input("/accounts filing")
    assert "ACCOUNTING STATUTORY/HMRC PACK" in filing
    assert "ct600.json" in filing

    statutory_build = ics.process_user_input("/accounts statutory build")
    assert "statutory filing-support build completed" in statutory_build
    assert ics.accounting_context.statutory_builds == 1
    assert any(event["topic"] == "accounting.statutory.generated" for event in ics.thought_bus.events)

    autonomous = ics.process_user_input("/accounts autonomous")
    assert "autonomous full-accounts workflow completed" in autonomous
    assert "handoff_ready=True" in autonomous
    assert "self_questioning=completed" in autonomous
    assert ics.accounting_context.autonomous_builds == 1
    assert any(event["topic"] == "accounting.autonomous.accounts.completed" for event in ics.thought_bus.events)

    build = ics.process_user_input("/accounts build")
    assert "Accounting build completed" in build
    assert ics.accounting_context.builds == 1
    assert any(event["topic"] == "accounting.accounts.generated" for event in ics.thought_bus.events)


def test_organism_spine_registers_accounting_suite_modules():
    manifest = build_organism_manifest(repo_root=REPO_ROOT)
    modules = manifest.by_module()

    assert "aureon.queen.accounting_context_bridge" in modules
    assert "Kings_Accounting_Suite.tools.generate_full_company_accounts" in modules
    assert modules["Kings_Accounting_Suite.tools.generate_full_company_accounts"].domain == "accounting"
