"""Aureon's file-by-file self-catalog.

The repo-wide organization audit answers "where does this file belong?".
This catalog goes one level deeper and gives Aureon a stable self-description
for every project file: what it is, what subsystem owns it, how it is used,
whether it is source/data/state/generated output, and how the vault/LLM layers
should reason about it.

The scanner is read-only. It never reads secret values into the manifest, never
executes files, and records dependency/cache roots as directory-level
infrastructure instead of pretending they are organism source.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

from aureon.obsidian_paths import resolve_obsidian_note_path
from aureon.autonomous.repo_wide_organization_audit import (
    SKIP_DIRS,
    classify_path,
    repo_root_from as organization_repo_root_from,
)


SCHEMA_VERSION = "aureon-repo-self-catalog-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_repo_self_catalog.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_repo_self_catalog.json")
DEFAULT_OUTPUT_CSV = Path("docs/audits/aureon_repo_self_catalog.csv")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/repo_self_catalog.md")

MAX_SAMPLE_BYTES = 64 * 1024
MAX_AST_BYTES = 512 * 1024

TEXT_SUFFIXES = {
    ".bat",
    ".cfg",
    ".conf",
    ".css",
    ".csv",
    ".env",
    ".example",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".jsx",
    ".md",
    ".py",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

DATA_SUFFIXES = {
    ".csv",
    ".db",
    ".json",
    ".jsonl",
    ".pdf",
    ".xls",
    ".xlsm",
    ".xlsx",
}

DOCUMENT_SUFFIXES = {".doc", ".docx", ".md", ".pdf", ".rtf", ".txt"}
IMAGE_SUFFIXES = {".gif", ".ico", ".jpg", ".jpeg", ".png", ".svg", ".webp"}
ARCHIVE_SUFFIXES = {".7z", ".gz", ".rar", ".tar", ".zip"}

SECRET_NAMES = {".env", ".env1.txt"}
SECRET_MARKERS = ("secret", "api_key", "apikey", "token", "password", "credential", "private_key")

RUNTIME_NAMES = {
    "thoughts.jsonl",
    "adaptive_learning_history.json",
    "brain_predictions_history.json",
    "miner_brain_knowledge.json",
    "real_portfolio_state.json",
    "queen_elephant_memory.json",
}

DOMAIN_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("accounting", ("account", "ledger", "hmrc", "companies", "ct600", "vat", "cis", "paye", "invoice", "receipt", "bank", "sumup", "zempler", "revolut")),
    ("trading", ("trade", "trader", "kraken", "exchange", "market", "ticker", "portfolio", "margin", "alpaca", "binance", "capital")),
    ("cognition", ("cogn", "conscious", "sentien", "meaning", "resolver", "brain", "mind", "queen", "hive", "thought")),
    ("vault_memory", ("vault", "obsidian", "memory", "knowledge", "jsonl", "history")),
    ("llm", ("llm", "ollama", "model", "prompt", "inhouse_ai", "adapter")),
    ("autonomy", ("autonomous", "goal", "agent", "task", "job", "contract", "work_order", "queue", "self_question", "self_enhance")),
    ("frontend", ("frontend", "dashboard", "ui", "tsx", "jsx", "css", "public", "command_center")),
    ("research", ("research", "paper", "whitepaper", "docs", "knowledge", "source", "corpus")),
    ("validation", ("test", "benchmark", "stress", "audit", "validation", "verification")),
    ("devops", ("docker", "deploy", "github", "netlify", "supabase", "requirements", "package", "eslint", "procfile")),
)

PATH_USE_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("scripts/",), ("operator boot", "ignition preflight", "single-start surface")),
    (("aureon/core/",), ("organism runtime", "ThoughtBus/contracts", "boot glue")),
    (("aureon/autonomous/", "autonomy/"), ("autonomous goals", "self-questioning", "work-order routing")),
    (("aureon/queen/", "aureon/cognition/", "aureon/intelligence/"), ("cognitive reasoning", "Queen/model context", "meaning resolution")),
    (("aureon/inhouse_ai/", "aureon/integrations/ollama/"), ("LLM adapter", "local model reasoning", "prompt execution")),
    (("aureon/vault/", ".obsidian/", "memory/"), ("vault memory", "recall", "long-term context")),
    (("aureon/exchanges/", "aureon/trading/", "aureon/data_feeds/"), ("trading decision path", "market/exchange context", "risk gate")),
    (("Kings_Accounting_Suite/", "accounting/", "uploads/", "bussiness accounts/"), ("accounting workflow", "business evidence", "accounts pack generation")),
    (("frontend/", "public/", "api/", "server/", "functions/", "netlify/"), ("operator interface", "frontend/API surface", "dashboard")),
    (("tests/",), ("test suite", "regression proof", "safe validation")),
    (("docs/",), ("knowledge base", "architecture/audit memory", "operator documentation")),
)


@dataclass
class PythonSymbols:
    module: str = ""
    docstring: str = ""
    classes: list[str] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    parse_error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FileSelfLabel:
    id: str
    path: str
    name: str
    extension: str
    size_bytes: int
    modified_utc: str
    subsystem: str
    organism_stage: str
    organism_domain: str
    file_kind: str
    role: str
    used_by: list[str]
    semantic_tags: list[str]
    read_status: str
    content_fingerprint: str
    data_sensitivity: str
    safety_flags: list[str]
    python_symbols: PythonSymbols
    llm_context: str
    vault_route: str
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["python_symbols"] = self.python_symbols.to_dict()
        return data


@dataclass
class ExcludedInfrastructureRoot:
    path: str
    reason: str
    catalog_status: str = "directory_level_only"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DirectorySummary:
    path: str
    file_count: int
    total_bytes: int
    dominant_subsystem: str
    dominant_kind: str
    domains: dict[str, int]
    kinds: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RepoSelfCatalog:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    summary: dict[str, Any]
    domain_counts: dict[str, int]
    subsystem_counts: dict[str, int]
    file_kind_counts: dict[str, int]
    sensitivity_counts: dict[str, int]
    directory_summaries: list[DirectorySummary]
    excluded_infrastructure_roots: list[ExcludedInfrastructureRoot]
    labels: list[FileSelfLabel]
    vault_memory: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "summary": self.summary,
            "domain_counts": self.domain_counts,
            "subsystem_counts": self.subsystem_counts,
            "file_kind_counts": self.file_kind_counts,
            "sensitivity_counts": self.sensitivity_counts,
            "directory_summaries": [item.to_dict() for item in self.directory_summaries],
            "excluded_infrastructure_roots": [item.to_dict() for item in self.excluded_infrastructure_roots],
            "labels": [label.to_dict() for label in self.labels],
            "vault_memory": dict(self.vault_memory),
            "notes": list(self.notes),
        }

    def compact(self, max_labels: int = 20) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "summary": self.summary,
            "domain_counts": self.domain_counts,
            "subsystem_counts": self.subsystem_counts,
            "file_kind_counts": self.file_kind_counts,
            "vault_memory": self.vault_memory,
            "sample_labels": [label.to_dict() for label in self.labels[:max_labels]],
        }


def repo_root_from(start: Optional[Path] = None) -> Path:
    if start is not None:
        return Path(start).resolve()
    return organization_repo_root_from(start)


def iter_project_files(root: Path) -> Iterable[Path]:
    """Yield project files while pruning dependency/cache internals early."""

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        try:
            rel_current = current.relative_to(root)
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in rel_current.parts):
            dirnames[:] = []
            continue
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
        for name in filenames:
            yield current / name


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "unknown"


def _normalise_ws(value: str, limit: int = 280) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _is_secret_surface(path: Path, rel_path: str) -> bool:
    lower = rel_path.lower()
    return path.name.lower() in SECRET_NAMES or any(marker in lower for marker in SECRET_MARKERS)


def _module_from_python_path(rel_path: str) -> str:
    return ".".join(Path(rel_path).with_suffix("").parts)


def _read_sample(path: Path, rel_path: str, secret: bool) -> tuple[str, str, str]:
    if secret:
        return "", "metadata_only_secret", ""
    suffix = path.suffix.lower()
    try:
        size = path.stat().st_size
    except OSError:
        return "", "unreadable_metadata", ""
    if suffix not in TEXT_SUFFIXES and suffix:
        digest = _sample_digest(path)
        return "", "binary_metadata", digest
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_SAMPLE_BYTES)
    except OSError as exc:
        return "", f"unreadable:{type(exc).__name__}", ""
    digest = hashlib.sha256(raw).hexdigest()[:16] if raw else ""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except UnicodeDecodeError:
            return "", "binary_or_unknown_encoding", digest
    if size > MAX_SAMPLE_BYTES:
        return text, "sampled_text", digest
    return text, "read_text_sample", digest


def _sample_digest(path: Path) -> str:
    try:
        with path.open("rb") as handle:
            return hashlib.sha256(handle.read(MAX_SAMPLE_BYTES)).hexdigest()[:16]
    except OSError:
        return ""


def _python_symbols(path: Path, rel_path: str, secret: bool) -> PythonSymbols:
    if path.suffix.lower() != ".py" or secret:
        return PythonSymbols(module=_module_from_python_path(rel_path) if path.suffix.lower() == ".py" else "")
    try:
        if path.stat().st_size > MAX_AST_BYTES:
            return PythonSymbols(module=_module_from_python_path(rel_path), parse_error="too_large_for_ast_probe")
        text = path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(text)
    except Exception as exc:
        return PythonSymbols(module=_module_from_python_path(rel_path), parse_error=f"{type(exc).__name__}: {exc}")

    imports: list[str] = []
    classes: list[str] = []
    functions: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module if node.level == 0 else f"{'.' * node.level}{module}")
    return PythonSymbols(
        module=_module_from_python_path(rel_path),
        docstring=_normalise_ws(ast.get_docstring(tree) or "", 360),
        classes=classes[:16],
        functions=functions[:24],
        imports=sorted({item for item in imports if item})[:24],
    )


def infer_file_kind(path: Path, rel_path: str, stage_record: Any) -> str:
    lower = rel_path.lower()
    suffix = path.suffix.lower()
    if lower.startswith("tests/") or path.name.startswith("test_"):
        return "test_or_benchmark"
    if suffix == ".py":
        return "python_source"
    if suffix in {".ts", ".tsx", ".js", ".jsx", ".css", ".html"}:
        return "frontend_source"
    if path.name.lower() in {"requirements.txt", "package.json", "package-lock.json", "dockerfile", "docker-compose.yml"}:
        return "dependency_or_deployment_config"
    if _is_secret_surface(path, rel_path):
        return "local_secret_or_environment_config"
    if getattr(stage_record, "runtime_state", False) or path.name.lower() in RUNTIME_NAMES:
        return "runtime_state_or_memory"
    if getattr(stage_record, "generated_or_cache", False):
        return "generated_output_or_cache"
    if lower.startswith("docs/audits/") and suffix in {".csv", ".json", ".md"}:
        return "audit_manifest_or_index"
    if (
        lower.startswith((".claude/", ".clawdhub/", ".do/", ".github/"))
        or getattr(stage_record, "domain", "") == "devops"
    ) and suffix in {".json", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf"}:
        return "configuration"
    if lower.startswith(("uploads/", "bussiness accounts/", "accounting/", "kings_accounting_suite/output/")):
        return "data_or_business_evidence"
    if suffix in {".json", ".jsonl"}:
        return "structured_manifest_or_memory"
    if suffix in DATA_SUFFIXES:
        return "data_or_business_evidence"
    if suffix in DOCUMENT_SUFFIXES:
        return "documentation_or_report"
    if suffix in IMAGE_SUFFIXES:
        return "visual_asset"
    if suffix in ARCHIVE_SUFFIXES:
        return "archive_or_bundle"
    if suffix in {".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf"}:
        return "configuration"
    return "misc_project_file"


def infer_subsystem(rel_path: str, stage_record: Any) -> str:
    lower = rel_path.lower()
    stage_domain = getattr(stage_record, "domain", "") or ""
    if lower.startswith("aureon/vault/") or lower.startswith(".obsidian/") or lower.startswith("memory/"):
        return "vault_memory"
    if lower.startswith(("aureon/inhouse_ai/", "aureon/integrations/ollama/")):
        return "llm_reasoning"
    if lower.startswith(("aureon/autonomous/", "autonomy/")):
        return "autonomy_and_self_management"
    if lower.startswith(("aureon/queen/", "aureon/cognition/", "aureon/intelligence/")):
        return "cognitive_queen_brain"
    if lower.startswith(("aureon/exchanges/", "aureon/trading/", "aureon/data_feeds/", "aureon/monitors/")):
        return "trading_and_market_risk"
    if lower.startswith(("kings_accounting_suite/", "accounting/", "uploads/", "bussiness accounts/")):
        return "accounting_tax_and_business_data"
    if lower.startswith(("frontend/", "public/", "api/", "server/", "functions/", "netlify/", "supabase/")):
        return "operator_interface_and_api"
    if lower.startswith(("tests/", "verification and validation/")):
        return "validation_and_benchmarking"
    if lower.startswith(("docs/",)) or Path(rel_path).suffix.lower() in DOCUMENT_SUFFIXES:
        return "knowledge_and_documentation"
    if lower.startswith(("scripts/", "deploy/", ".github/", "packaging/")):
        return "boot_devops_and_deployment"
    if stage_domain:
        return stage_domain
    return "general_project_surface"


def infer_domain(rel_path: str, stage_record: Any, subsystem: str) -> str:
    haystack = f"{rel_path} {subsystem} {getattr(stage_record, 'role', '')}".lower()
    for domain, markers in DOMAIN_MARKERS:
        if any(marker in haystack for marker in markers):
            return domain
    return getattr(stage_record, "domain", "") or subsystem or "unknown"


def infer_used_by(rel_path: str, file_kind: str, subsystem: str) -> list[str]:
    lower = rel_path.lower()
    used: list[str] = []
    for prefixes, surfaces in PATH_USE_RULES:
        if any(lower.startswith(prefix.lower()) for prefix in prefixes):
            used.extend(surfaces)
    if file_kind == "runtime_state_or_memory":
        used.extend(["runtime recall", "audit history", "state reconciliation"])
    if file_kind == "local_secret_or_environment_config":
        used.extend(["local boot configuration", "credential lookup by runtime only"])
    if subsystem == "accounting_tax_and_business_data":
        used.extend(["UK accounts generation", "evidence reconciliation"])
    if subsystem == "trading_and_market_risk":
        used.extend(["safe trading simulation/live-gated trading"])
    return sorted(dict.fromkeys(used)) or ["repo self-catalog", "operator inspection"]


def _tokens_from_path(rel_path: str, limit: int = 14) -> list[str]:
    text = re.sub(r"[^a-zA-Z0-9]+", " ", rel_path).lower()
    stop = {"aureon", "py", "json", "md", "txt", "the", "and", "suite", "test", "tests"}
    tokens = [token for token in text.split() if len(token) > 2 and token not in stop]
    return sorted(dict.fromkeys(tokens))[:limit]


def infer_role(rel_path: str, file_kind: str, subsystem: str, symbols: PythonSymbols, stage_role: str) -> str:
    subject = " ".join(_tokens_from_path(Path(rel_path).stem.replace("_", " "))) or Path(rel_path).stem
    if symbols.docstring:
        return symbols.docstring
    if file_kind == "python_source":
        return f"Executable Python logic for {subject} in the {subsystem} subsystem."
    if file_kind == "test_or_benchmark":
        return f"Validation coverage for {subject}; proves behavior without live external mutation."
    if file_kind == "frontend_source":
        return f"Frontend/operator interface asset for {subject}."
    if file_kind == "data_or_business_evidence":
        return f"Business, accounting, or structured data evidence used by {subsystem}."
    if file_kind == "audit_manifest_or_index":
        return f"Audit/index manifest that records self-knowledge or verification evidence for {subsystem}."
    if file_kind == "structured_manifest_or_memory":
        return f"Structured manifest, registry, or memory surface used by {subsystem}."
    if file_kind == "runtime_state_or_memory":
        return f"Runtime state or long-memory file preserved for recall/reconciliation by {subsystem}."
    if file_kind == "local_secret_or_environment_config":
        return "Local environment/secret surface; catalog records metadata only and never stores values."
    if file_kind == "documentation_or_report":
        return f"Knowledge/report document for {subject}."
    if stage_role:
        return stage_role
    return f"Project file associated with {subsystem}."


def infer_sensitivity(path: Path, rel_path: str, file_kind: str, stage_record: Any) -> str:
    lower = rel_path.lower()
    if _is_secret_surface(path, rel_path):
        return "secret_metadata_only"
    if lower.startswith(("uploads/", "bussiness accounts/", "accounting/", "kings_accounting_suite/output/")):
        return "business_financial_evidence"
    if "portfolio" in lower or "exchange" in lower or "kraken" in lower:
        return "trading_or_exchange_state"
    if file_kind == "runtime_state_or_memory":
        return "runtime_memory_state"
    if getattr(stage_record, "generated_or_cache", False):
        return "generated_output"
    return "project_knowledge_or_source"


def infer_next_action(file_kind: str, safety_flags: Sequence[str], subsystem: str) -> str:
    if "secret_or_credential_surface" in safety_flags:
        return "Keep values local; never ingest secret contents into LLM/vault reports."
    if safety_flags:
        return "Keep catalogued and review attention flags during organization/self-enhancement passes."
    if file_kind == "test_or_benchmark":
        return "Use in regression checks when touching its subsystem."
    if file_kind == "audit_manifest_or_index":
        return "Use as self-knowledge evidence for readiness, vault recall, and self-questioning loops."
    if file_kind == "data_or_business_evidence":
        return "Retain source trace and feed through the relevant reconciliation/intake workflow."
    if file_kind == "structured_manifest_or_memory":
        return "Keep schema-aware and preserve traceability when consumed by runtime or audit systems."
    if file_kind == "python_source":
        return f"Keep linked to {subsystem} tests, organism routing, and readiness audits."
    return "Keep visible in the self-catalog and update labels after material changes."


def build_label(path: Path, root: Path) -> FileSelfLabel:
    rel_path = _rel(path, root)
    stage_record = classify_path(path, root)
    secret = _is_secret_surface(path, rel_path)
    sample, read_status, digest = _read_sample(path, rel_path, secret)
    symbols = _python_symbols(path, rel_path, secret)
    file_kind = infer_file_kind(path, rel_path, stage_record)
    subsystem = infer_subsystem(rel_path, stage_record)
    domain = infer_domain(rel_path, stage_record, subsystem)
    tags = _tokens_from_path(rel_path)
    tags.extend(_tokens_from_path(" ".join(symbols.classes + symbols.functions), limit=8))
    semantic_tags = sorted(dict.fromkeys(tags))[:24]
    safety_flags = list(stage_record.attention)
    if secret and "secret_or_credential_surface" not in safety_flags:
        safety_flags.append("secret_or_credential_surface")
    if path.name.lower() in RUNTIME_NAMES and "runtime_state_outside_runtime_stage" not in safety_flags:
        safety_flags.append("runtime_memory_surface")
    role = infer_role(rel_path, file_kind, subsystem, symbols, stage_record.role)
    used_by = infer_used_by(rel_path, file_kind, subsystem)
    sensitivity = infer_sensitivity(path, rel_path, file_kind, stage_record)
    llm_context = _normalise_ws(
        f"{rel_path}: {role} Used by {', '.join(used_by)}. "
        f"Kind={file_kind}; subsystem={subsystem}; domain={domain}; read={read_status}."
    )
    if sample and not symbols.docstring and file_kind in {"documentation_or_report", "configuration"}:
        first_line = next((line.strip() for line in sample.splitlines() if line.strip()), "")
        if first_line:
            llm_context = _normalise_ws(f"{llm_context} First readable line: {first_line}", 420)
    stat = path.stat()
    return FileSelfLabel(
        id=f"file-{hashlib.sha1(rel_path.encode('utf-8')).hexdigest()[:12]}",
        path=rel_path,
        name=path.name,
        extension=path.suffix.lower(),
        size_bytes=stat.st_size,
        modified_utc=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        subsystem=subsystem,
        organism_stage=stage_record.stage,
        organism_domain=domain,
        file_kind=file_kind,
        role=role,
        used_by=used_by,
        semantic_tags=semantic_tags,
        read_status=read_status,
        content_fingerprint=digest,
        data_sensitivity=sensitivity,
        safety_flags=safety_flags,
        python_symbols=symbols,
        llm_context=llm_context,
        vault_route=f"repo.self_catalog.{_slug(domain)}.{_slug(subsystem)}",
        next_action=infer_next_action(file_kind, safety_flags, subsystem),
    )


def discover_excluded_infrastructure_roots(root: Path) -> list[ExcludedInfrastructureRoot]:
    excluded: list[ExcludedInfrastructureRoot] = []
    for dirpath, dirnames, _filenames in os.walk(root):
        current = Path(dirpath)
        try:
            rel_current = current.relative_to(root)
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in rel_current.parts):
            dirnames[:] = []
            continue
        matches = [name for name in dirnames if name in SKIP_DIRS]
        for name in matches:
            target = current / name
            excluded.append(
                ExcludedInfrastructureRoot(
                    path=target.relative_to(root).as_posix(),
                    reason="Dependency, virtualenv, git metadata, or generated cache root recorded at directory level.",
                )
            )
        dirnames[:] = [name for name in dirnames if name not in SKIP_DIRS]
    return sorted(excluded, key=lambda item: item.path.lower())


def build_directory_summaries(labels: Sequence[FileSelfLabel]) -> list[DirectorySummary]:
    grouped: dict[str, list[FileSelfLabel]] = defaultdict(list)
    for label in labels:
        parts = Path(label.path).parts
        key = parts[0] if parts else "."
        grouped[key].append(label)

    summaries: list[DirectorySummary] = []
    for key, items in grouped.items():
        domains = Counter(item.organism_domain for item in items)
        kinds = Counter(item.file_kind for item in items)
        subsystems = Counter(item.subsystem for item in items)
        summaries.append(
            DirectorySummary(
                path=key,
                file_count=len(items),
                total_bytes=sum(item.size_bytes for item in items),
                dominant_subsystem=subsystems.most_common(1)[0][0],
                dominant_kind=kinds.most_common(1)[0][0],
                domains=dict(sorted(domains.items())),
                kinds=dict(sorted(kinds.items())),
            )
        )
    return sorted(summaries, key=lambda item: item.path.lower())


def build_repo_self_catalog(
    repo_root: Optional[Path] = None,
    *,
    max_records: int = 0,
    vault_note: Optional[Path] = DEFAULT_VAULT_NOTE,
) -> RepoSelfCatalog:
    root = repo_root_from(repo_root)
    labels = [build_label(path, root) for path in iter_project_files(root)]
    labels.sort(key=lambda item: item.path.lower())
    total_labels = len(labels)
    truncated = False
    if max_records > 0 and len(labels) > max_records:
        labels = labels[:max_records]
        truncated = True

    domain_counts = Counter(label.organism_domain for label in labels)
    subsystem_counts = Counter(label.subsystem for label in labels)
    kind_counts = Counter(label.file_kind for label in labels)
    sensitivity_counts = Counter(label.data_sensitivity for label in labels)
    safety_counts = Counter(flag for label in labels for flag in label.safety_flags)
    read_counts = Counter(label.read_status for label in labels)
    excluded = discover_excluded_infrastructure_roots(root)
    directory_summaries = build_directory_summaries(labels)

    secret_count = sensitivity_counts.get("secret_metadata_only", 0)
    python_symbol_count = sum(1 for label in labels if label.python_symbols.classes or label.python_symbols.functions)
    status = "catalog_complete"
    if truncated:
        status = "catalog_truncated"
    elif safety_counts:
        status = "catalog_complete_with_attention_items"

    vault_path = (
        resolve_obsidian_note_path(vault_note, repo_root=root)
        if vault_note
        else None
    )
    summary = {
        "total_project_files_discovered": total_labels,
        "cataloged_file_count": len(labels),
        "truncated": truncated,
        "directory_summary_count": len(directory_summaries),
        "excluded_infrastructure_root_count": len(excluded),
        "domain_count": len(domain_counts),
        "subsystem_count": len(subsystem_counts),
        "file_kind_count": len(kind_counts),
        "secret_metadata_only_count": secret_count,
        "python_symbol_probe_count": python_symbol_count,
        "safety_flag_counts": dict(sorted(safety_counts.items())),
        "read_status_counts": dict(sorted(read_counts.items())),
        "coverage_policy": "Every project file outside dependency/cache/virtualenv/git internals is labelled; excluded infrastructure roots are recorded explicitly.",
    }
    vault_memory = {
        "status": "planned" if vault_path else "disabled",
        "note_path": str(vault_path) if vault_path else "",
        "topic": "repo.self_catalog.ready",
        "llm_context_available": True,
        "compact_manifest_for_prompts": "Use compact() or each label.llm_context; do not prompt with secret file contents.",
    }
    notes = [
        "Read-only self-catalog: no execution, no trading, no official filing, no payment, and no external mutation.",
        "Secret-risk files are catalogued by path and metadata only; values are never copied into JSON, CSV, Markdown, vault notes, or LLM context.",
        "Runtime memories and large logs are labelled without requiring full content ingestion.",
        "Dependency, virtualenv, git, and cache roots are directory-level infrastructure, not organism decision logic.",
        "The JSON and CSV manifests are the file-by-file source of truth; the Markdown and vault note are compact human/LLM indexes.",
    ]
    return RepoSelfCatalog(
        schema_version=SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        repo_root=str(root),
        status=status,
        summary=summary,
        domain_counts=dict(sorted(domain_counts.items())),
        subsystem_counts=dict(sorted(subsystem_counts.items())),
        file_kind_counts=dict(sorted(kind_counts.items())),
        sensitivity_counts=dict(sorted(sensitivity_counts.items())),
        directory_summaries=directory_summaries,
        excluded_infrastructure_roots=excluded,
        labels=labels,
        vault_memory=vault_memory,
        notes=notes,
    )


def render_markdown(report: RepoSelfCatalog, *, max_file_rows: int = 80) -> str:
    def esc(value: Any) -> str:
        return str(value).replace("|", "\\|")

    lines: list[str] = []
    lines.append("# Aureon Repo Self-Catalog")
    lines.append("")
    lines.append(f"- Generated: `{report.generated_at}`")
    lines.append(f"- Repo: `{report.repo_root}`")
    lines.append(f"- Status: `{report.status}`")
    lines.append("- Safety: read-only; secret contents excluded; no live orders, filing, payment, or execution")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key in (
        "total_project_files_discovered",
        "cataloged_file_count",
        "excluded_infrastructure_root_count",
        "secret_metadata_only_count",
        "python_symbol_probe_count",
    ):
        lines.append(f"- `{key}`: {report.summary.get(key, 0)}")
    lines.append(f"- `coverage_policy`: {report.summary.get('coverage_policy')}")
    lines.append("")

    lines.append("## What Aureon Can Know About Itself")
    lines.append("")
    lines.append("- Every catalogued project file has an owner subsystem, organism stage, domain, kind, role, safety flags, and next action.")
    lines.append("- Python files include module names, top-level classes/functions/imports where safe to inspect.")
    lines.append("- Secret and environment files are visible to the self-map as metadata only, not copied into memory.")
    lines.append("- Vault/LLM context is provided as compact per-file `llm_context` strings in the JSON manifest.")
    lines.append("")

    lines.append("## Subsystems")
    lines.append("")
    lines.append("| Subsystem | Files |")
    lines.append("| --- | ---: |")
    for subsystem, count in report.subsystem_counts.items():
        lines.append(f"| `{subsystem}` | {count} |")
    lines.append("")

    lines.append("## File Kinds")
    lines.append("")
    lines.append("| Kind | Files |")
    lines.append("| --- | ---: |")
    for kind, count in report.file_kind_counts.items():
        lines.append(f"| `{kind}` | {count} |")
    lines.append("")

    lines.append("## Top-Level Directory Map")
    lines.append("")
    lines.append("| Directory | Files | Dominant subsystem | Dominant kind |")
    lines.append("| --- | ---: | --- | --- |")
    for item in report.directory_summaries:
        lines.append(f"| `{esc(item.path)}` | {item.file_count} | `{esc(item.dominant_subsystem)}` | `{esc(item.dominant_kind)}` |")
    lines.append("")

    if report.excluded_infrastructure_roots:
        lines.append("## Directory-Level Infrastructure")
        lines.append("")
        for item in report.excluded_infrastructure_roots[:80]:
            lines.append(f"- `{item.path}`: {item.reason}")
        if len(report.excluded_infrastructure_roots) > 80:
            lines.append(f"- ... {len(report.excluded_infrastructure_roots) - 80} more infrastructure roots in JSON")
        lines.append("")

    lines.append("## File Label Samples")
    lines.append("")
    lines.append("| File | Subsystem | Kind | Domain | Role |")
    lines.append("| --- | --- | --- | --- | --- |")
    for label in report.labels[:max_file_rows]:
        lines.append(
            f"| `{esc(label.path)}` | `{esc(label.subsystem)}` | `{esc(label.file_kind)}` | `{esc(label.organism_domain)}` | {esc(label.role)} |"
        )
    if len(report.labels) > max_file_rows:
        lines.append(f"| ... | ... | ... | ... | {len(report.labels) - max_file_rows} more labels in JSON/CSV |")
    lines.append("")

    lines.append("## Vault Memory")
    lines.append("")
    for key, value in report.vault_memory.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")

    lines.append("## Notes")
    lines.append("")
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def render_vault_note(report: RepoSelfCatalog) -> str:
    lines: list[str] = []
    lines.append("# Aureon Repo Self-Catalog")
    lines.append("")
    lines.append("This note is the compact vault memory for Aureon's file-by-file self-map.")
    lines.append("")
    lines.append(f"- Generated: `{report.generated_at}`")
    lines.append(f"- Status: `{report.status}`")
    lines.append(f"- Catalogued project files: `{report.summary.get('cataloged_file_count')}`")
    lines.append(f"- Secret metadata-only files: `{report.summary.get('secret_metadata_only_count')}`")
    lines.append(f"- JSON manifest: `docs/audits/aureon_repo_self_catalog.json`")
    lines.append(f"- CSV manifest: `docs/audits/aureon_repo_self_catalog.csv`")
    lines.append("")
    lines.append("## Dominant Subsystems")
    lines.append("")
    for subsystem, count in sorted(report.subsystem_counts.items(), key=lambda item: (-item[1], item[0]))[:20]:
        lines.append(f"- `{subsystem}`: {count} files")
    lines.append("")
    lines.append("## Reasoning Rule")
    lines.append("")
    lines.append("When Aureon needs to know what it is, inspect this note first, then use the JSON manifest labels and per-file `llm_context` fields. Never ingest secret file contents.")
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: RepoSelfCatalog,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
    csv_path: Path = DEFAULT_OUTPUT_CSV,
    *,
    write_vault: bool = True,
) -> tuple[Path, Path, Path, Optional[Path]]:
    root = Path(report.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    out_csv_path = csv_path if csv_path.is_absolute() else root / csv_path
    md_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.parent.mkdir(parents=True, exist_ok=True)
    out_csv_path.parent.mkdir(parents=True, exist_ok=True)

    vault_path: Optional[Path] = None
    if write_vault and report.vault_memory.get("note_path"):
        vault_path = Path(report.vault_memory["note_path"])
        report.vault_memory["status"] = "written"

    md_path.write_text(render_markdown(report), encoding="utf-8")
    js_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")

    with out_csv_path.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "id",
            "path",
            "subsystem",
            "organism_stage",
            "organism_domain",
            "file_kind",
            "data_sensitivity",
            "read_status",
            "size_bytes",
            "role",
            "used_by",
            "semantic_tags",
            "safety_flags",
            "vault_route",
            "next_action",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for label in report.labels:
            writer.writerow(
                {
                    "id": label.id,
                    "path": label.path,
                    "subsystem": label.subsystem,
                    "organism_stage": label.organism_stage,
                    "organism_domain": label.organism_domain,
                    "file_kind": label.file_kind,
                    "data_sensitivity": label.data_sensitivity,
                    "read_status": label.read_status,
                    "size_bytes": label.size_bytes,
                    "role": label.role,
                    "used_by": "; ".join(label.used_by),
                    "semantic_tags": "; ".join(label.semantic_tags),
                    "safety_flags": "; ".join(label.safety_flags),
                    "vault_route": label.vault_route,
                    "next_action": label.next_action,
                }
            )

    if vault_path:
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        vault_path.write_text(render_vault_note(report), encoding="utf-8")
    return md_path, js_path, out_csv_path, vault_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's file-by-file repo self-catalog.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to the current Aureon repo.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--csv", default=str(DEFAULT_OUTPUT_CSV), help="CSV manifest path.")
    parser.add_argument("--vault-note", default=str(DEFAULT_VAULT_NOTE), help="Vault note path.")
    parser.add_argument("--no-vault", action="store_true", help="Do not write a compact Obsidian/vault note.")
    parser.add_argument("--max-records", type=int, default=0, help="Maximum file records to keep; 0 means all project files.")
    parser.add_argument("--no-write", action="store_true", help="Print a summary without writing artifacts.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    vault_note: Optional[Path]
    if args.no_vault:
        vault_note = None
    else:
        vault_note = Path(args.vault_note)
    report = build_repo_self_catalog(root, max_records=args.max_records, vault_note=vault_note)
    if args.no_write:
        print(json.dumps({"status": report.status, "summary": report.summary}, indent=2, sort_keys=True))
    else:
        md_path, json_path, csv_path, vault_path = write_report(
            report,
            Path(args.markdown),
            Path(args.json),
            Path(args.csv),
            write_vault=not args.no_vault,
        )
        print(
            json.dumps(
                {
                    "status": report.status,
                    "markdown": str(md_path),
                    "json": str(json_path),
                    "csv": str(csv_path),
                    "vault_note": str(vault_path) if vault_path else "",
                    "summary": report.summary,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 2 if report.status == "catalog_truncated" else 0


if __name__ == "__main__":
    raise SystemExit(main())
