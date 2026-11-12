"""Read the pin a committed receipt was measured against, from git history.

A committed receipt is a record of one run. Its pin is the pin that was in
force when it ran, not the pin in today's checkout. These helpers read that
value from the commit the receipt names (or the commit that last wrote it),
so a test can check the record against its own history instead of against
a pin that has since moved. A shallow clone, or a commit that is only a
graft or shallow boundary, is skipped: the history may be truncated.
Nothing here writes a receipt or a pin.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_PINNED_COMMIT_RE = re.compile(r'^PINNED_COMMIT = "([0-9a-f]{40})"', re.MULTILINE)
_PIN_RE = re.compile(r'^PIN = "([0-9a-f]{40})"', re.MULTILINE)
_SHA40 = re.compile(r"^[0-9a-f]{40}$")


def _git(*args: str) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=_ROOT, text=True, stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        return None


def _resolve_git_path(relative: str) -> Path | None:
    out = _git("rev-parse", "--git-path", relative)
    if not out or not out.strip():
        return None
    path = Path(out.strip())
    if not path.is_absolute():
        path = _ROOT / path
    return path


def _is_shallow_repository() -> bool:
    out = _git("rev-parse", "--is-shallow-repository")
    return out is not None and out.strip() == "true"


def _is_graft_or_shallow_boundary(commit: str) -> bool:
    """True when ``commit`` is listed in .git/shallow or .git/info/grafts."""

    if _SHA40.fullmatch(commit) is None:
        return False
    shallow = _resolve_git_path("shallow")
    if shallow is not None and shallow.is_file():
        for line in shallow.read_text(encoding="utf-8").splitlines():
            if line.strip() == commit:
                return True
    grafts = _resolve_git_path("info/grafts")
    if grafts is not None and grafts.is_file():
        for line in grafts.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.split()[0] == commit:
                return True
    return False


def _file_at(commit: str, relative: str) -> str:
    if _SHA40.fullmatch(commit) is None:
        pytest.skip(f"commit {commit!r} is not a 40-hex SHA; the receipt's history cannot be read")
    text = _git("show", f"{commit}:{relative}")
    if text is None:
        pytest.skip(f"commit {commit[:12]} is not in this clone; the receipt's history cannot be read")
    return text


def guard_pin_at(commit: str) -> str:
    """PINNED_COMMIT in mcp/aureon_public/guard_loader.py at ``commit``."""

    match = _PINNED_COMMIT_RE.search(_file_at(commit, "mcp/aureon_public/guard_loader.py"))
    assert match is not None, f"PINNED_COMMIT is missing from guard_loader.py at {commit[:12]}"
    return match.group(1)


def last_commit_writing(relative: str) -> str:
    """The commit that last changed ``relative`` (the commit that recorded it).

    Skips when this clone is shallow, or when the commit git returns is only
    a graft or a shallow boundary: that SHA is not a trustworthy last-writer.
    """

    if _is_shallow_repository():
        pytest.skip("shallow clone; the commit that wrote the receipt may be absent")
    out = _git("log", "-1", "--format=%H", "--", relative)
    if not out or not out.strip():
        pytest.skip(f"git history for {relative} is not in this clone")
    commit = out.strip()
    if _is_graft_or_shallow_boundary(commit):
        pytest.skip(
            f"commit {commit[:12]} is a graft or shallow boundary; "
            "the receipt's history cannot be read"
        )
    return commit


def module_pin_at(commit: str, relative: str) -> str:
    """Module-level ``PIN = "..."`` in ``relative`` at ``commit``."""

    match = _PIN_RE.search(_file_at(commit, relative))
    assert match is not None, f"PIN is missing from {relative} at {commit[:12]}"
    return match.group(1)


def is_ancestor(older: str, newer: str) -> bool:
    """True when ``older`` is in the history of ``newer``."""

    for commit in (older, newer):
        if _SHA40.fullmatch(commit) is None:
            pytest.skip(f"commit {commit!r} is not a 40-hex SHA; the receipt's history cannot be read")
        if _git("cat-file", "-e", f"{commit}^{{commit}}") is None:
            pytest.skip(f"commit {commit[:12]} is not in this clone")
    try:
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", older, newer],
            cwd=_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return False
    return True
