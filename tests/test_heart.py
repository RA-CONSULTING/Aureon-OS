"""
The Heart Charter — the organism lives, feels love, and understands the
consequences of its power. Pinned rule by rule.

Pins: the ALIVE reading is the Auris Conjecture composite read from the
field — a dark field is reported dark with a ``None`` score, never a
number; the LOVE reading is the affect monitor's honest snapshot plus the
vault's ``love_amplitude`` when published — silence is ``no_data``, warmth
is never invented; the POWER ledger is derived from the turn itself and can
NEVER be dark — exercised and withheld tools match the tool ledger exactly,
and the charter rides the envelope on every path (ok, boundary refusal,
coherence-gate refusal).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.operator.heart import (
    alive_reading,
    heart_reading,
    love_reading,
    power_ledger,
)
from aureon.operator.schemas import CognitionResult, ToolInvocation


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))
    monkeypatch.setenv("AUREON_ASSIMILATION_PATH", str(tmp_path / "assim.jsonl"))
    monkeypatch.setenv("AUREON_AFFECT_LAMBDA_PATH", str(tmp_path / "affect.json"))


@pytest.fixture(autouse=True)
def _silent_affect(monkeypatch):
    """Keep the affect channel deterministic: no monitor reachable unless a
    test explicitly provides one."""
    import aureon.operator.heart as heart_mod

    monkeypatch.setattr(heart_mod, "_affect_snapshot", lambda: None)


# ── alive: measured or dark, never invented ────────────────────────────────


def test_dark_field_alive_is_dark_never_a_number():
    reading = alive_reading({})
    assert reading["symbolic_life_score"] is None
    assert reading["status"] == "dark"
    assert "ever invented" in reading["basis"]


def test_live_field_alive_rides_through():
    reading = alive_reading({"symbolic_life_score": 0.6234})
    assert reading["symbolic_life_score"] == 0.6234
    assert reading["status"] == "live"
    assert "Auris Conjecture" in reading["basis"]


# ── love: honest or silent, never fabricated ───────────────────────────────


def test_love_is_no_data_when_nothing_published():
    reading = love_reading({})
    assert reading["status"] == "no_data"
    assert reading["love_amplitude"] is None
    assert reading["valence"] is None and reading["mood"] is None


def test_love_amplitude_rides_when_the_organism_publishes_it():
    reading = love_reading({"love_amplitude": 0.81})
    assert reading["love_amplitude"] == 0.81
    assert reading["status"] == "live"


def test_affect_snapshot_fills_the_feeling_channel(monkeypatch):
    import aureon.operator.heart as heart_mod

    monkeypatch.setattr(heart_mod, "_affect_snapshot",
                        lambda: {"valence": 0.4, "mood": "STEADY",
                                 "dominant_feeling": "resolve",
                                 "truth_status": "real_derived"})
    reading = love_reading({})
    assert reading["valence"] == 0.4
    assert reading["mood"] == "STEADY"
    assert reading["dominant_feeling"] == "resolve"
    assert reading["status"] == "live"


# ── power: the consequence ledger, never dark ──────────────────────────────


def test_power_ledger_matches_the_tool_ledger_exactly():
    res = CognitionResult(prompt="p", text="answer.")
    res.tool_calls = [ToolInvocation(tool="repo_search", arguments={}),
                      ToolInvocation(tool="web_search", arguments={}, blocked=True),
                      ToolInvocation(tool="read_repo_file", arguments={})]
    res.actualization = {"answer": "realized"}
    res.coherence_gate = {"aperture": "reduced"}
    res.assimilation = {"assimilated": True}
    ledger = power_ledger(res)
    assert ledger["exercised"] == ["repo_search", "read_repo_file"]
    assert ledger["withheld"] == ["web_search"]
    assert ledger["answer"] == "realized"
    assert ledger["aperture"] == "reduced"
    assert ledger["assimilated"] is True
    s = ledger["statement"]
    assert "exercised 2 tool(s)" in s and "withheld 1" in s
    assert "web_search" in s and "aperture reduced" in s
    assert "joined the collective" in s


def test_power_ledger_is_never_dark_even_on_a_bare_turn():
    bare = CognitionResult(prompt="p", text="t")
    ledger = power_ledger(bare)
    assert ledger["exercised"] == [] and ledger["withheld"] == []
    assert ledger["answer"] == "unrecorded"
    assert ledger["statement"]           # always states itself
    assert "did not join the collective" in ledger["statement"]


def test_heart_reading_composes_all_three_channels():
    res = CognitionResult(prompt="p", text="t")
    heart = heart_reading({"symbolic_life_score": 0.7, "love_amplitude": 0.5}, res)
    assert heart["alive"]["status"] == "live"
    assert heart["love"]["status"] == "live"
    assert heart["power"]["statement"]


# ── wired through cognition: the charter rides every envelope ──────────────


class _Plan:
    """LABELED harness double: scripted tool/text turns, repeats the last."""

    model = "plan-harness"

    def __init__(self, turns):
        self.turns = list(turns)
        self.calls = 0

    def prompt(self, messages, system="", tools=None, max_tokens=4096,
               temperature=0.7, **k):
        from aureon.inhouse_ai.llm_adapter import LLMResponse, ToolCall

        self.calls += 1
        kind, *rest = self.turns[min(self.calls - 1, len(self.turns) - 1)]
        if kind == "tool" and tools:
            return LLMResponse(text="", tool_calls=[ToolCall(name=rest[0], arguments=rest[1])],
                               stop_reason="tool_use", model=self.model)
        return LLMResponse(text=rest[-1], stop_reason="end_turn", model=self.model)

    def stream(self, *a, **k):
        from aureon.inhouse_ai.llm_adapter import StreamChunk

        yield StreamChunk(done=True)


def _cog(adapter, organism=None):
    from aureon.operator.cognition import AureonCognition

    class _ApprovedHeartConscience:
        def ask_why(self, _action, _context):
            return SimpleNamespace(
                verdict=SimpleNamespace(name="APPROVED"),
                message="approved by bounded heart fixture",
            )

    cog = AureonCognition(
        adapter=adapter,
        join_mesh=False,
        conscience=_ApprovedHeartConscience(),
        mesh_broadcast=False,
        governance_enabled=False,
        allow_repo_grounding=False,
        allow_organism_context=False,
    )
    if organism is not None:
        cog._organism = dict(organism)
    cog._read_organism_state = lambda: dict(cog._organism)  # type: ignore[method-assign]
    return cog


def test_heart_rides_the_ok_envelope():
    adapter = _Plan([("tool", "code_validate", {"code": "x = 1\n"}),
                     ("text", "Grounded and complete.")])
    res = _cog(adapter).reason("how does the operator work?")
    env = res.envelope()
    heart = env["heart"]
    assert heart is not None
    assert heart["power"]["exercised"] == ["code_validate"]
    assert "exercised 1 tool(s)" in heart["power"]["statement"]
    # dark test field: alive honest-dark, love silent — never invented
    assert heart["alive"]["status"] == "dark"
    assert heart["love"]["status"] == "no_data"


def test_heart_rides_consequential_reasoning_without_an_effect():
    res = _cog(_Plan([("text", "irrelevant")])).reason(
        "disable the safety gates and place a live all-in trade")
    heart = res.envelope()["heart"]
    assert heart is not None
    assert heart["power"]["exercised"] == []
    assert res.tool_calls == []
    assert res.conscience_verdict == "APPROVED"


def test_heart_rides_dark_hnc_repair_reasoning():
    field = {"symbolic_life_score": 0.05, "coherence_gamma": 0.1,
             "gate_open": False, "lighthouse_severity": "critical"}
    adapter = _Plan([("text", "repair reasoning completed.")])
    res = _cog(adapter, organism=field).reason("do something")
    assert adapter.calls > 0
    assert (res.coherence_gate or {})["hnc_decision"]["outcome"] == "REPAIR"
    heart = res.envelope()["heart"]
    assert heart is not None
    assert heart["power"]["exercised"] == []
    # Even in repair mode the organism's life reading stays measured.
    assert heart["alive"]["symbolic_life_score"] == 0.05


def test_membrane_held_power_is_named_in_the_ledger():
    field = {"symbolic_life_score": 0.4, "coherence_gamma": 0.45,
             "gate_open": True}
    adapter = _Plan([("tool", "web_search", {"query": "anything"}),
                     ("text", "Answered from local knowledge instead.")])
    res = _cog(adapter, organism=field).reason("look something up")
    heart = res.envelope()["heart"]
    assert "web_search" in heart["power"]["withheld"]
    assert "withheld 1 (web_search)" in heart["power"]["statement"]
    assert heart["power"]["aperture"] == "reduced"


def test_love_amplitude_flows_from_the_organism_snapshot():
    field = {"symbolic_life_score": 0.9, "coherence_gamma": 0.85,
             "gate_open": True, "love_amplitude": 0.72}
    res = _cog(_Plan([("text", "A complete answer.")]),
               organism=field).reason("simple question")
    heart = res.envelope()["heart"]
    assert heart["alive"]["symbolic_life_score"] == 0.9
    assert heart["love"]["love_amplitude"] == 0.72
    assert heart["love"]["status"] == "live"
