"""Miner read gate. The public depth table and queen and exchanges stay closed."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRIOR_SWEEP_PIN = "ad9be6c3179bba140fb7e88d5733616046110da9"

pytestmark = pytest.mark.timeout(180)


def _load(text: str) -> dict:
    return json.loads(text)


def _record() -> dict:
    return json.loads(
        (ROOT / "measured" / "aureon_public_miner_sweep.json").read_text(encoding="utf-8")
    )


def _entry(record: dict, symbol: str) -> dict:
    found = [row for row in record["entries"] if row["symbol"] == symbol]
    assert len(found) == 1
    return found[0]


def test_read_gate_keeps_the_bridge_closed_and_the_insight_open() -> None:
    from aureon_public.miner_surface import entry_rows, read_gate_refusal

    rows = {str(row["symbol"]): row for row in entry_rows()}
    assert read_gate_refusal(rows["MinerAIInsight.to_dict"]) is None
    assert read_gate_refusal(rows["get_miner_ai_bridge"]) == "constructor loads the miner bridge"
    assert read_gate_refusal(rows["MinerAIBridge.get_status"]) == "constructor loads the miner bridge"
    assert read_gate_refusal(rows["MinerAIBridge.suggest_quantum_weights"]) == (
        "constructor loads the miner bridge"
    )
    assert read_gate_refusal(rows["MinerAIBridge.start"]) == "name contains start"
    assert read_gate_refusal(rows["MinerAIBridge.is_alive"]) == (
        "property is not called; the worker calls methods"
    )
    assert read_gate_refusal(rows["MinerAIBridge.enhance_skeptical_analysis"]) == (
        "read gate refuses a risky token"
    )
    assert read_gate_refusal(rows["MinerAIBridge.synthesise_council_verdict"]) == (
        "read gate refuses a risky token"
    )
    assert read_gate_refusal(rows["MinerAIBridge.enhance_wisdom_synthesis"]) == (
        "read gate refuses a risky token"
    )


def test_miner_sweep_delta_matches_the_entries() -> None:
    from aureon_public.miner_surface import TESTED, summarize

    record = _record()
    assert record["schema"] == "aureon.public.miner-surface.v1"
    assert record["scope"] == "miner"
    assert record["package"] == "miner"
    assert record["orders"] == "refused"
    assert record["badge"] == "HOLD"
    assert record["go_live_clear"] is False
    assert record["charlie_gate"] == {
        "exchange_calls": "none",
        "live_orders": "off",
        "mining": "off",
        "posture": "HOLD",
        "read_gated": True,
    }
    from aureon_public.guard_loader import PINNED_COMMIT

    assert record["pin_moved"] is False
    assert record["public_depth_republished"] is False
    assert record["global_call_sweep_rewritten"] is False
    assert record["pin"] == PINNED_COMMIT
    assert record["sockets"] == "blocked"
    assert record["processes"] == "blocked"
    assert record["writes"] == "outside sandbox blocked"
    assert record["delta"] == summarize(record["entries"], record["public_table"])
    assert record["public_table"]["miner_reachable"] == 0
    assert record["public_table"]["miner_public_entry_points"] == 0
    assert record["public_table"]["reachable_all_packages"] == 69
    opened = [row for row in record["entries"] if row["opened"] is True]
    assert [(row["module"], row["symbol"]) for row in opened] == list(TESTED)
    assert record["delta"]["opened"] == 1
    assert record["delta"]["tested"] == 1
    assert record["delta"]["opened_delta"] == 1
    assert record["delta"]["tested_delta"] == 1
    assert record["delta"]["swept"] == len(record["entries"])
    assert record["delta"]["refused"] == record["delta"]["swept"] - 1
    for row in record["entries"]:
        assert row["package"] == "miner"
        assert row["order_keys"] == []
        assert row["socket"] == []
        assert row["process"] == []
        assert row["writes"] == []
        for name in row["bad"]:
            assert not str(name).startswith("aureon.exchanges")
            assert not str(name).startswith("aureon.trading")
            assert "exchange" not in str(name)
        if row["opened"]:
            assert row["called"] is True
            assert row["refusal"] is None
            assert row["read_gate"] is None
            assert row["measured_refusal"] is None
        else:
            assert row["called"] is False
            assert row["bad"] == []
            assert row["refusal"]
            assert row["refusal"] == row["read_gate"]
    insight = _entry(record, "MinerAIInsight.to_dict")
    assert insight["called"] is True
    assert "verdict" in insight["result_keys"]
    bridge = _entry(record, "get_miner_ai_bridge")
    assert bridge["opened"] is False
    assert bridge["called"] is False
    assert bridge["refusal"] == "constructor loads the miner bridge"
    start = _entry(record, "MinerAIBridge.start")
    assert start["called"] is False
    assert start["refusal"] == "name contains start"


def test_body_call_runs_the_opened_read_and_refuses_the_bridge() -> None:
    from aureon_public.body import body_call
    from aureon_public.miner_surface import TESTED

    record = _record()
    for module, symbol in TESTED:
        body = _load(body_call(module, symbol))
        assert body["status"] == "cited", body
        assert body["called"] is True
        assert body["result"]["verdict"] == "NEUTRAL"
        assert body["result"]["confidence"] == 0.5
        assert body["result"]["category"] == ""
        assert "order_id" not in body["result"]
        assert "live_orders" not in body
    for symbol in (
        "get_miner_ai_bridge",
        "MinerAIBridge.get_status",
        "MinerAIBridge.start",
        "MinerAIBridge.is_alive",
        "MinerAIBridge.enhance_skeptical_analysis",
        "MinerAIBridge.suggest_quantum_weights",
    ):
        entry = _entry(record, symbol)
        body = _load(body_call("miner/miner_inhouse_ai_bridge.py", symbol))
        assert body.get("called") is not True
        assert body["status"] == "unavailable"
        assert body["reason"] == entry["refusal"]
        assert body.get("live_orders") != "sent"


def test_public_depth_pin_and_badge_stay() -> None:
    from aureon_public.body import OPEN_PLAN_THROUGH, package_depth
    from aureon_public.guard_loader import PINNED_COMMIT

    depth = package_depth()
    assert OPEN_PLAN_THROUGH == 2
    assert PINNED_COMMIT == "bb04503119681adcf832f3c3e9b0cbf09fc7a938"
    assert depth["miner"] == {"public_entry_points": 0, "reachable": 0}
    assert depth["queen"]["reachable"] == 0
    assert depth["exchanges"]["reachable"] == 0
    assert depth["trading"]["reachable"] == 0
    readme = (ROOT / "mcp" / "aureon_public" / "README.md").read_text(encoding="utf-8")
    assert "| miner | 0 | 0 |" in readme
    census = json.loads(
        (ROOT / "measured" / "go_live_stage6_source_census.json").read_text(encoding="utf-8")
    )
    assert census["decision"] == "HOLD"
    assert census["go_live_clear"] is False
    assert census["coverage_plan_open_through"] == 2
    assert census["coverage_plan_stages_3_and_4_open"] is False
    sweep = json.loads(
        (ROOT / "measured" / "aureon_public_call_sweep.json").read_text(encoding="utf-8")
    )
    assert sweep["pin"] == PRIOR_SWEEP_PIN
    plan = (ROOT / "mcp" / "aureon_public" / "COVERAGE_PLAN.md").read_text(encoding="utf-8")
    assert "Reachable now: 69." in plan
    assert "## Miner surface" in plan
    assert "Opened delta 1." in plan


def test_sweep_child_does_not_start_mining_or_call_an_exchange() -> None:
    import os
    import subprocess
    import sys

    mcp = str(ROOT / "mcp")
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": mcp,
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    for symbol in ("MinerAIBridge.start", "get_miner_ai_bridge"):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "aureon_public.miner_sweep",
                "--module",
                "miner/miner_inhouse_ai_bridge.py",
                "--symbol",
                symbol,
            ],
            cwd="/tmp",
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        payload = json.loads(completed.stdout)
        assert payload["called"] is False
        assert payload["bad"] == []
        assert payload["socket"] == []
        assert payload["order_keys"] == []
    assert "aureon.exchanges" not in sys.modules
    assert "aureon.trading" not in sys.modules


def test_queen_call_stays_on_plan_stage_4() -> None:
    from aureon_public.body import body_call

    body = _load(body_call("queen/temporal_ground.py", "compute_zpe_ground"))
    assert body.get("called") is not True
    assert body["reason"] == "plan stage 4 is not open"
