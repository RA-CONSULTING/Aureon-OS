#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║          AUREON ATN MONITOR — EARTH HAZARD INTELLIGENCE ENGINE          ║
║  "What the Earth feels, the system feels.  What the system feels,       ║
║   becomes the trade."                                                   ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  Integrates 7 real-time planetary hazard streams into the cognitive      ║
║  loop.  Every stream is polled silently in the background;  the result   ║
║  is a single EarthHazardState with a trading_impact score (0.0–1.0).    ║
║                                                                          ║
║  STREAMS:                                                                ║
║   1. 🌋 Earthquakes   — USGS Earthquake Hazards (M4.5+ / hourly feed)   ║
║   2. 🌋 Volcanoes     — USGS Volcano Hazards + GVP alert level          ║
║   3. 🌪  Severe Weather— NOAA NWS Active Alerts (Extreme/Severe)        ║
║   4. ☀️  Space Weather — NOAA SWPC Kp Index + solar flares              ║
║   5. 🔥 Wildfires     — NASA FIRMS VIIRS thermal detection              ║
║   6. 🪐 Near-Earth Obj— NASA JPL CNEOS close-approach feed             ║
║   7. 🌍 Schumann Res. — Tomsk / Barcelona live Schumann 7.83 Hz        ║
║                                                                          ║
║  TRADING IMPACT (0.0 = red alert, 1.0 = clear field):                   ║
║   • Each stream scores 0–1; weighted average → risk_factor              ║
║   • Veto triggered if:  M7+ quake / Volcanic WATCH+ / KP≥7 / X-flare  ║
║   • Orca sees: {risk_factor, veto, reason, active_alerts}               ║
║                                                                          ║
║  Gary Leckey | March 2026                                               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import math
import os
import time
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from aureon.observer.real_data_contract import make_live_metric, make_no_data_metric

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS — API ENDPOINTS (all public / no auth unless noted)
# ─────────────────────────────────────────────────────────────────────────────

# 1. USGS Earthquakes
_QUAKE_SIGNIFICANT_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_hour.geojson"
)
_QUAKE_M45_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_hour.geojson"
)

# 2. USGS Volcanoes (current volcano alert levels)
_VOLCANO_USGS_URL = (
    "https://volcanoes.usgs.gov/vhp/api/v1/volcano/USA"
)

# 3. NOAA Severe Weather Alerts
_WEATHER_ALERTS_URL = (
    "https://api.weather.gov/alerts/active"
    "?status=actual&severity=Extreme,Severe&urgency=Immediate,Expected"
)

# 4. Space Weather — reused from aureon_space_weather_bridge
_NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
_NOAA_FLARES_URL = "https://services.swpc.noaa.gov/json/goes/primary/xray-flares-7-day.json"

# 5. NASA FIRMS Wildfires — DEMO key works for global snapshot
#    Full key: set FIRMS_MAP_KEY in .env
_FIRMS_COUNT_URL = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_NRT/world/1"
)

# 6. NASA JPL Near-Earth Objects
_NEO_URL = (
    "https://api.nasa.gov/neo/rest/v1/feed"
)

# 7. Schumann — Tomsk public endpoint (HTML parse) + Barcelona fallback
# (reuse SchumannResonanceBridge if available)

# ─────────────────────────────────────────────────────────────────────────────
# TTL CACHE PER STREAM (seconds)
# ─────────────────────────────────────────────────────────────────────────────
_TTL = {
    "quake":    60,    # USGS updates every 60s
    "volcano":  300,   # Alert levels change slowly
    "weather":  120,   # NWS updates alerts rapidly
    "space":    300,   # KP / flare updates every 5 min
    "fire":     600,   # FIRMS 10-min cadence
    "neo":      3600,  # Asteroid positions — hourly sufficient
    "schumann": 60,    # Live beat
}

