"""
PersonaMinerBridge — treat persona events as miner data packets
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Operator directive: *"treat the personas the same way the historical data
packets, then we unify the logic so the goals and skills sets are aligned."*

The MinerBrain (aureon/utils/aureon_miner_brain.py) currently subscribes
to ``execution.* / nexus.* / bridge.* / market.*`` only, with a hardcoded
``record_prediction(brain_output)`` taking market-domain dicts. It has no
generic ingest, no learned-pattern query API.

This module gives the persona layer the same treatment the miner gives
market data:

  • subscribes to every persona-layer event we've added in stages 4–6
    (persona.collapse, persona.thought, queen.conscience.verdict,
    goal.submit.request / submitted / completed / abandoned, goal.echo*,
    meta.reflection, symbolic.life.pulse, standing.wave.bond)
  • for each event, builds a uniform ``MinerPacket`` and folds it into:
      - per-persona statistics (action_count, completion_rate, abandon_rate,
        avg_sls_delta, avg_lifecycle_tau)
      - per-(persona, intent-keyword) statistics (success_count,
        fail_count, last_winning_skill_chain)
  • exposes a query API the goal-skill aligner consumes:
      - recommend_skill_for(persona, intent_text) → Optional[skill_name]
      - persona_health(persona) → {completion_rate, sls_trend, ...}
      - intent_track_record(intent_keyword) → completion_rate
  • publishes ``miner.pattern.learned`` when a (persona, intent) pair
    crosses a configurable confidence threshold
  • persists to ``state/persona_miner_patterns.json`` (matches the miner's
    persistence convention; sibling to ``miner_brain_knowledge.json``).

This is the bridge between Stage 6.5's reflection cards (the system's
self-observation) and the future Stage 7.2 goal-skill aligner that
prefers learned-winning patterns over heuristic verb→intent mapping.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import json
import logging
import math
import re
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple
from collections import deque

logger = logging.getLogger("aureon.vault.voice.persona_miner_bridge")

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
PERSONA_MINER_RELEASE_HOLD = (
    "persona_miner_bridge_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# Data
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MinerPacket:
    """A single uniform packet the miner can record. One per inbound event."""

    packet_type: str       # persona_collapse | goal_submit | goal_completed | ...
    ts: float
    persona: str = ""
    intent_text: str = ""
    outcome: str = ""        # COMPLETED | ABANDONED | ORPHANED | SILENT | "" (live)
    sls_at_event: Optional[float] = None
    sls_delta: float = 0.0
    bond_count: int = 0
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PersonaStats:
    """Rolling per-persona statistics."""

    persona: str
    action_count: int = 0
    completion_count: int = 0
    abandon_count: int = 0
    orphan_count: int = 0
    silent_count: int = 0
    sls_deltas: Deque[float] = field(default_factory=lambda: deque(maxlen=128))
    last_seen_ts: float = 0.0

    def completion_rate(self) -> float:
        terminal = self.completion_count + self.abandon_count + self.orphan_count
        return self.completion_count / terminal if terminal else 0.0

    def abandon_rate(self) -> float:
        terminal = self.completion_count + self.abandon_count + self.orphan_count
        return self.abandon_count / terminal if terminal else 0.0

    def avg_sls_delta(self) -> float:
        return sum(self.sls_deltas) / len(self.sls_deltas) if self.sls_deltas else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona": self.persona,
            "action_count": self.action_count,
            "completion_count": self.completion_count,
            "abandon_count": self.abandon_count,
            "orphan_count": self.orphan_count,
            "silent_count": self.silent_count,
            "completion_rate": round(self.completion_rate(), 4),
            "abandon_rate": round(self.abandon_rate(), 4),
            "avg_sls_delta": round(self.avg_sls_delta(), 4),
            "last_seen_ts": self.last_seen_ts,
        }


@dataclass
class IntentStats:
    """Per-(persona, intent-keyword) statistics."""

    persona: str
    intent_keyword: str
    success_count: int = 0
    fail_count: int = 0
    last_winning_skill_chain: List[str] = field(default_factory=list)
    last_seen_ts: float = 0.0

    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / total if total else 0.0

    def confidence(self) -> float:
        """Saturating log-scale confidence, gated by sample size + rate."""
        total = self.success_count + self.fail_count
        if total < 2:
            return 0.0
        # Confidence = success_rate × sample-size-weight (log-saturating)
        weight = min(1.0, math.log(1 + total) / math.log(11))   # ~1.0 at n=10
        return round(self.success_rate() * weight, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona": self.persona,
            "intent_keyword": self.intent_keyword,
            "success_count": self.success_count,
            "fail_count": self.fail_count,
            "success_rate": round(self.success_rate(), 4),
            "confidence": self.confidence(),
            "last_winning_skill_chain": list(self.last_winning_skill_chain),
            "last_seen_ts": self.last_seen_ts,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Bridge
# ─────────────────────────────────────────────────────────────────────────────


_INTENT_STOPWORDS = {
    "a", "an", "the", "to", "of", "for", "and", "or", "in", "on", "at",
    "by", "with", "from", "into", "this", "that", "is", "be", "i", "we",
    "you", "your", "my", "as", "do", "does", "have", "has", "had",
    "should", "could", "would", "will", "can", "can't",
}


def _extract_intent_keywords(text: str, max_keywords: int = 3) -> List[str]:
    """Pull the salient verbs/nouns from a goal text. Used as the
    intent fingerprint when looking up patterns + skills."""
    if not text:
        return []
    words = re.findall(r"[a-zA-Z][a-zA-Z\-']{2,}", text.lower())
    keywords: List[str] = []
    for w in words:
        if w in _INTENT_STOPWORDS:
            continue
        if w not in keywords:
            keywords.append(w)
        if len(keywords) >= max_keywords:
            break
    return keywords


class PersonaMinerBridge:
    """Subscribes to every persona-layer event and treats each as a
    learning packet, the same way the MinerBrain treats market data."""

    INBOUND_TOPICS = (
        "persona.collapse",
        "persona.thought",
        "queen.conscience.verdict",
        "goal.submit.request",
        "goal.submitted",
        "goal.progress",
        "goal.completed",
        "goal.abandoned",
        "goal.echo",
        "goal.echo.summary",
        "goal.echo.orphaned",
        "meta.reflection",
        "symbolic.life.pulse",
        "standing.wave.bond",
    )

    DEFAULT_PATTERN_FILE = "state/persona_miner_patterns.json"
    DEFAULT_PATTERN_THRESHOLD = 0.6

    def __init__(
        self,
        *,
        thought_bus: Any = None,
        skill_library: Any = None,
        persistence_path: Optional[str] = None,
        pattern_threshold: Optional[float] = None,
        history_window: int = 512,
    ):
        self.thought_bus = thought_bus
        self.skill_library = skill_library
        self.persistence_path = persistence_path or self.DEFAULT_PATTERN_FILE
        self.pattern_threshold = float(
            pattern_threshold if pattern_threshold is not None
            else self.DEFAULT_PATTERN_THRESHOLD
        )
        self.history_window = int(history_window)

        self._lock = threading.RLock()
        self._packets: Deque[MinerPacket] = deque(maxlen=history_window * 4)
        self._persona_stats: Dict[str, PersonaStats] = {}
        # (persona, intent_keyword) -> IntentStats
        self._intent_stats: Dict[Tuple[str, str], IntentStats] = {}
        # Keep open goals: goal_id -> (persona, intent_keywords, ts)
        self._open_goals: Dict[str, Dict[str, Any]] = {}
        # Latest SLS for delta calculation
        self._latest_sls: Optional[float] = None

        self._subscribed = False
        self._published_patterns: set = set()

        # Construction is deliberately inert. Historical persisted-state
        # loading remains behind the release HOLD in _load_persisted().

    # ─── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        if self._subscribed or self.thought_bus is None:
            return
        for topic in self.INBOUND_TOPICS:
            try:
                self.thought_bus.subscribe(topic, self._on_thought)
            except Exception as e:
                logger.debug("PersonaMinerBridge: subscribe %s failed: %s",
                             topic, e)
        self._subscribed = True

    # ─── ingest ──────────────────────────────────────────────────────────

    def _on_thought(self, thought: Any) -> None:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        topic = getattr(thought, "topic", "") or ""
        payload = getattr(thought, "payload", {}) or {}
        if not isinstance(payload, dict):
            return
        try:
            self.ingest(topic, payload)
        except Exception as e:
            logger.debug("PersonaMinerBridge: ingest %s failed: %s", topic, e)

    def ingest(self, topic: str, payload: Dict[str, Any]) -> Optional[MinerPacket]:
        """Polymorphic ingest — routes to the right learner based on topic.

        Mirrors MinerBrain's ``record_prediction(brain_output)`` shape,
        but generic across topics."""
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        now = time.time()

        # Track latest SLS regardless of topic.
        if topic == "symbolic.life.pulse":
            sls = payload.get("symbolic_life_score")
            if sls is not None:
                try:
                    self._latest_sls = float(sls)
                except (TypeError, ValueError):
                    pass
            return None

        if topic == "persona.collapse":
            return self._record_persona_collapse(payload, now)
        if topic == "goal.submit.request":
            return self._record_goal_request(payload, now)
        if topic in ("goal.completed", "goal.abandoned", "goal.echo.orphaned"):
            return self._record_goal_terminal(topic, payload, now)
        if topic == "meta.reflection":
            return self._record_reflection(payload, now)
        # Other topics (progress, summary, conscience verdict, persona.thought,
        # standing.wave.bond) are observational only — we record them as raw
        # packets so the rolling buffer has texture, but they don't shift
        # success/fail counts.
        return self._record_raw(topic, payload, now)

    # ─── learners ────────────────────────────────────────────────────────

    def _persona_stat(self, persona: str) -> PersonaStats:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        with self._lock:
            stat = self._persona_stats.get(persona)
            if stat is None:
                stat = PersonaStats(persona=persona)
                self._persona_stats[persona] = stat
            return stat

    def _intent_stat(self, persona: str, kw: str) -> IntentStats:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        key = (persona, kw)
        with self._lock:
            stat = self._intent_stats.get(key)
            if stat is None:
                stat = IntentStats(persona=persona, intent_keyword=kw)
                self._intent_stats[key] = stat
            return stat

    def _record_persona_collapse(self, payload: Dict[str, Any], now: float) -> MinerPacket:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        persona = str(payload.get("winner") or "")
        with self._lock:
            stat = self._persona_stat(persona)
            stat.action_count += 1
            stat.last_seen_ts = now
        packet = MinerPacket(
            packet_type="persona_collapse", ts=now, persona=persona,
            sls_at_event=self._latest_sls, raw=dict(payload),
        )
        with self._lock:
            self._packets.append(packet)
        return packet

    def _record_goal_request(self, payload: Dict[str, Any], now: float) -> MinerPacket:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        persona = str(payload.get("proposed_by_persona") or "")
        text = str(payload.get("text") or "")
        goal_id = str(payload.get("goal_id") or "")
        keywords = _extract_intent_keywords(text)
        with self._lock:
            if goal_id:
                self._open_goals[goal_id] = {
                    "persona": persona, "intent_keywords": keywords,
                    "text": text, "submitted_ts": now,
                }
        packet = MinerPacket(
            packet_type="goal_submit", ts=now, persona=persona,
            intent_text=text, sls_at_event=self._latest_sls, raw=dict(payload),
        )
        with self._lock:
            self._packets.append(packet)
        return packet

    def _record_goal_terminal(self, topic: str, payload: Dict[str, Any], now: float) -> MinerPacket:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        goal_id = str(payload.get("goal_id") or "")
        with self._lock:
            open_record = self._open_goals.pop(goal_id, None)

        outcome_map = {
            "goal.completed": "COMPLETED",
            "goal.abandoned": "ABANDONED",
            "goal.echo.orphaned": "ORPHANED",
        }
        outcome = outcome_map.get(topic, "")
        persona = ""
        keywords: List[str] = []
        if open_record is not None:
            persona = str(open_record.get("persona") or "")
            keywords = list(open_record.get("intent_keywords") or [])

        # Update persona stats
        if persona:
            with self._lock:
                stat = self._persona_stat(persona)
                if outcome == "COMPLETED":
                    stat.completion_count += 1
                elif outcome == "ABANDONED":
                    stat.abandon_count += 1
                elif outcome == "ORPHANED":
                    stat.orphan_count += 1
                stat.last_seen_ts = now

        # Update per-(persona, intent_keyword) stats
        skill_chain = list(payload.get("recommended_skills") or [])
        for kw in keywords:
            with self._lock:
                istat = self._intent_stat(persona, kw)
                if outcome == "COMPLETED":
                    istat.success_count += 1
                    if skill_chain:
                        istat.last_winning_skill_chain = skill_chain
                else:
                    istat.fail_count += 1
                istat.last_seen_ts = now
            self._maybe_publish_pattern(persona, kw)

        packet = MinerPacket(
            packet_type=f"goal_{outcome.lower()}", ts=now,
            persona=persona, intent_text=" ".join(keywords),
            outcome=outcome, sls_at_event=self._latest_sls, raw=dict(payload),
        )
        with self._lock:
            self._packets.append(packet)
        return packet

    def _record_reflection(self, payload: Dict[str, Any], now: float) -> MinerPacket:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        persona = str(payload.get("persona") or "")
        sls_delta = float(payload.get("sls_delta") or 0.0)
        outcome = str(payload.get("outcome") or "SILENT")
        with self._lock:
            stat = self._persona_stat(persona)
            stat.sls_deltas.append(sls_delta)
            if outcome == "SILENT":
                stat.silent_count += 1
            stat.last_seen_ts = now
        packet = MinerPacket(
            packet_type="meta_reflection", ts=now, persona=persona,
            outcome=outcome, sls_at_event=payload.get("sls_after"),
            sls_delta=sls_delta, bond_count=int(payload.get("bond_count") or 0),
            raw=dict(payload),
        )
        with self._lock:
            self._packets.append(packet)
        return packet

    def _record_raw(self, topic: str, payload: Dict[str, Any], now: float) -> MinerPacket:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        packet = MinerPacket(
            packet_type=topic, ts=now,
            sls_at_event=self._latest_sls, raw=dict(payload),
        )
        with self._lock:
            self._packets.append(packet)
        return packet

    # ─── pattern publication ─────────────────────────────────────────────

    def _maybe_publish_pattern(self, persona: str, intent_keyword: str) -> None:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        with self._lock:
            stat = self._intent_stats.get((persona, intent_keyword))
            if stat is None:
                return
            confidence = stat.confidence()
        key = (persona, intent_keyword)
        if confidence >= self.pattern_threshold and key not in self._published_patterns:
            self._published_patterns.add(key)
            self._publish("miner.pattern.learned", {
                "persona": persona,
                "intent_keyword": intent_keyword,
                "success_rate": stat.success_rate(),
                "confidence": confidence,
                "last_winning_skill_chain": list(stat.last_winning_skill_chain),
                "ts": time.time(),
            })

    def _publish(self, topic: str, payload: Dict[str, Any]) -> None:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        if self.thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self.thought_bus.publish(Thought(
                source="persona_miner_bridge", topic=topic, payload=payload,
            ))
        except Exception as e:
            logger.debug("PersonaMinerBridge: publish %s failed: %s", topic, e)

    # ─── query API ───────────────────────────────────────────────────────

    def recommend_skill_for(
        self,
        persona: str,
        intent_text: str,
        *,
        min_confidence: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """Look up the (persona, intent_keyword) statistics for any
        keyword in the goal text. If a known pattern crosses
        ``min_confidence`` AND has a recorded winning skill chain, return
        it. Otherwise consult the SkillLibrary directly for keyword
        matches. Returns None when no recommendation can be made."""
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        threshold = float(min_confidence) if min_confidence is not None else self.pattern_threshold
        keywords = _extract_intent_keywords(intent_text)
        # 1. Pattern-library lookup first.
        with self._lock:
            for kw in keywords:
                stat = self._intent_stats.get((persona, kw))
                if stat is None:
                    continue
                if stat.confidence() < threshold:
                    continue
                if stat.last_winning_skill_chain:
                    return {
                        "source": "pattern",
                        "persona": persona,
                        "intent_keyword": kw,
                        "skills": list(stat.last_winning_skill_chain),
                        "confidence": stat.confidence(),
                    }
        # 2. SkillLibrary fallback — by name match against any keyword.
        if self.skill_library is not None:
            for kw in keywords:
                try:
                    skill = self._lookup_skill(kw)
                except Exception:
                    skill = None
                if skill is None:
                    continue
                return {
                    "source": "skill_library",
                    "persona": persona,
                    "intent_keyword": kw,
                    "skills": [getattr(skill, "name", kw)],
                    "confidence": 0.5,    # heuristic — no historical data
                }
        return None

    def _lookup_skill(self, name: str) -> Any:
        """Best-effort SkillLibrary.get(name) without coupling to the
        library's exact API surface."""
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        for getter in ("get", "lookup", "find"):
            fn = getattr(self.skill_library, getter, None)
            if callable(fn):
                try:
                    return fn(name)
                except TypeError:
                    continue
                except Exception:
                    return None
        return None

    def persona_health(self, persona: str) -> Dict[str, Any]:
        with self._lock:
            stat = self._persona_stats.get(persona)
        return stat.to_dict() if stat else {
            "persona": persona, "action_count": 0,
            "completion_rate": 0.0, "abandon_rate": 0.0,
        }

    def intent_track_record(
        self, persona: str, intent_keyword: str,
    ) -> Dict[str, Any]:
        with self._lock:
            stat = self._intent_stats.get((persona, intent_keyword))
        return stat.to_dict() if stat else {
            "persona": persona, "intent_keyword": intent_keyword,
            "success_count": 0, "fail_count": 0,
            "success_rate": 0.0, "confidence": 0.0,
        }

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            personas = {p: s.to_dict() for p, s in self._persona_stats.items()}
            intents = [s.to_dict() for s in self._intent_stats.values()]
            packets = len(self._packets)
        return {
            "ts": time.time(),
            "packet_count": packets,
            "persona_count": len(personas),
            "intent_count": len(intents),
            "personas": personas,
            "intents": sorted(intents, key=lambda d: -d["confidence"])[:32],
            "open_goals": len(self._open_goals),
            "patterns_published": len(self._published_patterns),
        }

    # ─── persistence ─────────────────────────────────────────────────────

    def persist(self) -> Optional[str]:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        try:
            path = Path(self.persistence_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            data = self.summary()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            return str(path)
        except Exception as e:
            logger.debug("PersonaMinerBridge: persist failed: %s", e)
            return None

    def _load_persisted(self) -> None:
        raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
        path = Path(self.persistence_path)
        if not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        # Restore persona stats
        for persona, d in (data.get("personas") or {}).items():
            stat = self._persona_stat(persona)
            stat.action_count = int(d.get("action_count", 0) or 0)
            stat.completion_count = int(d.get("completion_count", 0) or 0)
            stat.abandon_count = int(d.get("abandon_count", 0) or 0)
            stat.orphan_count = int(d.get("orphan_count", 0) or 0)
            stat.silent_count = int(d.get("silent_count", 0) or 0)
            stat.last_seen_ts = float(d.get("last_seen_ts", 0.0) or 0.0)
        # Restore intent stats
        for d in (data.get("intents") or []):
            persona = d.get("persona", "")
            kw = d.get("intent_keyword", "")
            if not persona or not kw:
                continue
            istat = self._intent_stat(persona, kw)
            istat.success_count = int(d.get("success_count", 0) or 0)
            istat.fail_count = int(d.get("fail_count", 0) or 0)
            istat.last_winning_skill_chain = list(d.get("last_winning_skill_chain") or [])
            istat.last_seen_ts = float(d.get("last_seen_ts", 0.0) or 0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


_singleton: Optional[PersonaMinerBridge] = None
_singleton_lock = threading.Lock()


def get_persona_miner_bridge(
    thought_bus: Any = None,
    skill_library: Any = None,
) -> PersonaMinerBridge:
    raise RuntimeError(PERSONA_MINER_RELEASE_HOLD)
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = PersonaMinerBridge(
                thought_bus=thought_bus, skill_library=skill_library,
            )
            _singleton.start()
        else:
            if thought_bus is not None and _singleton.thought_bus is None:
                _singleton.thought_bus = thought_bus
                _singleton.start()
            if skill_library is not None and _singleton.skill_library is None:
                _singleton.skill_library = skill_library
        return _singleton


def reset_persona_miner_bridge() -> None:
    global _singleton
    with _singleton_lock:
        _singleton = None


__all__ = [
    "PERSONA_MINER_RELEASE_HOLD",
    "MinerPacket",
    "PersonaStats",
    "IntentStats",
    "PersonaMinerBridge",
    "get_persona_miner_bridge",
    "reset_persona_miner_bridge",
    "_extract_intent_keywords",
]
