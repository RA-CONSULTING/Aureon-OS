#!/usr/bin/env python3
"""Sky signal adapter — scan light directed at us from space through the engine.

Points the *same* phenolic engine (φ logic unchanged) at astronomical light: a
spectral line list (nm), a full emission/absorption spectrum (CSV
``wavelength_nm,intensity``), or radio frequencies (Hz, e.g. the 21 cm line). The
scan runs through the identical governed pipeline every other adapter uses
(``score_signal``: controls → Test A / Test B → separability at ``ALPHA``), and
reports whatever the pre-registered test returns.

Real open catalogs ship with it (``sky_reference``): hydrogen Balmer series and the
solar Fraunhofer lines, plus the 21 cm hydrogen line. Nothing about the engine is
modified; this module only feeds it sky light and reports the result.

Pure stdlib + numpy + the engine. No astropy/skyfield dependency — a line list or a
CSV is enough. Optical wavelengths and radio Hz both fold cleanly into the
modulation band.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np

import phenolic_fingerprint as engine
from aureon.bio import sky_reference as sky
from aureon.bio.human_harmonic_proxy import (
    SCIENTIFIC_BOUNDARY,
    HumanSignal,
    ProxyResult,
    fold_to_band,
    score_signal,
)
from aureon.bio.image_signal_adapter import _wavelength_nm_to_hz
from aureon.bio.upe_signal_adapter import _pick_emission_peaks

__all__ = [
    "SkySignalAdapter",
    "score_sky",
    "score_catalog",
    "score_diffuse",
    "main",
]


def _load_spectrum(spec: Any) -> tuple[np.ndarray, np.ndarray]:
    """Load (wavelength_nm, intensity) from a CSV path / 2-col array / list of tuples."""
    if isinstance(spec, (str, Path)):
        nm_vals: list[float] = []
        iv: list[float] = []
        with Path(spec).open("r", newline="", encoding="utf-8") as fh:
            for row in csv.reader(fh):
                if len(row) < 2:
                    continue
                try:
                    a, b = float(row[0]), float(row[1])
                except ValueError:
                    continue  # header / comment
                nm_vals.append(a)
                iv.append(b)
        return np.array(nm_vals), np.array(iv)
    arr = np.asarray(spec, dtype=float)
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError("spectrum must be an (N,2) array of (wavelength_nm, intensity)")
    return arr[:, 0], arr[:, 1]


class SkySignalAdapter:
    """Extract a derived signal from astronomical light (lines / spectrum / radio Hz).

    Implements the :class:`aureon.bio.human_harmonic_proxy.SignalAdapter` seam.
    Consent + provenance are required arguments (never fabricated); for public sky
    catalogs, consent is simply the operator affirming the scan.
    """

    modality: str = "sky"

    def extract(
        self,
        spec: Any,
        *,
        consent: bool,
        provenance: str,
        kind: str = "lines",
        max_peaks: int = 40,
    ) -> HumanSignal:
        """Return a :class:`HumanSignal` (modality='sky') of folded modulation tones.

        ``kind='lines'``  : ``spec`` is an iterable of wavelengths in nm.
        ``kind='spectrum'``: ``spec`` is a CSV/array of (wavelength_nm, intensity).
        ``kind='radio_hz'``: ``spec`` is an iterable of frequencies already in Hz.
        """
        if kind == "lines":
            raw_hz = [_wavelength_nm_to_hz(float(w)) for w in spec]
            note = f"{len(list(spec)) if hasattr(spec, '__len__') else len(raw_hz)} sky line(s)"
        elif kind == "spectrum":
            nm, intensity = _load_spectrum(spec)
            wavelengths = _pick_emission_peaks(nm, intensity, max_peaks=max_peaks)
            raw_hz = [_wavelength_nm_to_hz(w) for w in wavelengths]
            note = f"{len(wavelengths)} sky spectral line(s)"
        elif kind == "radio_hz":
            raw_hz = [float(f) for f in spec]
            note = f"{len(raw_hz)} radio frequency line(s)"
        else:  # pragma: no cover - guarded by callers
            raise ValueError(f"unknown kind {kind!r}; expected 'lines', 'spectrum', or 'radio_hz'")

        tones = tuple(sorted(f for f in (fold_to_band(v) for v in raw_hz) if f is not None))
        return HumanSignal(
            label=f"sky:{kind}",
            frequencies_hz=tones,
            provenance=provenance,
            consent=consent,
            modality=self.modality,
            notes=f"{note}; light directed at us from space, scanned through the same engine",
        )


def score_sky(
    spec: Any,
    *,
    consent: bool,
    provenance: str,
    kind: str = "lines",
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan sky light and score it through the governed pipeline."""
    signal = SkySignalAdapter().extract(spec, consent=consent, provenance=provenance, kind=kind)
    return score_signal(signal, nulls=nulls, seed=seed)


