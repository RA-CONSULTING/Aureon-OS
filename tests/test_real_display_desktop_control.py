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

It covers:
* import safety: importing the controllers never exits the process
  (pyautogui -> mouseinfo calls sys.exit() on Linux hosts without tkinter);
* SafeDesktopControl: dry-run moves nothing, approved live click/type land,
  propose(press_key) is queued for confirmation and runs via approve_next,
  the kill-switch file refuses the next action;
* GovernedDesktopGateway (default backend for the host): exact window binding,
  dry-run, one-time capability token + time-limited lease, before-hash /
  stale-frame / lease-scope refusals, live click/type/press with before/after
  evidence and redaction, emergency stop, lease expiry.
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


def test_safe_desktop_control_on_real_display(tmp_path: Path) -> None:
    r = _run("safe_controller", tmp_path)

    assert r["dry_run"]["status"] == "executed"
    assert r["dry_run"]["clicks"] == 0
    assert r["dry_run"]["pointer"] == [5, 5]

    assert (r["live_click"]["ok"], r["live_click"]["reason"], r["live_click"]["clicks"]) == (True, "executed", 1)
    assert (r["live_type"]["ok"], r["live_type"]["text"]) == (True, TEXT)

    # press_key is high-risk: propose() must queue it, approve_next(token) runs it.
    assert r["propose_press_key"]["proposed_status"] == "pending"
    assert (r["propose_press_key"]["approve_ok"], r["propose_press_key"]["approve_reason"]) == (True, "executed")
    assert r["propose_press_key"]["submitted"] == [TEXT]

    assert r["stop_file"] == {"ok": False, "reason": "emergency_stop_active", "unchanged": True}
    for key in ("png_before", "png_after", "png_stop"):
        assert Path(r[key]).stat().st_size > 0


def test_governed_desktop_gateway_on_real_display(tmp_path: Path) -> None:
    r = _run("gateway", tmp_path)

    assert r["binding"]["pid"] > 0
    assert (r["dry_run"]["ok"], r["dry_run"]["reason"], r["dry_run"]["dry_run"]) == (True, "dry_run", True)
    assert r["dry_run"]["clicks"] == 0

    assert r["token_replay"] == "capability_token_already_consumed"
    assert r["live_without_before_hash"] == "expected_before_sha256_required"
    assert r["live_stale_hash"] == "stale_source_frame"
    assert r["outside_lease_scope"] == "action_outside_lease_scope"
    assert r["clicks_after_refusals"] == 0

    for step in ("live_click", "live_focus", "live_type", "live_enter"):
        assert (r[step]["ok"], r[step]["reason"], r[step]["dry_run"]) == (True, "executed", False), step
        assert r[step]["before"] and r[step]["after"], step
    assert r["live_click"]["before"] != r["live_click"]["after"]
    assert r["live_click"]["clicks"] == 1
    assert r["live_type"]["text"] == TEXT
    assert r["live_enter"]["submitted"] == [TEXT]

    assert r["after_emergency_stop"]["ok"] is False
    assert r["after_emergency_stop"]["reason"] in {"emergency_stop_active", "valid_target_window_binding_required"}
    assert r["after_emergency_stop"]["unchanged"] is True
    assert r["after_lease_expiry"] == "active_authorization_lease_required"

    assert {"authorization_issued", "target_window_bound", "action_started", "action_completed",
            "emergency_stop"} <= set(r["evidence_events"])
    assert r["live_completed_with_before_after"] >= 4
    assert r["evidence_contains_typed_text"] is False
    assert r["evidence_contains_token"] is False
    for key in ("png_before", "png_after", "png_after_masked_observation", "png_stop"):
        assert Path(r[key]).stat().st_size > 0
