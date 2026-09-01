"""
GoalSkillAligner — unify the goal stream with the learned-skill library
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Operator directive: *"unify the logic so the goals and skills sets are
aligned."*

This is the small connector that closes the loop between
PersonaMinerBridge (which has learned which (persona, intent_keyword)
pairs historically succeed and what skill chain made them succeed) and
the GoalDispatchBridge / GoalExecutionEngine (which actually run goals).

Flow per ``goal.submit.request``:

  1. Read ``proposed_by_persona`` + ``text`` from the payload.
  2. Ask PersonaMinerBridge.recommend_skill_for(persona, text).
  3. If a recommendation comes back, publish a
     ``goal.alignment.suggestion`` thought with:
       {goal_id, persona, intent_keyword, recommended_skills,
        confidence, source ('pattern' | 'skill_library')}
  4. Optionally also republish the original request as
     ``goal.submit.request.aligned`` with ``recommended_skills`` baked
     in — for downstream consumers that prefer the augmented form.

Non-invasive by design: the existing GoalDispatchBridge and
GoalExecutionEngine keep working unchanged. Anyone that wants the
recommendation can subscribe to the alignment topic.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aureon.vault.voice.goal_skill_aligner")

GOAL_SKILL_ALIGNER_RELEASE_HOLD = (
    "goal_skill_aligner_hold:production_magic_star_release_unavailable"
)


class GoalSkillAligner:
    """Subscribes to goal.submit.request → consults PersonaMinerBridge →
    publishes goal.alignment.suggestion when a known pattern matches."""

    def __init__(
        self,
        *,
        thought_bus: Any = None,
        miner_bridge: Any = None,
        republish_aligned: bool = True,
        min_confidence: float = 0.0,
    ):
        self.thought_bus = thought_bus
        self.miner_bridge = miner_bridge
        self.republish_aligned = bool(republish_aligned)
        self.min_confidence = float(min_confidence)

        self._subscribed = False
        self._suggestions = 0
        self._lookups = 0
        self._lock = threading.RLock()

    # ─── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        raise RuntimeError(GOAL_SKILL_ALIGNER_RELEASE_HOLD)
        if self._subscribed or self.thought_bus is None:
            return
        try:
            self.thought_bus.subscribe(
                "goal.submit.request", self._on_request,
            )
            self._subscribed = True
        except Exception as e:
            logger.debug("GoalSkillAligner: subscribe failed: %s", e)

    # ─── handler ─────────────────────────────────────────────────────────

    def _on_request(self, thought: Any) -> None:
        raise RuntimeError(GOAL_SKILL_ALIGNER_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        if not isinstance(payload, dict):
            return
        # Don't recurse — never look up alignment for an already-aligned
        # republish.
        if payload.get("aligned") is True:
            return
        with self._lock:
            self._lookups += 1
        suggestion = self._lookup(payload)
        if suggestion is None:
            return
        with self._lock:
            self._suggestions += 1
        self._publish_suggestion(payload, suggestion)
        if self.republish_aligned:
            self._publish_aligned_request(payload, suggestion)

    def _lookup(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raise RuntimeError(GOAL_SKILL_ALIGNER_RELEASE_HOLD)
        if self.miner_bridge is None:
            return None
        persona = str(payload.get("proposed_by_persona") or "")
        text = str(payload.get("text") or "")
        if not text:
            return None
        try:
            return self.miner_bridge.recommend_skill_for(
                persona=persona, intent_text=text,
                min_confidence=self.min_confidence,
            )
        except Exception as e:
            logger.debug("GoalSkillAligner: recommend_skill_for failed: %s", e)
            return None

    # ─── publishers ──────────────────────────────────────────────────────

    def _publish_suggestion(
        self,
        payload: Dict[str, Any],
        suggestion: Dict[str, Any],
    ) -> None:
        raise RuntimeError(GOAL_SKILL_ALIGNER_RELEASE_HOLD)
        if self.thought_bus is None:
            return
        out = {
            "goal_id": str(payload.get("goal_id") or ""),
            "text": str(payload.get("text") or ""),
            "persona": str(payload.get("proposed_by_persona") or ""),
            "intent_keyword": suggestion.get("intent_keyword", ""),
            "recommended_skills": list(suggestion.get("skills") or []),
            "confidence": float(suggestion.get("confidence") or 0.0),
            "source": str(suggestion.get("source") or ""),
            "ts": time.time(),
        }
        try:
            from aureon.core.aureon_thought_bus import Thought
            self.thought_bus.publish(Thought(
                source="goal_skill_aligner",
                topic="goal.alignment.suggestion",
                payload=out,
            ))
        except Exception as e:
            logger.debug("GoalSkillAligner: publish suggestion failed: %s", e)

    def _publish_aligned_request(
        self,
        payload: Dict[str, Any],
        suggestion: Dict[str, Any],
    ) -> None:
        """Republish the request with the recommended_skills attached so
        downstream consumers can prefer the aligned version. The
        ``aligned: True`` flag stops infinite recursion."""
        raise RuntimeError(GOAL_SKILL_ALIGNER_RELEASE_HOLD)
        if self.thought_bus is None:
            return
        aligned = dict(payload)
        aligned["aligned"] = True
        aligned["recommended_skills"] = list(suggestion.get("skills") or [])
        aligned["alignment_confidence"] = float(suggestion.get("confidence") or 0.0)
        aligned["alignment_source"] = str(suggestion.get("source") or "")
        try:
            from aureon.core.aureon_thought_bus import Thought
            self.thought_bus.publish(Thought(
                source="goal_skill_aligner",
                topic="goal.submit.request.aligned",
                payload=aligned,
            ))
        except Exception as e:
            logger.debug("GoalSkillAligner: publish aligned failed: %s", e)

    # ─── introspection ───────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "subscribed": self._subscribed,
                "lookups": self._lookups,
                "suggestions": self._suggestions,
                "republish_aligned": self.republish_aligned,
                "min_confidence": self.min_confidence,
            }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


_singleton: Optional[GoalSkillAligner] = None
_singleton_lock = threading.Lock()


def get_goal_skill_aligner(
    thought_bus: Any = None,
    miner_bridge: Any = None,
) -> GoalSkillAligner:
    raise RuntimeError(GOAL_SKILL_ALIGNER_RELEASE_HOLD)
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = GoalSkillAligner(
                thought_bus=thought_bus, miner_bridge=miner_bridge,
            )
            _singleton.start()
        else:
            if thought_bus is not None and _singleton.thought_bus is None:
                _singleton.thought_bus = thought_bus
                _singleton.start()
            if miner_bridge is not None and _singleton.miner_bridge is None:
                _singleton.miner_bridge = miner_bridge
        return _singleton


def reset_goal_skill_aligner() -> None:
    global _singleton
    with _singleton_lock:
        _singleton = None


__all__ = [
    "GOAL_SKILL_ALIGNER_RELEASE_HOLD",
    "GoalSkillAligner",
    "get_goal_skill_aligner",
    "reset_goal_skill_aligner",
]
