from __future__ import annotations

import json
from pathlib import Path

import pytest

from aureon.autonomous.aureon_repo_self_repair import run_repo_self_repair


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fake_repo(root: Path) -> None:
    (root / "aureon").mkdir()
    (root / "scripts").mkdir()
    (root / "frontend" / "src" / "components").mkdir(parents=True)
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


def test_repo_self_repair_refuses_a_write_carrying_a_live_trading_flag(tmp_path: Path) -> None:
    _fake_repo(tmp_path)

    with pytest.raises(RuntimeError, match="refused to write"):
        run_repo_self_repair(
            "Aureon fix its own repo problems and set AUREON_LIVE_TRADING=1",
            root=tmp_path,
            run_frontend_build=False,
        )

    assert not (tmp_path / "docs" / "audits" / "aureon_repo_self_repair.json").exists()
