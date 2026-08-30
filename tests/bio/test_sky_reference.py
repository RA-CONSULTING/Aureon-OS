"""Tests for sky_reference — real open astronomical line lists + control references.

Pure data module (no governance surface). Asserts the catalogs are well-formed, fold
into the band, the control references behave as constructed, and citations are present.
"""

from __future__ import annotations

import pytest

from aureon.bio import sky_reference as sky
from aureon.bio.human_harmonic_proxy import TARGET_BAND_HZ, fold_to_band
from aureon.bio.image_signal_adapter import _wavelength_nm_to_hz


def test_catalogs_are_wellformed():
    assert sky.catalog_nm("balmer") == sky.HYDROGEN_BALMER_NM
    assert sky.catalog_nm("fraunhofer") == sky.SOLAR_FRAUNHOFER_NM
    assert sky.catalog_nm("airglow") == sky.AIRGLOW_NM
    for cat in (sky.HYDROGEN_BALMER_NM, sky.SOLAR_FRAUNHOFER_NM, sky.AIRGLOW_NM):
        assert len(cat) >= 2
        assert all(200.0 < nm < 1000.0 for nm in cat)  # optical/near-IR nm
    with pytest.raises(ValueError):
        sky.catalog_nm("nope")


def test_catalog_lines_fold_into_band():
    low, high = TARGET_BAND_HZ
    for name in ("balmer", "fraunhofer", "airglow"):
        for nm in sky.catalog_nm(name):
            folded = fold_to_band(_wavelength_nm_to_hz(nm))
            assert folded is not None and low <= folded < high


def test_21cm_line():
    assert pytest.approx(1_420_405_751.768) == sky.HYDROGEN_21CM_HZ
    assert fold_to_band(sky.HYDROGEN_21CM_HZ) is not None


def test_continuum_is_featureless_and_diffuse_delegates():
    cont = sky.continuum_spectrum(101)
    assert len(cont) == 101
    ys = [y for _, y in cont]
    assert ys == sorted(ys) or ys == sorted(ys, reverse=True)  # monotone, no peaks
    assert sky.diffuse_night_sky_spectrum(101) == cont


def test_structured_reference_has_lines():
    spec = sky.structured_spectrum()
    assert len(spec) > 100
    ys = [y for _, y in spec]
    assert max(ys) > min(ys)  # planted lines present


def test_citations_present():
    assert "nm" in sky.SKY_CITATION.lower()
    assert "not biological upe" in sky.AIRGLOW_CITATION.lower()
