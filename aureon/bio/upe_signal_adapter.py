#!/usr/bin/env python3
"""UPE signal adapter — ingest *real* ultraweak-photon-emission data.

This is the legitimate "field extraction" path: it scores **genuine UPE
measurements** — an emission spectrum (wavelength nm + intensity) or a photon-count
time-series — through the same governed phenolic pipeline. It does **not** accept a
photograph as UPE (a photo records reflected light, not biophotons), and it makes
**no** claim about any subject's health, state, emotion, relationships, or identity.

The honest anchor (see :mod:`aureon.bio.upe_reference`): a broadband, featureless
UPE spectrum has no discrete harmonic structure and therefore scores
**non-separable**. This adapter reproduces that — it reports structure only when the
data genuinely contains it (e.g. planted narrow emission lines), never by fiat.

Pure numpy + stdlib + the bio modules + engine. No import-time side effects.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

import phenolic_fingerprint as engine
from aureon.bio import upe_reference as upe
from aureon.bio.human_harmonic_proxy import (
    SCIENTIFIC_BOUNDARY,
    HumanSignal,
    ProxyResult,
    fold_to_band,
    score_signal,
)
from aureon.bio.image_signal_adapter import _wavelength_nm_to_hz

__all__ = [
    "UPESignalAdapter",
    "score_upe",
    "synthetic_upe",
    "main",
]

PHI: float = float(engine.PHI)


# ---------------------------------------------------------------------------
# emission-spectrum peak picking (nm / intensity; peaks are local maxima)
# ---------------------------------------------------------------------------


def _pick_emission_peaks(
    nm: np.ndarray,
    intensity: np.ndarray,
    *,
    min_prominence: float = 0.05,
    min_separation_nm: float = 1.0,
    max_peaks: int = 24,
) -> list[float]:
    """Return wavelengths (nm) of emission lines — strict local maxima of intensity.

    Intensity is normalised 0-1; a peak must rise at least ``min_prominence`` above
    the baseline. Peaks closer than ``min_separation_nm`` are merged (brighter kept).
    A flat/broadband spectrum yields no peaks — the honest non-structure result.
    """
    nm = np.asarray(nm, dtype=float)
    y = np.asarray(intensity, dtype=float)
    if nm.size < 3 or y.size != nm.size:
        return []
    lo, hi = float(np.min(y)), float(np.max(y))
    span = hi - lo
    if span <= 0:
        return []
    norm = (y - lo) / span

    cands: list[tuple[float, float]] = []  # (nm, height)
    for i in range(1, norm.size - 1):
        if norm[i] > norm[i - 1] and norm[i] >= norm[i + 1] and norm[i] >= min_prominence:
            cands.append((float(nm[i]), float(norm[i])))
    if not cands:
        return []
    cands.sort(key=lambda c: -c[1])  # brightest first
    kept: list[tuple[float, float]] = []
    for wl, ht in cands:
        if all(abs(wl - k[0]) >= min_separation_nm for k in kept):
            kept.append((wl, ht))
        if len(kept) >= max_peaks:
            break
    return sorted(wl for wl, _ in kept)


def _dominant_timeseries_hz(
    counts: np.ndarray,
    *,
    sample_rate_hz: float,
    min_prominence: float = 0.05,
    max_peaks: int = 24,
) -> list[float]:
    """Dominant temporal frequencies (Hz) of a photon-count series via real FFT."""
    x = np.asarray(counts, dtype=float)
    if x.size < 4 or sample_rate_hz <= 0:
        return []
    x = x - float(np.mean(x))
    freqs = np.fft.rfftfreq(x.size, d=1.0 / float(sample_rate_hz))
    power = np.abs(np.fft.rfft(x)) ** 2
    if freqs.size < 3 or float(np.max(power)) <= 0:
        return []
    norm = power / float(np.max(power))
    picks: list[tuple[float, float]] = []
    for i in range(1, norm.size - 1):
        if norm[i] > norm[i - 1] and norm[i] >= norm[i + 1] and norm[i] >= min_prominence and freqs[i] > 0:
            picks.append((float(freqs[i]), float(norm[i])))
    picks.sort(key=lambda p: -p[1])
    return sorted(f for f, _ in picks[:max_peaks])


# ---------------------------------------------------------------------------
# loading real UPE data
# ---------------------------------------------------------------------------


def _load_spectrum(spec: Any) -> tuple[np.ndarray, np.ndarray]:
    """Load (wavelength_nm, intensity) from a CSV path / 2-col array / list of tuples."""
    if isinstance(spec, (str, Path)):
        nm_vals: list[float] = []
        iv: list[float] = []
        with Path(spec).open("r", newline="", encoding="utf-8") as fh:
            reader = csv.reader(fh)
            for row in reader:
                if len(row) < 2:
                    continue
                try:
                    a, b = float(row[0]), float(row[1])
                except ValueError:
                    continue  # header / comment line
                nm_vals.append(a)
                iv.append(b)
        return np.array(nm_vals), np.array(iv)
    arr = np.asarray(spec, dtype=float)
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError("spectrum must be an (N,2) array of (wavelength_nm, intensity)")
    return arr[:, 0], arr[:, 1]


# ---------------------------------------------------------------------------
# adapter
# ---------------------------------------------------------------------------


class UPESignalAdapter:
    """Extract a derived signal from real UPE data (spectrum or photon-count series).

    Implements the :class:`aureon.bio.human_harmonic_proxy.SignalAdapter` seam.
    Consent + provenance are required arguments — the adapter never fabricates them.
    """

    modality: str = "upe"

    def extract(
        self,
        spec: Any,
        *,
        consent: bool,
        provenance: str,
        kind: str = "spectrum",
        sample_rate_hz: float | None = None,
        max_peaks: int = 24,
    ) -> HumanSignal:
        """Return a :class:`HumanSignal` (modality='upe') of folded modulation tones."""
        if kind == "spectrum":
            nm, intensity = _load_spectrum(spec)
            wavelengths = _pick_emission_peaks(nm, intensity, max_peaks=max_peaks)
            raw_hz = [_wavelength_nm_to_hz(wl) for wl in wavelengths]
            note = f"{len(wavelengths)} UPE emission line(s)"
        elif kind == "timeseries":
            if sample_rate_hz is None:
                raise ValueError("sample_rate_hz is required for kind='timeseries'")
            counts = np.asarray(spec, dtype=float) if not isinstance(spec, (str, Path)) else \
                np.loadtxt(spec, delimiter=",")
            raw_hz = _dominant_timeseries_hz(counts.ravel(), sample_rate_hz=sample_rate_hz, max_peaks=max_peaks)
            note = f"{len(raw_hz)} dominant photon-count mode(s)"
        else:  # pragma: no cover - guarded by callers
            raise ValueError(f"unknown kind {kind!r}; expected 'spectrum' or 'timeseries'")

        tones = tuple(sorted(f for f in (fold_to_band(v) for v in raw_hz) if f is not None))
        return HumanSignal(
            label=f"upe:{kind}",
            frequencies_hz=tones,
            provenance=provenance,
            consent=consent,
            modality=self.modality,
            notes=f"{note}; derived-signal structure only, not a claim about any subject",
        )


def score_upe(
    spec: Any,
    *,
    consent: bool,
    provenance: str,
    kind: str = "spectrum",
    sample_rate_hz: float | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Extract real UPE data and score it through the governed pipeline."""
    signal = UPESignalAdapter().extract(
        spec, consent=consent, provenance=provenance, kind=kind, sample_rate_hz=sample_rate_hz
    )
    return score_signal(signal, nulls=nulls, seed=seed)


