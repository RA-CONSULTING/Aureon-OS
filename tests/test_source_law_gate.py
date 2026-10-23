"""Source-law gate. Every case here makes HOLD easier and EXECUTE harder."""

from __future__ import annotations

import json
import time

import pytest

from aureon.queen import queen_source_law as law


class _State:
    def __init__(self, gamma: float) -> None:
        self.coherence_gamma = gamma
        self.consciousness_psi = 0.9
        self.consciousness_level = "UNIFIED"
        self.symbolic_life_score = 0.5


class _Engine:
    def __init__(self, gamma: float = 0.938, error: BaseException | None = None) -> None:
        self.gamma = gamma
        self.error = error

    def step(self, readings, volatility=0.05):
        if self.error is not None:
            raise self.error
        return _State(self.gamma)


class _Whisper:
    def __init__(self, name: str) -> None:
        self.verdict = type("Verdict", (), {"name": name})()


class _Conscience:
    def __init__(self, name: str = "APPROVED") -> None:
        self.name = name

    def ask_why(self, action, context=None):
        return _Whisper(self.name)


def _readings(confidence: float = 1.0) -> list[dict]:
    return [
        {
            "name": name,
            "hz": hz,
            "role": role,
            "value": 0.99,
            "confidence": confidence,
            "state": "calm",
        }
        for name, hz, role in law.AURIS_NODES
    ]


def _output(gamma: float, error: BaseException | None = None) -> law.CognitionOutput:
    out = law.CognitionOutput()
    out._lambda_engine = _Engine(gamma, error)
    return out


@pytest.fixture(autouse=True)
def _paper_platform(monkeypatch):
    monkeypatch.setattr("aureon_fusion.fleet_launcher.blocked_reason", lambda: None)
    monkeypatch.setattr(
        "aureon.queen.queen_conscience.get_conscience",
        lambda: _Conscience("APPROVED"),
    )


def test_gamma_boundary_execute_and_hold():
    execute = _output(0.938).collapse(_readings(), 9, 1)
    assert execute.action == "EXECUTE"
    hold = _output(0.9379).collapse(_readings(), 9, 1)
    assert hold.action == "HOLD"


def test_platform_hold_overrides_execute(monkeypatch):
    held = _output(0.99).collapse(_readings(), 9, 1, platform_hold=True)
    assert held.action == "HOLD"
    assert any("platform HOLD" in line for line in held.reasoning)

    monkeypatch.setattr(
        "aureon_fusion.fleet_launcher.blocked_reason",
        lambda: "live trading flag is set",
    )
    pinned = _output(0.99).collapse(_readings(), 9, 1, platform_hold=False)
    assert pinned.action == "HOLD"
    assert any("live trading flag" in line for line in pinned.reasoning)


def test_entry_override_cannot_fall_below_floor(monkeypatch):
    monkeypatch.setenv("AUREON_SOURCE_LAW_ENTRY", "0.5")
    assert law._resolve_threshold("AUREON_SOURCE_LAW_ENTRY", 0.938, floor=0.938) == 0.938
    monkeypatch.setenv("AUREON_SOURCE_LAW_ENTRY", "0.97")
    assert law._resolve_threshold("AUREON_SOURCE_LAW_ENTRY", 0.938, floor=0.938) == 0.97
    clamped = law.CognitionOutput(entry_coherence=0.5)
    assert clamped._entry_coherence >= 0.938


def test_engine_error_returns_hold_not_node_average():
    broken = _output(0.99, error=RuntimeError("lambda down")).collapse(_readings(), 9, 1)
    assert broken.action == "HOLD"
    assert broken.coherence_gamma == 0.0
    missing = law.CognitionOutput()
    missing._lambda_engine = None
    refused = missing.collapse(_readings(), 9, 1)
    assert refused.action == "HOLD"
    assert refused.coherence_gamma == 0.0


