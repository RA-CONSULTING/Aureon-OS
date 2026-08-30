"""
The Coherence Gate — the living membrane, pinned rule by rule.

Pins: the aperture is continuous and NAMED (full / reduced / introspective /
closed), driven by the live field (Γ + advisory + lighthouse); a DARK field
restricts nothing (tighten-only doctrine — the membrane only narrows on a
LIVE signal); the hard authority boundary stays the outer wall and fires
first; a tool outside the aperture is refused with a named coherence-gate
reason that lands on the blocked ledger (so it parks in the Film-Reel and
surfaces in the acquisition outcome); and the envelope records the gate's
decision on every cake.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.operator.coherence_gate import (
    APERTURES,
    EVOLUTION_FLOWS,
    GAMMA_FULL,
    GAMMA_REDUCED,
    GAMMA_REFUSE,
    compute_aperture,
    compute_evolution_flow,
    reach_for,
)

ALL_TOOLS = {"repo_search", "read_repo_file", "list_repo", "list_skills",
             "web_search", "web_fetch", "code_validate", "read_state"}


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch):
    # Avoid pytest's Windows numbered-dir symlink bookkeeping in this
    # lifecycle-sensitive suite; stdlib temp storage is isolated and removed.
    with tempfile.TemporaryDirectory(prefix="aureon-coherence-") as temp_dir:
        base = Path(temp_dir)
        monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(base / "hnc.jsonl"))
        monkeypatch.setenv("AUREON_ASSIMILATION_PATH", str(base / "assim.jsonl"))
        yield


@pytest.fixture
def _bounded_repo_search(monkeypatch):
    """Keep membrane tests focused; repo-index construction has its own suite."""
    from aureon.operator import cognition, tools

    def bounded(query, top_k=4):
        return [
            SimpleNamespace(
                doc_id="test_fixture:operator",
                score=1.0,
                text=f"bounded repository evidence for {query}",
            )
        ][:top_k]

    monkeypatch.setattr(tools, "_repo_search", bounded)
    monkeypatch.setattr(cognition, "repo_search", bounded)


# ── the aperture function (pure, deterministic) ───────────────────────────


def test_dark_field_never_restricts():
    gate = compute_aperture(None, None, None)
    assert gate["aperture"] == "full" and gate["field_status"] == "canonical_dark"
    assert any("only tightens on a LIVE signal" in r for r in gate["reasons"])
    assert reach_for("full", ALL_TOOLS) is None            # unrestricted


def test_live_field_scales_the_aperture():
    assert compute_aperture(0.8, True, None)["aperture"] == "full"
    reduced = compute_aperture(0.45, True, None)
    assert reduced["aperture"] == "reduced"
    assert any("network reach withdrawn" in r for r in reduced["reasons"])
    assert compute_aperture(0.2, True, None)["aperture"] == "skills_only"
    assert compute_aperture(GAMMA_FULL, True, None)["aperture"] == "full"
    assert compute_aperture(GAMMA_REDUCED, True, None)["aperture"] == "reduced"


def test_advisory_and_lighthouse_hold_the_membrane():
    # a clear Γ but a closed advisory → skills-only, not full
    assert compute_aperture(0.9, False, None)["aperture"] == "skills_only"
    assert compute_aperture(0.9, True, "critical")["aperture"] == "skills_only"
    # low coherence AND closed advisory → no tool runs
    local = compute_aperture(0.2, False, None)
    assert local["aperture"] == "local_only"
    assert any("no tool runs" in r for r in local["reasons"])


def test_refuse_needs_every_signal_against():
    # Γ below the refuse floor AND advisory closed AND lighthouse severe
    refused = compute_aperture(0.1, False, "critical")
    assert refused["aperture"] == "refuse"
    assert any("every signal is against" in r for r in refused["reasons"])
    # any single signal missing → local_only at worst, never refuse
    assert compute_aperture(0.1, False, None)["aperture"] == "local_only"
    assert compute_aperture(0.1, True, "critical")["aperture"] == "local_only"
    assert compute_aperture(GAMMA_REFUSE, False, "critical")["aperture"] == "local_only"


def test_reach_sets_are_named_and_exact():
    assert reach_for("reduced", ALL_TOOLS) == ALL_TOOLS - {"web_search", "web_fetch"}
    assert reach_for("skills_only", ALL_TOOLS) == {
        "repo_search", "read_repo_file", "list_repo", "list_skills"}
    assert reach_for("local_only", ALL_TOOLS) == set()
    assert reach_for("refuse", ALL_TOOLS) == set()
    with pytest.raises(ValueError, match="by name"):
        reach_for("anarchy", ALL_TOOLS)
    assert set(APERTURES) == {"full", "reduced", "skills_only", "local_only",
                              "refuse"}


def test_internal_evolution_flow_never_closes_the_organism():
    for flow in (
        compute_evolution_flow(None, None, None),
        compute_evolution_flow(0.45, True, None, auris_confidence=0.5, beta=1.0),
        compute_evolution_flow(0.05, False, "critical", auris_confidence=0.1, beta=1.2),
    ):
        assert flow["flow"] in EVOLUTION_FLOWS
        assert all(flow["capabilities"].values())
        assert flow["patch_batch_limit"] >= 1
        assert flow["outer_authority_boundary_preserved"] is True

    repair = compute_evolution_flow(0.05, False, 0.95, auris_confidence=0.1)
    assert repair["flow"] == "repair"
    assert "rollback" in repair["required_test_layers"]


def test_internal_evolution_flow_expands_only_on_coherent_hnc_and_auris():
    expanded = compute_evolution_flow(0.82, True, None, auris_confidence=0.79, beta=1.0)
    assert expanded["flow"] == "expand"
    assert expanded["patch_batch_limit"] == 3

    tempered = compute_evolution_flow(0.82, True, None, auris_confidence=0.42, beta=1.0)
    assert tempered["flow"] == "steady"


# ── enforcement: membrane second, wall first ──────────────────────────────


def test_registry_holds_tools_outside_the_aperture(_bounded_repo_search):
    from aureon.operator.tools import build_operator_tools

    reg = build_operator_tools(
        allow_writes=False,
        allow_shell=False,
        hnc_coherence_required=False,
    )
    reg.aperture_allowed = {"repo_search"}
    reg.aperture_note = "aperture 'skills_only' (live)"
    out = json.loads(reg.execute("list_repo", {}))
    assert out["blocked"] and "coherence gate" in out["reason"]
    assert any("coherence gate" in b["reason"] for b in reg.blocked_calls)
    # a tool inside the aperture still runs
    ok = json.loads(reg.execute("repo_search", {"query": "operator"}))
    assert "results" in ok


def test_hard_boundary_fires_before_the_membrane():
    from aureon.operator.tools import build_operator_tools

    reg = build_operator_tools(
        allow_writes=True,
        allow_shell=False,
        hnc_coherence_required=False,
    )
    reg.aperture_allowed = set()                            # membrane fully closed
    out = json.loads(reg.execute("write_repo_file", {"path": ".env", "content": "x"}))
    # the OUTER WALL names the refusal, not the membrane
    assert out["blocked"] and "sensitive path" in out["reason"]


# ── wired through cognition: the field decides, the envelope records ──────


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

    cog = AureonCognition(adapter=adapter, join_mesh=False, conscience=None,
                          mesh_broadcast=False, governance_enabled=False)
    if organism is not None:
        cog._organism = dict(organism)
    return cog


def test_low_coherence_parks_the_web_reach(_bounded_repo_search):
    field = {"symbolic_life_score": 0.4, "coherence_gamma": 0.45,
             "gate_open": True}
    adapter = _Plan([("tool", "web_search", {"query": "anything"}),
                     ("text", "Answered from local knowledge instead.")])
    res = _cog(adapter, organism=field).reason("look something up")
    gate = res.coherence_gate
    assert gate is not None and gate["aperture"] == "reduced"
    # the web call was held by the MEMBRANE, named, and parked
    assert any(t.tool == "web_search" and t.blocked for t in res.tool_calls)
    assert "web_search" in (res.actualization or {}).get("parked_possibilities", [])
    assert res.envelope()["coherence_gate"]["aperture"] == "reduced"


def test_dark_field_keeps_legacy_aperture_but_hnc_holds_non_repair_tools(
    _bounded_repo_search,
):
    adapter = _Plan([("tool", "repo_search", {"query": "operator"}),
                     ("text", "Grounded and complete.")])
    cognition = _cog(adapter)
    res = cognition.reason("how does the operator work?")
    gate = res.coherence_gate
    assert gate is not None and gate["field_status"] == "canonical_dark"
    assert gate["aperture"] == "full"
    assert gate["legacy_aperture_authoritative"] is False
    assert gate["hnc_decision"]["outcome"] == "REPAIR"
    assert any(t.tool == "repo_search" and t.blocked for t in res.tool_calls)
    assert cognition.tools.hnc_context_active is False


def test_hnc_context_is_revoked_when_cognition_turn_raises(monkeypatch):
    cognition = _cog(_Plan([("text", "unused")]))

    def _raise_after_capture(prompt, session_id=None):
        del prompt, session_id
        cognition.tools.set_hnc_coherence_context(None)
        raise RuntimeError("turn failed after HNC capture")

    monkeypatch.setattr(cognition, "_reason", _raise_after_capture)

    with pytest.raises(RuntimeError, match="turn failed"):
        cognition.reason("trigger failure cleanup")
    assert cognition.tools.hnc_context_active is False


def test_clear_field_opens_full_reach(_bounded_repo_search):
    field = {"symbolic_life_score": 0.9, "coherence_gamma": 0.85,
             "gate_open": True}
    adapter = _Plan([("text", "A complete answer.")])
    res = _cog(adapter, organism=field).reason("simple question")
    assert res.coherence_gate is not None
    assert res.coherence_gate["aperture"] == "full"
    assert res.coherence_gate["field_status"] == "live"


def test_legacy_refusal_becomes_hnc_repair_reasoning_not_a_hard_stop(
    _bounded_repo_search,
):
    field = {"symbolic_life_score": 0.05, "coherence_gamma": 0.1,
             "gate_open": False, "lighthouse_severity": "critical"}
    adapter = _Plan([("text", "Repair diagnosis only; no effect was executed.")])
    res = _cog(adapter, organism=field).reason("do something")
    assert adapter.calls >= 1
    assert res.blocked is False
    assert "Repair diagnosis" in res.text
    assert (res.coherence_gate or {})["hnc_decision"]["outcome"] == "REPAIR"
    # Reasoning remains available, while the evidence-only governance record
    # still refuses write-back.
    assert (res.actualization or {}).get("answer") == "realized"
    assert (res.assimilation or {}).get("assimilated") is False
    env = res.envelope()
    assert env["coherence_gate"]["aperture"] == "refuse"
    assert env["coherence_gate"]["legacy_aperture_authoritative"] is False
