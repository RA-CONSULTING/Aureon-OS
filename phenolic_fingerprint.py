#!/usr/bin/env python3
"""Phenolic Fingerprint — falsifiable spectral-coherence analysis engine.

This module tests, in a pre-registered and reproducible way, whether the
spectral peaks of a phenolic compound carry *non-random structure* once they are
converted into the HNC modulation band. It mirrors the decisive-test protocol of
the HNC BioMolecule white paper (data package
``docs/research/HNC_BioMolecule_White_Paper_Data_Package_v1.zip``): the
random-frequency control arm (arm E) and the assay-validation control arm
(arm J). The physics constants and the octave-downconversion are identical to
``hnc_biomolecule_packet_v02.py`` so a peak maps to exactly the same modulation
frequency here as it does in the packet blueprint.

Two independent, one-sided permutation tests are applied per compound:

* **Test A — coherence clustering.** Do the compound's modulation tones cluster
  more tightly (more close pairs within ``COHERENCE_TOLERANCE_HZ``) than an
  envelope-matched random-frequency control of the same tone count?
* **Test B — golden-interval alignment.** Do the pairwise frequency ratios sit
  closer to integer powers of ``PHI`` than the same random control?

A compound is flagged ``separable`` only when *both* tests reject the null at
``ALPHA``. Before any compound is scored, two controls validate the machinery:
a constructed positive control (structured signal — must be detected) and a
negative control (envelope-matched noise — must *not* over-fire). If either
control fails, the whole run is marked invalid and **no compound results are
returned** — the caller must treat the run as inconclusive.

Scientific boundary: this engine evaluates statistical structure in a derived
signal representation. It does not demonstrate biological efficacy.

Pure standard library + numpy. Deterministic given a seed. No global state.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import numpy as np

__all__ = [
    "Peak",
    "ControlResult",
    "RunResult",
    "load_peaks",
    "peak_to_modulation_hz",
    "test_A",
    "test_B",
    "positive_control",
    "negative_control",
    "run",
    "ALPHA",
    "DEFAULT_NULLS",
    "MIN_PEAK_CM1",
]

# ============================================================================
# PRE-REGISTERED CONSTANTS — do not tune per dataset.
# ============================================================================

PHI: Final[float] = 1.618033988749895
PHI_INV_9: Final[float] = PHI ** (-9)  # ~0.0132, the packet's geometric delta

# Spectral-peak -> frequency conversion (identical to hnc_biomolecule_packet_v02).
CM1_TO_THZ: Final[float] = 0.0299792458  # cm^-1 * this = THz
NM_TO_THZ_NUMERATOR: Final[float] = 299_792.458  # THz = numerator / nm
THZ_TO_HZ: Final[float] = 1.0e12

TARGET_BAND_HZ: Final[tuple[float, float]] = (1000.0, 2000.0)
OCTAVE_SEARCH_RANGE: Final[tuple[int, int]] = (20, 60)
COHERENCE_TOLERANCE_HZ: Final[float] = 25.0  # packet clustering tolerance

# Statistical thresholds.
ALPHA: Final[float] = 0.05
DEFAULT_NULLS: Final[int] = 500
MIN_PEAK_CM1: Final[float] = 100.0

# Negative-control calibration: over this many seeded random draws the machinery
# may flag at most this fraction as separable (nominal separable false-positive
# rate is ~ALPHA^2, so this tolerance carries a wide, deliberate safety margin).
_NEG_CONTROL_TRIALS: Final[int] = 20
_NEG_CONTROL_MAX_HIT_RATE: Final[float] = 0.20

# Native input schema (the schema the connector normalizes everything into).
NATIVE_FIELDS: Final[tuple[str, ...]] = (
    "molecule",
    "peak_value",
    "unit",
    "rel_intensity",
    "source",
)


# ============================================================================
# DATA CLASSES
# ============================================================================


@dataclass(frozen=True)
class Peak:
    """A single spectral peak in the native schema."""

    molecule: str
    peak_value: float
    unit: str
    rel_intensity: str | float | None
    source: str


@dataclass(frozen=True)
class ControlResult:
    """Outcome of a single control arm."""

    name: str
    passed: bool
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "passed": self.passed, "detail": dict(self.detail)}


@dataclass(frozen=True)
class RunResult:
    """Structured result of a full engine run.

    When ``valid`` is ``False`` (a control failed) ``compounds`` is always empty:
    the engine never emits per-compound scores from an invalid run.
    """

    valid: bool
    alpha: float
    n_nulls: int
    seed: int
    controls: dict[str, ControlResult]
    compounds: dict[str, dict[str, Any]]
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "alpha": self.alpha,
            "n_nulls": self.n_nulls,
            "seed": self.seed,
            "reason": self.reason,
            "controls": {k: v.to_dict() for k, v in self.controls.items()},
            "compounds": self.compounds,
        }


# ============================================================================
# LOADING + CONVERSION
# ============================================================================


def load_peaks(path: str | Path) -> list[Peak]:
    """Load peaks from a native-schema CSV (``molecule,peak_value,unit,rel_intensity,source``).

    ``peak_value`` is coerced to ``float``; a row with a missing or unparseable
    peak value raises ``ValueError`` (the engine fails loudly rather than
    silently dropping data — the connector's validation gate is responsible for
    cleaning inputs before they reach here).
    """
    path = Path(path)
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"{path} is empty or has no header row")
        missing = {"molecule", "peak_value", "unit", "source"} - set(reader.fieldnames)
        if missing:
            raise ValueError(
                f"{path} is missing required native columns: {sorted(missing)}"
            )
        peaks: list[Peak] = []
        for lineno, row in enumerate(reader, start=2):
            raw_value = (row.get("peak_value") or "").strip()
            try:
                peak_value = float(raw_value)
            except ValueError as exc:
                raise ValueError(
                    f"{path}:{lineno} has unparseable peak_value {raw_value!r}"
                ) from exc
            rel = row.get("rel_intensity")
            rel_intensity: str | float | None
            if rel is None or rel.strip() == "":
                rel_intensity = None
            else:
                try:
                    rel_intensity = float(rel)
                except ValueError:
                    rel_intensity = rel.strip()
            peaks.append(
                Peak(
                    molecule=(row.get("molecule") or "").strip(),
                    peak_value=peak_value,
                    unit=(row.get("unit") or "").strip(),
                    rel_intensity=rel_intensity,
                    source=(row.get("source") or "").strip(),
                )
            )
    return peaks


def _molecular_frequency_hz(peak_value: float, unit: str) -> float:
    """Convert a spectral peak to its molecular/electromagnetic frequency in Hz."""
    if unit == "cm^-1":
        return peak_value * CM1_TO_THZ * THZ_TO_HZ
    if unit == "nm":
        return (NM_TO_THZ_NUMERATOR / peak_value) * THZ_TO_HZ
    raise ValueError(f"Unsupported unit {unit!r}; expected 'cm^-1' or 'nm'.")


def _select_octaves(freq_hz: float) -> int:
    """Choose the octave divisor placing ``freq_hz`` nearest the target-band centre.

    Identical selection rule to ``hnc_biomolecule_packet_v02.SpectralPeak.select_octaves``.
    """
    low, high = TARGET_BAND_HZ
    center = math.sqrt(low * high)
    best_n = OCTAVE_SEARCH_RANGE[0]
    best_score = float("inf")
    for n in range(OCTAVE_SEARCH_RANGE[0], OCTAVE_SEARCH_RANGE[1] + 1):
        f_mod = freq_hz / (2**n)
        if low <= f_mod <= high:
            score = abs(math.log(f_mod / center))
        else:
            distance = min(abs(math.log(f_mod / low)), abs(math.log(f_mod / high)))
            score = 10.0 + distance
        if score < best_score:
            best_n = n
            best_score = score
    return best_n


def peak_to_modulation_hz(peak_value: float, unit: str) -> float:
    """Map a spectral peak to its octave-downconverted modulation frequency (Hz)."""
    freq_hz = _molecular_frequency_hz(peak_value, unit)
    return freq_hz / (2 ** _select_octaves(freq_hz))


# ============================================================================
# TEST STATISTICS
# ============================================================================


def _clustering_statistic(freqs: np.ndarray, tolerance_hz: float) -> float:
    """Number of unordered frequency pairs within ``tolerance_hz`` (higher = tighter)."""
    if freqs.size < 2:
        return 0.0
    diffs = np.abs(freqs[:, None] - freqs[None, :])
    iu = np.triu_indices(freqs.size, k=1)
    return float(np.count_nonzero(diffs[iu] <= tolerance_hz))


def _phi_alignment_statistic(freqs: np.ndarray) -> float:
    """Mean pairwise alignment of log frequency-ratios to integer powers of PHI.

    Each unordered pair contributes ``1 - 2 * d`` where ``d`` is the distance
    (in [0, 0.5]) from ``log(hi/lo)/log(PHI)`` to the nearest integer. 1.0 means a
    ratio exactly equal to a power of PHI; ~0 means maximally off-lattice.
    """
    if freqs.size < 2:
        return 0.0
    positive = freqs[freqs > 0.0]
    if positive.size < 2:
        return 0.0
    logs = np.log(positive) / math.log(PHI)
    iu = np.triu_indices(positive.size, k=1)
    gaps = np.abs(logs[:, None] - logs[None, :])[iu]
    d = np.abs(gaps - np.round(gaps))
    return float(np.mean(1.0 - 2.0 * d))


def _null_envelope(freqs: np.ndarray, rng: np.random.Generator, nulls: int) -> np.ndarray:
    """Draw ``nulls`` random-frequency control sets matched to the observed envelope.

    Each control has the same tone count as ``freqs`` and is drawn uniformly on
    ``[min(freqs), max(freqs)]`` — the arm-E random-frequency control idiom.
    """
    low, high = float(np.min(freqs)), float(np.max(freqs))
    if high <= low:
        high = low + 1.0
    return rng.uniform(low, high, size=(nulls, freqs.size))


def _one_sided_p(observed: float, null_stats: np.ndarray) -> float:
    """One-sided permutation p-value with add-one smoothing (larger = more extreme)."""
    n = null_stats.size
    exceed = int(np.count_nonzero(null_stats >= observed))
    return (1.0 + exceed) / (1.0 + n)


def test_A(freqs: np.ndarray, *, nulls: int, rng: np.random.Generator) -> float:
    """Test A (coherence clustering): p-value that tones cluster more than chance."""
    freqs = np.asarray(freqs, dtype=float)
    if freqs.size < 2:
        return 1.0
    observed = _clustering_statistic(freqs, COHERENCE_TOLERANCE_HZ)
    controls = _null_envelope(freqs, rng, nulls)
    null_stats = np.array(
        [_clustering_statistic(controls[i], COHERENCE_TOLERANCE_HZ) for i in range(nulls)]
    )
    return _one_sided_p(observed, null_stats)


def test_B(freqs: np.ndarray, *, nulls: int, rng: np.random.Generator) -> float:
    """Test B (golden-interval alignment): p-value that ratios align to PHI powers."""
    freqs = np.asarray(freqs, dtype=float)
    if freqs.size < 2:
        return 1.0
    observed = _phi_alignment_statistic(freqs)
    controls = _null_envelope(freqs, rng, nulls)
    null_stats = np.array([_phi_alignment_statistic(controls[i]) for i in range(nulls)])
    return _one_sided_p(observed, null_stats)


# ============================================================================
# CONTROLS
# ============================================================================


def _rng(seed: int, tag: int) -> np.random.Generator:
    """Independent, reproducible generator stream for a given (seed, purpose)."""
    return np.random.default_rng([int(seed), int(tag)])


def _structured_positive_signal() -> np.ndarray:
    """Construct a signal that is clustered AND golden-ratio spaced (assay control).

    Four cluster centres at ``1000 * PHI**i`` (all pairwise ratios are exact PHI
    powers) with a tight triple (+/- 4 Hz) around each centre, guaranteeing both
    high clustering and high PHI-alignment relative to any envelope-matched noise.
    """
    centers = 1000.0 * (PHI ** np.arange(4))
    offsets = np.array([-4.0, 0.0, 4.0])
    return np.sort((centers[:, None] + offsets[None, :]).ravel())


def positive_control(*, nulls: int, seed: int) -> ControlResult:
    """Assay-validation positive control: a structured signal that must be detected."""
    freqs = _structured_positive_signal()
    p_a = test_A(freqs, nulls=nulls, rng=_rng(seed, 101))
    p_b = test_B(freqs, nulls=nulls, rng=_rng(seed, 102))
    detected = p_a < ALPHA and p_b < ALPHA
    return ControlResult(
        name="positive",
        passed=detected,
        detail={"test_A_p": p_a, "test_B_p": p_b, "n_tones": int(freqs.size)},
    )


def negative_control(*, nulls: int, seed: int) -> ControlResult:
    """Calibration negative control: noise must not over-fire the separability call."""
    hits = 0
    trials: list[dict[str, float]] = []
    for trial in range(_NEG_CONTROL_TRIALS):
        draw_rng = _rng(seed, 200 + trial)
        freqs = np.sort(draw_rng.uniform(*TARGET_BAND_HZ, size=12))
        p_a = test_A(freqs, nulls=nulls, rng=_rng(seed, 300 + trial))
        p_b = test_B(freqs, nulls=nulls, rng=_rng(seed, 400 + trial))
        separable = p_a < ALPHA and p_b < ALPHA
        hits += int(separable)
        trials.append({"test_A_p": p_a, "test_B_p": p_b})
    hit_rate = hits / _NEG_CONTROL_TRIALS
    return ControlResult(
        name="negative",
        passed=hit_rate <= _NEG_CONTROL_MAX_HIT_RATE,
        detail={
            "hit_rate": hit_rate,
            "hits": hits,
            "trials": _NEG_CONTROL_TRIALS,
            "max_hit_rate": _NEG_CONTROL_MAX_HIT_RATE,
        },
    )


# ============================================================================
# ORCHESTRATION
# ============================================================================


def _group_frequencies(peaks: list[Peak]) -> dict[str, np.ndarray]:
    """Convert peaks to modulation frequencies grouped by compound (order-stable)."""
    grouped: dict[str, list[float]] = {}
    for peak in peaks:
        grouped.setdefault(peak.molecule, []).append(
            peak_to_modulation_hz(peak.peak_value, peak.unit)
        )
    return {name: np.array(sorted(values)) for name, values in grouped.items()}


def run(peaks: list[Peak], *, nulls: int = DEFAULT_NULLS, seed: int = 0) -> RunResult:
    """Run the full falsifiable analysis over ``peaks``.

    Controls are evaluated first. If either the positive or the negative control
    fails, the run is invalid and no per-compound results are produced. Otherwise
    every compound with at least two peaks is scored with Test A and Test B and
    flagged ``separable`` when both reject the null at ``ALPHA``.
    """
    if nulls < 1:
        raise ValueError("nulls must be a positive integer")

    pos = positive_control(nulls=nulls, seed=seed)
    neg = negative_control(nulls=nulls, seed=seed)
    controls = {"positive": pos, "negative": neg}

    if not (pos.passed and neg.passed):
        failed = [c.name for c in (pos, neg) if not c.passed]
        return RunResult(
            valid=False,
            alpha=ALPHA,
            n_nulls=nulls,
            seed=seed,
            controls=controls,
            compounds={},
            reason=f"control(s) failed: {', '.join(failed)}",
        )

    compounds: dict[str, dict[str, Any]] = {}
    for idx, (name, freqs) in enumerate(_group_frequencies(peaks).items()):
        if freqs.size < 2:
            compounds[name] = {
                "test_A_p": None,
                "test_B_p": None,
                "separable": False,
                "n_peaks": int(freqs.size),
                "note": "insufficient peaks (need >= 2) for testing",
            }
            continue
        p_a = test_A(freqs, nulls=nulls, rng=_rng(seed, 1000 + idx))
        p_b = test_B(freqs, nulls=nulls, rng=_rng(seed, 5000 + idx))
        compounds[name] = {
            "test_A_p": p_a,
            "test_B_p": p_b,
            "separable": bool(p_a < ALPHA and p_b < ALPHA),
            "n_peaks": int(freqs.size),
        }

    return RunResult(
        valid=True,
        alpha=ALPHA,
        n_nulls=nulls,
        seed=seed,
        controls=controls,
        compounds=compounds,
        reason=None,
    )


if __name__ == "__main__":  # pragma: no cover - manual smoke entry point
    import sys

    result = run(load_peaks(sys.argv[1]))
    print(f"valid={result.valid} reason={result.reason}")
    for compound, scores in result.compounds.items():
        print(f"  {compound}: {scores}")
