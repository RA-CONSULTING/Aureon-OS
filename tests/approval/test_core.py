"""The final approval gate: the question, the ledger, and the six properties.

Hermetic. Every test builds its own grounding, its own request and its own
``tmp_path`` ledger; the field readers are stubbed at their seams so nothing here
reads the live organism, the live ``state/`` directory, or the environment except
through ``monkeypatch``. No socket is opened — there is nothing in these modules
that could open one.

What this suite exists to pin down, in the owner's own terms:

- **A request without grounding is not created.** Not "is flagged" — cannot be
  constructed, at two independent layers. Sero does not ask for authority she
  cannot justify.
- **The caution block appears exactly when she is divided or thinly evidenced**,
  including at the boundaries and including when the reading is missing
  altogether, because unmeasured is not calm.
- **Single use.** A token, once resolved, is spent. A replayed reply is inert.
  UNCLEAR and IGNORED deliberately do *not* spend it — a stranger must not be able
  to burn Gary's token before he answers.
- **Expiry.** A late yes is refused and the request is closed as EXPIRED. An old
  yes cannot authorise a fresh action.
- **Owner-locked recipient.** No public callable in the whole package accepts a
  destination, and the only address resolvers take no arguments at all.

``tests/approval/test_reply.py`` and ``test_notify.py`` cover the reading of a
message and the sending of one. The two tests at the end of this file are the
seam between them: they use the *real* composed body to prove that an echo of
Sero's own question can never be read as Gary's answer to it.
"""

from __future__ import annotations

import importlib
import inspect
import json
import logging
import pkgutil
from dataclasses import fields as dataclass_fields
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

import aureon.approval as approval_pkg
from aureon.approval import compose, config, store
from aureon.approval.compose import (
    CAUTION_HEADING,
    QUESTION,
    SUBJECT_CAUTION,
    TOKEN_TAG,
    compose_request,
    render_body,
    subject_line,
)
from aureon.approval.schemas import (
    MAX_DIVERGENCE,
    MIN_EVIDENCE,
    OPEN_STATES,
    TERMINAL_STATES,
    ApprovalRequest,
    ApprovalState,
    GroundingSnapshot,
    is_token,
    new_token,
)

MOMENT = datetime(2026, 7, 31, 9, 0, tzinfo=UTC)
OWNER = "gary@aureonzorzatechnologies.com"


# ── builders ─────────────────────────────────────────────────────────────────


def _grounding(**kw) -> GroundingSnapshot:
    """A confident, fully grounded reading — the baseline the tests vary from."""
    base = {
        "coherence": 0.82,
        "divergence": 0.10,
        "panel_consensus": "RALLY",
        "panel_confidence": 0.9,
        "panel_evidence": 1.0,
        "gate_verdicts": ({"gate": "act", "decision": "ADVANCE", "confidence": 0.9,
                           "reasoning": "evidence supports it", "dissent": []},
                          {"gate": "submit", "decision": "HOLD", "confidence": 0.9,
                           "reasoning": "no automatic executor exists for this step",
                           "dissent": []}),
    }
    base.update(kw)
    return GroundingSnapshot(**base)


def _request(**kw) -> ApprovalRequest:
    token = kw.pop("token", None) or new_token()
    created = kw.pop("created_at", MOMENT)
    ttl = kw.pop("ttl_hours", 72)
    action = kw.pop("action", "submit")
    grounding = kw.pop("grounding", None) or _grounding()
    fields = {
        "token": token,
        "subject": f"{action} — APP-TEST-1",
        "action": action,
        "application_id": "APP-TEST-1",
        "body_markdown": f"# {QUESTION}\n\nToken `[{TOKEN_TAG} {token}]`",
        "created_at": created,
        "expires_at": created + timedelta(hours=ttl),
        "grounding": grounding,
        "state": ApprovalState.PENDING,
    }
    fields.update(kw)
    return ApprovalRequest(**fields)


