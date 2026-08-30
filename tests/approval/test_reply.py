"""Reading Gary's answer: the security surface, tested as one.

Hermetic — no network, no credential, no ``os.environ``, no real Gmail. The
mailbox is a fake that can only be searched and read, and which raises on any
other attribute access, so a future edit that reached for a write verb would fail
here rather than in production.

Every test in this file is an attack or a refusal. The five that matter most,
because each one is a way a machine could authorise something a human never
agreed to:

1. A display name carrying the owner's address does not make a stranger the
   owner — including the *unquoted* form that ``email.utils.parseaddr`` gets
   wrong, which is why this module does not use it.
2. A quoted copy of Sero's own "am I ok to go ahead" is not consent.
3. "yes and no" is UNCLEAR, and UNCLEAR is not approval.
4. A bare "yes" that references no token approves nothing.
5. A token only matches itself — never a token it is a prefix of.
"""

from __future__ import annotations

import ast
import inspect
from email.utils import parseaddr

import pytest

from aureon.approval import reply as reply_module
from aureon.approval.reply import (
    APPROVED,
    DECLINED,
    IGNORED,
    SUBJECT_TAG,
    UNCLEAR,
    ReplyVerdict,
    check_for_replies,
    find_token,
    parse_reply,
    read_intent,
    references_token,
    search_query,
    sender_is_owner,
    sender_of,
    strip_quoted,
    token_or_none,
)
from aureon.approval.schemas import ApprovalState, is_token
from aureon.connectors.base import ConnectorResult
from aureon.connectors.schemas import GmailMessage, GmailThread

# ── the cast ────────────────────────────────────────────────────────────────
# Addresses in a reserved-invalid TLD: if any of this ever reached a network it
# could not resolve to a real mailbox.
OWNER = "gary@aureonzorza.invalid"
ATTACKER = "attacker@evil.invalid"
SERO = "sero@aureonzorza.invalid"

# Real ``token_urlsafe``-shaped values. STEM is a strict prefix of LONGER, which
# is the whole of the exactness test: a substring search would confuse them.
TOKEN = "Ky7dQ2mVw9Lz4rTb8NfJ6sXaH3pE5cG1uZoY0iSlWnA"
OTHER = "Bq2XvN8mKd4Tz7LrJ9fS5cWa1pH6gE3uYoZ0iVlQnBx"
STEM = "Rk9mZ2qXvT7bLd4NfJ6sXaH3pE"
LONGER = STEM + "Wn0YiSlQ"


def test_the_fixtures_are_the_shapes_the_package_calls_tokens():
    """If this fails, every other token test below is testing the wrong thing."""
    for token in (TOKEN, OTHER, STEM, LONGER):
        assert is_token(token), f"{token!r} is not a token by the package's own definition"
    assert LONGER.startswith(STEM) and LONGER != STEM


# Sero's request, as Gary receives it. Note that it contains "go ahead" — an
# approval phrase — and the token. Every mail client will quote it back.
REQUEST_BODY = f"""Gary — am I ok to go ahead?

Action: submit application to Innovate UK
Coherence Γ: 0.81   Divergence: 0.09
Auris panel: RALLY (confidence 0.90, evidence 1.00)

Reply YES or NO to this email.

Approval token: {TOKEN}
"""


def quoted(text: str) -> str:
    """The body as a client quotes it: every line prefixed with '>'."""
    return "\n".join("> " + line for line in text.splitlines())


def gmail_reply(answer: str, *, request: str = REQUEST_BODY) -> str:
    """A realistic top-posted Gmail reply: the answer, then the quoted request."""
    return (
        f"{answer}\n\n"
        f"On Fri, 31 Jul 2026 at 09:12, Aureon Sero <{SERO}> wrote:\n"
        f"{quoted(request)}\n"
    )


# ── the fake mailbox ────────────────────────────────────────────────────────


class FakeMailbox:
    """A mailbox that can only be searched and read.

    ``__getattr__`` raises on anything else, so this fake proves a property the
    module claims rather than merely allowing it: if ``check_for_replies`` ever
    reached for ``send``, ``trash``, ``modify``, ``label`` or a bare ``users()``
    handle, the test that used it would fail with the name it reached for.
    """

    name = "gmail-fake"

    def __init__(self, threads=(), *, mailbox=SERO, blocked=False, explode=False):
        self._threads = {t.id: t for t in threads}
        self._mailbox = mailbox
        self._blocked = blocked
        self._explode = explode
        self.calls: list[tuple[str, str]] = []

    @property
    def mailbox(self):
        return self._mailbox

    def search_threads(self, query, *, limit=25):
        self.calls.append(("search_threads", query))
        if self._explode:
            raise RuntimeError("transport died mid-search")
        if self._blocked:
            return ConnectorResult(
                available=False, blocker="no mailbox to read", source="unconfigured"
            )
        term = query.strip().strip('"')
        hits = tuple(
            GmailThread(id=t.id, snippet=t.snippet)
            for t in self._threads.values()
            # Gmail's index covers the subject as well as the body, and the token
            # travels in the subject, so the fake matches both.
            if any(term in f"{m.subject or ''}\n{m.body_text or ''}" for m in t.messages)
        )
        return ConnectorResult(available=True, source="injected", records=hits)

    def read_thread(self, thread_id):
        self.calls.append(("read_thread", thread_id))
        if self._explode:
            raise RuntimeError("transport died mid-read")
        thread = self._threads.get(thread_id)
        if thread is None:
            return ConnectorResult(available=False, blocker="no such thread", source="injected")
        return ConnectorResult(available=True, source="injected", records=(thread,))

    def __getattr__(self, name):
        raise AssertionError(
            f"the reader reached for GmailConnector.{name} — it may touch only "
            "search_threads and read_thread"
        )


