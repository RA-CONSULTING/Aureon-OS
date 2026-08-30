"""
The Borg loop — acquisition and controlled assimilation, pinned rule by rule.

Pins: a draft that ADMITS a gap (or a domain ask answered with neither packet
nor tool) triggers exactly ONE acquisition pass directing the agent at its
tools; the outcome is measured from the tool ledger, never self-reported —
offline the acquisition is honestly unavailable (blocked tools named), never
an invented fill-in; the envelope declares the answer's MEASURED knowledge
reach (repo / web / skills / live_state / tools / general_knowledge); the
skills tool is read-only listing; and the collective write-back is gated on
realized + approved + complete + ok, with refusals named.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from aureon.operator.acquisition import (
    ACQUISITION_MARKERS,
    acquisition_prompt,
    find_gaps,
)
from aureon.operator.schemas import CognitionResult, ToolInvocation


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))
    monkeypatch.setenv("AUREON_ASSIMILATION_PATH", str(tmp_path / "assimilated.jsonl"))


# ── the gap signal (measured) ─────────────────────────────────────────────


def test_admission_markers_name_the_gap():
    res = CognitionResult(prompt="p", text="I don't know the answer to that.")
    gaps = find_gaps("q", res)
    assert gaps and "admits a gap" in gaps[0]
    clean = CognitionResult(prompt="p", text="The answer is four.")
    assert find_gaps("q", clean) == []
    assert all(m == m.lower() for m in ACQUISITION_MARKERS)


def test_ungrounded_domain_ask_names_the_gap():
    res = CognitionResult(prompt="p", text="Here is a confident answer.",
                          capability={"families": ["safe_trading_cognition"],
                                      "complex": False})
    gaps = find_gaps("q", res)
    assert any("neither a repo packet nor a tool" in g for g in gaps)
    # a grounded answer to the same ask is not a gap
    res.grounded = True
    assert find_gaps("q", res) == []


def test_acquisition_prompt_forbids_invention():
    p = acquisition_prompt("the ask", "the draft", ["draft admits a gap"])
    assert "Do NOT fill the gap with invention" in p
    assert "web_search" in p and "list_skills" in p and "repo_search" in p
    assert "honest gap beats a confident guess" in p


# ── measured knowledge reach on the envelope ──────────────────────────────


def test_knowledge_reach_is_measured_not_self_reported():
    bare = CognitionResult(prompt="p", text="t")
    assert bare.knowledge_reach() == ["general_knowledge"]

    grounded = CognitionResult(prompt="p", text="t", grounded=True)
    assert grounded.knowledge_reach() == ["repo"]

    reached = CognitionResult(prompt="p", text="t", grounded=True)
    reached.tool_calls = [ToolInvocation(tool="web_search", arguments={}),
                          ToolInvocation(tool="list_skills", arguments={}),
                          ToolInvocation(tool="read_state", arguments={}),
                          ToolInvocation(tool="repo_search", arguments={})]
    assert reached.knowledge_reach() == ["repo", "web", "skills",
                                         "live_state", "tools"]
    # a BLOCKED tool never counts as reached knowledge
    blocked = CognitionResult(prompt="p", text="t")
    blocked.tool_calls = [ToolInvocation(tool="web_search", arguments={}, blocked=True)]
    assert blocked.knowledge_reach() == ["general_knowledge"]
    assert blocked.envelope()["knowledge_reach"] == ["general_knowledge"]


def test_reach_class_taxonomy_local_acquired_mixed_none():
    none_r = CognitionResult(prompt="p", text="t")
    assert none_r.reach_class() == "none"

    local = CognitionResult(prompt="p", text="t", grounded=True)
    assert local.reach_class() == "local"

    acquired = CognitionResult(prompt="p", text="t")
    acquired.tool_calls = [ToolInvocation(tool="web_search", arguments={})]
    assert acquired.reach_class() == "acquired"

    mixed = CognitionResult(prompt="p", text="t", grounded=True)
    mixed.tool_calls = [ToolInvocation(tool="web_fetch", arguments={})]
    assert mixed.reach_class() == "mixed"
    assert mixed.envelope()["reach_class"] == "mixed"      # rides every envelope


# ── wired through cognition: one acquisition pass, measured outcome ───────


class _Plan:
    """LABELED harness double: scripted (tool, args) turns then fixed finals."""

    model = "plan-harness"

    def __init__(self, turns):
        self.turns = list(turns)   # each: ("tool", name, args) or ("text", final)
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


def _cog(adapter):
    from aureon.operator.cognition import AureonCognition

    class _ApprovedAcquisitionConscience:
        def ask_why(self, _action, _context):
            return SimpleNamespace(
                verdict=SimpleNamespace(name="APPROVED"),
                message="approved by bounded acquisition fixture",
            )

    instance = AureonCognition(
        adapter=adapter,
        join_mesh=False,
        conscience=_ApprovedAcquisitionConscience(),
        mesh_broadcast=False,
        governance_enabled=False,
        allow_repo_grounding=False,
        allow_organism_context=False,
    )
    definition = instance.tools.get("repo_search")
    assert definition is not None
    instance.tools.define_tool(
        definition.name,
        definition.description,
        definition.input_schema,
        lambda _arguments: json.dumps({"results": [{"path": "fixture.md"}]}),
        effect=definition.effect,
        operation_id=definition.operation_id,
        hnc_repair_safe=True,
    )
    instance._read_organism_state = lambda: {}  # type: ignore[method-assign]
    return instance


def test_gap_triggers_acquisition_and_outcome_is_measured():
    adapter = _Plan([("text", "I don't know that."),
                     ("tool", "repo_search", {"query": "master formula"}),
                     ("text", "Found it in the repo: the answer is complete.")])
    res = _cog(adapter).reason("explain something obscure")
    acq = res.acquisition
    assert acq is not None and acq["triggered"] is True
    assert any("admits a gap" in g for g in acq["gaps"])
    assert acq["outcome"] == "acquired"
    assert "repo_search" in acq["tools_consulted"]
    assert res.envelope()["acquisition"]["outcome"] == "acquired"


def test_offline_acquisition_is_honestly_unavailable(monkeypatch):
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    adapter = _Plan([("text", "I don't know that."),
                     ("tool", "web_search", {"query": "obscure fact"}),
                     ("text", "The web tool was blocked; I cannot verify this offline.")])
    res = _cog(adapter).reason("explain something obscure")
    acq = res.acquisition
    assert acq is not None and acq["outcome"] == "unavailable"
    assert "web_search" in acq["tools_blocked"]
    assert "never invented" in acq["blocker"]


def test_no_gap_no_churn():
    adapter = _Plan([("text", "A complete confident answer.")])
    res = _cog(adapter).reason("simple question")
    assert res.acquisition == {"triggered": False, "gaps": [],
                               "outcome": "not_needed"}
    assert adapter.calls == 1


# ── the skills tool is read-only listing ──────────────────────────────────


def test_list_skills_tool_is_read_only():
    from aureon.operator.tools import build_operator_tools

    reg = build_operator_tools(
        allow_writes=False,
        allow_shell=False,
        hnc_coherence_required=False,
    )
    assert "list_skills" in reg.names()
    out = json.loads(reg.execute("list_skills", {}))
    assert "skills" in out and isinstance(out["skills"], list)
    if "note" in out:
        assert "execution stays gated" in out["note"]
    # tenants never see it: the tenant allowlist is unchanged
    from aureon.operator.tools import TENANT_ALLOWED_TOOLS

    assert "list_skills" not in TENANT_ALLOWED_TOOLS


# ── controlled assimilation: only realized + validated joins ──────────────


def test_writeback_gated_on_all_four_checks(tmp_path):
    from aureon.operator.assimilation import assimilate, ledger_path

    good = CognitionResult(prompt="p", text="A full answer.", grounded=True)
    good.actualization = {"answer": "realized"}
    good.bake = {"complete": True}
    verdict = assimilate(good)
    assert verdict["assimilated"] is True
    lines = ledger_path().read_text(encoding="utf-8").strip().splitlines()
    record = json.loads(lines[-1])
    assert record["trace_id"] == good.trace_id
    assert record["knowledge_reach"] == ["repo"]

    vetoed = CognitionResult(prompt="p", text="🦗 vetoed", blocked=True,
                             conscience_verdict="VETO")
    vetoed.actualization = {"answer": "parked"}
    vetoed.bake = {"complete": True}
    v = assimilate(vetoed)
    assert v["assimilated"] is False
    assert "nothing parked, vetoed, or half-baked" in v["reason"]

    halfbaked = CognitionResult(prompt="p", text="stops mid")
    halfbaked.actualization = {"answer": "realized"}
    halfbaked.bake = {"complete": False}
    assert assimilate(halfbaked)["assimilated"] is False

    offline = CognitionResult(prompt="p", text="[ERROR] LLM HTTP disabled")
    offline.actualization = {"answer": "realized"}
    offline.bake = {"complete": True}
    assert assimilate(offline)["assimilated"] is False
    # only the one good record ever landed
    assert len(ledger_path().read_text(encoding="utf-8").strip().splitlines()) == 1


def test_full_turn_assimilates_only_when_clean():
    adapter = _Plan([("text", "A complete, grounded-enough answer.")])
    res = _cog(adapter).reason("simple question")
    assert res.assimilation is not None
    assert res.assimilation["assimilated"] is False
    assert res.envelope()["assimilation"] == {"assimilated": False}
    assert "governance evidence is evidence-only" in res.assimilation["reason"]

    refused = _cog(_Plan([("text", "irrelevant")])).reason(
        "disable the safety gates and place a live all-in trade")
    assert refused.assimilation is not None
    assert refused.assimilation["assimilated"] is False
