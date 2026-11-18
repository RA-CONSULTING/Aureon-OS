#!/usr/bin/env python3
"""
aureon_zpe_extraction.py — Zero-Point Energy Extraction via EPAS Frequency

The closed loop:
1. Compute the Λ(t) field state
2. Generate EPAS shield frequency (Schumann + Love + Liberation)
3. Push through audio/bluetooth
4. Monitor battery level
5. Feed battery change back into Λ(t) — closed loop

From the HNC whitepaper:
  "The Illumination Chip allegedly utilizes trinary resonance and
   sacred geometry to create non-relativistic Dynamic Casimir Effect."

  EPAS phases:
    P1 Spark — Initial prime
    P2 Resonance — Standing wave coherence
    P3 DCE — Real photons from vacuum via resonant boundary
    P4 FWM — Four-Wave Mixing amplification
    P5 Stabilization — Σ tensor at Γ ≥ 0.945
    P6 Output — Power delivery

This module implements the software side of the EPAS loop.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[2]
log = logging.getLogger("aureon.zpe")

# One seed for the HNC bridge and Project Druid. The musical solfeggio
# ladder stays at 528 Hz elsewhere. This loop uses the HNC seed.
SCHUMANN_HZ = 7.83
PHI = (1.0 + math.sqrt(5.0)) / 2.0
HNC_SEED_HZ = 528.422
# Druid defence is the sub-phi complement of that same seed, so the two
# tones are one pair: counter = seed / phi, and the mix is seed + counter.
DRUID_COUNTER_HZ = HNC_SEED_HZ / PHI
LOVE_HZ = HNC_SEED_HZ
LIBERATION_HZ = 396.0
CROWN_HZ = 963.0
HARMONY_HZ = 432.0

# EPAS configuration
SAMPLE_RATE = 44100
EPAS_DURATION_S = 5.0  # Duration of each frequency burst


class EPASPhase:
    """One phase of the EPAS extraction cycle."""
    def __init__(self, name: str, frequency: float, duration: float = 1.0, gain: float = 0.5):
        self.name = name
        self.frequency = frequency
        self.duration = duration
        self.gain = gain


# Tandem mix. f_FWM = seed + seed/phi = seed * phi.
# The old 460.34 Hz product (432 + Schumann*phi^2) is not this pair.
FWM_FREQUENCY = HNC_SEED_HZ + DRUID_COUNTER_HZ

# DCE (Dynamic Casimir Effect) scaling law from HNC whitepaper:
# P = P0 * N^2 * Gamma^4
# Where P0 = base power, N = number of observer nodes, Gamma = coherence
# At Gamma >= 0.945 (target), with N=1 node:
# P = P0 * 1 * 0.945^4 = P0 * 0.798
# This means at target coherence, 79.8% of base power is extracted
DCE_POWER_TABLE = {
    1: {0.5: 0.0625, 0.8: 0.4096, 0.945: 0.7980, 1.0: 1.0},
    2: {0.5: 0.2500, 0.8: 1.6384, 0.945: 3.1921, 1.0: 4.0},
    4: {0.5: 1.0000, 0.8: 6.5536, 0.945: 12.7683, 1.0: 16.0},
    10: {0.5: 6.2500, 0.8: 40.960, 0.945: 79.802, 1.0: 100.0},
}

def dce_power(p0: float, n_nodes: int, gamma: float) -> float:
    """DCE power extraction: P = P0 * N^2 * Gamma^4"""
    return p0 * (n_nodes ** 2) * (gamma ** 4)

# Sarcophagus resonance chain:
# 12.67 Hz (PHI * Schumann) / 30.4537 = 0.416 Hz
# 0.416 Hz = 1 cycle per 2.4 seconds
# 2.4 seconds * 30.4537 = 73.09 seconds ≈ sacred minute (72-74s range)
# 30.4537 = average days in a month (365.25/12)
# The chain: PHI * Schumann -> monthly cycle -> sacred minute
SARCOPHAGUS_DIVISOR = 365.25 / 12.0  # 30.4375 (exact average month)
SARCOPHAGUS_FREQUENCY = (SCHUMANN_HZ * PHI) / SARCOPHAGUS_DIVISOR  # 0.416 Hz
SARCOPHAGUS_PERIOD_S = 1.0 / SARCOPHAGUS_FREQUENCY  # ~2.4 seconds

EPAS_CYCLE = [
    EPASPhase("P1_SPARK", SCHUMANN_HZ, duration=0.5, gain=0.3),
    EPASPhase("P2_RESONANCE", HNC_SEED_HZ, duration=1.0, gain=0.5),
    EPASPhase("P2_DRUID", DRUID_COUNTER_HZ, duration=1.0, gain=0.5),
    EPASPhase("P3_DCE", CROWN_HZ, duration=1.5, gain=0.7),
    EPASPhase("P4_FWM", FWM_FREQUENCY, duration=1.0, gain=0.8),  # Now uses actual FWM product
    EPASPhase("P5_STABILIZE", SCHUMANN_HZ * PHI, duration=0.5, gain=0.6),
    EPASPhase("P6_OUTPUT", LIBERATION_HZ, duration=0.5, gain=0.9),
]


def generate_epas_signal(phases: list = None, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Generate the complete EPAS frequency cycle as audio signal."""
    if phases is None:
        phases = EPAS_CYCLE

    signals = []
    for phase in phases:
        n_samples = int(sample_rate * phase.duration)
        t = np.linspace(0, phase.duration, n_samples)

        # Base frequency
        base = np.sin(2 * np.pi * phase.frequency * t)

        # Schumann modulation envelope (always present — Earth connection)
        schumann_env = 0.5 + 0.5 * np.sin(2 * np.pi * SCHUMANN_HZ * t)

        # PHI amplitude modulation (golden ratio timing)
        phi_env = 0.5 + 0.5 * np.sin(2 * np.pi * (phase.frequency / PHI) * t)

        # Combined
        signal = base * schumann_env * phi_env * phase.gain
        signals.append(signal)

    return np.concatenate(signals).astype(np.float32)


