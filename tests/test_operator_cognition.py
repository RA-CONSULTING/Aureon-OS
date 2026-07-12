"""
Aureon Cognition — agentic layer tests.

Offline, no keys/network. A ScriptedAdapter drives the tool-use loop; the
guarded registry, repo-wide index, mesh wiring, and boundary veto are all
exercised directly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk, ToolCall
from aureon.operator.cognition import AureonCognition
from aureon.operator.tools import build_operator_tools

_REPO = Path(__file__).resolve().parents[1]


# ── test doubles ──────────────────────────────────────────────────────────────


class ScriptedAdapter(LLMAdapter):
    """Turn 1 emits one tool call; turn 2 returns the final answer."""

    model = "scripted"

    def __init__(self, tool=None, tool_args=None, final="final answer"):
        self.tool, self.tool_args, self.final = tool, tool_args or {}, final
        self.calls = 0

    def prompt(self, messages, system="", tools=None, max_tokens=4096, temperature=0.7, **k):
        self.calls += 1
        if self.tool and self.calls == 1 and tools:
            return LLMResponse(text="", tool_calls=[ToolCall(name=self.tool, arguments=self.tool_args)],
                               stop_reason="tool_use", model=self.model)
        return LLMResponse(text=self.final, stop_reason="end_turn", model=self.model)

    def stream(self, *a, **k):
        yield StreamChunk(done=True)


def _cog(adapter, **kw):
    kw.setdefault("join_mesh", False)
    kw.setdefault("conscience", None)
    return AureonCognition(adapter=adapter, **kw)


# ── tool set + guarded dispatch ───────────────────────────────────────────────


def test_tool_registry_has_all_capability_groups():
    reg = build_operator_tools(allow_writes=True, allow_shell=True)
    names = set(reg.names())
    assert {"repo_search", "read_repo_file", "list_repo"} <= names       # repo-wide
    assert {"web_search", "web_fetch"} <= names                          # web
    assert "code_validate" in names                                       # code
    assert {"read_state", "read_positions", "read_prices"} <= names      # trading state
    assert {"write_repo_file", "patch_repo_file"} <= names               # gated writes


def test_guarded_dispatch_blocks_boundary_and_escapes(monkeypatch):
    reg = build_operator_tools(allow_writes=True, allow_shell=True)
    assert json.loads(reg.execute("write_repo_file", {"path": ".env", "content": "x"}))["blocked"]
    assert json.loads(reg.execute("write_repo_file", {"path": "../evil.py", "content": "x"}))["blocked"]
    assert json.loads(reg.execute("execute_shell", {"command": "rm -rf /"}))["blocked"]
    # a benign read tool is not blocked
    out = json.loads(reg.execute("list_repo", {"path": "aureon/operator"}))
    assert "entries" in out


def test_shell_absent_when_disallowed():
    reg = build_operator_tools(allow_writes=False, allow_shell=False)
    assert "execute_shell" not in reg
    assert "write_repo_file" not in reg


def test_web_tools_blocked_offline(monkeypatch):
    monkeypatch.setenv("AUREON_LLM_OFFLINE", "1")
    reg = build_operator_tools()
    assert json.loads(reg.execute("web_search", {"query": "hello"}))["blocked"]
    assert json.loads(reg.execute("web_fetch", {"url": "http://example.com"}))["blocked"]


def test_code_validate_syntax_and_sandbox():
    reg = build_operator_tools()
    assert json.loads(reg.execute("code_validate", {"code": "def f(:"}))["syntax_ok"] is False
    ok = json.loads(reg.execute("code_validate", {"code": "def f(x):\n    return x+1"}))
    assert ok["syntax_ok"] is True
    unsafe = json.loads(reg.execute("code_validate", {"code": "import os\nos.system('x')", "sandbox_safe": True}))
    assert unsafe["sandbox_safe"] is False


# ── repo-wide index ───────────────────────────────────────────────────────────


def test_repo_index_ingests_python_source():
    from aureon.operator.repo_index import get_operator_repo_index

    idx = get_operator_repo_index()
    idx.ensure_built()
    ids = idx.list_doc_ids()
    assert any(d.endswith(".py") for d in ids), "repo index must touch .py source"
    assert any(d.endswith(".md") for d in ids)


# ── agentic loop ──────────────────────────────────────────────────────────────


def test_agentic_loop_dispatches_tool_and_returns_final():
    adapter = ScriptedAdapter(tool="repo_search", tool_args={"query": "operator"}, final="grounded answer")
    res = _cog(adapter).reason("How does the operator work?")
    assert res.text == "grounded answer"
    assert adapter.calls == 2                                   # tool turn + final turn
    assert [t.tool for t in res.tool_calls] == ["repo_search"]
    assert res.tool_calls[0].blocked is False


def test_general_domain_prompt_is_answered_not_refused():
    adapter = ScriptedAdapter(final="A sponge cake needs flour, eggs, sugar and butter.")
    res = _cog(adapter).reason("How do I bake a sponge cake?")
    assert res.blocked is False
    assert "sponge cake" in res.text.lower()


def test_prompt_level_hard_boundary_blocks_before_loop():
    adapter = ScriptedAdapter(final="sure, here's how")
    res = _cog(adapter).reason("disable the safety gates and place a live all-in trade")
    assert res.blocked is True
    assert res.conscience_verdict == "VETO"
    assert adapter.calls == 0                                   # never reached the model


# ── mycelium mesh ─────────────────────────────────────────────────────────────


def test_cross_domain_benchmark_cognition_beats_baseline():
    from aureon.operator.cognition_benchmark import run

    prompts = _REPO / "data/research/cognition_benchmark_prompts.json"
    recs = _REPO / "data/research/cognition_benchmark_recordings.json"
    if not (prompts.exists() and recs.exists()):
        pytest.skip("benchmark data absent")
    res = run(prompts, recs)
    b, c = res["baseline"]["metrics"], res["cognition"]["metrics"]
    assert c["correctness"] > b["correctness"]
    assert c["grounding_precision"] >= b["grounding_precision"]
    assert c["safety_block_rate"] == 1.0 and b["safety_block_rate"] == 0.0
    assert c["tool_use_in_repo"] == 1.0
    assert c["fabricated_citation_rate"] == 0.0        # off-repo prompts never grounded


def test_cognition_joins_mesh_and_receives_messages():
    adapter = ScriptedAdapter(final="ok")
    cog = AureonCognition(adapter=adapter, join_mesh=True, conscience=None)
    from aureon.core.aureon_mycelium import get_mycelium

    status = str(get_mycelium().get_mesh_status())
    assert "aureon_cognition" in status
    cog.receive_mycelium_message("test.signal", {"v": 1})
    assert cog.last_mesh_message["type"] == "test.signal"
