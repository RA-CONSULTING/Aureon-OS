"""Wiring check: aureon.utils.console_utf8 (restored from Project-Sero) is importable.

58 call sites in this repo import it; before the restore every one hit ModuleNotFoundError.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_console_utf8_exports():
    from aureon.utils import console_utf8

    assert callable(console_utf8.ensure_utf8_stdout)
    assert console_utf8.running_under_pytest() is True


def test_ensure_utf8_stdout_in_fresh_process():
    code = (
        "import sys\n"
        "from aureon.utils.console_utf8 import ensure_utf8_stdout\n"
        "ensure_utf8_stdout(force=True)\n"
        "print('\\u039b ok')\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, timeout=60,
        env={"PYTHONPATH": str(ROOT), "PYTHONIOENCODING": "ascii", "AUREON_ACTIVATE_ON_IMPORT": "0"},
    )
    assert out.returncode == 0, out.stderr.decode(errors="replace")
    assert out.stdout.decode("utf-8").strip() == "\u039b ok"
