"""The drafting organ: gated, honest about the model, and checked against its own claims.

Hermetic throughout. Every test builds its own repository under ``tmp_path``, its
own reconciliation document, and its own adapter — no test touches a model, the
network, or the live grant ledger. The organism's readings are stubbed at
``aureon.gates.switchboard.read_organism``, the same seam
``tests/grants/test_dossier.py`` uses, so a gate decision here is the real
``evaluate`` running over a reading the test chose.

These tests cover ``author.py``'s own contract — the gate, the model, and the
result. The brief's assembly is ``assemble.py``'s contract and the claim rules are
``claims.py``'s; what is asserted here is that this module *routes through* them
and does not paper over what they report:

* a chain that does not ADVANCE produces **no text**, and the adapter is never
  even called;
* an unavailable adapter yields a **blocker**, never the stub's configuration
  message wearing a draft's clothes;
* a blended draft comes back marked ``needs_revision`` with the reason attached;
* ``export_for_stronger_model`` carries the standing rule **verbatim**;
* and no company detail is written into the source — every one is read.
"""

from __future__ import annotations

import importlib
import json
from datetime import UTC, datetime

import pytest

from aureon.briefing import author as author_module
from aureon.briefing.assemble import assemble_brief
from aureon.briefing.author import (
    DRAFT_ACTION,
    DRAFT_CHAIN,
    MODEL_CAVEAT,
    REVISION_SEVERITIES,
    DraftResult,
    adapter_blocker,
    draft,
    export_for_stronger_model,
    response_blocker,
)
from aureon.briefing.claims import BLOCKING, RULE_BLENDING, ClaimReport, check_claims
from aureon.briefing.schemas import Brief
from aureon.gates.switchboard import ADVANCE, REDO, GateReading, is_human_held

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)

# ── fixture documents ────────────────────────────────────────────────────────

# Shaped exactly like the live reconciliation report — a labelled row, then a
# verbatim blockquote — but carrying invented values. That is the point of every
# assertion below: a fixture value appearing in an output is proof of a read, and
# a real company value appearing anywhere would be proof of a hardcode.
APPROVAL_RULE = "TEST APPROVAL RULE: nothing leaves this building unless the director says so."
CLAIM_RULE = "TEST CLAIM RULE: separate what is built from what is published from what is guessed."
THESIS = "TEST THESIS: a local-first evidence system for widget logistics."
COMPLIANCE_BLOCKER = "TEST BLOCKER: the annual return is overdue. Resolve before competitive bids."

RECONCILIATION = f"""# Test Reconciliation

## 6.1 Compliance blocker

Overview tab, row `Compliance blocker` — **verbatim:**

> "{COMPLIANCE_BLOCKER}"

## 6.2 Approval rule

Overview tab, row `Approval rule` — **verbatim:**

> "{APPROVAL_RULE}"

### 6.4 Primary grant thesis

Overview tab, row `Primary grant thesis` — **verbatim:**

> "{THESIS}"

### 6.5 Claim-discipline rule

Overview tab, row `Claim discipline` — **verbatim:**

> "{CLAIM_RULE}"
"""

# Named to match both aureon.grants.scout.RECONCILIATION_DOC (a fixed path) and
# the RECONCILIATION_*.md glob the auditor and the dossier use.
RECONCILIATION_NAME = "RECONCILIATION_20260731.md"

# Prose that keeps the three claim classes in separate sentences.
CLEAN_DRAFT = ("The ledger reader is tested against a fixture in this repository. "
               "A follow-on study is proposed for the coherence question.")
# One sentence welding a verified capability to a speculative claim — the blur the
# owner's claim-discipline row prohibits by name.
BLENDED_DRAFT = "The gate module is implemented and the harmonic field predicts market turns."


@pytest.fixture
def repo(tmp_path):
    """A repository root carrying a reconciliation and a one-application ledger."""
    grants = tmp_path / "data" / "research" / "grants"
    grants.mkdir(parents=True)
    (grants / RECONCILIATION_NAME).write_text(RECONCILIATION, encoding="utf-8")
    (grants / "pipeline.json").write_text(json.dumps({
        "active_applications": [{
            "id": "APP-TEST-001",
            "name": "Test Widget Fund",
            "funder": "Test Funder",
            "status": "EVIDENCE_REQUIRED_NOT_SUBMITTED",
            "deadline": "2026-08-05T11:00:00+00:00",
            "documents": ["evidence.pdf"],
        }],
    }), encoding="utf-8")
    return tmp_path


