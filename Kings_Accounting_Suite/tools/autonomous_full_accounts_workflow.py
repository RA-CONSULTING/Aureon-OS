"""Coordinate raw data, cognition, and accounting tools into final-ready accounts.

The workflow is deliberately local and safe. It coordinates the accounting
engines, ThoughtBus, goal routing, and cognitive review surfaces, but it never
files Companies House accounts, submits HMRC returns, pays tax, or mutates
exchange/trading state. Aureon generates the complete manual filing document
pack; the human handles approval, upload/entry, submission, and payment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence


KAS_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = KAS_DIR.parent
TOOLS_DIR = KAS_DIR / "tools"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(KAS_DIR))
sys.path.insert(0, str(TOOLS_DIR))

from company_house_tax_audit import (  # noqa: E402
    DEFAULT_COMPANY_NAME,
    DEFAULT_COMPANY_NUMBER,
    DEFAULT_PERIOD_END,
    DEFAULT_PERIOD_START,
)
from company_raw_data_intake import (  # noqa: E402
    build_company_raw_data_manifest,
    write_raw_data_manifest_artifacts,
)
from generate_full_company_accounts import build_full_company_accounts  # noqa: E402
from accounting_handoff_pack import build_accounting_handoff_pack  # noqa: E402


ACCOUNTING_AUTONOMOUS_TOPICS = (
    "accounting.raw_data.ingested",
    "accounting.autonomous.accounts.started",
    "accounting.vault.memory.written",
    "accounting.cognitive.review.started",
    "accounting.cognitive.review.completed",
    "accounting.cognitive.review.blocked",
    "accounting.evidence.authoring.ready",
    "accounting.uk_requirements.ready",
    "accounting.handoff.generated",
    "accounting.handoff.blocked",
    "accounting.agent.task",
    "accounting.autonomous.accounts.completed",
    "accounting.autonomous.accounts.blocked",
)


@dataclass
class AccountingAgentTask:
    agent: str
    system: str
    objective: str
    status: str = "planned"
    evidence: list[str] = field(default_factory=list)
    output: str = ""
    safe_boundary: str = "final_ready_local_pack_no_external_submission"


def build_agent_plan() -> list[AccountingAgentTask]:
    return [
        AccountingAgentTask(
            agent="raw_data_intake_agent",
            system="company_raw_data_intake",
            objective="Inventory every raw company data file and route each one to transaction ingestion or evidence review.",
        ),
        AccountingAgentTask(
            agent="bank_normaliser_agent",
            system="combined_bank_data",
            objective="Normalise bank/account CSV and supported statement PDFs into one deduplicated period feed.",
        ),
        AccountingAgentTask(
            agent="ledger_gateway_agent",
            system="HNCGateway",
            objective="Run the accounts gateway over the combined feed and generate final-ready local reports.",
        ),
        AccountingAgentTask(
            agent="king_accounting_agent",
            system="KingLedger/KingAccounting",
            objective="Keep ledger, trial balance, P&L, tax, VAT/CIS, and report systems visible to the workflow.",
        ),
        AccountingAgentTask(
            agent="compliance_audit_agent",
            system="company_house_tax_audit",
            objective="Refresh local compliance deadlines and review evidence gaps without submitting anything.",
        ),
        AccountingAgentTask(
            agent="statutory_pack_agent",
            system="generate_statutory_filing_pack",
            objective="Prepare final-ready Companies House accounts, CT600 manual-entry JSON, tax computation, and iXBRL readiness notes.",
        ),
        AccountingAgentTask(
            agent="evidence_authoring_agent",
            system="accounting_evidence_authoring/ObsidianBridge/SelfQuestioningAI",
            objective=(
                "Generate internal evidence requests, petty-cash voucher templates, invoice prompts, receipt requests, "
                "and allocation memos without pretending they are external evidence."
            ),
        ),
        AccountingAgentTask(
            agent="uk_requirements_brain_agent",
            system="uk_accounting_requirements_brain/HNCLawDataset",
            objective=(
                "Ask accountant-style UK tax, VAT, UTR, Companies House, confirmation statement, PAYE, CIS, "
                "and source-data completeness questions from the generated evidence."
            ),
        ),
        AccountingAgentTask(
            agent="human_filing_handoff_agent",
            system="accounting_handoff_pack",
            objective=(
                "Copy raw evidence, combined data, workpapers, Companies House support, HMRC support, "
                "confirmation readiness, and manual form prompts into one human filing handoff pack."
            ),
        ),
        AccountingAgentTask(
            agent="cognitive_review_agent",
            system="GoalCapabilityMap/SelfQuestioningAI/ThoughtBus",
            objective=(
                "Route the accounting goal through Obsidian memory, Ollama/self-questioning, "
                "ThoughtBus, and safe next-action reasoning."
            ),
        ),
    ]


def run_autonomous_full_accounts_workflow(
    *,
    repo_root: str | Path = REPO_ROOT,
    company_name: str = DEFAULT_COMPANY_NAME,
    company_number: str = DEFAULT_COMPANY_NUMBER,
    period_start: str = DEFAULT_PERIOD_START,
    period_end: str = DEFAULT_PERIOD_END,
    as_of: date | None = None,
    raw_data_roots: Sequence[str | Path] | None = None,
    include_default_roots: bool = True,
    no_fetch: bool = True,
    enable_cognitive_review: bool = True,
    thought_bus: Any = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    as_of_value = as_of or date.today()
    started_at = datetime.now(timezone.utc).isoformat()
    env_snapshot = {
        "AUREON_AUDIT_MODE": os.getenv("AUREON_AUDIT_MODE"),
        "AUREON_LIVE_TRADING": os.getenv("AUREON_LIVE_TRADING"),
        "AUREON_DISABLE_REAL_ORDERS": os.getenv("AUREON_DISABLE_REAL_ORDERS"),
    }
    tasks = build_agent_plan()
    publish(thought_bus, "accounting.autonomous.accounts.started", {
        "company_number": company_number,
        "period_start": period_start,
        "period_end": period_end,
        "raw_data_roots": [str(path) for path in raw_data_roots or []],
    })

    raw_manifest = build_company_raw_data_manifest(
        root,
        company_number=company_number,
        period_start=period_start,
        period_end=period_end,
        raw_roots=raw_data_roots,
        include_default_roots=include_default_roots,
    )
    raw_json, raw_md = write_raw_data_manifest_artifacts(raw_manifest)
    complete_task(
        tasks,
        "raw_data_intake_agent",
        evidence=[str(raw_json), str(raw_md)],
        output=f"{raw_manifest.summary.get('file_count', 0)} raw files inventoried",
        thought_bus=thought_bus,
    )
    publish(thought_bus, "accounting.raw_data.ingested", raw_manifest.to_dict())

    goal_map = build_goal_map(root, company_name, company_number, period_start, period_end)

    result = build_full_company_accounts(
        company_name=company_name,
        company_number=company_number,
        period_start=period_start,
        period_end=period_end,
        as_of=as_of_value,
        no_fetch=no_fetch,
        raw_data_roots=raw_data_roots,
        include_default_roots=include_default_roots,
    )
    manifest = result.get("manifest") or {}
    source_inventory = manifest.get("source_data_inventory") or {}
    combined = source_inventory.get("combined_bank_data") or {}
    outputs = manifest.get("outputs") or {}
    statutory = manifest.get("statutory_filing_pack") or {}

    complete_task(
        tasks,
        "bank_normaliser_agent",
        evidence=[combined.get("combined_csv_path", "")],
        output=(
            f"{combined.get('transaction_source_count', combined.get('csv_source_count', 0))} sources, "
            f"{combined.get('unique_rows_in_period', 0)} unique period rows"
        ),
        thought_bus=thought_bus,
    )
    complete_task(
        tasks,
        "ledger_gateway_agent",
        evidence=[(outputs.get("accounts_pack_pdf") or {}).get("path", "")],
        output=f"accounts build {manifest.get('accounts_build', {}).get('status', result.get('status'))}",
        thought_bus=thought_bus,
    )
    complete_task(
        tasks,
        "king_accounting_agent",
        evidence=["accounting registry", "general ledger", "trial balance"],
        output="ledger/report/tax systems kept in workflow context",
        thought_bus=thought_bus,
    )
    complete_task(
        tasks,
        "compliance_audit_agent",
        evidence=[result.get("audit_json", ""), result.get("audit_markdown", "")],
        output="compliance audit refreshed",
        thought_bus=thought_bus,
    )
    complete_task(
        tasks,
        "statutory_pack_agent",
        evidence=[
            (
                ((statutory.get("outputs") or {}).get("ct600_manual_entry_json") or {})
                or ((statutory.get("outputs") or {}).get("hmrc_ct600_draft_json") or {})
            ).get("path", ""),
            ((statutory.get("outputs") or {}).get("filing_checklist") or {}).get("path", ""),
        ],
        output=f"{len(statutory.get('outputs') or {})} statutory/HMRC support outputs",
        thought_bus=thought_bus,
    )

    handoff_pack = run_handoff_pack(
        root,
        company_name=company_name,
        company_number=company_number,
        period_start=period_start,
        period_end=period_end,
        raw_data_roots=raw_data_roots,
        include_default_roots=include_default_roots,
        thought_bus=thought_bus,
    )
    handoff_readiness = handoff_pack.get("readiness") or {}
    evidence_authoring = handoff_pack.get("accounting_evidence_authoring") or {}
    evidence_summary = evidence_authoring.get("summary") or {}
    llm_authoring = evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
    publish(thought_bus, "accounting.evidence.authoring.ready", evidence_authoring)
    complete_task(
        tasks,
        "evidence_authoring_agent",
        evidence=[
            ((evidence_authoring.get("outputs") or {}).get("accounting_evidence_authoring_manifest") or ""),
            ((evidence_authoring.get("outputs") or {}).get("accounting_evidence_requests_csv") or ""),
        ],
        output=(
            f"requests={evidence_summary.get('draft_count', 0)} "
            f"documents={evidence_summary.get('generated_document_count', 0)} "
            f"petty_cash={evidence_summary.get('petty_cash_withdrawal_count', 0)} "
            f"llm_status={llm_authoring.get('status', 'unknown')} "
            f"llm_docs={llm_authoring.get('completed_count', 0)} "
            "internal_support_documents_only"
        ),
        thought_bus=thought_bus,
    )
    uk_requirements_brain = handoff_pack.get("uk_accounting_requirements_brain") or {}
    uk_summary = uk_requirements_brain.get("summary") or {}
    publish(thought_bus, "accounting.uk_requirements.ready", uk_requirements_brain)
    complete_task(
        tasks,
        "uk_requirements_brain_agent",
        evidence=[
            (((uk_requirements_brain.get("outputs") or {}).get("uk_accounting_requirements_brain_json") or "")),
            (((uk_requirements_brain.get("outputs") or {}).get("accountant_self_questions_markdown") or "")),
        ],
        output=(
            f"requirements={uk_summary.get('requirement_count', 0)} "
            f"questions={uk_summary.get('question_count', 0)} "
            f"unresolved={uk_summary.get('unresolved_question_count', 0)}"
        ),
        thought_bus=thought_bus,
    )
    complete_task(
        tasks,
        "human_filing_handoff_agent",
        evidence=[
            ((handoff_pack.get("outputs") or {}).get("manifest") or ""),
            ((handoff_pack.get("outputs") or {}).get("start_here") or ""),
        ],
        output=(
            f"handoff pack {handoff_pack.get('status', 'unknown')} "
            f"ready={handoff_readiness.get('ready_for_manual_review', 'unknown')}"
        ),
        thought_bus=thought_bus,
    )

    status = "completed" if result.get("status") == "completed" else "failed"
    review_context = {
        "schema_version": "autonomous-full-accounts-workflow-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started_at,
        "company_name": company_name,
        "company_number": company_number,
        "period_start": period_start,
        "period_end": period_end,
        "as_of": as_of_value.isoformat(),
        "status": status,
        "environment": env_snapshot,
        "raw_data_manifest": raw_manifest.to_dict(),
        "goal_capability_map": goal_map,
        "agent_tasks": [asdict(task) for task in tasks],
        "full_accounts_result": result,
        "human_filing_handoff_pack": handoff_pack,
        "accounting_evidence_authoring": evidence_authoring,
        "uk_accounting_requirements_brain": uk_requirements_brain,
        "thoughtbus_topics": list(ACCOUNTING_AUTONOMOUS_TOPICS),
        "safety": {
            "submits_to_companies_house": False,
            "submits_to_hmrc": False,
            "pays_tax_or_penalties": False,
            "mutates_exchange_or_trading_state": False,
            "requires_director_or_accountant_review": True,
            "manual_filing_required": True,
        },
    }
    vault_memory = write_accounting_vault_memory(review_context, root, thought_bus=thought_bus)
    review_context["vault_memory"] = vault_memory
    cognitive_review = run_cognitive_accounting_review(
        review_context,
        root,
        thought_bus=thought_bus,
        enabled=enable_cognitive_review,
    )
    complete_task(
        tasks,
        "cognitive_review_agent",
        evidence=[
            "goal_capability_map",
            str(vault_memory.get("note_path") or ""),
            str(cognitive_review.get("note_path") or ""),
            "ThoughtBus accounting cognitive topics",
        ],
        output=(
            f"self-questioning {cognitive_review.get('status', 'unknown')} "
            f"via {cognitive_review.get('answer_source', 'n/a')}"
        ),
        thought_bus=thought_bus,
    )
    workflow_manifest = {
        **review_context,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "agent_tasks": [asdict(task) for task in tasks],
        "vault_memory": vault_memory,
        "cognitive_review": cognitive_review,
        "human_filing_handoff_pack": handoff_pack,
        "accounting_evidence_authoring": evidence_authoring,
        "uk_accounting_requirements_brain": uk_requirements_brain,
    }
    workflow_manifest["vault_memory"] = write_accounting_vault_memory(
        workflow_manifest,
        root,
        thought_bus=thought_bus,
        update_index=False,
    )
    manifest_path, summary_path = write_workflow_artifacts(workflow_manifest, root)
    workflow_manifest["manifest_path"] = str(manifest_path)
    workflow_manifest["summary_path"] = str(summary_path)
    publish(
        thought_bus,
        "accounting.autonomous.accounts.completed" if status == "completed" else "accounting.autonomous.accounts.blocked",
        workflow_manifest,
    )
    return workflow_manifest


def complete_task(
    tasks: list[AccountingAgentTask],
    agent: str,
    *,
    evidence: list[str],
    output: str,
    thought_bus: Any,
) -> None:
    for task in tasks:
        if task.agent != agent:
            continue
        task.status = "completed"
        task.evidence = [item for item in evidence if item]
        task.output = output
        publish(thought_bus, "accounting.agent.task", asdict(task))
        return


def build_goal_map(
    repo_root: Path,
    company_name: str,
    company_number: str,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    goal = (
        f"Generate full final-ready accounts for {company_name} {company_number} "
        f"from all raw company data for {period_start} to {period_end}; "
        "route accounting, cognition, ThoughtBus, Obsidian, and safe manual filing review."
    )
    try:
        from aureon.autonomous.aureon_goal_capability_map import build_goal_capability_map

        return build_goal_capability_map(repo_root=repo_root, current_goal=goal).compact()
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "goal": goal}


def run_handoff_pack(
    repo_root: Path,
    *,
    company_name: str,
    company_number: str,
    period_start: str,
    period_end: str,
    raw_data_roots: Sequence[str | Path] | None,
    include_default_roots: bool,
    thought_bus: Any = None,
) -> dict[str, Any]:
    try:
        manifest = build_accounting_handoff_pack(
            repo_root=repo_root,
            company_name=company_name,
            company_number=company_number,
            period_start=period_start,
            period_end=period_end,
            raw_data_roots=raw_data_roots,
            include_default_roots=include_default_roots,
            copy_raw_evidence=True,
        )
        ready = bool((manifest.get("readiness") or {}).get("ready_for_manual_review"))
        manifest["status"] = "completed" if ready else "partial"
        publish(
            thought_bus,
            "accounting.handoff.generated" if ready else "accounting.handoff.blocked",
            manifest,
        )
        return manifest
    except Exception as exc:
        result = {
            "schema_version": "accounting-human-filing-handoff-v1",
            "status": "blocked",
            "reason": f"{type(exc).__name__}: {exc}",
            "readiness": {
                "ready_for_manual_review": False,
                "missing_requirements": ["handoff_pack_generation"],
            },
            "safe_boundaries": {
                "official_companies_house_filing": "manual_only",
                "official_hmrc_submission": "manual_only",
                "tax_or_penalty_payment": "manual_only",
            },
        }
        publish(thought_bus, "accounting.handoff.blocked", result)
        return result


def write_accounting_vault_memory(
    manifest: dict[str, Any],
    repo_root: Path,
    *,
    thought_bus: Any = None,
    update_index: bool = True,
) -> dict[str, Any]:
    """Persist the current accounts run as an Obsidian memory note."""
    company_number = str(manifest.get("company_number") or DEFAULT_COMPANY_NUMBER)
    period_start = str(manifest.get("period_start") or DEFAULT_PERIOD_START)
    period_end = str(manifest.get("period_end") or DEFAULT_PERIOD_END)
    note_path = f"accounting/workflows/{_note_slug(company_number)}_{period_start}_to_{period_end}.md"
    index_path = "accounting/full_accounts_index.md"
    try:
        from aureon.integrations.obsidian import ObsidianBridge, resolve_obsidian_vault_path

        vault_path = resolve_obsidian_vault_path()
        obsidian = ObsidianBridge(vault_path=str(vault_path), prefer_filesystem=True)
        if not obsidian.health_check():
            result = {
                "status": "blocked",
                "reason": "obsidian_unavailable",
                "note_path": note_path,
                "index_path": index_path,
            }
            publish(thought_bus, "accounting.vault.memory.written", result)
            return result
        body = render_accounting_vault_note(manifest)
        wrote = obsidian.write_note(note_path, body, overwrite=True)
        if update_index:
            obsidian.patch_section(
                index_path,
                "Latest Autonomous Accounts Runs",
                (
                    f"- `{datetime.now(timezone.utc).isoformat()}` "
                    f"`{company_number}` `{period_start} to {period_end}` "
                    f"status={manifest.get('status')} ([[{note_path}]])"
                ),
                operation="append",
            )
        result = {
            "status": "written" if wrote else "blocked",
            "mode": str(getattr(obsidian, "mode", "")),
            "vault_path": str(vault_path),
            "note_path": note_path,
            "index_path": index_path,
        }
        publish(thought_bus, "accounting.vault.memory.written", result)
        return result
    except Exception as exc:
        result = {
            "status": "blocked",
            "reason": f"{type(exc).__name__}: {exc}",
            "note_path": note_path,
            "index_path": index_path,
        }
        publish(thought_bus, "accounting.vault.memory.written", result)
        return result


def render_accounting_vault_note(manifest: dict[str, Any]) -> str:
    raw_summary = ((manifest.get("raw_data_manifest") or {}).get("summary") or {})
    result = manifest.get("full_accounts_result") or {}
    full_manifest = result.get("manifest") or {}
    source_inventory = full_manifest.get("source_data_inventory") or {}
    combined = source_inventory.get("combined_bank_data") or {}
    statutory = full_manifest.get("statutory_filing_pack") or {}
    requirement_summary = (statutory.get("government_requirements_matrix") or {}).get("summary") or {}
    providers = combined.get("source_provider_summary") or {}
    flows = combined.get("flow_provider_summary") or {}
    cognitive_review = manifest.get("cognitive_review") or {}
    handoff_pack = manifest.get("human_filing_handoff_pack") or {}
    handoff_readiness = handoff_pack.get("readiness") or {}
    evidence_authoring = manifest.get("accounting_evidence_authoring") or handoff_pack.get("accounting_evidence_authoring") or {}
    evidence_summary = evidence_authoring.get("summary") or {}
    llm_authoring = evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
    uk_brain = manifest.get("uk_accounting_requirements_brain") or handoff_pack.get("uk_accounting_requirements_brain") or {}
    uk_summary = uk_brain.get("summary") or {}
    uk_figures = uk_brain.get("figures") or {}
    lines = [
        "---",
        "aureon_accounting_memory: true",
        f"company_number: {manifest.get('company_number')}",
        f"period_start: {manifest.get('period_start')}",
        f"period_end: {manifest.get('period_end')}",
        f"status: {manifest.get('status')}",
        "---",
        "",
        f"# Autonomous Accounts Memory {manifest.get('company_number')}",
        "",
        "## What Aureon Used",
        "",
        f"- Raw files inventoried: {raw_summary.get('file_count', 0)}",
        f"- Transaction sources: {combined.get('transaction_source_count', combined.get('csv_source_count', 0))}",
        f"- CSV sources: {combined.get('csv_source_count', 0)}",
        f"- Parsed PDF sources: {combined.get('pdf_source_count', 0)}",
        f"- Unique period rows: {combined.get('unique_rows_in_period', 0)}",
        f"- Duplicate overlaps removed: {combined.get('duplicate_rows_removed', 0)}",
        f"- Statutory/HMRC support outputs: {len(statutory.get('outputs') or {})}",
        f"- Government requirement groups tracked: {requirement_summary.get('requirement_count', 0)}",
        f"- Human filing handoff: {handoff_pack.get('status', 'unknown')} ready={handoff_readiness.get('ready_for_manual_review', 'unknown')}",
        f"- Evidence authoring: requests={evidence_summary.get('draft_count', 0)} documents={evidence_summary.get('generated_document_count', 0)} petty_cash={evidence_summary.get('petty_cash_withdrawal_count', 0)} llm_status={llm_authoring.get('status', 'unknown')} llm_docs={llm_authoring.get('completed_count', 0)}",
        f"- UK accounting brain: requirements={uk_summary.get('requirement_count', 0)} questions={uk_summary.get('question_count', 0)} unresolved={uk_summary.get('unresolved_question_count', 0)}",
        f"- VAT threshold review: turnover_over_threshold={uk_figures.get('turnover_over_vat_threshold', 'unknown')}",
        f"- Handoff folder: {handoff_pack.get('output_dir') or 'not generated'}",
        "",
        "## Bank And Data Coverage",
        "",
    ]
    if providers:
        for name, info in sorted(providers.items()):
            lines.append(f"- Source provider `{name}`: rows={info.get('rows', 0)} files={info.get('files', 0)}")
    if flows:
        for name, info in sorted(flows.items()):
            lines.append(f"- Flow provider `{name}`: rows={info.get('rows', 0)} files={info.get('files', 0)}")
    if not providers and not flows:
        lines.append("- No provider summary was available in the combined bank manifest.")
    lines.extend(
        [
            "",
            "## Agents",
            "",
        ]
    )
    for task in manifest.get("agent_tasks") or []:
        lines.append(f"- `{task.get('agent')}` {task.get('status')}: {task.get('output')}")
    if handoff_pack:
        lines.extend(
            [
                "",
                "## Human Filing Handoff",
                "",
                f"- Status: {handoff_pack.get('status', 'unknown')}",
                f"- Ready for manual upload: {handoff_readiness.get('ready_for_manual_upload', handoff_readiness.get('ready_for_manual_review'))}",
                f"- Output folder: {handoff_pack.get('output_dir')}",
                f"- Manual inputs still required: {handoff_readiness.get('manual_inputs_required_count', 0)}",
            ]
        )
    if evidence_authoring:
        lines.extend(
            [
                "",
                "## Evidence Authoring",
                "",
                f"- Status: {evidence_authoring.get('status', 'unknown')}",
                f"- Evidence requests: {evidence_summary.get('draft_count', 0)}",
                f"- Internal document templates: {evidence_summary.get('generated_document_count', 0)}",
                f"- LLM document authoring: {llm_authoring.get('status', 'unknown')} generated={llm_authoring.get('completed_count', 0)} model={llm_authoring.get('model') or 'not selected'}",
                f"- Petty-cash withdrawals: {evidence_summary.get('petty_cash_withdrawal_count', 0)}",
                f"- Related-party/director queries: {evidence_summary.get('related_party_query_count', 0)}",
                "- Generated documents are not external evidence.",
            ]
        )
    if uk_brain:
        lines.extend(
            [
                "",
                "## UK Accounting Requirements Brain",
                "",
                f"- Status: {uk_brain.get('status', 'unknown')}",
                f"- Requirement groups: {uk_summary.get('requirement_count', 0)}",
                f"- Accountant self-questions: {uk_summary.get('question_count', 0)}",
                f"- Unresolved questions: {uk_summary.get('unresolved_question_count', 0)}",
                f"- Turnover over VAT threshold: {uk_figures.get('turnover_over_vat_threshold')}",
            ]
        )
    if cognitive_review:
        lines.extend(
            [
                "",
                "## Cognitive Review",
                "",
                f"- Status: {cognitive_review.get('status', 'unknown')}",
                f"- Source: {cognitive_review.get('answer_source', 'n/a')}",
                f"- Cycle note: {cognitive_review.get('note_path') or 'not written'}",
                f"- Summary: {cognitive_review.get('summary') or ''}",
            ]
        )
    lines.extend(
        [
            "",
            "## Safe Boundaries",
            "",
            "- Local final-ready accounts and compliance support only.",
            "- No Companies House filing was submitted.",
            "- No HMRC filing was submitted.",
            "- No tax payment or penalty payment was made.",
            "- Director/accountant review remains required before official filing.",
            "",
            "## Next Cognitive Question",
            "",
            (
                "Given the raw intake, bank normalisation, ledger gateway, statutory pack, "
                "evidence authoring pack, UK accounting requirements brain, and government requirement matrix, what evidence is still missing before manual filing review?"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def run_cognitive_accounting_review(
    manifest: dict[str, Any],
    repo_root: Path,
    *,
    thought_bus: Any = None,
    enabled: bool = True,
) -> dict[str, Any]:
    """Ask Aureon's self-questioning AI to reason over the accounts run."""
    if not enabled:
        result = {
            "status": "skipped",
            "reason": "disabled_by_caller",
            "answer_source": "skipped",
            "actions": [],
        }
        publish(thought_bus, "accounting.cognitive.review.blocked", result)
        return result

    company_number = str(manifest.get("company_number") or DEFAULT_COMPANY_NUMBER)
    period_start = str(manifest.get("period_start") or DEFAULT_PERIOD_START)
    period_end = str(manifest.get("period_end") or DEFAULT_PERIOD_END)
    publish(
        thought_bus,
        "accounting.cognitive.review.started",
        {
            "company_number": company_number,
            "period_start": period_start,
            "period_end": period_end,
        },
    )
    try:
        from aureon.autonomous.aureon_self_questioning_ai import SelfQuestioningAI

        ai = SelfQuestioningAI(repo_root=repo_root, safe_mode=True)
        questions = [
            (
                f"For {company_number} accounts {period_start} to {period_end}, "
                "which raw data, bank feeds, ledger systems, evidence authoring pack, UK requirements brain, statutory outputs, human filing handoff pack, "
                "vault memory, and ThoughtBus topics did I use?"
            ),
            (
                "What HMRC, VAT, UTR, Companies House, confirmation statement, receipts, invoices, petty-cash vouchers, accounting evidence, "
                "or reconciliation work remains before a human manual "
                "Companies House/HMRC filing review?"
            ),
            (
                "Which safe autonomous next actions can I take using only inspect, reconcile, "
                "generate the final-ready local pack, ingest to vault, publish status, or ask a human?"
            ),
        ]
        cycle = ai.run_cycle(
            questions=questions,
            include_audit=False,
            include_self_scan=False,
        )
        result = {
            "status": "completed",
            "cycle_id": cycle.cycle_id,
            "answer_source": cycle.answer_source,
            "summary": cycle.summary,
            "note_path": cycle.note_path,
            "actions": [asdict(action) for action in cycle.next_actions],
            "errors": cycle.errors,
        }
        publish(thought_bus, "accounting.cognitive.review.completed", result)
        return result
    except Exception as exc:
        result = {
            "status": "blocked",
            "reason": f"{type(exc).__name__}: {exc}",
            "answer_source": "blocked",
            "actions": [],
        }
        publish(thought_bus, "accounting.cognitive.review.blocked", result)
        return result


