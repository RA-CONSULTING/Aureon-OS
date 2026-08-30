"""Validate a visual-regression manifest and its externally measured diffs."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path

from .common import (
    CapabilityInputError,
    CapabilityResult,
    finding,
    read_text,
    require_mapping,
    require_safe_relative_path,
    sha256_file,
)

SKILL_ID = "design_qa_visual_regression"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def evaluate_visual_regression(root: Path, manifest_path: str) -> CapabilityResult:
    """Verify artifact hashes, viewport coverage, and measured difference limits."""

    manifest_safe, source = read_text(root, manifest_path, suffixes={".json"})
    try:
        raw = json.loads(source)
    except json.JSONDecodeError as exc:
        raise CapabilityInputError("visual regression manifest must be valid JSON") from exc
    manifest = require_mapping(raw, "visual regression manifest")
    cases = manifest.get("cases")
    if not isinstance(cases, list) or not cases:
        raise CapabilityInputError("visual regression cases must be a non-empty list")
    evidence = [manifest_safe]
    ids: list[str] = []
    hash_mismatch: list[str] = []
    regression: list[str] = []
    missing_matrix: list[str] = []
    for index, value in enumerate(cases):
        row = require_mapping(value, f"cases[{index}]")
        case_id = row.get("id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            raise CapabilityInputError("visual case ids must be unique non-empty strings")
        ids.append(case_id)
        baseline = require_safe_relative_path(row.get("baseline"), f"cases[{index}].baseline")
        current = require_safe_relative_path(row.get("current"), f"cases[{index}].current")
        baseline_hash, _ = sha256_file(root, baseline)
        current_hash, _ = sha256_file(root, current)
        declared_baseline = row.get("baseline_sha256")
        declared_current = row.get("current_sha256")
        if (
            not isinstance(declared_baseline, str)
            or not _SHA256.fullmatch(declared_baseline)
            or not isinstance(declared_current, str)
            or not _SHA256.fullmatch(declared_current)
        ):
            raise CapabilityInputError("visual case hashes must be lowercase SHA-256")
        if baseline_hash != declared_baseline or current_hash != declared_current:
            hash_mismatch.append(case_id)
        ratio = row.get("difference_ratio")
        threshold = row.get("threshold")
        if (
            not isinstance(ratio, (int, float))
            or isinstance(ratio, bool)
            or not 0 <= ratio <= 1
            or not isinstance(threshold, (int, float))
            or isinstance(threshold, bool)
            or not 0 <= threshold <= 1
        ):
            raise CapabilityInputError("difference_ratio and threshold must be numbers from zero to one")
        if float(ratio) > float(threshold):
            regression.append(case_id)
        viewport = row.get("viewport")
        if (
            not isinstance(viewport, Mapping)
            or not isinstance(viewport.get("width"), int)
            or not isinstance(viewport.get("height"), int)
            or row.get("javascript") not in {"enabled", "disabled"}
        ):
            missing_matrix.append(case_id)
        evidence.extend((f"{baseline}#sha256={baseline_hash}", f"{current}#sha256={current_hash}"))
    findings = (
        finding(
            "visual-artifact-integrity",
            not hash_mismatch,
            "Visual artifacts match their declared hashes."
            if not hash_mismatch
            else f"Visual hash mismatch: {', '.join(hash_mismatch)}.",
        ),
        finding(
            "visual-diff-threshold",
            not regression,
            "All measured visual diffs are within threshold."
            if not regression
            else f"Visual regressions: {', '.join(regression)}.",
        ),
        finding(
            "visual-matrix-completeness",
            not missing_matrix,
            "Every case declares viewport and JavaScript state."
            if not missing_matrix
            else f"Incomplete visual cases: {', '.join(missing_matrix)}.",
        ),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(evidence),
        metrics={"case_count": len(ids), "regression_count": len(regression)},
    )
