"""Tests for the image harmonic overlay (photon -> geometry -> composite).

Content-agnostic; all images generated in-memory (no real photo). Operator
hard-boundary runs for real; only the conscience verdict is stubbed.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import image_harmonic_overlay as ov

NULLS = 200

_FORBIDDEN_CLAIM_WORDS = (
    "diagnos", "disease", "healthy", "illness", "personality", "trait",
    "chakra", "psychic", "cure", "efficacy",
)


class _StubConscience:
    def __init__(self, verdict_name: str) -> None:
        self._verdict = verdict_name

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._verdict), message="")


@pytest.fixture(autouse=True)
def _approved_conscience(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


def _multihue():
    a = np.zeros((120, 120, 3), np.uint8)
    a[:60, :60] = (230, 30, 30)
    a[:60, 60:] = (30, 200, 30)
    a[60:, :60] = (30, 30, 220)
    a[60:, 60:] = (230, 220, 20)
    return a


def _folded_from(img):
    from aureon.bio.image_signal_adapter import ImageSignalAdapter

    sig = ImageSignalAdapter().extract(img, consent=True, provenance="p")
    return [f for f in (proxy.fold_to_band(x) for x in sig.frequencies_hz) if f is not None]


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------


def test_build_pattern_deterministic_and_transparent_canvas():
    folded = _folded_from(_multihue())
    a = ov.build_geometric_pattern(folded, size=(160, 160))
    b = ov.build_geometric_pattern(folded, size=(160, 160))
    assert a.size == (160, 160)
    assert a.mode == "RGBA"
    assert a.tobytes() == b.tobytes()  # deterministic


def test_pattern_ray_count_matches_tone_count():
    # An empty tone list draws only the scaffold; a populated one draws tone points.
    empty = ov.build_geometric_pattern([], size=(120, 120))
    populated = ov.build_geometric_pattern(_folded_from(_multihue()), size=(120, 120))
    # more non-transparent pixels once tones/rays are drawn
    assert np.asarray(populated)[..., 3].sum() > np.asarray(empty)[..., 3].sum()


# ---------------------------------------------------------------------------
# render_overlay pipeline
# ---------------------------------------------------------------------------


def test_render_consented_writes_valid_composite(tmp_path):
    from PIL import Image

    out = tmp_path / "composite.png"
    result = ov.render_overlay(
        _multihue(), consent=True, provenance="synthetic image", out_path=out, nulls=NULLS
    )
    assert result.out_path == str(out)
    assert result.valid is True and result.blocked is False
    assert result.n_tones >= 2
    img = Image.open(out)
    assert img.size == (120, 120)  # matches source (downscale >= source)


def test_render_is_byte_deterministic(tmp_path):
    o1 = tmp_path / "a.png"
    o2 = tmp_path / "b.png"
    ov.render_overlay(_multihue(), consent=True, provenance="p", out_path=o1, nulls=NULLS)
    ov.render_overlay(_multihue(), consent=True, provenance="p", out_path=o2, nulls=NULLS)
    assert o1.read_bytes() == o2.read_bytes()


def test_blocked_run_renders_no_pattern(tmp_path):
    out = tmp_path / "blocked.png"
    result = ov.render_overlay(
        _multihue(), consent=False, provenance="p", out_path=out, nulls=NULLS
    )
    assert result.out_path is None
    assert result.blocked is True
    assert result.structure_present is False
    assert not out.exists()  # no harmonic file written


def test_boundary_and_no_person_claims(tmp_path):
    out = tmp_path / "c.png"
    result = ov.render_overlay(_multihue(), consent=True, provenance="p", out_path=out, nulls=NULLS)
    d = result.to_dict()
    assert d["boundary"] == proxy.SCIENTIFIC_BOUNDARY
    for key, value in d.items():
        if key == "boundary" or not isinstance(value, str):
            continue
        low = value.lower()
        for word in _FORBIDDEN_CLAIM_WORDS:
            assert word not in low, f"field {key!r} leaked claim word {word!r}: {value!r}"


def test_module_has_no_face_or_person_surface():
    names = [n.lower() for n in dir(ov)]
    for banned in ("face", "landmark", "detect", "biometric", "recognize", "recognise"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_upe_reference_mode_renders_valid_composite(tmp_path):
    from PIL import Image

    out = tmp_path / "upe.png"
    result = ov.render_overlay(
        _multihue(), consent=True, provenance="synthetic image",
        out_path=out, nulls=NULLS, upe_reference=True,
    )
    assert result.out_path == str(out)
    assert result.valid is True and result.blocked is False
    assert Image.open(out).size == (120, 120)
    # UPE mode must not claim a measurement; boundary still on the result dict
    assert result.to_dict()["boundary"] == proxy.SCIENTIFIC_BOUNDARY
