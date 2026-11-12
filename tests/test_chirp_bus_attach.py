"""Attach-first shared-memory behaviour for the chirp ring buffer.

These tests use unique aureon_test_* segment names only. They do not
touch the live aureon_chirp_bus segment. No network, no orders.
"""

from __future__ import annotations

import gc
import multiprocessing as mp
import os
import uuid
from multiprocessing import shared_memory
from typing import Any

from aureon.core.aureon_chirp_bus import ChirpDirection, ChirpPacket, ChirpRingBuffer, ChirpType

_LIVE_BUS_NAME = "aureon_chirp_bus"


def _unique_test_name() -> str:
    name = f"aureon_test_{uuid.uuid4().hex}"
    if name == _LIVE_BUS_NAME or not name.startswith("aureon_test_"):
        raise RuntimeError("refusing to use a non-test chirp segment name")
    return name


def _unlink_test_segment(name: str) -> None:
    if not name.startswith("aureon_test_"):
        raise RuntimeError("refusing to unlink a non-test segment")
    try:
        try:
            shm = shared_memory.SharedMemory(name=name, create=False, track=False)
        except TypeError:
            shm = shared_memory.SharedMemory(name=name, create=False)
        shm.close()
        shm.unlink()
    except FileNotFoundError:
        return
    except Exception:
        return



def _attach_test_segment(name: str) -> shared_memory.SharedMemory:
    if not name.startswith("aureon_test_"):
        raise RuntimeError("refusing to attach a non-test segment")
    try:
        return shared_memory.SharedMemory(name=name, create=False, track=False)
    except TypeError:
        shm = shared_memory.SharedMemory(name=name, create=False)
        try:
            from multiprocessing import resource_tracker
            resource_tracker.unregister(shm._name, "shared_memory")
        except Exception:
            pass
        return shm


def _ping_bytes() -> bytes:
    return ChirpPacket(message_type=ChirpType.PING, direction=ChirpDirection.DOWN).to_bytes()


def _owner_flag(buffer: ChirpRingBuffer) -> bool | None:
    return getattr(buffer, "_owner", None)


def _fd_inode(buffer: ChirpRingBuffer) -> int:
    assert buffer.shm is not None
    return os.fstat(buffer.shm._fd).st_ino


def _inode_from_maps(pid: int, name: str) -> tuple[int, bool]:
    """Return (inode, deleted) for /dev/shm/<name> in /proc/<pid>/maps."""
    if not name.startswith("aureon_test_"):
        raise RuntimeError("refusing to inspect a non-test segment")
    target = f"/dev/shm/{name}"
    found: list[tuple[int, bool]] = []
    with open(f"/proc/{pid}/maps", encoding="utf-8") as fh:
        for line in fh:
            if target not in line:
                continue
            parts = line.split()
            found.append((int(parts[4]), "(deleted)" in line))
    if not found:
        raise AssertionError(f"{target} not mapped in pid {pid}")
    inodes = {inode for inode, _ in found}
    if len(inodes) != 1:
        raise AssertionError(f"pid {pid} maps multiple inodes for {name}: {found}")
    return found[0][0], any(deleted for _, deleted in found)


def _process_hold_bus(name: str, ready: Any, hold: Any, report: Any) -> None:
    """Create or attach a ChirpBus in a real child process, then wait."""
    if not name.startswith("aureon_test_"):
        raise RuntimeError("refusing to use a non-test chirp segment name")
    from aureon.core.aureon_chirp_bus import ChirpBus

    bus = ChirpBus(name=name, create=True)
    if not bus.ring._initialized or bus.ring.shm is None:
        report.put({"ok": False, "error": "not initialized"})
        ready.set()
        return
    report.put({
        "ok": True,
        "pid": os.getpid(),
        "fd_inode": os.fstat(bus.ring.shm._fd).st_ino,
        "owner": getattr(bus.ring, "_owner", None),
    })
    ready.set()
    hold.wait(timeout=60)


def test_two_create_true_share_one_segment_and_second_does_not_unlink() -> None:
    name = _unique_test_name()
    first = second = None
    try:
        first = ChirpRingBuffer(name=name, create=True)
        assert first._initialized
        if _owner_flag(first) is not None:
            assert _owner_flag(first) is True
        inode = _fd_inode(first)

        second = ChirpRingBuffer(name=name, create=True)
        assert second._initialized
        if _owner_flag(second) is not None:
            assert _owner_flag(second) is False
        assert _fd_inode(second) == inode
        maps_first, deleted_first = _inode_from_maps(os.getpid(), name)
        assert deleted_first is False
        assert maps_first == inode

        payload = _ping_bytes()
        assert first.write(payload)
        assert second.read() == payload

        second.close()
        assert first.write(payload)
        assert first.read() == payload

        still_there = _attach_test_segment(name)
        still_there.close()
    finally:
        if second is not None:
            second.close()
        if first is not None:
            first.close()
        _unlink_test_segment(name)


