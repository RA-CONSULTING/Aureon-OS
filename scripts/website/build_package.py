#!/usr/bin/env python3
"""Build the deployable home.pl package for the static `website/` site.

Validates the site (runs :mod:`scripts.website.audit_site` — aborts on any ERROR), assembles a
clean deploy tree, regenerates ``HOMEPL_PACKAGE_MANIFEST.txt`` with real file counts, zips it
deterministically, and writes a **companion** manifest carrying the ZIP's own SHA-256 (which
cannot live inside the archive it checksums).

    python -m scripts.website.build_package [--out DIR] [--created-at ISO8601]

Pure standard library (`zipfile`, `hashlib`, `shutil`). No network. Two builds at the same
``--created-at`` produce byte-identical artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from scripts.website.audit_site import audit

MANIFEST_NAME = "HOMEPL_PACKAGE_MANIFEST.txt"
PACKAGE_STEM = "aureon-zorza-website"
_EXCLUDE_NAMES = {".git", ".gitignore", ".DS_Store", "Thumbs.db", "__pycache__", ".idea", ".vscode"}
_EXCLUDE_SUFFIXES = {".pyc", ".pyo"}
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)  # fixed → deterministic archive


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_excluded(rel: Path) -> bool:
    if any(part in _EXCLUDE_NAMES for part in rel.parts):
        return True
    return rel.suffix.lower() in _EXCLUDE_SUFFIXES


def _copy_tree(site_root: Path, pkg_dir: Path) -> None:
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    pkg_dir.mkdir(parents=True)
    for src in sorted(site_root.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(site_root)
        if _is_excluded(rel):
            continue
        dst = pkg_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _write_manifest(pkg_dir: Path, created_at: str) -> None:
    files = sorted(p for p in pkg_dir.rglob("*") if p.is_file())
    payload = [p for p in files if p.name != MANIFEST_NAME]  # counts exclude this manifest itself
    total_bytes = sum(p.stat().st_size for p in payload)
    root_entries = sorted(p.name for p in pkg_dir.iterdir())
    lines = [
        f"PACKAGE_NAME: {PACKAGE_STEM}",
        f"ARCHIVE_NAME: {PACKAGE_STEM}.zip",
        f"CREATED_AT: {created_at}",
        "HOSTING_MODEL: static files served directly from document root",
        f"TOTAL_FILE_COUNT: {len(payload):06d}",
        f"TOTAL_UNCOMPRESSED_BYTES: {total_bytes:012d}",
        "COUNTS_EXCLUDE: this manifest file",
        "INDEX_HTML_AT_PACKAGE_ROOT: " + ("YES" if (pkg_dir / "index.html").is_file() else "NO"),
        "ZIP_ROOT_WRAPPER_DIRECTORY: NO",
        "HTACCESS_REQUIRED: NO",
        "ZIP_SIZE_BYTES: SEE_COMPANION_MANIFEST",
        "ZIP_SHA256: SEE_COMPANION_MANIFEST",
        "",
        "MAIN_ROOT_ENTRIES:",
        *[f"- {name}" for name in root_entries],
        "",
        "NOTE:",
        "The final ZIP checksum cannot be embedded inside the ZIP without changing the archive",
        "being checksummed. The authoritative ZIP size and SHA-256 are in the companion manifest",
        f"written beside the archive ({PACKAGE_STEM}.zip.sha256.txt).",
        "",
    ]
    (pkg_dir / MANIFEST_NAME).write_text("\n".join(lines), encoding="utf-8")


def _zip_tree(pkg_dir: Path, zip_path: Path) -> bytes:
    """Zip ``pkg_dir`` deterministically (sorted entries, fixed timestamps) and return its bytes."""
    files = sorted(p for p in pkg_dir.rglob("*") if p.is_file())
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            arcname = p.relative_to(pkg_dir).as_posix()
            zi = zipfile.ZipInfo(arcname, date_time=_ZIP_EPOCH)
            zi.external_attr = 0o644 << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(zi, p.read_bytes())
    return zip_path.read_bytes()


def build(site_root: Path, out_dir: Path, created_at: str) -> dict:
    """Validate, assemble, manifest, zip, and checksum. Returns a result dict.

    Raises ``RuntimeError`` if the site fails the audit (any ERROR finding).
    """
    site_root = site_root.resolve()
    out_dir = out_dir.resolve()

    findings = audit(site_root)
    errors = [f for f in findings if f.level == "ERROR"]
    if errors:
        raise RuntimeError(f"site audit failed with {len(errors)} error(s); fix them before building")

    pkg_dir = out_dir / "website_package"
    _copy_tree(site_root, pkg_dir)
    if not (pkg_dir / "index.html").is_file():
        raise RuntimeError("assembled package has no index.html at its root")
    _write_manifest(pkg_dir, created_at)

    zip_path = out_dir / f"{PACKAGE_STEM}.zip"
    zip_bytes = _zip_tree(pkg_dir, zip_path)
    sha = hashlib.sha256(zip_bytes).hexdigest()

    companion = out_dir / f"{PACKAGE_STEM}.zip.sha256.txt"
    companion.write_text(
        f"ARCHIVE_NAME: {PACKAGE_STEM}.zip\n"
        f"CREATED_AT: {created_at}\n"
        f"ZIP_SIZE_BYTES: {len(zip_bytes)}\n"
        f"ZIP_SHA256: {sha}\n",
        encoding="utf-8",
    )
    n_files = sum(1 for p in pkg_dir.rglob("*") if p.is_file())
    return {
        "package_dir": str(pkg_dir),
        "zip_path": str(zip_path),
        "companion": str(companion),
        "zip_size": len(zip_bytes),
        "zip_sha256": sha,
        "n_files": n_files,
        "n_warnings": sum(1 for f in findings if f.level == "WARN"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the deterministic home.pl deploy package for website/.")
    parser.add_argument("--root", default=None, help="site root (default: <repo>/website)")
    parser.add_argument("--out", default=None, help="output dir (default: <repo>/dist)")
    parser.add_argument("--created-at", default=None,
                        help="ISO-8601 timestamp stamped into the manifest (default: now UTC; "
                             "pass a fixed value for byte-identical rebuilds)")
    args = parser.parse_args(argv)

    site_root = Path(args.root) if args.root else _repo_root() / "website"
    out_dir = Path(args.out) if args.out else _repo_root() / "dist"
    created_at = args.created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not site_root.is_dir():
        print(f"site root not found: {site_root}", file=sys.stderr)
        return 2
    try:
        result = build(site_root, out_dir, created_at)
    except RuntimeError as exc:
        print(f"build aborted: {exc}", file=sys.stderr)
        return 1

    print("home.pl package built")
    print(f"  package dir : {result['package_dir']}  ({result['n_files']} files)")
    print(f"  archive     : {result['zip_path']}  ({result['zip_size']} bytes)")
    print(f"  sha256      : {result['zip_sha256']}")
    print(f"  companion   : {result['companion']}")
    if result["n_warnings"]:
        print(f"  note        : {result['n_warnings']} advisory audit warning(s) (non-blocking)")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
