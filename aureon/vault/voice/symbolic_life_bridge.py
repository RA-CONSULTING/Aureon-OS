"""
SymbolicLifeBridge — make the persona layer feed the Λ engine
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The Auris Conjecture defines five criteria for symbolic life, and the
existing ``aureon/core/aureon_lambda_engine.py`` already computes them
on every ``step()``:

    ac_self_organization    — low variance in recent Λ history
    ac_memory_persistence   — history depth × lattice density
    ac_energy_stability     — 1 - |observer| (Ψ_max regulation)
    ac_adaptive_recursion   — |Δψ| over the last few samples
    ac_meaning_propagation  — coherence_phi × coherence_gamma

    symbolic_life_score     — weighted blend of the five, published on
                              the vault as ``current_symbolic_life_score``

This bridge connects everything I've added (PersonaVacuum, PersonaActuator,
AffinityChorus, LifeContext, OpportunityScanner, PhiBridgeMesh) to the Λ
engine: each subsystem event becomes a ``SubsystemReading`` so the
engine can see what the persona layer is doing. When the bridge pulses,
the five pillars move, ``symbolic_life_score`` updates, and the entity
has a live reading of its own aliveness.

Without this bridge the two halves of the codebase sit silent next to
each other. With it, the persona layer BECOMES the Λ substrate.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("aureon.vault.voice.symbolic_life_bridge")

SYMBOLIC_LIFE_RELEASE_HOLD = (
    "symbolic_life_bridge_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# Rolling observation buffer
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class _Rolling:
    """Tiny fixed-horizon counters for one kind of event."""

    window: int = 64
    events: Deque[float] = field(default_factory=lambda: deque(maxlen=64))

    def bump(self, weight: float = 1.0) -> None:
        self.events.append(max(0.0, float(weight)))

    def count(self) -> int:
        return len(self.events)

    def density(self, horizon: int = 64) -> float:
        """Normalised event density in [0, 1] over the recent horizon."""
        if horizon <= 0:
            return 0.0
        return min(1.0, self.count() / float(horizon))

    def mean(self) -> float:
        if not self.events:
            return 0.0
        return sum(self.events) / len(self.events)


# ─────────────────────────────────────────────────────────────────────────────
# Bridge
# ─────────────────────────────────────────────────────────────────────────────


class SymbolicLifeBridge:
    """Listens to the persona layer, drives the Λ engine, publishes the
    resulting Auris Conjecture pillar scores on the bus.

    Usage:
        bridge = SymbolicLifeBridge(thought_bus=bus, vault=vault)
        bridge.start()                   # subscribes to bus topics
        ...
        bridge.pulse()                   # one Λ step
        bridge.last_state.symbolic_life_score   # current reading
    """

    # Subsystem names we translate events into. These are intentionally
    # different from the Auris nodes so the Λ engine can average across
    # a wider set of signals.
    SUBSYSTEMS = (
        "persona_collapse",
        "chorus_coherence",
        "vault_memory",
        "actuator_pulse",
        "goal_commitment",
        "life_resonance",
        "mesh_unity",
        "goal_lighthouse",   # 5.1 — goal-echo health (completion_rate - orphan_rate)
    )

    # Topics the bridge subscribes to.
    TOPICS = (
        "persona.collapse",
        "persona.thought",
        "goal.submit.request",
        "goal.echo.summary",
        "goal.echo.orphaned",
        "life.event",
        "bridge.peer.state",
        "conversation.turn",
        "conversation.ambient",
    )

    def __init__(
        self,
        *,
        thought_bus: Any = None,
        vault: Any = None,
        lambda_engine: Any = None,
        interval_s: Optional[float] = None,
        volatility: float = 0.05,
        horizon: int = 32,
    ):
        self.thought_bus = thought_bus
        self.vault = vault
        self.interval_s = float(interval_s) if interval_s else None
        self.volatility = float(volatility)
        self.horizon = int(horizon)

        # Keep construction inert. The historical default engine/import path
        # remains below the release HOLD for compatibility inspection only.
        self._lambda_engine = lambda_engine
        self._SubsystemReading = None

        self._lock = threading.RLock()
        self._rolling: Dict[str, _Rolling] = {
            name: _Rolling(window=self.horizon) for name in self.SUBSYSTEMS
        }
        self._winner_buffer: Deque[str] = deque(maxlen=self.horizon)
        self._hash_buffer: Deque[str] = deque(maxlen=256)
        # Most recent goal.echo.summary — its completion_rate minus
        # orphan_rate is the lighthouse health signal (4.3/5.1 wiring).
        self._latest_goal_summary: Dict[str, Any] = {}
        self._subscribed = False

        self._last_state: Any = None
        self._last_pulse_ts: float = 0.0
        self._pulse_count: int = 0

        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ─── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        """Subscribe to bus topics. Optionally start the background pulse thread."""
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        if self._subscribed:
            return
        if self.thought_bus is None:
            logger.debug("SymbolicLifeBridge: no thought_bus; start() is a no-op")
            return
        try:
            self.thought_bus.subscribe("persona.collapse", self._on_persona_collapse)
            self.thought_bus.subscribe("persona.thought", self._on_persona_thought)
            self.thought_bus.subscribe("goal.submit.request", self._on_goal_request)
            self.thought_bus.subscribe("life.event", self._on_life_event)
            self.thought_bus.subscribe("bridge.peer.state", self._on_peer_state)
            self.thought_bus.subscribe("conversation.turn", self._on_conversation_turn)
            self.thought_bus.subscribe("conversation.ambient", self._on_conversation_turn)
            self.thought_bus.subscribe("goal.echo.summary", self._on_goal_echo_summary)
            self.thought_bus.subscribe("goal.echo.orphaned", self._on_goal_echo_orphaned)
            self._subscribed = True
        except Exception as e:
            logger.debug("SymbolicLifeBridge: subscribe failed: %s", e)
            return

        if self.interval_s:
            self._running = True
            self._thread = threading.Thread(
                target=self._loop, name="SymbolicLifeBridge", daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    # ─── subscribers ─────────────────────────────────────────────────────

    def _on_persona_collapse(self, thought: Any) -> None:
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        winner = str(payload.get("winner") or "")
        probs = payload.get("probabilities") or {}
        winning_prob = float(probs.get(winner, 0.0)) if isinstance(probs, dict) else 0.0
        # Higher winning probability = sharper chorus = more organised.
        with self._lock:
            self._rolling["persona_collapse"].bump(1.0)
            self._rolling["chorus_coherence"].bump(winning_prob)
            self._winner_buffer.append(winner)

    def _on_persona_thought(self, thought: Any) -> None:
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        with self._lock:
            self._rolling["actuator_pulse"].bump(0.5)
            # persona.thought sometimes carries the underlying VoiceStatement
            # fingerprint — use it as an LEV-node hash.
            fp = str(payload.get("vault_fingerprint") or "")
            if fp:
                self._hash_buffer.append(fp)

    def _on_goal_request(self, thought: Any) -> None:
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        urgency = float(payload.get("urgency") or 0.5)
        with self._lock:
            # Goals are commitments — they move adaptive_recursion by driving ψ.
            self._rolling["goal_commitment"].bump(max(0.3, min(1.0, urgency)))
            self._rolling["actuator_pulse"].bump(1.0)

    def _on_life_event(self, thought: Any) -> None:
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        status = str(payload.get("status") or "active")
        # Only active events radiate intent worth propagating.
        weight = 1.0 if status == "active" else 0.2
        with self._lock:
            self._rolling["life_resonance"].bump(weight)

    def _on_peer_state(self, thought: Any) -> None:
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        # Mesh heartbeat — every exchange with a peer is a lattice link.
        with self._lock:
            self._rolling["mesh_unity"].bump(0.8)

    def _on_conversation_turn(self, thought: Any) -> None:
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        with self._lock:
            self._rolling["vault_memory"].bump(1.0)
            self._rolling["actuator_pulse"].bump(0.4)
            if payload.get("question"):
                # Operator engagement lights meaning propagation too.
                self._rolling["life_resonance"].bump(0.6)

    def _on_goal_echo_summary(self, thought: Any) -> None:
        """The TemporalCausalityLaw pulses this every τ. Convert it into
        a lighthouse-health signal in [0, 1]: completion_rate minus
        orphan_rate, clamped. A closed causal line lifts it; a broken
        lighthouse pulls it toward zero."""
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        payload = getattr(thought, "payload", {}) or {}
        if not isinstance(payload, dict):
            return
        try:
            completion = float(payload.get("completion_rate", 0.0) or 0.0)
            orphan = float(payload.get("orphan_rate", 0.0) or 0.0)
        except (TypeError, ValueError):
            return
        health = max(0.0, min(1.0, completion - orphan + 0.5))
        with self._lock:
            self._latest_goal_summary = dict(payload)
            self._rolling["goal_lighthouse"].bump(health)

    def _on_goal_echo_orphaned(self, thought: Any) -> None:
        """An orphaned goal is a broken lighthouse — register it as a
        zero contribution to goal_lighthouse so the rolling mean drops."""
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        with self._lock:
            self._rolling["goal_lighthouse"].bump(0.0)

    # ─── Λ engine pulse ──────────────────────────────────────────────────

    def _build_readings(self) -> List[Any]:
        """Translate rolling counters into SubsystemReading objects."""
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        horizon = float(self.horizon)
        with self._lock:
            readings = []
            for name in self.SUBSYSTEMS:
                roll = self._rolling[name]
                density = roll.density(horizon)
                confidence = min(1.0, roll.count() / max(1.0, horizon / 2.0))
                # State strings give interpretability without affecting math.
                if density >= 0.7:
                    state = "alive"
                elif density >= 0.3:
                    state = "active"
                elif density > 0.0:
                    state = "stirring"
                else:
                    state = "dormant"
                readings.append(self._SubsystemReading(
                    name=name, value=density, confidence=confidence, state=state,
                ))

            # Winner coherence — if the same persona dominates a window, that
            # IS self-organization manifested. Boost the persona_collapse
            # reading when the winner is stable; dampen when winners thrash.
            if len(self._winner_buffer) >= 3:
                most = Counter(self._winner_buffer).most_common(1)[0][1]
                stability = most / len(self._winner_buffer)
                # Re-shape persona_collapse value by the stability.
                for r in readings:
                    if r.name == "persona_collapse":
                        r.value = min(1.0, (r.value + stability) / 2.0)
                        r.confidence = min(1.0, r.confidence + 0.2)
                        r.state = "unified" if stability > 0.5 else r.state

        return readings

    def pulse(self) -> Optional[Any]:
        """One Λ heartbeat — translate the rolling state into readings,
        step the Λ engine, publish the resulting pillars, return the state.
        """
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        if self._lambda_engine is None:
            return None
        readings = self._build_readings()
        try:
            state = self._lambda_engine.step(
                readings=readings,
                volatility=self.volatility,
                vault=self.vault,
            )
        except Exception as e:
            logger.debug("SymbolicLifeBridge: Λ step failed: %s", e)
            return None
        self._last_state = state
        self._last_pulse_ts = time.time()
        self._pulse_count += 1
        self._publish_pulse(state, readings)
        return state

    def _publish_pulse(self, state: Any, readings: List[Any]) -> None:
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        if self.thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        payload = self._state_to_payload(state, readings)
        try:
            if Thought is not None:
                self.thought_bus.publish(Thought(
                    source="symbolic_life_bridge",
                    topic="symbolic.life.pulse",
                    payload=payload,
                ))
            else:
                self.thought_bus.publish(
                    topic="symbolic.life.pulse",
                    payload=payload,
                    source="symbolic_life_bridge",
                )
        except Exception as e:
            logger.debug("SymbolicLifeBridge: publish failed: %s", e)

    @staticmethod
    def _state_to_payload(state: Any, readings: List[Any]) -> Dict[str, Any]:
        def _get(name: str) -> Any:
            return getattr(state, name, None)
        return {
            "lambda_t": _get("lambda_t"),
            "consciousness_psi": _get("consciousness_psi"),
            "consciousness_level": _get("consciousness_level"),
            "coherence_gamma": _get("coherence_gamma"),
            "coherence_phi": _get("coherence_phi"),
            "symbolic_life_score": _get("symbolic_life_score"),
            "ac_self_organization": _get("ac_self_organization"),
            "ac_memory_persistence": _get("ac_memory_persistence"),
            "ac_energy_stability": _get("ac_energy_stability"),
            "ac_adaptive_recursion": _get("ac_adaptive_recursion"),
            "ac_meaning_propagation": _get("ac_meaning_propagation"),
            "readings": [
                {"name": r.name, "value": round(r.value, 4),
                 "confidence": round(r.confidence, 4), "state": r.state}
                for r in readings
            ],
            "pulse_ts": time.time(),
        }

    # ─── loop ────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        while self._running:
            try:
                self.pulse()
            except Exception as e:
                logger.debug("SymbolicLifeBridge: pulse loop error: %s", e)
            time.sleep(float(self.interval_s or 1.0))

    # ─── introspection ───────────────────────────────────────────────────

    @property
    def last_state(self) -> Any:
        return self._last_state

    @property
    def pulse_count(self) -> int:
        return self._pulse_count

    def rolling_summary(self) -> Dict[str, Dict[str, float]]:
        with self._lock:
            return {
                name: {
                    "count": float(roll.count()),
                    "density": roll.density(self.horizon),
                    "mean": roll.mean(),
                }
                for name, roll in self._rolling.items()
            }

    # ─── helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def _build_lambda_engine() -> Any:
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        try:
            from aureon.core.aureon_lambda_engine import LambdaEngine
            return LambdaEngine()
        except Exception as e:
            logger.debug("SymbolicLifeBridge: LambdaEngine unavailable: %s", e)
            return None

    @staticmethod
    def _import_reading_cls() -> Any:
        raise RuntimeError(SYMBOLIC_LIFE_RELEASE_HOLD)
        try:
            from aureon.core.aureon_lambda_engine import SubsystemReading
            return SubsystemReading
        except Exception:
            # Fallback — simple object with the expected attrs. Lets the
            # bridge run in environments where LambdaEngine isn't present
            # (the Λ step will just do nothing).
            class _Reading:
                def __init__(self, name, value, confidence, state):
                    self.name = name
                    self.value = value
                    self.confidence = confidence
                    self.state = state
            return _Reading


__all__ = ["SYMBOLIC_LIFE_RELEASE_HOLD", "SymbolicLifeBridge"]
