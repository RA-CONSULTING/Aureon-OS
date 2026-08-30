"""The assembler: it reads the brief out of documents, or says it could not.

Hermetic. Every test builds a miniature repository under ``tmp_path`` and passes
it as ``root``, so nothing here touches the live ledger, the live COMPANY.md or
the network. The live reading of the organism is injected, because the spine is a
reading of whatever the machine is doing at the time and a test that depended on
that would pass or fail for reasons unrelated to this code.

The fixture documents are written by hand with an invented company, an invented
registrar sentence and invented rules. That is the point: the assembler must find
the standing rule, the positioning line, the claim discipline and the statutory
blocker by *reading*, so a fixture that shares none of the real repository's
strings has to work exactly as well as the real one — and a fallback into the
live repo shows up as a test that quotes a company this fixture never mentioned.

What is being proved, in order of importance:

  1. a missing document yields a blocker, never an invented line — and never the
     live repository's own facts;
  2. every priority carries a real ``days_remaining`` measured from a real date,
     or ``None``; never a placeholder zero;
  3. provenance is attached to every sourced line, and a line without a source
     cannot be constructed at all;
  4. the standing rule and the claim discipline appear **verbatim** in the
     rendered prompt, and an unreadable standing rule fails closed.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from aureon.briefing.assemble import (
    APPROVAL_CHECK,
    assemble_brief,
    live_priorities,
    probe_capabilities,
    spine_lines,
    standing_rule,
)
from aureon.briefing.render import NO_RULE_READ, render_markdown, render_prompt
from aureon.briefing.schemas import Brief, Capability, Priority, SourcedLine
from aureon.gates.switchboard import GateReading
from aureon.grants.scout import RECONCILIATION_DOC

NOW = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)

# ── the invented company ─────────────────────────────────────────────────────
# Not one string below appears in the real repository's documents. Anything the
# assembler reports that is not from this fixture came from somewhere it should
# not have been looking.

OFFICE = "1 Example Street, Exampleton, EX1 1EX"

COMPANY_MD = f"""# Example Systems Ltd

## Company

| | |
|---|---|
| **Registered name** | Example Systems Ltd |
| **Company number** | ZZ000001 |
| **Registered office** | {OFFICE} |
| **Director** | A Person |

## What the company builds

Evidence tooling for controlled automation, logistics telemetry and research
validation, assembled so a reviewer can audit every step.
"""

CHARTER_MD = """# Operating core

## MISSION

I operate as the research-operations core for an invented company used only in
tests.

1. Keep the evidence record complete and reviewable.
2. Guard honesty: every claim carries its evidence state.
"""

README_MD = """# Example OS

## What Example OS is

A local-first operating layer that lets one operator run and inspect
evidence-heavy automation from a single place.
"""

SYNTHESIS_MD = """# Synthesis

## What This Repository Is

A record of instrumentation, ledgers and audits kept together so a reviewer can
tell what exists from what is experimental.
"""

# The rules. Deliberately worded unlike the real ones, so a verbatim assertion
# proves reading rather than recognition.
STANDING = ("No external submission, legal representation, filing, payment, or email send "
            "should happen without Director approval.")
THESIS = "Example Systems is positioned as an evidence platform for controlled automation."
CLAIMS = ("Say only what the receipts support. Separate shipped software from published "
          "research from untested guesses.")
# Contains the auditor's own vocabulary ("confirmation statement", "overdue") because
# that is what the auditor reads for; the registrar, company and date are invented.
# One ISO date, in the past relative to NOW, so the days figure is measurable.
REGISTRY_BLOCKER = ("Registry shows the confirmation statement due 2026-05-01 as overdue. "
                    "Resolve before submitting competitive bids where possible.")

RECONCILIATION_MD = f"""# Reconciliation

## 6. Blockers and operating rules extracted from the sheet

### 6.1 Registry blocker

Overview tab, row `Compliance blocker` — **verbatim:**

> "{REGISTRY_BLOCKER}"

### 6.2 Approval rule

Overview tab, row `Approval rule` — **verbatim:**

> "{STANDING}"

### 6.4 Primary grant thesis

Overview tab, row `Primary grant thesis` — **verbatim:**

> "{THESIS}"

### 6.5 Claim-discipline rule

Overview tab, row `Claim discipline` — **verbatim:**

