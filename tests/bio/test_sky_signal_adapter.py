"""Tests for the sky signal adapter — scan light from space through the engine.

The engine's φ logic is unchanged. These tests assert the machinery: the control
references behave (featureless continuum doesn't over-fire; planted coherence is
detected), real catalogs scan to a valid deterministic result, and the governance
holds. No assertion is made about what the real sky "should" score.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from aureon.bio import human_harmonic_proxy as proxy
from aureon.bio import sky_reference as sky
from aureon.bio import sky_signal_adapter as ssa

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
# real catalogs
# ---------------------------------------------------------------------------


def test_catalog_lookup():
    assert sky.catalog_nm("balmer") == sky.HYDROGEN_BALMER_NM
    assert sky.catalog_nm("fraunhofer") == sky.SOLAR_FRAUNHOFER_NM
    with pytest.raises(ValueError):
        sky.catalog_nm("nope")


def test_scan_real_catalog_is_valid_and_deterministic():
    r1 = ssa.score_catalog("balmer", nulls=NULLS, seed=0)
    r2 = ssa.score_catalog("balmer", nulls=NULLS, seed=0)
    assert r1.valid is True and r1.blocked is False
    assert r1.n_tones == len(sky.HYDROGEN_BALMER_NM)
    assert (r1.test_A_p, r1.test_B_p) == (r2.test_A_p, r2.test_B_p)  # deterministic


# ---------------------------------------------------------------------------
# control references (negative does not over-fire; positive is detected)
# ---------------------------------------------------------------------------


def test_continuum_negative_control_does_not_overfire():
    r = ssa.score_sky(sky.continuum_spectrum(), consent=True, provenance="ctrl",
                      kind="spectrum", nulls=NULLS)
    assert r.valid is True
    assert r.structure_present is False


def test_planted_structure_positive_control_detected():
    r = ssa.score_sky(sky.structured_spectrum(), consent=True, provenance="ctrl",
                      kind="spectrum", nulls=NULLS)
    assert r.valid is True
    assert r.structure_present is True
    assert r.test_A_p < proxy.engine.ALPHA and r.test_B_p < proxy.engine.ALPHA


# ---------------------------------------------------------------------------
# radio path (21 cm and octaves fold into band)
# ---------------------------------------------------------------------------


def test_radio_frequencies_fold_into_band():
    freqs = [sky.HYDROGEN_21CM_HZ * k for k in (1, 2, 3, 5, 8)]
    sig = ssa.SkySignalAdapter().extract(freqs, consent=True, provenance="radio", kind="radio_hz")
    low, high = proxy.TARGET_BAND_HZ
    assert sig.frequencies_hz
    assert all(low <= f < high for f in sig.frequencies_hz)


# ---------------------------------------------------------------------------
# governance
# ---------------------------------------------------------------------------


def test_consent_gate_blocks():
    r = ssa.score_catalog("fraunhofer", consent=False, provenance="x", nulls=NULLS)
    assert r.blocked is True and r.valid is False
    assert r.to_dict()["structure_present"] is False


def test_missing_provenance_blocks():
    r = ssa.score_sky(sky.HYDROGEN_BALMER_NM, consent=True, provenance="  ", kind="lines", nulls=NULLS)
    assert r.blocked is True


def test_boundary_and_no_claim_words():
    r = ssa.score_catalog("balmer", nulls=NULLS)
    d = r.to_dict()
    assert d["boundary"] == proxy.SCIENTIFIC_BOUNDARY
    for key, value in d.items():
        if key == "boundary" or not isinstance(value, str):
            continue
        low = value.lower()
        for w in _FORBIDDEN:
            assert w not in low, f"field {key!r} leaked {w!r}: {value!r}"


def test_module_has_no_person_reading_surface():
    names = [n.lower() for n in dir(ssa)]
    for banned in ("face", "landmark", "detect", "emotion", "biometric", "recognize"):
        assert not any(banned in n for n in names), f"unexpected {banned!r} surface"


def test_catalog_helper_missing_provenance_blocks():
    # the catalog convenience helper defaults consent=True; blank provenance must block
    r = ssa.score_catalog("balmer", provenance="  ", nulls=100)
    assert r.blocked is True
