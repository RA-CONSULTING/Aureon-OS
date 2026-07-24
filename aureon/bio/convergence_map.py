#!/usr/bin/env python3
"""Convergence map — the "ghost-hunter grid" done rigorously.

Ghost-hunting, done as real anomaly detection rather than showmanship, rests on
two honest ideas this module implements literally:

* **Baseline + controls.** Take a null reading and validate the instrument before
  calling anything anomalous. Here that is the phenolic engine's positive/negative
  controls, run once for the whole image; if they fail, the whole map is invalid
  and nothing is rendered.
* **Multi-sensor convergence.** No single channel is trusted — a cell counts only
  when *independent* channels agree. Here each grid cell is scored by two
  independent structure detectors (Test A coherence-clustering and Test B
  golden-interval alignment); a cell "converges" only when **both** fire. A
  single-channel hit is noise, not a detection.

The result is a **spatial + multi-channel convergence map**: where, across a
uniform grid, independent measures of a *derived* colour signal agree that there is
non-random structure.

Scientific boundary (enforced, baked into the pixels)
-----------------------------------------------------
This maps **statistical structure in a derived signal only**. It is **NOT** a
detection of any entity, spirit, energy field, or person, and makes no paranormal
claim. Convergence across independent channels *reduces false positives* — it does
not prove anything exists. Derivation is content-agnostic: a **uniform** spatial
grid over global colour statistics, with **no** face/landmark/person logic. Consent
+ provenance are required, and the whole run is gated by the engine controls and
the Operator + conscience veto (via ``score_signal``) before any cell is scored.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

import blueprints
import phenolic_fingerprint as engine
from aureon.bio.human_harmonic_proxy import fold_to_band, score_signal
from aureon.bio.image_signal_adapter import (
    ImageSignalAdapter,
    _dominant_wavelengths_nm,
    _load_rgb,
    _wavelength_nm_to_hz,
)

__all__ = [
    "GHOST_HUNTER_BOUNDARY",
    "GridCell",
    "ConvergenceMap",
    "analyze_convergence",
    "render_convergence_map",
    "main",
]

#: Boundary specific to this "ghost-hunter grid" — baked into every rendered map.
GHOST_HUNTER_BOUNDARY: str = (
    "Spatial+multi-channel convergence map of statistical structure in a derived "
    "signal ONLY - NOT detection of any entity, spirit, energy, or person; "
    "convergence reduces false positives, it proves nothing paranormal."
)

_C_CONVERGED = blueprints.C_NODE   # cells where both channels agree
_C_SINGLE = blueprints.C_PHI       # single-channel (noise) cells, faint
_GRID_INK = (200, 200, 220)
_CAPTION_BG = (10, 10, 21)


@dataclass(frozen=True)
class GridCell:
    """One uniform grid cell's independent-channel scores + convergence verdict."""

    row: int
    col: int
    n_tones: int
    test_A_p: float | None
    test_B_p: float | None
    channels_fired: int  # 0, 1, or 2 independent channels below ALPHA
    converged: bool      # both independent channels agree (channels_fired == 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "row": self.row, "col": self.col, "n_tones": self.n_tones,
            "test_A_p": self.test_A_p, "test_B_p": self.test_B_p,
            "channels_fired": self.channels_fired, "converged": self.converged,
        }


@dataclass(frozen=True)
class ConvergenceMap:
    """Result of a ghost-hunter-grid analysis. ``out_path`` is None if not rendered."""

    valid: bool
    blocked: bool
    grid: int
    cells: list[GridCell]
    n_converged: int
    controls_pass: bool
    reason: str | None
    out_path: str | None = None
    boundary: str = GHOST_HUNTER_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid, "blocked": self.blocked, "grid": self.grid,
            "n_cells": len(self.cells), "n_converged": self.n_converged,
            "controls_pass": self.controls_pass, "reason": self.reason,
            "out_path": self.out_path, "boundary": self.boundary,
            "cells": [c.to_dict() for c in self.cells],
        }


