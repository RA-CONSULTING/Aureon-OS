"""Portal truth versus the local ledger — the drift this organ must never miss.

Hermetic. Every test builds its own repository root under ``tmp_path`` (ledger
included) and passes it explicitly, so nothing here reads the live pipeline, the
live grants directory, or the live organism. No network, no browser, no portal
session: the portal side is a fixture built from one real dashboard read, and the
ledger side is synthetic.

The fixture is the eleven applications a human read off the live dashboard once,
by hand. It lives **here and only here** — the module under test contains no
funder vocabulary, no application numbers and no dates, so these tests are
evidence about the reconciler rather than a restatement of its constants.

Four properties are what this suite exists to pin, and each corresponds to a
mistake that has already been made against this data:

1. **A ledger record carrying a deadline the portal cannot corroborate is a
   phantom** — reported ``high``, with the detail stating in words that its
   deadline field cannot be trusted. An earlier reading believed such a record
   and reported a dead route as live with days remaining.
2. **A submitted portal application with no ledger record is ``high``.** That is
   filed work the organism cannot see at all.
3. **A clean match produces no drift** — so a clean report is a measurement and
   not the reconciler failing to look.
4. **The portal wins a deadline conflict**, and the detail says so.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aureon.grants.ledger import read_pipeline
from aureon.portals.reconcile import (
    KIND_ABSENT_FROM_PORTAL,
    KIND_DEADLINE_CONFLICT,
    KIND_MISSING_FROM_LEDGER,
    KIND_STATE_CONFLICT,
    REPORT_PREFIX,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    TOPIC_RECONCILED,
    emit_reconciliation,
    reconcile,
    render_markdown,
    report_path,
    write_report,
)
from aureon.portals.schemas import (
    STATE_IN_PROGRESS,
    STATE_INELIGIBLE,
    STATE_NOT_STARTED,
    STATE_SUBMITTED,
    PortalApplication,
    PortalSnapshot,
    normalise_state,
)

# ── the portal fixture: one real dashboard read, pinned ──────────────────────

PORTAL_READ_AT = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
FUNDER = "Innovate UK — Innovation Funding Service"
SOURCE = "dashboard text"

# Scope declared by the fixture, the way a reader declares it. "ifs" is
# deliberately NOT among these: the synthetic ledger ids below begin with it, and
# a token that matched them would make the scope tests pass for the wrong reason.
SCOPE_TOKENS = ("innovate uk", "innovation funding service", "ukri")
NUMBER_PATTERN = r"^\d{7,10}$"

SUBMITTED_TEXT = "Submitted — awaiting assessment"

#: Submitted / awaiting assessment on the live dashboard.
SUBMITTED_ROWS: tuple[tuple[str, str], ...] = (
    ("10210780", "Advanced Connectivity Technologies"),
    ("10210045", "CfI SEN"),
    ("10209601", "Next Wave Breakthrough Wave 1"),
    ("10210032", "Consumer Led Flexibility"),
    ("10209992", "Future Leaders Fellowships R11"),
    ("10163647", "ATI Programme"),
)

#: Empty drafts under the dashboard's "Not submitted" heading — no titles shown.
DRAFT_NUMBERS: tuple[str, ...] = ("10162520", "10167738", "10169785")

IN_PROGRESS_NUMBER = "10210100"
IN_PROGRESS_TITLE = "UK-Switzerland CR&D Round 3"
IN_PROGRESS_DEADLINE = datetime(2026, 9, 3, tzinfo=UTC)

INELIGIBLE_NUMBER = "10143721"
INELIGIBLE_TITLE = "Project A.L.F.I.E."


def _row(number: str, title: str, state_text: str, **kwargs: object) -> PortalApplication:
    """Build a row the way a reader would: normalise the prose, keep it too."""
    return PortalApplication(
        number=number,
        title=title,
        state=normalise_state(state_text),
        state_text=state_text,
        read_at=PORTAL_READ_AT,
        **kwargs,  # type: ignore[arg-type]
    )


def portal_applications() -> tuple[PortalApplication, ...]:
    rows = [_row(number, title, SUBMITTED_TEXT) for number, title in SUBMITTED_ROWS]
    rows.append(
        _row(
            IN_PROGRESS_NUMBER,
            IN_PROGRESS_TITLE,
            "In progress",
            deadline=IN_PROGRESS_DEADLINE,
            deadline_text="Deadline 3 Sept 2026",
            percent_complete=93,
            days_left=33,
        )
    )
    rows += [_row(number, "", "Not submitted") for number in DRAFT_NUMBERS]
    rows.append(_row(INELIGIBLE_NUMBER, INELIGIBLE_TITLE, "Ineligible"))
    return tuple(rows)


def portal_snapshot(*, skipped: tuple[str, ...] = ()) -> PortalSnapshot:
    return PortalSnapshot(
        available=True,
        read_at=PORTAL_READ_AT,
        applications=portal_applications(),
        source=SOURCE,
        funder=FUNDER,
        scope_tokens=SCOPE_TOKENS,
        number_pattern=NUMBER_PATTERN,
        skipped=skipped,
    )


# ── the synthetic ledger ─────────────────────────────────────────────────────


def clean_records() -> list[dict]:
    """A ledger that agrees with the portal on every application.

    Statuses are written in the live ledger's own idiom — compound, free-text,
    upper-case — because that is what the reconciler has to cope with. The
    deliberate detail is that none of them is a clean vocabulary word.
    """
    rows: list[dict] = [
        {
            "id": f"ifs_{number}",
            "name": title,
            "funder": "Innovate UK",
            "status": "SUBMITTED_AWAITING_ASSESSMENT",
        }
        for number, title in SUBMITTED_ROWS
    ]
    rows.append(
        {
            "id": f"ifs_{IN_PROGRESS_NUMBER}",
            "name": IN_PROGRESS_TITLE,
            "funder": "Innovate UK",
            "status": "IN_PROGRESS_93_PERCENT_NOT_SUBMITTED",
            "deadline": "2026-09-03T00:00:00+00:00",
        }
    )
    rows += [
        {
            "id": f"ifs_{number}",
            "name": "",
            "funder": "Innovate UK",
            "status": "NOT_SUBMITTED_EMPTY_DRAFT",
        }
        for number in DRAFT_NUMBERS
    ]
    rows.append(
        {
            "id": f"ifs_{INELIGIBLE_NUMBER}",
            "name": INELIGIBLE_TITLE,
            "funder": "Innovate UK",
            "status": "NOT_ELIGIBLE",
        }
    )
    return rows


def _grants_dir(root: Path) -> Path:
    """Built independently of the module under test, on purpose."""
    return root / "data" / "research" / "grants"


def write_ledger(root: Path, records: list[dict]) -> Path:
    directory = _grants_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "pipeline.json"
    path.write_text(json.dumps({"active_applications": records}, indent=2), encoding="utf-8")
    return path


def ledger_state(root: Path, records: list[dict]):
    write_ledger(root, records)
    return read_pipeline(now=PORTAL_READ_AT, directory=_grants_dir(root))


@pytest.fixture(autouse=True)
def _no_live_traces(tmp_path, monkeypatch):
    """Keep sub-field publication from writing into the repository's state dir."""
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path / "bus_trace"))


