"""`--check` reads each HNC note from the commit it is attached to.

The temp repos are offline. Notes are created only inside those repos.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aureon.evidence.hnc_anchor import (
    NEXT_NOTE_NAME,
    NEXT_RECORD_REL,
    NEXT_TOKEN_REL,
    NOTE_NAME,
    RECORD_REL,
    TOKEN_REL,
    canonical_token_text,
    git_blob_sha1,
)
from aureon.evidence.runner import main

ROOT = Path(__file__).resolve().parents[1]


def _git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=check,
        capture_output=True,
    )


def _rev(root: Path, spec: str = "HEAD") -> str:
    return _git(root, "rev-parse", spec).stdout.decode().strip()


def _init(root: Path) -> None:
    root.mkdir(parents=True)
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "cursoragent@cursor.com")
    _git(root, "config", "user.name", "Cursor Agent")
    _git(root, "config", "commit.gpgsign", "false")


def _put(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _record(text: str) -> str:
    blob = git_blob_sha1(text.encode("ascii"))
    return json.dumps({"note_git_blob": blob}, indent=2) + "\n"


def _repo_with_note_on_an_earlier_commit(tmp: Path) -> tuple[Path, str]:
    """Commit both tokens, attach both notes, then move HEAD forward."""

    repo = tmp / "origin"
    _init(repo)
    first = canonical_token_text(b"\x30\x01")
    second = canonical_token_text(b"\x30\x02")
    _put(repo, TOKEN_REL, first)
    _put(repo, RECORD_REL, _record(first))
    _put(repo, NEXT_TOKEN_REL, second)
    _put(repo, NEXT_RECORD_REL, _record(second))
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "record tokens")
    noted = _rev(repo)
    for name, relative in ((NOTE_NAME, TOKEN_REL), (NEXT_NOTE_NAME, NEXT_TOKEN_REL)):
        _git(repo, "notes", "--ref", name, "add", "-F", relative, noted)
    _git(repo, "commit", "--allow-empty", "-m", "later")
    _git(repo, "commit", "--allow-empty", "-m", "later still")
    return repo, noted


def _fake_build(root: Path, *, require_note: bool = True) -> dict[str, str]:
    files: dict[str, str] = {}
    for relative in (TOKEN_REL, RECORD_REL, NEXT_TOKEN_REL, NEXT_RECORD_REL):
        files[relative] = (Path(root) / relative).read_text(encoding="utf-8")
    return files


def test_check_passes_when_the_note_is_on_an_earlier_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    origin, noted = _repo_with_note_on_an_earlier_commit(tmp_path)
    assert _rev(origin) != noted
    assert _git(origin, "notes", "--ref", NOTE_NAME, "show", "HEAD", check=False).returncode != 0
    assert _git(origin, "notes", "--ref", NOTE_NAME, "show", noted).returncode == 0
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", str(origin), str(clone))
    assert _git(clone, "notes", "--ref", NOTE_NAME, "list", check=False).returncode != 0 or (
        _git(clone, "notes", "--ref", NOTE_NAME, "list", check=False).stdout == b""
    )
    monkeypatch.setattr("aureon.evidence.runner.build", _fake_build)
    assert main(["--check", "--root", str(clone)]) == 0
    captured = capsys.readouterr()
    assert "byte-for-byte match" in captured.out
    listed = _git(clone, "notes", "--ref", NOTE_NAME, "list").stdout.decode()
    assert noted in listed
    assert _git(clone, "notes", "--ref", NOTE_NAME, "show", "HEAD", check=False).returncode != 0
    assert _git(clone, "notes", "--ref", NEXT_NOTE_NAME, "show", noted).returncode == 0


def test_check_fails_when_the_note_is_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, noted = _repo_with_note_on_an_earlier_commit(tmp_path)
    for name in (NOTE_NAME, NEXT_NOTE_NAME):
        _git(repo, "notes", "--ref", name, "remove", noted)
    monkeypatch.setattr("aureon.evidence.runner.build", _fake_build)
    assert main(["--check", "--root", str(repo)]) == 1
    captured = capsys.readouterr()
    assert "byte-for-byte match" not in captured.out
    assert "missing" in captured.err or "not fetched" in captured.err


def test_check_fails_when_the_note_is_tampered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, noted = _repo_with_note_on_an_earlier_commit(tmp_path)
    tampered = tmp_path / "tampered.txt"
    tampered.write_text(canonical_token_text(b"\x30\x7f"), encoding="utf-8")
    _git(repo, "notes", "--ref", NOTE_NAME, "add", "-f", "-F", str(tampered), noted)
    monkeypatch.setattr("aureon.evidence.runner.build", _fake_build)
    assert main(["--check", "--root", str(repo)]) == 1
    captured = capsys.readouterr()
    assert "byte-for-byte match" not in captured.out
    assert "content hash" in captured.err
    assert "does not match" in captured.err


def test_check_does_not_pass_when_notes_refs_are_not_fetched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    origin, _noted = _repo_with_note_on_an_earlier_commit(tmp_path)
    clone = tmp_path / "clone"
    _git(tmp_path, "clone", str(origin), str(clone))
    _git(clone, "remote", "remove", "origin")
    assert (clone / TOKEN_REL).is_file()
    monkeypatch.setattr("aureon.evidence.runner.build", _fake_build)
    assert main(["--check", "--root", str(clone)]) == 1
    captured = capsys.readouterr()
    assert "byte-for-byte match" not in captured.out
    assert "not fetched" in captured.err
    assert "refs/notes/*:refs/notes/*" in captured.err
