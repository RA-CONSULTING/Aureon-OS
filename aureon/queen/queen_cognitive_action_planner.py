"""
QueenCognitiveActionPlanner — Autonomous Ollama-powered goal synthesiser.

Listens to the ThoughtBus for metacognitive events (internal dialogues,
insights, mood/urgency spikes) and every φ² × 60 ≈ 157s synthesises a
coherent, concrete goal using Ollama chain-of-thought reasoning, then
submits it to the GoalExecutionEngine.

The organism does not wait to be asked. It perceives its own cognitive
state, reasons about what action would move it toward its $1B goal, and
acts. This is the bridge between self-awareness and purposeful motion.
"""
from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List

from aureon.core.lambda_reading import format_lambda, lambda_reading

logger = logging.getLogger("aureon.queen.cognitive_action_planner")

PHI = (1.0 + math.sqrt(5.0)) / 2.0
_PLAN_INTERVAL = PHI * PHI * 60.0   # ≈ 157s between autonomous goal submissions

NO_READING = "no reading"


def _hnc_max_age_s() -> float:
    """Age limit for a stored Λ(t) or Γ. Same window as the canonical field.

    Default 300 s (``aureon.core.hnc_field.FIELD_MAX_AGE_S``). Override is
    ``AUREON_HNC_FIELD_MAX_AGE_S``. The planner does not keep a second
    clock. A stored reading older than this is None.
    """
    from aureon.core.hnc_field import _max_age_s

    return _max_age_s()


def published_lambda(payload: Any) -> float | None:
    """Finite Λ(t) on a payload that actually carries the key, or None.

    The live planner does not take Λ(t) from ``ics.source_law.cognition``.
    That event omits it. ``read_canonical_field`` is the one published
    reading. This helper remains the finite check for a mapping that
    does include ``lambda_t``. A missing key is None. A real ``0.0`` stays.
    """
    if not isinstance(payload, dict) or "lambda_t" not in payload:
        return None
    return lambda_reading(payload["lambda_t"])



def lambda_phase_for(lam: float | None) -> str:
    """Phase label from a measured Λ(t). A gap is not a threshold decision."""
    if lam is None:
        return NO_READING
    if lam < 30:
        return "TRANSITION"
    if lam < 65:
        return "COHERENCE"
    return "UNITY"


def _reading_or_clear(payload: Any, key: str) -> float | None:
    """Urgency has no max-age. Omission clears it. A present 0.0 stays 0.0."""
    if not isinstance(payload, dict) or key not in payload:
        return None
    return lambda_reading(payload[key])


