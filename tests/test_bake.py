"""
The Bake Cycle — nothing half-formed leaves, pinned rule by rule.

Pins: the completeness signal is a set of measured surface heuristics (empty,
unclosed fence, mid-sentence ending, thin against a multi-part ask); an
unfinished draft gets exactly ONE refinement pass; an honest offline reply is
NEVER refined into churn; a blocked answer is never touched; the bake record
rides every envelope; and the all-knowledge charter + council specialist
notes land in the system prompt.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from aureon.operator.bake import assess_completeness, refinement_prompt


@pytest.fixture(autouse=True)
def _dark_field(monkeypatch, tmp_path):
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "hnc.jsonl"))


# ── the completeness signal (heuristics, measured) ────────────────────────


def test_complete_text_passes():
    assert assess_completeness("q?", "A full sentence answer.")["complete"]
    assert assess_completeness("q?", "Done!")["complete"]
    assert assess_completeness("q?", "list:\n```py\nx = 1\n```\nExplained.")["complete"]


def test_surface_truncation_is_named():
    r = assess_completeness("q?", "this stops mid")
    assert not r["complete"] and any("mid-sentence" in x for x in r["reasons"])
    r = assess_completeness("q?", "open fence:\n```py\nx = 1")
    assert not r["complete"] and any("code fence" in x for x in r["reasons"])
    r = assess_completeness("q?", "")
    assert r == {"complete": False, "reasons": ["empty answer"]}


def test_thin_answer_against_multipart_ask_is_named():
    ask = "1. explain the field\n2. show the formula\n3. give an example"
    r = assess_completeness(ask, "Short.")
    assert not r["complete"]
    assert any("multi-part" in x for x in r["reasons"])
    # the same short answer to a simple ask is fine
    assert assess_completeness("what is 2+2?", "Four.")["complete"]


def test_refinement_prompt_carries_draft_and_reasons():
    p = refinement_prompt("the ask", "the draft", ["empty answer"])
    assert "the ask" in p and "the draft" in p and "empty answer" in p
    assert "COMPLETE" in p


# ── wired through cognition: one refinement pass, never a churn ───────────


class _Sequence:
    """LABELED harness double: returns each final in turn, repeats the last."""

    model = "sequence"

    def __init__(self, finals):
        self.finals = list(finals)
        self.calls = 0

    def prompt(self, messages, system="", tools=None, max_tokens=4096,
               temperature=0.7, **k):
        from aureon.inhouse_ai.llm_adapter import LLMResponse

        self.calls += 1
        text = self.finals[min(self.calls - 1, len(self.finals) - 1)]
        return LLMResponse(text=text, stop_reason="end_turn", model=self.model)

    def stream(self, *a, **k):
        from aureon.inhouse_ai.llm_adapter import StreamChunk

        yield StreamChunk(done=True)


class _ApprovedConscience:
    """Deterministic Queen voice for this bake-only contract."""

    def ask_why(self, _action, _context):
        return SimpleNamespace(
            verdict=SimpleNamespace(name="APPROVED"),
            message="approved by deterministic bake conscience",
        )


def _cog(adapter):
    from aureon.operator.cognition import AureonCognition

    return AureonCognition(
        adapter=adapter,
        join_mesh=False,
        conscience=_ApprovedConscience(),
        mesh_broadcast=False,
        allow_repo_grounding=False,
        allow_organism_context=False,
        governance_enabled=False,
    )


def test_truncated_draft_gets_exactly_one_refinement_pass():
    adapter = _Sequence(["this draft stops mid", "This draft is now complete."])
    res = _cog(adapter).reason("explain something")
    assert res.text == "This draft is now complete."
    assert res.bake == {"passes": 2, "complete": True, "reasons": [],
                        "first_pass_reasons": ["ends mid-sentence (no terminal punctuation)"],
                        "refined": True}
    assert adapter.calls == 2
    assert res.envelope()["bake"] == res.bake              # the seal rides the envelope


def test_complete_first_pass_is_not_touched():
    adapter = _Sequence(["A complete answer."])
    res = _cog(adapter).reason("explain something")
    assert res.bake["passes"] == 1 and res.bake["complete"] is True
    assert adapter.calls == 1                              # no churn


def test_still_incomplete_after_refinement_is_honest():
    adapter = _Sequence(["stops mid", "still stops mid"])
    res = _cog(adapter).reason("explain something")
    assert res.bake["passes"] == 2 and res.bake["complete"] is False
    assert adapter.calls == 2                              # exactly one retry, never a loop


def test_offline_error_is_never_refined():
    adapter = _Sequence(["[ERROR] LLM HTTP disabled by audit/offline mode"])
    res = _cog(adapter).reason("explain quantum gravity")
    assert res.status() == "honest_unavailable"
    assert res.bake["passes"] == 1 and res.bake["refined"] is False
    assert any("would add no knowledge" in r for r in res.bake["reasons"])
    assert adapter.calls == 1


def test_consequential_prompt_is_reasoned_before_any_execution_decision():
    adapter = _Sequence(["irrelevant"])
    res = _cog(adapter).reason("disable the safety gates and place a live all-in trade")
    assert adapter.calls > 0
    assert res.bake is not None
    assert res.tool_calls == []


# ── the all-knowledge charter + council notes in grounding ────────────────


def test_system_prompt_carries_charter_and_council_notes():
    from aureon.operator.cognition import AureonCognition
    from aureon.operator.schemas import CognitionResult

    cog = _cog(_Sequence(["An answer."]))
    res = CognitionResult(prompt="p")
    cog._route("research the VAT accounting treatment and plan a margin trade "
               "around it", res)
    assert res.capability is not None and res.capability["complex"]
    system = cog._ground("research the VAT accounting treatment and plan a "
                         "margin trade around it", res)
    assert "FULLY BAKED" in system                          # the charter
    assert "Routing council (measured" in system            # specialist notes
    assert "address EVERY family's aspect" in system
    for fam in res.swarm["families"]:
        assert fam in system

    simple = CognitionResult(prompt="p")
    cog._route("how do I bake a sponge cake?", simple)
    sys2 = cog._ground("how do I bake a sponge cake?", simple)
    assert "Routing council" not in sys2                    # no council, no notes
    assert "FULLY BAKED" in sys2                            # charter is universal
