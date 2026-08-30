"""The sender can only ever ask the owner, and it can only ever ask.

Hermetic: every test builds its own request, its own environment and its own SMTP
transport, and writes its audit log under ``tmp_path``. Nothing here reads the
live configuration, opens a socket, or touches the repository's ``state/``.

Five properties are what this suite exists to pin:

1. **No callable in the module accepts a destination.** Not "the recipient is
   checked" — there is no parameter to pass one to. The scan walks every callable
   in the module's namespace, imported ones included, and is the structural proof
   of property 1: a sender that cannot address a funder cannot submit to one.
2. **A missing owner address is a blocker, not an exception.** An unconfigured
   organism does not crash at the last gate; it reports that there is nobody to
   ask. The feature-flag collision on ``AUREON_APPROVAL_EMAIL`` is pinned here
   too — ``"1"`` is not an address.
3. **A missing password file is a blocker**, and no blocker ever echoes a secret,
   including when an inline password is present and refused.
4. **Exactly one message, addressed to the configured owner and nobody else** —
   one connection, one STARTTLS, one login, one send, no Cc, no Bcc.
5. **The audit line is written even when nothing was sent.** The blocked half of
   the record is the evidence that the system stopped rather than improvised.
"""

from __future__ import annotations

import inspect
import json
from datetime import UTC, datetime, timedelta

import pytest

from aureon.approval import notify, reply
from aureon.approval.notify import (
    NOTIFY_LOG_NAME,
    SMTP_INLINE_PASSWORD_VAR,
    SMTP_PASSWORD_FILE_VAR,
    SUBJECT_TAG,
    TOKEN_HEADER,
    notify_log_path,
    render_request,
    resolve_owner_address,
    resolve_transport,
    send_approval_request,
    subject_line,
)
from aureon.approval.schemas import (
    ApprovalRequest,
    ApprovalState,
    GroundingSnapshot,
    new_token,
)

NOW = datetime(2026, 7, 31, 12, 0, 0, tzinfo=UTC)
OWNER = "gary@aureonzorzatechnologies.com"
SENDER = "sero@aureonzorzatechnologies.com"

# A fake credential, written out so the tests can assert it never appears in a
# blocker, a log line or a result.
FAKE_PASSWORD = "not-a-real-password-4c1f"

# Every variable the module reads, cleared before each test so nothing leaks in
# from the operator's live environment — the offline flags included, since the
# injected-transport path must not depend on them either way.
MANAGED_VARS = (
    "AUREON_APPROVAL_EMAIL",
    "AUREON_OWNER_EMAIL",
    "AUREON_APPROVALS_DIR",
    "AUREON_SMTP_HOST",
    "AUREON_SMTP_PORT",
    "AUREON_SMTP_USER",
    SMTP_PASSWORD_FILE_VAR,
    SMTP_INLINE_PASSWORD_VAR,
    "AUREON_LLM_OFFLINE",
    "AUREON_AUDIT_MODE",
)


# ── the fake transport ────────────────────────────────────────────────────────


