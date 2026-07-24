#!/usr/bin/env python3
"""Sky reference — real open astronomical line lists for scanning light from space.

"Same song, different singer": the *same* phenolic engine — with its φ (golden-ratio)
logic used exactly as-is — is pointed at light directed at us from space instead of
molecules. This module holds the real, openly published line data the sky adapter
scans, plus the two control references every governed scan uses.

The engine's logic is unchanged. Test A (coherence clustering) and Test B
(golden-interval alignment) and the controls are the same code that scores molecules
and everything else; this module only supplies sky data and reports what the test
returns.

Data (open, standard values):
* Hydrogen **Balmer series** air wavelengths (n→2), NIST ASD / standard.
* Solar **Fraunhofer** absorption lines (canonical set), standard air wavelengths.
* The neutral-hydrogen **21 cm** line (1420.405751768 MHz) — the Wow!-signal band.

Two control references (mirrors the engine's own control arms, not a claim either way):
* ``continuum_spectrum`` — a smooth, featureless continuum (the negative-control
  reference: noise must not over-fire the scan).
* ``structured_spectrum`` — a planted-coherence spectrum (the positive-control
  demonstration: the scan detects real clustered + φ structure when it is present).

Pure stdlib + numpy + engine constants; no astropy/skyfield dependency.
"""

from __future__ import annotations

from typing import Final

import phenolic_fingerprint as engine
from aureon.bio.human_harmonic_proxy import fold_to_band
from aureon.bio.image_signal_adapter import _wavelength_nm_to_hz

__all__ = [
    "HYDROGEN_BALMER_NM",
    "SOLAR_FRAUNHOFER_NM",
    "AIRGLOW_NM",
    "HYDROGEN_21CM_HZ",
    "SKY_CITATION",
    "AIRGLOW_CITATION",
    "OPTICAL_BAND_NM",
    "catalog_nm",
    "continuum_spectrum",
    "continuum_modulation_tones",
    "diffuse_night_sky_spectrum",
    "structured_spectrum",
]

PHI: float = float(engine.PHI)

#: Hydrogen Balmer series (n→2), air wavelengths in nm (Hα … Hη). NIST ASD.
HYDROGEN_BALMER_NM: Final[tuple[float, ...]] = (
    656.279,  # H-alpha   (n=3)
    486.135,  # H-beta    (n=4)
    434.047,  # H-gamma   (n=5)
    410.174,  # H-delta   (n=6)
    397.007,  # H-epsilon (n=7)
    388.905,  # H-zeta    (n=8)
    383.539,  # H-eta     (n=9)
)

#: Solar Fraunhofer absorption lines (canonical set), standard air nm.
SOLAR_FRAUNHOFER_NM: Final[tuple[float, ...]] = (
    759.370,   # A   O2
    686.719,   # B   O2
    656.281,   # C   H-alpha
    627.661,   # a   O2
    589.592,   # D1  Na
    588.995,   # D2  Na
    587.5618,  # D3  He
    546.073,   # e   Hg
    527.039,   # E2  Fe
    518.362,   # b1  Mg
    517.270,   # b2  Mg
    516.733,   # b4  Mg
    495.761,   # c   Fe
    486.134,   # F   H-beta
    466.814,   # d   Fe
    438.355,   # e   Fe
    434.047,   # G'  H-gamma
    430.790,   # G   Fe/Ca
    410.175,   # h   H-delta
    396.847,   # H   Ca+
    393.368,   # K   Ca+
)

#: Airglow / nightglow emission lines — the *real* faint self-emission of the night
#: sky (standard air nm). This is the honest "UPE-from-the-sky" analog: UPE proper is
#: biological (biophotons from living tissue); the sky does not emit biophotons. What
#: the sky itself faintly emits is airglow — atomic oxygen, the mesospheric sodium
#: layer, molecular oxygen, and the OH Meinel bands. Standard nightglow values
#: (Chamberlain, *Physics of the Aurora and Airglow*; Meinel 1950 for OH).
AIRGLOW_NM: Final[tuple[float, ...]] = (
    557.7339,  # O I     green line (¹S→¹D) — the dominant nightglow line
    589.0,     # Na D2   mesospheric sodium layer
    589.6,     # Na D1   mesospheric sodium layer
    630.0304,  # O I     red doublet (¹D→³P₂)
    636.3776,  # O I     red doublet (¹D→³P₁)
    761.9,     # O2      atmospheric A-band (0-0)
    864.5,     # O2      atmospheric band (0-1), nightglow
    730.0,     # OH      Meinel band head (8-3), approx standard value
    803.0,     # OH      Meinel band head (5-1), approx standard value
    840.0,     # OH      Meinel band head (6-2), approx standard value
)

#: Neutral-hydrogen 21 cm hyperfine line (Hz) — the Wow!-signal / SETI band.
HYDROGEN_21CM_HZ: Final[float] = 1_420_405_751.768

SKY_CITATION: Final[str] = (
    "Hydrogen Balmer + solar Fraunhofer lines (standard air nm, NIST ASD); "
    "HI 21 cm line 1420.405751768 MHz. Open/standard reference values."
)

