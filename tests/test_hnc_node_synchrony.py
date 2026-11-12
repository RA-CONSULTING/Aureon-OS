"""Hand-worked checks for aureon.harmonic.hnc_node_synchrony.

Paper line numbers refer to the plain-text copy of Leckey, "The Harmonic Nexus
Core" (sero_research.txt, newline count).  The paper describes nodes in or out
of sync (lines 615-630), phase lock (line 636) and Anchor as Φ=0 at a node
(lines 599-600), but gives no formula; R and PLV are standard modelling
choices.  Every expected number is worked by hand beside it.  Tolerances are
round test inputs, not values from the paper.  Claim state HOLD.
"""

from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path

import numpy as np
import pytest

from aureon.harmonic import hnc_node_synchrony as ns

MODULE = Path(ns.__file__)


def test_claim_state_and_formula_label():
    assert ns.CLAIM_STATE == "HOLD"
    assert ns.FORMULA_SOURCE.startswith("standard modelling choice")
    assert ns.NODE_COHERENCE_LINES == "615-630" and ns.ANCHOR_LINES == "599-600"


def test_all_nodes_in_unison_lines_617_618():
    # Four nodes all at 0.3 rad: mean e^{i0.3} = e^{i0.3}, so R = 1, ψ = 0.3.
    op = ns.kuramoto_order_parameter([0.3, 0.3, 0.3, 0.3])
    assert abs(op.R - 1.0) < 1e-15
    assert abs(op.psi - 0.3) < 1e-15
    assert op.n_nodes == 4 and op.claim_state == "HOLD"


def test_antiphase_pair_cancels():
    # e^{i0} + e^{iπ} = 1 - 1 = 0, so R = 0.
    assert ns.kuramoto_order_parameter([0.0, math.pi]).R < 1e-15


def test_quarter_turn_pair():
    # (e^{i0} + e^{iπ/2}) / 2 = (1 + i) / 2, |.| = √2/2 = 0.70710678, ψ = π/4.
    op = ns.kuramoto_order_parameter([0.0, math.pi / 2])
    assert abs(op.R - math.sqrt(2) / 2) < 1e-15
    assert abs(op.psi - math.pi / 4) < 1e-15


def test_one_node_out_of_phase_lines_624_626():
    # Two nodes at 0 and one shifted by π: (1 + 1 - 1) / 3 = 1/3.
    assert abs(ns.kuramoto_order_parameter([0.0, 0.0, math.pi]).R - 1.0 / 3.0) < 1e-15


def test_seven_evenly_spaced_phases_give_zero():
    # 2πk/7, k = 0..6: the seventh roots of unity sum to 0, so R = 0.
    phases = [2 * math.pi * k / 7 for k in range(7)]
    assert ns.kuramoto_order_parameter(phases).R < 1e-15


def test_R_is_rotation_invariant():
    # Adding 1.0 rad to every node multiplies the mean by e^{i1}: |.| unchanged.
    base = [0.0, 0.2, 0.5, 1.1]
    r0 = ns.kuramoto_order_parameter(base).R
    r1 = ns.kuramoto_order_parameter([p + 1.0 for p in base]).R
    assert abs(r0 - r1) < 1e-14


def test_plv_constant_lag_is_one_line_636():
    # θ_b(t) = θ_a(t) + 0.5: every difference is -0.5, so |mean e^{-i0.5}| = 1.
    a = [0.0, 1.0, 2.0, 3.0]
    b = [p + 0.5 for p in a]
    assert abs(ns.phase_locking_value(a, b) - 1.0) < 1e-15


def test_plv_wandering_difference_is_zero():
    # Differences 0, -π/2, -π, -3π/2 are the four quarter turns: sum is 0.
    a = [0.0, 0.0, 0.0, 0.0]
    b = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
    assert ns.phase_locking_value(a, b) < 1e-15


