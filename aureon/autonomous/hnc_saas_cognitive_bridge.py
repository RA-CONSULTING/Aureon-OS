"""Cognitive bridge between Aureon's mind and the HNC SaaS security loop.

The bridge makes the SaaS system part of the organism instead of a side report:
it loads the unhackable pursuit blueprint, the authorized self-attack lab, the
goal route brain, the contract queue, and publishes a compact state to
ThoughtBus so the cognitive systems can think on their feet.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from aureon.obsidian_paths import resolve_obsidian_note_path
from aureon.autonomous.aureon_goal_capability_map import build_goal_capability_map
from aureon.autonomous.hnc_authorized_attack_lab import build_authorized_attack_lab_report
from aureon.autonomous.hnc_saas_security_architect import build_hnc_saas_security_blueprint, repo_root_from


SCHEMA_VERSION = "aureon-hnc-saas-cognitive-bridge-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/hnc_saas_cognitive_bridge.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/hnc_saas_cognitive_bridge.json")
DEFAULT_VAULT_NOTE = Path(".obsidian/Aureon Self Understanding/hnc_saas_cognitive_bridge.md")

SAFE_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_DISABLE_EXTERNAL_ATTACKS": "1",
}

SAAS_COGNITIVE_TOPICS = {
    "ready": "saas.cognition.ready",
    "state": "saas.cognition.state",
    "question": "saas.cognition.question",
    "intent": "saas.cognition.intent",
    "finding": "saas.security.finding",
    "blocked": "saas.cognition.blocked",
}


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


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "path": str(path)}


def _publish(bus: Any, topic: str, payload: dict[str, Any], source: str = "hnc_saas_cognitive_bridge") -> None:
    if bus is None:
        return
    try:
        bus.publish(topic, payload, source=source)
    except Exception:
        pass


@dataclass
class SaaSCognitiveQuestion:
    id: str
    question: str
    trigger: str
    routed_systems: list[str] = field(default_factory=list)
    next_action: str = ""
    risk: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SaaSCognitiveState:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    summary: dict[str, Any]
    route_map: dict[str, Any]
    questions: list[SaaSCognitiveQuestion]
    decisions: list[dict[str, Any]]
    thought_topics: dict[str, str]
    contract_plan: dict[str, Any]
    safety: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "summary": dict(self.summary),
            "route_map": dict(self.route_map),
            "questions": [item.to_dict() for item in self.questions],
            "decisions": list(self.decisions),
            "thought_topics": dict(self.thought_topics),
            "contract_plan": dict(self.contract_plan),
            "safety": dict(self.safety),
            "notes": list(self.notes),
        }


class SaaSCognitiveBridge:
    """Runtime bridge that lets cognition observe and steer SaaS hardening."""

    def __init__(
        self,
        repo_root: Optional[Path] = None,
        *,
        thought_bus: Any = None,
        contract_stack: Any = None,
        vault: Any = None,
    ) -> None:
        self.repo_root = repo_root_from(repo_root)
        self.thought_bus = thought_bus
        self.contract_stack = contract_stack
        self.vault = vault
        self.last_state: Optional[SaaSCognitiveState] = None

    def load_context(self, *, force: bool = False, run_attack_lab_if_missing: bool = False) -> SaaSCognitiveState:
        apply_safe_environment()
        blueprint_path = self.repo_root / "docs" / "audits" / "hnc_saas_security_blueprint.json"
        attack_lab_path = self.repo_root / "docs" / "audits" / "hnc_authorized_attack_lab.json"
        blueprint = load_json(blueprint_path)
        if force or not blueprint:
            blueprint = build_hnc_saas_security_blueprint(self.repo_root).to_dict()
        attack_lab = load_json(attack_lab_path)
        if run_attack_lab_if_missing and (force or not attack_lab):
            attack_lab = build_authorized_attack_lab_report(self.repo_root).to_dict()

        route_map = build_goal_capability_map(
            repo_root=self.repo_root,
            current_goal=(
                "think on its feet about unhackable SaaS, cognitive systems, "
                "authorized self-attack, stress testing, fixing, retesting, and deployment gates"
            ),
        ).compact()

        questions = build_saas_cognitive_questions(blueprint, attack_lab)
        decisions = build_saas_cognitive_decisions(blueprint, attack_lab)
        contract_plan = self._queue_decisions(decisions)
        status = resolve_status(blueprint, attack_lab, decisions)
        summary = {
            "blueprint_status": blueprint.get("status"),
            "attack_lab_status": attack_lab.get("status"),
            "hnc_surface_count": (blueprint.get("summary") or {}).get("hnc_surface_count", 0),
            "unhackable_benchmark_count": (blueprint.get("summary") or {}).get("unhackable_benchmark_count", 0),
            "attack_case_count": (attack_lab.get("summary") or {}).get("attack_case_count", 0),
            "actionable_finding_count": (attack_lab.get("summary") or {}).get("actionable_finding_count", 0),
            "queued_decision_count": contract_plan.get("queued_decision_count", 0),
            "external_attacks_allowed": False,
            "cognitive_topics_wired": True,
        }
        state = SaaSCognitiveState(
            schema_version=SCHEMA_VERSION,
            generated_at=utc_now(),
            repo_root=str(self.repo_root),
            status=status,
            summary=summary,
            route_map=route_map,
            questions=questions,
            decisions=decisions,
            thought_topics=dict(SAAS_COGNITIVE_TOPICS),
            contract_plan=contract_plan,
            safety={
                **apply_safe_environment(),
                "external_attacks_allowed": False,
                "live_trading_allowed": False,
                "production_deploy_blocked_until_gates_pass": True,
            },
            notes=[
                "The SaaS system is wired to cognition through ThoughtBus, goal routing, vault memory, and organism work orders.",
                "Cognition may plan and queue authorized local/staging self-attacks, repairs, and retests.",
                "External targets, live trading, filing, payments, destructive payloads, and secret access remain blocked.",
            ],
        )
        self.last_state = state
        return state

    def publish_ready(self) -> dict[str, Any]:
        state = self.last_state or self.load_context()
        payload = state.to_dict()
        _publish(self.thought_bus, SAAS_COGNITIVE_TOPICS["ready"], payload)
        return payload

    def publish_state(self) -> dict[str, Any]:
        state = self.last_state or self.load_context()
        payload = state.to_dict()
        _publish(self.thought_bus, SAAS_COGNITIVE_TOPICS["state"], payload)
        for question in state.questions[:6]:
            _publish(self.thought_bus, SAAS_COGNITIVE_TOPICS["question"], question.to_dict())
        for decision in state.decisions[:6]:
            topic = SAAS_COGNITIVE_TOPICS["finding"] if decision.get("kind") == "fix_finding" else SAAS_COGNITIVE_TOPICS["intent"]
            _publish(self.thought_bus, topic, decision)
        return payload

    def status(self, *, force: bool = False) -> dict[str, Any]:
        state = self.load_context(force=force) if force or self.last_state is None else self.last_state
        return state.to_dict()

    def ingest_to_vault(self, vault: Any = None, *, force: bool = False) -> str:
        state = self.load_context(force=force) if force or self.last_state is None else self.last_state
        note_path = resolve_obsidian_note_path(DEFAULT_VAULT_NOTE, repo_root=self.repo_root)
        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(render_markdown(state), encoding="utf-8")
        target_vault = vault or self.vault
        if target_vault is not None:
            for method_name in ("add_card", "ingest", "write_note"):
                method = getattr(target_vault, method_name, None)
                if callable(method):
                    try:
                        method("hnc_saas_cognitive_bridge", state.to_dict())
                        break
                    except Exception:
                        pass
        return str(note_path)

    def _queue_decisions(self, decisions: Sequence[dict[str, Any]]) -> dict[str, Any]:
        actionable = [item for item in decisions if item.get("queue_work")]
        if self.contract_stack is None:
            return {"queued_persistently": False, "queued_decision_count": 0, "actionable_decision_count": len(actionable)}
        queued: list[dict[str, Any]] = []
        try:
            for decision in actionable:
                work_order = self.contract_stack.enqueue_work_order(
                    str(decision.get("title") or "SaaS cognitive work order"),
                    "execute_internal_task",
                    queue="organism.hnc_saas_cognition",
                    priority=int(decision.get("priority") or 5),
                    payload={
                        "decision": dict(decision),
                        "route": "hnc_saas_cognitive_bridge",
                        "safety": {
                            "external_attacks_allowed": False,
                            "authorized_self_attack_only": True,
                        },
                    },
                    source="hnc_saas_cognitive_bridge",
                )
                queued.append(work_order.to_dict())
            status = self.contract_stack.publish_status()
            return {
                "queued_persistently": True,
                "queued_decision_count": len(queued),
                "work_orders": queued,
                "status": status,
            }
        except Exception as exc:
            return {"queued_persistently": False, "error": f"{type(exc).__name__}: {exc}", "queued_decision_count": len(queued)}


def build_saas_cognitive_questions(blueprint: dict[str, Any], attack_lab: dict[str, Any]) -> list[SaaSCognitiveQuestion]:
    summary = blueprint.get("summary") or {}
    lab_summary = attack_lab.get("summary") or {}
    findings = attack_lab.get("findings") or []
    questions = [
        SaaSCognitiveQuestion(
            id="q_saas_goal",
            question="What is the current unhackable SaaS benchmark, and which gate blocks production next?",
            trigger="every_saas_cognitive_cycle",
            routed_systems=["HNCSaaSSecurityArchitect", "AureonSystemReadinessAudit"],
            next_action="Read blueprint, release gates, and unhackable pursuit loop.",
            risk="medium",
        ),
        SaaSCognitiveQuestion(
            id="q_attack_lab",
            question="Have authorized self-attacks run against owned local/staging surfaces, and what did they find?",
            trigger="attack_lab_status",
            routed_systems=["HNCAuthorizedAttackLab", "ThoughtBus", "OrganismContractStack"],
            next_action="Run or refresh attack-lab simulation before deployment gates can advance.",
            risk="high",
        ),
        SaaSCognitiveQuestion(
            id="q_cognitive_route",
            question="Which cognitive systems should reason about the SaaS finding right now?",
            trigger="finding_or_gate_change",
            routed_systems=["GoalCapabilityMap", "SelfQuestioningAI", "Queen reasoning", "CapabilityGrowthLoop"],
            next_action="Route through memory, reasoning, contracts, capability growth, and SaaS security.",
            risk="medium",
        ),
        SaaSCognitiveQuestion(
            id="q_fix_retest",
            question="What fix, test, and retest evidence is required before this SaaS control can move forward?",
            trigger="actionable_findings",
            routed_systems=["CodeArchitect", "SkillValidator", "pytest", "compileall"],
            next_action="Queue fix work orders and require retest proof.",
            risk="high",
        ),
    ]
    if summary.get("release_blocker_count", 0):
        questions.append(
            SaaSCognitiveQuestion(
                id="q_release_blockers",
                question="Which release blockers remain and what proof would close them?",
                trigger="release_blockers_present",
                routed_systems=["HNCSaaSSecurityArchitect", "HNCAuthorizedAttackLab"],
                next_action="Keep production deployment blocked and work the highest-risk blocker first.",
                risk="high",
            )
        )
    if lab_summary.get("actionable_finding_count", 0) or findings:
        questions.append(
            SaaSCognitiveQuestion(
                id="q_findings",
                question="Which self-attack findings are actionable and have they been queued for repair?",
                trigger="actionable_findings_present",
                routed_systems=["HNCAuthorizedAttackLab", "OrganismContractStack", "CapabilityGrowthLoop"],
                next_action="Queue fixes, publish findings, and retest the affected benchmark.",
                risk="high",
            )
        )
    return questions


def build_saas_cognitive_decisions(blueprint: dict[str, Any], attack_lab: dict[str, Any]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    b_summary = blueprint.get("summary") or {}
    a_summary = attack_lab.get("summary") or {}
    findings = attack_lab.get("findings") or []
    if not attack_lab:
        decisions.append(
            {
                "id": "decision_run_attack_lab",
                "kind": "run_authorized_self_attack",
                "title": "Run HNC authorized attack lab against owned local/staging SaaS surfaces",
                "reason": "No attack lab manifest is available for the current unhackable pursuit loop.",
                "queue_work": True,
                "priority": 7,
                "safe_scope": "repo-local or loopback/local staging only",
            }
        )
    if b_summary.get("production_deploy_blocked_until_gates_pass", True):
        decisions.append(
            {
                "id": "decision_keep_deployment_blocked",
                "kind": "gate",
                "title": "Keep SaaS production deployment blocked until unhackable gates pass",
                "reason": "Release gates require implementation, authorized self-attack, stress, repair, and retest evidence.",
                "queue_work": False,
                "priority": 6,
            }
        )
    for finding in findings:
        severity = str(finding.get("severity") or "").lower()
        if severity in {"critical", "high", "medium"}:
            decisions.append(
                {
                    "id": f"decision_fix_{finding.get('id', 'finding')}",
                    "kind": "fix_finding",
                    "title": f"Fix and retest SaaS self-attack finding: {finding.get('title', finding.get('id'))}",
                    "reason": finding.get("recommended_fix") or "Self-attack found a weakness that needs repair and retest.",
                    "queue_work": not bool(finding.get("queued")),
                    "priority": 8 if severity == "critical" else 7,
                    "finding": finding,
                    "required_retest": finding.get("benchmark_id"),
                }
            )
    if a_summary.get("executed_simulation_count", 0) < b_summary.get("unhackable_benchmark_count", 0):
        decisions.append(
            {
                "id": "decision_complete_benchmarks",
                "kind": "benchmark_gap",
                "title": "Complete all unhackable pursuit self-attack benchmarks",
                "reason": "Not every benchmark has simulation evidence yet.",
                "queue_work": True,
                "priority": 6,
            }
        )
    return decisions


def resolve_status(blueprint: dict[str, Any], attack_lab: dict[str, Any], decisions: Sequence[dict[str, Any]]) -> str:
    if not blueprint:
        return "blocked_missing_saas_blueprint"
    if not attack_lab:
        return "thinking_needs_attack_lab"
    if any(item.get("kind") == "fix_finding" for item in decisions):
        return "thinking_with_actionable_findings"
    if (attack_lab.get("summary") or {}).get("blocked_scope_count", 0):
        return "blocked_attack_scope"
    return "thinking_on_feet"


def build_saas_cognitive_state(
    repo_root: Optional[Path] = None,
    *,
    thought_bus: Any = None,
    contract_stack: Any = None,
    vault: Any = None,
    force: bool = False,
) -> SaaSCognitiveState:
    bridge = SaaSCognitiveBridge(repo_root, thought_bus=thought_bus, contract_stack=contract_stack, vault=vault)
    return bridge.load_context(force=force)


def render_markdown(state: SaaSCognitiveState) -> str:
    lines: list[str] = []
    lines.append("# HNC SaaS Cognitive Bridge")
    lines.append("")
    lines.append(f"- Generated: `{state.generated_at}`")
    lines.append(f"- Repo: `{state.repo_root}`")
    lines.append(f"- Status: `{state.status}`")
    lines.append("- Purpose: wire SaaS security into Aureon's cognitive organism so it can think on its feet")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    for key, value in state.summary.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## ThoughtBus Topics")
    lines.append("")
    for key, topic in state.thought_topics.items():
        lines.append(f"- `{key}`: `{topic}`")
    lines.append("")
    lines.append("## Questions")
    lines.append("")
    lines.append("| ID | Risk | Question | Routed systems | Next action |")
    lines.append("| --- | --- | --- | --- | --- |")
    for question in state.questions:
        lines.append(
            f"| `{question.id}` | `{question.risk}` | {question.question} | {', '.join(question.routed_systems)} | {question.next_action} |"
        )
    lines.append("")
    lines.append("## Decisions")
    lines.append("")
    lines.append("| ID | Kind | Priority | Queue work | Reason |")
    lines.append("| --- | --- | ---: | --- | --- |")
    for decision in state.decisions:
        lines.append(
            f"| `{decision.get('id')}` | `{decision.get('kind')}` | {decision.get('priority', 0)} | `{decision.get('queue_work')}` | {decision.get('reason', '')} |"
        )
    lines.append("")
    lines.append("## Safety")
    lines.append("")
    for key, value in state.safety.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in state.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def write_report(
    state: SaaSCognitiveState,
    markdown_path: Path = DEFAULT_OUTPUT_MD,
    json_path: Path = DEFAULT_OUTPUT_JSON,
    vault_path: Path = DEFAULT_VAULT_NOTE,
) -> tuple[Path, Path, Path]:
    root = Path(state.repo_root)
    md_path = markdown_path if markdown_path.is_absolute() else root / markdown_path
    js_path = json_path if json_path.is_absolute() else root / json_path
    note_path = resolve_obsidian_note_path(vault_path, repo_root=root)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    js_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_markdown(state)
    md_path.write_text(rendered, encoding="utf-8")
    js_path.write_text(json.dumps(state.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    note_path.write_text(rendered, encoding="utf-8")
    return md_path, js_path, note_path


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's HNC SaaS cognitive bridge state.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--force", action="store_true", help="Regenerate underlying SaaS context if needed.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    parser.add_argument("--vault-note", default=str(DEFAULT_VAULT_NOTE), help="Vault note path.")
    parser.add_argument("--no-write", action="store_true", help="Print summary only.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    state = build_saas_cognitive_state(root, force=args.force)
    if args.no_write:
        print(json.dumps({"status": state.status, "summary": state.summary}, indent=2, sort_keys=True))
    else:
        md_path, json_path, vault_path = write_report(state, Path(args.markdown), Path(args.json), Path(args.vault_note))
        print(
            json.dumps(
                {
                    "status": state.status,
                    "markdown": str(md_path),
                    "json": str(json_path),
                    "vault_note": str(vault_path),
                    "summary": state.summary,
                },
                indent=2,
                sort_keys=True,
            )
        )
    return 2 if state.status.startswith("blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