class FakeSMTP:
    """An SMTP client that records instead of connecting."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.entered = 0
        self.exited = 0
        self.starttls_calls = 0
        self.logins: list[tuple[str, str]] = []
        self.messages: list[object] = []

    def __enter__(self) -> FakeSMTP:
        self.entered += 1
        return self

    def __exit__(self, *_exc: object) -> bool:
        self.exited += 1
        return False

    def starttls(self, context: object = None) -> None:
        self.starttls_calls += 1

    def login(self, user: str, password: str) -> None:
        self.logins.append((user, password))

    def send_message(self, message: object) -> None:
        self.messages.append(message)


class Transport:
    """A factory recording every client it was asked to build."""

    def __init__(self, explode: type[Exception] | None = None) -> None:
        self.clients: list[FakeSMTP] = []
        self.calls: list[tuple[str, int]] = []
        self._explode = explode

    def __call__(self, host: str, port: int) -> FakeSMTP:
        self.calls.append((host, port))
        if self._explode is not None:
            raise self._explode("transport unavailable")
        client = FakeSMTP(host, port)
        self.clients.append(client)
        return client

    @property
    def sent(self) -> list[object]:
        return [m for client in self.clients for m in client.messages]


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def password_file(tmp_path):
    path = tmp_path / "smtp.secret"
    path.write_text(FAKE_PASSWORD + "\n", encoding="utf-8")
    return path


@pytest.fixture
def clean_env(monkeypatch):
    for var in MANAGED_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


@pytest.fixture
def configured(clean_env, password_file):
    """A fully configured organism: an owner to ask, and a transport to ask over."""
    clean_env.setenv("AUREON_APPROVAL_EMAIL", OWNER)
    clean_env.setenv("AUREON_SMTP_HOST", "smtp.example.test")
    clean_env.setenv("AUREON_SMTP_PORT", "587")
    clean_env.setenv("AUREON_SMTP_USER", SENDER)
    clean_env.setenv(SMTP_PASSWORD_FILE_VAR, str(password_file))
    return clean_env


def _grounding(**kw) -> GroundingSnapshot:
    base = {
        "coherence": 0.8123,
        "divergence": 0.11,
        "panel_consensus": "RALLY",
        "panel_confidence": 0.95,
        "panel_evidence": 0.71,
        "gate_verdicts": (
            {"gate": "act", "decision": "ADVANCE", "confidence": 0.67, "reasoning": "yes"},
            {"gate": "submit", "decision": "HOLD", "confidence": 0.67,
             "reasoning": "no automatic executor exists for this step",
             "dissent": ["panel ran on 71% real inputs"]},
        ),
    }
    base.update(kw)
    return GroundingSnapshot(**base)


BODY = (
    "# Gary — am I ok to go ahead?\n\n"
    "I have taken this as far as I can on my own.\n\n"
    "- **Action** `submit_application`\n"
)


def _request(**kw) -> ApprovalRequest:
    base = {
        "token": new_token(),
        "subject": "submit_application — APP-IFS-CFI-SEN-2511",
        "action": "submit_application",
        "application_id": "APP-IFS-CFI-SEN-2511-20260709",
        "body_markdown": BODY,
        "created_at": NOW,
        "expires_at": NOW + timedelta(hours=48),
        "grounding": _grounding(),
    }
    base.update(kw)
    return ApprovalRequest(**base)


def _log_rows(tmp_path) -> list[dict]:
    path = notify_log_path(tmp_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# ── 1. structurally incapable of addressing anyone ───────────────────────────

# Names that would let a caller choose a destination. Any of these on any
# signature in the module breaks the owner lock, whatever the body does.
FORBIDDEN_PARAMS = frozenset({
    "to", "cc", "bcc", "recipient", "recipients", "rcpt", "rcpt_to", "rcpts",
    "to_addr", "to_addrs", "to_address", "toaddrs", "addressee", "addressees",
    "mailto", "send_to", "sendto", "destination", "dest", "email", "address",
    "owner_address", "target_address", "reply_to", "envelope_to",
})


def _module_callables():
    """Every callable in the module's namespace, imported ones included."""
    out = {}
    for name, obj in vars(notify).items():
        if name.startswith("__") or not callable(obj):
            continue
        try:
            out[name] = tuple(p.lower() for p in inspect.signature(obj).parameters)
        except (ValueError, TypeError):
            # Typing constructs and a few C builtins have no introspectable
            # signature. None of them can send mail, and the assertion below
            # proves the ones that matter were actually examined.
            continue
    return out


def test_no_callable_in_the_module_accepts_a_recipient():
    examined = _module_callables()
    # The scan is only evidence if it reached the things that send.
    for required in ("send_approval_request", "subject_line", "render_request",
                     "resolve_owner_address", "resolve_transport", "_deliver",
                     "_default_transport", "NotifyResult", "SmtpConfig"):
        assert required in examined, f"{required} was not examined"

    for name, params in examined.items():
        for param in params:
            assert param not in FORBIDDEN_PARAMS, (
                f"{name}() accepts {param!r} — the sender must be structurally incapable of "
                "being pointed at anyone but the owner"
            )
            assert "recipient" not in param, f"{name}() accepts {param!r}"


