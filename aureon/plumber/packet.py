"""Pinned-trust semantic validation for Aureon Plumber v0 packets.

The established HNC validator remains authoritative for its encrypted carrier.
Without an explicit :class:`PacketTrustPolicy`, quorum policy pin, observer
transcript, and replay guard, inspection is structural-only and returns HOLD.
Embedded self-signatures never establish trust.
"""

from __future__ import annotations

import threading
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Self, cast

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .crypto import (
    b64url_decode,
    canonical_json_bytes,
    decode_canonical_json,
    domain_hash,
    ed25519_public_key_hex,
    load_ed25519_private_key,
    load_ed25519_public_key,
    sha256_hex,
    sign_ed25519,
    verify_ed25519,
)
from .immune_gate import GateClass
from .observer_transcript import ObserverTranscriptV0
from .quorum import AuthorityPermit, QuorumPolicyV0, evaluate_quorum
from .receipts import ReceiptKind, SignedReceipt
from .schema import (
    DenialCode,
    PlumberPacketV0,
    SchemaError,
    format_timestamp,
    freeze_mapping,
    parse_timestamp,
    require_aware_datetime,
    require_exact_keys,
    require_int,
    require_nonblank,
    require_sha256,
)
from .source_identity import SourceIdentityV0
from .spore_transport import SporeManifest
from .sympathetic_identity import SympatheticIdentityV0
from .temporal_identity import TemporalIdentityV0
from .twin_rune_seal import TwinRuneSealV0

HNC_PAYLOAD_BINDING_SCHEMA = "aureon.plumber.hnc-payload-binding.v0"
_PACKET_SIGNATURE_DOMAIN = "aureon.plumber.packet-signature.v0"
_REQUIRED_RECEIPT_KINDS = (
    str(ReceiptKind.FIELD),
    str(ReceiptKind.HEART),
    str(ReceiptKind.CONSCIENCE),
    str(ReceiptKind.GOVERNANCE),
)
_REFRESHABLE_CODES = {
    str(DenialCode.FUTURE_STATE),
    str(DenialCode.QUORUM_INCOMPLETE),
    str(DenialCode.STALE_STATE),
}


