"""Refresh the generated system registry the operator coordinator reads.

The coordinator opens ``aureon_system_registry.json`` from the checkout root.
The file is generated inventory, not source. Regenerate it when it is missing
or older than the requested age.

    .venv\\Scripts\\python.exe scripts\\ops\\ensure_system_registry.py
    .venv\\Scripts\\python.exe scripts\\ops\\ensure_system_registry.py --force
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TARGET = ROOT / "aureon_system_registry.json"
DEFAULT_MAX_AGE_DAYS = 7


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="regenerate even when the registry is fresh")
    parser.add_argument("--max-age-days", type=float, default=DEFAULT_MAX_AGE_DAYS)
    args = parser.parse_args(argv)
    if TARGET.is_file() and not args.force:
        age_days = max(0.0, time.time() - TARGET.stat().st_mtime) / 86400
        if age_days <= args.max_age_days:
            print(f"registry is current ({age_days:.1f} days old): {TARGET}")
            return 0
    from aureon.command_centers.aureon_system_hub import SystemRegistry

    registry = SystemRegistry(str(ROOT))
    registry.scan_workspace()
    registry.save_registry()
    total = len(registry.systems)
    print(f"registry refreshed: {total} systems -> {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
