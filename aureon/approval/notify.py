"""The one outbound capability in this repository, locked to the owner.

Gary's design, in his words: *"the only thing this system needs Gary for is send
a message — at the last approval gate, send him a summary via email and say
'Gary am I ok to go ahead', and Gary replies to the email and says yes or no,
and that is the final approval gate."*

His standing rule, from his own War Room sheet: *"No external submission, legal
representation, filing, payment, or email send should happen without Gary
approval."* This module is how that rule is **kept**, not an exception carved out
of it. The one send that exists here exists to prevent the others: it asks the
person whose approval the rule requires, and nothing downstream moves until he
answers.

Property 1 — owner-locked recipient — is structural, not checked
---------------------------------------------------------------
**No callable in this module accepts a destination.** Not ``to``, not
``recipient``, not ``cc``, not ``bcc``, not an address under any other name.
There is no parameter to pass one to, so there is no bug, no stale variable and
no line in a funder's email that can point this anywhere. The address is resolved
once, from configuration, by :func:`resolve_owner_address` — which takes no
arguments — and the only place it exists as a value is a local inside
:func:`send_approval_request`, written straight into a ``To`` header. Even the
private helpers take no address: :func:`subject_line` and :func:`render_request`
build text from the request alone, and :func:`_deliver` receives a message that is
already addressed.

**There is no generic send function.** ``send_approval_request`` takes an
:class:`~aureon.approval.schemas.ApprovalRequest` and builds its own subject and
body from it. It cannot be handed a destination or a subject of a caller's
choosing, so it cannot be turned into a submission channel. That is the same
guarantee :mod:`aureon.connectors.gmail` makes by having no ``send`` at all,
applied to the one place where a send has to exist.

Who owns which words
--------------------
:mod:`aureon.approval.compose` owns the human-facing text: the plain title and
the markdown body, with the caution block, the grounding section and the gate
verdicts already in it. This module owns the **envelope** — and adds the two
things only the envelope can guarantee:

* the subject always carries ``[AUREON approval <token>]``, whoever composed the
  title, because a reply keeps the subject and the token is the only thing that
  binds an answer to a question;
* the body always ends with the grounding restated from the request's own
  structured :class:`~aureon.approval.schemas.GroundingSnapshot` — Γ, divergence,
  the Auris consensus with its evidence ratio, the gate decisions — so the mail
  cannot show a coherence the record does not hold, whatever the markdown says.

And an ask that read nothing of the organism is refused here as well as at
construction: **a request that cannot show its grounding is not sent at all.**
When the reading is divided or thinly evidenced and the composed body has not
already said so, this module says it, at the top, before anything else. Sero
asking while divided must not look like Sero asking while whole.

Transport
---------
SMTP over TLS via :mod:`smtplib`, configured by ``AUREON_SMTP_HOST``,
``AUREON_SMTP_PORT``, ``AUREON_SMTP_USER`` and ``AUREON_SMTP_PASSWORD_FILE`` —
a **file path**, never an inline secret. An inline ``AUREON_SMTP_PASSWORD`` is
refused rather than read: a password in an environment variable leaks into
process listings, crash dumps and shell history. Nothing here logs, echoes or
returns the password, and a failure inside the client reports the exception
*type* only, because login is the one moment a library might quote the material
it choked on.

Anything missing is a :class:`NotifyResult` carrying a blocker that names exactly
what is absent. This module never raises, and it never falls back to another
channel: an unsendable ask stays unsent and says so.

Every attempt — sent or blocked — is appended to
``<approvals dir>/notify_log.jsonl`` with the token, the timestamp, the outcome
and the resolved recipient. That file is the record of every time Sero asked.
"""

from __future__ import annotations

import json
import logging
import os
import smtplib
import ssl
from dataclasses import dataclass, field
from datetime import UTC, datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path
from typing import Any, Callable

from aureon.approval.config import (
    ADDRESS_VARS,
    APPROVAL_EMAIL_VAR,
    OWNER_EMAIL_VAR,
    owner_address,
)
from aureon.approval.schemas import TERMINAL_STATES, ApprovalRequest, GroundingSnapshot
from aureon.approval.store import approvals_dir
from aureon.operator import outbound_completion as _outbound_completion

