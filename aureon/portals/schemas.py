"""The shape of one portal read, and the vocabulary it is normalised into.

Deliberately mirrors two shapes that already exist in this repo rather than
inventing a third:

* :class:`PortalSnapshot` carries the same ``available`` / ``blocker`` /
  ``source`` invariant as :class:`aureon.connectors.base.ConnectorStatus` — an
  available snapshot may not carry a blocker and an unavailable one may not omit
  it, so a reader that could not reach the portal cannot be mistaken for a
  portal with no applications on it. Those are opposite answers.
* Timestamps are parsed with :func:`aureon.grants.schemas.parse_dt`, so a portal
  date and a ledger date are read by exactly one function and compare cleanly.

Nothing in this module knows which portal it is describing. The funder, the
dashboard URL, the scope tokens and the shape of an application number are all
supplied by whatever performed the read. That is why
:mod:`aureon.portals.reconcile` can be tested against a fixture without a
funder's vocabulary being baked into the source.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from aureon.grants.schemas import parse_dt

# ── the normalised state vocabulary ──────────────────────────────────────────
#
# A portal writes prose ("Submitted — awaiting assessment", "In progress",
# "Not submitted"). Reconciliation needs a small closed set, so the prose is
# preserved verbatim on ``state_text`` and mapped to one of these. ``unknown``
# is a first-class member: an unrecognised phrase is *not* quietly filed as one
# of the others.
STATE_SUBMITTED = "submitted"
STATE_IN_PROGRESS = "in_progress"
STATE_NOT_STARTED = "not_started"
STATE_INELIGIBLE = "ineligible"
STATE_UNKNOWN = "unknown"

PORTAL_STATES = frozenset(
    {STATE_SUBMITTED, STATE_IN_PROGRESS, STATE_NOT_STARTED, STATE_INELIGIBLE, STATE_UNKNOWN}
)

# States in which the funder already holds the application, so the portal shows
# no remaining deadline for it. Used by reconciliation to spot a ledger deadline
# that has outlived the work it described.
PORTAL_HELD_STATES = frozenset({STATE_SUBMITTED, STATE_INELIGIBLE})


class PortalState(str, Enum):
    """The same five states as the ``STATE_*`` constants, as a closed type.

    Added for readers (:mod:`aureon.portals.ifs`) that would otherwise pass bare
    strings a typo could corrupt silently — ``"submited"`` is a valid ``str`` and
    an invalid state, and only one of those two facts is caught by a string.

    It is an *alias*, not a second vocabulary. Every member's value **is** the
    corresponding module constant, and the class subclasses ``str``, so
    ``PortalState.SUBMITTED == STATE_SUBMITTED`` is true, ``PortalState.SUBMITTED
    in PORTAL_STATES`` is true, ``normalise_state`` output converts straight into
    a member, and ``json.dumps`` emits ``"submitted"``. Nothing that consumes the
    constants needs to know this type exists.

    ``NOT_SUBMITTED`` and ``NOT_STARTED`` are two names for one member: the
    dashboard's heading reads "not submitted" while this repo's constant is
    ``STATE_NOT_STARTED``, and inventing a distinction the portal does not draw
    would be a fabricated state.
    """

    SUBMITTED = STATE_SUBMITTED
    IN_PROGRESS = STATE_IN_PROGRESS
    NOT_SUBMITTED = STATE_NOT_STARTED
    NOT_STARTED = STATE_NOT_STARTED  # alias of NOT_SUBMITTED — same member
    INELIGIBLE = STATE_INELIGIBLE
    UNKNOWN = STATE_UNKNOWN

    def __str__(self) -> str:  # so logs and f-strings read "submitted", not the repr
        return self.value

    @classmethod
    def of(cls, text: Any) -> "PortalState":
        """Normalise portal prose straight into a member. Never raises."""
        return cls(normalise_state(text))

# Order matters and is the whole correctness of :func:`normalise_state`.
# "not submitted" *contains* "submitted"; a substring test in the wrong order
# reports an empty draft as a filed application, which is the single most
# consequential mistake this function could make. Negations are tested first.
_NOT_STARTED_TOKENS = ("not started", "not submitted", "unsubmitted", "not yet submitted",
                       "no submission", "never submitted")
_INELIGIBLE_TOKENS = ("ineligible", "not eligible", "failed eligibility")
_SUBMITTED_TOKENS = ("submitted", "awaiting assessment", "under assessment", "in assessment",
                     "submission received")
_IN_PROGRESS_TOKENS = ("in progress", "in-progress", "started", "draft", "editing")


def normalise_state(text: Any) -> str:
    """Map a portal's own words onto :data:`PORTAL_STATES`. Never raises.

    An unrecognised phrase returns :data:`STATE_UNKNOWN` rather than the closest
    guess. Reconciliation treats ``unknown`` as "no comparison possible" and
    says so in its report, which is a smaller error than a confident wrong state.
    """
    s = " ".join(str(text or "").strip().lower().split())
    if not s:
        return STATE_UNKNOWN
    if any(t in s for t in _NOT_STARTED_TOKENS):
        return STATE_NOT_STARTED
    if any(t in s for t in _INELIGIBLE_TOKENS):
        return STATE_INELIGIBLE
    if any(t in s for t in _SUBMITTED_TOKENS):
        return STATE_SUBMITTED
    if any(t in s for t in _IN_PROGRESS_TOKENS):
        return STATE_IN_PROGRESS
    return STATE_UNKNOWN


def _int_or_none(value: Any) -> int | None:
    """A real integer or None. ``bool`` is refused: ``int(True)`` is 1, and a
    JSON ``true`` reported as "1% complete" is a fabricated measurement."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _first(source: Any, keys: tuple[str, ...]) -> Any:
    """First present, non-empty value among ``keys``, from a mapping or object.

    Exists so a snapshot produced by some other reader — one that calls the
    field ``application_number`` instead of ``number`` — is still readable.
    Absence of every alias yields None; nothing is defaulted.
    """
    for key in keys:
        value = source.get(key) if isinstance(source, Mapping) else getattr(source, key, None)
        if value is not None and value != "":
            return value
    return None


