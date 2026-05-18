#!/usr/bin/env python3
"""
Operator-facing Aureon coding organism bridge.

This is the live wire between an operator prompt and Aureon's existing coding
systems:
- LocalTaskQueue records the task intake.
- GoalExecutionEngine lets Aureon route/decompose the goal through its own
  goal logic.
- SafeCodeControl/QueenCodeBridge keep generated code work reviewable.
- Focused tests can run after the route so the evidence packet shows whether
  the coding lane still works.

The bridge writes an evidence packet to state/, docs/audits/, and
frontend/public/ so the console and mind hub can show what happened.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from aureon.autonomous.aureon_local_task_queue import LocalTask, LocalTaskQueue
from aureon.autonomous.aureon_safe_code_control import CodeProposal, SafeCodeControl
from aureon.autonomous.aureon_safe_desktop_control import DesktopAction, SafeDesktopControl


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = Path("state/aureon_coding_organism_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_coding_organism_bridge.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_coding_organism_bridge.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_coding_organism_bridge.json")
DEFAULT_TASK_QUEUE_PATH = Path("state/aureon_coding_organism_task_queue.json")
DEFAULT_CODE_STATE_PATH = Path("state/aureon_coding_organism_safe_code_state.json")
DEFAULT_DESKTOP_STATE_PATH = Path("state/aureon_coding_organism_desktop_state.json")
DEFAULT_DESKTOP_STOP_PATH = Path("state/aureon_coding_organism_desktop.stop")
DEFAULT_CAPABILITY_FORGE_STATE_PATH = Path("state/aureon_capability_forge_last_run.json")
DEFAULT_CAPABILITY_FORGE_AUDIT_JSON = Path("docs/audits/aureon_capability_forge.json")
DEFAULT_CAPABILITY_FORGE_PUBLIC_JSON = Path("frontend/public/aureon_capability_forge.json")
DEFAULT_CAPABILITY_STRESS_AUDIT_STATE_PATH = Path("state/aureon_capability_stress_audit_last_run.json")
DEFAULT_COMPLEX_BUILD_STRESS_AUDIT_STATE_PATH = Path("state/aureon_complex_build_stress_audit_last_run.json")
DEFAULT_CODING_CAPABILITY_UNBLOCKER_STATE_PATH = Path("state/aureon_coding_capability_unblocker_last_run.json")
DEFAULT_ARTIFACT_QUALITY_PUBLIC_JSON = Path("frontend/public/aureon_artifact_quality_report.json")
DEFAULT_CREATIVE_GUARDIAN_STATE_PATH = Path("state/aureon_agent_creative_process_guardian_last_run.json")
DEFAULT_CREATIVE_GUARDIAN_AUDIT_JSON = Path("docs/audits/aureon_agent_creative_process_guardian.json")
DEFAULT_CREATIVE_GUARDIAN_PUBLIC_JSON = Path("frontend/public/aureon_agent_creative_process_guardian.json")
DEFAULT_HNC_PROOF_MAX_AGE_SEC = 172800
HNC_PROOF_CANDIDATES = [
    Path("state/aureon_hnc_cognitive_proof.json"),
    Path("frontend/public/aureon_hnc_cognitive_proof.json"),
]
HARMONIC_AFFECT_CANDIDATES = [
    Path("docs/audits/aureon_harmonic_affect_state.json"),
    Path("frontend/public/aureon_harmonic_affect_state.json"),
]

SCOPE_STATES = [
    "needs_client_scope",
    "scope_locked",
    "team_working",
    "internal_review",
    "snagging",
    "ready_for_client",
    "client_accepted",
]

PHASE_TIMER_BLUEPRINT = [
    ("client_intake", "Estimator captures client prompt", 300),
    ("scope_of_works", "Project Manager locks deliverables and proof", 600),
    ("team_assignment", "Foreman assigns temporary agent team", 300),
    ("build_execution", "Workers build through existing Aureon routes", 1800),
    ("internal_review", "Test Pilot and CISO prove the work", 900),
    ("snagging", "Snagging Inspector clears blocking issues", 900),
    ("client_handover", "Release Manager prepares the visible handover", 300),
]

AGENT_TEAM_BLUEPRINT = [
    ("Estimator", "client_intake", "gathers missing scope and expectations"),
    ("Project Manager", "scope_of_works", "turns the prompt into a locked work order"),
    ("Foreman", "team_assignment", "assigns Aureon roles and agent capabilities"),
    ("Implementation Worker", "build_execution", "uses the existing coding route to produce changes"),
    ("Test Pilot", "internal_review", "runs focused tests and build proof"),
    ("Security Auditor", "internal_review", "checks authority boundaries and secret safety"),
    ("Snagging Inspector", "snagging", "blocks weak or unfinished handovers"),
    ("Release Manager", "client_handover", "publishes the finished client pack"),
    ("Archive Librarian", "client_handover", "records reusable job memory and evidence"),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rooted(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _jsonify(value: Any) -> Any:
    if is_dataclass(value):
        return _jsonify(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonify(v) for v in value]
    try:
        json.dumps(value)
        return value
    except TypeError:
        return repr(value)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(_jsonify(payload), indent=2, sort_keys=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    last_error: Optional[Exception] = None
    for attempt in range(8):
        try:
            tmp.write_text(content, encoding="utf-8")
            break
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.15 * (attempt + 1))
    else:
        if last_error:
            raise last_error

    for attempt in range(8):
        try:
            os.replace(tmp, path)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.25 * (attempt + 1))

    for attempt in range(8):
        try:
            path.write_text(content, encoding="utf-8")
            try:
                tmp.unlink(missing_ok=True)
            except Exception:
                pass
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(0.25 * (attempt + 1))

    try:
        tmp.unlink(missing_ok=True)
    except Exception:
        pass
    if last_error:
        raise last_error
    raise PermissionError(f"could not write {path}")


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _read_first_json(root: Path, candidates: Sequence[Path]) -> tuple[Dict[str, Any], str, float]:
    for rel_path in candidates:
        path = _rooted(root, rel_path)
        payload = _read_json(path)
        if payload:
            age_sec = max(0.0, time.time() - path.stat().st_mtime)
            return payload, str(path), age_sec
    return {}, "", 0.0


def _summarize_plan(plan: Any) -> Dict[str, Any]:
    data = _jsonify(plan)
    if not isinstance(data, dict):
        return {"raw": data}
    steps = data.get("steps") if isinstance(data.get("steps"), list) else []
    return {
        "goal_id": data.get("goal_id"),
        "objective": data.get("objective") or data.get("original_text"),
        "status": data.get("status"),
        "success_criteria": data.get("success_criteria"),
        "step_count": len(steps),
        "steps": [
            {
                "step_id": step.get("step_id"),
                "title": step.get("title"),
                "intent": step.get("intent"),
                "status": step.get("status"),
                "validation_result": step.get("validation_result"),
                "result": step.get("result"),
            }
            for step in steps
            if isinstance(step, dict)
        ],
    }


def _extract_target_files(plan_summary: Dict[str, Any]) -> List[str]:
    files: List[str] = []
    for step in plan_summary.get("steps", []):
        if not isinstance(step, dict):
            continue
        result = step.get("result") if isinstance(step.get("result"), dict) else {}
        validation = step.get("validation_result") if isinstance(step.get("validation_result"), dict) else {}
        payload = result.get("result") if isinstance(result.get("result"), dict) else {}
        for source in (result, payload, validation):
            for key in ("target_files", "files_written", "changed_files", "output_files"):
                value = source.get(key)
                if isinstance(value, list):
                    files.extend(str(item) for item in value)
                elif isinstance(value, str):
                    files.append(value)
    deduped: List[str] = []
    for item in files:
        if item and item not in deduped:
                deduped.append(item)
    return deduped[:25]


def _extract_step_payload(route: Dict[str, Any], schema_version: str) -> Dict[str, Any]:
    plan = route.get("plan") if isinstance(route.get("plan"), dict) else {}
    steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
    for step in steps:
        if not isinstance(step, dict):
            continue
        result = step.get("result") if isinstance(step.get("result"), dict) else {}
        payload = result.get("result") if isinstance(result.get("result"), dict) else {}
        if payload.get("schema_version") == schema_version:
            return payload
    return {}


def _extract_quality_payload(route: Dict[str, Any]) -> Dict[str, Any]:
    plan = route.get("plan") if isinstance(route.get("plan"), dict) else {}
    steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
    for step in steps:
        if not isinstance(step, dict):
            continue
        result = step.get("result") if isinstance(step.get("result"), dict) else {}
        payload = result.get("result") if isinstance(result.get("result"), dict) else {}
        for candidate in (
            payload.get("artifact_quality_report") if isinstance(payload, dict) else None,
            result.get("artifact_quality_report") if isinstance(result, dict) else None,
        ):
            if isinstance(candidate, dict) and candidate.get("schema_version") == "aureon-artifact-quality-report-v1":
                return candidate
    return {}


def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)


def _scope_signal_checks(prompt: str, scope_answers: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    answer_text = " ".join(str(value) for value in (scope_answers or {}).values())
    text = f"{prompt} {answer_text}".lower()
    checks = {
        "goal": _contains_any(
            text,
            [
                "add",
                "audit",
                "build",
                "create",
                "design",
                "fix",
                "generate",
                "implement",
                "inspect",
                "publish",
                "route",
                "test",
                "update",
                "wire",
            ],
        ),
        "deliverables": _contains_any(
            text,
            [
                "artifact",
                "audit",
                "bridge",
                "component",
                "dashboard",
                "docs",
                "endpoint",
                "evidence",
                "file",
                "handoff",
                "json",
                "markdown",
                "md",
                "panel",
                "patch",
                "report",
                "test",
                "tsx",
                "ui",
            ],
        ),
        "target_system": _contains_any(
            text,
            [
                ".py",
                ".tsx",
                "aureon",
                "backend",
                "bridge",
                "code",
                "coding",
                "console",
                "desktop",
                "frontend",
                "handoff",
                "repo",
                "system",
                "tests",
                "ui",
            ],
        ),
        "constraints": _contains_any(
            text,
            [
                "boundary",
                "do not",
                "keep",
                "must",
                "no ",
                "only",
                "preserve",
                "publish",
                "safe",
                "smallest",
                "without",
            ],
        ),
        "acceptance": _contains_any(
            text,
            [
                "acceptance",
                "audit",
                "build",
                "evidence",
                "pass",
                "proof",
                "report",
                "safe",
                "test",
                "validate",
                "verify",
            ],
        ),
    }
    score = sum(1 for present in checks.values() if present)
    return {
        "checks": checks,
        "score": score,
        "required_count": len(checks),
        "complete": score >= 4 and checks["goal"] and checks["deliverables"] and checks["target_system"],
        "missing": [name for name, present in checks.items() if not present],
    }


def _build_client_questions(scope_signals: Dict[str, Any]) -> List[Dict[str, Any]]:
    prompts = {
        "goal": "What exact finished outcome should Aureon produce for this client job?",
        "deliverables": "Which deliverables should be handed over: files, UI panels, reports, tests, or runbooks?",
        "target_system": "Which system, path, screen, or module should the team work on?",
        "constraints": "What must be preserved, avoided, or treated as out of scope?",
        "acceptance": "What proof must pass before Aureon is allowed to show the finished handover?",
    }
    reasons = {
        "goal": "The team cannot estimate or assign work without a clear outcome.",
        "deliverables": "The Release Manager needs a handover checklist.",
        "target_system": "The Foreman needs to route the correct workers and files.",
        "constraints": "The Security Auditor needs boundaries before work begins.",
        "acceptance": "The Snagging Inspector needs pass/fail proof before client handover.",
    }
    questions: List[Dict[str, Any]] = []
    for item in scope_signals.get("missing", []):
        questions.append(
            {
                "id": item,
                "question": prompts[item],
                "why_needed": reasons[item],
                "required": True,
                "answer": "",
            }
        )
    return questions


def _make_job_id(prompt: str, source: str, base_job_id: str = "") -> str:
    seed = f"{source}|{base_job_id}|{prompt}|{time.time_ns()}"
    return f"coding-job-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:14]}"


def _compose_execution_prompt(prompt: str, scope_answers: Optional[Dict[str, Any]]) -> str:
    answers = scope_answers or {}
    if not answers:
        return prompt
    lines = [prompt, "", "Client-approved scope answers:"]
    for key, value in answers.items():
        if str(value).strip():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _build_scope_of_works(
    *,
    prompt: str,
    scope_signals: Dict[str, Any],
    scope_answers: Optional[Dict[str, Any]],
    scope_status: str,
) -> Dict[str, Any]:
    return {
        "status": scope_status,
        "client_prompt": prompt,
        "goal": scope_answers.get("goal") if scope_answers else prompt,
        "deliverables": scope_answers.get("deliverables") if scope_answers else "derived from prompt when scope locks",
        "target_system": scope_answers.get("target_system") if scope_answers else "derived from prompt when scope locks",
        "constraints": scope_answers.get("constraints") if scope_answers else "preserve existing runtime, safety, and public interfaces",
        "acceptance": scope_answers.get("acceptance") if scope_answers else "route, proof checklist, tests/build when requested, and no blocking snags",
        "scope_signal_checks": scope_signals,
        "scope_lock_rule": "auto-lock complete prompts; otherwise require client answers",
    }


def _build_agent_team(scope_status: str) -> List[Dict[str, Any]]:
    waiting_for_scope = scope_status == "needs_client_scope"
    team: List[Dict[str, Any]] = []
    for role, phase, duty in AGENT_TEAM_BLUEPRINT:
        active = role in {"Estimator", "Project Manager"} if waiting_for_scope else True
        team.append(
            {
                "role": role,
                "phase": phase,
                "day_to_day": duty,
                "uses_whole_organism": True,
                "temporary_assignment": True,
                "status": "active" if active else "waiting_for_scope_lock",
                "hire_fire_policy": "temporary contractor memory archived after handover; no core code deleted",
            }
        )
    return team


def _build_phase_timers(scope_status: str, generated_at: str) -> List[Dict[str, Any]]:
    if scope_status == "needs_client_scope":
        completed = {"client_intake"}
        active = {"scope_of_works"}
    else:
        completed = {phase for phase, _, _ in PHASE_TIMER_BLUEPRINT}
        active = set()
    timers: List[Dict[str, Any]] = []
    for phase, label, estimate in PHASE_TIMER_BLUEPRINT:
        status = "completed" if phase in completed else "waiting_client" if phase in active else "not_started"
        timers.append(
            {
                "phase": phase,
                "label": label,
                "status": status,
                "started_at": generated_at if status in {"completed", "waiting_client"} else None,
                "completed_at": generated_at if status == "completed" else None,
                "estimated_sec": estimate,
                "elapsed_sec": 0,
                "overdue": False,
            }
        )
    return timers


def _build_proof_checklist(
    *,
    scope_locked: bool,
    route_clean: bool,
    proposal_created: bool,
    tests: Dict[str, Any],
    desktop_flow: Dict[str, Any],
    hnc_drift_proof: Dict[str, Any],
    artifact_quality_report: Optional[Dict[str, Any]] = None,
    creative_process_guardian: Optional[Dict[str, Any]] = None,
    evidence_publish_planned: bool = True,
) -> List[Dict[str, Any]]:
    tests_ok = bool(tests.get("ok")) or bool(tests.get("skipped"))
    desktop_status = desktop_flow.get("local_desktop_controller", {})
    desktop_ok = bool(desktop_status.get("ok", True)) and not bool(desktop_status.get("emergency_stopped"))
    checklist = [
        {
            "id": "scope_locked",
            "label": "Scope of works locked",
            "ok": scope_locked,
            "blocking": True,
            "evidence": "client scope complete or explicitly approved",
        },
        {
            "id": "goal_route_clean",
            "label": "Goal route completed cleanly",
            "ok": route_clean,
            "blocking": True,
            "evidence": "GoalExecutionEngine completed every route step",
        },
        {
            "id": "code_proposal_created",
            "label": "Reviewable code proposal recorded",
            "ok": proposal_created,
            "blocking": True,
            "evidence": "SafeCodeControl proposal exists",
        },
        {
            "id": "verification",
            "label": "Verification command proof",
            "ok": tests_ok,
            "blocking": True,
            "evidence": "focused tests passed or were explicitly skipped by operator",
        },
        {
            "id": "desktop_handoff_safe",
            "label": "Desktop/run handoff safe",
            "ok": desktop_ok,
            "blocking": True,
            "evidence": "SafeDesktopControl dry-run handoff is healthy",
        },
        {
            "id": "hnc_auris_drift_proof",
            "label": "HNC/Auris anti-drift proof",
            "ok": bool(hnc_drift_proof.get("ok")),
            "blocking": True,
            "evidence": hnc_drift_proof.get("summary", "HNC/Auris proof evidence not available"),
            "details": hnc_drift_proof,
        },
        {
            "id": "evidence_publish",
            "label": "Evidence publish planned",
            "ok": evidence_publish_planned,
            "blocking": True,
            "evidence": "state/docs/frontend JSON and Markdown artifacts are part of the handover",
        },
    ]
    if artifact_quality_report:
        checklist.append(
            {
                "id": "artifact_quality_gate",
                "label": "Artifact quality gate passed",
                "ok": bool(artifact_quality_report.get("handover_ready")),
                "blocking": True,
                "evidence": (
                    f"score {artifact_quality_report.get('score', 0)} / "
                    f"minimum {artifact_quality_report.get('minimum_score', 0)}"
                ),
                "details": artifact_quality_report,
            }
        )
    if creative_process_guardian:
        summary = creative_process_guardian.get("summary") if isinstance(creative_process_guardian.get("summary"), dict) else {}
        checklist.append(
            {
                "id": "agent_creative_process_guardian",
                "label": "Agent creative process guardian passed",
                "ok": bool(creative_process_guardian.get("ok")),
                "blocking": True,
                "evidence": (
                    f"roles {summary.get('creative_process_ready_role_count', 0)} / "
                    f"{summary.get('role_count', 0)} guarded; HNC/Auris {summary.get('hnc_auris_ready')}"
                ),
                "details": creative_process_guardian,
            }
        )
    return checklist


def _build_snagging_list(proof_checklist: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    snags: List[Dict[str, Any]] = []
    for item in proof_checklist:
        if item.get("blocking") and not item.get("ok"):
            snags.append(
                {
                    "id": f"snag_{item.get('id')}",
                    "title": item.get("label"),
                    "severity": "blocking",
                    "owner": "Snagging Inspector",
                    "status": "open",
                    "evidence": item.get("evidence"),
                    "next_action": "Resolve this proof item before client handover.",
                }
            )
    if not snags:
        snags.append(
            {
                "id": "client_acceptance_pending",
                "title": "Client acceptance pending",
                "severity": "notice",
                "owner": "Release Manager",
                "status": "ready_for_client_review",
                "evidence": "All blocking proof items cleared.",
                "next_action": "Present the finished handover and wait for client acceptance or a variation order.",
            }
        )
    return snags


def _build_hnc_auris_drift_proof(root: Path) -> Dict[str, Any]:
    hnc_payload, hnc_path, hnc_age_sec = _read_first_json(root, HNC_PROOF_CANDIDATES)
    harmonic_payload, harmonic_path, harmonic_age_sec = _read_first_json(root, HARMONIC_AFFECT_CANDIDATES)
    max_age_sec = float(os.environ.get("AUREON_CODING_HNC_PROOF_MAX_AGE_SEC", DEFAULT_HNC_PROOF_MAX_AGE_SEC))

    master = hnc_payload.get("master_formula") if isinstance(hnc_payload.get("master_formula"), dict) else {}
    auris = hnc_payload.get("auris_nodes") if isinstance(hnc_payload.get("auris_nodes"), dict) else {}
    hnc_passed = bool(hnc_payload.get("passed")) or str(hnc_payload.get("status", "")).lower() == "passing"
    master_passed = bool(master.get("passed", hnc_passed))
    auris_passed = bool(auris.get("passed", hnc_passed))
    hnc_fresh = bool(hnc_payload) and hnc_age_sec <= max_age_sec

    signals = harmonic_payload.get("signals") if isinstance(harmonic_payload.get("signals"), dict) else {}
    cognitive = signals.get("cognitive_trade_summary") if isinstance(signals.get("cognitive_trade_summary"), dict) else {}
    organism = signals.get("organism_summary") if isinstance(signals.get("organism_summary"), dict) else {}
    affect_summary = harmonic_payload.get("summary") if isinstance(harmonic_payload.get("summary"), dict) else {}

    warnings: List[str] = []
    blockers: List[str] = []
    if not hnc_payload:
        blockers.append("hnc_cognitive_proof_missing")
    if hnc_payload and not hnc_passed:
        blockers.append("hnc_cognitive_proof_not_passing")
    if hnc_payload and not master_passed:
        blockers.append("hnc_master_formula_not_passing")
    if hnc_payload and not auris_passed:
        blockers.append("auris_nodes_not_passing")
    if hnc_payload and not hnc_fresh:
        blockers.append("hnc_cognitive_proof_stale")
    if not harmonic_payload:
        warnings.append("harmonic_affect_state_missing")
    if cognitive.get("runtime_stale") is True:
        warnings.append("harmonic_affect_runtime_stale")
    if organism.get("runtime_feed_status") in {"offline", "stale"}:
        warnings.append(f"organism_runtime_feed_{organism.get('runtime_feed_status')}")
    safety_blockers = affect_summary.get("safety_blocker_count")
    if isinstance(safety_blockers, (int, float)) and safety_blockers > 0:
        warnings.append(f"harmonic_affect_safety_blockers_{int(safety_blockers)}")

    ok = not blockers
    return {
        "ok": ok,
        "status": "hnc_auris_drift_proof_passed" if ok else "hnc_auris_drift_proof_blocked",
        "summary": (
            "HNC proof, master formula, and Auris nodes are present, passing, and fresh enough."
            if ok
            else "HNC/Auris proof cannot clear the client handover."
        ),
        "hnc_proof_path": hnc_path,
        "hnc_proof_age_sec": round(hnc_age_sec, 3) if hnc_path else None,
        "hnc_proof_max_age_sec": max_age_sec,
        "harmonic_affect_path": harmonic_path,
        "harmonic_affect_age_sec": round(harmonic_age_sec, 3) if harmonic_path else None,
        "hnc_passed": hnc_passed,
        "master_formula_passed": master_passed,
        "auris_nodes_passed": auris_passed,
        "hnc_fresh": hnc_fresh,
        "coherence": master.get("score") or auris.get("coherence") or affect_summary.get("hnc_coherence_score"),
        "runtime_drift_warnings": warnings,
        "blockers": blockers,
    }


def _blocking_snag_count(snagging_list: List[Dict[str, Any]]) -> int:
    return len([item for item in snagging_list if item.get("severity") == "blocking" and item.get("status") != "resolved"])


def _build_client_job(
    *,
    prompt: str,
    source: str,
    scope_status: str,
    scope_signals: Dict[str, Any],
    scope_answers: Optional[Dict[str, Any]],
    base_job_id: str = "",
) -> Dict[str, Any]:
    generated_at = utc_now()
    questions = [] if scope_status != "needs_client_scope" else _build_client_questions(scope_signals)
    job_id = _make_job_id(prompt, source, base_job_id=base_job_id)
    return {
        "schema_version": "aureon-client-job-construction-flow-v1",
        "job_id": job_id,
        "base_job_id": base_job_id,
        "variation_order": {
            "created": bool(base_job_id),
            "base_job_id": base_job_id,
            "reason": "client scope approval or scope revision supplied through the prompt lane" if base_job_id else "",
        },
        "scope_states": list(SCOPE_STATES),
        "scope_status": scope_status,
        "scope_locked": scope_status != "needs_client_scope",
        "scope_of_works": _build_scope_of_works(
            prompt=prompt,
            scope_signals=scope_signals,
            scope_answers=scope_answers or {},
            scope_status=scope_status,
        ),
        "client_questions": questions,
        "scope_answers": scope_answers or {},
        "agent_team": _build_agent_team(scope_status),
        "phase_timers": _build_phase_timers(scope_status, generated_at),
        "proof_checklist": [],
        "snagging_list": [],
        "handover_status": {
            "state": "held_for_scope" if scope_status == "needs_client_scope" else "internal_proof_running",
            "client_visible_product": False,
            "reason": "Scope questions must be answered before the agent team starts."
            if scope_status == "needs_client_scope"
            else "Internal proof and snagging must pass before client handover.",
        },
    }


def _default_test_command(root: Path) -> List[str]:
    return [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_safe_code_control.py",
        "tests/test_coding_agent_skill_base.py",
        "-q",
    ]


def _run_test_commands(root: Path, commands: Optional[Sequence[Sequence[str]]] = None, timeout_sec: int = 180) -> Dict[str, Any]:
    commands = list(commands or [_default_test_command(root)])
    results: List[Dict[str, Any]] = []
    for command in commands:
        started = time.time()
        try:
            completed = subprocess.run(
                list(command),
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )
            results.append(
                {
                    "command": list(command),
                    "returncode": completed.returncode,
                    "duration_sec": round(time.time() - started, 3),
                    "stdout_tail": completed.stdout[-4000:],
                    "stderr_tail": completed.stderr[-4000:],
                    "ok": completed.returncode == 0,
                }
            )
        except subprocess.TimeoutExpired as exc:
            results.append(
                {
                    "command": list(command),
                    "returncode": None,
                    "duration_sec": round(time.time() - started, 3),
                    "stdout_tail": (exc.stdout or "")[-4000:] if isinstance(exc.stdout, str) else "",
                    "stderr_tail": (exc.stderr or "")[-4000:] if isinstance(exc.stderr, str) else "",
                    "ok": False,
                    "error": "timeout",
                }
            )
        except Exception as exc:
            results.append(
                {
                    "command": list(command),
                    "returncode": None,
                    "duration_sec": round(time.time() - started, 3),
                    "stdout_tail": "",
                    "stderr_tail": "",
                    "ok": False,
                    "error": str(exc),
                }
            )
    return {
        "ok": all(item.get("ok") for item in results) if results else True,
        "command_count": len(results),
        "results": results,
    }


def _build_desktop_run_flow(root: Path, prompt: str, source: str) -> Dict[str, Any]:
    controller = SafeDesktopControl(
        state_path=_rooted(root, DEFAULT_DESKTOP_STATE_PATH),
        kill_path=_rooted(root, DEFAULT_DESKTOP_STOP_PATH),
        dry_run=True,
    )
    handoff_text = (
        "Aureon coding product audit ready. Open http://127.0.0.1:8081/ "
        "and inspect the Aureon Coding Organism panel."
    )
    handoff = controller.propose(
        DesktopAction(
            action="type_text",
            params={"text": handoff_text},
            source=f"coding_organism:{source}",
        )
    )

    vm_tools: Dict[str, Any]
    try:
        from aureon.autonomous.vm_control.tools import VM_TOOL_NAMES

        vm_tools = {
            "available": True,
            "tool_count": len(VM_TOOL_NAMES),
            "tools": list(VM_TOOL_NAMES),
        }
    except Exception as exc:
        vm_tools = {"available": False, "tool_count": 0, "tools": [], "error": str(exc)}

    return {
        "status": "desktop_run_handoff_ready",
        "prompt": prompt,
        "local_desktop_controller": controller.status(),
        "desktop_handoff_action": handoff,
        "remote_vm_control": vm_tools,
        "run_surfaces": {
            "unified_console": "http://127.0.0.1:8081/",
            "coding_status": "http://127.0.0.1:13002/api/coding/status",
            "coding_prompt": "POST http://127.0.0.1:13002/api/coding/prompt",
        },
        "operator_flow": [
            "prompt Aureon",
            "route through GoalExecutionEngine",
            "write/propose code through safe coding path",
            "run focused tests/builds",
            "audit finished-product evidence",
            "use desktop/VM tools only through armed safe controllers",
        ],
        "safety": {
            "desktop_default": "dry_run",
            "desktop_live_requires": "explicit arm plus allowed action",
            "queued_action": "type_text handoff only; not auto-executed by the bridge",
        },
    }


def _build_finished_product_audit(
    *,
    route: Dict[str, Any],
    tests: Dict[str, Any],
    desktop_flow: Dict[str, Any],
    root: Path,
    prompt: str,
    client_job: Optional[Dict[str, Any]] = None,
    proof_checklist: Optional[List[Dict[str, Any]]] = None,
    snagging_list: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    route_ok = _route_is_clean(route)
    tests_ok = bool(tests.get("ok")) or bool(tests.get("skipped"))
    desktop_status = desktop_flow.get("local_desktop_controller", {})
    desktop_ready = bool(desktop_status.get("ok", True)) and not bool(desktop_status.get("emergency_stopped"))
    scope_locked = bool((client_job or {}).get("scope_locked", True))
    blocking_snags = _blocking_snag_count(snagging_list or [])
    ready = scope_locked and route_ok and tests_ok and desktop_ready and blocking_snags == 0
    if not scope_locked:
        status = "finished_product_scope_pending"
    elif ready:
        status = "finished_product_ready"
    else:
        status = "finished_product_attention"
    return {
        "status": status,
        "ready_to_run": ready,
        "ready_for_client": ready,
        "prompt": prompt,
        "stages": [
            {"stage": "user_prompt", "ok": True, "evidence": "prompt captured"},
            {"stage": "scope_of_works", "ok": scope_locked, "evidence": "scope locked before agent team handoff"},
            {"stage": "cognitive_route", "ok": route_ok, "evidence": "GoalExecutionEngine.submit_goal"},
            {"stage": "code_authoring", "ok": route_ok, "evidence": "SafeCodeControl proposal and any QueenCodeArchitect output"},
            {"stage": "verification", "ok": tests_ok, "evidence": "focused test command results"},
            {"stage": "desktop_run_handoff", "ok": desktop_ready, "evidence": "SafeDesktopControl and VM tool availability"},
            {"stage": "evidence_publish", "ok": True, "evidence": "state/docs/frontend JSON and Markdown artifacts"},
            {"stage": "snagging", "ok": blocking_snags == 0, "evidence": f"{blocking_snags} blocking snag(s)"},
        ],
        "proof_checklist": proof_checklist or [],
        "snagging_list": snagging_list or [],
        "handover_status": {
            "state": "ready_for_client" if ready else "held_for_internal_completion",
            "client_visible_product": ready,
            "blocking_snag_count": blocking_snags,
            "reason": "All proof and snagging gates passed."
            if ready
            else "Finished product is hidden until scope, proof, and snagging gates pass.",
        },
        "runbook": {
            "console": "http://127.0.0.1:8081/",
            "coding_status": "http://127.0.0.1:13002/api/coding/status",
            "terminal_prompt": (
                ".\\.venv\\Scripts\\python.exe -m aureon.autonomous.aureon_coding_organism_bridge "
                "--prompt \"Aureon, inspect this coding goal, propose the safest route, and run focused tests.\""
            ),
            "full_organism": ".\\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791",
        },
        "evidence_paths": {
            "state": str(_rooted(root, DEFAULT_STATE_PATH)),
            "audit_json": str(_rooted(root, DEFAULT_AUDIT_JSON)),
            "audit_md": str(_rooted(root, DEFAULT_AUDIT_MD)),
            "public_json": str(_rooted(root, DEFAULT_PUBLIC_JSON)),
            "capability_forge_state": str(_rooted(root, DEFAULT_CAPABILITY_FORGE_STATE_PATH)),
            "capability_forge_audit": str(_rooted(root, DEFAULT_CAPABILITY_FORGE_AUDIT_JSON)),
            "capability_forge_public": str(_rooted(root, DEFAULT_CAPABILITY_FORGE_PUBLIC_JSON)),
            "artifact_quality_public": str(_rooted(root, DEFAULT_ARTIFACT_QUALITY_PUBLIC_JSON)),
            "creative_guardian_state": str(_rooted(root, DEFAULT_CREATIVE_GUARDIAN_STATE_PATH)),
            "creative_guardian_audit": str(_rooted(root, DEFAULT_CREATIVE_GUARDIAN_AUDIT_JSON)),
            "creative_guardian_public": str(_rooted(root, DEFAULT_CREATIVE_GUARDIAN_PUBLIC_JSON)),
            "desktop_state": str(_rooted(root, DEFAULT_DESKTOP_STATE_PATH)),
        },
    }


def _shorten(value: Any, limit: int = 900) -> str:
    text = value if isinstance(value, str) else json.dumps(_jsonify(value), sort_keys=True)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _build_work_journal(
    *,
    prompt: str,
    source: str,
    task: Any,
    route: Dict[str, Any],
    proposal: Any,
    tests: Dict[str, Any],
    desktop_flow: Dict[str, Any],
    product_audit: Dict[str, Any],
    evidence_core: Dict[str, Any],
    target_files: List[str],
    agent_company_report: Optional[Dict[str, Any]] = None,
    capability_forge_report: Optional[Dict[str, Any]] = None,
    artifact_quality_report: Optional[Dict[str, Any]] = None,
    creative_process_guardian: Optional[Dict[str, Any]] = None,
    coding_capability_unblocker: Optional[Dict[str, Any]] = None,
    client_job: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build the operator-facing trail from prompt to finished files."""
    plan = route.get("plan") if isinstance(route.get("plan"), dict) else {}
    steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
    evidence_paths = product_audit.get("evidence_paths") if isinstance(product_audit.get("evidence_paths"), dict) else {}
    published_files = [str(value) for value in evidence_paths.values() if value]
    client_job = client_job or {}
    scope_status = client_job.get("scope_status", "scope_locked")
    client_questions = client_job.get("client_questions") if isinstance(client_job.get("client_questions"), list) else []
    stage_rows: List[Dict[str, Any]] = [
        {
            "id": "prompt_received",
            "title": "Prompt received",
            "status": "completed",
            "ok": True,
            "summary": "Aureon captured the operator goal and source.",
            "evidence": {"source": source, "prompt_preview": prompt[:220]},
        },
        {
            "id": "task_queued",
            "title": "Task queued",
            "status": "completed",
            "ok": True,
            "summary": "LocalTaskQueue accepted the work item.",
            "evidence": {
                "queue_status": _jsonify(task).get("status") if isinstance(_jsonify(task), dict) else "",
                "kind": _jsonify(task).get("kind") if isinstance(_jsonify(task), dict) else "",
            },
        },
        {
            "id": "scope_of_works",
            "title": "Scope of works",
            "status": "completed" if scope_status != "needs_client_scope" else "waiting_client",
            "ok": scope_status != "needs_client_scope",
            "summary": (
                "Scope locked; Aureon can hand this job to the agent team."
                if scope_status != "needs_client_scope"
                else f"Scope is missing {len(client_questions)} required answer(s); the agent team is held."
            ),
            "evidence": {
                "job_id": client_job.get("job_id"),
                "scope_status": scope_status,
                "scope_locked": client_job.get("scope_locked"),
                "missing": ((client_job.get("scope_of_works") or {}).get("scope_signal_checks") or {}).get("missing", []),
                "client_questions": client_questions,
            },
        },
        {
            "id": "agent_team_assignment",
            "title": "Agent team assignment",
            "status": "completed" if scope_status != "needs_client_scope" else "waiting_scope_lock",
            "ok": scope_status != "needs_client_scope",
            "summary": (
                "Estimator, Project Manager, Foreman, Workers, Test Pilot, Snagging Inspector, Release Manager, and Archive Librarian assigned."
                if scope_status != "needs_client_scope"
                else "Only Estimator and Project Manager are active until the client answers the scope questions."
            ),
            "evidence": {"agent_team": client_job.get("agent_team", []), "phase_timers": client_job.get("phase_timers", [])},
        },
        {
            "id": "goal_routed",
            "title": "Goal routed",
            "status": "completed" if route.get("ok") else "held_for_scope" if route.get("skipped") else "attention",
            "ok": bool(route.get("ok")),
            "summary": (
                f"GoalExecutionEngine selected {len(steps)} step(s)."
                if not route.get("skipped")
                else "GoalExecutionEngine did not run because scope is not locked."
            ),
            "evidence": {
                "objective": plan.get("objective"),
                "plan_status": plan.get("status"),
                "success_criteria": plan.get("success_criteria"),
                "skipped": route.get("skipped", False),
                "skip_reason": route.get("skip_reason", ""),
            },
        },
    ]

    for index, step in enumerate(steps, start=1):
        result = step.get("result") if isinstance(step.get("result"), dict) else {}
        payload = result.get("result") if isinstance(result.get("result"), dict) else {}
        validation = step.get("validation_result") if isinstance(step.get("validation_result"), dict) else {}
        summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
        completion = payload.get("completion_report") if isinstance(payload.get("completion_report"), dict) else {}
        stage_rows.append(
            {
                "id": f"goal_step_{index}",
                "title": step.get("title") or step.get("intent") or f"Goal step {index}",
                "status": step.get("status") or "unknown",
                "ok": step.get("status") in ("completed", "success", "ok") and validation.get("valid") is not False,
                "summary": validation.get("reason") or _shorten(summary or result, 280),
                "evidence": {
                    "intent": step.get("intent"),
                    "tool_used": result.get("tool_used"),
                    "validation": validation,
                    "summary": summary,
                    "completion_report": completion,
                    "write_info": payload.get("write_info"),
                },
            }
        )

    if agent_company_report:
        company_summary = agent_company_report.get("summary", {})
        stage_rows.append(
            {
                "id": "agent_company_bill_list",
                "title": "Agent company bill list published",
                "status": "completed",
                "ok": bool((agent_company_report.get("completion_report") or {}).get("did_build_company_registry")),
                "summary": (
                    f"{company_summary.get('role_count', 0)} role(s), "
                    f"{company_summary.get('department_count', 0)} department(s), "
                    f"{company_summary.get('work_order_count', 0)} work order(s), "
                    f"{company_summary.get('roles_with_day_plan_count', 0)} daily plan(s), "
                    f"{company_summary.get('roles_with_whole_organism_access_count', 0)} whole-organism access map(s), "
                    f"{company_summary.get('agency_workforce_role_count', 0)} agency role(s), "
                    f"{company_summary.get('sha256_memory_entry_count', 0)} memory pack(s)."
                ),
                "evidence": {
                    "company_name": agent_company_report.get("company_name"),
                    "summary": company_summary,
                    "published_files": agent_company_report.get("output_files", []),
                    "authority_boundaries": agent_company_report.get("authority_boundaries", []),
                    "daily_operating_loop": agent_company_report.get("daily_operating_loop", []),
                    "whole_organism_access_policy": agent_company_report.get("whole_organism_access_policy", {}),
                    "prompt_client_job_lifecycle": agent_company_report.get("prompt_client_job_lifecycle", []),
                    "workforce_memory_phonebook": agent_company_report.get("workforce_memory_phonebook", {}),
                },
            }
        )

    if capability_forge_report or artifact_quality_report:
        forge_summary = (capability_forge_report or {}).get("summary", {})
        quality = artifact_quality_report or (capability_forge_report or {}).get("artifact_quality_report", {})
        stage_rows.append(
            {
                "id": "capability_forge_quality_gate",
                "title": "Capability forge and quality gate",
                "status": (capability_forge_report or {}).get("status") or (quality or {}).get("status") or "artifact_quality_checked",
                "ok": bool((quality or {}).get("handover_ready")),
                "summary": (
                    f"Task family {(capability_forge_report or {}).get('task_family', (quality or {}).get('task_family', 'artifact'))}; "
                    f"quality score {(quality or {}).get('score', 0)}; "
                    f"{len((quality or {}).get('snags', []))} quality snag(s)."
                ),
                "evidence": {
                    "capability_forge": capability_forge_report or {},
                    "artifact_quality_report": quality or {},
                    "summary": forge_summary,
                    "approval_state": (capability_forge_report or {}).get("approval_state", client_job.get("approval_state", {})),
                },
            }
        )

    if creative_process_guardian:
        guardian_summary = creative_process_guardian.get("summary", {})
        stage_rows.append(
            {
                "id": "agent_creative_process_guardian",
                "title": "Agent creative process guardian",
                "status": creative_process_guardian.get("status", "agent_creative_process_guardian_checked"),
                "ok": bool(creative_process_guardian.get("ok")),
                "summary": (
                    f"{guardian_summary.get('creative_process_ready_role_count', 0)} / "
                    f"{guardian_summary.get('role_count', 0)} role process(es) guarded; "
                    f"{guardian_summary.get('present_mind_source_count', 0)} mind source(s) present."
                ),
                "evidence": {
                    "summary": guardian_summary,
                    "proof_checklist": creative_process_guardian.get("proof_checklist", []),
                    "snagging_list": creative_process_guardian.get("snagging_list", []),
                    "organism_mind_contract": creative_process_guardian.get("organism_mind_contract", {}),
                    "published_files": creative_process_guardian.get("output_files", []),
                },
            }
        )

    if coding_capability_unblocker:
        unblock_summary = coding_capability_unblocker.get("summary", {})
        stage_rows.append(
            {
                "id": "coding_capability_unblocker",
                "title": "Coding capability gates",
                "status": coding_capability_unblocker.get("status", "coding_capability_gates_checked"),
                "ok": True,
                "summary": (
                    f"{unblock_summary.get('ready_gate_count', 0)} / "
                    f"{unblock_summary.get('gate_count', 0)} coding gate(s) open; "
                    f"{unblock_summary.get('converted_coding_blocker_count', 0)} blocker(s) converted to autonomous gates."
                ),
                "evidence": {
                    "summary": unblock_summary,
                    "autonomous_gates": coding_capability_unblocker.get("autonomous_gates", []),
                    "source_discovery_routes": coding_capability_unblocker.get("source_discovery_routes", []),
                    "autonomous_work_orders": coding_capability_unblocker.get("autonomous_work_orders", []),
                    "published_files": coding_capability_unblocker.get("output_files", []),
                },
            }
        )

    stage_rows.extend(
        [
            {
                "id": "code_proposal",
                "title": "Code proposal recorded",
                "status": "completed" if proposal else "attention",
                "ok": bool(proposal),
                "summary": "SafeCodeControl recorded a reviewable proposal and target-file list.",
                "evidence": {
                    "target_files": target_files,
                    "proposal_status": _jsonify(proposal).get("status") if isinstance(_jsonify(proposal), dict) else "",
                },
            },
            {
                "id": "verification",
                "title": "Verification ran",
                "status": "completed" if tests.get("ok") else "attention",
                "ok": bool(tests.get("ok")),
                "summary": f"{tests.get('command_count', 0)} command(s), tests {'passed' if tests.get('ok') else 'need attention'}.",
                "evidence": {
                    "commands": [
                        {
                            "command": " ".join(item.get("command", [])) if isinstance(item.get("command"), list) else item.get("command"),
                            "returncode": item.get("returncode"),
                            "duration_sec": item.get("duration_sec"),
                            "ok": item.get("ok"),
                            "stdout_tail": _shorten(item.get("stdout_tail", ""), 360),
                            "stderr_tail": _shorten(item.get("stderr_tail", ""), 360),
                        }
                        for item in tests.get("results", [])
                        if isinstance(item, dict)
                    ],
                    "skipped": tests.get("skipped", False),
                },
            },
            {
                "id": "desktop_handoff",
                "title": "Desktop/run handoff prepared",
                "status": desktop_flow.get("status", "unknown"),
                "ok": desktop_flow.get("status") != "desktop_run_handoff_attention",
                "summary": "Desktop/VM capability was checked and kept dry-run unless armed.",
                "evidence": {
                    "dry_run": (desktop_flow.get("local_desktop_controller") or {}).get("dry_run"),
                    "vm_tool_count": (desktop_flow.get("remote_vm_control") or {}).get("tool_count", 0),
                    "safety": desktop_flow.get("safety", {}),
                },
            },
            {
                "id": "evidence_published",
                "title": "Evidence published",
                "status": "completed",
                "ok": True,
                "summary": "Aureon wrote state, audit, public JSON, and Markdown evidence.",
                "evidence": {
                    "published_files": published_files,
                    "who_what_where_when_how": {
                        key: evidence_core.get(key, {}) for key in ("who", "what", "where", "when", "how", "act")
                    },
                },
            },
            {
                "id": "finished_product",
                "title": "Finished product status",
                "status": product_audit.get("status", "pending"),
                "ok": bool(product_audit.get("ready_to_run")),
                "summary": "Ready for client handover." if product_audit.get("ready_to_run") else "Held until scope, proof, and snagging pass.",
                "evidence": {
                    "ready_to_run": product_audit.get("ready_to_run"),
                    "handover_status": product_audit.get("handover_status", {}),
                    "proof_checklist": product_audit.get("proof_checklist", []),
                    "snagging_list": product_audit.get("snagging_list", []),
                    "runbook": product_audit.get("runbook", {}),
                },
            },
        ]
    )

    return {
        "schema_version": "aureon-coding-work-journal-v1",
        "generated_at": utc_now(),
        "status": "complete" if all(row.get("ok") for row in stage_rows) else "attention",
        "stage_count": len(stage_rows),
        "completed_count": len([row for row in stage_rows if row.get("ok")]),
        "attention_count": len([row for row in stage_rows if not row.get("ok")]),
        "published_files": published_files,
        "target_files": target_files,
        "stages": stage_rows,
    }