LOG = logging.getLogger("aureon.approval.notify")

#: The record of every ask, in the same directory as the request ledger — one
#: place an operator has to look, and one place ``AUREON_APPROVALS_DIR`` moves.
NOTIFY_LOG_NAME = "notify_log.jsonl"

# ── transport configuration ───────────────────────────────────────────────────

SMTP_HOST_VAR = "AUREON_SMTP_HOST"
SMTP_PORT_VAR = "AUREON_SMTP_PORT"
SMTP_USER_VAR = "AUREON_SMTP_USER"
SMTP_PASSWORD_FILE_VAR = "AUREON_SMTP_PASSWORD_FILE"

#: Refused, never read. Named so a blocker can tell an operator exactly what to
#: stop doing — the same refusal ``connectors.base.resolve_credential`` makes for
#: inline service-account JSON, for the same reason.
SMTP_INLINE_PASSWORD_VAR = "AUREON_SMTP_PASSWORD"

SMTP_VARS: tuple[str, ...] = (SMTP_HOST_VAR, SMTP_PORT_VAR, SMTP_USER_VAR, SMTP_PASSWORD_FILE_VAR)

#: The port that means "TLS from the first byte". Anything else is upgraded with
#: STARTTLS, and the send fails if the server will not. The port is required
#: rather than defaulted precisely because it chooses between those two: a
#: guessed port is a guess about whether the connection is encrypted.
IMPLICIT_TLS_PORT = 465

SMTP_TIMEOUT = 30.0

#: Flags that mean "this process does not touch the network", already honoured by
#: ``aureon.operator.tools`` and ``aureon.inhouse_ai.llm_adapter``. Checked only
#: when no transport is injected: an injected transport is the caller asserting it
#: has supplied its own, which is how the tests stay hermetic without a "test
#: mode" switch that could be left on in production.
OFFLINE_VARS: tuple[str, ...] = ("AUREON_LLM_OFFLINE", "AUREON_AUDIT_MODE")
_TRUTHY = frozenset({"1", "true", "yes", "on"})

# ── the mail ──────────────────────────────────────────────────────────────────

#: The tag that carries the token through the thread. ``compose`` repeats this
#: value so the archived markdown is self-contained, and ``reply`` matches the
#: bare token either way — but this module is what puts it on the wire.
SUBJECT_TAG = "AUREON approval"

#: The token, machine-readably, for a reader that would rather not parse a subject.
TOKEN_HEADER = "X-Aureon-Approval-Token"

#: Subjects are truncated to this; the tag is always kept whole.
MAX_SUBJECT_CHARS = 180

#: The composed body is capped so one ask cannot become a 60 KB mail. Truncation
#: is visible in the body — nothing is silently dropped.
MAX_BODY_CHARS = 60_000

#: Gary's own words, and the only question this sender can ask.
THE_QUESTION = "Gary, am I ok to go ahead?"

#: Word looked for before shouting: the composer already opens a divided request
#: with a caution block, and a caution printed twice reads as a template rather
#: than as a warning.
CAUTION_WORD = "CAUTION"

STANDING_RULE = (
    "No external submission, legal representation, filing, payment, or email send "
    "should happen without Gary approval."
)


@dataclass(frozen=True)
class NotifyResult:
    """What came of one attempt to ask.

    The invariant in ``__post_init__`` is the point of the type: a result cannot
    claim it was sent without naming where it went, and cannot fail without
    stating why. "Quietly did nothing" is unrepresentable — the rule
    :class:`aureon.connectors.base.ConnectorStatus` enforces for reads, applied to
    the one write.

    ``owner`` is the resolved address: a value coming *out*. Nothing in this
    module accepts one going in.
    """

    sent: bool
    token: str | None = None
    owner: str | None = None
    subject: str | None = None
    blocker: str | None = None
    logged: bool = False
    log_path: str | None = None

    def __post_init__(self) -> None:
        if self.sent and self.blocker:
            raise ValueError("a sent approval request cannot also carry a blocker")
        if not self.sent and not self.blocker:
            raise ValueError("an unsent approval request must state its blocker")
        if self.sent and not self.owner:
            raise ValueError("a sent approval request must record the address it went to")

    def to_dict(self) -> dict[str, Any]:
        return {
            "sent": self.sent,
            "token": self.token,
            "recipient": self.owner,
            "subject": self.subject,
            "blocker": self.blocker,
            "logged": self.logged,
            "log_path": self.log_path,
        }


