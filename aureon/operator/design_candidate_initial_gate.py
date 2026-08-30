"""Source-bound initial browser gates for staged Aureon design candidates.

This module turns one focused browser receipt into a deterministic decision:
either a staged candidate has earned a sequential performance-repeatability
series, or its first objective gate has rejected it.  It deliberately cannot
alter a candidate, promote it, package it, access credentials, or deploy it.

The gate is intentionally narrower than a full candidate visual review.  A
passing initial gate only permits a performance series; it never replaces the
complete browser matrix, named pixel review, human visual acceptance, or the
owner-controlled WebsiteOperator release lifecycle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from aureon.operator.design_candidate_control import (
    CANDIDATE_SCHEMA,
    DesignCandidateControlError,
    verify_staged_candidate_receipt,
)

INITIAL_GATE_SCHEMA = "aureon.design-candidate-initial-gate.v1"
SNAPSHOT_ALGORITHM = "sha256(path NUL bytes NUL file_sha256 LF), paths sorted"
AUTHORITY = {
    "scope": "local staged-candidate initial browser-performance feedback only",
    "canonical_website_mutation": "never by this control or a design agent",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "human_visual_acceptance": "still required for material brand changes",
    "release_authority": "WebsiteOperator owner gate only",
}


class DesignCandidateInitialGateError(ValueError):
    """The supplied candidate or focused browser evidence is unsafe or malformed."""


def _utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignCandidateInitialGateError(
        "Could not locate an Aureon repository with pyproject.toml and aureon/."
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower()


def _relative_to_repo(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise DesignCandidateInitialGateError(f"Path must stay within the repository: {path}") from exc


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list_of_mappings(value: object) -> list[dict[str, Any]]:
    return (
        [dict(item) for item in value]
        if isinstance(value, list) and all(isinstance(item, Mapping) for item in value)
        else []
    )


def _empty(value: object) -> bool:
    return value in (None, [], {}, "")


def _check(identifier: str, passed: bool, message: str, **evidence: Any) -> dict[str, Any]:
    return {
        "id": identifier,
        "passed": bool(passed),
        "message": message,
        "evidence": evidence,
    }


def _file_under(root: Path, value: Path, *, label: str, allowed_root: Path | None = None) -> Path:
    target = value if value.is_absolute() else root / value
    target = target.resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise DesignCandidateInitialGateError(f"{label} must stay inside the repository.") from exc
    if allowed_root is not None:
        try:
            target.relative_to(allowed_root.resolve())
        except ValueError as exc:
            raise DesignCandidateInitialGateError(
                f"{label} must stay inside the staged candidate artifact."
            ) from exc
    if not target.is_file() or target.is_symlink():
        raise DesignCandidateInitialGateError(f"{label} must be a regular file: {target}")
    return target


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DesignCandidateInitialGateError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(raw, Mapping):
        raise DesignCandidateInitialGateError(f"{label} must be a JSON object: {path}")
    return dict(raw)


def snapshot_website_tree(site_root: Path) -> dict[str, Any]:
    """Return the deterministic tree format used by the V28 browser QA runner."""

    root = site_root.resolve()
    if not root.is_dir() or root.is_symlink():
        raise DesignCandidateInitialGateError(f"Candidate website must be a regular directory: {root}")
    files: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if path.is_symlink():
            raise DesignCandidateInitialGateError(
                f"Candidate website contains an unsupported symbolic link: {path}"
            )
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        files.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            }
        )
    tree_input = "".join(f"{item['path']}\0{item['bytes']}\0{item['sha256']}\n" for item in files).encode(
        "utf-8"
    )
    return {
        "algorithm": SNAPSHOT_ALGORITHM,
        "sha256": hashlib.sha256(tree_input).hexdigest().lower(),
        "fileCount": len(files),
        "totalBytes": sum(int(item["bytes"]) for item in files),
        "files": files,
    }


def _snapshot_matches(observed: Mapping[str, Any], expected: Mapping[str, Any]) -> bool:
    return (
        observed.get("algorithm") == SNAPSHOT_ALGORITHM
        and str(observed.get("sha256") or "").lower() == str(expected.get("sha256") or "").lower()
        and observed.get("fileCount") == expected.get("fileCount")
        and observed.get("totalBytes") == expected.get("totalBytes")
    )


def _targeted_records(
    visual: Mapping[str, Any], *, engine_name: str, route_name: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    engines = _list_of_mappings(visual.get("engines"))
    engines = [engine for engine in engines if engine.get("engine") == engine_name]
    if len(engines) != 1:
        raise DesignCandidateInitialGateError(
            f"Focused browser receipt must contain exactly one {engine_name!r} engine record."
        )
    engine = engines[0]
    routes = [item for item in _list_of_mappings(engine.get("routes")) if item.get("name") == route_name]
    performance = [
        item for item in _list_of_mappings(engine.get("performance")) if item.get("routeName") == route_name
    ]
    if len(routes) != 1 or len(performance) != 1:
        raise DesignCandidateInitialGateError(
            f"Focused browser receipt must contain exactly one {route_name!r} route and performance record."
        )
    return engine, routes[0], performance[0]


def evaluate_initial_candidate_gate(
    candidate_receipt_path: Path,
    visual_receipt_path: Path,
    *,
    route_name: str,
    engine_name: str = "chromium",
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate one focused browser result without granting any release authority."""

    root = _find_repo_root(repo_root)
    candidate_path = _file_under(root, candidate_receipt_path, label="Candidate receipt")
    candidate_receipt = _read_json(candidate_path, label="Candidate receipt")
    candidate = _mapping(candidate_receipt.get("candidate"))
    candidate_root_value = candidate.get("root")
    candidate_site_value = candidate.get("website_path")
    if not isinstance(candidate_root_value, str) or not isinstance(candidate_site_value, str):
        raise DesignCandidateInitialGateError(
            "Candidate receipt must declare its staged root and website path."
        )
    candidate_root = (root / candidate_root_value).resolve()
    candidate_site = (root / candidate_site_value).resolve()
    candidate_artifact_root = (root / "artifacts" / "website-candidates").resolve()
    try:
        candidate_root.relative_to(candidate_artifact_root)
        candidate_site.relative_to(candidate_root)
        candidate_path.relative_to(candidate_root)
    except ValueError as exc:
        raise DesignCandidateInitialGateError(
            "Candidate receipt and website path must remain within one staged candidate artifact."
        ) from exc
    if not candidate_root.is_dir() or candidate_root.is_symlink():
        raise DesignCandidateInitialGateError("Candidate root must be a regular staged directory.")

    visual_path = _file_under(
        root,
        visual_receipt_path,
        label="Focused browser receipt",
        allowed_root=candidate_root,
    )
    visual = _read_json(visual_path, label="Focused browser receipt")

    try:
        candidate_verification = verify_staged_candidate_receipt(
            candidate_receipt,
            repo_root=root,
        )
    except DesignCandidateControlError as exc:
        candidate_verification = {
            "schema": "aureon.design-candidate-verification.v1",
            "state": "fail",
            "passed": False,
            "error": str(exc),
        }

    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "candidate-control",
            candidate_receipt.get("schema") == CANDIDATE_SCHEMA
            and candidate_verification.get("passed") is True,
            "The immutable candidate receipt and its staged source must still pass candidate control.",
            candidate_state=candidate_receipt.get("state"),
            verification_state=candidate_verification.get("state"),
            verification_error=candidate_verification.get("error", ""),
        )
    )

    expected_snapshot = snapshot_website_tree(candidate_site)
    source_binding = _mapping(visual.get("sourceBinding"))
    observed_snapshot = _mapping(source_binding.get("before"))
    source_bound = (
        visual.get("selfHosted") is True
        and source_binding.get("stable") is True
        and source_binding.get("servedFromHashedSource") is True
        and _snapshot_matches(observed_snapshot, expected_snapshot)
    )
    checks.append(
        _check(
            "focused-source-binding",
            source_bound,
            "Focused browser evidence must be self-hosted from the unchanged staged candidate tree.",
            observed_sha256=observed_snapshot.get("sha256"),
            expected_sha256=expected_snapshot["sha256"],
            observed_file_count=observed_snapshot.get("fileCount"),
            expected_file_count=expected_snapshot["fileCount"],
            observed_total_bytes=observed_snapshot.get("totalBytes"),
            expected_total_bytes=expected_snapshot["totalBytes"],
            source_stable=source_binding.get("stable"),
            self_hosted=visual.get("selfHosted"),
        )
    )

    engine, route, performance = _targeted_records(
        visual,
        engine_name=engine_name,
        route_name=route_name,
    )
    engine_clean = (
        engine.get("status") != "UNSUPPORTED"
        and _empty(_mapping(engine.get("diagnostics")).get("warnings"))
        and _empty(_mapping(engine.get("diagnostics")).get("errors"))
        and _empty(_mapping(engine.get("engineWideDiagnostics")).get("warnings"))
        and _empty(_mapping(engine.get("engineWideDiagnostics")).get("errors"))
    )
    route_clean = (
        route.get("pass") is True
        and _empty(route.get("errors"))
        and _empty(route.get("warnings"))
        and _empty(route.get("resourceFailures"))
    )
    checks.append(
        _check(
            "targeted-runtime",
            engine_clean and route_clean,
            "The selected engine and route must complete without warnings, errors, or required-resource failures.",
            engine_status=engine.get("status"),
            route_status=route.get("status"),
            route_pass=route.get("pass"),
        )
    )

    geometry = _mapping(performance.get("renderingGeometry"))
    geometry_pass = (
        geometry.get("status") in {"RAN", "NOT_APPLICABLE", "NOT_SUPPORTED"}
        and geometry.get("pass") is True
        and _empty(geometry.get("failureReasons"))
    )
    checks.append(
        _check(
            "deferred-render-geometry",
            geometry_pass,
            "Any deferred rendering must preserve deterministic document geometry before a repeatability series.",
            status=geometry.get("status"),
            candidate_count=geometry.get("candidateCount"),
            deltas=geometry.get("deltas"),
            failure_reasons=geometry.get("failureReasons"),
        )
    )

    metric_checks = _mapping(performance.get("checks"))
    failed_metric_checks = sorted(
        identifier
        for identifier, value in metric_checks.items()
        if not isinstance(value, Mapping) or value.get("pass") is not True
    )
    performance_clean = (
        performance.get("pass") is True
        and bool(metric_checks)
        and not failed_metric_checks
        and _empty(performance.get("errors"))
        and _empty(performance.get("warnings"))
        and _empty(performance.get("resourceFailures"))
    )
    checks.append(
        _check(
            "initial-performance",
            performance_clean,
            "Every fixed performance check must pass on the first source-bound run before repeatability testing.",
            failed_checks=failed_metric_checks,
            metrics=_mapping(performance.get("metrics")),
            budgets=_mapping(performance.get("budgets")),
        )
    )

    checks_passed = {str(check["id"]): check["passed"] is True for check in checks}
    initial_gate_passed = all(checks_passed.values())
    if not checks_passed["candidate-control"] or not checks_passed["focused-source-binding"]:
        state = "blocked"
        next_gate = (
            "Repair provenance or source binding first. Do not use another browser run to mask an "
            "unbound result."
        )
    elif not checks_passed["deferred-render-geometry"]:
        state = "rejected-geometry"
        next_gate = (
            "Preserve this rejected candidate and its receipt. Do not start a retry-seeking performance "
            "series; any successor needs a fresh exact-path work order."
        )
    elif not checks_passed["targeted-runtime"] or not checks_passed["initial-performance"]:
        state = "rejected-performance"
        next_gate = (
            "Preserve this rejected candidate and its receipt. Do not start a retry-seeking performance "
            "series; profile the source-level cause before a separately authorised successor."
        )
    else:
        state = "eligible-for-repeatability"
        next_gate = (
            "Run the fixed sequential performance-repeatability series, then the complete staged browser "
            "matrix and named human visual review. This result does not grant promotion, packaging, or deployment."
        )

    return {
        "schema": INITIAL_GATE_SCHEMA,
        "assessed_at": _utc_iso(now),
        "state": state,
        "passed": initial_gate_passed,
        "repeatability_series_permitted": initial_gate_passed,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": dict(AUTHORITY),
        "candidate": {
            "receipt": {
                "path": _relative_to_repo(root, candidate_path),
                "sha256": _sha256_file(candidate_path),
            },
            "root": _relative_to_repo(root, candidate_root),
            "website_path": _relative_to_repo(root, candidate_site),
            "control_tree_sha256": candidate.get("tree_sha256"),
            "control_verification": candidate_verification,
        },
        "evidence": {
            "focused_browser_receipt": {
                "path": _relative_to_repo(root, visual_path),
                "sha256": _sha256_file(visual_path),
                "source_tree_sha256": expected_snapshot["sha256"],
                "full_visual_status": visual.get("status"),
            },
            "target": {"engine": engine_name, "route_name": route_name, "route": route.get("route")},
        },
        "checks": checks,
        "next_gate": next_gate,
    }