class _Bus:
    """Records what was published; publishes nothing anywhere."""

    def __init__(self) -> None:
        self.thoughts: list = []

    def publish(self, thought):
        self.thoughts.append(thought)
        return thought

    def topics(self) -> list[str]:
        return [t.topic for t in self.thoughts]

    def payload(self, topic: str) -> dict:
        for thought in self.thoughts:
            if thought.topic == topic:
                return thought.payload
        raise AssertionError(f"nothing published on {topic}: saw {self.topics()}")


# ── 0. the fixture itself ────────────────────────────────────────────────────


def test_not_submitted_is_never_read_as_submitted():
    """The one normalisation error that would invert the whole reconciliation.

    "Not submitted" *contains* "submitted". If the vocabulary mapping tested them
    in the wrong order, three empty drafts would be reported as filed with the
    funder — and every state conflict below would silently invert.
    """
    assert normalise_state("Not submitted") == STATE_NOT_STARTED
    assert normalise_state(SUBMITTED_TEXT) == STATE_SUBMITTED
    assert normalise_state("In progress") == STATE_IN_PROGRESS
    assert normalise_state("Ineligible") == STATE_INELIGIBLE

    states = {a.number: a.state for a in portal_applications()}
    assert [states[n] for n in DRAFT_NUMBERS] == [STATE_NOT_STARTED] * 3
    assert states[INELIGIBLE_NUMBER] == STATE_INELIGIBLE
    assert states[IN_PROGRESS_NUMBER] == STATE_IN_PROGRESS
    assert all(states[n] == STATE_SUBMITTED for n, _ in SUBMITTED_ROWS)


