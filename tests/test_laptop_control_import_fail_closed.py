"""aureon_laptop_control import failure modes that must stay closed.

``import sounddevice`` raises ``OSError`` ('PortAudio library not found') when
the host has no PortAudio library. That is not an ``ImportError``. The module
import must survive and report sounddevice unavailable.

The pyautogui import must go through ``import_pyautogui`` from #374. On Linux,
a plain ``import pyautogui`` loads mouseinfo, which calls ``sys.exit()`` when
tkinter is missing, and the ``except ImportError`` around that import does not
catch ``SystemExit``. These tests use stand-in modules in a subprocess, so
they need no display, no PortAudio, and no real pyautogui.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_EXIT_MSG = "NOTE: You must install tkinter on Linux to use MouseInfo."


def _run(site: Path, code: str) -> subprocess.CompletedProcess[str]:
    env = {
        "PYTHONPATH": f"{site}{os.pathsep}{REPO_ROOT}",
        "PATH": "/usr/bin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(site),
        timeout=120,
    )


def test_laptop_control_uses_safe_pyautogui_loader(tmp_path: Path) -> None:
    site = tmp_path / "fake_site"
    site.mkdir()
    (site / "tkinter.py").write_text("raise ImportError('No module named _tkinter')\n")
    (site / "mouseinfo.py").write_text(
        "import sys\n"
        "try:\n    import tkinter\n"
        f"except ImportError:\n    sys.exit({_EXIT_MSG!r})\n"
    )
    (site / "pyautogui.py").write_text(
        textwrap.dedent(
            """\
            import mouseinfo  # real pyautogui does this at import time
            FAILSAFE = False
            PAUSE = 0.0
            """
        )
    )
    proc = _run(
        site,
        """
        import json, sys
        from aureon.autonomous import aureon_laptop_control as m
        mouseinfo = sys.modules["mouseinfo"]
        print(json.dumps({
            "alive": True,
            "has_pyautogui": m.HAS_PYAUTOGUI,
            "shim": bool(getattr(mouseinfo, "__aureon_shim__", False)),
        }))
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload == {"alive": True, "has_pyautogui": True, "shim": True}


def test_laptop_control_imports_when_sounddevice_raises_oserror(tmp_path: Path) -> None:
    site = tmp_path / "fake_site"
    site.mkdir()
    (site / "sounddevice.py").write_text("raise OSError('PortAudio library not found')\n")
    proc = _run(
        site,
        """
        import json
        from aureon.autonomous import aureon_laptop_control as m
        print(json.dumps({
            "alive": True,
            "has_sounddevice": m.HAS_SOUNDDEVICE,
            "sounddevice_is_none": m.sounddevice is None,
        }))
        """,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload == {"alive": True, "has_sounddevice": False, "sounddevice_is_none": True}
