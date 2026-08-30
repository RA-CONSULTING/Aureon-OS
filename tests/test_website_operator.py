"""Focused offline guarantees for the Aureon Website Operator."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable, Sequence

import pytest

from aureon.operator import design_candidate_source_closure as source_closure
from aureon.operator import website_operator as website_operator_module
from aureon.operator.design_investor_copy_quality import (
    NON_AUTHORITATIVE_AUTHORITY as INVESTOR_COPY_AUTHORITY,
)
from aureon.operator.design_stakeholder_feedback import (
    FEEDBACK_SCHEMA,
)
from aureon.operator.design_stakeholder_feedback import (
    NON_AUTHORITATIVE_AUTHORITY as STAKEHOLDER_FEEDBACK_AUTHORITY,
)
from aureon.operator.live_surface_reconciliation import (
    reconcile_live_surface,
    write_live_surface_reconciliation,
)
from aureon.operator.website_operator import (
    CommandResult,
    WebsiteOperator,
    WebsiteOperatorError,
    _normalise_design_route,
    build_parser,
    main,
)


def _json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def test_atomic_receipt_write_preserves_concurrent_creator(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "receipt.json"

    def competing_creator(source: Path, target: Path) -> None:
        del source
        Path(target).write_text('{"owner":"concurrent"}\n', encoding="utf-8")
        raise FileExistsError

    monkeypatch.setattr(website_operator_module.os, "link", competing_creator)

    with pytest.raises(WebsiteOperatorError, match="Refusing to overwrite receipt"):
        website_operator_module._atomic_write_json(destination, {"owner": "operator"})

    assert json.loads(destination.read_text(encoding="utf-8")) == {"owner": "concurrent"}


def test_atomic_receipt_write_returns_a_regular_single_link_file(tmp_path: Path) -> None:
    destination = website_operator_module._atomic_write_json(
        tmp_path / "receipt.json",
        {"state": "new"},
    )

    assert destination.is_file()
    assert destination.stat().st_nlink == 1


def test_deploy_staging_directory_rejects_link_or_reparse_traversal(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    linked = tmp_path / "deploy-inputs"
    try:
        website_operator_module.os.symlink(
            outside,
            linked,
            target_is_directory=True,
        )
    except OSError as exc:
        pytest.skip(f"Directory links are unavailable on this host: {exc}")

    with pytest.raises(WebsiteOperatorError, match="link or reparse point"):
        website_operator_module._regular_directory(
            linked,
            label="Deployment-input staging root",
        )


def test_candidate_learning_command_is_explicit_and_local_only() -> None:
    args = build_parser().parse_args(
        [
            "candidate-learning",
            "--candidate-receipt",
            "candidate.v1.json",
            "--visual-review",
            "prepromotion-visual-review.v1.json",
            "--learning-manifest",
            "feedback/pattern.manifest.v1.json",
            "--output",
            "feedback/design-learning.v1.json",
        ]
    )

    assert args.command == "candidate-learning"
    assert args.candidate_receipt == Path("candidate.v1.json")
    assert args.visual_review == Path("prepromotion-visual-review.v1.json")
    assert args.learning_manifest == Path("feedback/pattern.manifest.v1.json")
    assert args.output == Path("feedback/design-learning.v1.json")


def test_editorial_provenance_is_not_required_only_when_no_controlled_asset_exists(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture

    control = operator._editorial_asset_evidence_control()

    assert control["passed"] is True
    assert control["state"] == "not-required-no-controlled-editorial-assets"
    assert control["binding"]["required_public_files"] == []
    assert control["release_eligible"] is False
    assert control["deployment_authority"] == "none"


def test_editorial_provenance_fails_closed_when_controlled_asset_has_no_manifest(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    controlled = operator.site_root / "assets" / "images" / "research" / "substack" / "unbound.webp"
    controlled.parent.mkdir(parents=True)
    controlled.write_bytes(b"not-a-cleared-editorial-image")

    control = operator._editorial_asset_evidence_control()

    assert control["passed"] is False
    assert "without the canonical per-asset provenance manifest" in control["error"]
    assert control["release_eligible"] is False
    assert control["deployment_authority"] == "none"


def test_editorial_semantic_surface_outside_legacy_asset_path_requires_manifest(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    asset = operator.site_root / "assets" / "unbound.webp"
    asset.parent.mkdir(parents=True, exist_ok=True)
    asset.write_bytes(b"unbound")
    index = operator.site_root / "index.html"
    index.write_text(
        index.read_text(encoding="utf-8")
        + (
            '<figure data-editorial-surface-id="rogue-research-surface">'
            '<a href="https://harmonicnexus.substack.com/p/example">'
            '<img src="assets/unbound.webp" alt="private-copy-must-not-leak"></a></figure>'
        ),
        encoding="utf-8",
    )

    control = operator._editorial_asset_evidence_control()

    assert control["passed"] is False
    assert "semantic surfaces exist without" in control["error"]
    assert "private-copy-must-not-leak" not in json.dumps(control)


def test_editorial_substack_webp_reference_without_surface_is_ambiguous(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    index = operator.site_root / "index.html"
    index.write_text(
        index.read_text(encoding="utf-8")
        + (
            '<a href="https://harmonicnexus.substack.com/p/example">'
            '<img src="assets/another-location.webp" alt="example"></a>'
        ),
        encoding="utf-8",
    )

    control = operator._editorial_asset_evidence_control()

    assert control["passed"] is False
    assert "semantic surfaces exist without" in control["error"]


def test_marked_editorial_surface_does_not_mask_unmarked_pair_in_same_file(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    index = operator.site_root / "index.html"
    index.write_text(
        index.read_text(encoding="utf-8")
        + (
            '<figure data-editorial-surface-id="declared-surface">'
            '<a href="https://harmonicnexus.substack.com/p/declared">'
            '<img src="assets/declared.webp" alt="declared"></a></figure>'
            '<article><a href="https://harmonicnexus.substack.com/p/unbound">'
            '<picture><img src="assets/unbound.webp" alt="unbound"></picture>'
            "</a></article>"
        ),
        encoding="utf-8",
    )

    observation = operator._editorial_semantic_surface_observation()

    assert observation["surface_ids"] == ["declared-surface"]
    assert observation["ambiguous_substack_webp_file_count"] == 1
    assert "unbound" not in json.dumps(observation)


def test_duplicate_editorial_surface_identifier_fails_with_manifest(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator, _, _ = operator_fixture
    manifest = operator.repo_root / website_operator_module.DEFAULT_EDITORIAL_PROVENANCE_MANIFEST
    _json(manifest, {"fixture": True})
    index = operator.site_root / "index.html"
    index.write_text(
        index.read_text(encoding="utf-8")
        + (
            '<figure data-editorial-surface-id="declared-surface"></figure>'
            '<section data-editorial-surface-id="declared-surface"></section>'
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        website_operator_module,
        "audit_design_editorial_asset_provenance_file",
        lambda *args, **kwargs: {
            "passed": False,
            "state": "blocked",
            "surface_bindings": [
                {
                    "placements": [
                        {"surface_id": "declared-surface"},
                    ]
                }
            ],
        },
    )

    control = operator._editorial_asset_evidence_control()

    assert control["passed"] is False
    assert "duplicate editorial surface identifier" in control["error"]


def test_editorial_semantic_surface_must_be_declared_by_provenance(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator, _, _ = operator_fixture
    manifest = operator.repo_root / website_operator_module.DEFAULT_EDITORIAL_PROVENANCE_MANIFEST
    _json(manifest, {"fixture": True})
    index = operator.site_root / "index.html"
    index.write_text(
        index.read_text(encoding="utf-8")
        + '<figure data-editorial-surface-id="undeclared-surface"></figure>',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        website_operator_module,
        "audit_design_editorial_asset_provenance_file",
        lambda *args, **kwargs: {
            "passed": True,
            "state": "pass",
            "surface_bindings": [
                {
                    "placements": [
                        {"surface_id": "declared-surface"},
                    ]
                }
            ],
        },
    )

    control = operator._editorial_asset_evidence_control()

    assert control["passed"] is False
    assert "absent from the canonical provenance manifest" in control["error"]


def test_live_drift_command_is_explicit_and_observational_only() -> None:
    args = build_parser().parse_args(
        [
            "live-drift",
            "--route",
            "/research/",
            "--route",
            "funding/investor-deck/index.html",
            "--output",
            "artifacts/website-operator/live-surface.json",
        ]
    )

    assert args.command == "live-drift"
    assert args.route == ["/research/", "funding/investor-deck/index.html"]
    assert args.output == Path("artifacts/website-operator/live-surface.json")


def test_research_attribution_command_is_explicit_and_has_no_output_override() -> None:
    args = build_parser().parse_args(
        [
            "research-attribution",
            "--source-root",
            "artifacts/website-candidates/v44/website",
        ]
    )

    assert args.command == "research-attribution"
    assert args.source_root == Path("artifacts/website-candidates/v44/website")
    assert not hasattr(args, "output")


def test_candidate_work_order_command_requires_reconciliation_evidence() -> None:
    args = build_parser().parse_args(
        [
            "candidate-work-order",
            "--goal",
            "Refine one bounded visual token.",
            "--allow",
            "styles.css",
            "--route",
            "/",
            "--reconciliation-receipt",
            "artifacts/website-operator/live-surface.json",
            "--owner-source-decision",
            "artifacts/website-operator/owner-source-reconciliations/decision.json",
            "--backup-receipt",
            "artifacts/website-operator/backup.json",
            "--run-id",
            "reconciled-style-candidate",
            "--output",
            "artifacts/website-candidates/work-orders/reconciled-style-candidate.v4.json",
        ]
    )

    assert args.command == "candidate-work-order"
    assert args.allowed_paths == ["styles.css"]
    assert args.routes == ["/"]
    assert args.reconciliation_receipt == Path("artifacts/website-operator/live-surface.json")
    assert args.owner_source_decision == Path(
        "artifacts/website-operator/owner-source-reconciliations/decision.json"
    )
    assert args.backup_receipt == Path("artifacts/website-operator/backup.json")


def test_live_drift_cli_returns_nonzero_for_drift_and_zero_only_for_alignment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    receipt = tmp_path / "live-drift.json"

    class FakeOperator:
        def observe_live_surface(self, **_kwargs) -> Path:
            return receipt

    monkeypatch.setattr(
        WebsiteOperator,
        "from_paths",
        classmethod(lambda _cls, **_kwargs: FakeOperator()),
    )

    _json(receipt, {"state": "live-drift-detected", "passed": False})
    assert main(["live-drift"]) == 2
    _json(receipt, {"state": "live-surface-semantically-aligned", "passed": True})
    assert main(["live-drift"]) == 0


def test_live_drift_uses_the_dedicated_artifact_bound_receipt_writer(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator, _, _ = operator_fixture

    class Response:
        status = 200
        headers = {"Content-Type": "text/html"}

        def __init__(self, body: bytes, url: str) -> None:
            self.body = body
            self.url = url

        def geturl(self) -> str:
            return self.url

        def read(self, amount: int = -1) -> bytes:
            return self.body if amount < 0 else self.body[:amount]

        def close(self) -> None:
            return None

    expected = reconcile_live_surface(
        repo_root=operator.repo_root,
        site_root=operator.site_root,
        base_url="https://example.test/",
        routes=["index.html"],
        opener=lambda request, timeout: Response(
            (operator.site_root / "index.html").read_bytes(),
            request.full_url,
        ),
    )
    monkeypatch.setattr(
        website_operator_module,
        "reconcile_live_surface",
        lambda **_kwargs: expected,
    )

    with pytest.raises(WebsiteOperatorError, match="must remain below"):
        operator.observe_live_surface(output=tmp_path / "outside-artifacts.json")

    target = operator.repo_root / "artifacts" / "website-operator" / "live-surface.json"
    written = operator.observe_live_surface(output=target)
    payload = json.loads(written.read_text(encoding="utf-8"))

    assert written == target
    assert payload["release_eligible"] is False
    assert payload["deployment_authority"] == "none"


def _manifest(path: Path, root: Path, relative_paths: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("Path", "Bytes", "Sha256"))
        writer.writeheader()
        for relative in sorted(relative_paths):
            source = root / relative
            writer.writerow(
                {
                    "Path": relative,
                    "Bytes": source.stat().st_size,
                    "Sha256": _sha(source),
                }
            )


def _manifest_records(root: Path, relative_paths: Sequence[str]) -> list[dict]:
    return [
        {
            "Path": relative,
            "Bytes": (root / relative).stat().st_size,
            "Sha256": _sha(root / relative),
        }
        for relative in sorted(relative_paths)
    ]


def _aligned_live_reconciliation(operator: WebsiteOperator, run_id: str) -> Path:
    class Response:
        status = 200
        headers = {"Content-Type": "text/html"}

        def __init__(self, body: bytes, url: str) -> None:
            self.body = body
            self.url = url

        def geturl(self) -> str:
            return self.url

        def read(self, amount: int = -1) -> bytes:
            return self.body if amount < 0 else self.body[:amount]

        def close(self) -> None:
            return None

    source = (operator.site_root / "index.html").read_bytes()
    receipt = reconcile_live_surface(
        repo_root=operator.repo_root,
        site_root=operator.site_root,
        base_url="https://example.test/",
        routes=["index.html"],
        opener=lambda request, timeout: Response(source, request.full_url),
    )
    return write_live_surface_reconciliation(
        receipt,
        operator.repo_root / "artifacts" / "website-operator" / f"{run_id}-alignment.json",
        repo_root=operator.repo_root,
    )


def _dependency_manifest(path: Path) -> int:
    rows = [
        {
            "Source": "index.html",
            "Reference": "styles.css",
            "Disposition": "local-included",
            "Target": "styles.css",
            "Fragment": "",
            "FragmentState": "not-applicable",
        },
        {
            "Source": "index.html",
            "Reference": "social.png",
            "Disposition": "local-included",
            "Target": "social.png",
            "Fragment": "",
            "FragmentState": "not-applicable",
        },
        {
            "Source": "index.html",
            "Reference": "script.js",
            "Disposition": "local-included",
            "Target": "script.js",
            "Fragment": "",
            "FragmentState": "not-applicable",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "Source",
                "Reference",
                "Disposition",
                "Target",
                "Fragment",
                "FragmentState",
            ),
        )
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def _page(body: str | None = None) -> str:
    visible = body or (
        "Aureon connects evidence and research to a retained human authority. "
        "Every public boundary separates a company record from external validation."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Aureon Evidence Company</title>
  <meta name="description" content="Aureon presents evidence-led research and bounded human review for serious technical and commercial decisions.">
  <link rel="canonical" href="https://example.test/">
  <meta property="og:title" content="Aureon Evidence Company">
  <meta property="og:description" content="Evidence-led research with retained human authority.">
  <meta property="og:image" content="https://example.test/social.png">
  <link rel="stylesheet" href="styles.css">
  <script type="application/ld+json">{{"@context":"https://schema.org"}}</script>
</head>
<body>
  <main>
    <h1>One evidence core, bounded decisions</h1>
    <p>{visible}</p>
    <img src="social.png" alt="Aureon evidence system">
    <button type="button">Inspect evidence</button>
  </main>
  <script src="script.js"></script>
</body>
</html>
"""


