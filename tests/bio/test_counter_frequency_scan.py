"""Tests for the counter-frequency scan — the repo's φ/Fibonacci canon, one engine.

The engine's φ logic is unchanged. These tests assert the governed scan machinery:
valid + deterministic, consent gate blocks, the governed boundary rides on the
result, and no person-reading surface exists. Offline.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.bio import counter_frequency_scan as cfs
from aureon.bio import human_harmonic_proxy as proxy

NULLS = 100
_SYSTEMS = ("counter", "fibonacci", "phi")


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
    r1 = cfs.score_counter_frequency(name, nulls=NULLS, seed=0)
    r2 = cfs.score_counter_frequency(name, nulls=NULLS, seed=0)
    assert r1.valid and r1.n_tones >= 2
    assert (r1.test_A_p, r1.test_B_p) == (r2.test_A_p, r2.test_B_p)


@pytest.mark.parametrize("name", _SYSTEMS)
def test_consent_gate_blocks(name):
    blocked = cfs.score_counter_frequency(name, consent=False, provenance="x", nulls=NULLS)
    assert blocked.blocked and not blocked.structure_present


def test_boundary_rides_on_result():
    r = cfs.score_counter_frequency("counter", nulls=NULLS, seed=0)
    assert r.boundary == proxy.SCIENTIFIC_BOUNDARY


def test_unknown_system_raises():
    with pytest.raises(ValueError):
        cfs.score_counter_frequency("nope", nulls=NULLS)


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(cfs)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