# ── 1. the phantom ───────────────────────────────────────────────────────────


PHANTOM = {
    "id": "full_adopt_grant_round_8",
    "name": "Full ADOPT Grant: Round 8",
    "funder": "Innovate UK",
    "status": "WATCHING_ROUTE_OPEN",
    "deadline": "2026-08-12T12:00:00+00:00",
}


def test_phantom_deadline_record_is_high_and_its_deadline_declared_untrustworthy(tmp_path):
    """The whole reason this capability exists.

    A ledger record carrying a deadline for something the portal has never heard
    of reads exactly like a live route with days remaining. The reconciler must
    name it, rank it ``high``, and say in words that the date cannot be trusted —
    a finding that merely said "not found on portal" would leave the next reader
    free to believe the deadline again.
    """
    state = ledger_state(tmp_path, clean_records() + [PHANTOM])
    report = reconcile(portal_snapshot(), state)

    assert report.available
    phantoms = report.of_kind(KIND_ABSENT_FROM_PORTAL)
    assert len(phantoms) == 1, [d.to_dict() for d in report.drifts]
    drift = phantoms[0]

    assert drift.severity == SEVERITY_HIGH
    assert drift.ledger_id == PHANTOM["id"]
    assert drift.portal_number is None
    assert "cannot be trusted" in drift.detail
    assert "deadline field" in drift.detail
    # It must name the untrusted date so a human can go and check that exact claim.
    assert "2026-08-12" in drift.detail
    assert PHANTOM["id"] in report.ledger_only

    # And nothing else drifted: the phantom is the only finding, so the test is
    # about the phantom rule rather than about general noise.
    assert len(report.drifts) == 1
    assert report.pressure is not None and report.pressure > 0.0

    document = render_markdown(report, root=tmp_path)
    assert "PHANTOM" in document
    assert "cannot be trusted" in document
    assert "Full ADOPT Grant: Round 8" in document


def test_a_phantom_without_a_deadline_is_ranked_below_one_with_a_deadline(tmp_path):
    """Severity tracks consequence: a dated phantom manufactures urgency."""
    undated = dict(PHANTOM, id="watch_item_no_date")
    undated.pop("deadline")
    state = ledger_state(tmp_path, clean_records() + [undated])
    report = reconcile(portal_snapshot(), state)

    (drift,) = report.of_kind(KIND_ABSENT_FROM_PORTAL)
    assert drift.severity == SEVERITY_MEDIUM
    assert "no deadline" in drift.detail
    assert "cannot be trusted" not in drift.detail


def test_a_partial_portal_read_qualifies_the_phantom_claim_without_dropping_it(tmp_path):
    """A row the reader could not read might be the phantom's application.

    The finding still stands — dropping it would hide real drift — but it must
    not be stated as a certainty the read did not support.
    """
    state = ledger_state(tmp_path, clean_records() + [PHANTOM])
    report = reconcile(portal_snapshot(skipped=("row 12: truncated",)), state)

    (drift,) = report.of_kind(KIND_ABSENT_FROM_PORTAL)
    assert drift.severity == SEVERITY_HIGH
    assert "PARTIAL" in drift.detail
    assert report.portal_read_partial
    assert "row 12: truncated" in render_markdown(report, root=tmp_path)


# ── 2. live work the organism cannot see ─────────────────────────────────────


def test_submitted_portal_application_missing_from_the_ledger_is_high(tmp_path):
    """Two of the real absences were submitted applications. That is the high case."""
    absent_submitted = "10210780"
    absent_draft = DRAFT_NUMBERS[0]
    kept = [
        r
        for r in clean_records()
        if r["id"] not in (f"ifs_{absent_submitted}", f"ifs_{absent_draft}")
    ]
    state = ledger_state(tmp_path, kept)
    report = reconcile(portal_snapshot(), state)

    by_number = {d.portal_number: d for d in report.of_kind(KIND_MISSING_FROM_LEDGER)}
    assert set(by_number) == {absent_submitted, absent_draft}

    submitted = by_number[absent_submitted]
    assert submitted.severity == SEVERITY_HIGH
    assert submitted.ledger_id is None
    assert "SUBMITTED" in submitted.detail
    assert "cannot see" in submitted.detail
    # The title is quoted so the finding is actionable without opening the portal.
    assert "Advanced Connectivity Technologies" in submitted.detail

    # An unstarted draft is real drift but not live work: medium, not high.
    assert by_number[absent_draft].severity == SEVERITY_MEDIUM

    assert set(report.portal_only) == {absent_submitted, absent_draft}
    assert report.high == (submitted,)