# ─────────────────────────────────────────────────────────────────────────────
# STREAM WEIGHTS in the final risk_factor composite
# ─────────────────────────────────────────────────────────────────────────────
_WEIGHTS = {
    "quake":    0.25,  # High priority — financial markets react to M7+
    "volcano":  0.10,
    "weather":  0.15,
    "space":    0.20,  # Solar flares knock out communications
    "fire":     0.08,
    "neo":      0.05,  # Rarissimum
    "schumann": 0.17,  # Earth heartbeat — Lyra's earth chamber
}


# ─────────────────────────────────────────────────────────────────────────────
# DATACLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StreamResult:
    """A single data-source reading."""
    name: str
    score: float          # 0.0 (danger) → 1.0 (clear)
    veto: bool            # Hard stop for this stream alone
    alerts: List[str]     # Human-readable alert descriptions
    raw: Dict[str, Any]   # Raw parsed data for display
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class EarthHazardState:
    """
    Merged snapshot of all 7 streams.

    risk_factor  0.0 = catastrophic hazard → full trade veto
                 1.0 = clear Earth field    → normal sizing
    """
    timestamp: float
    risk_factor: Optional[float]  # weighted composite; None when data is unavailable
    veto: bool                # any single veto → True
    reason: str               # brief justification
    active_alerts: List[str]  # all active alert strings
    streams: Dict[str, StreamResult]
    actionable: bool = True
    non_actionable_streams: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        stream_controls = {k: _stream_control(v) for k, v in self.streams.items()}
        non_actionable = sorted(
            set(self.non_actionable_streams)
            | {name for name, control in stream_controls.items() if control["non_actionable"]}
        )
        actionable = self.actionable and not self.veto and not non_actionable
        return {
            "timestamp":     self.timestamp,
            "received_at":   self.timestamp,
            "source_timestamp": None,  # An aggregate has no provider event time.
            "risk_factor":   round(self.risk_factor, 4) if actionable and self.risk_factor is not None else None,
            "veto":          self.veto,
            "actionable":    actionable,
            "reason":        self.reason,
            "active_alerts": self.active_alerts[:10],
            "provenance": {
                "truth_status": "no_data" if not actionable else "available",
                "non_actionable_streams": non_actionable,
                "source_timestamp": None,
                "received_at": self.timestamp,
            },
            "streams":       {k: {
                "score": round(v.score, 4),
                "veto":  v.veto,
                "alerts":v.alerts[:3],
                "error": v.error,
                "truth_status": stream_controls[k]["truth_status"],
                "source_id": stream_controls[k]["source_id"],
                "blocker": stream_controls[k]["blocker"],
                "source_timestamp": stream_controls[k]["source_timestamp"],
                "received_at": stream_controls[k]["received_at"],
                "actionable": not stream_controls[k]["non_actionable"],
            } for k, v in self.streams.items()},
        }


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _stream_control(result: StreamResult) -> Dict[str, Any]:
    """Return provenance controls without turning a receipt clock into source time."""
    raw = result.raw if isinstance(result.raw, dict) else {}
    metric = raw.get("real_data") if isinstance(raw.get("real_data"), dict) else {}
    truth_status = metric.get("truth_status")
    blocker = metric.get("blocker") or result.error or ""
    missing = not raw
    no_data = truth_status == "no_data"
    return {
        "truth_status": truth_status,
        "source_id": metric.get("source_id"),
        "blocker": blocker,
        "source_timestamp": raw.get("source_timestamp"),
        "received_at": result.timestamp,
        "non_actionable": bool(result.error) or no_data or missing,
    }


def _get(url: str, params: Optional[Dict] = None, timeout: int = 10) -> Any:
    """Lightweight GET with timeout; returns parsed JSON or raises."""
    resp = requests.get(url, params=params, timeout=timeout,
                        headers={"User-Agent": "AureonATNMonitor/1.0"})
    resp.raise_for_status()
    return resp.json()