def _rng(seed: int, tag: int) -> np.random.Generator:
    return np.random.default_rng([int(seed), int(tag)])


def _tile_bounds(w: int, h: int, grid: int) -> list[tuple[int, int, int, int, int, int]]:
    """Uniform grid tiles as (row, col, x0, y0, x1, y1). Not face/person regions."""
    out: list[tuple[int, int, int, int, int, int]] = []
    for r in range(grid):
        for c in range(grid):
            x0 = int(round(c * w / grid))
            x1 = int(round((c + 1) * w / grid))
            y0 = int(round(r * h / grid))
            y1 = int(round((r + 1) * h / grid))
            out.append((r, c, x0, y0, x1, y1))
    return out


def _tile_tones(tile_rgb: np.ndarray, max_colors: int) -> list[float]:
    """Fold a tile's dominant spectral hues into the modulation band (colour channel)."""
    wls = _dominant_wavelengths_nm(tile_rgb, max_colors=max_colors)
    tones = [fold_to_band(_wavelength_nm_to_hz(nm)) for nm in wls]
    return sorted(t for t in tones if t is not None)


def analyze_convergence(
    source: Any,
    *,
    consent: bool,
    provenance: str,
    grid: int = 5,
    nulls: int = 200,
    seed: int = 0,
    downscale: int = 384,
    max_colors: int = 6,
) -> ConvergenceMap:
    """Score a uniform grid over ``source`` with two independent channels per cell.

    Governance runs first via ``score_signal`` on the whole image (consent gate +
    engine controls + Operator/conscience veto). If that global run is blocked or
    invalid, no cells are scored — a blocked/invalid run yields no map ("no
    reading"). Otherwise each cell is scored by Test A and Test B independently, and
    marked ``converged`` only when both fire.
    """
    adapter = ImageSignalAdapter()
    global_signal = adapter.extract(source, consent=consent, provenance=provenance, downscale=downscale)
    gov = score_signal(global_signal, nulls=nulls, seed=seed)
    gd = gov.to_dict()
    controls_pass = bool(gd.get("controls")
                         and all(c.get("passed") for c in gd["controls"].values()))

    if gd["blocked"] or not gd["valid"]:
        return ConvergenceMap(
            valid=bool(gd["valid"]), blocked=bool(gd["blocked"]), grid=grid,
            cells=[], n_converged=0, controls_pass=controls_pass, reason=gd["reason"],
        )

    rgb = _load_rgb(source, downscale=downscale)
    h, w = rgb.shape[0], rgb.shape[1]
    alpha = engine.ALPHA
    cells: list[GridCell] = []
    for idx, (r, c, x0, y0, x1, y1) in enumerate(_tile_bounds(w, h, grid)):
        tile = rgb[y0:y1, x0:x1, :]
        tones = _tile_tones(tile, max_colors)
        if len(tones) < 2:
            cells.append(GridCell(r, c, len(tones), None, None, 0, False))
            continue
        arr = np.asarray(tones, dtype=float)
        p_a = engine.test_A(arr, nulls=nulls, rng=_rng(seed, 10_000 + idx))
        p_b = engine.test_B(arr, nulls=nulls, rng=_rng(seed, 20_000 + idx))
        fired = int(p_a < alpha) + int(p_b < alpha)
        cells.append(GridCell(r, c, len(tones), float(p_a), float(p_b), fired, fired == 2))

    n_conv = sum(1 for c in cells if c.converged)
    return ConvergenceMap(
        valid=True, blocked=False, grid=grid, cells=cells,
        n_converged=n_conv, controls_pass=controls_pass, reason=None,
    )


def _draw_caption(img: Any, lines: list[str]) -> None:
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    w, h = img.size
    bar_h = 14 * len(lines) + 12
    draw.rectangle([0, h - bar_h, w, h], fill=(*_CAPTION_BG, 235))
    y = h - bar_h + 6
    for line in lines:
        draw.text((8, y), line, fill=(230, 230, 240, 255))
        y += 14