def test_the_module_exposes_no_generic_send():
    senders = {
        name for name, obj in vars(notify).items()
        if callable(obj) and "send" in name.lower() and not name.startswith("__")
    }
    assert senders == {"send_approval_request"}, (
        "the only send in this module must be the one that builds its own approval request; "
        f"found {sorted(senders)}"
    )


def test_the_request_type_carries_no_destination():
    assert not set(inspect.signature(ApprovalRequest).parameters) & FORBIDDEN_PARAMS


def test_arbitrary_content_cannot_be_smuggled_through_the_sender(configured, tmp_path):
    transport = Transport()
    result = send_approval_request(
        {"to": "funder@example.test", "body": "please fund us"},  # type: ignore[arg-type]
        transport=transport, now=NOW, root=tmp_path,
    )
    assert result.sent is False
    assert "ApprovalRequest" in (result.blocker or "")
    assert transport.calls == []


# ── 2. a missing owner address is a blocker, never a raise ───────────────────


def test_resolve_owner_address_reports_absence_rather_than_guessing(clean_env):
    address, blocker = resolve_owner_address()
    assert address is None
    assert "AUREON_APPROVAL_EMAIL" in (blocker or "")
    assert "AUREON_OWNER_EMAIL" in (blocker or "")


def test_approval_email_wins_and_owner_email_is_the_fallback(clean_env):
    clean_env.setenv("AUREON_OWNER_EMAIL", OWNER)
    assert resolve_owner_address() == (OWNER, None)

    clean_env.setenv("AUREON_APPROVAL_EMAIL", "chosen@example.test")
    assert resolve_owner_address()[0] == "chosen@example.test"


def test_a_feature_flag_value_is_not_an_address(clean_env):
    # AUREON_APPROVAL_EMAIL is a boolean toggle elsewhere in this repository
    # (operator/approval_email.py reads it through _truthy). "1" must not become a
    # destination; resolution falls through to the owner variable.
    clean_env.setenv("AUREON_APPROVAL_EMAIL", "1")
    clean_env.setenv("AUREON_OWNER_EMAIL", OWNER)
    assert resolve_owner_address() == (OWNER, None)


def test_a_list_of_addresses_resolves_to_nobody(clean_env):
    clean_env.setenv("AUREON_APPROVAL_EMAIL", f"{OWNER}, funder@example.test")
    address, blocker = resolve_owner_address()
    assert address is None and blocker
    assert "funder@example.test" not in blocker  # a blocker never echoes a value


def test_a_display_name_cannot_smuggle_a_second_address(clean_env):
    clean_env.setenv("AUREON_APPROVAL_EMAIL", f'"{OWNER}" <funder@example.test>')
    address, _blocker = resolve_owner_address()
    assert address != OWNER, "the display name is not the address"
    assert address in (None, "funder@example.test")


def test_send_without_an_owner_is_blocked_and_sends_nothing(clean_env, tmp_path):
    transport = Transport()
    result = send_approval_request(_request(), transport=transport, now=NOW, root=tmp_path)
    assert result.sent is False
    assert result.owner is None
    assert "nobody to ask" in (result.blocker or "")
    assert transport.calls == []


# ── 3. a missing password file is a blocker, and no secret is ever printed ───


def _smtp_without_password(env):
    env.setenv("AUREON_APPROVAL_EMAIL", OWNER)
    env.setenv("AUREON_SMTP_HOST", "smtp.example.test")
    env.setenv("AUREON_SMTP_PORT", "587")
    env.setenv("AUREON_SMTP_USER", SENDER)


