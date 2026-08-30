#!/usr/bin/env python3
"""Build the deployable home.pl package for the static `website/` site.

Validates the site (runs :mod:`scripts.website.audit_site` — aborts on any ERROR), assembles a
clean deploy tree, regenerates ``HOMEPL_PACKAGE_MANIFEST.txt`` with real file counts, zips it
deterministically, and writes a **companion** manifest carrying the ZIP's own SHA-256 (which
cannot live inside the archive it checksums).

    python -m scripts.website.build_package --source-commit <full-HEAD> [--out DIR]
                                             [--created-at ISO8601]

Pure standard library (`zipfile`, `hashlib`, `shutil`). No network. Two builds at the same
``--created-at`` produce byte-identical artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from scripts.website.audit_site import audit

MANIFEST_NAME = "HOMEPL_PACKAGE_MANIFEST.txt"
FILE_HASH_MANIFEST_NAME = "HOMEPL_FILE_HASHES.json"
FILE_HASH_MANIFEST_SCHEMA = "aureon.homepl-file-hashes.v1"
PACKAGE_STEM = "aureon-zorza-website"
_SOURCE_COMMIT = re.compile(r"^[0-9a-f]{40}$")
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
    MANIFEST_NAME,
    FILE_HASH_MANIFEST_NAME,
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


@dataclass(frozen=True)
class SourceBinding:
    """Exact source revision bound to a release package."""

    commit: str
    verification: str


class BuildResult(TypedDict):
    """Stable fields returned by :func:`build`."""

    package_dir: str
    zip_path: str
    companion: str
    zip_size: int
    zip_sha256: str
    n_files: int
    n_warnings: int
    source_commit: str
    source_commit_verification: str
    file_hash_manifest: str
    file_hash_manifest_sha256: str
    file_hash_record_count: int


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _normalise_source_commit(value: str) -> str:
    commit = value.strip().lower()
    if not _SOURCE_COMMIT.fullmatch(commit):
        raise RuntimeError("source commit must be one complete 40-character hexadecimal Git commit")
    return commit


def _git(site_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(site_root), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Git is required to verify a repository-backed website release") from exc


def _bind_source_commit(site_root: Path, declared_commit: str) -> SourceBinding:
    """Validate an explicit commit and bind it to the checked-out website source.

    A fixture outside a Git worktree remains buildable when it supplies a valid
    commit explicitly. A website inside a Git worktree must match HEAD and the
    bounded website tree must be clean, otherwise the commit would be a false
    description of the packaged bytes.
    """

    commit = _normalise_source_commit(declared_commit)
    site_root = site_root.resolve()
    try:
        probe = _git(site_root, "rev-parse", "--show-toplevel")
    except RuntimeError:
        try:
            site_root.relative_to(_repo_root().resolve())
        except ValueError:
            return SourceBinding(commit, "declared-only-isolated-source")
        raise
    if probe.returncode != 0:
        try:
            site_root.relative_to(_repo_root().resolve())
        except ValueError:
            return SourceBinding(commit, "declared-only-isolated-source")
        raise RuntimeError("repository-backed website source could not be resolved to a Git worktree")

    repository_root = Path(probe.stdout.strip()).resolve()
    head_result = _git(repository_root, "rev-parse", "HEAD")
    if head_result.returncode != 0:
        raise RuntimeError("could not resolve the checked-out Git HEAD")
    head = _normalise_source_commit(head_result.stdout)
    if commit != head:
        raise RuntimeError(f"declared source commit {commit} does not match checked-out HEAD {head}")

    try:
        relative_site = site_root.relative_to(repository_root)
    except ValueError as exc:
        raise RuntimeError("website source is outside the resolved Git worktree") from exc
    pathspec = relative_site.as_posix() or "."
    status = _git(
        repository_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        pathspec,
    )
    if status.returncode != 0:
        raise RuntimeError("could not verify the website source tree against the declared commit")
    if status.stdout.strip():
        raise RuntimeError(
            "website source has tracked or untracked changes not represented by the declared commit"
        )
    return SourceBinding(commit, "verified-git-head-clean-site")


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


def _write_manifest(pkg_dir: Path, created_at: str, source: SourceBinding) -> None:
    payload = sorted(p for p in pkg_dir.rglob("*") if p.is_file())
    root_entries = sorted({p.name for p in pkg_dir.iterdir()} | {MANIFEST_NAME, FILE_HASH_MANIFEST_NAME})
    lines = [
        f"PACKAGE_NAME: {PACKAGE_STEM}",
        f"ARCHIVE_NAME: {PACKAGE_STEM}.zip",
        f"CREATED_AT: {created_at}",
        f"SOURCE_COMMIT: {source.commit}",
        f"SOURCE_COMMIT_VERIFICATION: {source.verification}",
        "HOSTING_MODEL: static files served directly from document root",
        f"TOTAL_FILE_COUNT: {len(payload) + 2:06d}",
        "TOTAL_UNCOMPRESSED_BYTES: SEE_COMPANION_MANIFEST",
        f"FILE_HASH_MANIFEST: {FILE_HASH_MANIFEST_NAME}",
        f"FILE_HASH_RECORD_COUNT: {len(payload) + 1:06d}",
        "FILE_HASH_ALGORITHM: SHA256",
        "FILE_HASH_MANIFEST_SELF_INCLUDED: NO",
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
        f"{FILE_HASH_MANIFEST_NAME} hashes every other package file, including this summary manifest,",
        "and intentionally excludes itself to avoid a recursive self-hash.",
        "",
    ]
    (pkg_dir / MANIFEST_NAME).write_text("\n".join(lines), encoding="utf-8")


def _write_file_hash_manifest(pkg_dir: Path, source_commit: str) -> tuple[int, str]:
    """Hash every package file except the hash manifest itself.

    The summary manifest is written first and therefore appears in this list.
    The hash manifest cannot contain its own digest without recursion; its hash
    is instead recorded in the external companion manifest.
    """

    target = pkg_dir / FILE_HASH_MANIFEST_NAME
    records: list[dict[str, object]] = []
    files = [path for path in pkg_dir.rglob("*") if path.is_file() and path != target]
    for path in sorted(files, key=lambda item: item.relative_to(pkg_dir).as_posix()):
        relative = path.relative_to(pkg_dir).as_posix()
        records.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    payload = {
        "algorithm": "sha256",
        "manifest_self_included": False,
        "record_count": len(records),
        "records": records,
        "schema": FILE_HASH_MANIFEST_SCHEMA,
        "source_commit": source_commit,
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target.write_bytes(encoded)
    return len(records), hashlib.sha256(encoded).hexdigest()


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


def build(site_root: Path, out_dir: Path, created_at: str, source_commit: str) -> BuildResult:
    """Validate, assemble, manifest, zip, and checksum. Returns a result dict.

    Raises ``RuntimeError`` if the site fails the audit (any ERROR finding).
    """
    site_root = site_root.resolve()
    out_dir = out_dir.resolve()
    source = _bind_source_commit(site_root, source_commit)

    findings = audit(site_root)
    errors = [f for f in findings if f.level == "ERROR"]
    if errors:
        raise RuntimeError(f"site audit failed with {len(errors)} error(s); fix them before building")

    pkg_dir = out_dir / "website_package"
    _copy_tree(site_root, pkg_dir)
    if not (pkg_dir / "index.html").is_file():
        raise RuntimeError("assembled package has no index.html at its root")
    _write_manifest(pkg_dir, created_at, source)
    hash_record_count, hash_manifest_sha256 = _write_file_hash_manifest(pkg_dir, source.commit)

    zip_path = out_dir / f"{PACKAGE_STEM}.zip"
    zip_bytes = _zip_tree(pkg_dir, zip_path)
    sha = hashlib.sha256(zip_bytes).hexdigest()

    companion = out_dir / f"{PACKAGE_STEM}.zip.sha256.txt"
    package_files = sorted(p for p in pkg_dir.rglob("*") if p.is_file())
    uncompressed_bytes = sum(path.stat().st_size for path in package_files)
    companion.write_text(
        f"ARCHIVE_NAME: {PACKAGE_STEM}.zip\n"
        f"CREATED_AT: {created_at}\n"
        f"SOURCE_COMMIT: {source.commit}\n"
        f"SOURCE_COMMIT_VERIFICATION: {source.verification}\n"
        f"PACKAGE_FILE_COUNT: {len(package_files)}\n"
        f"PACKAGE_UNCOMPRESSED_BYTES: {uncompressed_bytes}\n"
        f"FILE_HASH_MANIFEST: {FILE_HASH_MANIFEST_NAME}\n"
        f"FILE_HASH_RECORD_COUNT: {hash_record_count}\n"
        f"FILE_HASH_MANIFEST_SHA256: {hash_manifest_sha256}\n"
        f"ZIP_SIZE_BYTES: {len(zip_bytes)}\n"
        f"ZIP_SHA256: {sha}\n",
        encoding="utf-8",
    )
    return {
        "package_dir": str(pkg_dir),
        "zip_path": str(zip_path),
        "companion": str(companion),
        "zip_size": len(zip_bytes),
        "zip_sha256": sha,
        "n_files": len(package_files),
        "n_warnings": sum(1 for f in findings if f.level == "WARN"),
        "source_commit": source.commit,
        "source_commit_verification": source.verification,
        "file_hash_manifest": str(pkg_dir / FILE_HASH_MANIFEST_NAME),
        "file_hash_manifest_sha256": hash_manifest_sha256,
        "file_hash_record_count": hash_record_count,
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
    parser.add_argument(
        "--source-commit",
        required=True,
        help="complete 40-character Git commit represented by the package; must equal HEAD in a worktree",
    )
    args = parser.parse_args(argv)

    site_root = Path(args.root) if args.root else _repo_root() / "website"
    out_dir = Path(args.out) if args.out else _repo_root() / "dist"
    created_at = args.created_at or datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not site_root.is_dir():
        print(f"site root not found: {site_root}", file=sys.stderr)
        return 2
    try:
        result = build(site_root, out_dir, created_at, args.source_commit)
    except RuntimeError as exc:
        print(f"build aborted: {exc}", file=sys.stderr)
        return 1

    print("home.pl package built")
    print(f"  package dir : {result['package_dir']}  ({result['n_files']} files)")
    print(f"  archive     : {result['zip_path']}  ({result['zip_size']} bytes)")
    print(f"  sha256      : {result['zip_sha256']}")
    print(f"  source      : {result['source_commit']} ({result['source_commit_verification']})")
    print(f"  file hashes : {result['file_hash_manifest']} ({result['file_hash_record_count']} records)")
    print(f"  companion   : {result['companion']}")
    if result["n_warnings"]:
        print(f"  note        : {result['n_warnings']} advisory audit warning(s) (non-blocking)")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
