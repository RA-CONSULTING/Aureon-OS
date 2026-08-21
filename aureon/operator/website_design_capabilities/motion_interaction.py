"""Audit purposeful motion and its equivalent reduced-motion path."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from .common import CapabilityInputError, CapabilityResult, finding, read_text

SKILL_ID = "motion_interaction"


def audit_motion(root: Path, source_paths: Sequence[str]) -> CapabilityResult:
    """Detect motion, purpose annotations, reduced-motion, and hostile patterns."""

    if not source_paths:
        raise CapabilityInputError("source_paths must be non-empty")
    evidence: list[str] = []
    sources: list[str] = []
    for item in source_paths:
        safe, source = read_text(root, item, suffixes={".html", ".css", ".js"})
        evidence.append(safe)
        sources.append(source)
    combined = "\n".join(sources)
    lowered = combined.lower()
    motion_count = len(re.findall(r"\b(?:animation|transition|requestanimationframe|gsap\.)\b", lowered))
    animation_names = re.findall(r"\banimation\s*:\s*([a-z][a-z0-9-]*)", lowered)
    purposeful_terms = (
        "assemble",
        "connect",
        "evidence",
        "field",
        "flow",
        "orbit",
        "progress",
        "pulse",
        "reveal",
        "route",
        "scan",
        "signal",
        "weave",
    )
    semantic_names = [name for name in animation_names if any(term in name for term in purposeful_terms)]
    purpose_count = (
        lowered.count("data-motion-purpose") + lowered.count("motion-purpose:") + len(semantic_names)
    )
    hostile: list[str] = []
    if "scroll-hijack" in lowered:
        hostile.append("scroll-hijack")
    if re.search(
        r"addeventlistener\s*\(\s*[\"'](?:wheel|touchmove)[\"'][\s\S]{0,800}?preventdefault\s*\(",
        lowered,
    ):
        hostile.append("wheel-or-touchmove-prevent-default")
    findings = (
        finding(
            "motion-detected", motion_count > 0, "At least one declared motion behaviour is inspectable."
        ),
        finding(
            "motion-purpose",
            motion_count == 0 or purpose_count > 0,
            "Motion has a documented structural purpose.",
        ),
        finding(
            "reduced-motion",
            motion_count == 0 or "prefers-reduced-motion" in lowered,
            "Motion provides a reduced-motion path.",
        ),
        finding(
            "no-scroll-hostility",
            not hostile,
            "No scroll-hijack marker was found."
            if not hostile
            else f"Hostile interaction markers: {', '.join(hostile)}.",
        ),
        finding(
            "bounded-infinite-motion",
            "infinite" not in lowered or "prefers-reduced-motion" in lowered,
            "Infinite motion is absent or guarded by reduced-motion.",
        ),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(evidence),
        metrics={"motion_markers": motion_count, "purpose_markers": purpose_count},
    )