def _no_data_stream(
    name: str,
    *,
    source_id: str,
    source_name: str,
    source_url: str,
    blocker: str,
    score: float = 0.9,
) -> StreamResult:
    metric = make_no_data_metric(
        f"atn.{name}",
        source_id=source_id,
        source_name=source_name,
        source_url=source_url,
        blocker=blocker,
        freshness_ttl_sec=_TTL.get(name, 300),
    )
    return StreamResult(
        name=name,
        score=score,
        veto=False,
        alerts=[f"{name} unavailable: {blocker}"],
        raw={"real_data": metric},
        error=blocker,
    )


# ─────────────────────────────────────────────────────────────────────────────
# STREAM FETCHERS
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_earthquakes() -> StreamResult:
    """
    USGS GeoJSON feed — significant quakes + M4.5+ past hour.
    M7+ → veto; M6+ → risk drops; M5+ → mild flag.
    """
    name = "quake"
    alerts: List[str] = []
    max_mag = 0.0
    count_45 = 0
    try:
        sig = _get(_QUAKE_SIGNIFICANT_URL)
        for feat in sig.get("features", []):
            p   = feat.get("properties", {})
            mag = float(p.get("mag") or 0)
            place = p.get("place", "unknown")
            if mag >= 4.0:
                alerts.append(f"M{mag:.1f} {place}")
                max_mag = max(max_mag, mag)

        m45 = _get(_QUAKE_M45_URL)
        count_45 = len(m45.get("features", []))

        # Score: calm baseline 1.0, degrades with magnitude
        if max_mag >= 7.0:
            score = 0.0; veto = True
        elif max_mag >= 6.5:
            score = 0.25; veto = False
        elif max_mag >= 6.0:
            score = 0.45; veto = False
        elif max_mag >= 5.5:
            score = 0.65; veto = False
        elif max_mag >= 5.0:
            score = 0.80; veto = False
        else:
            score = 1.0; veto = False

        # Multiple M4.5+ events in one hour also depresses score slightly
        if count_45 >= 10:
            score = _clamp(score - 0.10)

        return StreamResult(
            name=name, score=score, veto=veto, alerts=alerts,
            raw={"max_mag": max_mag, "count_4_5_hour": count_45},
        )
    except Exception as e:
        return StreamResult(name=name, score=0.9, veto=False, alerts=[],
                            raw={}, error=str(e))


def _fetch_volcanoes() -> StreamResult:
    """
    USGS Volcano Hazards — parse alert levels.
    WATCH or WARNING → veto.  ADVISORY → depressed score.
    """
    name = "volcano"
    alerts: List[str] = []
    highest = "NORMAL"
    _order = {"NORMAL": 0, "ADVISORY": 1, "WATCH": 2, "WARNING": 3}
    try:
        data = _get(_VOLCANO_USGS_URL, timeout=12)
        volcanoes = data if isinstance(data, list) else data.get("items", [])
        for v in volcanoes:
            av = (v.get("alert_level") or v.get("alertLevel") or "NORMAL").upper()
            if _order.get(av, 0) > _order.get(highest, 0):
                highest = av
            if av in ("WATCH", "WARNING", "ADVISORY"):
                vname = v.get("name") or v.get("vname") or "Unknown"
                alerts.append(f"{av}: {vname}")

        if highest == "WARNING":
            score = 0.1; veto = True
        elif highest == "WATCH":
            score = 0.3; veto = True
        elif highest == "ADVISORY":
            score = 0.6; veto = False
        else:
            score = 1.0; veto = False

        return StreamResult(
            name=name, score=score, veto=veto, alerts=alerts,
            raw={"highest_alert": highest, "alert_count": len(alerts)},
        )
    except Exception as e:
        return StreamResult(name=name, score=0.9, veto=False, alerts=[],
                            raw={}, error=str(e))