def test_plv_two_samples():
    # Differences 0 and -π/2: (1 + (-i)) / 2, |.| = √2/2.
    assert abs(ns.phase_locking_value([0.0, 0.0], [0.0, math.pi / 2]) - math.sqrt(2) / 2) < 1e-15


def test_plv_matrix():
    # Node 0 and node 1 keep a constant 0.5 lag (PLV 1); node 2 has the
    # quarter-turn sequence against node 0 (PLV 0) and against node 1 (also 0,
    # since a constant shift does not change the modulus).
    n0 = [0.0, 0.0, 0.0, 0.0]
    n1 = [0.5, 0.5, 0.5, 0.5]
    n2 = [0.0, math.pi / 2, math.pi, 3 * math.pi / 2]
    m = ns.phase_locking_matrix([n0, n1, n2])
    assert m.shape == (3, 3)
    assert np.allclose(np.diag(m), 1.0)
    assert np.allclose(m, m.T)
    assert abs(m[0, 1] - 1.0) < 1e-12
    assert m[0, 2] < 1e-12 and m[1, 2] < 1e-12


def test_anchor_locked_after_wrap_lines_599_600():
    # 2π + 0.01 wraps to 0.01; |0.01| <= 0.02 so Φ = 0 holds within tolerance.
    res = ns.anchor_phase_lock([1.0, 2 * math.pi + 0.01, 3.0], 1, tolerance=0.02)
    assert abs(res.phase_wrapped - 0.01) < 1e-12
    assert res.locked is True and res.paper_lines == "599-600"


def test_anchor_not_locked():
    # -0.03 is 0.03 from 0, more than 0.02.
    res = ns.anchor_phase_lock([-0.03], 0, tolerance=0.02)
    assert abs(res.deviation - 0.03) < 1e-15
    assert res.locked is False


def test_anchor_at_pi_is_furthest():
    # π (and -π, which wraps to π) is the furthest point from 0: deviation π.
    assert ns.anchor_phase_lock([-math.pi], 0, tolerance=1.0).deviation == math.pi


def test_anchor_held_over_time():
    # Samples 0.0, 0.01, -0.015: worst |.| = 0.015 <= 0.02, held.
    held, worst = ns.anchor_held_over_time([0.0, 0.01, -0.015], tolerance=0.02)
    assert held is True and abs(worst - 0.015) < 1e-15
    # Adding 0.05 breaks it.
    held, worst = ns.anchor_held_over_time([0.0, 0.05], tolerance=0.02)
    assert held is False and abs(worst - 0.05) < 1e-15


def test_tolerance_is_required():
    for fn in (ns.anchor_phase_lock, ns.anchor_held_over_time):
        assert inspect.signature(fn).parameters["tolerance"].default is inspect.Parameter.empty
    with pytest.raises(TypeError):
        ns.anchor_phase_lock([0.0], 0)
    for bad in (0.0, -0.1, 4.0, float("nan")):
        with pytest.raises(ValueError):
            ns.anchor_phase_lock([0.0], 0, tolerance=bad)


def test_bad_inputs_rejected():
    with pytest.raises(ValueError):
        ns.kuramoto_order_parameter([])
    with pytest.raises(ValueError):
        ns.kuramoto_order_parameter([0.0, float("nan")])
    with pytest.raises(ValueError):
        ns.phase_locking_value([0.0, 1.0], [0.0])
    with pytest.raises(ValueError):
        ns.anchor_phase_lock([0.0], 1, tolerance=0.1)
    with pytest.raises(ValueError):
        ns.phase_locking_matrix([[]])


def test_deterministic():
    phases = [0.1 * k for k in range(50)]
    assert ns.kuramoto_order_parameter(phases) == ns.kuramoto_order_parameter(phases)


def test_import_hygiene():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots <= {"__future__", "cmath", "math", "dataclasses", "typing", "numpy"}
    src = MODULE.read_text(encoding="utf-8")
    assert "np.random" not in src and "import random" not in src and "open(" not in src
