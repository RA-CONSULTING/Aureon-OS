"""HNC memory feedback tensor Theta_mu_nu: the history term of the modified EFE.

Source: G. Leckey, "The Harmonic Nexus Core: A Unified Framework for Emergent
Spacetime and Coherent Information Dynamics" (line numbers refer to the plain
text copy of the paper used to write this module).

Claim state: HOLD.  This is a research model that writes the paper's equations
in code.  It is not measured or validated physics.

What the paper fixes (lines 213-316):

* Modified EFE (lines 218-226)::

      G_mu_nu + Lambda g_mu_nu = (8 pi G / c**4) (T^Planck_mu_nu + dT^mod_mu_nu(f)
                                                 + Theta^feedback_mu_nu(tau, f))

* Theta is a rank-2 tensor carrying the history-dependent, non-local
  interaction of the field with itself over a time delay tau (lines 252-259).
* The paper adds a non-local memory term to the action, built from a
  symmetric memory field Phi_mu_nu and a memory kernel K:
  ``int d^4x' K(x, x') Phi_mu_nu(x) Phi_mu_nu(x')`` inside the Lagrangian
  (lines 286-298).  Theta is what varying that action with respect to the
  metric gives.
* It averages out high-frequency jitter by destructive interference and
  reinforces coherent structure (lines 276-281).
* In the Surge Window Theta counterbalances dT^mod so the net source
  approaches T^Planck (lines 307-316).

Modelling choice, not from the paper: this module does not derive Theta
from the action.  It uses its own simplification, a linear time-delay sum
``Theta_n = sum_k w_k Phi_(n-k)`` (and the streaming form ``beta *
Phi(t - tau)``), which is the simplest causal stand-in for the memory term.

The paper does not give the kernel K, the delay tau, the gain, or the sign of
the feedback.  Those are explicit caller inputs here, each documented as "not
specified in the paper"; nothing is defaulted or invented.

This module is the tensor counterpart of the scalar ``CausalEcho`` in
``aureon.harmonic.aureon_harmonic_reality`` (``F_feedback(t) = beta *
Lambda(t - tau)``).  It reuses CausalEcho's conventions (``tau`` in seconds,
``beta`` gain, ``sample_rate``, a delay buffer of ``int(tau * sample_rate) + 1``
samples) without importing or changing it, and :class:`MemoryFeedbackTensor`
gives component-for-component the same numbers CausalEcho gives on the same
stream.  It does not compute the Master Formula Lambda(t); a caller who needs
Lambda uses the existing Master Formula code.

Pure numpy and math; deterministic; no I/O and no side effects at import.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Deque

import numpy as np

CLAIM_STATE = "HOLD"

#: Newtonian constant of gravitation, CODATA 2018 (m^3 kg^-1 s^-2).  The paper
#: writes 8 pi G / c**4 (line 222) but quotes no number.
GRAVITATIONAL_CONSTANT = 6.67430e-11
#: Speed of light, exact SI (m/s).
SPEED_OF_LIGHT = 299_792_458.0
#: Einstein coupling 8 pi G / c**4 (s^2 m^-1 kg^-1), line 222.
EINSTEIN_COUPLING = 8.0 * math.pi * GRAVITATIONAL_CONSTANT / SPEED_OF_LIGHT**4

_SYMMETRY_ATOL = 1e-12


def _as_symmetric_field(phi, name: str = "phi") -> np.ndarray:
    arr = np.asarray(phi, dtype=float)
    if arr.ndim < 2 or arr.shape[-1] != arr.shape[-2]:
        raise ValueError(f"{name} must have trailing shape (n, n)")
    if not np.allclose(arr, np.swapaxes(arr, -1, -2), rtol=0.0, atol=_SYMMETRY_ATOL):
        raise ValueError(f"{name} must be symmetric: Phi_mu_nu is a symmetric tensor field (line 295)")
    return arr


def memory_feedback_tensor(history, kernel_weights) -> np.ndarray:
    """Discrete memory convolution ``Theta_n = sum_k w_k Phi_{n-k}``.

    This is the module's own linear time-delay sum on a uniform time grid,
    with ``w_k = K(k dt) dt``.  It is a modelling choice: the paper puts
    ``int K(x, x') Phi_mu_nu(x) Phi_mu_nu(x')`` inside the Lagrangian (lines
    294-298) and this function does not derive Theta from that action.

    history:
        Array of shape (N, n, n), oldest first, newest last; each slice is a
        symmetric Phi_mu_nu.  ``history[-1]`` is lag 0.
    kernel_weights:
        ``w_0, w_1, ...`` for lags 0, 1, ... samples.  The memory kernel K is
        not specified in the paper and must be supplied.  Lags beyond the
        available history contribute nothing (no history, no memory).

    An empty history gives a zero tensor: shape (n, n) for a (0, n, n) array,
    otherwise (4, 4).
    """
    w = np.asarray(kernel_weights, dtype=float).ravel()
    hist = np.asarray(history, dtype=float)
    if hist.size == 0:
        n = hist.shape[-1] if hist.ndim == 3 else 4
        return np.zeros((n, n))
    hist = _as_symmetric_field(hist, "history")
    if hist.ndim != 3:
        raise ValueError("history must have shape (N, n, n)")
    lags = min(w.size, hist.shape[0])
    # history reversed so index k is lag k
    recent = hist[::-1][:lags]
    return np.tensordot(w[:lags], recent, axes=(0, 0))


def delayed_echo_kernel(tau: float, beta: float, sample_rate: float) -> np.ndarray:
    """Kernel equal to CausalEcho's single delayed echo, ``beta * delta(lag - L)``.

    ``L = int(tau * sample_rate) + 1`` samples, which is the lag CausalEcho's
    buffer produces (it returns the value pushed ``L`` calls earlier).  tau,
    beta and sample_rate are not specified in the paper.
    """
    if tau < 0 or sample_rate <= 0:
        raise ValueError("need tau >= 0 and sample_rate > 0")
    lag = int(tau * sample_rate) + 1
    w = np.zeros(lag + 1)
    w[lag] = beta
    return w


def surge_window_residual(delta_t_mod, theta) -> np.ndarray:
    """``dT^mod + Theta``; zero when Theta exactly counterbalances the
    modulation term, so the net source equals T^Planck (lines 309-312)."""
    return np.asarray(delta_t_mod, dtype=float) + np.asarray(theta, dtype=float)


def modified_efe_source(t_planck, delta_t_mod, theta) -> np.ndarray:
    """Right-hand side of the modified EFE (lines 218-226):
    ``(8 pi G / c**4) (T^Planck + dT^mod + Theta)``."""
    total = (
        np.asarray(t_planck, dtype=float)
        + np.asarray(delta_t_mod, dtype=float)
        + np.asarray(theta, dtype=float)
    )
    return EINSTEIN_COUPLING * total


class MemoryFeedbackTensor:
    """Streaming Theta_mu_nu with CausalEcho's single-delay kernel.

    ``Theta(t) = beta * Phi(t - tau)`` component by component, the rank-2
    form of CausalEcho's ``F_feedback(t) = beta * Lambda(t - tau)``.

    tau:
        Memory delay in seconds.  Not specified in the paper.
    beta:
        Feedback gain.  Not specified in the paper; its sign decides whether
        Theta reinforces (beta > 0) or counteracts (beta < 0) the delayed
        field.  (The Master Formula's echo gain is described separately with
        beta in [0.6, 1.1]; that range is not a statement about Theta.)
    sample_rate:
        Samples per second.  Not specified in the paper.
    dim:
        Tensor size n (4 for spacetime).
    """

    def __init__(self, tau: float, beta: float, sample_rate: float, dim: int = 4):
        if tau < 0 or sample_rate <= 0 or dim < 1:
            raise ValueError("need tau >= 0, sample_rate > 0, dim >= 1")
        self.tau = tau
        self.beta = beta
        self.sample_rate = sample_rate
        self.dim = dim
        buffer_size = int(tau * sample_rate) + 1
        self.buffer: Deque[np.ndarray] = deque(
            [np.zeros((dim, dim)) for _ in range(buffer_size)], maxlen=buffer_size
        )

    def evaluate(self, phi_now) -> np.ndarray:
        """Return ``beta * Phi(t - tau)`` and push ``phi_now`` (CausalEcho order)."""
        phi = _as_symmetric_field(phi_now, "phi_now")
        if phi.shape != (self.dim, self.dim):
            raise ValueError(f"phi_now must have shape ({self.dim}, {self.dim})")
        delayed = self.buffer[0]
        self.buffer.append(phi.copy())
        return self.beta * delayed

    def reset(self) -> None:
        """Clear the history; Theta is zero again until the delay refills."""
        self.buffer = deque(
            [np.zeros((self.dim, self.dim)) for _ in range(len(self.buffer))], maxlen=len(self.buffer)
        )


__all__ = [
    "CLAIM_STATE",
    "EINSTEIN_COUPLING",
    "GRAVITATIONAL_CONSTANT",
    "MemoryFeedbackTensor",
    "SPEED_OF_LIGHT",
    "delayed_echo_kernel",
    "memory_feedback_tensor",
    "modified_efe_source",
    "surge_window_residual",
]
