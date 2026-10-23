#!/usr/bin/env python3
"""Write a redacted environment dump next to a fresh-clone suite run.

Values whose names look like secrets are replaced. The dump records the
interpreter, installed distributions, OS, and the environment keys that
change how pytest and Aureon behave.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path


_SECRET_MARKERS = (
    "SECRET",
    "PASSWORD",
    "PASSWD",
    "API_KEY",
    "TOKEN",
    "PRIVATE",
    "CREDENTIAL",
    "AUTH",
)


def _redact(key: str, value: str) -> str:
    upper = key.upper()
    if any(marker in upper for marker in _SECRET_MARKERS):
        return "<redacted>"
    return value


def _pip_freeze() -> list[str]:
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"],
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return []
    return [line for line in completed.stdout.splitlines() if line.strip()]


def _git_sha(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def build_dump(root: Path) -> dict:
    interesting = {}
    for key, value in sorted(os.environ.items()):
        upper = key.upper()
        if (
            key.startswith("AUREON_")
            or key.startswith("PYTEST_")
            or key.startswith("PYTHON")
            or key in {"PATH", "VIRTUAL_ENV", "TMPDIR", "LANG", "LC_ALL"}
            or "LIVE" in upper
            or "DRY" in upper
        ):
            interesting[key] = _redact(key, value)
    return {
        "git_sha": _git_sha(root),
        "python": {
            "version": sys.version,
            "executable": sys.executable,
            "implementation": platform.python_implementation(),
        },
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
        "pip_freeze": _pip_freeze(),
        "environment": interesting,
    }


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    destination = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else root / "reports" / "environment.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(build_dump(root), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
