"""Cross-process tail of a ThoughtBus JSONL log.

Reads lines appended since the last call, by byte offset, without calling
``tell()`` while iterating a text file (which Python refuses).  Starts again
from the top when the file is replaced (inode change, e.g. after rotation)
or shrinks.  A partial last line is left for the next call.
"""
from __future__ import annotations

import json
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ThoughtTail:
    path: Path
    pos: int = 0
    inode: Optional[int] = None
    _seen: "OrderedDict[str, None]" = field(default_factory=OrderedDict)
    seen_limit: int = 10000
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @classmethod
    def at_end(cls, path: Path) -> "ThoughtTail":
        tail = cls(Path(path))
        try:
            st = os.stat(tail.path)
        except OSError:
            return tail
        tail.pos, tail.inode = st.st_size, st.st_ino
        return tail

    def mark_seen(self, thought_id: Any) -> None:
        """Record a thought this process receives directly so the tail skips it.

        Safe to call from the bus's publishing thread.
        """
        if not thought_id:
            return
        key = str(thought_id)
        with self._lock:
            self._seen[key] = None
            self._seen.move_to_end(key)
            while len(self._seen) > self.seen_limit:
                self._seen.popitem(last=False)

    def _is_seen(self, thought_id: Any) -> bool:
        if not thought_id:
            return False
        with self._lock:
            return str(thought_id) in self._seen

    def read_new(self) -> List[Dict[str, Any]]:
        try:
            st = os.stat(self.path)
        except OSError:
            return []
        if self.inode is not None and st.st_ino != self.inode:
            self.pos = 0
        elif st.st_size < self.pos:
            self.pos = 0
        self.inode = st.st_ino
        if st.st_size == self.pos:
            return []
        with open(self.path, "rb") as f:
            f.seek(self.pos)
            chunk = f.read()
        end = chunk.rfind(b"\n")
        if end < 0:
            return []
        self.pos += end + 1
        out: List[Dict[str, Any]] = []
        for raw in chunk[: end + 1].splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                data = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            if self._is_seen(data.get("id")):
                continue
            out.append(data)
        return out