@pytest.fixture()
def owner_env(monkeypatch):
    """The owner configured, and nothing else in the environment."""
    monkeypatch.setenv(config.APPROVAL_EMAIL_VAR, OWNER)
    monkeypatch.delenv(config.OWNER_EMAIL_VAR, raising=False)
    return OWNER


@pytest.fixture()
def live_readings(monkeypatch):
    """Stub the organism at compose's seams. Returns the knobs to turn."""
    state = SimpleNamespace(
        field=SimpleNamespace(available=True, coherence_gamma=0.82),
        blend=SimpleNamespace(available=True, divergence=0.10),
        panel=SimpleNamespace(available=True, consensus="RALLY", confidence=0.9,
                              evidence_ratio=1.0, ungrounded_nodes=("Tiger", "Panda"),
                              blocker=None),
        verdicts=({"gate": "submit", "decision": "HOLD", "confidence": 0.9,
                   "reasoning": "no automatic executor exists for this step",
                   "dissent": []},),
    )
    monkeypatch.setattr(compose, "_read_field", lambda bus: state.field)
    monkeypatch.setattr(compose, "_read_blend", lambda bus: state.blend)
    monkeypatch.setattr(compose, "_read_panel", lambda bus: state.panel)
    monkeypatch.setattr(compose, "_run_gates", lambda action, app_id, bus: state.verdicts)
    return state


# ── a request that cannot show its grounding does not exist ──────────────────


def test_a_request_without_grounding_cannot_be_constructed():
    with pytest.raises(ValueError, match="grounding"):
        _request(grounding=GroundingSnapshot())


def test_a_request_with_one_real_reading_is_enough_to_ask():
    # Only the panel spoke. Thin, so it will be cautioned — but it is a reading,
    # and a reading is what makes the question answerable.
    request = _request(grounding=GroundingSnapshot(panel_consensus="NEUTRAL"))
    assert request.state is ApprovalState.PENDING
    assert request.grounding.readable is True


def test_compose_returns_none_when_nothing_of_the_organism_can_be_read(
        live_readings, caplog):
    live_readings.field = SimpleNamespace(available=False)
    live_readings.blend = SimpleNamespace(available=False)
    live_readings.panel = SimpleNamespace(available=False, blocker="panel unavailable: ImportError")
    live_readings.verdicts = ()
    with caplog.at_level(logging.WARNING, logger="aureon.approval.compose"):
        assert compose_request("submit", application_id="APP-1") is None
    assert "no grounding could be read" in caplog.text
    assert "cannot justify" in caplog.text


def test_compose_builds_the_question_from_real_readings(live_readings):
    request = compose_request("submit", application_id="APP-1", ttl_hours=72, now=MOMENT)
    assert request is not None
    assert request.body_markdown.startswith(f"# {QUESTION}")
    assert request.action == "submit" and request.application_id == "APP-1"
    assert request.state is ApprovalState.PENDING
    assert request.expires_at == MOMENT + timedelta(hours=72)
    assert is_token(request.token) and request.token in request.body_markdown
    # The grounding travels with the question, not as a footnote.
    assert "GROUNDING" in request.body_markdown
    assert "0.820" in request.body_markdown          # Γ
    assert "0.100" in request.body_markdown          # divergence
    assert "RALLY" in request.body_markdown          # the nine nodes
    assert "HOLD" in request.body_markdown           # the verdict that got her here
    assert request.grounding.is_coherent is True


def test_compose_refuses_an_unnamed_action_or_a_dead_deadline(live_readings):
    assert compose_request("   ") is None
    assert compose_request("submit", ttl_hours=0) is None
    assert compose_request("submit", ttl_hours=-4) is None


def test_every_request_carries_its_own_unguessable_token(live_readings):
    tokens = {compose_request("submit", now=MOMENT).token for _ in range(25)}
    assert len(tokens) == 25
    assert all(len(t) >= 40 for t in tokens)


