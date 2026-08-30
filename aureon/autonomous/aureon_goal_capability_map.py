"""Goal-to-capability map for Aureon's autonomous organism.

This module gives the runtime a compact rulebook for goal pursuit:

1. understand the current goal;
2. inventory available memory, tools, logic, and code systems;
3. route work through the safest capable subsystem;
4. observe the result and write memory before the next step.

It is intentionally descriptive. It does not execute tools, mutate exchanges,
or edit code. Execution remains in the existing safe systems.
"""

from __future__ import annotations

from aureon.core.aureon_baton_link import link_system as _baton_link

_baton_link(__name__)

import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from aureon.core.aureon_runtime_safety import real_orders_allowed


DIRECTIVE_VERSION = "goal-capability-v1"

GOAL_LOOP = (
    "understand_goal",
    "recall_obsidian_memory",
    "inspect_current_state",
    "inventory_capabilities",
    "create_goal_contract",
    "choose_safest_route",
    "decompose_to_task_contracts",
    "use_relevant_systems",
    "queue_work_orders",
    "publish_thoughtbus_intent",
    "observe_result",
    "write_memory",
    "ask_next_question",
)

SAFETY_RULES = (
    "Never place live orders from the self-questioning loop.",
    "Never mutate exchange state unless explicit live-trading gates are enabled and a human-approved trading path owns the action.",
    "Never expose or overwrite secrets, API keys, exchange state, portfolio state, trade logs, or local machine state.",
    "Prefer audit, simulation, read-only inspection, Obsidian memory, and ThoughtBus publication for autonomous reasoning.",
    "Direct code changes must go through the repo/code-control path, not spontaneous model output.",
    "Accounting goals may generate final-ready manual filing packs on demand, but Companies House, HMRC, tax, and penalty filing/payment remain manual.",
    "Azyra desktop operation must use the AzyraOperatorBridge and SafeDesktopControl gates; live clicks, typing, submit keys, and window-close hotkeys require explicit local enablement.",
    "SaaS security goals must pursue unhackable as an internal benchmark loop through authorized self-attack, stress tests, repair, retest, and release gates.",
)

