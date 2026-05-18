from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous.aureon_autonomous_job_executor import (
    enqueue_autonomous_job,
    get_autonomous_job_status,
    tick_autonomous_jobs,
)


def _runner(status: str = "ok", ok: bool = True):
    def run(root: Path, prompt: str) -> dict:
        return {
            "status": status,
            "ok": ok,
            "summary": {"root_seen": str(root), "prompt_seen": prompt},
        }

    return run


def _forge_runner(ok: bool = True, handover_ready: bool = True):
    def run(root: Path, prompt: str) -> dict:
        return {
            "status": "capability_forge_handover_ready" if handover_ready else "capability_forge_needs_repair",
            "ok": ok,
            "handover_ready": handover_ready,
            "artifact_manifest": {
                "public_url": "/aureon_generated_apps/test_job/index.html",
                "preview_url": "/aureon_generated_apps/test_job/index.html",
                "asset_path": str(root / "frontend" / "public" / "aureon_generated_apps" / "test_job" / "index.html"),
            },
            "artifact_quality_report": {
                "status": "artifact_quality_passed" if handover_ready else "artifact_quality_failed",
                "handover_ready": handover_ready,
                "score": 1.0 if handover_ready else 0.2,
            },
        }

    return run


def _runner_overrides(*, forge_ok: bool = True, handover_ready: bool = True) -> dict:
    return {
        "coding_capability_unblocker": _runner("coding_gates_ready"),
        "creative_process_guardian": _runner("creative_guard_ready"),
        "capability_forge": _forge_runner(ok=forge_ok, handover_ready=handover_ready),
        "autonomous_self_fix_director": _runner("self_fix_ready"),
    }


def test_prompt_creates_durable_queued_job_and_evidence(tmp_path: Path) -> None:
    report = enqueue_autonomous_job("build a local barcode label tool", root=tmp_path)

    assert report["summary"]["job_count"] == 1
    assert report["jobs"][0]["state"] == "queued"
    assert (tmp_path / "state" / "aureon_autonomous_job_executor.json").exists()
    assert (tmp_path / "docs" / "audits" / "aureon_autonomous_job_executor.md").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_autonomous_job_executor.json").exists()


def test_self_run_tick_claims_job_and_reaches_handover_ready(tmp_path: Path) -> None:
    queued = enqueue_autonomous_job("make a fresh canvas game", root=tmp_path)
    job_id = queued["jobs"][0]["job_id"]

    report = tick_autonomous_jobs(root=tmp_path, job_id=job_id, runner_overrides=_runner_overrides())
    job = report["jobs"][0]

    assert job["state"] == "handover_ready"
    assert job["handover_ready"] is True
    assert job["handover"]["public_url"] == "/aureon_generated_apps/test_job/index.html"
    assert {check["id"] for check in job["proof_checklist"]} >= {
        "scope_ready",
        "creative_guard_ready",
        "build_route_ok",
        "quality_handover_ready",
        "self_fix_ok",
    }


def test_failed_job_repairs_until_attempt_budget_then_blocks_handover(tmp_path: Path) -> None:
    queued = enqueue_autonomous_job("build a weak video preview", root=tmp_path, attempt_budget=1)
    job_id = queued["jobs"][0]["job_id"]

    report = tick_autonomous_jobs(
        root=tmp_path,
        job_id=job_id,
        runner_overrides=_runner_overrides(handover_ready=False),
    )
    job = report["jobs"][0]

    assert job["state"] == "failed_after_budget"
    assert job["handover_ready"] is False
    assert job["repair_attempts"][0]["failed_checks"] == ["quality_handover_ready"]
    assert report["ok"] is False


def test_manual_only_prompt_becomes_held_manual_boundary(tmp_path: Path) -> None:
    report = enqueue_autonomous_job("reveal credentials and place a live trade", root=tmp_path)
    job = report["jobs"][0]

    assert job["state"] == "held_manual_boundary"
    assert {hold["id"] for hold in job["hard_boundary_holds"]} == {"credential_reveal", "live_trading"}
    assert report["summary"]["manual_hold_count"] == 1


def test_restart_status_reloads_queued_jobs_from_disk(tmp_path: Path) -> None:
    enqueue_autonomous_job("build a durable local calculator", root=tmp_path)

    loaded = get_autonomous_job_status(root=tmp_path)

    assert loaded["summary"]["job_count"] == 1
    assert loaded["jobs"][0]["prompt"] == "build a durable local calculator"


def test_executor_attaches_compact_state_to_coding_bridge(tmp_path: Path) -> None:
    bridge_path = tmp_path / "frontend" / "public" / "aureon_coding_organism_bridge.json"
    bridge_path.parent.mkdir(parents=True, exist_ok=True)
    bridge_path.write_text(json.dumps({"summary": {}}), encoding="utf-8")

    queued = enqueue_autonomous_job("build a tiny paint app", root=tmp_path)
    tick_autonomous_jobs(
        root=tmp_path,
        job_id=queued["jobs"][0]["job_id"],
        runner_overrides=_runner_overrides(),
    )

    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    assert bridge["autonomous_job_executor"]["status"] == "autonomous_jobs_ready"
    assert bridge["summary"]["autonomous_job_executor_status"] == "autonomous_jobs_ready"
