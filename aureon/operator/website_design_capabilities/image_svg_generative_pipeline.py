"""Audit route-scoped rights, alt text, hashes, and visual asset footprint."""

from __future__ import annotations

import json
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

SKILL_ID = "image_svg_generative_pipeline"
_PUBLIC_RIGHTS = {"owned", "licensed", "authorised-route-scoped", "public-domain"}
_SUFFIXES = {".avif", ".gif", ".jpg", ".jpeg", ".png", ".svg", ".webp"}


def audit_image_inventory(
    root: Path, inventory_path: str, *, max_total_bytes: int = 5_000_000
) -> CapabilityResult:
    """Verify every inventoried visual against rights, accessibility, and bytes."""

    if max_total_bytes <= 0:
        raise CapabilityInputError("max_total_bytes must be positive")
    safe_inventory, source = read_text(root, inventory_path, suffixes={".json"})
    try:
        raw = json.loads(source)
    except json.JSONDecodeError as exc:
        raise CapabilityInputError("image inventory must be valid JSON") from exc
    root_object = require_mapping(raw, "image inventory")
    assets = root_object.get("assets")
    if not isinstance(assets, list) or not assets:
        raise CapabilityInputError("image inventory assets must be a non-empty list")
    evidence = [safe_inventory]
    rights_blocked: list[str] = []
    alt_blocked: list[str] = []
    hashes_blocked: list[str] = []
    total_bytes = 0
    asset_ids: list[str] = []
    for index, value in enumerate(assets):
        row = require_mapping(value, f"assets[{index}]")
        asset_id = row.get("id")
        if not isinstance(asset_id, str) or not asset_id or asset_id in asset_ids:
            raise CapabilityInputError("asset ids must be unique non-empty strings")
        asset_ids.append(asset_id)
        relative = require_safe_relative_path(row.get("path"), f"assets[{index}].path")
        if Path(relative).suffix.lower() not in _SUFFIXES:
            raise CapabilityInputError(f"unsupported visual asset type: {relative}")
        digest, size = sha256_file(root, relative)
        total_bytes += size
        evidence.append(f"{relative}#sha256={digest}")
        rights = row.get("rights")
        route_scope = row.get("route_scope")
        if (
            rights not in _PUBLIC_RIGHTS
            or not isinstance(route_scope, list)
            or not route_scope
            or not all(isinstance(route, str) and route.startswith("/") for route in route_scope)
        ):
            rights_blocked.append(asset_id)
        alt = row.get("alt")
        decorative = row.get("decorative") is True
        if not decorative and (not isinstance(alt, str) or not alt.strip()):
            alt_blocked.append(asset_id)
        declared_digest = row.get("sha256")
        if declared_digest is not None and declared_digest != digest:
            hashes_blocked.append(asset_id)
    findings = (
        finding(
            "route-scoped-rights",
            not rights_blocked,
            "All visual assets have public route-scoped rights."
            if not rights_blocked
            else f"Rights blocked: {', '.join(rights_blocked)}.",
        ),
        finding(
            "asset-alt-text",
            not alt_blocked,
            "All informative visual assets have alt text."
            if not alt_blocked
            else f"Alt text missing: {', '.join(alt_blocked)}.",
        ),
        finding(
            "asset-hash-integrity",
            not hashes_blocked,
            "Declared asset hashes match source files."
            if not hashes_blocked
            else f"Hash mismatch: {', '.join(hashes_blocked)}.",
        ),
        finding(
            "asset-footprint-budget",
            total_bytes <= max_total_bytes,
            f"Visual assets total {total_bytes} bytes against a {max_total_bytes}-byte budget.",
        ),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(evidence),
        metrics={"asset_count": len(asset_ids), "total_bytes": total_bytes, "budget_bytes": max_total_bytes},
        publishable_ids=tuple(asset_ids)
        if not rights_blocked and not alt_blocked and not hashes_blocked
        else (),
    )