# ---------------------------------------------------------------------------
# synthetic self-test (no real subject)
# ---------------------------------------------------------------------------


def _fold_band_vec(f_hz: np.ndarray) -> np.ndarray:
    """Vectorised octave-fold of positive Hz into ``TARGET_BAND_HZ`` [1000, 2000)."""
    k = np.floor(np.log2(f_hz / 1000.0))
    return f_hz / (2.0 ** k)


def _wavelengths_for_tones(targets: list[float]) -> list[float]:
    """Find UPE-band wavelengths (nm) that octave-fold to the given modulation tones.

    The nm->Hz->fold transform is many-to-one, so for each target modulation tone a
    wavelength in [200, 800] nm exists whose folded frequency matches it. A fine grid
    search returns the closest wavelength per target — used only to build a *synthetic*
    structured spectrum whose folded tones equal a known-separable set.
    """
    low, high = upe.UPE_BAND_NM
    grid = np.linspace(low, high, 400_001)
    f = (engine.NM_TO_THZ_NUMERATOR / grid) * engine.THZ_TO_HZ
    folded = _fold_band_vec(f)
    return [float(grid[int(np.argmin(np.abs(folded - t)))]) for t in targets]


def synthetic_upe(kind: str = "broadband", *, seed: int = 0, n: int = 241) -> np.ndarray:
    """Return an (N,2) synthetic UPE spectrum for the self-test (no real subject).

    ``broadband`` = the cited featureless UPE reference (must score non-separable).
    ``structured`` = broadband + planted narrow emission lines whose *folded*
    modulation tones equal a known clustered + PHI-spaced set (must score
    structure_present) — proving the adapter detects real structure, not by fiat.
    """
    base = np.array(upe.reference_spectrum(n), dtype=float)  # (n,2): nm, intensity
    if kind == "broadband":
        return base
    if kind == "structured":
        # Two tight clusters one golden ratio apart in the *modulation* band; back-solve
        # the wavelengths that fold to them, then plant sharp emission lines there.
        centers = 1100.0 * np.array([1.0, PHI])
        offsets = np.array([-8.0, 0.0, 8.0])  # within-cluster spread (< 25 Hz tolerance)
        target_tones = list((centers[:, None] + offsets[None, :]).ravel())
        line_nm = _wavelengths_for_tones(target_tones)
        # dense wavelength axis so the sharp lines are resolved as local maxima
        nm = np.linspace(upe.UPE_BAND_NM[0], upe.UPE_BAND_NM[1], 4000)
        y = np.interp(nm, base[:, 0], base[:, 1])  # broadband continuum
        for c in line_nm:
            y = y + 0.9 * np.exp(-((nm - c) ** 2) / (2.0 * 0.4 ** 2))  # sharp emission line
        return np.column_stack([nm, y])
    raise ValueError(f"unknown synthetic kind {kind!r}")


