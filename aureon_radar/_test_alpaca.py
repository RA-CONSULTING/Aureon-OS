#!/usr/bin/env python3
"""
SWITCHBOARD TEST WRAPPER
========================
Captures all output to file for debugging.
"""

import sys
import traceback
from pathlib import Path

# Redirect all output to a log beside this script.
sys.stdout = open(Path(__file__).resolve().parent / "_switchboard_test.log", "w", encoding="utf-8")
sys.stderr = sys.stdout

print("Starting switchboard test...")

try:
    import alpaca_switchboard
    print("Alpaca module loaded")
    print(f"ALPACA_API_KEY: {alpaca_switchboard.ALPACA_API_KEY[:10]}..." if alpaca_switchboard.ALPACA_API_KEY else "NOT SET")
    alpaca_switchboard.main()
except Exception as e:
    traceback.print_exc()

print("Done")
