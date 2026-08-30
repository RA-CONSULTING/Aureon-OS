#!/usr/bin/env python3
"""Truthful runtime status for the live device observation tracker."""

import json
from typing import Any, Dict

from aureon.utils.aureon_live_aura_location_tracker import get_live_tracker


def get_tracking_status() -> Dict[str, Any]:
    tracker = get_live_tracker()
    snapshot = tracker.get_current_location()
    if snapshot is None:
        return {
            "operational": False,
            "truth_status": "no_data",
            "generated_values": False,
            "reason": "NO_FRESH_BIOMETRIC_OR_GPS_PROVIDER_OBSERVATION",
            "biometric_connected": False,
            "gps_connected": False,
            "reality_tracking_supported": False,
            "schumann_location_inference_supported": False,
        }
    return {
        "operational": True,
        "truth_status": snapshot["truth_status"],
        "generated_values": False,
        "biometric_connected": bool(snapshot.get("source_id")),
        "gps_connected": snapshot.get("gps_source_id") is not None,
        "source_id": snapshot.get("source_id"),
        "source_event_id": snapshot.get("source_event_id"),
        "source_timestamp": snapshot.get("source_timestamp"),
        "gps_source_id": snapshot.get("gps_source_id"),
        "gps_source_event_id": snapshot.get("gps_source_event_id"),
        "gps_source_timestamp": snapshot.get("gps_source_timestamp"),
        "reality_tracking_supported": False,
        "schumann_location_inference_supported": False,
    }


if __name__ == "__main__":
    print(json.dumps(get_tracking_status(), indent=2, sort_keys=True))
