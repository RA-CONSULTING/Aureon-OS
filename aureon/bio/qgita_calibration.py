#!/usr/bin/env python3
"""QGITA calibration — validate the φ engine against QGITA's golden-ratio systems.

QGITA ("Quantum Gravity in the Act", Gary Leckey, Aureon Institute) is a two-stage
golden-ratio event detector: it embeds a **Fibonacci time lattice** whose intervals
scale by φ and flags structure only under golden-ratio tuning. The phenolic
fingerprint engine is an *independent* golden-ratio detector: Test B measures how
closely a tone set's pairwise ratios align to integer powers of φ. Both systems hinge
on the **same** constant — ``engine.PHI == qgita.PHI == 1.618033988749895``.

This module **calibrates by validation** (the contract in the repo-root
``calibration.py``): it confirms, without changing a single engine threshold, that

  1. the phenolic engine's φ-alignment arm (Test B) **detects** QGITA's golden lattice
     (tones at ``base·φ^k``, the FibonacciTimeLattice φ-scaling), and
  2. at that lattice's scale, an envelope-matched random null still produces a
     separable false-positive rate at or below ``ALPHA``, and the engine's own
     positive/negative controls still hold.

It never tunes ``ALPHA``, ``TARGET_BAND_HZ``, the separability rule, or the engine's
control construction — that is what keeps the test falsifiable. The QGITA quantities
are reused verbatim from ``aureon.wisdom`` (the real framework), not re-derived.

Pure stdlib + numpy + engine; the QGITA framework is imported lazily so this module
stays light and offline-safe.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from typing import Any

import numpy as np

import phenolic_fingerprint as engine
from aureon.bio.human_harmonic_proxy import (
    SCIENTIFIC_BOUNDARY,
    HumanSignal,
    ProxyResult,
    fold_to_band,
    score_signal,
)

__all__ = [
    "QGITACalibrationReport",
    "qgita_phi",
    "phi_lattice_tones",
    "fibonacci_lattice_numbers",
    "auris_frequencies_hz",
    "qgita_structured_tones",
    "calibrate_qgita",
    "score_qgita_auris",
    "main",
]


# ---------------------------------------------------------------------------
# reuse the REAL QGITA systems (lazy — keeps the module light / offline-safe)
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def qgita_phi() -> float:
    """QGITA's golden ratio, reused from the real framework (equals ``engine.PHI``)."""
    try:
        from aureon.wisdom.aureon_qgita_framework import PHI
        return float(PHI)
    except Exception:  # pragma: no cover - framework always present in-repo
        return float(engine.PHI)


@lru_cache(maxsize=1)
def fibonacci_lattice_numbers(max_k: int = 12) -> tuple[int, ...]:
    """Fibonacci numbers of QGITA's FibonacciTimeLattice (reused, positive Fₖ)."""
    from aureon.wisdom.aureon_qgita_framework import FibonacciTimeLattice

    lattice = FibonacciTimeLattice(max_k=max_k)
    return tuple(k.fib_number for k in lattice.knots if k.fib_number > 0)


@lru_cache(maxsize=1)
def auris_frequencies_hz() -> tuple[float, ...]:
    """The 9 Auris frequencies (Hz) defined by the QGITA trading engine (reused)."""
    from aureon.wisdom.aureon_qgita import CONFIG

    return tuple(sorted(float(v) for k, v in CONFIG.items() if k.startswith("FREQ_")))


def phi_lattice_tones(base_hz: float = 1000.0, n: int = 5) -> np.ndarray:
    """QGITA's golden lattice as a tone set: ``base·φ^k`` (pairwise ratios = φ powers).

    This is exactly the φ-scaling of QGITA's Fibonacci time lattice; every pairwise
    ratio is an integer power of φ, so the engine's Test B (φ-alignment) responds to
    it maximally. It is φ-aligned but not clustered — the golden-ratio signature on
    its own.
    """
    return base_hz * (qgita_phi() ** np.arange(int(n)))


