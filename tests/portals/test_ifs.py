"""The IFS dashboard reader, tested hermetically.

No network, no browser, no clock. Every read goes through injected text or an
injected fetcher, ``read_at`` is pinned, and the two tests that exercise the
default CDP path are arranged to fail *before* a socket could be opened — one on
the loopback refusal, one on a monkeypatched dependency probe — with
``_cdp_targets`` replaced by a tripwire that fails the test if anything reaches
for the network. That matters more than usual here: the thing this reader attaches
to is the operator's real, signed-in browser, and a test suite that could touch it
would be reading a live funding portal from CI.

**Where the fixture comes from, and what it does and does not prove.**
``DASHBOARD_TEXT`` encodes a real reading of the live applicant dashboard: eleven
applications, their numbers, the section each sat under, and the three metrics
shown against the single in-progress row. Those values are ground truth and the
tests pin them.

The *layout* is reconstructed, and that limit is stated rather than glossed: the
reading captured what each row said, not the page's exact line order, so this
fixture is a regression contract for the parser's rules rather than a byte-level
capture of the page. Two consequences are deliberate:

* where the reading captured only a number — the three empty drafts — the fixture
  carries only a number, and the test asserts the parser reports ``title == ""``.
  It must not invent a name for a row it never saw named. That is the absence rule
  under test, not a gap in the fixture.
* where the reading captured one name per row, the fixture carries one name. The
  parser assigns it to ``title`` and leaves ``competition`` empty rather than
  splitting one observed string into two claimed fields. ``test_html_dashboard_*``
  covers the labelled-competition shape separately.

Fidelity to the live page's markup stays unverified until the reader is pointed at
it once; the shape-tolerance tests below (HTML input, wrapped label, alternate
heading wording) exist so that first live run has slack to land in.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aureon.portals import ifs
from aureon.portals.ifs import (
    DASHBOARD_URL,
    PortalBlocked,
    parse_dashboard,
    parse_date,
    read_dashboard,
    resolve_cdp_url,
)
from aureon.portals.schemas import (
    PORTAL_STATES,
    STATE_NOT_STARTED,
    STATE_SUBMITTED,
    PortalState,
)

READ_AT = datetime(2026, 7, 31, 12, 0, 0, tzinfo=timezone.utc)


# ── ground truth, as read from the live dashboard ─────────────────────────────

DASHBOARD_TEXT = """GOV.UK
Apply for innovation funding
Your applications

Applications in progress

UK-Switzerland CR&D Round 3
Application number: 10210100
33 days left
Deadline 3 Sept 2026
93% complete
Continue

Applications awaiting assessment

Advanced Connectivity Technologies
Application number: 10210780
Submitted

CfI SEN
Application number: 10210045
Submitted

Next Wave Breakthrough Wave 1
Application number: 10209601
Submitted

Consumer Led Flexibility
Application number: 10210032
Submitted

Future Leaders Fellowships R11
Application number: 10209992
Submitted

ATI Programme
Application number: 10163647
Submitted

Applications not submitted

Application number: 10162520
Application number: 10167738
Application number: 10169785

Ineligible applications

Project A.L.F.I.E.
Application number: 10143721
Ineligible

