#!/usr/bin/env python3
"""Sacred-lattice scan — direct the repo's own sky-mapping systems at the engine.

Others map the sky with object catalogs; Aureon maps it through Earth's harmonic
lattice. This module scans three of the repo's own frequency/position systems
(:mod:`aureon.bio.sacred_lattice_reference`) through the **identical** governed
pipeline every other sensor uses (``score_sky`` / ``score_signal``: controls →
Test A / Test B → separability at ``ALPHA`` → Operator/conscience veto →
``SCIENTIFIC_BOUNDARY``). Nothing about the engine is modified; each verdict is
reported exactly as the test returns it.

Reuses the sky adapter's ``radio_hz`` path for the lattice tone lists, and the
convergence map machinery (:mod:`aureon.bio.sky_map`) for the positional lattice grid.
No new engine machinery.
"""

from __future__ import annotations

import phenolic_fingerprint as engine
from aureon.bio import sacred_lattice_reference as lattice
from aureon.bio.human_harmonic_proxy import ProxyResult
from aureon.bio.sky_map import SkySource, analyze_sky_map
from aureon.bio.sky_signal_adapter import score_sky

__all__ = [
    "score_lattice",
    "lattice_sky_sources",
    "score_lattice_map",
    "main",
]

_CITATIONS = {
    "stargate": lattice.STARGATE_CITATION,
    "maeshowe": lattice.MAESHOWE_CITATION,
    "metatron": lattice.METATRON_CITATION,
}


def score_lattice(
    name: str,
    *,
    consent: bool = True,
    provenance: str | None = None,
    nulls: int = engine.DEFAULT_NULLS,
    seed: int = 0,
) -> ProxyResult:
    """Scan a named sacred-lattice catalog ('stargate' | 'maeshowe' | 'metatron')."""
    freqs = lattice.catalog_hz(name)
    citation = _CITATIONS.get(name, "")
    prov = provenance or f"sacred lattice: {name} ({citation})"
    return score_sky(freqs, consent=consent, provenance=prov, kind="radio_hz",
                     nulls=nulls, seed=seed)


def lattice_sky_sources() -> list[SkySource]:
    """The stargate lattice as positioned sources for the convergence-map lane.

    Earth sacred-site coordinates are mapped onto the same spherical grid the sky map
    uses: ``lon % 360`` fills the RA-analog axis, ``lat`` the Dec-analog axis, and each
    node carries its folded harmonic-signature tones. These are Earth positions, not
    celestial RA/Dec (see ``SACRED_LATTICE_BOUNDARY``).
    """
    out: list[SkySource] = []
    for name, _lat, lon, tones in lattice.stargate_positions():
        if not tones:
            continue
        out.append(SkySource(ra_deg=float(lon) % 360.0, dec_deg=float(_lat),
                             tones_hz=tones, label=name))
    return out


def score_lattice_map(
    *,
    consent: bool = True,
    provenance: str | None = None,
    ra_bins: int = 12,
    dec_bins: int = 6,
    nulls: int = 200,
    seed: int = 0,
):
    """Score the stargate lattice as a positional convergence grid (Earth-grid map)."""
    sources = lattice_sky_sources()
    prov = provenance or f"sacred lattice map ({lattice.STARGATE_CITATION})"
    return analyze_sky_map(sources, consent=consent, provenance=prov,
                           ra_bins=ra_bins, dec_bins=dec_bins, nulls=nulls, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """CLI: scan the sacred-lattice systems through the engine and report neutrally."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Direct the repo's own sacred-site / φ-geometry systems at the "
        "phenolic engine (φ logic unchanged)."
    )
    parser.add_argument("--system",
                        choices=["stargate", "maeshowe", "metatron", "all"], default="all")
    parser.add_argument("--map", action="store_true",
                        help="also score the stargate lattice as a positional grid")
    parser.add_argument("--nulls", type=int, default=engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    print("Sacred-lattice scan — the repo's OWN sky map, one unchanged φ engine")
    print(f"  boundary: {lattice.SACRED_LATTICE_BOUNDARY}")

    def _report(label, result):
        d = result.to_dict()
        print(f"  {label:10s}: n_tones={d['n_tones']} valid={d['valid']} "
              f"structure_present={d['structure_present']} "
              f"A_p={d['test_A_p']} B_p={d['test_B_p']}")

    want = ("stargate", "maeshowe", "metatron") if args.system == "all" else (args.system,)
    for sys_name in want:
        _report(sys_name, score_lattice(sys_name, nulls=args.nulls, seed=args.seed))

    if args.map:
        m = score_lattice_map(nulls=min(args.nulls, 200), seed=args.seed)
        d = m.to_dict()
        scored = sum(1 for c in m.cells if c.n_tones >= 2)
        print(f"  lattice map: valid={d['valid']} grid={d['ra_bins']}x{d['dec_bins']} "
              f"converged={d['n_converged']} of {scored} scored cells")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
