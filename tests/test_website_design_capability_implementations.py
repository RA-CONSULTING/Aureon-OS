"""Executable evidence tests for all fifteen website design capabilities."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pytest

from aureon.operator.website_design_capabilities.accessibility_reduced_motion import (
    prepare_accessibility_audit,
)
from aureon.operator.website_design_capabilities.claim_state_linter import lint_claim_states
from aureon.operator.website_design_capabilities.common import (
    CapabilityFinding,
    CapabilityInputError,
    CapabilityResult,
    Severity,
)
from aureon.operator.website_design_capabilities.competitor_position_audit import (
    audit_competitor_sources,
)
from aureon.operator.website_design_capabilities.content_inventory_connectors import (
    reconcile_content_inventory,
)
from aureon.operator.website_design_capabilities.cycle import (
    AuthorityDecision,
    run_readonly_design_cycle,
)
from aureon.operator.website_design_capabilities.design_qa_visual_regression import (
    evaluate_visual_regression,
)
from aureon.operator.website_design_capabilities.diagram_connectome_graphics import (
    audit_diagram_fallbacks,
)
from aureon.operator.website_design_capabilities.evidence_bound_copywriting import (
    audit_copy_provenance,
)
from aureon.operator.website_design_capabilities.homepl_deploy_cache_ssl_readback import (
    verify_homepl_readback,
)
from aureon.operator.website_design_capabilities.image_svg_generative_pipeline import (
    audit_image_inventory,
)
from aureon.operator.website_design_capabilities.information_architecture_routing import (
    audit_routing,
)
from aureon.operator.website_design_capabilities.layout_typography_grid import audit_layout
from aureon.operator.website_design_capabilities.motion_interaction import audit_motion
from aureon.operator.website_design_capabilities.performance_core_web_vitals import (
    audit_performance,
)
from aureon.operator.website_design_capabilities.research_object_rendering import (
    audit_research_objects,
)
from aureon.operator.website_design_capabilities.visual_identity_tokens import audit_tokens
from aureon.operator.website_design_capability_set import REQUIRED_SKILL_IDS


def _write(path: Path, content: str | bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _site_fixture(root: Path) -> Path:
    html = """<!doctype html>