Sign out
"""

# The reading, as a table. Kept next to the fixture so a future correction is a
# one-place edit rather than a hunt through assertions.
SUBMITTED_NUMBERS = ("10210780", "10210045", "10209601", "10210032", "10209992", "10163647")
NOT_SUBMITTED_NUMBERS = ("10162520", "10167738", "10169785")
IN_PROGRESS_NUMBER = "10210100"
INELIGIBLE_NUMBER = "10143721"

EXPECTED_TITLES = {
    "10210100": "UK-Switzerland CR&D Round 3",
    "10210780": "Advanced Connectivity Technologies",
    "10210045": "CfI SEN",
    "10209601": "Next Wave Breakthrough Wave 1",
    "10210032": "Consumer Led Flexibility",
    "10209992": "Future Leaders Fellowships R11",
    "10163647": "ATI Programme",
    "10143721": "Project A.L.F.I.E.",
}

ALL_NUMBERS = (
    (IN_PROGRESS_NUMBER,) + SUBMITTED_NUMBERS + NOT_SUBMITTED_NUMBERS + (INELIGIBLE_NUMBER,)
)


@pytest.fixture()
def snapshot():
    return parse_dashboard(DASHBOARD_TEXT, read_at=READ_AT)


# ── the eleven rows ──────────────────────────────────────────────────────────


def test_all_eleven_rows_parse(snapshot):
    assert snapshot.available is True
    assert snapshot.blocker is None
    assert len(snapshot.applications) == 11
    assert set(snapshot.numbers) == set(ALL_NUMBERS)
    # Nothing was skipped, so the count above is a measurement and not a floor.
    assert snapshot.skipped == ()
    assert snapshot.fully_read is True
    assert snapshot.parse_blocker is None


def test_every_row_lands_in_the_state_its_section_declared(snapshot):
    by_number = {app.number: app for app in snapshot.applications}

    for number in SUBMITTED_NUMBERS:
        assert by_number[number].state == PortalState.SUBMITTED, number
    for number in NOT_SUBMITTED_NUMBERS:
        assert by_number[number].state == PortalState.NOT_SUBMITTED, number
    assert by_number[IN_PROGRESS_NUMBER].state == PortalState.IN_PROGRESS
    assert by_number[INELIGIBLE_NUMBER].state == PortalState.INELIGIBLE


def test_not_submitted_is_never_read_as_submitted(snapshot):
    """The one substring mistake that would matter most.

    "Not submitted" contains "submitted". A reader that matched naively would
    report three empty drafts as filed with the funder — work still owed,
    reported as done, on the funder's own authority. Six rows are submitted and
    exactly six.
    """
    by_state = {}
    for app in snapshot.applications:
        by_state.setdefault(app.state, []).append(app.number)

    assert sorted(by_state[PortalState.SUBMITTED]) == sorted(SUBMITTED_NUMBERS)
    assert sorted(by_state[PortalState.NOT_SUBMITTED]) == sorted(NOT_SUBMITTED_NUMBERS)
    assert PortalState.NOT_SUBMITTED not in by_state[PortalState.SUBMITTED]


def test_titles_are_read_where_the_page_named_them(snapshot):
    by_number = {app.number: app for app in snapshot.applications}
    for number, title in EXPECTED_TITLES.items():
        assert by_number[number].title == title, number


def test_unnamed_draft_rows_are_left_unnamed(snapshot):
    """Absence stays absence.

    The manual read captured only the numbers of the three empty drafts, so the
    fixture carries only numbers, so the parser must report no title. A reader
    that filled these in — from the section heading, from a neighbouring row,
    from anywhere — would be manufacturing evidence about the funder's records.
    """
    by_number = {app.number: app for app in snapshot.applications}
    for number in NOT_SUBMITTED_NUMBERS:
        assert by_number[number].title == "", number
        assert by_number[number].competition == "", number


# ── the in-progress row: the only one with live numbers on it ─────────────────


def test_in_progress_row_yields_percent_days_and_a_real_deadline(snapshot):
    row = {app.number: app for app in snapshot.applications}[IN_PROGRESS_NUMBER]

    assert row.percent_complete == 93
    assert row.days_left == 33
    assert row.deadline == datetime(2026, 9, 3, tzinfo=timezone.utc)
    # The page said a date and no clock time, so the evidence is kept and the
    # midnight component is auditable as a representation rather than a reading.
    assert row.deadline_text == "Deadline 3 Sept 2026"
    assert row.state == PortalState.IN_PROGRESS


def test_govuk_september_abbreviation_parses():
    """"Sept" is four letters and `%b` cannot parse it.

    This is the whole reason :func:`ifs.parse_date` exists instead of a strptime
    call, and it lands on the single most consequential date on the dashboard —
    the only open application's deadline.
    """
    parsed, evidence = parse_date("Deadline 3 Sept 2026")
    assert parsed == datetime(2026, 9, 3, tzinfo=timezone.utc)
    assert evidence == "Deadline 3 Sept 2026"

    for text, expected in (
        ("Deadline 3 September 2026", datetime(2026, 9, 3, tzinfo=timezone.utc)),
        ("Deadline 1 Sep 2026", datetime(2026, 9, 1, tzinfo=timezone.utc)),
        ("Closes 12 Aug 2026", datetime(2026, 8, 12, tzinfo=timezone.utc)),
        ("Deadline 2026-09-03", datetime(2026, 9, 3, tzinfo=timezone.utc)),
    ):
        assert parse_date(text)[0] == expected, text


def test_an_unreadable_date_is_none_and_keeps_its_evidence():
    for text in ("Deadline 3 Smarch 2026", "Deadline 31 Feb 2026", "Deadline soon", "Deadline TBC"):
        parsed, evidence = parse_date(text)
        assert parsed is None, text
        # The words are preserved even though the value could not be: evidence of
        # an unreadable date is worth more than silence about it.
        assert evidence == text, text


def test_submitted_rows_carry_no_invented_deadline_or_progress(snapshot):
    """A filed application shows no countdown, so none is reported.

    This is the fault that a portal reader exists to prevent: a ledger row whose
    deadline field was meaningless was once read as a live route with days left on
    it. Absent fields must arrive as None, not as zero and not as a date.
    """
    by_number = {app.number: app for app in snapshot.applications}
    for number in SUBMITTED_NUMBERS + NOT_SUBMITTED_NUMBERS + (INELIGIBLE_NUMBER,):
        row = by_number[number]
        assert row.deadline is None, number
        assert row.deadline_text == "", number
        assert row.days_left is None, number
        assert row.percent_complete is None, number


def test_every_row_carries_its_provenance(snapshot):
    for app in snapshot.applications:
        assert app.read_at == READ_AT
        assert app.source_url == DASHBOARD_URL
        # innerText carries no hyperlinks, so a per-row link is absent, not faked.
        assert app.url == ""
    assert snapshot.read_at == READ_AT
    assert snapshot.funder
    assert snapshot.scope_declared is True


# ── a garbled row is skipped, never half-parsed ──────────────────────────────


GARBLED_TEXT = """Applications awaiting assessment

