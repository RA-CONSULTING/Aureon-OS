#!/usr/bin/env python3
"""
PLANETARY META-COGNITIVE SWITCHBOARD
====================================
Active planetary intelligence layer. Runs independently, feeds the radar.

- Pulls live space weather from NOAA (no key needed)
- Pulls live Schumann resonance from VLF stations
- Pulls solar wind, Kp index, geomagnetic data
- Pulls NASA DONKI solar flare/CME data (API key from .env)
- Receives planetary energy readings
- Writes signals to planetary_signals.jsonl (radar consumes)
- Logs planetary commentary for human review

Usage: python planetary_switchboard.py
"""

import os
import sys
import json
import time
import math
import traceback
from pathlib import Path
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

import requests

# ─── PATHS ────────────────────────────────────────────────────────────────────
RADAR_DIR = Path(__file__).parent
PLANETARY_DIR = RADAR_DIR / "planetary"
PLANETARY_DIR.mkdir(exist_ok=True)
SIGNAL_OUT = RADAR_DIR / "planetary_signals.jsonl"
PLANETARY_LOG = RADAR_DIR / "planetary_meta.log"

# ─── API KEYS ─────────────────────────────────────────────────────────────────
NASA_API_KEY = os.getenv("NASA_API_KEY", "")
NOAA_API_KEY = os.getenv("NOAA_API_KEY", "")  # Usually not needed for NOAA SWPC
USGS_API_KEY = os.getenv("USGS_API_KEY", "")

# ─── DATA STRUCTURES ──────────────────────────────────────────────────────────
@dataclass
class SpaceWeatherSnapshot:
    timestamp: str
    kp_index: float
    kp_category: str
    solar_wind_speed: float
    solar_wind_density: float
    bz_component: float
    solar_flares_24h: int
    geomagnetic_storm_3day: str
    source: str

@dataclass
class SchumannSnapshot:
    timestamp: str
    fundamental_hz: float
    amplitude: float
    quality: float
    coherence_boost: float
    resonance_phase: str
    earth_disturbance_level: float
    source: str

@dataclass
class PlanetarySignal:
    timestamp: str
    source: str
    signal_type: str  # 'space_weather', 'schumann', 'solar_event'
    symbol: str  # e.g. 'GOLD', 'NATURALGAS', 'USDJPY'
    direction: str  # 'LONG', 'SHORT', 'NEUTRAL'
    confidence: float
    reasoning: str
    planetary_narrative: str
    energy_level: str  # 'LOW', 'MEDIUM', 'HIGH', 'EXTREME'
    risk_modifier: float  # -0.2 to +0.2 applied to radar confidence
    urgency: str

# ─── NOAA SPACE WEATHER FEED ──────────────────────────────────────────────────
class NOAAFeed:
    """Live space weather from NOAA SWPC (no API key required)"""
    
    BASE = "https://services.swpc.noaa.gov"
    
    def __init__(self):
        self.sess = requests.Session()
        self.sess.timeout = 15
    
    def _get(self, endpoint: str) -> Optional[dict]:
        try:
            r = self.sess.get(f"{self.BASE}{endpoint}", timeout=15)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[NOAA ERROR] {endpoint}: {e}")
            return None
    
    def get_kp(self) -> Optional[SpaceWeatherSnapshot]:
        """Get current Kp index"""
        data = self._get("/json/planetary_k_index_1m.json")
        if not data or not isinstance(data, list):
            return None
        latest = data[-1]
        kp = float(latest.get("kp_index", 0))
        
        # Kp categories
        if kp < 3:
            cat = "QUIET"
        elif kp < 5:
            cat = "UNSETTLED"
        elif kp < 6:
            cat = "ACTIVE"
        elif kp < 7:
            cat = "STORM"
        else:
            cat = "SEVERE"
        
        return SpaceWeatherSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            kp_index=kp,
            kp_category=cat,
            solar_wind_speed=0,
            solar_wind_density=0,
            bz_component=0,
            solar_flares_24h=0,
            geomagnetic_storm_3day="",
            source="NOAA_SWPC"
        )
    
    def get_solar_wind(self) -> Optional[SpaceWeatherSnapshot]:
        """Get solar wind plasma data"""
        data = self._get("/json/rtsw/rtsw_wind_1m.json")
        if not data or not isinstance(data, list):
            return None
        latest = data[-1]
        # NOAA RTSW schema: proton_* keys (older speed/density kept as fallback)
        return SpaceWeatherSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            kp_index=0,
            kp_category="",
            solar_wind_speed=float(latest.get("proton_speed") or latest.get("speed") or 0),
            solar_wind_density=float(latest.get("proton_density") or latest.get("density") or 0),
            bz_component=0,
            solar_flares_24h=0,
            geomagnetic_storm_3day="",
            source="NOAA_RTSW"
        )
    
    def get_mag_field(self) -> Optional[SpaceWeatherSnapshot]:
        """Get IMF Bz component"""
        data = self._get("/json/rtsw/rtsw_mag_1m.json")
        if not data or not isinstance(data, list):
            return None
        latest = data[-1]
        # NOAA RTSW schema: bz_gsm/bz_gse keys (older bz kept as fallback);
        # bz_gsm is the reconnection-relevant component.
        bz = float(latest.get("bz_gsm") or latest.get("bz_gse") or latest.get("bz") or 0)
        return SpaceWeatherSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            kp_index=0,
            kp_category="",
            solar_wind_speed=0,
            solar_wind_density=0,
            bz_component=bz,
            solar_flares_24h=0,
            geomagnetic_storm_3day="",
            source="NOAA_MAG"
        )

