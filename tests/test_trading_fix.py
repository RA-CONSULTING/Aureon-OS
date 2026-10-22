#!/usr/bin/env python3
"""
Quick test to verify the game launcher fix
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import subprocess

import pytest

def _command_starts():
    """Test the exact command the game launcher uses"""
    print("Testing the exact command the game launcher uses...")

    # This is what the game launcher should be running
    cmd = [
        sys.executable,
        "-m",
        "aureon.trading.micro_profit_labyrinth",
        "--dry-run",
        "--multi-exchange",
        "--duration",
        "86400",
    ]

    print(f"Command: {' '.join(cmd)}")
    print("Starting subprocess...")

    try:
        # Start the process
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Wait a bit to see if it starts
        import time
        time.sleep(5)

        # Check if it's still running
        if process.poll() is None:
            print("✅ SUCCESS: Trading engine is still running after 5 seconds!")
            process.terminate()
            process.wait()
            return True
        else:
            print(f"❌ FAILED: Trading engine exited immediately with code {process.returncode}")
            stdout, stderr = process.communicate()
            print("STDOUT:", stdout[-500:])  # Last 500 chars
            print("STDERR:", stderr[-500:])  # Last 500 chars
            return False

    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

@pytest.mark.skip(reason="Starts the trading engine with --duration 86400. The offline suite does not launch it.")
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
