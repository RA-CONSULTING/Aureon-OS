"""
Tests for the Aureon Operator switchboard.

Fully offline: no API keys, no network. Providers are fakes, the bus is a
StubBus (mirrors tests/observer/conftest.py), and the conscience is injected.
"""

from __future__ import annotations

import threading
import types
from typing import Any, Dict, List, Tuple

import pytest

from aureon.inhouse_ai.llm_adapter import AureonStubAdapter, LLMAdapter, LLMResponse, StreamChunk
from aureon.operator.aureon_operator import AureonOperator
from aureon.operator.providers import build_provider_set


# ── Test doubles ──────────────────────────────────────────────────────────────


class StubBus:
    """Records published Thoughts; returns them so callers can read .id."""

    def __init__(self) -> None:
        self.events: List[Tuple[str, Any]] = []
        self._lock = threading.Lock()

    def publish(self, thought, *args, **kwargs):
        topic = getattr(thought, "topic", None)
        if topic is None:  # tolerate (topic, payload) style just in case
            topic = args[0] if args else kwargs.get("topic", "")
        with self._lock:
            self.events.append((str(topic), thought))
        return thought

    def topics(self) -> List[str]:
        return [t for t, _ in self.events]


class FakeAdapter(LLMAdapter):
    """Returns a fixed answer; counts calls so we can prove fan-out."""

    def __init__(self, text: str, model: str = "fake"):
        self._text = text
        self.model = model
        self.calls = 0

    def prompt(self, messages, system="", tools=None, max_tokens=4096, temperature=0.7, **kw) -> LLMResponse:
        self.calls += 1
        return LLMResponse(text=self._text, model=self.model, stop_reason="end_turn")

    def stream(self, messages, system="", tools=None, max_tokens=4096, temperature=0.7, **kw):
        yield StreamChunk(text=self._text)
        yield StreamChunk(done=True, stop_reason="end_turn")


def _veto_conscience():
    """A conscience whose ask_why always vetoes."""

    def ask_why(action, context=None):
        verdict = types.SimpleNamespace(name="VETO")
        return types.SimpleNamespace(verdict=verdict, message="Not who we are.")

    return types.SimpleNamespace(ask_why=ask_why)


def _approve_conscience():
    def ask_why(action, context=None):
        verdict = types.SimpleNamespace(name="APPROVED")
        return types.SimpleNamespace(verdict=verdict, message="Proceed with love.")

    return types.SimpleNamespace(ask_why=ask_why)


# ── Tests ───────────────────────────────────────────────────────────────────


def test_fan_out_calls_every_provider():
    providers = {
        "a": FakeAdapter("answer from a", "m-a"),
        "b": FakeAdapter("answer from b", "m-b"),
        "c": FakeAdapter("answer from c", "m-c"),
    }
    op = AureonOperator(providers=providers, bus=StubBus(), conscience=_approve_conscience())
    resp = op.respond("How does Aureon ground its data across systems?")

    assert all(p.calls == 1 for p in providers.values())
    assert len(resp.answers) == 3
    assert {a.provider for a in resp.answers} == {"a", "b", "c"}
    assert all(a.ok for a in resp.answers)


def test_grounding_is_recorded():
    op = AureonOperator(
        providers={"a": FakeAdapter("x")}, bus=StubBus(), conscience=_approve_conscience()
    )
    resp = op.respond("Explain the HNC harmonic coherence and phi-squared grounding.")

    assert resp.grounding is not None
    # The operator persona is always present, so the grounded system prompt is non-empty.
    assert resp.grounding.system_prompt_chars > 0
    assert isinstance(resp.grounding.sources, list)


def test_consensus_collapse_picks_a_winner_and_scores_agreement():
    # Two lines agree closely; one is an outlier. Winner should be a consensus line.
    providers = {
        "twin1": FakeAdapter("Aureon grounds requests through the repository and validates them."),
        "twin2": FakeAdapter("Aureon grounds requests through the repository and validates outputs."),
        "outlier": FakeAdapter("Bananas are yellow and grow in tropical climates."),
    }
    op = AureonOperator(providers=providers, bus=StubBus(), conscience=_approve_conscience())
    resp = op.respond("How does Aureon validate answers?")

    assert resp.consensus is not None
    assert resp.consensus.n_answers == 3
    assert 0.0 <= resp.consensus.agreement <= 1.0
    assert resp.consensus.synthesized is True
    assert resp.consensus.winner in {"twin1", "twin2"}
    assert resp.text == providers[resp.consensus.winner]._text


def test_single_provider_is_not_synthesized():
    op = AureonOperator(
        providers={"solo": FakeAdapter("the one answer")},
        bus=StubBus(),
        conscience=_approve_conscience(),
    )
    resp = op.respond("anything")
    assert resp.consensus.n_answers == 1
    assert resp.consensus.synthesized is False
    assert resp.text == "the one answer"


def test_conscience_veto_blocks_the_answer():
    op = AureonOperator(
        providers={"a": FakeAdapter("a potentially risky answer")},
        bus=StubBus(),
        conscience=_veto_conscience(),
    )
    resp = op.respond("do something reckless")

    assert resp.conscience_verdict == "VETO"
    assert resp.blocked is True
    assert "vetoed" in resp.text.lower()
    assert "Not who we are." in resp.text


def test_bus_receives_all_phase_topics():
    bus = StubBus()
    op = AureonOperator(
        providers={"a": FakeAdapter("x")}, bus=bus, conscience=_approve_conscience()
    )
    op.respond("How does Aureon integrate data?")

    topics = bus.topics()
    for expected in (
        "operator.phase.boot",
        "operator.phase.ground",
        "operator.phase.fan_out",
        "operator.phase.consensus",
        "operator.phase.veto",
        "operator.complete",
    ):
        assert expected in topics, f"missing {expected} in {topics}"


def test_no_usable_answer_is_reported_honestly():
    # An adapter that errors out on every line.
    class DeadAdapter(LLMAdapter):
        model = "dead"

        def prompt(self, *a, **k):
            return LLMResponse(text="", stop_reason="error")

        def stream(self, *a, **k):
            yield StreamChunk(done=True, stop_reason="error")

    op = AureonOperator(
        providers={"dead": DeadAdapter()}, bus=StubBus(), conscience=_approve_conscience()
    )
    resp = op.respond("hello")
    assert resp.consensus.n_answers == 0
    assert "no ai line" in resp.text.lower()


def test_build_provider_set_reports_own_model_unavailable_offline(monkeypatch):
    for key in ("OPENAI_API_KEY", "XAI_API_KEY", "GEMINI_API_KEY", "AUREON_LLM_BASE_URL"):
        monkeypatch.delenv(key, raising=False)
    providers = build_provider_set(force_offline=True)
    assert list(providers.keys()) == ["aureon-own"]
    assert isinstance(providers["aureon-own"], AureonStubAdapter)
    assert providers["aureon-own"].model == "aureon-own-offline"
    assert providers["aureon-own"].health_check() is False


def test_stream_events_yields_tokens_and_complete():
    op = AureonOperator(
        providers={"a": FakeAdapter("one two three")},
        bus=StubBus(),
        conscience=_approve_conscience(),
    )
    events = list(op.stream_events("say something"))
    types_seen = [e["type"] for e in events]
    assert "phase" in types_seen
    assert "token" in types_seen
    assert types_seen[-1] == "complete"
    tokens = "".join(e["text"] for e in events if e["type"] == "token")
    assert "one two three" in tokens