@pytest.fixture
def brief(repo) -> Brief:
    return assemble_brief(repo, now=NOW)


def _perfect(monkeypatch):
    """An organism that agrees with itself on real inputs — the chain can advance."""
    monkeypatch.setattr(
        "aureon.gates.switchboard.read_organism",
        lambda bus=None: GateReading(coherence=0.82, divergence=0.08, life_score=0.7,
                                     panel_consensus="RALLY", panel_confidence=0.9,
                                     panel_evidence=1.0),
    )


def _blind(monkeypatch):
    """An organism with no reading at all — every gate must REDO."""
    monkeypatch.setattr("aureon.gates.switchboard.read_organism", lambda bus=None: GateReading())


# ── adapters, none of which is a model ───────────────────────────────────────


class _Fake:
    """A model that returns exactly what a test asked for, and records its prompt."""

    def __init__(self, text=CLEAN_DRAFT, *, model="fake:test", stop_reason="end_turn",
                 healthy=True, raises: type[Exception] | None = None):
        self._text, self._model, self._stop = text, model, stop_reason
        self._healthy, self._raises = healthy, raises
        self.calls: list[dict] = []

    def health_check(self):
        return self._healthy

    def prompt(self, messages, system="", **kwargs):
        self.calls.append({"messages": messages, "system": system, **kwargs})
        if self._raises is not None:
            raise self._raises("model exploded")

        class _Response:
            pass

        response = _Response()
        response.text, response.model, response.stop_reason = self._text, self._model, self._stop
        return response


class _NeverCalled(_Fake):
    """An adapter that fails the test if it is asked for anything."""

    def prompt(self, messages, system="", **kwargs):  # pragma: no cover - must not run
        raise AssertionError("the model was called; it must not have been")


class _FakeStubAdapter(_Fake):
    """Stands in for AureonStubAdapter: healthy, and its 'draft' is boilerplate.

    This is the trap the module exists to avoid. ``build_voice_adapter()`` returns
    a stub whose ``health_check()`` is True and whose ``prompt()`` returns
    configuration text, so a health check alone protects nothing at all.
    """


# ── the chain runs before the pen moves ──────────────────────────────────────


def test_a_redo_chain_produces_no_text_at_all(monkeypatch, brief):
    _blind(monkeypatch)
    adapter = _NeverCalled()
    result = draft("Draft the widget narrative", brief=brief, adapter=adapter, now=NOW)

    assert result.text is None
    assert result.drafted is False
    assert result.decision == REDO
    assert result.gate_verdicts, "the verdicts must come back so the caller sees where it stopped"
    assert "did not advance" in (result.blocker or "")
    # No claim report, because there was nothing to check — not a clean one.
    assert result.claim_report is None
    assert adapter.calls == []


def test_the_verdicts_come_back_even_though_the_draft_does_not(monkeypatch, brief):
    _blind(monkeypatch)
    result = draft("Draft it", brief=brief, adapter=_NeverCalled(), now=NOW)
    assert result.gate_verdicts[0].gate == DRAFT_CHAIN[0].name
    assert result.blocker and result.gate_verdicts[0].reasoning in result.blocker
    assert result.advanced is False


def test_a_gate_failure_is_reported_not_swallowed(monkeypatch, brief):
    def _explode(*_a, **_kw):
        raise RuntimeError("switchboard down")

    monkeypatch.setattr(author_module, "run_chain", _explode)
    result = draft("Draft it", brief=brief, adapter=_NeverCalled(), now=NOW)
    assert result.text is None
    assert "gate chain could not be run" in result.blocker
    assert "RuntimeError" in result.blocker


def test_drafting_is_not_a_human_held_action_or_nothing_could_ever_be_written():
    # If DRAFT_ACTION were renamed to something the switchboard holds, or the
    # chain grew a human-held gate, every ask would return HOLD and the organ
    # would look broken rather than blocked.
    assert not is_human_held(DRAFT_ACTION)
    assert not any(gate.requires_human for gate in DRAFT_CHAIN)


