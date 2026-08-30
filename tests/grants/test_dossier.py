"""The approval packet: it always stops at a person, and it never guesses.

Hermetic — every test builds its own repository root under ``tmp_path`` (ledger,
reconciliation report, company documents) and passes it explicitly, so nothing
here reads the live pipeline, the live company record, or the live organism.

Four properties are what this suite exists to pin:

1. **A submission packet always ends in HOLD.** Including when the organism is
   blind, which is the case the switchboard's own ordering gets wrong: it tests
   blindness before it tests hands and returns REDO at the first gate, never
   reaching the human-held branch. A packet that reported that REDO as its
   answer would be inviting a retry on something that was never Aureon's to
   send.
2. **A missing compliance source degrades honestly** — unknown, never clear.
3. **What is missing is listed**, not quietly dropped.
4. **An id that is not in the ledger produces no file at all.**
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone

import pytest

from aureon.gates.switchboard import ADVANCE, HOLD, REDO, GateReading, is_human_held
from aureon.grants import dossier as dossier_module
from aureon.grants.dossier import (
    DOSSIER_DIRNAME,
    SUBMIT_ACTION,
    UNDECIDED,
    build_dossier,
    dossier_path,
    emit_dossier,
    read_approval_rule,
    render_markdown,
    write_dossier,
)
from aureon.grants.schemas import FitScore

NOW = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)

# Restated rather than imported from the module under test: an independent
# statement of the Queen's gate names is what makes the assertions below
# evidence instead of a tautology.
_CHAIN_GATE_NAMES = {"act", "validate", "test", "submit"}

APPROVAL_RULE = (
    "No external submission, legal representation, filing, payment, or email send "
    "should happen without Gary approval."
)
COMPLIANCE_BLOCKER = (
    "Companies House shows the confirmation statement due 2026-05-09 as overdue. "
    "Resolve before submitting competitive bids where possible."
)


# ── a repository root, built from nothing ────────────────────────────────────


def _app(app_id="APP-1", *, status="DRAFT_WAITING_PARTNER", days=None, name="A Call",
         funder="A Funder", **extra):
    row = {"id": app_id, "name": name, "funder": funder, "status": status}
    if days is not None:
        row["deadline"] = (NOW + timedelta(days=days)).isoformat()
    row.update(extra)
    return row


def _root(tmp_path, applications, *, reconciliation=True, company=True):
    """A repository root holding only what the packet is allowed to read."""
    grants = tmp_path / "data" / "research" / "grants"
    grants.mkdir(parents=True)
    (grants / "pipeline.json").write_text(
        json.dumps({"operator": "test", "active_applications": applications}), encoding="utf-8"
    )
    if reconciliation:
        (grants / "RECONCILIATION_20260731.md").write_text(
            "# Reconciliation\n\n"
            "### 6.1 Companies House confirmation-statement blocker\n\n"
            "Overview tab, row `Compliance blocker` — **verbatim:**\n\n"
            f"> \"{COMPLIANCE_BLOCKER}\"\n\n"
            "### 6.2 Approval rule\n\n"
            "Overview tab, row `Approval rule` — **verbatim:**\n\n"
            f"> \"{APPROVAL_RULE}\"\n",
            encoding="utf-8",
        )
    if company:
        # Deliberately fictional. The real entity is read from the real
        # repository at runtime and is never written into a test fixture.
        (tmp_path / "COMPANY.md").write_text(
            "# Company\n\n"
            "| Field | Value |\n| --- | --- |\n"
            "| Registered name | Fixture Holdings Ltd |\n"
            "| Company number | FX000001 |\n"
            "| Registered office | 1 Fixture Way |\n"
            "| Director | A Fixture Person |\n",
            encoding="utf-8",
        )
    return tmp_path


class _Report:
    """A compliance report shaped like the real one, with nothing measured."""

    def __init__(self, *, status="fail", blockers=(), problems=(), passed=0, failed=0, unknown=0):
        self.status = status
        self.blockers = blockers
        self.problems = problems
        self.passed_count = passed
        self.failed_count = failed
        self.unknown_count = unknown

    @property
    def blocking_count(self):
        return len(self.blockers)


class _Check:
    def __init__(self, name, status, detail, remedy="", human_held=False):
        self.name = name
        self.status = status
        self.detail = detail
        self.remedy = remedy
        self.human_held = human_held


def _blind(monkeypatch):
    """Make the organism unreadable — no field, no panel, nothing."""
    monkeypatch.setattr(
        "aureon.gates.switchboard.read_organism", lambda bus=None: GateReading()
    )


def _perfect(monkeypatch):
    """Make the organism read as strongly as it possibly can."""
    monkeypatch.setattr(
        "aureon.gates.switchboard.read_organism",
        lambda bus=None: GateReading(
            coherence=0.99, divergence=0.0, life_score=0.99,
            panel_consensus="RALLY", panel_confidence=1.0, panel_evidence=1.0, lighthouse=True,
        ),
    )


@pytest.fixture
def clean_compliance():
    """A compliance report with nothing outstanding, so the hold stands alone."""
    return _Report(status="pass", passed=7)


# ── 1. the packet always ends in HOLD ────────────────────────────────────────


def test_submit_action_is_recognised_as_human_held():
    # The packet's central guarantee rests on this. If a rename ever detached
    # the action from the switchboard's vocabulary, every other test here would
    # still pass while the guarantee quietly evaporated.
    assert is_human_held(SUBMIT_ACTION) is True


@pytest.mark.parametrize("organism", ["blind", "perfect"])
def test_submission_always_ends_in_hold(tmp_path, monkeypatch, clean_compliance, organism):
    (_blind if organism == "blind" else _perfect)(monkeypatch)
    root = _root(tmp_path, [_app(days=10)])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)

    assert d is not None
    assert d.approval_state == HOLD and d.held is True
    assert "human-held" in d.approval_reasoning
    assert "Gary" in d.approval_reasoning


def test_hold_stands_even_when_the_blind_chain_says_redo(tmp_path, monkeypatch, clean_compliance):
    # switchboard.evaluate tests blindness BEFORE it tests hands, so a blind
    # organism returns REDO at the first gate and never reaches the human-held
    # branch. REDO means "iterate and come back"; HOLD means "this was never
    # yours to send". The packet must report the second, and must not hide the
    # first while doing it.
    _blind(monkeypatch)
    root = _root(tmp_path, [_app(days=10)])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)

    chain = [v for v in d.gate_verdicts if v.gate == "act"]
    assert chain and chain[0].decision == REDO
    assert d.approval_state == HOLD
    # The chain's own answer is carried, not suppressed.
    assert "REDO" in d.approval_reasoning
    assert any("gate chain stopped at 'act' with REDO" in item for item in d.outstanding)


def test_a_perfect_organism_still_cannot_advance_the_submission(tmp_path, monkeypatch,
                                                                clean_compliance):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=10)])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)

    # The compliance gate may well advance — a clean audit is a real ADVANCE and
    # must be reported as one. What may never advance is the Queen's chain over
    # the submission: it holds at the first gate whatever the evidence says.
    chain = [v for v in d.gate_verdicts if v.gate in _CHAIN_GATE_NAMES]
    assert chain and ADVANCE not in {v.decision for v in chain}
    assert chain[-1].decision == HOLD
    assert d.approval_state == HOLD


def test_the_brief_states_the_approval_rule_and_the_hold(tmp_path, monkeypatch, clean_compliance):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=10)])

    md = render_markdown(build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance))

    assert "**Submission requires Gary's approval.**" in md
    assert APPROVAL_RULE in md
    assert "RECONCILIATION_20260731.md" in md
    assert "inform Gary's decision, not to replace it" in md
    assert "**HOLD.**" in md


def test_approval_rule_is_read_not_hardcoded(tmp_path):
    root = _root(tmp_path, [_app()])
    grants = root / "data" / "research" / "grants"

    cited = read_approval_rule(grants)
    assert cited is not None
    assert cited.value == APPROVAL_RULE
    assert cited.source == "RECONCILIATION_20260731.md"

    # A newer reconciliation supersedes the older one without a code change.
    (grants / "RECONCILIATION_20260901.md").write_text(
        "### Approval rule\n\n> \"A later rule that supersedes the earlier one entirely.\"\n",
        encoding="utf-8",
    )
    assert read_approval_rule(grants).source == "RECONCILIATION_20260901.md"


def test_an_unreadable_approval_rule_does_not_weaken_the_hold(tmp_path, monkeypatch,
                                                              clean_compliance):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=10)], reconciliation=False)

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)
    md = render_markdown(d)

    assert d.approval_rule is None
    assert any("approval rule" in item for item in d.outstanding)
    assert "could not be read" in md
    # The hold does not depend on the quote.
    assert d.approval_state == HOLD
    assert "**Submission requires Gary's approval.**" in md


def test_an_unrecognised_action_is_undecided_never_advance(tmp_path, monkeypatch,
                                                           clean_compliance):
    # If the packet's action were ever renamed to something the switchboard does
    # not hold, the safe direction is "we cannot vouch for this", not "go".
    _perfect(monkeypatch)
    monkeypatch.setattr(dossier_module, "SUBMIT_ACTION", "prepare_draft")
    root = _root(tmp_path, [_app(days=10)])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)

    assert d.approval_state == UNDECIDED
    assert d.approval_state != ADVANCE
    assert any("not recognised as human-held" in item for item in d.outstanding)


# ── 2. a missing compliance source degrades honestly ─────────────────────────


def test_missing_compliance_source_is_unknown_never_clear(tmp_path, monkeypatch):
    _perfect(monkeypatch)

    def _explode(*a, **k):
        raise RuntimeError("compliance organ unavailable")

    monkeypatch.setattr("aureon.grants.compliance.audit_readiness", _explode)
    root = _root(tmp_path, [_app(days=10)])

    d = build_dossier("APP-1", root=root, now=NOW)
    md = render_markdown(d)

    assert d.compliance is None
    assert d.compliance_blocker and "RuntimeError" in d.compliance_blocker
    assert any("compliance position unknown" in item for item in d.outstanding)
    assert "**Compliance position could not be read**" in md
    assert "Treat this as unknown, not as clear." in md
    # And the packet is still held — an unknown compliance position cannot
    # produce a green light by omission.
    assert d.approval_state == HOLD


def test_a_report_that_cannot_be_read_is_reported_not_rendered_clean(tmp_path, monkeypatch):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=10)])

    class _Opaque:
        """A report shape this packet does not understand."""

    d = build_dossier("APP-1", root=root, now=NOW, compliance=_Opaque())

    assert d.compliance is None
    assert d.compliance_blocker and "could not be read" in d.compliance_blocker
    assert "could not be read" in render_markdown(d)


def test_compliance_blockers_and_unread_sources_are_both_carried(tmp_path, monkeypatch):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=10)])
    report = _Report(
        status="fail",
        passed=2,
        failed=1,
        unknown=3,
        blockers=(
            _Check("statutory_filings_current", "fail", COMPLIANCE_BLOCKER,
                   remedy="file the outstanding statutory return", human_held=True),
        ),
        problems=("COMPANY.md: not found",),
    )

    d = build_dossier("APP-1", root=root, now=NOW, compliance=report)
    md = render_markdown(d)

    assert d.compliance is not None and "FAIL" in d.compliance
    assert any(COMPLIANCE_BLOCKER in item for item in d.outstanding)
    # "we could not check" is itself a finding, not a blank.
    assert any("source not read: COMPANY.md: not found" in item for item in d.outstanding)
    # A remedy with no automatic executor is labelled as such.
    assert any("no automatic executor" in item for item in d.outstanding)
    assert COMPLIANCE_BLOCKER in md


def test_the_real_auditor_runs_when_no_report_is_supplied(tmp_path, monkeypatch):
    # Not a stub: the packet must actually reach aureon.grants.compliance. An
    # empty root makes every check unknown, which is the honest answer.
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=10)], reconciliation=False, company=False)

    d = build_dossier("APP-1", root=root, now=NOW)

    assert d.compliance_blocker is None
    assert d.compliance is not None
    assert "PASS" not in d.compliance
    assert d.outstanding, "an empty repository must not produce a clean packet"


# ── 3. what is missing is listed, not dropped ────────────────────────────────


def test_outstanding_lists_every_absence_it_found(tmp_path, monkeypatch, clean_compliance):
    _perfect(monkeypatch)
    # No deadline, no documents, no amount, an unclassifiable status.
    root = _root(tmp_path, [_app(status="ENTIRELY_NOVEL_STATE_NO_MARKER_MATCHES")])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)
    md = render_markdown(d)

    joined = " || ".join(d.outstanding)
    assert "deadline" in joined
    assert "evidence documents" in joined
    assert "fit score" in joined
    assert "amount requested" in joined
    assert "could not be classified" in joined
    # Everything found missing reaches the page.
    for item in d.outstanding:
        assert item in md


def test_fit_score_is_never_invented(tmp_path, monkeypatch, clean_compliance):
    _perfect(monkeypatch)
    prose = "Route-fit only, no traction claim — framing depends on the evidence pack."
    root = _root(tmp_path, [_app(fit=prose)])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)
    md = render_markdown(d)

    # The ledger's fit is a sentence. A sentence is not a score.
    assert d.fit_score is None
    assert d.fit_basis == prose
    assert "**Not scored.**" in md
    assert prose in md


@pytest.mark.parametrize("junk", [True, False, "", None, [1, 2], {"a": 1}])
def test_no_ledger_value_is_coerced_into_a_fit_score(tmp_path, monkeypatch, clean_compliance, junk):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(fit=junk)])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)

    assert d.fit_score is None, f"{junk!r} became a fit score of {d.fit_score!r}"


def test_a_supplied_fit_score_is_used_and_a_blocked_one_is_not(tmp_path, monkeypatch,
                                                               clean_compliance):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app()])

    measured = FitScore(score=0.375, matched_terms=("evidence", "automation"))
    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance, fit=measured)
    assert d.fit_score == 0.375
    assert "evidence" in (d.fit_basis or "")
    assert "0.38" in render_markdown(d)

    # A FitScore that could not be measured carries None and its own reason.
    unmeasured = FitScore(score=None, blocker="call text was never retrieved")
    d2 = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance, fit=unmeasured)
    assert d2.fit_score is None
    assert d2.fit_basis == "call text was never retrieved"


def test_evidence_documents_are_kept_in_full_and_only_the_brief_is_capped(
    tmp_path, monkeypatch, clean_compliance
):
    _perfect(monkeypatch)
    docs = [f"EVIDENCE_{i:03d}.md" for i in range(60)]
    root = _root(tmp_path, [_app(documents=docs)])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)
    md = render_markdown(d)

    assert list(d.evidence_documents) == docs
    assert "60 document(s) recorded" in md
    assert "and 40 more" in md
    # The count is stated rather than the list being silently truncated.
    assert docs[0] in md and docs[-1] not in md


def test_a_closed_application_still_reports_its_lifecycle(tmp_path, monkeypatch,
                                                          clean_compliance):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(status="AKT6_DEADLINE_PASSED_NO_SAFE_SUBMISSION", days=-30)])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)
    md = render_markdown(d)

    assert d.lifecycle == "closed"
    assert "closed" in md
    assert "passed 30.0 days ago" in md


def test_overdue_pressure_is_stated_as_overdue(tmp_path, monkeypatch, clean_compliance):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=-2)])

    md = render_markdown(build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance))

    assert "passed 2.0 days ago" in md


def test_an_unparseable_deadline_is_unknown_not_absent(tmp_path, monkeypatch, clean_compliance):
    _perfect(monkeypatch)
    # The live ledger really does hold strings like this in `deadline`.
    root = _root(tmp_path, [_app(deadline="open-continuous-step-1-confirm-in-portal")])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)
    md = render_markdown(d)

    assert d.deadline is None and d.days_remaining is None
    assert "unknown, not absent" in md


def test_the_packet_survives_a_broken_bus(tmp_path, monkeypatch, clean_compliance):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=3)])

    class Exploding:
        def publish(self, *a, **k):
            raise RuntimeError("bus down")

    d = build_dossier("APP-1", root=root, now=NOW, bus=Exploding(), compliance=clean_compliance)
    assert d is not None and d.approval_state == HOLD


def test_the_packet_is_json_serialisable(tmp_path, monkeypatch, clean_compliance):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=3, amount_requested=175000, currency="GBP")])

    payload = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance).to_dict()

    json.loads(json.dumps(payload))
    assert payload["approval_state"] == HOLD
    assert payload["amount_requested"] == 175000.0


# ── 4. nothing is written for an id the ledger does not hold ─────────────────


def test_no_dossier_is_written_for_an_unknown_application_id(tmp_path, monkeypatch,
                                                             clean_compliance):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app("APP-1")])

    assert build_dossier("APP-NOT-IN-THE-LEDGER", root=root, now=NOW,
                         compliance=clean_compliance) is None
    assert emit_dossier("APP-NOT-IN-THE-LEDGER", root=root, now=NOW,
                        compliance=clean_compliance) is None
    assert not (root / "data" / "research" / "grants" / DOSSIER_DIRNAME).exists()


def test_a_near_miss_id_does_not_match(tmp_path, monkeypatch, clean_compliance):
    # An approver reading the right name over the wrong evidence is the worst
    # failure available here, so matching is exact.
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app("APP-1")])

    for near in ("app-1", "APP-1-B", "APP", "APP-1 "):
        built = build_dossier(near, root=root, now=NOW, compliance=clean_compliance)
        if near == "APP-1 ":
            assert built is not None, "surrounding whitespace is not a different application"
        else:
            assert built is None, f"{near!r} matched APP-1"


def test_an_unavailable_ledger_writes_nothing(tmp_path, monkeypatch, clean_compliance):
    _perfect(monkeypatch)
    grants = tmp_path / "data" / "research" / "grants"
    grants.mkdir(parents=True)
    (grants / "pipeline.json").write_text("{not json", encoding="utf-8")

    assert emit_dossier("APP-1", root=tmp_path, now=NOW, compliance=clean_compliance) is None
    assert not (grants / DOSSIER_DIRNAME).exists()


def test_write_dossier_declines_a_none_rather_than_writing_a_husk(tmp_path):
    assert write_dossier(None, root=tmp_path) is None
    assert not (tmp_path / "data").exists()


# ── the write itself ─────────────────────────────────────────────────────────


def test_the_dossier_is_written_where_it_says_and_the_ledger_is_untouched(
    tmp_path, monkeypatch, clean_compliance
):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=5)])
    grants = root / "data" / "research" / "grants"
    ledger = grants / "pipeline.json"
    before = ledger.read_bytes()
    listing_before = sorted(p.name for p in grants.iterdir())

    path = emit_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)

    assert path == grants / DOSSIER_DIRNAME / "APP-1.md"
    assert path.read_text(encoding="utf-8").startswith("# Approval brief")
    # pipeline.json is the grant operator's and is written live.
    assert ledger.read_bytes() == before
    assert sorted(p.name for p in grants.iterdir()) == sorted([*listing_before, DOSSIER_DIRNAME])


def test_a_hostile_application_id_cannot_escape_the_dossiers_directory(
    tmp_path, monkeypatch, clean_compliance
):
    # An id is ledger data, not code. The ledger is written by another process.
    _perfect(monkeypatch)
    hostile = "../../../escaped"
    root = _root(tmp_path, [_app(hostile)])
    dossiers = root / "data" / "research" / "grants" / DOSSIER_DIRNAME

    path = emit_dossier(hostile, root=root, now=NOW, compliance=clean_compliance)

    assert path is not None
    assert path.parent == dossiers
    assert path.resolve().parent == dossiers.resolve()
    assert not (tmp_path.parent / "escaped.md").exists()


@pytest.mark.parametrize("app_id,stem", [
    ("APP-IFS-CFI-SEN-2511-20260709", "APP-IFS-CFI-SEN-2511-20260709"),
    ("APP/with/slashes", "APP_with_slashes"),
    ("...", "unnamed"),
])
def test_dossier_paths_are_sanitised(tmp_path, app_id, stem):
    assert dossier_path(app_id, root=tmp_path).name == f"{stem}.md"


def test_rewriting_a_dossier_replaces_it_rather_than_accumulating(
    tmp_path, monkeypatch, clean_compliance
):
    _perfect(monkeypatch)
    root = _root(tmp_path, [_app(days=5)])
    dossiers = root / "data" / "research" / "grants" / DOSSIER_DIRNAME

    emit_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)
    emit_dossier("APP-1", root=root, now=NOW + timedelta(days=1), compliance=clean_compliance)

    assert [p.name for p in dossiers.iterdir()] == ["APP-1.md"]


def test_an_explicit_root_is_honoured_and_the_environment_is_not_consulted(
    tmp_path, monkeypatch, clean_compliance
):
    # The lesson from ledger.grants_dir: a reader that falls back to the
    # configured directory when the caller's tree comes up empty leaks live data
    # into tests and hides faults.
    _perfect(monkeypatch)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setenv("AUREON_GRANTS_DIR", str(elsewhere))
    root = _root(tmp_path / "repo", [_app(days=5)])

    d = build_dossier("APP-1", root=root, now=NOW, compliance=clean_compliance)

    assert d is not None
    assert str(root) in d.ledger_path
    assert str(elsewhere) not in d.ledger_path
