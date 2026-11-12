"""Launcher seat for the restored workspace sero_space_weather.py.

The real module lives at the repo root (restored from Project-Sero). It is
run by path as __main__ with --daemon so this seat can never import itself
by name. It reads public NOAA SWPC Kp and alerts through
aureon_fusion.api_communion once an hour, writes only under
WORKSPACE/sero_space_weather/, and places no orders.
"""

import runpy
import sys
from pathlib import Path

_REAL = Path(__file__).resolve().parents[3] / "sero_space_weather.py"


if __name__ == "__main__":
    if not any(a in sys.argv[1:] for a in ("--once", "--daemon", "--status", "--help")):
        sys.argv = [str(_REAL), "--daemon", *sys.argv[1:]]
    else:
        sys.argv = [str(_REAL), *sys.argv[1:]]
    runpy.run_path(str(_REAL), run_name="__main__")
