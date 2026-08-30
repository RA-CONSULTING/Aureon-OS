"""The shape of a question the Queen asks and an answer she is allowed to trust.

Gary's design, in his words: *"the only thing this system needs Gary for is send
a message — at the last approval gate, send him a summary via email and say
'Gary am I ok to go ahead', and Gary replies to the email and says yes or no, and
that is the final approval gate."*

His standing rule, from his own War Room sheet: *"No external submission, legal
representation, filing, payment, or email send should happen without Gary
approval."* The request is how that rule is kept, not an exception to it —
``switchboard.evaluate`` returns HOLD at the ``submit`` gate because no automatic
executor exists, and this package is the only thing that can turn that HOLD into
a hand: Gary's.

Two invariants live here rather than in a caller, because a caller can forget:

**A request with nothing to show cannot be constructed.** ``__post_init__``
refuses an :class:`ApprovalRequest` whose :class:`GroundingSnapshot` read
nothing at all. Sero does not get to ask for authority she cannot justify —
there is no code path that builds the object, so there is nothing to send.

**Coherence is derived, never asserted.** ``is_coherent`` is recomputed from
``divergence`` on every construction, including deserialisation. A record on
disk that claims coherence while carrying a divergence of 0.8 is read back as
incoherent; the flag cannot be forged by editing the ledger.

Every numeric field is a real reading or ``None``. Nothing here is estimated,
defaulted into existence, or inferred from silence.
"""

from __future__ import annotations

import re
import secrets
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

# The switchboard's own caution threshold (``Gate.max_divergence``, which in
# turn matches ``grounded_action._DIVERGENCE_CAUTION``). A body this divided is
# forced to REDO there; here it is allowed to ask, but it must say so.
MAX_DIVERGENCE = 0.35
# Below this share of real inputs the Auris panel is voting on constants — see
# ``aureon.gates.panel``, where four of nine nodes cannot tell an unmeasured
# slice from a measured zero.
MIN_EVIDENCE = 0.5

# 32 bytes of ``secrets`` entropy -> 43 urlsafe characters. The token is the
# whole of property 2: a reply approves exactly the request whose token it
# carries, so it has to be unguessable and it has to be the only thing that
# binds an answer to a question.
TOKEN_BYTES = 32
# Also the filename guard in ``store``: a token arrives from an inbound email,
# and a "token" of ``../../pipeline`` must not be able to steer a write.
TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{22,128}$")


def new_token() -> str:
    """A fresh, unguessable approval token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def is_token(value: Any) -> bool:
    """True when ``value`` is shaped like an approval token and nothing else."""
    return isinstance(value, str) and TOKEN_RE.match(value) is not None


def parse_dt(value: Any) -> datetime | None:
    """Parse an ISO stamp from a record, or return ``None``.

    Naive stamps are read as UTC so comparisons never raise. An unparseable
    value is ``None``, never "now" — a missing deadline must not silently become
    a live one.
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


class ApprovalState(StrEnum):
    """Where a request stands.

    ``PENDING`` — asked, unanswered.
    ``APPROVED`` — the owner said yes, in writing, against this token.
    ``DECLINED`` — the owner said no.
    ``EXPIRED`` — the deadline passed unanswered; an old yes cannot revive it.
    ``UNCLEAR`` — the owner replied, but not with an unambiguous answer. **Not
    approval.** The request stays open, because "I could not read your answer"
    is not the same as "you said no".
    ``IGNORED`` — someone who is not the owner replied. Recorded, never acted
    on, and it does not close the request either: a stranger must not be able to
    burn Gary's token before he answers.
    """

    # A ``StrEnum``, so a member compares equal to its own name and can be
    # written straight into a JSON record or a log line — ``f"{state}"`` prints
    # ``PENDING``, not ``ApprovalState.PENDING``. ``aureon.approval.reply`` relies
    # on that: its four aliases are these members.
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    EXPIRED = "EXPIRED"
    UNCLEAR = "UNCLEAR"
    IGNORED = "IGNORED"


# Once a request reaches one of these it is finished, for good. This frozenset
# is property 3 (single use): ``store.resolve`` refuses any token whose state is
# already in here, so a replayed reply cannot re-approve anything.
TERMINAL_STATES = frozenset({ApprovalState.APPROVED, ApprovalState.DECLINED, ApprovalState.EXPIRED})
# States a request can still be answered from. UNCLEAR and IGNORED are here on
# purpose: neither is an answer, so neither may consume the token.
OPEN_STATES = frozenset({ApprovalState.PENDING, ApprovalState.UNCLEAR, ApprovalState.IGNORED})


