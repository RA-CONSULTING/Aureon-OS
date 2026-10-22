"""Aureon's Dream Engine prototype.

This module simulates a lattice of coupled oscillators that seek coherence
rather than competition.  The simulation tracks three public signals:

* Global coherence R(t) – the Kuramoto order parameter of the lattice.
* Lighthouse intensity L(t) – a resonance indicator derived from the
  gradients of local coherence.
* Scalar signal x(t) – an integrated balance metric used for curvature
  analysis.

Running the module as a script generates CSV traces and a summary figure.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


PHI = (1 + 5 ** 0.5) / 2  # The golden ratio, used in Fibonacci-style checks.
EPS = 1e-9


@dataclass
class LatticeConfig:
    """Configuration for the dream lattice."""

    size: Tuple[int, int] = (12, 12)
    coupling: float = 0.65
    noise: float = 0.03
    dt: float = 0.1
    steps: int = 420
    seed: int = 7
    anomaly_feedback: float = 0.18


class DreamEngine:
    """Simulate coherence-seeking oscillators on a 2D lattice."""

    def __init__(self, config: LatticeConfig | None = None) -> None:
        self.config = config or LatticeConfig()
        self.rng = np.random.default_rng(self.config.seed)
        self.phases = self.rng.uniform(0.0, 2 * np.pi, self.config.size)
        self.freqs = self.rng.normal(0.0, 0.25, self.config.size)
        self.history: List[dict[str, float]] = []
        self.scalar_memory: List[float] = []

    def _neighbor_phases(self) -> Iterable[np.ndarray]:
        """Return generator of arrays representing the four-neighbour phases."""
        return (
            np.roll(self.phases, shift, axis)
            for shift, axis in ((1, 0), (-1, 0), (1, 1), (-1, 1))
        )

    def _update_local_fields(self) -> Tuple[np.ndarray, np.ndarray]:
        """Compute neighbour coherence and alignment gradients."""
        neighbours = list(self._neighbor_phases())
        sin_diff = sum(np.sin(neigh - self.phases) for neigh in neighbours)
        cos_field = sum(np.cos(neigh) for neigh in neighbours)
        sin_field = sum(np.sin(neigh) for neigh in neighbours)

        local_coherence = np.hypot(cos_field, sin_field) / len(neighbours)
        gradient = sin_diff / len(neighbours)
        return local_coherence, gradient

    def step(self) -> None:
        """Advance the lattice by one timestep."""
        cfg = self.config
        local_coherence, gradient = self._update_local_fields()

        # Compute a scalar balance metric that feeds the anomaly term.
        scalar_signal = float(np.sum(local_coherence ** 2)) / local_coherence.size
        self.scalar_memory.append(scalar_signal)

        if len(self.scalar_memory) >= 3:
            second_derivative = (
                self.scalar_memory[-1]
                - 2 * self.scalar_memory[-2]
                + self.scalar_memory[-3]
            ) / (cfg.dt**2)
        else:
            second_derivative = 0.0

        drift = self.freqs + cfg.coupling * gradient
        drift += cfg.anomaly_feedback * second_derivative
        noise = cfg.noise * self.rng.normal(size=self.phases.shape)
        self.phases = (self.phases + (drift * cfg.dt) + noise) % (2 * np.pi)

        order_parameter = np.mean(np.exp(1j * self.phases))
        global_coherence = np.abs(order_parameter)

        linear_coherence = float(np.mean(local_coherence))
        nonlinear_coherence = float(
            np.mean(local_coherence ** 2) / (linear_coherence**2 + EPS)
        )

        self.history.append(
            {
                "global_coherence": float(global_coherence),
                "scalar_signal": scalar_signal,
                "linear_coherence": linear_coherence,
                "nonlinear_coherence": nonlinear_coherence,
            }
        )

    def run(self) -> pd.DataFrame:
        """Run the simulation and return the recorded time-series."""
        for _ in range(self.config.steps):
            self.step()

        df = pd.DataFrame(self.history)
        df.insert(0, "t", np.arange(len(df)) * self.config.dt)
        return df


def detect_lighthouse_events(series: pd.Series, dt: float) -> pd.DataFrame:
    """Identify Lighthouse Events where the intensity crosses μ + 2σ."""
    if series.empty:
        return pd.DataFrame(columns=["index", "t", "intensity", "threshold"])

    threshold = series.mean() + 2 * series.std(ddof=0)
    mask = series > threshold
    indices = np.flatnonzero(mask.values)

    return pd.DataFrame(
        {
            "index": indices,
            "t": indices * dt,
            "intensity": series.iloc[indices].values,
            "threshold": threshold,
        }
    )


def detect_fibonacci_curvature(series: pd.Series, dt: float) -> pd.DataFrame:
    """Detect Fibonacci-style turning points based on curvature ratios."""
    if len(series) < 3:
        return pd.DataFrame(columns=["index", "t", "curvature", "ratio", "g_eff"])

    curvature = np.gradient(np.gradient(series.values))
    ratios = np.full_like(curvature, np.nan, dtype=float)
    matches: List[int] = []

    for i in range(1, len(curvature)):
        prev = curvature[i - 1]
        current = curvature[i]
        if abs(prev) < EPS:
            continue
        ratio = abs(current / prev)
        ratios[i] = ratio
        if abs(ratio - PHI) < 0.1 and abs(current) > np.std(curvature):
            matches.append(i)

    fib_match = ratios[matches] if matches else np.array([])
    curvature_strength = np.abs(curvature[matches]) if matches else np.array([])
    contrast = np.abs(series.diff().rolling(window=2).sum().fillna(0).values[matches])
    g_eff = fib_match * curvature_strength * contrast if matches else np.array([])

    return pd.DataFrame(
        {
            "index": matches,
            "t": np.array(matches) * dt,
            "curvature": curvature[matches] if matches else np.array([]),
            "ratio": fib_match,
            "g_eff": g_eff,
        }
    )


def normalize_series(series: pd.Series) -> pd.Series:
    """Normalise a series to the unit interval, guarding against zero span."""
    if series.empty:
        return series
    min_val = series.min()
    max_val = series.max()
    span = max_val - min_val
    if span < EPS:
        return pd.Series(np.ones_like(series), index=series.index)
    return (series - min_val) / span


def compute_pointer_fields(trace: pd.DataFrame, dt: float) -> pd.DataFrame:
    """Compute anomaly A(t) and pointer |Q(t)| from the scalar signal."""
    if len(trace) < 3:
        trace = trace.copy()
        trace["anomaly"] = 0.0
        trace["pointer"] = 0.0
        trace["curvature"] = 0.0
        trace["phi_coherence"] = 0.0
        return trace

    curvature = np.gradient(np.gradient(trace["scalar_signal"].values))
    energy = curvature**2
    mean_energy = np.mean(energy) + EPS
    anomaly = energy / mean_energy - 1
    pointer = np.abs(np.gradient(anomaly, dt))

    # φ-coherence uses a φ-shifted version of the global coherence trace.
    lag = max(1, int(round(PHI / dt)))
    shifted = np.roll(trace["global_coherence"].values, lag)
    centered = trace["global_coherence"].values - trace["global_coherence"].mean()
    shifted_centered = shifted - shifted.mean()
    phi_coherence = (
        np.correlate(centered, shifted_centered, mode="valid")[0]
        / (len(centered) * np.std(centered) * np.std(shifted_centered) + EPS)
    )
    phi_series = np.full_like(trace["global_coherence"].values, phi_coherence)

    enriched = trace.copy()
    enriched["curvature"] = curvature
    enriched["anomaly"] = anomaly
    enriched["pointer"] = pointer
    enriched["phi_coherence"] = phi_series
    return enriched


def compute_lighthouse(trace: pd.DataFrame) -> Tuple[pd.DataFrame, dict[str, pd.Series]]:
    """Compute lighthouse intensity and return component series."""

    components = {
        "linear": normalize_series(trace["linear_coherence"]),
        "nonlinear": normalize_series(trace["nonlinear_coherence"]),
        "phi": normalize_series(trace["phi_coherence"].abs()),
        "curvature": normalize_series(trace["curvature"].abs()),
        "pointer": normalize_series(trace["pointer"]),
    }

    product = np.ones(len(trace))
    for series in components.values():
        product *= series
    lighthouse = product ** (1 / len(components))

    enriched = trace.copy()
    enriched["lighthouse_intensity"] = lighthouse
    for name, series in components.items():
        enriched[f"component_{name}"] = series

    return enriched, components


def compute_ablation_table(
    components: dict[str, pd.Series],
    base_intensity: pd.Series,
    dt: float,
) -> pd.DataFrame:
    """Evaluate the impact of removing each component from the lighthouse."""

    rows = []
    base_events = detect_lighthouse_events(base_intensity, dt)
    rows.append(
        {
            "removed": "none",
            "event_count": len(base_events),
            "mean_intensity": float(base_intensity.mean()),
        }
    )

    component_items = list(components.items())
    for name, _series in component_items:
        remaining = [series for comp, series in component_items if comp != name]
        if not remaining:
            continue
        product = np.ones(len(base_intensity))
        for series in remaining:
            product *= series
        ablated = product ** (1 / len(remaining))
        events = detect_lighthouse_events(pd.Series(ablated), dt)
        rows.append(
            {
                "removed": name,
                "event_count": len(events),
                "mean_intensity": float(np.mean(ablated)),
            }
        )

    return pd.DataFrame(rows)


def save_trace(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def plot_results(
    trace: pd.DataFrame,
    lhe: pd.DataFrame,
    ftcp: pd.DataFrame,
    pointer: pd.DataFrame,
    output: Path,
) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)

    axes[0].plot(trace["t"], trace["global_coherence"], color="#d99c28", linewidth=2)
    axes[0].set_ylabel("R(t)")
    axes[0].set_title("Global Coherence R(t)")

    axes[1].plot(trace["t"], trace["lighthouse_intensity"], color="#d98f28")
    if not lhe.empty:
        axes[1].scatter(lhe["t"], lhe["intensity"], color="#1c6e8c", zorder=5)
        axes[1].axhline(lhe["threshold"].iloc[0], color="#d98f28", linestyle="--")
    else:
        axes[1].axhline(
            trace["lighthouse_intensity"].mean() + 2 * trace["lighthouse_intensity"].std(ddof=0),
            color="#d98f28",
            linestyle="--",
        )
    axes[1].set_ylabel("L(t)")
    axes[1].set_title("Lighthouse Intensity with LHE markers")

    axes[2].plot(trace["t"], trace["scalar_signal"], color="#d98f28")
    if not ftcp.empty:
        axes[2].scatter(ftcp["t"], trace.loc[ftcp["index"], "scalar_signal"], color="#1c6e8c")
    axes[2].set_ylabel("x(t)")
    axes[2].set_title("Scalar signal x(t) with Fibonacci knots")

    axes[3].plot(pointer["t"], pointer["pointer"], color="#1c6e8c", label="|Q(t)|")
    axes[3].plot(pointer["t"], pointer["anomaly"], color="#d99c28", alpha=0.7, label="A(t)")
    axes[3].set_ylabel("pointer / anomaly")
    axes[3].set_xlabel("t")
    axes[3].set_title("Quantum-gravity pointer fields")
    axes[3].legend()

    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output)
    plt.close(fig)


def run_engine(output_dir: Path | None = None) -> None:
    output_dir = output_dir or Path('.')
    engine = DreamEngine()
    trace = engine.run()

    dt = engine.config.dt
    pointer = compute_pointer_fields(trace, dt)
    pointer["t"] = np.arange(len(pointer)) * dt
    enriched, components = compute_lighthouse(pointer)
    lhe = detect_lighthouse_events(enriched["lighthouse_intensity"], dt)
    ftcp = detect_fibonacci_curvature(enriched["scalar_signal"], dt)
    ablation = compute_ablation_table(components, enriched["lighthouse_intensity"], dt)

    save_trace(enriched, output_dir / "dream_engine_trace.csv")
    save_trace(lhe, output_dir / "dream_engine_lhe.csv")
    save_trace(ftcp, output_dir / "dream_engine_ftcp.csv")
    save_trace(pointer[["t", "anomaly", "pointer", "curvature"]], output_dir / "dream_engine_pointer.csv")
    save_trace(ablation, output_dir / "dream_engine_ablation.csv")
    plot_results(enriched, lhe, ftcp, pointer, output_dir / "dream_engine_plot.png")

    print("Aureon's Dream Engine run complete.")
    print(f"Saved trace: {output_dir / 'dream_engine_trace.csv'}")
    print(f"Saved lighthouse events: {output_dir / 'dream_engine_lhe.csv'}")
    print(f"Saved Fibonacci curvature events: {output_dir / 'dream_engine_ftcp.csv'}")
    print(f"Saved pointer fields: {output_dir / 'dream_engine_pointer.csv'}")
    print(f"Saved ablation table: {output_dir / 'dream_engine_ablation.csv'}")
    print(f"Saved plot: {output_dir / 'dream_engine_plot.png'}")


if __name__ == "__main__":
    run_engine(Path("."))
