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
_EXCLUDE_NAMES = {
    ".git",
    ".gitignore",
    ".DS_Store",
    "Thumbs.db",
    "__pycache__",
    ".idea",
    ".vscode",
    "archive",
    "aureon-zorza-backgrounds.css",
    "company-platform.json",
    "project-graph.json",
    "projects.json",
    "styleguide.html",
}
_EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".md", ".ps1"}
_SECRET_DIRECTORY_NAMES = {".aws", ".azure", ".gcloud", ".gnupg", ".kube", ".ssh"}
_SECRET_NAMES = {
    ".dockercfg",
    ".dockerconfigjson",
    ".env",
    ".envrc",
    ".git-credentials",
    ".htpasswd",
    ".netrc",
    ".npmrc",
    ".pgpass",
    ".pypirc",
    "application_default_credentials.json",
    "auth.json",
    "credentials",
    "credentials.json",
    "google-services.json",
    "googleservice-info.plist",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "secrets.json",
    "secrets.toml",
    "secrets.yaml",
    "secrets.yml",
}
_SECRET_NAME_PREFIXES = (
    "client_secret",
    "firebase-adminsdk-",
    "service-account",
    "service_account",
)
_SECRET_NAME_SUFFIXES = (
    "-credentials.json",
    "_credentials.json",
    ".credentials.json",
    "-service-account.json",
    "_service_account.json",
    ".service-account.json",
    "-secrets.json",
    "_secrets.json",
    ".secrets.json",
)
_SECRET_SUFFIXES = {
    ".jks",
    ".kdbx",
    ".key",
    ".keystore",
    ".mobileprovision",
    ".ovpn",
    ".p12",
    ".pem",
    ".pfx",
    ".pkcs8",
    ".ppk",
}
_ASSET_REFERENCE_SUFFIXES = {".html", ".css", ".js", ".json", ".xml", ".webmanifest", ".svg"}
_ALWAYS_KEEP_ASSETS = {Path("assets/fonts/LICENSES.txt")}
_ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)  # fixed → deterministic archive


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_excluded(rel: Path) -> bool:
    folded_parts = tuple(part.casefold() for part in rel.parts)
    excluded_names = {item.casefold() for item in _EXCLUDE_NAMES}
    if any(part in excluded_names or part in _SECRET_DIRECTORY_NAMES for part in folded_parts):
        return True
    name = rel.name.casefold()
    if name == ".env" or name.startswith(".env."):
        return True
    if (
        name in _SECRET_NAMES
        or name.startswith(_SECRET_NAME_PREFIXES)
        or name.endswith(_SECRET_NAME_SUFFIXES)
    ):
        return True
    suffix = rel.suffix.lower()
    return suffix in _EXCLUDE_SUFFIXES or suffix in _SECRET_SUFFIXES


def _referenced_assets(site_root: Path) -> set[Path]:
    """Return runtime assets named by the public source surface.

    The working tree deliberately retains source PNGs, superseded responsive
    variants and design references.  Shipping them all increases the Home.pl
    rollback and transfer surface without improving a public route.  Runtime
    references are source-bound through HTML/CSS/JS/JSON/XML and SVG text.
    """
    corpus_parts: list[str] = []
    for source in sorted(site_root.rglob("*")):
        if not source.is_file():
            continue
        rel = source.relative_to(site_root)
        if _is_excluded(rel) or source.suffix.lower() not in _ASSET_REFERENCE_SUFFIXES:
            continue
        try:
            corpus_parts.append(source.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            continue
    corpus = "\n".join(corpus_parts)

    referenced = set(_ALWAYS_KEEP_ASSETS)
    asset_root = site_root / "assets"
    if not asset_root.is_dir():
        return referenced
    for asset in sorted(asset_root.rglob("*")):
        if not asset.is_file():
            continue
        rel = asset.relative_to(site_root)
        rel_text = rel.as_posix()
        if rel_text in corpus or asset.name in corpus:
            referenced.add(rel)
    return referenced


def _copy_tree(site_root: Path, pkg_dir: Path) -> None:
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    pkg_dir.mkdir(parents=True)
    referenced_assets = _referenced_assets(site_root)
    for src in sorted(site_root.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(site_root)
        if _is_excluded(rel):
            continue
        if rel.parts and rel.parts[0] == "assets" and rel not in referenced_assets:
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
        "HTACCESS_SECURITY_CONFIGURATION_INCLUDED: " + ("YES" if (pkg_dir / ".htaccess").is_file() else "NO"),
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
    parser = argparse.ArgumentParser(
        description="Build the deterministic home.pl deploy package for website/."
    )
    parser.add_argument("--root", default=None, help="site root (default: <repo>/website)")
    parser.add_argument("--out", default=None, help="output dir (default: <repo>/dist)")
    parser.add_argument(
        "--created-at",
        default=None,
        help="ISO-8601 timestamp stamped into the manifest (default: now UTC; "
        "pass a fixed value for byte-identical rebuilds)",
    )
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
