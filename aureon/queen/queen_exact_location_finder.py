#!/usr/bin/env python3
"""Location reporting constrained to fresh observed GPS evidence.

No biometric, memory, quantum, social-graph, or Schumann value can establish a
person's physical address. This compatibility surface reports only a fresh GPS
fix and its accuracy radius; otherwise it returns ``no_data``.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from aureon.queen.queen_street_homing import QueenStreetLevelHoming
from aureon.utils.aureon_live_aura_location_tracker import get_live_tracker


def read_live_biometric_data() -> Dict[str, Any]:
    snapshot = get_live_tracker().get_current_location()
    return snapshot or {
        "truth_status": "no_data",
        "generated_values": False,
        "reason": "NO_FRESH_BIOMETRIC_OR_GPS_OBSERVATION",
    }


def read_quantum_field_anchor() -> Dict[str, Any]:
    return {"truth_status": "no_data", "generated_values": False, "reason": "NOT_A_LOCATION_SOURCE"}


def read_elephant_memory() -> Dict[str, Any]:
    return {"truth_status": "no_data", "generated_values": False, "reason": "HISTORY_IS_NOT_CURRENT_LOCATION"}


def read_barter_graph() -> Dict[str, Any]:
    return {"truth_status": "no_data", "generated_values": False, "reason": "SOCIAL_GRAPH_IS_NOT_GPS"}


def read_live_schumann_data() -> Dict[str, Any]:
    return {"truth_status": "no_data", "generated_values": False, "reason": "SCHUMANN_IS_NOT_A_LOCATION_SOURCE"}


class QueenExactLocationFinder:
    """Report an observed coordinate without claiming an unverified address."""

    def analyze_all_systems(self) -> Dict[str, Any]:
        snapshot = get_live_tracker().get_current_location()
        if not snapshot or snapshot.get("gps_latitude") is None or snapshot.get("gps_longitude") is None:
            return {
                "truth_status": "no_data",
                "generated_values": False,
                "reason": "FRESH_GPS_PROVIDER_OBSERVATION_REQUIRED",
                "observed_location": None,
            }
        nearest = QueenStreetLevelHoming().home_on_street({
            "latitude": snapshot["gps_latitude"],
            "longitude": snapshot["gps_longitude"],
            "accuracy": snapshot["gps_accuracy_m"],
            "speed": snapshot["movement_speed_kmh"],
            "truth_status": "live",
            "source_id": snapshot["gps_source_id"],
            "source_event_id": snapshot["gps_source_event_id"],
            "source_timestamp": snapshot["gps_source_timestamp"],
            "generated_values": False,
        })
        return {
            "truth_status": "real_derived",
            "generated_values": False,
            "observed_location": {
                "latitude": snapshot["gps_latitude"],
                "longitude": snapshot["gps_longitude"],
                "accuracy_m": snapshot["gps_accuracy_m"],
            },
            "nearest_reference": nearest,
            "verified_address": None,
            "claim_scope": "GPS coordinate with provider accuracy; no address verification",
            "source_id": snapshot["gps_source_id"],
            "source_event_id": snapshot["gps_source_event_id"],
            "source_timestamp": snapshot["gps_source_timestamp"],
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }


if __name__ == "__main__":
    raise SystemExit("FRESH_GPS_PROVIDER_OBSERVATION_REQUIRED")