def _investor_copy_policy() -> dict:
    now = datetime.now(UTC)
    return {
        "schema": "aureon.investor-copy-quality-policy.v1",
        "policy_id": "operator-test-investor-copy",
        "issued_at": (now - timedelta(minutes=1)).isoformat(),
        "refresh_by": (now + timedelta(days=14)).isoformat(),
        "authority": INVESTOR_COPY_AUTHORITY,
        "snapshot_max_age_days": 14,
        "routes": [
            {
                "route": "/",
                "path": "index.html",
                "rule_ids": [
                    "category-language",
                    "claim-boundary",
                    "financial-figure",
                    "hype-language",
                    "meta-description",
                    "single-h1",
                    "snapshot-date",
                    "static-operating-count",
                    "static-research-count",
                    "static-traction-count",
                ],
                "required_concept_groups": [],
            }
        ],
    }


def _investor_copy_audit(operator: WebsiteOperator) -> dict:
    return website_operator_module.audit_investor_copy_quality_file(
        repo_root=operator.repo_root,
        website_root=operator.site_root,
    )


def _fixed_investor_copy_audit(receipt: dict) -> Callable[..., dict]:
    def audit(*_args: object, **_kwargs: object) -> dict:
        return receipt

    return audit


def _warning_only_investor_copy_audit(operator: WebsiteOperator) -> dict:
    receipt = json.loads(json.dumps(_investor_copy_audit(operator)))
    route = receipt["routes"][0]
    finding = {
        "rule_id": "hype-language",
        "severity": "warning",
        "route": route["route"],
        "path": route["path"],
        "message": "Fixture warning with no raw public copy.",
        "evidence": {"fixture": True},
    }
    receipt["findings"] = [finding]
    route["finding_count"] = 1
    route["blocker_count"] = 0
    route["warning_count"] = 1
    receipt["summary"] = {
        "route_count": len(receipt["routes"]),
        "finding_count": 1,
        "blocker_count": 0,
        "warning_count": 1,
    }
    receipt["state"] = "pass"
    receipt["passed"] = True
    return receipt


def _claim_register() -> dict:
    return {
        "schema": "aureon-sector-blades-v1",
        "positioning": {"boundary": "A submission is not an award, customer or independent validation."},
        "blades": [
            {
                "id": "evidence-operations",
                "lane": "commercial-now",
                "name": "Evidence operations",
                "buyer": "Evidence-heavy organisations",
                "problem_or_use_case": "Create a bounded review packet.",
                "shared_core": [
                    "Source lineage",
                    "Claim-state control",
                    "Human review authority",
                ],
                "public_evidence_basis": "Public source establishes the inspectable control method.",
                "strategic_relevance": "A source-bound entry point for evidence-heavy organisations.",
                "next_validation": "Run one design-partner evaluation.",
                "public_boundary": "No customer outcome or deployment is claimed.",
                "source_links": [{"label": "Inspect", "href": "/"}],
            }
        ],
    }


def _public_claim_evidence_register(source_path: Path) -> dict:
    claim = "Public source establishes the inspectable control method."
    boundary = "A submission is not an award, customer or independent validation."
    return {
        "schema": "aureon.public-claim-evidence-register.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "material public website positioning claims",
        "authority": {
            "scope": "read-only public-claim evidence control",
            "release_eligible": False,
            "deployment_authority": "none",
            "package_authority": "none",
            "human_review": "required for material public wording changes",
        },
        "claims": [
            {
                "id": "test-control-method",
                "title": "Inspectable control method",
                "claim": claim,
                "state": "company-authored",
                "boundary": boundary,
                "permitted_wording": [claim],
                "prohibited_inferences": ["customer adoption", "independent validation"],
                "expires_on": "2027-07-26",
                "source": {
                    "path": "website/data/blades.json",
                    "sha256": _sha(source_path),
                    "locator": "$.positioning.boundary",
                    "evidence_texts": [claim],
                    "boundary_text": boundary,
                },
                "public_routes": ["/"],
            }
        ],
    }


def _design_research_source_declaration(repo: Path) -> dict:
    """Create a minimal current local-only research-refresh fixture."""

    observed = datetime.now(UTC) - timedelta(days=1)
    expires = observed + timedelta(days=90)
    snapshot = repo / "docs" / "research" / "fixture-research-record.md"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(
        "# Fixture research record\n\n"
        "This source is a local public-record fixture for bounded evidence review.\n",
        encoding="utf-8",
    )
    source_snapshot = {
        "path": "docs/research/fixture-research-record.md",
        "sha256": _sha(snapshot),
    }
    return {
        "schema": "aureon.design-research-sources.v1",
        "declaration_id": "fixture-design-research-sources",
        "issued_at": (observed - timedelta(days=1)).isoformat(),
        "refresh_due_within_days": 14,
        "authority": {
            "scope": "local redacted research and design source freshness review only",
            "declaration_mutation": "never by this validator",
            "canonical_website_mutation": "never",
            "claim_register_mutation": "never",
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "credential_access": "none",
            "network_access": "none",
            "connector_access": "none",
            "research_refresh_authority": "human review of local public-source evidence only",
        },
        "sources": [
            {
                "id": "fixture-public-research-record",
                "kind": "public-research-record",
                "public_reference": {
                    "kind": "https-url",
                    "value": "https://example.test/research-record",
                },
                "observed_at": observed.isoformat(),
                "expires_at": expires.isoformat(),
                "snapshot": source_snapshot,
                "claim_ids": ["test-control-method"],
                "purpose": "Binds a public research-record fixture to a bounded source-refresh decision.",
                "boundary": "The fixture supports only local source freshness review and does not establish validation, adoption, funding, partnership or endorsement.",
            }
        ],
        "artwork_policy": {
            "state": "not-cleared",
            "confirmed_local_provenance": False,
            "source_artwork_included": False,
            "boundary": "No external artwork is included or cleared by this local source-refresh fixture.",
            "evidence_snapshot": source_snapshot,
        },
    }


def _design_stakeholder_feedback_declaration(repo: Path) -> dict:
    """Create one current, privacy-safe, claim-bound feedback fixture."""

    issued = datetime.now(UTC) - timedelta(hours=1)
    snapshot = repo / "docs" / "research" / "fixture-stakeholder-signals.md"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    snapshot.write_text(
        "# Human-created redacted evidence snapshot\n\n"
        "The first public route needs a clearer evidence-control entry point. "
        "This controlled summary contains no original correspondence or private identifiers.\n",
        encoding="utf-8",
    )
    claim_register = repo / "data" / "website_operator" / "public_claim_evidence_register.v1.json"
    return {
        "schema": FEEDBACK_SCHEMA,
        "feedback_id": "fixture-investor-site-signals",
        "issued_at": issued.isoformat(),
        "refresh_by": (issued + timedelta(days=14)).isoformat(),
        "authority": STAKEHOLDER_FEEDBACK_AUTHORITY,
        "claim_register": {
            "path": "data/website_operator/public_claim_evidence_register.v1.json",
            "sha256": _sha(claim_register),
        },
        "evidence_snapshot": {
            "kind": "human-created-redacted-evidence-snapshot",
            "path": "docs/research/fixture-stakeholder-signals.md",
            "sha256": _sha(snapshot),
        },
        "signals": [
            {
                "signal_id": "fixture-first-visit-clarity",
                "signal_kind": "clarity-gap",
                "disposition": "action-requested",
                "priority": "high",
                "requested_response_dimension": "first-visit-clarity",
                "route_scope": "/",
                "claim_ids": ["test-control-method"],
            }
        ],
    }


def _composite_evidence(repo: Path) -> dict[str, Path]:
    audit_root = repo / "docs" / "audits"
    visual = audit_root / "AUREON_WEBSITE_VISUAL_QA_TEST_V28.json"
    manual = audit_root / "AUREON_WEBSITE_MANUAL_PIXEL_REVIEW_TEST_V28.json"
    manifest = audit_root / "AUREON_VISUAL_RELEASE_GATE_20260726T120000Z_TEST_V28.manifest.json"
    visual_source_hash = "b" * 64
    _json(
        visual,
        {
            "schema": "aureon-website-visual-qa-v28.3",
            "generatedAt": datetime.now(UTC).isoformat(),
            "sourceBinding": {
                "before": {"sha256": visual_source_hash},
                "after": {"sha256": visual_source_hash},
                "stable": True,
            },
        },
    )
    _json(
        manual,
        {
            "schema": "aureon-manual-pixel-review-receipt-v28.1",
            "generatedAt": datetime.now(UTC).isoformat(),
            "websiteTreeSha256": visual_source_hash,
        },
    )
    _json(
        manifest,
        {
            "schema": "aureon-visual-release-gate-manifest-v28.1",
            "gateId": "aureon-v28-composite-visual-release",
            "intent": "final-release",
            "releaseId": "operator-test-final-release",
            "generatedAt": datetime.now(UTC).isoformat(),
            "websiteTreeSha256": visual_source_hash,
            "scope": {"engines": ["chromium", "firefox", "webkit"]},
            "policy": {},
            "evidence": {
                "visualReceipt": {
                    "path": visual.relative_to(repo).as_posix(),
                    "sha256": _sha(visual).lower(),
                },
                "manualPixelReviewReceipt": {
                    "path": manual.relative_to(repo).as_posix(),
                    "sha256": _sha(manual).lower(),
                },
            },
        },
    )
    return {"manifest": manifest, "visual": visual, "manual": manual}


def _config() -> dict:
    return {
        "schema": "aureon.website-operator.config.v1",
        "site": {
            "root": "website",
            "base_url": "https://example.test/",
            "capacity_receipt": "data/website_operator/capacity.json",
            "critical_routes": ["index.html"],
        },
        "ethos": {
            "principles": ["Evidence before momentum."],
            "required_site_signals": [
                {
                    "id": "evidence",
                    "pattern": "\\bevidence\\b",
                    "severity": "error",
                    "message": "Evidence signal is missing.",
                },
                {
                    "id": "research",
                    "pattern": "\\bresearch\\b",
                    "severity": "error",
                    "message": "Research signal is missing.",
                },
                {
                    "id": "human",
                    "pattern": "\\bhuman authority\\b",
                    "severity": "error",
                    "message": "Human authority signal is missing.",
                },
                {
                    "id": "boundary",
                    "pattern": "\\bboundary\\b",
                    "severity": "error",
                    "message": "Boundary signal is missing.",
                },
            ],
            "prohibited_claim_patterns": [
                {
                    "id": "guarantee",
                    "pattern": "\\bguaranteed results\\b",
                    "severity": "error",
                    "message": "Guaranteed results are not permitted.",
                }
            ],
            "claim_inputs": [
                {
                    "path": "website/data/blades.json",
                    "schema": "aureon-sector-blades-v1",
                    "required": True,
                }
            ],
        },
        "budgets": {
            "site_total_bytes": 2_000_000,
            "site_file_count": 100,
            "critical_page_direct_bytes": 500_000,
            "per_file_bytes": {
                ".html": 100_000,
                ".css": 100_000,
                ".js": 100_000,
                ".json": 100_000,
                ".png": 100_000,
            },
        },
        "checks": {
            "require_reduced_motion": True,
            "external": [
                {
                    "id": "v28-composite-visual-release-gate",
                    "enabled": True,
                    "required": True,
                    "command": [
                        "node",
                        "{repo_root}/tools/aureon_visual_release_gate_v28.js",
                        "--repo-root",
                        "{repo_root}",
                        "--manifest",
                        "{repo_root}/docs/audits/"
                        "AUREON_VISUAL_RELEASE_GATE_20260726T120000Z_TEST_V28.manifest.json",
                    ],
                }
            ],
        },
        "design": {
            "minimum_score": 85,
            "competitor_source_target": 2,
            "competitor_max_age_days": 45,
            "nexus_weights": {
                "source_strength": 0.3,
                "coherence": 0.25,
                "repeatability": 0.2,
                "feasibility": 0.15,
                "contradiction_control": 0.1,
            },
            "competitor_sources": [
                {
                    "id": "official-one",
                    "name": "Official benchmark one",
                    "url": "https://example.test/one",
                    "checked_at": datetime.now(UTC).isoformat(),
                    "patterns": ["calm technical authority"],
                },
                {
                    "id": "official-two",
                    "name": "Official benchmark two",
                    "url": "https://example.test/two",
                    "checked_at": datetime.now(UTC).isoformat(),
                    "patterns": ["evidence-led product framing"],
                },
            ],
        },
        "packaging": {
            "command": ["fake-builder", "{output_directory}"],
            "receipt_glob": "aureon-homepl-v28-*-receipt.json",
            "required_release_paths": [
                ".htaccess",
                "index.html",
                "styles.css",
                "script.js",
                "social.png",
                "data/blades.json",
            ],
            "blocked_file_names": [".env"],
            "blocked_extensions": [".key", ".pem"],
            "allowed_file_names": [".htaccess"],
            "allowed_extensions": [
                ".html",
                ".css",
                ".js",
                ".png",
                ".json",
            ],
            "secret_patterns": ["\\bsk-[A-Za-z0-9_-]{20,}\\b"],
        },
        "deployment": {
            "remote_root": "/",
            "backup_script": "website/backup.ps1",
            "publish_script": "website/publish.ps1",
            "readback_script": "tools/readback.ps1",
            "publish_command": [
                "fake-publish",
                "{package}",
                "{manifest}",
                "{site_root}",
                "{remote_root}",
            ],
            "readback_command": [
                "fake-readback",
                "{output}",
                "{package}",
                "{manifest}",
            ],
            "credential_env_names": [
                "AUREON_TEST_FTPS_HOST",
                "AUREON_TEST_FTPS_USER",
                "AUREON_TEST_FTPS_PASSWORD",
            ],
            "required_backup_paths": ["index.html", "styles.css", "script.js"],
            "audit_max_age_hours": 12,
            "backup_max_age_hours": 24,
            "approval_max_age_hours": 4,
            "automatic_rollback": False,
            "credentials_in_receipts": False,
        },
    }


