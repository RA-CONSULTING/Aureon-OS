"""
Cross-process bus trace — one signal, one dedicated file, re-read live.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The organism runs as several separate OS processes (``aureon_operator``,
``aureon_organism``, ``hnc_live_daemon`` under supervisord), each with its own
in-memory :class:`ThoughtBus`. A thought published in one process is invisible to
the others: ``recall`` reads only that process's memory, and ``subscribe``
handlers only fire for in-process publishes.

The proven, flood-proof way to cross that boundary is a **dedicated per-signal
trace file**: the producing process appends the signal to ``state/<name>.jsonl``,
and the consuming process re-reads that file live. Because the file carries ONLY
that one signal, a high-volume topic elsewhere (e.g. baton heartbeats) can never
bury it — the property the HNC field bridge (``hnc_field._read_field_from_trace``)
relies on. This module generalizes that pattern so every cross-process signal
uses one guarded, tail-bounded, multi-writer-safe helper instead of a bespoke copy.

Everything here is guarded and never raises: a missing or corrupt trace degrades
to "no data" (``[]`` / ``None``), never a crash and never a fabricated value.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Protocol, cast

logger = logging.getLogger("aureon.core.bus_trace")

_REPO_ROOT = Path(__file__).resolve().parents[2]
# Bounded tail read: only the last chunk of the file is ever scanned, so read
# cost is O(chunk) regardless of how large the trace has grown.
_TAIL_BYTES = 256 * 1024


class _PosixFcntl(Protocol):
    """The small POSIX locking surface used during best-effort compaction."""

    LOCK_EX: int
    LOCK_UN: int

    def flock(self, fd: int, operation: int) -> None: ...


def trace_dir() -> Path:
    """Directory holding the per-signal traces (override with ``AUREON_BUS_TRACE_DIR``)."""
    return Path(os.environ.get("AUREON_BUS_TRACE_DIR") or (_REPO_ROOT / "state"))


def trace_path(name: str) -> Path:
    """Absolute path of the dedicated trace file for signal ``name``."""
    return trace_dir() / f"{name}.jsonl"


def append_trace(name: str, payload: dict[str, Any], *, cap: int = 1000) -> None:
    """Append one JSON row to signal ``name``'s trace so another process can read it.

    Uses ``O_APPEND`` (atomic per line → safe when several processes write the same
    signal). When the file grows past ``2 * cap`` lines, it is best-effort compacted
    to the last ``cap`` lines under an ``flock`` so it never grows without bound.
    Never raises — a trace we could not write is a lost telemetry row, not a crash.
    """
    try:
        path = trace_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(payload, default=str)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        _maybe_compact(path, cap)
    except Exception as exc:  # noqa: BLE001 — telemetry, never fatal
        logger.debug("append_trace(%s) skipped: %s", name, exc)


def _maybe_compact(path: Path, cap: int) -> None:
    """Keep the trace bounded: when it exceeds 2×cap lines, rewrite the last cap.
    Guarded by an exclusive advisory lock so concurrent writers don't clobber."""
    try:
        # Cheap gate: only pay the read+rewrite cost occasionally.
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
        if len(lines) <= 2 * cap:
            return
        tail = lines[-cap:]
        try:
            import fcntl as native_fcntl

            # fcntl is intentionally imported only on POSIX.  Typeshed's Windows
            # fallback exposes the module without its POSIX attributes, so bind
            # the exact API used here at the platform boundary.
            fcntl = cast(_PosixFcntl, native_fcntl)

            with path.open("r+", encoding="utf-8") as fh:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
                try:
                    fh.seek(0)
                    fh.truncate()
                    fh.writelines(tail)
                finally:
                    fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except ImportError:  # pragma: no cover — non-POSIX fallback
            with path.open("w", encoding="utf-8") as fh:
                fh.writelines(tail)
    except Exception as exc:  # noqa: BLE001
        logger.debug("compact(%s) skipped: %s", path.name, exc)


def read_trace(name: str, limit: int = 200) -> list[dict[str, Any]]:
    """Read the last ``limit`` rows of signal ``name``'s trace, freshly from disk.

    Only the tail of the file is scanned (bounded bytes), and partial/corrupt lines
    are skipped. Returns ``[]`` when the trace is absent or empty. Never raises.
    """
    out: list[dict[str, Any]] = []
    try:
        path = trace_path(name)
        if not path.exists():
            return out
        size = path.stat().st_size
        with path.open("rb") as fh:
            if size > _TAIL_BYTES:
                fh.seek(size - _TAIL_BYTES)
                fh.readline()  # discard the (likely partial) first line
            raw = fh.read().decode("utf-8", errors="replace")
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except (ValueError, TypeError):
                continue  # partial/corrupt line — skip, never fail
            if isinstance(row, dict):
                out.append(row)
        return out[-limit:]
    except Exception as exc:  # noqa: BLE001
        logger.debug("read_trace(%s) failed: %s", name, exc)
        return out


def read_trace_latest(name: str) -> dict[str, Any] | None:
    """The most recent valid row of signal ``name``'s trace, or ``None``."""
    rows = read_trace(name, limit=1)
    return rows[-1] if rows else None


__all__ = ["trace_dir", "trace_path", "append_trace", "read_trace", "read_trace_latest"]
