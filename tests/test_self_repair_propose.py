"""Self-repair proposes diffs and refuses regressions and hard-coded addresses."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from aureon.autonomous.aureon_sandbox_self_repair import repair_sandbox
from aureon.autonomous.self_repair_guard import ENABLE_ENV, KILL_ENV, propose_repair_diff, review_log_path


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _repo(root: Path) -> None:
    _git(root, "init")
    _git(root, "config", "user.email", "self-repair@localhost")
    _git(root, "config", "user.name", "Aureon self-repair")


def _enable(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENABLE_ENV, "1")
    monkeypatch.delenv(KILL_ENV, raising=False)
    config = root / "state" / "self_repair_config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('{"enabled": true}\n', encoding="utf-8")


def test_a_safe_repair_is_proposed_and_the_tree_is_not_written(tmp_path: Path) -> None:
    target = tmp_path / "frontend" / "console.ts"
    target.parent.mkdir(parents=True)
    original = 'export const label = "seat";\n'
    target.write_text(original, encoding="utf-8")

    proposal = propose_repair_diff(tmp_path, "frontend/console.ts", 'export const label = "seats";\n')

    assert target.read_text(encoding="utf-8") == original
    assert proposal["applied"] is False
    assert proposal["wrote_tree"] is False
    assert proposal["status"] == "repair_proposed"
    assert proposal["reason"] == "proposed_only"
    assert '+export const label = "seats";' in str(proposal["diff"])
    assert not review_log_path(tmp_path).exists()


def test_a_diff_that_puts_back_a_removed_line_is_a_failed_repair(tmp_path: Path) -> None:
    _repo(tmp_path)
    target = tmp_path / "console.ts"
    target.write_text('const seat = "window-a";\nconst mode = "current";\n', encoding="utf-8")
    _git(tmp_path, "add", "console.ts")
    _git(tmp_path, "commit", "-m", "record the seat line")
    target.write_text('const mode = "current";\n', encoding="utf-8")
    _git(tmp_path, "add", "console.ts")
    _git(tmp_path, "commit", "-m", "remove the seat line")
    current = target.read_text(encoding="utf-8")

    proposal = propose_repair_diff(
        tmp_path,
        "console.ts",
        'const seat = "window-a";\nconst mode = "current";\n',
    )

    assert target.read_text(encoding="utf-8") == current
    assert proposal["status"] == "repair_failed"
    assert proposal["reason"] == "reintroduced_removed_line"
    assert proposal["applied"] is False
    assert proposal["wrote_tree"] is False
    log = review_log_path(tmp_path).read_text(encoding="utf-8")
    assert "repair_failed" in log
    assert "reintroduced_removed_line" in log


def test_a_diff_that_puts_back_a_hardcoded_host_is_a_failed_repair(tmp_path: Path) -> None:
    _repo(tmp_path)
    target = tmp_path / "console.ts"
    target.write_text("export const feed = terminalStateUrls;\n", encoding="utf-8")
    _git(tmp_path, "add", "console.ts")
    _git(tmp_path, "commit", "-m", "read the feed from config")
    current = target.read_text(encoding="utf-8")

    proposal = propose_repair_diff(
        tmp_path,
        "console.ts",
        'export const feed = "http://10.2.3.4/api/terminal-state";\n',
    )

    assert target.read_text(encoding="utf-8") == current
    assert proposal["status"] == "repair_failed"
    assert proposal["reason"] == "hardcoded_host"
    assert proposal["applied"] is False
    assert proposal["wrote_tree"] is False
    log = review_log_path(tmp_path).read_text(encoding="utf-8")
    assert "repair_failed" in log
    assert "hardcoded_host" in log
    assert "10.2.3.4" not in log


def test_sandbox_repair_does_not_restore_a_line_a_later_commit_removed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "app"
    root.mkdir()
    _repo(root)
    source = root / "seat.py"
    source.write_text('def seat():\n    return "window-a"\n', encoding="utf-8")
    _git(root, "add", "seat.py")
    _git(root, "commit", "-m", "old seat")
    source.write_text('def seat():\n    return "current"\n', encoding="utf-8")
    _git(root, "add", "seat.py")
    _git(root, "commit", "-m", "drop the old seat")
    (root / "test_seat.py").write_text(
        "from seat import seat\n\ndef test_seat():\n    assert seat() == \"window-a\"\n",
        encoding="utf-8",
    )
    _git(root, "add", "test_seat.py")
    _git(root, "commit", "-m", "ask for the old seat")
    current = source.read_text(encoding="utf-8")
    _enable(root, monkeypatch)

    report = repair_sandbox(root)

    assert report["status"] == "failed", report
    assert report["reason"] == "reintroduced_removed_line"
    assert report["applied"] is False
    assert source.read_text(encoding="utf-8") == current
    log = review_log_path(root).read_text(encoding="utf-8")
    assert "repair_failed" in log
    assert "reintroduced_removed_line" in log


def test_sandbox_repair_does_not_write_a_hardcoded_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "app"
    root.mkdir()
    source = root / "feed.py"
    source.write_text('def feed():\n    return "safe"\n', encoding="utf-8")
    (root / "test_feed.py").write_text(
        "from feed import feed\n\ndef test_feed():\n"
        "    assert feed() == \"http://10.2.3.4/api\"\n",
        encoding="utf-8",
    )
    current = source.read_text(encoding="utf-8")
    _enable(root, monkeypatch)

    report = repair_sandbox(root)

    assert report["status"] == "failed", report
    assert report["reason"] == "hardcoded_host"
    assert report["applied"] is False
    assert source.read_text(encoding="utf-8") == current
    log = review_log_path(root).read_text(encoding="utf-8")
    assert "repair_failed" in log
    assert "hardcoded_host" in log
    assert "10.2.3.4" not in log
