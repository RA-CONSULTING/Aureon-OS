"""The workspace self-questioning runner.

It stays up and records that no question was invented. It does not call a
model and it does not place an order. ``--interval`` is accepted so the organ
command can pass it through.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

_PATH = Path(__file__).resolve().parent / "state" / "self_questioning.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Self-questioning runner standing by")
    parser.add_argument("--interval", type=float, default=600.0)
    args = parser.parse_args(argv)
    _PATH.parent.mkdir(parents=True, exist_ok=True)
    while True:
        payload = {
            "available": False,
            "truth_status": "no_data",
            "reason": "no question is invented and no model is called",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "live_trading": False,
        }
        temporary = _PATH.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        temporary.replace(_PATH)
        print("self-questioning runner standing by; no model call; live_trading=false", flush=True)
        time.sleep(max(1.0, float(args.interval)))


if __name__ == "__main__":
    raise SystemExit(main())
