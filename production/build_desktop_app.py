#!/usr/bin/env python3
"""Desktop-build compatibility entrypoint routed to terminal release HOLD."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    bootstrap = root / "scripts" / "bootstrap" / "protected_bootstrap_v05.py"
    python = (
        root / ".venv" / "Scripts" / "python.exe"
        if os.name == "nt"
        else root / ".venv" / "bin" / "python"
    )
    if not python.is_file() or not bootstrap.is_file():
        print("Desktop release boundary unavailable; refusing build.", file=sys.stderr)
        return 1
    os.execv(
        str(python),
        (
            str(python),
            "-I",
            "-S",
            "-B",
            str(bootstrap),
            "--target-id",
            "local-gui",
        ),
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
