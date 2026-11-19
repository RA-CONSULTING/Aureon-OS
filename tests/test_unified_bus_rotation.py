"""Opt-in size rotation for aureon_fusion/state/unified_bus.jsonl.

Real files under pytest tmp_path only. No market payloads, no network, no
credentials, no /dev/shm. The cap is AUREON_UNIFIED_BUS_MAX_BYTES.
"""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_BUS_NAME = "unified_bus.jsonl"


def _append(path, record):
    (_REPO / "aureon_fusion" / "state").mkdir(parents=True, exist_ok=True)
    from aureon_fusion.bus_bridge import _append_jsonl

    _append_jsonl(path, record)


def _bus_files(directory):
    found = []
    for path in directory.iterdir():
        if not path.is_file():
            continue
        if path.name == _BUS_NAME or path.name.startswith(_BUS_NAME + "."):
            found.append(path)
    return found


def _records(path):
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def _int_ids(directory):
    found = []
    for path in _bus_files(directory):
        for row in _records(path):
            if isinstance(row.get("i"), int):
                found.append(row["i"])
    return found


def _archives(directory):
    return [path for path in _bus_files(directory) if path.name != _BUS_NAME]


def _record(i, pad="p"):
    return {"i": i, "pad": pad * 48}


def test_off_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("AUREON_UNIFIED_BUS_MAX_BYTES", raising=False)
    path = tmp_path / _BUS_NAME
    for i in range(30):
        _append(path, _record(i))
    assert _int_ids(tmp_path) == list(range(30))
    assert [p.name for p in tmp_path.iterdir()] == [_BUS_NAME]
    assert not _archives(tmp_path)


def test_zero_and_bad_limits_do_not_rotate(tmp_path, monkeypatch):
    path = tmp_path / _BUS_NAME
    for raw in ("0", "-1", "not-a-number", ""):
        monkeypatch.setenv("AUREON_UNIFIED_BUS_MAX_BYTES", raw)
        _append(path, _record(len(_records(path))))
    assert _int_ids(tmp_path) == [0, 1, 2, 3]
    assert not _archives(tmp_path)


def test_rotates_at_cap_and_keeps_every_line(tmp_path, monkeypatch):
    path = tmp_path / _BUS_NAME
    _append(path, _record(0))
    one = path.stat().st_size
    monkeypatch.setenv("AUREON_UNIFIED_BUS_MAX_BYTES", str(one * 3))
    for i in range(1, 12):
        _append(path, _record(i))
    archives = _archives(tmp_path)
    assert archives
    assert path.exists()
    assert path.stat().st_size < one * 5
    assert sorted(_int_ids(tmp_path)) == list(range(12))
    # The live path is the file a tailer opens, and it is only the fresh tail.
    live = [row["i"] for row in _records(path)]
    assert live
    assert live != list(range(12))
    assert max(_int_ids(tmp_path)) in live


def test_never_removes_or_truncates_existing_files(tmp_path, monkeypatch):
    """Plant the names a backup-count rotator would overwrite, then rotate past them.

    AUREON_UNIFIED_BUS_BACKUPS is set on purpose. It must not be honoured:
    nothing that already exists may be deleted, replaced, or shortened.
    """
    path = tmp_path / _BUS_NAME
    planted = {
        "unified_bus.jsonl.1": b'{"i":"old-archive","n":1}\n',
        "unified_bus.jsonl.2": b'{"i":"old-archive","n":2}\n{"i":"old-archive","n":2}\n',
        "unified_bus.jsonl.19990101T000000000000Z.sentinel": (
            b'{"i":"sentinel","keep":true}\n' * 4
        ),
    }
    for name, payload in planted.items():
        (tmp_path / name).write_bytes(payload)

    _append(path, _record(0, pad="y"))
    one = path.stat().st_size
    monkeypatch.setenv("AUREON_UNIFIED_BUS_MAX_BYTES", str(max(1, one * 2)))
    # The thought-bus knob. Copying it would drop the oldest file. This must not.
    monkeypatch.setenv("AUREON_UNIFIED_BUS_BACKUPS", "1")

    def frozen_archives():
        return {p.name: p.read_bytes() for p in _archives(tmp_path)}

    frozen = frozen_archives()
    for name, payload in planted.items():
        assert frozen[name] == payload

    for i in range(1, 16):
        live_before = path.read_bytes()
        _append(path, _record(i, pad="y"))
        now = frozen_archives()
        for name, payload in frozen.items():
            assert name in now, name
            assert now[name] == payload
        live_now = path.read_bytes()
        if not live_now.startswith(live_before):
            created = [payload for name, payload in now.items() if name not in frozen]
            assert live_before in created
        frozen = now

    for name, payload in planted.items():
        assert (tmp_path / name).read_bytes() == payload
    assert sorted(_int_ids(tmp_path)) == list(range(16))
    rotated = [name for name in frozen if name not in planted]
    assert len(rotated) > 1
    assert path.exists()
    assert path.stat().st_size < one * 4