ROUTE_SURFACES = {
    "memory": [
        "ObsidianBridge",
        "state/self_questioning_ai_cycles.jsonl",
        "ThoughtBus recall",
    ],
    "reasoning": [
        "OllamaBridge",
        "mind wiring audit",
        "self-check scanner",
        "cognition pipeline",
        "organism spine",
    ],
    "self_catalog": [
        "AureonRepoSelfCatalog",
        "file-by-file role labels",
        "docs/audits/aureon_repo_self_catalog.json",
        "docs/audits/aureon_repo_self_catalog.csv",
        "Obsidian repo self-catalog note",
        "per-file LLM context without secret contents",
    ],
    "capability_growth": [
        "AureonCapabilityGrowthLoop",
        "audit-benchmark-fix-retest-repeat cycle",
        "domain capability scoring",
        "safe benchmark checks",
        "SkillLibrary improvement authoring",
        "OrganismContractStack improvement queues",
        "Obsidian capability-growth memory note",
    ],
    "coordination": [
        "ThoughtBus",
        "OrganismContractStack",
        "authoring.research",
        "autonomy.goal.directive",
        "autonomy.self_question.*",
    ],
    "contracts": [
        "OrganismContractStack",
        "GoalContract",
        "SkillContract",
        "TaskContract",
        "JobContract",
        "WorkOrderContract",
        "organism.contract.* ThoughtBus topics",
        "persistent local work-order queue",
    ],
    "tools": [
        "ToolRegistry built-ins",
        "VM control tool definitions",
        "Azyra operator tool definitions",
        "Office logistics/admin tool definitions",
        "voice intent routes",
    ],
    "office_admin": [
        "logistics_admin_capability_matrix",
        "logistics_admin_cognitive_cycle",
        "logistics_admin_autonomous_job_tick",
        "logistics_office_solo_cycle",
        "logistics_office_workweek_monitor_tick",
        "logistics_office_workweek_dispatch_tick",
        "logistics_office_self_audit",
        "logistics_operations_readiness_audit",
        "desktop_email_create_job/validate/run queue",
        "spreadsheet summariser and office queue builder",
        "Azyra operator bridge for gated WMS/ERP live record updates",
    ],
    "azyra_operator": [
        "AzyraClient configurable API bridge",
        "AzyraOperatorBridge local desktop bridge",
        "azyra_operator_* ToolRegistry bindings",
        "AzyraOperationsKnowledgeBase module map and task planner",
        "Azyra procedure catalog and validator",
        "Azyra calibration session recorder",
        "Azyra email/message intake planner",
        "Azyra Companion process/window probe",
        "SafeDesktopControl dry-run/live gates",
        "operator screenshot/focus/mouse/keyboard actions",
        "submit-key and window-close env guards",
        "task specs across CRM, Customs, Forwarding, Freight, Transport, Financials, and WMS",
    ],
    "trading": [
        "dynamic margin sizer",
        "temporal trade cognition",
        "unified margin brain",
        "Kraken margin decision path",
    ],
    "accounting": [
        "AccountingContextBridge",
        "AccountingSystemRegistry",
        "CompanyRawDataIntake",
        "CombinedBankData",
        "AutonomousFullAccountsWorkflow",
        "Kings_Accounting_Suite",
        "HNCGateway",
        "KingLedger",
        "KingAccounting",
        "HNC reports/export/tax/VAT/CIS engines",
        "company compliance audit",
        "final-ready accounts pack generator",
        "accounting evidence authoring",
        "petty-cash voucher templates",
        "receipt and invoice evidence requests",
        "UK accounting requirements brain",
        "accountant self-question checklist",
        "manual Companies House/HMRC filing boundary",
    ],
    "research": [
        "ResearchCorpusIndex",
        "Queen meaning resolver research context",
        "docs/**/*.md corpus",
        "docs/research index",
        "ObsidianBridge",
        "vault memory search",
        "ThoughtBus research intents",
    ],
    "self_enhancement": [
        "AureonCapabilityGrowthLoop",
        "AureonSystemReadinessAudit",
        "AureonRepoSelfCatalog",
        "RepoWideOrganizationAudit",
        "MindWiringAudit",
        "SelfQuestioningAI",
        "SelfEnhancementEngine",
        "CodeArchitect",
        "SkillValidator",
        "SkillLibrary",
        "OrganismContractStack",
        "restart/apply handoff",
    ],
    "saas_security": [
        "HNCSaaSSecurityArchitect",
        "HNCAuthorizedAttackLab",
        "HNC system inventory",
        "OWASP ASVS control matrix",
        "OWASP Top 10 threat mapping",
        "NIST zero-trust runtime model",
        "authorized self-attack benchmarks",
        "break-in simulation and stress-test loop",
        "historical defensive tactic memory",
        "tenant isolation contract",
        "LLM tool-governance release gates",
        "manual filing/payment and live-trading authority boundaries",
        "OrganismContractStack SaaS security work orders",
        "Obsidian SaaS security memory note",
    ],
    "saas_product_inventory": [
        "AureonSaaSSystemInventory",
        "AureonFrontendUnificationPlan",
        "React/Vite unified observation shell",
        "Supabase function inventory",
        "vault UI and legacy dashboard inventory",
        "generated accounting document surfaces",
        "frontend public manifest mirror",
        "canonical screens for trading, accounting, research, cognition, SaaS security, self-improvement, and admin",
    ],
    "code": [
        "safe code control",
        "repo task bridge",
        "cognitive authoring loop",
    ],
}

EXTERNAL_SKILL_ROUTES = (
    "news_search",
    "stock_price",
    "crypto_price",
    "paper_search",
)

TRADING_GOAL_WORDS = (
    "trade",
    "margin",
    "kraken",
    "position",
    "collateral",
    "profit",
    "slippage",
    "ticker",
)

CODE_GOAL_WORDS = (
    "code",
    "fix",
    "implement",
    "wire",
    "dependency",
    "test",
    "repo",
    "module",
)

MEMORY_GOAL_WORDS = (
    "remember",
    "obsidian",
    "vault",
    "note",
    "learn",
    "history",
)