Readable Row
Application number: 10210780
Submitted

Truncated Row
Application number: 1021
Submitted
"""


def test_a_truncated_row_is_skipped_with_a_blocker():
    snap = parse_dashboard(GARBLED_TEXT, read_at=READ_AT)

    # The good row survives — failing the whole read over one bad row would throw
    # away a real observation.
    assert snap.available is True
    assert snap.numbers == ("10210780",)

    # The bad row is absent from applications entirely: no husk, no placeholder
    # number, no row carrying only a title.
    assert all(app.number != "1021" for app in snap.applications)
    assert not any(app.title == "Truncated Row" for app in snap.applications)

    # ...and it is reported, naming the fragment and the row it came from.
    assert len(snap.skipped) == 1
    assert "1021" in snap.skipped[0]
    assert "Truncated Row" in snap.skipped[0]
    assert snap.fully_read is False
    assert snap.parse_blocker is not None
    assert "1021" in snap.parse_blocker


def test_a_number_label_with_nothing_after_it_is_skipped():
    snap = parse_dashboard(
        "Applications awaiting assessment\n\nNameless Row\nApplication number:\n",
        read_at=READ_AT,
    )
    assert snap.applications == ()
    assert len(snap.skipped) == 1
    assert "Nameless Row" in snap.skipped[0]
    assert snap.parse_blocker is not None


def test_a_row_whose_deadline_is_unreadable_keeps_the_row_and_reports_the_field():
    """The row is identifiable, so it is kept; the field is not, so it is None.

    Skipping is for rows that cannot be *identified*. A readable row with one
    unreadable field is still a real observation of that application's existence
    and state, and discarding it would lose more than it protects — so the field
    goes absent and the failure is named.
    """
    snap = parse_dashboard(
        "Applications in progress\n\nSome Row\nApplication number: 10210100\n"
        "Deadline 3 Smarch 2026\n50% complete\n",
        read_at=READ_AT,
    )
    row = snap.applications[0]
    assert row.number == "10210100"
    assert row.deadline is None
    assert row.deadline_text == "Deadline 3 Smarch 2026"
    assert row.percent_complete == 50
    assert any("Smarch" in note for note in snap.skipped)
    assert snap.fully_read is False


def test_a_duplicate_number_is_reported_not_double_counted():
    snap = parse_dashboard(
        "Applications awaiting assessment\n\nA\nApplication number: 10210780\n"
        "Submitted\n\nB\nApplication number: 10210780\nSubmitted\n",
        read_at=READ_AT,
    )
    assert snap.numbers == ("10210780",)
    assert any("more than once" in note for note in snap.skipped)


# ── shape tolerance: the live markup is not yet verified ─────────────────────


HTML_DASHBOARD = """<main id="main-content">
  <h1>Your applications</h1>
  <h2>Applications in progress</h2>
  <ul class="govuk-list">
    <li>
      <h3><a href="/application/10210100">A Project Title</a></h3>
      <p>Competition: An Example Competition Round 3</p>
      <p>Application number: <span>10210100</span></p>
      <p>12&nbsp;days left</p>
      <p>Deadline 3 September 2026</p>
      <p>50% complete</p>
      <a href="/application/10210100">Continue</a>
    </li>
  </ul>
  <script>var tracking = "Application number: 99999999";</script>
