"""Tests for the QGITA ⇄ phenolic-φ calibration.

The engine's φ logic is unchanged. These tests assert the calibration machinery:
QGITA and the engine share the same φ constant, the engine's φ-alignment arm detects
QGITA's golden lattice, the calibrate-by-validation protocol reports CALIBRATED with a
bounded false-positive rate, and the governed Auris scan holds its boundary. No engine
threshold is tuned.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

import phenolic_fingerprint as engine
from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import qgita_calibration as qc

NULLS = 300


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


# ---------------------------------------------------------------------------
# reuse of the real QGITA systems + shared φ
# ---------------------------------------------------------------------------


def test_phi_shared_with_engine():
    assert qc.qgita_phi() == float(engine.PHI) == pytest.approx(1.618033988749895)


def test_fibonacci_lattice_reused():
    fibs = qc.fibonacci_lattice_numbers(12)
    assert fibs[:6] == (1, 1, 2, 3, 5, 8)  # QGITA FibonacciTimeLattice knots


def test_auris_frequencies_reused():
    freqs = qc.auris_frequencies_hz()
    assert len(freqs) == 9
    assert 432.0 in freqs and 528.0 in freqs  # QGITA Auris config


def test_phi_lattice_ratios_are_phi_powers():
    lattice = qc.phi_lattice_tones(1000.0, 5)
    ratios = lattice[1:] / lattice[:-1]
    assert np.allclose(ratios, qc.qgita_phi())


# ---------------------------------------------------------------------------
# the engine detects QGITA's golden lattice (φ-alignment arm)
# ---------------------------------------------------------------------------


def test_engine_detects_golden_lattice():
    lattice = qc.phi_lattice_tones(1000.0, 5)
    p = engine.test_B(lattice, nulls=NULLS, rng=np.random.default_rng([0, 2]))
    assert p < engine.ALPHA


# ---------------------------------------------------------------------------
# calibrate-by-validation protocol
# ---------------------------------------------------------------------------


def test_calibration_passes_and_is_deterministic():
    r1 = qc.calibrate_qgita(nulls=NULLS, seed=0, fpr_trials=100)
    r2 = qc.calibrate_qgita(nulls=NULLS, seed=0, fpr_trials=100)
    assert r1.calibrated is True
    assert r1.phi_shared_with_engine is True
    assert r1.phi_lattice_detected is True
    assert r1.controls_valid is True
    assert r1.to_dict() == r2.to_dict()  # deterministic


def test_false_positive_rate_bounded():
    r = qc.calibrate_qgita(nulls=NULLS, seed=1, fpr_trials=200)
    se = (engine.ALPHA * (1 - engine.ALPHA) / 200) ** 0.5
    assert r.empirical_fpr_separable <= engine.ALPHA + 3 * se


def test_engine_thresholds_unchanged():
    # calibration must not mutate any pre-registered engine constant
    before = (engine.ALPHA, engine.TARGET_BAND_HZ, float(engine.PHI))
    qc.calibrate_qgita(nulls=100, seed=0, fpr_trials=20)
    assert (engine.ALPHA, engine.TARGET_BAND_HZ, float(engine.PHI)) == before


# ---------------------------------------------------------------------------
# governed Auris scan (neutral, bounded)
# ---------------------------------------------------------------------------


def test_qgita_structured_reference_is_separable():
    tones = qc.qgita_structured_tones()
    pa = engine.test_A(tones, nulls=NULLS, rng=np.random.default_rng([0, 1]))
    pb = engine.test_B(tones, nulls=NULLS, rng=np.random.default_rng([0, 2]))
    assert pa < engine.ALPHA and pb < engine.ALPHA


def test_auris_scan_valid_and_folds_into_band():
    r = qc.score_qgita_auris(nulls=NULLS)
    assert r.valid is True and r.blocked is False
    assert r.n_tones == 9
    d = r.to_dict()
    assert d["boundary"] == proxy.SCIENTIFIC_BOUNDARY


def test_auris_consent_gate_blocks():
    r = qc.score_qgita_auris(consent=False, provenance="x", nulls=100)
    assert r.blocked is True and r.valid is False
    assert r.to_dict()["structure_present"] is False


def test_module_has_no_person_reading_surface():
    # Auris/QGITA framing is human-adjacent; guard the module surface explicitly.
    names = [n.lower() for n in dir(qc)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize", "aura"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
