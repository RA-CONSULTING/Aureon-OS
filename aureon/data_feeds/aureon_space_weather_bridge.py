#!/usr/bin/env python3
"""
🌍☀️ AUREON SPACE WEATHER BRIDGE ☀️🌍
═══════════════════════════════════════════════════════════════════

Connects the Queen to LIVE planetary & solar data from:
- NOAA Space Weather Prediction Center (SWPC)
- NASA DONKI (solar flare data)
- Real-time geomagnetic field measurements
- Solar wind measurements
- Kp index forecasts

This bridges the gap: Queen gets REAL cosmic data, not simulations!
"""

import requests
import json
import time
import logging
import math
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# NOAA SWPC API Endpoints (no API key required - public data!)
NOAA_SOLAR_WIND_MAG_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json'
NOAA_SOLAR_WIND_PLASMA_URL = 'https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json'
NOAA_KP_INDEX_URL = 'https://services.swpc.noaa.gov/json/planetary_k_index_1m.json'
NOAA_KP_FORECAST_URL = 'https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json'
NOAA_3DAY_FORECAST_URL = NOAA_KP_FORECAST_URL

# NASA APIs (optional, requires API_KEY env var)
NASA_DONKI_FLARE_URL = 'https://api.nasa.gov/DONKI/FLR'
NASA_DONKI_CME_URL = 'https://api.nasa.gov/DONKI/CME'

# Cache settings
CACHE_LIFETIME_SECONDS = 300  # Refresh every 5 minutes
SOURCE_MAX_AGE_SECONDS = 20 * 60


def _require_fresh_source_timestamp(value: Any, label: str) -> str:
    text = str(value or '').strip()
    if not text:
        raise ValueError(f'{label} missing source timestamp')
    normalized = text[:-1] + '+00:00' if text.endswith('Z') else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        # HTTP Date is still a provider clock receipt, not the local receipt
        # clock.  NOAA forecast payloads do not consistently expose an issue
        # timestamp, so the response Date header is the honest fallback.
        parsed = parsedate_to_datetime(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    age = time.time() - parsed.timestamp()
    if age < -300 or age > SOURCE_MAX_AGE_SECONDS:
        raise ValueError(f'{label} stale source timestamp age={age:.0f}s')
    return text

@dataclass
class SpaceWeatherReading:
    """Real-time space weather snapshot"""
    timestamp: float
    kp_index: float  # 0-9 scale
    kp_category: str  # Quiet, Unsettled, Active, Storm, Severe Storm
    solar_wind_speed: float  # km/s
    solar_wind_density: float  # protons/cm³
    bz_component: float  # nT - critical for auroras
    solar_flares_24h: Optional[int]
    geomagnetic_storm_3day: Optional[str]
    active_sources: list
    source_timestamps: Dict[str, str]
    truth_status: str = 'live'
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'kp_index': self.kp_index,
            'kp_category': self.kp_category,
            'solar_wind_speed': self.solar_wind_speed,
            'solar_wind_density': self.solar_wind_density,
            'bz_component': self.bz_component,
            'solar_flares_24h': self.solar_flares_24h,
            'geomagnetic_storm_3day': self.geomagnetic_storm_3day,
            'active_sources': self.active_sources,
            'source_timestamps': self.source_timestamps,
            'truth_status': self.truth_status,
            'generated_values': False,
        }