def test_the_action_the_chain_actually_sees_is_the_drafting_one(monkeypatch, brief):
    seen: dict = {}

    def _capture(context=None, **kwargs):
        seen.update(context or {})
        return []

    monkeypatch.setattr(author_module, "run_chain", _capture)
    draft("Submit the widget application", brief=brief, adapter=_NeverCalled(), now=NOW)
    assert seen["action"] == DRAFT_ACTION
    # The ask travels under its own key so an ask that merely mentions submission
    # cannot convert a drafting request into a HOLD.
    assert seen["requested"] == "Submit the widget application"


def test_an_empty_chain_authorises_nothing(monkeypatch, brief):
    monkeypatch.setattr(author_module, "run_chain", lambda *a, **kw: [])
    result = draft("Draft it", brief=brief, adapter=_NeverCalled(), now=NOW)
    assert result.text is None
    assert "nothing authorised this draft" in result.blocker


def test_the_chain_advances_on_a_sound_organism_and_she_writes(monkeypatch, brief):
    _perfect(monkeypatch)
    result = draft("Draft it", brief=brief, adapter=_Fake(), now=NOW)
    assert result.advanced is True
    assert result.decision == ADVANCE
    assert result.text == CLEAN_DRAFT


# ── an unavailable model is a blocker, never a stub paragraph ────────────────


def test_a_stub_adapter_yields_a_blocker_not_a_stub_paragraph(monkeypatch, brief):
    _perfect(monkeypatch)
    boilerplate = "No LLM backend is reachable.\nTo enable real conversation: start Ollama."
    result = draft("Draft it", brief=brief, adapter=_FakeStubAdapter(boilerplate), now=NOW)

    assert result.text is None, "configuration text must never be returned as a draft"
    assert "no local model is reachable" in result.blocker
    assert "export_for_stronger_model" in result.blocker


def test_a_placeholder_model_name_is_caught_even_when_the_text_reads_like_prose(monkeypatch, brief):
    _perfect(monkeypatch)
    # The class name gives nothing away here; only the response's model does. This
    # is the second line of defence and it has to hold on its own.
    prose = "Our organisation delivers evidence-grade automation for regulated operations."
    result = draft("Draft it", brief=brief,
                   adapter=_Fake(prose, model="ollama-unavailable"), now=NOW)
    assert result.text is None
    assert "placeholder rather than a model" in result.blocker


@pytest.mark.parametrize("text", ["[ERROR] LLM HTTP disabled by audit/offline mode",
                                  "[AUREON] No backend configured."])
def test_an_error_string_in_the_text_field_is_not_a_draft(monkeypatch, brief, text):
    _perfect(monkeypatch)
    result = draft("Draft it", brief=brief, adapter=_Fake(text, model="llama3:latest"), now=NOW)
    assert result.text is None
    assert "returned an error string" in result.blocker


def test_an_error_stop_reason_is_not_a_draft(monkeypatch, brief):
    _perfect(monkeypatch)
    result = draft("Draft it", brief=brief,
                   adapter=_Fake("half a sentence", stop_reason="error"), now=NOW)
    assert result.text is None and "stop_reason=error" in result.blocker


def test_empty_output_is_a_blocker_not_an_empty_draft(monkeypatch, brief):
    _perfect(monkeypatch)
    result = draft("Draft it", brief=brief, adapter=_Fake("   \n  "), now=NOW)
    assert result.text is None and "returned no text" in result.blocker


def test_an_unhealthy_adapter_is_refused_before_it_is_called(monkeypatch, brief):
    _perfect(monkeypatch)
    adapter = _Fake(healthy=False)
    result = draft("Draft it", brief=brief, adapter=adapter, now=NOW)
    assert result.text is None
    assert "unreachable" in result.blocker
    assert adapter.calls == []


def test_a_raising_model_is_a_blocker_and_names_the_export_route(monkeypatch, brief):
    _perfect(monkeypatch)
    result = draft("Draft it", brief=brief, adapter=_Fake(raises=TimeoutError), now=NOW)
    assert result.text is None
    assert "TimeoutError" in result.blocker
    assert "export_for_stronger_model" in result.blocker


def test_a_missing_adapter_is_named_rather_than_assumed_working():
    assert "returned nothing" in adapter_blocker(None)


def test_an_adapter_with_no_prompt_method_is_refused():
    class _NotAnAdapter:
        def health_check(self):
            return True

    assert "no prompt() method" in adapter_blocker(_NotAnAdapter())


