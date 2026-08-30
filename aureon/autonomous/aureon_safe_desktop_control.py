#!/usr/bin/env python3
"""
Safe local desktop control for supervised automation.

This module is intentionally constrained:
- local-only
- manual arm/disarm
- dry-run by default
- optional per-action confirmation token for non-trivial actions
- emergency stop support
- allowlisted action types only

It is meant to complement the repo's existing orchestration/control systems
without granting unrestricted autonomous takeover of the host machine.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]

try:
    import pyautogui  # type: ignore

    HAS_PYAUTOGUI = True
    try:
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.05
    except Exception:
        pass
except Exception:
    pyautogui = None  # type: ignore
    HAS_PYAUTOGUI = False


ALLOWED_ACTIONS = {
    "move_mouse",
    "left_click",
    "right_click",
    "double_click",
    "type_text",
    "press_key",
    "hotkey",
}

# Actions that are easy to misuse (typing/hotkeys).  The legacy controller keeps
# them behind confirmation by default.  New autonomous paths should use
# ``AureonGovernedDesktopGateway`` which additionally carries an expiring
# capability lease and before/after evidence.
HIGH_RISK_ACTIONS = {
    "type_text",
    "press_key",
    "hotkey",
}

# When a DesktopAction is proposed, we can auto-execute some low-risk actions if
# the controller is armed.
AUTO_EXECUTE_ACTIONS = {
    "move_mouse",
    "left_click",
    "right_click",
    "double_click",
    "press_key",
}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_env_path(env_name: str, default_path: Path) -> Path:
    raw = (os.getenv(env_name) or "").strip()
    p = Path(raw) if raw else default_path
    if not p.is_absolute():
        p = (REPO_ROOT / p).resolve()
    return p


DEFAULT_STATE_PATH = _resolve_env_path(
    "AUREON_DESKTOP_CONTROL_STATE",
    REPO_ROOT / "state" / "safe_desktop_control_state.json",
)
DEFAULT_KILL_PATH = _resolve_env_path(
    "AUREON_DESKTOP_KILL_SWITCH",
    REPO_ROOT / "state" / "safe_desktop_control.stop",
)


@dataclass
class DesktopAction:
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    confirm_token: str = ""
    requested_at: float = field(default_factory=time.time)
    source: str = "local"
    approved: bool = False


@dataclass
class DesktopActionResult:
    ok: bool
    action: str
    reason: str = ""
    executed_at: float = field(default_factory=time.time)
    dry_run: bool = False
    params: Dict[str, Any] = field(default_factory=dict)


class SafeDesktopControl:
    def __init__(
        self,
        state_path: Optional[Path] = None,
        kill_path: Optional[Path] = None,
        dry_run: bool = True,
    ) -> None:
        self.state_path = Path(state_path or DEFAULT_STATE_PATH)
        self.kill_path = Path(kill_path or DEFAULT_KILL_PATH)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.kill_path.parent.mkdir(parents=True, exist_ok=True)

        self.dry_run = dry_run
        self.armed = False
        self.last_error = ""
        self.last_result: Dict[str, Any] = {}
        self.recent_actions: List[Dict[str, Any]] = []
        self.pending_actions: List[Dict[str, Any]] = []

        self.require_confirmation = _env_bool("AUREON_DESKTOP_REQUIRE_CONFIRMATION", True)
        self.auto_approve_live_voice = _env_bool("AUREON_AUTO_APPROVE_LIVE_VOICE", False)
        self.confirmation_token = os.getenv("AUREON_DESKTOP_CONFIRM_TOKEN", "")
        self.max_recent_actions = 25
        self.max_pending_actions = 20

        self._load_state()
        self._persist_state()

    def arm(self) -> None:
        self.armed = True
        self.last_error = ""
        self._persist_state()

    def set_live_mode(self, enabled: bool) -> None:
        self.dry_run = not enabled
        self.last_error = ""
        self._persist_state()

    def arm_live(self) -> None:
        self.set_live_mode(True)
        self.arm()

    def arm_dry_run(self) -> None:
        self.set_live_mode(False)
        self.arm()

    def disarm(self) -> None:
        self.armed = False
        self._persist_state()

    def emergency_stop(self) -> None:
        self.disarm()
        self.kill_path.write_text("STOP\n", encoding="utf-8")

    def clear_emergency_stop(self) -> None:
        if self.kill_path.exists():
            self.kill_path.unlink()
        self._persist_state()

    def is_emergency_stopped(self) -> bool:
        return self.kill_path.exists()

    def status(self) -> Dict[str, Any]:
        return {
            "ok": True,
            "armed": self.armed,
            "dry_run": self.dry_run,
            "pyautogui_available": HAS_PYAUTOGUI,
            "emergency_stopped": self.is_emergency_stopped(),
            "require_confirmation": self.require_confirmation,
            "auto_approve_live_voice": self.auto_approve_live_voice,
            "allowed_actions": sorted(ALLOWED_ACTIONS),
            "auto_execute_actions": sorted(AUTO_EXECUTE_ACTIONS),
            "last_error": self.last_error,
            "last_result": dict(self.last_result),
            "pending_actions": [self._redact_action(item) for item in self.pending_actions[-10:]],
            "recent_actions": [self._redact_action(item) for item in self.recent_actions[-10:]],
        }

    def propose(self, req: DesktopAction) -> Dict[str, Any]:
        if self._should_auto_execute(req):
            result = self.execute(req)
            payload = asdict(req)
            payload["status"] = "executed" if result.ok else "failed"
            payload["execution_result"] = asdict(result)
            self._persist_state()
            return payload

        item = asdict(req)
        item["status"] = "pending"
        self.pending_actions.append(item)
        if len(self.pending_actions) > self.max_pending_actions:
            self.pending_actions = self.pending_actions[-self.max_pending_actions :]
        self._persist_state()
        return item

    def approve_next(self, confirm_token: str = "") -> DesktopActionResult:
        if not self.pending_actions:
            dummy = DesktopAction(action="noop")
            return self._reject(dummy, "no_pending_actions")

        item = self.pending_actions.pop(0)
        req = DesktopAction(
            action=str(item.get("action") or ""),
            params=dict(item.get("params") or {}),
            confirm_token=confirm_token,
            requested_at=float(item.get("requested_at") or time.time()),
            source=str(item.get("source") or "queue"),
            approved=True,
        )
        self._persist_state()
        return self.execute(req)

    def clear_pending(self) -> None:
        self.pending_actions = []
        self._persist_state()

    def execute(self, req: DesktopAction) -> DesktopActionResult:
        if req.action not in ALLOWED_ACTIONS:
            return self._reject(req, f"action_not_allowed:{req.action}")
        if self.is_emergency_stopped():
            return self._reject(req, "emergency_stop_active")
        if not self.armed:
            return self._reject(req, "controller_not_armed")
        if not self.dry_run and not req.approved:
            return self._reject(req, "explicit_action_approval_required")
        if self.require_confirmation and req.action in HIGH_RISK_ACTIONS and not self._bypass_confirmation(req):
            if not self.confirmation_token or req.confirm_token != self.confirmation_token:
                return self._reject(req, "confirmation_required")
        if not HAS_PYAUTOGUI and not self.dry_run:
            return self._reject(req, "pyautogui_not_available")

        result = DesktopActionResult(
            ok=True,
            action=req.action,
            reason="executed" if not self.dry_run else "dry_run",
            dry_run=self.dry_run,
            params=dict(req.params),
        )
        try:
            if not self.dry_run:
                self._dispatch(req)
            self._record_result(result)
            return result
        except Exception as e:
            return self._reject(req, f"execution_failed:{e}")

    def _dispatch(self, req: DesktopAction) -> None:
        assert pyautogui is not None
        p = req.params
        if req.action == "move_mouse":
            pyautogui.moveTo(int(p["x"]), int(p["y"]), duration=float(p.get("duration", 0.0) or 0.0))
        elif req.action == "left_click":
            pyautogui.click(x=p.get("x"), y=p.get("y"), button="left")
        elif req.action == "right_click":
            pyautogui.click(x=p.get("x"), y=p.get("y"), button="right")
        elif req.action == "double_click":
            pyautogui.doubleClick(x=p.get("x"), y=p.get("y"))
        elif req.action == "type_text":
            pyautogui.write(str(p.get("text", "")), interval=float(p.get("interval", 0.02) or 0.02))
        elif req.action == "press_key":
            pyautogui.press(str(p["key"]))
        elif req.action == "hotkey":
            keys = p.get("keys") or []
            if not isinstance(keys, list) or not keys:
                raise ValueError("hotkey requires keys list")
            pyautogui.hotkey(*[str(k) for k in keys])
        else:
            raise ValueError(f"unsupported_action:{req.action}")

    def _reject(self, req: DesktopAction, reason: str) -> DesktopActionResult:
        self.last_error = reason
        result = DesktopActionResult(
            ok=False,
            action=req.action,
            reason=reason,
            dry_run=self.dry_run,
            params=dict(req.params),
        )
        self._record_result(result)
        return result

    def _should_auto_execute(self, req: DesktopAction) -> bool:
        if not self.armed:
            return False
        if req.action in AUTO_EXECUTE_ACTIONS and (self.dry_run or req.approved):
            return True
        if self.auto_approve_live_voice and not self.dry_run and self._is_voice_request(req):
            return req.action in ALLOWED_ACTIONS
        return False

    def _bypass_confirmation(self, req: DesktopAction) -> bool:
        # Voice provenance is not an authorization credential.  Kept as a
        # method for compatibility, but live confirmation is never bypassed.
        return False

    def _is_voice_request(self, req: DesktopAction) -> bool:
        return str(req.source or "").startswith("voice:")

    def _record_result(self, result: DesktopActionResult) -> None:
        data = asdict(result)
        data["params"] = self._redact_params(data.get("params") or {})
        self.last_result = dict(data)
        self.recent_actions.append(data)
        if len(self.recent_actions) > self.max_recent_actions:
            self.recent_actions = self.recent_actions[-self.max_recent_actions :]
        self._persist_state()

    def _load_state(self) -> None:
        if not self.state_path.exists():
            return
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return

        # Arming and live mode are deliberately process-local.  A restart must
        # always return to disarmed dry-run even if an older state file says
        # otherwise.
        self.armed = False
        self.dry_run = True
        self.last_error = str(payload.get("last_error") or "")
        self.last_result = dict(payload.get("last_result") or {})
        self.pending_actions = list(payload.get("pending_actions") or [])[-self.max_pending_actions :]
        self.recent_actions = list(payload.get("recent_actions") or [])[-self.max_recent_actions :]

        # Persisted configuration (can be overridden via env on next start).
        # Security configuration comes from this build/environment, never from
        # a writable runtime state file.

    def _persist_state(self) -> None:
        payload = {
            "generated_at": time.time(),
            "armed": False,
            "dry_run": True,
            "runtime_armed": self.armed,
            "runtime_dry_run": self.dry_run,
            "pyautogui_available": HAS_PYAUTOGUI,
            "emergency_stopped": self.is_emergency_stopped(),
            "require_confirmation": self.require_confirmation,
            "auto_approve_live_voice": self.auto_approve_live_voice,
            "allowed_actions": sorted(ALLOWED_ACTIONS),
            "auto_execute_actions": sorted(AUTO_EXECUTE_ACTIONS),
            "last_error": self.last_error,
            "last_result": self._redact_action(self.last_result),
            "pending_actions": [self._redact_action(item) for item in self.pending_actions[-10:]],
            "recent_actions": [self._redact_action(item) for item in self.recent_actions[-10:]],
        }
        try:
            self.state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Could not persist desktop control state: %s", e)

    @staticmethod
    def _redact_params(params: Dict[str, Any]) -> Dict[str, Any]:
        clean = dict(params)
        if "text" in clean:
            text = str(clean.pop("text"))
            clean["text_redacted"] = True
            clean["text_length"] = len(text)
        if "confirm_token" in clean:
            clean["confirm_token"] = "[redacted]"
        return clean

    @classmethod
    def _redact_action(cls, item: Dict[str, Any]) -> Dict[str, Any]:
        clean = dict(item)
        clean["params"] = cls._redact_params(dict(clean.get("params") or {}))
        if clean.get("confirm_token"):
            clean["confirm_token"] = "[redacted]"
        return clean


def build_default_controller(dry_run: bool = True) -> SafeDesktopControl:
    return SafeDesktopControl(dry_run=dry_run)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ctl = build_default_controller(dry_run=True)
    print(json.dumps(ctl.status(), indent=2))

