"""Verifier-owned recipient challenge and possession proof for Magic Star v0.2."""

from __future__ import annotations

import re
import secrets
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .crypto import (
    b64url_encode,
    domain_hash,
    ed25519_public_key_hex,
    sign_ed25519,
    verify_ed25519,
)

CHALLENGE_SCHEMA = "aureon.plumber.magic-star.recipient-challenge.v02"
PROOF_SCHEMA = "aureon.plumber.magic-star.recipient-proof.v02"
_SIGNING_DOMAIN = "AUREON-PLUMBER-V02-RECIPIENT-PROOF"
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PUBLIC_KEY = re.compile(r"^[0-9a-f]{64}$")
_SIGNATURE = re.compile(r"^[0-9a-f]{128}$")
_MAX_CHALLENGE_TTL_MS = 5 * 60 * 1000


class RecipientProofError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


def _identifier(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise RecipientProofError(code)
    return value


def _sha256(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise RecipientProofError(code)
    return value


def _uint(value: object, *, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RecipientProofError(code)
    return value


def _system_now_ms() -> int:
    return time.time_ns() // 1_000_000


@dataclass(frozen=True, slots=True)
class RecipientEnrollmentV02:
    recipient_id: str
    principal: str
    key_id: str
    public_key_hex: str
    allowed_channel_bindings: tuple[str, ...]
    allowed_purposes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_channel_bindings, list | tuple):
            raise RecipientProofError("recipient_channel_policy_invalid")
        if not isinstance(self.allowed_purposes, list | tuple):
            raise RecipientProofError("recipient_purpose_policy_invalid")
        object.__setattr__(
            self,
            "allowed_channel_bindings",
            tuple(self.allowed_channel_bindings),
        )
        object.__setattr__(self, "allowed_purposes", tuple(self.allowed_purposes))
        _identifier(self.recipient_id, code="recipient_id_invalid")
        _identifier(self.principal, code="recipient_principal_invalid")
        _identifier(self.key_id, code="recipient_key_id_invalid")
        if not isinstance(self.public_key_hex, str) or _PUBLIC_KEY.fullmatch(self.public_key_hex) is None:
            raise RecipientProofError("recipient_public_key_invalid")
        if not self.allowed_channel_bindings or len(set(self.allowed_channel_bindings)) != len(
            self.allowed_channel_bindings
        ):
            raise RecipientProofError("recipient_channel_policy_invalid")
        for value in self.allowed_channel_bindings:
            _sha256(value, code="recipient_channel_policy_invalid")
        if not self.allowed_purposes or len(set(self.allowed_purposes)) != len(self.allowed_purposes):
            raise RecipientProofError("recipient_purpose_policy_invalid")
        for value in self.allowed_purposes:
            _identifier(value, code="recipient_purpose_policy_invalid")


@dataclass(frozen=True, slots=True)
class RecipientChallengeV02:
    schema: str
    challenge_id: str
    session_id: str
    packet_commitment: str
    purpose: str
    channel_binding_sha256: str
    nonce: str
    issued_at_ms: int
    expires_at_ms: int

    def payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "challenge_id": self.challenge_id,
            "session_id": self.session_id,
            "packet_commitment": self.packet_commitment,
            "purpose": self.purpose,
            "channel_binding_sha256": self.channel_binding_sha256,
            "nonce": self.nonce,
            "issued_at_ms": self.issued_at_ms,
            "expires_at_ms": self.expires_at_ms,
        }

    @property
    def commitment(self) -> str:
        return domain_hash("AUREON-PLUMBER-V02-RECIPIENT-CHALLENGE", self.payload())


@dataclass(frozen=True, slots=True)
class RecipientProofV02:
    schema: str
    challenge_commitment: str
    recipient_id: str
    principal: str
    key_id: str
    session_id: str
    packet_commitment: str
    purpose: str
    channel_binding_sha256: str
    signed_at_ms: int
    signature_hex: str

    def signed_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "challenge_commitment": self.challenge_commitment,
            "recipient_id": self.recipient_id,
            "principal": self.principal,
            "key_id": self.key_id,
            "session_id": self.session_id,
            "packet_commitment": self.packet_commitment,
            "purpose": self.purpose,
            "channel_binding_sha256": self.channel_binding_sha256,
            "signed_at_ms": self.signed_at_ms,
        }

    def public_dict(self) -> dict[str, Any]:
        return {**self.signed_payload(), "signature_hex": self.signature_hex}

    @property
    def commitment(self) -> str:
        return domain_hash("AUREON-PLUMBER-V02-RECIPIENT-PROOF-RECEIPT", self.public_dict())


