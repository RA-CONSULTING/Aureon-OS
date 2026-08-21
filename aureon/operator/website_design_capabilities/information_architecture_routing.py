"""Audit sitemap, canonical, navigation, and local-route coherence."""

from __future__ import annotations

import posixpath
import re
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from .common import CapabilityInputError, CapabilityResult, finding, read_text

SKILL_ID = "information_architecture_routing"
_CANONICAL = re.compile(r"<link\b[^>]*rel=[\"']canonical[\"'][^>]*href=[\"']([^\"']+)", re.IGNORECASE)
_HREF = re.compile(r"\bhref=[\"']([^\"']+)[\"']", re.IGNORECASE)


def _route_for_html(path: str) -> str:
    pure = PurePosixPath(path)
    if pure.name == "index.html":
        parent = pure.parent.as_posix()
        return "/" if parent == "." else f"/{parent.strip('/')}/"
    return f"/{pure.as_posix()}"


def _route_exists(root: Path, route: str) -> bool:
    path = PurePosixPath(route.lstrip("/"))
    if ".." in path.parts:
        return False
    candidates = [root / Path(*path.parts)]
    if route.endswith("/") or not path.suffix:
        candidates.append(root / Path(*path.parts) / "index.html")
    root_resolved = root.resolve(strict=True)
    for candidate in candidates:
        try:
            resolved = candidate.resolve(strict=True)
            resolved.relative_to(root_resolved)
        except (FileNotFoundError, ValueError):
            continue
        if resolved.is_file():
            return True
    return False


def audit_routing(root: Path, sitemap_path: str, html_paths: Sequence[str]) -> CapabilityResult:
    """Cross-check canonical URLs, sitemap routes, and unresolved internal links."""

    if not html_paths:
        raise CapabilityInputError("html_paths must be non-empty")
    sitemap_safe, sitemap_source = read_text(root, sitemap_path, suffixes={".xml"})
    try:
        xml_root = ET.fromstring(sitemap_source)
    except ET.ParseError as exc:
        raise CapabilityInputError("sitemap must be valid XML") from exc
    sitemap_routes = {
        urlparse(element.text.strip()).path
        for element in xml_root.iter()
        if element.tag.endswith("loc") and isinstance(element.text, str) and element.text.strip()
    }
    evidence = [sitemap_safe]
    expected_routes: set[str] = set()
    canonical_routes: list[str] = []
    internal_links: list[str] = []
    missing_canonical: list[str] = []
    for item in html_paths:
        safe, source = read_text(root, item, suffixes={".html", ".htm"})
        evidence.append(safe)
        expected_routes.add(_route_for_html(safe))
        matches = _CANONICAL.findall(source)
        if len(matches) != 1:
            missing_canonical.append(safe)
        else:
            canonical_routes.append(urlparse(matches[0]).path)
        page_route = _route_for_html(safe)
        page_base = page_route if page_route.endswith("/") else f"{posixpath.dirname(page_route)}/"
        for href in _HREF.findall(source):
            parsed = urlparse(href)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            if parsed.path.startswith("/"):
                route = parsed.path
            else:
                route = "/" + posixpath.normpath(posixpath.join(page_base.lstrip("/"), parsed.path)).lstrip(
                    "/"
                )
            if parsed.path.endswith("/") and not route.endswith("/"):
                route += "/"
            internal_links.append(route)
    missing_sitemap = sorted(expected_routes - sitemap_routes)
    canonical_mismatch = sorted(set(canonical_routes) - expected_routes)
    unresolved = sorted({link for link in internal_links if not _route_exists(root, link)})
    findings = (
        finding(
            "one-canonical-per-page",
            not missing_canonical,
            "Every page has exactly one canonical link."
            if not missing_canonical
            else f"Canonical count invalid: {', '.join(missing_canonical)}.",
        ),
        finding(
            "canonical-route-match",
            not canonical_mismatch,
            "Canonical paths map to supplied pages."
            if not canonical_mismatch
            else f"Unmapped canonical paths: {', '.join(canonical_mismatch)}.",
        ),
        finding(
            "sitemap-coverage",
            not missing_sitemap,
            "Every supplied page route appears in the sitemap."
            if not missing_sitemap
            else f"Routes absent from sitemap: {', '.join(missing_sitemap)}.",
        ),
        finding(
            "internal-route-resolution",
            not unresolved,
            "All root-relative links resolve within the supplied site root."
            if not unresolved
            else f"Unresolved routes: {', '.join(unresolved)}.",
        ),
    )
    return CapabilityResult(
        SKILL_ID,
        findings,
        evidence=tuple(evidence),
        metrics={
            "route_count": len(expected_routes),
            "sitemap_route_count": len(sitemap_routes),
            "internal_link_count": len(internal_links),
        },
    )
