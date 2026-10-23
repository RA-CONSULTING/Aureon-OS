#!/usr/bin/env python3
"""
RADAR COMPARTMENT LAUNCHER
==========================
Launches all radar compartments with proper environment.
Handles UTF-8 encoding, log rotation, and clean startup.

2026-09-04 | Gary Leckey
"""

import os
import sys
import time
import subprocess
from pathlib import Path

RADAR_DIR = Path("C:/Users/user/.kimi_openclaw/workspace/aureon_radar")
PYTHON = Path("C:/Users/user/AppData/Local/Programs/Python/Python312/python.exe")

# Environment
env = os.environ.copy()
env["PYTHONIOENCODING"] = "utf-8"
env["PYTHONUNBUFFERED"] = "1"

COMPARTMENTS = [
    ("planetary_switchboard.py", "planetary_meta.log"),
    ("ollama_switchboard.py", "ollama_switchboard.log"),
    ("alpaca_switchboard.py", "stock_meta.log"),
    ("binance_switchboard.py", "correlation_meta.log"),
    ("aureon_bridge.py", "aureon_bridge.log"),
    ("aureon_phi_radar.py", "radar.log"),
]

def archive_old_logs():
    """Rename old log files to free file handles."""
    ts = time.strftime("%Y%m%d_%H%M%S")
    for script, logfile in COMPARTMENTS:
        logpath = RADAR_DIR / logfile
        if logpath.exists():
            backup = RADAR_DIR / f"{logfile}.{ts}.bak"
            try:
                logpath.rename(backup)
                print(f"  Archived: {logfile}")
            except Exception as e:
                print(f"  Could not archive {logfile}: {e}")

def launch():
    print("=" * 60)
    print("AUREON RADAR — COMPARTMENT LAUNCHER")
    print("=" * 60)
    
    print("\n[1/3] Archiving old logs...")
    archive_old_logs()
    
    print("\n[2/3] Launching compartments...")
    processes = []
    for script, logfile in COMPARTMENTS:
        logpath = RADAR_DIR / logfile
        
        # Open log file
        log_f = open(logpath, "w", encoding="utf-8")
        
        # Launch process with stdout/stderr going to log file
        proc = subprocess.Popen(
            [str(PYTHON), "-u", script],
            cwd=str(RADAR_DIR),
            stdout=log_f,
            stderr=subprocess.STDOUT,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        processes.append((script, proc, log_f))
        print(f"  Launched: {script} (PID {proc.pid})")
        time.sleep(0.3)
    
    print("\n[3/3] All compartments launched!")
    print("\nMonitor these files for status:")
    for script, logfile in COMPARTMENTS:
        print(f"  - {logfile}")
    
    print("\nPress Ctrl+C to stop all compartments...")
    
    try:
        while True:
            alive = 0
            for script, proc, _ in processes:
                if proc.poll() is None:
                    alive += 1
                else:
                    print(f"\n[DEAD] {script} exited with code {proc.returncode}")
            
            if alive == 0:
                print("\nAll compartments have exited.")
                break
            
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n\nStopping all compartments...")
        for script, proc, log_f in processes:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except:
                proc.kill()
            log_f.close()
        print("All compartments stopped.")

if __name__ == "__main__":
    launch()