def test_a_health_check_that_raises_is_a_blocker_not_an_assumption():
    class _Angry:
        def prompt(self, *a, **kw):  # pragma: no cover - never reached
            raise AssertionError

        def health_check(self):
            raise ConnectionError("refused")

    assert "ConnectionError" in adapter_blocker(_Angry())


def test_a_real_looking_response_passes_the_response_guard():
    assert response_blocker("A grounded sentence.", "llama3:latest", "end_turn") is None


def test_every_result_carries_the_model_caveat_including_the_ones_that_failed(monkeypatch, brief):
    _blind(monkeypatch)
    blocked = draft("Draft it", brief=brief, adapter=_NeverCalled(), now=NOW)
    _perfect(monkeypatch)
    written = draft("Draft it", brief=brief, adapter=_Fake(), now=NOW)
    for result in (blocked, written):
        assert "NOT adequate for a competitive Innovate UK narrative" in result.model_caveat
        assert "export_for_stronger_model" in result.model_caveat


def test_the_caveat_names_the_configured_model_rather_than_a_remembered_one(monkeypatch, brief):
    monkeypatch.setenv("AUREON_LLM_MODEL", "tinyllama:1.1b")
    _perfect(monkeypatch)
    result = draft("Draft it", brief=brief, adapter=_Fake(), now=NOW)
    assert "tinyllama:1.1b" in result.model_caveat


def test_the_caveat_says_small_local_model_whatever_is_configured():
    assert "small local model" in MODEL_CAVEAT


# ── the claim check, over the OUTPUT ─────────────────────────────────────────


def test_a_blended_draft_is_marked_needs_revision_and_says_why(monkeypatch, brief):
    _perfect(monkeypatch)
    result = draft("Draft it", brief=brief, adapter=_Fake(BLENDED_DRAFT), now=NOW)

    assert result.text == BLENDED_DRAFT, "the draft comes back WITH the objection, not withheld"
    assert result.needs_revision is True
    assert result.revision_reasons, "needs_revision must always come with a stated reason"
    assert any(RULE_BLENDING in reason for reason in result.revision_reasons)
    assert any(BLENDED_DRAFT in reason for reason in result.revision_reasons)
    assert result.claim_report is not None
    assert result.claim_report.blended_count >= 1
    assert result.claim_report.highest_severity == BLOCKING


def test_a_clean_draft_still_carries_a_claim_report(monkeypatch, brief):
    _perfect(monkeypatch)
    result = draft("Draft it", brief=brief, adapter=_Fake(CLEAN_DRAFT), now=NOW)
    assert result.needs_revision is False
    assert result.revision_reasons == ()
    assert isinstance(result.claim_report, ClaimReport)
    assert result.claim_report.blended_count == 0
    assert result.claim_report.sentences_checked >= 2


def test_the_claim_check_runs_on_the_output_not_on_the_prompt(monkeypatch, brief):
    seen: dict = {}

    def _spy(text, **kwargs):
        seen["text"] = text
        return check_claims(text, **kwargs)

    _perfect(monkeypatch)
    monkeypatch.setattr(author_module, "check_claims", _spy)
    draft("Draft the widget narrative", brief=brief, adapter=_Fake(CLEAN_DRAFT), now=NOW)
    assert seen["text"] == CLEAN_DRAFT
    assert THESIS not in seen["text"], "the brief must not be fed back through the checker"


def test_the_capability_record_reaches_the_checker_so_contradictions_can_fire(monkeypatch, repo):
    seen: dict = {}

    def _spy(text, *, capability=None):
        seen["capability"] = capability
        return check_claims(text, capability=capability)

    _perfect(monkeypatch)
    monkeypatch.setattr(author_module, "check_claims", _spy)
    draft("Draft it", root=repo, adapter=_Fake(), now=NOW)
    profile = seen["capability"]
    assert profile is not None, "without the record, contradicted_by_own_record cannot fire"
    assert COMPLIANCE_BLOCKER in profile.compliance_blockers


