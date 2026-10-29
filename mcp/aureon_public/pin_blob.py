"""Git-blob check for a file loaded from the checkout beside a pinned aureon.

Later stages that load any other checkout file must use the same check.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

PINNED_PHENOLIC_BLOB = "325484e9299eecb427cf0063590b0a1d17c16f31"
PHENOLIC_MISMATCH = "checkout phenolic_fingerprint differs from pin a00f744d"


def git_blob_sha1(data: bytes) -> str:
    """SHA-1 of a git blob: the header ``blob <len>\\0`` plus the file bytes."""

    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def pinned_blob_refusal(path: Path, expected: str, mismatch: str) -> str | None:
    """Return mismatch text when path is not the pinned blob. None when it matches."""

    if not path.is_file():
        return f"{path.name} is not in this checkout"
    digest = git_blob_sha1(path.read_bytes())
    if digest != expected:
        return mismatch
    return None


def checkout_blob_refusal(path: Path, root: Path, commit: str) -> str | None:
    """Refuse a checkout file whose git blob is not the blob at ``commit``.

    Returns None when the bytes match. A missing pin path is a refusal.
    The caller skips this when the import comes from an installed copy
    outside the checkout.
    """

    if not path.is_file():
        return f"{path} is not in this checkout"
    try:
        relative = path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return None
    import subprocess

    try:
        pin_blob = subprocess.check_output(
            ["git", "rev-parse", f"{commit}:{relative}"],
            cwd=root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return f"{relative} is not in pin {commit[:12]}"
    digest = git_blob_sha1(path.read_bytes())
    if digest != pin_blob:
        return f"checkout {relative} differs from pin {commit[:12]}"
    return None
