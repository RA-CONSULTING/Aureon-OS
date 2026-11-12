"""Receipt provenance helpers skip when git history is truncated."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.support import receipt_provenance as provenance

_GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Provenance Test",
    "GIT_AUTHOR_EMAIL": "provenance@example.com",
    "GIT_COMMITTER_NAME": "Provenance Test",
    "GIT_COMMITTER_EMAIL": "provenance@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def _git(cwd: Path, *args: str) -> None:
    env = {**os.environ, **_GIT_IDENTITY}
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def test_last_commit_writing_skips_in_a_shallow_clone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "full"
    source.mkdir()
    _git(source, "init", "-q")
    (source / "receipt.txt").write_text("one\n", encoding="utf-8")
    _git(source, "add", "receipt.txt")
    _git(source, "commit", "-q", "-m", "one")
    (source / "receipt.txt").write_text("two\n", encoding="utf-8")
    _git(source, "add", "receipt.txt")
    _git(source, "commit", "-q", "-m", "two")

    clone = tmp_path / "shallow"
    _git(tmp_path, "clone", "-q", "--depth", "1", f"file://{source}", str(clone))

    monkeypatch.setattr(provenance, "_ROOT", clone)
    with pytest.raises(pytest.skip.Exception, match="shallow"):
        provenance.last_commit_writing("receipt.txt")
