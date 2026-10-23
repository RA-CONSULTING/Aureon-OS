"""
SimulatedVMController — In-Memory VM Simulation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A fully in-memory VM simulation that maintains a fake desktop state:
  - Cursor position tracker
  - Synthetic screen buffer with deterministic content
  - Mock window list
  - Typed text log
  - Shell command log with canned responses

Used for:
  - Unit tests + stress tests (no real VM required)
  - Development + dry-run rehearsals
  - CI/CD pipelines where a real VM isn't available
"""

from __future__ import annotations

import base64
import hashlib
import time
from typing import Any, Dict, List, Optional, Tuple

from aureon.autonomous.vm_control.base import VMController


class SimulatedVMController(VMController):
    """In-memory simulated Windows VM."""

    DEFAULT_SCREEN_WIDTH = 1920
    DEFAULT_SCREEN_HEIGHT = 1080

    def __init__(
        self,
        session_id: Optional[str] = None,
        name: str = "simulated-vm",
        host: str = "localhost:sim",
        screen_width: int = DEFAULT_SCREEN_WIDTH,
        screen_height: int = DEFAULT_SCREEN_HEIGHT,
    ):
        super().__init__(session_id=session_id, name=name, host=host, dry_run=False)

        self._screen_w = screen_width
        self._screen_h = screen_height
        self._cursor_x = screen_width // 2
        self._cursor_y = screen_height // 2

        # Fake desktop state
        self._windows: List[Dict[str, Any]] = [
            {"title": "Desktop", "x": 0, "y": 0, "width": screen_width, "height": screen_height, "active": True},
            {"title": "File Explorer", "x": 100, "y": 100, "width": 1200, "height": 800, "active": False},
            {"title": "Task Manager", "x": 200, "y": 200, "width": 900, "height": 600, "active": False},
        ]
        self._typed_text: List[str] = []
        self._shell_log: List[Dict[str, Any]] = []
        self._click_log: List[Tuple[int, int, str]] = []
        self._frame_counter = 0

    def _backend_name(self) -> str:
        return "simulated"

    def health_check(self) -> bool:
        return True

    # ─────────────────────────────────────────────────────────────────────
    # Screen / cursor actions
    # ─────────────────────────────────────────────────────────────────────

    def _generate_fake_screen(self) -> str:
        """Generate a deterministic fake screen as base64."""
        self._frame_counter += 1
        # Synthesize a reproducible fingerprint of the current state
        fingerprint = f"{self._frame_counter}|{self._cursor_x},{self._cursor_y}|{len(self._windows)}|{len(self._typed_text)}"
        # Create a small fake PNG header + hash-based payload
        payload = hashlib.sha256(fingerprint.encode()).digest()
        # Prefix with a mock 8-byte PNG signature so it resembles an image
        fake_png = b"\x89PNG\r\n\x1a\n" + payload
        return base64.b64encode(fake_png).decode("ascii")

    def _do_screenshot(self, **kwargs) -> Dict[str, Any]:
        return {
            "image_b64": self._generate_fake_screen(),
            "format": "png",
            "width": self._screen_w,
            "height": self._screen_h,
            "cursor_x": self._cursor_x,
            "cursor_y": self._cursor_y,
            "frame": self._frame_counter,
        }

    def _do_mouse_move(self, x: int, y: int, **kwargs) -> Dict[str, Any]:
        self._cursor_x = max(0, min(int(x), self._screen_w))
        self._cursor_y = max(0, min(int(y), self._screen_h))
        return {"x": self._cursor_x, "y": self._cursor_y}

    def _click_at(self, x: Optional[int], y: Optional[int], kind: str) -> Dict[str, Any]:
        if x is not None and y is not None:
            self._cursor_x = max(0, min(int(x), self._screen_w))
            self._cursor_y = max(0, min(int(y), self._screen_h))
        self._click_log.append((self._cursor_x, self._cursor_y, kind))
        return {"x": self._cursor_x, "y": self._cursor_y, "kind": kind}

    def _do_left_click(self, x=None, y=None, **kwargs) -> Dict[str, Any]:
        return self._click_at(x, y, "left")

    def _do_right_click(self, x=None, y=None, **kwargs) -> Dict[str, Any]:
        return self._click_at(x, y, "right")

    def _do_middle_click(self, x=None, y=None, **kwargs) -> Dict[str, Any]:
        return self._click_at(x, y, "middle")

    def _do_double_click(self, x=None, y=None, **kwargs) -> Dict[str, Any]:
        return self._click_at(x, y, "double")

    def _do_triple_click(self, x=None, y=None, **kwargs) -> Dict[str, Any]:
        return self._click_at(x, y, "triple")

    def _do_left_click_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, **kwargs) -> Dict[str, Any]:
        self._cursor_x = max(0, min(int(end_x), self._screen_w))
        self._cursor_y = max(0, min(int(end_y), self._screen_h))
        self._click_log.append((self._cursor_x, self._cursor_y, "drag"))
        return {
            "start": [start_x, start_y],
            "end": [self._cursor_x, self._cursor_y],
        }

    def _do_scroll(self, x: int, y: int, direction: str = "down", amount: int = 3, **kwargs) -> Dict[str, Any]:
        return {
            "x": x,
            "y": y,
            "direction": direction,
            "amount": amount,
        }

    # ─────────────────────────────────────────────────────────────────────
    # Keyboard actions
    # ─────────────────────────────────────────────────────────────────────

    def _do_type_text(self, text: str, **kwargs) -> Dict[str, Any]:
        self._typed_text.append(str(text))
        return {"chars_typed": len(text), "total_buffered": len(self._typed_text)}

    def _do_press_key(self, key: str, **kwargs) -> Dict[str, Any]:
        return {"key": str(key)}

    def _do_hotkey(self, keys: List[str], **kwargs) -> Dict[str, Any]:
        return {"keys": list(keys), "combo": "+".join(keys)}

    # ─────────────────────────────────────────────────────────────────────
    # Screen info
    # ─────────────────────────────────────────────────────────────────────

    def _do_get_cursor_position(self, **kwargs) -> Dict[str, Any]:
        return {"x": self._cursor_x, "y": self._cursor_y}

    def _do_get_screen_size(self, **kwargs) -> Dict[str, Any]:
        return {"width": self._screen_w, "height": self._screen_h}

    # ─────────────────────────────────────────────────────────────────────
    # Window management
    # ─────────────────────────────────────────────────────────────────────

    def _do_list_windows(self, **kwargs) -> Dict[str, Any]:
        return {"windows": list(self._windows), "count": len(self._windows)}

    def _do_get_active_window(self, **kwargs) -> Dict[str, Any]:
        for w in self._windows:
            if w.get("active"):
                return {"window": dict(w)}
        return {"window": None}

    def _do_focus_window(self, title: str, **kwargs) -> Dict[str, Any]:
        title_lower = str(title).lower()
        found = False
        for w in self._windows:
            if title_lower in w["title"].lower():
                w["active"] = True
                found = True
            else:
                w["active"] = False
        return {"focused": found, "title": title}

    # ─────────────────────────────────────────────────────────────────────
    # Shell execution
    # ─────────────────────────────────────────────────────────────────────

    CANNED_RESPONSES: Dict[str, str] = {
        "whoami": "simulated\\user",
        "hostname": "sim-windows-vm",
        "ver": "Microsoft Windows [Version 10.0.19045.3693]",
        "echo hello": "hello",
        "dir": "Volume in drive C is Windows\n Directory of C:\\\n<DIR>  Users",
        "pwd": ".",
        "cd": ".",
    }

    def _do_execute_shell(self, command: str, timeout: int = 30, **kwargs) -> Dict[str, Any]:
        cmd = str(command).strip()
        stdout = self.CANNED_RESPONSES.get(cmd.lower(), f"[simulated] executed: {cmd}")
        entry = {
            "command": cmd,
            "stdout": stdout,
            "returncode": 0,
            "shell": "cmd",
            "timestamp": time.time(),
        }
        self._shell_log.append(entry)
        return entry

    def _do_execute_powershell(self, command: str, timeout: int = 30, **kwargs) -> Dict[str, Any]:
        cmd = str(command).strip()
        stdout = f"[simulated PS] {cmd}"
        if "Get-Process" in cmd:
            stdout = "Handles  NPM(K)    PM(K)      WS(K)     CPU(s)     Id ProcessName\n" \
                     "------  ------    -----      -----     ------     -- -----------\n" \
                     "   428      28    15324      22104       0.50   1234 explorer"
        elif "Get-ComputerInfo" in cmd:
            stdout = "WindowsProductName : Windows 10 Enterprise\nOsVersion : 10.0.19045"
        entry = {
            "command": cmd,
            "stdout": stdout,
            "returncode": 0,
            "shell": "powershell",
            "timestamp": time.time(),
        }
        self._shell_log.append(entry)
        return entry

    # ─────────────────────────────────────────────────────────────────────
    # Introspection (for tests)
    # ─────────────────────────────────────────────────────────────────────

    def get_click_log(self) -> List[Tuple[int, int, str]]:
        return list(self._click_log)

    def get_typed_text(self) -> List[str]:
        return list(self._typed_text)

    def get_shell_log(self) -> List[Dict[str, Any]]:
        return list(self._shell_log)
