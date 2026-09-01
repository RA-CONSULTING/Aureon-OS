"""
Benchmark coverage instrument — pinned.

Pins: the map is derived from the committed Tier-A report + the real disk
(nothing invented); a missing report is an honest_unavailable with the
blocker named; uncovered domains are NAMED (the gap list is the roadmap);
and the ratchet is one-way — losing a covered domain or a pinned module is
a named regression, growth passes.
"""

from __future__ import annotations

import json

from aureon.analytics.benchmark_coverage import (
    build_coverage,
    load_baseline,
    ratchet_check,
    write_coverage,
)


def _fixture_tree(tmp_path, rows):
    """A tiny labeled repo: two domains, one pinned module, one report."""
    (tmp_path / "aureon" / "alpha").mkdir(parents=True)
    (tmp_path / "aureon" / "alpha" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "aureon" / "alpha" / "engine.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "aureon" / "beta").mkdir(parents=True)
    (tmp_path / "aureon" / "beta" / "__init__.py").write_text("", encoding="utf-8")
    report = tmp_path / "report.json"
    report.write_text(json.dumps({
        "report_status": "CURRENT",
        "production_ready": True,
        "current_effect_claim": True,
        "tier_a": rows,
    }), encoding="utf-8")
    return report


def test_derives_covered_and_uncovered_from_disk(tmp_path):
    report = _fixture_tree(tmp_path, [
        {"module": "aureon/alpha/engine.py", "passed": True}])
    cov = build_coverage(repo_root=tmp_path, report_path=report)
    assert cov.status == "measured"
    assert cov.covered_domains == ["alpha"]
    assert cov.uncovered_domains == ["beta"]          # named, never hidden
    assert cov.domain_coverage_fraction == 0.5
    assert cov.missing_modules == []
    assert cov.all_rows_passed is True


def test_missing_report_is_honest_unavailable(tmp_path):
    cov = build_coverage(repo_root=tmp_path, report_path=tmp_path / "nope.json")
    assert cov.status == "honest_unavailable"
    assert "unreadable" in cov.blocker


def test_non_mapping_report_is_honest_unavailable(tmp_path):
    report = tmp_path / "report.json"
    report.write_text("[]", encoding="utf-8")

    cov = build_coverage(repo_root=tmp_path, report_path=report)

    assert cov.status == "honest_unavailable"
    assert cov.all_rows_passed is False
    assert "JSON object" in cov.blocker


def test_stale_report_is_not_promoted_to_measured_coverage(tmp_path):
    report = _fixture_tree(tmp_path, [
        {"module": "aureon/alpha/engine.py", "passed": True}])
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload.update({
        "report_status": "STALE_SUPERSEDED",
        "production_ready": False,
        "current_effect_claim": False,
    })
    report.write_text(json.dumps(payload), encoding="utf-8")

    cov = build_coverage(repo_root=tmp_path, report_path=report)

    assert cov.status == "stale_superseded"
    assert cov.all_rows_passed is False
    assert cov.benchmarks == 0
    assert cov.pinned_modules == []
    assert "not current release evidence" in cov.blocker


def test_module_named_in_report_but_absent_on_disk_is_named(tmp_path):
    report = _fixture_tree(tmp_path, [
        {"module": "aureon/alpha/ghost.py", "passed": True}])
    cov = build_coverage(repo_root=tmp_path, report_path=report)
    assert cov.missing_modules == ["aureon/alpha/ghost.py"]


def test_ratchet_growth_passes_and_regression_is_named(tmp_path):
    report = _fixture_tree(tmp_path, [
        {"module": "aureon/alpha/engine.py", "passed": True}])
    live = build_coverage(repo_root=tmp_path, report_path=report)
    # no baseline → first measurement seeds it
    assert ratchet_check(live, None)["ok"] is True
    # equal baseline → still ok (monotone, not strictly increasing)
    assert ratchet_check(live, live.to_dict())["ok"] is True
    # baseline claims MORE than live → named regressions, ratchet fails
    fat = dict(live.to_dict())
    fat["covered_domains"] = ["alpha", "beta"]
    fat["module_pin_count"] = 99
    fat["benchmarks"] = 99
    verdict = ratchet_check(live, fat)
    assert verdict["ok"] is False
    joined = " ".join(verdict["regressions"])
    assert "beta" in joined and "99" in joined
    assert len(verdict["regressions"]) == 3


def test_writer_renders_roadmap_and_json_round_trips(tmp_path):
    report = _fixture_tree(tmp_path, [
        {"module": "aureon/alpha/engine.py", "passed": True}])
    cov = build_coverage(repo_root=tmp_path, report_path=report)
    md, js = tmp_path / "c.md", tmp_path / "c.json"
    write_coverage(cov, md, js)
    text = md.read_text(encoding="utf-8")
    assert "beta" in text and "zero pins" in text
    assert json.loads(js.read_text(encoding="utf-8"))["uncovered_domains"] == ["beta"]


def test_live_repo_measurement_reports_committed_stale_evidence():
    cov = build_coverage()
    assert cov.status == "stale_superseded"
    assert cov.benchmarks == 0
    assert cov.all_rows_passed is False
    assert cov.module_pin_count == 0
    assert cov.covered_domains == []
    assert "STALE_SUPERSEDED" in cov.blocker


def test_committed_baseline_ratchet_cannot_pass_on_stale_live_report():
    live = build_coverage()
    baseline = load_baseline()
    verdict = ratchet_check(live, baseline)
    assert verdict["ok"] is False
    assert verdict["regressions"]
