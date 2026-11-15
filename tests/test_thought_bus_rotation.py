import json

from aureon.core.aureon_thought_bus import Thought, ThoughtBus


def _thought(i):
    return Thought(source="test", topic="rotation.test", payload={"i": i})


def _lines(path):
    if not path.exists():
        return []
    return [json.loads(x)["payload"]["i"] for x in path.read_text().splitlines() if x]


def test_no_limit_keeps_appending(tmp_path, monkeypatch):
    monkeypatch.delenv("AUREON_THOUGHT_BUS_MAX_BYTES", raising=False)
    path = tmp_path / "thoughts.jsonl"
    bus = ThoughtBus(persist_path=str(path))
    for i in range(50):
        bus._persist(_thought(i))
    assert _lines(path) == list(range(50))
    assert not (tmp_path / "thoughts.jsonl.1").exists()


def test_rotates_at_limit_and_loses_nothing(tmp_path, monkeypatch):
    path = tmp_path / "thoughts.jsonl"
    bus = ThoughtBus(persist_path=str(path))
    bus._persist(_thought(0))
    one_line = path.stat().st_size
    monkeypatch.setenv("AUREON_THOUGHT_BUS_MAX_BYTES", str(one_line * 3))
    for i in range(1, 10):
        bus._persist(_thought(i))
    assert path.stat().st_size < one_line * 4
    rotated = _lines(tmp_path / "thoughts.jsonl.1")
    current = _lines(path)
    assert rotated and current
    assert rotated[-1] + 1 == current[0]
    assert not (tmp_path / "thoughts.jsonl.2").exists()


def test_backups_shift_up(tmp_path, monkeypatch):
    path = tmp_path / "thoughts.jsonl"
    bus = ThoughtBus(persist_path=str(path))
    bus._persist(_thought(0))
    one_line = path.stat().st_size
    monkeypatch.setenv("AUREON_THOUGHT_BUS_MAX_BYTES", str(one_line * 2))
    monkeypatch.setenv("AUREON_THOUGHT_BUS_BACKUPS", "3")
    for i in range(1, 20):
        bus._persist(_thought(i))
    kept = []
    for name in ("thoughts.jsonl.3", "thoughts.jsonl.2", "thoughts.jsonl.1", "thoughts.jsonl"):
        kept += _lines(tmp_path / name)
    assert kept == list(range(kept[0], 20))
    assert not (tmp_path / "thoughts.jsonl.4").exists()


def test_bad_limit_value_is_ignored(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_THOUGHT_BUS_MAX_BYTES", "not-a-number")
    path = tmp_path / "thoughts.jsonl"
    bus = ThoughtBus(persist_path=str(path))
    for i in range(5):
        bus._persist(_thought(i))
    assert _lines(path) == list(range(5))


def test_failed_rotation_still_writes(tmp_path, monkeypatch):
    import os
    path = tmp_path / "thoughts.jsonl"
    bus = ThoughtBus(persist_path=str(path))
    bus._persist(_thought(0))
    monkeypatch.setenv("AUREON_THOUGHT_BUS_MAX_BYTES", "1")

    def refuse(src, dst):
        raise PermissionError("file in use")

    monkeypatch.setattr(os, "replace", refuse)
    for i in range(1, 4):
        bus._persist(_thought(i))
    assert _lines(path) == [0, 1, 2, 3]
