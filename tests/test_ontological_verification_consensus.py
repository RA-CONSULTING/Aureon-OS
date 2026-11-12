"""Ontological Verification must tell coherent branches from incoherent ones.

Paper: Leckey, "The Harmonic Nexus Core", sero_research.txt (newline count).
A state is real "to the extent that it is replicated and in phase across many
parallel realities" (line 461); only histories with "widespread phase
agreement" survive (line 465); a deviant universe is corrected by the others
(lines 453-454).  Code: MultiversalEngine in aureon/harmonic/aureon_harmonic_reality.py.

Hand working.  Phase agreement across N branches with offsets Δ_k (amplitude
1) is R = |(1/N) Σ e^{iΔ_k}|.  For the engine's default seven branches at
2πk/7 the seventh roots of unity sum to 0, so R = 0: no agreement at all.
Before this change the score was (1/N) Σ (1 + cos Δ_k)/2 = 1/2 + 0 = 0.5 for
those branches, and also 0.5 for seven branches all at Δ = π/2 (cos = 0), so
it could not tell a fully coherent set of branches from a fully incoherent
one.  Claim state HOLD.
"""

from __future__ import annotations

import math

import pytest

from aureon.harmonic.aureon_harmonic_reality import HarmonicRealityField, MultiversalEngine


def _state(engine: MultiversalEngine, primary_phase: float):
    echoes = engine.generate_echoes(primary_signal=1.0, primary_phase=primary_phase, timestamp=0.0)
    return engine.compute_ontological_verification(primary_signal=1.0, echoes=echoes, timestamp=0.0)


def _clustered(phase: float) -> MultiversalEngine:
    eng = MultiversalEngine(n_parallel_universes=7, phase_lock_strength=0.3)
    eng.universe_phases = [phase] * 7
    return eng


@pytest.mark.parametrize("primary_phase", [0.0, 1.0, 2.5])
def test_evenly_spaced_branches_have_no_consensus(primary_phase):
    # Default lattice 2πk/7: R = 0 (see module docstring), so no consensus and
    # not verified, whatever the primary phase.  Main gave exactly 0.5.
    st = _state(MultiversalEngine(n_parallel_universes=7), primary_phase)
    assert st.consensus_score < 1e-12
    assert st.verification_status == "unstable"
    assert not st.is_verified()


def test_coherent_and_incoherent_branches_differ():
    # Coherent: all seven branches at 1.0 + π/2 while the primary is at 1.0,
    # so every Δ = π/2 and R = |e^{iπ/2}| = 1.  Incoherent: default lattice, R = 0.
    # Main scored both 0.5 (cos(π/2) = 0 and Σ cos(2πk/7) = 0).
    coherent = _state(_clustered(1.0 + math.pi / 2), 1.0)
    incoherent = _state(MultiversalEngine(n_parallel_universes=7), 1.0)
    assert abs(coherent.consensus_score - 1.0) < 1e-12
    assert coherent.consensus_score - incoherent.consensus_score > 0.99


def test_deviant_primary_is_not_verified_lines_453_454():
    # Branches agree with each other (R = 1) but sit π/2 from the primary:
    # the primary is the deviant one, so it is contested, not verified.
    # Dominant phase is the circular mean offset, π/2.
    st = _state(_clustered(1.0 + math.pi / 2), 1.0)
    assert abs(st.dominant_phase - math.pi / 2) < 1e-12
    assert st.verification_status == "contested"
    assert not st.is_verified()
    assert st.constructive_echoes == 0 and st.reality_strength() == 0.0


def test_branches_in_phase_with_primary_are_verified_line_461():
    # Every Δ = 0: R = 1, dominant phase 0, all seven constructive.
    # ontological_weight = 1 * 7 / (7 + 1) = 0.875, reality_strength = 0.875.
    st = _state(_clustered(0.4), 0.4)
    assert abs(st.consensus_score - 1.0) < 1e-12
    assert abs(st.dominant_phase) < 1e-12
    assert st.verification_status == "verified" and st.is_verified()
    assert abs(st.reality_strength() - 0.875) < 1e-12


def test_partial_agreement_value():
    # Branches: four at Δ = 0 and three at Δ = π.  Σ e^{iΔ} = 4 - 3 = 1, R = 1/7.
    eng = MultiversalEngine(n_parallel_universes=7)
    eng.universe_phases = [0.0] * 4 + [math.pi] * 3
    st = _state(eng, 0.0)
    assert abs(st.consensus_score - 1.0 / 7.0) < 1e-12
    assert st.verification_status == "unstable"


def test_correction_adds_nothing_for_incoherent_branches_lines_454_455():
    # Unchanged behaviour, kept as a guard: with evenly spaced branches the
    # interference sum is |s| Σ cos Δ_k = 0 (destructive, lines 454-455), so
    # the corrected signal equals the primary.  With all Δ = 0 it is
    # 1 + 0.3 * 1 * 1 = 1.3.
    eng = MultiversalEngine(n_parallel_universes=7, phase_lock_strength=0.3)
    echoes = eng.generate_echoes(primary_signal=1.0, primary_phase=0.0, timestamp=0.0)
    assert abs(eng.apply_phase_correction(1.0, echoes) - 1.0) < 1e-12
    eng2 = _clustered(0.0)
    echoes2 = eng2.generate_echoes(primary_signal=1.0, primary_phase=0.0, timestamp=0.0)
    assert abs(eng2.apply_phase_correction(1.0, echoes2) - 1.3) < 1e-12


def test_default_field_one_second_is_not_verified():
    # The default field's branches are the fixed 2πk/7 lattice plus a slow
    # drift, so after 1 s nothing is verified (rate 0.0) and consensus is near
    # 0, not pinned at 0.5.
    field = HarmonicRealityField()
    for _ in range(int(field.sample_rate)):
        field.step()
    assert field.ontological_verification_rate == 0.0
    last = field.multiverse.ontological_history[-1]
    assert last.consensus_score < 0.1
