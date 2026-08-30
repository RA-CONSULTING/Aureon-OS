"""Aureon coding-agent skill base and web-learning map.

This module teaches Aureon how to see its coding capability as a living
system:

repo code -> skill library -> coder agents -> web/repo learning sources
-> improvement work orders -> CodeArchitect/Queen writer -> tests/retest.

It is evidence-only by default. Online probes are read-only and optional.
No exchange mutation, filing, payment, credential reveal, or arbitrary code
application happens here.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

from aureon.autonomous.aureon_saas_system_inventory import repo_root_from
from aureon.obsidian_paths import resolve_obsidian_note_path

SCHEMA_VERSION = "aureon-coding-agent-skill-base-v2"
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_coding_agent_skill_base.json")
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_coding_agent_skill_base.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_coding_agent_skill_base.json")
DEFAULT_STATE_PATH = Path("state/aureon_coding_agent_skill_base_last_run.json")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/aureon_coding_agent_skill_base.md")
DEFAULT_COMPONENT = Path("frontend/src/components/generated/AureonCodingAgentSkillBaseConsole.tsx")
DEFAULT_APP_PATH = Path("frontend/src/App.tsx")
BOUNDED_LOCAL_WRITER = "bounded-local-writer"
WEBSITE_SOURCE_RATIONALISATION_MODULE = Path("aureon/operator/website_source_rationalisation.py")
WEBSITE_SOURCE_RATIONALISATION_RUNBOOK = Path("docs/runbooks/WEBSITE_SOURCE_RATIONALISATION.md")
WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256 = (
    "D79397371038912C26056A4C8A154671B0269DF54DDBBB2BAD0BE472D070DD09"
)
WEBSITE_SOURCE_RATIONALISATION_LAUNCHER = Path("tools/run-website-source-rationalisation.py")
WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256 = (
    "827D4112E6C6042B4931E987237E1E7B6035B5A147373CDE202D9DC95184B009"
)
WEBSITE_SOURCE_RATIONALISATION_REQUIRED_SYMBOLS = frozenset(
    {
        "create_source_rationalisation_plan",
        "write_source_rationalisation_plan",
        "validate_owner_source_rationalisation_decision",
        "write_owner_validation",
    }
)

IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "queen_backups",
}

CODE_EXTENSIONS = {
    ".py": "python",
    ".tsx": "react_typescript",
    ".ts": "typescript",
    ".jsx": "react_javascript",
    ".js": "javascript",
    ".ps1": "powershell",
    ".cmd": "windows_batch",
    ".json": "json_contract",
    ".md": "documentation",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
}

OFFICIAL_LEARNING_SOURCES = [
    {
        "id": "python_docs",
        "title": "Python documentation",
        "url": "https://docs.python.org/3/",
        "skill_domains": ["python", "testing", "tooling"],
    },
    {
        "id": "pytest_docs",
        "title": "pytest documentation",
        "url": "https://docs.pytest.org/",
        "skill_domains": ["testing", "quality_gate"],
    },
    {
        "id": "typescript_docs",
        "title": "TypeScript handbook",
        "url": "https://www.typescriptlang.org/docs/",
        "skill_domains": ["typescript", "frontend"],
    },
    {
        "id": "react_docs",
        "title": "React documentation",
        "url": "https://react.dev/learn",
        "skill_domains": ["react", "frontend"],
    },
    {
        "id": "vite_docs",
        "title": "Vite guide",
        "url": "https://vite.dev/guide/",
        "skill_domains": ["frontend", "build"],
    },
    {
        "id": "owasp_asvs",
        "title": "OWASP ASVS project",
        "url": "https://owasp.org/www-project-application-security-verification-standard/",
        "skill_domains": ["security", "review"],
    },
    {
        "id": "w3c_wcag_22",
        "title": "W3C Web Content Accessibility Guidelines 2.2",
        "url": "https://www.w3.org/TR/WCAG22/",
        "skill_domains": ["website_design", "accessibility", "quality_gate"],
    },
    {
        "id": "mdn_web_docs",
        "title": "MDN Web Docs",
        "url": "https://developer.mozilla.org/en-US/docs/Web",
        "skill_domains": ["website_design", "html", "css", "javascript", "accessibility"],
    },
    {
        "id": "playwright_docs",
        "title": "Playwright documentation",
        "url": "https://playwright.dev/docs/intro",
        "skill_domains": ["website_design", "browser_qa", "visual_regression"],
    },
    {
        "id": "web_vitals",
        "title": "web.dev Web Vitals",
        "url": "https://web.dev/articles/vitals",
        "skill_domains": ["website_design", "performance", "quality_gate"],
    },
    {
        "id": "binance_api_docs",
        "title": "Binance API documentation",
        "url": "https://developers.binance.com/docs",
        "skill_domains": ["exchange_api", "market_data"],
    },
    {
        "id": "kraken_api_docs",
        "title": "Kraken API documentation",
        "url": "https://docs.kraken.com/api/",
        "skill_domains": ["exchange_api", "market_data"],
    },
    {
        "id": "alpaca_api_docs",
        "title": "Alpaca API documentation",
        "url": "https://docs.alpaca.markets/",
        "skill_domains": ["exchange_api", "market_data"],
    },
]

WEB_LEARNING_QUERIES = [
    {
        "id": "python_ast_safe_transform",
        "query": "official Python ast documentation safe code transformation",
        "why": "Improve safe code analysis and patch validation.",
    },
    {
        "id": "react_accessible_dashboard_patterns",
        "query": "React official docs accessible dashboard component patterns",
        "why": "Improve frontend console components and UI smoke tests.",
    },
    {
        "id": "pytest_fixture_patterns",
        "query": "pytest official documentation fixtures monkeypatch tmp_path",
        "why": "Improve generated tests for Aureon self-repair work.",
    },
    {
        "id": "exchange_api_rate_limits",
        "query": "official Binance Kraken Alpaca API rate limits documentation",
        "why": "Teach coder agents to preserve market-data governor logic.",
    },
    {
        "id": "wcag_public_site_testing",
        "query": "W3C WCAG 2.2 keyboard focus reflow contrast official guidance",
        "why": "Keep public-site accessibility gates tied to the current normative source.",
    },
    {
        "id": "playwright_visual_regression",
        "query": "Playwright official visual comparisons reduced motion browser testing",
        "why": "Improve repeatable route, viewport, interaction, and screenshot proof.",
    },
    {
        "id": "web_vitals_performance",
        "query": "web.dev official Core Web Vitals LCP CLS INP thresholds",
        "why": "Keep public-site performance budgets current and source-linked.",
    },
]


@dataclass
class CoderAgentRole:
    name: str
    purpose: str
    owns: list[str]
    reads: list[str]
    writes: list[str]
    tools: list[str]
    evidence_required: list[str]
    safety_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CodingWorkOrder:
    id: str
    title: str
    status: str
    priority: int
    owner_agent: str
    reason: str
    proposed_action: str
    validation: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CodingLogicRule:
    id: str
    who: list[str]
    what: str
    where: list[str]
    when: list[str]
    how: list[str]
    validation: list[str]
    evidence: list[str]
    safety_boundary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def website_source_rationalisation_readiness(repo_root: Path) -> dict[str, Any]:
    """Inspect the planning/validation protocol without importing or executing it."""

    module_path = repo_root / WEBSITE_SOURCE_RATIONALISATION_MODULE
    runbook_path = repo_root / WEBSITE_SOURCE_RATIONALISATION_RUNBOOK
    launcher_path = repo_root / WEBSITE_SOURCE_RATIONALISATION_LAUNCHER
    installed = module_path.is_file()
    runbook_available = runbook_path.is_file()
    launcher_available = launcher_path.is_file()
    symbols: set[str] = set()
    functions: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    parse_error = ""
    source_sha256 = ""
    repo_code_imported = False
    launcher_sha256 = ""
    launcher_repo_code_imported = False
    if installed:
        try:
            module_bytes = module_path.read_bytes()
            source_sha256 = hashlib.sha256(module_bytes).hexdigest().upper()
            syntax_tree = ast.parse(
                module_bytes.decode("utf-8"),
                filename=WEBSITE_SOURCE_RATIONALISATION_MODULE.as_posix(),
            )
            functions = {
                node.name: node
                for node in syntax_tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            symbols = set(functions)
            repo_code_imported = any(
                (
                    isinstance(node, ast.ImportFrom)
                    and isinstance(node.module, str)
                    and node.module.startswith("aureon")
                )
                or (
                    isinstance(node, ast.Import)
                    and any(alias.name.startswith("aureon") for alias in node.names)
                )
                for node in syntax_tree.body
            )
        except (OSError, SyntaxError, UnicodeError) as exc:
            parse_error = f"{type(exc).__name__}: {exc}"

    if launcher_available:
        try:
            launcher_bytes = launcher_path.read_bytes()
            launcher_sha256 = hashlib.sha256(launcher_bytes).hexdigest().upper()
            launcher_tree = ast.parse(
                launcher_bytes.decode("utf-8"),
                filename=WEBSITE_SOURCE_RATIONALISATION_LAUNCHER.as_posix(),
            )
            launcher_repo_code_imported = any(
                (
                    isinstance(node, ast.ImportFrom)
                    and isinstance(node.module, str)
                    and node.module.startswith("aureon")
                )
                or (
                    isinstance(node, ast.Import)
                    and any(alias.name.startswith("aureon") for alias in node.names)
                )
                for node in launcher_tree.body
            )
        except (OSError, SyntaxError, UnicodeError) as exc:
            parse_error = f"{type(exc).__name__}: {exc}"

    missing_symbols = sorted(WEBSITE_SOURCE_RATIONALISATION_REQUIRED_SYMBOLS - symbols)
    source_hash_matches = source_sha256 == WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256

    def parameter_names(name: str) -> set[str] | None:
        node = functions.get(name)
        if node is None or node.args.vararg is not None or node.args.kwarg is not None:
            return None
        return {
            argument.arg
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            )
        }

    expected_public_parameters = {
        "create_source_rationalisation_plan": {"run_id"},
        "write_source_rationalisation_plan": {"plan", "output_path"},
        "validate_owner_source_rationalisation_decision": {"plan_path", "decision_path"},
        "write_owner_validation": {"plan_path", "decision_path", "output_path"},
    }
    public_signatures_locked = all(
        parameter_names(name) == expected for name, expected in expected_public_parameters.items()
    )
    launcher_hash_matches = launcher_sha256 == WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256
    authenticated_source = bool(
        source_hash_matches
        and launcher_hash_matches
        and public_signatures_locked
        and not repo_code_imported
        and not launcher_repo_code_imported
    )
    planning_protocol_available = authenticated_source and {
        "create_source_rationalisation_plan",
        "write_source_rationalisation_plan",
    }.issubset(symbols)
    owner_decision_validation_protocol_available = authenticated_source and {
        "validate_owner_source_rationalisation_decision",
        "write_owner_validation",
    }.issubset(symbols)
    available = bool(
        installed
        and runbook_available
        and launcher_available
        and not parse_error
        and not missing_symbols
        and planning_protocol_available
        and owner_decision_validation_protocol_available
    )
    state = "installed-not-executed" if available else "needs-repair" if installed else "unavailable"
    return {
        "available": available,
        "installed": installed,
        "runbook_available": runbook_available,
        "launcher_available": launcher_available,
        "state": state,
        "module_path": WEBSITE_SOURCE_RATIONALISATION_MODULE.as_posix(),
        "runbook_path": WEBSITE_SOURCE_RATIONALISATION_RUNBOOK.as_posix(),
        "discovery_mode": "metadata-only-ast-no-import-no-subprocess",
        "module_imported": False,
        "discovery_subprocess_launched": False,
        "source_sha256": source_sha256,
        "expected_source_sha256": WEBSITE_SOURCE_RATIONALISATION_REVIEWED_SHA256,
        "source_hash_matches": source_hash_matches,
        "public_signatures_locked": public_signatures_locked,
        "repo_code_imported": repo_code_imported,
        "launcher_path": WEBSITE_SOURCE_RATIONALISATION_LAUNCHER.as_posix(),
        "launcher_sha256": launcher_sha256,
        "expected_launcher_sha256": WEBSITE_SOURCE_RATIONALISATION_LAUNCHER_SHA256,
        "launcher_hash_matches": launcher_hash_matches,
        "launcher_repo_code_imported": launcher_repo_code_imported,
        "planning_protocol_available": planning_protocol_available,
        "owner_decision_validation_protocol_available": (owner_decision_validation_protocol_available),
        "planning_executed_during_discovery": False,
        "owner_decision_validation_executed_during_discovery": False,
        "writes_during_discovery": False,
        "missing_symbols": missing_symbols,
        "parse_error": parse_error,
        "allowed_role": "PublicWebsiteDesignQA",
        "text_worker_authority": "none",
        "owner_decision_maximum_age_hours": 4,
        "fixed_footprint_thresholds": {
            "max_total_bytes": 4_500_000,
            "max_image_bytes": 2_200_000,
            "max_css_bytes": 350_000,
            "max_single_asset_bytes": 500_000,
        },
        "autonomous_owner_decision": False,
        "omission_proves_readiness": False,
        "staging_authority": "none",
        "physical_source_file_removal": "none",
        "canonical_website_mutation": "none",
        "candidate_authority": "none",
        "package_authority": "none",
        "release_eligible": False,
        "deployment_authority": "none",
        "credential_access": "none",
        "network_access": "none",
    }


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "path": str(path)}


def _iter_repo_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix.lower() in CODE_EXTENSIONS:
            files.append(path)
    return files


def classify_repo_code(root: Path) -> dict[str, Any]:
    files = _iter_repo_files(root)
    by_language: Counter[str] = Counter()
    by_domain: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    for path in files:
        rel = path.relative_to(root).as_posix()
        language = CODE_EXTENSIONS.get(path.suffix.lower(), "other")
        by_language[language] += 1
        domain = _domain_for_path(rel)
        by_domain[domain] += 1
        examples.setdefault(domain, [])
        if len(examples[domain]) < 8:
            examples[domain].append(rel)
    return {
        "file_count": len(files),
        "by_language": dict(sorted(by_language.items())),
        "by_domain": dict(sorted(by_domain.items())),
        "examples": dict(sorted(examples.items())),
    }


def _domain_for_path(rel: str) -> str:
    text = rel.lower()
    if text.startswith("frontend/") or "/components/" in text or text.endswith((".tsx", ".css")):
        return "frontend"
    if "exchange" in text or "trading" in text or "kraken" in text or "binance" in text or "alpaca" in text:
        return "trading"
    if "account" in text or "hmrc" in text or "ct600" in text:
        return "accounting"
    if "test" in text or "pytest" in text:
        return "testing"
    if "code_architect" in text or "safe_code" in text:
        return "code_architect"
    if "security" in text or "auth" in text or "kyc" in text:
        return "security"
    if "voice" in text or "vault" in text or "knowledge" in text:
        return "knowledge_voice"
    if "autonomous" in text or "goal" in text or "agent" in text:
        return "autonomy"
    return "core"


def skill_library_snapshot(root: Path) -> dict[str, Any]:
    snapshots: list[dict[str, Any]] = []
    for storage_dir in (root / "state" / "skills", root / "state" / "capability_growth_skills"):
        library_path = storage_dir / "skill_library.json"
        raw = load_json(library_path)
        raw_skills = raw.get("skills")
        skills: list[Any] = raw_skills if isinstance(raw_skills, list) else []
        by_level = Counter(
            str(item.get("level_name") or item.get("level") or "unknown")
            for item in skills
            if isinstance(item, dict)
        )
        by_status = Counter(str(item.get("status") or "unknown") for item in skills if isinstance(item, dict))
        snapshots.append(
            {
                "storage_dir": storage_dir.as_posix(),
                "library_path": library_path.as_posix(),
                "exists": library_path.exists(),
                "count": len(skills),
                "by_level": dict(sorted(by_level.items())),
                "by_status": dict(sorted(by_status.items())),
                "examples": [
                    {
                        "name": item.get("name"),
                        "level": item.get("level_name") or item.get("level"),
                        "status": item.get("status"),
                        "category": item.get("category"),
                    }
                    for item in skills[:12]
                    if isinstance(item, dict)
                ],
            }
        )
    return {
        "libraries": snapshots,
        "total_skill_count": sum(int(item.get("count") or 0) for item in snapshots),
    }


def tool_registry_snapshot(root: Path) -> dict[str, Any]:
    names: list[str] = []
    agent_core_intents: list[str] = []
    errors: list[str] = []
    try:
        from aureon.inhouse_ai.tool_registry import ToolRegistry

        registry = ToolRegistry(include_builtins=True)
        names = sorted(registry.names())
    except Exception as exc:
        errors.append(f"ToolRegistry: {type(exc).__name__}: {exc}")

    try:
        from aureon.autonomous.aureon_agent_core import INTENT_MAP

        agent_core_intents = sorted(set(INTENT_MAP.values()))
    except Exception as exc:
        errors.append(f"AureonAgentCore: {type(exc).__name__}: {exc}")

    required = ["web_search", "web_fetch", "repo_search", "execute_shell", "skill_base_status"]
    return {
        "inhouse_tool_count": len(names),
        "inhouse_tools": names,
        "agent_core_intents": agent_core_intents,
        "required_coder_tools": required,
        "missing_required_coder_tools": [name for name in required if name not in names],
        "errors": errors,
    }


def coder_agent_roles() -> list[CoderAgentRole]:
    return [
        CoderAgentRole(
            name="RepoCartographer",
            purpose="Map existing code, tests, generated reports, and ownership boundaries before any edit.",
            owns=["repo map", "dependency hints", "path evidence"],
            reads=["aureon/**", "frontend/src/**", "tests/**", "docs/audits/**"],
            writes=["docs/audits/aureon_coding_agent_skill_base.json"],
            tools=["repo_search", "read_state", "skill_base_status"],
            evidence_required=["path list", "source count", "domain classification"],
            safety_boundary="Read-only except its own audit manifests.",
        ),
        CoderAgentRole(
            name="WebLearningScout",
            purpose="Use web_search and web_fetch to learn from official docs and open-source API documentation.",
            owns=["learning queries", "source summaries", "freshness evidence"],
            reads=["official docs", "public API docs", "repo manifests"],
            writes=["docs/audits/aureon_coding_agent_skill_base.md"],
            tools=["web_search", "web_fetch", "publish_thought"],
            evidence_required=["source url", "fetch status", "why source was relevant"],
            safety_boundary="Read-only online learning; no code copied blindly and no credential transmission.",
        ),
        CoderAgentRole(
            name="ImplementationWorker",
            purpose="Turn approved work orders into scoped code patches through the bounded local writer and reviewed code architecture.",
            owns=["implementation patch", "generated component or module", "authoring evidence"],
            reads=["repo map", "tests", "coding standards", "source manifests"],
            writes=["aureon/**", "frontend/src/**", "tests/**"],
            tools=["repo_search", "execute_shell", "skill_base_status"],
            evidence_required=["diff summary", "writer provenance", "validation command"],
            safety_boundary="Repo writes must be scoped and retested; no live trading or external mutation.",
        ),
        CoderAgentRole(
            name="TestPilot",
            purpose="Run compile, unit, frontend build, and smoke checks after each code change.",
            owns=["test plan", "test output", "regression risk"],
            reads=["tests/**", "package.json", "docs/audits/**"],
            writes=["docs/audits/aureon_repo_self_repair.json"],
            tools=["execute_shell", "repo_search"],
            evidence_required=["command", "return code", "stdout/stderr tail"],
            safety_boundary="Can run local tests/builds only; no destructive shell operations.",
        ),
        CoderAgentRole(
            name="SecurityReviewer",
            purpose="Check generated code for credential exposure, unsafe mutation, and missing evidence gates.",
            owns=["security review", "safety blocker records", "redaction checks"],
            reads=["repo_search", "public manifests", "tests"],
            writes=["docs/audits/security review notes"],
            tools=["repo_search", "execute_shell"],
            evidence_required=["blocked pattern scan", "secret redaction result"],
            safety_boundary="May report blockers; may not bypass payment, filing, credential, or live-order boundaries.",
        ),
        CoderAgentRole(
            name="PublicWebsiteDesignWorker",
            purpose=(
                "Propose one text-only patch manifest from a broker-issued sealed design context; "
                "the built-in declarative applier may apply it only inside one existing staged candidate."
            ),
            owns=["sealed text-only patch manifest", "before/after hashes", "design implementation receipt"],
            reads=[
                "website/**",
                "website/data/**",
                "data/website_operator/investor_site_design_brief.v1.json",
                "data/website_operator/design_research_sources.v1.json",
                "data/website_operator/design_stakeholder_feedback.v1.json",
                "data/website_operator/editorial_asset_provenance.v1.json",
                "data/website_operator/investor_copy_quality_policy.v1.json",
                "data/website_operator/hnc_evidence_graph.v1.json",
                "aureon/operator/design_evidence_brief.py",
                "aureon/operator/design_research_refresh.py",
                "aureon/operator/design_stakeholder_feedback.py",
                "aureon/operator/design_editorial_asset_provenance.py",
                "aureon/operator/design_investor_copy_quality.py",
                "aureon/operator/design_hnc_evidence_graph.py",
                "aureon/autonomous/aureon_public_website_design_runner.py",
                "aureon/autonomous/aureon_staged_design_worker_broker.py",
                "skills/aureon-harmonic-design-suite/**",
            ],
            writes=["broker-issued staged worker sandbox (declared text paths only)"],
            tools=["broker-issued staged sandbox", "built-in manifest-patch applier", "skill_base_status"],
            evidence_required=[
                "lease id",
                "work order id",
                "baseline source-tree hash",
                "candidate workspace snapshot SHA-256",
                "exact changed paths",
                "claim-impact declarations",
                "operator-pinned test-policy hash; worker pass strings are not evidence",
                "design-evidence brief SHA-256",
                "redacted design-research declaration SHA-256",
                "route claim-capsule SHA-256",
                "privacy-safe stakeholder-feedback declaration SHA-256",
                "route stakeholder-signal capsule SHA-256",
                "complete stakeholder response-manifest SHA-256",
                "redacted editorial-asset capsule-set and public-coverage SHA-256",
                "investor-copy policy and audit SHA-256",
                "source-neutral HNC graph contract and bundle SHA-256",
            ],
            safety_boundary=(
                "Works only through one short-lived broker lease and its sealed sandbox; cannot write canonical "
                "website/, issue its own lease, read raw correspondence or its redacted source snapshot, access "
                "credentials, back up, owner-gate, package, promote, or deploy. Stakeholder signals are available "
                "only as the broker-sealed declaration binding and controlled-code route capsule. Editorial "
                "binary content, private source locations and rights evidence are unavailable; a source-neutral "
                "HNC bundle is planning evidence until a fresh source-bound work order and human acceptance "
                "exist. A worker may neither choose test commands, arguments, environment or pass state nor "
                "turn a submitted `passed` string into evidence."
            ),
        ),
        CoderAgentRole(
            name="PublicWebsiteDesignQA",
            purpose="Veto public-site candidates that fail claims, accessibility, responsive, motion, performance, browser, or package-closure gates, and bind focused browser runs before any repeatability series.",
            owns=[
                "design council verdict",
                "objective gate report",
                "source-bound initial browser gate receipt",
                "repair work order",
            ],
            reads=[
                "website/**",
                "tools/aureon_website_*",
                "aureon/operator/design_candidate_initial_gate.py",
                "aureon/operator/secure_immutable_artifact.py",
                "aureon/operator/design_candidate_static_qa.py",
                "aureon/operator/design_candidate_motion_policy_compiler.py",
                "aureon/operator/design_candidate_test_policy_compiler.py",
                "aureon/operator/design_candidate_source_closure.py",
                "aureon/operator/design_motion_performance_budget.py",
                "aureon/operator/design_candidate_test_evidence.py",
                "aureon/autonomous/aureon_public_website_design_runner.py",
                "aureon/operator/design_evidence_brief.py",
                "aureon/operator/design_research_refresh.py",
                "aureon/operator/design_stakeholder_feedback.py",
                "aureon/operator/design_editorial_asset_provenance.py",
                "aureon/operator/design_editorial_asset_candidate_importer.py",
                "aureon/operator/design_investor_copy_quality.py",
                "aureon/operator/design_investor_copy_governance.py",
                "aureon/operator/design_hnc_evidence_graph.py",
                "aureon/operator/website_source_rationalisation.py",
                "tools/run-website-source-rationalisation.py",
                "aureon/operator/website_runtime_optimisation.py",
                "tools/run-website-runtime-optimisation.py",
                "aureon/operator/website_runtime_measurement_provenance.py",
                "tools/run-website-runtime-measurement-provenance.py",
                "data/website_operator/browser_acceptance_contract.v1.json",
                "docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_V1.schema.json",
                "docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_V1.schema.json",
                "docs/research/schemas/AUREON_WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_V1.schema.json",
                "data/website_operator/investor_site_design_brief.v1.json",
                "data/website_operator/design_research_sources.v1.json",
                "data/website_operator/design_stakeholder_feedback.v1.json",
                "data/website_operator/editorial_asset_provenance.v1.json",
                "data/website_operator/investor_copy_quality_policy.v1.json",
                "data/website_operator/hnc_evidence_graph.v1.json",
                "docs/audits/**",
                "artifacts/website-candidates/**",
                "artifacts/website-operator/**",
                "docs/runbooks/DESIGN_MOTION_PERFORMANCE_BUDGET.md",
                "docs/runbooks/DESIGN_CANDIDATE_TEST_EVIDENCE.md",
                "docs/runbooks/SECURE_IMMUTABLE_ARTIFACT.md",
                "docs/runbooks/DESIGN_CANDIDATE_STATIC_QA.md",
                "docs/runbooks/DESIGN_CANDIDATE_MOTION_POLICY_COMPILER.md",
                "docs/runbooks/DESIGN_CANDIDATE_TEST_POLICY_COMPILER.md",
                "docs/runbooks/WEBSITE_SOURCE_RATIONALISATION.md",
                "docs/runbooks/WEBSITE_RUNTIME_OPTIMISATION.md",
                "docs/research/AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_V2_RUNBOOK.md",
                "docs/research/schemas/AUREON_PUBLIC_WEBSITE_DESIGN_DELIVERY_RUNNER_V2.schema.json",
                "tests/test_website_runtime_measurement_provenance.py",
            ],
            writes=["docs/audits/**", "artifacts/website-candidates/**", "artifacts/website-operator/**"],
            tools=[
                "repo_search",
                "execute_shell",
                "skill_base_status",
                "trusted candidate-test evidence control",
                "source-pinned Node toolchain binding with no PATH fallback",
                "bounded shell-false Popen evidence execution",
                "deterministic motion/performance budget control",
                "read-only candidate QA control-plane readiness",
                "candidate-scoped static QA adapters",
                "imported compiler read-only drift-check APIs (not sealed ingress)",
                "runner-delegated sealed direct-file compiler verification",
                "V2 one-attempt candidate-QA runner",
                "website source-rationalisation planning protocol",
                "website source-rationalisation owner-decision validation protocol",
                "website runtime-optimisation structural validator with production compilation blocked",
                "fresh isolated-launcher runtime measurement static-integrity validator with provenance unverified and production blocked",
            ],
            evidence_required=[
                "tool versions",
                "source hash",
                "viewport results",
                "initial-gate verdict",
                "manifest closure",
                "design-evidence brief, redacted research-refresh and route claim-capsule hashes",
                "current privacy-safe stakeholder capsule and complete response-manifest hashes",
                "editorial-asset public-coverage and safe capsule-set hashes",
                "trusted editorial import receipt and replay-verification hashes",
                "investor-copy blocker counts and policy hash",
                "HNC graph exact-claim, budget and reduced-motion bundle hashes",
                "motion-budget receipt with decision.status pass and eligible_for_next_local_gate true",
                "independently sealed candidate-test receipt whose verifier retains origin_attested false and reports evidence_passed true",
                "reviewed Node absolute-path, size, SHA-256 and binding-digest evidence with no ambient PATH fallback",
                "candidate-test bounded subprocess.Popen shell false and 2 MiB per-stream capture contract",
                "handle-bound immutable-writer source hash",
                "V2 fixed motion-config compiler replay bound to one captured candidate manifest, both tree algorithms and hashes, reviewed source-policy hash, and exact threshold-set hash",
                "V2 fixed test-policy compiler replay bound to the unchanged V1 policy payload content-core hash and complete ordered command-id hash",
                "sealed direct-file read-only compiler replay through python -I -S -B and the source-closure helper, delegated by the V2 runner rather than an imported API",
                "one consumed V2 candidate-QA claim bound to the unchanged candidate, canonical tree, and single captured-manifest hash",
                "motion-first result before trusted test evidence, then candidate-qa-verified before the initial browser gate",
                "proposal-only source-rationalisation plan, retained/omitted manifests, closure and fixed-budget projection hashes",
                "separately supplied exact owner-decision and validation hashes with a maximum four-hour window",
                "static-integrity result binding the complete current website manifest, two pre-existing replicas, exact stored bytes, payload hashes, and header-derived dimensions while provenance stays unverified",
            ],
            safety_boundary=(
                "May test, veto, and record a staged initial gate locally; cannot create or edit an "
                "owner decision, treat broad access as governance approval, invoke the canonical "
                "investor-copy governance apply, weaken thresholds, promote a visual baseline, or deploy. "
                "Module installation and worker pass strings never establish a QA pass; candidate-test "
                "structural verification is not origin attestation and requires a separately preserved "
                "trusted orchestration seal plus evidence_passed true. QA agents cannot select or relax "
                "test policy, commands, thresholds, origins, retries, or gate order, and cannot infer a "
                "pass or enter the browser gate unless the V2 runner records candidate-qa-verified. "
                "Imported compiler verification is drift-check-only and cannot claim pre-import source "
                "authentication; only trusted runner delegation may launch the sealed direct-file "
                "read-only verifier through one bounded subprocess.Popen with shell false, a 64 KiB "
                "aggregate/per-stream output ceiling, 300-second timeout and no retry; candidate tests "
                "bind the reviewed Node absolute path, size and SHA-256 without PATH fallback, and "
                "discovery itself launches no subprocess. Source-rationalisation discovery is metadata-only "
                "and cannot execute planning or validation; QA may use the explicit protocols but cannot "
                "create an owner decision, stage or delete source, create or mutate a candidate, mutate "
                "canonical website/, package, release, access credentials or network, publish, or deploy. "
                "The text worker has no source-rationalisation capability, and omission from the current "
                "public-runtime closure does not prove readiness. The runtime measurement static-integrity "
                "validator can read and validate only an explicitly supplied existing artifact; it cannot prove "
                "producer execution, deterministic replay, full image decode, freshness, browser or visual "
                "acceptance, create evidence, mutate source or candidates, or unblock production, and the text "
                "worker receives no access. Trusted use requires a fresh hash-authenticated python -I -S -B "
                "launcher process; imported APIs are non-authoritative test and drift checks because same-process "
                "module state can be rebound."
            ),
        ),
    ]


def public_website_design_skill_stack() -> dict[str, Any]:
    return {
        "schema_version": "aureon-public-website-design-skill-stack-v1",
        "entry_skill": "skills/aureon-harmonic-design-suite/SKILL.md",
        "operator": "aureon/operator/website_operator.py",
        "goal_intent": "public_website_design_cycle",
        "capability_family": "website_design",
        "levels": {
            "L0_atomic": [
                "inventory_site",
                "observe_live_surface",
                "bind_owner_source_reconciliation",
                "validate_owner_source_reconciliation",
                "plan_website_source_rationalisation",
                "validate_website_source_rationalisation_owner_decision",
                "validate_runtime_optimisation_measurement_evidence",
                "validate_runtime_optimisation_static_integrity",
                "audit_design_research_refresh",
                "audit_stakeholder_feedback",
                "audit_editorial_asset_provenance",
                "prepare_editorial_asset_rights_decisions",
                "import_verified_editorial_assets_to_staged_candidate",
                "verify_editorial_asset_candidate_import",
                "audit_investor_copy_quality",
                "preflight_investor_copy_repair_contract",
                "preflight_investor_copy_repair_work_order",
                "verify_investor_copy_repair_contract",
                "evaluate_investor_copy_repair_candidate",
                "verify_investor_copy_governance_decision",
                "simulate_investor_copy_governance_application",
                "apply_exact_owner_approved_investor_copy_governance_delta",
                "build_source_neutral_hnc_evidence_graph",
                "audit_design_evidence_brief",
                "bind_route_feedback_capsules",
                "read_claim_register",
                "create_brief_bound_delivery_job",
                "issue_staged_design_worker_lease",
                "submit_staged_design_worker_delivery",
                "validate_feedback_response_manifest",
                "create_reconciled_source_bound_work_order",
                "stage_candidate_tree",
                "validate_candidate_diff",
                "advance_staged_delivery_receipt",
                "revalidate_candidate_provenance",
                "capture_candidate_visual_evidence",
                "evaluate_candidate_initial_gate",
                "inspect_candidate_qa_control_plane_readiness",
                "inspect_candidate_compiler_verification_ingress",
                "audit_candidate_static_qa",
                "compile_fixed_candidate_motion_config",
                "verify_fixed_candidate_motion_config",
                "compile_fixed_candidate_test_policy",
                "verify_fixed_candidate_test_policy",
                "delegate_sealed_read_only_compiler_verification_to_runner",
                "claim_one_shot_candidate_qa_attempt",
                "evaluate_candidate_qa_motion_first",
                "audit_motion_performance_budget",
                "replay_motion_performance_budget_receipt",
                "execute_hash_bound_candidate_test_suite",
                "verify_candidate_test_evidence_receipt",
                "attribute_research_route_layout",
                "verify_candidate_visual_review",
                "record_design_learning",
                "capture_route",
                "check_contrast",
                "test_keyboard",
                "test_reduced_motion",
                "measure_performance",
                "diff_screenshot",
                "verify_dependency_closure",
            ],
            "L1_compound": [
                "benchmark_competitor",
                "audit_route",
                "audit_design_system",
                "audit_copy_and_claims",
                "translate_stakeholder_signals",
                "draft_bounded_candidate",
            ],
            "L2_task": [
                "redesign_route",
                "motion_pass",
                "evidence_copy_pass",
                "visual_asset_pass",
                "repair_finding",
            ],
            "L3_workflow": [
                "public_site_design_cycle",
                "staged_candidate_change_control",
                "website_release_preflight",
            ],
            "L4_role": [
                "Website Design Director",
                "Competitor Research Scout",
                "Brand and Design-System Lead",
                "Technical Editorial Writer",
                "Claims and Evidence Editor",
                "Stakeholder Insight & Privacy Editor",
                "Motion Designer",
                "Visual Asset Director",
                "Accessibility and Performance QA",
                "Design Release QA",
            ],
        },
        "feedback_loop": [
            "sense",
            "orient",
            "branch",
            "compose",
            "prove",
            "challenge",
            "retain_or_revert",
            "package",
            "release",
            "learn",
        ],
        "candidate_qa_gate_order": [
            "compile-fixed-motion-config",
            "compile-fixed-test-policy",
            "run-motion-budget-first",
            "run-complete-trusted-test-policy",
            "enter-initial-browser-gate-only-after-qa-verification",
        ],
        "role_capability_grants": {
            "PublicWebsiteDesignQA": [
                "plan_website_source_rationalisation",
                "validate_website_source_rationalisation_owner_decision",
                "validate_runtime_optimisation_measurement_evidence",
                "validate_runtime_optimisation_static_integrity",
            ],
            "PublicWebsiteDesignWorker": [],
        },
        "authority": {
            "local_website_mutation": "staged-candidate-only; canonical website promotion is a separate owner-controlled action",
            "candidate_staging": "artifacts/website-candidates/<run-id>/website only",
            "candidate_control": "aureon.operator.design_candidate_control; exact allowlist, baseline, claim-impact and diff verification",
            "design_research_refresh": "aureon.operator.design_research_refresh; redacted local source freshness signal only, with not-cleared artwork retained and no candidate-delivery, package, release, credential, or deployment authority",
            "design_stakeholder_feedback": "aureon.operator.design_stakeholder_feedback; current privacy-safe controlled-code planning signals only, with no raw correspondence, candidate-delivery, package, release, credential, connector, or deployment authority",
            "editorial_asset_provenance": "aureon.operator.design_editorial_asset_provenance; per-asset byte, representation, route and named-human rights closure only, while global artwork remains not-cleared and binary content, private source paths, package, release, credential and deployment authority remain unavailable",
            "editorial_rights_decision_preparation": "aureon.operator.design_editorial_asset_provenance.prepare_editorial_asset_rights_decisions; verifies and records only an exact explicit decision already supplied by the allowlisted named human, never makes or infers a human decision, mutates the canonical manifest or artwork policy, creates candidate readiness, packages, releases, or deploys",
            "editorial_asset_candidate_importer": "aureon.operator.design_editorial_asset_candidate_importer; trusted content-addressed WebP import only after an existing source-bound work order and exact candidate-ready provenance capsule, writing exact image targets inside one staged candidate with rollback and replay verification; it never writes canonical website/, transforms media, uses credentials or network, packages, releases, or deploys",
            "investor_copy_quality": "aureon.operator.design_investor_copy_quality; read-only deterministic rejection of catch-all positioning, hard-coded traction or internal figures, stale snapshots, missing concepts and unqualified claims; it cannot rewrite or release copy",
            "investor_copy_repair": "aureon.operator.design_investor_copy_repair; read-only task and selected-source preflights plus a short-lived exact-HTML source-bound contract and current staged-candidate re-audit, with no source selection, candidate staging, canonical mutation, claim-register mutation, package, release, credential, network, or deployment authority",
            "investor_copy_governance": "aureon.operator.design_investor_copy_governance; verification and full shadow simulation are read-only, while its exact three-file governance apply remains inaccessible without a fresh immutable decision from the named owner plus explicit apply; broad system-access approval is invalid and the protocol has no website, policy, candidate, package, release, credential, network, or deployment authority",
            "hnc_evidence_graph": "aureon.operator.design_hnc_evidence_graph; exact-claim source-neutral semantic component generation with zero binary or network requests, bounded motion and static reduced-motion parity; bundle-ready never means source-selected, candidate-transplanted, visually accepted, packaged or deployed",
            "design_evidence_brief": "aureon.operator.design_evidence_brief; source-bound planning input only, never candidate-delivery, package, release, credential, or deployment authority",
            "staged_delivery_runner": "aureon.autonomous.aureon_public_website_design_runner; immutable brief-to-work-order-to-staged-candidate receipts only, ending at awaiting-owner-promotion before owner-controlled promotion",
            "staged_worker_broker": "aureon.autonomous.aureon_staged_design_worker_broker; one explicit short-lived lease, sealed text-only manifest, exact sandbox diff verification, and no canonical, credential, package, release, promotion, or deployment authority",
            "motion_performance_budget": "aureon.operator.design_motion_performance_budget; installed static-tree audit evidence only and never an inferred pass: a motion pass requires an exact receipt with decision.status pass and eligible_for_next_local_gate true, while candidate, canonical, package, release, credential, network and deployment authority remain none",
            "candidate_test_evidence": "aureon.operator.design_candidate_test_evidence; worker pass strings are not evidence and installation never authorises execution: the reviewed Node toolchain is source-pinned by absolute path, size, SHA-256 and binding digest with no ambient PATH fallback, one bounded subprocess.Popen uses shell false and a 2 MiB per-stream capture ceiling, and structural verification retains origin_attested false, so a separately preserved trusted orchestration seal plus evidence_passed true is required, without candidate validation, promotion, package, release, credential or deployment authority",
            "candidate_qa_control_plane": "installed-not-authorised read-only discovery of the V2 fixed chain: one captured manifest derives both candidate hashes and algorithms, and V2 compiler verifications bind that manifest and the unchanged V1 policy content core; the handle-bound chain requires one immutable claim, runs motion first, runs V2 trusted test evidence second, and permits the initial browser gate only from candidate-qa-verified; neither workers nor QA agents may select policy, commands, thresholds, origins, retries, or order, infer a pass from installation, or gain candidate, canonical, promotion, package, release, credential, or deployment authority",
            "candidate_qa_compiler_verification_ingress": "metadata-only discovery launches no subprocess: imported read-only verifier APIs are drift-check-only and cannot claim pre-import source authentication; the sealed read-only path is direct compiler-file execution under python -I -S -B with the source-closure helper, delegated only by the V2 delivery runner through one bounded subprocess.Popen with shell false, a 64 KiB aggregate/per-stream output ceiling, 300-second timeout and no retry during an explicit candidate-QA action; discovery records executed false and invoked false",
            "owner_source_reconciliation": "aureon.operator.owner_source_reconciliation; only an owner-supplied time-limited v1 decision may retain local canonical source or an exact v2 decision may select the manifest-bound verified live backup for staged work; agents validate and bind the choice but never make it",
            "website_source_rationalisation": "aureon.operator.website_source_rationalisation; PublicWebsiteDesignQA alone may create a proposal-only exact retained/omitted plan during an explicit planning action and validate one separately supplied exact named-owner decision valid for at most four hours. Discovery executes neither operation, omission does not prove readiness, and the protocol grants no autonomous owner decision, staging, deletion, candidate, canonical, package, release, credential, network, publishing, or deployment authority; PublicWebsiteDesignWorker receives no capability",
            "website_runtime_optimisation": "aureon.operator.website_runtime_optimisation; PublicWebsiteDesignQA may perform structural-only measurement-declaration validation, including the required not-executed declaration state. Production proposal compilation and writing are hard-blocked until a reviewed measurement-provenance tool and independently readable derivative artifacts are installed; QA therefore receives no compile grant. Discovery executes no validation or compilation, every downstream acceptance gate remains blocked-not-run, and the protocol grants no source selection, autonomous measurement, transformation, candidate, canonical, package, release, credential, network, publishing, or deployment authority; PublicWebsiteDesignWorker receives no capability",
            "website_runtime_measurement_static_integrity": "aureon.operator.website_runtime_measurement_provenance; PublicWebsiteDesignQA may explicitly read and validate one existing static-integrity artifact against the complete current website manifest, two pre-existing identical replicas, exact stored bytes, payload hashes, and header-derived dimensions, but trusted use requires a fresh hash-authenticated python -I -S -B launcher and imported APIs are non-authoritative test and drift checks. The result is provenance-unverified and production-blocked: it proves neither producer execution, deterministic replay, full media decode, source selection, freshness, browser acceptance, visual acceptance, nor production fitness; it creates no artifact, mutates no source or candidate, grants no package, release, credential, network, publishing, or deployment authority, and PublicWebsiteDesignWorker receives no capability",
            "candidate_initial_gate": "aureon.operator.design_candidate_initial_gate; source-bound focused browser decision before any repeatability series",
            "research_route_attribution": "aureon-website research-attribution; one self-hosted runtime-only Research capture can associate render events with document-root layout, but cannot prove causation, create a candidate, or change a release decision",
            "candidate_visual_review": "aureon.operator.design_candidate_visual_review; source-bound staged browser evidence and separate named human review only",
            "design_learning": "aureon.operator.design_learning_ledger; append-only human-reviewed skill proposal only",
            "test_threshold_changes": "separate governance run",
            "human_visual_acceptance": "required for material brand changes",
            "deployment": "WebsiteOperator owner gate only",
            "credentials": "never available to design agents",
        },
    }


def public_website_design_registry_snapshot(repo_root: Path) -> dict[str, Any]:
    """Expose the source-bound design registry without granting agent authority.

    The coding profile must remain useful in a deliberately small test fixture
    or partial checkout.  In those cases this returns an explicit unavailable
    state rather than fabricating a passing design capability.  A passing
    registry is still discovery evidence only: named human visual acceptance
    and the WebsiteOperator owner gate remain separate release controls.
    """

    source_rationalisation_readiness = website_source_rationalisation_readiness(repo_root)
    unavailable = {
        "available": False,
        "state": "unavailable",
        "verified": False,
        "release_eligible": False,
        "deployment_authority": "none",
        "website_source_rationalisation_readiness": source_rationalisation_readiness,
        "website_runtime_optimisation_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "proposal_compilation_protocol_available": False,
            "measurement_validation_protocol_available": False,
            "measurement_validation_scope": "unavailable",
            "measurement_provenance_verification_available": False,
            "production_compilation_blocked": True,
            "production_compilation_blocker": ("blocked-reviewed-measurement-provenance-tool-not-installed"),
            "browser_acceptance_contract_available": False,
            "measurement_schema_available": False,
            "proposal_schema_available": False,
            "proposal_compilation_executed": False,
            "measurement_validation_executed": False,
            "measurement_evidence_required": True,
            "autonomous_measurement_evidence": False,
            "source_selection_required": True,
            "autonomous_source_selection": False,
            "transformations_executed": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "website_runtime_measurement_static_integrity_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "capability_scope": "read-validate-only",
            "static_integrity_validation_available": False,
            "static_integrity_validation_executed": False,
            "measurement_provenance_verification_available": False,
            "production_eligible": False,
            "eligible_for_proposal_compilation": False,
            "production_compilation_blocked": True,
            "worker_available": False,
            "worker_executed": False,
            "artifact_emission_available": False,
            "artifact_emission_executed": False,
            "trusted_static_integrity_execution_path": "unavailable",
            "imported_api_authoritative": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "owner_source_reconciliation_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "validation_protocol_available": False,
            "v1_retain_local_supported": False,
            "v2_verified_live_backup_supported": False,
            "owner_decision_required": True,
            "autonomous_source_selection": False,
            "candidate_delivery_ready": False,
            "canonical_website_mutation": "none",
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
        },
        "design_research_refresh_readiness": {
            "available": False,
            "state": "unavailable",
            "current": False,
            "planning_signal_available": False,
            "candidate_delivery_ready": False,
            "delivery_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "stakeholder_feedback_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "current": False,
            "planning_only": True,
            "planning_signal_available": False,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "release_authority": "none",
            "package_authority": "none",
            "deployment_authority": "none",
            "raw_correspondence_access": "none",
        },
        "editorial_rights_decision_preparation_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "preparation_protocol_available": False,
            "human_decision_input_required": True,
            "autonomous_human_decision": False,
            "rights_inference": "never",
            "canonical_manifest_mutation": "never",
            "global_artwork_policy_mutation": "never",
            "candidate_use_rights_ready": False,
            "candidate_asset_ready": False,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
            "network_access": "none",
            "connector_access": "none",
        },
        "editorial_asset_provenance_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "integrity_verified": False,
            "public_use_ready": False,
            "candidate_asset_ready": False,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
        },
        "editorial_asset_importer_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "import_protocol_available": False,
            "receipt_verification_available": False,
            "candidate_asset_ready": False,
            "candidate_import_ready": False,
            "candidate_delivery_ready": False,
            "canonical_website_mutation": "never",
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
            "network_access": "none",
        },
        "investor_copy_quality_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "policy_current": False,
            "copy_ready": False,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
        },
        "investor_copy_repair_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "source_bound_protocol_available": False,
            "task_preflight_available": False,
            "selected_source_preflight_available": False,
            "contract_creation_available": False,
            "contract_verification_available": False,
            "candidate_reaudit_available": False,
            "current_contract_ready": False,
            "candidate_copy_ready": False,
            "candidate_delivery_ready": False,
            "canonical_website_mutation": "never",
            "candidate_staging": "never",
            "claim_register_mutation": "never",
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
            "network_access": "none",
        },
        "investor_copy_governance_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "decision_verification_available": False,
            "simulation_available": False,
            "apply_protocol_available": False,
            "implementation_tooling_verified": False,
            "exact_owner_decision_required": True,
            "autonomous_owner_decision": False,
            "broad_access_approval_valid": False,
            "current_owner_decision_present": False,
            "current_apply_authorised": False,
            "current_apply_ready": False,
            "canonical_governance_mutation": ("never without exact fresh owner decision and explicit apply"),
            "website_mutation": "never",
            "policy_mutation": "never",
            "candidate_authority": "none",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
            "credential_access": "none",
            "network_access": "none",
        },
        "hnc_evidence_graph_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "component_bundle_ready": False,
            "candidate_transplant_ready": False,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
        },
        "design_evidence_brief_readiness": {
            "available": False,
            "state": "unavailable",
            "brief_ready": False,
            "planning_pipeline_available": False,
            "candidate_delivery_ready": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "staged_design_worker_broker_readiness": {
            "available": False,
            "state": "unavailable",
            "lease_protocol_available": False,
            "candidate_delivery_ready": False,
            "canonical_website_mutation": "never",
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
        },
        "motion_performance_budget_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "audit_protocol_available": False,
            "receipt_replay_available": False,
            "audit_executed": False,
            "decision_status": "not-evaluated",
            "decision_passed": False,
            "eligible_for_next_local_gate": False,
            "pass_inferred_from_installation": False,
            "candidate_authority": "none",
            "candidate_validation_authority": "none",
            "promotion_authority": "none",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "candidate_test_evidence_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "execution_protocol_available": False,
            "structural_verification_available": False,
            "immutable_writer_available": False,
            "reviewed_node_toolchain": {
                "protocol_available": False,
                "schema": "aureon.node-toolchain-binding.v1",
                "locator_authority": "reviewed-source-pinned-absolute-path-no-path-fallback",
                "absolute_path_size_sha256_bound": False,
                "ambient_path_fallback_allowed": False,
                "resolved": False,
                "executed": False,
            },
            "bounded_process": {
                "protocol_available": False,
                "launcher": "subprocess.Popen",
                "shell": False,
                "max_stream_bytes": 2 * 1024 * 1024,
                "retry_authority": "none",
                "executed": False,
            },
            "execution_authorised": False,
            "test_suite_executed": False,
            "worker_pass_strings_are_evidence": False,
            "structural_verification_passed": False,
            "origin_attested": False,
            "trusted_orchestration_seal_required": True,
            "evidence_passed": False,
            "pass_inferred_from_installation": False,
            "candidate_validation_authority": "none",
            "promotion_authority": "none",
            "package_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "candidate_qa_control_plane_readiness": {
            "available": False,
            "installed": False,
            "state": "unavailable",
            "static_qa_available": False,
            "fixed_test_policy_compiler_available": False,
            "fixed_motion_policy_compiler_available": False,
            "handle_bound_immutable_writer_available": False,
            "v2_runner_available": False,
            "candidate_test_evidence_runtime_available": False,
            "v2_schema_available": False,
            "v2_runbook_available": False,
            "compiler_verification_ingress": {
                "discovery_mode": "metadata-only-no-subprocess",
                "discovery_subprocess_launched": False,
                "imported_api": {
                    "scope": "drift-check-only",
                    "motion_read_only_verifier_available": False,
                    "test_read_only_verifier_available": False,
                    "pre_import_source_authentication": False,
                },
                "sealed_direct_file_read_only": {
                    "protocol_available": False,
                    "motion_protocol_available": False,
                    "test_protocol_available": False,
                    "executed": False,
                    "python_flags": ["-I", "-S", "-B"],
                    "motion_verify_flag": "--verify-config",
                    "test_verify_flag": "--verify-policy",
                    "source_closure_helper_available": False,
                },
                "runner_delegation": {
                    "protocol_available": False,
                    "required_for_candidate_qa": True,
                    "bounded_popen_protocol_available": False,
                    "launcher": "subprocess.Popen",
                    "shell": False,
                    "timeout_seconds": 300,
                    "max_aggregate_output_bytes": 64 * 1024,
                    "retry_authority": "none",
                    "invoked": False,
                },
            },
            "execution_order_enforced": False,
            "qa_execution_authorised": False,
            "qa_executed": False,
            "qa_passed": False,
            "pass_inferred_from_installation": False,
            "candidate_creation_authority": "none",
            "candidate_mutation_authority": "none",
            "candidate_validation_authority": "none",
            "canonical_website_mutation": "none",
            "promotion_authority": "none",
            "package_authority": "none",
            "release_authority": "none",
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "human_visual_acceptance": "required for material brand changes",
        "owner_release_boundary": "WebsiteOperator owner gate only",
        "authority": {},
        "sources": [],
        "verification": {
            "passed": False,
            "release_eligible": False,
            "deployment_authority": "none",
        },
        "error": "",
    }
    try:
        from aureon.operator.design_capability_registry import discover_design_capability_registry

        registry = discover_design_capability_registry(repo_root)
        verification = registry.get("verification")
        authority = registry.get("authority")
        verified = (
            isinstance(verification, dict)
            and verification.get("passed") is True
            and verification.get("release_eligible") is False
            and verification.get("deployment_authority") == "none"
            and isinstance(authority, dict)
            and authority.get("release_eligibility") == "always-false"
            and authority.get("deployment_authority") == "none"
            and authority.get("release_authority") == "WebsiteOperator owner gate only"
        )
        return {
            "available": True,
            "state": "verified" if verified else "needs_repair",
            "verified": verified,
            "release_eligible": False,
            "deployment_authority": "none",
            "human_visual_acceptance": "required for material brand changes",
            "owner_release_boundary": "WebsiteOperator owner gate only",
            "authority": authority if isinstance(authority, dict) else {},
            "sources": registry.get("sources") if isinstance(registry.get("sources"), list) else [],
            "website_source_rationalisation_readiness": source_rationalisation_readiness,
            "website_runtime_optimisation_readiness": (
                registry.get("website_runtime_optimisation_readiness")
                if isinstance(registry.get("website_runtime_optimisation_readiness"), dict)
                else unavailable["website_runtime_optimisation_readiness"]
            ),
            "website_runtime_measurement_static_integrity_readiness": (
                registry.get("website_runtime_measurement_static_integrity_readiness")
                if isinstance(
                    registry.get("website_runtime_measurement_static_integrity_readiness"),
                    dict,
                )
                else unavailable["website_runtime_measurement_static_integrity_readiness"]
            ),
            "owner_source_reconciliation_readiness": (
                registry.get("owner_source_reconciliation_readiness")
                if isinstance(registry.get("owner_source_reconciliation_readiness"), dict)
                else unavailable["owner_source_reconciliation_readiness"]
            ),
            "design_research_refresh_readiness": (
                registry.get("design_research_refresh_readiness")
                if isinstance(registry.get("design_research_refresh_readiness"), dict)
                else unavailable["design_research_refresh_readiness"]
            ),
            "stakeholder_feedback_readiness": (
                registry.get("stakeholder_feedback_readiness")
                if isinstance(registry.get("stakeholder_feedback_readiness"), dict)
                else unavailable["stakeholder_feedback_readiness"]
            ),
            "editorial_rights_decision_preparation_readiness": (
                registry.get("editorial_rights_decision_preparation_readiness")
                if isinstance(
                    registry.get("editorial_rights_decision_preparation_readiness"),
                    dict,
                )
                else unavailable["editorial_rights_decision_preparation_readiness"]
            ),
            "editorial_asset_provenance_readiness": (
                registry.get("editorial_asset_provenance_readiness")
                if isinstance(registry.get("editorial_asset_provenance_readiness"), dict)
                else unavailable["editorial_asset_provenance_readiness"]
            ),
            "editorial_asset_importer_readiness": (
                registry.get("editorial_asset_importer_readiness")
                if isinstance(registry.get("editorial_asset_importer_readiness"), dict)
                else unavailable["editorial_asset_importer_readiness"]
            ),
            "investor_copy_quality_readiness": (
                registry.get("investor_copy_quality_readiness")
                if isinstance(registry.get("investor_copy_quality_readiness"), dict)
                else unavailable["investor_copy_quality_readiness"]
            ),
            "investor_copy_repair_readiness": (
                registry.get("investor_copy_repair_readiness")
                if isinstance(registry.get("investor_copy_repair_readiness"), dict)
                else unavailable["investor_copy_repair_readiness"]
            ),
            "investor_copy_governance_readiness": (
                registry.get("investor_copy_governance_readiness")
                if isinstance(registry.get("investor_copy_governance_readiness"), dict)
                else unavailable["investor_copy_governance_readiness"]
            ),
            "hnc_evidence_graph_readiness": (
                registry.get("hnc_evidence_graph_readiness")
                if isinstance(registry.get("hnc_evidence_graph_readiness"), dict)
                else unavailable["hnc_evidence_graph_readiness"]
            ),
            "design_evidence_brief_readiness": (
                registry.get("design_evidence_brief_readiness")
                if isinstance(registry.get("design_evidence_brief_readiness"), dict)
                else unavailable["design_evidence_brief_readiness"]
            ),
            "staged_design_worker_broker_readiness": (
                registry.get("staged_design_worker_broker_readiness")
                if isinstance(registry.get("staged_design_worker_broker_readiness"), dict)
                else unavailable["staged_design_worker_broker_readiness"]
            ),
            "motion_performance_budget_readiness": (
                registry.get("motion_performance_budget_readiness")
                if isinstance(registry.get("motion_performance_budget_readiness"), dict)
                else unavailable["motion_performance_budget_readiness"]
            ),
            "candidate_test_evidence_readiness": (
                registry.get("candidate_test_evidence_readiness")
                if isinstance(registry.get("candidate_test_evidence_readiness"), dict)
                else unavailable["candidate_test_evidence_readiness"]
            ),
            "candidate_qa_control_plane_readiness": (
                registry.get("candidate_qa_control_plane_readiness")
                if isinstance(registry.get("candidate_qa_control_plane_readiness"), dict)
                else unavailable["candidate_qa_control_plane_readiness"]
            ),
            "verification": verification if isinstance(verification, dict) else unavailable["verification"],
            "error": "",
        }
    except Exception as exc:
        unavailable["error"] = f"{type(exc).__name__}: {exc}"
        return unavailable


def coding_logic_rules() -> list[CodingLogicRule]:
    return [
        CodingLogicRule(
            id="public_website.design_logic",
            who=[
                "RepoCartographer",
                "WebLearningScout",
                "PublicWebsiteDesignWorker",
                "PublicWebsiteDesignQA",
                "Stakeholder Insight & Privacy Editor",
                "SecurityReviewer",
            ],
            what="Institutional public-site research, IA, copy, claims, graphics, purposeful motion, browser QA, and release-closure work.",
            where=[
                "website/**",
                "aureon/operator/website_operator.py",
                "aureon/operator/design_stakeholder_feedback.py",
                "data/website_operator/design_stakeholder_feedback.v1.json",
                "aureon/operator/design_editorial_asset_provenance.py",
                "data/website_operator/editorial_asset_provenance.v1.json",
                "aureon/operator/design_editorial_asset_candidate_importer.py",
                "aureon/operator/design_investor_copy_quality.py",
                "aureon/operator/design_investor_copy_governance.py",
                "data/website_operator/investor_copy_quality_policy.v1.json",
                "aureon/operator/design_hnc_evidence_graph.py",
                "data/website_operator/hnc_evidence_graph.v1.json",
                "aureon/operator/secure_immutable_artifact.py",
                "aureon/operator/design_candidate_static_qa.py",
                "aureon/operator/design_candidate_motion_policy_compiler.py",
                "aureon/operator/design_candidate_test_policy_compiler.py",
                "aureon/operator/design_motion_performance_budget.py",
                "aureon/operator/design_candidate_test_evidence.py",
                "aureon/autonomous/aureon_public_website_design_runner.py",
                "skills/aureon-harmonic-design-suite/**",
                "tools/aureon_website_*",
                "tests/test_website_operator.py",
                "tests/test_design_motion_performance_budget.py",
                "tests/test_design_candidate_test_evidence.py",
                "tests/test_secure_immutable_artifact.py",
                "tests/test_design_candidate_static_qa.py",
                "tests/test_design_candidate_motion_policy_compiler.py",
                "tests/test_design_candidate_test_policy_compiler.py",
                "tests/test_public_website_design_runner.py",
            ],
            when=[
                "A goal asks to design, redesign, benchmark, write, animate, audit, or package the public website.",
                "A design finding, stale benchmark, unsupported claim, browser regression, or incomplete release closure is observed.",
                "A current privacy-safe stakeholder signal requests a route-bounded design response.",
                "Editorial artwork is referenced, proposed, replaced, or represented as evidence.",
                "Investor copy contains a hard-coded metric, catch-all category, stale snapshot, hype term, or missing wedge concept.",
                "An exact owner-approved investor-copy claim-governance delta needs read-only verification, shadow simulation, or explicitly gated application.",
                "A source-neutral HNC evidence-control component needs exact-claim, motion and performance proof before source selection.",
                "A local candidate needs objective design-council proof before human visual review.",
            ],
            how=[
                "Route through the public_website_design_cycle intent before generic visual generation.",
                "Require a passing current design-evidence brief before deriving work-order scope; brief-ready is not candidate-delivery-ready.",
                "Audit only the canonical human-redacted stakeholder declaration; never expose correspondence, identities, quotations, provider metadata, URLs, finance, or free-form rationale to a worker.",
                "Bind the audited brief, route claim capsules, source, claims, benchmark, config, and website-tree hashes.",
                "Bind the current stakeholder declaration and exact route feedback-capsule hashes, then require a complete controlled-code response manifest that closes every sealed signal without widening its route or claim scope.",
                "Keep global artwork not-cleared; require exact per-asset integrity, representation boundary, route and named-human rights closure, and expose only redacted capsule-set and public-coverage hashes.",
                "Import approved editorial bytes only through the trusted content-addressed importer after an existing source-bound work order; replay-verify its immutable candidate-local receipt and never give binary write authority to the staged worker.",
                "Run the deterministic investor-copy audit and treat every blocker as a veto; do not turn static attention totals or internal finance into public proof.",
                "Treat investor-copy governance verification and simulation as read-only; reject broad access as approval, and expose apply only for the exact fresh immutable named-owner decision plus explicit apply.",
                "Generate HNC graph bundles only from the current claim register, preserve static first-paint and reduced-motion parity, and require a fresh source-bound work order before candidate transplant.",
                "Advance the staged delivery runner only through its immutable receipt chain; stop at awaiting-owner-promotion.",
                "Issue or consume a staged worker lease only through an explicit structured request; accept one sealed text-only manifest and broker verification, never a free-form website write.",
                "Treat worker-declared pass strings as untrusted request bookkeeping; accept candidate-test evidence only after a separately preserved trusted orchestration seal and strict verification that retains origin_attested false and reports evidence_passed true.",
                "Treat static motion/resource-budget installation as protocol discovery only; a motion pass requires the exact receipt decision.status pass and eligible_for_next_local_gate true.",
                "Treat candidate-QA control-plane discovery as installed-not-authorised metadata that launches no subprocess; imported verifier APIs are drift-check-only, while sealed read-only compiler replay requires direct compiler-file python -I -S -B execution delegated by the V2 runner. Then derive both tree hashes and algorithms from one candidate byte manifest, require both verifications to bind that manifest and the unchanged V1 policy content core, consume one handle-bound V2 attempt, run motion first, run V2 trusted test evidence only after motion passes, and enter the initial browser gate only from candidate-qa-verified.",
                "Never choose or relax a test, command, threshold, origin, retry, or QA order, and never infer QA execution or pass from source availability.",
                "Change only the paths allowed by one website work order and preserve unrelated dirty state.",
                "Use HNC as the weighted evidence-coherence loop; keep WCAG, performance, browser, claims, and package gates authoritative.",
                "Reject regressions, rerun the exact failed check, then rerun the full suite.",
                "Stop at package readiness; WebsiteOperator alone performs backup, owner gate, deploy, and live read-back.",
            ],
            validation=[
                "WebsiteOperator design-cycle hard gates",
                "claims and metadata audit",
                "stakeholder-feedback freshness and response-manifest closure audit",
                "editorial-asset provenance, representation, current-use and capsule-closure audit",
                "trusted editorial import receipt, exact candidate-byte and replay-verification audit",
                "investor-copy category, figure, freshness, concept and claim-boundary audit",
                "exact owner-decision, proposal, shadow-audit and three-file governance transaction boundary",
                "HNC graph exact-claim, semantic-order, zero-resource, motion and byte-budget audit",
                "deterministic static motion/resource-budget receipt decision and exact replay",
                "trusted hash-bound candidate-test receipt seal, structural verification, and evidence_passed state",
                "responsive browser and interaction matrix",
                "reduced-motion and keyboard parity",
                "performance and asset budgets",
                "exact runtime dependency closure",
                "source-plan, measurement-evidence, browser-contract, and projected-runtime hashes",
                "focused pytest and extracted-package smoke",
            ],
            evidence=[
                "source-tree and test-policy hashes",
                "competitor source ledger",
                "privacy-safe stakeholder declaration, route capsule, and complete response-manifest hashes",
                "redacted editorial-asset manifest, capsule-set, route-capsule and public-coverage hashes",
                "investor-copy policy hash and aggregate blocker counts",
                "owner-decision, proposal, validation, simulated after-state and immutable governance-application hashes",
                "source-neutral HNC graph contract, output and bundle hashes",
                "motion/performance configuration, doctrine, source-tree, decision and receipt hashes",
                "candidate-test policy, independently sealed receipt, verifier and evidence-pass hashes",
                "V2 motion-config and test-policy compiler replay hashes, single captured-manifest dual-hash binding, unchanged V1 policy content-core hash, handle-bound V2 attempt claim, and candidate-qa-verified receipt before browser entry",
                "design council verdict",
                "route screenshots and browser errors",
                "changed-path and package manifests",
                "runtime-optimisation structural validation with production compilation explicitly blocked",
            ],
            safety_boundary=(
                "Design agents may research, edit, test, reject, learn, and package locally; they may "
                "not create a named-owner decision or invoke investor-copy governance apply, and "
                "credentials and production publication remain unavailable. Worker pass strings, "
                "installed QA modules, and structural receipt validity alone never grant candidate, "
                "promotion, package, release, or deployment authority. Candidate-QA discovery never "
                "executes the chain, selects policy or thresholds, or implies a pass. Runtime optimisation "
                "production compilation is hard-blocked until reviewed measurement provenance and readable "
                "derivative artifacts exist; it cannot encode, prune, rewrite, stage, package, or deploy."
            ),
        ),
        CodingLogicRule(
            id="public_website.source_rationalisation_logic",
            who=["PublicWebsiteDesignQA"],
            what=(
                "Proposal-only website source rationalisation planning and validation of one exact "
                "separately supplied named-owner decision."
            ),
            where=[
                "aureon/operator/website_source_rationalisation.py",
                "tools/run-website-source-rationalisation.py",
                "docs/runbooks/WEBSITE_SOURCE_RATIONALISATION.md",
                "artifacts/website-operator/source-rationalisations/plans/**",
                "artifacts/website-operator/source-rationalisations/owner-decisions/**",
                "artifacts/website-operator/source-rationalisations/validations/**",
                "tests/test_website_source_rationalisation.py",
            ],
            when=[
                "Normal live reconciliation has selected the canonical website and an exact retained/omitted projection needs named-owner review.",
                "A separately supplied exact source-rationalisation decision needs freshness and hash-binding validation.",
            ],
            how=[
                "Discover the protocol by metadata-only AST inspection without importing the module, launching a subprocess, or executing planning or validation.",
                "Route the two L0 capabilities only to PublicWebsiteDesignQA; PublicWebsiteDesignWorker receives neither capability nor module access.",
                "Bind the unchanged canonical tree, reviewed VerifyOnly runtime closure, retained/omitted partition and fixed footprint projections in a proposal-only plan.",
                "Require a separately supplied exact named-human owner decision whose approval window is no more than four hours, then validate it without staging.",
                "Treat not-in-public-runtime-closure only as an omission reason, never as deletion safety, source completeness, candidate readiness, QA pass, package readiness, or release readiness.",
                "Stop after immutable validation evidence; any future stage needs a separate reviewed implementation and authority gate.",
            ],
            validation=[
                "focused website-source-rationalisation pytest",
                "metadata-only symbol and runbook readiness inspection",
                "proposal, closure, partition, four-budget and owner-decision binding checks",
                "no-planning-execution discovery assertion",
            ],
            evidence=[
                "module and runbook paths plus required-symbol inventory",
                "plan file and payload hashes, source/retained tree hashes, and omitted-manifest hash",
                "fixed budget projections and blocked-candidate-qa-not-run state",
                "named-owner decision and immutable validation hashes with maximum four-hour freshness",
            ],
            safety_boundary=(
                "PublicWebsiteDesignQA may plan and validate only during an explicit source-rationalisation "
                "action. Discovery executes neither operation. It cannot create an owner decision, stage or "
                "delete source, create or mutate a candidate, mutate canonical website/, package, release, "
                "access credentials or network, publish, or deploy. PublicWebsiteDesignWorker has no access."
            ),
        ),
        CodingLogicRule(
            id="public_website.runtime_optimisation_proposal_logic",
            who=["PublicWebsiteDesignQA"],
            what=(
                "Structurally validate runtime measurement declarations while keeping production proposal "
                "compilation blocked pending reviewed provenance tooling and readable derivative artifacts."
            ),
            where=[
                "aureon/operator/website_runtime_optimisation.py",
                "tools/run-website-runtime-optimisation.py",
                "data/website_operator/browser_acceptance_contract.v1.json",
                "docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_MEASUREMENT_V1.schema.json",
                "docs/research/schemas/AUREON_WEBSITE_RUNTIME_OPTIMISATION_PROPOSAL_V1.schema.json",
                "docs/runbooks/WEBSITE_RUNTIME_OPTIMISATION.md",
                "artifacts/website-operator/runtime-optimisations/measurements/**",
                "artifacts/website-operator/runtime-optimisations/proposals/**",
                "tests/test_website_runtime_optimisation.py",
            ],
            when=[
                "Owner-controlled live backup and source reconciliation have selected one exact source.",
                "A current source-rationalisation plan still matches the canonical website tree.",
                "Structural declaration review is needed; this is not provenance, freshness, or derivative proof.",
            ],
            how=[
                "Discover the protocol through authenticated AST and JSON inspection without import, subprocess, planning, or measurement execution.",
                "For structural validation, accept only explicit exact paths and never select a latest file.",
                "Reject every production compiler or writer invocation with the fixed measurement-provenance blocker.",
                "Do not treat a repo-relative tool path, self-supplied hash, or projected derivative declaration as measurement proof.",
                "Before any future re-enable, require a reviewed measurement-tool pin, recorded invocation provenance, and independently readable derivative artifact path, SHA-256, bytes, and decoded dimensions.",
                "Keep every browser, accessibility, progressive-enhancement, crawler, research, visual-regression, and human gate blocked-not-run.",
                "Stop after structural validation; no proposal artifact may be created in the current state.",
            ],
            validation=[
                "focused website-runtime-optimisation pytest",
                "Ruff, mypy, and Python bytecode compilation",
                "source, launcher, contract, and reviewed-tool pin inspection",
                "source-drift, stale-input, binding-tamper, authority-escalation, and fabricated-pass hostile tests",
            ],
            evidence=[
                "exact source-plan file and payload hashes",
                "strict measurement-evidence file and payload hashes",
                "browser-acceptance contract file and payload hashes",
                "pinned measurement and proposal JSON Schema hashes",
                "fixed production measurement-provenance blocker read-back",
                "absence of any production proposal output artifact",
            ],
            safety_boundary=(
                "PublicWebsiteDesignQA can perform structural-only measurement-declaration validation; it "
                "cannot compile or write a production proposal. It cannot select source, create measurement "
                "evidence, run encoders or CSS transformations, rewrite references, remove source, mutate a "
                "candidate or canonical website, package, release, access credentials or network, publish, "
                "or deploy. PublicWebsiteDesignWorker receives no access."
            ),
        ),
        CodingLogicRule(
            id="public_website.runtime_measurement_static_integrity_logic",
            who=["PublicWebsiteDesignQA"],
            what=(
                "Read and validate an explicitly supplied existing runtime-measurement static-integrity "
                "artifact while keeping provenance unverified and production blocked."
            ),
            where=[
                "aureon/operator/website_runtime_measurement_provenance.py",
                "tools/run-website-runtime-measurement-provenance.py",
                "docs/research/schemas/AUREON_WEBSITE_RUNTIME_MEASUREMENT_STATIC_INTEGRITY_V1.schema.json",
                "tests/test_website_runtime_measurement_provenance.py",
            ],
            when=[
                "One exact existing artifact and its two pre-existing identical replicas are supplied explicitly.",
                "Stored-byte, manifest, arithmetic, and header-derived dimension integrity needs read-only review.",
            ],
            how=[
                "Use a fresh reviewed hash-authenticated python -I -S -B isolated launcher and exact paths; never select a latest artifact or treat an imported API call as authoritative.",
                "Bind the complete current website manifest before and after validation, then require two identical replica payloads separately stored at distinct paths.",
                "Validate exact stored bytes, payload hashes, arithmetic, and PNG, JPEG, or WebP header-derived dimensions only.",
                "Report static-integrity-valid, provenance-unverified, and production-blocked without inferring producer execution, deterministic replay, full decode, freshness, browser acceptance, or visual acceptance.",
                "Stop without creating evidence, invoking encoders or CSS transformations, mutating references or source, compiling a proposal, staging, packaging, releasing, or deploying.",
            ],
            validation=[
                "focused runtime-measurement static-integrity pytest",
                "Ruff, strict mypy, and Python bytecode compilation",
                "source, launcher, and JSON Schema reviewed-hash inspection",
                "authority-mutation, path-link, replay-copy, time-skew, malformed-media, and fabricated-pass hostile tests",
            ],
            evidence=[
                "complete current website manifest and tree hash",
                "two pre-existing replica paths, exact bytes, and payload hashes",
                "source and derivative stored-byte hashes, byte counts, and header-derived dimensions",
                "fixed static-integrity-valid, provenance-unverified, production-blocked CLI status and no-authority read-back",
            ],
            safety_boundary=(
                "PublicWebsiteDesignQA can validate only an existing explicit artifact. Header inspection is not "
                "a full media decode, matching copies do not prove producer execution or deterministic replay, "
                "and current source equality does not prove source selection or freshness. The protocol creates "
                "no artifact, cannot transform or mutate any tree, cannot compile a production proposal, and "
                "grants no candidate, canonical, package, release, credential, network, publishing, or deployment "
                "authority. Same-process imported APIs are non-authoritative; trusted use requires a fresh "
                "hash-authenticated python -I -S -B launcher. PublicWebsiteDesignWorker receives no access."
            ),
        ),
        CodingLogicRule(
            id="frontend.interface_logic",
            who=["RepoCartographer", "ImplementationWorker", "TestPilot"],
            what="React/TypeScript interface work, generated console panels, hooks, services, styling, and browser smoke checks.",
            where=[
                "frontend/src/App.tsx",
                "frontend/src/components/**",
                "frontend/src/hooks/**",
                "frontend/src/services/**",
                "frontend/public/*.json",
            ],
            when=[
                "A goal asks for a visible console, operational dashboard, adapter, or human-readable status surface.",
                "A public JSON manifest already exists or the task creates one through the bounded local writer.",
                "The frontend build or browser smoke check is part of the acceptance evidence.",
            ],
            how=[
                "Read the public manifest contract before rendering UI fields.",
                "Prefer generated read-only operational cards for system evidence.",
                "Mount new generated panels from App.tsx and keep imports explicit.",
                "Run npm build or a focused browser smoke check after UI edits.",
            ],
            validation=[
                "npm run build",
                "browser smoke test on the local console",
                "public manifest loads with no stale fake state",
            ],
            evidence=[
                "frontend/public manifest path",
                "generated component path",
                "App.tsx mount line",
                "build or smoke-test result",
            ],
            safety_boundary="Frontend panels may display evidence and operator actions only; they may not reveal secrets or bypass runtime gates.",
        ),
        CodingLogicRule(
            id="backend.autonomous_logic",
            who=["RepoCartographer", "ImplementationWorker", "SecurityReviewer", "TestPilot"],
            what="Python autonomous modules, goal routing, self-repair, observer refresh, mind hub, and coding-agent orchestration.",
            where=[
                "aureon/autonomous/**",
                "aureon/core/goal_execution_engine.py",
                "aureon/inhouse_ai/**",
                "tests/test_*",
            ],
            when=[
                "A goal needs a new internal capability, agent skill, repo-learning loop, or evidence-producing workflow.",
                "Existing goal routes cannot classify the operator request accurately.",
                "The change needs repeatable local tests and a state/audit artifact.",
            ],
            how=[
                "Classify the request into an intent before writing code.",
                "Add the smallest module or route that fits existing GoalExecutionEngine patterns.",
                "Emit state, docs/audits, and frontend/public evidence when the capability is user-visible.",
                "Add focused pytest coverage for routing, files written, and validation semantics.",
            ],
            validation=[
                "python -m compileall",
                "focused pytest for the route/module",
                "GoalExecutionEngine validation result is valid",
            ],
            evidence=["goal id", "intent", "authoring path", "state artifact", "test command"],
            safety_boundary="Autonomous logic may author only scoped repository files through the bounded local writer; external mutations remain outside this layer.",
        ),
        CodingLogicRule(
            id="trading.exchange_logic",
            who=["RepoCartographer", "WebLearningScout", "SecurityReviewer", "TestPilot"],
            what="Exchange clients, market telemetry, rate governors, flight tests, stale-data logic, and order-intent evidence.",
            where=[
                "aureon/exchanges/**",
                "aureon/bots/**",
                "state/unified_runtime_status.json",
                "tests/test_unified_market_status_server.py",
            ],
            when=[
                "A task changes Binance, Kraken, Alpaca, Capital, spot, margin, market data, or trading readiness logic.",
                "Official exchange documentation or rate-limit behavior may have changed.",
                "The runtime reports stale ticks, guard blockers, or missing exchange coverage.",
            ],
            how=[
                "Use WebLearningScout to fetch official exchange docs before changing client behavior.",
                "Preserve stale-data, open-position, rate-limit, and reboot-window evidence.",
                "Separate shadow-trade validation from live order mutation.",
                "Expose status through the runtime manifest and console rather than hidden logs only.",
            ],
            validation=[
                "flight-test endpoint",
                "unified market status tests",
                "API governor utilization evidence",
                "shadow-trade reconciliation",
            ],
            evidence=[
                "official docs url",
                "exchange client path",
                "runtime status snapshot",
                "shadow/live mode field",
            ],
            safety_boundary="Trading code can improve observation, shadow validation, and gated order intent; it cannot remove exchange/risk/runtime gates.",
        ),
        CodingLogicRule(
            id="accounting.legal_pack_logic",
            who=["RepoCartographer", "WebLearningScout", "SecurityReviewer", "TestPilot"],
            what="UK accounting, HMRC/Companies House support packs, CT600 support data, filing checklists, and manual-only evidence.",
            where=[
                "Kings_Accounting_Suite/**",
                "aureon/queen/accounting_context_bridge.py",
                "docs/audits/accounting_system_registry.json",
                "tests/test_*accounting*",
            ],
            when=[
                "A task changes statutory filing packs, tax computations, CT financial-year splits, or requirements matrices.",
                "Official HMRC or Companies House guidance is cited or needs refreshing.",
                "The output could affect manual filing, payment, or legal records.",
            ],
            how=[
                "Keep full accounting-period totals unchanged unless a test proves the change is additive.",
                "Add support breakdowns as separate files/sections with reconciliation fields.",
                "Cite official sources in support notes and keep filings manual-only.",
                "Run focused accounting tests before regenerating packs.",
            ],
            validation=[
                "statutory pack tests",
                "requirements matrix includes new support file",
                "manual-only filing boundary remains visible",
            ],
            evidence=[
                "source transaction count",
                "period/fiscal split",
                "reconciliation tolerance",
                "official guidance url",
            ],
            safety_boundary="Accounting logic can prepare support documents only; it cannot submit filings, make payments, or expose credentials.",
        ),
        CodingLogicRule(
            id="voice.knowledge_expression_logic",
            who=["RepoCartographer", "ImplementationWorker", "SecurityReviewer"],
            what="Voice core, expression profile, HNC/Auris state translation, document artifacts, and human-readable prose.",
            where=[
                "aureon/vault/voice/**",
                "state/aureon_expression_profile.json",
                "docs/audits/aureon_harmonic_affect_state.json",
                "tests/test_*voice*",
            ],
            when=[
                "A task asks Aureon to explain itself, write documents, translate state, or reduce raw telemetry into human language.",
                "The output risks repeating template fragments or dumping raw internal data.",
                "The response needs grounded state with evidence retained separately.",
            ],
            how=[
                "Classify sources into voice facets before composing prose.",
                "Translate sensory/HNC fields into readable language while preserving raw evidence paths.",
                "Run repetition and redaction checks before writing public artifacts.",
                "Route document and console wording through the same voice profile.",
            ],
            validation=[
                "voice unit tests",
                "novelty/repetition report",
                "redaction scan",
                "artifact path evidence",
            ],
            evidence=["facets used", "state inputs", "redaction result", "novelty checks"],
            safety_boundary="Voice may describe synthetic state as system-state translation, not as unverified human biological sensation.",
        ),
        CodingLogicRule(
            id="quality.security_repair_logic",
            who=["SecurityReviewer", "TestPilot", "ImplementationWorker"],
            what="Test failures, build failures, secret scans, unsafe shell patterns, and self-repair work orders.",
            where=[
                "tests/**",
                "docs/audits/aureon_repo_self_repair.json",
                "state/aureon_*last_run.json",
                "frontend/package.json",
            ],
            when=[
                "A build/test fails or a generated artifact reports blockers.",
                "A public manifest could include secrets, private keys, or personal filing identifiers.",
                "A code change touches shared runtime, security, trading, or legal surfaces.",
            ],
            how=[
                "Capture the failing command and shortest useful output.",
                "Patch only the owned file set for the active goal.",
                "Rerun the exact failing command, then the focused regression suite.",
                "Publish blocker and repair evidence for the next agent loop.",
            ],
            validation=[
                "pytest return code",
                "npm build return code",
                "secret pattern scan",
                "self-repair status",
            ],
            evidence=["command", "return code", "stdout/stderr tail", "files changed"],
            safety_boundary="Repair agents may not use destructive git commands or revert unrelated user changes.",
        ),
    ]


def build_coding_logic_map(profile: dict[str, Any]) -> dict[str, Any]:
    rules = [rule.to_dict() for rule in coding_logic_rules()]
    file_area_index: dict[str, dict[str, Any]] = {}
    for rule in rules:
        for pattern in rule["where"]:
            file_area_index[pattern] = {
                "logic_rule": rule["id"],
                "owners": rule["who"],
                "primary_validation": rule["validation"][:2],
            }

    agent_route_index: dict[str, list[str]] = {}
    for rule in rules:
        for agent in rule["who"]:
            agent_route_index.setdefault(agent, []).append(rule["id"])

    repo_domains = sorted(((profile.get("repo_code") or {}).get("by_domain") or {}).keys())
    return {
        "status": "who_what_where_when_how_ready",
        "principle": "Every coding task is routed by who owns it, what kind of logic it changes, where the files live, when learning or writing is allowed, and how proof is produced.",
        "rules": rules,
        "file_area_index": file_area_index,
        "agent_route_index": dict(sorted(agent_route_index.items())),
        "repo_domains_seen": repo_domains,
        "decision_loop": [
            "who: select the responsible coder-agent chain",
            "what: classify the task domain and risk",
            "where: map file paths and public/state evidence contracts",
            "when: decide whether to learn, patch, test, pause, or escalate",
            "how: write through the Queen path, validate, publish evidence, and feed failures back",
        ],
        "write_protocol": {
            "context_first": True,
            "official_docs_for_external_api_changes": True,
            "queen_writer_required": True,
            "tests_required_for_code_changes": True,
            "public_evidence_required_for_operator_visible_capabilities": True,
            "do_not_revert_unowned_changes": True,
        },
    }


def build_work_orders(profile: dict[str, Any]) -> list[CodingWorkOrder]:
    tools = profile.get("tool_registry", {})
    missing_tools = list(tools.get("missing_required_coder_tools") or [])
    orders: list[CodingWorkOrder] = []
    if missing_tools:
        orders.append(
            CodingWorkOrder(
                id="coding_agents.register_missing_tools",
                title="Register missing coder web/repo tools",
                status="blocked_until_tool_registry_updated",
                priority=100,
                owner_agent="ImplementationWorker",
                reason=f"Missing coder tools: {', '.join(missing_tools)}",
                proposed_action="Add the missing built-ins to aureon.inhouse_ai.tool_registry and retest.",
                validation=["ToolRegistry names include every required coder tool."],
            )
        )
    else:
        orders.append(
            CodingWorkOrder(
                id="coding_agents.web_tools_active",
                title="Coder web/repo tools active",
                status="ready",
                priority=95,
                owner_agent="WebLearningScout",
                reason="In-house agents can now search the web, fetch docs, search the repo, and read skill-base status.",
                proposed_action="Use bounded official-doc learning before proposing coding improvements.",
                validation=["web_search", "web_fetch", "repo_search", "skill_base_status"],
            )
        )

    logic_map = profile.get("coding_logic_map") or {}
    logic_rules = list(logic_map.get("rules") or [])
    orders.append(
        CodingWorkOrder(
            id="coding_agents.who_what_where_when_how_logic",
            title="Use who/what/where/when/how coding route before writing files",
            status="active",
            priority=96,
            owner_agent="RepoCartographer",
            reason=f"{len(logic_rules)} coding logic rules route work across file areas, agents, validation, and evidence.",
            proposed_action="Before each code task, classify the task with coding_logic_map and assign the agent chain plus validation commands.",
            validation=[
                "coding_logic_map.status == who_what_where_when_how_ready",
                "file_area_index has owned write paths",
            ],
        )
    )

    skill_count = int((profile.get("skill_libraries") or {}).get("total_skill_count") or 0)
    if skill_count == 0:
        orders.append(
            CodingWorkOrder(
                id="coding_agents.bootstrap_skill_library",
                title="Bootstrap CodeArchitect skill library",
                status="planned",
                priority=90,
                owner_agent="ImplementationWorker",
                reason="No active skills found in the primary skill libraries.",
                proposed_action="Run CodeArchitect.bootstrap_atomics, then compose repo_search, test_runner, frontend_builder, and docs_research workflow skills.",
                validation=["state/skills/skill_library.json exists", "atomic skills validated"],
            )
        )
    else:
        orders.append(
            CodingWorkOrder(
                id="coding_agents.skill_library_explained",
                title="Explain active skill library to operator and agents",
                status="ready",
                priority=85,
                owner_agent="RepoCartographer",
                reason=f"{skill_count} skills are visible across known SkillLibrary stores.",
                proposed_action="Keep publishing skill summaries into frontend/public/aureon_coding_agent_skill_base.json.",
                validation=["Skill counts grouped by level and status."],
            )
        )

    repo_languages = (profile.get("repo_code") or {}).get("by_language") or {}
    for language, count in sorted(repo_languages.items(), key=lambda item: (-int(item[1]), item[0]))[:8]:
        orders.append(
            CodingWorkOrder(
                id=f"coding_agents.learn_{re.sub(r'[^a-z0-9]+', '_', language.lower())}",
                title=f"Learn and improve {language} coding patterns",
                status="learning_queued",
                priority=70,
                owner_agent="WebLearningScout",
                reason=f"Repo contains {count} {language} files.",
                proposed_action="Search official docs, compare against local patterns, then create scoped improvement proposals with tests.",
                validation=["official source recorded", "repo path evidence recorded", "tests proposed"],
            )
        )
    return orders


def run_online_probes(limit: int = 3) -> dict[str, Any]:
    """Run bounded read-only web probes through AureonAgentCore."""

    results: list[dict[str, Any]] = []
    search_results: list[dict[str, Any]] = []
    try:
        from aureon.autonomous.aureon_agent_core import AureonAgentCore

        agent = AureonAgentCore()
        for source in OFFICIAL_LEARNING_SOURCES[: max(0, limit)]:
            fetched = agent.web_fetch(str(source["url"]))
            results.append(
                {
                    "id": source["id"],
                    "url": source["url"],
                    "success": bool(fetched.get("success")),
                    "status_code": fetched.get("status_code"),
                    "sample_chars": len(str(fetched.get("text") or "")),
                    "error": fetched.get("error", ""),
                }
            )
        for query in WEB_LEARNING_QUERIES[: max(0, min(limit, 2))]:
            found = agent.web_search(str(query["query"]), num_results=3)
            search_results.append(
                {
                    "id": query["id"],
                    "query": query["query"],
                    "result_count": len(found) if isinstance(found, list) else 0,
                    "results": found[:3] if isinstance(found, list) else [],
                }
            )
    except Exception as exc:
        return {
            "enabled": True,
            "status": "probe_failed",
            "error": f"{type(exc).__name__}: {exc}",
            "fetches": results,
            "searches": search_results,
        }
    return {
        "enabled": True,
        "status": "probe_complete",
        "fetches": results,
        "searches": search_results,
    }


def render_component() -> str:
    return r"""import { useEffect, useMemo, useState, type ReactNode } from "react";