# The subject the sender writes, as it comes back on a reply.
SUBJECT = f"[{SUBJECT_TAG} {TOKEN}] am I ok to go ahead — submit application"
REPLY_SUBJECT = f"Re: {SUBJECT}"


def message(
    body: str,
    *,
    sender: str,
    mid: str = "m1",
    display: str = "",
    subject: str = REPLY_SUBJECT,
) -> GmailMessage:
    header = f'"{display}" <{sender}>' if display else sender
    return GmailMessage(
        id=mid, thread_id="t1", sender=header, subject=subject, body_text=body
    )


def thread(*messages: GmailMessage, tid: str = "t1") -> GmailThread:
    return GmailThread(id=tid, subject="Approval needed", messages=tuple(messages))


# ══ property 5 · only the owner's own address counts ════════════════════════


def test_display_name_carrying_the_owner_address_is_not_the_owner():
    """The attack the brief names: owner's address as display text, stranger's as sender."""
    header = f'"{OWNER}" <{ATTACKER}>'
    assert sender_is_owner(header, OWNER) is False
    assert sender_of(header) == ATTACKER


def test_unquoted_display_name_spoof_defeats_parseaddr_but_not_this_module():
    """Why the module uses ``getaddresses`` and requires exactly one address.

    ``parseaddr`` reads ``gary@x <attacker@evil>`` as two addresses and hands
    back the *first* — the display text. A verifier built on it would call this
    stranger the owner.
    """
    header = f"{OWNER} <{ATTACKER}>"
    assert parseaddr(header)[1] == OWNER          # the trap, documented
    assert sender_of(header) is None              # two addresses -> no sender
    assert sender_is_owner(header, OWNER) is False


@pytest.mark.parametrize("header", [
    f"Gary Leckey <{OWNER}>",
    f"<{OWNER}>",
    OWNER,
    f"  {OWNER}  ",
    f"Gary <{OWNER.upper()}>",
    f'"Leckey, Gary" <{OWNER}>',
])
def test_the_owner_himself_passes(header):
    assert sender_is_owner(header, OWNER) is True
    assert sender_is_owner(header, OWNER.upper()) is True


@pytest.mark.parametrize("header", [
    f"Gary <{OWNER}>, {ATTACKER}",                 # two addresses
    f"{ATTACKER}, Gary <{OWNER}>",                 # ...in the other order
    f"Gary <{OWNER}>\nBcc: {ATTACKER}",            # header injection
    f'"Gary" <{OWNER}>; {ATTACKER}',               # semicolon list
    f"Gary <{OWNER}> <{ATTACKER}>",
    "undisclosed-recipients:;",
    "Gary Leckey",
    "",
    "   ",
    None,
    12345,
    f"Gary <{OWNER}>" + "x" * 1200,                # absurd header length
])
def test_anything_but_one_clean_owner_address_fails(header):
    assert sender_is_owner(header, OWNER) is False


@pytest.mark.parametrize("owner", [None, "", "   ", "not-an-address", "a@b, c@d", 42])
def test_with_no_usable_owner_configured_nobody_is_the_owner(owner):
    """A misconfigured owner means every reply is unverifiable, so none approves."""
    assert sender_is_owner(f"Gary <{OWNER}>", owner) is False


def test_a_folded_header_still_reads_as_the_owner():
    """RFC 5322 folding is legitimate continuation, not injection."""
    assert sender_is_owner(f'"Gary\r\n Leckey" <{OWNER}>', OWNER) is True


# ══ property 6 · a quoted echo of the question is not its answer ════════════


def test_a_quoted_request_body_is_not_consent():
    """The whole body is Sero's own request, quoted back. It says "go ahead"."""
    verdict = parse_reply(quoted(REQUEST_BODY), token=TOKEN)
    assert verdict.state is UNCLEAR
    assert verdict.matched_token is None
    assert verdict.is_approval is False


def test_a_quote_under_an_attribution_line_is_not_consent():
    body = f"On Fri, 31 Jul 2026 at 09:12, Aureon Sero <{SERO}> wrote:\n{quoted(REQUEST_BODY)}"
    assert parse_reply(body, token=TOKEN).state is UNCLEAR


