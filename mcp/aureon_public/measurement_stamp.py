"""Identity fields for a measured record.

The record names the commit that was HEAD while it was written. That commit is
the parent of the commit that adds the record file.
"""

from __future__ import annotations

import subprocess

from aureon_public.guard_loader import PINNED_COMMIT
from aureon_public.paths import repo_root

# git rev-parse 8aa6a2d971cc529484e2a5e261e28afafab4e4f4:aureon
PIN_AUREON_TREE = "8aef927b7fe6276c187e4c73c79f0de012ad980d"
CODE_COMMIT_NOTE = (
    "This is the parent of the commit that contains this record. "
    "The record cannot name the commit that adds the file."
)


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo_root()), *args],
        text=True,
    ).strip()


def measurement_stamp() -> dict[str, str]:
    """Pin, aureon/ tree hash, and the code commit that was HEAD."""

    return {
        "aureon_tree": _git("rev-parse", "HEAD:aureon"),
        "code_commit": _git("rev-parse", "HEAD"),
        "code_commit_note": CODE_COMMIT_NOTE,
        "pin": PINNED_COMMIT,
        "pin_aureon_tree": _git("rev-parse", f"{PINNED_COMMIT}:aureon"),
    }
