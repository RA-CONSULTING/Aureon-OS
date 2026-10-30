"""Stage-2 tools. Inputs are the repo files and tests named in input_source."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.timeout(600)

_ALLOWLIST = {
    ("alignment/harmonic_resonance.py", "HarmonicAnalysis"),
    ("alignment/pillar_alignment.py", "AlignmentCycleResult"),
    ("alignment/unified_directive.py", "MasterDirective"),
    ("generated/research_cinema/harmonic_nexus_score_model.py", "HarmonicNexusScoreInputs"),
    ("swarm/agent.py", "SwarmAgent"),
    ("swarm/coherence.py", "ClusterCoherence"),
    ("swarm/druidic_council.py", "CouncilReceipt"),
    ("swarm/druidic_council.py", "SeatReceipt"),
    ("swarm/memory_bus.py", "CausalEchoBus"),
    ("swarm/queen_gate.py", "Actualization"),
    ("swarm/steering.py", "SteeringField"),
}


def _load(text: str) -> dict:
    body = json.loads(text)
    assert isinstance(body, dict)
    return body


def test_constructor_allowlist_is_unchanged() -> None:
    from aureon_public.body import _CONSTRUCTOR_ALLOWLIST

    assert _CONSTRUCTOR_ALLOWLIST == _ALLOWLIST


def test_stage2_tools_match_the_tested_entry_points() -> None:
    from aureon_public.stage2_layer import TESTED, TOOLS

    assert len(TOOLS) == len(TESTED)
    assert len({fn.__name__ for fn in TOOLS}) == len(TOOLS)
    for fn in TOOLS:
        assert fn.__doc__
        assert "Args:" in fn.__doc__


def test_import_refusal_names_process_and_outside_write() -> None:
    from aureon_public.stage2_import_sweep import import_refusal

    assert import_refusal(["requests"], [], [], []) == "module import loads an adapter or http client"
    assert import_refusal([], ["127.0.0.1"], [], []) == "module import loads an adapter or http client"
    assert import_refusal([], [], ["Popen x"], []) == "module import starts a process"
    assert import_refusal([], [], [], ["/tmp/outside"], ) == "module import writes outside the sandbox"
    assert import_refusal([], [], [], []) is None


def test_sweep_guard_blocks_a_process_and_an_outside_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import subprocess

    from aureon_public.sweep_guard import install_sweep_guard, snapshot, uninstall_sweep_guard

    monkeypatch.setenv("AUREON_PUBLIC_SWEEP", "1")
    monkeypatch.setenv("AUREON_PUBLIC_SANDBOX", str(tmp_path))
    outside = tmp_path.parent / "aureon-stage2-outside.txt"
    try:
        install_sweep_guard()
        with pytest.raises(OSError, match="process blocked"):
            subprocess.Popen(["/bin/true"])
        with pytest.raises(OSError, match="write blocked"):
            outside.write_text("no", encoding="utf-8")
        snap = snapshot()
    finally:
        uninstall_sweep_guard()
    assert any("Popen" in item for item in snap["processes"])
    assert snap["writes"]
    assert not outside.exists()


def test_fixture_argument_is_not_built_without_the_sweep_env() -> None:
    from aureon_public.body import body_call

    body = _load(
        body_call(
            "cognition/phenolic_bridge.py",
            "summarize_patterns",
            json.dumps({"__sweep_fixture__": "sumerian_enship"}),
        )
    )
    assert body["status"] == "unavailable"
    assert body.get("called") is not True


def test_stage2_known_results() -> None:
    from aureon_public.stage2_layer import (
        stage2_build_report,
        stage2_fallback_marker,
        stage2_is_human_held,
        stage2_predict_next,
        stage2_simulation_fallback,
        stage2_summarize_compounding,
        stage2_summarize_patterns,
        stage2_truth_counts,
        stage2_ungrounded_nodes,
    )

    patterns = _load(stage2_summarize_patterns())
    assert patterns["called"] is True
    assert patterns["result"]["n_compounds"] == 3
    assert patterns["result"]["separable"] == ["luteolin"]
    assert patterns["input_source"] == "tests/test_phenolic_bridge.py"

    predicted = _load(stage2_predict_next())
    assert predicted["called"] is True
    assert predicted["result"] == 7

    report = _load(stage2_build_report())
    assert report["called"] is True
    assert report["result"]["summary"]["status"] == "fail"
    assert report["result"]["summary"]["check_count"] == 0

    nodes = _load(stage2_ungrounded_nodes())
    assert nodes["called"] is True
    assert "Tiger" in nodes["result"]
    assert "Panda" in nodes["result"]

    assert _load(stage2_is_human_held())["result"] is False
    assert _load(stage2_is_human_held("submit"))["result"] is True
    assert _load(stage2_simulation_fallback())["result"] is False

    marker = _load(stage2_fallback_marker())
    assert marker["called"] is True
    assert marker["result"]["truth_status"] == "test_fixture"
    assert marker["result"]["is_live"] is False
    assert marker["result"]["fallback_used_at"] == 123.0

    counts = _load(stage2_truth_counts())
    assert counts["called"] is True
    assert counts["result"]["test_fixture"] == 1
    assert counts["result"]["live"] == 0

    compound = _load(stage2_summarize_compounding())
    assert compound["called"] is True
    assert compound["result"]["status"] == "no_data"
    assert compound["result"]["trade_count"] == 0


def test_stage2_tools_call_real_entry_points() -> None:
    from aureon_public.stage2_layer import TOOLS

    for fn in TOOLS:
        body = _load(fn())
        assert body.get("called") is True, (fn.__name__, body.get("reason"))
        assert body["status"] == "cited"
        assert not str(body["label"]).startswith("helper.")
        raw = json.dumps(body)
        assert "consciousness_" not in raw


def test_stage2_sweep_records_match_body_call() -> None:
    from aureon_public.body import body_call, public_entry_refusal, lookup
    from aureon_public.measurement_stamp import CODE_COMMIT_NOTE, PIN_AUREON_TREE

    calls = json.loads((ROOT / "measured" / "aureon_public_call_sweep.json").read_text(encoding="utf-8"))
    imports = json.loads((ROOT / "measured" / "aureon_public_stage2_imports.json").read_text(encoding="utf-8"))
    for record in (calls, imports):
        assert record["pin"].startswith("8aa6a2d9")
        assert record["aureon_tree"] == PIN_AUREON_TREE
        assert record["pin_aureon_tree"] == PIN_AUREON_TREE
        assert record["code_commit_note"] == CODE_COMMIT_NOTE
        assert record["sockets"] == "blocked"
        assert record["processes"] == "blocked"
        assert record["writes"] == "outside sandbox blocked"
    stage2 = [row for row in calls["entries"] if row["plan_stage"] == 2]
    assert stage2
    assert all(row.get("attempts") for row in stage2)
    for row in calls["entries"]:
        if not row["refused"]:
            continue
        sample = lookup(row["module"], row["symbol"])
        assert sample is not None
        assert public_entry_refusal(sample) == row["refusal"]
        body = _load(body_call(row["module"], row["symbol"]))
        assert body.get("called") is not True
        assert body["reason"] == row["refusal"]


def test_stages_three_and_four_stay_closed() -> None:
    from aureon_public.body import body_call

    closed = {
        "queen/temporal_ground.py": ("compute_zpe_ground", "plan stage 4 is not open"),
        "governance/celtic_voice_bank.py": ("seasonal_gate_for_date", "plan stage 4 is not open"),
        "organism/repository_layers.py": ("compose_repository_layers", "plan stage 4 is not open"),
        "swarm/capability_grid.py": ("build_lane", "stage 4 entry point is not called"),
    }
    for module, (symbol, reason) in closed.items():
        body = _load(body_call(module, symbol))
        assert body.get("called") is not True, symbol
        assert body["status"] == "unavailable"
        assert body["reason"] == reason


_UNTESTED_STAGE2 = (
    ("decoders/book_of_ur.py", "test_phi_resonance_me"),
    ("observer/momentum.py", "set_momentum_tracker"),
    ("observer/predictor.py", "make_predictor"),
    ("observer/wave_predictor.py", "set_wave_predictor"),
    ("observer/wave_predictor.py", "make_predictor"),
)


def test_untested_stage2_entry_points_are_refused() -> None:
    from aureon_public.body import _UNTESTED_STAGE2 as reason
    from aureon_public.body import body_call, dispatch, lookup, public_entry_refusal

    for module, symbol in _UNTESTED_STAGE2:
        row = lookup(module, symbol)
        assert row is not None
        assert public_entry_refusal(row) == reason
        for raw in (
            body_call(module, symbol),
            dispatch(module, symbol, {}, server="public"),
        ):
            body = _load(raw)
            assert body.get("called") is not True, (module, symbol)
            assert body["status"] == "unavailable"
            assert body["reason"] == reason


def test_observer_mode_tools_do_not_return_a_bare_live(monkeypatch: pytest.MonkeyPatch) -> None:
    from aureon_public.stage2_layer import (
        MODE_WHEN_UNSET,
        stage2_gate_buy_veto,
        stage2_gate_sell_veto,
        stage2_is_live,
        stage2_is_shadow,
        stage2_kelly_buffer,
        stage2_narrow_band,
        stage2_observer_mode,
        stage2_phase_veto,
        stage2_reload_mode,
        stage2_volatility_veto,
        stage2_vote_addition,
    )

    monkeypatch.delenv("AUREON_OBSERVER_MODE", raising=False)
    tools = (
        stage2_observer_mode,
        stage2_reload_mode,
        stage2_is_live,
        stage2_is_shadow,
        stage2_gate_buy_veto,
        stage2_gate_sell_veto,
        stage2_narrow_band,
        stage2_kelly_buffer,
        stage2_vote_addition,
        stage2_phase_veto,
        stage2_volatility_veto,
    )
    for fn in tools:
        raw = fn()
        body = _load(raw)
        assert body["called"] is True, fn.__name__
        assert body["result"] == MODE_WHEN_UNSET
        assert body["result"]["mode_env"] is None
        assert '"result": "live"' not in raw
        assert '"result": true' not in raw


def test_stage1_tested_entry_points_are_still_tested() -> None:
    from aureon_public.body import lookup, public_entry_refusal
    from aureon_public.call_sweep import _tested_stage1_tools

    for module, symbol in sorted(_tested_stage1_tools()):
        row = lookup(module, symbol)
        assert row is not None, (module, symbol)
        assert public_entry_refusal(row) is None, (module, symbol)


def test_atn_and_conversion_stay_closed() -> None:
    from aureon_public.body import package_depth

    depth = package_depth()
    assert depth["atn"]["reachable"] == 0
    assert depth["conversion"]["public_entry_points"] == 0
    assert depth["conversion"]["reachable"] == 0
