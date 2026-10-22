#!/usr/bin/env python3
"""
SAFE GLI — Launch Validation Plotter

Reads a Launch Validation JSON (the executive summary you provided),
reconstructs a piecewise-constant-acceleration profile per tier,
and renders engineering charts:
  1) Velocity vs Time
  2) Acceleration vs Time
  3) Instantaneous Input Power vs Time (from F·v / efficiency)
  4) Cumulative Input Energy vs Time

It also prints a validation summary comparing computed values against the JSON targets.

Usage:
  python3 safe_gli_validation_charts.py --json SAFE_GLI_LAUNCH_VALIDATION_2025-10-22.json --outdir out --mass_tons 111 --eff 0.952

Notes:
- We assume per-tier external acceleration is constant and equals the JSON 'accel_external_g'.
- Velocity is integrated piecewise with continuity at tier boundaries.
- Input power uses P_in = (m * a * v) / efficiency.
- If the JSON omits some fields, reasonable defaults are used.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np

G0 = 9.80665  # m/s^2


@dataclass
class Tier:
    name: str
    duration_s: float
    accel_g: float
    exit_velocity_kms: float


def load_report(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def tiers_from_report(rep: Dict[str, Any]) -> List[Tier]:
    tiers: List[Tier] = []
    for t in rep.get("tier_sequence", []):
        tiers.append(
            Tier(
                name=t.get("name", f"Tier {t.get('tier', '?')}").strip(),
                duration_s=float(t["duration_s"]),
                accel_g=float(t["accel_external_g"]),
                exit_velocity_kms=float(t["exit_velocity_kms"]),
            )
        )
    return tiers


def build_profile(tiers: List[Tier], mass_kg: float, eff: float, dt: float = 1e-3) -> Dict[str, Any]:
    """Return dict with time, velocity, acceleration, input power, energy and position arrays."""

    t_list: List[np.ndarray] = []
    v_list: List[np.ndarray] = []
    a_list: List[np.ndarray] = []
    p_in_list: List[np.ndarray] = []
    x_list: List[np.ndarray] = []

    t0 = 0.0
    v0 = 0.0
    x0 = 0.0
    markers: List[Tuple[float, str]] = []

    for tier in tiers:
        a = tier.accel_g * G0

        # Store the start-of-tier state for integration and continuity
        v_start = v0
        x_start = x0

        # Sample the tier timeline at ~dt resolution and ensure the boundary is included
        t_offsets = np.arange(0.0, tier.duration_s, dt)
        if t_offsets.size == 0 or not math.isclose(
            t_offsets[-1], tier.duration_s, rel_tol=1e-12, abs_tol=1e-15
        ):
            t_offsets = np.append(t_offsets, tier.duration_s)

        v_seg = v_start + a * t_offsets
        x_seg = x_start + v_start * t_offsets + 0.5 * a * t_offsets**2
        p_in_seg = (mass_kg * a * v_seg) / max(1e-9, eff)
        a_seg = np.full_like(t_offsets, a)

        if t_list:
            # Skip the boundary sample already recorded from the prior tier
            t_list.append(t0 + t_offsets[1:])
            v_list.append(v_seg[1:])
            a_list.append(a_seg[1:])
            p_in_list.append(p_in_seg[1:])
            x_list.append(x_seg[1:])
        else:
            t_list.append(t0 + t_offsets)
            v_list.append(v_seg)
            a_list.append(a_seg)
            p_in_list.append(p_in_seg)
            x_list.append(x_seg)

        # Advance the state to the tier boundary for the next iteration
        t0 += tier.duration_s
        v0 = v_start + a * tier.duration_s
        x0 = x_start + v_start * tier.duration_s + 0.5 * a * tier.duration_s**2
        markers.append((t0, tier.name))

    if not t_list:
        raise ValueError("No time samples generated for the profile.")

    t = np.concatenate(t_list)
    v = np.concatenate(v_list)
    a_arr = np.concatenate(a_list)
    p_in = np.concatenate(p_in_list)
    x = np.concatenate(x_list)

    dt_arr = np.empty_like(t)
    dt_arr[0] = 0.0
    dt_arr[1:] = np.diff(t)
    e_in = np.cumsum(p_in * dt_arr)

    return {
        "t": t,
        "v": v,
        "a": a_arr,
        "p_in": p_in,
        "e_in": e_in,
        "x": x,
        "markers": markers,
        "total_time": t0,
        "final_velocity": v0,
        "total_distance": x0,
    }


def plot_series(t: np.ndarray, y: np.ndarray, ylabel: str, title: str, out: Path) -> None:
    plt.figure(figsize=(10, 5))
    plt.plot(t, y, linewidth=2)
    plt.xlabel("Time (s)")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out, dpi=160)
    plt.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="SAFE GLI Launch Validation Plotter")
    ap.add_argument("--json", required=True, help="Path to Launch Validation JSON")
    ap.add_argument("--outdir", default="safe_gli_out", help="Output directory for charts")
    ap.add_argument("--mass_tons", type=float, default=111.0, help="Payload mass in metric tons")
    ap.add_argument(
        "--eff",
        type=float,
        default=0.952,
        help="Overall input→mechanical efficiency (0..1)",
    )
    ap.add_argument("--dt", type=float, default=1e-3, help="Time step in seconds for reconstruction")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rep = load_report(Path(args.json))
    tiers = tiers_from_report(rep)
    if not tiers:
        raise SystemExit("No tiers found in JSON tier_sequence.")

    mass_kg = args.mass_tons * 1000.0
    profile = build_profile(tiers, mass_kg=mass_kg, eff=args.eff, dt=args.dt)

    t = profile["t"]
    v = profile["v"]
    a = profile["a"]
    p_in = profile["p_in"]
    e_in = profile["e_in"]

    # Derived checks
    v_final = profile["final_velocity"]
    t_total = profile["total_time"]
    e_total = e_in[-1]
    x_total = profile["total_distance"]

    targets = {m["metric"]: m for m in rep.get("validation_metrics", [])}

    lines = []
    lines.append("SAFE GLI — Validation Reconstruction Summary")
    lines.append(
        f"Report: {rep.get('report_id', '(unknown)')}  |  Site: {rep.get('location', {}).get('site', '?')}"
    )
    lines.append(f"Payload mass: {mass_kg:,.0f} kg  |  Efficiency used: {args.eff:.3f}")
    lines.append("")
    lines.append(
        "Final velocity (calc): "
        f"{v_final / 1000:.3f} km/s  | Target: {targets.get('Final Velocity', {}).get('target', '?')}"
    )
    lines.append(
        f"Total time (calc): {t_total:.3f} s  | Target: {targets.get('Total Launch Duration', {}).get('target', '?')}"
    )
    lines.append(
        "Total track length (approx, kinematic): "
        f"{x_total / 1000:.3f} km  | Target: {targets.get('Total Track Length', {}).get('target', '?')}"
    )
    lines.append(
        "Total input energy (calc): "
        f"{e_total / 1e12:.3f} TJ  | Target: {targets.get('Total Energy Input', {}).get('simulated', '?')}"
    )

    ke = 0.5 * mass_kg * v_final**2
    eff_apparent = ke / max(1e-9, e_total)
    lines.append(
        f"Final kinetic energy: {ke / 1e12:.3f} TJ  |  Apparent efficiency KE/E_in: {eff_apparent * 100:.1f}%"
    )

    (outdir / "summary.txt").write_text("\n".join(lines), encoding="utf-8")

    plot_series(t, v / 1000.0, "Velocity (km/s)", "Velocity vs Time", outdir / "velocity_vs_time.png")
    plot_series(t, a / G0, "Acceleration (g)", "Acceleration vs Time", outdir / "acceleration_vs_time.png")
    plot_series(
        t,
        p_in / 1e12,
        "Input Power (TW)",
        "Input Power vs Time",
        outdir / "power_vs_time.png",
    )
    plot_series(
        t,
        e_in / 1e12,
        "Cumulative Energy (TJ)",
        "Cumulative Input Energy vs Time",
        outdir / "energy_vs_time.png",
    )

    with open(outdir / "tier_markers.txt", "w", encoding="utf-8") as f:
        for t_end, name in profile["markers"]:
            f.write(f"{t_end:.3f}s : {name}\n")

    print("\n".join(lines))
    print(f"\nCharts saved under: {outdir.resolve()}\n")


if __name__ == "__main__":
    main()
