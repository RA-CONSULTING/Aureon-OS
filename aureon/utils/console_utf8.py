#!/usr/bin/env python3
"""Windows UTF-8 console setup — explicit, opt-in, and safe to call anywhere.

Why this module exists
----------------------
The glyphs this system speaks in — φ, Λ, ✦, the Metatron and Flower-of-Life
box-drawing — need a UTF-8 console. On Windows the default code page is not
UTF-8, so ~250 modules in this repo each carried an inline copy of a fix that
ran at **import** time and did:

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', ...)

That is a session-killer under pytest. During collection ``sys.stdout`` is
pytest's capture object; the shim adopts *its* underlying tmpfile buffer and
installs the new wrapper as the global ``sys.stdout``. When pytest closes that
tmpfile at teardown the now-dangling wrapper raises

    ValueError: I/O operation on closed file

from inside ``_pytest/capture.py: snap()``, which aborts the entire session
(exit code 1) and destroys the report — even when every test passed. The
traceback names no test, so it is brutal to trace back to the importing module.

The fix is two-fold, and both halves matter:

1. **Never replace the stream object.** ``reconfigure()`` mutates the existing
   ``TextIOWrapper`` in place (Python 3.7+; this repo requires 3.11+), so
   nothing can be left dangling and no other component's handle goes stale.
2. **Never run at import time.** Callers opt in explicitly — from ``main()``
   or an equivalent entry point — so importing a module stays free of global
   side effects. Under pytest this is additionally a hard no-op.

Usage
-----
    from aureon.utils.console_utf8 import ensure_utf8_stdout

    def main() -> None:
        ensure_utf8_stdout()
        ...

Do **not** call this at module scope. That is the bug this module replaces.

This module imports nothing from the rest of the repo — it is a leaf, safe to
import from any package including ``aureon.core`` and ``aureon.utils``.
"""

from __future__ import annotations

import os
import sys

__all__ = ["ensure_utf8_stdout", "running_under_pytest"]

_APPLIED = False


def running_under_pytest() -> bool:
    """True when this process is a pytest run.

    ``PYTEST_CURRENT_TEST`` alone is not enough: it is set while a test *runs*,
    but module-level imports happen during *collection*, when it is absent —
    which is exactly when the old shim did its damage. ``'pytest' in
    sys.modules`` covers collection; the env var covers subprocesses that
    inherit it.
    """
    return "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ


def _reconfigure(stream: object) -> bool:
    """Switch one stream to UTF-8 in place. Never replaces the object."""
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        # Not a TextIOWrapper — e.g. a logging shim or a StringIO someone
        # installed. Wrapping it would be exactly the bug we are removing.
        return False
    try:
        reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    except Exception:
        # Closed, detached, or a wrapper that rejects the kwargs. Nothing to
        # do — degraded glyphs beat a crash.
        return False
    return True


def ensure_utf8_stdout(*, force: bool = False) -> bool:
    """Make ``sys.stdout``/``sys.stderr`` UTF-8 for interactive terminal output.

    Call this from ``main()`` / ``if __name__ == "__main__":``, never at import.

    Args:
        force: Apply even under pytest and even if already applied. For tests
            of this module itself; production callers should not pass it.

    Returns:
        True if either stream was reconfigured.
    """
    global _APPLIED

    if sys.platform == "win32":
        # Read at interpreter startup, so this does nothing for the current
        # process — it is inherited by child processes we spawn, which is what
        # the original inline shims were really buying. Safe under pytest.
        os.environ["PYTHONIOENCODING"] = "utf-8"

    # Escape hatch, kept from the blocks this replaced: force the reconfigure
    # even under pytest. Only reach for it if you know why you need it.
    force = force or os.getenv("AUREON_FORCE_UTF8_STDIO", "").strip().lower() in {
        "1", "true", "yes", "on",
    }

    if not force:
        if _APPLIED:
            return False
        if running_under_pytest():
            # Under pytest sys.stdout is the capture object. Leave it alone.
            return False

    changed = False
    for name in ("stdout", "stderr"):
        if _reconfigure(getattr(sys, name, None)):
            changed = True

    if not force:
        _APPLIED = True
    return changed
