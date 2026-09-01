"""
PersonaAction & PersonaActuator — turn persona collapses into real actions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CURRENT RELEASE: the design below is unreleased. Every dispatch and built-in
handler hard-HOLDs before bus, vault, filesystem, goal, or skill effects until
the production Magic Star release and receipt-backed governance exist.

The compatibility types and handler registry remain available for callers,
but this release does not execute persona intentions. Five historical action
kinds remain registered only so API inspection is stable:

    bus.publish    — emit a Thought on the ThoughtBus, with a chosen topic
                     and payload, so every subsystem that subscribes can
                     react (Queen cognition, rally coordinator, miner).
    vault.ingest   — write a VaultContent card into the vault directly
                     (useful for persisting a persona's observation as
                     durable memory even if no downstream reacts).
    file.append    — append a JSONL line to a named file (so the action
                     is visible on disk across restarts).
    skill.request  — emit ``skill.author.request`` for the Code Architect
                     to pick up, carrying a short natural-language brief.

``dispatch`` and every direct built-in handler raise the same release HOLD
before invoking callbacks, publishing, writing, or mutating downstream state.

Gary Leckey · Aureon Institute — April 2026
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Deque, Dict, List, Optional

logger = logging.getLogger("aureon.vault.voice.persona_action")


# ─────────────────────────────────────────────────────────────────────────────
# PersonaAction
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class PersonaAction:
    """A structured intention a persona wants executed after it speaks."""

    kind: str                                         # handler key, e.g. "bus.publish"
    topic: str = ""                                   # target topic / skill name / file path
    payload: Dict[str, Any] = field(default_factory=dict)
    target: str = ""                                  # optional sub-address for the handler
    reason: str = ""                                  # human-readable rationale
    urgency: float = 0.5                              # [0,1] — hints to handlers / governance

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "topic": self.topic,
            "payload": dict(self.payload),
            "target": self.target,
            "reason": self.reason,
            "urgency": float(self.urgency),
        }


@dataclass
class ActionExecution:
    """Record of one actuator dispatch — what persona, what action, what result."""

    ts: float
    persona: str
    action: PersonaAction
    ok: bool
    dry_run: bool
    result: Any = None
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts,
            "persona": self.persona,
            "action": self.action.to_dict(),
            "ok": self.ok,
            "dry_run": self.dry_run,
            "result": self.result,
            "error": self.error,
        }


# ─────────────────────────────────────────────────────────────────────────────
# PersonaActuator
# ─────────────────────────────────────────────────────────────────────────────


HandlerFn = Callable[[PersonaAction, Dict[str, Any]], Any]


PERSONA_ACTION_RELEASE_HOLD = (
    "persona_action_hold:production_magic_star_release_unavailable"
)


class PersonaActuator:
    """Registry of action handlers. Dispatches PersonaActions from the vacuum."""

    def __init__(
        self,
        *,
        vault: Any = None,
        thought_bus: Any = None,
        history_size: int = 256,
        file_root: Optional[str] = None,
    ):
        self.vault = vault
        self.thought_bus = thought_bus
        self.file_root = file_root
        self._history: Deque[ActionExecution] = deque(maxlen=int(history_size))
        self._handlers: Dict[str, HandlerFn] = {}
        self._lock = threading.Lock()
        self._register_defaults()

    # ─────────────────────────────────────────────────────────────────────
    # Handler registry
    # ─────────────────────────────────────────────────────────────────────

    def register(self, kind: str, handler: HandlerFn) -> None:
        with self._lock:
            self._handlers[kind] = handler

    def unregister(self, kind: str) -> None:
        with self._lock:
            self._handlers.pop(kind, None)

    def handler(self, kind: str) -> Optional[HandlerFn]:
        with self._lock:
            return self._handlers.get(kind)

    def _register_defaults(self) -> None:
        self.register("bus.publish", self._handle_bus_publish)
        self.register("vault.ingest", self._handle_vault_ingest)
        self.register("file.append", self._handle_file_append)
        self.register("skill.request", self._handle_skill_request)
        self.register("goal.submit", self._handle_goal_submit)

    # ─────────────────────────────────────────────────────────────────────
    # Dispatch
    # ─────────────────────────────────────────────────────────────────────

    def dispatch(
        self,
        persona: str,
        action: Optional[PersonaAction],
        state: Optional[Dict[str, Any]] = None,
    ) -> Optional[ActionExecution]:
        """Execute an action. Records the outcome in history regardless of success."""
        raise RuntimeError(PERSONA_ACTION_RELEASE_HOLD)
        if action is None:
            return None
        state_dict = dict(state or {})
        exec_record = ActionExecution(
            ts=time.time(),
            persona=str(persona),
            action=action,
            ok=False,
            dry_run=False,
        )
        handler = self.handler(action.kind)
        if handler is None:
            exec_record.error = f"no handler registered for kind={action.kind!r}"
            self._record(exec_record)
            return exec_record

        try:
            exec_record.result = handler(action, state_dict)
            exec_record.ok = True
        except Exception as e:
            exec_record.error = f"{type(e).__name__}: {e}"
            logger.debug("PersonaActuator: handler %s raised: %s", action.kind, e)
        self._record(exec_record)
        return exec_record

    def _record(self, exec_record: ActionExecution) -> None:
        with self._lock:
            self._history.append(exec_record)

    # ─────────────────────────────────────────────────────────────────────
    # Default handlers
    # ─────────────────────────────────────────────────────────────────────

    def _handle_bus_publish(self, action: PersonaAction, state: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError(PERSONA_ACTION_RELEASE_HOLD)
        if self.thought_bus is None:
            return {"ok": False, "reason": "no thought_bus"}
        if not action.topic:
            return {"ok": False, "reason": "action.topic empty"}
        # Avoid a hard import at module load so this module stays cheap to import.
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        payload = dict(action.payload)
        payload.setdefault("reason", action.reason)
        payload.setdefault("urgency", action.urgency)
        if Thought is not None:
            self.thought_bus.publish(Thought(
                source="persona_actuator",
                topic=action.topic,
                payload=payload,
            ))
        else:
            self.thought_bus.publish(topic=action.topic, payload=payload, source="persona_actuator")
        return {"ok": True, "topic": action.topic}

    def _handle_vault_ingest(self, action: PersonaAction, state: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError(PERSONA_ACTION_RELEASE_HOLD)
        if self.vault is None or not hasattr(self.vault, "ingest"):
            return {"ok": False, "reason": "vault has no ingest"}
        topic = action.topic or "persona.action.vault"
        self.vault.ingest(topic=topic, payload=dict(action.payload) or {"reason": action.reason})
        return {"ok": True, "topic": topic}

    def _handle_file_append(self, action: PersonaAction, state: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError(PERSONA_ACTION_RELEASE_HOLD)
        raw_path = action.target or action.topic
        if not raw_path:
            return {"ok": False, "reason": "action.target/topic missing"}
        path = raw_path
        if self.file_root and not os.path.isabs(raw_path):
            path = os.path.join(self.file_root, raw_path)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        line = json.dumps({
            "ts": time.time(),
            "reason": action.reason,
            "urgency": action.urgency,
            **action.payload,
        }, default=str)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
        return {"ok": True, "path": path, "bytes": len(line) + 1}

    def _handle_goal_submit(self, action: PersonaAction, state: Dict[str, Any]) -> Dict[str, Any]:
        """Publish a goal request on the bus for GoalExecutionEngine to pick up.

        We route through ``goal.submit.request`` rather than calling the
        engine directly so:
          - a system without the engine booted still records the intent
          - the existing goal.* namespace (goal.submitted / goal.progress)
            on the bus stays the engine's output contract
          - stage 4.3 can insert a human-approval gate between this
            publication and the engine's intake
        """
        raise RuntimeError(PERSONA_ACTION_RELEASE_HOLD)
        if self.thought_bus is None:
            return {"ok": False, "reason": "no thought_bus"}
        goal_text = action.topic or action.reason
        if not goal_text:
            return {"ok": False, "reason": "action.topic / reason must carry the goal text"}
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        payload = {
            "text": goal_text,
            "proposed_by_persona": state.get("persona", ""),
            "urgency": action.urgency,
            "parameters": dict(action.payload),
        }
        topic = "goal.submit.request"
        if Thought is not None:
            self.thought_bus.publish(Thought(
                source="persona_actuator",
                topic=topic,
                payload=payload,
            ))
        else:
            self.thought_bus.publish(topic=topic, payload=payload,
                                     source="persona_actuator")
        return {"ok": True, "topic": topic, "goal_text": goal_text}

    def _handle_skill_request(self, action: PersonaAction, state: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError(PERSONA_ACTION_RELEASE_HOLD)
        if self.thought_bus is None:
            return {"ok": False, "reason": "no thought_bus"}
        try:
            from aureon.core.aureon_thought_bus import Thought  # type: ignore
        except Exception:
            Thought = None  # type: ignore
        payload = {
            "brief": action.topic or action.reason,
            "parameters": action.payload,
            "requested_by_persona": state.get("persona", ""),
            "urgency": action.urgency,
        }
        thought_topic = "skill.author.request"
        if Thought is not None:
            self.thought_bus.publish(Thought(
                source="persona_actuator",
                topic=thought_topic,
                payload=payload,
            ))
        else:
            self.thought_bus.publish(topic=thought_topic, payload=payload, source="persona_actuator")
        return {"ok": True, "topic": thought_topic}

    # ─────────────────────────────────────────────────────────────────────
    # Introspection
    # ─────────────────────────────────────────────────────────────────────

    def history(self, n: int = 32) -> List[Dict[str, Any]]:
        with self._lock:
            tail = list(self._history)[-int(max(1, n)):]
        return [e.to_dict() for e in tail]

    def last(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            if not self._history:
                return None
            return self._history[-1].to_dict()

    def status(self) -> Dict[str, Any]:
        with self._lock:
            history_size = len(self._history)
            handler_count = len(self._handlers)
        return {
            "status": "HOLD",
            "reason_code": "production_magic_star_release_unavailable",
            "production_ready": False,
            "effect_enabled": False,
            "history_size": history_size,
            "registered_handler_count": handler_count,
        }


__all__ = [
    "PERSONA_ACTION_RELEASE_HOLD",
    "PersonaAction",
    "ActionExecution",
    "PersonaActuator",
]