class FakeRunner:
    def __init__(self, repo_root: Path, release_paths: Sequence[str]) -> None:
        self.repo_root = repo_root
        self.release_paths = list(release_paths)
        self.calls: list[list[str]] = []
        self.receipt_mutator = None
        self.composite_returncode = 0
        self.composite_stdout: dict | None = None
        self.attribution_returncode = 0
        self.attribution_stdout = ""

    def __call__(self, command: Sequence[str], cwd: Path) -> CommandResult:
        values = list(command)
        self.calls.append(values)
        if values[:2] == ["git", "status"]:
            return CommandResult(0, " M website/index.html\n")
        if values[:2] == ["git", "rev-parse"]:
            return CommandResult(0, "A" * 40 + "\n")
        if (
            len(values) == 6
            and Path(values[1]).name == "aureon_visual_release_gate_v28.js"
            and values[4] == "--manifest"
        ):
            manifest = json.loads(Path(values[5]).read_text(encoding="utf-8"))
            payload = self.composite_stdout or {
                "state": "pass" if self.composite_returncode == 0 else "blocked",
                "blockers": 0 if self.composite_returncode == 0 else 1,
                "axeViolations": 0,
                "axeIncompleteNodes": 3,
                "manualFailures": 0,
                "manualUnreviewed": 0,
                "sourceTreeSha256": manifest["websiteTreeSha256"],
                "output": None,
            }
            return CommandResult(
                self.composite_returncode,
                json.dumps(payload),
                "" if self.composite_returncode == 0 else "composite gate blocked",
            )
        if values[:2] == ["node", "tools/aureon_research_hydration_attribution.js"]:
            return CommandResult(
                self.attribution_returncode,
                self.attribution_stdout,
                "attribution blocked" if self.attribution_returncode else "",
            )
        if values and values[0] == "fake-builder":
            output = Path(values[1])
            output.mkdir(parents=True, exist_ok=True)
            package = output / "aureon-homepl-v28-test.zip"
            manifest = output / "aureon-homepl-v28-test-manifest.csv"
            dependencies = output / "aureon-homepl-v28-test-dependencies.csv"
            receipt = output / "aureon-homepl-v28-test-receipt.json"
            _manifest(manifest, self.repo_root / "website", self.release_paths)
            local_reference_count = _dependency_manifest(dependencies)
            with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for relative in self.release_paths:
                    archive.write(self.repo_root / "website" / relative, relative)
            files = _manifest_records(self.repo_root / "website", self.release_paths)
            payload = {
                "schema": "aureon-homepl-audited-release-v3",
                "release": "V28",
                "built_at": datetime.now(UTC).isoformat(),
                "source_root": str((self.repo_root / "website").resolve()),
                "package": str(package),
                "package_sha256": _sha(package),
                "manifest": str(manifest),
                "manifest_sha256": _sha(manifest),
                "dependency_manifest": str(dependencies),
                "dependency_manifest_sha256": _sha(dependencies),
                "file_count": len(self.release_paths),
                "total_bytes": sum(item["Bytes"] for item in files),
                "package_root": "/",
                "remote_root": "action-time-confirmation-required",
                "deployment_state": "audited-release-prepared-not-uploaded",
                "package_validation": {
                    "state": "verified",
                    "zip_file_count": len(self.release_paths),
                    "manifest_paths_exact": True,
                    "manifest_bytes_exact": True,
                    "manifest_sha256_exact": True,
                    "staging_dependency_closure_exact": True,
                    "staging_fragment_targets_exact": True,
                },
                "dependency_closure": {
                    "state": "verified-complete",
                    "entry_file_count": len(self.release_paths),
                    "discovered_file_count": 0,
                    "local_reference_count": local_reference_count,
                    "included_local_reference_count": local_reference_count,
                    "missing_local_reference_count": 0,
                    "fragment_reference_count": 0,
                    "verified_fragment_reference_count": 0,
                    "missing_fragment_reference_count": 0,
                    "remote_reference_count": 0,
                    "non_file_reference_count": 0,
                    "remote_origins": [],
                    "files_by_extension": [],
                },
                "files": files,
            }
            if self.receipt_mutator is not None:
                self.receipt_mutator(payload)
            _json(receipt, payload)
            return CommandResult(0, "release built")
        if values and values[0] == "fake-publish":
            return CommandResult(0, "verified")
        if values and values[0] == "fake-readback":
            _json(
                Path(values[1]),
                {
                    "summary": {
                        "successful": len(self.release_paths),
                        "failures": 0,
                    }
                },
            )
            return CommandResult(0, "live readback passed")
        return CommandResult(0)


@pytest.fixture
def operator_fixture(tmp_path: Path) -> tuple[WebsiteOperator, FakeRunner, dict]:
    repo = tmp_path / "repo"
    website = repo / "website"
    website.mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
    (website / "index.html").write_text(_page(), encoding="utf-8")
    (website / "styles.css").write_text(
        "@media (prefers-reduced-motion: reduce) { * { animation: none; } }\n",
        encoding="utf-8",
    )
    (website / "script.js").write_text('"use strict";\n', encoding="utf-8")
    (website / "social.png").write_bytes(b"\x89PNG\r\n\x1a\nfixture")
    (website / ".htaccess").write_text("Options -Indexes\n", encoding="utf-8")
    _json(website / "data" / "blades.json", _claim_register())
    for relative in ("backup.ps1", "publish.ps1"):
        (website / relative).write_text("# test\n", encoding="utf-8")
    (repo / "tools").mkdir()
    (repo / "tools" / "readback.ps1").write_text("# test\n", encoding="utf-8")
    (repo / "tools" / "aureon_visual_release_gate_v28.js").write_text(
        "// invoked through FakeRunner\n",
        encoding="utf-8",
    )
    (repo / "tools" / "aureon_research_hydration_attribution.js").write_text(
        "// invoked through FakeRunner\n",
        encoding="utf-8",
    )
    _composite_evidence(repo)
    _json(
        repo / "data" / "website_operator" / "capacity.json",
        {
            "schema": "aureon.website-operator.hosting-capacity.v1",
            "observed_on": "2026-07-26",
            "source": "authenticated-owner-panel",
            "plan": "test",
            "provider_display": {
                "web_allocation_gb": 37,
                "web_used_gb": 1.11,
            },
            "policy": "capacity-is-context-not-budget",
        },
    )
    config = _config()
    config_path = repo / "aureon" / "operator" / "website_operator.defaults.json"
    _json(config_path, config)
    _json(
        repo / "data" / "website_operator" / "public_claim_evidence_register.v1.json",
        _public_claim_evidence_register(website / "data" / "blades.json"),
    )
    _json(
        repo / "data" / "website_operator" / "design_research_sources.v1.json",
        _design_research_source_declaration(repo),
    )
    _json(
        repo / "data" / "website_operator" / "design_stakeholder_feedback.v1.json",
        _design_stakeholder_feedback_declaration(repo),
    )
    _json(
        repo / "data" / "website_operator" / "investor_copy_quality_policy.v1.json",
        _investor_copy_policy(),
    )
    runner = FakeRunner(repo, config["packaging"]["required_release_paths"])
    operator = WebsiteOperator(
        repo,
        config,
        tmp_path / "receipts",
        runner=runner,
        config_path=config_path,
    )
    return operator, runner, config


def _copy_executable_source_closure(destination_root: Path) -> None:
    source_root = Path(website_operator_module.__file__).resolve().parents[2]
    executable_closure = source_closure.build_source_closure(source_root)
    for row in executable_closure["files"]:
        relative = Path(str(row["path"]))
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / relative, destination)


