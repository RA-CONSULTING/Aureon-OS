"""
TracePump — re-fire cross-process signals whose consumers use ``subscribe``.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

``bus_trace`` lets any process READ a cross-process signal via ``recall`` +
file-fallback. But some consumers don't poll — they register a live
``bus.subscribe(topic, handler)`` and expect the handler to fire when the event
happens (e.g. cognition senses ``auris.throne.cosmic_state`` and
``lighthouse.event``). Tailing a file never fires those handlers, so those
signals stayed dead across the process boundary even after the trace existed.

The pump closes that gap without touching a single consumer: it runs in the
CONSUMING process, tails each signal's dedicated trace, and **re-publishes new
rows onto the local bus** as the original topic — so every existing subscriber
fires exactly as if the producer had published in-process. Dedup is by a
producer-stamped ``_ts`` (monotonic), and the backlog present at start is NOT
replayed (only optionally the single latest row for *state*-style topics, so a
fresh consumer senses the current state immediately without an event storm).

Guarded throughout: a missing/corrupt trace, an absent bus, or a slow tick is a
skipped beat, never a crash. Runs only when explicitly started (``build_boot_app``
in the operator process) — importing this module starts nothing.

Gary Leckey · Aureon Institute
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any

from aureon.core.bus_trace import read_trace

logger = logging.getLogger("aureon.core.trace_pump")


@dataclass(frozen=True)
class PumpRoute:
    """One trace → topic bridge. ``seed_latest`` publishes the current latest row
    once at start (for state topics like auris); events (lighthouse) leave it False."""

    trace_name: str
    topic: str
    seed_latest: bool = False


# The default routes: the two subscribe-based signals the earlier audit flagged as
# silently broken across the process boundary, plus the cognitive immune layer's
# breach/memory events so a neutralization sensed in one process reaches the
# in-process immune-memory subscriber (and the Queen, who may observe) in another.
DEFAULT_ROUTES: tuple[PumpRoute, ...] = (
    PumpRoute("auris_cosmic_state", "auris.throne.cosmic_state", seed_latest=True),
    PumpRoute("lighthouse_event", "lighthouse.event", seed_latest=False),
    PumpRoute("integrity_guard", "bio.integrity_guard.run", seed_latest=False),
    PumpRoute("swarm_defense", "bio.swarm_defense.run", seed_latest=False),
    PumpRoute("immune_memory", "bio.immune_memory.run", seed_latest=False),
    PumpRoute("immune_regulation", "bio.immune_regulation.run", seed_latest=False),
)


class TracePump:
    """Tails per-signal traces and republishes new rows onto the local bus."""

    def __init__(
        self,
        bus: Any = None,
        routes: tuple[PumpRoute, ...] = DEFAULT_ROUTES,
        interval_s: float = 3.0,
    ) -> None:
        self._bus = bus
        self._routes = routes
        self._interval = max(0.5, float(interval_s))
        self._last_ts: dict[str, float] = {}
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._published = 0
        self._primed = False

    def _get_bus(self) -> Any:
        if self._bus is not None:
            return self._bus
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus

            self._bus = get_thought_bus()
        except Exception as exc:  # noqa: BLE001
            logger.debug("trace pump: no bus (%s)", exc)
            self._bus = None
        return self._bus

    @staticmethod
    def _row_ts(row: dict[str, Any]) -> float:
        try:
            return float(row.get("_ts", 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def prime(self) -> None:
        """Initialize the per-trace high-water mark to the newest existing row so the
        backlog is not replayed. For ``seed_latest`` routes, emit the current latest
        row once so a fresh consumer senses present state immediately."""
        for route in self._routes:
            rows = read_trace(route.trace_name, limit=200)
            newest = max((self._row_ts(r) for r in rows), default=0.0)
            self._last_ts[route.trace_name] = newest
            if route.seed_latest and rows:
                self._emit(route.topic, rows[-1])
        self._primed = True

    def tick(self) -> int:
        """One sweep: publish rows newer than the high-water mark. Returns count."""
        if not self._primed:
            self.prime()
            return 0
        count = 0
        for route in self._routes:
            try:
                for row in read_trace(route.trace_name, limit=200):
                    ts = self._row_ts(row)
                    if ts > self._last_ts.get(route.trace_name, 0.0):
                        self._emit(route.topic, row)
                        self._last_ts[route.trace_name] = ts
                        count += 1
            except Exception as exc:  # noqa: BLE001 — one bad trace never stops the pump
                logger.debug("trace pump tick(%s) skipped: %s", route.trace_name, exc)
        return count

    def _emit(self, topic: str, row: dict[str, Any]) -> None:
        bus = self._get_bus()
        if bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought

            payload = {k: v for k, v in row.items() if k != "_ts"}
            bus.publish(Thought(source="trace_pump", topic=topic, payload=payload))
            self._published += 1
        except Exception as exc:  # noqa: BLE001
            logger.debug("trace pump emit(%s) skipped: %s", topic, exc)

    # ── lifecycle ──────────────────────────────────────────────────────────
    def _loop(self) -> None:
        self.prime()
        while not self._stop.wait(self._interval):
            self.tick()

    def start(self) -> TracePump:
        if self._thread is not None and self._thread.is_alive():
            return self
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="aureon-trace-pump", daemon=True)
        self._thread.start()
        logger.info("trace pump started (%d routes, %.1fs)", len(self._routes), self._interval)
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def stats(self) -> dict[str, Any]:
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "published": self._published,
            "routes": [r.topic for r in self._routes],
            "high_water": dict(self._last_ts),
        }


_pump: TracePump | None = None


def get_trace_pump() -> TracePump:
    """Process-global pump singleton (started by the operator boot)."""
    global _pump
    if _pump is None:
        _pump = TracePump()
    return _pump


__all__ = ["PumpRoute", "TracePump", "DEFAULT_ROUTES", "get_trace_pump"]
