"""Tests for the harmonic-core scan — the HNC's own substrate, one unchanged engine.

The engine's φ logic is unchanged. These tests assert the governed scan machinery for
each core system: valid + deterministic, consent gate blocks, the governed boundary
rides on the result, and no person-reading surface exists. No claim is made about what
any lane "should" score. Offline.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.bio import harmonic_core_scan as hc
from aureon.bio import human_harmonic_proxy as proxy

NULLS = 100
_SYSTEMS = ("lambda", "ogham", "ghostdance")


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


@pytest.mark.parametrize("name", _SYSTEMS)
def test_scan_is_valid_and_deterministic(name):
    r1 = hc.score_harmonic_core(name, nulls=NULLS, seed=0)
    r2 = hc.score_harmonic_core(name, nulls=NULLS, seed=0)
    assert r1.valid and r1.n_tones >= 2
    assert (r1.test_A_p, r1.test_B_p) == (r2.test_A_p, r2.test_B_p)


@pytest.mark.parametrize("name", _SYSTEMS)
def test_consent_gate_blocks(name):
    blocked = hc.score_harmonic_core(name, consent=False, provenance="x", nulls=NULLS)
    assert blocked.blocked and not blocked.structure_present


@pytest.mark.parametrize("name", _SYSTEMS)
def test_boundary_rides_on_result(name):
    r = hc.score_harmonic_core(name, nulls=NULLS, seed=0)
    assert r.boundary == proxy.SCIENTIFIC_BOUNDARY


def test_harmonic_core_boundary_is_honest():
    from aureon.bio.harmonic_core_reference import HARMONIC_CORE_BOUNDARY

    low = HARMONIC_CORE_BOUNDARY.lower()
    assert "not a claim" in low and "unchanged" in low
    assert "no efficacy claim" in low
    # the boundary explicitly names the esoteric registers it is NOT claiming
    assert "consciousness" in low and "ancestral spirits" in low


def test_unknown_system_raises():
    with pytest.raises(ValueError):
        hc.score_harmonic_core("nope", nulls=NULLS)


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(hc)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
