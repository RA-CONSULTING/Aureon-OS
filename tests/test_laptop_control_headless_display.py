"""A missing DISPLAY must not crash the laptop HAL.

pyautogui's X11 backend indexes ``os.environ['DISPLAY']`` while it is
imported. On a Linux host with no screen that is ``KeyError: 'DISPLAY'``.
Importing the HAL must not load pyautogui. The first GUI call reports the
GUI unavailable.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _env(extra: str = "") -> dict[str, str]:
    env = os.environ.copy()
    env.pop("DISPLAY", None)
    env.pop("WAYLAND_DISPLAY", None)
    env["PYTHONPATH"] = f"{extra}{os.pathsep}{ROOT}" if extra else str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = "/usr/bin:/bin"
    return env


def test_import_with_display_unset_does_not_load_pyautogui_and_reports_unavailable() -> None:
    """Goes red if the HAL imports pyautogui up front, or if KeyError escapes."""

    script = textwrap.dedent(
        """\
        import json, os, sys
        os.environ.pop("DISPLAY", None)
        os.environ.pop("WAYLAND_DISPLAY", None)
        from aureon.autonomous import aureon_laptop_control as m
        loaded_at_import = "pyautogui" in sys.modules
        shot = m.LaptopControl().screenshot()
        print(json.dumps({
            "loaded_at_import": loaded_at_import,
            "success": shot["success"],
            "error": shot["error"],
            "available": m.HAS_PYAUTOGUI,
        }))
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=_env(),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["loaded_at_import"] is False
    assert payload["success"] is False
    assert payload["available"] is False
    assert payload["error"] == "pyautogui not available"
    assert "DISPLAY" not in payload["error"]


def test_laptop_import_does_not_touch_pyautogui_until_a_gui_call(tmp_path: Path) -> None:
    """Goes red if the HAL imports pyautogui while the module is loading."""

    site = tmp_path / "site"
    site.mkdir()
    marker = tmp_path / "pyautogui-loaded"
    (site / "pyautogui.py").write_text(
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('loaded', encoding='utf-8')\n"
        'raise KeyError("DISPLAY")\n',
        encoding="utf-8",
    )
    script = textwrap.dedent(
        f"""\
        import json, os
        from pathlib import Path
        os.environ.pop("DISPLAY", None)
        from aureon.autonomous import aureon_laptop_control as m
        loaded_at_import = Path({str(marker)!r}).is_file()
        shot = m.LaptopControl().screenshot()
        print(json.dumps({{
            "loaded_at_import": loaded_at_import,
            "loaded_after_call": Path({str(marker)!r}).is_file(),
            "success": shot["success"],
            "error": shot["error"],
            "available": m.HAS_PYAUTOGUI,
        }}))
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=site,
        env=_env(str(site)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload == {
        "loaded_at_import": False,
        "loaded_after_call": True,
        "success": False,
        "error": "pyautogui not available",
        "available": False,
    }


def test_loader_turns_a_missing_display_into_import_error(tmp_path: Path) -> None:
    """Goes red if import_pyautogui lets KeyError: 'DISPLAY' escape."""

    site = tmp_path / "site"
    site.mkdir()
    (site / "pyautogui.py").write_text('raise KeyError("DISPLAY")\n', encoding="utf-8")
    script = textwrap.dedent(
        """\
        import json, os
        os.environ.pop("DISPLAY", None)
        from aureon.autonomous.pyautogui_loader import import_pyautogui
        try:
            import_pyautogui()
            out = {"raised": None}
        except ImportError as exc:
            out = {"raised": "ImportError", "msg": str(exc)}
        except KeyError as exc:
            out = {"raised": "KeyError", "msg": str(exc)}
        print(json.dumps(out))
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        cwd=site,
        env=_env(str(site)),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    payload = json.loads(proc.stdout.strip().splitlines()[-1])
    assert payload["raised"] == "ImportError"
    assert "DISPLAY" in payload["msg"]
