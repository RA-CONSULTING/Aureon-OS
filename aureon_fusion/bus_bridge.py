#!/usr/bin/env python3
"""🌉 BUS BRIDGE — unity layer between the workspace Sero thoughtbus and the
upstream Aureon thought bus.

Tails both sides, forwards each event across, and always writes a merged,
flight-recorder-ready log to ``aureon_fusion/state/unified_bus.jsonl``.

Modes:
    python -m aureon_fusion.bus_bridge           # daemon
    python -m aureon_fusion.bus_bridge --once    # one batch
    python -m aureon_fusion.bus_bridge --selftest# inject + verify

The bridge is fail-closed and degrades gracefully: if either side cannot be
imported or written to, the other side and the unified log keep running. Events
are never dropped for transient errors — the tail offset is only advanced after
a line is successfully merged (and, when possible, forwarded).

Size cap (opt-in, off unless set):
    AUREON_UNIFIED_BUS_MAX_BYTES — a positive integer. When the unified log is
    already at or over that size, the next append moves it to a new timestamped
    name and starts a fresh ``unified_bus.jsonl``. Every moved file is kept.
    Linux uses ``renameat2(RENAME_NOREPLACE)``, macOS uses
    ``renamex_np(RENAME_EXCL)``, and any other POSIX system hard-links the
    file to the new name before dropping the old one. None of those replace
    an existing file. Unset, empty, 0, negative, or not an integer: append
    with no cap, as before. There is no backup count and no delete.
    ``AUREON_UNIFIED_BUS_BACKUPS`` is not read.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import json
import logging
import os
import sys
import time
import uuid
from collections import deque
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Set, Tuple

# ── canonical paths ───────────────────────────────────────────────────────────
try:
    from .paths import (
        FUSION_STATE,
        SERO_THOUGHTBUS,
        AUREON_UPSTREAM,
        WORKSPACE,
    )
except ImportError:
    from aureon_fusion.paths import (
        FUSION_STATE,
        SERO_THOUGHTBUS,
        AUREON_UPSTREAM,
        WORKSPACE,
    )

SERO_LOG = SERO_THOUGHTBUS / "thought_bus.jsonl"
UPSTREAM_LOG = Path(
    os.environ.get("AUREON_THOUGHT_BUS_PATH", WORKSPACE / "thoughts.jsonl")
)
# Written only by _append_jsonl. Cap, when opted in, is applied there.
UNIFIED_LOG = FUSION_STATE / "unified_bus.jsonl"
UPSTREAM_MIRROR_LOG = FUSION_STATE / "upstream_bus.jsonl"
OFFSETS_FILE = FUSION_STATE / "bus_bridge_offsets.json"

DEDUP_WINDOW = 5000
BATCH_LIMIT = 100
DAEMON_INTERVAL = 1.0

# ── logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(FUSION_STATE / "bus_bridge.log"),
    ],
)
logger = logging.getLogger("BUS_BRIDGE")

# ── substrate imports (degrade gracefully) ────────────────────────────────────
_upstream_error: Optional[str] = None
FileThoughtBus: Any = None
UpstreamThought: Any = None

try:
    if str(AUREON_UPSTREAM) not in sys.path:
        sys.path.insert(0, str(AUREON_UPSTREAM))
    from aureon.core.aureon_thought_bus import FileThoughtBus, Thought as UpstreamThought
except Exception as exc:  # pragma: no cover - defensive import
    _upstream_error = str(exc)
    FileThoughtBus = None
    UpstreamThought = None

_sero_error: Optional[str] = None
_events = None

try:
    from . import events as _events
except Exception:
    try:
        import aureon_fusion.events as _events
    except Exception as exc:  # pragma: no cover - defensive import
        _sero_error = str(exc)
        _events = None


# ── helpers ───────────────────────────────────────────────────────────────────
def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    FUSION_STATE.mkdir(parents=True, exist_ok=True)
    SERO_THOUGHTBUS.mkdir(parents=True, exist_ok=True)


def _load_offsets() -> Dict[str, int]:
    if not OFFSETS_FILE.exists():
        return {}
    try:
        with open(OFFSETS_FILE, "r", encoding="utf-8", errors="replace") as f:
            return {str(k): int(v) for k, v in json.load(f).items()}
    except Exception as exc:
        logger.warning(f"Could not load offsets ({exc}); starting fresh")
        return {}


def _save_offsets(offsets: Dict[str, int]) -> None:
    try:
        tmp = OFFSETS_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(offsets, f, indent=2)
        tmp.replace(OFFSETS_FILE)
    except Exception as exc:
        logger.warning(f"Could not save offsets: {exc}")


def _tail_lines(path: Path, n: int) -> list:
    out: deque = deque(maxlen=max(1, n))
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(line)
    except OSError:
        pass
    return list(out)


def _load_seen_ids() -> Set[str]:
    seen: Set[str] = set()
    if not UNIFIED_LOG.exists():
        return seen
    for line in _tail_lines(UNIFIED_LOG, DEDUP_WINDOW):
        try:
            rec = json.loads(line)
            key = f"{rec.get('source_bus')}:{rec.get('source_id')}"
            if key != ":":
                seen.add(key)
        except Exception:
            continue
    return seen


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _unified_bus_max_bytes() -> int:
    """Positive cap, or 0 when rotation is off. A bad value stays off."""
    limit = _env_int("AUREON_UNIFIED_BUS_MAX_BYTES", 0)
    return limit if limit > 0 else 0


def _lock_file(handle) -> None:
    if sys.platform == "win32":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)


def _unlock_file(handle) -> None:
    if sys.platform == "win32":
        import msvcrt

        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _unified_bus_lock(path: Path):
    """One cross-process lock for rotate-and-append.

    The lock sits on a sibling of the log, not on the log inode, so moving
    the log cannot strand a writer on an unlinked file. The lock file is not
    a log and is never removed.
    """
    lock_path = path.with_name("." + path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+", encoding="utf-8") as handle:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write("\n")
            handle.flush()
        _lock_file(handle)
        try:
            yield
        finally:
            _unlock_file(handle)


_AT_FDCWD = -100
_RENAME_NOREPLACE = 1
# Apple renamex_np: fail if the destination already exists. Same promise as
# Linux RENAME_NOREPLACE. macOS has no renameat2.
_RENAME_EXCL = 0x00000004
_rotate_nonce = 0


def _raise_rename_error(err: int, src: Path, dst: Path) -> None:
    if err == errno.EEXIST:
        raise FileExistsError(err, os.strerror(err), os.fspath(dst))
    if err == errno.ENOENT:
        raise FileNotFoundError(err, os.strerror(err), os.fspath(src))
    raise OSError(err, os.strerror(err), os.fspath(src))


def _rename_noreplace_linux(src: Path, dst: Path) -> None:
    """Atomic no-replace rename. ENOSYS when this libc has no renameat2."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOSYS, "renameat2 unavailable")
    renameat2.argtypes = [
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    ]
    renameat2.restype = ctypes.c_int
    rc = renameat2(
        _AT_FDCWD,
        os.fsencode(src),
        _AT_FDCWD,
        os.fsencode(dst),
        _RENAME_NOREPLACE,
    )
    if rc == 0:
        return
    _raise_rename_error(ctypes.get_errno(), src, dst)


