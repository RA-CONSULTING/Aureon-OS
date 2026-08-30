#!/usr/bin/env python3
"""Fresh, provenance-bearing biometric and GPS observation tracker.

The original module started at an invented Belfast position with fabricated
biometrics. This implementation has no startup reading. A state exists only
after a fresh device observation is supplied, and stale state becomes
unavailable instead of being carried forward indefinitely.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link

_baton_link(__name__)

import math
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional


BELFAST_REFERENCE = {"lat": 54.5973, "lng": -5.9301}
FRESHNESS_TTL_SECONDS = 30.0


def _source_epoch(value: Any) -> float:
    if isinstance(value, (int, float)):
        epoch = float(value)
        return epoch / 1000.0 if epoch > 10_000_000_000 else epoch
    text = str(value or "").strip()
    if not text:
        raise ValueError("SOURCE_TIMESTAMP_REQUIRED")
    normalized = text.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).timestamp()


def _require_fresh_provenance(observation: Dict[str, Any]) -> tuple[str, str, float]:
    source_id = str(observation.get("source_id") or "").strip()
    source_event_id = str(observation.get("source_event_id") or "").strip()
    source_timestamp = _source_epoch(observation.get("source_timestamp"))
    age = time.time() - source_timestamp
    if (
        observation.get("truth_status") != "live"
        or observation.get("generated_values") is not False
        or not source_id
        or not source_event_id
        or age < -30
        or age > FRESHNESS_TTL_SECONDS
    ):
        raise ValueError("FRESH_LIVE_DEVICE_PROVENANCE_REQUIRED")
    return source_id, source_event_id, source_timestamp


def _finite(observation: Dict[str, Any], field: str, *, positive: bool = False) -> float:
    value = observation.get(field)
    if isinstance(value, bool):
        raise ValueError(f"INVALID_DEVICE_VALUE:{field}")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_DEVICE_VALUE:{field}") from exc
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError(f"INVALID_DEVICE_VALUE:{field}")
    return number


@dataclass
class LiveLocationSnapshot:
    timestamp: float
    consciousness_state: str
    calm_index: float
    eeg_coherence: float
    hrv_rmssd: float
    gsr_uS: float
    respiration_bpm: float
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_accuracy_m: Optional[float] = None
    primary_anchor: str = "Belfast reference"
    consciousness_lock_strength: float = 0.0
    best_match_stargate: str = "Belfast reference"
    distance_from_belfast_km: Optional[float] = None
    movement_speed_kmh: Optional[float] = None
    trading_multiplier: float = 1.0
    truth_status: str = "real_derived"
    source_id: str = ""
    source_event_id: str = ""
    source_timestamp: float = 0.0
    generated_values: bool = False
    gps_source_id: Optional[str] = None
    gps_source_event_id: Optional[str] = None
    gps_source_timestamp: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LiveAuraLocationTracker:
    """Derive state only from fresh biometric and GPS device observations."""

    def __init__(self):
        self.is_active = False
        self.current_snapshot: Optional[LiveLocationSnapshot] = None
        self.aura_history = deque(maxlen=60)
        self.gps_history = deque(maxlen=60)
        self.last_update: Optional[float] = None
        self.lock = threading.RLock()
        self._pending_gps: Optional[Dict[str, Any]] = None
        self.reality_lock_active = False
        self.reality_variant = None
        self.reality_class = None
        self.real_brainwaves_detected = False
        self.real_heart_rate: Optional[float] = None
        self.schumann_boost: Optional[float] = None
        self.earth_disturbance_level: Optional[float] = None

    def start(self) -> bool:
        """Arm the tracker without creating an initial observation."""
        self.is_active = True
        return True

    def stop(self) -> None:
        self.is_active = False

    def update_from_biometric(self, aura_data: Dict[str, Any]) -> LiveLocationSnapshot:
        """Ingest one complete fresh biometric device observation."""
        if not self.is_active:
            raise RuntimeError("LIVE_AURA_TRACKER_NOT_STARTED")
        source_id, source_event_id, source_timestamp = _require_fresh_provenance(aura_data)
        bands = aura_data.get("bands")
        if not isinstance(bands, dict):
            raise ValueError("BIOMETRIC_BANDS_REQUIRED")
        alpha_hz = _finite(bands, "alpha", positive=True)
        theta_hz = _finite(bands, "theta", positive=True)
        beta_hz = _finite(bands, "beta", positive=True)
        hrv = _finite(aura_data, "hrv_rmssd", positive=True)
        gsr = _finite(aura_data, "gsr_uS")
        respiration = _finite(aura_data, "resp_bpm", positive=True)
        heart_rate = _finite(aura_data, "heart_rate_bpm", positive=True)

        hrv_calm = min(1.0, hrv / 60.0)
        alpha_calm = min(1.0, alpha_hz / 3.0)
        beta_stress = max(0.0, 1.0 - beta_hz / 2.0)
        respiration_calm = max(0.0, 1.0 - abs(respiration - 6.0) / 12.0)
        calm_index = max(0.0, min(1.0,
            hrv_calm * 0.3 + alpha_calm * 0.3 + beta_stress * 0.2 + respiration_calm * 0.2
        ))
        eeg_coherence = (alpha_hz + theta_hz) / (alpha_hz + theta_hz + beta_hz + 0.1)

        if eeg_coherence >= 0.85 and calm_index >= 0.7:
            consciousness_state = "MEDITATIVE"
        elif eeg_coherence >= 0.75 and calm_index >= 0.6:
            consciousness_state = "AWAKENED"
        elif calm_index <= 0.4 and beta_hz > 1.5:
            consciousness_state = "ALERT"
        elif calm_index <= 0.4:
            consciousness_state = "STRESSED"
        elif calm_index >= 0.6:
            consciousness_state = "CALM"
        else:
            consciousness_state = "AWAKE"

        with self.lock:
            gps = self._pending_gps
            snapshot = LiveLocationSnapshot(
                timestamp=source_timestamp,
                consciousness_state=consciousness_state,
                calm_index=calm_index,
                eeg_coherence=eeg_coherence,
                hrv_rmssd=hrv,
                gsr_uS=gsr,
                respiration_bpm=respiration,
                consciousness_lock_strength=calm_index,
                trading_multiplier=0.5 + calm_index * 1.5,
                source_id=source_id,
                source_event_id=source_event_id,
                source_timestamp=source_timestamp,
            )
            self.current_snapshot = snapshot
            self.real_brainwaves_detected = True
            self.real_heart_rate = heart_rate
            if gps is not None:
                self._apply_gps(snapshot, gps)
            self.aura_history.append(snapshot)
            self.last_update = time.time()
            return snapshot

    def _apply_gps(self, snapshot: LiveLocationSnapshot, gps: Dict[str, Any]) -> None:
        snapshot.gps_latitude = gps["latitude"]
        snapshot.gps_longitude = gps["longitude"]
        snapshot.gps_accuracy_m = gps["accuracy"]
        snapshot.movement_speed_kmh = gps["speed"]
        snapshot.distance_from_belfast_km = self.haversine_distance(
            gps["latitude"], gps["longitude"], BELFAST_REFERENCE["lat"], BELFAST_REFERENCE["lng"]
        )
        snapshot.gps_source_id = gps["source_id"]
        snapshot.gps_source_event_id = gps["source_event_id"]
        snapshot.gps_source_timestamp = gps["source_timestamp"]

    def update_from_gps(self, gps_data: Dict[str, Any]) -> Optional[LiveLocationSnapshot]:
        """Ingest a fresh GPS provider observation; never assume Belfast."""
        source_id, source_event_id, source_timestamp = _require_fresh_provenance(gps_data)
        latitude = _finite(gps_data, "latitude")
        longitude = _finite(gps_data, "longitude")
        accuracy = _finite(gps_data, "accuracy")
        speed = _finite(gps_data, "speed")
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180 or accuracy < 0 or speed < 0:
            raise ValueError("INVALID_GPS_OBSERVATION")
        observation = {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
            "speed": speed,
            "source_id": source_id,
            "source_event_id": source_event_id,
            "source_timestamp": source_timestamp,
        }
        with self.lock:
            self._pending_gps = observation
            if self.current_snapshot is None:
                return None
            self._apply_gps(self.current_snapshot, observation)
            self.gps_history.append(self.current_snapshot)
            self.last_update = time.time()
            return self.current_snapshot

    def get_current_location(self) -> Optional[Dict[str, Any]]:
        """Return a fresh observed/derived snapshot or no data."""
        with self.lock:
            if self.current_snapshot is None:
                return None
            if time.time() - self.current_snapshot.source_timestamp > FRESHNESS_TTL_SECONDS:
                return None
            snapshot = self.current_snapshot.to_dict()
            snapshot.update({
                "reality_lock_active": False,
                "reality_variant": None,
                "reality_class": None,
                "real_brainwaves_detected": self.real_brainwaves_detected,
                "real_heart_rate": self.real_heart_rate,
                "schumann_boost": None,
                "earth_disturbance_level": None,
                "status": "OBSERVED",
            })
            return snapshot

    @staticmethod
    def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        radius_km = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        return radius_km * 2 * math.asin(math.sqrt(a))


_live_tracker: Optional[LiveAuraLocationTracker] = None


def get_live_tracker() -> LiveAuraLocationTracker:
    global _live_tracker
    if _live_tracker is None:
        _live_tracker = LiveAuraLocationTracker()
    return _live_tracker


if __name__ == "__main__":
    raise SystemExit("LIVE_BIOMETRIC_AND_GPS_PROVIDER_OBSERVATIONS_REQUIRED")
