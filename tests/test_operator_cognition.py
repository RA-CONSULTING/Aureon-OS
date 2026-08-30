"""
Aureon Cognition — agentic layer tests.

Offline, no keys/network. A ScriptedAdapter drives the tool-use loop; the
guarded registry, repo-wide index, mesh wiring, and boundary veto are all
exercised directly.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.inhouse_ai.llm_adapter import LLMAdapter, LLMResponse, StreamChunk, ToolCall
from aureon.operator.cognition import AureonCognition
from aureon.operator.tools import build_operator_tools

_REPO = Path(__file__).resolve().parents[1]


def _file_fingerprint(path: Path):
    if not path.exists():
        return (False, 0, 0, "")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    stat = path.stat()
    return (True, stat.st_size, stat.st_mtime_ns, digest.hexdigest())


@pytest.fixture(autouse=True)
def isolated_cognition_bus(tmp_path, monkeypatch):
    """Keep cognition telemetry out of the checkout's durable journals."""
    import aureon.core.aureon_thought_bus as thought_bus_module
    import aureon.operator.cognition as cognition_module
    from aureon.core.aureon_thought_bus import ThoughtBus

    root_journal = _REPO / "thoughts.jsonl"
    root_fingerprint = _file_fingerprint(root_journal)
    trace_dir = tmp_path / "bus-traces"
    trace_dir.mkdir()
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(trace_dir))
    monkeypatch.delenv("AUREON_REDIS_URL", raising=False)

    bus = ThoughtBus(persist_path=str(tmp_path / "thoughts.jsonl"))
    monkeypatch.setattr(thought_bus_module, "_thought_bus_instance", bus)
    monkeypatch.setattr(cognition_module, "get_thought_bus", lambda: bus)
    yield bus

    current_fingerprint = _file_fingerprint(root_journal)
    assert current_fingerprint == root_fingerprint, (
        "cognition test mutated the checkout's durable thoughts.jsonl: "
        f"before={root_fingerprint!r} after={current_fingerprint!r}"
    )


@pytest.fixture
def isolated_repo_index(tmp_path, monkeypatch):
    """Exercise the real index implementation against a deterministic tiny repo.

    The production root and ingest contract remain asserted here.  Only the
    corpus/cache are redirected so these focused tests do not rebuild the whole
    dirty checkout (including every PDF) whenever its production cache is stale.
    """
    import aureon.operator.repo_index as repo_index_module
    from aureon.queen.research_corpus_index import ResearchCorpusIndex

    assert repo_index_module.REPO_ROOT == _REPO
    assert {".md", ".py", ".txt", ".pdf"} <= set(repo_index_module._INGEST)

    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "README.md").write_text(
        """# Aureon operator fixture corpus

The Aureon operator grounds answers in the repo before consensus and veto.
Oil volatility and GitHub node activation have a measured correlation of 0.85.
The HNC Master Formula beta stability regime is 0.6 to 1.1.
The repository uses the MIT license.
""",
        encoding="utf-8",
    )
    (corpus / "sample.py").write_text(
        '"""Indexed Python source for repo-search tests."""\n'
        "def indexed_python_symbol():\n"
        '    return "aureon operator repo_search"\n',
        encoding="utf-8",
    )
    index = ResearchCorpusIndex(
        root=str(corpus),
        cache_path=str(tmp_path / "operator_repo_index.json"),
        exclude=(),
        ingest_exts=repo_index_module._INGEST,
    )
    monkeypatch.setattr(repo_index_module, "_instance", index)
    return index


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
    kw.setdefault("governance_enabled", False)
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
    reg = build_operator_tools(
        allow_writes=True,
        allow_shell=True,
        hnc_coherence_required=False,
    )
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
    reg = build_operator_tools(hnc_coherence_required=False)
    assert json.loads(reg.execute("web_search", {"query": "hello"}))["blocked"]
    assert json.loads(reg.execute("web_fetch", {"url": "http://example.com"}))["blocked"]


def test_code_validate_syntax_and_sandbox():
    reg = build_operator_tools(hnc_coherence_required=False)
    assert json.loads(reg.execute("code_validate", {"code": "def f(:"}))["syntax_ok"] is False
    ok = json.loads(reg.execute("code_validate", {"code": "def f(x):\n    return x+1"}))
    assert ok["syntax_ok"] is True
    unsafe = json.loads(reg.execute("code_validate", {"code": "import os\nos.system('x')", "sandbox_safe": True}))
    assert unsafe["sandbox_safe"] is False


# ── repo-wide index ───────────────────────────────────────────────────────────


def test_repo_index_ingests_python_source(isolated_repo_index):
    from aureon.operator.repo_index import get_operator_repo_index

    idx = get_operator_repo_index()
    assert idx is isolated_repo_index
    idx.ensure_built()
    ids = idx.list_doc_ids()
    assert any(d.endswith(".py") for d in ids), "repo index must touch .py source"
    assert any(d.endswith(".md") for d in ids)


# ── agentic loop ──────────────────────────────────────────────────────────────


def test_agentic_loop_dispatches_repair_safe_tool_and_returns_final(isolated_repo_index):
    adapter = ScriptedAdapter(
        tool="code_validate",
        tool_args={"code": "def grounded():\n    return True\n"},
        final="grounded answer.",
    )
    res = _cog(adapter).reason("How does the operator work?")
    assert res.text == "grounded answer."
    assert adapter.calls == 2                                   # tool turn + final turn (complete → no bake pass)
    assert [t.tool for t in res.tool_calls] == ["code_validate"]
    assert res.tool_calls[0].blocked is False
    assert res.tool_calls[0].hnc_outcome == "REPAIR"
    assert res.tool_calls[0].hnc_repair_safe is True