def _note_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "company"


def publish(thought_bus: Any, topic: str, payload: dict[str, Any]) -> None:
    bus = thought_bus
    if bus is None:
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus

            bus = get_thought_bus()
        except Exception:
            bus = None
    if bus is None or not hasattr(bus, "publish"):
        return
    try:
        bus.publish(topic, payload, source="accounting_autonomous_workflow")
    except TypeError:
        try:
            from aureon.core.aureon_thought_bus import Thought

            bus.publish(
                Thought(
                    source="accounting_autonomous_workflow",
                    topic=topic,
                    payload=payload,
                )
            )
        except Exception:
            pass
    except Exception:
        pass


def write_workflow_artifacts(manifest: dict[str, Any], repo_root: Path) -> tuple[Path, Path]:
    out_dir = (
        repo_root
        / "Kings_Accounting_Suite"
        / "output"
        / "company_compliance"
        / str(manifest.get("company_number") or DEFAULT_COMPANY_NUMBER)
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "autonomous_full_accounts_workflow_manifest.json"
    md_path = out_dir / "autonomous_full_accounts_workflow_summary.md"
    json_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8")

    raw_summary = ((manifest.get("raw_data_manifest") or {}).get("summary") or {})
    result = manifest.get("full_accounts_result") or {}
    full_manifest = result.get("manifest") or {}
    source_inventory = full_manifest.get("source_data_inventory") or {}
    combined = source_inventory.get("combined_bank_data") or {}
    statutory = full_manifest.get("statutory_filing_pack") or {}
    vault_memory = manifest.get("vault_memory") or {}
    cognitive_review = manifest.get("cognitive_review") or {}
    handoff_pack = manifest.get("human_filing_handoff_pack") or {}
    handoff_readiness = handoff_pack.get("readiness") or {}
    evidence_authoring = manifest.get("accounting_evidence_authoring") or handoff_pack.get("accounting_evidence_authoring") or {}
    evidence_summary = evidence_authoring.get("summary") or {}
    llm_authoring = evidence_authoring.get("llm_document_authoring") or evidence_summary.get("llm_document_authoring") or {}
    uk_brain = manifest.get("uk_accounting_requirements_brain") or handoff_pack.get("uk_accounting_requirements_brain") or {}
    uk_summary = uk_brain.get("summary") or {}
    lines = [
        "# Autonomous Full Accounts Workflow",
        "",
        f"- Generated: {manifest.get('generated_at')}",
        f"- Company: {manifest.get('company_number')} {manifest.get('company_name')}",
        f"- Period: {manifest.get('period_start')} to {manifest.get('period_end')}",
        f"- Status: {manifest.get('status')}",
        f"- Raw files inventoried: {raw_summary.get('file_count', 0)}",
        f"- Transaction sources: {combined.get('transaction_source_count', combined.get('csv_source_count', 0))}",
        f"- Unique period rows: {combined.get('unique_rows_in_period', 0)}",
        f"- Statutory/HMRC support outputs: {len(statutory.get('outputs') or {})}",
        f"- Human filing handoff: {handoff_pack.get('status', 'unknown')} ready={handoff_readiness.get('ready_for_manual_review', 'unknown')}",
        f"- Evidence authoring: requests={evidence_summary.get('draft_count', 0)} documents={evidence_summary.get('generated_document_count', 0)} llm_status={llm_authoring.get('status', 'unknown')} llm_docs={llm_authoring.get('completed_count', 0)}",
        f"- UK requirements brain: requirements={uk_summary.get('requirement_count', 0)} questions={uk_summary.get('question_count', 0)} unresolved={uk_summary.get('unresolved_question_count', 0)}",
        f"- Vault memory: {vault_memory.get('status', 'unknown')} {vault_memory.get('note_path', '')}".rstrip(),
        (
            f"- Cognitive review: {cognitive_review.get('status', 'unknown')} "
            f"via {cognitive_review.get('answer_source', 'n/a')} {cognitive_review.get('note_path', '')}"
        ).rstrip(),
        "",
        "## Agent Tasks",
        "",
    ]
    for task in manifest.get("agent_tasks") or []:
        lines.append(f"- {task.get('status')} `{task.get('agent')}` via {task.get('system')}: {task.get('output')}")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- Local final-ready accounts generation only.",
            "- No Companies House filing was submitted.",
            "- No HMRC filing was submitted.",
            "- No tax, penalty, exchange, or trading mutation was made.",
            "- Director/accountant review remains required before official filing.",
            "",
        ]
    )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the safe autonomous full-accounts workflow.")
    parser.add_argument("--company-name", default=DEFAULT_COMPANY_NAME)
    parser.add_argument("--company-number", default=DEFAULT_COMPANY_NUMBER)
    parser.add_argument("--period-start", default=DEFAULT_PERIOD_START)
    parser.add_argument("--period-end", default=DEFAULT_PERIOD_END)
    parser.add_argument("--as-of", default=date.today().isoformat())
    parser.add_argument("--raw-data-dir", action="append", default=[])
    parser.add_argument("--no-default-roots", action="store_true")
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--skip-cognitive-review", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = run_autonomous_full_accounts_workflow(
        company_name=args.company_name,
        company_number=args.company_number,
        period_start=args.period_start,
        period_end=args.period_end,
        as_of=date.fromisoformat(args.as_of),
        raw_data_roots=args.raw_data_dir,
        include_default_roots=not args.no_default_roots,
        no_fetch=args.no_fetch,
        enable_cognitive_review=not args.skip_cognitive_review,
    )
    print(manifest.get("manifest_path"))
    print(manifest.get("summary_path"))
    return 0 if manifest.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