def test_non_owner_close_or_delete_does_not_unlink() -> None:
    name = _unique_test_name()
    owner = None
    try:
        owner = ChirpRingBuffer(name=name, create=True)
        assert owner._initialized
        if _owner_flag(owner) is not None:
            assert _owner_flag(owner) is True
        inode = _fd_inode(owner)

        non_owner = ChirpRingBuffer(name=name, create=True)
        if _owner_flag(non_owner) is not None:
            assert _owner_flag(non_owner) is False
        assert _fd_inode(non_owner) == inode
        non_owner.close()

        probe = _attach_test_segment(name)
        probe.close()
        assert os.stat(f"/dev/shm/{name}").st_ino == inode

        non_owner2 = ChirpRingBuffer(name=name, create=True)
        if _owner_flag(non_owner2) is not None:
            assert _owner_flag(non_owner2) is False
        assert _fd_inode(non_owner2) == inode
        del non_owner2
        gc.collect()
        assert os.stat(f"/dev/shm/{name}").st_ino == inode

        probe = _attach_test_segment(name)
        probe.close()
        payload = _ping_bytes()
        assert owner.write(payload)
        assert owner.read() == payload
    finally:
        if owner is not None:
            owner.close()
        _unlink_test_segment(name)


def test_owner_close_unlinks() -> None:
    name = _unique_test_name()
    owner = ChirpRingBuffer(name=name, create=True)
    try:
        assert owner._initialized
        if _owner_flag(owner) is not None:
            assert _owner_flag(owner) is True
        owner.close()
        try:
            leftover = _attach_test_segment(name)
        except FileNotFoundError:
            leftover = None
        if leftover is not None:
            leftover.close()
            raise AssertionError("owner close left the segment in place")
    finally:
        _unlink_test_segment(name)


def test_two_processes_map_the_same_inode() -> None:
    name = _unique_test_name()
    ctx = mp.get_context("spawn")
    ready_a = ctx.Event()
    ready_b = ctx.Event()
    hold_a = ctx.Event()
    hold_b = ctx.Event()
    report_a = ctx.Queue()
    report_b = ctx.Queue()
    proc_a = ctx.Process(target=_process_hold_bus, args=(name, ready_a, hold_a, report_a))
    proc_b = ctx.Process(target=_process_hold_bus, args=(name, ready_b, hold_b, report_b))
    try:
        proc_a.start()
        assert ready_a.wait(timeout=30), "process A did not attach"
        info_a = report_a.get(timeout=5)
        assert info_a["ok"], info_a
        if info_a["owner"] is not None:
            assert info_a["owner"] is True
        maps_a, deleted_a = _inode_from_maps(info_a["pid"], name)
        assert deleted_a is False
        assert maps_a == info_a["fd_inode"]
        path_inode = os.stat(f"/dev/shm/{name}").st_ino
        assert path_inode == maps_a

        proc_b.start()
        assert ready_b.wait(timeout=30), "process B did not attach"
        info_b = report_b.get(timeout=5)
        assert info_b["ok"], info_b
        if info_b["owner"] is not None:
            assert info_b["owner"] is False
        maps_b, deleted_b = _inode_from_maps(info_b["pid"], name)
        maps_a_again, deleted_a_again = _inode_from_maps(info_a["pid"], name)
        assert deleted_b is False
        assert deleted_a_again is False
        assert maps_b == info_b["fd_inode"] == maps_a_again == maps_a

        hold_b.set()
        proc_b.join(timeout=30)
        assert proc_b.exitcode == 0
        path_after = os.stat(f"/dev/shm/{name}").st_ino
        maps_after, deleted_after = _inode_from_maps(info_a["pid"], name)
        assert deleted_after is False
        assert path_after == maps_after == maps_a
    finally:
        hold_b.set()
        hold_a.set()
        proc_a.join(timeout=10)
        if proc_b.is_alive():
            proc_b.join(timeout=10)
        if proc_a.is_alive():
            proc_a.terminate()
        if proc_b.is_alive():
            proc_b.terminate()
        _unlink_test_segment(name)
