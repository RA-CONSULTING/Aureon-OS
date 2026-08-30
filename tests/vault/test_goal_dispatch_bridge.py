#!/usr/bin/env python3
"""
Tests for GoalDispatchBridge — the wiring that routes goal.submit.request
through the Queen's conscience and (if approved) into the existing
GoalExecutionEngine.

What's being proved:
  - Bridge subscribes to goal.submit.request when enabled
  - Bridge does NOT subscribe when AUREON_GOAL_ENGINE_ENABLED=0
  - Happy path: SLS ≥ drift → conscience approves → engine called
  - VETO path: SLS < danger → conscience vetoes → goal.abandoned
    published with the HNC substrate-coherence reason; engine NOT called
  - No engine configured: goal.dispatch.unavailable carries no-data
    provenance and cannot acknowledge the TemporalCausalityLaw
  - Engine raises → goal.abandoned with engine error as reason
  - Idempotent per goal_id: second request for same id is ignored
  - Empty text → goal.abandoned
  - Conscience errors don't break the dispatch (soft-fail, engine still
    called)
  - Context carries persona + SLS + risk metadata through to conscience
"""

from __future__ import annotations

import os
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.vault.voice.goal_dispatch_bridge import (  # noqa: E402
    GoalDispatchBridge,
    get_goal_dispatch_bridge,
    reset_goal_dispatch_bridge,
)
from aureon.vault.voice.temporal_causality import (  # noqa: E402
    GoalState,
    TemporalCausalityLaw,
)


# ─────────────────────────────────────────────────────────────────────────────
# Doubles
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

    def subscribe(self, topic, handler):
        self._subs.setdefault(topic, []).append(handler)


class _Thought:
    def __init__(self, topic, payload, source="test"):
        self.topic = topic
        self.payload = payload
        self.source = source


class _StubConscience:
    """Lightweight conscience that returns a canned verdict so we don't
    drag the full QueenConscience import chain into every test."""

    VERDICTS = ("APPROVED", "CONCERNED", "VETO", "TEACHING_MOMENT")

    class _Verdict:
        def __init__(self, name: str):
            self.name = name

    class _Whisper:
        def __init__(self, name, message="", why=""):
            self.verdict = _StubConscience._Verdict(name)
            self.message = message
            self.why_it_matters = why

    def __init__(self, verdict: str = "APPROVED", message: str = "",
                 raises: bool = False):
        assert verdict in self.VERDICTS
        self.verdict = verdict
        self.message = message
        self.raises = raises
        self.calls: List[Dict[str, Any]] = []

    def ask_why(self, action: str, context: Dict[str, Any] = None):
        if self.raises:
            raise RuntimeError("conscience exploded")
        self.calls.append({"action": action, "context": dict(context or {})})
        return _StubConscience._Whisper(
            self.verdict,
            message=self.message or f"stub verdict: {self.verdict}",
            why="stub context",
        )


class _StubGoalEngine:
    """Engine double. submit_goal records the call; can be made to raise."""

    def __init__(self, raises: bool = False):
        self.raises = raises
        self.submissions: List[str] = []
        self._lock = threading.Lock()

    def submit_goal(self, text: str):
        if self.raises:
            raise RuntimeError("engine boom")
        with self._lock:
            self.submissions.append(text)
        return {"goal_id": f"engine-{len(self.submissions)}", "text": text}


class _SLSVault:
    def __init__(self, sls: Optional[float] = None):
        if sls is not None:
            self.current_symbolic_life_score = sls


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clear_goal_claims():
    """GoalClaims is a module-level singleton (by design — coordinates
    GoalDispatchBridge with SkillExecutorBridge across the process).
    Tests leak claims across runs unless reset. Autouse so it fires for
    every test in this file."""
    try:
        from aureon.vault.voice._goal_claims import GoalClaims
        GoalClaims.clear()
    except Exception:
        pass
    yield
    try:
        from aureon.vault.voice._goal_claims import GoalClaims
        GoalClaims.clear()
    except Exception:
        pass


def _bridge(**overrides) -> Any:
    bus = overrides.pop("bus", None) or _StubBus()
    conscience = overrides.pop("conscience", None)
    engine = overrides.pop("engine", None)
    vault = overrides.pop("vault", None)
    b = GoalDispatchBridge(
        thought_bus=bus, conscience=conscience, goal_engine=engine,
        vault=vault,
    )
    b._run_in_thread = False  # deterministic tests
    b.start()
    return b, bus, conscience, engine


def _submit(bus, goal_id="g1", text="draft a research note", persona="engineer",
            urgency=0.7, parameters=None):
    bus.publish(_Thought("goal.submit.request", {
        "goal_id": goal_id, "text": text,
        "proposed_by_persona": persona, "urgency": urgency,
        "parameters": dict(parameters or {}),
    }))


# ─────────────────────────────────────────────────────────────────────────────
# Subscription
# ─────────────────────────────────────────────────────────────────────────────


def test_bridge_subscribes():
    b, bus, _, _ = _bridge()
    assert "goal.submit.request" in bus._subs


