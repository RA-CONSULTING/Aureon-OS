#!/usr/bin/env python3
"""Production compatibility entrypoint routed to the terminal HOLD boundary."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    bootstrap = root / "scripts" / "bootstrap" / "protected_bootstrap_v05.py"
    if os.name == "nt":
        python = root / ".venv" / "Scripts" / "python.exe"
    else:
        python = root / ".venv" / "bin" / "python"
    if not python.is_file() or not bootstrap.is_file():
        print(
            "Aureon production boundary unavailable; refusing startup.",
            file=sys.stderr,
        )
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
            "production-supervisor",
        ),
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
