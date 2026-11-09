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


def _rev(repo: Path) -> str:
    return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()


def test_tip_not_on_main_is_refused_before_write(tmp_path: Path) -> None:
    module = _load()
    repo = _repo(tmp_path)
    frozen = _rev(repo)
    missing = "b2b0310362597dc520114de86d8700c0c50758d5"
    missing_reason = module.tip_blocks_write(repo, missing)
    assert missing_reason is not None
    assert "not on main" in missing_reason
    assert "does not exist" not in missing_reason

    (repo / "side.txt").write_text("pre-squash\n", encoding="utf-8")
    _git(repo, "add", "side.txt")
    _git(repo, "commit", "-m", "old branch")
    side = _rev(repo)
    _git(repo, "reset", "--hard", "HEAD~1")
    assert _rev(repo) == frozen
    kind = subprocess.check_output(["git", "-C", str(repo), "cat-file", "-t", side], text=True).strip()
    assert kind == "commit"
    side_reason = module.tip_blocks_write(repo, side)
    assert side_reason is not None
    assert "not on main" in side_reason
    assert "does not exist" not in side_reason
    assert module.commit_on_main(repo, frozen) is True
    assert module.tip_blocks_write(repo, frozen) is None

    script = repo / "scripts" / "validation" / "go_live_stage6.py"
    script.parent.mkdir(parents=True)
    script.write_text(f'TIP = "{side}"\n', encoding="utf-8")
    original = f'{{"go_live_clear": false, "tip": "{side}"}}\n'
    paths = (
        repo / "measured" / "go_live_stage6_provenance.json",
        repo / "measured" / "go_live_stage6_source_census.json",
    )
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(original, encoding="utf-8")
    before = [path.read_bytes() for path in paths]
    block = module.stage6_write_block(repo)
    assert block is not None
    assert "not on main" in block
    assert "does not exist" not in block
    assert side in block
    assert [path.read_bytes() for path in paths] == before

    script.write_text(f'TIP = "{frozen}"\n', encoding="utf-8")
    assert module.stage6_write_block(repo) is None
    assert [path.read_bytes() for path in paths] == before


def test_recorded_stage6_tip_is_not_on_main() -> None:
    module = _load()
    old_tip = "b2b0310362597dc520114de86d8700c0c50758d5"
    paths = (
        ROOT / "measured" / "go_live_stage6_provenance.json",
        ROOT / "measured" / "go_live_stage6_source_census.json",
    )
    before = [path.read_bytes() for path in paths]
    assert module.read_stage6_tip(ROOT) == old_tip
    block = module.stage6_write_block(ROOT)
    assert block is not None
    assert "not on main" in block
    assert "does not exist" not in block
    assert old_tip in block
    assert [path.read_bytes() for path in paths] == before


def test_child_go_live_clear_true_is_refused() -> None:
    module = _load()
    row = module._row(2, "release provenance", "hold", "wrote the file", go_live_clear=True)
    assert row["verdict"] == "refused"
    assert row["go_live_clear"] is False
