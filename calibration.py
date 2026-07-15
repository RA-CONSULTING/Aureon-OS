#!/usr/bin/env python3
"""Calibration — validate the engine's controls and null model on real data.

The Phenolic Fingerprint engine ships with *pre-registered* decision thresholds
(``ALPHA``), a fixed null model (envelope-matched random frequencies), and
constructed positive/negative controls. Those must not be tuned to a dataset —
that is what keeps the test falsifiable. What we *can* do, honestly, is
**calibrate by validation**: confirm that at a given dataset's real scale (its
peak-count distribution and modulation-frequency envelope) the null model still
produces a false-positive rate at or below ``ALPHA`` and the positive control
still detects. This module measures exactly that and reports it. It never
changes ``ALPHA``, the separability rule, or the engine's control construction.

Use it after enriching a dataset (e.g. with fetcher-derived NIST peaks) to show
that the enrichment did not break the calibration of the pre-registered test.

Pure standard library + numpy + the connector/engine. Deterministic given seed.
"""

from __future__ import annotations

import argparse
import statistics
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

import connector
import phenolic_fingerprint as engine

__all__ = ["ControlCalibrationReport", "calibrate", "main"]


@dataclass(frozen=True)
class ControlCalibrationReport:
    """Empirical calibration of the pre-registered controls on one dataset."""

    n_compounds: int
    n_peaks: int
    median_peaks_per_compound: int
    envelope_hz: tuple[float, float]
    alpha: float
    n_nulls: int
    fpr_trials: int
    empirical_fpr_test_A: float
    empirical_fpr_test_B: float
    empirical_fpr_separable: float
    positive_control_p_A: float
    positive_control_p_B: float
    controls_valid: bool
    calibrated: bool
    notes: list[str] = field(default_factory=lambda: [])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _modulation_hz_by_compound(sources: list[str | Path]) -> dict[str, np.ndarray]:
    """Ingest + validate sources, returning modulation-Hz arrays per compound."""
    raw, _ = connector.ingest_many(list(sources)) if isinstance(sources, list) else connector.ingest(sources)
    accepted, _ = connector.validate(raw)
    by: dict[str, list[float]] = {}
    for row in accepted:
        by.setdefault(row.molecule, []).append(
            engine.peak_to_modulation_hz(row.peak_value, row.unit)
        )
    return {k: np.array(sorted(v)) for k, v in by.items()}


def calibrate(
    sources: list[str | Path],
    *,
    nulls: int = 500,
    seed: int = 0,
    fpr_trials: int = 200,
) -> ControlCalibrationReport:
    """Measure the engine's false-positive rate and power at a dataset's scale.

    Draws ``fpr_trials`` synthetic random-frequency "compounds" matched to the
    dataset's median peak count and global modulation-frequency envelope, runs
    the engine's *unchanged* test_A / test_B on each, and reports the fraction
    flagged significant at ``ALPHA`` (the empirical false-positive rate). Also
    runs the pre-registered positive control for power. ``calibrated`` is True
    when the empirical separable-FPR sits at or below ``ALPHA`` (with a small
    Monte-Carlo margin) and the positive control detects.
    """
    by = _modulation_hz_by_compound(sources)
    counts = [len(v) for v in by.values() if len(v) >= 2]
    if not counts:
        raise ValueError("no compound has >= 2 validated peaks; cannot calibrate")
    all_freqs = np.concatenate([v for v in by.values() if v.size])
    lo, hi = float(all_freqs.min()), float(all_freqs.max())
    median_n = int(statistics.median(counts))

    rng = np.random.default_rng([seed, 909])
    hits_a = hits_b = hits_sep = 0
    for trial in range(fpr_trials):
        draw = np.sort(rng.uniform(lo, hi, size=median_n))
        pa = engine.test_A(draw, nulls=nulls, rng=np.random.default_rng([seed, 1, trial]))
        pb = engine.test_B(draw, nulls=nulls, rng=np.random.default_rng([seed, 2, trial]))
        hits_a += int(pa < engine.ALPHA)
        hits_b += int(pb < engine.ALPHA)
        hits_sep += int(pa < engine.ALPHA and pb < engine.ALPHA)

    fpr_a = hits_a / fpr_trials
    fpr_b = hits_b / fpr_trials
    fpr_sep = hits_sep / fpr_trials

    pos = engine.positive_control(nulls=nulls, seed=seed)
    neg = engine.negative_control(nulls=nulls, seed=seed)

    # Monte-Carlo margin: allow up to ALPHA + 3 SE of a Bernoulli(ALPHA) estimate.
    se = (engine.ALPHA * (1 - engine.ALPHA) / fpr_trials) ** 0.5
    fpr_ceiling = engine.ALPHA + 3 * se
    calibrated = fpr_sep <= fpr_ceiling and pos.passed and neg.passed

    notes = [
        f"null model = envelope-matched uniform draws in [{lo:.1f}, {hi:.1f}] Hz, "
        f"n={median_n} tones (dataset median)",
        f"separable-FPR ceiling (ALPHA + 3*SE) = {fpr_ceiling:.4f}",
        "thresholds unchanged: ALPHA and separability rule are pre-registered",
    ]
    if fpr_sep > fpr_ceiling:
        notes.append("WARNING: separable false-positive rate exceeds ceiling — investigate null model")

    return ControlCalibrationReport(
        n_compounds=len(by),
        n_peaks=int(all_freqs.size),
        median_peaks_per_compound=median_n,
        envelope_hz=(round(lo, 4), round(hi, 4)),
        alpha=engine.ALPHA,
        n_nulls=nulls,
        fpr_trials=fpr_trials,
        empirical_fpr_test_A=fpr_a,
        empirical_fpr_test_B=fpr_b,
        empirical_fpr_separable=fpr_sep,
        positive_control_p_A=pos.detail["test_A_p"],
        positive_control_p_B=pos.detail["test_B_p"],
        controls_valid=pos.passed and neg.passed,
        calibrated=calibrated,
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI: ``calibration.py <source...> [--nulls N] [--seed S] [--trials T]``."""
    parser = argparse.ArgumentParser(
        description="Validate the engine's controls/null model at a dataset's scale."
    )
    parser.add_argument("sources", nargs="+", help="CSV/zip paths to calibrate against (merged)")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--trials", type=int, default=200, help="Random-compound FPR trials")
    args = parser.parse_args(argv)

    try:
        report = calibrate(args.sources, nulls=args.nulls, seed=args.seed, fpr_trials=args.trials)
    except (connector.ConnectorError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    r = report
    print("Control / null calibration")
    print(f"  dataset: {r.n_compounds} compounds, {r.n_peaks} peaks, "
          f"median {r.median_peaks_per_compound} peaks/compound")
    print(f"  modulation envelope: {r.envelope_hz[0]}-{r.envelope_hz[1]} Hz")
    print(f"  alpha={r.alpha}  nulls={r.n_nulls}  fpr_trials={r.fpr_trials}")
    print(f"  empirical FPR  test_A={r.empirical_fpr_test_A:.4f}  "
          f"test_B={r.empirical_fpr_test_B:.4f}  separable={r.empirical_fpr_separable:.4f}")
    print(f"  positive control p: A={r.positive_control_p_A:.4f} B={r.positive_control_p_B:.4f}")
    print(f"  controls_valid={r.controls_valid}  CALIBRATED={r.calibrated}")
    for note in r.notes:
        print(f"    - {note}")
    return 0 if report.calibrated else 1


if __name__ == "__main__":
    raise SystemExit(main())
