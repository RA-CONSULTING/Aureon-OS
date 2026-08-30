"""Tests for the convergence map (ghost-hunter grid).

Structure-only, content-agnostic, consent-gated. All images generated in-memory.
Convergence = both independent channels (Test A + Test B) agree; single-channel is
noise. Nothing here claims detection of any entity or person.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from aureon.bio import convergence_map as cm
from aureon.bio import human_harmonic_proxy as proxy

NULLS = 120
_FORBIDDEN = ("ghost", "spirit", "entity", "paranormal", "demon", "haunt", "aura")


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


def _multihue(size=180):
    a = np.zeros((size, size, 3), np.uint8)
    h = size // 2
    a[:h, :h] = (230, 30, 30)
    a[:h, h:] = (30, 200, 30)
    a[h:, :h] = (30, 30, 220)
    a[h:, h:] = (230, 220, 20)
    return a


def test_tile_bounds_tile_the_whole_image():
    tiles = cm._tile_bounds(100, 60, 5)
    assert len(tiles) == 25
    assert tiles[0][2:] == (0, 0, 20, 12)
    assert tiles[-1][4] == 100 and tiles[-1][5] == 60  # last tile reaches the edge


def test_analyze_convergence_invariants():
    m = cm.analyze_convergence(_multihue(), consent=True, provenance="synthetic", grid=4, nulls=NULLS)
    assert m.valid is True and m.blocked is False
    assert m.grid == 4 and len(m.cells) == 16
    # convergence is exactly "both independent channels fired"
    for c in m.cells:
        assert c.converged == (c.channels_fired == 2)
        if c.converged:
            assert c.test_A_p < proxy.engine.ALPHA and c.test_B_p < proxy.engine.ALPHA
    assert m.n_converged == sum(1 for c in m.cells if c.converged)


def test_single_channel_is_not_convergence():
    # a cell with exactly one channel firing must never be marked converged
    m = cm.analyze_convergence(_multihue(), consent=True, provenance="p", grid=3, nulls=NULLS)
    assert all(not c.converged for c in m.cells if c.channels_fired == 1)


def test_consent_gate_blocks_map(tmp_path):
    out = tmp_path / "blocked.png"
    m = cm.render_convergence_map(_multihue(), consent=False, provenance="p", out_path=out, grid=3, nulls=NULLS)
    assert m.blocked is True and m.out_path is None
    assert m.n_converged == 0
    assert not out.exists()


def test_render_writes_valid_deterministic_composite(tmp_path):
    from PIL import Image

    o1 = tmp_path / "a.png"
    o2 = tmp_path / "b.png"
    m = cm.render_convergence_map(_multihue(), consent=True, provenance="p", out_path=o1, grid=4, nulls=NULLS)
    cm.render_convergence_map(_multihue(), consent=True, provenance="p", out_path=o2, grid=4, nulls=NULLS)
    assert m.out_path == str(o1)
    assert Image.open(o1).mode == "RGB"
    assert o1.read_bytes() == o2.read_bytes()  # deterministic


def test_boundary_and_no_paranormal_or_person_claims(tmp_path):
    out = tmp_path / "c.png"
    m = cm.render_convergence_map(_multihue(), consent=True, provenance="p", out_path=out, grid=3, nulls=NULLS)
    d = m.to_dict()
    assert d["boundary"] == cm.GHOST_HUNTER_BOUNDARY
    # the boundary NAMES what it is not; no OTHER field may assert those things
    for key, value in d.items():
        if key in ("boundary", "cells") or not isinstance(value, str):
            continue
        low = value.lower()
        for word in _FORBIDDEN:
            assert word not in low, f"field {key!r} leaked {word!r}: {value!r}"


def test_module_has_no_face_or_detect_surface():
    names = [n.lower() for n in dir(cm)]
    for banned in ("face", "landmark", "biometric", "recognize", "recognise"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