# ─────────────────────────────────────────────────────────────────────────────
# Happy path: conscience approves → engine called
# ─────────────────────────────────────────────────────────────────────────────


def test_approved_goal_is_submitted_to_engine():
    conscience = _StubConscience(verdict="APPROVED")
    engine = _StubGoalEngine()
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine)
    _submit(bus, text="compose a paper")
    assert engine.submissions == ["compose a paper"]
    assert conscience.calls[0]["action"] == "compose a paper"


def test_concerned_goal_is_also_submitted():
    """CONCERNED is advisory — the engine still runs."""
    conscience = _StubConscience(verdict="CONCERNED")
    engine = _StubGoalEngine()
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine)
    _submit(bus, text="do the thing")
    assert engine.submissions == ["do the thing"]


def test_no_conscience_still_submits():
    """If no conscience is attached, the bridge doesn't block dispatch."""
    engine = _StubGoalEngine()
    b, bus, _, _ = _bridge(conscience=None, engine=engine)
    _submit(bus, text="run the thing")
    assert engine.submissions == ["run the thing"]


# ─────────────────────────────────────────────────────────────────────────────
# VETO path
# ─────────────────────────────────────────────────────────────────────────────


def test_veto_blocks_engine_and_publishes_abandoned():
    conscience = _StubConscience(
        verdict="VETO",
        message="Substrate coherence is collapsing — below the stability cliff",
    )
    engine = _StubGoalEngine()
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine)
    bus.published.clear()
    _submit(bus, text="execute a risky trade")
    assert engine.submissions == []
    abandoned = [t for t in bus.published if t.topic == "goal.abandoned"]
    assert len(abandoned) == 1
    reason = abandoned[0].payload["reason"]
    # Reason carries the conscience's HNC-grounded message
    assert ("stability cliff" in reason.lower()
            or "substrate coherence" in reason.lower())


def test_veto_updates_stats():
    conscience = _StubConscience(verdict="VETO", message="no")
    engine = _StubGoalEngine()
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine)
    _submit(bus, text="risky thing")
    s = b.stats()
    assert s["vetoed"] == 1
    assert s["abandoned"] == 1


def test_no_engine_publishes_unavailable_without_temporal_acknowledgement():
    """An unavailable dispatch remains PROPOSED; it is not an engine receipt."""
    conscience = _StubConscience(verdict="APPROVED")
    bus = _StubBus()
    law = TemporalCausalityLaw(thought_bus=bus)
    law.start()
    b, _, _, _ = _bridge(bus=bus, conscience=conscience, engine=None)
    bus.published.clear()
    _submit(bus, text="unclaimed goal")
    unavailable = [t for t in bus.published if t.topic == "goal.dispatch.unavailable"]
    submitted = [t for t in bus.published if t.topic == "goal.submitted"]
    completed = [t for t in bus.published if t.topic == "goal.completed"]
    assert len(unavailable) == 1
    assert unavailable[0].payload == {
        "goal_id": "g1",
        "text": "unclaimed goal",
        "source": "goal_dispatch_bridge",
        "source_id": "goal_dispatch_bridge",
        "request_id": "g1",
        "receipt_id": None,
        "has_engine": False,
        "received_at": pytest.approx(unavailable[0].payload["received_at"]),
        "source_timestamp": None,
        "truth_status": "no_data",
        "generated_values": False,
        "action_enabled": False,
        "accounting_enabled": False,
        "learning_enabled": False,
    }
    assert law.get("g1").state == GoalState.PROPOSED
    assert submitted == []
    assert len(completed) == 0


# ─────────────────────────────────────────────────────────────────────────────
# Engine errors
# ─────────────────────────────────────────────────────────────────────────────


def test_engine_error_produces_goal_abandoned():
    conscience = _StubConscience(verdict="APPROVED")
    engine = _StubGoalEngine(raises=True)
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine)
    _submit(bus, text="will explode")
    abandoned = [t for t in bus.published if t.topic == "goal.abandoned"]
    assert len(abandoned) == 1
    assert "engine error" in abandoned[0].payload["reason"]
    assert "boom" in abandoned[0].payload["reason"]


# ─────────────────────────────────────────────────────────────────────────────
# Idempotency + input validation
# ─────────────────────────────────────────────────────────────────────────────


def test_duplicate_goal_id_dispatches_once():
    conscience = _StubConscience(verdict="APPROVED")
    engine = _StubGoalEngine()
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine)
    _submit(bus, goal_id="dup1", text="only once")
    _submit(bus, goal_id="dup1", text="only once")
    assert engine.submissions == ["only once"]


def test_empty_text_is_abandoned():
    conscience = _StubConscience(verdict="APPROVED")
    engine = _StubGoalEngine()
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine)
    bus.published.clear()
    bus.publish(_Thought("goal.submit.request",
                          {"goal_id": "empty", "text": "  "}))
    assert engine.submissions == []
    abandoned = [t for t in bus.published if t.topic == "goal.abandoned"]
    assert len(abandoned) == 1
    assert "no goal text" in abandoned[0].payload["reason"]


