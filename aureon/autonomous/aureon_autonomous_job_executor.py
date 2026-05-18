from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

from aureon.autonomous.aureon_agent_creative_process_guardian import (
    build_and_write_agent_creative_process_guardian,
)
from aureon.autonomous.aureon_autonomous_self_fix_director import (
    build_and_write_autonomous_self_fix_director,
)
from aureon.autonomous.aureon_capability_forge import REPO_ROOT, build_and_write_capability_forge
from aureon.autonomous.aureon_coding_capability_unblocker import (
    build_and_write_coding_capability_unblocker,
)


SCHEMA_VERSION = "aureon-autonomous-job-executor-v1"
DEFAULT_STATE_PATH = Path("state/aureon_autonomous_job_executor.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_autonomous_job_executor.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_autonomous_job_executor.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_autonomous_job_executor.json")
CODING_BRIDGE_EVIDENCE_PATHS = [
    Path("state/aureon_coding_organism_last_run.json"),
    Path("docs/audits/aureon_coding_organism_bridge.json"),
    Path("frontend/public/aureon_coding_organism_bridge.json"),
]

JOB_STATES = [
    "queued",
    "scoping",
    "building",
    "testing",
    "repairing",
    "handover_ready",
    "held_manual_boundary",
    "failed_after_budget",
]

ACTIVE_STATES = {"queued", "scoping", "building", "testing", "repairing"}
HARD_BOUNDARY_PATTERNS = {
    "credential_reveal": ("reveal credential", "show api key", "show secret", "private key", "password"),
    "live_trading": ("place a live trade", "execute live order", "order mutation", "live trading"),
    "payment": ("make payment", "charge card", "top up", "bank transfer"),
    "official_filing": ("submit hmrc", "file companies house", "official filing", "tax filing"),
    "destructive_os": ("delete the repo", "wipe disk", "format disk", "rm -rf", "destructive os"),
}

Runner = Callable[[Path, str], Dict[str, Any]]


def _default_root() -> Path:
    return REPO_ROOT


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rooted(root: Path, rel: Path) -> Path:
    return rel if rel.is_absolute() else root / rel


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}
    return {}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def _write_text(path: Path, text: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {"path": str(path), "bytes": path.stat().st_size}


def _detect_hard_holds(prompt: str) -> List[Dict[str, Any]]:
    lower = str(prompt or "").lower()
    holds: List[Dict[str, Any]] = []
    for hold_id, patterns in HARD_BOUNDARY_PATTERNS.items():
        if any(pattern in lower for pattern in patterns):
            holds.append(
                {
                    "id": hold_id,
                    "state": "held_manual_boundary",
                    "blocking": True,
                    "reason": "This authority is outside safe local coding autonomy.",
                    "next_action": "Human operator must handle this outside the autonomous job lane.",
                }
            )
    return holds


def _new_job_id(prompt: str) -> str:
    digest = hashlib.sha256(f"{prompt}|{time.time_ns()}".encode("utf-8")).hexdigest()[:12]
    return f"job_{digest}"


def _initial_state() -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "autonomous_jobs_waiting",
        "generated_at": _utc_now(),
        "jobs": [],
        "summary": {
            "queue_depth": 0,
            "active_job_count": 0,
            "handover_ready_count": 0,
            "manual_hold_count": 0,
            "failed_after_budget_count": 0,
        },
    }


def _load_state(root: Path) -> Dict[str, Any]:
    state = _read_json(_rooted(root, DEFAULT_STATE_PATH))
    if not state:
        state = _read_json(_rooted(root, DEFAULT_PUBLIC_JSON))
    if not state:
        return _initial_state()
    state.setdefault("schema_version", SCHEMA_VERSION)
    state.setdefault("jobs", [])
    return state


def _priority_value(job: Dict[str, Any]) -> int:
    raw = str(job.get("priority") or "P50").upper().strip()
    if raw.startswith("P"):
        raw = raw[1:]
    try:
        return int(raw)
    except Exception:
        return 50


def _select_job(jobs: Sequence[Dict[str, Any]], job_id: str = "") -> Optional[Dict[str, Any]]:
    if job_id:
        for job in jobs:
            if job.get("job_id") == job_id:
                return job if job.get("state") in ACTIVE_STATES else None
        return None
    active = [job for job in jobs if job.get("state") in ACTIVE_STATES]
    if not active:
        return None
    return sorted(active, key=lambda item: (_priority_value(item), str(item.get("created_at") or "")))[0]


