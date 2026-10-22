"""Tests for the NOSW activation module."""

from datetime import timezone
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from nosw_activation import (
    CANONICAL_RESONANCE_KEY,
    ActivationState,
    ResonanceMatrix,
    activate_nosw,
)


def test_resonance_key_matches_expected_hash():
    state = activate_nosw()
    assert state.resonance_matrix.resonance_key == CANONICAL_RESONANCE_KEY
    assert len(state.sequence) == 13


def test_activation_state_properties():
    state = activate_nosw()
    assert state.status == "ACTIVE"
    assert isinstance(state, ActivationState)
    assert state.timestamp.tzinfo is timezone.utc
    assert state.resonance_matrix.computed_key
    assert state.resonance_matrix.resonance_key


def test_resonance_matrix_is_deterministic():
    matrix = ResonanceMatrix.from_lines([
        "alpha",
        "beta",
        "gamma",
    ], canonical_key=None)
    second_matrix = ResonanceMatrix.from_lines([
        "alpha",
        "beta",
        "gamma",
    ], canonical_key=None)
    assert matrix.resonance_key == second_matrix.resonance_key
    assert matrix.lines == second_matrix.lines
    assert matrix.computed_key == second_matrix.computed_key
