"""Tests for cosmic_reference — Schumann / planetary / space-weather data.

Pure data module (copies the repo's constants so importing never trips the baton-link
side effects). Asserts the catalogs fold into the band, the space-weather loader reads
the real series, and the boundary is honest.
"""

from __future__ import annotations

import pytest

from aureon.bio import cosmic_reference as cosmic
from aureon.bio.human_harmonic_proxy import TARGET_BAND_HZ, fold_to_band


def test_schumann_modes():
    assert cosmic.catalog_hz("schumann") == cosmic.SCHUMANN_MODES_HZ
    assert cosmic.SCHUMANN_MODES_HZ[0] == 7.83
    assert len(cosmic.SCHUMANN_MODES_HZ) == 7


def test_planetary_table():
    assert cosmic.catalog_hz("planetary") == cosmic.PLANETARY_TONE_HZ
    assert set(cosmic.PLANETARY_TONE_MAP) == {
        "mercury", "venus", "earth", "mars", "jupiter", "saturn"
    }
    assert all(100.0 < hz < 300.0 for hz in cosmic.PLANETARY_TONE_HZ)
    with pytest.raises(ValueError):
        cosmic.catalog_hz("nope")


def test_catalogs_fold_into_band():
    low, high = TARGET_BAND_HZ
    for name in ("schumann", "planetary"):
        for f in cosmic.catalog_hz(name):
            folded = fold_to_band(f)
            assert folded is not None and low <= folded < high


def test_space_weather_loader_and_tones():
    channels = cosmic.load_space_weather()
    if channels:  # sim_kp.csv present
        for ch in ("Kp", "ap", "F107"):
            assert ch in channels and channels[ch].size > 4
        tones = cosmic.space_weather_tones()
        low, high = TARGET_BAND_HZ
        assert len(tones) >= 2
        assert all(low <= t < high for t in tones)


def test_boundary_is_honest():
    low = cosmic.COSMIC_BOUNDARY.lower()
    assert "not a claim" in low
    assert "ionospheric" in low
    for w in ("aura", "spirit", "diagnos", "personality"):
        assert w not in low
