#!/usr/bin/env python3
"""Static-site auditor for `website/` — correctness · SEO · a11y · perf.

Pure standard library (`html.parser`, `json`, `xml`, `re`). Walks every HTML page under the
site root, resolves every internal link/asset against the filesystem, and cross-checks the SEO
surfaces (titles, canonicals, `sitemap.xml`, `robots.txt`) and accessibility/perf basics.

Findings are graded: **ERROR** fails the run (exit non-zero); **WARN** is advisory. Run it before
building the home.pl package so a broken link or a sitemap drift can never ship.

    python -m scripts.website.audit_site [--root website] [--json]

The auditor is deterministic (sorted walk) and never modifies anything.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

CANONICAL_HOST = "aureonzorzatechnologies.pl"
CANONICAL_ORIGIN = f"https://{CANONICAL_HOST}"
REQUIRED_ROOT_FILES = ("index.html", "styles.css", "script.js", "robots.txt", "sitemap.xml")
_RASTER_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}
_BIG_RASTER_BYTES = 200 * 1024
_EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:", "javascript:")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Finding:
    level: str  # "ERROR" | "WARN"
    page: str   # site-relative path, e.g. "projects/aioa-core/index.html"
    check: str
    message: str

    def to_dict(self) -> dict:
        return {"level": self.level, "page": self.page, "check": self.check, "message": self.message}


class _PageParser(HTMLParser):
    """Collect the elements the audit needs from one HTML page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang: str | None = None
        self.has_html_tag = False
        self.title: str | None = None
        self.meta_description: str | None = None
        self.meta_robots: str = ""
        self.canonical: str | None = None
        self.og_url: str | None = None
        self.preload_images = 0
        self.h1_count = 0
        self.has_main_content = False
        self.is_js_detail = False  # JS-rendered detail page (heading injected at runtime)
        self.imgs: list[dict] = []            # {src, alt(has/empty), loading, decoding}
        self.anchors: list[dict] = []         # {href, target, rel}
        self.asset_refs: list[str] = []       # link/script/source src|href (+ img src, srcset firsts)
        self.jsonld: list[str] = []
        self._capture: str | None = None      # "title" | "h1" | "jsonld"
        self._buf: list[str] = []

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _attr(attrs: list[tuple[str, str | None]], name: str) -> str | None:
        for k, v in attrs:
            if k == name:
                return v if v is not None else ""
        return None

    def _has_attr(self, attrs, name) -> bool:
        return any(k == name for k, _ in attrs)

    # -- parser hooks -------------------------------------------------------
    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "html":
            self.has_html_tag = True
            self.html_lang = self._attr(attrs, "lang")
        elif tag == "title":
            self._capture, self._buf = "title", []
        elif tag == "h1":
            self.h1_count += 1
            self._capture, self._buf = "h1", []
        elif tag == "meta":
            name = (self._attr(attrs, "name") or "").lower()
            prop = (self._attr(attrs, "property") or "").lower()
            content = self._attr(attrs, "content") or ""
            if name == "description":
                self.meta_description = content
            elif name == "robots":
                self.meta_robots = content.lower()
            elif prop == "og:url":
                self.og_url = content
        elif tag == "link":
            rel = (self._attr(attrs, "rel") or "").lower()
            href = self._attr(attrs, "href") or ""
            if rel == "canonical":
                self.canonical = href
            if rel == "preload" and (self._attr(attrs, "as") or "") == "image":
                self.preload_images += 1
            if rel in {"stylesheet", "icon", "preload", "apple-touch-icon"} and href:
                self.asset_refs.append(href)
        elif tag == "script":
            src = self._attr(attrs, "src")
            if src:
                self.asset_refs.append(src)
            if (self._attr(attrs, "type") or "").lower() == "application/ld+json":
                self._capture, self._buf = "jsonld", []
        elif tag == "img":
            src = self._attr(attrs, "src") or ""
            self.imgs.append({
                "src": src,
                "has_alt": self._has_attr(attrs, "alt"),
                "alt": self._attr(attrs, "alt") or "",
                "loading": self._attr(attrs, "loading"),
                "decoding": self._attr(attrs, "decoding"),
            })
            if src:
                self.asset_refs.append(src)
            srcset = self._attr(attrs, "srcset")
            if srcset:
                for part in srcset.split(","):
                    url = part.strip().split(" ")[0].strip()
                    if url:
                        self.asset_refs.append(url)
        elif tag == "source":
            for key in ("src", "srcset"):
                val = self._attr(attrs, key)
                if val:
                    self.asset_refs.append(val.split(",")[0].strip().split(" ")[0].strip())
        elif tag == "a":
            self.anchors.append({
                "href": self._attr(attrs, "href") or "",
                "target": (self._attr(attrs, "target") or "").lower(),
                "rel": (self._attr(attrs, "rel") or "").lower(),
            })
        if (self._attr(attrs, "id") or "") == "main-content":
            self.has_main_content = True
        # JS-rendered detail pages inject their <h1> at runtime from data/*.json
        if self._has_attr(attrs, "data-project-detail"):
            self.is_js_detail = True
        if tag == "body" and self._has_attr(attrs, "data-project-slug"):
            self.is_js_detail = True

    def handle_endtag(self, tag: str) -> None:
        if self._capture and tag in {"title", "h1", "script"}:
            text = "".join(self._buf).strip()
            if self._capture == "title" and tag == "title":
                self.title = text
            elif self._capture == "h1" and tag == "h1":
                pass  # count only
            elif self._capture == "jsonld" and tag == "script":
                self.jsonld.append(text)
            self._capture, self._buf = None, []

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._buf.append(data)