> "{CLAIMS}"
"""

APPLICANT = {
    "applicant": {
        "legal_entity": "Example Systems Ltd",
        "company_number": "ZZ000001",
        "registered_office": OFFICE,
        "lead_contact": "A Person",
    },
    "automation_policy": [
        "Final submission requires exact action-time confirmation from the director.",
    ],
}

LEDGER = {
    "company_compliance_risk_active": True,
    "active_applications": [
        {
            "id": "APP-OVERDUE-0001",
            "name": "Overdue Example Call",
            "funder": "Example Funder",
            "status": "AWAITING_REVIEW",
            "deadline": "2026-07-20T11:00:00+00:00",
            "documents": ["pack.pdf"],
        },
        {
            "id": "APP-SOON-0002",
            "name": "Imminent Example Call",
            "funder": "Example Funder",
            "status": "APPROVAL_REQUIRED",
            "deadline": "2026-08-05T17:00:00+00:00",
            "documents": ["pack.pdf"],
        },
        {
            "id": "APP-NODATE-0003",
            "name": "Undated Example Call",
            "funder": "Example Funder",
            "status": "AWAITING_REVIEW",
            "documents": ["pack.pdf"],
        },
        {
            # Closed, with a deadline that would otherwise be urgent: it must not
            # become a priority. The ledger organ owns that rule; this row is here
            # so the brief cannot quietly stop honouring it.
            "id": "APP-CLOSED-0004",
            "name": "Closed Example Call",
            "funder": "Example Funder",
            "status": "SUBMITTED",
            "deadline": "2026-08-02T09:00:00+00:00",
            "documents": ["pack.pdf"],
        },
    ],
}

# Strings from the real repository. None of them may appear in a brief assembled
# from the fixture above; if one does, something reached out of the caller's root.
LIVE_LEAKS = ("NI696693", "Leckey", "Quadrant", "R&A Consulting", "Belfast", "Innovate UK")


def _repo(
    tmp_path,
    *,
    company=COMPANY_MD,
    charter=CHARTER_MD,
    readme=README_MD,
    synthesis=SYNTHESIS_MD,
    reconciliation=RECONCILIATION_MD,
    applicant=APPLICANT,
    ledger=LEDGER,
    package=None,
):
    """Build a miniature repository. Anything passed ``None`` is simply absent."""
    grants = tmp_path / "data" / "research" / "grants"
    grants.mkdir(parents=True, exist_ok=True)
    for name, text in (
        ("COMPANY.md", company),
        ("AUREON_OPERATING_CORE.md", charter),
        ("README.md", readme),
    ):
        if text is not None:
            (tmp_path / name).write_text(text, encoding="utf-8")
    if synthesis is not None:
        (tmp_path / "docs").mkdir(parents=True, exist_ok=True)
        (tmp_path / "docs" / "THE_SYNTHESIS.md").write_text(synthesis, encoding="utf-8")
    if reconciliation is not None:
        # The scout resolves the reconciliation by exact relative path, so the
        # fixture is written to the path the organ actually reads rather than to a
        # name this test invented.
        (tmp_path / RECONCILIATION_DOC).write_text(reconciliation, encoding="utf-8")
    if applicant is not None:
        (grants / "autopilot_status.json").write_text(json.dumps(applicant), encoding="utf-8")
    if ledger is not None:
        (grants / "pipeline.json").write_text(json.dumps(ledger), encoding="utf-8")
    if package is not None:
        pkg = tmp_path / "aureon" / package
        pkg.mkdir(parents=True, exist_ok=True)
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        tests = tmp_path / "tests" / package
        tests.mkdir(parents=True, exist_ok=True)
        (tests / "test_example.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    return tmp_path


READING = GateReading(
    coherence=0.8312,
    divergence=0.1204,
    life_score=0.5511,
    panel_consensus="NEUTRAL",
    panel_confidence=0.7,
    panel_evidence=0.4286,
)
BLIND = GateReading()


def _brief(tmp_path, *, reading=READING, **kwargs) -> Brief:
    return assemble_brief(
        _repo(tmp_path, **kwargs),
        now=NOW,
        organism_reader=lambda _bus: reading,
    )


# ── 1. a missing document is a blocker, not a sentence ───────────────────────


def test_an_empty_repository_yields_blockers_and_no_invented_lines(tmp_path):
    """Point it at nothing and it says so — in every section, for every fact."""
    brief = assemble_brief(tmp_path, now=NOW, organism_reader=lambda _bus: READING)

    assert brief.identity == ()
    assert brief.standing_rule is None
    assert brief.positioning is None
    assert brief.claim_discipline is None
    assert brief.capabilities_built == ()
    # The spine is a reading of the live organism rather than of this root, so it
    # is still present; every root-scoped section is empty.
    for section in ("identity", "standing_rule", "positioning", "claim_discipline",
                    "capabilities_built"):
        assert section in brief.omitted

    joined = " ".join(brief.blockers)
    assert "standing_rule" in joined
    assert "positioning" in joined
    assert "claim_discipline" in joined
    assert "capabilities_built" in joined
    assert "identity" in joined


def test_nothing_falls_back_to_the_live_repository(tmp_path):
    """A bare root must not be widened to the real repo — in any renderer."""
    for text in (
        render_markdown(assemble_brief(tmp_path, now=NOW, organism_reader=lambda _b: READING)),
        render_prompt(assemble_brief(tmp_path, now=NOW, organism_reader=lambda _b: READING), "any"),
        render_markdown(_brief(tmp_path)),
        render_prompt(_brief(tmp_path), "any"),
    ):
        for leak in LIVE_LEAKS:
            assert leak not in text, f"{leak!r} leaked from the live repository"


def test_a_missing_reconciliation_loses_the_rules_but_invents_nothing(tmp_path):
    """No reconciliation: no thesis, no claim discipline, and no borrowed wording.

    The standing rule survives here, and that is a measurement rather than a
    leniency: the applicant record states its own approval rule, the auditor reads
    that document too, and the brief quotes *that* document's words with that
    document as the source. What must never happen is the reconciliation's rule
    appearing when the reconciliation is gone.
    """
    brief = _brief(tmp_path, reconciliation=None)

    assert brief.positioning is None
    assert brief.claim_discipline is None
    assert any("claim_discipline" in b for b in brief.blockers)
    assert any("positioning" in b for b in brief.blockers)

    assert brief.standing_rule is not None
    assert brief.standing_rule.text == APPLICANT["automation_policy"][0]
    assert brief.standing_rule.source.endswith("autopilot_status.json")

    prompt = render_prompt(brief, "draft something")
    assert STANDING not in prompt
    assert CLAIMS not in prompt
    assert THESIS not in prompt


def test_with_no_approval_rule_anywhere_the_prompt_fails_closed(tmp_path):
    """No document states a rule: the prompt says so and forbids external action.

    Silence would read as "there is no such rule", which is the one misreading
    that could cost something irreversible.
    """
    brief = _brief(
        tmp_path,
        reconciliation=None,
        applicant={"applicant": APPLICANT["applicant"]},  # no automation policy
    )

    assert brief.standing_rule is None
    assert any("standing_rule" in b for b in brief.blockers)
    prompt = render_prompt(brief, "draft something")
    assert NO_RULE_READ in prompt
    assert "STANDING RULE: NOT READ" in prompt
    assert "does not authorise" in prompt or "authorises" in prompt


def test_an_unread_statutory_source_is_an_unknown_priority_not_a_clearance(tmp_path):
    """With no reconciliation the blocker is unknown — never absent, never passed."""
    brief = _brief(tmp_path, reconciliation=None, ledger={"active_applications": []})

    statutory = [p for p in brief.live_priorities if "statutory" in p.label]
    assert statutory, "an unreadable statutory source must still be a priority"
    assert statutory[0].severity == "unknown"
    assert statutory[0].days_remaining is None
    assert REGISTRY_BLOCKER not in render_prompt(brief, "x")


# ── 2. days_remaining is measured or None, never filled in ───────────────────


def test_every_priority_carries_a_real_days_remaining_or_none(tmp_path):
    brief = _brief(tmp_path)
    assert brief.live_priorities

    for priority in brief.live_priorities:
        assert isinstance(priority, Priority)
        if priority.days_remaining is None:
            assert priority.overdue is None
            continue
        assert isinstance(priority.days_remaining, float)
        assert priority.overdue is (priority.days_remaining < 0)
        # A placeholder would sit exactly on zero; a measurement almost never does.
        assert priority.days_remaining != 0.0


def test_deadline_days_are_the_ledgers_own_measurement(tmp_path):
    """The dated items match the real interval between NOW and the ledger's dates."""
    brief = _brief(tmp_path)
    by_label = {p.label: p for p in brief.live_priorities}

    overdue = by_label["Overdue Example Call"]
    assert overdue.severity == "overdue"
    assert overdue.days_remaining == pytest.approx(-11.04, abs=0.02)
    assert overdue.overdue is True

    soon = by_label["Imminent Example Call"]
    assert soon.days_remaining == pytest.approx(5.21, abs=0.02)
    assert soon.severity == "urgent"

    # No deadline in the ledger, so no alert and no invented urgency.
    assert "Undated Example Call" not in by_label
    # Closed, so not a priority however near its date.
    assert "Closed Example Call" not in by_label