# ── 3. a clean match is a measurement ────────────────────────────────────────


def test_a_clean_match_produces_no_drift(tmp_path):
    """No drift must mean "compared and agreed", never "did not look"."""
    state = ledger_state(tmp_path, clean_records())
    report = reconcile(portal_snapshot(), state)

    assert report.available
    assert report.blocker is None
    assert report.drifts == ()
    assert report.clean
    assert report.portal_only == ()
    assert report.ledger_only == ()

    # The evidence that it actually looked: every portal application was linked
    # to a ledger record, by the record's id.
    assert report.portal_count == 11
    assert report.ledger_count == 11
    assert report.in_scope_ledger_count == 11
    assert report.out_of_scope_ledger_count == 0
    assert len(report.matched) == 11
    assert {m.matched_on for m in report.matched} == {"id"}
    assert {m.portal_number for m in report.matched} == set(
        [n for n, _ in SUBMITTED_ROWS] + list(DRAFT_NUMBERS) + [IN_PROGRESS_NUMBER, INELIGIBLE_NUMBER]
    )
    # Every matched state was actually comparable — none of the eleven passed by
    # default. A clean report built on eleven uncompared states would be worthless.
    assert report.unconfirmed_states == 0
    assert report.ambiguous_ledger_ids == ()
    assert report.pressure == 0.0


def test_out_of_scope_ledger_records_are_never_called_missing(tmp_path):
    """A Horizon Europe record is not missing from a UK dashboard."""
    other_funder = {
        "id": "horizon_ep_cluster4_call",
        "name": "Horizon Europe Cluster 4",
        "funder": "European Commission",
        "status": "PREPARING",
        "deadline": "2026-10-01T12:00:00+00:00",
    }
    state = ledger_state(tmp_path, clean_records() + [other_funder])
    report = reconcile(portal_snapshot(), state)

    assert report.drifts == ()
    assert report.ledger_only == ()
    assert report.out_of_scope_ledger_count == 1
    assert report.in_scope_ledger_count == 11
    assert "other funders" in report.scope_note


def test_a_snapshot_with_no_declared_scope_makes_no_absence_claims(tmp_path):
    """Without a declared scope the reconciler declines to judge, and says why."""
    snapshot = PortalSnapshot(
        available=True,
        read_at=PORTAL_READ_AT,
        applications=portal_applications(),
        source=SOURCE,
        funder=FUNDER,
    )
    state = ledger_state(tmp_path, clean_records() + [PHANTOM])
    report = reconcile(snapshot, state)

    assert report.of_kind(KIND_ABSENT_FROM_PORTAL) == ()
    assert report.ledger_only == ()
    assert "no ledger record was judged absent" in report.scope_note
    assert "partial reconciliation" in report.scope_note
    assert "partial reconciliation" in render_markdown(report, root=tmp_path)


# ── 4. the portal wins ───────────────────────────────────────────────────────


def _with_deadline(records: list[dict], deadline: str) -> list[dict]:
    for record in records:
        if record["id"] == f"ifs_{IN_PROGRESS_NUMBER}":
            record["deadline"] = deadline
    return records


def test_the_portal_wins_a_deadline_conflict(tmp_path):
    """The portal is the funder's system of record and the detail must say so."""
    state = ledger_state(tmp_path, _with_deadline(clean_records(), "2026-09-17T12:00:00+00:00"))
    report = reconcile(portal_snapshot(), state)

    (drift,) = report.of_kind(KIND_DEADLINE_CONFLICT)
    assert drift.portal_number == IN_PROGRESS_NUMBER
    assert drift.ledger_id == f"ifs_{IN_PROGRESS_NUMBER}"
    assert "portal is authoritative" in drift.detail.lower()
    # Both dates named, so the correction needs no second lookup.
    assert "2026-09-03" in drift.detail
    assert "2026-09-17" in drift.detail
    # A ledger date LATER than the portal's is the direction that misses the
    # real close, so it is the high one.
    assert drift.severity == SEVERITY_HIGH
    assert "LATER" in drift.detail

    assert len(report.drifts) == 1
    assert "the portal wins" in render_markdown(report, root=tmp_path).lower()