def _summarize_jobs(state: Dict[str, Any]) -> Dict[str, Any]:
    jobs = [job for job in state.get("jobs", []) if isinstance(job, dict)]
    active = [job for job in jobs if job.get("state") in ACTIVE_STATES]
    current = _select_job(jobs)
    return {
        "job_count": len(jobs),
        "queue_depth": len([job for job in jobs if job.get("state") == "queued"]),
        "active_job_count": len(active),
        "handover_ready_count": len([job for job in jobs if job.get("state") == "handover_ready"]),
        "manual_hold_count": len([job for job in jobs if job.get("state") == "held_manual_boundary"]),
        "failed_after_budget_count": len([job for job in jobs if job.get("state") == "failed_after_budget"]),
        "current_job_id": current.get("job_id") if current else "",
        "current_job_state": current.get("state") if current else "",
    }


def _proof_check(id_: str, ok: bool, evidence: str) -> Dict[str, Any]:
    return {"id": id_, "ok": bool(ok), "evidence": evidence}


def _default_runners() -> Dict[str, Runner]:
    return {
        "coding_capability_unblocker": lambda root, prompt: build_and_write_coding_capability_unblocker(
            prompt, root=root
        ),
        "creative_process_guardian": lambda root, prompt: build_and_write_agent_creative_process_guardian(
            root=root, goal=prompt, refresh_inputs=True
        ),
        "capability_forge": lambda root, prompt: build_and_write_capability_forge(prompt, root=root),
        "autonomous_self_fix_director": lambda root, prompt: build_and_write_autonomous_self_fix_director(
            root=root,
            operator_prompt=prompt,
            codex_audit_state="autonomous_safe",
        ),
    }


def _run_runner(name: str, runner: Runner, root: Path, prompt: str) -> Dict[str, Any]:
    started = time.perf_counter()
    try:
        payload = runner(root, prompt)
        return {
            "id": name,
            "ok": bool(payload.get("ok", True)),
            "status": payload.get("status", "ok"),
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "payload": payload,
        }
    except Exception as exc:
        return {
            "id": name,
            "ok": False,
            "status": "runner_exception",
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
            "payload": {},
        }


def _append_stage(job: Dict[str, Any], stage: str, ok: bool, evidence: Dict[str, Any]) -> None:
    job.setdefault("work_journal", []).append(
        {
            "stage": stage,
            "ok": bool(ok),
            "at": _utc_now(),
            "evidence": evidence,
        }
    )


def _advance_job(
    job: Dict[str, Any],
    *,
    root: Path,
    runner_overrides: Optional[Dict[str, Runner]] = None,
) -> Dict[str, Any]:
    now = _utc_now()
    job["updated_at"] = now
    if job.get("hard_boundary_holds"):
        job["state"] = "held_manual_boundary"
        job["phase"] = "manual_boundary"
        _append_stage(job, "manual_boundary", False, {"holds": job.get("hard_boundary_holds", [])})
        return job

    prompt = str(job.get("prompt") or "")
    runners = _default_runners()
    if runner_overrides:
        runners.update(runner_overrides)

    job["state"] = "scoping"
    job["phase"] = "scoping"
    scope = _run_runner("coding_capability_unblocker", runners["coding_capability_unblocker"], root, prompt)
    creative = _run_runner("creative_process_guardian", runners["creative_process_guardian"], root, prompt)
    _append_stage(job, "scoping", scope["ok"] and creative["ok"], {"scope": scope["status"], "creative": creative["status"]})

    job["state"] = "building"
    job["phase"] = "building"
    forge = _run_runner("capability_forge", runners["capability_forge"], root, prompt)
    forge_payload = forge.get("payload", {})
    artifact_manifest = forge_payload.get("artifact_manifest") if isinstance(forge_payload.get("artifact_manifest"), dict) else {}
    quality_report = (
        forge_payload.get("artifact_quality_report")
        if isinstance(forge_payload.get("artifact_quality_report"), dict)
        else {}
    )
    job["artifact_manifest"] = artifact_manifest
    job["artifact_quality_report"] = quality_report
    _append_stage(job, "building", forge["ok"], {"status": forge["status"], "artifact": artifact_manifest.get("public_url") or artifact_manifest.get("preview_url")})

    job["state"] = "testing"
    job["phase"] = "testing"
    self_fix = _run_runner("autonomous_self_fix_director", runners["autonomous_self_fix_director"], root, prompt)
    proof = [
        _proof_check("scope_ready", scope["ok"], str(scope["status"])),
        _proof_check("creative_guard_ready", creative["ok"], str(creative["status"])),
        _proof_check("build_route_ok", forge["ok"], str(forge["status"])),
        _proof_check("quality_handover_ready", bool(quality_report.get("handover_ready") or forge_payload.get("handover_ready")), str(quality_report.get("status") or forge_payload.get("status"))),
        _proof_check("self_fix_ok", self_fix["ok"], str(self_fix["status"])),
    ]
    job["proof_checklist"] = proof
    job["last_runner_status"] = {
        "coding_capability_unblocker": scope["status"],
        "creative_process_guardian": creative["status"],
        "capability_forge": forge["status"],
        "autonomous_self_fix_director": self_fix["status"],
    }
    passed = all(item["ok"] for item in proof)
    _append_stage(job, "testing", passed, {"proof": proof})

    if passed:
        job["state"] = "handover_ready"
        job["phase"] = "client_handover"
        job["handover_ready"] = True
        job["handover"] = {
            "state": "visible",
            "public_url": artifact_manifest.get("public_url") or artifact_manifest.get("preview_url") or "",
            "quality_score": quality_report.get("score"),
        }
        _append_stage(job, "handover_ready", True, job["handover"])
        return job

    job["attempts"] = int(job.get("attempts") or 0) + 1
    job["handover_ready"] = False
    job.setdefault("repair_attempts", []).append(
        {
            "attempt": job["attempts"],
            "at": _utc_now(),
            "failed_checks": [item["id"] for item in proof if not item["ok"]],
            "next_action": "rerun autonomous job worker" if job["attempts"] < int(job.get("attempt_budget") or 2) else "publish failed_after_budget blocker",
        }
    )
    if job["attempts"] >= int(job.get("attempt_budget") or 2):
        job["state"] = "failed_after_budget"
        job["phase"] = "failed_after_budget"
    else:
        job["state"] = "repairing"
        job["phase"] = "repairing"
    return job