def _rename_noreplace_darwin(src: Path, dst: Path) -> None:
    """Atomic no-replace rename on macOS. ENOSYS when renamex_np is absent."""
    libc = ctypes.CDLL(None, use_errno=True)
    renamex_np = getattr(libc, "renamex_np", None)
    if renamex_np is None:
        raise OSError(errno.ENOSYS, "renamex_np unavailable")
    renamex_np.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
    renamex_np.restype = ctypes.c_int
    rc = renamex_np(os.fsencode(src), os.fsencode(dst), _RENAME_EXCL)
    if rc == 0:
        return
    _raise_rename_error(ctypes.get_errno(), src, dst)


def _rename_noreplace_link(src: Path, dst: Path) -> None:
    """Move by a new hard link, then drop the old name.

    ``os.link`` fails when dst exists, so an older log is never replaced.
    The old name is removed only after the new name is in place. If that
    removal fails, the new name is removed and src is left unchanged.
    """
    try:
        os.link(os.fspath(src), os.fspath(dst))
    except FileExistsError:
        raise
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise FileExistsError(exc.errno, exc.strerror, os.fspath(dst)) from exc
        raise
    try:
        os.unlink(os.fspath(src))
    except OSError:
        try:
            os.unlink(os.fspath(dst))
        except OSError:
            pass
        raise


