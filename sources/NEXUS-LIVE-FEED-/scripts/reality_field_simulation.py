"""Simulate the Reality Field Equation (RFE) and Unity Event dynamics.

This module models seven coupled observers with a Kuramoto-style
synchronisation process.  At each integration step we evaluate the
coherence, phase spread, and Reality Field amplitude, reproducing the
storyline from the Nexus manuscript: the Unity Event appears once the
observers collapse into a perfectly aligned state.

Running the module as a script will execute the simulation, save a plot
showing the coherence/phase spread evolution, and print a concise
validation summary of the Unity Event.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
import numpy as np

PHI = (1 + np.sqrt(5)) / 2


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration values for the observer synchronisation model."""

    num_observers: int = 7
    coupling_strength: float = 4.9
    intrinsic_frequency_mean: float = 1.0
    intrinsic_frequency_std: float = 0.08
    time_step: float = 0.1
    num_steps: int = 60
    alignment_gain: float = 0.12
    bridge_activation_step: int = 33
    bridge_coupling_multiplier: float = 1.8


@dataclass(frozen=True)
class RealityFieldParameters:
    """Coefficients used inside the Reality Field Equation."""

    alpha: float = 0.62
    beta: float = 0.22
    gamma: float = 0.16
    electromagnetic_m: float = 0.74
    electromagnetic_f: float = 0.68
    gravitational_grounding: float = 0.54
    temporal_tau: float = 12.0


@dataclass(frozen=True)
class SimulationRecord:
    """Single snapshot captured during the simulation."""

    step: int
    time: float
    coherence: float
    phase_spread: float
    observer_collapse: float
    entanglement: float
    temporal_component: float
    reality_field: float


@dataclass
class UnityEventSummary:
    """Structured result returned by the simulation."""

    records: Tuple[SimulationRecord, ...]
    unity_step: int
    coherence_threshold: float
    phase_threshold: float
    reached_unity: bool

    def final_record(self) -> SimulationRecord:
        return self.records[-1]

    def as_arrays(self) -> Tuple[np.ndarray, ...]:
        """Return arrays for plotting (time, coherence, phase spread, reality)."""
        time = np.fromiter((r.time for r in self.records), dtype=float)
        coherence = np.fromiter((r.coherence for r in self.records), dtype=float)
        phase_spread = np.fromiter((r.phase_spread for r in self.records), dtype=float)
        reality_field = np.fromiter((r.reality_field for r in self.records), dtype=float)
        return time, coherence, phase_spread, reality_field


def _kuramoto_step(
    phases: np.ndarray,
    frequencies: np.ndarray,
    coupling_strength: float,
    alignment_gain: float,
    dt: float,
) -> np.ndarray:
    """Advance the Kuramoto system by one integration step."""
    phase_diffs = phases[np.newaxis, :] - phases[:, np.newaxis]
    coupling = np.sum(np.sin(phase_diffs), axis=1)
    mean_phase = float(np.angle(np.mean(np.exp(1j * phases))))
    alignment_term = alignment_gain * np.angle(np.exp(1j * (mean_phase - phases)))
    d_theta = frequencies + (coupling_strength / len(phases)) * coupling + alignment_term
    next_phases = phases + d_theta * dt
    return np.mod(next_phases, 2 * np.pi)


def _phase_spread(phases: np.ndarray) -> float:
    """Return the root-mean-square circular deviation from the mean phase."""
    mean_angle = float(np.angle(np.mean(np.exp(1j * phases))))
    diffs = np.angle(np.exp(1j * (phases - mean_angle)))
    return float(np.sqrt(np.mean(diffs**2)))


