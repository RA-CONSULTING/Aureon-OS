"""Tests for the φ Celestial Observatory — the consolidated sky/cosmic instrument.

The engine's φ logic is unchanged. These tests assert the orchestration: every lane
produces a reading, the run is deterministic, the consented (NASA/map) lanes honour
consent, the boundary is present and honest, and no person-reading surface exists. No
claim is made about what any lane "should" score. Offline.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.bio import celestial_observatory as obs
from aureon.bio import human_harmonic_proxy as proxy

NULLS = 100
_FORBIDDEN = ("aura", "spirit", "diagnos", "disease", "personality", "efficacy claim")


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


def test_observe_runs_every_lane():
    r = obs.observe(nulls=NULLS, include_map=False)
    assert r.n_lanes >= 11
    assert len(r.readings) == r.n_lanes
    assert r.n_valid >= 1
    lanes = {reading.lane for reading in r.readings}
    for expected in (
        "Hydrogen Balmer", "Airglow", "Schumann modes", "DE440 coherence",
        "Stargate lattice", "Maeshowe solstice", "Metatron geometry",
    ):
        assert expected in lanes


def test_observe_is_deterministic():
    r1 = obs.observe(nulls=NULLS, include_map=False, seed=0)
    r2 = obs.observe(nulls=NULLS, include_map=False, seed=0)
    assert r1.to_dict()["readings"] == r2.to_dict()["readings"]


def test_consented_lane_honours_consent():
    from aureon.bio.sky_map import stellar_sources_from_nasa

    if not stellar_sources_from_nasa():
        pytest.skip("NASA cache absent")
    blocked = obs.observe(consent=False, nulls=NULLS, include_map=False)
    nasa = next(r for r in blocked.readings if r.lane == "NASA stellar Wien")
    assert nasa.valid is False  # consent=False blocks the governed pooled lane


def test_boundary_present_and_honest():
    r = obs.observe(nulls=NULLS, include_map=False)
    assert r.to_dict()["boundary"] == obs.OBSERVATORY_BOUNDARY
    low = obs.OBSERVATORY_BOUNDARY.lower()
    assert "not a claim" in low and "unchanged" in low
    for w in _FORBIDDEN:
        if w == "efficacy claim":
            assert "no efficacy claim" in low  # negated, not asserted
            continue
        assert w not in low


def test_render_writes_picture(tmp_path):
    r = obs.observe(nulls=NULLS, include_map=False)
    out = tmp_path / "obs.png"
    rendered = obs.render_observatory(r, out)
    assert rendered.out_path == str(out)
    assert out.exists() and out.stat().st_size > 0


def test_emit_publishes_to_cognition():
    published = []

    class _StubBus:
        def publish(self, thought):
            published.append(thought)

    r = obs.observe(nulls=NULLS, include_map=False)
    payload = obs.emit_observatory(r, bus=_StubBus(), trace=False)
    assert len(published) == 1
    assert published[0].topic == obs.OBS_RUN_TOPIC
    summary = published[0].payload
    assert summary["n_lanes"] == r.n_lanes
    assert summary["boundary"] == obs.OBSERVATORY_BOUNDARY
    assert isinstance(summary["lanes"], list) and len(summary["lanes"]) == r.n_lanes
    assert payload["n_lanes"] == r.n_lanes  # returns the full report dict


def test_emit_is_best_effort_and_never_raises():
    class _BoomBus:
        def publish(self, thought):
            raise RuntimeError("bus down")

    r = obs.observe(nulls=NULLS, include_map=False)
    # a throwing bus must be swallowed — emission never crashes an observation
    payload = obs.emit_observatory(r, bus=_BoomBus(), trace=False)
    assert payload["n_lanes"] == r.n_lanes


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(obs)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
