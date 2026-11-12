"""EPAS layers and the Lorentz force F = q v x B, as Gary Leckey's HNC paper describes them.

CLAIM_STATE is HOLD.  This is a research model of a passage in the paper, not
a measurement, not a design and not a working system.

Source.  Leckey, "The Harmonic Nexus Core: A Unified Framework for Emergent
Spacetime and Coherent Information Dynamics", plain-text copy
``sero_research.txt``.  Line numbers count newlines only (``sed -n 'Np'``).

What the paper fixes, and where.
  * EPAS is described as three coordinated layers around a vehicle (lines
    502-506).
  * Electromagnetic layer (lines 509-515): a magnetic field acts on charged
    particles through the Lorentz force, written in the paper as
    F = q v x B (lines 510-511).  This is the only formula the EPAS passage
    gives.
  * Plasma ablation layer (lines 518-524): a plasma just outside the hull,
    "sustained and shaped by the EM layer's magnetic field" (lines 523-524).
    The paper writes no separate formula for this layer.  Applying
    F = q v x B to a charged particle of that plasma, in the EM layer's
    field, is this module's reading of lines 523-524, not an equation the
    paper writes for the layer.  Neutral particles (lines 519-520) carry
    q = 0, so the formula gives them zero magnetic force; the paper's
    collisional drag and ablation heating for them (lines 520-522) are not
    modelled here.
  * Acoustic (resonant) layer (lines 527-534): acoustic pulses in the plasma
    medium.  The paper gives no magnetic force for this layer, so this module
    refuses to compute one for it.
  * Operating point (lines 563-566): the paper says that by tuning power and
    frequency EPAS "theoretically reaches a harmonic operating point", but it
    gives no numbers for it.  ``OPERATING_POINT_FROM_PAPER`` is therefore
    ``None`` and nothing here computes one.

Required arguments.  The paper gives no charge, no velocity and no field
strength.  ``q``, ``v`` and ``B`` are therefore required arguments of every
function that uses them, with no defaults.  Units are SI (coulomb, m/s,
tesla, newton); the formula itself is unit-agnostic.

Cited constants from Gary's EPAS whitepapers in this repository
(``aureon_fusion/knowledge/whitepapers/``):
  * seed 528 Hz and f_counter = 528/phi = 326.3 Hz
    (EPAS_Unified_Architecture_v2.md:349);
  * the 326-854 Hz band.  Both whitepapers state it inside a "Hypothesis" for
    a bench test that has not been run (EPAS_Unified_Architecture_v2.md:349,
    HNC_Project_Druid_EPAS_Technical_Framework.md:237).  It is recorded here
    only as the paper's stated hypothesis.  It is not a measurement and no
    function here uses it.

This module has no randomness, no I/O and no side effects at import.  It
produces no device, hardware or field output: it only evaluates the cross
product for numbers the caller supplies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np

CLAIM_STATE = "HOLD"

PAPER_SOURCE = "sero_research.txt (Leckey, The Harmonic Nexus Core)"

#: Golden ratio, used only to restate f_counter = 528/phi.
PHI = (1.0 + math.sqrt(5.0)) / 2.0

#: Seed frequency, EPAS_Unified_Architecture_v2.md:349.
SEED_HZ = 528.0

#: f_counter = 528/phi, EPAS_Unified_Architecture_v2.md:349 ("326.3 Hz").
F_COUNTER_HZ = SEED_HZ / PHI

#: The 326-854 Hz band, exactly as the whitepapers state it
#: (EPAS_Unified_Architecture_v2.md:349,
#: HNC_Project_Druid_EPAS_Technical_Framework.md:237).
HYPOTHESIS_BAND_HZ: Tuple[float, float] = (326.0, 854.0)
HYPOTHESIS_BAND_LABEL = "the paper's stated hypothesis"
HYPOTHESIS_BAND_SOURCES: Tuple[str, ...] = (
    "aureon_fusion/knowledge/whitepapers/EPAS_Unified_Architecture_v2.md:349",
    "aureon_fusion/knowledge/whitepapers/HNC_Project_Druid_EPAS_Technical_Framework.md:237",
)

#: The paper names an operating point (lines 563-566) but gives no numbers.
OPERATING_POINT_FROM_PAPER: dict | None = None
OPERATING_POINT_LINES = "563-566"


@dataclass(frozen=True)
class EpasLayer:
    """One EPAS layer as the paper describes it."""

    key: str
    name: str
    paper_lines: str
    lorentz_applies: bool
    note: str


EPAS_LAYERS: Tuple[EpasLayer, ...] = (
    EpasLayer(
        key="electromagnetic",
        name="Electromagnetic Layer",
        paper_lines="509-515",
        lorentz_applies=True,
        note="F = q v x B is written in the paper at lines 510-511.",
    ),
    EpasLayer(
        key="plasma_ablation",
        name="Plasma Ablation Layer",
        paper_lines="518-524",
        lorentz_applies=True,
        note=(
            "The plasma is held by the EM layer's magnetic field (lines 523-524); "
            "applying q v x B to its charged particles is this module's reading, "
            "not a formula the paper writes for this layer."
        ),
    ),
    EpasLayer(
        key="acoustic",
        name="Acoustic (Resonant) Layer",
        paper_lines="527-534",
        lorentz_applies=False,
        note="The paper gives no magnetic force for this layer.",
    ),
)

_LAYERS_BY_KEY = {layer.key: layer for layer in EPAS_LAYERS}


@dataclass(frozen=True)
class LayerLorentzForce:
    """Result of F = q v x B evaluated for one layer."""

    layer: str
    paper_lines: str
    force: Tuple[float, float, float]
    magnitude: float
    claim_state: str = CLAIM_STATE


def _vector3(name: str, value: Sequence[float]) -> np.ndarray:
    arr = np.asarray(value, dtype=float)
    if arr.shape != (3,):
        raise ValueError(f"{name} must be a 3-vector, got shape {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must be finite")
    return arr


def lorentz_force(q: float, v: Sequence[float], B: Sequence[float]) -> Tuple[float, float, float]:
    """Return F = q v x B (paper lines 510-511).

    All three arguments are required; the paper gives no value for any of
    them.  ``q`` is a scalar charge, ``v`` and ``B`` are 3-vectors.
    """
    qf = float(q)
    if not math.isfinite(qf):
        raise ValueError("q must be finite")
    force = qf * np.cross(_vector3("v", v), _vector3("B", B))
    return (float(force[0]), float(force[1]), float(force[2]))


def epas_layer(key: str) -> EpasLayer:
    """Look up an EPAS layer by key."""
    try:
        return _LAYERS_BY_KEY[key]
    except KeyError:
        raise ValueError(f"unknown EPAS layer {key!r}; known: {sorted(_LAYERS_BY_KEY)}") from None


def layer_lorentz_force(
    layer: str, *, q: float, v: Sequence[float], B: Sequence[float]
) -> LayerLorentzForce:
    """Evaluate F = q v x B for a charged particle in one EPAS layer.

    Refuses the acoustic layer, for which the paper gives no magnetic force
    (lines 527-534).
    """
    spec = epas_layer(layer)
    if not spec.lorentz_applies:
        raise ValueError(
            f"the paper gives no Lorentz force for the {spec.name} (lines {spec.paper_lines})"
        )
    force = lorentz_force(q, v, B)
    return LayerLorentzForce(
        layer=spec.key,
        paper_lines=spec.paper_lines,
        force=force,
        magnitude=math.sqrt(sum(c * c for c in force)),
    )


def lorentz_force_per_layer(
    *, q: float, v: Sequence[float], B: Sequence[float]
) -> Tuple[LayerLorentzForce, ...]:
    """Evaluate F = q v x B for every layer the paper ties to the magnetic field."""
    return tuple(
        layer_lorentz_force(spec.key, q=q, v=v, B=B) for spec in EPAS_LAYERS if spec.lorentz_applies
    )


__all__ = [
    "CLAIM_STATE",
    "EPAS_LAYERS",
    "EpasLayer",
    "F_COUNTER_HZ",
    "HYPOTHESIS_BAND_HZ",
    "HYPOTHESIS_BAND_LABEL",
    "HYPOTHESIS_BAND_SOURCES",
    "LayerLorentzForce",
    "OPERATING_POINT_FROM_PAPER",
    "OPERATING_POINT_LINES",
    "PAPER_SOURCE",
    "PHI",
    "SEED_HZ",
    "epas_layer",
    "layer_lorentz_force",
    "lorentz_force",
    "lorentz_force_per_layer",
]