def score_catalog(
    name: str,
    *,
    consent: bool = True,
    provenance: str | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan a named real catalog ('balmer', 'fraunhofer', 'airglow') through the engine."""
    lines = sky.catalog_nm(name)
    citation = sky.AIRGLOW_CITATION if name == "airglow" else sky.SKY_CITATION
    prov = provenance or f"open catalog: {name} ({citation})"
    return score_sky(lines, consent=consent, provenance=prov, kind="lines", nulls=nulls, seed=seed)


def score_diffuse(
    *,
    consent: bool = True,
    provenance: str | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan the diffuse night-sky background (featureless UPE-from-the-sky anchor)."""
    prov = provenance or "diffuse night-sky background (featureless reference)"
    return score_sky(sky.diffuse_night_sky_spectrum(), consent=consent, provenance=prov,
                     kind="spectrum", nulls=nulls, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """CLI: scan a real sky catalog, a spectrum CSV, or run the control self-test."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Scan light directed at space through the phenolic engine (φ logic unchanged)."
    )
    parser.add_argument("spectrum", nargs="?", help="CSV of wavelength_nm,intensity (a sky spectrum)")
    parser.add_argument("--catalog", choices=["balmer", "fraunhofer", "airglow"],
                        help="scan a real named catalog")
    parser.add_argument("--consent", action="store_true")
    parser.add_argument("--provenance", default="")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--self-test", action="store_true",
                        help="control self-test: featureless continuum + planted-structure references")
    parser.add_argument("--faint-sky", action="store_true",
                        help="UPE-from-the-sky: scan real airglow lines + the diffuse background")
    args = parser.parse_args(argv)

    print("Sky signal adapter — scanning light directed at us from space")
    print(f"  boundary: {SCIENTIFIC_BOUNDARY}")
    print(f"  data:     {sky.SKY_CITATION}")

    if args.self_test:
        prov = "sky control self-test"
        continuum = score_sky(sky.continuum_spectrum(), consent=True, provenance=prov,
                             kind="spectrum", nulls=args.nulls, seed=args.seed)
        structured = score_sky(sky.structured_spectrum(), consent=True, provenance=prov,
                             kind="spectrum", nulls=args.nulls, seed=args.seed)
        checks = [
            (continuum.valid and not continuum.structure_present,
             "featureless continuum -> negative control does NOT over-fire"),
            (structured.valid and structured.structure_present,
             "planted coherence     -> positive control detected"),
            (continuum.boundary == SCIENTIFIC_BOUNDARY, "boundary present"),
        ]
        ok = True
        for passed, label in checks:
            ok = ok and passed
            print(f"  {'✅' if passed else '❌'} {label}")
        print(f"  continuum:  A_p={continuum.test_A_p} B_p={continuum.test_B_p}")
        print(f"  structured: A_p={structured.test_A_p} B_p={structured.test_B_p}")
        return 0 if ok else 1

    if args.faint_sky:
        # UPE-from-the-sky: the sky's real faint self-emission (airglow lines) +
        # the featureless diffuse background anchor. UPE proper is biological; this is
        # the honest astronomical analog. Verdicts reported exactly as the engine returns.
        print(f"  airglow:  {sky.AIRGLOW_CITATION}")
        airglow = score_catalog("airglow", consent=True, nulls=args.nulls, seed=args.seed)
        diffuse = score_diffuse(consent=True, nulls=args.nulls, seed=args.seed)
        ad = airglow.to_dict()
        dd = diffuse.to_dict()
        print(f"  ✅ airglow lines scanned : n_tones={ad['n_tones']} valid={ad['valid']} "
              f"structure_present={ad['structure_present']} A_p={ad['test_A_p']} B_p={ad['test_B_p']}")
        anchor_ok = diffuse.valid and not diffuse.structure_present
        print(f"  {'✅' if anchor_ok else '❌'} diffuse background      : featureless anchor "
              f"non-separable (n_tones={dd['n_tones']}, structure_present={dd['structure_present']})")
        return 0 if (airglow.valid and anchor_ok) else 1

    if args.catalog:
        result = score_catalog(args.catalog, consent=True, nulls=args.nulls, seed=args.seed)
        label = f"catalog:{args.catalog}"
    elif args.spectrum:
        result = score_sky(args.spectrum, consent=bool(args.consent), provenance=args.provenance,
                          kind="spectrum", nulls=args.nulls, seed=args.seed)
        label = args.spectrum
    else:
        parser.error("provide a spectrum CSV, or --catalog balmer|fraunhofer, or --self-test")

    d = result.to_dict()
    print(f"  scan             : {label}")
    print(f"  n_tones          : {d['n_tones']}")
    print(f"  valid / blocked  : {d['valid']} / {d['blocked']}")
    print(f"  structure_present: {d['structure_present']}")
    print(f"  test_A_p/test_B_p: {d['test_A_p']} / {d['test_B_p']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