def test_missing_password_file_is_a_blocker(clean_env, tmp_path):
    _smtp_without_password(clean_env)

    config, blocker = resolve_transport()
    assert config is None
    assert SMTP_PASSWORD_FILE_VAR in (blocker or "")

    transport = Transport()
    result = send_approval_request(_request(), transport=transport, now=NOW, root=tmp_path)
    assert result.sent is False
    assert SMTP_PASSWORD_FILE_VAR in (result.blocker or "")
    assert result.owner == OWNER  # the address resolved; the transport did not
    assert transport.calls == []


def test_a_password_file_that_does_not_exist_names_itself(clean_env, tmp_path):
    _smtp_without_password(clean_env)
    clean_env.setenv(SMTP_PASSWORD_FILE_VAR, str(tmp_path / "absent.secret"))

    config, blocker = resolve_transport()
    assert config is None and "does not exist" in (blocker or "")


def test_a_password_file_that_is_a_directory_is_refused(clean_env, tmp_path):
    _smtp_without_password(clean_env)
    clean_env.setenv(SMTP_PASSWORD_FILE_VAR, str(tmp_path))

    config, blocker = resolve_transport()
    assert config is None and "not a file" in (blocker or "")


def test_an_inline_password_is_refused_and_never_echoed(clean_env):
    _smtp_without_password(clean_env)
    clean_env.setenv(SMTP_INLINE_PASSWORD_VAR, FAKE_PASSWORD)

    config, blocker = resolve_transport()
    assert config is None
    assert SMTP_PASSWORD_FILE_VAR in (blocker or "")
    assert FAKE_PASSWORD not in (blocker or "")


def test_a_missing_port_is_not_defaulted(clean_env, password_file):
    clean_env.setenv("AUREON_APPROVAL_EMAIL", OWNER)
    clean_env.setenv("AUREON_SMTP_HOST", "smtp.example.test")
    clean_env.setenv("AUREON_SMTP_USER", SENDER)
    clean_env.setenv(SMTP_PASSWORD_FILE_VAR, str(password_file))

    config, blocker = resolve_transport()
    assert config is None
    assert "AUREON_SMTP_PORT" in (blocker or "")


def test_the_password_is_never_in_a_repr(configured):
    config, blocker = resolve_transport()
    assert blocker is None and config is not None
    assert FAKE_PASSWORD not in repr(config)
    assert config.password == FAKE_PASSWORD  # it is there, just not printable


# ── 4. exactly one message, to the owner, and nobody else ────────────────────


def test_one_message_addressed_only_to_the_configured_owner(configured, tmp_path):
    transport = Transport()
    request = _request()
    result = send_approval_request(request, transport=transport, now=NOW, root=tmp_path)

    assert result.sent is True and result.blocker is None
    assert result.owner == OWNER

    # One connection, one login, one send.
    assert len(transport.clients) == 1
    client = transport.clients[0]
    assert (client.host, client.port) == ("smtp.example.test", 587)
    assert client.entered == 1 and client.exited == 1
    assert client.starttls_calls == 1, "STARTTLS is not optional on a non-465 port"
    assert client.logins == [(SENDER, FAKE_PASSWORD)], "the password comes from the file"
    assert len(client.messages) == 1

    message = transport.sent[0]
    assert message.get_all("To") == [OWNER]
    assert message["Cc"] is None and message["Bcc"] is None
    assert message["From"] == SENDER
    assert message[TOKEN_HEADER] == request.token
    assert message["Auto-Submitted"] == "auto-generated"


def test_the_subject_carries_the_token_and_the_question(configured, tmp_path):
    request = _request()
    transport = Transport()
    result = send_approval_request(request, transport=transport, now=NOW, root=tmp_path)

    assert request.token in result.subject
    assert SUBJECT_TAG in result.subject
    assert "am I ok to go ahead?" in result.subject
    assert transport.sent[0]["Subject"] == result.subject


