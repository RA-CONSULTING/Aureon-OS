#!/usr/bin/env python3
"""Build the Aureon sky map — the harmonic sensors, pointed at the sky.

Reads the committed real sky data offline (NASA Exoplanet Archive host stars with
RA/Dec + the DE440 planetary ephemeris) and maps φ-structure across the sky through
the **unchanged** phenolic engine, rendering an RA/Dec heatmap PNG. Two lanes:

  Stellar   — host stars binned by RA/Dec, each folding its Wien colour (st_teff).
  Planetary — DE440 planets painting their orbital-motion tones along the ecliptic.

Offline by default (committed cache + committed ephemeris). ``--fetch`` refreshes the
NASA cache from the keyless Exoplanet Archive TAP first. Verdicts are printed exactly
as the engine returns them; nothing about the engine is modified.

Run:
    python scripts/validation/build_sky_map.py --both --out sky_map.png
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Map φ-structure across the sky from real NASA + DE440 data (engine unchanged)."
    )
    parser.add_argument("--stellar", action="store_true", help="NASA host-star lane only")
    parser.add_argument("--planets", action="store_true", help="DE440 planetary lane only")
    parser.add_argument("--both", action="store_true", help="both lanes combined (default)")
    parser.add_argument("--out", default="sky_map.png")
    parser.add_argument("--ra-bins", type=int, default=12)
    parser.add_argument("--dec-bins", type=int, default=6)
    parser.add_argument("--nulls", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--fetch", action="store_true", help="refresh the NASA cache first")
    args = parser.parse_args(argv)

    from aureon.bio.sky_map import (
        SKY_MAP_BOUNDARY,
        planet_track_sources_from_de440,
        render_sky_map,
        stellar_sources_from_nasa,
    )

    if args.fetch:
        from scripts.validation.fetch_nasa_sky_data import fetch_rows, write_cache

        try:
            write_cache(fetch_rows())
            print("refreshed NASA cache", file=sys.stderr)
        except Exception as exc:  # network optional; fall back to committed cache
            print(f"fetch failed ({exc}); using committed cache", file=sys.stderr)

    want_planets = args.planets or args.both or not (args.stellar or args.planets or args.both)
    want_stellar = args.stellar or args.both or not (args.stellar or args.planets or args.both)

    sources = []
    if want_stellar:
        sources += stellar_sources_from_nasa()
    if want_planets:
        sources += planet_track_sources_from_de440()

    print("Aureon sky map — harmonic sensors pointed at the sky (φ logic unchanged)")
    print(f"  boundary: {SKY_MAP_BOUNDARY}")
    if not sources:
        print("  no positioned sources (is the NASA cache position-carrying? run --fetch)")
        return 1

    result = render_sky_map(
        sources, consent=True,
        provenance="Aureon sky map: NASA Exoplanet Archive hosts (RA/Dec + Wien colour) "
        "+ DE440 planetary ephemeris (RA/Dec + orbital-motion tones)",
        out_path=args.out, ra_bins=args.ra_bins, dec_bins=args.dec_bins,
        nulls=args.nulls, seed=args.seed)

    scored = [c for c in result.cells if c.n_tones >= 2]
    top = sorted((c for c in scored), key=lambda c: (c.test_A_p or 1.0) + (c.test_B_p or 1.0))[:5]
    print(f"  sources          : {result.n_sources} "
          f"(stellar {len(stellar_sources_from_nasa()) if want_stellar else 0}, "
          f"planetary {len(planet_track_sources_from_de440()) if want_planets else 0})")
    print(f"  grid             : {result.ra_bins}×{result.dec_bins} ({len(result.cells)} cells)")
    print(f"  scored cells     : {len(scored)} (>= 2 tones)")
    print(f"  converged cells  : {result.n_converged} (both channels < ALPHA)")
    print(f"  controls_pass    : {result.controls_pass}")
    print(f"  rendered         : {result.out_path}")
    for c in top:
        print(f"    cell r{c.row}c{c.col} RA[{c.ra_lo:.0f},{c.ra_hi:.0f}) "
              f"Dec[{c.dec_lo:.0f},{c.dec_hi:.0f}) n_tones={c.n_tones} "
              f"A_p={c.test_A_p:.3f} B_p={c.test_B_p:.3f} fired={c.channels_fired}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
