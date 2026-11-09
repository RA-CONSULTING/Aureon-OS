"""Remeasure runner: a dirty worktree is refused, and the summary stays HOLD."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validation" / "remeasure_go_live_receipts.py"
PIN = "bb04503119681adcf832f3c3e9b0cbf09fc7a938"


def _load():
    spec = importlib.util.spec_from_file_location("remeasure_go_live_receipts", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> None:
    subprocess.check_call(["git", "-C", str(repo), *args])


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "remeasure@example.com")
    _git(tmp_path, "config", "user.name", "remeasure")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    _git(tmp_path, "add", "a.txt")
    _git(tmp_path, "commit", "-m", "init")
    return tmp_path


def test_dirty_worktree_is_refused(tmp_path: Path) -> None:
    module = _load()
    repo = _repo(tmp_path)
    (repo / "a.txt").write_text("changed\n", encoding="utf-8")

    dirty = module.refuse_dirty(repo)
    assert dirty is not None
    assert "a.txt" in dirty
    assert module.main(["--root", str(repo)]) == 2


def test_untracked_file_is_a_dirty_worktree(tmp_path: Path) -> None:
    module = _load()
    repo = _repo(tmp_path)
    assert module.refuse_dirty(repo) is None
    (repo / "extra.txt").write_text("x\n", encoding="utf-8")
    assert module.refuse_dirty(repo) is not None


def test_summary_lists_verdicts_and_keeps_go_live_clear_false() -> None:
    module = _load()
    context = {
        "head": "0726a325ac934ed2e8d2d18d5c69c31fbfafc666",
        "published_pin": PIN,
        "tools": {
            "python": "3.12.3",
            "git": "git version 2.43.0",
            "unshare": "unshare from util-linux 2.39.3",
            "openssl": "OpenSSL 3.0.13",
        },
    }
    rows = [
        {"receipt": 1, "name": "containment", "verdict": "pass", "detail": "worktree_dirty False"},
        {"receipt": 2, "name": "release provenance", "verdict": "fail", "detail": "on-disk tip b2b03103"},
        {"receipt": 3, "name": "hnc head anchor", "verdict": "absent", "detail": "note is not on HEAD"},
        {"receipt": 4, "name": "census and call sweep", "verdict": "fail", "detail": "census exit 1"},
    ]
    text = module.format_summary(context, rows)

    assert f"HEAD: {context['head']}" in text
    assert f"published_pin: {PIN}" in text
    assert "published_pin_matches_checkout: true" in text
    assert "go_live_clear: false" in text
    assert "go_live_clear: true" not in text
    assert "python: 3.12.3" in text
    assert "git version 2.43.0" in text
    assert "| 1 | containment | pass |" in text
    assert "| 2 | release provenance | fail |" in text
    assert "| 3 | hnc head anchor | absent |" in text
    assert "| 4 | census and call sweep | fail |" in text
    assert "does not push refs/notes/aureon-hnc-head" in text


def test_note_command_reattaches_sequence_one_bytes_without_push_or_timestamp() -> None:
    module = _load()
    lines = module.reattach_command_lines()
    assert lines == [" ".join(module.reattach_argv())]
    command = lines[0]
    assert command == (
        "git notes --ref=aureon-hnc-head add -f -F "
        "evidence/output/hnc_head_anchor.tsr.b64 HEAD"
    )
    assert "push" not in command
    assert "timestamp.digicert.com" not in command
    assert "stamp" not in command


def test_child_go_live_clear_true_is_refused() -> None:
    module = _load()
    row = module._row(2, "release provenance", "hold", "wrote the file", go_live_clear=True)
    assert row["verdict"] == "refused"
    assert row["go_live_clear"] is False
