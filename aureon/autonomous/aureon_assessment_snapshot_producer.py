"""Read-only assessment snapshot producer.

The organ registry launches this module with ``--daemon``. A fresh checkout
has no scored assessment sample. This process stays up and writes that fact.
It does not invent a score and it does not place an order.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO = Path(__file__).resolve().parents[2]
DEFAULT_PATH = REPO / "state" / "assessment_snapshot.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_snapshot(root: Path) -> dict:
    watched = (
        root / "real_time_data.json",
        root / "schumann_state.json",
        root / "aureon_fusion" / "state" / "hnc_core_state.json",
    )
    present = [str(path.relative_to(root)) for path in watched if path.is_file()]
    return {
        "schema": "aureon-assessment-snapshot-v1",
        "generated_at": utc_now(),
        "timestamp": utc_now(),
        "truth_status": "no_data",
        "live_trading": False,
        "orders": 0,
        "score": None,
        "sources_present": present,
        "note": "no assessment sample has been measured; the producer is awake and does not invent a score",
    }


def write_snapshot(root: Path, path: Path) -> Path:
    payload = build_snapshot(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write a read-only assessment snapshot")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--interval", type=float, default=60)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--output", default=str(DEFAULT_PATH))
    args = parser.parse_args(list(argv) if argv is not None else None)
    destination = Path(args.output)
    while True:
        path = write_snapshot(REPO, destination)
        if not args.quiet:
            print(f"assessment snapshot wrote {path} truth_status=no_data live_trading=false", flush=True)
        if not args.daemon:
            return 0
        time.sleep(max(1.0, float(args.interval)))


if __name__ == "__main__":
    raise SystemExit(main())
