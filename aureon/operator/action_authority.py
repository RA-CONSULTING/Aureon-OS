"""Typed, payload-bound authority for one bounded outbound action path.

This module deliberately supports only ``owner_notification``.  It does not
authorise third-party email, grant submission, filings, payments, trades, or
publication.  An authority is HMAC-signed, target-bound, payload-bound,
evidence-linked, and time-limited.  Signature verification proves possession
of the configured runtime key; it is not identity proof or a substitute for a
provider receipt.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Final, Mapping, Sequence

from aureon.bio.mcp_membrane import screen_ingress

OWNER_NOTIFICATION: Final[str] = "owner_notification"
ALLOWED_ACTIONS: Final[frozenset[str]] = frozenset({OWNER_NOTIFICATION})
MAX_TTL_SECONDS: Final[int] = 86_400
_SHA256_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")


class AuthorityBlockedError(RuntimeError):
    """Raised when an action has no exact, current, trusted authority."""


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def payload_sha256(value: Any) -> str:
    """Return the canonical SHA-256 digest used to bind an action payload."""

    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise AuthorityBlockedError("authority timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise AuthorityBlockedError("authority timestamp is invalid") from exc
    if parsed.tzinfo is None:
        raise AuthorityBlockedError("authority timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def _required(label: str, value: object) -> str:
    text = str(value or "").strip()
    if not text or text.casefold() in {"none", "null", "unknown", "placeholder"}:
        raise AuthorityBlockedError(f"{label} is required")
    return text


def _signing_key(value: object) -> bytes:
    key = _required("authority signing key", value).encode("utf-8")
    if len(key) < 32:
        raise AuthorityBlockedError("authority signing key must be at least 32 bytes")
    return key


def _normalise_target(value: object) -> str:
    return _required("authority target", value).casefold()


@dataclass(frozen=True)
class ActionAuthority:
    """Signed authority for exactly one action, target, and payload digest."""

    approval_id: str
    approved_by: str
    action: str
    target: str
    payload_sha256: str
    evidence_sha256: tuple[str, ...]
    authorization_ref: str
    idempotency_key: str
    issued_at: str
    expires_at: str
    signature: str = field(repr=False)

    @classmethod
    def create(
        cls,
        *,
        approved_by: str,
        action: str,
        target: str,
        payload: Mapping[str, Any],
        evidence_sha256: Sequence[str],
        authorization_ref: str,
        signing_key: str,
        ttl_seconds: int = 900,
        now: datetime | None = None,
        approval_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> ActionAuthority:
        if action not in ALLOWED_ACTIONS:
            raise AuthorityBlockedError(f"action is not allowlisted: {action}")
        if not 0 < int(ttl_seconds) <= MAX_TTL_SECONDS:
            raise AuthorityBlockedError("authority TTL is outside the allowed range")
        evidence = tuple(sorted({str(item).casefold() for item in evidence_sha256}))
        if not evidence or any(not _SHA256_RE.fullmatch(item) for item in evidence):
            raise AuthorityBlockedError("valid evidence SHA-256 digests are required")
        issued = now or _utc_now()
        unsigned: dict[str, Any] = {
            "approval_id": _required(
                "approval_id", approval_id or secrets.token_urlsafe(18)
            ),
            "approved_by": _required("approved_by", approved_by),
            "action": action,
            "target": _normalise_target(target),
            "payload_sha256": payload_sha256(dict(payload)),
            "evidence_sha256": evidence,
            "authorization_ref": _required(
                "authorization_ref", authorization_ref
            ),
            "idempotency_key": _required(
                "idempotency_key", idempotency_key or secrets.token_urlsafe(18)
            ),
            "issued_at": _iso(issued),
            "expires_at": _iso(issued + timedelta(seconds=int(ttl_seconds))),
        }
        signature = hmac.new(
            _signing_key(signing_key),
            _canonical_json(unsigned),
            hashlib.sha256,
        ).hexdigest()
        return cls(**unsigned, signature=signature)

    def unsigned_payload(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("signature", None)
        return value

    def verify(
        self,
        *,
        signing_key: str,
        action: str,
        target: str,
        payload: Mapping[str, Any],
        untrusted_text: str = "",
        now: datetime | None = None,
    ) -> None:
        expected = hmac.new(
            _signing_key(signing_key),
            _canonical_json(self.unsigned_payload()),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(self.signature, expected):
            raise AuthorityBlockedError("authority signature is invalid")
        if self.action not in ALLOWED_ACTIONS or self.action != action:
            raise AuthorityBlockedError("authority action does not match")
        if self.target != _normalise_target(target):
            raise AuthorityBlockedError("authority target does not match")
        if not hmac.compare_digest(
            self.payload_sha256,
            payload_sha256(dict(payload)),
        ):
            raise AuthorityBlockedError("authority payload does not match")
        if not self.evidence_sha256 or any(
            not _SHA256_RE.fullmatch(item) for item in self.evidence_sha256
        ):
            raise AuthorityBlockedError("authority evidence digests are invalid")
        instant = now or _utc_now()
        if instant.tzinfo is None:
            raise AuthorityBlockedError("verification time must be timezone-aware")
        instant = instant.astimezone(UTC)
        if _parse_time(self.issued_at) > instant + timedelta(seconds=30):
            raise AuthorityBlockedError("authority is not yet valid")
        if _parse_time(self.expires_at) <= instant:
            raise AuthorityBlockedError("authority has expired")
        try:
            verdict = screen_ingress(
                str(untrusted_text or ""),
                source="authority_bearing_action_payload",
            )
        except Exception as exc:  # fail closed on an authority-bearing path
            raise AuthorityBlockedError("action payload screening failed") from exc
        if verdict.contained:
            raise AuthorityBlockedError("action payload was contained before dispatch")

    def redacted(self) -> dict[str, Any]:
        return {**self.unsigned_payload(), "signature": "<redacted>"}


__all__ = [
    "ALLOWED_ACTIONS",
    "MAX_TTL_SECONDS",
    "OWNER_NOTIFICATION",
    "ActionAuthority",
    "AuthorityBlockedError",
    "payload_sha256",
]