def test_a_ledger_deadline_earlier_than_the_portals_is_reported_but_ranked_lower(tmp_path):
    """Overstated pressure is drift; it is not the dangerous direction."""
    state = ledger_state(tmp_path, _with_deadline(clean_records(), "2026-08-20T12:00:00+00:00"))
    report = reconcile(portal_snapshot(), state)

    (drift,) = report.of_kind(KIND_DEADLINE_CONFLICT)
    assert drift.severity == SEVERITY_MEDIUM
    assert "portal is authoritative" in drift.detail.lower()
    assert "overstated" in drift.detail


def test_transcription_noise_under_a_day_is_not_reported_as_drift(tmp_path):
    """The portal prints a date, the ledger stores a timestamp. Same deadline."""
    state = ledger_state(tmp_path, _with_deadline(clean_records(), "2026-09-03T17:00:00+00:00"))
    report = reconcile(portal_snapshot(), state)
    assert report.of_kind(KIND_DEADLINE_CONFLICT) == ()


def test_a_future_deadline_on_an_application_the_funder_already_holds_is_drift(tmp_path):
    """A submitted application with a live-looking date manufactures urgency."""
    records = clean_records()
    for record in records:
        if record["id"] == "ifs_10210780":
            record["deadline"] = "2026-12-01T12:00:00+00:00"
    state = ledger_state(tmp_path, records)
    report = reconcile(portal_snapshot(), state)

    (drift,) = report.of_kind(KIND_DEADLINE_CONFLICT)
    assert drift.portal_number == "10210780"
    assert drift.severity == SEVERITY_MEDIUM
    assert "must not be read as time remaining" in drift.detail
    assert "portal is authoritative" in drift.detail.lower()


# ── state conflicts, in both directions ──────────────────────────────────────


def test_ledger_denying_a_submission_the_portal_holds_is_high(tmp_path):
    records = clean_records()
    for record in records:
        if record["id"] == "ifs_10163647":
            record["status"] = "PACK_READY_NOT_SUBMITTED_BY_OPERATOR"
    state = ledger_state(tmp_path, records)
    report = reconcile(portal_snapshot(), state)

    (drift,) = report.of_kind(KIND_STATE_CONFLICT)
    assert drift.severity == SEVERITY_HIGH
    assert drift.portal_number == "10163647"
    assert "portal is authoritative" in drift.detail.lower()
    assert "not submitted" in drift.detail.lower()


def test_ledger_claiming_a_submission_the_portal_has_not_received_is_high(tmp_path):
    """The dangerous direction: nobody works on it because the ledger says done."""
    records = clean_records()
    for record in records:
        if record["id"] == f"ifs_{IN_PROGRESS_NUMBER}":
            record["status"] = "SUBMITTED_2026_07_01"
    state = ledger_state(tmp_path, records)
    report = reconcile(portal_snapshot(), state)

    (drift,) = report.of_kind(KIND_STATE_CONFLICT)
    assert drift.severity == SEVERITY_HIGH
    assert drift.portal_number == IN_PROGRESS_NUMBER
    assert "still outstanding" in drift.detail


def test_an_uninterpretable_ledger_status_is_counted_not_classified(tmp_path):
    """The ledger's status is prose. Silence is reported as silence."""
    records = clean_records()
    for record in records:
        if record["id"] == "ifs_10209601":
            record["status"] = "SERAPHIM_DECK_ROUTE_UNDER_REVIEW_BY_PANEL"
    state = ledger_state(tmp_path, records)
    report = reconcile(portal_snapshot(), state)

    assert report.of_kind(KIND_STATE_CONFLICT) == ()
    assert report.unconfirmed_states == 1
    document = render_markdown(report, root=tmp_path)
    assert "no comparable state" in document
    assert "silence, not agreement" in document


def test_a_status_that_both_claims_and_denies_submission_is_read_as_a_denial(tmp_path):
    """Prepared-and-not-sent is not sent. The denial wins."""
    records = clean_records()
    for record in records:
        if record["id"] == "ifs_10210045":
            record["status"] = "SUBMITTED_PACK_ASSEMBLED_BUT_NOT_SUBMITTED_TO_FUNDER"
    state = ledger_state(tmp_path, records)
    report = reconcile(portal_snapshot(), state)

    (drift,) = report.of_kind(KIND_STATE_CONFLICT)
    assert drift.portal_number == "10210045"
    assert drift.severity == SEVERITY_HIGH