def test_the_title_leaves_the_token_to_the_sender(live_readings):
    """The composer must not duplicate ``notify``'s tag — one token, one place."""
    request = compose_request("submit", application_id="APP-1", now=MOMENT)
    assert TOKEN_TAG not in request.subject
    assert request.token not in request.subject
    assert "submit" in request.subject and "APP-1" in request.subject

    notify = pytest.importorskip("aureon.approval.notify")
    wire = notify.subject_line(request)
    assert wire.count(request.token) == 1
    assert wire.count(f"[{TOKEN_TAG}") == 1


# ── asking while divided must not look like asking while confident ──────────


CAUTION_CASES = [
    # (divergence, evidence, cautioned, why)
    (0.10, 1.00, False, "coherent and fully grounded"),
    (0.3499, 0.50, False, "just inside both bars"),
    (0.35, 1.00, True, "divergence exactly at the caution threshold"),
    (0.80, 1.00, True, "plainly divided"),
    (0.10, 0.49, True, "panel just below the evidence bar"),
    (0.10, 0.00, True, "panel voting entirely on constants"),
    (None, 1.00, True, "divergence never measured — unmeasured is not calm"),
    (0.10, None, True, "evidence ratio unknown — cannot be vouched for"),
    (None, None, True, "neither measured"),
]


@pytest.mark.parametrize(("divergence", "evidence", "cautioned", "why"), CAUTION_CASES)
def test_the_caution_block_appears_exactly_when_she_is_divided_or_thin(
        divergence, evidence, cautioned, why):
    grounding = _grounding(divergence=divergence, panel_evidence=evidence)
    assert grounding.needs_caution is cautioned, why
    body = render_body("submit", new_token(), grounding=grounding, created_at=MOMENT,
                       expires_at=MOMENT + timedelta(hours=72))
    assert (CAUTION_HEADING in body) is cautioned, why
    # And the question itself is always the first thing on the page.
    assert body.startswith(f"# {QUESTION}")


def test_the_caution_block_says_which_bar_was_crossed():
    divided = render_body("submit", new_token(), grounding=_grounding(divergence=0.62),
                          created_at=MOMENT, expires_at=MOMENT + timedelta(hours=1))
    assert "does not agree with itself" in divided
    assert "0.620" in divided and str(MAX_DIVERGENCE) in divided

    thin = render_body("submit", new_token(), grounding=_grounding(panel_evidence=0.28),
                       created_at=MOMENT, expires_at=MOMENT + timedelta(hours=1))
    assert "voted thin" in thin and "28%" in thin and f"{MIN_EVIDENCE:.0%}" in thin

    unmeasured = render_body("submit", new_token(), grounding=_grounding(divergence=None),
                             created_at=MOMENT, expires_at=MOMENT + timedelta(hours=1))
    assert "never measured whether I agree with myself" in unmeasured


def test_a_cautioned_request_is_cautioned_in_the_subject_too(live_readings):
    confident = compose_request("submit", now=MOMENT)
    assert SUBJECT_CAUTION not in confident.subject
    assert CAUTION_HEADING not in confident.body_markdown

    live_readings.blend = SimpleNamespace(available=True, divergence=0.71)
    divided = compose_request("submit", now=MOMENT)
    assert SUBJECT_CAUTION in divided.subject
    assert CAUTION_HEADING in divided.body_markdown
    assert divided.grounding.is_coherent is False


def test_coherence_is_derived_from_divergence_not_asserted():
    lie = GroundingSnapshot(divergence=0.9, panel_consensus="RALLY", is_coherent=True)
    assert lie.is_coherent is False and lie.divided is True
    # And it survives a round trip through the ledger the same way.
    assert GroundingSnapshot.from_dict(lie.to_dict()).is_coherent is False
    honest = GroundingSnapshot(divergence=0.01, is_coherent=False)
    assert honest.is_coherent is True


def test_the_body_tells_gary_the_rules_he_is_playing_by(live_readings):
    body = compose_request("submit", now=MOMENT).body_markdown
    assert "expires" in body.lower()
    assert "single-use" in body.lower() or "single use" in body.lower()
    assert "not** approval" in body or "not approval" in body


# ── single use ──────────────────────────────────────────────────────────────


