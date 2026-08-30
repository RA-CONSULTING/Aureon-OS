"""The gated write path, and the submission it is structurally incapable of making.

Hermetic. Every test owns its approval ledger and its action log under
``tmp_path``, holds the clock still, and feeds the organism's readings through the
seams :mod:`aureon.approval.compose` and :mod:`aureon.gates.switchboard` provide.
No network, no SMTP, no browser, no live HNC trace, no live pipeline — and no
portal: the only object in this suite that could touch one is a fake the test
injects, so a call to a real portal would fail with ``AttributeError`` rather than
happen.

The application numbers below are the ones on Gary's live Innovate UK dashboard,
used **as inputs** — 10210100 is the draft at 93% complete, 10210780 is submitted
and awaiting assessment. They appear here and nowhere in ``aureon/``: the module
under test reports what it is given and knows no application numbers of its own.

What this file exists to pin:

1. **There is no submission path.** No callable in the module names a human-held
   step, no kind of action can claim to be one, and a submit intent cannot pass
   the gate chain either. Both layers are tested, because either alone is
   defeatable.
2. **The gate refuses before the owner is troubled.** A chain that does not clear
   yields ``REFUSED_BY_GATE`` with no token, and nobody is asked.
3. **Absence is never approval.** Pending, declined, expired, unknown, and
   approved-for-something-else all leave the value unwritten, each for its own
   recorded reason.
4. **Nothing can write without an injected writer**, and one approval authorises
   exactly one attempt.
5. **Every path leaves an audit line**, refusals included, and no writer's
   exception message leaks into it.
"""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from aureon.approval import compose, gate, store
from aureon.approval.notify import NotifyResult
from aureon.approval.schemas import ApprovalState, is_token
from aureon.connectors.base import ConnectorStatus
from aureon.gates.switchboard import HOLD, GateReading, is_human_held, run_chain
from aureon.portals import actions
from aureon.portals.actions import ActionState, PortalAction
from aureon.portals.schemas import (
    STATE_IN_PROGRESS,
    STATE_SUBMITTED,
    PortalApplication,
    PortalState,
)

NOW = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)

#: Never the owner's real address: a test that embeds a live mailbox is one `sed`
#: away from mailing it.
OWNER = "owner@example.test"

#: Ground truth from the portal, as test input only. A draft, and a filed one.
DRAFT = "10210100"
FILED = "10210780"

FIELD = "project_summary"
VALUE = "Aureon measures phi-squared coherence in repository activity under stress."
WHY = "the draft field is empty and the evidence pack already carries this text"


# ── the world, built from nothing ────────────────────────────────────────────


class _Clock:
    """A clock the tests move by hand. Expiry is a fact about time, so time is the
    one thing these tests control exactly."""

    def __init__(self, start: datetime) -> None:
        self.moment = start

    def __call__(self) -> datetime:
        return self.moment

    def advance(self, **delta: float) -> datetime:
        self.moment = self.moment + timedelta(**delta)
        return self.moment


#: "nothing was passed", distinct from "None was passed" — which is a real case
#: here, because a writer that returns None is one of the outcomes under test.
_UNSET = object()


class _Writer:
    """The only thing in this suite that could touch a portal, and it is injected.

    It has ``write_field`` and nothing else — no ``submit``, no ``file``, no
    ``login``, no session. If the module under test ever reached for one of those
    this stub would raise ``AttributeError`` and the suite would fail. The fake is
    part of the guarantee.

    ``outcome`` is a real :class:`~aureon.connectors.base.ConnectorStatus` so a
    change in that contract breaks this suite instead of silently passing.
    """

    def __init__(self, outcome: object = _UNSET) -> None:
        self.outcome = (ConnectorStatus.ready(source="injected fake portal")
                        if outcome is _UNSET else outcome)
        self.calls: list[tuple[str, str, str]] = []

    def write_field(self, application_number: str, field: str, value: str) -> object:
        self.calls.append((application_number, field, value))
        return self.outcome


class _RaisingWriter:
    """A writer whose failure quotes a secret, the way a real client would."""

    #: Shaped like a session cookie on purpose. It must not reach the audit trail.
    SECRET = "Cookie: IFS_SESSION=not-a-real-session-value"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def write_field(self, application_number: str, field: str, value: str) -> object:
        self.calls.append((application_number, field, value))
        raise RuntimeError(f"portal rejected the request — {self.SECRET}")


class _Bus:
    """Collects thoughts. Publishing is visibility, so it is observed, not asserted on."""

    def __init__(self) -> None:
        self.thoughts: list[object] = []

    def publish(self, thought: object) -> None:
        self.thoughts.append(thought)


