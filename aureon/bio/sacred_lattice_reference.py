#!/usr/bin/env python3
"""Sacred-lattice reference — the repo's OWN way of mapping the sky.

Others map the sky with object catalogs and physics tables (the observatory's
conventional lanes already do that). Aureon maps it differently: through **Earth's
harmonic lattice** — the coordinates of ancient sites, φ-scaled sacred geometry, and
the Solfeggio/Schumann canon that runs through the HNC thread
(Ziggurat → Pyramid → Maeshowe → Wow!). This module carries three of the repo's own
frequency/position systems as clean static data so each can be scanned through the
**unchanged** phenolic φ engine.

The literal constants are **copied** here (not imported from ``aureon.wisdom``) for the
same reason ``cosmic_reference`` copies its tables: importing any ``aureon/wisdom/*``
module runs an import-time ``_baton_link`` heartbeat that writes ``logs/…jsonl`` and
wires the Mycelium sonar. Copying the constants keeps this module pure stdlib + numpy —
no repo import, no network, no import-time writes.

Systems (with their in-repo sources):
* **Stargate lattice** — ``aureon/wisdom/aureon_stargate_protocol.py::PLANETARY_STARGATES``:
  12 ancient sites, each with lat/lon + a resonance frequency + a 3-tone harmonic
  signature (Göbekli Tepe's ``7.83·φ·10 ≈ 126.7 Hz`` among them).
* **Maeshowe solstice** — ``aureon/wisdom/maeshowe_seer_decode.py``: the Solfeggio ×
  Schumann-mode lattice, the four ``WALL_AURIS`` Auris-node frequencies, and the
  chamber standing wave ``343/(2·4.57) ≈ 37.5 Hz``.
* **Metatron φ-geometry** — ``aureon/wisdom/metatrons_cube_knowledge_exchange.py``: the
  13-sphere set — a central Love tone plus 12 φ-scaled icosahedral vertices — each
  carrying a Solfeggio / Schumann-harmonic frequency.

Pure stdlib + numpy; no repo import, no network.
"""

from __future__ import annotations

import math
from typing import Final

from aureon.bio.human_harmonic_proxy import fold_to_band

__all__ = [
    "SACRED_LATTICE_BOUNDARY",
    "PHI",
    "STARGATE_NODES",
    "MAESHOWE_LATTICE_HZ",
    "METATRON_TONES_HZ",
    "METATRON_POSITIONS",
    "STARGATE_CITATION",
    "MAESHOWE_CITATION",
    "METATRON_CITATION",
    "catalog_hz",
    "stargate_positions",
]

#: Golden ratio — the constant the whole lattice is scaled by.
PHI: Final[float] = (1 + math.sqrt(5)) / 2  # 1.618033988749895

SACRED_LATTICE_BOUNDARY: Final[str] = (
    "The sacred-lattice lanes report statistical structure in a derived tone set built "
    "from the repo's OWN sacred-site / φ-geometry frequency tables, scanned through one "
    "unchanged φ engine - NOT a claim about ancient sites, ley lines, consciousness, or "
    "any esoteric effect, and no efficacy claim. Lattice-map coordinates are Earth "
    "sacred-site positions, not celestial RA/Dec. Each verdict is exactly what the "
    "pre-registered test returned."
)

#: 12 ancient-site nodes (name, latitude, longitude, resonance_hz, signature_hz).
#: Copied verbatim from ``PLANETARY_STARGATES``; Göbekli Tepe's resonance is 7.83·φ·10.
STARGATE_NODES: Final[tuple[tuple[str, float, float, float, tuple[float, ...]], ...]] = (
    ("Great Pyramid of Giza", 29.9792, 31.1342, 432.0, (432.0, 528.0, 963.0)),
    ("Stonehenge", 51.1789, -1.8262, 396.0, (396.0, 528.0, 741.0)),
    ("Uluru (Ayers Rock)", -25.3444, 131.0369, 174.0, (174.0, 285.0, 639.0)),
    ("Machu Picchu", -13.1631, -72.5450, 528.0, (528.0, 639.0, 852.0)),
    ("Angkor Wat", 13.4125, 103.8670, 639.0, (396.0, 639.0, 963.0)),
    ("Glastonbury Tor", 51.1442, -2.6987, 852.0, (417.0, 528.0, 852.0)),
    ("Sedona Vortex", 34.8697, -111.7610, 741.0, (285.0, 528.0, 741.0)),
    ("Teotihuacan", 19.6925, -98.8438, 417.0, (396.0, 417.0, 963.0)),
    ("Mount Shasta", 41.3099, -122.3106, 963.0, (528.0, 852.0, 963.0)),
    ("Newgrange", 53.6947, -6.4754, 285.0, (174.0, 285.0, 528.0)),
    ("Göbekli Tepe", 37.2236, 38.9225, 7.83 * PHI * 10, (126.7, 432.0, 528.0)),
    ("Baalbek", 34.0067, 36.2039, 432.0, (396.0, 432.0, 741.0)),
)