CONTRACT_GOAL_WORDS = (
    "contract",
    "contracts",
    "task",
    "tasks",
    "job",
    "jobs",
    "queue",
    "queues",
    "work order",
    "work_order",
    "directive",
    "internal talk",
    "talk internal",
    "skills",
)

ACCOUNTING_GOAL_WORDS = (
    "account",
    "accounts",
    "accounting",
    "tax",
    "vat",
    "utr",
    "hmrc",
    "company house",
    "companies house",
    "ledger",
    "invoice",
    "receipt",
    "petty cash",
    "voucher",
    "evidence",
    "raw data",
    "end user",
    "accounts pack",
    "ct600",
    "corporation tax",
    "confirmation statement",
    "filing",
    "balance sheet",
    "trial balance",
    "statement",
    "penalty",
)

RESEARCH_GOAL_WORDS = (
    "research",
    "study",
    "paper",
    "papers",
    "corpus",
    "whitepaper",
    "evidence",
    "claim",
    "claims",
    "source",
    "sources",
    "investigate",
    "knowledge",
)

SELF_ENHANCEMENT_GOAL_WORDS = (
    "enhance",
    "enhancement",
    "enhancements",
    "improve",
    "improvement",
    "self improve",
    "self-improve",
    "learn",
    "learning",
    "reboot",
    "restart",
    "apply",
    "self repair",
    "self-repair",
    "self modify",
    "self-modify",
    "understand itself",
    "understands itself",
)

SELF_CATALOG_GOAL_WORDS = (
    "catalog",
    "catalogue",
    "categorise",
    "categorize",
    "label",
    "labels",
    "every file",
    "all files",
    "what it is",
    "what it does",
    "what files do",
    "file-by-file",
    "self map",
    "self-map",
    "self catalog",
    "self-catalog",
)

CAPABILITY_GROWTH_GOAL_WORDS = (
    "capability",
    "capabilities",
    "benchmark",
    "benchmarks",
    "test",
    "tests",
    "audit fix",
    "audit and fix",
    "retest",
    "repeat",
    "over and over",
    "continuous",
    "constantly",
    "improvement loop",
    "growth loop",
    "write its own improvements",
    "writes its own improvements",
    "advanced system logic",
    "all domains",
)

SAAS_SECURITY_GOAL_WORDS = (
    "saas",
    "software as a service",
    "unhackable",
    "secure",
    "security",
    "zero trust",
    "zero-trust",
    "tenant",
    "tenancy",
    "multi tenant",
    "multi-tenant",
    "asvs",
    "owasp",
    "rbac",
    "auth",
    "hardened",
    "hardening",
)

SAAS_PRODUCT_GOAL_WORDS = (
    "frontend",
    "front end",
    "ui",
    "user interface",
    "dashboard",
    "dashboards",
    "operator",
    "command surface",
    "observation",
    "cockpit",
    "unified app",
    "unified frontend",
    "saas",
    "saas inventory",
    "saas map",
    "saas product",
    "canonical screen",
)

AZYRA_OPERATOR_GOAL_WORDS = (
    "azyra",
    "azera",
    "azra",
    "azrra",
    "aureon use azyra",
    "human operator",
    "operator bridge",
    "companion",
    "warehouse erp",
    "erp operator",
)

OFFICE_ADMIN_GOAL_WORDS = (
    "admin",
    "administration",
    "administrator",
    "office",
    "workweek",
    "inbox",
    "email",
    "outlook",
    "spreadsheet",
    "excel",
    "data entry",
    "record update",
    "report",
    "reports",
    "reporting",
    "evidence pack",
    "customer service",
    "supplier",
    "warehouse administration",
    "high level admin",
    "fix the warehouse",
    "stock balance",
    "stock balances",
)


