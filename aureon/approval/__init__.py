"""The final approval gate — Sero asks, Gary answers, and his answer is the gate.

Gary's design, in his words: *"the only thing this system needs Gary for is send
a message — at the last approval gate, send him a summary via email and say
'Gary am I ok to go ahead', and Gary replies to the email and says yes or no, and
that is the final approval gate."*

His standing rule, from his own War Room sheet: *"No external submission, legal
representation, filing, payment, or email send should happen without Gary
approval."* This package does not carve an exception out of that rule — it is the
mechanism by which the rule is kept. ``aureon.gates.switchboard`` returns HOLD at
the final gate because no automatic executor exists for a submission, a filing or
a payment. Human approval is not removed here; it is made **asynchronous**.

The shape of it:

    compose_request(action, dossier=...)   →  the question, with its grounding
    save(request)                          →  state/approvals/<token>.json
    (delivery, elsewhere: one address, resolved from config, never passed in)
    check_for_replies(connector, ...)      →  read the mailbox, read-only
    parse_reply(body, token=...)           →  APPROVED / DECLINED / UNCLEAR / IGNORED
    resolve(token, state, evidence)        →  single-use, expiry-bound, on disk

The six properties are structural, not checks bolted on afterwards:

1. **Owner-locked recipient** — no callable in this package accepts a recipient,
   and :class:`ApprovalRequest` has no field for one. The single address comes
   from :func:`aureon.approval.config.owner_address`, which takes no arguments. A
   sender that cannot address a funder cannot accidentally submit to one.
2. **Token-scoped** — 43 characters of ``secrets`` entropy bind one answer to one
   request. :class:`~aureon.approval.reply.ReplyVerdict` cannot exist in a
   resolving state without a token, so a bare "yes" matches nothing.
3. **Single use** — ``save`` claims a token with ``O_EXCL``; ``resolve`` refuses a
   token already resolved. A replayed reply is inert.
4. **Expiry** — ``resolve`` stamps a late answer EXPIRED and discards it. An old
   yes cannot authorise a fresh action.
5. **Sender verification** — only the owner's address, parsed properly and
   compared case-insensitively; anyone else is recorded IGNORED.
6. **Explicit intent** — unambiguous words only, read from what Gary typed with
   quoted text stripped. Ambiguity, emptiness and silence are never approval.

And the organism's own honesty: the request carries the coherence Γ, the field
divergence, the nine-node Auris consensus with its evidence ratio, and the gate
verdicts that reached the hold. **Sero asking while divided looks different from
Sero asking while confident**, and a request whose grounding cannot be read is
never created at all.

Nothing in this package executes anything. It records a decision; the
irreversible step stays a separate, deliberate act.
"""

from aureon.approval.compose import compose_request
from aureon.approval.config import is_owner, owner_address
from aureon.approval.reply import ReplyVerdict, check_for_replies, parse_reply
from aureon.approval.schemas import ApprovalRequest, ApprovalState, GroundingSnapshot
from aureon.approval.store import expire_overdue, load, open_requests, resolve, save

__all__ = [
    "ApprovalRequest",
    "ApprovalState",
    "GroundingSnapshot",
    "ReplyVerdict",
    "check_for_replies",
    "compose_request",
    "expire_overdue",
    "is_owner",
    "load",
    "open_requests",
    "owner_address",
    "parse_reply",
    "resolve",
    "save",
]
