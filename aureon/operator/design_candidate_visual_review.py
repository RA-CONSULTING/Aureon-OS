"""Source-bound visual-review evidence for one staged Aureon website candidate.

This module is intentionally a pre-promotion evidence bridge.  It verifies a
candidate-control receipt, a browser QA capture, a completed manual pixel
review, and a separate named human visual-acceptance receipt against the exact
staged tree.  It never copies a candidate to ``website/``, packages a release,
uses credentials, or deploys.  A separately owner-controlled canonical
promotion must still be followed by a fresh canonical V28 audit, manual
review, composite gate, package, backup, owner approval, and live read-back.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from aureon.operator.design_candidate_control import (
    CANDIDATE_SCHEMA,
    DEFAULT_CANDIDATE_ROOT,
    DesignCandidateControlError,
    _find_repo_root,
    _resolve_under,
    verify_staged_candidate_receipt,
)

VISUAL_REVIEW_SCHEMA = "aureon.design-candidate-visual-review.v1"
VISUAL_CAPTURE_SCHEMA = "aureon.design-candidate-visual-capture.v1"
VISUAL_QA_SCHEMA = "aureon-website-visual-qa-v28.3"
MANUAL_REVIEW_SCHEMA = "aureon.design-candidate-manual-pixel-review.v1"
HUMAN_ACCEPTANCE_SCHEMA = "aureon.design-candidate-human-visual-acceptance.v1"

AUTHORITY = {
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "canonical_promotion_authority": "owner-controlled",
}

FINAL_ENGINES = ("chromium", "firefox", "webkit")
CANONICAL_ROUTES = (
    ("home", "/"),
    ("about", "/about/"),
    ("community", "/community/"),
    ("contact", "/contact/"),
    ("diligence", "/diligence/"),
    ("funding", "/funding/"),
    ("investor", "/funding/investor-deck/"),
    ("live", "/live/"),
    ("projects", "/projects/"),
    ("publications", "/publications/"),
    ("research", "/research/"),
    ("journal", "/research/journal/"),
    ("updates", "/updates/"),
    ("vision", "/vision/"),
)
CANONICAL_VIEWPORTS = ("reflow", "compact", "mobile", "tablet", "laptop", "desktop", "wide")
CANONICAL_INTERACTIONS = (
    "projects packet inspector",
    "live evidence packet",
    "engagement router",
    "research proof path",
)
SCREENSHOT_SCOPE = (
    ("desktop", "home"),
    ("desktop", "funding"),
    ("desktop", "investor"),
    ("desktop", "research"),
    ("desktop", "publications"),
    ("mobile", "home"),
    ("mobile", "projects"),
    ("mobile", "research"),
    ("mobile", "contact"),
)
_SHA256 = re.compile(r"[A-Fa-f0-9]{64}")
_RUN_ID = re.compile(r"[a-z0-9][a-z0-9._-]{2,80}")
_CANONICAL_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z")


class DesignCandidateVisualReviewError(ValueError):
    """One staged visual-review input is missing, stale, malformed, or misbound."""


def _utc_iso(value: datetime | None = None) -> str:
    return (
        (value or datetime.now(UTC)).astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _check(identifier: str, passed: bool, message: str, **evidence: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "passed": bool(passed),
        "message": message,
        "evidence": evidence,
    }


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise DesignCandidateVisualReviewError(f"{label} does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise DesignCandidateVisualReviewError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise DesignCandidateVisualReviewError(f"{label} must be a JSON object.")
    return value


def _relative_to_repo(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise DesignCandidateVisualReviewError("Evidence must stay inside the Aureon repository.") from exc


def _canonical_time(value: object) -> datetime | None:
    if not isinstance(value, str) or not _CANONICAL_UTC.fullmatch(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if _utc_iso(parsed) == value else None


def _file_under(root: Path, raw: object, *, label: str, allowed_root: Path) -> tuple[Path, str]:
    try:
        candidate = _resolve_under(root, raw, label=label)
        candidate.relative_to(allowed_root.resolve())
    except (DesignCandidateControlError, ValueError) as exc:
        raise DesignCandidateVisualReviewError(
            f"{label} must stay below {_relative_to_repo(root, allowed_root)}/."
        ) from exc
    if not candidate.is_file() or candidate.is_symlink():
        raise DesignCandidateVisualReviewError(f"{label} must be a regular existing file.")
    return candidate, _relative_to_repo(root, candidate)


def _candidate_paths(
    candidate_receipt_path: Path,
    *,
    root: Path,
) -> tuple[dict[str, Any], Path, Path, Path, str]:
    receipt_path = (
        candidate_receipt_path if candidate_receipt_path.is_absolute() else root / candidate_receipt_path
    )
    receipt_path = receipt_path.resolve()
    receipt = _read_json(receipt_path, label="Candidate receipt")
    candidate = receipt.get("candidate")
    if receipt.get("schema") != CANDIDATE_SCHEMA or not isinstance(candidate, Mapping):
        raise DesignCandidateVisualReviewError(
            "Candidate receipt must use the staged candidate-control schema."
        )
    try:
        candidate_root = _resolve_under(root, candidate.get("root"), label="Candidate root")
        candidate_site = _resolve_under(root, candidate.get("website_path"), label="Candidate website")
    except DesignCandidateControlError as exc:
        raise DesignCandidateVisualReviewError(str(exc)) from exc
    relative_root = _relative_to_repo(root, candidate_root)
    parts = Path(relative_root).parts
    if (
        len(parts) != 3
        or parts[:2] != DEFAULT_CANDIDATE_ROOT.parts
        or not _RUN_ID.fullmatch(parts[2])
        or candidate_site != candidate_root / "website"
        or receipt_path != candidate_root / "candidate.v1.json"
    ):
        raise DesignCandidateVisualReviewError(
            "Candidate receipt and website must use their deterministic staged artifact paths."
        )
    if not candidate_site.is_dir() or candidate_site.is_symlink():
        raise DesignCandidateVisualReviewError("Candidate website must be a regular staged directory.")
    return receipt, receipt_path, candidate_root, candidate_site, relative_root


def _qa_snapshot(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink():
            raise DesignCandidateVisualReviewError(f"Candidate website contains a symbolic link: {path}")
        if not path.is_file():
            continue
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path).lower(),
            }
        )
    tree_input = "".join(f"{row['path']}\0{row['bytes']}\0{row['sha256']}\n" for row in rows)
    return {
        "algorithm": "sha256(path NUL bytes NUL file_sha256 LF), paths sorted",
        "sha256": hashlib.sha256(tree_input.encode("utf-8")).hexdigest(),
        "fileCount": len(rows),
        "totalBytes": sum(int(row["bytes"]) for row in rows),
        "files": rows,
    }


def _same(value: object, expected: object) -> bool:
    return value == expected


def _empty(value: object) -> bool:
    return isinstance(value, list) and not value


def _list_of_mappings(value: object) -> list[Mapping[str, Any]]:
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _canonical_json_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest().upper()


def _variant_public_path(value: object) -> str:
    if not isinstance(value, str) or not value or value.startswith(("/", "\\")):
        return ""
    if "\\" in value or "?" in value or "#" in value:
        return ""
    parts = value.split("/")
    if len(parts) < 2 or parts[0] != "website" or any(part in {"", ".", ".."} for part in parts):
        return ""
    public_path = "/".join(parts[1:])
    if not public_path.casefold().endswith(".webp"):
        return ""
    return "/" + public_path


def _positive_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0


def _observed_editorial_surface_matches(
    observed: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> bool:
    variants = _list_of_mappings(expected.get("variants"))
    variants_by_role = {
        str(item.get("role") or ""): item
        for item in variants
        if str(item.get("role") or "") in {"small", "large"}
    }
    if set(variants_by_role) != {"small", "large"} or len(variants) != 2:
        return False
    small = variants_by_role["small"]
    large = variants_by_role["large"]
    small_path = _variant_public_path(small.get("path"))
    large_path = _variant_public_path(large.get("path"))
    if not small_path or not large_path or small_path == large_path:
        return False
    image = _mapping(observed.get("image"))
    current_path = image.get("currentSrcPath")
    current_variant = small if current_path == small_path else large if current_path == large_path else {}
    observed_keys = {
        "surfaceId",
        "visible",
        "pictureCount",
        "imageCount",
        "anchorCount",
        "figcaptionCount",
        "nestedSurfaceCount",
        "publicPostUrl",
        "captionMatches",
        "captionVisible",
        "creditMatchCount",
        "creditVisible",
        "image",
        "sourcePaths",
        "failures",
        "pass",
    }
    image_keys = {
        "srcPath",
        "currentSrcPath",
        "altMatches",
        "complete",
        "naturalWidth",
        "naturalHeight",
        "declaredWidth",
        "declaredHeight",
        "renderedWidth",
        "renderedHeight",
        "visible",
    }
    return (
        set(observed) == observed_keys
        and set(image) == image_keys
        and observed.get("surfaceId") == expected.get("surface_id")
        and observed.get("visible") is True
        and observed.get("pictureCount") == 1
        and observed.get("imageCount") == 1
        and observed.get("anchorCount") == 1
        and observed.get("figcaptionCount") == 1
        and observed.get("nestedSurfaceCount") == 0
        and observed.get("publicPostUrl") == expected.get("public_post_url")
        and observed.get("captionMatches") is True
        and observed.get("captionVisible") is True
        and observed.get("creditMatchCount") == 1
        and observed.get("creditVisible") is True
        and observed.get("sourcePaths") == [small_path]
        and observed.get("failures") == []
        and observed.get("pass") is True
        and image.get("srcPath") == large_path
        and image.get("currentSrcPath") in {small_path, large_path}
        and image.get("altMatches") is True
        and image.get("complete") is True
        and image.get("visible") is True
        and image.get("declaredWidth") == large.get("width")
        and image.get("declaredHeight") == large.get("height")
        and image.get("naturalWidth") == current_variant.get("width")
        and image.get("naturalHeight") == current_variant.get("height")
        and _positive_number(image.get("renderedWidth"))
        and _positive_number(image.get("renderedHeight"))
    )


def _editorial_surface_checks(
    candidate: Mapping[str, Any],
    visual: Mapping[str, Any],
) -> dict[str, Any]:
    raw_checks = candidate.get("checks")
    candidate_checks = (
        [
            item
            for item in raw_checks
            if isinstance(item, Mapping) and item.get("id") == "trusted-editorial-surface-replay"
        ]
        if isinstance(raw_checks, list)
        else []
    )
    trusted = candidate_checks[0] if len(candidate_checks) == 1 else {}
    evidence = _mapping(trusted.get("evidence"))
    required = evidence.get("required")
    raw_expected = evidence.get("expected_surfaces")
    expected_surfaces = (
        [dict(item) for item in raw_expected if isinstance(item, Mapping)]
        if isinstance(raw_expected, list)
        else []
    )
    expected_hash = evidence.get("expected_surfaces_sha256")
    candidate_binding_valid = (
        len(candidate_checks) == 1
        and trusted.get("passed") is True
        and isinstance(required, bool)
        and isinstance(raw_expected, list)
        and len(expected_surfaces) == len(raw_expected)
        and isinstance(expected_hash, str)
    )
    if required is True:
        candidate_binding_valid = (
            candidate_binding_valid
            and bool(expected_surfaces)
            and _SHA256.fullmatch(str(expected_hash)) is not None
            and expected_hash == _canonical_json_sha256(expected_surfaces)
        )
    elif required is False:
        candidate_binding_valid = candidate_binding_valid and expected_surfaces == [] and expected_hash == ""
    else:
        candidate_binding_valid = False

    report_binding_valid = (
        visual.get("editorialSurfaceExpectations") == expected_surfaces
        and visual.get("editorialSurfaceExpectationsSha256") == expected_hash
    )
    canonical_routes = {route for _, route in CANONICAL_ROUTES}
    uncovered_routes = sorted(
        {
            str(item.get("route_scope") or "")
            for item in expected_surfaces
            if item.get("route_scope") not in canonical_routes
        }
    )
    audit_failures: list[str] = []
    engines = _list_of_mappings(visual.get("engines"))
    if [str(item.get("engine") or "") for item in engines] != list(FINAL_ENGINES):
        audit_failures.append("engine-scope")
    for engine in engines:
        engine_name = str(engine.get("engine") or "")
        routes = _list_of_mappings(engine.get("routes"))
        route_keys = {
            (
                str(item.get("name") or ""),
                str(item.get("route") or ""),
                str(item.get("mode") or ""),
            )
            for item in routes
        }
        expected_route_keys = {
            (name, route, viewport) for name, route in CANONICAL_ROUTES for viewport in CANONICAL_VIEWPORTS
        }
        if route_keys != expected_route_keys or len(routes) != len(expected_route_keys):
            audit_failures.append(f"{engine_name}:route-scope")
        for route in routes:
            route_path = str(route.get("route") or "")
            viewport = str(route.get("mode") or "")
            route_expected = [item for item in expected_surfaces if item.get("route_scope") == route_path]
            route_hash = _canonical_json_sha256(route_expected)
            audit = _mapping(route.get("editorialSurfaceAudit"))
            raw_observed = audit.get("observedSurfaces")
            observed = _list_of_mappings(raw_observed)
            observed_by_id = {str(item.get("surfaceId") or ""): item for item in observed}
            expected_ids = [str(item.get("surface_id") or "") for item in route_expected]
            audit_keys = {
                "pass",
                "expectedSurfaces",
                "expectedSurfacesSha256",
                "observedSurfaces",
                "expectedSurfaceCount",
                "observedSurfaceCount",
                "surfaceCount",
                "duplicateSurfaceIds",
                "failures",
            }
            observations_match = (
                len(observed) == len(observed_by_id) == len(route_expected)
                and set(observed_by_id) == set(expected_ids)
                and all(
                    _observed_editorial_surface_matches(
                        observed_by_id[str(item.get("surface_id") or "")],
                        item,
                    )
                    for item in route_expected
                )
            )
            audit_valid = (
                set(audit) == audit_keys
                and audit.get("pass") is True
                and audit.get("expectedSurfaces") == route_expected
                and audit.get("expectedSurfacesSha256") == route_hash
                and isinstance(raw_observed, list)
                and len(observed) == len(raw_observed)
                and observations_match
                and audit.get("expectedSurfaceCount") == len(route_expected)
                and audit.get("observedSurfaceCount") == len(observed)
                and audit.get("surfaceCount") == len(observed)
                and audit.get("duplicateSurfaceIds") == []
                and audit.get("failures") == []
            )
            if not audit_valid:
                audit_failures.append(f"{engine_name}:{viewport}:{route_path or '<missing>'}")

    passed = candidate_binding_valid and report_binding_valid and not uncovered_routes and not audit_failures
    return _check(
        "visual-editorial-surface-binding",
        passed,
        "Visual QA must bind the one trusted candidate editorial-surface replay and reproduce every expected surface exactly in every browser viewport without persisting raw resource URLs or copy.",
        binary_required=required is True,
        candidate_binding_valid=candidate_binding_valid,
        report_binding_valid=report_binding_valid,
        expected_surface_count=len(expected_surfaces),
        expected_surfaces_sha256=expected_hash if isinstance(expected_hash, str) else "",
        uncovered_routes=uncovered_routes,
        audit_failures=audit_failures,
    )


def _incomplete_nodes(visual: Mapping[str, Any]) -> list[dict[str, Any]]:
    source_sha = str(_mapping(_mapping(visual.get("sourceBinding")).get("before")).get("sha256") or "")
    nodes: list[dict[str, Any]] = []
    for engine in _list_of_mappings(visual.get("engines")):
        for accessibility in _list_of_mappings(engine.get("accessibility")):
            axe = accessibility.get("axe")
            if not isinstance(axe, Mapping):
                continue
            for rule in _list_of_mappings(axe.get("incomplete")):
                for node in _list_of_mappings(rule.get("nodes")):
                    target = node.get("target")
                    payload = [
                        "aureon-axe-incomplete-node-v1",
                        unicodedata.normalize("NFC", str(engine.get("engine") or "")),
                        unicodedata.normalize("NFC", str(accessibility.get("route") or "")),
                        unicodedata.normalize("NFC", str(rule.get("id") or "")),
                        [unicodedata.normalize("NFC", str(item)) for item in target]
                        if isinstance(target, list)
                        else target,
                    ]
                    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                    nodes.append(
                        {
                            "nodeId": f"axei1-{hashlib.sha256(encoded).hexdigest()}",
                            "sourceTreeSha256": source_sha,
                            "engine": engine.get("engine"),
                            "routeName": accessibility.get("routeName"),
                            "route": accessibility.get("route"),
                            "ruleId": rule.get("id"),
                            "impact": rule.get("impact"),
                            "target": target,
                            "failureSummary": node.get("failureSummary"),
                        }
                    )
    return nodes


def _reference_matches(
    value: object,
    *,
    expected_path: str,
    expected_sha256: str,
    required_keys: tuple[str, ...] = ("path", "sha256"),
) -> bool:
    return (
        isinstance(value, Mapping)
        and tuple(sorted(value)) == tuple(sorted(required_keys))
        and value.get("path") == expected_path
        and str(value.get("sha256") or "").upper() == expected_sha256.upper()
    )


def _visual_checks(
    visual: Mapping[str, Any],
    *,
    candidate: Mapping[str, Any],
    visual_path: Path,
    candidate_site: Path,
    root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    qa_snapshot = _qa_snapshot(candidate_site)
    source_binding = _mapping(visual.get("sourceBinding"))
    before = _mapping(source_binding.get("before"))
    after = _mapping(source_binding.get("after"))
    checks.append(
        _check(
            "visual-source-inventory",
            (
                visual.get("schema") == VISUAL_QA_SCHEMA
                and visual.get("selfHosted") is True
                and source_binding.get("stable") is True
                and source_binding.get("servedFromHashedSource") is True
                and _same(before, qa_snapshot)
                and _same(after, qa_snapshot)
            ),
            "Visual QA must self-host one unchanged staged candidate and preserve its complete QA-format source inventory.",
            candidate_qa_tree_sha256=qa_snapshot["sha256"],
            visual_before_sha256=before.get("sha256"),
            visual_after_sha256=after.get("sha256"),
        )
    )
    selected_routes = [
        (item.get("name"), item.get("route")) for item in _list_of_mappings(visual.get("selectedRoutes"))
    ]
    selected_viewports = tuple(
        str(item.get("name") or "") for item in _list_of_mappings(visual.get("selectedViewports"))
    )
    coverage = _mapping(visual.get("engineCoverage"))
    capabilities = _mapping(visual.get("capabilities"))
    axe_capability = _mapping(capabilities.get("axe"))
    checks.append(
        _check(
            "visual-scope",
            (
                tuple(selected_routes) == CANONICAL_ROUTES
                and selected_viewports == CANONICAL_VIEWPORTS
                and coverage.get("requested") == list(FINAL_ENGINES)
                and coverage.get("selectionExplicit") is False
                and coverage.get("mode") == "requested-browser-engine-matrix"
                and coverage.get("unsupported") == []
                and axe_capability.get("status") == "INSTALLED"
            ),
            "Candidate visual evidence must cover the fixed full browser, route, viewport, and axe scope.",
        )
    )
    checks.append(_editorial_surface_checks(candidate, visual))
    non_axe_failures: list[str] = []
    axe_violations: list[str] = []
    expected_incomplete: list[dict[str, Any]] = []
    source_sha = qa_snapshot["sha256"]
    screenshot_failures: list[str] = []
    screenshot_dir = visual_path.with_suffix("")
    engines = _list_of_mappings(visual.get("engines"))
    engine_names = [str(engine.get("engine") or "") for engine in engines]
    if engine_names != list(FINAL_ENGINES):
        non_axe_failures.append("engine-scope")
    for engine in engines:
        engine_name = str(engine.get("engine") or "")
        engine_incomplete_nodes = 0
        engine_violations = 0
        engine_non_axe_before = len(non_axe_failures)
        if engine_name not in FINAL_ENGINES or engine.get("status") == "UNSUPPORTED":
            non_axe_failures.append(f"{engine_name}:availability")
            continue
        diagnostics = _mapping(engine.get("diagnostics"))
        if not _empty(diagnostics.get("warnings")) or not _empty(diagnostics.get("errors")):
            non_axe_failures.append(f"{engine_name}:diagnostics")
        routes = _list_of_mappings(engine.get("routes"))
        route_keys = {(item.get("name"), item.get("route"), item.get("mode")) for item in routes}
        expected_route_keys = {
            (name, route, viewport) for name, route in CANONICAL_ROUTES for viewport in CANONICAL_VIEWPORTS
        }
        if route_keys != expected_route_keys or any(
            item.get("pass") is not True
            or not _empty(item.get("errors"))
            or not _empty(item.get("warnings"))
            or not _empty(item.get("resourceFailures"))
            for item in routes
        ):
            non_axe_failures.append(f"{engine_name}:routes")
        interactions = _list_of_mappings(engine.get("interactions"))
        if {item.get("name") for item in interactions} != set(CANONICAL_INTERACTIONS) or any(
            item.get("pass") is not True
            or not _empty(item.get("errors"))
            or not _empty(item.get("warnings"))
            or not _empty(item.get("resourceFailures"))
            for item in interactions
        ):
            non_axe_failures.append(f"{engine_name}:interactions")
        accessibility = _list_of_mappings(engine.get("accessibility"))
        if {(item.get("routeName"), item.get("route")) for item in accessibility} != set(CANONICAL_ROUTES):
            non_axe_failures.append(f"{engine_name}:accessibility-scope")
        for item in accessibility:
            axe = _mapping(item.get("axe"))
            contrast = _mapping(item.get("contrast"))
            keyboard = _mapping(item.get("keyboard"))
            reflow = _mapping(item.get("reflow200"))
            violations = _list_of_mappings(axe.get("violations"))
            if (
                contrast.get("pass") is not True
                or keyboard.get("pass") is not True
                or reflow.get("pass") is not True
                or not _empty(item.get("errors"))
                or not _empty(item.get("warnings"))
                or not _empty(item.get("resourceFailures"))
                or axe.get("status") != "RAN"
                or axe.get("completeNodeEvidence") is not True
            ):
                non_axe_failures.append(f"{engine_name}:accessibility:{item.get('routeName')}")
            for violation in violations:
                axe_violations.append(f"{engine_name}:{item.get('routeName')}:{violation.get('id')}")
                engine_violations += 1
            for incomplete in _list_of_mappings(axe.get("incomplete")):
                engine_incomplete_nodes += len(_list_of_mappings(incomplete.get("nodes")))
                if incomplete.get("id") != "color-contrast":
                    non_axe_failures.append(
                        f"{engine_name}:incomplete-rule:{item.get('routeName')}:{incomplete.get('id')}"
                    )
        performance = _list_of_mappings(engine.get("performance"))
        performance_valid = {(item.get("routeName"), item.get("route")) for item in performance} == set(
            CANONICAL_ROUTES
        )
        for item in performance:
            rendering_geometry = _mapping(item.get("renderingGeometry"))
            geometry_valid = (
                rendering_geometry.get("status") in {"RAN", "NOT_APPLICABLE", "NOT_SUPPORTED"}
                and rendering_geometry.get("pass") is True
                and _empty(rendering_geometry.get("failureReasons"))
            )
            if (
                item.get("pass") is not True
                or not _empty(item.get("errors"))
                or not _empty(item.get("warnings"))
                or not _empty(item.get("resourceFailures"))
                or not geometry_valid
            ):
                performance_valid = False
        if not performance_valid:
            non_axe_failures.append(f"{engine_name}:performance")
        motion = _mapping(engine.get("motion"))
        if motion.get("status") != "RAN" or motion.get("pass") is not True:
            non_axe_failures.append(f"{engine_name}:motion")
        screenshots = _list_of_mappings(engine.get("screenshots"))
        expected_screenshots = {(engine_name, viewport, route) for viewport, route in SCREENSHOT_SCOPE}
        observed_screenshots = {
            (item.get("engine"), item.get("viewport"), item.get("routeName")) for item in screenshots
        }
        if observed_screenshots != expected_screenshots:
            screenshot_failures.append(f"{engine_name}:scope")
        for screenshot in screenshots:
            filename = screenshot.get("filename")
            expected_filename = (
                f"{screenshot.get('engine')}-{screenshot.get('viewport')}-{screenshot.get('routeName')}.png"
            )
            target = screenshot_dir / str(filename or "")
            try:
                target.resolve().relative_to(screenshot_dir.resolve())
                screenshot_path_ok = True
            except ValueError:
                screenshot_path_ok = False
            if (
                filename != expected_filename
                or Path(str(filename or "")).name != filename
                or not screenshot_path_ok
                or not target.is_file()
                or target.is_symlink()
                or str(screenshot.get("sha256") or "").lower() != _sha256_file(target).lower()
                or screenshot.get("bytes") != target.stat().st_size
                or screenshot.get("sourceTreeSha256") != source_sha
            ):
                screenshot_failures.append(f"{engine_name}:{filename}")
        engine_non_axe_failures = len(non_axe_failures) - engine_non_axe_before
        expected_engine_pass = (
            engine_violations == 0
            and engine_incomplete_nodes == 0
            and engine_non_axe_failures == 0
            and not any(item.startswith(f"{engine_name}:") for item in screenshot_failures)
        )
        if engine.get("pass") != expected_engine_pass or engine.get("status") != (
            "PASS" if expected_engine_pass else "FAIL"
        ):
            non_axe_failures.append(f"{engine_name}:status-consistency")
    expected_incomplete = _incomplete_nodes(visual)
    declared_screenshot_count = sum(len(_list_of_mappings(engine.get("screenshots"))) for engine in engines)
    screenshot_integrity = _mapping(visual.get("screenshotIntegrity"))
    if (
        screenshot_integrity.get("pass") is not True
        or screenshot_integrity.get("count") != declared_screenshot_count
    ):
        screenshot_failures.append("declared-integrity")
    diagnostics = _mapping(visual.get("diagnostics"))
    if not _empty(diagnostics.get("warnings")) or not _empty(diagnostics.get("errors")):
        non_axe_failures.append("report-diagnostics")
    expected_status = (
        "PASS"
        if not expected_incomplete and not axe_violations and not non_axe_failures and not screenshot_failures
        else "FAIL"
    )
    checks.append(
        _check(
            "visual-automated-gates",
            not axe_violations
            and not non_axe_failures
            and not screenshot_failures
            and visual.get("status") == expected_status,
            "Candidate visual evidence may leave only complete color-contrast incomplete nodes for separate human inspection; all other browser gates must pass.",
            axe_violations=axe_violations,
            non_axe_failures=non_axe_failures,
            screenshot_failures=screenshot_failures,
            incomplete_node_count=len(expected_incomplete),
            expected_status=expected_status,
            observed_status=visual.get("status"),
        )
    )
    return checks, expected_incomplete, qa_snapshot


def _manual_checks(
    manual: Mapping[str, Any],
    *,
    candidate_receipt_path: str,
    candidate_receipt_sha: str,
    candidate_root: str,
    candidate_site: str,
    control_tree_sha: str,
    visual_path: str,
    visual_sha: str,
    visual: Mapping[str, Any],
    expected_nodes: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], datetime | None]:
    checks: list[dict[str, Any]] = []
    generated_at = _canonical_time(manual.get("generatedAt"))
    visual_generated_at = _canonical_time(visual.get("generatedAt"))
    expected_candidate = {
        "root": candidate_root,
        "websitePath": candidate_site,
        "controlTreeSha256": control_tree_sha,
    }
    expected_visual = {
        "path": visual_path,
        "sha256": visual_sha,
        "generatedAt": visual.get("generatedAt"),
        "sourceTreeSha256": ((visual.get("sourceBinding") or {}).get("before") or {}).get("sha256"),
    }
    checks.append(
        _check(
            "manual-review-binding",
            (
                manual.get("schema") == MANUAL_REVIEW_SCHEMA
                and _reference_matches(
                    manual.get("candidateReceipt"),
                    expected_path=candidate_receipt_path,
                    expected_sha256=candidate_receipt_sha,
                )
                and manual.get("candidate") == expected_candidate
                and manual.get("visualReceipt") == expected_visual
                and isinstance(manual.get("reviewer"), Mapping)
                and bool(str(manual["reviewer"].get("name") or "").strip())
                and manual["reviewer"].get("method") == "manual-pixel-inspection"
                and generated_at is not None
                and visual_generated_at is not None
                and generated_at >= visual_generated_at
            ),
            "Manual pixel review must bind the exact candidate receipt, visual receipt, candidate tree, named reviewer, and non-predating review timestamp.",
        )
    )
    expected_by_id = {str(node["nodeId"]): node for node in expected_nodes}
    reviews = _list_of_mappings(manual.get("reviews"))
    seen: set[str] = set()
    context_ok = True
    status_ok = True
    notes_ok = True
    timing_ok = True
    reviewed = 0
    verified = 0
    not_applicable = 0
    failed = 0
    unreviewed = 0
    for review in reviews:
        node_id = str(review.get("nodeId") or "")
        expected = expected_by_id.get(node_id)
        if not node_id or node_id in seen or expected is None:
            context_ok = False
        seen.add(node_id)
        expected_context = {
            key: expected.get(key) if expected else None
            for key in ("engine", "routeName", "route", "ruleId", "impact", "target", "failureSummary")
        }
        observed_context = {
            key: review.get(key)
            for key in ("engine", "routeName", "route", "ruleId", "impact", "target", "failureSummary")
        }
        if observed_context != expected_context:
            context_ok = False
        status = review.get("status")
        if status == "verified-pass":
            verified += 1
            reviewed += 1
        elif status == "not-applicable":
            not_applicable += 1
            reviewed += 1
        elif status == "fail":
            failed += 1
            reviewed += 1
            status_ok = False
        elif status == "unreviewed":
            unreviewed += 1
            status_ok = False
        else:
            status_ok = False
        if status in {"verified-pass", "not-applicable", "fail"}:
            reviewed_at = _canonical_time(review.get("reviewedAt"))
            if (
                reviewed_at is None
                or visual_generated_at is None
                or generated_at is None
                or reviewed_at < visual_generated_at
                or reviewed_at > generated_at
            ):
                timing_ok = False
            if not isinstance(review.get("notes"), str) or not review["notes"].strip():
                notes_ok = False
        elif review.get("reviewedAt") is not None or review.get("notes") not in {"", None}:
            context_ok = False
    missing = set(expected_by_id).difference(seen)
    if missing:
        unreviewed += len(missing)
        status_ok = False
    expected_summary = {
        "expectedIncompleteNodes": len(expected_by_id),
        "reviewedNodes": reviewed,
        "verifiedPassNodes": verified,
        "notApplicableNodes": not_applicable,
        "failedNodes": failed,
        "unreviewedNodes": unreviewed,
    }
    checks.append(
        _check(
            "manual-pixel-disposition",
            (
                len(reviews) == len(expected_by_id)
                and context_ok
                and status_ok
                and notes_ok
                and timing_ok
                and manual.get("summary") == expected_summary
            ),
            "Manual pixel review must give exactly one current, contextual, non-failed disposition to every automated incomplete node.",
            expected_node_count=len(expected_by_id),
            observed_review_count=len(reviews),
            missing_node_count=len(missing),
            failed_node_count=failed,
            unreviewed_node_count=unreviewed,
        )
    )
    return checks, generated_at


def validate_candidate_visual_review(
    candidate_receipt_path: Path,
    capture_receipt_path: Path,
    manual_review_path: Path,
    human_acceptance_path: Path,
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Validate pre-promotion visual evidence for one unchanged staged candidate."""

    root = _find_repo_root(repo_root)
    try:
        candidate, candidate_path, candidate_root, candidate_site, candidate_root_relative = _candidate_paths(
            candidate_receipt_path,
            root=root,
        )
    except (DesignCandidateControlError, DesignCandidateVisualReviewError) as exc:
        raise DesignCandidateVisualReviewError(str(exc)) from exc
    visual_root = candidate_root / "visual-review"
    checks: list[dict[str, Any]] = []
    candidate_verification = verify_staged_candidate_receipt(candidate, repo_root=root)
    checks.append(
        _check(
            "staged-candidate-provenance",
            candidate_verification.get("passed") is True,
            "The candidate-control receipt must still revalidate against its immutable source-bound work order before visual review can be retained.",
            failed_checks=[
                item["id"]
                for item in candidate_verification.get("checks", [])
                if item.get("passed") is not True
            ],
        )
    )
    candidate_path_relative = _relative_to_repo(root, candidate_path)
    candidate_sha = _sha256_file(candidate_path)
    control_tree_sha = str((candidate.get("candidate") or {}).get("tree_sha256") or "")

    capture_path, capture_relative = _file_under(
        root,
        _relative_to_repo(
            root, capture_receipt_path if capture_receipt_path.is_absolute() else root / capture_receipt_path
        ),
        label="Candidate visual capture receipt",
        allowed_root=visual_root,
    )
    capture = _read_json(capture_path, label="Candidate visual capture receipt")
    visual_ref = _mapping(capture.get("visualReceipt"))
    visual_path: Path | None = None
    visual_relative = ""
    visual_sha = ""
    try:
        visual_path, visual_relative = _file_under(
            root,
            visual_ref.get("path"),
            label="Candidate visual receipt",
            allowed_root=visual_root,
        )
        visual_sha = _sha256_file(visual_path)
    except DesignCandidateVisualReviewError:
        pass
    capture_ok = (
        capture.get("schema") == VISUAL_CAPTURE_SCHEMA
        and _reference_matches(
            capture.get("candidateReceipt"),
            expected_path=candidate_path_relative,
            expected_sha256=candidate_sha,
        )
        and capture.get("candidate")
        == {
            "root": candidate_root_relative,
            "websitePath": _relative_to_repo(root, candidate_site),
            "controlTreeSha256": control_tree_sha,
        }
        and visual_path is not None
        and str(visual_ref.get("sha256") or "").upper() == visual_sha
        and str(visual_ref.get("sourceTreeSha256") or "").lower() == _qa_snapshot(candidate_site)["sha256"]
        and capture.get("authority") == AUTHORITY
        and _canonical_time(capture.get("generatedAt")) is not None
    )
    checks.append(
        _check(
            "visual-capture-binding",
            capture_ok,
            "Visual capture must bind exact candidate receipt bytes, the staged candidate control tree, an in-scope visual receipt, and no publication authority.",
            capture_path=capture_relative,
        )
    )
    if visual_path is None:
        raise DesignCandidateVisualReviewError(
            "Candidate capture does not reference a readable in-scope visual receipt."
        )
    visual = _read_json(visual_path, label="Candidate visual receipt")
    visual_checks, expected_nodes, qa_snapshot = _visual_checks(
        visual,
        candidate=candidate,
        visual_path=visual_path,
        candidate_site=candidate_site,
        root=root,
    )
    checks.extend(visual_checks)

    manual_path, manual_relative = _file_under(
        root,
        _relative_to_repo(
            root, manual_review_path if manual_review_path.is_absolute() else root / manual_review_path
        ),
        label="Candidate manual pixel-review receipt",
        allowed_root=visual_root,
    )
    manual = _read_json(manual_path, label="Candidate manual pixel-review receipt")
    manual_checks, manual_generated_at = _manual_checks(
        manual,
        candidate_receipt_path=candidate_path_relative,
        candidate_receipt_sha=candidate_sha,
        candidate_root=candidate_root_relative,
        candidate_site=_relative_to_repo(root, candidate_site),
        control_tree_sha=control_tree_sha,
        visual_path=visual_relative,
        visual_sha=visual_sha,
        visual=visual,
        expected_nodes=expected_nodes,
    )
    checks.extend(manual_checks)

    acceptance_path, acceptance_relative = _file_under(
        root,
        _relative_to_repo(
            root,
            human_acceptance_path if human_acceptance_path.is_absolute() else root / human_acceptance_path,
        ),
        label="Candidate human visual-acceptance receipt",
        allowed_root=visual_root,
    )
    acceptance = _read_json(acceptance_path, label="Candidate human visual-acceptance receipt")
    acceptance_at = _canonical_time(acceptance.get("acceptedAt"))
    acceptance_ok = (
        acceptance.get("schema") == HUMAN_ACCEPTANCE_SCHEMA
        and acceptance.get("decision") == "accepted"
        and isinstance(acceptance.get("reviewer"), Mapping)
        and bool(str(acceptance["reviewer"].get("name") or "").strip())
        and acceptance["reviewer"].get("method") == "manual-visual-review"
        and _reference_matches(
            acceptance.get("candidateReceipt"),
            expected_path=candidate_path_relative,
            expected_sha256=candidate_sha,
        )
        and _reference_matches(
            acceptance.get("visualReceipt"),
            expected_path=visual_relative,
            expected_sha256=visual_sha,
        )
        and _reference_matches(
            acceptance.get("manualPixelReview"),
            expected_path=manual_relative,
            expected_sha256=_sha256_file(manual_path),
        )
        and acceptance_at is not None
        and (manual_generated_at is None or acceptance_at >= manual_generated_at)
        and isinstance(acceptance.get("note"), str)
        and bool(acceptance["note"].strip())
        and acceptance.get("authority") == AUTHORITY
    )
    checks.append(
        _check(
            "human-visual-acceptance",
            acceptance_ok,
            "A separate named human visual-acceptance receipt must bind the exact candidate, visual, and completed manual review evidence without release or deployment authority.",
            acceptance_path=acceptance_relative,
        )
    )
    passed = all(check["passed"] for check in checks)
    return {
        "schema": VISUAL_REVIEW_SCHEMA,
        "reviewed_at": _utc_iso(now),
        "state": "prepromotion-visual-review-passed" if passed else "blocked",
        "passed": passed,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "canonical_promotion_authority": "owner-controlled",
        "candidate": {
            "receipt": {"path": candidate_path_relative, "sha256": candidate_sha},
            "root": candidate_root_relative,
            "website_path": _relative_to_repo(root, candidate_site),
            "control_tree_sha256": control_tree_sha,
            "visual_qa_tree_sha256": qa_snapshot["sha256"],
        },
        "evidence": {
            "capture": {"path": capture_relative, "sha256": _sha256_file(capture_path)},
            "visual_receipt": {"path": visual_relative, "sha256": visual_sha},
            "manual_pixel_review": {"path": manual_relative, "sha256": _sha256_file(manual_path)},
            "human_visual_acceptance": {
                "path": acceptance_relative,
                "sha256": _sha256_file(acceptance_path),
            },
        },
        "checks": checks,
        "next_gate": (
            "Separate owner-controlled canonical promotion, then a fresh canonical WebsiteOperator audit, "
            "V28 visual/manual/composite evidence, package, backup, owner approval, and live HTTPS read-back."
        ),
    }