def _plain_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Thaw schema-frozen tuples/mappings through strict canonical JSON."""

    parsed = decode_canonical_json(canonical_json_bytes(value), require_mapping=True)
    if not isinstance(parsed, dict):  # pragma: no cover - guaranteed by the decoder
        raise SchemaError(DenialCode.INVALID_TYPE, field="mapping")
    return parsed


class PacketContractError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PacketDisposition(StrEnum):
    VALID = "valid"
    HOLD = "hold"
    DENY = "deny"


class PacketCode(StrEnum):
    HNC_CONTRACT_INVALID = "hnc_contract_invalid"
    HNC_BINDING_MISMATCH = "hnc_binding_mismatch"
    SOURCE_BINDING_INVALID = "source_binding_invalid"
    TEMPORAL_BINDING_INVALID = "temporal_binding_invalid"
    TEMPORAL_ANCHOR_REQUIRED = "temporal_anchor_required"
    OBSERVER_TRANSCRIPT_INVALID = "observer_transcript_invalid"
    SYMPATHETIC_IDENTITY_INVALID = "sympathetic_identity_invalid"
    TWIN_RUNE_INVALID = "twin_rune_invalid"
    SPORE_BINDING_INVALID = "spore_binding_invalid"
    RECEIPT_INVALID = "receipt_invalid"
    RECEIPT_STALE = "receipt_stale"
    QUORUM_POLICY_INVALID = "quorum_policy_invalid"
    QUORUM_POLICY_PIN_REQUIRED = "quorum_policy_pin_required"
    QUORUM_INVALID = "quorum_invalid"
    QUORUM_AUTHORITY_UNTRUSTED = "quorum_authority_untrusted"
    TRUST_POLICY_REQUIRED = "trust_policy_required"
    REPLAY_GUARD_REQUIRED = "replay_guard_required"
    REPLAY_DETECTED = "replay_detected"
    PACKET_SIGNATURE_MISSING = "packet_signature_missing"
    PACKET_SIGNATURE_INVALID = "packet_signature_invalid"
    PACKET_SIGNER_UNTRUSTED = "packet_signer_untrusted"
    RECEIPT_SIGNER_UNTRUSTED = "receipt_signer_untrusted"


_BINDING_FIELDS = (
    "schema",
    "hnc_magic",
    "hnc_schema_version",
    "hnc_packet_commitment",
    "hnc_alignment_commitment",
    "ciphertext_commitment",
    "purpose_commitment",
    "binding_commitment",
)


@dataclass(frozen=True, slots=True)
class HNCPayloadBindingV0:
    schema: str
    hnc_magic: str
    hnc_schema_version: int
    hnc_packet_commitment: str
    hnc_alignment_commitment: str
    ciphertext_commitment: str
    purpose_commitment: str
    binding_commitment: str

    def __post_init__(self) -> None:
        if self.schema != HNC_PAYLOAD_BINDING_SCHEMA:
            raise SchemaError(DenialCode.INVALID_SCHEMA, field="schema")
        require_nonblank(self.hnc_magic, field="hnc_magic")
        require_int(self.hnc_schema_version, field="hnc_schema_version", minimum=0)
        for field in _BINDING_FIELDS[3:]:
            require_sha256(getattr(self, field), field=field)
        if domain_hash("aureon.plumber.hnc-payload-binding.v0", self.commitment_payload()) != self.binding_commitment:
            raise SchemaError(DenialCode.PACKET_COMMITMENT_MISMATCH, field="binding_commitment")

    @classmethod
    def build(
        cls,
        *,
        hnc_magic: str,
        hnc_schema_version: int,
        hnc_packet_commitment: str,
        hnc_alignment_commitment: str,
        ciphertext_commitment: str,
        purpose_commitment: str,
    ) -> Self:
        values: dict[str, Any] = {
            "schema": HNC_PAYLOAD_BINDING_SCHEMA,
            "hnc_magic": hnc_magic,
            "hnc_schema_version": hnc_schema_version,
            "hnc_packet_commitment": hnc_packet_commitment,
            "hnc_alignment_commitment": hnc_alignment_commitment,
            "ciphertext_commitment": ciphertext_commitment,
            "purpose_commitment": purpose_commitment,
        }
        return cls(
            **values,
            binding_commitment=domain_hash("aureon.plumber.hnc-payload-binding.v0", values),
        )

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> Self:
        return cls(**require_exact_keys(value, _BINDING_FIELDS, field="hnc_payload_binding"))

    def commitment_payload(self) -> dict[str, Any]:
        return {field: getattr(self, field) for field in _BINDING_FIELDS if field != "binding_commitment"}

    def to_dict(self) -> dict[str, Any]:
        return {**self.commitment_payload(), "binding_commitment": self.binding_commitment}

    def public_summary(self) -> dict[str, Any]:
        return self.to_dict()


def bind_hnc_packet(hnc_packet: Mapping[str, Any]) -> HNCPayloadBindingV0:
    """Validate and bind one existing HNC packet without decoding it."""

    if not isinstance(hnc_packet, Mapping):
        raise PacketContractError(str(PacketCode.HNC_CONTRACT_INVALID))
    try:
        from aureon.harmonic.hnc_quantum_packet_crypto import validate_hnc_packet_contract

        validation = validate_hnc_packet_contract(hnc_packet)
        if not validation.get("valid"):
            raise PacketContractError(str(PacketCode.HNC_CONTRACT_INVALID))
        purpose = require_nonblank(validation.get("purpose"), field="hnc_packet.purpose", max_length=1024)
        b64url_decode(
            require_nonblank(
                hnc_packet.get("nonce_b64"),
                field="hnc_packet.nonce_b64",
                max_length=64,
            ),
            expected_bytes=12,
        )
        ciphertext = b64url_decode(
            require_nonblank(
                hnc_packet.get("ciphertext_b64"),
                field="hnc_packet.ciphertext_b64",
                max_length=32 * 1024 * 1024,
            )
        )
        return HNCPayloadBindingV0.build(
            hnc_magic=require_nonblank(hnc_packet.get("magic"), field="hnc_packet.magic"),
            hnc_schema_version=require_int(
                hnc_packet.get("schema_version"),
                field="hnc_packet.schema_version",
                minimum=0,
            ),
            hnc_packet_commitment=require_sha256(
                validation.get("packet_sha256"),
                field="hnc_packet.packet_sha256",
            ),
            hnc_alignment_commitment=require_sha256(
                validation.get("hnc_alignment_sha256"),
                field="hnc_packet.hnc_alignment_sha256",
            ),
            ciphertext_commitment=sha256_hex(ciphertext),
            purpose_commitment=domain_hash("aureon.plumber.purpose.v0", purpose),
        )
    except PacketContractError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        raise PacketContractError(str(PacketCode.HNC_CONTRACT_INVALID)) from exc


def _validate_authority_map(
    value: Mapping[str, Any],
    *,
    field: str,
    required_keys: set[str] | None = None,
    require_distinct: bool = False,
) -> Mapping[str, Any]:
    frozen = freeze_mapping(value, field=field)
    if required_keys is not None and set(frozen) != required_keys:
        raise SchemaError(DenialCode.INVALID_VALUE, field=field)
    authority_ids: set[str] = set()
    public_keys: set[str] = set()
    for role, authority in frozen.items():
        require_nonblank(role, field=f"{field}.role")
        parsed = require_exact_keys(authority, {"authority_id", "public_key"}, field=f"{field}.{role}")
        authority_id = require_nonblank(parsed["authority_id"], field=f"{field}.{role}.authority_id")
        public_key = ed25519_public_key_hex(load_ed25519_public_key(parsed["public_key"]))
        if require_distinct and (authority_id in authority_ids or public_key in public_keys):
            raise SchemaError(DenialCode.INVALID_VALUE, field=field)
        authority_ids.add(authority_id)
        public_keys.add(public_key)
    return frozen


@dataclass(frozen=True, slots=True)
class PacketTrustPolicy:
    """Pinned authorities; packet-embedded keys are never trust anchors."""

    packet_signer_public_keys: tuple[str, ...]
    receipt_authorities: Mapping[str, Mapping[str, str]]
    quorum_authorities: Mapping[str, Mapping[str, str]]
    expected_hardware_identity_commitment: str
    expected_operator_identity_commitment: str
    trust_policy_commitment: str

    def __post_init__(self) -> None:
        if not self.packet_signer_public_keys or tuple(sorted(set(self.packet_signer_public_keys))) != (
            self.packet_signer_public_keys
        ):
            raise SchemaError(DenialCode.INVALID_VALUE, field="packet_signer_public_keys")
        for key in self.packet_signer_public_keys:
            load_ed25519_public_key(key)
        object.__setattr__(
            self,
            "receipt_authorities",
            _validate_authority_map(
                self.receipt_authorities,
                field="receipt_authorities",
                required_keys=set(_REQUIRED_RECEIPT_KINDS),
                require_distinct=True,
            ),
        )
        object.__setattr__(
            self,
            "quorum_authorities",
            _validate_authority_map(self.quorum_authorities, field="quorum_authorities"),
        )
        require_sha256(
            self.expected_hardware_identity_commitment,
            field="expected_hardware_identity_commitment",
        )
        require_sha256(
            self.expected_operator_identity_commitment,
            field="expected_operator_identity_commitment",
        )
        require_sha256(self.trust_policy_commitment, field="trust_policy_commitment")
        if domain_hash("aureon.plumber.packet-trust-policy.v0", self.commitment_payload()) != (
            self.trust_policy_commitment
        ):
            raise SchemaError(DenialCode.INVALID_VALUE, field="trust_policy_commitment")

    @classmethod
    def build(
        cls,
        *,
        packet_signer_public_keys: Sequence[str],
        receipt_authorities: Mapping[str, Mapping[str, str]],
        quorum_authorities: Mapping[str, Mapping[str, str]],
        expected_hardware_identity_commitment: str,
        expected_operator_identity_commitment: str,
    ) -> PacketTrustPolicy:
        keys = tuple(sorted(set(packet_signer_public_keys)))
        values = {
            "packet_signer_public_keys": list(keys),
            "receipt_authorities": dict(receipt_authorities),
            "quorum_authorities": dict(quorum_authorities),
            "expected_hardware_identity_commitment": expected_hardware_identity_commitment,
            "expected_operator_identity_commitment": expected_operator_identity_commitment,
        }
        return cls(
            packet_signer_public_keys=keys,
            receipt_authorities=receipt_authorities,
            quorum_authorities=quorum_authorities,
            expected_hardware_identity_commitment=expected_hardware_identity_commitment,
            expected_operator_identity_commitment=expected_operator_identity_commitment,
            trust_policy_commitment=domain_hash("aureon.plumber.packet-trust-policy.v0", values),
        )

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "packet_signer_public_keys": list(self.packet_signer_public_keys),
            "receipt_authorities": {
                role: dict(authority) for role, authority in self.receipt_authorities.items()
            },
            "quorum_authorities": {
                role: dict(authority) for role, authority in self.quorum_authorities.items()
            },
            "expected_hardware_identity_commitment": self.expected_hardware_identity_commitment,
            "expected_operator_identity_commitment": self.expected_operator_identity_commitment,
        }

    def public_summary(self) -> dict[str, Any]:
        return {
            "packet_signer_count": len(self.packet_signer_public_keys),
            "receipt_authority_count": len(self.receipt_authorities),
            "quorum_authority_count": len(self.quorum_authorities),
            "trust_policy_commitment": self.trust_policy_commitment,
        }


@dataclass(slots=True)
class _TemporalAnchor:
    expected_previous_state_commitment: str
    minimum_counter: int
    expected_field_receipt_commitment: str
    expected_runtime_measurement_commitment: str


@dataclass(frozen=True, slots=True)
class _TemporalReservation:
    session_identity: str
    temporal_commitment: str
    nonce_commitment: str
    counter: int


class PacketReplayGuard:
    """Atomic, anchored in-memory replay guard for local-development execution."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._consumed: set[str] = set()
        self._anchors: dict[str, _TemporalAnchor] = {}
        self._reservations: dict[str, _TemporalReservation] = {}
        self._execution_claims: dict[str, _TemporalReservation] = {}
        self._reserved_sessions: set[str] = set()
        self._seen_temporal_commitments: set[str] = set()
        self._seen_nonce_commitments: set[str] = set()

    def register_temporal_anchor(
        self,
        session_identity: str,
        *,
        expected_previous_state_commitment: str,
        minimum_counter: int,
        expected_field_receipt_commitment: str,
        expected_runtime_measurement_commitment: str,
    ) -> bool:
        """Register one immutable external anchor for a session."""

        session = require_nonblank(session_identity, field="session_identity")
        require_sha256(
            expected_previous_state_commitment,
            field="expected_previous_state_commitment",
        )
        require_int(minimum_counter, field="minimum_counter", minimum=0)
        require_sha256(
            expected_field_receipt_commitment,
            field="expected_field_receipt_commitment",
        )
        require_sha256(
            expected_runtime_measurement_commitment,
            field="expected_runtime_measurement_commitment",
        )
        anchor = _TemporalAnchor(
            expected_previous_state_commitment=expected_previous_state_commitment,
            minimum_counter=minimum_counter,
            expected_field_receipt_commitment=expected_field_receipt_commitment,
            expected_runtime_measurement_commitment=expected_runtime_measurement_commitment,
        )
        with self._lock:
            if session in self._anchors:
                return False
            self._anchors[session] = anchor
            return True

    def has_temporal_anchor(self, session_identity: str) -> bool:
        session = require_nonblank(session_identity, field="session_identity")
        with self._lock:
            return session in self._anchors

    def has_seen(self, replay_token: str) -> bool:
        require_sha256(replay_token, field="replay_token")
        with self._lock:
            return (
                replay_token in self._consumed
                or replay_token in self._reservations
                or replay_token in self._execution_claims
            )

    def reserve_temporal(
        self,
        temporal: TemporalIdentityV0,
        replay_token: str,
        *,
        now: datetime,
    ) -> bool:
        """Atomically validate external continuity and reserve one temporal identity."""

        if not isinstance(temporal, TemporalIdentityV0):
            raise SchemaError(DenialCode.INVALID_TYPE, field="temporal_identity")
        require_sha256(replay_token, field="replay_token")
        current = require_aware_datetime(now, field="now")
        with self._lock:
            anchor = self._anchors.get(temporal.session_identity)
            if (
                anchor is None
                or replay_token in self._consumed
                or replay_token in self._reservations
                or replay_token in self._execution_claims
                or temporal.session_identity in self._reserved_sessions
            ):
                return False
            reserved_temporal = {
                reservation.temporal_commitment
                for reservation in (
                    *self._reservations.values(),
                    *self._execution_claims.values(),
                )
            }
            reserved_nonces = {
                reservation.nonce_commitment
                for reservation in (
                    *self._reservations.values(),
                    *self._execution_claims.values(),
                )
            }
            validation = temporal.validate(
                now=current,
                expected_previous_state_commitment=anchor.expected_previous_state_commitment,
                minimum_counter=anchor.minimum_counter,
                seen_temporal_commitments=self._seen_temporal_commitments | reserved_temporal,
                seen_nonce_commitments=self._seen_nonce_commitments | reserved_nonces,
            )
            external_anchors_match = (
                temporal.field_receipt_commitment
                == anchor.expected_field_receipt_commitment
                and temporal.runtime_measurement_commitment
                == anchor.expected_runtime_measurement_commitment
            )
            if not validation.valid or not external_anchors_match:
                return False
            self._reservations[replay_token] = _TemporalReservation(
                session_identity=temporal.session_identity,
                temporal_commitment=temporal.temporal_commitment,
                nonce_commitment=temporal.nonce_commitment,
                counter=temporal.counter,
            )
            self._reserved_sessions.add(temporal.session_identity)
            return True

    def claim_for_execution(self, replay_token: str) -> bool:
        """Atomically claim a reservation while pre-capability work runs."""

        require_sha256(replay_token, field="replay_token")
        with self._lock:
            if replay_token in self._consumed or replay_token in self._execution_claims:
                return False
            reservation = self._reservations.pop(replay_token, None)
            if reservation is None:
                return False
            self._execution_claims[replay_token] = reservation
            return True

    def rollback_execution_claim(self, replay_token: str) -> bool:
        """Return an uncommitted claim to its original reservation."""

        require_sha256(replay_token, field="replay_token")
        with self._lock:
            if replay_token in self._consumed or replay_token in self._reservations:
                return False
            reservation = self._execution_claims.pop(replay_token, None)
            if reservation is None:
                return False
            self._reservations[replay_token] = reservation
            return True

    def commit_execution_claim(self, replay_token: str) -> bool:
        """Irreversibly consume a claim immediately before capability dispatch."""

        require_sha256(replay_token, field="replay_token")
        with self._lock:
            reservation = self._execution_claims.pop(replay_token, None)
            if reservation is None:
                return False
            return self._commit_reservation(replay_token, reservation)

    def consume(self, replay_token: str) -> bool:
        require_sha256(replay_token, field="replay_token")
        with self._lock:
            reservation = self._reservations.pop(replay_token, None)
            if reservation is None:
                return False
            return self._commit_reservation(replay_token, reservation)

    def _commit_reservation(
        self,
        replay_token: str,
        reservation: _TemporalReservation,
    ) -> bool:
        """Commit one reservation while ``self._lock`` is held."""

        anchor = self._anchors.get(reservation.session_identity)
        if anchor is None:  # pragma: no cover - anchors are never removed
            return False
        self._reserved_sessions.remove(reservation.session_identity)
        self._consumed.add(replay_token)
        self._seen_temporal_commitments.add(reservation.temporal_commitment)
        self._seen_nonce_commitments.add(reservation.nonce_commitment)
        anchor.expected_previous_state_commitment = reservation.temporal_commitment
        anchor.minimum_counter = reservation.counter
        return True

    def public_summary(self) -> dict[str, Any]:
        with self._lock:
            summary = {
                "anchor_count": len(self._anchors),
                "reservation_count": len(self._reservations),
                "execution_claim_count": len(self._execution_claims),
                "consumed_count": len(self._consumed),
                "seen_temporal_count": len(self._seen_temporal_commitments),
                "seen_nonce_count": len(self._seen_nonce_commitments),
            }
        return {
            "scope": "in_memory_local_development_only",
            **summary,
            "persistent": False,
        }


