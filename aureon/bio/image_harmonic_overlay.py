#!/usr/bin/env python3
"""Image harmonic overlay — photon -> analysis -> geometry -> composite.

The creative end of the bio pipeline: take an image, extract its **photon
(light/colour) data** with :class:`aureon.bio.image_signal_adapter.ImageSignalAdapter`,
**analyze** it through the governed :func:`aureon.bio.human_harmonic_proxy.score_signal`,
build a **geometric harmonic pattern** from that analysis, **layer** it over the
source image, and **recompile** into a single composite PNG.

Scientific boundary (enforced, baked into the pixels)
-----------------------------------------------------
The overlay is a *derived geometric figure computed from the image's global colour
statistics* — **not** a measurement, aura, field, health, or trait of any person,
and no efficacy claim. Every composite carries the :data:`SCIENTIFIC_BOUNDARY`
sentence as a visible caption. The analysis still passes the consent/provenance
gate, the mandatory engine controls, and the Operator + conscience veto; a
**blocked or invalid run renders no harmonic pattern** — it cannot produce a
"reading". Derivation is content-agnostic (whole-image colour only; there is no
face/landmark/person logic anywhere in this module), so it is structurally not
physiognomy.

Every drawn element ties to the *same* statistics the engine scores: coherence
nodes are Test A (clustering), φ-interval chords are Test B (golden-interval
alignment), and the φ-scaled ring scaffold is the modulation band itself.

Pure numpy + Pillow + the two bio modules + engine constants. Pillow is imported
lazily; no import-time side effects.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Ensure the repo root is importable (blueprints.py + phenolic_fingerprint.py live
# there), regardless of how this module is invoked. Idempotent, side-effect-free.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import blueprints  # noqa: E402
import phenolic_fingerprint as engine  # noqa: E402
from aureon.bio import human_harmonic_proxy as proxy  # noqa: E402
from aureon.bio.human_harmonic_proxy import (  # noqa: E402
    SCIENTIFIC_BOUNDARY,
    ProxyResult,
    fold_to_band,
    score_signal,
)
from aureon.bio.image_signal_adapter import ImageSignalAdapter, _load_rgb  # noqa: E402

__all__ = [
    "OverlayResult",
    "build_geometric_pattern",
    "render_overlay",
    "main",
]

PHI: float = float(engine.PHI)

# Palette (reuse the validated blueprint accents).
_C_NODE = blueprints.C_NODE          # coherence-node / harmonic accent
_C_PHI = blueprints.C_PHI            # golden-ratio sideband accent
_C_RAY = blueprints.C_EXPERIMENTAL   # tone-ray accent
_C_RING = (200, 200, 220)            # φ scaffold rings
_CAPTION_BG = (10, 10, 21)


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


@dataclass(frozen=True)
class OverlayResult:
    """Outcome of a harmonic-overlay render.

    ``out_path`` is ``None`` when the analysis was blocked or invalid — a
    blocked/invalid run never renders the harmonic pattern.
    """

    out_path: str | None
    valid: bool
    blocked: bool
    structure_present: bool
    n_tones: int
    n_nodes: int
    reason: str | None
    boundary: str = SCIENTIFIC_BOUNDARY

    def to_dict(self) -> dict[str, Any]:
        return {
            "out_path": self.out_path,
            "valid": self.valid,
            "blocked": self.blocked,
            "structure_present": self.structure_present,
            "n_tones": self.n_tones,
            "n_nodes": self.n_nodes,
            "reason": self.reason,
            "boundary": self.boundary,
        }


def _coherence_nodes(folded: list[float]) -> list[dict[str, Any]]:
    """Cluster folded tones into coherence nodes (reuses the blueprint clustering)."""
    records = [{"molecule": "image", "modulation_frequency_hz": float(f)} for f in folded]
    return blueprints.cluster_coherence_nodes(records)


def _phi_aligned_pairs(folded: list[float]) -> list[tuple[int, int]]:
    """Index pairs whose frequency-ratio log sits near an integer power of PHI (Test B)."""
    pairs: list[tuple[int, int]] = []
    logs = [math.log(f) / math.log(PHI) for f in folded]
    for i in range(len(folded)):
        for j in range(i + 1, len(folded)):
            gap = abs(logs[i] - logs[j])
            if abs(gap - round(gap)) <= 0.06:  # within 6% of a PHI-power lattice point
                pairs.append((i, j))
    return pairs


def _tone_xy(f: float, cx: float, cy: float, radius: float) -> tuple[float, float]:
    """Map a folded tone to a point: angle from its band position, radius fixed ring."""
    low, high = proxy.TARGET_BAND_HZ
    theta = 2.0 * math.pi * (float(f) - low) / (high - low)
    return (cx + radius * math.cos(theta), cy + radius * math.sin(theta))


def build_geometric_pattern(
    folded_tones: list[float] | tuple[float, ...],
    *,
    size: tuple[int, int],
    dominant_hz: list[float] | None = None,
) -> Any:
    """Draw the deterministic φ-harmonic geometry on a transparent RGBA layer.

    Elements: a φ-scaled concentric-ring scaffold, one radial ray per tone
    (ray count == tone count), filled coherence-node polygons (Test A clustering),
    and φ-interval chords (Test B alignment). Deterministic given the tones.
    """
    from PIL import Image, ImageDraw

    w, h = size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    cx, cy = w / 2.0, h / 2.0
    base_r = min(w, h) * 0.42
    tone_ring = base_r * 0.82

    # φ scaffold: concentric rings scaling by 1/PHI inward.
    r = base_r
    for _ in range(5):
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*_C_RING, 60), width=1)
        r /= PHI

    folded = [float(f) for f in folded_tones]
    if not folded:
        return layer
    pts = [_tone_xy(f, cx, cy, tone_ring) for f in folded]

    # Coherence-node polygons (Test A): join co-node tones, mark the node centre.
    node_rgb = _hex_to_rgb(_C_NODE)
    for node in _coherence_nodes(folded):
        idxs = [i for i, f in enumerate(folded) if node["min_hz"] <= f <= node["max_hz"]]
        if len(idxs) >= 2:
            poly = [pts[i] for i in idxs]
            draw.polygon(poly, fill=(*node_rgb, 40), outline=(*node_rgb, 150))
            mx = sum(p[0] for p in poly) / len(poly)
            my = sum(p[1] for p in poly) / len(poly)
            draw.ellipse([mx - 5, my - 5, mx + 5, my + 5], fill=(*node_rgb, 210))

    # φ-interval chords (Test B).
    phi_rgb = _hex_to_rgb(_C_PHI)
    for i, j in _phi_aligned_pairs(folded):
        draw.line([pts[i], pts[j]], fill=(*phi_rgb, 140), width=2)

    # Tone rays + tone points (one per tone).
    ray_rgb = _hex_to_rgb(_C_RAY)
    for (x, y) in pts:
        draw.line([(cx, cy), (x, y)], fill=(*ray_rgb, 110), width=1)
        draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(*ray_rgb, 220))

    draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=(255, 255, 255, 220))
    return layer


def _draw_caption(img: Any, lines: list[str]) -> None:
    """Draw a bottom caption bar carrying the scientific boundary + key numbers."""
    from PIL import ImageDraw

    draw = ImageDraw.Draw(img)
    w, h = img.size
    bar_h = 14 * len(lines) + 12
    draw.rectangle([0, h - bar_h, w, h], fill=(*_CAPTION_BG, 235))
    y = h - bar_h + 6
    for line in lines:
        draw.text((8, y), line, fill=(230, 230, 240, 255))
        y += 14


def render_overlay(
    source: Any,
    *,
    consent: bool,
    provenance: str,
    out_path: str | Path,
    alpha: float = 0.45,
    nulls: int = proxy.engine.DEFAULT_NULLS,
    seed: int = 0,
    max_colors: int = 12,
    downscale: int = 512,
    annotate_blocked: bool = False,
    upe_reference: bool = False,
) -> OverlayResult:
    """Extract photon data, analyze, and recompile the source with the harmonic overlay.

    A blocked or invalid analysis renders **no** harmonic pattern (no "reading").
    On success writes a composite PNG to ``out_path`` and returns its path.

    ``upe_reference=True`` puts the render in **UPE-model mode**: the caption is
    rewritten to state plainly that the result is an HNC *model* informed by
    reference ultraweak-photon-emission spectra — **not** a measurement of UPE or of
    any person, since a standard photo records reflected light, not biophotons. It
    also reports how the broadband UPE reference scores through the engine (expected
    non-separable — UPE is featureless), so the honest anchor rides on the image.
    """
    from PIL import Image

    adapter = ImageSignalAdapter()
    signal = adapter.extract(
        source, consent=consent, provenance=provenance, max_colors=max_colors, downscale=downscale
    )
    result: ProxyResult = score_signal(signal, nulls=nulls, seed=seed)
    d = result.to_dict()

    folded = [f for f in (fold_to_band(x) for x in signal.frequencies_hz) if f is not None]
    nodes = _coherence_nodes(folded) if folded else []

    if d["blocked"] or not d["valid"]:
        written: str | None = None
        if annotate_blocked:
            base = _load_rgb(source, downscale=downscale)
            img = Image.fromarray(base, "RGB").convert("RGBA")
            _draw_caption(img, [SCIENTIFIC_BOUNDARY, f"run not scored: {d['reason']} (no pattern rendered)"])
            img.convert("RGB").save(out_path)
            written = str(out_path)
        return OverlayResult(
            out_path=written, valid=bool(d["valid"]), blocked=bool(d["blocked"]),
            structure_present=False, n_tones=0, n_nodes=0, reason=d["reason"],
        )

    base = _load_rgb(source, downscale=downscale)
    img = Image.fromarray(base, "RGB").convert("RGBA")
    pattern = build_geometric_pattern(folded, size=img.size, dominant_hz=folded)
    # Alpha-scale the pattern so the source photo shows through.
    r, g, b, a = pattern.split()
    a = a.point(lambda v: int(v * alpha))
    pattern = Image.merge("RGBA", (r, g, b, a))
    composite = Image.alpha_composite(img, pattern)

    if upe_reference:
        caption = [
            "HNC MODEL informed by reference UPE spectra - NOT a measurement of UPE or of any person.",
            "A standard photo records REFLECTED light, not biophotons (UPE is ~1e3-1e6x dimmer).",
            (f"reflected-colour tones={len(folded)} nodes={len(nodes)} "
             f"| UPE reference is broadband/featureless -> non-separable (A_p~1.0)"),
        ]
    else:
        caption = [
            SCIENTIFIC_BOUNDARY,
            (f"derived geometric pattern | tones={len(folded)} nodes={len(nodes)} "
             f"structure_present={d['structure_present']} A_p={d['test_A_p']:.3f} B_p={d['test_B_p']:.3f}"),
        ]
    _draw_caption(composite, caption)
    composite.convert("RGB").save(out_path)

    return OverlayResult(
        out_path=str(out_path), valid=True, blocked=False,
        structure_present=bool(d["structure_present"]), n_tones=len(folded),
        n_nodes=len(nodes), reason=None,
    )


def main(argv: list[str] | None = None) -> int:
    """CLI: recompile a consented image with its harmonic overlay (or refuse)."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Photon -> analysis -> geometry -> composite (content-agnostic; no face analysis)."
    )
    parser.add_argument("image", help="path to an image the caller consents to analyse")
    parser.add_argument("--consent", action="store_true")
    parser.add_argument("--provenance", default="")
    parser.add_argument("--out", default="harmonic_overlay.png")
    parser.add_argument("--alpha", type=float, default=0.45)
    parser.add_argument("--nulls", type=int, default=proxy.engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--annotate-blocked", action="store_true")
    parser.add_argument("--upe-reference", action="store_true",
                        help="UPE-model mode: label as an HNC model vs reference UPE spectra, not a measurement")
    args = parser.parse_args(argv)

    result = render_overlay(
        args.image, consent=bool(args.consent), provenance=args.provenance,
        out_path=args.out, alpha=args.alpha, nulls=args.nulls, seed=args.seed,
        annotate_blocked=args.annotate_blocked, upe_reference=args.upe_reference,
    )
    d = result.to_dict()
    print("Image harmonic overlay — photon -> analysis -> geometry -> composite")
    print(f"  boundary         : {SCIENTIFIC_BOUNDARY}")
    print(f"  out_path         : {d['out_path']}")
    print(f"  valid / blocked  : {d['valid']} / {d['blocked']}")
    print(f"  structure_present: {d['structure_present']}")
    print(f"  tones / nodes    : {d['n_tones']} / {d['n_nodes']}")
    print(f"  reason           : {d['reason']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
