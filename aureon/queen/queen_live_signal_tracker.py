#!/usr/bin/env python3
"""Adapter for live biometric observations; no generated signal stream."""

from copy import deepcopy
from typing import Any, Dict, Optional

from aureon.utils.aureon_live_aura_location_tracker import LiveAuraLocationTracker


class LiveSignalEmitter:
    """Hold the most recent fresh device observation supplied by a connector."""

    def __init__(self):
        self.running = False
        self.current_signals: Optional[Dict[str, Any]] = None

    def start_streaming(self) -> None:
        self.running = True

    def ingest_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        required = {
            "truth_status", "generated_values", "source_id", "source_event_id",
            "source_timestamp", "heart_rate_bpm", "hrv_rmssd", "bands",
            "gsr_uS", "resp_bpm",
        }
        missing = sorted(required - set(observation))
        if missing:
            raise ValueError(f"BIOMETRIC_OBSERVATION_FIELDS_REQUIRED:{','.join(missing)}")
        if observation.get("truth_status") != "live" or observation.get("generated_values") is not False:
            raise ValueError("LIVE_BIOMETRIC_OBSERVATION_REQUIRED")
        self.current_signals = deepcopy(observation)
        return deepcopy(observation)

    def get_live_data(self) -> Dict[str, Any]:
        if self.current_signals is None:
            raise RuntimeError("NO_LIVE_BIOMETRIC_OBSERVATION")
        return deepcopy(self.current_signals)

    def stop_streaming(self) -> None:
        self.running = False


class QueenRealTimeTracker:
    """Process explicit device observations through the real-data tracker."""

    def __init__(self, signal_emitter: LiveSignalEmitter):
        self.tracker = LiveAuraLocationTracker()
        self.emitter = signal_emitter
        self.is_tracking = False

    def start_real_time_tracking(self, duration_seconds: float = 60) -> None:
        del duration_seconds
        self.tracker.start()
        self.is_tracking = True

    def process_observation(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_tracking:
            raise RuntimeError("REAL_TIME_TRACKER_NOT_STARTED")
        live_data = self.emitter.ingest_observation(observation)
        snapshot = self.tracker.update_from_biometric(live_data)
        return snapshot.to_dict()

    def stop_real_time_tracking(self) -> None:
        self.is_tracking = False
        self.tracker.stop()


if __name__ == "__main__":
    raise SystemExit("LIVE_BIOMETRIC_PROVIDER_CONNECTOR_REQUIRED")