def _fetch_weather() -> StreamResult:
    """
    NOAA NWS active alerts — only market-relevant catastrophic events trigger veto.

    Veto events (true infrastructure/market catastrophes):
      Tornado Emergency, Major Hurricane Warning, Flash Flood Emergency,
      Tsunami Warning, Extreme Wind Warning, Dust Storm Warning (rare)

    Score-depressing events (significant but not veto):
      Blizzard, Severe Thunderstorm, Winter Storm, Flood Warning, etc.
    """
    name = "weather"

    # These NWS event types warrant a hard trade veto
    _VETO_EVENTS = {
        "Tornado Emergency",
        "Flash Flood Emergency",
        "Tsunami Warning",
        "Extreme Wind Warning",
        "Hurricane Warning",
        "Typhoon Warning",
        "Special Weather Statement",   # only when paired with 'Emergency'
    }
    # These depress score but do not veto
    _RISK_EVENTS = {
        "Blizzard Warning", "Ice Storm Warning", "High Wind Warning",
        "Severe Thunderstorm Warning", "Tornado Warning", "Flash Flood Warning",
        "Hurricane Watch", "Typhoon Watch", "Winter Storm Warning",
        "Freeze Warning", "Extreme Heat Warning", "Dense Fog Advisory",
        "Red Flag Warning", "Storm Warning",
    }

    alerts: List[str] = []
    veto_count = 0
    risk_count = 0
    try:
        data     = _get(_WEATHER_ALERTS_URL, timeout=12)
        features = data.get("features", [])
        for feat in features:
            p   = feat.get("properties", {})
            evt = (p.get("event") or "Alert").strip()
            area = (p.get("areaDesc") or "")[:50]
            alerts.append(f"{evt}: {area}")
            if evt in _VETO_EVENTS:
                veto_count += 1
            elif evt in _RISK_EVENTS:
                risk_count += 1

        veto  = veto_count >= 1
        if veto_count >= 5:
            score = 0.05
        elif veto_count >= 2:
            score = 0.2
        elif veto_count >= 1:
            score = 0.35
        elif risk_count >= 50:
            score = 0.55
        elif risk_count >= 20:
            score = 0.70
        elif risk_count >= 5:
            score = 0.82
        else:
            score = 1.0

        return StreamResult(
            name=name, score=score, veto=veto, alerts=alerts[:10],
            raw={"veto_events": veto_count, "risk_events": risk_count,
                 "total": len(features)},
        )
    except Exception as e:
        return StreamResult(name=name, score=0.9, veto=False, alerts=[],
                            raw={}, error=str(e))


def _fetch_space_weather() -> StreamResult:
    """
    NOAA SWPC — Kp index + GOES X-ray flares.
    X-class flare → veto.  KP ≥ 7 → veto.  KP ≥ 5 → risk.
    Reuses aureon_space_weather_bridge if available.
    """
    name = "space"
    alerts: List[str] = []

    # ── try the existing bridge first ──────────────────────────────────────
    try:
        from aureon.data_feeds.aureon_space_weather_bridge import get_space_weather_bridge
        bridge = get_space_weather_bridge()
        sw = bridge.get_reading()
        kp   = float(sw.kp_index)
        cat  = sw.kp_category
        flares_24h = int(sw.solar_flares_24h)

        if kp >= 7 or flares_24h > 0:
            alerts.append(f"KP={kp:.1f} ({cat}), {flares_24h} flares (24h)")

        # Detect X-class from bridge reading; fall through to raw fetch below
        x_class = False
        try:
            raw_flares = _get(_NOAA_FLARES_URL, timeout=8)
            for f in (raw_flares if isinstance(raw_flares, list) else []):
                cls = (f.get("class") or "").upper()
                if cls.startswith("X"):
                    x_class = True
                    alerts.append(f"X-class flare: {cls}")
        except Exception:
            pass

        if x_class or kp >= 7:
            score = 0.05; veto = True
        elif kp >= 5:
            score = 0.4; veto = False
        elif kp >= 4:
            score = 0.65; veto = False
        elif kp >= 3:
            score = 0.80; veto = False
        else:
            score = 1.0; veto = False

        return StreamResult(
            name=name, score=score, veto=veto, alerts=alerts,
            raw={"kp": kp, "kp_category": cat, "flares_24h": flares_24h,
                 "x_class": x_class},
        )
    except Exception:
        pass  # fall through to direct fetch

    # ── direct NOAA fetch (bridge unavailable) ─────────────────────────────
    try:
        kp_data = _get(_NOAA_KP_URL, timeout=8)
        # Format: [[time_tag, Kp, ...], ...]
        latest  = [row for row in kp_data[1:] if len(row) >= 2]
        kp = float(latest[-1][1]) if latest else 3.0
        alerts.append(f"Kp={kp:.1f}")

        x_class = False
        try:
            raw_flares = _get(_NOAA_FLARES_URL, timeout=8)
            for f in (raw_flares if isinstance(raw_flares, list) else []):
                cls = (f.get("class") or "").upper()
                if cls.startswith("X"):
                    x_class = True
                    alerts.append(f"X-flare: {cls}")
        except Exception:
            pass

        if x_class or kp >= 7:
            score = 0.05; veto = True
        elif kp >= 5:
            score = 0.4; veto = False
        elif kp >= 4:
            score = 0.65; veto = False
        else:
            score = 1.0; veto = False

        return StreamResult(
            name=name, score=score, veto=veto, alerts=alerts,
            raw={"kp": kp, "x_class": x_class},
        )
    except Exception as e:
        return StreamResult(name=name, score=0.85, veto=False, alerts=[],
                            raw={}, error=str(e))


