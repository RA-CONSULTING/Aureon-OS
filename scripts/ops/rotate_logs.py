"""Rotate Aureon runtime logs that are not handled by an in-process logger.

Run this before starting the stack or after stopping it, when no component
holds the files open. The ThoughtBus rotates its own active log on write; this
helper also moves an oversized active file aside once, so the next run starts
small. Existing archives are shifted, never truncated.

    .venv\\Scripts\\python.exe scripts\\ops\\rotate_logs.py
    .venv\\Scripts\\python.exe scripts\\ops\\rotate_logs.py --dry-run
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
LAUNCHER_LOGS = STATE / "launcher" / "logs"
FUSION_STATE = ROOT / "aureon_fusion" / "state"

MIB = 1024 * 1024


@dataclass(frozen=True)
class Target:
    path: Path
    max_bytes: int
    backups: int


def targets() -> list[Target]:
    items: list[Target] = []
    for directory in (LAUNCHER_LOGS, FUSION_STATE):
        if directory.is_dir():
            for path in sorted(directory.glob("*.log")):
                # The stack service rotates its own log at cycle start, before
                # it reopens the file for the next launcher run.
                if path.name == "stack_service.log":
                    continue
                items.append(Target(path, 8 * MIB, 3))
    for name, limit, backups in (
        ("thoughts.jsonl", 32 * MIB, 3),
        ("state/hnc_live_trace.jsonl", 16 * MIB, 2),
        ("state/monitor/monitor.out.log", 4 * MIB, 2),
    ):
        items.append(Target(ROOT / name, limit, backups))
    return items


def rotate(target: Target, *, dry_run: bool = False) -> int:
    path = target.path
    try:
        size = path.stat().st_size
    except OSError:
        return 0
    if size < target.max_bytes:
        return 0
    if dry_run:
        print(f"would rotate {path.relative_to(ROOT)} ({size / MIB:.1f} MiB)")
        return 0
    for index in range(target.backups - 1, 0, -1):
        source = path.with_name(f"{path.name}.{index}")
        destination = path.with_name(f"{path.name}.{index + 1}")
        if source.exists():
            os.replace(source, destination)
    try:
        os.replace(path, path.with_name(f"{path.name}.1"))
    except OSError as exc:
        print(f"skip {path.relative_to(ROOT)}: {exc.__class__.__name__}: {exc}")
        return 0
    print(f"rotated {path.relative_to(ROOT)} ({size / MIB:.1f} MiB) to .1")
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report without moving files")
    args = parser.parse_args(argv)
    rotated = sum(rotate(item, dry_run=args.dry_run) for item in targets())
    if not rotated and not args.dry_run:
        print("no log exceeded its cap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
