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

def _number(value):
    """A real finite number from the provider, or None. Never a stand-in 0."""
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if value == value and value not in (float("inf"), float("-inf")) else None


def build_state(data):
    """The state to write for one provider response, or None (fail-closed).

    ResonanceOne keeps sending schumann_frequency_hz = 7.83 while it flags the
    Tomsk feed as paused (schumann_unavailable = true, data_quality = "stale").
    That 7.83 is the provider's placeholder, not a measurement, so it must not
    be written as real_data. Missing activity / Kp / flare stay None, never 0.
    """
    if not isinstance(data, dict):
        return None, "response is not a JSON object"
    freq = data.get('schumann_frequency_hz')
    if not isinstance(freq, (int, float)) or isinstance(freq, bool) or freq <= 0:
        return None, "response missing measured frequency_hz"
    if data.get('schumann_unavailable') is True:
        return None, f"provider marks Schumann unavailable (last reading {data.get('last_schumann_at')})"
    quality = data.get('data_quality')
    if isinstance(quality, str) and quality.strip().lower() in ('stale', 'unavailable', 'offline', 'missing'):
        return None, f"provider data_quality is {quality!r}"
    state = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "observed_at": data.get('last_schumann_at'),
        "source": "resonanceone_tomsk",
        "frequency_hz": freq,
        "activity_index": _number(data.get('activity_index')),
        "activity_label": data.get('activity_index_label') or 'unknown',
        "kp_index": _number(data.get('kp_index')),
        "solar_flare_class": data.get('solar_flare_class'),
        "geomagnetic_status": data.get('geomagnetic_status') or 'unknown',
        "data_quality": quality,
        "summary": data.get('summary', ''),
        "real_data": True,
        "simulation": False
    }
    return state, None


def main():
    PID_FILE.write_text(str(os.getpid()))
    log(f"SCHUMANN SENSOR STARTED — PID {os.getpid()} — REAL DATA MODE")

    while running:
        data = fetch()
        if data:
            # FAIL-CLOSED: write only a measured, provider-live Schumann
            # reading. No fabricated 7.83 Hz default, and no provider
            # placeholder written as if measured.
            state, why = build_state(data)
            if state is None:
                log(f"UNAVAILABLE — {why}. Skipping write (fail-closed).")
            else:
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