@dataclass
class GoalCapabilityMap:
    directive_version: str
    directive: str
    goal_loop: List[str]
    safety_rules: List[str]
    real_orders_allowed: bool
    audit_mode: bool
    route_surfaces: Dict[str, List[str]]
    tool_registry: Dict[str, Any]
    organism: Dict[str, Any]
    contract_capabilities: Dict[str, Any] = field(default_factory=dict)
    accounting_capabilities: Dict[str, Any] = field(default_factory=dict)
    recommended_routes: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def compact(self) -> Dict[str, Any]:
        return {
            "directive_version": self.directive_version,
            "directive": self.directive,
            "goal_loop": self.goal_loop,
            "safety_rules": self.safety_rules,
            "real_orders_allowed": self.real_orders_allowed,
            "audit_mode": self.audit_mode,
            "route_surfaces": self.route_surfaces,
            "tool_registry": {
                "count": self.tool_registry.get("count"),
                "builtin_tools": self.tool_registry.get("builtin_tools", [])[:10],
                "vm_tools": self.tool_registry.get("vm_tools", [])[:10],
                "azyra_operator_tools": self.tool_registry.get("azyra_operator_tools", [])[:10],
                "office_logistics_tools": self.tool_registry.get("office_logistics_tools", [])[:10],
                "external_skill_routes": self.tool_registry.get("external_skill_routes", []),
            },
            "organism": {
                "node_count": self.organism.get("node_count"),
                "domains": self.organism.get("domains", {}),
            },
            "contract_capabilities": {
                "contract_schema_version": self.contract_capabilities.get("contract_schema_version"),
                "contract_types": self.contract_capabilities.get("contract_types", []),
                "queue_count": self.contract_capabilities.get("queue_count", 0),
                "topics": self.contract_capabilities.get("topics", {}),
            },
            "accounting_capabilities": {
                "module_count": self.accounting_capabilities.get("module_count", 0),
                "artifact_count": self.accounting_capabilities.get("artifact_count", 0),
                "domain_counts": self.accounting_capabilities.get("domain_counts", {}),
                "combined_bank_data": self.accounting_capabilities.get("combined_bank_data", {}),
            },
            "recommended_routes": self.recommended_routes[:5],
            "errors": self.errors[:5],
        }


def build_goal_capability_map(
    repo_root: Optional[Path] = None,
    current_goal: str = "",
) -> GoalCapabilityMap:
    root = Path(repo_root or Path.cwd()).resolve()
    errors: List[str] = []
    return GoalCapabilityMap(
        directive_version=DIRECTIVE_VERSION,
        directive=(
            "For every goal, Aureon must consider and safely use all relevant "
            "available skills, tools, logic modules, code systems, memory, and "
            "ThoughtBus routes as one connected organism."
        ),
        goal_loop=list(GOAL_LOOP),
        safety_rules=list(SAFETY_RULES),
        real_orders_allowed=real_orders_allowed(),
        audit_mode=os.environ.get("AUREON_AUDIT_MODE", "0").strip() == "1",
        route_surfaces={key: list(value) for key, value in ROUTE_SURFACES.items()},
        tool_registry=_tool_registry_snapshot(errors),
        organism=_organism_snapshot(root, errors),
        contract_capabilities=_contract_capability_snapshot(root, errors),
        accounting_capabilities=_accounting_capability_snapshot(root, errors),
        recommended_routes=recommend_goal_routes(current_goal),
        errors=errors,
    )