# ─────────────────────────────────────────────────────────────────────────────
# Soft-fail paths
# ─────────────────────────────────────────────────────────────────────────────


def test_conscience_exception_does_not_block_dispatch():
    """A broken conscience is advisory; we still dispatch. This keeps
    the lighthouse unbroken if the conscience module is wedged."""
    conscience = _StubConscience(verdict="VETO", raises=True)
    engine = _StubGoalEngine()
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine)
    _submit(bus, text="still runs")
    assert engine.submissions == ["still runs"]


# ─────────────────────────────────────────────────────────────────────────────
# Context propagation into the conscience
# ─────────────────────────────────────────────────────────────────────────────


def test_context_includes_sls_from_vault():
    conscience = _StubConscience(verdict="APPROVED")
    engine = _StubGoalEngine()
    vault = _SLSVault(sls=0.73)
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine, vault=vault)
    _submit(bus, text="something")
    ctx = conscience.calls[0]["context"]
    assert ctx["symbolic_life_score"] == pytest.approx(0.73)


def test_context_carries_persona_and_parameters():
    conscience = _StubConscience(verdict="APPROVED")
    engine = _StubGoalEngine()
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine)
    _submit(bus, text="trade BTC", persona="engineer",
            parameters={"risk": 0.08, "leverage": 3.0, "symbol": "BTC"})
    ctx = conscience.calls[0]["context"]
    assert ctx["persona"] == "engineer"
    assert ctx["risk"] == 0.08
    assert ctx["leverage"] == 3.0
    assert ctx["symbol"] == "BTC"


def test_no_sls_means_no_sls_in_context():
    conscience = _StubConscience(verdict="APPROVED")
    engine = _StubGoalEngine()
    b, bus, _, _ = _bridge(conscience=conscience, engine=engine)
    _submit(bus, text="zero-context thing")
    ctx = conscience.calls[0]["context"]
    assert "symbolic_life_score" not in ctx


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end with real QueenConscience + TemporalCausalityLaw
# ─────────────────────────────────────────────────────────────────────────────


def _real_conscience(monkeypatch, bus, vault_sls: Optional[float] = None):
    """Build a real QueenConscience wired to the provided bus."""
    try:
        import aureon.queen.queen_conscience as qc_mod
        from aureon.queen.queen_conscience import QueenConscience
    except Exception:
        pytest.skip("queen_conscience not importable")
    monkeypatch.setattr(qc_mod, "_HAS_THOUGHT_BUS", True, raising=False)
    monkeypatch.setattr(qc_mod, "_get_thought_bus", lambda: bus, raising=False)

    class _Thought2:
        def __init__(self, topic, payload=None, source="test", meta=None):
            self.topic = topic; self.payload = payload or {}
            self.source = source; self.meta = meta or {}
    monkeypatch.setattr(qc_mod, "_Thought", _Thought2, raising=False)
    monkeypatch.setattr(QueenConscience, "_load_state", lambda self: None)
    monkeypatch.setattr(QueenConscience, "_save_state", lambda self: None)

    c = QueenConscience()
    if vault_sls is not None:
        c.attach_vault(_SLSVault(sls=vault_sls))
    return c


def test_end_to_end_low_sls_vetoes_through_real_conscience(monkeypatch):
    bus = _StubBus()
    conscience = _real_conscience(monkeypatch, bus, vault_sls=0.05)
    engine = _StubGoalEngine()
    vault = _SLSVault(sls=0.05)
    b = GoalDispatchBridge(thought_bus=bus, conscience=conscience,
                           goal_engine=engine, vault=vault)
    b._run_in_thread = False
    b.start()
    bus.published.clear()
    _submit(bus, goal_id="e2e-veto", text="execute risky trade",
            parameters={"risk": 0.08})
    assert engine.submissions == []
    abandoned = [t for t in bus.published if t.topic == "goal.abandoned"]
    assert len(abandoned) == 1
    reason = abandoned[0].payload["reason"]
    assert ("stability cliff" in reason.lower()
            or "substrate coherence" in reason.lower())


def test_end_to_end_high_sls_dispatches_through_real_conscience(monkeypatch):
    bus = _StubBus()
    conscience = _real_conscience(monkeypatch, bus, vault_sls=0.85)
    engine = _StubGoalEngine()
    vault = _SLSVault(sls=0.85)
    b = GoalDispatchBridge(thought_bus=bus, conscience=conscience,
                           goal_engine=engine, vault=vault)
    b._run_in_thread = False
    b.start()
    _submit(bus, goal_id="e2e-ok", text="write research note",
            parameters={"risk": 0.01})
    # Should reach the engine (SLS=0.85 is well above drift 0.40).
    assert engine.submissions == ["write research note"]


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


def test_singleton():
    reset_goal_dispatch_bridge()
    a = get_goal_dispatch_bridge()
    b = get_goal_dispatch_bridge()
    assert a is b
    reset_goal_dispatch_bridge()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