# ── matching ─────────────────────────────────────────────────────────────────


def test_a_number_in_a_note_matches_and_the_field_is_recorded(tmp_path):
    """That is how the numbers actually appear — and a note is weaker evidence."""
    records = [r for r in clean_records() if r["id"] != "ifs_10209992"]
    records.append(
        {
            "id": "flf_round_11_bid",
            "name": "Future Leaders Fellowships R11",
            "funder": "UKRI",
            "status": "SUBMITTED_AWAITING_ASSESSMENT",
            "notes": "Filed on the IFS dashboard as application 10209992.",
        }
    )
    state = ledger_state(tmp_path, records)
    report = reconcile(portal_snapshot(), state)

    assert report.drifts == ()
    matched = {m.portal_number: m for m in report.matched}
    assert matched["10209992"].ledger_id == "flf_round_11_bid"
    assert matched["10209992"].matched_on == "notes"


def test_a_number_inside_a_longer_number_is_not_a_match(tmp_path):
    """A false match silences the missing-from-ledger finding it displaced."""
    records = [r for r in clean_records() if r["id"] != "ifs_10210045"]
    records.append(
        {
            "id": "unrelated_ref_102100456789",
            "name": "Unrelated internal reference",
            "funder": "Innovate UK",
            "status": "NOTE_ONLY",
        }
    )
    state = ledger_state(tmp_path, records)
    report = reconcile(portal_snapshot(), state)

    assert "10210045" in report.portal_only
    assert not any(m.portal_number == "10210045" for m in report.matched)


def test_a_record_naming_two_applications_is_reported_ambiguous_not_compared(tmp_path):
    """Its status and deadline belong to neither, so neither is compared."""
    records = [
        r for r in clean_records() if r["id"] not in ("ifs_10210780", "ifs_10163647")
    ]
    records.append(
        {
            "id": "combined_bid_note",
            "name": "Two bids tracked together",
            "funder": "Innovate UK",
            "status": "SUBMITTED_AWAITING_ASSESSMENT",
            "notes": "Covers 10210780 and 10163647.",
            "deadline": "2026-01-01T12:00:00+00:00",
        }
    )
    state = ledger_state(tmp_path, records)
    report = reconcile(portal_snapshot(), state)

    assert report.ambiguous_ledger_ids == ("combined_bid_note",)
    assert report.drifts == ()
    assert {m.portal_number for m in report.matched if m.ledger_id == "combined_bid_note"} == {
        "10210780",
        "10163647",
    }
    assert "more than one portal application" in render_markdown(report, root=tmp_path)


# ── absence is not agreement ─────────────────────────────────────────────────


def test_an_unread_portal_is_not_a_clean_report(tmp_path):
    """No session, no reconciliation — and the document must not read as clean."""
    snapshot = PortalSnapshot.blocked(
        "no authenticated dashboard tab found — the portal session belongs to the "
        "operator's browser",
        read_at=PORTAL_READ_AT,
        source=SOURCE,
        funder=FUNDER,
    )
    state = ledger_state(tmp_path, clean_records())
    report = reconcile(snapshot, state)

    assert not report.available
    assert not report.clean
    assert report.drifts == ()
    assert report.pressure is None
    assert report.symbolic_life_score is None
    assert "portal not read" in (report.blocker or "")
    assert "operator's browser" in (report.blocker or "")

    document = render_markdown(report, root=tmp_path)
    assert "No reconciliation was performed" in document
    assert "not a clean result" in document.lower()


def test_an_unreadable_ledger_blocks_the_reconciliation(tmp_path):
    """The other half of the same rule."""
    state = read_pipeline(now=PORTAL_READ_AT, directory=tmp_path / "nowhere")
    report = reconcile(portal_snapshot(), state)

    assert not report.available
    assert "ledger not read" in (report.blocker or "")
    assert report.pressure is None


def test_a_snapshot_of_the_wrong_shape_reports_absence_rather_than_raising():
    """Nothing a caller can hand this organ makes it throw."""
    report = reconcile(object(), None)
    assert not report.available
    assert "no .applications" in (report.blocker or "")


