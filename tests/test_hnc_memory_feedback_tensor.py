"""Hand-worked checks for aureon.harmonic.hnc_memory_feedback_tensor.

Paper line numbers refer to the plain-text copy of Leckey, "The Harmonic Nexus
Core".  Expected values are worked by hand beside each check; kernels, delays
and gains are round test inputs because the paper specifies none.  Claim
state HOLD.
"""

from __future__ import annotations

import ast
import math
from pathlib import Path

import numpy as np
import pytest

from aureon.harmonic import hnc_memory_feedback_tensor as mt

MODULE = Path(mt.__file__)
I4 = np.eye(4)
ETA = np.diag([-1.0, 1.0, 1.0, 1.0])


def test_theta_is_zero_with_no_history():
    # No history -> nothing to remember -> Theta = 0 (lines 252-259).
    assert np.array_equal(mt.memory_feedback_tensor(np.zeros((0, 4, 4)), [1.0, 0.5]), np.zeros((4, 4)))
    assert np.array_equal(mt.memory_feedback_tensor([], [1.0]), np.zeros((4, 4)))
    # All-zero history -> Theta = 0.
    assert np.array_equal(mt.memory_feedback_tensor(np.zeros((5, 4, 4)), [1.0, 0.5, 0.25]), np.zeros((4, 4)))


def test_convolution_hand_value_lines_294_298():
    # history (oldest -> newest): 1*I, 2*I, 3*I.  Lag 0 = 3I, lag 1 = 2I, lag 2 = I.
    # w = [0.5, 0.25, 0.125] -> 0.5*3 + 0.25*2 + 0.125*1 = 1.5 + 0.5 + 0.125 = 2.125 on the diagonal.
    hist = np.stack([1 * I4, 2 * I4, 3 * I4])
    theta = mt.memory_feedback_tensor(hist, [0.5, 0.25, 0.125])
    assert theta == pytest.approx(2.125 * I4)
    # Kernel longer than history: extra lags see nothing.
    assert mt.memory_feedback_tensor(hist, [0.5, 0.25, 0.125, 9.0]) == pytest.approx(2.125 * I4)


def test_theta_is_rank2_and_symmetric_and_rejects_asymmetric_phi():
    a = np.arange(16.0).reshape(4, 4)
    sym = a + a.T
    theta = mt.memory_feedback_tensor(np.stack([sym, ETA]), [1.0, 1.0])
    assert theta.shape == (4, 4)
    assert np.array_equal(theta, theta.T)
    assert theta == pytest.approx(sym + ETA)
    with pytest.raises(ValueError):
        mt.memory_feedback_tensor(np.stack([a]), [1.0])


def test_jitter_cancels_and_coherent_history_reinforces_lines_276_281():
    # Alternating +Phi, -Phi (highest-frequency jitter) under a flat 4-lag kernel:
    # 0.25*(+1 -1 +1 -1) = 0.  A constant history: 0.25*(1+1+1+1) = 1.
    jitter = np.stack([((-1) ** k) * ETA for k in range(8)])
    steady = np.stack([ETA for _ in range(8)])
    flat = [0.25, 0.25, 0.25, 0.25]
    assert mt.memory_feedback_tensor(jitter, flat) == pytest.approx(np.zeros((4, 4)))
    assert mt.memory_feedback_tensor(steady, flat) == pytest.approx(ETA)


def test_delayed_echo_kernel_matches_causal_echo_lag():
    # tau = 0.02 s at 100 Hz -> int(2.0) + 1 = 3 samples, weight beta at index 3.
    w = mt.delayed_echo_kernel(0.02, 0.9, 100.0)
    assert w.tolist() == [0.0, 0.0, 0.0, 0.9]


def test_stream_equals_causal_echo_component_for_component():
    from aureon.harmonic.aureon_harmonic_reality import CausalEcho

    tau, beta, sr = 0.02, 0.9, 100.0
    stream = [float(k + 1) for k in range(8)]
    echo = CausalEcho(tau=tau, beta=beta, sample_rate=sr)
    scalar = [echo.evaluate(x) for x in stream]
    # Hand: lag 3, so outputs 0, 0, 0, 0.9*1, 0.9*2, 0.9*3, 0.9*4, 0.9*5.
    assert scalar == pytest.approx([0, 0, 0, 0.9, 1.8, 2.7, 3.6, 4.5])

    tensor = mt.MemoryFeedbackTensor(tau=tau, beta=beta, sample_rate=sr)
    out = [tensor.evaluate(x * ETA) for x in stream]
    for got, want in zip(out, scalar, strict=True):
        assert got == pytest.approx(want * ETA)

    # Batch convolution with the same kernel gives the last streamed value.
    hist = np.stack([x * ETA for x in stream[:-1]])  # history up to the call before last
    w = mt.delayed_echo_kernel(tau, beta, sr)
    assert mt.memory_feedback_tensor(np.concatenate([hist, [stream[-1] * ETA]]), w) == pytest.approx(
        0.9 * stream[-1 - 3] * ETA
    )


def test_reset_forgets_history():
    t = mt.MemoryFeedbackTensor(tau=0.0, beta=1.0, sample_rate=10.0)
    t.evaluate(ETA)
    t.reset()
    assert np.array_equal(t.evaluate(I4), np.zeros((4, 4)))


def test_surge_window_residual_lines_309_312():
    # Theta = -dT^mod -> residual 0 and source equals the Planck term alone.
    d_mod = 0.3 * ETA
    assert np.array_equal(mt.surge_window_residual(d_mod, -d_mod), np.zeros((4, 4)))
    t_planck = np.diag([1.0, 1 / 3, 1 / 3, 1 / 3])
    assert np.array_equal(mt.modified_efe_source(t_planck, d_mod, -d_mod), mt.modified_efe_source(t_planck, 0, 0))


def test_einstein_coupling_hand_value_line_222():
    # 8 * pi * 6.67430e-11 / 299792458**4
    # = 1.677456e-9 / 8.0776087e33 = 2.0766e-43 s^2 m^-1 kg^-1.
    coupling = mt.EINSTEIN_COUPLING
    assert coupling == pytest.approx(8 * math.pi * 6.67430e-11 / 299792458.0**4, rel=1e-15)
    assert coupling == pytest.approx(2.0766e-43, rel=1e-4)
    src = mt.modified_efe_source(I4, I4, I4)
    assert src == pytest.approx(3 * mt.EINSTEIN_COUPLING * I4)


def test_unspecified_constants_are_required():
    with pytest.raises(TypeError):
        mt.MemoryFeedbackTensor()  # type: ignore[call-arg]
    assert mt.CLAIM_STATE == "HOLD"


def test_module_imports_only_math_and_numpy():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots <= {"__future__", "math", "collections", "typing", "numpy"}
    src = MODULE.read_text(encoding="utf-8")
    assert "np.random" not in src and "import random" not in src
