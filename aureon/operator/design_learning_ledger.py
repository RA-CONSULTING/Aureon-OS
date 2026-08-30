"""Source-bound learning records for Aureon's staged website Design Suite.

This module implements the ``learn`` phase of the Harmonic Design Suite as a
small, append-only evidence record.  A learned pattern is a *proposal* for a
future human-reviewed skill update; it never modifies the canonical website,
skills, release package, hosting account, credentials, or production site.

The record is intentionally stricter than a free-form retrospective.  It
revalidates the staged candidate control and staged visual-review evidence,
requires a bounded pattern contract, binds every input with a SHA-256 digest,
and limits a proposed skill target to the local Harmonic Design Suite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from aureon.operator.design_candidate_control import (
    CANDIDATE_SCHEMA,
    verify_staged_candidate_receipt,
)
from aureon.operator.design_candidate_visual_review import (
    VISUAL_REVIEW_SCHEMA,
    validate_candidate_visual_review,
)

LEARNING_MANIFEST_SCHEMA = "aureon.design-learning-manifest.v1"
LEARNING_RECORD_SCHEMA = "aureon.design-learning-record.v1"

AUTHORITY = {
    "scope": "local staged design-pattern learning and proposal recording",
    "canonical_website_mutation": "never by this ledger or a design agent",
    "skill_mutation": "never automatic; proposal only",
    "release_eligible": False,
    "package_authority": "none",
    "deployment_authority": "none",
    "credential_access": "none",
    "human_visual_acceptance": "already-bound candidate evidence required",
    "release_authority": "WebsiteOperator owner gate only",
}

_PATTERN_ID = re.compile(r"[a-z0-9][a-z0-9-]{2,80}\Z")
_SEMVER = re.compile(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\Z")
_SHA256 = re.compile(r"[A-F0-9]{64}\Z")
_MAX_REFRESH_WINDOW = timedelta(days=366)


class DesignLearningLedgerError(ValueError):
    """A design-learning input cannot be verified safely."""


def _utc_iso(value: datetime | None = None) -> str:
    return (value or datetime.now(UTC)).astimezone(UTC).isoformat().replace("+00:00", "Z")


def _find_repo_root(start: Path | None = None) -> Path:
    candidate = (start or Path.cwd()).resolve()
    for root in (candidate, *candidate.parents):
        if (root / "pyproject.toml").is_file() and (root / "aureon").is_dir():
            return root
    raise DesignLearningLedgerError("Could not locate an Aureon repository with pyproject.toml and aureon/.")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().upper()


def _safe_relative(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignLearningLedgerError(f"{label} must be a non-empty repository-relative path.")
    normalised = value.replace("\\", "/")
    path = Path(normalised)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise DesignLearningLedgerError(f"{label} is unsafe: {value}")
    return path.as_posix()


def _resolve_under(root: Path, value: object, *, label: str) -> tuple[Path, str]:
    relative = _safe_relative(value, label=label)
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise DesignLearningLedgerError(f"{label} escapes its allowed root: {value}") from exc
    return target, relative


def _resolve_input_path(root: Path, value: Path, *, label: str) -> tuple[Path, str]:
    target = value.resolve() if value.is_absolute() else (root / value).resolve()
    try:
        relative = target.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise DesignLearningLedgerError(f"{label} must remain inside the repository.") from exc
    if not target.is_file():
        raise DesignLearningLedgerError(f"{label} does not exist: {relative}")
    return target, relative


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DesignLearningLedgerError(f"{label} is not valid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise DesignLearningLedgerError(f"{label} must contain one JSON object.")
    return value


def _check(identifier: str, passed: bool, message: str, **evidence: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {"id": identifier, "passed": passed, "message": message}
    if evidence:
        payload["evidence"] = evidence
    return payload


def _nonempty_text(value: object, *, label: str, limit: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignLearningLedgerError(f"{label} must be a non-empty string.")
    text = value.strip()
    if len(text) > limit:
        raise DesignLearningLedgerError(f"{label} exceeds {limit} characters.")
    return text


def _text_list(value: object, *, label: str, minimum: int = 1) -> list[str]:
    if not isinstance(value, list):
        raise DesignLearningLedgerError(f"{label} must be a list.")
    values = [_nonempty_text(item, label=f"{label} item", limit=500) for item in value]
    if len(values) < minimum or len(set(values)) != len(values):
        raise DesignLearningLedgerError(f"{label} must contain at least {minimum} unique non-empty values.")
    return values


def _parse_refresh_deadline(value: object, *, now: datetime) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignLearningLedgerError("Pattern refresh_by must be an ISO-8601 timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DesignLearningLedgerError("Pattern refresh_by must be an ISO-8601 timestamp.") from exc
    if parsed.tzinfo is None:
        raise DesignLearningLedgerError("Pattern refresh_by must include a UTC offset.")
    deadline = parsed.astimezone(UTC)
    current = now.astimezone(UTC)
    if deadline <= current or deadline - current > _MAX_REFRESH_WINDOW:
        raise DesignLearningLedgerError(
            "Pattern refresh_by must be future-dated and no more than 366 days away."
        )
    return _utc_iso(deadline)


def _candidate_root(root: Path, candidate: Mapping[str, Any]) -> tuple[Path, str]:
    raw = candidate.get("candidate")
    if not isinstance(raw, Mapping):
        raise DesignLearningLedgerError("Candidate receipt must declare a candidate object.")
    candidate_root, relative = _resolve_under(root, raw.get("root"), label="Candidate root")
    candidates_root = (root / "artifacts" / "website-candidates").resolve()
    try:
        candidate_root.relative_to(candidates_root)
    except ValueError as exc:
        raise DesignLearningLedgerError(
            "Candidate root must stay below artifacts/website-candidates/."
        ) from exc
    if not candidate_root.is_dir():
        raise DesignLearningLedgerError("Candidate root is missing.")
    return candidate_root, relative


def _candidate_path_under_root(
    path: Path,
    candidate_root: Path,
    *,
    label: str,
) -> str:
    try:
        return path.resolve().relative_to(candidate_root.resolve()).as_posix()
    except ValueError as exc:
        raise DesignLearningLedgerError(f"{label} must remain inside the staged candidate root.") from exc


def _evidence_path(
    root: Path,
    candidate_root: Path,
    evidence: Mapping[str, Any],
    key: str,
) -> tuple[Path, str, str]:
    row = evidence.get(key)
    if not isinstance(row, Mapping):
        raise DesignLearningLedgerError(f"Visual-review evidence lacks {key}.")
    path, relative = _resolve_under(root, row.get("path"), label=f"Visual-review {key} path")
    if not path.is_file():
        raise DesignLearningLedgerError(f"Visual-review {key} is missing: {relative}")
    _candidate_path_under_root(path, candidate_root, label=f"Visual-review {key}")
    declared = str(row.get("sha256") or "").upper()
    if not _SHA256.fullmatch(declared):
        raise DesignLearningLedgerError(f"Visual-review {key} has an invalid SHA-256.")
    return path, relative, declared


def _load_pattern_manifest(
    manifest_path: Path,
    *,
    root: Path,
    candidate_root: Path,
    now: datetime,
    changed_paths: set[str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _candidate_path_under_root(manifest_path, candidate_root, label="Learning manifest")
    manifest = _read_json(manifest_path, label="Design-learning manifest")
    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "learning-manifest-schema",
            manifest.get("schema") == LEARNING_MANIFEST_SCHEMA,
            "Learning manifest schema must match the current contract.",
        )
    )
    try:
        pattern_id = _nonempty_text(manifest.get("pattern_id"), label="Pattern id", limit=81)
        id_ok = bool(_PATTERN_ID.fullmatch(pattern_id))
    except DesignLearningLedgerError:
        pattern_id = ""
        id_ok = False
    checks.append(
        _check(
            "pattern-id",
            id_ok,
            "Pattern id must be stable lowercase kebab-case and safe for a learning ledger.",
            pattern_id=pattern_id,
        )
    )

    try:
        version = _nonempty_text(manifest.get("version"), label="Pattern version", limit=32)
        version_ok = bool(_SEMVER.fullmatch(version))
    except DesignLearningLedgerError:
        version = ""
        version_ok = False
    checks.append(
        _check(
            "pattern-version", version_ok, "Pattern version must use semantic versioning.", version=version
        )
    )

    try:
        title = _nonempty_text(manifest.get("title"), label="Pattern title", limit=180)
        summary = _nonempty_text(manifest.get("summary"), label="Pattern summary", limit=1000)
        contracts = {
            "input": _text_list(manifest.get("input_contract"), label="Input contract"),
            "output": _text_list(manifest.get("output_contract"), label="Output contract"),
        }
        content_ok = bool(title and summary and contracts["input"] and contracts["output"])
    except DesignLearningLedgerError:
        title = ""
        summary = ""
        contracts = {"input": [], "output": []}
        content_ok = False
    checks.append(
        _check(
            "pattern-contract",
            content_ok,
            "Pattern title, summary, input contract and output contract must be explicit.",
        )
    )

    allowed_paths: list[str] = []
    path_error = ""
    try:
        raw_paths = _text_list(manifest.get("allowed_paths"), label="Pattern allowed_paths")
        allowed_paths = [_safe_relative(value, label="Pattern allowed path") for value in raw_paths]
        paths_ok = set(allowed_paths).issubset(changed_paths)
    except DesignLearningLedgerError as exc:
        paths_ok = False
        path_error = str(exc)
    checks.append(
        _check(
            "pattern-allowed-paths",
            paths_ok,
            "Every reusable pattern path must be an exact path changed and validated by this candidate.",
            allowed_paths=allowed_paths,
            changed_paths=sorted(changed_paths),
            error=path_error,
        )
    )

    regression_tests: list[str] = []
    test_error = ""
    try:
        raw_tests = _text_list(manifest.get("regression_tests"), label="Pattern regression_tests")
        regression_tests = [_safe_relative(value, label="Pattern regression test") for value in raw_tests]
        tests_ok = all(
            test_path.startswith("tests/") and (root / test_path).is_file() for test_path in regression_tests
        )
    except DesignLearningLedgerError as exc:
        tests_ok = False
        test_error = str(exc)
    checks.append(
        _check(
            "pattern-regression-tests",
            tests_ok,
            "Every proposed regression test must exist under tests/; the source-bound candidate and visual evidence record their prior execution context.",
            regression_tests=regression_tests,
            error=test_error,
        )
    )

    skill_target = ""
    target_error = ""
    try:
        skill_target = _safe_relative(manifest.get("proposed_skill_target"), label="Proposed skill target")
        target = (root / skill_target).resolve()
        suite_root = (root / "skills" / "aureon-harmonic-design-suite").resolve()
        target.relative_to(suite_root)
        target_ok = target.is_file() and target.suffix.lower() == ".md"
    except (DesignLearningLedgerError, ValueError) as exc:
        target_ok = False
        target_error = str(exc)
    checks.append(
        _check(
            "pattern-skill-target",
            target_ok,
            "A proposed skill target must be an existing Markdown source inside the local Harmonic Design Suite; this ledger never writes it.",
            proposed_skill_target=skill_target,
            error=target_error,
        )
    )

    try:
        refresh_by = _parse_refresh_deadline(manifest.get("refresh_by"), now=now)
        refresh_ok = True
    except DesignLearningLedgerError:
        refresh_by = ""
        refresh_ok = False
    checks.append(
        _check(
            "pattern-refresh-deadline",
            refresh_ok,
            "A bounded reusable pattern must carry a future source/evidence refresh deadline.",
            refresh_by=refresh_by,
        )
    )

    normalised = {
        "schema": LEARNING_MANIFEST_SCHEMA,
        "pattern_id": pattern_id,
        "version": version,
        "title": title,
        "summary": summary,
        "input_contract": contracts["input"],
        "output_contract": contracts["output"],
        "allowed_paths": allowed_paths,
        "regression_tests": regression_tests,
        "proposed_skill_target": skill_target,
        "refresh_by": refresh_by,
    }
    return normalised, checks


def validate_design_learning_record(
    candidate_receipt_path: Path,
    visual_review_path: Path,
    learning_manifest_path: Path,
    *,
    repo_root: Path | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Revalidate accepted staged evidence and produce a non-authoritative learning record."""

    root = _find_repo_root(repo_root)
    current = (now or datetime.now(UTC)).astimezone(UTC)
    candidate_path, candidate_relative = _resolve_input_path(
        root, candidate_receipt_path, label="Candidate receipt"
    )
    candidate = _read_json(candidate_path, label="Candidate receipt")
    candidate_root, candidate_root_relative = _candidate_root(root, candidate)
    _candidate_path_under_root(candidate_path, candidate_root, label="Candidate receipt")

    checks: list[dict[str, Any]] = []
    candidate_verification = verify_staged_candidate_receipt(candidate, repo_root=root)
    candidate_ok = (
        candidate.get("schema") == CANDIDATE_SCHEMA
        and candidate_verification.get("passed") is True
        and candidate_verification.get("release_eligible") is False
        and candidate_verification.get("deployment_authority") == "none"
    )
    checks.append(
        _check(
            "candidate-control-revalidated",
            candidate_ok,
            "The staged candidate must still satisfy its immutable work order, current tree, claims, scope and authority boundary.",
            verification_state=candidate_verification.get("state"),
        )
    )

    visual_path, visual_relative = _resolve_input_path(
        root, visual_review_path, label="Candidate visual-review receipt"
    )
    _candidate_path_under_root(visual_path, candidate_root, label="Candidate visual-review receipt")
    visual = _read_json(visual_path, label="Candidate visual-review receipt")
    visual_candidate_value = visual.get("candidate")
    visual_candidate: Mapping[str, Any] = (
        visual_candidate_value if isinstance(visual_candidate_value, Mapping) else {}
    )
    candidate_binding_value = visual_candidate.get("receipt")
    candidate_binding: Mapping[str, Any] = (
        candidate_binding_value if isinstance(candidate_binding_value, Mapping) else {}
    )
    candidate_summary_value = candidate.get("candidate")
    candidate_summary: Mapping[str, Any] = (
        candidate_summary_value if isinstance(candidate_summary_value, Mapping) else {}
    )
    visual_binding_ok = (
        visual.get("schema") == VISUAL_REVIEW_SCHEMA
        and visual.get("state") == "prepromotion-visual-review-passed"
        and visual.get("passed") is True
        and visual.get("release_eligible") is False
        and visual.get("package_authority") == "none"
        and visual.get("deployment_authority") == "none"
        and visual.get("canonical_promotion_authority") == "owner-controlled"
        and isinstance(candidate_binding, Mapping)
        and candidate_binding.get("path") == candidate_relative
        and candidate_binding.get("sha256") == _sha256_file(candidate_path)
        and visual_candidate.get("root") == candidate_root_relative
        and visual_candidate.get("website_path") == candidate_summary.get("website_path")
        and visual_candidate.get("control_tree_sha256") == candidate_summary.get("tree_sha256")
    )
    checks.append(
        _check(
            "visual-review-binding",
            visual_binding_ok,
            "Visual review must be a passing local pre-promotion review bound to this exact staged candidate without package or deployment authority.",
        )
    )

    visual_revalidation_ok = False
    visual_revalidation_error = ""
    evidence_value = visual.get("evidence")
    evidence: Mapping[str, Any] = evidence_value if isinstance(evidence_value, Mapping) else {}
    evidence_paths: dict[str, tuple[Path, str, str]] = {}
    try:
        for key in ("capture", "visual_receipt", "manual_pixel_review", "human_visual_acceptance"):
            evidence_paths[key] = _evidence_path(root, candidate_root, evidence, key)
        revalidated_visual = validate_candidate_visual_review(
            candidate_path,
            evidence_paths["capture"][0],
            evidence_paths["manual_pixel_review"][0],
            evidence_paths["human_visual_acceptance"][0],
            repo_root=root,
            now=current,
        )
        visual_revalidation_ok = (
            revalidated_visual.get("passed") is True
            and revalidated_visual.get("state") == "prepromotion-visual-review-passed"
            and revalidated_visual.get("candidate") == visual.get("candidate")
            and revalidated_visual.get("evidence") == visual.get("evidence")
            and revalidated_visual.get("release_eligible") is False
            and revalidated_visual.get("deployment_authority") == "none"
        )
    except Exception as exc:  # The verifier has its own strict error classes.
        visual_revalidation_error = f"{type(exc).__name__}: {exc}"
    checks.append(
        _check(
            "visual-review-revalidated",
            visual_revalidation_ok,
            "Capture, screenshot, manual pixel and named human acceptance evidence must still reproduce the passing review.",
            error=visual_revalidation_error,
        )
    )

    manifest_path, manifest_relative = _resolve_input_path(
        root, learning_manifest_path, label="Design-learning manifest"
    )
    _candidate_path_under_root(manifest_path, candidate_root, label="Design-learning manifest")
    changed_paths = {
        str(change.get("path") or "")
        for change in candidate.get("changes", [])
        if isinstance(change, Mapping) and str(change.get("change") or "") in {"added", "modified"}
    }
    pattern, manifest_checks = _load_pattern_manifest(
        manifest_path,
        root=root,
        candidate_root=candidate_root,
        now=current,
        changed_paths=changed_paths,
    )
    checks.extend(manifest_checks)

    passed = all(check["passed"] for check in checks)
    return {
        "schema": LEARNING_RECORD_SCHEMA,
        "recorded_at": _utc_iso(current),
        "state": "learning-proposal-recorded" if passed else "blocked",
        "passed": passed,
        "release_eligible": False,
        "package_authority": "none",
        "deployment_authority": "none",
        "authority": dict(AUTHORITY),
        "candidate": {
            "receipt": {"path": candidate_relative, "sha256": _sha256_file(candidate_path)},
            "root": candidate_root_relative,
            "website_path": candidate_summary.get("website_path"),
            "tree_sha256": candidate_summary.get("tree_sha256"),
        },
        "visual_review": {"path": visual_relative, "sha256": _sha256_file(visual_path)},
        "learning_manifest": {"path": manifest_relative, "sha256": _sha256_file(manifest_path)},
        "pattern": pattern,
        "promotion": {
            "state": "proposed-human-reviewed-skill-update" if passed else "not-proposed",
            "applied": False,
            "target": pattern.get("proposed_skill_target"),
            "authority": "A human-reviewed repository change is required; this ledger never applies it.",
        },
        "checks": checks,
        "next_gate": (
            "Review the proposed pattern, source freshness deadline and regression tests; "
            "only a separate human-reviewed repository change may update the Design Suite. "
            "Canonical promotion, packaging, backup, owner approval and deployment remain separate WebsiteOperator gates."
        ),
    }