def _fetch_wildfires() -> StreamResult:
    """
    NASA FIRMS global active fire count.
    Uses FIRMS_MAP_KEY env var. Missing keys produce a no_data sentinel.
    High count in a trading session = supply chain / energy risk.
    """
    name = "fire"
    key = os.getenv("FIRMS_MAP_KEY", "").strip()
    if not key:
        return _no_data_stream(
            name,
            source_id="nasa_firms",
            source_name="NASA FIRMS Active Fire Data",
            source_url=_FIRMS_COUNT_URL.format(key="{FIRMS_MAP_KEY}"),
            blocker="missing_env:FIRMS_MAP_KEY",
        )
    url  = _FIRMS_COUNT_URL.format(key=key)
    alerts: List[str] = []
    try:
        # FIRMS returns CSV — just count lines (header + data rows)
        resp = requests.get(url, timeout=15,
                            headers={"User-Agent": "AureonATNMonitor/1.0"})
        resp.raise_for_status()
        lines = [l for l in resp.text.strip().splitlines() if l.strip()]
        count = max(0, len(lines) - 1)  # subtract header

        alerts.append(f"{count} active fire detections (FIRMS VIIRS, 24h)")

        if count >= 50000:
            score = 0.3; veto = False
        elif count >= 20000:
            score = 0.55; veto = False
        elif count >= 5000:
            score = 0.75; veto = False
        else:
            score = 1.0; veto = False

        return StreamResult(
            name=name, score=score, veto=False, alerts=alerts,
            raw={
                "detection_count": count,
                "real_data": make_live_metric(
                    "atn.fire.detection_count",
                    source_id="nasa_firms",
                    source_name="NASA FIRMS Active Fire Data",
                    source_url=_FIRMS_COUNT_URL.format(key="{FIRMS_MAP_KEY}"),
                    value=count,
                    unit="detections",
                    freshness_ttl_sec=_TTL[name],
                ),
            },
        )
    except Exception as e:
        return _no_data_stream(
            name,
            source_id="nasa_firms",
            source_name="NASA FIRMS Active Fire Data",
            source_url=_FIRMS_COUNT_URL.format(key="{FIRMS_MAP_KEY}"),
            blocker=f"{type(e).__name__}:{str(e)[:120]}",
        )