def _build_goal_engine() -> Any:
    from aureon.core.goal_execution_engine import GoalExecutionEngine

    return GoalExecutionEngine()


def _route_is_clean(route: Dict[str, Any]) -> bool:
    """Return True only when the goal engine actually completed its route."""
    if not route.get("ok"):
        return False
    plan = route.get("plan") if isinstance(route.get("plan"), dict) else {}
    if plan.get("status") not in ("completed", "success", "ok"):
        return False
    steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
    for step in steps:
        if not isinstance(step, dict):
            continue
        if step.get("status") not in ("completed", "success", "ok"):
            return False
        validation = step.get("validation_result")
        if isinstance(validation, dict) and validation.get("valid") is False:
            return False
    return True


def _route_goal(prompt: str, goal_engine: Any = None) -> Dict[str, Any]:
    engine = goal_engine or _build_goal_engine()
    try:
        plan = engine.submit_goal(prompt)
        return {"ok": True, "plan": _summarize_plan(plan), "engine_status": _jsonify(getattr(engine, "get_status", lambda: {})())}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "plan": {}, "engine_status": {}}


def _is_interactive_app_prompt(prompt: str) -> bool:
    text = str(prompt or "").lower()
    if any(keyword in text for keyword in ("video", "clip", "animation", "mp4", "webm", "image", "picture", "draw")):
        return False
    return any(
        keyword in text
        for keyword in (
            "game",
            "playable",
            "keyboard",
            "arrow key",
            "wasd",
            "player",
            "level",
            "html app",
            "walks up",
        )
    )