def _attach_to_coding_bridge(root: Path, compact: Dict[str, Any]) -> List[Dict[str, Any]]:
    writes: List[Dict[str, Any]] = []
    for rel in CODING_BRIDGE_EVIDENCE_PATHS:
        path = _rooted(root, rel)
        payload = _read_json(path)
        if not payload:
            continue
        payload["autonomous_job_executor"] = compact
        summary = payload.setdefault("summary", {})
        if isinstance(summary, dict):
            compact_summary = compact.get("summary") or {}
            summary["autonomous_job_executor_status"] = compact.get("status")
            summary["autonomous_job_queue_depth"] = compact_summary.get("queue_depth")
            summary["autonomous_job_current_state"] = compact_summary.get("current_job_state")
        writes.append(_write_json(path, payload))
    return writes


def _make_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# Aureon Autonomous Job Executor",
        "",
        f"- status: {report.get('status')}",
        f"- jobs: {summary.get('job_count')}",
        f"- queue depth: {summary.get('queue_depth')}",
        f"- active jobs: {summary.get('active_job_count')}",
        f"- handover ready: {summary.get('handover_ready_count')}",
        "",
        "## Jobs",
    ]
    for job in report.get("jobs", [])[:20]:
        lines.append(
            f"- {job.get('job_id')}: state={job.get('state')} phase={job.get('phase')} attempts={job.get('attempts')} prompt={str(job.get('prompt') or '')[:80]}"
        )
    return "\n".join(lines) + "\n"


def _persist(root: Path, state: Dict[str, Any]) -> Dict[str, Any]:
    state["generated_at"] = _utc_now()
    state["summary"] = _summarize_jobs(state)
    active = _select_job(state.get("jobs", []))
    state["active_job"] = active or {}
    if active:
        state["status"] = "autonomous_jobs_active"
    elif state["summary"]["queue_depth"]:
        state["status"] = "autonomous_jobs_queued"
    elif state["summary"]["failed_after_budget_count"]:
        state["status"] = "autonomous_jobs_need_attention"
    else:
        state["status"] = "autonomous_jobs_ready"
    state["ok"] = state["summary"]["failed_after_budget_count"] == 0 and state["summary"]["manual_hold_count"] == 0
    writes = [
        _write_json(_rooted(root, DEFAULT_STATE_PATH), state),
        _write_json(_rooted(root, DEFAULT_AUDIT_JSON), state),
        _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(state)),
        _write_json(_rooted(root, DEFAULT_PUBLIC_JSON), state),
    ]
    compact = {
        "schema_version": SCHEMA_VERSION,
        "status": state.get("status"),
        "generated_at": state.get("generated_at"),
        "summary": state.get("summary"),
        "active_job": state.get("active_job") or {},
        "recent_jobs": state.get("jobs", [])[-5:],
    }
    state["write_info"] = {"evidence_writes": writes, "coding_bridge_evidence_writes": _attach_to_coding_bridge(root, compact)}
    for rel in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root, rel), state)
    _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(state))
    return state


