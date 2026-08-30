"""Audit semantic fallbacks for system diagrams and connectome graphics."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from .common import CapabilityInputError, CapabilityResult, finding, read_text

SKILL_ID = "diagram_connectome_graphics"
_FIGURE = re.compile(r"<figure\b[^>]*data-system-diagram[^>]*>(.*?)</figure>", re.IGNORECASE | re.DOTALL)


def audit_diagram_fallbacks(root: Path, html_paths: Sequence[str]) -> CapabilityResult:
    """Require labelled figures, text fallback, and non-colour-only semantics."""

    if not html_paths:
        raise CapabilityInputError("html_paths must be non-empty")
    evidence: list[str] = []
    total = 0
    missing_caption: list[str] = []
    missing_fallback: list[str] = []
    colour_only: list[str] = []
    for item in html_paths:
        safe, source = read_text(root, item, suffixes={".html", ".htm"})
        evidence.append(safe)
        figures = _FIGURE.findall(source)
        total += len(figures)
        for ordinal, figure in enumerate(figures, start=1):
            location = f"{safe}#diagram-{ordinal}"
            lowered = figure.lower()
            if "<figcaption" not in lowered:
                missing_caption.append(location)
            if (
                "data-diagram-fallback" not in lowered
                and 'class="diagram-fallback' not in lowered
                and "class='diagram-fallback" not in lowered
            ):
                missing_fallback.append(location)
            if "data-edge-label" not in lowered and "aria-label" not in lowered:
                colour_only.append(location)
    findings = (
        finding("diagram-present", total > 0, "At least one declared system diagram is inspectable."),
        finding(
            "diagram-caption",
            not missing_caption,
            "Every diagram has a figcaption."
            if not missing_caption
            else f"Missing captions: {', '.join(missing_caption)}.",
        ),
        finding(
            "diagram-text-fallback",
            not missing_fallback,
            "Every diagram has a semantic text fallback."
            if not missing_fallback
            else f"Missing fallbacks: {', '.join(missing_fallback)}.",
        ),
        finding(
            "diagram-labelled-relations",
            not colour_only,
            "Every diagram labels relationships beyond colour."
            if not colour_only
            else f"Potential colour-only relations: {', '.join(colour_only)}.",
        ),
    )
    return CapabilityResult(SKILL_ID, findings, evidence=tuple(evidence), metrics={"diagram_count": total})
