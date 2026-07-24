#!/usr/bin/env python3
"""Image signal adapter — the first *real* :class:`SignalAdapter` for the
human-harmonic proxy.

It turns an image into a derived frequency series and hands it to
:func:`aureon.bio.human_harmonic_proxy.score_signal`, so an image can finally be
scored by the same falsifiable engine — **without** becoming a face or "aura"
reader.

Content-agnostic by construction
--------------------------------
The signal is derived from the image's **global colour statistics only**: the
dominant spectral hues across the whole frame. There is **no** face detection, no
landmark extraction, and no per-region/per-person analysis anywhere in this
module. That makes it *structurally* incapable of physiognomy regardless of what
the picture contains. Colour is not identity, and the output is only *statistical
structure in a derived signal* — never a claim, reading, health signal, or trait
about a person. The immutable scientific boundary and the consent/provenance gate
of :mod:`aureon.bio.human_harmonic_proxy` still apply, because all scoring flows
through :func:`score_signal` unchanged.

Physics, reused (not invented)
------------------------------
A colour *is* an electromagnetic frequency. Each dominant spectral hue is mapped
to its visible wavelength (nm) and then to an EM frequency (Hz) using the engine's
own molecular constants (``phenolic_fingerprint.NM_TO_THZ_NUMERATOR`` /
``THZ_TO_HZ`` — the exact relation the molecular ``nm`` peak path uses). The
proxy's ``fold_to_band`` then octave-folds those ~10^14 Hz light frequencies into
the 1000-2000 Hz modulation band, the same octave-fold the engine performs for
molecular peaks.

Pillow is imported lazily so importing the pure proxy core never requires it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio.human_harmonic_proxy import (
    SCIENTIFIC_BOUNDARY,
    HumanSignal,
    ProxyResult,
    score_signal,
)

__all__ = [
    "ImageSignalAdapter",
    "score_image",
    "main",
]

# Anchor points for the spectral hue -> wavelength(nm) map. Hue in degrees over
# the spectral arc red(0) .. violet(270); magenta/pink (271-360) is non-spectral
# (no single wavelength) and is excluded upstream. Anchors are the textbook
# rainbow centres; we piecewise-linearly interpolate between them.
_HUE_ANCHORS: tuple[tuple[float, float], ...] = (
    (0.0, 700.0),    # red
    (60.0, 580.0),   # yellow
    (120.0, 530.0),  # green
    (180.0, 490.0),  # cyan
    (240.0, 450.0),  # blue
    (270.0, 400.0),  # violet
)

_SPECTRAL_HUE_MAX: float = 270.0  # hues above this are non-spectral -> dropped
_SAT_MIN: float = 0.20            # below this saturation the pixel is achromatic
_VAL_MIN: float = 0.15            # below this value the pixel is (near) black
_HUE_BINS: int = 36               # histogram resolution over the spectral arc


def _hue_to_wavelength_nm(hue_deg: float) -> float | None:
    """Map a spectral hue angle (0-270 deg) to a visible wavelength in nm.

    Returns ``None`` for non-spectral hues (magenta/pink, > 270 deg) which
    correspond to no single wavelength. Piecewise-linear across ``_HUE_ANCHORS``.
    """
    h = float(hue_deg)
    if not (0.0 <= h <= _SPECTRAL_HUE_MAX):
        return None
    for (h0, w0), (h1, w1) in zip(_HUE_ANCHORS, _HUE_ANCHORS[1:], strict=False):
        if h0 <= h <= h1:
            frac = 0.0 if h1 == h0 else (h - h0) / (h1 - h0)
            return w0 + frac * (w1 - w0)
    return _HUE_ANCHORS[-1][1]  # exactly at the violet end


def _wavelength_nm_to_hz(nm: float) -> float:
    """Convert a wavelength (nm) to its EM frequency (Hz), engine constants."""
    return (proxy.engine.NM_TO_THZ_NUMERATOR / float(nm)) * proxy.engine.THZ_TO_HZ


def _load_rgb(spec: Any, downscale: int) -> np.ndarray:
    """Load ``spec`` (path / PIL image / RGB array) to a downscaled uint8 RGB array.

    Deterministic: fixed resample filter, no randomness.
    """
    try:
        from PIL import Image
    except Exception as exc:  # noqa: BLE001
        raise ImportError(
            "Pillow is required for the image signal adapter "
            "(`pip install pillow`); the pure proxy core does not need it."
        ) from exc

    if isinstance(spec, np.ndarray):
        arr = spec
        if arr.ndim == 2:  # grayscale -> RGB
            arr = np.stack([arr] * 3, axis=-1)
        img = Image.fromarray(arr.astype(np.uint8)[:, :, :3], mode="RGB")
    elif isinstance(spec, (str, Path)):
        img = Image.open(spec).convert("RGB")
    elif isinstance(spec, Image.Image):
        img = spec.convert("RGB")
    else:  # pragma: no cover - guarded by callers
        raise TypeError(f"unsupported image spec type: {type(spec)!r}")

    w, h = img.size
    longest = max(w, h)
    if longest > downscale:
        scale = downscale / longest
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BILINEAR)
    return np.asarray(img.convert("RGB"), dtype=np.uint8)


def _dominant_wavelengths_nm(rgb: np.ndarray, *, max_colors: int) -> list[float]:
    """Return the wavelengths (nm) of the most-populated spectral hue bins.

    Global colour statistics over the whole frame only. Achromatic pixels
    (grey/black/white) and non-spectral hues (magenta/pink) are dropped, so an
    image with no clear spectral colour yields few or no wavelengths — which the
    scorer honestly reports as "insufficient tones" rather than fabricating any.
    """
    from PIL import Image

    hsv = np.asarray(Image.fromarray(rgb, mode="RGB").convert("HSV"), dtype=np.float64)
    hue = hsv[..., 0].ravel() / 255.0 * 360.0
    sat = hsv[..., 1].ravel() / 255.0
    val = hsv[..., 2].ravel() / 255.0

    keep = (sat >= _SAT_MIN) & (val >= _VAL_MIN) & (hue <= _SPECTRAL_HUE_MAX)
    hue = hue[keep]
    if hue.size == 0:
        return []

    counts, edges = np.histogram(hue, bins=_HUE_BINS, range=(0.0, _SPECTRAL_HUE_MAX))
    centers = (edges[:-1] + edges[1:]) / 2.0
    order = sorted(
        (i for i in range(_HUE_BINS) if counts[i] > 0),
        key=lambda i: (-int(counts[i]), float(centers[i])),  # stable: count desc, hue asc
    )[:max_colors]

    wavelengths: list[float] = []
    for i in sorted(order, key=lambda i: float(centers[i])):
        nm = _hue_to_wavelength_nm(float(centers[i]))
        if nm is not None:
            wavelengths.append(nm)
    return wavelengths


class ImageSignalAdapter:
    """Extract a derived signal from an image's global colour statistics.

    Implements the :class:`aureon.bio.human_harmonic_proxy.SignalAdapter` seam.
    Consent and provenance are **required arguments** — the adapter never
    fabricates them; the caller must affirmatively grant consent for the image.
    """

    modality: str = "image"

    def extract(
        self,
        spec: Any,
        *,
        consent: bool,
        provenance: str,
        max_colors: int = 8,
        downscale: int = 256,
        seed: int = 0,  # accepted for protocol symmetry; extraction is deterministic
    ) -> HumanSignal:
        """Return a :class:`HumanSignal` of light frequencies from ``spec``'s colours."""
        rgb = _load_rgb(spec, downscale=downscale)
        wavelengths = _dominant_wavelengths_nm(rgb, max_colors=max_colors)
        freqs = tuple(_wavelength_nm_to_hz(nm) for nm in wavelengths)
        label = f"image:{Path(spec).name}" if isinstance(spec, (str, Path)) else "image:array"
        return HumanSignal(
            label=label,
            frequencies_hz=freqs,
            provenance=provenance,
            consent=consent,
            modality=self.modality,
            notes=(
                f"{len(freqs)} dominant spectral hue(s) -> wavelength -> EM Hz "
                "(global colour statistics only; no face/person analysis)"
            ),
        )


