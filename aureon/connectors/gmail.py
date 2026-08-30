"""Read-only Gmail access the daemon can hold its own credentials for.

A funder replies. A deadline moves. An assessor asks for one more document. All
of it arrives in a mailbox the running system has never been able to open — the
grant organ can see the ledger and the deadlines, but not the correspondence
that changes them. This connector is that eye, and nothing more.

**The class cannot send.** There is no ``send``, no ``draft``, no ``reply``, no
``forward``, no ``trash``, no ``modify``. That absence *is* the enforcement.
A policy flag can be flipped, a config can be edited, an agent can be argued
into believing an exception applies — but a method that does not exist cannot be
called by any of them. The sheet's rule is quoted here because it is the reason:

    "No external submission, legal representation, filing, payment, or email
    send should happen without Gary approval."

Approval is a human act. A connector that cannot send is a connector that cannot
accidentally implement the un-approved case. :data:`NO_WRITE_VERBS` names the
surface this class is forbidden to grow, and ``tests/connectors`` asserts it
structurally so a future edit that adds one fails the suite rather than shipping.
The OAuth scope requested is ``gmail.readonly``, so even a compromised caller
holds a token that cannot send.

**Optional dependency.** Not a project dependency — the repo installs and tests
offline with none of it present. To enable live access::

    pip install google-api-python-client google-auth

then point ``GOOGLE_APPLICATION_CREDENTIALS`` (or ``AUREON_GOOGLE_SERVICE_ACCOUNT_JSON``)
at a service-account key *file*, and set ``AUREON_GOOGLE_DELEGATED_USER`` to the
mailbox to read. That last one is required, not optional: a service account has
no mailbox of its own, so Gmail access is only ever domain-wide delegation to a
real Workspace user. Without it this connector reports a blocker saying so
rather than building a client that would 400 on every call.
"""

from __future__ import annotations

import base64
import binascii
import logging
from typing import Any, Mapping

from aureon.connectors.base import (
    SOURCE_INJECTED,
    SUBJECT_ENV_VAR,
    ConnectorResult,
    ConnectorStatus,
    blocked_result,
    build_google_service,
    describe_api_failure,
    env_subject,
    result_from_status,
)
from aureon.connectors.schemas import GmailMessage, GmailThread, text_or_none

LOG = logging.getLogger("aureon.connectors.gmail")

API_NAME = "gmail"
API_VERSION = "v1"
SCOPES: tuple[str, ...] = ("https://www.googleapis.com/auth/gmail.readonly",)

# ``me`` resolves to the delegated user, which is the only identity this
# connector can ever have — see the module docstring.
USER_ID = "me"

DEFAULT_LIMIT = 25
MAX_LIMIT = 500  # Gmail's own maxResults ceiling for threads.list.

# One message body is capped so a mail with a giant inline attachment cannot
# exhaust the daemon. Truncation is visible: the text is cut, never summarised.
MAX_BODY_CHARS = 100_000

# Bodies are taken from the first part matching one of these, in this order.
# text/plain first because it is the real text; text/html only as the fallback
# for mail that has no plain part, and it is labelled as HTML when returned.
BODY_MIMES: tuple[str, ...] = ("text/plain", "text/html")

# The method surface this class is forbidden to grow. Not a runtime check — a
# named contract that tests/connectors/test_connectors.py enforces against every
# public attribute of GmailConnector. Written out as whole words so a legitimate
# name is not caught by accident: "read_thread" contains no verb from this set.
NO_WRITE_VERBS: frozenset[str] = frozenset({
    "send", "sends", "sending",
    "draft", "drafts", "drafting",
    "compose", "composes",
    "reply", "replies", "replying",
    "forward", "forwards", "forwarding",
    "trash", "untrash", "delete", "deletes",
    "insert", "import", "modify", "batchmodify", "batchdelete",
    "create", "update", "write", "archive", "label", "unlabel",
})


