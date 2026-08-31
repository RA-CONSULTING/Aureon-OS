"""Opaque five-role custody for the same-process Magic Star v0.2 lab path.

This adapter intentionally requires an insecure-development opt-in.  It keeps
the complete legacy carrier, its payload key, raw shares, reconstructed KEK and
plaintext inside one supported release call.  Python process isolation is not
an HSM, enclave or production custody boundary.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from aureon.harmonic.hnc_quantum_packet_crypto import (
    HNCPacketError,
    _normalize_hnc_key_material_for_validated_contract,
    decode_hnc_quantum_packet,
    validate_hnc_packet_contract,
)
from aureon.harmonic.hnc_quantum_packet_crypto import (
    canonical_json_bytes as legacy_canonical_json_bytes,
)

from .authorization_chain_v02 import (
    AuthorizationChainV02,
    validate_authorization_chain_v02,
    validate_authorization_trust_v02,
)
from .crypto import b64url_decode, b64url_encode, canonical_json_bytes, domain_hash, sha256_hex
from .magic_star_v02 import (
    POINT_ROLES,
    PROFILE_ID,
    PROTOCOL_ID,
    SOURCE_PROFILE_COMMITMENT,
    AuthorityBindingV02,
    MagicStarError,
    component_commitment_v02,
    sign_component_v02,
    verify_component_v02,
)
from .release_state_v02 import (
    InMemoryReleaseStateStoreV02,
    OpaqueCustodyLease,
)
from .schema import freeze_mapping, thaw_json

PROTECTED_PACKET_MAGIC = "AUREON-HNC-PLUMBER-MAGIC-STAR-V02"
PROTECTED_PACKET_SCHEMA = "aureon.plumber.magic-star.protected-packet.v02"
_MAX_INNER_BYTES = 16 * 1024 * 1024
_MAX_CAPABILITY_RESULT_BYTES = 64 * 1024


def _system_now_ms() -> int:
    return time.time_ns() // 1_000_000


class StarCustodyError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = str(code)
        super().__init__(self.code)


@dataclass(frozen=True, slots=True)
class RegisteredCapabilityV02:
    """A construction-time capability binding for the same-process lab."""

    capability_id: str
    measurement_sha256: str
    policy_measurement_sha256: str
    handler: Callable[[bytes], Mapping[str, Any]] = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        _identifier(self.capability_id, code="capability_id_invalid")
        _sha256(self.measurement_sha256, code="capability_measurement_invalid")
        _sha256(
            self.policy_measurement_sha256,
            code="capability_policy_measurement_invalid",
        )
        if not callable(self.handler):
            raise StarCustodyError("capability_handler_invalid")


def _sha256(value: object, *, code: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise StarCustodyError(code)
    return value


def _identifier(value: object, *, code: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 128
        or any(not (c.isascii() and (c.isalnum() or c in "._:/-")) for c in value)
    ):
        raise StarCustodyError(code)
    return value


def _xor(left: bytes, right: bytes) -> bytes:
    if len(left) != len(right):
        raise StarCustodyError("custody_share_length_mismatch")
    return bytes(a ^ b for a, b in zip(left, right, strict=True))


def _split_five(secret: bytes) -> tuple[bytes, ...]:
    shares = [os.urandom(len(secret)) for _ in range(4)]
    final = secret
    for share in shares:
        final = _xor(final, share)
    return (*shares, final)


def _join_five(shares: tuple[bytes, ...]) -> bytes:
    if len(shares) != 5:
        raise StarCustodyError("all_five_custody_shares_required")
    value = bytes(len(shares[0]))
    for share in shares:
        value = _xor(value, share)
    return value


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StarCustodyError("inner_json_duplicate_key")
        result[key] = value
    return result


def _assert_result_does_not_expose_plaintext(
    result: Mapping[str, Any],
    *,
    plaintext: bytes,
) -> bytes:
    """Reject direct encodings of plaintext at the last same-process boundary."""

    encoded = canonical_json_bytes(dict(result))
    if len(encoded) > _MAX_CAPABILITY_RESULT_BYTES:
        raise StarCustodyError("capability_result_too_large")
    if not plaintext:
        return encoded
    representations = {plaintext, plaintext.hex().encode("ascii")}
    representations.add(b64url_encode(plaintext).encode("ascii"))
    representations.add(base64.b64encode(plaintext))
    try:
        text = plaintext.decode("utf-8", errors="strict").encode("utf-8")
    except UnicodeDecodeError:
        text = b""
    if text:
        representations.add(text)
    lowered = encoded.lower()
    for representation in representations:
        if representation and representation.lower() in lowered:
            raise StarCustodyError("capability_plaintext_exfiltration_denied")
    return encoded


def _invoke_capability_safely(
    capability: RegisteredCapabilityV02,
    plaintext: bytes,
) -> tuple[dict[str, Any] | None, str | None]:
    """Drop handler exceptions before returning a stable, non-secret denial."""

    try:
        result = capability.handler(plaintext)
    except BaseException:
        return None, "capability_execution_failed"
    if not isinstance(result, Mapping):
        return None, "capability_result_must_be_mapping"
    try:
        public_result = dict(result)
    except BaseException:
        return None, "capability_execution_failed"
    try:
        _assert_result_does_not_expose_plaintext(public_result, plaintext=plaintext)
    except StarCustodyError as exc:
        return None, exc.code
    except BaseException:
        return None, "capability_execution_failed"
    return public_result, None


@dataclass(frozen=True, slots=True)
class ProtectedMagicStarPacketV02:
    magic: str
    schema: str
    protocol_id: str
    profile_id: str
    source_profile_commitment: str
    packet_id: str
    purpose: str
    release_context_sha256: str
    carrier_commitment: str
    share_bindings: tuple[Mapping[str, str], ...]
    nonce_b64: str
    ciphertext_b64: str
    aad_sha256: str
    source_signature: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "share_bindings",
            tuple(
                freeze_mapping(binding, field=f"share_bindings[{index}]")
                for index, binding in enumerate(self.share_bindings)
            ),
        )
        object.__setattr__(
            self,
            "source_signature",
            freeze_mapping(self.source_signature, field="source_signature"),
        )

    def unsigned_public_dict(self) -> dict[str, Any]:
        return {
            "magic": self.magic,
            "schema": self.schema,
            "protocol_id": self.protocol_id,
            "profile_id": self.profile_id,
            "source_profile_commitment": self.source_profile_commitment,
            "packet_id": self.packet_id,
            "purpose": self.purpose,
            "release_context_sha256": self.release_context_sha256,
            "carrier_commitment": self.carrier_commitment,
            "share_bindings": [thaw_json(item) for item in self.share_bindings],
            "nonce_b64": self.nonce_b64,
            "ciphertext_b64": self.ciphertext_b64,
            "aad_sha256": self.aad_sha256,
        }

    def public_dict(self) -> dict[str, Any]:
        return {
            **self.unsigned_public_dict(),
            "source_signature": thaw_json(self.source_signature),
        }

    @property
    def packet_commitment(self) -> str:
        return domain_hash("AUREON-PLUMBER-V02-PROTECTED-PACKET", self.public_dict())


@dataclass(slots=True)
class _CustodyRecord:
    shares: tuple[bytearray, ...]
    packet_commitment: str
    claimed: bool = False


def _outer_aad_fields(
    *,
    packet_id: str,
    purpose: str,
    release_context_sha256: str,
    carrier_commitment: str,
    share_bindings: tuple[Mapping[str, str], ...],
    source_key_id: str,
) -> dict[str, Any]:
    return {
        "magic": PROTECTED_PACKET_MAGIC,
        "schema": PROTECTED_PACKET_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        "packet_id": packet_id,
        "purpose": purpose,
        "release_context_sha256": release_context_sha256,
        "carrier_commitment": carrier_commitment,
        "share_bindings": [dict(item) for item in share_bindings],
        "source_key_id": source_key_id,
    }


def validate_magic_star_hnc_packet_v02(
    packet: ProtectedMagicStarPacketV02,
    *,
    source_authority: AuthorityBindingV02,
) -> dict[str, Any]:
    if not isinstance(packet, ProtectedMagicStarPacketV02):
        raise StarCustodyError("v02_protected_packet_type_invalid")
    if (
        packet.magic != PROTECTED_PACKET_MAGIC
        or packet.schema != PROTECTED_PACKET_SCHEMA
        or packet.protocol_id != PROTOCOL_ID
        or packet.profile_id != PROFILE_ID
        or packet.source_profile_commitment != SOURCE_PROFILE_COMMITMENT
    ):
        raise StarCustodyError("v02_protected_packet_schema_or_downgrade_invalid")
    if source_authority.role != "SOURCE":
        raise StarCustodyError("protected_packet_source_authority_invalid")
    packet_id = _identifier(packet.packet_id, code="packet_id_invalid")
    purpose = _identifier(packet.purpose, code="purpose_invalid")
    context = _sha256(packet.release_context_sha256, code="release_context_invalid")
    carrier = _sha256(packet.carrier_commitment, code="carrier_commitment_invalid")
    if len(packet.share_bindings) != len(POINT_ROLES):
        raise StarCustodyError("all_five_share_bindings_required")
    normalized_bindings: list[dict[str, str]] = []
    for role, item in zip(POINT_ROLES, packet.share_bindings, strict=True):
        if not isinstance(item, Mapping) or set(item) != {"role", "binding_sha256"}:
            raise StarCustodyError("share_binding_shape_invalid")
        if item.get("role") != role:
            raise StarCustodyError("share_binding_order_or_role_invalid")
        normalized_bindings.append(
            {"role": role, "binding_sha256": _sha256(item.get("binding_sha256"), code="share_binding_invalid")}
        )
    try:
        nonce = b64url_decode(packet.nonce_b64, expected_bytes=12)
        ciphertext = b64url_decode(packet.ciphertext_b64)
    except Exception as exc:
        raise StarCustodyError("protected_packet_cipher_encoding_invalid") from exc
    if len(ciphertext) < 17 or len(ciphertext) > _MAX_INNER_BYTES + 16:
        raise StarCustodyError("protected_packet_ciphertext_size_invalid")
    aad_fields = _outer_aad_fields(
        packet_id=packet_id,
        purpose=purpose,
        release_context_sha256=context,
        carrier_commitment=carrier,
        share_bindings=tuple(normalized_bindings),
        source_key_id=source_authority.key_id,
    )
    aad_sha256 = sha256_hex(canonical_json_bytes(aad_fields))
    if packet.aad_sha256 != aad_sha256:
        raise StarCustodyError("protected_packet_aad_hash_mismatch")
    try:
        signature_payload = verify_component_v02(
            packet.source_signature,
            expected_type="PROTECTED_PACKET_SOURCE_SIGNATURE",
            expected_authority=source_authority,
        )
    except MagicStarError as exc:
        raise StarCustodyError(exc.code) from exc
    expected_signature_payload = {
        **packet.unsigned_public_dict(),
        "protected_packet_unsigned_sha256": domain_hash(
            "AUREON-PLUMBER-V02-PROTECTED-PACKET-UNSIGNED", packet.unsigned_public_dict()
        ),
    }
    if signature_payload != expected_signature_payload:
        raise StarCustodyError("protected_packet_source_join_mismatch")
    return {
        "valid": True,
        "packet_id": packet_id,
        "purpose": purpose,
        "release_context_sha256": context,
        "carrier_commitment": carrier,
        "share_bindings": normalized_bindings,
        "nonce_bytes": len(nonce),
        "ciphertext_bytes": len(ciphertext),
        "source_signature_commitment": component_commitment_v02(packet.source_signature),
        "packet_commitment": packet.packet_commitment,
        "structural_preflight_only": True,
        "aead_authenticated": False,
        "production_ready": False,
    }


class LocalDevelopmentStarCustodyV02:
    """Same-process custody model; construction requires explicit insecure opt-in."""

    production_ready = False

    def __init__(
        self,
        *,
        allow_insecure_same_process: bool,
        source_authority: AuthorityBindingV02,
        source_private_key: Ed25519PrivateKey,
        state_store: InMemoryReleaseStateStoreV02,
        authorization_trust: Mapping[str, AuthorityBindingV02],
        capabilities: Mapping[str, RegisteredCapabilityV02],
        trusted_now_ms: Callable[[], int] = _system_now_ms,
    ) -> None:
        if allow_insecure_same_process is not True:
            raise StarCustodyError("explicit_insecure_same_process_opt_in_required")
        if source_authority.role != "SOURCE":
            raise StarCustodyError("protected_packet_source_authority_invalid")
        if not isinstance(state_store, InMemoryReleaseStateStoreV02):
            raise StarCustodyError("custody_release_state_store_invalid")
        try:
            validate_authorization_trust_v02(authorization_trust)
        except Exception as exc:
            raise StarCustodyError("custody_authorization_trust_invalid") from exc
        if authorization_trust["SOURCE"] != source_authority:
            raise StarCustodyError("custody_source_authority_join_mismatch")
        if not capabilities or not callable(trusted_now_ms):
            raise StarCustodyError("custody_capability_registry_invalid")
        normalized_capabilities: dict[str, RegisteredCapabilityV02] = {}
        for capability_id, capability in capabilities.items():
            if (
                not isinstance(capability, RegisteredCapabilityV02)
                or capability_id != capability.capability_id
                or capability_id in normalized_capabilities
            ):
                raise StarCustodyError("custody_capability_registry_invalid")
            normalized_capabilities[capability_id] = capability
        self._source_authority = source_authority
        self._source_private_key = source_private_key
        self._state_store = state_store
        self._authorization_trust = dict(authorization_trust)
        self._capabilities = normalized_capabilities
        self._trusted_now_ms = trusted_now_ms
        self._records: dict[str, _CustodyRecord] = {}
        self._lock = threading.RLock()

    def capability_measurement(self, capability_id: str) -> str:
        selected = _identifier(capability_id, code="capability_id_invalid")
        capability = self._capabilities.get(selected)
        if capability is None:
            raise StarCustodyError("capability_not_registered")
        return capability.measurement_sha256

    def capability_policy_measurement(self, capability_id: str) -> str:
        selected = _identifier(capability_id, code="capability_id_invalid")
        capability = self._capabilities.get(selected)
        if capability is None:
            raise StarCustodyError("capability_not_registered")
        return capability.policy_measurement_sha256

    def protect_carrier(
        self,
        *,
        packet_id: str,
        purpose: str,
        release_context_sha256: str,
        legacy_carrier: Mapping[str, Any],
        legacy_master_key: bytes | str,
    ) -> ProtectedMagicStarPacketV02:
        identity = _identifier(packet_id, code="packet_id_invalid")
        bounded_purpose = _identifier(purpose, code="purpose_invalid")
        context = _sha256(release_context_sha256, code="release_context_invalid")
        carrier = dict(legacy_carrier)
        contract = validate_hnc_packet_contract(carrier)
        if contract.get("valid") is not True:
            raise StarCustodyError("legacy_carrier_contract_invalid")
        metadata_candidate = carrier.get("metadata")
        metadata: Mapping[str, Any] = (
            metadata_candidate if isinstance(metadata_candidate, Mapping) else {}
        )
        if metadata.get("purpose") != bounded_purpose:
            raise StarCustodyError("legacy_carrier_purpose_mismatch")
        try:
            key_bytes = _normalize_hnc_key_material_for_validated_contract(
                legacy_master_key,
                contract,
            )
        except HNCPacketError as exc:
            raise StarCustodyError("legacy_master_key_invalid") from exc
        if len(key_bytes) > 4096:
            raise StarCustodyError("legacy_master_key_size_invalid")
        carrier_bytes = legacy_canonical_json_bytes(carrier)
        carrier_commitment = sha256_hex(carrier_bytes)
        inner = legacy_canonical_json_bytes(
            {
                "schema": "aureon.plumber.magic-star.inner-carrier.v02",
                "packet_id": identity,
                "purpose": bounded_purpose,
                "carrier": carrier,
                "carrier_master_key_b64": b64url_encode(key_bytes),
                "carrier_commitment": carrier_commitment,
            }
        )
        if len(inner) > _MAX_INNER_BYTES:
            raise StarCustodyError("inner_carrier_too_large")
        kek = os.urandom(32)
        shares = _split_five(kek)
        share_bindings = tuple(
            {
                "role": role,
                "binding_sha256": domain_hash(
                    "AUREON-PLUMBER-V02-SHARE-BINDING",
                    {
                        "packet_id": identity,
                        "role": role,
                        "share_sha256": sha256_hex(share),
                    },
                ),
            }
            for role, share in zip(POINT_ROLES, shares, strict=True)
        )
        aad_fields = _outer_aad_fields(
            packet_id=identity,
            purpose=bounded_purpose,
            release_context_sha256=context,
            carrier_commitment=carrier_commitment,
            share_bindings=share_bindings,
            source_key_id=self._source_authority.key_id,
        )
        aad = canonical_json_bytes(aad_fields)
        nonce = os.urandom(12)
        ciphertext = AESGCM(kek).encrypt(nonce, inner, aad)
        unsigned: dict[str, Any] = {
            "magic": PROTECTED_PACKET_MAGIC,
            "schema": PROTECTED_PACKET_SCHEMA,
            "protocol_id": PROTOCOL_ID,
            "profile_id": PROFILE_ID,
            "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
            "packet_id": identity,
            "purpose": bounded_purpose,
            "release_context_sha256": context,
            "carrier_commitment": carrier_commitment,
            "share_bindings": [dict(item) for item in share_bindings],
            "nonce_b64": b64url_encode(nonce),
            "ciphertext_b64": b64url_encode(ciphertext),
            "aad_sha256": sha256_hex(aad),
        }
        try:
            signature = sign_component_v02(
                component_type="PROTECTED_PACKET_SOURCE_SIGNATURE",
                authority=self._source_authority,
                payload={
                    **unsigned,
                    "protected_packet_unsigned_sha256": domain_hash(
                        "AUREON-PLUMBER-V02-PROTECTED-PACKET-UNSIGNED", unsigned
                    ),
                },
                private_key=self._source_private_key,
            )
        except MagicStarError as exc:
            raise StarCustodyError(exc.code) from exc
        packet = ProtectedMagicStarPacketV02(
            magic=PROTECTED_PACKET_MAGIC,
            schema=PROTECTED_PACKET_SCHEMA,
            protocol_id=PROTOCOL_ID,
            profile_id=PROFILE_ID,
            source_profile_commitment=SOURCE_PROFILE_COMMITMENT,
            packet_id=identity,
            purpose=bounded_purpose,
            release_context_sha256=context,
            carrier_commitment=carrier_commitment,
            share_bindings=share_bindings,
            nonce_b64=unsigned["nonce_b64"],
            ciphertext_b64=unsigned["ciphertext_b64"],
            aad_sha256=unsigned["aad_sha256"],
            source_signature=signature,
        )
        validate_magic_star_hnc_packet_v02(packet, source_authority=self._source_authority)
        with self._lock:
            if identity in self._records:
                raise StarCustodyError("protected_packet_id_reused")
            self._records[identity] = _CustodyRecord(
                shares=tuple(bytearray(share) for share in shares),
                packet_commitment=packet.packet_commitment,
            )
        kek_buffer = bytearray(kek)
        kek_buffer[:] = bytes(len(kek_buffer))
        return packet

    def release_to_capability(
        self,
        packet: ProtectedMagicStarPacketV02,
        *,
        lease: OpaqueCustodyLease,
        authorization_chain: AuthorizationChainV02,
        capability_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        preflight = validate_magic_star_hnc_packet_v02(
            packet, source_authority=self._source_authority
        )
        if not isinstance(lease, OpaqueCustodyLease) or lease.packet_id != packet.packet_id:
            raise StarCustodyError("custody_lease_packet_mismatch")
        try:
            lease_valid = self._state_store.validate_lease(lease)
        except Exception as exc:
            raise StarCustodyError("custody_lease_validation_failed") from exc
        if lease_valid is not True:
            raise StarCustodyError("custody_lease_validation_failed")
        selected_capability_id = _identifier(
            capability_id, code="capability_id_invalid"
        )
        registered_capability = self._capabilities.get(selected_capability_id)
        if registered_capability is None:
            raise StarCustodyError("capability_not_registered")
        try:
            authorization_summary = validate_authorization_chain_v02(
                authorization_chain,
                trust=self._authorization_trust,
                trusted_now_ms=self._trusted_now_ms,
            )
        except Exception as exc:
            raise StarCustodyError("custody_authorization_chain_invalid") from exc
        expected_auth_fields = {
            "packet_commitment": packet.packet_commitment,
            "session_id": lease.session_id,
            "purpose": packet.purpose,
            "policy_measurement_sha256": registered_capability.policy_measurement_sha256,
            "share_bindings": [item["binding_sha256"] for item in packet.share_bindings],
            "permit_count": 5,
        }
        if any(
            authorization_summary.get(key) != value
            for key, value in expected_auth_fields.items()
        ):
            raise StarCustodyError("custody_authorization_runtime_join_mismatch")
        with self._lock:
            record = self._records.get(packet.packet_id)
            if record is None or record.packet_commitment != packet.packet_commitment:
                raise StarCustodyError("custody_material_unavailable_or_reused")
            if record.claimed:
                raise StarCustodyError("custody_material_already_claimed")
            record.claimed = True

        share_bytes = tuple(bytes(share) for share in record.shares)
        material_consumed = False
        try:
            if len(share_bytes) != len(POINT_ROLES):
                raise StarCustodyError("all_five_custody_shares_required")
            actual_bindings = [
                domain_hash(
                    "AUREON-PLUMBER-V02-SHARE-BINDING",
                    {
                        "packet_id": packet.packet_id,
                        "role": role,
                        "share_sha256": sha256_hex(share),
                    },
                )
                for role, share in zip(POINT_ROLES, share_bytes, strict=True)
            ]
            if actual_bindings != expected_auth_fields["share_bindings"]:
                raise StarCustodyError("custody_share_binding_mismatch")
            kek = _join_five(share_bytes)
            aad_fields = _outer_aad_fields(
                packet_id=packet.packet_id,
                purpose=packet.purpose,
                release_context_sha256=packet.release_context_sha256,
                carrier_commitment=packet.carrier_commitment,
                share_bindings=packet.share_bindings,
                source_key_id=self._source_authority.key_id,
            )
            try:
                inner_bytes = AESGCM(kek).decrypt(
                    b64url_decode(packet.nonce_b64, expected_bytes=12),
                    b64url_decode(packet.ciphertext_b64),
                    canonical_json_bytes(aad_fields),
                )
            except InvalidTag as exc:
                raise StarCustodyError("protected_packet_authentication_failed") from exc
            try:
                inner = json.loads(
                    inner_bytes.decode("utf-8", errors="strict"),
                    object_pairs_hook=_reject_duplicate_pairs,
                    parse_constant=lambda _value: (_ for _ in ()).throw(
                        StarCustodyError("inner_json_non_finite_number")
                    ),
                )
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise StarCustodyError("inner_carrier_json_invalid") from exc
            if not isinstance(inner, dict) or set(inner) != {
                "schema",
                "packet_id",
                "purpose",
                "carrier",
                "carrier_master_key_b64",
                "carrier_commitment",
            }:
                raise StarCustodyError("inner_carrier_shape_invalid")
            if (
                inner["schema"] != "aureon.plumber.magic-star.inner-carrier.v02"
                or inner["packet_id"] != packet.packet_id
                or inner["purpose"] != packet.purpose
                or inner["carrier_commitment"] != packet.carrier_commitment
            ):
                raise StarCustodyError("inner_carrier_join_mismatch")
            carrier = inner["carrier"]
            if not isinstance(carrier, dict) or sha256_hex(
                legacy_canonical_json_bytes(carrier)
            ) != packet.carrier_commitment:
                raise StarCustodyError("inner_carrier_commitment_mismatch")
            master_key = b64url_decode(str(inner["carrier_master_key_b64"]))
            try:
                decoded = decode_hnc_quantum_packet(
                    carrier,
                    master_key,
                    expected_purpose=packet.purpose,
                )
            except HNCPacketError as exc:
                raise StarCustodyError("legacy_carrier_aead_release_failed") from exc
            # Once authenticated plaintext reaches a capability, the handler may
            # have produced effects even if it later raises or returns an invalid
            # result.  Commit one-use custody before dispatch; only failures above
            # this boundary are safe to retry.
            material_consumed = True
            public_result, capability_error = _invoke_capability_safely(
                registered_capability,
                decoded.plaintext,
            )
            if capability_error is not None or public_result is None:
                raise StarCustodyError(
                    capability_error or "capability_execution_failed"
                ) from None
            metadata: dict[str, Any] = {
                "packet_id": packet.packet_id,
                "packet_commitment": packet.packet_commitment,
                "purpose": packet.purpose,
                "carrier_commitment": packet.carrier_commitment,
                "source_signature_commitment": preflight["source_signature_commitment"],
                "capability_result_sha256": domain_hash(
                    "AUREON-PLUMBER-V02-CAPABILITY-RESULT", public_result
                ),
                "capability_id": registered_capability.capability_id,
                "capability_measurement_sha256": registered_capability.measurement_sha256,
                "capability_policy_commitment": registered_capability.policy_measurement_sha256,
                "plaintext_returned": False,
                "carrier_returned": False,
                "shares_returned": False,
                "keys_returned": False,
                "production_ready": False,
            }
            return public_result, metadata
        finally:
            with self._lock:
                current = self._records.get(packet.packet_id)
                if current is record:
                    if material_consumed:
                        self._records.pop(packet.packet_id, None)
                    else:
                        record.claimed = False
            if material_consumed:
                for share in record.shares:
                    share[:] = bytes(len(share))
            if "kek" in locals():
                wipe = bytearray(kek)
                wipe[:] = bytes(len(wipe))
            if "master_key" in locals():
                wipe_key = bytearray(master_key)
                wipe_key[:] = bytes(len(wipe_key))


__all__ = [
    "PROTECTED_PACKET_MAGIC",
    "PROTECTED_PACKET_SCHEMA",
    "LocalDevelopmentStarCustodyV02",
    "ProtectedMagicStarPacketV02",
    "RegisteredCapabilityV02",
    "StarCustodyError",
    "validate_magic_star_hnc_packet_v02",
]
