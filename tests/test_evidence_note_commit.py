"""`--check` reads each HNC note by walking back to its recording commit.

The temp repos are offline. Notes are created only inside those repos.
A clone does not receive notes, and the check does not fetch them.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aureon.evidence.hnc_anchor import (
    NEXT_NOTE_NAME,
    NEXT_NOTE_REF,
    NEXT_RECORD_REL,
    NEXT_TOKEN_REL,
    NOTE_NAME,
    NOTE_REF,
    RECORD_REL,
    TOKEN_REL,
    canonical_token_text,
    git_blob_sha1,
)
from aureon.evidence.runner import main


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


def _record(text: str, note_ref: str, **extra: str) -> str:
    payload: dict[str, str] = {
        "note_ref": note_ref,
        "note_git_blob": git_blob_sha1(text.encode("ascii")),
    }
    payload.update(extra)
    return json.dumps(payload, indent=2) + "\n"


def _repo_with_note_on_an_earlier_commit(tmp: Path) -> tuple[Path, str]:
    """Commit both tokens, attach both notes, then move HEAD forward."""

    repo = tmp / "origin"
    _init(repo)
    first = canonical_token_text(b"\x30\x01")
    second = canonical_token_text(b"\x30\x02")
    _put(repo, TOKEN_REL, first)
    _put(repo, RECORD_REL, _record(first, NOTE_REF))
    _put(repo, NEXT_TOKEN_REL, second)
    _put(repo, NEXT_RECORD_REL, _record(second, NEXT_NOTE_REF))
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
    repo, noted = _repo_with_note_on_an_earlier_commit(tmp_path)
    assert _rev(repo) != noted
    assert _git(repo, "notes", "--ref", NOTE_NAME, "show", "HEAD", check=False).returncode != 0
    assert _git(repo, "notes", "--ref", NOTE_NAME, "show", noted).returncode == 0
    monkeypatch.setattr("aureon.evidence.runner.build", _fake_build)
    assert main(["--check", "--root", str(repo)]) == 0
    captured = capsys.readouterr()
    assert "byte-for-byte match" in captured.out
    assert captured.out.count(f"anchored on {noted}") == 2
    assert _git(repo, "notes", "--ref", NOTE_NAME, "show", "HEAD", check=False).returncode != 0
    assert _git(repo, "notes", "--ref", NEXT_NOTE_NAME, "show", noted).returncode == 0


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
    assert "anchored on " not in captured.out
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
    assert "anchored on " not in captured.out
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
    missing = _git(clone, "show-ref", "--verify", "--quiet", f"refs/notes/{NOTE_NAME}", check=False)
    assert missing.returncode != 0
    monkeypatch.setattr("aureon.evidence.runner.build", _fake_build)
    assert main(["--check", "--root", str(clone)]) == 1
    captured = capsys.readouterr()
    assert "byte-for-byte match" not in captured.out
    assert "anchored on " not in captured.out
    assert "not fetched" in captured.err
    assert "refs/notes/*:refs/notes/*" in captured.err


def test_check_ignores_a_matching_note_on_a_non_ancestor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, noted = _repo_with_note_on_an_earlier_commit(tmp_path)
    _git(repo, "notes", "--ref", NOTE_NAME, "remove", noted)
    _git(repo, "checkout", "--detach", noted)
    _put(repo, "side.txt", "side\n")
    _git(repo, "add", "side.txt")
    _git(repo, "commit", "-m", "side")
    side = _rev(repo)
    _git(repo, "notes", "--ref", NOTE_NAME, "add", "-F", TOKEN_REL, side)
    _git(repo, "checkout", "main")
    assert _git(repo, "merge-base", "--is-ancestor", side, "HEAD", check=False).returncode != 0
    assert _git(repo, "notes", "--ref", NOTE_NAME, "show", side).returncode == 0
    assert _git(repo, "notes", "--ref", NOTE_NAME, "show", noted, check=False).returncode != 0
    monkeypatch.setattr("aureon.evidence.runner.build", _fake_build)
    assert main(["--check", "--root", str(repo)]) == 1
    captured = capsys.readouterr()
    assert "byte-for-byte match" not in captured.out
    assert "anchored on " not in captured.out
    assert side in captured.err
    assert "not an ancestor of HEAD" in captured.err
    assert "ignores" in captured.err


def test_recording_commit_off_history_fails_the_ancestor_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, noted = _repo_with_note_on_an_earlier_commit(tmp_path)
    off = "ab" * 20
    assert len(off) == 40
    first = canonical_token_text(b"\x30\x01")
    _put(repo, RECORD_REL, _record(first, NOTE_REF, recording_commit=off))
    _git(repo, "add", RECORD_REL)
    _git(repo, "commit", "-m", "name a commit off this history")
    assert _git(repo, "cat-file", "-e", f"{off}^{{commit}}", check=False).returncode != 0
    assert _git(repo, "notes", "--ref", NOTE_NAME, "show", noted).returncode == 0
    monkeypatch.setattr("aureon.evidence.runner.build", _fake_build)
    assert main(["--check", "--root", str(repo)]) == 1
    captured = capsys.readouterr()
    assert "byte-for-byte match" not in captured.out
    assert "anchored on " not in captured.out
    assert off in captured.err
    assert "not an ancestor of HEAD" in captured.err


def test_explicit_note_commit_wins_over_a_later_match(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo, noted = _repo_with_note_on_an_earlier_commit(tmp_path)
    first = canonical_token_text(b"\x30\x01")
    second = canonical_token_text(b"\x30\x02")
    _put(repo, RECORD_REL, _record(first, NOTE_REF, note_commit=noted))
    _put(repo, NEXT_RECORD_REL, _record(second, NEXT_NOTE_REF, note_commit=noted))
    _git(repo, "add", RECORD_REL, NEXT_RECORD_REL)
    _git(repo, "commit", "-m", "name the earlier recording commit")
    later = _rev(repo)
    assert later != noted
    tampered = tmp_path / "tampered.txt"
    tampered.write_text(canonical_token_text(b"\x30\x7f"), encoding="utf-8")
    for name in (NOTE_NAME, NEXT_NOTE_NAME):
        _git(repo, "notes", "--ref", name, "add", "-f", "-F", str(tampered), later)
    monkeypatch.setattr("aureon.evidence.runner.build", _fake_build)
    assert main(["--check", "--root", str(repo)]) == 0
    captured = capsys.readouterr()
    assert captured.out.count(f"anchored on {noted}") == 2
    assert f"anchored on {later}" not in captured.out
