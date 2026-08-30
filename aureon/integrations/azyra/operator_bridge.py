"""Azyra operator bridge — gated local-desktop control for the Azyra WMS RemoteApp.

This is the ONLY sanctioned route for Aureon to touch live warehouse records:
every mouse click, keystroke, and submit runs through explicit gates
(``AZYRA_OPERATOR_ALLOW_INPUT`` / ``ALLOW_SUBMIT`` / ``ALLOW_FOCUS`` and the
keyboard-route-proven flag), and every refused action is reported honestly with
named blockers (``input_gate_disabled``, ``submit_gate_disabled``,
``keyboard_route_not_safe``, ``desktop_backend_unavailable``, …) instead of a
pretend success. On a headless host (CI, the cloud runner) the desktop backend
is absent, so the bridge stays fully importable and observable — status,
capabilities, and diagnostics are real — while every live action refuses.

See ``docs/azyra_warehouse_admin_reality_check.md`` for the production
contract: a dry run or a blocked preflight NEVER counts as a stock change.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Sequence

TRUTHY = {"1", "true", "yes", "y", "on"}


def _env_true(name: str) -> bool:
    return str(os.getenv(name) or "").strip().lower() in TRUTHY


@dataclass
class ActionResult:
    """Outcome of one bridge action. ``ok=False`` always carries blockers."""

    ok: bool
    action: str
    detail: str = ""
    blockers: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "action": self.action,
            "detail": self.detail,
            "blockers": list(self.blockers),
            "data": dict(self.data),
            "at": self.at,
        }


class DesktopBackend:
    """Best-effort desktop input backend.

    Resolution order follows ``AUREON_DESKTOP_INPUT_BACKEND`` (pydirectinput,
    then pyautogui). When neither library — or no display — is available the
    backend reports itself unavailable and every primitive refuses. It never
    fabricates a success.
    """

    def __init__(self) -> None:
        self.name: str | None = None
        self._impl: Any = None
        preferred = str(os.getenv("AUREON_DESKTOP_INPUT_BACKEND") or "").strip().lower()
        order = [preferred] if preferred else []
        order += [b for b in ("pydirectinput", "pyautogui") if b not in order]
        for candidate in order:
            if not candidate:
                continue
            try:
                self._impl = __import__(candidate)
                self.name = candidate
                break
            except Exception:
                continue

    @property
    def available(self) -> bool:
        return self._impl is not None

    def blockers(self) -> List[str]:
        return [] if self.available else ["desktop_backend_unavailable"]

    def foreground_window(self) -> Dict[str, Any]:
        """Return the current foreground window title/handle when knowable."""
        try:
            import ctypes  # Windows-only route

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return {"available": True, "handle": int(hwnd), "title": buf.value}
        except Exception:
            return {"available": False, "handle": None, "title": ""}

    def click(self, x: int, y: int) -> bool:
        if not self.available:
            return False
        self._impl.click(x=int(x), y=int(y))
        return True

    def hotkey(self, keys: Sequence[str]) -> bool:
        if not self.available:
            return False
        self._impl.hotkey(*[str(k) for k in keys])
        return True

    def type_text(self, text: str) -> bool:
        if not self.available:
            return False
        self._impl.typewrite(str(text)) if hasattr(self._impl, "typewrite") else self._impl.write(str(text))
        return True

    def screenshot(self, path: Path) -> bool:
        try:
            import PIL.ImageGrab  # noqa: F401  (pillow present?)
            from PIL import ImageGrab

            img = ImageGrab.grab()
            path.parent.mkdir(parents=True, exist_ok=True)
            img.save(str(path))
            return True
        except Exception:
            return False


def _find_process(query: str) -> Dict[str, Any]:
    """Look for a running process whose name/cmdline contains ``query``."""
    query = str(query or "").strip().lower()
    if not query:
        return {"found": False, "pids": []}
    pids: List[int] = []
    try:
        if shutil.which("pgrep"):
            out = subprocess.run(
                ["pgrep", "-f", query], capture_output=True, text=True, timeout=5
            )
            pids = [int(p) for p in out.stdout.split() if p.strip().isdigit()]
        else:  # Windows fallback via tasklist
            out = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=10)
            pids = [1] if query in out.stdout.lower() else []
    except Exception:
        pids = []
    return {"found": bool(pids), "pids": pids}


class AzyraOperatorBridge:
    """Gated bridge between Aureon and the Azyra WMS desktop session.

    Gates (constructor args OR the matching environment flags):

    * ``allow_focus`` / ``AZYRA_OPERATOR_ALLOW_FOCUS`` — may bring windows forward
    * ``allow_input`` / ``AZYRA_OPERATOR_ALLOW_INPUT`` — may move the mouse / type
    * ``allow_submit`` / ``AZYRA_OPERATOR_ALLOW_SUBMIT`` — may press submit/post keys
    * ``remoteapp_keyboard_route_proven`` /
      ``AZYRA_OPERATOR_REMOTEAPP_KEYBOARD_ROUTE_PROVEN`` — the RemoteApp keyboard
      route has a recorded proof for this session

    Nothing live happens until ``arm(live=True)`` succeeds, and arming itself
    refuses when the gates or the desktop backend are missing.
    """

    def __init__(
        self,
        window_title: str = "Azyra",
        process_query: str = "msrdc",
        allow_input: bool | None = None,
        allow_submit: bool | None = None,
        allow_focus: bool | None = None,
        remoteapp_keyboard_route_proven: bool | None = None,
    ) -> None:
        self.window_title = str(window_title or "Azyra")
        self.process_query = str(process_query or "")
        self.allow_input = _env_true("AZYRA_OPERATOR_ALLOW_INPUT") if allow_input is None else bool(allow_input)
        self.allow_submit = _env_true("AZYRA_OPERATOR_ALLOW_SUBMIT") if allow_submit is None else bool(allow_submit)
        self.allow_focus = _env_true("AZYRA_OPERATOR_ALLOW_FOCUS") if allow_focus is None else bool(allow_focus)
        if remoteapp_keyboard_route_proven is None:
            self.keyboard_route_proven = _env_true("AZYRA_OPERATOR_REMOTEAPP_KEYBOARD_ROUTE_PROVEN")
        else:
            self.keyboard_route_proven = bool(remoteapp_keyboard_route_proven)
        self.backend = DesktopBackend()
        self._armed_live = False
        self._action_log: List[Dict[str, Any]] = []

    # ── gates / observability ────────────────────────────────────────────────

    def _gate_blockers(self, *, need_input: bool = False, need_submit: bool = False,
                       need_focus: bool = False, need_keyboard: bool = False) -> List[str]:
        blockers = list(self.backend.blockers())
        if need_focus and not self.allow_focus:
            blockers.append("focus_gate_disabled")
        if need_input and not self.allow_input:
            blockers.append("input_gate_disabled")
        if need_submit and not self.allow_submit:
            blockers.append("submit_gate_disabled")
        if need_keyboard and not self.keyboard_route_proven:
            blockers.append("keyboard_route_not_safe")
        if (need_input or need_submit) and not self._armed_live:
            blockers.append("bridge_not_armed_live")
        return blockers

    def arm(self, live: bool = False) -> ActionResult:
        """Arm the bridge. Live arming requires the input gate and a backend."""
        if not live:
            self._armed_live = False
            return self._record(ActionResult(True, "arm", "armed for dry-run observation only"))
        blockers = list(self.backend.blockers())
        if not self.allow_input:
            blockers.append("input_gate_disabled")
        if blockers:
            self._armed_live = False
            return self._record(ActionResult(False, "arm", "live arming refused", blockers))
        self._armed_live = True
        return self._record(ActionResult(True, "arm", "armed LIVE — actions will touch the desktop"))

    def status(self) -> Dict[str, Any]:
        window = self.backend.foreground_window()
        process = _find_process(self.process_query)
        return {
            "schema_version": "azyra-operator-bridge-status-v1",
            "window_title_expected": self.window_title,
            "foreground_window": window,
            "window_focused": self.window_title.lower() in str(window.get("title") or "").lower(),
            "process_query": self.process_query,
            "process": process,
            "armed_live": self._armed_live,
            "gates": {
                "allow_focus": self.allow_focus,
                "allow_input": self.allow_input,
                "allow_submit": self.allow_submit,
                "keyboard_route_proven": self.keyboard_route_proven,
            },
            "backend": {"name": self.backend.name, "available": self.backend.available},
            "action_count": len(self._action_log),
        }

    def capabilities(self) -> Dict[str, Any]:
        """What the bridge can genuinely do right now, with per-action blockers."""
        return {
            "schema_version": "azyra-operator-bridge-capabilities-v1",
            "observe": {"allowed_now": True, "blockers": []},
            "focus": self._capability(need_focus=True),
            "click": self._capability(need_input=True),
            "type_text": self._capability(need_input=True, need_keyboard=True),
            "hotkey": self._capability(need_input=True, need_keyboard=True),
            "submit": self._capability(need_input=True, need_submit=True, need_keyboard=True),
            "capture_screen": {
                "allowed_now": self.backend.available,
                "blockers": self.backend.blockers(),
            },
        }

    def _capability(self, **needs: bool) -> Dict[str, Any]:
        blockers = self._gate_blockers(**needs)
        return {"allowed_now": not blockers, "blockers": blockers}

    def input_route_diagnostics(self) -> Dict[str, Any]:
        """The honest preflight the warehouse runbook requires before live typing."""
        blockers = self._gate_blockers(need_input=True, need_keyboard=True)
        return {
            "schema_version": "azyra-operator-input-route-diagnostics-v1",
            "backend": self.backend.name,
            "backend_available": self.backend.available,
            "keyboard_route_proven": self.keyboard_route_proven,
            "armed_live": self._armed_live,
            "blockers": blockers,
            "live_typing_ready": not blockers,
        }

    # ── actions (all gated, all honest) ──────────────────────────────────────

    def focus(self) -> ActionResult:
        blockers = self._gate_blockers(need_focus=True)
        if blockers:
            return self._record(ActionResult(False, "focus", "focus refused", blockers))
        window = self.backend.foreground_window()
        ok = self.window_title.lower() in str(window.get("title") or "").lower()
        return self._record(ActionResult(
            ok, "focus",
            "target window already foreground" if ok else "target window not in foreground",
            [] if ok else ["target_window_not_foreground"],
            {"foreground": window},
        ))

    def click_window(self, x: int, y: int, submit_like: bool = False) -> ActionResult:
        blockers = self._gate_blockers(need_input=True, need_submit=submit_like)
        if blockers:
            return self._record(ActionResult(False, "click_window", "click refused", blockers,
                                             {"x": x, "y": y, "submit_like": submit_like}))
        ok = self.backend.click(x, y)
        return self._record(ActionResult(ok, "click_window",
                                         "clicked" if ok else "backend click failed",
                                         [] if ok else ["backend_click_failed"],
                                         {"x": x, "y": y, "submit_like": submit_like}))

    def hotkey(self, keys: Sequence[str]) -> ActionResult:
        blockers = self._gate_blockers(need_input=True, need_keyboard=True)
        if blockers:
            return self._record(ActionResult(False, "hotkey", "hotkey refused", blockers, {"keys": list(keys)}))
        ok = self.backend.hotkey(keys)
        return self._record(ActionResult(ok, "hotkey", "sent" if ok else "backend hotkey failed",
                                         [] if ok else ["backend_hotkey_failed"], {"keys": list(keys)}))

    def type_text(self, text: str, method: str = "type") -> ActionResult:
        blockers = self._gate_blockers(need_input=True, need_keyboard=True)
        if blockers:
            return self._record(ActionResult(False, "type_text", "typing refused", blockers,
                                             {"length": len(str(text)), "method": method}))
        ok = self.backend.type_text(str(text))
        return self._record(ActionResult(ok, "type_text", "typed" if ok else "backend typing failed",
                                         [] if ok else ["backend_type_failed"],
                                         {"length": len(str(text)), "method": method}))

    def capture_screen(self, path: Path, window_only: bool = False) -> ActionResult:
        target = Path(path)
        ok = self.backend.screenshot(target)
        return self._record(ActionResult(ok, "capture_screen",
                                         "captured" if ok else "screen capture unavailable on this host",
                                         [] if ok else ["screen_capture_unavailable"],
                                         {"path": str(target), "window_only": window_only}))

    def run_workflow(self, steps: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        """Run a declarative step list through the gated primitives.

        Every step is preflighted; the workflow stops at the first refusal so a
        half-typed record can never be silently submitted.
        """
        results: List[Dict[str, Any]] = []
        for i, step in enumerate(steps or []):
            kind = str(step.get("action") or "")
            if kind == "focus":
                res = self.focus()
            elif kind == "click":
                res = self.click_window(int(step.get("x", 0)), int(step.get("y", 0)),
                                        submit_like=bool(step.get("submit_like")))
            elif kind == "hotkey":
                res = self.hotkey(list(step.get("keys") or []))
            elif kind == "type_text":
                res = self.type_text(str(step.get("text") or ""), method=str(step.get("method") or "type"))
            elif kind == "capture":
                res = self.capture_screen(Path(str(step.get("path") or "azyra_capture.png")))
            else:
                res = ActionResult(False, "run_workflow", f"unknown step action: {kind!r}",
                                   ["unknown_step_action"], {"index": i})
            results.append(res.to_dict())
            if not res.ok:
                break
        ok = bool(results) and all(r["ok"] for r in results)
        return {
            "schema_version": "azyra-operator-workflow-result-v1",
            "ok": ok,
            "steps_requested": len(list(steps or [])),
            "steps_executed": len(results),
            "results": results,
            "stopped_early": len(results) < len(list(steps or [])),
        }

    def action_log(self) -> List[Dict[str, Any]]:
        return list(self._action_log)

    def _record(self, result: ActionResult) -> ActionResult:
        self._action_log.append(result.to_dict())
        return result


__all__ = ["ActionResult", "AzyraOperatorBridge", "DesktopBackend"]
