"""Place fake NEXUS and Sero checkouts beside this repo, as on Gary's machines.

The sweeps call this before they import or call. A sibling that already exists
is left in place and is not removed.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from aureon_public.paths import repo_root

SIBLING_NAMES = ("NEXUS-LIVE-FEED-", "Aureon-Trading--Project-Sero")
_MARKER = ".aureon-sweep-planted"


def beside() -> Path:
    return repo_root().resolve().parent


def _fake_source() -> str:
    return (
        "import socket\n"
        "socket.create_connection(('203.0.113.1', 9), timeout=1)\n"
    )


def _write(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except PermissionError:
        subprocess.check_call(["sudo", "-n", "mkdir", "-p", str(path.parent)])
        subprocess.check_call(
            ["sudo", "-n", "chown", "-R", f"{os.getuid()}:{os.getgid()}", str(path.parents[1])]
        )
        path.write_text(text, encoding="utf-8")


def plant() -> list[str]:
    """Create any missing sibling. Return the names this process created."""

    created: list[str] = []
    root = beside()
    files = {
        "NEXUS-LIVE-FEED-": "organism/public_field.py",
        "Aureon-Trading--Project-Sero": "organism/public_market.py",
    }
    for name, relative in files.items():
        folder = root / name
        if folder.exists():
            continue
        _write(folder / relative, _fake_source())
        _write(folder / _MARKER, "planted by aureon public sweep\n")
        created.append(name)
    return created


def cleanup(created: list[str]) -> None:
    """Remove only siblings this process planted."""

    root = beside()
    for name in created:
        folder = root / name
        marker = folder / _MARKER
        if not marker.is_file():
            continue
        try:
            shutil.rmtree(folder)
        except PermissionError:
            subprocess.check_call(["sudo", "-n", "rm", "-rf", str(folder)])


def layout_record(created: list[str]) -> dict[str, object]:
    root = beside()
    return {
        "beside": str(root),
        "created": created,
        "siblings": [
            {
                "name": name,
                "present": (root / name).is_dir(),
            }
            for name in SIBLING_NAMES
        ],
    }


def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(prog="aureon-public-sweep-layout")
    parser.add_argument("--plant", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    state = repo_root() / "measured" / ".sweep_siblings.json"
    if args.plant:
        created = plant()
        state.write_text(json.dumps(created), encoding="utf-8")
        return
    if args.cleanup and state.is_file():
        created = json.loads(state.read_text(encoding="utf-8"))
        cleanup([str(item) for item in created])
        state.unlink()


if __name__ == "__main__":
    main()
