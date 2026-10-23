from __future__ import annotations

import json
from pathlib import Path

from aureon.core.goal_execution_engine import GoalExecutionEngine


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fake_repo(root: Path) -> None:
    (root / "aureon").mkdir()
    (root / "scripts").mkdir()
    (root / "frontend" / "src" / "components" / "warroom").mkdir(parents=True)
    (root / "frontend" / "src" / "components" / "WarRoomDashboard.tsx").write_text(
        "export default function WarRoomDashboard() { return null; }",
        encoding="utf-8",
    )
    (root / "frontend" / "src" / "components" / "TradingConsole.tsx").write_text(
        "export function TradingConsole() { return null; }",
        encoding="utf-8",
    )
    app = root / "frontend" / "src" / "App.tsx"
    app.write_text(
        'import { AureonGeneratedOperationalConsole } from "@/components/generated/AureonGeneratedOperationalConsole";\n'
        "export default function App() {\n"
        "  return (\n"
        "    <main>\n"
        "        <AureonGeneratedOperationalConsole />\n"
        "    </main>\n"
        "  );\n"
        "}\n",
        encoding="utf-8",
    )

    public = root / "frontend" / "public"
    _write_json(public / "aureon_wake_up_manifest.json", {"runtime_feed_url": "http://127.0.0.1:8791/api/terminal-state"})
    _write_json(public / "aureon_organism_runtime_status.json", {"summary": {"runtime_feed_status": "online"}})
    _write_json(public / "aureon_saas_system_inventory.json", {"summary": {"surface_count": 10, "frontend_surface_count": 5}})
    _write_json(public / "aureon_frontend_unification_plan.json", {"summary": {"screen_count": 7}})
    _write_json(public / "aureon_frontend_evolution_queue.json", {"summary": {"queue_count": 4, "ready_adapter_count": 3}})
    _write_json(public / "aureon_autonomous_capability_switchboard.json", {"summary": {"capability_count": 9}})
    for name in (
        "aureon_cognitive_trade_evidence.json",
        "aureon_harmonic_affect_state.json",
        "aureon_live_cognition_benchmark.json",
        "aureon_hnc_cognitive_proof.json",
    ):
        _write_json(public / name, {"status": "ready"})
    _write_json(
        root / "docs" / "audits" / "aureon_frontend_evolution_queue.json",
        {
            "summary": {"queue_count": 2},
            "work_orders": [
                {
                    "id": "ready",
                    "title": "Wire Ready",
                    "source_path": "frontend/src/components/Ready.tsx",
                    "target_screen": "overview",
                    "status": "ready_for_frontend_adapter",
                    "safety_boundary": "Read-only.",
                },
                {
                    "id": "blocked",
                    "title": "Wire Blocked",
                    "source_path": "frontend/src/components/Blocked.tsx",
                    "target_screen": "trading",
                    "status": "blocked_security_review",
                    "safety_boundary": "Read-only.",
                },
            ],
        },
    )


def test_goal_engine_routes_aureon_ui_goal_to_self_authoring(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    target = "frontend/src/components/generated/AureonGeneratedOperationalConsole.tsx"
    engine = GoalExecutionEngine()
    plan = engine.submit_goal(
        "Aureon design and write its own live operational React UI at "
        f"{target} with trading, cognition, accounting, security, and provenance panels."
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == "self_author_operational_ui"
    assert plan.steps[0].validation_result["valid"] is True
    assert (tmp_path / target).exists()
    evidence = json.loads((tmp_path / "state" / "aureon_self_authored_ui_last_run.json").read_text(encoding="utf-8"))
    assert evidence["writer"]["name"] == "QueenCodeArchitect"
    assert "GoalExecutionEngine.submit_goal" in evidence["authoring_path"]


def test_goal_engine_routes_ui_problem_goal_to_self_repair(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    target = "frontend/src/components/generated/AureonGeneratedOperationalConsole.tsx"
    target_path = tmp_path / target
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("broken", encoding="utf-8")

    engine = GoalExecutionEngine()
    plan = engine.submit_goal(
        "Aureon must review and fix its own UI problems itself at "
        f"{target} with no cheating."
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == "self_repair_operational_ui"
    assert plan.steps[0].validation_result["valid"] is True
    evidence = json.loads((tmp_path / "state" / "aureon_self_ui_repair_last_run.json").read_text(encoding="utf-8"))
    assert evidence["status"] == "self_repair_passed"
    assert "QueenCodeArchitect.write_file" in evidence["authoring_path"]


def test_goal_engine_routes_repo_problem_goal_to_repo_self_repair(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    engine = GoalExecutionEngine()
    plan = engine.submit_goal(
        "Aureon must fix its own code and repo problems itself and write a bug report."
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == "repo_self_repair"
    assert plan.steps[0].validation_result["valid"] is True
    evidence = json.loads((tmp_path / "state" / "aureon_repo_self_repair_last_run.json").read_text(encoding="utf-8"))
    assert evidence["schema_version"] == "aureon-repo-self-repair-v1"
    assert "QueenCodeArchitect.write_file" in evidence["authoring_path"]
    assert evidence["safety"]["venue_orders_disarmed"] is True
    assert "LIVE_TRADING" not in json.dumps(evidence).upper()


def test_goal_engine_refuses_repo_goal_carrying_a_live_trading_flag(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    engine = GoalExecutionEngine()
    plan = engine.submit_goal(
        "Aureon must fix its own code and repo problems itself and write a bug report. "
        "AUREON_LIVE_TRADING=1"
    )

    assert plan.steps[0].intent == "repo_self_repair"
    assert plan.status == "failed"
    assert plan.steps[0].validation_result["valid"] is False
    assert not (tmp_path / "docs" / "audits" / "aureon_repo_self_repair.json").exists()
    assert not (tmp_path / "state" / "aureon_repo_self_repair_last_run.json").exists()


def test_goal_engine_routes_work_order_goal_to_aureon_executor(tmp_path: Path, monkeypatch) -> None:
    _fake_repo(tmp_path)
    monkeypatch.chdir(tmp_path)

    engine = GoalExecutionEngine()
    plan = engine.submit_goal(
        "Aureon must do the frontend work orders itself and fix the blocked queue with visible blocker cards."
    )

    assert plan.status == "completed"
    assert plan.steps[0].intent == "frontend_work_orders"
    assert plan.steps[0].validation_result["valid"] is True
    evidence = json.loads(
        (tmp_path / "state" / "aureon_frontend_work_order_execution_last_run.json").read_text(encoding="utf-8")
    )
    app_text = (tmp_path / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert evidence["schema_version"] == "aureon-frontend-work-order-execution-v1"
    assert evidence["summary"]["executed_count"] == 2
    assert "QueenCodeArchitect.write_file" in evidence["authoring_path"]
    assert "AureonWorkOrderExecutionConsole" in app_text