def write_initial_candidate_gate(
    receipt: Mapping[str, Any], output_path: Path, *, repo_root: Path | None = None
) -> Path:
    """Write immutable initial-gate evidence inside the candidate artifact only."""

    root = _find_repo_root(repo_root)
    candidate = _mapping(receipt.get("candidate"))
    candidate_root_value = candidate.get("root")
    if not isinstance(candidate_root_value, str):
        raise DesignCandidateInitialGateError("Initial-gate receipt must declare its candidate root.")
    candidate_root = (root / candidate_root_value).resolve()
    target = output_path if output_path.is_absolute() else root / output_path
    target = target.resolve()
    try:
        target.relative_to(candidate_root)
    except ValueError as exc:
        raise DesignCandidateInitialGateError(
            "Initial-gate evidence must stay inside the staged candidate artifact."
        ) from exc
    if target.suffix.lower() != ".json":
        raise DesignCandidateInitialGateError("Initial-gate output must use a .json filename.")
    if target.exists():
        raise DesignCandidateInitialGateError(f"Refusing to overwrite initial-gate evidence: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(dict(receipt), indent=2) + "\n", encoding="utf-8")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-design-candidate-initial-gate",
        description="Evaluate one source-bound focused browser gate for a staged Aureon design candidate.",
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--candidate-receipt", type=Path, required=True)
    parser.add_argument("--visual-receipt", type=Path, required=True)
    parser.add_argument("--route-name", required=True)
    parser.add_argument("--engine", default="chromium")
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        receipt = evaluate_initial_candidate_gate(
            args.candidate_receipt,
            args.visual_receipt,
            route_name=args.route_name,
            engine_name=args.engine,
            repo_root=args.repo_root,
        )
        root = _find_repo_root(args.repo_root)
        output = write_initial_candidate_gate(receipt, args.output, repo_root=root)
        print(
            json.dumps(
                {
                    "state": receipt["state"],
                    "passed": receipt["passed"],
                    "repeatability_series_permitted": receipt["repeatability_series_permitted"],
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
        DesignCandidateInitialGateError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