def enqueue_autonomous_job(
    prompt: str,
    *,
    root: Optional[Path] = None,
    source: str = "operator",
    priority: str = "P50",
    attempt_budget: int = 2,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    state = _load_state(root)
    holds = _detect_hard_holds(prompt)
    job = {
        "job_id": _new_job_id(prompt),
        "prompt": str(prompt or "").strip(),
        "source": source,
        "priority": priority,
        "state": "held_manual_boundary" if holds else "queued",
        "phase": "manual_boundary" if holds else "queued",
        "attempts": 0,
        "attempt_budget": max(1, int(attempt_budget or 1)),
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "hard_boundary_holds": holds,
        "work_journal": [],
        "repair_attempts": [],
        "metadata": metadata or {},
        "handover_ready": False,
    }
    if holds:
        _append_stage(job, "manual_boundary", False, {"holds": holds})
    state.setdefault("jobs", []).append(job)
    return _persist(root, state)


def tick_autonomous_jobs(
    *,
    root: Optional[Path] = None,
    job_id: str = "",
    runner_overrides: Optional[Dict[str, Runner]] = None,
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    state = _load_state(root)
    jobs = [job for job in state.get("jobs", []) if isinstance(job, dict)]
    state["jobs"] = jobs
    selected = _select_job(jobs, job_id=job_id)
    if selected:
        _advance_job(selected, root=root, runner_overrides=runner_overrides)
    return _persist(root, state)


def get_autonomous_job_status(*, root: Optional[Path] = None, job_id: str = "") -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    state = _load_state(root)
    state["summary"] = _summarize_jobs(state)
    state["active_job"] = _select_job(state.get("jobs", [])) or {}
    if job_id:
        for job in state.get("jobs", []):
            if job.get("job_id") == job_id:
                return {"schema_version": SCHEMA_VERSION, "status": "autonomous_job_found", "job": job, "summary": state["summary"]}
        return {"schema_version": SCHEMA_VERSION, "status": "autonomous_job_missing", "job": {}, "summary": state["summary"]}
    return state


def enqueue_and_tick_autonomous_job(
    prompt: str,
    *,
    root: Optional[Path] = None,
    source: str = "operator",
    priority: str = "P50",
    attempt_budget: int = 2,
    metadata: Optional[Dict[str, Any]] = None,
    runner_overrides: Optional[Dict[str, Runner]] = None,
) -> Dict[str, Any]:
    state = enqueue_autonomous_job(
        prompt,
        root=root,
        source=source,
        priority=priority,
        attempt_budget=attempt_budget,
        metadata=metadata,
    )
    job = state.get("jobs", [])[-1]
    if job.get("state") in ACTIVE_STATES:
        return tick_autonomous_jobs(root=root, job_id=str(job.get("job_id") or ""), runner_overrides=runner_overrides)
    return state


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aureon's durable autonomous job executor.")
    parser.add_argument("--root", default="", help="Repository root. Defaults to current Aureon repo.")
    parser.add_argument("--prompt", default="", help="Prompt to enqueue.")
    parser.add_argument("--tick", action="store_true", help="Advance the next queued/repairing job.")
    parser.add_argument("--job-id", default="", help="Specific job id for tick/status.")
    parser.add_argument("--status", action="store_true", help="Print current job status.")
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else None
    if args.prompt and args.tick:
        report = enqueue_and_tick_autonomous_job(args.prompt, root=root)
    elif args.prompt:
        report = enqueue_autonomous_job(args.prompt, root=root)
    elif args.tick:
        report = tick_autonomous_jobs(root=root, job_id=args.job_id)
    else:
        report = get_autonomous_job_status(root=root, job_id=args.job_id)
    if args.json or args.status:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        summary = report.get("summary", {})
        print(
            f"{report.get('status')}: jobs={summary.get('job_count', 0)} "
            f"queue={summary.get('queue_depth', 0)} active={summary.get('active_job_count', 0)} "
            f"handover={summary.get('handover_ready_count', 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
