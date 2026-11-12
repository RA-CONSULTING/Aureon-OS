"""Launcher seat for the restored workspace sero_autonomous_expansion.py.

The real module lives at the repo root (restored from Project-Sero). It is
loaded by path so this seat can never import itself by name. With no
arguments it runs in continuous mode, matching the organ registry. It writes
only to WORKSPACE/sero_autonomous_state and places no orders.
"""

import importlib.util
import sys
from pathlib import Path

_REAL = Path(__file__).resolve().parents[3] / "sero_autonomous_expansion.py"


def _load_real():
    spec = importlib.util.spec_from_file_location("sero_autonomous_expansion_real", _REAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("--continuous")
    raise SystemExit(_load_real().main())
