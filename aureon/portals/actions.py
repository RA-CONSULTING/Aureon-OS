"""The gated write path into a funder portal — and the submission it cannot make.

Gary's brief, in his words: *"this entire operation needs to be done via the
aureon repo."* Reading his Innovate UK dashboard by hand in a chat session is the
anti-pattern it replaces: not repeatable, not testable, not gated, and leaving no
trail in the repository. This module is the half of that capability that *writes*.

His standing rule, from his own War Room sheet, is the whole design:

    "No external submission, legal representation, filing, payment, or email send
    should happen without Gary approval."

So the operator's ask — *complete the applications, start new ones* — is split
where his rule splits it. Filling a draft field is legitimate automation. Pressing
**submit** is an official filing, reserved to him; and beyond his rule, the
substance of a legal declaration is not something an assistant should author into
a live filing unreviewed. This module therefore proposes field updates, and has no
way at all to submit one.

THE TWO LAYERS THAT MAKE SUBMISSION IMPOSSIBLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
**Layer 1 — absence.** There is no ``submit``, ``file`` or ``lodge`` function
here. Not a disabled one, not one behind a flag, not one that raises: *absent*.
A capability that does not exist cannot be enabled by a config change, an
exception handler, or a caller who is very sure. The same absence is repeated
downwards: :data:`ALLOWED_KINDS` holds one kind, ``field_update``, and
:meth:`PortalAction.__post_init__` refuses any other — so an action *describing*
a submission cannot even be constructed. And this module imports no HTTP client
and no browser driver: the only thing that can touch a portal is a ``writer`` the
caller injects, and there is **no default writer** — no ``_default_writer()``, no
registry lookup, no environment variable that conjures one. With nothing injected
the file cannot reach a portal at all. Grep for a default: the absence *is* the
guarantee. (The one transport anywhere in its import graph is the owner-locked
SMTP in :mod:`aureon.approval.notify`, which resolves exactly one address —
Gary's, from configuration — and accepts none from a caller.)

**Layer 2 — the switchboard's own vocabulary.**
:func:`aureon.gates.switchboard.is_human_held` already holds ``submit`` / ``file``
/ ``lodge`` / ``pay`` / ``transfer`` / ``withdraw`` / ``wire`` and their
inflections, matched per word. Two consequences are load-bearing here:

- ``evaluate`` returns HOLD at the *first* gate for any context whose action names
  a held verb, so a submit intent routed through :func:`run_chain` never advances
  and can never reach an approval request; and
- :func:`_validate` runs the same test over the caller's own ``field`` name,
  which closes the smuggling route that layer 1 alone leaves open — writing
  ``"yes"`` into a field *called* ``submit`` is a submission wearing a field
  update's clothes. It is refused, by name, with the audit line to prove it.

The import-time guard below applies the same test to :data:`ALLOWED_KINDS`, so
this module will not import at all if a future edit adds a held kind to it.

**And one refusal that is about the application rather than the verb.** When the
caller has read the funder's dashboard, an application in
:data:`aureon.portals.schemas.PORTAL_HELD_STATES` — already submitted, or ruled
ineligible — is refused outright: there is no draft to complete, and writing into
one would be an alteration to a filed application. The ground truth that prompted
this capability makes the risk concrete — of eleven applications on one dashboard,
six were already submitted, and two of those were absent from the local ledger
entirely. A write path that trusted the ledger alone would have edited a filed
application believing it was a draft.

WHAT AN APPROVED ACTION ACTUALLY IS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    propose_field_update(...)  → run the gate chain
                               → if it does not clear: REFUSED_BY_GATE, no token
                               → if it clears: ask Gary, return AWAITING_APPROVAL
                                 **the value is not written**
    apply_approved_action(a, writer=w)
                               → re-read the ledger *now*, refuse unless APPROVED
                               → refuse unless the token was issued for *this*
                                 action, verbatim
                               → refuse if this token has already been spent
                               → then, and only then, hand it to the writer

The re-read is deliberate and is the contract
:mod:`aureon.approval.gate` states: *never cache the answer*. Between a state read
at the top of a function and a write at the bottom, a deadline can pass and an
operator can decline. The only safe distance between the check and the act is
zero, so :func:`approval_state` is called as the last thing before the writer.

Every path writes one line to ``state/portals/action_log.jsonl`` — refusals
included. The refusals are the more interesting half: they are the evidence that
the system stopped rather than improvised.

WHAT THIS MODULE DOES NOT MEASURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
It publishes no HNC sub-field of its own. It measures no coherence, so it
contributes none — the rule :class:`aureon.approval.gate.WaitingPressure` keeps.
The pressure of a portal write waiting on Gary *is* already in the field:
:func:`~aureon.approval.gate.request_approval` calls
:func:`~aureon.approval.gate.publish_pressure`, which publishes the open request
through :func:`aureon.core.hnc_field.publish_subfield`. A second publisher here
would double-count the same wait.

Nothing in this file handles a credential. There is no login flow, no username,
no password, no cookie jar and no session store — the authenticated portal session
belongs to the operator's browser, and a writer that has no session must report
that absence (the :class:`~aureon.connectors.base.ConnectorStatus` pattern) rather
than acquire one. The one place a caller's secret could leak into the repository
is an exception message from a writer, so writer failures record the exception
*type* only, for the reason
:func:`aureon.connectors.base.build_google_service` gives.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from aureon.approval.gate import approval_state, hold_resolved, request_approval
from aureon.approval.schemas import ApprovalState, is_token
from aureon.gates.switchboard import DEFAULT_CHAIN, Gate, GateVerdict, is_human_held, run_chain
from aureon.portals.schemas import PORTAL_HELD_STATES, PORTAL_STATES, normalise_state

LOG = logging.getLogger("aureon.portals.actions")

# aureon/portals/actions.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PORTALS_DIR = REPO_ROOT / "state" / "portals"
DIR_VAR = "AUREON_PORTALS_DIR"

#: The append-only trail. One line per action, on every path.
ACTION_LOG_NAME = "action_log.jsonl"

BUS_SOURCE = "portal_actions"
TOPIC_PROPOSED = "portals.action.proposed"
TOPIC_REFUSED = "portals.action.refused"
TOPIC_APPLIED = "portals.action.applied"
#: A write that was attempted and did not demonstrably land. Distinct from
#: ``refused`` on purpose: "I did not act" and "I acted and cannot prove the
#: outcome" are different facts, and the organism needs to see which it is.
TOPIC_WRITE_FAILED = "portals.action.write_failed"

#: The one kind of write this module knows how to describe.
KIND_FIELD_UPDATE = "field_update"
#: Deliberately a set of one. Adding ``"submit"`` here does not enable a
#: submission — there is no function to run one — but it would let an action
#: *claim* to be one, so the import-time guard below refuses it outright.
ALLOWED_KINDS: frozenset[str] = frozenset({KIND_FIELD_UPDATE})

#: The action class handed to the gate chain, exactly as the switchboard sees it.
#: ``is_human_held("portal_field_update")`` is False — updating a draft field is
#: the Queen's to decide. What she may not do is decide it *alone*: clearing the
#: chain leads to an approval request, never to a write.
ACTION_FIELD_UPDATE = "portal_field_update"

#: The gates a field update actually passes. Derived from
#: :data:`~aureon.gates.switchboard.DEFAULT_CHAIN` rather than redeclared, so the
#: thresholds cannot drift from the trading lane's, with the human-held gates
#: filtered out.
#:
#: Why filtered: ``DEFAULT_CHAIN`` ends at ``Gate("submit", requires_human=True)``,
#: which returns HOLD however strong the evidence — so *every* completed pass of
#: the full chain ends in HOLD, whatever it was asked about. Reading that as "the
#: chain did not clear" would make :attr:`ActionState.REFUSED_BY_GATE` a constant
#: and this module inert; reading it as "ask Gary" would be the decay
#: :mod:`aureon.grants.dossier` warns about, where a gate that always fires stops
#: being read. Neither is honest. The hand that gate names as missing is supplied
#: here **unconditionally** — a field update is never written without an APPROVED
#: token, whatever the chain said — so the chain is asked only the question it can
#: actually answer: is this work justified?
WORK_CHAIN: tuple[Gate, ...] = tuple(g for g in DEFAULT_CHAIN if not g.requires_human)

# Import-time structural guard, not a runtime check: a held verb must not be
# nameable as a kind of write this module performs. Raised rather than asserted
# because ``python -O`` strips assertions, and this one is load-bearing.
_HELD_KINDS = tuple(sorted(k for k in ALLOWED_KINDS if is_human_held(k)))
if _HELD_KINDS:  # pragma: no cover — unreachable unless ALLOWED_KINDS is edited
    raise RuntimeError(
        f"aureon.portals.actions must not name a human-held step as a writable kind: "
        f"{', '.join(_HELD_KINDS)}. There is no executor for it here and there must not be one."
    )

# ── limits, all of them refusals rather than truncations ─────────────────────
#: A value longer than this is refused with its length stated. It is **not**
#: truncated: a human must approve the text that will be written, and silently
#: shortening it would put a different value in front of him than the one applied.
MAX_VALUE_CHARS = 20_000
MAX_FIELD_CHARS = 128
MAX_RATIONALE_CHARS = 2_000
#: How much of the value the audit line quotes. The full text lives in the
#: approval record (``state/approvals/<token>.json``), alongside the digest below,
#: so the trail can prove *which* text was approved without a second archive.
PREVIEW_CHARS = 240

#: A portal reference: alphanumeric with dots, dashes and underscores. Permissive
#: across funders (numeric at IFS, alphanumeric elsewhere) and closed against path
#: separators and control characters, because this string reaches an audit file and
#: an external system.
_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
#: Control characters, newlines included. A field *name* carrying a newline is
#: either a mistake or an injection into whatever renders it.
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


class ActionState(StrEnum):
    """Where one proposed write stands. Every refusal is its own state.

    A ``StrEnum``, so a member compares equal to its own name and writes straight
    into a JSON line — the same reason
    :class:`aureon.approval.schemas.ApprovalState` is one.

    There is no state meaning "probably fine". ``WRITE_UNVERIFIED`` exists because
    a writer that returns nothing has told us nothing: reading that as success
    would be a fabrication, and reading it as failure would be one too.
    """

    #: Constructed, nothing done with it yet. Never returned by a public function.
    PROPOSED = "PROPOSED"
    #: The proposal itself was malformed, or named a human-held step.
    REFUSED_INVALID = "REFUSED_INVALID"
    #: The gate chain did not clear it. No token was requested.
    REFUSED_BY_GATE = "REFUSED_BY_GATE"
    #: The chain cleared, but Gary could not be asked — see the approval log.
    REFUSED_UNASKABLE = "REFUSED_UNASKABLE"
    #: Asked. A live token, and **nothing written**.
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    #: The ledger did not say APPROVED at the moment of asking, or the token was
    #: issued for a different action.
    REFUSED_NOT_APPROVED = "REFUSED_NOT_APPROVED"
    #: This token has already been used for a write attempt. One approval, one act.
    REFUSED_TOKEN_SPENT = "REFUSED_TOKEN_SPENT"
    #: No writer was injected, so there is nothing that could touch the portal.
    REFUSED_NO_WRITER = "REFUSED_NO_WRITER"
    #: The writer reported that the value landed.
    APPLIED = "APPLIED"
    #: The writer reported that it did not.
    WRITE_FAILED = "WRITE_FAILED"
    #: The writer was called and did not say. Unknown, recorded as unknown.
    WRITE_UNVERIFIED = "WRITE_UNVERIFIED"

    @property
    def refused(self) -> bool:
        return self.value.startswith("REFUSED_")

    @property
    def attempted_write(self) -> bool:
        """True when a writer was actually called — whatever came of it.

        This is what spends a token. A blocker from a writer does not prove the
        write failed to land, so a retry needs a fresh approval, not a loop.
        """
        return self in {ActionState.APPLIED, ActionState.WRITE_FAILED,
                        ActionState.WRITE_UNVERIFIED}


def coerce_action_state(value: Any) -> ActionState:
    """Read a state from a member or its name. Raises on anything else."""
    if isinstance(value, ActionState):
        return value
    if isinstance(value, str):
        try:
            return ActionState(value.strip().upper())
        except ValueError as exc:
            raise ValueError(f"not a portal action state: {value!r}") from exc
    raise ValueError(f"not a portal action state: {value!r}")


@runtime_checkable
class FieldWriter(Protocol):
    """The one seam that can touch a portal — and it is always the caller's.

    A writer is expected to follow the connector rule
    (:class:`aureon.connectors.base.ConnectorStatus`): an unconfigured writer
    *reports* absence, it does not raise, and it certainly does not log in. The
    authenticated session belongs to the operator's browser; a writer without one
    returns ``available=False`` with a blocker naming what is missing.

    Return anything carrying ``available`` (and ``blocker`` when unavailable).
    A return value without ``available`` is recorded as
    :attr:`ActionState.WRITE_UNVERIFIED` rather than guessed at.

    Note what this protocol has no method for: submitting. A writer *may* have
    one; this module will never call it, because it never names one.
    """

    def write_field(self, application_number: str, field: str, value: str) -> Any:
        """Put ``value`` in ``field`` on the named draft application."""


@dataclass(frozen=True)
class PortalAction:
    """One proposed write, its grounding, its authority, and what became of it.

    Frozen: an audit record is not a mutable object. Each step returns a new
    instance through :func:`dataclasses.replace`.

    ``__post_init__`` enforces the *structural* invariants only — the ones that
    make a dishonest record unrepresentable:

    - the kind is one this module can actually perform (so an action describing a
      submission cannot be constructed at all);
    - a refused or failed state must carry a blocker, and an applied one must not
      (the :class:`~aureon.connectors.base.ConnectorStatus` discipline: "quietly
      did nothing" and "quietly did something" are both unrepresentable);
    - anything that claims authority — awaiting, applied, attempted — must carry a
      token.

    Content rules (empty field, oversized value, a field named ``submit``) are
    *not* enforced here, deliberately: a malformed proposal has to be
    constructible in order to be refused **and logged**. :func:`_validate` owns
    those, and the refusal it builds is a real record with a stated reason.

    The four properties at the bottom are the seam
    :mod:`aureon.approval.compose` reads when this action is handed to
    :func:`~aureon.approval.gate.request_approval` as its dossier. They are how
    Gary sees the field, the verbatim value and the reason in the mail he
    answers — an approval request he cannot read the substance of is a
    rubber stamp.
    """

    kind: str
    application_number: str
    field: str
    proposed_value: str
    rationale: str
    gate_verdicts: tuple[dict[str, Any], ...] = ()
    approval_token: str | None = None
    state: ActionState = ActionState.PROPOSED
    #: Why this action is not an ``APPLIED`` one. Never ``None`` on a refusal.
    blocker: str | None = None
    #: The funder's own state for this application when the caller had read one,
    #: normalised through :func:`aureon.portals.schemas.normalise_state`, and
    #: ``None`` when nobody read it. ``None`` means *unread*, never *draft*.
    portal_state: str | None = None
    #: Whether the audit line for this state actually reached disk.
    logged: bool = False

    def __post_init__(self) -> None:
        kind = str(self.kind or "").strip()
        if kind not in ALLOWED_KINDS:
            raise ValueError(
                f"{kind!r} is not a portal action this module performs "
                f"(allowed: {', '.join(sorted(ALLOWED_KINDS))}). There is no executor for "
                "anything else here, and a submission is not a kind of field update.")
        for name in ("application_number", "field", "proposed_value", "rationale"):
            if not isinstance(getattr(self, name), str):
                raise TypeError(f"{name} must be a string, not {type(getattr(self, name)).__name__}")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "state", coerce_action_state(self.state))
        object.__setattr__(self, "gate_verdicts",
                           tuple(dict(v) for v in (self.gate_verdicts or ())))
        blocker = str(self.blocker).strip() if self.blocker else None
        object.__setattr__(self, "blocker", blocker or None)

        state = self.state
        if (state.refused or state in {ActionState.WRITE_FAILED, ActionState.WRITE_UNVERIFIED}) \
                and not self.blocker:
            raise ValueError(f"a {state} action must state its blocker")
        if state in {ActionState.PROPOSED, ActionState.APPLIED} and self.blocker:
            raise ValueError(f"a {state} action cannot also carry a blocker")
        needs_token = state is ActionState.AWAITING_APPROVAL or state.attempted_write
        if needs_token and not is_token(self.approval_token or ""):
            raise ValueError(f"a {state} action must carry the approval token it acted on")

    # ── what happened, in one question each ──────────────────────────────────

    @property
    def wrote(self) -> bool:
        """True only for :attr:`ActionState.APPLIED`. The only "yes" in the type."""
        return self.state is ActionState.APPLIED

    @property
    def value_sha256(self) -> str:
        """A digest of the exact text proposed, so the trail can prove which one."""
        return hashlib.sha256(self.proposed_value.encode("utf-8")).hexdigest()

    @property
    def approval_action(self) -> str:
        """The action string this write's approval must have been issued for.

        **Derived, never stored.** A stored copy could drift from the fields
        around it; a derivation cannot. Edit ``application_number`` or ``field`` on
        a copy of an awaiting action and this name changes with them, so
        :func:`aureon.approval.gate.hold_resolved` — which compares verbatim
        against what the request was composed for — refuses the token. Tampering
        with the record fails closed.
        """
        return f"{ACTION_FIELD_UPDATE} {self.application_number} field={self.field}"

    def to_dict(self) -> dict[str, Any]:
        """The record, as it is written to the trail.

        ``logged`` is deliberately not in it: this dict *becomes* the audit line,
        and a line cannot truthfully report whether it was itself written. That
        flag lives on the returned action, where the answer is known.
        """
        return {
            "kind": self.kind,
            "application_number": self.application_number,
            "field": self.field,
            "state": self.state.value,
            "blocker": self.blocker,
            "rationale": self.rationale,
            "portal_state": self.portal_state,
            "approval_action": self.approval_action,
            "approval_token": self.approval_token,
            # The value by measurement and digest, plus a bounded quotation. The
            # full text is in the approval record Gary read; this file is a trail,
            # not a second archive of his application prose.
            "value_chars": len(self.proposed_value),
            "value_sha256": self.value_sha256,
            "value_preview": _preview(self.proposed_value),
            "gates": [{"gate": v.get("gate"), "decision": v.get("decision"),
                       "confidence": v.get("confidence")} for v in self.gate_verdicts],
        }

    # ── the seam aureon.approval.compose reads (see the class docstring) ─────

    @property
    def application_id(self) -> str:
        return self.application_number

    @property
    def name(self) -> str:
        return f"portal {self.kind}: {self.field}"

    @property
    def status(self) -> str:
        return self.state.value

    @property
    def outstanding(self) -> tuple[str, ...]:
        """What Gary is actually being asked to check, in his own mail."""
        return (
            f"Field to change: {self.field}",
            f"Why: {self.rationale}",
            "Portal state of this application: "
            + (self.portal_state if self.portal_state
               else "not read — nobody checked the funder's own dashboard for this proposal"),
            f"Value to be written if you approve ({len(self.proposed_value)} characters, "
            f"sha256 {self.value_sha256[:16]}…), verbatim:",
            self.proposed_value,
            "Nothing is written unless you reply yes. This is a draft field only — "
            "submitting the application is not something this system can do.",
        )


# ── where the trail lives ────────────────────────────────────────────────────


def portals_dir(root: Path | str | None = None) -> Path:
    """Where portal action records live.

    An explicit ``root`` wins and is used verbatim (``<root>/state/portals``),
    with no environment fallback, for the reason
    :func:`aureon.approval.store.approvals_dir` gives: a writer that quietly
    reaches out of the caller's tree into the live repository hides faults and
    leaks live data into tests. Otherwise :data:`DIR_VAR`, otherwise
    ``state/portals`` beside this repository.
    """
    if root is not None:
        return Path(root) / "state" / "portals"
    override = str(os.environ.get(DIR_VAR, "") or "").strip()
    return Path(override) if override else DEFAULT_PORTALS_DIR


def action_log_path(root: Path | str | None = None) -> Path:
    """The append-only record of every proposal, refusal and write."""
    return portals_dir(root) / ACTION_LOG_NAME


# ── proposing ────────────────────────────────────────────────────────────────


def propose_field_update(
    number: Any,
    field: Any,
    value: Any,
    *,
    rationale: Any,
    portal_state: Any = None,
    bus: Any = None,
    root: Path | str | None = None,
) -> PortalAction:
    """Propose one draft field change, run the gates, and ask Gary. Writes nothing.

    ``portal_state`` is what the funder's own dashboard says about this
    application, when the caller has read it: a
    :class:`~aureon.portals.schemas.PortalApplication`, that vocabulary's own
    state string, or the portal's raw prose (normalised through
    :func:`~aureon.portals.schemas.normalise_state`). A proposal against an
    application in :data:`~aureon.portals.schemas.PORTAL_HELD_STATES` — submitted,
    or ruled ineligible — is refused: the funder already holds it, so there is no
    draft to complete, and an "edit" there would be an alteration to a filed
    application. ``None`` means *nobody read it*, and is recorded as unread rather
    than assumed to be a draft; this module has no reader and no session of its
    own, so it never guesses this value.

    Returns a :class:`PortalAction` in exactly one of four states, and appends one
    audit line whichever it is:

    - :attr:`~ActionState.REFUSED_INVALID` — the proposal was malformed, named
      a human-held step (a field called ``submit`` is refused here, by name), or
      targets an application the funder already holds.
    - :attr:`~ActionState.REFUSED_BY_GATE` — the chain did not clear every gate.
      **No approval was requested**, so there is no token: a proposal the organism
      cannot justify does not get put in front of the owner as though it could.
    - :attr:`~ActionState.REFUSED_UNASKABLE` — the chain cleared but
      :func:`~aureon.approval.gate.request_approval` declined to ask (no owner
      address configured, no grounding it could show, or a ledger that refused the
      record). Nothing was written and nothing is pending.
    - :attr:`~ActionState.AWAITING_APPROVAL` — asked. The token is live, the value
      is **not** written, and :func:`apply_approved_action` is the only thing that
      can act on it.

    There is no ``writer`` parameter on this function, and that is structural:
    the deciding half and the acting half are separate calls, so the code that
    decides cannot also act.
    """
    action, blocker = _validate(number, field, value, rationale, portal_state)
    if blocker is not None:
        return _finish(replace(action, state=ActionState.REFUSED_INVALID, blocker=blocker),
                       root=root, bus=bus)

    try:
        verdicts: list[GateVerdict] = run_chain(
            {"action": ACTION_FIELD_UPDATE, "kind": action.kind,
             "application_number": action.application_number, "field": action.field},
            chain=WORK_CHAIN, bus=bus,
        )
    except Exception as exc:  # noqa: BLE001 — a chain that failed is not a chain that cleared
        LOG.warning("gate chain failed for %s on %s", action.field, action.application_number,
                    exc_info=True)
        return _finish(replace(action, state=ActionState.REFUSED_BY_GATE,
                               blocker=f"the gate chain could not be run ({type(exc).__name__})"),
                       root=root, bus=bus)

    action = replace(action, gate_verdicts=tuple(v.to_dict() for v in verdicts))

    # An empty chain must not read as unanimous consent. ``all(())`` is True, and
    # that is precisely the shape of "nothing checked this".
    if not verdicts or not all(v.advanced for v in verdicts):
        stopped = next((v for v in verdicts if not v.advanced), None)
        blocker = (f"gate {stopped.gate} returned {stopped.decision}: {stopped.reasoning}"
                   if stopped is not None else
                   "no gate was asked — an unexamined proposal is not an approved one")
        return _finish(replace(action, state=ActionState.REFUSED_BY_GATE, blocker=blocker),
                       root=root, bus=bus)

    # The chain cleared. That earns the right to *ask*, and nothing else. The
    # action itself is the dossier: it carries the verdicts and the verbatim value
    # Gary decides on — see PortalAction's compose seam.
    request = request_approval(action.approval_action,
                               application_id=action.application_number,
                               dossier=action, bus=bus)
    if request is None:
        return _finish(replace(
            action, state=ActionState.REFUSED_UNASKABLE,
            blocker=("the approval gate declined to ask — no owner address configured, no "
                     "grounding it could show, or the ledger refused the record; see the "
                     "approval log"),
        ), root=root, bus=bus)

    return _finish(replace(action, state=ActionState.AWAITING_APPROVAL,
                           approval_token=request.token), root=root, bus=bus)


# ── applying ─────────────────────────────────────────────────────────────────


def apply_approved_action(
    action: PortalAction,
    writer: Any = None,
    *,
    root: Path | str | None = None,
    bus: Any = None,
) -> PortalAction:
    """Write an approved field update — if, and only if, all four things hold.

    In this order, and the order is the point:

    1. the action is one that was actually asked about (``AWAITING_APPROVAL``);
    2. a ``writer`` was injected. **There is no default.** With nothing injected
       this returns :attr:`~ActionState.REFUSED_NO_WRITER` and the module has no
       other way to reach a portal — checked before the ledger so a missing hand
       never burns a live token;
    3. this token has not already been spent on a write attempt, per the audit
       log. One approval authorises one act; a retry needs a fresh ask;
    4. **and then, immediately**, the approval ledger is read — never a cached
       answer, never a value carried down from step 1 — and must say APPROVED
       *for this exact action*. :func:`~aureon.approval.gate.hold_resolved`
       compares the derived :attr:`PortalAction.approval_action` verbatim against
       what the request was composed for, so a token approved for another field,
       another application, or another kind of act cannot be spent here.

    Only after all four does the writer get called. Every outcome — including all
    four refusals — appends one audit line.
    """
    if not isinstance(action, PortalAction):
        raise TypeError("apply_approved_action expects a PortalAction")

    if action.state is not ActionState.AWAITING_APPROVAL:
        # Includes an already-applied action: re-applying a finished record is a
        # replay, whatever the ledger now says.
        return _finish(_refuse(action, ActionState.REFUSED_NOT_APPROVED,
                               f"this action is {action.state}, not AWAITING_APPROVAL — "
                               "only an action that was asked about can be applied"),
                       root=root, bus=bus)

    token = action.approval_token or ""
    if not is_token(token):  # unreachable: __post_init__ requires it. Belt as well as braces.
        return _finish(_refuse(action, ActionState.REFUSED_NOT_APPROVED,
                               "no approval token — nothing authorises this"), root=root, bus=bus)

    write_field = getattr(writer, "write_field", None)
    if writer is None or not callable(write_field):
        return _finish(_refuse(
            action, ActionState.REFUSED_NO_WRITER,
            "no writer was injected" if writer is None else
            f"the injected {type(writer).__name__} has no callable write_field",
        ), root=root, bus=bus)

    spent, unreadable = _token_spent(token, root=root)
    if unreadable is not None:
        # Cannot prove the token is unspent, so it is not spent. Fail closed: the
        # worst case is that Gary is asked again, never that a write happens twice.
        return _finish(_refuse(action, ActionState.REFUSED_TOKEN_SPENT,
                               f"could not prove this token is unspent ({unreadable})"),
                       root=root, bus=bus)
    if spent:
        return _finish(_refuse(action, ActionState.REFUSED_TOKEN_SPENT,
                               "this approval has already been used for a write attempt — "
                               "one approval authorises one act"), root=root, bus=bus)

    # ── the ledger, read now, and not one line earlier ───────────────────────
    state_now = approval_state(token)
    if state_now is not ApprovalState.APPROVED:
        return _finish(_refuse(action, ActionState.REFUSED_NOT_APPROVED,
                               f"the approval ledger says {state_now}, not APPROVED"),
                       root=root, bus=bus, approval_state_now=state_now)
    if not hold_resolved(action.approval_action, token):
        return _finish(_refuse(
            action, ActionState.REFUSED_NOT_APPROVED,
            "the token is APPROVED but was not issued for this exact action — refusing to "
            "spend it here"), root=root, bus=bus, approval_state_now=state_now)

    try:
        outcome = write_field(action.application_number, action.field, action.proposed_value)
    except Exception as exc:  # noqa: BLE001
        # The type only. A writer's exception message is the one place a portal
        # URL, cookie or session token could reach this repository's audit trail.
        LOG.warning("portal write raised for %s on %s", action.field, action.application_number,
                    exc_info=True)
        return _finish(replace(action, state=ActionState.WRITE_FAILED,
                               blocker=f"the writer raised {type(exc).__name__}"),
                       root=root, bus=bus, writer=writer, approval_state_now=state_now)

    available = getattr(outcome, "available", None)
    if available is True:
        return _finish(replace(action, state=ActionState.APPLIED, blocker=None),
                       root=root, bus=bus, writer=writer, approval_state_now=state_now)
    if available is False:
        return _finish(replace(
            action, state=ActionState.WRITE_FAILED,
            blocker=str(getattr(outcome, "blocker", None) or "the writer reported failure "
                        "without naming a blocker"),
        ), root=root, bus=bus, writer=writer, approval_state_now=state_now)

    return _finish(replace(
        action, state=ActionState.WRITE_UNVERIFIED,
        blocker=(f"the writer returned {type(outcome).__name__}, which does not say whether the "
                 "write landed — treat this application field as unknown, not written"),
    ), root=root, bus=bus, writer=writer, approval_state_now=state_now)


# ── validation ───────────────────────────────────────────────────────────────


def _read_portal_state(value: Any) -> str | None:
    """Normalise whatever the caller knows about the funder's own state, or ``None``.

    Accepts a :class:`~aureon.portals.schemas.PortalApplication`, a state from that
    vocabulary, or the portal's raw prose. ``None`` in means ``None`` out: unread is
    not a state, and it must never come back as ``not_started``.
    """
    if value is None:
        return None
    declared = getattr(value, "state", None)
    text = declared if isinstance(declared, str) and declared else value
    if isinstance(text, str) and text.strip() in PORTAL_STATES:
        return text.strip()
    state = normalise_state(text)
    return state


def _validate(number: Any, field: Any, value: Any, rationale: Any,
              portal_state: Any = None) -> tuple[PortalAction, str | None]:
    """Build the action, and say what is wrong with it. Never raises on content.

    Returns ``(action, blocker)``. The action is always constructible — a
    malformed proposal must be recordable in order to be refused in the trail —
    and ``blocker`` is ``None`` only when every rule below holds.

    Nothing is coerced into plausibility. A non-string value is refused, not
    stringified: ``str(None)`` is ``"None"``, and writing that into a live funding
    application is exactly the fabrication the Owner's Rule forbids.
    """
    reasons: list[str] = []

    if isinstance(number, bool) or not isinstance(number, (str, int)):
        reasons.append(f"application number must be a portal reference string, not "
                       f"{type(number).__name__}")
        reference = ""
    else:
        reference = str(number).strip()
        if not _REFERENCE_RE.match(reference):
            reasons.append("application number is not a portal reference "
                           "(letters, digits, dot, dash, underscore; 1-64 characters)")

    if not isinstance(field, str):
        reasons.append(f"field must be a string, not {type(field).__name__}")
        field_name = ""
    else:
        field_name = field.strip()
        if not field_name:
            reasons.append("no field was named")
        elif len(field_name) > MAX_FIELD_CHARS:
            reasons.append(f"field name is {len(field_name)} characters (limit {MAX_FIELD_CHARS})")
        elif _CONTROL_RE.search(field_name):
            reasons.append("field name carries control characters")
        elif is_human_held(field_name):
            # Layer 2, on the caller's own words. See the module docstring: this is
            # the smuggling route that the absence of a submit function alone
            # leaves open, and it is closed by the switchboard's own vocabulary.
            reasons.append(
                f"the field {field_name!r} names a human-held step — writing into it would be a "
                "submission wearing a field update's clothes, and no executor for that exists "
                "here or anywhere in this repository")

    if not isinstance(value, str):
        reasons.append(f"proposed value must be a string, not {type(value).__name__} — an "
                       "absence must never be written into a live application as text")
        text = ""
    else:
        text = value
        if not text.strip():
            reasons.append("the proposed value is blank — clearing a field is a separate "
                           "deliberate act this module does not offer")
        elif len(text) > MAX_VALUE_CHARS:
            reasons.append(f"the proposed value is {len(text)} characters (limit "
                           f"{MAX_VALUE_CHARS}); it is refused rather than truncated, because "
                           "Gary must approve the text that will actually be written")

    if not isinstance(rationale, str) or not rationale.strip():
        reasons.append("no rationale — a proposal without a stated reason cannot be approved "
                       "on its merits")
        reason_text = ""
    else:
        reason_text = rationale.strip()[:MAX_RATIONALE_CHARS]

    state = _read_portal_state(portal_state)
    if state in PORTAL_HELD_STATES:
        reasons.append(
            f"the funder's own dashboard shows this application as {state} — it already holds it, "
            "so there is no draft field to complete here and an edit would be an alteration to a "
            "filed application")

    action = PortalAction(kind=KIND_FIELD_UPDATE, application_number=reference, field=field_name,
                          proposed_value=text, rationale=reason_text, portal_state=state)
    return action, ("; ".join(reasons) if reasons else None)


def _refuse(action: PortalAction, state: ActionState, blocker: str) -> PortalAction:
    """A refusal that keeps the token it refused to spend, for the trail."""
    return replace(action, state=state, blocker=blocker)


# ── the trail ────────────────────────────────────────────────────────────────


def _token_spent(token: str, *, root: Path | str | None = None) -> tuple[bool, str | None]:
    """Has this token already been used for a write attempt?

    Returns ``(spent, unreadable)``. ``unreadable`` is a blocker string when the
    log exists but cannot be read — in which case the caller must treat the token
    as spent, because an unprovable token is not an authorisation.

    A missing log is not unreadable: it is a log with nothing in it, and that is a
    real answer. Individual malformed lines are skipped and warned about rather
    than fatal — this guard is a replay brake on top of the approval ledger, not a
    substitute for it, and one corrupt byte must not permanently block every
    future write.
    """
    path = action_log_path(root)
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    LOG.warning("portal action log carries a line that is not JSON — skipped")
                    continue
                if not isinstance(row, dict) or row.get("approval_token") != token:
                    continue
                try:
                    if coerce_action_state(row.get("state")).attempted_write:
                        return True, None
                except ValueError:
                    LOG.warning("portal action log carries an unknown state — skipped")
    except FileNotFoundError:
        return False, None
    except (OSError, UnicodeDecodeError) as exc:
        return False, f"the action log could not be read: {type(exc).__name__}"
    return False, None


def _finish(
    action: PortalAction,
    *,
    root: Path | str | None,
    bus: Any = None,
    writer: Any = None,
    approval_state_now: Any = None,
) -> PortalAction:
    """Write the audit line, announce it, and return the action carrying both.

    The single exit from both public functions, which is how "one line per action,
    on every path" is a property of the code rather than a promise in a docstring.
    """
    row = action.to_dict()
    row["timestamp"] = datetime.now(UTC).isoformat()
    # Which portal this reaches is a property of the injected writer, not of the
    # action: this module names no portal, no URL and no funder. The writer's type
    # is recorded — never its configuration, and never a credential.
    row["writer"] = type(writer).__name__ if writer is not None else None
    row["approval_state_at_write"] = str(approval_state_now) if approval_state_now else None
    row["wrote"] = action.wrote

    path = action_log_path(root)
    logged = _append_line(path, row)
    if not logged:
        LOG.error("portal action %s on %s (%s) could not be recorded at %s",
                  action.field, action.application_number, action.state, path)

    final = replace(action, logged=logged)
    topic = (TOPIC_APPLIED if final.wrote
             else TOPIC_WRITE_FAILED if final.state.attempted_write
             else TOPIC_REFUSED if final.state.refused
             else TOPIC_PROPOSED)
    _publish(bus, topic, row)
    return final


def _append_line(path: Path, row: dict[str, Any]) -> bool:
    """Append one JSON line. Never raises — the caller decides what a lost line means."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return True
    except OSError:
        LOG.debug("portal action log append failed: %s", path, exc_info=True)
        return False


