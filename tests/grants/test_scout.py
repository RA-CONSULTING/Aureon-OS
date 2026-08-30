"""The grant scout: provenance is mandatory, absence is never a number.

Hermetic. Every capability profile is built from documents written into
``tmp_path``, and every retrieval goes through a fake fetcher, so nothing here
touches the network, the live ledger, or the repository's real COMPANY.md. The
one test that does read the real documents asserts only structural facts about
them (that the thesis row exists and no company detail was hardcoded), never a
score, so it cannot rot into a snapshot of the company's positioning.
"""

from __future__ import annotations

from datetime import UTC, datetime, timezone
from pathlib import Path

import pytest

from aureon.gates.switchboard import ADVANCE, HOLD, REDO, GateReading, is_human_held
from aureon.grants.schemas import CapabilityProfile, Opportunity
from aureon.grants.scout import (
    PURSUE_ACTION,
    RECONCILIATION_DOC,
    SOURCE_DEGRADED_SEARCH,
    assess,
    read_capability,
    score_fit,
    scout,
)

NOW = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)
REPO_ROOT = Path(__file__).resolve().parents[2]

# A call text that shares vocabulary with the fixture profile below.
CALL_TEXT = """AI Evidence Systems Fund
The fund supports automation and research validation in fintech and logistics.
Applicants must hold a current safeguarding certificate.
Deadline: 12 August 2026.
Awards of up to £150,000 per project.
"""


# ── fixtures: a repository root that is not this repository ──────────────────


def _repo(tmp_path, *, company=True, synthesis=True, thesis=True, blocker=True):
    """Write a miniature repo whose documents contain no real company data."""
    if company:
        (tmp_path / "COMPANY.md").write_text(
            "# Example Holdings\n\n## Company\n\n| x | y |\n\n"
            "## What the company builds\n\n"
            "A grounded automation platform for evidence-heavy research validation.\n",
            encoding="utf-8",
        )
    if synthesis:
        docs = tmp_path / "docs"
        docs.mkdir(exist_ok=True)
        (docs / "THE_SYNTHESIS.md").write_text(
            "# Synthesis\n\n## Something Else\n\nIgnore me.\n\n"
            "## What This Repository Is\n\nA logistics and fintech evidence system.\n",
            encoding="utf-8",
        )
    recon = tmp_path / RECONCILIATION_DOC
    recon.parent.mkdir(parents=True, exist_ok=True)
    body = ["# Reconciliation", ""]
    if thesis:
        body += ["### 6.4 Primary grant thesis", "",
                 "Overview tab, row `Primary grant thesis` — **verbatim:**", "",
                 '> "Example is positioned as an evidence platform for automation."', ""]
    if blocker:
        body += ["### 6.1 Registry blocker", "",
                 "Overview tab, row `Compliance blocker` — **verbatim:**", "",
                 '> "The registry shows a filing overdue. Resolve before competitive bids."', ""]
    recon.write_text("\n".join(body), encoding="utf-8")
    return tmp_path


def _fetcher(text="", *, success=True, error=None, status=200):
    def fetch(url):
        if success:
            return {"success": True, "url": url, "status_code": status, "text": text}
        return {"success": False, "url": url, "error": error or "boom"}

    return fetch


def _opportunity(**kw):
    base = {
        "id": "OPP-TEST",
        "title": "t",
        "funder": "f",
        "url": "https://example.test/call",
        "deadline": None,
        "max_award": None,
        "currency": "",
        "source": "web_fetch:https://example.test/call",
        "discovered_at": NOW,
        "text": CALL_TEXT,
    }
    base.update(kw)
    return Opportunity(**base)


# ── provenance is structural, not a convention ───────────────────────────────


def test_opportunity_cannot_exist_without_a_source():
    # The whole point of the field: an unsourced row is indistinguishable from a
    # sourced one by the time anyone reads it, so it must not be constructible.
    with pytest.raises(ValueError, match="source is mandatory"):
        _opportunity(source="")
    with pytest.raises(ValueError, match="id is mandatory"):
        _opportunity(id="   ")


def test_every_scouted_opportunity_carries_provenance(tmp_path):
    found = scout(
        ["https://example.test/a", {"url": "https://example.test/b", "id": "FUNDER-REF-9"}],
        fetcher=_fetcher(CALL_TEXT),
        now=NOW,
    )
    assert len(found) == 2
    assert all(o.source for o in found)
    assert all(o.url in o.source or o.source == SOURCE_DEGRADED_SEARCH for o in found)
    assert all(o.discovered_at == NOW for o in found)
    # A caller-supplied funder reference is kept; a derived handle is obviously
    # derived and cannot be mistaken for a funder's own id.
    assert found[1].id == "FUNDER-REF-9"
    assert found[0].id.startswith("OPP-")


