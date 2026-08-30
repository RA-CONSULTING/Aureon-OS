"""Owner-scoped approval notification and decision capture.

Aureon may prepare a proposal and notify the configured director address, but
this module never executes the proposed trade, payment, filing, grant, deal, or
third-party correspondence. The notification path is opt-in and requires an
``ActionAuthority`` that is signed, evidence-linked, expiring, target-bound,
payload-bound, and unused in this process.

Replies are accepted only from the configured owner, only for tagged approval
subjects, and only when the body screens cleanly and begins with an unambiguous
approve/reject token. Recording a decision still does not execute the move.

The HMAC proves possession of the configured runtime key. It is not identity
proof, provider authentication, or a production deployment attestation.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from email.utils import parseaddr
from threading import Lock
from typing import Any, Callable, Protocol

from aureon.bio.mcp_membrane import screen_ingress
from aureon.operator.action_authority import (
    OWNER_NOTIFICATION,
    ActionAuthority,
    AuthorityBlockedError,
)

logger = logging.getLogger("aureon.operator.approval_email")

_SUBJECT_PREFIX = "[AUREON approval"
_ID_RE = re.compile(r"\[AUREON approval\s+([0-9a-f]{6,12})\]", re.IGNORECASE)
_APPROVE_WORDS = (
    "approve",
    "approved",
    "yes",
    "go",
    "ok",
    "okay",
    "proceed",
    "confirm",
)
_REJECT_WORDS = (
    "reject",
    "rejected",
    "no",
    "deny",
    "denied",
    "stop",
    "cancel",
    "hold",
)


def _truthy(name: str) -> bool:
    return str(os.environ.get(name, "") or "").strip().casefold() in {
        "1",
        "true",
        "yes",
        "on",
    }


class EmailTransport(Protocol):
    """Minimal injectable transport; test stubs and real adapters share it."""

    def send(self, to: str, subject: str, body: str) -> bool: ...

    def fetch_replies(self) -> list[dict[str, Any]]: ...


def _parse_decision(body: str) -> str | None:
    """Return a clear first-line decision; never guess from ambiguous prose."""

    for raw in str(body or "").splitlines():
        line = raw.strip().casefold()
        if not line or line.startswith(">"):
            continue
        token = re.split(r"[\s,.!:;]", line, maxsplit=1)[0]
        if token in _APPROVE_WORDS or line in _APPROVE_WORDS:
            return "approve"
        if token in _REJECT_WORDS or line in _REJECT_WORDS:
            return "reject"
        return None
    return None


class ApprovalEmail:
    """Typed-authority owner notification and records-only reply capture."""

    def __init__(
        self,
        transport: EmailTransport | None = None,
        owner_email: str | None = None,
        *,
        authority_signing_key: str | None = None,
        enabled: bool | None = None,
    ) -> None:
        self._transport = transport
        self._owner = owner_email or os.environ.get("AUREON_OWNER_EMAIL", "")
        self._authority_signing_key = authority_signing_key or os.environ.get(
            "AUREON_ACTION_AUTHORITY_KEY", ""
        )
        self._enabled_override = enabled
        self._consumed_authorities: set[str] = set()
        self._authority_lock = Lock()

    @property
    def enabled(self) -> bool:
        opted_in = (
            bool(self._enabled_override)
            if self._enabled_override is not None
            else _truthy("AUREON_APPROVAL_EMAIL")
        )
        return (
            opted_in
            and bool(self._owner)
            and self._transport is not None
            and bool(self._authority_signing_key)
        )

    @property
    def owner_email(self) -> str:
        return self._owner

    def prepare_notification(self, item: dict[str, Any]) -> dict[str, str]:
        """Render the exact payload that an authority must bind."""

        item_id = str(item.get("id", ""))
        subject = (
            f"{_SUBJECT_PREFIX} {item_id}] "
            f"{item.get('kind', 'decision')} — needs your call"
        )
        body = (
            f"Aureon has prepared a {item.get('kind')} and is holding it for you.\n\n"
            f"{item.get('summary', '')}\n\n"
            f"Risk: {item.get('risk')}\n\n"
            "Reply APPROVE or REJECT to record your decision. This records your "
            "decision only — the live move stays your deliberate step."
        )
        return {"to": self._owner, "subject": subject, "body": body}

    def notify(
        self,
        item: dict[str, Any],
        *,
        authority: ActionAuthority | None = None,
        now: datetime | None = None,
    ) -> bool:
        """Send one exact owner notification when every authority check passes."""

        if (
            not self.enabled
            or self._transport is None
            or authority is None
            or not self._authority_signing_key
        ):
            return False
        try:
            payload = self.prepare_notification(item)
            with self._authority_lock:
                if authority.approval_id in self._consumed_authorities:
                    return False
                authority.verify(
                    signing_key=self._authority_signing_key,
                    action=OWNER_NOTIFICATION,
                    target=self._owner,
                    payload=payload,
                    untrusted_text=f"{payload['subject']}\n{payload['body']}",
                    now=now,
                )
                sent = bool(
                    self._transport.send(
                        payload["to"],
                        payload["subject"],
                        payload["body"],
                    )
                )
                if sent:
                    self._consumed_authorities.add(authority.approval_id)
                return sent
        except AuthorityBlockedError as exc:
            logger.debug("approval notify blocked: %s", exc)
            return False
        except Exception as exc:  # noqa: BLE001
            logger.debug("approval notify skipped: %s", exc)
            return False

    def notify_pending(
        self,
        authority_provider: Callable[
            [dict[str, Any], dict[str, str]], ActionAuthority | None
        ]
        | None = None,
        *,
        now: datetime | None = None,
    ) -> int:
        """Notify pending items only with a per-item, per-payload authority."""

        if not self.enabled or authority_provider is None:
            return 0
        try:
            from aureon.core.approval_queue import get_approval_queue

            sent = 0
            for item in get_approval_queue().pending():
                payload = self.prepare_notification(item)
                authority = authority_provider(item, payload)
                if self.notify(item, authority=authority, now=now):
                    sent += 1
            return sent
        except Exception as exc:  # noqa: BLE001
            logger.debug("notify_pending skipped: %s", exc)
            return 0

    def ingest_replies(self) -> list[dict[str, Any]]:
        """Record clear, screened decisions only from the configured owner."""

        if not self.enabled or self._transport is None:
            return []
        applied: list[dict[str, Any]] = []
        try:
            from aureon.core.approval_queue import get_approval_queue

            owner = parseaddr(self._owner)[1].casefold()
            q = get_approval_queue()
            for message in self._transport.fetch_replies():
                match = _ID_RE.search(str(message.get("subject", "")))
                if not match:
                    continue
                sender = parseaddr(str(message.get("from", "")))[1].casefold()
                if not sender or sender != owner:
                    continue
                try:
                    verdict = screen_ingress(
                        str(message.get("body", "")),
                        source="owner_approval_reply",
                    )
                except Exception:  # fail closed before recording authority
                    continue
                if verdict.contained:
                    continue
                decision = _parse_decision(str(message.get("body", "")))
                if decision is None:
                    continue
                item = q.decide(
                    match.group(1),
                    decision,
                    approver="gary-email",
                    note="via screened owner email reply",
                )
                if item is not None:
                    applied.append(
                        {
                            "id": match.group(1),
                            "decision": decision,
                            "status": item.get("status"),
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            logger.debug("ingest_replies skipped: %s", exc)
        return applied


_email: ApprovalEmail | None = None


def get_approval_email() -> ApprovalEmail:
    """Return the process-global, owner-scoped approval-email control."""

    global _email
    if _email is None:
        _email = ApprovalEmail()
    return _email


__all__ = ["ApprovalEmail", "EmailTransport", "get_approval_email"]