def test_the_statutory_blocker_is_read_and_its_date_measured(tmp_path):
    """The blocker appears because a document said so, with days from its own date."""
    brief = _brief(tmp_path)
    statutory = next(p for p in brief.live_priorities if "statutory" in p.label)

    assert REGISTRY_BLOCKER in statutory.detail
    assert statutory.severity == "blocker"
    # 2026-05-01 is 91 days before NOW; the figure is derived from the quote.
    assert statutory.days_remaining == pytest.approx(-91.5, abs=0.02)
    assert statutory.overdue is True
    assert statutory.source.endswith(".md")
    # Sorted above the deadlines: a live blocker gates the effort they would take.
    assert brief.live_priorities[0].severity in {"blocker", "unknown"}


def test_a_compliance_finding_with_no_date_carries_none(tmp_path):
    """No date in the quote means no days figure, not a zero."""
    priorities, _sources, _blockers = live_priorities(
        _repo(tmp_path, ledger={"active_applications": [
            {"id": "APP-BARE-0001", "status": "AWAITING_REVIEW", "name": "Bare"},
        ]}),
        now=NOW,
    )
    undated = [p for p in priorities if p.days_remaining is None]
    assert undated, "the evidence-completeness finding carries no date and must say so"
    assert all(p.overdue is None for p in undated)