def build_recipient_challenge_v02(
    *,
    session_id: str,
    packet_commitment: str,
    purpose: str,
    channel_binding_sha256: str,
    ttl_ms: int = 60_000,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> RecipientChallengeV02:
    now = _uint(trusted_now_ms(), code="trusted_time_invalid")
    ttl = _uint(ttl_ms, code="challenge_ttl_invalid")
    if ttl == 0 or ttl > _MAX_CHALLENGE_TTL_MS:
        raise RecipientProofError("challenge_ttl_invalid")
    return RecipientChallengeV02(
        schema=CHALLENGE_SCHEMA,
        challenge_id=f"challenge-{b64url_encode(secrets.token_bytes(18))}",
        session_id=_identifier(session_id, code="session_id_invalid"),
        packet_commitment=_sha256(packet_commitment, code="packet_commitment_invalid"),
        purpose=_identifier(purpose, code="purpose_invalid"),
        channel_binding_sha256=_sha256(channel_binding_sha256, code="channel_binding_invalid"),
        nonce=b64url_encode(secrets.token_bytes(32)),
        issued_at_ms=now,
        expires_at_ms=now + ttl,
    )


def build_recipient_proof_v02(
    challenge: RecipientChallengeV02,
    *,
    enrollment: RecipientEnrollmentV02,
    private_key: Ed25519PrivateKey,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> RecipientProofV02:
    if not isinstance(challenge, RecipientChallengeV02):
        raise RecipientProofError("challenge_type_invalid")
    now = _uint(trusted_now_ms(), code="trusted_time_invalid")
    if now < challenge.issued_at_ms or now >= challenge.expires_at_ms:
        raise RecipientProofError("challenge_not_current")
    if ed25519_public_key_hex(private_key) != enrollment.public_key_hex:
        raise RecipientProofError("recipient_private_key_not_enrolled")
    if challenge.channel_binding_sha256 not in enrollment.allowed_channel_bindings:
        raise RecipientProofError("recipient_channel_not_enrolled")
    if challenge.purpose not in enrollment.allowed_purposes:
        raise RecipientProofError("recipient_purpose_not_enrolled")
    unsigned = RecipientProofV02(
        schema=PROOF_SCHEMA,
        challenge_commitment=challenge.commitment,
        recipient_id=enrollment.recipient_id,
        principal=enrollment.principal,
        key_id=enrollment.key_id,
        session_id=challenge.session_id,
        packet_commitment=challenge.packet_commitment,
        purpose=challenge.purpose,
        channel_binding_sha256=challenge.channel_binding_sha256,
        signed_at_ms=now,
        signature_hex="",
    )
    return RecipientProofV02(
        **unsigned.signed_payload(),
        signature_hex=sign_ed25519(private_key, unsigned.signed_payload(), domain=_SIGNING_DOMAIN),
    )


def verify_recipient_proof_v02(
    proof: RecipientProofV02,
    challenge: RecipientChallengeV02,
    *,
    enrollment: RecipientEnrollmentV02,
    expected_packet_commitment: str,
    expected_purpose: str,
    expected_channel_binding_sha256: str,
    trusted_now_ms: Callable[[], int] = _system_now_ms,
) -> dict[str, Any]:
    if not isinstance(proof, RecipientProofV02) or not isinstance(challenge, RecipientChallengeV02):
        raise RecipientProofError("recipient_proof_type_invalid")
    expected_packet = _sha256(expected_packet_commitment, code="packet_commitment_invalid")
    expected_channel = _sha256(expected_channel_binding_sha256, code="channel_binding_invalid")
    purpose = _identifier(expected_purpose, code="purpose_invalid")
    now = _uint(trusted_now_ms(), code="trusted_time_invalid")
    if challenge.schema != CHALLENGE_SCHEMA or proof.schema != PROOF_SCHEMA:
        raise RecipientProofError("recipient_wire_downgrade_or_schema_mismatch")
    if now < challenge.issued_at_ms or now >= challenge.expires_at_ms:
        raise RecipientProofError("challenge_not_current")
    if (
        proof.signed_at_ms < challenge.issued_at_ms
        or proof.signed_at_ms > now
        or proof.signed_at_ms >= challenge.expires_at_ms
    ):
        raise RecipientProofError("recipient_proof_timestamp_invalid")
    if proof.challenge_commitment != challenge.commitment:
        raise RecipientProofError("recipient_challenge_commitment_mismatch")
    exact = {
        "session_id": challenge.session_id,
        "packet_commitment": expected_packet,
        "purpose": purpose,
        "channel_binding_sha256": expected_channel,
    }
    if any(getattr(challenge, key) != value or getattr(proof, key) != value for key, value in exact.items()):
        raise RecipientProofError("recipient_context_mismatch")
    if (
        proof.recipient_id != enrollment.recipient_id
        or proof.principal != enrollment.principal
        or proof.key_id != enrollment.key_id
    ):
        raise RecipientProofError("recipient_enrollment_mismatch")
    if expected_channel not in enrollment.allowed_channel_bindings or purpose not in enrollment.allowed_purposes:
        raise RecipientProofError("recipient_enrollment_policy_denied")
    if not isinstance(proof.signature_hex, str) or _SIGNATURE.fullmatch(proof.signature_hex) is None:
        raise RecipientProofError("recipient_signature_invalid")
    if not verify_ed25519(
        enrollment.public_key_hex,
        proof.signed_payload(),
        proof.signature_hex,
        domain=_SIGNING_DOMAIN,
    ):
        raise RecipientProofError("recipient_signature_invalid")
    return {
        "valid": True,
        "recipient_id": proof.recipient_id,
        "session_id": proof.session_id,
        "packet_commitment": proof.packet_commitment,
        "purpose": proof.purpose,
        "channel_binding_sha256": proof.channel_binding_sha256,
        "proof_commitment": proof.commitment,
    }


class RecipientProofVerifierV02:
    """Verifier-owned enrollment, challenge issuance, and one-use registry."""

    production_ready = False

    def __init__(
        self,
        *,
        enrollments: Mapping[str, RecipientEnrollmentV02],
        trusted_now_ms: Callable[[], int] = _system_now_ms,
    ) -> None:
        if not enrollments or not callable(trusted_now_ms):
            raise RecipientProofError("recipient_verifier_configuration_invalid")
        normalized: dict[str, RecipientEnrollmentV02] = {}
        for recipient_id, enrollment in enrollments.items():
            if (
                not isinstance(enrollment, RecipientEnrollmentV02)
                or recipient_id != enrollment.recipient_id
                or recipient_id in normalized
            ):
                raise RecipientProofError("recipient_enrollment_registry_invalid")
            normalized[recipient_id] = enrollment
        self._enrollments = normalized
        self._trusted_now_ms = trusted_now_ms
        self._issued: dict[str, RecipientChallengeV02] = {}
        self._consumed: set[str] = set()
        self._sessions: set[str] = set()
        self._lock = threading.RLock()

    def enrollment_for(self, recipient_id: str) -> RecipientEnrollmentV02:
        identity = _identifier(recipient_id, code="recipient_id_invalid")
        enrollment = self._enrollments.get(identity)
        if enrollment is None:
            raise RecipientProofError("recipient_not_enrolled")
        return enrollment

    def issue_challenge(
        self,
        *,
        session_id: str,
        packet_commitment: str,
        purpose: str,
        channel_binding_sha256: str,
        ttl_ms: int = 60_000,
    ) -> RecipientChallengeV02:
        with self._lock:
            session = _identifier(session_id, code="session_id_invalid")
            if session in self._sessions:
                raise RecipientProofError("recipient_challenge_session_reused")
            challenge = build_recipient_challenge_v02(
                session_id=session,
                packet_commitment=packet_commitment,
                purpose=purpose,
                channel_binding_sha256=channel_binding_sha256,
                ttl_ms=ttl_ms,
                trusted_now_ms=self._trusted_now_ms,
            )
            self._issued[challenge.commitment] = challenge
            self._sessions.add(session)
            return challenge

    def verify_and_consume(
        self,
        proof: RecipientProofV02,
        challenge: RecipientChallengeV02,
        *,
        expected_packet_commitment: str,
        expected_purpose: str,
        expected_channel_binding_sha256: str,
    ) -> dict[str, Any]:
        if not isinstance(proof, RecipientProofV02):
            raise RecipientProofError("recipient_proof_type_invalid")
        with self._lock:
            commitment = challenge.commitment
            issued = self._issued.get(commitment)
            if issued != challenge:
                raise RecipientProofError("recipient_challenge_not_verifier_issued")
            if commitment in self._consumed:
                raise RecipientProofError("recipient_challenge_replayed")
            enrollment = self.enrollment_for(proof.recipient_id)
            summary = verify_recipient_proof_v02(
                proof,
                challenge,
                enrollment=enrollment,
                expected_packet_commitment=expected_packet_commitment,
                expected_purpose=expected_purpose,
                expected_channel_binding_sha256=expected_channel_binding_sha256,
                trusted_now_ms=self._trusted_now_ms,
            )
            self._consumed.add(commitment)
            return summary


__all__ = [
    "CHALLENGE_SCHEMA",
    "PROOF_SCHEMA",
    "RecipientChallengeV02",
    "RecipientEnrollmentV02",
    "RecipientProofError",
    "RecipientProofV02",
    "RecipientProofVerifierV02",
    "build_recipient_challenge_v02",
    "build_recipient_proof_v02",
    "verify_recipient_proof_v02",
]