def test_an_unquoted_forward_of_the_request_is_not_consent():
    """Some clients forward without '>' markers. The attribution still cuts it."""
    body = f"---------- Forwarded message ---------\nFrom: Aureon Sero <{SERO}>\n\n{REQUEST_BODY}"
    verdict = parse_reply(body, token=TOKEN)
    assert verdict.state is UNCLEAR
    assert verdict.matched_token is None


def test_the_ordinary_reply_gary_will_actually_send_is_approval():
    """One word of his own above the quoted request that carries the token."""
    verdict = parse_reply(gmail_reply("yes"), token=TOKEN)
    assert verdict.state is APPROVED
    assert verdict.matched_token == TOKEN
    assert verdict.intent_phrase == "yes"
    assert verdict.is_approval is True


def test_words_below_a_signature_delimiter_are_not_read_as_an_answer():
    """Everything under '-- ' is the client's, not Gary's. Cutting fails closed."""
    body = f"Thanks for the summary.\n\n-- \nyes\nGary\n\n{quoted(REQUEST_BODY)}"
    assert parse_reply(body, token=TOKEN).state is UNCLEAR


def test_strip_quoted_keeps_only_his_own_words():
    assert strip_quoted(gmail_reply("go ahead")) == "go ahead"
    assert strip_quoted(quoted(REQUEST_BODY)) == ""
    assert strip_quoted(None) == ""


# ── the same rules when the client sends HTML instead of plain text ──────────


def html_reply(answer: str, *, request: str = REQUEST_BODY) -> str:
    """An HTML-only reply: the answer, then the request inside a blockquote."""
    inner = "<br>".join(request.splitlines())
    return (
        f'<div dir="ltr">{answer}</div><br>'
        f'<div class="gmail_quote">'
        f'<div dir="ltr" class="gmail_attr">On Fri, 31 Jul 2026, Aureon Sero '
        f'&lt;{SERO}&gt; wrote:<br></div>'
        f'<blockquote class="gmail_quote"><div>{inner}</div></blockquote></div>'
    )


def test_an_html_reply_is_read_the_same_way():
    verdict = parse_reply(html_reply("yes"), token=TOKEN)
    assert verdict.state is APPROVED
    assert verdict.matched_token == TOKEN


def test_an_html_reply_that_refuses_is_read_as_refusal():
    assert parse_reply(html_reply("no — hold this one"), token=TOKEN).state is DECLINED


def test_the_html_blockquote_holding_seros_question_is_not_consent():
    """No answer of his own above the quote: the quote says "go ahead", not him."""
    markup = html_reply("")
    assert "go ahead" in markup                      # it really is in there
    assert parse_reply(markup, token=TOKEN).state is UNCLEAR


def test_nested_html_blockquotes_cannot_leak_a_tail_of_the_question():
    """A long thread nests quotes; a balanced-tag excision would leave a tail."""
    markup = (
        '<div dir="ltr">thanks</div>'
        f"<blockquote><blockquote><div>inner quote</div></blockquote>"
        f"<div>go ahead — {TOKEN}</div></blockquote>"
    )
    assert parse_reply(markup, token=TOKEN).state is UNCLEAR


def test_an_html_quote_encoded_as_entities_is_still_a_quote():
    markup = f"<div>&gt; am I ok to go ahead?<br>&gt; token {TOKEN}</div>"
    assert parse_reply(markup, token=TOKEN).state is UNCLEAR


def test_html_script_and_style_are_never_read_as_words():
    markup = (
        "<html><head><style>.yes{color:red}</style>"
        "<script>var approved = 'go ahead';</script></head>"
        f"<body><div>what is the deadline?</div>"
        f'<blockquote>{TOKEN}</blockquote></body></html>'
    )
    assert parse_reply(markup, token=TOKEN).state is UNCLEAR


# ══ property 6 · unambiguous, or nothing ═══════════════════════════════════


@pytest.mark.parametrize("answer", [
    "yes", "Yes.", "YES!", "yes please", "approved", "Approved — nice work",
    "go ahead", "Go-ahead", "proceed", "yep", "affirmative", "green light",
    "ok to go ahead", "send it",
])
def test_unambiguous_approval_vocabulary(answer):
    verdict = parse_reply(gmail_reply(answer), token=TOKEN)
    assert verdict.state is APPROVED, f"{answer!r} did not read as approval"
    assert verdict.matched_token == TOKEN


@pytest.mark.parametrize("answer", [
    "no", "No.", "NO — not this one", "stop", "hold", "hold off", "declined",
    "decline", "denied", "not yet", "don't", "do not send", "cancel", "abort", "wait",
])
def test_unambiguous_refusal_vocabulary(answer):
    verdict = parse_reply(gmail_reply(answer), token=TOKEN)
    assert verdict.state is DECLINED, f"{answer!r} did not read as refusal"
    assert verdict.matched_token == TOKEN
    assert verdict.is_approval is False


@pytest.mark.parametrize("answer", [
    "yes and no",
    "no, and yes to the second one",
    "yes but hold on the payment",
    "approved — but wait for the deadline",
])
def test_both_answers_present_is_unclear(answer):
    verdict = parse_reply(gmail_reply(answer), token=TOKEN)
    assert verdict.state is UNCLEAR, f"{answer!r} was read as a decision"
    assert verdict.matched_token is None
    assert verdict.is_approval is False