def render_convergence_map(
    source: Any,
    *,
    consent: bool,
    provenance: str,
    out_path: str | Path,
    grid: int = 5,
    alpha: float = 0.5,
    nulls: int = 200,
    seed: int = 0,
    downscale: int = 384,
) -> ConvergenceMap:
    """Analyze then render the convergence map as a heatmap over the source image.

    Converged cells (both independent channels agree) are highlighted; single-channel
    cells get only a faint outline (labelled noise); a blocked/invalid run renders
    nothing. The scientific boundary is baked into the composite as a caption.
    """
    from PIL import Image, ImageDraw

    cmap = analyze_convergence(
        source, consent=consent, provenance=provenance, grid=grid,
        nulls=nulls, seed=seed, downscale=downscale,
    )
    if cmap.blocked or not cmap.valid:
        return cmap  # no reading rendered

    rgb = _load_rgb(source, downscale=downscale)
    img = Image.fromarray(rgb, "RGB").convert("RGBA")
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    conv_rgb = tuple(int(blueprints.C_NODE.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    single_rgb = tuple(int(blueprints.C_PHI.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    bounds = {(r, c): (x0, y0, x1, y1) for (r, c, x0, y0, x1, y1) in _tile_bounds(w, h, grid)}

    for cell in cmap.cells:
        x0, y0, x1, y1 = bounds[(cell.row, cell.col)]
        draw.rectangle([x0, y0, x1, y1], outline=(*_GRID_INK, 40), width=1)
        if cell.converged:
            # strength from how far below ALPHA both channels sit
            worst = max(cell.test_A_p or 1.0, cell.test_B_p or 1.0)
            strength = max(0.0, min(1.0, 1.0 - worst / engine.ALPHA))
            a = int(210 * (0.35 + 0.65 * strength) * alpha)
            draw.rectangle([x0, y0, x1, y1], fill=(*conv_rgb, a), outline=(*conv_rgb, 220), width=2)
        elif cell.channels_fired == 1:
            draw.rectangle([x0, y0, x1, y1], outline=(*single_rgb, 120), width=1)

    composite = Image.alpha_composite(img, layer)
    _draw_caption(
        composite,
        [
            GHOST_HUNTER_BOUNDARY,
            (f"grid={grid}x{grid} converged(both channels)={cmap.n_converged}/"
             f"{len(cmap.cells)} | single-channel cells = noise, not detections"),
        ],
    )
    composite.convert("RGB").save(out_path)
    return ConvergenceMap(
        valid=True, blocked=False, grid=grid, cells=cmap.cells,
        n_converged=cmap.n_converged, controls_pass=cmap.controls_pass,
        reason=None, out_path=str(out_path),
    )


def main(argv: list[str] | None = None) -> int:
    """CLI: render a ghost-hunter convergence grid over a consented image."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Spatial + multi-channel convergence map (derived-signal structure only; no entity/person claims)."
    )
    parser.add_argument("image")
    parser.add_argument("--consent", action="store_true")
    parser.add_argument("--provenance", default="")
    parser.add_argument("--out", default="convergence_map.png")
    parser.add_argument("--grid", type=int, default=5)
    parser.add_argument("--alpha", type=float, default=0.5)
    parser.add_argument("--nulls", type=int, default=200)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    cmap = render_convergence_map(
        args.image, consent=bool(args.consent), provenance=args.provenance,
        out_path=args.out, grid=args.grid, alpha=args.alpha, nulls=args.nulls, seed=args.seed,
    )
    d = cmap.to_dict()
    print("Convergence map — spatial + multi-channel (ghost-hunter grid)")
    print(f"  boundary        : {GHOST_HUNTER_BOUNDARY}")
    print(f"  out_path        : {d['out_path']}")
    print(f"  valid / blocked : {d['valid']} / {d['blocked']}")
    print(f"  grid            : {d['grid']}x{d['grid']} ({d['n_cells']} cells)")
    print(f"  converged cells : {d['n_converged']} (both independent channels agree)")
    print(f"  controls_pass   : {d['controls_pass']}")
    print(f"  reason          : {d['reason']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
