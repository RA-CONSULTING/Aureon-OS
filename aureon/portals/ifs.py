"""Read the Innovate UK dashboard. No credentials, no login, no writes.

This module replaces a manual habit. Until now the only way anything in this
operation saw the funder's own record of its applications was a human — or an
assistant driving a browser in a chat window — reading the dashboard by eye and
retyping what it said. That read is not repeatable, not testable, not gated, and
leaves no artifact in the repository. It is also the read that mattered most:
reconciling one such reading against the local ledger found drift in *both*
directions, including two applications the funder has recorded as **submitted**
that the ledger had never heard of, and ledger rows carried as live applications
that the portal has no record of at all — whose deadline fields were therefore
meaningless, and one of which had already been reported as a live route with
"12 days left". Nothing in that class of error survives a portal reader that runs
every cycle. That is what this module is.

Two halves, and the split is the design
---------------------------------------
:func:`parse_dashboard` is a **pure function over text**. No browser, no network,
no clock it did not receive. Everything that can be wrong about reading a
dashboard — a state misfiled, a deadline invented, a truncated row half-parsed —
is wrong inside that function, so all of it is testable with a string. It is the
part with the bugs, so it is the part with no I/O.

:func:`read_dashboard` is the thin, untestable-by-nature shell that obtains the
text. It is a handful of statements, each of which can only fail by returning an
unavailable :class:`~aureon.portals.schemas.PortalSnapshot` with a stated
blocker.

What this module cannot do, structurally
----------------------------------------
**It cannot log in.** There is no username field, no password field, no token
store, no cookie read, no OAuth flow, and no code path that could acquire a
session. It calls no CDP method that returns cookies or any other credential
material; the *only* expression it evaluates in the page is the constant
``document.body.innerText``. Grep this file for a secret and you
will find that the absence is structural, not a policy note: a module with no
authentication path cannot be argued into authenticating.

**It cannot write.** It does not submit, save, click, fill, or navigate. It does
not even open a tab — see :func:`cdp_fetcher`, which reads a dashboard tab the
operator already has open and reports absence when there is none, rather than
navigating a live authenticated session somewhere it was not asked to go.

How the operator exposes the session (the only setup step)
----------------------------------------------------------
The session belongs to the operator's browser. Chrome publishes a *local*
debugging endpoint when launched with a debugging port, and this module attaches
to that endpoint read-only.

1. Close Chrome completely (a running instance ignores the flag; check Task
   Manager for stragglers).
2. Relaunch it with the port open. On Windows::

       "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" ^
           --remote-debugging-port=9222 ^
           --remote-debugging-address=127.0.0.1

   Adding ``--user-data-dir="%LOCALAPPDATA%\\Aureon\\chrome-portal"`` runs a
   *separate* profile, which keeps the debugging port away from the everyday
   browser — but that profile starts signed out, so step 3 must be done in it.
3. **Sign in yourself**, in that window, as normal. This module never sees that
   happen and holds nothing from it.
4. Open ``https://apply-for-innovation-funding.service.gov.uk/applicant/dashboard``
   and leave the tab open. The reader finds that tab by URL and reads its text.

Set ``AUREON_CDP_URL`` if the port differs; the default is
``http://127.0.0.1:9222``. A non-loopback host is **refused**, not attempted: a
CDP endpoint is full control of an authenticated browser, so pointing this at a
remote machine would be handing a session to the network. That refusal is a
stated blocker like any other.

Where this sits
---------------
It composes the shapes in :mod:`aureon.portals.schemas` rather than inventing
its own, so :mod:`aureon.portals.reconcile` can compare a portal reading with the
ledger read by :func:`aureon.grants.ledger.read_pipeline` without a translation
layer in between. It publishes nothing and decides nothing. Acting on drift —
and every verb in :data:`aureon.gates.switchboard.HUMAN_HELD` — stays where the
War Room put it: "No external submission, legal representation, filing, payment,
or email send should happen without Gary approval."
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from html import unescape
from typing import Any, Callable

from aureon.portals.schemas import (
    PortalApplication,
    PortalSnapshot,
    PortalState,
    normalise_state,
)

# ── what we are reading ──────────────────────────────────────────────────────

FUNDER = "Innovate UK — Innovation Funding Service"
DASHBOARD_URL = "https://apply-for-innovation-funding.service.gov.uk/applicant/dashboard"
DASHBOARD_HOST = "apply-for-innovation-funding.service.gov.uk"
# Matched against an open tab's URL. Path-only so a query string, a trailing
# slash, or a signed-in redirect target still matches the same page.
DASHBOARD_PATH_MARKER = "/applicant/dashboard"

# Declared scope: which ledger records this portal is entitled to have an opinion
# about. Reconciliation needs it to distinguish "the ledger has a record the
# portal never heard of" (real drift) from "the ledger has a Horizon Europe
# record" (not this portal's business, and not drift). Widening this tuple makes
# reconciliation bolder about calling a record absent; narrowing it makes the
# reconciler decline to judge and say so. It is a judgement, held in one place,
# not a fact discovered from a page.
IFS_SCOPE_TOKENS: tuple[str, ...] = (
    "innovate uk",
    "innovation funding service",
    "apply for innovation funding",
    "ifs",
    "ukri",
)

# The shape of an IFS application number. Every number observed on the live
# dashboard is exactly 8 digits; the 7–10 band is deliberate slack so a format
# change degrades into a *skipped row with a blocker* rather than into silence.
IFS_NUMBER_PATTERN = r"^\d{7,10}$"
_VALID_NUMBER = re.compile(IFS_NUMBER_PATTERN)

# ── CDP attachment (the shell) ───────────────────────────────────────────────

CDP_ENV_VAR = "AUREON_CDP_URL"
DEFAULT_CDP_URL = "http://127.0.0.1:9222"
# Loopback only. See the module docstring: a CDP endpoint is a live authenticated
# browser, and the set of hosts that may hold one is exactly "this machine".
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "[::1]", "0.0.0.0"})
DEFAULT_TIMEOUT = 8.0

WEBSOCKET_MODULE = "websocket"  # the `websocket-client` distribution
WEBSOCKET_HINT = "pip install websocket-client"
PLAYWRIGHT_HINT = "pip install playwright"

SOURCE_INJECTED = "injected fetcher"
SOURCE_TEXT = "dashboard text"

# The single expression ever evaluated in the operator's page. A constant, held
# as a constant so a reviewer can confirm at a glance that nothing else is run
# and nothing is passed in from outside.
READ_EXPRESSION = "document.body.innerText"


class PortalBlocked(Exception):
    """Raised by a fetcher to hand :func:`read_dashboard` a *precise* blocker.

    A fetcher's contract is "return page text", which has no room for a reason
    when there is no text. Rather than degrade every failure to "the fetcher
    returned nothing", a fetcher may raise this with the real explanation, and
    :func:`read_dashboard` turns it into the snapshot's blocker verbatim. Any
    *other* exception is caught too, but only its type is reported — a stray
    exception message is not a blocker anyone vetted.
    """


# ── line-level recognition ───────────────────────────────────────────────────
#
# The dashboard, reduced to text, is a flat sequence of lines: a section heading,
# then for each application a name, an application number, and some details. HTML
# gave those rows structure and innerText throws it away, so the number is used
# as each row's anchor and the recognisers below decide which neighbouring lines
# belong to it. Every recogniser is deliberately narrow: an unrecognised line
# *ends* the current row rather than being absorbed into it, because absorbing
# the wrong line is how a value ends up attached to the wrong application.

_NUMBER_LABEL = re.compile(
    r"application\s*(?:number|reference|ref\.?|no\.?)\s*[:#]?\s*(\S+)?",
    re.IGNORECASE,
)
_BARE_NUMBER = re.compile(r"^\d{7,10}$")
_DAYS_LEFT = re.compile(r"\b(\d{1,4})\s+days?\s+(?:left|remaining|to\s+go)\b", re.IGNORECASE)
_DAYS_IN = re.compile(r"\bcloses?\s+in\s+(\d{1,4})\s+days?\b", re.IGNORECASE)
_PERCENT_COMPLETE = re.compile(r"\b(\d{1,3})\s*%\s*complete\b", re.IGNORECASE)
_PERCENT_ALT = re.compile(r"\bcomplete[^0-9%]{0,12}(\d{1,3})\s*%", re.IGNORECASE)
_DEADLINE_LABEL = re.compile(r"\b(?:deadline|closes|closing\s+date|submit\s+by)\b", re.IGNORECASE)
_BARE_COUNT = re.compile(r"^\s*(\d{1,4})\s*$")
_DAYS_WORD_ONLY = re.compile(r"^\s*days?\s+(?:left|remaining|to\s+go)\s*$", re.IGNORECASE)
_COMPETITION_LABEL = re.compile(r"^\s*competition\s*[:\-]\s*(.+)$", re.IGNORECASE)

# GOV.UK style abbreviates September as "Sept", not "Sep" — a four-letter month
# that `%b` cannot parse. A hand-built map exists for exactly that reason:
# `strptime("%d %b %Y")` raises on a GOV.UK September date, and the only date on
# an in-progress dashboard row is its deadline, so that single gap would have
# silently produced `deadline=None` on the one row where a deadline matters.
_MONTHS: dict[str, int] = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}
_DMY = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\.?,?\s+(\d{4})\b")
_ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")

# Interface chrome that sits inside a row and carries no data. Matched exactly
# (lower-cased, punctuation trimmed) so a line merely *containing* one of these
# words still ends the row instead of being silently discarded.
_NOISE: frozenset[str] = frozenset(
    {
        "continue", "continue application", "view", "view application",
        "view submitted application", "view your application", "edit", "delete",
        "remove", "print", "print application", "download", "read only view",
        "read-only view", "manage team", "manage contributors", "manage",
        "track your application", "lead applicant", "you are the lead applicant",
        "collaborator", "complete", "incomplete", "assessment feedback",
        "no feedback available", "feedback", "open", "closed",
    }
)

# A "state" line long enough to be prose is prose. Real state labels on this
# dashboard are two or three words.
_MAX_STATE_LINE = 60

_HTML_HINT = re.compile(r"<\s*(?:html|body|div|table|ul|ol|li|h[1-6]|p|span|a|main)\b", re.I)
_SCRIPTISH = re.compile(r"(?is)<(script|style|noscript|template|head)\b.*?</\1\s*>")
# Block-level boundaries only. Breaking on inline tags (`</a>`, `</span>`) would
# split "Application number: 12345678" in two when the number sits in a span,
# and the anchor recogniser is line-based. (No real application number appears
# anywhere in this module: what the portal says is data, and data lives in the
# response being parsed or in a test fixture, never in the parser.)
_BLOCK_BREAK = re.compile(
    r"(?i)</?(?:p|div|li|ul|ol|tr|td|th|h[1-6]|section|article|header|footer|nav|"
    r"dl|dd|dt|table|tbody|thead|form|fieldset|main|aside|figure|blockquote)\b[^>]*>"
    r"|<br\s*/?>|<hr\s*/?>"
)
_TAG = re.compile(r"(?s)<[^>]+>")

# Wording that means the browser is showing a sign-in wall rather than the
# dashboard. Worth naming precisely: "the session is not authenticated" is a
# completely different instruction to the operator than "the page had no rows".
_SIGNIN_MARKERS = (
    "sign in to your account",
    "enter your email address and password",
    "you have been signed out",
    "your session has expired",
    "reset your password",
)


def _now() -> datetime:
    return datetime.now(UTC)


def _norm(line: str) -> str:
    return " ".join(line.strip().lower().strip(".,;:!·•-").split())


def _state_of(text: str) -> PortalState:
    """The normalised vocabulary, as an enum member. Never raises.

    Delegates the word-order problem ("not submitted" contains "submitted") to
    :func:`aureon.portals.schemas.normalise_state` so there is exactly one place
    in the repository where that ordering is decided.
    """
    return PortalState(normalise_state(text))


def parse_date(text: Any) -> tuple[datetime | None, str]:
    """Read a date out of portal wording. Returns ``(datetime | None, evidence)``.

    The returned datetime is midnight **UTC** on the date the page named. The
    page states a date and no clock time, so the time component is a
    representation of the date and not a reading of a moment — Innovate UK
    competitions generally close at 11:00 UK time, this function does not know
    that from the page, and it will not encode a guess. The second element is the
    literal text the value came from, so any downstream claim can be audited back
    to the words on the page; it is returned even when parsing fails, because the
    evidence of an unreadable date is worth more than its absence.
    """
    if not isinstance(text, str) or not text.strip():
        return None, ""
    evidence = " ".join(text.split())

    match = _DMY.search(evidence)
    if match:
        day, month_word, year = match.group(1), match.group(2).lower(), match.group(3)
        month = _MONTHS.get(month_word)
        if month is not None:
            try:
                return datetime(int(year), month, int(day), tzinfo=UTC), evidence
            except ValueError:
                # A real month name with an impossible day ("31 Feb 2026"). The
                # date is unreadable, not fixable; the evidence goes back intact.
                return None, evidence
        return None, evidence

    match = _ISO_DATE.search(evidence)
    if match:
        try:
            return (
                datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)),
                         tzinfo=UTC),
                evidence,
            )
        except ValueError:
            return None, evidence

    return None, evidence


def html_to_text(html: str) -> str:
    """Reduce a dashboard page to the text a person sees. Never raises.

    Not a general-purpose HTML parser and not trying to be. ``script`` / ``style``
    / ``head`` content is dropped, block boundaries become newlines, inline tags
    are removed without breaking the line, and entities are unescaped. That is
    the whole job: produce the same flat text ``innerText`` produces, so the live
    reader and an HTML fixture exercise the identical code path.
    """
    if not isinstance(html, str):
        return ""
    text = _SCRIPTISH.sub("\n", html)
    text = _BLOCK_BREAK.sub("\n", text)
    text = _TAG.sub("", text)
    text = unescape(text)
    return "\n".join(line.strip() for line in text.splitlines())


def looks_like_html(text: Any) -> bool:
    return isinstance(text, str) and "<" in text and bool(_HTML_HINT.search(text))


# ── the row state machine ────────────────────────────────────────────────────


class _Row:
    """Lines gathered around one application number, before validation."""

    __slots__ = (
        "names", "number_raw", "has_anchor", "awaiting_number", "days_left",
        "percent_complete", "deadline", "deadline_text", "state", "state_text",
    )

    def __init__(self) -> None:
        self.names: list[str] = []
        self.number_raw: str = ""
        self.has_anchor: bool = False
        self.awaiting_number: bool = False
        self.days_left: int | None = None
        self.percent_complete: int | None = None
        self.deadline: datetime | None = None
        self.deadline_text: str = ""
        self.state: PortalState | None = None
        self.state_text: str = ""

    @property
    def empty(self) -> bool:
        return not (self.has_anchor or self.names)


def _classify(line: str) -> tuple[str, Any]:
    """What kind of line is this? One of the tags consumed by :func:`_walk`.

    Order is load-bearing. The anchor test runs first because
    ``"Application number: 12345678"`` contains the word "application", which the
    section-heading test also looks for. The state test runs late and only on
    short lines, so a competition title is never mistaken for a status.
    """
    stripped = line.strip()
    if not stripped:
        return "blank", None

    match = _NUMBER_LABEL.search(stripped)
    if match:
        return "anchor", (match.group(1) or "").strip()
    if _BARE_NUMBER.match(stripped):
        return "anchor", stripped

    # "Competition: X" belongs to the row it follows. Classified as a generic
    # name it flushed the row (a post-anchor name opens the next record), which
    # detached every real dashboard row from its own metrics. The fixture used
    # in the tests omitted this line, so nothing caught it.
    match = _COMPETITION_LABEL.match(stripped)
    if match:
        return "competition", (match.group(1) or "").strip()

    match = _DAYS_LEFT.search(stripped) or _DAYS_IN.search(stripped)
    if match:
        return "days", int(match.group(1))

    # The live page splits a countdown over two lines — "33" then "days left".
    # A bare integer alone is ambiguous, so it is held as a PENDING count and
    # only becomes a day count if the next line says so; otherwise it is noise.
    if _BARE_COUNT.match(stripped):
        return "count", int(stripped)
    if _DAYS_WORD_ONLY.match(stripped):
        return "days_word", None

    match = _PERCENT_COMPLETE.search(stripped) or _PERCENT_ALT.search(stripped)
    if match:
        return "percent", int(match.group(1))

    if _DEADLINE_LABEL.search(stripped):
        return "deadline", stripped

    if len(stripped) <= _MAX_STATE_LINE:
        state = _state_of(stripped)
        if state is not PortalState.UNKNOWN:
            # A state line naming "application(s)" is a section heading over
            # several rows; a bare one ("Submitted") is that row's own label.
            # This is a heuristic about page wording, not a fact — a bare heading
            # can be absorbed as the preceding row's label, which is why
            # disagreement between a row's label and its section is reported as a
            # note instead of resolved silently.
            kind = "heading" if "application" in stripped.lower() else "state"
            return kind, state

    if _norm(stripped) in _NOISE:
        return "noise", None

    return "name", stripped


def _walk(lines: list[str]) -> tuple[list[tuple[_Row, PortalState]], bool, list[str]]:
    """Group lines into rows, each paired with the section state in force.

    Returns ``(rows, saw_heading)``. ``saw_heading`` is how the caller tells a
    dashboard with no applications on it from a page that is not the dashboard:
    the first is a real answer, the second is a failed read, and they must not
    collapse into the same snapshot.
    """
    rows: list[tuple[_Row, PortalState]] = []
    section = PortalState.UNKNOWN
    saw_heading = False
    current = _Row()
    # Lines carrying a real value that belongs to no identifiable application.
    # Surfaced so a caller can see the page was not wholly understood.
    orphans: list[str] = []
    pending_count: int | None = None

    def flush() -> None:
        nonlocal current
        if not current.empty:
            rows.append((current, section))
        current = _Row()

    for raw in lines:
        # A label whose value wrapped onto the next line ("Application number:"
        # then "12345678"). Resolved before classification, because the value
        # line looks like an anchor of its own and would otherwise split the row.
        if current.awaiting_number:
            current.awaiting_number = False
            token = raw.strip().split()[0] if raw.strip() else ""
            if token:
                current.number_raw = token.strip(".,;:#")
                continue

        kind, value = _classify(raw)
        if kind == "blank":
            continue

        if kind == "heading":
            flush()
            section = value
            saw_heading = True
            continue

        if kind == "anchor":
            if current.has_anchor:
                flush()
            current.has_anchor = True
            if value:
                current.number_raw = str(value).strip(".,;:#")
            else:
                current.awaiting_number = True
            continue

        if kind == "state":
            # A second state label cannot belong to the same row; it is a bare
            # section heading. Flushing here is what keeps the next row's state
            # from leaking backwards into this one.
            if current.state is not None:
                flush()
                section = value
                saw_heading = True
                continue
            if not current.has_anchor:
                orphans.append(raw.strip())
                continue
            current.state = value
            current.state_text = raw.strip()
            continue

        # A METRIC MAY ONLY ATTACH TO A ROW THAT HAS AN ANCHOR.
        #
        # This is the whole fix, and it is a boundary rule rather than a parsing
        # improvement. Previously any unrecognised line after the number line
        # flushed the row and opened a new, anchorless one; the metrics that
        # followed attached to THAT row, and the next "Application number:" then
        # adopted them wholesale, because an anchor arriving on an anchorless row
        # does not flush. The observed result:
        #
        #   Application number: <A> / Lead applicant: Some Org Ltd /
        #   <N> days left / Deadline <date> / <P>% complete /
        #   Application number: <B> / Submitted
        #
        # reported <B> as SUBMITTED carrying <A>'s countdown and completion —
        # another application's numbers — while <A> came back with all three
        # fields None. And it said fully_read=True, skipped=(). Real numbers are
        # deliberately not written here: this guard is enforced by
        # test_no_portal_data_is_hardcoded_in_the_parser, and a comment is
        # exactly where a fact goes stale unnoticed.
        #
        # A number that cannot be attributed to a row is now recorded as an
        # orphan and DROPPED. Attribution may still be imperfect on a malformed
        # page, but the failure is now a stated absence instead of a plausible
        # figure sitting under the wrong application.
        if kind in ("days", "percent", "deadline") and not current.has_anchor:
            orphans.append(raw.strip())
            continue

        if kind == "days":
            if current.days_left is None:
                current.days_left = value
            continue

        if kind == "percent":
            if current.percent_complete is None:
                current.percent_complete = value
            continue

        if kind == "deadline":
            if not current.deadline_text:
                current.deadline, current.deadline_text = parse_date(value)
            continue

        if kind == "competition":
            # Appended to names rather than stored on its own slot: the record
            # builder already scans names for _COMPETITION_LABEL, so the only
            # thing that had to change was NOT treating this as a generic name,
            # because a post-anchor name ends the row.
            current.names.append(raw.strip())
            continue

        if kind == "count":
            # Held, not used. Only the following "days left" line makes it a
            # countdown; on its own it stays unattributed rather than guessed.
            pending_count = int(value)
            continue

        if kind == "days_word":
            if pending_count is not None:
                if not current.has_anchor:
                    orphans.append(f"{pending_count} {raw.strip()}")
                elif current.days_left is None:
                    current.days_left = pending_count
                pending_count = None
            continue

        if kind == "noise":
            continue

        # kind == "name". Before the anchor it is this row's name; after it, the
        # row is finished and this line opens the next one.
        if current.has_anchor:
            flush()
        current.names.append(value)

    flush()
    return rows, saw_heading, orphans


def _split_names(names: list[str]) -> tuple[str, str, list[str]]:
    """``(title, competition, extras)`` from a row's unclassified lines.

    An explicitly labelled competition wins. Otherwise the first line is the
    title and a second, if present, is the competition — the order the service
    renders them in. Anything beyond that is *returned*, not dropped: an
    unplaced line is reported as a note, because a reader that quietly discards
    page content cannot be trusted to have read all of it.
    """
    labelled = ""
    plain: list[str] = []
    for name in names:
        match = _COMPETITION_LABEL.match(name)
        if match:
            labelled = match.group(1).strip()
        else:
            plain.append(name)
    title = plain[0] if plain else ""
    competition = labelled or (plain[1] if len(plain) > 1 else "")
    return title, competition, plain[2:]


def parse_dashboard(
    text_or_html: Any,
    *,
    source_url: str = DASHBOARD_URL,
    read_at: datetime | None = None,
) -> PortalSnapshot:
    """Turn dashboard text (or HTML) into a snapshot. Pure, and never raises.

    This is the whole testable core of the capability: no browser, no network, no
    ambient clock. ``read_at`` is injected so a test can pin it and so a snapshot
    always carries the moment of the *read*, not the moment of the parse.

    Three outcomes, kept distinct on purpose:

    * **Unavailable** — the text was empty, or was a sign-in wall, or contained
      neither a recognisable section heading nor a single application number.
      That last case is "this is not the dashboard", and the blocker says so.
    * **Available with rows** — what a good read looks like. A row that could not
      be read is *absent from* ``applications`` and named in ``skipped``; it is
      never emitted half-parsed, and a field that could not be read is ``None``
      with the offending text recorded, never a plausible substitute.
    * **Available with no rows** — a real dashboard belonging to an applicant with
      no applications. Only reachable when a section heading was recognised,
      which is what separates it from the first case.
    """
    read_at = read_at or _now()

    if text_or_html is None or not isinstance(text_or_html, str) or not text_or_html.strip():
        return PortalSnapshot.blocked(
            "no dashboard text to parse — the reader was handed "
            f"{'nothing' if not text_or_html else type(text_or_html).__name__}",
            read_at=read_at,
            source=SOURCE_TEXT,
            funder=FUNDER,
        )

    text = html_to_text(text_or_html) if looks_like_html(text_or_html) else text_or_html
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    lowered = "\n".join(lines).lower()
    rows, saw_heading, orphans = _walk(lines)
    anchored = [pair for pair in rows if pair[0].has_anchor]

    if not anchored:
        for marker in _SIGNIN_MARKERS:
            if marker in lowered:
                return PortalSnapshot.blocked(
                    "the page is a sign-in / session-expired page, not the dashboard — "
                    "the operator's browser session is not authenticated. Sign in in that "
                    "browser window and leave the dashboard tab open; this reader holds no "
                    "credentials and cannot sign in.",
                    read_at=read_at,
                    source=SOURCE_TEXT,
                    funder=FUNDER,
                )
        if not saw_heading:
            return PortalSnapshot.blocked(
                f"no application rows and no recognised dashboard section heading in "
                f"{len(lines)} lines of text — this does not look like the applicant "
                f"dashboard at {DASHBOARD_URL}",
                read_at=read_at,
                source=SOURCE_TEXT,
                funder=FUNDER,
            )

    applications: list[PortalApplication] = []
    skipped: list[str] = []
    seen: set[str] = set()

    for row, section in anchored:
        title, competition, extras = _split_names(row.names)
        label = f" (row named {title!r})" if title else ""
        number = row.number_raw

        if not number:
            skipped.append(
                f"a row carried an application-number label with no number after it{label}"
            )
            continue
        if not _VALID_NUMBER.match(number):
            skipped.append(
                f"{number!r} is not a readable application number "
                f"(expected {IFS_NUMBER_PATTERN}){label} — row skipped rather than guessed"
            )
            continue
        if number in seen:
            skipped.append(f"application {number} appeared more than once; the first was kept")
            continue
        seen.add(number)

        state = row.state or section
        if row.state is not None and section is not PortalState.UNKNOWN and row.state != section:
            skipped.append(
                f"application {number}: the row says {row.state} but its section says "
                f"{section}; the row's own label was used"
            )
        if row.deadline_text and row.deadline is None:
            skipped.append(
                f"application {number}: could not read a date from {row.deadline_text!r} — "
                "deadline left unset"
            )
        for extra in extras:
            skipped.append(f"application {number}: unplaced line {extra[:60]!r}")

        try:
            applications.append(
                PortalApplication(
                    number=number,
                    title=title,
                    state=state,
                    state_text=row.state_text,
                    deadline=row.deadline,
                    deadline_text=row.deadline_text,
                    competition=competition,
                    percent_complete=row.percent_complete,
                    days_left=row.days_left,
                    url="",  # innerText carries no hyperlinks; absence stays absence
                    source_url=source_url,
                    read_at=read_at,
                )
            )
        except (TypeError, ValueError) as exc:
            # The schema's own invariants refused the row. Report it as skipped
            # rather than letting a parse fault escape as an exception.
            skipped.append(f"application {number} was refused by the schema: {exc}")

    return PortalSnapshot(
        available=True,
        read_at=read_at,
        applications=tuple(applications),
        source=SOURCE_TEXT,
        funder=FUNDER,
        scope_tokens=IFS_SCOPE_TOKENS,
        number_pattern=IFS_NUMBER_PATTERN,
        skipped=tuple(skipped),
    )


# ── attaching to the operator's existing session ─────────────────────────────


def resolve_cdp_url(
    override: str | None = None, env: dict[str, str] | None = None
) -> tuple[str, str | None]:
    """``(url, blocker)``. Refuses anything that is not a local loopback endpoint.

    The refusal is the point. A Chrome DevTools endpoint is unauthenticated
    *and* omnipotent over the browser behind it — cookies, sessions, every open
    tab. A misconfigured ``AUREON_CDP_URL`` pointing off-box would hand the
    operator's authenticated funding-portal session to whatever answered. So a
    non-loopback host is never dialled, and the blocker names the host only,
    never the whole URL, which could carry a token.
    """
    source = os.environ if env is None else env
    raw = (override or source.get(CDP_ENV_VAR, "") or DEFAULT_CDP_URL).strip()
    if not raw:
        raw = DEFAULT_CDP_URL
    if "://" not in raw:
        raw = "http://" + raw

    try:
        parts = urllib.parse.urlsplit(raw)
    except ValueError:
        return "", f"{CDP_ENV_VAR} is not a usable URL"

    if parts.scheme not in ("http", "https"):
        return "", (
            f"{CDP_ENV_VAR} must be an http(s) URL for a local Chrome debugging port; "
            f"got scheme {parts.scheme!r}"
        )
    host = (parts.hostname or "").lower()
    if host not in LOOPBACK_HOSTS:
        return "", (
            f"refusing to attach a debugger to a non-local browser (host {host!r}). "
            "A CDP endpoint grants full control of an authenticated session, so "
            f"{CDP_ENV_VAR} must point at the loopback interface "
            f"(e.g. {DEFAULT_CDP_URL})."
        )
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{host}{port}", None


def missing_transport() -> str | None:
    """Name the absent way of speaking CDP, or None when one is available.

    Discovery (``/json/list``) is plain HTTP and needs only the standard library;
    reading a page needs a WebSocket, which does not. Either ``websocket-client``
    or ``playwright`` will do. ``find_spec`` is used rather than an import so the
    probe costs nothing and cannot execute third-party module code as a side
    effect of asking whether it exists.
    """
    import importlib.util  # noqa: PLC0415 — probe only, kept off the import path

    for module in (WEBSOCKET_MODULE, "playwright.sync_api"):
        try:
            if importlib.util.find_spec(module) is not None:
                return None
        except (ImportError, ValueError):
            continue
    return (
        "no way to speak CDP: neither websocket-client nor playwright is installed "
        f"({WEBSOCKET_HINT}, or {PLAYWRIGHT_HINT})"
    )


def _cdp_targets(cdp_url: str, timeout: float) -> tuple[list[dict[str, Any]], str | None]:
    """List the browser's open targets over plain HTTP. ``(targets, blocker)``."""
    endpoint = cdp_url.rstrip("/") + "/json/list"
    try:
        with urllib.request.urlopen(endpoint, timeout=timeout) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, OSError) as exc:
        return [], (
            f"no Chrome debugging endpoint at {cdp_url} ({type(exc).__name__}) — "
            "launch Chrome with --remote-debugging-port=9222, sign in yourself, and "
            "leave the dashboard tab open (see the module docstring)"
        )
    except (ValueError, json.JSONDecodeError) as exc:
        return [], f"{endpoint} did not return usable JSON ({type(exc).__name__})"
    if not isinstance(payload, list):
        return [], f"{endpoint} returned {type(payload).__name__}, expected a list of targets"
    return [t for t in payload if isinstance(t, dict)], None


