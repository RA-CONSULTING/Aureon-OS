import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Dict, Sequence, Iterable, List


@dataclass
class HarmonicNexusParameters:
    """Input parameters for the Harmonic Nexus metrics.

    All values are expected to be in the range [0, 1], except ``force_vector``
    which is a sequence of four components representing the fundamental forces.
    """

    source_potential: float
    nexus_coherence: float
    planetary_resonance: float
    force_vector: Sequence[float]
    observer_entropy: float


@dataclass
class SchumannWindow:
    """Summary statistics for a Schumann resonance sample window."""

    fundamental_hz: float
    """Dominant frequency observed around 7.83 Hz."""

    harmonics_hz: Sequence[float]
    """Estimated harmonic peaks for the window (e.g. 14.3, 20.8, …)."""

    amplitude: float
    """Average amplitude of the window after filtering."""


@dataclass
class AuraBioWindow:
    """Condensed biometric features from the aura bio scan."""

    alpha: float
    theta: float
    beta: float
    hrv_rmssd: float
    gsr_us: float
    respiration_bpm: float


def compute_metrics(params: HarmonicNexusParameters) -> Dict[str, float]:
    """Compute derived metrics for the Harmonic Nexus Theory.

    Parameters
    ----------
    params:
        ``HarmonicNexusParameters`` instance containing input values.

    Returns
    -------
    dict
        Dictionary containing base and derived metrics.
    """

    cognition_value = params.observer_entropy * params.source_potential
    unity_metric = float(np.sum(params.force_vector)) * params.nexus_coherence

    return {
        "Source Potential": params.source_potential,
        "Nexus Coherence": params.nexus_coherence,
        "Planetary Resonance": params.planetary_resonance,
        "Observer Entropy": params.observer_entropy,
        "Cognition Value": cognition_value,
        "Unity Metric": unity_metric,
    }


def _normalize(value: float, *, lower: float, upper: float) -> float:
    """Return ``value`` scaled into ``[0, 1]`` using the provided bounds."""

    if upper <= lower:
        raise ValueError("upper bound must be greater than lower bound")
    scaled = (value - lower) / (upper - lower)
    return float(np.clip(scaled, 0.0, 1.0))


