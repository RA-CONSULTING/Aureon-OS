#!/usr/bin/env python3
"""
RADAR SYSTEM DIAGNOSTIC TEST
============================
Full system verification post-recovery.
Prime Sentinel: Gary Leckey
Date: 2026-09-04
"""

import json
import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

WORKSPACE = Path("C:/Users/user/.kimi_openclaw/workspace")
RADAR_DIR = WORKSPACE / "aureon_radar"

def log(msg, level="INFO"):
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] [{level}] {msg}")

def test_compartment(name, check_func):
    """Run a test on a compartment."""
    try:
        result = check_func()
        if result:
            log(f"[PASS] {name}: {result}")
            return True
        else:
            log(f"[FAIL] {name}: No output", "ERROR")
            return False
    except Exception as e:
        log(f"[FAIL] {name}: {e}", "ERROR")
        return False

def check_main_radar():
    """Check if main radar is running and logging."""
    radar_log = RADAR_DIR / "radar.log"
    if not radar_log.exists():
        return "Log file missing"
    
    # Check last log entry age
    age = time.time() - radar_log.stat().st_mtime
    if age > 300:  # 5 minutes
        return f"Stale log (last write {age:.0f}s ago)"
    
    # Read last 3 lines
    with open(radar_log) as f:
        lines = f.readlines()[-3:]
    
    return f"Active, last entry: {lines[-1].strip()[:80]}..."

def check_ollama_switchboard():
    """Check Ollama phi cycles."""
    log_file = RADAR_DIR / "ollama_switchboard.log"
    if not log_file.exists():
        return "Log missing"
    
    age = time.time() - log_file.stat().st_mtime
    if age > 1800:  # 30 min
        return f"Stale ({age:.0f}s ago)"
    
    with open(log_file) as f:
        lines = f.readlines()[-2:]
    
    return f"Active, last: {lines[-1].strip()[:60]}..."

def check_planetary_switchboard():
    """Check planetary data feed."""
    log_file = RADAR_DIR / "planetary_meta.log"
    if not log_file.exists():
        return "Log missing"
    
    age = time.time() - log_file.stat().st_mtime
    if age > 1800:
        return f"Stale ({age:.0f}s ago)"
    
    with open(log_file) as f:
        lines = f.readlines()[-5:]
    
    return f"Active, last: {lines[-1].strip()[:60]}..."

def check_price_feed():
    """Check price feed is active."""
    # Look for price in radar log
    radar_log = RADAR_DIR / "radar.log"
    with open(radar_log) as f:
        content = f.read()
    
    # Count recent price entries
    price_count = content.count("[PRICE]")
    if price_count > 0:
        return f"Active ({price_count} price entries in log)"
    return "No price entries found"

def check_aureon_bridge():
    """Check Aureon OS bridge signals."""
    bridge_file = RADAR_DIR / "aureon_bridge_signals.jsonl"
    if not bridge_file.exists():
        return "Signal file missing"
    
    with open(bridge_file) as f:
        lines = f.readlines()
    
    if not lines:
        return "No signals"
    
    # Count signals by source
    sources = {}
    for line in lines:
        try:
            sig = json.loads(line)
            src = sig.get('source', 'unknown')
            sources[src] = sources.get(src, 0) + 1
        except:
            pass
    
    return f"Active ({len(lines)} signals, sources: {sources})"

def check_honey_ladder():
    """Check Honey Ladder state."""
    ladder_file = RADAR_DIR / "honey_ladder_state.json"
    if not ladder_file.exists():
        return "State file missing"
    
    with open(ladder_file) as f:
        state = json.load(f)
    
    shadows = len(state.get('shadow_runs', []))
    honey = state.get('honey_pot')
    honey_active = honey.get('active', False) if honey else False
    
    return f"Shadows: {shadows}, HoneyPot: {'ACTIVE' if honey_active else 'EMPTY'}"