def test_the_reply_reader_can_read_the_token_back_off_the_subject(configured):
    # The round trip that makes the token load-bearing: Gary replies, the subject
    # comes back, and the reader must bind that reply to this request and no other.
    request = _request()
    line = subject_line(request)
    assert reply.find_token(f"Re: {line}") == request.token
    assert reply.references_token(f"Re: {line}", request.token) is True
    assert reply.references_token("Re: something else entirely", request.token) is False


def test_the_tag_is_never_doubled(configured):
    # A hand-built request whose title already carries the tag is passed through.
    request = _request()
    tagged = _request(token=request.token, subject=f"[{SUBJECT_TAG} {request.token}] already tagged")
    assert subject_line(tagged).count(SUBJECT_TAG) == 1


def test_the_body_restates_the_grounding_from_the_record(configured, tmp_path):
    request = _request()
    send_approval_request(request, transport=Transport(), now=NOW, root=tmp_path)
    body = render_request(request, now=NOW)

    assert request.body_markdown.strip() in body    # the composed ask, verbatim
    assert "0.8123" in body                         # Γ, as read
    assert "0.1100" in body                         # divergence
    assert "RALLY" in body                          # the nine nodes' consensus
    assert "71%" in body                            # how much of it was measured
    assert "act ADVANCE" in body and "submit HOLD" in body   # the gate trail
    assert request.token in body                    # how to answer this one
    assert "No external submission" in body         # his own standing rule


def test_a_divided_organism_asks_differently(configured):
    calm = render_request(_request(), now=NOW)
    assert "DIVIDED" not in calm

    divided = _request(grounding=_grounding(divergence=0.62, panel_evidence=0.28))
    body = render_request(divided, now=NOW)
    assert "ASKING WHILE DIVIDED" in body
    assert "THIN EVIDENCE" in body
    # Loud means first: above the composed body, not in a footnote under it.
    assert body.index("DIVIDED") < body.index(divided.body_markdown.strip()[:24])


def test_unmeasured_divergence_is_reported_as_division_not_calm(configured):
    body = render_request(_request(grounding=_grounding(divergence=None)), now=NOW)
    assert "NEVER MEASURED WHETHER I AGREE WITH MYSELF" in body
    assert "unmeasured is not calm" in body
    assert "self-agreement never checked" in body


def test_a_body_that_already_cautions_is_not_shouted_over(configured):
    grounding = _grounding(divergence=0.62)
    composed = "> ## CAUTION — I am asking from an uncertain position\n>\n> divergence 0.620\n"
    body = render_request(_request(grounding=grounding, body_markdown=composed), now=NOW)
    assert body.count("CAUTION") == 1, "a caution printed twice reads as a template"
    assert composed.strip() in body


def test_a_transport_failure_is_a_blocker_with_no_fallback_channel(configured, tmp_path):
    transport = Transport(explode=TimeoutError)
    result = send_approval_request(_request(), transport=transport, now=NOW, root=tmp_path)
    assert result.sent is False
    assert "TimeoutError" in (result.blocker or "")
    assert transport.sent == []
    assert _log_rows(tmp_path)[0]["outcome"] == "blocked"


def test_the_real_transport_is_refused_while_the_offline_flag_is_set(configured, tmp_path):
    configured.setenv("AUREON_AUDIT_MODE", "1")
    result = send_approval_request(_request(), now=NOW, root=tmp_path)
    assert result.sent is False
    assert "network disabled" in (result.blocker or "")


def test_port_465_is_tls_from_the_first_byte(configured, tmp_path):
    configured.setenv("AUREON_SMTP_PORT", "465")
    transport = Transport()
    result = send_approval_request(_request(), transport=transport, now=NOW, root=tmp_path)
    assert result.sent is True
    assert transport.clients[0].starttls_calls == 0
    assert transport.clients[0].port == 465


# ── refusals that protect the gate itself ────────────────────────────────────


def test_an_expired_request_is_not_sent(configured, tmp_path):
    request = _request()
    later = request.expires_at + timedelta(seconds=1)
    transport = Transport()
    result = send_approval_request(request, transport=transport, now=later, root=tmp_path)
    assert result.sent is False
    assert "expired" in (result.blocker or "")
    assert transport.sent == []


