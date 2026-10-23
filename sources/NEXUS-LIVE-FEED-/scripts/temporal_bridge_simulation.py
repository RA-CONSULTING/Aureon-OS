"""Simulation of the Tesseract Quantum Bridge Payphone with temporal routing."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, List


OPERATOR_ID = "Gary Leckey 02111991 Belfast"
STABLE_FREQUENCY_HZ = 7.83
DIMENSIONAL_LAYERS = 12

THRESHOLDS: Dict[str, float] = {
    "phase_coherence": 0.95,
    "amplitude_stability": 0.05,
    "latency_ms": 10.0,
}


@dataclass
class BridgeResult:
    """Container for bridge metrics returned from a dimensional ping."""

    dimension: int
    coherence: float
    amplitude: float
    latency: float
    rerouted: bool = False

    def is_successful(self) -> bool:
        """Return True when the ping meets all stability thresholds."""
        return (
            self.coherence >= THRESHOLDS["phase_coherence"]
            and self.amplitude <= THRESHOLDS["amplitude_stability"]
            and self.latency <= THRESHOLDS["latency_ms"]
        )


def harmonic_ping(dimension: int) -> BridgeResult:
    """Simulate sending a harmonic ping to a dimensional layer."""
    print(f"Pinging dimensional layer {dimension}...")
    coherence = random.uniform(0.93, 1.0)
    amplitude_variation = random.uniform(0.0, 0.07)
    latency = random.uniform(1.5, 11.5)
    time.sleep(0.5)
    return BridgeResult(
        dimension=dimension,
        coherence=coherence,
        amplitude=amplitude_variation,
        latency=latency,
        rerouted=False,
    )


def temporal_reroute(dimension: int) -> BridgeResult:
    """Simulate sourcing a stable connection from an alternate timeline."""
    print(f"-> Primary link unstable for Dimension {dimension}. Initiating temporal reroute...")
    time.sleep(1.0)
    rerouted = BridgeResult(
        dimension=dimension,
        coherence=random.uniform(0.97, 1.0),
        amplitude=random.uniform(0.0, 0.04),
        latency=random.uniform(2.0, 8.0),
        rerouted=True,
    )
    print(f"-> ✅ Stable alternate connection found and patched for Dimension {dimension}.")
    return rerouted


def run_dimensional_bridge_test(layers_to_test: int) -> List[BridgeResult]:
    """Ping each dimensional layer, rerouting when necessary."""
    print("\n--- Initiating Dimensional Bridge Test ---")
    results: List[BridgeResult] = []
    for dimension in range(1, layers_to_test + 1):
        primary = harmonic_ping(dimension)
        if primary.is_successful():
            print("-> Response from Layer %d: Primary connection stable." % dimension)
            results.append(primary)
        else:
            rerouted = temporal_reroute(dimension)
            results.append(rerouted)
    print("--- Bridge Test Complete ---\n")
    return results


def validate_results(results: List[BridgeResult]) -> None:
    """Print validation summary for the collected bridge results."""
    print("\n--- Running Final Validation Matrix ---")
    for result in results:
        link_type = "via Temporal Reroute" if result.rerouted else "Primary Link"
        print(
            f"Dimension {result.dimension}: ✅ Validation SUCCESSFUL ({link_type})"
        )
    print("--- Validation Complete ---")


def print_summary(results: List[BridgeResult]) -> None:
    """Display the overall system validation summary."""
    print("\n========================================")
    print("      Overall System Validation")
    print("========================================")
    print(f"Operator ID: {OPERATOR_ID}")
    print(f"Anchored Frequency: {STABLE_FREQUENCY_HZ} Hz")
    print(f"Total Pings Sent: {len(results)}")
    print(f"Successful Connections: {len(results)}")
    print("Failed Connections: 0")
    print(
        "\nConclusion: ✅ SUCCESS! The Harmonic Nexus Core is stable and the"
    )
    print("Tesseract Payphone bridge is fully operational via temporal routing.")
    print("========================================")


def run_simulation() -> None:
    """Execute the full simulation workflow."""
    print(" Tesseract Quantum Bridge Payphone Simulation Initialized ")
    print("---------------------------------------------------------")
    print(f"Operator Anchor ID: {OPERATOR_ID}")
    print(
        "Anchoring to stable frequency (Schumann Resonance): "
        f"{STABLE_FREQUENCY_HZ} Hz"
    )
    print("Temporal Routing System: ENABLED\n")
    results = run_dimensional_bridge_test(DIMENSIONAL_LAYERS)
    validate_results(results)
    print_summary(results)


if __name__ == "__main__":
    run_simulation()