# ── the document, and the operator's file ────────────────────────────────────


def test_the_document_is_written_dated_and_the_ledger_is_never_touched(tmp_path):
    state = ledger_state(tmp_path, clean_records() + [PHANTOM])
    ledger_file = _grants_dir(tmp_path) / "pipeline.json"
    before = ledger_file.read_bytes()

    report = reconcile(portal_snapshot(), state)
    path = write_report(report, root=tmp_path)

    assert path == report_path(report.generated_at, root=tmp_path)
    assert path.name == f"{REPORT_PREFIX}20260731.md"
    assert path.parent == _grants_dir(tmp_path)
    # The operator owns the ledger. Byte-for-byte unchanged.
    assert ledger_file.read_bytes() == before

    document = path.read_text(encoding="utf-8")
    assert "grant operator's file" in document
    assert "recommendation" in document
    assert "Recommended corrections" in document
    # The recommendation for a phantom is to stop trusting its date, not to
    # rewrite the ledger automatically.
    assert "clear or annotate its deadline field" in document


def test_an_unavailable_report_still_leaves_a_trace(tmp_path):
    """An unreconciled cycle must not look like a clean one by leaving no file."""
    _grants_dir(tmp_path).mkdir(parents=True, exist_ok=True)
    snapshot = PortalSnapshot.blocked("no session", read_at=PORTAL_READ_AT, funder=FUNDER)
    state = ledger_state(tmp_path, clean_records())
    report = reconcile(snapshot, state)

    path = write_report(report, root=tmp_path)
    assert path is not None and path.exists()
    assert "No reconciliation was performed" in path.read_text(encoding="utf-8")


def test_the_document_name_cannot_collide_with_the_operators_own_sheet():
    """``dossier.read_approval_rule`` globs ``RECONCILIATION_*.md`` for a rule a
    human owns. A generated file matching that glob would become the source of
    it."""
    from aureon.grants.dossier import RECONCILIATION_GLOB

    name = f"{REPORT_PREFIX}20260731.md"
    assert not Path(name).match(RECONCILIATION_GLOB)


# ── the organism senses it ───────────────────────────────────────────────────


def test_drift_is_published_and_presses_the_shared_field(tmp_path):
    bus = _Bus()
    state = ledger_state(tmp_path, clean_records() + [PHANTOM])
    report, path = emit_reconciliation(portal_snapshot(), state=state, root=tmp_path, bus=bus)

    assert path is not None
    payload = bus.payload(TOPIC_RECONCILED)
    assert payload["available"] is True
    assert payload["drift_count"] == 1
    assert payload["counts_by_severity"]["high"] == 1
    # Rounded on the way out, deliberately: the payload is telemetry, and 17
    # significant figures of a weighted index would imply a precision it has not got.
    assert report.pressure is not None
    assert payload["pressure"] == round(report.pressure, 4)
    # JSON-serialisable, because it crosses a bus.
    json.dumps(payload)

    field = bus.payload("symbolic.life.subfield")
    assert field["source"] == "portal"
    assert field["symbolic_life_score"] == pytest.approx(1.0 - (report.pressure or 0.0))
    assert field["symbolic_life_score"] < 1.0


def test_a_clean_reconciliation_announces_itself_but_claims_no_coherence(tmp_path):
    """This organ looked at one dashboard. It has no standing to publish a 1.0."""
    bus = _Bus()
    state = ledger_state(tmp_path, clean_records())
    report, _ = emit_reconciliation(portal_snapshot(), state=state, root=tmp_path, bus=bus)

    assert report.clean
    assert TOPIC_RECONCILED in bus.topics()
    assert "symbolic.life.subfield" not in bus.topics()


def test_an_unavailable_reconciliation_is_still_announced(tmp_path):
    bus = _Bus()
    _grants_dir(tmp_path).mkdir(parents=True, exist_ok=True)
    snapshot = PortalSnapshot.blocked("no session", read_at=PORTAL_READ_AT, funder=FUNDER)
    emit_reconciliation(snapshot, state=ledger_state(tmp_path, clean_records()),
                        root=tmp_path, bus=bus)

    payload = bus.payload(TOPIC_RECONCILED)
    assert payload["available"] is False
    assert payload["pressure"] is None
    assert "symbolic.life.subfield" not in bus.topics()
