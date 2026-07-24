"""Tests for the real-NASA sky data lane — offline, reads the committed cache.

The engine's φ logic is unchanged. These tests assert the machinery around the
NASA Exoplanet Archive snapshot: the conversions (Wien nm, period→Hz→fold) land
where they should, a scan of the cached data is valid and deterministic, and the
governance gate holds. No assertion is made about what the real sky "should"
score. No network access — everything reads the committed CSV.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio.sky_signal_adapter import SkySignalAdapter, score_sky
from scripts.validation.benchmark_nasa_sky import (
    DEFAULT_CACHE,
    SECONDS_PER_DAY,
    WIEN_NM_K,
    orbital_frequencies_hz,
    stellar_peak_wavelengths_nm,
)
from scripts.validation.fetch_nasa_sky_data import FIELDS, read_cache

NULLS = 200

pytestmark = pytest.mark.skipif(
    not DEFAULT_CACHE.exists(), reason="NASA cache not present (offline fetch skipped)"
)


class _StubConscience:
    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name="APPROVED"), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience())


# ---------------------------------------------------------------------------
# cache shape
# ---------------------------------------------------------------------------


def test_cache_reads_real_rows():
    rows = read_cache(DEFAULT_CACHE)
    assert len(rows) > 0
    for r in rows[:5]:
        assert set(FIELDS) <= set(r)
        assert float(r["st_teff"]) > 0
        assert float(r["pl_orbper"]) > 0


# ---------------------------------------------------------------------------
# conversions
# ---------------------------------------------------------------------------


def test_wien_wavelengths_are_physical():
    rows = read_cache(DEFAULT_CACHE)
    nm = stellar_peak_wavelengths_nm(rows)
    assert nm
    # Wien peak wavelength is physical: hot O-stars peak in the EUV (~50 nm),
    # cool M-dwarfs in the near-IR (~1200 nm). All finite and positive.
    assert all(40.0 < w < 1300.0 for w in nm)
    # spot-check the formula on the first row
    teff = float(rows[0]["st_teff"])
    assert nm[0] == pytest.approx(WIEN_NM_K / teff)


def test_orbital_frequencies_fold_into_band():
    rows = read_cache(DEFAULT_CACHE)
    freqs = orbital_frequencies_hz(rows)
    assert freqs
    # raw orbital frequencies are tiny (sub-Hz); spot-check the formula
    period = float(rows[0]["pl_orbper"])
    assert freqs[0] == pytest.approx(1.0 / (period * SECONDS_PER_DAY))
    # after folding they land in the modulation band
    sig = SkySignalAdapter().extract(freqs, consent=True, provenance="test", kind="radio_hz")
    low, high = proxy.TARGET_BAND_HZ
    assert sig.frequencies_hz
    assert all(low <= f < high for f in sig.frequencies_hz)


# ---------------------------------------------------------------------------
# scan through the engine (deterministic, valid, governed)
# ---------------------------------------------------------------------------


def test_stellar_scan_is_valid_and_deterministic():
    rows = read_cache(DEFAULT_CACHE)
    nm = stellar_peak_wavelengths_nm(rows)
    r1 = score_sky(nm, consent=True, provenance="test", kind="lines", nulls=NULLS, seed=0)
    r2 = score_sky(nm, consent=True, provenance="test", kind="lines", nulls=NULLS, seed=0)
    assert r1.valid is True and r1.blocked is False
    assert r1.n_tones > 0
    assert (r1.test_A_p, r1.test_B_p) == (r2.test_A_p, r2.test_B_p)


def test_orbital_scan_is_valid():
    rows = read_cache(DEFAULT_CACHE)
    freqs = orbital_frequencies_hz(rows)
    r = score_sky(freqs, consent=True, provenance="test", kind="radio_hz", nulls=NULLS)
    assert r.valid is True and r.blocked is False
    assert r.n_tones > 0


def test_consent_gate_blocks():
    rows = read_cache(DEFAULT_CACHE)
    nm = stellar_peak_wavelengths_nm(rows)
    r = score_sky(nm, consent=False, provenance="x", kind="lines", nulls=100)
    assert r.blocked is True and r.valid is False
    assert r.to_dict()["structure_present"] is False


def test_boundary_present():
    rows = read_cache(DEFAULT_CACHE)
    nm = stellar_peak_wavelengths_nm(rows)
    r = score_sky(nm, consent=True, provenance="test", kind="lines", nulls=NULLS)
    assert r.to_dict()["boundary"] == proxy.SCIENTIFIC_BOUNDARY
