"""Hand-worked checks for aureon.harmonic.hnc_auris_codex_glyphs.

Paper line numbers refer to the plain-text copy of Leckey, "The Harmonic Nexus
Core".  Amplitudes, decay times, grids and tolerances are round test inputs
because the paper specifies none.  Claim state HOLD.
"""

from __future__ import annotations

import ast
import json
import math
from pathlib import Path

import numpy as np
import pytest

from aureon.harmonic import hnc_auris_codex_glyphs as cg

MODULE = Path(cg.__file__)
ROOT = Path(__file__).resolve().parents[1]


def test_paper_has_four_glyphs_with_line_ranges():
    assert set(cg.PAPER_GLYPHS) == {"Crown", "Anchor", "Peace", "Seal"}
    for spec in cg.PAPER_GLYPHS.values():
        assert callable(getattr(cg, spec["function"]))
    assert cg.CLAIM_STATE == "HOLD"


def test_crown_laplacian_of_known_potentials_lines_597_598():
    # phi = x^2 + y^2 -> nabla^2 = 2 + 2 = 4 (stencil exact for quadratics), h = 0.5.
    x = np.arange(6) * 0.5
    X, Y = np.meshgrid(x, x, indexing="ij")
    assert cg.crown_laplacian(X**2 + Y**2, 0.5) == pytest.approx(np.full((4, 4), 4.0))
    # phi = x^2 + y^2 + z^2 -> 6.
    g = np.arange(5.0)
    X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    assert cg.crown_laplacian(X**2 + Y**2 + Z**2) == pytest.approx(np.full((3, 3, 3), 6.0))
    # Harmonic phi = x*y -> 0.  1-D phi = 3x^2 -> 6.
    X, Y = np.meshgrid(g, g, indexing="ij")
    assert cg.crown_laplacian(X * Y) == pytest.approx(np.zeros((3, 3)))
    assert cg.crown_laplacian(3 * g**2) == pytest.approx([6.0, 6.0, 6.0])
    # Per-axis spacing: phi = x^2 (hx = 0.5) + y^2 (hy = 2): still 4.
    xs, ys = np.arange(4) * 0.5, np.arange(4) * 2.0
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    assert cg.crown_laplacian(X**2 + Y**2, (0.5, 2.0)) == pytest.approx(np.full((2, 2), 4.0))


def test_anchor_sets_phi_zero_at_node_only_lines_599_600():
    field = np.array([[0.3, 1.2], [2.0, -0.7]])
    out = cg.anchor_phase(field, (1, 0))
    assert out[1, 0] == 0.0
    assert out[0, 0] == 0.3 and out[0, 1] == 1.2 and out[1, 1] == -0.7
    assert field[1, 0] == 2.0  # input not mutated


def test_peace_zero_crossings_at_k_over_2f_lines_601_603():
    # sin(2 pi 8.88 t) = 0 at t = k / (2 * 8.88) = k * 0.05630630... s.
    assert cg.PEACE_FREQUENCY_HZ == 8.88
    t = np.arange(6) / (2 * 8.88)
    assert t[1] == pytest.approx(0.0563063063, rel=1e-9)
    assert cg.peace_waveform(t, 1.0, 1.0, 0.0) == pytest.approx(np.zeros(6), abs=1e-12)
    # Quarter period t = 1/(4*8.88): sin = 1 -> value = exp(-t/T).
    tq = 1 / (4 * 8.88)
    assert cg.peace_waveform(tq, 2.0, 0.5, 0.0) == pytest.approx(2.0 * math.exp(-tq / 0.5), rel=1e-12)


def test_peace_decays_by_exp_minus_period_over_T_line_709():
    # Successive positive peaks are one period P = 1/8.88 s apart, so their ratio
    # is exp(-P/T).  T = 0.5 s: exp(-0.112612.../0.5) = exp(-0.225225...) = 0.79834...
    period = 1 / 8.88
    tq = 1 / (4 * 8.88)
    a, b = cg.peace_waveform([tq, tq + period], 1.0, 0.5, 0.0)
    assert b / a == pytest.approx(math.exp(-period / 0.5), rel=1e-12)
    assert b / a == pytest.approx(0.798336, rel=1e-5)


def test_seal_locks_phase_lines_604_605():
    dt = 0.01
    t = np.arange(10) * dt
    psi = np.exp(1j * 2 * math.pi * 3.0 * t)
    sealed = cg.seal_phase_lock(psi, 4)
    assert np.array_equal(sealed[:5], psi[:5])
    assert np.all(sealed[4:] == psi[4])
    assert np.array_equal(cg.phase_rate(sealed[4:], dt), np.zeros(5))
    assert cg.is_phase_locked(sealed[4:], dt, 0.0)
    # Before the seal the mode evolves: |d psi/dt| ~ 2 pi * 3 ~ 18.8 per s.
    assert not cg.is_phase_locked(psi, dt, 1.0)


def test_legacy_peace_values_still_in_the_json_codex_untouched():
    a = json.loads((ROOT / "public/auris_codex.json").read_text(encoding="utf-8"))
    b = json.loads((ROOT / "public/auris_codex_expanded.json").read_text(encoding="utf-8"))
    assert tuple(a["intent_mappings"]["peace"]["frequencies"]) == (7.83, 6.0, 4.0)
    assert b["prime_frequencies"]["peace"]["hz"] == 432
    assert cg.LEGACY_PEACE["public/auris_codex.json:intent_mappings.peace.frequencies"] == (7.83, 6.0, 4.0)
    assert cg.LEGACY_PEACE["public/auris_codex_expanded.json:prime_frequencies.peace.hz"] == 432


def test_unspecified_constants_are_required():
    with pytest.raises(TypeError):
        cg.peace_waveform(0.0)  # type: ignore[call-arg]
    with pytest.raises(TypeError):
        cg.is_phase_locked([0.0, 0.0], 0.1)  # type: ignore[call-arg]


def test_module_imports_only_math_and_numpy():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots <= {"__future__", "math", "typing", "numpy"}
    src = MODULE.read_text(encoding="utf-8")
    assert "np.random" not in src and "import random" not in src
