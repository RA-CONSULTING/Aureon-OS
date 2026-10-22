"""Generate the complete hash-bound production VM release source list.

The source must be a clean detached checkout at the requested revision. The
tracked runtime closure is derived from Git; the ignored frontend ``dist``
directory is included only as a complete artifact set and is rebuilt again by
``build_release_bundle.py`` before acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

from operator_runtime_closure import required_operator_runtime_sources
from release_update import (
    COLLECTOR_REQUIRED_SOURCES,
    PUBLIC_BRIDGE_REQUIRED_SOURCES,
    READ_ORGAN_REQUIRED_SOURCES,
    TOKEN_BROKER_REQUIRED_SOURCES,
    UI_GATEWAY_REQUIRED_SOURCES,
    confined,
    source_path,
)


FRONTEND_DIST = "aureon-os-upstream/frontend/dist/"
_REVISION = re.compile(r"[0-9a-f]{40}")


class ReviewedPathsError(RuntimeError):
    """Stable manifest-generation failure."""


def _git(source: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(source), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReviewedPathsError("source_git_readback_failed") from exc
    if result.returncode:
        raise ReviewedPathsError("source_git_readback_failed")
    return result.stdout.strip()


def _bind_source(source: Path, revision: str) -> list[str]:
    if (
        not source.is_absolute()
        or source.is_symlink()
        or not source.is_dir()
        or _REVISION.fullmatch(revision or "") is None
    ):
        raise ReviewedPathsError("frozen_source_invalid")
    if Path(_git(source, "rev-parse", "--show-toplevel")).resolve() != source.resolve():
        raise ReviewedPathsError("source_must_be_checkout_root")
    if _git(source, "rev-parse", "HEAD") != revision:
        raise ReviewedPathsError("source_revision_mismatch")
    if _git(source, "status", "--porcelain=v1", "--untracked-files=no"):
        raise ReviewedPathsError("tracked_source_checkout_not_clean")
    return _git(
        source,
        "ls-tree",
        "-r",
        "--name-only",
        revision,
        "--",
        "aureon-os-upstream/aureon",
    ).splitlines()


def _git_blob(source: Path, revision: str, relative: str) -> bytes:
    """Read a tracked source from the exact commit, independent of autocrlf."""

    try:
        result = subprocess.run(
            ["git", "-C", str(source), "cat-file", "blob", f"{revision}:{relative}"],
            check=False,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReviewedPathsError("committed_source_bytes_unavailable") from exc
    if result.returncode or len(result.stdout) > 32 * 1024 * 1024:
        raise ReviewedPathsError("committed_source_bytes_unavailable")
    return result.stdout


def reviewed_paths(source: Path, revision: str) -> list[dict[str, str]]:
    package_tree = _bind_source(source, revision)
    required = set(required_operator_runtime_sources(package_tree))
    required.update(COLLECTOR_REQUIRED_SOURCES)
    required.update(UI_GATEWAY_REQUIRED_SOURCES)
    required.update(READ_ORGAN_REQUIRED_SOURCES)
    required.update(TOKEN_BROKER_REQUIRED_SOURCES)
    required.update(PUBLIC_BRIDGE_REQUIRED_SOURCES)

    dist = source / FRONTEND_DIST.rstrip("/")
    if dist.is_symlink() or not dist.is_dir():
        raise ReviewedPathsError("complete_frontend_dist_required")
    dist_paths = []
    for path in sorted(dist.rglob("*")):
        if path.is_symlink():
            raise ReviewedPathsError("frontend_dist_link_forbidden")
        if path.is_file():
            dist_paths.append(path.relative_to(source).as_posix())
    if FRONTEND_DIST + "index.html" not in dist_paths:
        raise ReviewedPathsError("complete_frontend_dist_required")
    required.update(dist_paths)

    rows = []
    for raw in sorted(required):
        relative = source_path(raw)
        path = confined(source, relative)
        if path.is_symlink() or not path.is_file():
            raise ReviewedPathsError("required_release_source_missing")
        data = (
            path.read_bytes()
            if relative.startswith(FRONTEND_DIST)
            else _git_blob(source, revision, relative)
        )
        rows.append(
            {"path": relative, "sha256": hashlib.sha256(data).hexdigest()}
        )
    return rows


def write_manifest(path: Path, rows: list[dict[str, str]]) -> str:
    if not path.is_absolute() or path.exists() or path.is_symlink():
        raise ReviewedPathsError("new_absolute_manifest_path_required")
    raw = json.dumps(rows, sort_keys=True, indent=2).encode("ascii") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        prefix=".reviewed-paths-", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
    return hashlib.sha256(raw).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        rows = reviewed_paths(args.source, args.source_revision)
        manifest_hash = write_manifest(args.output, rows)
        print(
            json.dumps(
                {
                    "files": len(rows),
                    "manifest_sha256": manifest_hash,
                    "source_revision": args.source_revision,
                },
                sort_keys=True,
            )
        )
        return 0
    except (ReviewedPathsError, ValueError) as exc:
        print(str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