def test_a_yes_lands_once_and_never_again(tmp_path):
    request = _request()
    path = store.save(request, root=tmp_path)
    assert path == tmp_path / "state" / "approvals" / f"{request.token}.json"

    assert store.resolve(request.token, ApprovalState.APPROVED, "owner said yes",
                         root=tmp_path, now=MOMENT) is True
    assert store.load(request.token, root=tmp_path).state is ApprovalState.APPROVED

    # The same reply, delivered twice.
    assert store.resolve(request.token, ApprovalState.APPROVED, "the same reply again",
                         root=tmp_path, now=MOMENT) is False
    # And a later change of mind cannot reopen a spent token either.
    assert store.resolve(request.token, ApprovalState.DECLINED, "actually, no",
                         root=tmp_path, now=MOMENT) is False
    assert store.load(request.token, root=tmp_path).state is ApprovalState.APPROVED


def test_a_no_is_just_as_final(tmp_path):
    request = _request()
    store.save(request, root=tmp_path)
    assert store.resolve(request.token, ApprovalState.DECLINED, "owner said no",
                         root=tmp_path, now=MOMENT) is True
    assert store.resolve(request.token, ApprovalState.APPROVED, "a second, later yes",
                         root=tmp_path, now=MOMENT) is False
    assert store.load(request.token, root=tmp_path).state is ApprovalState.DECLINED


@pytest.mark.parametrize("non_answer", [ApprovalState.UNCLEAR, ApprovalState.IGNORED])
def test_a_non_answer_does_not_burn_the_token(tmp_path, non_answer):
    """UNCLEAR and IGNORED are recorded, and Gary can still answer afterwards."""
    request = _request()
    store.save(request, root=tmp_path)
    assert store.resolve(request.token, non_answer, "not an answer",
                         root=tmp_path, now=MOMENT) is True
    still_open = store.load(request.token, root=tmp_path)
    assert still_open.state is non_answer
    assert still_open.state in OPEN_STATES and still_open.resolved is False
    assert store.resolve(request.token, ApprovalState.APPROVED, "owner's actual yes",
                         root=tmp_path, now=MOMENT) is True
    assert store.load(request.token, root=tmp_path).state is ApprovalState.APPROVED


def test_saving_a_token_twice_is_refused(tmp_path):
    request = _request()
    store.save(request, root=tmp_path)
    store.resolve(request.token, ApprovalState.APPROVED, "yes", root=tmp_path, now=MOMENT)
    # A re-save would reset a resolved approval to PENDING. There is no such path.
    with pytest.raises(FileExistsError):
        store.save(request, root=tmp_path)
    assert store.load(request.token, root=tmp_path).state is ApprovalState.APPROVED


def test_resolving_what_was_never_asked_changes_nothing(tmp_path):
    assert store.resolve(new_token(), ApprovalState.APPROVED, "a yes from nowhere",
                         root=tmp_path) is False
    assert store.tokens(root=tmp_path) == ()


def test_a_request_cannot_be_pushed_back_to_pending(tmp_path):
    request = _request()
    store.save(request, root=tmp_path)
    assert store.resolve(request.token, ApprovalState.PENDING, "un-ask it",
                         root=tmp_path, now=MOMENT) is False
    assert store.resolve(request.token, "nonsense", "?", root=tmp_path, now=MOMENT) is False
    assert store.load(request.token, root=tmp_path).state is ApprovalState.PENDING


def test_the_ledger_keeps_the_evidence_for_every_step(tmp_path):
    request = _request()
    store.save(request, root=tmp_path)
    store.resolve(request.token, ApprovalState.UNCLEAR, "reply said maybe",
                  root=tmp_path, now=MOMENT)
    store.resolve(request.token, ApprovalState.APPROVED, "reply from gary said yes",
                  root=tmp_path, now=MOMENT)
    record = store.load_record(request.token, root=tmp_path)
    states = [entry["state"] for entry in record["history"]]
    assert states == ["PENDING", "UNCLEAR", "APPROVED"]
    assert "reply from gary said yes" in record["history"][-1]["evidence"]
    assert record["resolved_at"] is not None


