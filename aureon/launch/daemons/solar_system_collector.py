"""Launcher seat for the restored workspace solar_system_collector.py.

The real module lives at the repo root (restored from Project-Sero). It is
loaded by path so this seat can never import itself by name. The Sero file
has no main(); this seat runs it as __main__ so the existing CLI is used.
It polls public NOAA SWPC feeds, writes only under WORKSPACE/solar_system_data
and places no orders.
"""

import runpy
from pathlib import Path

_REAL = Path(__file__).resolve().parents[3] / "solar_system_collector.py"


def main():
    runpy.run_path(str(_REAL), run_name="__main__")


if __name__ == "__main__":
    raise SystemExit(main())