@pytest.mark.parametrize("answer", [
    "what is the deadline on this one?",
    "seen",
    "ok",                    # deliberately not consent — see APPROVE_PHRASES
    "interesting",
    "😀",
])
def test_anything_unrecognised_is_unclear(answer):
    verdict = parse_reply(gmail_reply(answer), token=TOKEN)
    assert verdict.state is UNCLEAR
    assert verdict.matched_token is None


@pytest.mark.parametrize("body", ["", "   ", "\n\n\t\n", None, 12345, b"yes"])
def test_an_empty_or_impossible_body_is_unclear(body):
    verdict = parse_reply(body, token=TOKEN)
    assert verdict.state is UNCLEAR
    assert verdict.matched_token is None


def test_a_word_is_never_matched_inside_a_longer_one():
    """'nope' must not be found by 'no', 'yesterday' must not be found by 'yes'."""
    assert parse_reply(gmail_reply("yesterday I asked for a summary"), token=TOKEN).state is UNCLEAR
    assert parse_reply(gmail_reply("nope"), token=TOKEN).state is DECLINED


# ══ property 2 · bound to exactly one request, or bound to none ═════════════


def test_a_bare_yes_with_no_token_matches_nothing():
    """The stray or stale 'yes'. He said something; it authorises nothing."""
    verdict = parse_reply("yes", token=TOKEN)
    assert verdict.state is UNCLEAR
    assert verdict.matched_token is None
    assert verdict.intent_phrase == "yes"      # recorded, but bound to nothing
    assert "no request token" in verdict.reason


def test_a_yes_quoting_a_different_request_does_not_approve_this_one():
    verdict = parse_reply(gmail_reply("yes"), token=OTHER)
    assert verdict.state is UNCLEAR
    assert verdict.matched_token is None


def test_a_token_never_matches_a_token_it_is_a_prefix_of():
    """The exactness requirement. A substring search would approve the wrong thing."""
    body = gmail_reply("yes", request=f"Approval token: {LONGER}")
    assert references_token(body, LONGER) is True
    assert references_token(body, STEM) is False
    assert parse_reply(body, token=STEM).state is UNCLEAR
    assert parse_reply(body, token=LONGER).state is APPROVED


def test_a_token_never_matches_as_a_suffix_or_inside_a_run_either():
    assert references_token(f"see PREFIX{TOKEN}", TOKEN) is False
    assert references_token(f"see {TOKEN}_extra", TOKEN) is False
    assert references_token(f"see [{TOKEN}].", TOKEN) is True


def test_a_token_hard_wrapped_across_a_line_still_binds():
    """Clients wrap the longest word in the message, which is the token."""
    split = f"Approval token: {TOKEN[:20]}\n{TOKEN[20:]}"
    assert references_token(split, TOKEN) is True
    assert parse_reply(f"yes\n\n{split}", token=TOKEN).state is APPROVED


def test_a_quoted_printable_soft_break_inside_the_token_still_binds():
    split = f"Approval token: {TOKEN[:25]}=\n{TOKEN[25:]}"
    assert references_token(split, TOKEN) is True


@pytest.mark.parametrize("token", [None, "", "   ", "yes", "short", "not a token!", 42,
                                   "../../data/research/grants/pipeline"])
def test_an_unusable_token_approves_nothing(token):
    """Including a path-shaped 'token' — it matches nothing and steers nothing."""
    assert token_or_none(token) is None
    verdict = parse_reply("yes go ahead", token=token)
    assert verdict.state is UNCLEAR
    assert verdict.matched_token is None


# ══ the verdict type itself makes an unbound approval unconstructable ═══════


def test_a_resolving_verdict_cannot_exist_without_its_token():
    for state in (APPROVED, DECLINED):
        with pytest.raises(ValueError, match="must name the token"):
            ReplyVerdict(state, None, "yes", "would authorise nothing in particular")


def test_a_non_resolving_verdict_cannot_carry_a_token():
    for state in (UNCLEAR, IGNORED):
        with pytest.raises(ValueError, match="must not carry a token"):
            ReplyVerdict(state, TOKEN, None, "resolves nothing")


def test_a_reply_cannot_be_read_as_a_state_only_a_request_can_have():
    for state in (ApprovalState.PENDING, ApprovalState.EXPIRED):
        with pytest.raises(ValueError, match="not something a reply can be read as"):
            ReplyVerdict(state, None, None, "no message establishes this")


def test_is_approval_is_the_only_question_a_caller_has_to_ask():
    approved = parse_reply(gmail_reply("yes"), token=TOKEN)
    assert approved.is_approval is True and approved.resolves is True
    for body in ("yes and no", "no", "what deadline?", ""):
        assert parse_reply(gmail_reply(body), token=TOKEN).is_approval is False
    assert approved.to_dict()["state"] == "APPROVED"


# ══ sweeping the mailbox ════════════════════════════════════════════════════