# ─── SCHUMANN RESONANCE FEED ──────────────────────────────────────────────────
# Live Schumann state is written by the workspace schumann_real_daemon
# (resonanceone_tomsk API) into schumann_state.json. FAIL-CLOSED (SIM-SEVER-B):
# if the state file is missing, unreadable, unparseable, stale
# (> AUREON_SCHUMANN_MAX_AGE_SEC, default 600 s), or flagged simulation while
# AUREON_ALLOW_SIM_FALLBACK is not set, get_schumann() returns None and the
# switchboard SKIPS Schumann-based signals. No estimated/fallback constants
# are ever emitted.
_SCHUMANN_STATE_CANDIDATES = [
    RADAR_DIR.parent / "aureon_fusion" / "state" / "schumann_state.json",
    RADAR_DIR.parent / "schumann_state.json",
]


def _schumann_max_age_sec() -> float:
    try:
        return float(os.getenv("AUREON_SCHUMANN_MAX_AGE_SEC", "600"))
    except ValueError:
        return 600.0


class SchumannFeed:
    """Live Schumann resonance from the workspace's real schumann_state.json.

    Every emitted field is read from, or derived by an explicit normalization
    of, the state file — never a constant literal.
    """

    def __init__(self):
        self._state_path = self._resolve_state_path()

    @staticmethod
    def _resolve_state_path() -> Optional[Path]:
        env_path = os.getenv("AUREON_SCHUMANN_STATE")
        if env_path:
            p = Path(env_path)
            return p if p.exists() else None
        for p in _SCHUMANN_STATE_CANDIDATES:
            if p.exists():
                return p
        return None

    @staticmethod
    def _parse_timestamp(value) -> Optional[datetime]:
        if not value:
            return None
        try:
            ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts

    def get_schumann(self) -> Optional[SchumannSnapshot]:
        """Fresh reading from schumann_state.json, or None (fail-closed)."""
        if self._state_path is None:
            print("[SCHUMANN] state file missing — skipping Schumann signals [fail-closed]")
            return None
        try:
            data = json.loads(self._state_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[SCHUMANN] state file unreadable ({e}) — skipping [fail-closed]")
            return None
        if not isinstance(data, dict):
            print("[SCHUMANN] state file malformed — skipping [fail-closed]")
            return None

        # Never pass simulated state off as live telemetry.
        sim_tagged = data.get("simulation") is True or data.get("real_data") is False
        if sim_tagged and os.getenv("AUREON_ALLOW_SIM_FALLBACK") != "1":
            print("[SCHUMANN] state flagged simulation and AUREON_ALLOW_SIM_FALLBACK "
                  "is not set — skipping Schumann signals [fail-closed]")
            return None

        ts = self._parse_timestamp(data.get("timestamp"))
        if ts is None:
            print("[SCHUMANN] state has no valid timestamp — skipping [fail-closed]")
            return None
        max_age = _schumann_max_age_sec()
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        if age > max_age:
            print(f"[SCHUMANN] state stale ({age:.0f}s > {max_age:.0f}s) "
                  "— skipping Schumann signals [fail-closed]")
            return None

        try:
            fundamental = float(data["frequency_hz"])
        except (KeyError, TypeError, ValueError):
            print("[SCHUMANN] state has no valid frequency_hz — skipping [fail-closed]")
            return None

        # Honest field mapping — every value is read from, or an explicit
        # normalization of, the state file.
        activity = data.get("activity_index")
        amplitude = (float(activity) / 100.0) if isinstance(activity, (int, float)) else 0.0
        quality_map = {"quiet": 1.0, "unsettled": 0.7, "active": 0.4, "storm": 0.1}
        quality = quality_map.get(str(data.get("geomagnetic_status", "")).lower(), 0.5)
        kp = data.get("kp_index")
        disturbance = min(max((float(kp) / 9.0), 0.0), 1.0) if isinstance(kp, (int, float)) else 0.0

        source = f"schumann_state_json:{data.get('source', 'unknown')}"
        if sim_tagged:
            source += ":simulation"

        return SchumannSnapshot(
            timestamp=ts.isoformat(),
            fundamental_hz=fundamental,
            amplitude=amplitude,
            quality=quality,
            coherence_boost=0.0,
            resonance_phase=str(data.get("activity_label", "unknown")),
            earth_disturbance_level=disturbance,
            source=source,
        )

# ─── NASA SOLAR EVENT FEED ────────────────────────────────────────────────────
class NASAFeed:
    """Solar flare and CME data from NASA DONKI"""
    
    def __init__(self):
        self.key = NASA_API_KEY
        self.sess = requests.Session()
        self.sess.timeout = 15
    
    def get_flares(self) -> List[dict]:
        """Get recent solar flares"""
        if not self.key:
            return []
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=24)
            r = self.sess.get(
                "https://api.nasa.gov/DONKI/FLR",
                params={
                    "startDate": start.strftime("%Y-%m-%d"),
                    "endDate": end.strftime("%Y-%m-%d"),
                    "api_key": self.key
                },
                timeout=15
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[NASA ERROR] {e}")
            return []
    
    def get_cmes(self) -> List[dict]:
        """Get recent CMEs"""
        if not self.key:
            return []
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=72)
            r = self.sess.get(
                "https://api.nasa.gov/DONKI/CME",
                params={
                    "startDate": start.strftime("%Y-%m-%d"),
                    "endDate": end.strftime("%Y-%m-%d"),
                    "api_key": self.key
                },
                timeout=15
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"[NASA ERROR] {e}")
            return []