def test_concurrent_writers_keep_every_line(tmp_path, monkeypatch):
    path = tmp_path / _BUS_NAME
    cap = 12000
    writers = 4
    per_writer = 12
    monkeypatch.setenv("AUREON_UNIFIED_BUS_MAX_BYTES", str(cap))
    (_REPO / "aureon_fusion" / "state").mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["AUREON_UNIFIED_BUS_MAX_BYTES"] = str(cap)
    env["PYTHONPATH"] = str(_REPO) + os.pathsep + env.get("PYTHONPATH", "")
    ready = tmp_path / "reader.ready"
    stop = tmp_path / "reader.stop"
    stats = tmp_path / "reader.stats"
    reader = subprocess.Popen(
        [
            sys.executable,
            "-c",
            _READER,
            str(path),
            str(ready),
            str(stop),
            str(stats),
        ],
        cwd=str(_REPO),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.time() + 10
    while not ready.exists():
        if reader.poll() is not None:
            raise AssertionError(reader.stderr.read())
        if time.time() > deadline:
            reader.kill()
            raise AssertionError("tail reader did not start")
        time.sleep(0.01)

    procs = []
    for slot in range(writers):
        procs.append(
            subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    _WRITER,
                    str(path),
                    str(slot * per_writer),
                    str(per_writer),
                    str(cap),
                ],
                cwd=str(_REPO),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        )
    for proc in procs:
        try:
            _out, err = proc.communicate(timeout=40)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            raise
        assert proc.returncode == 0, err

    stop.write_text("stop\n", encoding="utf-8")
    try:
        _out, err = reader.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        reader.kill()
        reader.communicate()
        raise
    assert reader.returncode == 0, err
    opened, bad = (int(part) for part in stats.read_text(encoding="utf-8").split())
    assert opened > 0
    assert bad == 0

    ids = _int_ids(tmp_path)
    assert sorted(ids) == list(range(writers * per_writer))
    assert len(ids) == len(set(ids))
    for bus_file in _bus_files(tmp_path):
        text = bus_file.read_text(encoding="utf-8")
        assert text.endswith("\n")
        for line in text.splitlines():
            json.loads(line)
    archives = _archives(tmp_path)
    assert len(archives) >= 3
    assert path.exists()
    assert path.stat().st_size < cap + 8000

    # A tailer that opens the canonical path still sees the live file.
    _append(path, {"i": 100000, "pad": "c" * 5000})
    assert path.exists()
    assert any(row["i"] == 100000 for row in _records(path))
    assert sorted(_int_ids(tmp_path)) == list(range(writers * per_writer)) + [100000]


def test_tail_reader_finds_current_file(tmp_path, monkeypatch):
    path = tmp_path / _BUS_NAME
    monkeypatch.setenv("AUREON_UNIFIED_BUS_MAX_BYTES", "80")
    for i in range(6):
        _append(path, {"i": i, "pad": "t" * 40})
    assert path.is_file()
    archives = _archives(tmp_path)
    assert archives
    live_ids = [row["i"] for row in _records(path)]
    assert live_ids
    assert 0 not in live_ids
    newest = max(_int_ids(tmp_path))
    assert newest in live_ids

    with path.open("r", encoding="utf-8") as followed:
        followed.seek(0, os.SEEK_END)
        held_inode = os.fstat(followed.fileno()).st_ino
    _append(path, {"i": 99, "pad": "t" * 40})
    # Re-open by path, the way tail -F finds the file after a rotation.
    assert path.is_file()
    reopened = [row["i"] for row in _records(path)]
    assert 99 in reopened
    assert path.stat().st_ino != held_inode or 99 in live_ids
    # The file the held descriptor still names was moved, not truncated.
    moved = [
        candidate
        for candidate in _bus_files(tmp_path)
        if candidate.stat().st_ino == held_inode
    ]
    assert len(moved) == 1
    assert moved[0].stat().st_size > 0


def test_missing_renameat2_still_rotates_without_replacing(tmp_path, monkeypatch):
    """macOS and other POSIX hosts have no renameat2. The cap still applies."""
    import errno

    import aureon_fusion.bus_bridge as bridge

    def _missing(src, dst):
        raise OSError(errno.ENOSYS, "renameat2 unavailable")

    monkeypatch.setattr(bridge, "_rename_noreplace_linux", _missing)
    monkeypatch.setattr(bridge, "_rename_noreplace_darwin", _missing)
    used = {"link": 0}
    real_link = bridge._rename_noreplace_link

    def _count_link(src, dst):
        used["link"] += 1
        real_link(src, dst)

    monkeypatch.setattr(bridge, "_rename_noreplace_link", _count_link)

    src = tmp_path / "src.jsonl"
    taken = tmp_path / "taken.jsonl"
    src.write_bytes(b"live-bytes\n")
    taken.write_bytes(b"already-there\n")
    try:
        bridge._rename_noreplace(src, taken)
    except FileExistsError:
        pass
    else:
        raise AssertionError("an existing file was replaced")
    assert src.read_bytes() == b"live-bytes\n"
    assert taken.read_bytes() == b"already-there\n"
    used["link"] = 0

    planted = tmp_path / "unified_bus.jsonl.1"
    planted.write_bytes(b'{"i":"kept"}\n')
    path = tmp_path / _BUS_NAME
    monkeypatch.setenv("AUREON_UNIFIED_BUS_MAX_BYTES", "80")
    for i in range(6):
        _append(path, {"i": i, "pad": "m" * 40})
    fresh = [item for item in _archives(tmp_path) if item.name != planted.name]
    assert fresh
    assert used["link"] >= 1
    assert planted.read_bytes() == b'{"i":"kept"}\n'
    assert sorted(_int_ids(tmp_path)) == list(range(6))
    assert path.is_file()
    assert max(_int_ids(tmp_path)) in [row["i"] for row in _records(path)]


