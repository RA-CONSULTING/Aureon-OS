#!/usr/bin/env python3
"""
🌌 SOLAR SYSTEM METRICS COLLECTOR
═══════════════════════════════════════════════════════════════════════

Collects heliospheric and solar system-wide metrics from multiple sources.

Data Sources:
  • Solar Activity: Sunspot number, F10.7 flux, solar cycle position
  • Solar Wind: DSCOVR/ACE at L1 (already in Schumann calibrator)
  • Geomagnetic: Kp, Dst, auroral indices (already in Schumann calibrator)
  • Solar Imagery: SDO/HMI continuum, magnetograms
  • Particle Flux: GOES proton/electron, cosmic rays
  • Radio: Solar radio bursts, Jupiter DAM
  • Planetary: Positions, conjunctions, alignments

Output: Unified solar system state for temporal command center.
"""

import json
import time
import math
import logging
import sys
import requests
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from aureon_fusion.paths import WORKSPACE
from aureon_fusion.api_communion import get_json as communion_get_json

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# ─── Source Config ─────────────────────────────────────────────────────
# TTLs are served from the shared api_communion disk cache — the
# real_time_data_feeder's 60 s cycle refreshes the same NOAA URLs, so these
# organs mostly hit cache instead of the network.
SOLAR_SOURCES = {
    'sunspot_cycle': {
        'url': 'https://services.swpc.noaa.gov/json/solar-cycle/observed-solar-cycle-indices.json',
        'timeout': 10,
        'ttl': 3600,
        'desc': 'Sunspot number and F10.7 flux (solar cycle)'
    },
    'solar_wind_l1': {
        'url': 'https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json',
        'timeout': 10,
        'ttl': 300,
        'desc': 'Solar wind at L1 (RTSW 1-min)'
    },
    'mag_field_l1': {
        'url': 'https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json',
        'timeout': 10,
        'ttl': 300,
        'desc': 'IMF at L1 (RTSW 1-min magnetometer)'
    },
    'proton_flux': {
        'url': 'https://services.swpc.noaa.gov/json/goes/primary/integral-protons-plot-6-hour.json',
        'timeout': 10,
        'ttl': 300,
        'desc': 'GOES proton flux (SEP)'
    },
    'electron_flux': {
        'url': 'https://services.swpc.noaa.gov/json/goes/primary/integral-electrons-6-hour.json',
        'timeout': 10,
        'ttl': 300,
        'desc': 'GOES electron flux'
    },
    'xray_flux': {
        'url': 'https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json',
        'timeout': 10,
        'ttl': 300,
        'desc': 'GOES X-ray flux (flares)'
    },
    'alerts': {
        'url': 'https://services.swpc.noaa.gov/products/alerts.json',
        'timeout': 10,
        'ttl': 300,
        'desc': 'NOAA space weather alerts'
    },
    'aurora_forecast': {
        'url': 'https://services.swpc.noaa.gov/json/ovation_aurora_latest.json',
        'timeout': 10,
        'ttl': 600,
        'desc': 'Aurora oval forecast'
    }
}

DATA_DIR = WORKSPACE / "solar_system_data"
STATE_FILE = DATA_DIR / "solar_system_state.json"
TIMESERIES_FILE = DATA_DIR / "solar_system_timeseries.jsonl"


