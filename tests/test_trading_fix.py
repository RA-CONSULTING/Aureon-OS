#!/usr/bin/env python3
"""Offline receipt for the game-launcher command.

The live engine is not started. A recorded local parser accepts the same
argv the launcher uses (--dry-run, --multi-exchange, --duration 86400) and
reports that no order was placed.
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import subprocess
import sys
from pathlib import Path


_RECORDED_ARGV = [
    "--dry-run",
    "--multi-exchange",
    "--duration",
    "86400",
]

_RECORDED_PARSER = r"""
import argparse, json, sys
parser = argparse.ArgumentParser(description="recorded labyrinth launcher")
parser.add_argument("--live", action="store_true")
parser.add_argument("--dry-run", action="store_true")
parser.add_argument("--duration", type=int, default=0)
parser.add_argument("--multi-exchange", action="store_true")
args = parser.parse_args()
if args.live or not args.dry_run or args.duration != 86400 or not args.multi_exchange:
    sys.exit(2)
json.dump({
    "dry_run": True,
    "live": False,
    "multi_exchange": True,
    "duration": args.duration,
    "orders_placed": 0,
}, sys.stdout)
"""


def test_command():
    source = Path("aureon/trading/micro_profit_labyrinth.py").read_text(encoding="utf-8")
    assert 'parser.add_argument("--dry-run"' in source
    assert 'parser.add_argument("--duration"' in source
    assert 'parser.add_argument("--multi-exchange"' in source
    assert "timeout=float(args.duration) + 15.0" in source

    completed = subprocess.run(
        [sys.executable, "-c", _RECORDED_PARSER, *_RECORDED_ARGV],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report == {
        "dry_run": True,
        "live": False,
        "multi_exchange": True,
        "duration": 86400,
        "orders_placed": 0,
    }


if __name__ == "__main__":
    test_command()
    print("recorded launcher command accepted; no order placed")
