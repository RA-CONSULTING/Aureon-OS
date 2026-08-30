"""Audit responsive layout, reading structure, and typography markers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from .common import CapabilityInputError, CapabilityResult, finding, read_text

SKILL_ID = "layout_typography_grid"


def audit_layout(
    root: Path,
    html_paths: Sequence[str],
    stylesheet_paths: Sequence[str],
) -> CapabilityResult:
    """Check viewport/read-order markers plus responsive grid and type controls."""

    if not html_paths or not stylesheet_paths:
        raise CapabilityInputError("html_paths and stylesheet_paths must both be non-empty")
    evidence: list[str] = []
    html_sources: list[tuple[str, str]] = []
    css_sources: list[tuple[str, str]] = []
    for item in html_paths:
        safe, source = read_text(root, item, suffixes={".html", ".htm"})
        evidence.append(safe)
        html_sources.append((safe, source.lower()))
    for item in stylesheet_paths:
        safe, source = read_text(root, item, suffixes={".css"})
        evidence.append(safe)
        css_sources.append((safe, source.lower()))
    missing_viewport = [
        safe
        for safe, source in html_sources
        if 'name="viewport"' not in source and "name='viewport'" not in source
    ]
    missing_main = [safe for safe, source in html_sources if "<main" not in source]
    css = "\n".join(source for _, source in css_sources)
    findings = (
        finding(
            "viewport-meta",
            not missing_viewport,
            "Every page declares a viewport."
            if not missing_viewport
            else f"Missing viewport: {', '.join(missing_viewport)}.",
        ),
        finding(
            "main-reading-order",
            not missing_main,
            "Every page exposes one semantic main region."
            if not missing_main
            else f"Missing main: {', '.join(missing_main)}.",
        ),
        finding(
            "responsive-breakpoint", "@media" in css, "Styles include at least one responsive media query."
        ),
        finding(
            "responsive-type",
            "clamp(" in css or "rem" in css,
            "Typography uses scalable units or a fluid clamp.",
        ),
        finding(
            "grid-system", "display: grid" in css or "display:grid" in css, "Styles define a CSS grid layout."
        ),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(evidence),
        metrics={"page_count": len(html_sources), "stylesheet_count": len(css_sources)},
    )
