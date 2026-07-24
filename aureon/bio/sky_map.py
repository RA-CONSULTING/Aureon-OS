#!/usr/bin/env python3
"""Sky map — point the harmonic sensors at the sky and map φ-structure by position.

The harmonic/frequency-detection sensor suite was proven on the market test-bed; this
turns the *same* sensors on the sky. It bins real sky sources by celestial position
(right ascension / declination) into a grid and scores each cell's derived light
through the **unchanged** phenolic φ engine — producing an all-sky map of *where* the
engine detects φ-structure. Nothing about the engine is modified; every cell verdict
is reported exactly as the pre-registered test returns it.

It reuses the spatial-map machinery of :mod:`aureon.bio.convergence_map` — the
two-channel "converged" semantics (a cell converges only when both independent engine
tests agree below ``ALPHA``) and one global governance pass through ``score_signal``
(consent/provenance → controls → Operator/conscience veto → ``SCIENTIFIC_BOUNDARY``)
before any cell is scored.

Two real lanes feed the generic engine:
* **Stellar** — NASA Exoplanet Archive host stars: real RA/Dec + Wien-law colour from
  each star's effective temperature (``stellar_sources_from_nasa``).
* **Planetary** — DE440 ephemeris: real RA/Dec ecliptic track, each planet painting
  its orbital-motion tones along where it moves (``planet_track_sources_from_de440``).

Pure stdlib + numpy + engine; matplotlib for rendering (PIL raster fallback).
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final, Sequence

import numpy as np

import phenolic_fingerprint as engine
from aureon.bio.human_harmonic_proxy import (
    HumanSignal,
    fold_to_band,
    score_signal,
)
from aureon.bio.image_signal_adapter import _wavelength_nm_to_hz
from aureon.bio.upe_signal_adapter import _dominant_timeseries_hz

__all__ = [
    "SKY_MAP_BOUNDARY",
    "SkySource",
    "SkyCell",
    "SkyMap",
    "wien_peak_nm",
    "analyze_sky_map",
    "render_sky_map",
    "stellar_sources_from_nasa",
    "planet_track_sources_from_de440",
    "main",
]

SKY_MAP_BOUNDARY: Final[str] = (
    "All-sky spatial map of statistical φ-structure in light from the sky (derived "
    "signal only) - NOT a claim about the nature, composition, or behaviour of any "
    "celestial object; convergence reduces false positives, it proves nothing beyond "
    "the test."
)

#: Wien's displacement constant expressed for nm·K.
WIEN_NM_K: Final[float] = 2.897771955e6

_DEFAULT_NASA: Final[str] = "data/sky/nasa_exoplanet_hosts.csv"
_DEFAULT_DE440: Final[str] = "data/de440_ephemeris.csv"


def _rng(seed: int, tag: int) -> np.random.Generator:
    return np.random.default_rng([int(seed), int(tag)])


@dataclass(frozen=True)
class SkySource:
    """A positioned sky source with modulation tones already folded into the band."""

    ra_deg: float
    dec_deg: float
    tones_hz: tuple[float, ...]
    label: str = ""


@dataclass(frozen=True)
class SkyCell:
    """One RA/Dec grid cell scored through the engine's two independent tests."""

    row: int
    col: int
    ra_lo: float
    ra_hi: float
    dec_lo: float
    dec_hi: float
    n_sources: int
    n_tones: int
    test_A_p: float | None
    test_B_p: float | None
    channels_fired: int
    converged: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SkyMap:
    """The all-sky φ-structure map — cells + governance state + boundary."""

    valid: bool
    blocked: bool
    ra_bins: int
    dec_bins: int
    cells: list[SkyCell]
    n_converged: int
    controls_pass: bool
    reason: str | None
    n_sources: int = 0
    out_path: str | None = None
    boundary: str = SKY_MAP_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["cells"] = [c.to_dict() for c in self.cells]
        return d


def wien_peak_nm(teff_k: float) -> float:
    """Wien-law blackbody peak wavelength (nm) for an effective temperature (K)."""
    return WIEN_NM_K / float(teff_k)