def main(argv: list[str] | None = None) -> int:
    """CLI: score a real UPE spectrum, or run the synthetic self-test."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Score real UPE data (emission spectrum / photon-count series); derived-signal structure only."
    )
    parser.add_argument("spectrum", nargs="?", help="CSV of wavelength_nm,intensity (real UPE measurement)")
    parser.add_argument("--consent", action="store_true")
    parser.add_argument("--provenance", default="")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true", help="run broadband⇒absent / structured⇒present demo")
    args = parser.parse_args(argv)

    print("UPE signal adapter — real UPE data only (not a photograph)")
    print(f"  boundary: {SCIENTIFIC_BOUNDARY}")

    if args.self_test:
        prov = "synthetic UPE self-test (no real subject)"
        broadband = score_upe(synthetic_upe("broadband"), consent=True, provenance=prov,
                              nulls=args.nulls, seed=args.seed)
        structured = score_upe(synthetic_upe("structured"), consent=True, provenance=prov,
                              nulls=args.nulls, seed=args.seed)
        checks = [
            (broadband.valid and not broadband.structure_present,
             "broadband UPE reference -> structure ABSENT (honest anchor)"),
            (structured.valid and structured.structure_present,
             "structured (planted lines)  -> structure PRESENT"),
            (broadband.boundary == SCIENTIFIC_BOUNDARY,
             "scientific boundary present"),
        ]
        ok = True
        for passed, label in checks:
            ok = ok and passed
            print(f"  {'✅' if passed else '❌'} {label}")
        print(f"  broadband:  A_p={broadband.test_A_p} B_p={broadband.test_B_p} n_tones={broadband.n_tones}")
        print(f"  structured: A_p={structured.test_A_p} B_p={structured.test_B_p} n_tones={structured.n_tones}")
        return 0 if ok else 1

    if not args.spectrum:
        parser.error("provide a spectrum CSV, or use --self-test")
    result = score_upe(args.spectrum, consent=bool(args.consent), provenance=args.provenance,
                       nulls=args.nulls, seed=args.seed)
    d = result.to_dict()
    print(f"  n_tones          : {d['n_tones']}")
    print(f"  valid / blocked  : {d['valid']} / {d['blocked']}")
    print(f"  structure_present: {d['structure_present']}")
    print(f"  test_A_p/test_B_p: {d['test_A_p']} / {d['test_B_p']}")
    print(f"  reason           : {d['reason']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