</main>
"""


def test_html_dashboard_is_reduced_and_parsed():
    snap = parse_dashboard(HTML_DASHBOARD, read_at=READ_AT)
    assert snap.available is True
    assert len(snap.applications) == 1

    row = snap.applications[0]
    # The number sits inside a <span>: breaking on inline tags would have split
    # the label from its value and lost the row's identity.
    assert row.number == "10210100"
    assert row.title == "A Project Title"
    assert row.competition == "An Example Competition Round 3"
    assert row.days_left == 12
    assert row.percent_complete == 50
    assert row.deadline == datetime(2026, 9, 3, tzinfo=timezone.utc)
    assert row.state == PortalState.IN_PROGRESS


def test_script_content_is_not_read_as_a_row():
    """A number inside a <script> tag is not on the page a person sees."""
    snap = parse_dashboard(HTML_DASHBOARD, read_at=READ_AT)
    assert "99999999" not in snap.numbers


def test_a_label_wrapped_onto_the_next_line_still_resolves():
    snap = parse_dashboard(
        "Applications in progress\n\nWrapped Row\nApplication number:\n10209601\n"
        "5 days left\n",
        read_at=READ_AT,
    )
    assert snap.numbers == ("10209601",)
    assert snap.applications[0].title == "Wrapped Row"
    assert snap.applications[0].days_left == 5
    assert snap.skipped == ()


def test_bare_number_and_alternate_wordings_are_accepted():
    snap = parse_dashboard(
        "Applications awaiting assessment\n\nRow One\n10210780\nSubmitted\n\n"
        "Row Two\nApplication ref: 10210045\nAwaiting assessment\n",
        read_at=READ_AT,
    )
    assert set(snap.numbers) == {"10210780", "10210045"}
    assert all(app.state == PortalState.SUBMITTED for app in snap.applications)


# ── the three ways there is no reading at all ────────────────────────────────


@pytest.mark.parametrize("text", ["", "   \n\n  ", None, 42, b"bytes"])
def test_no_text_is_unavailable_with_a_blocker(text):
    snap = parse_dashboard(text, read_at=READ_AT)
    assert snap.available is False
    assert snap.blocker
    assert snap.applications == ()


def test_a_page_that_is_not_the_dashboard_is_unavailable():
    snap = parse_dashboard("Hello world.\nThis is some other page.\n", read_at=READ_AT)
    assert snap.available is False
    assert "does not look like the applicant dashboard" in snap.blocker


def test_a_sign_in_wall_says_the_session_is_not_authenticated():
    """The blocker must be actionable, and these two are different instructions.

    "Not signed in" tells the operator to sign in; "no rows" tells them the read
    happened and found nothing. Collapsing them would send them looking in the
    wrong place.
    """
    snap = parse_dashboard(
        "GOV.UK\nApply for innovation funding\nSign in to your account\n"
        "Enter your email address and password\n",
        read_at=READ_AT,
    )
    assert snap.available is False
    assert "not authenticated" in snap.blocker
    assert "cannot sign in" in snap.blocker


def test_a_real_dashboard_with_no_applications_is_available_and_empty():
    """A genuinely empty dashboard is a *reading*, not a failure.

    The section heading is what distinguishes it from "this is not the
    dashboard", and the two must not collapse: one means the applicant has no
    applications, the other means the reader looked at the wrong page.
    """
    snap = parse_dashboard(
        "Your applications\nApplications in progress\nYou have no applications yet.\n",
        read_at=READ_AT,
    )
    assert snap.available is True
    assert snap.applications == ()
    assert snap.blocker is None


# ── read_dashboard: injection, and the absent session ───────────────────────


def test_injected_fetcher_reads_the_dashboard():
    snap = read_dashboard(fetcher=lambda: DASHBOARD_TEXT, read_at=READ_AT)
    assert snap.available is True
    assert len(snap.applications) == 11
    assert snap.read_at == READ_AT
    assert "injected" in snap.source


def test_a_missing_fetcher_yields_unavailable_with_a_blocker(monkeypatch):
    """No fetcher, no session: a value with a reason, never an exception.

    Hermetic by construction. ``AUREON_CDP_URL`` names a non-loopback host, which
    :func:`ifs.resolve_cdp_url` refuses *before* anything is dialled, and the
    tripwire below fails the test if any code path reaches for the network anyway.
    """
    monkeypatch.setattr(
        ifs,
        "_cdp_targets",
        lambda *a, **k: pytest.fail("read_dashboard must not touch the network in tests"),
    )
    snap = read_dashboard(env={"AUREON_CDP_URL": "http://cdp.example.com:9222"})

    assert snap.available is False
    assert snap.applications == ()
    assert "non-local" in snap.blocker
    assert "cdp.example.com" in snap.blocker
    # The refusal is about the endpoint, never a prompt for credentials.
    assert "password" not in snap.blocker.lower()


def test_an_absent_websocket_dependency_is_a_stated_blocker(monkeypatch):
    monkeypatch.setattr(ifs, "missing_transport", lambda: "no way to speak CDP: nothing installed")
    monkeypatch.setattr(
        ifs, "_cdp_targets", lambda *a, **k: pytest.fail("dependency check must come first")
    )
    snap = read_dashboard(cdp_url="http://127.0.0.1:9222")

    assert snap.available is False
    assert "nothing installed" in snap.blocker


def test_an_unreachable_port_is_a_stated_blocker(monkeypatch):
    monkeypatch.setattr(ifs, "missing_transport", lambda: None)
    monkeypatch.setattr(
        ifs, "_cdp_targets", lambda *a, **k: ([], "no Chrome debugging endpoint at http://127.0.0.1:9222")
    )
    snap = read_dashboard(cdp_url="http://127.0.0.1:9222")
    assert snap.available is False
    assert "no Chrome debugging endpoint" in snap.blocker


def test_dashboard_tab_not_open_names_no_other_tab(monkeypatch):
    """The blocker counts tabs and names none of them.

    The operator's other tabs are their business, and a blocker string ends up in
    logs and on the thought bus.
    """
    monkeypatch.setattr(ifs, "missing_transport", lambda: None)
    monkeypatch.setattr(
        ifs,
        "_cdp_targets",
        lambda *a, **k: (
            [
                {"type": "page", "url": "https://example.invalid/private-thing"},
                {"type": "page", "url": "https://other.invalid/another"},
            ],
            None,
        ),
    )
    snap = read_dashboard(cdp_url="http://127.0.0.1:9222")

    assert snap.available is False
    assert "2 page tab(s) seen" in snap.blocker
    assert "example.invalid" not in snap.blocker
    assert "private-thing" not in snap.blocker


@pytest.mark.parametrize("returned", ["", "   ", None, 17])
def test_a_fetcher_that_returns_nothing_is_unavailable(returned):
    snap = read_dashboard(fetcher=lambda: returned, read_at=READ_AT)
    assert snap.available is False
    assert snap.blocker


def test_a_fetcher_that_raises_never_escapes():
    def boom() -> str:
        raise RuntimeError("the browser went away")

    snap = read_dashboard(fetcher=boom, read_at=READ_AT)
    assert snap.available is False
    assert "RuntimeError" in snap.blocker
    # The exception's own message is not promoted to a blocker anyone vetted.
    assert "went away" not in snap.blocker


def test_a_fetcher_may_hand_over_a_precise_blocker():
    def blocked() -> str:
        raise PortalBlocked("the operator's browser has no dashboard tab open")

    snap = read_dashboard(fetcher=blocked, read_at=READ_AT)
    assert snap.available is False
    assert snap.blocker == "the operator's browser has no dashboard tab open"


def test_a_fetcher_returning_a_sign_in_page_is_unavailable():
    snap = read_dashboard(
        fetcher=lambda: "Sign in to your account\nEnter your email address and password",
        read_at=READ_AT,
    )
    assert snap.available is False
    assert "not authenticated" in snap.blocker


# ── the loopback rule ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url",
    ["http://127.0.0.1:9222", "http://localhost:9222", "127.0.0.1:9222", "http://[::1]:9222"],
)
def test_loopback_endpoints_are_accepted(url):
    resolved, blocker = resolve_cdp_url(url, env={})
    assert blocker is None
    assert resolved.startswith("http://")


@pytest.mark.parametrize(
    "url",
    [
        "http://10.0.0.5:9222",
        "https://cdp.example.com",
        "ws://127.0.0.1:9222",
        "file:///etc/hosts",
    ],
)
def test_non_loopback_or_wrong_scheme_is_refused_not_attempted(url):
    """A CDP endpoint is full control of an authenticated browser.

    So the set of hosts allowed to hold one is exactly "this machine", and the
    check is a refusal rather than a failed connection: nothing is dialled.
    """
    resolved, blocker = resolve_cdp_url(url, env={})
    assert resolved == ""
    assert blocker


def test_the_default_endpoint_is_loopback():
    resolved, blocker = resolve_cdp_url(None, env={})
    assert blocker is None
    assert resolved == "http://127.0.0.1:9222"


# ── structural guarantees: what this module cannot do ────────────────────────


def _module_source() -> str:
    return Path(ifs.__file__).read_text(encoding="utf-8")


# The guards below check the *raw* source deliberately, comments and docstrings
# included. A CDP method is only ever named as a string literal, so a check that
# skipped literals would miss the very thing it is guarding; and the module's own
# prose is held to the same standard, which is why its docstring describes what it
# refuses to do without spelling out the identifiers that would do it.


def test_the_reader_holds_no_credential_path():
    """Grep the module and find the absence.

    Not a style check. The rule is that the portal session belongs to the
    operator's browser and this capability never handles credentials, and the way
    to keep a rule like that is to make the code incapable rather than
    well-behaved. A module with no credential API cannot be argued into using one.
    """
    source = _module_source()
    for forbidden in (
        "getpass",
        "keyring",
        "Network.getAllCookies",
        "Network.getCookies",
        "Storage.getCookies",
        "set_cookie",
        "add_cookies",
        "AUREON_IFS_PASSWORD",
        "input type=\"password\"",
    ):
        assert forbidden not in source, forbidden


def test_the_reader_holds_no_write_or_navigation_path():
    """Read-only, structurally: nothing here can click, type, or navigate.

    The operator's browser is live and signed in. Navigating it could land on a
    re-authentication flow or, worse, a form; so the reader finds an already-open
    tab and reads its text, and the absence of every other verb is the guarantee.
    """
    source = _module_source()
    for forbidden in (
        "Page.navigate",
        "Input.dispatchKeyEvent",
        "Input.dispatchMouseEvent",
        "Runtime.callFunctionOn",
        "page.goto",
        "new_page",
        ".click(",
        ".fill(",
        ".press(",
        "requests.post",
    ):
        assert forbidden not in source, forbidden

    # Exactly one expression is ever evaluated in the operator's page, and it is
    # a constant.
    assert ifs.READ_EXPRESSION == "document.body.innerText"
    assert source.count('"Runtime.evaluate"') == 1


def test_no_portal_data_is_hardcoded_in_the_parser():
    """What the portal says is data. Data lives in a response or a fixture.

    An earlier reading was wrong precisely because portal facts had been written
    down somewhere and then trusted after they stopped being true. Every one of
    the eleven numbers below is asserted *absent* from the parser's source: the
    module must derive them from the page each time or not report them at all.
    """
    source = _module_source()
    for number in ALL_NUMBERS:
        assert number not in source, number
    for title in EXPECTED_TITLES.values():
        assert title not in source, title


def test_no_owner_details_are_hardcoded():
    source = _module_source()
    for detail in ("NI696693", "Leckey", "Quadrant", "Belfast", "R&A Consulting"):
        assert detail not in source, detail


def test_the_module_imports_and_parses_with_no_optional_dependency():
    """Absence of playwright / websocket-client is reported, never raised.

    The pure core must work on a machine with neither installed — which is the
    machine this was written on, and the machine CI runs.
    """
    blocker = ifs.missing_transport()
    assert blocker is None or "pip install" in blocker
    # Whatever the answer, the pure path is unaffected by it.
    assert parse_dashboard(DASHBOARD_TEXT, read_at=READ_AT).available is True


# ── interop with the schema the reconciler reads ─────────────────────────────


def test_portal_state_is_an_alias_not_a_second_vocabulary():
    """The enum must be usable everywhere the ``STATE_*`` constants are.

    Otherwise the reader and the reconciler would be speaking two vocabularies
    that happen to look alike, which is worse than one.
    """
    assert PortalState.SUBMITTED == STATE_SUBMITTED
    assert PortalState.SUBMITTED in PORTAL_STATES
    assert PortalState.NOT_SUBMITTED == STATE_NOT_STARTED
    # Two names, one member: the portal draws no distinction, so neither do we.
    assert PortalState.NOT_SUBMITTED is PortalState.NOT_STARTED
    assert PortalState.of("Submitted — awaiting assessment") is PortalState.SUBMITTED
    assert PortalState.of("something the portal has never said") is PortalState.UNKNOWN


def test_a_snapshot_round_trips_through_json(snapshot):
    payload = json.dumps(snapshot.to_dict())
    restored = json.loads(payload)

    assert restored["available"] is True
    assert restored["application_count"] == 11
    assert restored["fully_read"] is True
    assert restored["funder"]
    assert {row["number"] for row in restored["applications"]} == set(ALL_NUMBERS)

    in_progress = next(r for r in restored["applications"] if r["number"] == IN_PROGRESS_NUMBER)
    assert in_progress["state"] == "in_progress"
    assert in_progress["percent_complete"] == 93
    assert in_progress["days_left"] == 33
    assert in_progress["deadline"].startswith("2026-09-03")


def test_the_snapshot_declares_its_scope_for_reconciliation(snapshot):
    """Without a declared scope, reconciliation cannot judge absence honestly.

    A Horizon Europe record is not "missing from the Innovate UK dashboard" — it
    was never on it. The snapshot has to say what it is entitled to have an
    opinion about, or the reconciler must decline and say why.
    """
    assert snapshot.scope_tokens
    assert "innovate uk" in snapshot.scope_tokens
    pattern = snapshot.compiled_number_pattern()
    assert pattern is not None
    for number in ALL_NUMBERS:
        assert pattern.match(number), number
    assert not pattern.match("1021")