def test_queen_veto_forces_hold(monkeypatch):
    vetoed = _output(0.99).collapse(
        _readings(),
        9,
        1,
        queen_veto=lambda readings: (True, "sovereign veto"),
    )
    assert vetoed.action == "HOLD"
    assert any("sovereign veto" in line for line in vetoed.reasoning)

    low = _output(0.99).collapse(_readings(confidence=0.1), 9, 1)
    assert low.action == "HOLD"
    assert any("VETO" in line for line in low.reasoning)

    monkeypatch.setattr(
        "aureon.queen.queen_conscience.get_conscience",
        lambda: _Conscience("VETO"),
    )
    conscience = _output(0.99).collapse(_readings(), 9, 1)
    assert conscience.action == "HOLD"
    assert any("veto" in line.lower() for line in conscience.reasoning)


def test_zero_input_hnc_step_is_degraded_no_data(tmp_path):
    from aureon_fusion import flight_recorder as recorder

    path = tmp_path / "hnc_core_state.json"
    path.write_text(
        json.dumps({
            "timestamp": time.time(),
            "truth_status": "real_derived",
            "input_count": 0,
            "inputs": {},
        }),
        encoding="utf-8",
    )
    faculty = {
        "name": "hnc_core",
        "path": path,
        "ts_keys": ("timestamp",),
        "source_id": "hnc_core",
    }
    record = recorder._build_record(time.time(), faculty)
    assert record["truth_status"] == "no_data"
    assert record["status"] == "degraded"

    path.write_text(
        json.dumps({
            "timestamp": time.time(),
            "truth_status": "real_derived",
            "input_kp_index": 1.0,
        }),
        encoding="utf-8",
    )
    measured = recorder._build_record(time.time(), faculty)
    assert measured["truth_status"] == "real_derived"
    assert measured["status"] == "fresh"


def test_core_state_write_errors_propagate(monkeypatch, tmp_path):
    from aureon_fusion import hnc_core

    target = tmp_path / "hnc_core_state.json"
    monkeypatch.setattr(hnc_core, "CORE_STATE_PATH", target)
    real_open = open

    def boom(*args, **kwargs):
        name = args[0] if args else kwargs.get("file")
        if str(name).endswith(".tmp"):
            raise OSError("disk full")
        return real_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", boom)
    with pytest.raises(OSError, match="disk full"):
        hnc_core._save_core_state({"organ": "hnc_core"})


def test_check_reports_when_hnc_core_organ_is_not_running(monkeypatch, tmp_path, capsys):
    from aureon_fusion import fleet_launcher
    from aureon_fusion import hnc_core

    monkeypatch.setattr(hnc_core, "ORGAN_PID_PATH", tmp_path / "absent.pid")
    monkeypatch.setattr(hnc_core, "CORE_STATE_PATH", tmp_path / "absent.json")
    alive, why = hnc_core.organ_running()
    assert alive is False
    assert why == "hnc_core organ is not running"

    code = fleet_launcher.main(["--check"])
    captured = capsys.readouterr().out
    assert code == 1
    assert "hnc_core organ is not running" in captured


def test_lambda_matches_the_master_equation(tmp_path):
    """Λ(t) = Σ wᵢ sin(2πfᵢt + φᵢ) + α tanh(g Λ̄_Δt) + β Λ(t−τ)."""
    import math

    from aureon.core.aureon_lambda_engine import (
        ALPHA,
        BETA,
        DELTA_T,
        FREQUENCIES,
        G,
        TAU,
        WEIGHTS,
        LambdaEngine,
        SubsystemReading,
    )

    engine = LambdaEngine(state_path=tmp_path / "lambda.json")
    readings = [
        SubsystemReading(name="a", value=0.4, confidence=1.0, state="measured"),
        SubsystemReading(name="b", value=0.6, confidence=0.5, state="measured"),
    ]
    history: list[float] = []
    for step in range(1, 13):
        state = engine.step(readings, volatility=0.0, auto_persist=False)
        harmonic_sum = sum(
            weight * math.sin(2 * math.pi * (freq / 1000.0) * step)
            for freq, weight in zip(FREQUENCIES, WEIGHTS)
        )
        subsystem_avg = sum(item.value * item.confidence for item in readings) / len(readings)
        substrate = (harmonic_sum + subsystem_avg) / 2.0
        observer = 0.0
        if len(history) >= DELTA_T:
            recent = history[-DELTA_T:]
            observer = ALPHA * math.tanh(G * (sum(recent) / len(recent)))
        echo = 0.0
        if len(history) >= TAU:
            echo = BETA * history[-TAU]
        assert state.substrate == pytest.approx(substrate)
        assert state.observer == pytest.approx(observer)
        assert state.echo == pytest.approx(echo)
        assert state.lambda_t == pytest.approx(substrate + observer + echo)
        history.append(state.lambda_t)
    assert len(history) > TAU


