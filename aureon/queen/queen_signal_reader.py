#!/usr/bin/env python3
"""Read only fresh signals actually supplied by device/provider connectors."""

from datetime import datetime, timezone
from typing import Any, Dict

from aureon.utils.aureon_live_aura_location_tracker import get_live_tracker


def _no_data(reason: str) -> Dict[str, Any]:
    return {"truth_status": "no_data", "generated_values": False, "reason": reason}


def detect_movement_state() -> Dict[str, Any]:
    snapshot = get_live_tracker().get_current_location()
    if not snapshot or snapshot.get("movement_speed_kmh") is None:
        return _no_data("FRESH_GPS_SPEED_OBSERVATION_REQUIRED")
    speed = float(snapshot["movement_speed_kmh"])
    return {
        "state": "STATIONARY" if speed < 0.5 else "MOVING",
        "speed_kmh": speed,
        "truth_status": "real_derived",
        "source_id": snapshot["gps_source_id"],
        "source_event_id": snapshot["gps_source_event_id"],
        "source_timestamp": snapshot["gps_source_timestamp"],
        "generated_values": False,
    }


def detect_consciousness_state() -> Dict[str, Any]:
    snapshot = get_live_tracker().get_current_location()
    if not snapshot:
        return _no_data("FRESH_BIOMETRIC_DEVICE_OBSERVATION_REQUIRED")
    return {
        "state": snapshot["consciousness_state"],
        "coherence": snapshot["eeg_coherence"],
        "calm_index": snapshot["calm_index"],
        "truth_status": "real_derived",
        "source_id": snapshot["source_id"],
        "source_event_id": snapshot["source_event_id"],
        "source_timestamp": snapshot["source_timestamp"],
        "generated_values": False,
    }


def detect_direction_from_signals() -> Dict[str, Any]:
    return _no_data("GPS_HEADING_OR_SUCCESSIVE_FRESH_FIXES_REQUIRED")


def detect_schumann_alignment() -> Dict[str, Any]:
    return _no_data("FRESH_SCHUMANN_AND_BIOMETRIC_PHASE_OBSERVATIONS_REQUIRED")


class QueenSignalReader:
    def read_all_signals(self) -> Dict[str, Any]:
        return {
            "movement": detect_movement_state(),
            "consciousness": detect_consciousness_state(),
            "direction": detect_direction_from_signals(),
            "schumann": detect_schumann_alignment(),
            "truth_status": "real_derived" if get_live_tracker().get_current_location() else "no_data",
            "generated_values": False,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }


if __name__ == "__main__":
    raise SystemExit("LIVE_DEVICE_PROVIDER_OBSERVATIONS_REQUIRED")
