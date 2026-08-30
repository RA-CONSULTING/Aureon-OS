"""The final approval gate: Gary's reply is the gate, and nothing else is.

Hermetic. Every test writes its ledger under ``tmp_path``, holds the clock still,
feeds the organism's readings through the seams :mod:`aureon.approval.compose`
provides, and hands the reply sweep a fake mailbox built from the *real*
connector record types — so a shape change in ``GmailMessage`` breaks this suite
instead of silently passing. No network, no SMTP, no live HNC trace, no live
pipeline.

What this file exists to pin, beyond the happy path:

1. **Nothing is a recipient.** No public callable anywhere in the package accepts
   a destination argument (property 1), and the three entry points have exactly
   the signature the owner specified — checked by walking every signature rather
   than by trusting a docstring.
2. **Absence is never approval.** A bare "yes", a quoted "yes", an ambiguous
   reply, a stranger's reply, a reply after the deadline and a replayed reply all
   leave the action unauthorised, each for its own recorded reason.
3. **A request that cannot show its grounding is never made** — and one made
   while the organism is divided does not look like a confident one.
4. **Waiting on Gary is a real state of the organism**, published into the HNC
   field, and only when something is actually open.
"""

from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from aureon.approval import compose, config, gate, notify, reply, schemas, store
from aureon.approval.notify import NotifyResult
from aureon.approval.schemas import ApprovalState
from aureon.connectors.base import ConnectorResult
from aureon.connectors.schemas import GmailMessage, GmailThread
from aureon.gates.switchboard import GateReading

NOW = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)

#: Never the owner's real address: a test that embeds a live mailbox is one
#: `sed` away from mailing it.
OWNER = "owner@example.test"
STRANGER = "assessor@funder.example.test"

HELD_ACTION = "submit_application"
APP_ID = "APP-TEST-0001"


# ── the world, built from nothing ────────────────────────────────────────────


class _Clock:
    """A clock the tests move by hand. Expiry is a fact about time, so time is
    the one thing these tests must control exactly."""

    def __init__(self, start: datetime) -> None:
        self.moment = start

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, **delta: float) -> datetime:
        self.moment = self.moment + timedelta(**delta)
        return self.moment


class _Mailbox:
    """The two read-only methods the sweep uses, and not one more.

    Deliberately has no ``send``, ``draft``, ``label`` or ``trash``: if the
    approval loop ever grew a call to one, this stub would raise
    ``AttributeError`` and the suite would fail. The fake is part of the
    guarantee, not just a convenience.
    """

    mailbox = OWNER

    def __init__(self, *threads: GmailThread) -> None:
        self.threads = list(threads)
        self.queries: list[str] = []
        self.reads: list[str] = []

    def search_threads(self, query: str, *, limit: int = 25) -> ConnectorResult:
        self.queries.append(query)
        stubs = tuple(GmailThread(id=t.id, snippet=t.snippet) for t in self.threads)
        return ConnectorResult(available=True, source="injected", records=stubs[:limit])

    def read_thread(self, thread_id: str) -> ConnectorResult:
        self.reads.append(thread_id)
        for thread in self.threads:
            if thread.id == thread_id:
                return ConnectorResult(available=True, source="injected", records=(thread,))
        return ConnectorResult(available=False, source="injected", blocker="no such thread")


class _Bus:
    """Records what the organism was told, so the tests can read the announcements."""

    def __init__(self) -> None:
        self.thoughts: list[object] = []

    def publish(self, thought: object) -> None:
        self.thoughts.append(thought)

    def recall(self, topic_prefix: str, limit: int = 1) -> list[object]:
        return []  # nothing pre-existing: the field is read through the seams

    def topics(self) -> list[str]:
        return [getattr(t, "topic", "") for t in self.thoughts]

    def payloads(self, topic: str) -> list[dict]:
        return [getattr(t, "payload", {}) for t in self.thoughts
                if getattr(t, "topic", "") == topic]


