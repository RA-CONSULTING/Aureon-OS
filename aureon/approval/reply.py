"""Reading Gary's answer — the one sentence in this system that authorises an act.

Everything else Aureon does, it does on its own evidence. This module is the
exception: it is where a human being's word enters the machine. The owner's rule
is the reason it exists at all, quoted from his own War Room sheet:

    "No external submission, legal representation, filing, payment, or email
    send should happen without Gary approval."

And his design for satisfying it:

    "at the last approval gate, send him a summary via email and say 'Gary am I
    ok to go ahead', and Gary replies to the email and says yes or no, and that
    is the final approval gate."

So the approval is asynchronous, not absent. :mod:`aureon.gates.switchboard`
returns HOLD at the final gate because no automatic hand exists for a submission;
this package is how that hold gets resolved by the only hand that may resolve it.
Which makes *this file* the security surface. Everything here is written to fail
closed: every unclear, malformed, unverifiable or unexpected input produces a
non-approval, and no path in this module can produce APPROVED by accident.

**What this module does and does not decide.** It reads. It answers four
questions about one message — is it from the owner, which request does it
reference, what did he actually say, and is any of that unambiguous — and returns
a :class:`ReplyVerdict`. It does not record the answer, does not enforce
single-use, and does not check expiry; those are the pending-request store's job,
because they are facts about a *request's history* rather than about a message.
A verdict from here is a reading, not a resolution.

The four structural properties this file is responsible for:

**Token-scoped (property 2).** An approval is bound to exactly one request. The
token must literally appear in the message, matched as a whole token with
non-token characters either side, so a token that is a prefix or substring of
another token cannot be mistaken for it. A bare "yes" referencing nothing matches
nothing. The binding is enforced by the type: :class:`ReplyVerdict` refuses to
exist in an APPROVED or DECLINED state without a matched token, so "approved, but
of what?" is unrepresentable rather than merely unlikely.

**Sender verification (property 5).** ``From`` is parsed properly and compared on
the *address*, never on the display name. That distinction is the whole attack:
``"gary@aureon.com" <attacker@evil.com>`` puts the owner's address in the part of
the header a human reads and a stranger's in the part the mail actually came
from. Worse, :func:`email.utils.parseaddr` alone does **not** stop it — an
*unquoted* ``gary@x.com <attacker@evil.com>`` parses as two addresses and
``parseaddr`` hands back the first, which is the display text. So this module
uses :func:`email.utils.getaddresses` and requires the header to carry exactly
one address (see :func:`sender_of`). A ``From`` with two addresses in it is not a
sender this code will vouch for.

**What this layer cannot do, stated plainly.** It verifies which address a
message *claims* to be from; it cannot verify that the claim is true. SPF, DKIM
and DMARC are what authenticate that, they are enforced by Gmail before the
message is ever in the mailbox, and their results are not among the fields
:class:`~aureon.connectors.schemas.GmailMessage` carries — so no amount of parsing
here can add them. A ``From`` header that has been forged past Gmail's own checks
would read as the owner. The second lock is the token: it is 43 characters of
:mod:`secrets` entropy that exist only in the owner's mailbox, so an attacker who
cannot read that mailbox cannot reference the request even with a forged sender,
and a reply that references nothing resolves nothing.

**Explicit intent (property 6).** Only unambiguous vocabularies count.
Approval and refusal both present, neither present, or nothing but a quoted copy
of Sero's own request — all UNCLEAR, which is not approval. Silence is never
approval, because silence produces no message and therefore no verdict at all.

**Never a quoted echo.** Sero's own request says "am I ok to go ahead" — a phrase
that is itself in the approval vocabulary — and her subject line says it too:
``[AUREON approval <token>] am I ok to go ahead — submit``. Every mail client
quotes the body back and keeps the subject. So intent is read *only* from the
lines Gary himself wrote: quoted lines and the signature block are removed, and
the subject is never consulted for intent at all. The token, by contrast, is
looked for in the body *and* the subject, quotes included — an echoed token is
legitimate evidence of *which request* the reply is about, and the subject is how
it survives a reply from a phone that quoted nothing. Evidence of which; never
evidence of consent.

**Read-only.** The mailbox is reached through :class:`~aureon.connectors.gmail.GmailConnector`,
which holds a ``gmail.readonly`` scope and has no ``send``, ``draft``, ``reply``,
``modify`` or ``trash`` method to call. :func:`check_for_replies` touches two
methods of it — ``search_threads`` and ``read_thread`` — and nothing else. No
function in this module accepts a recipient, an address to write to, or a body to
send; there is no outbound path here to misuse. ``owner_address`` is the one
address that crosses this module's boundary and it travels *inbound only*: it is
the yardstick a sender is measured against, never a destination anything is
handed to.

Types are shared with the rest of the package rather than re-declared:
:class:`~aureon.approval.schemas.ApprovalState` is the vocabulary of answers and
:func:`~aureon.approval.schemas.is_token` is the one definition of a token's
shape, so the reader and the store cannot drift apart about what either means.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, replace
from email.utils import getaddresses
from functools import lru_cache
from html import unescape
from typing import Any, Iterable

from aureon.approval.schemas import ApprovalState, coerce_state, is_token

LOG = logging.getLogger("aureon.approval.reply")

# ── the four answers a message can be ───────────────────────────────────────
# Aliases into the package's own vocabulary (``ApprovalState`` is a ``str`` enum,
# so these compare equal to their plain names and can be written straight into a
# record). PENDING and EXPIRED are deliberately absent: they are facts about a
# request's history, which no reading of a *message* can establish.
#
# APPROVED / DECLINED are resolutions: the owner answered this exact request.
# UNCLEAR is a real reading that resolves nothing — the message existed but did
# not unambiguously say either thing, or said it without binding it to a request.
# IGNORED is a message this module refuses to read as an answer at all, because
# it did not come from the owner.
APPROVED = ApprovalState.APPROVED
DECLINED = ApprovalState.DECLINED
UNCLEAR = ApprovalState.UNCLEAR
IGNORED = ApprovalState.IGNORED

STATES: frozenset[ApprovalState] = frozenset({APPROVED, DECLINED, UNCLEAR, IGNORED})

# The only two states that authorise the store to close a request. Everything
# else leaves it open, which is how UNCLEAR and IGNORED avoid burning a token
# that Gary has not answered yet — see ``schemas.OPEN_STATES``.
RESOLVING: frozenset[ApprovalState] = frozenset({APPROVED, DECLINED})

# The alphabet ``secrets.token_urlsafe`` draws from, and therefore the alphabet
# ``schemas.TOKEN_RE`` allows. Used to build the boundary assertions that make
# token matching exact — a character from this set on either side of a match
# means the match is part of a *different, longer* token.
TOKEN_CHARS = "A-Za-z0-9_-"

# The tag the sender writes into the subject line and the body, carrying the
# token through the round trip so Gary never has to copy anything:
#
#     [AUREON approval <token>] am I ok to go ahead — submit
#
# Declared here rather than imported so this module has no dependency on the
# composer, and cross-checked against ``compose.SUBJECT_TAG`` and
# ``notify.SUBJECT_TAG`` in ``tests/approval/test_reply.py`` — if a sender ever
# changes the shape it writes, that test fails rather than the reader silently
# stopping recognising its own requests.
SUBJECT_TAG = "AUREON approval"

# Bodies are truncated before any regex touches them. The Gmail connector
# already caps a body at 100k, so this is the second line of defence against a
# pathological message rather than the first.
MAX_BODY_CHARS = 200_000

# RFC 5322 caps a header line at 998 characters. Anything longer is not a From
# header any real mail agent produced.
MAX_HEADER_CHARS = 998

# Bounds on one sweep of the mailbox. A search that would return more than this
# is reported as far as it goes rather than growing without limit — a verdict
# list is an audit record held in memory, not a stream.
SEARCH_LIMIT = 10           # threads per token
MAX_MESSAGES_PER_THREAD = 100
MAX_VERDICTS = 200


# ── vocabularies ────────────────────────────────────────────────────────────
# Deliberately small. Every phrase added here is a new way for something to be
# read as consent, so the bar for inclusion is that a reasonable person could not
# write it while meaning the opposite.
#
# The four the owner specified are the core: "yes", "approved", "go ahead",
# "proceed". The rest are inflections of those.
#
# Two omissions are deliberate. Bare "ok" / "okay" is *not* here: it is filler as
# often as it is consent ("ok so what about the deadline"), and the cost of
# leaving it out is one extra round trip while the cost of putting it in is a
# submission Gary did not authorise. The noun "approval" is not here either — it
# appears in the subject line of Sero's own request, and a vocabulary that
# matched it would read an echo of the question as its answer.
APPROVE_PHRASES: tuple[str, ...] = (
    "yes",
    "yes please",
    "yep",
    "yeah",
    "yup",
    "approve",
    "approved",
    "i approve",
    "go ahead",
    "you are ok to go ahead",
    "ok to go ahead",
    "ok to go",
    "ok to proceed",
    "ok to send",
    "proceed",
    "go for it",
    "green light",
    "send it",
    "affirmative",
    "confirmed",
)

# Sero's own voice. Text carrying any of these is *her* request coming back —
# forwarded, echoed by a client that quoted nothing, or pasted — and it is
# therefore not an answer to anything, whatever vocabulary it happens to contain.
#
# This exists because the composer's defence, on its own, is contingent. Its body
# quotes both vocabularies at Gary ("reply yes / approved / go ahead" and "no /
# stop / hold / declined") so that an echo reads as ambiguous; but that only holds
# for as long as it keeps quoting both. A body that lost its refusal line would
# echo back as pure approval. Keying on the question itself removes the
# dependency: the reader recognises her question in his mouth and refuses it,
# without needing the composer to keep an accident-preventing sentence in place.
#
# ``tests/approval/test_reply.py`` cross-checks these against ``compose.QUESTION``
# and ``notify.THE_QUESTION``, so rewording the question fails the suite rather
# than silently reopening the hole.
ECHO_MARKERS: tuple[str, ...] = (
    "am i ok to go ahead",
    "reply yes",
    "reply with yes",
    "no automatic executor",
    "standing rule",
)

DECLINE_PHRASES: tuple[str, ...] = (
    "no",
    "nope",
    "no thanks",
    "no go",
    "not yet",
    "not now",
    "do not",
    "don't",
    "dont",
    "stop",
    "hold",
    "hold off",
    "hold on",
    "on hold",
    "wait",
    "pause",
    "decline",
    "declined",
    "deny",
    "denied",
    "reject",
    "rejected",
    "refuse",
    "refused",
    "negative",
    "cancel",
    "cancelled",
    "abort",
    "veto",
)


# ── the verdict ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ReplyVerdict:
    """What one message said, and which request (if any) it said it about.

    The invariant in :meth:`__post_init__` is the point of the type, and it is
    property 3's foundation as much as property 2's: **a resolving state cannot
    exist without a token, and a non-resolving state cannot carry one.** So
    ``matched_token is not None`` is exactly equivalent to "this verdict closes
    that request", and a caller cannot read a token off an UNCLEAR verdict and
    close something with it. An approval that does not know what it approved is
    not merely rejected here — it cannot be constructed.

    ``intent_phrase`` is the words that were recognised, kept even on a verdict
    that resolves nothing, because "he said yes but referenced no request" is a
    materially different audit record from "he said nothing recognisable".

    ``sender`` is the parsed *address* only, never the display name — a display
    name is attacker-controlled text and does not belong in a log line.
    """

    state: ApprovalState
    matched_token: str | None
    intent_phrase: str | None
    reason: str
    message_id: str | None = None
    sender: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", coerce_state(self.state))
        if self.state not in STATES:
            # PENDING and EXPIRED are states of a *request*, not readings of a
            # message. Nothing here can establish either, so nothing here may
            # claim one.
            raise ValueError(f"{self.state} is not something a reply can be read as")
        if self.state in RESOLVING:
            if not isinstance(self.matched_token, str) or not self.matched_token.strip():
                raise ValueError(
                    f"a {self.state} verdict must name the token it resolves — "
                    "an approval that cannot say what it approved is not an approval"
                )
        elif self.matched_token is not None:
            raise ValueError(
                f"a {self.state} verdict resolves nothing and must not carry a token"
            )
        if not self.reason.strip():
            raise ValueError("a verdict must state its reason")

    @property
    def resolves(self) -> bool:
        """True when this verdict closes its request (approved or declined)."""
        return self.state in RESOLVING

    @property
    def is_approval(self) -> bool:
        """True only for a token-bound APPROVED. The single question callers ask."""
        return self.state == APPROVED and bool(self.matched_token)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "matched_token": self.matched_token,
            "intent_phrase": self.intent_phrase,
            "reason": self.reason,
            "message_id": self.message_id,
            "sender": self.sender,
            "resolves": self.resolves,
            "is_approval": self.is_approval,
        }


# ── tokens ──────────────────────────────────────────────────────────────────

# Quoted-printable soft line break. A mail transport may insert one *inside* a
# 43-character token, and "=\n" is not part of the token, so it is removed before
# matching. Without this a perfectly good approval silently fails to bind.
_SOFT_BREAK = re.compile(r"=\r?\n")


def token_or_none(token: Any) -> str | None:
    """A syntactically usable request token, or None. Never raises.

    Shape is decided by :func:`aureon.approval.schemas.is_token` — one definition
    for the whole package, so the store and the reader cannot disagree about what
    a token is. It refuses anything that is not a plausible
    ``secrets.token_urlsafe`` value: wrong type, empty, too short to be
    unguessable, or carrying characters the generator cannot produce. A refused
    token matches nothing, which means a caller that passes rubbish gets no
    approval rather than a loose match.
    """
    if not isinstance(token, str):
        return None
    stripped = token.strip()
    return stripped if is_token(stripped) else None


@lru_cache(maxsize=512)
def _exact_pattern(token: str) -> re.Pattern[str]:
    """The token, bounded by non-token characters on both sides.

    The lookarounds are what make property 2's "exact" real. A plain substring
    search for token ``AAAABBBB`` would happily match inside ``AAAABBBBCCCC`` —
    i.e. one request's reply would resolve a different request whose token merely
    shares a prefix. The assertions refuse a match with ``[A-Za-z0-9_-]`` on
    either side, so a token only matches when it stands alone.
    """
    return re.compile(rf"(?<![{TOKEN_CHARS}]){re.escape(token)}(?![{TOKEN_CHARS}])")


@lru_cache(maxsize=512)
def _wrapped_pattern(token: str) -> re.Pattern[str]:
    """The same token, tolerating whitespace inserted between its characters.

    Mail clients hard-wrap long lines, and a 43-character token is the longest
    "word" in the message — exactly the thing that gets broken across a line.
    Allowing whitespace *between* characters recovers those without loosening the
    ends: the boundary assertions still apply to the first and last character, so
    a prefix of a longer token still cannot match. Only tried when the plain
    search fails, so the ordinary case pays nothing for it.
    """
    body = r"\s*".join(re.escape(ch) for ch in token)
    return re.compile(rf"(?<![{TOKEN_CHARS}]){body}(?![{TOKEN_CHARS}])")


# The tag as it appears in a subject line or a body, with the token inside it.
# ``\s+`` between the words so a client that re-wrapped the subject still matches,
# and the token's own shape re-stated here so the tag cannot yield something the
# rest of the package would refuse to call a token.
# The candidate run of token characters is captured loosely and then validated by
# ``token_or_none``, so this pattern cannot drift out of step with
# ``schemas.TOKEN_RE`` — there is one definition of a token and it is not here.
_TAG_RE = re.compile(
    r"\[\s*" + r"\s+".join(re.escape(word) for word in SUBJECT_TAG.split())
    + rf"\s+([{TOKEN_CHARS}]+)\s*\]",
    re.IGNORECASE,
)


def find_token(text: Any) -> str | None:
    """The token a subject line or body *claims*, or None. Authorises nothing.

    Reads the shape the sender writes — ``[AUREON approval <token>]`` — from a
    subject like ``Re: [AUREON approval Ky7d…] am I ok to go ahead — submit``.
    That is how the token survives a reply from a phone that quoted no body at
    all.

    This is a claim, not a credential. It says which request a message *says* it
    is about; whether such a request exists, is still open and has not already
    been answered is the store's to decide (properties 3 and 4). Nothing here
    treats a found token as authority — :func:`check_for_replies` only ever
    matches against tokens the caller already knows are pending.
    """
    if not isinstance(text, str) or not text:
        return None
    match = _TAG_RE.search(_SOFT_BREAK.sub("", text[:MAX_BODY_CHARS]))
    return token_or_none(match.group(1)) if match else None


def references_token(body: Any, token: Any) -> bool:
    """Does this text carry that exact token? Case-sensitive, whole-token only.

    Case-sensitive on purpose: ``token_urlsafe`` is case-significant, so folding
    case would merge distinct tokens into one match space.
    """
    tok = token_or_none(token)
    if tok is None or not isinstance(body, str) or not body:
        return False
    text = _SOFT_BREAK.sub("", body[:MAX_BODY_CHARS])
    if _exact_pattern(tok).search(text):
        return True
    return bool(_wrapped_pattern(tok).search(text))


# ── separating Gary's words from the quoted question ────────────────────────

_QUOTED_LINE = re.compile(r"^\s*>")

# Where the reply stops and the machinery of the mail client begins. Everything
# from the first of these onward is discarded, not just the marker line, because
# what follows is Sero's own request text — the request that asks "am I ok to go
# ahead", a phrase in the approval vocabulary. Cutting is the conservative
# direction: text lost below a signature can only ever *reduce* the chance of
# reading consent, and a reply whose consent got cut reads as UNCLEAR and gets
# asked again.
_CUT_MARKERS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*--\s*$"),                                       # RFC 3676 sig delimiter
    re.compile(r"^\s*_{5,}\s*$"),                                    # Outlook's divider rule
    re.compile(r"^\s*-{3,}\s*original message\s*-{3,}\s*$", re.I),   # Outlook / older clients
    re.compile(r"^\s*begin forwarded message\s*:", re.I),
    re.compile(r"^\s*on\b.*\bwrote\s*:\s*$", re.I),                  # Gmail attribution
    re.compile(r"^\s*wrote\s*:\s*$", re.I),                          # ...when it wrapped
    re.compile(r"^\s*on\b.{0,300}<[^>]+@[^>]+>\s*$", re.I),          # ...its first half
    re.compile(r"^\s*from\s*:\s", re.I),                             # quoted header block
    re.compile(r"^\s*sent\s+from\s+my\b", re.I),                     # phone signatures
    re.compile(r"^\s*get\s+outlook\s+for\b", re.I),
)


# An HTML-only reply. The Gmail connector prefers ``text/plain`` and most clients
# send one, but Outlook and some phones do not, and then the body arrives as
# markup with the quoted request inside a ``<blockquote>``.
#
# The quote is *cut at its opening tag*, not excised as a balanced region. That is
# deliberate: nested blockquotes are the norm in a long thread, and a non-greedy
# ``<blockquote>.*?</blockquote>`` would leave the outer quote's tail behind as if
# Gary had written it — which is precisely how a stray "go ahead" from Sero's own
# question could be read as his answer. A mail quote is always *below* the reply,
# so everything from the first container down is the machine's text.
_HTML_HINT = re.compile(r"<(?:br|div|p|blockquote|span|table|html|body)\b[^>]*>", re.I)
_HTML_CUT = re.compile(
    r"<blockquote\b|<div[^>]*(?:gmail_quote|divRplyFwdMsg|appendonsend)", re.I
)
_HTML_DROP = re.compile(r"<(script|style)\b.*?</\1\s*>", re.I | re.S)
_HTML_BREAK = re.compile(r"<(?:br|/p|/div|/tr|/li|hr)\b[^>]*>", re.I)
_HTML_TAG = re.compile(r"<[^>]*>")


def _from_html(markup: str) -> str:
    """Markup reduced to the text above the first quote container.

    Entities are unescaped *last* so that a quoted line encoded as ``&gt; yes``
    becomes ``> yes`` before the line-by-line pass runs, and is therefore dropped
    as the quote it is rather than read as an answer.
    """
    text = _HTML_DROP.sub(" ", markup)
    cut = _HTML_CUT.search(text)
    if cut:
        text = text[: cut.start()]
    text = _HTML_BREAK.sub("\n", text)
    return unescape(_HTML_TAG.sub(" ", text))


def strip_quoted(body: Any) -> str:
    """The lines Gary actually typed: no quotes, nothing below the signature.

    This is the single most important function in the file for property 6. Sero's
    request contains its own approval phrase and its own token; every client
    quotes it back verbatim. If intent were read from the whole body, Sero would
    approve herself on the strength of her own question. So intent is read only
    from what survives here — and if that is nothing, the answer is UNCLEAR.

    Handles both shapes a body can arrive in: ``text/plain``, where the quote is
    marked with ``>`` and introduced by an attribution line, and ``text/html``,
    where it sits in a ``<blockquote>``. In both, the cut is conservative — losing
    text can only ever produce UNCLEAR, and UNCLEAR is a question asked again.
    """
    if not isinstance(body, str):
        return ""
    text = body[:MAX_BODY_CHARS]
    if _HTML_HINT.search(text):
        text = _from_html(text)
    kept: list[str] = []
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if _QUOTED_LINE.match(line):
            continue
        if any(marker.match(line) for marker in _CUT_MARKERS):
            break
        kept.append(line)
    return "\n".join(kept).strip()


# ── intent ──────────────────────────────────────────────────────────────────

# Curly apostrophes, backticks and the modifier-letter apostrophe all become the
# plain one, so "don’t" typed on a phone matches the same pattern as "don't".
_APOSTROPHES = str.maketrans({"‘": "'", "’": "'", "ʼ": "'", "`": "'"})
_NOT_WORD = re.compile(r"[^a-z0-9']+")


def _normalise(text: str) -> str:
    """Lower-cased, punctuation flattened to single spaces, apostrophes kept.

    Flattening punctuation is what lets one pattern match "yes", "Yes!", "yes."
    and "yes," — and lets "go-ahead" match "go ahead". Apostrophes survive
    because "don't" is a refusal and "dont" is a different spelling of it, not a
    different word.
    """
    lowered = text.lower().translate(_APOSTROPHES)
    return " ".join(_NOT_WORD.sub(" ", lowered).split())


@lru_cache(maxsize=256)
def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    """One phrase, bounded so it cannot match inside a longer word.

    Custom boundaries rather than ``\\b`` because an apostrophe is a non-word
    character to ``re``: ``\\bno\\b`` would match the "no" in "no't". These
    assertions treat letters, digits and apostrophes alike as continuation, so
    "no" does not match "nope" and "yes" does not match "yesterday".
    """
    return re.compile(rf"(?<![a-z0-9']){re.escape(phrase)}(?![a-z0-9'])")


# Longest first, so the reason records "hold off" rather than the "hold" inside
# it, and "not yet" rather than a bare "no" that is not even there.
_APPROVE_ORDER: tuple[str, ...] = tuple(sorted(APPROVE_PHRASES, key=len, reverse=True))
_DECLINE_ORDER: tuple[str, ...] = tuple(sorted(DECLINE_PHRASES, key=len, reverse=True))
_ECHO_ORDER: tuple[str, ...] = tuple(sorted(ECHO_MARKERS, key=len, reverse=True))


def _first_phrase(normalised: str, ordered: tuple[str, ...]) -> str | None:
    for phrase in ordered:
        if _phrase_pattern(phrase).search(normalised):
            return phrase
    return None


def _classify(own_words: str) -> tuple[ApprovalState, str | None, str]:
    """``(state, phrase, reason)`` for text already stripped of quotes.

    Never returns APPROVED or DECLINED on ambiguity. The two vocabularies are
    both searched, always — deciding on the first hit would let "yes but hold
    off" read as consent because "yes" came first.

    Sero's own question is checked for first: text that repeats it is her request
    coming back, not Gary answering it, and it must not be classified at all.
    """
    normalised = _normalise(own_words)

    echo = _first_phrase(normalised, _ECHO_ORDER)
    if echo:
        return UNCLEAR, None, (
            f"the text repeats Sero's own words ({echo!r}) — it is the request coming "
            "back, not an answer to it"
        )

    approve = _first_phrase(normalised, _APPROVE_ORDER)
    decline = _first_phrase(normalised, _DECLINE_ORDER)

    if approve and decline:
        return UNCLEAR, None, (
            f"both approval ({approve!r}) and refusal ({decline!r}) are present — "
            "an ambiguous answer is not consent"
        )
    if approve:
        return APPROVED, approve, f"{approve!r} in Gary's own words"
    if decline:
        return DECLINED, decline, f"{decline!r} in Gary's own words"
    return UNCLEAR, None, "no recognised approval or refusal in the reply — nothing to act on"


def read_intent(text: Any) -> ApprovalState:
    """What a message says, ignoring which request it says it about.

    APPROVED, DECLINED or UNCLEAR — never IGNORED, which is a fact about a sender
    rather than about words. Quoted lines and the signature are stripped first, so
    this is safe to hand a whole raw body: an echo of Sero's own request reads as
    UNCLEAR, because her request quotes *both* vocabularies at Gary ("reply yes /
    approved / go ahead" and "no / stop / hold / declined") and a text containing
    both is ambiguous by definition. :mod:`aureon.approval.compose` relies on
    exactly that.

    Intent alone authorises nothing. :func:`parse_reply` is the function that can
    resolve a request, and it will not do so without a token.
    """
    if not isinstance(text, str) or not text.strip():
        return UNCLEAR
    own_words = strip_quoted(text)
    if not own_words:
        return UNCLEAR
    return _classify(own_words)[0]


# ── parsing one reply ───────────────────────────────────────────────────────


def parse_reply(body: Any, *, token: Any, subject: Any = None) -> ReplyVerdict:
    """Read one message as an answer to one request. Never raises.

    Returns APPROVED or DECLINED only when **both** halves hold: the token
    appears in the message, and the lines Gary wrote himself say one thing
    unambiguously. Everything else is UNCLEAR, which authorises nothing.

    The two halves are looked for in deliberately different places, and that
    asymmetry is the design:

    *The token* is searched for across the whole body — quoted text included —
    and in ``subject``. A quote is how a mail client says "this reply is about
    that message", and the subject is how the token survives a reply from a phone
    that quoted nothing at all (the sender writes ``[AUREON approval <token>]``
    into it, and a reply keeps it).

    *Intent* is searched for only in :func:`strip_quoted`'s output, and **never**
    in the subject. Sero's own subject line reads "am I ok to go ahead" and her
    body says "go ahead" in the instructions; both come back on every reply.
    Reading either as consent would be the machine approving itself.

    ``token`` and ``subject`` are keyword-only, so no call site can transpose
    them with the body or with each other.
    """
    tok = token_or_none(token)
    if tok is None:
        # A caller with no usable token cannot be asking about a real request.
        # Fail closed and say so, rather than raise: this runs inside a polling
        # loop, and a loop that dies on a bad argument stops watching the
        # mailbox, which is its own kind of failure.
        LOG.debug("parse_reply called without a usable token")
        return ReplyVerdict(
            UNCLEAR, None, None,
            "no usable request token was supplied — nothing could be approved",
        )

    if not isinstance(body, str) or not body.strip():
        return ReplyVerdict(
            UNCLEAR, None, None,
            "empty reply — silence and an empty message are never consent",
        )

    own_words = strip_quoted(body)
    bound = references_token(body, tok) or references_token(subject, tok)

    if not own_words:
        return ReplyVerdict(
            UNCLEAR, None, None,
            "nothing but quoted text and signature — the reply contains no words of Gary's own"
            + ("" if bound else "; and it references no request token"),
        )

    state, phrase, reason = _classify(own_words)

    if state is UNCLEAR:
        return ReplyVerdict(UNCLEAR, None, phrase, reason)

    if not bound:
        # He answered something. It is not knowable *what*, so it resolves
        # nothing — this is the stray-or-stale "yes" that property 2 exists to
        # stop authorising an action it never saw.
        return ReplyVerdict(
            UNCLEAR, None, phrase,
            f"{phrase!r} was said but the reply references no request token — "
            "an answer that names no request approves no request",
        )

    return ReplyVerdict(state, tok, phrase, f"{reason}, bound to this request's token")


# ── who sent it ─────────────────────────────────────────────────────────────

# RFC 5322 header folding: a line break followed by whitespace is a continuation
# of the same header and unfolds to a single space. Any line break that is *not*
# folding is a header-injection attempt, and :func:`sole_address` refuses it.
_UNFOLD = re.compile(r"\r?\n[ \t]+")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


def sender_of(from_header: Any) -> str | None:
    """The one address a ``From`` header carries, lower-cased, or None.

    This is the function :func:`aureon.approval.config.is_owner` expects to be
    handed a bare address by: ``is_owner(sender_of(header))`` is the
    configuration-driven path, and :func:`sender_is_owner` is the explicit one
    used by tests and by callers that already hold the owner address.

    "Exactly one" is the security property, not a convenience. These are all real
    header shapes and all of them must fail:

    ==========================================  =============================
    header                                      why it is refused
    ==========================================  =============================
    ``"gary@x.com" <attacker@evil.com>``        one address, and it is not the
                                                owner's — the owner's address is
                                                display text
    ``gary@x.com <attacker@evil.com>``          *two* addresses. ``parseaddr``
                                                returns ``gary@x.com`` here,
                                                which is why this module does
                                                not use ``parseaddr``
    ``Gary <gary@x.com>, attacker@evil.com``    two addresses
    ``Gary <gary@x.com>\\nBcc: evil@evil.com``   two addresses, via injection
    ==========================================  =============================

    A ``From`` header with more than one address in it is not a header a real
    sender produced, so refusing it costs nothing and closes the whole class.

    An RFC 5322 *comment* is not a second address: ``"Gary" <gary@x.com>
    (someone@else.com)`` is one address — ``gary@x.com`` — with a parenthesised
    remark after it, and that is who the mail is from. It reads as the owner
    because it *is* the owner's address; putting a string in a comment changes
    nothing about the sender. Forging the address itself is a different problem,
    and one this layer cannot solve — see the module docstring.
    """
    if not isinstance(from_header, str):
        return None
    header = _UNFOLD.sub(" ", from_header)
    if "\n" in header or "\r" in header or _CONTROL.search(header):
        return None  # a line break that is not folding, or a control character
    if not header.strip() or len(header) > MAX_HEADER_CHARS:
        return None
    try:
        pairs = getaddresses([header])
    except Exception:  # noqa: BLE001 — a malformed header is "no sender", not a crash
        LOG.debug("From header would not parse", exc_info=True)
        return None

    addresses = [
        addr.strip().lower()
        for _display, addr in pairs
        if isinstance(addr, str) and addr.strip()
    ]
    if len(addresses) != 1:
        return None

    address = addresses[0]
    if address.count("@") != 1 or any(ch.isspace() for ch in address):
        return None
    local, _, domain = address.partition("@")
    if not local or not domain:
        return None
    return address


def sender_is_owner(from_header: Any, owner_address: Any) -> bool:
    """Did this message genuinely come from the owner's address? Never raises.

    Compares the parsed **address** against the configured owner address,
    case-insensitively. The display name is never consulted, and a header
    carrying more than one address is refused outright — see :func:`sender_of`
    for the attacks that makes structurally impossible.

    ``owner_address`` is an inbound yardstick, not a destination: it is the
    address a message is checked *against*, and nothing in this module can send
    to it.

    False on anything it cannot verify: no owner configured, unparseable header,
    wrong type. An unverified sender is not the owner.
    """
    owner = _owner_or_none(owner_address)
    if owner is None:
        return False
    address = sender_of(from_header)
    return address is not None and address == owner


def _owner_or_none(owner_address: Any) -> str | None:
    """The configured owner address, normalised, or None if it is not usable.

    A missing or malformed owner address means nobody can be verified, so every
    sender check fails and nothing is ever approved. That is the correct failure
    mode for a misconfiguration on this particular surface.
    """
    if not isinstance(owner_address, str):
        return None
    owner = owner_address.strip().lower()
    if owner.count("@") != 1 or any(ch.isspace() for ch in owner):
        return None
    local, _, domain = owner.partition("@")
    if not local or not domain:
        return None
    return owner


def _safe_address(value: Any) -> str | None:
    """An address fit to put in a reason string, or None.

    Whatever a stranger put in their ``From`` is attacker-controlled text that
    ends up in an audit record and a log line. Only the parsed address survives,
    with control characters stripped and a length cap, so a crafted display name
    cannot forge log structure or smuggle instructions into the record.
    """
    address = sender_of(value)
    if address is None:
        if not isinstance(value, str) or not value.strip():
            return None
        # Unparseable, but the caller still deserves to see *something*.
        cleaned = _CONTROL.sub(" ", value).strip()
        return (cleaned[:120] + "…") if len(cleaned) > 120 else cleaned or None
    return address


# ── sweeping the mailbox ────────────────────────────────────────────────────


def search_query(token: str) -> str:
    """The Gmail search that finds replies about one request.

    Searched by token rather than by sender on purpose: a ``from:`` filter would
    make an impostor's message invisible, and property 5 requires that a reply
    from someone else is *seen and recorded as ignored*, not quietly missing.
    """
    return f'"{token}"'


def check_for_replies(
    connector: Any,
    *,
    owner_address: Any,
    tokens: Iterable[Any],
) -> list[ReplyVerdict]:
    """Look for answers to the pending requests. Reads only; never raises.

    Uses two methods of the read-only Gmail connector — ``search_threads`` and
    ``read_thread`` — and no others. There is nothing here that labels, marks
    read, archives or deletes: the connector has no such method to call, and this
    function would have no reason to.

    Every message that carries a pending token gets a verdict, including the ones
    that resolve nothing:

    - from the owner, unambiguous, token-bound → APPROVED / DECLINED
    - from the owner, anything less → UNCLEAR, with the reason
    - from anyone else → IGNORED, naming the address it actually came from
    - Sero's own outbound request → IGNORED, named as such rather than as an
      impostor, since it is the request and not an answer to it

    Pass ``owner_address=None`` to resolve the owner from configuration
    (:func:`aureon.approval.config.owner_address`, which takes no arguments) —
    that is the daemon's path. Tests pass it explicitly so they never read the
    environment.

    Returns ``[]`` when there is nothing it could verify — no owner address
    configured, no pending tokens, or a blocked mailbox. An empty list is "no
    answer arrived", which leaves every request pending. Nothing in this function
    can turn absence into approval.
    """
    if owner_address is None:
        owner_address = _configured_owner()
    owner = _owner_or_none(owner_address)
    if owner is None:
        LOG.warning(
            "no usable owner address configured — no reply can be verified, "
            "so none is read as an answer"
        )
        return []

    pending = _pending_tokens(tokens)
    if not pending:
        return []

    mailbox = _mailbox_of(connector)
    verdicts: list[ReplyVerdict] = []
    seen_threads: set[str] = set()
    seen_messages: set[str] = set()

    for token in pending:
        for thread_id in _thread_ids(connector, token):
            if thread_id in seen_threads:
                continue
            seen_threads.add(thread_id)
            for message in _messages(connector, thread_id):
                if len(verdicts) >= MAX_VERDICTS:
                    LOG.warning("reply sweep stopped at %d verdicts", MAX_VERDICTS)
                    return verdicts
                verdict = _read_message(
                    message, owner=owner, pending=pending, searched=token, mailbox=mailbox
                )
                if verdict is None:
                    continue
                key = verdict.message_id or ""
                if key and key in seen_messages:
                    continue
                if key:
                    seen_messages.add(key)
                verdicts.append(verdict)

    return verdicts


def _mailbox_of(connector: Any) -> str | None:
    """Which mailbox is being read, for telling Sero's own request apart from a
    reply to it. Unknown rather than fatal — ``mailbox`` may be a property that
    raises on an unconfigured connector, and this sweep must survive that.
    """
    try:
        return _safe_address(getattr(connector, "mailbox", None))
    except Exception:  # noqa: BLE001
        LOG.debug("connector mailbox unreadable", exc_info=True)
        return None


def _configured_owner() -> str | None:
    """The owner address from configuration, or None. Never raises.

    Imported lazily so this module stays importable — and testable — on its own,
    and so no environment variable is read unless a caller actually asked for the
    configured owner by passing ``None``.
    """
    try:
        from aureon.approval.config import owner_address as configured

        return configured()
    except Exception:  # noqa: BLE001 — unconfigured is a state, not an error
        LOG.debug("owner address could not be resolved from configuration", exc_info=True)
        return None


def _pending_tokens(tokens: Iterable[Any]) -> tuple[str, ...]:
    """The usable tokens, de-duplicated, order preserved. Unusable ones dropped."""
    if isinstance(tokens, (str, bytes)) or tokens is None:
        # A bare string is a common call-site slip and would otherwise iterate
        # character by character, matching nothing while looking like it worked.
        LOG.warning("check_for_replies expects a collection of tokens, not %s", type(tokens).__name__)
        return ()
    out: list[str] = []
    seen: set[str] = set()
    try:
        candidates = list(tokens)
    except Exception:  # noqa: BLE001
        LOG.debug("pending tokens would not iterate", exc_info=True)
        return ()
    for raw in candidates:
        tok = token_or_none(raw)
        if tok is None:
            LOG.debug("dropped an unusable pending token")
            continue
        if tok in seen:
            continue
        seen.add(tok)
        out.append(tok)
    return tuple(out)


def _thread_ids(connector: Any, token: str) -> tuple[str, ...]:
    """Thread ids matching one token, or empty. Absence is never an exception."""
    try:
        result = connector.search_threads(search_query(token), limit=SEARCH_LIMIT)
    except Exception:  # noqa: BLE001 — a transport that throws must not stop the sweep
        LOG.debug("thread search failed", exc_info=True)
        return ()
    if not getattr(result, "available", False):
        blocker = getattr(result, "blocker", None)
        if blocker:
            LOG.info("mailbox unreadable: %s", blocker)
        return ()
    ids: list[str] = []
    for record in getattr(result, "records", ()) or ():
        thread_id = getattr(record, "id", None)
        if isinstance(thread_id, str) and thread_id.strip():
            ids.append(thread_id.strip())
    return tuple(ids)


def _messages(connector: Any, thread_id: str) -> tuple[Any, ...]:
    """Every message in one thread, capped. Empty on any failure."""
    try:
        result = connector.read_thread(thread_id)
    except Exception:  # noqa: BLE001
        LOG.debug("thread read failed", exc_info=True)
        return ()
    if not getattr(result, "available", False):
        return ()
    thread = getattr(result, "record", None)
    if thread is None:
        records = getattr(result, "records", ()) or ()
        thread = records[0] if records else None
    messages = getattr(thread, "messages", ()) or ()
    try:
        return tuple(messages)[:MAX_MESSAGES_PER_THREAD]
    except Exception:  # noqa: BLE001
        LOG.debug("thread messages would not iterate", exc_info=True)
        return ()


def _read_message(
    message: Any,
    *,
    owner: str,
    pending: tuple[str, ...],
    searched: str,
    mailbox: str | None,
) -> ReplyVerdict | None:
    """One message → one verdict, or None when it is not an answer at all.

    None means "this message carries no pending token": another turn in the
    conversation, not a reply to any request. It is skipped rather than recorded,
    because a verdict list of unrelated mail is not an audit record.
    """
    body = getattr(message, "body_text", None)
    if not isinstance(body, str):
        body = ""
    subject = getattr(message, "subject", None)
    if not isinstance(subject, str):
        subject = ""
    message_id = getattr(message, "id", None)
    message_id = message_id.strip() if isinstance(message_id, str) else None
    from_header = getattr(message, "sender", None)

    # Subject *and* body: a reply that quoted nothing still carries the token in
    # ``Re: [AUREON approval <token>] …``. The subject is only ever read for the
    # token — see ``parse_reply``, which never reads intent from it.
    hits = tuple(t for t in pending if references_token(body, t) or references_token(subject, t))
    if not hits:
        return None

    if not sender_is_owner(from_header, owner):
        who = _safe_address(from_header)
        if who is not None and mailbox is not None and who == mailbox:
            reason = (
                "this is Sero's own approval request in the thread, not an answer to it — ignored"
            )
        else:
            reason = (
                f"not from the owner (came from {who or 'an unparseable From header'}) — "
                "ignored, and it approves nothing"
            )
        return ReplyVerdict(IGNORED, None, None, reason, message_id=message_id, sender=who)

    bound, ambiguity = _bind_token(body, subject, pending, searched)
    if bound is None:
        return ReplyVerdict(
            UNCLEAR, None, None, ambiguity or "could not bind the reply to one request",
            message_id=message_id, sender=owner,
        )

    verdict = parse_reply(body, token=bound, subject=subject)
    return replace(verdict, message_id=message_id, sender=owner)


def _bind_token(
    body: str, subject: str, pending: tuple[str, ...], searched: str
) -> tuple[str | None, str | None]:
    """Which single pending request is this message answering?

    Two tiers, and the order between them matters. A token Gary *typed himself*
    outranks one that merely came back in the quoted text or the subject line,
    which gives him a way to be explicit when a thread has collected more than one
    request: paste the token next to the answer.

    When more than one pending token is in play and he did not disambiguate, the
    answer binds to nothing. A "yes" that could belong to either of two requests
    must not resolve both — property 2 says a reply approves exactly the request
    it references *and nothing else*, and "either of these" is not a reference.
    """
    own_words = strip_quoted(body)
    written = tuple(t for t in pending if references_token(own_words, t))
    if len(written) == 1:
        return written[0], None
    if len(written) > 1:
        return None, (
            f"the reply names {len(written)} pending request tokens — "
            "it cannot be told which one it answers, so it answers none"
        )

    echoed = tuple(
        t for t in pending if references_token(body, t) or references_token(subject, t)
    )
    if len(echoed) == 1:
        return echoed[0], None
    if len(echoed) > 1:
        return None, (
            f"the quoted thread carries {len(echoed)} pending request tokens and the reply "
            "names none of them explicitly — it cannot be told which one it answers"
        )
    # Nothing present at all: hand back the token whose search surfaced this
    # thread so ``parse_reply`` reports the absence against a real request.
    return searched, None


__all__ = [
    "APPROVED",
    "DECLINED",
    "UNCLEAR",
    "IGNORED",
    "STATES",
    "RESOLVING",
    "APPROVE_PHRASES",
    "DECLINE_PHRASES",
    "SUBJECT_TAG",
    "TOKEN_CHARS",
    "ReplyVerdict",
    "check_for_replies",
    "find_token",
    "parse_reply",
    "read_intent",
    "references_token",
    "search_query",
    "sender_is_owner",
    "sender_of",
    "strip_quoted",
    "token_or_none",
]
