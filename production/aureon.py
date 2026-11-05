#!/usr/bin/env python3
"""Production compatibility entrypoint routed to the terminal HOLD boundary.

The stage 11 gate can replace this process with the contained cold boot only
when receipts 1-5 verify on HEAD. Until then this file execs the isolated
bootstrap and does not import a target.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    bootstrap = root / "scripts" / "bootstrap" / "protected_bootstrap_v05.py"
    gate = root / "scripts" / "bootstrap" / "go_live_stage11_gate.py"
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
    if gate.is_file():
        check = subprocess.run(
            (str(python), "-I", "-S", "-B", str(gate), "--check"),
            check=False,
        )
        if check.returncode == 0:
            os.execv(
                str(python),
                (
                    str(python),
                    "-I",
                    "-S",
                    "-B",
                    str(gate),
                    "--launch-contained",
                ),
            )
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
