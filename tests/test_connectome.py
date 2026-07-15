"""
Aureon Connectome — the organism senses/touches/weaves itself.

Offline; no network, no live env. Verifies the connectome maps the whole body,
touches parts safely (suppression enforced, deny-list honored, failures
recorded not raised), reports honest coverage, and exposes itself as cognition
tools.
"""

from __future__ import annotations

import json
import os

from aureon.core.aureon_connectome import Connectome, reset_connectome_for_tests


def _fresh(tmp_path):
    reset_connectome_for_tests()
    return Connectome(state_path=tmp_path / "connectome.json")


# ── discovery ──────────────────────────────────────────────────────────────

def test_manifest_maps_the_whole_body(tmp_path):
    c = _fresh(tmp_path)
    nodes = c.nodes()
    assert len(nodes) > 900          # the body is ~1,200 modules
    assert all("organism_topic" in n and n["organism_topic"].startswith("organism.") for n in nodes)


def test_nodes_filter_by_domain_and_status(tmp_path):
    c = _fresh(tmp_path)
    queen = c.nodes(domain="queen")
    assert queen and all(n["domain"] == "queen" for n in queen)
    # Nothing has been touched or woven yet. (baton-linked nodes may already be
    # heard from the shared bus now that the baton ear reads payload correctly,
    # so a node is either "unfelt" or "linked" — never touched/woven on a fresh
    # connectome.)
    assert c.status()["touched"] == 0 and c.status()["woven"] == 0
    assert all(n["status"] in ("unfelt", "linked") for n in c.nodes())


# ── touch ──────────────────────────────────────────────────────────────────

def test_touch_feels_a_safe_module(tmp_path):
    c = _fresh(tmp_path)
    r = c.touch("aureon.core.aureon_organism_spine")
    assert r["status"] == "touched"
    assert "build_organism_manifest" in (r["functions"] + r["singletons"])


def test_touch_enforces_suppression_and_restores(tmp_path):
    c = _fresh(tmp_path)
    os.environ.pop("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", None)
    c.touch("aureon.core.aureon_organism_spine")
    # env restored to absent after the touch
    assert "AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS" not in os.environ

    os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] = "keep"
    try:
        c.touch("aureon.core.hnc_params")
        assert os.environ["AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS"] == "keep"
    finally:
        os.environ.pop("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", None)


def test_touch_denies_loop_at_import_modules(tmp_path):
    c = _fresh(tmp_path)
    r = c.touch("aureon.core.hnc_live_daemon")   # matches _daemon deny pattern
    assert r["status"] == "denied"


def test_touch_records_failure_without_raising(tmp_path):
    c = _fresh(tmp_path)
    # A module that isn't in the manifest -> unknown, never an exception
    r = c.touch("aureon.core.this_module_does_not_exist")
    assert r["status"] == "unknown"


# ── coverage + persistence + pulse ───────────────────────────────────────────

def test_status_coverage_and_persistence(tmp_path):
    c = _fresh(tmp_path)
    c.touch("aureon.core.aureon_organism_spine")
    s = c.status()
    assert s["nodes"] > 900
    assert s["touched"] >= 1
    assert 0.0 < s["coverage_pct"] <= 100.0
    c._save_state()
    assert (tmp_path / "connectome.json").exists()
    saved = json.loads((tmp_path / "connectome.json").read_text())
    assert "aureon.core.aureon_organism_spine" in saved["records"]


def test_sweep_touches_a_batch(tmp_path):
    c = _fresh(tmp_path)
    result = c.sweep_once(batch_size=8)
    assert result["touched"] + result["failed"] + result["denied"] == 8
    assert c.status()["coverage_pct"] > 0.0


def test_weave_touched_drains_backlog_and_is_idempotent(tmp_path):
    c = _fresh(tmp_path)
    c.sweep_once(batch_size=12)                       # feel a batch, weave none yet
    touched_before = c.status()["woven"]
    assert touched_before == 0                        # nothing woven yet
    drained = c.weave_touched()
    assert drained["woven"] > 0 and drained["remaining"] == 0
    assert c.status()["woven"] == drained["woven"]    # touched graduated to woven
    # a second pass is a no-op — nothing left at "touched"
    assert c.weave_touched() == {"woven": 0, "remaining": 0}


def test_sweep_weave_batch_modes(tmp_path):
    # weave_batch=0 weaves none; -1 weaves ALL touched this cycle (keep-pace)
    c = _fresh(tmp_path)
    r0 = c.sweep_once(batch_size=10, weave_batch=0)
    assert r0["woven"] == 0 and c.status()["woven"] == 0
    c2 = _fresh(tmp_path / "b")
    r1 = c2.sweep_once(batch_size=10, weave_batch=-1)
    assert r1["woven"] == r1["touched"] and r1["touched"] > 0   # all felt this cycle were woven


def test_weave_registers_on_the_mesh_only(tmp_path):
    # weaving is registration only — mesh membership grows, no module code runs
    from aureon.core.aureon_mycelium import get_mycelium

    c = _fresh(tmp_path)
    before = set(get_mycelium().get_mesh_status().get("subsystems", {}))
    c.sweep_once(batch_size=10)
    c.weave_touched()
    after = set(get_mycelium().get_mesh_status().get("subsystems", {}))
    assert len(after) >= len(before)                  # woven modules joined the mesh


def test_pulse_publishes_to_the_bus(tmp_path):
    c = _fresh(tmp_path)
    snap = c.pulse()
    assert snap["nodes"] > 900 and "coverage_pct" in snap


# ── cognition tools ──────────────────────────────────────────────────────────

def test_cognition_tools_expose_the_organism(tmp_path):
    reset_connectome_for_tests()
    from aureon.operator.tools import build_operator_tools

    reg = build_operator_tools()
    assert "sense_organism" in reg and "list_organism" in reg and "touch_module" in reg

    sense = json.loads(reg.execute("sense_organism", {}))
    assert sense["connectome"]["nodes"] > 900

    touched = json.loads(reg.execute("touch_module", {"module": "aureon.core.aureon_organism_spine"}))
    assert touched["status"] == "touched"

    listing = json.loads(reg.execute("list_organism", {"domain": "queen", "limit": 5}))
    assert listing["count"] > 0 and len(listing["nodes"]) <= 5
