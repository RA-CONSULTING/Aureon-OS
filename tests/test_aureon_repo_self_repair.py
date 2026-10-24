from __future__ import annotations

import json
from pathlib import Path

import pytest

from aureon.autonomous.aureon_repo_self_repair import default_check_commands, run_repo_self_repair


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


def test_repo_self_repair_refuses_a_write_carrying_a_live_trading_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUREON_AUTONOMY_MODE", "guarded")
    _fake_repo(tmp_path)

    with pytest.raises(RuntimeError, match="refused to write"):
        run_repo_self_repair(
            "Aureon fix its own repo problems and set AUREON_LIVE_TRADING=1",
            root=tmp_path,
            run_frontend_build=False,
        )

    assert not (tmp_path / "docs" / "audits" / "aureon_repo_self_repair.json").exists()


def _quiet_ranking(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Start circulation on a fresh bus so a prior test's ranking does not leak."""

    from aureon.core.organism_circulation import start_organism_circulation, stop_organism_circulation

    monkeypatch.setenv("AUREON_ORGANISM_STATE", str(tmp_path / "organism-state"))
    monkeypatch.setenv("AUREON_ORGANISM_HTTP_PORT", "0")
    monkeypatch.setenv("AUREON_AUTONOMY_AUDIT_PATH", str(tmp_path / "audit.jsonl"))
    stop_organism_circulation()
    started = start_organism_circulation(port=0)
    assert started["started"] is True
    return stop_organism_circulation


def test_a_repeatedly_failing_path_is_ranked_last_and_still_checked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from aureon.autonomous.autonomy_mode import audit_event
    from aureon.core.organism_circulation import deprioritised_targets

    early = "tests/test_aureon_unified_ui_builder.py"
    later = "tests/test_frontend_work_order_executor.py"
    (tmp_path / "aureon").mkdir()
    (tmp_path / "tests").mkdir()
    for name in (early, later):
        (tmp_path / name).write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    stop = _quiet_ranking(tmp_path, monkeypatch)
    try:
        def focused(root: Path) -> list[str]:
            commands = dict(default_check_commands(root))
            return [part for part in commands["focused_self_repair_tests"] if part.endswith(".py")]

        assert focused(tmp_path) == [early, later]
        for _ in range(2):
            audit_event(
                "self_patch_kept",
                tmp_path,
                path=early,
                reason="tests_failed",
                rolled_back=False,
            )
        assert deprioritised_targets() == [early]
        ranked = focused(tmp_path)
        assert ranked == [later, early]
        assert early in ranked
    finally:
        stop()
        _quiet_ranking(tmp_path, monkeypatch)
        stop()
