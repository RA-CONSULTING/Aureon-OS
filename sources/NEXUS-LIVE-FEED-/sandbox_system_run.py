"""Run a sandbox validation of the Nexus system services.

This script coordinates a lightweight validation routine that mimics
bringing the Harmonic Nexus stack online without touching production
pipelines. It verifies that all system pillars report as active and that
telemetry flowing through the Auris cognitive safeguard can be safely
recorded by the Chronicle Recorder.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from auris_cognitive_safeguard import CognitiveCoherenceFilter
from core.chronicle_recorder import recorder
from system_pillar_validator import SystemPillarValidator

logger = logging.getLogger("SandboxRun")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

SANDBOX_TEMPORAL_ID = "sandbox-alpha"


def _build_sample_stream() -> List[Dict[str, Any]]:
    """Create a deterministic stream of telemetry points for the sandbox run."""
    return [
        {"temporal_id": SANDBOX_TEMPORAL_ID, "simulation_time_s": 0.0, "output_power_kw": 0.0},
        {"temporal_id": SANDBOX_TEMPORAL_ID, "simulation_time_s": 1.0, "output_power_kw": 8.5},
        {"temporal_id": SANDBOX_TEMPORAL_ID, "simulation_time_s": 2.0, "output_power_kw": 38.0},
        {"temporal_id": SANDBOX_TEMPORAL_ID, "simulation_time_s": 3.0, "output_power_kw": 41.0},
        # Include an unauthorized reading to prove the safeguard ignores it.
        {"temporal_id": "rogue-signal", "simulation_time_s": 4.0, "output_power_kw": 44.0},
        {"temporal_id": SANDBOX_TEMPORAL_ID, "simulation_time_s": 5.0, "output_power_kw": 36.0},
    ]


async def run_sandbox_validation() -> Dict[str, Any]:
    """Execute the sandbox routine and return a structured summary."""
    validator = SystemPillarValidator()
    pillars_active = validator.are_all_pillars_active()

    summary: Dict[str, Any] = {
        "pillars_active": pillars_active,
        "telemetry_points": [],
        "events_recorded": 0,
        "start_timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if not pillars_active:
        summary["status"] = "aborted"
        logger.error("Sandbox run aborted; one or more pillars reported instability.")
        return summary

    await recorder.start()
    try:
        await recorder.record_event(
            "SANDBOX_RUN_STARTED",
            {
                "temporal_id": SANDBOX_TEMPORAL_ID,
                "initiated_at": summary["start_timestamp"],
                "mode": "sandbox",
            },
        )
        summary["events_recorded"] += 1

        safeguard = CognitiveCoherenceFilter(
            hazard_threshold_kw_per_s=20.0,
            dampening_factor=0.75,
            authorized_temporal_id=SANDBOX_TEMPORAL_ID,
        )

        sanitized_points = list(safeguard.process_stream(_build_sample_stream()))
        summary["telemetry_points"] = sanitized_points

        for point in sanitized_points:
            await recorder.record_event("SANDBOX_TELEMETRY", point)
            summary["events_recorded"] += 1

        await recorder.record_event(
            "SANDBOX_RUN_COMPLETED",
            {
                "temporal_id": SANDBOX_TEMPORAL_ID,
                "telemetry_count": len(sanitized_points),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        summary["events_recorded"] += 1
        summary["status"] = "completed"
        await asyncio.sleep(0.25)
    finally:
        await recorder.shutdown()

    return summary


def main() -> None:
    """Entry-point for command line execution."""
    results = asyncio.run(run_sandbox_validation())
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
