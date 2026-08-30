"""Portal truth versus the local ledger — the organ that catches a phantom.

**Why this exists.** The ledger at ``data/research/grants/pipeline.json`` is the
grant operator's running record, and it is the only funding picture the organism
has ever had. A funder's portal is the funder's picture. Nobody had ever put the
two side by side, and the first time it was done — by hand, in a chat window —
it found drift in *both* directions at once:

* portal applications with no record in the ledger at all, including submitted
  ones, which is live work the organism cannot see: no deadline tracking, no
  approval packet, no compliance check;
* ledger records the portal has never heard of, carrying deadline fields that
  therefore describe nothing. Those records are watch-items and off-portal
  routes filed as applications, and an earlier reading had already tripped over
  one — it reported a call as a live route with days remaining, on the strength
  of a deadline field no funder had ever confirmed.

The second class is the dangerous one, because it is *plausible*. A stale row
with a date on it reads exactly like a live obligation, and every downstream
consumer — urgency, alerts, the daemon's pressure on the HNC field — will treat
it as one. This module names that class explicitly: a ledger record with a
deadline that the portal cannot corroborate is a **phantom**, reported ``high``,
with the detail stating in words that its deadline field cannot be trusted.

**Who wins.** On any question the portal is authoritative and every conflict
detail says so. The portal is the funder's own system of record; the ledger is a
local transcription of it.

**What this module does not do.** It does not write the ledger. Not one field,
not once — ``pipeline.json`` is the operator's file, written live by him, and
this module only ever reads it. Every finding is a *recommendation* in a dated
markdown document, and the document says whose file it is. Nothing here submits,
files, sends or pays; there is no portal write path in this package at all, and
no credential handling anywhere in it.

**Scope, and why it is not guessed.** "The portal has never heard of it" is only
meaningful for a record that claims to be on that portal. A Horizon Europe
record is not missing from a UK dashboard — it was never on it. So the snapshot
declares its own scope (``scope_tokens`` / ``number_pattern``, see
:class:`~aureon.portals.schemas.PortalSnapshot`) and a snapshot that declares
none gets a report that makes **no** absent-from-portal claims and states that
reason in place of them. That is the difference between a reconciliation and a
list of everything the reader happened not to recognise.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aureon.grants.dossier import grants_directory, read_approval_rule
from aureon.grants.ledger import LEDGER_NAME, read_pipeline
from aureon.grants.schemas import Application, PipelineState
from aureon.portals.schemas import (
    STATE_IN_PROGRESS,
    STATE_INELIGIBLE,
    STATE_NOT_STARTED,
    STATE_SUBMITTED,
    STATE_UNKNOWN,
    PortalApplication,
    PortalSnapshot,
    coerce_snapshot,
)

LOG = logging.getLogger("aureon.portals.reconcile")

# ── the vocabulary of drift ──────────────────────────────────────────────────

KIND_MISSING_FROM_LEDGER = "missing_from_ledger"
KIND_ABSENT_FROM_PORTAL = "absent_from_portal"
KIND_STATE_CONFLICT = "state_conflict"
KIND_DEADLINE_CONFLICT = "deadline_conflict"

DRIFT_KINDS = frozenset(
    {KIND_MISSING_FROM_LEDGER, KIND_ABSENT_FROM_PORTAL, KIND_STATE_CONFLICT, KIND_DEADLINE_CONFLICT}
)

SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_LOW = "low"
SEVERITIES = (SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW)
_SEVERITY_RANK = {name: i for i, name in enumerate(SEVERITIES)}

#: Contribution of one drift to :attr:`ReconciliationReport.pressure`. Weights,
#: not measurements — see that property's docstring.
_SEVERITY_WEIGHT = {SEVERITY_HIGH: 1.0, SEVERITY_MEDIUM: 0.5, SEVERITY_LOW: 0.2}

TOPIC_RECONCILED = "portal.reconciled"

#: Source name used when this reading contributes to the shared HNC field.
SUBFIELD_SOURCE = "portal"

#: The document's filename prefix. Deliberately *not* ``RECONCILIATION_*``:
#: :func:`aureon.grants.dossier.read_approval_rule` globs that pattern for the
#: operator's own reconciliation sheet and quotes the approval rule out of it. A
#: name that collided would make this generated file the source of a rule a
#: human is supposed to own.
REPORT_PREFIX = "PORTAL_RECONCILIATION_"

#: Ledger fields searched for a portal application number, best first. The
#: numbers really do turn up in all of them — an id built around one, a name
#: quoting one, a note mentioning one — so a match in any is a match, and which
#: field carried it is recorded because a note is weaker evidence than an id.
LEDGER_NUMBER_FIELDS: tuple[str, ...] = ("id", "opportunity_id", "name", "notes")

#: Fields joined to test a ledger record against the snapshot's scope tokens.
_SCOPE_FIELDS: tuple[str, ...] = ("funder", "name", "notes", "status", "opportunity_id", "id")

#: How far two dates for the same deadline may differ before it is drift. A
#: portal prints a calendar date with no time of day while the ledger stores a
#: timestamp, so anything under a day is transcription, not disagreement.
DEADLINE_TOLERANCE_DAYS = 1.0

# Explicit negations in the ledger's free-text status. The ledger's ``status``
# is prose, not a vocabulary (see ``Application.CLOSED_STATES`` for the full
# argument), so this module refuses to classify it — it only reads the two
# statements that are unambiguous: an explicit denial of submission, and a claim
# of submission with no denial beside it. Everything else is *not compared*, and
# ``ReconciliationReport.unconfirmed_states`` counts how often that happened so
# a reader can see how much of "no state conflict" is silence.
_DENIES_SUBMISSION = ("NOT_SUBMITTED", "NOT_SENT", "UNSUBMITTED", "NOT_YET_SUBMITTED",
                      "NO_SUBMISSION", "NEVER_SUBMITTED", "NOT_LIVE")
_CLAIMS_SUBMISSION = ("SUBMITTED", "SUBMISSION_CONFIRMED", "FILED")


@dataclass(frozen=True)
class Drift:
    """One disagreement between the funder's record and the local one.

    ``detail`` is written for a person, not a parser: it names both sides, says
    which is authoritative, and where a value cannot be trusted it says that in
    words. The severity is about consequence, never about confidence — a drift
    is only reported when it was actually observed.
    """

    kind: str
    detail: str
    severity: str
    portal_number: str | None = None
    ledger_id: str | None = None

    def __post_init__(self) -> None:
        # Validated at construction rather than trusted by convention: a typo in
        # a kind or severity would silently drop the drift out of every count
        # and filter downstream, which is worse than not detecting it at all.
        if self.kind not in DRIFT_KINDS:
            raise ValueError(f"Drift.kind must be one of {sorted(DRIFT_KINDS)}, got {self.kind!r}")
        if self.severity not in SEVERITIES:
            raise ValueError(f"Drift.severity must be one of {list(SEVERITIES)}, got {self.severity!r}")
        if not str(self.detail).strip():
            raise ValueError("Drift.detail is mandatory — a finding nobody can read is not a finding")
        if self.portal_number is None and self.ledger_id is None:
            raise ValueError("Drift must name at least one side (portal_number or ledger_id)")

    @property
    def rank(self) -> int:
        return _SEVERITY_RANK[self.severity]

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "portal_number": self.portal_number,
            "ledger_id": self.ledger_id,
            "detail": self.detail,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class Match:
    """A ledger record tied to a portal application, and how it was tied.

    ``matched_on`` is the ledger field that carried the number. It is kept
    because the strength of the link differs: an id built around the number is
    the record *being* that application; the number appearing in a free-text
    note may only be a cross-reference. Reports quote it so a human can weigh
    the finding rather than take it on trust.
    """

    portal_number: str
    ledger_id: str
    matched_on: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "portal_number": self.portal_number,
            "ledger_id": self.ledger_id,
            "matched_on": self.matched_on,
        }


@dataclass(frozen=True)
class ReconciliationReport:
    """What the funder's record and the local one say about each other.

    ``available=False`` means no reconciliation happened — the portal could not
    be read, or the ledger could not be — and ``blocker`` says which. An
    unavailable report has no drifts, and that emptiness must never be read as
    agreement. The two states are as different here as they are on a connector.
    """

    available: bool
    generated_at: datetime
    drifts: tuple[Drift, ...] = ()
    matched: tuple[Match, ...] = ()
    portal_only: tuple[str, ...] = ()
    ledger_only: tuple[str, ...] = ()
    blocker: str | None = None
    portal_source: str = ""
    portal_funder: str = ""
    portal_read_at: datetime | None = None
    ledger_path: str = ""
    portal_count: int = 0
    ledger_count: int = 0
    in_scope_ledger_count: int = 0
    out_of_scope_ledger_count: int = 0
    scope_note: str = ""
    unconfirmed_states: int = 0
    ambiguous_ledger_ids: tuple[str, ...] = ()
    # Rows the portal reader could not read, carried through verbatim from
    # ``PortalSnapshot.skipped``. These matter to exactly one finding: a ledger
    # record can only be called absent from the portal if the whole portal was
    # read. A skipped row might BE that record's application, so every
    # absent-from-portal detail says so when this is non-empty. It does not
    # weaken ``missing_from_ledger`` — a row that was read is on the portal.
    portal_skipped: tuple[str, ...] = ()

    @property
    def portal_read_partial(self) -> bool:
        """True when the portal read left rows unread — see :attr:`portal_skipped`."""
        return bool(self.portal_skipped)

    # ── reading the result ───────────────────────────────────────────────
    @property
    def clean(self) -> bool:
        """True only when a reconciliation actually ran and found nothing."""
        return self.available and not self.drifts

    @property
    def high(self) -> tuple[Drift, ...]:
        return tuple(d for d in self.drifts if d.severity == SEVERITY_HIGH)

    def of_kind(self, kind: str) -> tuple[Drift, ...]:
        return tuple(d for d in self.drifts if d.kind == kind)

    @property
    def counts_by_severity(self) -> dict[str, int]:
        return {s: sum(1 for d in self.drifts if d.severity == s) for s in SEVERITIES}

    @property
    def counts_by_kind(self) -> dict[str, int]:
        return {k: len(self.of_kind(k)) for k in sorted(DRIFT_KINDS)}

    @property
    def pressure(self) -> float | None:
        """0..1 weight of unreconciled drift. ``None`` when nothing was compared.

        Two honest limits, stated because they are choices rather than facts:

        * The weights in :data:`_SEVERITY_WEIGHT` are a **ranking made numeric**,
          not a measurement of harm. They exist so one high finding outweighs one
          medium one in the field contribution, and nothing finer should be read
          into the value.
        * The denominator is how many records were actually compared, so the
          same absolute drift on a larger pipeline reads as less pressure. That
          is intended — drift matters relative to the picture it distorts — but
          it means this number is a *proportion of a picture*, not a count.

        ``None`` when the report is unavailable or nothing was in scope: no
        comparison happened, and 0.0 would say the opposite. ``0.0`` from an
        available report is a real measurement — it means reconciled and clean.
        """
        if not self.available:
            return None
        considered = self.portal_count + self.in_scope_ledger_count
        if considered <= 0:
            return None
        weighted = sum(_SEVERITY_WEIGHT.get(d.severity, 0.0) for d in self.drifts)
        return max(0.0, min(1.0, weighted / considered))

    @property
    def symbolic_life_score(self) -> float | None:
        """The field contribution: unreconciled drift is a real cost.

        Shaped for :func:`aureon.core.hnc_field.publish_subfield`, which reads
        this attribute off whatever it is given. ``None`` when there is no
        reading, so the organism senses an absence rather than a calm.
        """
        pressure = self.pressure
        return None if pressure is None else 1.0 - pressure

    # Plain class attributes, deliberately *not* dataclass fields.
    # ``publish_subfield`` reads three attributes off whatever it is handed, and
    # these are two of them. A reconciliation measures neither Γ nor a
    # consciousness level, so they are present and ``None`` — the field reads an
    # absence rather than a value this organ had no way to compute.
    coherence_gamma = None
    consciousness_level = None

    def to_dict(self) -> dict[str, Any]:
        pressure = self.pressure
        return {
            "available": self.available,
            "generated_at": self.generated_at.isoformat(),
            "blocker": self.blocker,
            "portal_source": self.portal_source,
            "portal_funder": self.portal_funder,
            "portal_read_at": self.portal_read_at.isoformat() if self.portal_read_at else None,
            "ledger_path": self.ledger_path,
            "portal_count": self.portal_count,
            "ledger_count": self.ledger_count,
            "in_scope_ledger_count": self.in_scope_ledger_count,
            "out_of_scope_ledger_count": self.out_of_scope_ledger_count,
            "scope_note": self.scope_note,
            "matched_count": len(self.matched),
            "portal_only": list(self.portal_only),
            "ledger_only": list(self.ledger_only),
            "ambiguous_ledger_ids": list(self.ambiguous_ledger_ids),
            "portal_skipped": list(self.portal_skipped),
            "portal_read_partial": self.portal_read_partial,
            "unconfirmed_states": self.unconfirmed_states,
            "drift_count": len(self.drifts),
            "counts_by_severity": self.counts_by_severity,
            "counts_by_kind": self.counts_by_kind,
            "pressure": None if pressure is None else round(pressure, 4),
            "clean": self.clean,
            "matched": [m.to_dict() for m in self.matched],
            "drifts": [d.to_dict() for d in self.drifts],
        }


# ── matching ─────────────────────────────────────────────────────────────────


def _field_text(app: Application, name: str) -> str:
    value = getattr(app, name, "")
    return str(value) if value else ""


def _number_regex(number: str) -> re.Pattern[str]:
    """Match this application number, but never inside a longer number.

    The lookarounds matter: without them the number ``10210045`` matches inside
    ``102100456``, tying a ledger record to an application that is not it — and
    a false match is worse than a miss, because it silences the
    ``missing_from_ledger`` finding that would otherwise have been raised.
    """
    return re.compile(rf"(?<!\d){re.escape(number)}(?!\d)")


def _match_field(app: Application, pattern: re.Pattern[str]) -> str | None:
    """Which ledger field carries this number, strongest first, or None."""
    for name in LEDGER_NUMBER_FIELDS:
        if pattern.search(_field_text(app, name)):
            return name
    return None


def _in_scope(app: Application, tokens: tuple[str, ...],
              number_pattern: re.Pattern[str] | None) -> bool:
    """Does this ledger record claim to live on the portal that was read?

    Two independent ways to qualify: the snapshot's scope tokens appearing
    anywhere in the record, or the record carrying a number of the portal's own
    shape. The second catches a record for an application the portal no longer
    lists at all, which the first would miss whenever the funder is not named.

    How far the second rule reaches is the reader's choice, not this function's:
    an *anchored* ``number_pattern`` (``^\\d{7,10}$``) qualifies only a field that
    **is** such a number, while an unanchored one also finds a number embedded in
    a longer id or note. Both are honoured as written — silently stripping a
    reader's anchors would widen a scope judgement it deliberately narrowed.
    """
    if tokens:
        haystack = " ".join(_field_text(app, f) for f in _SCOPE_FIELDS).lower()
        if any(token in haystack for token in tokens):
            return True
    if number_pattern is not None:
        for name in LEDGER_NUMBER_FIELDS:
            if number_pattern.search(_field_text(app, name)):
                return True
    return False


# ── the comparisons ──────────────────────────────────────────────────────────


def _ledger_submission_claim(app: Application) -> bool | None:
    """Does the ledger say this was submitted? ``None`` when it does not say.

    Deliberately weak. The ledger's status is a free-text sentence, and this
    module will not build the classifier :mod:`aureon.grants.schemas` correctly
    refused to build. It reads only what is unambiguous:

    * an explicit denial (``…NOT_SUBMITTED…``) → ``False``, and a denial always
      wins over a claim in the same string, because a status that says both is
      describing something that was prepared and not sent;
    * a submission marker with no denial → ``True``;
    * anything else → ``None``, meaning *no comparison is possible*, which is
      counted rather than resolved.
    """
    status = _field_text(app, "status").strip().upper()
    if not status:
        return None
    if any(marker in status for marker in _DENIES_SUBMISSION):
        return False
    if any(marker in status for marker in _CLAIMS_SUBMISSION):
        return True
    return None


def _state_drift(portal: PortalApplication, ledger: Application) -> tuple[Drift | None, bool]:
    """Compare submission state. Returns ``(drift, compared)``.

    ``compared`` is False when the two sides could not be put in the same terms,
    so the caller can count the silence instead of reporting agreement.
    """
    claim = _ledger_submission_claim(ledger)
    said = portal.state_text or portal.state

    if portal.state == STATE_SUBMITTED:
        if claim is False:
            return (
                Drift(
                    kind=KIND_STATE_CONFLICT,
                    severity=SEVERITY_HIGH,
                    portal_number=portal.number,
                    ledger_id=ledger.id,
                    detail=(
                        f"the portal shows {portal.label} as submitted (\"{said}\") but ledger "
                        f"record `{ledger.id}` states it was not submitted (\"{ledger.status}\"). "
                        "The portal is authoritative on submission: the funder holds this "
                        "application. Until the ledger is corrected, the organism will keep "
                        "treating filed work as outstanding and may re-prepare or re-send it."
                    ),
                ),
                True,
            )
        return (None, claim is not None)

    if portal.state in (STATE_IN_PROGRESS, STATE_NOT_STARTED):
        if claim is True:
            return (
                Drift(
                    kind=KIND_STATE_CONFLICT,
                    severity=SEVERITY_HIGH,
                    portal_number=portal.number,
                    ledger_id=ledger.id,
                    detail=(
                        f"ledger record `{ledger.id}` records this as submitted "
                        f"(\"{ledger.status}\") but the portal shows {portal.label} as \"{said}\" — "
                        "the funder has not received it. The portal is authoritative: work the "
                        "ledger believes finished is still outstanding, and the ledger's status is "
                        "the reason nobody is working on it."
                    ),
                ),
                True,
            )
        return (None, claim is not None)

    if portal.state == STATE_INELIGIBLE:
        if ledger.lifecycle == "live":
            return (
                Drift(
                    kind=KIND_STATE_CONFLICT,
                    severity=SEVERITY_MEDIUM,
                    portal_number=portal.number,
                    ledger_id=ledger.id,
                    detail=(
                        f"the portal has ruled {portal.label} ineligible (\"{said}\") while ledger "
                        f"record `{ledger.id}` still carries it as live work "
                        f"(\"{ledger.status}\"). The portal is authoritative: effort spent here "
                        "cannot produce an award."
                    ),
                ),
                True,
            )
        return (None, True)

    # The portal's own words were not recognised (:data:`STATE_UNKNOWN`).
    # Nothing is asserted about it; the report says the state was not compared.
    assert portal.state == STATE_UNKNOWN  # noqa: S101 — the vocabulary is closed
    return (None, False)


def _deadline_drift(portal: PortalApplication, ledger: Application, now: datetime) -> Drift | None:
    """Compare deadlines. The portal wins, and the detail says so."""
    p_deadline, l_deadline = portal.deadline, ledger.deadline

    if p_deadline is not None and l_deadline is not None:
        gap_days = (l_deadline - p_deadline).total_seconds() / 86400.0
        if abs(gap_days) <= DEADLINE_TOLERANCE_DAYS:
            return None
        # A ledger date LATER than the portal's is the dangerous direction: work
        # paced to it arrives after the funder has closed. Earlier is wasteful
        # but safe, so it is reported at a lower severity rather than not at all.
        late = gap_days > 0
        return Drift(
            kind=KIND_DEADLINE_CONFLICT,
            severity=SEVERITY_HIGH if late else SEVERITY_MEDIUM,
            portal_number=portal.number,
            ledger_id=ledger.id,
            detail=(
                f"deadline disagreement on {portal.label}: the portal says "
                f"{p_deadline.date().isoformat()}"
                + (f" (\"{portal.deadline_text}\")" if portal.deadline_text else "")
                + f", ledger record `{ledger.id}` says {l_deadline.date().isoformat()} — "
                f"{abs(gap_days):.1f} days apart. **The portal is authoritative**; the ledger "
                "should be corrected to the portal's date. "
                + (
                    "The ledger's date is the LATER of the two, so anything paced to the ledger "
                    "misses the funder's real deadline."
                    if late
                    else "The ledger's date is the earlier of the two, so the pressure it "
                    "generates is overstated rather than dangerous."
                )
            ),
        )

    if p_deadline is not None and l_deadline is None:
        return Drift(
            kind=KIND_DEADLINE_CONFLICT,
            severity=SEVERITY_MEDIUM,
            portal_number=portal.number,
            ledger_id=ledger.id,
            detail=(
                f"the portal states a deadline for {portal.label} of "
                f"{p_deadline.date().isoformat()}"
                + (f" (\"{portal.deadline_text}\")" if portal.deadline_text else "")
                + f" which ledger record `{ledger.id}` does not carry. The portal is "
                "authoritative; with no date in the ledger this application contributes nothing "
                "to deadline alerting and can pass its close date unnoticed."
            ),
        )

    if l_deadline is not None and p_deadline is None and portal.portal_holds_it:
        if l_deadline <= now:
            return None
        return Drift(
            kind=KIND_DEADLINE_CONFLICT,
            severity=SEVERITY_MEDIUM,
            portal_number=portal.number,
            ledger_id=ledger.id,
            detail=(
                f"ledger record `{ledger.id}` carries a future deadline "
                f"({l_deadline.date().isoformat()}) for {portal.label}, which the portal shows as "
                f"\"{portal.state_text or portal.state}\" with no open deadline. The portal is "
                "authoritative: this date describes work the funder already holds, so it must not "
                "be read as time remaining. Left in place it generates urgency for nothing."
            ),
        )

    return None


def _missing_from_ledger(portal: PortalApplication) -> Drift:
    """A portal application with no record in the ledger at all."""
    if portal.is_submitted:
        return Drift(
            kind=KIND_MISSING_FROM_LEDGER,
            severity=SEVERITY_HIGH,
            portal_number=portal.number,
            detail=(
                f"portal application {portal.label} is SUBMITTED "
                f"(\"{portal.state_text or portal.state}\") and has no record in the ledger. "
                "This is live work the organism cannot see: it is absent from deadline tracking, "
                "from compliance checks, and from any approval packet. A funder decision on it "
                "would arrive against a record that does not exist locally."
            ),
        )
    return Drift(
        kind=KIND_MISSING_FROM_LEDGER,
        severity=SEVERITY_MEDIUM,
        portal_number=portal.number,
        detail=(
            f"portal application {portal.label} is \"{portal.state_text or portal.state}\" on the "
            "portal and has no record in the ledger"
            + (
                f"; the portal shows {portal.percent_complete}% complete"
                if portal.percent_complete is not None
                else ""
            )
            + (
                f" with {portal.days_left} days left"
                if portal.days_left is not None
                else ""
            )
            + ". Nothing local is tracking it."
        ),
    )


def _partial_caveat(skipped: tuple[str, ...]) -> str:
    """The sentence that keeps an absent-from-portal finding honest on a partial read."""
    if not skipped:
        return ""
    return (
        f" This portal read was PARTIAL — {len(skipped)} row(s) could not be read — so the "
        "possibility that this record matches an unread row cannot be excluded. Confirm against "
        "the portal before reclassifying it."
    )


def _absent_from_portal(ledger: Application, funder: str, caveat: str = "") -> Drift:
    """A ledger record the portal has never heard of — the phantom case.

    The severity split is the point of this whole module. A record carrying a
    **deadline** the portal cannot corroborate is not merely stale: it is
    actively manufacturing urgency out of a field nobody confirmed, and it reads
    identically to a real live route. That is the error this capability exists
    to catch, so its detail says in words that the deadline cannot be trusted.
    """
    whose = f"the {funder} portal" if funder else "the portal"
    label = f"`{ledger.id}`" + (f" (\"{ledger.name}\")" if ledger.name else "")
    if ledger.deadline is not None:
        return Drift(
            kind=KIND_ABSENT_FROM_PORTAL,
            severity=SEVERITY_HIGH,
            ledger_id=ledger.id,
            detail=(
                f"PHANTOM: ledger record {label} carries a deadline of "
                f"{ledger.deadline.date().isoformat()} but {whose} has no application for it. "
                "Its deadline field cannot be trusted — no funder has confirmed that date, and "
                "the record is most likely a watch-item or an off-portal route being carried as "
                "an application. Any urgency, alert or days-remaining figure computed from this "
                "date is an artefact of the ledger, not a fact about a call. Verify against the "
                "funder before acting on it, and do not report it as a live route." + caveat
            ),
        )
    return Drift(
        kind=KIND_ABSENT_FROM_PORTAL,
        severity=SEVERITY_MEDIUM,
        ledger_id=ledger.id,
        detail=(
            f"ledger record {label} is in the portal's scope but {whose} has no application for "
            "it. It carries no deadline, so it generates no false urgency, but it is being "
            "counted as an application the funder has never received — which overstates the "
            "pipeline. Confirm whether it is a watch-item rather than an application." + caveat
        ),
    )


# ── the organ ────────────────────────────────────────────────────────────────


def reconcile(
    snapshot: Any,
    state: PipelineState | None = None,
    *,
    now: datetime | None = None,
) -> ReconciliationReport:
    """Put the funder's record and the local one side by side. Never raises.

    ``snapshot`` is a :class:`~aureon.portals.schemas.PortalSnapshot`, or
    anything :func:`~aureon.portals.schemas.coerce_snapshot` can read as one.
    ``state`` defaults to a fresh read of the live ledger via
    :func:`aureon.grants.ledger.read_pipeline` — read-only, always.

    Either side being unreadable yields an ``available=False`` report naming the
    blocker. That is not a failure mode to be smoothed over: a reconciliation
    that did not happen must never look like one that found nothing.
    """
    snap = coerce_snapshot(snapshot)
    reference = now or (snap.read_at if snap.available else None) or datetime.now(UTC)
    if state is None:
        state = read_pipeline(now=reference)

    blockers: list[str] = []
    if not snap.available:
        blockers.append(f"portal not read: {snap.blocker}")
    if not state.available:
        blockers.append(f"ledger not read: {state.blocker}")
    if blockers:
        return ReconciliationReport(
            available=False,
            generated_at=reference,
            blocker="; ".join(blockers),
            portal_source=snap.source,
            portal_funder=snap.funder,
            portal_read_at=snap.read_at,
            ledger_path=state.ledger_path,
            portal_count=len(snap.applications),
            ledger_count=len(state.applications),
            portal_skipped=tuple(snap.skipped),
        )

    by_number = {a.number: a for a in snap.applications}
    patterns = {number: _number_regex(number) for number in by_number}
    scope_tokens = tuple(t for t in (s.strip().lower() for s in snap.scope_tokens) if t)
    number_pattern = snap.compiled_number_pattern()
    skipped = tuple(snap.skipped)
    caveat = _partial_caveat(skipped)

    matches: list[Match] = []
    drifts: list[Drift] = []
    matched_numbers: set[str] = set()
    ledger_only: list[str] = []
    ambiguous: list[str] = []
    in_scope = 0
    out_of_scope = 0
    unconfirmed = 0

    for app in state.applications:
        carried = [
            (number, matched_on)
            for number, pattern in patterns.items()
            if (matched_on := _match_field(app, pattern)) is not None
        ]
        if carried:
            in_scope += 1
            for number, matched_on in carried:
                matched_numbers.add(number)
                matches.append(Match(portal_number=number, ledger_id=app.id, matched_on=matched_on))
            if len(carried) > 1:
                # One record naming several applications cannot have its own
                # status and deadline attributed to any single one of them.
                # Comparing anyway would invent a conflict; the ambiguity is
                # reported instead so a human can split the record.
                ambiguous.append(app.id)
                continue
            portal_app = by_number[carried[0][0]]
            state_drift, compared = _state_drift(portal_app, app)
            if state_drift is not None:
                drifts.append(state_drift)
            if not compared:
                unconfirmed += 1
            deadline_drift = _deadline_drift(portal_app, app, reference)
            if deadline_drift is not None:
                drifts.append(deadline_drift)
            continue

        if _in_scope(app, scope_tokens, number_pattern):
            in_scope += 1
            ledger_only.append(app.id)
            drifts.append(_absent_from_portal(app, snap.funder, caveat))
        else:
            out_of_scope += 1

    portal_only = [n for n in by_number if n not in matched_numbers]
    for number in portal_only:
        drifts.append(_missing_from_ledger(by_number[number]))

    drifts.sort(key=lambda d: (d.rank, d.kind, d.portal_number or "", d.ledger_id or ""))
    matches.sort(key=lambda m: (m.portal_number, m.ledger_id))

    return ReconciliationReport(
        available=True,
        generated_at=reference,
        drifts=tuple(drifts),
        matched=tuple(matches),
        portal_only=tuple(sorted(portal_only)),
        ledger_only=tuple(ledger_only),
        portal_source=snap.source,
        portal_funder=snap.funder,
        portal_read_at=snap.read_at,
        ledger_path=state.ledger_path,
        portal_count=len(snap.applications),
        ledger_count=len(state.applications),
        in_scope_ledger_count=in_scope,
        out_of_scope_ledger_count=out_of_scope,
        scope_note=_scope_note(snap, out_of_scope),
        unconfirmed_states=unconfirmed,
        ambiguous_ledger_ids=tuple(ambiguous),
        portal_skipped=skipped,
    )


def _scope_note(snap: PortalSnapshot, out_of_scope: int) -> str:
    """State plainly which ledger records this reconciliation could judge.

    A reader must be able to tell a clean reconciliation from a narrow one. When
    the snapshot declared no scope, this is the sentence that says no
    absent-from-portal finding could be made at all — printed in place of the
    findings, never instead of mentioning them.
    """
    if not snap.scope_declared:
        return (
            "The snapshot declared no scope (no funder tokens, no application-number shape), so "
            "**no ledger record was judged absent from the portal**. Only records already carrying "
            "a portal application number were compared. This is a partial reconciliation: a "
            "phantom record that never names the funder cannot be detected without a declared "
            "scope."
        )
    tokens = ", ".join(f"`{t}`" for t in snap.scope_tokens) or "none"
    return (
        f"Ledger records were judged in scope by funder tokens ({tokens})"
        + (f" and by application-number shape `{snap.number_pattern}`" if snap.number_pattern else "")
        + f". {out_of_scope} ledger record(s) matched neither and were left out of the comparison "
        "entirely — they belong to other funders and are not claimed to be missing from anything."
    )


# ── the document ─────────────────────────────────────────────────────────────

_LEDGER_OWNERSHIP = (
    "**`pipeline.json` is the grant operator's file and is written live by him.** Nothing in "
    "this reconciliation has been applied to it and nothing in this repository will apply it. "
    "Every item below is a recommendation for a human to accept, reject or correct."
)


def _severity_badge(severity: str) -> str:
    return {SEVERITY_HIGH: "HIGH", SEVERITY_MEDIUM: "MEDIUM", SEVERITY_LOW: "LOW"}[severity]


def _kind_heading(kind: str) -> str:
    return {
        KIND_MISSING_FROM_LEDGER: "On the portal, missing from the ledger",
        KIND_ABSENT_FROM_PORTAL: "In the ledger, absent from the portal",
        KIND_STATE_CONFLICT: "State conflicts",
        KIND_DEADLINE_CONFLICT: "Deadline conflicts — the portal wins",
    }[kind]


def render_markdown(report: ReconciliationReport, *, root: Path | str | None = None) -> str:
    """One document a person can act from. Every absence printed as an absence.

    There is no section that reads as clean because its source was missing: an
    unavailable report renders as a blocker and nothing else, and a narrow scope
    is stated where the findings would have been.

    ``root`` locates the grants directory the operating constraint is quoted
    from, and is honoured verbatim with no environment fallback — the rule
    :func:`aureon.grants.ledger.grants_dir` follows, so a caller working in a
    temporary tree cannot silently reach into the live repository.
    """
    stamp = report.generated_at.date().isoformat()
    who = report.portal_funder or "portal"
    lines: list[str] = [
        f"# Portal reconciliation — {who} vs the local ledger",
        "",
        f"**Generated** {report.generated_at.isoformat()}  ",
        f"**Portal read** {report.portal_read_at.isoformat() if report.portal_read_at else 'not recorded'}"
        + (f" from {report.portal_source}" if report.portal_source else "")
        + "  ",
        f"**Ledger** `{report.ledger_path or 'not recorded'}` (read-only)",
        "",
        f"> {_LEDGER_OWNERSHIP}",
        "",
    ]

    rule = read_approval_rule(grants_directory(root))
    if rule is not None:
        lines += [
            f"Operating constraint in force, quoted verbatim from `{rule.source}`:",
            "",
            f"> {rule.value}",
            "",
        ]
    else:
        lines += [
            "**Approval rule not quotable** — no operator reconciliation sheet in the grants "
            "directory carried one. The constraint still stands; this document simply could not "
            "cite its source.",
            "",
        ]

    if not report.available:
        lines += [
            "## No reconciliation was performed",
            "",
            f"**Blocker:** {report.blocker or 'not recorded'}",
            "",
            "This is not a clean result. Nothing was compared, so nothing below can be read as "
            "agreement between the portal and the ledger. The portal session belongs to the "
            "operator's browser: an unauthenticated reader reports absence and stops, which is "
            "what happened here.",
            "",
        ]
        return "\n".join(lines) + "\n"

    counts = report.counts_by_severity
    pressure = report.pressure
    lines += [
        "## What was compared",
        "",
        f"- **{report.portal_count}** application(s) on the portal",
        f"- **{report.ledger_count}** record(s) in the ledger, of which **{report.in_scope_ledger_count}** "
        f"were in the portal's scope and **{report.out_of_scope_ledger_count}** were not",
        f"- **{len(report.matched)}** portal-to-ledger link(s) established",
        f"- **{len(report.drifts)}** drift(s): {counts[SEVERITY_HIGH]} high, "
        f"{counts[SEVERITY_MEDIUM]} medium, {counts[SEVERITY_LOW]} low",
        f"- **Drift pressure** {'not computable' if pressure is None else f'{pressure:.2f}'} "
        "(a weighted proportion of the records compared, not a measurement of harm)",
        "",
        report.scope_note,
        "",
    ]

    if report.portal_read_partial:
        lines += [
            f"**The portal read was PARTIAL — {len(report.portal_skipped)} row(s) could not be "
            "read.** The count above is therefore a floor, not a total, and no ledger record below "
            "can be called absent from the portal with certainty: one of the unread rows may be "
            "its application. Unread rows, verbatim:",
            "",
        ]
        lines += [f"- {note}" for note in report.portal_skipped]
        lines.append("")

    if report.unconfirmed_states:
        lines += [
            f"**{report.unconfirmed_states} matched record(s) had no comparable state.** The "
            "ledger's `status` is free text, and this reconciliation reads only two unambiguous "
            "statements from it — an explicit denial of submission, or a submission marker with no "
            "denial beside it. Anything else is left uncompared rather than classified by guess. "
            "Absence of a state conflict on those records is silence, not agreement.",
            "",
        ]

    if report.ambiguous_ledger_ids:
        lines += [
            "**Records naming more than one portal application** (their status and deadline cannot "
            "be attributed to a single application, so neither was compared): "
            + ", ".join(f"`{i}`" for i in report.ambiguous_ledger_ids),
            "",
        ]

    if report.clean:
        lines += [
            "## No drift",
            "",
            "Every portal application "
            + ("that could be read " if report.portal_read_partial else "")
            + "has a ledger record, every in-scope ledger record has a portal application, and no "
            "state or deadline disagreed. This is a measurement, not a default: the comparison ran "
            "over the counts above."
            + (
                " It is not a clean bill of health, because the portal read was partial."
                if report.portal_read_partial
                else ""
            ),
            "",
        ]
    else:
        lines += ["## Drift", ""]
        for kind in (KIND_ABSENT_FROM_PORTAL, KIND_MISSING_FROM_LEDGER,
                     KIND_STATE_CONFLICT, KIND_DEADLINE_CONFLICT):
            found = report.of_kind(kind)
            if not found:
                continue
            lines += [f"### {_kind_heading(kind)} ({len(found)})", ""]
            for drift in found:
                where = " · ".join(
                    part for part in (
                        f"portal `{drift.portal_number}`" if drift.portal_number else "",
                        f"ledger `{drift.ledger_id}`" if drift.ledger_id else "",
                    ) if part
                )
                lines += [f"- **[{_severity_badge(drift.severity)}]** {where} — {drift.detail}", ""]

    lines += [
        "## Recommended corrections",
        "",
        _LEDGER_OWNERSHIP,
        "",
    ]
    if report.clean:
        lines.append("None. Nothing was found that needs correcting.")
    else:
        for drift in report.drifts:
            lines.append(f"- {_recommendation(drift)}")
    lines += [
        "",
        "## Provenance",
        "",
        "Every value above was parsed from the portal read or from the ledger. No value was "
        "defaulted, inferred, or carried over from a previous document. Where a comparison could "
        "not be made it is named as uncompared rather than reported as agreement.",
        "",
        f"Document: `{REPORT_PREFIX}{report.generated_at.strftime('%Y%m%d')}.md` · "
        f"reconciled {stamp}",
    ]
    return "\n".join(lines) + "\n"


def _recommendation(drift: Drift) -> str:
    """The single action a human would take on one finding."""
    if drift.kind == KIND_MISSING_FROM_LEDGER:
        return (
            f"Add portal application `{drift.portal_number}` to the ledger with the portal's own "
            "state and deadline (operator action)."
        )
    if drift.kind == KIND_ABSENT_FROM_PORTAL:
        return (
            f"Confirm what ledger record `{drift.ledger_id}` actually is. If it is a watch-item or "
            "an off-portal route, reclassify it so it stops being counted as an application, and "
            "clear or annotate its deadline field so nothing computes urgency from it."
        )
    if drift.kind == KIND_STATE_CONFLICT:
        return (
            f"Set ledger record `{drift.ledger_id}` to the state the portal reports for "
            f"`{drift.portal_number}` (the portal is authoritative)."
        )
    return (
        f"Correct the deadline on ledger record `{drift.ledger_id}` to the portal's date for "
        f"`{drift.portal_number}` (the portal is authoritative)."
    )


# ── writing, publishing ──────────────────────────────────────────────────────


def report_path(when: datetime, *, root: Path | str | None = None) -> Path:
    """Where a reconciliation for this date is written."""
    return grants_directory(root) / f"{REPORT_PREFIX}{when.strftime('%Y%m%d')}.md"


def write_report(report: ReconciliationReport, *, root: Path | str | None = None) -> Path | None:
    """Write the document. Returns the path, or None if it could not be written.

    An *unavailable* report is still written: a cycle in which the portal could
    not be read is a fact about the operation and leaving no trace of it would
    make an unreconciled day indistinguishable from a clean one.

    The only file this function will write is the dated document named by
    :func:`report_path`. The guard below is not defensive noise — it is the
    single mechanical assurance that no future edit can point this writer at the
    operator's ledger.
    """
    if report is None:
        return None
    path = report_path(report.generated_at, root=root)
    if path.name == LEDGER_NAME or not path.name.startswith(REPORT_PREFIX):
        raise ValueError(f"refusing to write outside the reconciliation document: {path.name}")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_markdown(report, root=root), encoding="utf-8")
    except OSError as exc:
        LOG.warning("portal reconciliation could not be written to %s: %s", path, type(exc).__name__)
        return None
    LOG.info("portal reconciliation written: %s", path)
    return path


def publish(report: ReconciliationReport, bus: Any = None) -> None:
    """Announce the reconciliation, and let drift press on the shared field.

    Two separate acts, both guarded, both best-effort — visibility must never be
    able to stop the organ:

    * ``portal.reconciled`` on the thought bus, for *every* report including an
      unavailable one. A cycle where the portal could not be read is exactly the
      thing another organ needs to hear about.
    * ``publish_subfield("portal", …)`` **only when there is drift**. A clean
      reconciliation would publish a symbolic life score of 1.0, and this organ
      has no standing to make that claim about the whole organism — it looked at
      one funder's dashboard. Silence on a clean read is the honest contribution;
      unreconciled drift is real pressure and is published as such.
    """
    try:
        from aureon.core.aureon_thought_bus import Thought, get_thought_bus

        target = bus if bus is not None else get_thought_bus()
        if target is not None:
            target.publish(
                Thought(source=SUBFIELD_SOURCE, topic=TOPIC_RECONCILED, payload=report.to_dict())
            )
    except Exception:  # noqa: BLE001 — awareness must never crash the organ
        LOG.debug("portal.reconciled publish skipped", exc_info=True)

    pressure = report.pressure
    if pressure is None or pressure <= 0.0:
        return
    try:
        from aureon.core.hnc_field import publish_subfield

        publish_subfield(SUBFIELD_SOURCE, report, bus=bus)
    except Exception:  # noqa: BLE001
        LOG.debug("portal sub-field publish skipped", exc_info=True)


def emit_reconciliation(
    snapshot: Any,
    *,
    state: PipelineState | None = None,
    root: Path | str | None = None,
    bus: Any = None,
    now: datetime | None = None,
    write: bool = True,
) -> tuple[ReconciliationReport, Path | None]:
    """Reconcile, publish, write — one call, the unit a daemon would repeat."""
    report = reconcile(snapshot, state, now=now)
    publish(report, bus=bus)
    return report, (write_report(report, root=root) if write else None)


__all__ = [
    "DEADLINE_TOLERANCE_DAYS",
    "DRIFT_KINDS",
    "KIND_ABSENT_FROM_PORTAL",
    "KIND_DEADLINE_CONFLICT",
    "KIND_MISSING_FROM_LEDGER",
    "KIND_STATE_CONFLICT",
    "LEDGER_NUMBER_FIELDS",
    "REPORT_PREFIX",
    "SEVERITIES",
    "SEVERITY_HIGH",
    "SEVERITY_LOW",
    "SEVERITY_MEDIUM",
    "SUBFIELD_SOURCE",
    "TOPIC_RECONCILED",
    "Drift",
    "Match",
    "ReconciliationReport",
    "emit_reconciliation",
    "publish",
    "reconcile",
    "render_markdown",
    "report_path",
    "write_report",
]
