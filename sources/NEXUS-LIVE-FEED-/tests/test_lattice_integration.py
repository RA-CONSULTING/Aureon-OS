from __future__ import annotations

import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from lattice_integration import (
    LatticeIntegrationConfig,
    LatticeIntegrator,
    LatticeState,
    SymbolicCompiler,
    UnityTensorField,
)


def build_integrator() -> LatticeIntegrator:
    compiler = SymbolicCompiler(
        keyword_map={"harmonize": (528.0, 1.0), "protect": (396.0, 1.2)},
        default_frequency=528.0,
        default_decay=1.1,
    )
    field = UnityTensorField(samples=[{"phi": 0.0, "kappa": 0.0, "psi": 0.0, "tsv": 0.9}])
    config = LatticeIntegrationConfig(phi_threshold=0.2, dissonance_cap=0.3, epsilon=0.05)
    return LatticeIntegrator(compiler=compiler, tensor_field=field, config=config)


def test_symbolic_compiler_lookup_and_waveform() -> None:
    compiler = SymbolicCompiler(keyword_map={"stabilize": (432.0, 1.0)})
    freqs, decays = compiler.lookup("stabilize + unknown")
    assert math.isclose(freqs[0], 432.0)
    assert len(freqs) == len(decays) == 2

    waveform = compiler.synthesize("stabilize")
    assert waveform  # non-empty
    assert max(abs(value) for value in waveform) <= 1.0


def test_integrator_respects_prime_window() -> None:
    integrator = build_integrator()
    base_state = LatticeState(
        intent="harmonize",
        cp=0.86,
        coherence=0.42,
        phi_ga=0.05,
        dissonance=0.1,
        x_norm=0.9,
        phi=0.0,
        kappa=0.0,
        psi=0.0,
        psi_max=8.5,
        previous_drive=0.1,
        yield_metric=0.4,
    )
    open_result = integrator.integrate(base_state)
    assert open_result.drive != 0.0
    assert open_result.sandbox["phase_lock"] is True

    blocked_state = LatticeState(
        intent="harmonize",
        cp=0.86,
        coherence=0.42,
        phi_ga=0.6,
        dissonance=0.4,
        x_norm=0.9,
        phi=0.0,
        kappa=0.0,
        psi=0.0,
        psi_max=13.0,
        previous_drive=open_result.drive,
        yield_metric=0.41,
    )
    blocked_result = integrator.integrate(blocked_state)
    assert abs(blocked_result.drive) <= abs(open_result.drive)
    assert blocked_result.sandbox["stability_alert"] is True
