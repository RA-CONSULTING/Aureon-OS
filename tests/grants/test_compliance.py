"""The auditor: reads compliance from real documents, and never reports green on silence.

Hermetic. Every test builds its own miniature repository under tmp_path and
passes it as ``root``, so nothing here touches the live ledger, the live
COMPANY.md, or the network. The fixture documents are written by hand rather
than copied from the repo, which is the point: the module must find the
Companies House blocker by *reading*, so a fixture that merely paraphrases the
real sheet has to work exactly as well as the real one.

What is being proved, in order of importance:

  1. a missing source document yields ``unknown``, never ``pass``;
  2. an all-``unknown`` report cannot read as healthy;
  3. the Companies House blocker is detected from a fixture document, from
     either of its two real sources, and survives the "overdue cleared" trap;
  4. ``blocking_count`` counts live blockers and only live blockers.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from aureon.gates.switchboard import ADVANCE, HOLD, REDO
from aureon.grants.compliance import (
    FAIL,
    PASS,
    UNKNOWN,
    ComplianceCheck,
    ComplianceReport,
    audit_readiness,
    compliance_verdict,
    run_gate_chain,
)

NOW = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)

# Written in the shape the real war-room export uses — a blockquoted verbatim
# row — but with an invented company and date, so a pass here is a pass on
# reading rather than on recognising this repository's own strings.
OVERDUE_LINE = (
    "> \"Companies House shows the confirmation statement due 2031-01-02 as overdue. "
    "Resolve before submitting competitive bids where possible.\"\n"
)
# The trap: this row from the real checklist contains the word "cleared" while
# asserting the opposite. Anything matching on "cleared" reports a live P0
# blocker as resolved.
OVERDUE_CLEARED_TRAP = (
    "| Company compliance | Confirmation statement overdue cleared | **Not clear** | "
    "Gary | File Companies House confirmation statement or verify current resolution. |\n"
)
RESOLVED_LINE = "> \"The confirmation statement is filed and accepted; no longer overdue.\"\n"
APPROVAL_LINE = (
    "> \"No external submission, legal representation, filing, payment, or email send "
    "should happen without Director approval.\"\n"
)

COMPANY_MD = """# Example Holdings Ltd

## Company

