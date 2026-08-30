"""Tests for the image signal adapter (colour -> wavelength -> frequency).

Content-agnostic by construction: the adapter reads global colour statistics
only, never faces. All images here are generated in-memory — no real photo. The
Operator hard-boundary runs for real; only the conscience verdict is stubbed.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import image_signal_adapter as isa

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


def _solid(rgb, size=64):
    return np.full((size, size, 3), rgb, dtype=np.uint8)


def _multihue():
    a = np.zeros((120, 120, 3), np.uint8)
    a[:60, :60] = (230, 30, 30)    # red
    a[:60, 60:] = (30, 200, 30)    # green
    a[60:, :60] = (30, 30, 220)    # blue
    a[60:, 60:] = (230, 220, 20)   # yellow
    return a


# ---------------------------------------------------------------------------
# hue -> wavelength -> frequency
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("hue,nm", [(0.0, 700.0), (120.0, 530.0), (240.0, 450.0), (270.0, 400.0)])
def test_hue_to_wavelength_anchors(hue, nm):
    assert isa._hue_to_wavelength_nm(hue) == pytest.approx(nm)


@pytest.mark.parametrize("hue", [271.0, 300.0, 359.0, -1.0])
def test_non_spectral_hue_dropped(hue):
    assert isa._hue_to_wavelength_nm(hue) is None


def test_wavelength_to_hz_in_visible_range():
    for nm in (400.0, 550.0, 700.0):
        hz = isa._wavelength_nm_to_hz(nm)
        assert 4.0e14 <= hz <= 8.0e14


# ---------------------------------------------------------------------------
# extraction: determinism, content-agnostic honesty, folding
# ---------------------------------------------------------------------------


def test_extraction_is_deterministic():
    img = _multihue()
    a = isa.ImageSignalAdapter().extract(img, consent=True, provenance="synthetic")
    b = isa.ImageSignalAdapter().extract(img, consent=True, provenance="synthetic")
    assert a.frequencies_hz == b.frequencies_hz
    assert len(a.frequencies_hz) >= 2


def test_grey_image_yields_no_tones_and_honest_absent():
    sig = isa.ImageSignalAdapter().extract(_solid((128, 128, 128)), consent=True, provenance="grey")
    assert sig.frequencies_hz == ()
    result = proxy.score_signal(sig, nulls=NULLS, seed=0)
    assert result.valid is True
    assert result.structure_present is False
    assert "insufficient tones" in (result.reason or "")


def test_extracted_tones_fold_into_band():
    sig = isa.ImageSignalAdapter().extract(_multihue(), consent=True, provenance="synthetic")
    low, high = proxy.TARGET_BAND_HZ
    for f in sig.frequencies_hz:
        folded = proxy.fold_to_band(f)
        assert folded is not None and low <= folded < high


# ---------------------------------------------------------------------------
# governed scoring through score_image
# ---------------------------------------------------------------------------


def test_score_image_consented_is_valid_with_boundary_and_no_claims():
    result = isa.score_image(_multihue(), consent=True, provenance="synthetic image", nulls=NULLS)
    d = result.to_dict()
    assert d["valid"] is True
    assert d["blocked"] is False
    assert d["n_tones"] >= 2
    assert d["boundary"] == proxy.SCIENTIFIC_BOUNDARY
    for key, value in d.items():
        if key == "boundary" or not isinstance(value, str):
            continue
        low = value.lower()
        for word in _FORBIDDEN_CLAIM_WORDS:
            assert word not in low, f"field {key!r} leaked claim word {word!r}: {value!r}"


def test_score_image_without_consent_is_blocked():
    result = isa.score_image(_multihue(), consent=False, provenance="synthetic image", nulls=NULLS)
    d = result.to_dict()
    assert d["blocked"] is True
    assert d["structure_present"] is False


def test_score_image_missing_provenance_is_blocked():
    result = isa.score_image(_multihue(), consent=True, provenance="   ", nulls=NULLS)
    assert result.blocked is True


def test_adapter_has_no_face_or_person_surface():
    # structural guarantee: the module exposes no face/landmark/detector API
    names = [n.lower() for n in dir(isa)]
    for banned in ("face", "landmark", "detect", "biometric", "recognize", "recognise"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface in adapter"