def add_packet_signature(
    packet: PlumberPacketV0,
    private_key: Ed25519PrivateKey | bytes | str,
) -> PlumberPacketV0:
    if not isinstance(packet, PlumberPacketV0):
        raise SchemaError(DenialCode.INVALID_TYPE, field="packet")
    key = load_ed25519_private_key(private_key)
    signer = ed25519_public_key_hex(key)
    signature = sign_ed25519(
        key,
        {"packet_commitment": packet.packet_commitment},
        domain=_PACKET_SIGNATURE_DOMAIN,
    )
    values = packet.to_dict()
    values["signatures"] = {**values["signatures"], signer: signature}
    return PlumberPacketV0.from_dict(values)


@dataclass(frozen=True, slots=True)
class PacketInspection:
    disposition: PacketDisposition
    trusted: bool
    packet_identity: str
    session_identity: str
    temporal_counter: int
    inspected_at: str
    evidence_not_before: str
    evidence_expires_at: str
    gate_evidence_commitments: Mapping[str, str]
    packet_commitment: str
    purpose_commitment: str
    hnc_packet_commitment: str
    trust_policy_commitment: str
    quorum_policy_commitment: str
    quorum_commitment: str
    quorum_validated: bool
    replay_token: str
    denial_codes: tuple[str, ...]
    evidence_commitment: str
    inspection_commitment: str

    def __post_init__(self) -> None:
        try:
            disposition = PacketDisposition(self.disposition)
        except ValueError as exc:
            raise SchemaError(DenialCode.INVALID_VALUE, field="disposition") from exc
        object.__setattr__(self, "disposition", disposition)
        if type(self.trusted) is not bool or type(self.quorum_validated) is not bool:
            raise SchemaError(DenialCode.INVALID_TYPE, field="inspection_flags")
        require_nonblank(self.packet_identity, field="packet_identity")
        require_nonblank(self.session_identity, field="session_identity")
        require_int(self.temporal_counter, field="temporal_counter", minimum=0)
        inspected_at = parse_timestamp(self.inspected_at, field="inspected_at")
        evidence_not_before = parse_timestamp(
            self.evidence_not_before,
            field="evidence_not_before",
        )
        evidence_expires_at = parse_timestamp(
            self.evidence_expires_at,
            field="evidence_expires_at",
        )
        expected_gate_classes = {str(gate_class) for gate_class in GateClass}
        gate_commitments = freeze_mapping(
            self.gate_evidence_commitments,
            field="gate_evidence_commitments",
        )
        if set(gate_commitments) != expected_gate_classes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="gate_evidence_commitments")
        for commitment in gate_commitments.values():
            require_sha256(commitment, field="gate_evidence_commitments")
        object.__setattr__(self, "gate_evidence_commitments", gate_commitments)
        for field in (
            "packet_commitment",
            "purpose_commitment",
            "hnc_packet_commitment",
            "trust_policy_commitment",
            "quorum_policy_commitment",
            "quorum_commitment",
            "replay_token",
            "evidence_commitment",
            "inspection_commitment",
        ):
            require_sha256(getattr(self, field), field=field)
        if tuple(sorted(set(self.denial_codes))) != self.denial_codes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="denial_codes")
        if (disposition is PacketDisposition.VALID) != (not self.denial_codes):
            raise SchemaError(DenialCode.INVALID_VALUE, field="disposition")
        if disposition is PacketDisposition.VALID and (not self.trusted or not self.quorum_validated):
            raise SchemaError(DenialCode.INVALID_VALUE, field="trusted")
        if disposition is PacketDisposition.VALID and not (
            evidence_not_before <= inspected_at < evidence_expires_at
        ):
            raise SchemaError(DenialCode.INVALID_VALUE, field="evidence_window")
        if domain_hash("aureon.plumber.packet-inspection.v0", self.commitment_payload()) != self.inspection_commitment:
            raise SchemaError(DenialCode.PACKET_COMMITMENT_MISMATCH, field="inspection_commitment")

    @classmethod
    def build(cls, **values: Any) -> PacketInspection:
        payload = {
            **values,
            "disposition": str(values["disposition"]),
            "denial_codes": list(values["denial_codes"]),
        }
        return cls(
            **values,
            inspection_commitment=domain_hash("aureon.plumber.packet-inspection.v0", payload),
        )

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "disposition": str(self.disposition),
            "trusted": self.trusted,
            "packet_identity": self.packet_identity,
            "session_identity": self.session_identity,
            "temporal_counter": self.temporal_counter,
            "inspected_at": self.inspected_at,
            "evidence_not_before": self.evidence_not_before,
            "evidence_expires_at": self.evidence_expires_at,
            "gate_evidence_commitments": dict(self.gate_evidence_commitments),
            "packet_commitment": self.packet_commitment,
            "purpose_commitment": self.purpose_commitment,
            "hnc_packet_commitment": self.hnc_packet_commitment,
            "trust_policy_commitment": self.trust_policy_commitment,
            "quorum_policy_commitment": self.quorum_policy_commitment,
            "quorum_commitment": self.quorum_commitment,
            "quorum_validated": self.quorum_validated,
            "replay_token": self.replay_token,
            "denial_codes": list(self.denial_codes),
            "evidence_commitment": self.evidence_commitment,
        }

    def public_summary(self) -> dict[str, Any]:
        return {**self.commitment_payload(), "inspection_commitment": self.inspection_commitment}