def _fetch_neo() -> StreamResult:
    """
    NASA JPL CNEOS — Near-Earth Objects close approach today + tomorrow.
    Objects within 0.002 AU (Lunar Distance ≈5) flag caution (rare event).
    Objects within 0.001 AU → risk signal.  No veto (not actionable).
    """
    name = "neo"
    alerts: List[str] = []
    nasa_key = os.getenv("NASA_API_KEY", "").strip()
    if not nasa_key:
        return _no_data_stream(
            name,
            source_id="nasa_neo",
            source_name="NASA Near Earth Object Web Service",
            source_url=_NEO_URL,
            blocker="missing_env:NASA_API_KEY",
            score=0.95,
        )
    today  = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tmrw   = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        data = _get(_NEO_URL, params={
            "start_date": today, "end_date": tmrw,
            "api_key": nasa_key,
        }, timeout=15)

        near_earth = []
        for date_key, objects in data.get("near_earth_objects", {}).items():
            for obj in objects:
                for ca in obj.get("close_approach_data", []):
                    au = float(ca.get("miss_distance", {}).get("astronomical", 1.0))
                    km = float(ca.get("miss_distance", {}).get("kilometers", 1e9))
                    name_str = obj.get("name", "Unknown")
                    haz = obj.get("is_potentially_hazardous_asteroid", False)
                    near_earth.append((au, name_str, haz, km))

        near_earth.sort()
        closest = near_earth[0][0] if near_earth else 1.0
        hazardous = [n for n in near_earth if n[2]]

        for au, nm, haz, km in near_earth[:5]:
            tag = "⚠ PHO" if haz else "NEO"
            alerts.append(f"{tag}: {nm} @ {au:.4f} AU ({km:,.0f} km)")

        if closest <= 0.001:
            score = 0.6; veto = False
        elif closest <= 0.002:
            score = 0.75; veto = False
        elif hazardous:
            score = 0.85; veto = False
        else:
            score = 1.0; veto = False

        return StreamResult(
            name=name, score=score, veto=False, alerts=alerts,
            raw={
                "closest_au": round(closest, 6),
                "neo_count": len(near_earth),
                "potentially_hazardous": len(hazardous),
                "real_data": make_live_metric(
                    "atn.neo.close_approach",
                    source_id="nasa_neo",
                    source_name="NASA Near Earth Object Web Service",
                    source_url=_NEO_URL,
                    value={"closest_au": round(closest, 6), "neo_count": len(near_earth)},
                    freshness_ttl_sec=_TTL[name],
                ),
            },
        )
    except Exception as e:
        return _no_data_stream(
            name,
            source_id="nasa_neo",
            source_name="NASA Near Earth Object Web Service",
            source_url=_NEO_URL,
            blocker=f"{type(e).__name__}:{str(e)[:120]}",
            score=0.95,
        )