def test_the_owners_reply_is_found_and_approves_exactly_its_own_request():
    box = FakeMailbox([thread(message(gmail_reply("yes"), sender=f"Gary <{OWNER}>"))])
    verdicts = check_for_replies(box, owner_address=OWNER, tokens=[TOKEN, OTHER])
    assert [v.state for v in verdicts] == [APPROVED]
    assert verdicts[0].matched_token == TOKEN
    assert verdicts[0].sender == OWNER
    assert verdicts[0].message_id == "m1"


def test_the_sweep_touches_nothing_but_the_two_read_methods():
    box = FakeMailbox([thread(message(gmail_reply("yes"), sender=OWNER))])
    check_for_replies(box, owner_address=OWNER, tokens=[TOKEN])
    assert {name for name, _arg in box.calls} == {"search_threads", "read_thread"}
    assert box.calls[0] == ("search_threads", search_query(TOKEN))


def test_a_reply_from_a_stranger_is_ignored_and_recorded_as_such():
    """It carries the real token and says yes. It is still not Gary."""
    box = FakeMailbox([thread(message(gmail_reply("yes go ahead"), sender=ATTACKER))])
    verdicts = check_for_replies(box, owner_address=OWNER, tokens=[TOKEN])
    assert [v.state for v in verdicts] == [IGNORED]
    assert verdicts[0].matched_token is None
    assert verdicts[0].sender == ATTACKER
    assert "not from the owner" in verdicts[0].reason
    assert not any(v.is_approval for v in verdicts)


def test_a_stranger_wearing_the_owners_name_is_still_ignored():
    box = FakeMailbox([
        thread(message(gmail_reply("yes"), sender=ATTACKER, display=f"Gary Leckey {OWNER}"))
    ])
    verdicts = check_for_replies(box, owner_address=OWNER, tokens=[TOKEN])
    assert [v.state for v in verdicts] == [IGNORED]
    assert verdicts[0].sender == ATTACKER


def test_seros_own_request_in_the_thread_is_ignored_as_the_question_not_an_answer():
    box = FakeMailbox([thread(message(REQUEST_BODY, sender=f"Aureon Sero <{SERO}>"))])
    verdicts = check_for_replies(box, owner_address=OWNER, tokens=[TOKEN])
    assert [v.state for v in verdicts] == [IGNORED]
    assert "own approval request" in verdicts[0].reason


def test_a_reply_that_could_answer_either_of_two_requests_answers_neither():
    body = f"yes\n\n{quoted(REQUEST_BODY)}\n{quoted(f'Approval token: {OTHER}')}"
    box = FakeMailbox([thread(message(body, sender=OWNER))])
    verdicts = check_for_replies(box, owner_address=OWNER, tokens=[TOKEN, OTHER])
    assert [v.state for v in verdicts] == [UNCLEAR]
    assert verdicts[0].matched_token is None
    assert "cannot be told which one it answers" in verdicts[0].reason


def test_naming_one_token_in_his_own_words_disambiguates_a_crowded_thread():
    body = f"yes — {TOKEN}\n\n{quoted(REQUEST_BODY)}\n{quoted(f'Approval token: {OTHER}')}"
    box = FakeMailbox([thread(message(body, sender=OWNER))])
    verdicts = check_for_replies(box, owner_address=OWNER, tokens=[TOKEN, OTHER])
    assert [v.state for v in verdicts] == [APPROVED]
    assert verdicts[0].matched_token == TOKEN


def test_a_second_message_on_the_thread_is_recorded_but_resolves_nothing():
    """Only one of the two says anything answerable. Only one resolves."""
    box = FakeMailbox([thread(
        message(gmail_reply("yes"), sender=OWNER, mid="m1"),
        message("and one more thing about the deadline", sender=OWNER, mid="m2"),
    )])
    verdicts = check_for_replies(box, owner_address=OWNER, tokens=[TOKEN])
    assert [v.state for v in verdicts] == [APPROVED, UNCLEAR]
    assert [v.resolves for v in verdicts] == [True, False]
    assert verdicts[1].matched_token is None


def test_mail_unrelated_to_any_request_produces_no_verdicts():
    box = FakeMailbox([thread(
        message("lunch tomorrow?", sender=OWNER, subject="lunch")
    )])
    assert check_for_replies(box, owner_address=OWNER, tokens=[TOKEN]) == []


# ══ the token rides in the subject, and only the token ══════════════════════


def test_a_reply_that_quoted_nothing_still_binds_through_the_subject():
    """A phone reply: one word, no quoted body. The subject carries the token."""
    verdict = parse_reply("yes", token=TOKEN, subject=REPLY_SUBJECT)
    assert verdict.state is APPROVED
    assert verdict.matched_token == TOKEN


def test_the_subject_is_never_read_for_intent_even_though_it_says_go_ahead():
    """``Re: [AUREON approval …] am I ok to go ahead`` must not answer itself."""
    assert "go ahead" in REPLY_SUBJECT
    for body in ("what is the deadline on this?", "", "   "):
        verdict = parse_reply(body, token=TOKEN, subject=REPLY_SUBJECT)
        assert verdict.state is UNCLEAR, f"the subject answered for body {body!r}"
        assert verdict.matched_token is None