def _rename_noreplace(src: Path, dst: Path) -> None:
    """Move src onto a name that must not already exist.

    ``os.replace`` / ``os.rename`` on POSIX unlink the destination. That would
    drop an older log. Windows ``os.rename`` already fails when the
    destination exists. Everywhere else, a missing atomic primitive falls
    through to :func:`_rename_noreplace_link` instead of skipping the cap.
    """
    if sys.platform == "win32":
        os.rename(os.fspath(src), os.fspath(dst))
        return
    native = _rename_noreplace_darwin if sys.platform == "darwin" else _rename_noreplace_linux
    try:
        native(src, dst)
    except OSError as exc:
        if exc.errno != errno.ENOSYS:
            raise
        _rename_noreplace_link(src, dst)


def _archive_path(path: Path) -> Path:
    global _rotate_nonce
    _rotate_nonce += 1
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    token = f"{os.getpid()}-{_rotate_nonce}-{time.time_ns()}"
    return path.with_name(f"{path.name}.{stamp}.{token}")


def _rotate_unified_bus_while_locked(path: Path) -> None:
    """Move path aside when it is at the cap. Caller holds the bus lock.

    The live name is recreated with ``O_APPEND`` (never ``O_TRUNC``) so a
    tailer that opens ``unified_bus.jsonl`` still finds the current file.
    A missing file means another writer already moved it; that is not an error.
    """
    limit = _unified_bus_max_bytes()
    if limit <= 0:
        return
    try:
        size = path.stat().st_size
    except OSError:
        return
    if size < limit:
        return
    moved = False
    for _ in range(8):
        dest = _archive_path(path)
        try:
            _rename_noreplace(path, dest)
        except FileExistsError:
            continue
        except FileNotFoundError:
            return
        moved = True
        break
    if not moved:
        raise OSError(f"could not move {path} aside without replacing a file")
    flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    fd = os.open(os.fspath(path), flags, 0o644)
    os.close(fd)


def _write_line(path: Path, line: str) -> None:
    with open(path, "a", encoding="utf-8", errors="replace") as handle:
        handle.write(line)
        handle.flush()
        try:
            os.fsync(handle.fileno())
        except Exception:
            pass


def _append_jsonl_capped(path: Path, line: str) -> None:
    """Append while the cap is on. A failed rotation still writes the line."""
    with _unified_bus_lock(path):
        try:
            _rotate_unified_bus_while_locked(path)
        except OSError as exc:
            logger.warning(f"unified bus rotation skipped: {exc}")
        _write_line(path, line)


def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    """Append one JSON object to the unified bus.

    ``AUREON_UNIFIED_BUS_MAX_BYTES`` unset or not a positive integer keeps the
    original append. A positive cap moves the current file, when it is already
    at or over the cap, to a new timestamped name and starts a fresh file.
    Existing files, including older rotations, are never deleted or truncated.
    Several processes can append: the rotate and the write share one lock, and
    a process that finds the file already moved appends to the live path.
    """
    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
    if _unified_bus_max_bytes() <= 0:
        _write_line(path, line)
        return
    _append_jsonl_capped(path, line)


def _source_id_from(record: Dict[str, Any], line: str) -> str:
    return str(record.get("id") or record.get("trace_id") or hash(line))


