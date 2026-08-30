"""
VMControlDispatcher — Multi-Session Dispatcher with Safety Gates
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Top-level dispatcher that routes tool calls from agents to the correct
VM controller. Supports multiple simultaneous VM sessions.

Mirrors the Claude tool-dispatch pattern:
  1. Agent emits a tool_use block with action name + params
  2. Dispatcher looks up the active session (or the default one)
  3. Builds a VMAction and calls controller.dispatch(action)
  4. Returns a JSON string result (matching the ToolRegistry contract)

Session management:
  - create_session(backend, **kwargs) — spin up a new VM session
  - set_default(session_id) — the session used when none is specified
  - get_session(session_id) — fetch by id
  - list_sessions() — all active sessions
  - destroy_session(session_id) — clean up

Safety:
  - Global emergency_stop kills all sessions
  - Per-session arm/disarm + dry_run
  - Action counts + error rates tracked per session
  - Publishes all actions to ThoughtBus as 'vm.action' events
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, List, Optional

from aureon.autonomous.vm_control.base import (
    VMController,
    VMAction,
)
from aureon.autonomous.vm_control.simulated import SimulatedVMController
from aureon.autonomous.vm_control.winrm_backend import WinRMVMController
from aureon.autonomous.vm_control.ssh_backend import SSHVMController

logger = logging.getLogger("aureon.vm.dispatcher")


class VMControlDispatcher:
    """Manages multiple VM sessions and routes actions to the correct one."""

    def __init__(self):
        self._sessions: Dict[str, VMController] = {}
        self._default_session_id: Optional[str] = None
        self._lock = threading.RLock()
        self._thought_bus = None
        self._global_emergency_stop = False

        # Metrics
        self._total_actions = 0
        self._total_errors = 0
        self._created_at = time.time()

        # Wire ThoughtBus
        self._wire_thought_bus()

    def _wire_thought_bus(self):
        try:
            from aureon.core.aureon_thought_bus import ThoughtBus
            self._thought_bus = ThoughtBus()
            logger.info("VM Dispatcher wired to ThoughtBus")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Session management
    # ─────────────────────────────────────────────────────────────────────

    def create_session(
        self,
        backend: str = "simulated",
        name: str = "",
        host: str = "",
        make_default: bool = False,
        **kwargs,
    ) -> str:
        """
        Create a new VM session.

        Args:
            backend: 'simulated' | 'winrm' | 'ssh'
            name: friendly name for the session
            host: VM hostname/IP
            make_default: if True, set as default session
            **kwargs: passed to the controller constructor
                     (username, password, key_filename, port, use_ssl, platform, etc.)

        Returns:
            The session_id of the created session.
        """
        backend = backend.lower()
        if backend == "simulated":
            controller: VMController = SimulatedVMController(name=name, host=host, **kwargs)
        elif backend == "winrm":
            controller = WinRMVMController(name=name, host=host, **kwargs)
        elif backend == "ssh":
            controller = SSHVMController(name=name, host=host, **kwargs)
        else:
            raise ValueError(f"Unknown backend: {backend}. Use: simulated | winrm | ssh")

        # Try to connect (backends gracefully fall back to stub)
        try:
            controller.connect()
        except Exception as e:
            logger.warning("Session %s connect failed: %s", controller.session.session_id, e)

        with self._lock:
            sid = controller.session.session_id
            self._sessions[sid] = controller
            if make_default or self._default_session_id is None:
                self._default_session_id = sid

        logger.info("VM session created: %s (%s) backend=%s", sid, name or "unnamed", backend)
        self._publish_event("vm.session.created", {
            "session_id": sid,
            "backend": backend,
            "name": name,
            "host": host,
        })
        return sid

    def get_session(self, session_id: Optional[str] = None) -> Optional[VMController]:
        with self._lock:
            if session_id is None:
                session_id = self._default_session_id
            if session_id is None:
                return None
            return self._sessions.get(session_id)

    def set_default(self, session_id: str) -> bool:
        with self._lock:
            if session_id in self._sessions:
                self._default_session_id = session_id
                return True
            return False

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [c.session.to_dict() for c in self._sessions.values()]

    def destroy_session(self, session_id: str) -> bool:
        with self._lock:
            controller = self._sessions.pop(session_id, None)
            if controller:
                try:
                    controller.disconnect()
                except Exception:
                    pass
                if self._default_session_id == session_id:
                    self._default_session_id = next(iter(self._sessions), None)
                return True
            return False

    def destroy_all(self):
        with self._lock:
            for sid in list(self._sessions.keys()):
                self.destroy_session(sid)

    # ─────────────────────────────────────────────────────────────────────
    # Global safety
    # ─────────────────────────────────────────────────────────────────────

    def emergency_stop_all(self) -> Dict[str, Any]:
        """Emergency stop every active session."""
        with self._lock:
            self._global_emergency_stop = True
            stopped = []
            for sid, controller in self._sessions.items():
                try:
                    controller.emergency_stop()
                    stopped.append(sid)
                except Exception:
                    pass
        self._publish_event("vm.emergency_stop_all", {"sessions": stopped})
        return {"ok": True, "stopped": stopped}

    def clear_emergency_stop_all(self) -> Dict[str, Any]:
        with self._lock:
            self._global_emergency_stop = False
            cleared = []
            for sid, controller in self._sessions.items():
                try:
                    controller.clear_emergency_stop()
                    cleared.append(sid)
                except Exception:
                    pass
        return {"ok": True, "cleared": cleared}

    # ─────────────────────────────────────────────────────────────────────
    # Dispatch — the core entry point
    # ─────────────────────────────────────────────────────────────────────

    def dispatch(
        self,
        action_name: str,
        params: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        source: str = "agent",
        confirm_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatch a VM action.

        This is what tool handlers call. Returns a dict suitable for
        JSON serialisation back to the agent.
        """
        if self._global_emergency_stop:
            return {"ok": False, "error": "global_emergency_stop"}

        controller = self.get_session(session_id)
        if not controller:
            return {"ok": False, "error": "no_session", "available": list(self._sessions.keys())}

        action = VMAction(
            action=action_name,
            params=params or {},
            session_id=controller.session.session_id,
            source=source,
            confirm_token=confirm_token,
        )

        with self._lock:
            self._total_actions += 1

        result = controller.dispatch(action)

        if not result.ok:
            with self._lock:
                self._total_errors += 1

        # Publish
        self._publish_event(
            f"vm.action.{action_name}",
            {
                "session_id": result.session_id,
                "action": action_name,
                "ok": result.ok,
                "dry_run": result.dry_run,
                "duration_s": result.duration_s,
                "error": result.error,
            },
        )

        return result.to_dict()

    # ─────────────────────────────────────────────────────────────────────
    # ThoughtBus publishing
    # ─────────────────────────────────────────────────────────────────────

    def _publish_event(self, topic: str, payload: Dict[str, Any]):
        if not self._thought_bus:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self._thought_bus.publish(Thought(
                source="vm.dispatcher",
                topic=topic,
                payload=payload,
            ))
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_sessions": len(self._sessions),
                "default_session_id": self._default_session_id,
                "global_emergency_stop": self._global_emergency_stop,
                "total_actions": self._total_actions,
                "total_errors": self._total_errors,
                "uptime_s": time.time() - self._created_at,
                "sessions": [c.session.to_dict() for c in self._sessions.values()],
            }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


_dispatcher_instance: Optional[VMControlDispatcher] = None
_dispatcher_lock = threading.Lock()


def get_vm_dispatcher() -> VMControlDispatcher:
    """Get or create the global VMControlDispatcher singleton."""
    global _dispatcher_instance
    with _dispatcher_lock:
        if _dispatcher_instance is None:
            _dispatcher_instance = VMControlDispatcher()
        return _dispatcher_instance
