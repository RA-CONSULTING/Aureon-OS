#!/usr/bin/env python3
"""Counter-frequency reference — the repo's φ/Fibonacci harmonic canon.

The observatory's other lanes carry planetary, Schumann, coherence, sacred-site,
and Master-Formula tones. This adds the one repo-native table anchored on the
**Fibonacci ladder and golden-ratio harmonics**: the ``SACRED_FREQUENCIES`` canon
of the planetary harmonic **counter-frequency** engine
(``aureon/harmonic/aureon_harmonic_counter_frequency.py``) — the module that FFTs
market/volume patterns and maps them to sacred harmonics. Its distinctive content
is the low-Hz Fibonacci tones (8·13·21·34) and φ-harmonics (φ, 2φ, 24/φ ≈ 14.83),
which no other observatory lane carries.

The literal constants are **copied** here (not imported) for the same reason the
other ``aureon/bio`` reference modules copy theirs: the source module runs an
import-time ``_baton_link`` heartbeat and imports ``requests``/``numpy``. Copying
keeps this module pure stdlib — no repo import, no network, no import-time writes.

Pure stdlib; no repo import, no network.
"""

from __future__ import annotations

import math
from typing import Final

from aureon.bio.human_harmonic_proxy import fold_to_band

__all__ = [
    "COUNTER_FREQUENCY_BOUNDARY",
    "PHI",
    "SACRED_FREQUENCIES",
    "FIBONACCI_HZ",
    "PHI_HARMONIC_HZ",
    "COUNTER_FREQUENCY_CITATION",
    "catalog_hz",
    "fibonacci_hz",
    "phi_harmonic_hz",
]

#: Golden ratio — the constant the φ-harmonics are built on.
PHI: Final[float] = (1 + math.sqrt(5)) / 2  # 1.618033988749895

COUNTER_FREQUENCY_BOUNDARY: Final[str] = (
    "The counter-frequency lane reports statistical structure in a derived tone "
    "set built from the repo's OWN φ/Fibonacci harmonic canon (the counter-"
    "frequency engine's SACRED_FREQUENCIES), scanned through one unchanged φ "
    "engine - NOT a claim about markets, whales, manipulation, consciousness, or "
    "any esoteric effect, and no efficacy claim. Each verdict is exactly what the "
    "pre-registered test returned."
)

#: Copied verbatim from aureon_harmonic_counter_frequency.SACRED_FREQUENCIES.
SACRED_FREQUENCIES: Final[dict[str, float]] = {
    "SCHUMANN_RESONANCE": 7.83,
    "FIBONACCI_8": 8.0,
    "FIBONACCI_13": 13.0,
    "FIBONACCI_21": 21.0,
    "FIBONACCI_34": 34.0,
    "PHI_HARMONIC": PHI,
    "DOUBLE_PHI": PHI * 2,
    "GOLDEN_CYCLE": 24.0 / PHI,  # ≈ 14.83
    "SOLFEGGIO_396": 396.0,
    "SOLFEGGIO_417": 417.0,
    "SOLFEGGIO_432": 432.0,
    "SOLFEGGIO_528": 528.0,
    "SOLFEGGIO_639": 639.0,
    "SOLFEGGIO_741": 741.0,
    "SOLFEGGIO_852": 852.0,
    "SOLFEGGIO_963": 963.0,
}

#: The distinctive Fibonacci-ladder tones (Hz) — new to the observatory.
FIBONACCI_HZ: Final[tuple[float, ...]] = (8.0, 13.0, 21.0, 34.0)
#: The golden-ratio harmonics (Hz): φ, 2φ, 24/φ.
PHI_HARMONIC_HZ: Final[tuple[float, ...]] = (PHI, PHI * 2, 24.0 / PHI)

COUNTER_FREQUENCY_CITATION: Final[str] = (
    "φ/Fibonacci harmonic canon (Fibonacci 8/13/21/34 + φ-harmonics + Solfeggio); "
    "repo: aureon/harmonic/aureon_harmonic_counter_frequency.SACRED_FREQUENCIES."
)


_CATALOGS = {
    "counter": tuple(sorted({round(v, 6) for v in SACRED_FREQUENCIES.values()})),
    "fibonacci": tuple(sorted(FIBONACCI_HZ)),
    "phi": tuple(sorted({round(v, 6) for v in PHI_HARMONIC_HZ})),
}


def catalog_hz(name: str) -> tuple[float, ...]:
    """Return a named counter-frequency catalog (raw Hz).

    'counter' is the full SACRED_FREQUENCIES canon; 'fibonacci' is the 8/13/21/34
    ladder; 'phi' is the φ / 2φ / 24-over-φ harmonics.
    """
    try:
        return _CATALOGS[name]
    except KeyError:
        raise ValueError(
            f"unknown counter-frequency catalog {name!r}; expected one of {sorted(_CATALOGS)}"
        ) from None


def fibonacci_hz() -> tuple[float, ...]:
    """The Fibonacci-ladder tones (8, 13, 21, 34 Hz)."""
    return FIBONACCI_HZ


def phi_harmonic_hz() -> tuple[float, ...]:
    """The golden-ratio harmonics (φ, 2φ, 24/φ Hz)."""
    return PHI_HARMONIC_HZ


def _assert_foldable() -> None:  # pragma: no cover - import-time sanity guard
    folded = [f for f in (fold_to_band(v) for v in catalog_hz("counter")) if f is not None]
    if len(folded) < 2:
        raise AssertionError("counter-frequency canon folds to < 2 tones")


_assert_foldable()
