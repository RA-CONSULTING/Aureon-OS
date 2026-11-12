"""Launcher seat for the restored workspace real_time_data_feeder.py.

The real module lives at the repo root (restored from Project-Sero). It is
run by path as __main__ so this seat can never import itself by name. It
polls public NOAA SWPC and USGS feeds through aureon_fusion.api_communion
every 60 s, writes real_time_data.json and real_data_feeder.log under
WORKSPACE/LOGS, and places no orders.
"""

import runpy
from pathlib import Path

_REAL = Path(__file__).resolve().parents[3] / "real_time_data_feeder.py"


if __name__ == "__main__":
    runpy.run_path(str(_REAL), run_name="__main__")