def qgita_structured_tones(base_hz: float = 1000.0, n_centers: int = 4) -> np.ndarray:
    """A fully-structured QGITA reference: golden-lattice centres + tight clusters.

    Centres at ``base·φ^k`` (QGITA's lattice) each wrapped in a tight triple, so the
    set is both clustered (Test A) and φ-aligned (Test B) — the separable positive.
    Mirrors the engine's own ``_structured_positive_signal`` construction, sourced
    from QGITA's φ.
    """
    centers = base_hz * (qgita_phi() ** np.arange(int(n_centers)))
    offsets = np.array([-4.0, 0.0, 4.0])
    return np.sort((centers[:, None] + offsets[None, :]).ravel())


# ---------------------------------------------------------------------------
# calibration report + protocol (mirrors calibration.ControlCalibrationReport)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QGITACalibrationReport:
    """Empirical calibration of the φ engine against QGITA's golden lattice."""

    phi: float
    phi_shared_with_engine: bool
    n_lattice_tones: int
    envelope_hz: tuple[float, float]
    alpha: float
    n_nulls: int
    fpr_trials: int
    empirical_fpr_test_A: float
    empirical_fpr_test_B: float
    empirical_fpr_separable: float
    phi_lattice_alignment_p: float
    phi_lattice_detected: bool
    positive_control_p_A: float
    positive_control_p_B: float
    controls_valid: bool
    calibrated: bool
    notes: list[str] = field(default_factory=lambda: [])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def calibrate_qgita(
    *,
    base_hz: float = 1000.0,
    n_lattice: int = 5,
    nulls: int = 500,
    seed: int = 0,
    fpr_trials: int = 200,
) -> QGITACalibrationReport:
    """Validate the engine against QGITA's golden lattice — engine unchanged.

    Confirms (a) the engine's Test B detects QGITA's ``base·φ^k`` lattice, (b) at that
    lattice's scale an envelope-matched uniform null keeps the separable false-positive
    rate at/below ``ALPHA`` (with a Monte-Carlo margin), and (c) the engine's own
    positive/negative controls hold. ``calibrated`` requires all three. No engine
    threshold is touched.
    """
    lattice = phi_lattice_tones(base_hz, n_lattice)
    lo, hi = float(lattice.min()), float(lattice.max())

    # (a) does the engine's φ-alignment arm detect QGITA's golden lattice?
    phi_p = engine.test_B(lattice, nulls=nulls, rng=np.random.default_rng([seed, 2]))
    phi_detected = phi_p < engine.ALPHA

    # (b) envelope-matched random-null false-positive rate at the lattice's scale
    rng = np.random.default_rng([seed, 909])
    hits_a = hits_b = hits_sep = 0
    for trial in range(fpr_trials):
        draw = np.sort(rng.uniform(lo, hi, size=int(n_lattice)))
        pa = engine.test_A(draw, nulls=nulls, rng=np.random.default_rng([seed, 1, trial]))
        pb = engine.test_B(draw, nulls=nulls, rng=np.random.default_rng([seed, 2, trial]))
        hits_a += int(pa < engine.ALPHA)
        hits_b += int(pb < engine.ALPHA)
        hits_sep += int(pa < engine.ALPHA and pb < engine.ALPHA)
    fpr_a = hits_a / fpr_trials
    fpr_b = hits_b / fpr_trials
    fpr_sep = hits_sep / fpr_trials

    # (c) the engine's own controls
    pos = engine.positive_control(nulls=nulls, seed=seed)
    neg = engine.negative_control(nulls=nulls, seed=seed)

    se = (engine.ALPHA * (1 - engine.ALPHA) / fpr_trials) ** 0.5
    fpr_ceiling = engine.ALPHA + 3 * se
    calibrated = bool(
        phi_detected and fpr_sep <= fpr_ceiling and pos.passed and neg.passed
    )

    phi = qgita_phi()
    notes = [
        f"QGITA φ = {phi:.15g}; engine.PHI = {engine.PHI:.15g} (shared constant)",
        f"golden lattice = base·φ^k, base={base_hz} Hz, k=0..{n_lattice - 1}",
        f"null model = envelope-matched uniform draws in [{lo:.1f}, {hi:.1f}] Hz, n={n_lattice}",
        f"separable-FPR ceiling (ALPHA + 3*SE) = {fpr_ceiling:.4f}",
        "thresholds unchanged: ALPHA, TARGET_BAND_HZ, separability rule are pre-registered",
    ]
    if not phi_detected:
        notes.append("WARNING: engine did not detect the golden lattice — investigate")
    if fpr_sep > fpr_ceiling:
        notes.append("WARNING: separable false-positive rate exceeds ceiling")

    return QGITACalibrationReport(
        phi=phi,
        phi_shared_with_engine=(phi == float(engine.PHI)),
        n_lattice_tones=int(lattice.size),
        envelope_hz=(round(lo, 4), round(hi, 4)),
        alpha=engine.ALPHA,
        n_nulls=nulls,
        fpr_trials=fpr_trials,
        empirical_fpr_test_A=fpr_a,
        empirical_fpr_test_B=fpr_b,
        empirical_fpr_separable=fpr_sep,
        phi_lattice_alignment_p=phi_p,
        phi_lattice_detected=phi_detected,
        positive_control_p_A=pos.detail["test_A_p"],
        positive_control_p_B=pos.detail["test_B_p"],
        controls_valid=pos.passed and neg.passed,
        calibrated=calibrated,
        notes=notes,
    )


