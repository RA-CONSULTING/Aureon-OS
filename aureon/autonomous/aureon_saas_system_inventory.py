"""Repo-wide SaaS surface inventory for Aureon.

This scanner counts and classifies Aureon's product-facing stack: React/Vite
frontend files, Supabase edge functions, local dashboard/static UI surfaces,
legacy templates, and generated accounting HTML that may be shown to an
operator. It is read-only and produces both audit artifacts and public copies
that the unified frontend can observe.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from aureon.obsidian_paths import resolve_obsidian_note_path


SCHEMA_VERSION = "aureon-saas-system-inventory-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_saas_system_inventory.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_saas_system_inventory.json")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_saas_system_inventory.json")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/aureon_saas_system_inventory.md")

SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".html", ".css", ".scss", ".json"}
SKIP_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".vite",
    ".cache",
}
GENERATED_PUBLIC_MANIFESTS = {
    "aureon_saas_system_inventory.json",
    "aureon_frontend_unification_plan.json",
    "aureon_organism_runtime_status.json",
    "aureon_frontend_evolution_queue.json",
}

SAAS_ROOTS = (
    "frontend",
    "supabase/functions",
    "aureon/vault/ui",
    "templates",
    "public",
    "Kings_Accounting_Suite/output",
)

LOCAL_DASHBOARD_GLOBS = (
    "aureon/command_centers/**/*.py",
    "aureon/vault/ui/**/*.py",
    "aureon/bots/*command_center*.py",
    "aureon/bots/orca_launcher.py",
    "aureon/wisdom/aureon_samuel_agent.py",
)

DOMAIN_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("trading", ("trade", "trading", "kraken", "binance", "alpaca", "capital", "market", "position", "portfolio", "order", "margin")),
    ("accounting", ("account", "accounts", "hmrc", "companies", "ct600", "vat", "cis", "ledger", "invoice", "filing", "tax")),
    ("research", ("research", "source", "corpus", "gallery", "validation", "knowledge", "paper")),
    ("vault_memory", ("vault", "obsidian", "memory", "utterance", "voice", "bridge")),
    ("cognition", ("brain", "mind", "queen", "hive", "conscious", "thought", "self", "cognitive", "aureon")),
    ("saas_security", ("auth", "security", "tenant", "permission", "credential", "kyc", "admin", "session", "hnc", "nexus")),
    ("operator", ("dashboard", "command", "status", "health", "terminal", "monitor", "panel", "overview")),
)

SCREEN_DEFINITIONS = {
    "overview": ("organism", "health", "status", "terminal", "command", "overview", "dashboard"),
    "trading": DOMAIN_KEYWORDS[0][1],
    "accounting": DOMAIN_KEYWORDS[1][1],
    "research": DOMAIN_KEYWORDS[2][1],
    "vault": DOMAIN_KEYWORDS[3][1],
    "cognition": DOMAIN_KEYWORDS[4][1],
    "saas_security": DOMAIN_KEYWORDS[5][1],
    "self_improvement": ("audit", "benchmark", "readiness", "capability", "self", "wiring", "growth", "retest"),
    "admin": ("admin", "credential", "env", "settings", "payment", "kyc", "permission", "config"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root_from(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "aureon").is_dir() and (candidate / "scripts").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix().replace("\\", "/")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "surface"


def _read_text(path: Path, limit: int = 180_000) -> str:
    try:
        if not path.exists() or path.stat().st_size > 8_000_000:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


def _json_load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}


def _should_skip(path: Path) -> bool:
    return any(part in SKIP_PARTS for part in path.parts)


@dataclass
class SaaSSurface:
    id: str
    path: str
    name: str
    kind: str
    domain: str
    purpose: str
    owner_subsystem: str
    entrypoint_status: str
    imports: list[str] = field(default_factory=list)
    exports: list[str] = field(default_factory=list)
    called_apis: list[str] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)
    safety_class: str = "observation"
    auth_requirement: str = "unknown"
    runtime_route: str = ""
    wiring_status: str = "unknown"
    missing_next_step: str = ""
    legacy_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SaaSSystemInventory:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    summary: dict[str, Any]
    counts: dict[str, Any]
    gaps: dict[str, Any]
    surfaces: list[SaaSSurface]
    canonical_shell_targets: list[dict[str, Any]]
    vault_memory: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "summary": dict(self.summary),
            "counts": dict(self.counts),
            "gaps": dict(self.gaps),
            "surfaces": [item.to_dict() for item in self.surfaces],
            "canonical_shell_targets": list(self.canonical_shell_targets),
            "vault_memory": dict(self.vault_memory),
            "notes": list(self.notes),
        }


def collect_saas_paths(root: Path) -> list[Path]:
    paths: set[Path] = set()
    for rel_root in SAAS_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES and not _should_skip(path):
                if path.name in GENERATED_PUBLIC_MANIFESTS:
                    continue
                if rel_root == "Kings_Accounting_Suite/output" and path.suffix.lower() != ".html":
                    continue
                paths.add(path)
    for pattern in LOCAL_DASHBOARD_GLOBS:
        for path in root.glob(pattern):
            if path.is_file() and not _should_skip(path):
                paths.add(path)
    return sorted(paths, key=lambda item: _rel(item, root))


def _classify_kind(rel: str) -> str:
    if rel == "frontend/package.json" or rel.startswith("frontend/") and rel.endswith((".config.ts", ".config.js")):
        return "frontend_config"
    if rel.startswith("frontend/src/components/") and rel.endswith((".tsx", ".jsx")):
        return "frontend_component"
    if rel.startswith("frontend/src/pages/"):
        return "frontend_page"
    if rel.startswith("frontend/src/hooks/"):
        return "frontend_hook"
    if rel.startswith("frontend/src/services/"):
        return "frontend_service"
    if rel.startswith("frontend/src/core/"):
        return "frontend_core"
    if rel.startswith("frontend/src/lib/"):
        return "frontend_lib"
    if rel.startswith("frontend/src/integrations/"):
        return "frontend_integration"
    if rel.startswith("frontend/"):
        return "frontend_source"
    if rel.startswith("supabase/functions/"):
        return "supabase_function"
    if rel.startswith("aureon/vault/ui/static/"):
        return "vault_ui_static"
    if rel.startswith("aureon/vault/ui/"):
        return "vault_ui_server"
    if rel.startswith("templates/"):
        return "legacy_template"
    if rel.startswith("public/"):
        return "public_asset"
    if rel.startswith("Kings_Accounting_Suite/output/"):
        return "accounting_generated_html"
    if rel.startswith("aureon/command_centers/") or "command_center" in rel or "samuel_agent" in rel or "orca_launcher" in rel:
        return "local_dashboard_server"
    return "saas_surface"


def _classify_domain(rel: str, text: str) -> str:
    haystack = f"{rel} {text[:1200]}".lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in haystack)
        for domain, keywords in DOMAIN_KEYWORDS
    }
    domain, score = max(scores.items(), key=lambda item: item[1])
    return domain if score else "operator"


def _owner_subsystem(rel: str, kind: str, domain: str) -> str:
    if kind.startswith("frontend"):
        return "frontend_react_vite"
    if kind == "supabase_function":
        return "supabase_edge_functions"
    if kind.startswith("vault"):
        return "vault_ui"
    if kind == "legacy_template":
        return "legacy_queen_dashboards"
    if kind == "accounting_generated_html":
        return "kings_accounting_suite"
    if kind == "local_dashboard_server":
        return "local_command_center"
    return f"{domain}_saas_surface"


def _purpose(rel: str, kind: str, domain: str) -> str:
    stem = Path(rel).stem.replace("_", " ").replace("-", " ")
    if kind == "supabase_function":
        function_name = rel.split("/")[2] if len(rel.split("/")) > 2 else stem
        return f"Serverless API function for {function_name.replace('-', ' ')}."
    if kind == "accounting_generated_html":
        return "Generated accounting document HTML visible to filing/review workflows."
    if kind == "legacy_template":
        return f"Legacy dashboard template for {stem}."
    if kind == "vault_ui_static":
        return f"Vault UI static page or client asset for {stem}."
    if kind == "local_dashboard_server":
        return f"Local Python dashboard or command server for {stem}."
    return f"{kind.replace('_', ' ')} for {domain.replace('_', ' ')}: {stem}."


IMPORT_RE = re.compile(r"import(?:\s+type)?(?:[\s\S]*?)from\s+['\"]([^'\"]+)['\"]|import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)")
EXPORT_RE = re.compile(r"\bexport\s+(?:default\s+)?(?:class|function|const|let|var|interface|type|enum)\s+([A-Za-z0-9_]+)")
INVOKE_RE = re.compile(r"supabase\.functions\.invoke\(\s*['\"]([^'\"]+)['\"]")
FETCH_RE = re.compile(r"\bfetch\(\s*['\"]([^'\"]+)['\"]")
WS_RE = re.compile(r"new\s+WebSocket\(\s*([^)]+)\)|['\"](wss?://[^'\"]+)['\"]")
PY_ROUTE_RE = re.compile(r"(?:@app\.route|router\.add_(?:get|post)|app\.router\.add_(?:get|post))\(\s*['\"]([^'\"]+)['\"]")


def _extract_imports(text: str) -> list[str]:
    imports = []
    for match in IMPORT_RE.finditer(text):
        imports.append(match.group(1) or match.group(2) or "")
    return sorted({item for item in imports if item})


def _extract_exports(text: str) -> list[str]:
    return sorted({match.group(1) for match in EXPORT_RE.finditer(text) if match.group(1)})


def _extract_called_apis(text: str) -> list[str]:
    calls: set[str] = set()
    calls.update(f"supabase:{match.group(1)}" for match in INVOKE_RE.finditer(text))
    calls.update(match.group(1) for match in FETCH_RE.finditer(text))
    for match in WS_RE.finditer(text):
        value = match.group(1) or match.group(2) or ""
        if value:
            calls.add(value.strip())
    calls.update(f"route:{match.group(1)}" for match in PY_ROUTE_RE.finditer(text))
    return sorted(calls)


def _extract_data_sources(text: str) -> list[str]:
    sources = set()
    for token in re.findall(r"['\"]([^'\"]+\.(?:csv|json|jsonl|pdf|xlsx|html))['\"]", text, flags=re.I):
        sources.add(token)
    for token in re.findall(r"\b(?:localStorage|sessionStorage|supabase|ThoughtBus|Obsidian|WebSocket)\b", text):
        sources.add(token)
    return sorted(sources)


def _safety_class(rel: str, text: str) -> str:
    haystack = f"{rel} {text}".lower()
    if any(word in haystack for word in ("execute-trade", "addorder", "place order", "realmoney", "live trade", "withdraw", "exchange mutation")):
        return "live_trading_boundary"
    if any(word in haystack for word in ("payment", "gas-tank", "topup", "deduct-fee", "kyc")):
        return "payment_or_kyc_boundary"
    if any(word in haystack for word in ("api_key", "api key", "secret", "credential", "password", "session_token", "auth")):
        return "credential_or_auth_boundary"
    if any(word in haystack for word in ("hmrc", "companies house", "filing", "ct600", "tax")):
        return "manual_filing_boundary"
    if any(word in haystack for word in ("admin", "tenant", "permission", "rbac")):
        return "admin_or_tenant_boundary"
    return "observation"


def _auth_requirement(kind: str, safety_class: str, text: str) -> str:
    if safety_class in {"live_trading_boundary", "payment_or_kyc_boundary", "credential_or_auth_boundary", "admin_or_tenant_boundary"}:
        return "required"
    if "supabase.auth" in text or "Authorization" in text or "Bearer" in text:
        return "required"
    if kind in {"accounting_generated_html", "public_asset"}:
        return "not_applicable"
    return "read_only_or_unknown"


def _runtime_route(rel: str, kind: str, called_apis: Sequence[str]) -> str:
    if kind == "supabase_function":
        parts = rel.split("/")
        return f"supabase.functions.invoke('{parts[2]}')" if len(parts) > 2 else "supabase.functions.invoke"
    if kind == "legacy_template":
        return f"template:{rel}"
    if kind == "vault_ui_static":
        return f"/{Path(rel).name}"
    if kind == "public_asset":
        return f"/{Path(rel).name}"
    if called_apis:
        return ", ".join(called_apis[:3])
    return ""


def _resolve_import(import_path: str, source_rel: str, root: Path) -> Optional[str]:
    if not import_path or import_path.startswith((".", "@")) is False:
        return None
    if import_path.startswith("@/"):
        base = root / "frontend" / "src" / import_path[2:]
    else:
        base = (root / source_rel).parent / import_path
    candidates = [base]
    for suffix in (".tsx", ".ts", ".jsx", ".js", ".json"):
        candidates.append(Path(str(base) + suffix))
    candidates.extend([base / "index.tsx", base / "index.ts", base / "index.jsx", base / "index.js"])
    for candidate in candidates:
        if candidate.exists():
            return _rel(candidate, root)
    return None


def build_frontend_reachability(root: Path, surfaces: Sequence[SaaSSurface]) -> set[str]:
    imports_by_file: dict[str, list[str]] = {}
    known_paths = {surface.path for surface in surfaces}
    for surface in surfaces:
        if not surface.path.startswith("frontend/") or not surface.imports:
            continue
        imports_by_file[surface.path] = [
            resolved
            for imported in surface.imports
            for resolved in [_resolve_import(imported, surface.path, root)]
            if resolved in known_paths
        ]
    reachable: set[str] = set()
    queue = deque(path for path in ("frontend/src/main.tsx", "frontend/src/App.tsx") if path in known_paths)
    while queue:
        current = queue.popleft()
        if current in reachable:
            continue
        reachable.add(current)
        queue.extend(imports_by_file.get(current, []))
    return reachable


def _initial_surface(root: Path, path: Path) -> SaaSSurface:
    rel = _rel(path, root)
    text = _read_text(path)
    kind = _classify_kind(rel)
    domain = _classify_domain(rel, text)
    imports = _extract_imports(text)
    exports = _extract_exports(text)
    called_apis = _extract_called_apis(text)
    data_sources = _extract_data_sources(text)
    safety_class = _safety_class(rel, text)
    return SaaSSurface(
        id=f"saas_{_slug(rel)}",
        path=rel,
        name=Path(rel).name,
        kind=kind,
        domain=domain,
        purpose=_purpose(rel, kind, domain),
        owner_subsystem=_owner_subsystem(rel, kind, domain),
        entrypoint_status="entrypoint" if rel in {"frontend/src/App.tsx", "frontend/src/main.tsx", "frontend/index.html"} else "internal",
        imports=imports,
        exports=exports,
        called_apis=called_apis,
        data_sources=data_sources,
        safety_class=safety_class,
        auth_requirement=_auth_requirement(kind, safety_class, text),
        runtime_route=_runtime_route(rel, kind, called_apis),
    )


def finalize_wiring(root: Path, surfaces: list[SaaSSurface]) -> None:
    reachable = build_frontend_reachability(root, surfaces)
    called_supabase = {
        call.split(":", 1)[1]
        for surface in surfaces
        for call in surface.called_apis
        if call.startswith("supabase:")
    }
    for surface in surfaces:
        text = _read_text(root / surface.path)
        if "autoLogin(" in text:
            surface.wiring_status = "security_blocker"
            surface.missing_next_step = "Replace demo auto-login with explicit session/MFA/policy gate before SaaS production."
            continue
        if surface.kind.startswith("frontend"):
            surface.wiring_status = "wired" if surface.path in reachable else "orphaned"
            surface.missing_next_step = (
                "Keep as canonical reachable UI."
                if surface.wiring_status == "wired"
                else "Decide whether to migrate into the unified shell, expose through navigation, or archive."
            )
        elif surface.kind == "supabase_function":
            name = surface.path.split("/")[2] if len(surface.path.split("/")) > 2 else surface.name
            surface.wiring_status = "wired" if name in called_supabase else "partial"
            surface.missing_next_step = (
                "Verify auth and data contract from frontend caller."
                if surface.wiring_status == "wired"
                else "Decide whether this backend function needs a unified frontend panel or should be archived."
            )
        elif surface.kind in {"legacy_template", "vault_ui_static", "public_asset", "local_dashboard_server"}:
            surface.wiring_status = "legacy" if surface.kind == "legacy_template" else "partial"
            surface.legacy_action = "embed_or_migrate" if "dashboard" in surface.path.lower() else "keep_or_link"
            surface.missing_next_step = "Inventory for migration into the unified observation shell."
        elif surface.kind == "accounting_generated_html":
            surface.wiring_status = "generated_output"
            surface.missing_next_step = "Expose as accounting evidence/document link, not source UI code."
        else:
            surface.wiring_status = "unknown"
            surface.missing_next_step = "Review manually during SaaS unification planning."


def _canonical_targets(surfaces: Sequence[SaaSSurface]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    for screen, keywords in SCREEN_DEFINITIONS.items():
        matches = [
            surface
            for surface in surfaces
            if surface.wiring_status != "generated_output"
            and any(keyword in f"{surface.path} {surface.purpose} {surface.domain}".lower() for keyword in keywords)
        ]
        matches.sort(key=lambda item: (item.wiring_status != "wired", item.kind, item.path))
        targets.append(
            {
                "screen": screen,
                "surface_count": len(matches),
                "canonical_candidates": [item.path for item in matches[:12]],
                "missing": len(matches) == 0,
            }
        )
    return targets


def build_saas_system_inventory(repo_root: Optional[Path] = None) -> SaaSSystemInventory:
    root = repo_root_from(repo_root)
    paths = collect_saas_paths(root)
    surfaces = [_initial_surface(root, path) for path in paths]
    finalize_wiring(root, surfaces)

    kind_counts = Counter(surface.kind for surface in surfaces)
    domain_counts = Counter(surface.domain for surface in surfaces)
    wiring_counts = Counter(surface.wiring_status for surface in surfaces)
    safety_counts = Counter(surface.safety_class for surface in surfaces)
    owner_counts = Counter(surface.owner_subsystem for surface in surfaces)
    supabase_functions = {surface.path.split("/")[2] for surface in surfaces if surface.kind == "supabase_function" and len(surface.path.split("/")) > 2}
    called_supabase = {
        call.split(":", 1)[1]
        for surface in surfaces
        for call in surface.called_apis
        if call.startswith("supabase:")
    }
    missing_backend_calls = sorted(called_supabase - supabase_functions)
    uncalled_backend = sorted(supabase_functions - called_supabase)
    local_api_calls = sorted(
        {
            call
            for surface in surfaces
            for call in surface.called_apis
            if call.startswith("/") or call.startswith("http://") or call.startswith("https://") or call.startswith("route:")
        }
    )
    dashboard_like = [
        surface.path
        for surface in surfaces
        if "dashboard" in surface.path.lower() or surface.kind in {"legacy_template", "local_dashboard_server", "vault_ui_static"}
    ]
    gaps = {
        "security_blockers": [surface.to_dict() for surface in surfaces if surface.wiring_status == "security_blocker"],
        "orphaned_frontend": [surface.path for surface in surfaces if surface.wiring_status == "orphaned"][:200],
        "orphaned_frontend_count": wiring_counts.get("orphaned", 0),
        "uncalled_supabase_functions": uncalled_backend,
        "missing_supabase_functions_called_by_frontend": missing_backend_calls,
        "local_or_external_api_calls": local_api_calls[:200],
        "dashboard_like_surfaces": dashboard_like[:200],
        "dashboard_like_count": len(dashboard_like),
    }
    status = "inventory_ready_with_blockers" if gaps["security_blockers"] else "inventory_ready"
    summary = {
        "surface_count": len(surfaces),
        "frontend_surface_count": sum(count for kind, count in kind_counts.items() if kind.startswith("frontend")),
        "supabase_function_count": kind_counts.get("supabase_function", 0),
        "legacy_dashboard_count": kind_counts.get("legacy_template", 0) + kind_counts.get("local_dashboard_server", 0),
        "generated_accounting_html_count": kind_counts.get("accounting_generated_html", 0),
        "orphaned_frontend_count": wiring_counts.get("orphaned", 0),
        "security_blocker_count": wiring_counts.get("security_blocker", 0),
        "uncalled_supabase_function_count": len(uncalled_backend),
        "missing_supabase_function_call_count": len(missing_backend_calls),
    }
    counts = {
        "by_kind": dict(sorted(kind_counts.items())),
        "by_domain": dict(sorted(domain_counts.items())),
        "by_wiring_status": dict(sorted(wiring_counts.items())),
        "by_safety_class": dict(sorted(safety_counts.items())),
        "by_owner_subsystem": dict(sorted(owner_counts.items())),
    }
    return SaaSSystemInventory(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(root),
        status=status,
        summary=summary,
        counts=counts,
        gaps=gaps,
        surfaces=surfaces,
        canonical_shell_targets=_canonical_targets(surfaces),
        vault_memory={
            "status": "ready",
            "memory_summary": (
                f"Aureon SaaS inventory found {len(surfaces)} product-facing surfaces, "
                f"{summary['supabase_function_count']} Supabase functions, "
                f"{summary['orphaned_frontend_count']} orphaned frontend surfaces, "
                f"and {summary['security_blocker_count']} security blockers."
            ),
        },
        notes=[
            "Inventory is read-only and does not call live trading, payment, filing, or external attack paths.",
            "Generated accounting HTML is treated as review/output material, not source UI.",
            "The unified frontend should migrate important orphaned and legacy surfaces before anything is removed.",
        ],
    )


def render_markdown(inventory: SaaSSystemInventory) -> str:
    lines: list[str] = []
    lines.append("# Aureon SaaS System Inventory")
    lines.append("")
    lines.append(f"- Generated: `{inventory.generated_at}`")
    lines.append(f"- Repo: `{inventory.repo_root}`")
    lines.append(f"- Status: `{inventory.status}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in inventory.summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Counts")
    lines.append("")
    for key, value in inventory.counts.items():
        lines.append(f"- `{key}`:")
        lines.append("```json")
        lines.append(json.dumps(value, indent=2, sort_keys=True))
        lines.append("```")
    lines.append("")
    lines.append("## Canonical Shell Targets")
    lines.append("")
    lines.append("| Screen | Surface count | Canonical candidates |")
    lines.append("| --- | ---: | --- |")
    for target in inventory.canonical_shell_targets:
        candidates = ", ".join(f"`{item}`" for item in target.get("canonical_candidates", [])[:5]) or "missing"
        lines.append(f"| `{target['screen']}` | {target['surface_count']} | {candidates} |")
    lines.append("")
    lines.append("## Gaps")
    lines.append("")
    lines.append(f"- Security blockers: `{len(inventory.gaps.get('security_blockers') or [])}`")
    lines.append(f"- Orphaned frontend surfaces: `{inventory.gaps.get('orphaned_frontend_count', 0)}`")
    lines.append(f"- Uncalled Supabase functions: `{len(inventory.gaps.get('uncalled_supabase_functions') or [])}`")
    lines.append(f"- Missing Supabase functions called by frontend: `{len(inventory.gaps.get('missing_supabase_functions_called_by_frontend') or [])}`")
    lines.append("")
    lines.append("## Surface Checklist")
    lines.append("")
    lines.append("| Status | Kind | Domain | Safety | Path | Next step |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for surface in inventory.surfaces[:1200]:
        next_step = surface.missing_next_step.replace("|", "\\|")
        lines.append(
            f"| `{surface.wiring_status}` | `{surface.kind}` | `{surface.domain}` | `{surface.safety_class}` | `{surface.path}` | {next_step} |"
        )
    if len(inventory.surfaces) > 1200:
        lines.append(f"| ... | ... | ... | ... | `{len(inventory.surfaces) - 1200} more surfaces in JSON` | ... |")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in inventory.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def write_inventory(
    inventory: SaaSSystemInventory,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
    public_json_path: Path = DEFAULT_PUBLIC_JSON,
    vault_path: Path = DEFAULT_VAULT_NOTE,
) -> tuple[Path, Path, Path, Path]:
    root = Path(inventory.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    public_path = public_json_path if public_json_path.is_absolute() else root / public_json_path
    note_path = resolve_obsidian_note_path(vault_path, repo_root=root)
    for path in (md_path, js_path, public_path, note_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_markdown(inventory)
    data = json.dumps(inventory.to_dict(), indent=2, sort_keys=True, default=str)
    md_path.write_text(rendered, encoding="utf-8")
    js_path.write_text(data, encoding="utf-8")
    public_path.write_text(data, encoding="utf-8")
    note_path.write_text(rendered, encoding="utf-8")
    return md_path, js_path, public_path, note_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's full SaaS system inventory.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--public-json", default=str(DEFAULT_PUBLIC_JSON), help="Frontend-readable public JSON path.")
    parser.add_argument("--vault-note", default=str(DEFAULT_VAULT_NOTE), help="Vault note path.")
    parser.add_argument("--no-write", action="store_true", help="Print summary without writing artifacts.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    inventory = build_saas_system_inventory(root)
    if args.no_write:
        print(json.dumps({"status": inventory.status, "summary": inventory.summary}, indent=2, sort_keys=True))
    else:
        md_path, js_path, public_path, note_path = write_inventory(
            inventory,
            Path(args.markdown),
            Path(args.json),
            Path(args.public_json),
            Path(args.vault_note),
        )
        print(
            json.dumps(
                {
                    "status": inventory.status,
                    "markdown": str(md_path),
                    "json": str(js_path),
                    "public_json": str(public_path),
                    "vault_note": str(note_path),
                    "summary": inventory.summary,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
