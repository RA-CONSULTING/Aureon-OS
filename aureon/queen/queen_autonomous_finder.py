#!/usr/bin/env python3
"""Compatibility finder constrained to observed GPS data.

Brainwaves, Schumann measurements, model state, and mycelium signals cannot
locate a person. The finder therefore reports no_data until a fresh GPS
provider observation is explicitly ingested.
"""

from typing import Any, Dict, Optional

from aureon.utils.aureon_live_aura_location_tracker import LiveAuraLocationTracker


class QueenAutonomousFinder:
    def __init__(self):
        self.tracker = LiveAuraLocationTracker()
        self.is_searching = False

    def start_autonomous_search(self) -> Dict[str, Any]:
        self.tracker.start()
        self.is_searching = True
        return {
            "truth_status": "no_data",
            "generated_values": False,
            "reason": "FRESH_GPS_PROVIDER_OBSERVATION_REQUIRED",
        }

    def ingest_gps_observation(self, observation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.is_searching:
            self.start_autonomous_search()
        self.tracker.update_from_gps(observation)
        return self.get_location_status()

    def get_location_status(self) -> Optional[Dict[str, Any]]:
        snapshot = self.tracker.get_current_location()
        if not snapshot or snapshot.get("gps_latitude") is None:
            return None
        return {
            "position": (snapshot["gps_latitude"], snapshot["gps_longitude"]),
            "accuracy_m": snapshot["gps_accuracy_m"],
            "distance_from_belfast_reference_km": snapshot["distance_from_belfast_km"],
            "truth_status": "real_derived",
            "source_id": snapshot["gps_source_id"],
            "source_event_id": snapshot["gps_source_event_id"],
            "source_timestamp": snapshot["gps_source_timestamp"],
            "generated_values": False,
            "claim_scope": "observed GPS coordinate and geometric distance only",
        }

    def stop_search(self) -> None:
        self.is_searching = False
        self.tracker.stop()


if __name__ == "__main__":
    raise SystemExit("FRESH_GPS_PROVIDER_OBSERVATION_REQUIRED")