#: Maeshowe lattice: Solfeggio (9) + Schumann modes (7) + WALL_AURIS node freqs +
#: the ~37.5 Hz chamber standing wave. Copied from ``maeshowe_seer_decode``.
_SOLFEGGIO: Final[tuple[float, ...]] = (174, 285, 396, 417, 528, 639, 741, 852, 963)
_SCHUMANN_MODES: Final[tuple[float, ...]] = (7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0)
_WALL_AURIS_HZ: Final[tuple[float, ...]] = (528.0, 396.0, 174.0, 210.0)  # OWL/DEER/CARGOSHIP/FALCON
_CHAMBER_STANDING_WAVE_HZ: Final[float] = 343.0 / (2 * 4.57)  # ≈ 37.5 Hz
MAESHOWE_LATTICE_HZ: Final[tuple[float, ...]] = tuple(sorted(set(
    _SOLFEGGIO + _SCHUMANN_MODES + _WALL_AURIS_HZ + (round(_CHAMBER_STANDING_WAVE_HZ, 2),)
)))

#: Metatron's Cube 13 spheres: central Love tone + 12 φ-scaled icosahedral vertices,
#: each carrying a Solfeggio / Schumann-harmonic frequency. Copied from the source.
_METATRON_OUTER_HZ: Final[tuple[float, ...]] = (
    396, 417, 432, 528, 639, 741, 852, 963,  # Solfeggio
    7.83, 14.1, 20.8, 27.3,                   # Schumann harmonics
)
METATRON_TONES_HZ: Final[tuple[float, ...]] = (528.0, *(float(f) for f in _METATRON_OUTER_HZ))
#: 13 positions: centre + the 12 icosahedral vertices (±1, 0, ±φ) and permutations.
METATRON_POSITIONS: Final[tuple[tuple[float, float, float], ...]] = (
    (0.0, 0.0, 0.0),
    (1, 0, PHI), (-1, 0, PHI), (1, 0, -PHI), (-1, 0, -PHI),
    (0, PHI, 1), (0, PHI, -1), (0, -PHI, 1), (0, -PHI, -1),
    (PHI, 1, 0), (-PHI, 1, 0), (PHI, -1, 0), (-PHI, -1, 0),
)

STARGATE_CITATION: Final[str] = (
    "12 ancient-site nodes (lat/lon + resonance + 3-tone harmonic signature); repo: "
    "aureon/wisdom/aureon_stargate_protocol.PLANETARY_STARGATES."
)
MAESHOWE_CITATION: Final[str] = (
    "Solfeggio × Schumann-mode lattice + WALL_AURIS node freqs + ~37.5 Hz chamber "
    "standing wave; repo: aureon/wisdom/maeshowe_seer_decode."
)
METATRON_CITATION: Final[str] = (
    "13-sphere set: central Love tone + 12 φ-scaled icosahedral vertices, each with a "
    "Solfeggio/Schumann-harmonic freq; repo: aureon/wisdom/metatrons_cube_knowledge_exchange."
)


def _stargate_tones() -> tuple[float, ...]:
    """Every stargate node's resonance + harmonic-signature tones, pooled (raw Hz)."""
    tones: list[float] = []
    for _name, _lat, _lon, resonance, signature in STARGATE_NODES:
        tones.append(float(resonance))
        tones.extend(float(f) for f in signature)
    return tuple(sorted(set(tones)))


_CATALOGS = {
    "stargate": _stargate_tones(),
    "maeshowe": MAESHOWE_LATTICE_HZ,
    # METATRON_TONES_HZ is in sphere order (centre first, dup Love tone); the scan
    # view is sorted + deduped like the other catalogs.
    "metatron": tuple(sorted(set(METATRON_TONES_HZ))),
}


def catalog_hz(name: str) -> tuple[float, ...]:
    """Return a named sacred-lattice frequency list (raw Hz).

    'stargate' pools every node's resonance + harmonic-signature tones; 'maeshowe' is
    the Solfeggio × Schumann lattice; 'metatron' is the 13-sphere tone set.
    """
    try:
        return _CATALOGS[name]
    except KeyError:
        raise ValueError(
            f"unknown sacred-lattice catalog {name!r}; expected one of {sorted(_CATALOGS)}"
        ) from None


def stargate_positions() -> list[tuple[str, float, float, tuple[float, ...]]]:
    """The stargate nodes as (name, lat, lon, folded_tones) for the positional map lane.

    Each node's harmonic-signature tones are octave-folded into the modulation band so a
    positional grid can pool ``>= 2`` tones per cell and run Test A / Test B. Coordinates
    are Earth sacred-site lat/lon — not celestial RA/Dec (see the boundary).
    """
    out: list[tuple[str, float, float, tuple[float, ...]]] = []
    for name, lat, lon, _resonance, signature in STARGATE_NODES:
        folded = tuple(sorted(
            f for f in (fold_to_band(v) for v in signature) if f is not None
        ))
        out.append((name, float(lat), float(lon), folded))
    return out