def test_failed_retrieval_still_returns_a_row_with_the_error(tmp_path):
    found = scout(["https://example.test/a"], fetcher=_fetcher(success=False, error="404"), now=NOW)
    # Dropping it would turn "we could not read this call" into an absence.
    assert len(found) == 1
    assert found[0].retrieved is False and found[0].retrieval_error == "404"
    assert found[0].deadline is None and found[0].max_award is None


def test_the_default_fetcher_is_the_real_web_fetch_tool(monkeypatch):
    """The default path must reach the tool registry, not a stub.

    Asserted by substitution rather than by calling the real tool: importing
    the registry pulls in the agent core, and this repo's rule is that an
    unguarded aureon import can flip live-trading flags. Proving the default
    is wired is worth a test; proving it by loading the trading stack is not.
    """
    import importlib

    # NOT ``import aureon.grants.scout as scout_mod``: the package re-exports the
    # ``scout`` *function*, which shadows the submodule attribute of the same
    # name, so that form binds the function and monkeypatching it fails with a
    # bewildering AttributeError. importlib goes to sys.modules and gets the
    # module. See the note in aureon/grants/__init__.py.
    scout_mod = importlib.import_module("aureon.grants.scout")

    seen: list[str] = []

    def spy(url):
        seen.append(url)
        return {"success": True, "url": url, "status_code": 200, "text": "x"}

    monkeypatch.setattr(scout_mod, "_registry_fetch", spy)
    found = scout_mod.scout(["https://x.test"], now=NOW)  # no fetcher argument
    assert seen == ["https://x.test"] and found[0].retrieved


def test_a_raising_fetcher_does_not_end_the_run():
    def boom(url):
        raise RuntimeError("network down")

    found = scout(["https://a.test", "https://b.test"], fetcher=boom, now=NOW)
    assert len(found) == 2
    assert all("network down" in (o.retrieval_error or "") for o in found)


# ── the degraded search path is flagged, always ──────────────────────────────


def test_search_discovered_results_are_flagged_degraded():
    # web_search silently returns a hardcoded developer-docs catalogue when the
    # scrape is blocked, so anything discovered through it must be discountable.
    found = scout(
        [{"url": "https://docs.python.org/3/", "via": "web_search"}],
        fetcher=_fetcher(CALL_TEXT),
        now=NOW,
    )
    assert found[0].source == SOURCE_DEGRADED_SEARCH


def test_degradation_survives_a_successful_fetch(tmp_path):
    # The fetch is genuine; what is in doubt is whether the URL belonged in the
    # list at all. A real fetch must not launder a degraded discovery.
    profile = read_capability(_repo(tmp_path))
    found = scout([{"url": "https://x.test", "via": "duckduckgo"}], fetcher=_fetcher(CALL_TEXT), now=NOW)
    fit = score_fit(found[0], profile)
    assert found[0].retrieved is True
    assert found[0].source == SOURCE_DEGRADED_SEARCH
    assert any("DEGRADED" in e for e in fit.evidence)


def test_directly_fetched_results_are_not_flagged_degraded(tmp_path):
    profile = read_capability(_repo(tmp_path))
    found = scout(["https://x.test"], fetcher=_fetcher(CALL_TEXT), now=NOW)
    fit = score_fit(found[0], profile)
    assert found[0].source != SOURCE_DEGRADED_SEARCH
    assert not any("DEGRADED" in e for e in fit.evidence)


# ── an unretrieved call scores None with a blocker, never a number ───────────


def test_unretrieved_call_scores_none_with_a_blocker(tmp_path):
    profile = read_capability(_repo(tmp_path))
    found = scout(["https://example.test/a"], fetcher=_fetcher(success=False, error="timed out"), now=NOW)
    fit = score_fit(found[0], profile)
    assert fit.score is None
    assert fit.blocker and "timed out" in fit.blocker and "example.test" in fit.blocker
    assert fit.matched_terms == ()


def test_empty_capability_profile_scores_none_not_zero(tmp_path):
    empty = read_capability(tmp_path)  # an empty directory, honoured verbatim
    assert empty.available is False and empty.blocker
    fit = score_fit(_opportunity(), empty)
    assert fit.score is None and fit.blocker


def test_a_read_call_with_no_overlap_scores_real_zero(tmp_path):
    profile = read_capability(_repo(tmp_path))
    fit = score_fit(_opportunity(text="Zebra husbandry bursary. Apply early."), profile)
    # Zero is a measurement — the call was read and shares nothing. It must not
    # be conflated with None, which means nothing was measured at all.
    assert fit.score == 0.0 and fit.blocker is None
    assert fit.matched_terms == ()


