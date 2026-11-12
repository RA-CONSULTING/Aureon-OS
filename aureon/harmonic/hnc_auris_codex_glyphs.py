"""Auris Codex glyphs as described in the HNC paper: Crown, Anchor, Peace, Seal.

Source: G. Leckey, "The Harmonic Nexus Core: A Unified Framework for Emergent
Spacetime and Coherent Information Dynamics" (line numbers refer to the plain
text copy of the paper used to write this module).

Claim state: HOLD.  These are research models of the paper's glyph-to-field
mappings, not measured or validated physics, and they emit no hardware output
(no watts, volts or device commands).  The paper's glyph text (lines 597-605).  Only Peace is stated as defined in
the Auris Codex (line 708); Crown ("might correspond"), Anchor ("could map")
and Seal ("might correspond") are the paper's examples:

* Crown: take the Laplacian ``nabla**2`` of a potential field (lines 597-598).
* Anchor: fix a node in phase, ``Phi = 0`` at that node, a stabilising
  boundary condition (lines 599-600).
* Peace: ``Waveform[8.88 Hz]`` with amplitude decay, a decaying sinusoid at
  8.88 Hz (lines 601-603, 707-710).
* Seal: phase fix with ``d psi / dt = 0``, halting the time evolution of a
  field mode (lines 604-605).

Legacy values.  The repository's JSON codex files list Peace differently:
``public/auris_codex.json`` gives ``intent_mappings.peace.frequencies =
[7.83, 6.0, 4.0]`` and ``public/auris_codex_expanded.json`` gives
``prime_frequencies.peace.hz = 432``.  Existing loaders read those files, so
they are left unchanged and recorded in :data:`LEGACY_PEACE` as legacy values.
The paper's definition is :data:`PEACE_FREQUENCY_HZ` = 8.88.

Pure numpy and math; deterministic; no I/O and no side effects at import.
"""

from __future__ import annotations

import math
from typing import Dict, Sequence

import numpy as np

CLAIM_STATE = "HOLD"

#: Peace glyph frequency, "Waveform[8.88 Hz]" (lines 601-602, 708-709).
PEACE_FREQUENCY_HZ = 8.88

#: Legacy Peace values already in the repo's JSON codex files.  Kept as is
#: because existing loaders read those files; they are not the paper's value.
LEGACY_PEACE: Dict[str, object] = {
    "public/auris_codex.json:intent_mappings.peace.frequencies": (7.83, 6.0, 4.0),
    "public/auris_codex_expanded.json:prime_frequencies.peace.hz": 432,
}

#: The paper's four glyphs: operation and line range.
PAPER_GLYPHS: Dict[str, Dict[str, str]] = {
    "Crown": {"operation": "laplacian of a potential field", "function": "crown_laplacian", "paper_lines": "597-598"},
    "Anchor": {"operation": "Phi = 0 at a node (phase fix)", "function": "anchor_phase", "paper_lines": "599-600"},
    "Peace": {"operation": "8.88 Hz sinusoid with amplitude decay", "function": "peace_waveform", "paper_lines": "601-603, 707-710"},
    "Seal": {"operation": "phase lock, d psi / dt = 0", "function": "seal_phase_lock", "paper_lines": "604-605"},
}

Spacing = float | Sequence[float]


def crown_laplacian(potential, spacing: Spacing = 1.0) -> np.ndarray:
    """Crown: ``nabla**2 potential`` by second-order central differences.

    Returns the Laplacian on interior points, shape ``s - 2`` on every axis.
    ``spacing`` is the grid step, one value or one per axis (the grid is the
    caller's; the paper specifies none).  The stencil is exact for quadratic
    potentials.
    """
    phi = np.asarray(potential, dtype=float)
    if phi.ndim < 1 or min(phi.shape) < 3:
        raise ValueError("potential needs at least 3 points on every axis")
    steps = np.broadcast_to(np.asarray(spacing, dtype=float), (phi.ndim,))
    if np.any(steps <= 0):
        raise ValueError("spacing must be > 0")
    core = tuple(slice(1, -1) for _ in range(phi.ndim))
    out = np.zeros(tuple(n - 2 for n in phi.shape))
    for axis, h in enumerate(steps):
        lo = list(core)
        hi = list(core)
        lo[axis] = slice(0, -2)
        hi[axis] = slice(2, None)
        out += (phi[tuple(hi)] - 2.0 * phi[core] + phi[tuple(lo)]) / (h * h)
    return out


def anchor_phase(phase_field, node) -> np.ndarray:
    """Anchor: return a copy with ``Phi = 0`` at ``node`` (Dirichlet phase fix).

    ``node`` is an index into the field.  Other nodes are untouched.
    """
    out = np.array(phase_field, dtype=float, copy=True)
    out[node] = 0.0
    return out


def peace_waveform(t, amplitude: float, decay_time_s: float, phase_rad: float) -> np.ndarray:
    """Peace: ``A * exp(-t / T) * sin(2 pi 8.88 t + phase)``.

    amplitude:
        Not specified in the paper (the figure is in arbitrary units, line 709).
    decay_time_s:
        e-folding time T in seconds.  Not specified in the paper; the figure
        caption says only that the amplitude decays "over ~1.5 s" (line 709),
        which is not a time constant.  The exponential form follows the
        caption's "exponentially decays".
    phase_rad:
        Starting phase.  Not specified in the paper.
    """
    if decay_time_s <= 0:
        raise ValueError("decay_time_s must be > 0")
    tt = np.asarray(t, dtype=float)
    return amplitude * np.exp(-tt / decay_time_s) * np.sin(2.0 * math.pi * PEACE_FREQUENCY_HZ * tt + phase_rad)


def seal_phase_lock(psi, seal_index: int) -> np.ndarray:
    """Seal: halt the mode's time evolution from ``seal_index`` on.

    ``psi`` is the mode's (real or complex) time series.  The returned series
    equals ``psi`` before ``seal_index`` and is held at ``psi[seal_index]``
    afterwards, so ``d psi / dt = 0`` there (lines 604-605).
    """
    arr = np.array(psi, copy=True)
    if not 0 <= seal_index < arr.shape[0]:
        raise ValueError("seal_index out of range")
    arr[seal_index:] = arr[seal_index]
    return arr


def phase_rate(psi, dt: float) -> np.ndarray:
    """Forward difference ``(psi[n+1] - psi[n]) / dt``, one shorter than psi."""
    if dt <= 0:
        raise ValueError("dt must be > 0")
    return np.diff(np.asarray(psi), axis=0) / dt


def is_phase_locked(psi, dt: float, tolerance: float) -> bool:
    """True when ``|d psi / dt| <= tolerance`` everywhere.  The tolerance is not
    specified in the paper and must be given."""
    rate = phase_rate(psi, dt)
    return bool(rate.size == 0 or np.max(np.abs(rate)) <= tolerance)


__all__ = [
    "CLAIM_STATE",
    "LEGACY_PEACE",
    "PAPER_GLYPHS",
    "PEACE_FREQUENCY_HZ",
    "anchor_phase",
    "crown_laplacian",
    "is_phase_locked",
    "peace_waveform",
    "phase_rate",
    "seal_phase_lock",
]