def _fetch_schumann() -> StreamResult:
    """
    Live Schumann resonance from Tomsk / Barcelona.
    Reuses SchumannResonanceBridge if available; otherwise returns neutral.
    7.83 Hz = Earth heartbeat.  Disturbed field = elevated resonance / noise.
    """
    name = "schumann"
    alerts: List[str] = []
    try:
        from aureon.harmonic.aureon_schumann_resonance_bridge import get_schumann_bridge
        bridge = get_schumann_bridge()
        reading = bridge.get_reading()

        hz   = float(reading.fundamental_hz)
        dist = float(reading.earth_disturbance_level)
        phase= reading.resonance_phase
        coh  = float(reading.coherence_boost)

        deviation = abs(hz - 7.83) / 7.83  # fractional deviation from baseline

        if phase in ("disturbed",) or dist >= 0.7:
            alerts.append(f"Schumann disturbed: {hz:.2f} Hz (disturbance={dist:.0%})")
            score = _clamp(0.5 - dist * 0.4)
            veto  = False
        elif deviation > 0.15 or dist >= 0.4:
            alerts.append(f"Schumann elevated: {hz:.2f} Hz")
            score = _clamp(0.75 - dist * 0.3)
            veto  = False
        else:
            score = _clamp(0.9 + coh * 0.1)
            veto  = False

        return StreamResult(
            name=name, score=score, veto=veto, alerts=alerts,
            raw={"hz": hz, "disturbance": dist, "phase": phase,
                 "coherence_boost": coh},
        )
    except Exception as e:
        return StreamResult(name=name, score=0.85, veto=False, alerts=[],
                            raw={}, error=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# ATN MONITOR — main class
# ─────────────────────────────────────────────────────────────────────────────

_FETCHERS = {
    "quake":    _fetch_earthquakes,
    "volcano":  _fetch_volcanoes,
    "weather":  _fetch_weather,
    "space":    _fetch_space_weather,
    "fire":     _fetch_wildfires,
    "neo":      _fetch_neo,
    "schumann": _fetch_schumann,
}


class ATNMonitor:
    """
    Earth Hazard Intelligence Engine.

    Call .get_state() to get the latest merged EarthHazardState.
    All 7 streams are fetched lazily and cached independently.

    Thread-safe (lock per stream).
    """

    def __init__(self):
        self._cache:   Dict[str, Tuple[float, StreamResult]] = {}  # name → (ts, result)
        self._lock     = threading.Lock()
        logger.info("🌍 ATN Monitor initialised — 7 Earth hazard streams ready")

    # ── single stream ─────────────────────────────────────────────────────────

    def _get_stream(self, name: str) -> StreamResult:
        now   = time.time()
        ttl   = _TTL[name]
        fetch = _FETCHERS[name]
        with self._lock:
            cached = self._cache.get(name)
            if cached and (now - cached[0]) < ttl:
                return cached[1]
        # Fetch outside lock
        try:
            result = fetch()
        except Exception as e:
            result = StreamResult(name=name, score=0.9, veto=False,
                                  alerts=[], raw={}, error=str(e))
        with self._lock:
            self._cache[name] = (time.time(), result)
        return result

    # ── merged state ─────────────────────────────────────────────────────────

    def get_state(self) -> EarthHazardState:
        """
        Fetch all 7 streams (from cache if fresh) and merge into one state.
        Safe to call every trading cycle — cached data serves immediately.
        """
        streams: Dict[str, StreamResult] = {}
        for name in _FETCHERS:
            streams[name] = self._get_stream(name)

        controls = {name: _stream_control(stream) for name, stream in streams.items()}
        non_actionable_streams = [
            name for name, control in controls.items() if control["non_actionable"]
        ]
        if non_actionable_streams:
            risk_factor = None
        else:
            total_w = sum(_WEIGHTS.values())
            risk_factor = sum(
                _WEIGHTS[n] * streams[n].score for n in streams
            ) / total_w

        # Missing, errored, or no-data streams never become clear-field evidence.
        veto = any(s.veto for s in streams.values()) or bool(non_actionable_streams)

        # Collect all active alerts + build reason
        active_alerts: List[str] = []
        veto_reasons:  List[str] = []
        for n, s in streams.items():
            active_alerts.extend(s.alerts)
            if s.veto:
                veto_reasons.append(f"{n}:{s.alerts[0] if s.alerts else 'VETO'}")

        if non_actionable_streams:
            reason = "NO DATA - action blocked: " + ", ".join(sorted(non_actionable_streams))
        elif veto:
            reason = "EARTH VETO — " + "; ".join(veto_reasons)
        elif risk_factor < 0.5:
            reason = "HIGH HAZARD FIELD — elevated risk across streams"
        elif risk_factor < 0.75:
            reason = "MODERATE HAZARD — some streams flagged"
        else:
            reason = "CLEAR FIELD — Earth systems nominal"

        return EarthHazardState(
            timestamp=time.time(),
            risk_factor=_clamp(risk_factor) if risk_factor is not None else None,
            veto=veto,
            reason=reason,
            active_alerts=active_alerts,
            streams=streams,
            actionable=not veto,
            non_actionable_streams=non_actionable_streams,
        )

    def get_trading_impact(self) -> Dict[str, Any]:
        """
        Convenience wrapper for cognitive_cycle.think().
        Returns a dict ready to be stored on CognitiveState.
        """
        state = self.get_state()
        return state.to_dict()

    # ── pretty print ─────────────────────────────────────────────────────────

    def print_dashboard(self) -> None:
        state = self.get_state()
        _print_dashboard(state)


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD RENDERER
# ─────────────────────────────────────────────────────────────────────────────

_STREAM_ICONS = {
    "quake":    "🌋",
    "volcano":  "🌋",
    "weather":  "🌪 ",
    "space":    "☀️ ",
    "fire":     "🔥",
    "neo":      "🪐",
    "schumann": "🌍",
}


def _score_bar(score: float, width: int = 20) -> str:
    filled = int(round(score * width))
    empty  = width - filled
    colour = "\033[92m" if score >= 0.75 else ("\033[93m" if score >= 0.50 else "\033[91m")
    rst    = "\033[0m"
    return f"{colour}{'█' * filled}{'░' * empty}{rst} {score:.2f}"


def _print_dashboard(state: EarthHazardState) -> None:
    W     = 70
    bold  = "\033[1m"
    rst   = "\033[0m"
    cyan  = "\033[96m"
    red   = "\033[91m"
    grn   = "\033[92m"
    yel   = "\033[93m"

    ts = datetime.fromtimestamp(state.timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    rf_colour = grn if state.risk_factor >= 0.75 else (yel if state.risk_factor >= 0.5 else red)

    print(f"\n{bold}{cyan}{'═' * W}{rst}")
    print(f"{bold}{cyan}  🌍 ATN MONITOR — EARTH HAZARD DASHBOARD       {ts}{rst}")
    print(f"{bold}{cyan}{'═' * W}{rst}")
    print(f"  RISK FACTOR  {_score_bar(state.risk_factor)}   {rf_colour}{'▲ VETO' if state.veto else ''}{rst}")
    print(f"  STATUS       {state.reason}")
    print(f"  {'─' * (W - 2)}")

    for name, stream in state.streams.items():
        icon = _STREAM_ICONS.get(name, "  ")
        veto_tag = f"  {red}[VETO]{rst}" if stream.veto else ""
        err_tag  = f"  \033[33m[no data]{rst}" if stream.error else ""
        print(f"  {icon} {name.upper():<10} {_score_bar(stream.score, 16)}{veto_tag}{err_tag}")
        for alert in stream.alerts[:2]:
            print(f"               \033[93m↳ {alert[:55]}{rst}")

    if state.active_alerts:
        print(f"  {'─' * (W - 2)}")
        print(f"  {bold}ACTIVE ALERTS:{rst}")
        for a in state.active_alerts[:8]:
            print(f"    • {a[:62]}")

    print(f"{bold}{cyan}{'═' * W}{rst}\n")


# ─────────────────────────────────────────────────────────────────────────────
# MODULE SINGLETON
# ─────────────────────────────────────────────────────────────────────────────

_monitor_instance: Optional[ATNMonitor] = None
_monitor_lock = threading.Lock()


def get_atn_monitor() -> ATNMonitor:
    """Return the module-level ATNMonitor singleton."""
    global _monitor_instance
    if _monitor_instance is None:
        with _monitor_lock:
            if _monitor_instance is None:
                _monitor_instance = ATNMonitor()
    return _monitor_instance


def atn_state() -> EarthHazardState:
    """One-liner — get current Earth hazard state."""
    return get_atn_monitor().get_state()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.WARNING)

    print("\n  🌍 ATN Monitor — fetching all 7 Earth hazard streams…\n")
    monitor = ATNMonitor()

    watch = "--watch" in sys.argv
    interval = 60

    while True:
        try:
            monitor.print_dashboard()
        except KeyboardInterrupt:
            print("\n  Stopped.")
            break
        except Exception as e:
            print(f"  Error: {e}")

        if not watch:
            break

        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n  Stopped.")
            break
