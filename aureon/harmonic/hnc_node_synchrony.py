"""Node-synchrony coherence and the Anchor phase lock, after Gary Leckey's HNC paper.

CLAIM_STATE is HOLD.  This is a research model of a passage in the paper, not
a measurement of any running system.

Source.  Leckey, "The Harmonic Nexus Core: A Unified Framework for Emergent
Spacetime and Coherent Information Dynamics", plain-text copy
``sero_research.txt``.  Line numbers count newlines only (``sed -n 'Np'``).

What the paper says, and where.
  * Auris has "Binary Response Nodes"; the system's coherence is seen by
    monitoring them.  In a highly coherent state all nodes are synchronised
    and repeat in unison (lines 615-618, 624).  In disturbed conditions some
    nodes "fall out of sync" or "shift phase relative to others" (lines
    624-626).  Stable states give "phase-aligned outputs" (lines 628-630).
    Auris uses "resonance and phase-lock" (line 636).
  * The Anchor glyph "could map to a command to fix a particular node in
    phase (Φ=0 at some node - a stabilizing boundary condition)" (lines
    599-600).  The paper offers this as an example mapping, not a definition.

What the paper does not give.  It gives no formula for node coherence, no
formula for phase locking and no tolerance for Φ=0.  The measures below are
therefore standard modelling choices, not the paper's equations:
  * the Kuramoto order parameter R = |(1/N) Σ_k e^{iθ_k}| (Kuramoto, 1975),
    with mean phase ψ = arg of the same sum.  R = 1 when every node has the
    same phase and R is near 0 when the phases are spread out;
  * the pairwise phase-locking value PLV_jk = |(1/T) Σ_t e^{i(θ_j(t) - θ_k(t))}|
    (Lachaux et al., 1999).  PLV = 1 when two nodes keep a constant phase
    difference over time and is near 0 when that difference wanders;
  * the Anchor check: a node's phase, wrapped to (-π, π], lies within a
    caller-given tolerance of 0.

The tolerance is a required argument with no default because the paper gives
none.  No threshold here calls a state "coherent" or "fractured"; the paper
gives no cut-off, so callers get the numbers only.

The repo's existing "anchor" is a 0.1 weight in the codex JSON, not a phase
constraint.  This module adds a phase-lock check alongside it and does not
rewire that weight or any caller.

This module has no randomness, no I/O and no side effects at import.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np

CLAIM_STATE = "HOLD"

PAPER_SOURCE = "sero_research.txt (Leckey, The Harmonic Nexus Core)"
NODE_COHERENCE_LINES = "615-630"
PHASE_LOCK_LINE = "636"
ANCHOR_LINES = "599-600"
FORMULA_SOURCE = (
    "standard modelling choice: the paper gives no formula for node coherence or phase lock"
)


def _phases_1d(name: str, phases: Sequence[float]) -> np.ndarray:
    arr = np.asarray(phases, dtype=float)
    if arr.ndim != 1 or arr.size == 0:
        raise ValueError(f"{name} must be a non-empty 1-D sequence of phases (radians)")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must be finite")
    return arr


def wrap_phase(phase: float) -> float:
    """Wrap a phase in radians to (-π, π]."""
    p = float(phase)
    if not math.isfinite(p):
        raise ValueError("phase must be finite")
    w = math.atan2(math.sin(p), math.cos(p))
    return math.pi if w == -math.pi else w


@dataclass(frozen=True)
class OrderParameter:
    """Kuramoto order parameter for one snapshot of node phases."""

    R: float
    psi: float
    n_nodes: int
    formula_source: str = FORMULA_SOURCE
    claim_state: str = CLAIM_STATE


def kuramoto_order_parameter(phases: Sequence[float]) -> OrderParameter:
    """R = |mean_k e^{iθ_k}| and ψ = arg of that mean, for N node phases.

    Modelling choice (Kuramoto); the paper (lines 615-630) describes nodes in
    or out of sync but gives no formula.
    """
    arr = _phases_1d("phases", phases)
    z = complex(np.mean(np.exp(1j * arr)))
    return OrderParameter(R=abs(z), psi=cmath.phase(z), n_nodes=int(arr.size))


def phase_locking_value(phases_a: Sequence[float], phases_b: Sequence[float]) -> float:
    """PLV = |mean_t e^{i(θ_a(t) - θ_b(t))}| over two equal-length phase series.

    Modelling choice (Lachaux et al.); the paper names phase lock (line 636)
    without a formula.
    """
    a = _phases_1d("phases_a", phases_a)
    b = _phases_1d("phases_b", phases_b)
    if a.shape != b.shape:
        raise ValueError("phases_a and phases_b must have the same length")
    return float(abs(np.mean(np.exp(1j * (a - b)))))


def phase_locking_matrix(phase_series: Sequence[Sequence[float]]) -> np.ndarray:
    """Pairwise PLV matrix for an (N nodes x T samples) array of phases.

    The diagonal is 1 and the matrix is symmetric.
    """
    arr = np.asarray(phase_series, dtype=float)
    if arr.ndim != 2 or arr.shape[0] == 0 or arr.shape[1] == 0:
        raise ValueError("phase_series must be a non-empty 2-D array (nodes x samples)")
    if not np.all(np.isfinite(arr)):
        raise ValueError("phase_series must be finite")
    z = np.exp(1j * arr)
    plv = np.abs(z @ z.conj().T) / arr.shape[1]
    np.fill_diagonal(plv, 1.0)
    return plv


@dataclass(frozen=True)
class AnchorCheck:
    """Result of the Anchor check Φ = 0 at one node (lines 599-600)."""

    node: int
    phase_wrapped: float
    deviation: float
    tolerance: float
    locked: bool
    paper_lines: str = ANCHOR_LINES
    claim_state: str = CLAIM_STATE


def anchor_phase_lock(phases: Sequence[float], node: int, *, tolerance: float) -> AnchorCheck:
    """Check Φ = 0 at ``node``: |wrap(θ_node)| <= tolerance.

    ``tolerance`` (radians, 0 < tolerance <= π) is required; the paper gives
    no tolerance.
    """
    arr = _phases_1d("phases", phases)
    if isinstance(node, bool) or not isinstance(node, int) or not 0 <= node < arr.size:
        raise ValueError(f"node must be an index in [0, {arr.size - 1}]")
    tol = float(tolerance)
    if not math.isfinite(tol) or not 0.0 < tol <= math.pi:
        raise ValueError("tolerance must be in (0, π] radians")
    w = wrap_phase(float(arr[node]))
    dev = abs(w)
    return AnchorCheck(node=node, phase_wrapped=w, deviation=dev, tolerance=tol, locked=dev <= tol)


def anchor_held_over_time(
    phase_series: Sequence[float], *, tolerance: float
) -> Tuple[bool, float]:
    """For one node's phase over time, return (every sample within tolerance of 0, worst deviation).

    ``tolerance`` (radians, 0 < tolerance <= π) is required and is validated
    before any phase is read or wrapped, as in ``anchor_phase_lock``.
    """
    tol = float(tolerance)
    if not math.isfinite(tol) or not 0.0 < tol <= math.pi:
        raise ValueError("tolerance must be in (0, π] radians")
    arr = _phases_1d("phase_series", phase_series)
    worst = max(abs(wrap_phase(float(p))) for p in arr)
    return worst <= tol, worst


__all__ = [
    "ANCHOR_LINES",
    "AnchorCheck",
    "CLAIM_STATE",
    "FORMULA_SOURCE",
    "NODE_COHERENCE_LINES",
    "OrderParameter",
    "PAPER_SOURCE",
    "PHASE_LOCK_LINE",
    "anchor_held_over_time",
    "anchor_phase_lock",
    "kuramoto_order_parameter",
    "phase_locking_matrix",
    "phase_locking_value",
    "wrap_phase",
]
