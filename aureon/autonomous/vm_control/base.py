"""
VM Controller Base — Abstract interface for all VM backends
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Defines the contract every VM backend must implement. The API mirrors the
computer-use tool set: screenshot, cursor actions, keyboard actions,
shell execution, and window management.

Safety model (inherited by all backends):
  - Arm/disarm gate (default: DRY_RUN)
  - Emergency stop flag (instant kill of all pending actions)
  - Pending action queue with confirmation tokens for high-risk ops
  - Per-session action history (last 50)
  - Risk classification for every action type
"""

from __future__ import annotations

import enum
import hashlib
import hmac
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class ActionRisk(enum.Enum):
    """Risk level for each action type."""
    SAFE = "safe"             # read-only: screenshot, list_windows, get_cursor_position
    LOW = "low"               # cursor moves, scroll — no state change
    MEDIUM = "medium"         # mouse clicks, key presses
    HIGH = "high"             # typing text, hotkeys, focus_window
    CRITICAL = "critical"     # shell execution, file operations


# Action risk classification
ACTION_RISK: Dict[str, ActionRisk] = {
    # Safe / read-only
    "screenshot": ActionRisk.SAFE,
    "get_cursor_position": ActionRisk.SAFE,
    "get_screen_size": ActionRisk.SAFE,
    "list_windows": ActionRisk.SAFE,
    "get_active_window": ActionRisk.SAFE,
    "wait": ActionRisk.SAFE,
    "status": ActionRisk.SAFE,
    # Low — cursor positioning
    "mouse_move": ActionRisk.LOW,
    "scroll": ActionRisk.LOW,
    # Medium — single-click actions
    "left_click": ActionRisk.MEDIUM,
    "right_click": ActionRisk.MEDIUM,
    "middle_click": ActionRisk.MEDIUM,
    "double_click": ActionRisk.MEDIUM,
    "triple_click": ActionRisk.MEDIUM,
    "left_click_drag": ActionRisk.MEDIUM,
    # High — text input and key presses
    "type_text": ActionRisk.HIGH,
    "press_key": ActionRisk.HIGH,
    "hotkey": ActionRisk.HIGH,
    "focus_window": ActionRisk.HIGH,
    # Critical — code execution / file ops
    "execute_shell": ActionRisk.CRITICAL,
    "execute_powershell": ActionRisk.CRITICAL,
    "upload_file": ActionRisk.CRITICAL,
    "download_file": ActionRisk.CRITICAL,
}


@dataclass
class VMAction:
    """A single action proposed for a VM."""

    action: str                                    # screenshot | left_click | type_text | ...
    params: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""                           # which VM session
    source: str = "agent"                          # which agent requested it
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requested_at: float = field(default_factory=time.time)
    confirm_token: Optional[str] = None            # required for high-risk actions when armed

    @property
    def risk(self) -> ActionRisk:
        return ACTION_RISK.get(self.action, ActionRisk.CRITICAL)


@dataclass
class VMActionResult:
    """Result of a VM action."""

    ok: bool = False
    action: str = ""
    session_id: str = ""
    dry_run: bool = False
    executed_at: float = field(default_factory=time.time)
    duration_s: float = 0.0
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "action": self.action,
            "session_id": self.session_id,
            "dry_run": self.dry_run,
            "executed_at": self.executed_at,
            "duration_s": self.duration_s,
            "data": self.data,
            "error": self.error,
        }


@dataclass
class VMSessionState:
    """State tracked per VM session."""

    session_id: str = ""
    name: str = ""
    backend: str = ""                              # simulated | winrm | ssh
    host: str = ""
    armed: bool = False
    dry_run: bool = True
    emergency_stopped: bool = False
    created_at: float = field(default_factory=time.time)
    action_count: int = 0
    error_count: int = 0
    last_action: Optional[str] = None
    last_screenshot_at: Optional[float] = None
    pending_actions: List[VMAction] = field(default_factory=list)
    action_history: List[VMActionResult] = field(default_factory=list)
    _lock: threading.RLock = field(default_factory=threading.RLock)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session_id": self.session_id,
                "name": self.name,
                "backend": self.backend,
                "host": self.host,
                "armed": self.armed,
                "dry_run": self.dry_run,
                "emergency_stopped": self.emergency_stopped,
                "created_at": self.created_at,
                "action_count": self.action_count,
                "error_count": self.error_count,
                "last_action": self.last_action,
                "last_screenshot_at": self.last_screenshot_at,
                "pending_count": len(self.pending_actions),
                "history_count": len(self.action_history),
            }


