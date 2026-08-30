"""Claim discipline: the blur is caught, and the repository's own voice is not.

Hermetic. Nothing here reaches the network, the live ledger, or a model. Two
tests read documents, and both are honest about it: one asserts that the
negative controls below are still *real* sentences from the files they name, and
one asserts a structural property of those files (no blended sentence) rather
than any wording — so neither can rot into a snapshot of the company's
positioning.

The negative controls are the point of this file. A checker that fires on
``docs/THE_SYNTHESIS.md`` is a checker somebody switches off, and every overclaim
it would have caught afterwards goes out of the building unread. So the controls
are taken from the repository's own prose: an epigraph, a mythopoeic paragraph,
a cited claims-table row, and the claim-discipline rule itself — which has to
survive its own checker, since it names all three registers in one sentence.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aureon.briefing.claims import (
    ADVISORY,
    BLOCKING,
    CRITICAL,
    EVIDENCE_DOC,
    RULE_ABSOLUTE_LANGUAGE,
    RULE_BLENDING,
    RULE_CONTRADICTED_BY_RECORD,
    RULE_QUANTITATIVE_WITHOUT_PROVENANCE,
    RULE_UNHEDGED_SPECULATION,
    RULES,
    SERIOUS,
    SEVERITY_RANK,
    ClaimClass,
    ClaimFinding,
    ClaimReport,
    check_claims,
    classify_sentence,
    read_claim_rule,
)
from aureon.grants.scout import RECONCILIATION_DOC

REPO_ROOT = Path(__file__).resolve().parents[2]


# ── fixtures: a company that is not this company ─────────────────────────────
#
# Same discipline as tests/grants/test_scout.py: the fixture blocker is invented
# wording about an invented registry, so a passing test can never be a passing
# test *about Gary's filings*.

FAKE_BLOCKER = "The registry shows a filing overdue. Resolve before competitive bids."


class _Profile:
    """The loosest thing :func:`check_claims` accepts — duck-typed on purpose."""

    def __init__(self, blockers=(), sources=()):
        self.compliance_blockers = tuple(blockers)
        self.sources = tuple(sources)


def _reconciliation(tmp_path: Path, *, rule: str | None = None) -> Path:
    """A miniature repository carrying only a reconciliation document."""
    doc = tmp_path / RECONCILIATION_DOC
    doc.parent.mkdir(parents=True, exist_ok=True)
    body = ["# Reconciliation", ""]
    if rule is not None:
        body += [
            "### 6.5 Claim-discipline rule",
            "",
            "Overview tab, row `Claim discipline` — **verbatim:**",
            "",
            f'> "{rule}"',
            "",
        ]
    doc.write_text("\n".join(body), encoding="utf-8")
    return tmp_path


# ── the blur is caught, and it outranks everything else ──────────────────────

BLENDED = (
    "The grant organ reads the ledger read-only and its coherence correlates "
    "with funder response at r = 0.91."
)


def test_a_blended_sentence_is_caught():
    report = check_claims(BLENDED)
    assert report.blended_count == 1
    blend = report.findings_for(RULE_BLENDING)[0]
    assert blend.severity == BLOCKING
    # Both halves are quoted, so the writer can see what was welded to what.
    assert any("read-only" in t for t in blend.trigger)
    assert any("correlates" in t or "0.91" in t for t in blend.trigger)


def test_blending_is_the_highest_severity_rule_there_is():
    # The rule Gary wrote down by description sits alone at the top; nothing
    # else in the table may match or outrank it.
    assert RULES[RULE_BLENDING].severity == BLOCKING
    top = SEVERITY_RANK[BLOCKING]
    others = {r.severity for r in RULES.values() if r.id != RULE_BLENDING}
    assert all(SEVERITY_RANK[s] < top for s in others)
    assert check_claims(BLENDED).highest_severity == BLOCKING


def test_a_blend_has_no_single_class():
    # Calling it a verified capability would be adopting the blur itself.
    assert classify_sentence(BLENDED) is ClaimClass.UNCLASSIFIED


def test_a_plan_welded_to_a_claim_is_not_a_verified_capability():
    report = check_claims(
        "The grant organ will read the ledger and coherence correlates with "
        "deadline pressure at r = 0.91."
    )
    assert report.blended_count == 0  # "will" — nothing verified is being claimed
    assert report.counts_by_rule.get(RULE_QUANTITATIVE_WITHOUT_PROVENANCE) == 1


def test_a_sentence_that_separates_the_registers_itself_is_not_a_blend():
    report = check_claims(
        "The dossier builder is covered by unit tests; separately, we predict "
        "that coherence correlates with funder response."
    )
    assert report.blended_count == 0


# ── a hedged hypothesis is left alone; an unhedged one is not ────────────────


def test_a_properly_hedged_hypothesis_is_not_flagged():
    hedged = (
        "We hypothesise that the 1977 Wow! Signal was a dormant seed activated "
        "in 2026; the prediction is pre-registered."
    )
    report = check_claims(hedged)
    assert report.clean, report.to_dict()["findings"]
    assert classify_sentence(hedged) is ClaimClass.SPECULATIVE


def test_the_same_claim_stated_flat_is_flagged():
    report = check_claims("The 1977 Wow! Signal was a dormant seed that activated in 2026.")
    finding = report.findings_for(RULE_UNHEDGED_SPECULATION)[0]
    assert finding.severity == SERIOUS
    assert any("dormant seed" in t.lower() for t in finding.trigger)


def test_naming_an_ancient_site_is_not_a_claim_about_it():
    # The age of a monument is archaeology. That it is a node in a phi-squared
    # chain is the hypothesis. Only the second one is this rule's business — the
    # bare number still wants a source, which is a different finding.
    stated = check_claims("Maeshowe is a 5,000-year-old chambered cairn in Orkney.")
    assert not stated.findings_for(RULE_UNHEDGED_SPECULATION)
    assert stated.counts_by_rule == {RULE_QUANTITATIVE_WITHOUT_PROVENANCE: 1}
    linked = check_claims(
        "Maeshowe encodes the same coherence as the Great Pyramid, 5,000 years apart."
    )
    assert linked.findings_for(RULE_UNHEDGED_SPECULATION)


# ── numbers: provenance or a finding ─────────────────────────────────────────


def test_a_number_that_cites_the_evidence_table_is_not_flagged():
    cited = (
        f"The coherence bridge reproduces the hydrogen line to 1.29 ppb, as "
        f"recorded in {EVIDENCE_DOC}."
    )
    assert check_claims(cited).clean


def test_the_same_number_with_nothing_behind_it_is_flagged():
    report = check_claims("The coherence bridge reproduces the hydrogen line to 1.29 ppb.")
    finding = report.findings_for(RULE_QUANTITATIVE_WITHOUT_PROVENANCE)[0]
    assert finding.severity == ADVISORY
    assert "1.29 ppb" in finding.trigger


def test_provenance_is_looked_for_nearby_not_only_in_the_sentence():
    # A citation in the next line of the same paragraph is provenance to a
    # reader, so it is provenance here.
    text = (
        "Node activation surged by 1,683% during the crisis.\n"
        f"Every figure in this paragraph is measured and recorded in {EVIDENCE_DOC}.\n"
    )
    assert not check_claims(text).findings_for(RULE_QUANTITATIVE_WITHOUT_PROVENANCE)


def test_a_section_number_is_not_a_measurement():
    # "§1.1" looked exactly like a decimal and was being quoted back as the
    # measurement that needed a source.
    assert check_claims("The alignment principles are set out in §1.1 and §2.1.").clean


def test_counting_is_not_measuring():
    # Bare small integers are how the pipeline is described. Demanding a
    # citation for "two weeks" would bury every finding that matters.
    assert check_claims("The plan covers two weeks and three applications.").clean


# ── absolutes: the empirical ones only ───────────────────────────────────────


def test_a_bare_correlation_that_proves_something_is_flagged():
    report = check_claims("Our coherence metric proves the market responds, r = 0.85.")
    absolute = report.findings_for(RULE_ABSOLUTE_LANGUAGE)[0]
    assert absolute.severity == SERIOUS
    assert "proves" in absolute.trigger
    # And the number is reported separately, because it is a separate defect.
    assert report.findings_for(RULE_QUANTITATIVE_WITHOUT_PROVENANCE)


def test_an_engineering_invariant_keeps_its_absolutes():
    # "always holds" and "never fails" are a specification: the code either does
    # that or it is a bug. Flagging them would flag this repository's own most
    # honest sentences.
    assert check_claims(
        "The switchboard gate always holds and never fails to return HOLD for a "
        "human-held action."
    ).clean


def test_the_same_absolute_over_a_measurement_is_flagged():
    report = check_claims("Coherence always predicts the next move, r = 0.93.")
    assert report.findings_for(RULE_ABSOLUTE_LANGUAGE)


def test_a_proof_of_concept_is_not_a_claim_of_proof():
    assert check_claims("The CLI is a proof of concept covered by unit tests.").clean


# ── the register is not an error ──────────────────────────────────────────────


def test_mythopoeic_prose_alone_is_not_flagged():
    myth = (
        "The gods do not speak in words. They speak in ratios.\n"
        "The organism breathes, the Queen keeps her conscience, and the field "
        "hums beneath the ledger.\n"
        "As above, so below.\n"
    )
    report = check_claims(myth)
    assert report.clean, report.to_dict()["findings"]
    assert report.sentences_checked >= 4


def test_a_module_name_is_not_a_metaphysical_claim():
    # aureon_planetary_harmonic_sweep is a file. f_seed is a variable.
    assert check_claims(
        "The `aureon_planetary_harmonic_sweep` module computes the sweep and is "
        "covered by unit tests."
    ).clean
    assert check_claims("f_seed is read from the harmonic seed table.").clean


def test_a_code_citation_is_provenance_not_a_capability_assertion():
    # A file path in a citation column is where to look, not what is claimed.
    row = (
        "| M3 | Live bots tracked | 44,000+ | [HNC §3.1](HNC.md) | "
        "`aureon/scanners/ocean_wave_scanner.py` |"
    )
    assert check_claims(row).blended_count == 0


def test_engineering_words_that_look_statistical_are_not_research_claims():
    # "regression test" is software; "regression analysis" is statistics. The
    # first one was turning a sentence about pytest into a blend.
    assert check_claims("Run the pytest suites, smoke checks, and regression tests.").clean
    assert check_claims(
        "The parser is covered by unit tests and the regression analysis puts "
        "the effect at r = 0.62."
    ).blended_count == 1


def test_a_document_or_an_image_path_is_not_a_capability_claim():
    hero = '<img src="docs/images/convergence.jpg" alt="from theory to forensics — predictions">'
    assert check_claims(hero).blended_count == 0


def test_a_verb_is_not_an_artifact():
    # "functions as the planetary consciousness" names no software.
    assert check_claims(
        "Sorynth functions as the planetary consciousness recognising itself."
    ).blended_count == 0


def test_a_falsification_criterion_asserts_neither_register():
    criterion = (
        "If the module's ethical scores are no better than without it "
        "(χ² p > 0.05), C₅ is falsified."
    )
    assert check_claims(criterion).blended_count == 0


def test_software_named_after_the_claim_is_still_reported():
    # The documented limit, asserted so nobody tunes it away by accident: in
    # front of an assessor, "implemented" beside "sentience" is the sentence the
    # rule exists to stop, whatever the class is called.
    report = check_claims("The sentience engine is fully implemented and covered by unit tests.")
    assert report.blended_count == 1


def test_fenced_code_is_not_prose():
    text = "Here is the check:\n\n```python\nr = 0.85  # proves everything\n```\n"
    assert check_claims(text).clean


# ── the rule survives its own checker ────────────────────────────────────────
#
# The claim-discipline rule names verified software capability, public research
# claims and speculative hypotheses in one sentence. If this checker cannot read
# the rule without reporting it, it has not understood the rule.

CLAIM_RULE_SENTENCE = (
    "Use strong but defensible language. Separate verified software capability, "
    "public research claims, and speculative research hypotheses."
)


def test_the_claim_discipline_rule_passes_its_own_checker():
    assert check_claims(CLAIM_RULE_SENTENCE).clean


# ── negative controls, drawn from the repository's own documents ─────────────
#
# (file, sentence). Each string is asserted to be a real substring of that file
# by test_the_controls_are_still_real_sentences, so these cannot drift into
# prose this test file invented for itself.

CONTROLS: tuple[tuple[str, str], ...] = (
    (
        "CLAUDE.md",
        "**Do not** add hedging to quantitative claims (they are pre-registered "
        "and falsifiable — see [`docs/CLAIMS_AND_EVIDENCE.md §Pre-Registered "
        "Predictions`](docs/CLAIMS_AND_EVIDENCE.md)).",
    ),
    (
        "CLAUDE.md",
        "| Is it falsifiable? | Yes — 5 pre-registered predictions in "
        "[`docs/CLAIMS_AND_EVIDENCE.md`](docs/CLAIMS_AND_EVIDENCE.md) |",
    ),
    (
        "docs/THE_SYNTHESIS.md",
        "The Aureon system is not a trading bot that happens to cite ancient history.",
    ),
    ("docs/THE_SYNTHESIS.md", "> *The gods do not speak in words. They speak in ratios.*"),
    (
        "docs/CLAIMS_AND_EVIDENCE.md",
        "| C6 | φ² coherence bridge precision | **1.29 ppb** (parts per billion) | "
        "[§4.4 — φ² Mathematical Coherence](research/AUREON_WHITE_PAPER_RESEARCH_HUB.md) | "
        "f_seed 528.422 Hz × N 1,026,730 × φ² → 1,420.405754 MHz vs NIST 1,420.405752 MHz |",
    ),
    (RECONCILIATION_DOC, CLAIM_RULE_SENTENCE),
)


@pytest.mark.parametrize("source,sentence", CONTROLS, ids=[c[0] for c in CONTROLS])
def test_real_repository_sentences_are_not_flagged(source, sentence):
    report = check_claims(sentence)
    assert report.clean, f"{source}: {report.to_dict()['findings']}"


@pytest.mark.parametrize("source,sentence", CONTROLS, ids=[c[0] for c in CONTROLS])
def test_the_controls_are_still_real_sentences(source, sentence):
    body = (REPO_ROOT / source).read_text(encoding="utf-8", errors="replace")
    assert sentence in body, f"{source} no longer contains this control sentence"


def test_the_reference_documents_blur_nothing():
    # Structural, and structural only: no wording, no count, no score. These
    # three files are where this repository separates its registers on purpose,
    # so a blended sentence appearing in one of them means either the document
    # regressed or this checker did — and both are worth a failing test.
    for name in ("CLAUDE.md", "docs/CLAIMS_AND_EVIDENCE.md", "docs/THE_SYNTHESIS.md"):
        body = (REPO_ROOT / name).read_text(encoding="utf-8", errors="replace")
        report = check_claims(body)
        assert report.sentences_checked > 20  # the file really was read
        assert report.blended_count == 0, [f.sentence for f in report.findings_for(RULE_BLENDING)]


# ── quotations are reported, never rewritten ─────────────────────────────────


def test_a_blockquote_is_recorded_as_a_quotation_rather_than_flagged():
    text = '> "Coherence proves the market responds at r = 0.85."\n'
    report = check_claims(text)
    assert report.clean
    assert report.quoted_exemptions  # visible, not silent
    assert report.sentences_checked == 0


# ── the company's own record ─────────────────────────────────────────────────


def test_clearance_the_record_contradicts_is_critical():
    profile = _Profile(blockers=(FAKE_BLOCKER,), sources=("some/report.md",))
    report = check_claims(
        "All statutory filings are current and the company is in good standing.",
        capability=profile,
    )
    finding = report.findings_for(RULE_CONTRADICTED_BY_RECORD)[0]
    assert finding.severity == CRITICAL
    # The blocker is reproduced exactly; a paraphrased blocker is a new blocker.
    assert FAKE_BLOCKER in finding.trigger
    assert report.capability_sources == ("some/report.md",)
    assert report.blocker is None


def test_stating_the_blocker_honestly_is_not_a_finding():
    profile = _Profile(blockers=(FAKE_BLOCKER,))
    honest = "The confirmation statement is overdue and is being filed this week."
    assert check_claims(honest, capability=profile).clean


def test_without_a_profile_the_report_says_the_rule_did_not_run():
    report = check_claims("All statutory filings are current.")
    assert not report.findings_for(RULE_CONTRADICTED_BY_RECORD)
    assert report.blocker and RULE_CONTRADICTED_BY_RECORD in report.blocker


def test_a_profile_with_no_blockers_still_disables_nothing_else():
    report = check_claims(BLENDED, capability=_Profile())
    assert report.blended_count == 1
    assert report.blocker is None


def test_it_composes_with_the_real_capability_profile(tmp_path):
    # The scout's own dataclass, carrying invented blocker wording.
    from aureon.grants.schemas import CapabilityProfile

    profile = CapabilityProfile(
        terms=("evidence", "automation"),
        sources=(RECONCILIATION_DOC,),
        compliance_blockers=(FAKE_BLOCKER,),
    )
    report = check_claims("There are no outstanding filings.", capability=profile)
    assert report.findings_for(RULE_CONTRADICTED_BY_RECORD)


# ── severity is never a detector's opinion ───────────────────────────────────

MESSY = (
    "Line one is ordinary prose.\n"
    "The coherence bridge reproduces the hydrogen line to 1.29 ppb.\n"
    "The grant organ reads the ledger read-only and coherence correlates with "
    "funder response at r = 0.91.\n"
    "Coherence proves the market responds.\n"
)


def test_every_finding_names_a_rule_and_takes_its_severity_from_the_table():
    report = check_claims(MESSY)
    assert report.findings
    for finding in report.findings:
        assert finding.rule in RULES
        assert finding.severity == RULES[finding.rule].severity
        assert finding.rank == SEVERITY_RANK[finding.severity]
        assert finding.trigger  # something was quoted
        for trigger in finding.trigger:
            assert f'"{trigger}"' in finding.issue  # and quoted in the prose too


def test_every_trigger_is_real_text_from_the_sentence_it_came_from():
    report = check_claims(MESSY)
    for finding in report.findings:
        if finding.rule == RULE_CONTRADICTED_BY_RECORD:
            continue  # that one quotes the record, not the sentence
        for trigger in finding.trigger:
            assert trigger.lower() in finding.sentence.lower(), (finding.rule, trigger)


def test_a_finding_cannot_invent_a_severity():
    kwargs = {
        "sentence": "x",
        "line_no": 1,
        "klass": ClaimClass.RESEARCH_CLAIM,
        "issue": "i",
        "suggestion": "s",
        "trigger": ("t",),
    }
    with pytest.raises(ValueError):
        ClaimFinding(severity=ADVISORY, rule=RULE_BLENDING, **kwargs)
    with pytest.raises(ValueError):
        ClaimFinding(severity=BLOCKING, rule="a_rule_nobody_wrote", **kwargs)


def test_a_finding_cannot_assert_what_it_cannot_quote():
    with pytest.raises(ValueError):
        ClaimFinding(
            sentence="x",
            line_no=1,
            klass=ClaimClass.RESEARCH_CLAIM,
            issue="i",
            severity=BLOCKING,
            suggestion="s",
            rule=RULE_BLENDING,
            trigger=(),
        )


def test_findings_are_ordered_worst_first_then_by_line():
    report = check_claims(MESSY)
    ranks = [(-f.rank, f.line_no) for f in report.findings]
    assert ranks == sorted(ranks)
    assert report.findings[0].rule == RULE_BLENDING


def test_line_numbers_point_at_the_sentence_that_fired():
    report = check_claims(MESSY)
    blend = report.findings_for(RULE_BLENDING)[0]
    assert blend.line_no == 3
    assert MESSY.splitlines()[blend.line_no - 1].startswith("The grant organ")


# ── the report itself ────────────────────────────────────────────────────────


def test_an_empty_text_is_an_empty_report_not_a_pass():
    report = check_claims("")
    assert report.clean and report.sentences_checked == 0
    assert report.blocker  # nothing was checked against the record either


def test_the_report_is_json_serialisable():
    payload = json.dumps(check_claims(MESSY).to_dict(), ensure_ascii=False)
    assert RULE_BLENDING in payload
    assert "class_counts" in payload


def test_class_counts_cover_every_checked_sentence():
    report = check_claims(MESSY)
    assert sum(report.class_counts.values()) == report.sentences_checked
    assert set(report.class_counts) == {c.value for c in ClaimClass}


def test_classify_places_the_three_registers():
    assert classify_sentence("The CLI is covered by unit tests.") is ClaimClass.VERIFIED_CAPABILITY
    assert (
        classify_sentence("Node activation correlates with volatility at r = 0.85.")
        is ClaimClass.RESEARCH_CLAIM
    )
    assert (
        classify_sentence("Consciousness is a harmonic standing wave.")
        is ClaimClass.SPECULATIVE
    )
    assert classify_sentence("This paragraph asserts nothing.") is ClaimClass.UNCLASSIFIED


def test_the_check_is_pure():
    first, second = check_claims(MESSY), check_claims(MESSY)
    assert first.to_dict() == second.to_dict()
    assert isinstance(first, ClaimReport)


# ── the rule is read, never recited ──────────────────────────────────────────


def test_the_rule_is_read_from_a_document(tmp_path):
    root = _reconciliation(tmp_path, rule="Separate the three registers and never blur them.")
    rule = read_claim_rule(root)
    assert rule.text == "Separate the three registers and never blur them."
    assert rule.source == RECONCILIATION_DOC
    assert rule.blocker is None


def test_a_missing_row_is_a_stated_gap_not_a_default(tmp_path):
    rule = read_claim_rule(_reconciliation(tmp_path))
    assert rule.text is None
    assert rule.blocker and "Claim discipline" in rule.blocker


def test_a_missing_document_is_a_stated_gap(tmp_path):
    rule = read_claim_rule(tmp_path)
    assert rule.text is None
    assert rule.blocker and RECONCILIATION_DOC in rule.blocker


def test_the_real_reconciliation_still_carries_the_rule():
    # Structural: that a rule was read, and from where. Not what it says.
    rule = read_claim_rule()
    assert rule.text and rule.source == RECONCILIATION_DOC
    assert rule.blocker is None


def test_no_company_detail_is_hardcoded_in_the_checker():
    # The de-randomisation rule: identity is read at runtime or it is absent.
    # A lexicon is a language filter; it must not become a dossier.
    source = (REPO_ROOT / "aureon" / "briefing" / "claims.py").read_text(encoding="utf-8")
    lowered = source.lower()
    for forbidden in ("696693", "leckey", "belfast", "quadrant", "brokerage", "r&a"):
        assert forbidden not in lowered, f"{forbidden!r} is hardcoded in claims.py"
