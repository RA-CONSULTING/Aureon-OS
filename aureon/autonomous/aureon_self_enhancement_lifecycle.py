"""Aureon's safe self-enhancement lifecycle.

This module makes the learning loop explicit and auditable:

observe self -> understand capabilities -> detect gaps -> plan enhancements
-> queue work -> validate/apply safe learning -> create restart handoff.

It does not secretly rewrite code, reboot the machine, place trades, file
accounts, or expose secrets. Code and skill changes must pass the existing
validator/CodeArchitect path, and process restart is represented as a handoff
that a supervisor or human-owned boot path can execute.
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


SCHEMA_VERSION = "aureon-self-enhancement-lifecycle-v1"
DEFAULT_OUTPUT_MD = Path("docs/audits/aureon_self_enhancement_lifecycle.md")
DEFAULT_OUTPUT_JSON = Path("docs/audits/aureon_self_enhancement_lifecycle.json")
DEFAULT_STATE_PATH = Path("state/self_enhancement_lifecycle.json")

SAFE_ENV = {
    "AUREON_AUDIT_MODE": "1",
    "AUREON_LIVE_TRADING": "0",
    "AUREON_DISABLE_REAL_ORDERS": "1",
    "AUREON_ALLOW_SIM_FALLBACK": "0",
}


@dataclass
class LifecycleStage:
    id: str
    name: str
    status: str
    purpose: str
    evidence: dict[str, Any] = field(default_factory=dict)
    next_action: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EnhancementIntent:
    id: str
    title: str
    source: str
    priority: int
    risk: str
    route: str
    systems: list[str]
    evidence: list[str] = field(default_factory=list)
    safe_apply_mode: str = "proposal_only"
    requires_validation: bool = True
    requires_restart: bool = False
    requires_human: bool = False
    status: str = "planned"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RestartHandoff:
    required: bool
    reason: str
    preflight_command: str
    apply_command: str
    rollback_guidance: str
    mode: str = "operator_or_supervisor_confirmed"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SelfEnhancementLifecycleReport:
    schema_version: str
    generated_at: str
    repo_root: str
    status: str
    stages: list[LifecycleStage]
    enhancement_intents: list[EnhancementIntent]
    contract_plan: dict[str, Any]
    restart_handoff: RestartHandoff
    safety: dict[str, Any]
    summary: dict[str, Any]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "generated_at": self.generated_at,
            "repo_root": self.repo_root,
            "status": self.status,
            "stages": [stage.to_dict() for stage in self.stages],
            "enhancement_intents": [intent.to_dict() for intent in self.enhancement_intents],
            "contract_plan": dict(self.contract_plan),
            "restart_handoff": self.restart_handoff.to_dict(),
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


def _status(ok: bool, attention: bool = False) -> str:
    if ok and attention:
        return "working_with_attention"
    return "working" if ok else "blocked_or_missing"


def identity_stage(
    root: Path,
    readiness: dict[str, Any],
    repo_org: dict[str, Any],
    mind: dict[str, Any],
    self_catalog: Optional[dict[str, Any]] = None,
    capability_growth: Optional[dict[str, Any]] = None,
) -> LifecycleStage:
    proofs = readiness.get("proofs") or []
    capabilities = [
        {"id": proof.get("id"), "status": proof.get("status"), "summary": proof.get("summary")}
        for proof in proofs
    ]
    return LifecycleStage(
        id="identity",
        name="Self Identity And Capability Map",
        status=_status(bool(capabilities)),
        purpose="Know what Aureon is, where its parts live, and what each major capability can do.",
        evidence={
            "repo_root": str(root),
            "readiness_status": readiness.get("status"),
            "capabilities": capabilities,
            "repo_stage_count": ((repo_org.get("summary") or {}).get("stage_count")),
            "self_catalog_status": (self_catalog or {}).get("status"),
            "self_catalog_file_count": (((self_catalog or {}).get("summary") or {}).get("cataloged_file_count")),
            "capability_growth_status": (capability_growth or {}).get("status"),
            "capability_growth_latest_gap_count": (((capability_growth or {}).get("summary") or {}).get("latest_gap_count")),
            "mind_counts": mind.get("counts", {}),
        },
        next_action="Keep readiness, repo organization, and mind wiring reports fresh at boot.",
    )


def self_catalog_stage(self_catalog: dict[str, Any]) -> LifecycleStage:
    summary = self_catalog.get("summary") or {}
    file_count = int(summary.get("cataloged_file_count") or 0)
    secret_count = int(summary.get("secret_metadata_only_count") or 0)
    ok = file_count > 0
    return LifecycleStage(
        id="self_catalog",
        name="File-By-File Self Catalog",
        status=_status(ok, attention=not ok or bool(summary.get("safety_flag_counts"))),
        purpose="Know what every project file is, what subsystem owns it, and how vault/LLM context may safely use it.",
        evidence={
            "catalog_status": self_catalog.get("status") or "missing",
            "cataloged_file_count": file_count,
            "secret_metadata_only_count": secret_count,
            "excluded_infrastructure_root_count": summary.get("excluded_infrastructure_root_count"),
            "vault_memory": self_catalog.get("vault_memory") or {},
            "sample_subsystems": list((self_catalog.get("subsystem_counts") or {}).keys())[:12],
        },
        next_action="Regenerate aureon_repo_self_catalog after large repo changes so self-questioning and LLM prompts see current file labels.",
    )


def capability_growth_stage(capability_growth: dict[str, Any]) -> LifecycleStage:
    summary = capability_growth.get("summary") or {}
    ok = bool(summary)
    return LifecycleStage(
        id="capability_growth",
        name="Capability Growth Loop",
        status=_status(ok, attention=bool(summary.get("latest_gap_count"))),
        purpose="Audit, benchmark, score, improve, retest, and repeat across all organism domains.",
        evidence={
            "growth_status": capability_growth.get("status") or "missing",
            "iteration_count": summary.get("iteration_count"),
            "latest_gap_count": summary.get("latest_gap_count"),
            "latest_mean_score": summary.get("latest_mean_score"),
            "latest_registered_improvement_count": summary.get("latest_registered_improvement_count"),
            "contract_queue_persisted": summary.get("contract_queue_persisted"),
        },
        next_action="Run aureon_capability_growth_loop with safe checks, skill authoring, and contract queueing after each major change.",
    )


def code_architect_snapshot() -> dict[str, Any]:
    try:
        from aureon.code_architect import CodeArchitect, SkillLibrary

        with tempfile.TemporaryDirectory(prefix="aureon_architect_probe_") as tmp:
            library = SkillLibrary(storage_dir=Path(tmp) / "skills")
            architect = CodeArchitect(library=library, auto_wire=False)
            return {"available": True, "status": architect.get_status()}
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def self_enhancement_snapshot() -> dict[str, Any]:
    try:
        from aureon.queen.self_enhancement_engine import SelfEnhancementEngine

        with tempfile.TemporaryDirectory(prefix="aureon_enhance_probe_") as tmp:
            engine = SelfEnhancementEngine(storage_dir=Path(tmp), auto_start=False)
            return {"available": True, "status": engine.status()}
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def observation_stage(repo_org: dict[str, Any], mind: dict[str, Any], readiness: dict[str, Any]) -> LifecycleStage:
    readiness_counts = ((readiness.get("summary") or {}).get("status_counts") or {})
    repo_attention = ((repo_org.get("summary") or {}).get("attention_counts") or {})
    mind_counts = mind.get("counts") or {}
    ok = bool(repo_org) and bool(mind) and bool(readiness)
    return LifecycleStage(
        id="observe",
        name="Self Observation And Audit Gathering",
        status=_status(ok, attention=bool(repo_attention or readiness_counts.get("working_with_attention"))),
        purpose="Gather its own audits, service probes, capability proofs, repo staging, and runtime evidence.",
        evidence={
            "repo_attention_counts": repo_attention,
            "mind_counts": mind_counts,
            "readiness_status_counts": readiness_counts,
            "readiness_real_orders_allowed": ((readiness.get("summary") or {}).get("real_orders_allowed")),
        },
        next_action="Treat blocked/attention evidence as enhancement input, not as hidden logs.",
    )


def enhancement_engine_stage(code_architect: dict[str, Any], self_enhancement: dict[str, Any]) -> LifecycleStage:
    ok = bool(code_architect.get("available")) and bool(self_enhancement.get("available"))
    return LifecycleStage(
        id="authoring",
        name="Validated Skill And Code Authoring",
        status=_status(ok),
        purpose="Use SelfEnhancementEngine and CodeArchitect to turn gaps into validated skills or safe code work.",
        evidence={
            "code_architect": code_architect,
            "self_enhancement_engine": self_enhancement,
        },
        next_action="Only register generated skills after validator/sandbox pass; route repo code edits through tests.",
    )


def derive_enhancement_intents(
    repo_org: dict[str, Any],
    readiness: dict[str, Any],
    self_enhancement: dict[str, Any],
) -> list[EnhancementIntent]:
    intents: list[EnhancementIntent] = []
    repo_attention = ((repo_org.get("summary") or {}).get("attention_counts") or {})
    if repo_attention.get("runtime_state_outside_runtime_stage"):
        intents.append(
            EnhancementIntent(
                id="runtime_state_staging_policy",
                title="Create or apply runtime-state staging policy",
                source="repo_wide_organization_audit",
                priority=3,
                risk="low",
                route="safe_code_repair",
                systems=["RepoWideOrganizationAudit", "runtime_state", "tests"],
                evidence=[f"{repo_attention.get('runtime_state_outside_runtime_stage')} runtime files outside runtime stage"],
                safe_apply_mode="proposal_then_patch",
                requires_restart=False,
            )
        )
    if repo_attention.get("generated_output_inside_source_area"):
        intents.append(
            EnhancementIntent(
                id="frontend_generated_output_policy",
                title="Separate frontend generated output from source ownership",
                source="repo_wide_organization_audit",
                priority=2,
                risk="low",
                route="safe_code_repair",
                systems=["frontend", "RepoWideOrganizationAudit", "tests"],
                evidence=[f"{repo_attention.get('generated_output_inside_source_area')} generated frontend files flagged"],
                safe_apply_mode="proposal_then_patch",
                requires_restart=False,
            )
        )
    for proof in readiness.get("proofs") or []:
        status = str(proof.get("status") or "")
        if status == "blocked_or_missing":
            intents.append(
                EnhancementIntent(
                    id=f"repair_{proof.get('id', 'capability')}",
                    title=f"Repair blocked capability: {proof.get('name', proof.get('id'))}",
                    source="aureon_system_readiness_audit",
                    priority=5,
                    risk="medium",
                    route="safe_code_repair",
                    systems=list(proof.get("systems") or []),
                    evidence=[str(proof.get("summary") or "")],
                    safe_apply_mode="proposal_then_tests_then_patch",
                    requires_restart=True,
                    requires_human=True,
                )
            )
    top_gaps = (((self_enhancement.get("status") or {}).get("top_gaps")) or [])[:4]
    for gap in top_gaps:
        name = str(gap.get("suggested_name") or "new_skill")
        intents.append(
            EnhancementIntent(
                id=f"skill_gap_{name}",
                title=f"Author validated skill: {name}",
                source="SelfEnhancementEngine",
                priority=max(1, min(5, int(round(float(gap.get("priority") or 0.5) * 5)))),
                risk="low",
                route="self_enhancement_skill_authoring",
                systems=["SelfEnhancementEngine", "CodeArchitect", "SkillValidator", "SkillLibrary"],
                evidence=list(gap.get("evidence") or []) + [str(gap.get("description") or "")],
                safe_apply_mode="validator_sandbox_then_skill_library",
                requires_restart=False,
            )
        )
    intents.append(
        EnhancementIntent(
            id="refresh_self_readiness_after_changes",
            title="Re-run readiness and mind audits after each accepted enhancement",
            source="lifecycle_guard",
            priority=4,
            risk="low",
            route="run_audit_probe",
            systems=["aureon_system_readiness_audit", "mind_wiring_audit", "repo_wide_organization_audit"],
            evidence=["learning loop must prove the enhancement improved or did not regress the organism"],
            safe_apply_mode="audit_only",
            requires_restart=False,
        )
    )
    return intents


def planning_stage(intents: Sequence[EnhancementIntent]) -> LifecycleStage:
    return LifecycleStage(
        id="plan",
        name="Enhancement Planning",
        status=_status(bool(intents)),
        purpose="Convert audit evidence and skill gaps into concrete, prioritized enhancement intents.",
        evidence={
            "intent_count": len(intents),
            "routes": sorted({intent.route for intent in intents}),
            "restart_required_count": sum(1 for intent in intents if intent.requires_restart),
        },
        next_action="Queue the intents as contracts, then execute only through validators and tests.",
    )


def build_contract_plan(root: Path, intents: Sequence[EnhancementIntent], queue_contracts: bool = False) -> dict[str, Any]:
    try:
        from aureon.core.aureon_thought_bus import ThoughtBus
        from aureon.core.organism_contracts import OrganismContractStack

        if queue_contracts:
            state_path = root / "state" / "self_enhancement_contracts.json"
            thought_path = root / "state" / "self_enhancement_thoughts.jsonl"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_ctx = None
        else:
            tmp_ctx = tempfile.TemporaryDirectory(prefix="aureon_self_enhance_contracts_")
            temp_root = Path(tmp_ctx.name)
            state_path = temp_root / "contracts.json"
            thought_path = temp_root / "thoughts.jsonl"
        try:
            bus = ThoughtBus(persist_path=str(thought_path))
            stack = OrganismContractStack(
                thought_bus=bus,
                state_path=state_path,
                source="self_enhancement_lifecycle",
            )
            workflow = stack.create_goal_workflow(
                "Run the safe self-enhancement lifecycle for the Aureon organism.",
                skills=[
                    "repo_wide_organization_audit",
                    "mind_wiring_audit",
                    "system_readiness_audit",
                    "self_enhancement_engine",
                    "code_architect",
                    "skill_validator",
                ],
                route_surfaces=["self_enhancement", "contracts", "memory", "code", "validation"],
                source="self_enhancement_lifecycle",
            )
            for intent in intents[:8]:
                stack.enqueue_work_order(
                    intent.title,
                    "execute_internal_task",
                    payload={
                        "objective": intent.title,
                        "intent_id": intent.id,
                        "route": intent.route,
                        "systems": intent.systems,
                        "safe_apply_mode": intent.safe_apply_mode,
                        "requires_validation": intent.requires_validation,
                        "requires_restart": intent.requires_restart,
                    },
                    queue="organism.self_enhancement",
                    priority=intent.priority,
                    requires_human=intent.requires_human,
                    source="self_enhancement_lifecycle",
                )
            status = stack.status()
            return {
                "queued_persistently": bool(queue_contracts),
                "state_path": str(state_path),
                "thought_path": str(thought_path),
                "goal_id": workflow["goal"]["contract_id"],
                "workflow_contract_count": 4,
                "intent_work_order_count": min(len(intents), 8),
                "status": status,
            }
        finally:
            if tmp_ctx is not None:
                tmp_ctx.cleanup()
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "queued_persistently": False}


def restart_handoff_for(intents: Sequence[EnhancementIntent]) -> RestartHandoff:
    requires_restart = any(intent.requires_restart for intent in intents)
    reason = (
        "One or more planned enhancements may alter code or dependency behavior."
        if requires_restart
        else "Current planned enhancements are audit, memory, contract, or skill-library changes."
    )
    return RestartHandoff(
        required=requires_restart,
        reason=reason,
        preflight_command=(
            ".venv/bin/python -I -S -B scripts/bootstrap/protected_bootstrap_v05.py "
            "--target-id ignition"
        ),
        apply_command="HOLD: protected bootstrap does not execute the ignition target",
        rollback_guidance=(
            "Keep the previous integrated folder as fallback; do not delete state, secrets, "
            "portfolio data, accounting evidence, or exchange logs during restart."
        ),
    )


def build_self_enhancement_lifecycle(
    repo_root: Optional[Path] = None,
    *,
    queue_contracts: bool = False,
    write_state: bool = True,
) -> SelfEnhancementLifecycleReport:
    root = repo_root_from(repo_root)
    safe = apply_safe_environment()
    audits = root / "docs" / "audits"
    repo_org = load_json(audits / "repo_wide_organization_audit.json")
    self_catalog = load_json(audits / "aureon_repo_self_catalog.json")
    capability_growth = load_json(audits / "aureon_capability_growth_loop.json")
    mind = load_json(audits / "mind_wiring_audit.json")
    readiness = load_json(audits / "aureon_system_readiness_audit.json")
    code_architect = code_architect_snapshot()
    self_enhancement = self_enhancement_snapshot()
    intents = derive_enhancement_intents(repo_org, readiness, self_enhancement)
    if not ((self_catalog.get("summary") or {}).get("cataloged_file_count")):
        intents.append(
            EnhancementIntent(
                id="generate_repo_self_catalog",
                title="Generate the file-by-file repo self-catalog",
                source="self_enhancement_lifecycle",
                priority=4,
                risk="low",
                route="repo_self_catalog",
                systems=["AureonRepoSelfCatalog", "vault memory", "goal_capability_map"],
                evidence=["No current aureon_repo_self_catalog.json with file labels was found."],
                safe_apply_mode="read_only_catalog_generation",
                requires_restart=False,
            )
        )
    if not (capability_growth.get("summary") or {}):
        intents.append(
            EnhancementIntent(
                id="run_capability_growth_loop",
                title="Run the audit-benchmark-fix-retest capability growth loop",
                source="self_enhancement_lifecycle",
                priority=4,
                risk="low",
                route="capability_growth_loop",
                systems=["AureonCapabilityGrowthLoop", "CodeArchitect", "SkillLibrary", "OrganismContractStack"],
                evidence=["No current aureon_capability_growth_loop.json was found."],
                safe_apply_mode="safe_local_growth_cycle",
                requires_restart=False,
            )
        )
    stages = [
        identity_stage(root, readiness, repo_org, mind, self_catalog, capability_growth),
        self_catalog_stage(self_catalog),
        capability_growth_stage(capability_growth),
        observation_stage(repo_org, mind, readiness),
        enhancement_engine_stage(code_architect, self_enhancement),
        planning_stage(intents),
    ]
    contract_plan = build_contract_plan(root, intents, queue_contracts=queue_contracts)
    restart_handoff = restart_handoff_for(intents)
    stages.append(
        LifecycleStage(
            id="contract_queue",
            name="Contract Queue And Work Orders",
            status=_status(not contract_plan.get("error")),
            purpose="Turn enhancement intents into internal goal/task/job/work-order contracts.",
            evidence=contract_plan,
            next_action="Claim queued work through safe workers; never execute external mutations from this loop.",
        )
    )
    stages.append(
        LifecycleStage(
            id="restart_apply",
            name="Restart And Apply Handoff",
            status="working",
            purpose="Carry accepted enhancements through preflight, restart, and post-restart audit.",
            evidence=restart_handoff.to_dict(),
            next_action="Run audit-only preflight before live boot; use fallback folder if any regression appears.",
        )
    )
    blocked = [stage for stage in stages if stage.status == "blocked_or_missing"]
    attention = [stage for stage in stages if "attention" in stage.status]
    if blocked:
        status = "blocked_self_enhancement_lifecycle"
    elif attention:
        status = "working_with_attention_items"
    else:
        status = "working_safe_self_enhancement_lifecycle"
    summary = {
        "stage_count": len(stages),
        "blocked_stage_count": len(blocked),
        "attention_stage_count": len(attention),
        "enhancement_intent_count": len(intents),
        "restart_required": restart_handoff.required,
        "contracts_queued_persistently": bool(contract_plan.get("queued_persistently")),
        "code_architect_available": bool(code_architect.get("available")),
        "self_enhancement_engine_available": bool(self_enhancement.get("available")),
    }
    notes = [
        "The lifecycle can learn through audits, vault/memory, contracts, skill gaps, and validated code/skill authoring.",
        "The repo self-catalog gives self-questioning and local LLM prompts safe labels for every project file.",
        "The capability growth loop turns audit/benchmark evidence into validated skills, contracts, and retest work.",
        "Skill learning can be hot-loaded when it stays inside the SkillLibrary and passes validation.",
        "Repo code changes require tests and a restart handoff; this audit does not reboot the process.",
        "Live trading, exchange mutation, official filing, payments, and secret exposure remain outside the self-enhancement loop.",
    ]
    report = SelfEnhancementLifecycleReport(
        schema_version=SCHEMA_VERSION,
        generated_at=datetime.now(timezone.utc).isoformat(),
        repo_root=str(root),
        status=status,
        stages=stages,
        enhancement_intents=list(intents),
        contract_plan=contract_plan,
        restart_handoff=restart_handoff,
        safety={**safe, "manual_restart_handoff": True},
        summary=summary,
        notes=notes,
    )
    if write_state:
        state_path = root / DEFAULT_STATE_PATH
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str), encoding="utf-8")
    return report


def render_markdown(report: SelfEnhancementLifecycleReport) -> str:
    def md_escape(value: Any) -> str:
        return str(value).replace("|", "\\|")

    lines: list[str] = []
    lines.append("# Aureon Self-Enhancement Lifecycle")
    lines.append("")
    lines.append(f"- Generated: `{report.generated_at}`")
    lines.append(f"- Repo: `{report.repo_root}`")
    lines.append(f"- Status: `{report.status}`")
    lines.append("- Safety: audit-mode, no live orders, no filing, no payment, no forced reboot")
    lines.append("")
    lines.append("## Lifecycle Stages")
    lines.append("")
    lines.append("| Stage | Status | Purpose | Next action |")
    lines.append("| --- | --- | --- | --- |")
    for stage in report.stages:
        lines.append(
            f"| {stage.name} | `{stage.status}` | {md_escape(stage.purpose)} | {md_escape(stage.next_action)} |"
        )
    lines.append("")
    lines.append("## Enhancement Intents")
    lines.append("")
    lines.append("| Priority | Intent | Route | Apply mode | Restart |")
    lines.append("| ---: | --- | --- | --- | --- |")
    for intent in sorted(report.enhancement_intents, key=lambda item: (-item.priority, item.id)):
        lines.append(
            f"| {intent.priority} | {md_escape(intent.title)} | `{intent.route}` | `{intent.safe_apply_mode}` | `{intent.requires_restart}` |"
        )
    lines.append("")
    lines.append("## Contract Plan")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report.contract_plan, indent=2, sort_keys=True, default=str)[:2400])
    lines.append("```")
    lines.append("")
    lines.append("## Restart Handoff")
    lines.append("")
    lines.append(f"- Required: `{report.restart_handoff.required}`")
    lines.append(f"- Reason: {report.restart_handoff.reason}")
    lines.append(f"- Preflight: `{report.restart_handoff.preflight_command}`")
    lines.append(f"- Apply: `{report.restart_handoff.apply_command}`")
    lines.append(f"- Rollback: {report.restart_handoff.rollback_guidance}")
    lines.append("")
    lines.append("## Stage Evidence")
    lines.append("")
    for stage in report.stages:
        lines.append(f"### {stage.name}")
        lines.append("")
        lines.append("```json")
        text = json.dumps(stage.evidence, indent=2, sort_keys=True, default=str)
        lines.append(text[:3000] + ("\n..." if len(text) > 3000 else ""))
        lines.append("```")
        lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in report.notes:
        lines.append(f"- {note}")
    lines.append("")
    return "\n".join(lines)


def write_report(
    report: SelfEnhancementLifecycleReport,
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
    parser = argparse.ArgumentParser(description="Audit Aureon's safe self-enhancement lifecycle.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--queue-contracts", action="store_true", help="Persist enhancement work orders into state/self_enhancement_contracts.json.")
    parser.add_argument("--no-state", action="store_true", help="Do not write state/self_enhancement_lifecycle.json.")
    parser.add_argument("--no-write", action="store_true", help="Print summary without writing report artifacts.")
    parser.add_argument("--markdown", default=str(DEFAULT_OUTPUT_MD), help="Markdown report path.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="JSON manifest path.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else repo_root_from()
    report = build_self_enhancement_lifecycle(
        root,
        queue_contracts=args.queue_contracts,
        write_state=not args.no_state,
    )
    if args.no_write:
        print(json.dumps({"status": report.status, "summary": report.summary}, indent=2, sort_keys=True))
    else:
        md_path, json_path = write_report(report, Path(args.markdown), Path(args.json))
        print(json.dumps({"status": report.status, "markdown": str(md_path), "json": str(json_path), "summary": report.summary}, indent=2, sort_keys=True))
    return 2 if report.status.startswith("blocked") else 0


if __name__ == "__main__":
    raise SystemExit(main())
