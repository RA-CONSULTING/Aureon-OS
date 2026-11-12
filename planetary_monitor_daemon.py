#!/usr/bin/env python3
"""
ALERT
ALERT                                                                               ALERT
ALERT     PLANETARY PERSISTENT PLANETARY MONITOR DAEMON                                    ALERT
ALERT                                                                               ALERT
ALERT     Runs continuously, polling all open-source stations every 5 minutes.      ALERT
ALERT     Saves data, detects anomalies, alerts on significant changes.            ALERT
ALERT                                                                               ALERT
ALERT     Gary Leckey | Prime Sentinel of Gaia                                      ALERT
ALERT                                                                               ALERT
ALERT
"""

import sys, json, time, os, urllib.request, signal
from datetime import datetime, timezone
from pathlib import Path

# Configuration — cross-platform
from aureon_fusion.paths import WORKSPACE, PLANETARY_MONITOR
from aureon_fusion.api_communion import get_json as communion_get_json

BASE_DIR = WORKSPACE
DATA_DIR = str(PLANETARY_MONITOR)
LOG_FILE = f"{DATA_DIR}/daemon.log"
STATE_FILE = f"{DATA_DIR}/daemon_state.json"
POLL_INTERVAL = 300  # 5 minutes

os.makedirs(DATA_DIR, exist_ok=True)

# Running flag
running = True

def signal_handler(sig, frame):
    global running
    running = False
    print("\nPLANETARY Monitor daemon shutting down...")

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def log(msg):
    timestamp = datetime.now(timezone.utc).isoformat()
    line = f"[{timestamp}] {msg}"
    # Safe print — strip non-ASCII for Windows console
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode('ascii', 'replace').decode('ascii'))
    with open(LOG_FILE, "a", encoding='utf-8') as f:
        f.write(line + "\n")

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_kp": None, "alerts": [], "start_time": datetime.now(timezone.utc).isoformat()}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def fetch_noaa_kp():
    """Fetch latest Kp index from NOAA SWPC (via shared communion cache)"""
    try:
        url = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"
        data = communion_get_json(url, ttl_s=120, timeout=15)

        # Get latest observed (not predicted)
        observed = [d for d in data if d.get('observed') == 'observed']
        latest = observed[-1] if observed else data[-1]
        
        return {
            "time_tag": latest['time_tag'],
            "kp": latest['kp'],
            "status": latest['observed'],
            "scale": latest.get('noaa_scale', 'N/A'),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

def fetch_noaa_scales():
    """Fetch current NOAA space weather scales (via shared communion cache)"""
    try:
        url = "https://services.swpc.noaa.gov/products/noaa-scales.json"
        data = communion_get_json(url, ttl_s=120, timeout=15)
        
        current = data.get("0", {})
        return {
            "date": current.get('DateStamp'),
            "time": current.get('TimeStamp'),
            "geomagnetic": current.get('G', {}),
            "radio": current.get('R', {}),
            "solar": current.get('S', {}),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

def fetch_ace_plasma():
    """Fetch solar wind plasma data (RTSW 1-min, via shared communion cache)"""
    try:
        url = "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json"
        data = communion_get_json(url, ttl_s=120, timeout=15)
        if not data:
            raise ValueError("no data")

        latest = None
        for row in reversed(data):
            if isinstance(row, dict) and row.get("active", True) \
                    and row.get("proton_speed") is not None:
                latest = row
                break
        if latest is None:
            latest = data[-1]

        return {
            "time": latest.get("time_tag"),
            "density": latest.get("proton_density"),
            "speed": latest.get("proton_speed"),
            "temperature": latest.get("proton_temperature"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()}

def check_anomalies(current_kp, state):
    """Check for significant changes and generate alerts"""
    alerts = []
    
    last_kp = state.get('last_kp')
    if last_kp is not None:
        kp_change = current_kp['kp'] - last_kp['kp']
        
        # Alert on significant changes
        if abs(kp_change) >= 1.0:
            direction = "RISING" if kp_change > 0 else "FALLING"
            alerts.append({
                "level": "WARNING",
                "message": f"Kp {direction} sharply: {last_kp['kp']:.2f} → {current_kp['kp']:.2f}",
                "time": datetime.now(timezone.utc).isoformat(),
            })
        
        if current_kp['kp'] >= 5.0:
            alerts.append({
                "level": "CRITICAL",
                "message": f"Geomagnetic storm in progress! Kp = {current_kp['kp']}",
                "time": datetime.now(timezone.utc).isoformat(),
            })
        
        if current_kp['kp'] >= 7.0:
            alerts.append({
                "level": "EMERGENCY",
                "message": f"SEVERE geomagnetic storm! Kp = {current_kp['kp']}",
                "time": datetime.now(timezone.utc).isoformat(),
            })
    
    return alerts

def save_reading(reading_type, data):
    """Save a reading to the appropriate file"""
    filename = f"{DATA_DIR}/{reading_type}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.jsonl"
    with open(filename, "a") as f:
        f.write(json.dumps(data) + "\n")

def main():
    log("=" * 70)
    log("PLANETARY PERSISTENT PLANETARY MONITOR DAEMON STARTED")
    log(f"Poll interval: {POLL_INTERVAL} seconds ({POLL_INTERVAL/60:.0f} minutes)")
    log("=" * 70)
    
    state = load_state()
    
    cycle = 0
    while running:
        cycle += 1
        log(f"--- Cycle {cycle} ---")
        
        # Fetch all data sources
        kp_data = fetch_noaa_kp()
        scales_data = fetch_noaa_scales()
        plasma_data = fetch_ace_plasma()
        
        # Log results
        if 'error' not in kp_data:
            log(f"Kp: {kp_data['kp']:.2f} at {kp_data['time_tag']} ({kp_data['status']})")
            save_reading("kp", kp_data)
            
            # Check for anomalies
            alerts = check_anomalies(kp_data, state)
            for alert in alerts:
                log(f"ALERT ALERT [{alert['level']}]: {alert['message']}")
                state['alerts'].append(alert)
            
            state['last_kp'] = kp_data
        else:
            log(f"Kp fetch error: {kp_data.get('error')}")
        
        if 'error' not in scales_data:
            g_scale = scales_data.get('geomagnetic', {}).get('Scale', 'N/A')
            log(f"Geomagnetic scale: {g_scale}")
            save_reading("scales", scales_data)
        
        if 'error' not in plasma_data:
            log(f"Solar wind: {plasma_data.get('speed', 'N/A')} km/s, "
                f"density: {plasma_data.get('density', 'N/A')} p/cm³")
            save_reading("plasma", plasma_data)
        
        save_state(state)
        
        # Wait for next cycle
        log(f"Sleeping {POLL_INTERVAL} seconds...")
        
        # Sleep in small increments to allow clean shutdown
        slept = 0
        while slept < POLL_INTERVAL and running:
            time.sleep(1)
            slept += 1
    
    log("PLANETARY Monitor daemon stopped.")
    save_state(state)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
