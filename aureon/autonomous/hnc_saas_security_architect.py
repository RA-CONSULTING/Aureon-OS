"""HNC-led SaaS security architect for Aureon.

"Unhackable SaaS" is the internal north-star benchmark. Aureon must pursue it
by testing, stress testing, reviewing, trying safe authorized break-in
simulations against its own surfaces, finding weaknesses, fixing them, and
repeating the loop. Public claims and production deployment remain blocked until
the evidence gates are satisfied.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from aureon.obsidian_paths import resolve_obsidian_note_path


SCHEMA_VERSION = "aureon-hnc-saas-security-architect-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/hnc_saas_security_blueprint.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/hnc_saas_security_blueprint.json")
DEFAULT_CONTRACT_STATE = Path("state/hnc_saas_security_contracts.json")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/hnc_saas_security_blueprint.md")

SAFE_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_ALLOW_SIM_FALLBACK": "0",
    "AUREON_DISABLE_OFFICIAL_FILING": "1",
}

OFFICIAL_ANCHORS = {
    "owasp_asvs": "https://owasp.org/www-project-application-security-verification-standard/",
    "owasp_top_10": "https://owasp.org/www-project-top-ten/",
    "nist_zero_trust": "https://csrc.nist.gov/pubs/sp/800/207/final",
}

SKIP_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".pytest_cache",
    ".mypy_cache",
    "output",
}

HNC_MARKERS = (
    "hnc",
    "HNC",
    "Harmonic Nexus",
    "HarmonicNexus",
    "HNCSoup",
    "HNCAuris",
    "HNCGateway",
    "HNCQueen",
    "HNCValidator",
)

REQUIRED_SECURITY_DOMAINS = (
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
)

UNHACKABLE_PHASES = (
    "define_authorized_scope",
    "threat_model",
    "implement_control",
    "try_to_break_own_system",
    "stress_test",
    "record_vulnerability_or_proof",
    "queue_fix",
    "retest",
    "update_benchmark",
    "deployment_gate_review",
    "write_vault_memory",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root_from(start: Optional[Path] = None) -> Path:
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "aureon").is_dir() and (candidate / "scripts").is_dir():
            return candidate
    return Path(__file__).resolve().parents[2]


def apply_safe_environment() -> dict[str, str]:
    os.environ.update(SAFE_ENV)
    try:
        from aureon.core.aureon_runtime_safety import apply_safe_runtime_environment

        apply_safe_runtime_environment(os.environ)
    except Exception:
        pass
    return {key: os.environ.get(key, "") for key in SAFE_ENV}


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _skip_path(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def _read_sample(path: Path, max_chars: int = 24000) -> str:
    try:
        if path.stat().st_size > 3_000_000:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except Exception:
        return ""


def _classify_hnc_surface(rel_path: str, text: str) -> str:
    lower = rel_path.lower()
    joined = f"{lower}\n{text[:4000].lower()}"
    if "kings_accounting_suite" in lower or "hmrc" in joined or "cis" in joined or "vat" in joined:
        return "accounting_hnc"
    if "/strategies/" in lower or "\\strategies\\" in lower or "trading" in joined or "ticker" in joined:
        return "trading_hnc"
    if "/vault/" in lower or "\\vault\\" in lower or "obsidian" in joined:
        return "vault_memory_hnc"
    if "frontend" in lower or "supabase" in lower or "auth" in joined:
        return "frontend_identity_hnc"
    if "research" in lower or "whitepaper" in lower or "verification" in lower:
        return "research_evidence_hnc"
    if "test" in lower or "bench" in lower:
        return "validation_hnc"
    return "core_hnc"


def inventory_hnc_systems(root: Path) -> list[dict[str, Any]]:
    """Inventory HNC-related repo surfaces without importing or executing them."""

    surfaces: list[dict[str, Any]] = []
    candidates: list[Path] = []
    for pattern in ("*.py", "*.ts", "*.tsx", "*.md", "*.json"):
        candidates.extend(root.rglob(pattern))
    for path in sorted(set(candidates)):
        if _skip_path(path):
            continue
        rel_path = _rel(path, root)
        path_hit = any(marker.lower() in rel_path.lower() for marker in HNC_MARKERS)
        text = _read_sample(path)
        text_hit = any(marker in text for marker in HNC_MARKERS)
        if not (path_hit or text_hit):
            continue
        symbols = sorted(set(re.findall(r"\bHNC[A-Za-z0-9_]*\b|\bHarmonicNexus[A-Za-z0-9_]*\b", text)))[:16]
        surfaces.append(
            {
                "path": rel_path,
                "surface_type": _classify_hnc_surface(rel_path, text),
                "suffix": path.suffix,
                "symbols": symbols,
                "evidence": "path_marker" if path_hit and not text_hit else "content_marker",
            }
        )
    return surfaces


@dataclass
class SaaSSecurityControl:
    id: str
    domain: str
    title: str
    status: str
    risk: str
    requirement: str
    implementation_pattern: str
    verification: list[str] = field(default_factory=list)
    hnc_systems: list[str] = field(default_factory=list)
    standards: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    next_action: str = ""
    blocks_release: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UnhackableBenchmark:
    id: str
    phase: str
    status: str
    objective: str
    safe_scope: str
    attack_simulations: list[str] = field(default_factory=list)
    stress_tests: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)
    repair_route: str = "organism.hnc_saas_security"
    evidence_outputs: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    blocks_deployment: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HNCSaaSSecurityBlueprint:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    summary: dict[str, Any]
    safe_environment: dict[str, str]
    official_anchors: dict[str, str]
    hnc_inventory: list[dict[str, Any]]
    architecture: dict[str, Any]
    threat_model: list[dict[str, Any]]
    controls: list[SaaSSecurityControl]
    unhackable_pursuit_loop: list[UnhackableBenchmark]
    release_gates: list[dict[str, Any]]
    contract_plan: dict[str, Any]
    vault_memory: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "summary": dict(self.summary),
            "safe_environment": dict(self.safe_environment),
            "official_anchors": dict(self.official_anchors),
            "hnc_inventory": list(self.hnc_inventory),
            "architecture": dict(self.architecture),
            "threat_model": list(self.threat_model),
            "controls": [item.to_dict() for item in self.controls],
            "unhackable_pursuit_loop": [item.to_dict() for item in self.unhackable_pursuit_loop],
            "release_gates": list(self.release_gates),
            "contract_plan": dict(self.contract_plan),
            "vault_memory": dict(self.vault_memory),
            "notes": list(self.notes),
        }


def _surfaces_by_type(inventory: Sequence[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for item in inventory:
        grouped.setdefault(str(item.get("surface_type") or "unknown"), []).append(str(item.get("path") or ""))
    return {key: value[:12] for key, value in sorted(grouped.items())}


def build_threat_model() -> list[dict[str, Any]]:
    return [
        {
            "id": "threat_tenant_escape",
            "risk": "critical",
            "question": "Can one tenant read, alter, or infer another tenant's data?",
            "controls": ["control_tenant_rls", "control_audit_trace", "control_zero_trust_service_mesh"],
        },
        {
            "id": "threat_llm_tool_injection",
            "risk": "critical",
            "question": "Can prompt injection or poisoned vault data make the organism call unsafe tools?",
            "controls": ["control_llm_tool_governance", "control_audit_trace", "control_secure_sdlc"],
        },
        {
            "id": "threat_live_money_mutation",
            "risk": "critical",
            "question": "Can SaaS users or model output bypass trading, filing, payment, or secret boundaries?",
            "controls": ["control_trading_authority", "control_accounting_filing", "control_identity_rbac"],
        },
        {
            "id": "threat_api_appsec",
            "risk": "high",
            "question": "Can standard web flaws such as injection, broken access control, SSRF, or unsafe upload paths compromise the app?",
            "controls": ["control_api_asvs", "control_supply_chain", "control_secure_sdlc"],
        },
        {
            "id": "threat_operational_recovery",
            "risk": "high",
            "question": "Can Aureon recover from key rotation, failed deployment, data corruption, or incident response?",
            "controls": ["control_resilience", "control_data_protection", "control_audit_trace"],
        },
    ]


def build_controls(inventory: Sequence[dict[str, Any]]) -> list[SaaSSecurityControl]:
    grouped = _surfaces_by_type(inventory)

    def evidence(*surface_types: str) -> list[str]:
        output: list[str] = []
        for surface_type in surface_types:
            output.extend(grouped.get(surface_type, []))
        return output[:10]

    return [
        SaaSSecurityControl(
            id="control_identity_rbac",
            domain="identity_and_access",
            title="Phishing-resistant identity, RBAC, and session control",
            status="needs_implementation",
            risk="critical",
            requirement="Every user, device, service, worker, and organism agent must authenticate and authorize before SaaS access.",
            implementation_pattern="Use a trusted IdP with MFA/WebAuthn, short-lived sessions, rotating refresh tokens, role/attribute policies, and tenant-scoped permissions.",
            verification=["unit RBAC matrix", "E2E forbidden cross-role tests", "session expiry and token rotation tests"],
            hnc_systems=["HarmonicNexusAuth", "OrganismContractStack", "ThoughtBus"],
            standards=["OWASP ASVS", "OWASP Top 10 Broken Access Control", "NIST SP 800-207"],
            evidence=evidence("frontend_identity_hnc"),
            next_action="Replace any auto-login style SaaS path with explicit authenticated sessions and policy checks.",
        ),
        SaaSSecurityControl(
            id="control_tenant_rls",
            domain="tenant_isolation",
            title="Tenant isolation on every data boundary",
            status="needs_implementation",
            risk="critical",
            requirement="Every database row, object-store key, cache entry, event, vault note, work order, and log line must carry tenant context.",
            implementation_pattern="Add tenant_id, DB row-level security, per-tenant storage prefixes, tenant-aware queues, and denial-by-default service policies.",
            verification=["cross-tenant negative tests", "DB RLS policy tests", "object storage path traversal tests"],
            hnc_systems=["HNCGateway", "OrganismContractStack", "ObsidianBridge"],
            standards=["OWASP ASVS", "NIST SP 800-207"],
            evidence=evidence("core_hnc", "vault_memory_hnc"),
            next_action="Create the tenant contract schema before any SaaS endpoint becomes public.",
        ),
        SaaSSecurityControl(
            id="control_data_protection",
            domain="data_protection",
            title="Secrets, vault, accounting, and trading data protection",
            status="needs_implementation",
            risk="critical",
            requirement="Secrets and user financial data must be encrypted, minimized, redacted from prompts, and excluded from public logs/artifacts.",
            implementation_pattern="Use a secrets manager, envelope encryption for sensitive records, prompt redaction, key rotation, and metadata-only cataloging for secret files.",
            verification=["secret scanning", "prompt redaction tests", "encryption-at-rest checks", "backup restore drill"],
            hnc_systems=["AureonRepoSelfCatalog", "ObsidianBridge", "AccountingContextBridge"],
            standards=["OWASP ASVS", "OWASP Top 10 Cryptographic Failures", "NIST SP 800-207"],
            evidence=evidence("vault_memory_hnc", "accounting_hnc"),
            next_action="Define the SaaS secret/data classification map and enforce it in upload, vault, LLM, and report paths.",
        ),
        SaaSSecurityControl(
            id="control_api_asvs",
            domain="api_application_security",
            title="ASVS-backed API and frontend hardening",
            status="needs_implementation",
            risk="high",
            requirement="All SaaS routes must meet a defined ASVS level for authentication, access control, validation, encoding, upload safety, SSRF, CSRF, and rate limits.",
            implementation_pattern="Create middleware for validation/auth/policy/rate-limit, use safe parsers, isolate file scanning, and map controls to ASVS IDs.",
            verification=["ASVS checklist", "OWASP Top 10 regression suite", "file upload malware/path tests", "rate limit tests"],
            hnc_systems=["frontend", "supabase functions", "self-check scanner"],
            standards=["OWASP ASVS", "OWASP Top 10"],
            evidence=evidence("frontend_identity_hnc"),
            next_action="Add a SaaS route security middleware contract and tests before building public endpoints.",
        ),
        SaaSSecurityControl(
            id="control_llm_tool_governance",
            domain="ai_llm_tool_governance",
            title="LLM, tool, and self-writing code governance",
            status="needs_implementation",
            risk="critical",
            requirement="Model output may propose, classify, and queue work, but cannot bypass typed contracts, tests, operator approvals, or unsafe-action blockers.",
            implementation_pattern="Route all agent actions through allowlisted tools, policy checks, signed work orders, static tests, and vault memory with source provenance.",
            verification=["prompt injection tests", "unsafe tool denial tests", "contract safety tests", "self-written code static validation"],
            hnc_systems=["AureonCapabilityGrowthLoop", "SelfEnhancementEngine", "SkillValidator", "CodeArchitect"],
            standards=["OWASP ASVS", "NIST SP 800-207"],
            evidence=evidence("core_hnc", "validation_hnc"),
            next_action="Use this blueprint as the policy source for self-enhancement work orders touching SaaS code.",
        ),
        SaaSSecurityControl(
            id="control_trading_authority",
            domain="trading_authority_boundary",
            title="Trading authority boundary for SaaS users and agents",
            status="needs_implementation",
            risk="critical",
            requirement="The SaaS must never let SaaS UI, tenants, or LLM planning directly place live trades or mutate exchange state.",
            implementation_pattern="Keep live orders behind existing runtime gates, dry-run defaults, human-approved live profile, per-tenant risk limits, and immutable audit logs.",
            verification=["real_orders_allowed=false tests", "Kraken order call mock tests", "risk limit tests", "live-profile preflight tests"],
            hnc_systems=["dynamic margin sizer", "temporal trade cognition", "HNC probability matrix"],
            standards=["OWASP ASVS", "NIST SP 800-207"],
            evidence=evidence("trading_hnc"),
            next_action="Add SaaS trading command contracts that can observe/simulate by default and require explicit live-gate ownership.",
        ),
        SaaSSecurityControl(
            id="control_accounting_filing",
            domain="accounting_filing_boundary",
            title="Accounting generation with manual filing/payment boundary",
            status="needs_implementation",
            risk="high",
            requirement="The SaaS can prepare accounts packs and evidence, but cannot submit HMRC/Companies House filings or make payments automatically.",
            implementation_pattern="Expose accounting build/status endpoints that produce human-readable packs, manual filing checklists, and evidence gaps only.",
            verification=["HMRC/Companies House submit call denial tests", "payment denial tests", "evidence-not-fake tests"],
            hnc_systems=["Kings_Accounting_Suite", "HNCSoupKitchen", "HNC VAT/CIS/tax engines", "AccountingContextBridge"],
            standards=["OWASP ASVS", "NIST SP 800-207"],
            evidence=evidence("accounting_hnc"),
            next_action="Create SaaS accounting APIs that return packs and workpapers, while filing/payment action types remain blocked.",
        ),
        SaaSSecurityControl(
            id="control_audit_trace",
            domain="audit_observability",
            title="Tamper-evident audit trace for users, agents, and money workflows",
            status="needs_implementation",
            risk="high",
            requirement="Every login, data import, model decision, work order, accounting build, trading decision, and admin action must be traceable.",
            implementation_pattern="Use append-only event logs with trace_id, tenant_id, actor_id, decision input hash, result hash, retention policy, and exportable audit packs.",
            verification=["event schema tests", "trace propagation tests", "tamper-evidence hash-chain tests", "audit export test"],
            hnc_systems=["ThoughtBus", "OrganismContractStack", "capability growth loop"],
            standards=["OWASP ASVS", "NIST SP 800-207"],
            evidence=evidence("core_hnc", "validation_hnc"),
            next_action="Promote ThoughtBus/contract events into the SaaS audit event schema.",
        ),
        SaaSSecurityControl(
            id="control_supply_chain",
            domain="supply_chain",
            title="Dependency, build, and deployment supply-chain control",
            status="needs_implementation",
            risk="high",
            requirement="Every Python, Node, container, CI, and deployment artifact must be reproducible, scanned, and traceable.",
            implementation_pattern="Use lockfiles, SBOM, dependency review, SAST, secret scanning, signed artifacts, protected branches, and environment promotion gates.",
            verification=["pip/npm audit", "SBOM generation", "secret scanning", "signed build verification"],
            hnc_systems=["AureonCapabilityGrowthLoop", "RepoWideOrganizationAudit", "CodeArchitect"],
            standards=["OWASP ASVS", "OWASP Top 10 Vulnerable and Outdated Components"],
            evidence=evidence("validation_hnc"),
            next_action="Add supply-chain checks to the SaaS build benchmark before deployment work begins.",
        ),
        SaaSSecurityControl(
            id="control_resilience",
            domain="resilience_and_recovery",
            title="Backups, recovery, limits, and incident response",
            status="needs_implementation",
            risk="high",
            requirement="Aureon SaaS must survive failed deploys, data corruption, service outages, abuse bursts, and credential compromise.",
            implementation_pattern="Define RPO/RTO, encrypted backups, restore drills, circuit breakers, quotas, abuse throttles, incident runbooks, and kill switches.",
            verification=["restore drill", "rate-limit tests", "kill-switch tests", "incident tabletop checklist"],
            hnc_systems=["ignition preflight", "system readiness audit", "operator surfaces"],
            standards=["OWASP ASVS", "NIST SP 800-207"],
            evidence=evidence("validation_hnc", "core_hnc"),
            next_action="Create the SaaS incident and recovery runbook as a release gate.",
        ),
        SaaSSecurityControl(
            id="control_secure_sdlc",
            domain="secure_sdlc",
            title="Self-audit, benchmark, fix, and retest loop for SaaS",
            status="needs_implementation",
            risk="high",
            requirement="No SaaS change is release-ready until Aureon audits, benchmarks, queues fixes, retests, and records memory.",
            implementation_pattern="Attach the capability growth loop to SaaS controls and require compile, unit, integration, DAST, and policy tests before release.",
            verification=["capability growth report", "focused SaaS security tests", "DAST smoke", "vault memory proof"],
            hnc_systems=["AureonCapabilityGrowthLoop", "MindWiringAudit", "AureonSystemReadinessAudit"],
            standards=["OWASP ASVS", "OWASP Top 10"],
            evidence=evidence("validation_hnc", "research_evidence_hnc"),
            next_action="Add SaaS security to the capability growth domain matrix and work-order queue.",
        ),
        SaaSSecurityControl(
            id="control_zero_trust_service_mesh",
            domain="zero_trust_runtime",
            title="Zero-trust service-to-service runtime",
            status="needs_implementation",
            risk="critical",
            requirement="Every internal service call must be authenticated, authorized, least-privileged, logged, and continuously evaluated.",
            implementation_pattern="Use service identity, mTLS or signed requests, policy enforcement points, network segmentation, and continuous risk signals.",
            verification=["service auth tests", "deny-by-default tests", "network segmentation review", "trace continuity tests"],
            hnc_systems=["HNCGateway", "ThoughtBus", "OrganismContractStack"],
            standards=["NIST SP 800-207", "OWASP ASVS"],
            evidence=evidence("core_hnc", "frontend_identity_hnc"),
            next_action="Define service identities and policies before exposing multi-tenant jobs or agent queues.",
        ),
    ]


def build_unhackable_pursuit_loop(controls: Sequence[SaaSSecurityControl]) -> list[UnhackableBenchmark]:
    """Build the safe adversarial loop Aureon uses to pursue the unhackable goal."""

    control_ids = {control.id for control in controls}
    return [
        UnhackableBenchmark(
            id="bench_auth_breakout",
            phase="try_to_break_own_system",
            status="planned_authorized_self_test",
            objective="Prove no user, worker, model, or stale session can bypass authentication, MFA, session expiry, or RBAC.",
            safe_scope="Aureon-owned local/staging SaaS only, with test tenants and throwaway accounts.",
            attack_simulations=[
                "expired token replay",
                "role escalation attempt",
                "missing authorization header",
                "cross-role endpoint access",
            ],
            stress_tests=["high-frequency login attempts under rate limits"],
            success_metrics=[
                "all unauthorized requests denied",
                "audit event emitted for every denial",
                "no privileged action reachable without policy approval",
            ],
            evidence_outputs=["auth_breakout_report.json", "auth_breakout_report.md"],
            guardrails=["no password spraying against real third-party systems", "test accounts only"],
            blocks_deployment="control_identity_rbac" in control_ids,
        ),
        UnhackableBenchmark(
            id="bench_tenant_escape",
            phase="try_to_break_own_system",
            status="planned_authorized_self_test",
            objective="Prove one tenant cannot read, write, infer, queue, or export another tenant's data.",
            safe_scope="Two or more synthetic tenants in local/staging data stores and queues.",
            attack_simulations=[
                "tamper tenant_id in API request",
                "cross-tenant object-store path guessing",
                "queue claim from wrong tenant",
                "vault note retrieval across tenant boundary",
            ],
            stress_tests=["parallel cross-tenant negative access attempts"],
            success_metrics=[
                "zero cross-tenant reads",
                "zero cross-tenant writes",
                "tenant_id present in every audit event",
            ],
            evidence_outputs=["tenant_escape_matrix.json", "tenant_escape_matrix.md"],
            guardrails=["synthetic tenant data only", "no real customer data in adversarial fixtures"],
            blocks_deployment="control_tenant_rls" in control_ids,
        ),
        UnhackableBenchmark(
            id="bench_prompt_tool_breakout",
            phase="try_to_break_own_system",
            status="planned_authorized_self_test",
            objective="Prove poisoned prompts, vault notes, uploads, or user text cannot make LLM systems call unsafe tools or reveal secrets.",
            safe_scope="Local LLM/vault fixtures, mocked tools, and blocked unsafe action contracts.",
            attack_simulations=[
                "prompt injection requests to ignore policy",
                "vault note instruction poisoning",
                "fake tool result requesting live order",
                "secret exfiltration request through generated report",
            ],
            stress_tests=["prompt-injection corpus replay", "tool-denial fuzz cases"],
            success_metrics=[
                "unsafe tool action blocked",
                "secret values never printed",
                "blocked contract contains reason and trace_id",
            ],
            evidence_outputs=["llm_tool_breakout_report.json", "llm_tool_breakout_report.md"],
            guardrails=["mock tools for live orders, filings, payments, and secrets", "no secret values in fixtures"],
            blocks_deployment="control_llm_tool_governance" in control_ids,
        ),
        UnhackableBenchmark(
            id="bench_money_authority_breakout",
            phase="try_to_break_own_system",
            status="planned_authorized_self_test",
            objective="Prove SaaS users and model output cannot place live trades, submit filings, make payments, or mutate official/exchange state.",
            safe_scope="Contract safety layer, ignition preflight, mocked exchange/filing/payment clients.",
            attack_simulations=[
                "attempt live order work order",
                "attempt HMRC submission action",
                "attempt Companies House filing action",
                "attempt payment or withdrawal action",
            ],
            stress_tests=["repeated unsafe action queue attempts"],
            success_metrics=[
                "all unsafe contracts blocked",
                "real_orders_allowed remains false unless explicit live gate is owned by trading runtime",
                "manual filing/payment boundary preserved",
            ],
            evidence_outputs=["money_authority_breakout_report.json", "money_authority_breakout_report.md"],
            guardrails=["mocked external clients only", "no real Kraken, HMRC, Companies House, banking, or payment mutation"],
            blocks_deployment="control_trading_authority" in control_ids and "control_accounting_filing" in control_ids,
        ),
        UnhackableBenchmark(
            id="bench_api_fuzz_dast",
            phase="try_to_break_own_system",
            status="planned_authorized_self_test",
            objective="Probe Aureon-owned API/UI routes for injection, SSRF, CSRF, unsafe upload, broken access control, and validation failures.",
            safe_scope="Local/staging endpoint allowlist only; no third-party targets.",
            attack_simulations=[
                "SQL/NoSQL injection payloads against test endpoints",
                "SSRF canary URL denial",
                "path traversal upload names",
                "CSRF missing token requests",
            ],
            stress_tests=["rate-limit and concurrency stress", "large upload rejection tests"],
            success_metrics=[
                "all malformed inputs rejected safely",
                "no server-side fetch to unapproved egress",
                "no route exposes stack trace or secret metadata",
            ],
            evidence_outputs=["api_dast_fuzz_report.json", "api_dast_fuzz_report.md"],
            guardrails=["authorized local/staging allowlist required", "no destructive payloads", "no third-party scanning"],
            blocks_deployment="control_api_asvs" in control_ids,
        ),
        UnhackableBenchmark(
            id="bench_supply_chain_breakout",
            phase="stress_test",
            status="planned_authorized_self_test",
            objective="Prove dependencies, lockfiles, builds, and generated artifacts do not carry known vulnerable packages or secrets.",
            safe_scope="Local repo dependency graph, lockfiles, CI/build manifests, and generated artifacts.",
            attack_simulations=[
                "secret scan of generated artifacts",
                "dependency vulnerability scan",
                "lockfile drift check",
                "unsigned artifact rejection",
            ],
            stress_tests=["fresh install/build repeatability", "artifact provenance review"],
            success_metrics=[
                "no high/critical untriaged dependency issue",
                "no secret-like value in generated artifacts",
                "build artifact trace links back to commit and checks",
            ],
            evidence_outputs=["supply_chain_assurance.json", "supply_chain_assurance.md"],
            guardrails=["no publishing packages", "no token upload to scanners"],
            blocks_deployment="control_supply_chain" in control_ids,
        ),
        UnhackableBenchmark(
            id="bench_audit_tamper_resilience",
            phase="try_to_break_own_system",
            status="planned_authorized_self_test",
            objective="Prove audit trails survive tampering attempts and preserve traceability across agents, users, decisions, and money workflows.",
            safe_scope="Local/staging audit log fixtures and append-only event stores.",
            attack_simulations=[
                "delete audit event attempt",
                "modify prior event hash",
                "drop trace_id mid-workflow",
                "replay stale work-order result",
            ],
            stress_tests=["high-volume audit event write/read verification"],
            success_metrics=[
                "tampering detected",
                "hash chain or immutable event proof remains valid",
                "trace_id continuity preserved",
            ],
            evidence_outputs=["audit_tamper_report.json", "audit_tamper_report.md"],
            guardrails=["test audit stores only", "no deletion of production logs"],
            blocks_deployment="control_audit_trace" in control_ids,
        ),
        UnhackableBenchmark(
            id="bench_deploy_canary_review",
            phase="deployment_gate_review",
            status="planned_gate_only",
            objective="Prove deployment canary, rollback, backup restore, and incident response work before production release.",
            safe_scope="Staging/canary environment only until all release gates are satisfied.",
            attack_simulations=[
                "failed deployment rollback",
                "rotated secret recovery",
                "service outage fail-closed test",
                "abuse burst throttling test",
            ],
            stress_tests=["backup restore drill", "traffic spike within safe load budget"],
            success_metrics=[
                "rollback completes within target window",
                "restore drill passes",
                "kill switch disables risky actions",
            ],
            evidence_outputs=["deploy_canary_review.json", "deploy_canary_review.md"],
            guardrails=["no production deployment until every blocker is closed", "operator approval required for production promotion"],
            blocks_deployment=True,
        ),
    ]


def build_architecture(inventory: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {
        "target": "unhackable as an internal north-star benchmark, pursued through continuous authorized self-attack and repair",
        "cycle": list(UNHACKABLE_PHASES),
        "layers": [
            "tenant-aware SaaS UI/API",
            "identity and policy enforcement",
            "Aureon organism command plane",
            "HNC cognition/accounting/trading/research services",
            "vault and evidence memory",
            "tenant-scoped data stores and object storage",
            "append-only audit plane",
        ],
        "safe_defaults": [
            "read-only or simulation mode by default",
            "manual-only official filing and payment",
            "live trading remains behind existing explicit runtime gates",
            "LLM output routes through contract and tool governance",
            "secrets are never copied to reports or model context",
        ],
        "hnc_surface_counts": {
            key: len(value)
            for key, value in _surfaces_by_type(inventory).items()
        },
    }


def build_release_gates(
    controls: Sequence[SaaSSecurityControl],
    pursuit_loop: Sequence[UnhackableBenchmark] = (),
) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    for domain in REQUIRED_SECURITY_DOMAINS:
        domain_controls = [control for control in controls if control.domain == domain]
        gates.append(
            {
                "id": f"gate_{domain}",
                "domain": domain,
                "status": "blocked_until_control_verified",
                "control_ids": [control.id for control in domain_controls],
                "required_evidence": [
                    "implementation merged",
                    "unit/integration tests passed",
                    "policy denial tests passed",
                    "audit event evidence generated",
                ],
                "blocks_release": True,
            }
        )
    gates.append(
        {
            "id": "gate_unhackable_evidence",
            "domain": "unhackable_pursuit",
            "status": "required",
            "control_ids": [item.id for item in pursuit_loop],
            "required_evidence": [
                "authorized self-attack suite completed",
                "stress tests completed",
                "all discovered vulnerabilities routed to fixes",
                "all critical/high findings retested clean",
                "public/operator claim remains evidence-gated until proof pack exists",
            ],
            "blocks_release": True,
        }
    )
    return gates


def queue_security_contracts(
    root: Path,
    controls: Sequence[SaaSSecurityControl],
    pursuit_loop: Sequence[UnhackableBenchmark] = (),
    *,
    enabled: bool,
    state_path: Optional[Path] = None,
) -> dict[str, Any]:
    if not enabled:
        return {"queued_persistently": False, "control_count": len(controls), "benchmark_count": len(pursuit_loop)}
    try:
        from aureon.core.organism_contracts import OrganismContractStack

        resolved_state = state_path or root / DEFAULT_CONTRACT_STATE
        stack = OrganismContractStack(state_path=resolved_state, source="hnc_saas_security_architect")
        stack.register_skill(
            "hnc_saas_security_architect",
            "Inventories HNC systems and turns the unhackable SaaS north-star into controls, self-attack benchmarks, and auditable work orders.",
            safe_modes=["read_only", "local_blueprint", "authorized_self_test_plan", "queue_work_orders"],
            risk="medium",
        )
        workflow = stack.create_goal_workflow(
            "Pursue Aureon's unhackable HNC SaaS north-star through zero-trust controls, authorized self-attack, stress tests, repair, retest, and release gates.",
            skills=["hnc_saas_security_architect", "capability_growth_loop", "organism_contract_stack"],
            route_surfaces=["saas_security", "contracts", "capability_growth", "self_enhancement", "validation"],
            source="hnc_saas_security_architect",
        )
        work_orders: list[dict[str, Any]] = []
        for control in controls:
            priority = 6 if control.risk == "critical" else 4
            work_order = stack.enqueue_work_order(
                f"Implement SaaS security control: {control.title}",
                "execute_internal_task",
                queue="organism.hnc_saas_security",
                priority=priority,
                payload={
                    "control": control.to_dict(),
                    "acceptance_checks": control.verification,
                    "official_anchors": OFFICIAL_ANCHORS,
                    "release_gate": "blocked_until_control_verified",
                },
                source="hnc_saas_security_architect",
            )
            work_orders.append(work_order.to_dict())
        benchmark_work_orders: list[dict[str, Any]] = []
        for benchmark in pursuit_loop:
            work_order = stack.enqueue_work_order(
                f"Run unhackable pursuit benchmark: {benchmark.objective[:82]}",
                "execute_internal_task",
                queue="organism.hnc_saas_security",
                priority=7,
                payload={
                    "benchmark": benchmark.to_dict(),
                    "cycle": list(UNHACKABLE_PHASES),
                    "allowed_scope": benchmark.safe_scope,
                    "guardrails": benchmark.guardrails,
                    "release_gate": "gate_unhackable_evidence",
                },
                source="hnc_saas_security_architect",
            )
            benchmark_work_orders.append(work_order.to_dict())
        status = stack.publish_status()
        return {
            "queued_persistently": True,
            "state_path": str(resolved_state),
            "workflow": workflow,
            "work_order_count": len(work_orders),
            "benchmark_work_order_count": len(benchmark_work_orders),
            "work_orders": work_orders,
            "benchmark_work_orders": benchmark_work_orders,
            "status": status,
        }
    except Exception as exc:
        return {"queued_persistently": False, "error": f"{type(exc).__name__}: {exc}"}


def build_hnc_saas_security_blueprint(
    repo_root: Optional[Path] = None,
    *,
    queue_contracts: bool = False,
    contract_state_path: Optional[Path] = None,
) -> HNCSaaSSecurityBlueprint:
    root = repo_root_from(repo_root)
    safe_env = apply_safe_environment()
    inventory = inventory_hnc_systems(root)
    controls = build_controls(inventory)
    pursuit_loop = build_unhackable_pursuit_loop(controls)
    release_gates = build_release_gates(controls, pursuit_loop)
    contract_plan = queue_security_contracts(
        root,
        controls,
        pursuit_loop,
        enabled=queue_contracts,
        state_path=contract_state_path,
    )
    blocker_count = sum(1 for gate in release_gates if gate.get("blocks_release"))
    hnc_types = _surfaces_by_type(inventory)
    if not inventory:
        status = "blocked_missing_hnc_evidence"
    elif queue_contracts and contract_plan.get("queued_persistently"):
        status = "blueprint_ready_implementation_queued"
    else:
        status = "blueprint_ready_implementation_required"
    vault_path = resolve_obsidian_note_path(DEFAULT_VAULT_NOTE, repo_root=root)
    summary = {
        "hnc_surface_count": len(inventory),
        "hnc_surface_type_count": len(hnc_types),
        "control_count": len(controls),
        "critical_control_count": sum(1 for control in controls if control.risk == "critical"),
        "release_gate_count": len(release_gates),
        "release_blocker_count": blocker_count,
        "contract_queued": bool(contract_plan.get("queued_persistently")),
        "unhackable_internal_goal_active": True,
        "public_unhackable_claim_allowed": False,
        "security_target": "unhackable_pursuit_loop",
        "unhackable_phase_count": len(UNHACKABLE_PHASES),
        "unhackable_benchmark_count": len(pursuit_loop),
        "authorized_self_attack_required": True,
        "production_deploy_blocked_until_gates_pass": True,
    }
    return HNCSaaSSecurityBlueprint(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(root),
        status=status,
        summary=summary,
        safe_environment=safe_env,
        official_anchors=dict(OFFICIAL_ANCHORS),
        hnc_inventory=inventory,
        architecture=build_architecture(inventory),
        threat_model=build_threat_model(),
        controls=controls,
        unhackable_pursuit_loop=pursuit_loop,
        release_gates=release_gates,
        contract_plan=contract_plan,
        vault_memory={
            "status": "planned",
            "note_path": str(vault_path),
            "topic": "hnc.saas_security.blueprint.ready",
            "memory_summary": "Aureon has an HNC-led unhackable SaaS pursuit loop with authorized self-attack benchmarks, release-blocking controls, and queued implementation contracts.",
        },
        notes=[
            "Unhackable is the internal north-star benchmark: Aureon must test, stress test, try to break its own authorized surfaces, fix, retest, and repeat.",
            "Public claims and production deployment stay blocked until evidence gates prove the current benchmark set.",
            "This architect does not deploy services, expose secrets, place trades, file accounts, submit official forms, or make payments.",
            "Controls are release blockers until implementation and verification evidence exists.",
        ],
    )


def render_markdown(blueprint: HNCSaaSSecurityBlueprint) -> str:
    def esc(value: Any) -> str:
        return str(value).replace("|", "\\|")

    lines: list[str] = []
    lines.append("# HNC SaaS Security Blueprint")
    lines.append("")
    lines.append(f"- Generated: `{blueprint.generated_at}`")
    lines.append(f"- Repo: `{blueprint.repo_root}`")
    lines.append(f"- Status: `{blueprint.status}`")
    lines.append("- North star: `unhackable` is an active internal benchmark loop")
    lines.append("- Boundary: public claims and production deployment remain blocked until the proof gates pass")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in blueprint.summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Official Anchors")
    lines.append("")
    for key, url in blueprint.official_anchors.items():
        lines.append(f"- `{key}`: {url}")
    lines.append("")
    lines.append("## HNC Inventory")
    lines.append("")
    by_type = _surfaces_by_type(blueprint.hnc_inventory)
    lines.append("| Surface type | Count | Example paths |")
    lines.append("| --- | ---: | --- |")
    for surface_type, paths in by_type.items():
        count = sum(1 for item in blueprint.hnc_inventory if item.get("surface_type") == surface_type)
        lines.append(f"| `{esc(surface_type)}` | {count} | {esc(', '.join(paths[:5]))} |")
    lines.append("")
    lines.append("## Threat Model")
    lines.append("")
    lines.append("| Threat | Risk | Question | Linked controls |")
    lines.append("| --- | --- | --- | --- |")
    for threat in blueprint.threat_model:
        lines.append(
            f"| `{esc(threat['id'])}` | `{esc(threat['risk'])}` | {esc(threat['question'])} | {esc(', '.join(threat['controls']))} |"
        )
    lines.append("")
    lines.append("## Unhackable Pursuit Loop")
    lines.append("")
    lines.append("`" + " -> ".join(UNHACKABLE_PHASES) + "`")
    lines.append("")
    lines.append("| Benchmark | Phase | Status | Safe scope | Blocks deployment |")
    lines.append("| --- | --- | --- | --- | --- |")
    for benchmark in blueprint.unhackable_pursuit_loop:
        lines.append(
            f"| `{esc(benchmark.id)}` {esc(benchmark.objective)} | `{esc(benchmark.phase)}` | `{esc(benchmark.status)}` | {esc(benchmark.safe_scope)} | `{benchmark.blocks_deployment}` |"
        )
    lines.append("")
    lines.append("## Break-In And Stress Benchmarks")
    lines.append("")
    for benchmark in blueprint.unhackable_pursuit_loop:
        lines.append(f"### {benchmark.id}")
        lines.append("")
        lines.append(f"- Objective: {benchmark.objective}")
        lines.append(f"- Safe scope: {benchmark.safe_scope}")
        lines.append(f"- Attack simulations: {', '.join(benchmark.attack_simulations)}")
        lines.append(f"- Stress tests: {', '.join(benchmark.stress_tests)}")
        lines.append(f"- Success metrics: {', '.join(benchmark.success_metrics)}")
        lines.append(f"- Repair route: `{benchmark.repair_route}`")
        lines.append(f"- Guardrails: {', '.join(benchmark.guardrails)}")
        lines.append("")
    lines.append("## Security Controls")
    lines.append("")
    lines.append("| Control | Domain | Risk | Status | Release blocker | Next action |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for control in blueprint.controls:
        lines.append(
            f"| `{esc(control.id)}` {esc(control.title)} | `{esc(control.domain)}` | `{esc(control.risk)}` | `{esc(control.status)}` | `{control.blocks_release}` | {esc(control.next_action)} |"
        )
    lines.append("")
    lines.append("## Control Detail")
    lines.append("")
    for control in blueprint.controls:
        lines.append(f"### {control.title}")
        lines.append("")
        lines.append(f"- ID: `{control.id}`")
        lines.append(f"- Domain: `{control.domain}`")
        lines.append(f"- Requirement: {control.requirement}")
        lines.append(f"- Implementation pattern: {control.implementation_pattern}")
        lines.append(f"- HNC systems: {', '.join(f'`{item}`' for item in control.hnc_systems)}")
        lines.append(f"- Standards: {', '.join(f'`{item}`' for item in control.standards)}")
        lines.append(f"- Verification: {', '.join(control.verification)}")
        if control.evidence:
            lines.append(f"- Evidence paths: {', '.join(f'`{item}`' for item in control.evidence[:6])}")
        lines.append("")
    lines.append("## Release Gates")
    lines.append("")
    lines.append("| Gate | Status | Blocks release | Required evidence |")
    lines.append("| --- | --- | --- | --- |")
    for gate in blueprint.release_gates:
        lines.append(
            f"| `{esc(gate['id'])}` | `{esc(gate['status'])}` | `{gate.get('blocks_release')}` | {esc(', '.join(gate.get('required_evidence', [])))} |"
        )
    lines.append("")
    lines.append("## Contract Plan")
    lines.append("")
    for key, value in blueprint.contract_plan.items():
        if key == "work_orders":
            lines.append(f"- `work_orders`: `{len(value) if isinstance(value, list) else 0}`")
        elif isinstance(value, (dict, list)):
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
    lines.append("## Notes")
    lines.append("")
    for note in blueprint.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def write_report(
    blueprint: HNCSaaSSecurityBlueprint,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
    vault_path: Path = DEFAULT_VAULT_NOTE,
) -> tuple[Path, Path, Path]:
    root = Path(blueprint.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    note_path = resolve_obsidian_note_path(vault_path, repo_root=root)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_markdown(blueprint)
    md_path.write_text(rendered, encoding="utf-8")
    js_path.write_text(json.dumps(blueprint.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    note_path.write_text(rendered, encoding="utf-8")
    return md_path, js_path, note_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's HNC SaaS security blueprint.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--vault-note", default=str(DEFAULT_VAULT_NOTE), help="Vault note path.")
    parser.add_argument("--queue-contracts", action="store_true", help="Queue safe implementation work orders.")
    parser.add_argument("--no-write", action="store_true", help="Print JSON summary without writing artifacts.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    blueprint = build_hnc_saas_security_blueprint(root, queue_contracts=args.queue_contracts)
    if args.no_write:
        print(json.dumps({"status": blueprint.status, "summary": blueprint.summary}, indent=2, sort_keys=True))
    else:
        md_path, json_path, vault_path = write_report(
            blueprint,
            Path(args.markdown),
            Path(args.json),
            Path(args.vault_note),
        )
        print(
            json.dumps(
                {
                    "status": blueprint.status,
                    "markdown": str(md_path),
                    "json": str(json_path),
                    "vault_note": str(vault_path),
                    "summary": blueprint.summary,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 2 if blueprint.status.startswith("blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
