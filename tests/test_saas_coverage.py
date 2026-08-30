"""Tests for the SaaS repo-wide coverage audit + deepened domain adapters.

The audit reconciles the real `aureon/` package tree against the SaaS taxonomy + catalog and proves
every package is covered (no uncovered, no phantom). Each covered domain carries a real operational
health rollup derived from the filesystem scan — so `/api/domains` reports depth, not just
import-reachability. Read-only; offline; nothing fabricated.
"""

from __future__ import annotations

import json

from aureon.saas import coverage as cov
from aureon.saas import domains as dom


# ── the reconciliation ────────────────────────────────────────────────────────────────────────


def test_filesystem_packages_are_real_and_plentiful():
    pkgs = cov.filesystem_packages()
    assert len(pkgs) >= 38
    assert "__pycache__" not in pkgs
    for known in ("core", "harmonic", "queen", "operator", "bio", "saas", "cognition"):
        assert known in pkgs


def test_reconcile_is_fully_covered():
    audit = cov.reconcile()
    assert audit.all_covered is True
    assert audit.uncovered == []          # nothing on disk is missing from the taxonomy
    assert audit.phantom == []            # nothing in the taxonomy is absent on disk
    assert audit.coverage_fraction == 1.0
    assert audit.fs_package_count >= 38


def test_build_coverage_audit_has_per_domain_health():
    audit = cov.build_coverage_audit()
    assert audit["all_covered"] is True
    assert audit["adapter_deep_count"] >= 7
    assert len(audit["domains"]) == len(audit["covered"])
    for d in audit["domains"]:
        h = d["health"]
        assert isinstance(h, dict)
        assert h["system_count"] > 0                     # every domain surfaces real systems
        assert 0.0 <= h["wired_fraction"] <= 1.0
        assert h["wired_count"] <= h["system_count"]
        assert isinstance(h["capabilities"], list)


def test_audit_is_deterministic_and_report_byte_identical(tmp_path):
    audit = cov.build_coverage_audit()
    assert cov.build_coverage_audit() == audit          # deterministic (no wall-clock in the body)
    a_md, a_json = tmp_path / "a.md", tmp_path / "a.json"
    b_md, b_json = tmp_path / "b.md", tmp_path / "b.json"
    cov.write_coverage_report(audit, a_md, a_json)
    cov.write_coverage_report(audit, b_md, b_json)
    assert a_md.read_bytes() == b_md.read_bytes()
    assert a_json.read_bytes() == b_json.read_bytes()


def test_json_report_round_trips(tmp_path):
    audit = cov.build_coverage_audit()
    out = tmp_path / "c.json"
    cov.write_coverage_report(audit, tmp_path / "c.md", out)
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["all_covered"] == audit["all_covered"]
    assert loaded["fs_package_count"] == audit["fs_package_count"]


def test_cli_main_exits_zero_when_covered():
    assert cov.main([]) == 0


# ── the deepened domain report ────────────────────────────────────────────────────────────────


def test_domain_report_carries_health_when_catalog_supplied():
    from aureon.saas.catalog import build_catalog

    catalog = build_catalog(use_cache=True)
    report = dom.domain_report(catalog=catalog)
    assert len(report) >= 38
    withealth = [r for r in report if r.get("health")]
    assert len(withealth) >= 30                          # the vast majority carry a real rollup
    for r in report:
        assert "has_adapter" in r
        if r.get("health"):
            assert r["health"]["system_count"] >= 1


def test_domain_report_without_catalog_is_still_reachability_only():
    report = dom.domain_report()
    assert all("health" not in r for r in report)        # backward-compatible: no catalog → no rollup
    assert all("available" in r for r in report)


def test_domain_health_is_none_for_unknown_domain():
    from aureon.saas.catalog import build_catalog

    assert dom.domain_health("definitely_not_a_domain", build_catalog(use_cache=True)) is None
