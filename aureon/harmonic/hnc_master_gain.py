"""The Master Formula gain g as a gain-loss-recovery profile, not a constant.

CLAIM_STATE is HOLD.  This is a research model of Gary Leckey's HNC work, not
a measurement of any running system.

What Gary said (12 Nov 2026, in his own words, recorded by the team): g "is
more like 1 to 1.3", it follows "gain loss recovery", and "it fluctuates".
He confirmed ("Yes go") that g is read from the gain-loss-recovery profile of
the HNC photon feedback loop.  That link is Gary's instruction; the paper
lines below do not themselves name g.

Source.  Leckey, "The Harmonic Nexus Core: A Unified Framework for Emergent
Spacetime and Coherent Information Dynamics", plain-text copy
``sero_research.txt``.  Line numbers count newlines only (``sed -n 'Np'``).
The landmarks are taken from
:data:`aureon.harmonic.hnc_photon_feedback_loop.PAPER_REPORTED_LANDMARKS`
so the two modules cannot drift apart:

  * Gain: peak of about +30 % at ~1.45e14 Hz (lines 82-83), so g ~ 1.30.
  * Loss: maximum deficit of about -1.79 % at ~9.12e15 Hz (line 89),
    so g ~ 0.9821.  This sits slightly below 1.0; Gary's "1 to 1.3" is
    taken as a rounded description, and the paper's figure is kept.
  * Recovery: deviation returns to ~0 % by ~1e16 Hz (lines 94-95), so g ~ 1.0.

Definition used here: g = E_mod / E_ideal = 1 + deviation_pct / 100, the
ratio of modulated to ideal photon energy (observable at lines 71-74).

What the paper does not give, and how this module handles it:
  * Values between the landmarks.  :func:`gain_at_frequency` interpolates
    linearly in log10(f) between the three landmarks.  That is a modelling
    choice, not the paper's curve, and the result says so.  Outside
    [1.45e14, 1e16] Hz it raises instead of extrapolating.
  * Path dependence (lines 100-104).  The landmark interpolation has none.
    For a history-dependent g, compute a profile with
    ``hnc_photon_feedback_loop.modulated_energy`` (caller-supplied
    parameters, path-dependent restoring term) and convert it with
    :func:`gain_from_deviation_pct`.

Not wired in.  The Master Formula paper (zenodo.17527831 eq. 5) prints
g = 1.5, and several modules read a fixed g.  None of them is changed here;
switching them to this profile is a separate, gated change, because it moves
the formula's output and may shift existing coherence cut-offs.

No randomness, no I/O and no side effects at import.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple

import numpy as np

from aureon.harmonic.hnc_photon_feedback_loop import PAPER_REPORTED_LANDMARKS

CLAIM_STATE = "HOLD"

PAPER_SOURCE = "sero_research.txt (Leckey, The Harmonic Nexus Core)"
LANDMARK_LINES = {"peak_gain": "82-83", "max_loss": "89", "recovery": "94-95"}
GARY_DIRECTION = (
    "12 Nov 2026: g fluctuates about 1 to 1.3 through gain, loss and recovery; "
    "read from the photon loop gain-loss-recovery profile ('Yes go')"
)
INTERPOLATION_SOURCE = (
    "modelling choice: linear in log10(f) between the paper's landmarks; "
    "the paper gives no values between them"
)

_ORDER = ("peak_gain", "max_loss", "recovery")


def gain_from_deviation_pct(deviation_pct):
    """g = 1 + deviation_pct / 100 (E_mod / E_ideal), element-wise.

    Raises ValueError on non-finite input or on a deviation at or below -100 %,
    where E_mod would be zero or negative.
    """
    d = np.asarray(deviation_pct, dtype=float)
    if not np.all(np.isfinite(d)):
        raise ValueError("deviation_pct must be finite")
    if np.any(d <= -100.0):
        raise ValueError("deviation_pct must be above -100 %")
    g = 1.0 + d / 100.0
    return float(g) if g.ndim == 0 else g


def landmark_gains() -> Dict[str, Dict[str, float]]:
    """The three paper landmarks with their g value, in sweep order."""
    out: Dict[str, Dict[str, float]] = {}
    for key in _ORDER:
        lm = PAPER_REPORTED_LANDMARKS[key]
        out[key] = {
            "frequency_hz": float(lm["frequency_hz"]),
            "deviation_pct": float(lm["deviation_pct"]),
            "g": gain_from_deviation_pct(lm["deviation_pct"]),
            "lines": LANDMARK_LINES[key],
        }
    return out


def gain_range() -> Tuple[float, float]:
    """(lowest, highest) g over the paper's landmarks."""
    gs = [v["g"] for v in landmark_gains().values()]
    return min(gs), max(gs)


@dataclass(frozen=True)
class GainReading:
    frequency_hz: float
    g: float
    phase: str          # "gain", "loss" or "recovery" (the paper's names)
    source: str         # "paper landmark" or the interpolation note
    claim_state: str = CLAIM_STATE


def gain_at_frequency(frequency_hz: float) -> GainReading:
    """g at one frequency from the paper's landmarks.

    Exact at a landmark; between landmarks, linear in log10(f) (a modelling
    choice, labelled in ``source``).  Raises ValueError outside the landmark
    span or for a non-finite or non-positive frequency.
    """
    f = float(frequency_hz)
    if not math.isfinite(f) or f <= 0.0:
        raise ValueError("frequency_hz must be finite and positive")
    lms = [landmark_gains()[k] for k in _ORDER]
    lo, hi = lms[0]["frequency_hz"], lms[-1]["frequency_hz"]
    if f < lo or f > hi:
        raise ValueError(
            f"frequency_hz outside the paper's landmark span [{lo:g}, {hi:g}] Hz; "
            "the paper gives no landmark there, so g is not extrapolated"
        )
    for lm, key in zip(lms, _ORDER, strict=True):
        if f == lm["frequency_hz"]:
            phase = {"peak_gain": "gain", "max_loss": "loss", "recovery": "recovery"}[key]
            return GainReading(f, lm["g"], phase, f"paper landmark, line {lm['lines']}")
    for a, b, phase in ((lms[0], lms[1], "loss"), (lms[1], lms[2], "recovery")):
        fa, fb = a["frequency_hz"], b["frequency_hz"]
        if fa <= f <= fb:
            t = (math.log10(f) - math.log10(fa)) / (math.log10(fb) - math.log10(fa))
            g = a["g"] + t * (b["g"] - a["g"])
            return GainReading(f, g, phase, INTERPOLATION_SOURCE)
    raise AssertionError("unreachable")  # pragma: no cover


__all__ = [
    "CLAIM_STATE",
    "GARY_DIRECTION",
    "GainReading",
    "INTERPOLATION_SOURCE",
    "LANDMARK_LINES",
    "PAPER_SOURCE",
    "gain_at_frequency",
    "gain_from_deviation_pct",
    "gain_range",
    "landmark_gains",
]