def _confident(monkeypatch, *, divergence: float = 0.02, evidence: float = 0.86) -> None:
    """An organism that reads strongly, through the seams the real code uses."""
    monkeypatch.setattr(compose, "_read_field",
                        lambda bus: SimpleNamespace(available=True, coherence_gamma=0.91))
    monkeypatch.setattr(compose, "_read_blend",
                        lambda bus: SimpleNamespace(available=True, divergence=divergence))
    monkeypatch.setattr(compose, "_read_panel",
                        lambda bus: SimpleNamespace(available=True, consensus="RALLY",
                                                    confidence=0.95, evidence_ratio=evidence,
                                                    ungrounded_nodes=("Tiger",)))
    monkeypatch.setattr(
        "aureon.gates.switchboard.read_organism",
        lambda bus=None: GateReading(coherence=0.91, divergence=divergence, life_score=0.88,
                                     panel_consensus="RALLY", panel_confidence=0.95,
                                     panel_evidence=evidence),
    )


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A repository-free world: own ledger, own action log, one configured owner."""
    clock = _Clock(NOW)
    monkeypatch.setattr(gate, "_now", clock)
    monkeypatch.setenv("AUREON_APPROVALS_DIR", str(tmp_path / "approvals"))
    monkeypatch.setenv(actions.DIR_VAR, str(tmp_path / "portals"))
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path / "trace"))
    monkeypatch.setenv("AUREON_HNC_TRACE_PATH", str(tmp_path / "trace" / "hnc_live.jsonl"))
    monkeypatch.setenv("AUREON_APPROVAL_EMAIL", OWNER)
    monkeypatch.delenv("AUREON_OWNER_EMAIL", raising=False)
    monkeypatch.setenv("AUREON_APPROVAL_TTL_HOURS", "48")

    delivered: list[object] = []

    def _deliver(request, *, transport=None, now=None, directory=None):
        delivered.append(request)
        return NotifyResult(sent=True, token=request.token, owner=OWNER, subject=request.subject)

    monkeypatch.setattr(gate, "send_approval_request", _deliver)
    _confident(monkeypatch)
    return SimpleNamespace(tmp=tmp_path, clock=clock, bus=_Bus(), delivered=delivered,
                           monkeypatch=monkeypatch)


def _rows(world) -> list[dict]:
    """Every audit line, in order."""
    path = actions.action_log_path()
    assert path == world.tmp / "portals" / actions.ACTION_LOG_NAME, \
        "the log must live where AUREON_PORTALS_DIR says, or this suite is not hermetic"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _only(world) -> dict:
    rows = _rows(world)
    assert len(rows) == 1, f"expected exactly one audit line, got {len(rows)}"
    return rows[0]


def _propose(world, *, number: str = DRAFT, field: str = FIELD, value: str = VALUE,
             rationale: str = WHY, portal_state: object = STATE_IN_PROGRESS) -> PortalAction:
    return actions.propose_field_update(number, field, value, rationale=rationale,
                                        portal_state=portal_state, bus=world.bus)


def _awaiting(world) -> PortalAction:
    action = _propose(world)
    assert action.state is ActionState.AWAITING_APPROVAL, action.blocker
    return action


def _say_yes(action: PortalAction, *, now: datetime = NOW) -> None:
    """Gary answers, through the real ledger — nothing else can grant this."""
    assert store.resolve(action.approval_token, ApprovalState.APPROVED,
                         "the owner replied yes in the test", now=now)


# ── 1. layer one: the capability is absent, not disabled ─────────────────────

_SOURCE = Path(actions.__file__).read_text(encoding="utf-8")
_DEFINED = re.findall(r"^\s*(?:async\s+)?def\s+(\w+)", _SOURCE, re.M)
_CLASSES = re.findall(r"^\s*class\s+(\w+)", _SOURCE, re.M)


def test_the_source_actually_parsed() -> None:
    """Guard the guards: a regex that matches nothing would pass every test below."""
    assert len(_DEFINED) > 10, "the def scan found nothing — the tests below would be vacuous"
    assert "propose_field_update" in _DEFINED
    assert "PortalAction" in _CLASSES


def test_no_callable_here_names_a_human_held_step() -> None:
    """No submit / file / lodge function exists — not disabled, absent.

    Tested with the switchboard's own vocabulary rather than a hand-written list,
    so the module and the gate that holds those verbs cannot drift apart. It
    catches ``submit``, ``submit_application``, ``resubmit``, ``filing``,
    ``lodgement`` and the rest, per word.
    """
    for name in _DEFINED + _CLASSES:
        assert not is_human_held(name), f"{name} names a step no executor exists for"


def test_no_module_attribute_names_a_human_held_step() -> None:
    """The same test on what the module actually exports at runtime.

    Dunders are excluded: ``__file__`` tokenises to "file" and is held by name,
    which is a fact about the vocabulary and not about this module.
    """
    for name in dir(actions):
        if name.startswith("__"):
            continue
        assert not is_human_held(name), f"actions.{name} names a human-held step"
    for forbidden in ("submit", "submit_application", "submit_field", "file", "file_application",
                      "lodge", "pay", "transfer"):
        assert not hasattr(actions, forbidden), f"actions.{forbidden} must not exist"


def test_no_kind_of_action_can_claim_to_be_a_submission() -> None:
    """``ALLOWED_KINDS`` is a set of one, and it is not a held verb."""
    assert set(actions.ALLOWED_KINDS) == {actions.KIND_FIELD_UPDATE}
    for kind in actions.ALLOWED_KINDS:
        assert not is_human_held(kind)


@pytest.mark.parametrize("kind", ["submit", "submit_application", "file", "lodge", "pay_invoice"])
def test_an_action_describing_a_submission_cannot_be_constructed(kind: str) -> None:
    with pytest.raises(ValueError, match="not a portal action this module performs"):
        PortalAction(kind=kind, application_number=DRAFT, field=FIELD, proposed_value=VALUE,
                     rationale=WHY)


def test_there_is_no_default_writer_anywhere_in_the_module() -> None:
    """Nothing here can produce a writer, so nothing here can reach a portal alone."""
    # No function here builds, resolves or defaults one — the only ``writer`` in the
    # module is a parameter. (The name is asserted over definitions rather than over
    # the source text, so the docstring may go on explaining the absence.)
    assert [n for n in _DEFINED if "writer" in n.lower()] == []
    for name in dir(actions):
        obj = getattr(actions, name)
        if obj is actions.FieldWriter:  # the Protocol declares the method; it is not one
            continue
        assert not hasattr(obj, "write_field"), f"actions.{name} could write to a portal"
    # ``writer`` is a parameter of the applying half only. The deciding half cannot act.
    assert "writer" not in inspect.signature(actions.propose_field_update).parameters
    assert inspect.signature(actions.apply_approved_action).parameters["writer"].default is None


def test_the_module_imports_no_client_that_could_reach_a_portal() -> None:
    forbidden = {"requests", "httpx", "aiohttp", "urllib", "urllib2", "urllib3", "http",
                 "socket", "ssl", "selenium", "playwright", "webbrowser", "pycurl", "mechanize",
                 "subprocess", "smtplib"}
    imported = {mod.split(".")[0] for mod in re.findall(r"^\s*(?:from|import)\s+([\w.]+)",
                                                        _SOURCE, re.M)}
    assert not (imported & forbidden), f"actions.py imports {sorted(imported & forbidden)}"


def test_nothing_here_accepts_a_credential() -> None:
    """No public callable takes a password, a session or a cookie. Ever."""
    forbidden = {"password", "passwd", "username", "user", "cookie", "cookies", "session",
                 "credential", "credentials", "auth", "api_key", "secret", "login"}
    for name, obj in vars(actions).items():
        if name.startswith("_") or not callable(obj) or getattr(obj, "__module__", "") != actions.__name__:
            continue
        params = set(inspect.signature(obj).parameters)
        assert not (params & forbidden), f"{name} accepts {sorted(params & forbidden)}"
    # And it reads exactly one environment variable: where to put its own log.
    assert re.findall(r"os\.environ\.get\(\s*([\w.]+)", _SOURCE) == ["DIR_VAR"]


# ── 2. layer two: the switchboard holds a submit intent by itself ────────────


def test_a_submit_intent_cannot_pass_the_chain_this_module_runs(world) -> None:
    """The second layer, independent of the first.

    Even if a submit function existed, an action naming a held verb HOLDs at the
    first gate of :data:`~aureon.portals.actions.WORK_CHAIN` — so it could never
    reach an approval request through this path.
    """
    verdicts = run_chain({"action": "submit_application"}, chain=actions.WORK_CHAIN,
                         bus=world.bus)
    assert [v.decision for v in verdicts] == [HOLD], "a held verb must stop at the first gate"
    assert not any(v.advanced for v in verdicts)


def test_a_field_named_submit_is_refused_by_name(world) -> None:
    """The smuggling route: writing "yes" into a field *called* submit."""
    action = _propose(world, field="submit", value="yes")
    assert action.state is ActionState.REFUSED_INVALID
    assert "human-held" in (action.blocker or "")
    assert action.approval_token is None
    assert _only(world)["state"] == "REFUSED_INVALID"


@pytest.mark.parametrize("field", ["submit", "Submit ", "submit_declaration", "confirm-and-file",
                                   "lodgement", "payment_details"])
def test_every_inflection_of_a_held_verb_is_refused(world, field: str) -> None:
    action = _propose(world, field=field)
    assert action.state is ActionState.REFUSED_INVALID
    assert action.approval_token is None


# ── 3. the gate refuses before the owner is troubled ────────────────────────


def test_a_redo_chain_refuses_and_asks_nobody(world) -> None:
    """A divided organism yields REFUSED_BY_GATE, no token, and no approval request.

    The second assertion is the important one: a proposal the organism cannot
    justify must not be put in front of Gary as though it could be. Asking anyway
    is how a real gate decays into a rubber stamp.
    """
    asked: list[object] = []
    world.monkeypatch.setattr(actions, "request_approval",
                              lambda *a, **k: asked.append(a) or None)
    _confident(world.monkeypatch, divergence=0.42)  # above Gate.max_divergence

    action = _propose(world)

    assert action.state is ActionState.REFUSED_BY_GATE
    assert action.approval_token is None
    assert asked == [], "the owner must not be asked about work the gates refused"
    assert action.gate_verdicts, "the verdicts that refused it are part of the record"
    assert action.gate_verdicts[0]["decision"] == "REDO"
    row = _only(world)
    assert row["state"] == "REFUSED_BY_GATE"
    assert row["gates"][0]["decision"] == "REDO"


def test_a_blind_organism_refuses_too(world) -> None:
    """Unreadable is not permission — it is REDO at the first gate."""
    world.monkeypatch.setattr("aureon.gates.switchboard.read_organism",
                              lambda bus=None: GateReading())
    action = _propose(world)
    assert action.state is ActionState.REFUSED_BY_GATE
    assert action.approval_token is None


def test_an_application_the_funder_already_holds_is_refused(world) -> None:
    """A submitted application has no draft field to complete."""
    action = _propose(world, number=FILED, portal_state=STATE_SUBMITTED)
    assert action.state is ActionState.REFUSED_INVALID
    assert "already holds it" in (action.blocker or "")
    assert action.approval_token is None
    assert _only(world)["portal_state"] == STATE_SUBMITTED


def test_the_portals_own_prose_is_normalised_not_guessed(world) -> None:
    """The funder writes prose; the refusal uses the shared vocabulary to read it."""
    action = _propose(world, number=FILED, portal_state="Submitted — awaiting assessment")
    assert action.state is ActionState.REFUSED_INVALID
    assert action.portal_state == STATE_SUBMITTED


def test_the_funders_state_is_read_from_the_shared_types(world) -> None:
    """Built from the real :mod:`aureon.portals.schemas` types, not from strings.

    A reader hands over whatever it read — a member of the closed vocabulary, or a
    whole :class:`~aureon.portals.schemas.PortalApplication`. A shape change in
    either breaks this test instead of silently disabling the refusal.
    """
    filed = PortalApplication(number=FILED, title="Advanced Connectivity Technologies",
                              state=STATE_SUBMITTED, state_text="Submitted")
    by_record = _propose(world, number=FILED, portal_state=filed)
    by_member = _propose(world, number=FILED, portal_state=PortalState.SUBMITTED)

    for action in (by_record, by_member):
        assert action.state is ActionState.REFUSED_INVALID
        assert action.portal_state == STATE_SUBMITTED
        assert action.approval_token is None

    draft = PortalApplication(number=DRAFT, state=STATE_IN_PROGRESS, percent_complete=93)
    proceeds = _propose(world, portal_state=draft)
    assert proceeds.state is ActionState.AWAITING_APPROVAL
    assert proceeds.portal_state == STATE_IN_PROGRESS


def test_an_unread_portal_state_is_recorded_as_unread(world) -> None:
    """``None`` means nobody looked. It must never come back as "draft"."""
    action = _propose(world, portal_state=None)
    assert action.portal_state is None
    assert action.state is ActionState.AWAITING_APPROVAL
    assert "not read" in " ".join(action.outstanding)


@pytest.mark.parametrize(("number", "field", "value", "rationale", "expect"), [
    ("", FIELD, VALUE, WHY, "portal reference"),
    ("../../pipeline", FIELD, VALUE, WHY, "portal reference"),
    (10210100.5, FIELD, VALUE, WHY, "portal reference string"),
    (DRAFT, "", VALUE, WHY, "no field was named"),
    (DRAFT, "line\none", VALUE, WHY, "control characters"),
    (DRAFT, FIELD, None, WHY, "must be a string"),
    (DRAFT, FIELD, 42, WHY, "must be a string"),
    (DRAFT, FIELD, "   ", WHY, "blank"),
    (DRAFT, FIELD, "x" * (actions.MAX_VALUE_CHARS + 1), WHY, "refused rather than truncated"),
    (DRAFT, FIELD, VALUE, "", "no rationale"),
])
def test_a_malformed_proposal_is_refused_with_its_reason(world, number, field, value, rationale,
                                                        expect: str) -> None:
    action = actions.propose_field_update(number, field, value, rationale=rationale,
                                          portal_state=STATE_IN_PROGRESS, bus=world.bus)
    assert action.state is ActionState.REFUSED_INVALID
    assert expect in (action.blocker or ""), action.blocker
    assert action.approval_token is None
    assert _only(world)["state"] == "REFUSED_INVALID"


def test_an_oversized_value_is_never_silently_shortened(world) -> None:
    """Gary must approve the text that will actually be written."""
    action = _propose(world, value="x" * (actions.MAX_VALUE_CHARS + 5))
    assert action.state is ActionState.REFUSED_INVALID
    assert str(actions.MAX_VALUE_CHARS + 5) in (action.blocker or "")


# ── 4. asking: a live token, and nothing written ────────────────────────────


def test_a_cleared_chain_asks_gary_and_writes_nothing(world) -> None:
    action = _awaiting(world)

    assert is_token(action.approval_token or "")
    assert action.blocker is None
    assert [v["decision"] for v in action.gate_verdicts] == ["ADVANCE"] * len(actions.WORK_CHAIN)
    assert len(world.delivered) == 1, "asked exactly once"

    row = _only(world)
    assert row["state"] == "AWAITING_APPROVAL"
    assert row["writer"] is None, "no writer was involved in proposing"
    assert row["wrote"] is False


def test_with_nobody_configured_to_ask_nothing_is_proposed(world) -> None:
    """No owner address means no reply could ever approve it, so it is not asked."""
    world.monkeypatch.delenv("AUREON_APPROVAL_EMAIL")

    action = _propose(world)

    assert action.state is ActionState.REFUSED_UNASKABLE
    assert action.approval_token is None
    assert world.delivered == []
    assert _only(world)["state"] == "REFUSED_UNASKABLE"


def test_a_request_it_cannot_justify_is_never_made(world) -> None:
    """The gates cleared, but the organism cannot show Gary why. So it does not ask.

    Reached by leaving the switchboard's reading intact while the grounding seams go
    dark — the two are separate reads, and only the second is what the owner would
    have been shown.
    """
    unreadable = lambda bus: SimpleNamespace(available=False, blocker="nothing to read")  # noqa: E731
    for seam in ("_read_field", "_read_blend", "_read_panel"):
        world.monkeypatch.setattr(compose, seam, unreadable)

    action = _propose(world)

    assert action.state is ActionState.REFUSED_UNASKABLE
    assert action.approval_token is None
    assert world.delivered == []


def test_the_owner_can_read_the_verbatim_value_he_is_approving(world) -> None:
    """An approval request whose substance he cannot see is a rubber stamp."""
    action = _awaiting(world)
    record = json.loads((world.tmp / "approvals" / f"{action.approval_token}.json")
                        .read_text(encoding="utf-8"))
    body = record["request"]["body_markdown"]

    assert VALUE in body, "the exact text that would be written must be in front of him"
    assert WHY in body
    assert FIELD in body
    assert record["request"]["action"] == action.approval_action
    assert record["request"]["application_id"] == DRAFT
    assert record["request"]["state"] == "PENDING"


def test_the_audit_line_measures_the_value_rather_than_copying_it(world) -> None:
    action = _awaiting(world)
    row = _only(world)
    assert row["value_chars"] == len(VALUE)
    assert row["value_sha256"] == action.value_sha256
    assert row["approval_token"] == action.approval_token
    assert row["approval_action"] == action.approval_action
    # A line cannot report whether it was itself written, so it does not pretend to.
    assert "logged" not in row
    assert action.logged is True


# ── 5. applying: four things must hold, and absence is never one of them ────


def test_a_pending_token_cannot_apply(world) -> None:
    """He has not answered. Silence authorises nothing."""
    action = _awaiting(world)
    writer = _Writer()

    applied = actions.apply_approved_action(action, writer, bus=world.bus)

    assert applied.state is ActionState.REFUSED_NOT_APPROVED
    assert "PENDING" in (applied.blocker or "")
    assert writer.calls == [], "the portal must not have been touched"
    assert _rows(world)[-1]["state"] == "REFUSED_NOT_APPROVED"


def test_a_declined_token_cannot_apply(world) -> None:
    action = _awaiting(world)
    assert store.resolve(action.approval_token, ApprovalState.DECLINED, "he said no", now=NOW)
    writer = _Writer()

    applied = actions.apply_approved_action(action, writer, bus=world.bus)

    assert applied.state is ActionState.REFUSED_NOT_APPROVED
    assert "DECLINED" in (applied.blocker or "")
    assert writer.calls == []


def test_an_expired_token_cannot_apply(world) -> None:
    """The clock is part of the answer, whether or not any sweep has run."""
    action = _awaiting(world)
    world.clock.advance(hours=49)  # the configured window is 48
    writer = _Writer()

    applied = actions.apply_approved_action(action, writer, bus=world.bus)

    assert applied.state is ActionState.REFUSED_NOT_APPROVED
    assert "EXPIRED" in (applied.blocker or "")
    assert writer.calls == []


def test_a_late_yes_cannot_apply_either(world) -> None:
    """Approved after the deadline is not approved. The ledger refuses it first."""
    action = _awaiting(world)
    world.clock.advance(hours=49)
    assert not store.resolve(action.approval_token, ApprovalState.APPROVED, "too late",
                             now=world.clock.moment)
    writer = _Writer()

    applied = actions.apply_approved_action(action, writer, bus=world.bus)

    assert applied.state is ActionState.REFUSED_NOT_APPROVED
    assert writer.calls == []


def test_an_unknown_token_cannot_apply(world) -> None:
    """A token nobody can find reads EXPIRED, never PENDING and never approved."""
    action = _awaiting(world)
    (world.tmp / "approvals" / f"{action.approval_token}.json").unlink()
    writer = _Writer()

    applied = actions.apply_approved_action(action, writer, bus=world.bus)

    assert applied.state is ActionState.REFUSED_NOT_APPROVED
    assert writer.calls == []


def test_applying_without_an_injected_writer_is_impossible(world) -> None:
    """Approved, and still nothing happens: there is nothing here that could act."""
    action = _awaiting(world)
    _say_yes(action)

    applied = actions.apply_approved_action(action, bus=world.bus)

    assert applied.state is ActionState.REFUSED_NO_WRITER
    assert applied.blocker == "no writer was injected"
    assert _rows(world)[-1]["state"] == "REFUSED_NO_WRITER"
    # And the ledger still says APPROVED — the refusal was structural, not a verdict.
    assert gate.approval_state(action.approval_token) is ApprovalState.APPROVED


def test_a_writer_without_write_field_is_refused(world) -> None:
    """Something writer-shaped is not a writer."""
    action = _awaiting(world)
    _say_yes(action)

    applied = actions.apply_approved_action(action, SimpleNamespace(), bus=world.bus)

    assert applied.state is ActionState.REFUSED_NO_WRITER
    assert "no callable write_field" in (applied.blocker or "")


def test_the_writer_is_checked_before_the_token_is_read(world) -> None:
    """A missing hand must not burn a live approval."""
    action = _awaiting(world)
    _say_yes(action)

    actions.apply_approved_action(action, None, bus=world.bus)
    row = _rows(world)[-1]
    assert row["approval_state_at_write"] is None, \
        "the ledger should not even have been consulted"


def test_an_approved_token_writes_exactly_what_was_approved(world) -> None:
    action = _awaiting(world)
    _say_yes(action)
    writer = _Writer()

    applied = actions.apply_approved_action(action, writer, bus=world.bus)

    assert applied.state is ActionState.APPLIED
    assert applied.wrote is True
    assert applied.blocker is None
    assert writer.calls == [(DRAFT, FIELD, VALUE)], "verbatim, and once"
    row = _rows(world)[-1]
    assert row["state"] == "APPLIED"
    assert row["writer"] == "_Writer"
    assert row["approval_state_at_write"] == "APPROVED"
    assert row["wrote"] is True


def test_one_approval_authorises_one_attempt(world) -> None:
    """A stale copy of the awaiting action cannot be replayed against the same token."""
    action = _awaiting(world)
    _say_yes(action)
    writer = _Writer()

    first = actions.apply_approved_action(action, writer, bus=world.bus)
    second = actions.apply_approved_action(action, writer, bus=world.bus)

    assert first.state is ActionState.APPLIED
    assert second.state is ActionState.REFUSED_TOKEN_SPENT
    assert len(writer.calls) == 1, "the value must have been written exactly once"
    assert gate.approval_state(action.approval_token) is ApprovalState.APPROVED, \
        "the brake is this module's, not a mutation of the owner's ledger"


def test_an_already_applied_action_cannot_be_applied_again(world) -> None:
    action = _awaiting(world)
    _say_yes(action)
    writer = _Writer()
    applied = actions.apply_approved_action(action, writer, bus=world.bus)

    again = actions.apply_approved_action(applied, writer, bus=world.bus)

    assert again.state is ActionState.REFUSED_NOT_APPROVED
    assert "not AWAITING_APPROVAL" in (again.blocker or "")
    assert len(writer.calls) == 1


def test_a_failed_attempt_also_spends_the_approval(world) -> None:
    """A blocker does not prove the write did not land, so a retry needs a fresh ask."""
    action = _awaiting(world)
    _say_yes(action)
    writer = _Writer(ConnectorStatus.blocked("no authenticated session in the operator browser"))

    first = actions.apply_approved_action(action, writer, bus=world.bus)
    second = actions.apply_approved_action(action, _Writer(), bus=world.bus)

    assert first.state is ActionState.WRITE_FAILED
    assert "no authenticated session" in (first.blocker or "")
    assert second.state is ActionState.REFUSED_TOKEN_SPENT


def test_a_token_approved_for_another_field_cannot_be_spent_here(world) -> None:
    """Token scope is "this approval was for this", not "an approval exists".

    The action name is derived from the fields, never stored, so editing the record
    changes the name and the ledger refuses it. Tampering fails closed.
    """
    action = _awaiting(world)
    _say_yes(action)
    writer = _Writer()

    moved = replace(action, field="finance_summary")
    applied = actions.apply_approved_action(moved, writer, bus=world.bus)

    assert applied.state is ActionState.REFUSED_NOT_APPROVED
    assert "not issued for this exact action" in (applied.blocker or "")
    assert writer.calls == []


def test_a_token_approved_for_another_application_cannot_be_spent_here(world) -> None:
    action = _awaiting(world)
    _say_yes(action)
    writer = _Writer()

    moved = replace(action, application_number=FILED)
    applied = actions.apply_approved_action(moved, writer, bus=world.bus)

    assert applied.state is ActionState.REFUSED_NOT_APPROVED
    assert writer.calls == []


def test_a_writer_that_says_nothing_is_recorded_as_unknown(world) -> None:
    """Not applied, not failed: unverified. Neither lie is available."""
    action = _awaiting(world)
    _say_yes(action)
    writer = _Writer(None)

    applied = actions.apply_approved_action(action, writer, bus=world.bus)

    assert applied.state is ActionState.WRITE_UNVERIFIED
    assert applied.wrote is False
    assert "does not say whether the write landed" in (applied.blocker or "")
    assert writer.calls == [(DRAFT, FIELD, VALUE)]


def test_a_writers_exception_message_never_reaches_the_trail(world) -> None:
    """The one place a session cookie could leak into this repository."""
    action = _awaiting(world)
    _say_yes(action)
    writer = _RaisingWriter()

    applied = actions.apply_approved_action(action, writer, bus=world.bus)

    assert applied.state is ActionState.WRITE_FAILED
    assert applied.blocker == "the writer raised RuntimeError"
    log_text = actions.action_log_path().read_text(encoding="utf-8")
    assert _RaisingWriter.SECRET not in log_text
    assert "IFS_SESSION" not in log_text


# ── 6. the trail: one line per action, on every path ────────────────────────


def test_every_path_leaves_exactly_one_audit_line(world) -> None:
    """Refusals included — they are the evidence the system stopped."""
    expected: list[str] = []

    expected.append("REFUSED_INVALID")
    _propose(world, field="submit")

    expected.append("REFUSED_INVALID")
    _propose(world, number=FILED, portal_state=STATE_SUBMITTED)

    action = _awaiting(world)
    expected.append("AWAITING_APPROVAL")

    expected.append("REFUSED_NOT_APPROVED")
    actions.apply_approved_action(action, _Writer(), bus=world.bus)

    _say_yes(action)
    expected.append("REFUSED_NO_WRITER")
    actions.apply_approved_action(action, bus=world.bus)

    expected.append("APPLIED")
    actions.apply_approved_action(action, _Writer(), bus=world.bus)

    expected.append("REFUSED_TOKEN_SPENT")
    actions.apply_approved_action(action, _Writer(), bus=world.bus)

    rows = _rows(world)
    assert [r["state"] for r in rows] == expected
    for row in rows:
        assert row["timestamp"], "every line is stamped"
        assert row["kind"] == actions.KIND_FIELD_UPDATE
        assert row["application_number"] in {DRAFT, FILED}
        assert (row["blocker"] is None) == (row["state"] in {"AWAITING_APPROVAL", "APPLIED"})


def test_a_refusal_before_the_gates_still_records_the_action(world) -> None:
    """The earliest possible refusal is still a line, or the trail has holes."""
    actions.propose_field_update(None, None, None, rationale=None, bus=world.bus)
    row = _only(world)
    assert row["state"] == "REFUSED_INVALID"
    assert row["approval_token"] is None
    assert row["gates"] == []


def test_the_log_is_appended_never_rewritten(world) -> None:
    _propose(world, field="submit")
    first = actions.action_log_path().read_text(encoding="utf-8")
    _propose(world, field="lodge")
    second = actions.action_log_path().read_text(encoding="utf-8")
    assert second.startswith(first)
    assert len(_rows(world)) == 2


def test_an_explicit_root_is_honoured_verbatim(tmp_path) -> None:
    """No environment fallback: a caller's tree is the caller's tree."""
    assert actions.portals_dir(tmp_path) == tmp_path / "state" / "portals"
    assert actions.action_log_path(tmp_path) == tmp_path / "state" / "portals" / "action_log.jsonl"
    assert actions.DEFAULT_PORTALS_DIR.parts[-2:] == ("state", "portals")


def test_an_unreadable_log_refuses_the_write(world, monkeypatch) -> None:
    """Fail closed: a token that cannot be proven unspent is not spent."""
    action = _awaiting(world)
    _say_yes(action)

    def _boom(*a, **k):
        raise OSError("log is unreadable")

    monkeypatch.setattr(Path, "open", _boom)
    writer = _Writer()
    applied = actions.apply_approved_action(action, writer, bus=world.bus)

    assert applied.state is ActionState.REFUSED_TOKEN_SPENT
    assert "could not prove this token is unspent" in (applied.blocker or "")
    assert writer.calls == []


# ── 7. the record type itself makes dishonesty unrepresentable ──────────────


def test_a_refusal_must_state_its_blocker() -> None:
    with pytest.raises(ValueError, match="must state its blocker"):
        PortalAction(kind=actions.KIND_FIELD_UPDATE, application_number=DRAFT, field=FIELD,
                     proposed_value=VALUE, rationale=WHY,
                     state=ActionState.REFUSED_BY_GATE)


def test_an_applied_action_cannot_also_carry_a_blocker() -> None:
    with pytest.raises(ValueError, match="cannot also carry a blocker"):
        PortalAction(kind=actions.KIND_FIELD_UPDATE, application_number=DRAFT, field=FIELD,
                     proposed_value=VALUE, rationale=WHY, state=ActionState.APPLIED,
                     approval_token="a" * 43, blocker="but also this")


def test_anything_claiming_authority_must_carry_its_token() -> None:
    for state in (ActionState.AWAITING_APPROVAL, ActionState.APPLIED,
                  ActionState.WRITE_FAILED, ActionState.WRITE_UNVERIFIED):
        with pytest.raises(ValueError, match="must carry the approval token"):
            PortalAction(kind=actions.KIND_FIELD_UPDATE, application_number=DRAFT, field=FIELD,
                         proposed_value=VALUE, rationale=WHY, state=state,
                         blocker=None if state is ActionState.APPLIED else "stated")


def test_an_invented_state_is_refused() -> None:
    with pytest.raises(ValueError, match="not a portal action state"):
        PortalAction(kind=actions.KIND_FIELD_UPDATE, application_number=DRAFT, field=FIELD,
                     proposed_value=VALUE, rationale=WHY, state="APPROVED_BY_ME")


def _specimen(state: ActionState) -> PortalAction:
    """A minimally valid action in one state. The invariants make this fiddly on purpose."""
    quiet = {ActionState.PROPOSED, ActionState.APPLIED, ActionState.AWAITING_APPROVAL}
    return PortalAction(
        kind=actions.KIND_FIELD_UPDATE, application_number=DRAFT, field=FIELD,
        proposed_value=VALUE, rationale=WHY, state=state,
        blocker=None if state in quiet else "a recorded reason",
        approval_token=("t" * 43) if (state is ActionState.AWAITING_APPROVAL
                                     or state.attempted_write) else None,
    )


def test_only_applied_means_written() -> None:
    """One state means "yes". Every other state, including the unverified one, does not."""
    assert {state for state in ActionState if _specimen(state).wrote} == {ActionState.APPLIED}
    assert ActionState.APPLIED.attempted_write
    assert ActionState.WRITE_FAILED.attempted_write
    assert ActionState.WRITE_UNVERIFIED.attempted_write
    assert not ActionState.AWAITING_APPROVAL.attempted_write
    assert not ActionState.REFUSED_BY_GATE.attempted_write
    assert all(s.refused for s in ActionState if s.value.startswith("REFUSED_"))


def test_apply_refuses_anything_that_is_not_a_portal_action() -> None:
    with pytest.raises(TypeError, match="expects a PortalAction"):
        actions.apply_approved_action(SimpleNamespace(state="AWAITING_APPROVAL"), _Writer())
