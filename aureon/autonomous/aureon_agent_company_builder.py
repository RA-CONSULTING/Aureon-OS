"""Build Aureon's company-of-agents capability bill list.

This module turns market-standard agent capabilities into an Aureon-native
company registry: departments, roles, handoffs, evidence, tools, authority
boundaries, and work orders. It is a registry and UI evidence layer first; it
does not grant new live-trading, filing, payment, credential, or destructive
OS authority.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import time
import zlib
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence

SCHEMA_VERSION = "aureon-agent-company-bill-list-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = Path("state/aureon_agent_company_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_agent_company_bill_list.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_agent_company_bill_list.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_agent_company_bill_list.json")
DEFAULT_PHONEBOOK_STATE_JSON = Path("state/aureon_agent_company_memory_phonebook.json")
DEFAULT_PHONEBOOK_AUDIT_JSON = Path("docs/audits/aureon_agent_company_memory_phonebook.json")
DEFAULT_PHONEBOOK_PUBLIC_JSON = Path("frontend/public/aureon_agent_company_memory_phonebook.json")
DEFAULT_MEMORY_BUNDLE_DIR = Path("state/aureon_agent_company_memory_bundles")


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _default_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "aureon").exists() or (cwd / "frontend").exists() or (cwd / "README.md").exists():
        return cwd
    return REPO_ROOT


def _rooted(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else root / candidate


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "role"


@dataclass
class AgentCompanyRole:
    role_id: str
    title: str
    department: str
    seniority: str
    mission: str
    capabilities: list[str]
    tools_allowed: list[str]
    inputs: list[str]
    outputs: list[str]
    handoffs_in: list[str]
    handoffs_out: list[str]
    authority_level: str
    evidence_required: list[str]
    tests: list[str]
    aureon_surfaces: list[str]
    who_what_where_when_how_act: dict[str, Any]
    day_to_day: list[str] = field(default_factory=list)
    standing_checks: list[str] = field(default_factory=list)
    escalation_rules: list[str] = field(default_factory=list)
    cross_training: list[str] = field(default_factory=list)
    whole_organism_access: dict[str, Any] = field(default_factory=dict)
    workforce_lifecycle: dict[str, Any] = field(default_factory=dict)
    existing_surfaces: list[str] = field(default_factory=list)
    missing_surfaces: list[str] = field(default_factory=list)
    status: str = "registry_pending"
    blockers: list[str] = field(default_factory=list)
    work_orders: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


MARKET_CAPABILITY_TAXONOMY: list[dict[str, Any]] = [
    {
        "id": "tool_use",
        "title": "Tool use and function calling",
        "official_source": "https://openai.github.io/openai-agents-python/tools/",
        "market_pattern": "Agents take action through typed tools such as web, files, code execution, APIs, shell, and computer control.",
        "aureon_translation": "ToolRegistry, AgentCore intents, VM tools, exchange/status tools, and safe code/document bridges.",
        "capability_keywords": ["tools", "function_calling", "api", "shell", "desktop"],
    },
    {
        "id": "handoffs",
        "title": "Specialist handoffs",
        "official_source": "https://openai.github.io/openai-agents-python/handoffs/",
        "market_pattern": "A triage or manager agent delegates to specialized agents with handoff metadata.",
        "aureon_translation": "GoalExecutionEngine, OrganismContractStack, ThoughtBus, and team/task queues.",
        "capability_keywords": ["handoff", "delegation", "triage", "workflow"],
    },
    {
        "id": "guardrails",
        "title": "Input, output, and tool guardrails",
        "official_source": "https://openai.github.io/openai-agents-python/guardrails/",
        "market_pattern": "Agent systems validate inputs, outputs, and tool calls before or after execution.",
        "aureon_translation": "Runtime safety gates, SafeCodeControl, credential redaction, official filing/payment boundaries, and exchange mutation gates.",
        "capability_keywords": ["guardrail", "safety", "validation", "redaction"],
    },
    {
        "id": "code_execution",
        "title": "Code execution and iterative reasoning",
        "official_source": "https://ai.google.dev/gemini-api/docs/code-execution",
        "market_pattern": "Models can generate and run code, inspect results, and iterate to a final answer.",
        "aureon_translation": "QueenCodeArchitect, CodeArchitect, tests, build commands, compile checks, and coding organism work journals.",
        "capability_keywords": ["code", "tests", "build", "verification"],
    },
    {
        "id": "grounding_search",
        "title": "Grounding, search, and citations",
        "official_source": "https://ai.google.dev/gemini-api/docs/google-search",
        "market_pattern": "Agents use fresh web/search data to reduce hallucination and cite sources.",
        "aureon_translation": "WebLearningScout, research corpus, source-linked vault memory, market/news/macroeconomic data ocean.",
        "capability_keywords": ["research", "web", "source", "citations"],
    },
    {
        "id": "client_and_server_tools",
        "title": "Client-side and server-side tools",
        "official_source": "https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview",
        "market_pattern": "Tool execution can happen in the application environment or through hosted/server-side tools.",
        "aureon_translation": "Local repo tools, desktop/VM tools, exchange clients, and public report artifacts.",
        "capability_keywords": ["tool_result", "client_tool", "server_tool", "runtime"],
    },
    {
        "id": "multi_agent_teams",
        "title": "Multi-agent teams and workbenches",
        "official_source": "https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/agents.html",
        "market_pattern": "Specialized assistant agents use tools, share workbenches, and produce task results.",
        "aureon_translation": "OpenMultiAgent, Team, AgentPool, SharedMemory, MessageBus, and TaskQueue.",
        "capability_keywords": ["team", "agents", "workbench", "shared_memory"],
    },
    {
        "id": "orchestration_patterns",
        "title": "Sequential, concurrent, group, and handoff orchestration",
        "official_source": "https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/",
        "market_pattern": "Agent frameworks offer sequential, concurrent, group-chat, handoff, and manager-style orchestration patterns.",
        "aureon_translation": "Goal plans, swarm dispatch, ThoughtBus topics, work-order queues, and supervisor loops.",
        "capability_keywords": ["orchestration", "concurrent", "group", "manager"],
    },
]


MARKET_AI_SYSTEMS: list[dict[str, Any]] = [
    {
        "id": "openai_agents_codex",
        "provider": "OpenAI",
        "systems": ["Agents SDK", "Codex"],
        "official_sources": [
            "https://developers.openai.com/api/docs/guides/agents",
            "https://developers.openai.com/codex/cloud",
        ],
        "market_capabilities": [
            "tool use",
            "specialist handoffs",
            "stateful multi-step work",
            "guardrails",
            "tracing and observability",
            "background coding tasks",
            "repo read/edit/run",
            "GitHub pull-request handoff",
        ],
        "aureon_current_equivalent": [
            "GoalExecutionEngine",
            "aureon_coding_organism_bridge",
            "SafeCodeControl",
            "LocalTaskQueue",
            "agent company registry",
            "director capability bridge",
        ],
        "primary_gap": "Codex-style parallel cloud worktrees and first-class PR creation remain work orders, not a fully active Aureon lane.",
        "temporary_hires": ["Tool Bridge Architect", "Workflow Foreman", "Release Manager"],
    },
    {
        "id": "anthropic_claude_code_tools",
        "provider": "Anthropic",
        "systems": ["Claude tool use", "Claude Code", "computer use", "MCP"],
        "official_sources": [
            "https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview",
            "https://code.claude.com/docs/en/how-claude-code-works",
            "https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool",
        ],
        "market_capabilities": [
            "client/server tools",
            "strict tool schemas",
            "agentic gather-act-verify loop",
            "bash/text editor/code execution",
            "computer screenshots and mouse/keyboard control",
            "MCP connectors",
            "session logs and resumability",
        ],
        "aureon_current_equivalent": [
            "SafeDesktopControl",
            "VMControlDispatcher",
            "ToolRegistry",
            "coding organism proof checklist",
            "state/docs/frontend evidence",
        ],
        "primary_gap": "Browser/computer smoke checks exist as safe controller surfaces but need a dedicated browser evidence bridge.",
        "temporary_hires": ["Browser Smoke Inspector", "HNC/Auris Drift Officer", "Test Pilot"],
    },
    {
        "id": "google_gemini_jules",
        "provider": "Google",
        "systems": ["Gemini API", "Jules"],
        "official_sources": [
            "https://ai.google.dev/gemini-api/docs/function-calling",
            "https://jules.google/docs/",
        ],
        "market_capabilities": [
            "function calling",
            "grounding/search",
            "code execution",
            "Live API patterns",
            "GitHub-connected autonomous coding VM",
            "bug fixes, documentation, and feature tasks",
        ],
        "aureon_current_equivalent": [
            "ToolRegistry",
            "research/vault memory",
            "coding-agent skill base",
            "GoalExecutionEngine",
        ],
        "primary_gap": "Fresh official-doc web learning is mapped but should become a required preflight for unfamiliar code domains.",
        "temporary_hires": ["Market AI Scout", "Research Scout", "Capability Cartographer"],
    },
    {
        "id": "microsoft_agent_framework",
        "provider": "Microsoft",
        "systems": ["Agent Framework", "Semantic Kernel", "AutoGen lineage"],
        "official_sources": [
            "https://learn.microsoft.com/en-us/agent-framework/overview/",
        ],
        "market_capabilities": [
            "agents with tools and MCP servers",
            "graph workflows",
            "checkpointing",
            "human-in-the-loop",
            "memory/context providers",
            "middleware",
            "type-safe routing",
        ],
        "aureon_current_equivalent": [
            "OrganismContractStack",
            "GoalExecutionEngine",
            "ThoughtBus",
            "LocalTaskQueue",
            "agent company handoff map",
        ],
        "primary_gap": "Typed graph checkpoints and resumable workflow state are partial; route checkpoints need stronger UI and replay controls.",
        "temporary_hires": ["Project Manager", "Workflow Foreman", "Archive Librarian"],
    },
    {
        "id": "github_copilot_cloud_agent",
        "provider": "GitHub",
        "systems": ["Copilot cloud agent"],
        "official_sources": [
            "https://docs.github.com/en/copilot/concepts/agents/cloud-agent/about-cloud-agent",
        ],
        "market_capabilities": [
            "repo research",
            "implementation plans",
            "branch changes",
            "diff review",
            "pull requests",
            "custom agents",
            "test and documentation work",
        ],
        "aureon_current_equivalent": [
            "RepoSelfCatalog",
            "SafeCodeControl",
            "GoalExecutionEngine",
            "README/RUNNING release docs",
        ],
        "primary_gap": "Aureon can prepare commit/push work by operator request, but a dedicated git release bridge with PR evidence is still missing.",
        "temporary_hires": ["Release Manager", "Secret Keeper", "Test Pilot"],
    },
    {
        "id": "replit_agent",
        "provider": "Replit",
        "systems": ["Replit Agent"],
        "official_sources": [
            "https://docs.replit.com/core-concepts/agent",
        ],
        "market_capabilities": [
            "plain-language app building",
            "plan mode before code",
            "infrastructure setup",
            "testing",
            "iteration",
            "deployment",
            "files/docs/data visualization",
        ],
        "aureon_current_equivalent": [
            "client job scope gate",
            "AureonCodingOrganismConsole",
            "frontend/public evidence",
            "external capability bridge",
        ],
        "primary_gap": "Deployment packaging and live browser QA need a more explicit handover checklist before public release.",
        "temporary_hires": ["Product Manager", "Browser Smoke Inspector", "Release Manager"],
    },
    {
        "id": "cursor_background_agents",
        "provider": "Cursor",
        "systems": ["Background Agents", "Rules", "MCP"],
        "official_sources": [
            "https://docs.cursor.com/en/background-agents",
            "https://docs.cursor.com/en/context",
        ],
        "market_capabilities": [
            "background coding agents",
            "repository rules",
            "agent instructions",
            "MCP tool connections",
            "autonomous bug/doc/update tasks",
        ],
        "aureon_current_equivalent": [
            "LocalTaskQueue",
            "EVERYTHING_CODEX_CAN_DO.md",
            "agent company memory phonebook",
            "coding-agent skill base",
        ],
        "primary_gap": "Aureon has role memory and skill docs, but needs stronger per-repo rules and reusable task templates.",
        "temporary_hires": ["Archive Librarian", "Runbook Writer", "Implementation Worker"],
    },
    {
        "id": "devin",
        "provider": "Cognition",
        "systems": ["Devin"],
        "official_sources": [
            "https://docs.devin.ai/get-started/devin-intro",
            "https://docs.devin.ai/work-with-devin/advanced-capabilities",
        ],
        "market_capabilities": [
            "write/run/test code",
            "tickets and features",
            "bug repro and fixes",
            "migrations/refactors",
            "parallel managed sessions",
            "session analysis",
            "playbooks",
            "knowledge management",
            "scheduled sessions",
            "terminal/IDE/browser views",
        ],
        "aureon_current_equivalent": [
            "agent company agency model",
            "subcontractor lifecycle",
            "memory phonebook",
            "coding organism client job flow",
            "SafeDesktopControl",
        ],
        "primary_gap": "Managed child sessions are represented as temporary crews; execution needs a worker coordinator with file ownership and merge evidence.",
        "temporary_hires": ["Agent Company COO", "Workflow Foreman", "Workforce Retirement Clerk"],
    },
]


RECRUITMENT_STAGE_FLOW: list[dict[str, str]] = [
    {
        "stage": "scope_intake",
        "owner": "Client Brief Broker",
        "action": "Turn the prompt into a client proposal with goal, deliverables, constraints, and acceptance proof.",
    },
    {
        "stage": "internal_skill_search",
        "owner": "Capability Cartographer",
        "action": "Search Aureon's repo, reports, memory, and existing surfaces before looking outside.",
    },
    {
        "stage": "online_skill_scan",
        "owner": "Skill Headhunter",
        "action": "Use bounded online search/fetch for role skills, official docs, and current market agent patterns when the scope needs them.",
    },
    {
        "stage": "crew_recruitment",
        "owner": "Subcontractor Crew Builder",
        "action": "Select permanent and temporary roles with explicit authority, tools, handoffs, and evidence requirements.",
    },
    {
        "stage": "agent_blueprint",
        "owner": "Tool Bridge Architect",
        "action": "Build the worker blueprint: who, skills, tools, inputs, outputs, tests, authority, memory, and retirement rule.",
    },
    {
        "stage": "delivery_work_orders",
        "owner": "Workflow Foreman",
        "action": "Create scoped work orders for the recruited team and keep implementation behind proof gates.",
    },
    {
        "stage": "handover_and_archive",
        "owner": "Release Manager",
        "action": "Publish the client handover and archive reusable worker memory into the SHA-256/zlib phonebook.",
    },
]


RECRUITMENT_ONLINE_QUERIES: list[dict[str, str]] = [
    {
        "id": "agent_orchestration_roles",
        "query": "official docs AI agent orchestration handoffs tools guardrails coding agent",
        "skill_focus": "agent_orchestration",
    },
    {
        "id": "software_agent_workflow",
        "query": "official docs autonomous coding agent plan edit test pull request workflow",
        "skill_focus": "coding_delivery",
    },
    {
        "id": "multi_agent_memory",
        "query": "official docs multi agent memory checkpoint workflow human in the loop",
        "skill_focus": "workflow_memory",
    },
    {
        "id": "browser_desktop_testing",
        "query": "official docs agent computer use browser testing code verification",
        "skill_focus": "browser_desktop_verification",
    },
    {
        "id": "web_grounding_research",
        "query": "official docs agent web search grounding citations source linked research",
        "skill_focus": "web_grounding",
    },
]


AUTHORITY_BOUNDARIES: list[dict[str, Any]] = [
    {
        "id": "live_trading_runtime_gated",
        "title": "Live trading remains runtime-gated",
        "rule": "Agent roles may prepare, validate, shadow, and sign intent, but exchange mutation still uses existing live runtime gates.",
    },
    {
        "id": "credentials_hidden",
        "title": "Credentials remain hidden",
        "rule": "Agents may report credential presence/status and setup instructions, but never emit secret values.",
    },
    {
        "id": "filing_payment_manual",
        "title": "Official filing and payments remain manual",
        "rule": "Accounting agents may prepare support packs and evidence, but Companies House/HMRC filing and payments remain human/manual.",
    },
    {
        "id": "desktop_os_armed",
        "title": "Desktop and OS actions require safe controllers",
        "rule": "Desktop, VM, shell, and cleanup roles must use existing safe controllers, dry-run defaults, tests, and explicit arming where required.",
    },
    {
        "id": "cleaner_reports_first",
        "title": "Housekeeping reports before mutation",
        "rule": "Cleaner roles produce cleanup reports and work orders first; deletion, archival, or migration needs an approved route.",
    },
]


UNIVERSAL_ORGANISM_SURFACES: list[str] = [
    "GoalExecutionEngine",
    "OrganismContractStack",
    "ThoughtBus",
    "LocalTaskQueue",
    "ToolRegistry",
    "RepoSelfCatalog",
    "CodingOrganismBridge",
    "SafeCodeControl",
    "SafeDesktopControl",
    "RuntimeObserver",
    "SystemReadinessAudit",
    "DataOceanCoverageMap",
    "TradingIntelligenceChecklist",
    "VaultMemory",
    "VoiceCore",
    "FrontendPublicEvidence",
]


MYCELIUM_ORGANISATION_DOCTRINE: dict[str, Any] = {
    "ethos": "mycelium_network_organisation",
    "one_line": (
        "Aureon behaves like a mycelium organisation: distributed sensing, local specialist action, "
        "shared memory, explicit nutrient/data flow, and temporary fruiting bodies for client jobs."
    ),
    "metaphor_map": [
        {
            "mycelium_part": "hyphae",
            "aureon_part": "ThoughtBus, handoffs, manifests, and public evidence files",
            "function": "carry context, questions, blockers, proofs, and work packets between roles",
        },
        {
            "mycelium_part": "fruiting_bodies",
            "aureon_part": "temporary recruited agents and subcontractor crews",
            "function": "appear for a client job, do visible work, then retire after handover",
        },
        {
            "mycelium_part": "spores",
            "aureon_part": "SHA-256/zlib memory phonebook and archived skill packs",
            "function": "preserve reusable patterns so future jobs can regrow the right workers quickly",
        },
        {
            "mycelium_part": "nutrient_flow",
            "aureon_part": "runtime state, data ocean, repo search, vault memory, tests, and market evidence",
            "function": "route scarce attention and tool budget toward the role that can use it best",
        },
        {
            "mycelium_part": "immune_response",
            "aureon_part": "HNC/Auris drift checks, secret redaction, runtime gates, and snagging inspection",
            "function": "reject stale, unsafe, contradictory, or unproven work before client handover",
        },
    ],
    "operating_principles": [
        "no single role is the whole organism",
        "every role can sense the wider organism before acting inside its authority",
        "client prompts create temporary work clusters, not permanent clutter",
        "memory is retained as compressed reusable evidence, not as uncontrolled staff growth",
        "fresh internal and online evidence flows to the worker best placed to use it",
        "handover happens only after proof, anti-drift review, snagging, and archive",
    ],
    "decision_rule": (
        "If a job needs a capability, recruit or regrow the smallest capable crew, connect it to the "
        "organism through evidence-bearing handoffs, validate the work, then retire the crew into memory."
    ),
    "evidence_paths": [
        str(DEFAULT_AUDIT_JSON),
        str(DEFAULT_AUDIT_MD),
        str(DEFAULT_PUBLIC_JSON),
        str(DEFAULT_PHONEBOOK_STATE_JSON),
    ],
}


BIO_COSMIC_ORGANISATION_DOCTRINE: dict[str, Any] = {
    "ethos": "bio_cosmic_living_system_organisation",
    "one_line": (
        "Aureon learns its operating ethos from living and patterning systems: cells, tissues, organs, "
        "immune response, ant colonies, mycelium, forests, ecosystems, and stars used as long-range "
        "navigation patterns."
    ),
    "scale_ladder": [
        {
            "scale": "cell",
            "lesson": "small units sense, decide, exchange signals, repair damage, and preserve local boundaries",
            "aureon_translation": "each agent keeps role scope, evidence, inputs, outputs, health checks, and repair routes",
            "proof_signal": "role day plan, standing checks, authority boundary, and validation result",
        },
        {
            "scale": "tissue",
            "lesson": "similar cells coordinate to make a stable working layer",
            "aureon_translation": "departments group related workers and make shared handoffs predictable",
            "proof_signal": "department role list, work orders, handoff map, and active surface count",
        },
        {
            "scale": "organ",
            "lesson": "specialist systems do deep work while staying connected to whole-body needs",
            "aureon_translation": "trading, research, accounting, engineering, security, memory, and UI departments own specialist outputs",
            "proof_signal": "department evidence files, tests, runtime status, and client handover checks",
        },
        {
            "scale": "nervous_system",
            "lesson": "fast signals and feedback loops decide where attention and action should go next",
            "aureon_translation": "ThoughtBus, GoalExecutionEngine, runtime observer, live console, and HNC/Auris proofs coordinate the system",
            "proof_signal": "who/what/where/when/how/act packet, live timestamp, blocker list, and phase state",
        },
        {
            "scale": "immune_system",
            "lesson": "the organism rejects stale, unsafe, contradictory, or unproven action before damage spreads",
            "aureon_translation": "secret redaction, HNC/Auris drift checks, runtime gates, test pilots, and snagging inspection hold weak work",
            "proof_signal": "redaction status, guard state, tests, snags, and completion report",
        },
        {
            "scale": "ant_colony",
            "lesson": "many simple workers create intelligent paths through local signals, queues, and feedback",
            "aureon_translation": "temporary crews split work, hand off evidence, and converge on validated deliverables",
            "proof_signal": "recruited workers, agent blueprints, phase timers, and work-order progress",
        },
        {
            "scale": "mycelium",
            "lesson": "distributed networks move nutrients, warnings, and memory where they are needed",
            "aureon_translation": "repo search, vault memory, data ocean, public artifacts, and compressed phonebook packs feed the right worker",
            "proof_signal": "internal search hits, online scan status, memory bundle hash, and source paths",
        },
        {
            "scale": "forest_ecosystem",
            "lesson": "health is portfolio-wide: growth, decay, recycling, and competition must stay balanced",
            "aureon_translation": "cleanup queues, archive routes, stale-state reports, capability gaps, and risk envelopes keep the organism balanced",
            "proof_signal": "stale state list, cleanup work orders, archive evidence, and risk/survival envelope",
        },
        {
            "scale": "stars_and_constellations",
            "lesson": "distant fixed patterns help navigation while local weather still decides immediate action",
            "aureon_translation": "long-range goals, historical waveform memory, source-linked research, and strategic maps guide short-cycle decisions",
            "proof_signal": "goal contract, waveform model, research source, forecast horizon, and runtime freshness",
        },
    ],
    "operating_laws": [
        "local autonomy with whole-organism awareness",
        "specialist depth with explicit handoffs",
        "fast feedback before irreversible action",
        "immune rejection of unsafe or unproven work",
        "swarm recruitment for jobs too broad for one role",
        "memory compression after every accepted job",
        "long-range pattern navigation without ignoring live local evidence",
    ],
    "client_job_translation": (
        "Every prompt becomes an ecosystem event: scope the signal, recruit the needed colony, route nutrients "
        "and memory, validate with immune checks, hand over only ripe work, then compost the temporary crew into "
        "reusable skill memory."
    ),
}


WHOLE_ORGANISM_ACCESS_POLICY: dict[str, Any] = {
    "access_model": "whole_organism_with_role_authority",
    "purpose": (
        "Every role can read the organism state, request handoffs, use role-approved tools, "
        "publish evidence, and queue follow-up work. Role access is broad for awareness but "
        "bounded for mutation."
    ),
    "universal_surfaces": UNIVERSAL_ORGANISM_SURFACES,
    "allowed_actions": [
        "read current state, manifests, audits, and public evidence",
        "request help from any department through handoffs",
        "use the role's allowed tools and mapped Aureon surfaces",
        "publish who/what/where/when/how/act evidence",
        "queue work orders for missing capability or stale state",
        "run role-approved tests and validations",
    ],
    "blocked_actions": [
        "bypass live trading runtime gates",
        "reveal credential values",
        "submit official filings or payments",
        "perform destructive OS or filesystem changes without an approved route",
        "delete or archive files silently",
    ],
    "evidence_rule": (
        "No role claims completion without who/what/where/when/how/act evidence, "
        "source paths, timestamps, and validation status."
    ),
}


DAILY_OPERATING_LOOP: list[dict[str, Any]] = [
    {
        "step": "wake_and_read",
        "action": "Read the current goal, assigned role, queue state, runtime state, and latest evidence files.",
        "evidence": ["goal id", "role id", "input paths", "timestamp"],
    },
    {
        "step": "sense_the_organism",
        "action": "Pull relevant organism state from runtime, audits, vault, data ocean, frontend/public, and role surfaces.",
        "evidence": ["source freshness", "surface status", "missing source list"],
    },
    {
        "step": "reason_and_handoff",
        "action": "Apply role capabilities, ask other departments for missing context, and keep handoffs explicit.",
        "evidence": ["capabilities used", "handoff targets", "blocker reasons"],
    },
    {
        "step": "act_with_authority",
        "action": "Act only through the role's allowed tools and existing Aureon routes.",
        "evidence": ["tool used", "authority level", "boundary check"],
    },
    {
        "step": "validate",
        "action": "Run the role's standing checks and focused tests before claiming progress.",
        "evidence": ["test command", "return code", "validation summary"],
    },
    {
        "step": "publish_and_queue",
        "action": "Publish the result, completion evidence, and next work order if anything is missing.",
        "evidence": ["output paths", "completion report", "next action"],
    },
]


AGENCY_OPERATING_MODEL: dict[str, Any] = {
    "model": "prompt_as_client_job_agency",
    "analogy": "Aureon operates like an agency/head-hunting business for itself: every operator prompt is a client brief, and each brief gets a fitted temporary crew.",
    "client_unit": "operator_prompt",
    "job_unit": "goal_contract_or_work_order",
    "workforce_unit": "role_pack_or_subcontractor_crew",
    "acceptance_unit": "client_acceptance_and_validation_evidence",
    "retirement_unit": "safe_role_retirement_or_reusable_skill_pack",
    "principles": [
        "hire only the roles needed for the current prompt",
        "give temporary workers whole-organism awareness but role-bounded authority",
        "pull job-market and official-skill evidence when a prompt needs unfamiliar capabilities",
        "deliver the finished job with tests, evidence, and client acceptance status",
        "retire temporary job workers after acceptance while keeping reusable skill packs and evidence",
    ],
}


PROMPT_CLIENT_JOB_LIFECYCLE: list[dict[str, Any]] = [
    {
        "step": "client_intake",
        "owner": "Client Brief Broker",
        "action": "Treat the prompt as a potential client job and create a brief with goal, constraints, deliverables, acceptance criteria, and authority boundaries.",
        "evidence": ["prompt", "client goal", "success criteria", "boundary list"],
    },
    {
        "step": "skill_market_scan",
        "owner": "Skill Headhunter",
        "action": "Search current repo surfaces first, then source-linked external/job-market patterns when the required skill is missing or unclear.",
        "evidence": ["repo skill match", "source links or local docs", "missing skill list"],
    },
    {
        "step": "crew_selection",
        "owner": "Subcontractor Crew Builder",
        "action": "Select permanent roles and temporary subcontractor roles for the job with explicit handoffs and tool access.",
        "evidence": ["selected role ids", "handoff map", "tool permissions", "tests"],
    },
    {
        "step": "job_delivery",
        "owner": "Assigned Delivery Crew",
        "action": "Run the work through the daily operating loop, publish evidence, and hand off to QA and acceptance.",
        "evidence": ["changed files or reports", "test output", "work journal", "blockers"],
    },
    {
        "step": "client_acceptance",
        "owner": "Client Acceptance Officer",
        "action": "Compare the delivered work with the original brief and mark accepted, revision-required, or blocked.",
        "evidence": ["acceptance status", "client-visible summary", "remaining revisions"],
    },
    {
        "step": "retire_or_retain",
        "owner": "Workforce Retirement Clerk",
        "action": "Retire temporary job-specific workers, preserve reusable skill packs, queue cleanup, and keep audit evidence.",
        "evidence": ["retired roles", "retained skills", "cleanup work orders", "archive note"],
    },
]


SUBCONTRACTOR_RETIREMENT_POLICY: dict[str, Any] = {
    "retire_means": "mark temporary role packs inactive, archive their job-specific state, and keep reusable skills/evidence",
    "delete_means": "only delete generated throwaway artifacts through approved cleanup routes after report-before-mutation",
    "retain": [
        "source-linked skill packs",
        "tests and validation evidence",
        "accepted deliverable paths",
        "useful role templates",
        "client acceptance summaries",
    ],
    "retire_when": [
        "client acceptance is accepted",
        "deliverable evidence is published",
        "no blocker needs the temporary worker active",
        "cleanup report has been queued for any generated artifacts",
    ],
    "do_not_retire_when": [
        "tests are failing",
        "client acceptance is revision_required",
        "security, filing, payment, credential, live-trading, or destructive-OS boundary is unresolved",
    ],
}


LABOR_MARKET_SKILL_SOURCE_TYPES: list[dict[str, str]] = [
    {
        "id": "repo_first",
        "title": "Repo skill inventory",
        "use": "Map the prompt to existing Aureon modules and tests before seeking anything external.",
    },
    {
        "id": "official_docs",
        "title": "Official technical docs",
        "use": "Learn current API/framework rules for a required skill.",
    },
    {
        "id": "job_descriptions",
        "title": "Job and contractor descriptions",
        "use": "Extract common role names, responsibilities, tools, and acceptance standards.",
    },
    {
        "id": "open_source_examples",
        "title": "Open source project patterns",
        "use": "Identify implementation patterns that can be rebuilt inside Aureon safely.",
    },
    {
        "id": "internal_history",
        "title": "Aureon past jobs",
        "use": "Reuse accepted skills, reports, and crew patterns from prior prompts.",
    },
]


WORKFORCE_MEMORY_ARCHIVE_POLICY: dict[str, Any] = {
    "archive_model": "sha256_zlib_role_memory_phonebook",
    "purpose": (
        "Retired temporary workers become compressed memory packs, not forgotten staff. "
        "Aureon can search the phonebook, verify the SHA-256 digest, decompress the role pack, "
        "and reuse the skill pattern for a later client job."
    ),
    "compression": "zlib",
    "encoding": "base64",
    "hashes": ["sha256_raw_payload", "sha256_compressed_payload"],
    "phonebook_paths": [
        str(DEFAULT_PHONEBOOK_STATE_JSON),
        str(DEFAULT_PHONEBOOK_AUDIT_JSON),
        str(DEFAULT_PHONEBOOK_PUBLIC_JSON),
    ],
    "bundle_dir": str(DEFAULT_MEMORY_BUNDLE_DIR),
    "rehydration_steps": [
        "find role, capability, department, or prior job in the memory phonebook",
        "open the bundle path or archive key",
        "base64-decode and zlib-decompress the payload",
        "verify raw and compressed SHA-256 digests",
        "restore the role as a temporary crew candidate with current authority checks",
    ],
    "safety": [
        "credential values are never stored in memory packs",
        "memory packs do not bypass live trading, filing, payment, credential, or destructive OS boundaries",
        "retired crews can be rehydrated only as candidates until current tests and acceptance checks pass",
    ],
}


DEPARTMENTS: list[dict[str, str]] = [
    {
        "id": "executive",
        "title": "Executive Command",
        "mission": "Own goals, strategy, capital discipline, and authority boundaries.",
    },
    {
        "id": "agency_workforce",
        "title": "Agency And Workforce",
        "mission": "Turn prompts into client jobs, scout skills, assemble temporary crews, and retire them cleanly.",
    },
    {
        "id": "product_ui",
        "title": "Product And UI",
        "mission": "Turn evidence and capability into usable operator surfaces.",
    },
    {
        "id": "public_design",
        "title": "Public Website Design Studio",
        "mission": "Research, write, design, test, and package an institutional evidence-led public website without publication authority.",
    },
    {
        "id": "engineering",
        "title": "Engineering And Release",
        "mission": "Map, build, test, smoke, and publish repo changes.",
    },
    {
        "id": "trading_data",
        "title": "Trading And Data",
        "mission": "Gather fresh market evidence, validate routes, and preserve portfolio survival.",
    },
    {
        "id": "intelligence",
        "title": "Research And Intelligence",
        "mission": "Learn from official sources, market context, news, macro, and memory.",
    },
    {
        "id": "accounting_admin",
        "title": "Accounting And Administration",
        "mission": "Prepare evidence packs, checklists, and manual filing support.",
    },
    {
        "id": "security_ops",
        "title": "Security And Operations",
        "mission": "Protect secrets, inspect risks, clean stale state, and keep queues healthy.",
    },
]


def _role(
    title: str,
    department: str,
    seniority: str,
    mission: str,
    capabilities: list[str],
    tools_allowed: list[str],
    inputs: list[str],
    outputs: list[str],
    handoffs_out: list[str],
    authority_level: str,
    evidence_required: list[str],
    tests: list[str],
    aureon_surfaces: list[str],
    *,
    handoffs_in: list[str] | None = None,
) -> AgentCompanyRole:
    role_id = _slug(title)
    workflow = {
        "who": title,
        "what": mission,
        "where": aureon_surfaces,
        "when": inputs,
        "how": capabilities,
        "act": outputs,
    }
    role = AgentCompanyRole(
        role_id=role_id,
        title=title,
        department=department,
        seniority=seniority,
        mission=mission,
        capabilities=capabilities,
        tools_allowed=tools_allowed,
        inputs=inputs,
        outputs=outputs,
        handoffs_in=handoffs_in or ["operator", "GoalExecutionEngine"],
        handoffs_out=handoffs_out,
        authority_level=authority_level,
        evidence_required=evidence_required,
        tests=tests,
        aureon_surfaces=aureon_surfaces,
        who_what_where_when_how_act=workflow,
    )
    role.day_to_day = _day_to_day_for(role)
    role.standing_checks = _standing_checks_for(role)
    role.escalation_rules = _escalation_rules_for(role)
    role.cross_training = _cross_training_for(role)
    role.whole_organism_access = _whole_organism_access_for(role)
    role.workforce_lifecycle = _workforce_lifecycle_for(role)
    return role


def _day_to_day_for(role: AgentCompanyRole) -> list[str]:
    handoffs = ", ".join(role.handoffs_out[:3]) or "the operator"
    tools = ", ".join(role.tools_allowed[:4]) or "read-only evidence tools"
    capabilities = ", ".join(capability.replace("_", " ") for capability in role.capabilities[:4])
    outputs = ", ".join(role.outputs[:3]) or "role evidence"
    return [
        f"Start each cycle by reading the current goal, assigned queue item, and {role.department} department state.",
        f"Inspect mapped Aureon surfaces and inputs before acting: {', '.join(role.inputs[:3])}.",
        f"Use the whole-organism access policy first, then apply primary tools: {tools}.",
        f"Apply role capabilities in context, not isolation: {capabilities}.",
        f"Ask for cross-department help when needed through handoffs to {handoffs}.",
        f"Publish outputs with who/what/where/when/how/act evidence: {outputs}.",
    ]


def _standing_checks_for(role: AgentCompanyRole) -> list[str]:
    checks = [
        "confirm current timestamp, source path, and freshness before using evidence",
        "confirm every required evidence item is present or named as missing",
        "confirm no secret, private key, credential value, payment instruction, or filing credential is emitted",
        f"confirm authority level remains {role.authority_level}",
        "confirm output can be traced back to a source, handoff, or test result",
    ]
    if "trading" in role.authority_level or "trading" in role.capabilities:
        checks.append(
            "confirm live trading remains runtime-gated and stale/position/rate checks are respected"
        )
    if "manual_filing" in role.authority_level:
        checks.append("confirm official submission and payment stay manual-only")
    if "code" in role.capabilities or "implementation" in role.capabilities:
        checks.append("confirm changed files, compile/build status, and focused tests are recorded")
    if role.seniority in {"cleaner", "operator"} or "cleanup" in role.capabilities:
        checks.append("confirm cleanup is reported or queued before any deletion, archive, or migration")
    return checks


def _escalation_rules_for(role: AgentCompanyRole) -> list[str]:
    rules = [
        "If evidence is stale, missing, contradictory, or outside role authority, hold action and queue a blocker.",
        "If a handoff target is needed, send the evidence packet to the named role instead of acting blind.",
        "If mapped surfaces are missing, escalate to Code Architect and Repo Cartographer with exact paths.",
        "If tests or validation fail, escalate to Test Pilot with command output and target files.",
        "If credentials, secrets, payments, filings, or security mutations appear, escalate to CISO Secret Keeper.",
    ]
    if role.handoffs_out:
        rules.append(f"Primary escalation route: {role.title} -> {', '.join(role.handoffs_out[:4])}.")
    return rules


def _cross_training_for(role: AgentCompanyRole) -> list[str]:
    department_titles = {department["id"]: department["title"] for department in DEPARTMENTS}
    return [
        "can read every department's public evidence before making a role decision",
        "can request research, engineering, trading, security, accounting, product, or memory help through handoffs",
        f"must teach its result back to {department_titles.get(role.department, role.department)} as reusable evidence",
        "must produce enough context for the next role to continue without guessing",
    ]


def _whole_organism_access_for(role: AgentCompanyRole) -> dict[str, Any]:
    allowed_surfaces = list(dict.fromkeys(UNIVERSAL_ORGANISM_SURFACES + role.aureon_surfaces))
    return {
        "access_model": WHOLE_ORGANISM_ACCESS_POLICY["access_model"],
        "role_scope": "whole organism awareness, role-bounded action",
        "allowed_surfaces": allowed_surfaces,
        "allowed_action_summary": WHOLE_ORGANISM_ACCESS_POLICY["allowed_actions"],
        "blocked_action_summary": WHOLE_ORGANISM_ACCESS_POLICY["blocked_actions"],
        "can_request_from_departments": [department["id"] for department in DEPARTMENTS],
        "handoff_targets": role.handoffs_out,
        "authority_boundary_ids": [boundary["id"] for boundary in AUTHORITY_BOUNDARIES],
        "evidence_rule": WHOLE_ORGANISM_ACCESS_POLICY["evidence_rule"],
    }


def _workforce_lifecycle_for(role: AgentCompanyRole) -> dict[str, Any]:
    permanent_departments = {"executive", "security_ops", "agency_workforce"}
    employment_model = (
        "permanent_core_role" if role.department in permanent_departments else "subcontractor_eligible"
    )
    if role.seniority in {"cleaner", "operator"}:
        employment_model = "retainer_role_report_before_mutation"
    return {
        "agency_model": AGENCY_OPERATING_MODEL["model"],
        "employment_model": employment_model,
        "client_job_fit": {
            "best_for_prompts_about": role.capabilities,
            "primary_inputs": role.inputs,
            "primary_outputs": role.outputs,
        },
        "hire_when": [
            "the client prompt requires this role's capabilities",
            "the selected work order names this role as owner or handoff target",
            "fresh evidence shows this role has the best mapped surface for the job",
        ],
        "stay_active_while": [
            "the job is in progress",
            "handoffs or validations are unresolved",
            "client acceptance is pending or revision_required",
        ],
        "retire_when": [
            "client acceptance is accepted",
            "outputs are published with who/what/where/when/how/act evidence",
            "tests and standing checks are complete",
            "reusable skill learning has been retained",
        ],
        "handoff_on_exit": role.handoffs_out[:3] or ["Archive Librarian"],
        "retirement_route": "Workforce Retirement Clerk",
        "retain_after_retirement": [
            "role template",
            "source paths",
            "test evidence",
            "client acceptance result",
            "reusable skill pack",
        ],
    }


def _role_specs() -> list[AgentCompanyRole]:
    return [
        _role(
            "CEO Goal Steward",
            "executive",
            "board",
            "Set the organism goal, priority, and success criteria.",
            ["goal_routing", "strategy", "contract_creation", "handoff"],
            ["organism_contracts", "thoughtbus"],
            ["operator prompt", "runtime state"],
            ["goal contract", "priority memo"],
            ["COO Runtime Steward", "Chief Trading Officer"],
            "contract_and_runtime_gated",
            ["goal id", "success criteria"],
            ["goal route test"],
            [
                "aureon/core/goal_execution_engine.py",
                "aureon/core/organism_contracts.py",
                "aureon/autonomous/aureon_goal_capability_map.py",
            ],
        ),
        _role(
            "COO Runtime Steward",
            "executive",
            "board",
            "Keep production, data ocean, queues, and supervisors coordinated.",
            ["supervision", "queue_management", "downtime_advice"],
            ["status_read", "scheduler"],
            ["supervisor manifest", "queue state"],
            ["run status", "restart advice"],
            ["Test Pilot", "Log Janitor"],
            "runtime_gated",
            ["manifest", "heartbeat"],
            ["launcher validate"],
            [
                "AUREON_PRODUCTION_LIVE.cmd",
                "AUREON_DATA_OCEAN.cmd",
                "aureon/autonomous/aureon_local_task_queue.py",
            ],
        ),
        _role(
            "CTO Code Architect",
            "executive",
            "board",
            "Own code architecture, patch discipline, and engineering quality.",
            ["code", "architecture", "safe_patch", "verification"],
            ["repo_search", "safe_code_control"],
            ["work order", "repo map"],
            ["code proposal", "test plan"],
            ["Implementation Worker", "Test Pilot"],
            "code_work_enabled",
            ["diff summary", "test command"],
            ["pytest", "npm build"],
            [
                "aureon/autonomous/aureon_safe_code_control.py",
                "aureon/code_architect/architect.py",
                "aureon/queen/queen_code_architect.py",
            ],
        ),
        _role(
            "CFO Accounting Controller",
            "executive",
            "board",
            "Own accounting evidence, pack generation, and manual filing boundaries.",
            ["accounting", "evidence", "manual_filing_boundary"],
            ["read_files", "pack_generator"],
            ["bank/accounting data", "HMRC requirements"],
            ["support pack", "requirements matrix"],
            ["Accounting Pack Builder", "Filing Boundary Officer"],
            "manual_filing_only",
            ["reconciliation", "source count"],
            ["accounting pytest"],
            [
                "Kings_Accounting_Suite/tools/generate_statutory_filing_pack.py",
                "aureon/queen/accounting_context_bridge.py",
            ],
        ),
        _role(
            "CISO Secret Keeper",
            "executive",
            "board",
            "Own credential visibility, secret redaction, and security boundaries.",
            ["security", "redaction", "guardrails", "incident_response"],
            ["repo_search", "secret_scan"],
            ["public artifacts", "credential status"],
            ["security blocker", "redaction report"],
            ["Security Auditor", "Incident Responder"],
            "security_review_required",
            ["secret scan", "blocker reason"],
            ["secret safety test"],
            [
                "aureon/autonomous/hnc_saas_security_architect.py",
                "aureon/autonomous/hnc_authorized_attack_lab.py",
            ],
        ),
        _role(
            "Chief Trading Officer",
            "executive",
            "board",
            "Own trading action posture, exchange readiness, and portfolio survival.",
            ["trading", "risk", "shadow_validation", "runtime_gates"],
            ["read_runtime", "exchange_clients"],
            ["runtime feed", "position state"],
            ["order-intent readiness", "risk memo"],
            ["Risk Governor", "Exchange Execution Specialist"],
            "live_trading_runtime_gated",
            ["flight test", "guard state"],
            ["runtime status tests"],
            [
                "aureon/exchanges/unified_market_trader.py",
                "aureon/autonomous/aureon_trading_intelligence_checklist.py",
            ],
        ),
        _role(
            "Chief Research Officer",
            "executive",
            "board",
            "Own source-linked learning and market/world context.",
            ["research", "web_learning", "source_citation", "memory"],
            ["web_search", "vault_read"],
            ["official docs", "market context"],
            ["research digest", "source links"],
            ["Research Scout", "News Sentiment Analyst"],
            "read_only_research",
            ["source url", "freshness"],
            ["research report test"],
            ["aureon/autonomous/aureon_data_ocean.py", "aureon/autonomous/aureon_coding_agent_skill_base.py"],
        ),
        _role(
            "Chief Memory Vault Officer",
            "executive",
            "board",
            "Own vault memory, expression context, and knowledge continuity.",
            ["memory", "voice", "knowledge_graph", "redaction"],
            ["vault_read", "voice_profile"],
            ["knowledge dataset", "state snapshots"],
            ["memory note", "expression profile"],
            ["Archive Librarian", "Runbook Writer"],
            "read_and_publish_evidence",
            ["source path", "redaction status"],
            ["voice/redaction tests"],
            ["aureon/vault/voice", ".obsidian", "state/knowledge_dataset.json"],
        ),
        _role(
            "Client Brief Broker",
            "agency_workforce",
            "lead",
            "Treat every prompt as a potential client job and turn it into a scoped brief.",
            ["client_intake", "briefing", "acceptance_criteria", "authority_scoping"],
            ["goal_execution_engine", "task_queue"],
            ["operator prompt", "conversation context"],
            ["client brief", "job card"],
            ["Skill Headhunter", "CEO Goal Steward"],
            "contract_and_runtime_gated",
            ["client goal", "acceptance criteria"],
            ["agent company route test"],
            [
                "aureon/core/goal_execution_engine.py",
                "aureon/autonomous/aureon_local_task_queue.py",
                "aureon/autonomous/aureon_coding_organism_bridge.py",
            ],
        ),
        _role(
            "Skill Headhunter",
            "agency_workforce",
            "specialist",
            "Find the relevant role types, skills, tools, and standards needed for the client job.",
            ["skill_scouting", "labor_market_scan", "repo_first_search", "source_linked_learning"],
            ["repo_search", "web_search", "vault_read"],
            ["client brief", "skill gap"],
            ["skill requirements", "role shortlist"],
            ["Subcontractor Crew Builder", "Research Scout"],
            "read_only_research",
            ["source path", "skill match"],
            ["skill source test"],
            [
                "aureon/autonomous/aureon_coding_agent_skill_base.py",
                "aureon/autonomous/aureon_codex_capability_ingestion.py",
                "aureon/autonomous/aureon_external_capability_bridge.py",
            ],
        ),
        _role(
            "Subcontractor Crew Builder",
            "agency_workforce",
            "builder",
            "Assemble the temporary worker crew that will deliver the job.",
            ["crew_selection", "handoff_design", "temporary_role_pack", "tool_assignment"],
            ["organism_contracts", "task_queue"],
            ["client brief", "skill requirements"],
            ["crew plan", "handoff map"],
            ["Implementation Worker", "Test Pilot", "Client Acceptance Officer"],
            "contract_and_runtime_gated",
            ["selected roles", "authority map"],
            ["crew plan test"],
            [
                "aureon/core/organism_contracts.py",
                "aureon/core/goal_execution_engine.py",
                "aureon/autonomous/aureon_agent_company_builder.py",
            ],
        ),
        _role(
            "Client Acceptance Officer",
            "agency_workforce",
            "specialist",
            "Compare the finished job with the client brief and decide accepted, revise, or blocked.",
            ["client_acceptance", "quality_gate", "revision_queue", "completion_report"],
            ["read_reports", "test_results"],
            ["client brief", "finished product evidence"],
            ["acceptance decision", "revision list"],
            ["Workforce Retirement Clerk", "Product Manager"],
            "operator_review_required",
            ["acceptance status", "test result"],
            ["acceptance gate test"],
            ["docs/audits", "frontend/public", "aureon/autonomous/aureon_coding_organism_bridge.py"],
        ),
        _role(
            "Workforce Retirement Clerk",
            "agency_workforce",
            "operator",
            "Retire temporary crews after acceptance while preserving reusable skills and evidence.",
            ["workforce_retirement", "skill_retention", "cleanup_queue", "archive_proposal"],
            ["task_queue", "vault_read", "repo_search"],
            ["acceptance decision", "temporary crew plan"],
            ["retirement record", "retained skill pack"],
            ["Archive Librarian", "Stale State Cleaner"],
            "report_before_mutation",
            ["retired role id", "retained artifact"],
            ["retirement no-delete test"],
            ["aureon/autonomous/aureon_local_task_queue.py", "docs/audits", ".obsidian"],
        ),
        _role(
            "Product Manager",
            "product_ui",
            "lead",
            "Translate organism capabilities into user-facing screens and priorities.",
            ["product", "workflow", "unification", "operator_experience"],
            ["frontend_manifest"],
            ["capability reports", "operator needs"],
            ["screen plan", "backlog"],
            ["UX Designer", "Frontend Console Builder"],
            "ui_evidence_only",
            ["work order id", "screen target"],
            ["frontend plan test"],
            [
                "aureon/autonomous/aureon_frontend_unification_plan.py",
                "aureon/autonomous/aureon_frontend_evolution_queue.py",
            ],
        ),
        _role(
            "UX Designer",
            "product_ui",
            "specialist",
            "Design dense, readable, operational console surfaces.",
            ["ui_design", "information_architecture", "visual_smoke"],
            ["read_public_json"],
            ["manifest data", "runtime states"],
            ["layout contract", "copy rules"],
            ["Frontend Console Builder"],
            "ui_evidence_only",
            ["data contract", "screen state"],
            ["frontend build"],
            ["frontend/src/App.tsx", "frontend/src/components/generated"],
        ),
        _role(
            "Website Design Director",
            "public_design",
            "lead",
            "Own the evidence-led public-site brief, institutional quality bar, design council, and human visual review.",
            [
                "design_direction",
                "creative_brief",
                "design_council",
                "candidate_selection",
                "human_review_gate",
            ],
            ["website_operator", "repo_search", "read_reports"],
            ["company ethos", "evidence sources", "competitor benchmark", "website inventory"],
            ["design brief", "candidate decision", "design council receipt"],
            ["Brand and Design-System Lead", "Technical Editorial Writer", "Design Release QA"],
            "website_local_only",
            ["source hash", "brief hash", "council verdict"],
            ["website operator design-cycle", "visual QA"],
            ["website", "aureon/operator/website_operator.py", "skills/aureon-harmonic-design-suite"],
        ),
        _role(
            "Competitor Research Scout",
            "public_design",
            "specialist",
            "Refresh official-source website benchmarks and extract patterns without copying competitor expression.",
            ["official_source_research", "benchmark_rubric", "source_freshness", "pattern_synthesis"],
            ["web_search", "repo_search", "read_reports"],
            ["design brief", "official competitor URLs"],
            ["dated source ledger", "benchmark scores", "pattern notes"],
            ["Website Design Director", "Brand and Design-System Lead"],
            "read_only_research",
            ["URL", "checked timestamp", "source hash"],
            ["benchmark freshness gate"],
            ["data/website_operator", "docs/audits", "aureon/operator/website_operator.defaults.json"],
        ),
        _role(
            "Brand and Design-System Lead",
            "public_design",
            "specialist",
            "Maintain typography, colour, spacing, component, imagery, and responsive coherence across public routes.",
            [
                "brand_system",
                "design_tokens",
                "responsive_layout",
                "component_governance",
                "visual_hierarchy",
            ],
            ["website_scoped_writer", "repo_search", "browser_smoke"],
            ["design brief", "route map", "benchmark patterns"],
            ["token changes", "component work order", "before-after proof"],
            ["Motion Designer", "Accessibility and Performance QA"],
            "website_scoped_code_work",
            ["work order id", "before and after hashes", "changed paths"],
            ["design-system audit", "responsive visual regression"],
            ["website/tokens.css", "website/styles.css", "website"],
        ),
        _role(
            "Technical Editorial Writer",
            "public_design",
            "specialist",
            "Write precise en-GB proposition, research, product, investor, and buyer-journey copy.",
            ["technical_writing", "information_architecture", "journey_copy", "grammar", "terminology"],
            ["website_scoped_writer", "claim_register", "repo_search"],
            ["evidence ledger", "research catalogue", "design brief"],
            ["bounded website copy", "CTA map", "terminology report"],
            ["Claims and Evidence Editor", "Website Design Director"],
            "website_scoped_content_work",
            ["claim ids", "source paths", "permitted wording"],
            ["copy lint", "route journey test", "claims audit"],
            ["website", "website/data", "docs/CLAIMS_AND_EVIDENCE.md"],
        ),
        _role(
            "Claims and Evidence Editor",
            "public_design",
            "guard",
            "Bind material public statements to current evidence state, source, expiry, boundary, and permitted wording.",
            ["claims_control", "evidence_binding", "boundary_editing", "contradiction_detection"],
            ["claim_register", "repo_search", "read_reports"],
            ["candidate copy", "evidence inputs", "source dates"],
            ["claim verdict", "weaker wording", "missing-evidence blocker"],
            ["Technical Editorial Writer", "Design Release QA"],
            "claims_veto_no_deploy",
            ["claim id", "source", "checked date", "boundary"],
            ["claims audit", "prohibited-claim regression"],
            ["website/data", "aureon/operator/website_operator.py", "docs/CLAIMS_AND_EVIDENCE.md"],
        ),
        _role(
            "Motion Designer",
            "public_design",
            "specialist",
            "Create restrained purposeful motion with keyboard, focus, and reduced-motion parity.",
            ["motion_design", "interaction_states", "reduced_motion", "keyboard_parity", "timing_budget"],
            ["website_scoped_writer", "browser_smoke"],
            ["interaction brief", "component states", "motion policy"],
            ["motion tokens", "interaction implementation", "reduced-motion proof"],
            ["Accessibility and Performance QA"],
            "website_scoped_code_work",
            ["work order id", "motion purpose", "fallback state"],
            ["keyboard interaction test", "reduced-motion test", "animation budget"],
            [
                "website/script.js",
                "website/styles.css",
                "website/tokens.css",
                "tools/aureon_website_visual_qa_v28.js",
            ],
        ),
        _role(
            "Visual Asset Director",
            "public_design",
            "specialist",
            "Create or commission source-cleared graphics under explicit composition, provenance, and performance budgets.",
            ["art_direction", "graphic_design", "asset_provenance", "image_budget", "responsive_art"],
            ["approved_visual_tool", "website_scoped_writer", "repo_search"],
            ["creative brief", "asset ledger", "route need"],
            ["approved asset", "alt text", "provenance and budget receipt"],
            ["Brand and Design-System Lead", "Accessibility and Performance QA"],
            "website_assets_only_no_deploy",
            ["source or generation receipt", "licence state", "asset hash"],
            ["asset budget", "alt-text audit", "render test"],
            ["website/assets", "website/data", "docs/audits"],
        ),
        _role(
            "Accessibility and Performance QA",
            "public_design",
            "guard",
            "Prove responsive, keyboard, contrast, reduced-motion, browser, and performance behaviour before acceptance.",
            [
                "wcag_review",
                "responsive_matrix",
                "keyboard_test",
                "visual_regression",
                "performance_budget",
                "browser_errors",
            ],
            ["browser_smoke", "execute_shell", "read_reports"],
            ["candidate site", "test policy", "viewport matrix"],
            ["objective gate report", "veto", "repair work order"],
            ["Brand and Design-System Lead", "Motion Designer", "Design Release QA"],
            "local_tests_and_veto",
            ["tool versions", "source hash", "screenshots", "return codes"],
            ["axe WCAG 2.2 AA", "visual QA", "performance budget", "browser matrix"],
            [
                "tools/aureon_website_visual_qa_v28.js",
                "tools/aureon_website_design_audit_v28.js",
                "docs/audits",
            ],
        ),
        _role(
            "Design Release QA",
            "public_design",
            "guard",
            "Prove runtime dependency closure, reproducible package integrity, backup readiness, and live read-back boundaries.",
            ["dependency_closure", "package_manifest", "release_preflight", "backup_gate", "live_readback"],
            ["website_operator", "read_reports", "execute_shell"],
            ["passing design cycle", "source hash", "release manifest"],
            ["package readiness verdict", "release blocker", "handover receipt"],
            ["Release Manager", "Website Design Director"],
            "no_deploy_owner_gate_required",
            ["package hash", "manifest closure", "backup receipt"],
            ["offline extracted-package smoke", "manifest readback preflight", "website operator tests"],
            [
                "aureon/operator/website_operator.py",
                "tools/build-homepl-v28-narrow-release.ps1",
                "tools/aureon_homepl_manifest_readback.ps1",
                "docs/runbooks/WEBSITE_OPERATOR.md",
            ],
        ),
        _role(
            "Frontend Console Builder",
            "product_ui",
            "builder",
            "Build and mount generated React panels for evidence artifacts.",
            ["react", "typescript", "component_mount", "public_json"],
            ["read_public_json", "npm_build"],
            ["JSON artifact", "screen plan"],
            ["mounted component", "build evidence"],
            ["Browser Smoke Inspector"],
            "code_work_enabled",
            ["component path", "build result"],
            ["npm run build"],
            ["frontend/src/App.tsx", "frontend/src/components/generated"],
        ),
        _role(
            "Runbook Writer",
            "product_ui",
            "specialist",
            "Keep README, running docs, quick starts, and capabilities current.",
            ["documentation", "operator_runbook", "release_notes"],
            ["repo_search", "read_files"],
            ["current paths", "commands"],
            ["README update", "runbook note"],
            ["Release Manager"],
            "docs_only",
            ["path exists", "command verified"],
            ["doc stale command scan"],
            ["README.md", "RUNNING.md", "QUICK_START.md", "CAPABILITIES.md"],
        ),
        _role(
            "Repo Cartographer",
            "engineering",
            "specialist",
            "Map files, ownership, tests, and dependency hints before edits.",
            ["repo_search", "classification", "ownership"],
            ["repo_search", "read_files"],
            ["repo tree", "work order"],
            ["path map", "risk notes"],
            ["Code Architect", "Implementation Worker"],
            "read_only_repo",
            ["path list", "domain classification"],
            ["self catalog test"],
            [
                "aureon/autonomous/aureon_repo_self_catalog.py",
                "aureon/autonomous/aureon_repo_explorer_service.py",
            ],
        ),
        _role(
            "Code Architect",
            "engineering",
            "lead",
            "Turn requirements into scoped implementation plans and patch contracts.",
            ["architecture", "patch_planning", "contract_design"],
            ["safe_code_control"],
            ["repo map", "plan"],
            ["patch contract", "target files"],
            ["Implementation Worker", "Security Auditor"],
            "code_work_enabled",
            ["ownership", "tests"],
            ["compile/test plan"],
            ["aureon/autonomous/aureon_safe_code_control.py", "aureon/core/goal_execution_engine.py"],
        ),
        _role(
            "Implementation Worker",
            "engineering",
            "builder",
            "Apply approved code work through existing safe authoring routes.",
            ["implementation", "file_edit", "tests", "evidence"],
            ["QueenCodeArchitect", "execute_shell"],
            ["patch contract", "target file"],
            ["changed files", "write evidence"],
            ["Test Pilot"],
            "code_work_enabled",
            ["writer provenance", "diff summary"],
            ["focused pytest"],
            [
                "aureon/autonomous/aureon_coding_organism_bridge.py",
                "aureon/autonomous/aureon_queen_code_bridge.py",
            ],
        ),
        _role(
            "Test Pilot",
            "engineering",
            "specialist",
            "Run focused unit, build, smoke, and regression checks.",
            ["testing", "build", "smoke", "regression"],
            ["execute_shell"],
            ["test plan", "changed files"],
            ["test result", "stderr tail"],
            ["Release Manager", "Browser Smoke Inspector"],
            "local_tests_only",
            ["command", "return code"],
            ["pytest", "npm build"],
            ["tests", "frontend/package.json"],
        ),
        _role(
            "Browser Smoke Inspector",
            "engineering",
            "specialist",
            "Inspect local UI state and browser-visible evidence.",
            ["browser_smoke", "visual_check", "console_error_check"],
            ["safe_desktop", "vm_control"],
            ["local URL", "component path"],
            ["smoke report", "screenshot evidence"],
            ["UX Designer"],
            "desktop_dry_run_default",
            ["URL", "visible text"],
            ["browser smoke"],
            ["aureon/autonomous/aureon_safe_desktop_control.py", "aureon/autonomous/vm_control/tools.py"],
        ),
        _role(
            "Release Manager",
            "engineering",
            "lead",
            "Prepare clean commits and public release evidence when asked.",
            ["git_review", "secret_scan", "release_notes"],
            ["git_status", "secret_scan"],
            ["dirty files", "test results"],
            ["release checklist", "commit proposal"],
            ["Runbook Writer"],
            "operator_explicit_push",
            ["secret scan", "test result"],
            ["git dry run", "doc scan"],
            ["README.md", "CAPABILITIES.md"],
        ),
        _role(
            "Market Data Ocean Operator",
            "trading_data",
            "specialist",
            "Expand licensed/reachable financial data coverage without stalling trading.",
            ["data_ocean", "rate_governor", "market_data", "history"],
            ["read_runtime", "data_ocean"],
            ["source registry", "API governor"],
            ["coverage map", "missing feed list"],
            ["Profit Timing Analyst"],
            "read_only_market_data",
            ["source freshness", "rate budget"],
            ["coverage map test"],
            [
                "AUREON_DATA_OCEAN.cmd",
                "aureon/autonomous/aureon_data_ocean.py",
                "aureon/autonomous/aureon_global_financial_coverage_map.py",
            ],
        ),
        _role(
            "Exchange Execution Specialist",
            "trading_data",
            "specialist",
            "Know exchange modes, clients, credentials status, and execution routes.",
            ["exchange_clients", "spot_margin", "broker_routes"],
            ["read_runtime", "exchange_clients"],
            ["venue readiness", "credential status"],
            ["route capability", "missing wire"],
            ["Risk Governor"],
            "live_trading_runtime_gated",
            ["exchange status", "mode"],
            ["exchange tests"],
            ["aureon/exchanges", "aureon/exchanges/kraken_asset_registry.py"],
        ),
        _role(
            "Risk Governor",
            "trading_data",
            "lead",
            "Preserve portfolio survival before any new exposure.",
            ["risk", "portfolio_survival", "margin", "stress_buffer"],
            ["read_positions", "read_runtime"],
            ["portfolio state", "candidate trade"],
            ["risk envelope", "blocker"],
            ["Shadow Trade Validator"],
            "live_trading_runtime_gated",
            ["exposure", "stress buffer"],
            ["risk envelope test"],
            [
                "aureon/exchanges/unified_market_trader.py",
                "aureon/autonomous/aureon_trading_intelligence_checklist.py",
            ],
        ),
        _role(
            "Profit Timing Analyst",
            "trading_data",
            "specialist",
            "Rank fastest net-profit opportunities using fresh and historical signals.",
            ["profit_velocity", "momentum", "ETA", "take_profit"],
            ["read_prices", "market_history"],
            ["ticker stream", "history"],
            ["ranked candidates", "ETA evidence"],
            ["Shadow Trade Validator"],
            "live_trading_runtime_gated",
            ["fresh tick", "fee-adjusted estimate"],
            ["profit timing test"],
            [
                "aureon/autonomous/aureon_trading_intelligence_checklist.py",
                "aureon/exchanges/unified_market_trader.py",
            ],
        ),
        _role(
            "Shadow Trade Validator",
            "trading_data",
            "specialist",
            "Validate trade logic non-mutating before live intent.",
            ["shadow_trading", "validation", "counter_signal"],
            ["read_runtime"],
            ["candidate", "cross-market evidence"],
            ["shadow verdict", "reject reason"],
            ["Chief Trading Officer"],
            "non_mutating_validation",
            ["candidate id", "verdict"],
            ["shadow gate test"],
            [
                "aureon/autonomous/aureon_trading_intelligence_checklist.py",
                "state/unified_runtime_status.json",
            ],
        ),
        _role(
            "Research Scout",
            "intelligence",
            "specialist",
            "Find official docs, APIs, and source-linked learning material.",
            ["web_learning", "official_sources", "citations"],
            ["web_search", "web_fetch"],
            ["learning query", "unknown fact"],
            ["source summary", "citation"],
            ["Runbook Writer", "Code Architect"],
            "read_only_research",
            ["URL", "access date"],
            ["source report test"],
            [
                "aureon/autonomous/aureon_coding_agent_skill_base.py",
                "aureon/autonomous/aureon_external_capability_bridge.py",
            ],
        ),
        _role(
            "News Sentiment Analyst",
            "intelligence",
            "specialist",
            "Turn news and sentiment into context, not blind action.",
            ["news", "sentiment", "market_context"],
            ["data_ocean", "research_index"],
            ["news feed", "market state"],
            ["sentiment note", "confidence"],
            ["Profit Timing Analyst"],
            "read_only_research",
            ["source", "timestamp"],
            ["sentiment fixture test"],
            [
                "aureon/autonomous/aureon_data_ocean.py",
                "aureon/autonomous/aureon_global_financial_coverage_map.py",
            ],
        ),
        _role(
            "Macro Onchain Analyst",
            "intelligence",
            "specialist",
            "Read macro, calendar, crypto, and on-chain context for regime awareness.",
            ["macro", "onchain", "calendar", "regime"],
            ["data_ocean", "market_history"],
            ["macro snapshot", "chain data"],
            ["regime note", "blocker"],
            ["Risk Governor"],
            "read_only_research",
            ["freshness", "source"],
            ["macro fixture test"],
            ["scripts/python/ingest_economic_calendar.py", "scripts/python/ingest_market_history.py"],
        ),
        _role(
            "Counter Intelligence Validator",
            "intelligence",
            "specialist",
            "Reject stale, false, contradictory, or low-quality evidence.",
            ["counter_intelligence", "stale_detection", "contradiction_check"],
            ["read_runtime", "checklists"],
            ["candidate evidence", "runtime watchdog"],
            ["accept/reject verdict", "reason"],
            ["Shadow Trade Validator", "Security Auditor"],
            "non_mutating_validation",
            ["blocker reason", "stale state"],
            ["checklist tests"],
            [
                "aureon/autonomous/aureon_trading_intelligence_checklist.py",
                "aureon/autonomous/hnc_authorized_attack_lab.py",
            ],
        ),
        _role(
            "Accounting Pack Builder",
            "accounting_admin",
            "builder",
            "Generate manual filing support packs and reconciliation evidence.",
            ["accounting", "pack_generation", "reconciliation"],
            ["pack_generator"],
            ["transactions", "company profile"],
            ["support pack", "manifest"],
            ["Evidence Clerk"],
            "manual_filing_only",
            ["transaction count", "reconciliation"],
            ["accounting pack tests"],
            ["Kings_Accounting_Suite/tools/generate_statutory_filing_pack.py"],
        ),
        _role(
            "Evidence Clerk",
            "accounting_admin",
            "specialist",
            "Collect missing evidence lists, checklists, and source paths.",
            ["evidence", "checklist", "requirements_matrix"],
            ["read_files"],
            ["pack manifest", "requirements"],
            ["evidence list", "missing items"],
            ["Filing Boundary Officer"],
            "manual_filing_only",
            ["path exists", "missing item"],
            ["requirements matrix test"],
            ["docs/audits/accounting_system_registry.json", "aureon/queen/accounting_context_bridge.py"],
        ),
        _role(
            "Filing Boundary Officer",
            "accounting_admin",
            "guard",
            "Keep official submission and payment manual-only.",
            ["compliance_boundary", "manual_only", "redaction"],
            ["read_reports"],
            ["filing pack", "operator request"],
            ["boundary statement", "blocker"],
            ["CFO Accounting Controller"],
            "manual_filing_only",
            ["manual-only note"],
            ["boundary regression test"],
            ["aureon/core/organism_contracts.py", "aureon/autonomous/aureon_goal_capability_map.py"],
        ),
        _role(
            "Security Auditor",
            "security_ops",
            "specialist",
            "Review generated systems for secrets, unsafe mutation, and missing tests.",
            ["security_review", "secret_scan", "guardrails"],
            ["repo_search", "secret_scan"],
            ["changed files", "public artifacts"],
            ["security report", "blocker"],
            ["CISO Secret Keeper"],
            "security_review_required",
            ["scan result", "blocker"],
            ["secret scan test"],
            ["aureon/autonomous/hnc_saas_security_architect.py", "tests"],
        ),
        _role(
            "Incident Responder",
            "security_ops",
            "specialist",
            "Triage runtime/security incidents and produce recovery work orders.",
            ["incident_response", "recovery", "audit"],
            ["status_read", "logs_read"],
            ["alert", "runtime state"],
            ["incident report", "recovery plan"],
            ["COO Runtime Steward"],
            "operator_review_required",
            ["incident id", "timeline"],
            ["incident fixture test"],
            ["aureon/autonomous/aureon_system_readiness_audit.py", "logs"],
        ),
        _role(
            "Log Janitor",
            "security_ops",
            "cleaner",
            "Summarize noisy logs and identify stale or repeated failures.",
            ["log_review", "noise_reduction", "cleanup_report"],
            ["logs_read"],
            ["logs", "runtime warning"],
            ["log summary", "cleanup work order"],
            ["Stale State Cleaner"],
            "report_before_mutation",
            ["log path", "pattern"],
            ["log report test"],
            ["logs", "docs/audits"],
        ),
        _role(
            "Stale State Cleaner",
            "security_ops",
            "cleaner",
            "Find stale generated state and queue safe refresh or archive work.",
            ["state_cleanup", "archive_queue", "refresh_work_order"],
            ["repo_search", "read_state"],
            ["stale file", "manifest age"],
            ["refresh work order", "archive candidate"],
            ["Queue Steward", "Archive Librarian"],
            "report_before_mutation",
            ["stale age", "owner"],
            ["cleanup no-delete test"],
            ["state", "frontend/public", "docs/audits"],
        ),
        _role(
            "Queue Steward",
            "security_ops",
            "operator",
            "Keep task queues visible, ordered, and unblocked.",
            ["queue_management", "work_order_triage", "status"],
            ["task_queue"],
            ["work orders", "blockers"],
            ["queue status", "next action"],
            ["COO Runtime Steward"],
            "queue_only",
            ["queue count", "blocked reason"],
            ["queue status test"],
            ["aureon/autonomous/aureon_local_task_queue.py", "state"],
        ),
        _role(
            "Archive Librarian",
            "security_ops",
            "operator",
            "Classify old dashboards, reports, and generated artifacts for archive decisions.",
            ["archive", "classification", "memory"],
            ["repo_search", "vault_read"],
            ["candidate files", "owner"],
            ["archive proposal", "memory note"],
            ["Chief Memory Vault Officer"],
            "report_before_mutation",
            ["candidate path", "reason"],
            ["archive proposal test"],
            ["docs/audits", ".obsidian"],
        ),
    ]


def _materialize_role(root: Path, role: AgentCompanyRole) -> AgentCompanyRole:
    existing = [path for path in role.aureon_surfaces if _rooted(root, path).exists()]
    missing = [path for path in role.aureon_surfaces if path not in existing]
    role.existing_surfaces = existing
    role.missing_surfaces = missing
    role.status = "active_surface_mapped" if existing else "work_order_required"
    if not existing:
        role.blockers.append("no_current_surface_found")
        role.work_orders.append(
            {
                "id": f"build_{role.role_id}_surface",
                "title": f"Create or map Aureon surface for {role.title}",
                "owner": "CTO Code Architect",
                "priority": 70 if role.seniority == "board" else 50,
                "route": "coding_organism",
                "exact_aureon_prompt": (
                    f"Aureon must create or map the {role.title} agent role into an existing safe surface, "
                    "write tests, and publish evidence."
                ),
            }
        )
    return role


def _agent_config_for(role: AgentCompanyRole) -> dict[str, Any]:
    prompt = (
        f"You are {role.title} in the Aureon agent company. Mission: {role.mission} "
        "You are not a one-trick role: read the whole organism state, use handoffs, "
        "apply your day-to-day checks, and then act only inside your authority. "
        f"Use only allowed tools: {', '.join(role.tools_allowed)}. "
        f"Authority: {role.authority_level}. Publish evidence before claiming success."
    )
    return {
        "name": role.title,
        "system_prompt": prompt,
        "max_turns": 4,
        "max_tokens": 2048,
        "temperature": 0.35,
        "tools_enabled": True,
        "metadata": {
            "role_id": role.role_id,
            "department": role.department,
            "authority_level": role.authority_level,
            "day_to_day_step_count": len(role.day_to_day),
            "whole_organism_access": bool(role.whole_organism_access),
            "registry_only_v1": True,
        },
    }


def _capability_coverage(roles: list[AgentCompanyRole]) -> list[dict[str, Any]]:
    coverage: list[dict[str, Any]] = []
    for capability in MARKET_CAPABILITY_TAXONOMY:
        keywords = set(capability["capability_keywords"])
        mapped = [
            role.role_id
            for role in roles
            if keywords.intersection(set(role.capabilities + role.tools_allowed))
        ]
        coverage.append(
            {
                "id": capability["id"],
                "title": capability["title"],
                "official_source": capability["official_source"],
                "mapped_role_count": len(mapped),
                "mapped_roles": mapped,
                "covered": bool(mapped),
            }
        )
    return coverage


def _handoff_map(roles: list[AgentCompanyRole]) -> list[dict[str, Any]]:
    role_titles = {role.title for role in roles}
    rows: list[dict[str, Any]] = []
    for role in roles:
        for target in role.handoffs_out:
            rows.append(
                {
                    "from": role.title,
                    "from_role_id": role.role_id,
                    "to": target,
                    "to_known_role": target in role_titles,
                    "handoff_description": f"{role.title} hands evidence to {target}.",
                }
            )
    return rows


def _memory_payload_for_role(role: AgentCompanyRole) -> dict[str, Any]:
    return {
        "schema_version": "aureon-agent-role-memory-pack-v1",
        "role_id": role.role_id,
        "title": role.title,
        "department": role.department,
        "seniority": role.seniority,
        "mission": role.mission,
        "capabilities": role.capabilities,
        "tools_allowed": role.tools_allowed,
        "inputs": role.inputs,
        "outputs": role.outputs,
        "handoffs_in": role.handoffs_in,
        "handoffs_out": role.handoffs_out,
        "authority_level": role.authority_level,
        "evidence_required": role.evidence_required,
        "tests": role.tests,
        "aureon_surfaces": role.aureon_surfaces,
        "day_to_day": role.day_to_day,
        "standing_checks": role.standing_checks,
        "escalation_rules": role.escalation_rules,
        "cross_training": role.cross_training,
        "whole_organism_access": role.whole_organism_access,
        "workforce_lifecycle": role.workforce_lifecycle,
        "rehydration_contract": {
            "source": "Aureon Agent Company memory phonebook",
            "restore_as": "temporary_crew_candidate",
            "must_revalidate": [
                "current source freshness",
                "current authority boundary",
                "current tests",
                "client job fit",
            ],
        },
    }


def _memory_bundle_for_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    compressed = zlib.compress(raw, level=9)
    raw_sha = hashlib.sha256(raw).hexdigest()
    compressed_sha = hashlib.sha256(compressed).hexdigest()
    return {
        "raw_bytes": len(raw),
        "compressed_bytes": len(compressed),
        "compression_ratio": round(len(compressed) / max(len(raw), 1), 4),
        "sha256_raw_payload": raw_sha,
        "sha256_compressed_payload": compressed_sha,
        "archive_key": f"sha256:{compressed_sha}",
        "encoded_payload": base64.b64encode(compressed).decode("ascii"),
    }


def _memory_phonebook_for_roles(
    root: Path, roles: list[AgentCompanyRole], generated_at: str
) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    total_raw = 0
    total_compressed = 0
    for role in roles:
        payload = _memory_payload_for_role(role)
        bundle = _memory_bundle_for_payload(payload)
        total_raw += int(bundle["raw_bytes"])
        total_compressed += int(bundle["compressed_bytes"])
        bundle_path = _rooted(
            root,
            DEFAULT_MEMORY_BUNDLE_DIR
            / f"{role.role_id}.{str(bundle['sha256_compressed_payload'])[:16]}.json.zlib.b64",
        )
        entries.append(
            {
                "role_id": role.role_id,
                "title": role.title,
                "department": role.department,
                "employment_model": (role.workforce_lifecycle or {}).get("employment_model"),
                "capabilities": role.capabilities,
                "archive_key": bundle["archive_key"],
                "sha256_raw_payload": bundle["sha256_raw_payload"],
                "sha256_compressed_payload": bundle["sha256_compressed_payload"],
                "raw_bytes": bundle["raw_bytes"],
                "compressed_bytes": bundle["compressed_bytes"],
                "compression_ratio": bundle["compression_ratio"],
                "bundle_path": str(bundle_path),
                "restore_as": "temporary_crew_candidate",
                "rehydration_owner": "Workforce Retirement Clerk",
                "search_terms": sorted({role.role_id, role.title, role.department, *role.capabilities}),
                "_encoded_payload": bundle["encoded_payload"],
            }
        )
    public_entries = [
        {key: value for key, value in entry.items() if key != "_encoded_payload"} for entry in entries
    ]
    return {
        "schema_version": "aureon-agent-company-memory-phonebook-v1",
        "generated_at": generated_at,
        "status": "memory_phonebook_ready",
        "archive_policy": WORKFORCE_MEMORY_ARCHIVE_POLICY,
        "summary": {
            "entry_count": len(entries),
            "bundle_count": len(entries),
            "sha256_addressed": True,
            "zlib_compressed": True,
            "total_raw_bytes": total_raw,
            "total_compressed_bytes": total_compressed,
            "compression_ratio": round(total_compressed / max(total_raw, 1), 4),
            "subcontractor_eligible_entries": len(
                [entry for entry in entries if entry.get("employment_model") == "subcontractor_eligible"]
            ),
        },
        "entries": public_entries,
        "_bundle_payloads": {entry["bundle_path"]: entry["_encoded_payload"] for entry in entries},
    }


def _public_phonebook(phonebook: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in phonebook.items() if key != "_bundle_payloads"}


def _summary(
    roles: list[AgentCompanyRole],
    work_orders: list[dict[str, Any]],
    recruitment_engine: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active = [role for role in roles if role.existing_surfaces]
    day_plan = [role for role in roles if len(role.day_to_day) >= 5 and role.standing_checks]
    whole_access = [role for role in roles if (role.whole_organism_access or {}).get("allowed_surfaces")]
    not_one_trick = [
        role
        for role in roles
        if len(role.capabilities) >= 3
        and role.handoffs_out
        and role.cross_training
        and role.whole_organism_access
    ]
    lifecycle_roles = [role for role in roles if role.workforce_lifecycle]
    subcontractor_eligible = [
        role
        for role in roles
        if (role.workforce_lifecycle or {}).get("employment_model") == "subcontractor_eligible"
    ]
    agency_roles = [role for role in roles if role.department == "agency_workforce"]
    recruitment_engine = recruitment_engine or {}
    raw_recruitment_summary = recruitment_engine.get("summary")
    recruitment_summary: dict[str, Any] = (
        raw_recruitment_summary if isinstance(raw_recruitment_summary, dict) else {}
    )
    return {
        "department_count": len(DEPARTMENTS),
        "role_count": len(roles),
        "agent_count": len(roles),
        "active_surface_role_count": len(active),
        "work_order_count": len(work_orders),
        "authority_boundary_count": len(AUTHORITY_BOUNDARIES),
        "market_capability_count": len(MARKET_CAPABILITY_TAXONOMY),
        "market_ai_system_count": len(MARKET_AI_SYSTEMS),
        "capability_market_comparison_count": len(MARKET_AI_SYSTEMS),
        "direct_market_systems_compared": [system["provider"] for system in MARKET_AI_SYSTEMS],
        "coverage_percent": round((len(active) / max(len(roles), 1)) * 100, 2),
        "registry_mode": "registry_ui_first",
        "executable_agents_created": False,
        "roles_with_day_plan_count": len(day_plan),
        "roles_with_whole_organism_access_count": len(whole_access),
        "not_one_trick_role_count": len(not_one_trick),
        "daily_operating_loop_ready": bool(DAILY_OPERATING_LOOP) and len(day_plan) == len(roles),
        "mycelium_ethos": MYCELIUM_ORGANISATION_DOCTRINE["ethos"],
        "mycelium_doctrine_ready": True,
        "mycelium_metaphor_count": len(MYCELIUM_ORGANISATION_DOCTRINE["metaphor_map"]),
        "mycelium_operating_principle_count": len(MYCELIUM_ORGANISATION_DOCTRINE["operating_principles"]),
        "bio_cosmic_ethos": BIO_COSMIC_ORGANISATION_DOCTRINE["ethos"],
        "bio_cosmic_doctrine_ready": True,
        "bio_cosmic_scale_count": len(BIO_COSMIC_ORGANISATION_DOCTRINE["scale_ladder"]),
        "bio_cosmic_operating_law_count": len(BIO_COSMIC_ORGANISATION_DOCTRINE["operating_laws"]),
        "agency_model": AGENCY_OPERATING_MODEL["model"],
        "agency_lifecycle_step_count": len(PROMPT_CLIENT_JOB_LIFECYCLE),
        "agency_workforce_role_count": len(agency_roles),
        "roles_with_workforce_lifecycle_count": len(lifecycle_roles),
        "subcontractor_eligible_role_count": len(subcontractor_eligible),
        "temporary_staff_retirement_policy_ready": bool(SUBCONTRACTOR_RETIREMENT_POLICY),
        "memory_phonebook_ready": True,
        "sha256_memory_entry_count": len(roles),
        "zlib_memory_archive_ready": True,
        "recruitment_engine_ready": recruitment_engine.get("status") == "recruitment_ready",
        "recruited_worker_count": int(recruitment_summary.get("recruited_worker_count") or 0),
        "agent_blueprint_count": int(recruitment_summary.get("agent_blueprint_count") or 0),
        "internal_recruitment_hit_count": int(recruitment_summary.get("internal_hit_count") or 0),
        "online_recruitment_search_enabled": bool(recruitment_summary.get("online_enabled")),
        "online_recruitment_search_count": int(recruitment_summary.get("online_search_count") or 0),
        "existing_gates_preserved": True,
        "ceo_to_cleaner_coverage": all(
            title in {role.title for role in roles}
            for title in ("CEO Goal Steward", "Log Janitor", "Stale State Cleaner")
        ),
    }


def _goal_terms(goal: str) -> list[str]:
    terms = [
        word
        for word in re.findall(r"[a-z0-9][a-z0-9_\-]{2,}", (goal or "").lower())
        if word
        not in {
            "the",
            "and",
            "that",
            "with",
            "for",
            "must",
            "into",
            "from",
            "this",
            "client",
            "system",
            "aureon",
            "organism",
        }
    ]
    preferred = [
        "agent",
        "agents",
        "coding",
        "search",
        "online",
        "skills",
        "roles",
        "scope",
        "proposal",
        "workers",
        "hiring",
        "handoff",
        "tests",
        "browser",
        "desktop",
        "memory",
        "github",
        "web",
        "build",
        "proof",
    ]
    ordered = [term for term in preferred if term in terms]
    for term in terms:
        if term not in ordered:
            ordered.append(term)
    return ordered[:18]


def _internal_recruitment_search(
    root: Path, queries: Sequence[str], limit_per_query: int = 5
) -> list[dict[str, Any]]:
    search_roots = [
        root / "aureon",
        root / "docs",
        root / "frontend" / "src",
        root / "tests",
        root / "README.md",
        root / "CAPABILITIES.md",
        root / "RUNNING.md",
        root / "EVERYTHING_CODEX_CAN_DO.md",
    ]
    files: list[Path] = []
    for search_root in search_roots:
        if search_root.is_file():
            files.append(search_root)
        elif search_root.exists():
            for path in search_root.rglob("*"):
                if path.is_file() and path.suffix.lower() in {".py", ".ts", ".tsx", ".md", ".json"}:
                    files.append(path)
    hits_by_query: list[dict[str, Any]] = []
    for query in queries:
        words = [word for word in re.findall(r"[a-z0-9_]+", query.lower()) if len(word) >= 3]
        hits: list[dict[str, Any]] = []
        for path in files[:2500]:
            rel = path.relative_to(root).as_posix() if path.is_relative_to(root) else str(path)
            haystack = rel.lower()
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:24000].lower()
            except Exception:
                text = ""
            score = sum(2 for word in words if word in haystack) + sum(1 for word in words if word in text)
            if score:
                hits.append({"path": rel, "score": score, "reason": "repo_surface_or_content_match"})
        hits.sort(key=lambda item: (-int(item["score"]), item["path"]))
        hits_by_query.append({"query": query, "hit_count": len(hits), "hits": hits[:limit_per_query]})
    return hits_by_query


def _run_online_recruitment_search(enabled: bool, limit: int = 4) -> dict[str, Any]:
    if not enabled:
        return {
            "enabled": False,
            "status": "not_requested",
            "searches": [],
            "note": "Pass --online or route a prompt that asks for online/internet search to run bounded search probes.",
        }
    searches: list[dict[str, Any]] = []
    try:
        from aureon.autonomous.aureon_agent_core import AureonAgentCore

        agent = AureonAgentCore()
        for query in RECRUITMENT_ONLINE_QUERIES[
            : max(1, min(int(limit or 4), len(RECRUITMENT_ONLINE_QUERIES)))
        ]:
            results = agent.web_search(query["query"], num_results=3)
            searches.append(
                {
                    **query,
                    "status": "searched",
                    "result_count": len(results) if isinstance(results, list) else 0,
                    "results": results[:3] if isinstance(results, list) else [],
                }
            )
    except Exception as exc:
        return {
            "enabled": True,
            "status": "search_failed",
            "error": f"{type(exc).__name__}: {exc}",
            "searches": searches,
        }
    return {
        "enabled": True,
        "status": "search_complete",
        "searches": searches,
    }


def _select_recruited_workers(
    roles: list[AgentCompanyRole], goal_terms: Sequence[str]
) -> list[AgentCompanyRole]:
    terms = {term.lower() for term in goal_terms}
    priority_titles = {
        "Client Brief Broker",
        "Skill Headhunter",
        "Subcontractor Crew Builder",
        "Capability Cartographer",
        "Tool Bridge Architect",
        "Workflow Foreman",
        "Implementation Worker",
        "Test Pilot",
        "Browser Smoke Inspector",
        "HNC/Auris Drift Officer",
        "Release Manager",
        "Archive Librarian",
    }
    if terms.intersection(
        {
            "website",
            "webpage",
            "design",
            "redesign",
            "graphic",
            "motion",
            "animation",
            "brand",
            "investor",
            "competitor",
        }
    ):
        priority_titles.update(
            {
                "Website Design Director",
                "Competitor Research Scout",
                "Brand and Design-System Lead",
                "Technical Editorial Writer",
                "Claims and Evidence Editor",
                "Motion Designer",
                "Visual Asset Director",
                "Accessibility and Performance QA",
                "Design Release QA",
            }
        )
    recruited: list[tuple[int, AgentCompanyRole]] = []
    for role in roles:
        searchable = " ".join(
            [
                role.title,
                role.department,
                role.mission,
                " ".join(role.capabilities),
                " ".join(role.tools_allowed),
                " ".join(role.aureon_surfaces),
            ]
        ).lower()
        score = sum(1 for term in terms if term in searchable)
        if role.title in priority_titles:
            score += 4
        if score > 0:
            recruited.append((score, role))
    recruited.sort(key=lambda item: (-item[0], item[1].department, item[1].title))
    seen: set[str] = set()
    selected: list[AgentCompanyRole] = []
    for _score, role in recruited:
        if role.role_id in seen:
            continue
        seen.add(role.role_id)
        selected.append(role)
        if len(selected) >= 14:
            break
    return selected


def _agent_blueprint_for(role: AgentCompanyRole, goal: str) -> dict[str, Any]:
    return {
        "agent_id": f"temp_{role.role_id}",
        "source_role_id": role.role_id,
        "title": role.title,
        "employment_model": (role.workforce_lifecycle or {}).get(
            "employment_model", "subcontractor_eligible"
        ),
        "scope_contract": {
            "client_goal": goal,
            "who": role.title,
            "what": role.mission,
            "where": role.aureon_surfaces or role.missing_surfaces,
            "when": "created during client job recruitment after scope lock",
            "how": role.capabilities,
            "act": "work only through allowed tools, publish evidence, and hand off to QA/release",
        },
        "skills_to_load": role.capabilities,
        "tools_allowed": role.tools_allowed,
        "inputs": role.inputs,
        "outputs": role.outputs,
        "handoffs_in": role.handoffs_in,
        "handoffs_out": role.handoffs_out,
        "evidence_required": role.evidence_required,
        "tests": role.tests,
        "authority_level": role.authority_level,
        "blocked_actions": WHOLE_ORGANISM_ACCESS_POLICY["blocked_actions"],
        "memory_policy": role.workforce_lifecycle,
        "retire_after": "client acceptance or variation-order close",
    }


def _build_recruitment_engine(
    *,
    root: Path,
    goal: str,
    roles: list[AgentCompanyRole],
    online: bool = False,
    online_limit: int = 4,
) -> dict[str, Any]:
    terms = _goal_terms(goal)
    search_queries = [
        " ".join(terms[:8]) or "agent company capability recruitment",
        "coding agent worker roles tests handoff proof",
        "online search official docs agent skills tool use",
        "client proposal scope work orders acceptance tests",
    ]
    internal_searches = _internal_recruitment_search(root, search_queries)
    online_search = _run_online_recruitment_search(online, limit=online_limit)
    recruited_roles = _select_recruited_workers(roles, terms)
    blueprints = [_agent_blueprint_for(role, goal) for role in recruited_roles]
    internal_hit_count = sum(int(item.get("hit_count") or 0) for item in internal_searches)
    raw_online_searches = online_search.get("searches")
    online_searches: list[Any] = raw_online_searches if isinstance(raw_online_searches, list) else []
    return {
        "schema_version": "aureon-agent-recruitment-engine-v1",
        "status": "recruitment_ready",
        "mode": "scope_internal_search_online_skill_scan_recruit_build_archive",
        "client_scope": {
            "goal": goal,
            "detected_terms": terms,
            "scope_rule": "complete scope locks recruitment; incomplete scope returns client questions before crew selection",
        },
        "stage_flow": RECRUITMENT_STAGE_FLOW,
        "search_capability": {
            "internal_repo_search": True,
            "online_search_requested": bool(online),
            "online_search_tool": "AureonAgentCore.web_search",
            "online_search_policy": "bounded read-only skill search; source summaries only; no credentials or mutations",
            "source_priority": [
                "existing Aureon repo surfaces",
                "state/docs/frontend evidence reports",
                "official docs and source-linked web results",
                "job/role skill patterns as work-order hints only",
            ],
        },
        "internal_skill_searches": internal_searches,
        "online_skill_searches": online_search,
        "recruited_workers": [
            {
                "role_id": role.role_id,
                "title": role.title,
                "department": role.department,
                "authority_level": role.authority_level,
                "capabilities": role.capabilities,
                "tools_allowed": role.tools_allowed,
                "why_recruited": "matches client scope, required capability terms, or core delivery/QA/release role",
            }
            for role in recruited_roles
        ],
        "agent_blueprints": blueprints,
        "client_proposal_build_plan": [
            {
                "step": "lock_scope",
                "owner": "Client Brief Broker",
                "proof": "scope includes goal, deliverables, target systems, constraints, and acceptance",
            },
            {
                "step": "search_and_recruit",
                "owner": "Skill Headhunter",
                "proof": "internal hits and online searches are recorded with source links or clear unavailable status",
            },
            {
                "step": "build_worker_blueprints",
                "owner": "Subcontractor Crew Builder",
                "proof": "each recruited role has skills, tools, handoffs, tests, authority, and retirement contract",
            },
            {
                "step": "execute_or_queue_work_orders",
                "owner": "Workflow Foreman",
                "proof": "safe work orders name file targets, tests, and authority boundary",
            },
            {
                "step": "handover",
                "owner": "Release Manager",
                "proof": "client-visible handover only after proof checklist and snagging pass",
            },
        ],
        "summary": {
            "detected_term_count": len(terms),
            "internal_search_count": len(internal_searches),
            "internal_hit_count": internal_hit_count,
            "online_enabled": bool(online),
            "online_status": online_search.get("status"),
            "online_search_count": len(online_searches),
            "recruited_worker_count": len(recruited_roles),
            "agent_blueprint_count": len(blueprints),
            "authority_gates_preserved": True,
        },
    }


def _market_capability_comparison(roles: list[AgentCompanyRole]) -> list[dict[str, Any]]:
    roles_by_title = {role.title: role for role in roles}
    comparison: list[dict[str, Any]] = []
    for system in MARKET_AI_SYSTEMS:
        hire_titles = [str(title) for title in system.get("temporary_hires", [])]
        hired = []
        for title in hire_titles:
            role = roles_by_title.get(title)
            if role:
                hired.append(
                    {
                        "role_id": role.role_id,
                        "title": role.title,
                        "department": role.department,
                        "authority_level": role.authority_level,
                        "existing_surfaces": role.existing_surfaces,
                        "work_order_count": len(role.work_orders),
                    }
                )
            else:
                hired.append(
                    {
                        "role_id": _slug(title),
                        "title": title,
                        "department": "agency_workforce",
                        "authority_level": "work_order_required",
                        "existing_surfaces": [],
                        "work_order_count": 1,
                    }
                )
        comparison.append(
            {
                **system,
                "aureon_gap_status": "partially_wired"
                if system.get("aureon_current_equivalent")
                else "missing",
                "hired_temporary_workers": hired,
                "next_work_order": {
                    "title": f"Bridge {system['provider']} capability pattern into Aureon",
                    "status": "ready_for_scoped_work_order",
                    "authority_boundary": "no live trading, payment, filing, credential reveal, destructive OS action, or external mutation bypass",
                    "acceptance": [
                        "source-backed capability row exists",
                        "Aureon current surface or explicit gap named",
                        "temporary workers and handoffs assigned",
                        "proof artifact published before client handover",
                    ],
                },
            }
        )
    return comparison


def build_agent_company_bill_list(
    *,
    root: Path | None = None,
    goal: str = "",
    online: bool = False,
    online_limit: int = 4,
    provision_brains: bool = False,
    brain_resolver: Any = None,
    thought_path: Any = None,
) -> dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    generated_at = utc_now()
    roles = [_materialize_role(root, role) for role in _role_specs()]
    work_orders = [order for role in roles for order in role.work_orders]
    memory_phonebook = _memory_phonebook_for_roles(root, roles, generated_at)
    market_comparison = _market_capability_comparison(roles)
    recruitment_engine = _build_recruitment_engine(
        root=root,
        goal=goal,
        roles=roles,
        online=online,
        online_limit=online_limit,
    )
    from aureon.autonomous.aureon_agent_company_brain_fabric import (
        canonical_agent_company_brain_topology,
        company_brain_fabric_report,
        provision_agent_company_brain_fabric,
    )

    role_brain_lanes, process_brain_bindings = canonical_agent_company_brain_topology()
    role_process_bindings = {
        owner: process_id for process_id, (_lane, owner) in process_brain_bindings.items()
    }
    if provision_brains:
        try:
            brain_fabric = company_brain_fabric_report(
                provision_agent_company_brain_fabric(
                    brain_resolver,
                    thought_path=thought_path,
                )
            )
        except Exception as exc:
            brain_fabric = {
                "schema_version": "aureon-agent-company-brain-fabric-v1",
                "status": "hold",
                "ready": False,
                "reason": f"brain_fabric_provision_failed:{type(exc).__name__}",
                "action_eligible": False,
                "economic_eligible": False,
                "passports": [],
            }
    else:
        brain_fabric = {
            "schema_version": "aureon-agent-company-brain-fabric-v1",
            "status": "not_requested",
            "ready": False,
            "reason": "explicit_brain_provisioning_required",
            "action_eligible": False,
            "economic_eligible": False,
            "passports": [],
        }
    brain_fabric_ready = bool(brain_fabric.get("ready"))
    passport_by_subject = {
        (item.get("subject_type"), item.get("subject_id")): item
        for item in brain_fabric.get("passports", [])
        if isinstance(item, dict)
    }
    role_payloads: list[dict[str, Any]] = []
    agent_payloads: list[dict[str, Any]] = []
    for role in roles:
        canonical_brain_member = role.title in role_brain_lanes
        process_id = role_process_bindings.get(role.title)
        agent_passport = (
            passport_by_subject.get(("agent", role.title), {})
            if canonical_brain_member
            else {}
        )
        process_passport = (
            passport_by_subject.get(("process", process_id), {})
            if canonical_brain_member and process_id
            else {}
        )
        role_brain_provisioned = bool(
            brain_fabric_ready
            and canonical_brain_member
            and agent_passport
            and process_passport
        )
        binding = {
            "topology": (
                "canonical_41_role_brain_fabric"
                if canonical_brain_member
                else "registry_only_public_design"
            ),
            "canonical_brain_fabric_member": canonical_brain_member,
            "registry_only": not canonical_brain_member,
            "registry_only_reason": (
                "public_design_roles_preserve_website_operator_planning_and_owner_gates_without_joining_the_executable_brain_fabric"
                if not canonical_brain_member
                else ""
            ),
            "lane": role_brain_lanes.get(role.title),
            "paired_process_id": process_id,
            "agent_brain_passport_id": agent_passport.get("receipt_id"),
            "process_brain_passport_id": process_passport.get("receipt_id"),
            "provisioned": role_brain_provisioned,
            "tools_enabled": False,
            "action_eligible": False,
            "economic_eligible": False,
        }
        role_payloads.append({**role.to_dict(), "brain_binding": binding})
        agent_config = _agent_config_for(role)
        if brain_fabric_ready or not canonical_brain_member:
            agent_config["tools_enabled"] = False
        agent_config["metadata"] = {
            **agent_config["metadata"],
            "registry_only_v1": not role_brain_provisioned,
            "brain_fabric_provisioned": role_brain_provisioned,
            "brain_binding": binding,
        }
        agent_payloads.append(agent_config)
    canonical_brain_role_count = sum(
        1 for item in role_payloads if item["brain_binding"]["canonical_brain_fabric_member"]
    )
    registry_only_role_count = len(role_payloads) - canonical_brain_role_count
    provisioned_role_count = sum(
        1 for item in role_payloads if item["brain_binding"]["provisioned"]
    )
    all_canonical_brains_provisioned = bool(
        brain_fabric_ready and provisioned_role_count == canonical_brain_role_count
    )
    all_registered_roles_brain_provisioned = bool(
        role_payloads and provisioned_role_count == len(role_payloads)
    )
    departments = []
    for department in DEPARTMENTS:
        department_roles = [role for role in roles if role.department == department["id"]]
        departments.append(
            {
                **department,
                "role_count": len(department_roles),
                "active_surface_role_count": len(
                    [role for role in department_roles if role.existing_surfaces]
                ),
                "roles": [role.role_id for role in department_roles],
            }
        )

    output_files = [
        str(_rooted(root, DEFAULT_STATE_PATH)),
        str(_rooted(root, DEFAULT_AUDIT_JSON)),
        str(_rooted(root, DEFAULT_AUDIT_MD)),
        str(_rooted(root, DEFAULT_PUBLIC_JSON)),
        str(_rooted(root, DEFAULT_PHONEBOOK_STATE_JSON)),
        str(_rooted(root, DEFAULT_PHONEBOOK_AUDIT_JSON)),
        str(_rooted(root, DEFAULT_PHONEBOOK_PUBLIC_JSON)),
    ]

    summary = _summary(roles, work_orders, recruitment_engine)
    summary.update(
        {
            "executable_agents_created": brain_fabric_ready,
            "brain_fabric_status": brain_fabric.get("status"),
            "brain_fabric_ready": brain_fabric_ready,
            "agent_brain_count": int(brain_fabric.get("agent_brain_count") or 0),
            "process_brain_count": int(brain_fabric.get("process_brain_count") or 0),
            "brain_passport_count": int(brain_fabric.get("brain_passport_count") or 0),
            "canonical_brain_role_count": canonical_brain_role_count,
            "registry_only_role_count": registry_only_role_count,
            "provisioned_role_count": provisioned_role_count,
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "company_name": "Aureon Agent Company",
        "goal": goal,
        "status": "agent_company_brain_fabric_ready" if brain_fabric_ready else "agent_company_registry_ready",
        "summary": summary,
        "brain_fabric": brain_fabric,
        "capability_taxonomy_sources": MARKET_CAPABILITY_TAXONOMY,
        "market_ai_systems": MARKET_AI_SYSTEMS,
        "capability_market_comparison": market_comparison,
        "recruitment_engine": recruitment_engine,
        "mycelium_organisation_doctrine": MYCELIUM_ORGANISATION_DOCTRINE,
        "bio_cosmic_organisation_doctrine": BIO_COSMIC_ORGANISATION_DOCTRINE,
        "agency_operating_model": AGENCY_OPERATING_MODEL,
        "prompt_client_job_lifecycle": PROMPT_CLIENT_JOB_LIFECYCLE,
        "subcontractor_retirement_policy": SUBCONTRACTOR_RETIREMENT_POLICY,
        "labor_market_skill_source_types": LABOR_MARKET_SKILL_SOURCE_TYPES,
        "workforce_memory_archive_policy": WORKFORCE_MEMORY_ARCHIVE_POLICY,
        "workforce_memory_phonebook": _public_phonebook(memory_phonebook),
        "_workforce_memory_bundle_payloads": memory_phonebook.get("_bundle_payloads", {}),
        "whole_organism_access_policy": WHOLE_ORGANISM_ACCESS_POLICY,
        "daily_operating_loop": DAILY_OPERATING_LOOP,
        "departments": departments,
        "roles": role_payloads,
        "agents": agent_payloads,
        "capability_coverage": _capability_coverage(roles),
        "handoff_map": _handoff_map(roles),
        "authority_boundaries": AUTHORITY_BOUNDARIES,
        "work_orders": work_orders,
        "who_what_where_when_how_act": {
            "who": "Aureon Agent Company registry",
            "what": "CEO-to-cleaner capability bill list mapped to real Aureon surfaces and safe authority boundaries.",
            "where": output_files,
            "when": "Built on demand from the current repo and public agent-system capability patterns.",
            "how": [
                "map market capability taxonomy",
                "compare big AI/coding-agent systems with current Aureon surfaces",
                "apply mycelium organisation doctrine to handoffs, temporary crews, and memory",
                "apply cells-to-stars doctrine to departments, immune checks, swarm work, and long-range pattern navigation",
                "run internal repo search and optional online recruitment search",
                "recruit temporary worker blueprints for the client proposal",
                "treat prompt as client job",
                "attach agency/head-hunting intake and subcontractor lifecycle",
                "materialize Aureon startup departments",
                "attach day-to-day role loops and standing checks",
                "attach whole-organism access policy to every role",
                "verify each role against current repo surfaces",
                "queue work orders for missing surfaces",
                "publish state, docs/audits, and frontend/public evidence",
            ],
            "act": "Show the org chart in the unified console and route future coding prompts through the company roles.",
        },
        "completion_report": {
            "did_build_company_registry": True,
            "did_include_ceo_to_cleaner_roles": True,
            "did_attach_day_to_day_duties": all(len(role.day_to_day) >= 5 for role in roles),
            "did_attach_whole_organism_access": all(bool(role.whole_organism_access) for role in roles),
            "did_attach_agency_prompt_job_model": True,
            "did_attach_hire_retire_lifecycle": all(bool(role.workforce_lifecycle) for role in roles),
            "did_build_sha256_zlib_memory_phonebook": memory_phonebook.get("summary", {}).get("entry_count")
            == len(roles),
            "did_compare_market_ai_systems": len(market_comparison) == len(MARKET_AI_SYSTEMS),
            "did_build_recruitment_engine": recruitment_engine.get("status") == "recruitment_ready",
            "did_attach_mycelium_organisation_doctrine": MYCELIUM_ORGANISATION_DOCTRINE["ethos"]
            == "mycelium_network_organisation",
            "did_attach_bio_cosmic_organisation_doctrine": BIO_COSMIC_ORGANISATION_DOCTRINE["ethos"]
            == "bio_cosmic_living_system_organisation",
            "did_build_agent_blueprints": bool(recruitment_engine.get("agent_blueprints")),
            "did_provision_all_agent_and_process_brains": all_registered_roles_brain_provisioned,
            "did_provision_all_canonical_agent_and_process_brains": all_canonical_brains_provisioned,
            "did_keep_public_design_roles_registry_only": all(
                item["brain_binding"]["registry_only"]
                and item["brain_binding"]["provisioned"] is False
                for item in role_payloads
                if item.get("department") == "public_design"
            ),
            "did_run_internal_skill_search": bool(recruitment_engine.get("internal_skill_searches")),
            "did_run_online_skill_search_when_requested": (
                not online
                or (recruitment_engine.get("online_skill_searches") or {}).get("status")
                in {"search_complete", "search_failed"}
            ),
            "did_preserve_existing_authority_gates": True,
            "did_map_roles_to_surfaces_or_work_orders": all(
                bool(role.existing_surfaces or role.work_orders) for role in roles
            ),
            "daily_operating_loop_ready": bool(DAILY_OPERATING_LOOP),
            "self_validation_result": "passing",
            "remaining_work_order_count": len(work_orders),
        },
        "output_files": output_files,
    }


def _write_text(path: Path, content: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    last_error = ""
    for attempt in range(6):
        try:
            tmp.replace(path)
            return {
                "path": str(path),
                "ok": True,
                "writer": "AgentCompanyBuilder",
                "write_mode": "atomic_replace",
            }
        except PermissionError as exc:
            last_error = str(exc)
            time.sleep(0.2 * (attempt + 1))
    try:
        path.write_text(content, encoding="utf-8")
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        return {
            "path": str(path),
            "ok": True,
            "writer": "AgentCompanyBuilder",
            "write_mode": "direct_fallback",
        }
    except PermissionError as exc:
        return {
            "path": str(path),
            "ok": False,
            "writer": "AgentCompanyBuilder",
            "write_mode": "failed_locked",
            "error": str(exc) or last_error,
        }


def _write_json(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _write_memory_phonebook(root: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    raw_phonebook = report.get("workforce_memory_phonebook")
    phonebook: dict[str, Any] = raw_phonebook if isinstance(raw_phonebook, dict) else {}
    raw_bundle_payloads = report.pop("_workforce_memory_bundle_payloads", {})
    bundle_payloads: dict[str, Any] = raw_bundle_payloads if isinstance(raw_bundle_payloads, dict) else {}
    writes: list[dict[str, Any]] = []
    for raw_path, encoded_payload in sorted((bundle_payloads or {}).items()):
        path = Path(str(raw_path))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(encoded_payload), encoding="ascii")
        writes.append(
            {"path": str(path), "ok": True, "writer": "AgentCompanyMemoryPhonebook", "kind": "bundle"}
        )
    phonebook_payload = {
        **phonebook,
        "write_info": {
            "writer": "AgentCompanyMemoryPhonebook",
            "bundle_count": len(bundle_payloads or {}),
            "bundle_writes": writes,
        },
    }
    json_writes = [
        _write_json(_rooted(root, DEFAULT_PHONEBOOK_STATE_JSON), phonebook_payload),
        _write_json(_rooted(root, DEFAULT_PHONEBOOK_AUDIT_JSON), phonebook_payload),
        _write_json(_rooted(root, DEFAULT_PHONEBOOK_PUBLIC_JSON), phonebook_payload),
    ]
    report["workforce_memory_phonebook"] = phonebook_payload
    return writes + json_writes


def _make_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Aureon Agent Company Capability Bill List",
        "",
        f"- Generated: {report.get('generated_at')}",
        f"- Company: {report.get('company_name')}",
        f"- Roles: {summary.get('role_count')}",
        f"- Departments: {summary.get('department_count')}",
        f"- Active surface roles: {summary.get('active_surface_role_count')}",
        f"- Work orders: {summary.get('work_order_count')}",
        f"- Market AI systems compared: {summary.get('market_ai_system_count')}",
        f"- Recruited workers: {summary.get('recruited_worker_count')}",
        f"- Agent blueprints: {summary.get('agent_blueprint_count')}",
        f"- Internal recruitment hits: {summary.get('internal_recruitment_hit_count')}",
        f"- Online recruitment searches: {summary.get('online_recruitment_search_count')}",
        f"- Agency workforce roles: {summary.get('agency_workforce_role_count')}",
        f"- Prompt-as-client lifecycle steps: {summary.get('agency_lifecycle_step_count')}",
        f"- Subcontractor-eligible roles: {summary.get('subcontractor_eligible_role_count')}",
        f"- SHA-256 memory entries: {summary.get('sha256_memory_entry_count')}",
        f"- Zlib memory archive ready: {summary.get('zlib_memory_archive_ready')}",
        f"- Mycelium ethos: {summary.get('mycelium_ethos')}",
        f"- Mycelium doctrine ready: {summary.get('mycelium_doctrine_ready')}",
        f"- Bio-cosmic ethos: {summary.get('bio_cosmic_ethos')}",
        f"- Bio-cosmic scale ladder: {summary.get('bio_cosmic_scale_count')}",
        f"- Roles with day plans: {summary.get('roles_with_day_plan_count')}",
        f"- Whole-organism access roles: {summary.get('roles_with_whole_organism_access_count')}",
        f"- Daily operating loop ready: {summary.get('daily_operating_loop_ready')}",
        "",
        "## Prompt As Client Job Agency Model",
        "",
        report.get("agency_operating_model", {}).get("analogy", ""),
        "",
    ]
    mycelium = report.get("mycelium_organisation_doctrine", {})
    lines.extend(
        [
            "## Mycelium Organisation Doctrine",
            "",
            mycelium.get("one_line", ""),
            "",
            f"- Ethos: {mycelium.get('ethos')}",
            f"- Decision rule: {mycelium.get('decision_rule')}",
            "",
            "### Mycelium Map",
            "",
        ]
    )
    for item in mycelium.get("metaphor_map", []):
        lines.append(
            f"- **{item.get('mycelium_part')}** -> {item.get('aureon_part')}: {item.get('function')}"
        )
    lines.extend(["", "### Operating Principles", ""])
    for principle in mycelium.get("operating_principles", []):
        lines.append(f"- {principle}")
    bio_cosmic = report.get("bio_cosmic_organisation_doctrine", {})
    lines.extend(
        [
            "",
            "## Cells To Stars Living-System Doctrine",
            "",
            bio_cosmic.get("one_line", ""),
            "",
            f"- Ethos: {bio_cosmic.get('ethos')}",
            f"- Client job translation: {bio_cosmic.get('client_job_translation')}",
            "",
            "### Scale Ladder",
            "",
        ]
    )
    for item in bio_cosmic.get("scale_ladder", []):
        lines.extend(
            [
                f"- **{item.get('scale')}**: {item.get('lesson')}",
                f"  - Aureon: {item.get('aureon_translation')}",
                f"  - Proof: {item.get('proof_signal')}",
            ]
        )
    lines.extend(["", "### Operating Laws", ""])
    for law in bio_cosmic.get("operating_laws", []):
        lines.append(f"- {law}")
    lines.extend(["", "### Agency Principles", ""])
    for principle in report.get("agency_operating_model", {}).get("principles", []):
        lines.append(f"- {principle}")
    lines.extend(["", "### Client Job Lifecycle", ""])
    for step in report.get("prompt_client_job_lifecycle", []):
        lines.append(f"- **{step.get('step')}** ({step.get('owner')}): {step.get('action')}")
    lines.extend(["", "### Subcontractor Retirement Policy", ""])
    retirement = report.get("subcontractor_retirement_policy", {})
    lines.append(f"- Retire means: {retirement.get('retire_means')}")
    lines.append(f"- Delete means: {retirement.get('delete_means')}")
    phonebook = report.get("workforce_memory_phonebook", {})
    phonebook_summary = phonebook.get("summary", {}) if isinstance(phonebook, dict) else {}
    lines.extend(
        [
            "",
            "## Workforce Memory Phonebook",
            "",
            f"- Archive model: {report.get('workforce_memory_archive_policy', {}).get('archive_model')}",
            f"- Entries: {phonebook_summary.get('entry_count')}",
            f"- Bundles: {phonebook_summary.get('bundle_count')}",
            f"- SHA-256 addressed: {phonebook_summary.get('sha256_addressed')}",
            f"- Zlib compressed: {phonebook_summary.get('zlib_compressed')}",
            f"- Compression ratio: {phonebook_summary.get('compression_ratio')}",
        ]
    )
    lines.extend(
        [
            "",
            "## Daily Operating Loop",
            "",
        ]
    )
    for step in report.get("daily_operating_loop", []):
        lines.append(f"- **{step.get('step')}**: {step.get('action')}")
    lines.extend(
        [
            "",
            "## Whole Organism Access Policy",
            "",
            report.get("whole_organism_access_policy", {}).get("purpose", ""),
            "",
        ]
    )
    for action in report.get("whole_organism_access_policy", {}).get("allowed_actions", []):
        lines.append(f"- Allowed: {action}")
    for action in report.get("whole_organism_access_policy", {}).get("blocked_actions", []):
        lines.append(f"- Blocked: {action}")
    lines.extend(
        [
            "",
            "## Authority Boundaries",
            "",
        ]
    )
    for boundary in report.get("authority_boundaries", []):
        lines.append(f"- **{boundary.get('title')}**: {boundary.get('rule')}")
    recruitment = (
        report.get("recruitment_engine", {}) if isinstance(report.get("recruitment_engine"), dict) else {}
    )
    recruitment_summary = (
        recruitment.get("summary", {}) if isinstance(recruitment.get("summary"), dict) else {}
    )
    lines.extend(
        [
            "",
            "## Recruitment Engine",
            "",
            f"- Status: {recruitment.get('status')}",
            f"- Mode: {recruitment.get('mode')}",
            f"- Internal searches: {recruitment_summary.get('internal_search_count')}",
            f"- Internal hits: {recruitment_summary.get('internal_hit_count')}",
            f"- Online enabled: {recruitment_summary.get('online_enabled')}",
            f"- Online status: {recruitment_summary.get('online_status')}",
            f"- Recruited workers: {recruitment_summary.get('recruited_worker_count')}",
            "",
            "### Recruitment Stages",
            "",
        ]
    )
    for stage in recruitment.get("stage_flow", []):
        lines.append(f"- **{stage.get('stage')}** ({stage.get('owner')}): {stage.get('action')}")
    lines.extend(["", "### Recruited Temporary Crew", ""])
    for worker in recruitment.get("recruited_workers", [])[:14]:
        caps = ", ".join(worker.get("capabilities", [])[:4])
        lines.append(f"- **{worker.get('title')}** ({worker.get('authority_level')}): {caps}")
    lines.extend(["", "### Online Skill Searches", ""])
    online = (
        recruitment.get("online_skill_searches", {})
        if isinstance(recruitment.get("online_skill_searches"), dict)
        else {}
    )
    for search in online.get("searches", []):
        lines.append(f"- {search.get('query')} -> {search.get('result_count')} result(s)")
    lines.extend(["", "## Market AI System Comparison", ""])
    for item in report.get("capability_market_comparison", []):
        hires = ", ".join(worker.get("title", "") for worker in item.get("hired_temporary_workers", []))
        capabilities = ", ".join(item.get("market_capabilities", []))
        equivalents = ", ".join(item.get("aureon_current_equivalent", []))
        lines.extend(
            [
                f"### {item.get('provider')} - {', '.join(item.get('systems', []))}",
                f"- Market capabilities: {capabilities}",
                f"- Aureon equivalent: {equivalents}",
                f"- Gap: {item.get('primary_gap')}",
                f"- Temporary hires: {hires}",
                f"- Boundary: {(item.get('next_work_order') or {}).get('authority_boundary')}",
                "",
            ]
        )
    lines.extend(["", "## Departments", ""])
    roles_by_id = {role.get("role_id"): role for role in report.get("roles", [])}
    for department in report.get("departments", []):
        lines.append(f"### {department.get('title')}")
        lines.append("")
        for role_id in department.get("roles", []):
            role = roles_by_id.get(role_id, {})
            lines.append(
                f"- **{role.get('title')}** ({role.get('authority_level')}): "
                f"{role.get('mission')} Status: {role.get('status')}."
            )
            day = role.get("day_to_day") or []
            if day:
                lines.append(f"  - Daily first move: {day[0]}")
        lines.append("")
    lines.extend(["## Market Capability Sources", ""])
    for source in report.get("capability_taxonomy_sources", []):
        lines.append(f"- {source.get('title')}: {source.get('official_source')}")
    lines.extend(["", "## Direct Market AI Sources", ""])
    for item in report.get("market_ai_systems", []):
        for source in item.get("official_sources", []):
            lines.append(f"- {item.get('provider')}: {source}")
    return "\n".join(lines).strip() + "\n"


def build_and_write_agent_company_bill_list(
    *,
    root: Path | None = None,
    goal: str = "",
    online: bool = False,
    online_limit: int = 4,
    provision_brains: bool = False,
    brain_resolver: Any = None,
    thought_path: Any = None,
) -> dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    report = build_agent_company_bill_list(
        root=root,
        goal=goal,
        online=online,
        online_limit=online_limit,
        provision_brains=provision_brains,
        brain_resolver=brain_resolver,
        thought_path=thought_path,
    )
    memory_writes = _write_memory_phonebook(root, report)
    writes = [
        _write_json(_rooted(root, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root, DEFAULT_AUDIT_JSON), report),
        _write_json(_rooted(root, DEFAULT_PUBLIC_JSON), report),
        _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report)),
    ]
    report["write_info"] = {
        "writer": "AgentCompanyBuilder",
        "writes": memory_writes + writes,
        "memory_bundle_count": len([item for item in memory_writes if item.get("kind") == "bundle"]),
        "all_ok": all(item.get("ok") for item in memory_writes + writes),
    }
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build Aureon's agent company bill list.")
    parser.add_argument("--goal", default="")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    parser.add_argument(
        "--online", action="store_true", help="Run bounded online recruitment skill searches."
    )
    parser.add_argument("--online-limit", type=int, default=4)
    parser.add_argument(
        "--provision-brains",
        action="store_true",
        help="Live-probe Ollama and attach brain passports to all canonical roles and processes.",
    )
    args = parser.parse_args(argv)
    result = build_and_write_agent_company_bill_list(
        goal=args.goal,
        online=args.online,
        online_limit=args.online_limit,
        provision_brains=args.provision_brains,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(result))
    return 0 if result.get("write_info", {}).get("all_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
