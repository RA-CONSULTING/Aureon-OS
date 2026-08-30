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
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger("aureon.queen.cognitive_action_planner")

PHI = (1.0 + math.sqrt(5.0)) / 2.0
_PLAN_INTERVAL = PHI * PHI * 60.0   # ≈ 157s between autonomous goal submissions


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
        self._last_urgency: float = 0.0
        self._last_coherence: float = 0.0
        self._last_consciousness: str = "DORMANT"
        self._last_lambda_phase: str = "TRANSITION"
        self._last_lambda_t: float = 0.0

        self._last_plan_ts: float = 0.0
        self._plan_count: int = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None
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
                    self._last_mood = payload.get("mood", self._last_mood)
                    self._last_urgency = float(payload.get("urgency", self._last_urgency))
                    self._last_coherence = float(payload.get("coherence", self._last_coherence))
                    self._last_consciousness = payload.get("consciousness", self._last_consciousness)
        elif subtopic in ("insight", "dream") or topic.startswith("queen.metacognition.insight"):
            with self._lock:
                self._insights.append({"type": subtopic, "data": payload, "ts": time.time()})

    def _on_source_law(self, topic: str, payload: Dict[str, Any], **_) -> None:
        with self._lock:
            self._last_coherence = float(payload.get("coherence_gamma", self._last_coherence))
            self._last_lambda_t = float(payload.get("lambda_t", self._last_lambda_t))
            lam = self._last_lambda_t
            if lam < 30:
                self._last_lambda_phase = "TRANSITION"
            elif lam < 65:
                self._last_lambda_phase = "COHERENCE"
            else:
                self._last_lambda_phase = "UNITY"

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
            dialogues = list(self._dialogues)
            insights = list(self._insights)
            mood = self._last_mood
            urgency = self._last_urgency
            coherence = self._last_coherence
            consciousness = self._last_consciousness
            lambda_phase = self._last_lambda_phase
            lambda_t = self._last_lambda_t

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
                    "urgency": str(urgency),
                    "coherence": str(coherence),
                    "consciousness": str(consciousness),
                    "lambda_phase": str(lambda_phase),
                    "lambda_t": str(lambda_t),
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
        lambda_t: float,
    ) -> str:
        recent_dialogue = "\n".join(f"  - {d}" for d in dialogues[-6:]) or "  (none yet)"
        recent_insights = "\n".join(
            f"  - [{i['type']}] {str(i['data'])[:80]}" for i in insights[-4:]
        ) or "  (none yet)"

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
            f"  Urgency         : {urgency:.2f}\n"
            f"  Coherence γ     : {coherence:.3f}\n"
            f"  Consciousness   : {consciousness}\n"
            f"  Λ(t) field      : {lambda_t:.2f} ({lambda_phase})\n\n"
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
