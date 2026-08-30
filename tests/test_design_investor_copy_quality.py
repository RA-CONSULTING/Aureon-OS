"""Tests for the bounded investor-copy quality control."""

from __future__ import annotations

import io
import json
import sys
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aureon.operator import design_investor_copy_quality as copy_quality
from aureon.operator.design_investor_copy_quality import (
    AUDIT_SCHEMA,
    DEFAULT_POLICY_PATH,
    NON_AUTHORITATIVE_AUTHORITY,
    POLICY_SCHEMA,
    InvestorCopyQualityError,
    audit_investor_copy_quality,
    audit_investor_copy_quality_file,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / DEFAULT_POLICY_PATH
AS_OF = datetime(2026, 7, 30, 18, 0, tzinfo=UTC)


def _policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def _write_site(root: Path, *, investor_extra: str = "") -> Path:
    site = root / "site"
    pages = {
        "index.html": (
            "Home | Aureon Zorza Technologies",
            "Aureon is a research-led systems company. Harmonic Nexus Core informs "
            "Aureon OS through a source-linked, human-gated evidence discipline.",
            "One shared core. Many specialised systems.",
            "Aureon is a research-led systems company. Harmonic Nexus Core informs "
            "Aureon OS and its source-linked, human-gated delivery system.",
        ),
        "funding/investor-deck/index.html": (
            "Investor Brief | Aureon Zorza Technologies",
            "A research-led systems company presenting Evidence OS, a human-gated "
            "commercial wedge grounded in a checkable source trail.",
            "One company. A disciplined path to value.",
            "Aureon is a research-led systems company. Evidence OS is the first "
            "wedge, with an accountable approval point. " + investor_extra,
        ),
        "research/index.html": (
            "Research | Aureon Zorza Technologies",
            "Explore Aureon's source-linked public research trail, conservative "
            "interpretation, and explicit independent-validation boundaries.",
            "Research defines the principles.",
            "The source-linked public research trail does not establish peer review "
            "and is not independent validation.",
        ),
    }
    for relative, (title, description, h1, body) in pages.items():
        target = site / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "<!doctype html><html><head>"
            f"<title>{title}</title>"
            f'<meta name="description" content="{description}">'
            "</head><body>"
            f"<h1>{h1}</h1><main><p>{body}</p></main>"
            "</body></html>",
            encoding="utf-8",
        )
    return site


def test_cli_stdout_is_safe_for_legacy_windows_code_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = {
        "passed": True,
        "feedback_loop": "sense \u2192 orient \u2192 prove",
    }
    monkeypatch.setattr(
        copy_quality,
        "audit_investor_copy_quality_file",
        lambda *args, **kwargs: receipt,
    )
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", stream)

    assert copy_quality.main([]) == 0
    stream.flush()
    output = raw.getvalue().decode("cp1252")
    assert "\\u2192" in output


