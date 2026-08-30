"""Unified frontend planning layer for Aureon.

The planner consumes the SaaS inventory and turns the current spread of pages,
dashboards, APIs, and generated artifacts into one canonical observation shell:
Overview, Trading, Accounting, Research, SaaS Security, Self-Improvement, and
Admin.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from aureon.obsidian_paths import resolve_obsidian_note_path
from aureon.autonomous.aureon_saas_system_inventory import (
    DEFAULT_OUTPUT_JSON as DEFAULT_INVENTORY_JSON,
    build_saas_system_inventory,
    repo_root_from,
)


SCHEMA_VERSION = "aureon-frontend-unification-plan-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_frontend_unification_plan.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_frontend_unification_plan.json")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_frontend_unification_plan.json")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/aureon_frontend_unification_plan.md")


CANONICAL_SCREENS = (
    {
        "id": "overview",
        "title": "Overview",
        "domain": "operator",
        "goal": "Show organism state, active goals, ThoughtBus health, blockers, and what Aureon is doing now.",
        "keywords": ("overview", "status", "terminal", "health", "dashboard", "command"),
        "manual_only_actions": (),
    },
    {
        "id": "trading",
        "title": "Trading",
        "domain": "trading",
        "goal": "Observe dynamic margin, positions, risk, live/sim status, and decision audit without hiding order gates.",
        "keywords": ("trade", "trading", "kraken", "binance", "alpaca", "capital", "position", "margin", "order", "risk"),
        "manual_only_actions": ("live orders remain behind runtime trading gates",),
    },
    {
        "id": "accounting",
        "title": "Accounting",
        "domain": "accounting",
        "goal": "Show company accounts status, raw-data coverage, generated packs, evidence, missing data, and manual filing checklist.",
        "keywords": ("account", "accounts", "hmrc", "companies", "ct600", "vat", "cis", "ledger", "filing", "tax"),
        "manual_only_actions": ("Companies House filing", "HMRC submission", "tax or penalty payment"),
    },
    {
        "id": "research",
        "title": "Research",
        "domain": "research",
        "goal": "Show vault sources, research reports, source ingestion, knowledge coverage, and evidence freshness.",
        "keywords": ("research", "source", "corpus", "knowledge", "vault", "obsidian", "paper"),
        "manual_only_actions": (),
    },
    {
        "id": "saas_security",
        "title": "SaaS Security",
        "domain": "saas_security",
        "goal": "Show auth, tenant isolation, release gates, authorized attack-lab findings, fixes, and retest evidence.",
        "keywords": ("saas", "security", "auth", "tenant", "hnc", "permission", "session", "attack", "gate"),
        "manual_only_actions": ("production deployment approval", "third-party authorization scope signoff"),
    },
    {
        "id": "self_improvement",
        "title": "Self-Improvement",
        "domain": "autonomy",
        "goal": "Show audits, benchmarks, capability gaps, queued fixes, retest loop, and restart/apply handoff.",
        "keywords": ("audit", "benchmark", "readiness", "capability", "self", "wiring", "growth", "retest"),
        "manual_only_actions": ("code apply/restart approval when required",),
    },
    {
        "id": "admin",
        "title": "Admin",
        "domain": "admin",
        "goal": "Show env checks, integrations, credentials status, safety gates, manual-only actions, and operator handoff.",
        "keywords": ("admin", "credential", "env", "settings", "payment", "kyc", "permission", "config", "secret"),
        "manual_only_actions": ("credential entry", "payment approval", "official filing approval"),
    },
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "path": str(path)}


@dataclass
class CanonicalScreenPlan:
    id: str
    title: str
    domain: str
    goal: str
    source_surface_count: int
    canonical_sources: list[str] = field(default_factory=list)
    migrated_components: list[str] = field(default_factory=list)
    embedded_legacy_surfaces: list[str] = field(default_factory=list)
    backend_functions: list[str] = field(default_factory=list)
    generated_outputs: list[str] = field(default_factory=list)
    safety_notes: list[str] = field(default_factory=list)
    missing_capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FrontendUnificationPlan:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    summary: dict[str, Any]
    canonical_screens: list[CanonicalScreenPlan]
    migration_actions: list[dict[str, Any]]
    duplicate_dashboard_groups: list[dict[str, Any]]
    safety_contract: dict[str, Any]
    observation_loop: dict[str, Any]
    source_inventory_summary: dict[str, Any]
    vault_memory: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "summary": dict(self.summary),
            "canonical_screens": [item.to_dict() for item in self.canonical_screens],
            "migration_actions": list(self.migration_actions),
            "duplicate_dashboard_groups": list(self.duplicate_dashboard_groups),
            "safety_contract": dict(self.safety_contract),
            "observation_loop": dict(self.observation_loop),
            "source_inventory_summary": dict(self.source_inventory_summary),
            "vault_memory": dict(self.vault_memory),
            "notes": list(self.notes),
        }


def _surface_matches(surface: dict[str, Any], keywords: Sequence[str], domain: str) -> bool:
    haystack = " ".join(
        str(surface.get(key) or "")
        for key in ("path", "kind", "domain", "purpose", "owner_subsystem", "safety_class")
    ).lower()
    return surface.get("domain") == domain or any(keyword in haystack for keyword in keywords)


def _rank_surface(surface: dict[str, Any]) -> tuple[int, int, str]:
    status_order = {
        "wired": 0,
        "security_blocker": 1,
        "partial": 2,
        "legacy": 3,
        "orphaned": 4,
        "generated_output": 5,
        "unknown": 6,
    }
    kind_order = {
        "frontend_page": 0,
        "frontend_component": 1,
        "frontend_service": 2,
        "frontend_core": 3,
        "supabase_function": 4,
        "vault_ui_static": 5,
        "legacy_template": 6,
        "local_dashboard_server": 7,
        "accounting_generated_html": 8,
    }
    return (
        status_order.get(str(surface.get("wiring_status")), 9),
        kind_order.get(str(surface.get("kind")), 9),
        str(surface.get("path") or ""),
    )


def _build_screen_plans(inventory: dict[str, Any]) -> list[CanonicalScreenPlan]:
    surfaces = list(inventory.get("surfaces") or [])
    plans: list[CanonicalScreenPlan] = []
    for screen in CANONICAL_SCREENS:
        matches = [surface for surface in surfaces if _surface_matches(surface, screen["keywords"], screen["domain"])]
        matches.sort(key=_rank_surface)
        canonical = [surface["path"] for surface in matches if surface.get("kind", "").startswith("frontend")][:12]
        backend = [
            surface["path"].split("/")[2]
            for surface in matches
            if surface.get("kind") == "supabase_function" and len(str(surface.get("path") or "").split("/")) > 2
        ][:20]
        generated = [surface["path"] for surface in matches if surface.get("wiring_status") == "generated_output"][:20]
        legacy = [
            surface["path"]
            for surface in matches
            if surface.get("wiring_status") == "legacy" or surface.get("kind") in {"legacy_template", "local_dashboard_server", "vault_ui_static"}
        ][:20]
        blockers = [surface for surface in matches if surface.get("wiring_status") == "security_blocker"]
        missing: list[str] = []
        if not canonical:
            missing.append("No canonical React screen/component has been selected yet.")
        if screen["id"] in {"trading", "accounting", "saas_security", "admin"} and blockers:
            missing.append("Security blockers must be fixed before production promotion.")
        if screen["id"] == "accounting" and not generated:
            missing.append("Accounting generated outputs need to be linked from the shell.")
        if screen["id"] == "research" and not backend:
            missing.append("Research/vault status endpoint should be exposed or linked.")
        safety_notes = list(screen["manual_only_actions"])
        if blockers:
            safety_notes.append(f"{len(blockers)} security blocker surface(s) visible in inventory.")
        plans.append(
            CanonicalScreenPlan(
                id=screen["id"],
                title=screen["title"],
                domain=screen["domain"],
                goal=screen["goal"],
                source_surface_count=len(matches),
                canonical_sources=canonical,
                migrated_components=canonical[:6],
                embedded_legacy_surfaces=legacy,
                backend_functions=sorted(set(backend)),
                generated_outputs=generated,
                safety_notes=safety_notes,
                missing_capabilities=missing,
            )
        )
    return plans


def _migration_actions(inventory: dict[str, Any], screens: Sequence[CanonicalScreenPlan]) -> list[dict[str, Any]]:
    surfaces = list(inventory.get("surfaces") or [])
    actions: list[dict[str, Any]] = []
    gaps = inventory.get("gaps") or {}
    if gaps.get("security_blockers"):
        actions.append(
            {
                "id": "fix_security_blockers",
                "priority": 1,
                "action": "fix_before_production",
                "reason": "Security blocker surfaces cannot be hidden by the new shell.",
                "surface_count": len(gaps.get("security_blockers") or []),
            }
        )
    actions.append(
        {
            "id": "build_unified_shell",
            "priority": 2,
            "action": "canonicalize",
            "reason": "Create one observation shell with the seven canonical screens.",
            "screen_ids": [screen.id for screen in screens],
        }
    )
    orphaned_count = int((inventory.get("summary") or {}).get("orphaned_frontend_count") or 0)
    if orphaned_count:
        actions.append(
            {
                "id": "triage_orphaned_frontend",
                "priority": 3,
                "action": "migrate_keep_or_archive",
                "reason": "Important frontend surfaces exist but are not reachable from the current app entrypoint.",
                "surface_count": orphaned_count,
            }
        )
    uncalled = gaps.get("uncalled_supabase_functions") or []
    if uncalled:
        actions.append(
            {
                "id": "triage_backend_functions",
                "priority": 4,
                "action": "link_or_archive",
                "reason": "Backend functions exist without a confirmed frontend caller.",
                "surface_count": len(uncalled),
            }
        )
    legacy = [surface for surface in surfaces if surface.get("wiring_status") == "legacy"]
    if legacy:
        actions.append(
            {
                "id": "legacy_dashboard_transition",
                "priority": 5,
                "action": "embed_migrate_or_keep_link",
                "reason": "Legacy dashboards stay available until their useful panels are migrated.",
                "surface_count": len(legacy),
            }
        )
    return actions


def _duplicate_groups(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for surface in inventory.get("surfaces") or []:
        path = str(surface.get("path") or "")
        haystack = f"{path} {surface.get('purpose') or ''}".lower()
        if "dashboard" in haystack:
            groups["dashboards"].append(path)
        elif "credential" in haystack or "auth" in haystack:
            groups["auth_and_credentials"].append(path)
        elif "trade" in haystack or "exchange" in haystack:
            groups["trading_controls"].append(path)
        elif "account" in haystack or "filing" in haystack:
            groups["accounting_outputs"].append(path)
    return [
        {"group": key, "surface_count": len(paths), "surfaces": sorted(paths)[:80]}
        for key, paths in sorted(groups.items())
        if len(paths) > 1
    ]


def build_frontend_unification_plan(
    repo_root: Optional[Path] = None,
    *,
    inventory: Optional[dict[str, Any]] = None,
    regenerate_inventory: bool = False,
) -> FrontendUnificationPlan:
    root = repo_root_from(repo_root)
    if inventory is None:
        inventory_path = root / DEFAULT_INVENTORY_JSON
        if regenerate_inventory or not inventory_path.exists():
            inv_obj = build_saas_system_inventory(root)
            inventory = inv_obj.to_dict()
        else:
            inventory = load_json(inventory_path)
    screens = _build_screen_plans(inventory)
    actions = _migration_actions(inventory, screens)
    missing_screen_count = sum(1 for screen in screens if screen.missing_capabilities)
    security_blockers = int((inventory.get("summary") or {}).get("security_blocker_count") or 0)
    status = "unification_plan_ready_with_security_blockers" if security_blockers else "unification_plan_ready"
    summary = {
        "screen_count": len(screens),
        "migration_action_count": len(actions),
        "missing_screen_capability_count": missing_screen_count,
        "source_surface_count": (inventory.get("summary") or {}).get("surface_count", 0),
        "security_blocker_count": security_blockers,
        "frontend_surface_count": (inventory.get("summary") or {}).get("frontend_surface_count", 0),
        "supabase_function_count": (inventory.get("summary") or {}).get("supabase_function_count", 0),
    }
    return FrontendUnificationPlan(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(root),
        status=status,
        summary=summary,
        canonical_screens=screens,
        migration_actions=actions,
        duplicate_dashboard_groups=_duplicate_groups(inventory),
        safety_contract={
            "human_observes_aureon_works": True,
            "live_trading_requires_existing_runtime_gates": True,
            "official_filing_and_payments_manual_only": True,
            "credentials_status_visible_secret_values_hidden": True,
            "security_blockers_visible": True,
            "legacy_dashboards_preserved_until_migrated": True,
        },
        observation_loop={
            "manifest_sources": [
                "/aureon_frontend_unification_plan.json",
                "/aureon_saas_system_inventory.json",
                "docs/audits/aureon_frontend_unification_plan.json",
                "docs/audits/aureon_saas_system_inventory.json",
            ],
            "safe_status_sources": [
                "local terminal state endpoint",
                "Supabase read/status functions",
                "generated audit manifests",
                "ThoughtBus/status exports",
            ],
            "visible_decision_fields": ["what", "why", "confidence", "evidence", "next_action", "blockers"],
        },
        source_inventory_summary=inventory.get("summary") or {},
        vault_memory={
            "status": "ready",
            "memory_summary": (
                "Aureon has a canonical seven-screen frontend unification plan "
                f"covering {summary['source_surface_count']} SaaS surfaces."
            ),
        },
        notes=[
            "The unified frontend is an observation and command surface; Aureon remains the worker.",
            "Old dashboards are not removed in this pass; they are linked, embedded, or migrated after inventory proof.",
            "Manual-only actions stay visible and explicit instead of being automated silently.",
        ],
    )


def render_markdown(plan: FrontendUnificationPlan) -> str:
    lines: list[str] = []
    lines.append("# Aureon Frontend Unification Plan")
    lines.append("")
    lines.append(f"- Generated: `{plan.generated_at}`")
    lines.append(f"- Repo: `{plan.repo_root}`")
    lines.append(f"- Status: `{plan.status}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in plan.summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Canonical Screens")
    lines.append("")
    lines.append("| Screen | Sources | Backend | Missing | Safety |")
    lines.append("| --- | ---: | ---: | --- | --- |")
    for screen in plan.canonical_screens:
        missing = "; ".join(screen.missing_capabilities) or "none"
        safety = "; ".join(screen.safety_notes) or "observation"
        lines.append(
            f"| `{screen.title}` | {screen.source_surface_count} | {len(screen.backend_functions)} | {missing} | {safety} |"
        )
    lines.append("")
    lines.append("## Migration Actions")
    lines.append("")
    lines.append("| Priority | Action | Reason |")
    lines.append("| ---: | --- | --- |")
    for action in plan.migration_actions:
        lines.append(f"| {action.get('priority')} | `{action.get('id')}` {action.get('action')} | {action.get('reason')} |")
    lines.append("")
    lines.append("## Duplicate Groups")
    lines.append("")
    for group in plan.duplicate_dashboard_groups:
        lines.append(f"- `{group['group']}`: `{group['surface_count']}` surfaces")
    lines.append("")
    lines.append("## Safety Contract")
    lines.append("")
    for key, value in plan.safety_contract.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in plan.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def write_plan(
    plan: FrontendUnificationPlan,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
    public_json_path: Path = DEFAULT_PUBLIC_JSON,
    vault_path: Path = DEFAULT_VAULT_NOTE,
) -> tuple[Path, Path, Path, Path]:
    root = Path(plan.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    public_path = public_json_path if public_json_path.is_absolute() else root / public_json_path
    note_path = resolve_obsidian_note_path(vault_path, repo_root=root)
    for path in (md_path, js_path, public_path, note_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_markdown(plan)
    data = json.dumps(plan.to_dict(), indent=2, sort_keys=True, default=str)
    md_path.write_text(rendered, encoding="utf-8")
    js_path.write_text(data, encoding="utf-8")
    public_path.write_text(data, encoding="utf-8")
    note_path.write_text(rendered, encoding="utf-8")
    return md_path, js_path, public_path, note_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's unified autonomous frontend plan.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--regenerate-inventory", action="store_true", help="Regenerate SaaS inventory first.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--public-json", default=str(DEFAULT_PUBLIC_JSON), help="Frontend-readable public JSON path.")
    parser.add_argument("--vault-note", default=str(DEFAULT_VAULT_NOTE), help="Vault note path.")
    parser.add_argument("--no-write", action="store_true", help="Print summary without writing artifacts.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    plan = build_frontend_unification_plan(root, regenerate_inventory=args.regenerate_inventory)
    if args.no_write:
        print(json.dumps({"status": plan.status, "summary": plan.summary}, indent=2, sort_keys=True))
    else:
        md_path, js_path, public_path, note_path = write_plan(
            plan,
            Path(args.markdown),
            Path(args.json),
            Path(args.public_json),
            Path(args.vault_note),
        )
        print(
            json.dumps(
                {
                    "status": plan.status,
                    "markdown": str(md_path),
                    "json": str(js_path),
                    "public_json": str(public_path),
                    "vault_note": str(note_path),
                    "summary": plan.summary,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
