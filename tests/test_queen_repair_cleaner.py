"""Tests for the self-repair disk cleaner (owner's call, 12:30 GMT)."""

from __future__ import annotations

import gzip
import subprocess
import time
from pathlib import Path

import pytest

from aureon.autonomous import queen_repair_cleaner as C


def _fake_tmp(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    fake = tmp_path / "tmp"
    fake.mkdir()
    monkeypatch.setattr(C.tempfile, "gettempdir", lambda: str(fake))
    return fake


def test_sweep_basetemps_removes_ours_keeps_the_live_one(tmp_path, monkeypatch):
    fake = _fake_tmp(monkeypatch, tmp_path)
    stale = fake / (C.BASETEMP_PREFIX + "stale")
    live = fake / (C.BASETEMP_PREFIX + "live")
    for d in (stale, live):
        d.mkdir()
        (d / "big.bin").write_bytes(b"0" * 1000)
    removed = C.sweep_basetemps(keep=live)
    assert str(stale) in removed
    assert not stale.exists()
    assert live.exists()  # the running cycle's dir is kept


def test_sweep_never_touches_other_agents_or_secrets(tmp_path, monkeypatch):
    fake = _fake_tmp(monkeypatch, tmp_path)
    # A path that matches the prefix but belongs elsewhere / is a secret is left alone.
    spike = fake / (C.BASETEMP_PREFIX + "spike277")
    quarantine = fake / (C.BASETEMP_PREFIX + "quarantine")
    for d in (spike, quarantine):
        d.mkdir()
    removed = C.sweep_basetemps()
    assert removed == []
    assert spike.exists() and quarantine.exists()


def test_sweep_journals_removes_only_stale(tmp_path, monkeypatch):
    fake = _fake_tmp(monkeypatch, tmp_path)
    old = fake / (C.JOURNAL_PREFIX + "old")
    fresh = fake / (C.JOURNAL_PREFIX + "fresh")
    for d in (old, fresh):
        d.mkdir()
    old_time = time.time() - 7200  # 2h ago
    import os
    os.utime(old, (old_time, old_time))
    removed = C.sweep_journals(max_age_s=3600)
    assert str(old) in removed and not old.exists()
    assert fresh.exists()


def _git(root, *args):
    return subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, timeout=60)


def test_prune_branches_keeps_fixes_and_current(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init")
    _git(root, "config", "user.email", "a@b.c")
    _git(root, "config", "user.name", "t")
    (root / "f.txt").write_text("x", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "base")
    base = (_git(root, "rev-parse", "--abbrev-ref", "HEAD").stdout or "").strip()
    _git(root, "checkout", "-B", "aureon-self-repair/held")  # no fix commit
    _git(root, "checkout", "-B", "aureon-self-repair/fixed")
    _git(root, "commit", "--allow-empty", "-m", "self-repair (gate-verified): f.txt")
    _git(root, "checkout", base)
    deleted = C.prune_branches(root, keep_recent=0)
    assert "aureon-self-repair/held" in deleted
    assert "aureon-self-repair/fixed" not in deleted
    branches = (_git(root, "branch", "--format=%(refname:short)").stdout or "")
    assert "aureon-self-repair/fixed" in branches
    assert "aureon-self-repair/held" not in branches


def test_rotate_logs_archives_whole_and_keeps_tail(tmp_path):
    root = tmp_path / "proj"
    (root / "state").mkdir(parents=True)
    log = root / "state" / "thoughts.jsonl"
    lines = [f'{{"n": {i}}}\n' for i in range(2000)]
    log.write_text("".join(lines), encoding="utf-8")
    original = log.read_bytes()
    protected = root / "state" / "queen_repair_progress.jsonl"
    protected.write_text("x" * 50000, encoding="utf-8")
    rotated = C.rotate_logs(root, cap=1000, tail=200)
    assert len(rotated) == 1
    archive = Path(rotated[0])
    assert archive.exists()
    # Nothing dropped: the gzip holds the complete original file.
    assert gzip.decompress(archive.read_bytes()) == original
    # The live file is now a small recent tail ending on the last line.
    assert log.stat().st_size <= 400
    assert log.read_text(encoding="utf-8").endswith('{"n": 1999}\n')
    # Protected logs are never rotated.
    assert protected.read_text(encoding="utf-8") == "x" * 50000


def test_ensure_space_cleans_when_low(tmp_path, monkeypatch):
    root = tmp_path / "proj"
    (root / "state").mkdir(parents=True)
    calls = {"n": 0}
    # Low before cleaning, healthy after -> ensure_space must clean and report ok.
    seq = iter([1 * 1024**3, 9 * 1024**3, 9 * 1024**3])
    monkeypatch.setattr(C, "free_bytes", lambda *a, **k: next(seq))
    monkeypatch.setattr(C, "clean_cycle", lambda *a, **k: calls.__setitem__("n", calls["n"] + 1) or {})
    result = C.ensure_space(root, min_free=5 * 1024**3)
    assert result["ok"] is True
    assert calls["n"] == 1


def test_ensure_space_skips_cleaning_when_healthy(tmp_path, monkeypatch):
    monkeypatch.setattr(C, "free_bytes", lambda *a, **k: 20 * 1024**3)
    called = {"n": 0}
    monkeypatch.setattr(C, "clean_cycle", lambda *a, **k: called.__setitem__("n", 1))
    result = C.ensure_space(tmp_path, min_free=5 * 1024**3)
    assert result["ok"] is True and result["cleaned"] is None
    assert called["n"] == 0