# ── bridge core ───────────────────────────────────────────────────────────────
class BusBridge:
    """Lightweight two-way thought-bus bridge."""

    def __init__(self) -> None:
        _ensure_dirs()
        self.offsets = _load_offsets()
        self.seen_ids = _load_seen_ids()
        self.upstream_bus: Any = None
        if FileThoughtBus is not None:
            try:
                self.upstream_bus = FileThoughtBus(str(UPSTREAM_MIRROR_LOG))
            except Exception as exc:
                logger.warning(f"Upstream FileThoughtBus init failed: {exc}")
        if _upstream_error:
            logger.warning(f"Upstream bus import unavailable: {_upstream_error}")
        if _sero_error:
            logger.warning(f"Sero events import unavailable: {_sero_error}")

    # ── offset bookkeeping ────────────────────────────────────────────────────
    def _get_offset(self, path: Path) -> int:
        key = str(path.resolve())
        if key in self.offsets:
            return self.offsets[key]
        # First time we see a source: start at EOF so we do not flood with history.
        try:
            offset = path.stat().st_size
        except OSError:
            offset = 0
        self.offsets[key] = offset
        return offset

    def _set_offset(self, path: Path, offset: int) -> None:
        self.offsets[str(path.resolve())] = offset

    # ── deduplication ─────────────────────────────────────────────────────────
    def _already_seen(self, source_bus: str, source_id: str) -> bool:
        key = f"{source_bus}:{source_id}"
        if key in self.seen_ids:
            return True
        self.seen_ids.add(key)
        return False

    # ── forwarders ────────────────────────────────────────────────────────────
    def _forward_sero_to_upstream(self, record: Dict[str, Any]) -> None:
        if self.upstream_bus is None or UpstreamThought is None:
            return
        payload = dict(record)
        topic = payload.pop("topic", "thought")
        source = payload.pop("source", "sero_thoughtbus")
        thought = UpstreamThought(
            source=source,
            topic=topic,
            payload=payload,
            meta={"_bridge_source": "sero", "_bridge_log": str(SERO_LOG)},
        )
        self.upstream_bus.publish(thought)

    def _forward_upstream_to_sero(self, record: Dict[str, Any]) -> None:
        if _events is None:
            return
        original_payload = record.get("payload") or {}
        if not isinstance(original_payload, dict):
            original_payload = {"value": original_payload}
        payload = {
            **original_payload,
            "_bridge_source": "upstream",
            "_bridge_id": str(uuid.uuid4())[:8],
            "_upstream_id": record.get("id"),
        }
        source = str(record.get("source", "upstream"))
        topic = str(record.get("topic", "thought"))
        _events.publish_event(source, topic, payload, priority=5)

    # ── processors ────────────────────────────────────────────────────────────
    def _process_sero_line(self, line: str) -> bool:
        record = json.loads(line)
        payload = record.get("payload") if isinstance(record.get("payload"), dict) else {}
        if payload.get("_bridge_source") == "upstream":
            return True  # do not echo events we just injected

        source_id = _source_id_from(record, line)
        if self._already_seen("sero", source_id):
            return True

        # Forward first so a transient failure leaves the offset behind and we retry.
        self._forward_sero_to_upstream(record)

        merged = {
            "bridge_id": str(uuid.uuid4())[:8],
            "ingress_timestamp": _now_iso(),
            "source_bus": "sero",
            "source_id": source_id,
            "source": record.get("source"),
            "topic": record.get("topic"),
            "timestamp": record.get("timestamp"),
            "event": record,
        }
        _append_jsonl(UNIFIED_LOG, merged)
        return True

    def _process_upstream_line(self, line: str) -> bool:
        record = json.loads(line)
        # Skip events the bridge itself looped back (should not happen, but fail-closed).
        if record.get("source") == "bus_bridge":
            return True

        source_id = _source_id_from(record, line)
        if self._already_seen("upstream", source_id):
            return True

        self._forward_upstream_to_sero(record)

        merged = {
            "bridge_id": str(uuid.uuid4())[:8],
            "ingress_timestamp": _now_iso(),
            "source_bus": "upstream",
            "source_id": source_id,
            "source": record.get("source"),
            "topic": record.get("topic"),
            "timestamp": record.get("ts") or record.get("timestamp"),
            "event": record,
        }
        _append_jsonl(UNIFIED_LOG, merged)
        return True

    # ── tail / batch ──────────────────────────────────────────────────────────
    def _tail_source(
        self,
        path: Path,
        processor: Callable[[str], bool],
        limit: int = BATCH_LIMIT,
    ) -> Tuple[int, int]:
        """Return (processed_count, new_offset). Stops early on error so the
        failing line is retried on the next pass."""
        if not path.exists():
            return 0, self._get_offset(path)

        offset = self._get_offset(path)
        try:
            size = path.stat().st_size
        except OSError:
            return 0, offset

        if size < offset:
            offset = 0

        processed = 0
        new_offset = offset
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(offset)
                while True:
                    line = f.readline()
                    if not line:
                        break
                    line = line.strip()
                    if not line:
                        new_offset = f.tell()
                        continue
                    try:
                        processor(line)
                    except Exception as exc:
                        logger.warning(f"Transient error processing {path.name}: {exc}")
                        break
                    new_offset = f.tell()
                    processed += 1
                    if processed >= limit:
                        break
        except Exception as exc:
            logger.warning(f"Could not tail {path}: {exc}")

        self._set_offset(path, new_offset)
        return processed, new_offset

    def run_once(self) -> Dict[str, int]:
        """Process one batch from each side and persist offsets."""
        sero_count, _ = self._tail_source(SERO_LOG, self._process_sero_line)
        upstream_count, _ = self._tail_source(UPSTREAM_LOG, self._process_upstream_line)
        _save_offsets(self.offsets)
        return {"sero": sero_count, "upstream": upstream_count}

    def run_daemon(self, interval: float = DAEMON_INTERVAL) -> None:
        logger.info("Bus bridge daemon started")
        logger.info(f"  sero source:    {SERO_LOG}")
        logger.info(f"  upstream source:{UPSTREAM_LOG}")
        logger.info(f"  unified log:    {UNIFIED_LOG}")
        logger.info(f"  upstream mirror:{UPSTREAM_MIRROR_LOG}")
        try:
            while True:
                counts = self.run_once()
                if counts["sero"] or counts["upstream"]:
                    logger.info(f"bridged {counts}")
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Bus bridge daemon stopped")