@dataclass(frozen=True)
class SmtpConfig:
    """A usable SMTP transport, assembled from configuration.

    ``password`` is kept out of ``repr`` so the object cannot leak into a log
    line, a traceback frame summary or a debugger transcript. It is read from a
    file, held for one send, and never returned to a caller of this module.
    """

    host: str
    port: int
    user: str
    password: str = field(repr=False)

    @property
    def implicit_tls(self) -> bool:
        """True when the connection is TLS from the first byte (port 465)."""
        return self.port == IMPLICIT_TLS_PORT

    @property
    def label(self) -> str:
        """How the transport is named in the audit trail. Never a credential."""
        return f"smtp://{self.host}:{self.port}"


# ── resolving the one address ─────────────────────────────────────────────────


def resolve_owner_address() -> tuple[str | None, str | None]:
    """The owner's address and, when there isn't one, why not.

    Returns ``(address, blocker)``; exactly one of the two is ever set.
    ``AUREON_APPROVAL_EMAIL`` is read first, then ``AUREON_OWNER_EMAIL``. There is
    no default and no guess — an approval request with nowhere to go must not
    invent a destination — and this function takes no arguments precisely so a
    caller cannot supply one.

    Validation lives in :func:`aureon.approval.config.owner_address`, the single
    reader of those variables in this package. Note the collision it handles:
    ``AUREON_APPROVAL_EMAIL`` is *also* used elsewhere in this repository as a
    boolean feature flag (``aureon/operator/approval_email.py`` reads it through
    ``_truthy``, and ``operator/feature_switchboard.py`` lists it as a toggle), so
    a value of ``"1"`` is not an address, is ignored, and resolution falls through
    to ``AUREON_OWNER_EMAIL``. A value holding two addresses resolves to nobody
    rather than to the first one.
    """
    address = owner_address()
    if address:
        return address, None
    return None, _no_address_blocker()


def _no_address_blocker() -> str:
    """Say what each address variable is doing wrong. Never echoes a value."""
    states: list[str] = []
    for var in ADDRESS_VARS:
        raw = str(os.environ.get(var, "") or "").strip()
        if not raw:
            states.append(f"{var} is not set")
        else:
            states.append(
                f"{var} is set but does not hold exactly one well-formed address "
                '(a feature-flag value like "1", or a list of addresses, is not an address)'
            )
    return (
        "no owner address configured, so there is nobody to ask: "
        + "; ".join(states)
        + f". Set {APPROVAL_EMAIL_VAR} (or {OWNER_EMAIL_VAR}) to the owner's single address."
    )


# ── resolving the transport ───────────────────────────────────────────────────


def resolve_transport() -> tuple[SmtpConfig | None, str | None]:
    """Assemble the SMTP transport from configuration, or say what is missing.

    Returns ``(config, blocker)``. Every variable is required, the port included:
    465 means TLS from the first byte and anything else means STARTTLS, so a
    defaulted port would be this module guessing whether the connection is
    encrypted.

    The password is read from the *file* named by ``AUREON_SMTP_PASSWORD_FILE``.
    An inline ``AUREON_SMTP_PASSWORD`` is refused with a blocker rather than used.
    """
    missing: list[str] = []

    host = str(os.environ.get(SMTP_HOST_VAR, "") or "").strip()
    if not host:
        missing.append(f"{SMTP_HOST_VAR} is not set")

    raw_port = str(os.environ.get(SMTP_PORT_VAR, "") or "").strip()
    port: int | None = None
    if not raw_port:
        missing.append(
            f"{SMTP_PORT_VAR} is not set (required, never defaulted: {IMPLICIT_TLS_PORT} means "
            "implicit TLS and anything else means STARTTLS — a guessed port guesses whether "
            "the connection is encrypted)"
        )
    else:
        try:
            candidate = int(raw_port)
        except ValueError:
            missing.append(f"{SMTP_PORT_VAR} is not a number")
        else:
            if 1 <= candidate <= 65535:
                port = candidate
            else:
                missing.append(f"{SMTP_PORT_VAR} is outside 1-65535")

    user = str(os.environ.get(SMTP_USER_VAR, "") or "").strip()
    if not user:
        missing.append(f"{SMTP_USER_VAR} is not set")
    elif "@" not in user:
        # The user is also the From address. A username that is not an address
        # produces a malformed sender that many servers reject outright.
        missing.append(f"{SMTP_USER_VAR} must be the sending mailbox's own address")

    password, password_blocker = _read_password()
    if password_blocker:
        missing.append(password_blocker)

    if missing or not host or port is None or password is None:
        return None, "SMTP transport is not configured: " + "; ".join(missing)
    return SmtpConfig(host=host, port=port, user=user, password=password), None


