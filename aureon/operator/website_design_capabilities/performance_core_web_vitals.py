"""Audit static asset budgets and validate captured Core Web Vitals."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path

from .common import (
    CapabilityInputError,
    CapabilityResult,
    finding,
    require_safe_relative_path,
    resolve_readonly_file,
)

SKILL_ID = "performance_core_web_vitals"
_GROUPS = {
    ".css": "css_bytes",
    ".js": "javascript_bytes",
    ".avif": "image_bytes",
    ".gif": "image_bytes",
    ".jpg": "image_bytes",
    ".jpeg": "image_bytes",
    ".png": "image_bytes",
    ".svg": "image_bytes",
    ".webp": "image_bytes",
}
_VITAL_LIMITS = {"lcp_ms": 2500.0, "inp_ms": 200.0, "cls": 0.1}


def audit_performance(
    root: Path,
    asset_paths: Sequence[str],
    budgets: Mapping[str, int],
    live_vitals: Mapping[str, float] | None = None,
) -> CapabilityResult:
    """Measure source bytes and validate an optional externally captured vitals row."""

    if not asset_paths:
        raise CapabilityInputError("asset_paths must be non-empty")
    allowed_budgets = {"total_bytes", "css_bytes", "javascript_bytes", "image_bytes"}
    if (
        not budgets
        or set(budgets) - allowed_budgets
        or any(not isinstance(value, int) or value <= 0 for value in budgets.values())
    ):
        raise CapabilityInputError("budgets must contain positive integer values for supported byte groups")
    totals = dict.fromkeys(allowed_budgets, 0)
    evidence: list[str] = []
    for item in asset_paths:
        safe = require_safe_relative_path(item)
        path = resolve_readonly_file(root, safe, max_bytes=50_000_000)
        size = path.stat().st_size
        totals["total_bytes"] += size
        group = _GROUPS.get(path.suffix.lower())
        if group is not None:
            totals[group] += size
        evidence.append(f"{safe}#bytes={size}")
    budget_failures = [name for name, limit in budgets.items() if totals[name] > limit]
    findings = [
        finding(
            "static-asset-budgets",
            not budget_failures,
            "All supplied static asset budgets pass."
            if not budget_failures
            else f"Exceeded budgets: {', '.join(sorted(budget_failures))}.",
        ),
    ]
    if live_vitals is None:
        findings.append(
            finding(
                "live-vitals-evidence",
                False,
                "No live LCP, INP, and CLS capture was supplied; collect it before release.",
            )
        )
    else:
        if set(live_vitals) != set(_VITAL_LIMITS) or any(
            not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0
            for value in live_vitals.values()
        ):
            raise CapabilityInputError(
                "live_vitals must contain non-negative numeric lcp_ms, inp_ms, and cls"
            )
        vital_failures = [name for name, limit in _VITAL_LIMITS.items() if float(live_vitals[name]) > limit]
        findings.append(
            finding(
                "live-vitals-thresholds",
                not vital_failures,
                "Captured Core Web Vitals meet the good thresholds."
                if not vital_failures
                else f"Vitals above threshold: {', '.join(vital_failures)}.",
            )
        )
        evidence.append("live-vitals:externally-captured-input")
    metrics: dict[str, str | int | float | bool] = dict(totals)
    if live_vitals is not None:
        metrics.update({name: float(value) for name, value in live_vitals.items()})
    return CapabilityResult(SKILL_ID, tuple(findings), evidence=tuple(evidence), metrics=metrics)
