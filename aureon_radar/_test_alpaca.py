#!/usr/bin/env python3
"""
SWITCHBOARD TEST WRAPPER
========================
Captures all output to file for debugging.
"""

import sys
import traceback

# Redirect all output to file
sys.stdout = open(r'C:\Users\user\.kimi_openclaw\workspace\aureon_radar\_switchboard_test.log', 'w')
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