# ── 3. provenance is structural, not conventional ────────────────────────────


def test_every_sourced_line_names_a_source(tmp_path):
    brief = _brief(tmp_path)
    assert brief.lines

    for line in brief.lines:
        assert isinstance(line, SourcedLine)
        assert line.source.strip()
        assert line.source in line.cite()
    for priority in brief.live_priorities:
        assert priority.source.strip()
    for capability in brief.capabilities_built:
        assert capability.source.strip()


def test_a_line_without_provenance_cannot_be_constructed():
    """The rule is enforced by the type, so it cannot be forgotten downstream."""
    with pytest.raises(ValueError):
        SourcedLine(text="a claim with no file behind it", source="")
    with pytest.raises(ValueError):
        SourcedLine(text="   ", source="COMPANY.md")
    with pytest.raises(ValueError):
        Priority(label="x", detail="d", days_remaining=None, severity="blocker", source="")
    with pytest.raises(ValueError):
        Priority(label="x", detail="d", days_remaining=None, severity="", source="COMPANY.md")


def test_identity_lines_quote_the_documents_they_came_from(tmp_path):
    brief = _brief(tmp_path)
    facts = {line.text: line.source for line in brief.identity}

    assert "company number: ZZ000001" in facts
    assert facts["company number: ZZ000001"].endswith(("autopilot_status.json", "COMPANY.md"))
    assert any(t.startswith("mission:") for t in facts)
    assert any(t.startswith("goal:") for t in facts)


def test_the_markdown_page_cites_every_line(tmp_path):
    page = render_markdown(_brief(tmp_path))
    assert "# Aureon context brief" in page
    assert "Read verbatim from" in page
    for line in _brief(tmp_path).lines:
        assert line.source in page


# ── 4. the two rules survive rendering unchanged ─────────────────────────────


def test_the_standing_rule_and_claim_discipline_are_verbatim_in_the_prompt(tmp_path):
    brief = _brief(tmp_path)
    prompt = render_prompt(brief, "plan the next two weeks against the deadlines")

    assert f"STANDING RULE: {STANDING}" in prompt
    assert f"CLAIM DISCIPLINE: {CLAIMS}" in prompt
    assert f"POSITIONING: {THESIS}" in prompt
    # Verbatim also means unannotated: the auditor's corroboration note must not
    # end up inside the quoted rule.
    assert "(corroborated by" not in brief.standing_rule.text
    # And the citation must sit outside the quote, not inside it.
    assert brief.standing_rule.text.endswith("approval.")
    assert brief.standing_rule.source in prompt
    assert "plan the next two weeks against the deadlines" in prompt


