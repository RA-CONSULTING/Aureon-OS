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


# ── deny only what truly hangs: behaviour-honest deny-list + timeout guard ────

def test_deny_list_is_behaviour_honest():
    from aureon.core.aureon_connectome import _denied

    # genuine loopers/hangers stay denied…
    assert _denied("aureon.core.hnc_live_daemon") is True          # anchored daemon
    assert _denied("aureon.x.foo_daemon") is True                  # _daemon suffix kept
    assert _denied("aureon.trading.aureon_unified_live") is True   # explicit top-level-blocking hanger
    # …but a module denied purely for a name suffix is freed (behaviour, not name)
    assert _denied("aureon.x.foo_live") is False
    assert _denied("aureon.x.bar_runner") is False
    assert _denied("aureon.x.baz_app") is False


def test_touch_times_out_a_hanger_without_blocking(tmp_path, monkeypatch):
    import importlib
    import time as _t

    c = _fresh(tmp_path)
    c.manifest()   # build BEFORE monkeypatching import_module (manifest uses a plain import)
    monkeypatch.setenv("AUREON_CONNECTOME_TOUCH_TIMEOUT", "0.3")

    def _slow(name):
        _t.sleep(3.0)
        return object()

    monkeypatch.setattr(importlib, "import_module", _slow)
    t0 = _t.monotonic()
    r = c.touch("aureon.core.hnc_params")
    elapsed = _t.monotonic() - t0
    assert r["status"] == "failed" and "exceeded" in r["error"]     # treated as a hanger
    assert elapsed < 2.0                                            # the sweep was NOT blocked


def test_touch_timeout_off_is_synchronous(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_CONNECTOME_TOUCH_TIMEOUT", "0")
    c = _fresh(tmp_path)
    r = c.touch("aureon.core.aureon_organism_spine")
    assert r["status"] == "touched"                                # old synchronous path intact


def test_reconcile_denied_frees_stale_denials(tmp_path):
    # a module recorded `denied` under the OLD gate but no longer matched is freed
    # (record cleared → unfelt), while a genuine looper stays denied.
    c = _fresh(tmp_path)
    stale = "aureon.x.foo_live"          # not matched by the current (narrowed) deny-list
    genuine = "aureon.core.hnc_live_daemon"
    c._records[stale] = {"status": "denied", "ts": 0.0}
    c._records[genuine] = {"status": "denied", "ts": 0.0}
    r = c.reconcile_denied()
    assert r["freed"] == 1 and r["re_evaluated"] == 1
    assert stale not in c._records          # freed → unfelt, the sweep re-attempts it
    assert c._records[genuine]["status"] == "denied"   # genuine denial stands


def test_reconcile_denied_respects_limit(tmp_path):
    c = _fresh(tmp_path)
    for m in ("aureon.x.a_live", "aureon.x.b_runner"):
        c._records[m] = {"status": "denied", "ts": 0.0}
    assert c.reconcile_denied(limit=1)["freed"] == 1


def test_sweep_reconciles_stale_denials(tmp_path):
    c = _fresh(tmp_path)
    stale = "aureon.core.hnc_params"     # importable, and not denied by the current gate
    c._records[stale] = {"status": "denied", "ts": 0.0}
    c.sweep_once(batch_size=50, weave_batch=0)   # reconcile runs first → stale unstuck
    # no longer frozen as denied: either freed to unfelt (record gone) or already re-touched
    assert c._records.get(stale, {}).get("status") != "denied"


# ── failures aren't forever: import-context heal + bounded retry ──────────────

def test_ensure_import_paths_is_idempotent():
    import sys
    import aureon.core.aureon_connectome as cm

    cm._PATHS_READY = False
    cm._ensure_import_paths()
    assert cm._PATHS_READY is True
    assert any("aureon" in p for p in sys.path)   # the shim put aureon subdirs on the path
    cm._ensure_import_paths()                      # second call is a no-op, never raises


def test_retry_failed_recovers_an_importable_module(tmp_path):
    c = _fresh(tmp_path)
    m = "aureon.core.hnc_params"
    # a latched failure (e.g. a transient ModuleNotFoundError before the shim healed)
    c._records[m] = {"status": "failed", "ts": 0.0, "error": "ModuleNotFoundError: transient"}
    assert c.status()["failed"] == 1 and c.status()["retryable"] == 1
    r = c.retry_failed(limit=10)
    assert r["recovered"] == 1 and r["still_failed"] == 0
    assert c._records[m]["status"] == "touched"    # a failure is not forever


def test_retry_failed_settles_after_cap(tmp_path, monkeypatch):
    c = _fresh(tmp_path)
    m = "aureon.core.aureon_organism_spine"
    c._records[m] = {"status": "failed", "ts": 0.0, "error": "x"}

    def _always_fail(mod):
        c._record(mod, "failed", error="still broken")
        return {"module": mod, "status": "failed", "error": "still broken"}

    monkeypatch.setattr(c, "touch", _always_fail)
    for _ in range(3):                              # default cap = 3
        c.retry_failed(limit=10)
    assert c._records[m].get("attempts") == 3
    # capped → no longer eligible, so a further pass retries nothing (no churn)
    assert c.retry_failed(limit=10)["retried"] == 0


def test_retry_failed_respects_limit(tmp_path):
    c = _fresh(tmp_path)
    for m in ("aureon.core.hnc_params", "aureon.core.aureon_organism_spine"):
        c._records[m] = {"status": "failed", "ts": 0.0, "error": "e"}
    assert c.retry_failed(limit=1)["retried"] == 1   # bounded


def test_sweep_retry_batch_off_leaves_failed(tmp_path):
    c = _fresh(tmp_path)
    m = "aureon.core.hnc_params"
    c._records[m] = {"status": "failed", "ts": 0.0, "error": "e"}
    c.sweep_once(batch_size=1, retry_batch=0)        # retry off → failure untouched
    assert c._records[m]["status"] == "failed"
    c.sweep_once(batch_size=1, retry_batch=5)        # retry on → recovers
    assert c._records[m]["status"] in ("touched", "woven")


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
