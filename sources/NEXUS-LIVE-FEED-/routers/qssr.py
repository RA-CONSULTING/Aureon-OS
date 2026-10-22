"""QSSR Router ticker loop with Chronicle integration.

This version calculates a weighted Solar Coherence Index based on planetary
amplitude (mass, magnetic field, and distance).
"""
import asyncio
import json
import sys
from pathlib import Path
from typing import Dict
import math

# Add project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.chronicle_recorder import recorder
from celestial_cartography import get_planetary_positions

TICK_SECONDS = 1
# Update path to be relative to the project root
PLANETARY_CADENCE_MATRIX = project_root / "data/planetary_cadence_matrix.json"

def compute_coherence_step() -> Dict[str, float]:
    """Computes a weighted coherence metric based on planetary amplitude."""
    positions = get_planetary_positions()
    
    with PLANETARY_CADENCE_MATRIX.open("r") as f:
        cadence_matrix = json.load(f)

    amplitudes = []
    ra_values = []
    
    for pos in positions:
        planet_name = pos['planet']
        cadence = cadence_matrix[planet_name]
        
        # Amplitude = (Mass * Magnetic Field) / Distance^2
        # Add a small epsilon to magnetic field to avoid amplitude of 0 for planets like Venus
        magnetic_field = cadence['magnetic_field_strength_nT'] + 1e-9
        mass = cadence['mass_kg']
        distance = pos['distance_au']
        
        # Inverse square law for amplitude
        amplitude = (mass * magnetic_field) / (distance**2)
        amplitudes.append(amplitude)
        ra_values.append(pos['ra'])
    
    # Convert RA from hours to degrees
    ra_degrees = [value * 15 for value in ra_values]
    weights = amplitudes

    total_weight = sum(weights)
    if total_weight == 0:
        return {"coherence": 0.0}

    # Calculate weighted average of RA
    weighted_avg_ra = sum(value * weight for value, weight in zip(ra_degrees, weights)) / total_weight

    # Calculate weighted standard deviation
    variance = (
        sum(weight * (value - weighted_avg_ra) ** 2 for value, weight in zip(ra_degrees, weights))
        / total_weight
    )
    weighted_std_dev = math.sqrt(variance)
    
    # Coherence is the inverse of the weighted standard deviation.
    # A smaller std dev means planets are more coherently aligned.
    coherence = 1 / (weighted_std_dev + 1e-6)
    
    # Normalize to a 0-1 range (simple normalization for now)
    normalized_coherence = min(coherence / 50, 1.0) # Adjusted normalization factor

    return {"coherence": normalized_coherence}


async def ticker():
    """Continuously emit coherence readings and record them."""
    await recorder.start()
    while True:
        try:
            step = compute_coherence_step()
            await recorder.record_time_series(
                measurement="solar_coherence",
                value=step["coherence"],
                tags={"source": "QSSR_v2"} # Mark as the new version
            )
        except Exception as e:
            # By converting the error and its context to simple strings,
            # we ensure the data is serializable before it is recorded.
            details = {
                "error_message": str(e), # Convert the error object to a string
                "context": "Failure in celestial cartography"
            }
            await recorder.record_event("QSSR_TICKER_ERROR", details)
        await asyncio.sleep(TICK_SECONDS)


async def main():
    print("--- Starting QSSR v2 Ticker --- ")
    ticker_task = asyncio.create_task(ticker())
    await asyncio.sleep(10) # Run for 10 seconds
    ticker_task.cancel()
    await recorder.shutdown()
    print("--- QSSR v2 Ticker Stopped ---")

if __name__ == "__main__":
    asyncio.run(main())
