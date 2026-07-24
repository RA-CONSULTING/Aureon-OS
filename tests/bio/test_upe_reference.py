"""Tests for the UPE reference model — the honest broadband anchor.

The load-bearing assertion: a broadband/featureless UPE reference is NOT separable
through the phenolic engine (no discrete harmonic structure). This is the honest
result the science predicts and the anchor for any HNC "UPE render".
"""

from __future__ import annotations

import numpy as np

import phenolic_fingerprint as engine
from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import upe_reference as upe


def test_reference_spectrum_shape_and_band():
    spec = upe.reference_spectrum(61)
    assert len(spec) == 61
    low, high = upe.UPE_BAND_NM
    nms = [nm for nm, _ in spec]
    assert nms[0] == low and nms[-1] == high
    assert all(low <= nm <= high for nm in nms)
    # nearly flat: intensities within a narrow band around the flat base
    intensities = [i for _, i in spec]
    assert min(intensities) >= upe._FLAT_BASE
    assert max(intensities) <= upe._FLAT_BASE + upe._ORANGE_BUMP_AMPLITUDE + 1e-9
    # subtle maximum sits near the orange reference wavelength
    peak_nm = max(spec, key=lambda t: t[1])[0]
    assert abs(peak_nm - upe.UPE_SUBTLE_MAX_NM) <= 20.0


def test_reference_modulation_tones_in_band():
    low, high = proxy.TARGET_BAND_HZ
    tones = upe.reference_modulation_tones(61)
    assert len(tones) == 61
    assert all(low <= t < high for t in tones)
    assert tones == sorted(tones)


def test_broadband_upe_reference_is_non_separable():
    # The honest anchor: featureless UPE -> no clustering, no phi structure.
    tones = np.array(upe.reference_modulation_tones(121))
    p_a = engine.test_A(tones, nulls=300, rng=np.random.default_rng([0, 1]))
    p_b = engine.test_B(tones, nulls=300, rng=np.random.default_rng([0, 2]))
    separable = bool(p_a < engine.ALPHA and p_b < engine.ALPHA)
    assert separable is False
    assert p_a >= engine.ALPHA  # broadband -> not clustered


def test_citation_and_constants_present():
    assert "doi" in upe.UPE_CITATION.lower()
    assert upe.UPE_BAND_NM == (200.0, 800.0)
    assert upe.UPE_FLUX_PHOTONS_CM2_S == (10.0, 1000.0)
