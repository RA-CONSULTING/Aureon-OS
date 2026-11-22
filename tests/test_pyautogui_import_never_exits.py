"""pyautogui's import must never terminate an Aureon process.

On Linux, pyautogui imports mouseinfo, which calls ``sys.exit()`` when tkinter
is missing.  Before the fix, importing ``aureon_safe_desktop_control`` (or the
legacy laptop HAL) on such a host exited the interpreter with status 1, and the
governed gateway's lazy backend raised ``SystemExit`` past its
``except Exception`` guard.  These tests reproduce that host in a subprocess
with stand-in ``tkinter``/``mouseinfo``/``pyautogui`` modules, so they need no
display and no real pyautogui.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_EXIT_MSG = "NOTE: You must install tkinter on Linux to use MouseInfo."


def _fake_host(tmp_path: Path, *, pyautogui_body: str) -> Path:
    site = tmp_path / "fake_site"
    site.mkdir()
    # tkinter missing, exactly as on a headless Linux box / CI image.
    (site / "tkinter.py").write_text("raise ImportError('No module named _tkinter')\n")
    # mouseinfo behaves like the real package without tkinter.
    (site / "mouseinfo.py").write_text(
        "import sys\n"
        "try:\n    import tkinter\n"
        f"except ImportError:\n    sys.exit({_EXIT_MSG!r})\n"
    )
    (site / "pyautogui.py").write_text(textwrap.dedent(pyautogui_body))
    return site


def _run(site: Path, code: str) -> subprocess.CompletedProcess[str]:
    env = {
        "PYTHONPATH": f"{site}{__import__('os').pathsep}{REPO_ROOT}",
        "PATH": "/usr/bin:/bin",
        "AUREON_DESKTOP_CONTROL_STATE": str(site / "state.json"),
        "AUREON_DESKTOP_KILL_SWITCH": str(site / "stop"),
    }
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(site),
        timeout=120,
    )


_PYAUTOGUI_NEEDS_MOUSEINFO = """
    import mouseinfo  # real pyautogui does this at import time
    FAILSAFE = False
    PAUSE = 0.0
    def position():
        return (1, 2)
"""


def test_safe_desktop_control_import_survives_mouseinfo_exit(tmp_path: Path) -> None:
    site = _fake_host(tmp_path, pyautogui_body=_PYAUTOGUI_NEEDS_MOUSEINFO)
    proc = _run(
        site,
        """
        import json
        from aureon.autonomous import aureon_safe_desktop_control as m
        print(json.dumps({"alive": True, "has_pyautogui": m.HAS_PYAUTOGUI}))
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    # The mouseinfo shim lets pyautogui load without tkinter.
    assert payload == {"alive": True, "has_pyautogui": True}


def test_safe_desktop_control_fails_closed_when_pyautogui_itself_exits(tmp_path: Path) -> None:
    site = _fake_host(tmp_path, pyautogui_body="import sys\nsys.exit('display backend missing')\n")
    proc = _run(
        site,
        """
        import json
        from aureon.autonomous import aureon_safe_desktop_control as m
        c = m.SafeDesktopControl(dry_run=False)
        c.arm_live()
        r = c.execute(m.DesktopAction("left_click", {"x": 1, "y": 1}, approved=True))
        print(json.dumps({"has_pyautogui": m.HAS_PYAUTOGUI, "ok": r.ok, "reason": r.reason}))
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload == {"has_pyautogui": False, "ok": False, "reason": "pyautogui_not_available"}


def test_gateway_lazy_backend_converts_import_exit_to_backend_error(tmp_path: Path) -> None:
    site = _fake_host(tmp_path, pyautogui_body="import sys\nsys.exit('display backend missing')\n")
    proc = _run(
        site,
        """
        import json
        from aureon.autonomous.aureon_governed_desktop_gateway import (
            DesktopBackendError, LazyPyAutoGUIBackend,
        )
        try:
            LazyPyAutoGUIBackend()._pyautogui()
            out = {"raised": None}
        except DesktopBackendError as exc:
            out = {"raised": "DesktopBackendError", "reason": str(exc)}
        print(json.dumps(out))
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload == {"raised": "DesktopBackendError", "reason": "local_desktop_backend_unavailable"}


def test_gateway_lazy_backend_loads_pyautogui_without_tkinter(tmp_path: Path) -> None:
    site = _fake_host(tmp_path, pyautogui_body=_PYAUTOGUI_NEEDS_MOUSEINFO)
    proc = _run(
        site,
        """
        import json, sys
        from aureon.autonomous.aureon_governed_desktop_gateway import LazyPyAutoGUIBackend
        b = LazyPyAutoGUIBackend()
        print(json.dumps({"pos": list(b.pointer_position()),
                          "shim": bool(getattr(sys.modules["mouseinfo"], "__aureon_shim__", False))}))
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload == {"pos": [1, 2], "shim": True}


def test_loader_leaves_real_mouseinfo_alone_when_tkinter_present(tmp_path: Path) -> None:
    site = _fake_host(tmp_path, pyautogui_body=_PYAUTOGUI_NEEDS_MOUSEINFO)
    (site / "tkinter.py").write_text("TkVersion = 8.6\n")
    proc = _run(
        site,
        """
        import json, sys
        from aureon.autonomous.pyautogui_loader import import_pyautogui
        import_pyautogui()
        print(json.dumps({"shim": bool(getattr(sys.modules["mouseinfo"], "__aureon_shim__", False))}))
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert json.loads(proc.stdout.strip().splitlines()[-1]) == {"shim": False}