def test_the_rules_are_verbatim_in_the_markdown_page_too(tmp_path):
    page = render_markdown(_brief(tmp_path))
    assert f"> {STANDING}" in page
    assert f"> {CLAIMS}" in page
    assert f"> {THESIS}" in page


def test_the_auditor_fallback_still_yields_a_verbatim_rule(tmp_path, monkeypatch):
    """With the purpose-built quoter unavailable, the rule stays exact.

    The auditor annotates its own finding with ``(corroborated by …)``. That is the
    auditor's sentence, not the owner's, so it is stripped and the source it named
    is kept — otherwise the fallback would quietly paraphrase the one rule that
    must never be paraphrased.
    """
    import aureon.grants.dossier as dossier

    monkeypatch.setattr(dossier, "read_approval_rule", lambda *_a, **_k: None)
    line, sources, blockers, report = standing_rule(_repo(tmp_path), now=NOW)

    assert line is not None and line.text == STANDING
    assert blockers == []
    assert report is not None
    # The corroborating document is preserved rather than dropped with the note.
    assert any("autopilot_status.json" in s for s in sources)
    check = next(c for c in report.checks if c.name == APPROVAL_CHECK)
    assert "(corroborated by" in check.detail, "fixture must exercise the annotation"


def test_an_ask_is_never_invented(tmp_path):
    brief = _brief(tmp_path)
    assert "ASK" not in render_prompt(brief, None)
    assert "ASKS" in render_prompt(brief, ["first ask", "second ask"])
    assert "1. first ask" in render_prompt(brief, ["first ask", "second ask"])


# ── the spine is a reading, and says so when it is not ───────────────────────


def test_the_spine_reports_live_numbers_with_the_organ_that_took_them(tmp_path):
    brief = _brief(tmp_path)
    spine = {line.text: line.source for line in brief.spine}

    gamma = next(t for t in spine if "coherence" in t)
    assert "0.8312" in gamma
    assert spine[gamma] == "aureon/core/hnc_field.py::read_canonical_field"
    assert any("divergence = 0.1204" in t for t in spine)
    assert any("ADVANCE / REDO / HOLD" in t for t in spine)
    assert any("submit" in t and "human-held" in t for t in spine)


def test_an_unreadable_field_says_so_rather_than_going_quiet(tmp_path):
    """A blind reading produces a stated absence in the section and a blocker."""
    lines, _sources, blockers = spine_lines(None, organism_reader=lambda _bus: BLIND)
    text = " ".join(line.text for line in lines)

    assert "not readable in this pass" in text
    assert "not measured in this pass" in text
    assert any("coherence" in b for b in blockers)
    assert any("divergence" in b for b in blockers)
    # No number was invented in place of the missing ones.
    assert "0.0000" not in text


def test_a_reader_that_explodes_becomes_a_blocker_not_a_crash():
    def boom(_bus):
        raise RuntimeError("field organ on fire")

    lines, _sources, blockers = spine_lines(None, organism_reader=boom)
    assert lines == ()
    assert any("RuntimeError" in b for b in blockers)


# ── the capability probe measures, and declines to overstate ──────────────────


def test_the_probe_finds_only_what_is_on_disk(tmp_path):
    root = _repo(tmp_path, package="widgets")
    found, sources, blockers = probe_capabilities(root)

    assert [c.package for c in found] == ["aureon.widgets"]
    assert found[0].test_modules == ("test_example.py",)
    assert sources and "tests/widgets/" in sources[0]
    assert blockers == []
    # This root is not the tree the import system resolves, so importability was
    # not measured — and the record says that rather than guessing either way.
    assert found[0].importable is None
    assert "not measured" in found[0].probe
    assert "importability not measured" in found[0].claim


def test_a_package_with_no_tests_is_not_reported_as_built(tmp_path):
    root = _repo(tmp_path)
    (root / "aureon" / "lonely").mkdir(parents=True)
    (root / "aureon" / "lonely" / "__init__.py").write_text("", encoding="utf-8")
    (root / "tests").mkdir(exist_ok=True)

    found, _sources, blockers = probe_capabilities(root)
    assert found == ()
    assert any("no package" in b for b in blockers)


