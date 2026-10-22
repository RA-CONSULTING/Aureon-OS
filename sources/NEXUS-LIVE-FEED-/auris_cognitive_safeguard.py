"""
Auris Cognitive Safeguard Module
Author: RA Consulting
Date: 2025-09-14

Description:
Prevents cognitive data bleed from temporal wave fluctuations in quantum simulations
by detecting rapid power oscillations and dampening them to a safe threshold.

This version locks processing to an authorized temporal identifier. Data points
with mismatched identifiers are ignored to ensure system integrity.

"""

from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, Optional
import logging
import math

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AurisSafeguard")

# -----------------------------------------------------------------------------
# Configuration & Filter
# -----------------------------------------------------------------------------
@dataclass
class CognitiveCoherenceFilter:
    """Filters simulation data to prevent cognitive hazards."""

    hazard_threshold_kw_per_s: float = 25.0
    dampening_factor: float = 1.0
    authorized_temporal_id: str = field(default="")

    def __post_init__(self) -> None:
        self.previous_power_kw: Optional[float] = None
        self.previous_time_s: Optional[float] = None
        logger.info(
            "Auris Cognitive Safeguard initialized. Threshold=%.2f kW/s, Dampening=%.2f, TemporalID=%s",
            self.hazard_threshold_kw_per_s,
            self.dampening_factor,
            self.authorized_temporal_id,
        )

    def process_stream(self, data_stream: Iterable[Dict[str, float]]) -> Iterator[Dict[str, float]]:
        """Process an iterable of data-point dictionaries, yielding sanitized output."""
        for data_point in data_stream:
            if data_point.get("temporal_id") != self.authorized_temporal_id:
                logger.error(
                    "Unauthorized temporal_id '%s'; data point ignored.",
                    data_point.get("temporal_id"),
                )
                continue

            if "output_power_kw" not in data_point or "simulation_time_s" not in data_point:
                logger.warning("Missing required keys in data point: %s", data_point)
                continue

            current_power_kw = data_point["output_power_kw"]
            current_time_s = data_point["simulation_time_s"]

            if self.previous_time_s is not None and self.previous_power_kw is not None:
                delta_power = current_power_kw - self.previous_power_kw
                delta_time = current_time_s - self.previous_time_s

                if delta_time > 0:
                    temporal_wave = delta_power / delta_time
                    if abs(temporal_wave) > self.hazard_threshold_kw_per_s:
                        logger.warning(
                            "Hazard detected (%.2f kW/s). Dampening engaged.",
                            temporal_wave,
                        )
                        power_direction = math.copysign(1.0, delta_power) if delta_power else 0.0
                        dampened_power = (
                            self.previous_power_kw
                            + self.dampening_factor
                            * self.hazard_threshold_kw_per_s
                            * delta_time
                            * power_direction
                        )
                        data_point["output_power_kw"] = float(round(dampened_power, 4))
                        data_point["is_stable"] = False
                        data_point["cognitive_safeguard_active"] = True

            self.previous_power_kw = data_point["output_power_kw"]
            self.previous_time_s = current_time_s

            data_point.setdefault("cognitive_safeguard_active", False)
            data_point.setdefault("is_stable", True)

            yield data_point

# -----------------------------------------------------------------------------
# Example Usage
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    sample_data = [
        {"temporal_id": "alpha", "output_power_kw": 0.0, "simulation_time_s": 0.0},
        {"temporal_id": "alpha", "output_power_kw": 10.0, "simulation_time_s": 1.0},
        {"temporal_id": "alpha", "output_power_kw": 60.0, "simulation_time_s": 2.0},
        {"temporal_id": "alpha", "output_power_kw": 65.0, "simulation_time_s": 3.0},
        {"temporal_id": "beta", "output_power_kw": 70.0, "simulation_time_s": 4.0},  # unauthorized
    ]

    safeguard = CognitiveCoherenceFilter(
        hazard_threshold_kw_per_s=25.0,
        dampening_factor=1.0,
        authorized_temporal_id="alpha",
    )

    for point in safeguard.process_stream(sample_data):
        logger.info("Sanitized point: %s", point)