def test_two_writers_in_the_rotate_window_keep_every_line(tmp_path, monkeypatch):
    """Two writers meet after both have linked the live file and before either drops it.

    The rotation lock keeps the second writer out of that window. Without the
    lock the second unlink removes the line the first writer just stored, and
    this fails every time. A planted archive must stay byte-for-byte.
    """
    import errno

    import aureon_fusion.bus_bridge as bridge

    def _missing(src, dst):
        raise OSError(errno.ENOSYS, "native rename unavailable")

    monkeypatch.setattr(bridge, "_rename_noreplace_linux", _missing)
    monkeypatch.setattr(bridge, "_rename_noreplace_darwin", _missing)

    path = tmp_path / _BUS_NAME
    monkeypatch.delenv("AUREON_UNIFIED_BUS_MAX_BYTES", raising=False)
    _append(path, {"i": 0, "pad": "s" * 40})
    seed = path.read_bytes()
    planted = tmp_path / "unified_bus.jsonl.1"
    planted_bytes = b'{"i":"planted"}\n'
    planted.write_bytes(planted_bytes)
    monkeypatch.setenv("AUREON_UNIFIED_BUS_MAX_BYTES", "1")

    state = {
        "n": 0,
        "owner": None,
        "event": threading.Event(),
        "second": threading.Event(),
    }
    gate = threading.Lock()

    def _meet(live):
        with gate:
            state["n"] += 1
            n = state["n"]
            if n == 1:
                state["owner"] = threading.get_ident()
        if n == 1:
            # The second writer arrives only when the rotation lock does not
            # exclude it. A timeout means it is blocked on that lock.
            state["second"].wait(timeout=0.5)
            return
        state["second"].set()
        state["event"].wait()

    monkeypatch.setattr(bridge, "_rotation_window_hook", _meet)

    errors = []

    def _writer(i):
        try:
            _append(path, {"i": i, "pad": "w" * 40})
        except Exception as exc:
            errors.append(exc)
        finally:
            if threading.get_ident() == state["owner"]:
                state["event"].set()

    threads = [threading.Thread(target=_writer, args=(i,)) for i in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(5)
        assert not thread.is_alive()
    assert errors == []
    assert planted.read_bytes() == planted_bytes
    assert any(archive.read_bytes() == seed for archive in _archives(tmp_path))
    assert _int_ids(tmp_path).count(0) == 1
    assert _int_ids(tmp_path).count(1) == 1
    assert _int_ids(tmp_path).count(2) == 1
    for bus_file in _bus_files(tmp_path):
        for line in bus_file.read_text(encoding="utf-8").splitlines():
            if line:
                json.loads(line)


def test_link_rename_rolls_back_if_the_old_name_cannot_be_dropped(tmp_path, monkeypatch):
    import aureon_fusion.bus_bridge as bridge

    src = tmp_path / "src.jsonl"
    dst = tmp_path / "dst.jsonl"
    src.write_bytes(b"same-bytes\n")
    real_unlink = os.unlink

    def _unlink(path, *args, **kwargs):
        if os.fspath(path) == os.fspath(src):
            raise PermissionError("busy")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", _unlink)
    try:
        bridge._rename_noreplace_link(src, dst)
    except PermissionError:
        pass
    else:
        raise AssertionError("the source name was dropped")
    assert src.read_bytes() == b"same-bytes\n"
    assert not dst.exists()


_WRITER = r"""
import os
import sys
from pathlib import Path

os.environ["AUREON_UNIFIED_BUS_MAX_BYTES"] = sys.argv[4]
from aureon_fusion.bus_bridge import _append_jsonl

path = Path(sys.argv[1])
start = int(sys.argv[2])
count = int(sys.argv[3])
for i in range(start, start + count):
    _append_jsonl(path, {"i": i, "w": start, "pad": "c" * 5000})
"""


_READER = r"""
import json
import sys
import time
from pathlib import Path

path = Path(sys.argv[1])
ready = Path(sys.argv[2])
stop = Path(sys.argv[3])
stats = Path(sys.argv[4])
opened = 0
bad = 0
ready.write_text("ready\n", encoding="utf-8")
while not stop.exists():
    if path.exists():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            time.sleep(0.002)
            continue
        opened += 1
        lines = text.splitlines()
        if text and not text.endswith("\n") and lines:
            lines = lines[:-1]
        for line in lines:
            try:
                json.loads(line)
            except json.JSONDecodeError:
                bad += 1
    time.sleep(0.002)
stats.write_text(f"{opened} {bad}\n", encoding="utf-8")
"""
