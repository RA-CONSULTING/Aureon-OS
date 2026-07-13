"""Living frontend evolution queue for Aureon.

The SaaS inventory answers "what exists?" and the unification plan answers
"where should it live?". This module turns those into concrete migration work
orders so the unified frontend can show Aureon continuously deciding which old
dashboard, API, vault, accounting, or cognition surface should be wired next.

It is proposal-only: no source file is edited and no external service is
called. A future apply step can consume these work orders with human-approved
or CI-approved code changes.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from aureon.autonomous.aureon_saas_system_inventory import (
    DEFAULT_OUTPUT_JSON as DEFAULT_INVENTORY_JSON,
    build_saas_system_inventory,
    repo_root_from,
)


SCHEMA_VERSION = "aureon-frontend-evolution-queue-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_frontend_evolution_queue.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_frontend_evolution_queue.json")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_frontend_evolution_queue.json")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/aureon_frontend_evolution_queue.md")

SCREEN_BY_DOMAIN = {
    "trading": "trading",
    "accounting": "accounting",
    "research": "research",
    "vault_memory": "research",
    "cognition": "self_improvement",
    "saas_security": "saas_security",
    "operator": "overview",
    "admin": "admin",
    "autonomy": "self_improvement",
}

SCREEN_TITLES = {
    "overview": "Overview",
    "trading": "Trading",
    "accounting": "Accounting",
    "research": "Research",
    "saas_security": "SaaS Security",
    "self_improvement": "Self-Improvement",
    "admin": "Admin",
}

OLD_SYSTEM_KINDS = {
    "legacy_template",
    "local_dashboard_server",
    "vault_ui_static",
    "accounting_generated_html",
    "frontend_component",
    "frontend_page",
    "frontend_service",
    "frontend_core",
}

LOW_VALUE_FRONTEND_FILES = {
    "components.json",
    "eslint.config.js",
    "postcss.config.js",
    "tailwind.config.ts",
    "tsconfig.json",
    "package-lock.json",
    "package.json",
}


_MD_PIPE = "\\|"  # markdown-escaped pipe (kept out of f-string expressions for 3.11)

@dataclass
class EvolutionWorkOrder:
    id: str
    title: str
    source_path: str
    source_kind: str
    source_domain: str
    target_screen: str
    target_title: str
    priority: int
    status: str
    capability_summary: str
    evidence: dict[str, Any] = field(default_factory=dict)
    data_contract: dict[str, Any] = field(default_factory=dict)
    frontend_action: str = ""
    safety_boundary: str = ""
    acceptance_tests: list[str] = field(default_factory=list)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FrontendEvolutionQueue:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    summary: dict[str, Any]
    work_orders: list[EvolutionWorkOrder]
    counts: dict[str, Any]
    source_inventory_summary: dict[str, Any]
    safety_contract: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "summary": dict(self.summary),
            "work_orders": [item.to_dict() for item in self.work_orders],
            "counts": dict(self.counts),
            "source_inventory_summary": dict(self.source_inventory_summary),
            "safety_contract": dict(self.safety_contract),
            "notes": list(self.notes),
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "path": str(path)}


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "surface"


def title_from_path(path: str) -> str:
    stem = Path(path).stem
    words = re.sub(r"[_\-]+", " ", stem).strip()
    return words.title() if words else Path(path).name


def target_screen_for(surface: dict[str, Any]) -> str:
    domain = str(surface.get("domain") or "")
    path = str(surface.get("path") or "").lower()
    if "account" in path or "hmrc" in path or "ct600" in path:
        return "accounting"
    if "kraken" in path or "trade" in path or "capital" in path or "binance" in path:
        return "trading"
    if "security" in path or "auth" in path or "kyc" in path or "tenant" in path:
        return "saas_security"
    if "vault" in path or "obsidian" in path or "research" in path:
        return "research"
    return SCREEN_BY_DOMAIN.get(domain, "overview")


def capability_summary(surface: dict[str, Any]) -> str:
    purpose = str(surface.get("purpose") or "").strip()
    if purpose:
        return purpose
    return f"{surface.get('kind', 'surface')} surface for {title_from_path(str(surface.get('path') or 'unknown'))}."


def work_order_status(surface: dict[str, Any]) -> str:
    safety = str(surface.get("safety_class") or "")
    wiring = str(surface.get("wiring_status") or "")
    kind = str(surface.get("kind") or "")
    filename = Path(str(surface.get("path") or "")).name
    if wiring == "security_blocker" or safety in {"live_trading_boundary", "payment_or_kyc_boundary"}:
        return "blocked_security_review"
    if safety in {"credential_or_auth_boundary", "admin_or_tenant_boundary"}:
        return "needs_safe_status_adapter"
    if kind == "accounting_generated_html":
        return "link_generated_output"
    if filename in LOW_VALUE_FRONTEND_FILES:
        return "archive_candidate"
    if wiring in {"orphaned", "legacy", "partial"}:
        return "ready_for_frontend_adapter"
    return "watch_only"


def priority_for(surface: dict[str, Any], status: str) -> int:
    score = 30
    kind = str(surface.get("kind") or "")
    domain = str(surface.get("domain") or "")
    path = str(surface.get("path") or "").lower()
    wiring = str(surface.get("wiring_status") or "")
    if status == "blocked_security_review":
        score += 45
    if status == "ready_for_frontend_adapter":
        score += 25
    if kind in {"local_dashboard_server", "legacy_template", "vault_ui_static"}:
        score += 24
    if wiring == "orphaned":
        score += 16
    if "dashboard" in path or "command_center" in path or "war" in path:
        score += 14
    if domain in {"trading", "accounting", "cognition", "saas_security"}:
        score += 10
    if Path(path).name in LOW_VALUE_FRONTEND_FILES:
        score -= 45
    return max(1, min(100, score))


def data_contract_for(surface: dict[str, Any], target_screen: str) -> dict[str, Any]:
    path = str(surface.get("path") or "")
    called_apis = list(surface.get("called_apis") or [])
    if target_screen == "trading":
        fields = ["mode", "positions", "risk", "decision", "blocked_reason", "last_updated"]
        topic = "trading.status"
    elif target_screen == "accounting":
        fields = ["company", "period", "pack_status", "evidence_status", "manual_filing_required", "last_updated"]
        topic = "accounting.status"
    elif target_screen == "research":
        fields = ["vault_status", "source_count", "freshness", "missing_sources", "last_updated"]
        topic = "research.status"
    elif target_screen == "saas_security":
        fields = ["release_gate", "findings", "fixes", "retest_status", "authorization_scope"]
        topic = "security.status"
    elif target_screen == "self_improvement":
        fields = ["audit", "benchmark", "queued_fix", "retest_status", "restart_required"]
        topic = "self_improvement.status"
    elif target_screen == "admin":
        fields = ["integration", "credential_status", "manual_action", "secret_value_hidden"]
        topic = "admin.status"
    else:
        fields = ["status", "health", "blockers", "last_updated"]
        topic = "organism.status"
    return {
        "expected_topic": topic,
        "safe_fields": fields,
        "source_called_apis": called_apis,
        "source_path": path,
        "secret_policy": "metadata_only_hide_values",
    }


def frontend_action_for(surface: dict[str, Any], target_screen: str, status: str) -> str:
    title = title_from_path(str(surface.get("path") or "surface"))
    component = re.sub(r"[^A-Za-z0-9]", "", title) or "LegacySurface"
    if status == "archive_candidate":
        return "Mark as infrastructure/supporting file; do not create an operator panel."
    if status == "blocked_security_review":
        return f"Create a read-only blocker card in {SCREEN_TITLES[target_screen]} before any interactive control."
    if status == "link_generated_output":
        return f"Add a document/evidence link card in {SCREEN_TITLES[target_screen]}."
    return f"Create frontend/src/components/unified/{component}StatusCard.tsx and mount it in the {SCREEN_TITLES[target_screen]} screen."


def should_include_surface(surface: dict[str, Any]) -> bool:
    kind = str(surface.get("kind") or "")
    wiring = str(surface.get("wiring_status") or "")
    legacy_action = str(surface.get("legacy_action") or "")
    path = str(surface.get("path") or "")
    if kind in {"frontend_config"} and Path(path).name in LOW_VALUE_FRONTEND_FILES:
        return wiring == "orphaned"
    return (
        kind in OLD_SYSTEM_KINDS
        and wiring in {"orphaned", "legacy", "partial", "security_blocker", "generated_output"}
    ) or bool(legacy_action)


def build_work_order(surface: dict[str, Any]) -> EvolutionWorkOrder:
    source_path = str(surface.get("path") or "")
    target_screen = target_screen_for(surface)
    status = work_order_status(surface)
    title = f"Wire {title_from_path(source_path)} into {SCREEN_TITLES[target_screen]}"
    priority = priority_for(surface, status)
    called_apis = list(surface.get("called_apis") or [])
    evidence = {
        "wiring_status": surface.get("wiring_status"),
        "legacy_action": surface.get("legacy_action"),
        "safety_class": surface.get("safety_class"),
        "auth_requirement": surface.get("auth_requirement"),
        "called_apis": called_apis,
        "missing_next_step": surface.get("missing_next_step"),
    }
    return EvolutionWorkOrder(
        id=f"frontend_evolution.{slug(source_path)}",
        title=title,
        source_path=source_path,
        source_kind=str(surface.get("kind") or "unknown"),
        source_domain=str(surface.get("domain") or "unknown"),
        target_screen=target_screen,
        target_title=SCREEN_TITLES[target_screen],
        priority=priority,
        status=status,
        capability_summary=capability_summary(surface),
        evidence=evidence,
        data_contract=data_contract_for(surface, target_screen),
        frontend_action=frontend_action_for(surface, target_screen, status),
        safety_boundary=(
            "Read-only observation card; no live trading, official filing, payment, "
            "credential reveal, or external mutation."
        ),
        acceptance_tests=[
            "Manifest exposes source path, target screen, safety boundary, and status.",
            "Unified frontend renders the work order without importing/executing the legacy system.",
            "Any missing/stale/fake data is displayed as a blocker instead of trusted.",
        ],
        next_action=(
            "Generate the read-only adapter/component and add a focused smoke test."
            if status not in {"archive_candidate", "blocked_security_review"}
            else "Resolve blocker or archive decision before migration."
        ),
    )


def build_frontend_evolution_queue(root: Optional[Path] = None, inventory: Optional[dict[str, Any]] = None) -> FrontendEvolutionQueue:
    root = repo_root_from(root)
    if inventory is None:
        inventory_path = root / DEFAULT_INVENTORY_JSON
        inventory = load_json(inventory_path)
        if not inventory:
            inventory = build_saas_system_inventory(root).to_dict()

    surfaces = [surface for surface in (inventory.get("surfaces") or []) if should_include_surface(surface)]
    work_orders = [build_work_order(surface) for surface in surfaces]
    work_orders.sort(key=lambda item: (-item.priority, item.target_screen, item.source_path))

    status_counts = Counter(order.status for order in work_orders)
    target_counts = Counter(order.target_screen for order in work_orders)
    kind_counts = Counter(order.source_kind for order in work_orders)
    blocked = status_counts.get("blocked_security_review", 0)
    ready = status_counts.get("ready_for_frontend_adapter", 0)
    queue_count = len(work_orders)
    status = "evolution_queue_ready_with_blockers" if blocked else "evolution_queue_ready"
    if queue_count == 0:
        status = "evolution_queue_empty"

    summary = {
        "queue_count": queue_count,
        "ready_adapter_count": ready,
        "blocked_count": blocked,
        "archive_candidate_count": status_counts.get("archive_candidate", 0),
        "generated_output_link_count": status_counts.get("link_generated_output", 0),
        "target_screen_count": len(target_counts),
        "highest_priority": work_orders[0].priority if work_orders else 0,
    }

    return FrontendEvolutionQueue(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(root),
        status=status,
        summary=summary,
        work_orders=work_orders,
        counts={
            "by_status": dict(sorted(status_counts.items())),
            "by_target_screen": dict(sorted(target_counts.items())),
            "by_source_kind": dict(sorted(kind_counts.items())),
        },
        source_inventory_summary=dict(inventory.get("summary") or {}),
        safety_contract={
            "proposal_only": True,
            "legacy_systems_not_executed": True,
            "read_only_frontend_adapters_first": True,
            "no_live_trading": True,
            "no_official_filing": True,
            "no_payments": True,
            "secret_values_hidden": True,
            "apply_requires_explicit_handoff": True,
        },
        notes=[
            "This queue is generated from the current SaaS inventory and is safe to show in the frontend.",
            "Work orders are migration intent, not proof that the legacy system has already been wired.",
            "Old systems stay available until their useful panels are replaced, embedded, or archived.",
        ],
    )


def render_markdown(queue: FrontendEvolutionQueue) -> str:
    lines = [
        "# Aureon Frontend Evolution Queue",
        "",
        f"- Generated: `{queue.generated_at}`",
        f"- Status: `{queue.status}`",
        f"- Repo: `{queue.repo_root}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in queue.summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Target Counts", "", "```json", json.dumps(queue.counts, indent=2, sort_keys=True), "```", ""])
    lines.extend(["## Work Orders", "", "| Priority | Status | Target | Source | Action |", "| ---: | --- | --- | --- | --- |"])
    for order in queue.work_orders[:200]:
        lines.append(
            f"| {order.priority} | `{order.status}` | `{order.target_screen}` | `{order.source_path}` | "
            f"{order.frontend_action.replace('|', _MD_PIPE)} |"
        )
    if len(queue.work_orders) > 200:
        lines.append(f"| ... | ... | ... | `{len(queue.work_orders) - 200} more work orders in JSON` | ... |")
    lines.extend(["", "## Safety", ""])
    for key, value in queue.safety_contract.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Notes", ""])
    for note in queue.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def write_queue(
    queue: FrontendEvolutionQueue,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
    public_json_path: Path = DEFAULT_PUBLIC_JSON,
    vault_path: Path = DEFAULT_VAULT_NOTE,
) -> tuple[Path, Path, Path, Path]:
    root = Path(queue.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    public_path = public_json_path if public_json_path.is_absolute() else root / public_json_path
    note_path = vault_path if vault_path.is_absolute() else root / vault_path
    for path in (md_path, js_path, public_path, note_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_markdown(queue)
    data = json.dumps(queue.to_dict(), indent=2, sort_keys=True, default=str)
    md_path.write_text(rendered, encoding="utf-8")
    js_path.write_text(data, encoding="utf-8")
    public_path.write_text(data, encoding="utf-8")
    note_path.write_text(rendered, encoding="utf-8")
    return md_path, js_path, public_path, note_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's frontend legacy-system evolution queue.")
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
    queue = build_frontend_evolution_queue(root)
    if args.no_write:
        print(json.dumps({"status": queue.status, "summary": queue.summary}, indent=2, sort_keys=True))
    else:
        md_path, js_path, public_path, note_path = write_queue(
            queue,
            Path(args.markdown),
            Path(args.json),
            Path(args.public_json),
            Path(args.vault_note),
        )
        print(
            json.dumps(
                {
                    "status": queue.status,
                    "markdown": str(md_path),
                    "json": str(js_path),
                    "public_json": str(public_path),
                    "vault_note": str(note_path),
                    "summary": queue.summary,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
