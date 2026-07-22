"""Tests for the SaaS Defense & Validation catalog.

The catalog surfaces the bio family (sensor lanes · statistical-validity dossier · cognitive immune
layer) from the committed Tier-A benchmark report + live bus-traces. It must be pure-read: never import
or run a bio module on a request, never raise (even with no report), and never fabricate status.
"""

from __future__ import annotations

import sys

from aureon.saas import defense_catalog as dc


def test_builds_three_groups_from_committed_report():
    cat = dc.build_defense_catalog()
    assert cat["group_order"] == ["cognitive_immune_layer", "statistical_validity", "sensor_lane"]
    groups = cat["groups"]
    assert set(groups) == set(cat["group_order"])
    # the immune layer's six organs and the six statistical modules are grouped exactly
    assert groups["cognitive_immune_layer"]["module_count"] == 6
    assert groups["statistical_validity"]["module_count"] == 6
    assert groups["sensor_lane"]["module_count"] >= 1
    assert cat["counts"]["total"] == sum(g["module_count"] for g in groups.values())


def test_immune_and_stat_modules_land_in_the_right_group():
    cat = dc.build_defense_catalog()
    immune = {dc._basename(m["module"]) for m in cat["groups"]["cognitive_immune_layer"]["modules"]}
    stat = {dc._basename(m["module"]) for m in cat["groups"]["statistical_validity"]["modules"]}
    assert {"integrity_guard", "swarm_defense", "mcp_membrane",
            "authenticity_discriminator", "immune_memory", "immune_regulation"} <= immune
    assert {"proxy_suite", "null_calibration", "power_analysis",
            "calibration_curve", "multiplicity", "false_discovery"} <= stat


def test_every_row_is_honest_and_bio_scoped():
    cat = dc.build_defense_catalog()
    valid_status = {"live", "real_derived", "cached_real", "no_data", "test_fixture"}
    for g in cat["groups"].values():
        for row in g["modules"]:
            assert row["module"].startswith("aureon/bio/")
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