AIRGLOW_CITATION: Final[str] = (
    "Night-sky airglow emission (atomic O 557.7/630.0/636.4 nm, Na D 589.0/589.6 nm, "
    "O2 atmospheric bands, OH Meinel bands), standard nightglow reference values. "
    "The sky's own faint self-emission — NOT biological UPE."
)

OPTICAL_BAND_NM: Final[tuple[float, float]] = (380.0, 760.0)

#: The optical span the airglow catalog reaches (extends past OPTICAL_BAND_NM into the
#: near-IR OH/O2 bands, which are genuine airglow features).
AIRGLOW_BAND_NM: Final[tuple[float, float]] = (380.0, 900.0)

_CATALOGS = {
    "balmer": HYDROGEN_BALMER_NM,
    "fraunhofer": SOLAR_FRAUNHOFER_NM,
    "airglow": AIRGLOW_NM,
}


def catalog_nm(name: str) -> tuple[float, ...]:
    """Return a named real line list (nm): 'balmer' or 'fraunhofer'."""
    try:
        return _CATALOGS[name]
    except KeyError:
        raise ValueError(
            f"unknown sky catalog {name!r}; expected one of {sorted(_CATALOGS)}"
        ) from None


def continuum_spectrum(n: int = 241) -> list[tuple[float, float]]:
    """Featureless optical continuum (nm, relative intensity) — negative-control ref.

    A smooth blackbody-like slope across ``OPTICAL_BAND_NM`` with no lines. Used as
    the scan's negative-control reference (noise must not over-fire).
    """
    if n < 2:
        raise ValueError("n must be >= 2")
    low, high = OPTICAL_BAND_NM
    step = (high - low) / (n - 1)
    out: list[tuple[float, float]] = []
    for i in range(n):
        nm = low + i * step
        out.append((nm, 1.0 + 0.3 * (high - nm) / (high - low)))
    return out


def continuum_modulation_tones(n: int = 241) -> list[float]:
    """Fold the featureless continuum's samples into the engine's modulation band."""
    tones = []
    for nm, _ in continuum_spectrum(n):
        f = fold_to_band(_wavelength_nm_to_hz(nm))
        if f is not None:
            tones.append(f)
    return sorted(tones)


def diffuse_night_sky_spectrum(n: int = 241) -> list[tuple[float, float]]:
    """The diffuse night-sky background (nm, relative intensity) — featureless ref.

    The optical diffuse night-sky background (integrated starlight + zodiacal light +
    diffuse galactic light + the airglow continuum) is broadly smooth, with no
    discrete lines. This is the honest UPE-from-the-sky non-structure anchor: a
    featureless faint glow peak-picks to nothing and therefore scans non-separable —
    structure is reported only when the sky genuinely carries discrete lines
    (:data:`AIRGLOW_NM`), never by fiat. Implemented as the smooth continuum.
    """
    return continuum_spectrum(n)


def _fold_band_vec(f_hz):  # numpy array in, array out
    import numpy as np

    k = np.floor(np.log2(f_hz / 1000.0))
    return f_hz / (2.0 ** k)


def _wavelengths_for_tones(targets: list[float]) -> list[float]:
    """Optical-band wavelengths (nm) that octave-fold to the given modulation tones."""
    import numpy as np

    low, high = OPTICAL_BAND_NM
    grid = np.linspace(low, high, 400_001)
    f = (engine.NM_TO_THZ_NUMERATOR / grid) * engine.THZ_TO_HZ
    folded = _fold_band_vec(f)
    return [float(grid[int(np.argmin(np.abs(folded - t)))]) for t in targets]


def structured_spectrum(n: int = 4000) -> list[tuple[float, float]]:
    """Continuum + planted lines whose folded tones form a clustered + φ set.

    The positive-control demonstration: two tight clusters one golden ratio apart in
    the modulation band, back-solved to optical wavelengths and planted as sharp
    lines, so the scan is shown to detect real coherence when it is present.
    """
    import numpy as np

    centers = 1100.0 * np.array([1.0, PHI])
    offsets = np.array([-8.0, 0.0, 8.0])
    target_tones = list((centers[:, None] + offsets[None, :]).ravel())
    line_nm = _wavelengths_for_tones(target_tones)
    low, high = OPTICAL_BAND_NM
    nm = np.linspace(low, high, n)
    base = np.array(continuum_spectrum(min(n, 400)), dtype=float)
    y = np.interp(nm, base[:, 0], base[:, 1])
    for c in line_nm:
        y = y + 0.9 * np.exp(-((nm - c) ** 2) / (2.0 * 0.4 ** 2))
    return [(float(w), float(v)) for w, v in zip(nm, y, strict=False)]


if __name__ == "__main__":  # pragma: no cover - manual scan of the real catalogs
    import numpy as np

    for name in ("balmer", "fraunhofer"):
        lines = catalog_nm(name)
        tones = np.array(sorted(
            f for f in (fold_to_band(_wavelength_nm_to_hz(w)) for w in lines) if f is not None
        ))
        p_a = engine.test_A(tones, nulls=500, rng=np.random.default_rng([0, 1]))
        p_b = engine.test_B(tones, nulls=500, rng=np.random.default_rng([0, 2]))
        sep = bool(p_a < engine.ALPHA and p_b < engine.ALPHA)
        print(f"{name:11s} n={len(lines):2d} lines -> A_p={p_a:.4f} B_p={p_b:.4f} separable={sep}")
