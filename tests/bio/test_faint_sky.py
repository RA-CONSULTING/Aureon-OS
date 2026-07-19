"""Tests for the UPE-from-the-sky lane — real airglow lines + diffuse background.

The engine's φ logic is unchanged. These tests assert the machinery: the sky's real
faint self-emission (airglow) scans to a valid deterministic result, the featureless
diffuse night-sky background is the honest non-structure anchor (peak-picks to
nothing, non-separable), a planted positive is still detected, and the governance
holds. No assertion is made about what airglow "should" score, and the citation makes
the honest boundary explicit: this is the sky's own faint emission, NOT biological UPE.
"""

from __future__ import annotations

from types import SimpleNamespace

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
# real airglow catalog
# ---------------------------------------------------------------------------


def test_airglow_catalog_registered():
    assert sky.catalog_nm("airglow") == sky.AIRGLOW_NM
    assert len(sky.AIRGLOW_NM) >= 6
    # the honest boundary is explicit in the citation
    assert "not biological upe" in sky.AIRGLOW_CITATION.lower()


def test_airglow_scan_valid_and_deterministic():
    r1 = ssa.score_catalog("airglow", nulls=NULLS, seed=0)
    r2 = ssa.score_catalog("airglow", nulls=NULLS, seed=0)
    assert r1.valid is True and r1.blocked is False
    assert 2 <= r1.n_tones <= len(sky.AIRGLOW_NM)
    assert (r1.test_A_p, r1.test_B_p) == (r2.test_A_p, r2.test_B_p)


def test_airglow_tones_fold_into_band():
    sig = ssa.SkySignalAdapter().extract(
        sky.AIRGLOW_NM, consent=True, provenance="p", kind="lines")
    low, high = proxy.TARGET_BAND_HZ
    assert sig.frequencies_hz
    assert all(low <= f < high for f in sig.frequencies_hz)


# ---------------------------------------------------------------------------
# diffuse background = featureless non-structure anchor
# ---------------------------------------------------------------------------


def test_diffuse_background_is_featureless_anchor():
    r = ssa.score_diffuse(nulls=NULLS)
    assert r.valid is True
    assert r.structure_present is False
    assert r.n_tones == 0  # smooth continuum peak-picks to nothing


def test_planted_positive_still_detected():
    r = ssa.score_sky(sky.structured_spectrum(), consent=True, provenance="ctrl",
                      kind="spectrum", nulls=NULLS)
    assert r.valid is True
    assert r.structure_present is True
    assert r.test_A_p < proxy.engine.ALPHA and r.test_B_p < proxy.engine.ALPHA


# ---------------------------------------------------------------------------
# governance
# ---------------------------------------------------------------------------


def test_consent_gate_blocks_airglow():
    r = ssa.score_catalog("airglow", consent=False, provenance="x", nulls=100)
    assert r.blocked is True and r.valid is False
    assert r.to_dict()["structure_present"] is False


def test_boundary_and_no_claim_words():
    r = ssa.score_catalog("airglow", nulls=NULLS)
    d = r.to_dict()
    assert d["boundary"] == proxy.SCIENTIFIC_BOUNDARY
    for key, value in d.items():
        if key == "boundary" or not isinstance(value, str):
            continue
        low = value.lower()
        for w in _FORBIDDEN:
            assert w not in low, f"field {key!r} leaked {w!r}: {value!r}"