def recommend_goal_routes(goal: str) -> List[Dict[str, Any]]:
    text = str(goal or "").lower()
    routes: List[Dict[str, Any]] = [
        {
            "route": "memory_and_state",
            "systems": ["ObsidianBridge", "ThoughtBus", "self_questioning_state"],
            "reason": "Every goal should start with memory recall and current state inspection.",
            "risk": "low",
        },
        {
            "route": "organism_wiring",
            "systems": ["mind_wiring_audit", "organism_spine", "self_check_scanner"],
            "reason": "Aureon should know which subsystems are available before selecting actions.",
            "risk": "low",
        },
    ]
    if any(word in text for word in CONTRACT_GOAL_WORDS):
        routes.append(
            {
                "route": "internal_contract_stack",
                "systems": [
                    "OrganismContractStack",
                    "GoalContract",
                    "TaskContract",
                    "JobContract",
                    "WorkOrderContract",
                    "ThoughtBus organism.contract.* topics",
                    "persistent local work-order queue",
                ],
                "reason": "Internal coordination goals need typed contracts, task/job decomposition, and queued work-order handoff.",
                "risk": "low",
            }
        )
    if any(word in text for word in TRADING_GOAL_WORDS):
        routes.append(
            {
                "route": "safe_trading_cognition",
                "systems": [
                    "dynamic_margin_sizer",
                    "temporal_trade_cognition",
                    "unified_margin_brain",
                    "Kraken margin decision path",
                ],
                "reason": "Trading goals require sizing, time reasoning, costs, slippage, and strict order gates.",
                "risk": "high",
                "requires_human": True,
            }
        )
    if any(word in text for word in ACCOUNTING_GOAL_WORDS):
        routes.append(
            {
                "route": "safe_accounting_context",
                "systems": [
                    "AccountingContextBridge",
                    "AccountingSystemRegistry",
                    "CombinedBankData",
                    "Kings_Accounting_Suite",
                    "HNCGateway",
                    "KingLedger",
                    "HNC reports/export/tax/VAT/CIS engines",
                    "company_house_tax_audit",
                    "generate_full_company_accounts",
                    "end_user_accounting_automation",
                    "accounting_evidence_authoring",
                    "uk_accounting_requirements_brain",
                    "accountant self-question checklist",
                    "vault accounting context",
                ],
                "reason": "Accounting goals require local evidence, UK tax/VAT/UTR requirement reasoning, final-ready accounts packs, compliance status, and manual filing boundaries.",
                "risk": "medium",
                "requires_human": True,
                "manual_filing_required": True,
            }
        )
    if any(word in text for word in RESEARCH_GOAL_WORDS):
        routes.append(
            {
                "route": "safe_research_corpus",
                "systems": [
                    "ResearchCorpusIndex",
                    "Queen meaning resolver research context",
                    "docs/**/*.md corpus",
                    "docs/research index",
                    "ObsidianBridge",
                    "ThoughtBus research intents",
                ],
                "reason": "Research goals should retrieve repo evidence, vault memory, and source-linked snippets before answering or writing new notes.",
                "risk": "low",
            }
        )
    if any(word in text for word in SELF_CATALOG_GOAL_WORDS):
        routes.append(
            {
                "route": "repo_self_catalog",
                "systems": [
                    "AureonRepoSelfCatalog",
                    "RepoWideOrganizationAudit",
                    "organism_spine",
                    "Obsidian repo self-catalog note",
                    "per-file LLM context",
                ],
                "reason": "Self-knowledge and categorisation goals need every project file labelled by role, subsystem, domain, safety flags, and vault/LLM context.",
                "risk": "low",
            }
        )
    if any(word in text for word in CAPABILITY_GROWTH_GOAL_WORDS):
        routes.append(
            {
                "route": "capability_growth_loop",
                "systems": [
                    "AureonCapabilityGrowthLoop",
                    "AureonSystemReadinessAudit",
                    "AureonRepoSelfCatalog",
                    "MindWiringAudit",
                    "CodeArchitect",
                    "SkillLibrary",
                    "SkillValidator",
                    "OrganismContractStack",
                    "pytest/compileall safe checks",
                    "Obsidian capability growth memory",
                ],
                "reason": "Capability-growth goals need the organism to audit, benchmark, score domains, detect gaps, author safe improvement skills, queue work, retest, and repeat.",
                "risk": "medium",
                "requires_validation": True,
            }
        )
    if any(word in text for word in SELF_ENHANCEMENT_GOAL_WORDS):
        routes.append(
            {
                "route": "safe_self_enhancement_lifecycle",
                "systems": [
                    "AureonCapabilityGrowthLoop",
                    "AureonSystemReadinessAudit",
                    "AureonRepoSelfCatalog",
                    "RepoWideOrganizationAudit",
                    "MindWiringAudit",
                    "SelfQuestioningAI",
                    "SelfEnhancementEngine",
                    "CodeArchitect",
                    "SkillValidator",
                    "SkillLibrary",
                    "OrganismContractStack",
                    "restart/apply handoff",
                ],
                "reason": "Self-improvement goals need evidence gathering, gap detection, validated skill/code authoring, contract queues, memory, and a controlled restart/apply handoff.",
                "risk": "medium",
                "requires_human": True,
                "restart_handoff_required": True,
            }
        )
    if any(word in text for word in SAAS_SECURITY_GOAL_WORDS):
        routes.append(
            {
                "route": "hnc_saas_security_architect",
                "systems": [
                    "HNCSaaSSecurityArchitect",
                    "HNCAuthorizedAttackLab",
                    "HNC system inventory",
                    "OrganismContractStack",
                    "AureonCapabilityGrowthLoop",
                    "AureonSystemReadinessAudit",
                    "OWASP ASVS",
                    "OWASP Top 10",
                    "NIST zero-trust model",
                ],
                "reason": "SaaS security goals require an HNC-led blueprint, historical defensive tactic memory, authorized self-attacks, tenant isolation, identity and policy controls, LLM/tool governance, release-blocking tests, and auditable implementation work orders.",
                "risk": "high",
                "requires_validation": True,
                "unhackable_internal_goal_active": True,
                "public_unhackable_claim_allowed": False,
                "authorized_self_attack_required": True,
            }
        )
    if any(word in text for word in SAAS_PRODUCT_GOAL_WORDS):
        routes.append(
            {
                "route": "saas_product_inventory",
                "systems": [
                    "AureonSaaSSystemInventory",
                    "AureonFrontendUnificationPlan",
                    "React/Vite unified observation shell",
                    "Supabase function inventory",
                    "legacy dashboard transition map",
                    "frontend public manifest mirror",
                ],
                "reason": "Frontend/SaaS product goals need every UI, API, dashboard, generated output, and safety boundary counted before the canonical observation shell is wired.",
                "risk": "medium",
                "requires_validation": True,
            }
        )
    if any(word in text for word in OFFICE_ADMIN_GOAL_WORDS):
        routes.append(
            {
                "route": "office_admin_workweek",
                "systems": [
                    "build_logistics_admin_capability_matrix",
                    "run_logistics_admin_cognitive_cycle",
                    "run_logistics_admin_autonomous_job_tick",
                    "run_logistics_office_solo_cycle",
                    "run_workweek_monitor_tick",
                    "run_workweek_dispatch_tick",
                    "logistics_office_self_audit",
                    "logistics_operations_readiness_audit",
                    "desktop_email_create_job/validate/run queue",
                    "register_office_logistics_tools",
                ],
                "reason": "Administration goals need workweek observation, inbox/file intake, spreadsheet review, queue dispatch, email job control, self-audit, evidence packs, and controlled live-system updates through explicit gates.",
                "risk": "medium",
                "requires_validation": True,
                "live_mutation_gates": [
                    "AUREON_ADMIN_LIVE_MODE=true",
                    "AZYRA_OPERATOR_ALLOW_INPUT=true for Azyra typing",
                    "AZYRA_OPERATOR_ALLOW_SUBMIT=true for submit keys",
                    "AUREON_DESKTOP_EMAIL_ALLOW_SEND=true for Outlook sends",
                    "AUREON_EXCEL_WRITE_ALLOW=true for workbook writes",
                ],
            }
        )
    if any(word in text for word in AZYRA_OPERATOR_GOAL_WORDS):
        routes.append(
            {
                "route": "azyra_human_operator",
                "systems": [
                    "AzyraClient",
                    "AzyraOperatorBridge",
                    "AzyraOperationsKnowledgeBase",
                    "Azyra procedure catalog",
                    "Azyra calibration recorder",
                    "Azyra email/message intake planner",
                    "register_azyra_operator_tools",
                    "SafeDesktopControl",
                    "ToolRegistry",
                ],
                "reason": "Azyra goals need module/task requirements, calibrated screen procedures, observation, and logged-in desktop operation through named tools with dry-run and live-input gates.",
                "risk": "high",
                "requires_human": True,
                "requires_validation": True,
                "live_input_env_required": "AZYRA_OPERATOR_ALLOW_INPUT=true",
                "submit_env_required": "AZYRA_OPERATOR_ALLOW_SUBMIT=true",
            }
        )
    if any(word in text for word in CODE_GOAL_WORDS):
        routes.append(
            {
                "route": "safe_code_repair",
                "systems": ["repo task bridge", "safe code control", "cognitive authoring loop"],
                "reason": "Code goals should become auditable proposals, tests, and safe patches.",
                "risk": "medium",
            }
        )
    if any(word in text for word in MEMORY_GOAL_WORDS):
        routes.append(
            {
                "route": "vault_memory",
                "systems": ["ObsidianBridge", "ObsidianSink", "self_questioning_ai index"],
                "reason": "Memory goals should be written to the vault and recalled in future cycles.",
                "risk": "low",
            }
        )
    return routes


