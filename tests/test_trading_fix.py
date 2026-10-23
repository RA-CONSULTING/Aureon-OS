#!/usr/bin/env python3
"""
Quick test to verify the game launcher fix.

The recorded receipt is a fast path: it returns before the engine exists.
``test_command`` also starts the real labyrinth, dry-run, offline, and bounded
by ``--duration`` plus the subprocess timeout.
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RECORDED_LAUNCH = REPO / "tests" / "fixtures" / "micro_profit_labyrinth_dry_run_launch.json"
COMMAND = [
    "-m",
    "aureon.trading.micro_profit_labyrinth",
    "--dry-run",
    "--multi-exchange",
]


def _child_env(recorded: bool) -> dict[str, str]:
    env = os.environ.copy()
    env["AUREON_OFFLINE"] = "1"
    env["AUREON_LIVE_TRADING"] = "0"
    env["AUREON_DISABLE_REAL_ORDERS"] = "1"
    env["ENABLE_WEBSOCKETS"] = "false"
    env["LIVE"] = "0"
    env["AUREON_SIMULATED_BOOT"] = "0"
    env["PYTHONPATH"] = str(REPO) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    if recorded:
        env["AUREON_RECORDED_LAUNCH_FIXTURE"] = str(RECORDED_LAUNCH)
    else:
        env.pop("AUREON_RECORDED_LAUNCH_FIXTURE", None)
    return env


def _launch(args: list[str], env: dict[str, str], cwd: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    cwd.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _command_starts(tmp: Path) -> bool:
    """Replay the recorded receipt, then start the real engine offline."""
    print("Testing the exact command the game launcher uses...")
    replay = _launch(
        [*COMMAND, "--duration", "86400"],
        _child_env(recorded=True),
        tmp / "replay",
        timeout=40,
    )
    if replay.returncode != 0 or "RECORDED_DRY_RUN_LAUNCH_OK" not in replay.stdout:
        print(f"❌ FAILED: recorded dry-run exited {replay.returncode}")
        print("STDOUT:", replay.stdout[-500:])
        print("STDERR:", replay.stderr[-500:])
        return False
    if "ENGINE_START_OK" in replay.stdout:
        print("❌ FAILED: recorded dry-run constructed the engine")
        return False
    print("✅ recorded dry-run stayed a fast path")

    print("Starting the real engine offline...")
    started = _launch(
        [*COMMAND, "--duration", "1"],
        _child_env(recorded=False),
        tmp / "engine",
        timeout=50,
    )
    output = started.stdout
    if started.returncode != 0:
        print(f"❌ FAILED: engine exited {started.returncode}")
        print("STDOUT:", output[-800:])
        print("STDERR:", started.stderr[-800:])
        return False
    required = (
        "INITIALIZING MICRO PROFIT LABYRINTH",
        "ENTERING MICRO PROFIT LABYRINTH",
        "ENGINE_START_OK duration=1 dry_run=1 live=0 offline=1",
        "OFFLINE BOOT: venues not contacted",
        "🔵 DRY RUN",
    )
    missing = [line for line in required if line not in output]
    if missing or "RECORDED_DRY_RUN_LAUNCH_OK" in output:
        print(f"❌ FAILED: real start missing {missing}")
        print("STDOUT:", output[-800:])
        print("STDERR:", started.stderr[-800:])
        return False
    print("✅ SUCCESS: trading engine started offline and exited on its duration.")
    return True


def test_command(tmp_path: Path):
    assert _command_starts(tmp_path)


if __name__ == "__main__":
    print("🔍 Testing trading engine startup with duration parameter...")
    success = _command_starts(Path(os.environ.get("TMPDIR", "/tmp")) / "aureon-test-command")
    if success:
        print("\n✅ The fix works! The trading engine runs with --duration parameter.")
        print("   Make sure you git pull the latest changes on Windows.")
    else:
        print("\n❌ There's still an issue. Check the error output above.")