def test_a_capability_read_that_fails_does_not_take_the_draft_down(monkeypatch, brief):
    def _explode(*_a, **_kw):
        raise OSError("disk gone")

    _perfect(monkeypatch)
    # importlib, not the dotted string: aureon.grants re-exports a *function*
    # named ``scout``, which shadows the submodule attribute — see the note in
    # aureon/grants/__init__.py.
    monkeypatch.setattr(importlib.import_module("aureon.grants.scout"),
                        "read_capability", _explode)
    result = draft("Draft it", brief=brief, adapter=_Fake(), now=NOW)
    assert result.text == CLEAN_DRAFT
    # The report must say the contradiction rule could not be run, rather than
    # reading clean as though the record had been consulted.
    assert result.claim_report.blocker


def test_only_the_owners_own_rules_force_a_revision():
    # blocking == blending, the blur his claim-discipline row names; critical ==
    # contradicting the company's own record. Everything softer is reported and
    # left to a human, because "this absolute is strong" is a judgement.
    assert REVISION_SEVERITIES == (BLOCKING, "critical")


def test_an_advisory_finding_alone_does_not_force_a_revision(monkeypatch, brief):
    _perfect(monkeypatch)
    # A bare number with no citation is advisory: worth saying, not a hand-back.
    result = draft("Draft it", brief=brief,
                   adapter=_Fake("The reconciliation counted 1,100 artifacts."), now=NOW)
    assert result.claim_report.findings, "the finding must still be reported"
    assert all(f.severity not in REVISION_SEVERITIES for f in result.claim_report.findings)
    assert result.needs_revision is False


# ── the export, which is the honest route for high-stakes work ──────────────


def test_export_contains_the_standing_rule_verbatim(brief):
    rendered = export_for_stronger_model(brief, "Draft the widget narrative")
    assert brief.standing_rule is not None
    assert brief.standing_rule.text == APPROVAL_RULE
    assert APPROVAL_RULE in rendered, "the standing rule must travel verbatim, never paraphrased"
    assert brief.standing_rule.source in rendered


def test_export_contains_the_claim_rule_verbatim_and_the_ask(brief):
    rendered = export_for_stronger_model(brief, "Sharpen section 3")
    assert brief.claim_discipline.text == CLAIM_RULE
    assert CLAIM_RULE in rendered
    assert "Sharpen section 3" in rendered


def test_export_carries_the_brief_facts_and_the_live_deadline(brief):
    rendered = export_for_stronger_model(brief, "Draft it")
    assert THESIS in rendered
    assert "Test Widget Fund" in rendered, "the live deadline must reach the prompt"


def test_export_lists_what_could_not_be_read_rather_than_filling_it_in(tmp_path):
    bare = assemble_brief(tmp_path, now=NOW)
    rendered = export_for_stronger_model(bare, "Draft it")
    assert bare.blockers
    assert "NOT READ" in rendered


def test_an_unreadable_standing_rule_is_declared_not_invented(tmp_path):
    bare = assemble_brief(tmp_path, now=NOW)
    assert bare.standing_rule is None
    rendered = export_for_stronger_model(bare, "Draft it")
    # No fabricated quote stands in for the rule that could not be read.
    assert f'"{APPROVAL_RULE}"' not in rendered
    assert APPROVAL_RULE not in rendered


def test_an_export_with_no_ask_invents_none(brief):
    rendered = export_for_stronger_model(brief)
    assert APPROVAL_RULE in rendered
    assert "\nASK\n" not in rendered and "\nASKS\n" not in rendered


def test_several_asks_are_carried_as_several(brief):
    rendered = export_for_stronger_model(brief, ["Draft the narrative", "Say if we do not fit"])
    assert "Draft the narrative" in rendered
    assert "Say if we do not fit" in rendered


# ── what the model was actually asked ────────────────────────────────────────


def test_the_prompt_the_model_received_carried_both_rules_and_the_facts(monkeypatch, brief):
    _perfect(monkeypatch)
    adapter = _Fake()
    draft("Draft it", brief=brief, adapter=adapter, now=NOW)

    assert len(adapter.calls) == 1
    call = adapter.calls[0]
    content = call["messages"][0]["content"]
    assert APPROVAL_RULE in content
    assert CLAIM_RULE in content
    assert THESIS in content
    assert "binding" in call["system"]
    # Evidence-bound prose, not invention.
    assert call["temperature"] <= 0.3


