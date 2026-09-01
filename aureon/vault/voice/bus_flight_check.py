"""
BusFlightCheck — what is attached to the standing wave right now
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The HNC log 17/04/2026 08:49 says Aureon must be able to answer, on
demand, "*what is attached to the standing wave at any given time?*"
Without that answer the chorus cannot tell whether it is forming a
prime timeline or broadcasting into silence.

This module is the answer. It subscribes to the bus with the ``*``
wildcard to watch traffic in real time, and it reads the bus's new
``list_subscribed_topics()`` accessor to see who is listening. From
those two inputs it builds:

  topology()               — per-topic snapshot: subscribers, publishers
                             observed, recent publication count, last-seen
                             delta, dead-branch flags.
  standing_wave_report()   — scalar health score in [0, 1] combining
                             coverage (subscribed-and-active), publication
                             balance (variance), and freshness.
  watch(interval_s=PHI²)   — background daemon that publishes
                             ``flight.check.pulse`` on the bus at the
                             φ² cadence the rest of the harmonic stack
                             runs on.

Non-invasive by design — no monkey-patching of subscribe/publish, one
read-only accessor added to ThoughtBus. Survives the Redis bus variant
transparently (the Redis bus exposes the same API).

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("aureon.vault.voice.bus_flight_check")

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
PHI_SQUARED: float = PHI * PHI
BUS_FLIGHT_CHECK_RELEASE_HOLD = (
    "bus_flight_check_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# Activity tracker
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class _TopicActivity:
    """Per-topic rolling stats."""

    publications: int = 0
    last_seen_ts: float = 0.0
    recent_ts: Deque[float] = field(default_factory=lambda: deque(maxlen=128))
    publishers: Counter = field(default_factory=Counter)

    def bump(self, source: str) -> None:
        now = time.time()
        self.publications += 1
        self.last_seen_ts = now
        self.recent_ts.append(now)
        if source:
            self.publishers[source] += 1

    def recent_count(self, horizon_s: float) -> int:
        if not self.recent_ts:
            return 0
        cutoff = time.time() - horizon_s
        return sum(1 for t in self.recent_ts if t >= cutoff)

    def last_seen_s_ago(self) -> float:
        if self.last_seen_ts == 0.0:
            return float("inf")
        return max(0.0, time.time() - self.last_seen_ts)


# ─────────────────────────────────────────────────────────────────────────────
# BusFlightCheck
# ─────────────────────────────────────────────────────────────────────────────


class BusFlightCheck:
    """Live standing-wave topology inspector."""

    def __init__(
        self,
        thought_bus: Any,
        *,
        recent_horizon_s: float = 30.0,
        orphan_silent_s: float = 60.0,
        watch_interval_s: float = PHI_SQUARED,
    ):
        self.thought_bus = thought_bus
        self.recent_horizon_s = float(recent_horizon_s)
        self.orphan_silent_s = float(orphan_silent_s)
        self.watch_interval_s = float(watch_interval_s)

        self._lock = threading.RLock()
        self._activity: Dict[str, _TopicActivity] = defaultdict(_TopicActivity)
        self._start_ts = time.time()
        self._subscribed = False

        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ─── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to the wildcard so we see every publication."""
        raise RuntimeError(BUS_FLIGHT_CHECK_RELEASE_HOLD)
        if self._subscribed or self.thought_bus is None:
            return
        try:
            self.thought_bus.subscribe("*", self._on_any_thought)
            self._subscribed = True
        except Exception as e:
            logger.debug("BusFlightCheck: subscribe failed: %s", e)

    def start_watching(self) -> None:
        """Start the background daemon that publishes flight.check.pulse."""
        raise RuntimeError(BUS_FLIGHT_CHECK_RELEASE_HOLD)
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._watch_loop, name="BusFlightCheck", daemon=True,
        )
        self._thread.start()

    def stop_watching(self) -> None:
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    # ─── observer ────────────────────────────────────────────────────────

    def _on_any_thought(self, thought: Any) -> None:
        raise RuntimeError(BUS_FLIGHT_CHECK_RELEASE_HOLD)
        topic = getattr(thought, "topic", "") or ""
        source = getattr(thought, "source", "") or ""
        if not topic:
            return
        # Skip our own publication so it doesn't self-bloat.
        if topic == "flight.check.pulse" and source == "bus_flight_check":
            return
        with self._lock:
            self._activity[topic].bump(source)

    # ─── topology ────────────────────────────────────────────────────────

    def topology(self) -> Dict[str, Any]:
        """Full snapshot: per-topic subscribers + publishers + activity."""
        subscribed = self._subscribed_topics()
        # Subscriber counts per pattern
        sub_counts: Dict[str, int] = {}
        for pattern in subscribed:
            try:
                sub_counts[pattern] = int(
                    self.thought_bus.subscriber_count(pattern)
                )
            except Exception:
                sub_counts[pattern] = 1  # best-effort — assume present

        with self._lock:
            active = dict(self._activity)

        # Build per-topic records for topics we've seen OR topics subscribed to
        all_topics: Set[str] = set(active.keys()) | set(subscribed)
        # Exclude "*" — it's a meta-subscription pattern, not a real topic
        all_topics.discard("*")

        topics_report: List[Dict[str, Any]] = []
        orphan_published: List[str] = []
        orphan_subscribed: List[str] = []

        for topic in sorted(all_topics):
            activity = active.get(topic)
            pubs = activity.publications if activity else 0
            recent = activity.recent_count(self.recent_horizon_s) if activity else 0
            last_s_ago = activity.last_seen_s_ago() if activity else float("inf")
            publishers = list(activity.publishers.most_common(5)) if activity else []

            # Subscribers that match this topic
            matching_subs = self._subscribers_matching(topic, subscribed, sub_counts)
            sub_total = sum(matching_subs.values())
            is_subscribed = sub_total > 0

            orphan_pub = (pubs > 0 and not is_subscribed)
            orphan_sub = (is_subscribed and pubs == 0)
            if orphan_pub:
                orphan_published.append(topic)
            if orphan_sub and topic in subscribed:
                orphan_subscribed.append(topic)

            topics_report.append({
                "topic": topic,
                "subscribers": sub_total,
                "subscriber_patterns": matching_subs,
                "publishers": publishers,
                "publications": pubs,
                "publications_recent": recent,
                "last_seen_s_ago": round(last_s_ago, 3) if last_s_ago != float("inf") else None,
                "orphan_published": orphan_pub,
                "orphan_subscribed": orphan_sub,
            })

        return {
            "ts": time.time(),
            "uptime_s": round(time.time() - self._start_ts, 3),
            "recent_horizon_s": self.recent_horizon_s,
            "topics": topics_report,
            "active_topic_count": sum(1 for r in topics_report if r["publications_recent"] > 0),
            "dormant_topic_count": sum(
                1 for r in topics_report
                if r["publications"] > 0 and r["publications_recent"] == 0
            ),
            "subscribed_topic_count": sum(1 for r in topics_report if r["subscribers"] > 0),
            "orphans_published_unsubscribed": orphan_published,
            "orphans_subscribed_unpublished": orphan_subscribed,
            "wildcard_subscribers": sub_counts.get("*", 0),
            "total_publications": sum(r["publications"] for r in topics_report),
        }

    def standing_wave_report(self) -> Dict[str, Any]:
        """One scalar health score for the whole standing wave, plus the
        inputs it was computed from."""
        topo = self.topology()
        topics = topo["topics"]
        if not topics:
            return {**topo, "health": 0.0,
                    "covered_ratio": 0.0,
                    "active_ratio": 0.0,
                    "publication_balance": 0.0}

        covered = sum(1 for r in topics if r["subscribers"] > 0) / len(topics)
        active = (topo["active_topic_count"] / len(topics)) if topics else 0.0

        # Publication balance: inverse of normalised variance across topics.
        # A flat distribution (every topic sees roughly the same traffic)
        # scores high. Concentrated traffic scores low.
        pubs = [r["publications"] for r in topics if r["publications"] > 0]
        if len(pubs) >= 2:
            mu = sum(pubs) / len(pubs)
            var = sum((p - mu) ** 2 for p in pubs) / len(pubs)
            # Normalise by mu² so it doesn't scale with absolute volume.
            balance = 1.0 / (1.0 + (var / max(mu ** 2, 1e-6)))
        else:
            balance = 1.0 if pubs else 0.0

        # Three-factor health. Clamp each factor to [0, 1] defensively.
        covered = max(0.0, min(1.0, covered))
        active = max(0.0, min(1.0, active))
        balance = max(0.0, min(1.0, balance))
        health = covered * active * balance

        return {
            **topo,
            "health": round(health, 4),
            "covered_ratio": round(covered, 4),
            "active_ratio": round(active, 4),
            "publication_balance": round(balance, 4),
        }

    # ─── watch loop ──────────────────────────────────────────────────────

    def _watch_loop(self) -> None:
        raise RuntimeError(BUS_FLIGHT_CHECK_RELEASE_HOLD)
        while self._running:
            try:
                report = self.standing_wave_report()
                self._publish_pulse(report)
            except Exception as e:
                logger.debug("BusFlightCheck: watch iteration failed: %s", e)
            time.sleep(self.watch_interval_s)

    def _publish_pulse(self, report: Dict[str, Any]) -> None:
        raise RuntimeError(BUS_FLIGHT_CHECK_RELEASE_HOLD)
        if self.thought_bus is None:
            return
        # Compact payload for the bus — trim per-topic arrays so we don't
        # flood the channel.
        payload = {
            "ts": report["ts"],
            "health": report["health"],
            "covered_ratio": report["covered_ratio"],
            "active_ratio": report["active_ratio"],
            "publication_balance": report["publication_balance"],
            "active_topic_count": report["active_topic_count"],
            "dormant_topic_count": report["dormant_topic_count"],
            "subscribed_topic_count": report["subscribed_topic_count"],
            "total_publications": report["total_publications"],
            "orphans_published_unsubscribed": report["orphans_published_unsubscribed"],
            "orphans_subscribed_unpublished": report["orphans_subscribed_unpublished"],
        }
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        try:
            if Thought is not None:
                self.thought_bus.publish(Thought(
                    source="bus_flight_check",
                    topic="flight.check.pulse",
                    payload=payload,
                ))
            else:
                self.thought_bus.publish(topic="flight.check.pulse",
                                         payload=payload,
                                         source="bus_flight_check")
        except Exception as e:
            logger.debug("BusFlightCheck: pulse publish failed: %s", e)

    # ─── helpers ─────────────────────────────────────────────────────────

    def _subscribed_topics(self) -> List[str]:
        getter = getattr(self.thought_bus, "list_subscribed_topics", None)
        if callable(getter):
            try:
                return list(getter())
            except Exception as e:
                logger.debug("BusFlightCheck: list_subscribed_topics failed: %s", e)
        # Fallback — read _subs directly (private, but present on both
        # ThoughtBus variants).
        try:
            subs = getattr(self.thought_bus, "_subs", None)
            if subs:
                return list(subs.keys())
        except Exception:
            pass
        return []

    @staticmethod
    def _matches(topic: str, pattern: str) -> bool:
        """Mirror ThoughtBus._match_handlers' prefix-* semantics."""
        if pattern == "*":
            return True
        if pattern.endswith(".*"):
            return topic.startswith(pattern[:-1])
        return topic == pattern

    def _subscribers_matching(
        self,
        topic: str,
        patterns: List[str],
        counts: Dict[str, int],
    ) -> Dict[str, int]:
        """Which subscription patterns match a concrete topic, and with
        how many handlers each. Excludes the raw ``*`` wildcard so we
        don't double-count BusFlightCheck itself."""
        matches: Dict[str, int] = {}
        for pattern in patterns:
            if pattern == "*":
                continue
            if self._matches(topic, pattern):
                matches[pattern] = counts.get(pattern, 1)
        return matches


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


_singleton: Optional[BusFlightCheck] = None
_singleton_lock = threading.Lock()


def get_bus_flight_check(thought_bus: Any = None) -> BusFlightCheck:
    raise RuntimeError(BUS_FLIGHT_CHECK_RELEASE_HOLD)
    global _singleton
    with _singleton_lock:
        if _singleton is None and thought_bus is not None:
            _singleton = BusFlightCheck(thought_bus=thought_bus)
            _singleton.start()
        return _singleton


def reset_bus_flight_check() -> None:
    global _singleton
    with _singleton_lock:
        _singleton = None


__all__ = [
    "BUS_FLIGHT_CHECK_RELEASE_HOLD",
    "BusFlightCheck",
    "get_bus_flight_check",
    "reset_bus_flight_check",
    "PHI",
    "PHI_SQUARED",
]