def _thread(token: str | None, body: str, *, sender: str = OWNER, subject: str | None = None,
            thread_id: str = "t-1", message_id: str = "m-1") -> GmailThread:
    """One reply, as Gmail would hand it back.

    When ``token`` is given the subject carries it, which is the real path: Gary
    hits reply, the ``Re:`` subject keeps the tag, and he types one word.
    """
    line = subject if subject is not None else (
        f"Re: [AUREON approval {token}] Gary — am I ok to go ahead?" if token
        else "Re: a message with no token in it"
    )
    return GmailThread(
        id=thread_id, subject=line, message_count=1,
        messages=(GmailMessage(id=message_id, thread_id=thread_id, sender=sender,
                               subject=line, body_text=body, body_mime="text/plain"),),
    )


def _confident(monkeypatch, *, divergence: float = 0.02, evidence: float = 0.86) -> None:
    """An organism that reads strongly, through compose's own seams."""
    monkeypatch.setattr(compose, "_read_field",
                        lambda bus: SimpleNamespace(available=True, coherence_gamma=0.91))
    monkeypatch.setattr(compose, "_read_blend",
                        lambda bus: SimpleNamespace(available=True, divergence=divergence))
    monkeypatch.setattr(compose, "_read_panel",
                        lambda bus: SimpleNamespace(available=True, consensus="RALLY",
                                                    confidence=0.95, evidence_ratio=evidence,
                                                    ungrounded_nodes=("Tiger", "Panda")))
    monkeypatch.setattr(
        "aureon.gates.switchboard.read_organism",
        lambda bus=None: GateReading(coherence=0.91, divergence=divergence, life_score=0.88,
                                     panel_consensus="RALLY", panel_confidence=0.95,
                                     panel_evidence=evidence),
    )


def _blind(monkeypatch) -> None:
    """An organism that cannot read itself at all."""
    unreadable = lambda bus: SimpleNamespace(available=False, blocker="nothing to read")  # noqa: E731
    for seam in ("_read_field", "_read_blend", "_read_panel"):
        monkeypatch.setattr(compose, seam, unreadable)
    monkeypatch.setattr("aureon.gates.switchboard.read_organism", lambda bus=None: GateReading())


@pytest.fixture
def clock(monkeypatch):
    ticker = _Clock(NOW)
    monkeypatch.setattr(gate, "_now", ticker)
    return ticker


@pytest.fixture
def sent(monkeypatch):
    """Capture the delivery instead of performing it.

    The delivery layer has its own suite; here it is replaced so nothing writes
    outside ``tmp_path`` and no SMTP configuration can make a test send mail.
    What is asserted is that the loop asks it to deliver, once, per request.
    """
    calls: list[object] = []

    def _deliver(request, *, transport=None, now=None, directory=None):
        calls.append(request)
        return NotifyResult(sent=True, token=request.token, owner=OWNER,
                            subject=request.subject)

    monkeypatch.setattr(gate, "send_approval_request", _deliver)
    return calls


@pytest.fixture
def world(tmp_path, monkeypatch, clock, sent):
    """A repository-free world: own ledger, own traces, one configured owner."""
    monkeypatch.setenv("AUREON_APPROVALS_DIR", str(tmp_path / "approvals"))
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path / "trace"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "trace" / "hnc_live.jsonl"))
    monkeypatch.setenv("AUREON_APPROVAL_EMAIL", OWNER)
    monkeypatch.delenv("AUREON_OWNER_EMAIL", raising=False)
    monkeypatch.setenv("AUREON_APPROVAL_TTL_HOURS", "48")
    _confident(monkeypatch)
    return SimpleNamespace(clock=clock, sent=sent, bus=_Bus(), tmp=tmp_path,
                           monkeypatch=monkeypatch)


def _ask(world) -> object:
    request = gate.request_approval(HELD_ACTION, application_id=APP_ID, bus=world.bus)
    assert request is not None, "the confident world must be able to ask"
    return request


# ── 1. property 1, structurally: nothing here can address anyone ─────────────

_PACKAGE = (config, schemas, compose, reply, store, notify, gate)

#: Parameter names that would mean "where this goes". ``owner_address`` and
#: ``candidate`` are deliberately absent: both name an address arriving *inbound*
#: on a reply, to be verified against configuration, and neither is ever handed
#: to a transport. A destination is what this set forbids.
_DESTINATION_NAMES = frozenset({
    "to", "to_addr", "to_address", "toaddr", "recipient", "recipients", "rcpt",
    "cc", "bcc", "address", "addresses", "email", "emails", "mailbox",
    "destination", "dest", "send_to", "sendto", "addressee", "envelope_to",
})


