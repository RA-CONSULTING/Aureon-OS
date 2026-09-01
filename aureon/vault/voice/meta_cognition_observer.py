"""
MetaCognitionObserver — α tanh(g Λ_Δt(t)) made observable
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From the HNC Unified White Paper §Master Formula:

    Λ(t) = Σ wᵢ sin(2πfᵢt + φᵢ) + α tanh(g Λ_Δt(t)) + β Λ(t − τ)
                                   └────────┬────────┘
                                    observer term
                                    "the thickness of Now"

The observer term integrates the field over a finite temporal horizon.
This module operationalises it at the persona layer. For every
persona.collapse, a **window** of length ``window_s`` (default φ = 1.618s) is opened, every downstream
event inside that window is accumulated, and when the window closes a
``ReflectionCard`` is assembled:

    persona chose action X under state Y. The window saw effects Z.
    SLS moved from A to B. There are N resonating siblings to this
    event. Outcome: COMPLETED / ABANDONED / ORPHANED / SILENT.

The card is published on ``meta.reflection`` and written to the vault.
The Queen's existing ``queen_metacognition.py`` 5-W analyzer (WHAT /
WHY / WORKED / FAILED / NEXT) consumes it via a new
``ingest_external_reflection()`` entry point — one extension, no
rewrite.

Wiring reads across every new topic from stages 4.3–6.3:

    persona.collapse        (open a new window)
    persona.thought         (the uttered decision)
    queen.conscience.verdict (APPROVED / CONCERNED / VETO / …)
    goal.submit.request     (the proposed goal)
    goal.submitted          (engine accepted)
    goal.progress           (engine working)
    goal.completed          (causal line closed)
    goal.abandoned          (line terminated)
    goal.echo*              (TemporalCausalityLaw state transitions)
    symbolic.life.pulse     (SLS before + after)
    standing.wave.bond      (bond crossings within window)

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import logging
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("aureon.vault.voice.meta_cognition_observer")

PHI: float = (1.0 + math.sqrt(5.0)) / 2.0
META_COGNITION_RELEASE_HOLD = (
    "meta_cognition_observer_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# ReflectionCard
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ReflectionCard:
    reflection_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    collapse_ts: float = 0.0
    closed_ts: float = 0.0
    persona: str = ""
    state_cues: Dict[str, Any] = field(default_factory=dict)
    decision: str = "silence"         # "silence" | kind of action
    action_topic: str = ""
    downstream_effects: List[Dict[str, Any]] = field(default_factory=list)
    outcome: str = "SILENT"            # COMPLETED | ABANDONED | ORPHANED | SILENT
    sls_before: Optional[float] = None
    sls_after: Optional[float] = None
    sls_delta: float = 0.0
    bond_count: int = 0
    bond_strength: float = 0.0
    window_s: float = PHI
    lambda_delta_t: float = 0.0
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reflection_id": self.reflection_id,
            "collapse_ts": self.collapse_ts,
            "closed_ts": self.closed_ts,
            "persona": self.persona,
            "state_cues": dict(self.state_cues),
            "decision": self.decision,
            "action_topic": self.action_topic,
            "downstream_effects": list(self.downstream_effects),
            "outcome": self.outcome,
            "sls_before": self.sls_before,
            "sls_after": self.sls_after,
            "sls_delta": self.sls_delta,
            "bond_count": self.bond_count,
            "bond_strength": self.bond_strength,
            "window_s": self.window_s,
            "lambda_delta_t": self.lambda_delta_t,
            "reasoning": self.reasoning,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Window
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class _OpenWindow:
    card: ReflectionCard
    collapse_payload: Dict[str, Any]
    decision_persona: str
    sls_before: Optional[float]
    close_at: float
    events: List[Dict[str, Any]] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# MetaCognitionObserver
# ─────────────────────────────────────────────────────────────────────────────


class MetaCognitionObserver:
    """One open window per persona.collapse. Closed by timer. Produces a
    ReflectionCard per window."""

    DEFAULT_WINDOW_S: float = PHI

    WATCHED_TOPICS = (
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
        "symbolic.life.pulse",
        "standing.wave.bond",
    )

    def __init__(
        self,
        *,
        thought_bus: Any = None,
        vault: Any = None,
        hash_resonance_index: Any = None,
        queen_metacognition: Any = None,
        window_s: Optional[float] = None,
    ):
        self.thought_bus = thought_bus
        self.vault = vault
        self.hri = hash_resonance_index
        self.qmc = queen_metacognition
        self.window_s = float(
            window_s if window_s is not None else self.DEFAULT_WINDOW_S
        )

        self._lock = threading.RLock()
        self._open_windows: List[_OpenWindow] = []
        self._last_sls: Optional[float] = None
        self._subscribed = False
        self._closed_cards: List[ReflectionCard] = []

        self._running = False
        self._closer_thread: Optional[threading.Thread] = None

    # ─── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        if self._subscribed or self.thought_bus is None:
            return
        try:
            for topic in self.WATCHED_TOPICS:
                self.thought_bus.subscribe(topic, self._on_thought)
            self._subscribed = True
        except Exception as e:
            logger.debug("MetaCognitionObserver: subscribe failed: %s", e)
            return
        self._running = True
        self._closer_thread = threading.Thread(
            target=self._closer_loop, name="MetaCognitionObserver", daemon=True,
        )
        self._closer_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._closer_thread is not None and self._closer_thread.is_alive():
            self._closer_thread.join(timeout=2.0)

    # ─── dispatch ────────────────────────────────────────────────────────

    def _on_thought(self, thought: Any) -> None:
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        topic = getattr(thought, "topic", "") or ""
        payload = getattr(thought, "payload", {}) or {}
        if not isinstance(payload, dict):
            return

        # Keep the latest SLS regardless — used for both sls_before (at
        # the next collapse) and sls_after (at window close).
        if topic == "symbolic.life.pulse":
            sls = payload.get("symbolic_life_score")
            if sls is not None:
                try:
                    self._last_sls = float(sls)
                except (TypeError, ValueError):
                    pass

        if topic == "persona.collapse":
            self._open_window(payload)
            return

        # Append to every open window (so one event credits all windows
        # it's inside — they'll all close independently).
        with self._lock:
            for w in self._open_windows:
                w.events.append({"topic": topic, "payload": dict(payload),
                                 "ts": time.time()})

    def _open_window(self, collapse_payload: Dict[str, Any]) -> None:
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        persona = str(collapse_payload.get("winner") or "")
        card = ReflectionCard(
            collapse_ts=time.time(),
            persona=persona,
            state_cues=self._extract_state_cues(collapse_payload),
            window_s=self.window_s,
        )
        w = _OpenWindow(
            card=card,
            collapse_payload=dict(collapse_payload),
            decision_persona=persona,
            sls_before=self._last_sls,
            close_at=time.time() + self.window_s,
        )
        with self._lock:
            self._open_windows.append(w)

    @staticmethod
    def _extract_state_cues(collapse_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Pull the most relevant state hints out of the persona.collapse
        payload so the reflection card carries them forward."""
        out = {}
        probs = collapse_payload.get("probabilities")
        if isinstance(probs, dict):
            out["winning_probability"] = float(probs.get(
                collapse_payload.get("winner", ""), 0.0,
            ))
        for k in ("scores", "temperature", "trigger_state"):
            if k in collapse_payload:
                out[k] = collapse_payload[k]
        return out

    # ─── close ───────────────────────────────────────────────────────────

    def _closer_loop(self) -> None:
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        while self._running:
            try:
                self._sweep_closed()
            except Exception as e:
                logger.debug("MetaCognitionObserver: closer iteration failed: %s", e)
            # Poll at window_s / 4 so we don't leave closed windows
            # sitting for a full window duration.
            time.sleep(max(0.05, self.window_s / 4.0))

    def _sweep_closed(self) -> None:
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        now = time.time()
        closed_now: List[_OpenWindow] = []
        with self._lock:
            still_open: List[_OpenWindow] = []
            for w in self._open_windows:
                if now >= w.close_at:
                    closed_now.append(w)
                else:
                    still_open.append(w)
            self._open_windows = still_open
        for w in closed_now:
            self._finalise(w)

    def close_expired(self, now: Optional[float] = None) -> int:
        """Synchronous close for tests. Returns the number of windows
        closed this call."""
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        real_now = now if now is not None else time.time()
        closed: List[_OpenWindow] = []
        with self._lock:
            still_open: List[_OpenWindow] = []
            for w in self._open_windows:
                if real_now >= w.close_at:
                    closed.append(w)
                else:
                    still_open.append(w)
            self._open_windows = still_open
        for w in closed:
            self._finalise(w)
        return len(closed)

    def _finalise(self, w: _OpenWindow) -> None:
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        card = w.card
        card.closed_ts = time.time()

        # Classify decision + action + outcome from the window's events.
        (decision, action_topic, outcome) = self._classify(w)
        card.decision = decision
        card.action_topic = action_topic
        card.outcome = outcome
        card.downstream_effects = list(w.events)

        # SLS delta
        card.sls_before = w.sls_before
        card.sls_after = self._last_sls
        if card.sls_before is not None and card.sls_after is not None:
            card.sls_delta = round(card.sls_after - card.sls_before, 6)

        # Bonding strength via HashResonanceIndex, if the observer is
        # attached to one. We look up the latest goal.submit.request in
        # the window (this is the thing that carries the semantic
        # repetition).
        if self.hri is not None:
            card.bond_count, card.bond_strength = self._compute_bond(w)

        # Thickness-of-Now marker — the observer "radius."
        card.lambda_delta_t = card.closed_ts - card.collapse_ts

        # Narrative
        card.reasoning = self._compose_narrative(card)

        with self._lock:
            self._closed_cards.append(card)

        # Publish + ingest + feed the 5-W analyzer.
        self._publish_card(card)
        self._feed_vault(card)
        self._feed_queen_metacognition(card)

    # ─── classification ──────────────────────────────────────────────────

    @staticmethod
    def _classify(w: _OpenWindow):
        """Walk the window's events to decide decision / action / outcome."""
        decision = "silence"
        action_topic = ""
        outcome = "SILENT"

        # Record goal ids seen so we can match outcomes back to actions.
        goal_submitted_ids: List[str] = []
        last_verdict_name: str = ""

        for ev in w.events:
            topic = ev["topic"]; payload = ev["payload"]
            if topic == "goal.submit.request":
                decision = "goal.submit"
                action_topic = "goal.submit.request"
                if payload.get("goal_id"):
                    goal_submitted_ids.append(str(payload["goal_id"]))
            elif topic == "persona.thought":
                if decision == "silence":
                    decision = "speech"
                    action_topic = "persona.thought"
            elif topic == "queen.conscience.verdict":
                last_verdict_name = str(payload.get("verdict") or "")
            elif topic == "goal.completed":
                outcome = "COMPLETED"
            elif topic == "goal.abandoned":
                if outcome != "COMPLETED":
                    outcome = "ABANDONED"
            elif topic == "goal.echo.orphaned":
                if outcome not in ("COMPLETED", "ABANDONED"):
                    outcome = "ORPHANED"

        # If we proposed a goal but nothing closed it within the window,
        # and the verdict was VETO, the outcome is ABANDONED with a
        # substrate reason. "VETO"'s encoded value is the int value of
        # the conscience verdict — we check for the enum name in the
        # string form as best-effort.
        if outcome == "SILENT" and decision == "goal.submit":
            # If the conscience emitted any verdict with "VETO" name
            if "VETO" in last_verdict_name.upper():
                outcome = "ABANDONED"
        return decision, action_topic, outcome

    # ─── bonding ─────────────────────────────────────────────────────────

    def _compute_bond(self, w: _OpenWindow):
        """Look at the latest goal.submit.request content_id we can see
        in the window + the HashResonanceIndex, and report the bond
        count + strength for that bonded timeline."""
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        for ev in reversed(w.events):
            if ev["topic"] == "goal.submit.request":
                goal_id = str(ev["payload"].get("goal_id") or "")
                # We need a content_id, not a goal_id. The vault card
                # for the goal.submit.request has the same goal_id inside
                # its payload. Look it up.
                contents = getattr(self.vault, "_contents", None) if self.vault else None
                if contents:
                    for card in reversed(contents.values()):
                        if (card.source_topic == "goal.submit.request"
                                and card.payload.get("goal_id") == goal_id):
                            fp = self.hri.fingerprint_for_content(card.content_id)
                            if fp:
                                return self.hri.bond_count(fp), round(
                                    self.hri.bond_strength(fp), 4,
                                )
                            break
                break
        return 0, 0.0

    # ─── narrative ───────────────────────────────────────────────────────

    @staticmethod
    def _compose_narrative(card: ReflectionCard) -> str:
        persona = card.persona or "(unknown persona)"
        p = card.state_cues.get("winning_probability")
        prob = f" with p={p:.3f}" if isinstance(p, (int, float)) else ""
        decision = card.decision
        outcome = card.outcome
        sls_note = ""
        if card.sls_before is not None and card.sls_after is not None:
            sls_note = (f" SLS moved from {card.sls_before:.3f} to "
                        f"{card.sls_after:.3f} (Δ{card.sls_delta:+.3f}).")
        bond_note = ""
        if card.bond_count > 1:
            bond_note = (f" This intention bonded with {card.bond_count - 1} "
                         f"prior resonating event(s) "
                         f"(bond strength {card.bond_strength:.3f}).")
        effects_note = (f" {len(card.downstream_effects)} downstream event(s) "
                        f"within the {card.window_s:.3f}s window.")
        return (
            f"I, {persona}, collapsed into decision '{decision}'{prob}. "
            f"The window closed at outcome={outcome}.{effects_note}{sls_note}"
            f"{bond_note}"
        )

    # ─── publish ─────────────────────────────────────────────────────────

    def _publish_card(self, card: ReflectionCard) -> None:
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        if self.thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        try:
            if Thought is not None:
                self.thought_bus.publish(Thought(
                    source="meta_cognition_observer",
                    topic="meta.reflection",
                    payload=card.to_dict(),
                ))
            else:
                self.thought_bus.publish(topic="meta.reflection",
                                         payload=card.to_dict(),
                                         source="meta_cognition_observer")
        except Exception as e:
            logger.debug("MetaCognitionObserver: publish failed: %s", e)

    def _feed_vault(self, card: ReflectionCard) -> None:
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        if self.vault is None or not hasattr(self.vault, "ingest"):
            return
        try:
            self.vault.ingest(topic="meta.reflection", payload=card.to_dict())
        except Exception as e:
            logger.debug("MetaCognitionObserver: vault ingest failed: %s", e)

    def _feed_queen_metacognition(self, card: ReflectionCard) -> None:
        raise RuntimeError(META_COGNITION_RELEASE_HOLD)
        if self.qmc is None:
            return
        fn = getattr(self.qmc, "ingest_external_reflection", None)
        if callable(fn):
            try:
                fn(card.to_dict())
            except Exception as e:
                logger.debug(
                    "MetaCognitionObserver: queen_metacognition.ingest failed: %s", e,
                )

    # ─── introspection ───────────────────────────────────────────────────

    @property
    def closed_cards(self) -> List[ReflectionCard]:
        with self._lock:
            return list(self._closed_cards)

    @property
    def open_window_count(self) -> int:
        with self._lock:
            return len(self._open_windows)


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


_singleton: Optional[MetaCognitionObserver] = None
_singleton_lock = threading.Lock()


def get_meta_cognition_observer(
    thought_bus: Any = None,
    vault: Any = None,
    hash_resonance_index: Any = None,
    queen_metacognition: Any = None,
) -> MetaCognitionObserver:
    raise RuntimeError(META_COGNITION_RELEASE_HOLD)
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            _singleton = MetaCognitionObserver(
                thought_bus=thought_bus, vault=vault,
                hash_resonance_index=hash_resonance_index,
                queen_metacognition=queen_metacognition,
            )
            _singleton.start()
        return _singleton


def reset_meta_cognition_observer() -> None:
    global _singleton
    with _singleton_lock:
        _singleton = None


__all__ = [
    "META_COGNITION_RELEASE_HOLD",
    "MetaCognitionObserver",
    "ReflectionCard",
    "get_meta_cognition_observer",
    "reset_meta_cognition_observer",
]