def test_a_subject_carrying_a_different_request_does_not_bind_this_one():
    other_subject = f"Re: [{SUBJECT_TAG} {OTHER}] am I ok to go ahead — submit"
    assert parse_reply("yes", token=TOKEN, subject=other_subject).state is UNCLEAR


def test_the_phone_reply_is_found_and_approved_end_to_end():
    box = FakeMailbox([thread(message("Yes", sender=f"Gary <{OWNER}>"))])
    verdicts = check_for_replies(box, owner_address=OWNER, tokens=[TOKEN])
    assert [v.state for v in verdicts] == [APPROVED]
    assert verdicts[0].matched_token == TOKEN


# ══ find_token · a claim, read from the shape the sender writes ═════════════


def test_find_token_reads_the_tag_the_sender_writes():
    assert find_token(SUBJECT) == TOKEN
    assert find_token(REPLY_SUBJECT) == TOKEN
    assert find_token(f"Fwd: Re: [{SUBJECT_TAG} {TOKEN}] am I ok to go ahead") == TOKEN
    assert find_token(f"- **Token** `[{SUBJECT_TAG} {TOKEN}]`") == TOKEN


@pytest.mark.parametrize("text", [
    "",
    None,
    12345,
    "Re: am I ok to go ahead — submit",           # no tag
    f"[{SUBJECT_TAG} short]",                     # not a token shape
    f"[{SUBJECT_TAG}]",
    f"{SUBJECT_TAG} {TOKEN}",                     # no brackets: not the shape
    "[AUREON approval ../../data/research/grants/pipeline]",
])
def test_find_token_refuses_anything_that_is_not_the_shape(text):
    assert find_token(text) is None


def test_the_tag_matches_the_shape_the_senders_actually_write():
    """Cross-checked against the modules that compose and send the request.

    If a sender ever changes the tag it writes, this fails here rather than the
    reader quietly stopping recognising its own requests. Both spellings in use
    across the package are checked, so a rename cannot make this test vacuous.
    """
    found = 0
    for module_name in ("aureon.approval.compose", "aureon.approval.notify"):
        module = pytest.importorskip(module_name)
        for attr in ("SUBJECT_TAG", "TOKEN_TAG"):
            tag = getattr(module, attr, None)
            if tag is None:
                continue
            found += 1
            assert tag == SUBJECT_TAG, (
                f"{module_name}.{attr} is {tag!r}, which the reader cannot read"
            )
    assert found, "neither sender declares a tag — the cross-check is watching nothing"


# ══ against the real composer, not a fixture ════════════════════════════════


def _real_request():
    """``(subject, body, token)`` as the real composer and sender produce them.

    The body comes from :func:`aureon.approval.compose.render_body` and the wire
    subject from :func:`aureon.approval.notify.subject_line` — the actual text
    Gary receives, not a fixture that resembles it.
    """
    compose = pytest.importorskip("aureon.approval.compose")
    notify = pytest.importorskip("aureon.approval.notify")
    schemas = pytest.importorskip("aureon.approval.schemas")
    from datetime import UTC, datetime, timedelta

    created = datetime(2026, 7, 31, 9, 12, tzinfo=UTC)
    expires = created + timedelta(hours=72)
    grounding = schemas.GroundingSnapshot(
        coherence=0.81, divergence=0.09, panel_consensus="RALLY",
        panel_confidence=0.90, panel_evidence=1.0,
    )
    try:
        body = compose.render_body(
            "submit", TOKEN, grounding=grounding,
            created_at=created, expires_at=expires,
        )
        request = schemas.ApprovalRequest(
            token=TOKEN,
            subject=compose.subject_line("submit"),
            action="submit",
            application_id=None,
            body_markdown=body,
            created_at=created,
            expires_at=expires,
            grounding=grounding,
        )
        subject = notify.subject_line(request)
    except (TypeError, ValueError) as exc:  # a sibling's signature moved
        pytest.skip(f"sender/composer API differs: {exc}")
    return subject, body, TOKEN


def test_the_real_subject_line_carries_a_token_this_reader_can_find():
    subject, _body, token = _real_request()
    assert find_token(subject) == token
    assert references_token(subject, token) is True


def test_the_real_request_body_cannot_be_echoed_back_as_its_own_approval():
    """The self-approval hole, closed against the actual text Gary receives.

    The composer quotes both vocabularies at him on purpose. So a client that
    echoes its body back — quoted or not — produces text containing an approval
    word *and* a refusal word, which is ambiguous, which is not consent.
    """
    subject, body, token = _real_request()
    assert read_intent(body) is UNCLEAR
    assert parse_reply(body, token=token, subject=subject).state is UNCLEAR
    assert parse_reply(quoted(body), token=token, subject=subject).state is UNCLEAR
    # ...and the same text with the machinery's own attribution line above it.
    echoed = f"On Fri, 31 Jul 2026 at 09:12, Aureon Sero <{SERO}> wrote:\n{quoted(body)}"
    assert parse_reply(echoed, token=token, subject=subject).state is UNCLEAR