def _public_callables():
    """Every public callable the package defines, with its qualified name."""
    for module in _PACKAGE:
        for name, obj in vars(module).items():
            if name.startswith("_") or getattr(obj, "__module__", None) != module.__name__:
                continue
            if inspect.isfunction(obj):
                yield f"{module.__name__}.{name}", obj
            elif inspect.isclass(obj):
                for attr, member in vars(obj).items():
                    if attr.startswith("_") and attr != "__init__":
                        continue
                    if inspect.isfunction(member):
                        yield f"{module.__name__}.{name}.{attr}", member


def test_no_public_callable_in_the_package_accepts_a_recipient():
    # Property 1. Not "the recipient is checked" — there is nothing to check,
    # because there is nowhere to put one. A sender that cannot address a funder
    # cannot accidentally submit to one.
    offenders = []
    for qualname, func in _public_callables():
        for param in inspect.signature(func).parameters:
            if param.lower() in _DESTINATION_NAMES:
                offenders.append(f"{qualname}({param})")
    assert offenders == [], f"a destination argument appeared: {offenders}"


def test_the_entry_points_have_exactly_the_owner_specified_signature():
    # Locked exactly, so a later edit cannot slip a recipient in beside them.
    assert list(inspect.signature(gate.request_approval).parameters) == [
        "action", "application_id", "dossier", "bus"]
    assert list(inspect.signature(gate.poll_approvals).parameters) == ["connector", "bus"]
    assert list(inspect.signature(gate.approval_state).parameters) == ["token"]
    assert list(inspect.signature(config.owner_address).parameters) == []


def test_the_request_type_has_no_field_for_a_destination():
    assert not _DESTINATION_NAMES & set(schemas.ApprovalRequest.__dataclass_fields__)


def test_the_caution_threshold_matches_the_switchboards():
    # Stated independently in two packages; if they ever drift, this fails rather
    # than one of them quietly becoming more permissive than the other.
    from aureon.gates.switchboard import DEFAULT_CHAIN

    assert DEFAULT_CHAIN[-1].max_divergence == schemas.MAX_DIVERGENCE


# ── 2. the happy path, end to end ────────────────────────────────────────────


def test_the_full_happy_path_request_wait_reply_yes_approved(world):
    request = _ask(world)

    # asked, delivered once, and waiting
    assert gate.approval_state(request.token) is ApprovalState.PENDING
    assert world.sent == [request]
    assert gate.hold_resolved(HELD_ACTION, request.token) is False

    # Gary hits reply and types one word
    changed = gate.poll_approvals(_Mailbox(_thread(request.token, "yes")), bus=world.bus)

    assert [r.token for r in changed] == [request.token]
    assert gate.approval_state(request.token) is ApprovalState.APPROVED
    assert gate.hold_resolved(HELD_ACTION, request.token) is True

    # and the state is readable from the ledger, by anyone, without the bus
    assert store.load(request.token).state is ApprovalState.APPROVED


def test_the_bus_topics_fire(world):
    request = _ask(world)
    assert gate.TOPIC_REQUESTED in world.bus.topics()

    requested = world.bus.payloads(gate.TOPIC_REQUESTED)[0]
    assert requested["token"] == request.token
    assert requested["action"] == HELD_ACTION
    assert requested["notified"] is True
    # The grounding travels with the announcement, not just in the email.
    assert requested["grounding"]["coherence"] == pytest.approx(0.91)

    gate.poll_approvals(_Mailbox(_thread(request.token, "go ahead")), bus=world.bus)

    assert gate.TOPIC_GRANTED in world.bus.topics()
    assert world.bus.payloads(gate.TOPIC_GRANTED)[0]["token"] == request.token
    assert gate.TOPIC_DECLINED not in world.bus.topics()