# ── expiry ──────────────────────────────────────────────────────────────────


def test_an_old_yes_cannot_authorise_a_fresh_action(tmp_path):
    request = _request(ttl_hours=72)
    store.save(request, root=tmp_path)
    late = MOMENT + timedelta(hours=73)

    assert store.resolve(request.token, ApprovalState.APPROVED, "yes, four days later",
                         root=tmp_path, now=late) is False
    expired = store.load(request.token, root=tmp_path)
    assert expired.state is ApprovalState.EXPIRED
    assert expired.approved is False and expired.resolved is True

    # And the expired token is spent: the late yes cannot be retried.
    assert store.resolve(request.token, ApprovalState.APPROVED, "yes, again",
                         root=tmp_path, now=late) is False
    assert store.load(request.token, root=tmp_path).state is ApprovalState.EXPIRED
    # The refusal is on the record, with the answer that arrived too late.
    history = store.load_record(request.token, root=tmp_path)["history"]
    assert "expired at" in history[-1]["evidence"]
    assert "APPROVED" in history[-1]["evidence"]


def test_a_yes_inside_the_window_stands(tmp_path):
    request = _request(ttl_hours=72)
    store.save(request, root=tmp_path)
    assert store.resolve(request.token, ApprovalState.APPROVED, "yes, same day",
                         root=tmp_path, now=MOMENT + timedelta(hours=71, minutes=59)) is True
    assert store.load(request.token, root=tmp_path).approved is True


def test_the_deadline_is_the_deadline(tmp_path):
    request = _request(ttl_hours=1)
    store.save(request, root=tmp_path)
    assert store.resolve(request.token, ApprovalState.APPROVED, "yes, on the stroke",
                         root=tmp_path, now=MOMENT + timedelta(hours=1)) is False
    assert store.load(request.token, root=tmp_path).state is ApprovalState.EXPIRED


def test_the_sweep_expires_only_what_is_open_and_overdue(tmp_path):
    overdue = _request(ttl_hours=1)
    answered = _request(ttl_hours=1)
    live = _request(ttl_hours=500)
    for request in (overdue, answered, live):
        store.save(request, root=tmp_path)
    store.resolve(answered.token, ApprovalState.APPROVED, "yes, in time",
                  root=tmp_path, now=MOMENT)

    swept = store.expire_overdue(root=tmp_path, now=MOMENT + timedelta(hours=48))
    assert swept == (overdue.token,)
    assert store.load(answered.token, root=tmp_path).state is ApprovalState.APPROVED
    assert store.load(live.token, root=tmp_path).state is ApprovalState.PENDING
    assert {r.token for r in store.open_requests(root=tmp_path)} == {live.token}


# ── fail closed ─────────────────────────────────────────────────────────────


@pytest.mark.parametrize("bad", ["../../data/research/grants/pipeline", "short", "",
                                 "has spaces in it", "tok/../en", None, 17])
def test_a_malformed_token_cannot_steer_a_write(tmp_path, bad):
    with pytest.raises(ValueError):
        store.record_path(bad, root=tmp_path)
    assert store.load(bad, root=tmp_path) is None
    assert store.resolve(bad, ApprovalState.APPROVED, "yes", root=tmp_path) is False


def test_an_unreadable_record_approves_nothing(tmp_path):
    request = _request()
    path = store.save(request, root=tmp_path)
    path.write_text("{ this is not json", encoding="utf-8")
    assert store.load(request.token, root=tmp_path) is None
    assert store.resolve(request.token, ApprovalState.APPROVED, "yes", root=tmp_path) is False


def test_a_record_that_disagrees_with_its_own_filename_is_refused(tmp_path):
    request = _request()
    path = store.save(request, root=tmp_path)
    record = json.loads(path.read_text(encoding="utf-8"))
    record["request"]["token"] = new_token()          # hand-edited ledger
    path.write_text(json.dumps(record), encoding="utf-8")
    assert store.load(request.token, root=tmp_path) is None
    assert store.resolve(request.token, ApprovalState.APPROVED, "yes", root=tmp_path) is False