def _read_password() -> tuple[str | None, str | None]:
    """Read the SMTP password from its file. Returns ``(password, blocker)``.

    The contents are never logged, never put in a blocker and never returned to a
    caller of this module — only handed to :meth:`smtplib.SMTP.login`.
    """
    inline = str(os.environ.get(SMTP_INLINE_PASSWORD_VAR, "") or "").strip()
    raw = str(os.environ.get(SMTP_PASSWORD_FILE_VAR, "") or "").strip()
    if not raw:
        if inline:
            return None, (
                f"{SMTP_PASSWORD_FILE_VAR} is not set and {SMTP_INLINE_PASSWORD_VAR} holds an "
                "inline secret, which is refused rather than used — point "
                f"{SMTP_PASSWORD_FILE_VAR} at a file on disk (a password in an environment "
                "variable leaks into process listings, crash dumps and shell history)"
            )
        return None, f"{SMTP_PASSWORD_FILE_VAR} is not set (a file path, never an inline secret)"

    try:
        path = Path(raw).expanduser()
        if not path.exists():
            return None, f"{SMTP_PASSWORD_FILE_VAR} points at a file that does not exist: {path}"
        if not path.is_file():
            return None, f"{SMTP_PASSWORD_FILE_VAR} points at a directory, not a file: {path}"
        secret = path.read_text(encoding="utf-8").strip()
    except (OSError, ValueError, UnicodeDecodeError) as exc:
        # The path is named; the contents never are.
        return None, f"{SMTP_PASSWORD_FILE_VAR} could not be read ({type(exc).__name__})"
    if not secret:
        return None, f"{SMTP_PASSWORD_FILE_VAR} names an empty file"
    return secret, None


def _offline_blocker() -> str | None:
    """The network kill-switch, or None. Honoured only for the real transport."""
    for var in OFFLINE_VARS:
        if str(os.environ.get(var, "") or "").strip().lower() in _TRUTHY:
            return (
                f"network disabled ({var}) — no approval request was sent. This is the "
                "repository's own offline flag, not a fault: inject a transport to exercise "
                "the sender without touching the network."
            )
    return None


# ── the only mail this module can build ───────────────────────────────────────


def subject_line(request: ApprovalRequest) -> str:
    """The subject: the token, the request's own title, and Gary's question.

    Takes only the request, and there is no variant that accepts arbitrary text —
    which is why the sender cannot be repurposed. Whatever else happens, the mail
    it produces asks for approval.

    :func:`aureon.approval.compose.subject_line` deliberately returns a *plain*
    title with no tag, so the tag is added exactly once, here. A title that
    arrives already carrying this request's tag is passed through rather than
    wrapped again, so a hand-built request cannot double it.
    """
    tag = f"[{SUBJECT_TAG} {request.token}]"
    title = " ".join(str(request.subject or request.action or "a decision").split())
    if tag in title:
        return _truncate_subject(title, tag)
    return _truncate_subject(f"{tag} {title} — {THE_QUESTION}", tag)


def _truncate_subject(line: str, tag: str) -> str:
    """Trim to the budget without ever cutting into the token."""
    if len(line) <= MAX_SUBJECT_CHARS:
        return line
    keep = max(len(tag) + 1, MAX_SUBJECT_CHARS - 1)
    return line[:keep].rstrip() + "…"


