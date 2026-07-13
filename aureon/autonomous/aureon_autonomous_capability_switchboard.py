"""Autonomous capability and presentation switchboard for Aureon.

The switchboard is the contract between the cognitive layer and the unified
frontend. It tells Aureon which internal capability can answer a goal, what it
may do autonomously, what evidence it must cite, and how the result should be
shown to the operator.

It is intentionally safe by design: the LLM/cognitive systems may choose,
plan, generate read-only presentation contracts, and queue work orders, but
live trading, official filing, payment, secret access, destructive deployment,
and third-party attacks stay behind their existing authority gates.
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

from aureon.autonomous.aureon_frontend_evolution_queue import (
    DEFAULT_OUTPUT_JSON as DEFAULT_EVOLUTION_JSON,
    build_frontend_evolution_queue,
)
from aureon.autonomous.aureon_goal_capability_map import build_goal_capability_map
from aureon.autonomous.aureon_saas_system_inventory import (
    DEFAULT_OUTPUT_JSON as DEFAULT_INVENTORY_JSON,
    build_saas_system_inventory,
    repo_root_from,
)


SCHEMA_VERSION = "aureon-autonomous-capability-switchboard-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_autonomous_capability_switchboard.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_autonomous_capability_switchboard.json")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_autonomous_capability_switchboard.json")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/aureon_autonomous_capability_switchboard.md")
DEFAULT_RUNTIME_JSON = Path("docs/audits/aureon_organism_runtime_status.json")
DEFAULT_PLAN_JSON = Path("docs/audits/aureon_frontend_unification_plan.json")
DEFAULT_HNC_SAAS_JSON = Path("docs/audits/hnc_saas_cognitive_bridge.json")


HNC_GATES = (
    "source_evidence_required",
    "manifest_freshness_checked",
    "data_contract_declared",
    "no_fake_state_or_hidden_totals",
    "confidence_and_blockers_visible",
    "safe_authority_boundary_checked",
    "result_retest_or_visual_smoke_required",
)


_MD_PIPE = "\\|"  # markdown-escaped pipe (kept out of f-string expressions for 3.11)

@dataclass
class CapabilityMode:
    id: str
    title: str
    domain: str
    authority_level: str
    status: str
    autonomous_allowed: bool
    triggers: list[str] = field(default_factory=list)
    systems: list[str] = field(default_factory=list)
    data_sources: list[str] = field(default_factory=list)
    hnc_checks: list[str] = field(default_factory=list)
    safe_actions: list[str] = field(default_factory=list)
    blocked_actions: list[str] = field(default_factory=list)
    frontend_contract: dict[str, Any] = field(default_factory=dict)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PresentationIntent:
    id: str
    title: str
    display_mode: str
    target_screen: str
    priority: int
    status: str
    reason: str
    source_paths: list[str] = field(default_factory=list)
    generated_artifact_contract: dict[str, Any] = field(default_factory=dict)
    hnc_evidence: dict[str, Any] = field(default_factory=dict)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AutonomousCapabilitySwitchboard:
    schema_version: str
    generated_at: str
    repo_root: str
    goal: str
    status: str
    summary: dict[str, Any]
    capability_modes: list[CapabilityMode]
    presentation_intents: list[PresentationIntent]
    route_map: dict[str, Any]
    hnc_control_contract: dict[str, Any]
    safety_contract: dict[str, Any]
    blockers: list[dict[str, Any]]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "goal": self.goal,
            "status": self.status,
            "summary": dict(self.summary),
            "capability_modes": [item.to_dict() for item in self.capability_modes],
            "presentation_intents": [item.to_dict() for item in self.presentation_intents],
            "route_map": dict(self.route_map),
            "hnc_control_contract": dict(self.hnc_control_contract),
            "safety_contract": dict(self.safety_contract),
            "blockers": list(self.blockers),
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
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "intent"


def _summary(manifest: dict[str, Any]) -> dict[str, Any]:
    return manifest.get("summary") if isinstance(manifest.get("summary"), dict) else {}


def _positive(summary: dict[str, Any], key: str) -> int:
    try:
        return int(float(summary.get(key) or 0))
    except Exception:
        return 0


def _domain_status(runtime_status: dict[str, Any], domain_id: str) -> str:
    for item in runtime_status.get("domains") or []:
        if isinstance(item, dict) and item.get("id") == domain_id:
            return str(item.get("status") or "unknown")
    return "unknown"


def _mode_status_from_domain(runtime_status: dict[str, Any], domain_id: str, fallback: str = "ready") -> str:
    status = _domain_status(runtime_status, domain_id)
    if status in {"missing", "broken"}:
        return "blocked_missing_manifest"
    if status in {"stale", "attention"}:
        return f"ready_with_{status}"
    return fallback


def build_capability_modes(
    inventory: dict[str, Any],
    evolution_queue: dict[str, Any],
    runtime_status: dict[str, Any],
    hnc_saas_state: dict[str, Any],
) -> list[CapabilityMode]:
    inventory_summary = _summary(inventory)
    queue_summary = _summary(evolution_queue)
    runtime_summary = _summary(runtime_status)
    security_blockers = _positive(inventory_summary, "security_blocker_count")
    ready_adapters = _positive(queue_summary, "ready_adapter_count")
    runtime_feed = str(runtime_summary.get("runtime_feed_status") or "unknown")
    real_time_feeds = runtime_status.get("real_time_feeds", {}) if isinstance(runtime_status.get("real_time_feeds"), dict) else {}
    action_capability = real_time_feeds.get("action_capability", {}) if isinstance(real_time_feeds.get("action_capability"), dict) else {}
    action_mode = str(runtime_summary.get("action_mode") or action_capability.get("mode") or "unknown")
    trading_action_allowed = bool(runtime_summary.get("trading_action_allowed", False))
    trading_status = (
        "guarded_live_action_ready"
        if trading_action_allowed
        else "runtime_feed_offline"
        if runtime_feed != "online"
        else f"{action_mode}_waiting_on_guards"
    )

    common_blocked = [
        "Inventing or displaying fake live data.",
        "Revealing secrets, API keys, credential values, or private tokens.",
        "Bypassing HNC evidence gates or hiding low confidence.",
    ]

    return [
        CapabilityMode(
            id="conversation_goal_router",
            title="Conversation And Goal Router",
            domain="operator",
            authority_level="autonomous_reasoning_and_contract_creation",
            status="ready",
            autonomous_allowed=True,
            triggers=["operator message", "self-question", "new goal", "unclear blocker"],
            systems=["GoalCapabilityMap", "OrganismContractStack", "ThoughtBus", "Queen meaning resolver", "Ollama/in-house LLM adapters"],
            data_sources=["operator prompt", "vault memory", "goal route map", "organism pulse"],
            hnc_checks=list(HNC_GATES),
            safe_actions=["Ask/answer internal questions.", "Create goal/task/job/work-order contracts.", "Explain current evidence and blockers to the operator."],
            blocked_actions=[*common_blocked, "Treating a generated answer as source evidence."],
            frontend_contract={
                "display_mode": "conversation_turn",
                "target_screen": "overview",
                "must_show": ["question", "route", "evidence", "confidence", "next_action"],
            },
            next_action="Use this route for operator dialogue and self-questioning before selecting a deeper capability.",
        ),
        CapabilityMode(
            id="frontend_design_orchestrator",
            title="Frontend Design And Layout Orchestrator",
            domain="frontend",
            authority_level="generate_read_only_ui_contracts",
            status="ready_with_backlog" if ready_adapters else "ready_watch_only",
            autonomous_allowed=True,
            triggers=["new dashboard need", "legacy screen found", "operator needs visibility", "important blocker"],
            systems=["AureonSaaSSystemInventory", "AureonFrontendUnificationPlan", "AureonFrontendEvolutionQueue", "React/Vite unified shell"],
            data_sources=[
                "docs/audits/aureon_saas_system_inventory.json",
                "docs/audits/aureon_frontend_unification_plan.json",
                "docs/audits/aureon_frontend_evolution_queue.json",
            ],
            hnc_checks=list(HNC_GATES),
            safe_actions=["Choose canonical screen.", "Propose or generate read-only status panels.", "Show source path, freshness, blocker, and safety boundary."],
            blocked_actions=[*common_blocked, "Executing legacy dashboard code inside the unified shell without an adapter."],
            frontend_contract={
                "display_mode": "dashboard_panel",
                "target_screen": "self_improvement",
                "must_show": ["source_path", "target_screen", "data_contract", "acceptance_tests"],
            },
            next_action="Convert high-priority ready work orders into read-only adapters and visual smoke tests.",
        ),
        CapabilityMode(
            id="app_generation",
            title="App Generation And Local Tool Builder",
            domain="self_improvement",
            authority_level="proposal_patch_test_retest",
            status=_mode_status_from_domain(runtime_status, "capability_growth_loop", "ready_for_validated_generation"),
            autonomous_allowed=True,
            triggers=["missing capability", "new workflow", "frontend adapter", "benchmark failure"],
            systems=["AureonCapabilityGrowthLoop", "SelfEnhancementEngine", "CodeArchitect", "SkillLibrary", "OrganismContractStack"],
            data_sources=["capability growth audit", "self-enhancement lifecycle", "test results", "repo self-catalog"],
            hnc_checks=list(HNC_GATES),
            safe_actions=["Generate scoped local code proposals.", "Run compile/tests/build/lint.", "Queue restart/apply handoff when needed."],
            blocked_actions=[*common_blocked, "Deploying to production or restarting critical services without an apply handoff."],
            frontend_contract={
                "display_mode": "generated_app_surface",
                "target_screen": "self_improvement",
                "must_show": ["requested_change", "files_changed", "tests_run", "retest_status"],
            },
            next_action="Keep generated code behind audit, benchmark, patch, retest, and explicit apply records.",
        ),
        CapabilityMode(
            id="image_generation_request",
            title="Image And Visual Asset Generation",
            domain="presentation",
            authority_level="prompt_contract_and_asset_request",
            status="ready_for_prompt_contract",
            autonomous_allowed=True,
            triggers=["visual explanation needed", "frontend design asset missing", "report needs diagram", "operator needs clarity"],
            systems=["frontend asset registry", "report renderer", "visual prompt contract", "HNC evidence gate"],
            data_sources=["source manifest", "report facts", "frontend screen plan", "repo asset folders"],
            hnc_checks=list(HNC_GATES),
            safe_actions=["Generate a visual brief from real source evidence.", "Request or attach a generated image asset.", "Label generated visuals as generated."],
            blocked_actions=[*common_blocked, "Using generated images as proof of real-world facts.", "Creating misleading charts without source data."],
            frontend_contract={
                "display_mode": "image_prompt_contract",
                "target_screen": "research",
                "must_show": ["visual_goal", "source_facts", "generated_asset_label", "review_status"],
            },
            next_action="Use generated visuals for explanation and interface clarity, never as hidden evidence.",
        ),
        CapabilityMode(
            id="research_search_and_vault",
            title="Research, Search, And Vault Memory",
            domain="research",
            authority_level="read_research_ingest_summarise",
            status=_mode_status_from_domain(runtime_status, "repo_self_catalog", "ready"),
            autonomous_allowed=True,
            triggers=["research question", "source missing", "fresh public fact needed", "vault recall"],
            systems=["ObsidianBridge", "ResearchCorpusIndex", "Queen meaning resolver", "RepoSelfCatalog", "ThoughtBus research intents"],
            data_sources=[".obsidian", "docs", "uploads", "public source links", "repo catalog"],
            hnc_checks=list(HNC_GATES),
            safe_actions=["Search local memory.", "Read source documents.", "Ingest source-linked summaries.", "Flag missing/uncertain evidence."],
            blocked_actions=[*common_blocked, "Treating unsourced memory as authoritative current fact."],
            frontend_contract={
                "display_mode": "search_report",
                "target_screen": "research",
                "must_show": ["sources", "freshness", "confidence", "unknowns"],
            },
            next_action="Keep research outputs source-linked and visible in the vault/research tab.",
        ),
        CapabilityMode(
            id="accounting_document_brain",
            title="Accounting Accounts And Evidence Builder",
            domain="accounting",
            authority_level="generate_manual_filing_support_documents",
            status=_mode_status_from_domain(runtime_status, "accounting_registry", "ready_with_manual_filing_boundary"),
            autonomous_allowed=True,
            triggers=["accounts", "tax", "VAT", "CIS", "Companies House", "HMRC", "missing evidence"],
            systems=["AccountingContextBridge", "AccountingSystemRegistry", "CombinedBankData", "Kings_Accounting_Suite", "UK accounting requirements brain"],
            data_sources=["bank feeds", "uploads", "accounting outputs", "evidence manifests", "generated accounts pack"],
            hnc_checks=list(HNC_GATES),
            safe_actions=["Generate final-ready support documents.", "Classify transactions.", "Prepare evidence requests.", "Show manual filing checklist."],
            blocked_actions=[*common_blocked, "HMRC submission.", "Companies House filing.", "Tax payment.", "Fake receipts or fake CIS statements."],
            frontend_contract={
                "display_mode": "document_link",
                "target_screen": "accounting",
                "must_show": ["period", "data_coverage", "documents", "manual_filing_required", "exceptions"],
            },
            next_action="Refresh the accounting registry and show every missing evidence item before final-ready claims.",
        ),
        CapabilityMode(
            id="trading_cognition_surface",
            title="Trading Cognition And Dynamic Positioning",
            domain="trading",
            authority_level=(
                "guarded_live_action_via_existing_runtime_gates"
                if trading_action_allowed
                else "observe_plan_and_delegate_to_existing_trading_gates"
            ),
            status=trading_status,
            autonomous_allowed=True,
            triggers=["market opportunity", "margin sizing", "Kraken collateral", "position risk", "temporal ETA"],
            systems=["dynamic_margin_sizer", "temporal_trade_cognition", "unified_margin_brain", "Kraken margin decision path", "ThoughtBus"],
            data_sources=["runtime feed", "exchange state metadata", "trade logs", "decision audit", "risk config"],
            hnc_checks=list(HNC_GATES),
            safe_actions=[
                "Observe balances and positions.",
                "Explain proposed decision logic.",
                "Publish risk and blocker state.",
                "Act only through the existing live executor when runtime guards allow it.",
                "Record every action with timestamp, source, blocker state, and verification result.",
            ],
            blocked_actions=[*common_blocked, "LLM direct order placement outside the explicit live trading executor."],
            frontend_contract={
                "display_mode": "decision_audit",
                "target_screen": "trading",
                "must_show": ["mode", "authority", "collateral", "risk", "decision_path", "costs", "api_governor", "verification"],
            },
            next_action=(
                "Trade through the existing runtime gates and record verified action evidence."
                if trading_action_allowed
                else "Bring the local runtime feed online and clear guard blockers before live action."
            ),
        ),
        CapabilityMode(
            id="saas_security_cognition",
            title="HNC SaaS Security And Authorized Test Lab",
            domain="saas_security",
            authority_level="authorized_local_or_owned_scope_test_fix_retest",
            status="blocked_security_review" if security_blockers else str(hnc_saas_state.get("status") or "ready"),
            autonomous_allowed=True,
            triggers=["security blocker", "release gate", "tenant isolation", "auth risk", "stress test"],
            systems=["HNCSaaSSecurityArchitect", "HNCAuthorizedAttackLab", "HNCSaaSCognitiveBridge", "OWASP ASVS map", "OrganismContractStack"],
            data_sources=["security blueprint", "authorized attack lab report", "SaaS inventory", "release gate evidence"],
            hnc_checks=list(HNC_GATES),
            safe_actions=["Run authorized local/owned-scope checks.", "Queue fixes.", "Retest and block release until evidence passes."],
            blocked_actions=[*common_blocked, "Third-party attacks without written authorization.", "Destructive payloads.", "Credential theft."],
            frontend_contract={
                "display_mode": "release_gate",
                "target_screen": "saas_security",
                "must_show": ["scope", "findings", "fixes", "retest", "release_blockers"],
            },
            next_action="Show blockers clearly and only test owned/local/staging surfaces.",
        ),
        CapabilityMode(
            id="continuous_self_enhancement",
            title="Continuous Audit, Benchmark, Fix, Retest Loop",
            domain="self_improvement",
            authority_level="safe_loop_with_apply_handoff",
            status=_mode_status_from_domain(runtime_status, "self_enhancement_lifecycle", "ready"),
            autonomous_allowed=True,
            triggers=["blind spot", "stale data", "failed test", "new capability request", "old system discovered"],
            systems=["RuntimeObserver", "SystemReadinessAudit", "MindWiringAudit", "CapabilityGrowthLoop", "RepoSelfCatalog", "FrontendEvolutionQueue"],
            data_sources=["runtime pulse", "audit manifests", "test reports", "benchmarks", "vault memory"],
            hnc_checks=list(HNC_GATES),
            safe_actions=["Refresh manifests.", "Benchmark domains.", "Queue work orders.", "Write vault memory.", "Report restart/apply requirements."],
            blocked_actions=[*common_blocked, "Infinite uncontrolled mutation loop.", "Silent rewrite of critical code without tests."],
            frontend_contract={
                "display_mode": "self_improvement_loop",
                "target_screen": "self_improvement",
                "must_show": ["audit", "benchmark", "fix", "retest", "apply_status"],
            },
            next_action="Keep observer running and use blockers as the next improvement queue.",
        ),
    ]


def build_presentation_intents(
    evolution_queue: dict[str, Any],
    runtime_status: dict[str, Any],
    inventory: dict[str, Any],
) -> list[PresentationIntent]:
    intents: list[PresentationIntent] = []
    queue_summary = _summary(evolution_queue)
    runtime_summary = _summary(runtime_status)
    inventory_summary = _summary(inventory)

    if _positive(queue_summary, "ready_adapter_count"):
        intents.append(
            PresentationIntent(
                id="intent.frontend_adapters_from_old_systems",
                title="Build read-only adapters from older dashboard systems",
                display_mode="generated_app_surface",
                target_screen="self_improvement",
                priority=98,
                status="ready_to_queue_adapters",
                reason=f"{_positive(queue_summary, 'ready_adapter_count')} old/frontend surfaces are ready to become unified console adapters.",
                source_paths=["docs/audits/aureon_frontend_evolution_queue.json"],
                generated_artifact_contract={
                    "artifact_type": "React status card",
                    "write_scope": "frontend/src/components/unified",
                    "verification": ["npm run build", "npm run lint", "visual smoke test"],
                },
                hnc_evidence={"required_gates": list(HNC_GATES), "source_manifest": "aureon_frontend_evolution_queue.json"},
                next_action="Take the highest-priority work order and generate a read-only adapter with tests.",
            )
        )

    if str(runtime_summary.get("runtime_feed_status") or "") != "online":
        intents.append(
            PresentationIntent(
                id="intent.runtime_feed_visibility",
                title="Show runtime feed as offline until real data arrives",
                display_mode="dashboard_panel",
                target_screen="overview",
                priority=95,
                status="blocked_waiting_for_runtime_feed",
                reason="The local runtime feed is offline, so the frontend must display manifest/audit state instead of fake live state.",
                source_paths=["docs/audits/aureon_organism_runtime_status.json"],
                generated_artifact_contract={"artifact_type": "status line", "fake_data_policy": "blocked"},
                hnc_evidence={"required_gates": list(HNC_GATES), "source_manifest": "aureon_organism_runtime_status.json"},
                next_action="Start the safe runtime status service or ignition process that exposes the read-only terminal-state endpoint.",
            )
        )

    if _positive(inventory_summary, "security_blocker_count"):
        intents.append(
            PresentationIntent(
                id="intent.security_blocker_wall",
                title="Surface security blockers before interactive controls",
                display_mode="release_gate",
                target_screen="saas_security",
                priority=94,
                status="blocked_security_review",
                reason=f"{_positive(inventory_summary, 'security_blocker_count')} security blockers are present in the SaaS inventory.",
                source_paths=["docs/audits/aureon_saas_system_inventory.json"],
                generated_artifact_contract={"artifact_type": "read-only blocker wall", "interactive_controls": "disabled_until_review"},
                hnc_evidence={"required_gates": list(HNC_GATES), "source_manifest": "aureon_saas_system_inventory.json"},
                next_action="Wire blockers into the SaaS Security screen and queue fixes through authorized local tests.",
            )
        )

    for order in (evolution_queue.get("work_orders") or [])[:12]:
        if not isinstance(order, dict):
            continue
        priority = _positive(order, "priority")
        target_screen = str(order.get("target_screen") or "overview")
        status = str(order.get("status") or "unknown")
        intents.append(
            PresentationIntent(
                id=f"intent.{slug(str(order.get('id') or order.get('source_path') or 'work_order'))}",
                title=str(order.get("title") or "Frontend work order"),
                display_mode="dashboard_panel" if status != "link_generated_output" else "document_link",
                target_screen=target_screen,
                priority=max(1, min(100, priority)),
                status=status,
                reason=str(order.get("capability_summary") or "Legacy surface should be represented in the unified console."),
                source_paths=[str(order.get("source_path") or "")],
                generated_artifact_contract={
                    "frontend_action": order.get("frontend_action"),
                    "data_contract": order.get("data_contract"),
                    "acceptance_tests": order.get("acceptance_tests"),
                },
                hnc_evidence={
                    "required_gates": list(HNC_GATES),
                    "safety_boundary": order.get("safety_boundary"),
                    "evidence": order.get("evidence"),
                },
                next_action=str(order.get("next_action") or "Create a read-only adapter or resolve blocker."),
            )
        )

    intents.sort(key=lambda item: (-item.priority, item.id))
    return intents[:40]


def build_blockers(
    capability_modes: Sequence[CapabilityMode],
    runtime_status: dict[str, Any],
    inventory: dict[str, Any],
    evolution_queue: dict[str, Any],
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    runtime_summary = _summary(runtime_status)
    inventory_summary = _summary(inventory)
    queue_summary = _summary(evolution_queue)
    if str(runtime_summary.get("runtime_feed_status") or "") != "online":
        blockers.append(
            {
                "id": "runtime_feed.offline",
                "domain": "runtime",
                "severity": "medium",
                "reason": "Real-time feed is offline; show audit/manifest state only.",
                "next_action": "Start the local read-only runtime status endpoint.",
            }
        )
    if _positive(inventory_summary, "security_blocker_count"):
        blockers.append(
            {
                "id": "saas_inventory.security_blockers",
                "domain": "saas_security",
                "severity": "high",
                "reason": f"{_positive(inventory_summary, 'security_blocker_count')} SaaS security blockers remain.",
                "next_action": "Route through HNC SaaS Security and authorized local retests.",
            }
        )
    if _positive(queue_summary, "blocked_count"):
        blockers.append(
            {
                "id": "frontend_evolution.blocked_work_orders",
                "domain": "frontend",
                "severity": "medium",
                "reason": f"{_positive(queue_summary, 'blocked_count')} frontend evolution work orders are blocked.",
                "next_action": "Resolve blocker status or create safe read-only status adapters.",
            }
        )
    for mode in capability_modes:
        if mode.status.startswith("blocked"):
            blockers.append(
                {
                    "id": f"capability.{mode.id}",
                    "domain": mode.domain,
                    "severity": "medium",
                    "reason": f"{mode.title} is {mode.status}.",
                    "next_action": mode.next_action,
                }
            )
    return blockers


def build_hnc_control_contract() -> dict[str, Any]:
    return {
        "decision_ladder": [
            "perceive_current_goal_or_blind_spot",
            "recall_vault_and_manifest_evidence",
            "classify_domain_and_select_capability",
            "run_hnc_anti_drift_gates",
            "create_contract_or_presentation_intent",
            "render_or_execute_only_within_authority",
            "verify_with_tests_or_source_reconciliation",
            "publish_status_back_to_frontend_vault_and_thoughtbus",
        ],
        "anti_hallucination_gates": list(HNC_GATES),
        "authority_matrix": {
            "conversation": "autonomous_allowed_with_evidence",
            "search_and_research": "autonomous_allowed_read_only",
            "frontend_design": "autonomous_allowed_read_only_or_tested_patch",
            "image_generation": "autonomous_prompt_contract_generated_asset_must_be_labelled",
            "app_generation": "autonomous_patch_allowed_only_with_tests_and_scope",
            "accounting_documents": "autonomous_generation_manual_filing_only",
            "trading_orders": "delegated_to_existing_live_trading_gates_only",
            "saas_security_tests": "owned_or_local_authorized_scope_only",
            "secrets": "metadata_status_only_never_reveal_values",
        },
        "drift_controls": [
            "No frontend panel may show trusted data without source_path and freshness.",
            "Generated media and generated reports must be labelled as generated.",
            "Low confidence or missing evidence must become a visible blocker.",
            "Unsafe side effects must become manual or gated actions, not hidden autonomy.",
        ],
    }


def build_autonomous_capability_switchboard(
    root: Optional[Path] = None,
    *,
    goal: str = "",
    inventory: Optional[dict[str, Any]] = None,
    evolution_queue: Optional[dict[str, Any]] = None,
    runtime_status: Optional[dict[str, Any]] = None,
    frontend_plan: Optional[dict[str, Any]] = None,
    hnc_saas_state: Optional[dict[str, Any]] = None,
) -> AutonomousCapabilitySwitchboard:
    root = repo_root_from(root)
    if inventory is None:
        inventory = load_json(root / DEFAULT_INVENTORY_JSON)
        if not inventory:
            inventory = build_saas_system_inventory(root).to_dict()
    if evolution_queue is None:
        evolution_queue = load_json(root / DEFAULT_EVOLUTION_JSON)
        if not evolution_queue:
            evolution_queue = build_frontend_evolution_queue(root, inventory=inventory).to_dict()
    if runtime_status is None:
        runtime_status = load_json(root / DEFAULT_RUNTIME_JSON)
    if frontend_plan is None:
        frontend_plan = load_json(root / DEFAULT_PLAN_JSON)
    if hnc_saas_state is None:
        hnc_saas_state = load_json(root / DEFAULT_HNC_SAAS_JSON)

    goal_text = goal or (
        "Select the best Aureon capability, presentation surface, generated artifact, "
        "search/research route, or conversation turn while preventing hallucination and drift."
    )
    route_map = build_goal_capability_map(root, current_goal=goal_text).compact()
    capability_modes = build_capability_modes(inventory, evolution_queue, runtime_status, hnc_saas_state)
    presentation_intents = build_presentation_intents(evolution_queue, runtime_status, inventory)
    blockers = build_blockers(capability_modes, runtime_status, inventory, evolution_queue)
    mode_counts = Counter(mode.status for mode in capability_modes)
    intent_counts = Counter(intent.status for intent in presentation_intents)
    autonomous_count = sum(1 for mode in capability_modes if mode.autonomous_allowed)
    blocked_capabilities = sum(1 for mode in capability_modes if mode.status.startswith("blocked"))
    status = "switchboard_ready_with_blockers" if blockers else "switchboard_ready"

    summary = {
        "capability_count": len(capability_modes),
        "autonomous_capability_count": autonomous_count,
        "blocked_capability_count": blocked_capabilities,
        "presentation_intent_count": len(presentation_intents),
        "blocker_count": len(blockers),
        "frontend_work_order_count": _positive(_summary(evolution_queue), "queue_count"),
        "ready_adapter_count": _positive(_summary(evolution_queue), "ready_adapter_count"),
        "security_blocker_count": _positive(_summary(inventory), "security_blocker_count"),
        "runtime_feed_status": _summary(runtime_status).get("runtime_feed_status", "unknown"),
        "action_mode": _summary(runtime_status).get("action_mode", "unknown"),
        "trading_action_allowed": bool(_summary(runtime_status).get("trading_action_allowed", False)),
        "canonical_screen_count": _positive(_summary(frontend_plan), "screen_count"),
    }

    safety_contract = {
        "llm_can_select_capability": True,
        "llm_can_create_presentation_intents": True,
        "llm_can_queue_work_orders": True,
        "llm_can_generate_frontend_or_app_code_after_tests": True,
        "llm_can_request_labelled_generated_visuals": True,
        "llm_can_publish_thoughtbus_status": True,
        "runtime_can_place_live_orders_via_existing_gates": bool(summary["trading_action_allowed"]),
        "llm_can_place_direct_live_orders": False,
        "llm_can_file_hmrc_or_companies_house": False,
        "llm_can_make_payments": False,
        "llm_can_attack_third_party_targets": False,
        "secret_values_hidden": True,
        "unsafe_actions_become_blockers": True,
    }

    return AutonomousCapabilitySwitchboard(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(root),
        goal=goal_text,
        status=status,
        summary=summary,
        capability_modes=capability_modes,
        presentation_intents=presentation_intents,
        route_map={
            **route_map,
            "capability_status_counts": dict(sorted(mode_counts.items())),
            "presentation_intent_status_counts": dict(sorted(intent_counts.items())),
        },
        hnc_control_contract=build_hnc_control_contract(),
        safety_contract=safety_contract,
        blockers=blockers,
        notes=[
            "The switchboard lets cognition choose between conversation, search, app generation, image/visual requests, accounting, trading observation, SaaS security, and self-enhancement.",
            "Every generated UI/report/action must carry source evidence, freshness, confidence, and a safe authority boundary.",
            "Aureon may evolve frontend/app surfaces through scoped work orders and tests; unsafe side effects stay blocked or manual.",
        ],
    )


def render_markdown(switchboard: AutonomousCapabilitySwitchboard) -> str:
    lines = [
        "# Aureon Autonomous Capability Switchboard",
        "",
        f"- Generated: `{switchboard.generated_at}`",
        f"- Status: `{switchboard.status}`",
        f"- Repo: `{switchboard.repo_root}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in switchboard.summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Capability Modes", "", "| Status | Domain | Authority | Capability | Next action |", "| --- | --- | --- | --- | --- |"])
    for mode in switchboard.capability_modes:
        lines.append(
            f"| `{mode.status}` | `{mode.domain}` | `{mode.authority_level}` | {mode.title} | "
            f"{mode.next_action.replace('|', _MD_PIPE)} |"
        )
    lines.extend(["", "## Presentation Intents", "", "| Priority | Status | Display | Target | Intent |", "| ---: | --- | --- | --- | --- |"])
    for intent in switchboard.presentation_intents[:80]:
        lines.append(
            f"| {intent.priority} | `{intent.status}` | `{intent.display_mode}` | `{intent.target_screen}` | "
            f"{intent.title.replace('|', _MD_PIPE)} |"
        )
    lines.extend(["", "## HNC Control Contract", "", "```json", json.dumps(switchboard.hnc_control_contract, indent=2, sort_keys=True), "```"])
    lines.extend(["", "## Safety Contract", ""])
    for key, value in switchboard.safety_contract.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Blockers", ""])
    if switchboard.blockers:
        for blocker in switchboard.blockers:
            lines.append(f"- `{blocker.get('severity')}` `{blocker.get('id')}`: {blocker.get('reason')} Next: {blocker.get('next_action')}")
    else:
        lines.append("- No blockers detected in this switchboard pass.")
    lines.append("")
    return "\n".join(lines)


def write_switchboard(
    switchboard: AutonomousCapabilitySwitchboard,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
    public_json_path: Path = DEFAULT_PUBLIC_JSON,
    vault_path: Path = DEFAULT_VAULT_NOTE,
) -> tuple[Path, Path, Path, Path]:
    root = Path(switchboard.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    public_path = public_json_path if public_json_path.is_absolute() else root / public_json_path
    note_path = vault_path if vault_path.is_absolute() else root / vault_path
    for path in (md_path, js_path, public_path, note_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_markdown(switchboard)
    data = json.dumps(switchboard.to_dict(), indent=2, sort_keys=True, default=str)
    md_path.write_text(rendered, encoding="utf-8")
    js_path.write_text(data, encoding="utf-8")
    public_path.write_text(data, encoding="utf-8")
    note_path.write_text(rendered, encoding="utf-8")
    return md_path, js_path, public_path, note_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's autonomous capability switchboard.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--goal", default="", help="Current goal/intention used to route capabilities.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--public-json", default=str(DEFAULT_PUBLIC_JSON), help="Frontend-readable public JSON path.")
    parser.add_argument("--vault-note", default=str(DEFAULT_VAULT_NOTE), help="Vault note path.")
    parser.add_argument("--no-write", action="store_true", help="Print summary without writing artifacts.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    switchboard = build_autonomous_capability_switchboard(root, goal=str(args.goal or ""))
    if args.no_write:
        print(json.dumps({"status": switchboard.status, "summary": switchboard.summary}, indent=2, sort_keys=True))
    else:
        md_path, js_path, public_path, note_path = write_switchboard(
            switchboard,
            Path(args.markdown),
            Path(args.json),
            Path(args.public_json),
            Path(args.vault_note),
        )
        print(
            json.dumps(
                {
                    "status": switchboard.status,
                    "markdown": str(md_path),
                    "json": str(js_path),
                    "public_json": str(public_path),
                    "vault_note": str(note_path),
                    "summary": switchboard.summary,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
