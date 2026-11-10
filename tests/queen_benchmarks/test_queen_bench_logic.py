"""Queen logic seed set — grounded in aureon/gates/benchmark.py.

Every value here is one the gate-switchboard benchmark itself uses (its STRONG /
DIVERGENT / BLIND readings, panel tiers 0.3/0.7/0.95, evidence k/PANEL_INPUTS,
divergence bar 0.35 = grounded_action._DIVERGENCE_CAUTION). No recorded
gate_switchboard_benchmark.json exists on disk, so these assert the benchmark's
critical contract, not a stored score.
"""

import pytest

from aureon.gates import benchmark as gb
from aureon.gates.panel import PANEL_INPUTS
from aureon.gates.switchboard import ADVANCE, DEFAULT_CHAIN, HOLD, HUMAN_HELD, REDO, evaluate

ACT = DEFAULT_CHAIN[0]


def test_gate_benchmark_critical_tier_all_pass():
    checks = gb.run_gates_benchmark()
    failed = [c["check"] for c in checks if c["critical"] and not c["ok"]]
    assert failed == []
    assert gb.build_report(checks)["summary"]["status"] == "pass"


@pytest.mark.parametrize("action", sorted(HUMAN_HELD) + ["TRANSFER"])
def test_human_held_actions_hold_at_full_confidence(action):
    assert evaluate(ACT, gb.STRONG, context={"action": action}).decision == HOLD


def test_ordinary_action_can_advance():
    assert evaluate(ACT, gb.STRONG, context={"action": "draft"}).decision == ADVANCE


def test_human_gate_holds_and_keeps_confidence():
    submit = DEFAULT_CHAIN[-1]
    verdict = evaluate(submit, gb.STRONG)
    assert submit.requires_human
    assert verdict.decision == HOLD
    assert verdict.confidence == 0.95


def test_divergence_bar_is_035_and_forces_redo():
    assert abs(ACT.max_divergence - 0.35) < 1e-9
    assert evaluate(ACT, gb._reading(divergence=ACT.max_divergence)).decision == REDO
    assert evaluate(ACT, gb.DIVERGENT).decision == REDO
    assert evaluate(ACT, gb._reading(divergence=ACT.max_divergence - 0.01)).decision == ADVANCE


@pytest.mark.parametrize("tier", (0.3, 0.7, 0.95))
def test_confidence_is_panel_times_evidence(tier):
    for k in range(PANEL_INPUTS + 1):
        ratio = k / PANEL_INPUTS
        verdict = evaluate(ACT, gb._reading(confidence=tier, evidence=ratio))
        assert verdict.confidence is not None
        assert abs(verdict.confidence - tier * ratio) < 1e-9


def test_unanimous_on_defaults_and_blind_redo():
    ungrounded = evaluate(ACT, gb.UNGROUNDED)
    assert ungrounded.decision == REDO and ungrounded.confidence == 0.0
    blind = evaluate(ACT, gb.BLIND)
    assert blind.decision == REDO and blind.confidence is None
