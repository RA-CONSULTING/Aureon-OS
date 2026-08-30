"""Repo-wide accounting capability and artifact registry.

The accounting codebase has several generations of tools: HNC gateway/reporting
engines, King's double-entry ledger, cash-flow analysis, workbook generators,
compliance audits, and the Aureon bridge. This scanner builds one safe,
machine-readable map without importing those modules or triggering side effects.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .combined_bank_data import combine_bank_data_for_period
except Exception:  # pragma: no cover - direct script execution fallback
    from combined_bank_data import combine_bank_data_for_period


DEFAULT_PERIOD_START = "2024-05-01"
DEFAULT_PERIOD_END = "2025-04-30"
DEFAULT_OUTPUT_JSON = Path("docs/audits/accounting_system_registry.json")
DEFAULT_OUTPUT_MD = Path("docs/audits/accounting_system_registry.md")

ACCOUNTING_TEST_TOOL_NAMES = {
    "build_full_picture.py",
    "generate_final_docs.py",
    "generate_full_workbook.py",
    "real_data_cleaned.py",
    "real_data_test.py",
    "sumup_analysis.py",
}

ACCOUNTING_AUREON_SYSTEM_NAMES = {
    "aureon_deep_money_flow_analyzer.py",
    "compound_king.py",
}

ACCOUNTING_ANALYTICS_NAMES = {
    "aureon_deep_money_flow_analyzer.py",
    "bitcoin_lighthouse_forensics.py",
    "lighthouse_financial_analyzer.py",
    "lighthouse_metrics.py",
}

ACCOUNTING_TRADING_REFERENCE_NAMES = {
    "compound_king.py",
}

TARGETED_ACCOUNTING_ARTIFACTS = (
    Path("data/exchange_account_archives/latest/coverage_report.json"),
)

SAFE_BOUNDARIES = {
    "official_companies_house_filing": "manual_only",
    "official_hmrc_submission": "manual_only",
    "tax_or_penalty_payment": "manual_only",
    "quickbooks_mutation": "signed_expiring_payload_bound_approval_required",
    "quickbooks_bank_or_billing_change": "manual_only",
    "exchange_or_trading_mutation": "blocked_from_accounting_registry",
}

DOMAIN_EXPLANATIONS = {
    "accounting_registry": "Discovery and inventory layer. Finds bank/account data, tools, generated packs, and safe/manual boundaries.",
    "external_accounting_platform": "Read-first QuickBooks OAuth/API control plane, reconciliation snapshots, audit receipts, and gated bookkeeping mutations.",
    "accounting_status_tools": "Small local display/check scripts for portfolio, live status, firm data, Kraken ledgers, and system flow.",
    "accounting_support": "Supporting intelligence, forecasting, hive, lattice, and unified accounting reasoning modules.",
    "cash_flow": "Money-flow analysis and local checks for how funds move through the business.",
    "cis": "Construction Industry Scheme classification, deduction, gross-up, and reconciliation logic.",
    "compliance_audit": "HMRC-style inspection, conscience, validation, risk, metacognition, and evidence stress testing.",
    "compound_projection": "Read-only compound, capital growth, and scenario projection harnesses for planning, not live execution.",
    "exchange_reconciliation": "Read-only balance/P&L/ledger checks for exchange-derived financial activity.",
    "financial_analysis": "Read-only money-flow, Lighthouse, market-forensic, and profit/capital analytics used as accounting intelligence.",
    "gateway_orchestration": "Top-level final-ready account build workflow that imports, processes, generates, and audits packs.",
    "invoice": "Invoice, line-item, party, payment-status, and PDF invoice generation logic.",
    "king_accounting": "Battlefield/tax intelligence registry for accounting decision support.",
    "ledger_double_entry": "Double-entry ledger, journal, King treasury, tax lot, P&L, portfolio, and trade accounting core.",
    "reports_exports": "P&L, balance sheet, cash flow, aged debtors, management accounts, tax summary, and export writers.",
    "tax_computation": "Tax, legal/rates data, strategy, cost basis, capital gains, Companies House/HMRC audit, and filing-pack preparation.",
    "tax_intelligence": "Tax battlefield intelligence, policy/risk scoring, and strategy prioritisation.",
    "transaction_import": "CSV/workbook import, clean-up, statement parsing, full-picture assembly, and legacy workbook generators.",
    "vat": "VAT/MTD return structures and HMRC API boundary code. Official submissions stay manual.",
}

WORKFLOW_STEPS = (
    (
        "1. Discover business evidence",
        "company_raw_data_intake inventories uploaded company folders, uploads, bussiness accounts, generated workbooks, King state data, gateway output, final packs, and compliance reports.",
    ),
    (
        "2. Combine bank/account exports",
        "combined_bank_data normalises every repo-held CSV source and supported statement PDF into Date/Description/Amount/Balance rows, removes overlapping exports, and keeps source-account evidence.",
    ),
    (
        "3. Import and normalise transactions",
        "hnc_import and the workbook/full-picture tools parse bank, card, crypto, statement, and legacy CSV formats into a common transaction shape.",
    ),
    (
        "4. Classify and reason",
        "hnc_categoriser, hnc_soup, hnc_metacognition, hnc_deep_scanner, hnc_intelligence_registry, and related systems classify income/expenses and explain the accounting treatment.",
    ),
    (
        "5. Build ledger and tax facts",
        "hnc_ledger, king_ledger, king_accounting, hnc_cost_basis, hnc_tax, hnc_vat, hnc_cis, hnc_invoice, and tax_strategy produce double-entry, P&L, cost basis, VAT/CIS/tax facts, and invoice data.",
    ),
    (
        "6. Generate final-ready accounts",
        "hnc_gateway orchestrates import -> Queen pipeline -> reports -> exports. build_period_accounts_pack and generate_full_company_accounts wrap that into the current company pack.",
    ),
    (
        "7. Produce human and machine artifacts",
        "hnc_reports and hnc_export write P&L, balance sheet, trial balance, general ledger, management accounts, tax summaries, PDFs, XLSX files, JSON manifests, and audit Markdown.",
    ),
    (
        "8. Audit compliance without filing",
        "company_house_tax_audit, hnc_hmrc_inspector, hnc_consciousness, hnc_auris_validator, and related checks flag deadlines, evidence gaps, risk, and human filing actions.",
    ),
    (
        "9. Feed Aureon's cognition",
        "AccountingContextBridge publishes status to ThoughtBus, ingests summaries to the vault, injects context into Queen prompts, and exposes /accounts commands.",
    ),
    (
        "10. Coordinate autonomous accounts workflow",
        "autonomous_full_accounts_workflow routes raw intake, bank normalisation, gateway reports, King accounting visibility, compliance audit, statutory pack generation, ThoughtBus, and cognitive goal routing as one safe local workflow.",
    ),
    (
        "11. Package end-user accounting automation",
        "end_user_accounting_automation is the raw-data-in/accounts-pack-out wrapper: it runs the autonomous workflow, maps outputs to HMRC and Companies House requirement coverage, and writes an end-user start-here pack.",
    ),
    (
        "12. Bridge nonstandard and mirrored accounting systems",
        "The registry also inventories misspelled/local data roots, accounting vault notes, Kings_Accounting_Suite/aureon_systems mirrors, aureon.bots King modules, compound projection harnesses, Lighthouse/Deep Money Flow analyzers, and exchange archive coverage as read-only accounting intelligence.",
    ),
    (
        "13. Reconcile the external QuickBooks ledger",
        "aureon_accounting_control_plane owns the evidence-bound double-entry journal, approval and projection queue; quickbooks_accounting_integration authorizes with OAuth, reads CompanyInfo/ledger/reports, hashes audit receipts, and blocks writes unless an expiring payload-bound approval passes every gate.",
    ),
)

GENERIC_BUSINESS_WORKFLOW = (
    "The core HNCGateway/UserProfile path is the generic business engine: give it an entity profile, accounting period, tax year, VAT/CIS flags, and raw data roots, then run in skip_hmrc=True mode to generate final-ready local accounts.",
    "The one-command wrappers accept company, period, and raw-data folder arguments while remaining preconfigured for R&A Consulting and Brokerage Services Ltd for 2024-05-01 to 2025-04-30.",
    "For any business, official Companies House filing, HMRC submission, tax payment, and penalty payment must stay human-reviewed and manual.",
)


@dataclass
class AccountingSystemEntry:
    id: str
    name: str
    path: str
    module: str
    domain: str
    role: str
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    has_main: bool = False
    safe_modes: list[str] = field(default_factory=list)
    external_mutation_risk: str = "none_detected"
    official_action: str = "no_official_submission"
    evidence: list[str] = field(default_factory=list)
    next_action: str = ""


@dataclass
class AccountingArtifact:
    path: str
    name: str
    kind: str
    bytes: int
    modified_at: str


@dataclass
class AccountingSystemRegistry:
    schema_version: str
    generated_at: str
    repo_root: str
    period_start: str
    period_end: str
    entries: list[AccountingSystemEntry]
    artifacts: list[AccountingArtifact]
    combined_bank_data: dict[str, Any]
    safe_boundaries: dict[str, str]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def compact(self, max_entries: int = 12, max_artifacts: int = 12) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "module_count": self.summary.get("module_count", 0),
            "artifact_count": self.summary.get("artifact_count", 0),
            "domain_counts": self.summary.get("domain_counts", {}),
            "mirrored_module_count": self.summary.get("mirrored_module_count", 0),
            "nonstandard_surfaces": self.summary.get("nonstandard_surfaces", {}),
            "runnable_tool_count": self.summary.get("runnable_tool_count", 0),
            "safe_boundaries": self.safe_boundaries,
            "combined_bank_data": {
                key: self.combined_bank_data.get(key)
                for key in (
                    "csv_source_count",
                    "pdf_source_count",
                    "transaction_source_count",
                    "evidence_file_count",
                    "rows_in_period_before_dedupe",
                    "unique_rows_in_period",
                    "duplicate_rows_removed",
                    "source_accounts",
                    "source_provider_summary",
                    "flow_provider_summary",
                    "combined_csv_path",
                )
                if key in self.combined_bank_data
            },
            "entries": [asdict(entry) for entry in self.entries[:max_entries]],
            "artifacts": [asdict(item) for item in self.artifacts[:max_artifacts]],
        }


def build_accounting_system_registry(
    repo_root: str | Path,
    *,
    period_start: str = DEFAULT_PERIOD_START,
    period_end: str = DEFAULT_PERIOD_END,
) -> AccountingSystemRegistry:
    root = Path(repo_root).resolve()
    entries = [scan_python_accounting_file(root, path) for path in discover_accounting_python_files(root)]
    entries.sort(key=lambda item: (item.domain, item.path.lower()))
    artifacts = discover_accounting_artifacts(root)
    computed_combined = combine_bank_data_for_period(root, period_start, period_end).to_summary()
    generated_combined = load_period_manifest_combined_summary(root, period_start, period_end)
    combined = prefer_fuller_combined_summary(computed_combined, generated_combined)
    summary = build_summary(entries, artifacts)
    return AccountingSystemRegistry(
        schema_version="accounting-system-registry-v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        repo_root=str(root),
        period_start=period_start,
        period_end=period_end,
        entries=entries,
        artifacts=artifacts,
        combined_bank_data=combined,
        safe_boundaries=dict(SAFE_BOUNDARIES),
        summary=summary,
    )


def load_period_manifest_combined_summary(
    repo_root: Path,
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    manifest_path = (
        repo_root
        / "Kings_Accounting_Suite"
        / "output"
        / "gateway"
        / f"{period_start}_to_{period_end}"
        / "period_pack_manifest.json"
    )
    try:
        if not manifest_path.exists():
            return {}
        manifest = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
        combined = manifest.get("combined_bank_data") or {}
        if not isinstance(combined, dict):
            return {}
        combined = dict(combined)
        combined.setdefault("combined_csv_path", str(
            manifest_path.parent / f"combined_bank_transactions_{period_start}_to_{period_end}.csv"
        ))
        combined["registry_summary_source"] = "period_pack_manifest"
        combined["period_manifest_path"] = str(manifest_path)
        return combined
    except Exception:
        return {}


def prefer_fuller_combined_summary(
    computed: dict[str, Any],
    generated: dict[str, Any],
) -> dict[str, Any]:
    """Prefer the existing full period pack when live parsing is dependency-limited."""
    if not generated:
        computed = dict(computed)
        computed["registry_summary_source"] = "live_scan"
        return computed
    computed_rows = int(computed.get("unique_rows_in_period") or 0)
    generated_rows = int(generated.get("unique_rows_in_period") or 0)
    computed_sources = int(computed.get("transaction_source_count", computed.get("csv_source_count", 0)) or 0)
    generated_sources = int(generated.get("transaction_source_count", generated.get("csv_source_count", 0)) or 0)
    if generated_rows >= computed_rows and generated_sources >= computed_sources:
        return dict(generated)
    computed = dict(computed)
    computed["registry_summary_source"] = "live_scan"
    computed["period_manifest_available"] = True
    return computed


def discover_accounting_python_files(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    direct_roots = [
        repo_root / "Kings_Accounting_Suite" / "core",
        repo_root / "Kings_Accounting_Suite" / "tools",
        repo_root / "Kings_Accounting_Suite" / "cash_flow",
        repo_root / "Kings_Accounting_Suite" / "ledger",
        repo_root / "Kings_Accounting_Suite" / "show_tools",
    ]
    for root in direct_roots:
        if root.exists():
            candidates.extend(path for path in root.rglob("*.py") if not is_skipped(path))

    tests_root = repo_root / "Kings_Accounting_Suite" / "tests"
    if tests_root.exists():
        candidates.extend(
            path
            for path in tests_root.glob("*.py")
            if path.name in ACCOUNTING_TEST_TOOL_NAMES and not is_skipped(path)
        )

    aureon_systems = repo_root / "Kings_Accounting_Suite" / "aureon_systems"
    if aureon_systems.exists():
        candidates.extend(
            path
            for path in aureon_systems.glob("*.py")
            if path.name.startswith("king_") or path.name in ACCOUNTING_AUREON_SYSTEM_NAMES
        )

    aureon_bots = repo_root / "aureon" / "bots"
    if aureon_bots.exists():
        candidates.extend(
            path
            for path in aureon_bots.glob("king_*.py")
            if not is_skipped(path)
        )

    aureon_analytics = repo_root / "aureon" / "analytics"
    if aureon_analytics.exists():
        candidates.extend(
            path
            for path in aureon_analytics.glob("*.py")
            if path.name in ACCOUNTING_ANALYTICS_NAMES and not is_skipped(path)
        )

    aureon_trading = repo_root / "aureon" / "trading"
    if aureon_trading.exists():
        candidates.extend(
            path
            for path in aureon_trading.glob("*.py")
            if path.name in ACCOUNTING_TRADING_REFERENCE_NAMES and not is_skipped(path)
        )

    scripts_roots = [repo_root / "scripts" / "diagnostics", repo_root / "scripts" / "validation"]
    for root in scripts_roots:
        if not root.exists():
            continue
        candidates.extend(
            path
            for path in root.glob("*.py")
            if is_accounting_related_name(path.name) and not is_skipped(path)
        )

    return sorted(set(candidates), key=lambda path: str(path).lower())


def scan_python_accounting_file(repo_root: Path, path: Path) -> AccountingSystemEntry:
    text = path.read_text(encoding="utf-8", errors="replace")
    classes: list[str] = []
    functions: list[str] = []
    parse_error = ""
    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
    except SyntaxError as exc:
        parse_error = f"syntax_error:{exc.lineno}"

    rel = path.relative_to(repo_root)
    has_main = (
        'if __name__ == "__main__"' in text
        or "if __name__ == '__main__'" in text
        or "show_tools" in rel.parts
    )
    domain = classify_domain(rel, text)
    role = classify_role(rel, text, has_main)
    external_risk = classify_external_risk(rel, text)
    safe_modes = classify_safe_modes(rel, text, role, external_risk)
    evidence = [
        f"classes={len(classes)}",
        f"functions={len(functions)}",
        f"main={has_main}",
    ]
    if parse_error:
        evidence.append(parse_error)
    if classes:
        evidence.append("top_classes=" + ", ".join(classes[:5]))
    if functions:
        evidence.append("top_functions=" + ", ".join(functions[:6]))

    return AccountingSystemEntry(
        id=stable_id(rel),
        name=path.stem,
        path=str(rel).replace("\\", "/"),
        module=module_name_from_path(rel),
        domain=domain,
        role=role,
        classes=classes[:12],
        functions=functions[:20],
        has_main=has_main,
        safe_modes=safe_modes,
        external_mutation_risk=external_risk,
        official_action="manual_only" if external_risk != "none_detected" else "no_official_submission",
        evidence=evidence,
        next_action=next_action_for(domain, role, external_risk),
    )


def discover_accounting_artifacts(repo_root: Path) -> list[AccountingArtifact]:
    roots = [
        repo_root / "Kings_Accounting_Suite" / "output",
        repo_root / "Kings_Accounting_Suite" / "data",
        repo_root / "Kings_Accounting_Suite" / "cash_flow",
        repo_root / "Kings_Accounting_Suite",
        repo_root / "accounting",
    ]
    suffixes = {".json", ".jsonl", ".xlsx", ".xls", ".pdf", ".csv", ".md"}
    artifacts: list[AccountingArtifact] = []
    for root in roots:
        if not root.exists():
            continue
        if root.name in {"output", "data", "cash_flow", "accounting"}:
            iterator = root.rglob("*")
        else:
            iterator = list(root.glob("*.xlsx")) + list(root.glob("*.md"))
        for path in iterator:
            if not path.is_file() or is_skipped(path) or path.suffix.lower() not in suffixes:
                continue
            stat = path.stat()
            artifacts.append(
                AccountingArtifact(
                    path=str(path.relative_to(repo_root)).replace("\\", "/"),
                    name=path.name,
                    kind=artifact_kind(path),
                    bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                )
            )
    for rel_target in TARGETED_ACCOUNTING_ARTIFACTS:
        path = repo_root / rel_target
        if path.exists() and path.is_file() and not is_skipped(path):
            stat = path.stat()
            artifacts.append(
                AccountingArtifact(
                    path=rel_target.as_posix(),
                    name=path.name,
                    kind=artifact_kind(path),
                    bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                )
            )
    artifacts.sort(key=lambda item: (item.kind, item.path.lower()))
    return artifacts


def build_summary(entries: list[AccountingSystemEntry], artifacts: list[AccountingArtifact]) -> dict[str, Any]:
    domains = Counter(entry.domain for entry in entries)
    roles = Counter(entry.role for entry in entries)
    artifact_kinds = Counter(item.kind for item in artifacts)
    mirrored_module_count = sum(
        1
        for entry in entries
        if any(
            marker in entry.path
            for marker in (
                "Kings_Accounting_Suite/aureon_systems/",
                "aureon/bots/",
                "aureon/analytics/",
                "aureon/trading/",
            )
        )
    )
    paths = {entry.path for entry in entries}
    artifact_paths = {item.path for item in artifacts}
    return {
        "module_count": len(entries),
        "class_count": sum(len(entry.classes) for entry in entries),
        "function_count": sum(len(entry.functions) for entry in entries),
        "runnable_tool_count": sum(1 for entry in entries if entry.has_main),
        "external_mutation_risk_count": sum(1 for entry in entries if entry.external_mutation_risk != "none_detected"),
        "domain_counts": dict(sorted(domains.items())),
        "role_counts": dict(sorted(roles.items())),
        "artifact_count": len(artifacts),
        "artifact_kind_counts": dict(sorted(artifact_kinds.items())),
        "official_filing_manual_only": True,
        "hmrc_submission_manual_only": True,
        "companies_house_submission_manual_only": True,
        "mirrored_module_count": mirrored_module_count,
        "nonstandard_surfaces": {
            "misspelled_business_accounts_dir": True,
            "accounting_vault_memory": any(path.startswith("accounting/") for path in artifact_paths),
            "exchange_archive_coverage_report": "data/exchange_account_archives/latest/coverage_report.json" in artifact_paths,
            "kings_aureon_systems_mirror": any(path.startswith("Kings_Accounting_Suite/aureon_systems/") for path in paths),
            "root_aureon_king_bots": any(path.startswith("aureon/bots/") for path in paths),
            "root_aureon_financial_analytics": any(path.startswith("aureon/analytics/") for path in paths),
            "root_aureon_compound_projection": "aureon/trading/compound_king.py" in paths,
        },
    }


def write_registry_artifacts(
    registry: AccountingSystemRegistry,
    *,
    json_path: str | Path = DEFAULT_OUTPUT_JSON,
    markdown_path: str | Path = DEFAULT_OUTPUT_MD,
) -> tuple[Path, Path]:
    json_out = Path(json_path)
    md_out = Path(markdown_path)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(registry.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    md_out.write_text(render_registry_markdown(registry), encoding="utf-8")
    return json_out, md_out


def render_registry_markdown(registry: AccountingSystemRegistry) -> str:
    summary = registry.summary
    entries_by_domain: dict[str, list[AccountingSystemEntry]] = {}
    for entry in registry.entries:
        entries_by_domain.setdefault(entry.domain, []).append(entry)

    lines = [
        "# Accounting System Registry",
        "",
        f"- Generated: {registry.generated_at}",
        f"- Period: {registry.period_start} to {registry.period_end}",
        f"- Modules/tools discovered: {summary.get('module_count', 0)}",
        f"- Runnable tool scripts: {summary.get('runnable_tool_count', 0)}",
        f"- Artifacts discovered: {summary.get('artifact_count', 0)}",
        f"- Classes discovered: {summary.get('class_count', 0)}",
        f"- Functions discovered: {summary.get('function_count', 0)}",
        "- Official filing/payment boundary: manual only",
        "",
        "## How The Accounting Organism Works Together",
        "",
    ]
    for title, detail in WORKFLOW_STEPS:
        lines.append(f"- {title}: {detail}")
    lines.extend(
        [
            "",
            "## Full Accounts For A Business",
            "",
        ]
    )
    for item in GENERIC_BUSINESS_WORKFLOW:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Combined Bank Data",
            "",
            f"- Transaction sources: {registry.combined_bank_data.get('transaction_source_count', registry.combined_bank_data.get('csv_source_count', 0))}",
            f"- CSV sources: {registry.combined_bank_data.get('csv_source_count', 0)}",
            f"- Parsed statement PDFs: {registry.combined_bank_data.get('pdf_source_count', 0)}",
            f"- Evidence files: {registry.combined_bank_data.get('evidence_file_count', 0)}",
            f"- Rows before dedupe: {registry.combined_bank_data.get('rows_in_period_before_dedupe', 0)}",
            f"- Unique period rows: {registry.combined_bank_data.get('unique_rows_in_period', 0)}",
            f"- Duplicate overlaps removed: {registry.combined_bank_data.get('duplicate_rows_removed', 0)}",
            f"- Source accounts: {', '.join(registry.combined_bank_data.get('source_accounts') or []) or 'none'}",
            "",
        ]
    )
    source_summary = registry.combined_bank_data.get("source_provider_summary") or {}
    if source_summary:
        lines.extend(["### Source Provider Rollup", ""])
        for provider, info in sorted(source_summary.items()):
            lines.append(
                f"- {provider}: {info.get('rows', 0)} rows; "
                f"in {info.get('money_in', '0.00')}; out {info.get('money_out', '0.00')}; net {info.get('net', '0.00')}"
            )
        lines.append("")
    flow_summary = registry.combined_bank_data.get("flow_provider_summary") or {}
    if flow_summary:
        lines.extend(["### Flow Provider Rollup", ""])
        for provider, info in sorted(flow_summary.items()):
            lines.append(
                f"- {provider}: {info.get('rows', 0)} rows; "
                f"in {info.get('money_in', '0.00')}; out {info.get('money_out', '0.00')}; net {info.get('net', '0.00')}"
            )
        lines.append("")
    lines.extend(["## Domains", ""])
    for domain, count in (summary.get("domain_counts") or {}).items():
        explanation = DOMAIN_EXPLANATIONS.get(domain, "Accounting support module group.")
        lines.append(f"- {domain}: {count} - {explanation}")
    lines.extend(["", "## Complete Accounting Module List", ""])
    for domain in sorted(entries_by_domain):
        lines.extend(["", f"### {domain}", ""])
        lines.append(DOMAIN_EXPLANATIONS.get(domain, "Accounting support module group."))
        lines.append("")
        for entry in entries_by_domain[domain]:
            risk = entry.external_mutation_risk
            classes = ", ".join(entry.classes[:6]) or "none"
            functions = ", ".join(entry.functions[:8]) or "none"
            lines.extend(
                [
                    f"- `{entry.path}`",
                    f"  - Role: {entry.role}",
                    f"  - Module: `{entry.module}`",
                    f"  - Classes: {classes}",
                    f"  - Functions: {functions}",
                    f"  - Runnable script: {entry.has_main}",
                    f"  - Safe modes: {', '.join(entry.safe_modes) or 'none'}",
                    f"  - External mutation risk: {risk}",
                    f"  - Official action: {entry.official_action}",
                    f"  - Next wiring action: {entry.next_action}",
                ]
            )
    lines.extend(["", "## Artifacts", ""])
    for item in registry.artifacts[:80]:
        lines.append(f"- `{item.path}` - {item.kind}; bytes={item.bytes}")
    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- No Companies House filing is automated by this registry.",
            "- No HMRC submission or payment is automated by this registry.",
            "- No exchange/trading mutation is allowed from accounting discovery.",
            "- Final-ready pack generation and local report refreshes remain on demand.",
            "",
        ]
    )
    return "\n".join(lines)


def classify_domain(rel: Path, text: str) -> str:
    blob = f"{rel.as_posix()} {text[:3000]}".lower()
    rel_text = rel.as_posix().lower()
    name = rel.name.lower()
    if "/show_tools/" in f"/{rel_text}":
        return "accounting_status_tools"
    if name in {"accounting_system_registry.py", "combined_bank_data.py", "company_raw_data_intake.py"}:
        return "accounting_registry"
    if name == "quickbooks_accounting_integration.py":
        return "external_accounting_platform"
    if name == "aureon_accounting_control_plane.py":
        return "ledger_double_entry"
    if name == "king_accounting.py":
        return "king_accounting"
    if name in {"king_ledger.py", "king_integration.py", "hnc_ledger.py"}:
        return "ledger_double_entry"
    if name == "hnc_intelligence_registry.py":
        return "tax_intelligence"
    if "/aureon/analytics/" in f"/{rel_text}" or name in ACCOUNTING_ANALYTICS_NAMES:
        return "financial_analysis"
    if name == "compound_king.py":
        return "compound_projection"
    rules = [
        ("gateway_orchestration", ("hnc_gateway", "build_period_accounts_pack", "generate_full_company_accounts", "autonomous_full_accounts_workflow", "end_user_accounting_automation")),
        ("transaction_import", ("hnc_import", "normalisedtransaction", "import_csv")),
        ("reports_exports", ("hnc_reports", "hnc_export", "generate_pnl", "trial_balance", "management_accounts")),
        ("ledger_double_entry", ("king_ledger", "hnc_ledger", "double-entry", "journalentry")),
        ("king_accounting", ("king_accounting", "royaltreasury", "theking", "taxlot")),
        ("tax_computation", ("hnc_tax", "tax_strategy", "corporation tax", "ct600", "cgt")),
        ("vat", ("hnc_vat", "vatreturn", "making tax digital")),
        ("cis", ("hnc_cis", "cis_reconciliation", "subcontractor", "cis300")),
        ("invoice", ("hnc_invoice", "invoice")),
        ("compliance_audit", ("company_house_tax_audit", "companies house", "company house", "hmrc")),
        ("cash_flow", ("cash_flow", "money_flow", "cash forecast")),
        ("data_generation", ("generate_full_workbook", "generate_final_docs", "build_full_picture", "real_data")),
        ("exchange_reconciliation", ("kraken_ledger", "balances", "pnl")),
        ("accounting_registry", ("accounting_system_registry", "combined_bank_data", "company_raw_data_intake")),
    ]
    for domain, keywords in rules:
        if any(keyword in blob for keyword in keywords):
            return domain
    return "accounting_support"


def classify_role(rel: Path, text: str, has_main: bool) -> str:
    blob = f"{rel.as_posix()} {text[:2000]}".lower()
    if rel.name.lower() == "aureon_accounting_control_plane.py":
        return "ledger_core"
    if "bridge" in blob:
        return "bridge"
    if "audit" in blob or "inspector" in blob:
        return "audit_or_probe"
    if "generate" in blob or "build_" in blob or "export_" in blob:
        return "final_ready_generation"
    if "reconcile" in blob or "check_" in blob:
        return "reconciliation"
    if "import" in blob or "parse_" in blob:
        return "data_import"
    if "ledger" in blob or "journal" in blob:
        return "ledger_core"
    if has_main:
        return "runnable_tool"
    return "library"


def classify_external_risk(rel: Path, text: str) -> str:
    blob = f"{rel.as_posix()} {text[:5000]}".lower()
    name = rel.name.lower()
    if name in {"accounting_system_registry.py", "combined_bank_data.py", "company_raw_data_intake.py"}:
        return "none_detected"
    if name == "quickbooks_accounting_integration.py":
        return "quickbooks_api_boundary"
    if "hmrc" in blob and any(word in blob for word in ("submit", "oauth", "api", "payment")):
        return "hmrc_submission_or_api_boundary"
    if "companies house" in blob and any(word in blob for word in ("submit", "file", "filing")):
        return "companies_house_filing_boundary"
    if any(word in blob for word in ("place_order", "add_order", "withdraw", "deposit", "exchange mutation")):
        return "exchange_mutation_boundary"
    return "none_detected"


def classify_safe_modes(rel: Path, text: str, role: str, external_risk: str) -> list[str]:
    modes = ["read_only_inventory"]
    if role in {"final_ready_generation", "runnable_tool"}:
        modes.append("final_ready_generation_on_demand")
    if role in {"audit_or_probe", "reconciliation", "data_import", "ledger_core"}:
        modes.append("local_analysis")
    if external_risk != "none_detected":
        modes.append("official_action_manual_only")
    return sorted(set(modes))


def next_action_for(domain: str, role: str, external_risk: str) -> str:
    if external_risk != "none_detected":
        return "Expose read-only status only; keep official action manual."
    if role == "final_ready_generation":
        return "Make available through AccountingContextBridge on explicit request."
    if domain == "gateway_orchestration" and "autonomous" in role:
        return "Use as the safe whole-organism entry point for raw-data-to-final-ready-accounts runs."
    if role in {"ledger_core", "reconciliation", "data_import"}:
        return "Use as supporting evidence and reconciliation logic for final-ready accounts."
    if domain in {"compound_projection", "financial_analysis"}:
        return "Keep read-only and feed planning, cash-flow, profit, and evidence context into accounting cognition."
    if domain in {"reports_exports", "gateway_orchestration"}:
        return "Keep wired to final-ready accounts pack generation."
    return "Keep inventoried for accounting cognition and future wiring."


def artifact_kind(path: Path) -> str:
    text = path.as_posix().lower()
    if "/accounting/" in f"/{text}" or text.startswith("accounting/"):
        return "accounting_vault_memory"
    if "exchange_account_archives/latest/coverage_report.json" in text:
        return "exchange_archive_coverage"
    if "company_compliance" in text:
        return "company_compliance"
    if "/gateway/" in text:
        return "gateway_output"
    if "/final/" in text:
        return "final_pack"
    if "/data/" in text:
        return "king_state_data"
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return "workbook"
    if path.suffix.lower() == ".pdf":
        return "pdf"
    return path.suffix.lower().lstrip(".") or "artifact"


def stable_id(rel: Path) -> str:
    return re.sub(r"[^a-z0-9]+", ".", rel.with_suffix("").as_posix().lower()).strip(".")


def module_name_from_path(rel: Path) -> str:
    return ".".join(rel.with_suffix("").parts)


def is_skipped(path: Path) -> bool:
    return any(part in {"__pycache__", ".pytest_cache", ".git", "node_modules"} for part in path.parts)


def is_accounting_related_name(name: str) -> bool:
    lowered = name.lower()
    return any(
        word in lowered
        for word in (
            "account",
            "ledger",
            "tax",
            "vat",
            "hmrc",
            "balance",
            "pnl",
            "cash",
            "statement",
            "financial",
            "money",
            "flow",
            "profit",
            "compound",
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the unified accounting system registry.")
    parser.add_argument("--repo-root", default=str(Path.cwd()))
    parser.add_argument("--period-start", default=DEFAULT_PERIOD_START)
    parser.add_argument("--period-end", default=DEFAULT_PERIOD_END)
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    registry = build_accounting_system_registry(
        args.repo_root,
        period_start=args.period_start,
        period_end=args.period_end,
    )
    json_path, md_path = write_registry_artifacts(
        registry,
        json_path=args.json,
        markdown_path=args.markdown,
    )
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(
        "Accounting modules: "
        f"{registry.summary.get('module_count', 0)}; "
        f"artifacts: {registry.summary.get('artifact_count', 0)}; "
        f"bank sources: {registry.combined_bank_data.get('transaction_source_count', registry.combined_bank_data.get('csv_source_count', 0))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