import { BrainCircuit, Code2, Globe2, SearchCheck, ShieldCheck, UsersRound } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";

type JsonMap = Record<string, any>;

async function fetchJson(url: string): Promise<JsonMap> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return {};
    return await response.json();
  } catch {
    return {};
  }
}

function fmt(value: unknown): string {
  const number = Number(value || 0);
  return Number.isFinite(number) ? number.toLocaleString() : String(value || "0");
}

export function AureonCodingAgentSkillBaseConsole() {
  const [profile, setProfile] = useState<JsonMap>({});

  useEffect(() => {
    let cancelled = false;
    fetchJson("/aureon_coding_agent_skill_base.json").then((payload) => {
      if (!cancelled) setProfile(payload);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const summary = profile.summary || {};
  const agents = Array.isArray(profile.coder_agents) ? profile.coder_agents : [];
  const orders = Array.isArray(profile.coding_work_orders) ? profile.coding_work_orders : [];
  const tools = profile.tool_registry || {};
  const repoCode = profile.repo_code || {};
  const domains = repoCode.by_domain || {};
  const languages = repoCode.by_language || {};
  const logicMap = profile.coding_logic_map || {};
  const logicRules = Array.isArray(logicMap.rules) ? logicMap.rules : [];
  const sources = Array.isArray(profile.official_learning_sources) ? profile.official_learning_sources : [];
  const visibleOrders = useMemo(() => orders.slice(0, 30), [orders]);

  return (
    <Card className="mb-5 bg-card/80">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <BrainCircuit className="h-4 w-4 text-primary" />
          Aureon Coding Agent Skill Base
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant="outline" className="border-green-500/40 bg-green-500/10 text-green-100">{profile.status || "pending"}</Badge>
          <Badge variant="outline" className="border-border bg-muted/20 text-muted-foreground">updated {profile.generated_at ? new Date(profile.generated_at).toLocaleTimeString() : "pending"}</Badge>
          <Badge variant="outline" className="border-blue-500/40 bg-blue-500/10 text-blue-100">web tools {summary.web_tools_ready ? "ready" : "attention"}</Badge>
          <Badge variant="outline" className="border-purple-500/40 bg-purple-500/10 text-purple-100">{logicMap.status || "logic pending"}</Badge>
        </div>
        <div className="grid gap-2 md:grid-cols-6">
          <Stat icon={UsersRound} label="coder agents" value={summary.coder_agent_count} />
          <Stat icon={Code2} label="repo files" value={repoCode.file_count} />
          <Stat icon={BrainCircuit} label="skills" value={summary.skill_count} />
          <Stat icon={Globe2} label="learning sources" value={sources.length} />
          <Stat icon={ShieldCheck} label="logic rules" value={logicRules.length} />
          <Stat icon={SearchCheck} label="work orders" value={orders.length} />
        </div>
        <div className="grid gap-3 lg:grid-cols-3">
          <Panel title="Agents">
            {agents.slice(0, 6).map((agent: JsonMap) => (
              <div key={agent.name} className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="text-sm font-medium">{agent.name}</div>
                <div className="mt-1 text-xs text-muted-foreground">{agent.purpose}</div>
              </div>
            ))}
          </Panel>
          <Panel title="Skill And Tool State">
            <Mini label="In-house tools" value={tools.inhouse_tool_count} />
            <Mini label="Missing coder tools" value={(tools.missing_required_coder_tools || []).length} />
            <Mini label="Languages" value={Object.keys(languages).length} />
            <Mini label="Domains" value={Object.keys(domains).length} />
          </Panel>
          <Panel title="Learning Sources">
            {sources.slice(0, 7).map((source: JsonMap) => (
              <div key={source.id} className="rounded-md border border-border/40 bg-muted/10 p-2">
                <div className="text-xs font-medium">{source.title}</div>
                <div className="truncate font-mono text-[10px] text-muted-foreground">{source.url}</div>
              </div>
            ))}
          </Panel>
        </div>
        <Panel title="Who What Where When How">
          <div className="text-xs text-muted-foreground">{logicMap.principle || "Coding route pending."}</div>
          <div className="grid gap-2 lg:grid-cols-2">
            {logicRules.slice(0, 6).map((rule: JsonMap) => (
              <div key={rule.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm font-medium">{rule.id}</div>
                  <Badge variant="outline" className="border-border bg-muted/20 text-muted-foreground">{(rule.who || []).slice(0, 2).join(" + ")}</Badge>
                </div>
                <div className="mt-2 text-xs text-muted-foreground">{rule.what}</div>
                <div className="mt-2 truncate font-mono text-[10px] text-green-100">{(rule.where || []).slice(0, 3).join(" | ")}</div>
              </div>
            ))}
          </div>
        </Panel>
        <ScrollArea className="h-[320px] pr-3">
          <div className="space-y-2">
            {visibleOrders.map((order: JsonMap) => (
              <div key={order.id} className="rounded-md border border-border/40 bg-muted/10 p-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="text-sm font-medium">{order.title}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{order.reason}</div>
                  </div>
                  <Badge variant="outline" className="border-border bg-muted/20 text-muted-foreground">{order.owner_agent}</Badge>
                </div>
                <div className="mt-2 text-xs text-green-100">{order.proposed_action}</div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

function Stat({ icon: Icon, label, value }: { icon: any; label: string; value: unknown }) {
  return (
    <div className="rounded-md border border-border/40 bg-muted/10 p-3">
      <div className="flex items-center gap-2 text-[11px] uppercase text-muted-foreground"><Icon className="h-3.5 w-3.5" />{label}</div>
      <div className="mt-1 text-lg font-semibold">{fmt(value)}</div>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="space-y-2 rounded-md border border-border/40 bg-muted/10 p-3">
      <div className="flex items-center gap-2 text-sm font-medium"><ShieldCheck className="h-4 w-4 text-primary" />{title}</div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Mini({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border/30 bg-background/20 px-3 py-2 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-semibold">{fmt(value)}</span>
    </div>
  );
}
"""


def mount_component_in_app(app_text: str) -> str:
    import_line = 'import { AureonCodingAgentSkillBaseConsole } from "@/components/generated/AureonCodingAgentSkillBaseConsole";'
    if import_line not in app_text:
        anchor = 'import { AureonWorkOrderExecutionConsole } from "@/components/generated/AureonWorkOrderExecutionConsole";'
        fallback_anchor = 'import { AureonGeneratedOperationalConsole } from "@/components/generated/AureonGeneratedOperationalConsole";'
        if anchor in app_text:
            app_text = app_text.replace(anchor, f"{anchor}\n{import_line}", 1)
        elif fallback_anchor in app_text:
            app_text = app_text.replace(fallback_anchor, f"{fallback_anchor}\n{import_line}", 1)

    mount_line = "        <AureonCodingAgentSkillBaseConsole />"
    if mount_line not in app_text:
        anchor = "        <AureonWorkOrderExecutionConsole />"
        fallback_anchor = "        <AureonGeneratedOperationalConsole />"
        if anchor in app_text:
            app_text = app_text.replace(anchor, f"{anchor}\n{mount_line}", 1)
        elif fallback_anchor in app_text:
            app_text = app_text.replace(fallback_anchor, f"{fallback_anchor}\n{mount_line}", 1)
    return app_text


def build_profile(
    goal: str, *, root: Path | None = None, online: bool = False, online_limit: int = 3
) -> dict[str, Any]:
    repo_root = repo_root_from(root)
    repo_code = classify_repo_code(repo_root)
    skill_libraries = skill_library_snapshot(repo_root)
    website_design_skills = public_website_design_skill_stack()
    website_design_registry = public_website_design_registry_snapshot(repo_root)
    source_rationalisation_readiness = website_design_registry.get("website_source_rationalisation_readiness")
    if not isinstance(source_rationalisation_readiness, dict):
        source_rationalisation_readiness = {}
    runtime_optimisation_readiness = website_design_registry.get("website_runtime_optimisation_readiness")
    if not isinstance(runtime_optimisation_readiness, dict):
        runtime_optimisation_readiness = {}
    runtime_measurement_static_integrity_readiness = website_design_registry.get(
        "website_runtime_measurement_static_integrity_readiness"
    )
    if not isinstance(runtime_measurement_static_integrity_readiness, dict):
        runtime_measurement_static_integrity_readiness = {}
    owner_source_readiness = website_design_registry.get("owner_source_reconciliation_readiness")
    if not isinstance(owner_source_readiness, dict):
        owner_source_readiness = {}
    research_refresh_readiness = website_design_registry.get("design_research_refresh_readiness")
    if not isinstance(research_refresh_readiness, dict):
        research_refresh_readiness = {}
    stakeholder_feedback_readiness = website_design_registry.get("stakeholder_feedback_readiness")
    if not isinstance(stakeholder_feedback_readiness, dict):
        stakeholder_feedback_readiness = {}
    editorial_rights_preparation_readiness = website_design_registry.get(
        "editorial_rights_decision_preparation_readiness"
    )
    if not isinstance(editorial_rights_preparation_readiness, dict):
        editorial_rights_preparation_readiness = {}
    editorial_asset_readiness = website_design_registry.get("editorial_asset_provenance_readiness")
    if not isinstance(editorial_asset_readiness, dict):
        editorial_asset_readiness = {}
    editorial_importer_readiness = website_design_registry.get("editorial_asset_importer_readiness")
    if not isinstance(editorial_importer_readiness, dict):
        editorial_importer_readiness = {}
    investor_copy_readiness = website_design_registry.get("investor_copy_quality_readiness")
    if not isinstance(investor_copy_readiness, dict):
        investor_copy_readiness = {}
    investor_copy_repair_protocol = website_design_registry.get("investor_copy_repair_readiness")
    if not isinstance(investor_copy_repair_protocol, dict):
        investor_copy_repair_protocol = {}
    investor_copy_governance_protocol = website_design_registry.get("investor_copy_governance_readiness")
    if not isinstance(investor_copy_governance_protocol, dict):
        investor_copy_governance_protocol = {}
    hnc_graph_readiness = website_design_registry.get("hnc_evidence_graph_readiness")
    if not isinstance(hnc_graph_readiness, dict):
        hnc_graph_readiness = {}
    design_brief_readiness = website_design_registry.get("design_evidence_brief_readiness")
    if not isinstance(design_brief_readiness, dict):
        design_brief_readiness = {}
    staged_worker_broker_readiness = website_design_registry.get("staged_design_worker_broker_readiness")
    if not isinstance(staged_worker_broker_readiness, dict):
        staged_worker_broker_readiness = {}
    motion_budget_readiness = website_design_registry.get("motion_performance_budget_readiness")
    if not isinstance(motion_budget_readiness, dict):
        motion_budget_readiness = {}
    candidate_test_readiness = website_design_registry.get("candidate_test_evidence_readiness")
    if not isinstance(candidate_test_readiness, dict):
        candidate_test_readiness = {}
    reviewed_node_toolchain = candidate_test_readiness.get("reviewed_node_toolchain")
    if not isinstance(reviewed_node_toolchain, dict):
        reviewed_node_toolchain = {}
    candidate_test_bounded_process = candidate_test_readiness.get("bounded_process")
    if not isinstance(candidate_test_bounded_process, dict):
        candidate_test_bounded_process = {}
    reviewed_node_toolchain_available = bool(
        reviewed_node_toolchain.get("protocol_available") is True
        and reviewed_node_toolchain.get("schema") == "aureon.node-toolchain-binding.v1"
        and reviewed_node_toolchain.get("locator_authority")
        == "reviewed-source-pinned-absolute-path-no-path-fallback"
        and reviewed_node_toolchain.get("absolute_path_size_sha256_bound") is True
        and reviewed_node_toolchain.get("ambient_path_fallback_allowed") is False
        and reviewed_node_toolchain.get("resolved") is False
        and reviewed_node_toolchain.get("executed") is False
    )
    candidate_test_bounded_popen_available = bool(
        candidate_test_bounded_process.get("protocol_available") is True
        and candidate_test_bounded_process.get("launcher") == "subprocess.Popen"
        and candidate_test_bounded_process.get("shell") is False
        and candidate_test_bounded_process.get("max_stream_bytes") == 2 * 1024 * 1024
        and candidate_test_bounded_process.get("retry_authority") == "none"
        and candidate_test_bounded_process.get("executed") is False
    )
    candidate_qa_control_plane = website_design_registry.get("candidate_qa_control_plane_readiness")
    if not isinstance(candidate_qa_control_plane, dict):
        candidate_qa_control_plane = {}
    compiler_verification_ingress = candidate_qa_control_plane.get("compiler_verification_ingress")
    if not isinstance(compiler_verification_ingress, dict):
        compiler_verification_ingress = {}
    imported_compiler_api = compiler_verification_ingress.get("imported_api")
    if not isinstance(imported_compiler_api, dict):
        imported_compiler_api = {}
    sealed_compiler_verification = compiler_verification_ingress.get("sealed_direct_file_read_only")
    if not isinstance(sealed_compiler_verification, dict):
        sealed_compiler_verification = {}
    sealed_compiler_runner_delegation = compiler_verification_ingress.get("runner_delegation")
    if not isinstance(sealed_compiler_runner_delegation, dict):
        sealed_compiler_runner_delegation = {}
    imported_compiler_drift_checks_available = bool(
        imported_compiler_api.get("scope") == "drift-check-only"
        and imported_compiler_api.get("motion_read_only_verifier_available") is True
        and imported_compiler_api.get("test_read_only_verifier_available") is True
        and imported_compiler_api.get("pre_import_source_authentication") is False
    )
    sealed_compiler_read_only_protocol_available = bool(
        sealed_compiler_verification.get("protocol_available") is True
        and sealed_compiler_verification.get("motion_protocol_available") is True
        and sealed_compiler_verification.get("test_protocol_available") is True
        and sealed_compiler_verification.get("executed") is False
        and sealed_compiler_verification.get("python_flags") == ["-I", "-S", "-B"]
        and sealed_compiler_verification.get("motion_verify_flag") == "--verify-config"
        and sealed_compiler_verification.get("test_verify_flag") == "--verify-policy"
        and sealed_compiler_verification.get("source_closure_helper_available") is True
    )
    sealed_compiler_runner_delegation_available = bool(
        sealed_compiler_runner_delegation.get("protocol_available") is True
        and sealed_compiler_runner_delegation.get("required_for_candidate_qa") is True
        and sealed_compiler_runner_delegation.get("bounded_popen_protocol_available") is True
        and sealed_compiler_runner_delegation.get("launcher") == "subprocess.Popen"
        and sealed_compiler_runner_delegation.get("shell") is False
        and sealed_compiler_runner_delegation.get("timeout_seconds") == 300
        and sealed_compiler_runner_delegation.get("max_aggregate_output_bytes") == 64 * 1024
        and sealed_compiler_runner_delegation.get("retry_authority") == "none"
        and sealed_compiler_runner_delegation.get("invoked") is False
    )
    candidate_qa_control_plane_available = bool(
        candidate_qa_control_plane.get("available") is True
        and candidate_qa_control_plane.get("state") == "installed-not-authorised"
        and candidate_qa_control_plane.get("execution_order_enforced") is True
        and candidate_qa_control_plane.get("candidate_test_evidence_runtime_available") is True
        and compiler_verification_ingress.get("discovery_mode") == "metadata-only-no-subprocess"
        and compiler_verification_ingress.get("discovery_subprocess_launched") is False
        and imported_compiler_drift_checks_available
        and sealed_compiler_read_only_protocol_available
        and sealed_compiler_runner_delegation_available
    )
    tools = tool_registry_snapshot(repo_root)
    agents = [role.to_dict() for role in coder_agent_roles()]
    profile: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "repo_root": str(repo_root),
        "status": "coding_agent_skill_base_ready"
        if not tools.get("missing_required_coder_tools")
        else "coding_agent_skill_base_ready_with_tool_gaps",
        "goal": goal,
        "summary": {
            "coder_agent_count": len(agents),
            "repo_code_file_count": repo_code.get("file_count", 0),
            "skill_count": skill_libraries.get("total_skill_count", 0),
            "web_tools_ready": not bool(tools.get("missing_required_coder_tools")),
            "official_learning_source_count": len(OFFICIAL_LEARNING_SOURCES),
            "web_learning_query_count": len(WEB_LEARNING_QUERIES),
            "public_website_design_skill_count": sum(
                len(items)
                for items in website_design_skills.get("levels", {}).values()
                if isinstance(items, list)
            ),
            "public_website_design_registry_verified": bool(website_design_registry.get("verified")),
            "public_website_design_registry_source_count": len(website_design_registry.get("sources") or []),
            "public_website_design_source_rationalisation_planning_protocol_available": bool(
                source_rationalisation_readiness.get("planning_protocol_available")
            ),
            "public_website_design_source_rationalisation_owner_decision_validation_protocol_available": bool(
                source_rationalisation_readiness.get("owner_decision_validation_protocol_available")
            ),
            "public_website_design_source_rationalisation_discovery_planning_executed": bool(
                source_rationalisation_readiness.get("planning_executed_during_discovery")
            ),
            "public_website_design_source_rationalisation_discovery_validation_executed": bool(
                source_rationalisation_readiness.get("owner_decision_validation_executed_during_discovery")
            ),
            "public_website_design_source_rationalisation_autonomous_owner_decision": bool(
                source_rationalisation_readiness.get("autonomous_owner_decision")
            ),
            "public_website_design_source_rationalisation_omission_proves_readiness": bool(
                source_rationalisation_readiness.get("omission_proves_readiness")
            ),
            "public_website_design_source_rationalisation_text_worker_authority": (
                source_rationalisation_readiness.get("text_worker_authority") or "none"
            ),
            "public_website_design_runtime_optimisation_proposal_protocol_available": bool(
                runtime_optimisation_readiness.get("proposal_compilation_protocol_available")
            ),
            "public_website_design_runtime_optimisation_measurement_validation_available": bool(
                runtime_optimisation_readiness.get("measurement_validation_protocol_available")
            ),
            "public_website_design_runtime_optimisation_browser_contract_available": bool(
                runtime_optimisation_readiness.get("browser_acceptance_contract_available")
            ),
            "public_website_design_runtime_optimisation_measurement_schema_available": bool(
                runtime_optimisation_readiness.get("measurement_schema_available")
            ),
            "public_website_design_runtime_optimisation_proposal_schema_available": bool(
                runtime_optimisation_readiness.get("proposal_schema_available")
            ),
            "public_website_design_runtime_optimisation_measurement_provenance_verified": bool(
                runtime_optimisation_readiness.get("measurement_provenance_verification_available")
            ),
            "public_website_design_runtime_optimisation_production_compilation_blocked": bool(
                runtime_optimisation_readiness.get("production_compilation_blocked", True)
            ),
            "public_website_design_runtime_optimisation_discovery_executed": bool(
                runtime_optimisation_readiness.get("proposal_compilation_executed")
                or runtime_optimisation_readiness.get("measurement_validation_executed")
            ),
            "public_website_design_runtime_optimisation_autonomous_source_selection": bool(
                runtime_optimisation_readiness.get("autonomous_source_selection")
            ),
            "public_website_design_runtime_optimisation_autonomous_measurement_evidence": bool(
                runtime_optimisation_readiness.get("autonomous_measurement_evidence")
            ),
            "public_website_design_runtime_measurement_static_integrity_available": bool(
                runtime_measurement_static_integrity_readiness.get("static_integrity_validation_available")
            ),
            "public_website_design_runtime_measurement_static_integrity_executed": bool(
                runtime_measurement_static_integrity_readiness.get("static_integrity_validation_executed")
            ),
            "public_website_design_runtime_measurement_static_integrity_production_eligible": bool(
                runtime_measurement_static_integrity_readiness.get("production_eligible")
            ),
            "public_website_design_runtime_measurement_static_integrity_worker_available": bool(
                runtime_measurement_static_integrity_readiness.get("worker_available")
            ),
            "public_website_design_runtime_measurement_static_integrity_execution_path": (
                runtime_measurement_static_integrity_readiness.get("trusted_static_integrity_execution_path")
                or "unavailable"
            ),
            "public_website_design_runtime_measurement_static_integrity_imported_api_authoritative": bool(
                runtime_measurement_static_integrity_readiness.get("imported_api_authoritative")
            ),
            "public_website_design_owner_source_validation_protocol_available": bool(
                owner_source_readiness.get("validation_protocol_available")
            ),
            "public_website_design_owner_source_v1_retain_local_supported": bool(
                owner_source_readiness.get("v1_retain_local_supported")
            ),
            "public_website_design_owner_source_v2_verified_live_backup_supported": bool(
                owner_source_readiness.get("v2_verified_live_backup_supported")
            ),
            "public_website_design_autonomous_source_selection": bool(
                owner_source_readiness.get("autonomous_source_selection")
            ),
            "public_website_design_research_refresh_current": bool(research_refresh_readiness.get("current")),
            "public_website_design_stakeholder_feedback_current": bool(
                stakeholder_feedback_readiness.get("current")
            ),
            "public_website_design_stakeholder_feedback_planning_only": bool(
                stakeholder_feedback_readiness.get("planning_only")
            ),
            "public_website_design_editorial_asset_integrity_verified": bool(
                editorial_asset_readiness.get("integrity_verified")
            ),
            "public_website_design_editorial_asset_public_use_ready": bool(
                editorial_asset_readiness.get("public_use_ready")
            ),
            "public_website_design_editorial_rights_preparation_protocol_available": bool(
                editorial_rights_preparation_readiness.get("preparation_protocol_available")
            ),
            "public_website_design_autonomous_human_rights_decision": bool(
                editorial_rights_preparation_readiness.get("autonomous_human_decision")
            ),
            "public_website_design_editorial_import_protocol_available": bool(
                editorial_importer_readiness.get("import_protocol_available")
            ),
            "public_website_design_editorial_import_ready": bool(
                editorial_importer_readiness.get("candidate_import_ready")
            ),
            "public_website_design_investor_copy_ready": bool(investor_copy_readiness.get("copy_ready")),
            "public_website_design_investor_copy_repair_protocol_available": bool(
                investor_copy_repair_protocol.get("source_bound_protocol_available")
            ),
            "public_website_design_investor_copy_repair_candidate_reaudit_available": bool(
                investor_copy_repair_protocol.get("candidate_reaudit_available")
            ),
            "public_website_design_investor_copy_repair_current_contract_ready": bool(
                investor_copy_repair_protocol.get("current_contract_ready")
            ),
            "public_website_design_investor_copy_governance_verification_available": bool(
                investor_copy_governance_protocol.get("decision_verification_available")
            ),
            "public_website_design_investor_copy_governance_simulation_available": bool(
                investor_copy_governance_protocol.get("simulation_available")
            ),
            "public_website_design_investor_copy_governance_apply_protocol_available": bool(
                investor_copy_governance_protocol.get("apply_protocol_available")
            ),
            "public_website_design_investor_copy_governance_implementation_tooling_verified": bool(
                investor_copy_governance_protocol.get("implementation_tooling_verified")
            ),
            "public_website_design_investor_copy_governance_current_owner_decision_present": bool(
                investor_copy_governance_protocol.get("current_owner_decision_present")
            ),
            "public_website_design_investor_copy_governance_current_apply_authorised": bool(
                investor_copy_governance_protocol.get("current_apply_authorised")
            ),
            "public_website_design_investor_copy_governance_current_apply_ready": bool(
                investor_copy_governance_protocol.get("current_apply_ready")
            ),
            "public_website_design_investor_copy_governance_broad_access_approval_valid": bool(
                investor_copy_governance_protocol.get("broad_access_approval_valid")
            ),
            "public_website_design_hnc_graph_bundle_ready": bool(
                hnc_graph_readiness.get("component_bundle_ready")
            ),
            "public_website_design_hnc_graph_candidate_transplant_ready": bool(
                hnc_graph_readiness.get("candidate_transplant_ready")
            ),
            "public_website_design_brief_ready": bool(design_brief_readiness.get("brief_ready")),
            "public_website_design_planning_pipeline_available": bool(
                design_brief_readiness.get("planning_pipeline_available")
            ),
            "public_website_design_worker_broker_protocol_available": bool(
                staged_worker_broker_readiness.get("lease_protocol_available")
            ),
            "public_website_design_motion_budget_protocol_available": bool(
                motion_budget_readiness.get("audit_protocol_available")
            ),
            "public_website_design_motion_budget_passed": bool(
                motion_budget_readiness.get("decision_passed")
                and motion_budget_readiness.get("eligible_for_next_local_gate")
            ),
            "public_website_design_candidate_test_protocol_available": bool(
                candidate_test_readiness.get("execution_protocol_available")
                and candidate_test_readiness.get("structural_verification_available")
                and reviewed_node_toolchain_available
                and candidate_test_bounded_popen_available
            ),
            "public_website_design_candidate_test_reviewed_node_toolchain_available": (
                reviewed_node_toolchain_available
            ),
            "public_website_design_candidate_test_bounded_popen_available": (
                candidate_test_bounded_popen_available
            ),
            "public_website_design_candidate_test_origin_attested": bool(
                candidate_test_readiness.get("origin_attested")
            ),
            "public_website_design_candidate_test_evidence_passed": bool(
                candidate_test_readiness.get("evidence_passed")
            ),
            "public_website_design_candidate_qa_control_plane_available": (
                candidate_qa_control_plane_available
            ),
            "public_website_design_imported_compiler_drift_check_apis_available": (
                imported_compiler_drift_checks_available
            ),
            "public_website_design_sealed_compiler_read_only_protocol_available": (
                sealed_compiler_read_only_protocol_available
            ),
            "public_website_design_sealed_compiler_runner_delegation_available": (
                sealed_compiler_runner_delegation_available
            ),
            "public_website_design_candidate_qa_discovery_subprocess_launched": bool(
                compiler_verification_ingress.get("discovery_subprocess_launched")
            ),
            "public_website_design_candidate_qa_executed": bool(
                candidate_qa_control_plane.get("qa_executed")
            ),
            "public_website_design_candidate_qa_passed": bool(candidate_qa_control_plane.get("qa_passed")),
            "public_website_design_candidate_delivery_ready": bool(
                design_brief_readiness.get("candidate_delivery_ready")
            ),
        },
        "coder_agents": agents,
        "repo_code": repo_code,
        "skill_libraries": skill_libraries,
        "public_website_design_skill_stack": website_design_skills,
        "public_website_design_capability_registry": website_design_registry,
        "tool_registry": tools,
        "official_learning_sources": list(OFFICIAL_LEARNING_SOURCES),
        "web_learning_queries": list(WEB_LEARNING_QUERIES),
        "web_probe": run_online_probes(online_limit)
        if online
        else {"enabled": False, "status": "not_requested"},
        "learning_flow": [
            "RepoCartographer maps existing code and evidence paths.",
            "WebLearningScout searches/fetches official docs and public API references.",
            "ImplementationWorker converts verified learning into scoped work orders.",
            "SecurityReviewer checks redaction, mutation boundaries, and unsafe patterns.",
            "TestPilot runs focused tests/builds and feeds failures back into repo self-repair.",
            "PublicWebsiteDesignWorker can only propose a sealed text-only manifest under one explicit broker lease; the broker verifies the exact staged-candidate diff before any separate canonical promotion.",
            "A current redacted design-research refresh must remain hash-bound and not-cleared for artwork before the source-bound design-evidence brief can be used as planning evidence; neither record makes a candidate delivery-ready or release-ready.",
            "Current stakeholder feedback is reduced to a privacy-safe declaration binding and controlled-code route capsule before a worker sees it; raw correspondence and the redacted source snapshot stay unavailable, and every sealed signal requires a complete hash-bound response manifest.",
            "Observed live drift can proceed only after validating the owner's exact time-limited v1 retained-local or v2 verified-live-backup choice; no coding or design agent chooses the source.",
            "Website source-rationalisation discovery is metadata-only and executes neither planning nor validation. Only PublicWebsiteDesignQA receives the proposal-only planner and exact owner-decision validator; PublicWebsiteDesignWorker receives neither, omission never proves readiness, and validation stops without staging, deletion, candidate, canonical, package, release, credential, network, publishing, or deployment authority.",
            "Website runtime-optimisation discovery is metadata-only and executes neither structural validation nor proposal compilation. PublicWebsiteDesignQA receives structural declaration validation only; production compilation and writing are hard-blocked until reviewed measurement provenance and readable derivative evidence exist, and PublicWebsiteDesignWorker receives neither capability.",
            "Runtime measurement static-integrity validation is a separate QA-only read/validate surface for one explicitly supplied existing artifact. Trusted use requires a fresh hash-authenticated python -I -S -B launcher; imported APIs are non-authoritative test and drift checks. It can bind current stored bytes, a complete website manifest, two pre-existing replicas, hashes, arithmetic, and header-derived dimensions, but it remains provenance-unverified and production-blocked, creates no evidence, grants no worker access, and cannot prove producer execution, deterministic replay, full decode, freshness, browser acceptance, or visual acceptance.",
            "Editorial rights preparation verifies and records only an exact decision already supplied by the controlled named human; it never acts as the reviewer, infers approval, changes the canonical manifest, or creates candidate readiness.",
            "Editorial binaries stay outside the text worker; the trusted importer can copy only exact approved content-addressed WebPs into one staged candidate and must emit a replay-verifiable immutable receipt.",
            "Investor-copy repair requires the exact DESIGN-COPY task, one-HTML v4 work order, selected-source preflight, short-lived source-bound contract, and exact candidate re-audit; the installed protocol alone cannot stage copy or advance a browser or release gate.",
            "Investor-copy governance verification and shadow simulation are read-only; broad system access is never the required decision, and the exact three-file apply remains blocked until a fresh immutable named-owner decision and explicit apply are both present.",
            "The installed worker broker is not a standing website-write capability: it requires an existing source-bound staged candidate, one short-lived lease, and its built-in declarative applier, while release, package, credentials, and deployment remain unavailable.",
            "A worker's pass string is not test evidence. The installed candidate-test protocol remains unauthorised until trusted orchestration runs the complete pinned suite, independently seals the immutable receipt, and strict verification reports origin_attested false plus evidence_passed true.",
            "The installed motion/performance protocol does not imply a pass. A current static receipt must report decision.status pass and eligible_for_next_local_gate true, while browser performance and human visual acceptance remain separate.",
            "Candidate-QA control-plane discovery is installed-not-authorised metadata only and launches no subprocess. Imported compiler verifier APIs are drift-check-only; trusted orchestration must delegate sealed direct compiler-file read-only replay under python -I -S -B through the V2 runner, derive both candidate tree hashes from one captured manifest, bind the unchanged V1 policy content core, consume one handle-bound attempt, run motion first, accept V2 trusted test evidence only after motion passes, and enter the initial browser gate only from candidate-qa-verified.",
            "PublicWebsiteDesignQA uses the source-bound initial gate to reject unsafe geometry or failed first-run performance before any repeatability series.",
            "PublicWebsiteDesignWorker and PublicWebsiteDesignQA use the source-bound registry for local planning and vetoes only; human visual acceptance and WebsiteOperator owner release remain mandatory.",
            "Accepted staged candidates may be recorded as source-bound, non-applied Design Suite learning proposals; a human-reviewed repository change is still required before any skill source changes.",
        ],
        "safety": {
            "web_learning_read_only": True,
            "official_sources_preferred": True,
            "secret_values_written": False,
            "external_mutations": False,
            "live_trading_mutation": False,
            "repo_writes_require_queen_writer_and_tests": True,
            "public_website_design_registry_non_authoritative": True,
            "public_website_design_research_refresh_planning_only": True,
            "public_website_design_stakeholder_feedback_planning_only": True,
            "public_website_design_raw_correspondence_unavailable": True,
            "public_website_design_autonomous_source_selection": False,
            "public_website_design_source_rationalisation_discovery_executes_planning": False,
            "public_website_design_source_rationalisation_discovery_executes_validation": False,
            "public_website_design_source_rationalisation_autonomous_owner_decision": False,
            "public_website_design_source_rationalisation_text_worker_authority": False,
            "public_website_design_source_rationalisation_staging_authority": False,
            "public_website_design_source_rationalisation_deletion_authority": False,
            "public_website_design_source_rationalisation_candidate_or_canonical_authority": False,
            "public_website_design_source_rationalisation_package_release_or_deploy_authority": False,
            "public_website_design_source_rationalisation_credential_or_network_authority": False,
            "public_website_design_source_rationalisation_omission_proves_readiness": False,
            "public_website_design_runtime_optimisation_discovery_executes_compilation": False,
            "public_website_design_runtime_optimisation_discovery_validates_measurement": False,
            "public_website_design_runtime_optimisation_autonomous_source_selection": False,
            "public_website_design_runtime_optimisation_autonomous_measurement_evidence": False,
            "public_website_design_runtime_optimisation_encoding_or_css_execution": False,
            "public_website_design_runtime_optimisation_reference_or_source_mutation": False,
            "public_website_design_runtime_optimisation_candidate_or_canonical_authority": False,
            "public_website_design_runtime_optimisation_package_release_or_deploy_authority": False,
            "public_website_design_runtime_optimisation_credential_or_network_authority": False,
            "public_website_design_runtime_optimisation_projection_is_acceptance_evidence": False,
            "public_website_design_runtime_measurement_static_integrity_proves_producer_execution": False,
            "public_website_design_runtime_measurement_static_integrity_proves_full_decode_or_freshness": False,
            "public_website_design_runtime_measurement_static_integrity_production_authority": False,
            "public_website_design_runtime_measurement_static_integrity_worker_access": False,
            "public_website_design_runtime_measurement_static_integrity_imported_api_authoritative": False,
            "public_website_design_runtime_measurement_static_integrity_fresh_isolated_launcher_required": True,
            "public_website_design_autonomous_human_rights_decision": False,
            "public_website_design_investor_copy_repair_non_authoritative": True,
            "public_website_design_investor_copy_governance_autonomous_owner_decision": False,
            "public_website_design_investor_copy_governance_broad_approval_sufficient": False,
            "public_website_design_investor_copy_governance_current_owner_decision_present": False,
            "public_website_design_investor_copy_governance_current_apply_authorised": False,
            "public_website_design_investor_copy_governance_website_authority": False,
            "public_website_design_investor_copy_governance_package_or_deploy_authority": False,
            "public_website_design_worker_binary_write_authority": False,
            "public_website_design_worker_pass_strings_are_evidence": False,
            "public_website_design_motion_budget_pass_inferred_from_installation": False,
            "public_website_design_candidate_test_pass_inferred_from_installation": False,
            "public_website_design_candidate_test_origin_attested": False,
            "public_website_design_candidate_test_trusted_orchestration_seal_required": True,
            "public_website_design_candidate_qa_control_plane_execution_authorised": False,
            "public_website_design_candidate_qa_pass_inferred_from_installation": False,
            "public_website_design_candidate_qa_policy_or_threshold_selection_authority": False,
            "public_website_design_imported_compiler_pre_import_source_authentication": False,
            "public_website_design_direct_compiler_verifier_agent_execution_authorised": False,
            "public_website_design_candidate_qa_discovery_launches_subprocess": False,
            "public_website_design_qa_candidate_or_promotion_authority": False,
            "public_website_design_qa_package_or_deploy_authority": False,
            "public_website_design_editorial_import_staged_only": True,
            "public_website_design_brief_planning_only": True,
            "public_website_design_candidates_staged_only": True,
            "public_website_human_visual_acceptance_required": True,
            "public_website_deployment_owner_gated": True,
        },
        "authoring_path": [
            "GoalExecutionEngine.submit_goal",
            "GoalExecutionEngine._execute_coding_agent_skill_base",
            "aureon.autonomous.aureon_coding_agent_skill_base.build_and_write_profile",
            "bounded_local_writer.write_text",
        ],
    }
    profile["coding_logic_map"] = build_coding_logic_map(profile)
    profile["summary"]["coding_logic_rule_count"] = len(
        (profile["coding_logic_map"] or {}).get("rules") or []
    )
    profile["coding_work_orders"] = [order.to_dict() for order in build_work_orders(profile)]
    profile["summary"]["coding_work_order_count"] = len(profile["coding_work_orders"])
    return profile


def render_markdown(profile: dict[str, Any]) -> str:
    lines = [
        "# Aureon Coding Agent Skill Base",
        "",
        f"- Generated: `{profile.get('generated_at')}`",
        f"- Status: `{profile.get('status')}`",
        f"- Goal: {profile.get('goal')}",
        "",
        "## Summary",
        "",
    ]
    for key, value in (profile.get("summary") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Coder Agents", ""])
    for agent in profile.get("coder_agents") or []:
        lines.append(f"- `{agent['name']}`: {agent['purpose']}")
    registry = profile.get("public_website_design_capability_registry") or {}
    lines.extend(["", "## Public Website Design Capability Registry", ""])
    lines.append(f"- State: `{registry.get('state') or 'unavailable'}`")
    lines.append(f"- Source-bound verification: `{bool(registry.get('verified'))}`")
    lines.append(f"- Deployment authority: `{registry.get('deployment_authority') or 'none'}`")
    lines.append(f"- Human visual acceptance: `{registry.get('human_visual_acceptance') or 'required'}`")
    lines.append(
        f"- Release boundary: `{registry.get('owner_release_boundary') or 'WebsiteOperator owner gate only'}`"
    )
    lines.extend(["", "## Tool Registry", ""])
    tools = profile.get("tool_registry") or {}
    lines.append(f"- In-house tools: `{', '.join(tools.get('inhouse_tools') or [])}`")
    missing = tools.get("missing_required_coder_tools") or []
    lines.append(f"- Missing required coder tools: `{', '.join(missing) if missing else 'none'}`")
    lines.extend(["", "## Learning Sources", ""])
    for source in profile.get("official_learning_sources") or []:
        lines.append(f"- `{source['id']}`: {source['title']} - {source['url']}")
    logic_map = profile.get("coding_logic_map") or {}
    lines.extend(["", "## Who What Where When How Coding Logic", ""])
    lines.append(str(logic_map.get("principle") or ""))
    lines.extend(["", "### Decision Loop", ""])
    for item in logic_map.get("decision_loop") or []:
        lines.append(f"- {item}")
    lines.extend(["", "### Rules", ""])
    for rule in logic_map.get("rules") or []:
        lines.append(f"- `{rule['id']}`")
        lines.append(f"  - who: {', '.join(rule.get('who') or [])}")
        lines.append(f"  - what: {rule.get('what')}")
        lines.append(f"  - where: {', '.join(rule.get('where') or [])}")
        lines.append(f"  - when: {'; '.join(rule.get('when') or [])}")
        lines.append(f"  - how: {'; '.join(rule.get('how') or [])}")
    lines.extend(["", "## Coding Work Orders", ""])
    for order in profile.get("coding_work_orders") or []:
        lines.append(
            f"- `{order['status']}` `{order['owner_agent']}` {order['title']}: {order['proposed_action']}"
        )
    lines.extend(["", "## Safety", ""])
    for key, value in (profile.get("safety") or {}).items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def write_profile(profile: dict[str, Any], root: Path) -> dict[str, Any]:
    payload = json.dumps(profile, indent=2, sort_keys=True, default=str)
    markdown = render_markdown(profile)
    root = root.resolve()
    vault_path = resolve_obsidian_note_path(DEFAULT_VAULT_NOTE, repo_root=root)
    files = {
        DEFAULT_OUTPUT_JSON.as_posix(): payload,
        DEFAULT_OUTPUT_MD.as_posix(): markdown,
        DEFAULT_PUBLIC_JSON.as_posix(): payload,
        DEFAULT_STATE_PATH.as_posix(): payload,
        DEFAULT_COMPONENT.as_posix(): render_component(),
    }
    try:
        vault_relative = vault_path.relative_to(root)
    except ValueError:
        vault_relative = None
    if vault_relative is not None:
        files[vault_relative.as_posix()] = markdown
    app_path = root / DEFAULT_APP_PATH
    if app_path.exists():
        files[DEFAULT_APP_PATH.as_posix()] = mount_component_in_app(
            app_path.read_text(encoding="utf-8", errors="replace")
        )

    for rel, content in files.items():
        path = (root / rel).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError as exc:
            raise RuntimeError(f"Bounded local writer refused to escape the repository: {rel}") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    created_files = list(files)
    if vault_relative is None:
        vault_path.parent.mkdir(parents=True, exist_ok=True)
        vault_path.write_text(markdown, encoding="utf-8")
        created_files.append(str(vault_path))
    return {"writer": BOUNDED_LOCAL_WRITER, "created_files": created_files}


def build_and_write_profile(
    goal: str,
    *,
    root: Path | None = None,
    online: bool = False,
    online_limit: int = 3,
) -> dict[str, Any]:
    repo_root = repo_root_from(root)
    profile = build_profile(goal, root=repo_root, online=online, online_limit=online_limit)
    write_info = write_profile(profile, repo_root)
    result = dict(profile)
    result["write_info"] = write_info
    state_payload = json.dumps(result, indent=2, sort_keys=True, default=str)
    state_path = (repo_root / DEFAULT_STATE_PATH).resolve()
    try:
        state_path.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise RuntimeError("Bounded local writer refused to escape the repository state path.") from exc
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(state_payload, encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Aureon's coding-agent skill base profile.")
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--goal", default="Teach Aureon to use its agents as coders and learn coding skills.")
    parser.add_argument(
        "--online", action="store_true", help="Run bounded read-only web search/fetch probes."
    )
    parser.add_argument("--online-limit", type=int, default=3)
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    result = build_and_write_profile(args.goal, root=root, online=args.online, online_limit=args.online_limit)
    print(json.dumps({"status": result["status"], "summary": result["summary"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