def test_one_word_above_the_real_request_body_is_the_approval():
    """And the workflow still works: his word, her question, one token."""
    subject, body, token = _real_request()
    reply = (
        f"yes\n\nOn Fri, 31 Jul 2026 at 09:12, Aureon Sero <{SERO}> wrote:\n{quoted(body)}"
    )
    verdict = parse_reply(reply, token=token, subject=subject)
    assert verdict.state is APPROVED
    assert verdict.matched_token == token


# ══ read_intent · words only, and never a self-answer ══════════════════════


def test_read_intent_reads_words_and_nothing_else():
    assert read_intent("yes") is APPROVED
    assert read_intent("no") is DECLINED
    assert read_intent("what is the deadline?") is UNCLEAR
    assert read_intent("") is UNCLEAR
    assert read_intent(None) is UNCLEAR
    assert read_intent(quoted(REQUEST_BODY)) is UNCLEAR


def test_seros_own_question_in_his_mouth_is_not_an_answer():
    """The hole a red-team pass found, closed at the reader rather than upstream.

    A client that echoes the request back with no ``>`` markers used to be caught
    only because the composer quotes *both* vocabularies — an accident-preventing
    sentence that a future edit could delete. Recognising her question closes it
    here, where it does not depend on anyone else's wording.
    """
    echoed = f"Gary — am I ok to go ahead?\nReply yes to authorise.\nToken: {TOKEN}"
    assert read_intent(echoed) is UNCLEAR
    verdict = parse_reply(echoed, token=TOKEN)
    assert verdict.state is UNCLEAR
    assert verdict.matched_token is None
    assert "the request coming back" in verdict.reason


def test_the_question_the_senders_ask_is_one_the_reader_recognises_as_an_echo():
    """Cross-check: reword the question upstream and this fails, loudly.

    Without it, ``ECHO_MARKERS`` could silently stop matching the text actually
    sent, and the echo would go back to being read as consent.
    """
    from aureon.approval.reply import ECHO_MARKERS

    assert ECHO_MARKERS and all(m == m.lower() for m in ECHO_MARKERS)

    checked = 0
    for module_name, attr in (
        ("aureon.approval.compose", "QUESTION"),
        ("aureon.approval.notify", "THE_QUESTION"),
    ):
        module = pytest.importorskip(module_name)
        question = getattr(module, attr, None)
        if question is None:
            continue
        checked += 1
        # Not merely "no vocabulary found" — the echo path itself must fire, which
        # the reason names. Otherwise a reworded question would pass this test
        # while quietly falling back to vocabulary matching.
        verdict = parse_reply(f"{question}\n{TOKEN}", token=TOKEN)
        assert verdict.state is UNCLEAR
        assert "the request coming back" in verdict.reason, (
            f"{module_name}.{attr} = {question!r} is not recognised as Sero's own question"
        )
    assert checked, "neither sender declares its question — the cross-check is vacuous"


def test_an_rfc_comment_after_the_owners_address_is_still_the_owner():
    """Deliberate, and pinned so nobody "fixes" it into a false refusal.

    ``"Gary" <gary@…> (someone@else)`` is *one* address with a parenthesised
    comment. The mail is from the owner; a string in a comment does not change
    that. The reverse — the owner's address inside the comment and a stranger's as
    the address — is refused, which is the case that matters.
    """
    assert sender_is_owner(f'"Gary" <{OWNER}> ({ATTACKER})', OWNER) is True
    assert sender_is_owner(f'"Gary" <{ATTACKER}> ({OWNER})', OWNER) is False


def test_an_echo_of_the_requests_own_instructions_is_unclear():
    """The composer relies on this: its instructions quote *both* vocabularies.

    A client that echoes the request body back without '>' markers therefore
    produces text containing an approval word and a refusal word, which is
    ambiguous — so Sero's own question can never parse as Gary's yes.
    """
    echoed = (
        "Reply to this email with yes / approved / go ahead / proceed to authorise it, "
        "or no / stop / hold / declined to refuse."
    )
    assert read_intent(echoed) is UNCLEAR
    assert parse_reply(f"{echoed}\n\nToken: {TOKEN}", token=TOKEN).state is UNCLEAR


@pytest.mark.parametrize("kwargs", [
    {"owner_address": "not-an-address", "tokens": [TOKEN]},
    {"owner_address": OWNER, "tokens": []},
    {"owner_address": OWNER, "tokens": None},
    {"owner_address": OWNER, "tokens": TOKEN},          # a bare string, not a collection
    {"owner_address": OWNER, "tokens": ["short", "", None]},
])
def test_nothing_verifiable_means_no_verdicts(kwargs):
    box = FakeMailbox([thread(message(gmail_reply("yes"), sender=OWNER))])
    assert check_for_replies(box, **kwargs) == []