def test_score_is_the_stated_ratio(tmp_path):
    profile = CapabilityProfile(terms=("automation", "evidence", "logistics", "zebra"),
                                sources=("fixture",))
    fit = score_fit(_opportunity(text="Automation and evidence in logistics."), profile)
    assert fit.matched_terms == ("automation", "evidence", "logistics")
    assert fit.score == pytest.approx(3 / 4)
    assert any("3/4" in e for e in fit.evidence)


# ── the capability profile is read, never hardcoded ──────────────────────────


def test_profile_comes_from_documents_not_from_source(tmp_path):
    profile = read_capability(_repo(tmp_path))
    assert profile.available
    assert "automation" in profile.terms and "logistics" in profile.terms
    assert profile.thesis == "Example is positioned as an evidence platform for automation."
    # Nothing about the real company leaked in from the package source.
    assert not any(t in profile.terms for t in ("aureon", "consulting", "brokerage"))


def test_a_missing_document_is_a_stated_gap_not_a_fallback(tmp_path):
    profile = read_capability(_repo(tmp_path, synthesis=False))
    assert profile.available  # the other two still read
    assert profile.blocker and "THE_SYNTHESIS.md" in profile.blocker
    assert "docs/THE_SYNTHESIS.md" not in profile.sources


def test_empty_root_does_not_fall_back_to_the_real_repository(tmp_path):
    profile = read_capability(tmp_path)
    assert profile.terms == () and profile.sources == ()
    assert profile.blocker and str(tmp_path) in profile.blocker


def test_compliance_blocker_is_carried_verbatim_into_missing_requirements(tmp_path):
    profile = read_capability(_repo(tmp_path))
    assert profile.compliance_blockers == (
        "The registry shows a filing overdue. Resolve before competitive bids.",
    )
    fit = score_fit(_opportunity(), profile)
    # Reproduced exactly, with its source attached — a paraphrased constraint
    # would be a different constraint.
    assert any(
        r == f"compliance ({RECONCILIATION_DOC}): "
        "The registry shows a filing overdue. Resolve before competitive bids."
        for r in fit.missing_requirements
    )


def test_uncovered_requirement_sentences_are_quoted_from_the_call(tmp_path):
    profile = read_capability(_repo(tmp_path))
    fit = score_fit(_opportunity(), profile)
    quoted = [r for r in fit.missing_requirements if r.startswith("call text: ")]
    assert any("safeguarding certificate" in r for r in quoted)
    # Every quoted requirement is a real substring of the call, not a summary.
    assert all(r[len("call text: "):] in " ".join(CALL_TEXT.split()) for r in quoted)


def test_the_real_repository_documents_parse_or_report_the_operational_gap():
    # Structural only: the tracked identity documents must parse. The operational
    # reconciliation may be mounted locally, but a clean clone must fail closed
    # rather than importing ledger evidence merely to make this test green.
    profile = read_capability()
    assert profile.available and profile.terms
    joined = " ".join(profile.sources)
    for expected in ("COMPANY.md", "THE_SYNTHESIS.md"):
        assert expected in joined, f"{expected} missing from sources: {profile.sources}"

    if (REPO_ROOT / RECONCILIATION_DOC).is_file():
        assert profile.thesis and profile.compliance_blockers
        for expected in ("grant thesis", "compliance blockers"):
            assert expected in joined, f"{expected} missing from sources: {profile.sources}"
        assert profile.blocker is None
    else:
        assert profile.thesis is None and not profile.compliance_blockers
        assert profile.blocker and RECONCILIATION_DOC in profile.blocker


# ── extraction refuses to guess ──────────────────────────────────────────────


def test_deadline_needs_a_deadline_word_and_an_unambiguous_date():
    found = scout(["https://x.test"], fetcher=_fetcher("Deadline: 12 August 2026.\n"), now=NOW)
    assert found[0].deadline == datetime(2026, 8, 12, tzinfo=UTC)

    # A bare date with no deadline word is not a deadline.
    loose = scout(["https://x.test"], fetcher=_fetcher("Published 12 August 2026.\n"), now=NOW)
    assert loose[0].deadline is None

    # DD/MM vs MM/DD is unresolvable across UK and US calls, so it is refused.
    ambiguous = scout(["https://x.test"], fetcher=_fetcher("Deadline: 12/08/2026\n"), now=NOW)
    assert ambiguous[0].deadline is None


