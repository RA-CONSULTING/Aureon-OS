"""Tests for the cosmic scan — Schumann / planetary / space-weather through the engine.

The engine's φ logic is unchanged. These tests assert the machinery: the reused repo
frequency systems fold into the band and scan to valid deterministic results, the
governance holds, and the boundary is explicit and honest. No assertion is made about
what any cosmic system "should" score. Offline.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.bio import cosmic_reference as cosmic
from aureon.bio import cosmic_scan as cs
from aureon.bio import human_harmonic_proxy as proxy

NULLS = 300
_FORBIDDEN = ("aura", "spirit", "entity", "diagnos", "disease", "personality")


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


# ---------------------------------------------------------------------------
# reference data (reused repo systems)
# ---------------------------------------------------------------------------


def test_schumann_modes():
    assert cosmic.catalog_hz("schumann") == cosmic.SCHUMANN_MODES_HZ
    assert cosmic.SCHUMANN_MODES_HZ[0] == 7.83  # fundamental
    assert len(cosmic.SCHUMANN_MODES_HZ) == 7


def test_planetary_tones():
    assert cosmic.catalog_hz("planetary") == cosmic.PLANETARY_TONE_HZ
    assert set(cosmic.PLANETARY_TONE_MAP) == {
        "mercury", "venus", "earth", "mars", "jupiter", "saturn"
    }
    with pytest.raises(ValueError):
        cosmic.catalog_hz("nope")


def test_all_catalog_tones_fold_into_band():
    from aureon.bio.human_harmonic_proxy import fold_to_band

    low, high = proxy.TARGET_BAND_HZ
    for name in ("schumann", "planetary"):
        for f in cosmic.catalog_hz(name):
            folded = fold_to_band(f)
            assert folded is not None and low <= folded < high


def test_space_weather_pools_multiple_tones():
    tones = cosmic.space_weather_tones()
    low, high = proxy.TARGET_BAND_HZ
    assert len(tones) >= 2  # pooling Kp/ap/F107 clears the >=2 the engine needs
    assert all(low <= t < high for t in tones)


# ---------------------------------------------------------------------------
# scans (valid, deterministic, governed)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["schumann", "planetary"])
def test_cosmic_catalog_scan_valid_and_deterministic(name):
    r1 = cs.score_cosmic_catalog(name, nulls=NULLS, seed=0)
    r2 = cs.score_cosmic_catalog(name, nulls=NULLS, seed=0)
    assert r1.valid is True and r1.blocked is False
    assert r1.n_tones == len(cosmic.catalog_hz(name))
    assert (r1.test_A_p, r1.test_B_p) == (r2.test_A_p, r2.test_B_p)


def test_space_weather_scan_valid():
    r = cs.score_space_weather(nulls=NULLS)
    assert r.valid is True and r.blocked is False
    assert r.n_tones >= 2


def test_consent_gate_blocks():
    r = cs.score_cosmic_catalog("schumann", consent=False, provenance="x", nulls=100)
    assert r.blocked is True and r.valid is False
    assert r.to_dict()["structure_present"] is False


def test_cosmic_boundary_is_honest():
    low = cosmic.COSMIC_BOUNDARY.lower()
    assert "not a claim" in low
    assert "ionospheric" in low  # Schumann framed as real geophysics
    for w in _FORBIDDEN:
        assert w not in low, f"boundary leaked {w!r}"


def test_scan_result_boundary_present():
    r = cs.score_cosmic_catalog("planetary", nulls=NULLS)
    assert r.to_dict()["boundary"] == proxy.SCIENTIFIC_BOUNDARY


def test_missing_provenance_blocks_at_helper_layer():
    # the convenience helper defaults consent=True; a blank provenance must still block
    r = cs.score_cosmic_catalog("schumann", consent=True, provenance="  ", nulls=100)
    assert r.blocked is True


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(cs)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
