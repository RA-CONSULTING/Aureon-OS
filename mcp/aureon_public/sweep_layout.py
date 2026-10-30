"""Place fake NEXUS and Sero checkouts beside the checkout this process loads.

The sweep scripts copy the checkout under an ordinary temp parent and run this
module from that copy, so the parent is not the filesystem root. There is no
privilege escalation. A sibling that already exists is left in place.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from aureon_public.paths import repo_root

SIBLING_NAMES = ("NEXUS-LIVE-FEED-", "Aureon-Trading--Project-Sero")
_MARKER = ".aureon-sweep-planted"


def beside() -> Path:
    return repo_root().resolve().parent


def _state_path() -> Path:
    return beside() / ".sweep_siblings.json"


def _fake_source() -> str:
    return (
        "import socket\n"
        "socket.create_connection(('203.0.113.1', 9), timeout=1)\n"
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
        shutil.rmtree(folder)


def created_names() -> list[str]:
    path = _state_path()
    if not path.is_file():
        return []
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded]


def layout_record(created: list[str] | None = None) -> dict[str, object]:
    root = beside()
    names = created_names() if created is None else created
    return {
        "beside": str(root),
        "created": names,
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

    parser = argparse.ArgumentParser(prog="aureon-public-sweep-layout")
    parser.add_argument("--plant", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args()
    state = _state_path()
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
