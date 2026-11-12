"""Hand-worked checks for aureon.harmonic.hnc_epas_lorentz.

Paper line numbers refer to the plain-text copy of Leckey, "The Harmonic Nexus
Core" (sero_research.txt, newline count).  Every expected number is worked by
hand in the comment beside it.  Charges, velocities and fields below are round
test inputs: the paper gives none, so none is a default.  Claim state HOLD.
"""

from __future__ import annotations

import ast
import inspect
import math
import re
from pathlib import Path

import pytest

from aureon.harmonic import hnc_epas_lorentz as ep

MODULE = Path(ep.__file__)


def test_claim_state_is_hold():
    assert ep.CLAIM_STATE == "HOLD"


def test_unit_cross_product_lines_510_511():
    # F = q v x B (lines 510-511).  x-hat x y-hat = z-hat, so q=1 gives (0, 0, 1).
    assert ep.lorentz_force(1.0, (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)) == (0.0, 0.0, 1.0)
    # Swapping v and B flips the sign: y-hat x x-hat = -z-hat.
    assert ep.lorentz_force(1.0, (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)) == (0.0, 0.0, -1.0)


def test_electron_round_numbers():
    # q = -1.602176634e-19 C, v = 1e6 m/s along x, B = 1e-5 T along z.
    # x-hat x z-hat = -y-hat, so F = q * 1e6 * 1e-5 * (-y-hat)
    #   = -1.602176634e-19 * 10 * (-1) y-hat = +1.602176634e-18 N along y.
    fx, fy, fz = ep.lorentz_force(-1.602176634e-19, (1.0e6, 0.0, 0.0), (0.0, 0.0, 1.0e-5))
    assert fx == 0.0 and fz == 0.0
    assert fy == pytest.approx(1.602176634e-18, rel=1e-15)


def test_general_vector_and_zero_work():
    # v = (1,2,3), B = (4,5,6): v x B = (2*6-3*5, 3*4-1*6, 1*5-2*4) = (-3, 6, -3).
    # q = 2 gives F = (-6, 12, -6).  F . v = -6 + 24 - 18 = 0: the magnetic
    # force is perpendicular to v, a property of the cross product itself.
    f = ep.lorentz_force(2.0, (1.0, 2.0, 3.0), (4.0, 5.0, 6.0))
    assert f == (-6.0, 12.0, -6.0)
    assert f[0] * 1 + f[1] * 2 + f[2] * 3 == 0.0


def test_parallel_velocity_gives_zero():
    # v parallel to B: v x B = 0 for any q.
    assert ep.lorentz_force(3.0, (0.0, 0.0, 2.0), (0.0, 0.0, 5.0)) == (0.0, 0.0, 0.0)


def test_neutral_particle_lines_519_520():
    # Neutral debris (lines 519-520) has q = 0, so q v x B = 0.
    res = ep.layer_lorentz_force("plasma_ablation", q=0.0, v=(1.0, 0.0, 0.0), B=(0.0, 1.0, 0.0))
    assert res.force == (0.0, 0.0, 0.0) and res.magnitude == 0.0


def test_layers_match_paper_lines():
    keys = [layer.key for layer in ep.EPAS_LAYERS]
    assert keys == ["electromagnetic", "plasma_ablation", "acoustic"]  # three layers, line 506
    lines = {layer.key: layer.paper_lines for layer in ep.EPAS_LAYERS}
    assert lines == {"electromagnetic": "509-515", "plasma_ablation": "518-524", "acoustic": "527-534"}


def test_acoustic_layer_has_no_lorentz_force_lines_527_534():
    with pytest.raises(ValueError, match="no Lorentz force"):
        ep.layer_lorentz_force("acoustic", q=1.0, v=(1.0, 0.0, 0.0), B=(0.0, 1.0, 0.0))


def test_per_layer_magnitude():
    # q = 2, v = (3,0,0), B = (0,4,0): F = 2 * 12 z-hat = (0, 0, 24), |F| = 24.
    # Only the two magnetically coupled layers are evaluated.
    out = ep.lorentz_force_per_layer(q=2.0, v=(3.0, 0.0, 0.0), B=(0.0, 4.0, 0.0))
    assert [r.layer for r in out] == ["electromagnetic", "plasma_ablation"]
    for r in out:
        assert r.force == (0.0, 0.0, 24.0)
        assert r.magnitude == 24.0
        assert r.claim_state == "HOLD"


def test_q_v_B_are_required_with_no_defaults():
    for fn in (ep.lorentz_force, ep.layer_lorentz_force, ep.lorentz_force_per_layer):
        sig = inspect.signature(fn)
        for name in ("q", "v", "B"):
            assert sig.parameters[name].default is inspect.Parameter.empty, (fn.__name__, name)
    with pytest.raises(TypeError):
        ep.layer_lorentz_force("electromagnetic", v=(1.0, 0.0, 0.0), B=(0.0, 1.0, 0.0))


def test_bad_inputs_rejected():
    with pytest.raises(ValueError):
        ep.lorentz_force(1.0, (1.0, 0.0), (0.0, 1.0, 0.0))
    with pytest.raises(ValueError):
        ep.lorentz_force(float("nan"), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    with pytest.raises(ValueError):
        ep.lorentz_force(1.0, (1.0, 0.0, 0.0), (0.0, math.inf, 0.0))
    with pytest.raises(ValueError):
        ep.epas_layer("no_such_layer")


def test_operating_point_not_given_lines_563_566():
    # Lines 563-566 name an operating point but give no numbers.
    assert ep.OPERATING_POINT_FROM_PAPER is None
    assert ep.OPERATING_POINT_LINES == "563-566"


def test_cited_constants():
    # EPAS_Unified_Architecture_v2.md:349: f_counter = 528/phi, stated as 326.3 Hz.
    # phi = 1.6180339887..., 528 / 1.6180339887 = 326.32194606.
    assert ep.SEED_HZ == 528.0
    assert abs(ep.F_COUNTER_HZ - 326.32194606) < 1e-8
    assert round(ep.F_COUNTER_HZ, 1) == 326.3


def test_band_is_labelled_as_the_papers_stated_hypothesis():
    assert ep.HYPOTHESIS_BAND_HZ == (326.0, 854.0)
    assert ep.HYPOTHESIS_BAND_LABEL == "the paper's stated hypothesis"
    assert ep.HYPOTHESIS_BAND_SOURCES == (
        "aureon_fusion/knowledge/whitepapers/EPAS_Unified_Architecture_v2.md:349",
        "aureon_fusion/knowledge/whitepapers/HNC_Project_Druid_EPAS_Technical_Framework.md:237",
    )


def test_wording_and_surface():
    src = MODULE.read_text(encoding="utf-8")
    assert not re.search(r"shield|defen[cs]e|protect|coil", src, re.IGNORECASE)
    public = [n for n in dir(ep) if not n.startswith("_")]
    assert not [n for n in public if re.search(r"emit|drive|output|device|generate", n, re.I)]


def test_import_hygiene():
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            roots.add((node.module or "").split(".")[0])
    assert roots <= {"__future__", "math", "dataclasses", "typing", "numpy"}
    src = MODULE.read_text(encoding="utf-8")
    assert "np.random" not in src and "import random" not in src
    assert "open(" not in src
