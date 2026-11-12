#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════
REAL-TIME DATA FEEDER — UNIFIED
═══════════════════════════════════════════════════════════════════════

Pulls live data from verified working NOAA + USGS endpoints.
NO synthetic data. NO simulation. Only what instruments measure.

Writes to: real_time_data.json (shared state file)
Updates every 60 seconds.

Verified endpoints (tested 2026-06-20):
- Kp index:     services.swpc.noaa.gov/json/planetary_k_index_1m.json
- Solar wind:   services.swpc.noaa.gov/products/solar-wind/plasma-5-minute.json
- Magnetometers: services.swpc.noaa.gov/products/solar-wind/mag-5-minute.json
- X-ray flux:   services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json
- Alerts:       services.swpc.noaa.gov/products/alerts.json
- Forecast:     services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json
- Quakes:       earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson

All fetches route through aureon_fusion.api_communion (shared disk cache,
conditional GETs, per-host rate limiting, backoff + circuit breaker), so the
other planetary organs polling the same NOAA products hit this cache instead
of the network.
"""

import json, time, urllib.request, urllib.error, ssl, signal, sys, os
from datetime import datetime, timezone

from aureon_fusion.paths import WORKSPACE, LOGS
from aureon_fusion.api_communion import get_json as communion_get_json

# TLS verification enabled — certificates are verified against system trust store.
SSL_CONTEXT = ssl.create_default_context()

DATA_FILE = str(WORKSPACE / "real_time_data.json")
LOG_FILE = str(LOGS / "real_data_feeder.log")

# ═══════════════════════════════════════════════════════════════════════
# VERIFIED ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

ENDPOINTS = {
    "kp_index": {
        "url": "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json",
        "type": "json",
        "desc": "Planetary K-index, 1-minute",
    },
    "solar_wind_plasma": {
        "url": "https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json",
        "type": "json",
        "desc": "Solar wind plasma, 1-min (RTSW)",
    },
    "solar_wind_mag": {
        "url": "https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json",
        "type": "json",
        "desc": "Solar wind magnetic field, 1-min (RTSW)",
    },
    "xray_flux": {
        "url": "https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json",
        "type": "json",
        "desc": "GOES X-ray flux, 6-hour",
    },
    "alerts": {
        "url": "https://services.swpc.noaa.gov/products/alerts.json",
        "type": "json",
        "desc": "NOAA space weather alerts",
    },
    "forecast": {
        "url": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json",
        "type": "json",
        "desc": "Kp forecast",
    },
    "scales": {
        "url": "https://services.swpc.noaa.gov/products/noaa-scales.json",
        "type": "json",
        "desc": "NOAA space weather scales",
    },
    "quakes": {
        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_hour.geojson",
        "type": "json",
        "desc": "USGS significant earthquakes, last hour",
        # significant_hour rarely changes; a 300 s communion TTL means one
        # cheap ETag revalidation (304) per 5 cycles instead of a full
        # download every cycle. Freshness stays well under the feeder cycle.
        "ttl_s": 300,
    },
}

# Full-hour feed, only fetched when the significant feed reports activity
ALL_HOUR_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"

# ═══════════════════════════════════════════════════════════════════════
# FETCH
# ═══════════════════════════════════════════════════════════════════════

def fetch_json(url, timeout=15, ttl_s=45):
    """Fetch JSON via api_communion (shared cache + conditional GETs).

    TTL is set just under the 60 s cycle so each cycle revalidates with a
    conditional GET (304 when unchanged) instead of a full download, while
    sibling organs with longer TTLs are served from this shared cache.
    Endpoints that change rarely (USGS significant_hour) pass a longer
    ttl_s so most cycles are served straight from cache; the TTL expiring
    triggers one cheap ETag revalidation (304) rather than a full fetch.
    """
    data = communion_get_json(url, ttl_s=ttl_s, timeout=timeout, headers={
        'User-Agent': 'Mozilla/5.0 (Aureon-DataBot/1.0; RealDataOnly)',
        'Accept': 'application/json',
    })
    if data is None:
        return {"_error": f"Fetch failed (no cache)", "_url": url}
    return data

# ═══════════════════════════════════════════════════════════════════════
# PROCESS
# ═══════════════════════════════════════════════════════════════════════

def extract_kp_summary(data):
    """Extract latest Kp from NOAA data."""
    if not data or "_error" in data:
        return None
    try:
        if isinstance(data, list) and len(data) > 0:
            latest = data[-1]
            if isinstance(latest, dict):
                return {
                    "timestamp": latest.get("time_tag"),
                    "kp_index": latest.get("kp_index"),
                    "estimated_kp": latest.get("estimated_kp"),
                    "kp": latest.get("kp"),
                }
            # Fallback for list format
            return {
                "timestamp": latest[0] if len(latest) > 0 else None,
                "kp": float(latest[1]) if len(latest) > 1 else None,
            }
    except Exception as e:
        return {"_error": f"Parse error: {e}"}
    return None

def extract_solar_wind_summary(data):
    """Extract latest solar wind params (RTSW dict rows, legacy header rows)."""
    if not data or "_error" in data:
        return None
    try:
        if isinstance(data, list) and data and isinstance(data[-1], dict):
            latest = None
            for row in reversed(data):
                if (isinstance(row, dict) and row.get("active", True)
                        and row.get("proton_speed") is not None):
                    latest = row
                    break
            if latest is None:
                latest = data[-1]
            return {
                "time_tag": latest.get("time_tag"),
                "density": latest.get("proton_density"),
                "speed": latest.get("proton_speed"),
                "temperature": latest.get("proton_temperature"),
                "source": latest.get("source"),
            }
        if isinstance(data, list) and len(data) > 1 and isinstance(data[0], list):
            # Fallback for list format
            header = data[0]
            latest = data[-1]
            return {header[i]: latest[i] for i in range(min(len(header), len(latest)))}
    except Exception as e:
        return {"_error": f"Parse error: {e}"}
    return None

def extract_xray_summary(data):
    """Extract latest X-ray flux."""
    if not data or "_error" in data:
        return None
    try:
        if isinstance(data, list) and len(data) > 0:
            latest = data[-1]
            return {
                "time_tag": latest.get("time_tag") if isinstance(latest, dict) else None,
                "flux": latest.get("flux") if isinstance(latest, dict) else None,
                "energy": latest.get("energy") if isinstance(latest, dict) else None,
            }
    except Exception as e:
        return {"_error": f"Parse error: {e}"}
    return None

def extract_quake_summary(data):
    """Extract quake count and latest."""
    if not data or "_error" in data:
        return None
    try:
        features = data.get("features", [])
        count = len(features)
        latest = None
        if count > 0:
            f = features[0]
            props = f.get("properties", {})
            latest = {
                "mag": props.get("mag"),
                "place": props.get("place"),
                "time": props.get("time"),
            }
        return {"count": count, "latest": latest}
    except Exception as e:
        return {"_error": f"Parse error: {e}"}
    return None

# ═══════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ═══════════════════════════════════════════════════════════════════════

def collect_all():
    """Fetch all endpoints and compile unified state."""
    results = {}

    for name, cfg in ENDPOINTS.items():
        raw = fetch_json(cfg["url"], ttl_s=cfg.get("ttl_s", 45))
        results[name] = {
            "_raw": raw,
            "_fetched_at": datetime.now(timezone.utc).isoformat(),
            "_url": cfg["url"],
        }

    # Quake honesty rule: the feed polls the lightweight significant_hour
    # feed; when it reports activity, the full all_hour feed is fetched too
    # so the count/latest reflect every quake, not just significant ones.
    sig = results["quakes"]["_raw"]
    sig_count = None
    if isinstance(sig, dict) and "features" in sig:
        sig_count = len(sig.get("features", []))
    elif isinstance(sig, dict) and "_error" in sig:
        sig_count = None  # fetch failed — try the full feed below
    if sig_count or (isinstance(sig, dict) and "_error" in sig):
        full = fetch_json(ALL_HOUR_URL)
        if isinstance(full, dict) and "features" in full:
            results["quakes"] = {
                "_raw": full,
                "_fetched_at": datetime.now(timezone.utc).isoformat(),
                "_url": ALL_HOUR_URL,
                "_supplement_of": "significant_hour",
            }
    # Extract summaries
    summary = {
        "kp": extract_kp_summary(results["kp_index"]["_raw"]),
        "solar_wind": extract_solar_wind_summary(results["solar_wind_plasma"]["_raw"]),
        "xray": extract_xray_summary(results["xray_flux"]["_raw"]),
        "quakes": extract_quake_summary(results["quakes"]["_raw"]),
        "alerts_count": len(results["alerts"]["_raw"]) if isinstance(results["alerts"]["_raw"], list) else 0,
    }
    
    # Build unified output
    output = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "real_time_data_feeder",
        "data_policy": "REAL_ONLY_NO_SYNTHETIC",
        "summary": summary,
        "endpoints": results,
    }
    
    return output

def write_output(data):
    """Write to shared state file."""
    # Write atomically
    tmp = DATA_FILE + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, DATA_FILE)

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + "\n")

# ═══════════════════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════════════════

running = True

def shutdown(sig, frame):
    global running
    running = False
    log("Shutting down (signal received)")

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    log("═ REAL-TIME DATA FEEDER STARTED ═")
    log(f"Data file: {DATA_FILE}")
    log(f"Endpoints: {len(ENDPOINTS)}")
    
    while running:
        try:
            data = collect_all()
            write_output(data)
            
            # Quick summary log
            s = data["summary"]
            kp = s.get("kp", {})
            kp_val = kp.get("kp", "?") if kp else "?"
            quakes = s.get("quakes", {})
            quake_count = quakes.get("count", "?") if quakes else "?"
            
            log(f"Kp={kp_val} | Quakes={quake_count} | Alerts={s.get('alerts_count', '?')}")
            
        except Exception as e:
            log(f"ERROR: {e}")
        
        # Sleep with interrupt check
        for _ in range(60):
            if not running:
                break
            time.sleep(1)
    
    log("═ FEEDER STOPPED ═")