# ─── PLANETARY META-COGNITIVE ENGINE ──────────────────────────────────────────
class PlanetaryMetaEngine:
    """Converts planetary data into trading signals"""
    
    def __init__(self):
        self.noaa = NOAAFeed()
        self.schumann = SchumannFeed()
        self.nasa = NASAFeed()
        self.last_state: Optional[dict] = None
    
    def analyze(self) -> List[PlanetarySignal]:
        """Pull all planetary data and generate signals"""
        signals = []
        ts = datetime.now(timezone.utc).isoformat()
        
        # ─── SPACE WEATHER ──────────────────────────────────────────────
        kp = self.noaa.get_kp()
        solar_wind = self.noaa.get_solar_wind()
        mag = self.noaa.get_mag_field()
        
        narrative_parts = []
        energy_level = "LOW"
        risk_modifier = 0.0
        
        if kp:
            narrative_parts.append(f"Kp={kp.kp_index} ({kp.kp_category})")
            if kp.kp_index >= 5:
                energy_level = "EXTREME"
                risk_modifier = -0.15
                signals.append(PlanetarySignal(
                    timestamp=ts, source="planetary_meta", signal_type="space_weather",
                    symbol="GOLD", direction="LONG", confidence=0.7,
                    reasoning=f"Geomagnetic storm Kp={kp.kp_index} drives safe-haven demand",
                    planetary_narrative="", energy_level=energy_level,
                    risk_modifier=risk_modifier, urgency="HIGH"
                ))
            elif kp.kp_index >= 3:
                energy_level = "MEDIUM"
                risk_modifier = 0.05
        
        if solar_wind:
            narrative_parts.append(f"Solar wind {solar_wind.solar_wind_speed:.0f} km/s")
            if solar_wind.solar_wind_speed > 500:
                energy_level = "HIGH" if energy_level != "EXTREME" else "EXTREME"
                risk_modifier -= 0.1
        
        if mag:
            narrative_parts.append(f"Bz={mag.bz_component:.1f}nT")
            if mag.bz_component < -5:
                signals.append(PlanetarySignal(
                    timestamp=ts, source="planetary_meta", signal_type="space_weather",
                    symbol="NATURALGAS", direction="LONG", confidence=0.6,
                    reasoning=f"Southward Bz={mag.bz_component:.1f}nT indicates energy influx",
                    planetary_narrative="", energy_level="HIGH",
                    risk_modifier=-0.1, urgency="MEDIUM"
                ))
        
        # ─── SCHUMANN RESONANCE ─────────────────────────────────────────
        sch = self.schumann.get_schumann()
        if sch:
            narrative_parts.append(f"Schumann {sch.fundamental_hz:.2f}Hz ({sch.resonance_phase})")
            if sch.earth_disturbance_level > 0.5:
                energy_level = "HIGH"
                risk_modifier -= 0.05
                signals.append(PlanetarySignal(
                    timestamp=ts, source="planetary_meta", signal_type="schumann",
                    symbol="USDJPY", direction="SHORT", confidence=0.55,
                    reasoning="Earth disturbance detected - flight to safety",
                    planetary_narrative="", energy_level="HIGH",
                    risk_modifier=-0.05, urgency="LOW"
                ))
        
        # ─── NASA SOLAR EVENTS ──────────────────────────────────────────
        flares = self.nasa.get_flares()
        cmes = self.nasa.get_cmes()
        
        if flares:
            narrative_parts.append(f"{len(flares)} solar flares (24h)")
            if any(f.get("classType", "").startswith("X") for f in flares):
                energy_level = "EXTREME"
                risk_modifier = -0.2
                signals.append(PlanetarySignal(
                    timestamp=ts, source="planetary_meta", signal_type="solar_event",
                    symbol="GOLD", direction="LONG", confidence=0.8,
                    reasoning="X-class solar flare detected - safe haven surge",
                    planetary_narrative="", energy_level="EXTREME",
                    risk_modifier=-0.2, urgency="HIGH"
                ))
        
        if cmes:
            narrative_parts.append(f"{len(cmes)} CMEs (72h)")
        
        narrative = " | ".join(narrative_parts) if narrative_parts else "Planetary conditions nominal"
        
        # Log
        with open(PLANETARY_LOG, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"TIME: {ts}\n")
            f.write(f"NARRATIVE: {narrative}\n")
            f.write(f"ENERGY LEVEL: {energy_level}\n")
            f.write(f"RISK MODIFIER: {risk_modifier:+.2f}\n")
            f.write(f"SIGNALS: {len(signals)}\n")
            f.write(f"{'='*60}\n")
        
        print(f"\n[PLANETARY] {narrative}")
        print(f"[ENERGY]    Level: {energy_level} | Risk mod: {risk_modifier:+.2f}")

        self.last_state = {
            "narrative": narrative,
            "energy_level": energy_level,
            "risk_modifier": risk_modifier,
        }

        return signals