def test_the_system_prompt_forbids_supplying_missing_facts(monkeypatch, brief):
    _perfect(monkeypatch)
    adapter = _Fake()
    draft("Draft it", brief=brief, adapter=adapter, now=NOW)
    system = adapter.calls[0]["system"]
    assert "not in the brief" in system
    assert "never supply it from general knowledge" in system
    assert "Nothing in this task is a request to submit, file, pay or send." in system


def test_an_ask_that_names_a_held_step_is_flagged_to_the_model(monkeypatch, brief):
    _perfect(monkeypatch)
    adapter = _Fake("The application is not yet ready to send.")
    result = draft("Submit the widget application", brief=brief, adapter=adapter, now=NOW)
    # Drafting text about a submission is drafting: the organ has no submit path
    # at all, so refusing here would protect nothing and hide the work.
    assert result.text is not None
    assert "no automatic executor" in adapter.calls[0]["system"]
    assert "does not perform it" in adapter.calls[0]["system"]


def test_an_ordinary_ask_carries_no_held_step_note(monkeypatch, brief):
    _perfect(monkeypatch)
    adapter = _Fake()
    draft("Sharpen the narrative", brief=brief, adapter=adapter, now=NOW)
    assert "no automatic executor" not in adapter.calls[0]["system"]


def test_the_brief_is_assembled_when_none_was_passed(monkeypatch, repo):
    _perfect(monkeypatch)
    result = draft("Draft it", root=repo, adapter=_Fake(), now=NOW)
    assert RECONCILIATION_NAME in " ".join(result.brief_sources)
    assert result.text == CLEAN_DRAFT


def test_an_empty_root_still_drafts_but_carries_its_blockers(monkeypatch, tmp_path):
    # An explicit root is honoured verbatim and never widened to the real
    # repository. If that regressed, this test would quietly assert against the
    # live company record.
    _perfect(monkeypatch)
    result = draft("Draft it", root=tmp_path, adapter=_Fake(), now=NOW)
    assert result.brief_blockers, "an unread source must be reported, not silently omitted"
    assert not any(APPROVAL_RULE in b for b in result.brief_blockers)


# ── the result object ────────────────────────────────────────────────────────


def test_a_bare_result_is_honest_about_having_nothing():
    result = DraftResult()
    assert result.drafted is False
    assert result.decision is None
    assert result.advanced is False
    assert result.needs_revision is False
    json.dumps(result.to_dict())


def test_the_result_round_trips_and_narrates_the_objection(monkeypatch, brief):
    _perfect(monkeypatch)
    result = draft("Draft it", brief=brief, adapter=_Fake(BLENDED_DRAFT), now=NOW)
    payload = result.to_dict()
    json.dumps(payload)
    assert payload["needs_revision"] is True
    assert payload["decision"] == ADVANCE
    assert payload["claim_report"]["blended_count"] >= 1

    narration = result.narrate()
    assert "NEEDS REVISION" in narration
    assert RULE_BLENDING in narration
    assert BLENDED_DRAFT in narration
    assert "small local model" in narration


def test_a_blocked_result_narrates_the_blocker_and_the_gates(monkeypatch, brief):
    _blind(monkeypatch)
    narration = draft("Draft it", brief=brief, adapter=_NeverCalled(), now=NOW).narrate()
    assert "NOT produced" in narration
    assert "blocker:" in narration
    assert f"gate {DRAFT_CHAIN[0].name}:" in narration


# ── nothing about the company is written into the source ────────────────────


@pytest.mark.parametrize("forbidden", ["NI696693", "Leckey", "Quadrant", "BT12", "R&A Consulting"])
def test_no_company_detail_is_hardcoded_in_the_module(forbidden):
    # The repository went through a large de-randomisation. A company fact written
    # into source is a fabricated measurement that happens to be true today; every
    # one of these is read at runtime by aureon.identity instead.
    with open(author_module.__file__, encoding="utf-8") as handle:
        text = handle.read()
    assert forbidden.lower() not in text.lower(), f"{forbidden!r} must be read, not written down"


def test_no_rule_text_is_hardcoded_either(brief):
    with open(author_module.__file__, encoding="utf-8") as handle:
        text = handle.read()
    # Proof that the module is not the source of the rules: a fixture rule with
    # entirely different wording is what the brief and the export actually carry.
    assert brief.standing_rule.text == APPROVAL_RULE
    assert APPROVAL_RULE not in text
    assert CLAIM_RULE not in text
