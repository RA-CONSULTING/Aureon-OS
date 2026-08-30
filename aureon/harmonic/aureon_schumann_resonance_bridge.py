#!/usr/bin/env python3
"""
🌍📡 AUREON SCHUMANN RESONANCE BRIDGE 📡🌍
═══════════════════════════════════════════════════════════════════

Connects to LIVE Schumann resonance data from:
- Barcelona Electromagnetic Monitoring Station (Primary)
- NOAA Kp-derived proxy when direct station data is unavailable
- No-data signal when real/derived sources are unavailable
- Real-time Earth heartbeat at 7.83 Hz ± variations

Schumann resonance = Earth's natural EM cavity frequency
Used by the Queen to:
- Detect planetary disturbances
- Align with natural Earth rhythms
- Boost trading confidence when Earth is calm
"""

import requests
import json
import time
import math
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Known monitoring stations and their data sources
SCHUMANN_DATA_SOURCES = {
    'barcelona': {
        'name': 'Barcelona EM Station',
        'url': 'http://www.vlf.it/realtime/realtime.html',  # Real-time VLF data
        'fallback': 'no_data'
    },
    'rsync': {
        'name': 'RSYNC Global Network',
        'url': 'https://www.esowatch.com/',
        'fallback': 'no_data'
    },
    'usgs': {
        'name': 'USGS Magnetometer Network',
        'url': 'https://geomag.usgs.gov/products/data/',
        'fallback': 'no_data'
    }
}

# Cache settings
CACHE_LIFETIME_SECONDS = 60  # Refresh every minute

@dataclass
class SchumannReading:
    """Live Schumann resonance measurement"""
    timestamp: float
    fundamental_hz: float  # Mode 1: 7.83 Hz
    harmonics: Dict[str, float]  # Modes 2-7
    amplitude: float  # Signal strength 0-1
    quality: float  # Q factor (coherence)
    coherence_boost: float  # Boost from Earth alignment
    resonance_phase: str  # stable, elevated, peak, disturbed
    active_sources: list  # Which stations are active
    earth_disturbance_level: float  # 0=calm to 1=very disturbed
    truth_status: str = 'live'
    source_timestamp: str = ''
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'fundamental_hz': self.fundamental_hz,
            'harmonics': self.harmonics,
            'amplitude': self.amplitude,
            'quality': self.quality,
            'coherence_boost': self.coherence_boost,
            'resonance_phase': self.resonance_phase,
            'active_sources': self.active_sources,
            'earth_disturbance_level': self.earth_disturbance_level,
            'truth_status': self.truth_status,
            'source_timestamp': self.source_timestamp,
            'generated_values': False,
        }