def _dashboard_target(
    targets: list[dict[str, Any]], marker: str
) -> tuple[dict[str, Any] | None, str | None]:
    """Find the already-open dashboard tab. ``(target, blocker)``.

    No tab is opened and nothing is navigated. Navigating the operator's live,
    authenticated browser is a side effect this reader has no mandate for, and it
    could land on a re-authentication flow. So the honest failure is "the tab is
    not open", with instructions.

    The blocker counts the tabs it saw and names none of them: the operator's
    open tabs are their business, and a blocker string ends up in logs.
    """
    pages = [t for t in targets if t.get("type") == "page"]
    for target in pages:
        url = str(target.get("url", ""))
        if marker in url and DASHBOARD_HOST in url:
            return target, None
    return None, (
        f"the Innovate UK dashboard is not open in the attached browser "
        f"({len(pages)} page tab(s) seen, none at {DASHBOARD_HOST}{marker}). "
        f"Open {DASHBOARD_URL} in that window and leave the tab open — this reader "
        "does not navigate and cannot sign in."
    )


def _innertext_via_websocket(ws_url: str, timeout: float) -> tuple[str, str | None]:
    """Read ``document.body.innerText`` over the target's debugger socket."""
    try:
        import websocket  # noqa: PLC0415 — optional dependency, probed above
    except ImportError:
        return "", f"websocket-client is not installed ({WEBSOCKET_HINT})"

    request = {
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {
            "expression": READ_EXPRESSION,
            "returnByValue": True,
            "awaitPromise": False,
        },
    }
    connection = None
    try:
        connection = websocket.create_connection(ws_url, timeout=timeout)
        connection.send(json.dumps(request))
        # The socket also carries unsolicited events; read until our id comes
        # back, with a hard cap so a chatty page cannot loop forever.
        for _ in range(40):
            message = json.loads(connection.recv())
            if message.get("id") != 1:
                continue
            if "error" in message:
                return "", f"CDP refused the read: {message['error'].get('message', 'unknown')}"
            result = message.get("result", {})
            if result.get("exceptionDetails"):
                return "", "the page raised while reading its text"
            value = result.get("result", {}).get("value")
            if isinstance(value, str):
                return value, None
            return "", f"the page returned {type(value).__name__}, not text"
        return "", "the browser never answered the read request"
    except Exception as exc:  # noqa: BLE001 — a reader reports absence, never throws
        return "", f"could not read the dashboard tab over CDP ({type(exc).__name__})"
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001, S110 — closing a socket cannot fail usefully
                pass