class GmailConnector:
    """Search and read mail threads. Read-only by scope and by surface.

    ``service`` injects a transport (the real ``googleapiclient`` resource, or a
    fake in tests). An injected transport is taken at face value — the caller is
    asserting it is already authenticated — so no credential lookup happens and
    ``status().source`` records that the answer came from injection rather than
    from the environment. That keeps the tests hermetic without a "test mode"
    switch that could be left on in production.
    """

    name = "gmail"

    def __init__(
        self,
        *,
        service: Any | None = None,
        subject: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self._injected = service
        self._env = env
        self._subject = subject if subject is not None else env_subject(env)
        self._resolved: tuple[Any | None, ConnectorStatus] | None = None

    # ---- availability -------------------------------------------------

    def status(self) -> ConnectorStatus:
        """Reachability now. Builds the client on first call and caches it."""
        return self._resolve()[1]

    @property
    def mailbox(self) -> str | None:
        """The Workspace mailbox being read, or None when none is configured."""
        return self._subject

    def _resolve(self) -> tuple[Any | None, ConnectorStatus]:
        if self._injected is not None:
            return self._injected, ConnectorStatus.ready(source=SOURCE_INJECTED)
        if self._resolved is None:
            self._resolved = self._build()
        return self._resolved

    def _build(self) -> tuple[Any | None, ConnectorStatus]:
        # Checked before the credential so the blocker names the thing that is
        # specific to Gmail. A service account with a perfect key file still
        # cannot read mail without a mailbox to impersonate, and "credential OK
        # but every call 400s" is a far worse thing to hand an operator.
        if not self._subject:
            return None, ConnectorStatus.blocked(
                f"no mailbox to read: set {SUBJECT_ENV_VAR} to the Workspace user this "
                "service account is delegated to (a service account has no mailbox of its own)"
            )
        return build_google_service(
            API_NAME, API_VERSION, SCOPES, subject=self._subject, env=self._env
        )

    # ---- reads --------------------------------------------------------

    def search_threads(self, query: str, *, limit: int = DEFAULT_LIMIT) -> ConnectorResult:
        """Find threads matching a Gmail search expression.

        ``query`` is passed through as Gmail's own search syntax (``from:``,
        ``subject:``, ``newer_than:``), because that language is the API's
        contract and re-inventing a wrapper around it would only be able to
        express less.

        The threads returned carry an id and a snippet and nothing else — that is
        all ``threads.list`` reports. Their ``subject`` and ``message_count`` are
        None rather than guessed; :meth:`read_thread` is what fills them in.
        """
        term = (query or "").strip()
        if not term:
            return blocked_result(
                "search query is empty — Gmail needs an expression (e.g. \"newer_than:7d\")"
            )

        service, status = self._resolve()
        if service is None:
            return result_from_status(status)

        page_size = max(1, min(int(limit), MAX_LIMIT))
        try:
            response = (
                service.users()
                .threads()
                .list(userId=USER_ID, q=term, maxResults=page_size)
                .execute()
            )
        except Exception as exc:  # noqa: BLE001 — absence is reported, never thrown
            LOG.debug("gmail threads.list failed", exc_info=True)
            return blocked_result(
                describe_api_failure("Gmail threads.list", exc), source=status.source
            )

        rows = response.get("threads") if isinstance(response, dict) else None
        if rows is None and isinstance(response, dict):
            # Gmail omits the key entirely when nothing matches. That is a real
            # empty result, not a shape this code failed to understand.
            rows = []
        if not isinstance(rows, list):
            return blocked_result(
                "Gmail threads.list returned no 'threads' list — response shape not understood",
                source=status.source,
            )

        threads = tuple(t for t in (_thread_stub(r) for r in rows) if t is not None)
        return ConnectorResult(available=True, source=status.source, records=threads)

    def read_thread(self, thread_id: str) -> ConnectorResult:
        """Read one whole thread: every message, its headers and its body."""
        identifier = (thread_id or "").strip()
        if not identifier:
            return blocked_result("no thread id given")

        service, status = self._resolve()
        if service is None:
            return result_from_status(status)

        try:
            response = (
                service.users()
                .threads()
                .get(userId=USER_ID, id=identifier, format="full")
                .execute()
            )
        except Exception as exc:  # noqa: BLE001
            LOG.debug("gmail threads.get failed", exc_info=True)
            return blocked_result(
                describe_api_failure("Gmail threads.get", exc), source=status.source
            )

        if not isinstance(response, dict):
            return blocked_result(
                f"Gmail threads.get returned {type(response).__name__}, not an object",
                source=status.source,
            )

        raw_messages = response.get("messages")
        rows = raw_messages if isinstance(raw_messages, list) else []
        messages = tuple(m for m in (_message(r) for r in rows) if m is not None)

        thread = GmailThread(
            id=str(response.get("id") or identifier),
            # The thread's subject is the first message's — Gmail stores no
            # thread-level subject, so it is read from the conversation rather
            # than invented. None when there are no messages to read it from.
            subject=messages[0].subject if messages else None,
            snippet=text_or_none(response.get("snippet")),
            # A real count of what was returned. Only set when the API actually
            # gave a messages list; a response without one leaves it None, since
            # "not returned" and "zero messages" are different answers.
            message_count=len(messages) if isinstance(raw_messages, list) else None,
            messages=messages,
        )
        return ConnectorResult(available=True, source=status.source, records=(thread,))


# ---- parsing ----------------------------------------------------------


def _thread_stub(raw: Any) -> GmailThread | None:
    """A thread as ``threads.list`` reports it — id and snippet, nothing more."""
    if not isinstance(raw, dict):
        return None
    thread_id = str(raw.get("id") or "").strip()
    if not thread_id:
        return None
    return GmailThread(id=thread_id, snippet=text_or_none(raw.get("snippet")))


def _message(raw: Any) -> GmailMessage | None:
    if not isinstance(raw, dict):
        return None
    message_id = str(raw.get("id") or "").strip()
    if not message_id:
        return None

    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
    headers = _headers(payload.get("headers"))
    body_text, body_mime = _body(payload)

    return GmailMessage(
        id=message_id,
        thread_id=text_or_none(raw.get("threadId")),
        sender=headers.get("from"),
        recipient=headers.get("to"),
        subject=headers.get("subject"),
        date=headers.get("date"),
        snippet=text_or_none(raw.get("snippet")),
        body_text=body_text,
        body_mime=body_mime,
    )


def _headers(raw: Any) -> dict[str, str]:
    """Header name -> value, lower-cased keys.

    Gmail's casing is conventional but not contractual, and a header list is a
    list of dicts rather than a mapping, so it is normalised once here instead
    of at four call sites.
    """
    out: dict[str, str] = {}
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        key = str(item.get("name") or "").strip().lower()
        value = item.get("value")
        if key and isinstance(value, str) and value.strip():
            out.setdefault(key, value.strip())
    return out


def _body(payload: Any) -> tuple[str | None, str | None]:
    """Find the best body part and decode it. Returns ``(text, mime)``.

    MIME trees nest (``multipart/mixed`` wrapping ``multipart/alternative``
    wrapping the parts), so the walk is recursive. Every candidate is collected
    before choosing, because the preferred ``text/plain`` part frequently sits
    *after* the HTML one in the tree and a first-match-wins walk would return
    markup for a message that had perfectly good plain text further down.
    """
    if not isinstance(payload, dict):
        return None, None

    found: dict[str, str] = {}
    _collect(payload, found)
    for mime in BODY_MIMES:
        text = found.get(mime)
        if text is not None:
            return (text[:MAX_BODY_CHARS] if len(text) > MAX_BODY_CHARS else text), mime
    return None, None


def _collect(part: Any, found: dict[str, str], depth: int = 0) -> None:
    """Walk the MIME tree, recording the first decoded body per mime type."""
    if not isinstance(part, dict) or depth > 10:  # depth guard: a malformed tree must not spin
        return
    mime = str(part.get("mimeType") or "").split(";")[0].strip().lower()
    body = part.get("body")
    if mime in BODY_MIMES and mime not in found and isinstance(body, dict):
        decoded = _decode_b64(body.get("data"))
        if decoded is not None:
            found[mime] = decoded
    children = part.get("parts")
    if isinstance(children, list):
        for child in children:
            _collect(child, found, depth + 1)


def _decode_b64(data: Any) -> str | None:
    """Decode Gmail's base64url body data, or None.

    Gmail strips ``=`` padding; ``b64decode`` requires it, so it is restored.
    Decoding uses ``errors="replace"`` here — unlike Drive, where a non-UTF-8
    payload means "this is not text at all". A mail body genuinely is text, in a
    charset the header may misdeclare, so a few replacement characters in an
    otherwise readable message is better than discarding the message.
    """
    if not isinstance(data, str) or not data.strip():
        return None
    padded = data + "=" * (-len(data) % 4)
    try:
        return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
    except (binascii.Error, ValueError):
        LOG.debug("gmail body base64 decode failed")
        return None


__all__ = ["GmailConnector", "API_NAME", "API_VERSION", "SCOPES", "NO_WRITE_VERBS"]
