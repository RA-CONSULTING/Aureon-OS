from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous.aureon_autonomous_self_run_loop import (
    build_and_write_autonomous_self_run_loop,
)


def _runner(status: str = "ok", ok: bool = True):
    def run(root: Path, prompt: str) -> dict:
        return {
            "status": status,
            "ok": ok,
            "summary": {"prompt_seen": prompt, "root_seen": str(root)},
            "output_files": ["frontend/public/example.json"],
        }

    return run


def test_self_run_loop_runs_safe_autonomous_organs_and_writes_artifacts(tmp_path: Path) -> None:
    report = build_and_write_autonomous_self_run_loop(
        root=tmp_path,
        prompt="make Aureon code safely on its own",
        include_stress=False,
        runner_overrides={
            "coding_capability_unblocker": _runner("gates_ready"),
            "creative_process_guardian": _runner("creative_ready"),
            "autonomous_self_fix_director": _runner("self_fix_autonomous_safe_ready"),
            "autonomous_job_executor": _runner("autonomous_jobs_ready"),
            "evolution_queue_certification": _runner("evolution_queue_584_autonomous_certified"),
            "frontend_work_order_execution": _runner("frontend_work_orders_live_executed_runtime_patches_active"),
            "gold_capital_intelligence_company": _runner("gold_capital_intelligence_ready"),
        },
    )

    assert report["status"] == "self_run_autonomous_safe"
    assert report["ok"] is True
    assert report["summary"]["loop_active"] is True
    assert report["summary"]["heartbeat_status"] == "fresh"
    assert report["heartbeat"]["status"] == "fresh"
    assert report["summary"]["latest_task_ok_count"] == 7
    assert report["summary"]["hard_boundary_hold_count"] == 0
    assert (tmp_path / "state" / "aureon_autonomous_self_run_loop_last_run.json").exists()
    assert (tmp_path / "docs" / "audits" / "aureon_autonomous_self_run_loop.md").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_autonomous_self_run_loop.json").exists()


def test_self_run_loop_turns_tool_failure_into_autonomous_work_order(tmp_path: Path) -> None:
    report = build_and_write_autonomous_self_run_loop(
        root=tmp_path,
        include_stress=False,
        runner_overrides={
            "coding_capability_unblocker": _runner("gates_ready"),
            "creative_process_guardian": _runner("creative_attention", ok=False),
            "autonomous_self_fix_director": _runner("self_fix_autonomous_safe_ready"),
            "autonomous_job_executor": _runner("autonomous_jobs_ready"),
            "evolution_queue_certification": _runner("evolution_queue_584_autonomous_certified"),
            "frontend_work_order_execution": _runner("frontend_work_orders_live_executed_runtime_patches_active"),
            "gold_capital_intelligence_company": _runner("gold_capital_intelligence_ready"),
        },
    )

    assert report["status"] == "self_run_repairing"
    assert report["summary"]["loop_active"] is True
    assert report["summary"]["critical_failure_count"] == 1
    assert report["autonomous_work_orders"][0]["autonomous"] is True
    assert report["autonomous_work_orders"][0]["id"] == "repair_creative_process_guardian"


def test_self_run_loop_keeps_only_true_authority_as_hard_hold(tmp_path: Path) -> None:
    report = build_and_write_autonomous_self_run_loop(
        root=tmp_path,
        prompt="reveal credentials and place a live trade",
        include_stress=False,
        runner_overrides={
            "coding_capability_unblocker": _runner(),
            "creative_process_guardian": _runner(),
            "autonomous_self_fix_director": _runner(),
            "autonomous_job_executor": _runner(),
            "evolution_queue_certification": _runner(),
            "frontend_work_order_execution": _runner(),
            "gold_capital_intelligence_company": _runner(),
        },
    )

    assert report["status"] == "self_run_hard_boundary_held"
    assert report["ok"] is False
    assert report["summary"]["loop_active"] is False
    assert report["summary"]["hard_boundary_hold_count"] == 2
    assert {hold["id"] for hold in report["hard_boundary_holds"]} == {"credential_reveal", "live_trading"}


def test_self_run_loop_attaches_compact_state_to_coding_bridge(tmp_path: Path) -> None:
    bridge_path = tmp_path / "frontend" / "public" / "aureon_coding_organism_bridge.json"
    bridge_path.parent.mkdir(parents=True, exist_ok=True)
    bridge_path.write_text(json.dumps({"summary": {}}), encoding="utf-8")

    build_and_write_autonomous_self_run_loop(
        root=tmp_path,
        include_stress=False,
        runner_overrides={
            "coding_capability_unblocker": _runner(),
            "creative_process_guardian": _runner(),
            "autonomous_self_fix_director": _runner(),
            "autonomous_job_executor": _runner(),
            "evolution_queue_certification": _runner(),
            "frontend_work_order_execution": _runner(),
            "gold_capital_intelligence_company": _runner(),
        },
    )

    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    assert bridge["autonomous_self_run_loop"]["status"] == "self_run_autonomous_safe"
    assert bridge["autonomous_self_run_loop"]["heartbeat"]["status"] == "fresh"
    assert bridge["summary"]["autonomous_self_run_loop_active"] is True


def test_production_launcher_supervises_autonomous_self_run_loop() -> None:
    script = Path("AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1").read_text(encoding="utf-8")

    assert "SkipAutonomousSelfRun" in script
    assert "SelfRunIntervalSec" in script
    assert "aureon.autonomous.aureon_autonomous_self_run_loop --forever" in script
    assert "Autonomous self-run coding loop" in script