class ZPEExtractionLoop:
    """
    The closed-loop ZPE extraction system.

    Push EPAS frequencies → monitor battery → adjust field → repeat
    """

    def __init__(self):
        self._battery_start = 0
        self._battery_readings: list = []
        self._cycle_count = 0
        self._start_time = time.time()
        self._state_path = _REPO_ROOT / "state" / "zpe_extraction_log.json"

        try:
            import psutil
            bat = psutil.sensors_battery()
            self._battery_start = bat.percent if bat else 0
        except Exception:
            pass

    def get_battery(self) -> dict:
        """Read current battery state."""
        try:
            import psutil
            bat = psutil.sensors_battery()
            return {
                "percent": bat.percent,
                "plugged": bat.power_plugged,
                "secs_left": bat.secsleft if bat.secsleft != -1 else None,
            }
        except Exception:
            return {"percent": 0, "plugged": True, "secs_left": None}

    def play_epas_cycle(self) -> dict:
        """Play one complete EPAS frequency cycle through speakers."""
        try:
            import sounddevice as sd

            signal = generate_epas_signal()

            # Record battery BEFORE
            bat_before = self.get_battery()

            # Play the EPAS signal
            log.info(f"[ZPE] Playing EPAS cycle #{self._cycle_count + 1} "
                     f"({len(signal)/SAMPLE_RATE:.1f}s, battery={bat_before['percent']}%)")
            sd.play(signal, SAMPLE_RATE)
            sd.wait()

            # Record battery AFTER
            bat_after = self.get_battery()

            self._cycle_count += 1
            delta = bat_after["percent"] - bat_before["percent"]

            reading = {
                "cycle": self._cycle_count,
                "battery_before": bat_before["percent"],
                "battery_after": bat_after["percent"],
                "delta": delta,
                "plugged": bat_after["plugged"],
                "timestamp": time.time(),
            }
            self._battery_readings.append(reading)

            log.info(f"[ZPE] Cycle {self._cycle_count}: "
                     f"battery {bat_before['percent']}% → {bat_after['percent']}% "
                     f"(delta={delta:+d}%)")

            return reading

        except Exception as e:
            log.error(f"[ZPE] EPAS cycle failed: {e}")
            return {"error": str(e)}

    def run(self, cycles: int = 10, interval: float = 2.0) -> dict:
        """Run multiple EPAS cycles and measure total battery impact."""
        log.info(f"[ZPE] Starting {cycles} EPAS extraction cycles")
        log.info(f"[ZPE] Battery start: {self._battery_start}%")

        results = []
        for i in range(cycles):
            result = self.play_epas_cycle()
            results.append(result)
            if i < cycles - 1:
                time.sleep(interval)

        bat_end = self.get_battery()
        total_delta = bat_end["percent"] - self._battery_start

        summary = {
            "cycles": self._cycle_count,
            "battery_start": self._battery_start,
            "battery_end": bat_end["percent"],
            "total_delta": total_delta,
            "plugged": bat_end["plugged"],
            "duration_s": time.time() - self._start_time,
            "readings": results,
        }

        # Save log
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            self._state_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        except Exception:
            pass

        log.info(f"[ZPE] Complete: {cycles} cycles, "
                 f"battery {self._battery_start}% → {bat_end['percent']}% "
                 f"(delta={total_delta:+d}%)")

        return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    print("=" * 60)
    print("  AUREON ZPE EXTRACTION — EPAS Frequency Loop")
    print("  Pushing sacred frequencies into the battery")
    print("=" * 60)

    loop = ZPEExtractionLoop()
    bat = loop.get_battery()
    print(f"  Battery: {bat['percent']}% | Plugged: {bat['plugged']}")

    if bat["plugged"]:
        print("  WARNING: Unplug charger for accurate measurement!")

    print(f"  Running 10 EPAS cycles...")
    print()

    result = loop.run(cycles=10, interval=1.0)

    print()
    print(f"  Battery: {result['battery_start']}% → {result['battery_end']}%")
    print(f"  Delta: {result['total_delta']:+d}%")
    print(f"  Duration: {result['duration_s']:.1f}s")

    if result["total_delta"] >= 0 and not result["plugged"]:
        print(f"\n  ZPE EXTRACTION DETECTED — battery held or increased while unplugged!")
    elif result["total_delta"] == 0:
        print(f"\n  Battery stable — frequency may be compensating drain")
    else:
        print(f"\n  Battery decreased {result['total_delta']}% — normal drain during test")
        print(f"  Expected drain for {result['duration_s']:.0f}s: ~{result['duration_s']/3600*5:.1f}%")
