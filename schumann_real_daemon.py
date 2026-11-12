#!/usr/bin/env python3
"""
Schumann Real-Data Feed Daemon (Windows/Desktop)
Pulls live Schumann data from ResonanceOne API and writes state files.
No hardware required. Pure real data.
"""
import sys, os, json, time, urllib.request, signal
from datetime import datetime, timezone
from pathlib import Path

from aureon_fusion.paths import WORKSPACE

PID_FILE = WORKSPACE / 'schumann_sensor.pid'
STATE_FILE = WORKSPACE / 'schumann_state.json'
LOG_FILE = WORKSPACE / 'schumann_sensor.log'
POLL_INTERVAL = 60
API_URL = 'https://resonanceone.app/api/now'

running = True
def handler(sig, frame):
    global running
    running = False

signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGTERM, handler)

def log(msg):
    ts = datetime.now(timezone.utc).isoformat()
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')

def fetch():
    try:
        req = urllib.request.Request(API_URL, headers={'User-Agent': 'Sero-Schumann/1.0'})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
            return data
    except Exception as e:
        log(f"FETCH ERROR: {e}")
        return None

def main():
    PID_FILE.write_text(str(os.getpid()))
    log(f"SCHUMANN SENSOR STARTED — PID {os.getpid()} — REAL DATA MODE")
    
    while running:
        data = fetch()
        if data:
            # FAIL-CLOSED: the resonanceone response must carry a measured
            # frequency. A missing/non-numeric frequency_hz means the fetch
            # did not return real telemetry (bad URL, missing/invalid API
            # key, error page) — never default to 7.83 Hz as if measured.
            freq = data.get('schumann_frequency_hz')
            if not isinstance(freq, (int, float)) or isinstance(freq, bool) or freq <= 0:
                log("UNAVAILABLE — response missing measured frequency_hz "
                    "(check API key/endpoint). Skipping write (fail-closed); "
                    "no fabricated 7.83 Hz default.")
            else:
                state = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "resonanceone_tomsk",
                    "frequency_hz": freq,
                    "activity_index": data.get('activity_index', 0),
                    "activity_label": data.get('activity_index_label', 'unknown'),
                    "kp_index": data.get('kp_index', 0),
                    "solar_flare_class": data.get('solar_flare_class', 'A0'),
                    "geomagnetic_status": data.get('geomagnetic_status', 'unknown'),
                    "summary": data.get('summary', ''),
                    "real_data": True,
                    "simulation": False
                }
                with open(STATE_FILE, 'w') as f:
                    json.dump(state, f, indent=2)
                log(f"Schumann: {state['frequency_hz']} Hz | Activity: {state['activity_index']}/100 | Kp: {state['kp_index']} | {state['geomagnetic_status']}")

        time.sleep(POLL_INTERVAL)
    
    PID_FILE.unlink(missing_ok=True)
    log("SCHUMANN SENSOR STOPPED")

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    main()
