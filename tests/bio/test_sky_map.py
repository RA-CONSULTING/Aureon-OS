"""Tests for the sky map — the harmonic sensors, mapped across the sky by RA/Dec.

The engine's φ logic is unchanged. These tests assert the map machinery: the grid
tiles the whole sphere, real sources bin and score to a valid deterministic map, the
two-channel "converged" semantics hold, the governance gate blocks + empties the map,
and no person-reading surface exists. No claim is made about what the sky "should"
score. Offline — reads committed data; skips if the position cache is absent.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import sky_map as sm

NULLS = 150
_FORBIDDEN = ("health", "aura", "emotion", "spirit", "entity", "ghost", "paranormal", "personality")

_HAS_POSITIONS = bool(sm.stellar_sources_from_nasa()) or bool(sm.planet_track_sources_from_de440())
pytestmark = pytest.mark.skipif(not _HAS_POSITIONS, reason="no positioned sky data (offline)")


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


def _sources():
    return sm.stellar_sources_from_nasa() + sm.planet_track_sources_from_de440()


# ---------------------------------------------------------------------------
# grid geometry
# ---------------------------------------------------------------------------


def test_sky_bounds_tile_the_whole_sphere():
    bounds = list(sm._sky_bounds(12, 6))
    assert len(bounds) == 72
    ra_lo_min = min(b[2] for b in bounds)
    ra_hi_max = max(b[3] for b in bounds)
    dec_lo_min = min(b[4] for b in bounds)
    dec_hi_max = max(b[5] for b in bounds)
    assert (ra_lo_min, ra_hi_max) == (0.0, 360.0)
    assert (dec_lo_min, dec_hi_max) == (-90.0, 90.0)


def test_cell_index_maps_positions():
    assert sm._cell_index(0.0, -90.0, 12, 6) == (0, 0)
    assert sm._cell_index(359.9, 89.9, 12, 6) == (5, 11)
    # RA wraps
    assert sm._cell_index(360.0, 0.0, 12, 6) == sm._cell_index(0.0, 0.0, 12, 6)


# ---------------------------------------------------------------------------
# real-data lanes
# ---------------------------------------------------------------------------


def test_source_builders_return_positioned_folded_tones():
    low, high = proxy.TARGET_BAND_HZ
    for s in _sources()[:50]:
        assert 0.0 <= s.ra_deg < 360.0 or s.ra_deg == 360.0
        assert -90.0 <= s.dec_deg <= 90.0
        assert s.tones_hz
        assert all(low <= t < high for t in s.tones_hz)


def test_analyze_map_valid_and_deterministic():
    src = _sources()
    m1 = sm.analyze_sky_map(src, consent=True, provenance="test", nulls=NULLS)
    m2 = sm.analyze_sky_map(src, consent=True, provenance="test", nulls=NULLS)
    assert m1.valid is True and m1.blocked is False and m1.controls_pass is True
    assert len(m1.cells) == m1.ra_bins * m1.dec_bins
    assert m1.to_dict() == m2.to_dict()
    assert any(c.n_tones >= 2 for c in m1.cells)


def test_converged_semantics():
    m = sm.analyze_sky_map(_sources(), consent=True, provenance="test", nulls=NULLS)
    for c in m.cells:
        assert c.converged == (c.channels_fired == 2)
        if c.converged:
            assert c.test_A_p < proxy.engine.ALPHA and c.test_B_p < proxy.engine.ALPHA
    assert m.n_converged == sum(1 for c in m.cells if c.converged)


def test_single_channel_is_not_convergence():
    m = sm.analyze_sky_map(_sources(), consent=True, provenance="test", nulls=NULLS)
    assert all(not c.converged for c in m.cells if c.channels_fired == 1)


# ---------------------------------------------------------------------------
# governance + render
# ---------------------------------------------------------------------------


def test_consent_gate_blocks_and_empties(tmp_path):
    m = sm.render_sky_map(_sources(), consent=False, provenance="x",
                          out_path=tmp_path / "blocked.png", nulls=100)
    assert m.blocked is True
    assert m.cells == []
    assert m.n_converged == 0
    assert m.out_path is None
    assert not (tmp_path / "blocked.png").exists()


def test_render_writes_deterministic_png(tmp_path):
    src = _sources()
    o1, o2 = tmp_path / "a.png", tmp_path / "b.png"
    m1 = sm.render_sky_map(src, consent=True, provenance="test", out_path=o1, nulls=NULLS)
    sm.render_sky_map(src, consent=True, provenance="test", out_path=o2, nulls=NULLS)
    assert m1.out_path == str(o1)
    assert o1.read_bytes() == o2.read_bytes()  # deterministic


def test_boundary_and_no_forbidden_words():
    m = sm.analyze_sky_map(_sources(), consent=True, provenance="test", nulls=NULLS)
    d = m.to_dict()
    assert d["boundary"] == sm.SKY_MAP_BOUNDARY
    low = sm.SKY_MAP_BOUNDARY.lower()
    assert "not a claim" in low
    for w in _FORBIDDEN:
        assert w not in low, f"boundary leaked {w!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(sm)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