# ---------------------------------------------------------------------------
# link / asset resolution
# ---------------------------------------------------------------------------


def _strip_target(href: str) -> str:
    return href.split("#", 1)[0].split("?", 1)[0].strip()


def _is_external(href: str) -> bool:
    low = href.lower()
    return low.startswith(_EXTERNAL_SCHEMES) or low.startswith("//")


def _resolve(root: Path, page: Path, href: str) -> Path | None:
    """Resolve an internal href/src to a filesystem path (or None if it exists as-is/dir)."""
    target = _strip_target(href)
    if not target:
        return None
    if target.startswith("/"):
        base = posixpath.normpath(target.lstrip("/"))
        fs = root / base
    else:
        page_dir = page.parent.relative_to(root).as_posix()
        joined = posixpath.normpath(posixpath.join(page_dir, target))
        fs = root / joined
    # directory-style link → its index.html
    if href.rstrip().endswith("/") or (fs.suffix == "" and not fs.is_file()):
        return fs / "index.html"
    return fs


def _page_url(root: Path, page: Path) -> str:
    rel = page.relative_to(root).as_posix()
    if page.name == "index.html":
        parent = posixpath.dirname(rel)
        return f"{CANONICAL_ORIGIN}/" if not parent else f"{CANONICAL_ORIGIN}/{parent}/"
    return f"{CANONICAL_ORIGIN}/{rel}"


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------