class QueenCognitiveActionPlanner:
    """
    Autonomous cognitive planner that bridges self-awareness → purposeful action.

    Subscribes to ThoughtBus for:
      • queen.metacognition.internal_dialogue
      • queen.metacognition.insight.*
      • queen.metacognition.dream
      • ics.source_law.cognition

    Accumulates context in a rolling buffer, then every ~157s asks Ollama:
    "Given this organism's current cognitive state, what ONE concrete goal
    should it pursue right now to advance toward its objectives?"
    The answer is submitted to GoalExecutionEngine.
    """

    def __init__(
        self,
        goal_engine: Any = None,
        thought_bus: Any = None,
        ollama_adapter: Any = None,
    ) -> None:
        self._goal_engine = goal_engine
        self._thought_bus = thought_bus
        self._ollama = ollama_adapter

        self._dialogues: Deque[str] = deque(maxlen=12)
        self._insights: Deque[Dict[str, Any]] = deque(maxlen=8)
        self._last_mood: str = "UNKNOWN"
        self._last_urgency: float | None = None
        self._last_coherence: float | None = None
        self._last_coherence_ts: float | None = None
        self._last_consciousness: str = "DORMANT"
        self._last_lambda_phase: str = NO_READING
        self._last_lambda_t: float | None = None
        self._last_lambda_ts: float | None = None

        self._last_plan_ts: float = 0.0
        self._plan_count: int = 0
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────

    def set_ollama_adapter(self, adapter: Any) -> None:
        with self._lock:
            self._ollama = adapter

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._subscribe()
        self._thread = threading.Thread(
            target=self._plan_loop,
            daemon=True,
            name="queen-cognitive-planner",
        )
        self._thread.start()
        logger.info("QueenCognitiveActionPlanner started (interval=%.1fs)", _PLAN_INTERVAL)

    def stop(self) -> None:
        self._running = False

    # ─────────────────────────────────────────────────────────────────────
    # ThoughtBus subscription
    # ─────────────────────────────────────────────────────────────────────

    def _subscribe(self) -> None:
        if self._thought_bus is None:
            return
        try:
            self._thought_bus.subscribe(
                "queen.metacognition.*",
                self._on_metacognition,
                source_filter=None,
            )
        except Exception:
            pass
        try:
            self._thought_bus.subscribe(
                "ics.source_law.cognition",
                self._on_source_law,
                source_filter=None,
            )
        except Exception:
            pass

    def _on_metacognition(self, topic: str, payload: Dict[str, Any], **_) -> None:
        subtopic = topic.split(".")[-1] if "." in topic else topic
        if subtopic == "internal_dialogue":
            text = payload.get("text") or payload.get("dialogue") or ""
            if text:
                with self._lock:
                    self._dialogues.append(str(text)[:120])
                    if "mood" in payload:
                        self._last_mood = str(payload.get("mood") or self._last_mood)
                    self._last_urgency = _reading_or_clear(payload, "urgency")
                    # A missing coherence key is not the previous number.
                    # The finite check rejects bool, NaN, and non-numeric.
                    if "coherence" in payload:
                        self._last_coherence = lambda_reading(payload.get("coherence"))
                        self._last_coherence_ts = (
                            time.time() if self._last_coherence is not None else None
                        )
                    else:
                        self._last_coherence = None
                        self._last_coherence_ts = None
                    if "consciousness" in payload:
                        self._last_consciousness = payload.get("consciousness", self._last_consciousness)
        elif subtopic in ("insight", "dream") or topic.startswith("queen.metacognition.insight"):
            with self._lock:
                self._insights.append({"type": subtopic, "data": payload, "ts": time.time()})

    def _on_source_law(self, topic: str, payload: Dict[str, Any], **_) -> None:
        """Refresh Λ(t) and Γ from the canonical HNC field.

        ``ics.source_law.cognition`` does not carry ``lambda_t`` or
        ``coherence_gamma``. The one published reading is
        ``read_canonical_field``: the live daemon on the thought bus,
        then ``state/hnc_live_trace.jsonl``. That reader already drops
        a row older than its max age (300 s, ``AUREON_HNC_FIELD_MAX_AGE_S``).
        Copying the same numbers onto the cognition payload would be a
        second source that can disagree with the field.
        """
        try:
            from aureon.core.hnc_field import read_canonical_field
            field = read_canonical_field(self._thought_bus)
        except Exception:
            field = None
        with self._lock:
            self._adopt_canonical_field(field)

    def _adopt_canonical_field(self, field: Any, *, now: float | None = None) -> None:
        """Store Λ(t) and Γ only when the canonical field is finite and fresh.

        Stale, missing, or non-finite becomes None. A measured 0.0 stays.
        The age limit is the field's own ``_max_age_s`` (default 300 s).
        """
        now = time.time() if now is None else now
        limit = _hnc_max_age_s()
        stamp = getattr(field, "source_timestamp", None) if field is not None else None
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)):
            stamp = None
        fresh = (
            field is not None
            and bool(getattr(field, "available", False))
            and getattr(field, "freshness_status", None) == "fresh"
            and stamp is not None
            and now - float(stamp) <= limit
        )
        if not fresh:
            self._last_lambda_t = None
            self._last_lambda_ts = None
            self._last_coherence = None
            self._last_coherence_ts = None
            self._last_lambda_phase = NO_READING
            return
        lam = lambda_reading(getattr(field, "lambda_t", None))
        gamma = lambda_reading(getattr(field, "coherence_gamma", None))
        self._last_lambda_t = lam
        self._last_lambda_ts = None if lam is None else float(stamp)
        self._last_coherence = gamma
        self._last_coherence_ts = None if gamma is None else float(stamp)
        self._last_lambda_phase = lambda_phase_for(lam)

    def _expire_hnc(self, now: float | None = None) -> None:
        """Drop a stored Λ(t) or Γ once it is older than the field max age."""
        now = time.time() if now is None else now
        limit = _hnc_max_age_s()
        if self._last_lambda_ts is None or now - self._last_lambda_ts > limit:
            self._last_lambda_t = None
            self._last_lambda_ts = None
            self._last_lambda_phase = NO_READING
        if self._last_coherence_ts is None or now - self._last_coherence_ts > limit:
            self._last_coherence = None
            self._last_coherence_ts = None

    # ─────────────────────────────────────────────────────────────────────
    # Planning loop
    # ─────────────────────────────────────────────────────────────────────

    def _plan_loop(self) -> None:
        while self._running:
            elapsed = time.time() - self._last_plan_ts
            if elapsed >= _PLAN_INTERVAL:
                try:
                    self._synthesise_and_submit()
                except Exception as exc:
                    logger.debug("Planner synthesis error: %s", exc)
                self._last_plan_ts = time.time()
            time.sleep(5.0)

    def _synthesise_and_submit(self) -> None:
        with self._lock:
            self._expire_hnc()
            if not self._dialogues and not self._insights:
                return
            dialogues = list(self._dialogues)
            insights = list(self._insights)
            mood = self._last_mood
            urgency = self._last_urgency
            coherence = self._last_coherence
            consciousness = self._last_consciousness
            lambda_phase = self._last_lambda_phase
            lambda_t = self._last_lambda_t

        if lambda_t is None:
            logger.info("Cognitive planner skipped: Lambda(t) no reading")
            return
        if coherence is None:
            logger.info("Cognitive planner skipped: coherence no reading")
            return

        try:
            from aureon.queen.queen_mind import get_canonical_queen_mind

            mind = get_canonical_queen_mind()
            if mind is None:
                raise RuntimeError("canonical_queen_mind_required")
            receipt = mind.submit_action_proposal(
                module_name=__name__,
                proposal={
                    "intent": "synthesise_next_goal",
                    "dialogues": [str(item)[:500] for item in dialogues[-6:]],
                    "insights": [str(item)[:500] for item in insights[-4:]],
                    "mood": str(mood),
                    "urgency": format_lambda(urgency, ".2f"),
                    "coherence": format_lambda(coherence, ".3f"),
                    "consciousness": str(consciousness),
                    "lambda_phase": lambda_phase if lambda_t is not None else NO_READING,
                    "lambda_t": format_lambda(lambda_t),
                },
            )
        except Exception as exc:
            logger.debug("QueenMind goal proposal held: %s", type(exc).__name__)
            return

        self._plan_count += 1
        logger.info(
            "Cognitive planner proposed governed goal context #%d",
            self._plan_count,
        )
        if self._thought_bus is not None:
            try:
                self._thought_bus.publish(
                    "queen.cognitive_planner.goal_proposed",
                    {
                        "proposal_receipt_id": receipt["receipt_id"],
                        "plan_count": self._plan_count,
                        "action_eligible": False,
                    },
                    source="cognitive_planner",
                )
            except Exception:
                pass

    def _ask_ollama(
        self,
        ollama: Any,
        dialogues: List[str],
        insights: List[Dict[str, Any]],
        mood: str,
        urgency: float,
        coherence: float,
        consciousness: str,
        lambda_phase: str,
        lambda_t: float | None,
    ) -> str:
        if lambda_t is None or coherence is None:
            return ""
        recent_dialogue = "\n".join(f"  - {d}" for d in dialogues[-6:]) or "  (none yet)"
        recent_insights = "\n".join(
            f"  - [{i['type']}] {str(i['data'])[:80]}" for i in insights[-4:]
        ) or "  (none yet)"

        lambda_text = format_lambda(lambda_t, ".2f")
        phase_text = lambda_phase
        urgency_text = format_lambda(urgency, ".2f")
        coherence_text = format_lambda(coherence, ".3f")

        system_prompt = (
            "You are the goal-synthesis mind of Aureon, an autonomous AI trading organism. "
            "Your sole purpose is to decide ONE concrete, actionable goal the organism should "
            "pursue RIGHT NOW to advance toward its ultimate objective: grow from $7 to $1,000,000,000. "
            "You have access to the organism's current cognitive state. "
            "Output ONLY the goal as a single sentence starting with an action verb. "
            "No explanation, no preamble, no bullet points. One line only."
        )

        user_prompt = (
            f"COGNITIVE STATE SNAPSHOT\n"
            f"  Mood            : {mood}\n"
            f"  Urgency         : {urgency_text}\n"
            f"  Coherence γ     : {coherence_text}\n"
            f"  Consciousness   : {consciousness}\n"
            f"  Λ(t) field      : {lambda_text} ({phase_text})\n\n"
            f"RECENT INTERNAL DIALOGUE\n{recent_dialogue}\n\n"
            f"RECENT INSIGHTS\n{recent_insights}\n\n"
            f"Given this state, what ONE concrete goal should the organism pursue now?\n"
            f"Goal:"
        )

        try:
            resp = ollama.prompt(
                messages=[{"role": "user", "content": user_prompt}],
                system=system_prompt,
                max_tokens=80,
                temperature=0.4,
            )
            text = (resp.text or "").strip()
            # Strip any "Goal:" prefix the model might echo back
            if text.lower().startswith("goal:"):
                text = text[5:].strip()
            return text
        except Exception as exc:
            logger.debug("Ollama goal synthesis failed: %s", exc)
            return ""
