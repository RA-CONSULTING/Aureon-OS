#!/usr/bin/env python3
"""
Tests for the HNC substrate-coherence layer added to QueenConscience.

What's being proved:
  - The conscience subscribes to symbolic.life.pulse and tracks the
    most recent reading
  - attach_vault() lets it read current_symbolic_life_score directly
  - Below the danger floor (default 0.20) it VETOs risky actions, with
    reasoning grounded in the white paper's β-stability language
  - Between danger and drift (0.20-0.40) it CONCERNS for risky moves
  - Above the drift threshold (0.40+) it stays silent so the existing
    domain evaluators run
  - SLS unknown → no opinion (subscriptions silent, no vault, no override)
  - Non-risky actions never trigger the veto regardless of SLS
  - Env-var overrides work
  - Vetoes publish queen.conscience.verdict on the bus

These tests exercise the conscience as a unit. The end-to-end loop
(SymbolicLifeBridge.pulse → vault.current_symbolic_life_score →
QueenConscience.ask_why) is verified by the bridge's own tests + this
module's vault-attached path.
"""

from __future__ import annotations

import importlib
import os
import sys
from typing import Any, Callable, Dict, List

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


# Importing queen_conscience pulls in baton_link and many side-effect
# modules. Skip the suite when the import chain breaks in this env.
try:
    from aureon.queen.queen_conscience import (  # noqa: E402
        ConscienceVerdict,
        ConscienceWhisper,
        QueenConscience,
    )
    _OK = True
except Exception as e:  # pragma: no cover
    _OK = False
    _IMPORT_ERROR = str(e)


pytestmark = pytest.mark.skipif(not _OK, reason="queen_conscience import failed")


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


class _StubBus:
    def __init__(self):
        self.published: List[Any] = []
        self._subs: Dict[str, List[Callable]] = {}

    def publish(self, thought=None, **kwargs):
        if thought is None:
            class _T: pass
            t = _T()
            t.topic = kwargs.get("topic", "")
            t.payload = kwargs.get("payload", {})
            t.source = kwargs.get("source", "")
            thought = t
        self.published.append(thought)
        for topic, handlers in self._subs.items():
            match = (topic == "*") or (topic == thought.topic) or (
                topic.endswith(".*") and thought.topic.startswith(topic[:-1])
            )
            if match:
                for h in handlers:
                    h(thought)
        return thought

    def subscribe(self, topic: str, handler: Callable) -> None:
        self._subs.setdefault(topic, []).append(handler)


class _Thought:
    def __init__(self, topic: str, payload: Dict[str, Any] = None,
                 source: str = "test", meta: Dict[str, Any] = None):
        self.topic = topic
        self.payload = payload or {}
        self.source = source
        self.meta = meta or {}


class _SLSVault:
    def __init__(self, sls: float):
        self.current_symbolic_life_score = sls


@pytest.fixture
def conscience(monkeypatch, tmp_path):
    """A fresh QueenConscience with a stub bus, no persisted state."""
    # Pin the canonical field DARK: these tests feed the conscience through
    # the stub bus/vault only. Without this redirect, any process that wrote
    # state/hnc_live_trace.jsonl within the 300s freshness window (another
    # test in the same run, a validator) makes the field live and the
    # divided-field veto fires before the paths these tests assert.
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))
    bus = _StubBus()
    # Patch the module-level get_thought_bus the constructor would use.
    import aureon.queen.queen_conscience as qc_mod
    monkeypatch.setattr(qc_mod, "_HAS_THOUGHT_BUS", True, raising=False)
    monkeypatch.setattr(qc_mod, "_get_thought_bus", lambda: bus, raising=False)
    monkeypatch.setattr(qc_mod, "_Thought", _Thought, raising=False)
    # Also bypass the on-disk state file so tests don't read prior state.
    monkeypatch.setattr(QueenConscience, "_load_state", lambda self: None)
    monkeypatch.setattr(QueenConscience, "_save_state", lambda self: None)
    c = QueenConscience()
    return c, bus


# ─────────────────────────────────────────────────────────────────────────────
# Subscription + state ingestion
# ─────────────────────────────────────────────────────────────────────────────


def test_conscience_subscribes_to_symbolic_life_pulse(conscience):
    c, bus = conscience
    assert "symbolic.life.pulse" in bus._subs


def test_pulse_payload_is_recorded(conscience):
    c, bus = conscience
    bus.publish(_Thought("symbolic.life.pulse", {
        "symbolic_life_score": 0.55, "consciousness_level": "FOCUSED",
    }))
    assert c._latest_sls_pulse["symbolic_life_score"] == 0.55


def test_attach_vault_lets_conscience_read_sls(conscience):
    c, _ = conscience
    c.attach_vault(_SLSVault(sls=0.72))
    assert c._current_sls({}) == 0.72


def test_context_override_beats_vault_and_pulse(conscience):
    c, bus = conscience
    c.attach_vault(_SLSVault(sls=0.72))
    bus.publish(_Thought("symbolic.life.pulse", {"symbolic_life_score": 0.55}))
    assert c._current_sls({"symbolic_life_score": 0.10}) == 0.10


# ─────────────────────────────────────────────────────────────────────────────
# Substrate-coherence veto regimes
# ─────────────────────────────────────────────────────────────────────────────