def score_qgita_auris(
    *,
    consent: bool = True,
    provenance: str | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan QGITA's 9 Auris frequencies through the governed pipeline (neutral)."""
    raw_hz = auris_frequencies_hz()
    tones = tuple(sorted(f for f in (fold_to_band(v) for v in raw_hz) if f is not None))
    signal = HumanSignal(
        label="qgita:auris",
        frequencies_hz=tones,
        provenance=provenance or "QGITA Auris frequencies (aureon.wisdom.aureon_qgita)",
        consent=consent,
        modality="qgita",
        notes="QGITA-defined Auris frequency set; derived-signal structure only",
    )
    return score_signal(signal, nulls=nulls, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """CLI: calibrate the φ engine against QGITA's golden lattice."""
    parser = argparse.ArgumentParser(
        description="Calibrate the phenolic φ engine against QGITA's golden-ratio lattice "
        "(engine thresholds unchanged)."
    )
    parser.add_argument("--base-hz", type=float, default=1000.0)
    parser.add_argument("--n-lattice", type=int, default=5)
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--trials", type=int, default=200, help="random-null FPR trials")
    parser.add_argument("--auris", action="store_true",
                        help="also scan QGITA's 9 Auris frequencies through the governed pipeline")
    args = parser.parse_args(argv)

    r = calibrate_qgita(base_hz=args.base_hz, n_lattice=args.n_lattice,
                        nulls=args.nulls, seed=args.seed, fpr_trials=args.trials)
    print("QGITA ⇄ phenolic-φ calibration (engine unchanged)")
    print(f"  φ shared with engine : {r.phi_shared_with_engine}  (φ={r.phi:.15g})")
    print(f"  golden lattice       : {r.n_lattice_tones} tones, envelope "
          f"{r.envelope_hz[0]}-{r.envelope_hz[1]} Hz")
    print(f"  φ-alignment detect   : p={r.phi_lattice_alignment_p:.4f}  "
          f"detected={r.phi_lattice_detected}")
    print(f"  empirical FPR        : test_A={r.empirical_fpr_test_A:.4f} "
          f"test_B={r.empirical_fpr_test_B:.4f} separable={r.empirical_fpr_separable:.4f}")
    print(f"  positive control p   : A={r.positive_control_p_A:.4f} B={r.positive_control_p_B:.4f}")
    print(f"  controls_valid={r.controls_valid}  CALIBRATED={r.calibrated}")
    for note in r.notes:
        print(f"    - {note}")

    if args.auris:
        a = score_qgita_auris(nulls=args.nulls, seed=args.seed).to_dict()
        print("  Auris scan (neutral) :")
        print(f"    boundary          : {SCIENTIFIC_BOUNDARY}")
        print(f"    n_tones={a['n_tones']} valid={a['valid']} "
              f"structure_present={a['structure_present']} "
              f"A_p={a['test_A_p']} B_p={a['test_B_p']}")

    return 0 if r.calibrated else 1


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