def test_a_blocked_mailbox_reports_no_answer_rather_than_no_approval():
    box = FakeMailbox([thread(message(gmail_reply("yes"), sender=OWNER))], blocked=True)
    assert check_for_replies(box, owner_address=OWNER, tokens=[TOKEN]) == []


def test_a_transport_that_throws_does_not_stop_the_watch():
    box = FakeMailbox([thread(message(gmail_reply("yes"), sender=OWNER))], explode=True)
    assert check_for_replies(box, owner_address=OWNER, tokens=[TOKEN]) == []


def test_a_connector_that_is_not_one_at_all_is_survived():
    assert check_for_replies(object(), owner_address=OWNER, tokens=[TOKEN]) == []
    assert check_for_replies(None, owner_address=OWNER, tokens=[TOKEN]) == []


def test_a_connector_whose_mailbox_property_raises_is_survived():
    """An unconfigured connector can raise on ``mailbox``. The sweep still runs."""

    class HostileMailbox(FakeMailbox):
        @property
        def mailbox(self):
            raise RuntimeError("no mailbox configured")

    box = HostileMailbox([thread(message(gmail_reply("yes"), sender=OWNER))])
    verdicts = check_for_replies(box, owner_address=OWNER, tokens=[TOKEN])
    assert [v.state for v in verdicts] == [APPROVED]


def test_the_same_thread_matched_by_two_token_searches_is_read_once():
    body = f"yes — {TOKEN}\n\n{quoted(REQUEST_BODY)}"
    box = FakeMailbox([thread(message(body, sender=OWNER))])
    verdicts = check_for_replies(box, owner_address=OWNER, tokens=[TOKEN, TOKEN, OTHER])
    assert len(verdicts) == 1


# ══ structural · there is no outbound path in this module ═══════════════════

# Names that would mean "somewhere to send this". ``owner_address`` is not among
# them: it is a yardstick an inbound sender is compared against, and no function
# here hands it to anything.
DESTINATION_NAMES = frozenset({
    "to", "to_address", "to_addr", "recipient", "recipients", "rcpt", "cc", "bcc",
    "dest", "destination", "send_to", "mailto", "addressee", "audience",
})


def _public_callables():
    for name, obj in vars(reply_module).items():
        if name.startswith("_"):
            continue
        if inspect.isfunction(obj) and obj.__module__ == reply_module.__name__:
            yield f"{name}()", obj
        elif inspect.isclass(obj) and obj.__module__ == reply_module.__name__:
            for attr, member in vars(obj).items():
                if not attr.startswith("_") and inspect.isfunction(member):
                    yield f"{name}.{attr}()", member


def test_no_public_callable_accepts_a_recipient():
    """Property 1, from this side: the reader cannot be told where to send.

    Walked with ``inspect.signature`` over every public function in the module,
    so a future edit that added ``to=`` fails here.
    """
    checked = 0
    for label, func in _public_callables():
        checked += 1
        for param in inspect.signature(func).parameters:
            assert param.lower() not in DESTINATION_NAMES, (
                f"{label} accepts a destination parameter {param!r} — "
                "no callable in this package may be told who to write to"
            )
    assert checked >= 8, "the signature walk found almost nothing — it is not walking"


# Anything that could put a byte on a wire. ``email`` is absent from this set on
# purpose: ``email.utils`` parses headers and cannot send one.
TRANSPORT_MODULES = frozenset({
    "smtplib", "socket", "ssl", "http", "urllib", "requests", "httpx", "aiohttp",
    "googleapiclient", "asyncio", "subprocess", "ftplib", "telnetlib",
})

# Method names that would mean the reader had grown a hand. Checked as parsed
# attribute names rather than as text, so prose in a docstring cannot trip it and
# a real call cannot hide from it.
WRITE_VERBS = frozenset({
    "send", "sendmail", "send_message", "sendMail", "draft", "drafts", "compose",
    "trash", "untrash", "delete", "insert", "modify", "batchModify", "batchDelete",
    "label", "unlabel", "archive", "write", "post", "put", "patch",
})


def test_the_module_imports_nothing_that_could_send():
    """Parsed, not grepped: no transport is imported anywhere in this module."""
    tree = ast.parse(inspect.getsource(reply_module))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    smuggled = imported & TRANSPORT_MODULES
    assert not smuggled, f"the reply reader imports a transport: {sorted(smuggled)}"


def test_the_module_calls_no_write_verb_on_anything():
    """The mailbox is read through two methods and touched by no others."""
    tree = ast.parse(inspect.getsource(reply_module))
    attributes = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    reached = attributes & WRITE_VERBS
    assert not reached, f"the reply reader reaches for {sorted(reached)}"
    assert {"search_threads", "read_thread"} <= attributes, (
        "the two read methods are not called — this test is no longer watching anything"
    )


def test_the_gmail_connector_it_reads_through_has_no_send_method():
    """The read-only guarantee this module leans on, asserted where it is used."""
    from aureon.connectors.gmail import GmailConnector

    for verb in ("send", "draft", "reply", "trash", "modify", "delete", "insert"):
        assert not hasattr(GmailConnector, verb)
