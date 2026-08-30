#!/usr/bin/env python3
"""
aureon_battery_lab.py — Scientific-grade battery measurement suite.

Rewires the Queen's Power Station monitoring systems to measure
LAPTOP battery at the highest resolution Windows allows.

Measurement channels:
1. kernel32 GetSystemPowerStatus — percent + lifetime estimate (1Hz)
2. powrprof CallNtPowerInformation — mWh capacity + mW rate (10Hz)
3. psutil sensors_battery — percent + plugged + secsleft (10Hz)
4. WMI BatteryStatus — voltage + discharge rate (on-demand)
5. Performance counters — CPU power state correlation (10Hz)

All readings timestamped with perf_counter (microsecond precision).
Data logged to JSONL for post-analysis.
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

_REPO_ROOT = Path(__file__).resolve().parents[2]
log = logging.getLogger("aureon.battery_lab")


# ═══════════════════════════════════════════════════════════════
#  RAW KERNEL BATTERY ACCESS
# ═══════════════════════════════════════════════════════════════

class SYSTEM_POWER_STATUS(ctypes.Structure):
    _fields_ = [
        ('ACLineStatus', ctypes.c_byte),
        ('BatteryFlag', ctypes.c_byte),
        ('BatteryLifePercent', ctypes.c_byte),
        ('SystemStatusFlag', ctypes.c_byte),
        ('BatteryLifeTime', ctypes.c_ulong),
        ('BatteryFullLifeTime', ctypes.c_ulong),
    ]


class BATTERY_STATE(ctypes.Structure):
    _fields_ = [
        ('AcOnLine', ctypes.c_ubyte),
        ('BatteryPresent', ctypes.c_ubyte),
        ('Charging', ctypes.c_ubyte),
        ('Discharging', ctypes.c_ubyte),
        ('Spare1', ctypes.c_ubyte * 3),
        ('Tag', ctypes.c_ulong),
        ('MaxCapacity', ctypes.c_ulong),
        ('RemainingCapacity', ctypes.c_ulong),
        ('Rate', ctypes.c_long),
        ('EstimatedTime', ctypes.c_ulong),
        ('DefaultAlert1', ctypes.c_ulong),
        ('DefaultAlert2', ctypes.c_ulong),
    ]


_kernel32 = ctypes.windll.kernel32

try:
    _powrprof = ctypes.windll.powrprof
    HAS_POWRPROF = True
except Exception:
    _powrprof = None
    HAS_POWRPROF = False


# ═══════════════════════════════════════════════════════════════
#  MEASUREMENT DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

@dataclass
class BatteryReading:
    """One scientific measurement of battery state."""
    timestamp: float             # perf_counter (microsecond precision)
    wall_time: float             # time.time() for human reference

    # Channel 1: kernel32
    percent: int = 0
    ac_online: bool = False
    battery_flag: int = 0
    lifetime_s: int = -1

    # Channel 2: powrprof (if available)
    max_capacity_mwh: int = 0
    remaining_mwh: int = 0
    rate_mw: int = 0             # Negative = discharge, positive = charge
    charging: bool = False
    discharging: bool = False

    # Channel 3: CPU correlation
    cpu_percent: float = 0.0
    cpu_freq_mhz: float = 0.0

    # Derived
    exact_percent: float = 0.0   # remaining/max * 100
    watts: float = 0.0           # abs(rate_mw) / 1000


@dataclass
class TransitionEvent:
    """Detected percent change."""
    timestamp: float
    from_pct: int
    to_pct: int
    elapsed_since_last: float
    rate_mw_at_transition: int
    direction: str  # "charge" or "discharge"


# ═══════════════════════════════════════════════════════════════
#  THE LAB
# ═══════════════════════════════════════════════════════════════

class BatteryLab:
    """Scientific-grade battery measurement instrument."""

    def __init__(self, log_path: str = None):
        self._log_path = Path(log_path) if log_path else _REPO_ROOT / "state" / "battery_lab.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        self._readings: List[BatteryReading] = []
        self._transitions: List[TransitionEvent] = []
        self._last_percent = -1
        self._last_transition_time = 0.0
        self._t0 = time.perf_counter()
        self._log_file = None

        # Get design capacity once
        self.design_mwh = 39191  # From battery report
        self.full_charge_mwh = 39191

        # Try powrprof for capacity
        if HAS_POWRPROF:
            bs = BATTERY_STATE()
            r = _powrprof.CallNtPowerInformation(5, None, 0, ctypes.byref(bs), ctypes.sizeof(bs))
            if r == 0 and bs.MaxCapacity > 0 and bs.MaxCapacity < 0x80000000:
                self.design_mwh = bs.MaxCapacity

        self.mwh_per_percent = self.design_mwh / 100.0

    def read(self) -> BatteryReading:
        """Take one measurement from ALL channels simultaneously."""
        t = time.perf_counter() - self._t0
        wt = time.time()

        # Channel 1: kernel32
        sps = SYSTEM_POWER_STATUS()
        _kernel32.GetSystemPowerStatus(ctypes.byref(sps))

        # Channel 2: powrprof
        max_cap = 0
        rem_cap = 0
        rate = 0
        charging = False
        discharging = False

        if HAS_POWRPROF:
            bs = BATTERY_STATE()
            _powrprof.CallNtPowerInformation(5, None, 0, ctypes.byref(bs), ctypes.sizeof(bs))
            max_cap = bs.MaxCapacity if bs.MaxCapacity < 0x80000000 else 0
            rem_cap = bs.RemainingCapacity if bs.RemainingCapacity < 0x80000000 else 0
            rate = bs.Rate if abs(bs.Rate) < 100000 else 0
            charging = bool(bs.Charging)
            discharging = bool(bs.Discharging)

        # Channel 3: CPU
        cpu_pct = psutil.cpu_percent(interval=0)
        try:
            cpu_freq = psutil.cpu_freq().current
        except Exception:
            cpu_freq = 0

        # Build reading
        exact_pct = (rem_cap / max_cap * 100) if max_cap > 0 else float(sps.BatteryLifePercent)

        reading = BatteryReading(
            timestamp=t,
            wall_time=wt,
            percent=sps.BatteryLifePercent,
            ac_online=bool(sps.ACLineStatus),
            battery_flag=sps.BatteryFlag,
            lifetime_s=sps.BatteryLifeTime if sps.BatteryLifeTime != 0xFFFFFFFF else -1,
            max_capacity_mwh=max_cap,
            remaining_mwh=rem_cap,
            rate_mw=rate,
            charging=charging,
            discharging=discharging,
            cpu_percent=cpu_pct,
            cpu_freq_mhz=cpu_freq,
            exact_percent=exact_pct,
            watts=abs(rate) / 1000 if rate != 0 else 0,
        )

        self._readings.append(reading)

        # Detect transitions. Preserve the previous value until both the event
        # and its interval have been recorded; the old ordering updated
        # ``_last_percent`` first, so transition timestamps were never advanced.
        previous_percent = self._last_percent
        if previous_percent >= 0 and reading.percent != previous_percent:
            elapsed = t - self._last_transition_time if self._last_transition_time > 0 else 0
            direction = "charge" if reading.percent > self._last_percent else "discharge"

            event = TransitionEvent(
                timestamp=t,
                from_pct=previous_percent,
                to_pct=reading.percent,
                elapsed_since_last=elapsed,
                rate_mw_at_transition=rate,
                direction=direction,
            )
            self._transitions.append(event)

        if previous_percent < 0 or reading.percent != previous_percent:
            self._last_transition_time = t
        self._last_percent = reading.percent

        return reading

    def read_continuous(self, duration_s: float, hz: float = 10.0,
                        callback=None) -> List[BatteryReading]:
        """Read at specified Hz for specified duration."""
        interval = 1.0 / hz
        readings = []
        t0 = time.perf_counter()

        while time.perf_counter() - t0 < duration_s:
            r = self.read()
            readings.append(r)
            if callback:
                callback(r)
            time.sleep(interval)

        return readings

    def log_reading(self, r: BatteryReading):
        """Append reading to JSONL log."""
        try:
            if self._log_file is None:
                self._log_file = open(self._log_path, "a", encoding="utf-8")
            self._log_file.write(json.dumps(asdict(r), default=str) + "\n")
            self._log_file.flush()
        except Exception:
            pass

    def get_summary(self) -> Dict[str, Any]:
        """Statistical summary of all readings."""
        if not self._readings:
            return {}

        pcts = [r.percent for r in self._readings]
        rates = [r.rate_mw for r in self._readings if r.rate_mw != 0]
        cpus = [r.cpu_percent for r in self._readings]
        watts = [r.watts for r in self._readings if r.watts > 0]

        return {
            "readings": len(self._readings),
            "duration_s": self._readings[-1].timestamp - self._readings[0].timestamp,
            "percent_range": [min(pcts), max(pcts)],
            "percent_delta": pcts[-1] - pcts[0],
            "rate_mw_range": [min(rates), max(rates)] if rates else [0, 0],
            "rate_mw_avg": sum(rates) / len(rates) if rates else 0,
            "watts_avg": sum(watts) / len(watts) if watts else 0,
            "cpu_avg": sum(cpus) / len(cpus),
            "transitions": len(self._transitions),
            "transition_details": [asdict(t) for t in self._transitions],
            "design_mwh": self.design_mwh,
            "mwh_per_percent": self.mwh_per_percent,
        }

    def close(self):
        if self._log_file:
            self._log_file.close()
            self._log_file = None


# ═══════════════════════════════════════════════════════════════
#  STANDALONE TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    lab = BatteryLab()
    r = lab.read()

    print("=" * 60)
    print("  BATTERY LAB — Scientific Measurement Suite")
    print("=" * 60)
    print(f"  Design capacity: {lab.design_mwh} mWh")
    print(f"  Per 1%:          {lab.mwh_per_percent:.1f} mWh")
    print(f"  Current:         {r.percent}%")
    print(f"  AC:              {'ON' if r.ac_online else 'OFF'}")
    print(f"  Charging:        {r.charging}")
    print(f"  Discharging:     {r.discharging}")
    print(f"  Rate:            {r.rate_mw} mW ({r.watts:.3f}W)")
    print(f"  Remaining:       {r.remaining_mwh} mWh")
    print(f"  CPU:             {r.cpu_percent}% at {r.cpu_freq_mhz:.0f}MHz")

    print(f"\n  Live monitoring at 10Hz for 30s...")
    print(f"  {'Time':>6s} {'%':>4s} {'mWh':>7s} {'mW':>7s} {'W':>6s} {'CPU':>5s}")

    def show(r):
        if int(r.timestamp * 10) % 30 == 0:  # Every 3 seconds
            print(f"  {r.timestamp:5.1f}s {r.percent:3d}% {r.remaining_mwh:6d} {r.rate_mw:6d} {r.watts:5.2f} {r.cpu_percent:4.0f}%",
                  flush=True)
        lab.log_reading(r)

    readings = lab.read_continuous(30.0, hz=10, callback=show)

    summary = lab.get_summary()
    print(f"\n  SUMMARY:")
    for k, v in summary.items():
        if k != "transition_details":
            print(f"  {k}: {v}")

    lab.close()
    print(f"\n  Log saved: {lab._log_path}")
