#!/usr/bin/env python3
"""
RADAR SYSTEM RECOVERY SCRIPT
============================
Fixes the radar after shutdown and restarts all compartments.

Date: 2026-09-04
Prime Sentinel: Gary Leckey
"""
import os

import json
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path(os.environ.get("SERO_WORKSPACE") or Path(__file__).resolve().parents[1])
RADAR_DIR = WORKSPACE / "aureon_radar"

def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] {msg}")

def fix_radar_state():
    """Reset radar state to DISARMED for safe restart."""
    state_file = RADAR_DIR / "radar_state.json"
    state = {
        "state": "DISARMED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "psk": "REDACTED",
        "phi": 1.618033988749895,
        "live_trades_today": 0,
        "profit_today": 0.0,
        "recovery_note": "Reset after system shutdown 2026-09-04"
    }
    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
    log("Radar state reset to DISARMED")

def clear_stale_signals():
    """Archive old signal files and create fresh ones."""
    files_to_archive = [
        "shadow_trades.jsonl",
        "live_trades.jsonl",
        "signal_log.jsonl",
        "fused_signals.jsonl",
        "ollama_signals.jsonl",
        "planetary_signals.jsonl",
        "crypto_signals.jsonl",
        "stock_signals.jsonl",
    ]
    
    archive_dir = RADAR_DIR / "archive" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    for fname in files_to_archive:
        fpath = RADAR_DIR / fname
        if fpath.exists():
            # Archive old file
            archived = archive_dir / fname
            fpath.rename(archived)
            log(f"Archived: {fname} -> {archived}")
            # Create fresh empty file
            fpath.write_text("")
            log(f"Created fresh: {fname}")

def reset_honey_ladder():
    """Reset the honey ladder state."""
    ladder_file = RADAR_DIR / "honey_ladder_state.json"
    if ladder_file.exists():
        ladder_file.rename(RADAR_DIR / "archive" / datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") / "honey_ladder_state.json")
    
    # Fresh state
    fresh = {
        "shadow_runs": [],
        "honey_pot": None,
        "source_records": {},
        "sector_heat": {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(ladder_file, 'w') as f:
        json.dump(fresh, f, indent=2)
    log("Honey ladder reset")

def kill_old_python_processes():
    """Kill old Python processes that might be hanging."""
    import psutil
    killed = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            if proc.info['name'] == 'python.exe':
                cmdline = proc.info['cmdline'] or []
                cmd_str = ' '.join(cmdline)
                # Kill radar-related processes older than 1 hour
                if any(x in cmd_str for x in ['aureon_phi_radar', 'honey_ladder', 'planetary_switchboard', 
                                                 'ollama_switchboard', 'alpaca_switchboard', 'binance_switchboard']):
                    age = time.time() - proc.info['create_time']
                    if age > 3600:  # Older than 1 hour
                        proc.kill()
                        killed += 1
                        log(f"Killed old process: {proc.info['pid']} ({cmd_str[:80]})")
        except:
            pass
    log(f"Killed {killed} old processes")

def start_compartments():
    """Start all radar compartments."""
    log("Starting radar compartments...")
    
    # Use the launch_all.bat script
    launch_script = RADAR_DIR / "launch_all.bat"
    if launch_script.exists():
        log(f"Running: {launch_script}")
        subprocess.Popen(
            ["cmd", "/c", str(launch_script)],
            cwd=str(RADAR_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    else:
        log("WARNING: launch_all.bat not found, starting main radar only")
        subprocess.Popen(
            [sys.executable, str(RADAR_DIR / "aureon_phi_radar.py")],
            cwd=str(RADAR_DIR),
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    
    log("Compartments launched. Check radar.log for status.")

def main():
    log("=" * 60)
    log("AUREON RADAR SYSTEM RECOVERY")
    log("=" * 60)
    
    log("Step 1: Fixing radar state...")
    fix_radar_state()
    
    log("Step 2: Clearing stale signals...")
    clear_stale_signals()
    
    log("Step 3: Resetting honey ladder...")
    reset_honey_ladder()
    
    log("Step 4: Killing old processes...")
    try:
        kill_old_python_processes()
    except Exception as e:
        log(f"Could not kill old processes: {e}")
    
    log("Step 5: Starting compartments...")
    start_compartments()
    
    log("=" * 60)
    log("RECOVERY COMPLETE")
    log("Radar state: DISARMED (will auto-arm when shadows prove)")
    log("All stale signals cleared")
    log("Check radar.log for live status")
    log("=" * 60)

if __name__ == "__main__":
    main()
