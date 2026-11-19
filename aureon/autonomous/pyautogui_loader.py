"""Import pyautogui without letting a host dependency end the process.

On Linux, ``pyautogui`` imports ``mouseinfo``, and ``mouseinfo`` calls
``sys.exit()`` at import time when ``tkinter`` is not installed.  Every Aureon
desktop module guarded that import with ``except Exception`` or
``except ImportError``, neither of which catches ``SystemExit``, so merely
importing ``aureon_safe_desktop_control`` on such a host terminated the whole
process (exit status 1).

``import_pyautogui`` fixes both halves:

* when ``tkinter`` is unavailable it registers a tiny ``mouseinfo`` shim first.
  ``mouseinfo`` is only used by pyautogui's interactive ``mouseInfo()`` helper,
  never by mouse/keyboard/screenshot calls, so Linux hosts and CI no longer need
  tkinter just to drive the pointer;
* any ``SystemExit`` raised while importing is converted to ``ImportError`` so
  callers fail closed (``pyautogui_available = False``) instead of exiting.
"""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

MOUSEINFO_SHIM_NAME = "mouseinfo"


def _tkinter_available() -> bool:
    try:
        import tkinter  # noqa: F401
    except Exception:
        return False
    return True


def _mouseinfo_shim() -> types.ModuleType:
    shim = types.ModuleType(MOUSEINFO_SHIM_NAME)
    shim.__doc__ = "Aureon shim: mouseinfo needs tkinter, which this host lacks."
    shim.__aureon_shim__ = True  # type: ignore[attr-defined]

    def MouseInfoWindow(*_args: Any, **_kwargs: Any) -> None:  # noqa: N802
        raise RuntimeError("mouseinfo_unavailable_without_tkinter")

    shim.MouseInfoWindow = MouseInfoWindow  # type: ignore[attr-defined]
    return shim


def install_mouseinfo_shim_if_needed() -> bool:
    """Register the shim when tkinter is missing.  Returns True if installed."""

    if MOUSEINFO_SHIM_NAME in sys.modules or "pyautogui" in sys.modules:
        return False
    if _tkinter_available():
        return False
    sys.modules[MOUSEINFO_SHIM_NAME] = _mouseinfo_shim()
    return True


def import_pyautogui() -> Any:
    """Return the pyautogui module or raise ``ImportError``; never exit."""

    install_mouseinfo_shim_if_needed()
    try:
        return importlib.import_module("pyautogui")
    except SystemExit as exc:
        raise ImportError(f"pyautogui_import_exited:{exc}") from None
