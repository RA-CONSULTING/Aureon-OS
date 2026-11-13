"""Cross-process tail of the ThoughtBus ``thoughts.jsonl`` file.

The command center gets in-process thoughts from its ThoughtBus subscription.
Thoughts written by other processes only reach it through the shared JSONL
file, so this module follows that file.

* The file stays open between reads. When the path is replaced (for example
  by the opt-in rotation from #355, which renames ``thoughts.jsonl`` to
  ``thoughts.jsonl.1``), the open handle still points at the old file, so the
  lines written there since the last read come through first. Only once the
  old file is drained does the tail switch to the new file, from offset 0.
* If the same file gets shorter than the read position (truncated in place),
  reading starts again from 0. Known gap: a truncate followed by growth past
  the old position between two reads looks like normal growth, so those lines
  are missed. Rotation renames the file, so it does not hit this.
* Each call reads at most ``max_read_bytes``. That is an I/O buffer size, not
  a data threshold: the rest stays in the file for the next call, so a large
  backlog never blocks the event loop in one read or floods clients at once.
* Only complete lines are consumed; a half-written last line is read again
  once its newline lands.

Duplicates: a thought published in this process reaches the listener twice,
once from the subscription and once from the file. ``SeenIds`` is the single
check both paths use, and both run on one event loop, so whichever copy
arrives first is handled and the other is skipped. This holds even when the
file copy is read first (``ThoughtBus.publish`` persists before handlers run).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Any

# I/O buffer per read call, in bytes. Unread data stays in the file.
DEFAULT_MAX_READ_BYTES = 1024 * 1024


class SeenIds:
    """Bounded record of thought ids already handled.

    ``limit`` only has to cover the gap between the two copies of one thought.
    Its file copy is read within one or two tail reads of its subscription
    copy, so the limit is derived from the read buffer: enough ids for two
    full reads of lines as short as ``min_line_bytes``.
    """

    def __init__(self, max_read_bytes: int = DEFAULT_MAX_READ_BYTES, min_line_bytes: int = 100) -> None:
        self.limit = max(1, 2 * max_read_bytes // max(1, min_line_bytes))
        self._ids: OrderedDict[str, None] = OrderedDict()

    def first_time(self, thought_id: object) -> bool:
        """Return True and record the id if it is new.

        A thought without an id cannot be matched, so it always counts as new.
        """
        if not thought_id:
            return True
        key = str(thought_id)
        if key in self._ids:
            return False
        self._ids[key] = None
        while len(self._ids) > self.limit:
            self._ids.popitem(last=False)
        return True


async def next_local(queue: asyncio.Queue, timeout: float = 1.0) -> Any | None:
    """Wait up to ``timeout`` seconds for an in-process thought.

    Returns None on timeout so the caller still polls the file tail while this
    process is quiet.
    """
    try:
        return await asyncio.wait_for(queue.get(), timeout=timeout)
    except asyncio.TimeoutError:
        return None


@dataclass
class ThoughtTail:
    path: Path
    max_read_bytes: int = DEFAULT_MAX_READ_BYTES
    _fh: IO[bytes] | None = field(default=None, repr=False)
    _inode: tuple[int, int] | None = field(default=None, repr=False)

    @classmethod
    def at_end(cls, path: Path, max_read_bytes: int = DEFAULT_MAX_READ_BYTES) -> ThoughtTail:
        """Start at the current end of ``path``; history is not replayed."""
        tail = cls(Path(path), max_read_bytes=max_read_bytes)
        if tail._open() and tail._fh is not None:
            tail._fh.seek(0, os.SEEK_END)
        return tail

    def _open(self) -> bool:
        try:
            fh = open(self.path, "rb")  # noqa: SIM115 - held open across reads on purpose
        except OSError:
            return False
        st = os.fstat(fh.fileno())
        self._fh = fh
        self._inode = (st.st_dev, st.st_ino)
        return True

    def close(self) -> None:
        if self._fh is not None:
            with contextlib.suppress(OSError):
                self._fh.close()
        self._fh = None
        self._inode = None

    def _path_inode(self) -> tuple[int, int] | None:
        try:
            st = os.stat(self.path)
        except OSError:
            return None
        return (st.st_dev, st.st_ino)

    def _read_chunk(self) -> bytes:
        """Read up to one buffer, keeping only complete lines."""
        fh = self._fh
        if fh is None:
            return b""
        start = fh.tell()
        try:
            size = os.fstat(fh.fileno()).st_size
        except OSError:
            size = start
        if size < start:
            fh.seek(0)
            start = 0
        data = fh.read(self.max_read_bytes)
        cut = data.rfind(b"\n")
        if cut < 0:
            fh.seek(start)
            return b""
        fh.seek(start + cut + 1)
        return data[: cut + 1]

    def read_raw(self) -> bytes:
        """Return complete new lines as bytes, at most one buffer's worth."""
        if self._fh is None and not self._open():
            return b""
        chunk = self._read_chunk()
        if chunk:
            return chunk
        # Current file drained. If the path now names another file, switch.
        current = self._path_inode()
        if current is not None and current != self._inode:
            self.close()
            if self._open():
                return self._read_chunk()
        return b""

    def read_new(self) -> list[dict]:
        out: list[dict] = []
        for raw in self.read_raw().splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(data, dict):
                out.append(data)
        return out
