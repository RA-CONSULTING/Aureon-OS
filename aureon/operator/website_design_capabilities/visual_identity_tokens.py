"""Audit the source-controlled CSS token system."""

from __future__ import annotations

import re
from pathlib import Path

from .common import CapabilityResult, finding, read_text

SKILL_ID = "visual_identity_tokens"
_TOKEN = re.compile(r"(--[a-z0-9-]+)\s*:\s*([^;{}]+);", re.IGNORECASE)
_FAMILY_ALIASES = {
    "colour": ("color", "page", "surface", "text", "muted", "line", "mint", "cyan", "violet", "amber"),
    "typography": ("font", "type", "leading", "tracking"),
    "spacing": ("space", "gap", "gutter"),
    "radius": ("radius",),
}


def audit_tokens(root: Path, stylesheet_path: str) -> CapabilityResult:
    """Inspect token coverage, duplicate definitions, and raw hex colour drift."""

    safe, css = read_text(root, stylesheet_path, suffixes={".css"})
    definitions = _TOKEN.findall(css)
    names = [name.lower() for name, _ in definitions]
    duplicate_names = sorted({name for name in names if names.count(name) > 1})
    missing_families = [
        family
        for family, aliases in _FAMILY_ALIASES.items()
        if not any(any(name.startswith(f"--{alias}") for alias in aliases) for name in names)
    ]
    hex_literals = re.findall(r"#[0-9a-fA-F]{3,8}\b", css)
    findings = (
        finding(
            "tokens-present",
            bool(definitions),
            "CSS must define source-controlled custom properties.",
            location=safe,
        ),
        finding(
            "required-token-families",
            not missing_families,
            "Required token families are present."
            if not missing_families
            else f"Missing token families: {', '.join(missing_families)}.",
            location=safe,
            warning=True,
        ),
        finding(
            "unique-token-names",
            not duplicate_names,
            "Token names are unique."
            if not duplicate_names
            else f"Duplicate tokens: {', '.join(duplicate_names)}.",
            location=safe,
            warning=True,
        ),
        finding(
            "colour-token-ratio",
            len(hex_literals) <= max(4, len([name for name in names if "color" in name]) * 2),
            "Raw colour literals remain bounded relative to colour tokens.",
            location=safe,
            warning=True,
        ),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=(safe,),
        metrics={"token_count": len(definitions), "raw_hex_literals": len(hex_literals)},
    )