def test_a_resolved_request_is_never_asked_about_again(configured, tmp_path):
    transport = Transport()
    request = _request().with_state(ApprovalState.APPROVED)
    result = send_approval_request(request, transport=transport, now=NOW, root=tmp_path)
    assert result.sent is False
    assert "spent" in (result.blocker or "")
    assert transport.sent == []


def test_a_request_that_cannot_show_its_grounding_is_not_sent(configured, tmp_path):
    request = _request()
    # ApprovalRequest.__post_init__ refuses an unreadable grounding outright, so
    # this forces the state the constructor forbids — a record rehydrated from a
    # tampered file, say — to prove the sender does not lean on the constructor.
    object.__setattr__(request, "grounding", GroundingSnapshot())
    transport = Transport()
    result = send_approval_request(request, transport=transport, now=NOW, root=tmp_path)
    assert result.sent is False
    assert "cannot show its grounding" in (result.blocker or "")
    assert transport.sent == []


# ── 5. every ask is recorded, especially the ones that never left ─────────────


def test_the_audit_line_is_written_when_the_send_succeeds(configured, tmp_path):
    request = _request()
    result = send_approval_request(request, transport=Transport(), now=NOW, root=tmp_path)

    rows = _log_rows(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["token"] == request.token
    assert row["outcome"] == "sent"
    assert row["recipient"] == OWNER
    assert row["timestamp"] == NOW.isoformat()
    assert row["action"] == "submit_application"
    assert row["reference"] == "APP-IFS-CFI-SEN-2511-20260709"
    assert row["blocker"] is None
    assert row["grounding"]["divergence"] == 0.11
    assert row["grounding"]["needs_caution"] is False
    assert result.logged is True
    assert result.log_path == str(notify_log_path(tmp_path))


def test_the_audit_line_is_written_even_when_blocked(clean_env, tmp_path):
    request = _request()
    result = send_approval_request(request, transport=Transport(), now=NOW, root=tmp_path)
    assert result.sent is False

    rows = _log_rows(tmp_path)
    assert len(rows) == 1
    row = rows[0]
    assert row["token"] == request.token
    assert row["outcome"] == "blocked"
    assert row["recipient"] is None          # it went nowhere, and says so
    assert "nobody to ask" in row["blocker"]
    assert result.logged is True


def test_the_log_never_contains_the_password(configured, tmp_path):
    send_approval_request(_request(), transport=Transport(), now=NOW, root=tmp_path)
    text = notify_log_path(tmp_path).read_text(encoding="utf-8")
    assert FAKE_PASSWORD not in text
    assert "password" not in text.lower()


def test_the_log_is_append_only_across_asks(configured, tmp_path):
    first, second = _request(), _request()
    send_approval_request(first, transport=Transport(), now=NOW, root=tmp_path)
    send_approval_request(second, transport=Transport(), now=NOW, root=tmp_path)
    rows = _log_rows(tmp_path)
    assert [r["token"] for r in rows] == [first.token, second.token]
    assert notify_log_path(tmp_path).name == NOTIFY_LOG_NAME


def test_the_log_lands_beside_the_request_ledger(configured, tmp_path):
    from aureon.approval.store import approvals_dir

    assert notify_log_path(tmp_path).parent == approvals_dir(tmp_path)


def test_a_result_cannot_claim_it_was_sent_without_saying_where():
    with pytest.raises(ValueError):
        notify.NotifyResult(sent=True)
    with pytest.raises(ValueError):
        notify.NotifyResult(sent=False)
    with pytest.raises(ValueError):
        notify.NotifyResult(sent=True, owner=OWNER, blocker="both")


def test_subject_line_keeps_the_token_whole_however_long_the_title(configured):
    request = _request(subject="X" * 400)
    line = subject_line(request)
    assert request.token in line
    assert len(line) <= notify.MAX_SUBJECT_CHARS
