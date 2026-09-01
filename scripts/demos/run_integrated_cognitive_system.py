#!/usr/bin/env python3
"""Fail-closed public launcher for the unreleased Aureon ICS runtime."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
    )
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from aureon.core.integrated_cognitive_system import (  # noqa: E402
    integrated_cognitive_system_security_preflight,
)


def main(argv: list[str] | None = None) -> int:
    """Reject runtime launch until production Magic Star is available."""

    parser = argparse.ArgumentParser(
        description="Report the Aureon ICS production release gate",
    )
    parser.add_argument("--lan", action="store_true")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--port", type=int, default=5566)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.parse_args(argv)

    status = integrated_cognitive_system_security_preflight()
    print(json.dumps(status, sort_keys=True), file=sys.stderr)
    return 0 if status.get("production_ready") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
