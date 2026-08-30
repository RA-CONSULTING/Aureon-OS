"""Grant-capability data model.

Mirrors the shapes Codex's operator runs already write into
``data/research/grants/pipeline.json`` — this package reads that ledger as the
source of truth rather than inventing a parallel one. Every field is either a
real value from the ledger or ``None``; nothing is defaulted into existence.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _round(value: Any, places: int = 4) -> Any:
    return round(value, places) if isinstance(value, float) else value


def parse_dt(value: Any) -> datetime | None:
    """Parse an ISO timestamp from the ledger, or return None.

    The ledger mixes tz-aware (`+01:00`) and naive stamps. Naive values are
    assumed UTC so comparisons never raise; an unparseable value is None, never
    "now" — a missing deadline must not silently become an urgent one.
    """
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@dataclass
class Application:
    """One funding application as recorded in the ledger."""

    id: str
    name: str = ""
    funder: str = ""
    status: str = ""
    opportunity_id: str = ""
    amount_requested: float | None = None
    currency: str = ""
    deadline: datetime | None = None
    submitted_at: datetime | None = None
    documents: tuple[str, ...] = ()
    notes: str = ""
    last_checked: datetime | None = None

    # Terminal states — no further action is possible or needed. Matched
    # EXACTLY (after strip + upper), never by substring or token.
    #
    # That exactness is deliberate and it is the reason ``is_open`` is weaker
    # than it looks. The live ledger's ``status`` field is free text, not a
    # vocabulary: 61 of its 66 entries carry compound sentences such as
    # ``SERAPHIM_SPACE_CONTACT_SUBMITTED_DECK_ROUTE_REQUESTED_WAITING_REPLY``
    # or ``FOUNDER_ONLY_FORM_POLICY_GATE_NOT_SUBMITTED_BY_OPERATOR``. Substring
    # or token matching on "SUBMITTED" would close the first (it is plainly
    # still live — it is waiting on a reply) and, without a negation guard,
    # the second as well. Both directions are wrong, and neither can be fixed
    # without inventing a classifier the data does not support.
    #
    # So the code declines to guess. Only an exact terminal status is
    # recognised; everything else is *unclassified* and counted as open,
    # because unattended-but-unknown is the direction that keeps a deadline
    # visible. ``status_recognised`` and
    # ``PipelineState.unrecognised_status_count`` exist so a reader can see how
    # much of ``open_count`` is a measurement and how much is that default.
    CLOSED_STATES = frozenset({"SUBMITTED", "AWARDED", "REJECTED", "WITHDRAWN", "CLOSED"})

    # The objection above is correct about naive matching and wrong about the
    # remedy: declining entirely left 5 of 66 classified, so 92% of "open" was
    # the default wearing the name of a measurement. Precedence resolves the
    # counterexample it raises. A status that says BOTH "submitted" and
    # "waiting reply" is waiting — so live markers are tested FIRST and win.
    # Only then are terminal markers considered. Anything matching neither stays
    # unclassified, which remains a real answer rather than a synonym for open.
    _LIVE_MARKERS = ("WAITING", "AWAITING", "_REQUIRED", "REQUESTED", "READY",
                     "BLOCKED", "GATED", "NOT_SUBMITTED", "NOT_SENT", "NOT_LIVE",
                     "UNCONFIRMED", "RESUBMITTED", "APPROVAL_REQUIRED")
    _TERMINAL_MARKERS = ("DEADLINE_PASSED", "CALL_CLOSED", "NO_SAFE_SUBMISSION",
                         "NO_APPLICATION", "WILL_NOT_PARTICIPATE", "NOT_ELIGIBLE",
                         "NO_DIRECT_FORM_ROUTE_FOUND")

    @property
    def lifecycle(self) -> str:
        """``live`` | ``closed`` | ``unclassified`` — measured, never guessed."""
        s = self.status.strip().upper()
        if not s:
            return "unclassified"
        if s in self.CLOSED_STATES:
            return "closed"
        # Live wins over terminal: SUBMITTED_DECK…WAITING_REPLY is waiting.
        if any(m in s for m in self._LIVE_MARKERS):
            return "live"
        if any(m in s for m in self._TERMINAL_MARKERS):
            return "closed"
        return "unclassified"

    @property
    def status_recognised(self) -> bool:
        """True only when the status is one this code can actually classify."""
        return self.lifecycle != "unclassified"

    @property
    def is_open(self) -> bool:
        """Could this still need action? Deliberately conservative.

        Unclassified counts as open: hiding a live deadline costs more than
        carrying a dead record. Use :attr:`lifecycle` for what was measured.
        """
        return self.lifecycle != "closed"

    def days_remaining(self, now: datetime) -> float | None:
        """Days until the deadline, negative if passed. None when unknown."""
        if self.deadline is None:
            return None
        return (self.deadline - now).total_seconds() / 86400.0

    @classmethod
    def from_ledger(cls, raw: Any) -> "Application | None":
        """Build from a ledger entry, tolerating the list's mixed shapes.

        ``active_applications`` contains both dicts and bare strings; a string
        carries no application data, so it yields None rather than a husk with
        invented fields.
        """
        if not isinstance(raw, dict):
            return None
        app_id = str(raw.get("id") or "").strip()
        if not app_id:
            return None
        # A money figure is either a real, finite number or absent. ``bool`` is
        # excluded before the cast because ``float(True)`` is 1.0 — a JSON
        # ``true`` would otherwise be reported as a £1 request. NaN and ±inf are
        # rejected for the same reason: they are not amounts, and they cannot
        # even survive ``json.dumps`` as valid JSON.
        raw_amount = raw.get("amount_requested")
        amount: float | None = None
        if raw_amount is not None and not isinstance(raw_amount, bool):
            try:
                parsed = float(raw_amount)
            except (TypeError, ValueError):
                parsed = None
            if parsed is not None and math.isfinite(parsed):
                amount = parsed
        docs = raw.get("documents")
        return cls(
            id=app_id,
            name=str(raw.get("name") or ""),
            funder=str(raw.get("funder") or ""),
            status=str(raw.get("status") or ""),
            opportunity_id=str(raw.get("opportunity_id") or ""),
            amount_requested=amount,
            currency=str(raw.get("currency") or ""),
            deadline=parse_dt(raw.get("deadline")),
            submitted_at=parse_dt(raw.get("submitted_at")),
            documents=tuple(d for d in docs if isinstance(d, str)) if isinstance(docs, list) else (),
            notes=str(raw.get("notes") or ""),
            last_checked=parse_dt(raw.get("last_continuous_monitor_checked_at")),
        )

    def to_dict(self, now: datetime | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "funder": self.funder,
            "status": self.status,
            "opportunity_id": self.opportunity_id,
            "amount_requested": self.amount_requested,
            "currency": self.currency,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "document_count": len(self.documents),
            "is_open": self.is_open,
        }
        if now is not None:
            out["days_remaining"] = _round(self.days_remaining(now), 2)
        return out


@dataclass
class DeadlineAlert:
    """An open application whose deadline is close enough to matter."""

    application_id: str
    name: str
    funder: str
    days_remaining: float
    deadline: datetime
    severity: str  # overdue | critical | urgent | approaching

    def to_dict(self) -> dict[str, Any]:
        return {
            "application_id": self.application_id,
            "name": self.name,
            "funder": self.funder,
            "days_remaining": _round(self.days_remaining, 2),
            "deadline": self.deadline.isoformat(),
            "severity": self.severity,
        }


@dataclass
class PipelineState:
    """A reconciled read of the whole grant pipeline at one moment."""

    available: bool
    generated_at: datetime
    applications: tuple[Application, ...] = ()
    alerts: tuple[DeadlineAlert, ...] = ()
    artifact_count: int = 0
    blocker: str | None = None
    ledger_path: str = ""
    # Ledger entries that carried no application data (bare strings, non-dicts,
    # blank ids) and so produced no Application. Reported rather than dropped:
    # the live ledger's ``active_applications`` holds 68 entries but only 66
    # parse, and an application_count of 66 presented alone would quietly
    # understate the pipeline.
    skipped_entries: int = 0

    @property
    def open_count(self) -> int:
        """Applications not in a *recognised* terminal state.

        Read with :attr:`unrecognised_status_count`: on the live ledger only 5
        of 66 statuses are classifiable, so most of this count is the
        unknown-means-still-open default rather than a measurement.
        """
        return sum(1 for a in self.applications if a.is_open)

    @property
    def unrecognised_status_count(self) -> int:
        """How many applications carry a status this code cannot classify."""
        return sum(1 for a in self.applications if not a.status_recognised)

    @property
    def urgency(self) -> float | None:
        """0..1 pressure from the nearest open deadline. None if none known.

        Not a fabricated score: it is a pure function of a real deadline. With
        no dated open application there is no urgency to report, so it is None
        rather than 0 — absent and calm are different things.

        Two properties of the curve worth stating plainly, because they are
        choices rather than facts about the world:

        * The 30-day normalisation is a **horizon, not a measurement**. Anything
          further out than 30 days clamps to 0.0, so a deadline 31 days away and
          one 1,000 days away are indistinguishable here. That matches the
          alerting bands (``approaching`` also ends at 30 days) and keeps the
          scale linear where it is acted on, but 0.0 means "beyond the horizon",
          not "no deadline" — that case is None.
        * The minimum is over *every* open dated application, so a single stale
          application that was never closed pins urgency at 1.0 permanently and
          masks the rest of the pipeline. That is deliberate — an overdue open
          obligation is a real cost and should not decay quietly — but it means
          urgency 1.0 says "something is overdue", not "something is imminent".
          :attr:`alerts` carries the per-application detail.
        """
        soonest = min(
            (a.days_remaining(self.generated_at) for a in self.applications
             if a.is_open and a.deadline is not None),
            default=None,
        )
        if soonest is None:
            return None
        if soonest <= 0:
            return 1.0
        # 30 days out ≈ 0, on the day ≈ 1.
        return max(0.0, min(1.0, 1.0 - (soonest / 30.0)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "generated_at": self.generated_at.isoformat(),
            "ledger_path": self.ledger_path,
            "blocker": self.blocker,
            "artifact_count": self.artifact_count,
            "application_count": len(self.applications),
            "skipped_entries": self.skipped_entries,
            "open_count": self.open_count,
            "unrecognised_status_count": self.unrecognised_status_count,
            "urgency": _round(self.urgency),
            "alerts": [a.to_dict() for a in self.alerts],
        }


@dataclass(frozen=True)
class Opportunity:
    """A funding call the scout found, with the route it came down.

    ``source`` is not decoration. Two of the three retrieval paths available to
    this repo are unreliable in different ways — ``web_search`` silently
    degrades to a hardcoded catalogue of developer-documentation URLs, and a
    caller-supplied record is only as good as the caller — so every downstream
    reader needs to know which one produced this row before it weighs it. An
    Opportunity with no source cannot be constructed at all; see
    :meth:`__post_init__`.

    ``text`` is the retrieved call text and is the only thing
    :func:`aureon.grants.scout.score_fit` will score against. It is ``""`` when
    retrieval did not happen or failed, and in that case ``retrieval_error``
    says why. The pair exists precisely so that "we never read this call" stays
    distinguishable from "we read it and it said nothing" — the first is a
    blocker, the second is a measurement of zero.
    """

    id: str
    title: str
    funder: str
    url: str
    deadline: datetime | None
    max_award: float | None
    currency: str
    source: str
    discovered_at: datetime
    text: str = ""
    retrieval_error: str | None = None
    http_status: int | None = None

    def __post_init__(self) -> None:
        # Provenance is mandatory and enforced at construction rather than
        # checked by convention downstream: an unsourced Opportunity that
        # reaches a report is indistinguishable from a sourced one, and by then
        # the information needed to tell them apart is gone.
        if not str(self.source or "").strip():
            raise ValueError("Opportunity.source is mandatory — record WHERE this came from")
        if not str(self.id or "").strip():
            raise ValueError("Opportunity.id is mandatory")

    @property
    def retrieved(self) -> bool:
        """True only when real call text was read back."""
        return bool(self.text.strip())

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "funder": self.funder,
            "url": self.url,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "max_award": self.max_award,
            "currency": self.currency,
            "source": self.source,
            "discovered_at": self.discovered_at.isoformat(),
            "retrieved": self.retrieved,
            "text_chars": len(self.text),
            "retrieval_error": self.retrieval_error,
            "http_status": self.http_status,
        }


@dataclass(frozen=True)
class CapabilityProfile:
    """What this company can credibly claim, read from its own documents.

    Every term here was lifted from a file on disk at runtime. Nothing about
    the company — not a name, a sector, a technology or a positioning phrase —
    is written into the source of this package, so pointing the reader at an
    empty directory yields an empty profile with a blocker, not the answer it
    gave last time. That is the same contract :mod:`aureon.identity` holds.

    ``compliance_blockers`` and ``claim_discipline`` carry verbatim operating
    constraints found in the reconciliation report. They are reproduced exactly
    and never paraphrased, because a paraphrased constraint is a new constraint.
    """

    terms: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    compliance_blockers: tuple[str, ...] = ()
    thesis: str | None = None
    # The claim-discipline rule, verbatim. Read here rather than in the consumer
    # because this is the organ that already opens the reconciliation report;
    # opening it a second time elsewhere would make two answers to one question.
    claim_discipline: str | None = None
    blocker: str | None = None

    @property
    def available(self) -> bool:
        return bool(self.terms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "term_count": len(self.terms),
            "terms": list(self.terms),
            "sources": list(self.sources),
            "thesis": self.thesis,
            "claim_discipline": self.claim_discipline,
            "compliance_blockers": list(self.compliance_blockers),
            "blocker": self.blocker,
        }


@dataclass(frozen=True)
class FitScore:
    """How much of the company's capability the call text actually asks for.

    ``score`` is a real ratio with a stated denominator: the fraction of
    :attr:`CapabilityProfile.terms` that appear in the retrieved call text. It
    is a *measurement of overlap*, and it is worth being blunt about the three
    things it is therefore not:

    * It is not a probability of winning, and nothing here estimates one.
    * It is asymmetric. A 40-page call mentions more of any vocabulary than a
      one-paragraph call does, so scores are comparable between calls of
      similar length and much less so across them.
    * It is lexical. "Evidence" in a funder's boilerplate and "evidence" in
      this company's thesis are the same token to this code and different
      things in the world. :attr:`matched_terms` is published so a reader can
      check that for themselves rather than trust the number.

    ``score`` is ``None`` whenever the overlap could not be measured — an
    unretrieved call, an empty profile — and :attr:`blocker` then says which.
    None is not zero: zero means the call text was read and shared nothing with
    the profile, which is a finding. None means there is nothing to report.
    """

    score: float | None
    matched_terms: tuple[str, ...] = ()
    missing_requirements: tuple[str, ...] = ()
    blocker: str | None = None
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": _round(self.score),
            "matched_terms": list(self.matched_terms),
            "missing_requirements": list(self.missing_requirements),
            "blocker": self.blocker,
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class OpportunityAssessment:
    """A scored opportunity and the switchboard verdicts on pursuing it.

    The two halves are deliberately kept side by side and un-merged. The fit
    score is evidence; the verdicts are the decision; collapsing them into a
    single "pursue: yes/no" would hide which of the two produced the answer.
    """

    opportunity: Opportunity
    fit: FitScore
    verdicts: tuple[Any, ...] = ()

    @property
    def decision(self) -> str | None:
        """The last gate's decision, or None if the chain never ran."""
        return self.verdicts[-1].decision if self.verdicts else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity": self.opportunity.to_dict(),
            "fit": self.fit.to_dict(),
            "decision": self.decision,
            "verdicts": [v.to_dict() for v in self.verdicts],
        }


__all__ = [
    "Application",
    "CapabilityProfile",
    "DeadlineAlert",
    "FitScore",
    "Opportunity",
    "OpportunityAssessment",
    "PipelineState",
    "parse_dt",
]
