"""Identity fields for a measured record.

The record names the commit that was HEAD while it was written. That commit is
the parent of the commit that adds the record file. A dirty working tree is
refused: the stamp would mix uncommitted edits into that commit name.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

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


def pin_tree_skip_reason(root: Path) -> str | None:
    """Why this checkout cannot be compared with the pinned aureon tree.

    None means the comparison can run. A missing .git, a shallow clone, or a
    clone that does not contain the pin commit is skipped. The comparison
    itself stays an assertion when the history is present.
    """

    if not (Path(root) / ".git").exists():
        return "no .git; the pin tree comparison needs a git checkout"
    try:
        shallow = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--is-shallow-repository"],
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stdout", None) or str(exc)
        return f"git could not read this checkout: {detail}".strip()
    if shallow == "true":
        return "shallow clone; the pin commit may be absent"
    present = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{PINNED_COMMIT}^{{commit}}"],
        check=False,
        capture_output=True,
        text=True,
    )
    if present.returncode != 0:
        return f"pin commit {PINNED_COMMIT} is not in this clone"
    return None


def measurement_stamp() -> dict[str, str]:
    """Pin, aureon/ tree hash, and the code commit that was HEAD.

    Raises RuntimeError when git status --porcelain is not empty.
    """

    dirty = _git("status", "--porcelain")
    if dirty.strip():
        raise RuntimeError(
            "measurement_stamp refuses a dirty working tree. "
            "Commit the code, then write the measured record.\n" + dirty.strip()
        )
    return {
        "aureon_tree": _git("rev-parse", "HEAD:aureon"),
        "code_commit": _git("rev-parse", "HEAD"),
        "code_commit_note": CODE_COMMIT_NOTE,
        "pin": PINNED_COMMIT,
        "pin_aureon_tree": _git("rev-parse", f"{PINNED_COMMIT}:aureon"),
    }