def test_the_request_carries_its_grounding_and_the_dossier_summary(world):
    dossier = SimpleNamespace(
        application_id=APP_ID, name="A Sensing Call", funder="A Funder",
        status="DRAFT_WAITING_PARTNER", amount_requested=250_000.0, currency="GBP",
        compliance="pass", outstanding=("no fit score: no call text retrieved",),
        gate_verdicts=(), deadline=NOW + timedelta(days=10),
    )
    request = gate.request_approval(HELD_ACTION, application_id=APP_ID, dossier=dossier,
                                   bus=world.bus)

    assert request is not None
    body = request.body_markdown
    # WHY she wants to proceed — the four voices, in the message Gary reads.
    assert "0.91" in body                      # Γ
    assert "RALLY" in body                     # the nine nodes' consensus
    assert "A Funder" in body                  # the dossier summary
    assert request.token in body               # what binds his answer to this ask


# ── 3. every way an answer can fail to be an approval ────────────────────────


def test_a_declined_reply_blocks(world):
    request = _ask(world)

    changed = gate.poll_approvals(_Mailbox(_thread(request.token, "no")), bus=world.bus)

    assert [r.state for r in changed] == [ApprovalState.DECLINED]
    assert gate.approval_state(request.token) is ApprovalState.DECLINED
    assert gate.hold_resolved(HELD_ACTION, request.token) is False
    assert gate.TOPIC_DECLINED in world.bus.topics()
    assert gate.TOPIC_GRANTED not in world.bus.topics()


def test_a_declined_token_cannot_later_be_approved(world):
    request = _ask(world)
    gate.poll_approvals(_Mailbox(_thread(request.token, "no")), bus=world.bus)

    # He changes his mind by replying again — that is a new request's job, not a
    # spent token's. Single use cuts both ways.
    again = gate.poll_approvals(
        _Mailbox(_thread(request.token, "yes", message_id="m-2")), bus=world.bus)

    assert again == []
    assert gate.approval_state(request.token) is ApprovalState.DECLINED


def test_an_expired_request_cannot_be_approved_afterwards(world):
    request = _ask(world)
    world.clock.advance(hours=49)  # the 48h window has closed

    # The clock alone expires it — no sweep has run yet.
    assert gate.approval_state(request.token) is ApprovalState.EXPIRED

    changed = gate.poll_approvals(_Mailbox(_thread(request.token, "yes")), bus=world.bus)

    assert [r.state for r in changed] == [ApprovalState.EXPIRED]
    assert gate.approval_state(request.token) is ApprovalState.EXPIRED
    assert gate.hold_resolved(HELD_ACTION, request.token) is False
    assert gate.TOPIC_EXPIRED in world.bus.topics()
    assert gate.TOPIC_GRANTED not in world.bus.topics()

    # And it stays refused on every later look — an old yes never lands.
    assert gate.poll_approvals(
        _Mailbox(_thread(request.token, "yes", message_id="m-3")), bus=world.bus) == []
    assert gate.approval_state(request.token) is ApprovalState.EXPIRED


def test_replaying_the_same_reply_re_approves_nothing(world):
    request = _ask(world)
    mailbox = _Mailbox(_thread(request.token, "yes"))

    first = gate.poll_approvals(mailbox, bus=world.bus)
    second = gate.poll_approvals(mailbox, bus=world.bus)

    assert [r.token for r in first] == [request.token]
    assert second == [], "the same reply, delivered twice, must change nothing"
    assert len(world.bus.payloads(gate.TOPIC_GRANTED)) == 1


def test_a_bare_yes_with_no_token_matches_nothing(world):
    request = _ask(world)

    changed = gate.poll_approvals(
        _Mailbox(_thread(None, "yes — go ahead")), bus=world.bus)

    assert changed == []
    assert gate.approval_state(request.token) is ApprovalState.PENDING
    assert gate.TOPIC_GRANTED not in world.bus.topics()


def test_a_reply_from_anyone_else_is_ignored_and_recorded(world):
    request = _ask(world)

    changed = gate.poll_approvals(
        _Mailbox(_thread(request.token, "yes, submit it", sender=STRANGER)), bus=world.bus)

    assert changed == []
    assert gate.approval_state(request.token) is ApprovalState.PENDING
    assert gate.TOPIC_IGNORED in world.bus.topics()
    ignored = world.bus.payloads(gate.TOPIC_IGNORED)[0]
    assert ignored["sender"] == STRANGER
    assert ignored["matched_token"] is None, "a non-resolving verdict must name no request"


