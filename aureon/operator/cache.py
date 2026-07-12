"""
Aureon Operator — response cache.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A small, thread-safe, TTL + LRU in-memory cache keyed by the *full* determinants
of an answer: the prompt, the grounding signature, and the exact set of models on
the board. Change any of those and it's a different question → a cache miss.

This is deliberately in-process (no Redis dependency): the switchboard is thin
glue and the cache is a latency/cost optimisation, not a source of truth.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import OrderedDict
from typing import Any


def cache_key(prompt: str, grounding_signature: str, model_set: str) -> str:
    raw = f"{prompt}\x1f{grounding_signature}\x1f{model_set}".encode("utf-8", "replace")
    return hashlib.sha256(raw).hexdigest()


class ResponseCache:
    """TTL + LRU cache. Values are opaque (the operator stores OperatorResponse dicts)."""

    def __init__(self, ttl_s: float = 900.0, max_entries: int = 512):
        self.ttl_s = float(ttl_s)
        self.max_entries = int(max_entries)
        self._store: OrderedDict[str, tuple] = OrderedDict()  # key -> (expires_at, value)
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < now:
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)  # LRU touch
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.time() + self.ttl_s, value)
            self._store.move_to_end(key)
            while len(self._store) > self.max_entries:
                self._store.popitem(last=False)  # evict oldest

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)


__all__ = ["ResponseCache", "cache_key"]