class VMController(ABC):
    """
    Abstract base class for all VM backends.

    Every backend must implement the 15 core action methods. The base class
    provides safety gating, session state tracking, and action history.
    """

    def __init__(
        self,
        session_id: Optional[str] = None,
        name: str = "",
        host: str = "",
        dry_run: bool = True,
        max_history: int = 50,
    ):
        self.session = VMSessionState(
            session_id=session_id or str(uuid.uuid4())[:8],
            name=name,
            backend=self._backend_name(),
            host=host,
            dry_run=dry_run,
            armed=False,
        )
        self._max_history = max_history
        self._confirmation_token_digest: Optional[str] = None

    @abstractmethod
    def _backend_name(self) -> str:
        """Return the backend name (simulated | winrm | ssh)."""

    # ─────────────────────────────────────────────────────────────────────
    # Session lifecycle
    # ─────────────────────────────────────────────────────────────────────

    def arm(self, dry_run: bool = True, confirmation_token: Optional[str] = None) -> Dict[str, Any]:
        """Arm the controller. Required before any action can execute."""
        with self.session._lock:
            if self.session.emergency_stopped:
                return {"ok": False, "error": "emergency_stopped"}
            if not dry_run and self.session.backend != "simulated" and not confirmation_token:
                return {"ok": False, "error": "live_confirmation_token_required"}
            self.session.armed = True
            self.session.dry_run = dry_run
            self._confirmation_token_digest = (
                hashlib.sha256(confirmation_token.encode("utf-8")).hexdigest()
                if confirmation_token else None
            )
        return {"ok": True, "armed": True, "dry_run": dry_run}

    def disarm(self) -> Dict[str, Any]:
        with self.session._lock:
            self.session.armed = False
            self._confirmation_token_digest = None
        return {"ok": True, "armed": False}

    def emergency_stop(self) -> Dict[str, Any]:
        with self.session._lock:
            self.session.emergency_stopped = True
            self.session.armed = False
            self._confirmation_token_digest = None
            self.session.pending_actions.clear()
        return {"ok": True, "emergency_stopped": True}

    def clear_emergency_stop(self) -> Dict[str, Any]:
        with self.session._lock:
            self.session.emergency_stopped = False
        return {"ok": True, "emergency_stopped": False}

    def connect(self) -> bool:
        """Establish a connection to the VM. Override in backends."""
        return True

    def disconnect(self) -> None:
        """Close the connection to the VM. Override in backends."""

    def health_check(self) -> bool:
        """Check if the backend can reach the VM."""
        return True

    # ─────────────────────────────────────────────────────────────────────
    # Safety gate
    # ─────────────────────────────────────────────────────────────────────

    def _check_gate(self, action: VMAction) -> Optional[VMActionResult]:
        """
        Return an error result if the action is not allowed, else None.
        """
        if self.session.emergency_stopped:
            return VMActionResult(
                ok=False,
                action=action.action,
                session_id=self.session.session_id,
                error="emergency_stopped",
            )

        if not self.session.armed:
            # Safe/read-only actions can run without arming
            if action.risk != ActionRisk.SAFE:
                return VMActionResult(
                    ok=False,
                    action=action.action,
                    session_id=self.session.session_id,
                    error="not_armed",
                )

        if (
            not self.session.dry_run
            and self.session.backend != "simulated"
            and action.risk in {ActionRisk.HIGH, ActionRisk.CRITICAL}
        ):
            supplied = hashlib.sha256((action.confirm_token or "").encode("utf-8")).hexdigest()
            expected = self._confirmation_token_digest or ""
            if not expected or not hmac.compare_digest(supplied, expected):
                return VMActionResult(
                    ok=False,
                    action=action.action,
                    session_id=self.session.session_id,
                    error="confirmation_required",
                )

        return None

    def _record(self, result: VMActionResult) -> VMActionResult:
        """Record the result in session history."""
        with self.session._lock:
            self.session.action_count += 1
            if not result.ok:
                self.session.error_count += 1
            self.session.last_action = result.action
            if result.action == "screenshot" and result.ok:
                self.session.last_screenshot_at = result.executed_at
            self.session.action_history.append(result)
            if len(self.session.action_history) > self._max_history:
                self.session.action_history = self.session.action_history[-self._max_history:]
        return result

    # ─────────────────────────────────────────────────────────────────────
    # Dispatch — top-level entry point for all actions
    # ─────────────────────────────────────────────────────────────────────

    def dispatch(self, action: VMAction) -> VMActionResult:
        """
        Main dispatch entry point. Applies safety gates, routes to the
        correct method, records history.
        """
        # Safety gate
        gate_error = self._check_gate(action)
        if gate_error:
            return self._record(gate_error)

        # Dry-run: simulate without executing
        if self.session.dry_run and action.risk != ActionRisk.SAFE:
            result = VMActionResult(
                ok=True,
                action=action.action,
                session_id=self.session.session_id,
                dry_run=True,
                data={"simulated": True, "params": action.params},
            )
            return self._record(result)

        # Route to concrete method
        method_name = f"_do_{action.action}"
        method = getattr(self, method_name, None)
        if not method:
            return self._record(VMActionResult(
                ok=False,
                action=action.action,
                session_id=self.session.session_id,
                error=f"unknown_action: {action.action}",
            ))

        start = time.time()
        try:
            data = method(**action.params) or {}
            result = VMActionResult(
                ok=True,
                action=action.action,
                session_id=self.session.session_id,
                dry_run=False,
                duration_s=time.time() - start,
                data=data if isinstance(data, dict) else {"value": data},
            )
        except Exception as e:
            result = VMActionResult(
                ok=False,
                action=action.action,
                session_id=self.session.session_id,
                dry_run=False,
                duration_s=time.time() - start,
                error=f"{type(e).__name__}: {e}",
            )
        return self._record(result)

    # ─────────────────────────────────────────────────────────────────────
    # Abstract action methods — backends override these
    # ─────────────────────────────────────────────────────────────────────

    @abstractmethod
    def _do_screenshot(self, **kwargs) -> Dict[str, Any]:
        """Take a screenshot. Return {'image_b64': ..., 'width': N, 'height': N}."""

    @abstractmethod
    def _do_mouse_move(self, x: int, y: int, **kwargs) -> Dict[str, Any]:
        """Move cursor to (x, y)."""

    @abstractmethod
    def _do_left_click(self, x: Optional[int] = None, y: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Left-click at current position or (x, y)."""

    @abstractmethod
    def _do_right_click(self, x: Optional[int] = None, y: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Right-click at current position or (x, y)."""

    @abstractmethod
    def _do_middle_click(self, x: Optional[int] = None, y: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Middle-click at current position or (x, y)."""

    @abstractmethod
    def _do_double_click(self, x: Optional[int] = None, y: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Double-click at current position or (x, y)."""

    @abstractmethod
    def _do_triple_click(self, x: Optional[int] = None, y: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        """Triple-click at current position or (x, y) — select a line."""

    @abstractmethod
    def _do_left_click_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, **kwargs) -> Dict[str, Any]:
        """Click-and-drag from start to end."""

    @abstractmethod
    def _do_scroll(self, x: int, y: int, direction: str = "down", amount: int = 3, **kwargs) -> Dict[str, Any]:
        """Scroll at (x, y). direction: up|down|left|right."""

    @abstractmethod
    def _do_type_text(self, text: str, **kwargs) -> Dict[str, Any]:
        """Type arbitrary text."""

    @abstractmethod
    def _do_press_key(self, key: str, **kwargs) -> Dict[str, Any]:
        """Press a single key (e.g. 'enter', 'escape', 'f1')."""

    @abstractmethod
    def _do_hotkey(self, keys: List[str], **kwargs) -> Dict[str, Any]:
        """Press a key combination (e.g. ['ctrl', 'c'])."""

    @abstractmethod
    def _do_get_cursor_position(self, **kwargs) -> Dict[str, Any]:
        """Return current cursor position."""

    @abstractmethod
    def _do_get_screen_size(self, **kwargs) -> Dict[str, Any]:
        """Return screen dimensions."""

    @abstractmethod
    def _do_list_windows(self, **kwargs) -> Dict[str, Any]:
        """List all open windows on the VM."""

    @abstractmethod
    def _do_get_active_window(self, **kwargs) -> Dict[str, Any]:
        """Return the currently focused window."""

    @abstractmethod
    def _do_focus_window(self, title: str, **kwargs) -> Dict[str, Any]:
        """Focus the window matching the given title."""

    @abstractmethod
    def _do_execute_shell(self, command: str, timeout: int = 30, **kwargs) -> Dict[str, Any]:
        """Execute a cmd.exe command."""

    @abstractmethod
    def _do_execute_powershell(self, command: str, timeout: int = 30, **kwargs) -> Dict[str, Any]:
        """Execute a PowerShell command."""

    def _do_wait(self, seconds: float = 1.0, **kwargs) -> Dict[str, Any]:
        """Wait N seconds (safe, universal implementation)."""
        seconds = min(max(0.0, float(seconds)), 30.0)  # cap at 30s
        time.sleep(seconds)
        return {"waited_s": seconds}

    def _do_status(self, **kwargs) -> Dict[str, Any]:
        """Return session status (safe, universal implementation)."""
        return self.session.to_dict()
