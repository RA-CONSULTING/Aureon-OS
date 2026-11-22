"""Opt-in real-display test for Aureon's desktop control layer.

Skipped unless BOTH ``AUREON_REAL_DISPLAY_TEST`` and ``DISPLAY`` are set (and
the host is Linux with pyautogui, python-xlib and Pillow installed).  It drives
the real pointer and keyboard of ``$DISPLAY``, so point it at a throwaway
virtual display only, never a desktop someone is using::

    Xvfb :42 -screen 0 1280x800x24 -nolisten tcp &
    AUREON_REAL_DISPLAY_TEST=1 DISPLAY=:42 \
    AUREON_REAL_DISPLAY_ARTIFACTS=/tmp/aureon_real_display \
        python -m pytest -q tests/test_real_display_desktop_control.py

Each scenario runs in its own interpreter (``tests/real_display_driver.py``)
against a tiny python-xlib window (``tests/real_display_testpad.py``) whose
state is read back from a JSON file; screenshots are written to
``AUREON_REAL_DISPLAY_ARTIFACTS`` (default: pytest's tmp dir).

It pins only behaviour that survives the move to full autonomy (no arming,
dry-run or confirmation refusals are asserted; the driver passes those
credentials only when the build still has them):

* import safety: importing the controllers never exits the process
  (pyautogui -> mouseinfo calls sys.exit() on Linux hosts without tkinter);
* real clicks, typing and Enter land on the display and are read back, through
  both SafeDesktopControl and GovernedDesktopGateway (host default backend);
* every action is written to the audit log (controller state
  ``recent_actions``; gateway evidence JSONL with before/after frame hashes),
  and typed text is not written to either;
* the kill-switch file stops SafeDesktopControl's next action - kept as its
  own test so it can be dropped independently.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TEXT = "hello aureon 42"

pytestmark = [
    pytest.mark.skipif(
        not (os.environ.get("AUREON_REAL_DISPLAY_TEST") and os.environ.get("DISPLAY")),
        reason="opt-in: set AUREON_REAL_DISPLAY_TEST=1 and DISPLAY to a throwaway X display",
    ),
    pytest.mark.skipif(not sys.platform.startswith("linux"), reason="X11 real-display test"),
    pytest.mark.skipif(
        any(importlib.util.find_spec(m) is None for m in ("pyautogui", "Xlib", "PIL")),
        reason="needs pyautogui, python-xlib and Pillow",
    ),
]


def _run(scenario: str, tmp_path: Path) -> dict:
    proc = subprocess.run(
        [sys.executable, str(HERE / "real_display_driver.py"), scenario, str(tmp_path)],
        capture_output=True,
        text=True,
        timeout=180,
        env=dict(os.environ),
    )
    lines = [line for line in proc.stdout.splitlines() if line.startswith("RESULT ")]
    assert proc.returncode == 0 and lines, (
        f"driver {scenario!r} exited {proc.returncode}\n"
        f"stdout tail:\n{proc.stdout[-1500:]}\nstderr tail:\n{proc.stderr[-3000:]}"
    )
    return json.loads(lines[-1][len("RESULT "):])


def test_importing_desktop_controllers_never_exits_the_process(tmp_path: Path) -> None:
    result = _run("import", tmp_path)
    assert result == {"alive": True, "has_pyautogui": True}


def test_safe_desktop_control_clicks_and_types_on_real_display(tmp_path: Path) -> None:
    r = _run("safe_controller", tmp_path)

    assert (r["click"]["ok"], r["click"]["clicks"]) == (True, 1)
    assert r["focus"]["ok"] is True
    assert (r["type"]["ok"], r["type"]["text"]) == (True, TEXT)
    assert (r["enter"]["ok"], r["enter"]["submitted"]) == (True, [TEXT])
    # Every action is in the controller's persisted log, without the typed text.
    assert [tuple(a) for a in r["log_actions"][-4:]] == [
        ("left_click", True), ("left_click", True), ("type_text", True), ("press_key", True)
    ]
    assert r["log_contains_typed_text"] is False
    for key in ("png_before", "png_after"):
        assert Path(r[key]).stat().st_size > 0


def test_safe_desktop_control_kill_switch_file_stops_next_action(tmp_path: Path) -> None:
    r = _run("safe_kill_switch", tmp_path)

    assert r["before_stop"] == {"ok": True, "clicks": 1}
    assert r["after_stop"] == {"ok": False, "reason": "emergency_stop_active", "unchanged": True}
    assert r["log_last"] == "emergency_stop_active"
    assert Path(r["png_stop"]).stat().st_size > 0


def test_governed_desktop_gateway_clicks_and_types_on_real_display(tmp_path: Path) -> None:
    r = _run("gateway", tmp_path)

    assert r["binding_pid_matches"] is True
    for name, step in r["steps"].items():
        assert step["ok"] is True, (name, step["reason"])
    assert r["steps"]["click"]["clicks"] == 1
    assert r["steps"]["click"]["before"] != r["steps"]["click"]["after"]
    assert r["steps"]["type"]["text"] == TEXT
    assert r["steps"]["enter"]["submitted"] == [TEXT]
    # Every action has a completed audit record with before/after frame hashes.
    assert r["audited"] == {"click": True, "focus": True, "type": True, "enter": True}
    assert r["evidence_contains_typed_text"] is False
    for key in ("png_before", "png_after", "png_after_masked_observation"):
        assert Path(r[key]).stat().st_size > 0