def test_an_address_hidden_in_a_display_name_does_not_pass_as_the_owner(world):
    request = _ask(world)

    # The classic: the owner's address as the *display name*, a stranger's as the
    # actual address. Parsing the header properly is the difference.
    changed = gate.poll_approvals(
        _Mailbox(_thread(request.token, "yes", sender=f"{OWNER} <{STRANGER}>")), bus=world.bus)

    assert changed == []
    assert gate.approval_state(request.token) is ApprovalState.PENDING
    assert gate.TOPIC_IGNORED in world.bus.topics()


@pytest.mark.parametrize("body, why", [
    ("yes but hold off until the partner confirms", "both vocabularies present"),
    ("", "an empty body"),
    ("what is the deadline on this one?", "a question, not an answer"),
    ("> yes\n> go ahead", "only a quoted copy of the question"),
])
def test_an_unclear_reply_is_never_approval(world, body, why):
    request = _ask(world)

    changed = gate.poll_approvals(_Mailbox(_thread(request.token, body)), bus=world.bus)

    assert changed == [], why
    assert gate.approval_state(request.token) is ApprovalState.PENDING
    assert gate.TOPIC_GRANTED not in world.bus.topics()


def test_an_unclear_reply_is_announced_without_a_token(world):
    request = _ask(world)
    gate.poll_approvals(_Mailbox(_thread(request.token, "yes but not yet")), bus=world.bus)

    assert gate.TOPIC_UNCLEAR in world.bus.topics()
    payload = world.bus.payloads(gate.TOPIC_UNCLEAR)[0]
    assert payload["matched_token"] is None
    assert payload["is_approval"] is False


def test_silence_authorises_nothing(world):
    request = _ask(world)

    assert gate.poll_approvals(_Mailbox(), bus=world.bus) == []
    assert gate.approval_state(request.token) is ApprovalState.PENDING
    assert gate.hold_resolved(HELD_ACTION, request.token) is False


# ── 4. token scope: an approval is for one action, and one only ──────────────


def test_an_approval_for_one_action_cannot_clear_another(world):
    request = _ask(world)
    gate.poll_approvals(_Mailbox(_thread(request.token, "yes")), bus=world.bus)

    assert gate.hold_resolved(HELD_ACTION, request.token) is True
    # The same live, approved token — asked about a different irreversible step.
    assert gate.hold_resolved("pay_invoice", request.token) is False
    assert gate.hold_resolved("submit_applications", request.token) is False


def test_an_unknown_token_is_not_permission(world):
    assert gate.approval_state("a" * 43) is ApprovalState.EXPIRED
    assert gate.hold_resolved(HELD_ACTION, "a" * 43) is False
    assert gate.hold_resolved(HELD_ACTION, "") is False


# ── 5. she does not ask what she cannot justify, or ask nobody ───────────────


def test_a_request_with_no_grounding_is_never_made(world):
    _blind(world.monkeypatch)

    assert gate.request_approval(HELD_ACTION, application_id=APP_ID, bus=world.bus) is None
    assert store.open_requests() == ()
    assert gate.TOPIC_WITHHELD in world.bus.topics()
    assert gate.TOPIC_REQUESTED not in world.bus.topics()
    assert world.sent == [], "nothing may be sent for a request that was never made"


def test_with_no_owner_configured_nothing_is_asked(world):
    world.monkeypatch.delenv("AUREON_APPROVAL_EMAIL")

    assert gate.request_approval(HELD_ACTION, bus=world.bus) is None
    assert store.open_requests() == ()
    assert world.sent == []
    assert world.bus.payloads(gate.TOPIC_WITHHELD)[0]["reason"].startswith("no approval address")


def test_asking_while_divided_does_not_look_like_asking_while_confident(world):
    confident = _ask(world)

    _confident(world.monkeypatch, divergence=0.42, evidence=0.29)
    divided = gate.request_approval(HELD_ACTION, application_id=APP_ID, bus=world.bus)

    assert divided is not None, "a divided organism may still ask — it must just say so"
    assert divided.grounding.needs_caution is True
    assert compose.CAUTION_HEADING in divided.body_markdown
    assert compose.SUBJECT_CAUTION in divided.subject
    assert "0.42" in divided.body_markdown

    assert confident.grounding.needs_caution is False
    assert compose.CAUTION_HEADING not in confident.body_markdown
    assert compose.SUBJECT_CAUTION not in confident.subject