def test_the_write_leaves_no_debris(tmp_path):
    request = _request()
    store.save(request, root=tmp_path)
    store.resolve(request.token, ApprovalState.APPROVED, "yes", root=tmp_path, now=MOMENT)
    directory = store.approvals_dir(tmp_path)
    assert [p.name for p in directory.iterdir()] == [f"{request.token}.json"]


def test_an_explicit_root_is_honoured_and_never_reaches_into_the_repository(tmp_path, monkeypatch):
    monkeypatch.setenv(store.DIR_VAR, str(tmp_path / "from-the-environment"))
    assert store.approvals_dir(tmp_path) == tmp_path / "state" / "approvals"
    assert store.approvals_dir() == tmp_path / "from-the-environment"
    assert store.DEFAULT_APPROVALS_DIR.name == "approvals"


# ── property 1: she can only ever ask the owner ──────────────────────────────


# Names that would mean "somebody told this function where to send". An inbound
# address being *verified* (``from_header``, ``candidate``, ``owner_address``) is a
# different thing and is allowed; a destination is not.
DESTINATION_PARAMS = frozenset({
    "to", "to_address", "to_addr", "to_addrs", "to_email", "toaddr", "recipient",
    "recipients", "rcpt", "rcpt_to", "cc", "bcc", "send_to", "sendto", "mailto",
    "destination", "destinations", "dest", "addressee", "addressees", "envelope_to",
    "reply_to", "forward_to",
})


def _public_callables():
    """Every public callable in the package, module by module, methods included."""
    found: list[tuple[str, object]] = []
    for info in pkgutil.iter_modules(approval_pkg.__path__):
        module = importlib.import_module(f"{approval_pkg.__name__}.{info.name}")
        names = getattr(module, "__all__", None) or [
            n for n in vars(module) if not n.startswith("_")]
        for name in names:
            obj = getattr(module, name, None)
            if isinstance(obj, type):
                found.append((f"{info.name}.{name}", obj))
                for attr, member in vars(obj).items():
                    if not attr.startswith("_") and callable(member):
                        found.append((f"{info.name}.{name}.{attr}", member))
            elif callable(obj):
                found.append((f"{info.name}.{name}", obj))
    return found


def test_no_public_callable_in_the_package_accepts_a_recipient():
    """The structural form of property 1: there is nothing to pass an address to."""
    checked = 0
    for label, obj in _public_callables():
        try:
            signature = inspect.signature(obj)
        except (TypeError, ValueError):  # pragma: no cover — unsignable builtins
            continue
        checked += 1
        offending = sorted(p.lower() for p in signature.parameters if p.lower() in DESTINATION_PARAMS)
        assert not offending, f"{label} accepts a destination argument: {offending}"
    assert checked > 20, "the signature walk found almost nothing — it is not looking"


def test_the_only_address_resolvers_take_no_arguments():
    for label, obj in _public_callables():
        if "owner_address" in label.rsplit(".", 1)[-1]:
            assert inspect.signature(obj).parameters == {}, (
                f"{label} must resolve the address itself, not be handed one")
    assert inspect.signature(config.owner_address).parameters == {}


def test_a_request_has_no_field_that_could_hold_a_destination():
    names = {f.name.lower() for f in dataclass_fields(ApprovalRequest)}
    assert not names & DESTINATION_PARAMS
    assert "email" not in names and "address" not in names


def test_the_packages_public_surface_stays_lean():
    assert approval_pkg.__all__ == sorted(approval_pkg.__all__)
    for name in approval_pkg.__all__:
        assert hasattr(approval_pkg, name), f"{name} is exported but missing"


# ── the configured address, and the flag it collides with ────────────────────


def test_the_approval_address_wins_when_it_is_an_address(owner_env):
    assert config.owner_address() == OWNER
    assert config.owner_configured() is True