def _signature_denials(packet: PlumberPacketV0, trust_policy: PacketTrustPolicy | None) -> tuple[set[str], set[str]]:
    hard: set[str] = set()
    holds: set[str] = set()
    if not packet.signatures:
        holds.add(str(PacketCode.PACKET_SIGNATURE_MISSING))
        return hard, holds
    valid_signers = {
        signer
        for signer, signature in packet.signatures.items()
        if verify_ed25519(
            signer,
            {"packet_commitment": packet.packet_commitment},
            signature,
            domain=_PACKET_SIGNATURE_DOMAIN,
        )
    }
    if len(valid_signers) != len(packet.signatures):
        hard.add(str(PacketCode.PACKET_SIGNATURE_INVALID))
    if trust_policy is not None:
        if not valid_signers & set(trust_policy.packet_signer_public_keys):
            hard.add(str(PacketCode.PACKET_SIGNER_UNTRUSTED))
        if set(packet.signatures) - set(trust_policy.packet_signer_public_keys):
            hard.add(str(PacketCode.PACKET_SIGNER_UNTRUSTED))
    return hard, holds


def inspect_plumber_packet(
    packet: PlumberPacketV0,
    hnc_packet: Mapping[str, Any],
    *,
    now: datetime,
    observer_transcript: ObserverTranscriptV0 | Mapping[str, Any] | None = None,
    sympathetic_identity: SympatheticIdentityV0 | Mapping[str, Any] | None = None,
    quorum_permits: Sequence[AuthorityPermit] = (),
    trust_policy: PacketTrustPolicy | None = None,
    required_quorum_policy_commitment: str | None = None,
    replay_guard: PacketReplayGuard | None = None,
) -> PacketInspection:
    """Inspect structurally, or establish trust only with every explicit pin."""

    if not isinstance(packet, PlumberPacketV0):
        raise SchemaError(DenialCode.INVALID_TYPE, field="packet")
    current = require_aware_datetime(now, field="now")
    inspected_at = format_timestamp(current.replace(microsecond=0))
    purpose_commitment = domain_hash("aureon.plumber.purpose.v0", packet.requested_purpose)
    hard: set[str] = set()
    holds: set[str] = set()
    evidence_not_before_values: list[datetime] = []
    evidence_expires_at_values: list[datetime] = []
    gate_evidence_commitments = {
        str(gate_class): domain_hash(
            "aureon.plumber.unavailable-gate-evidence.v0",
            {
                "packet_commitment": packet.packet_commitment,
                "gate_class": str(gate_class),
            },
        )
        for gate_class in GateClass
    }
    if trust_policy is None:
        holds.add(str(PacketCode.TRUST_POLICY_REQUIRED))
        trust_commitment = domain_hash("aureon.plumber.no-trust-policy.v0", {"packet": packet.packet_commitment})
    else:
        trust_commitment = trust_policy.trust_policy_commitment
    if trust_policy is not None and required_quorum_policy_commitment is None:
        holds.add(str(PacketCode.QUORUM_POLICY_PIN_REQUIRED))
    if required_quorum_policy_commitment is not None:
        require_sha256(required_quorum_policy_commitment, field="required_quorum_policy_commitment")
    if trust_policy is not None and replay_guard is None:
        holds.add(str(PacketCode.REPLAY_GUARD_REQUIRED))

    fallback_hnc = domain_hash("aureon.plumber.unavailable-hnc-binding.v0", packet.packet_commitment)
    live_binding: HNCPayloadBindingV0 | None = None
    live_ciphertext_size: int | None = None
    try:
        live_binding = bind_hnc_packet(hnc_packet)
        fallback_hnc = live_binding.hnc_packet_commitment
        live_ciphertext_size = len(
            b64url_decode(
                require_nonblank(
                    hnc_packet.get("ciphertext_b64"),
                    field="hnc_packet.ciphertext_b64",
                    max_length=32 * 1024 * 1024,
                )
            )
        )
    except PacketContractError:
        hard.add(str(PacketCode.HNC_CONTRACT_INVALID))
    try:
        packet_binding = HNCPayloadBindingV0.from_dict(_plain_mapping(packet.encrypted_payload))
        fallback_hnc = packet_binding.hnc_packet_commitment
        if live_binding is None or packet_binding != live_binding:
            hard.add(str(PacketCode.HNC_BINDING_MISMATCH))
        if packet_binding.purpose_commitment != purpose_commitment:
            hard.add(str(DenialCode.PURPOSE_MISMATCH))
    except (SchemaError, TypeError, ValueError):
        hard.add(str(PacketCode.HNC_BINDING_MISMATCH))
        packet_binding = None

    try:
        source = SourceIdentityV0.from_dict(_plain_mapping(packet.source_identity))
        if packet_binding is None or source.source_content_commitment != packet_binding.hnc_packet_commitment:
            hard.add(str(PacketCode.SOURCE_BINDING_INVALID))
    except (SchemaError, TypeError, ValueError):
        hard.add(str(PacketCode.SOURCE_BINDING_INVALID))
        source = None

    try:
        temporal = TemporalIdentityV0.from_dict(_plain_mapping(packet.temporal_identity))
        if temporal.packet_identity != packet.packet_identity:
            hard.add(str(PacketCode.TEMPORAL_BINDING_INVALID))
        temporal_issued_at = parse_timestamp(temporal.issued_at, field="issued_at")
        temporal_expires_at = parse_timestamp(temporal.expires_at, field="expires_at")
        evidence_not_before_values.append(temporal_issued_at)
        evidence_expires_at_values.append(temporal_expires_at)
        if current < temporal_issued_at or current >= temporal_expires_at:
            holds.add(str(PacketCode.RECEIPT_STALE))
        session_identity = temporal.session_identity
        temporal_counter = temporal.counter
        gate_evidence_commitments[str(GateClass.TEMPORAL)] = temporal.temporal_commitment
        replay_token = domain_hash(
            "aureon.plumber.packet-replay-token.v0",
            {
                "packet_commitment": packet.packet_commitment,
                "session_identity": temporal.session_identity,
                "counter": temporal.counter,
                "nonce_commitment": temporal.nonce_commitment,
            },
        )
    except (SchemaError, TypeError, ValueError):
        hard.add(str(PacketCode.TEMPORAL_BINDING_INVALID))
        temporal = None
        session_identity = "invalid-session"
        temporal_counter = 0
        replay_token = domain_hash("aureon.plumber.invalid-replay-token.v0", packet.packet_commitment)

    if replay_guard is not None and replay_guard.has_seen(replay_token):
        hard.add(str(PacketCode.REPLAY_DETECTED))

    parsed_observer: ObserverTranscriptV0 | None = None
    if observer_transcript is not None:
        try:
            parsed_observer = (
                observer_transcript
                if isinstance(observer_transcript, ObserverTranscriptV0)
                else ObserverTranscriptV0.from_dict(observer_transcript)
            )
            expected = (
                packet.packet_identity,
                session_identity,
                purpose_commitment,
                packet.hnc_observer_challenge,
                packet.observer_transcript_commitment,
            )
            actual = (
                parsed_observer.packet_identity,
                parsed_observer.session_identity,
                parsed_observer.purpose_commitment,
                parsed_observer.challenge_commitment,
                parsed_observer.transcript_commitment,
            )
            if actual != expected:
                hard.add(str(PacketCode.OBSERVER_TRANSCRIPT_INVALID))
            if source is not None and source.provenance_receipt_commitment not in (
                parsed_observer.source_receipt_commitments
            ):
                hard.add(str(PacketCode.OBSERVER_TRANSCRIPT_INVALID))
            if (
                temporal is None
                or temporal.observer_receipt_commitment
                != parsed_observer.transcript_commitment
            ):
                hard.add(str(PacketCode.TEMPORAL_BINDING_INVALID))
        except (SchemaError, TypeError, ValueError):
            hard.add(str(PacketCode.OBSERVER_TRANSCRIPT_INVALID))
    elif trust_policy is not None:
        hard.add(str(PacketCode.OBSERVER_TRANSCRIPT_INVALID))

    try:
        rune = TwinRuneSealV0.from_dict(_plain_mapping(packet.twin_rune_seal))
        expected_rune = (
            None if source is None else source.identity_commitment,
            packet.observer_transcript_commitment,
            None if temporal is None else temporal.temporal_commitment,
            purpose_commitment,
            packet.hnc_observer_challenge,
        )
        actual_rune = (
            rune.source_identity_commitment,
            rune.observer_transcript_commitment,
            rune.temporal_identity_commitment,
            rune.purpose_commitment,
            rune.challenge_commitment,
        )
        if actual_rune != expected_rune:
            hard.add(str(PacketCode.TWIN_RUNE_INVALID))
    except (SchemaError, TypeError, ValueError):
        hard.add(str(PacketCode.TWIN_RUNE_INVALID))

    try:
        policy = QuorumPolicyV0.from_dict(_plain_mapping(packet.quorum_policy))
        policy_commitment = policy.policy_commitment
        if required_quorum_policy_commitment is not None and policy_commitment != required_quorum_policy_commitment:
            hard.add(str(PacketCode.QUORUM_POLICY_INVALID))
    except (SchemaError, TypeError, ValueError):
        hard.add(str(PacketCode.QUORUM_POLICY_INVALID))
        policy = None
        policy_commitment = domain_hash("aureon.plumber.invalid-quorum-policy.v0", packet.packet_commitment)

    parsed_sympathetic: SympatheticIdentityV0 | None = None
    if sympathetic_identity is not None:
        try:
            parsed_sympathetic = (
                sympathetic_identity
                if isinstance(sympathetic_identity, SympatheticIdentityV0)
                else SympatheticIdentityV0.from_dict(sympathetic_identity)
            )
            expected_sympathetic = (
                None if source is None else source.identity_commitment,
                None if temporal is None else temporal.temporal_commitment,
                None if parsed_observer is None else parsed_observer.transcript_commitment,
                purpose_commitment,
                None if policy is None else policy.policy_commitment,
                packet.sympathetic_identity_commitment,
            )
            actual_sympathetic = (
                parsed_sympathetic.source_identity_commitment,
                parsed_sympathetic.temporal_identity_commitment,
                parsed_sympathetic.observer_identity_commitment,
                parsed_sympathetic.purpose_commitment,
                parsed_sympathetic.policy_commitment,
                parsed_sympathetic.identity_commitment,
            )
            if actual_sympathetic != expected_sympathetic:
                hard.add(str(PacketCode.SYMPATHETIC_IDENTITY_INVALID))
            if trust_policy is not None and (
                parsed_sympathetic.hardware_identity_commitment
                != trust_policy.expected_hardware_identity_commitment
                or parsed_sympathetic.operator_identity_commitment
                != trust_policy.expected_operator_identity_commitment
            ):
                hard.add(str(PacketCode.SYMPATHETIC_IDENTITY_INVALID))
            gate_evidence_commitments[str(GateClass.IDENTITY)] = (
                parsed_sympathetic.identity_commitment
            )
        except (SchemaError, TypeError, ValueError):
            hard.add(str(PacketCode.SYMPATHETIC_IDENTITY_INVALID))
            parsed_sympathetic = None
    elif trust_policy is not None:
        hard.add(str(PacketCode.SYMPATHETIC_IDENTITY_INVALID))

    try:
        manifest = SporeManifest.from_dict(_plain_mapping(packet.spore_manifest))
        if (
            packet_binding is None
            or temporal is None
            or manifest.ciphertext_commitment != packet_binding.ciphertext_commitment
            or manifest.packet_identity != packet.packet_identity
            or manifest.temporal_epoch != temporal.counter
            or manifest.challenge_commitment != packet.hnc_observer_challenge
            or live_ciphertext_size is None
            or manifest.ciphertext_size != live_ciphertext_size
        ):
            hard.add(str(PacketCode.SPORE_BINDING_INVALID))
        manifest_expires_at = parse_timestamp(manifest.expires_at, field="expires_at")
        evidence_expires_at_values.append(manifest_expires_at)
        if current >= manifest_expires_at:
            holds.add(str(PacketCode.RECEIPT_STALE))
    except (SchemaError, TypeError, ValueError):
        hard.add(str(PacketCode.SPORE_BINDING_INVALID))

    receipt_fields = (
        ("canonical_field_receipt", ReceiptKind.FIELD, GateClass.FIELD),
        ("heart_receipt", ReceiptKind.HEART, GateClass.HEART),
        ("conscience_receipt", ReceiptKind.CONSCIENCE, GateClass.CONSCIENCE),
        ("governance_receipt", ReceiptKind.GOVERNANCE, GateClass.GOVERNANCE),
    )
    for field, kind, gate_class in receipt_fields:
        try:
            receipt = SignedReceipt.from_dict(_plain_mapping(getattr(packet, field)))
            gate_evidence_commitments[str(gate_class)] = receipt.receipt_hash
            evidence_not_before_values.append(
                parse_timestamp(receipt.issued_at, field="issued_at")
            )
            evidence_expires_at_values.append(
                parse_timestamp(receipt.expires_at, field="expires_at")
            )
            expected_key = None
            if trust_policy is not None:
                authority = trust_policy.receipt_authorities[str(kind)]
                expected_key = authority["public_key"]
                if receipt.signer_id != authority["authority_id"]:
                    hard.add(str(PacketCode.RECEIPT_SIGNER_UNTRUSTED))
            validation = receipt.validate(
                now=current,
                expected_packet_identity=packet.packet_identity,
                expected_session_identity=session_identity,
                expected_purpose_commitment=purpose_commitment,
                expected_signer_public_key=expected_key,
            )
            if receipt.kind != kind:
                hard.add(str(PacketCode.RECEIPT_INVALID))
            for code in validation.denial_codes:
                if code in _REFRESHABLE_CODES:
                    holds.add(str(PacketCode.RECEIPT_STALE))
                elif code == str(DenialCode.SIGNER_MISMATCH):
                    hard.add(str(PacketCode.RECEIPT_SIGNER_UNTRUSTED))
                else:
                    hard.add(str(PacketCode.RECEIPT_INVALID))
            if source is not None and receipt.source_identity_commitment != source.identity_commitment:
                hard.add(str(PacketCode.RECEIPT_INVALID))
            if temporal is not None and receipt.temporal_identity_commitment != temporal.temporal_commitment:
                hard.add(str(PacketCode.RECEIPT_INVALID))
            if (
                temporal is None
                or receipt.runtime_measurement_commitment
                != temporal.runtime_measurement_commitment
            ):
                hard.add(str(PacketCode.RECEIPT_INVALID))
            if receipt.observer_transcript_commitment != packet.observer_transcript_commitment:
                hard.add(str(PacketCode.RECEIPT_INVALID))
            if policy is not None and receipt.policy_commitment != policy.policy_commitment:
                hard.add(str(PacketCode.RECEIPT_INVALID))
        except (KeyError, SchemaError, TypeError, ValueError):
            hard.add(str(PacketCode.RECEIPT_INVALID))

    signature_hard, signature_holds = _signature_denials(packet, trust_policy)
    hard.update(signature_hard)
    holds.update(signature_holds)

    quorum_commitment = domain_hash("aureon.plumber.no-quorum-validation.v0", policy_commitment)
    quorum_validated = False
    if policy is not None and temporal is not None:
        try:
            for permit in quorum_permits:
                if not isinstance(permit, AuthorityPermit):
                    raise SchemaError(DenialCode.INVALID_TYPE, field="quorum_permits")
                evidence_not_before_values.append(
                    parse_timestamp(permit.issued_at, field="issued_at")
                )
                evidence_expires_at_values.append(
                    parse_timestamp(permit.expires_at, field="expires_at")
                )
            quorum_validation = evaluate_quorum(
                policy,
                quorum_permits,
                now=current,
                packet_identity=packet.packet_identity,
                session_identity=temporal.session_identity,
                purpose_commitment=purpose_commitment,
            )
            quorum_commitment = quorum_validation.permit_set_commitment
            for code in quorum_validation.denial_codes:
                if code in _REFRESHABLE_CODES:
                    holds.add(str(PacketCode.QUORUM_INVALID))
                else:
                    hard.add(str(PacketCode.QUORUM_INVALID))
            pinned = trust_policy is not None
            if trust_policy is not None:
                if set(policy.required_roles) != set(trust_policy.quorum_authorities):
                    hard.add(str(PacketCode.QUORUM_AUTHORITY_UNTRUSTED))
                    pinned = False
                for permit in quorum_permits:
                    quorum_authority = trust_policy.quorum_authorities.get(permit.role)
                    if quorum_authority is None or (
                        permit.authority_id != quorum_authority["authority_id"]
                        or permit.signer_public_key != quorum_authority["public_key"]
                    ):
                        hard.add(str(PacketCode.QUORUM_AUTHORITY_UNTRUSTED))
                        pinned = False
            quorum_validated = quorum_validation.valid and pinned
        except (KeyError, SchemaError, TypeError, ValueError):
            hard.add(str(PacketCode.QUORUM_INVALID))

    ready_for_temporal_reservation = (
        trust_policy is not None
        and required_quorum_policy_commitment is not None
        and replay_guard is not None
        and parsed_observer is not None
        and parsed_sympathetic is not None
        and temporal is not None
        and quorum_validated
        and not hard
        and not holds
    )
    temporal_reserved = False
    if ready_for_temporal_reservation:
        trusted_replay_guard = cast(PacketReplayGuard, replay_guard)
        trusted_temporal = cast(TemporalIdentityV0, temporal)
        if not trusted_replay_guard.has_temporal_anchor(
            trusted_temporal.session_identity
        ):
            hard.add(str(PacketCode.TEMPORAL_ANCHOR_REQUIRED))
        elif not trusted_replay_guard.reserve_temporal(
            trusted_temporal,
            replay_token,
            now=current,
        ):
            hard.add(str(PacketCode.TEMPORAL_BINDING_INVALID))
            hard.add(str(PacketCode.REPLAY_DETECTED))
        else:
            temporal_reserved = True
    trusted = ready_for_temporal_reservation and temporal_reserved and not hard and not holds
    if hard:
        disposition = PacketDisposition.DENY
        codes = tuple(sorted(hard | holds))
    elif holds or not trusted:
        disposition = PacketDisposition.HOLD
        codes = tuple(sorted(holds or {str(PacketCode.TRUST_POLICY_REQUIRED)}))
    else:
        disposition = PacketDisposition.VALID
        codes = ()
    evidence_not_before = format_timestamp(
        max(evidence_not_before_values)
        if evidence_not_before_values
        else current.replace(microsecond=0)
    )
    evidence_expires_at = format_timestamp(
        min(evidence_expires_at_values)
        if evidence_expires_at_values
        else current.replace(microsecond=0)
    )
    evidence = {
        "packet_commitment": packet.packet_commitment,
        "hnc_packet_commitment": fallback_hnc,
        "purpose_commitment": purpose_commitment,
        "trust_policy_commitment": trust_commitment,
        "quorum_policy_commitment": policy_commitment,
        "quorum_commitment": quorum_commitment,
        "replay_token": replay_token,
        "inspected_at": inspected_at,
        "evidence_not_before": evidence_not_before,
        "evidence_expires_at": evidence_expires_at,
        "gate_evidence_commitments": gate_evidence_commitments,
    }
    return PacketInspection.build(
        disposition=disposition,
        trusted=trusted,
        packet_identity=packet.packet_identity,
        session_identity=session_identity,
        temporal_counter=temporal_counter,
        inspected_at=inspected_at,
        evidence_not_before=evidence_not_before,
        evidence_expires_at=evidence_expires_at,
        gate_evidence_commitments=gate_evidence_commitments,
        packet_commitment=packet.packet_commitment,
        purpose_commitment=purpose_commitment,
        hnc_packet_commitment=fallback_hnc,
        trust_policy_commitment=trust_commitment,
        quorum_policy_commitment=policy_commitment,
        quorum_commitment=quorum_commitment,
        quorum_validated=quorum_validated,
        replay_token=replay_token,
        denial_codes=codes,
        evidence_commitment=domain_hash("aureon.plumber.packet-evidence.v0", evidence),
    )


__all__ = [
    "HNC_PAYLOAD_BINDING_SCHEMA",
    "HNCPayloadBindingV0",
    "PacketCode",
    "PacketContractError",
    "PacketDisposition",
    "PacketInspection",
    "PacketReplayGuard",
    "PacketTrustPolicy",
    "add_packet_signature",
    "bind_hnc_packet",
    "inspect_plumber_packet",
]