def _prefer_adaptive_forge_prompt(prompt: str) -> bool:
    text = str(prompt or "").lower()
    if any(keyword in text for keyword in ("video", "clip", "animation", "mp4", "webm", "image", "picture", "draw", "pdf", "document")):
        return False
    if any(keyword in text for keyword in ("full stack", "full-stack", "frontend and backend", "backend api", "api server", "crud app")):
        return True
    return _is_interactive_app_prompt(prompt) or any(
        keyword in text
        for keyword in (
            "local tool",
            "tool",
            "skill",
            "calculator",
            "converter",
            "generator",
            "workflow",
            "micro app",
            "html app",
            "code on the fly",
            "on the fly",
        )
    )


def _is_build_prompt(prompt: str) -> bool:
    text = str(prompt or "").lower()
    return any(
        keyword in text
        for keyword in (
            "build",
            "make",
            "create",
            "code",
            "write",
            "ui",
            "app",
            "game",
            "tool",
            "skill",
            "calculator",
            "converter",
            "generator",
            "workflow",
            "implement",
            "fix",
            "repair",
            "enhance",
            "adapt",
        )
    )


def _route_mentions_agentcore_unavailable(value: Any) -> bool:
    if isinstance(value, dict):
        return any(_route_mentions_agentcore_unavailable(item) for item in value.values())
    if isinstance(value, list):
        return any(_route_mentions_agentcore_unavailable(item) for item in value)
    return "agentcore not available" in str(value or "").lower()


