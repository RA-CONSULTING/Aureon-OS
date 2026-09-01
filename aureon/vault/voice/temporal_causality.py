"""
TemporalCausalityLaw — the β Λ(t - τ) lighthouse over goal lifecycles
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The HNC Master Formula is

    Λ(t) = Σ wᵢ sin(2πfᵢt + φᵢ) + α tanh(g Λ_Δt(t)) + β Λ(t - τ)

The third term — β Λ(t - τ) — is the memory, the "lighthouse protocol"
described in docs/HNC_UNIFIED_WHITE_PAPER.md: *"the delayed feedback
loop, which generates a characteristic spectral comb structure near
multiples of 1/τ. This signature [..] allows for the diagnostic
identification of historical causal constraints acting upon the
present state."*

Applied to goals, it says: a goal set at t₀ must NOT silently vanish.
At every t₀ + nτ the echo of that goal is a causal constraint on the
present state. The system is bound to carry the echo forward until the
goal either completes (causal line closed) or is explicitly abandoned
(causal line terminated with audit). A goal that just fades is a
broken lighthouse — and the paper says β > 1.1 is the "stability
cliff" where broken feedback produces chaotic dynamics.

This module enforces the HNC invariant. It is NOT a work queue. It is
the lawful echo tracker for every goal the persona layer commits to.

Lifecycle:

    PROPOSED    goal.submit.request seen; nothing has acknowledged it yet.
    ACKNOWLEDGED a GoalExecutionEngine (or any consumer) picked it up.
    IN_PROGRESS  progress events have arrived; the goal is being executed.
    COMPLETED    the goal finished; the causal line is closed.
    ABANDONED    explicitly abandoned with a reason; line terminated.
    ORPHANED     not acknowledged within the τ budget — the lighthouse
                 broke. A warning echo goes out so the Queen / operator
                 can respond.

Wiring:

    subscribes to:
        goal.submit.request           (persona layer via PersonaActuator)
        goal.submitted                (GoalExecutionEngine intake echo)
        goal.progress                 (engine step events)
        goal.completed                (engine terminal echo)
        goal.abandoned                (explicit abandonment)

    publishes:
        goal.echo                     (every lifecycle transition)
        goal.echo.summary             (every τ pulse; aggregate health
                                       for SymbolicLifeBridge to ingest)
        goal.echo.orphaned            (a goal crossed the τ budget)

Every transition also lands as a ``goal.echo`` card on the vault so the
mesh gossips it, the Obsidian mirror writes it, and the five Auris
Conjecture pillars feel it.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aureon.vault.voice.temporal_causality")

TEMPORAL_CAUSALITY_RELEASE_HOLD = (
    "temporal_causality_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# Lifecycle + data
# ─────────────────────────────────────────────────────────────────────────────


class GoalState(str, Enum):
    PROPOSED = "PROPOSED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    ORPHANED = "ORPHANED"


_TERMINAL = (GoalState.COMPLETED, GoalState.ABANDONED, GoalState.ORPHANED)


@dataclass
class GoalEcho:
    """One goal's full temporal trace. The β Λ(t-τ) signal of the echo
    is the sequence of lifecycle states this object carries forward
    until the causal line closes."""

    goal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    text: str = ""
    proposed_by_persona: str = ""
    urgency: float = 0.5
    parameters: Dict[str, Any] = field(default_factory=dict)
    state: GoalState = GoalState.PROPOSED
    lifecycle_tau: int = 0                      # τ ticks since proposal
    transitions: List[Dict[str, Any]] = field(default_factory=list)
    progress_pct: float = 0.0
    result_summary: str = ""
    abandoned_reason: str = ""
    acknowledged_by: str = ""
    ts_proposed: float = field(default_factory=time.time)
    ts_last_update: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "text": self.text,
            "proposed_by_persona": self.proposed_by_persona,
            "urgency": self.urgency,
            "parameters": dict(self.parameters),
            "state": self.state.value,
            "lifecycle_tau": self.lifecycle_tau,
            "progress_pct": self.progress_pct,
            "transitions": list(self.transitions),
            "result_summary": self.result_summary,
            "abandoned_reason": self.abandoned_reason,
            "acknowledged_by": self.acknowledged_by,
            "ts_proposed": self.ts_proposed,
            "ts_last_update": self.ts_last_update,
        }

    def is_terminal(self) -> bool:
        return self.state in _TERMINAL


# ─────────────────────────────────────────────────────────────────────────────
# The law itself
# ─────────────────────────────────────────────────────────────────────────────


class TemporalCausalityLaw:
    """Enforces the HNC lighthouse protocol over goal lifecycles.

    Wire it once; it listens to the bus and carries every goal's echo
    forward until the causal line closes. Between pulses it is silent;
    on pulse() it advances every active goal's lifecycle_tau, orphans
    stale PROPOSED goals, and emits the aggregate summary that the
    SymbolicLifeBridge folds into the five Auris Conjecture pillars.
    """

    # Default τ budgets. φ-aligned / Fibonacci defaults (3, 144). Override
    # per-instance via the constructor kwargs if your cadence differs.
    DEFAULT_ACK_BUDGET_TAU: int = 3
    DEFAULT_COMPLETE_BUDGET_TAU: int = 144

    INBOUND_TOPICS = (
        "goal.submit.request",
        "goal.submitted",
        "goal.progress",
        "goal.completed",
        "goal.abandoned",
    )

    def __init__(
        self,
        *,
        thought_bus: Any = None,
        vault: Any = None,
        ack_budget_tau: Optional[int] = None,
        complete_budget_tau: Optional[int] = None,
    ):
        self.thought_bus = thought_bus
        self.vault = vault
        self.ack_budget_tau = max(1, int(
            ack_budget_tau if ack_budget_tau is not None
            else self.DEFAULT_ACK_BUDGET_TAU
        ))
        self.complete_budget_tau = max(1, int(
            complete_budget_tau if complete_budget_tau is not None
            else self.DEFAULT_COMPLETE_BUDGET_TAU
        ))

        self._lock = threading.RLock()
        self._goals: Dict[str, GoalEcho] = {}
        self._pulse_count: int = 0
        self._subscribed: bool = False

    # ─── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to bus topics. Safe to call twice."""
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        if self._subscribed or self.thought_bus is None:
            return
        try:
            self.thought_bus.subscribe("goal.submit.request", self._on_submit_request)
            self.thought_bus.subscribe("goal.submitted", self._on_submitted)
            self.thought_bus.subscribe("goal.progress", self._on_progress)
            self.thought_bus.subscribe("goal.completed", self._on_completed)
            self.thought_bus.subscribe("goal.abandoned", self._on_abandoned)
            self._subscribed = True
        except Exception as e:
            logger.debug("TemporalCausalityLaw: subscribe failed: %s", e)

    # ─── inbound subscribers ─────────────────────────────────────────────

    def _on_submit_request(self, thought: Any) -> None:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        if not isinstance(payload, dict):
            return
        self.track(payload)

    def _on_submitted(self, thought: Any) -> None:
        """The existing GoalExecutionEngine publishes goal.submitted when
        it accepts a goal via submit_goal(). Use it to auto-acknowledge."""
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        text = str(payload.get("text") or "")
        goal_id = str(payload.get("goal_id") or "")
        engine_id = str(payload.get("source") or "goal_execution_engine")
        if goal_id:
            self.acknowledge(goal_id, engine_id)
        elif text:
            # Match by text if the engine didn't echo our goal_id back.
            match = self._find_by_text(text)
            if match is not None:
                self.acknowledge(match.goal_id, engine_id)

    def _on_progress(self, thought: Any) -> None:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        goal_id = str(payload.get("goal_id") or "")
        pct = payload.get("progress_pct")
        note = str(payload.get("note") or payload.get("step") or "")
        if not goal_id:
            return
        try:
            pct_f = float(pct) if pct is not None else None
        except (TypeError, ValueError):
            pct_f = None
        self.update_progress(goal_id, pct_f, note)

    def _on_completed(self, thought: Any) -> None:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        goal_id = str(payload.get("goal_id") or "")
        summary = str(payload.get("result_summary") or payload.get("summary") or "")
        if not goal_id:
            text = str(payload.get("text") or "")
            if text:
                m = self._find_by_text(text)
                goal_id = m.goal_id if m else ""
        if goal_id:
            self.complete(goal_id, summary)

    def _on_abandoned(self, thought: Any) -> None:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        goal_id = str(payload.get("goal_id") or "")
        reason = str(payload.get("reason") or payload.get("why") or "unspecified")
        if goal_id:
            self.abandon(goal_id, reason)

    # ─── API ─────────────────────────────────────────────────────────────

    def track(self, payload: Dict[str, Any]) -> GoalEcho:
        """Register a new goal from a goal.submit.request payload."""
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        with self._lock:
            goal_id = str(payload.get("goal_id") or "") or uuid.uuid4().hex[:10]
            if goal_id in self._goals:
                return self._goals[goal_id]
            echo = GoalEcho(
                goal_id=goal_id,
                text=str(payload.get("text") or ""),
                proposed_by_persona=str(payload.get("proposed_by_persona") or ""),
                urgency=float(payload.get("urgency") or 0.5),
                parameters=dict(payload.get("parameters") or {}),
                state=GoalState.PROPOSED,
            )
            self._record_transition(echo, GoalState.PROPOSED, "goal observed at t₀")
            self._goals[goal_id] = echo
        self._publish_echo(echo, "goal.echo")
        self._feed_vault(echo)
        return echo

    def acknowledge(self, goal_id: str, engine_id: str = "") -> Optional[GoalEcho]:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        with self._lock:
            echo = self._goals.get(goal_id)
            if echo is None or echo.is_terminal():
                return echo
            if echo.state == GoalState.ACKNOWLEDGED:
                return echo
            echo.acknowledged_by = str(engine_id)
            self._record_transition(echo, GoalState.ACKNOWLEDGED,
                                     f"picked up by {engine_id or 'consumer'}")
        self._publish_echo(echo, "goal.echo")
        self._feed_vault(echo)
        return echo

    def update_progress(
        self,
        goal_id: str,
        progress_pct: Optional[float] = None,
        note: str = "",
    ) -> Optional[GoalEcho]:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        with self._lock:
            echo = self._goals.get(goal_id)
            if echo is None or echo.is_terminal():
                return echo
            if progress_pct is not None:
                try:
                    echo.progress_pct = max(0.0, min(1.0, float(progress_pct)))
                except (TypeError, ValueError):
                    pass
            if echo.state in (GoalState.PROPOSED, GoalState.ACKNOWLEDGED):
                self._record_transition(echo, GoalState.IN_PROGRESS,
                                         note or "progress reported")
            else:
                echo.ts_last_update = time.time()
                echo.transitions.append({
                    "ts": echo.ts_last_update,
                    "lifecycle_tau": echo.lifecycle_tau,
                    "state": echo.state.value,
                    "note": note,
                    "progress_pct": echo.progress_pct,
                })
        self._publish_echo(echo, "goal.echo")
        self._feed_vault(echo)
        return echo

    def complete(self, goal_id: str, result_summary: str = "") -> Optional[GoalEcho]:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        with self._lock:
            echo = self._goals.get(goal_id)
            if echo is None or echo.is_terminal():
                return echo
            echo.result_summary = str(result_summary)
            echo.progress_pct = 1.0
            self._record_transition(echo, GoalState.COMPLETED,
                                     result_summary or "causal line closed")
        self._publish_echo(echo, "goal.echo")
        self._feed_vault(echo)
        return echo

    def abandon(self, goal_id: str, reason: str = "unspecified") -> Optional[GoalEcho]:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        with self._lock:
            echo = self._goals.get(goal_id)
            if echo is None or echo.is_terminal():
                return echo
            echo.abandoned_reason = str(reason)
            self._record_transition(echo, GoalState.ABANDONED,
                                     f"abandoned — {reason}")
        self._publish_echo(echo, "goal.echo")
        self._feed_vault(echo)
        return echo

    # ─── pulse (τ step) ──────────────────────────────────────────────────

    def pulse(self) -> Dict[str, Any]:
        """One τ step. Advance every active goal's lifecycle_tau; orphan
        stale PROPOSED goals; publish the aggregate summary so the
        SymbolicLifeBridge can ingest it into the five pillars.

        Returns the summary dict for callers that want to inspect it
        synchronously (tests, dashboards)."""
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        self._pulse_count += 1
        orphaned: List[GoalEcho] = []
        with self._lock:
            for echo in self._goals.values():
                if echo.is_terminal():
                    continue
                echo.lifecycle_tau += 1
                if (echo.state == GoalState.PROPOSED
                        and echo.lifecycle_tau >= self.ack_budget_tau):
                    self._record_transition(
                        echo, GoalState.ORPHANED,
                        f"no acknowledge within τ budget ({self.ack_budget_tau})",
                    )
                    orphaned.append(echo)
                elif (echo.state in (GoalState.ACKNOWLEDGED, GoalState.IN_PROGRESS)
                        and echo.lifecycle_tau >= self.complete_budget_tau):
                    self._record_transition(
                        echo, GoalState.ORPHANED,
                        f"no completion within τ budget ({self.complete_budget_tau})",
                    )
                    orphaned.append(echo)

        # Publish orphan echoes outside the lock
        for echo in orphaned:
            self._publish_echo(echo, "goal.echo")
            self._publish_echo(echo, "goal.echo.orphaned")
            self._feed_vault(echo)

        summary = self.summary()
        self._publish_summary(summary)
        return summary

    # ─── introspection ───────────────────────────────────────────────────

    def summary(self) -> Dict[str, Any]:
        with self._lock:
            counts = {s.value: 0 for s in GoalState}
            active_tau_sum = 0
            active_count = 0
            for echo in self._goals.values():
                counts[echo.state.value] += 1
                if not echo.is_terminal():
                    active_tau_sum += echo.lifecycle_tau
                    active_count += 1
            avg_tau = (active_tau_sum / active_count) if active_count else 0.0
            total = len(self._goals)
            terminal = sum(counts[s.value] for s in _TERMINAL)
            completion_rate = (counts[GoalState.COMPLETED.value] / terminal
                               if terminal else 0.0)
            orphan_rate = (counts[GoalState.ORPHANED.value] / terminal
                           if terminal else 0.0)
            return {
                "pulse": self._pulse_count,
                "ts": time.time(),
                "total_goals": total,
                "counts": counts,
                "active_count": active_count,
                "avg_active_lifecycle_tau": round(avg_tau, 3),
                "completion_rate": round(completion_rate, 3),
                "orphan_rate": round(orphan_rate, 3),
                "ack_budget_tau": self.ack_budget_tau,
                "complete_budget_tau": self.complete_budget_tau,
            }

    def get(self, goal_id: str) -> Optional[GoalEcho]:
        with self._lock:
            return self._goals.get(goal_id)

    def active(self) -> List[GoalEcho]:
        with self._lock:
            return [e for e in self._goals.values() if not e.is_terminal()]

    def all(self) -> List[GoalEcho]:
        with self._lock:
            return list(self._goals.values())

    # ─── helpers ─────────────────────────────────────────────────────────

    def _find_by_text(self, text: str) -> Optional[GoalEcho]:
        text_l = text.strip().lower()
        if not text_l:
            return None
        with self._lock:
            for echo in self._goals.values():
                if echo.text.strip().lower() == text_l and not echo.is_terminal():
                    return echo
        return None

    def _record_transition(
        self,
        echo: GoalEcho,
        new_state: GoalState,
        note: str,
    ) -> None:
        """Must be called under self._lock."""
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        ts = time.time()
        echo.state = new_state
        echo.ts_last_update = ts
        echo.transitions.append({
            "ts": ts,
            "lifecycle_tau": echo.lifecycle_tau,
            "state": new_state.value,
            "note": note,
            "progress_pct": echo.progress_pct,
        })

    # ─── bus publish ─────────────────────────────────────────────────────

    def _publish_echo(self, echo: GoalEcho, topic: str) -> None:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        if self.thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        payload = echo.to_dict()
        try:
            if Thought is not None:
                self.thought_bus.publish(Thought(
                    source="temporal_causality_law",
                    topic=topic,
                    payload=payload,
                ))
            else:
                self.thought_bus.publish(topic=topic, payload=payload,
                                         source="temporal_causality_law")
        except Exception as e:
            logger.debug("TemporalCausalityLaw: publish %s failed: %s", topic, e)

    def _publish_summary(self, summary: Dict[str, Any]) -> None:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        if self.thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        try:
            if Thought is not None:
                self.thought_bus.publish(Thought(
                    source="temporal_causality_law",
                    topic="goal.echo.summary",
                    payload=dict(summary),
                ))
            else:
                self.thought_bus.publish(topic="goal.echo.summary",
                                         payload=dict(summary),
                                         source="temporal_causality_law")
        except Exception as e:
            logger.debug("TemporalCausalityLaw: summary publish failed: %s", e)

    def _feed_vault(self, echo: GoalEcho) -> None:
        raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
        if self.vault is None or not hasattr(self.vault, "ingest"):
            return
        try:
            self.vault.ingest(topic="goal.echo", payload=echo.to_dict())
        except Exception as e:
            logger.debug("TemporalCausalityLaw: vault ingest failed: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


_singleton: Optional[TemporalCausalityLaw] = None
_singleton_lock = threading.Lock()


def get_temporal_causality_law(
    thought_bus: Any = None,
    vault: Any = None,
) -> TemporalCausalityLaw:
    raise RuntimeError(TEMPORAL_CAUSALITY_RELEASE_HOLD)
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = TemporalCausalityLaw(thought_bus=thought_bus, vault=vault)
            _singleton.start()
        else:
            if thought_bus is not None and _singleton.thought_bus is None:
                _singleton.thought_bus = thought_bus
                _singleton.start()
            if vault is not None and _singleton.vault is None:
                _singleton.vault = vault
        return _singleton


def reset_temporal_causality_law() -> None:
    global _singleton
    with _singleton_lock:
        _singleton = None


__all__ = [
    "TEMPORAL_CAUSALITY_RELEASE_HOLD",
    "GoalState",
    "GoalEcho",
    "TemporalCausalityLaw",
    "get_temporal_causality_law",
    "reset_temporal_causality_law",
]
