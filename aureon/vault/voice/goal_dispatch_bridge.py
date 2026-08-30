"""
GoalDispatchBridge — goal.submit.request → Queen's conscience → engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The persona layer publishes ``goal.submit.request`` whenever a facet
proposes a goal. The TemporalCausalityLaw already enforces the
β Λ(t-τ) invariant over those goals, but until now nothing was picking
them up for execution. This bridge closes that gap.

Flow for every ``goal.submit.request``:

  1. Dedup by goal_id so the same request can't dispatch twice.
  2. Pull the current substrate state (SLS from vault / bus pulse) and
     hand it to QueenConscience.ask_why(goal_text, context).
  3. If the conscience returns VETO — publish ``goal.abandoned`` with
     the HNC substrate-coherence reason. Engine is not called.
     (This is the same 4th-pass veto the white paper describes at the
     trading layer, now applied to the goal layer.)
  4. Otherwise dispatch ``GoalExecutionEngine.submit_goal(text)`` on a
     daemon thread (submit_goal is blocking) so the bus stays
     responsive.
  5. The engine already publishes ``goal.submitted`` / ``goal.progress``
     / ``goal.completed`` which the TemporalCausalityLaw listens on —
     the lifecycle telemetry is continuous without any extra wiring.
  6. If the engine raises, publish ``goal.abandoned`` with the
     exception message so the causal line closes cleanly.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("aureon.vault.voice.goal_dispatch_bridge")


class GoalDispatchBridge:
    """Subscribes to goal.submit.request and dispatches each one through
    the conscience and into the GoalExecutionEngine."""

    def __init__(
        self,
        *,
        thought_bus: Any = None,
        conscience: Any = None,
        goal_engine: Any = None,
        vault: Any = None,
    ):
        self.thought_bus = thought_bus
        self.conscience = conscience
        self.goal_engine = goal_engine
        self.vault = vault

        self._lock = threading.RLock()
        self._dispatched: Set[str] = set()
        self._subscribed = False
        self._dispatch_count = 0
        self._veto_count = 0
        self._abandon_count = 0
        self._run_in_thread = True  # toggle off for deterministic tests

    def start(self) -> None:
        if self._subscribed or self.thought_bus is None:
            return
        try:
            self.thought_bus.subscribe("goal.submit.request", self._on_submit_request)
            self._subscribed = True
        except Exception as e:
            logger.debug("GoalDispatchBridge: subscribe failed: %s", e)

    # ─── intake ──────────────────────────────────────────────────────────

    def _on_submit_request(self, thought: Any) -> None:
        payload = getattr(thought, "payload", {}) or {}
        if not isinstance(payload, dict):
            return
        goal_id = str(payload.get("goal_id") or "") or uuid.uuid4().hex[:10]
        # If the SkillExecutorBridge has already claimed this goal_id
        # (because the aligner fired before us and matched a pattern),
        # defer — the skill executor will run the chain AND publish the
        # terminal goal.completed / goal.abandoned. Running the engine
        # here too would cause double execution.
        try:
            from aureon.vault.voice._goal_claims import GoalClaims
            if GoalClaims.is_claimed(goal_id):
                return
        except Exception:
            pass
        with self._lock:
            if goal_id in self._dispatched:
                return
            self._dispatched.add(goal_id)
        text = str(payload.get("text") or "").strip()
        if not text:
            self._publish_abandoned(goal_id, "no goal text in submit.request")
            return
        context = self._build_context(payload)
        # The conscience's ask_why is fast (no I/O); the engine's
        # submit_goal is blocking and can run long — so we gate here and
        # fork into the engine from the gate.
        self._dispatch(goal_id, text, context, payload)

    def _build_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Conscience context. We surface the SLS explicitly so the
        substrate-coherence check doesn't depend on the conscience
        having the vault attached."""
        ctx: Dict[str, Any] = {
            "persona": str(payload.get("proposed_by_persona") or ""),
            "goal_id": str(payload.get("goal_id") or ""),
            "urgency": float(payload.get("urgency") or 0.5),
        }
        sls = self._current_sls()
        if sls is not None:
            ctx["symbolic_life_score"] = sls
        # Merge any risk / leverage / size the persona passed in so the
        # conscience's _is_risky_action classification sees them.
        params = payload.get("parameters") or {}
        if isinstance(params, dict):
            for k in ("risk", "leverage", "size", "symbol", "profit_potential",
                      "confidence"):
                if k in params:
                    ctx[k] = params[k]
        return ctx

    def _current_sls(self) -> Optional[float]:
        if self.vault is not None:
            sls = getattr(self.vault, "current_symbolic_life_score", None)
            if sls is not None:
                try:
                    return max(0.0, min(1.0, float(sls)))
                except (TypeError, ValueError):
                    pass
        return None

    # ─── dispatch ────────────────────────────────────────────────────────

    def _dispatch(
        self,
        goal_id: str,
        text: str,
        context: Dict[str, Any],
        full_payload: Dict[str, Any],
    ) -> None:
        """Run the conscience gate, then hand off to the engine.

        Always non-blocking — the engine call runs on a daemon thread so
        the bus handler returns immediately.
        """
        # Conscience gate (synchronous; it's in-memory).
        verdict_label = ""
        try:
            if self.conscience is not None and hasattr(self.conscience, "ask_why"):
                whisper = self.conscience.ask_why(text, context)
                verdict_label = self._verdict_label(whisper)
                if verdict_label == "VETO":
                    self._veto_count += 1
                    self._publish_abandoned(
                        goal_id,
                        reason=self._whisper_reason(whisper)
                                or "substrate_coherence: conscience vetoed",
                        text=text,
                        persona=context.get("persona", ""),
                    )
                    return
        except Exception as e:
            logger.debug("GoalDispatchBridge: conscience ask_why failed: %s", e)
            # Soft-fail: the conscience is advisory. If it's broken, we
            # continue the dispatch — the TemporalCausalityLaw will still
            # see the downstream state.

        # A goal.submitted event is an engine acknowledgement. The bridge
        # must not invent one when no engine is wired, or use local time as
        # a provider timestamp. The original request stays open so the
        # lighthouse can orphan it honestly.
        if self.goal_engine is None:
            self._publish_dispatch_unavailable(goal_id, text)
            return

        if self._run_in_thread:
            threading.Thread(
                target=self._run_engine_submit,
                args=(goal_id, text),
                name=f"GoalDispatch-{goal_id}",
                daemon=True,
            ).start()
        else:
            # Test mode — run inline for deterministic assertions.
            self._run_engine_submit(goal_id, text)

    def _run_engine_submit(self, goal_id: str, text: str) -> None:
        """Thread target. Calls the blocking engine and converts any
        exception into a goal.abandoned event so the lighthouse closes."""
        try:
            self.goal_engine.submit_goal(text)
            self._dispatch_count += 1
        except Exception as e:
            self._publish_abandoned(goal_id, reason=f"engine error: {e}",
                                    text=text)

    # ─── publishers ──────────────────────────────────────────────────────

    def _publish_abandoned(
        self,
        goal_id: str,
        reason: str,
        text: str = "",
        persona: str = "",
    ) -> None:
        self._abandon_count += 1
        payload = {
            "goal_id": goal_id,
            "reason": reason,
            "text": text,
            "proposed_by_persona": persona,
            "ts": time.time(),
        }
        self._publish("goal.abandoned", payload)

    def _publish_dispatch_unavailable(self, goal_id: str, text: str) -> None:
        """Record the no-engine condition without impersonating an acknowledgement."""
        payload = {
            "goal_id": goal_id,
            "text": text,
            "source": "goal_dispatch_bridge",
            "source_id": "goal_dispatch_bridge",
            "request_id": goal_id,
            "receipt_id": None,
            "has_engine": False,
            "received_at": time.time(),
            "source_timestamp": None,
            "truth_status": "no_data",
            "generated_values": False,
            "action_enabled": False,
            "accounting_enabled": False,
            "learning_enabled": False,
        }
        self._publish("goal.dispatch.unavailable", payload)

    def _publish(self, topic: str, payload: Dict[str, Any]) -> None:
        if self.thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        try:
            if Thought is not None:
                self.thought_bus.publish(Thought(
                    source="goal_dispatch_bridge",
                    topic=topic,
                    payload=payload,
                ))
            else:
                self.thought_bus.publish(topic=topic, payload=payload,
                                         source="goal_dispatch_bridge")
        except Exception as e:
            logger.debug("GoalDispatchBridge: publish %s failed: %s", topic, e)

    # ─── conscience helpers ──────────────────────────────────────────────

    @staticmethod
    def _verdict_label(whisper: Any) -> str:
        """Return a stable label regardless of the ConscienceVerdict enum
        implementation (value=auto()/str/etc.)."""
        if whisper is None:
            return ""
        v = getattr(whisper, "verdict", None)
        if v is None:
            return ""
        name = getattr(v, "name", None)
        if isinstance(name, str):
            return name.upper()
        return str(v).rsplit(".", 1)[-1].upper()

    @staticmethod
    def _whisper_reason(whisper: Any) -> str:
        if whisper is None:
            return ""
        msg = getattr(whisper, "message", "") or ""
        why = getattr(whisper, "why_it_matters", "") or ""
        if msg and why:
            return f"{msg} | {why}"
        return msg or why

    # ─── introspection ───────────────────────────────────────────────────

    def stats(self) -> Dict[str, Any]:
        return {
            "dispatched": self._dispatch_count,
            "vetoed": self._veto_count,
            "abandoned": self._abandon_count,
            "has_engine": self.goal_engine is not None,
            "has_conscience": self.conscience is not None,
            "subscribed": self._subscribed,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


_singleton: Optional[GoalDispatchBridge] = None
_singleton_lock = threading.Lock()


def get_goal_dispatch_bridge(
    thought_bus: Any = None,
    conscience: Any = None,
    goal_engine: Any = None,
    vault: Any = None,
) -> GoalDispatchBridge:
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = GoalDispatchBridge(
                thought_bus=thought_bus,
                conscience=conscience,
                goal_engine=goal_engine,
                vault=vault,
            )
            _singleton.start()
        else:
            if thought_bus is not None and _singleton.thought_bus is None:
                _singleton.thought_bus = thought_bus
                _singleton.start()
            if conscience is not None and _singleton.conscience is None:
                _singleton.conscience = conscience
            if goal_engine is not None and _singleton.goal_engine is None:
                _singleton.goal_engine = goal_engine
            if vault is not None and _singleton.vault is None:
                _singleton.vault = vault
        return _singleton


def reset_goal_dispatch_bridge() -> None:
    global _singleton
    with _singleton_lock:
        _singleton = None


__all__ = [
    "GoalDispatchBridge",
    "get_goal_dispatch_bridge",
    "reset_goal_dispatch_bridge",
]