def write_design_learning_record(
    record: Mapping[str, Any],
    output_path: Path,
    *,
    repo_root: Path | None = None,
) -> Path:
    """Write one append-only learning proposal beneath its staged candidate root."""

    root = _find_repo_root(repo_root)
    candidate = record.get("candidate") if isinstance(record, Mapping) else None
    if not isinstance(candidate, Mapping):
        raise DesignLearningLedgerError("Learning record must declare a staged candidate.")
    candidate_root, _ = _resolve_under(root, candidate.get("root"), label="Learning record candidate root")
    target = output_path.resolve() if output_path.is_absolute() else (root / output_path).resolve()
    _candidate_path_under_root(target, candidate_root, label="Learning record output")
    if target.suffix.lower() != ".json":
        raise DesignLearningLedgerError("Learning record output must use a .json filename.")
    if target.exists():
        raise DesignLearningLedgerError(f"Refusing to overwrite learning evidence: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aureon-design-learning-ledger",
        description="Record only source-bound, human-reviewed staged design patterns as local skill proposals.",
    )
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--candidate-receipt", type=Path, required=True)
    parser.add_argument("--visual-review", type=Path, required=True)
    parser.add_argument("--learning-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        record = validate_design_learning_record(
            args.candidate_receipt,
            args.visual_review,
            args.learning_manifest,
            repo_root=args.repo_root,
        )
        root = _find_repo_root(args.repo_root)
        output = write_design_learning_record(record, args.output, repo_root=root)
        print(
            json.dumps(
                {
                    "state": record["state"],
                    "passed": record["passed"],
                    "output": output.relative_to(root).as_posix(),
                    "release_eligible": False,
                    "deployment_authority": "none",
                },
                indent=2,
            )
        )
        return 0 if record["passed"] else 2
    except DesignLearningLedgerError as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
