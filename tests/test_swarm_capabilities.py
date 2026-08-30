"""
The Capability Grid — every Aureon domain through the hive, honestly.

Pins: the grid holds exactly the five named lanes; every lane's context
comes from a REAL organ with named provenance; a dark source refuses with a
named blocker (never synthesizes); an unknown lane is refused by name; and
the march is deterministic — timing is measured but never part of identity.
"""

from __future__ import annotations

import pytest

import aureon.swarm.capability_grid as grid
from aureon.swarm.capability_grid import LANES, build_lane, run_grid, run_lane


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


def test_grid_holds_exactly_the_five_named_lanes():
    assert set(LANES) == {"trading", "pattern_recognition", "accounting",
                          "fintech", "coding"}
    with pytest.raises(ValueError, match="by name"):
        build_lane("astrology")


def test_every_lane_carries_real_provenance():
    expectations = {
        "trading": "Kraken",
        "pattern_recognition": "autocorrelation",
        "accounting": "King's Court",
        "fintech": "HMRC MTD",
        "coding": "logic-train audit",
    }
    for name, marker in expectations.items():
        lane = build_lane(name)
        assert marker in lane.provenance, (name, lane.provenance)
        assert lane.blockers == []
        assert lane.contexts, f"{name} produced no contexts"


def test_dark_source_refuses_with_a_named_blocker(monkeypatch, tmp_path):
    monkeypatch.setattr(grid, "_OHLC", tmp_path / "missing.json")
    lane = build_lane("trading")
    assert lane.contexts == []
    assert any("missing" in b and "nothing is synthesized" in b
               for b in lane.blockers)
    out = run_lane(lane)
    assert out["ran"] is False and out["blockers"]


def test_lane_march_is_deterministic_timing_excluded():
    a = run_lane(build_lane("fintech"))
    b = run_lane(build_lane("fintech"))
    assert a["ledger"] == b["ledger"]              # identity: the march itself
    assert a["steps"] == b["steps"] == 24
    assert a["elapsed_s"] > 0.0                    # timing measured, not pinned


def test_grid_runs_all_lanes_with_measured_throughput():
    g = run_grid(max_steps=40)
    assert g["lanes_ran"] == g["lanes_total"] == 5
    for name, lane in g["lanes"].items():
        assert lane["ran"], (name, lane.get("blockers"))
        assert lane["steps_per_s"] > 0
        assert lane["agent_updates_per_s"] > 0
        assert 0 <= lane["decisions_actualized"] <= lane["decisions_total"]
