"""Tests for the coherence scan — the repo's DE440 coherence spectrum through the engine.

The engine's φ logic is unchanged. These tests assert the machinery: the coherence
peaks fold into the band, the real + sim scans are valid and deterministic, the
governance holds, and no person-reading surface exists. No claim is made about what
the coherence spectrum "should" score. Offline.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.bio import coherence_scan as cohs
from aureon.bio import human_harmonic_proxy as proxy

NULLS = 200
_REAL = "data/de440_gate3_coherence.csv"
_SIM = "data/sim_gate3_coherence.csv"

pytestmark = pytest.mark.skipif(
    not __import__("pathlib").Path(_REAL).exists(), reason="coherence data absent"
)


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


def test_load_coherence():
    freqs, coh = cohs.load_coherence(_REAL)
    assert freqs.size == coh.size and freqs.size > 0


def test_peak_tones_fold_into_band():
    tones = cohs.coherence_peak_tones(_REAL, top_k=32)
    low, high = proxy.TARGET_BAND_HZ
    assert len(tones) >= 2
    assert tones == tuple(sorted(set(tones)))  # sorted + deduped
    assert all(low <= t < high for t in tones)


def test_real_scan_valid_and_deterministic():
    r1 = cohs.score_coherence(_REAL, nulls=NULLS, seed=0)
    r2 = cohs.score_coherence(_REAL, nulls=NULLS, seed=0)
    assert r1.valid is True and r1.blocked is False
    assert r1.n_tones >= 2
    assert (r1.test_A_p, r1.test_B_p) == (r2.test_A_p, r2.test_B_p)


def test_sim_control_scans_valid():
    r = cohs.score_coherence(_SIM, nulls=NULLS)
    assert r.valid is True and r.blocked is False


def test_consent_gate_blocks():
    r = cohs.score_coherence(_REAL, consent=False, provenance="x", nulls=100)
    assert r.blocked is True and r.valid is False
    assert r.to_dict()["structure_present"] is False


def test_missing_provenance_blocks():
    r = cohs.score_coherence(_REAL, consent=True, provenance="  ", nulls=100)
    assert r.blocked is True


def test_boundary_present():
    r = cohs.score_coherence(_REAL, nulls=NULLS)
    assert r.to_dict()["boundary"] == proxy.SCIENTIFIC_BOUNDARY


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(cohs)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