def test_real_engine_gamma_gate(tmp_path, monkeypatch):
    """Γ from the lambda engine, then the 0.938 source-law gate."""
    from aureon.core.aureon_lambda_engine import LambdaEngine

    monkeypatch.setattr(
        "aureon.core.hnc_field.canonical_field_reading",
        lambda *args, **kwargs: None,
    )
    out = law.CognitionOutput()
    out._lambda_engine = LambdaEngine(state_path=tmp_path / "gate.json")

    equal = _readings(confidence=1.0)
    for row in equal:
        row["value"] = 0.8
    executed = out.collapse(equal, 9, 1)
    assert executed.coherence_gamma >= 0.938
    assert executed.action == "EXECUTE"

    spread = _readings(confidence=1.0)
    for index, row in enumerate(spread):
        row["value"] = 0.1 if index % 2 == 0 else 0.95
    held = out.collapse(spread, 9, 2)
    assert held.coherence_gamma < 0.938
    assert held.action == "HOLD"


def test_low_node_confidence_forces_hold_even_at_high_gamma():
    """Nine nodes at confidence 0.2 cannot EXECUTE, even at Γ 0.99."""
    held = _output(0.99).collapse(_readings(confidence=0.2), 9, 1)
    assert held.action == "HOLD"
    assert held.coherence_gamma == 0.99
    assert any("node confidence" in line for line in held.reasoning)
    cleared = _output(0.99).collapse(_readings(confidence=0.5), 9, 1)
    assert cleared.action == "EXECUTE"


def test_canonical_auris_table_tiger_220_clownfish_963():
    from aureon.core.aureon_unified import MasterEquationSystem
    from aureon.trading.aureon_auris_trader import AurisEngine, CANONICAL_AURIS_HZ
    from aureon.trading.aureon_unified_ecosystem import CONFIG as trading_config
    from Kings_Accounting_Suite.core.hnc_auris_nodes import HNCAurisEngine

    assert MasterEquationSystem.AURIS_NODES["Tiger"]["freq"] == 220.0
    assert MasterEquationSystem.AURIS_NODES["Clownfish"]["freq"] == 963.0
    assert trading_config["FREQ_TIGER"] == 220.0
    assert trading_config["FREQ_CLOWNFISH"] == 963.0
    assert trading_config["QUARANTINED_FREQ_TIGER"] == 741.0
    assert trading_config["QUARANTINED_FREQ_CLOWNFISH"] == 639.0
    engine = AurisEngine()
    live = {node.name: node.freq for node in engine.nodes}
    assert live == CANONICAL_AURIS_HZ
    assert live["Tiger"] == 220.0 and live["Clownfish"] == 963.0
    kings = {node.name: node.freq for node in HNCAurisEngine().nodes}
    assert kings["Tiger"] == 220.0 and kings["Clownfish"] == 963.0
    from aureon_fusion.hnc_core import GAMMA_TARGET, SOURCE_LAW_ENTRY_FLOOR

    assert GAMMA_TARGET >= SOURCE_LAW_ENTRY_FLOOR
    assert GAMMA_TARGET == 0.945
    assert SOURCE_LAW_ENTRY_FLOOR == 0.938
