"""The restored Sero self-questioning runner is the real one, and the
launcher seat runs it.

No network and no randomness.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "aureon_self_questioning_runner.py"
SEAT = REPO / "aureon" / "launch" / "daemons" / "aureon_self_questioning_runner.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("asqr_under_test", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_real_module_replaces_placeholder():
    text = RUNNER.read_text(encoding="utf-8")
    assert "no question is invented" not in text
    assert "checkout_daemons" not in text
    assert "Self-questioning loop runner — supervised organ wrapper" in text
    assert "from aureon.autonomous.aureon_self_questioning_ai import SelfQuestioningAI" in text
    for word in ("place_order", "create_order", "close_position", "submit_order"):
        assert word not in text
    # byte-identical to Project-Sero blob d856999e
    import subprocess
    sha = subprocess.check_output(["git", "hash-object", str(RUNNER)], text=True).strip()
    assert sha == "d856999e1318395fe3b12f25364096800ebeaad3"


def test_one_cycle_drives_the_engine(monkeypatch):
    mod = _load_runner()
    calls = []

    class Cycle:
        cycle_id = "c1"
        answer_source = "ollama"
        summary = "checked wiring"
        note_path = "autonomy/cycles/c1.md"

    class FakeAI:
        def run_cycle(self, questions=None):
            calls.append(questions)
            return Cycle()

    engine = types.ModuleType("aureon.autonomous.aureon_self_questioning_ai")
    engine.SelfQuestioningAI = FakeAI
    monkeypatch.setitem(sys.modules, "aureon.autonomous.aureon_self_questioning_ai", engine)

    sleeps = []

    def sleep(seconds):
        sleeps.append(seconds)
        raise KeyboardInterrupt

    monkeypatch.setattr(mod.time, "sleep", sleep)
    # The Sero runner catches KeyboardInterrupt only around the cycle,
    # not around the interval sleep. One mocked sleep must therefore
    # surface, and the cycle must already have run.
    with pytest.raises(KeyboardInterrupt):
        mod.main(["--interval", "60", "--question", "What needs attention?"])
    assert calls == [["What needs attention?"]]
    assert sleeps == [60.0]


def test_launcher_seat_delegates_to_real_module():
    text = SEAT.read_text(encoding="utf-8")
    assert "aureon_self_questioning_runner.py" in text
    assert "_REAL" in text
    assert "_load_real" in text and ".main(" in text
    assert "checkout_daemons" not in text
    assert "no question is invented" not in text
