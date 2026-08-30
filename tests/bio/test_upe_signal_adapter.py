"""Tests for the UPE signal adapter (real UPE data -> governed engine).

The honest anchor: broadband/featureless UPE scores non-separable; genuine planted
emission lines score present. Real UPE data only (spectrum / photon-count series) —
never a photograph, and never a claim about a subject.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import upe_signal_adapter as usa

NULLS = 300
_FORBIDDEN = ("health", "aura", "emotion", "spirit", "entity", "diagnos", "disease", "personality")


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


# ---------------------------------------------------------------------------
# peak picking
# ---------------------------------------------------------------------------


def test_pick_emission_peaks_finds_lines_and_ignores_flat():
    nm = np.linspace(200, 800, 2000)
    flat = np.ones_like(nm)
    assert usa._pick_emission_peaks(nm, flat) == []
    y = flat + 0.9 * np.exp(-((nm - 400) ** 2) / (2 * 0.5 ** 2)) \
            + 0.9 * np.exp(-((nm - 600) ** 2) / (2 * 0.5 ** 2))
    peaks = usa._pick_emission_peaks(nm, y)
    assert any(abs(p - 400) < 2 for p in peaks)
    assert any(abs(p - 600) < 2 for p in peaks)


# ---------------------------------------------------------------------------
# the honest anchor: broadband absent, structured present
# ---------------------------------------------------------------------------


def test_broadband_upe_scores_non_separable():
    r = usa.score_upe(usa.synthetic_upe("broadband"), consent=True,
                      provenance="synthetic UPE", nulls=NULLS)
    assert r.valid is True
    assert r.blocked is False
    assert r.structure_present is False  # featureless -> no structure


def test_rescan_is_deterministic():
    spec = usa.synthetic_upe("structured")
    r1 = usa.score_upe(spec, consent=True, provenance="det", nulls=200, seed=0)
    r2 = usa.score_upe(spec, consent=True, provenance="det", nulls=200, seed=0)
    assert (r1.test_A_p, r1.test_B_p) == (r2.test_A_p, r2.test_B_p)


def test_structured_upe_scores_present():
    r = usa.score_upe(usa.synthetic_upe("structured"), consent=True,
                      provenance="synthetic UPE", nulls=NULLS)
    assert r.valid is True
    assert r.structure_present is True
    assert r.test_A_p < proxy.engine.ALPHA and r.test_B_p < proxy.engine.ALPHA


# ---------------------------------------------------------------------------
# time-series (photon-count) path
# ---------------------------------------------------------------------------


def test_timeseries_recovers_dominant_frequencies():
    sr = 100.0
    t = np.arange(1024) / sr
    sig = np.sin(2 * np.pi * 5.0 * t) + 0.9 * np.sin(2 * np.pi * 12.0 * t)
    dom = usa._dominant_timeseries_hz(sig, sample_rate_hz=sr)
    assert any(abs(f - 5.0) < 0.5 for f in dom)
    assert any(abs(f - 12.0) < 0.5 for f in dom)
    # folded tones land in the modulation band
    sig_obj = usa.UPESignalAdapter().extract(sig, consent=True, provenance="p",
                                             kind="timeseries", sample_rate_hz=sr)
    low, high = proxy.TARGET_BAND_HZ
    assert sig_obj.frequencies_hz
    assert all(low <= f < high for f in sig_obj.frequencies_hz)


# ---------------------------------------------------------------------------
# governance
# ---------------------------------------------------------------------------


def test_consent_gate_blocks():
    r = usa.score_upe(usa.synthetic_upe("structured"), consent=False,
                      provenance="p", nulls=NULLS)
    assert r.blocked is True and r.valid is False
    assert r.to_dict()["structure_present"] is False


def test_missing_provenance_blocks():
    r = usa.score_upe(usa.synthetic_upe("structured"), consent=True, provenance="  ", nulls=NULLS)
    assert r.blocked is True


def test_boundary_and_no_subject_claims():
    r = usa.score_upe(usa.synthetic_upe("structured"), consent=True, provenance="p", nulls=NULLS)
    d = r.to_dict()
    assert d["boundary"] == proxy.SCIENTIFIC_BOUNDARY
    for key, value in d.items():
        if key == "boundary" or not isinstance(value, str):
            continue
        low = value.lower()
        for w in _FORBIDDEN:
            assert w not in low, f"field {key!r} leaked {w!r}: {value!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(usa)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