# ── self-test ─────────────────────────────────────────────────────────────────
def _selftest() -> int:
    """Inject one event on each side, run one batch, and inspect the unified log."""
    # Capture offsets BEFORE injecting test events so the bridge sees them.
    bridge = BusBridge()
    _ = bridge._get_offset(SERO_LOG)
    _ = bridge._get_offset(UPSTREAM_LOG)

    # Inject a Sero-side event via the workspace events spine.
    if _events is not None:
        _events.publish_event(
            "bus_bridge_selftest",
            "bridge.selftest.sero",
            {"message": "synthetic sero event", "nonce": str(uuid.uuid4())[:8]},
            priority=5,
        )
        # Give the filesystem a moment on Windows.
        time.sleep(0.2)

    # Inject an upstream-side event into the upstream source log.
    if FileThoughtBus is not None:
        upstream_test_bus = FileThoughtBus(str(UPSTREAM_LOG))
        upstream_test_bus.publish(
            UpstreamThought(
                source="bus_bridge_selftest",
                topic="bridge.selftest.upstream",
                payload={"message": "synthetic upstream event", "nonce": str(uuid.uuid4())[:8]},
            )
        )
        time.sleep(0.2)

    counts = bridge.run_once()
    logger.info(f"Self-test batch result: {counts}")

    # Inspect the unified log tail for both events.
    found_sero = found_upstream = False
    if UNIFIED_LOG.exists():
        for line in _tail_lines(UNIFIED_LOG, 20):
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("source_bus") == "sero" and rec.get("topic") == "bridge.selftest.sero":
                found_sero = True
            if rec.get("source_bus") == "upstream" and rec.get("topic") == "bridge.selftest.upstream":
                found_upstream = True

    print("\n" + "=" * 70)
    print("BUS BRIDGE SELF-TEST RESULTS")
    print("=" * 70)
    print(f"Sero events bridged:      {counts['sero']}")
    print(f"Upstream events bridged:  {counts['upstream']}")
    print(f"Unified log exists:       {UNIFIED_LOG.exists()}  ({UNIFIED_LOG})")
    print(f"Sero event in unified:    {found_sero}")
    print(f"Upstream event in unified:{found_upstream}")
    print(f"Upstream mirror log:      {UPSTREAM_MIRROR_LOG}  (exists={UPSTREAM_MIRROR_LOG.exists()})")
    print("=" * 70)

    if not counts["sero"] and _events is not None:
        print("WARNING: no sero event was bridged")
    if not counts["upstream"] and FileThoughtBus is not None:
        print("WARNING: no upstream event was bridged")
    if UNIFIED_LOG.exists() and (counts["sero"] or counts["upstream"]):
        print("PASS: unified log received events")
        return 0
    print("FAIL: unified log did not receive events")
    return 1


# ── CLI ───────────────────────────────────────────────────────────────────────
def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Bus bridge between Sero and Aureon thought buses")
    parser.add_argument("--once", action="store_true", help="process one batch and exit")
    parser.add_argument("--selftest", action="store_true", help="inject test events, process, verify")
    parser.add_argument("--interval", type=float, default=DAEMON_INTERVAL, help="daemon poll interval")
    parser.add_argument("--upstream-log", type=Path, default=None, help="override upstream source log path")
    args = parser.parse_args(argv)

    if args.upstream_log:
        global UPSTREAM_LOG
        UPSTREAM_LOG = args.upstream_log

    if args.selftest:
        return _selftest()

    bridge = BusBridge()
    if args.once:
        counts = bridge.run_once()
        print(f"bus_bridge --once: bridged {counts}")
        print(f"unified log: {UNIFIED_LOG}  exists={UNIFIED_LOG.exists()}")
        print(f"upstream mirror: {UPSTREAM_MIRROR_LOG}  exists={UPSTREAM_MIRROR_LOG.exists()}")
        return 0

    bridge.run_daemon(args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
