"""HNC photon feedback loop: a phenomenological frequency-sweep model.

Source: G. Leckey, "The Harmonic Nexus Core: A Unified Framework for Emergent
Spacetime and Coherent Information Dynamics" (line numbers refer to the plain
text copy of the paper used to write this module).

Claim state: HOLD. This is a research model that writes down the paper's
frequency-sweep simulation in code. It is not measured or validated physics.
The paper's landmarks (lines 80-95, 676-680) can be matched by a
phenomenological gain-plus-loss function; standard silicon coefficients give
only limited parametric transfer from external pumps. Nothing here claims more.

What the paper fixes, and what it does not:

* Sweep: 1 THz to 10 PHz, sampling interval ~90 GHz (lines 67-69).
* Baseline: ``E_ideal = h f`` (line 70).  ``h`` is the exact SI value.
* Observable: ``100 % x (E_mod - E_ideal) / E_ideal`` (lines 71-74).
* Gain from four-wave mixing, ``f4 = f1 + f2 - f3`` (lines 118-123, 163-170).
* Loss from two-photon absorption (proportional to intensity squared, so a
  fractional loss proportional to intensity) and free-carrier absorption
  (carrier density grows with TPA), both saturable (lines 124-133, 172-191).
* Recovery ("Surge Window"): competing gain and loss balance into a stable
  attractor with near-zero net deviation, and the response is path dependent
  (lines 93-103, 136-155).

The paper does not give functional forms, widths, coefficients, onset
frequencies, saturation levels or a relaxation rate.  Every such quantity is
an explicit, required field of :class:`PhotonFeedbackParams`, documented as
"not specified in the paper".  No default values are invented and nothing is
fitted to the reported landmarks.  :data:`PAPER_REPORTED_LANDMARKS` records
what the paper reports so a caller can compare, but nothing in this module
asserts the model reproduces them.

Pure numpy and math; deterministic; no I/O and no side effects at import.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

import numpy as np

CLAIM_STATE = "HOLD"

#: Planck constant, exact SI value (J s).  Used for E_ideal = h f (line 70).
PLANCK_H_J_S = 6.62607015e-34

#: Sweep start, 1 THz (line 68).
SWEEP_F_MIN_HZ = 1.0e12
#: Sweep end, 10 PHz (line 68).
SWEEP_F_MAX_HZ = 1.0e16
#: Sampling interval, "~90 GHz" (line 69).
SWEEP_STEP_HZ = 9.0e10

#: Landmarks the paper reports for its own simulation.  For comparison only;
#: they are not model inputs and nothing is tuned to them.
PAPER_REPORTED_LANDMARKS: Dict[str, Dict[str, float]] = {
    # lines 82-83, 167, 678
    "peak_gain": {"frequency_hz": 1.45e14, "deviation_pct": 30.0},
    # lines 88-89 (-1.79 % at ~9.12e15 Hz); line 678 rounds to -1.8 % near 9e15
    "max_loss": {"frequency_hz": 9.12e15, "deviation_pct": -1.79},
    # lines 94-95, 679: deviation returns to ~0 % by ~1e16 Hz
    "recovery": {"frequency_hz": 1.0e16, "deviation_pct": 0.0},
}


@dataclass(frozen=True)
class PhotonFeedbackParams:
    """Shape parameters of the phenomenological model.

    Every field is not specified in the paper and must be supplied by the
    caller; there are no defaults.

    fwm_peak_gain:
        Fractional FWM gain at ``fwm_peak_hz`` (dimensionless).  Not specified
        in the paper; the paper's +30 % (lines 82-83) is a net observed
        deviation, not this coefficient.
    fwm_peak_hz:
        Centre of the FWM phase-matching band (Hz).  Not specified in the
        paper as a model input.
    fwm_width_decades:
        Standard deviation of the log10-Gaussian FWM band (decades).  Not
        specified in the paper.
    absorption_onset_hz:
        Reference frequency ``f0`` at which the dimensionless drive
        ``x = f / f0`` equals 1 (Hz).  Not specified in the paper.
    tpa_coefficient:
        Fractional TPA loss per unit drive, ``a_tpa * x`` (TPA absorption is
        proportional to intensity squared, line 176, so the *fractional* loss
        is linear in intensity).  Not specified in the paper.
    fca_coefficient:
        Fractional FCA loss ``a_fca * x**2`` (carrier density grows with the
        TPA rate, lines 185-186).  Not specified in the paper.
    loss_saturation:
        Saturated fractional loss ``L_sat`` (lines 129-133, 188-191).  Not
        specified in the paper.
    surge_relaxation:
        Relaxation rate ``kappa`` of the path-dependent restoring term that
        realises the Surge Window attractor (lines 136-150).  Not specified in
        the paper.  The attractor is stable when
        ``0 < kappa * s < 2`` with ``s`` the saturation fraction.
    """

    fwm_peak_gain: float
    fwm_peak_hz: float
    fwm_width_decades: float
    absorption_onset_hz: float
    tpa_coefficient: float
    fca_coefficient: float
    loss_saturation: float
    surge_relaxation: float

    def __post_init__(self) -> None:
        for name in ("fwm_peak_hz", "fwm_width_decades", "absorption_onset_hz", "loss_saturation"):
            if not getattr(self, name) > 0:
                raise ValueError(f"{name} must be > 0")
        for name in ("fwm_peak_gain", "tpa_coefficient", "fca_coefficient", "surge_relaxation"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be >= 0")


def frequency_sweep(
    f_min_hz: float = SWEEP_F_MIN_HZ,
    f_max_hz: float = SWEEP_F_MAX_HZ,
    step_hz: float = SWEEP_STEP_HZ,
) -> np.ndarray:
    """Linear sweep ``f_k = f_min + k * step`` for every ``f_k <= f_max``.

    Defaults are the paper's 1 THz to 10 PHz at ~90 GHz (lines 67-69).
    """
    if not (f_min_hz > 0 and f_max_hz >= f_min_hz and step_hz > 0):
        raise ValueError("need 0 < f_min <= f_max and step > 0")
    count = int(math.floor((f_max_hz - f_min_hz) / step_hz)) + 1
    return f_min_hz + step_hz * np.arange(count, dtype=float)


def photon_energy_ideal(frequency_hz):
    """``E_ideal = h f`` in joules (line 70)."""
    return PLANCK_H_J_S * np.asarray(frequency_hz, dtype=float)


def fwm_gain(frequency_hz, params: PhotonFeedbackParams) -> np.ndarray:
    """Phenomenological FWM gain band (lines 118-123, 163-170).

    ``G(f) = g0 * exp(-(log10(f / f_g))**2 / (2 w**2))``.  The log-Gaussian
    shape is a modelling choice; the paper gives no functional form.
    """
    f = np.asarray(frequency_hz, dtype=float)
    z = np.log10(f / params.fwm_peak_hz) / params.fwm_width_decades
    return params.fwm_peak_gain * np.exp(-0.5 * z * z)


def tpa_fca_loss(frequency_hz, params: PhotonFeedbackParams) -> np.ndarray:
    """Saturable TPA + FCA fractional loss (lines 124-133, 172-191).

    ``x = f / f0``; ``raw = a_tpa * x + a_fca * x**2``;
    ``L = raw / (1 + raw / L_sat)``, which grows with ``x`` and then stops
    increasing, approaching ``L_sat`` ("maxes out", line 190).
    """
    x = np.asarray(frequency_hz, dtype=float) / params.absorption_onset_hz
    raw = params.tpa_coefficient * x + params.fca_coefficient * x * x
    return raw / (1.0 + raw / params.loss_saturation)


def surge_window_sweep(open_loop_deviation, saturation_fraction, relaxation: float) -> np.ndarray:
    """Path-dependent restoring term along the sweep (lines 98-103, 136-150).

    With ``D_n`` the open-loop deviation (gain minus loss) and ``s_n`` in
    ``[0, 1)`` the loss saturation fraction, the closed-loop deviation is
    ``d_n = D_n + C_n`` with ``C_0 = 0`` and ``C_{n+1} = C_n - kappa * s_n * d_n``.
    For constant ``D`` and ``s`` this gives ``d_{n+1} = (1 - kappa s) d_n``:
    ``d = 0`` (the Surge Window, gain and loss balanced) is the fixed point and
    is stable for ``0 < kappa s < 2``.  Each value depends on the history of
    the sweep, which is the path dependence the paper describes.
    """
    open_loop = np.asarray(open_loop_deviation, dtype=float)
    sat = np.asarray(saturation_fraction, dtype=float)
    if open_loop.shape != sat.shape:
        raise ValueError("open_loop_deviation and saturation_fraction must have the same shape")
    out = np.empty_like(open_loop)
    compensation = 0.0
    for n in range(open_loop.size):
        d = open_loop.flat[n] + compensation
        out.flat[n] = d
        compensation -= relaxation * sat.flat[n] * d
    return out


def modulated_energy(frequency_hz, params: PhotonFeedbackParams) -> Dict[str, np.ndarray]:
    """``E_mod = E_ideal * (1 + d)`` with ``d`` the closed-loop deviation.

    The frequencies must be in sweep order, because the restoring term is
    path dependent.  Returns ``frequency_hz``, ``e_ideal_j``, ``e_mod_j``,
    ``gain``, ``loss``, ``deviation`` (fraction) and ``deviation_pct``
    (``100 x (E_mod - E_ideal) / E_ideal``, lines 71-74).
    """
    f = np.asarray(frequency_hz, dtype=float)
    gain = fwm_gain(f, params)
    loss = tpa_fca_loss(f, params)
    deviation = surge_window_sweep(gain - loss, loss / params.loss_saturation, params.surge_relaxation)
    e_ideal = photon_energy_ideal(f)
    e_mod = e_ideal * (1.0 + deviation)
    return {
        "frequency_hz": f,
        "e_ideal_j": e_ideal,
        "e_mod_j": e_mod,
        "gain": gain,
        "loss": loss,
        "deviation": deviation,
        "deviation_pct": 100.0 * (e_mod - e_ideal) / e_ideal,
    }


def profile_landmarks(frequency_hz, deviation_pct) -> Dict[str, Dict[str, float]]:
    """Peak gain, maximum loss and final deviation of a computed profile.

    Same keys as :data:`PAPER_REPORTED_LANDMARKS` so a caller can put them side
    by side.  This only reads the profile; it does not judge a match.
    """
    f = np.asarray(frequency_hz, dtype=float)
    d = np.asarray(deviation_pct, dtype=float)
    i_max = int(np.argmax(d))
    i_min = int(np.argmin(d))
    return {
        "peak_gain": {"frequency_hz": float(f[i_max]), "deviation_pct": float(d[i_max])},
        "max_loss": {"frequency_hz": float(f[i_min]), "deviation_pct": float(d[i_min])},
        "recovery": {"frequency_hz": float(f[-1]), "deviation_pct": float(d[-1])},
    }


__all__ = [
    "CLAIM_STATE",
    "PAPER_REPORTED_LANDMARKS",
    "PLANCK_H_J_S",
    "SWEEP_F_MAX_HZ",
    "SWEEP_F_MIN_HZ",
    "SWEEP_STEP_HZ",
    "PhotonFeedbackParams",
    "fwm_gain",
    "frequency_sweep",
    "modulated_energy",
    "photon_energy_ideal",
    "profile_landmarks",
    "surge_window_sweep",
    "tpa_fca_loss",
]
