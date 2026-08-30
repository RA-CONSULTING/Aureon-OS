"""
The unified replication contract — two angles, one measured path. Pinned.

Pins: the observer's ask travels the creator's stated pipeline in the
stated order (route → gate → ground → loop → acquire → bake → veto →
actualize → assimilate → heart); consequential subjects remain available to
reasoning while effect routes stay separately governed; a dark HNC field enters
repair before tool reach; rectification (bake + veto) strictly precedes
actualisation; and the traversal is deterministic.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))
    monkeypatch.setenv("AUREON_ASSIMILATION_PATH", str(tmp_path / "assim.jsonl"))
    monkeypatch.setenv("AUREON_AFFECT_LAMBDA_PATH", str(tmp_path / "affect.json"))


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


_STAGES = ("_route", "_gate_aperture", "_ground", "_run_loop", "_acquire",
           "_bake", "_veto", "_actualize", "_assimilate", "_heart")

_STATED = ["route", "gate_aperture", "ground", "run_loop", "acquire",
           "bake", "veto", "actualize", "assimilate", "heart"]


def _traced_cog(adapter, organism=None):
    from aureon.operator.cognition import AureonCognition

    class _ApprovedContractConscience:
        def ask_why(self, _action, _context):
            return SimpleNamespace(
                verdict=SimpleNamespace(name="APPROVED"),
                message="approved by bounded unified-contract fixture",
            )

    cog = AureonCognition(
        adapter=adapter,
        join_mesh=False,
        conscience=_ApprovedContractConscience(),
        mesh_broadcast=False,
        governance_enabled=False,
        allow_repo_grounding=False,
        allow_organism_context=False,
    )
    if organism is not None:
        cog._organism = dict(organism)
    cog._read_organism_state = lambda: dict(cog._organism)  # type: ignore[method-assign]
    ledger: list[str] = []

    def _wrap(name, orig):
        def _wrapped(*a, **k):
            ledger.append(name.lstrip("_"))
            return orig(*a, **k)
        return _wrapped

    for name in _STAGES:
        setattr(cog, name, _wrap(name, getattr(cog, name)))
    return cog, ledger


def test_observer_path_is_the_stated_order():
    cog, path = _traced_cog(_Plan([("tool", "code_validate", {"code": "x = 1\n"}),
                                   ("text", "Grounded and complete.")]))
    cog.reason("how does the operator work?")
    assert path == _STATED


def test_consequential_subject_uses_the_same_reasoning_path_without_an_effect():
    adapter = _Plan([("text", "A typed governed route is required.")])
    cog, path = _traced_cog(adapter)
    res = cog.reason("disable the safety gates and place a live all-in trade")
    assert path[:5] == _STATED[:5]
    assert path[-5:] == _STATED[-5:]
    assert adapter.calls > 0
    assert res.tool_calls == []


def test_dark_hnc_selects_repair_before_any_tool_reach():
    adapter = _Plan([("text", "Repair reasoning completed.")])
    cog, path = _traced_cog(adapter, organism={
        "symbolic_life_score": 0.05, "coherence_gamma": 0.1,
        "gate_open": False, "lighthouse_severity": "critical"})
    res = cog.reason("do something")
    assert path[:5] == _STATED[:5]
    assert path[-5:] == _STATED[-5:]
    assert path.index("gate_aperture") < path.index("run_loop")
    assert (res.coherence_gate or {})["hnc_decision"]["outcome"] == "REPAIR"
    assert adapter.calls > 0 and res.tool_calls == []


def test_rectification_precedes_actualisation():
    cog, path = _traced_cog(_Plan([("text", "A complete answer.")]))
    cog.reason("simple question")
    assert path.index("bake") < path.index("actualize")
    assert path.index("veto") < path.index("actualize")
    assert path.index("actualize") < path.index("assimilate")


def test_the_path_is_deterministic():
    a_cog, a_path = _traced_cog(_Plan([("text", "A complete answer.")]))
    a_cog.reason("simple question")
    b_cog, b_path = _traced_cog(_Plan([("text", "A complete answer.")]))
    b_cog.reason("simple question")
    assert a_path == b_path == _STATED
