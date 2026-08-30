#!/usr/bin/env python3
"""Scan real NASA host-star data through the phenolic engine (φ logic unchanged).

Reads the cached NASA Exoplanet Archive snapshot
(``data/sky/nasa_exoplanet_hosts.csv``, fetched by ``fetch_nasa_sky_data.py``)
and runs it through the *same* sky adapter every other light-from-space scan
uses. Two honest lanes, both straight into the unchanged engine:

  Lane 1 — starlight colour (spectral).  Host-star effective temperature
      ``st_teff`` (K) -> Wien's-law peak wavelength ``λ_peak(nm) = 2.897771955e6 / T``
      -> ``SkySignalAdapter.extract(kind="lines")``.
  Lane 2 — planetary rhythm (radio_hz).  Orbital period ``pl_orbper`` (days)
      -> frequency ``Hz = 1 / (period · 86400)`` -> ``extract(kind="radio_hz")``
      (``fold_to_band`` folds the tiny orbital Hz up into the modulation band).

Nothing about the engine is modified; the scan verdict (valid, n_tones,
structure_present, Test A/B p-values) is printed exactly as the pre-registered
test returns it. This driver is offline by default (reads the committed cache);
``--fetch`` refreshes the cache from NASA first.

Run:
    python scripts/validation/benchmark_nasa_sky.py
    python scripts/validation/benchmark_nasa_sky.py --fetch     # refresh cache
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.validation.fetch_nasa_sky_data import (  # noqa: E402
    DEFAULT_CACHE,
    SOURCE_CITATION,
    read_cache,
)

#: Wien's displacement constant expressed for nm·K (b = 2.897771955e-3 m·K).
WIEN_NM_K: Final[float] = 2.897771955e6
SECONDS_PER_DAY: Final[float] = 86_400.0


def stellar_peak_wavelengths_nm(rows: list[dict[str, str]]) -> list[float]:
    """Wien peak wavelength (nm) for each host star's effective temperature."""
    out: list[float] = []
    for r in rows:
        try:
            teff = float(r["st_teff"])
        except (KeyError, ValueError):
            continue
        if teff > 0:
            out.append(WIEN_NM_K / teff)
    return out


def orbital_frequencies_hz(rows: list[dict[str, str]]) -> list[float]:
    """Orbital frequency (Hz) for each planet's period (days)."""
    out: list[float] = []
    for r in rows:
        try:
            period_days = float(r["pl_orbper"])
        except (KeyError, ValueError):
            continue
        if period_days > 0:
            out.append(1.0 / (period_days * SECONDS_PER_DAY))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Scan real NASA host-star data through the phenolic engine (φ logic unchanged)."
    )
    parser.add_argument("--cache", default=str(DEFAULT_CACHE), help="cached NASA CSV path")
    parser.add_argument("--fetch", action="store_true", help="refresh the cache from NASA first")
    parser.add_argument("--nulls", type=int, default=500)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    from aureon.bio.human_harmonic_proxy import SCIENTIFIC_BOUNDARY
    from aureon.bio.sky_signal_adapter import score_sky

    if args.fetch:
        from scripts.validation.fetch_nasa_sky_data import fetch_rows, write_cache

        try:
            write_cache(fetch_rows(), args.cache)
            print("refreshed cache from NASA", file=sys.stderr)
        except Exception as exc:  # network optional; fall back to committed cache
            print(f"fetch failed ({exc}); using committed cache", file=sys.stderr)

    try:
        rows = read_cache(args.cache)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    wavelengths = stellar_peak_wavelengths_nm(rows)
    frequencies = orbital_frequencies_hz(rows)
    prov = f"NASA cache {Path(args.cache).name}: {SOURCE_CITATION}"

    print("NASA sky scan — real host-star data through the engine (φ logic unchanged)")
    print(f"  boundary: {SCIENTIFIC_BOUNDARY}")
    print(f"  data:     {SOURCE_CITATION}")
    print(f"  rows:     {len(rows)} confirmed planets")

    ok = True
    lanes = (
        ("stellar Wien wavelengths (starlight colour)", wavelengths, "lines"),
        ("orbital-period frequencies (planetary rhythm)", frequencies, "radio_hz"),
    )
    for label, values, kind in lanes:
        if not values:
            print(f"  ❌ {label}: no usable values")
            ok = False
            continue
        result = score_sky(values, consent=True, provenance=prov, kind=kind,
                           nulls=args.nulls, seed=args.seed)
        d = result.to_dict()
        mark = "✅" if d["valid"] else "❌"
        ok = ok and bool(d["valid"])
        print(f"  {mark} {label}")
        print(f"       inputs={len(values)}  n_tones={d['n_tones']}  "
              f"valid={d['valid']}  structure_present={d['structure_present']}")
        print(f"       test_A_p={d['test_A_p']}  test_B_p={d['test_B_p']}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