def _sky_bounds(ra_bins: int, dec_bins: int):
    """Tile RA [0,360) × Dec [-90,90] into ra_bins × dec_bins cells."""
    ra_step = 360.0 / ra_bins
    dec_step = 180.0 / dec_bins
    for row in range(dec_bins):
        dec_lo = -90.0 + row * dec_step
        dec_hi = dec_lo + dec_step
        for col in range(ra_bins):
            ra_lo = col * ra_step
            ra_hi = ra_lo + ra_step
            yield row, col, ra_lo, ra_hi, dec_lo, dec_hi


def _cell_index(ra_deg: float, dec_deg: float, ra_bins: int, dec_bins: int) -> tuple[int, int]:
    """Row (dec) / col (ra) of the cell containing a position."""
    ra = float(ra_deg) % 360.0
    dec = min(max(float(dec_deg), -90.0), 90.0)
    col = min(int(ra // (360.0 / ra_bins)), ra_bins - 1)
    row = min(int((dec + 90.0) // (180.0 / dec_bins)), dec_bins - 1)
    return row, col


def analyze_sky_map(
    sources: Sequence[SkySource],
    *,
    consent: bool,
    provenance: str,
    ra_bins: int = 12,
    dec_bins: int = 6,
    nulls: int = 200,
    seed: int = 0,
) -> SkyMap:
    """Bin sources by RA/Dec and score each cell through the engine (φ unchanged).

    A single global governance pass runs first (``score_signal`` on the pooled tones):
    consent/provenance gate, engine controls, and the Operator/conscience veto. A
    blocked or invalid run yields an empty map. Otherwise each cell pools the tones of
    the sources it contains and, when it has >= 2, scores them with ``engine.test_A``
    and ``engine.test_B``; a cell converges only when both fall below ``ALPHA``.
    """
    pooled = tuple(sorted(t for s in sources for t in s.tones_hz))
    global_signal = HumanSignal(
        label="sky_map",
        frequencies_hz=pooled,
        provenance=provenance,
        consent=consent,
        modality="sky",
        notes=f"{len(sources)} positioned sky source(s); all-sky φ-structure map",
    )
    gov = score_signal(global_signal, nulls=nulls, seed=seed)
    gd = gov.to_dict()
    controls_pass = bool(gd.get("controls") and all(c.get("passed") for c in gd["controls"].values()))

    if gd["blocked"] or not gd["valid"]:
        return SkyMap(
            valid=bool(gd["valid"]), blocked=bool(gd["blocked"]), ra_bins=ra_bins,
            dec_bins=dec_bins, cells=[], n_converged=0, controls_pass=controls_pass,
            reason=gd["reason"], n_sources=len(sources),
        )

    # bucket source tones by cell
    buckets: dict[tuple[int, int], list[float]] = {}
    for s in sources:
        key = _cell_index(s.ra_deg, s.dec_deg, ra_bins, dec_bins)
        buckets.setdefault(key, []).extend(s.tones_hz)

    alpha = engine.ALPHA
    cells: list[SkyCell] = []
    for idx, (row, col, ra_lo, ra_hi, dec_lo, dec_hi) in enumerate(_sky_bounds(ra_bins, dec_bins)):
        tones = sorted(buckets.get((row, col), []))
        n_src = sum(1 for s in sources if _cell_index(s.ra_deg, s.dec_deg, ra_bins, dec_bins) == (row, col))
        if len(tones) < 2:
            cells.append(SkyCell(row, col, ra_lo, ra_hi, dec_lo, dec_hi, n_src, len(tones),
                                 None, None, 0, False))
            continue
        arr = np.asarray(tones, dtype=float)
        p_a = float(engine.test_A(arr, nulls=nulls, rng=_rng(seed, 10_000 + idx)))
        p_b = float(engine.test_B(arr, nulls=nulls, rng=_rng(seed, 20_000 + idx)))
        fired = int(p_a < alpha) + int(p_b < alpha)
        cells.append(SkyCell(row, col, ra_lo, ra_hi, dec_lo, dec_hi, n_src, len(tones),
                             p_a, p_b, fired, fired == 2))

    n_conv = sum(1 for c in cells if c.converged)
    return SkyMap(
        valid=True, blocked=False, ra_bins=ra_bins, dec_bins=dec_bins, cells=cells,
        n_converged=n_conv, controls_pass=controls_pass, reason=None, n_sources=len(sources),
    )


def render_sky_map(
    sources: Sequence[SkySource],
    *,
    consent: bool,
    provenance: str,
    out_path: str | Path,
    ra_bins: int = 12,
    dec_bins: int = 6,
    nulls: int = 200,
    seed: int = 0,
) -> SkyMap:
    """Analyze + render an RA/Dec heatmap PNG; returns the SkyMap with out_path set."""
    result = analyze_sky_map(sources, consent=consent, provenance=provenance,
                             ra_bins=ra_bins, dec_bins=dec_bins, nulls=nulls, seed=seed)
    if result.blocked or not result.valid:
        return result  # render nothing on a governance block

    grid = np.zeros((dec_bins, ra_bins), dtype=float)
    for c in result.cells:
        grid[c.row, c.col] = c.channels_fired  # 0 / 1 / 2
    out = str(out_path)
    _render_png(grid, out, ra_bins, dec_bins, result.n_converged, len(sources))
    return SkyMap(
        valid=result.valid, blocked=result.blocked, ra_bins=ra_bins, dec_bins=dec_bins,
        cells=result.cells, n_converged=result.n_converged, controls_pass=result.controls_pass,
        reason=result.reason, n_sources=result.n_sources, out_path=out,
    )


def _render_png(grid: np.ndarray, out_path: str, ra_bins: int, dec_bins: int,
                n_converged: int, n_sources: int) -> None:
    """Render the channels-fired grid as an RA/Dec heatmap (matplotlib; PIL fallback)."""
    caption = (f"Sky map — φ-structure by RA/Dec  ·  {n_sources} sources  ·  "
               f"{n_converged} converged cells\n{SKY_MAP_BOUNDARY}")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 5.5))
        ax.imshow(grid, origin="lower", extent=(0, 360, -90, 90), aspect="auto",
                  cmap="magma", vmin=0, vmax=2)
        ax.set_xlabel("Right ascension (deg)")
        ax.set_ylabel("Declination (deg)")
        ax.set_xticks(np.linspace(0, 360, ra_bins + 1))
        ax.set_yticks(np.linspace(-90, 90, dec_bins + 1))
        ax.grid(True, color="white", alpha=0.15, linewidth=0.5)
        ax.set_title("Aureon sky map — channels fired (0/1/2)")
        fig.text(0.5, 0.01, caption, ha="center", va="bottom", fontsize=6, wrap=True)
        fig.subplots_adjust(bottom=0.22)
        fig.savefig(out_path, dpi=120)
        plt.close(fig)
        return
    except Exception:  # pragma: no cover - fallback path
        pass

    # PIL raster fallback: scale the grid up into a simple heatmap.
    from PIL import Image

    scale = 40
    hi = float(grid.max()) or 1.0
    img = np.zeros((dec_bins * scale, ra_bins * scale, 3), dtype=np.uint8)
    for r in range(dec_bins):
        for c in range(ra_bins):
            v = int(255 * grid[r, c] / hi)
            img[(dec_bins - 1 - r) * scale:(dec_bins - r) * scale, c * scale:(c + 1) * scale] = (v, v // 3, 255 - v)
    Image.fromarray(img, "RGB").save(out_path)


# ---------------------------------------------------------------------------
# source builders (real data → positioned, folded tones)
# ---------------------------------------------------------------------------


def _read_nasa_cache(path: str | Path) -> list[dict[str, str]]:
    lines = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if not ln.startswith("#")]
    import io

    return list(csv.DictReader(io.StringIO("\n".join(lines))))


def stellar_sources_from_nasa(path: str | Path = _DEFAULT_NASA) -> list[SkySource]:
    """Host-star sources: real RA/Dec + one Wien-colour tone per star.

    Requires the position-carrying cache (``ra``/``dec`` columns). Returns an empty
    list if the cache is absent or positionless, so callers degrade gracefully.
    """
    p = Path(path)
    if not p.exists():
        return []
    out: list[SkySource] = []
    for row in _read_nasa_cache(p):
        if not row.get("ra") or not row.get("dec") or not row.get("st_teff"):
            continue
        try:
            ra, dec, teff = float(row["ra"]), float(row["dec"]), float(row["st_teff"])
        except (ValueError, TypeError):
            continue
        if teff <= 0:
            continue
        tone = fold_to_band(_wavelength_nm_to_hz(wien_peak_nm(teff)))
        if tone is None:
            continue
        out.append(SkySource(ra_deg=ra, dec_deg=dec, tones_hz=(tone,),
                             label=str(row.get("hostname", ""))))
    return out


def planet_track_sources_from_de440(
    path: str | Path = _DEFAULT_DE440,
    *,
    track_samples: int = 24,
) -> list[SkySource]:
    """Planet sources: each planet paints its orbital-motion tones along its RA/Dec track.

    For each planet, the ``r_au`` distance timeseries is run through the timeseries
    sensor (``_dominant_timeseries_hz``) → folded tones; the planet's (ra,dec) track is
    subsampled into ``track_samples`` points, each carrying those tones, so the planet's
    motion-tones are mapped along where it actually moves in the sky.
    """
    p = Path(path)
    if not p.exists():
        return []
    by_planet: dict[str, list[tuple[float, float, float]]] = {}
    with p.open("r", newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            planet = (row.get("planet") or "").strip()
            if not planet or planet.lower() == "earth":
                continue
            try:
                ra, dec, r_au = float(row["ra_deg"]), float(row["dec_deg"]), float(row["r_au"])
            except (KeyError, ValueError, TypeError):
                continue
            by_planet.setdefault(planet, []).append((ra, dec, r_au))

    from aureon.bio.cosmic_reference import PLANETARY_TONE_MAP

    out: list[SkySource] = []
    for planet, samples in by_planet.items():
        if len(samples) < 8:
            continue
        r_series = np.array([s[2] for s in samples], dtype=float)
        raw_hz = _dominant_timeseries_hz(r_series, sample_rate_hz=1.0, max_peaks=12)
        tones = [f for f in (fold_to_band(v) for v in raw_hz) if f is not None]
        # Enrich with the planet's octave-shifted period tone (Cosmic Octave), if known,
        # so the ecliptic lane carries both the motion tone and the planetary tone.
        octave = PLANETARY_TONE_MAP.get(planet.lower())
        if octave is not None:
            folded = fold_to_band(octave)
            if folded is not None:
                tones.append(folded)
        tones = tuple(sorted(set(tones)))
        # A planet contributes its own distance-modulation tone(s); cells along the
        # ecliptic pool tones across planets to reach the >=2 the engine needs.
        if not tones:
            continue
        step = max(1, len(samples) // int(track_samples))
        for ra, dec, _r in samples[::step]:
            out.append(SkySource(ra_deg=ra, dec_deg=dec, tones_hz=tones, label=planet))
    return out


def main(argv: list[str] | None = None) -> int:
    """CLI: build + render the sky map from the stellar and/or planetary lanes."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Map φ-structure across the sky by RA/Dec (engine φ logic unchanged)."
    )
    parser.add_argument("--stellar", action="store_true", help="NASA host-star lane")
    parser.add_argument("--planets", action="store_true", help="DE440 planetary lane")
    parser.add_argument("--both", action="store_true", help="both lanes combined")
    parser.add_argument("--out", default="sky_map.png")
    parser.add_argument("--ra-bins", type=int, default=12)
    parser.add_argument("--dec-bins", type=int, default=6)
    parser.add_argument("--nulls", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    want_stellar = args.stellar or args.both or not (args.stellar or args.planets or args.both)
    want_planets = args.planets or args.both

    sources: list[SkySource] = []
    if want_stellar:
        sources += stellar_sources_from_nasa()
    if want_planets:
        sources += planet_track_sources_from_de440()

    print("Sky map — pointing the harmonic sensors at the sky (φ logic unchanged)")
    print(f"  boundary: {SKY_MAP_BOUNDARY}")
    if not sources:
        print("  no positioned sources available (is the NASA cache position-carrying?)")
        return 1

    result = render_sky_map(sources, consent=True,
                            provenance="Aureon sky map: NASA Exoplanet Archive hosts + DE440 ephemeris",
                            out_path=args.out, ra_bins=args.ra_bins, dec_bins=args.dec_bins,
                            nulls=args.nulls, seed=args.seed)
    scored = [c for c in result.cells if c.n_tones >= 2]
    print(f"  sources          : {result.n_sources}")
    print(f"  grid             : {result.ra_bins}×{result.dec_bins} ({len(result.cells)} cells)")
    print(f"  scored cells     : {len(scored)} (>= 2 tones)")
    print(f"  converged cells  : {result.n_converged} (both channels < ALPHA)")
    print(f"  controls_pass    : {result.controls_pass}")
    print(f"  rendered         : {result.out_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