def aggregate_windows(
    schumann: Iterable[SchumannWindow],
    aura: Iterable[AuraBioWindow],
) -> HarmonicNexusParameters:
    """Derive canonical Harmonic Nexus parameters from paired sensor windows.

    The computation fuses the environmental Schumann resonance feed with the
    biometric aura scan, mirroring the protocol executed by the validation
    bridge.  All heuristics are scaled into ``[0, 1]`` so the downstream radar
    plot remains interpretable even when only a few synthetic samples are
    available.
    """

    schumann_list: List[SchumannWindow] = list(schumann)
    aura_list: List[AuraBioWindow] = list(aura)
    if not schumann_list:
        raise ValueError("schumann sequence must not be empty")
    if not aura_list:
        raise ValueError("aura sequence must not be empty")

    window_count = min(len(schumann_list), len(aura_list))
    schumann_list = schumann_list[:window_count]
    aura_list = aura_list[:window_count]

    fundamental = np.array([w.fundamental_hz for w in schumann_list])
    amplitudes = np.array([w.amplitude for w in schumann_list])
    harmonics = [w.harmonics_hz for w in schumann_list]

    alpha = np.array([w.alpha for w in aura_list])
    theta = np.array([w.theta for w in aura_list])
    beta = np.array([w.beta for w in aura_list])
    hrv = np.array([w.hrv_rmssd for w in aura_list])
    gsr = np.array([w.gsr_us for w in aura_list])
    respiration = np.array([w.respiration_bpm for w in aura_list])

    # Source Potential favours relaxed alpha/theta dominance, strong heart-rate
    # variability and a gently elevated galvanic response (biocharge).
    total_brain = alpha + theta + beta + 1e-9
    calm_ratio = np.mean((alpha + theta) / total_brain)
    hrv_norm = _normalize(np.mean(hrv), lower=20.0, upper=120.0)
    biocharge = _normalize(np.mean(gsr), lower=1.0, upper=20.0)
    source_potential = float(np.clip((calm_ratio + hrv_norm + biocharge) / 3.0, 0.0, 1.0))

    # Nexus Coherence measures how tightly the Schumann amplitude tracks the
    # heart-coherence readout.  A neutral value of 0.5 is used when the series
    # are too short or perfectly flat.
    coherence_score = 0.0
    if window_count >= 2 and not np.allclose(amplitudes, amplitudes[0]) and not np.allclose(hrv, hrv[0]):
        correlation = float(np.corrcoef(amplitudes, hrv)[0, 1])
        if np.isnan(correlation):
            correlation = 0.0
        coherence_score = float(np.clip(correlation, -1.0, 1.0))
    nexus_coherence = float(np.clip((coherence_score + 1.0) / 2.0, 0.0, 1.0))
    if window_count < 2 or np.allclose(amplitudes, amplitudes[0]) or np.allclose(hrv, hrv[0]):
        nexus_coherence = max(nexus_coherence, 0.5)

    # Planetary Resonance rewards fundamental frequencies near 7.83 Hz.
    fund_dev = float(np.mean(np.abs(fundamental - 7.83)))
    planetary_resonance = float(np.clip(1.0 - (fund_dev / 0.6), 0.0, 1.0))

    # Observer Entropy relies on variability in GSR and breathing cadence.
    variability = 0.7 * float(np.std(gsr)) + 0.3 * float(np.std(respiration) / 4.0)
    observer_entropy = _normalize(variability, lower=0.0, upper=2.5)

    # Force-vector components map to the speculative "fundamental forces".
    amp_norm = _normalize(float(np.mean(amplitudes)), lower=0.0, upper=1.5)
    theta_ratio = float(np.clip(np.mean(theta / total_brain), 0.0, 1.0))
    coherence_inverse = float(np.clip(1.0 - observer_entropy, 0.0, 1.0))
    force_vector = (
        amp_norm,
        theta_ratio,
        coherence_inverse,
        nexus_coherence,
    )

    # Blend harmonic alignment into the second component to honour the Schumann
    # ladder without expanding the vector beyond four dimensions.
    expected_harmonics = (14.3, 20.8, 27.3, 33.8)
    harmonic_scores = []
    for index, target in enumerate(expected_harmonics):
        diffs = [abs(window[index] - target) for window in harmonics if len(window) > index]
        if diffs:
            alignment = 1.0 - (float(np.mean(diffs)) / 1.2)
            harmonic_scores.append(float(np.clip(alignment, 0.0, 1.0)))
    if harmonic_scores:
        harmonic_alignment = float(np.mean(harmonic_scores))
        force_vector = (
            force_vector[0],
            float(np.clip((force_vector[1] + harmonic_alignment) / 2.0, 0.0, 1.0)),
            force_vector[2],
            force_vector[3],
        )

    return HarmonicNexusParameters(
        source_potential=source_potential,
        nexus_coherence=nexus_coherence,
        planetary_resonance=planetary_resonance,
        force_vector=force_vector,
        observer_entropy=observer_entropy,
    )


def compute_metrics_from_streams(
    schumann: Iterable[SchumannWindow],
    aura: Iterable[AuraBioWindow],
) -> Dict[str, float]:
    """Convenience wrapper returning derived metrics from paired streams."""

    params = aggregate_windows(schumann, aura)
    return compute_metrics(params)


def radar_plot(metrics: Dict[str, float], *, show: bool = True, save_path: str | None = None) -> None:
    """Create a radar plot from metric values.

    Parameters
    ----------
    metrics:
        Mapping of metric names to values.
    show:
        If ``True`` (default), display the plot in a window.
    save_path:
        Optional path to save the figure as an image file.
    """

    labels = list(metrics.keys())
    values = list(metrics.values())

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
    values_closed = np.concatenate((values, [values[0]]))
    angles_closed = np.concatenate((angles, [angles[0]]))

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
    ax.plot(angles_closed, values_closed, "o-", linewidth=2)
    ax.fill(angles_closed, values_closed, alpha=0.25)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, max(1.0, max(values_closed)))
    ax.set_title("Harmonic Nexus Metrics")

    if save_path:
        plt.savefig(save_path)
    if show:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    # Example usage mirroring the speculative framework.
    schumann_samples = [
        SchumannWindow(7.82, [14.3, 20.9, 27.4, 33.7], 0.95),
        SchumannWindow(7.84, [14.2, 20.8, 27.3, 33.6], 1.02),
        SchumannWindow(7.81, [14.4, 20.7, 27.2, 33.9], 0.88),
    ]
    aura_samples = [
        AuraBioWindow(0.46, 0.31, 0.23, 62.0, 5.4, 9.5),
        AuraBioWindow(0.5, 0.33, 0.17, 68.0, 6.1, 9.0),
        AuraBioWindow(0.48, 0.34, 0.18, 70.0, 5.8, 8.8),
    ]
    metrics = compute_metrics_from_streams(schumann_samples, aura_samples)
    radar_plot(metrics)