def test_programme_total_is_not_read_as_a_max_award():
    text = "A £10m fund.\nAwards of up to £150,000 per project.\n"
    found = scout(["https://x.test"], fetcher=_fetcher(text), now=NOW)
    assert found[0].max_award == 150_000.0 and found[0].currency == "GBP"

    # No per-award marker anywhere: refuse rather than report the fund size.
    total_only = scout(["https://x.test"], fetcher=_fetcher("A £10m fund is available.\n"), now=NOW)
    assert total_only[0].max_award is None and total_only[0].currency == ""


def test_award_and_fund_total_on_one_line_are_still_separated():
    # The case a line-wide scan gets wrong, and funders write it constantly.
    text = "Awards of up to 500,000 GBP per project. Total fund 25m GBP.\n"
    found = scout(["https://x.test"], fetcher=_fetcher(text), now=NOW)
    assert found[0].max_award == 500_000.0 and found[0].currency == "GBP"


def test_a_year_is_never_mistaken_for_an_award():
    text = "Deadline: 12 August 2026. Awards of up to £50k.\n"
    found = scout(["https://x.test"], fetcher=_fetcher(text), now=NOW)
    assert found[0].max_award == 50_000.0
    assert found[0].deadline == datetime(2026, 8, 12, tzinfo=UTC)


def test_ambiguous_dollar_keeps_the_amount_and_refuses_the_currency():
    found = scout(["https://x.test"], fetcher=_fetcher("Grants of up to $50,000.\n"), now=NOW)
    assert found[0].max_award == 50_000.0
    assert found[0].currency == ""  # $ names at least five currencies


# ── the decision goes through the switchboard, not around it ─────────────────


def _strong_reading():
    return GateReading(coherence=0.9, divergence=0.05, life_score=0.8,
                       panel_consensus="BUY", panel_confidence=0.9, panel_evidence=1.0)


def test_pursue_routes_through_the_switchboard_and_holds_at_submit(tmp_path, monkeypatch):
    import aureon.gates.switchboard as sb

    monkeypatch.setattr(sb, "read_organism", lambda bus=None: _strong_reading())
    profile = read_capability(_repo(tmp_path))
    result = assess(_opportunity(), profile)

    assert [v.gate for v in result.verdicts] == ["act", "validate", "test", "submit"]
    assert [v.decision for v in result.verdicts[:3]] == [ADVANCE, ADVANCE, ADVANCE]
    # The chain's own gate holds the irreversible step. The scout has no submit
    # path of its own, and the sheet's approval rule survives even a perfect score.
    assert result.decision == HOLD
    assert result.fit.score is not None


def test_no_local_threshold_overrides_the_chain(tmp_path, monkeypatch):
    import aureon.gates.switchboard as sb

    monkeypatch.setattr(sb, "read_organism", lambda bus=None: _strong_reading())
    profile = read_capability(_repo(tmp_path))
    # A call that scores nothing, and an unreadable one. If this module owned a
    # threshold, these would short-circuit before the chain ever ran.
    for opportunity in (_opportunity(text="Zebra husbandry bursary."),
                        _opportunity(text="", retrieval_error="timed out")):
        result = assess(opportunity, profile)
        assert [v.gate for v in result.verdicts] == ["act", "validate", "test", "submit"]
        assert result.decision == HOLD


def test_a_blind_organism_redoes_rather_than_advancing(tmp_path, monkeypatch):
    import aureon.gates.switchboard as sb

    monkeypatch.setattr(sb, "read_organism", lambda bus=None: GateReading())
    profile = read_capability(_repo(tmp_path))
    result = assess(_opportunity(), profile)
    assert result.decision == REDO
    assert len(result.verdicts) == 1  # the chain stops where it stopped


def test_the_pursue_action_is_not_itself_human_held(tmp_path, monkeypatch):
    # If it were, every gate would HOLD and the chain would prove nothing about
    # the act/validate/test questions. The hold must come from the submit gate.
    assert is_human_held(PURSUE_ACTION) is False


def test_verdicts_and_score_are_published_side_by_side(tmp_path, monkeypatch):
    import aureon.gates.switchboard as sb

    monkeypatch.setattr(sb, "read_organism", lambda bus=None: _strong_reading())

    published = []

    class Bus:
        def publish(self, thought):
            published.append(thought)

    profile = read_capability(_repo(tmp_path))
    result = assess(_opportunity(), profile, bus=Bus())
    payload = result.to_dict()
    assert payload["fit"]["score"] is not None
    assert payload["decision"] == HOLD
    assert len(payload["verdicts"]) == 4
    assert payload["opportunity"]["source"].startswith("web_fetch:")
    assert published, "verdicts must reach the bus the rest of the organism reads"