_NUMBER_KEYS = ("number", "application_number", "application_id", "ifs_number", "id")
_TITLE_KEYS = ("title", "name", "project", "project_name")
_STATE_KEYS = ("state_text", "status_text", "state", "status")
_DEADLINE_KEYS = ("deadline", "deadline_at", "closes_at")


@dataclass(frozen=True)
class PortalApplication:
    """One application as the funder's own dashboard shows it.

    ``state`` is the normalised vocabulary; ``state_text`` is what the portal
    actually said. Both are kept because the normalisation is this code's
    interpretation and the text is evidence — a report that quotes the portal
    can be checked, one that only quotes ``state`` cannot.

    Every field other than ``number`` may legitimately be absent. A dashboard
    row for a submitted application carries no deadline and no completion
    percentage, and inventing either would be exactly the fabrication the
    Owner's Rule forbids.
    """

    number: str
    title: str = ""
    state: str = STATE_UNKNOWN
    state_text: str = ""
    deadline: datetime | None = None
    deadline_text: str = ""
    competition: str = ""
    percent_complete: int | None = None
    days_left: int | None = None
    url: str = ""
    # Provenance, appended so positional construction is unchanged. ``url`` is a
    # link to *this application* (absent when the read came from rendered text,
    # which carries no hyperlinks); ``source_url`` is the page the row was read
    # from, and ``read_at`` is when. Without those two a row cannot be audited
    # back to a moment and a page, which is the difference between an observation
    # and an assertion.
    source_url: str = ""
    read_at: datetime | None = None

    def __post_init__(self) -> None:
        # The number is the join key onto the ledger. An application without one
        # cannot be reconciled against anything, so it cannot be constructed:
        # a numberless row in a snapshot would silently become a phantom
        # "missing from ledger" drift that no operator could act on.
        if not str(self.number).strip():
            raise ValueError("PortalApplication.number is mandatory — it is the join key")
        if self.state not in PORTAL_STATES:
            raise ValueError(f"PortalApplication.state must be one of {sorted(PORTAL_STATES)}")

    @property
    def is_submitted(self) -> bool:
        return self.state == STATE_SUBMITTED

    @property
    def portal_holds_it(self) -> bool:
        """True when the funder already has it and shows no open deadline."""
        return self.state in PORTAL_HELD_STATES

    @property
    def label(self) -> str:
        """How to name this application in a sentence a person will read."""
        return f"{self.number} ({self.title})" if self.title else self.number

    @classmethod
    def from_any(cls, raw: Any) -> "PortalApplication | None":
        """Build from a mapping or a foreign snapshot's row. None when unusable.

        Tolerant on input, strict on output: a row with no recognisable
        application number yields None rather than a husk with an invented key.
        """
        if raw is None or isinstance(raw, (str, bytes, int, float)):
            return None
        if isinstance(raw, cls):
            return raw
        number = _text(_first(raw, _NUMBER_KEYS))
        if not number:
            return None
        state_text = _text(_first(raw, _STATE_KEYS))
        declared = _text(_first(raw, ("state",)))
        # A snapshot that already speaks the normalised vocabulary is believed;
        # anything else is prose and gets normalised.
        state = declared if declared in PORTAL_STATES else normalise_state(state_text)
        raw_deadline = _first(raw, _DEADLINE_KEYS)
        deadline = raw_deadline if isinstance(raw_deadline, datetime) else parse_dt(raw_deadline)
        if deadline is not None and deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        return cls(
            number=number,
            title=_text(_first(raw, _TITLE_KEYS)),
            state=state,
            state_text=state_text,
            deadline=deadline,
            deadline_text=_text(_first(raw, ("deadline_text",))),
            competition=_text(_first(raw, ("competition", "competition_name"))),
            percent_complete=_int_or_none(_first(raw, ("percent_complete", "completion"))),
            days_left=_int_or_none(_first(raw, ("days_left", "days_remaining"))),
            url=_text(_first(raw, ("url", "link"))),
            source_url=_text(_first(raw, ("source_url", "page_url"))),
            read_at=parse_dt(_first(raw, ("read_at", "observed_at"))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "state": self.state,
            "state_text": self.state_text,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "deadline_text": self.deadline_text,
            "competition": self.competition,
            "percent_complete": self.percent_complete,
            "days_left": self.days_left,
            "url": self.url,
            "source_url": self.source_url,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }


@dataclass(frozen=True)
class PortalSnapshot:
    """One read of a funder's portal, or a stated reason there wasn't one.

    ``available=False`` with a blocker is a normal, expected value — it is what
    an absent operator session produces, and it is the only honest thing to
    return when nobody is logged in. The ``__post_init__`` invariant is the same
    one :class:`aureon.connectors.base.ConnectorStatus` enforces and exists for
    the same reason: a caller must never be able to read "could not look" as
    "looked, found nothing".

    Three fields describe the *scope* of the read, and reconciliation depends on
    them being honest:

    ``funder``
        Whose portal this is, in prose, for the report to quote.
    ``scope_tokens``
        Lower-case substrings that identify a ledger record as belonging to this
        portal. Without them nothing in the ledger can be judged absent from the
        portal — a Horizon Europe record is not missing from a UK dashboard, it
        was never on it — so reconciliation declines to make that judgement and
        says why rather than guessing. See
        :func:`aureon.portals.reconcile.reconcile`.
    ``number_pattern``
        Optional regex for what this portal's application numbers look like. It
        lets reconciliation notice a ledger record that names a portal-shaped
        number the portal no longer shows, which is a withdrawn or deleted
        application and would otherwise be invisible.
    """

    available: bool
    read_at: datetime
    applications: tuple[PortalApplication, ...] = ()
    blocker: str | None = None
    source: str = ""
    funder: str = ""
    scope_tokens: tuple[str, ...] = ()
    number_pattern: str = ""
    # Rows the reader could not read, one note each.
    #
    # These cannot live in ``blocker`` — the invariant below forbids an available
    # snapshot from carrying one, and rightly so: ten rows read and one truncated
    # is a *successful* read, and failing the whole snapshot over it would throw
    # away nine good observations. But the truncated row must not vanish either,
    # so it is named here, and :attr:`fully_read` is the flag for a caller that
    # needs "all of it, or treat it as partial". A skipped row is always ABSENT
    # from ``applications``; it is never emitted half-parsed.
    skipped: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.skipped, tuple):
            object.__setattr__(self, "skipped", tuple(self.skipped))
        if self.available and self.blocker:
            raise ValueError("an available snapshot cannot also carry a blocker")
        if not self.available and not self.blocker:
            raise ValueError("an unavailable snapshot must state its blocker")

    @classmethod
    def blocked(cls, blocker: str, *, read_at: datetime | None = None, source: str = "",
                funder: str = "") -> "PortalSnapshot":
        """The shape of "nobody was logged in" — a value, never an exception."""
        return cls(available=False, read_at=read_at or datetime.now(timezone.utc),
                   blocker=blocker, source=source, funder=funder)

    @property
    def numbers(self) -> tuple[str, ...]:
        return tuple(a.number for a in self.applications)

    @property
    def submitted(self) -> tuple[PortalApplication, ...]:
        return tuple(a for a in self.applications if a.is_submitted)

    @property
    def fully_read(self) -> bool:
        """Available *and* nothing skipped — the only state safe to call complete."""
        return self.available and not self.skipped

    @property
    def parse_blocker(self) -> str | None:
        """What stopped this read from being complete, or None.

        The blocker for *rows*, as distinct from ``blocker``, which is the reason
        there was no read at all. A caller that reports "the portal shows N
        applications" without consulting this is claiming a completeness it was
        not given.
        """
        if self.blocker:
            return self.blocker
        if self.skipped:
            return f"{len(self.skipped)} portal row(s) could not be read: " + "; ".join(self.skipped)
        return None

    @property
    def scope_declared(self) -> bool:
        """True when this snapshot said enough for a ledger record to be judged
        in or out of the portal's scope."""
        return bool(self.scope_tokens) or bool(self.number_pattern.strip())

    def compiled_number_pattern(self) -> "re.Pattern[str] | None":
        """The number shape as a compiled regex, or None. Never raises.

        A malformed pattern is treated as no pattern rather than as an error,
        because a bad scope hint must not be able to stop a reconciliation that
        can still be performed on the numbers actually read.
        """
        pattern = self.number_pattern.strip()
        if not pattern:
            return None
        try:
            return re.compile(pattern)
        except re.error:
            return None

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "PortalSnapshot":
        """Rebuild a snapshot from its own ``to_dict`` (or an equivalent)."""
        read_at = parse_dt(raw.get("read_at")) or datetime.now(timezone.utc)
        rows = raw.get("applications")
        apps = tuple(
            a for a in (PortalApplication.from_any(r) for r in (rows if isinstance(rows, list) else []))
            if a is not None
        )
        available = bool(raw.get("available"))
        blocker = raw.get("blocker")
        blocker = str(blocker) if blocker else None
        if not available and not blocker:
            blocker = "snapshot declared unavailable without stating a blocker"
        tokens = raw.get("scope_tokens")
        return cls(
            available=available,
            read_at=read_at,
            applications=apps,
            blocker=None if available else blocker,
            source=_text(raw.get("source")),
            funder=_text(raw.get("funder")),
            scope_tokens=tuple(str(t).strip().lower() for t in tokens if str(t).strip())
            if isinstance(tokens, (list, tuple)) else (),
            number_pattern=_text(raw.get("number_pattern")),
            skipped=tuple(str(s) for s in raw.get("skipped") or ()
                          if isinstance(raw.get("skipped"), (list, tuple))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "read_at": self.read_at.isoformat(),
            "blocker": self.blocker,
            "source": self.source,
            "funder": self.funder,
            "scope_tokens": list(self.scope_tokens),
            "number_pattern": self.number_pattern,
            "application_count": len(self.applications),
            "fully_read": self.fully_read,
            "skipped": list(self.skipped),
            "applications": [a.to_dict() for a in self.applications],
        }


def coerce_snapshot(obj: Any) -> PortalSnapshot:
    """Accept whatever a reader hands over and return a real snapshot.

    A :class:`PortalSnapshot` passes through. A mapping is rebuilt. Any object
    exposing ``.applications`` is duck-typed, so a reader written later — or by
    someone else — needs no coordination with this module beyond that one
    attribute. Anything else, including ``None``, becomes an *unavailable*
    snapshot whose blocker names what it was handed. Never raises: a caller
    reconciling against a broken input gets a report that says so.
    """
    if isinstance(obj, PortalSnapshot):
        return obj
    if obj is None:
        return PortalSnapshot.blocked("no portal snapshot supplied")
    if isinstance(obj, Mapping):
        return PortalSnapshot.from_dict(obj)
    rows = getattr(obj, "applications", None)
    if rows is None:
        return PortalSnapshot.blocked(
            f"cannot read a portal snapshot from {type(obj).__name__} — it exposes no .applications"
        )
    try:
        apps = tuple(a for a in (PortalApplication.from_any(r) for r in rows) if a is not None)
    except TypeError:
        return PortalSnapshot.blocked(
            f"{type(obj).__name__}.applications is not iterable"
        )
    read_at = getattr(obj, "read_at", None) or getattr(obj, "generated_at", None)
    if not isinstance(read_at, datetime):
        read_at = datetime.now(timezone.utc)
    available = bool(getattr(obj, "available", True))
    blocker = getattr(obj, "blocker", None)
    if not available and not blocker:
        blocker = f"{type(obj).__name__} reported unavailable without a blocker"
    tokens = getattr(obj, "scope_tokens", ()) or ()
    return PortalSnapshot(
        available=available,
        read_at=read_at,
        applications=apps,
        blocker=None if available else str(blocker),
        source=_text(getattr(obj, "source", "")),
        funder=_text(getattr(obj, "funder", "")),
        scope_tokens=tuple(str(t).strip().lower() for t in tokens if str(t).strip()),
        number_pattern=_text(getattr(obj, "number_pattern", "")),
    )


__all__ = [
    "PORTAL_HELD_STATES",
    "PORTAL_STATES",
    "STATE_IN_PROGRESS",
    "STATE_INELIGIBLE",
    "STATE_NOT_STARTED",
    "STATE_SUBMITTED",
    "STATE_UNKNOWN",
    "PortalApplication",
    "PortalSnapshot",
    "PortalState",
    "coerce_snapshot",
    "normalise_state",
]