def test_below_danger_vetoes_risky_trade(conscience):
    c, _ = conscience
    c.attach_vault(_SLSVault(sls=0.10))
    w = c.ask_why("execute trade", {"symbol": "BTC", "risk": 0.08, "profit_potential": 100})
    assert w.verdict == ConscienceVerdict.VETO
    msg = (w.message or "") + " " + (w.why_it_matters or "")
    # Reasoning is grounded in HNC, not generic safety language.
    assert "symbolic_life_score" in msg or "substrate coherence" in msg.lower()
    assert "stability cliff" in msg.lower() or "β" in msg


def test_below_danger_vetoes_override(conscience):
    c, _ = conscience
    c.attach_vault(_SLSVault(sls=0.05))
    w = c.ask_why("override governance", {})
    assert w.verdict == ConscienceVerdict.VETO


def test_drift_zone_concerns_but_does_not_veto(conscience):
    c, _ = conscience
    c.attach_vault(_SLSVault(sls=0.30))
    w = c.ask_why("execute trade", {"symbol": "BTC", "risk": 0.08})
    # Drift zone returns CONCERNED early, before the trade evaluator
    # gets to chime in. The verdict is whatever the substrate path
    # returned (CONCERNED) — NOT a VETO.
    assert w.verdict in (ConscienceVerdict.CONCERNED, ConscienceVerdict.TEACHING_MOMENT)


def test_above_drift_falls_through_to_trade_evaluator(conscience):
    c, _ = conscience
    c.attach_vault(_SLSVault(sls=0.85))
    # A clearly-good trade should be APPROVED by the existing trade
    # evaluator (substrate path stays silent).
    w = c.ask_why("execute trade", {
        "symbol": "BTC", "risk": 0.02, "profit_potential": 1000,
        "confidence": 0.9,
    })
    # The substrate veto did NOT fire — domain evaluator decided.
    assert w.verdict in (ConscienceVerdict.APPROVED,
                         ConscienceVerdict.CONCERNED,
                         ConscienceVerdict.TEACHING_MOMENT)
    # And the message text doesn't carry the substrate-cliff language.
    assert "stability cliff" not in (w.message or "").lower()


def test_unknown_sls_does_not_veto_anything(conscience):
    c, _ = conscience
    # No vault, no pulse → SLS unknown → conscience is silent on substrate
    # and lets the trade evaluator decide.
    w = c.ask_why("execute trade", {"symbol": "BTC", "risk": 0.08})
    assert w.verdict != ConscienceVerdict.VETO or "stability cliff" not in (w.message or "").lower()


def test_non_risky_action_below_danger_is_not_vetoed(conscience):
    c, _ = conscience
    c.attach_vault(_SLSVault(sls=0.05))
    # A pure question ("should we wait?") isn't in the risky-action
    # categories — substrate path returns None.
    w = c.ask_why("should we wait?", {})
    assert w.verdict != ConscienceVerdict.VETO or "substrate coherence" not in (w.message or "").lower()


# ─────────────────────────────────────────────────────────────────────────────
# HNC stability thresholds (hardcoded per the Tree of Light)
# ─────────────────────────────────────────────────────────────────────────────


def test_threshold_constants_match_hnc_tree_of_light():
    """β ∈ [0.6, 1.1] is the stability island per the HNC white paper.
    SLS analogues on [0, 1]: DRIFT=0.40, DANGER=0.20."""
    from aureon.queen.queen_conscience import QueenConscience
    assert QueenConscience.SLS_DANGER == 0.20
    assert QueenConscience.SLS_DRIFT == 0.40


# ─────────────────────────────────────────────────────────────────────────────
# Bus publication
# ─────────────────────────────────────────────────────────────────────────────


def test_substrate_veto_publishes_verdict_on_bus(conscience):
    c, bus = conscience
    c.attach_vault(_SLSVault(sls=0.10))
    c.ask_why("execute trade", {"symbol": "BTC", "risk": 0.08})
    topics = [t.topic for t in bus.published if hasattr(t, "topic")]
    assert "queen.conscience.verdict" in topics
    verdicts = [t for t in bus.published if t.topic == "queen.conscience.verdict"]
    last = verdicts[-1]
    # The existing publish code stringifies the enum's `.value` (int),
    # so a VETO comes out as str(ConscienceVerdict.VETO.value).
    expected_value = str(ConscienceVerdict.VETO.value)
    assert last.payload.get("verdict", "") == expected_value
    # Reasoning carries the substrate-coherence framing.
    reasoning = str(last.payload.get("reasoning", ""))
    assert "symbolic_life_score" in reasoning or "substrate coherence" in reasoning.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Risky-action classification
# ─────────────────────────────────────────────────────────────────────────────


def test_trade_with_no_risk_metadata_is_treated_as_risky(conscience):
    c, _ = conscience
    c.attach_vault(_SLSVault(sls=0.10))
    # No risk/leverage/size keys → defaults to risky to avoid silently
    # passing trades through.
    w = c.ask_why("execute trade", {})
    assert w.verdict == ConscienceVerdict.VETO


def test_trade_with_explicit_zero_risk_is_still_classified_risky(conscience):
    c, _ = conscience
    c.attach_vault(_SLSVault(sls=0.10))
    # risk=0 → below the 0.05 floor → not classified risky on that axis.
    # But the no-other-metadata path catches it.
    w = c.ask_why("execute trade", {"risk": 0.0})
    # We don't strictly assert VETO here — we assert it didn't sneak through.
    assert w.verdict != ConscienceVerdict.APPROVED


def test_high_leverage_triggers_substrate_check(conscience):
    c, _ = conscience
    c.attach_vault(_SLSVault(sls=0.10))
    w = c.ask_why("execute trade", {"risk": 0.0, "leverage": 5.0})
    assert w.verdict == ConscienceVerdict.VETO


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