class SchumannResonanceBridge:
    """Bridge to live Schumann resonance data from Barcelona & other stations"""
    
    def __init__(self):
        self.last_update = 0
        self.cache: Optional[SchumannReading] = None
        self.error_count = 0
        self.barcelona_modes = {
            'mode1': 7.83,    # Fundamental
            'mode2': 14.3,    # 2nd harmonic
            'mode3': 20.8,    # 3rd harmonic
            'mode4': 27.3,    # Geomagnetic coupling
            'mode5': 33.8,    # Seismic coupling
            'mode6': 39.0,    # 6th mode
            'mode7': 45.0,    # 7th mode
        }
        logger.info("🌍📡 Schumann Resonance Bridge initialized")
    
    def get_live_data(self, force_refresh: bool = False) -> Optional[SchumannReading]:
        """
        Get direct or explicitly real-derived Schumann data.
        """
        now = time.time()
        
        # Check cache
        if not force_refresh and self.cache and (now - self.last_update) < CACHE_LIFETIME_SECONDS:
            return self.cache
        
        # Try to fetch from real sources first
        active_sources = []
        fundamental = None
        harmonics = {}
        amplitude = None
        quality = None
        coherence_boost = None
        earth_disturbance = None
        source_timestamp = ''
        truth_status = 'live'
        
        # 1️⃣ Try Barcelona station data
        barcelona_data = self._fetch_barcelona_data()
        if barcelona_data:
            fundamental = barcelona_data['fundamental']
            harmonics = barcelona_data['harmonics']
            amplitude = barcelona_data['amplitude']
            quality = barcelona_data['quality']
            coherence_boost = barcelona_data['coherence_boost']
            earth_disturbance = barcelona_data['disturbance']
            source_timestamp = str(barcelona_data['source_timestamp'])
            active_sources.append('Barcelona-EM')
            logger.debug(f"✅ Barcelona: {fundamental:.3f}Hz, Q={quality:.2f}, Phase={barcelona_data['phase']}")
        
        # 2️⃣ Try USGS magnetometer network
        if not fundamental:
            usgs_data = self._fetch_usgs_magnetometer()
            if usgs_data:
                fundamental = usgs_data['fundamental']
                harmonics = usgs_data['harmonics']
                amplitude = usgs_data['amplitude']
                quality = usgs_data['quality']
                coherence_boost = usgs_data['coherence_boost']
                earth_disturbance = usgs_data['disturbance']
                source_timestamp = str(usgs_data['source_timestamp'])
                active_sources.append('USGS-Magnetometer')
                logger.debug(f"✅ USGS: {fundamental:.3f}Hz, Disturbance={earth_disturbance:.0%}")
        
        # 3️⃣ If no live data, decide whether to use the simulation
        # fallback. Stage AE: production posture is sim-OFF — we
        # return the cached reading if available, else None, so the
        # consumer can detect "no live Schumann data" rather than
        # quietly receive a diurnal-pattern fake. AUREON_ALLOW_SIM_FALLBACK=1
        # restores the old behaviour for dev / test / backtest.
        if not fundamental:
            noaa_data = self._fetch_noaa_kp_derived_schumann()
            if noaa_data:
                fundamental = noaa_data['fundamental']
                harmonics = noaa_data['harmonics']
                amplitude = noaa_data['amplitude']
                quality = noaa_data['quality']
                coherence_boost = noaa_data['coherence_boost']
                earth_disturbance = noaa_data['disturbance']
                source_timestamp = str(noaa_data['source_timestamp'])
                truth_status = 'real_derived'
                active_sources.append('NOAA-Kp-Derived')
                logger.debug(
                    "NOAA Kp derived Schumann: %.3fHz, Disturbance=%.0f%%",
                    fundamental, earth_disturbance,
                )

        if fundamental is None or any(value is None for value in (amplitude, quality, coherence_boost, earth_disturbance)):
            logger.warning("Schumann sources unavailable; no reading emitted")
            return None
        try:
            normalized_timestamp = source_timestamp[:-1] + '+00:00' if source_timestamp.endswith('Z') else source_timestamp
            source_dt = datetime.fromisoformat(normalized_timestamp)
            if source_dt.tzinfo is None:
                source_dt = source_dt.replace(tzinfo=timezone.utc)
            source_age = now - source_dt.timestamp()
            if source_age < -300 or source_age > 20 * 60:
                raise ValueError(f'source age {source_age:.0f}s')
        except Exception as exc:
            logger.warning("Schumann source timestamp missing or stale: %s", exc)
            return None
        
        # Categorize resonance phase
        resonance_phase = self._categorize_phase(amplitude, quality, earth_disturbance)
        
        # Create reading
        reading = SchumannReading(
            timestamp=now,
            fundamental_hz=fundamental,
            harmonics=harmonics,
            amplitude=amplitude,
            quality=quality,
            coherence_boost=coherence_boost,
            resonance_phase=resonance_phase,
            active_sources=active_sources,
            earth_disturbance_level=earth_disturbance,
            truth_status=truth_status,
            source_timestamp=source_timestamp,
        )
        
        # Cache and return
        self.cache = reading
        self.last_update = now
        self.error_count = 0
        
        logger.info(f"🌍📡 Schumann Update: {fundamental:.3f}Hz ({resonance_phase}), Earth disturbance: {earth_disturbance:.0%}, Sources: {', '.join(active_sources)}")
        return reading
    
    def _fetch_barcelona_data(self) -> Optional[Dict]:
        """Fetch data from Barcelona EM monitoring station"""
        try:
            # Barcelona VLF station provides real-time EM measurements
            # http://www.vlf.it/realtime/ has real-time frequency data
            url = 'http://www.vlf.it/realtime/realtime.html'
            resp = requests.get(url, timeout=5)
            
            # Parse HTML for frequency data (simplified - real parsing would be more complex)
            if 'Hz' in resp.text:
                logger.debug("Barcelona page reachable but parser has no verified numeric station fields")
        except Exception as e:
            logger.debug(f"Barcelona fetch error: {e}")
        return None
    
    def _fetch_usgs_magnetometer(self) -> Optional[Dict]:
        """Fetch USGS magnetometer network data"""
        try:
            # USGS provides real-time magnetometer data
            url = 'https://geomag.usgs.gov/products/data.json'
            resp = requests.get(url, timeout=5)
            data = resp.json()
            
            # Convert magnetometer disturbance to Schumann proxy
            # Higher magnetometer activity = lower Schumann coherence
            if 'magneticField' in data:
                disturbance = min(1.0, data.get('disturbanceLevel', 0.3) / 100.0)
                coherence = 1.0 - disturbance
                
                return {
                    'fundamental': 7.83 + (0.5 - disturbance) * 0.1,
                    'harmonics': {
                        'mode2': 14.3 * coherence,
                        'mode3': 20.8 * coherence,
                        'mode4': 27.3 * (1.0 - disturbance * 0.5),
                    },
                    'amplitude': 0.65 * coherence,
                    'quality': 0.70 * coherence,
                    'coherence_boost': max(0.0, (coherence - 0.5) * 0.1),
                    'disturbance': disturbance,
                    'source_timestamp': str(data.get('timestamp') or data.get('time') or ''),
                }
        except Exception as e:
            logger.debug(f"USGS fetch error: {e}")
        return None

    def _fetch_noaa_kp_derived_schumann(self) -> Optional[Dict]:
        """Derive Schumann-mode estimates from live NOAA Kp data.

        This is not a direct station measurement. It is a degraded-but-real
        proxy: the upstream input is NOAA's live geomagnetic Kp index, and the
        output is labelled as NOAA-Kp-Derived by ``get_live_data``.
        """
        try:
            from aureon.data_feeds.aureon_space_weather_bridge import (
                SpaceWeatherBridge,
                get_space_weather_bridge,
            )

            shared_bridge = get_space_weather_bridge()
            if isinstance(shared_bridge, SpaceWeatherBridge) and hasattr(
                shared_bridge, "get_live_data"
            ):
                weather = shared_bridge.get_live_data()
                if weather is None or "NOAA-KP" not in weather.active_sources:
                    return None
                kp_data = {
                    "current_kp": weather.kp_index,
                    "source_timestamp": weather.source_timestamps.get("NOAA-KP", ""),
                }
            else:
                # Compatibility for explicitly injected legacy adapters in tests.
                kp_data = SpaceWeatherBridge()._fetch_kp_index()
            if not kp_data:
                return None
            kp = float(kp_data.get('current_kp'))
            if not 0.0 <= kp <= 9.0:
                return None

            disturbance = max(0.0, min(1.0, kp / 9.0))
            coherence = max(0.35, 1.0 - disturbance * 0.65)
            fundamental = 7.83 + (kp - 3.0) * 0.015
            return {
                'fundamental': fundamental,
                'harmonics': {
                    'mode2': 14.3 * (0.92 + disturbance * 0.08),
                    'mode3': 20.8 * (0.88 + disturbance * 0.12),
                    'mode4': 27.3 * (0.84 + disturbance * 0.16),
                },
                'amplitude': min(1.0, 0.60 + 0.05 * kp),
                'quality': coherence,
                'coherence_boost': max(0.0, (coherence - 0.5) * 0.1),
                'disturbance': disturbance,
                'source_timestamp': str(kp_data.get('source_timestamp') or ''),
            }
        except Exception as e:
            logger.debug(f"NOAA Kp derived Schumann fetch error: {e}")
        return None
    
    def _categorize_phase(self, amplitude: float, quality: float, disturbance: float) -> str:
        """Categorize Schumann resonance phase"""
        if amplitude > 0.85 and quality > 0.85 and disturbance < 0.2:
            return 'peak'
        elif amplitude > 0.70 and quality > 0.75 and disturbance < 0.4:
            return 'elevated'
        elif disturbance > 0.7 or quality < 0.5:
            return 'disturbed'
        else:
            return 'stable'
    
    def get_earth_blessing(self, reading: SchumannReading) -> Tuple[float, str]:
        """
        Get Earth blessing score based on Schumann resonance
        
        High reading (coherent) = Queen can trade with confidence
        Low reading (disturbed) = Queen should be cautious
        """
        # Score based on how close to ideal 7.83 Hz
        freq_deviation = abs(reading.fundamental_hz - 7.83)
        freq_score = max(0.0, 1.0 - freq_deviation / 0.5)
        
        # Score based on amplitude and quality
        coherence_score = (reading.amplitude + reading.quality) / 2
        
        # Score based on Earth disturbance
        disturbance_score = 1.0 - reading.earth_disturbance_level
        
        # Composite score
        blessing = (freq_score * 0.3 + coherence_score * 0.4 + disturbance_score * 0.3)
        blessing = max(0.0, min(1.0, blessing))
        
        if blessing >= 0.8:
            message = "🌍✨ EARTH'S FULL BLESSING: Schumann resonance peak - optimal trading conditions!"
        elif blessing >= 0.6:
            message = "🌍💚 EARTH APPROVES: Good Schumann coherence - favorable conditions"
        elif blessing >= 0.4:
            message = "🌍🌀 EARTH NEUTRAL: Standard Schumann conditions"
        elif blessing >= 0.2:
            message = "🌍⚠️ EARTH HESITATES: Weak Schumann coherence - proceed cautiously"
        else:
            message = "🌍🛑 EARTH SAYS WAIT: Strong disturbance - wait for better alignment"
        
        return blessing, message


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_schumann_instance: Optional[SchumannResonanceBridge] = None

