from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous.aureon_unified_ui_builder import (
    SCHEMA_VERSION,
    build_operational_ui_spec,
    review_operational_ui,
    self_author_operational_ui,
    self_review_and_repair_operational_ui,
    write_operational_ui,
)


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
    (root / "frontend" / "src" / "components" / "warroom" / "MultiExchangePanel.tsx").write_text(
        "export function MultiExchangePanel() { return null; }",
        encoding="utf-8",
    )

    _write_json(
        root / "frontend" / "public" / "aureon_wake_up_manifest.json",
        {
            "generated_at": "2026-05-13T12:00:00+00:00",
            "runtime_feed_url": "http://127.0.0.1:8791/api/terminal-state",
            "runtime_flight_test_url": "http://127.0.0.1:8791/api/flight-test",
            "runtime_reboot_advice_url": "http://127.0.0.1:8791/api/reboot-advice",
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_organism_runtime_status.json",
        {
            "generated_at": "2026-05-13T12:00:00+00:00",
            "status": "organism_guarded_live_action",
            "mode": "guarded_live_action",
            "summary": {"runtime_feed_status": "online", "blind_spot_count": 1},
            "domains": [],
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_saas_system_inventory.json",
        {
            "status": "inventory_ready",
            "summary": {"surface_count": 80, "frontend_surface_count": 32},
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_frontend_unification_plan.json",
        {
            "status": "unification_plan_ready",
            "summary": {"screen_count": 7},
            "canonical_screens": [{"id": "trading", "title": "Trading", "source_surface_count": 12}],
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_frontend_evolution_queue.json",
        {
            "status": "evolution_queue_ready",
            "summary": {"queue_count": 4, "ready_adapter_count": 3, "blocked_count": 0},
            "work_orders": [],
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_autonomous_capability_switchboard.json",
        {
            "status": "switchboard_ready",
            "summary": {
                "capability_count": 9,
                "autonomous_capability_count": 8,
                "frontend_work_order_count": 4,
            },
            "capability_modes": [],
        },
    )
    for name in (
        "aureon_cognitive_trade_evidence.json",
        "aureon_harmonic_affect_state.json",
        "aureon_live_cognition_benchmark.json",
        "aureon_hnc_cognitive_proof.json",
    ):
        _write_json(root / "frontend" / "public" / name, {"status": "ready", "generated_at": "2026-05-13T12:00:00+00:00"})


def test_unified_ui_builder_writes_component_spec_and_evidence(tmp_path: Path):
    _fake_repo(tmp_path)

    build = build_operational_ui_spec(tmp_path)
    component, public_spec, audit, state = write_operational_ui(build)
    spec = json.loads(public_spec.read_text(encoding="utf-8"))
    component_text = component.read_text(encoding="utf-8")

    assert spec["schema_version"] == SCHEMA_VERSION
    assert spec["status"] == "operational_ui_spec_ready"
    assert spec["capability_coverage"]["canonical_screen_count"] == 7
    assert spec["capability_coverage"]["capability_count"] == 9
    assert spec["capability_coverage"]["template_count"] >= 3
    assert "frontend/src/components/WarRoomDashboard.tsx" in spec["templates_used"]
    assert "aureon_code_expression_context_v1" in spec["expression_context"]["schema_features"]
    assert "AureonGeneratedOperationalConsole" in component_text
    assert "AureonCodingOrganismConsole" in component_text
    assert "Four-Exchange Coverage" in component_text
    assert "HNC/Auris" in component_text
    assert "API_SECRET" not in json.dumps(spec)
    assert audit.exists()
    assert state.exists()


def test_self_author_operational_ui_uses_queen_code_writer(tmp_path: Path):
    _fake_repo(tmp_path)

    result = self_author_operational_ui(
        "Aureon design your own live UI",
        root=tmp_path,
    )

    assert result["success"] is True
    assert "QueenCodeArchitect.write_file" in result["authoring_path"]
    component = tmp_path / result["component_path"]
    state = tmp_path / result["state_path"]
    evidence = json.loads(state.read_text(encoding="utf-8"))

    assert component.exists()
    assert "AureonGeneratedOperationalConsole" in component.read_text(encoding="utf-8")
    assert evidence["status"] == "self_authored_operational_ui_ready"
    assert evidence["writer"]["name"] == "QueenCodeArchitect"
    assert evidence["authoring_goal"] == "Aureon design your own live UI"


def test_operational_console_template_matches_the_current_file() -> None:
    from aureon.autonomous.aureon_unified_ui_builder import render_react_component

    current = (
        Path(__file__).resolve().parents[1]
        / "frontend/src/components/generated/AureonGeneratedOperationalConsole.tsx"
    ).read_text(encoding="utf-8")
    assert render_react_component() == current


def test_self_review_proposes_a_diff_and_does_not_rewrite_the_console(tmp_path: Path):
    _fake_repo(tmp_path)
    target = tmp_path / "frontend" / "src" / "components" / "generated" / "AureonGeneratedOperationalConsole.tsx"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("placeholder", encoding="utf-8")

    initial = review_operational_ui(root=tmp_path, run_build=False)
    result = self_review_and_repair_operational_ui(
        "Aureon work through your own UI problems",
        root=tmp_path,
        run_build=False,
    )
    repair = result["repair_actions"][0]["repair"]

    assert initial["success"] is False
    assert result["success"] is False
    assert result["status"] == "self_repair_failed"
    assert result["applied"] is False
    assert result["wrote_tree"] is False
    assert repair["status"] == "repair_failed"
    assert repair["reason"] == "hardcoded_host"
    assert repair["applied"] is False
    assert repair["wrote_tree"] is False
    assert "propose_repair_diff" in result["authoring_path"]
    assert target.read_text(encoding="utf-8") == "placeholder"
    assert not (tmp_path / "frontend" / "public" / "aureon_operational_ui_spec.json").exists()
    log = (tmp_path / "state" / "self_repair_review_log.jsonl").read_text(encoding="utf-8")
    assert "repair_failed" in log
    assert "hardcoded_host" in log


def test_self_review_catches_path_specific_export_mismatch(tmp_path: Path):
    _fake_repo(tmp_path)
    target = tmp_path / "frontend" / "src" / "components" / "generated" / "AureonCodingOrganismConsole.tsx"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("export function AureonGeneratedOperationalConsole() { return null; }", encoding="utf-8")

    review = review_operational_ui(
        root=tmp_path,
        component_path=Path("frontend/src/components/generated/AureonCodingOrganismConsole.tsx"),
        run_build=False,
    )

    assert review["success"] is False
    assert any(issue["code"] == "missing_expected_component_export" for issue in review["issues"])