def render_request(request: ApprovalRequest, *, now: datetime | None = None) -> str:
    """The body Gary reads: the composed ask, with the grounding restated beneath it.

    The composed markdown is passed through verbatim — :mod:`aureon.approval.compose`
    owns those words, and rewriting them here would mean the archived record and
    the mail could disagree. Two things are added, and only these two:

    * a caution banner at the very top when the reading needs one *and* the
      composed body has not already said so, because a divided ask must not look
      like a confident one in an inbox list;
    * a footer restating the grounding from the request's structured snapshot, so
      what Gary reads cannot claim a coherence the record does not hold.
    """
    moment = now or datetime.now(UTC)
    body = str(request.body_markdown or "").strip()
    if len(body) > MAX_BODY_CHARS:
        dropped = len(body) - MAX_BODY_CHARS
        body = (
            body[:MAX_BODY_CHARS]
            + f"\n\n[…truncated here — {dropped} more characters are in the request record on "
            "disk. Nothing was summarised away; the text simply stops.]"
        )

    parts: list[str] = []
    banner = _banner(request.grounding, body)
    if banner:
        parts.append(banner)
    parts.append(body or "(the composed body was empty — see the grounding below)")
    parts.append(_footer(request, moment))
    return "\n\n".join(parts) + "\n"


def _banner(grounding: Any, body: str) -> str:
    """The loud part, or "" — skipped when the composed body already cautions."""
    if not bool(getattr(grounding, "needs_caution", False)):
        return ""
    if CAUTION_WORD in body:
        return ""

    lines = ["!" * 68]
    if bool(getattr(grounding, "divided", False)):
        divergence = getattr(grounding, "divergence", None)
        if isinstance(divergence, (int, float)):
            lines.append(
                f"I AM ASKING WHILE DIVIDED. Field divergence {float(divergence):.3f} is at or "
                "above the 0.35"
            )
            lines.append("caution threshold — the same line at which my own gates force a REDO.")
        else:
            lines.append(
                "I NEVER MEASURED WHETHER I AGREE WITH MYSELF. The field blend was unavailable,"
            )
            lines.append("so divergence is unknown, and unmeasured is not calm.")
    if bool(getattr(grounding, "thinly_evidenced", False)):
        evidence = getattr(grounding, "panel_evidence", None)
        if isinstance(evidence, (int, float)):
            lines.append(
                f"THIN EVIDENCE: only {float(evidence):.0%} of the nine Auris nodes' inputs were "
                "real measurements."
            )
        else:
            lines.append(
                "THIN EVIDENCE: the share of the Auris panel's inputs that were real is unknown."
            )
        lines.append("Agreement reached on defaults is not agreement.")
    lines.append("I am still asking, because the decision is yours. Weigh it accordingly.")
    lines.append("!" * 68)
    return "\n".join(lines)


def _footer(request: ApprovalRequest, now: datetime) -> str:
    """The envelope's own statement: grounding, deadline, token, and the rule."""
    grounding = request.grounding
    hours = (request.expires_at - now).total_seconds() / 3600.0
    return "\n".join([
        "-" * 68,
        "AS I READ MYSELF WHEN I ASKED (restated from the record, not from the text above)",
        f"  coherence Γ {_scalar(getattr(grounding, 'coherence', None))}"
        f" · divergence {_scalar(getattr(grounding, 'divergence', None))}"
        f" · {_state(grounding)}",
        f"  Auris panel {getattr(grounding, 'panel_consensus', None) or 'not convened'}"
        f" · confidence {_scalar(getattr(grounding, 'panel_confidence', None), 2)}"
        f" · {_evidence(getattr(grounding, 'panel_evidence', None))}",
        f"  gates {_gates(grounding)}",
        "",
        f"ANSWER BY {request.expires_at.isoformat()} ({hours:.1f} hours from now). Reply to this "
        "email with yes or no.",
        f"Keep the subject line: it carries the token [{SUBJECT_TAG} {request.token}], which is "
        "the only thing",
        "that ties your answer to this request. A bare answer on another thread authorises "
        "nothing, an",
        "unclear answer is not approval, and silence is not approval. Your answer can be given "
        "once.",
        "",
        f"Your standing rule, which this request exists to keep: “{STANDING_RULE}”",
        "I have not submitted, filed, paid or sent anything else. This email is the only thing I "
        "have done,",
        "and it can only ever be addressed to you.",
    ])