def write_candidate_visual_review(
    receipt: Mapping[str, Any],
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Write immutable review evidence only inside its candidate artifact root."""

    root = _find_repo_root(repo_root)
    candidate = receipt.get("candidate") if isinstance(receipt, Mapping) else None
    if not isinstance(candidate, Mapping):
        raise DesignCandidateVisualReviewError(
            "Visual-review receipt must declare its staged candidate root."
        )
    candidate_root = _resolve_under(root, candidate.get("root"), label="Candidate visual-review root")
    target = output_path if output_path.is_absolute() else root / output_path
    target = target.resolve()
    try:
        target.relative_to(candidate_root)
    except ValueError as exc:
        raise DesignCandidateVisualReviewError(
            "Candidate visual-review output must stay inside its staged candidate artifact root."
        ) from exc
    if target.suffix.lower() != ".json":
        raise DesignCandidateVisualReviewError("Candidate visual-review output must use a .json filename.")
    if target.exists():
        raise DesignCandidateVisualReviewError(f"Refusing to overwrite review evidence: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-design-candidate-visual-review",
        description="Verify source-bound pre-promotion visual evidence for one staged Aureon website candidate.",
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--candidate-receipt", type=Path, required=True)
    parser.add_argument("--capture-receipt", type=Path, required=True)
    parser.add_argument("--manual-review", type=Path, required=True)
    parser.add_argument("--human-acceptance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        receipt = validate_candidate_visual_review(
            args.candidate_receipt,
            args.capture_receipt,
            args.manual_review,
            args.human_acceptance,
            repo_root=args.repo_root,
        )
        root = _find_repo_root(args.repo_root)
        output = write_candidate_visual_review(receipt, args.output, repo_root=root)
        print(
            json.dumps(
                {
                    "state": receipt["state"],
                    "passed": receipt["passed"],
                    "output": _relative_to_repo(root, output),
                    "release_eligible": False,
                    "deployment_authority": "none",
                },
                indent=2,
            )
        )
        return 0 if receipt["passed"] else 2
    except (
        DesignCandidateControlError,
        DesignCandidateVisualReviewError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
