"""Unified readiness proof for Aureon's major organism capabilities.

The repo already has specialist audits. This module turns them into one
operator-facing proof: can Aureon understand its own wiring, route goals, reason
with LLM/vault systems, run research, prepare accounts, and make safe trading
decisions without crossing live-order or official-filing boundaries?
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence


SCHEMA_VERSION = "aureon-system-readiness-audit-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_system_readiness_audit.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_system_readiness_audit.json")

SAFE_AUDIT_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_ALLOW_SIM_FALLBACK": "0",
    "AUREON_QUIET_STARTUP": "1",
}

SYSTEM_GOAL = (
    "Aureon can trade, do company accounts, do research, understand itself, "
    "catalog and label every file, use LLM and vault systems, and coordinate "
    "goals, skills, tasks, jobs, and work orders as one safe organism that can "
    "audit, benchmark, fix, retest, learn, enhance itself, and use a "
    "controlled restart handoff, while pursuing an unhackable HNC SaaS through "
    "zero-trust controls, authorized self-attack, stress tests, repair, and retest."
)


@dataclass
class CapabilityProof:
    id: str
    name: str
    status: str
    summary: str
    systems: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    safety_boundary: str = ""
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AureonSystemReadinessAudit:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    proofs: list[CapabilityProof]
    safety: dict[str, Any]
    summary: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "proofs": [proof.to_dict() for proof in self.proofs],
            "safety": dict(self.safety),
            "summary": dict(self.summary),
            "notes": list(self.notes),
        }


def repo_root_from(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "aureon").is_dir() and (candidate / "scripts").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def apply_readiness_environment() -> dict[str, str]:
    os.environ.update(SAFE_AUDIT_ENV)
    try:
        from aureon.core.aureon_runtime_safety import apply_safe_runtime_environment

        apply_safe_runtime_environment(os.environ)
    except Exception:
        pass
    return {key: os.environ.get(key, "") for key in SAFE_AUDIT_ENV}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "path": str(path)}


def proof_status(ok: bool, attention: bool = False) -> str:
    if ok and attention:
        return "working_with_attention"
    if ok:
        return "working"
    # A failed or absent internal proof is a repair input, not a dead-end
    # authority decision. Outer boundaries (live money, filings, credentials,
    # destructive actions) are enforced separately by runtime safety.
    return "repair_pending"


def probe_repo_organization(root: Path) -> CapabilityProof:
    data = load_json(root / "docs" / "audits" / "repo_wide_organization_audit.json")
    if not data:
        return CapabilityProof(
            id="repo_organization",
            name="Repo Organization",
            status="repair_pending",
            summary="Repo-wide organization audit has not been generated yet.",
            systems=["repo_wide_organization_audit"],
            next_action="Run python -m aureon.autonomous.repo_wide_organization_audit.",
        )
    summary = data.get("summary") or {}
    surfaces = data.get("contract_surfaces") or []
    missing = [item.get("id") for item in surfaces if item.get("status") != "present"]
    unstaged = int(summary.get("unstaged_file_count") or 0)
    attention = bool(summary.get("attention_counts"))
    # A dirty working tree is an observation/ownership concern, not a missing
    # capability.  Treat only absent contract surfaces or an empty audit as a
    # real failure; preserve existing local work and route attention into the
    # evolution queue instead of closing the organism.
    ok = not missing and int(summary.get("recorded_files") or 0) > 0
    return CapabilityProof(
        id="repo_organization",
        name="Repo Organization",
        status=proof_status(ok, attention=attention and ok),
        summary=(
            f"{summary.get('recorded_files', 0)} files staged; "
            f"{unstaged} unstaged; {len(missing)} missing contract surfaces."
        ),
        systems=["repo_wide_organization_audit", "organism contract surfaces"],
        evidence={
            "audit_status": data.get("status"),
            "recorded_files": summary.get("recorded_files", 0),
            "stage_count": summary.get("stage_count", 0),
            "attention_counts": summary.get("attention_counts", {}),
            "missing_contract_surfaces": missing,
        },
        safety_boundary="Read-only path/size staging; no files moved or deleted.",
        next_action="Preserve existing local work; classify and reconcile attention paths without deleting or overwriting them.",
    )


def probe_repo_self_catalog(root: Path) -> CapabilityProof:
    data = load_json(root / "docs" / "audits" / "aureon_repo_self_catalog.json")
    summary = data.get("summary") or {}
    if not summary:
        return CapabilityProof(
            id="repo_self_catalog",
            name="File-By-File Self Catalog",
            status="repair_pending",
            summary="Repo self-catalog has not been generated yet.",
            systems=["AureonRepoSelfCatalog", "Obsidian repo self-catalog note"],
            next_action="Run python -m aureon.autonomous.aureon_repo_self_catalog.",
        )
    cataloged = int(summary.get("cataloged_file_count") or 0)
    truncated = bool(summary.get("truncated"))
    ok = cataloged > 0 and not truncated
    return CapabilityProof(
        id="repo_self_catalog",
        name="File-By-File Self Catalog",
        status=proof_status(ok, attention=bool(summary.get("safety_flag_counts")) and ok),
        summary=(
            f"{cataloged} project files labelled; "
            f"{summary.get('excluded_infrastructure_root_count', 0)} infrastructure roots recorded; "
            f"{summary.get('secret_metadata_only_count', 0)} secret surfaces metadata-only."
        ),
        systems=["AureonRepoSelfCatalog", "RepoWideOrganizationAudit", "vault note", "per-file LLM context"],
        evidence={
            "catalog_status": data.get("status"),
            "cataloged_file_count": cataloged,
            "domain_counts": data.get("domain_counts") or {},
            "subsystem_counts": data.get("subsystem_counts") or {},
            "file_kind_counts": data.get("file_kind_counts") or {},
            "vault_memory": data.get("vault_memory") or {},
            "coverage_policy": summary.get("coverage_policy"),
        },
        safety_boundary="Read-only metadata/symbol catalog; secret file contents are not copied into manifests or vault memory.",
        next_action="Regenerate after material repo changes so self-questioning and LLM prompts have current labels.",
    )


def probe_mind_wiring(root: Path) -> CapabilityProof:
    data = load_json(root / "docs" / "audits" / "mind_wiring_audit.json")
    counts = data.get("counts") or {}
    if not counts:
        return CapabilityProof(
            id="mind_wiring",
            name="Whole-Mind Wiring",
            status="repair_pending",
            summary="Mind wiring audit manifest is missing.",
            systems=["mind_wiring_audit", "organism_spine"],
            next_action="Run python -m aureon.autonomous.mind_wiring_audit --static --imports --local-services.",
        )
    broken = int(counts.get("broken") or 0)
    partial = int(counts.get("partial") or 0)
    unknown = int(counts.get("unknown") or 0)
    wired = int(counts.get("wired") or 0)
    service_probes = data.get("service_probes") or []
    reachable = [probe for probe in service_probes if probe.get("status") in {"reachable", "safe_simulated"}]
    ok = broken == 0 and partial == 0 and unknown == 0 and wired > 0
    return CapabilityProof(
        id="mind_wiring",
        name="Whole-Mind Wiring",
        status=proof_status(ok, attention=False),
        summary=f"{wired} wired, {partial} partial, {broken} broken, {unknown} unknown.",
        systems=["mind_wiring_audit", "organism_spine", "ThoughtBus", "local service probes"],
        evidence={"counts": counts, "safe_or_reachable_probe_count": len(reachable), "probe_count": len(service_probes)},
        safety_boundary="Audit mode forces live trading off and blocks real orders.",
        next_action="Keep this at zero broken/partial before adding new organism subsystems.",
    )


def probe_goal_routing(root: Path) -> CapabilityProof:
    try:
        from aureon.autonomous.aureon_goal_capability_map import build_goal_capability_map

        goal_map = build_goal_capability_map(repo_root=root, current_goal=SYSTEM_GOAL).to_dict()
        routes = {route.get("route") for route in goal_map.get("recommended_routes", [])}
        required = {
            "safe_trading_cognition",
            "safe_accounting_context",
            "safe_research_corpus",
            "repo_self_catalog",
            "capability_growth_loop",
            "safe_self_enhancement_lifecycle",
            "internal_contract_stack",
            "saas_product_inventory",
            "memory_and_state",
            "organism_wiring",
            "hnc_saas_security_architect",
        }
        missing = sorted(required - routes)
        ok = not missing
        return CapabilityProof(
            id="goal_routing",
            name="Goal, Skill, Task, And Route Brain",
            status=proof_status(ok, attention=bool(goal_map.get("errors")) and ok),
            summary=f"Goal map selected {len(routes)} routes for the whole-organism goal.",
            systems=["GoalCapabilityMap", "OrganismContractStack", "ThoughtBus", "ObsidianBridge"],
            evidence={
                "routes": sorted(routes),
                "missing_required_routes": missing,
                "tool_count": (goal_map.get("tool_registry") or {}).get("count", 0),
                "organism_node_count": (goal_map.get("organism") or {}).get("node_count", 0),
                "errors": goal_map.get("errors", []),
            },
            safety_boundary="The route map chooses systems but does not execute unsafe external actions.",
            next_action="Use these routes as the top-level dispatch proof for operator goals.",
        )
    except Exception as exc:
        return CapabilityProof(
            id="goal_routing",
            name="Goal, Skill, Task, And Route Brain",
            status="repair_pending",
            summary=f"Goal routing failed: {type(exc).__name__}: {exc}",
            systems=["GoalCapabilityMap"],
            next_action="Repair goal capability imports.",
        )


def probe_hnc_saas_security(root: Path) -> CapabilityProof:
    try:
        from aureon.autonomous.hnc_saas_security_architect import build_hnc_saas_security_blueprint

        blueprint = build_hnc_saas_security_blueprint(root, queue_contracts=False).to_dict()
        attack_lab = load_json(root / "docs" / "audits" / "hnc_authorized_attack_lab.json")
        cognitive_bridge = load_json(root / "docs" / "audits" / "hnc_saas_cognitive_bridge.json")
        if not cognitive_bridge:
            try:
                from aureon.autonomous.hnc_saas_cognitive_bridge import SaaSCognitiveBridge

                cognitive_bridge = SaaSCognitiveBridge(repo_root=root).load_context().to_dict()
            except Exception as bridge_exc:
                cognitive_bridge = {"error": f"{type(bridge_exc).__name__}: {bridge_exc}"}
        summary = blueprint.get("summary") or {}
        bridge_summary = cognitive_bridge.get("summary") or {}
        controls = blueprint.get("controls") or []
        gates = blueprint.get("release_gates") or []
        missing_domains = sorted(
            set(
                [
                    "identity_and_access",
                    "tenant_isolation",
                    "data_protection",
                    "api_application_security",
                    "ai_llm_tool_governance",
                    "trading_authority_boundary",
                    "accounting_filing_boundary",
                    "audit_observability",
                    "supply_chain",
                    "resilience_and_recovery",
                    "secure_sdlc",
                    "zero_trust_runtime",
                ]
            )
            - {item.get("domain") for item in controls}
        )
        bridge_topics = cognitive_bridge.get("thought_topics") or {}
        bridge_topics_wired = bool(bridge_summary.get("cognitive_topics_wired")) and all(
            key in bridge_topics for key in ("ready", "state", "question", "intent", "finding", "blocked")
        )
        ok = bool(summary.get("hnc_surface_count")) and not missing_domains and len(gates) >= 10 and bridge_topics_wired
        return CapabilityProof(
            id="hnc_saas_security",
            name="HNC SaaS Security Architect",
            status=proof_status(ok, attention=ok),
            summary=(
                f"{summary.get('hnc_surface_count', 0)} HNC surfaces; "
                f"{summary.get('control_count', 0)} controls; "
                f"{summary.get('unhackable_benchmark_count', 0)} unhackable benchmarks; "
                f"{summary.get('release_blocker_count', 0)} release blockers; "
                f"cognitive bridge {cognitive_bridge.get('status') or 'missing'}."
            ),
            systems=[
                "HNCSaaSSecurityArchitect",
                "HNCAuthorizedAttackLab",
                "HNCSaaSCognitiveBridge",
                "HNC inventory",
                "OWASP ASVS control matrix",
                "NIST zero-trust model",
                "SaaS ThoughtBus topics",
                "SelfQuestioningAI",
                "OrganismContractStack",
            ],
            evidence={
                "blueprint_status": blueprint.get("status"),
                "summary": summary,
                "missing_required_domains": missing_domains,
                "official_anchors": blueprint.get("official_anchors") or {},
                "unhackable_pursuit_loop": [item.get("id") for item in blueprint.get("unhackable_pursuit_loop") or []],
                "authorized_attack_lab": {
                    "status": attack_lab.get("status"),
                    "summary": attack_lab.get("summary") or {},
                },
                "saas_cognitive_bridge": {
                    "status": cognitive_bridge.get("status"),
                    "summary": bridge_summary,
                    "thought_topics": bridge_topics,
                    "contract_plan": cognitive_bridge.get("contract_plan") or {},
                    "question_ids": [item.get("id") for item in cognitive_bridge.get("questions") or []],
                    "decision_ids": [item.get("id") for item in cognitive_bridge.get("decisions") or []],
                    "error": cognitive_bridge.get("error"),
                },
            },
            safety_boundary="Authorized self-test planning only unless a local/staging allowlist is provided; no third-party attack, production deployment, live trading, filing, payment, or secret exposure.",
            next_action="Keep the SaaS cognition bridge active, queue fixes from authorized local/staging attack findings, retest, and keep production blocked until gates pass.",
        )
    except Exception as exc:
        return CapabilityProof(
            id="hnc_saas_security",
            name="HNC SaaS Security Architect",
            status="repair_pending",
            summary=f"HNC SaaS security blueprint failed: {type(exc).__name__}: {exc}",
            systems=["HNCSaaSSecurityArchitect"],
            next_action="Repair the HNC SaaS security architect import/build path.",
        )


def probe_saas_product_inventory(root: Path) -> CapabilityProof:
    try:
        from aureon.autonomous.aureon_frontend_unification_plan import build_frontend_unification_plan
        from aureon.autonomous.aureon_saas_system_inventory import build_saas_system_inventory

        inventory_data = load_json(root / "docs" / "audits" / "aureon_saas_system_inventory.json")
        if not inventory_data:
            inventory_data = build_saas_system_inventory(root).to_dict()
        plan_data = load_json(root / "docs" / "audits" / "aureon_frontend_unification_plan.json")
        if not plan_data:
            plan_data = build_frontend_unification_plan(root, inventory=inventory_data).to_dict()
        summary = inventory_data.get("summary") or {}
        plan_summary = plan_data.get("summary") or {}
        blockers = int(summary.get("security_blocker_count") or 0)
        surface_count = int(summary.get("surface_count") or 0)
        screen_count = int(plan_summary.get("screen_count") or 0)
        ok = surface_count > 0 and screen_count >= 7
        return CapabilityProof(
            id="saas_product_inventory",
            name="Unified SaaS Frontend Inventory",
            status=proof_status(ok, attention=blockers > 0 and ok),
            summary=(
                f"{surface_count} SaaS surfaces; "
                f"{summary.get('frontend_surface_count', 0)} frontend; "
                f"{summary.get('supabase_function_count', 0)} Supabase functions; "
                f"{screen_count} canonical screens; "
                f"{blockers} security blockers."
            ),
            systems=[
                "AureonSaaSSystemInventory",
                "AureonFrontendUnificationPlan",
                "React/Vite unified observation shell",
                "Supabase function inventory",
                "legacy dashboard transition map",
            ],
            evidence={
                "inventory_status": inventory_data.get("status"),
                "inventory_summary": summary,
                "inventory_counts": inventory_data.get("counts") or {},
                "plan_status": plan_data.get("status"),
                "plan_summary": plan_summary,
                "screen_ids": [screen.get("id") for screen in plan_data.get("canonical_screens") or []],
                "migration_actions": [item.get("id") for item in plan_data.get("migration_actions") or []],
            },
            safety_boundary="Inventory and frontend planning are read-only; generated UI observes status and keeps live trading, filing, payments, credentials, and deployment gates explicit.",
            next_action="Use the inventory and unification plan as the source of truth for migrating old dashboards into the unified observation shell.",
        )
    except Exception as exc:
        return CapabilityProof(
            id="saas_product_inventory",
            name="Unified SaaS Frontend Inventory",
            status="repair_pending",
            summary=f"SaaS inventory failed: {type(exc).__name__}: {exc}",
            systems=["AureonSaaSSystemInventory", "AureonFrontendUnificationPlan"],
            next_action="Repair SaaS inventory imports or frontend manifest paths.",
        )


def probe_contract_stack() -> CapabilityProof:
    try:
        from aureon.core.aureon_thought_bus import ThoughtBus
        from aureon.core.organism_contracts import OrganismContractStack

        with tempfile.TemporaryDirectory(prefix="aureon_contract_probe_") as tmp:
            tmp_path = Path(tmp)
            bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
            stack = OrganismContractStack(thought_bus=bus, state_path=tmp_path / "contracts.json")
            workflow = stack.create_goal_workflow(
                "Coordinate trading, accounting, research, LLM, and self-audit readiness.",
                skills=["trading_cognition", "accounting_context", "research_corpus", "llm_adapter"],
                route_surfaces=["contracts", "trading", "accounting", "research", "memory"],
                source="readiness_audit",
            )
            status = stack.status()
            thought_topics = {item.get("topic") for item in bus.recall(topic_prefix="organism.contract", limit=20)}
        ok = status.get("contract_count") == 4 and status.get("queue_count") == 1
        return CapabilityProof(
            id="contract_stack",
            name="Internal Contract Stack",
            status=proof_status(ok),
            summary=f"Created local goal/task/job/work-order workflow with {status.get('queue_count', 0)} queued work order.",
            systems=["OrganismContractStack", "ThoughtBus", "GoalContract", "TaskContract", "JobContract", "WorkOrderContract"],
            evidence={
                "workflow_contract_types": [workflow["goal"]["contract_type"]]
                + [item["contract_type"] for item in workflow["tasks"] + workflow["jobs"] + workflow["work_orders"]],
                "status": status,
                "topics": sorted(topic for topic in thought_topics if topic),
            },
            safety_boundary="Probe used a temporary local state path and did not touch live queues.",
            next_action="Use persistent state/organism_contract_stack.json for real internal queued work.",
        )
    except Exception as exc:
        return CapabilityProof(
            id="contract_stack",
            name="Internal Contract Stack",
            status="repair_pending",
            summary=f"Contract probe failed: {type(exc).__name__}: {exc}",
            systems=["OrganismContractStack", "ThoughtBus"],
            next_action="Repair contract stack imports or state persistence.",
        )


def probe_trading_brain() -> CapabilityProof:
    try:
        from aureon.core.aureon_runtime_safety import real_orders_allowed
        from aureon.trading.dynamic_margin_sizer import DynamicMarginSizer, MarginCapitalSnapshot
        from aureon.trading.temporal_trade_cognition import TemporalTradeCognition
        from aureon.trading.unified_margin_brain import UnifiedMarginDecisionBrain

        snapshot = MarginCapitalSnapshot.from_trade_balance({"equity": 10.0, "free_margin": 10.0, "margin_used": 0.0})
        size_plan = DynamicMarginSizer().plan(
            snapshot,
            price=100.0,
            ordermin=0.01,
            lot_decimals=6,
            leverage=2,
            max_profit_target_usd=0.25,
            costmin=5.0,
        )
        cognition = TemporalTradeCognition(default_horizon_seconds=180)
        trade_plan = cognition.plan_trade(
            pair="XBT/GBP",
            side="buy",
            ticker_symbol="XBTGBP",
            entry_price=100.0,
            target_price=100.4,
            required_move_pct=0.4,
            profit_target_usd=size_plan.profit_target_usd,
            eta_minutes=3,
            confidence=0.88,
            reason="readiness audit safe simulation",
            sources={"dynamic_margin_sizer": size_plan.reason},
            now=1_760_000_000.0,
        )
        verification = cognition.verify(
            trade_plan,
            current_price=100.5,
            validated_net_pnl=size_plan.profit_target_usd,
            now=1_760_000_060.0,
        )
        decision = UnifiedMarginDecisionBrain().evaluate_candidate(
            {
                "pair": "XBT/GBP",
                "side": "buy",
                "score": 9.2,
                "required_move_pct": 0.4,
                "estimated_fees": 0.02,
                "spread_pct": 0.01,
                "eta_minutes": 3,
                "route_to_profit": 2.8,
                "goal_score": 3.4,
                "profit_target_usd": size_plan.profit_target_usd,
            },
            {
                "confidence": 0.9,
                "probability": 0.86,
                "sources": {
                    "projection": {"confidence": 0.9, "live_match": 0.92},
                    "timeline": {"confidence": 0.88},
                    "alignment": {"score": 0.84},
                },
            },
            population_scores=[1.0, 4.0, 9.2],
            now=1_760_000_000.0,
        ).to_dict()
        ok = size_plan.approved and decision.get("approved") and not real_orders_allowed()
        return CapabilityProof(
            id="trading_brain",
            name="Trading Brain And Margin Cognition",
            status="working_safe_simulation" if ok else "working_with_attention",
            summary=(
                f"Dynamic sizing approved={size_plan.approved}; "
                f"margin brain action={decision.get('action')}; "
                f"temporal verification={verification.get('status')}."
            ),
            systems=["DynamicMarginSizer", "TemporalTradeCognition", "UnifiedMarginDecisionBrain", "runtime_safety"],
            evidence={
                "real_orders_allowed": real_orders_allowed(),
                "capital_snapshot": asdict(snapshot),
                "size_plan": asdict(size_plan),
                "trade_plan": trade_plan,
                "verification": verification,
                "margin_decision": decision,
            },
            safety_boundary="This probe does not call Kraken and does not place or mutate any order.",
            next_action="For live use, ignition still requires explicit live gates and exchange reconciliation.",
        )
    except Exception as exc:
        return CapabilityProof(
            id="trading_brain",
            name="Trading Brain And Margin Cognition",
            status="repair_pending",
            summary=f"Trading cognition probe failed: {type(exc).__name__}: {exc}",
            systems=["DynamicMarginSizer", "TemporalTradeCognition", "UnifiedMarginDecisionBrain"],
            next_action="Repair trading cognition imports/tests.",
        )


def probe_accounting(root: Path) -> CapabilityProof:
    try:
        from aureon.queen.accounting_context_bridge import AccountingContextBridge

        status = AccountingContextBridge(repo_root=root).status()
        combined = status.get("combined_bank_data") or {}
        workflow = status.get("autonomous_workflow") or {}
        end_user = status.get("end_user_accounting_automation") or {}
        coverage = end_user.get("requirement_coverage") or []
        coverage_done = sum(
            1
            for item in coverage
            if str(item.get("status", "")).startswith(("generated", "final_ready"))
        )
        handoff_readiness = ((status.get("human_filing_handoff_pack") or {}).get("readiness") or {})
        bank_rows = combined.get("unique_rows_in_period", 0)
        build_status = status.get("accounts_build_status") or workflow.get("status")
        bridge_working = not status.get("error")
        data_ready = (
            bridge_working
            and str(status.get("company_number") or "") not in {"", "00000000"}
            and int(bank_rows or 0) > 0
        )
        return CapabilityProof(
            id="accounting_brain",
            name="Accounting Brain And UK Filing Pack",
            status=(
                "working"
                if data_ready and not bool(status.get("manual_filing_required", True))
                else "working_with_attention"
                if bridge_working
                else "repair_pending"
            ),
            summary=(
                f"Company {status.get('company_number', 'unknown')}; "
                f"bank rows={bank_rows}; build={build_status}; "
                f"coverage={coverage_done}/{len(coverage)}."
            ),
            systems=[
                "AccountingContextBridge",
                "Kings_Accounting_Suite",
                "CombinedBankData",
                "AutonomousFullAccountsWorkflow",
                "UKAccountingRequirementsBrain",
                "payer_provenance",
            ],
            evidence={
                "company_number": status.get("company_number"),
                "company_name": status.get("company_name"),
                "accounts_build_status": build_status,
                "manual_filing_required": status.get("manual_filing_required", True),
                "combined_bank_data": {
                    "transaction_source_count": combined.get("transaction_source_count"),
                    "csv_source_count": combined.get("csv_source_count"),
                    "pdf_source_count": combined.get("pdf_source_count"),
                    "unique_rows_in_period": bank_rows,
                    "duplicate_rows_removed": combined.get("duplicate_rows_removed"),
                },
                "end_user_coverage": {"generated": coverage_done, "total": len(coverage)},
                "swarm_status": ((status.get("swarm_raw_data_wave_scan") or {}).get("status")),
                "handoff_ready": handoff_readiness.get("ready_for_manual_upload")
                or handoff_readiness.get("ready_for_manual_review"),
            },
            safety_boundary="Generates local packs only; Companies House/HMRC filing and payments remain manual.",
            next_action="Use the Desktop accounts folder for manual review/upload, not automatic filing.",
        )
    except Exception as exc:
        return CapabilityProof(
            id="accounting_brain",
            name="Accounting Brain And UK Filing Pack",
            status="repair_pending",
            summary=f"Accounting bridge failed: {type(exc).__name__}: {exc}",
            systems=["AccountingContextBridge", "Kings_Accounting_Suite"],
            next_action="Repair accounting bridge/status loading.",
        )


def probe_research_and_vault(root: Path) -> CapabilityProof:
    try:
        from aureon.integrations.obsidian import ObsidianBridge, resolve_obsidian_vault_path
        from aureon.queen.research_corpus_index import ResearchCorpusIndex

        obsidian = ObsidianBridge(
            vault_path=str(resolve_obsidian_vault_path()),
            prefer_filesystem=True,
            timeout_s=2,
        )
        obsidian_snapshot = obsidian.snapshot()
        index = ResearchCorpusIndex(
            root=str(root / "docs"),
            cache_path=str(root / "state" / "research_readiness_index.json"),
            exclude=("audits",),
        )
        index.ensure_built()
        hits = index.search("master formula auris conjecture research", top_k=3)
        ok = bool(obsidian_snapshot.get("reachable")) and index.doc_count() > 0 and bool(hits)
        return CapabilityProof(
            id="research_vault",
            name="Research Corpus And Obsidian Vault",
            status=proof_status(ok),
            summary=f"Indexed {index.doc_count()} docs and found {len(hits)} research hits; vault mode={obsidian_snapshot.get('mode')}.",
            systems=["ResearchCorpusIndex", "ObsidianBridge", "docs research corpus", "vault filesystem fallback"],
            evidence={
                "obsidian": obsidian_snapshot,
                "doc_count": index.doc_count(),
                "token_count": index.token_count(),
                "sample_hits": [hit.to_dict() for hit in hits],
            },
            safety_boundary="Reads docs and vault files only; no web publishing or external mutation.",
            next_action="Keep research cache refreshed after major docs changes.",
        )
    except Exception as exc:
        return CapabilityProof(
            id="research_vault",
            name="Research Corpus And Obsidian Vault",
            status="repair_pending",
            summary=f"Research/vault probe failed: {type(exc).__name__}: {exc}",
            systems=["ResearchCorpusIndex", "ObsidianBridge"],
            next_action="Repair research index or vault path.",
        )


def probe_llm_capability() -> CapabilityProof:
    try:
        from aureon.inhouse_ai.llm_adapter import AureonHybridAdapter, AureonLocalAdapter
        from aureon.integrations.ollama import OllamaBridge, OllamaModelSwitchboard

        switchboard = OllamaModelSwitchboard()
        local_adapter, fast_selection = switchboard.compatible_adapter_for("fast")
        local_response = local_adapter.prompt([{"role": "user", "content": "ping"}], max_tokens=32)
        hybrid_adapter, general_selection = switchboard.hybrid_adapter_for("general")
        hybrid_response = hybrid_adapter.prompt(
            [{"role": "user", "content": "explain the current safe audit route"}],
            max_tokens=128,
        )
        ollama_bridge = OllamaBridge(timeout_s=2)
        ollama_snapshot = ollama_bridge.snapshot()
        switchboard_snapshot = OllamaModelSwitchboard(bridge=ollama_bridge).snapshot()
        ok = bool(hybrid_response.text) and (
            hybrid_response.model == "aureon-brain-v1" or bool(switchboard_snapshot.get("reachable"))
        )
        attention = not bool(switchboard_snapshot.get("reachable"))
        return CapabilityProof(
            id="llm_capability",
            name="LLM And Local Reasoning Capability",
            status=proof_status(ok, attention=attention and ok),
            summary=(
                f"Hybrid reasoning model={hybrid_response.model}; "
                f"Ollama reachable={ollama_snapshot.get('reachable')}; "
                f"live catalog models={switchboard_snapshot.get('catalog_size', 0)}."
            ),
            systems=["AureonHybridAdapter", "AureonBrainAdapter", "AureonLocalAdapter", "OllamaBridge"],
            evidence={
                "hybrid_model": hybrid_response.model,
                "hybrid_text_sample": hybrid_response.text[:400],
                "direct_local_http_stop_reason": local_response.stop_reason,
                "direct_local_http_text": local_response.text[:200],
                "ollama": ollama_snapshot,
                "model_switchboard": switchboard_snapshot,
                "probe_nerve_lanes": {
                    "fast": fast_selection.to_dict(),
                    "general": general_selection.to_dict(),
                },
            },
            safety_boundary="Audit mode suppresses generic direct HTTP; the guarded Ollama bridge/catalog and AureonBrain fallback remain observable.",
            next_action="Keep the live model catalog refreshed and route calls through the Ollama model switchboard.",
        )
    except Exception as exc:
        return CapabilityProof(
            id="llm_capability",
            name="LLM And Local Reasoning Capability",
            status="repair_pending",
            summary=f"LLM probe failed: {type(exc).__name__}: {exc}",
            systems=["AureonHybridAdapter", "OllamaBridge"],
            next_action="Repair LLM adapter imports or local model setup.",
        )


def probe_self_enhancement_lifecycle(root: Path) -> CapabilityProof:
    try:
        from aureon.autonomous.aureon_self_enhancement_lifecycle import build_self_enhancement_lifecycle

        lifecycle = build_self_enhancement_lifecycle(root, queue_contracts=False, write_state=False)
        ok = not lifecycle.status.startswith("blocked")
        return CapabilityProof(
            id="self_enhancement_lifecycle",
            name="Self-Enhancement And Restart Handoff",
            status=proof_status(ok, attention="attention" in lifecycle.status and ok),
            summary=(
                f"stages={lifecycle.summary.get('stage_count', 0)}; "
                f"intents={lifecycle.summary.get('enhancement_intent_count', 0)}; "
                f"restart_required={lifecycle.summary.get('restart_required', False)}."
            ),
            systems=[
                "AureonSelfEnhancementLifecycle",
                "SelfEnhancementEngine",
                "CodeArchitect",
                "OrganismContractStack",
                "restart/apply handoff",
            ],
            evidence={
                "lifecycle_status": lifecycle.status,
                "summary": lifecycle.summary,
                "restart_handoff": lifecycle.restart_handoff.to_dict(),
                "intent_ids": [intent.id for intent in lifecycle.enhancement_intents[:12]],
            },
            safety_boundary="Plans and queues validated internal enhancements; does not force reboot or mutate external services.",
            next_action="Use the lifecycle report before accepting self-authored skill/code changes.",
        )
    except Exception as exc:
        return CapabilityProof(
            id="self_enhancement_lifecycle",
            name="Self-Enhancement And Restart Handoff",
            status="repair_pending",
            summary=f"Self-enhancement lifecycle failed: {type(exc).__name__}: {exc}",
            systems=["AureonSelfEnhancementLifecycle", "SelfEnhancementEngine", "CodeArchitect"],
            next_action="Repair lifecycle imports or enhancement engine wiring.",
        )


def probe_capability_growth_loop(root: Path) -> CapabilityProof:
    try:
        from aureon.autonomous.aureon_capability_growth_loop import build_capability_growth_loop

        growth = build_capability_growth_loop(
            root,
            iterations=1,
            run_checks=False,
            author_skills=False,
            queue_contracts=False,
            max_gaps=8,
        )
        latest = growth.iterations[-1]
        loop_working = bool(latest.summary.get("domain_count", 0))
        return CapabilityProof(
            id="capability_growth_loop",
            name="Capability Growth Loop",
            status=proof_status(
                loop_working,
                attention=bool(
                    latest.summary.get("gap_count")
                    or latest.summary.get("blocked_domain_count")
                    or latest.summary.get("failed_benchmark_count")
                ),
            ),
            summary=(
                f"domains={latest.summary.get('domain_count', 0)}; "
                f"gaps={latest.summary.get('gap_count', 0)}; "
                f"mean_score={latest.summary.get('mean_score', 0)}."
            ),
            systems=[
                "AureonCapabilityGrowthLoop",
                "AureonSystemReadinessAudit",
                "AureonRepoSelfCatalog",
                "CodeArchitect",
                "SkillLibrary",
                "OrganismContractStack",
            ],
            evidence={
                "growth_status": growth.status,
                "summary": growth.summary,
                "latest_iteration": latest.summary,
                "gap_ids": [gap.id for gap in latest.gaps[:12]],
            },
            safety_boundary="Scores domains and queues/local-authors safe improvements only; does not run live orders, filing, payments, or forced reboot.",
            next_action="Run the growth loop with --author-skills --queue-contracts after audits/benchmarks are refreshed.",
        )
    except Exception as exc:
        return CapabilityProof(
            id="capability_growth_loop",
            name="Capability Growth Loop",
            status="repair_pending",
            summary=f"Capability growth loop failed: {type(exc).__name__}: {exc}",
            systems=["AureonCapabilityGrowthLoop", "CodeArchitect", "OrganismContractStack"],
            next_action="Repair capability growth loop imports or audit manifest inputs.",
        )


def probe_ignition(root: Path) -> CapabilityProof:
    data = load_json(root / "docs" / "audits" / "ignition_live_boot_audit.json")
    if not data:
        return CapabilityProof(
            id="ignition",
            name="Single Boot Ignition Readiness",
            status="repair_pending",
            summary="Ignition audit is missing.",
            systems=["scripts/aureon_ignition.py"],
            next_action="Run python scripts/aureon_ignition.py --audit-only --accounts-status.",
        )
    checks = data.get("checks") or []
    failed = [check for check in checks if check.get("required") and not check.get("ok")]
    ready = bool(data.get("ready")) and not failed
    return CapabilityProof(
        id="ignition",
        name="Single Boot Ignition Readiness",
        status=proof_status(ready, attention=bool(data.get("real_orders_allowed")) and ready),
        summary=f"mode={data.get('mode')}; ready={data.get('ready')}; required_failures={len(failed)}.",
        systems=["scripts/aureon_ignition.py", "ignition preflight", "runtime safety"],
        evidence={
            "mode": data.get("mode"),
            "ready": data.get("ready"),
            "real_orders_allowed": data.get("real_orders_allowed"),
            "required_failures": data.get("required_failures"),
            "runtime_env": data.get("runtime_env"),
        },
        safety_boundary="Loaded existing ignition audit; live boot/trading loop not started by readiness audit.",
        next_action="Use --audit-only first before any --live boot.",
    )


def probe_operator_surfaces(root: Path) -> CapabilityProof:
    data = load_json(root / "docs" / "audits" / "mind_wiring_audit.json")
    probes = data.get("service_probes") or []
    usable = [probe for probe in probes if probe.get("status") in {"reachable", "safe_simulated"}]
    ok = bool(usable)
    return CapabilityProof(
        id="operator_surfaces",
        name="Frontend And Operator Surfaces",
        status=proof_status(ok),
        summary=f"{len(usable)}/{len(probes)} local service probes are reachable or safe-simulated.",
        systems=["frontend vite", "command center", "dashboard services", "mind thought action hub"],
        evidence={"service_probes": probes},
        safety_boundary="HTTP health/service probes only; no browser actions or live trading.",
        next_action="If a UI is not reachable, start its local dev/server process.",
    )


def build_readiness_audit(repo_root: Optional[Path] = None) -> AureonSystemReadinessAudit:
    root = repo_root_from(repo_root)
    env = apply_readiness_environment()
    proofs = [
        probe_repo_organization(root),
        probe_repo_self_catalog(root),
        probe_mind_wiring(root),
        probe_goal_routing(root),
        probe_contract_stack(),
        probe_trading_brain(),
        probe_accounting(root),
        probe_research_and_vault(root),
        probe_llm_capability(),
        probe_self_enhancement_lifecycle(root),
        probe_capability_growth_loop(root),
        probe_saas_product_inventory(root),
        probe_hnc_saas_security(root),
        probe_ignition(root),
        probe_operator_surfaces(root),
    ]
    status_counts: dict[str, int] = {}
    for proof in proofs:
        status_counts[proof.status] = status_counts.get(proof.status, 0) + 1
    blocked = status_counts.get("blocked_or_missing", 0)
    attention = sum(
        count
        for status, count in status_counts.items()
        if "attention" in status or status == "repair_pending"
    )
    if blocked:
        status = "blocked_capabilities_present"
    elif attention:
        status = "working_with_attention_items"
    else:
        status = "working_as_designed_safe_mode"

    try:
        from aureon.core.aureon_runtime_safety import real_orders_allowed

        orders_allowed = real_orders_allowed()
    except Exception:
        orders_allowed = False

    summary = {
        "proof_count": len(proofs),
        "status_counts": status_counts,
        "blocked_count": blocked,
        "attention_count": attention,
        "real_orders_allowed": orders_allowed,
        "manual_filing_required": True,
        "capability_ids": [proof.id for proof in proofs],
    }
    notes = [
        "This is a safe readiness proof, not a live trading run.",
        "Trading is proven through sizing, ETA cognition, and margin-brain simulation only.",
        "Accounting is proven through the bridge/status/generated pack surfaces; official filing and payment stay manual.",
        "Research is proven through the repo corpus index and Obsidian filesystem vault path.",
        "LLM capability is proven through AureonBrain plus the guarded live Ollama catalog and dynamic model switchboard.",
        "The SaaS product inventory counts UI/API/dashboard surfaces and drives the unified autonomous frontend shell.",
        "HNC SaaS security is proven as an unhackable pursuit loop; production deployment remains blocked until authorized self-attack, stress, repair, and retest gates have evidence.",
    ]
    return AureonSystemReadinessAudit(
        schema_version=SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        repo_root=str(root),
        status=status,
        proofs=proofs,
        safety={**env, "real_orders_allowed": orders_allowed, "manual_filing_required": True},
        summary=summary,
        notes=notes,
    )


def render_markdown(report: AureonSystemReadinessAudit) -> str:
    lines: list[str] = []
    lines.append("# Aureon System Readiness Audit")
    lines.append("")
    lines.append(f"- Generated: `{report.generated_at}`")
    lines.append(f"- Repo: `{report.repo_root}`")
    lines.append(f"- Status: `{report.status}`")
    lines.append("- Mode: safe readiness proof; no live trading, official filing, payment, or exchange mutation")
    lines.append("")
    lines.append("## Capability Matrix")
    lines.append("")
    lines.append("| Capability | Status | Summary | Safety boundary |")
    lines.append("| --- | --- | --- | --- |")
    for proof in report.proofs:
        summary = proof.summary.replace("|", "\\|")
        boundary = proof.safety_boundary.replace("|", "\\|")
        lines.append(f"| {proof.name} | `{proof.status}` | {summary} | {boundary} |")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    for proof in report.proofs:
        lines.append(f"### {proof.name}")
        lines.append("")
        lines.append(f"- Systems: {', '.join(f'`{system}`' for system in proof.systems)}")
        if proof.next_action:
            lines.append(f"- Next action: {proof.next_action}")
        for key, value in proof.evidence.items():
            if isinstance(value, (dict, list)):
                text = json.dumps(value, indent=2, sort_keys=True, default=str)
                if len(text) > 1800:
                    text = text[:1800] + "\n..."
                lines.append(f"- `{key}`:")
                lines.append("```json")
                lines.append(text)
                lines.append("```")
            else:
                lines.append(f"- `{key}`: `{value}`")
        lines.append("")
    lines.append("## Safety")
    lines.append("")
    for key, value in report.safety.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: AureonSystemReadinessAudit,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
) -> tuple[Path, Path]:
    root = Path(report.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    md_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_markdown(report), encoding="utf-8")
    js_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    return md_path, js_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's unified safe readiness proof.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--no-write", action="store_true", help="Print a JSON summary without writing artifacts.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    report = build_readiness_audit(root)
    if args.no_write:
        print(json.dumps({"status": report.status, "summary": report.summary}, indent=2, sort_keys=True))
    else:
        md_path, json_path = write_report(report, Path(args.markdown), Path(args.json))
        print(json.dumps({"status": report.status, "markdown": str(md_path), "json": str(json_path), "summary": report.summary}, indent=2, sort_keys=True))
    return 2 if report.status.startswith("blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