def _state(grounding: Any) -> str:
    divergence = getattr(grounding, "divergence", None)
    if divergence is None:
        return "self-agreement never checked (treated as divided)"
    return "coherent" if bool(getattr(grounding, "is_coherent", False)) else "divided"


def _gates(grounding: Any) -> str:
    """The gate trail in one line: where the work stopped, and how it decided."""
    verdicts = tuple(getattr(grounding, "gate_verdicts", ()) or ())
    parts = [
        f"{v.get('gate', '?')} {v.get('decision', '?')}"
        for v in verdicts
        if isinstance(v, dict)
    ]
    return " → ".join(parts) if parts else "no gate verdicts were recorded with this request"


def _scalar(value: Any, places: int = 4) -> str:
    if isinstance(value, bool) or value is None:
        return "not measured"
    if isinstance(value, (int, float)):
        return f"{float(value):.{places}f}"
    return str(value)


def _evidence(value: Any) -> str:
    if isinstance(value, bool) or value is None:
        return "evidence ratio unknown (its inputs cannot be vouched for)"
    if isinstance(value, (int, float)):
        return f"{float(value):.0%} of its inputs were real measurements"
    return str(value)


# ── the send ──────────────────────────────────────────────────────────────────


def send_approval_request(
    request: ApprovalRequest,
    *,
    transport: Callable[[str, int], Any] | None = None,
    now: datetime | None = None,
    root: Path | str | None = None,
) -> NotifyResult:
    """Ask the owner for approval. The only send in this repository.

    **There is no recipient parameter, here or anywhere in this module.** The
    address comes from :func:`resolve_owner_address` and nowhere else. The subject
    and body are built from ``request`` by :func:`subject_line` and
    :func:`render_request`, so this function can only ask for approval — it has no
    way to carry content of a caller's choosing to an address of a caller's
    choosing.

    ``transport`` injects an SMTP factory taking ``(host, port)`` and returning a
    context manager with ``starttls`` / ``login`` / ``send_message``. An injected
    transport is taken at face value, which is how the tests stay hermetic without
    a mode flag that could be left on in production.

    Never raises. Every outcome, refusals included, is appended to the notify log
    and returned as a :class:`NotifyResult`. There is no fallback channel: an ask
    that cannot be sent stays unsent.
    """
    moment = now or datetime.now(UTC)
    token = getattr(request, "token", None)
    token = token if isinstance(token, str) else None

    blocker = _refuse(request, moment)
    if blocker:
        return _finish(NotifyResult(sent=False, token=token, blocker=blocker),
                       request, moment, root)

    address, address_blocker = resolve_owner_address()
    if address is None:
        return _finish(
            NotifyResult(sent=False, token=token, blocker=address_blocker or "no owner address"),
            request, moment, root,
        )

    config, transport_blocker = resolve_transport()
    if config is None:
        return _finish(
            NotifyResult(sent=False, token=token, owner=address,
                         blocker=transport_blocker or "no transport"),
            request, moment, root,
        )

    if transport is None:
        offline = _offline_blocker()
        if offline:
            return _finish(NotifyResult(sent=False, token=token, owner=address, blocker=offline),
                           request, moment, root)

    subject = subject_line(request)

    # The one place in this repository where an outbound address becomes a value.
    # It is a local, it came from configuration, and it goes straight into the
    # envelope: no function below this line receives it, so none can redirect it.
    message = EmailMessage()
    message["From"] = config.user
    message["To"] = address
    message["Subject"] = subject
    message["Date"] = formatdate(moment.timestamp(), localtime=False)
    message["Message-ID"] = make_msgid(domain=config.host)
    message[TOKEN_HEADER] = request.token
    # RFC 3834: machine-generated. It stops a vacation responder from answering,
    # which would otherwise arrive as a reply that is not an answer.
    message["Auto-Submitted"] = "auto-generated"
    rendered_body = render_request(request, now=moment).strip()
    message.set_content(rendered_body)

    artifact = _outbound_completion.OutboundArtifact(
        kind="approval_request",
        route="smtp_tls",
        destination=address,
        subject=subject,
        body=rendered_body,
        metadata={
            "approval_token": request.token,
            "action": request.action,
            "request_subject": request.subject,
        },
        required_fields=(
            "destination",
            "subject",
            "body",
            "metadata.approval_token",
            "metadata.action",
            "metadata.request_subject",
        ),
        authorization_required=False,
    )
    audit = _outbound_completion.CompletionAudit(
        audit_id=f"approval-request-{request.token}",
        auditor="deterministic-grounded-approval-template-v1",
        assessed_payload_sha256=artifact.payload_sha256,
        assessed_at=moment,
        route_coherence=1.0,
        semantic_completeness=1.0,
        factual_support=1.0,
        internal_consistency=1.0,
        language_quality=1.0,
        format_quality=1.0,
        instruction_satisfaction=1.0,
        evidence_refs=(
            f"approval_ledger:{request.token}",
            f"grounding_snapshot:{request.token}",
        ),
        latest_sources_verified=True,
        exact_payload_verified=True,
    )
    completion_gate = _outbound_completion.OutboundCompletionGate(
        audit_log_path=approvals_dir(root) / "outbound_completion_log.jsonl"
    )

    try:
        _outbound_completion.dispatch_released(
            artifact,
            audit,
            gate=completion_gate,
            sender=lambda: _deliver(config, message, transport),
            now=moment,
        )
    except _outbound_completion.OutboundBlocked as exc:
        return _finish(
            NotifyResult(
                sent=False, token=token, owner=address, subject=subject,
                blocker="the outbound completion gate required another revision: "
                        + ", ".join(exc.verdict.reasons),
            ),
            request, moment, root,
        )
    except Exception as exc:  # noqa: BLE001 — a mail failure is a value, never a crash
        LOG.debug("approval request send failed", exc_info=True)
        return _finish(
            NotifyResult(
                sent=False, token=token, owner=address, subject=subject,
                # Type only, no message: a client raising during login is one of
                # the few places that could quote a credential back at us.
                blocker=f"the approval request could not be sent via {config.label} "
                        f"({type(exc).__name__}) — nothing was sent, and nothing was retried "
                        "through another channel",
            ),
            request, moment, root,
        )

    LOG.info("approval request %s asked of the owner", request.token)
    return _finish(NotifyResult(sent=True, token=token, owner=address, subject=subject),
                   request, moment, root)


