#!/usr/bin/env python3
"""Coherence scan — direct the repo's DE440 coherence spectrum at the engine.

The repo already computed a frequency-domain coherence spectrum of the DE440 planetary
timeseries (``data/de440_gate3_coherence.csv``, ``freq_hz,coherence``) — but nothing
consumed it. This lane picks the highest-coherence frequency bins, folds them into the
modulation band, and scans them through the **unchanged** phenolic φ engine via the
identical governed pipeline (``score_signal``: controls → Test A / Test B →
separability at ``ALPHA`` → Operator/conscience veto → ``SCIENTIFIC_BOUNDARY``).
Nothing about the engine is modified; the verdict is reported exactly as the test
returns it. ``data/sim_gate3_coherence.csv`` is the simulated control.

Pure stdlib + numpy + engine. No network. Reuses ``fold_to_band`` / ``score_signal``.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Final

import numpy as np

import phenolic_fingerprint as engine
from aureon.bio.human_harmonic_proxy import (
    HumanSignal,
    ProxyResult,
    fold_to_band,
    score_signal,
)

__all__ = [
    "COHERENCE_CITATION",
    "load_coherence",
    "coherence_peak_tones",
    "score_coherence",
    "main",
]

COHERENCE_CITATION: Final[str] = (
    "DE440 planetary-timeseries coherence spectrum (freq_hz,coherence); "
    "repo-computed gate3 analysis (data/de440_gate3_coherence.csv; "
    "sim control data/sim_gate3_coherence.csv)."
)

_DEFAULT_COHERENCE: Final[str] = "data/de440_gate3_coherence.csv"
_SIM_COHERENCE: Final[str] = "data/sim_gate3_coherence.csv"


def load_coherence(path: str | Path = _DEFAULT_COHERENCE) -> tuple[np.ndarray, np.ndarray]:
    """Load (freq_hz, coherence) from a gate3 coherence CSV."""
    freqs: list[float] = []
    cohs: list[float] = []
    with Path(path).open("r", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                f, c = float(row["freq_hz"]), float(row["coherence"])
            except (KeyError, ValueError, TypeError):
                continue
            freqs.append(f)
            cohs.append(c)
    return np.array(freqs), np.array(cohs)


def coherence_peak_tones(
    path: str | Path = _DEFAULT_COHERENCE,
    *,
    top_k: int = 32,
    min_coherence: float = 0.0,
) -> tuple[float, ...]:
    """Fold the highest-coherence frequency bins into the modulation band.

    Selects the ``top_k`` positive-frequency bins with the greatest coherence (above
    ``min_coherence``), folds each into ``[1000, 2000)`` Hz, and returns the sorted,
    de-duplicated tone set.
    """
    freqs, cohs = load_coherence(path)
    if freqs.size == 0:
        return ()
    mask = (freqs > 0) & (cohs >= float(min_coherence))
    freqs, cohs = freqs[mask], cohs[mask]
    if freqs.size == 0:
        return ()
    order = np.argsort(cohs)[::-1][: int(top_k)]
    picks = freqs[order]
    tones = {t for t in (fold_to_band(float(f)) for f in picks) if t is not None}
    return tuple(sorted(tones))


def score_coherence(
    path: str | Path = _DEFAULT_COHERENCE,
    *,
    consent: bool = True,
    provenance: str | None = None,
    top_k: int = 32,
    min_coherence: float = 0.0,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan the coherence-peak tones through the governed pipeline (neutral)."""
    tones = coherence_peak_tones(path, top_k=top_k, min_coherence=min_coherence)
    signal = HumanSignal(
        label="coherence:gate3",
        frequencies_hz=tones,
        provenance=provenance or f"coherence spectrum ({COHERENCE_CITATION})",
        consent=consent,
        modality="sky",
        notes="DE440 coherence-peak tones; derived-signal structure only",
    )
    return score_signal(signal, nulls=nulls, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """CLI: scan the real DE440 coherence spectrum (and the sim control)."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Scan the repo's DE440 coherence spectrum through the phenolic engine "
        "(φ logic unchanged)."
    )
    parser.add_argument("--path", default=_DEFAULT_COHERENCE)
    parser.add_argument("--sim", action="store_true", help="also scan the sim control")
    parser.add_argument("--top-k", type=int, default=32)
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    print("Coherence scan — DE440 coherence spectrum through the engine (φ logic unchanged)")
    print(f"  data: {COHERENCE_CITATION}")

    def _report(label, result):
        d = result.to_dict()
        print(f"  {label:12s}: n_tones={d['n_tones']} valid={d['valid']} "
              f"structure_present={d['structure_present']} "
              f"A_p={d['test_A_p']} B_p={d['test_B_p']}")

    _report("de440", score_coherence(args.path, top_k=args.top_k, nulls=args.nulls, seed=args.seed))
    if args.sim:
        _report("sim (ctrl)", score_coherence(_SIM_COHERENCE, top_k=args.top_k,
                                              nulls=args.nulls, seed=args.seed))
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