def coerce_state(value: Any) -> ApprovalState:
    """Read a state from an enum member or its name. Raises on anything else."""
    if isinstance(value, ApprovalState):
        return value
    if isinstance(value, str):
        try:
            return ApprovalState(value.strip().upper())
        except ValueError as exc:
            raise ValueError(f"not an approval state: {value!r}") from exc
    raise ValueError(f"not an approval state: {value!r}")


def _num(value: Any) -> float | None:
    """A float, or ``None``. Never a zero standing in for an absent reading."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class GroundingSnapshot:
    """Why Sero wants to proceed, as the organism actually read at the time.

    This is the part of the request that makes it answerable. Gary is not being
    asked to trust a claim; he is being shown the coherence Γ, how much the body
    disagrees with itself, what the nine Auris nodes concluded and on how much
    real evidence, and the gate verdicts that carried the work to the hold.
    """

    coherence: float | None = None            # Γ from the canonical HNC field
    divergence: float | None = None           # max-min spread across subfields
    panel_consensus: str | None = None        # the nine nodes' verdict
    panel_confidence: float | None = None
    panel_evidence: float | None = None       # share of panel inputs that were real
    gate_verdicts: tuple[dict[str, Any], ...] = ()
    is_coherent: bool = False                 # derived from divergence; see __post_init__
    ungrounded_nodes: tuple[str, ...] = ()    # nodes that voted on a constant
    blockers: tuple[str, ...] = ()            # what could not be read, and why

    def __post_init__(self) -> None:
        object.__setattr__(self, "coherence", _num(self.coherence))
        object.__setattr__(self, "divergence", _num(self.divergence))
        object.__setattr__(self, "panel_confidence", _num(self.panel_confidence))
        object.__setattr__(self, "panel_evidence", _num(self.panel_evidence))
        object.__setattr__(self, "gate_verdicts", tuple(self.gate_verdicts or ()))
        object.__setattr__(self, "ungrounded_nodes", tuple(self.ungrounded_nodes or ()))
        object.__setattr__(self, "blockers", tuple(self.blockers or ()))
        # Not a check — a derivation. ``is_coherent`` is whatever the divergence
        # says it is, whoever passed what.
        object.__setattr__(self, "is_coherent", not self.divided)

    @property
    def divided(self) -> bool:
        """True when the body demonstrably disagrees with itself — or never checked.

        Unmeasured is not calm. ``switchboard.evaluate`` treats an unmeasured
        divergence as division for the same reason: a body that never asked
        whether it agrees with itself has not earned the benefit of the doubt.
        """
        return self.divergence is None or self.divergence >= MAX_DIVERGENCE

    @property
    def thinly_evidenced(self) -> bool:
        """True when the panel voted mostly on defaults, or on unknown ground."""
        return self.panel_evidence is None or self.panel_evidence < MIN_EVIDENCE

    @property
    def needs_caution(self) -> bool:
        """True when this request must not look like a confident one."""
        return self.divided or self.thinly_evidenced

    @property
    def readable(self) -> bool:
        """True when at least one voice of the organism was actually heard."""
        return (self.coherence is not None
                or self.divergence is not None
                or self.panel_consensus is not None)

    def to_dict(self) -> dict[str, Any]:
        r = lambda v: round(v, 4) if isinstance(v, float) else v  # noqa: E731
        return {
            "coherence": r(self.coherence),
            "divergence": r(self.divergence),
            "panel_consensus": self.panel_consensus,
            "panel_confidence": r(self.panel_confidence),
            "panel_evidence": r(self.panel_evidence),
            "gate_verdicts": [dict(v) for v in self.gate_verdicts],
            "is_coherent": self.is_coherent,
            "ungrounded_nodes": list(self.ungrounded_nodes),
            "blockers": list(self.blockers),
        }

    @classmethod
    def from_dict(cls, raw: Any) -> GroundingSnapshot:
        if not isinstance(raw, dict):
            raise ValueError("grounding record is not an object")
        verdicts = raw.get("gate_verdicts") or []
        return cls(
            coherence=raw.get("coherence"),
            divergence=raw.get("divergence"),
            panel_consensus=raw.get("panel_consensus"),
            panel_confidence=raw.get("panel_confidence"),
            panel_evidence=raw.get("panel_evidence"),
            gate_verdicts=tuple(dict(v) for v in verdicts if isinstance(v, dict)),
            ungrounded_nodes=tuple(str(n) for n in (raw.get("ungrounded_nodes") or ())),
            blockers=tuple(str(b) for b in (raw.get("blockers") or ())),
        )


@dataclass(frozen=True)
class ApprovalRequest:
    """One question, one token, one deadline, one answer.

    Frozen on purpose: an approval is not a mutable object. State changes go
    through :meth:`with_state`, which returns a new instance, and only
    ``store.resolve`` is allowed to persist one.

    There is no recipient field, and that is the whole of property 1. The
    address this request goes to is not data the request carries and not an
    argument any function here accepts — it is resolved, once, from
    :func:`aureon.approval.config.owner_address`. A request that cannot name a
    destination cannot be re-pointed at a funder by a bug, a stale variable, or
    a line in a document.
    """

    token: str
    subject: str
    action: str
    application_id: str | None
    body_markdown: str
    created_at: datetime
    expires_at: datetime
    grounding: GroundingSnapshot
    state: ApprovalState = ApprovalState.PENDING

    def __post_init__(self) -> None:
        if not is_token(self.token):
            raise ValueError("approval token is missing or malformed")
        if not str(self.action or "").strip():
            raise ValueError("an approval request must name the action it is asking about")
        if not str(self.body_markdown or "").strip():
            raise ValueError("an approval request must carry the body Gary will read")
        created = parse_dt(self.created_at)
        expires = parse_dt(self.expires_at)
        if created is None or expires is None:
            raise ValueError("an approval request needs both a creation time and a deadline")
        if expires <= created:
            raise ValueError("an approval request's deadline must be after its creation")
        if not isinstance(self.grounding, GroundingSnapshot):
            raise ValueError("an approval request must carry a GroundingSnapshot")
        # The hard line. A request that read nothing of the organism cannot show
        # Gary why it exists, so it does not exist. See the module docstring.
        if not self.grounding.readable:
            raise ValueError(
                "no grounding could be read — Sero must not ask for approval she cannot justify")
        object.__setattr__(self, "created_at", created)
        object.__setattr__(self, "expires_at", expires)
        object.__setattr__(self, "state", coerce_state(self.state))
        object.__setattr__(self, "action", str(self.action).strip())
        object.__setattr__(self, "application_id",
                           str(self.application_id).strip() if self.application_id else None)

    @property
    def resolved(self) -> bool:
        """True when this token has already been spent. Property 3 reads this."""
        return self.state in TERMINAL_STATES

    def is_expired(self, now: datetime | None = None) -> bool:
        """True when the deadline has passed. Purely temporal — see ``store.resolve``."""
        return (now or datetime.now(UTC)) >= self.expires_at

    @property
    def approved(self) -> bool:
        """The only property in this package that means "go"."""
        return self.state is ApprovalState.APPROVED

    def with_state(self, state: Any) -> ApprovalRequest:
        """A copy in a new state. Does not persist anything."""
        return replace(self, state=coerce_state(state))

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "subject": self.subject,
            "action": self.action,
            "application_id": self.application_id,
            "body_markdown": self.body_markdown,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "grounding": self.grounding.to_dict(),
            "state": self.state.value,
        }

    @classmethod
    def from_dict(cls, raw: Any) -> ApprovalRequest:
        """Rebuild a request from a record. Raises on anything malformed.

        Fails closed by design: a record this cannot read becomes an
        unresolvable request, never a fresh PENDING one.
        """
        if not isinstance(raw, dict):
            raise ValueError("approval record is not an object")
        return cls(
            token=str(raw.get("token") or ""),
            subject=str(raw.get("subject") or ""),
            action=str(raw.get("action") or ""),
            application_id=raw.get("application_id"),
            body_markdown=str(raw.get("body_markdown") or ""),
            created_at=parse_dt(raw.get("created_at")),  # type: ignore[arg-type]
            expires_at=parse_dt(raw.get("expires_at")),  # type: ignore[arg-type]
            grounding=GroundingSnapshot.from_dict(raw.get("grounding")),
            state=coerce_state(raw.get("state") or ApprovalState.PENDING),
        )


__all__ = ["MAX_DIVERGENCE", "MIN_EVIDENCE", "OPEN_STATES", "TERMINAL_STATES", "TOKEN_RE",
           "ApprovalRequest", "ApprovalState", "GroundingSnapshot",
           "coerce_state", "is_token", "new_token", "parse_dt"]