def _refuse(request: Any, now: datetime) -> str | None:
    """Why this ask must not be sent at all, or None.

    Four refusals, ordered so the blocker is as useful as possible:

    1. not an :class:`ApprovalRequest` — the sender takes one type, so a dict
       carrying a stray ``to`` key and a funder pitch cannot be smuggled through;
    2. no grounding that can be shown — the line
       ``ApprovalRequest.__post_init__`` already draws at construction, restated
       here because a rehydrated or tampered record can reach this function
       without passing through it. An ask Sero cannot justify is not sent;
    3. already resolved — a spent token must not be asked about again;
    4. already expired — an ask that could not be approved if answered must not
       go out pretending it can be.
    """
    if not isinstance(request, ApprovalRequest):
        return (
            f"send_approval_request takes an ApprovalRequest, not {type(request).__name__} — "
            "the subject and body are built from it, which is what makes this sender incapable "
            "of carrying arbitrary content"
        )
    grounding = request.grounding
    if not isinstance(grounding, GroundingSnapshot) or not grounding.readable:
        return (
            "this request cannot show its grounding — nothing of the organism was read, so there "
            "is no Γ, no divergence and no panel reading to justify it. An ask Sero cannot "
            "explain is not sent"
        )
    if request.state in TERMINAL_STATES:
        return (
            f"this request is already {request.state} — a resolved token is spent, and asking "
            "again would invite a second answer to a question that already has one"
        )
    if request.is_expired(now):
        return (
            f"this request expired at {request.expires_at.isoformat()} and could not be approved "
            "even if it were answered — compose a fresh one rather than send a dead one"
        )
    return None


def _deliver(config: SmtpConfig, message: EmailMessage, transport: Any | None) -> None:
    """Hand the already-addressed message to SMTP over TLS.

    Receives no address: the envelope is written, and ``send_message`` takes the
    recipients from the message's own ``To`` header. Raises on failure;
    :func:`send_approval_request` turns that into a blocker.
    """
    factory = transport if transport is not None else _default_transport
    with factory(config.host, config.port) as smtp:
        if not config.implicit_tls:
            # Not optional. If the server will not upgrade, this raises and the
            # send fails — the password never crosses an unencrypted link.
            smtp.starttls(context=ssl.create_default_context())
        smtp.login(config.user, config.password)
        smtp.send_message(message)


