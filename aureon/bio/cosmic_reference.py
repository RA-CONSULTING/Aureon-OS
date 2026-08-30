#!/usr/bin/env python3
"""Cosmic reference — more of the repo's harmonic systems, directed at the sky.

The sky picture gets clearer as more of Aureon's existing frequency systems are
pointed at it. This module carries three real sky/space frequency systems already
present in the repo, as clean static data (the literal constants are copied here so
importing this module never trips the repo's import-time ``_baton_link`` side
effects). Each is scanned through the **unchanged** phenolic φ engine and reported
exactly as the test returns it.

Systems (with their in-repo sources and physical basis):
* **Schumann modes** — the Earth-ionosphere cavity ELF resonances
  (7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0 Hz). Real, measured geophysics; the same
  seven modes appear in ``aureon/harmonic/aureon_schumann_resonance_bridge.py``
  (``barcelona_modes``), ``aureon/harmonic/earth_resonance_engine.py``
  (``SCHUMANN_MODES``), and ``aureon/wisdom/maeshowe_seer_decode.py``.
* **Planetary tones** — the repo's planetary-frequency table
  (``aureon/wisdom/prime_sentinel_reclaimer.py::PLANETARY_FREQ``): each planet's
  rotation/orbital period octave-shifted up into the audio band (the "Cosmic Octave",
  Cousto). Derived from real astronomy.
* **Space weather** — real Kp / ap / F10.7 geomagnetic + solar-flux series
  (``data/sim_kp.csv``, 6-hourly), the solar-driven signal Dr. Auris Throne reads.

Pure stdlib + numpy; no repo import, no network.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Final

import numpy as np

from aureon.bio.human_harmonic_proxy import fold_to_band
from aureon.bio.upe_signal_adapter import _dominant_timeseries_hz

__all__ = [
    "COSMIC_BOUNDARY",
    "SCHUMANN_MODES_HZ",
    "PLANETARY_TONE_HZ",
    "PLANETARY_TONE_MAP",
    "SCHUMANN_CITATION",
    "PLANETARY_CITATION",
    "SPACE_WEATHER_CITATION",
    "catalog_hz",
    "load_space_weather",
    "space_weather_tones",
]

COSMIC_BOUNDARY: Final[str] = (
    "Statistical structure in a derived signal only - the Schumann modes are Earth's "
    "ionospheric ELF resonances, the planetary tones are octave-shifted orbital/rotation "
    "periods, the space-weather series is real geomagnetic/solar flux; NOT a claim about "
    "consciousness, health, or any esoteric effect, and no efficacy claim."
)

#: Earth-ionosphere Schumann cavity resonances (Hz), the standard seven modes.
SCHUMANN_MODES_HZ: Final[tuple[float, ...]] = (7.83, 14.3, 20.8, 27.3, 33.8, 39.0, 45.0)

#: Planetary tones (Hz) — octave-shifted rotation/orbital periods (Cousto Cosmic Octave),
#: the repo's ``prime_sentinel_reclaimer.PLANETARY_FREQ`` table.
PLANETARY_TONE_MAP: Final[dict[str, float]] = {
    "mercury": 141.27,
    "venus": 221.23,
    "earth": 194.18,
    "mars": 144.72,
    "jupiter": 183.58,
    "saturn": 147.85,
}
PLANETARY_TONE_HZ: Final[tuple[float, ...]] = tuple(sorted(PLANETARY_TONE_MAP.values()))

SCHUMANN_CITATION: Final[str] = (
    "Schumann Earth-ionosphere cavity resonances 7.83/14.3/20.8/27.3/33.8/39.0/45.0 Hz "
    "(standard modes; repo: aureon_schumann_resonance_bridge, earth_resonance_engine)."
)
PLANETARY_CITATION: Final[str] = (
    "Planetary tones (Hz) = octave-shifted orbital/rotation periods (Cosmic Octave); "
    "repo: aureon/wisdom/prime_sentinel_reclaimer.PLANETARY_FREQ."
)
SPACE_WEATHER_CITATION: Final[str] = (
    "Kp / ap / F10.7 geomagnetic + solar-flux series (data/sim_kp.csv, 6-hourly "
    "2023-2024); real solar-driven space weather."
)

_CATALOGS = {
    "schumann": SCHUMANN_MODES_HZ,
    "planetary": PLANETARY_TONE_HZ,
}

_DEFAULT_SPACE_WEATHER: Final[str] = "data/sim_kp.csv"
_SW_CHANNELS: Final[tuple[str, ...]] = ("Kp", "ap", "F107")


def catalog_hz(name: str) -> tuple[float, ...]:
    """Return a named cosmic frequency list (Hz): 'schumann' or 'planetary'."""
    try:
        return _CATALOGS[name]
    except KeyError:
        raise ValueError(
            f"unknown cosmic catalog {name!r}; expected one of {sorted(_CATALOGS)}"
        ) from None


def load_space_weather(path: str | Path = _DEFAULT_SPACE_WEATHER) -> dict[str, np.ndarray]:
    """Load the Kp / ap / F10.7 series (ordered by datetime) from ``sim_kp.csv``."""
    p = Path(path)
    if not p.exists():
        return {}
    rows = list(csv.DictReader(p.open("r", newline="", encoding="utf-8")))
    rows.sort(key=lambda r: str(r.get("datetime", "")))
    out: dict[str, np.ndarray] = {}
    for ch in _SW_CHANNELS:
        vals = []
        for r in rows:
            try:
                vals.append(float(r[ch]))
            except (KeyError, ValueError, TypeError):
                vals.append(np.nan)
        arr = np.array(vals, dtype=float)
        out[ch] = arr[np.isfinite(arr)]
    return out


def space_weather_tones(path: str | Path = _DEFAULT_SPACE_WEATHER) -> tuple[float, ...]:
    """Pooled dominant folded tones from the Kp / ap / F10.7 channels.

    Each channel's dominant temporal frequencies (via the timeseries sensor) fold into
    the band; pooling the three solar-driven channels yields the >= 2 tones the engine
    needs (each channel alone is dominated by ~one period, e.g. the 27-day solar
    rotation in F10.7).
    """
    channels = load_space_weather(path)
    tones: list[float] = []
    for ch in _SW_CHANNELS:
        series = channels.get(ch)
        if series is None or series.size < 4:
            continue
        raw = _dominant_timeseries_hz(series, sample_rate_hz=1.0, max_peaks=12)
        tones.extend(f for f in (fold_to_band(v) for v in raw) if f is not None)
    return tuple(sorted(tones))