def _preview(text: str) -> str:
    """A bounded, single-line quotation of the value, with truncation made visible."""
    flat = " ".join(str(text).split())
    if len(flat) <= PREVIEW_CHARS:
        return flat
    return flat[:PREVIEW_CHARS] + f"… (+{len(flat) - PREVIEW_CHARS} more characters)"


def _publish(bus: Any, topic: str, payload: dict[str, Any]) -> None:
    """Put one portal event on the thought bus. Guarded; never fatal.

    A bus that will not take a thought must not be able to stop a write from being
    recorded — the log on disk is the trail, and this is the organism noticing.
    """
    if bus is None:
        return
    try:
        from aureon.core.aureon_thought_bus import Thought

        bus.publish(Thought(source=BUS_SOURCE, topic=topic, payload=dict(payload)))
    except Exception:  # noqa: BLE001
        LOG.debug("portal action publish skipped (%s)", topic, exc_info=True)


__all__ = [
    "ACTION_FIELD_UPDATE",
    "ACTION_LOG_NAME",
    "ALLOWED_KINDS",
    "BUS_SOURCE",
    "DEFAULT_PORTALS_DIR",
    "DIR_VAR",
    "KIND_FIELD_UPDATE",
    "MAX_FIELD_CHARS",
    "MAX_RATIONALE_CHARS",
    "MAX_VALUE_CHARS",
    "PREVIEW_CHARS",
    "TOPIC_APPLIED",
    "TOPIC_PROPOSED",
    "TOPIC_REFUSED",
    "TOPIC_WRITE_FAILED",
    "WORK_CHAIN",
    "ActionState",
    "FieldWriter",
    "PortalAction",
    "action_log_path",
    "apply_approved_action",
    "coerce_action_state",
    "portals_dir",
    "propose_field_update",
]