def _innertext_via_playwright(cdp_url: str, marker: str, timeout: float) -> tuple[str, str | None]:
    """Fallback path for a machine that has playwright but not websocket-client.

    ``connect_over_cdp`` attaches to the running browser; it does not launch one
    and does not own the profile. No page is created and none is navigated.
    """
    try:
        from playwright.sync_api import sync_playwright  # noqa: PLC0415
    except ImportError:
        return "", f"playwright is not installed ({PLAYWRIGHT_HINT})"

    try:
        with sync_playwright() as driver:
            browser = driver.chromium.connect_over_cdp(cdp_url, timeout=timeout * 1000)
            try:
                for context in browser.contexts:
                    for page in context.pages:
                        if marker in page.url and DASHBOARD_HOST in page.url:
                            return page.inner_text("body"), None
                return "", (
                    f"the Innovate UK dashboard is not open in the attached browser — "
                    f"open {DASHBOARD_URL} and leave the tab open"
                )
            finally:
                # Close our client connection only. The operator's browser and
                # their session keep running; we were a guest.
                browser.close()
    except Exception as exc:  # noqa: BLE001
        return "", f"playwright could not attach to {cdp_url} ({type(exc).__name__})"


def _cdp_read(
    *,
    cdp_url: str | None = None,
    env: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    marker: str = DASHBOARD_PATH_MARKER,
) -> tuple[str, str, str | None]:
    """``(text, source, blocker)`` for the default read. Never raises.

    Ordered so the cheapest and most security-relevant check comes first: the
    loopback refusal happens before any socket is opened, and the dependency
    probe before any connection is attempted.
    """
    url, blocker = resolve_cdp_url(cdp_url, env)
    if blocker:
        return "", "cdp (refused)", blocker
    source = f"cdp {url} (existing operator browser session)"

    blocker = missing_transport()
    if blocker:
        return "", source, blocker

    targets, blocker = _cdp_targets(url, timeout)
    if blocker:
        return "", source, blocker

    target, blocker = _dashboard_target(targets, marker)
    if blocker or target is None:
        return "", source, blocker or "no dashboard tab"

    ws_url = str(target.get("webSocketDebuggerUrl", ""))
    if ws_url:
        text, ws_blocker = _innertext_via_websocket(ws_url, timeout)
        if text:
            return text, source, None
    else:
        ws_blocker = "the dashboard tab exposes no debugger socket"

    text, pw_blocker = _innertext_via_playwright(url, marker, timeout)
    if text:
        return text, source, None
    return "", source, f"{ws_blocker}; playwright fallback: {pw_blocker}"


