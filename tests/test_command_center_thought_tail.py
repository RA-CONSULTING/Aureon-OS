import json
import os

from aureon.command_centers.thought_tail import ThoughtTail


def _write(path, *ids, mode="a"):
    with open(path, mode, encoding="utf-8") as f:
        for i in ids:
            f.write(json.dumps({"id": i, "topic": "t", "payload": {"i": i}, "source": "s"}) + "\n")


def _ids(rows):
    return [r["id"] for r in rows]


def test_starts_at_end_and_reads_only_new_lines(tmp_path):
    p = tmp_path / "thoughts.jsonl"
    _write(p, "a", "b")
    tail = ThoughtTail.at_end(p)
    assert tail.read_new() == []
    _write(p, "c", "d")
    assert _ids(tail.read_new()) == ["c", "d"]
    assert tail.read_new() == []


def test_missing_file_then_created(tmp_path):
    p = tmp_path / "thoughts.jsonl"
    tail = ThoughtTail.at_end(p)
    assert tail.read_new() == []
    _write(p, "a")
    assert _ids(tail.read_new()) == ["a"]


def test_partial_last_line_waits_for_newline(tmp_path):
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    tail = ThoughtTail.at_end(p)
    with open(p, "a", encoding="utf-8") as f:
        f.write('{"id": "a", "topic": "t"')
    assert tail.read_new() == []
    with open(p, "a", encoding="utf-8") as f:
        f.write(', "payload": {}}\n')
    assert _ids(tail.read_new()) == ["a"]


def test_rotation_inode_change_restarts_from_top(tmp_path):
    p = tmp_path / "thoughts.jsonl"
    _write(p, "a", "b", "c")
    tail = ThoughtTail.at_end(p)
    os.replace(p, tmp_path / "thoughts.jsonl.1")
    _write(p, "d")
    assert _ids(tail.read_new()) == ["d"]


def test_truncation_restarts_from_top(tmp_path):
    p = tmp_path / "thoughts.jsonl"
    _write(p, "a", "b", "c")
    tail = ThoughtTail.at_end(p)
    _write(p, "x", mode="w")
    assert _ids(tail.read_new()) == ["x"]


def test_skips_thoughts_seen_in_process_and_bad_lines(tmp_path):
    p = tmp_path / "thoughts.jsonl"
    p.write_text("")
    tail = ThoughtTail.at_end(p)
    tail.mark_seen("mine")
    _write(p, "mine", "theirs")
    with open(p, "a", encoding="utf-8") as f:
        f.write("not json\n[1, 2]\n")
    assert _ids(tail.read_new()) == ["theirs"]


def test_seen_set_is_bounded(tmp_path):
    tail = ThoughtTail.at_end(tmp_path / "x")
    tail.seen_limit = 3
    for i in range(10):
        tail.mark_seen(str(i))
    assert list(tail._seen) == ["7", "8", "9"]
