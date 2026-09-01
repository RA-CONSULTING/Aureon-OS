"""
OpportunityScanner — every persona scanning for ways to help
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT RELEASE: background scanning, threads, and goal dispatch are
hard-HOLD before effects until the production Magic Star release is available.
Persona opportunity-shaping functions remain pure and inspectable.

Between user turns, the scanner walks every persona against every
active LifeEvent and asks ``scan_for_opportunity(event)``. If a
persona sees a way to help, the scanner emits a ``goal.submit.request``
via the existing PersonaActuator so the goal flows into the standard
engine pipeline — and eventually, when stage 4.3 is wired, past the
human-approval gate.

Each (persona, event_id) pair fires at most once per ``dedupe_window_s``
so the backlog doesn't flood. The scanner is designed to run on its
own thread at a slow cadence; it never competes with foreground user
observes because it only dispatches goals, not full vacuum observes.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aureon.vault.voice.aureon_personas import ResonantPersona
from aureon.vault.voice.life_context import LifeContext
from aureon.vault.voice.persona_action import PersonaAction, PersonaActuator

logger = logging.getLogger("aureon.vault.voice.opportunity_scanner")


OPPORTUNITY_SCANNER_RELEASE_HOLD = (
    "opportunity_scanner_hold:production_magic_star_release_unavailable"
)


@dataclass
class OpportunityHit:
    persona: str
    event_id: str
    goal_text: str
    urgency: float
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona": self.persona,
            "event_id": self.event_id,
            "goal_text": self.goal_text,
            "urgency": self.urgency,
            "ts": self.ts,
        }


class OpportunityScanner:
    """Runs every persona's ``scan_for_opportunity`` against every active
    LifeEvent on a slow cadence and emits goal requests through the
    PersonaActuator.

    Designed for the "all working in the background" pattern — one
    thread, one mutex, idempotent per window.
    """

    def __init__(
        self,
        *,
        personas: Dict[str, ResonantPersona],
        life_context: LifeContext,
        actuator: PersonaActuator,
        dedupe_window_s: float = 3600.0,   # at most one emit per hour per pair
        interval_s: float = 30.0,           # sweep every 30s in background mode
        urgency: float = 0.7,
    ):
        self._personas = dict(personas)
        self._life_context = life_context
        self._actuator = actuator
        self.dedupe_window_s = float(dedupe_window_s)
        self.interval_s = float(interval_s)
        self.urgency = float(urgency)

        self._lock = threading.RLock()
        self._recent: Dict[Tuple[str, str], float] = {}   # (persona, event_id) -> ts
        self._history: List[OpportunityHit] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ─── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> None:
        raise RuntimeError(OPPORTUNITY_SCANNER_RELEASE_HOLD)
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._loop, name="OpportunityScanner", daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    @property
    def running(self) -> bool:
        return self._running

    # ─── scan ────────────────────────────────────────────────────────────

    def scan_once(self, state: Optional[Dict[str, Any]] = None) -> List[OpportunityHit]:
        """Perform one full sweep: every persona × every active event.
        Returns the list of OpportunityHits dispatched this sweep."""
        raise RuntimeError(OPPORTUNITY_SCANNER_RELEASE_HOLD)
        state = dict(state or {})
        events = self._life_context.active()
        if not events:
            return []
        fired: List[OpportunityHit] = []
        now = time.time()
        with self._lock:
            self._prune_recent(now)
        for persona_name, persona in self._personas.items():
            for event in events:
                key = (persona_name, event.event_id)
                with self._lock:
                    last = self._recent.get(key)
                if last is not None and now - last < self.dedupe_window_s:
                    continue
                try:
                    goal_text = persona.scan_for_opportunity(event, state)
                except Exception as e:
                    logger.debug(
                        "OpportunityScanner: %s scan failed on %s: %s",
                        persona_name, event.event_id, e,
                    )
                    goal_text = None
                if not goal_text:
                    continue
                hit = OpportunityHit(
                    persona=persona_name,
                    event_id=event.event_id,
                    goal_text=goal_text,
                    urgency=self.urgency,
                )
                self._dispatch(hit, event)
                with self._lock:
                    self._recent[key] = now
                    self._history.append(hit)
                fired.append(hit)
        return fired

    def _dispatch(self, hit: OpportunityHit, event: Any) -> None:
        raise RuntimeError(OPPORTUNITY_SCANNER_RELEASE_HOLD)
        action = PersonaAction(
            kind="goal.submit",
            topic=hit.goal_text,
            payload={
                "event_id": hit.event_id,
                "event_title": event.title,
                "event_date": event.date,
                "event_tags": list(event.tags),
                "source": "opportunity_scanner",
            },
            reason=f"{hit.persona} sees a way to help with \u201c{event.title}\u201d",
            urgency=hit.urgency,
        )
        try:
            self._actuator.dispatch(hit.persona, action,
                                    state={"persona": hit.persona})
        except Exception as e:
            logger.debug("OpportunityScanner: dispatch failed: %s", e)

    def _prune_recent(self, now: float) -> None:
        expired = [k for k, t in self._recent.items()
                   if now - t > self.dedupe_window_s]
        for k in expired:
            del self._recent[k]

    # ─── loop ────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        raise RuntimeError(OPPORTUNITY_SCANNER_RELEASE_HOLD)
        while self._running:
            time.sleep(self.interval_s)
            if not self._running:
                break
            try:
                self.scan_once()
            except Exception as e:
                logger.debug("OpportunityScanner: loop iteration failed: %s", e)

    # ─── introspection ───────────────────────────────────────────────────

    def history(self, n: int = 32) -> List[Dict[str, Any]]:
        with self._lock:
            tail = self._history[-int(max(1, n)):]
        return [h.to_dict() for h in tail]


__all__ = ["OpportunityScanner", "OpportunityHit"]