| | |
|---|---|
| **Registered name** | Example Holdings Ltd |
| **Company number** | ZZ000001 |
| **Registered office** | 1 Example Street, Exampleton, EX1 1EX |
| **Director** | A Person |
"""


def _repo(tmp_path, *, ledger=None, reconciliation=None, company=COMPANY_MD, applicant=None):
    """Build a miniature repository. Anything passed as None is simply absent."""
    grants = tmp_path / "data" / "research" / "grants"
    grants.mkdir(parents=True, exist_ok=True)
    if company is not None:
        (tmp_path / "COMPANY.md").write_text(company, encoding="utf-8")
    if ledger is not None:
        (grants / "pipeline.json").write_text(json.dumps(ledger), encoding="utf-8")
    if reconciliation is not None:
        (grants / "RECONCILIATION_20310102.md").write_text(reconciliation, encoding="utf-8")
    if applicant is not None:
        (grants / "autopilot_status.json").write_text(json.dumps(applicant), encoding="utf-8")
    return tmp_path


def _app(app_id, *, status="DRAFT", documents=None, submitted_at=None):
    out = {"id": app_id, "name": app_id, "funder": "F", "status": status}
    if documents is not None:
        out["documents"] = documents
    if submitted_at is not None:
        out["submitted_at"] = submitted_at
    return out


def _check(name, status, *, blocking=False, remedy=""):
    return ComplianceCheck(name=name, status=status, detail="d", source="s",
                           blocking=blocking, remedy=remedy)


def _named(report, name):
    return next(c for c in report.checks if c.name == name)


@pytest.fixture(autouse=True)
def _no_live_ledger(monkeypatch, tmp_path):
    """Point the operator override somewhere empty so a leak would be obvious."""
    monkeypatch.setenv("AUREON_GRANTS_DIR", str(tmp_path / "definitely-not-here"))


# ── 1. a missing source is unknown, never pass ───────────────────────────────


def test_empty_root_yields_unknown_everywhere_and_never_pass(tmp_path):
    report = audit_readiness(tmp_path, now=NOW)
    assert {c.status for c in report.checks} == {UNKNOWN}
    assert report.passed_count == 0
    # An unknown carries no source, and says where it looked instead.
    for check in report.checks:
        assert check.source == ""
        assert "looked in" in check.detail
    assert report.problems  # the absent documents are named, not swallowed


def test_missing_reconciliation_and_ledger_make_the_filing_check_unknown_not_pass(tmp_path):
    _repo(tmp_path)  # COMPANY.md only — nothing that could speak to a filing
    check = _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current")
    assert check.status == UNKNOWN
    assert check.blocking is True and check.is_live_blocker is True


def test_a_ledger_that_is_silent_on_compliance_does_not_clear_the_filing_check(tmp_path):
    # The ledger exists and parses; it simply carries none of the compliance
    # keys. Silence is not clearance.
    _repo(tmp_path, ledger={"active_applications": [_app("A1")]})
    assert _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current").status == UNKNOWN


def test_an_explicit_false_flag_does_clear_the_filing_check(tmp_path):
    # The difference between the previous test and this one is the whole rule:
    # a missing key is silence, an explicit ``false`` is a statement.
    _repo(tmp_path, ledger={
        "company_compliance_risk_active": False,
        "company_confirmation_statement_warning_active": False,
        "active_applications": [],
    })
    check = _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current")
    assert check.status == PASS and check.source == "pipeline.json"


def test_no_live_application_makes_completeness_unknown_not_a_vacuous_pass(tmp_path):
    _repo(tmp_path, ledger={"active_applications": [_app("A1", status="SUBMITTED")]})
    check = _named(audit_readiness(tmp_path, now=NOW), "application_evidence_complete")
    assert check.status == UNKNOWN
    assert "not measured rather than assumed" in check.detail
    # Nothing to check is not an obstruction — it must not manufacture a blocker.
    assert check.is_live_blocker is False


# ── 2. an all-unknown report is not healthy ──────────────────────────────────


def test_all_unknown_report_is_not_healthy(tmp_path):
    report = audit_readiness(tmp_path, now=NOW)
    assert report.status == FAIL
    assert report.ready is False
    assert report.to_dict()["status"] == FAIL


def test_all_unknown_is_unhealthy_even_when_nothing_is_marked_blocking():
    # The structural guarantee, isolated from the blocking machinery: a report
    # where nothing passed is FAIL because ``passed_count == 0``, not merely
    # because a blocker happened to be live. Constructed directly, because this
    # must hold for any ComplianceReport a caller can build.
    report = ComplianceReport(checks=(
        _check("a", UNKNOWN), _check("b", UNKNOWN), _check("c", UNKNOWN),
    ))
    assert report.blocking_count == 0
    assert report.status == FAIL and report.ready is False


def test_status_is_derived_and_cannot_be_assigned():
    # ``status`` is a property on a frozen dataclass: there is no code path that
    # can stamp a report clean without a check having passed.
    report = ComplianceReport(checks=(_check("a", UNKNOWN),))
    with pytest.raises((AttributeError, TypeError)):
        report.status = PASS  # type: ignore[misc]


def test_a_report_passes_only_when_something_passed_and_nothing_blocks():
    clean = ComplianceReport(checks=(_check("a", PASS, blocking=True), _check("b", PASS)))
    assert clean.status == PASS and clean.ready is True

    one_blocker = ComplianceReport(checks=(
        _check("a", PASS, blocking=True), _check("b", FAIL, blocking=True),
    ))
    assert one_blocker.status == FAIL

    # A non-blocking failure does not sink an otherwise clean report.
    tolerated = ComplianceReport(checks=(
        _check("a", PASS, blocking=True), _check("b", FAIL, blocking=False),
    ))
    assert tolerated.status == PASS


# ── 3. the Companies House blocker is detected by reading ────────────────────


def test_companies_house_blocker_is_read_from_the_reconciliation_document(tmp_path):
    _repo(tmp_path, reconciliation="# Report\n\n" + OVERDUE_LINE)
    report = audit_readiness(tmp_path, now=NOW)
    check = _named(report, "statutory_filings_current")
    assert check.status == FAIL
    assert check.source == "RECONCILIATION_20310102.md"
    # The finding is quoted from the document, not composed from a constant.
    assert "confirmation statement due 2031-01-02 as overdue" in check.detail
    assert check.blocking is True and check in report.blockers


def test_companies_house_blocker_is_read_from_the_ledger_when_no_report_exists(tmp_path):
    _repo(tmp_path, ledger={
        "company_compliance_risk_active": True,
        "company_compliance_risk_status": "CONFIRMATION_STATEMENT_OVERDUE_ON_COMPANIES_HOUSE",
        "active_applications": [],
    })
    check = _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current")
    assert check.status == FAIL and check.source == "pipeline.json"
    assert "CONFIRMATION_STATEMENT_OVERDUE_ON_COMPANIES_HOUSE" in check.detail


def test_the_overdue_finding_survives_the_word_cleared_on_the_same_line(tmp_path):
    # "Confirmation statement overdue cleared | Not clear" is a real row. A
    # module that matched on "cleared" would report a live P0 blocker resolved.
    _repo(tmp_path, reconciliation="# Report\n\n" + OVERDUE_CLEARED_TRAP)
    assert _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current").status == FAIL


def test_an_overdue_line_anywhere_beats_a_resolved_line_elsewhere(tmp_path):
    _repo(tmp_path, reconciliation="# Report\n\n" + RESOLVED_LINE + "\n" + OVERDUE_LINE)
    assert _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current").status == FAIL


def test_a_document_stating_resolution_clears_the_check(tmp_path):
    # Proves the FAIL above is a reading of the document and not a constant:
    # change what the document says and the verdict changes with it.
    _repo(tmp_path, reconciliation="# Report\n\n" + RESOLVED_LINE)
    check = _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current")
    assert check.status == PASS and check.source == "RECONCILIATION_20310102.md"


def test_the_negation_guard_is_narrow_and_fails_safe(tmp_path):
    # "no longer overdue" is the one negation recognised, because without it a
    # clearance reads as the thing it clears and the blocker becomes permanent.
    # Everything else that mentions both stays a blocker.
    _repo(tmp_path, reconciliation="# R\n\n"
          "> \"Confirmation statement: overdue; resolution recorded as pending.\"\n")
    assert _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current").status == FAIL


def test_a_ledger_status_naming_the_risk_as_closed_is_not_read_as_overdue(tmp_path):
    _repo(tmp_path, ledger={
        "company_compliance_risk_status": "CONFIRMATION_STATEMENT_NO_LONGER_OVERDUE_FILED_AND_ACCEPTED",
        "company_compliance_risk_active": False,
        "company_confirmation_statement_warning_active": False,
        "active_applications": [],
    })
    assert _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current").status == PASS


def test_the_two_sources_corroborate_each_other(tmp_path):
    _repo(
        tmp_path,
        reconciliation="# Report\n\n" + OVERDUE_LINE,
        ledger={"company_compliance_risk_active": True, "active_applications": []},
    )
    check = _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current")
    assert check.status == FAIL and "corroborated by pipeline.json" in check.detail


def test_the_newest_reconciliation_is_the_one_that_is_read(tmp_path):
    grants = tmp_path / "data" / "research" / "grants"
    grants.mkdir(parents=True)
    (grants / "RECONCILIATION_20300101.md").write_text("# Old\n\n" + OVERDUE_LINE, encoding="utf-8")
    (grants / "RECONCILIATION_20310102.md").write_text("# New\n\n" + RESOLVED_LINE, encoding="utf-8")
    check = _named(audit_readiness(tmp_path, now=NOW), "statutory_filings_current")
    assert check.source == "RECONCILIATION_20310102.md" and check.status == PASS


def test_the_approval_rule_is_read_not_assumed(tmp_path):
    _repo(tmp_path, reconciliation="# Report\n\n" + APPROVAL_LINE)
    check = _named(audit_readiness(tmp_path, now=NOW), "human_approval_rule")
    assert check.status == PASS
    assert "without Director approval" in check.detail

    # With no document stating it, the rule is unknown and blocking — an
    # automation that cannot see its approval rule must not proceed on the
    # assumption that there isn't one.
    bare = _named(audit_readiness(_repo(tmp_path / "bare"), now=NOW), "human_approval_rule")
    assert bare.status == UNKNOWN and bare.is_live_blocker is True


def test_the_approval_rule_is_also_read_from_the_machine_readable_policy(tmp_path):
    _repo(tmp_path, applicant={"automation_policy": [
        "Prepare, validate and package grant materials.",
        "Final legal external submission buttons require exact action-time confirmation.",
    ]})
    check = _named(audit_readiness(tmp_path, now=NOW), "human_approval_rule")
    assert check.status == PASS
    assert "require exact action-time confirmation" in check.detail


# ── 4. blocking_count counts live blockers, and only those ───────────────────


def test_blocking_count_counts_only_blocking_checks_that_did_not_pass():
    report = ComplianceReport(checks=(
        _check("passed_blocking", PASS, blocking=True),      # blocking, cleared
        _check("failed_blocking", FAIL, blocking=True),      # live blocker
        _check("unknown_blocking", UNKNOWN, blocking=True),  # live blocker
        _check("failed_advisory", FAIL, blocking=False),     # not a blocker
        _check("unknown_advisory", UNKNOWN, blocking=False),
    ))
    assert report.blocking_count == 2
    assert [c.name for c in report.blockers] == ["failed_blocking", "unknown_blocking"]
    assert report.passed_count == 1 and report.failed_count == 2 and report.unknown_count == 2
    assert report.to_dict()["blocking_count"] == 2


def test_an_unknown_blocking_check_is_a_live_blocker():
    # The rule that makes silence expensive rather than free.
    assert _check("x", UNKNOWN, blocking=True).is_live_blocker is True
    assert _check("x", PASS, blocking=True).is_live_blocker is False


def test_blocking_count_on_a_real_audit_of_an_empty_root(tmp_path):
    report = audit_readiness(tmp_path, now=NOW)
    expected = [c.name for c in report.checks if c.blocking]
    assert report.blocking_count == len(expected)
    # prior_grant_status is advisory: a first-time applicant is eligible, so a
    # zero there must not obstruct anything.
    assert "prior_grant_status" not in expected


# ── evidence completeness and identity ───────────────────────────────────────


def test_a_live_application_with_no_documents_is_a_blocker(tmp_path):
    _repo(tmp_path, ledger={"active_applications": [
        _app("A1", status="EVIDENCE_REQUESTED", documents=["pack.pdf"]),
        _app("A2", status="PARTNER_EVIDENCE_REQUIRED"),          # documents key absent
        _app("A3", status="AWAITING_REPLY", documents=[]),       # present but empty
        _app("A4", status="DEADLINE_PASSED_NO_SAFE_SUBMISSION"),  # closed — not counted
    ]})
    check = _named(audit_readiness(tmp_path, now=NOW), "application_evidence_complete")
    assert check.status == FAIL
    assert "2 of 3 live applications" in check.detail
    assert "A2" in check.detail and "A3" in check.detail and "A4" not in check.detail
    assert check.is_live_blocker is True


def test_a_complete_evidence_pack_passes(tmp_path):
    _repo(tmp_path, ledger={"active_applications": [
        _app("A1", status="AWAITING_REPLY", documents=["a.pdf"]),
    ]})
    assert _named(audit_readiness(tmp_path, now=NOW), "application_evidence_complete").status == PASS


def test_prior_grant_zero_is_a_reading_not_a_failure(tmp_path):
    _repo(tmp_path, ledger={"active_applications": [_app("A1")]})
    check = _named(audit_readiness(tmp_path, now=NOW), "prior_grant_status")
    assert check.status == PASS and check.blocking is False
    assert "0 of 1" in check.detail


def test_prior_grant_never_infers_an_award_from_free_text(tmp_path):
    # "award terms incomplete" is a real ledger phrase. Substring matching on
    # "award" would report a grant nobody won.
    _repo(tmp_path, ledger={"active_applications": [
        _app("A1", status="UK_SWISS_DRAFT_93_PERCENT_PROJECT_IMPACT_AND_AWARD_TERMS_INCOMPLETE"),
        _app("A2", status="AWARDED"),
    ]})
    assert "1 carry an exact AWARDED status" in _named(
        audit_readiness(tmp_path, now=NOW), "prior_grant_status").detail


def test_company_facts_are_read_from_the_document_not_hardcoded(tmp_path):
    _repo(tmp_path)
    report = audit_readiness(tmp_path, now=NOW)
    number = _named(report, "company_number")
    assert number.status == PASS
    # The fixture's invented number, not this repository's real one.
    assert "ZZ000001" in number.detail and number.source == "COMPANY.md"
    assert "Example Holdings Ltd" in _named(report, "legal_entity").detail


def test_documents_that_contradict_each_other_are_a_failure_not_a_soft_pass(tmp_path):
    _repo(tmp_path, applicant={"applicant": {
        "legal_entity": "Example Holdings Ltd",
        "company_number": "ZZ999999",   # COMPANY.md says ZZ000001
        "registered_office": "1 Example Street, Exampleton, EX1 1EX",
    }})
    check = _named(audit_readiness(tmp_path, now=NOW), "company_number")
    assert check.status == FAIL and check.is_live_blocker is True
    # Both values are surfaced so a human can reconcile them.
    assert "ZZ999999" in check.detail and "ZZ000001" in check.detail


# ── the audit is safe, hermetic and read-only ────────────────────────────────


def test_root_is_honoured_verbatim_and_the_env_override_is_ignored(tmp_path, monkeypatch):
    """A supplied root must never be widened to the configured live directory."""
    elsewhere = tmp_path / "elsewhere" / "data" / "research" / "grants"
    elsewhere.mkdir(parents=True)
    (elsewhere / "pipeline.json").write_text(
        json.dumps({"company_compliance_risk_active": False,
                    "company_confirmation_statement_warning_active": False,
                    "active_applications": []}), encoding="utf-8")
    monkeypatch.setenv("AUREON_GRANTS_DIR", str(elsewhere))

    empty = _repo(tmp_path / "empty")
    check = _named(audit_readiness(empty, now=NOW), "statutory_filings_current")
    # Had the override leaked in, this would read PASS from the other directory.
    assert check.status == UNKNOWN


def test_audit_never_raises_on_malformed_documents(tmp_path):
    grants = tmp_path / "data" / "research" / "grants"
    grants.mkdir(parents=True)
    (grants / "pipeline.json").write_text("{not json", encoding="utf-8")
    (grants / "RECONCILIATION_20310102.md").write_text("", encoding="utf-8")
    (grants / "autopilot_status.json").write_text("[]", encoding="utf-8")
    (tmp_path / "COMPANY.md").write_text("no table here", encoding="utf-8")

    report = audit_readiness(tmp_path, now=NOW)
    assert report.status == FAIL
    assert any("not valid JSON" in p for p in report.problems)
    assert any("empty" in p for p in report.problems)


def test_active_applications_of_the_wrong_shape_is_reported_not_assumed(tmp_path):
    _repo(tmp_path, ledger={"active_applications": "not a list"})
    report = audit_readiness(tmp_path, now=NOW)
    assert any("no active_applications list" in p for p in report.problems)
    assert _named(report, "application_evidence_complete").status == UNKNOWN


def test_the_audit_writes_nothing(tmp_path):
    _repo(tmp_path, ledger={"active_applications": [_app("A1", documents=["a.pdf"])]},
          reconciliation="# Report\n\n" + OVERDUE_LINE)
    ledger = tmp_path / "data" / "research" / "grants" / "pipeline.json"
    before = ledger.read_bytes()
    listing = sorted(p.name for p in (tmp_path / "data" / "research" / "grants").iterdir())

    audit_readiness(tmp_path, now=NOW)

    assert ledger.read_bytes() == before
    assert sorted(p.name for p in (tmp_path / "data" / "research" / "grants").iterdir()) == listing


def test_to_dict_and_narrate_survive_a_real_audit(tmp_path):
    _repo(tmp_path, reconciliation="# Report\n\n" + OVERDUE_LINE + APPROVAL_LINE,
          ledger={"active_applications": [_app("A1", status="AWAITING_REPLY")]})
    report = audit_readiness(tmp_path, now=NOW)
    json.loads(json.dumps(report.to_dict()))  # must be serialisable, not just dict-shaped
    text = report.narrate()
    assert "COMPLIANCE READINESS: FAIL" in text
    assert "statutory_filings_current" in text


# ── routing through the Queen's switchboard ──────────────────────────────────


def test_a_blocker_with_no_executor_holds_rather_than_asking_for_a_retry(tmp_path):
    _repo(tmp_path, reconciliation="# Report\n\n" + OVERDUE_LINE)
    verdict = compliance_verdict(audit_readiness(tmp_path, now=NOW))
    # REDO would tell the organism to iterate on a statutory filing it has no
    # hand to make — an instruction it can only fail.
    assert verdict.decision == HOLD
    assert verdict.confidence is None  # no panel was convened; no number is invented
    assert any("statutory_filings_current" in d for d in verdict.dissent)


def test_a_blocker_the_organism_could_fix_asks_for_a_retry():
    report = ComplianceReport(checks=(
        _check("a", PASS, blocking=True),
        _check("evidence", FAIL, blocking=True, remedy="attach the evidence pack"),
    ))
    assert compliance_verdict(report).decision == REDO


def test_a_report_that_confirmed_nothing_asks_for_a_retry():
    report = ComplianceReport(checks=(_check("a", UNKNOWN), _check("b", UNKNOWN)))
    verdict = compliance_verdict(report)
    assert verdict.decision == REDO and "actually passed" in verdict.reasoning


def test_a_clean_report_advances():
    report = ComplianceReport(checks=(_check("a", PASS, blocking=True), _check("b", PASS)))
    assert compliance_verdict(report).decision == ADVANCE


def test_the_chain_is_not_spent_while_a_blocker_is_live(tmp_path, monkeypatch):
    calls: list[object] = []
    monkeypatch.setattr("aureon.grants.compliance.run_chain",
                        lambda *a, **k: calls.append((a, k)) or [])

    _repo(tmp_path, reconciliation="# Report\n\n" + OVERDUE_LINE)
    verdicts = run_gate_chain(audit_readiness(tmp_path, now=NOW))

    assert len(verdicts) == 1 and verdicts[0].decision == HOLD
    # Reading the field, convening the panel and asking the conscience cannot
    # change whether a statutory return is overdue.
    assert calls == []


def test_a_clean_report_hands_the_decision_to_the_chain(monkeypatch):
    seen: dict[str, object] = {}

    def _fake_run_chain(context=None, **kwargs):
        seen["context"] = context
        return []

    monkeypatch.setattr("aureon.grants.compliance.run_chain", _fake_run_chain)
    report = ComplianceReport(checks=(_check("a", PASS, blocking=True),))
    verdicts = run_gate_chain(report, context={"action": "draft"})

    assert [v.decision for v in verdicts] == [ADVANCE]
    assert seen["context"]["action"] == "draft"  # the caller's context is preserved
    assert seen["context"]["compliance"]["status"] == PASS


def test_run_gate_chain_survives_a_broken_bus(tmp_path):
    class Exploding:
        def publish(self, *a, **k):
            raise RuntimeError("bus down")

    _repo(tmp_path, reconciliation="# Report\n\n" + OVERDUE_LINE)
    verdicts = run_gate_chain(audit_readiness(tmp_path, now=NOW), bus=Exploding())
    assert verdicts[0].decision == HOLD  # awareness must never crash the organ