def test_capabilities_expose_governance_as_owner_gated_and_non_release(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture

    payload = operator.capabilities_payload()

    tool = next(item for item in payload["tools"] if item["id"] == "investor-copy-governance")
    assert tool["category"] == "governance"
    governance = payload["investor_copy_governance"]
    assert governance["decision_verification_available"] is False
    assert governance["simulation_available"] is False
    assert governance["apply_protocol_available"] is False
    assert governance["implementation_tooling_verified"] is False
    assert governance["exact_owner_decision_required"] is True
    assert governance["autonomous_owner_decision"] is False
    assert governance["broad_access_approval_valid"] is False
    assert governance["current_owner_decision_present"] is False
    assert governance["current_apply_authorised"] is False
    assert governance["current_apply_ready"] is False
    assert governance["website_mutation"] == "never"
    assert governance["policy_mutation"] == "never"
    assert governance["candidate_authority"] == "none"
    assert governance["package_authority"] == "none"
    assert governance["release_eligible"] is False
    assert governance["deployment_authority"] == "none"
    boundaries = " ".join(payload["hard_boundaries"])
    assert "Broad system-access approval is not" in boundaries
    assert "verification and shadow simulation are read-only" in boundaries
    assert "no website, package, release, or deployment authority" in boundaries


def _release_inputs(operator: WebsiteOperator) -> tuple[Path, Path]:
    audit_path = operator.audit(run_external=True)
    design_path = operator.design_cycle(
        "Verify the exact current website source before release packaging.",
        run_external=True,
    )
    return audit_path, design_path


def test_research_attribution_is_artifact_bound_and_non_authoritative(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, _ = operator_fixture
    (operator.site_root / "research").mkdir()
    (operator.site_root / "research" / "index.html").write_text("research\n", encoding="utf-8")
    (operator.site_root / "data" / "research.json").write_text("{}\n", encoding="utf-8")
    (operator.site_root / "data" / "research-catalogue.json").write_text("{}\n", encoding="utf-8")
    artifact = (
        operator.repo_root / "artifacts" / "website-operator" / "research-hydration-attribution" / "fixture"
    )
    artifact.mkdir(parents=True)
    trace = artifact / "research-hydration.trace.json"
    prefix = "aureon-attribution:" + ("a" * 24) + ":"
    marker_names = [
        f"{prefix}resource:research-json:complete",
        f"{prefix}resource:research-catalogue-json:complete",
        f"{prefix}research-register-hydration:mutation-observer-delivery",
        f"{prefix}research-profiles-hydration:mutation-observer-delivery",
        f"{prefix}research-notes-hydration:mutation-observer-delivery",
        f"{prefix}research-catalogue-hydration:mutation-observer-delivery",
        f"{prefix}capture-complete",
    ]
    trace_events = [
        {
            "name": "Layout",
            "ph": "X",
            "ts": 100000,
            "dur": 25000,
            "pid": 1,
            "tid": 1,
            "args": {
                "beginData": {"dirtyObjects": 20, "totalObjects": 20, "partialLayout": False},
                "endData": {"layoutRoots": [{"nodeName": "#document"}]},
            },
        },
        *[
            {"name": name, "ph": "I", "ts": 90000 + index, "dur": 0, "pid": 1, "tid": 1}
            for index, name in enumerate(marker_names)
        ],
    ]
    trace_payload = {
        "schema": "aureon.research-hydration-minimized-trace.v1",
        "marker_prefix": prefix,
        "original_event_count": len(trace_events),
        "relevant_event_count": len(trace_events),
        "retained_event_count": len(trace_events),
        "event_limit": 1200,
        "trace_truncated": False,
        "redaction": "minimized fixture",
        "traceEvents": trace_events,
    }
    _json(trace, trace_payload)
    source_snapshot = website_operator_module._research_attribution_tree_snapshot(operator.site_root)
    source_files = {row["path"]: row for row in source_snapshot["files"]}
    selected_paths = (
        "research/index.html",
        "script.js",
        "data/research.json",
        "data/research-catalogue.json",
    )
    selected_files = [source_files[path] for path in selected_paths]
    marker_rows = [
        {"name": name, "timestamp_us": 90000 + index, "phase": "I", "pid": 1, "tid": 1}
        for index, name in enumerate(marker_names)
    ]
    hypotheses = [
        {
            "id": target,
            "state": "temporally-correlated",
            "marker_count": 1,
            "document_root_layout_count": 1,
            "full_document_layout_count": 1,
            "correlations": [
                {
                    "marker": f"{prefix}{target}:mutation-observer-delivery",
                    "relation": "precedes-within-window",
                    "marker_to_layout_start_ms": 10,
                    "layout_kind": "full-document",
                    "layout_duration_ms": 25,
                    "layout_dirty_objects": 20,
                    "layout_total_objects": 20,
                }
            ],
            "limitation": "A temporal relationship does not prove causation.",
        }
        for target in (
            "research-register-hydration",
            "research-profiles-hydration",
            "research-notes-hydration",
            "research-catalogue-hydration",
        )
    ]
    receipt = artifact / "AUREON_RESEARCH_HYDRATION_ATTRIBUTION.json"
    _json(
        receipt,
        {
            "schema": "aureon.research-hydration-attribution.v1",
            "observed_at": "2026-07-28T12:00:00Z",
            "state": "complete",
            "analysis_only": True,
            "release_eligible": False,
            "package_authority": "none",
            "deployment_authority": "none",
            "authority": {
                "scope": "read-only staged or canonical research-route runtime attribution",
                "canonical_website_mutation": "never",
                "candidate_creation": "none",
                "release_eligibility": False,
                "package_authority": "none",
                "deployment_authority": "none",
                "credential_access": "none",
            },
            "target": {
                "route": "/research/",
                "viewport": {"width": 1440, "height": 1000},
                "browser": "chromium",
                "self_hosted": True,
                "response": {"status": 200, "same_origin": True},
                "source_root": str(operator.site_root),
                "source_before": {
                    "root": str(operator.site_root),
                    "tree_sha256": source_snapshot["sha256"],
                    "file_count": source_snapshot["file_count"],
                    "total_bytes": source_snapshot["total_bytes"],
                    "selected_files": selected_files,
                },
                "source_after_tree_sha256": source_snapshot["sha256"],
                "source_stable": True,
            },
            "instrumentation": {
                "protocol_version": "aureon.research-hydration-attribution.protocol.v2",
                "protocol_sha256": _sha(
                    operator.repo_root / "tools" / "aureon_research_hydration_attribution.js"
                ).lower(),
                "marker_prefix": prefix,
                "post_load_wait_ms": 800,
                "playwright_source": "fixture",
                "browser_version": "fixture",
                "capture_count": 1,
                "method": "fixture single capture",
                "non_gating": True,
                "caveat": "single capture only",
            },
            "observed": {
                "events": [
                    {"name": name, "time_ms": float(index)} for index, name in enumerate(marker_names)
                ],
                "events_truncated": False,
                "register_rows": 1,
                "profile_cards": 1,
                "note_cards": 1,
                "catalogue_records": 1,
            },
            "runtime_messages": {"console_counts": {}, "page_error_count": 0},
            "coverage": {
                "route_success": True,
                "route_status": 200,
                "same_origin": True,
                "runtime_clean": True,
                "expected_resources": ["research-json", "research-catalogue-json"],
                "missing_resources": [],
                "expected_targets": [
                    "research-register-hydration",
                    "research-profiles-hydration",
                    "research-notes-hydration",
                    "research-catalogue-hydration",
                ],
                "missing_targets": [],
                "missing_runtime_marks": [],
                "missing_observed_counts": [],
                "observer_log_complete": True,
                "minimized_trace_complete": True,
                "document_root_layout_count": 1,
                "passed": True,
            },
            "correlation": {
                "marker_count": len(marker_rows),
                "markers": marker_rows,
                "layout_count": 1,
                "document_root_layout_count": 1,
                "full_document_layout_count": 1,
                "longest_layouts": [{"duration_ms": 25}],
                "initial_document_layout_finding": {"state": "inconclusive"},
                "hypotheses": hypotheses,
            },
            "trace": {
                "path": trace.relative_to(operator.repo_root).as_posix(),
                "schema": "aureon.research-hydration-minimized-trace.v1",
                "sha256": _sha(trace).lower(),
                "original_event_count": len(trace_events),
                "relevant_event_count": len(trace_events),
                "retained_event_count": len(trace_events),
                "trace_truncated": False,
                "raw_trace_persisted": False,
            },
            "next_step": "Investigative hint only.",
        },
    )
    runner.attribution_stdout = json.dumps(
        {"state": "complete", "receipt": str(receipt), "trace": str(trace)}
    )

    assert operator.research_hydration_attribution() == receipt
    assert runner.calls[-1] == [
        "node",
        "tools/aureon_research_hydration_attribution.js",
        "--source-root",
        "website",
    ]
    with pytest.raises(WebsiteOperatorError, match="inside this repository"):
        operator.research_hydration_attribution(tmp_path / "outside")

    original_receipt = json.loads(receipt.read_text(encoding="utf-8"))
    incomplete_receipt = dict(original_receipt)
    incomplete_coverage = dict(original_receipt["coverage"])
    incomplete_coverage["passed"] = False
    incomplete_receipt["coverage"] = incomplete_coverage
    _json(receipt, incomplete_receipt)
    with pytest.raises(WebsiteOperatorError, match="coverage did not pass"):
        operator.research_hydration_attribution()
    _json(receipt, original_receipt)

    trace.write_text('{"traceEvents":["mutated"]}\n', encoding="utf-8")
    with pytest.raises(WebsiteOperatorError, match="trace is missing or no longer matches"):
        operator.research_hydration_attribution()


def test_default_operator_config_and_schema_stay_in_contract() -> None:
    repo = Path(__file__).resolve().parents[1]
    defaults = json.loads(
        (repo / "aureon" / "operator" / "website_operator.defaults.json").read_text(encoding="utf-8")
    )
    schema = json.loads(
        (repo / "aureon" / "operator" / "website_operator.schema.json").read_text(encoding="utf-8")
    )

    properties = schema["properties"]
    assert set(defaults).issubset(properties)
    design_schema = properties["design"]
    assert design_schema["type"] == "object"
    assert set(defaults["design"]).issubset(design_schema["properties"])
    assert set(defaults["design"]["nexus_weights"]) == set(
        design_schema["properties"]["nexus_weights"]["required"]
    )


def _build_accepted_release(
    operator: WebsiteOperator,
    output_directory: Path,
) -> Path:
    audit_path, design_path = _release_inputs(operator)
    return operator.build_release(
        audit_path,
        output_directory,
        design_cycle_receipt=design_path,
        human_visual_accepted=True,
        human_visual_accepted_by="Test visual reviewer",
    )


def test_inventory_separates_capacity_from_performance_budget(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, config = operator_fixture
    inventory = operator.inventory_payload()
    capacity = inventory["hosting_capacity"]
    assert inventory["state"] == "observed-read-only"
    assert inventory["tree_sha256"]
    assert capacity["available"] is True
    assert capacity["observation"]["provider_display"]["web_allocation_gb"] == 37
    assert "not a performance or media budget" in capacity["policy"]
    assert inventory["total_bytes"] < config["budgets"]["site_total_bytes"]
    assert inventory["git"]["website_dirty"] is True


def test_clean_site_passes_and_unsafe_claim_blocks(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    clean = operator.audit_payload(run_external=False)
    assert clean["state"] == "pass"
    assert clean["summary"]["blockers"] == 0
    index = operator.site_root / "index.html"
    index.write_text(
        _page("Guaranteed results from research with human authority and a public boundary."),
        encoding="utf-8",
    )
    blocked = operator.audit_payload(run_external=False)
    assert blocked["state"] == "blocked"
    assert any(item["code"] == "ethos.claim.guarantee" for item in blocked["findings"])


def test_legacy_blade_disclosure_fields_block_audit(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    register_path = operator.site_root / "data" / "blades.json"
    register = json.loads(register_path.read_text(encoding="utf-8"))
    register["blades"][0]["current_evidence_state"] = "Internal company record"
    _json(register_path, register)

    blocked = operator.audit_payload(run_external=False)

    assert blocked["state"] == "blocked"
    finding = next(item for item in blocked["findings"] if item["code"] == "claims.blade_legacy_fields")
    assert finding["evidence"]["fields"] == ["current_evidence_state"]


def test_blocked_audit_becomes_non_authoritative_work_order(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    (operator.site_root / "index.html").write_text(
        _page("Guaranteed results from research with human authority and a public boundary."),
        encoding="utf-8",
    )
    audit_path = operator.audit(run_external=False)
    order_path = operator.work_order(audit_path)
    order = json.loads(order_path.read_text(encoding="utf-8"))
    assert order["state"] == "proposed-local-work"
    assert order["task_count"] >= 1
    assert order["mutation_authority"] == "none"
    assert order["publication_authority"] == "none"


def test_operator_stages_and_validates_v30_candidate_without_mutating_canonical_site(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    _copy_executable_source_closure(operator.repo_root)
    canonical_before = (operator.site_root / "styles.css").read_text(encoding="utf-8")

    work_order = operator.create_candidate_work_order(
        goal="Refine one existing style token without changing public claims.",
        allowed_paths=["styles.css"],
        routes=["/"],
        reconciliation_receipt=_aligned_live_reconciliation(operator, "operator-style-candidate"),
        run_id="operator-style-candidate",
    )
    staged = operator.stage_candidate(work_order)
    candidate_style = operator.repo_root / staged["candidate_website"] / "styles.css"
    candidate_style.write_text(
        "@media (prefers-reduced-motion: reduce) { * { animation: none; } }\nbody { color: #123456; }\n",
        encoding="utf-8",
    )

    receipt_path = operator.validate_candidate(
        work_order,
        claim_impacts=[
            {
                "path": "styles.css",
                "classification": "no-material-claim-change",
                "rationale": "The bounded styling adjustment does not alter public positioning wording.",
            }
        ],
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert receipt["passed"] is True
    assert receipt["state"] == "validated-local"
    assert receipt["release_eligible"] is False
    assert receipt["deployment_authority"] == "none"
    assert (operator.site_root / "styles.css").read_text(encoding="utf-8") == canonical_before
    assert receipt_path.parent == operator.repo_root / staged["candidate_root"]


def test_previous_design_cycle_auto_discovery_ignores_noncanonical_audit_artifacts(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    canonical = operator.receipts_dir / "20260730T010000Z-design-cycle-deadbeef.json"
    expected = {
        "schema": website_operator_module.DESIGN_CYCLE_SCHEMA,
        "config_sha256": operator.config_sha256,
        "run_id": "canonical-cycle",
    }
    _json(canonical, expected)

    unrelated = operator.receipts_dir / "20260730T020000Z-design-cycle-schema-contract-fix.json"
    _json(
        unrelated,
        {
            "schema": "aureon.website_operator.design_cycle_schema_contract_fix.v1",
            "config_sha256": operator.config_sha256,
        },
    )
    os.utime(unrelated, (canonical.stat().st_mtime + 10, canonical.stat().st_mtime + 10))

    assert operator._previous_design_cycle() == expected
    with pytest.raises(WebsiteOperatorError, match="unsupported schema"):
        operator._previous_design_cycle(unrelated)


def test_design_cycle_is_scored_source_bound_and_cannot_deploy(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    payload = operator.design_cycle_payload(
        "Benchmark and improve the public website to an investor-ready institutional standard.",
        run_external=True,
    )

    assert payload["schema"] == "aureon-website-design-job-v1"
    assert payload["state"] == "verified-local-human-review-required"
    assert payload["source_tree_sha256"]
    assert payload["design_nexus"]["score"] >= 85
    assert payload["design_nexus"]["kind"] == "operational-evidence-coherence-score"
    assert "not scientific validation" in payload["design_nexus"]["claim_boundary"]
    assert payload["hard_gates_pass"] is True
    assert payload["summary"]["ready_for_deployment"] is False
    assert payload["deployment_state"] == "not-authorised-not-attempted"
    assert payload["authority_boundaries"]["deployment"] == "none"
    assert payload["authority_boundaries"]["human_visual_acceptance_required"] is True
    assert "v1 retained-local" in payload["authority_boundaries"]["owner_source_selection"]
    assert "v2 verified-live-backup" in payload["authority_boundaries"]["owner_source_selection"]
    assert "never make or infer" in payload["authority_boundaries"]["editorial_rights_decision"]
    assert "candidate re-audit only" in payload["authority_boundaries"]["investor_copy_repair"]
    assert {
        "validate_owner_source_reconciliation",
        "prepare_editorial_asset_rights_decisions",
        "preflight_investor_copy_repair_contract",
        "preflight_investor_copy_repair_work_order",
        "verify_investor_copy_repair_contract",
        "evaluate_investor_copy_repair_candidate",
        "verify_investor_copy_governance_decision",
        "simulate_investor_copy_governance_application",
        "apply_exact_owner_approved_investor_copy_governance_delta",
    }.issubset(payload["skill_hierarchy"]["L0_atomic"])
    assert "shadow simulation are read-only" in payload["authority_boundaries"]["investor_copy_governance"]
    assert (
        "broad system access is not approval" in payload["authority_boundaries"]["investor_copy_governance"]
    )
    assert (
        "no website, policy, candidate, package"
        in payload["authority_boundaries"]["investor_copy_governance"]
    )
    assert payload["candidate_control"]["schema"] == "aureon.design-work-order.v4"
    assert payload["candidate_control"]["release_eligible"] is False
    assert payload["candidate_control"]["deployment_authority"] == "none"
    assert payload["work_orders"][0]["candidate_work_order_required"] is True
    assert "artifacts/website-candidates" in payload["work_orders"][0]["allowed_scope"][0]
    assert payload["release_eligible"] is True
    assert payload["stop_control"]["continuation_allowed"] is True
    controls = payload["evidence_controls"]
    assert controls["benchmark"]["passed"] is True
    assert controls["benchmark"]["release_eligible"] is False
    assert controls["benchmark"]["deployment_authority"] == "none"
    assert controls["public_claims"]["passed"] is True
    assert controls["public_claims"]["release_eligible"] is False
    assert controls["public_claims"]["deployment_authority"] == "none"
    assert controls["investor_copy"]["passed"] is True
    assert controls["investor_copy"]["release_eligible"] is False
    assert controls["investor_copy"]["deployment_authority"] == "none"
    assert controls["investor_copy"]["binding"]["blocker_count"] == 0
    assert controls["investor_copy"]["binding"]["warning_count"] == 0
    assert controls["research_refresh"]["passed"] is True
    assert controls["research_refresh"]["release_eligible"] is False
    assert controls["research_refresh"]["deployment_authority"] == "none"
    assert controls["research_refresh"]["receipt"]["artwork"]["state"] == "not-cleared"
    assert controls["research_refresh"]["receipt"]["artwork"]["cleared_for_use"] is False
    assert controls["editorial_assets"]["passed"] is True
    assert controls["editorial_assets"]["state"] == "not-required-no-controlled-editorial-assets"
    assert controls["editorial_assets"]["release_eligible"] is False
    assert controls["editorial_assets"]["deployment_authority"] == "none"
    assert {
        "benchmark_evidence_current",
        "claims_evidence_current",
        "investor_copy_quality_current",
        "research_source_refresh_current",
        "editorial_asset_provenance_current",
    }.issubset({gate["id"] for gate in payload["hard_gates"]})
    titles = {member["title"] for member in payload["design_council"]}
    assert {
        "Website Design Director",
        "Claims and Evidence Editor",
        "Motion Designer",
        "Accessibility and Performance QA",
        "Design Release QA",
    }.issubset(titles)


def test_design_cycle_external_skip_is_diagnostic_only(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    payload = operator.design_cycle_payload(
        "Run a deliberately incomplete diagnostic cycle.",
        run_external=False,
    )

    assert payload["state"] == "diagnostic-only-external-checks-skipped"
    assert payload["hard_gates_pass"] is False
    assert payload["release_eligible"] is False
    gate = next(gate for gate in payload["hard_gates"] if gate["id"] == "external_checks_complete")
    assert gate["passed"] is False
    assert gate["evidence"]["diagnostic_skip_cannot_verify"] is True
    assert payload["evidence_controls"]["benchmark"]["passed"] is True
    assert payload["evidence_controls"]["public_claims"]["passed"] is True
    assert payload["evidence_controls"]["investor_copy"]["passed"] is True
    assert payload["evidence_controls"]["research_refresh"]["passed"] is True
    assert payload["evidence_controls"]["editorial_assets"]["passed"] is True


def test_design_cycle_blocks_static_investor_figures_and_emits_bounded_task(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    (operator.site_root / "index.html").write_text(
        _page(
            "Aureon is a research-led systems company. Harmonic Nexus Core informs "
            "Aureon OS. The public snapshot recorded 12 views checked 2026-07-30."
        ),
        encoding="utf-8",
    )

    payload = operator.design_cycle_payload(
        "Remove internal-looking figures from the investor-facing route.",
        run_external=True,
    )

    control = payload["evidence_controls"]["investor_copy"]
    gate = next(item for item in payload["hard_gates"] if item["id"] == "investor_copy_quality_current")
    assert control["passed"] is False
    assert control["binding"]["blocker_count"] == 2
    assert gate["passed"] is False
    assert gate["evidence"]["binding"]["blocker_count"] == 2
    assert "register" not in gate["evidence"]
    assert payload["summary"]["blocker_count"] >= 2
    closure_gate = next(item for item in payload["hard_gates"] if item["id"] == "open_audit_findings_closed")
    assert closure_gate["evidence"]["investor_copy_blockers"] == 2
    assert payload["hard_gates_pass"] is False
    assert payload["release_eligible"] is False
    assert "12 views" not in json.dumps(control)
    assert any(
        task.get("finding", {}).get("code") == "copy.investor-quality" for task in payload["work_orders"]
    )


def test_investor_copy_control_rejects_malformed_or_private_receipt_fields(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator, _, _ = operator_fixture
    valid = _investor_copy_audit(operator)
    malformed_cases: list[tuple[str, dict]] = []

    wrong_schema = json.loads(json.dumps(valid))
    wrong_schema["schema"] = "aureon.investor-copy-quality-audit.v0"
    malformed_cases.append(("schema", wrong_schema))

    wrong_state = json.loads(json.dumps(valid))
    wrong_state["state"] = "blocked"
    malformed_cases.append(("state", wrong_state))

    wrong_authority = json.loads(json.dumps(valid))
    wrong_authority["authority"] = {"release_eligible": True}
    malformed_cases.append(("authority", wrong_authority))

    wrong_policy = json.loads(json.dumps(valid))
    wrong_policy["policy"]["current"] = False
    malformed_cases.append(("policy-current", wrong_policy))

    wrong_policy_path = json.loads(json.dumps(valid))
    wrong_policy_path["policy"]["path"] = "data/website_operator/other-policy.json"
    malformed_cases.append(("policy-path", wrong_policy_path))

    wrong_root = json.loads(json.dumps(valid))
    wrong_root["website_root"] = "artifacts/website-candidates/substituted/website"
    malformed_cases.append(("website-root", wrong_root))

    wrong_policy_hash = json.loads(json.dumps(valid))
    wrong_policy_hash["policy"]["sha256"] = "0" * 64
    malformed_cases.append(("policy-hash", wrong_policy_hash))

    wrong_route_hash = json.loads(json.dumps(valid))
    wrong_route_hash["routes"][0]["sha256"] = "0" * 64
    malformed_cases.append(("route-hash", wrong_route_hash))

    negative_count = json.loads(json.dumps(valid))
    negative_count["summary"]["blocker_count"] = -1
    malformed_cases.append(("negative-count", negative_count))

    private_route = json.loads(json.dumps(valid))
    private_route["routes"][0]["path"] = {"raw_copy": "PRIVATE INVESTOR COPY"}
    malformed_cases.append(("private-route", private_route))

    for label, malformed in malformed_cases:
        monkeypatch.setattr(
            website_operator_module,
            "audit_investor_copy_quality_file",
            _fixed_investor_copy_audit(malformed),
        )
        control = operator._investor_copy_evidence_control()
        assert control["passed"] is False, label
        assert "PRIVATE INVESTOR COPY" not in json.dumps(control), label


def test_investor_copy_control_reconciles_route_findings_and_summary_before_release(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator, _, _ = operator_fixture
    inconsistent = json.loads(json.dumps(_investor_copy_audit(operator)))
    route = inconsistent["routes"][0]
    inconsistent["findings"] = [
        {
            "rule_id": "static-traction-count",
            "severity": "blocker",
            "route": route["route"],
            "path": route["path"],
            "message": "Fixture blocker.",
            "evidence": {"fixture": 1},
        },
        {
            "rule_id": "static-operating-count",
            "severity": "blocker",
            "route": route["route"],
            "path": route["path"],
            "message": "Fixture blocker.",
            "evidence": {"fixture": 2},
        },
    ]
    route["finding_count"] = 2
    route["blocker_count"] = 2
    inconsistent["summary"] = {
        "route_count": 1,
        "finding_count": 0,
        "blocker_count": 0,
        "warning_count": 0,
    }
    inconsistent["state"] = "pass"
    inconsistent["passed"] = True
    monkeypatch.setattr(
        website_operator_module,
        "audit_investor_copy_quality_file",
        _fixed_investor_copy_audit(inconsistent),
    )

    payload = operator.design_cycle_payload(
        "Reject an internally inconsistent investor-copy receipt.",
        run_external=True,
    )

    control = payload["evidence_controls"]["investor_copy"]
    investor_gate = next(
        gate for gate in payload["hard_gates"] if gate["id"] == "investor_copy_quality_current"
    )
    assert control["passed"] is False
    assert investor_gate["passed"] is False
    assert payload["hard_gates_pass"] is False
    assert payload["release_eligible"] is False


def test_design_cycle_fails_closed_without_source_bound_config_provenance(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, config = operator_fixture
    unbound = WebsiteOperator(
        operator.repo_root,
        config,
        tmp_path / "unbound-receipts",
        runner=runner,
    )

    payload = unbound.design_cycle_payload(
        "Prove an in-memory config cannot replace source-bound benchmark provenance.",
        run_external=False,
    )

    gate = next(item for item in payload["hard_gates"] if item["id"] == "benchmark_evidence_current")
    assert gate["passed"] is False
    assert "config file is required" in gate["evidence"]["error"]
    assert payload["release_eligible"] is False
    assert payload["deployment_state"] == "not-authorised-not-attempted"


def test_design_cycle_blocks_stale_benchmark_evidence(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, config = operator_fixture
    stale_config = json.loads(json.dumps(config))
    stale_config["design"]["competitor_sources"][0]["checked_at"] = "2020-01-01T00:00:00Z"
    assert operator.config_path is not None
    _json(operator.config_path, stale_config)
    stale = WebsiteOperator(
        operator.repo_root,
        stale_config,
        tmp_path / "stale-benchmark-receipts",
        runner=runner,
        config_path=operator.config_path,
    )

    payload = stale.design_cycle_payload(
        "Prove stale benchmark metadata is a repair gate.",
        run_external=False,
    )

    gate = next(item for item in payload["hard_gates"] if item["id"] == "benchmark_evidence_current")
    assert gate["passed"] is False
    assert payload["evidence_controls"]["benchmark"]["passed"] is False
    assert payload["evidence_controls"]["benchmark"]["release_eligible"] is False
    assert payload["evidence_controls"]["benchmark"]["deployment_authority"] == "none"


def test_design_cycle_stops_when_a_bound_public_claim_source_drifts(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    blades_path = operator.site_root / "data" / "blades.json"
    blades = json.loads(blades_path.read_text(encoding="utf-8"))
    blades["blades"][0]["public_evidence_basis"] = "Changed after the claim register was bound."
    _json(blades_path, blades)

    payload = operator.design_cycle_payload(
        "Prove a drifted public claim source stops the design cycle.",
        run_external=False,
    )

    gate = next(item for item in payload["hard_gates"] if item["id"] == "claims_evidence_current")
    assert gate["passed"] is False
    assert payload["evidence_controls"]["public_claims"]["passed"] is False
    assert payload["stop_control"]["missing_claim_evidence"] is True
    assert payload["state"] == "stopped"


def test_design_cycle_stops_when_a_bound_research_refresh_snapshot_drifts(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    snapshot = operator.repo_root / "docs" / "research" / "fixture-research-record.md"
    snapshot.write_text("# Drifted fixture\n", encoding="utf-8")

    payload = operator.design_cycle_payload(
        "Prove a drifted research source snapshot stops the design cycle.",
        run_external=False,
    )

    gate = next(item for item in payload["hard_gates"] if item["id"] == "research_source_refresh_current")
    assert gate["passed"] is False
    assert payload["evidence_controls"]["research_refresh"]["passed"] is False
    assert payload["release_eligible"] is False


def test_release_external_suite_requires_canonical_non_empty_composite_gate(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, config = operator_fixture
    weakened = json.loads(json.dumps(config))
    weakened["checks"]["external"] = []
    weakened_operator = WebsiteOperator(
        operator.repo_root,
        weakened,
        tmp_path / "weakened-receipts",
        runner=runner,
    )

    audit = weakened_operator.audit_payload(run_external=True)
    design = weakened_operator.design_cycle_payload(
        "Prove an empty external suite cannot authorise release.",
        run_external=True,
    )

    assert audit["state"] == "blocked"
    assert audit["summary"]["external_checks_run"] is False
    assert audit["external_checks"]["complete"] is False
    assert any(item["code"] == "external.release_gate_configuration" for item in audit["findings"])
    assert design["release_eligible"] is False
    assert design["hard_gates_pass"] is False


def test_composite_external_success_is_parseable_and_source_bound_in_audit_and_design(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture

    audit = operator.audit_payload(run_external=True)
    design = operator.design_cycle_payload(
        "Record exact successful composite visual evidence.",
        run_external=True,
    )

    assert audit["state"] == "pass"
    assert audit["summary"]["external_checks_run"] is True
    assert audit["external_checks"]["complete"] is True
    result = audit["external_checks"]["results"][0]
    assert result["id"] == "v28-composite-visual-release-gate"
    assert result["returncode"] == 0
    assert result["state"] == "pass"
    assert result["current_source_tree_sha256"] == audit["source_tree_sha256"]
    assert result["stdout_json"]["state"] == "pass"
    binding = result["composite_gate"]
    assert binding["release_id"] == "operator-test-final-release"
    assert binding["operator_source_tree_sha256"] == audit["source_tree_sha256"]
    assert binding["manifest"]["path"].endswith(".manifest.json")
    assert binding["visual_receipt"]["sha256"]
    assert binding["manual_pixel_review_receipt"]["sha256"]
    assert design["external_checks"] == design["audit"]["external_checks"]
    assert design["external_checks"]["complete"] is True
    assert design["release_eligible"] is True


def test_composite_external_nonzero_blocks_audit_and_design(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, runner, _ = operator_fixture
    runner.composite_returncode = 1

    audit = operator.audit_payload(run_external=True)
    design = operator.design_cycle_payload(
        "Prove a nonzero composite gate blocks release.",
        run_external=True,
    )

    assert audit["state"] == "blocked"
    assert audit["summary"]["external_checks_run"] is False
    result = audit["external_checks"]["results"][0]
    assert result["returncode"] == 1
    assert result["state"] == "failed"
    assert any(item["code"] == "external.v28-composite-visual-release-gate" for item in audit["findings"])
    assert design["release_eligible"] is False
    assert design["hard_gates_pass"] is False


def test_composite_zero_exit_with_malformed_result_fails_closed(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, runner, _ = operator_fixture
    runner.composite_stdout = {
        "state": "pass",
        "blockers": "not-a-number",
        "sourceTreeSha256": "b" * 64,
    }

    audit = operator.audit_payload(run_external=True)

    assert audit["state"] == "blocked"
    assert audit["summary"]["external_checks_run"] is False
    result = audit["external_checks"]["results"][0]
    assert result["returncode"] == 0
    assert result["state"] == "invalid-success-evidence"
    assert any(
        item["code"] == "external.v28-composite-visual-release-gate.evidence" for item in audit["findings"]
    )


@pytest.mark.parametrize(
    ("field", "value", "remove"),
    [
        ("blockers", "0", None),
        ("blockers", False, None),
        ("blockers", 0.5, None),
        ("axeViolations", False, None),
        ("axeIncompleteNodes", -1, None),
        ("output", "docs/audits/unexpected.json", None),
        ("sourceTreeSha256", "B" * 64, None),
        ("manualFailures", 0, "manualUnreviewed"),
    ],
)
def test_composite_zero_exit_requires_the_exact_strict_stdout_contract(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    field: str,
    value: object,
    remove: str | None,
) -> None:
    operator, runner, _ = operator_fixture
    payload: dict[str, object] = {
        "state": "pass",
        "blockers": 0,
        "axeViolations": 0,
        "axeIncompleteNodes": 3,
        "manualFailures": 0,
        "manualUnreviewed": 0,
        "sourceTreeSha256": "b" * 64,
        "output": None,
    }
    payload[field] = value
    if remove is not None:
        payload.pop(remove)
    runner.composite_stdout = payload

    audit = operator.audit_payload(run_external=True)

    assert audit["state"] == "blocked"
    assert audit["summary"]["external_checks_run"] is False
    assert audit["external_checks"]["complete"] is False
    result = audit["external_checks"]["results"][0]
    assert result["state"] == "invalid-success-evidence"


def test_composite_gate_config_rejects_noncanonical_command_shape(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, config = operator_fixture
    malformed = json.loads(json.dumps(config))
    malformed["checks"]["external"][0]["command"] = [
        "node",
        "{repo_root}/tools/aureon_visual_release_gate_v28.js",
        "--manifest",
        "docs/audits/latest.json",
    ]

    with pytest.raises(WebsiteOperatorError, match="canonical six-token command"):
        WebsiteOperator(
            operator.repo_root,
            malformed,
            tmp_path / "malformed-receipts",
            runner=runner,
        )


def test_composite_gate_config_rejects_mutable_latest_manifest_alias(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, config = operator_fixture
    mutable = json.loads(json.dumps(config))
    mutable["checks"]["external"][0]["command"][-1] = "{repo_root}/docs/audits/latest.manifest.json"

    with pytest.raises(WebsiteOperatorError, match="immutable, timestamped"):
        WebsiteOperator(
            operator.repo_root,
            mutable,
            tmp_path / "mutable-manifest-receipts",
            runner=runner,
        )


def test_design_cycle_warning_blocks_release_eligibility(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    index = operator.site_root / "index.html"
    index.write_text(
        _page().replace(
            "<title>Aureon Evidence Company</title>",
            f"<title>{'Aureon institutional evidence platform ' * 3}</title>",
        ),
        encoding="utf-8",
    )

    payload = operator.design_cycle_payload("Check warning closure.", run_external=True)

    assert payload["summary"]["warning_count"] >= 1
    assert payload["release_eligible"] is False
    gate = next(gate for gate in payload["hard_gates"] if gate["id"] == "open_audit_findings_closed")
    assert gate["passed"] is False


def test_noindex_route_skips_search_snippet_length_warnings(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    legacy = operator.site_root / "legacy" / "index.html"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        _page()
        .replace(
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            '  <meta name="robots" content="noindex, follow">',
        )
        .replace(
            "<title>Aureon Evidence Company</title>",
            f"<title>{'Legacy continuity route ' * 5}</title>",
        ),
        encoding="utf-8",
    )

    payload = operator.audit_payload(run_external=False)

    assert not any(
        item["code"] == "metadata.title_length" and item["path"] == "legacy/index.html"
        for item in payload["findings"]
    )


def test_design_cycle_enforces_no_progress_and_repeated_blocker_stops(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    first_path = operator.design_cycle(
        "Exercise no-progress stop control.",
        run_external=True,
    )
    second_path = operator.design_cycle(
        "Exercise no-progress stop control.",
        run_external=True,
        previous_cycle=first_path,
    )
    third = operator.design_cycle_payload(
        "Exercise no-progress stop control.",
        run_external=True,
        previous_cycle=second_path,
    )

    assert third["state"] == "stopped"
    assert third["hard_gates_pass"] is False
    assert "two_consecutive_no_progress_iterations" in third["stop_control"]["triggered"]
    assert third["stop_control"]["continuation_allowed"] is False

    blocker_path = operator.design_cycle(
        "Exercise repeated blocker stop control.",
        routes=["missing/index.html"],
        run_external=True,
    )
    repeated = operator.design_cycle_payload(
        "Exercise repeated blocker stop control.",
        routes=["missing/index.html"],
        run_external=True,
        previous_cycle=blocker_path,
    )
    assert repeated["state"] == "stopped"
    assert "repeated_identical_blocker" in repeated["stop_control"]["triggered"]


def test_design_cycle_blocks_missing_route_and_records_repair_gate(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    payload = operator.design_cycle_payload(
        "Audit the requested public website route.",
        routes=["missing/index.html"],
        run_external=True,
    )

    assert payload["state"] == "needs-repair"
    route_gate = next(gate for gate in payload["hard_gates"] if gate["id"] == "route_coverage")
    assert route_gate["passed"] is False
    assert route_gate["evidence"]["missing"] == ["missing/index.html"]
    assert payload["summary"]["ready_for_deployment"] is False


@pytest.mark.parametrize(
    ("route", "expected"),
    [
        ("/", "index.html"),
        ("/projects/", "projects/index.html"),
        ("research/", "research/index.html"),
        ("vision", "vision/index.html"),
        ("funding/investor-deck/index.html", "funding/investor-deck/index.html"),
    ],
)
def test_design_cycle_normalises_public_route_syntax(route: str, expected: str) -> None:
    assert _normalise_design_route(route) == expected


@pytest.mark.parametrize(
    "route",
    [
        "https://example.test/research/",
        "//example.test/research/",
        "/research/?campaign=one",
        "/research/#method",
        "/../private/",
    ],
)
def test_design_cycle_rejects_nonlocal_or_unsafe_public_route_syntax(route: str) -> None:
    with pytest.raises(WebsiteOperatorError):
        _normalise_design_route(route)


def test_build_is_bound_to_passing_current_tree(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    audit_path, design_path = _release_inputs(operator)
    (operator.site_root / "script.js").write_text('"use strict";\n// changed\n', encoding="utf-8")
    with pytest.raises(WebsiteOperatorError, match="changed after the audit"):
        operator.build_release(
            audit_path,
            tmp_path / "releases",
            design_cycle_receipt=design_path,
            human_visual_accepted=True,
            human_visual_accepted_by="Test visual reviewer",
        )


def test_build_requires_design_cycle_and_explicit_visual_acceptance(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    audit_path, design_path = _release_inputs(operator)

    with pytest.raises(WebsiteOperatorError, match="design-cycle receipt is required"):
        operator.build_release(audit_path, tmp_path / "missing-design")
    with pytest.raises(WebsiteOperatorError, match="human visual acceptance"):
        operator.build_release(
            audit_path,
            tmp_path / "missing-acceptance",
            design_cycle_receipt=design_path,
        )

    diagnostic_path = operator.design_cycle(
        "Diagnostic-only cycle.",
        run_external=False,
    )
    with pytest.raises(WebsiteOperatorError, match="not passing and release-eligible"):
        operator.build_release(
            audit_path,
            tmp_path / "diagnostic-design",
            design_cycle_receipt=diagnostic_path,
            human_visual_accepted=True,
            human_visual_accepted_by="Test visual reviewer",
        )


def test_build_revalidates_public_claim_register_after_design_cycle(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    audit_path, design_path = _release_inputs(operator)
    register_path = (
        operator.repo_root / "data" / "website_operator" / "public_claim_evidence_register.v1.json"
    )
    register = json.loads(register_path.read_text(encoding="utf-8"))
    register["generated_at"] = "2026-07-26T12:00:00Z"
    _json(register_path, register)

    with pytest.raises(WebsiteOperatorError, match="Public-claim evidence register changed"):
        operator.build_release(
            audit_path,
            tmp_path / "changed-claim-register-release",
            design_cycle_receipt=design_path,
            human_visual_accepted=True,
            human_visual_accepted_by="Test visual reviewer",
        )


def test_build_revalidates_investor_copy_policy_after_design_cycle(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    audit_path, design_path = _release_inputs(operator)
    policy_path = operator.repo_root / "data" / "website_operator" / "investor_copy_quality_policy.v1.json"
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    policy["refresh_by"] = (datetime.now(UTC) + timedelta(days=10)).isoformat()
    _json(policy_path, policy)

    with pytest.raises(WebsiteOperatorError, match="Investor-copy policy"):
        operator.build_release(
            audit_path,
            tmp_path / "changed-investor-copy-policy-release",
            design_cycle_receipt=design_path,
            human_visual_accepted=True,
            human_visual_accepted_by="Test visual reviewer",
        )


def test_release_revalidation_rejects_warning_only_investor_copy_binding(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator, _, _ = operator_fixture
    warning_receipt = _warning_only_investor_copy_audit(operator)
    monkeypatch.setattr(
        website_operator_module,
        "audit_investor_copy_quality_file",
        _fixed_investor_copy_audit(warning_receipt),
    )
    design_path = operator.design_cycle(
        "Prove warning-only investor copy cannot be promoted.",
        run_external=True,
    )
    design = json.loads(design_path.read_text(encoding="utf-8"))
    assert design["release_eligible"] is False
    assert design["evidence_controls"]["investor_copy"]["passed"] is False
    assert design["evidence_controls"]["investor_copy"]["binding"]["warning_count"] == 1

    stored_copy = design["evidence_controls"]["investor_copy"]
    stored_copy["passed"] = True
    stored_copy["state"] = "pass"
    stored_copy["receipt"]["passed"] = True
    stored_copy["receipt"]["state"] = "pass"
    stored_copy["binding"]["state"] = "pass"
    copy_gate = next(gate for gate in design["hard_gates"] if gate["id"] == "investor_copy_quality_current")
    copy_gate["passed"] = True
    copy_gate["evidence"] = operator._design_evidence_gate_summary(stored_copy)
    design["state"] = "verified-local-human-review-required"
    design["hard_gates_pass"] = True
    design["release_eligible"] = True
    design["summary"]["blocker_count"] = 0
    design["summary"]["warning_count"] = 0
    _json(design_path, design)

    with pytest.raises(WebsiteOperatorError, match="zero blockers and warnings"):
        operator._validate_design_cycle_for_release(
            design_path,
            design["source_tree_sha256"],
        )


def test_release_revalidation_requires_one_exact_investor_copy_hard_gate(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    design_path = operator.design_cycle(
        "Bind one exact investor-copy hard gate.",
        run_external=True,
    )
    baseline = json.loads(design_path.read_text(encoding="utf-8"))
    source_tree = baseline["source_tree_sha256"]
    copy_gate_index = next(
        index
        for index, gate in enumerate(baseline["hard_gates"])
        if gate["id"] == "investor_copy_quality_current"
    )
    variants: list[tuple[str, dict]] = []

    missing = json.loads(json.dumps(baseline))
    missing["hard_gates"].pop(copy_gate_index)
    variants.append(("missing", missing))

    renamed = json.loads(json.dumps(baseline))
    renamed["hard_gates"][copy_gate_index]["id"] = "investor_copy_quality_renamed"
    variants.append(("renamed", renamed))

    duplicate = json.loads(json.dumps(baseline))
    duplicate["hard_gates"].append(json.loads(json.dumps(duplicate["hard_gates"][copy_gate_index])))
    variants.append(("duplicate", duplicate))

    failed = json.loads(json.dumps(baseline))
    failed["hard_gates"][copy_gate_index]["passed"] = False
    variants.append(("failed", failed))

    inconsistent = json.loads(json.dumps(baseline))
    inconsistent["hard_gates"][copy_gate_index]["evidence"]["binding"]["policy_sha256"] = "0" * 64
    variants.append(("inconsistent", inconsistent))

    for label, payload in variants:
        candidate = tmp_path / f"investor-copy-hard-gate-{label}.json"
        _json(candidate, payload)
        with pytest.raises(
            WebsiteOperatorError,
            match="investor-copy quality hard gate",
        ):
            operator._validate_design_cycle_for_release(candidate, source_tree)


def test_build_revalidates_benchmark_config_after_design_cycle(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    audit_path, design_path = _release_inputs(operator)
    assert operator.config_path is not None
    config = json.loads(operator.config_path.read_text(encoding="utf-8"))
    config["design"]["competitor_sources"][0]["patterns"].append("Changed after benchmark evidence was bound")
    _json(operator.config_path, config)

    with pytest.raises(WebsiteOperatorError, match="Current benchmark evidence no longer passes"):
        operator.build_release(
            audit_path,
            tmp_path / "changed-benchmark-config-release",
            design_cycle_receipt=design_path,
            human_visual_accepted=True,
            human_visual_accepted_by="Test visual reviewer",
        )


def test_build_revalidates_composite_evidence_and_rejects_post_design_mutation(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    audit_path, design_path = _release_inputs(operator)
    manual = operator.repo_root / "docs" / "audits" / "AUREON_WEBSITE_MANUAL_PIXEL_REVIEW_TEST_V28.json"
    manual.write_text(
        manual.read_text(encoding="utf-8") + " \n",
        encoding="utf-8",
    )

    with pytest.raises(WebsiteOperatorError, match="revalidation failed"):
        operator.build_release(
            audit_path,
            tmp_path / "mutated-evidence-release",
            design_cycle_receipt=design_path,
            human_visual_accepted=True,
            human_visual_accepted_by="Test visual reviewer",
        )


def test_build_preserves_v3_dependency_closure_proof(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    package_path = _build_accepted_release(operator, tmp_path / "releases")
    package = json.loads(package_path.read_text(encoding="utf-8"))

    assert package["schema"] == "aureon.website-operator.package.v1"
    assert package["builder_schema"] == "aureon-homepl-audited-release-v3"
    assert package["package_validation"]["staging_dependency_closure_exact"] is True
    assert package["dependency_closure"]["state"] == "verified-complete"
    assert package["dependency_closure"]["missing_local_reference_count"] == 0
    assert package["dependency_manifest_sha256"]
    assert package["dependency_evidence_rows"] == 3
    assert ".htaccess" in package["paths"]
    assert package["design_cycle_receipt_sha256"]
    assert package["composite_visual_gate"]["returncode"] == 0
    assert package["composite_visual_gate"]["current_source_tree_sha256"] == package["source_tree_sha256"]
    assert package["composite_visual_gate"]["binding"]["release_id"] == "operator-test-final-release"
    assert package["composite_visual_gate"]["binding"]["manifest"]["sha256"]
    assert package["composite_visual_gate"]["binding"]["visual_receipt"]["sha256"]
    assert package["composite_visual_gate"]["binding"]["manual_pixel_review_receipt"]["sha256"]
    assert package["human_visual_acceptance"]["accepted"] is True
    assert package["human_visual_acceptance"]["accepted_by"] == "Test visual reviewer"
    assert package["human_visual_acceptance"]["source_tree_sha256"] == package["source_tree_sha256"]
    assert package["editorial_asset_provenance"]["package_required_files_exact"] is True
    assert package["editorial_asset_provenance"]["candidate_control_receipts_excluded"] is True


def test_package_validation_rejects_deleted_bound_composite_evidence(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    package_path = _build_accepted_release(operator, tmp_path / "releases")
    visual = operator.repo_root / "docs" / "audits" / "AUREON_WEBSITE_VISUAL_QA_TEST_V28.json"
    visual.unlink()

    with pytest.raises(WebsiteOperatorError, match="revalidation failed"):
        operator._validate_package_receipt(package_path)


def test_build_rejects_legacy_builder_receipt(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, _ = operator_fixture
    runner.receipt_mutator = lambda payload: payload.update({"schema": "aureon-homepl-narrow-release-v1"})

    with pytest.raises(WebsiteOperatorError, match="V3 dependency-closed"):
        _build_accepted_release(operator, tmp_path / "releases")


def test_build_rejects_unproven_transitive_dependency_closure(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, _ = operator_fixture

    def mark_dependency_missing(payload: dict) -> None:
        payload["dependency_closure"]["missing_local_reference_count"] = 1

    runner.receipt_mutator = mark_dependency_missing
    with pytest.raises(WebsiteOperatorError, match="exact transitive runtime dependency closure"):
        _build_accepted_release(operator, tmp_path / "releases")


def test_build_rejects_false_staging_closure_attestation(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, _ = operator_fixture

    def clear_staging_proof(payload: dict) -> None:
        payload["package_validation"]["staging_dependency_closure_exact"] = False

    runner.receipt_mutator = clear_staging_proof
    with pytest.raises(WebsiteOperatorError, match="staging_dependency_closure_exact"):
        _build_accepted_release(operator, tmp_path / "releases")


def test_build_rejects_unbound_dependency_manifest(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, _ = operator_fixture
    runner.receipt_mutator = lambda payload: payload.update({"dependency_manifest_sha256": "0" * 64})

    with pytest.raises(WebsiteOperatorError, match="Dependency manifest hash"):
        _build_accepted_release(operator, tmp_path / "releases")


def test_build_rejects_dependency_target_outside_package(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, runner, _ = operator_fixture

    def point_dependency_outside_package(payload: dict) -> None:
        dependency_path = Path(payload["dependency_manifest"])
        with dependency_path.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        rows[0]["Target"] = "missing.css"
        with dependency_path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=(
                    "Source",
                    "Reference",
                    "Disposition",
                    "Target",
                    "Fragment",
                    "FragmentState",
                ),
            )
            writer.writeheader()
            writer.writerows(rows)
        payload["dependency_manifest_sha256"] = _sha(dependency_path)

    runner.receipt_mutator = point_dependency_outside_package
    with pytest.raises(WebsiteOperatorError, match="absent from the package"):
        _build_accepted_release(operator, tmp_path / "releases")


def test_raw_v3_receipt_mutation_invalidates_operator_package_receipt(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    package_path = _build_accepted_release(operator, tmp_path / "releases")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    raw_path = Path(package["raw_receipt"])
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    raw["built_at"] = "2026-07-26T00:00:00+00:00"
    _json(raw_path, raw)

    with pytest.raises(WebsiteOperatorError, match="raw_receipt_sha256"):
        operator._validate_package_receipt(package_path)


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("raw_receipt", "missing-raw-receipt.json"),
        ("package", "substituted-package.zip"),
        ("manifest", "substituted-manifest.csv"),
        ("dependency_manifest", "substituted-dependencies.csv"),
        ("package_bytes", -1),
    ],
)
def test_outer_package_receipt_cannot_substitute_validated_builder_fields(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
    field: str,
    replacement: str | int,
) -> None:
    operator, _, _ = operator_fixture
    package_path = _build_accepted_release(operator, tmp_path / "releases")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package[field] = str((tmp_path / replacement).resolve()) if isinstance(replacement, str) else replacement
    _json(package_path, package)

    with pytest.raises(WebsiteOperatorError):
        operator._validate_package_receipt(package_path)


def test_operator_package_receipt_must_remain_a_single_link(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    package_path = _build_accepted_release(operator, tmp_path / "releases")
    alias = tmp_path / "package-receipt-alias.json"
    website_operator_module.os.link(package_path, alias)

    with pytest.raises(WebsiteOperatorError, match="exactly one hard link"):
        operator._validate_package_receipt(package_path)


@pytest.mark.parametrize(
    ("relative", "schema"),
    [
        (
            website_operator_module.DEFAULT_EDITORIAL_IMPORT_RECEIPT_NAME,
            "benign-public-data.v1",
        ),
        (
            "renamed-editorial-state.json",
            "aureon.design-editorial-asset-candidate-import.v1",
        ),
        (
            "renamed-candidate-state.json",
            "aureon.design-candidate.v1",
        ),
        (
            "renamed-work-order-state.json",
            "aureon.design-work-order.v4",
        ),
    ],
)
def test_build_rejects_named_or_renamed_candidate_control_receipts(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
    relative: str,
    schema: str,
) -> None:
    operator, runner, _ = operator_fixture
    _json(operator.site_root / relative, {"schema": schema})
    runner.release_paths.append(relative)

    with pytest.raises(WebsiteOperatorError, match="Candidate-control receipt"):
        _build_accepted_release(operator, tmp_path / "releases")


def test_editorial_package_binding_mutation_invalidates_operator_package_receipt(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    package_path = _build_accepted_release(operator, tmp_path / "releases")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package["editorial_asset_provenance"]["package_required_files_exact"] = False
    _json(package_path, package)

    with pytest.raises(WebsiteOperatorError, match="editorial provenance binding"):
        operator._validate_package_receipt(package_path)


def test_design_receipt_or_visual_acceptance_mutation_invalidates_package(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    package_path = _build_accepted_release(operator, tmp_path / "releases")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    design_path = Path(package["design_cycle_receipt"])
    design = json.loads(design_path.read_text(encoding="utf-8"))
    design["goal"] = "mutated after packaging"
    _json(design_path, design)

    with pytest.raises(WebsiteOperatorError, match="design-cycle receipt is missing or has changed"):
        operator._validate_package_receipt(package_path)

    package["design_cycle_receipt_sha256"] = _sha(design_path)
    package["human_visual_acceptance"]["accepted_by"] = ""
    _json(package_path, package)
    with pytest.raises(WebsiteOperatorError, match="human visual acceptance"):
        operator._validate_package_receipt(package_path)


def _build_and_backup(
    operator: WebsiteOperator,
    tmp_path: Path,
) -> tuple[Path, Path, Path]:
    audit_path, design_path = _release_inputs(operator)
    package_path = operator.build_release(
        audit_path,
        tmp_path / "releases",
        design_cycle_receipt=design_path,
        human_visual_accepted=True,
        human_visual_accepted_by="Test visual reviewer",
    )
    package = json.loads(package_path.read_text(encoding="utf-8"))
    backup_parent = operator.repo_root / "artifacts" / "homepl-backups"
    backup_parent.mkdir(parents=True, exist_ok=True)
    backup_root = backup_parent / "homepl-backup"
    live_receipt = _aligned_live_reconciliation(operator, "backup-live-source")
    preflight_path = operator.backup_preflight(
        backup_root,
        "homepl.test",
        "test-account@example.test",
        live_receipt,
    )
    for relative in package["paths"]:
        source = operator.site_root / relative
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    manifest = Path(f"{backup_root}-manifest.csv")
    _manifest(manifest, backup_root, package["paths"])
    root_mapping_path = _homepl_root_mapping_receipt(
        operator,
        backup_root,
        preflight_path,
    )
    transfer_path = _homepl_transfer_receipt(
        operator,
        backup_root,
        manifest,
        preflight_path,
        root_mapping_path,
    )
    backup_receipt = operator.verify_backup(
        backup_root,
        manifest,
        "homepl-ftps",
        package_receipt=package_path,
        preflight_receipt=preflight_path,
        transfer_receipt=transfer_path,
    )
    return audit_path, package_path, backup_receipt


def _homepl_transfer_receipt(
    operator: WebsiteOperator,
    backup_root: Path,
    manifest: Path,
    preflight_path: Path,
    root_mapping_path: Path,
) -> Path:
    rows = list(csv.DictReader(manifest.read_text(encoding="utf-8-sig").splitlines()))
    now = datetime.now(UTC)
    script = operator.repo_root / operator.config["deployment"]["backup_script"]
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    root_mapping = json.loads(root_mapping_path.read_text(encoding="utf-8"))
    transfer_path = Path(f"{backup_root}-transfer.json")
    _json(
        transfer_path,
        {
            "schema": "aureon.homepl-backup-transfer.v1",
            "state": "backup-complete",
            "method": "homepl-ftps",
            "source_assertion": "Authenticated Home.pl document-root download",
            "source_tool": "repo-read-only-ftps-script",
            "started_at": (now - timedelta(seconds=1)).isoformat(),
            "completed_at": now.isoformat(),
            "remote_root": "/",
            "ftp_host_id": preflight["ftp_host_id"],
            "ftp_host_sha256": preflight["ftp_host_sha256"],
            "ftp_account_sha256": preflight["ftp_account_sha256"],
            "ftp_binding_sha256": preflight["ftp_binding_sha256"],
            "backup_directory": str(backup_root),
            "manifest": str(manifest),
            "manifest_sha256": _sha(manifest),
            "file_count": len(rows),
            "total_bytes": sum(int(row["Bytes"]) for row in rows),
            "preflight_receipt": str(preflight_path),
            "preflight_receipt_sha256": _sha(preflight_path),
            "backup_script": str(script),
            "backup_script_sha256": _sha(script),
            "root_mapping_receipt": str(root_mapping_path),
            "root_mapping_receipt_sha256": _sha(root_mapping_path),
            "live_reconciliation_receipt": preflight["live_reconciliation_receipt"],
            "live_reconciliation_receipt_sha256": preflight["live_reconciliation_receipt_sha256"],
            "public_root_sha256": preflight["public_root_sha256"],
            "root_continuity_observed": True,
            "transfer_start_root_listing_sha256": root_mapping["listing_sha256"],
            "transfer_start_root_listing_entry_count": root_mapping["listing_entry_count"],
            "transfer_start_root_index_sha256": root_mapping["remote_root_index_sha256"],
            "transfer_start_root_index_bytes": root_mapping["remote_root_index_bytes"],
            "transfer_end_root_listing_sha256": root_mapping["listing_sha256"],
            "transfer_end_root_listing_entry_count": root_mapping["listing_entry_count"],
            "transfer_end_root_index_sha256": root_mapping["remote_root_index_sha256"],
            "transfer_end_root_index_bytes": root_mapping["remote_root_index_bytes"],
            "remote_operations": ["ListDirectory", "GetFileSize", "DownloadFile"],
            "remote_write_methods_used": False,
            "credentials_recorded": False,
        },
    )
    return transfer_path


def _homepl_root_mapping_receipt(
    operator: WebsiteOperator,
    backup_root: Path,
    preflight_path: Path,
) -> Path:
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    path = Path(f"{backup_root}-root-mapping.json")
    required = list(preflight["required_root_entries"])
    _json(
        path,
        {
            "schema": "aureon.homepl-root-mapping.v1",
            "state": "authenticated-served-root-mapped",
            "method": "homepl-ftps",
            "source_assertion": ("Authenticated Home.pl account mapped to current public root bytes"),
            "source_tool": "repo-read-only-ftps-script",
            "observed_at": datetime.now(UTC).isoformat(),
            "remote_root": "/",
            "ftp_host_id": preflight["ftp_host_id"],
            "ftp_host_sha256": preflight["ftp_host_sha256"],
            "ftp_account_sha256": preflight["ftp_account_sha256"],
            "ftp_binding_sha256": preflight["ftp_binding_sha256"],
            "preflight_receipt": str(preflight_path),
            "preflight_receipt_sha256": _sha(preflight_path),
            "backup_script": preflight["backup_script"],
            "backup_script_sha256": preflight["backup_script_sha256"],
            "live_reconciliation_receipt": preflight["live_reconciliation_receipt"],
            "live_reconciliation_receipt_sha256": preflight["live_reconciliation_receipt_sha256"],
            "live_reconciliation_observed_at": preflight["live_reconciliation_observed_at"],
            "public_root_url": preflight["public_root_url"],
            "public_root_sha256": preflight["public_root_sha256"],
            "public_root_bytes": preflight["public_root_bytes"],
            "remote_root_index_sha256": preflight["public_root_sha256"],
            "remote_root_index_bytes": preflight["public_root_bytes"],
            "listing_entry_count": len(required),
            "listing_sha256": "A" * 64,
            "required_root_entries": required,
            "required_root_entries_observed": True,
            "remote_operations": ["ListDirectory", "DownloadFile"],
            "remote_write_methods_used": False,
            "credentials_recorded": False,
        },
    )
    return path


def _minimal_homepl_backup_material(
    operator: WebsiteOperator,
    name: str = "homepl-minimal",
) -> tuple[Path, Path, Path, Path]:
    backup_parent = operator.repo_root / "artifacts" / "homepl-backups"
    backup_parent.mkdir(parents=True, exist_ok=True)
    backup_root = backup_parent / name
    live_receipt = _aligned_live_reconciliation(operator, f"{name}-live-source")
    preflight_path = operator.backup_preflight(
        backup_root,
        "homepl.test",
        "test-account@example.test",
        live_receipt,
    )
    paths = list(operator.config["deployment"]["required_backup_paths"])
    for relative in paths:
        source = operator.site_root / relative
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    manifest = Path(f"{backup_root}-manifest.csv")
    _manifest(manifest, backup_root, paths)
    root_mapping_path = _homepl_root_mapping_receipt(
        operator,
        backup_root,
        preflight_path,
    )
    transfer_path = _homepl_transfer_receipt(
        operator,
        backup_root,
        manifest,
        preflight_path,
        root_mapping_path,
    )
    return backup_root, manifest, preflight_path, transfer_path


def test_backup_preflight_binds_exact_read_only_artifact_paths_without_secret_values(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator, _, config = operator_fixture
    backup_parent = operator.repo_root / "artifacts" / "homepl-backups"
    backup_parent.mkdir(parents=True)
    output = backup_parent / "homepl-exact-root"
    sentinels = []
    for index, name in enumerate(config["deployment"]["credential_env_names"]):
        sentinel = f"must-not-be-recorded-{index}"
        sentinels.append(sentinel)
        monkeypatch.setenv(name, sentinel)

    live_receipt = _aligned_live_reconciliation(operator, "preflight-binding-live")
    account = "test-account@example.test"
    receipt_path = operator.backup_preflight(
        output,
        "homepl.test",
        account,
        live_receipt,
    )
    text = receipt_path.read_text(encoding="utf-8")
    receipt = json.loads(text)

    assert receipt["state"] == "ready-for-explicit-backup"
    assert receipt["remote_root"] == "/"
    assert receipt["backup_script_sha256"] == _sha(operator.repo_root / config["deployment"]["backup_script"])
    assert receipt["output_directory"] == str(output)
    assert receipt["manifest"] == f"{output}-manifest.csv"
    assert receipt["root_mapping_receipt"] == f"{output}-root-mapping.json"
    assert receipt["transfer_receipt"] == f"{output}-transfer.json"
    assert receipt["ftp_host_id"] == "homepl.test:21"
    assert receipt["ftp_host_sha256"]
    assert receipt["ftp_account_sha256"]
    assert receipt["ftp_binding_sha256"]
    assert receipt["output_within_backup_root"] is True
    assert receipt["read_only_contract"] == {
        "remote_methods": ["ListDirectory", "GetFileSize", "DownloadFile"],
        "remote_write_methods_permitted": False,
        "final_output_published_only_after_complete_download": True,
        "manifest_overwrite_permitted": False,
    }
    assert receipt["credentials"]["values_recorded"] is False
    assert account not in text
    assert all(sentinel not in text for sentinel in sentinels)


def test_backup_preflight_blocks_output_outside_homepl_artifact_boundary(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    (operator.repo_root / "artifacts" / "homepl-backups").mkdir(parents=True)
    live_receipt = _aligned_live_reconciliation(operator, "outside-preflight-live")

    receipt_path = operator.backup_preflight(
        tmp_path / "outside-homepl-backup",
        "homepl.test",
        "test-account@example.test",
        live_receipt,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert receipt["state"] == "blocked"
    assert receipt["output_within_backup_root"] is False


def test_backup_preflight_rejects_stale_public_root_observation(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    backup_parent = operator.repo_root / "artifacts" / "homepl-backups"
    backup_parent.mkdir(parents=True)
    live_receipt = _aligned_live_reconciliation(operator, "stale-preflight-live")
    payload = json.loads(live_receipt.read_text(encoding="utf-8"))
    payload["observed_at"] = (datetime.now(UTC) - timedelta(minutes=16)).isoformat()
    _json(live_receipt, payload)

    with pytest.raises(WebsiteOperatorError, match="too old"):
        operator.backup_preflight(
            backup_parent / "homepl-stale-live",
            "homepl.test",
            "test-account@example.test",
            live_receipt,
        )


def test_backup_preflight_maps_nested_required_paths_to_root_entries(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    operator.config["deployment"]["required_backup_paths"] = [
        "assets/app.css",
        "assets/runtime.js",
    ]
    backup_parent = operator.repo_root / "artifacts" / "homepl-backups"
    backup_parent.mkdir(parents=True)
    live_receipt = _aligned_live_reconciliation(operator, "nested-root-entry-live")
    receipt_path = operator.backup_preflight(
        backup_parent / "homepl-nested-root-entry",
        "homepl.test",
        "test-account@example.test",
        live_receipt,
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert receipt["required_root_entries"] == ["assets"]
    assert operator.config["deployment"]["required_backup_paths"] == [
        "assets/app.css",
        "assets/runtime.js",
    ]


def test_verify_backup_rejects_unmanifested_downloaded_file(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    backup_root, manifest, preflight, transfer = _minimal_homepl_backup_material(operator)
    (backup_root / "unmanifested.txt").write_text("unexpected", encoding="utf-8")

    with pytest.raises(WebsiteOperatorError, match="complete downloaded tree"):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            preflight_receipt=preflight,
            transfer_receipt=transfer,
        )


def test_verify_backup_rejects_hardlinked_downloaded_file(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    backup_parent = operator.repo_root / "artifacts" / "homepl-backups"
    backup_parent.mkdir(parents=True)
    backup_root = backup_parent / "homepl-hardlink"
    live_receipt = _aligned_live_reconciliation(operator, "hardlink-live")
    preflight = operator.backup_preflight(
        backup_root,
        "homepl.test",
        "test-account@example.test",
        live_receipt,
    )
    paths = list(operator.config["deployment"]["required_backup_paths"])
    for relative in paths:
        source = operator.site_root / relative
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    hardlink = backup_root / "index-alias.html"
    try:
        os.link(backup_root / "index.html", hardlink)
    except OSError as exc:
        pytest.skip(f"Hard links unavailable on this test host: {exc}")
    paths.append("index-alias.html")
    manifest = Path(f"{backup_root}-manifest.csv")
    _manifest(manifest, backup_root, paths)
    root_mapping = _homepl_root_mapping_receipt(operator, backup_root, preflight)
    transfer = _homepl_transfer_receipt(
        operator,
        backup_root,
        manifest,
        preflight,
        root_mapping,
    )

    with pytest.raises(WebsiteOperatorError, match="exactly one hard link"):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            preflight_receipt=preflight,
            transfer_receipt=transfer,
        )


def test_verify_backup_rejects_future_transfer_completion(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    backup_root, manifest, preflight, transfer = _minimal_homepl_backup_material(
        operator,
        "homepl-future",
    )
    payload = json.loads(transfer.read_text(encoding="utf-8"))
    future = datetime.now(UTC) + timedelta(hours=1)
    payload["started_at"] = (future - timedelta(seconds=1)).isoformat()
    payload["completed_at"] = future.isoformat()
    transfer.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(WebsiteOperatorError, match="completion time is in the future"):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            preflight_receipt=preflight,
            transfer_receipt=transfer,
        )


def test_verify_backup_rejects_transfer_rebound_to_another_account(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    backup_root, manifest, preflight, transfer = _minimal_homepl_backup_material(
        operator,
        "homepl-account-rebind",
    )
    payload = json.loads(transfer.read_text(encoding="utf-8"))
    payload["ftp_account_sha256"] = "F" * 64
    payload["ftp_binding_sha256"] = "E" * 64
    transfer.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(WebsiteOperatorError, match="exact read-only run"):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            preflight_receipt=preflight,
            transfer_receipt=transfer,
        )


def test_verify_backup_requires_durable_authenticated_root_mapping(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    backup_root, manifest, preflight, transfer = _minimal_homepl_backup_material(
        operator,
        "homepl-missing-root-map",
    )
    Path(f"{backup_root}-root-mapping.json").unlink()

    with pytest.raises(WebsiteOperatorError, match="root-mapping"):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            preflight_receipt=preflight,
            transfer_receipt=transfer,
        )


def test_verify_backup_rejects_root_mapping_not_matching_public_bytes(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    backup_root, manifest, preflight, transfer = _minimal_homepl_backup_material(
        operator,
        "homepl-wrong-public-root",
    )
    root_mapping = Path(f"{backup_root}-root-mapping.json")
    mapping = json.loads(root_mapping.read_text(encoding="utf-8"))
    mapping["remote_root_index_sha256"] = "F" * 64
    root_mapping.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    transfer_payload = json.loads(transfer.read_text(encoding="utf-8"))
    transfer_payload["root_mapping_receipt_sha256"] = _sha(root_mapping)
    transfer.write_text(json.dumps(transfer_payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(WebsiteOperatorError, match="authenticated served root"):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            preflight_receipt=preflight,
            transfer_receipt=transfer,
        )


def test_verify_backup_rejects_downloaded_root_changed_after_mapping(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    backup_root, manifest, preflight, _ = _minimal_homepl_backup_material(
        operator,
        "homepl-root-remap-replay",
    )
    (backup_root / "index.html").write_text(
        "<!doctype html><title>different authenticated root</title>\n",
        encoding="utf-8",
    )
    paths = list(operator.config["deployment"]["required_backup_paths"])
    _manifest(manifest, backup_root, paths)
    root_mapping = Path(f"{backup_root}-root-mapping.json")
    transfer = _homepl_transfer_receipt(
        operator,
        backup_root,
        manifest,
        preflight,
        root_mapping,
    )

    with pytest.raises(
        WebsiteOperatorError,
        match="Downloaded root index does not match",
    ):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            preflight_receipt=preflight,
            transfer_receipt=transfer,
        )


def test_verify_backup_rejects_transfer_root_continuity_mismatch(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    backup_root, manifest, preflight, transfer = _minimal_homepl_backup_material(
        operator,
        "homepl-continuity-mismatch",
    )
    payload = json.loads(transfer.read_text(encoding="utf-8"))
    payload["transfer_end_root_listing_sha256"] = "F" * 64
    _json(transfer, payload)

    with pytest.raises(WebsiteOperatorError, match="exact read-only run"):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            preflight_receipt=preflight,
            transfer_receipt=transfer,
        )


def test_verify_backup_rejects_duplicate_transfer_fields(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, _ = operator_fixture
    backup_root, manifest, preflight, transfer = _minimal_homepl_backup_material(
        operator,
        "homepl-duplicate-transfer-key",
    )
    text = transfer.read_text(encoding="utf-8")
    text = text.replace(
        '  "credentials_recorded": false',
        '  "credentials_recorded": true,\n  "credentials_recorded": false',
        1,
    )
    transfer.write_text(text, encoding="utf-8")

    with pytest.raises(WebsiteOperatorError, match="Duplicate JSON object field"):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            preflight_receipt=preflight,
            transfer_receipt=transfer,
        )


def test_verify_backup_rejects_script_changed_after_preflight(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
) -> None:
    operator, _, config = operator_fixture
    backup_parent = operator.repo_root / "artifacts" / "homepl-backups"
    backup_parent.mkdir(parents=True)
    backup_root = backup_parent / "homepl-script-drift"
    live_receipt = _aligned_live_reconciliation(operator, "script-drift-live")
    preflight = operator.backup_preflight(
        backup_root,
        "homepl.test",
        "test-account@example.test",
        live_receipt,
    )
    script = operator.repo_root / config["deployment"]["backup_script"]
    script.write_text("# changed after preflight\n", encoding="utf-8")
    paths = list(config["deployment"]["required_backup_paths"])
    for relative in paths:
        source = operator.site_root / relative
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    manifest = Path(f"{backup_root}-manifest.csv")
    _manifest(manifest, backup_root, paths)
    root_mapping = _homepl_root_mapping_receipt(operator, backup_root, preflight)
    transfer = _homepl_transfer_receipt(
        operator,
        backup_root,
        manifest,
        preflight,
        root_mapping,
    )

    with pytest.raises(WebsiteOperatorError, match="preflight field changed"):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            preflight_receipt=preflight,
            transfer_receipt=transfer,
        )


def test_verify_backup_revalidates_package_composite_evidence(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    package_path = _build_accepted_release(operator, tmp_path / "releases")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    backup_parent = operator.repo_root / "artifacts" / "homepl-backups"
    backup_parent.mkdir(parents=True, exist_ok=True)
    backup_root = backup_parent / "homepl-backup"
    live_receipt = _aligned_live_reconciliation(operator, "composite-backup-live")
    preflight_path = operator.backup_preflight(
        backup_root,
        "homepl.test",
        "test-account@example.test",
        live_receipt,
    )
    for relative in package["paths"]:
        source = operator.site_root / relative
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    manifest = Path(f"{backup_root}-manifest.csv")
    _manifest(manifest, backup_root, package["paths"])
    root_mapping_path = _homepl_root_mapping_receipt(
        operator,
        backup_root,
        preflight_path,
    )
    transfer_path = _homepl_transfer_receipt(
        operator,
        backup_root,
        manifest,
        preflight_path,
        root_mapping_path,
    )

    manual_reference = package["composite_visual_gate"]["binding"]["manual_pixel_review_receipt"]
    (operator.repo_root / manual_reference["path"]).unlink()

    with pytest.raises(
        WebsiteOperatorError,
        match="Composite visual gate revalidation failed|missing",
    ):
        operator.verify_backup(
            backup_root,
            manifest,
            "homepl-ftps",
            package_receipt=package_path,
            preflight_receipt=preflight_path,
            transfer_receipt=transfer_path,
        )


def test_owner_gate_and_deploy_preflight_are_hash_bound(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    audit_path, package_path, backup_path = _build_and_backup(operator, tmp_path)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    approval_path = tmp_path / "owner-approval.json"
    _json(
        approval_path,
        {
            "schema": "aureon.website-operator.owner-approval.v1",
            "decision": "approved",
            "scope": "static-website-release",
            "package_sha256": package["package_sha256"],
            "approved_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=2)).isoformat(),
            "approved_by": "Company owner",
        },
    )
    gate_path = operator.gate_deployment(
        audit_path,
        package_path,
        backup_path,
        approval_path,
    )
    deploy_path = operator.deploy(gate_path, package["package_sha256"], execute=False)
    deploy = json.loads(deploy_path.read_text(encoding="utf-8"))
    assert deploy["state"] == "deployment-preflight-passed"
    assert deploy["execute"] is False
    assert deploy["publication_complete"] is False
    with pytest.raises(WebsiteOperatorError, match="Exact package hash"):
        operator.deploy(gate_path, "0" * 64, execute=False)


def test_owner_gate_rejects_backup_not_bound_to_exact_package(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    audit_path, design_path = _release_inputs(operator)
    package_path = operator.build_release(
        audit_path,
        tmp_path / "releases",
        design_cycle_receipt=design_path,
        human_visual_accepted=True,
        human_visual_accepted_by="Test visual reviewer",
    )
    package = json.loads(package_path.read_text(encoding="utf-8"))
    backup_root, manifest, preflight, transfer = _minimal_homepl_backup_material(
        operator,
        "homepl-package-unbound",
    )
    backup_path = operator.verify_backup(
        backup_root,
        manifest,
        "homepl-ftps",
        preflight_receipt=preflight,
        transfer_receipt=transfer,
    )
    now = datetime.now(UTC)
    approval_path = tmp_path / "owner-approval-unbound.json"
    _json(
        approval_path,
        {
            "schema": "aureon.website-operator.owner-approval.v1",
            "decision": "approved",
            "scope": "static-website-release",
            "package_sha256": package["package_sha256"],
            "approved_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=2)).isoformat(),
            "approved_by": "Company owner",
        },
    )

    with pytest.raises(WebsiteOperatorError, match="not bound to this exact"):
        operator.gate_deployment(
            audit_path,
            package_path,
            backup_path,
            approval_path,
        )


def test_explicit_deploy_requires_runtime_credentials_and_live_readback(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator, runner, config = operator_fixture
    audit_path, package_path, backup_path = _build_and_backup(operator, tmp_path)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    approval_path = tmp_path / "owner-approval.json"
    _json(
        approval_path,
        {
            "schema": "aureon.website-operator.owner-approval.v1",
            "decision": "approved",
            "scope": "static-website-release",
            "package_sha256": package["package_sha256"],
            "approved_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=2)).isoformat(),
            "approved_by": "Company owner",
        },
    )
    gate_path = operator.gate_deployment(
        audit_path,
        package_path,
        backup_path,
        approval_path,
    )
    with pytest.raises(WebsiteOperatorError, match="credentials are missing"):
        operator.deploy(gate_path, package["package_sha256"], execute=True)
    for index, name in enumerate(config["deployment"]["credential_env_names"]):
        monkeypatch.setenv(name, f"runtime-secret-{index}")
    deploy_path = operator.deploy(gate_path, package["package_sha256"], execute=True)
    deploy_text = deploy_path.read_text(encoding="utf-8")
    deploy = json.loads(deploy_text)
    assert deploy["state"] == "deployed-and-verified-live"
    assert deploy["publication_complete"] is True
    assert deploy["readback_data_sha256"]
    assert all(f"runtime-secret-{index}" not in deploy_text for index in range(3))
    publish_call = next(call for call in runner.calls if call[0] == "fake-publish")
    readback_call = next(call for call in runner.calls if call[0] == "fake-readback")
    staged_package = Path(deploy["deployment_inputs"]["package"])
    staged_manifest = Path(deploy["deployment_inputs"]["manifest"])
    assert staged_package != Path(package["package"])
    assert staged_manifest != Path(package["manifest"])
    assert staged_package.parent.parent == operator.receipts_dir / "deploy-inputs"
    assert publish_call[1:3] == [str(staged_package), str(staged_manifest)]
    assert readback_call[2:4] == [str(staged_package), str(staged_manifest)]
    assert _sha(staged_package) == package["package_sha256"]
    assert _sha(staged_manifest) == package["manifest_sha256"]


def test_backup_mutation_invalidates_existing_gate(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    audit_path, package_path, backup_path = _build_and_backup(operator, tmp_path)
    package = json.loads(package_path.read_text(encoding="utf-8"))
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    now = datetime.now(UTC)
    approval_path = tmp_path / "owner-approval.json"
    _json(
        approval_path,
        {
            "schema": "aureon.website-operator.owner-approval.v1",
            "decision": "approved",
            "scope": "static-website-release",
            "package_sha256": package["package_sha256"],
            "approved_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=2)).isoformat(),
            "approved_by": "Company owner",
        },
    )
    gate_path = operator.gate_deployment(
        audit_path,
        package_path,
        backup_path,
        approval_path,
    )
    (Path(backup["backup_directory"]) / "index.html").write_text("changed", encoding="utf-8")
    with pytest.raises(WebsiteOperatorError, match="backup file has changed"):
        operator.deploy(gate_path, package["package_sha256"], execute=False)


def test_backup_rollback_or_extra_field_mutation_fails_revalidation(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    tmp_path: Path,
) -> None:
    operator, _, _ = operator_fixture
    _, _, backup_path = _build_and_backup(operator, tmp_path)
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    backup["rollback"]["protected_release_paths"] = []

    with pytest.raises(WebsiteOperatorError, match="rollback coverage"):
        operator._revalidate_backup_receipt(backup)

    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    backup["HOMEPL_FTPS_PASSWORD"] = "must-not-be-accepted"
    with pytest.raises(WebsiteOperatorError, match="fields are incomplete or unexpected"):
        operator._revalidate_backup_receipt(backup)


def test_backup_revalidation_rejects_transfer_beyond_mapping_window(
    operator_fixture: tuple[WebsiteOperator, FakeRunner, dict],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    operator, _, _ = operator_fixture
    backup_root, manifest, preflight, transfer = _minimal_homepl_backup_material(
        operator,
        "homepl-long-transfer",
    )
    backup_path = operator.verify_backup(
        backup_root,
        manifest,
        "homepl-ftps",
        preflight_receipt=preflight,
        transfer_receipt=transfer,
    )
    mapping = json.loads(Path(f"{backup_root}-root-mapping.json").read_text(encoding="utf-8"))
    mapping_observed = datetime.fromisoformat(str(mapping["observed_at"]).replace("Z", "+00:00")).astimezone(
        UTC
    )
    started = mapping_observed + timedelta(seconds=1)
    completed = mapping_observed + timedelta(minutes=16)
    transfer_payload = json.loads(transfer.read_text(encoding="utf-8"))
    transfer_payload["started_at"] = started.isoformat()
    transfer_payload["completed_at"] = completed.isoformat()
    _json(transfer, transfer_payload)
    backup = json.loads(backup_path.read_text(encoding="utf-8"))
    backup["observed_at"] = completed.isoformat()
    backup["generated_at"] = (completed + timedelta(seconds=1)).isoformat()
    backup["transfer_receipt_sha256"] = _sha(transfer)
    monkeypatch.setattr(
        website_operator_module,
        "_utc_now",
        lambda: completed + timedelta(minutes=1),
    )

    with pytest.raises(WebsiteOperatorError, match="transfer chronology"):
        operator._revalidate_backup_receipt(backup)
