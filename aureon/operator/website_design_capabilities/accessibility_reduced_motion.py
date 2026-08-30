"""Prepare a deterministic static accessibility and reduced-motion audit."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from .common import CapabilityInputError, CapabilityResult, finding, read_text

SKILL_ID = "accessibility_reduced_motion"
_IMG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_BUTTON = re.compile(r"<button\b([^>]*)>(.*?)</button>", re.IGNORECASE | re.DOTALL)


def prepare_accessibility_audit(
    root: Path, html_paths: Sequence[str], stylesheet_paths: Sequence[str]
) -> CapabilityResult:
    """Inspect static semantics and emit the required manual-test evidence plan."""

    if not html_paths or not stylesheet_paths:
        raise CapabilityInputError("html_paths and stylesheet_paths must both be non-empty")
    evidence: list[str] = []
    semantic_failures: list[str] = []
    image_failures: list[str] = []
    button_failures: list[str] = []
    positive_tabindex: list[str] = []
    static_reading_failures: list[str] = []
    for item in html_paths:
        safe, source = read_text(root, item, suffixes={".html", ".htm"})
        evidence.append(safe)
        lowered = source.lower()
        if (
            "<html" not in lowered
            or not re.search(r"<html\b[^>]*\blang=[\"'][^\"']+", source, re.IGNORECASE)
            or "<title>" not in lowered
            or "<main" not in lowered
        ):
            semantic_failures.append(safe)
        if any(not re.search(r"\balt=[\"'][^\"']*[\"']", tag, re.IGNORECASE) for tag in _IMG.findall(source)):
            image_failures.append(safe)
        for attrs, body in _BUTTON.findall(source):
            visible = re.sub(r"<[^>]+>", "", body).strip()
            if not visible and not re.search(r"\baria-label=[\"'][^\"']+", attrs, re.IGNORECASE):
                button_failures.append(safe)
                break
        if re.search(r"\btabindex=[\"']?[1-9]\d*", source, re.IGNORECASE):
            positive_tabindex.append(safe)
        main_match = re.search(r"<main\b[^>]*>(.*?)</main>", source, re.IGNORECASE | re.DOTALL)
        main_text = re.sub(r"<[^>]+>", " ", main_match.group(1) if main_match else "")
        if len(" ".join(main_text.split())) < 20:
            static_reading_failures.append(safe)
    css_sources: list[str] = []
    for item in stylesheet_paths:
        safe, source = read_text(root, item, suffixes={".css"})
        evidence.append(safe)
        css_sources.append(source.lower())
    css = "\n".join(css_sources)
    findings = (
        finding(
            "document-semantics",
            not semantic_failures,
            "Pages expose language, title, and main semantics."
            if not semantic_failures
            else f"Semantic shell incomplete: {', '.join(sorted(set(semantic_failures)))}.",
        ),
        finding(
            "image-alternatives",
            not image_failures,
            "Every image declares alt text, including empty alt for decorative images."
            if not image_failures
            else f"Images without alt: {', '.join(sorted(set(image_failures)))}.",
        ),
        finding(
            "button-names",
            not button_failures,
            "Every button has a visible or accessible name."
            if not button_failures
            else f"Unnamed buttons: {', '.join(sorted(set(button_failures)))}.",
        ),
        finding(
            "natural-tab-order",
            not positive_tabindex,
            "No positive tabindex disrupts document order."
            if not positive_tabindex
            else f"Positive tabindex: {', '.join(sorted(set(positive_tabindex)))}.",
        ),
        finding(
            "no-javascript-reading",
            not static_reading_failures,
            "Every page retains meaningful main content without JavaScript."
            if not static_reading_failures
            else f"Static main content is missing or too thin: {', '.join(sorted(set(static_reading_failures)))}.",
        ),
        finding("focus-visible", ":focus-visible" in css, "Styles preserve a visible keyboard focus state."),
        finding(
            "reduced-motion-css", "prefers-reduced-motion" in css, "Styles define a reduced-motion path."
        ),
    )
    manual_plan = (
        "manual:keyboard-route-and-dialog-flow",
        "manual:contrast-at-rendered-state",
        "manual:screen-reader-landmarks-and-names",
        "manual:reduced-motion-operating-system-setting",
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(evidence) + manual_plan,
        metrics={"page_count": len(html_paths), "manual_checks_required": len(manual_plan)},
    )
