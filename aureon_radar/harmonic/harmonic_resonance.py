"""
HarmonicResonance — the math of alignment
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Computes how "aligned" a set of pillar signals is. Alignment has four
components, each in [0, 1]:

  1. signal_consensus  — fraction agreeing on direction (BUY/SELL/NEUTRAL)
  2. harmonic_lock     — how cleanly each frequency relates to the fundamental
                          528 Hz (perfect unison/octave/fifth/fourth/third score 1.0;
                          distant ratios score lower)
  3. phase_coherence   — how tightly the sin(2πft + φ) phases cluster
                          (low std dev of phase angles = high coherence)
  4. mean_coherence    — average of each pillar's self-reported Γ

The overall alignment score is the geometric mean of these four components,
which means ALL four must be high for the Lighthouse to clear — any one
weak link drags the whole score down. This is deliberate: alignment is
all-or-nothing.

Lighthouse threshold: Γ > 0.945 (from the Aureon white paper).
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

FUNDAMENTAL_HZ: float = 528.0
"""Love tone — the root of the harmonic stack the pillars sing on."""

LIGHTHOUSE_THRESHOLD: float = 0.945
"""Γ > 0.945 clears the Lighthouse consensus gate (Aureon white paper)."""

# Musically consonant ratios (numerator/denominator of 528 Hz)
# The closer a frequency ratio is to one of these, the more harmonic it is
CONSONANT_RATIOS: Dict[str, float] = {
    "unison":         1.0,      # 528 Hz
    "octave":         2.0,      # 1056 Hz
    "sub_octave":     0.5,      # 264 Hz
    "perfect_fifth":  1.5,      # 792 Hz
    "perfect_fourth": 4 / 3,    # 704 Hz
    "sub_fourth":     3 / 4,    # 396 Hz ← Piano
    "major_third":    5 / 4,    # 660 Hz
    "minor_third":    6 / 5,    # 633.6 Hz
    "major_sixth":    5 / 3,    # 880 Hz
    "major_second":   9 / 8,    # 594 Hz
    "minor_seventh":  16 / 9,   # 938.67 Hz
    "tritone":        math.sqrt(2),  # 746.99 Hz ← Auris (741)
    # 432 Hz is 528 × (432/528) = 528 × 18/22 = 528 × 9/11 — dissonant
    "sub_major_third": 432 / 528,   # 0.8181...  ← Nexus/Omega
}

# Invert for lookup
_RATIO_VALUES = list(CONSONANT_RATIOS.values())


# ─────────────────────────────────────────────────────────────────────────────
# Dataclasses
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class HarmonicAnalysis:
    """The full harmonic profile of a set of pillar signals."""

    signal_consensus: float = 0.0        # fraction agreeing on direction
    harmonic_lock: float = 0.0           # frequency consonance to 528 Hz
    phase_coherence: float = 0.0         # phase alignment across pillars
    mean_coherence: float = 0.0          # average Γ across pillars
    alignment_score: float = 0.0         # geometric mean of the 4 components
    lighthouse_cleared: bool = False     # alignment_score > 0.945
    dominant_signal: str = "NEUTRAL"
    agreeing_pillars: int = 0
    total_pillars: int = 0
    mean_frequency_hz: float = 0.0
    frequency_std_hz: float = 0.0
    per_pillar_ratios: Dict[str, float] = field(default_factory=dict)
    per_pillar_consonance: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_consensus": round(self.signal_consensus, 4),
            "harmonic_lock": round(self.harmonic_lock, 4),
            "phase_coherence": round(self.phase_coherence, 4),
            "mean_coherence": round(self.mean_coherence, 4),
            "alignment_score": round(self.alignment_score, 4),
            "lighthouse_cleared": self.lighthouse_cleared,
            "dominant_signal": self.dominant_signal,
            "agreeing_pillars": self.agreeing_pillars,
            "total_pillars": self.total_pillars,
            "mean_frequency_hz": round(self.mean_frequency_hz, 2),
            "frequency_std_hz": round(self.frequency_std_hz, 2),
            "per_pillar_ratios": {k: round(v, 4) for k, v in self.per_pillar_ratios.items()},
            "per_pillar_consonance": {k: round(v, 4) for k, v in self.per_pillar_consonance.items()},
        }


# ─────────────────────────────────────────────────────────────────────────────
# Signal consensus
# ─────────────────────────────────────────────────────────────────────────────


def compute_signal_consensus(signals: Iterable[str]) -> Tuple[float, str, int, int]:
    """
    Compute what fraction of signals agree on the same direction.

    Returns:
        (consensus_score ∈ [0,1], dominant_signal, agreeing_count, total)
    """
    sig_list = [str(s).upper() for s in signals]
    if not sig_list:
        return 0.0, "NEUTRAL", 0, 0

    counts: Dict[str, int] = {}
    for s in sig_list:
        counts[s] = counts.get(s, 0) + 1

    dominant = max(counts, key=counts.get)
    agreeing = counts[dominant]
    total = len(sig_list)

    # Consensus = fraction agreeing. If perfectly split, ~0.5.
    consensus = agreeing / total
    return consensus, dominant, agreeing, total


# ─────────────────────────────────────────────────────────────────────────────
# Frequency harmony — how consonant is a ratio to 528 Hz
# ─────────────────────────────────────────────────────────────────────────────


def consonance_score(ratio: float) -> float:
    """
    Score how consonant a frequency ratio is.
    1.0 = exactly a known consonant interval.
    Closer to an interval = higher score; midway between intervals = lower.

    Uses a Gaussian-like falloff around each consonant ratio.
    """
    if ratio <= 0:
        return 0.0

    # Find the closest consonant ratio
    best = min(_RATIO_VALUES, key=lambda r: abs(math.log(ratio) - math.log(r)))
    # Log-space distance so octaves behave correctly
    log_diff = abs(math.log(ratio) - math.log(best))
    # Sharp Gaussian: 0 log diff → 1.0, log diff of 0.1 (~10%) → ~0.6
    sigma = 0.12
    return math.exp(-(log_diff ** 2) / (2 * sigma ** 2))


def analyse_frequency_harmony(
    pillar_frequencies: Dict[str, float],
    fundamental_hz: float = FUNDAMENTAL_HZ,
) -> Tuple[float, Dict[str, float], Dict[str, float]]:
    """
    Analyse how well each pillar frequency harmonises with the fundamental.

    Returns:
        (mean_harmonic_lock, ratios, consonance_scores)
    """
    if not pillar_frequencies:
        return 0.0, {}, {}

    ratios: Dict[str, float] = {}
    consonances: Dict[str, float] = {}
    for name, freq in pillar_frequencies.items():
        if freq <= 0:
            ratios[name] = 0.0
            consonances[name] = 0.0
            continue
        ratio = freq / fundamental_hz
        ratios[name] = ratio
        consonances[name] = consonance_score(ratio)

    # Mean consonance = how tightly the stack locks
    mean_lock = sum(consonances.values()) / len(consonances)
    return mean_lock, ratios, consonances


# ─────────────────────────────────────────────────────────────────────────────
# Phase coherence
# ─────────────────────────────────────────────────────────────────────────────


def compute_phase_coherence(phases_rad: List[float]) -> float:
    """
    Compute phase coherence as the magnitude of the mean complex phasor.

    R = |<e^(iφ)>| ∈ [0, 1]
    R = 1 → perfect phase lock
    R = 0 → phases uniformly distributed on the circle (no coherence)

    This is the Kuramoto order parameter.
    """
    if not phases_rad:
        return 0.0
    n = len(phases_rad)
    sum_cos = sum(math.cos(p) for p in phases_rad)
    sum_sin = sum(math.sin(p) for p in phases_rad)
    r = math.sqrt(sum_cos ** 2 + sum_sin ** 2) / n
    return max(0.0, min(1.0, r))


def derive_phase(frequency_hz: float, t: float, signal: str) -> float:
    """
    Derive a phase angle for a pillar signal at time t.
    BUY pillars are at phase 0, SELL at phase π, NEUTRAL mid.
    Frequency phase drift adds 2π f t.
    """
    base = 0.0
    sig = str(signal).upper()
    if sig == "BUY":
        base = 0.0
    elif sig == "SELL":
        base = math.pi
    else:  # NEUTRAL / HOLD
        base = math.pi / 2
    return (base + 2 * math.pi * frequency_hz * t) % (2 * math.pi)


# ─────────────────────────────────────────────────────────────────────────────
# Full analysis
# ─────────────────────────────────────────────────────────────────────────────


def geometric_mean(values: List[float]) -> float:
    """Geometric mean — penalises any weak component."""
    if not values:
        return 0.0
    clamped = [max(1e-9, min(1.0, v)) for v in values]
    return math.exp(sum(math.log(v) for v in clamped) / len(clamped))


def full_harmonic_analysis(
    pillar_results: List[Dict[str, Any]],
    t: Optional[float] = None,
    fundamental_hz: float = FUNDAMENTAL_HZ,
) -> HarmonicAnalysis:
    """
    Run the full harmonic analysis on a list of pillar result dicts.

    Each dict should have:
        - signal        : BUY | SELL | NEUTRAL
        - confidence    : [0, 1]
        - coherence     : [0, 1]
        - frequency_hz  : Solfeggio frequency
        - pillar        : pillar name (optional)
    """
    import time as _time
    if t is None:
        t = _time.time()

    analysis = HarmonicAnalysis(total_pillars=len(pillar_results))
    if not pillar_results:
        return analysis

    # 1. Signal consensus
    signals = [r.get("signal", "NEUTRAL") for r in pillar_results]
    consensus, dominant, agreeing, total = compute_signal_consensus(signals)
    analysis.signal_consensus = consensus
    analysis.dominant_signal = dominant
    analysis.agreeing_pillars = agreeing

    # 2. Harmonic lock
    freqs = {
        str(r.get("pillar", f"pillar_{i}")): float(r.get("frequency_hz", fundamental_hz))
        for i, r in enumerate(pillar_results)
    }
    harmonic_lock, ratios, consonances = analyse_frequency_harmony(freqs, fundamental_hz)
    analysis.harmonic_lock = harmonic_lock
    analysis.per_pillar_ratios = ratios
    analysis.per_pillar_consonance = consonances

    # Mean / std frequency
    freq_values = [f for f in freqs.values() if f > 0]
    if freq_values:
        analysis.mean_frequency_hz = sum(freq_values) / len(freq_values)
        if len(freq_values) > 1:
            analysis.frequency_std_hz = statistics.stdev(freq_values)

    # 3. Phase coherence
    phases = [
        derive_phase(float(r.get("frequency_hz", fundamental_hz)), t, r.get("signal", "NEUTRAL"))
        for r in pillar_results
    ]
    analysis.phase_coherence = compute_phase_coherence(phases)

    # 4. Mean self-reported coherence
    coherences = [float(r.get("coherence", 0.5)) for r in pillar_results]
    analysis.mean_coherence = sum(coherences) / len(coherences) if coherences else 0.0

    # Overall alignment = geometric mean of the 4 components
    analysis.alignment_score = geometric_mean([
        analysis.signal_consensus,
        analysis.harmonic_lock,
        analysis.phase_coherence,
        analysis.mean_coherence,
    ])

    # Lighthouse
    analysis.lighthouse_cleared = analysis.alignment_score > LIGHTHOUSE_THRESHOLD

    return analysis