def score_image(
    spec: Any,
    *,
    consent: bool,
    provenance: str,
    nulls: int = proxy.engine.DEFAULT_NULLS,
    seed: int = 0,
    max_colors: int = 8,
    downscale: int = 256,
) -> ProxyResult:
    """Extract an image's colour signal and score it through the governed pipeline."""
    signal = ImageSignalAdapter().extract(
        spec, consent=consent, provenance=provenance, max_colors=max_colors, downscale=downscale
    )
    return score_signal(signal, nulls=nulls, seed=seed)


def main(argv: list[str] | None = None) -> int:
    """CLI: score an image the caller consents to (or demonstrate the block)."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Score an image's colour-derived signal (content-agnostic, no face analysis)."
    )
    parser.add_argument("image", help="path to an image the caller consents to analyse")
    parser.add_argument("--consent", action="store_true", help="affirm consent to analyse this image")
    parser.add_argument("--provenance", default="", help="provenance string (required with --consent)")
    parser.add_argument("--nulls", type=int, default=proxy.engine.DEFAULT_NULLS)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    result = score_image(
        args.image,
        consent=bool(args.consent),
        provenance=args.provenance,
        nulls=args.nulls,
        seed=args.seed,
    )
    d = result.to_dict()
    print("Image signal adapter — colour -> wavelength -> frequency (no face analysis)")
    print(f"  image            : {args.image}")
    print(f"  boundary         : {SCIENTIFIC_BOUNDARY}")
    print(f"  n_tones          : {d['n_tones']}")
    print(f"  valid            : {d['valid']}")
    print(f"  blocked          : {d['blocked']}")
    print(f"  structure_present: {d['structure_present']}")
    print(f"  test_A_p / test_B_p : {d['test_A_p']} / {d['test_B_p']}")
    print(f"  reason           : {d['reason']}")
    return 0


if __name__ == "__main__":  # pragma: no cover - manual entry point
    raise SystemExit(main())