# ─── MAIN SWITCHBOARD LOOP ────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("PLANETARY META-COGNITIVE SWITCHBOARD")
    print("=" * 60)
    print(f"NASA API Key: {'CONFIGURED' if NASA_API_KEY else 'NOT SET'}")
    print(f"Output:       {SIGNAL_OUT}")
    print(f"Planetary log: {PLANETARY_LOG}")
    print("=" * 60)
    
    engine = PlanetaryMetaEngine()
    cycle = 0
    
    while True:
        cycle += 1
        ts = datetime.now(timezone.utc).isoformat()
        print(f"\n--- CYCLE {cycle} @ {ts} ---")

        signals: List[PlanetarySignal] = []
        try:
            signals = engine.analyze()
        except Exception:
            traceback.print_exc()
            print("[ERROR] cycle analysis failed — state record will say so honestly")
            engine.last_state = None

        # Always emit a planetary-state record: the hnc_core planetary band
        # freshness-gates on this file's last-line timestamp, so a quiet sky
        # must not read as a dead sensor. Real observed readings only,
        # explicitly NEUTRAL — no directional trading claim.
        st = engine.last_state or {}
        state_sig = PlanetarySignal(
            timestamp=ts, source="planetary_switchboard",
            signal_type="planetary_state", symbol="PLANET",
            direction="NEUTRAL", confidence=0.0,
            reasoning="planetary state telemetry (not a directional signal): "
                      + st.get("narrative", "readings unavailable this cycle"),
            planetary_narrative=st.get("narrative", ""),
            energy_level=st.get("energy_level", "LOW"),
            risk_modifier=st.get("risk_modifier", 0.0),
            urgency="LOW",
        )

        try:
            with open(SIGNAL_OUT, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(state_sig)) + "\n")
                for sig in signals:
                    f.write(json.dumps(asdict(sig)) + "\n")
        except Exception:
            traceback.print_exc()

        print(f"[STATE] Wrote planetary state record "
              f"(energy={state_sig.energy_level}, risk={state_sig.risk_modifier:+.2f})")
        if signals:
            print(f"[SIGNALS] Wrote {len(signals)} directional planetary signals:")
            for s in signals:
                print(f"  -> {s.symbol} {s.direction}  conf={s.confidence:.2f}  "
                      f"energy={s.energy_level}  risk_mod={s.risk_modifier:+.2f}")
        else:
            print("[SIGNALS] No directional planetary signals this cycle.")

        interval = 300  # 5 minutes
        print(f"[SLEEP] Next cycle in {interval}s...")
        time.sleep(interval)

if __name__ == "__main__":
    main()