def _tool_registry_snapshot(errors: List[str]) -> Dict[str, Any]:
    builtin_tools: List[str] = []
    vm_tools: List[str] = []
    azyra_operator_tools: List[str] = []
    office_logistics_tools: List[str] = []
    try:
        from aureon.inhouse_ai.tool_registry import ToolRegistry

        builtin_tools = ToolRegistry(include_builtins=True).names()
    except Exception as exc:
        errors.append(f"tool registry snapshot failed: {exc}")

    try:
        from aureon.autonomous.vm_control.tools import VM_TOOL_NAMES

        vm_tools = list(VM_TOOL_NAMES)
    except Exception as exc:
        errors.append(f"vm tool snapshot failed: {exc}")

    try:
        from aureon.integrations.azyra.tools import AZYRA_OPERATOR_TOOL_NAMES

        azyra_operator_tools = list(AZYRA_OPERATOR_TOOL_NAMES)
    except Exception as exc:
        errors.append(f"azyra operator tool snapshot failed: {exc}")

    try:
        from aureon.integrations.office.tools import OFFICE_LOGISTICS_TOOL_NAMES

        office_logistics_tools = list(OFFICE_LOGISTICS_TOOL_NAMES)
    except Exception as exc:
        errors.append(f"office logistics tool snapshot failed: {exc}")

    return {
        "count": len(builtin_tools)
        + len(vm_tools)
        + len(azyra_operator_tools)
        + len(office_logistics_tools)
        + len(EXTERNAL_SKILL_ROUTES),
        "builtin_tools": builtin_tools,
        "vm_tools": vm_tools,
        "azyra_operator_tools": azyra_operator_tools,
        "office_logistics_tools": office_logistics_tools,
        "external_skill_routes": list(EXTERNAL_SKILL_ROUTES),
    }


