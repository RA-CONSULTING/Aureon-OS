"""Launcher seat for the restored workspace schumann_real_daemon.py.

The real module lives at the repo root (restored from Project-Sero). It is
loaded by path so this seat can never import itself by name. It polls the
public ResonanceOne endpoint every 60 s, writes schumann_state.json,
schumann_sensor.log and schumann_sensor.pid under WORKSPACE, and places no
orders.
"""

import importlib.util
from pathlib import Path

_REAL = Path(__file__).resolve().parents[3] / "schumann_real_daemon.py"


def _load_real():
    spec = importlib.util.spec_from_file_location("schumann_real_daemon_real", _REAL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(_load_real().main())
