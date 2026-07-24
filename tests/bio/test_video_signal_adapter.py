"""Tests for the video signal adapter (per-frame luminance -> governed engine).

Each frame collapses to one global mean-luminance scalar, so the per-frame series is
a time-series: a structured-luminance clip scores present, random luminance scores
absent. Global per-frame luminance only — never face/object/pose analysis, and never
a claim about a person.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import video_signal_adapter as vsa

NULLS = 300
_FORBIDDEN = ("health", "aura", "emotion", "spirit", "entity", "diagnos", "disease", "personality")


class _StubConscience:
    def __init__(self, verdict):
        self._v = verdict

    def ask_why(self, action, context=None):
        return SimpleNamespace(verdict=SimpleNamespace(name=self._v), message="")


@pytest.fixture(autouse=True)
def _approved(monkeypatch):
    monkeypatch.setattr(proxy, "_get_conscience", lambda: _StubConscience("APPROVED"))


# ---------------------------------------------------------------------------
# luminance reduction + dominant-frequency picking
# ---------------------------------------------------------------------------


def test_frames_to_luma_reduces_to_one_scalar_per_frame():
    frames = np.zeros((10, 4, 5, 3), dtype=float)
    frames[3] = 255.0  # one bright frame
    luma = vsa._frames_to_luma(frames)
    assert luma.shape == (10,)
    assert luma[3] > luma[0]


def test_dominant_video_hz_recovers_tones_and_ignores_flat():
    fr = 4000.0
    t = np.arange(4000) / fr
    sig = np.sin(2 * np.pi * 220.0 * t) + 0.9 * np.sin(2 * np.pi * 600.0 * t)
    dom = vsa._dominant_video_hz(sig, frame_rate_hz=fr)
    assert any(abs(f - 220.0) < 2.0 for f in dom)
    assert any(abs(f - 600.0) < 2.0 for f in dom)
    assert vsa._dominant_video_hz(np.ones(4000), frame_rate_hz=fr) == []


def test_extract_folds_into_modulation_band():
    frames, fr = vsa.synthetic_video("structured")
    signal = vsa.VideoSignalAdapter().extract(frames, consent=True, provenance="p", frame_rate_hz=fr)
    low, high = proxy.TARGET_BAND_HZ
    assert signal.frequencies_hz
    assert all(low <= f < high for f in signal.frequencies_hz)
    assert signal.modality == "video"


# ---------------------------------------------------------------------------
# the honest anchor: noise absent, structured present
# ---------------------------------------------------------------------------


def test_noise_video_scores_non_separable():
    r = vsa.score_video(vsa.synthetic_video("noise"), consent=True,
                        provenance="synthetic video", nulls=NULLS)
    assert r.valid is True
    assert r.blocked is False
    assert r.structure_present is False


def test_structured_video_scores_present():
    r = vsa.score_video(vsa.synthetic_video("structured"), consent=True,
                        provenance="synthetic video", nulls=NULLS)
    assert r.valid is True
    assert r.structure_present is True
    assert r.n_tones >= 2
    assert r.test_A_p < proxy.engine.ALPHA and r.test_B_p < proxy.engine.ALPHA


def test_rescan_is_deterministic():
    clip = vsa.synthetic_video("structured")
    r1 = vsa.score_video(clip, consent=True, provenance="det", nulls=200, seed=0)
    r2 = vsa.score_video(clip, consent=True, provenance="det", nulls=200, seed=0)
    assert r1.to_dict() == r2.to_dict()


# ---------------------------------------------------------------------------
# frame-stack round-trip (numpy stack, no decode dependency)
# ---------------------------------------------------------------------------


def test_frame_stack_round_trip_scores_valid():
    frames, fr = vsa.synthetic_video("structured")
    # a genuine (F, H, W, 3) colour stack built from the grayscale luminance
    colour = np.repeat(frames[..., None], 3, axis=-1)
    r = vsa.score_video((colour, fr), consent=True, provenance="frame-stack round-trip", nulls=NULLS)
    assert r.valid is True
    assert r.blocked is False
    assert r.n_tones >= 2


# ---------------------------------------------------------------------------
# governance
# ---------------------------------------------------------------------------


def test_consent_gate_blocks():
    r = vsa.score_video(vsa.synthetic_video("structured"), consent=False,
                        provenance="p", nulls=NULLS)
    assert r.blocked is True and r.valid is False
    assert r.to_dict()["structure_present"] is False


def test_missing_provenance_blocks():
    r = vsa.score_video(vsa.synthetic_video("structured"), consent=True, provenance="  ", nulls=NULLS)
    assert r.blocked is True


def test_boundary_and_no_subject_claims():
    r = vsa.score_video(vsa.synthetic_video("structured"), consent=True, provenance="p", nulls=NULLS)
    d = r.to_dict()
    assert d["boundary"] == proxy.SCIENTIFIC_BOUNDARY
    for key, value in d.items():
        if key == "boundary" or not isinstance(value, str):
            continue
        low = value.lower()
        for wd in _FORBIDDEN:
            assert wd not in low, f"field {key!r} leaked {wd!r}: {value!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(vsa)]
    for banned in ("face", "object", "pose", "emotion", "identity", "recognize", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
