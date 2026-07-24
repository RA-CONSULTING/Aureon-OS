#!/usr/bin/env python3
"""Ultraweak photon emission (UPE) reference model — the honest science anchor.

UPE (a.k.a. biophoton emission) is a real, peer-reviewed phenomenon: living
tissue spontaneously emits extremely low-intensity light from reactive-oxygen-
species chemistry in normal metabolism, and it ceases at death. Two facts from the
literature are load-bearing here and are encoded as constants below:

* **Intensity** ~10–10³ photons/cm²/s — 1,000 to 1,000,000× dimmer than the human
  eye can perceive; only measurable with cooled photon-counting cameras (EMCCD/PMT)
  in total darkness.
* **Spectrum** ~200–800 nm (full range to 1000 nm), a **nearly flat, broadband
  distribution with no distinct spectral lines** and only a subtle maximum in the
  orange (~600 nm).

Sources: Calgary study, *J. Phys. Chem. Lett.* 2024 (doi:10.1021/acs.jpclett.4c03546);
bioRxiv 2024.11.08.622743; biophoton spectral reviews (arXiv:2305.09524,
arXiv:2511.11080).

**Why this matters for the HNC.** Because a true UPE spectrum is *broadband and
featureless*, it carries **no discrete harmonic peaks** — so when its modulation
tones are pushed through the phenolic engine's pre-registered tests, it should come
out **non-separable** (no coherence clustering, no φ-interval structure). This
module exists so any HNC "UPE render" is anchored to that honest result rather than
to invented structure. A standard photograph records *reflected ambient light*,
never UPE, so nothing here claims to measure UPE from an ordinary image.
"""

from __future__ import annotations

import math
from typing import Final

from aureon.bio.human_harmonic_proxy import fold_to_band
from aureon.bio.image_signal_adapter import _wavelength_nm_to_hz

__all__ = [
    "UPE_BAND_NM",
    "UPE_FLUX_PHOTONS_CM2_S",
    "UPE_SUBTLE_MAX_NM",
    "UPE_CITATION",
    "reference_spectrum",
    "reference_modulation_tones",
]

# Literature-reported UPE facts (cited above). Constants, not tunables.
UPE_BAND_NM: Final[tuple[float, float]] = (200.0, 800.0)
UPE_FLUX_PHOTONS_CM2_S: Final[tuple[float, float]] = (10.0, 1000.0)
UPE_SUBTLE_MAX_NM: Final[float] = 600.0  # subtle broadband maximum, orange region
UPE_CITATION: Final[str] = (
    "UPE reference: flat 200-800 nm, ~10-1e3 photons/cm2/s, subtle orange max "
    "(J. Phys. Chem. Lett. 2024, doi:10.1021/acs.jpclett.4c03546; bioRxiv 2024.11.08.622743)"
)

# Shape parameters for the *nearly flat* reference profile (broadband, no lines).
_FLAT_BASE: Final[float] = 1.0            # flat continuum level
_ORANGE_BUMP_AMPLITUDE: Final[float] = 0.15  # subtle (15%) maximum near 600 nm
_ORANGE_BUMP_WIDTH_NM: Final[float] = 90.0


def reference_spectrum(n: int = 121) -> list[tuple[float, float]]:
    """Return ``n`` (wavelength_nm, relative_intensity) samples of the UPE reference.

    A deterministic, nearly-flat broadband profile across ``UPE_BAND_NM`` with a
    subtle Gaussian maximum near ``UPE_SUBTLE_MAX_NM`` — the shape the biophoton
    literature reports. Intentionally *featureless*: this is a smooth reference, not
    a line spectrum, and it is not presented as a measurement of any organism.
    """
    if n < 2:
        raise ValueError("n must be >= 2")
    low, high = UPE_BAND_NM
    step = (high - low) / (n - 1)
    out: list[tuple[float, float]] = []
    for i in range(n):
        nm = low + i * step
        bump = _ORANGE_BUMP_AMPLITUDE * math.exp(
            -((nm - UPE_SUBTLE_MAX_NM) ** 2) / (2.0 * _ORANGE_BUMP_WIDTH_NM ** 2)
        )
        out.append((nm, _FLAT_BASE + bump))
    return out


def reference_modulation_tones(n: int = 121) -> list[float]:
    """Map the UPE reference wavelengths into the engine's modulation band (Hz).

    Each sampled wavelength → EM frequency (engine constants) → octave-folded into
    1000–2000 Hz. Because the source spectrum is broadband, these tones are spread
    across the band with no discrete clustering — the honest non-structure that the
    phenolic engine's tests should report.
    """
    tones: list[float] = []
    for nm, _intensity in reference_spectrum(n):
        folded = fold_to_band(_wavelength_nm_to_hz(nm))
        if folded is not None:
            tones.append(folded)
    return sorted(tones)


if __name__ == "__main__":  # pragma: no cover - manual anchor check
    import numpy as np

    import phenolic_fingerprint as engine

    tones = np.array(reference_modulation_tones())
    p_a = engine.test_A(tones, nulls=500, rng=np.random.default_rng([0, 1]))
    p_b = engine.test_B(tones, nulls=500, rng=np.random.default_rng([0, 2]))
    print(f"UPE reference tones: {tones.size}")
    print(f"  test_A (clustering) p = {p_a:.4f}")
    print(f"  test_B (phi)        p = {p_b:.4f}")
    print(f"  separable (both<0.05) = {bool(p_a < 0.05 and p_b < 0.05)}  "
          f"(expected False — UPE is broadband/featureless)")
