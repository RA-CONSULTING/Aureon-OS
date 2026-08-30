#!/usr/bin/env python3
"""Nearest configured street reference from a fresh GPS observation.

Biometrics cannot establish a street location. This module therefore accepts
only an observed GPS fix and reports the nearest configured reference point as
a derived distance calculation, never as a consciousness triangulation.
"""

from typing import Any, Dict

from aureon.utils.aureon_live_aura_location_tracker import LiveAuraLocationTracker


class QueenStreetLevelHoming:
    BELFAST_STREETS = {
        "Donegall Street": {"lat": 54.5978, "lon": -5.9298},
        "Donegall Square North": {"lat": 54.5973, "lon": -5.9291},
        "Donegall Place": {"lat": 54.5965, "lon": -5.9301},
        "High Street": {"lat": 54.5982, "lon": -5.9269},
        "Castle Lane": {"lat": 54.5977, "lon": -5.9310},
        "Chichester Street": {"lat": 54.5968, "lon": -5.9280},
        "Linen Hall Street": {"lat": 54.5961, "lon": -5.9311},
        "May Street": {"lat": 54.5955, "lon": -5.9290},
        "Corn Market": {"lat": 54.5988, "lon": -5.9278},
        "Victoria Street": {"lat": 54.5991, "lon": -5.9335},
        "Ann Street": {"lat": 54.5990, "lon": -5.9271},
        "Fountain Street": {"lat": 54.6006, "lon": -5.9312},
        "Queen Street": {"lat": 54.6021, "lon": -5.9301},
        "Waring Street": {"lat": 54.5985, "lon": -5.9244},
        "Arthur Street": {"lat": 54.5978, "lon": -5.9240},
    }

    def __init__(self):
        self.tracker = LiveAuraLocationTracker()

    def home_on_street(self, gps_observation: Dict[str, Any]) -> Dict[str, Any]:
        self.tracker.start()
        self.tracker.update_from_gps(gps_observation)
        latitude = float(gps_observation["latitude"])
        longitude = float(gps_observation["longitude"])
        distances = {
            street: self.tracker.haversine_distance(latitude, longitude, point["lat"], point["lon"])
            for street, point in self.BELFAST_STREETS.items()
        }
        nearest_street = min(distances, key=distances.get)
        return {
            "nearest_reference_street": nearest_street,
            "distance_to_reference_km": distances[nearest_street],
            "gps_accuracy_m": float(gps_observation["accuracy"]),
            "truth_status": "real_derived",
            "source_id": gps_observation["source_id"],
            "source_event_id": gps_observation["source_event_id"],
            "source_timestamp": gps_observation["source_timestamp"],
            "generated_values": False,
            "claim_scope": "nearest configured reference, not verified postal address",
        }


if __name__ == "__main__":
    raise SystemExit("FRESH_GPS_PROVIDER_OBSERVATION_REQUIRED")