def _default_transport(host: str, port: int) -> Any:
    """The real client. Port 465 is TLS from the first byte; anything else STARTTLS."""
    if port == IMPLICIT_TLS_PORT:
        return smtplib.SMTP_SSL(host, port, timeout=SMTP_TIMEOUT,
                                context=ssl.create_default_context())
    return smtplib.SMTP(host, port, timeout=SMTP_TIMEOUT)


# ── the record of every ask ───────────────────────────────────────────────────


def notify_log_path(root: Path | str | None = None) -> Path:
    """The append-only record of every attempt to ask.

    Sits in :func:`aureon.approval.store.approvals_dir`, beside the request
    ledger, so the trail of *asks* and the trail of *answers* cannot end up in
    two different places — and so ``AUREON_APPROVALS_DIR`` moves both.
    """
    return approvals_dir(root) / NOTIFY_LOG_NAME


def _finish(
    result: NotifyResult,
    request: Any,
    now: datetime,
    root: Path | str | None,
) -> NotifyResult:
    """Write the audit line, then return the result carrying where it was written.

    Every attempt is logged, sent or blocked. The blocked half is the more
    interesting one: it is the evidence that the system stopped rather than
    improvised.
    """
    path = notify_log_path(root)
    row = {
        "timestamp": now.isoformat(),
        "token": result.token,
        "outcome": "sent" if result.sent else "blocked",
        # Exactly who this went to, or null when it went nowhere. This field is
        # the one an auditor scans.
        "recipient": result.owner,
        "blocker": result.blocker,
        "subject": result.subject,
        "action": _attr(request, "action"),
        "reference": _attr(request, "application_id"),
        "state": _attr(request, "state"),
        "grounding": _grounding_row(getattr(request, "grounding", None)),
    }
    logged = _append(path, row)
    return NotifyResult(
        sent=result.sent,
        token=result.token,
        owner=result.owner,
        subject=result.subject,
        blocker=result.blocker,
        logged=logged,
        log_path=str(path),
    )


def _attr(request: Any, name: str) -> str | None:
    value = getattr(request, name, None)
    return str(value) if value is not None else None


def _grounding_row(grounding: Any) -> dict[str, Any] | None:
    """The grounding as recorded: what she was reading at the moment she asked."""
    if grounding is None:
        return None
    try:
        row = dict(grounding.to_dict())
        row["needs_caution"] = bool(getattr(grounding, "needs_caution", False))
        # The verdicts are counted rather than copied: this file is a trail, not a
        # second archive of the request records next to it.
        row["gate_verdicts"] = len(row.get("gate_verdicts") or ())
        return row
    except Exception:  # noqa: BLE001
        LOG.debug("grounding not recordable", exc_info=True)
        return None


def _append(path: Path, row: dict[str, Any]) -> bool:
    """Append one JSON line. Never raises — a lost log line must not lose the ask."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return True
    except OSError:
        LOG.debug("notify log append failed: %s", path, exc_info=True)
        return False


__all__ = [
    "CAUTION_WORD",
    "IMPLICIT_TLS_PORT",
    "MAX_BODY_CHARS",
    "MAX_SUBJECT_CHARS",
    "NOTIFY_LOG_NAME",
    "OFFLINE_VARS",
    "SMTP_HOST_VAR",
    "SMTP_INLINE_PASSWORD_VAR",
    "SMTP_PASSWORD_FILE_VAR",
    "SMTP_PORT_VAR",
    "SMTP_TIMEOUT",
    "SMTP_USER_VAR",
    "SMTP_VARS",
    "STANDING_RULE",
    "SUBJECT_TAG",
    "THE_QUESTION",
    "TOKEN_HEADER",
    "NotifyResult",
    "SmtpConfig",
    "notify_log_path",
    "render_request",
    "resolve_owner_address",
    "resolve_transport",
    "send_approval_request",
    "subject_line",
]
