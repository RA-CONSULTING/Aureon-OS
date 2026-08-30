"""Proof that staged candidate visual review is source-bound and non-authoritative."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aureon.operator import design_candidate_source_closure as source_closure
from aureon.operator.design_candidate_control import (
    create_design_work_order,
    stage_design_candidate,
    validate_design_candidate,
    write_design_candidate_receipt,
    write_design_work_order,
)
from aureon.operator.design_candidate_visual_review import (
    AUTHORITY,
    CANONICAL_INTERACTIONS,
    CANONICAL_ROUTES,
    CANONICAL_VIEWPORTS,
    FINAL_ENGINES,
    HUMAN_ACCEPTANCE_SCHEMA,
    MANUAL_REVIEW_SCHEMA,
    SCREENSHOT_SCOPE,
    VISUAL_CAPTURE_SCHEMA,
    _canonical_json_sha256,
    _editorial_surface_checks,
    _incomplete_nodes,
    _qa_snapshot,
    validate_candidate_visual_review,
    write_candidate_visual_review,
)
from aureon.operator.design_learning_ledger import (
    AUTHORITY as LEARNING_AUTHORITY,
)
from aureon.operator.design_learning_ledger import (
    LEARNING_MANIFEST_SCHEMA,
    LEARNING_RECORD_SCHEMA,
    DesignLearningLedgerError,
    validate_design_learning_record,
    write_design_learning_record,
)
from aureon.operator.live_surface_reconciliation import (
    reconcile_live_surface,
    write_live_surface_reconciliation,
)

NOW = datetime(2026, 7, 28, 12, 5, tzinfo=UTC)
VISUAL_AT = "2026-07-28T12:00:00.000Z"
MANUAL_AT = "2026-07-28T12:01:00.000Z"
ACCEPTED_AT = "2026-07-28T12:02:00.000Z"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _copy_executable_source_closure(destination_root: Path) -> None:
    executable_closure = source_closure.build_source_closure(REPO_ROOT)
    for row in executable_closure["files"]:
        relative = Path(str(row["path"]))
        destination = destination_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO_ROOT / relative, destination)


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _empty_editorial_audit() -> dict:
    expected: list[dict] = []
    return {
        "pass": True,
        "expectedSurfaces": expected,
        "expectedSurfacesSha256": _canonical_json_sha256(expected),
        "observedSurfaces": [],
        "expectedSurfaceCount": 0,
        "observedSurfaceCount": 0,
        "surfaceCount": 0,
        "duplicateSurfaceIds": [],
        "failures": [],
    }


def _fake_repo(root: Path) -> None:
    _write(root / "pyproject.toml", "[tool.pytest.ini_options]\n")
    (root / "aureon" / "operator").mkdir(parents=True)
    _write(root / "aureon" / "operator" / "website_operator.defaults.json", '{"policy":"test"}\n')
    index = (
        "<!doctype html><title>Aureon</title><p>Aureon evidence fixture. "
        "This fixture is not evidence of customer adoption or independent validation.</p>\n"
    )
    _write(root / "website" / "index.html", index)
    _write(root / "website" / "styles.css", "body { color: #123456; }\n")
    register = {
        "schema": "aureon.public-claim-evidence-register.v1",
        "generated_at": "2026-07-28T10:00:00Z",
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
                "id": "fixture-positioning",
                "title": "Fixture positioning",
                "claim": "Aureon evidence fixture.",
                "state": "company-authored",
                "boundary": "This fixture is not evidence of customer adoption or independent validation.",
                "permitted_wording": ["Aureon evidence fixture."],
                "prohibited_inferences": ["customer adoption", "independent validation"],
                "expires_on": "2027-07-28",
                "source": {
                    "path": "website/index.html",
                    "sha256": _sha(root / "website" / "index.html"),
                    "locator": "fixture:index",
                    "evidence_texts": ["Aureon", "fixture"],
                    "boundary_text": "This fixture is not evidence of customer adoption or independent validation.",
                },
                "public_routes": ["/"],
            }
        ],
    }
    _write_json(root / "data" / "website_operator" / "public_claim_evidence_register.v1.json", register)
    _copy_executable_source_closure(root)


class _Response:
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


def _aligned_reconciliation(root: Path, run_id: str) -> Path:
    source = (root / "website" / "index.html").read_bytes()
    receipt = reconcile_live_surface(
        repo_root=root,
        site_root=root / "website",
        base_url="https://example.test/",
        routes=["index.html"],
        now=NOW,
        opener=lambda request, timeout: _Response(source, request.full_url),
    )
    return write_live_surface_reconciliation(
        receipt,
        root / "artifacts" / "website-operator" / f"{run_id}-alignment.json",
        repo_root=root,
    )


def _candidate(root: Path) -> tuple[Path, Path]:
    order = create_design_work_order(
        goal="Test an evidence-bound staged visual review.",
        allowed_paths=["styles.css"],
        routes=["/"],
        reconciliation_receipt=_aligned_reconciliation(root, "visual-review-candidate"),
        run_id="visual-review-candidate",
        repo_root=root,
        now=NOW,
    )
    order_path = write_design_work_order(
        order,
        root / "artifacts" / "website-candidates" / "work-orders" / "visual-review-candidate.v4.json",
        repo_root=root,
    )
    stage_design_candidate(order_path, repo_root=root)
    candidate_root = root / order["candidate_layout"]["root"]
    _write(candidate_root / "website" / "styles.css", "body { color: #234567; }\n")
    receipt = validate_design_candidate(
        order_path,
        claim_impacts=[
            {
                "path": "styles.css",
                "classification": "no-material-claim-change",
                "rationale": "The bounded visual styling change does not alter public positioning wording.",
            }
        ],
        repo_root=root,
        now=NOW,
    )
    assert receipt["passed"] is True
    candidate_receipt = write_design_candidate_receipt(
        receipt,
        candidate_root / "candidate.v1.json",
        repo_root=root,
    )
    return candidate_root, candidate_receipt


def _visual_fixture(root: Path, candidate_root: Path, candidate_receipt: Path) -> tuple[Path, Path, Path]:
    website = candidate_root / "website"
    snapshot = _qa_snapshot(website)
    visual_root = candidate_root / "visual-review"
    visual_path = visual_root / "AUREON_WEBSITE_VISUAL_QA_20260728T120000Z_V28.json"
    screenshot_dir = visual_path.with_suffix("")
    engines = []
    for engine_name in FINAL_ENGINES:
        screenshots = []
        for viewport, route_name in SCREENSHOT_SCOPE:
            filename = f"{engine_name}-{viewport}-{route_name}.png"
            target = screenshot_dir / filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(f"{engine_name}:{viewport}:{route_name}".encode())
            screenshots.append(
                {
                    "engine": engine_name,
                    "viewport": viewport,
                    "routeName": route_name,
                    "filename": filename,
                    "bytes": target.stat().st_size,
                    "sha256": _sha(target).lower(),
                    "sourceTreeSha256": snapshot["sha256"],
                }
            )
        accessibility = []
        for route_name, route in CANONICAL_ROUTES:
            incomplete = (
                [
                    {
                        "id": "color-contrast",
                        "impact": "serious",
                        "nodeCount": 1,
                        "nodes": [
                            {
                                "target": [f".{engine_name}-fixture-title"],
                                "failureSummary": "Rendered pixel inspection required.",
                            }
                        ],
                    }
                ]
                if route_name == "home"
                else []
            )
            accessibility.append(
                {
                    "routeName": route_name,
                    "route": route,
                    "contrast": {"pass": True},
                    "axe": {
                        "status": "RAN",
                        "violations": [],
                        "incomplete": incomplete,
                        "completeNodeEvidence": True,
                    },
                    "keyboard": {"pass": True},
                    "reflow200": {"pass": True},
                    "errors": [],
                    "warnings": [],
                    "resourceFailures": [],
                    "pass": not incomplete,
                }
            )
        engines.append(
            {
                "engine": engine_name,
                "status": "FAIL",
                "pass": False,
                "diagnostics": {"warnings": [], "errors": []},
                "routes": [
                    {
                        "name": route_name,
                        "route": route,
                        "mode": viewport,
                        "editorialSurfaceAudit": _empty_editorial_audit(),
                        "pass": True,
                        "errors": [],
                        "warnings": [],
                        "resourceFailures": [],
                    }
                    for route_name, route in CANONICAL_ROUTES
                    for viewport in CANONICAL_VIEWPORTS
                ],
                "interactions": [
                    {
                        "name": name,
                        "pass": True,
                        "errors": [],
                        "warnings": [],
                        "resourceFailures": [],
                    }
                    for name in CANONICAL_INTERACTIONS
                ],
                "accessibility": accessibility,
                "performance": [
                    {
                        "routeName": route_name,
                        "route": route,
                        "renderingGeometry": {
                            "status": "NOT_APPLICABLE",
                            "pass": True,
                            "failureReasons": [],
                        },
                        "pass": True,
                        "errors": [],
                        "warnings": [],
                        "resourceFailures": [],
                    }
                    for route_name, route in CANONICAL_ROUTES
                ],
                "motion": {"status": "RAN", "pass": True},
                "screenshots": screenshots,
            }
        )
    visual = {
        "schema": "aureon-website-visual-qa-v28.3",
        "generatedAt": VISUAL_AT,
        "status": "FAIL",
        "selfHosted": True,
        "capabilities": {"axe": {"status": "INSTALLED"}},
        "engineCoverage": {
            "requested": list(FINAL_ENGINES),
            "selectionExplicit": False,
            "mode": "requested-browser-engine-matrix",
            "unsupported": [],
        },
        "selectedRoutes": [{"name": name, "route": route} for name, route in CANONICAL_ROUTES],
        "selectedViewports": [{"name": name} for name in CANONICAL_VIEWPORTS],
        "editorialSurfaceExpectations": [],
        "editorialSurfaceExpectationsSha256": "",
        "sourceBinding": {
            "before": snapshot,
            "after": snapshot,
            "stable": True,
            "servedFromHashedSource": True,
        },
        "screenshotIntegrity": {"count": len(FINAL_ENGINES) * len(SCREENSHOT_SCOPE), "pass": True},
        "diagnostics": {"warnings": [], "errors": []},
        "engines": engines,
    }
    _write_json(visual_path, visual)
    candidate_relative = candidate_receipt.relative_to(root).as_posix()
    visual_relative = visual_path.relative_to(root).as_posix()
    capture_path = visual_root / "AUREON_CANDIDATE_VISUAL_CAPTURE_20260728T120000Z.json"
    capture = {
        "schema": VISUAL_CAPTURE_SCHEMA,
        "generatedAt": VISUAL_AT,
        "state": "captured-local-fail",
        "candidateReceipt": {"path": candidate_relative, "sha256": _sha(candidate_receipt)},
        "candidate": {
            "root": candidate_root.relative_to(root).as_posix(),
            "websitePath": website.relative_to(root).as_posix(),
            "controlTreeSha256": json.loads(candidate_receipt.read_text(encoding="utf-8"))["candidate"][
                "tree_sha256"
            ],
        },
        "visualReceipt": {
            "path": visual_relative,
            "sha256": _sha(visual_path),
            "status": "FAIL",
            "sourceTreeSha256": snapshot["sha256"],
            "screenshotCount": len(FINAL_ENGINES) * len(SCREENSHOT_SCOPE),
            "screenshotsStable": True,
        },
        "authority": AUTHORITY,
    }
    _write_json(capture_path, capture)
    visual_payload = json.loads(visual_path.read_text(encoding="utf-8"))
    nodes = _incomplete_nodes(visual_payload)
    manual_path = visual_root / "AUREON_CANDIDATE_MANUAL_PIXEL_REVIEW_20260728T120100Z.json"
    reviews = [
        {
            "nodeId": node["nodeId"],
            "engine": node["engine"],
            "routeName": node["routeName"],
            "route": node["route"],
            "ruleId": node["ruleId"],
            "impact": node["impact"],
            "target": node["target"],
            "failureSummary": node["failureSummary"],
            "status": "verified-pass",
            "reviewedAt": MANUAL_AT,
            "notes": "Named reviewer inspected the rendered pixels and verified adequate contrast.",
        }
        for node in nodes
    ]
    manual = {
        "schema": MANUAL_REVIEW_SCHEMA,
        "generatedAt": MANUAL_AT,
        "candidateReceipt": {"path": candidate_relative, "sha256": _sha(candidate_receipt)},
        "candidate": capture["candidate"],
        "reviewer": {"name": "Fixture Pixel Reviewer", "method": "manual-pixel-inspection"},
        "visualReceipt": {
            "path": visual_relative,
            "sha256": _sha(visual_path),
            "generatedAt": VISUAL_AT,
            "sourceTreeSha256": snapshot["sha256"],
        },
        "summary": {
            "expectedIncompleteNodes": len(reviews),
            "reviewedNodes": len(reviews),
            "verifiedPassNodes": len(reviews),
            "notApplicableNodes": 0,
            "failedNodes": 0,
            "unreviewedNodes": 0,
        },
        "reviews": reviews,
        "authority": AUTHORITY,
    }
    _write_json(manual_path, manual)
    acceptance_path = visual_root / "AUREON_CANDIDATE_HUMAN_VISUAL_ACCEPTANCE_20260728T120200Z.json"
    acceptance = {
        "schema": HUMAN_ACCEPTANCE_SCHEMA,
        "decision": "accepted",
        "acceptedAt": ACCEPTED_AT,
        "reviewer": {"name": "Fixture Visual Reviewer", "method": "manual-visual-review"},
        "candidateReceipt": {"path": candidate_relative, "sha256": _sha(candidate_receipt)},
        "visualReceipt": {"path": visual_relative, "sha256": _sha(visual_path)},
        "manualPixelReview": {"path": manual_path.relative_to(root).as_posix(), "sha256": _sha(manual_path)},
        "note": "Reviewed full desktop and mobile evidence for this exact staged candidate.",
        "authority": AUTHORITY,
    }
    _write_json(acceptance_path, acceptance)
    return capture_path, manual_path, acceptance_path


def _check(receipt: dict, identifier: str) -> dict:
    return next(item for item in receipt["checks"] if item["id"] == identifier)


def _editorial_candidate(expected: list[dict], *, required: bool) -> dict:
    expected_hash = _canonical_json_sha256(expected) if required else ""
    return {
        "checks": [
            {
                "id": "trusted-editorial-surface-replay",
                "passed": True,
                "message": "Fixture trusted editorial replay.",
                "evidence": {
                    "required": required,
                    "expected_surfaces": expected,
                    "expected_surfaces_sha256": expected_hash,
                },
            }
        ]
    }


def _observed_editorial_surface(expected: dict) -> dict:
    variants = {item["role"]: item for item in expected["variants"]}
    small = variants["small"]
    large = variants["large"]
    small_path = f"/{small['path'].removeprefix('website/')}"
    large_path = f"/{large['path'].removeprefix('website/')}"
    return {
        "surfaceId": expected["surface_id"],
        "visible": True,
        "pictureCount": 1,
        "imageCount": 1,
        "anchorCount": 1,
        "figcaptionCount": 1,
        "nestedSurfaceCount": 0,
        "publicPostUrl": expected["public_post_url"],
        "captionMatches": True,
        "captionVisible": True,
        "creditMatchCount": 1,
        "creditVisible": True,
        "image": {
            "srcPath": large_path,
            "currentSrcPath": small_path,
            "altMatches": True,
            "complete": True,
            "naturalWidth": small["width"],
            "naturalHeight": small["height"],
            "declaredWidth": large["width"],
            "declaredHeight": large["height"],
            "renderedWidth": 480,
            "renderedHeight": 270,
            "visible": True,
        },
        "sourcePaths": [small_path],
        "failures": [],
        "pass": True,
    }


def _editorial_visual(expected: list[dict], *, candidate_hash: str) -> dict:
    engines = []
    for engine_name in FINAL_ENGINES:
        routes = []
        for route_name, route in CANONICAL_ROUTES:
            route_expected = [item for item in expected if item["route_scope"] == route]
            observed = [_observed_editorial_surface(item) for item in route_expected]
            for viewport in CANONICAL_VIEWPORTS:
                routes.append(
                    {
                        "name": route_name,
                        "route": route,
                        "mode": viewport,
                        "editorialSurfaceAudit": {
                            "pass": True,
                            "expectedSurfaces": route_expected,
                            "expectedSurfacesSha256": _canonical_json_sha256(route_expected),
                            "observedSurfaces": observed,
                            "expectedSurfaceCount": len(route_expected),
                            "observedSurfaceCount": len(observed),
                            "surfaceCount": len(observed),
                            "duplicateSurfaceIds": [],
                            "failures": [],
                        },
                    }
                )
        engines.append({"engine": engine_name, "routes": routes})
    return {
        "editorialSurfaceExpectations": expected,
        "editorialSurfaceExpectationsSha256": candidate_hash,
        "engines": engines,
    }


def test_editorial_visual_binding_requires_exact_candidate_and_browser_replay() -> None:
    expected = [
        {
            "asset_id": "editorial-fixture",
            "route_scope": "/",
            "destination_path": "index.html",
            "surface_id": "home-editorial-fixture",
            "public_post_url": "https://aureonresearch.substack.com/p/editorial-fixture",
            "variants": [
                {
                    "role": "large",
                    "path": "website/assets/images/research/substack/editorial-fixture-large.webp",
                    "sha256": "A" * 64,
                    "media_type": "image/webp",
                    "width": 1200,
                    "height": 675,
                },
                {
                    "role": "small",
                    "path": "website/assets/images/research/substack/editorial-fixture-small.webp",
                    "sha256": "B" * 64,
                    "media_type": "image/webp",
                    "width": 600,
                    "height": 338,
                },
            ],
            "alt": "Fixture alt text.",
            "caption": "Fixture caption.",
            "credit": "Fixture credit.",
            "route_asset_capsule_sha256": "C" * 64,
            "expected_binding_sha256": "D" * 64,
            "observation_sha256": "E" * 64,
            "surface_binding_sha256": "F" * 64,
        }
    ]
    candidate = _editorial_candidate(expected, required=True)
    expected_hash = candidate["checks"][0]["evidence"]["expected_surfaces_sha256"]
    visual = _editorial_visual(expected, candidate_hash=expected_hash)

    bound = _editorial_surface_checks(candidate, visual)

    assert bound["passed"] is True
    assert bound["evidence"]["expected_surface_count"] == 1
    assert bound["evidence"]["audit_failures"] == []

    altered = json.loads(json.dumps(visual))
    altered["engines"][0]["routes"][0]["editorialSurfaceAudit"]["observedSurfaces"][0]["image"][
        "currentSrcPath"
    ] += "?token=secret"
    rejected = _editorial_surface_checks(candidate, altered)
    assert rejected["passed"] is False
    assert rejected["evidence"]["audit_failures"] == ["chromium:reflow:/"]

    duplicate = json.loads(json.dumps(candidate))
    duplicate["checks"].append(duplicate["checks"][0])
    assert _editorial_surface_checks(duplicate, visual)["passed"] is False

    leaked = json.loads(json.dumps(visual))
    leaked["engines"][0]["routes"][0]["editorialSurfaceAudit"]["rawUrl"] = (
        "https://example.invalid/art.webp?token=secret"
    )
    assert _editorial_surface_checks(candidate, leaked)["passed"] is False


def test_editorial_visual_binding_requires_empty_expectations_for_text_only_candidate() -> None:
    candidate = _editorial_candidate([], required=False)
    visual = _editorial_visual([], candidate_hash="")
    assert _editorial_surface_checks(candidate, visual)["passed"] is True

    visual["editorialSurfaceExpectations"] = [{"surface_id": "injected"}]
    assert _editorial_surface_checks(candidate, visual)["passed"] is False


def test_candidate_visual_review_binds_both_tree_algorithms_and_human_evidence(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    candidate_root, candidate_receipt = _candidate(tmp_path)
    capture, manual, acceptance = _visual_fixture(tmp_path, candidate_root, candidate_receipt)

    receipt = validate_candidate_visual_review(
        candidate_receipt,
        capture,
        manual,
        acceptance,
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["passed"] is True
    assert receipt["state"] == "prepromotion-visual-review-passed"
    assert receipt["release_eligible"] is False
    assert receipt["package_authority"] == "none"
    assert receipt["deployment_authority"] == "none"
    assert receipt["canonical_promotion_authority"] == "owner-controlled"
    assert receipt["candidate"]["control_tree_sha256"].isupper()
    assert receipt["candidate"]["visual_qa_tree_sha256"].islower()


def test_candidate_visual_review_fails_closed_for_changed_pixels_or_unreviewed_nodes(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    candidate_root, candidate_receipt = _candidate(tmp_path)
    capture, manual, acceptance = _visual_fixture(tmp_path, candidate_root, candidate_receipt)
    visual = json.loads(
        (candidate_root / "visual-review" / "AUREON_WEBSITE_VISUAL_QA_20260728T120000Z_V28.json").read_text(
            encoding="utf-8"
        )
    )
    first_screenshot = visual["engines"][0]["screenshots"][0]["filename"]
    (
        candidate_root / "visual-review" / "AUREON_WEBSITE_VISUAL_QA_20260728T120000Z_V28" / first_screenshot
    ).write_bytes(b"altered")

    altered = validate_candidate_visual_review(
        candidate_receipt,
        capture,
        manual,
        acceptance,
        repo_root=tmp_path,
        now=NOW,
    )
    assert altered["passed"] is False
    assert _check(altered, "visual-automated-gates")["passed"] is False

    _fake_repo(tmp_path / "second")
    candidate_root, candidate_receipt = _candidate(tmp_path / "second")
    capture, manual, acceptance = _visual_fixture(tmp_path / "second", candidate_root, candidate_receipt)
    manual_payload = json.loads(manual.read_text(encoding="utf-8"))
    manual_payload["reviews"][0]["status"] = "unreviewed"
    manual_payload["reviews"][0]["reviewedAt"] = None
    manual_payload["reviews"][0]["notes"] = ""
    manual_payload["summary"]["reviewedNodes"] -= 1
    manual_payload["summary"]["verifiedPassNodes"] -= 1
    manual_payload["summary"]["unreviewedNodes"] = 1
    _write_json(manual, manual_payload)
    acceptance_payload = json.loads(acceptance.read_text(encoding="utf-8"))
    acceptance_payload["manualPixelReview"]["sha256"] = _sha(manual)
    _write_json(acceptance, acceptance_payload)

    unreviewed = validate_candidate_visual_review(
        candidate_receipt,
        capture,
        manual,
        acceptance,
        repo_root=tmp_path / "second",
        now=NOW,
    )
    assert unreviewed["passed"] is False
    assert _check(unreviewed, "manual-pixel-disposition")["passed"] is False


def test_candidate_visual_review_requires_investor_desktop_screenshot_and_rendering_geometry(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    candidate_root, candidate_receipt = _candidate(tmp_path)
    capture, manual, acceptance = _visual_fixture(tmp_path, candidate_root, candidate_receipt)
    visual_path = candidate_root / "visual-review" / "AUREON_WEBSITE_VISUAL_QA_20260728T120000Z_V28.json"
    visual = json.loads(visual_path.read_text(encoding="utf-8"))
    for engine in visual["engines"]:
        engine["screenshots"] = [
            item
            for item in engine["screenshots"]
            if not (item["viewport"] == "desktop" and item["routeName"] == "investor")
        ]
    visual["screenshotIntegrity"]["count"] = sum(len(engine["screenshots"]) for engine in visual["engines"])
    _write_json(visual_path, visual)
    visual_sha = _sha(visual_path)
    capture_payload = json.loads(capture.read_text(encoding="utf-8"))
    capture_payload["visualReceipt"]["sha256"] = visual_sha
    capture_payload["visualReceipt"]["screenshotCount"] = visual["screenshotIntegrity"]["count"]
    _write_json(capture, capture_payload)
    manual_payload = json.loads(manual.read_text(encoding="utf-8"))
    manual_payload["visualReceipt"]["sha256"] = visual_sha
    _write_json(manual, manual_payload)
    acceptance_payload = json.loads(acceptance.read_text(encoding="utf-8"))
    acceptance_payload["visualReceipt"]["sha256"] = visual_sha
    acceptance_payload["manualPixelReview"]["sha256"] = _sha(manual)
    _write_json(acceptance, acceptance_payload)

    missing_investor = validate_candidate_visual_review(
        candidate_receipt,
        capture,
        manual,
        acceptance,
        repo_root=tmp_path,
        now=NOW,
    )
    assert missing_investor["passed"] is False
    assert _check(missing_investor, "visual-automated-gates")["passed"] is False

    _fake_repo(tmp_path / "geometry")
    candidate_root, candidate_receipt = _candidate(tmp_path / "geometry")
    capture, manual, acceptance = _visual_fixture(tmp_path / "geometry", candidate_root, candidate_receipt)
    visual_path = candidate_root / "visual-review" / "AUREON_WEBSITE_VISUAL_QA_20260728T120000Z_V28.json"
    visual = json.loads(visual_path.read_text(encoding="utf-8"))
    visual["engines"][0]["performance"][0]["renderingGeometry"] = {
        "status": "RAN",
        "pass": False,
        "failureReasons": ["scroll-height:24>2"],
    }
    visual["engines"][0]["performance"][0]["pass"] = False
    _write_json(visual_path, visual)
    visual_sha = _sha(visual_path)
    capture_payload = json.loads(capture.read_text(encoding="utf-8"))
    capture_payload["visualReceipt"]["sha256"] = visual_sha
    _write_json(capture, capture_payload)
    manual_payload = json.loads(manual.read_text(encoding="utf-8"))
    manual_payload["visualReceipt"]["sha256"] = visual_sha
    _write_json(manual, manual_payload)
    acceptance_payload = json.loads(acceptance.read_text(encoding="utf-8"))
    acceptance_payload["visualReceipt"]["sha256"] = visual_sha
    acceptance_payload["manualPixelReview"]["sha256"] = _sha(manual)
    _write_json(acceptance, acceptance_payload)

    geometry_failure = validate_candidate_visual_review(
        candidate_receipt,
        capture,
        manual,
        acceptance,
        repo_root=tmp_path / "geometry",
        now=NOW,
    )
    assert geometry_failure["passed"] is False
    assert _check(geometry_failure, "visual-automated-gates")["passed"] is False


def test_candidate_visual_review_rejects_candidate_mutation_after_capture(tmp_path: Path) -> None:
    _fake_repo(tmp_path)
    candidate_root, candidate_receipt = _candidate(tmp_path)
    capture, manual, acceptance = _visual_fixture(tmp_path, candidate_root, candidate_receipt)
    _write(candidate_root / "website" / "styles.css", "body { color: #345678; }\n")

    receipt = validate_candidate_visual_review(
        candidate_receipt,
        capture,
        manual,
        acceptance,
        repo_root=tmp_path,
        now=NOW,
    )

    assert receipt["passed"] is False
    assert _check(receipt, "staged-candidate-provenance")["passed"] is False


def test_visual_review_schema_preserves_pre_promotion_authority_boundary() -> None:
    root = Path(__file__).resolve().parents[1]
    schema = json.loads(
        (
            root / "docs" / "research" / "schemas" / "AUREON_DESIGN_CANDIDATE_VISUAL_REVIEW_V1.schema.json"
        ).read_text(encoding="utf-8")
    )

    properties = schema["properties"]
    assert properties["release_eligible"]["const"] is False
    assert properties["package_authority"]["const"] == "none"
    assert properties["deployment_authority"]["const"] == "none"
    assert properties["canonical_promotion_authority"]["const"] == "owner-controlled"


def _accepted_visual_review(
    root: Path,
    candidate_root: Path,
    candidate_receipt: Path,
) -> Path:
    capture, manual, acceptance = _visual_fixture(root, candidate_root, candidate_receipt)
    review = validate_candidate_visual_review(
        candidate_receipt,
        capture,
        manual,
        acceptance,
        repo_root=root,
        now=NOW,
    )
    assert review["passed"] is True
    return write_candidate_visual_review(
        review,
        candidate_root / "visual-review" / "prepromotion-visual-review.v1.json",
        repo_root=root,
    )


def _learning_manifest(root: Path, candidate_root: Path) -> Path:
    _write(root / "skills" / "aureon-harmonic-design-suite" / "SKILL.md", "# Fixture skill\n")
    _write(root / "tests" / "test_fixture_design_pattern.py", "def test_fixture():\n    assert True\n")
    manifest_path = candidate_root / "feedback" / "research-evidence-rail.manifest.v1.json"
    _write_json(
        manifest_path,
        {
            "schema": LEARNING_MANIFEST_SCHEMA,
            "pattern_id": "research-evidence-rail",
            "version": "1.0.0",
            "title": "Research evidence rail",
            "summary": "A bounded visual styling repair with current staged and human-review evidence.",
            "input_contract": ["A source-bound visual styling work order."],
            "output_contract": ["A staged candidate with a passing visual review."],
            "allowed_paths": ["styles.css"],
            "regression_tests": ["tests/test_fixture_design_pattern.py"],
            "proposed_skill_target": "skills/aureon-harmonic-design-suite/SKILL.md",
            "refresh_by": "2027-07-28T12:05:00Z",
        },
    )
    return manifest_path


def test_design_learning_ledger_records_only_source_bound_human_reviewed_proposal(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    canonical_before = (tmp_path / "website" / "styles.css").read_text(encoding="utf-8")
    candidate_root, candidate_receipt = _candidate(tmp_path)
    visual_review = _accepted_visual_review(tmp_path, candidate_root, candidate_receipt)
    manifest = _learning_manifest(tmp_path, candidate_root)

    record = validate_design_learning_record(
        candidate_receipt,
        visual_review,
        manifest,
        repo_root=tmp_path,
        now=NOW,
    )

    assert record["schema"] == LEARNING_RECORD_SCHEMA
    assert record["state"] == "learning-proposal-recorded"
    assert record["passed"] is True
    assert record["authority"] == LEARNING_AUTHORITY
    assert record["release_eligible"] is False
    assert record["package_authority"] == "none"
    assert record["deployment_authority"] == "none"
    assert record["promotion"]["applied"] is False
    assert record["promotion"]["state"] == "proposed-human-reviewed-skill-update"
    assert record["pattern"]["allowed_paths"] == ["styles.css"]
    assert (tmp_path / "website" / "styles.css").read_text(encoding="utf-8") == canonical_before

    output = write_design_learning_record(
        record,
        candidate_root / "feedback" / "design-learning.v1.json",
        repo_root=tmp_path,
    )
    assert output.is_file()
    with pytest.raises(DesignLearningLedgerError, match="Refusing to overwrite"):
        write_design_learning_record(record, output, repo_root=tmp_path)


def test_design_learning_ledger_fails_closed_for_stale_human_review_or_unsupported_scope(
    tmp_path: Path,
) -> None:
    _fake_repo(tmp_path)
    candidate_root, candidate_receipt = _candidate(tmp_path)
    visual_review = _accepted_visual_review(tmp_path, candidate_root, candidate_receipt)
    manifest = _learning_manifest(tmp_path, candidate_root)

    acceptance = (
        candidate_root / "visual-review" / "AUREON_CANDIDATE_HUMAN_VISUAL_ACCEPTANCE_20260728T120200Z.json"
    )
    acceptance_payload = json.loads(acceptance.read_text(encoding="utf-8"))
    acceptance_payload["note"] = "Changed after visual-review validation."
    _write_json(acceptance, acceptance_payload)

    stale = validate_design_learning_record(
        candidate_receipt,
        visual_review,
        manifest,
        repo_root=tmp_path,
        now=NOW,
    )
    assert stale["passed"] is False
    assert stale["state"] == "blocked"
    assert stale["release_eligible"] is False
    assert (
        next(item for item in stale["checks"] if item["id"] == "visual-review-revalidated")["passed"] is False
    )

    scoped_root = tmp_path / "scope"
    _fake_repo(scoped_root)
    candidate_root, candidate_receipt = _candidate(scoped_root)
    visual_review = _accepted_visual_review(scoped_root, candidate_root, candidate_receipt)
    manifest = _learning_manifest(scoped_root, candidate_root)
    manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_payload["allowed_paths"] = ["index.html"]
    _write_json(manifest, manifest_payload)

    unsupported_scope = validate_design_learning_record(
        candidate_receipt,
        visual_review,
        manifest,
        repo_root=scoped_root,
        now=NOW,
    )
    assert unsupported_scope["passed"] is False
    assert (
        next(item for item in unsupported_scope["checks"] if item["id"] == "pattern-allowed-paths")["passed"]
        is False
    )
