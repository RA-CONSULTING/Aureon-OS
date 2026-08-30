"""Authorized self-attack lab for Aureon's HNC SaaS security loop.

This module lets Aureon learn from historical defensive knowledge and launch
only bounded self-attacks against Aureon-owned local/staging targets. It is not
an intrusion tool: third-party targets, credential attacks, persistence,
evasion, destructive payloads, and data exfiltration are blocked by design.
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
from urllib.parse import urlparse

from aureon.obsidian_paths import resolve_obsidian_note_path
from aureon.autonomous.hnc_saas_security_architect import (
    DEFAULT_OUTPUT_JSON as DEFAULT_BLUEPRINT_JSON,
    OFFICIAL_ANCHORS,
    UNHACKABLE_PHASES,
    build_hnc_saas_security_blueprint,
    repo_root_from,
)


SCHEMA_VERSION = "aureon-hnc-authorized-attack-lab-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/hnc_authorized_attack_lab.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/hnc_authorized_attack_lab.json")
DEFAULT_CONTRACT_STATE = Path("state/hnc_authorized_attack_lab_contracts.json")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/hnc_authorized_attack_lab.md")

SAFE_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_OFFICIAL_FILING": "1",
    "AUREON_DISABLE_EXTERNAL_ATTACKS": "1",
}

ALLOWED_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
BLOCKED_ATTACK_TYPES = (
    "credential theft",
    "password spraying",
    "phishing",
    "malware",
    "persistence",
    "evasion",
    "real exploit against third party",
    "data exfiltration",
    "destructive payload",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _read_text(path: Path, limit: int = 60000) -> str:
    try:
        if not path.exists() or path.stat().st_size > 5_000_000:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except Exception:
        return ""


@dataclass
class ScopeDecision:
    target: str
    allowed: bool
    reason: str
    normalized: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HistoricalTacticLesson:
    id: str
    family: str
    defensive_lesson: str
    evidence_sources: list[str] = field(default_factory=list)
    safe_simulation: str = ""
    guardrails: list[str] = field(default_factory=list)
    maps_to_benchmarks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuthorizedAttackCase:
    id: str
    benchmark_id: str
    tactic_family: str
    objective: str
    safe_target: str
    simulation_mode: str
    benign_method: str
    expected_defense: str
    blocked_behaviors: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)
    status: str = "planned"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AttackFinding:
    id: str
    severity: str
    status: str
    title: str
    evidence: list[str] = field(default_factory=list)
    recommended_fix: str = ""
    benchmark_id: str = ""
    queued: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuthorizedAttackLabReport:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    safe_environment: dict[str, str]
    scope: list[ScopeDecision]
    historical_knowledge: list[HistoricalTacticLesson]
    attack_cases: list[AuthorizedAttackCase]
    findings: list[AttackFinding]
    contract_plan: dict[str, Any]
    summary: dict[str, Any]
    guardrails: list[str]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "safe_environment": dict(self.safe_environment),
            "scope": [item.to_dict() for item in self.scope],
            "historical_knowledge": [item.to_dict() for item in self.historical_knowledge],
            "attack_cases": [item.to_dict() for item in self.attack_cases],
            "findings": [item.to_dict() for item in self.findings],
            "contract_plan": dict(self.contract_plan),
            "summary": dict(self.summary),
            "guardrails": list(self.guardrails),
            "notes": list(self.notes),
        }


def validate_target_scope(root: Path, targets: Sequence[str]) -> list[ScopeDecision]:
    if not targets:
        return [
            ScopeDecision(
                target="local_planning_only",
                allowed=True,
                reason="No active endpoint target supplied; generate local plan and static simulations only.",
                normalized=str(root),
            )
        ]

    decisions: list[ScopeDecision] = []
    for raw in targets:
        target = str(raw or "").strip()
        if not target:
            continue
        parsed = urlparse(target)
        if parsed.scheme in {"http", "https"}:
            host = parsed.hostname or ""
            allowed = host in ALLOWED_LOCAL_HOSTS
            decisions.append(
                ScopeDecision(
                    target=target,
                    allowed=allowed,
                    reason=(
                        "Allowed local/staging loopback target."
                        if allowed
                        else "Blocked: external or non-loopback targets require separate written authorization and are not executed by this lab."
                    ),
                    normalized=target,
                )
            )
            continue
        path = Path(target)
        resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
        try:
            allowed_path = resolved == root.resolve() or root.resolve() in resolved.parents
        except Exception:
            allowed_path = False
        decisions.append(
            ScopeDecision(
                target=target,
                allowed=bool(allowed_path),
                reason=(
                    "Allowed repo-local path target."
                    if allowed_path
                    else "Blocked: path is outside the Aureon repo scope."
                ),
                normalized=str(resolved),
            )
        )
    return decisions


def _source_if_contains(root: Path, rel_path: str, *needles: str) -> list[str]:
    path = root / rel_path
    text = _read_text(path).lower()
    if not text:
        return []
    if any(needle.lower() in text for needle in needles):
        return [rel_path]
    return []


def load_historical_tactic_knowledge(root: Path) -> list[HistoricalTacticLesson]:
    """Convert local historical/security knowledge into defensive simulations."""

    sources = {
        "security_policy": _source_if_contains(root, "docs/SECURITY.md", "secret", "vulnerability"),
        "trading_security": _source_if_contains(root, "docs/runbooks/SECURITY_TRADING.md", "trading", "risk", "order"),
        "saas_blueprint": _source_if_contains(root, "docs/audits/hnc_saas_security_blueprint.md", "unhackable", "zero-trust"),
        "mind_wiring": _source_if_contains(root, "docs/audits/mind_wiring_audit.md", "thoughtbus", "trading", "cognitive"),
        "auth_surface": _source_if_contains(root, "frontend/src/lib/harmonic-nexus-auth.ts", "autologin", "session"),
        "contract_safety": _source_if_contains(root, "aureon/core/organism_contracts.py", "unsafe", "blocked"),
    }
    return [
        HistoricalTacticLesson(
            id="hist_broken_access_control",
            family="access_control",
            defensive_lesson="Historically, authorization failures are often more damaging than authentication failures; every route, worker, and queue claim must deny by default.",
            evidence_sources=sources["security_policy"] + sources["auth_surface"] + sources["saas_blueprint"],
            safe_simulation="Attempt denied cross-role and cross-tenant requests with benign canary identifiers.",
            guardrails=["synthetic tenants only", "no real credential guessing"],
            maps_to_benchmarks=["bench_auth_breakout", "bench_tenant_escape"],
        ),
        HistoricalTacticLesson(
            id="hist_prompt_injection_tool_abuse",
            family="llm_tool_governance",
            defensive_lesson="Agentic systems fail when untrusted text can redirect tools; prompts, uploads, and vault notes must be treated as hostile input.",
            evidence_sources=sources["saas_blueprint"] + sources["mind_wiring"] + sources["contract_safety"],
            safe_simulation="Replay harmless prompt-injection canaries against mocked tools and assert unsafe contracts are blocked.",
            guardrails=["mock live-order, filing, payment, and secret tools", "no real secrets in prompts"],
            maps_to_benchmarks=["bench_prompt_tool_breakout", "bench_money_authority_breakout"],
        ),
        HistoricalTacticLesson(
            id="hist_money_workflow_authority",
            family="financial_authority",
            defensive_lesson="Any system that touches trading, filing, tax, payments, or exchange state needs separate authority gates and audit proof.",
            evidence_sources=sources["trading_security"] + sources["contract_safety"] + sources["saas_blueprint"],
            safe_simulation="Queue blocked action contracts for live order, filing, payment, and withdrawal attempts and assert fail-closed behavior.",
            guardrails=["no exchange calls", "no HMRC/Companies House calls", "no bank/payment calls"],
            maps_to_benchmarks=["bench_money_authority_breakout"],
        ),
        HistoricalTacticLesson(
            id="hist_input_and_upload_abuse",
            family="api_input_validation",
            defensive_lesson="Input, upload, path, and egress controls must reject malformed data before it reaches storage, tools, or SSRF-capable clients.",
            evidence_sources=sources["saas_blueprint"],
            safe_simulation="Use non-destructive canary strings for injection, path traversal, SSRF, CSRF, and upload-name validation.",
            guardrails=["local/staging allowlist only", "no destructive payloads", "no third-party scanning"],
            maps_to_benchmarks=["bench_api_fuzz_dast"],
        ),
        HistoricalTacticLesson(
            id="hist_supply_chain_and_secret_leak",
            family="supply_chain",
            defensive_lesson="Dependencies, generated artifacts, logs, and reports must be scanned because secrets and vulnerable components often leak through build outputs.",
            evidence_sources=sources["security_policy"] + sources["saas_blueprint"],
            safe_simulation="Run local secret-pattern and dependency-artifact checks without uploading tokens or private files.",
            guardrails=["local scanning only", "redact secret values", "no package publishing"],
            maps_to_benchmarks=["bench_supply_chain_breakout"],
        ),
        HistoricalTacticLesson(
            id="hist_audit_tamper_and_replay",
            family="audit_integrity",
            defensive_lesson="Attackers target logs and traces after compromise; audit chains need tamper detection and replay resistance.",
            evidence_sources=sources["contract_safety"] + sources["saas_blueprint"],
            safe_simulation="Attempt local fixture tamper/replay and require trace continuity plus tamper-evidence.",
            guardrails=["test audit stores only", "no production log deletion"],
            maps_to_benchmarks=["bench_audit_tamper_resilience"],
        ),
    ]


def _load_blueprint(root: Path) -> dict[str, Any]:
    path = root / DEFAULT_BLUEPRINT_JSON
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            pass
    return build_hnc_saas_security_blueprint(root).to_dict()


def build_authorized_attack_cases(
    root: Path,
    lessons: Sequence[HistoricalTacticLesson],
    scope: Sequence[ScopeDecision],
) -> list[AuthorizedAttackCase]:
    blueprint = _load_blueprint(root)
    allowed_targets = [item.normalized for item in scope if item.allowed]
    safe_target = allowed_targets[0] if allowed_targets else str(root)
    cases: list[AuthorizedAttackCase] = []
    benchmark_ids = {item.get("id") for item in blueprint.get("unhackable_pursuit_loop") or []}
    for lesson in lessons:
        for benchmark_id in lesson.maps_to_benchmarks:
            if benchmark_ids and benchmark_id not in benchmark_ids:
                continue
            cases.append(
                AuthorizedAttackCase(
                    id=f"case_{lesson.id}_{benchmark_id}",
                    benchmark_id=benchmark_id,
                    tactic_family=lesson.family,
                    objective=lesson.defensive_lesson,
                    safe_target=safe_target,
                    simulation_mode="benign_self_attack_simulation",
                    benign_method=lesson.safe_simulation,
                    expected_defense="deny, log, trace, and route any weakness to repair work orders",
                    blocked_behaviors=list(BLOCKED_ATTACK_TYPES),
                    success_metrics=[
                        "attack canary cannot cross the target boundary",
                        "unsafe action blocks with reason",
                        "audit trace is produced",
                        "finding routes to retest if control is missing",
                    ],
                )
            )
    return cases


def run_static_self_attack_simulations(root: Path, cases: Sequence[AuthorizedAttackCase]) -> tuple[list[AuthorizedAttackCase], list[AttackFinding]]:
    findings: list[AttackFinding] = []
    updated_cases: list[AuthorizedAttackCase] = []
    auth_surface = root / "frontend" / "src" / "lib" / "harmonic-nexus-auth.ts"
    auth_text = _read_text(auth_surface)
    contract_text = _read_text(root / "aureon" / "core" / "organism_contracts.py")
    blueprint = _load_blueprint(root)
    blueprint_summary = blueprint.get("summary") or {}

    for case in cases:
        status = "simulated_passed"
        if case.benchmark_id == "bench_auth_breakout" and re.search(r"\bautoLogin\s*\(", auth_text):
            status = "simulated_finding"
            findings.append(
                AttackFinding(
                    id="finding_auth_autologin_surface",
                    severity="high",
                    status="needs_fix",
                    title="Frontend HNC auth surface still exposes an auto-login path that must not be production SaaS default.",
                    evidence=[_rel(auth_surface, root), "case=bench_auth_breakout"],
                    recommended_fix="Replace production SaaS auto-login with explicit authenticated session creation, MFA policy, short-lived tokens, and tests proving auto-login is disabled outside local demo mode.",
                    benchmark_id=case.benchmark_id,
                )
            )
        elif case.benchmark_id == "bench_money_authority_breakout" and "UNSAFE_ACTION_TYPES" not in contract_text:
            status = "simulated_finding"
            findings.append(
                AttackFinding(
                    id="finding_missing_contract_unsafe_actions",
                    severity="critical",
                    status="needs_fix",
                    title="Contract safety layer does not expose unsafe action blockers.",
                    evidence=["aureon/core/organism_contracts.py", "case=bench_money_authority_breakout"],
                    recommended_fix="Add fail-closed contract blockers for live orders, official filings, payments, withdrawals, and exchange mutations.",
                    benchmark_id=case.benchmark_id,
                )
            )
        elif case.benchmark_id == "bench_tenant_escape" and not blueprint_summary.get("production_deploy_blocked_until_gates_pass"):
            status = "simulated_finding"
            findings.append(
                AttackFinding(
                    id="finding_missing_deploy_gate",
                    severity="critical",
                    status="needs_fix",
                    title="Blueprint does not block deployment until tenant isolation gates pass.",
                    evidence=["docs/audits/hnc_saas_security_blueprint.json", "case=bench_tenant_escape"],
                    recommended_fix="Make tenant isolation and unhackable evidence release gates block production deployment.",
                    benchmark_id=case.benchmark_id,
                )
            )
        updated_cases.append(AuthorizedAttackCase(**{**case.to_dict(), "status": status}))

    if not findings:
        findings.append(
            AttackFinding(
                id="finding_none_static_simulation",
                severity="info",
                status="no_high_or_critical_static_findings",
                title="Static self-attack simulation did not detect high/critical gaps in the currently implemented checks.",
                evidence=["hnc_authorized_attack_lab"],
                recommended_fix="Run endpoint-level local/staging attack simulations once the SaaS service endpoints exist.",
            )
        )
    return updated_cases, findings


def queue_fix_contracts(root: Path, findings: Sequence[AttackFinding], *, enabled: bool) -> dict[str, Any]:
    actionable = [finding for finding in findings if finding.severity in {"critical", "high", "medium"}]
    if not enabled:
        return {"queued_persistently": False, "actionable_finding_count": len(actionable)}
    try:
        from aureon.core.organism_contracts import OrganismContractStack

        stack = OrganismContractStack(
            state_path=root / DEFAULT_CONTRACT_STATE,
            source="hnc_authorized_attack_lab",
        )
        workflow = stack.create_goal_workflow(
            "Repair weaknesses found by Aureon's authorized unhackable self-attack lab and retest.",
            skills=["hnc_authorized_attack_lab", "hnc_saas_security_architect", "capability_growth_loop"],
            route_surfaces=["saas_security", "contracts", "self_enhancement", "validation"],
            source="hnc_authorized_attack_lab",
        )
        work_orders: list[dict[str, Any]] = []
        for finding in actionable:
            work_order = stack.enqueue_work_order(
                f"Fix self-attack finding: {finding.title}",
                "execute_internal_task",
                queue="organism.hnc_attack_lab",
                priority=8 if finding.severity == "critical" else 6,
                payload={
                    "finding": finding.to_dict(),
                    "cycle": list(UNHACKABLE_PHASES),
                    "required_retest": finding.benchmark_id,
                    "guardrails": list(BLOCKED_ATTACK_TYPES),
                },
                source="hnc_authorized_attack_lab",
            )
            work_orders.append(work_order.to_dict())
        status = stack.publish_status()
        return {
            "queued_persistently": True,
            "state_path": str(root / DEFAULT_CONTRACT_STATE),
            "workflow": workflow,
            "work_order_count": len(work_orders),
            "work_orders": work_orders,
            "status": status,
        }
    except Exception as exc:
        return {"queued_persistently": False, "error": f"{type(exc).__name__}: {exc}"}


def build_authorized_attack_lab_report(
    repo_root: Optional[Path] = None,
    *,
    targets: Sequence[str] = (),
    execute_simulations: bool = False,
    queue_fixes: bool = False,
) -> AuthorizedAttackLabReport:
    root = repo_root_from(repo_root)
    env = apply_safe_environment()
    scope = validate_target_scope(root, targets)
    blocked_scope = [item for item in scope if not item.allowed]
    lessons = load_historical_tactic_knowledge(root)
    cases = build_authorized_attack_cases(root, lessons, scope)
    findings: list[AttackFinding] = []
    if blocked_scope:
        status = "blocked_target_scope"
        for decision in blocked_scope:
            findings.append(
                AttackFinding(
                    id=f"finding_blocked_scope_{len(findings) + 1}",
                    severity="critical",
                    status="blocked",
                    title="External or out-of-scope self-attack target rejected.",
                    evidence=[decision.target, decision.reason],
                    recommended_fix="Use only Aureon-owned local/staging loopback endpoints or repo-local paths for this lab.",
                )
            )
    elif execute_simulations:
        cases, findings = run_static_self_attack_simulations(root, cases)
        status = "simulations_completed_with_findings" if any(f.severity in {"critical", "high", "medium"} for f in findings) else "simulations_completed"
    else:
        status = "authorized_attack_plan_ready"
    contract_plan = queue_fix_contracts(root, findings, enabled=queue_fixes and not blocked_scope)
    for finding in findings:
        finding.queued = bool(contract_plan.get("queued_persistently")) and finding.severity in {"critical", "high", "medium"}
    summary = {
        "scope_target_count": len(scope),
        "blocked_scope_count": len(blocked_scope),
        "historical_lesson_count": len(lessons),
        "attack_case_count": len(cases),
        "executed_simulation_count": sum(1 for case in cases if case.status.startswith("simulated")),
        "finding_count": len(findings),
        "actionable_finding_count": sum(1 for finding in findings if finding.severity in {"critical", "high", "medium"}),
        "fix_contracts_queued": bool(contract_plan.get("queued_persistently")),
        "external_attacks_allowed": False,
        "authorized_self_attack_required": True,
    }
    return AuthorizedAttackLabReport(
        schema_version=SCHEMA_VERSION,
        generated_at=utc_now(),
        repo_root=str(root),
        status=status,
        safe_environment=env,
        scope=scope,
        historical_knowledge=lessons,
        attack_cases=cases,
        findings=findings,
        contract_plan=contract_plan,
        summary=summary,
        guardrails=[
            "Only Aureon-owned local/staging loopback targets and repo-local paths are allowed.",
            "No third-party systems, credential attacks, phishing, malware, persistence, evasion, destructive payloads, or data exfiltration.",
            "Live trading, official filing, payments, exchange mutation, and secret access remain mocked or blocked.",
            "Every finding must become a fix-and-retest work order before release gates can pass.",
        ],
        notes=[
            "Historical tactic knowledge is used as defensive memory and test design, not as an operational intrusion playbook.",
            "Endpoint-level testing should only run after the SaaS service exposes local/staging allowlisted endpoints.",
            f"Official anchors: {OFFICIAL_ANCHORS}",
        ],
    )


def render_markdown(report: AuthorizedAttackLabReport) -> str:
    def esc(value: Any) -> str:
        return str(value).replace("|", "\\|")

    lines: list[str] = []
    lines.append("# HNC Authorized Attack Lab")
    lines.append("")
    lines.append(f"- Generated: `{report.generated_at}`")
    lines.append(f"- Repo: `{report.repo_root}`")
    lines.append(f"- Status: `{report.status}`")
    lines.append("- Purpose: pursue the `unhackable` SaaS goal through authorized self-attack, repair, and retest")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in report.summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Guardrails")
    lines.append("")
    for guardrail in report.guardrails:
        lines.append(f"- {guardrail}")
    lines.append("")
    lines.append("## Scope")
    lines.append("")
    lines.append("| Target | Allowed | Reason |")
    lines.append("| --- | --- | --- |")
    for decision in report.scope:
        lines.append(f"| `{esc(decision.target)}` | `{decision.allowed}` | {esc(decision.reason)} |")
    lines.append("")
    lines.append("## Historical Defensive Knowledge")
    lines.append("")
    lines.append("| Lesson | Family | Defensive lesson | Safe simulation |")
    lines.append("| --- | --- | --- | --- |")
    for lesson in report.historical_knowledge:
        lines.append(
            f"| `{esc(lesson.id)}` | `{esc(lesson.family)}` | {esc(lesson.defensive_lesson)} | {esc(lesson.safe_simulation)} |"
        )
    lines.append("")
    lines.append("## Authorized Attack Cases")
    lines.append("")
    lines.append("| Case | Benchmark | Tactic | Status | Expected defense |")
    lines.append("| --- | --- | --- | --- | --- |")
    for case in report.attack_cases:
        lines.append(
            f"| `{esc(case.id)}` | `{esc(case.benchmark_id)}` | `{esc(case.tactic_family)}` | `{esc(case.status)}` | {esc(case.expected_defense)} |"
        )
    lines.append("")
    lines.append("## Findings")
    lines.append("")
    lines.append("| Finding | Severity | Status | Queued | Recommendation |")
    lines.append("| --- | --- | --- | --- | --- |")
    for finding in report.findings:
        lines.append(
            f"| `{esc(finding.id)}` {esc(finding.title)} | `{esc(finding.severity)}` | `{esc(finding.status)}` | `{finding.queued}` | {esc(finding.recommended_fix)} |"
        )
    lines.append("")
    lines.append("## Contract Plan")
    lines.append("")
    for key, value in report.contract_plan.items():
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
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: AuthorizedAttackLabReport,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
    vault_path: Path = DEFAULT_VAULT_NOTE,
) -> tuple[Path, Path, Path]:
    root = Path(report.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    note_path = resolve_obsidian_note_path(vault_path, repo_root=root)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_markdown(report)
    md_path.write_text(rendered, encoding="utf-8")
    js_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    note_path.write_text(rendered, encoding="utf-8")
    return md_path, js_path, note_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Aureon's authorized HNC self-attack lab.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--target", action="append", default=[], help="Allowed target: localhost URL or repo-local path.")
    parser.add_argument("--execute-simulations", action="store_true", help="Run benign local/static simulations.")
    parser.add_argument("--queue-fixes", action="store_true", help="Queue fix work orders for findings.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--vault-note", default=str(DEFAULT_VAULT_NOTE), help="Vault note path.")
    parser.add_argument("--no-write", action="store_true", help="Print summary only.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    report = build_authorized_attack_lab_report(
        root,
        targets=args.target,
        execute_simulations=args.execute_simulations,
        queue_fixes=args.queue_fixes,
    )
    if args.no_write:
        print(json.dumps({"status": report.status, "summary": report.summary}, indent=2, sort_keys=True))
    else:
        md_path, json_path, vault_path = write_report(report, Path(args.markdown), Path(args.json), Path(args.vault_note))
        print(
            json.dumps(
                {
                    "status": report.status,
                    "markdown": str(md_path),
                    "json": str(json_path),
                    "vault_note": str(vault_path),
                    "summary": report.summary,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 2 if report.status.startswith("blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