def cdp_fetcher(
    *,
    cdp_url: str | None = None,
    env: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    marker: str = DASHBOARD_PATH_MARKER,
) -> Callable[[], str]:
    """The default fetcher, as an injectable callable.

    Raises :class:`PortalBlocked` with the precise reason when it cannot read,
    because a ``Callable[[], str]`` has nowhere else to put one. Callers who want
    a value rather than an exception should use :func:`read_dashboard`, which
    catches it.
    """

    def _fetch() -> str:
        text, _source, blocker = _cdp_read(cdp_url=cdp_url, env=env, timeout=timeout, marker=marker)
        if blocker:
            raise PortalBlocked(blocker)
        return text

    return _fetch


def read_dashboard(
    fetcher: Callable[[], Any] | None = None,
    *,
    cdp_url: str | None = None,
    env: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    source_url: str = DASHBOARD_URL,
    read_at: datetime | None = None,
) -> PortalSnapshot:
    """Read the dashboard and return a snapshot. **Never raises, never logs in.**

    ``fetcher`` is any zero-argument callable returning page text — a test's
    fixture, a saved page, an operator's own transport. When it is ``None`` the
    default path attaches to an *existing* Chrome session over a loopback CDP
    endpoint (see the module docstring for the one launch flag the operator
    needs) and returns an unavailable snapshot, with the precise reason, whenever
    that session is not there: no browser on the port, the dashboard tab not
    open, the required dependency absent, the endpoint not on the loopback
    interface, or the page showing a sign-in wall.

    Every one of those is a *value*, not an exception, and none of them is ever a
    prompt for credentials. There is no login path here to fall back to.
    """
    read_at = read_at or _now()

    if fetcher is None:
        text, source, blocker = _cdp_read(cdp_url=cdp_url, env=env, timeout=timeout)
        if blocker:
            return PortalSnapshot.blocked(blocker, read_at=read_at, source=source, funder=FUNDER)
    else:
        source = SOURCE_INJECTED
        try:
            text = fetcher()
        except PortalBlocked as exc:
            return PortalSnapshot.blocked(
                str(exc) or "the fetcher reported it could not read the dashboard",
                read_at=read_at,
                source=source,
                funder=FUNDER,
            )
        except Exception as exc:  # noqa: BLE001 — a reader reports absence, never throws
            return PortalSnapshot.blocked(
                f"the injected fetcher raised {type(exc).__name__} — no dashboard text was read",
                read_at=read_at,
                source=source,
                funder=FUNDER,
            )

    if not isinstance(text, str) or not text.strip():
        return PortalSnapshot.blocked(
            "the fetcher returned no dashboard text "
            f"({'empty' if isinstance(text, str) else type(text).__name__})",
            read_at=read_at,
            source=source,
            funder=FUNDER,
        )

    snapshot = parse_dashboard(text, source_url=source_url, read_at=read_at)
    # Re-stamp provenance: `parse_dashboard` only knows it was handed text, while
    # this function knows where the text came from. Nothing else is altered.
    if not snapshot.available:
        return PortalSnapshot.blocked(
            snapshot.blocker or "the dashboard text could not be parsed",
            read_at=read_at,
            source=source,
            funder=FUNDER,
        )
    return PortalSnapshot(
        available=True,
        read_at=snapshot.read_at,
        applications=snapshot.applications,
        source=source,
        funder=FUNDER,
        scope_tokens=snapshot.scope_tokens,
        number_pattern=snapshot.number_pattern,
        skipped=snapshot.skipped,
    )


__all__ = [
    "CDP_ENV_VAR",
    "DASHBOARD_HOST",
    "DASHBOARD_PATH_MARKER",
    "DASHBOARD_URL",
    "DEFAULT_CDP_URL",
    "FUNDER",
    "IFS_NUMBER_PATTERN",
    "IFS_SCOPE_TOKENS",
    "LOOPBACK_HOSTS",
    "READ_EXPRESSION",
    "PortalBlocked",
    "cdp_fetcher",
    "html_to_text",
    "looks_like_html",
    "missing_transport",
    "parse_dashboard",
    "parse_date",
    "read_dashboard",
    "resolve_cdp_url",
]