def audit(root: Path) -> list[Finding]:
    """Audit the static site at ``root`` and return all findings (sorted, deterministic)."""
    root = root.resolve()
    findings: list[Finding] = []

    def add(level: str, page: Path | str, check: str, message: str) -> None:
        page_str = page if isinstance(page, str) else page.relative_to(root).as_posix()
        findings.append(Finding(level, page_str, check, message))

    # required root files
    for name in REQUIRED_ROOT_FILES:
        if not (root / name).is_file():
            add("ERROR", name, "root-file", f"required root file missing: {name}")

    # data JSON validity
    data_dir = root / "data"
    if data_dir.is_dir():
        for jf in sorted(data_dir.glob("*.json")):
            try:
                json.loads(jf.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                add("ERROR", jf, "json", f"invalid JSON: {exc}")

    # CSS url(...) asset resolution
    for css in sorted(root.rglob("*.css")):
        text = css.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", text):
            ref = m.group(1).strip()
            if _is_external(ref) or ref.startswith("data:"):
                continue
            resolved = _resolve(root, css, ref)
            if resolved is not None and not resolved.exists():
                add("ERROR", css, "css-asset", f"missing asset referenced in CSS: {ref}")

    pages = sorted(root.rglob("*.html"))
    indexable_urls: set[str] = set()

    for page in pages:
        parser = _PageParser()
        try:
            parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001
            add("ERROR", page, "parse", f"HTML parse failed: {exc}")
            continue

        noindex = "noindex" in parser.meta_robots

        # --- a11y ----------------------------------------------------------
        if not parser.html_lang:
            add("ERROR", page, "a11y-lang", "<html> is missing a non-empty lang attribute")
        for img in parser.imgs:
            if not img["has_alt"]:
                add("ERROR", page, "a11y-img-alt", f"<img> without alt attribute: {img['src'] or '(no src)'}")
        if not parser.is_js_detail and parser.h1_count != 1:
            add("WARN", page, "a11y-h1", f"expected exactly one <h1>, found {parser.h1_count}")
        has_skip_to_main = any(a["href"].strip() == "#main-content" for a in parser.anchors)
        if has_skip_to_main and not parser.has_main_content:
            add("ERROR", page, "a11y-skip-target",
                'skip link targets #main-content but no element has id="main-content"')

        # --- links / assets ------------------------------------------------
        for a in parser.anchors:
            href = a["href"]
            if not href or _is_external(href):
                if a["target"] == "_blank" and "noopener" not in a["rel"]:
                    add("ERROR", page, "a11y-noopener",
                        f'target="_blank" link without rel="noopener": {href}')
                continue
            if href.startswith("#"):
                continue
            resolved = _resolve(root, page, href)
            if resolved is not None and not resolved.exists():
                add("ERROR", page, "dead-link", f"internal link resolves to a missing file: {href}")

        for ref in parser.asset_refs:
            if not ref or _is_external(ref) or ref.startswith("#"):
                continue
            resolved = _resolve(root, page, ref)
            if resolved is not None and not resolved.exists():
                add("ERROR", page, "dead-asset", f"asset reference resolves to a missing file: {ref}")

        # --- perf ----------------------------------------------------------
        if parser.preload_images > 1:
            add("WARN", page, "perf-preload", f"{parser.preload_images} image preloads (keep to the hero only)")
        for img in parser.imgs:
            src = _strip_target(img["src"])
            if not src or _is_external(src):
                continue
            # lazy-loading advice is for raster images; SVGs are vector (tiny) and heroes
            # should stay eager, so only flag raster <img>s that opt out of loading hints.
            if not img["loading"] and posixpath.splitext(src)[1].lower() in _RASTER_SUFFIXES | {".webp"}:
                add("WARN", page, "perf-loading", f"raster <img> without loading attribute: {src}")
            resolved = _resolve(root, page, src)
            if (resolved and resolved.suffix.lower() in _RASTER_SUFFIXES and resolved.is_file()
                    and resolved.stat().st_size > _BIG_RASTER_BYTES):
                kb = resolved.stat().st_size // 1024
                add("WARN", page, "perf-image", f"non-WebP raster {src} is {kb} KB (consider WebP)")

        # --- JSON-LD -------------------------------------------------------
        for i, block in enumerate(parser.jsonld):
            try:
                json.loads(block)
            except Exception as exc:  # noqa: BLE001
                add("ERROR", page, "jsonld", f"JSON-LD block #{i + 1} is invalid: {exc}")

        # --- SEO -----------------------------------------------------------
        if noindex:
            continue  # noindex pages are exempt from indexable SEO checks + sitemap
        if page.name == "index.html":
            indexable_urls.add(_page_url(root, page))
        if not parser.title:
            add("ERROR", page, "seo-title", "missing or empty <title>")
        if not parser.meta_description:
            add("ERROR", page, "seo-description", "missing or empty <meta name=description>")
        if not parser.canonical:
            add("ERROR", page, "seo-canonical", "missing <link rel=canonical>")
        elif CANONICAL_HOST not in parser.canonical:
            add("ERROR", page, "seo-canonical-host",
                f"canonical host is not {CANONICAL_HOST}: {parser.canonical}")
        if parser.og_url and parser.canonical and parser.og_url != parser.canonical:
            add("ERROR", page, "seo-og-url",
                f"og:url ({parser.og_url}) does not match canonical ({parser.canonical})")

    # --- sitemap / robots cross-check --------------------------------------
    sitemap = root / "sitemap.xml"
    if sitemap.is_file():
        try:
            tree = ElementTree.fromstring(sitemap.read_text(encoding="utf-8"))
            ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
            locs = {el.text.strip() for el in tree.findall(".//sm:loc", ns) if el.text}
        except Exception as exc:  # noqa: BLE001
            add("ERROR", "sitemap.xml", "sitemap-parse", f"could not parse sitemap: {exc}")
            locs = set()
        for url in sorted(locs):
            if not url.startswith("https://"):
                add("ERROR", "sitemap.xml", "sitemap-abs", f"sitemap URL is not absolute HTTPS: {url}")
            if CANONICAL_HOST not in url:
                add("ERROR", "sitemap.xml", "sitemap-host", f"sitemap URL host is not {CANONICAL_HOST}: {url}")
        for missing in sorted(indexable_urls - locs):
            add("ERROR", "sitemap.xml", "sitemap-missing", f"indexable page not in sitemap: {missing}")
        for extra in sorted(locs - indexable_urls):
            add("ERROR", "sitemap.xml", "sitemap-extra",
                f"sitemap lists a URL with no matching indexable page: {extra}")

    robots = root / "robots.txt"
    if robots.is_file():
        text = robots.read_text(encoding="utf-8")
        want = f"{CANONICAL_ORIGIN}/sitemap.xml"
        sitemap_lines = [ln.strip() for ln in text.splitlines() if ln.strip().lower().startswith("sitemap:")]
        if not sitemap_lines:
            add("ERROR", "robots.txt", "robots-sitemap", "robots.txt has no Sitemap: line")
        elif not any(ln.split(":", 1)[1].strip() == want for ln in sitemap_lines):
            add("ERROR", "robots.txt", "robots-sitemap",
                f"robots.txt Sitemap: line does not point to {want}")

    return sorted(findings, key=lambda f: (f.level != "ERROR", f.page, f.check, f.message))


def _print_report(findings: list[Finding]) -> None:
    errors = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level == "WARN"]
    by_page: dict[str, list[Finding]] = {}
    for f in findings:
        by_page.setdefault(f.page, []).append(f)
    print("Static-site audit — website/  (correctness · SEO · a11y · perf)")
    for page in sorted(by_page):
        print(f"\n  {page}")
        for f in by_page[page]:
            mark = "✗" if f.level == "ERROR" else "•"
            print(f"    {mark} [{f.level}] {f.check}: {f.message}")
    print(f"\n  {len(errors)} error(s) · {len(warns)} warning(s)")
    if not findings:
        print("  ✅ clean")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit the static website/ site (correctness · SEO · a11y · perf).")
    parser.add_argument("--root", default=None, help="site root (default: <repo>/website)")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args(argv)

    root = Path(args.root) if args.root else _repo_root() / "website"
    if not root.is_dir():
        print(f"site root not found: {root}", file=sys.stderr)
        return 2

    findings = audit(root)
    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        _print_report(findings)
    return 1 if any(f.level == "ERROR" for f in findings) else 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
