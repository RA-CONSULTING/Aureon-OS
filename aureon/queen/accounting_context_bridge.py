"""
AccountingContextBridge - wire accounting artifacts into Aureon's organism.

The accounting suite writes final-ready manual filing packs, compliance audits,
gateway manifests, bank evidence inventories, and legacy HMRC filing packs. This
bridge is the single safe interface used by Queen prompts, the vault,
ThoughtBus, ignition, self-questioning, and audits.

Default behavior is read-only. It never files with Companies House, never submits
to HMRC, never pays tax or penalties, and never mutates exchange state. The only
mutating operation is the explicit on-demand final-ready pack builder.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import subprocess
import sys
import threading
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger("aureon.queen.accounting_context_bridge")

DEFAULT_COMPANY_NUMBER = "00000000"
DEFAULT_PERIOD_START = "2024-05-01"
DEFAULT_PERIOD_END = "2025-04-30"
FINAL_READY_ACCOUNTING_STATUS = "final_ready_manual_upload_required"

ACCOUNTING_TOPICS = (
    "accounting.context.ready",
    "accounting.status",
    "accounting.system_registry.ready",
    "accounting.canonical_journal.status",
    "accounting.reconciliation.status",
    "accounting.quickbooks.status",
    "accounting.quickbooks.projection.queued",
    "accounting.quickbooks.projection.readback",
    "accounting.quickbooks.webhook.verified",
    "accounting.quickbooks.refresh.requested",
    "accounting.data.combined",
    "accounting.accounts.generated",
    "accounting.accounts.blocked",
    "accounting.statutory.generated",
    "accounting.statutory.blocked",
    "accounting.readiness",
    "accounting.raw_data.ingested",
    "accounting.raw_data.swarm_scan.ready",
    "accounting.logic_chain.ready",
    "accounting.end_user_confirmation.ready",
    "accounting.autonomous.accounts.started",
    "accounting.vault.memory.ready",
    "accounting.vault.memory.written",
    "accounting.cognitive.review.started",
    "accounting.cognitive.review.completed",
    "accounting.cognitive.review.blocked",
    "accounting.evidence.authoring.ready",
    "accounting.uk_requirements.ready",
    "accounting.handoff.generated",
    "accounting.handoff.blocked",
    "accounting.autonomous.accounts.completed",
    "accounting.autonomous.accounts.blocked",
    "accounting.agent.task",
)


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _clip(value: Any, limit: int = 240) -> str:
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


class AccountingContextBridge:
    """Load, cache, publish, and vault-ingest local accounting context."""

    def __init__(
        self,
        repo_root: str | Path | None = None,
        *,
        company_number: str = DEFAULT_COMPANY_NUMBER,
        period_start: str = DEFAULT_PERIOD_START,
        period_end: str = DEFAULT_PERIOD_END,
    ):
        self.repo_root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[2]
        self.company_number = company_number
        self.period_start = period_start
        self.period_end = period_end
        self._lock = threading.RLock()
        self._cached_context: Dict[str, Any] = {}
        self._cached_signature: Tuple[Tuple[str, float, int], ...] = ()
        self._last_vault_signature: str = ""

    def _paths(self) -> Dict[str, Path]:
        company_dir = (
            self.repo_root
            / "Kings_Accounting_Suite"
            / "output"
            / "company_compliance"
            / self.company_number
        )
        period_dir = (
            self.repo_root
            / "Kings_Accounting_Suite"
            / "output"
            / "gateway"
            / f"{self.period_start}_to_{self.period_end}"
        )
        statutory_dir = (
            self.repo_root
            / "Kings_Accounting_Suite"
            / "output"
            / "statutory"
            / self.company_number
            / f"{self.period_start}_to_{self.period_end}"
        )
        raw_data_dir = (
            self.repo_root
            / "Kings_Accounting_Suite"
            / "output"
            / "company_raw_data"
            / self.company_number
            / f"{self.period_start}_to_{self.period_end}"
        )
        handoff_dir = (
            self.repo_root
            / "Kings_Accounting_Suite"
            / "output"
            / "filing_handoff"
            / self.company_number
            / f"{self.period_start}_to_{self.period_end}"
        )
        end_user_dir = (
            self.repo_root
            / "Kings_Accounting_Suite"
            / "output"
            / "end_user_accounts"
            / self.company_number
            / f"{self.period_start}_to_{self.period_end}"
        )
        return {
            "accounting_suite": self.repo_root / "Kings_Accounting_Suite",
            "full_run_manifest": company_dir / "full_company_accounts_run_manifest.json",
            "full_run_summary": company_dir / "full_company_accounts_run_summary.md",
            "autonomous_workflow_manifest": company_dir / "autonomous_full_accounts_workflow_manifest.json",
            "autonomous_workflow_summary": company_dir / "autonomous_full_accounts_workflow_summary.md",
            "compliance_audit_json": company_dir / "company_house_tax_audit.json",
            "compliance_audit_markdown": company_dir / "company_house_tax_audit.md",
            "period_manifest": period_dir / "period_pack_manifest.json",
            "combined_bank_transactions": period_dir / f"combined_bank_transactions_{self.period_start}_to_{self.period_end}.csv",
            "accounting_system_registry_json": self.repo_root / "docs" / "audits" / "accounting_system_registry.json",
            "accounting_system_registry_markdown": self.repo_root / "docs" / "audits" / "accounting_system_registry.md",
            "quickbooks_status": self.repo_root / "Kings_Accounting_Suite" / "output" / "quickbooks" / "status.json",
            "quickbooks_audit_dir": self.repo_root / "Kings_Accounting_Suite" / "output" / "quickbooks" / "audit",
            "quickbooks_control_plane": self.repo_root / "Kings_Accounting_Suite" / "tools" / "quickbooks_accounting_integration.py",
            "aureon_accounting_control_status": self.repo_root / "Kings_Accounting_Suite" / "output" / "accounting_control" / "status.json",
            "aureon_accounting_control_plane": self.repo_root / "Kings_Accounting_Suite" / "tools" / "aureon_accounting_control_plane.py",
            "aureon_accounting_reconciliation_status": self.repo_root / "Kings_Accounting_Suite" / "output" / "accounting_control" / "reconciliation_status.json",
            "aureon_accounting_reconciliation": self.repo_root / "Kings_Accounting_Suite" / "tools" / "aureon_accounting_reconciliation.py",
            "accounting_vault_index": self.repo_root / "accounting" / "full_accounts_index.md",
            "accounting_vault_workflows_dir": self.repo_root / "accounting" / "workflows",
            "accounts_pack_pdf": period_dir / f"ra_consulting_and_brokerage_accounts_pack_{self.period_start}_to_{self.period_end}.pdf",
            "management_accounts": period_dir / "management_accounts.xlsx",
            "general_ledger": period_dir / "general_ledger.xlsx",
            "trial_balance": period_dir / "trial_balance.xlsx",
            "profit_and_loss": period_dir / "pnl.pdf",
            "tax_summary": period_dir / "tax_summary.pdf",
            "statutory_manifest": statutory_dir / "statutory_filing_pack_manifest.json",
            "raw_data_manifest": raw_data_dir / "raw_data_manifest.json",
            "raw_data_manifest_markdown": raw_data_dir / "raw_data_manifest.md",
            "handoff_manifest": handoff_dir / "filing_handoff_manifest.json",
            "handoff_index": handoff_dir / "filing_handoff_index.md",
            "handoff_start_here": handoff_dir / "00_start_here" / "START_HERE.md",
            "end_user_accounting_automation_manifest": end_user_dir / "end_user_accounting_automation_manifest.json",
            "end_user_accounting_automation_start_here": end_user_dir / "END_USER_START_HERE.md",
            "end_user_confirmation_json": end_user_dir / "END_USER_CONFIRMATION.json",
            "end_user_confirmation_markdown": end_user_dir / "END_USER_CONFIRMATION.md",
            "internal_logic_chain_checklist_json": end_user_dir / "internal_logic_chain_checklist.json",
            "internal_logic_chain_checklist_markdown": end_user_dir / "internal_logic_chain_checklist.md",
            "swarm_raw_data_wave_scan_json": end_user_dir / "swarm_raw_data_wave_scan.json",
            "swarm_raw_data_wave_scan_markdown": end_user_dir / "swarm_raw_data_wave_scan.md",
            "accounting_evidence_authoring_manifest": handoff_dir / "07_review_workpapers" / "evidence_authoring" / "evidence_authoring_manifest.json",
            "accounting_evidence_authoring_summary": handoff_dir / "07_review_workpapers" / "evidence_authoring" / "evidence_authoring_summary.md",
            "accounting_evidence_requests_csv": handoff_dir / "07_review_workpapers" / "evidence_authoring" / "evidence_requests.csv",
            "uk_accounting_requirements_brain_json": handoff_dir / "07_review_workpapers" / "uk_accounting_requirements_brain.json",
            "uk_accounting_requirements_brain_markdown": handoff_dir / "07_review_workpapers" / "uk_accounting_requirements_brain.md",
            "accountant_self_questions_markdown": handoff_dir / "00_start_here" / "accountant_self_questions.md",
            "companies_house_accounts_final_ready_markdown": statutory_dir / "companies_house_accounts_final_ready.md",
            "companies_house_accounts_final_ready_pdf": statutory_dir / "companies_house_accounts_final_ready.pdf",
            "directors_report_final_ready_markdown": statutory_dir / "directors_report_final_ready.md",
            "directors_report_final_ready_pdf": statutory_dir / "directors_report_final_ready.pdf",
            "audit_exemption_statement_final_ready_markdown": statutory_dir / "audit_exemption_statement_final_ready.md",
            "hmrc_tax_computation_final_ready_markdown": statutory_dir / "hmrc_tax_computation_final_ready.md",
            "hmrc_tax_computation_final_ready_pdf": statutory_dir / "hmrc_tax_computation_final_ready.pdf",
            "ct600_manual_entry_json": statutory_dir / "hmrc_ct600_manual_entry.json",
            "ct600_box_map_final_ready_markdown": statutory_dir / "ct600_box_map_final_ready.md",
            "companies_house_accounts_markdown": statutory_dir / "companies_house_accounts_draft.md",
            "companies_house_accounts_pdf": statutory_dir / "companies_house_accounts_draft.pdf",
            "directors_report_markdown": statutory_dir / "directors_report_draft.md",
            "directors_report_pdf": statutory_dir / "directors_report_draft.pdf",
            "audit_exemption_statement_markdown": statutory_dir / "audit_exemption_statement_draft.md",
            "hmrc_tax_computation_markdown": statutory_dir / "hmrc_tax_computation_draft.md",
            "hmrc_tax_computation_pdf": statutory_dir / "hmrc_tax_computation_draft.pdf",
            "hmrc_ct600_draft_json": statutory_dir / "hmrc_ct600_draft.json",
            "ct600_box_map_markdown": statutory_dir / "ct600_box_map_draft.md",
            "supplementary_pages_review_json": statutory_dir / "ct600_supplementary_pages_review.json",
            "confirmation_statement_readiness_json": statutory_dir / "confirmation_statement_readiness.json",
            "confirmation_statement_readiness_markdown": statutory_dir / "confirmation_statement_readiness.md",
            "accounts_readable_for_ixbrl_html": statutory_dir / "accounts_readable_for_ixbrl.html",
            "computation_readable_for_ixbrl_html": statutory_dir / "computation_readable_for_ixbrl.html",
            "draft_accounts_html": statutory_dir / "draft_accounts_readable_not_ixbrl.html",
            "draft_computation_html": statutory_dir / "draft_computation_readable_not_ixbrl.html",
            "ixbrl_readiness_note": statutory_dir / "ixbrl_readiness_note.md",
            "government_requirements_matrix_json": statutory_dir / "government_filing_requirements_matrix.json",
            "government_requirements_matrix_markdown": statutory_dir / "government_filing_requirements_matrix.md",
            "filing_checklist": statutory_dir / "filing_checklist.md",
            "filing_pack": self.repo_root / "Kings_Accounting_Suite" / "output" / "final" / "hmrc_filing_pack_2024_2025.json",
            "gateway_summary": self.repo_root / "Kings_Accounting_Suite" / "output" / "gateway" / "filling_prep_summary_2024_2025.json",
            "exchange_coverage": self.repo_root / "data" / "exchange_account_archives" / "latest" / "coverage_report.json",
            "year_2024_25_csv": self.repo_root / "uploads" / "Statement_06_Apr_2024_05_Apr_2025.csv",
            "year_2025_26_csv": self.repo_root / "uploads" / "Statement_06_Apr_2025_05_Apr_2026.csv",
            "full_period_csv": self.repo_root / "uploads" / "Statement_31_Aug_2024_10_Apr_2026.csv",
            "business_accounts_dir": self.repo_root / "bussiness accounts",
            "accounts_generator": self.repo_root / "Kings_Accounting_Suite" / "tools" / "generate_full_company_accounts.py",
            "statutory_generator": self.repo_root / "Kings_Accounting_Suite" / "tools" / "generate_statutory_filing_pack.py",
            "autonomous_workflow_runner": self.repo_root / "Kings_Accounting_Suite" / "tools" / "autonomous_full_accounts_workflow.py",
            "end_user_accounting_automation_runner": self.repo_root / "Kings_Accounting_Suite" / "tools" / "end_user_accounting_automation.py",
            "handoff_pack_runner": self.repo_root / "Kings_Accounting_Suite" / "tools" / "accounting_handoff_pack.py",
            "accounting_evidence_authoring_runner": self.repo_root / "Kings_Accounting_Suite" / "tools" / "accounting_evidence_authoring.py",
            "uk_accounting_requirements_brain_runner": self.repo_root / "Kings_Accounting_Suite" / "tools" / "uk_accounting_requirements_brain.py",
        }

    @staticmethod
    def _signature_for(paths: Dict[str, Path]) -> Tuple[Tuple[str, float, int], ...]:
        parts: List[Tuple[str, float, int]] = []
        for key, path in sorted(paths.items()):
            try:
                if path.is_dir():
                    files = [p for p in path.iterdir() if p.is_file()]
                    latest = max((p.stat().st_mtime for p in files), default=path.stat().st_mtime)
                    total = sum(p.stat().st_size for p in files)
                    parts.append((key, float(latest), int(total)))
                    continue
                if path.exists():
                    st = path.stat()
                    parts.append((key, float(st.st_mtime), int(st.st_size)))
                else:
                    parts.append((key, -1.0, -1))
            except Exception:
                parts.append((key, -1.0, -1))
        return tuple(parts)

    @staticmethod
    def _read_json(path: Path) -> Dict[str, Any]:
        try:
            if not path.exists():
                return {}
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.debug("accounting bridge json read failed %s: %s", path, exc)
            return {}

    @staticmethod
    def _read_text(path: Path, limit: int = 4000) -> str:
        try:
            if not path.exists():
                return ""
            return path.read_text(encoding="utf-8", errors="replace")[:limit]
        except Exception:
            return ""

    @staticmethod
    def _fallback_accounting_evidence_authoring(paths: Dict[str, Path]) -> Dict[str, Any]:
        runner = paths.get("accounting_evidence_authoring_runner")
        manifest = paths.get("accounting_evidence_authoring_manifest")
        if runner is None or not runner.exists():
            return {}
        return {
            "status": "capability_ready_no_private_pack",
            "summary": {
                "draft_count": 1,
                "generated_document_count": 0,
                "petty_cash_withdrawal_count": 0,
                "llm_document_authoring": {
                    "status": "not_run",
                    "completed_count": 0,
                },
            },
            "outputs": {
                "accounting_evidence_authoring_manifest": str(manifest) if manifest is not None else "",
            },
            "manual_filing_required": True,
            "source": "public_runner_available_generated_pack_not_committed",
        }

    @staticmethod
    def _fallback_uk_accounting_requirements_brain(paths: Dict[str, Path]) -> Dict[str, Any]:
        runner = paths.get("uk_accounting_requirements_brain_runner")
        output = paths.get("uk_accounting_requirements_brain_json")
        if runner is None or not runner.exists():
            return {}
        return {
            "status": "capability_ready_no_private_pack",
            "summary": {
                "requirement_count": 5,
                "question_count": 8,
                "unresolved_question_count": 8,
            },
            "figures": {
                "turnover_over_vat_threshold": "review_required",
                "vat_registration_threshold": "90000.00",
            },
            "outputs": {
                "uk_accounting_requirements_brain_json": str(output) if output is not None else "",
            },
            "manual_filing_required": True,
            "source": "public_runner_available_generated_pack_not_committed",
        }

    def _fallback_statutory_filing_pack(self, paths: Dict[str, Path]) -> Dict[str, Any]:
        runner = paths.get("statutory_generator")
        manifest = paths.get("statutory_manifest")
        if runner is None or not runner.exists():
            return {}
        return {
            "schema_version": "statutory-filing-pack-v1",
            "status": "capability_ready_no_private_pack",
            "company_number": self.company_number,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "generated_at": "",
            "manual_filing_required": True,
            "outputs": {
                "statutory_generator": {"path": str(runner), "exists": True},
                "statutory_manifest": {
                    "path": str(manifest) if manifest is not None else "",
                    "exists": bool(manifest and manifest.exists()),
                },
            },
            "source": "public_runner_available_generated_pack_not_committed",
        }

    @staticmethod
    def _csv_rows(path: Path) -> int:
        try:
            if not path.exists():
                return 0
            with path.open("r", encoding="utf-8-sig", newline="") as fh:
                return max(0, sum(1 for _ in csv.reader(fh)) - 1)
        except Exception as exc:
            logger.debug("accounting bridge csv read failed %s: %s", path, exc)
            return 0

    @staticmethod
    def _dir_file_count(path: Path) -> int:
        try:
            if not path.exists() or not path.is_dir():
                return 0
            return sum(1 for item in path.iterdir() if item.is_file())
        except Exception:
            return 0

    def _accounting_vault_memory_status(self, paths: Dict[str, Path]) -> Dict[str, Any]:
        index_path = paths["accounting_vault_index"]
        workflows_dir = paths["accounting_vault_workflows_dir"]
        workflow_files: List[Path] = []
        try:
            if workflows_dir.exists() and workflows_dir.is_dir():
                workflow_files = sorted(workflows_dir.glob("*.md"), key=lambda item: item.name.lower())
        except Exception:
            workflow_files = []
        return {
            "index_exists": index_path.exists(),
            "index_path": str(index_path),
            "workflow_count": len(workflow_files),
            "workflow_paths": [str(path) for path in workflow_files[:12]],
            "index_excerpt": self._read_text(index_path, limit=900),
            "status": "ready" if index_path.exists() or workflow_files else "missing",
        }

    @staticmethod
    def _extract_year_metrics(year_blob: Dict[str, Any]) -> Dict[str, Any]:
        boxes = year_blob.get("sa103_boxes") or {}
        turnover = _to_float(boxes.get("9"))
        allowable = _to_float(boxes.get("21"))
        if allowable <= 0.0:
            allowable = sum(
                _to_float(boxes.get(str(i)))
                for i in (10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20)
            )
        profit = _to_float(boxes.get("22"))
        if abs(profit) < 1e-9 and turnover > 0.0:
            profit = turnover - allowable
        return {
            "turnover": round(turnover, 2),
            "allowable_expenses": round(allowable, 2),
            "net_profit": round(profit, 2),
            "filing_deadlines": year_blob.get("filing_deadlines") or {},
        }

    def _output_status(self, manifest: Dict[str, Any], paths: Dict[str, Path]) -> Dict[str, Any]:
        expected = (
            "accounts_pack_pdf",
            "management_accounts",
            "general_ledger",
            "trial_balance",
            "profit_and_loss",
            "tax_summary",
            "combined_bank_transactions",
            "period_manifest",
            "compliance_audit_json",
            "compliance_audit_markdown",
            "raw_data_manifest",
            "raw_data_manifest_markdown",
            "handoff_manifest",
            "handoff_index",
            "handoff_start_here",
            "autonomous_workflow_manifest",
            "autonomous_workflow_summary",
            "end_user_accounting_automation_manifest",
            "end_user_accounting_automation_start_here",
            "end_user_confirmation_json",
            "end_user_confirmation_markdown",
            "internal_logic_chain_checklist_json",
            "internal_logic_chain_checklist_markdown",
            "swarm_raw_data_wave_scan_json",
            "swarm_raw_data_wave_scan_markdown",
            "statutory_manifest",
            "companies_house_accounts_final_ready_markdown",
            "companies_house_accounts_final_ready_pdf",
            "directors_report_final_ready_markdown",
            "directors_report_final_ready_pdf",
            "audit_exemption_statement_final_ready_markdown",
            "hmrc_tax_computation_final_ready_markdown",
            "hmrc_tax_computation_final_ready_pdf",
            "ct600_manual_entry_json",
            "ct600_box_map_final_ready_markdown",
            "companies_house_accounts_markdown",
            "companies_house_accounts_pdf",
            "directors_report_markdown",
            "directors_report_pdf",
            "audit_exemption_statement_markdown",
            "hmrc_tax_computation_markdown",
            "hmrc_tax_computation_pdf",
            "hmrc_ct600_draft_json",
            "ct600_box_map_markdown",
            "supplementary_pages_review_json",
            "confirmation_statement_readiness_json",
            "confirmation_statement_readiness_markdown",
            "accounts_readable_for_ixbrl_html",
            "computation_readable_for_ixbrl_html",
            "draft_accounts_html",
            "draft_computation_html",
            "ixbrl_readiness_note",
            "government_requirements_matrix_json",
            "government_requirements_matrix_markdown",
            "filing_checklist",
        )
        outputs = manifest.get("outputs") or {}
        status: Dict[str, Any] = {}
        for key in expected:
            manifest_item = outputs.get(key) or {}
            path = Path(manifest_item.get("path") or paths.get(key, ""))
            exists = bool(manifest_item.get("exists")) if manifest_item else path.exists()
            status[key] = {
                "exists": exists,
                "path": str(path) if str(path) else "",
                "bytes": int(manifest_item.get("bytes") or (path.stat().st_size if path.exists() else 0)),
            }
        for key, manifest_item in outputs.items():
            if key in status or not isinstance(manifest_item, dict):
                continue
            path = Path(manifest_item.get("path") or "")
            status[key] = {
                "exists": bool(manifest_item.get("exists")) if manifest_item else path.exists(),
                "path": str(path) if str(path) else "",
                "bytes": int(manifest_item.get("bytes") or (path.stat().st_size if path.exists() else 0)),
            }
        return status

    def _accounting_registry_snapshot(self, source_inventory: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from Kings_Accounting_Suite.tools.accounting_system_registry import (
                build_accounting_system_registry,
            )

            registry = build_accounting_system_registry(
                self.repo_root,
                period_start=self.period_start,
                period_end=self.period_end,
            )
            return registry.compact(max_entries=12, max_artifacts=12)
        except Exception as exc:
            fallback = source_inventory.get("accounting_system_registry") or {}
            if fallback:
                fallback = dict(fallback)
                fallback.setdefault("error", f"live_registry_snapshot_failed:{type(exc).__name__}: {exc}")
                return fallback
            return {"error": f"{type(exc).__name__}: {exc}"}

    @staticmethod
    def _deadline_summary(audit: Dict[str, Any]) -> Dict[str, Any]:
        overdue: List[Dict[str, Any]] = []
        upcoming: List[Dict[str, Any]] = []
        for item in audit.get("deadline_assessments") or []:
            if not isinstance(item, dict):
                continue
            compact = {
                "name": item.get("name"),
                "due_date": item.get("due_date"),
                "status": item.get("status"),
                "days_overdue": item.get("days_overdue", 0),
                "estimated_penalty": item.get("estimated_penalty", ""),
            }
            if str(item.get("status", "")).lower() == "overdue":
                overdue.append(compact)
            else:
                upcoming.append(compact)
        return {
            "overdue_count": len(overdue),
            "overdue": overdue,
            "upcoming": upcoming[:5],
        }

    @staticmethod
    def _manual_safety(manifest: Dict[str, Any], audit: Dict[str, Any]) -> Dict[str, Any]:
        safety = dict(audit.get("safety") or {})
        safety.update(manifest.get("safety") or {})
        safety.setdefault("submits_to_companies_house", False)
        safety.setdefault("submits_to_hmrc", False)
        safety.setdefault("pays_tax_or_penalties", False)
        safety.setdefault("requires_human_approval", True)
        safety.setdefault("manual_filing_required", True)
        return safety

    @staticmethod
    def _build_prompt_lines(context: Dict[str, Any]) -> List[str]:
        lines: List[str] = []
        company = context.get("company") or {}
        run = context.get("full_run") or {}
        if company.get("company_name"):
            lines.append(
                f"Company {company.get('company_number')}: {company.get('company_name')} "
                f"status={company.get('company_status') or 'unknown'}"
            )
        if run.get("generated_at"):
            lines.append(
                f"Accounts pack {run.get('period_start')} to {run.get('period_end')}: "
                f"{run.get('accounts_build_status')} at {run.get('generated_at')}"
            )
        lines.append("Safety: manual director/accountant action required for Companies House, HMRC, tax payments, and penalties.")
        raw_manifest = context.get("raw_data_manifest") or {}
        raw_summary = raw_manifest.get("summary") or {}
        if raw_summary:
            lines.append(
                "Raw company data intake: "
                f"{raw_summary.get('file_count', 0)} files; "
                f"{raw_summary.get('transaction_source_count', 0)} transaction sources; "
                f"{raw_summary.get('evidence_only_count', 0)} evidence-only files."
            )
        autonomous = context.get("autonomous_workflow") or {}
        if autonomous:
            cognitive = autonomous.get("cognitive_review") or {}
            vault_memory = autonomous.get("vault_memory") or {}
            handoff_pack = (
                context.get("human_filing_handoff_pack")
                or autonomous.get("human_filing_handoff_pack")
                or {}
            )
            handoff_readiness = handoff_pack.get("readiness") or {}
            uk_brain = (
                context.get("uk_accounting_requirements_brain")
                or autonomous.get("uk_accounting_requirements_brain")
                or handoff_pack.get("uk_accounting_requirements_brain")
                or {}
            )
            uk_summary = uk_brain.get("summary") or {}
            uk_figures = uk_brain.get("figures") or {}
            evidence_authoring = (
                context.get("accounting_evidence_authoring")
                or autonomous.get("accounting_evidence_authoring")
                or handoff_pack.get("accounting_evidence_authoring")
                or {}
            )
            evidence_summary = evidence_authoring.get("summary") or {}
            llm_authoring = evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
            lines.append(
                "Autonomous accounts: "
                f"status={autonomous.get('status', 'unknown')}; "
                f"tasks={len(autonomous.get('agent_tasks') or [])}; "
                f"handoff={handoff_pack.get('status', 'unknown')} ready={handoff_readiness.get('ready_for_manual_upload', handoff_readiness.get('ready_for_manual_review', 'unknown'))}; "
                f"evidence_requests={evidence_summary.get('draft_count', 0)} docs={evidence_summary.get('generated_document_count', 0)}; "
                f"llm_docs={llm_authoring.get('completed_count', 0)} llm_status={llm_authoring.get('status', 'unknown')}; "
                f"uk_req={uk_summary.get('requirement_count', 0)} q={uk_summary.get('question_count', 0)} "
                f"vat={uk_figures.get('turnover_over_vat_threshold', 'unknown')}; "
                f"vault={vault_memory.get('status', 'unknown')}; "
                f"selfq={cognitive.get('status', 'unknown')} via {cognitive.get('answer_source', 'n/a')}; "
                "final-ready local pack, manual submission only."
            )
        end_user_automation = context.get("end_user_accounting_automation") or {}
        if end_user_automation:
            coverage = end_user_automation.get("requirement_coverage") or []
            generated = sum(
                1
                for item in coverage
                if str(item.get("status", "")).startswith("generated")
                or str(item.get("status", "")).startswith("final_ready")
            )
            manual = sum(1 for item in coverage if item.get("manual_required"))
            lines.append(
                "End-user accounting automation: "
                f"status={end_user_automation.get('status', 'unknown')}; "
                f"coverage={generated}/{len(coverage)} generated; "
                f"manual_items={manual}; "
                f"start_here={(end_user_automation.get('outputs') or {}).get('end_user_start_here', 'not generated')}"
            )
        swarm_scan = context.get("swarm_raw_data_wave_scan") or {}
        if swarm_scan:
            benchmark = swarm_scan.get("benchmark") or {}
            consensus = ((swarm_scan.get("waves") or {}).get("phi_swarm_consensus") or {})
            lines.append(
                "Accounting swarm wave scan: "
                f"status={swarm_scan.get('status', 'unknown')}; "
                f"files={benchmark.get('files_scanned', 0)}; "
                f"benchmark={benchmark.get('total_duration_seconds', 0)}s "
                f"{benchmark.get('files_per_second', 0)} files/s; "
                f"consensus={consensus.get('status', 'unknown')} score={consensus.get('score', 'n/a')}"
            )
        end_user_confirmation = context.get("end_user_confirmation") or {}
        if end_user_confirmation:
            confirmation = end_user_confirmation.get("confirmation") or end_user_confirmation
            lines.append(
                "End-user confirmation feed: "
                f"status={end_user_confirmation.get('status', confirmation.get('status', 'unknown'))}; "
                f"confirmed={len(confirmation.get('what_aureon_confirmed') or [])}; "
                f"attention={len(confirmation.get('attention_items') or [])}"
            )
        accounting_vault_memory = context.get("accounting_vault_memory") or {}
        if accounting_vault_memory:
            lines.append(
                "Accounting vault memory: "
                f"status={accounting_vault_memory.get('status', 'unknown')}; "
                f"index={accounting_vault_memory.get('index_exists', False)}; "
                f"workflows={accounting_vault_memory.get('workflow_count', 0)}"
            )
        registry = context.get("accounting_system_registry") or {}
        if registry and not registry.get("error"):
            domains = registry.get("domain_counts") or {}
            domain_text = ", ".join(f"{key}={value}" for key, value in sorted(domains.items())[:5])
            surfaces = registry.get("nonstandard_surfaces") or {}
            surface_text = ", ".join(key for key, ready in sorted(surfaces.items()) if ready) or "none"
            lines.append(
                "Accounting tools unified: "
                f"{registry.get('module_count', 0)} modules/tools, "
                f"{registry.get('artifact_count', 0)} artifacts; "
                f"domains={domain_text or 'none'}; "
                f"nonstandard={surface_text}"
            )
        accounting_control = context.get("aureon_accounting_control") or {}
        if accounting_control:
            journal = accounting_control.get("journal") or {}
            projection = accounting_control.get("quickbooks_projection") or {}
            lines.append(
                "Aureon canonical journal: "
                f"integrity={journal.get('integrity_verified', False)}; "
                f"entries={journal.get('entry_count', 0)}; "
                f"approved={journal.get('approved_entry_count', 0)}; "
                f"QBO queued={projection.get('queued_count', 0)}; "
                f"readback={projection.get('readback_verified_count', 0)}; "
                f"outstanding={projection.get('outstanding_readback_count', 0)}."
            )
        reconciliation = context.get("accounting_reconciliation") or {}
        if reconciliation:
            summary = reconciliation.get("summary") or {}
            workstreams = reconciliation.get("workstreams") or []
            critical = [
                item.get("id")
                for item in workstreams
                if isinstance(item, dict) and item.get("priority") == "critical"
            ]
            lines.append(
                "Aureon accounting reconciliation: "
                f"workstreams={summary.get('workstream_count', 0)}; "
                f"critical={','.join(str(item) for item in critical) or 'none'}; "
                f"postings_authorised={summary.get('posting_authorised_count', 0)}; "
                f"external_actions_authorised={summary.get('external_compliance_action_authorised_count', 0)}."
            )
        quickbooks = context.get("quickbooks") or {}
        if quickbooks:
            api = quickbooks.get("api") or {}
            bank_feed = quickbooks.get("bank_feed") or {}
            chart = quickbooks.get("chart_of_accounts") or {}
            lines.append(
                "QuickBooks control plane: "
                "authority=Aureon OS canonical; QuickBooks=projection/read-back; "
                f"state={quickbooks.get('connection_state', 'unknown')}; "
                f"api={api.get('company_info_readback', 'not_verified')}; "
                f"bank_feed={bank_feed.get('connected', False)} "
                f"pending={bank_feed.get('pending_transaction_count', 0)} "
                f"ownership={bank_feed.get('ownership_status', 'unknown')}; "
                f"chart_accounts={chart.get('account_count', 0)}; "
                f"aureon_posted={bank_feed.get('aureon_posted_transaction_count', 0)}; "
                "writes remain gated."
            )
        statutory = context.get("statutory_filing_pack") or {}
        if statutory:
            statutory_outputs = statutory.get("outputs") or {}
            requirement_summary = (statutory.get("government_requirements_matrix") or {}).get("summary") or {}
            lines.append(
                "Companies House/HMRC final-ready manual filing pack: "
                f"{len(statutory_outputs)} outputs; "
                f"{requirement_summary.get('requirement_count', 'all tracked')} government requirements tracked; "
                "CT600/iXBRL official submission remains manual."
            )
        local_pack = context.get("local_accounts_pack") or {}
        if local_pack:
            complete = local_pack.get("complete")
            rows = local_pack.get("rows_in_period")
            lines.append(f"Local accounts pack complete={complete}; rows_in_period={rows}")
        combined = context.get("combined_bank_data") or {}
        if combined:
            accounts = ", ".join(combined.get("source_accounts") or []) or "unknown"
            transaction_sources = combined.get("transaction_source_count", combined.get("csv_source_count", 0))
            lines.append(
                "Bank/account data combined: "
                f"{transaction_sources} transaction sources "
                f"({combined.get('csv_source_count', 0)} CSV, {combined.get('pdf_source_count', 0)} parsed PDF), "
                f"{combined.get('unique_rows_in_period', 0)} unique period rows, "
                f"{combined.get('duplicate_rows_removed', 0)} duplicate overlaps removed; "
                f"accounts={accounts}"
            )
            source_summary = combined.get("source_provider_summary") or {}
            flow_summary = combined.get("flow_provider_summary") or {}
            if source_summary:
                provider_text = ", ".join(
                    f"{name}:{info.get('rows', 0)}"
                    for name, info in sorted(source_summary.items())
                )
                lines.append(f"Source providers: {provider_text}")
            if flow_summary:
                flow_text = ", ".join(
                    f"{name}:{info.get('rows', 0)}"
                    for name, info in sorted(flow_summary.items())
                )
                lines.append(f"Flow providers: {flow_text}")
        deadlines = context.get("deadlines") or {}
        if deadlines.get("overdue_count"):
            bits = [
                f"{item.get('name')} due {item.get('due_date')}"
                for item in deadlines.get("overdue", [])[:3]
            ]
            lines.append(f"Overdue accounting/compliance items: {deadlines.get('overdue_count')} ({'; '.join(bits)})")
        coverage = context.get("bank_statement_coverage") or {}
        if coverage:
            lines.append(
                f"Bank evidence complete={coverage.get('complete')}; "
                f"missing_months={coverage.get('missing_months') or []}"
            )
        source_inventory = context.get("source_data_inventory") or {}
        if source_inventory:
            lines.append(
                f"Source data: {source_inventory.get('csv_count', 0)} CSV files, "
                f"{source_inventory.get('evidence_file_count', 0)} evidence files"
            )
        years = context.get("tax_years") or {}
        for year in ("2024/25", "2025/26"):
            data = years.get(year) or {}
            if not data:
                continue
            lines.append(
                f"{year}: turnover GBP {data.get('turnover', 0):,.2f}, "
                f"expenses GBP {data.get('allowable_expenses', 0):,.2f}, "
                f"net GBP {data.get('net_profit', 0):,.2f}, rows={data.get('bank_rows', 0)}"
            )
        submit = context.get("submission_status") or {}
        if submit:
            reason = str(submit.get("reason", "")).strip()
            lines.append(f"HMRC submitted={bool(submit.get('hmrc_api_submitted'))}; {reason}".rstrip("; "))
        return [line for line in lines if line]

    def load_context(self, force: bool = False) -> Dict[str, Any]:
        with self._lock:
            paths = self._paths()
            signature = self._signature_for(paths)
            if not force and self._cached_context and signature == self._cached_signature:
                return dict(self._cached_context)

            filing_pack = self._read_json(paths["filing_pack"])
            gateway_summary = self._read_json(paths["gateway_summary"])
            exchange_coverage = self._read_json(paths["exchange_coverage"])
            full_run = self._read_json(paths["full_run_manifest"])
            compliance = self._read_json(paths["compliance_audit_json"])
            period_manifest = self._read_json(paths["period_manifest"])
            statutory_manifest = self._read_json(paths["statutory_manifest"])
            raw_data_manifest = self._read_json(paths["raw_data_manifest"])
            autonomous_workflow = self._read_json(paths["autonomous_workflow_manifest"])
            end_user_automation = self._read_json(paths["end_user_accounting_automation_manifest"])
            swarm_raw_data_wave_scan = (
                self._read_json(paths["swarm_raw_data_wave_scan_json"])
                or end_user_automation.get("swarm_raw_data_wave_scan")
                or {}
            )
            internal_logic_chain = (
                self._read_json(paths["internal_logic_chain_checklist_json"])
                or {"checklist": end_user_automation.get("internal_logic_chain_checklist") or []}
            )
            end_user_confirmation = (
                self._read_json(paths["end_user_confirmation_json"])
                or {"confirmation": end_user_automation.get("end_user_confirmation") or {}}
            )
            handoff_pack = (
                self._read_json(paths["handoff_manifest"])
                or autonomous_workflow.get("human_filing_handoff_pack")
                or end_user_automation.get("workflow_manifest", {}).get("human_filing_handoff_pack")
                or {}
            )
            uk_accounting_brain = (
                self._read_json(paths["uk_accounting_requirements_brain_json"])
                or handoff_pack.get("uk_accounting_requirements_brain")
                or autonomous_workflow.get("uk_accounting_requirements_brain")
                or self._fallback_uk_accounting_requirements_brain(paths)
            )
            accounting_evidence_authoring = (
                self._read_json(paths["accounting_evidence_authoring_manifest"])
                or handoff_pack.get("accounting_evidence_authoring")
                or autonomous_workflow.get("accounting_evidence_authoring")
                or self._fallback_accounting_evidence_authoring(paths)
            )
            accounting_vault_memory = self._accounting_vault_memory_status(paths)
            quickbooks_status = self._read_json(paths["quickbooks_status"])
            accounting_control_status = self._read_json(paths["aureon_accounting_control_status"])
            accounting_reconciliation = self._read_json(paths["aureon_accounting_reconciliation_status"])

            years_out: Dict[str, Dict[str, Any]] = {}
            for year in ("2024/25", "2025/26"):
                year_blob = (filing_pack.get("tax_years") or {}).get(year) or {}
                metrics = self._extract_year_metrics(year_blob) if year_blob else {
                    "turnover": 0.0,
                    "allowable_expenses": 0.0,
                    "net_profit": 0.0,
                    "filing_deadlines": {},
                }
                gw = gateway_summary.get(year) or {}
                import_summary = gw.get("import_summary") or {}
                metrics["bank_rows"] = int(import_summary.get("bank_transactions", 0))
                metrics["gateway_status"] = gw.get("status", "")
                metrics["gateway_warnings"] = list(gw.get("warnings") or [])
                years_out[year] = metrics

            source_inventory = full_run.get("source_data_inventory") or {}
            combined_bank_data = (
                period_manifest.get("combined_bank_data")
                or source_inventory.get("combined_bank_data")
                or {}
            )
            accounting_registry = self._accounting_registry_snapshot(source_inventory)
            csv_files = source_inventory.get("csv_files") or []
            evidence_files = source_inventory.get("evidence_files") or []
            source_summary = {
                "csv_count": len(csv_files),
                "evidence_file_count": len(evidence_files) or self._dir_file_count(paths["business_accounts_dir"]),
                "business_accounts_dir": source_inventory.get("business_accounts_dir") or str(paths["business_accounts_dir"]),
                "csv_files": csv_files[:10],
                "evidence_files": evidence_files[:10],
                "combined_bank_data": combined_bank_data,
                "accounting_system_registry": accounting_registry,
                "accounting_vault_memory": accounting_vault_memory,
                "aureon_accounting_control": accounting_control_status,
                "accounting_reconciliation": accounting_reconciliation,
                "quickbooks": quickbooks_status,
            }

            company = dict(compliance.get("public_company_profile") or {})
            company.setdefault("company_number", self.company_number)
            company.setdefault("company_name", (period_manifest.get("entity") or "").upper())
            statutory_pack = (
                full_run.get("statutory_filing_pack")
                or statutory_manifest
                or self._fallback_statutory_filing_pack(paths)
            )

            context: Dict[str, Any] = {
                "schema_version": "accounting-context-v2",
                "generated_at": (
                    full_run.get("generated_at")
                    or compliance.get("generated_at")
                    or filing_pack.get("generated_at")
                    or exchange_coverage.get("generated_at_utc")
                    or ""
                ),
                "repo_root": str(self.repo_root),
                "company": company,
                "full_run": {
                    "company_number": full_run.get("company_number") or self.company_number,
                    "period_start": full_run.get("period_start") or self.period_start,
                    "period_end": full_run.get("period_end") or self.period_end,
                    "generated_at": full_run.get("generated_at") or "",
                    "mode": full_run.get("mode") or "read_only_prepare_accounts_no_filing",
                    "accounts_build_status": ((full_run.get("accounts_build") or {}).get("status") or "unknown"),
                    "next_human_step": full_run.get("next_human_step") or "",
                },
                "tax_years": years_out,
                "exchange_venues": exchange_coverage.get("venue_summary") or {},
                "submission_status": filing_pack.get("submission_status") or {},
                "bank_statement_coverage": compliance.get("bank_statement_coverage") or {},
                "deadlines": self._deadline_summary(compliance),
                "local_accounts_pack": compliance.get("local_accounts_pack") or {},
                "next_actions": list(compliance.get("next_actions") or []),
                "official_sources": compliance.get("official_sources") or {},
                "period_manifest": {
                    "period_start": period_manifest.get("period_start") or self.period_start,
                    "period_end": period_manifest.get("period_end") or self.period_end,
                    "entity": period_manifest.get("entity") or "",
                    "rows_in_period": period_manifest.get("rows_in_period", 0),
                    "combined_bank_data": combined_bank_data,
                    "merged_pdf": period_manifest.get("merged_pdf") or "",
                    "desktop_pdf": period_manifest.get("desktop_pdf") or "",
                },
                "outputs": self._output_status(full_run, paths),
                "statutory_filing_pack": statutory_pack,
                "raw_data_manifest": raw_data_manifest,
                "swarm_raw_data_wave_scan": swarm_raw_data_wave_scan,
                "internal_logic_chain_checklist": internal_logic_chain,
                "end_user_confirmation": end_user_confirmation,
                "autonomous_workflow": autonomous_workflow,
                "end_user_accounting_automation": end_user_automation,
                "human_filing_handoff_pack": handoff_pack,
                "accounting_evidence_authoring": accounting_evidence_authoring,
                "uk_accounting_requirements_brain": uk_accounting_brain,
                "accounting_vault_memory": accounting_vault_memory,
                "aureon_accounting_control": accounting_control_status,
                "accounting_reconciliation": accounting_reconciliation,
                "quickbooks": quickbooks_status,
                "safety": self._manual_safety(full_run, compliance),
                "combined_bank_data": combined_bank_data,
                "accounting_system_registry": accounting_registry,
                "source_data_inventory": source_summary,
                "source_files": {key: str(path) for key, path in paths.items() if path.exists()},
                "csv_rows": {
                    "2024/25": self._csv_rows(paths["year_2024_25_csv"]),
                    "2025/26": self._csv_rows(paths["year_2025_26_csv"]),
                    "full_period": self._csv_rows(paths["full_period_csv"]),
                },
                "summary_markdown_excerpt": self._read_text(paths["full_run_summary"], limit=1200),
                "thoughtbus_topics": list(ACCOUNTING_TOPICS),
            }
            context["prompt_lines"] = self._build_prompt_lines(context)

            self._cached_context = context
            self._cached_signature = signature
            return dict(context)

    def validate_accounting_readiness(
        self,
        context: Dict[str, Any] | None = None,
        *,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Return a software/data readiness checklist for final-ready accounts work."""
        context = context or self.load_context(force=force)
        outputs = context.get("outputs") or {}
        combined = context.get("combined_bank_data") or {}
        registry = context.get("accounting_system_registry") or {}
        safety = context.get("safety") or {}
        company = context.get("company") or {}
        statutory = context.get("statutory_filing_pack") or {}
        raw_manifest = context.get("raw_data_manifest") or {}
        swarm_scan = context.get("swarm_raw_data_wave_scan") or {}
        internal_logic_chain = context.get("internal_logic_chain_checklist") or {}
        end_user_confirmation = context.get("end_user_confirmation") or {}
        handoff_pack = context.get("human_filing_handoff_pack") or {}
        accounting_evidence_authoring = context.get("accounting_evidence_authoring") or handoff_pack.get("accounting_evidence_authoring") or {}
        uk_accounting_brain = context.get("uk_accounting_requirements_brain") or handoff_pack.get("uk_accounting_requirements_brain") or {}
        accounting_vault_memory = context.get("accounting_vault_memory") or {}
        quickbooks = context.get("quickbooks") or {}
        source_providers = combined.get("source_provider_summary") or {}
        flow_providers = combined.get("flow_provider_summary") or {}
        source_files = context.get("source_files") or {}
        public_capability_mode = (
            (company.get("company_number") or self.company_number) == DEFAULT_COMPANY_NUMBER
            and bool(source_files.get("statutory_generator"))
        )

        def provider_rows(provider: str) -> int:
            source = source_providers.get(provider) or {}
            flow = flow_providers.get(provider) or {}
            return int(source.get("rows", 0) or 0) + int(flow.get("rows", 0) or 0)

        def output_exists(key: str) -> bool:
            aliases = {
                "companies_house_accounts_final_ready_markdown": ("companies_house_accounts_markdown",),
                "companies_house_accounts_final_ready_pdf": ("companies_house_accounts_pdf",),
                "directors_report_final_ready_markdown": ("directors_report_markdown",),
                "directors_report_final_ready_pdf": ("directors_report_pdf",),
                "audit_exemption_statement_final_ready_markdown": ("audit_exemption_statement_markdown",),
                "hmrc_tax_computation_final_ready_markdown": ("hmrc_tax_computation_markdown",),
                "hmrc_tax_computation_final_ready_pdf": ("hmrc_tax_computation_pdf",),
                "ct600_manual_entry_json": ("hmrc_ct600_draft_json",),
                "ct600_box_map_final_ready_markdown": ("ct600_box_map_markdown",),
                "accounts_readable_for_ixbrl_html": ("draft_accounts_html",),
                "computation_readable_for_ixbrl_html": ("draft_computation_html",),
                "companies_house_accounts_markdown": ("companies_house_accounts_final_ready_markdown",),
                "companies_house_accounts_pdf": ("companies_house_accounts_final_ready_pdf",),
                "directors_report_markdown": ("directors_report_final_ready_markdown",),
                "directors_report_pdf": ("directors_report_final_ready_pdf",),
                "audit_exemption_statement_markdown": ("audit_exemption_statement_final_ready_markdown",),
                "hmrc_tax_computation_markdown": ("hmrc_tax_computation_final_ready_markdown",),
                "hmrc_tax_computation_pdf": ("hmrc_tax_computation_final_ready_pdf",),
                "hmrc_ct600_draft_json": ("ct600_manual_entry_json",),
                "ct600_box_map_markdown": ("ct600_box_map_final_ready_markdown",),
                "draft_accounts_html": ("accounts_readable_for_ixbrl_html",),
                "draft_computation_html": ("computation_readable_for_ixbrl_html",),
            }
            item = outputs.get(key) or {}
            if bool(isinstance(item, dict) and item.get("exists")):
                return True
            return any(
                bool(isinstance(outputs.get(alias), dict) and outputs.get(alias, {}).get("exists"))
                for alias in aliases.get(key, ())
            )

        checks: List[Dict[str, Any]] = []

        def add(name: str, ok: bool, detail: str, *, required: bool = True) -> None:
            checks.append(
                {
                    "name": name,
                    "ok": bool(ok),
                    "required": bool(required),
                    "status": "ready" if ok else "blocked",
                    "detail": detail,
                }
            )

        transaction_sources = combined.get("transaction_source_count", combined.get("csv_source_count", 0))
        add(
            "combined_bank_data",
            bool(transaction_sources and combined.get("unique_rows_in_period", 0)),
            (
                f"sources={transaction_sources}, "
                f"unique_rows={combined.get('unique_rows_in_period', 0)}, "
                f"duplicates_removed={combined.get('duplicate_rows_removed', 0)}"
            ),
        )
        raw_summary = raw_manifest.get("summary") or {}
        add(
            "raw_company_data_intake",
            bool(raw_summary.get("file_count", 0)),
            (
                f"files={raw_summary.get('file_count', 0)}, "
                f"transaction_sources={raw_summary.get('transaction_source_count', 0)}, "
                f"evidence_only={raw_summary.get('evidence_only_count', 0)}"
            ),
            required=False,
        )
        swarm_benchmark = swarm_scan.get("benchmark") or {}
        swarm_consensus = ((swarm_scan.get("waves") or {}).get("phi_swarm_consensus") or {})
        add(
            "raw_data_swarm_wave_scan",
            swarm_scan.get("status") == "completed" and bool(swarm_benchmark.get("files_scanned", 0)),
            (
                f"files={swarm_benchmark.get('files_scanned', 0)}, "
                f"duration={swarm_benchmark.get('total_duration_seconds', 0)}s, "
                f"consensus={swarm_consensus.get('status', 'unknown')}, "
                f"score={swarm_consensus.get('score', 'n/a')}"
            ),
            required=not public_capability_mode,
        )
        if isinstance(internal_logic_chain, dict):
            logic_items = internal_logic_chain.get("checklist") or []
        elif isinstance(internal_logic_chain, list):
            logic_items = internal_logic_chain
        else:
            logic_items = []
        add(
            "internal_logic_chain_checklist",
            bool(logic_items),
            f"items={len(logic_items) if isinstance(logic_items, list) else 0}",
            required=not public_capability_mode,
        )
        confirmation_payload = end_user_confirmation.get("confirmation") or end_user_confirmation
        add(
            "end_user_confirmation_feed",
            bool(confirmation_payload.get("what_aureon_confirmed") or confirmation_payload.get("status")),
            (
                f"status={end_user_confirmation.get('status', confirmation_payload.get('status', 'unknown'))}, "
                f"confirmed={len(confirmation_payload.get('what_aureon_confirmed') or [])}, "
                f"attention={len(confirmation_payload.get('attention_items') or [])}"
            ),
            required=not public_capability_mode,
        )
        add("zempler_bank_feed", provider_rows("zempler") > 0, f"rows={provider_rows('zempler')}")
        add("revolut_bank_feed", provider_rows("revolut") > 0, f"rows={provider_rows('revolut')}")
        add("sumup_sales_flow", provider_rows("sumup") > 0, f"rows={provider_rows('sumup')}")
        add(
            "duplicate_overlap_control",
            "duplicate_rows_removed" in combined,
            f"duplicate_rows_removed={combined.get('duplicate_rows_removed', 'unknown')}",
        )
        add(
            "source_evidence_inventory",
            bool((context.get("source_data_inventory") or {}).get("evidence_file_count", 0)),
            f"evidence_files={(context.get('source_data_inventory') or {}).get('evidence_file_count', 0)}",
        )
        add(
            "public_company_profile",
            bool(company.get("company_number")),
            f"{company.get('company_number', self.company_number)} status={company.get('company_status') or 'unknown'}",
            required=False,
        )
        add(
            "accounting_tool_registry",
            bool(registry and not registry.get("error") and registry.get("module_count", 0) > 0),
            f"modules={registry.get('module_count', 0)}, artifacts={registry.get('artifact_count', 0)}",
        )
        add(
            "accounting_vault_memory",
            bool(accounting_vault_memory.get("index_exists") or accounting_vault_memory.get("workflow_count", 0)),
            (
                f"status={accounting_vault_memory.get('status', 'unknown')}, "
                f"index={accounting_vault_memory.get('index_exists', False)}, "
                f"workflows={accounting_vault_memory.get('workflow_count', 0)}"
            ),
            required=False,
        )
        accounting_control = context.get("aureon_accounting_control") or {}
        canonical_journal = accounting_control.get("journal") or {}
        projection_queue = accounting_control.get("quickbooks_projection") or {}
        add(
            "aureon_canonical_accounting_journal",
            bool(accounting_control and canonical_journal.get("integrity_verified")),
            (
                f"integrity={canonical_journal.get('integrity_verified', False)}, "
                f"entries={canonical_journal.get('entry_count', 0)}, "
                f"approved={canonical_journal.get('approved_entry_count', 0)}, "
                f"qbo_queued={projection_queue.get('queued_count', 0)}, "
                f"qbo_readback={projection_queue.get('readback_verified_count', 0)}, "
                f"outstanding={projection_queue.get('outstanding_readback_count', 0)}"
            ),
            required=False,
        )
        reconciliation = context.get("accounting_reconciliation") or {}
        reconciliation_summary = reconciliation.get("summary") or {}
        add(
            "aureon_accounting_reconciliation",
            bool(
                reconciliation.get("schema_version") == "aureon-accounting-reconciliation-v1"
                and reconciliation_summary.get("posting_authorised_count", 0) == 0
                and reconciliation_summary.get("external_compliance_action_authorised_count", 0) == 0
            ),
            (
                f"workstreams={reconciliation_summary.get('workstream_count', 0)}, "
                f"critical={reconciliation_summary.get('critical_workstream_count', 0)}, "
                f"postings_authorised={reconciliation_summary.get('posting_authorised_count', 0)}, "
                "role=derived_work_queue_not_ledger_or_filing_instruction"
            ),
            required=False,
        )
        quickbooks_api = quickbooks.get("api") or {}
        quickbooks_bank = quickbooks.get("bank_feed") or {}
        add(
            "quickbooks_control_plane",
            bool(quickbooks and quickbooks.get("connection_state")),
            (
                f"state={quickbooks.get('connection_state', 'not_configured')}, "
                f"api_readback={quickbooks_api.get('company_info_readback', 'not_verified')}, "
                f"bank_feed={quickbooks_bank.get('connected', False)}, "
                f"ownership={quickbooks_bank.get('ownership_status', 'unknown')}, "
                f"pending={quickbooks_bank.get('pending_transaction_count', 0)}"
            ),
            required=False,
        )
        for output_key in (
            "accounts_pack_pdf",
            "management_accounts",
            "general_ledger",
            "trial_balance",
            "profit_and_loss",
            "tax_summary",
            "combined_bank_transactions",
            "period_manifest",
        ):
            item = outputs.get(output_key) or {}
            add(
                f"accounts_output:{output_key}",
                output_exists(output_key),
                item.get("path") or "not found",
            )
        for output_key in (
            "companies_house_accounts_final_ready_markdown",
            "companies_house_accounts_final_ready_pdf",
            "directors_report_final_ready_markdown",
            "directors_report_final_ready_pdf",
            "audit_exemption_statement_final_ready_markdown",
            "hmrc_tax_computation_final_ready_markdown",
            "hmrc_tax_computation_final_ready_pdf",
            "ct600_manual_entry_json",
            "ct600_box_map_final_ready_markdown",
            "companies_house_accounts_markdown",
            "companies_house_accounts_pdf",
            "directors_report_markdown",
            "directors_report_pdf",
            "audit_exemption_statement_markdown",
            "hmrc_tax_computation_markdown",
            "hmrc_tax_computation_pdf",
            "hmrc_ct600_draft_json",
            "ct600_box_map_markdown",
            "supplementary_pages_review_json",
            "confirmation_statement_readiness_json",
            "confirmation_statement_readiness_markdown",
            "accounts_readable_for_ixbrl_html",
            "computation_readable_for_ixbrl_html",
            "draft_accounts_html",
            "draft_computation_html",
            "ixbrl_readiness_note",
            "government_requirements_matrix_json",
            "government_requirements_matrix_markdown",
            "filing_checklist",
            "statutory_manifest",
        ):
            item = outputs.get(output_key) or {}
            add(
                f"statutory_output:{output_key}",
                output_exists(output_key),
                item.get("path") or "not found",
                required=not public_capability_mode,
            )
        add(
            "statutory_pack_manifest",
            bool(statutory and statutory.get("schema_version")),
            statutory.get("generated_at") or "not generated",
            required=not public_capability_mode,
        )
        handoff_readiness = handoff_pack.get("readiness") or {}
        add(
            "human_filing_handoff_pack",
            bool(handoff_pack and handoff_readiness.get("ready_for_manual_upload", handoff_readiness.get("ready_for_manual_review"))),
            (
                f"status={handoff_pack.get('status', 'unknown')}, "
                f"ready={handoff_readiness.get('ready_for_manual_upload', handoff_readiness.get('ready_for_manual_review', 'unknown'))}, "
                f"output_dir={handoff_pack.get('output_dir', 'not generated')}"
            ),
            required=not public_capability_mode,
        )
        evidence_summary = accounting_evidence_authoring.get("summary") or {}
        llm_authoring = accounting_evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
        add(
            "accounting_evidence_authoring",
            bool(accounting_evidence_authoring and evidence_summary.get("draft_count", 0) >= 0 and accounting_evidence_authoring.get("outputs")),
            (
                f"status={accounting_evidence_authoring.get('status', 'unknown')}, "
                f"requests={evidence_summary.get('draft_count', 0)}, "
                f"documents={evidence_summary.get('generated_document_count', 0)}, "
                f"petty_cash={evidence_summary.get('petty_cash_withdrawal_count', 0)}, "
                f"llm_status={llm_authoring.get('status', 'unknown')}, "
                f"llm_docs={llm_authoring.get('completed_count', 0)}, "
                "internal_support_documents_only"
            ),
        )
        uk_summary = uk_accounting_brain.get("summary") or {}
        uk_figures = uk_accounting_brain.get("figures") or {}
        add(
            "uk_accounting_requirements_brain",
            bool(uk_accounting_brain and uk_summary.get("requirement_count", 0) and uk_summary.get("question_count", 0)),
            (
                f"status={uk_accounting_brain.get('status', 'unknown')}, "
                f"requirements={uk_summary.get('requirement_count', 0)}, "
                f"questions={uk_summary.get('question_count', 0)}, "
                f"vat_over_threshold={uk_figures.get('turnover_over_vat_threshold', 'unknown')}"
            ),
        )
        add(
            "manual_government_filing_boundary",
            bool(safety.get("manual_filing_required", True))
            and not safety.get("submits_to_companies_house", False)
            and not safety.get("submits_to_hmrc", False)
            and not safety.get("pays_tax_or_penalties", False),
            "Companies House, HMRC, tax and penalty actions are manual only.",
        )

        required_failures = [item for item in checks if item["required"] and not item["ok"]]
        optional_failures = [item for item in checks if not item["required"] and not item["ok"]]
        return {
            "schema_version": "accounting-readiness-v1",
            "ready": not required_failures,
            "ready_for": (
                "public_tooling_ready_private_pack_generation_required"
                if public_capability_mode and not (statutory and statutory.get("schema_version"))
                else "final_ready_manual_upload_pack"
            ),
            "required_failures": required_failures,
            "optional_failures": optional_failures,
            "checks": checks,
            "bank_sources": transaction_sources,
            "unique_bank_rows": combined.get("unique_rows_in_period", 0),
            "raw_file_count": raw_summary.get("file_count", 0),
            "statutory_outputs": len(statutory.get("outputs") or {}),
            "manual_filing_required": bool(safety.get("manual_filing_required", True)),
        }

    def status(self, *, force: bool = False) -> Dict[str, Any]:
        context = self.load_context(force=force)
        outputs = context.get("outputs") or {}
        missing_outputs = sorted(
            key for key, value in outputs.items()
            if not (isinstance(value, dict) and value.get("exists"))
        )
        deadlines = context.get("deadlines") or {}
        company = context.get("company") or {}
        full_run = context.get("full_run") or {}
        readiness = self.validate_accounting_readiness(context)
        statutory = context.get("statutory_filing_pack") or {}
        raw_manifest = context.get("raw_data_manifest") or {}
        autonomous_workflow = context.get("autonomous_workflow") or {}
        end_user_automation = context.get("end_user_accounting_automation") or {}
        handoff_pack = context.get("human_filing_handoff_pack") or {}
        accounting_evidence_authoring = context.get("accounting_evidence_authoring") or handoff_pack.get("accounting_evidence_authoring") or autonomous_workflow.get("accounting_evidence_authoring") or {}
        uk_accounting_brain = context.get("uk_accounting_requirements_brain") or handoff_pack.get("uk_accounting_requirements_brain") or autonomous_workflow.get("uk_accounting_requirements_brain") or {}
        return {
            "available": bool((self.repo_root / "Kings_Accounting_Suite").exists()),
            "company_number": company.get("company_number") or self.company_number,
            "company_name": company.get("company_name") or "",
            "company_status": company.get("company_status") or "",
            "period_start": full_run.get("period_start") or self.period_start,
            "period_end": full_run.get("period_end") or self.period_end,
            "generated_at": context.get("generated_at") or "",
            "accounts_build_status": full_run.get("accounts_build_status") or "unknown",
            "overdue_count": deadlines.get("overdue_count", 0),
            "missing_outputs": missing_outputs,
            "bank_evidence_complete": (context.get("bank_statement_coverage") or {}).get("complete"),
            "manual_filing_required": bool((context.get("safety") or {}).get("manual_filing_required", True)),
            "combined_bank_data": context.get("combined_bank_data") or {},
            "accounting_system_registry": context.get("accounting_system_registry") or {},
            "statutory_filing_pack": statutory,
            "raw_data_manifest": raw_manifest,
            "swarm_raw_data_wave_scan": context.get("swarm_raw_data_wave_scan") or {},
            "internal_logic_chain_checklist": context.get("internal_logic_chain_checklist") or {},
            "end_user_confirmation": context.get("end_user_confirmation") or {},
            "autonomous_workflow": autonomous_workflow,
            "end_user_accounting_automation": end_user_automation,
            "cognitive_review": autonomous_workflow.get("cognitive_review") or {},
            "vault_memory": autonomous_workflow.get("vault_memory") or {},
            "accounting_vault_memory": context.get("accounting_vault_memory") or {},
            "aureon_accounting_control": context.get("aureon_accounting_control") or {},
            "accounting_reconciliation": context.get("accounting_reconciliation") or {},
            "quickbooks": context.get("quickbooks") or {},
            "human_filing_handoff_pack": handoff_pack,
            "accounting_evidence_authoring": accounting_evidence_authoring,
            "uk_accounting_requirements_brain": uk_accounting_brain,
            "accounting_readiness": readiness,
            "source_files": context.get("source_files") or {},
            "outputs": outputs,
            "topics": list(ACCOUNTING_TOPICS),
        }

    def render_for_prompt(self, context: Dict[str, Any] | None = None, max_chars: int = 700) -> str:  # type: ignore[override]
        # Backward-compatible class call support:
        # AccountingContextBridge.render_for_prompt(context, max_chars=...)
        if isinstance(self, dict):  # type: ignore[unreachable]
            render_context = self  # type: ignore[assignment]
            if isinstance(context, int):
                max_chars = int(context)
        else:
            render_context = context if isinstance(context, dict) else self.load_context()

        lines = list(render_context.get("prompt_lines") or [])
        if not lines:
            return ""
        text = "Accounting context (final-ready accounts + compliance artifacts):\n" + "\n".join(f"  - {line}" for line in lines)
        if len(text) > max_chars:
            text = text[: max_chars - 3].rstrip() + "..."
        return text

    def ingest_to_vault(self, vault: Any, *, force: bool = False) -> int:
        if vault is None or not hasattr(vault, "ingest"):
            return 0
        context = self.load_context(force=force)
        if not context:
            return 0

        signature_payload = {
            "generated_at": context.get("generated_at"),
            "company": context.get("company"),
            "full_run": context.get("full_run"),
            "deadlines": context.get("deadlines"),
            "combined_bank_data": context.get("combined_bank_data"),
            "accounting_system_registry": context.get("accounting_system_registry"),
            "statutory_filing_pack": context.get("statutory_filing_pack"),
            "raw_data_manifest": context.get("raw_data_manifest"),
            "swarm_raw_data_wave_scan": context.get("swarm_raw_data_wave_scan"),
            "internal_logic_chain_checklist": context.get("internal_logic_chain_checklist"),
            "end_user_confirmation": context.get("end_user_confirmation"),
            "autonomous_workflow": context.get("autonomous_workflow"),
            "end_user_accounting_automation": context.get("end_user_accounting_automation"),
            "accounting_vault_memory": context.get("accounting_vault_memory"),
            "aureon_accounting_control": context.get("aureon_accounting_control"),
            "accounting_reconciliation": context.get("accounting_reconciliation"),
            "quickbooks": context.get("quickbooks"),
            "human_filing_handoff_pack": context.get("human_filing_handoff_pack"),
            "accounting_evidence_authoring": context.get("accounting_evidence_authoring"),
            "uk_accounting_requirements_brain": context.get("uk_accounting_requirements_brain"),
            "accounting_readiness": self.validate_accounting_readiness(context),
            "outputs": context.get("outputs"),
            "safety": context.get("safety"),
        }
        signature = json.dumps(signature_payload, sort_keys=True, separators=(",", ":"))
        if not force and signature == self._last_vault_signature:
            return 0

        ingested = 0
        try:
            vault.ingest(
                topic="accounting.context.summary",
                category="accounting_summary",
                payload={
                    "generated_at": context.get("generated_at"),
                    "company": context.get("company"),
                    "full_run": context.get("full_run"),
                    "prompt_lines": context.get("prompt_lines"),
                    "deadlines": context.get("deadlines"),
                    "combined_bank_data": context.get("combined_bank_data"),
                    "accounting_system_registry": context.get("accounting_system_registry"),
                    "statutory_filing_pack": context.get("statutory_filing_pack"),
                    "raw_data_manifest": context.get("raw_data_manifest"),
                    "swarm_raw_data_wave_scan": context.get("swarm_raw_data_wave_scan"),
                    "internal_logic_chain_checklist": context.get("internal_logic_chain_checklist"),
                    "end_user_confirmation": context.get("end_user_confirmation"),
                    "autonomous_workflow": context.get("autonomous_workflow"),
                    "end_user_accounting_automation": context.get("end_user_accounting_automation"),
                    "accounting_vault_memory": context.get("accounting_vault_memory"),
                    "aureon_accounting_control": context.get("aureon_accounting_control"),
                    "accounting_reconciliation": context.get("accounting_reconciliation"),
                    "quickbooks": context.get("quickbooks"),
                    "human_filing_handoff_pack": context.get("human_filing_handoff_pack"),
                    "accounting_evidence_authoring": context.get("accounting_evidence_authoring"),
                    "uk_accounting_requirements_brain": context.get("uk_accounting_requirements_brain"),
                    "accounting_readiness": self.validate_accounting_readiness(context),
                    "outputs": context.get("outputs"),
                    "safety": context.get("safety"),
                    "source_files": context.get("source_files"),
                },
            )
            ingested += 1
            vault.ingest(
                topic="accounting.readiness",
                category="accounting_readiness",
                payload=self.validate_accounting_readiness(context),
            )
            ingested += 1
            accounting_vault_memory = context.get("accounting_vault_memory") or {}
            if accounting_vault_memory:
                vault.ingest(
                    topic="accounting.vault.memory.ready",
                    category="accounting_vault_memory",
                    payload=accounting_vault_memory,
                )
                ingested += 1
            accounting_control = context.get("aureon_accounting_control") or {}
            if accounting_control:
                vault.ingest(
                    topic="accounting.canonical_journal.status",
                    category="accounting_canonical_journal",
                    payload=accounting_control,
                )
                ingested += 1
            reconciliation = context.get("accounting_reconciliation") or {}
            if reconciliation:
                vault.ingest(
                    topic="accounting.reconciliation.status",
                    category="accounting_reconciliation",
                    payload=reconciliation,
                )
                ingested += 1
            quickbooks = context.get("quickbooks") or {}
            if quickbooks:
                vault.ingest(
                    topic="accounting.quickbooks.status",
                    category="accounting_quickbooks",
                    payload=quickbooks,
                )
                ingested += 1
            swarm_scan = context.get("swarm_raw_data_wave_scan") or {}
            if swarm_scan:
                vault.ingest(
                    topic="accounting.raw_data.swarm_scan.ready",
                    category="accounting_swarm_scan",
                    payload=swarm_scan,
                )
                ingested += 1
            logic_chain = context.get("internal_logic_chain_checklist") or {}
            if logic_chain:
                vault.ingest(
                    topic="accounting.logic_chain.ready",
                    category="accounting_logic_chain",
                    payload=logic_chain,
                )
                ingested += 1
            end_user_confirmation = context.get("end_user_confirmation") or {}
            if end_user_confirmation:
                vault.ingest(
                    topic="accounting.end_user_confirmation.ready",
                    category="accounting_end_user_confirmation",
                    payload=end_user_confirmation,
                )
                ingested += 1
            uk_brain = context.get("uk_accounting_requirements_brain") or {}
            evidence_authoring = context.get("accounting_evidence_authoring") or {}
            if evidence_authoring:
                vault.ingest(
                    topic="accounting.evidence.authoring.ready",
                    category="accounting_evidence",
                    payload=evidence_authoring,
                )
                ingested += 1
            if uk_brain:
                vault.ingest(
                    topic="accounting.uk_requirements.ready",
                    category="accounting_requirements",
                    payload=uk_brain,
                )
                ingested += 1
            for item in (context.get("deadlines") or {}).get("overdue", []):
                vault.ingest(
                    topic="accounting.deadline.overdue",
                    category="accounting_deadline",
                    payload=dict(item),
                )
                ingested += 1
            for year, data in (context.get("tax_years") or {}).items():
                vault.ingest(
                    topic=f"accounting.tax_year.{year.replace('/', '-')}",
                    category="accounting_year",
                    payload={"tax_year": year, **data},
                )
                ingested += 1
            for venue, data in (context.get("exchange_venues") or {}).items():
                vault.ingest(
                    topic=f"accounting.exchange.{venue}",
                    category="exchange_archive",
                    payload={"venue": venue, **(data or {})},
                )
                ingested += 1
            self._last_vault_signature = signature
        except Exception as exc:
            logger.debug("accounting bridge ingest_to_vault failed: %s", exc)
        return ingested

    def publish_status(self, thought_bus: Any, *, topic: str = "accounting.status") -> Dict[str, Any]:
        status = self.status()
        if thought_bus is not None and hasattr(thought_bus, "publish"):
            try:
                thought_bus.publish(topic, status, source="accounting_context_bridge")
            except TypeError:
                try:
                    from aureon.core.aureon_thought_bus import Thought

                    thought_bus.publish(
                        Thought(
                            source="accounting_context_bridge",
                            topic=topic,
                            payload=status,
                        )
                    )
                except Exception:
                    pass
            except Exception:
                pass
        return status

    def run_full_accounts(self, as_of: str | None = None, no_fetch: bool = True) -> Dict[str, Any]:
        paths = self._paths()
        script = paths["accounts_generator"]
        if not script.exists():
            result = {
                "status": "blocked",
                "reason": "accounts_generator_missing",
                "script": str(script),
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result("accounting.accounts.blocked", result)
            return result

        as_of_value = as_of or date.today().isoformat()
        cmd = [
            sys.executable,
            str(script),
            "--company-number",
            self.company_number,
            "--period-start",
            self.period_start,
            "--period-end",
            self.period_end,
            "--as-of",
            as_of_value,
        ]
        if no_fetch:
            cmd.append("--no-fetch")

        env = dict(os.environ)
        env["AUREON_ACCOUNTING_ON_DEMAND"] = "1"
        env["AUREON_DISABLE_GOVERNMENT_SUBMISSION"] = "1"
        env["AUREON_DISABLE_REAL_ORDERS"] = env.get("AUREON_DISABLE_REAL_ORDERS", "1")

        try:
            completed = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                env=env,
                text=True,
                capture_output=True,
                timeout=300,
                check=False,
            )
            self.load_context(force=True)
            result = {
                "status": "completed" if completed.returncode == 0 else "failed",
                "exit_code": completed.returncode,
                "command": cmd,
                "stdout": _clip(completed.stdout, 2000),
                "stderr": _clip(completed.stderr, 2000),
                "as_of": as_of_value,
                "no_fetch": bool(no_fetch),
                "summary": self.status(force=True),
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result(
                "accounting.accounts.generated" if completed.returncode == 0 else "accounting.accounts.blocked",
                result,
            )
            return result
        except Exception as exc:
            result = {
                "status": "blocked",
                "reason": f"{type(exc).__name__}: {exc}",
                "command": cmd,
                "as_of": as_of_value,
                "no_fetch": bool(no_fetch),
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result("accounting.accounts.blocked", result)
            return result

    def run_statutory_filing_pack(self) -> Dict[str, Any]:
        """Generate the local Companies House/HMRC final-ready manual filing pack only."""
        paths = self._paths()
        script = paths["statutory_generator"]
        if not script.exists():
            result = {
                "status": "blocked",
                "reason": "statutory_generator_missing",
                "script": str(script),
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result("accounting.statutory.blocked", result)
            return result

        context = self.load_context(force=True)
        company = context.get("company") or {}
        company_name = company.get("company_name") or "EXAMPLE TRADING LTD"
        cmd = [
            sys.executable,
            str(script),
            "--company-name",
            company_name,
            "--company-number",
            self.company_number,
            "--period-start",
            self.period_start,
            "--period-end",
            self.period_end,
        ]

        env = dict(os.environ)
        env["AUREON_ACCOUNTING_ON_DEMAND"] = "1"
        env["AUREON_DISABLE_GOVERNMENT_SUBMISSION"] = "1"
        env["AUREON_DISABLE_REAL_ORDERS"] = env.get("AUREON_DISABLE_REAL_ORDERS", "1")

        try:
            completed = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                env=env,
                text=True,
                capture_output=True,
                timeout=180,
                check=False,
            )
            self.load_context(force=True)
            result = {
                "status": "completed" if completed.returncode == 0 else "failed",
                "exit_code": completed.returncode,
                "command": cmd,
                "stdout": _clip(completed.stdout, 2000),
                "stderr": _clip(completed.stderr, 2000),
                "summary": self.status(force=True),
                "readiness": self.validate_accounting_readiness(force=True),
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result(
                "accounting.statutory.generated" if completed.returncode == 0 else "accounting.statutory.blocked",
                result,
            )
            return result
        except Exception as exc:
            result = {
                "status": "blocked",
                "reason": f"{type(exc).__name__}: {exc}",
                "command": cmd,
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result("accounting.statutory.blocked", result)
            return result

    def run_autonomous_full_accounts(
        self,
        *,
        as_of: str | None = None,
        no_fetch: bool = True,
        raw_data_roots: List[str] | None = None,
        include_default_roots: bool = True,
    ) -> Dict[str, Any]:
        """Run the safe raw-data-to-final-ready-accounts organism workflow."""
        paths = self._paths()
        script = paths["autonomous_workflow_runner"]
        if not script.exists():
            result = {
                "status": "blocked",
                "reason": "autonomous_workflow_runner_missing",
                "script": str(script),
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result("accounting.autonomous.accounts.blocked", result)
            return result

        context = self.load_context(force=True)
        company = context.get("company") or {}
        company_name = company.get("company_name") or "EXAMPLE TRADING LTD"
        as_of_value = as_of or date.today().isoformat()
        cmd = [
            sys.executable,
            str(script),
            "--company-name",
            company_name,
            "--company-number",
            self.company_number,
            "--period-start",
            self.period_start,
            "--period-end",
            self.period_end,
            "--as-of",
            as_of_value,
        ]
        if no_fetch:
            cmd.append("--no-fetch")
        if not include_default_roots:
            cmd.append("--no-default-roots")
        for raw_root in raw_data_roots or []:
            cmd.extend(["--raw-data-dir", str(raw_root)])

        env = dict(os.environ)
        env["AUREON_ACCOUNTING_ON_DEMAND"] = "1"
        env["AUREON_DISABLE_GOVERNMENT_SUBMISSION"] = "1"
        env["AUREON_DISABLE_REAL_ORDERS"] = env.get("AUREON_DISABLE_REAL_ORDERS", "1")

        try:
            completed = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                env=env,
                text=True,
                capture_output=True,
                timeout=360,
                check=False,
            )
            self.load_context(force=True)
            summary = self.status(force=True)
            result = {
                "status": "completed" if completed.returncode == 0 else "failed",
                "exit_code": completed.returncode,
                "command": cmd,
                "stdout": _clip(completed.stdout, 2000),
                "stderr": _clip(completed.stderr, 2000),
                "as_of": as_of_value,
                "no_fetch": bool(no_fetch),
                "raw_data_roots": list(raw_data_roots or []),
                "summary": summary,
                "readiness": summary.get("accounting_readiness") or {},
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result(
                "accounting.autonomous.accounts.completed"
                if completed.returncode == 0
                else "accounting.autonomous.accounts.blocked",
                result,
            )
            return result
        except Exception as exc:
            result = {
                "status": "blocked",
                "reason": f"{type(exc).__name__}: {exc}",
                "command": cmd,
                "as_of": as_of_value,
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result("accounting.autonomous.accounts.blocked", result)
            return result

    def run_end_user_accounting_automation(
        self,
        *,
        as_of: str | None = None,
        no_fetch: bool = True,
        raw_data_roots: List[str] | None = None,
        include_default_roots: bool = True,
        enable_cognitive_review: bool = True,
    ) -> Dict[str, Any]:
        """Run the top-level raw-data-in/accounts-pack-out end-user wrapper."""
        paths = self._paths()
        script = paths["end_user_accounting_automation_runner"]
        if not script.exists():
            result = {
                "status": "blocked",
                "reason": "end_user_accounting_automation_runner_missing",
                "script": str(script),
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result("accounting.end_user_accounts.blocked", result)
            return result

        context = self.load_context(force=True)
        company = context.get("company") or {}
        company_name = company.get("company_name") or "EXAMPLE TRADING LTD"
        as_of_value = as_of or date.today().isoformat()
        cmd = [
            sys.executable,
            str(script),
            "--company-name",
            company_name,
            "--company-number",
            self.company_number,
            "--period-start",
            self.period_start,
            "--period-end",
            self.period_end,
            "--as-of",
            as_of_value,
        ]
        if no_fetch:
            cmd.append("--no-fetch")
        if not include_default_roots:
            cmd.append("--no-default-roots")
        if not enable_cognitive_review:
            cmd.append("--skip-cognitive-review")
        for raw_root in raw_data_roots or []:
            cmd.extend(["--raw-data-dir", str(raw_root)])

        env = dict(os.environ)
        env["AUREON_ACCOUNTING_ON_DEMAND"] = "1"
        env["AUREON_DISABLE_GOVERNMENT_SUBMISSION"] = "1"
        env["AUREON_DISABLE_REAL_ORDERS"] = env.get("AUREON_DISABLE_REAL_ORDERS", "1")
        env["AUREON_LIVE_TRADING"] = env.get("AUREON_LIVE_TRADING", "0")

        try:
            completed = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                env=env,
                text=True,
                capture_output=True,
                timeout=480,
                check=False,
            )
            self.load_context(force=True)
            summary = self.status(force=True)
            result = {
                "status": "completed" if completed.returncode == 0 else "failed",
                "exit_code": completed.returncode,
                "command": cmd,
                "stdout": _clip(completed.stdout, 2000),
                "stderr": _clip(completed.stderr, 2000),
                "as_of": as_of_value,
                "no_fetch": bool(no_fetch),
                "raw_data_roots": list(raw_data_roots or []),
                "summary": summary,
                "end_user_accounting_automation": summary.get("end_user_accounting_automation") or {},
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result(
                "accounting.end_user_accounts.completed"
                if completed.returncode == 0
                else "accounting.end_user_accounts.blocked",
                result,
            )
            return result
        except Exception as exc:
            result = {
                "status": "blocked",
                "reason": f"{type(exc).__name__}: {exc}",
                "command": cmd,
                "as_of": as_of_value,
                "safety": self._manual_safety({}, {}),
            }
            self._publish_run_result("accounting.end_user_accounts.blocked", result)
            return result

    def _publish_run_result(self, topic: str, payload: Dict[str, Any]) -> None:
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus

            bus = get_thought_bus()
            if hasattr(bus, "publish"):
                bus.publish(topic, payload, source="accounting_context_bridge")
        except Exception:
            pass

    def snapshot(self) -> Dict[str, Any]:
        """Compatibility snapshot for health/audit surfaces."""
        try:
            status = self.status()
            status["reachable"] = status.pop("available", False)
            status["mode"] = "read_only_context_on_demand_build"
            return status
        except Exception as exc:
            return {"reachable": False, "error": str(exc)}


_bridge_singleton: AccountingContextBridge | None = None
_bridge_lock = threading.Lock()


def get_accounting_context_bridge() -> AccountingContextBridge:
    global _bridge_singleton
    with _bridge_lock:
        if _bridge_singleton is None:
            _bridge_singleton = AccountingContextBridge()
        return _bridge_singleton


def reset_accounting_context_bridge() -> None:
    global _bridge_singleton
    with _bridge_lock:
        _bridge_singleton = None


__all__ = [
    "ACCOUNTING_TOPICS",
    "AccountingContextBridge",
    "DEFAULT_COMPANY_NUMBER",
    "DEFAULT_PERIOD_END",
    "DEFAULT_PERIOD_START",
    "get_accounting_context_bridge",
    "reset_accounting_context_bridge",
]