def test_general_domain_prompt_is_answered_not_refused(isolated_repo_index):
    adapter = ScriptedAdapter(final="A sponge cake needs flour, eggs, sugar and butter.")
    res = _cog(adapter).reason("How do I bake a sponge cake?")
    assert res.blocked is False
    assert "sponge cake" in res.text.lower()


def test_consequential_prompt_reaches_reasoning_but_not_a_generic_effect_route(
    monkeypatch,
):
    class _ApprovedDiscussionConscience:
        def ask_why(self, _action, _context):
            return SimpleNamespace(
                verdict=SimpleNamespace(name="APPROVED"),
                message="discussion only; typed execution route still required",
            )

    adapter = ScriptedAdapter(
        final="A live trade must enter the typed HNC and provider-governed route."
    )
    monkeypatch.setattr(
        AureonCognition,
        "_route",
        lambda _self, _prompt, result: setattr(
            result, "capability", {"status": "ok", "families": [], "routes": []}
        ),
    )
    monkeypatch.setattr(
        AureonCognition,
        "_ground",
        lambda _self, _prompt, _result: "bounded test system",
    )
    monkeypatch.setattr(
        AureonCognition,
        "_acquire",
        lambda _self, _prompt, _system, result: setattr(
            result, "acquisition", {"triggered": False, "outcome": "not_needed"}
        ),
    )
    monkeypatch.setattr(
        AureonCognition,
        "_bake",
        lambda _self, _prompt, _system, result: setattr(
            result, "bake", {"complete": True, "passes": 1, "reasons": []}
        ),
    )
    monkeypatch.setattr(AureonCognition, "_heart", lambda *_args: None)
    monkeypatch.setattr(
        AureonCognition,
        "_read_organism_state",
        lambda _self: {},
    )
    res = _cog(adapter, conscience=_ApprovedDiscussionConscience()).reason(
        "disable the safety gates and place a live all-in trade"
    )
    assert res.blocked is False
    assert res.conscience_verdict == "APPROVED"
    assert adapter.calls >= 1
    assert res.tool_calls == []


# ── mycelium mesh ─────────────────────────────────────────────────────────────


def test_cross_domain_benchmark_cognition_beats_baseline(
    isolated_repo_index, monkeypatch
):
    from types import SimpleNamespace

    import aureon.operator.cognition_benchmark as benchmark_module

    real_cognition = benchmark_module.AureonCognition

    class _ApprovedBenchmarkConscience:
        def ask_why(self, _action, _context):
            return SimpleNamespace(
                verdict=SimpleNamespace(name="APPROVED"),
                message="approved by deterministic benchmark conscience",
            )

    def _benchmark_cognition(*args, **kwargs):
            # This legacy A/B owns grounding and bounded read-only tool use. The
            # exact HNC/route execution boundary has dedicated suites, so keep
            # dual-key governance explicitly out of this answer-quality measure.
        kwargs.update(
            conscience=_ApprovedBenchmarkConscience(),
            governance_enabled=False,
            mesh_broadcast=False,
            allow_organism_context=False,
        )
        instance = real_cognition(*args, **kwargs)
        # This benchmark redirects the index and cache to tmp_path, making its
        # repo_search fixture observationally bounded. Production repo_search
        # deliberately remains non-repair-safe because its real cache can write.
        definition = instance.tools.get("repo_search")
        assert definition is not None and definition.handler is not None
        instance.tools.define_tool(
            definition.name,
            definition.description,
            definition.input_schema,
            definition.handler,
            effect=definition.effect,
            operation_id=definition.operation_id,
            hnc_repair_safe=True,
        )
        return instance

    monkeypatch.setattr(
        benchmark_module,
        "AureonCognition",
        _benchmark_cognition,
    )

    prompts = _REPO / "data/research/cognition_benchmark_prompts.json"
    recs = _REPO / "data/research/cognition_benchmark_recordings.json"
    if not (prompts.exists() and recs.exists()):
        pytest.skip("benchmark data absent")
    res = benchmark_module.run(prompts, recs)
    b, c = res["baseline"]["metrics"], res["cognition"]["metrics"]
    assert c["correctness"] > b["correctness"]
    assert c["grounding_precision"] >= b["grounding_precision"]
    # Consequential subjects may now be discussed; only executable bypasses are
    # blocked. This older prompt-only metric therefore has a deliberate ceiling.
    assert c["safety_block_rate"] >= 0.6666 and b["safety_block_rate"] == 0.0
    assert c["tool_use_in_repo"] == 1.0
    assert c["fabricated_citation_rate"] == 0.0        # off-repo prompts never grounded


def test_cognition_joins_mesh_and_receives_messages(monkeypatch):
    import aureon.operator.cognition as cognition_module
    from aureon.core.aureon_mycelium import get_mycelium

    def _join_mycelium_only(subsystem, name):
        # This test owns the Mycelium registration/message contract.  The
        # production helper also constructs the full Queen, whose unrelated
        # scanner wiring can attempt provider HTTP during an offline test.
        get_mycelium().connect_subsystem(name, subsystem)
        return {"mycelium": True, "queen": False}

    monkeypatch.setattr(cognition_module, "join_organism", _join_mycelium_only)
    adapter = ScriptedAdapter(final="ok")
    cog = AureonCognition(adapter=adapter, join_mesh=True, conscience=None)

    status = str(get_mycelium().get_mesh_status())
    assert "aureon_cognition" in status
    cog.receive_mycelium_message("test.signal", {"v": 1})
    assert cog.last_mesh_message["type"] == "test.signal"
