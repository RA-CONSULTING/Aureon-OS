"""Tests for the sacred-lattice scan — the repo's own systems, one unchanged engine.

The engine's φ logic is unchanged. These tests assert the governed scan machinery for
each lattice system and the positional Earth-grid map: valid + deterministic, consent
gate blocks (and a blank provenance blocks), the boundary rides on the result, the map
honours the convergence semantics, and no person-reading surface exists. No claim is
made about what any lane "should" score. Offline.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import sacred_lattice_scan as sl

NULLS = 100
_SYSTEMS = ("stargate", "maeshowe", "metatron")
_FORBIDDEN = ("aura", "spirit", "diagnos", "disease", "personality")


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
    r1 = sl.score_lattice(name, nulls=NULLS, seed=0)
    r2 = sl.score_lattice(name, nulls=NULLS, seed=0)
    assert r1.valid and r1.n_tones >= 2
    assert (r1.test_A_p, r1.test_B_p) == (r2.test_A_p, r2.test_B_p)


@pytest.mark.parametrize("name", _SYSTEMS)
def test_consent_gate_blocks(name):
    blocked = sl.score_lattice(name, consent=False, provenance="x", nulls=NULLS)
    assert blocked.blocked and not blocked.structure_present


@pytest.mark.parametrize("name", _SYSTEMS)
def test_boundary_rides_on_result(name):
    r = sl.score_lattice(name, nulls=NULLS, seed=0)
    # the governed scientific boundary rides on every result
    assert r.boundary == proxy.SCIENTIFIC_BOUNDARY


def test_sacred_lattice_boundary_is_honest():
    from aureon.bio.sacred_lattice_reference import SACRED_LATTICE_BOUNDARY

    low = SACRED_LATTICE_BOUNDARY.lower()
    assert "not a claim" in low and "unchanged" in low
    assert "not celestial ra/dec" in low
    for w in _FORBIDDEN:
        assert w not in low


def test_lattice_map_valid_and_converged_semantics():
    m = sl.score_lattice_map(nulls=NULLS, seed=0)
    assert m.valid
    assert m.n_sources >= 2
    for c in m.cells:
        assert c.converged == (c.channels_fired == 2)


def test_lattice_map_consent_gate_blocks():
    m = sl.score_lattice_map(consent=False, provenance="x", nulls=NULLS)
    assert m.blocked and m.n_converged == 0


def test_sources_carry_earth_positions():
    sources = sl.lattice_sky_sources()
    assert len(sources) == 12
    for s in sources:
        assert 0.0 <= s.ra_deg < 360.0   # lon-analog
        assert -90.0 <= s.dec_deg <= 90.0  # lat-analog
        assert len(s.tones_hz) >= 1


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(sl)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
