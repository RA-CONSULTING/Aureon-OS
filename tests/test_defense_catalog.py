"""Tests for the SaaS Defense & Validation catalog.

The catalog surfaces the bio family (sensor lanes · statistical-validity dossier · cognitive immune
layer) from the committed Tier-A benchmark report + live bus-traces. It must be pure-read: never import
or run a bio module on a request, never raise (even with no report), and never fabricate status.
"""

from __future__ import annotations

import sys

from aureon.saas import defense_catalog as dc


def test_builds_nine_groups_from_committed_report():
    cat = dc.build_defense_catalog()
    assert cat["group_order"] == [
        "cognitive_immune_layer", "statistical_validity", "adaptive_direction", "sensor_lane",
        "market_validation", "kings_court_accounting", "harmonic_swarm", "universal_prompt_router",
        "measured_benchmarks",
    ]
    groups = cat["groups"]
    assert set(groups) == set(cat["group_order"])
    # the immune layer's six organs, the six statistical modules, and the adaptive-direction dossier
    # (source audit + inbound MCP transport + runtime audit + outbound brain-reply
    # membrane + the b64 one-field seam itself) grouped exactly
    assert groups["cognitive_immune_layer"]["module_count"] == 6
    assert groups["statistical_validity"]["module_count"] == 6
    assert groups["adaptive_direction"]["module_count"] == 5
    assert groups["sensor_lane"]["module_count"] >= 1
    # HNC market validation: the sentinel benchmark + real-data replay, once the
    # regenerated Tier-A report carries b47/b48
    assert groups["market_validation"]["module_count"] == 2
    # the King's Court accounting body joins by explicit name (b49)
    assert groups["kings_court_accounting"]["module_count"] == 1
    # the harmonic swarm, capability grid, Fleadh scenario + containment
    # study join by name (b50-b52, b55)
    assert groups["harmonic_swarm"]["module_count"] == 4
    # the universal prompt router (one door, enforced envelope, replicator
    # contract, bake suite, Borg acquisition, coherence gate) joins by name
    # (b53-b54, b56-b58)
    # entries are defenses (benchmark rows), not unique files: b54 and b61
    # are distinct defenses that both live in operator/cognition.py
    assert groups["universal_prompt_router"]["module_count"] == 7
    # the honesty layer over the benchmarks themselves: open benchmark (b62)
    # + the coverage march ratchet (b63) join by name
    assert groups["measured_benchmarks"]["module_count"] == 2
    assert cat["counts"]["total"] == sum(g["module_count"] for g in groups.values())


def test_immune_and_stat_modules_land_in_the_right_group():
    cat = dc.build_defense_catalog()
    immune = {dc._basename(m["module"]) for m in cat["groups"]["cognitive_immune_layer"]["modules"]}
    stat = {dc._basename(m["module"]) for m in cat["groups"]["statistical_validity"]["modules"]}
    assert {"integrity_guard", "swarm_defense", "mcp_membrane",
            "authenticity_discriminator", "immune_memory", "immune_regulation"} <= immune
    assert {"proxy_suite", "null_calibration", "power_analysis",
            "calibration_curve", "multiplicity", "false_discovery"} <= stat


def test_every_row_is_honest_and_explicitly_registered():
    cat = dc.build_defense_catalog()
    valid_status = {"live", "real_derived", "cached_real", "no_data", "test_fixture"}
    for g in cat["groups"].values():
        for row in g["modules"]:
            # bio modules join by family; anything else ONLY by explicit
            # registration in _GROUPS — a connection is named, never inferred
            assert (row["module"].startswith("aureon/bio/")
                    or dc._basename(row["module"]) in dc._GROUPS)
            assert isinstance(row["passed"], bool)
            assert row["truth_status"] in valid_status
            assert row["group"] in cat["group_order"]
            assert isinstance(row["metrics"], dict)
            assert row["invariants_passed"] <= row["invariants_total"] or row["invariants_total"] == 0


def test_top_level_truth_status_and_provenance():
    cat = dc.build_defense_catalog()
    assert cat["truth_status"] in {"live", "real_derived", "no_data"}
    assert "provenance" in cat
    assert cat["counts"]["passing"] <= cat["counts"]["total"]


def test_does_not_import_or_run_bio_modules():
    for mod in [m for m in sys.modules if m.startswith("aureon.bio")]:
        del sys.modules[mod]
    before = {m for m in sys.modules if m.startswith("aureon.bio")}
    dc.build_defense_catalog()
    after = {m for m in sys.modules if m.startswith("aureon.bio")}
    assert after == before, f"catalog imported bio modules: {after - before}"


def test_never_raises_without_report(monkeypatch, tmp_path):
    monkeypatch.setattr(dc, "_REPORT_PATH", tmp_path / "does_not_exist.json")
    cat = dc.build_defense_catalog()  # must not raise
    assert cat["counts"]["total"] == 0
    assert cat["truth_status"] == "no_data"
    # groups still present (empty), so the frontend renders an honest empty state
    assert set(cat["groups"]) == set(cat["group_order"])