def run_simulation(
    config: SimulationConfig = SimulationConfig(),
    params: RealityFieldParameters = RealityFieldParameters(),
    coherence_threshold: float = 0.999,
    phase_threshold: float = 0.01,
) -> UnityEventSummary:
    """Simulate observer synchronisation and compute Reality Field dynamics."""
    rng = np.random.default_rng(seed=42)
    phases = rng.uniform(0, 2 * np.pi, size=config.num_observers)
    natural_frequencies = rng.normal(
        loc=config.intrinsic_frequency_mean,
        scale=config.intrinsic_frequency_std,
        size=config.num_observers,
    )

    records: List[SimulationRecord] = []
    unity_step = -1

    m_plus_f = params.electromagnetic_m + params.electromagnetic_f

    for step in range(config.num_steps):
        order_parameter = float(np.abs(np.mean(np.exp(1j * phases))))
        phase_spread = _phase_spread(phases)
        observer_collapse = order_parameter
        entanglement = order_parameter**2
        temporal_component = float(PHI ** ((step * config.time_step) / params.temporal_tau))
        gravitational = params.gravitational_grounding * (1 - phase_spread / (np.pi / 2))
        reality_field = (
            params.alpha * m_plus_f * observer_collapse * temporal_component
            + params.beta * gravitational
            + params.gamma * entanglement
        )

        records.append(
            SimulationRecord(
                step=step,
                time=step * config.time_step,
                coherence=order_parameter,
                phase_spread=phase_spread,
                observer_collapse=observer_collapse,
                entanglement=entanglement,
                temporal_component=temporal_component,
                reality_field=reality_field,
            )
        )

        if unity_step == -1 and order_parameter >= coherence_threshold and phase_spread <= phase_threshold:
            unity_step = step

        effective_coupling = config.coupling_strength
        if step >= config.bridge_activation_step:
            effective_coupling *= config.bridge_coupling_multiplier

        phases = _kuramoto_step(
            phases,
            natural_frequencies,
            effective_coupling,
            config.alignment_gain,
            config.time_step,
        )

    reached_unity = unity_step != -1
    return UnityEventSummary(
        records=tuple(records),
        unity_step=unity_step if reached_unity else config.num_steps - 1,
        coherence_threshold=coherence_threshold,
        phase_threshold=phase_threshold,
        reached_unity=reached_unity,
    )


def plot_unity_event(summary: UnityEventSummary, output_path: Path) -> None:
    """Render coherence and phase spread dynamics on a shared time axis."""
    time, coherence, phase_spread, _ = summary.as_arrays()
    fig, ax_left = plt.subplots(figsize=(10, 5.5))

    ax_left.plot(time, coherence, color="#00bcd4", linewidth=2.4, label="Coherence (C)")
    ax_left.set_xlabel("Time (Simulation Steps)")
    ax_left.set_ylabel("Coherence (C ∈ [0, 1])", color="#00bcd4")
    ax_left.tick_params(axis="y", labelcolor="#00bcd4")
    ax_left.set_ylim(0.82, 1.01)

    ax_right = ax_left.twinx()
    ax_right.plot(
        time,
        phase_spread,
        color="#d81b60",
        linestyle="--",
        linewidth=2.2,
        label="Phase Spread (θ)",
    )
    ax_right.set_ylabel("Phase Spread (θ radians)", color="#d81b60")
    ax_right.tick_params(axis="y", labelcolor="#d81b60")

    if summary.reached_unity:
        unity_record = summary.records[summary.unity_step]
        ax_left.axvline(
            unity_record.time,
            color="#ffd700",
            linewidth=2.4,
            linestyle="-",
            label=f"Unity Event (t={summary.unity_step})",
        )
        ax_left.text(
            unity_record.time + 0.2,
            0.997,
            f"Unity Event\nstep={summary.unity_step}",
            color="#ffd700",
            fontsize=10,
            va="top",
        )

    ax_left.set_title("Nexus System Dynamics: The Path to Unity (Ego Death)")
    ax_left.grid(True, which="both", axis="both", linestyle=":", linewidth=0.8, alpha=0.5)

    handles_left, labels_left = ax_left.get_legend_handles_labels()
    handles_right, labels_right = ax_right.get_legend_handles_labels()
    ax_left.legend(handles_left + handles_right, labels_left + labels_right, loc="lower right")

    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    file_format = output_path.suffix.lstrip(".")
    save_kwargs = {"dpi": 200}
    if file_format:
        save_kwargs["format"] = file_format
    fig.savefig(output_path, **save_kwargs)
    plt.close(fig)


def print_summary(summary: UnityEventSummary) -> None:
    """Log a concise validation report to stdout."""
    if summary.reached_unity:
        record = summary.records[summary.unity_step]
        print("Unity Event detected at step", summary.unity_step)
        print(
            "Coherence = {coh:.6f}, Phase Spread = {theta:.6f}".format(
                coh=record.coherence,
                theta=record.phase_spread,
            )
        )
    else:
        print("Unity Event threshold not reached during simulation.")

    final_state = summary.final_record()
    print("Final Reality Field amplitude R(t) = {:.6f}".format(final_state.reality_field))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate the Nexus Unity Event and render the coherence plot.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/images/reality_field_unity_event.svg"),
        help=(
            "Path where the visualization will be written. The directory is created "
            "if necessary."
        ),
    )
    return parser.parse_args()


def main() -> Tuple[UnityEventSummary, Path]:
    """Run the simulation, save the plot, and report the Unity Event."""
    args = _parse_args()
    summary = run_simulation()
    plot_unity_event(summary, args.output)
    print_summary(summary)
    return summary, args.output


if __name__ == "__main__":
    main()