def test_canonical_policy_is_strict_non_authoritative_and_current() -> None:
    policy = _policy()
    assert policy["schema"] == POLICY_SCHEMA
    assert policy["authority"] == NON_AUTHORITATIVE_AUTHORITY

    result = audit_investor_copy_quality_file(
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert result["schema"] == AUDIT_SCHEMA
    assert result["policy"]["current"] is True
    assert result["release_eligible"] is False
    assert result["package_authority"] == "none"
    assert result["deployment_authority"] == "none"
    assert result["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert result["summary"]["route_count"] == 3
    # The current source intentionally remains blocked until hard-coded investor
    # metrics are removed or routed through a current verified evidence surface.
    assert result["passed"] is False
    assert any(
        item["rule_id"] == "static-traction-count" and item["path"] == "funding/investor-deck/index.html"
        for item in result["findings"]
    )
    assert not any(
        item["rule_id"] == "static-operating-count"
        and item["evidence"].get("match") in {"02 Application", "04 Application"}
        for item in result["findings"]
    )


def test_clean_bounded_site_passes_without_mutation(tmp_path: Path) -> None:
    site = _write_site(REPO_ROOT / "artifacts" / "_copy-quality-test-clean")
    try:
        result = audit_investor_copy_quality(
            _policy(),
            policy_path=POLICY_PATH,
            website_root=site,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )
    finally:
        for path in sorted(site.parent.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        site.parent.rmdir()

    assert result["state"] == "pass"
    assert result["passed"] is True
    assert result["summary"] == {
        "route_count": 3,
        "finding_count": 0,
        "blocker_count": 0,
        "warning_count": 0,
    }


def test_catch_all_language_and_static_metrics_fail_closed() -> None:
    site = _write_site(
        REPO_ROOT / "artifacts" / "_copy-quality-test-blocked",
        investor_extra=(
            "Our Swiss Army architecture has 74 ORCID work groups, 560 views, "
            "521 downloads, 3,745 clones and 947 unique cloners. The public "
            "snapshot lists 11 selected routes, ~1,200 modules, 92 offline "
            "tests and commit 908c4c4."
        ),
    )
    try:
        result = audit_investor_copy_quality(
            _policy(),
            policy_path=POLICY_PATH,
            website_root=site,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )
    finally:
        for path in sorted(site.parent.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        site.parent.rmdir()

    rule_ids = {item["rule_id"] for item in result["findings"]}
    assert result["passed"] is False
    assert {
        "category-language",
        "static-operating-count",
        "static-research-count",
        "static-traction-count",
    }.issubset(rule_ids)
    assert result["summary"]["blocker_count"] >= 10


def test_stale_snapshot_date_and_stale_policy_block() -> None:
    site = _write_site(
        REPO_ROOT / "artifacts" / "_copy-quality-test-stale",
        investor_extra="Evidence snapshot checked 2026-07-01.",
    )
    try:
        snapshot_result = audit_investor_copy_quality(
            _policy(),
            policy_path=POLICY_PATH,
            website_root=site,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )
        stale_policy = deepcopy(_policy())
        stale_policy["refresh_by"] = "2026-07-30T12:00:00Z"
        policy_result = audit_investor_copy_quality(
            stale_policy,
            policy_path=POLICY_PATH,
            website_root=site,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )
    finally:
        for path in sorted(site.parent.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        site.parent.rmdir()

    assert any(item["rule_id"] == "snapshot-date" for item in snapshot_result["findings"])
    assert policy_result["policy"]["current"] is False
    assert policy_result["findings"][0]["rule_id"] == "policy-freshness"


def test_archived_v28_public_finance_figures_remain_blocked() -> None:
    site = _write_site(
        REPO_ROOT / "artifacts" / "_copy-quality-test-finance",
        investor_extra=(
            "The public proposal seeks \u20ac1.5m at a \u20ac6m valuation, "
            "with 18 months runway, 10 customers and \u20ac400k ARR."
        ),
    )
    try:
        result = audit_investor_copy_quality(
            _policy(),
            policy_path=POLICY_PATH,
            website_root=site,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )
    finally:
        for path in sorted(site.parent.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        site.parent.rmdir()

    financial_findings = [item for item in result["findings"] if item["rule_id"] == "financial-figure"]
    assert len(financial_findings) >= 4
    assert any(
        item["rule_id"] == "static-operating-count" and item["evidence"].get("match") == "10 customers"
        for item in result["findings"]
    )
    assert result["passed"] is False


def test_unknown_rule_private_path_and_authority_change_are_rejected(
    tmp_path: Path,
) -> None:
    policy = _policy()
    policy["routes"][0]["rule_ids"].append("free-form-regex")
    with pytest.raises(InvestorCopyQualityError, match="unknown rule"):
        audit_investor_copy_quality(
            policy,
            policy_path=POLICY_PATH,
            website_root=REPO_ROOT / "website",
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    policy = _policy()
    policy["routes"][0]["path"] = "../private.html"
    with pytest.raises(InvestorCopyQualityError, match="safe relative HTML"):
        audit_investor_copy_quality(
            policy,
            policy_path=POLICY_PATH,
            website_root=REPO_ROOT / "website",
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    policy = _policy()
    policy["authority"]["deployment_authority"] = "autonomous"
    with pytest.raises(InvestorCopyQualityError, match="authority changed"):
        audit_investor_copy_quality(
            policy,
            policy_path=POLICY_PATH,
            website_root=REPO_ROOT / "website",
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )
