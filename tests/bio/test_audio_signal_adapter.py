"""Tests for the audio signal adapter (waveform -> governed engine).

An audio clip is a time-series, so a real FFT recovers its dominant frequencies:
a structured tone clip scores present, broadband noise scores absent. Global clip
statistics only — never speech/speaker/emotion analysis, and never a claim about a
person.
"""

from __future__ import annotations

import wave
from types import SimpleNamespace

import numpy as np
import pytest

from aureon.bio import audio_signal_adapter as asa
from aureon.bio import human_harmonic_proxy as proxy

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
# dominant-frequency picking
# ---------------------------------------------------------------------------


def test_dominant_audio_hz_recovers_tones_and_ignores_flat():
    sr = 8000.0
    t = np.arange(8000) / sr
    sig = np.sin(2 * np.pi * 440.0 * t) + 0.9 * np.sin(2 * np.pi * 1200.0 * t)
    dom = asa._dominant_audio_hz(sig, sample_rate_hz=sr)
    assert any(abs(f - 440.0) < 2.0 for f in dom)
    assert any(abs(f - 1200.0) < 2.0 for f in dom)
    # a DC / silent clip has no dominant tone
    assert asa._dominant_audio_hz(np.zeros(8000), sample_rate_hz=sr) == []


def test_extract_folds_into_modulation_band():
    sig, sr = asa.synthetic_audio("structured")
    signal = asa.AudioSignalAdapter().extract(sig, consent=True, provenance="p", sample_rate_hz=sr)
    low, high = proxy.TARGET_BAND_HZ
    assert signal.frequencies_hz
    assert all(low <= f < high for f in signal.frequencies_hz)
    assert signal.modality == "audio"


# ---------------------------------------------------------------------------
# the honest anchor: noise absent, structured present
# ---------------------------------------------------------------------------


def test_noise_audio_scores_non_separable():
    r = asa.score_audio(asa.synthetic_audio("noise"), consent=True,
                        provenance="synthetic audio", nulls=NULLS)
    assert r.valid is True
    assert r.blocked is False
    assert r.structure_present is False


def test_structured_audio_scores_present():
    r = asa.score_audio(asa.synthetic_audio("structured"), consent=True,
                        provenance="synthetic audio", nulls=NULLS)
    assert r.valid is True
    assert r.structure_present is True
    assert r.n_tones >= 2
    assert r.test_A_p < proxy.engine.ALPHA and r.test_B_p < proxy.engine.ALPHA


def test_rescan_is_deterministic():
    clip = asa.synthetic_audio("structured")
    r1 = asa.score_audio(clip, consent=True, provenance="det", nulls=200, seed=0)
    r2 = asa.score_audio(clip, consent=True, provenance="det", nulls=200, seed=0)
    assert r1.to_dict() == r2.to_dict()


# ---------------------------------------------------------------------------
# WAV round-trip (stdlib wave, no new dependency)
# ---------------------------------------------------------------------------


def test_wav_round_trip_scores_valid(tmp_path):
    sig, sr = asa.synthetic_audio("structured")
    pcm = np.clip(sig / np.max(np.abs(sig)) * 32767.0, -32768, 32767).astype("<i2")
    path = tmp_path / "clip.wav"
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(int(sr))
        wav.writeframes(pcm.tobytes())
    r = asa.score_audio(str(path), consent=True, provenance="wav round-trip", nulls=NULLS)
    assert r.valid is True
    assert r.blocked is False
    assert r.n_tones >= 2


# ---------------------------------------------------------------------------
# governance
# ---------------------------------------------------------------------------


def test_consent_gate_blocks():
    r = asa.score_audio(asa.synthetic_audio("structured"), consent=False,
                        provenance="p", nulls=NULLS)
    assert r.blocked is True and r.valid is False
    assert r.to_dict()["structure_present"] is False


def test_missing_provenance_blocks():
    r = asa.score_audio(asa.synthetic_audio("structured"), consent=True, provenance="  ", nulls=NULLS)
    assert r.blocked is True


def test_boundary_and_no_subject_claims():
    r = asa.score_audio(asa.synthetic_audio("structured"), consent=True, provenance="p", nulls=NULLS)
    d = r.to_dict()
    assert d["boundary"] == proxy.SCIENTIFIC_BOUNDARY
    for key, value in d.items():
        if key == "boundary" or not isinstance(value, str):
            continue
        low = value.lower()
        for w in _FORBIDDEN:
            assert w not in low, f"field {key!r} leaked {w!r}: {value!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(asa)]
    for banned in ("face", "speaker", "voice", "emotion", "identity", "recognize", "biometric"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"