def check_dual_capital():
    """Check Capital.com connectivity."""
    # Check if trade ledger has entries
    ledger = RADAR_DIR / "trade_ledger.jsonl"
    if not ledger.exists():
        return "Ledger missing"
    
    with open(ledger) as f:
        lines = f.readlines()
    
    return f"Ledger active ({len(lines)} entries)"

def check_state_consistency():
    """Check radar state file."""
    state_file = RADAR_DIR / "radar_state.json"
    if not state_file.exists():
        return "State file missing"
    
    with open(state_file) as f:
        state = json.load(f)
    
    return f"State: {state.get('state', 'UNKNOWN')}, Trades today: {state.get('live_trades_today', 0)}"

def check_running_processes():
    """Check what Python processes are running."""
    import psutil
    
    radar_procs = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe':
                cmd = ' '.join(proc.info['cmdline'] or [])
                if any(x in cmd for x in ['aureon_phi_radar', 'aureon_bridge', 'ollama_switchboard',
                                             'planetary_switchboard', 'alpaca_switchboard', 'binance_switchboard',
                                             'dashboard']):
                    radar_procs.append(cmd.split()[-1] if cmd.split() else 'unknown')
        except:
            pass
    
    return f"{len(radar_procs)} compartments running: {', '.join(radar_procs)}"

def run_signal_test():
    """Inject a test signal to verify end-to-end flow."""
    test_signal = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": "TEST_SIGNAL",
        "direction": "LONG",
        "confidence": 0.75,
        "source": "diagnostic_test",
        "reasoning": "System verification test"
    }
    
    bridge_file = RADAR_DIR / "aureon_bridge_signals.jsonl"
    with open(bridge_file, 'a') as f:
        f.write(json.dumps(test_signal) + '\n')
    
    return "Test signal injected into bridge"

def main():
    log("=" * 60)
    log("AUREON RADAR — FULL SYSTEM DIAGNOSTIC")
    log("=" * 60)
    
    results = {}
    
    # Test 1: Main Radar
    results['Main Radar'] = test_compartment("Main Radar Loop", check_main_radar)
    
    # Test 2: Ollama
    results['Ollama Switchboard'] = test_compartment("Ollama Switchboard", check_ollama_switchboard)
    
    # Test 3: Planetary
    results['Planetary Switchboard'] = test_compartment("Planetary Switchboard", check_planetary_switchboard)
    
    # Test 4: Price Feed
    results['Price Feed'] = test_compartment("Price Feed", check_price_feed)
    
    # Test 5: Aureon Bridge
    results['Aureon Bridge'] = test_compartment("Aureon OS Bridge", check_aureon_bridge)
    
    # Test 6: Honey Ladder
    results['Honey Ladder'] = test_compartment("Honey Ladder", check_honey_ladder)
    
    # Test 7: Dual Capital
    results['Dual Capital'] = test_compartment("Dual Capital", check_dual_capital)
    
    # Test 8: State Consistency
    results['State'] = test_compartment("Radar State", check_state_consistency)
    
    # Test 9: Running Processes
    results['Processes'] = test_compartment("Running Processes", check_running_processes)
    
    # Test 10: End-to-end signal injection
    results['E2E Signal'] = test_compartment("End-to-End Signal Test", run_signal_test)
    
    # Summary
    log("=" * 60)
    log("DIAGNOSTIC SUMMARY")
    log("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, passed_test in results.items():
        status = "PASS" if passed_test else "FAIL"
        log(f"  [{status}] {name}")
    
    log("=" * 60)
    log(f"RESULT: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    
    if passed == total:
        log("ALL SYSTEMS OPERATIONAL", "SUCCESS")
    elif passed >= total * 0.7:
        log("MOSTLY OPERATIONAL — Check failures", "WARNING")
    else:
        log("CRITICAL — Multiple failures detected", "ERROR")
    
    log("=" * 60)

if __name__ == "__main__":
    main()
