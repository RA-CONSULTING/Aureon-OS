"""QueenSoulReader must not invent a location, and a failed shield
totals load must not overwrite history.

With no measured location signal, city/distance/confidence are None
(or a clear no-reading status) and Belfast is never reported as a
reading. If queen_shield_stats.json exists but cannot be loaded, a
later save is skipped so a session starting at 1 cannot replace the
file. The reader's __main__ demo still exits 0 offline.

No network and no randomness.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
READER = REPO / "aureon" / "queen" / "queen_soul_reader.py"


def _reader(monkeypatch):
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    sys.path.insert(0, str(REPO))
    from aureon.queen.queen_soul_reader import QueenSoulReader
    return QueenSoulReader()


def test_location_is_none_with_no_signal(monkeypatch):
    location = _reader(monkeypatch)._read_location_from_signals()
    assert location["city"] is None
    assert location["country"] is None
    assert location["environment"] is None
    assert location["environment_type"] is None
    assert location["distance_from_anchor_km"] is None
    assert location["confidence"] is None
    assert location["method"] is None
    assert location.get("status") == "no_reading"
    assert location.get("is_live") is False

    reading = _reader(monkeypatch).read_soul()
    loc = reading["location"]
    assert loc["city"] is None
    assert loc["confidence"] is None
    assert loc.get("status") == "no_reading"
    verdicts = reading["queen_verdict"]["verdicts"]
    assert any("LOCATION: no reading" in v for v in verdicts)
    assert not any("Belfast" in v for v in verdicts)
    assert "Belfast" not in reading["queen_verdict"]["queen_message"]


def test_no_belfast_stand_in(monkeypatch):
    location = _reader(monkeypatch)._read_location_from_signals()
    blob = json.dumps(location)
    assert "Belfast" not in blob
    assert "Northern Ireland" not in blob
    assert 0.5 != location.get("distance_from_anchor_km")
    assert 0.75 != location.get("confidence")


def test_shield_skips_save_after_failed_load(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("AUREON_ALLOW_SIM_FALLBACK", raising=False)
    stats = tmp_path / "queen_shield_stats.json"
    original = "{not-json"
    stats.write_text(original, encoding="utf-8")

    sys.path.insert(0, str(REPO))
    from aureon.queen.queen_soul_shield import QueenSoulShield

    shield = QueenSoulShield()
    assert shield.attacks_blocked_total is None
    assert shield._stats_load_failed is True

    shield.attacks_blocked_session += 1
    shield._save_stats()
    assert stats.read_text(encoding="utf-8") == original


def test_demo_exits_zero_offline(tmp_path, monkeypatch):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO) + os.pathsep + env.get("PYTHONPATH", "")
    env.pop("AUREON_ALLOW_SIM_FALLBACK", None)
    result = subprocess.run(
        [sys.executable, str(READER)],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "LOCATION READING:" in result.stdout
    assert "City: no reading" in result.stdout
    assert "I know you are in Belfast" not in result.stdout
    # The location block itself must not report the stand-in city.
    loc_start = result.stdout.index("LOCATION READING:")
    loc_end = result.stdout.index("SOUL COHERENCE:", loc_start)
    assert "Belfast" not in result.stdout[loc_start:loc_end]
