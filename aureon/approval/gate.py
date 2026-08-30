"""The loop that resolves a HOLD — Sero asks by email, waits, and reads the answer.

``aureon.gates.switchboard`` ends the chain at ``submit`` with a HOLD, because no
automatic executor exists anywhere in this repository for a submission, a filing
or a payment. That HOLD is not a bug to be argued round; it is the absence of a
hand. This module is the only thing that puts a hand there, and the hand is
Gary's.

Gary's design, in his words: *"the only thing this system needs Gary for is send
a message — at the last approval gate, send him a summary via email and say
'Gary am I ok to go ahead', and Gary replies to the email and says yes or no, and
that is the final approval gate."*

So the loop is::

    resolve_hold(action, dossier=...)   run the gates; if they HOLD, ask
      └─ compose_request  → the question, carrying its own grounding
      └─ store.save       → state/approvals/<token>.json, O_EXCL
      └─ send_approval_request → one address, resolved from config
      └─ publish approval.requested

    poll_approvals(connector)           read the mailbox, resolve what he said
      └─ store.expire_overdue   → publish approval.expired
      └─ check_for_replies      → APPROVED / DECLINED / UNCLEAR / IGNORED
      └─ store.resolve          → single-use, expiry-bound, on disk
      └─ publish approval.granted / .declined / .unclear / .ignored
      └─ publish_subfield("approval", …) → waiting registers in the HNC field

    approval_state(token)               what the ledger says, right now

This module assembles; it does not re-implement. The six non-negotiable
properties are enforced one layer down, in the places a caller cannot go around
— :mod:`aureon.approval.config` (owner-locked address),
:mod:`aureon.approval.schemas` (token-bound verdicts, unforgeable coherence),
:mod:`aureon.approval.store` (single use, expiry) and
:mod:`aureon.approval.reply` (sender verification, explicit intent). Nothing
here can loosen any of them, and this file adds no second path to any of them.

THE CONTRACT, EXPLICITLY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A HOLD from :func:`aureon.gates.switchboard.run_chain` is resolved **only** by an
APPROVED token for **that exact action**. Not by a token for a similar action,
not by a token that was APPROVED and has since been superseded, not by a chain
that would now come out differently, and never by silence.

Executing code must therefore:

1. call :func:`hold_resolved` (or :func:`approval_state`) **immediately** before
   the irreversible step, in the same breath as taking it; and
2. **never cache the answer.** A state read at the top of a function and acted on
   at the bottom is a stale read: between the two, a deadline can pass, an
   operator can decline, and a token can be spent by another worker. The ledger
   is the authority, the clock is part of the ledger, and the only safe distance
   between the check and the act is zero.

There is no ``execute`` in this package, and that is deliberate: approval is
recorded here, and the irreversible move stays a separate, deliberate act
elsewhere. An APPROVED token authorises a person or a narrowly-scoped executor to
proceed; it does not itself proceed.

WAITING IS A REAL STATE OF THE ORGANISM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sero blocked on Gary is not a neutral pause, so :func:`publish_pressure` reports
it as a sub-field: an approval ageing towards its deadline lowers this organ's
local life score, which raises the whole-body divergence in
:func:`~aureon.core.hnc_field.blend_field` and makes the switchboard more
cautious everywhere else. That is the truth of the situation — a body waiting on
a decision it cannot take is less coherent than one that is not.

It publishes **only** when something is actually open, exactly as
``grants.daemon._publish_field`` declines to publish an urgency it has not
measured. Publishing "all calm" while nothing is pending would be a fabricated
reading dressed as a measurement, and it would drag the organism's mean coherence
upward for free.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from aureon.approval.compose import DEFAULT_TTL_HOURS, compose_request
from aureon.approval.config import owner_address
from aureon.approval.notify import send_approval_request
from aureon.approval.reply import check_for_replies
from aureon.approval.schemas import ApprovalRequest, ApprovalState
from aureon.approval.store import expire_overdue, load, open_requests, resolve, save

LOG = logging.getLogger("aureon.approval.gate")

# ── the bus vocabulary ───────────────────────────────────────────────────────
# One topic per thing that actually happened. ``unclear`` and ``ignored`` are
# published as well as the resolving three, because "he replied and I could not
# read it" and "a stranger replied" are facts the organism needs to be able to
# see. Neither is approval, and neither closes a request.
TOPIC_REQUESTED = "approval.requested"
TOPIC_GRANTED = "approval.granted"
TOPIC_DECLINED = "approval.declined"
TOPIC_EXPIRED = "approval.expired"
TOPIC_UNCLEAR = "approval.unclear"
TOPIC_IGNORED = "approval.ignored"
#: Published when Sero refuses to ask at all — no grounding, or nobody to ask.
TOPIC_WITHHELD = "approval.withheld"

BUS_SOURCE = "approval_gate"

#: The sub-field name this organ contributes to the shared HNC field.
SUBFIELD_SOURCE = "approval"

#: How long an ask stays answerable, in hours. Overridable per deployment;
#: :data:`aureon.approval.compose.DEFAULT_TTL_HOURS` (72) when unset or unusable.
TTL_VAR = "AUREON_APPROVAL_TTL_HOURS"


def _now() -> datetime:
    """The clock, in one place, so tests can hold it still.

    Every timestamp this module hands to ``compose``, ``store`` and ``notify``
    comes from here. Expiry is decided by comparing a stored deadline against
    this value — there is no background sweep that a stopped daemon could make
    stale, and no cached "is it still live" flag to go out of date.
    """
    return datetime.now(UTC)


def ttl_hours() -> float:
    """The configured answering window. Falls back rather than failing.

    A value that is not a positive number is a misconfiguration, not an
    instruction to make the window infinite, so it is logged and the default
    stands. There is no way to configure a request that never expires.
    """
    raw = str(os.environ.get(TTL_VAR, "") or "").strip()
    if not raw:
        return float(DEFAULT_TTL_HOURS)
    try:
        hours = float(raw)
    except (TypeError, ValueError):
        LOG.warning("%s=%r is not a number — using %sh", TTL_VAR, raw, DEFAULT_TTL_HOURS)
        return float(DEFAULT_TTL_HOURS)
    if hours <= 0:
        LOG.warning("%s must be positive — using %sh", TTL_VAR, DEFAULT_TTL_HOURS)
        return float(DEFAULT_TTL_HOURS)
    return hours


# ── asking ───────────────────────────────────────────────────────────────────


def request_approval(
    action: str,
    *,
    application_id: str | None = None,
    dossier: Any = None,
    bus: Any = None,
) -> ApprovalRequest | None:
    """Ask Gary, once, about one action. Compose, persist, notify, announce.

    Returns the persisted request, or ``None`` when the ask did not happen at
    all. There are exactly three reasons for ``None``, and each is announced on
    :data:`TOPIC_WITHHELD` and logged:

    - **no grounding.** :func:`~aureon.approval.compose.compose_request` refuses
      to build a request whose reading of the organism is entirely unreadable.
      Sero does not ask for authority she cannot justify, so there is nothing to
      send.
    - **nobody to ask.** With no owner address configured there is no address to
      send to *and* — because :func:`~aureon.approval.config.is_owner` then
      matches nobody — no reply could ever approve it. Asking would be theatre.
    - **the ledger refused it.** A token collision or an unwritable ledger; an
      approval that cannot be recorded must not be requested, because the reply
      would have nothing to resolve against.

    A request that is persisted but **could not be delivered** is returned, with
    ``sent: false`` and the blocker on :data:`TOPIC_REQUESTED`. That is the
    honest outcome: the token is live but unanswerable, so it will expire and
    nothing will have been authorised. Note the asymmetry that makes this safe —
    a failure anywhere in this function can only ever result in *less* authority,
    never more.

    Note also what is *not* a parameter: there is no recipient. The address is
    resolved from configuration by the delivery layer and is never accepted from
    a caller — see :mod:`aureon.approval.config`.
    """
    now = _now()

    owner = owner_address()
    if owner is None:
        LOG.error(
            "NOT asking about %s: no approval address configured. With nobody configured, "
            "no reply can be verified, so no reply could approve it either.", action)
        _publish(bus, TOPIC_WITHHELD, {"action": action, "application_id": application_id,
                                       "reason": "no approval address configured"})
        return None

    request = compose_request(
        action, application_id=application_id, dossier=dossier, bus=bus,
        ttl_hours=ttl_hours(), now=now,
    )
    if request is None:
        # compose_request has already logged the blockers that made it refuse.
        _publish(bus, TOPIC_WITHHELD, {"action": action, "application_id": application_id,
                                       "reason": "no grounding could be read"})
        return None

    try:
        save(request)
    except Exception as exc:  # noqa: BLE001 — an unrecordable ask is not made
        LOG.error("NOT asking about %s: the approval ledger refused the request (%s)",
                  action, type(exc).__name__)
        _publish(bus, TOPIC_WITHHELD, {"action": action, "application_id": application_id,
                                       "token": request.token,
                                       "reason": f"ledger refused: {type(exc).__name__}"})
        return None

    result = send_approval_request(request, now=now)
    if not result.sent:
        LOG.warning(
            "approval %s is recorded but was NOT delivered: %s. The token is live and "
            "unanswerable — it will expire and authorise nothing.",
            request.token[:8], result.blocker)

    payload = request.to_dict()
    payload["notified"] = result.sent
    payload["notify_blocker"] = result.blocker
    _publish(bus, TOPIC_REQUESTED, payload)
    publish_pressure(bus)
    return request


def resolve_hold(
    action: str,
    *,
    application_id: str | None = None,
    dossier: Any = None,
    bus: Any = None,
) -> ApprovalRequest | None:
    """Ask Gary when the step is one no executor exists for. The switchboard's way in.

    This is the resolving step for a HOLD. Returns ``None`` when there is **no
    hold to resolve**, which is not a failure: the action was never a person's to
    take, and the caller should simply proceed on the chain's own verdict. It also
    returns ``None`` for every reason :func:`request_approval` does.

    **Why the chain's terminal decision is not the test.** It is tempting to ask
    "did ``run_chain`` return HOLD?" — and it is wrong in both directions:

    - ``DEFAULT_CHAIN``'s last gate is ``Gate("submit", …, requires_human=True)``,
      so *every* completed pass of the chain ends in HOLD whatever it was asked
      about. Reading that as "ask Gary" would put a draft summary in front of him
      and train him to rubber-stamp, which is how a real gate decays into a
      formality. The most dangerous approval loop is not one that asks too
      rarely; it is one that asks so often the answer stops being read.
    - And the trap :mod:`aureon.grants.dossier` documents runs the other way:
      ``switchboard.evaluate`` tests *blindness* before it tests *hands*, so a
      blind organism returns REDO at the first gate and never reaches the
      human-held branch at all. A caller reading only the terminal decision would
      see "iterate and come back" where the truth is "this was never yours".

    :func:`~aureon.gates.switchboard.is_human_held` is the switchboard's own
    statement about which hands exist — matched per word, so ``"Submit "``,
    ``"submit_application"`` and ``"wire-transfer"`` are all held — and it is
    unaffected by both failure modes. The chain still runs, inside
    :func:`~aureon.approval.compose.read_grounding`, and its verdicts travel to
    Gary in the request; they are evidence for his decision, not the trigger for
    asking.
    """
    try:
        from aureon.gates.switchboard import is_human_held

        held = is_human_held(action)
    except Exception:  # noqa: BLE001 — an unreadable vocabulary is not permission
        # Fail towards asking. Asking is inert — it records a question and waits —
        # whereas returning None tells the caller to proceed on the chain alone.
        LOG.warning("could not establish whether %s is human-held — asking anyway", action,
                    exc_info=True)
        held = True

    if not held:
        LOG.info("no hold to resolve for %s — no irreversible step is named in it", action)
        return None

    return request_approval(action, application_id=application_id, dossier=dossier, bus=bus)


# ── reading the answer ───────────────────────────────────────────────────────


def poll_approvals(connector: Any, *, bus: Any = None) -> list[ApprovalRequest]:
    """Read the owner's replies and resolve what he said. Returns what changed.

    ``connector`` is a read-only :class:`~aureon.connectors.gmail.GmailConnector`
    (or anything with its ``search_threads`` / ``read_thread`` pair). It has no
    send method, no label method and no delete method, so this sweep is
    structurally incapable of touching the mailbox it reads.

    The order matters and is deliberate:

    1. **Expire first.** Anything past its deadline is stamped EXPIRED before a
       single reply is looked at, so a late "yes" arrives to find its request
       already closed. ``store.resolve`` refuses late answers on its own too —
       this is the belt as well as the braces.
    2. **Then read**, for the tokens that are still open, and resolve each
       through the ledger.

    Returns the requests whose state this call changed — granted, declined or
    expired. An empty list means nothing arrived, which leaves every request
    pending: there is no path in this function from absence to approval.

    UNCLEAR and IGNORED are announced but carry **no token**, because
    :class:`~aureon.approval.reply.ReplyVerdict` forbids a non-resolving verdict
    from naming one. An answer that cannot say what it answered is not allowed to
    point at a request, so those topics report the reason and the sender and
    nothing that could be mistaken for a decision.
    """
    now = _now()
    changed: dict[str, ApprovalRequest] = {}

    # 1. the clock closes what the owner did not answer in time.
    for token in expire_overdue(now=now):
        request = load(token)
        if request is not None:
            changed[token] = request
            _publish(bus, TOPIC_EXPIRED, _event(request, "deadline passed unanswered"))
            LOG.warning("approval %s expired unanswered (%s)", token[:8], request.action)

    open_now = open_requests()
    if not open_now:
        publish_pressure(bus)
        return list(changed.values())

    # 2. what did he say? ``owner_address=None`` resolves the one configured
    #    address inside the reply layer — the daemon path, with no address
    #    travelling through this function.
    verdicts = check_for_replies(connector, owner_address=None,
                                 tokens=[r.token for r in open_now])

    for verdict in verdicts:
        if not verdict.resolves:
            topic = TOPIC_IGNORED if verdict.state is ApprovalState.IGNORED else TOPIC_UNCLEAR
            _publish(bus, topic, verdict.to_dict())
            LOG.info("approval reply recorded as %s: %s", verdict.state, verdict.reason)
            continue

        token = verdict.matched_token
        if not token:  # unreachable: ReplyVerdict.__post_init__ forbids it.
            continue

        evidence = f"reply {verdict.message_id or '?'} from the owner: {verdict.reason}"
        recorded = resolve(token, verdict.state, evidence, now=now)
        after = load(token)
        if after is None:
            LOG.warning("approval %s resolved but could not be read back", token[:8])
            continue

        if recorded:
            changed[token] = after
            topic = TOPIC_GRANTED if after.state is ApprovalState.APPROVED else TOPIC_DECLINED
            _publish(bus, topic, _event(after, verdict.reason, verdict=verdict))
            LOG.info("approval %s: %s by the owner", token[:8], after.state)
        elif token not in changed:
            # The ledger refused: already spent, or the deadline had passed and
            # ``resolve`` stamped it EXPIRED on the way out. Either way nothing
            # was authorised, and the refusal is announced rather than silent.
            if after.state is ApprovalState.EXPIRED:
                changed[token] = after
                _publish(bus, TOPIC_EXPIRED, _event(after, "a late answer was refused",
                                                    verdict=verdict))
            LOG.warning("approval %s: reply refused — request is %s", token[:8], after.state)

    publish_pressure(bus)
    return list(changed.values())


def approval_state(token: str) -> ApprovalState:
    """What the ledger says about one token, as of this instant.

    Call this immediately before acting, every time, and do not keep the answer —
    see the contract in the module docstring. The clock is part of the answer: a
    request whose deadline has passed reads EXPIRED here whether or not any sweep
    has run, so a stopped poller cannot leave a stale PENDING looking live.

    An unknown, malformed or unreadable token is
    :attr:`~aureon.approval.schemas.ApprovalState.PENDING`-free and cannot be
    mistaken for permission: it returns ``EXPIRED``, the state that authorises
    nothing. Absence never reads as approval.
    """
    request = load(token)
    if request is None:
        # Fail closed. A token nobody can find is not an approval, and saying
        # "EXPIRED" rather than inventing a PENDING keeps every caller's
        # ``is APPROVED`` test correct without a special case.
        LOG.debug("approval state asked for an unknown token")
        return ApprovalState.EXPIRED
    if request.state in {ApprovalState.APPROVED, ApprovalState.DECLINED, ApprovalState.EXPIRED}:
        return request.state
    if request.is_expired(_now()):
        return ApprovalState.EXPIRED
    return request.state


def hold_resolved(action: str, token: str) -> bool:
    """True only when ``token`` is an APPROVED approval **for this exact action**.

    The one question executing code should ask, and the whole of the contract in
    a single call: a HOLD is resolved only by an APPROVED token for that exact
    action. Both halves matter —

    - **APPROVED**, read now, through :func:`approval_state`, so an expired or
      declined token cannot pass; and
    - **that exact action**, compared verbatim against what the request was
      composed for, so an approval to ``submit_application`` cannot be spent on
      ``pay_invoice``. Token scope is not just "some approval exists"; it is
      "this approval was for this".

    Never cache this. It is cheap, it is a file read, and its answer changes with
    the clock.
    """
    wanted = str(action or "").strip()
    if not wanted or not token:
        return False
    request = load(token)
    if request is None:
        return False
    if request.action != wanted:
        LOG.warning("approval %s was for %r, not %r — refusing to clear that hold",
                    request.token[:8], request.action, wanted)
        return False
    return approval_state(token) is ApprovalState.APPROVED


# ── waiting, as a reading of the organism ────────────────────────────────────


@dataclass(frozen=True)
class WaitingPressure:
    """How hard this organ is blocked on a human, as a real measurement.

    ``pressure`` is the deepest share of any open request's answering window that
    has been consumed: 0.0 the moment Sero asks, 1.0 at the deadline. It is
    derived from two stored timestamps and the clock — nothing here is estimated.

    ``symbolic_life_score`` is ``1.0 - pressure``, the shape
    ``grants.daemon._publish_field`` uses for the same reason: an unmet
    obligation is a real cost to the organism, not a neutral fact. ``None`` when
    nothing is open, and a ``None`` reading is not published.
    """

    open_count: int = 0
    oldest_age_s: float | None = None
    pressure: float | None = None
    #: This organ measures no coherence of its own, and says so rather than
    #: contributing a number it did not measure to the field's Γ mean.
    coherence_gamma: None = None

    @property
    def symbolic_life_score(self) -> float | None:
        return None if self.pressure is None else 1.0 - self.pressure

    @property
    def consciousness_level(self) -> str | None:
        return "waiting_on_owner" if self.open_count else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "open_count": self.open_count,
            "oldest_age_s": round(self.oldest_age_s, 1) if self.oldest_age_s is not None else None,
            "pressure": round(self.pressure, 4) if self.pressure is not None else None,
            "symbolic_life_score": (round(self.symbolic_life_score, 4)
                                    if self.symbolic_life_score is not None else None),
            "consciousness_level": self.consciousness_level,
        }


def waiting_pressure() -> WaitingPressure:
    """Measure how long Sero has been waiting on Gary. Never raises."""
    try:
        requests = open_requests()
    except Exception:  # noqa: BLE001 — an unreadable ledger is not zero pressure
        LOG.debug("waiting pressure could not be read", exc_info=True)
        return WaitingPressure()
    if not requests:
        return WaitingPressure()

    now = _now()
    deepest: float | None = None
    oldest: float | None = None
    for request in requests:
        age = (now - request.created_at).total_seconds()
        window = (request.expires_at - request.created_at).total_seconds()
        if oldest is None or age > oldest:
            oldest = age
        if window > 0:
            share = max(0.0, min(1.0, age / window))
            if deepest is None or share > deepest:
                deepest = share
    return WaitingPressure(open_count=len(requests), oldest_age_s=oldest, pressure=deepest)


def publish_pressure(bus: Any = None) -> WaitingPressure:
    """Contribute the waiting to the shared HNC field, when there is any.

    Publishes nothing when nothing is open — see the module docstring. Returns
    the reading either way so a caller can log it. Never raises: visibility is
    best-effort, and a field that could not be published is not a reason to stop
    waiting for Gary.
    """
    pressure = waiting_pressure()
    if pressure.symbolic_life_score is None:
        return pressure
    try:
        from aureon.core.hnc_field import publish_subfield

        publish_subfield(SUBFIELD_SOURCE, pressure, bus=bus)
    except Exception:  # noqa: BLE001
        LOG.debug("approval sub-field publish skipped", exc_info=True)
    return pressure


# ── plumbing ─────────────────────────────────────────────────────────────────


def _event(request: ApprovalRequest, reason: str, *, verdict: Any = None) -> dict[str, Any]:
    """One bus payload describing what happened to a request."""
    payload = request.to_dict()
    payload["reason"] = reason
    if verdict is not None:
        payload["sender"] = getattr(verdict, "sender", None)
        payload["message_id"] = getattr(verdict, "message_id", None)
        payload["intent_phrase"] = getattr(verdict, "intent_phrase", None)
    return payload


def _publish(bus: Any, topic: str, payload: dict[str, Any]) -> None:
    """Put one approval event on the thought bus. Guarded; never fatal.

    A bus that will not take a thought must not be able to stop an approval from
    being recorded — the ledger on disk is the authority, and this is the
    organism noticing.
    """
    if bus is None:
        return
    try:
        from aureon.core.aureon_thought_bus import Thought

        bus.publish(Thought(source=BUS_SOURCE, topic=topic, payload=dict(payload)))
    except Exception:  # noqa: BLE001
        LOG.debug("approval publish skipped (%s)", topic, exc_info=True)


__all__ = [
    "BUS_SOURCE",
    "SUBFIELD_SOURCE",
    "TOPIC_DECLINED",
    "TOPIC_EXPIRED",
    "TOPIC_GRANTED",
    "TOPIC_IGNORED",
    "TOPIC_REQUESTED",
    "TOPIC_UNCLEAR",
    "TOPIC_WITHHELD",
    "TTL_VAR",
    "WaitingPressure",
    "approval_state",
    "hold_resolved",
    "poll_approvals",
    "publish_pressure",
    "request_approval",
    "resolve_hold",
    "ttl_hours",
    "waiting_pressure",
]