def test_a_feature_flag_value_is_not_an_address(monkeypatch):
    """``AUREON_APPROVAL_EMAIL=1`` is the existing boolean toggle, not a mailbox."""
    monkeypatch.setenv(config.APPROVAL_EMAIL_VAR, "1")
    monkeypatch.setenv(config.OWNER_EMAIL_VAR, OWNER)
    assert config.owner_address() == OWNER


def test_two_addresses_resolve_to_nobody(monkeypatch):
    monkeypatch.setenv(config.APPROVAL_EMAIL_VAR, f"{OWNER}, funder@example.org")
    monkeypatch.delenv(config.OWNER_EMAIL_VAR, raising=False)
    assert config.owner_address() is None
    assert config.is_owner(OWNER) is False


def test_nobody_configured_means_nobody_is_the_owner(monkeypatch):
    monkeypatch.delenv(config.APPROVAL_EMAIL_VAR, raising=False)
    monkeypatch.delenv(config.OWNER_EMAIL_VAR, raising=False)
    assert config.owner_address() is None
    assert config.is_owner(OWNER) is False
    assert config.owner_configured() is False


def test_the_owner_is_matched_case_insensitively_and_nobody_else_is(owner_env):
    assert config.is_owner("GARY@AureonZorzaTechnologies.COM") is True
    assert config.is_owner(f"  {OWNER}  ") is True
    assert config.is_owner("gary@aureonzorzatechnologies.com.evil.example") is False
    assert config.is_owner("funder@innovateuk.example") is False
    assert config.is_owner(None) is False


def test_an_address_hidden_in_a_display_name_does_not_pass_for_the_owner(owner_env):
    reply = pytest.importorskip("aureon.approval.reply")
    spoof = f'"{OWNER}" <attacker@elsewhere.example>'
    assert reply.sender_of(spoof) == "attacker@elsewhere.example"
    assert config.is_owner(reply.sender_of(spoof)) is False
    assert config.is_owner(reply.sender_of(f"Gary Leckey <{OWNER}>")) is True


# ── the seam: her own question can never be her answer ──────────────────────


def test_an_echo_of_the_composed_request_is_not_an_approval(live_readings):
    """Property 6, against the real body: the request quotes both vocabularies."""
    reply = pytest.importorskip("aureon.approval.reply")
    request = compose_request("submit", application_id="APP-1", now=MOMENT)

    # Quoted the ordinary way.
    quoted = "\n".join(f"> {line}" for line in request.body_markdown.splitlines())
    verdict = reply.parse_reply(quoted, token=request.token)
    assert verdict.is_approval is False
    assert verdict.state is ApprovalState.UNCLEAR

    # And quoted badly, with no markers at all — the body still says both things.
    verbatim = reply.parse_reply(request.body_markdown, token=request.token)
    assert verbatim.is_approval is False


def test_the_whole_loop_once_and_only_once(tmp_path, live_readings, owner_env):
    reply = pytest.importorskip("aureon.approval.reply")
    request = compose_request("submit", application_id="APP-1", now=MOMENT)
    store.save(request, root=tmp_path)

    quoted = "\n".join(f"> {line}" for line in request.body_markdown.splitlines())
    verdict = reply.parse_reply(f"yes\n\n{quoted}", token=request.token)
    assert verdict.is_approval is True and verdict.matched_token == request.token
    assert reply.sender_is_owner(f"Gary Leckey <{OWNER}>", OWNER) is True

    assert store.resolve(request.token, verdict.state, f"reply: {verdict.reason}",
                         root=tmp_path, now=MOMENT) is True
    assert store.load(request.token, root=tmp_path).approved is True

    # The same message arriving a second time authorises nothing further.
    assert store.resolve(request.token, verdict.state, "the same reply again",
                         root=tmp_path, now=MOMENT) is False

    # A stray yes on another thread names no request and so resolves none.
    stray = reply.parse_reply("yes, go ahead", token=request.token)
    assert stray.is_approval is False and stray.matched_token is None
    assert ApprovalState.APPROVED in TERMINAL_STATES
