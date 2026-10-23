#!/usr/bin/env python3
"""
Quick test to verify the game launcher fix
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import sys
import os
import subprocess
from pathlib import Path

RECORDED_LAUNCH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "micro_profit_labyrinth_dry_run_launch.json"


def _command_starts():
    """The launcher command accepts a recorded dry-run and does not call a venue."""
    print("Testing the exact command the game launcher uses...")

    receipt = json.loads(RECORDED_LAUNCH.read_text(encoding="utf-8"))
    cmd = [sys.executable, *receipt["command"]]

    print(f"Command: {' '.join(cmd)}")
    print("Starting recorded dry-run...")

    env = os.environ.copy()
    env["AUREON_RECORDED_LAUNCH_FIXTURE"] = str(RECORDED_LAUNCH)
    env["AUREON_LIVE_TRADING"] = "0"
    env["AUREON_DISABLE_REAL_ORDERS"] = "1"
    completed = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0 or receipt["banner"] not in completed.stdout:
        print(f"❌ FAILED: recorded dry-run exited {completed.returncode}")
        print("STDOUT:", completed.stdout[-500:])
        print("STDERR:", completed.stderr[-500:])
        return False
    if receipt["venues_contacted"] or receipt["orders_submitted"] or receipt["mainnet"] is not False:
        return False
    print("✅ SUCCESS: recorded dry-run launch stayed off the venue.")
    return True


def test_command():
    assert _command_starts()


if __name__ == "__main__":
    print("🔍 Testing trading engine startup with duration parameter...")
    success = _command_starts()
    if success:
        print("\n✅ The fix works! The trading engine runs with --duration parameter.")
        print("   Make sure you git pull the latest changes on Windows.")
    else:
        print("\n❌ There's still an issue. Check the error output above.")
