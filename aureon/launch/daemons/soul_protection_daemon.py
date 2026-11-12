"""Launcher seat for the restored workspace soul_protection_daemon.py.

The real module lives at the repo root (restored from Project-Sero). It is
loaded by path so this seat can never import itself by name. It runs a 5s
protection cycle, writes soul_shield_logs/, soul_protection.pid and
queen_shield_stats.json under WORKSPACE, and places no orders.
"""

import importlib.util
from pathlib import Path

_REAL = Path(__file__).resolve().parents[3] / "soul_protection_daemon.py"


def _load_real():
    spec = importlib.util.spec_from_file_location("soul_protection_daemon_real", _REAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(_load_real().main())
