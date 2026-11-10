"""Tests for the self-repair progress ledger (owner's call, 11:54 GMT)."""

from __future__ import annotations

import json
from pathlib import Path

from aureon.autonomous import queen_repair_progress as P


def test_is_narrower_moves_deeper_only():
    assert P.is_narrower("ImportError", "AssertionError") is True
    assert P.is_narrower("NameError", "TypeError") is True
    assert P.is_narrower("", "AssertionError") is True
    # Not narrower: same, shallower, or onto an import error.
    assert P.is_narrower("AssertionError", "AssertionError") is False
    assert P.is_narrower("AssertionError", "ImportError") is False
    assert P.is_narrower("TypeError", "") is False


def test_record_and_read_reverted_changes(tmp_path: Path):
    P.record_cycle(
        tmp_path,
        fixed=["tests/t.py::test_a"],
        narrowed=[{"test": "tests/t.py::test_b", "from": "ImportError", "to": "AssertionError"}],
        attempts=[
            {"path": "m.py", "change": "a - b -> a + b", "result": "reverted_regression"},
            {"path": "n.py", "change": "x -> y", "result": "kept"},
            {"path": "o.py", "change": "p -> q", "result": "reverted_inert"},
        ],
        committed=True,
        reason="partial_progress",
    )
    keys = P.reverted_changes(tmp_path)
    assert "m.py::a - b -> a + b" in keys
    assert "o.py::p -> q" in keys
    # A kept edit is not a dead end; it must not block a future retry.
    assert "n.py::x -> y" not in keys


def test_reverted_changes_empty_when_no_ledger(tmp_path: Path):
    assert P.reverted_changes(tmp_path) == set()