<html lang="en"><head><title>Aureon evidence</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="canonical" href="https://example.test/">
</head><body><main>
<a href="/">Home</a>
<h1 data-claim-id="claim-a">Evidence-led systems</h1>
<div data-motion-purpose="reveal-structure">System route</div>
<figure data-system-diagram><svg aria-label="Evidence route"><path data-edge-label="supports"></path></svg>
<figcaption>Evidence moves to review.</figcaption><p data-diagram-fallback>Source supports reviewed claim.</p></figure>
<img src="asset.svg" alt="Evidence route diagram"><button>Inspect evidence</button>
</main></body></html>"""
    css = """:root {
  --color-ink: #08111f;
  --color-paper: #f8fafc;
  --font-body: system-ui;
  --space-unit: 1rem;
  --radius-panel: .5rem;
}
.grid { display: grid; font-size: clamp(1rem, 2vw, 1.25rem); animation: reveal 200ms ease; }
.grid:focus-visible { outline: 2px solid var(--color-paper); }
@media (max-width: 40rem) { .grid { grid-template-columns: 1fr; } }
@media (prefers-reduced-motion: reduce) { .grid { animation: none; transition: none; } }
/* motion-purpose: reveal structure */
"""
    _write(root / "index.html", html)
    _write(root / "style.css", css)
    _write(
        root / "sitemap.xml",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.test/</loc></url></urlset>',
    )
    _write(
        root / "claims.json",
        json.dumps(
            {
                "claims": [
                    {
                        "id": "claim-a",
                        "state": "evidenced",
                        "source": "repo:COMPANY.md",
                        "observed_at": "2026-08-21",
                    }
                ]
            }
        ),
    )
    _write(
        root / "asset.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><path d="M0 0L10 10"/></svg>',
    )
    asset_hash = _sha(root / "asset.svg")
    _write(
        root / "images.json",
        json.dumps(
            {
                "assets": [
                    {
                        "id": "diagram-a",
                        "path": "asset.svg",
                        "rights": "owned",
                        "route_scope": ["/"],
                        "alt": "Evidence route diagram",
                        "sha256": asset_hash,
                    }
                ]
            }
        ),
    )
    _write(root / "baseline.png", b"stable-image-fixture")
    _write(root / "current.png", b"stable-image-fixture")
    _write(
        root / "visual.json",
        json.dumps(
            {
                "cases": [
                    {
                        "id": "home-desktop",
                        "baseline": "baseline.png",
                        "current": "current.png",
                        "baseline_sha256": _sha(root / "baseline.png"),
                        "current_sha256": _sha(root / "current.png"),
                        "difference_ratio": 0.0,
                        "threshold": 0.01,
                        "viewport": {"width": 1440, "height": 900},
                        "javascript": "enabled",
                    }
                ]
            }
        ),
    )
    readback = root / "readback"
    readback.mkdir()
    for relative in ("index.html", "style.css"):
        _write(readback / relative, (root / relative).read_bytes())
    _write(
        root / "release.json",
        json.dumps(
            {
                "cache_version": "fixture-v1",
                "files": [
                    {
                        "path": relative,
                        "sha256": _sha(root / relative),
                        "size": (root / relative).stat().st_size,
                    }
                    for relative in ("index.html", "style.css")
                ],
            }
        ),
    )
    return readback


def test_visual_identity_tokens_executes_on_css_fixture(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = audit_tokens(tmp_path, "style.css")
    assert result.passed
    assert result.metrics["token_count"] == 5


def test_layout_typography_grid_executes_on_page_fixture(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = audit_layout(tmp_path, ["index.html"], ["style.css"])
    assert result.passed
    assert result.metrics["page_count"] == 1


def test_motion_interaction_executes_and_finds_purpose_and_fallback(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = audit_motion(tmp_path, ["index.html", "style.css"])
    assert result.passed
    assert result.metrics["purpose_markers"] >= 2


def test_information_architecture_executes_on_sitemap_and_canonical(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = audit_routing(tmp_path, "sitemap.xml", ["index.html"])
    assert result.passed
    assert result.metrics["route_count"] == 1


def test_evidence_copy_executes_on_claim_ledger(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = audit_copy_provenance(tmp_path, "claims.json", ["index.html"])
    assert result.passed
    assert result.metrics["rendered_claim_count"] == 1


def test_research_object_rendering_executes_on_valid_orcid_and_doi() -> None:
    result = audit_research_objects(
        [
            {
                "id": "orcid-gary",
                "kind": "orcid",
                "title": "Gary Anthony Leckey",
                "identifier": "0009-0004-2792-4649",
                "observed_at": "2026-08-21",
                "source_url": "https://orcid.org/0009-0004-2792-4649",
            },
            {
                "id": "doi-paper",
                "kind": "doi",
                "title": "Method paper",
                "identifier": "10.5281/zenodo.1234567",
                "observed_at": "2026-08-21",
                "source_url": "https://doi.org/10.5281/zenodo.1234567",
            },
        ]
    )
    assert result.passed
    assert result.publishable_ids == ("orcid-gary", "doi-paper")


def test_diagram_connectome_executes_on_semantic_fallback(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = audit_diagram_fallbacks(tmp_path, ["index.html"])
    assert result.passed
    assert result.metrics["diagram_count"] == 1


def test_image_pipeline_executes_on_rights_and_hash_inventory(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = audit_image_inventory(tmp_path, "images.json", max_total_bytes=10_000)
    assert result.passed
    assert result.publishable_ids == ("diagram-a",)


def test_accessibility_executes_and_emits_manual_evidence_plan(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = prepare_accessibility_audit(tmp_path, ["index.html"], ["style.css"])
    assert result.passed
    assert "manual:keyboard-route-and-dialog-flow" in result.evidence


def test_performance_executes_on_static_budgets_and_live_vitals(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = audit_performance(
        tmp_path,
        ["style.css", "asset.svg"],
        {"total_bytes": 20_000, "css_bytes": 10_000, "image_bytes": 10_000},
        {"lcp_ms": 1800.0, "inp_ms": 120.0, "cls": 0.02},
    )
    assert result.passed
    assert result.metrics["lcp_ms"] == 1800.0


def test_performance_vetoes_incomplete_live_vitals(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = audit_performance(tmp_path, ["style.css"], {"total_bytes": 20_000}, None)
    assert not result.passed
    assert any(
        item.code == "live-vitals-evidence" and item.severity is Severity.BLOCKER for item in result.findings
    )


def test_homepl_verifier_executes_without_deploying(tmp_path: Path) -> None:
    readback = _site_fixture(tmp_path)
    result = verify_homepl_readback(
        tmp_path, "release.json", readback, {"hostname": "example.test", "valid": True, "protocol": "TLSv1.3"}
    )
    assert result.passed
    assert result.to_dict()["deployment_authority"] == "none"
    assert any(item.startswith("readback:index.html#sha256=") for item in result.evidence)


def test_claim_linter_executes_and_maps_every_rendered_claim() -> None:
    result = lint_claim_states(
        [
            {
                "id": "claim-a",
                "text": "A validated provider record exists.",
                "state": "evidenced",
                "source": "https://example.test/evidence",
            },
            {
                "id": "claim-b",
                "text": "This remains research.",
                "state": "research",
                "source": "repo:research.md",
                "qualifier": "Research state; not deployed.",
            },
        ],
        ["claim-a", "claim-b"],
    )
    assert result.passed
    assert result.publishable_ids == ("claim-a", "claim-b")


def test_competitor_audit_executes_on_dated_primary_sources() -> None:
    result = audit_competitor_sources(
        [
            {
                "id": "competitor-a",
                "competitor": "Example Systems",
                "source_url": "https://example.test/product",
                "source_type": "primary",
                "captured_at": "2026-08-20",
                "observation": "The product page uses a sparse category statement.",
                "aureon_inference": "Retain a concise first-screen category explanation without copying expression.",
                "copy_instruction": "do-not-copy",
            }
        ],
        as_of=date(2026, 8, 21),
    )
    assert result.passed
    assert result.metrics["record_count"] == 1


def test_visual_regression_executes_on_hash_bound_diff_manifest(tmp_path: Path) -> None:
    _site_fixture(tmp_path)
    result = evaluate_visual_regression(tmp_path, "visual.json")
    assert result.passed
    assert result.metrics["regression_count"] == 0


def test_content_inventory_executes_and_excludes_private_records() -> None:
    result = reconcile_content_inventory(
        [
            {
                "id": "repo-paper",
                "canonical_id": "paper-a",
                "source": "repo",
                "source_id": "research/paper-a.md",
                "visibility": "approved-public",
                "observed_at": "2026-08-21",
                "title": "Public method",
            },
            {
                "id": "drive-finance",
                "canonical_id": "finance-a",
                "source": "drive",
                "source_id": "file-private",
                "visibility": "private",
                "observed_at": "2026-08-21",
                "title": "Internal finance record",
            },
        ],
        ["paper-a"],
    )
    assert result.passed
    assert result.publishable_ids == ("paper-a",)
    assert result.metrics["excluded_count"] == 1


def test_every_capability_rejects_unsafe_or_malformed_input(tmp_path: Path) -> None:
    readback = _site_fixture(tmp_path)
    bad_visual = json.loads((tmp_path / "visual.json").read_text(encoding="utf-8"))
    bad_visual["cases"][0]["difference_ratio"] = 2.0
    _write(tmp_path / "bad-visual.json", json.dumps(bad_visual))
    bad_images = {
        "assets": [
            {"id": "bad", "path": "../escape.svg", "rights": "owned", "route_scope": ["/"], "alt": "bad"}
        ]
    }
    _write(tmp_path / "bad-images.json", json.dumps(bad_images))
    _write(tmp_path / "bad-sitemap.xml", "<urlset>")
    _write(tmp_path / "bad-claims.json", "not json")

    actions: list[tuple[str, Callable[[], object]]] = [
        ("visual_identity_tokens", lambda: audit_tokens(tmp_path, "../style.css")),
        ("layout_typography_grid", lambda: audit_layout(tmp_path, [], ["style.css"])),
        ("motion_interaction", lambda: audit_motion(tmp_path, [])),
        (
            "information_architecture_routing",
            lambda: audit_routing(tmp_path, "bad-sitemap.xml", ["index.html"]),
        ),
        (
            "evidence_bound_copywriting",
            lambda: audit_copy_provenance(tmp_path, "bad-claims.json", ["index.html"]),
        ),
        ("research_object_rendering", lambda: audit_research_objects([])),
        ("diagram_connectome_graphics", lambda: audit_diagram_fallbacks(tmp_path, [])),
        ("image_svg_generative_pipeline", lambda: audit_image_inventory(tmp_path, "bad-images.json")),
        ("accessibility_reduced_motion", lambda: prepare_accessibility_audit(tmp_path, [], ["style.css"])),
        (
            "performance_core_web_vitals",
            lambda: audit_performance(tmp_path, ["style.css"], {"total_bytes": -1}),
        ),
        (
            "homepl_deploy_cache_ssl_readback",
            lambda: verify_homepl_readback(tmp_path, "release.json", readback, {"password": "forbidden"}),
        ),
        (
            "claim_state_linter",
            lambda: lint_claim_states([{"id": "x", "text": "text", "state": "unknown"}], ["x"]),
        ),
        ("competitor_position_audit", lambda: audit_competitor_sources([], as_of=date(2026, 8, 21))),
        ("design_qa_visual_regression", lambda: evaluate_visual_regression(tmp_path, "bad-visual.json")),
        ("content_inventory_connectors", lambda: reconcile_content_inventory([], [])),
    ]
    assert [name for name, _ in actions] == list(REQUIRED_SKILL_IDS)
    for _name, action in actions:
        with pytest.raises(CapabilityInputError, match=".+"):
            action()


def test_claim_and_content_reconciliation_fail_closed_on_unmapped_or_hidden() -> None:
    claims = lint_claim_states(
        [{"id": "mapped", "text": "A sourced fact.", "state": "evidenced", "source": "repo:fact"}],
        ["mapped", "unmapped-rendered"],
    )
    inventory = reconcile_content_inventory(
        [
            {
                "id": "approved",
                "canonical_id": "hidden-approved",
                "source": "orcid",
                "source_id": "work-1",
                "visibility": "public",
                "observed_at": "2026-08-21",
                "title": "Public work",
            }
        ],
        [],
    )
    assert not claims.passed
    assert not inventory.passed
    assert any(
        finding.code == "rendered-claims-mapped" and finding.severity is Severity.BLOCKER
        for finding in claims.findings
    )
    assert any(
        finding.code == "approved-work-coverage" and finding.severity is Severity.BLOCKER
        for finding in inventory.findings
    )


def _passing_results() -> dict[str, CapabilityResult]:
    return {
        skill_id: CapabilityResult(
            skill_id,
            (CapabilityFinding("fixture-pass", Severity.PASS, "Fixture evidence passed."),),
            evidence=(f"fixture:{skill_id}",),
        )
        for skill_id in REQUIRED_SKILL_IDS
    }


def test_hnc_cycle_is_deterministic_closed_and_default_deny() -> None:
    results = _passing_results()
    candidate_hash = "a" * 64
    decision = AuthorityDecision(True, candidate_hash, "homepl:aureonzorzatechnologies.pl")
    first = run_readonly_design_cycle(
        cycle_id="fixture-cycle",
        candidate_hash=candidate_hash,
        target=decision.target,
        results=results,
        authority_decision=decision,
    )
    second = run_readonly_design_cycle(
        cycle_id="fixture-cycle",
        candidate_hash=candidate_hash,
        target=decision.target,
        results=results,
        authority_decision=decision,
    )

    assert first == second
    assert first.state == "authority-recorded-awaiting-external-deployment"
    assert len(first.stages) == 12
    assert all(isinstance(stage.owner, str) and stage.owner for stage in first.stages)
    assert first.stages[-1].next_stage == "Sense"
    assert first.to_dict()["write_performed"] is False
    assert first.to_dict()["deployment_authority"] == "none"
    assert first.stages[8].outcome == "external-effect-not-performed"


def test_hnc_cycle_veto_overrides_supplied_authority_and_missing_skill_fails() -> None:
    results = _passing_results()
    results["claim_state_linter"] = CapabilityResult(
        "claim_state_linter",
        (CapabilityFinding("unsupported", Severity.BLOCKER, "Unsupported claim."),),
    )
    candidate_hash = "b" * 64
    decision = AuthorityDecision(True, candidate_hash, "https://example.test/")
    receipt = run_readonly_design_cycle(
        cycle_id="veto-cycle",
        candidate_hash=candidate_hash,
        target=decision.target,
        results=results,
        authority_decision=decision,
    )
    assert receipt.veto_active
    assert not receipt.authority_binding_valid
    assert receipt.state == "vetoed"

    del results["visual_identity_tokens"]
    with pytest.raises(CapabilityInputError, match="result set mismatch"):
        run_readonly_design_cycle(
            cycle_id="missing-cycle", candidate_hash=candidate_hash, target=decision.target, results=results
        )
