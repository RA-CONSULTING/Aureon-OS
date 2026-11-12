"""Launcher seat for the restored workspace aureon_self_questioning_runner.py.

The real module lives at the repo root (restored from Project-Sero). It is
loaded by path so this seat can never import itself by name. The Sero file
has main(); this seat calls it. It drives SelfQuestioningAI with a real
sleep between cycles, writes no orders, and does not change live switches.
"""

import importlib.util
from pathlib import Path

_REAL = Path(__file__).resolve().parents[3] / "aureon_self_questioning_runner.py"


def _load_real():
    spec = importlib.util.spec_from_file_location(
        "aureon_self_questioning_runner_real", _REAL
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None):
    return _load_real().main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