def test_a_test_file_on_disk_is_never_reported_as_passing(tmp_path):
    root = _repo(tmp_path, package="widgets")
    found, _sources, _blockers = probe_capabilities(root)

    assert found[0].tests_verified is None
    assert "not run in this pass" in found[0].claim
    assert "passing" not in found[0].claim


def test_a_runner_that_actually_ran_is_reported_as_such(tmp_path):
    root = _repo(tmp_path, package="widgets")
    ran: list[str] = []

    def runner(package, test_dir):
        ran.append(package)
        assert test_dir.is_dir()
        return True

    found, _sources, _blockers = probe_capabilities(root, test_runner=runner)
    assert ran == ["widgets"]
    assert found[0].tests_verified is True
    assert "all passing" in found[0].claim

    failing, _s, _b = probe_capabilities(root, test_runner=lambda *_a: False)
    assert failing[0].tests_verified is False
    assert "FAILING" in failing[0].claim

    unknown, _s, _b = probe_capabilities(root, test_runner=lambda *_a: None)
    assert unknown[0].tests_verified is None
    assert "no pass/fail is claimed" in unknown[0].claim


def test_a_runner_that_explodes_is_recorded_not_believed(tmp_path):
    root = _repo(tmp_path, package="widgets")

    def boom(_package, _dir):
        raise OSError("pytest is missing")

    found, _sources, blockers = probe_capabilities(root, test_runner=boom)
    assert found[0].tests_verified is None
    assert any("OSError" in b for b in blockers)


def test_the_capability_claim_never_outruns_the_probe():
    """The sentence a capability renders is exactly what its fields support."""
    measured = Capability(package="aureon.x", test_modules=("test_a.py",), importable=True,
                          probe="find_spec", tests_verified=True, verification="pytest -q tests/x")
    assert "importable" in measured.claim and "all passing" in measured.claim

    absent = Capability(package="aureon.y", test_modules=(), importable=False, probe="find_spec")
    assert "NOT importable" in absent.claim
    assert "0 test modules on disk" in absent.claim
    assert "passing" not in absent.claim


# ── the whole brief holds together ───────────────────────────────────────────


def test_the_brief_reports_which_sections_it_has(tmp_path):
    brief = _brief(tmp_path, package="widgets")

    assert brief.available
    assert set(brief.present) == {
        "identity", "spine", "capabilities_built", "standing_rule",
        "live_priorities", "positioning", "claim_discipline",
    }
    assert brief.omitted == ()
    assert brief.generated_at == NOW
    assert brief.sources
    # Serialisable, because the brief travels: to a file, a bus, an export.
    assert json.dumps(brief.to_dict())


def test_an_injected_runner_reaches_the_capability_section(tmp_path):
    """The verification path is plumbed end to end, not only inside the probe."""
    brief = assemble_brief(
        _repo(tmp_path, package="widgets"),
        now=NOW,
        organism_reader=lambda _b: READING,
        test_runner=lambda _package, _dir: True,
    )
    assert [c.tests_verified for c in brief.capabilities_built] == [True]
    assert "all passing" in render_prompt(brief, "x")


def test_a_broken_ledger_is_a_blocker_and_the_rest_still_assembles(tmp_path):
    root = _repo(tmp_path)
    (root / "data" / "research" / "grants" / "pipeline.json").write_text("{ not json",
                                                                        encoding="utf-8")
    brief = assemble_brief(root, now=NOW, organism_reader=lambda _b: READING)

    assert any("pipeline" in b.lower() for b in brief.blockers)
    # The rules were still read; one unreadable source does not silence the brief.
    assert brief.standing_rule is not None and brief.standing_rule.text == STANDING
    assert brief.claim_discipline is not None
    assert not any(p.source.endswith("pipeline.json") and p.severity == "overdue"
                   for p in brief.live_priorities)


def test_assemble_brief_never_raises_on_a_hostile_root(tmp_path):
    """A file where a directory belongs, a directory where a file belongs."""
    root = tmp_path / "hostile"
    root.mkdir()
    (root / "COMPANY.md").mkdir()  # a directory wearing a document's name
    (root / "data").write_text("not a directory", encoding="utf-8")

    brief = assemble_brief(root, now=NOW, organism_reader=lambda _b: READING)
    assert brief.blockers
    assert brief.standing_rule is None
    assert json.dumps(brief.to_dict())
