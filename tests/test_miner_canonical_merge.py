"""Unit test for the miner brain's canonical-field merge helper (extracted from run_cycle).

`merge_canonical_into_qc` self-sources Λ/Γ/Ψ from the one canonical field into the miner's quantum
context, filling only gaps (an explicit value always wins) and leaving the context untouched when the
field is unavailable. This is the cheap, pure entry point the runtime direction audit (b43) exercises.
"""

from __future__ import annotations

from aureon.core.hnc_field import CanonicalField
from aureon.utils.aureon_miner_brain import merge_canonical_into_qc


def _field(gamma=0.9, lam=1.1, psi=0.7):
    return CanonicalField(available=True, symbolic_life_score=0.6, coherence_gamma=gamma,
                          consciousness_psi=psi, lambda_t=lam, source="test")


def test_gap_fill_from_canonical_field():
    qc: dict = {}
    merge_canonical_into_qc(qc, _field())
    assert qc["planetary_gamma"] == 0.9
    assert qc["piano_lambda"] == 1.1
    assert qc["quantum_coherence"] == 0.7
    assert qc["hnc_field_source"] == "test"


def test_explicitly_injected_value_wins():
    qc = {"planetary_gamma": 0.123}
    merge_canonical_into_qc(qc, _field())
    assert qc["planetary_gamma"] == 0.123  # caller's value is not overwritten
    assert qc["piano_lambda"] == 1.1       # the gap is still filled


def test_unavailable_field_is_a_no_op():
    qc: dict = {}
    merge_canonical_into_qc(qc, CanonicalField(available=False))
    assert qc == {}


def test_returns_the_same_dict():
    qc: dict = {}
    assert merge_canonical_into_qc(qc, _field()) is qc