# ── 6. the switchboard's HOLD is what this resolves ──────────────────────────


def test_resolve_hold_asks_when_the_chain_holds(world):
    request = gate.resolve_hold(HELD_ACTION, application_id=APP_ID, bus=world.bus)

    assert request is not None
    assert request.action == HELD_ACTION
    assert gate.approval_state(request.token) is ApprovalState.PENDING


@pytest.mark.parametrize("action", ["draft_summary", "score_fit", "read_pipeline"])
def test_resolve_hold_does_not_ask_about_reversible_work(world, action):
    # Reversible work is Sero's own. Asking about it would train Gary to rubber
    # stamp, which is how a real gate becomes a formality.
    #
    # This is the case a "did run_chain say HOLD?" test gets wrong: DEFAULT_CHAIN's
    # last gate is requires_human=True, so every completed pass ends in HOLD
    # whatever it was asked about, and every action would be escalated.
    assert gate.resolve_hold(action, bus=world.bus) is None
    assert store.open_requests() == ()
    assert world.sent == []


@pytest.mark.parametrize("action", ["submit_application", "Submit ", "wire-transfer",
                                    "Pay Invoice", "lodge_filing"])
def test_resolve_hold_asks_about_every_inflection_of_an_irreversible_step(world, action):
    assert gate.resolve_hold(action, bus=world.bus) is not None


def test_resolve_hold_still_asks_when_the_chain_would_only_say_redo(world):
    # The trap dossier.py documents: switchboard.evaluate tests blindness and
    # division before it tests hands. A divided organism does not reach the
    # human-held branch through some paths, and a caller reading the chain's
    # terminal decision would see "iterate and come back" for something that was
    # never Sero's to send. The hold must stand anyway.
    _confident(world.monkeypatch, divergence=0.42, evidence=0.29)

    request = gate.resolve_hold(HELD_ACTION, application_id=APP_ID, bus=world.bus)

    assert request is not None
    assert request.grounding.needs_caution is True
    assert gate.approval_state(request.token) is ApprovalState.PENDING


# ── 7. waiting on Gary is a real state of the organism ───────────────────────


def test_waiting_registers_as_pressure_in_the_hnc_field(world):
    from aureon.core.bus_trace import read_trace

    assert gate.waiting_pressure().open_count == 0
    assert gate.publish_pressure(world.bus).symbolic_life_score is None
    assert read_trace("symbolic_subfield") == [], "no ask, no reading, nothing published"

    request = _ask(world)
    fresh = gate.waiting_pressure()
    assert fresh.open_count == 1
    assert fresh.pressure == pytest.approx(0.0)

    world.clock.advance(hours=24)  # half of the 48h window consumed
    half = gate.publish_pressure(world.bus)
    assert half.pressure == pytest.approx(0.5)
    assert half.symbolic_life_score == pytest.approx(0.5)
    assert half.coherence_gamma is None, "this organ measures no Γ and must claim none"

    published = [row for row in read_trace("symbolic_subfield") if row.get("source") == "approval"]
    assert published, "a long-pending approval must reach the shared field"
    assert published[-1]["symbolic_life_score"] == pytest.approx(0.5)

    # Answered: the pressure is gone, and nothing further is published.
    gate.poll_approvals(_Mailbox(_thread(request.token, "yes")), bus=world.bus)
    assert gate.waiting_pressure().open_count == 0
    assert gate.publish_pressure(world.bus).symbolic_life_score is None


def test_the_ledger_survives_a_ttl_that_makes_no_sense(world):
    world.monkeypatch.setenv("AUREON_APPROVAL_TTL_HOURS", "not-a-number")
    assert gate.ttl_hours() == float(compose.DEFAULT_TTL_HOURS)

    world.monkeypatch.setenv("AUREON_APPROVAL_TTL_HOURS", "-5")
    assert gate.ttl_hours() == float(compose.DEFAULT_TTL_HOURS)

    # A misconfigured window falls back to the default; it never becomes infinite.
    request = _ask(world)
    assert request.expires_at > request.created_at
