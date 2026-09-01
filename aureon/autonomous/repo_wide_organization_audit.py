"""Repo-wide staged organization audit for the Aureon organism.

This audit is intentionally read-only. It answers a different question from the
mind wiring audit: not "does this module import?" but "where does every part of
the repo belong in the organism, what looks loose, and what needs staging before
the whole system can be treated as organized?"
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence


SCHEMA_VERSION = "aureon-repo-wide-organization-audit-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/repo_wide_organization_audit.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/repo_wide_organization_audit.json")

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
    "venv",
}

GENERATED_PARTS = {
    "build",
    "dist",
    "output",
    "outputs",
    "coverage",
    "htmlcov",
}

RUNTIME_STATE_SUFFIXES = {
    ".log",
    ".jsonl",
}

SECRET_RISK_NAMES = {
    ".env",
    ".env1.txt",
}

SECRET_RISK_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "credential",
    "token",
    "password",
    "private_key",
)

CONTRACT_CHECKS = {
    "boot_ignition": "scripts/aureon_ignition.py",
    "organism_spine": "aureon/core/aureon_organism_spine.py",
    "organism_contracts": "aureon/core/organism_contracts.py",
    "thought_bus": "aureon/core/aureon_thought_bus.py",
    "integrated_cognitive_system": "aureon/core/integrated_cognitive_system.py",
    "mind_wiring_audit": "aureon/autonomous/mind_wiring_audit.py",
    "goal_capability_map": "aureon/autonomous/aureon_goal_capability_map.py",
    "self_questioning_ai": "aureon/autonomous/aureon_self_questioning_ai.py",
    "accounting_bridge": "aureon/queen/accounting_context_bridge.py",
    "accounting_system_registry": "Kings_Accounting_Suite/tools/accounting_system_registry.py",
    "accounting_full_workflow": "Kings_Accounting_Suite/tools/end_user_accounting_automation.py",
    "payer_provenance": "Kings_Accounting_Suite/tools/accounting_payer_provenance.py",
    "frontend_manifest": "frontend/package.json",
    "repo_tests": "tests",
    "audit_docs": "docs/audits",
}


@dataclass(frozen=True)
class StageRule:
    stage: str
    domain: str
    role: str
    prefixes: tuple[str, ...] = ()
    exact: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()
    markers: tuple[str, ...] = ()

    def matches_direct(self, rel_path: str) -> bool:
        lower = rel_path.lower()
        name = Path(rel_path).name.lower()
        if lower in self.exact or name in self.exact:
            return True
        if any(lower.startswith(prefix) for prefix in self.prefixes):
            return True
        return any(lower.endswith(suffix) for suffix in self.suffixes)

    def matches_marker(self, rel_path: str) -> bool:
        return any(marker in rel_path.lower() for marker in self.markers)

    def matches(self, rel_path: str) -> bool:
        return self.matches_direct(rel_path) or self.matches_marker(rel_path)


STAGE_RULES: tuple[StageRule, ...] = (
    StageRule(
        "00_boot_and_runtime_entrypoints",
        "boot",
        "Launchers, deployment files, ignition scripts, and operator entrypoints.",
        prefixes=("scripts/", "deploy/", "packaging/", "aureon_launcher/", ".github/"),
        exact=("procfile", "runtime.txt", "dockerfile", "docker-compose.yml", "docker-compose.autonomous.yml", "supervisord.conf", "app.yaml"),
    ),
    StageRule(
        "01_core_contracts_and_bus",
        "core",
        "Shared organism contracts, safety gates, ThoughtBus, spine, environment, and cognitive runtime glue.",
        prefixes=("aureon/core/",),
        markers=("thought_bus", "contract", "organism_spine", "runtime_safety", "aureon_env"),
    ),
    StageRule(
        "02_cognition_memory_and_models",
        "cognition",
        "Queen, cognition, LLM, Obsidian, memory, BeingModel, world-sense, and internal reasoning surfaces.",
        prefixes=(
            "aureon/alignment/",
            "aureon/cognition/",
            "aureon/inhouse_ai/",
            "aureon/intelligence/",
            "aureon/queen/",
            "aureon/vault/",
            "memory/",
            ".obsidian/",
            "queen_configs/",
            "queen_research/",
            "queen_strategies/",
            "queen_backups/",
            "wisdom_data/",
        ),
        markers=("queen", "brain", "mind", "cogn", "conscious", "obsidian", "ollama", "llm", "memory"),
    ),
    StageRule(
        "03_autonomy_goals_agents_and_contract_queues",
        "autonomy",
        "Autonomous goals, self-questioning, agents, work-order queues, task routing, and action hubs.",
        prefixes=("aureon/autonomous/", "autonomy/", "skills/"),
        markers=("goal", "agent", "autonomous", "self_question", "work_order", "queue", "task"),
    ),
    StageRule(
        "04_trading_market_execution_and_risk",
        "trading",
        "Market data, exchange adapters, trading decision engines, risk sizing, state reconciliation, and live gates.",
        prefixes=(
            "aureon/exchanges/",
            "aureon/trading/",
            "aureon/data_feeds/",
            "aureon/monitors/",
            "data/exchange_account_archives/",
        ),
        markers=("kraken", "alpaca", "binance", "trade", "trading", "market", "ticker", "margin", "portfolio", "exchange"),
    ),
    StageRule(
        "05_accounting_tax_compliance_and_raw_business_data",
        "accounting",
        "Accounting suite, bank feeds, uploads, ledgers, Companies House/HMRC support packs, VAT, CIS, and compliance data.",
        prefixes=("kings_accounting_suite/", "accounting/", "uploads/", "bussiness accounts/"),
        markers=("account", "ledger", "hmrc", "companies_house", "ct600", "vat", "cis", "paye", "invoice", "receipt", "filing"),
    ),
    StageRule(
        "06_frontend_apis_and_operator_interfaces",
        "interface",
        "Frontend UI, public assets, API/server endpoints, Supabase/Netlify surfaces, and command-center screens.",
        prefixes=("frontend/", "public/", "api/", "server/", "functions/", "netlify/", "supabase/", "aureon/command_centers/"),
        suffixes=(".tsx", ".jsx", ".ts", ".js", ".css", ".html"),
        markers=("dashboard", "command_center", "ui"),
    ),
    StageRule(
        "06b_aureon_package_misc_and_compatibility_wrappers",
        "core",
        "Aureon package files that are not in a narrower subsystem folder yet, including compatibility wrappers and package glue.",
        prefixes=("aureon/",),
    ),
    StageRule(
        "07_tests_benchmarks_and_validation",
        "validation",
        "Unit tests, smoke tests, stress tests, benchmarks, external validation evidence, and verification documents.",
        prefixes=("tests/", "verification and validation/"),
        markers=("test_", "benchmark", "stress", "verification", "validation"),
    ),
    StageRule(
        "08_docs_audits_and_architecture_knowledge",
        "knowledge",
        "Human-readable docs, architecture maps, audits, whitepapers, and repo operating knowledge.",
        prefixes=("docs/",),
        suffixes=(".md", ".pdf", ".docx"),
        exact=("readme.md", "running.md", "quick_start.md", "capabilities.md", "data_flow.md", "audit_summary.md", "swot_analysis.md", "live_proof.md", "index.md", "claude.md"),
    ),
    StageRule(
        "09_runtime_state_logs_and_generated_outputs",
        "runtime_state",
        "Runtime logs, generated caches, local state snapshots, and history files that must be preserved but controlled.",
        prefixes=("logs/", "state/", "harmonic_cache/", "ws_cache/", "data/"),
        suffixes=(".log", ".jsonl"),
        markers=("history.json", "state.json", "cache", "snapshot", "thoughts.jsonl"),
    ),
    StageRule(
        "10_devops_config_and_repo_metadata",
        "devops",
        "Git, Docker, linting, dependency, deployment, and local environment metadata.",
        exact=(".gitignore", ".dockerignore", ".env", ".env1.txt", ".env.example", "requirements.txt", "eslint.config.js", "package.json", "package-lock.json"),
        prefixes=(".claude/", ".clawdhub/", ".do/", "cli/", "production/", "tools/"),
        suffixes=(".yaml", ".yml", ".toml", ".ini"),
    ),
    StageRule(
        "11_archives_imports_templates_and_legacy_snapshots",
        "archive",
        "Historical imports, legacy snapshots, templates, design assets, and archived recovery materials.",
        prefixes=("archive/", "imports/", "templates/"),
        suffixes=(".zip", ".patch", ".backup", ".working"),
        markers=("archive", "snapshot", "template"),
    ),
    StageRule(
        "12_root_compatibility_wrappers_and_visual_assets",
        "legacy_root",
        "Loose root-level launch helpers, compatibility wrappers, visual assets, and historical top-level utilities retained for compatibility.",
        exact=(
            "antarctic_4d_panels.png",
            "aureon_animal_momentum_scanners.py",
            "aureon_baton_link.py",
            "aureon_bot_intelligence_profiler.py",
            "aureon_chirp_bus.py",
            "aureon_elephant_learning.py",
            "aureon_harmonic_seed.py",
            "aureon_hft_harmonic_mycelium.py",
            "aureon_lighthouse.py",
            "aureon_mycelium.py",
            "aureon_probability_nexus.py",
            "aureon_whale_behavior_predictor.py",
            "boot_result.txt",
            "bot_army_catalog.json",
            "capital_diag.py",
            "conftest.py",
            "dockerfile.ephemeris",
            "headless_watch.py",
            "lattice_simulation.png",
            "license",
            "lighthouse_metrics.py",
            "prime_sentinel_decree.py",
            "probability_intelligence_matrix.py",
            "probability_ultimate_intelligence.py",
            "run_dj_resonance.py",
            "run_hnc_live.py",
            "untitled.canvas",
            "use_cases.py",
            "watch_log.txt",
        ),
    ),
)


@dataclass
class FileStageRecord:
    path: str
    stage: str
    domain: str
    role: str
    bytes: int
    suffix: str
    generated_or_cache: bool = False
    runtime_state: bool = False
    secret_risk: bool = False
    attention: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ContractSurfaceRecord:
    id: str
    path: str
    status: str
    stage: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepoWideOrganizationAudit:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    summary: dict[str, Any]
    stage_counts: dict[str, int]
    domain_counts: dict[str, int]
    contract_surfaces: list[ContractSurfaceRecord]
    attention_items: list[str]
    records: list[FileStageRecord]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "summary": self.summary,
            "stage_counts": self.stage_counts,
            "domain_counts": self.domain_counts,
            "contract_surfaces": [item.to_dict() for item in self.contract_surfaces],
            "attention_items": list(self.attention_items),
            "records": [record.to_dict() for record in self.records],
            "notes": list(self.notes),
        }


def repo_root_from(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "aureon").is_dir() and (candidate / "scripts").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def rel_to_posix(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def should_skip(path: Path, root: Path) -> bool:
    try:
        rel_parts = path.resolve().relative_to(root.resolve()).parts
    except ValueError:
        return True
    return any(part in SKIP_DIRS for part in rel_parts)


def iter_repo_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if should_skip(path, root):
            continue
        if path.is_file():
            yield path


def is_generated_or_cache(rel_path: str) -> bool:
    parts = set(Path(rel_path).parts)
    lower = rel_path.lower()
    return bool(parts & GENERATED_PARTS) or "/output/" in lower or lower.endswith(".pyc")


def is_runtime_state(path: Path, rel_path: str) -> bool:
    name = path.name.lower()
    lower = rel_path.lower()
    return (
        path.suffix.lower() in RUNTIME_STATE_SUFFIXES
        or name.endswith("_state.json")
        or name.endswith("_history.json")
        or name.endswith("_snapshot.json")
        or lower.startswith(("logs/", "state/", "harmonic_cache/", "ws_cache/"))
        or lower == "thoughts.jsonl"
    )


def is_secret_risk(path: Path, rel_path: str) -> bool:
    lower = rel_path.lower()
    name = path.name.lower()
    if name in SECRET_RISK_NAMES:
        return True
    return any(marker in lower for marker in SECRET_RISK_MARKERS)


def classify_path(path: Path, root: Path) -> FileStageRecord:
    rel_path = rel_to_posix(path, root)
    lower = rel_path.lower()
    generated = is_generated_or_cache(lower)
    runtime_state = is_runtime_state(path, lower)
    secret_risk = is_secret_risk(path, lower)

    # Directory ownership is stronger evidence than fuzzy keyword markers.
    # For example, an accounting output named "autonomous_full_accounts..." must
    # stay in the accounting stage because it lives under Kings_Accounting_Suite.
    matched = next((rule for rule in STAGE_RULES if rule.matches_direct(lower)), None)
    if matched is None:
        matched = next((rule for rule in STAGE_RULES if rule.matches_marker(lower)), None)
    attention: list[str] = []
    if matched is None:
        stage = "99_unstaged_or_needs_owner"
        domain = "unknown"
        role = "No stage rule matched; needs an owner or explicit route."
        attention.append("unstaged_path")
    else:
        stage = matched.stage
        domain = matched.domain
        role = matched.role

    if secret_risk:
        attention.append("secret_or_credential_surface")
    if runtime_state and not stage.startswith("09_"):
        attention.append("runtime_state_outside_runtime_stage")
    if generated and not stage.startswith("09_") and not stage.startswith("05_"):
        attention.append("generated_output_inside_source_area")
    if rel_path.count("/") == 0 and matched is None:
        attention.append("loose_repo_root_file")
    if lower.startswith("bussiness accounts/"):
        attention.append("legacy_misspelled_business_data_root_preserved")

    return FileStageRecord(
        path=rel_path,
        stage=stage,
        domain=domain,
        role=role,
        bytes=path.stat().st_size,
        suffix=path.suffix.lower(),
        generated_or_cache=generated,
        runtime_state=runtime_state,
        secret_risk=secret_risk,
        attention=attention,
    )


def contract_stage_for(path: str, records_by_path: dict[str, FileStageRecord]) -> str:
    record = records_by_path.get(path)
    return record.stage if record else "missing"


def build_contract_surface_records(root: Path, records_by_path: dict[str, FileStageRecord]) -> list[ContractSurfaceRecord]:
    surfaces: list[ContractSurfaceRecord] = []
    for surface_id, rel_path in CONTRACT_CHECKS.items():
        target = root / rel_path
        exists = target.exists()
        if exists:
            status = "present"
            evidence = "path exists"
        else:
            status = "missing"
            evidence = "path missing"
        surfaces.append(
            ContractSurfaceRecord(
                id=surface_id,
                path=rel_path,
                status=status,
                stage=contract_stage_for(rel_path, records_by_path) if target.is_file() else ("directory" if target.is_dir() else "missing"),
                evidence=evidence,
            )
        )
    return surfaces


def _top_paths(records: Sequence[FileStageRecord], predicate: str, limit: int = 20) -> list[str]:
    matched = [record.path for record in records if predicate in record.attention]
    return matched[:limit]


def build_audit(repo_root: Optional[Path] = None, max_records: int = 20000) -> RepoWideOrganizationAudit:
    root = repo_root_from(repo_root)
    records = [classify_path(path, root) for path in iter_repo_files(root)]
    records.sort(key=lambda item: item.path.lower())
    total_records = len(records)
    truncated = False
    if max_records > 0 and len(records) > max_records:
        records = records[:max_records]
        truncated = True

    records_by_path = {record.path: record for record in records}
    stage_counts = Counter(record.stage for record in records)
    domain_counts = Counter(record.domain for record in records)
    attention_counts = Counter(attention for record in records for attention in record.attention)
    contract_surfaces = build_contract_surface_records(root, records_by_path)

    missing_contracts = [surface.id for surface in contract_surfaces if surface.status != "present"]
    unstaged_count = stage_counts.get("99_unstaged_or_needs_owner", 0)
    secret_count = attention_counts.get("secret_or_credential_surface", 0)
    runtime_outside_count = attention_counts.get("runtime_state_outside_runtime_stage", 0)
    generated_source_count = attention_counts.get("generated_output_inside_source_area", 0)

    attention_items: list[str] = []
    if missing_contracts:
        attention_items.append(f"Missing critical contract surfaces: {', '.join(missing_contracts)}")
    if unstaged_count:
        attention_items.append(f"{unstaged_count} files do not map to a known organism stage.")
    if secret_count:
        attention_items.append(f"{secret_count} credential/secret-risk surfaces exist; audit recorded paths only and did not read values.")
    if runtime_outside_count:
        attention_items.append(f"{runtime_outside_count} runtime/state files sit outside the runtime-state stage.")
    if generated_source_count:
        attention_items.append(f"{generated_source_count} generated/cache outputs sit inside source stages.")
    if truncated:
        attention_items.append(f"Manifest records truncated to {len(records)} of {total_records} discovered files.")

    if missing_contracts:
        status = "blocked_missing_contract_surfaces"
    elif unstaged_count or runtime_outside_count or generated_source_count:
        status = "organized_with_attention_items"
    else:
        status = "organized"

    summary = {
        "total_discovered_files": total_records,
        "recorded_files": len(records),
        "truncated": truncated,
        "stage_count": len(stage_counts),
        "domain_count": len(domain_counts),
        "unstaged_file_count": unstaged_count,
        "secret_risk_surface_count": secret_count,
        "runtime_state_file_count": sum(1 for record in records if record.runtime_state),
        "generated_or_cache_file_count": sum(1 for record in records if record.generated_or_cache),
        "attention_counts": dict(sorted(attention_counts.items())),
        "sample_unstaged_paths": _top_paths(records, "unstaged_path"),
        "sample_secret_surfaces": _top_paths(records, "secret_or_credential_surface"),
        "sample_runtime_state_outside_stage": _top_paths(records, "runtime_state_outside_runtime_stage"),
        "sample_generated_source_outputs": _top_paths(records, "generated_output_inside_source_area"),
    }

    notes = [
        "Read-only organization audit: no files are moved, deleted, submitted, paid, or traded.",
        "The audit stages code, data, generated outputs, state, docs, tests, and interfaces into a single organism map.",
        "Secret-risk files are identified by path/name only; values are not read into the report.",
        "The legacy 'bussiness accounts' data root is preserved and explicitly mapped as business/accounting evidence.",
        "Official filing, payments, and live exchange mutation remain outside this organization audit.",
    ]

    return RepoWideOrganizationAudit(
        schema_version=SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        repo_root=str(root),
        status=status,
        summary=summary,
        stage_counts=dict(sorted(stage_counts.items())),
        domain_counts=dict(sorted(domain_counts.items())),
        contract_surfaces=contract_surfaces,
        attention_items=attention_items,
        records=records,
        notes=notes,
    )


def render_markdown(report: RepoWideOrganizationAudit) -> str:
    lines: list[str] = []
    lines.append("# Aureon Repo-Wide Organization Audit")
    lines.append("")
    lines.append(f"- Generated: `{report.generated_at}`")
    lines.append(f"- Repo: `{report.repo_root}`")
    lines.append(f"- Status: `{report.status}`")
    lines.append("- Safety: read-only; no live trading, filing, payment, or external mutation")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in (
        "total_discovered_files",
        "recorded_files",
        "unstaged_file_count",
        "secret_risk_surface_count",
        "runtime_state_file_count",
        "generated_or_cache_file_count",
    ):
        lines.append(f"- `{key}`: {report.summary.get(key, 0)}")
    lines.append("")

    lines.append("## Organism Stages")
    lines.append("")
    lines.append("| Stage | Files | Purpose |")
    lines.append("| --- | ---: | --- |")
    purpose_by_stage = {rule.stage: rule.role for rule in STAGE_RULES}
    purpose_by_stage["99_unstaged_or_needs_owner"] = "Needs a named owner/stage before the repo can be considered fully organized."
    for stage, count in report.stage_counts.items():
        purpose = purpose_by_stage.get(stage, "")
        lines.append(f"| `{stage}` | {count} | {purpose} |")
    lines.append("")

    lines.append("## Domains")
    lines.append("")
    lines.append("| Domain | Files |")
    lines.append("| --- | ---: |")
    for domain, count in report.domain_counts.items():
        lines.append(f"| `{domain}` | {count} |")
    lines.append("")

    lines.append("## Contract Surfaces")
    lines.append("")
    lines.append("| Surface | Status | Stage | Path |")
    lines.append("| --- | --- | --- | --- |")
    for surface in report.contract_surfaces:
        lines.append(f"| `{surface.id}` | `{surface.status}` | `{surface.stage}` | `{surface.path}` |")
    lines.append("")

    if report.attention_items:
        lines.append("## Attention Items")
        lines.append("")
        for item in report.attention_items:
            lines.append(f"- {item}")
        lines.append("")

    samples = (
        ("Unstaged Path Samples", "sample_unstaged_paths"),
        ("Secret-Risk Surface Samples", "sample_secret_surfaces"),
        ("Runtime State Outside Runtime Stage Samples", "sample_runtime_state_outside_stage"),
        ("Generated Output In Source Stage Samples", "sample_generated_source_outputs"),
    )
    for title, key in samples:
        values = report.summary.get(key) or []
        if not values:
            continue
        lines.append(f"## {title}")
        lines.append("")
        for value in values:
            lines.append(f"- `{value}`")
        lines.append("")

    lines.append("## Staging Checklist")
    lines.append("")
    checklist = [
        "Keep ignition behind `scripts/bootstrap/protected_bootstrap_v05.py --target-id ignition`; it remains HOLD.",
        "Keep core contracts, ThoughtBus, runtime safety, and organism spine in `aureon/core`.",
        "Keep accounting/code-generated compliance packs under `Kings_Accounting_Suite` and business evidence under explicit raw-data roots.",
        "Keep runtime state, generated logs, and giant memory files in controlled state/output locations.",
        "Assign every remaining root-level helper or historical artifact to a stage, archive, or documented compatibility wrapper.",
        "Do not move `.env`, API keys, portfolio state, exchange state, accounting evidence, or generated filing packs automatically.",
    ]
    for item in checklist:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: RepoWideOrganizationAudit,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
) -> tuple[Path, Path]:
    root = Path(report.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    md_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(report), encoding="utf-8")
    js_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return md_path, js_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's repo-wide staged organization audit.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to the current Aureon repo.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--max-records", type=int, default=20000, help="Maximum file records to keep in JSON; 0 means no limit.")
    parser.add_argument("--no-write", action="store_true", help="Print a JSON summary without writing artifacts.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    report = build_audit(root, max_records=args.max_records)
    if not args.no_write:
        md_path, js_path = write_report(report, Path(args.markdown), Path(args.json))
        print(json.dumps({"status": report.status, "markdown": str(md_path), "json": str(js_path), "summary": report.summary}, indent=2))
    else:
        print(json.dumps({"status": report.status, "summary": report.summary}, indent=2))
    return 2 if report.status.startswith("blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