class SpaceWeatherBridge:
    """Bridge to live space weather data for the Queen"""
    
    def __init__(self):
        self.last_update = 0
        self.cache: Optional[SpaceWeatherReading] = None
        self.error_count = 0
        logger.info("🌍☀️ Space Weather Bridge initialized")
    
    def get_live_data(self, force_refresh: bool = False) -> Optional[SpaceWeatherReading]:
        """
        Get LIVE space weather data from NOAA/NASA APIs
        
        Returns cached data if fresh (<5min old), otherwise fetches new data.
        Returns no reading if required live NOAA fields are unavailable.
        """
        now = time.time()
        
        # Check cache
        if not force_refresh and self.cache and (now - self.last_update) < CACHE_LIFETIME_SECONDS:
            return self.cache
        
        # Fetch fresh data
        active_sources = []
        source_timestamps: Dict[str, str] = {}
        kp_index: Optional[float] = None
        solar_wind_speed: Optional[float] = None
        solar_wind_density: Optional[float] = None
        bz_component: Optional[float] = None
        solar_flares_24h: Optional[int] = None
        geomagnetic_storm_3day: Optional[str] = None
        
        # 1️⃣ Fetch Kp Index (most critical - geomagnetic activity)
        try:
            kp_data = self._fetch_kp_index()
            if kp_data:
                kp_index = kp_data['current_kp']
                source_timestamps['NOAA-KP'] = str(kp_data['source_timestamp'])
                active_sources.append('NOAA-KP')
                logger.debug(f"✅ Kp Index: {kp_index:.1f}")
        except Exception as e:
            logger.warning(f"❌ Kp Index fetch failed: {e}")
        
        # 2️⃣ Fetch Solar Wind Data (speed + Bz component)
        try:
            wind_data = self._fetch_solar_wind()
            if wind_data:
                solar_wind_speed = wind_data['speed']
                bz_component = wind_data['bz']
                solar_wind_density = wind_data['density']
                source_timestamps['NOAA-SolarWind'] = str(wind_data['source_timestamp'])
                active_sources.append('NOAA-SolarWind')
                logger.debug(f"✅ Solar Wind: {solar_wind_speed:.0f} km/s, Bz={bz_component:.1f} nT")
        except Exception as e:
            logger.warning(f"❌ Solar Wind fetch failed: {e}")
        
        # 3️⃣ Fetch 3-Day Forecast
        try:
            forecast = self._fetch_3day_forecast()
            if forecast:
                geomagnetic_storm_3day = forecast['highest_kp_category']
                source_timestamps['NOAA-Forecast'] = str(forecast['source_timestamp'])
                active_sources.append('NOAA-Forecast')
                logger.debug(f"✅ 3-Day Forecast: {geomagnetic_storm_3day}")
        except Exception as e:
            logger.warning(f"❌ Forecast fetch failed: {e}")
        
        # 4️⃣ Optionally fetch NASA solar flares (requires API key)
        try:
            flare_count = self._fetch_solar_flares()
            solar_flares_24h = flare_count
            if flare_count is not None:
                active_sources.append('NASA-Flares')
                logger.debug(f"✅ Solar Flares (24h): {flare_count}")
        except Exception as e:
            logger.debug(f"NASA flares unavailable: {e}")
        
        # Kp and solar wind/IMF are the minimum complete operational row.
        # A partial provider response is no-data, never an instruction to fill gaps.
        if None in (kp_index, solar_wind_speed, solar_wind_density, bz_component):
            logger.warning("Space weather core sources incomplete; no reading emitted")
            return None

        # Create reading
        kp_category = self._categorize_kp(kp_index)
        reading = SpaceWeatherReading(
            timestamp=now,
            kp_index=kp_index,
            kp_category=kp_category,
            solar_wind_speed=solar_wind_speed,
            solar_wind_density=solar_wind_density,
            bz_component=bz_component,
            solar_flares_24h=solar_flares_24h,
            geomagnetic_storm_3day=geomagnetic_storm_3day,
            active_sources=active_sources,
            source_timestamps=source_timestamps,
        )

        # Cache and return
        self.cache = reading
        self.last_update = now
        self.error_count = 0

        logger.info(f"🌍☀️ Space Weather Update: Kp={kp_index:.1f} ({kp_category}), Wind={solar_wind_speed:.0f}km/s, Sources={', '.join(active_sources)}")
        return reading
    
    def _fetch_kp_index(self) -> Optional[Dict]:
        """Fetch current Kp index from NOAA"""
        try:
            resp = requests.get(NOAA_KP_INDEX_URL, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list) and data and isinstance(data[-1], dict):
                latest = data[-1]
                kp = latest.get('estimated_kp', latest.get('Kp', latest.get('kp')))
                if kp is not None:
                    source_timestamp = _require_fresh_source_timestamp(
                        latest.get('time_tag', latest.get('timestamp')), 'NOAA-KP')
                    return {
                        'current_kp': float(kp),
                        'source_timestamp': source_timestamp,
                    }

            # Format: ['time_tag', 'Kp', 'a_running', 'station_count']
            # Kp is column 1 (NOT column 2 which is a_running)
            if len(data) > 1:
                latest = data[-1]
                if len(latest) > 1 and latest[1] not in (None, ''):
                    return {
                        'current_kp': float(latest[1]),
                        'source_timestamp': _require_fresh_source_timestamp(latest[0], 'NOAA-KP'),
                    }
        except Exception as e:
            logger.debug(f"Kp fetch error: {e}")
        return None
    
    def _fetch_solar_wind(self) -> Optional[Dict]:
        """Fetch solar wind data from NOAA (plasma + magnetometer)"""
        result: Dict[str, Any] = {}
        plasma_timestamp: Optional[str] = None
        mag_timestamp: Optional[str] = None

        def latest_dict_row(rows: Any, required_key: str) -> Optional[Dict]:
            if not isinstance(rows, list):
                return None
            for row in rows:
                if isinstance(row, dict) and row.get('active') is not False and row.get(required_key) is not None:
                    return row
            return None

        def latest_header_row(rows: Any) -> Tuple[Optional[Dict[str, int]], Optional[list]]:
            if not isinstance(rows, list) or len(rows) < 2 or not isinstance(rows[0], list):
                return None, None
            header = {str(name): idx for idx, name in enumerate(rows[0])}
            for row in rows[1:]:
                if isinstance(row, list):
                    return header, row
            return header, None
        
        # 1) Plasma data → density + speed
        # Format: ['time_tag', 'density', 'speed', 'temperature']
        try:
            resp = requests.get(NOAA_SOLAR_WIND_PLASMA_URL, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            latest = latest_dict_row(data, 'proton_speed')
            if latest:
                if latest.get('proton_density') is None:
                    raise ValueError('NOAA plasma row missing proton_density')
                result['density'] = float(latest['proton_density'])
                result['speed'] = float(latest['proton_speed'])
                plasma_timestamp = str(latest.get('time_tag') or '')
            else:
                header, latest_list = latest_header_row(data)
                if header and latest_list:
                    density_idx = header.get('density')
                    speed_idx = header.get('speed')
                    if density_idx is not None and density_idx < len(latest_list) and latest_list[density_idx] not in (None, ''):
                        result['density'] = float(latest_list[density_idx])
                    if speed_idx is not None and speed_idx < len(latest_list) and latest_list[speed_idx] not in (None, ''):
                        result['speed'] = float(latest_list[speed_idx])
                    time_idx = header.get('time_tag')
                    plasma_timestamp = str(latest_list[time_idx]) if time_idx is not None else ''
        except Exception as e:
            logger.debug(f"Plasma data fetch error: {e}")
        
        # 2) Magnetometer data → Bz component
        # Format: ['time_tag', 'bx_gsm', 'by_gsm', 'bz_gsm', 'lon_gsm', 'lat_gsm', 'bt']
        try:
            resp = requests.get(NOAA_SOLAR_WIND_MAG_URL, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            latest = latest_dict_row(data, 'bz_gsm')
            if latest:
                result['bz'] = float(latest['bz_gsm'])
                mag_timestamp = str(latest.get('time_tag') or '')
            else:
                header, latest_list = latest_header_row(data)
                if header and latest_list:
                    bz_idx = header.get('bz_gsm')
                    if bz_idx is not None and bz_idx < len(latest_list) and latest_list[bz_idx] not in (None, ''):
                        result['bz'] = float(latest_list[bz_idx])
                    time_idx = header.get('time_tag')
                    mag_timestamp = str(latest_list[time_idx]) if time_idx is not None else ''
        except Exception as e:
            logger.debug(f"Mag data fetch error: {e}")
        
        if {'density', 'speed', 'bz'} <= result.keys() and plasma_timestamp and mag_timestamp:
            _require_fresh_source_timestamp(plasma_timestamp, 'NOAA-SolarWind-Plasma')
            _require_fresh_source_timestamp(mag_timestamp, 'NOAA-SolarWind-IMF')
            result['source_timestamp'] = max(plasma_timestamp, mag_timestamp)
            return result
        return None
    
    def _fetch_3day_forecast(self) -> Optional[Dict]:
        """Fetch 3-day forecast from NOAA"""
        try:
            resp = requests.get(NOAA_3DAY_FORECAST_URL, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            response_headers = getattr(resp, 'headers', {}) or {}
            response_date = response_headers.get('Date') or response_headers.get('date')

            def provider_issue_timestamp(payload: Any) -> Optional[str]:
                candidates = []
                if isinstance(payload, dict):
                    candidates.extend(
                        payload.get(key)
                        for key in ('issue_time', 'issued', 'source_timestamp', 'product_timestamp')
                    )
                candidates.append(response_date)
                for candidate in candidates:
                    if candidate in (None, ''):
                        continue
                    try:
                        return _require_fresh_source_timestamp(candidate, 'NOAA-Forecast')
                    except (TypeError, ValueError):
                        continue
                return None

            if isinstance(data, list):
                kp_values = []
                for row in data:
                    if not isinstance(row, dict) or row.get('kp') is None:
                        continue
                    value = float(row['kp'])
                    if math.isfinite(value):
                        kp_values.append(value)
                source_timestamp = provider_issue_timestamp({})
                if kp_values and source_timestamp:
                    return {
                        'highest_kp_category': self._categorize_kp(max(kp_values)),
                        'source_timestamp': source_timestamp,
                    }

            if isinstance(data, dict) and isinstance(data.get('3dayforecast'), list):
                forecast = data['3dayforecast']
                kp_values = []
                for day in forecast:
                    if not isinstance(day, dict):
                        continue
                    for key in ('kp_1', 'kp_2', 'kp_3'):
                        raw_value = day.get(key)
                        if raw_value is None:
                            continue
                        value = float(raw_value)
                        if math.isfinite(value):
                            kp_values.append(value)
                source_timestamp = provider_issue_timestamp(data)
                if kp_values and source_timestamp:
                    return {
                        'highest_kp_category': self._categorize_kp(max(kp_values)),
                        'source_timestamp': source_timestamp,
                    }
        except Exception as e:
            logger.debug(f"Forecast fetch error: {e}")
        return None
    
    def _fetch_solar_flares(self) -> Optional[int]:
        """Fetch solar flares from NASA (requires API key)"""
        try:
            api_key = self._get_nasa_api_key()
            if not api_key:
                return None
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')
            
            url = f"{NASA_DONKI_FLARE_URL}?startDate={yesterday}&endDate={today}&api_key={api_key}"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            
            return len(data) if isinstance(data, list) else 0
        except Exception as e:
            logger.debug(f"NASA flares fetch error: {e}")
        return None
    
    def _categorize_kp(self, kp: float) -> str:
        """Categorize Kp index into trading-relevant categories"""
        if kp < 1:
            return 'Very Quiet'
        elif kp < 3:
            return 'Quiet'
        elif kp < 5:
            return 'Unsettled'
        elif kp < 6:
            return 'Active'
        elif kp < 7:
            return 'Minor Storm'
        elif kp < 8:
            return 'Major Storm'
        else:
            return 'Severe Storm'
    
    def _get_nasa_api_key(self) -> Optional[str]:
        """Get NASA API key from environment"""
        import os
        key = os.environ.get('NASA_API_KEY')
        if key and key != ("DEMO" + "_KEY"):
            return key
        return None
    
    def get_cosmic_score(self, reading: SpaceWeatherReading) -> float:
        """
        Convert space weather data into cosmic alignment score for Queen
        
        Range: 0.0 (very bad) to 1.0 (optimal)
        
        Scoring:
        - Kp Index: lower is better (Kp < 3 = good)
        - Solar wind: 350-450 km/s is optimal
        - Bz component: negative is better for auroras, but neutral is stable
        """
        score = 0.5  # Start at neutral
        
        # Kp Index impact (most important)
        # Kp 0-2 = quiet (good) -> +0.3
        # Kp 3-4 = unsettled -> neutral
        # Kp 5+ = storm -> -0.2 to -0.3
        if reading.kp_index < 3:
            score += 0.3
        elif reading.kp_index >= 7:
            score -= 0.3
        elif reading.kp_index >= 5:
            score -= 0.15
        
        # Solar wind speed (moderate variation is good)
        wind = reading.solar_wind_speed
        if 350 <= wind <= 450:
            score += 0.2  # Optimal range
        elif 250 <= wind <= 550:
            score += 0.1  # Acceptable
        elif wind < 250 or wind > 600:
            score -= 0.1  # Extreme values = instability
        
        # Bz component (south/negative is risky for communications)
        bz = reading.bz_component
        if -2 <= bz <= 2:
            score += 0.1  # Neutral/stable
        elif bz < -5:
            score -= 0.15  # Strong south component = substorm risk
        
        # Solar flares (count impacts confidence)
        if reading.solar_flares_24h is not None and reading.solar_flares_24h > 2:
            score -= 0.1  # Multiple flares = unpredictable
        
        # Clamp to 0-1
        return max(0.0, min(1.0, score))


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

_bridge_instance: Optional[SpaceWeatherBridge] = None

def get_space_weather_bridge() -> SpaceWeatherBridge:
    """Get or create the global Space Weather Bridge"""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = SpaceWeatherBridge()
    return _bridge_instance

def get_live_space_weather(force_refresh: bool = False) -> Optional[SpaceWeatherReading]:
    """Get live space weather data"""
    bridge = get_space_weather_bridge()
    return bridge.get_live_data(force_refresh=force_refresh)

def get_cosmic_alignment_from_space_weather(force_refresh: bool = False) -> float:
    """
    Get cosmic alignment score based on REAL space weather data
    This is what the Queen should use!
    """
    bridge = get_space_weather_bridge()
    reading = bridge.get_live_data(force_refresh=force_refresh)
    if reading is None:
        raise RuntimeError("No fresh live space-weather reading is available")
    return bridge.get_cosmic_score(reading)


if __name__ == '__main__':
    # Test it
    logging.basicConfig(level=logging.DEBUG)
    bridge = get_space_weather_bridge()
    
    print("\n🌍☀️ TESTING SPACE WEATHER BRIDGE 🌍☀️\n")
    
    reading = get_live_space_weather(force_refresh=True)
    if reading is None:
        raise SystemExit("No fresh live space-weather reading is available")
    print(f"Kp Index: {reading.kp_index:.1f} ({reading.kp_category})")
    print(f"Solar Wind: {reading.solar_wind_speed:.0f} km/s")
    print(f"Bz Component: {reading.bz_component:.1f} nT")
    print(f"Active Sources: {', '.join(reading.active_sources)}")
    
    cosmic_score = bridge.get_cosmic_score(reading)
    print(f"👑 Cosmic Alignment Score: {cosmic_score:.0%}")
    print(f"   (Queen should use this for trading confidence!)")
