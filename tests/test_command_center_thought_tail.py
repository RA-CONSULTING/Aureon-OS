"""Tests for the command center's cross-process ThoughtBus tail (#358)."""

from __future__ import annotations

import ast
import asyncio
import json
import os
import time
from pathlib import Path

import pytest

from aureon.command_centers.thought_tail import SeenIds, ThoughtTail, next_local

CC = Path(__file__).resolve().parents[1] / "aureon" / "command_centers" / "aureon_command_center.py"


def _line(i: int, pad: str = "") -> str:
    return json.dumps({"id": f"t{i}", "topic": "x", "source": "other", "payload": {"i": i, "pad": pad}}) + "\n"


def _write(path: Path, *lines: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.writelines(lines)


def _ids(rows: list[dict]) -> list[str]:
    return [r["id"] for r in rows]


def _drain(tail: ThoughtTail) -> list[dict]:
    out: list[dict] = []
    for _ in range(10_000):
        rows = tail.read_new()
        if not rows:
            return out
        out.extend(rows)
    raise AssertionError("tail never drained")


def _poll(tail: ThoughtTail, calls: int = 50) -> list[dict]:
    """Call read_new a fixed number of times, like the listener loop does.

    Skipping an oversized line moves the position without returning rows, so
    an empty read does not mean the file is drained.
    """
    out: list[dict] = []
    for _ in range(calls):
        out.extend(tail.read_new())
    return out


def test_starts_at_end_and_reads_new_lines(tmp_path: Path) -> None:
    p = tmp_path / "thoughts.jsonl"
    _write(p, _line(0))
    tail = ThoughtTail.at_end(p)
    assert tail.read_new() == []
    _write(p, _line(1), _line(2))
    assert _ids(tail.read_new()) == ["t1", "t2"]
    assert tail.read_new() == []


def test_missing_file_then_created(tmp_path: Path) -> None:
    p = tmp_path / "thoughts.jsonl"
    tail = ThoughtTail.at_end(p)
    assert tail.read_new() == []
    _write(p, _line(1))
    assert _ids(tail.read_new()) == ["t1"]


def test_partial_line_is_held_until_newline(tmp_path: Path) -> None:
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    tail = ThoughtTail.at_end(p)
    whole = _line(1)
    _write(p, whole[:10])
    assert tail.read_new() == []
    _write(p, whole[10:])
    assert _ids(tail.read_new()) == ["t1"]


def test_malformed_lines_are_skipped(tmp_path: Path) -> None:
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    tail = ThoughtTail.at_end(p)
    _write(p, "not json\n", "[1, 2]\n", _line(3))
    assert _ids(tail.read_new()) == ["t3"]


def test_truncate_in_place_restarts_from_top(tmp_path: Path) -> None:
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    tail = ThoughtTail.at_end(p)
    _write(p, _line(1), _line(2), _line(3))
    assert _ids(tail.read_new()) == ["t1", "t2", "t3"]
    with open(p, "w", encoding="utf-8") as f:
        f.write(_line(4))
    assert _ids(tail.read_new()) == ["t4"]


def test_rename_rotation_drains_old_file_then_reads_new_past_old_offset(tmp_path: Path) -> None:
    """The new file is longer than the old offset, so the shrink reset cannot
    stand in for a missing inode switch."""
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    tail = ThoughtTail.at_end(p)
    _write(p, _line(1))
    assert _ids(tail.read_new()) == ["t1"]
    _write(p, _line(2), _line(3))  # written after the last read, then rotated away
    os.replace(p, tmp_path / "thoughts.jsonl.1")
    _write(p, *[_line(i, pad="y" * 200) for i in range(4, 10)])
    assert p.stat().st_size > (tmp_path / "thoughts.jsonl.1").stat().st_size
    assert _ids(_drain(tail)) == [f"t{i}" for i in range(2, 10)]


def test_real_thought_bus_rotation_loses_no_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Rotate through ThoughtBus (#355) and read after every third write."""
    from aureon.core.aureon_thought_bus import Thought, ThoughtBus

    monkeypatch.setenv("AUREON_THOUGHT_BUS_MAX_BYTES", "600")
    monkeypatch.setenv("AUREON_THOUGHT_BUS_BACKUPS", "1")
    p = tmp_path / "thoughts.jsonl"
    bus = ThoughtBus(persist_path=str(p))
    tail = ThoughtTail.at_end(p)
    sent: list[str] = []
    got: list[str] = []
    for i in range(30):
        t = bus.publish(Thought(source="other", topic="x", payload={"i": i}))
        sent.append(t.id)
        if i % 3 == 2:
            got.extend(_ids(_drain(tail)))
    got.extend(_ids(_drain(tail)))
    assert (tmp_path / "thoughts.jsonl.1").exists(), "rotation did not happen"
    assert got == sent


def test_backlog_bigger_than_cap_is_read_in_bounded_chunks(tmp_path: Path) -> None:
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    cap = 1000
    tail = ThoughtTail.at_end(p, max_read_bytes=cap)
    _write(p, *[_line(i, pad="z" * 20) for i in range(200)])
    assert p.stat().st_size > 5 * cap
    got: list[str] = []
    calls = 0
    while True:
        chunk = tail.read_raw()
        if not chunk:
            break
        assert len(chunk) <= cap
        got.extend(json.loads(x)["id"] for x in chunk.splitlines())
        calls += 1
    assert calls > 5
    assert got == [f"t{i}" for i in range(200)]


def test_seen_ids_dedupes_either_order_and_is_tied_to_read_cap() -> None:
    seen = SeenIds(max_read_bytes=1000, min_line_bytes=100)
    assert seen.limit == 20
    assert seen.first_time("a") is True   # file copy first (persist before handlers)
    assert seen.first_time("a") is False  # queue copy skipped
    assert seen.first_time("b") is True   # queue copy first
    assert seen.first_time("b") is False  # file copy skipped
    assert seen.first_time(None) is True  # no id: cannot be matched, always handled
    assert seen.first_time(None) is True
    for i in range(25):
        seen.first_time(f"n{i}")
    assert len(seen._ids) == 20
    assert seen.first_time("a") is True  # evicted, oldest first


def test_next_local_times_out_so_the_tail_still_runs() -> None:
    async def run() -> tuple[object, float, object]:
        q: asyncio.Queue = asyncio.Queue()
        t0 = time.monotonic()
        empty = await next_local(q, timeout=0.05)
        waited = time.monotonic() - t0
        q.put_nowait("thought")
        full = await next_local(q, timeout=0.05)
        return empty, waited, full

    empty, waited, full = asyncio.run(asyncio.wait_for(run(), timeout=5))
    assert empty is None
    assert waited < 1.0
    assert full == "thought"


def _listener_source() -> str:
    tree = ast.parse(CC.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "thought_bus_listener_task":
            return ast.unparse(node)
    raise AssertionError("thought_bus_listener_task not found")


def test_listener_uses_timeout_and_one_shared_dedupe() -> None:
    src = _listener_source()
    assert "await queue.get()" not in src
    assert "next_local(queue" in src
    assert src.count("seen.first_time(") == 2
    assert "mark_seen" not in src
    assert "tail.read_new()" in src


def test_line_longer_than_cap_is_skipped_and_later_lines_arrive(tmp_path: Path) -> None:
    """Spike's and Buzz's wedge: one line over the cap must not stop the tail."""
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    cap = 1000
    tail = ThoughtTail.at_end(p, max_read_bytes=cap)
    big = _line(0, pad="b" * 2000)
    _write(p, big, _line(1))
    assert _ids(_poll(tail)) == ["t1"]
    _write(p, _line(2))
    assert _ids(_poll(tail)) == ["t2"]
    assert tail.take_skipped() == (1, len(big))
    assert tail.take_skipped() == (0, 0)


def test_line_many_times_the_cap_still_written_is_skipped_once(tmp_path: Path) -> None:
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    cap = 256
    tail = ThoughtTail.at_end(p, max_read_bytes=cap)
    big = _line(0, pad="c" * (5 * cap))
    _write(p, big[:600])  # still being written, already over the cap
    assert _poll(tail) == []
    _write(p, big[600:], _line(1), _line(2))
    assert _ids(_poll(tail)) == ["t1", "t2"]
    assert tail.take_skipped() == (1, len(big))


def test_short_partial_line_is_not_skipped(tmp_path: Path) -> None:
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    tail = ThoughtTail.at_end(p, max_read_bytes=1000)
    whole = _line(1)
    _write(p, whole[:-5])
    assert _poll(tail) == []
    _write(p, whole[-5:])
    assert _ids(_poll(tail)) == ["t1"]
    assert tail.take_skipped() == (0, 0)


def test_skipping_an_oversized_line_does_not_count_as_drained_on_rotation(tmp_path: Path) -> None:
    """While a long line is being skipped the old file is not finished, so a
    rename must not make the tail jump to the new file and lose t1."""
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    cap = 256
    tail = ThoughtTail.at_end(p, max_read_bytes=cap)
    _write(p, _line(0, pad="d" * (4 * cap)), _line(1))
    os.replace(p, tmp_path / "thoughts.jsonl.1")
    _write(p, _line(2))
    assert _ids(_poll(tail)) == ["t1", "t2"]
    assert tail.take_skipped()[0] == 1


def test_listener_logs_skipped_lines() -> None:
    src = _listener_source()
    assert "tail.take_skipped()" in src


def test_truncate_during_a_skip_resets_the_skip(tmp_path: Path) -> None:
    """A truncate mid-skip must not swallow the first line of the new content."""
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    cap = 256
    tail = ThoughtTail.at_end(p, max_read_bytes=cap)
    _write(p, _line(0, pad="e" * (4 * cap))[:600])  # oversized, no newline yet
    assert _poll(tail) == []
    with open(p, "w", encoding="utf-8") as f:
        f.write(_line(1))
    assert _ids(_poll(tail)) == ["t1"]


def test_unfinished_skip_is_counted_on_rotation_without_a_newline(tmp_path: Path) -> None:
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    cap = 256
    tail = ThoughtTail.at_end(p, max_read_bytes=cap)
    _write(p, _line(0, pad="f" * (4 * cap))[:600])  # oversized, never finished
    assert _poll(tail) == []
    os.replace(p, tmp_path / "thoughts.jsonl.1")
    _write(p, _line(1))
    assert _ids(_poll(tail)) == ["t1"]
    assert tail.take_skipped() == (1, 600)


def test_skip_end_returns_exactly_the_following_lines(tmp_path: Path) -> None:
    """No fragment of the skipped line, and not its newline, reaches read_raw."""
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    cap = 256
    tail = ThoughtTail.at_end(p, max_read_bytes=cap)
    _write(p, _line(0, pad="g" * (3 * cap)), _line(1), _line(2))
    raw = b"".join(tail.read_raw() for _ in range(50))
    assert raw == (_line(1) + _line(2)).encode()
