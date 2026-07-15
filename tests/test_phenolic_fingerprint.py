"""Unit tests for the Phenolic Fingerprint analysis engine."""

from __future__ import annotations

import numpy as np
import pytest

import phenolic_fingerprint as pf

# Real chlorogenic + luteolin cm^-1 peaks (from the HNC conversion table).
_REAL_PEAKS = [
    pf.Peak("chlorogenic acid", 1603.0, "cm^-1", None, "doi:cga"),
    pf.Peak("chlorogenic acid", 1632.0, "cm^-1", None, "doi:cga"),
    pf.Peak("chlorogenic acid", 1160.0, "cm^-1", None, "doi:cga"),
    pf.Peak("chlorogenic acid", 1444.0, "cm^-1", None, "doi:cga"),
    pf.Peak("luteolin", 1624.0, "cm^-1", None, "doi:lut"),
    pf.Peak("luteolin", 1607.0, "cm^-1", None, "doi:lut"),
    pf.Peak("luteolin", 1594.0, "cm^-1", None, "doi:lut"),
    pf.Peak("luteolin", 1582.0, "cm^-1", None, "doi:lut"),
    pf.Peak("luteolin", 1567.0, "cm^-1", None, "doi:lut"),
]


def test_peak_to_modulation_hz_matches_conversion_table():
    # 1603 cm^-1 downconverts to ~1398.6 Hz in the packet's target band.
    assert pf.peak_to_modulation_hz(1603.0, "cm^-1") == pytest.approx(1398.635, abs=0.01)
    # nm peaks are supported too (330 nm -> ~1652.5 Hz).
    assert pf.peak_to_modulation_hz(330.0, "nm") == pytest.approx(1652.48, abs=0.1)


def test_unsupported_unit_raises():
    with pytest.raises(ValueError):
        pf.peak_to_modulation_hz(1000.0, "eV")


def test_positive_control_detects():
    result = pf.positive_control(nulls=200, seed=0)
    assert result.passed is True
    assert result.detail["test_A_p"] < pf.ALPHA
    assert result.detail["test_B_p"] < pf.ALPHA


def test_negative_control_does_not_overfire():
    result = pf.negative_control(nulls=100, seed=0)
    assert result.passed is True
    assert result.detail["hit_rate"] <= pf._NEG_CONTROL_MAX_HIT_RATE


def test_run_is_valid_and_deterministic():
    r1 = pf.run(_REAL_PEAKS, nulls=100, seed=0)
    r2 = pf.run(_REAL_PEAKS, nulls=100, seed=0)
    assert r1.valid is True
    assert r1.reason is None
    assert r1.to_dict() == r2.to_dict()
    assert set(r1.compounds) == {"chlorogenic acid", "luteolin"}
    for scores in r1.compounds.values():
        assert 0.0 < scores["test_A_p"] <= 1.0
        assert 0.0 < scores["test_B_p"] <= 1.0
        assert isinstance(scores["separable"], bool)


def test_single_peak_compound_is_not_separable():
    peaks = [pf.Peak("lonely", 1600.0, "cm^-1", None, "doi:x")]
    result = pf.run(peaks, nulls=50, seed=0)
    assert result.valid is True
    assert result.compounds["lonely"]["separable"] is False
    assert result.compounds["lonely"]["n_peaks"] == 1


def test_run_rejects_nonpositive_nulls():
    with pytest.raises(ValueError):
        pf.run(_REAL_PEAKS, nulls=0, seed=0)


def test_test_functions_return_probability():
    freqs = np.array([1000.0, 1005.0, 1010.0, 1618.0])
    rng = np.random.default_rng(1)
    p = pf.test_A(freqs, nulls=100, rng=rng)
    assert 0.0 < p <= 1.0


def test_load_peaks_missing_columns_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("molecule,peak_value\nx,100\n", encoding="utf-8")
    with pytest.raises(ValueError):
        pf.load_peaks(bad)