def _organism_snapshot(root: Path, errors: List[str]) -> Dict[str, Any]:
    try:
        from aureon.core.aureon_organism_spine import build_organism_manifest

        manifest = build_organism_manifest(repo_root=root)
        domains: Dict[str, int] = {}
        for node in manifest.nodes:
            domains[node.domain] = domains.get(node.domain, 0) + 1
        return {
            "node_count": len(manifest.nodes),
            "domains": dict(sorted(domains.items())),
        }
    except Exception as exc:
        errors.append(f"organism snapshot failed: {exc}")
        return {"node_count": 0, "domains": {}}


def _contract_capability_snapshot(root: Path, errors: List[str]) -> Dict[str, Any]:
    try:
        from aureon.core.organism_contracts import build_contract_stack_snapshot

        return build_contract_stack_snapshot(root)
    except Exception as exc:
        errors.append(f"contract stack snapshot failed: {exc}")
        return {
            "contract_schema_version": "",
            "contract_types": [],
            "queue_count": 0,
            "topics": {},
        }


def _accounting_capability_snapshot(root: Path, errors: List[str]) -> Dict[str, Any]:
    try:
        from Kings_Accounting_Suite.tools.accounting_system_registry import (
            build_accounting_system_registry,
        )

        registry = build_accounting_system_registry(root)
        return registry.compact(max_entries=8, max_artifacts=8)
    except Exception as exc:
        errors.append(f"accounting capability snapshot failed: {exc}")
        return {
            "module_count": 0,
            "artifact_count": 0,
            "domain_counts": {},
            "combined_bank_data": {},
        }


__all__ = [
    "DIRECTIVE_VERSION",
    "GOAL_LOOP",
    "ROUTE_SURFACES",
    "SAFETY_RULES",
    "GoalCapabilityMap",
    "build_goal_capability_map",
    "recommend_goal_routes",
]