class SolarSystemCollector:
    """Heliospheric and solar system metrics collector"""
    
    def __init__(self):
        self.data_dir = DATA_DIR
        self.data_dir.mkdir(exist_ok=True)
        self.collection_history = []
        
        logger.info("🌌 Solar System Metrics Collector initialized")
        logger.info(f"   Sources: {len(SOLAR_SOURCES)}")
    
    def _fetch(self, url: str, timeout: int, ttl: int = 300) -> Optional[dict]:
        try:
            return communion_get_json(url, ttl_s=ttl, timeout=timeout,
                                      headers={'Accept': 'application/json'})
        except Exception as e:
            logger.warning(f"   ⚠️ Fetch failed: {url[:60]}... | {e}")
            return None
    
    # ─── Parsers ────────────────────────────────────────────────────────
    
    def _parse_sunspot_cycle(self, data: dict) -> dict:
        """Parse solar cycle indices (sunspot number, F10.7)"""
        if not data or not isinstance(data, list) or len(data) < 1:
            return None
        
        latest = data[-1]
        if not isinstance(latest, dict):
            return None
        
        ssn = latest.get('ssn', 0)
        f107 = latest.get('f10.7', latest.get('f107', 0))
        smoothed_ssn = latest.get('smoothed_ssn', ssn)
        time_tag = latest.get('time_tag', 'unknown')
        
        # Solar cycle phase classification
        if f107 < 70:
            cycle_phase = 'solar_minimum'
        elif f107 < 120:
            cycle_phase = 'ascending' if smoothed_ssn > ssn else 'descending'
        elif f107 < 200:
            cycle_phase = 'solar_maximum' if smoothed_ssn > 100 else 'approaching_max'
        else:
            cycle_phase = 'solar_maximum'
        
        return {
            'source': 'sunspot_cycle',
            'time_tag': time_tag,
            'sunspot_number': ssn,
            'smoothed_ssn': smoothed_ssn,
            'f10.7_flux': f107,
            'cycle_phase': cycle_phase,
            'activity_level': self._classify_solar_activity(f107),
            'confidence': 0.90
        }
    
    def _classify_solar_activity(self, f107: float) -> str:
        if f107 < 70: return 'very_low'
        elif f107 < 100: return 'low'
        elif f107 < 150: return 'moderate'
        elif f107 < 200: return 'high'
        elif f107 < 250: return 'very_high'
        else: return 'extreme'
    
    def _parse_solar_wind(self, data: dict) -> dict:
        """Parse solar wind at L1 (RTSW 1-min dict rows)"""
        if not data or not isinstance(data, list) or len(data) < 1:
            return None

        latest = None
        for row in reversed(data):
            if isinstance(row, dict) and row.get("active", True) \
                    and row.get("proton_speed") is not None:
                latest = row
                break
        if latest is None:
            latest = data[-1]
        if not isinstance(latest, dict):
            return None

        density = latest.get('proton_density') or 0
        speed = latest.get('proton_speed') or 0
        temp = latest.get('proton_temperature') or 0
        
        # Classify solar wind regime
        if speed < 350:
            regime = 'slow_wind'
        elif speed < 500:
            regime = 'intermediate'
        elif speed < 600:
            regime = 'fast_wind'
        elif speed < 800:
            regime = 'high_speed_stream'
        else:
            regime = 'extreme'
        
        # Dynamic pressure (nPa) ≈ n * v² * 1.67e-6
        dynamic_pressure = density * (speed ** 2) * 1.67e-6
        
        return {
            'source': 'solar_wind_l1',
            'time_tag': latest.get('time_tag', 'unknown'),
            'density': density,
            'speed': speed,
            'temperature': temp,
            'dynamic_pressure': dynamic_pressure,
            'regime': regime,
            'confidence': 0.85
        }
    
    def _parse_mag_field(self, data: dict, solar_wind_speed: Optional[float] = None) -> dict:
        """Parse IMF at L1 (RTSW 1-min dict rows)"""
        if not data or not isinstance(data, list) or len(data) < 1:
            return None

        latest = None
        for row in reversed(data):
            if isinstance(row, dict) and row.get("active", True) \
                    and row.get("bt") is not None:
                latest = row
                break
        if latest is None:
            latest = data[-1]
        if not isinstance(latest, dict):
            return None

        bx = float(latest.get('bx_gsm') or 0)
        by = float(latest.get('by_gsm') or 0)
        bz = float(latest.get('bz_gsm') or 0)
        bt = float(latest.get('bt') or 0)
        
        # Clock angle
        if bt > 0:
            clock_angle = math.degrees(math.atan2(by, bz))
        else:
            clock_angle = None
        
        # Geomagnetic coupling (simplified): southward Bz couples most efficiently
        coupling = (max(0, -bz * solar_wind_speed * 1e-3)
                    if solar_wind_speed is not None else None)
        
        return {
            'source': 'mag_field_l1',
            'time_tag': latest.get('time_tag', 'unknown'),
            'bx': bx,
            'by': by,
            'bz': bz,
            'bt': bt,
            'clock_angle': clock_angle,
            'coupling_efficiency': coupling,
            'confidence': 0.80
        }
    
    def _parse_proton_flux(self, data: dict) -> dict:
        """Parse proton flux (SEP)"""
        if not data or not isinstance(data, list) or len(data) < 1:
            return None
        
        latest = data[-1]
        if not isinstance(latest, dict):
            return None
        
        flux = latest.get('flux')
        if not isinstance(flux, (int, float)) or isinstance(flux, bool) or not math.isfinite(flux) or flux < 0:
            return None
        energy = latest.get('energy', 'unknown')
        
        # SEP classification
        if flux < 10:
            sep_level = 'none'
        elif flux < 100:
            sep_level = 'minor'
        elif flux < 1000:
            sep_level = 'moderate'
        elif flux < 10000:
            sep_level = 'strong'
        else:
            sep_level = 'extreme'
        
        return {
            'source': 'proton_flux',
            'time_tag': latest.get('time_tag', 'unknown'),
            'flux': flux,
            'energy': energy,
            'sep_level': sep_level,
            'confidence': 0.70
        }
    
    def _parse_electron_flux(self, data: dict) -> dict:
        """Parse electron flux"""
        if not data or not isinstance(data, list) or len(data) < 1:
            return None
        
        latest = data[-1]
        if not isinstance(latest, dict):
            return None
        
        flux = latest.get('flux')
        if not isinstance(flux, (int, float)) or isinstance(flux, bool) or not math.isfinite(flux) or flux < 0:
            return None
        energy = latest.get('energy', 'unknown')
        
        return {
            'source': 'electron_flux',
            'time_tag': latest.get('time_tag', 'unknown'),
            'flux': flux,
            'energy': energy,
            'confidence': 0.70
        }
    
    def _parse_xray(self, data: dict) -> dict:
        """Parse X-ray flux (flare classification)"""
        if not data or not isinstance(data, list) or len(data) < 1:
            return None
        
        latest = data[-1]
        if not isinstance(latest, dict):
            return None
        
        flux = latest.get('flux')
        if not isinstance(flux, (int, float)) or isinstance(flux, bool) or not math.isfinite(flux) or flux < 0:
            return None
        time_tag = latest.get('time_tag', 'unknown')
        
        # Flare classification
        if flux < 1e-7:
            flare_class = 'A'
        elif flux < 1e-6:
            flare_class = 'B'
        elif flux < 1e-5:
            flare_class = 'C'
        elif flux < 1e-4:
            flare_class = 'M'
        else:
            flare_class = 'X'
        
        return {
            'source': 'xray_flux',
            'time_tag': time_tag,
            'flux': flux,
            'flare_class': flare_class,
            'confidence': 0.80
        }
    
    def _parse_alerts(self, data: dict) -> dict:
        """Parse NOAA alerts"""
        if not data or not isinstance(data, list):
            return None
        
        # Count active alerts by type
        g_alerts = [a for a in data if 'G' in a.get('product_id', '')]
        r_alerts = [a for a in data if 'R' in a.get('product_id', '')]
        s_alerts = [a for a in data if 'S' in a.get('product_id', '')]
        
        # Extract highest severity
        max_g = max([a.get('scale', 0) for a in g_alerts] or [0])
        max_r = max([a.get('scale', 0) for a in r_alerts] or [0])
        max_s = max([a.get('scale', 0) for a in s_alerts] or [0])
        
        return {
            'source': 'alerts',
            'time_tag': datetime.now(timezone.utc).isoformat(),
            'total_alerts': len(data),
            'geomagnetic_alerts': len(g_alerts),
            'radio_blackout_alerts': len(r_alerts),
            'radiation_storm_alerts': len(s_alerts),
            'max_geomagnetic_scale': max_g,
            'max_radio_scale': max_r,
            'max_radiation_scale': max_s,
            'confidence': 0.95
        }
    
    def _parse_aurora(self, data: dict) -> dict:
        """Parse aurora forecast"""
        if not data or not isinstance(data, dict):
            return None
        
        forecast_time = data.get('Forecast Time', 'unknown')
        observation_time = data.get('Observation Time', 'unknown')
        
        # Get coordinates if available
        coordinates = data.get('coordinates', [])
        
        # Calculate approximate auroral power (simplified)
        # Higher latitudes = stronger aurora
        auroral_power = len(coordinates) * 0.01 if coordinates else 0
        
        return {
            'source': 'aurora_forecast',
            'forecast_time': forecast_time,
            'observation_time': observation_time,
            'auroral_power': auroral_power,
            'coordinate_count': len(coordinates),
            'confidence': 0.60
        }
    
    # ─── Collection Engine ──────────────────────────────────────────────
    
    def collect(self) -> Optional[dict]:
        """Collect all solar system metrics"""
        logger.info("🌌 Starting solar system data collection...")
        
        # First pass: fetch all data
        raw_data = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {}
            for name, config in SOLAR_SOURCES.items():
                future = executor.submit(self._fetch, config['url'],
                                         config['timeout'], config.get('ttl', 300))
                futures[future] = name
            
            for future in as_completed(futures):
                name = futures[future]
                try:
                    data = future.result()
                    if data is not None:
                        raw_data[name] = data
                    else:
                        logger.warning(f"   ⚠️ {name}: fetch failed")
                except Exception as e:
                    logger.error(f"   ❌ {name}: {e}")
        
        # Second pass: parse all data (allows cross-referencing)
        results = {}
        
        # A fetched response can still be empty or malformed. One optional
        # provider must not terminate collection of the other independent feeds.
        parsers = {
            'sunspot_cycle': self._parse_sunspot_cycle,
            'solar_wind_l1': self._parse_solar_wind,
            'mag_field_l1': lambda data: self._parse_mag_field(
                data, (results.get('solar_wind_l1') or {}).get('speed')),
            'proton_flux': self._parse_proton_flux,
            'electron_flux': self._parse_electron_flux,
            'xray_flux': self._parse_xray,
            'alerts': self._parse_alerts,
            'aurora_forecast': self._parse_aurora,
        }
        for name, parser in parsers.items():
            if name not in raw_data:
                continue
            try:
                result = parser(raw_data[name])
                if isinstance(result, dict) and result:
                    results[name] = result
                else:
                    logger.warning("   ⚠️ %s: no usable provider reading", name)
            except Exception as error:
                logger.warning("   ⚠️ %s: provider parse failed (%s)", name, type(error).__name__)
        
        for name, result in results.items():
            if result:
                logger.info(f"   ✅ {name}: collected")
        
        # Build unified solar system state
        state = self._build_state(results)
        if state:
            self._save_state(state)
        
        return state
    
    def _build_state(self, results: dict) -> dict:
        """Build unified solar system state"""
        # Callers may retain an optional source whose parser returned None.
        # Count and dereference only actual readings; never synthesize a zero
        # or a current provider timestamp for a missing source.
        results = {name: result for name, result in results.items()
                   if name in SOLAR_SOURCES and isinstance(result, dict) and result}
        if not results:
            logger.error("❌ No solar system data available")
            return None
        
        state = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'timestamp_kind': 'collection_time',
            'collection_status': {
                'total_sources': len(SOLAR_SOURCES),
                'successful_sources': len(results),
                'failed_sources': len(SOLAR_SOURCES) - len(results),
                'available_source_names': sorted(results),
                'unavailable_source_names': sorted(set(SOLAR_SOURCES) - set(results)),
                'complete': len(results) == len(SOLAR_SOURCES),
            },
            'solar_activity': {},
            'solar_wind': {},
            'magnetic_field': {},
            'particle_environment': {},
            'alerts': {},
            'aurora': {},
            'solar_system_health': {}
        }
        
        # Solar activity
        if 'sunspot_cycle' in results:
            r = results['sunspot_cycle']
            state['solar_activity'] = {
                'sunspot_number': r['sunspot_number'],
                'f10.7_flux': r['f10.7_flux'],
                'cycle_phase': r['cycle_phase'],
                'activity_level': r['activity_level'],
                'time_tag': r['time_tag']
            }
        
        # Solar wind
        if 'solar_wind_l1' in results:
            r = results['solar_wind_l1']
            state['solar_wind'] = {
                'speed': r['speed'],
                'density': r['density'],
                'temperature': r['temperature'],
                'dynamic_pressure': r['dynamic_pressure'],
                'regime': r['regime'],
                'time_tag': r['time_tag']
            }
        
        # Magnetic field
        if 'mag_field_l1' in results:
            r = results['mag_field_l1']
            state['magnetic_field'] = {
                'bx': r['bx'],
                'by': r['by'],
                'bz': r['bz'],
                'bt': r['bt'],
                'clock_angle': r['clock_angle'],
                'coupling_efficiency': r['coupling_efficiency'],
                'time_tag': r['time_tag']
            }
        
        # Particle environment
        state['particle_environment'] = {}
        if 'proton_flux' in results:
            state['particle_environment']['proton_flux'] = results['proton_flux']['flux']
            state['particle_environment']['sep_level'] = results['proton_flux']['sep_level']
        if 'electron_flux' in results:
            state['particle_environment']['electron_flux'] = results['electron_flux']['flux']
        if 'xray_flux' in results:
            state['particle_environment']['xray_flux'] = results['xray_flux']['flux']
            state['particle_environment']['flare_class'] = results['xray_flux']['flare_class']
        
        # Alerts
        if 'alerts' in results:
            r = results['alerts']
            state['alerts'] = {
                'total': r['total_alerts'],
                'geomagnetic': r['geomagnetic_alerts'],
                'radio_blackout': r['radio_blackout_alerts'],
                'radiation_storm': r['radiation_storm_alerts'],
                'max_geomagnetic_scale': r['max_geomagnetic_scale'],
                'max_radio_scale': r['max_radio_scale'],
                'max_radiation_scale': r['max_radiation_scale']
            }
        
        # Aurora
        if 'aurora_forecast' in results:
            r = results['aurora_forecast']
            state['aurora'] = {
                'power': r['auroral_power'],
                'coordinate_count': r['coordinate_count']
            }
        
        # Solar system health score
        state['solar_system_health'] = self._calculate_health(state)
        state['solar_system_health']['assessment_scope'] = 'available_sources_only'
        state['solar_system_health']['data_complete'] = state['collection_status']['complete']
        
        # Raw results for detail
        state['raw_results'] = results
        
        logger.info(f"✅ Solar system state built: {len(results)}/{len(SOLAR_SOURCES)} sources")
        return state
    
    def _calculate_health(self, state: dict) -> dict:
        """Calculate overall solar system health indicators"""
        health = {
            'score': 1.0,
            'threat_level': 'low',
            'concerns': []
        }
        
        # Check solar activity
        solar = state.get('solar_activity', {})
        if solar.get('activity_level') in ['high', 'very_high', 'extreme']:
            health['score'] -= 0.3
            health['concerns'].append(f"High solar activity: {solar.get('activity_level')}")
        
        # Check solar wind
        sw = state.get('solar_wind', {})
        if sw.get('speed', 0) > 600:
            health['score'] -= 0.2
            health['concerns'].append(f"High-speed solar wind: {sw.get('speed'):.0f} km/s")
        if sw.get('dynamic_pressure', 0) > 10:
            health['score'] -= 0.2
            health['concerns'].append(f"High dynamic pressure: {sw.get('dynamic_pressure'):.1f} nPa")
        
        # Check magnetic field
        mag = state.get('magnetic_field', {})
        if mag.get('bz', 0) < -10:
            health['score'] -= 0.3
            health['concerns'].append(f"Strong southward Bz: {mag.get('bz'):.1f} nT")
        
        # Check alerts
        alerts = state.get('alerts', {})
        if alerts.get('max_geomagnetic_scale', 0) >= 5:
            health['score'] -= 0.3
            health['concerns'].append(f"Extreme geomagnetic storm (G{alerts.get('max_geomagnetic_scale')})")
        elif alerts.get('max_geomagnetic_scale', 0) >= 3:
            health['score'] -= 0.2
            health['concerns'].append(f"Strong geomagnetic storm (G{alerts.get('max_geomagnetic_scale')})")
        
        if alerts.get('max_radio_scale', 0) >= 3:
            health['score'] -= 0.1
            health['concerns'].append(f"Strong radio blackout (R{alerts.get('max_radio_scale')})")
        
        # Check particles
        particles = state.get('particle_environment', {})
        if particles.get('sep_level') in ['strong', 'extreme']:
            health['score'] -= 0.2
            health['concerns'].append(f"Solar proton event: {particles.get('sep_level')}")
        
        # Clamp score
        health['score'] = max(0.0, min(1.0, health['score']))
        
        # Set threat level
        if health['score'] >= 0.8:
            health['threat_level'] = 'low'
        elif health['score'] >= 0.5:
            health['threat_level'] = 'moderate'
        elif health['score'] >= 0.2:
            health['threat_level'] = 'high'
        else:
            health['threat_level'] = 'extreme'
        
        return health
    
    def _save_state(self, state: dict):
        """Save state to files"""
        # Save latest state
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2, default=str)
        
        # Append to timeseries
        with open(TIMESERIES_FILE, 'a') as f:
            f.write(json.dumps({
                'timestamp': state['timestamp'],
                'health_score': state['solar_system_health']['score'],
                'threat_level': state['solar_system_health']['threat_level'],
                'solar_activity': state.get('solar_activity', {}),
                'solar_wind': state.get('solar_wind', {}),
                'alerts': state.get('alerts', {})
            }, default=str) + '\n')
        
        self.collection_history.append(state)
    
    def get_latest(self) -> Optional[dict]:
        """Get latest solar system state"""
        if STATE_FILE.exists():
            with open(STATE_FILE) as f:
                return json.load(f)
        return None
    
    def run_continuous(self, interval_seconds: int = 300):
        """Run continuous collection"""
        logger.info(f"🏃 Continuous solar system monitoring: {interval_seconds}s interval")
        
        try:
            while True:
                self.collect()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("🛑 Solar system monitoring stopped")


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    import argparse
    
    parser = argparse.ArgumentParser(description='Solar System Metrics Collector')
    parser.add_argument('--once', action='store_true', help='Run one collection and exit')
    parser.add_argument('--interval', type=int, default=300, help='Collection interval (seconds)')
    parser.add_argument('--status', action='store_true', help='Show latest state')
    args = parser.parse_args()
    
    collector = SolarSystemCollector()
    
    if args.status:
        latest = collector.get_latest()
        if latest:
            print(json.dumps(latest, indent=2, default=str))
        else:
            print("No solar system data available")
    elif args.once:
        result = collector.collect()
        if result:
            # Print summary
            print(f"\n🌌 SOLAR SYSTEM STATE")
            print(f"   Time: {result['timestamp']}")
            print(f"   Sources: {result['collection_status']['successful_sources']}/{result['collection_status']['total_sources']}")
            
            health = result['solar_system_health']
            print(f"\n   Health Score: {health['score']:.2f}")
            print(f"   Threat Level: {health['threat_level'].upper()}")
            
            if health['concerns']:
                print(f"\n   ⚠️ Concerns:")
                for c in health['concerns']:
                    print(f"      • {c}")
            else:
                print(f"\n   ✅ All systems nominal")
            
            solar = result.get('solar_activity', {})
            if solar:
                print(f"\n   ☀️ Solar Activity:")
                print(f"      SSN: {solar.get('sunspot_number', 'N/A')}")
                print(f"      F10.7: {solar.get('f10.7_flux', 'N/A')} sfu")
                print(f"      Phase: {solar.get('cycle_phase', 'N/A')}")
            
            sw = result.get('solar_wind', {})
            if sw:
                print(f"\n   🌬️ Solar Wind (L1):")
                print(f"      Speed: {sw.get('speed', 'N/A'):.1f} km/s")
                print(f"      Density: {sw.get('density', 'N/A'):.2f} cm⁻³")
                print(f"      Pressure: {sw.get('dynamic_pressure', 'N/A'):.2f} nPa")
            
            mag = result.get('magnetic_field', {})
            if mag:
                print(f"\n   🧲 IMF (L1):")
                print(f"      Bz: {mag.get('bz', 'N/A'):.2f} nT")
                print(f"      Bt: {mag.get('bt', 'N/A'):.2f} nT")
            
            alerts = result.get('alerts', {})
            if alerts:
                print(f"\n   🚨 Alerts:")
                print(f"      Total: {alerts.get('total', 0)}")
                print(f"      G-scale max: {alerts.get('max_geomagnetic_scale', 0)}")
        else:
            print("Collection failed")
    else:
        collector.run_continuous(args.interval)