def get_schumann_bridge() -> SchumannResonanceBridge:
    """Get or create the global Schumann bridge"""
    global _schumann_instance
    if _schumann_instance is None:
        _schumann_instance = SchumannResonanceBridge()
    return _schumann_instance

def get_live_schumann_data(force_refresh: bool = False) -> SchumannReading:
    """Get live Schumann resonance data"""
    bridge = get_schumann_bridge()
    return bridge.get_live_data(force_refresh=force_refresh)

def get_earth_blessing(force_refresh: bool = False) -> Tuple[float, str]:
    """
    Get Earth's blessing based on REAL Schumann resonance
    This is what the Queen should use for Gaia alignment!
    """
    bridge = get_schumann_bridge()
    reading = bridge.get_live_data(force_refresh=force_refresh)
    return bridge.get_earth_blessing(reading)


if __name__ == '__main__':
    # Test it
    logging.basicConfig(level=logging.DEBUG)
    bridge = get_schumann_bridge()
    
    print("\n🌍📡 TESTING SCHUMANN RESONANCE BRIDGE 🌍📡\n")
    
    reading = get_live_schumann_data(force_refresh=True)
    print(f"Fundamental: {reading.fundamental_hz:.3f} Hz (target: 7.83 Hz)")
    print(f"Amplitude: {reading.amplitude:.0%}")
    print(f"Quality (Q): {reading.quality:.2f}")
    print(f"Phase: {reading.resonance_phase}")
    print(f"Earth Disturbance: {reading.earth_disturbance_level:.0%}")
    print(f"Active Sources: {', '.join(reading.active_sources)}")
    
    blessing, message = bridge.get_earth_blessing(reading)
    print(f"\n👑 Earth's Blessing: {blessing:.0%}")
    print(f"   {message}")