def _route_local_capability_forge(prompt: str, root: Path, *, previous_route: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    try:
        from aureon.autonomous.aureon_capability_forge import build_and_write_capability_forge

        report = build_and_write_capability_forge(prompt, root=root)
        manifest = report.get("artifact_manifest") if isinstance(report.get("artifact_manifest"), dict) else {}
        output_files = [str(item) for item in report.get("output_files", []) if item]
        for key in ("asset_path", "metadata_path", "preview_path", "public_url", "preview_url"):
            value = manifest.get(key)
            if value and str(value) not in output_files:
                output_files.append(str(value))
        validation = {
            "valid": bool(report.get("handover_ready")),
            "reason": "Local capability forge produced adaptive artifact/code evidence without AgentCore",
            "changed_files": output_files,
        }
        step = {
            "step_id": "adaptive-capability-forge",
            "title": "Build through local adaptive capability forge",
            "intent": "capability_forge",
            "status": "completed" if report.get("ok") else "attention",
            "validation_result": validation,
            "result": {
                "success": bool(report.get("ok")),
                "tool_used": "capability_forge",
                "target_files": output_files,
                "files_written": output_files,
                "output_files": output_files,
                "result": report,
            },
        }
        return {
            "ok": bool(report.get("ok")),
            "fallback_from_agentcore": bool(previous_route),
            "previous_route": previous_route or {},
            "plan": {
                "goal_id": report.get("job_id", "adaptive-capability-forge"),
                "objective": prompt,
                "status": "completed" if report.get("ok") else "attention",
                "success_criteria": "adaptive local artifact/code evidence, quality proof, and approval state",
                "step_count": 1,
                "steps": [step],
            },
            "engine_status": {
                "route": "local_capability_forge",
                "agentcore_required": False,
                "adaptive_skill_created": (report.get("summary") or {}).get("adaptive_skill_created", False),
            },
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "plan": {},
            "engine_status": {"route": "local_capability_forge", "agentcore_required": False},
        }


def _make_markdown(evidence: Dict[str, Any]) -> str:
    summary = evidence.get("summary", {})
    lines = [
        "# Aureon Coding Organism Bridge",
        "",
        f"- status: {evidence.get('status')}",
        f"- generated_at: {evidence.get('generated_at')}",
        f"- prompt: {evidence.get('prompt')}",
        f"- goal_engine_routed: {summary.get('goal_engine_routed')}",
        f"- safe_code_proposal_created: {summary.get('safe_code_proposal_created')}",
        f"- tests_ok: {summary.get('tests_ok')}",
        "",
        "## Who What Where When How Act",
    ]
    for key in ("who", "what", "where", "when", "how", "act"):
        lines.append(f"- {key}: {json.dumps(_jsonify(evidence.get(key, {})), sort_keys=True)}")
    client_job = evidence.get("client_job", {})
    if isinstance(client_job, dict) and client_job:
        lines.extend(
            [
                "",
                "## Client Job Construction Flow",
                f"- job_id: {client_job.get('job_id')}",
                f"- scope_status: {client_job.get('scope_status')}",
                f"- scope_locked: {client_job.get('scope_locked')}",
                f"- client_questions: {len(client_job.get('client_questions', []))}",
                f"- blocking_snags: {_blocking_snag_count(client_job.get('snagging_list', []))}",
            ]
        )
    plan = evidence.get("goal_route", {}).get("plan", {})
    if plan:
        lines.extend(["", "## Goal Steps"])
        for step in plan.get("steps", []):
            lines.append(f"- {step.get('intent')}: {step.get('title')} ({step.get('status')})")
    return "\n".join(lines) + "\n"


def submit_coding_prompt(
    prompt: str,
    *,
    source: str = "operator",
    run_tests: bool = True,
    root: Optional[Path] = None,
    goal_engine: Any = None,
    test_commands: Optional[Sequence[Sequence[str]]] = None,
    test_timeout_sec: int = 180,
    include_desktop: bool = True,
    scope_answers: Optional[Dict[str, Any]] = None,
    scope_approved: bool = False,
    base_job_id: str = "",
) -> Dict[str, Any]:
    root = Path(root or REPO_ROOT).resolve()
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        raise ValueError("prompt is required")

    state_path = _rooted(root, DEFAULT_STATE_PATH)
    audit_json = _rooted(root, DEFAULT_AUDIT_JSON)
    audit_md = _rooted(root, DEFAULT_AUDIT_MD)
    public_json = _rooted(root, DEFAULT_PUBLIC_JSON)

    queue = LocalTaskQueue(state_path=_rooted(root, DEFAULT_TASK_QUEUE_PATH))
    controller = SafeCodeControl(state_path=_rooted(root, DEFAULT_CODE_STATE_PATH))
    scope_signals = _scope_signal_checks(prompt_text, scope_answers=scope_answers)
    scope_locked = bool(scope_approved or scope_signals.get("complete"))
    scope_status = "scope_locked" if scope_locked else "needs_client_scope"
    client_job = _build_client_job(
        prompt=prompt_text,
        source=source,
        scope_status=scope_status,
        scope_signals=scope_signals,
        scope_answers=scope_answers or {},
        base_job_id=base_job_id,
    )
    execution_prompt = _compose_execution_prompt(prompt_text, scope_answers if scope_locked else None)

    task = queue.enqueue(
        LocalTask(
            title=prompt_text[:96],
            message=prompt_text,
            source=source,
            kind="coding_organism_prompt" if scope_locked else "coding_organism_scope_intake",
        )
    )
    queue.next_task()

    if scope_locked:
        if _prefer_adaptive_forge_prompt(execution_prompt):
            route = _route_local_capability_forge(execution_prompt, root)
        else:
            route = _route_goal(execution_prompt, goal_engine=goal_engine)
            if (
                not _route_is_clean(route)
                and _is_build_prompt(execution_prompt)
                and _route_mentions_agentcore_unavailable(route)
            ):
                route = _route_local_capability_forge(execution_prompt, root, previous_route=route)
    else:
        route = {
            "ok": False,
            "skipped": True,
            "skip_reason": "scope_of_works_not_locked",
            "plan": {},
            "engine_status": {},
        }
    route_clean = _route_is_clean(route)
    plan_summary = route.get("plan", {})
    target_files = _extract_target_files(plan_summary)
    agent_company_report = _extract_step_payload(route, "aureon-agent-company-bill-list-v1")
    capability_forge_report = _extract_step_payload(route, "aureon-local-capability-forge-v1")
    artifact_quality_report = _extract_quality_payload(route)
    creative_process_guardian = _extract_step_payload(route, "aureon-agent-creative-process-guardian-v1")
    coding_capability_unblocker = None

    evidence_core = {
        "who": {
            "operator_source": source,
            "organism_bridge": "aureon.autonomous.aureon_coding_organism_bridge",
            "client_job_estimator": "Estimator",
            "client_job_project_manager": "Project Manager",
            "snagging_owner": "Snagging Inspector",
            "hnc_drift_owner": "HNC/Auris Drift Proof",
            "creative_process_guardian": "aureon.autonomous.aureon_agent_creative_process_guardian",
            "planner": "aureon.core.goal_execution_engine.GoalExecutionEngine",
            "proposal_controller": "aureon.autonomous.aureon_safe_code_control.SafeCodeControl",
        },
        "what": {
            "goal": prompt_text,
            "task_kind": "coding_organism_prompt" if scope_locked else "coding_organism_scope_intake",
            "scope_status": scope_status,
            "scope_locked": scope_locked,
            "target_files": target_files,
            "agent_company_report_created": bool(agent_company_report),
            "capability_forge_report_created": bool(capability_forge_report),
            "artifact_quality_gate_present": bool(artifact_quality_report),
            "creative_process_guardian_created": bool(creative_process_guardian),
            "plan_status": plan_summary.get("status"),
            "step_count": plan_summary.get("step_count", 0),
        },
        "where": {
            "repo_root": str(root),
            "state_path": str(state_path),
            "audit_json": str(audit_json),
            "audit_md": str(audit_md),
            "public_json": str(public_json),
        },
        "when": {
            "submitted_at": utc_now(),
            "tests_requested": run_tests,
        },
        "how": {
            "authoring_path": [
                "operator prompt",
                "LocalTaskQueue.enqueue",
                "ScopeOfWorks detector",
                "client questions when scope is incomplete",
                "agent team handoff only after scope lock",
                "agent creative process guardian reads metacognitive, sensory, HNC/Auris, and sentient-style evidence",
                "coding capability unblocker converts missing tools, skills, dependencies, and proof gaps into autonomous gates",
                "GoalExecutionEngine.submit_goal",
                "Adaptive local capability forge when AgentCore tool intents are unavailable",
                "SafeCodeControl.propose",
                "CapabilityForge and ArtifactQualityGate when the route produces media or local capability work",
                "focused pytest validation",
                "proof checklist",
                "HNC/Auris anti-drift proof",
                "snagging list",
                "SafeDesktopControl desktop/run handoff",
                "VMControlDispatcher tool availability check",
                "finished product audit",
                "state/docs/frontend evidence publish",
            ],
            "review_contract": "code proposals remain reviewable; env AUREON_CODE_AUTO_APPROVE can mark trusted local proposals approved but does not apply patches by itself",
        },
        "act": {
            "task_enqueued": True,
            "goal_engine_routed": bool(route.get("ok")),
            "goal_route_clean": route_clean,
            "scope_locked": scope_locked,
            "client_questions_created": len(client_job.get("client_questions", [])),
            "agent_team_assigned": scope_locked,
            "proposal_created": False,
            "tests_ran": False,
            "desktop_handoff_created": False,
            "finished_product_audit_written": False,
        },
    }

    proposal = None
    if scope_locked:
        proposal = controller.propose(
            CodeProposal(
                kind="coding_organism_goal",
                title=prompt_text[:120],
                summary=(
                    "Aureon accepted this scoped coding job, routed it through the goal engine, "
                    "and recorded a reviewable code-work proposal with who/what/where/when/how evidence."
                ),
                target_files=target_files,
                patch_text="",
                metadata={
                    "prompt": prompt_text,
                    "execution_prompt": execution_prompt,
                    "client_job": client_job,
                    "goal_route": route,
                    "who_what_where_when_how": evidence_core,
                },
                source=f"aureon_coding_organism:{source}",
            )
        )
        evidence_core["act"]["proposal_created"] = True

    tests = {"ok": True, "command_count": 0, "results": [], "skipped": True}
    if run_tests and scope_locked:
        tests = _run_test_commands(root, commands=test_commands, timeout_sec=test_timeout_sec)
        tests["skipped"] = False
        evidence_core["act"]["tests_ran"] = True

    desktop_flow = (
        _build_desktop_run_flow(root, prompt_text, source)
        if include_desktop and scope_locked
        else {"status": "desktop_run_handoff_skipped", "local_desktop_controller": {}, "remote_vm_control": {}}
    )
    evidence_core["act"]["desktop_handoff_created"] = include_desktop and scope_locked
    hnc_drift_proof = _build_hnc_auris_drift_proof(root)
    if scope_locked and not creative_process_guardian:
        try:
            from aureon.autonomous.aureon_agent_creative_process_guardian import (
                build_and_write_agent_creative_process_guardian,
            )

            creative_process_guardian = build_and_write_agent_creative_process_guardian(
                root=root,
                goal=prompt_text,
            )
        except Exception as exc:
            creative_process_guardian = {
                "schema_version": "aureon-agent-creative-process-guardian-v1",
                "status": "agent_creative_process_guardian_error",
                "ok": False,
                "error": str(exc),
                "summary": {"blocking_snag_count": 1},
            }
    evidence_core["what"]["creative_process_guardian_created"] = bool(creative_process_guardian)
    evidence_core["act"]["creative_process_guardian_checked"] = bool(creative_process_guardian)
    try:
        from aureon.autonomous.aureon_coding_capability_unblocker import (
            build_and_write_coding_capability_unblocker,
        )

        coding_capability_unblocker = build_and_write_coding_capability_unblocker(
            execution_prompt if scope_locked else prompt_text,
            root=root,
            attach_to_bridge=False,
        )
    except Exception as exc:
        coding_capability_unblocker = {
            "schema_version": "aureon-coding-capability-unblocker-v1",
            "status": "coding_capability_unblocker_error",
            "ok": False,
            "error": str(exc),
            "summary": {"gate_repair_count": 1},
        }
    evidence_core["what"]["coding_capability_unblocker_created"] = bool(coding_capability_unblocker)
    evidence_core["act"]["coding_capability_gates_checked"] = bool(coding_capability_unblocker)
    if capability_forge_report:
        client_job["capability_forge"] = capability_forge_report
    if artifact_quality_report:
        client_job["artifact_quality_report"] = artifact_quality_report
        client_job["approval_state"] = (
            capability_forge_report.get("approval_state")
            if isinstance(capability_forge_report.get("approval_state"), dict)
            else {
                "state": "pending_user_review_after_apply"
                if artifact_quality_report.get("handover_ready")
                else "blocked_by_quality_gate",
                "policy": "after_apply",
            }
        )
    if creative_process_guardian:
        client_job["creative_process_guardian"] = creative_process_guardian
    if coding_capability_unblocker:
        client_job["coding_capability_unblocker"] = coding_capability_unblocker
    proof_checklist = _build_proof_checklist(
        scope_locked=scope_locked,
        route_clean=route_clean,
        proposal_created=bool(proposal),
        tests=tests,
        desktop_flow=desktop_flow,
        hnc_drift_proof=hnc_drift_proof,
        artifact_quality_report=artifact_quality_report,
        creative_process_guardian=creative_process_guardian,
    )
    snagging_list = _build_snagging_list(proof_checklist)
    client_job["proof_checklist"] = proof_checklist
    client_job["snagging_list"] = snagging_list
    product_audit = _build_finished_product_audit(
        route=route,
        tests=tests,
        desktop_flow=desktop_flow,
        root=root,
        prompt=prompt_text,
        client_job=client_job,
        proof_checklist=proof_checklist,
        snagging_list=snagging_list,
    )
    if product_audit.get("ready_for_client"):
        client_job["scope_status"] = "ready_for_client"
    client_job["handover_status"] = product_audit.get("handover_status", client_job.get("handover_status", {}))
    evidence_core["act"]["finished_product_audit_written"] = True
    work_journal = _build_work_journal(
        prompt=prompt_text,
        source=source,
        task=task,
        route=route,
        proposal=proposal,
        tests=tests,
        desktop_flow=desktop_flow,
        product_audit=product_audit,
        evidence_core=evidence_core,
        target_files=target_files,
        agent_company_report=agent_company_report,
        capability_forge_report=capability_forge_report,
        artifact_quality_report=artifact_quality_report,
        creative_process_guardian=creative_process_guardian,
        coding_capability_unblocker=coding_capability_unblocker,
        client_job=client_job,
    )

    queue.complete_next(
        note="routed through Aureon coding organism bridge"
        if scope_locked
        else "scope questions published; waiting for client scope approval"
    )
    controller_status = controller.status()

    ok = scope_locked and route_clean and bool(proposal) and (not run_tests or bool(tests.get("ok"))) and bool(product_audit.get("ready_to_run"))
    status = (
        "coding_organism_needs_client_scope"
        if not scope_locked
        else "coding_organism_ready"
        if ok
        else "coding_organism_ready_with_attention"
    )
    evidence: Dict[str, Any] = {
        "schema_version": "aureon-coding-organism-bridge-v1",
        "status": status,
        "ok": ok,
        "generated_at": utc_now(),
        "prompt": prompt_text,
        "summary": {
            "client_job_id": client_job.get("job_id"),
            "scope_status": client_job.get("scope_status"),
            "scope_locked": bool(client_job.get("scope_locked")),
            "client_question_count": len(client_job.get("client_questions", [])),
            "blocking_snag_count": _blocking_snag_count(client_job.get("snagging_list", [])),
            "hnc_auris_drift_proof_ok": bool(hnc_drift_proof.get("ok")),
            "hnc_auris_drift_warnings": hnc_drift_proof.get("runtime_drift_warnings", []),
            "creative_process_guardian_ok": bool(creative_process_guardian.get("ok")) if creative_process_guardian else None,
            "creative_process_role_count": (creative_process_guardian.get("summary") or {}).get("role_count", 0)
            if creative_process_guardian
            else 0,
            "creative_process_blocked_role_count": (creative_process_guardian.get("summary") or {}).get(
                "blocked_role_count", 0
            )
            if creative_process_guardian
            else 0,
            "creative_process_hnc_auris_ready": (creative_process_guardian.get("summary") or {}).get(
                "hnc_auris_ready", False
            )
            if creative_process_guardian
            else False,
            "coding_capability_unblocker_ok": bool(coding_capability_unblocker.get("ok"))
            if coding_capability_unblocker
            else None,
            "coding_capability_ready_gate_count": (coding_capability_unblocker.get("summary") or {}).get(
                "ready_gate_count", 0
            )
            if coding_capability_unblocker
            else 0,
            "coding_capability_gate_count": (coding_capability_unblocker.get("summary") or {}).get("gate_count", 0)
            if coding_capability_unblocker
            else 0,
            "coding_capability_converted_blocker_count": (coding_capability_unblocker.get("summary") or {}).get(
                "converted_coding_blocker_count", 0
            )
            if coding_capability_unblocker
            else 0,
            "goal_engine_routed": bool(route.get("ok")),
            "goal_route_clean": route_clean,
            "safe_code_proposal_created": bool(proposal),
            "pending_code_proposal_count": controller_status.get("pending_count", 0),
            "tests_requested": run_tests,
            "tests_ok": bool(tests.get("ok")) or bool(tests.get("skipped")),
            "target_file_count": len(target_files),
            "agent_company_report_created": bool(agent_company_report),
            "capability_forge_report_created": bool(capability_forge_report),
            "capability_forge_task_family": capability_forge_report.get("task_family", ""),
            "capability_forge_build_id": capability_forge_report.get("build_id", ""),
            "capability_forge_project_id": capability_forge_report.get("project_id", ""),
            "fresh_project_per_request": (capability_forge_report.get("summary") or {}).get(
                "fresh_project_per_request",
                False,
            ),
            "artifact_public_url": (capability_forge_report.get("artifact_manifest") or {}).get("public_url", ""),
            "artifact_quality_gate_present": bool(artifact_quality_report),
            "artifact_quality_passed": bool(artifact_quality_report.get("handover_ready")) if artifact_quality_report else None,
            "artifact_quality_score": artifact_quality_report.get("score") if artifact_quality_report else None,
            "agent_company_role_count": (agent_company_report.get("summary") or {}).get("role_count", 0),
            "agent_company_roles_with_day_plan": (agent_company_report.get("summary") or {}).get(
                "roles_with_day_plan_count", 0
            ),
            "agent_company_whole_access_roles": (agent_company_report.get("summary") or {}).get(
                "roles_with_whole_organism_access_count", 0
            ),
            "agent_company_daily_loop_ready": (agent_company_report.get("summary") or {}).get(
                "daily_operating_loop_ready", False
            ),
            "agent_company_agency_model": (agent_company_report.get("summary") or {}).get("agency_model", ""),
            "agent_company_agency_roles": (agent_company_report.get("summary") or {}).get(
                "agency_workforce_role_count", 0
            ),
            "agent_company_memory_packs": (agent_company_report.get("summary") or {}).get(
                "sha256_memory_entry_count", 0
            ),
            "desktop_handoff_created": include_desktop,
            "remote_vm_tool_count": desktop_flow.get("remote_vm_control", {}).get("tool_count", 0),
            "finished_product_status": product_audit.get("status"),
            "ready_to_run": product_audit.get("ready_to_run"),
        },
        "task": task,
        "client_job": client_job,
        "hnc_auris_drift_proof": hnc_drift_proof,
        "goal_route": route,
        "safe_code_proposal": _jsonify(proposal),
        "safe_code_status": controller_status,
        "tests": tests,
        "desktop_run_flow": desktop_flow,
        "finished_product_audit": product_audit,
        "work_journal": work_journal,
        "agent_company_report": agent_company_report,
        "capability_forge": capability_forge_report,
        "artifact_quality_report": artifact_quality_report,
        "creative_process_guardian": creative_process_guardian,
        "coding_capability_unblocker": coding_capability_unblocker,
        **evidence_core,
    }

    _write_json(state_path, evidence)
    _write_json(audit_json, evidence)
    try:
        _write_json(public_json, evidence)
    except OSError as exc:
        evidence.setdefault("publish_warnings", []).append(
            {
                "path": str(public_json),
                "error": f"{type(exc).__name__}: {exc}",
                "fallback": "state_and_audit_json_written; status endpoint remains authoritative",
            }
        )
        _write_json(state_path, evidence)
        _write_json(audit_json, evidence)
    audit_md.parent.mkdir(parents=True, exist_ok=True)
    audit_md.write_text(_make_markdown(evidence), encoding="utf-8")
    return evidence


def get_coding_organism_status(*, root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(root or REPO_ROOT).resolve()
    state = _read_json(_rooted(root, DEFAULT_STATE_PATH))
    public_state = _read_json(_rooted(root, DEFAULT_PUBLIC_JSON))
    code_state = _read_json(_rooted(root, DEFAULT_CODE_STATE_PATH))
    task_state = _read_json(_rooted(root, DEFAULT_TASK_QUEUE_PATH))
    stress_audit_state = _read_json(_rooted(root, DEFAULT_CAPABILITY_STRESS_AUDIT_STATE_PATH))
    complex_stress_state = _read_json(_rooted(root, DEFAULT_COMPLEX_BUILD_STRESS_AUDIT_STATE_PATH))
    coding_capability_unblocker_state = _read_json(_rooted(root, DEFAULT_CODING_CAPABILITY_UNBLOCKER_STATE_PATH))
    last_run = state or public_state
    if stress_audit_state and isinstance(last_run, dict):
        last_run = dict(last_run)
        last_run.setdefault("capability_stress_audit", stress_audit_state)
    if complex_stress_state and isinstance(last_run, dict):
        last_run = dict(last_run)
        last_run.setdefault("complex_build_stress_audit", complex_stress_state)
    if coding_capability_unblocker_state and isinstance(last_run, dict):
        last_run = dict(last_run)
        last_run.setdefault("coding_capability_unblocker", coding_capability_unblocker_state)
    return {
        "available": True,
        "schema_version": "aureon-coding-organism-status-v1",
        "status": last_run.get("status", "coding_organism_waiting_for_prompt"),
        "generated_at": utc_now(),
        "last_run": last_run,
        "safe_code_status": code_state,
        "task_queue_status": task_state,
        "capability_stress_audit": stress_audit_state,
        "complex_build_stress_audit": complex_stress_state,
        "coding_capability_unblocker": coding_capability_unblocker_state,
        "endpoints": {
            "prompt": "POST /api/coding/prompt",
            "status": "GET /api/coding/status",
            "public_json": "/aureon_coding_organism_bridge.json",
        },
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Aureon coding organism bridge.")
    parser.add_argument("--prompt", "-p", default="", help="Coding prompt for Aureon to route.")
    parser.add_argument("--prompt-file", default="", help="Read the prompt from a text file.")
    parser.add_argument("--source", default="operator_cli")
    parser.add_argument("--no-tests", action="store_true", help="Route and publish evidence without running pytest.")
    parser.add_argument("--no-desktop", action="store_true", help="Skip desktop/run handoff evidence.")
    parser.add_argument("--scope-approved", action="store_true", help="Treat the supplied prompt as a locked client scope.")
    parser.add_argument("--status", action="store_true", help="Print current coding organism status.")
    args = parser.parse_args(argv)

    if args.status:
        print(json.dumps(get_coding_organism_status(), indent=2))
        return 0

    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    if not prompt.strip():
        parser.error("--prompt or --prompt-file is required unless --status is used")

    result = submit_coding_prompt(
        prompt,
        source=args.source,
        run_tests=not args.no_tests,
        include_desktop=not args.no_desktop,
        scope_approved=args.scope_approved,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
