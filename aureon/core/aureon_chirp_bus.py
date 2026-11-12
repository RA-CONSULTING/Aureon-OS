#!/usr/bin/env python3
"""
Aureon Chirp Bus
----------------
Ultra-compact kHz-rate signaling between running components using
8-byte chirp packets and shared-memory ring buffer transport.

Startup: the creator zeroes the header and writes the layout version
word last, so a nonzero version means the segment is ready. Attachers
that see a size of 0 or a version of 0 treat the segment as "not ready
yet" and re-read for up to CHIRP_ATTACH_READY_TIMEOUT_S before refusing.
A wrong nonzero size or version is refused at once.

Restart runbook: stop the old run before starting a run on this code.
While an older run still maps its old-size aureon_chirp_bus segment,
the new launcher's unlink_chirp_bus refuses (the segment is still
mapped) and every new child refuses the segment on size. That failure
is loud (error log, publish/emit return False, undelivered counts up),
but no chirps flow until the old run is stopped and the new run is
started.
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import logging
import os
import struct
import sys
import time
import zlib
from dataclasses import dataclass, field
from enum import IntEnum
from multiprocessing import shared_memory

# Windows UTF-8 Fix
if sys.platform == 'win32' and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        # Avoid replacing sys.stdout with a new TextIOWrapper around stdout.buffer:
        # that pattern can close stdout in some Windows shells.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CHIRP_MAGIC = 0xC1
CHIRP_SIZE = 8
HEADER_SIZE = 16  # write_idx (8) + read_idx (8)
CHIRP_RING_VERSION = 1
VERSION_SIZE = 4  # uint32 layout version stored after the ring payload
# Longest time an attacher waits for a creator to finish a fresh segment
# (size still 0 or version word still 0) before refusing it.
CHIRP_ATTACH_READY_TIMEOUT_S = 2.0
CHIRP_ATTACH_READY_POLL_S = 0.005

CHIRP_STRUCT = struct.Struct(">BBBBHBB")
logger = logging.getLogger(__name__)


def ring_segment_size(slots: int = 512) -> int:
    return HEADER_SIZE + (slots * CHIRP_SIZE) + VERSION_SIZE


class ChirpType(IntEnum):
    PING = 0
    OPPORTUNITY = 1
    EXECUTE = 2
    OUTCOME = 3
    ALERT = 4
    STATUS = 5


class ChirpDirection(IntEnum):
    DOWN = 0
    UP = 1


@dataclass
class ChirpPacket:
    message_type: ChirpType
    direction: ChirpDirection
    coherence: float = 1.0
    confidence: float = 1.0
    symbol_id: int = 0
    frequency: int = 528
    amplitude: int = 128
    timestamp_bucket: int = 0

    def to_bytes(self) -> bytes:
        type_dir = ((int(self.message_type) & 0x0F) << 4) | (int(self.direction) & 0x0F)
        coh = max(0, min(15, int(round(self.coherence * 15))))
        conf = max(0, min(15, int(round(self.confidence * 15))))
        coh_conf = (coh << 4) | conf
        freq = max(0, min(0xFFFF, int(self.frequency)))
        amp = max(0, min(0xFF, int(self.amplitude)))
        tsb = max(0, min(0xFF, int(self.timestamp_bucket)))
        return CHIRP_STRUCT.pack(CHIRP_MAGIC, type_dir, coh_conf, self.symbol_id & 0xFF, freq, amp, tsb)

    @classmethod
    def from_bytes(cls, data: bytes) -> ChirpPacket:
        if len(data) != CHIRP_SIZE:
            raise ValueError("Invalid chirp size")
        magic, type_dir, coh_conf, symbol_id, freq, amp, tsb = CHIRP_STRUCT.unpack(data)
        if magic != CHIRP_MAGIC:
            raise ValueError("Invalid chirp magic")
        message_type = ChirpType((type_dir >> 4) & 0x0F)
        direction = ChirpDirection(type_dir & 0x0F)
        coherence = ((coh_conf >> 4) & 0x0F) / 15.0
        confidence = (coh_conf & 0x0F) / 15.0
        return cls(
            message_type=message_type,
            direction=direction,
            coherence=coherence,
            confidence=confidence,
            symbol_id=symbol_id,
            frequency=freq,
            amplitude=amp,
            timestamp_bucket=tsb,
        )



def _open_shared_memory(
    name: str,
    *,
    create: bool,
    size: int = 0,
    track: bool,
) -> shared_memory.SharedMemory:
    """Open a segment. Always leave the resource tracker unregistered when track is False."""
    try:
        return shared_memory.SharedMemory(name=name, create=create, size=size, track=track)
    except TypeError:
        # Python < 3.13 has no track=; unregister non-owners ourselves.
        shm = shared_memory.SharedMemory(name=name, create=create, size=size)
        if not track:
            try:
                from multiprocessing import resource_tracker
                resource_tracker.unregister(shm._name, "shared_memory")
            except Exception:
                pass
        return shm


@dataclass
class ChirpRingBuffer:
    name: str
    slots: int = 512
    create: bool = False
    shm: shared_memory.SharedMemory | None = field(init=False, default=None)
    buf: memoryview | None = field(init=False, default=None)
    _initialized: bool = field(init=False, default=False)
    _owner: bool = field(init=False, default=False)
    _refused: bool = field(init=False, default=False)
    _refuse_reason: str | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        size = ring_segment_size(self.slots)
        self._owner = False
        self._refused = False
        self._refuse_reason = None
        try:
            self.shm = _open_shared_memory(self.name, create=False, track=False)
        except FileNotFoundError:
            if not self.create:
                self._initialized = False
                return
            try:
                self.shm = _open_shared_memory(self.name, create=True, size=size, track=False)
                self._owner = True
            except FileExistsError:
                # Lost the create race; attach to the winner's segment.
                if not self._attach_when_ready():
                    return
            except Exception:
                logger.exception("chirp bus %r: could not create the segment", self.name)
                self._initialized = False
                return
        except ValueError:
            # A creator has opened the name but not sized it yet.
            if not self._attach_when_ready():
                return
        except Exception:
            logger.exception("chirp bus %r: could not open the segment", self.name)
            self._initialized = False
            return

        version_offset = HEADER_SIZE + (self.slots * CHIRP_SIZE)
        if self._owner:
            if self.shm.size != size:
                self._refuse(
                    f"wrong-size leftover segment {self.name!r}: "
                    f"size {self.shm.size} != {size}"
                )
                return
            self.buf = self.shm.buf
            # Header first, version word last: a nonzero version means ready.
            self.buf[:HEADER_SIZE] = b"\x00" * HEADER_SIZE
            struct.pack_into(">I", self.buf, version_offset, CHIRP_RING_VERSION)
        else:
            if not self._wait_until_ready(size, version_offset):
                return
        self._initialized = True

    def _attach_when_ready(self) -> bool:
        """Re-open a segment another process is still creating. Bounded wait."""
        deadline = time.monotonic() + CHIRP_ATTACH_READY_TIMEOUT_S
        while True:
            try:
                self.shm = _open_shared_memory(self.name, create=False, track=False)
                return True
            except FileNotFoundError:
                self._initialized = False
                return False
            except ValueError:
                # Still empty (not sized yet); keep waiting.
                if time.monotonic() >= deadline:
                    self._refuse(
                        f"wrong-size leftover segment {self.name!r}: "
                        f"still empty after {CHIRP_ATTACH_READY_TIMEOUT_S}s"
                    )
                    return False
                time.sleep(CHIRP_ATTACH_READY_POLL_S)
            except Exception:
                logger.exception("chirp bus %r: could not attach to the segment", self.name)
                self._initialized = False
                return False

    def _wait_until_ready(self, size: int, version_offset: int) -> bool:
        """Attach path: wait (bounded) while size or version is still 0.

        A wrong nonzero size or version is refused at once. Size 0 or
        version 0 means the creator has not finished; re-read for up to
        CHIRP_ATTACH_READY_TIMEOUT_S, then refuse.
        """
        deadline = time.monotonic() + CHIRP_ATTACH_READY_TIMEOUT_S
        while True:
            assert self.shm is not None
            actual = self.shm.size
            if actual == 0:
                if time.monotonic() >= deadline:
                    self._refuse(
                        f"wrong-size leftover segment {self.name!r}: "
                        f"size 0 != {size} after {CHIRP_ATTACH_READY_TIMEOUT_S}s"
                    )
                    return False
                # Re-open to pick up the creator's ftruncate.
                try:
                    self.shm.close()
                except Exception:
                    pass
                self.shm = None
                time.sleep(CHIRP_ATTACH_READY_POLL_S)
                if not self._attach_when_ready():
                    return False
                continue
            if actual != size:
                self._refuse(
                    f"wrong-size leftover segment {self.name!r}: "
                    f"size {actual} != {size}"
                )
                return False
            version = struct.unpack_from(">I", self.shm.buf, version_offset)[0]
            if version == CHIRP_RING_VERSION:
                self.buf = self.shm.buf
                return True
            if version != 0:
                self._refuse(
                    f"wrong-version leftover segment {self.name!r}: "
                    f"version {version} != {CHIRP_RING_VERSION}"
                )
                return False
            if time.monotonic() >= deadline:
                self._refuse(
                    f"wrong-version leftover segment {self.name!r}: "
                    f"version 0 != {CHIRP_RING_VERSION} after "
                    f"{CHIRP_ATTACH_READY_TIMEOUT_S}s"
                )
                return False
            time.sleep(CHIRP_ATTACH_READY_POLL_S)

    def _refuse(self, reason: str) -> None:
        # Leave a leftover segment in place; do not create another name.
        logger.error(reason)
        try:
            if self.shm:
                self.shm.close()
        except Exception:
            pass
        self.shm = None
        self.buf = None
        self._owner = False
        self._initialized = False
        self._refused = True
        self._refuse_reason = reason

    def close(self) -> None:
        """Close the mapping. Never unlinks the segment."""
        if self.shm:
            try:
                self.shm.close()
            except Exception:
                pass
            self.shm = None
            self.buf = None
            self._initialized = False

    def __del__(self) -> None:
        """Cleanup on deletion - only if initialized."""
        if getattr(self, '_initialized', False):
            self.close()

    def _read_idx(self) -> int:
        return struct.unpack("Q", self.buf[8:16])[0]

    def _write_idx(self) -> int:
        return struct.unpack("Q", self.buf[0:8])[0]

    def _set_write_idx(self, value: int) -> None:
        struct.pack_into("Q", self.buf, 0, value)

    def _set_read_idx(self, value: int) -> None:
        struct.pack_into("Q", self.buf, 8, value)

    def write(self, chirp_bytes: bytes) -> bool:
        if not self._initialized or self.buf is None:
            return False
        if len(chirp_bytes) != CHIRP_SIZE:
            return False
        write_idx = self._write_idx()
        read_idx = self._read_idx()
        next_write = (write_idx + CHIRP_SIZE) % (self.slots * CHIRP_SIZE)
        if next_write == read_idx:
            return False
        offset = HEADER_SIZE + write_idx
        self.buf[offset:offset + CHIRP_SIZE] = chirp_bytes
        self._set_write_idx(next_write)
        return True

    def read(self) -> bytes | None:
        if not self._initialized or self.buf is None:
            return None
        write_idx = self._write_idx()
        read_idx = self._read_idx()
        if read_idx == write_idx:
            return None
        offset = HEADER_SIZE + read_idx
        chirp_bytes = bytes(self.buf[offset:offset + CHIRP_SIZE])
        next_read = (read_idx + CHIRP_SIZE) % (self.slots * CHIRP_SIZE)
        self._set_read_idx(next_read)
        return chirp_bytes


try:
    from aureon.harmonic.aureon_harmonic_symbol_table import get_symbol_id
    _SYMBOL_TABLE_AVAILABLE = True
except Exception:
    _SYMBOL_TABLE_AVAILABLE = False
    def get_symbol_id(symbol: str) -> int:
        if not symbol:
            return 0
        return zlib.crc32(symbol.encode("utf-8")) & 0xFF


@dataclass
class ChirpBus:
    name: str = "aureon_chirp_bus"
    create: bool = False
    ring: ChirpRingBuffer = field(init=False)
    _undelivered: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.ring = ChirpRingBuffer(name=self.name, create=self.create)
        self._undelivered = 0

    @property
    def refused(self) -> bool:
        return bool(getattr(self.ring, "_refused", False))

    @property
    def undelivered(self) -> int:
        return self._undelivered

    def _mark_undelivered(self) -> bool:
        self._undelivered += 1
        return False

    def emit(self, packet: ChirpPacket) -> bool:
        if not getattr(self.ring, "_initialized", False):
            return self._mark_undelivered()
        ok = self.ring.write(packet.to_bytes())
        return ok if ok else self._mark_undelivered()

    def publish(self, message: str | ChirpPacket = "", **kwargs) -> bool:
        """Publish a chirp. False means the message was not delivered."""
        if isinstance(message, ChirpPacket):
            return self.emit(message)
        return self.emit_message(message, **kwargs)

    def emit_message(
        self,
        message: str,
        *,
        direction: ChirpDirection = ChirpDirection.DOWN,
        coherence: float = 1.0,
        confidence: float = 1.0,
        symbol: str | None = None,
        frequency: int = 528,
        amplitude: int = 128,
        message_type: ChirpType | None = None,
    ) -> bool:
        packet = ChirpPacket(
            message_type=message_type or classify_message(message),
            direction=direction,
            coherence=coherence,
            confidence=confidence,
            symbol_id=get_symbol_id(symbol) if symbol else 0,
            frequency=frequency,
            amplitude=amplitude,
            timestamp_bucket=_timestamp_bucket(),
        )
        return self.emit(packet)

    def emit_signal(
        self,
        *,
        message: str,
        direction: ChirpDirection,
        coherence: float,
        confidence: float,
        symbol: str | None,
        frequency: int,
        amplitude: int = 128,
    ) -> bool:
        return self.emit_message(
            message,
            direction=direction,
            coherence=coherence,
            confidence=confidence,
            symbol=symbol,
            frequency=frequency,
            amplitude=amplitude,
        )


_chirp_bus: ChirpBus | None = None


def get_chirp_bus(create_if_missing: bool = True) -> ChirpBus | None:
    global _chirp_bus
    if _chirp_bus is not None:
        return _chirp_bus
    try:
        _chirp_bus = ChirpBus(create=create_if_missing)
        return _chirp_bus
    except Exception:
        return None


def _mapping_pids(name: str) -> list[int]:
    """Return pids whose /proc/<pid>/maps mention /dev/shm/<name>.

    /proc entries this process cannot read are skipped. That includes
    processes run by another user (and ones that exit mid-scan), so a
    mapper run by another user cannot be seen here and will not stop
    unlink_chirp_bus. The current process is included if it maps the name.
    """
    target = f"/dev/shm/{name}"
    pids: list[int] = []
    try:
        entries = os.listdir("/proc")
    except OSError:
        return pids
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/maps", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if target in line:
                        pids.append(int(entry))
                        break
        except (FileNotFoundError, PermissionError, OSError):
            continue
    return pids


def unlink_chirp_bus(name: str = "aureon_chirp_bus") -> bool:
    """Unlink a chirp bus segment. This is the only unlink path.

    Returns False and logs a warning if any live process still maps
    /dev/shm/<name>, including this process. A missing segment is
    treated as already gone (returns True).
    """
    if not name or "/" in name or name in {".", ".."}:
        logger.warning("unlink_chirp_bus refused an invalid name")
        return False
    if not os.path.isdir("/proc"):
        logger.warning("unlink_chirp_bus refused %r: cannot scan process mappings", name)
        return False
    mapped = _mapping_pids(name)
    if mapped:
        logger.warning(
            "unlink_chirp_bus refused %r: still mapped by pids %s",
            name,
            mapped,
        )
        return False
    try:
        shm = _open_shared_memory(name, create=False, track=False)
    except FileNotFoundError:
        return True
    except Exception:
        logger.warning("unlink_chirp_bus could not attach to %r", name)
        return False
    try:
        shm.close()
        shm.unlink()
        return True
    except FileNotFoundError:
        return True
    except Exception:
        logger.warning("unlink_chirp_bus failed to unlink %r", name)
        return False


def _timestamp_bucket() -> int:
    return int((time.time_ns() // 1_000_000) % 256)


def classify_message(message: str) -> ChirpType:
    text = (message or "").upper()
    if "EXECUTE" in text or "FIRE" in text:
        return ChirpType.EXECUTE
    if "BUY" in text or "ENTRY" in text:
        return ChirpType.OPPORTUNITY
    if "SELL" in text or "EXIT" in text:
        return ChirpType.ALERT
    if "WIN" in text or "PROFIT" in text:
        return ChirpType.OUTCOME
    if "STATUS" in text or "HEALTH" in text:
        return ChirpType.STATUS
    return ChirpType.PING
