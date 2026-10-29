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
