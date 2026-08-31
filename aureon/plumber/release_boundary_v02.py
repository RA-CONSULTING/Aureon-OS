"""Pinned, fail-closed orchestration for the Magic Star v0.2 local lab.

Every trust root, evidence probe, recipient verifier, and capability policy is
pinned when the boundary is constructed.  The implementation is intentionally
process-local: it is useful for deterministic integration and attack testing,
but it is not an HSM, sandbox, durable replay ledger, or production release
service.
"""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .authorization_chain_v02 import (
    AUTHORIZATION_ROLES,
    AuthorizationChainError,
    AuthorizationChainV02,
    validate_authorization_chain_v02,
)
from .crypto import canonical_json_bytes, domain_hash, ed25519_public_key_hex
from .magic_star_v02 import (
    POINT_ROLES,
    PROFILE_ID,
    PROTOCOL_ID,
    SOURCE_PROFILE_COMMITMENT,
    AuthorityBindingV02,
    MagicStarError,
    MagicStarV02,
    build_candidate_center_v02,
    build_heart_source_identity_commitment_v02,
    component_commitment_v02,
    sign_component_v02,
    validate_magic_star_v02,
    verify_component_v02,
)
from .recipient_proof_v02 import (
    RecipientChallengeV02,
    RecipientEnrollmentV02,
    RecipientProofError,
    RecipientProofV02,
    RecipientProofVerifierV02,
)
from .release_evidence_v02 import (
    ORGAN_ROLES,
    RELEASE_EVIDENCE_ROLES,
    ReleaseEvidenceError,
    ReleaseEvidenceV02,
    validate_release_evidence_v02,
)
from .release_state_v02 import (
    EPAS_STATE_SCHEMA,
    STATE_SCHEMA,
    EPASChainSnapshot,
    InMemoryEPASChainStoreV02,
    InMemoryReleaseStateStoreV02,
    OpaqueEPASReservation,
    ReleasePhase,
    ReleaseStateError,
    ReleaseStateSnapshot,
)
from .schema import freeze_mapping, thaw_json
from .star_custody_v02 import (
    LocalDevelopmentStarCustodyV02,
    ProtectedMagicStarPacketV02,
    StarCustodyError,
    validate_magic_star_hnc_packet_v02,
)

RELEASE_BOUNDARY_SCHEMA = "aureon.plumber.magic-star.release-boundary.v02"
CAPABILITY_POLICY_SCHEMA = "aureon.plumber.magic-star.capability-policy.v02"
CAPABILITY_RECEIPT_SCHEMA = "aureon.plumber.magic-star.capability-receipt.v02"

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_RESULT_KEY = re.compile(
    r"(?:plain(?:text)?|payload|secret|private|master.?key|raw.?key|key.?share|"
    r"share.?bytes|carrier|ciphertext|nonce|lease.?token)",
    re.IGNORECASE,
)
_MAX_LIVE_AGE_MS = 5_000
_MAX_RESULT_BYTES = 64 * 1024
_RECEIPT_PAYLOAD_FIELDS = {
    "schema",
    "protocol_id",
    "profile_id",
    "source_profile_commitment",
    "packet_id",
    "packet_commitment",
    "session_id",
    "purpose",
    "release_context_sha256",
    "recipient_proof_commitment",
    "star_commitment",
    "epas_commitment",
    "live_binding_sha256",
    "runtime_measurement_sha256",
    "policy_measurement_sha256",
    "release_proof_commitment",
    "authorization_chain_commitment",
    "custody_authorization_commitment",
    "capability_id",
    "capability_measurement_sha256",
    "capability_policy_commitment",
    "capability_result_sha256",
    "result_bytes",
    "state_transition",
    "epas_previous_epoch",
    "epas_previous_head_sha256",
    "epas_next_epoch",
    "epas_next_head_sha256",
    "issued_at_ms",
    "plaintext_returned",
    "keys_returned",
    "shares_returned",
    "carrier_returned",
    "production_ready",
}


class ReleaseBoundaryError(ValueError):
    """Stable, non-secret denial from the v0.2 release boundary."""

    def __init__(self, code: str) -> None:
        candidate = str(code)
        self.code = (
            candidate
            if _IDENTIFIER.fullmatch(candidate) is not None
            else "release_boundary_denied"
        )
        super().__init__(self.code)


def _identifier(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ReleaseBoundaryError(code)
    return value


def _sha256(value: object, *, code: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ReleaseBoundaryError(code)
    return value


def _uint(value: object, *, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReleaseBoundaryError(code)
    return value


def _system_now_ms() -> int:
    return time.time_ns() // 1_000_000


def build_release_context_v02(
    *,
    packet_id: str,
    session_id: str,
    purpose: str,
    channel_binding_sha256: str,
    temporal_commitment: str,
    observer_commitment: str,
    live_binding_sha256: str,
    runtime_measurement_sha256: str,
    policy_measurement_sha256: str,
) -> str:
    """Build the non-circular context committed before packet protection."""

    return domain_hash(
        "AUREON-PLUMBER-V02-RELEASE-CONTEXT",
        {
            "protocol_id": PROTOCOL_ID,
            "profile_id": PROFILE_ID,
            "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
            "packet_id": _identifier(packet_id, code="packet_id_invalid"),
            "session_id": _identifier(session_id, code="session_id_invalid"),
            "purpose": _identifier(purpose, code="purpose_invalid"),
            "channel_binding_sha256": _sha256(
                channel_binding_sha256, code="channel_binding_invalid"
            ),
            "temporal_commitment": _sha256(
                temporal_commitment, code="temporal_commitment_invalid"
            ),
            "observer_commitment": _sha256(
                observer_commitment, code="observer_commitment_invalid"
            ),
            "live_binding_sha256": _sha256(
                live_binding_sha256, code="live_binding_invalid"
            ),
            "runtime_measurement_sha256": _sha256(
                runtime_measurement_sha256, code="runtime_measurement_invalid"
            ),
            "policy_measurement_sha256": _sha256(
                policy_measurement_sha256, code="policy_measurement_invalid"
            ),
        },
    )


@dataclass(frozen=True, slots=True)
class LiveBindingEvidenceV02:
    live_binding_sha256: str
    runtime_measurement_sha256: str
    policy_measurement_sha256: str
    observed_at_ms: int
    valid: bool

    def validate(self, *, trusted_now_ms: int, max_age_ms: int) -> None:
        now = _uint(trusted_now_ms, code="trusted_time_invalid")
        observed = _uint(self.observed_at_ms, code="live_observed_at_invalid")
        age_limit = _uint(max_age_ms, code="live_age_policy_invalid")
        if self.valid is not True:
            raise ReleaseBoundaryError("live_binding_not_valid")
        _sha256(self.live_binding_sha256, code="live_binding_invalid")
        _sha256(self.runtime_measurement_sha256, code="runtime_measurement_invalid")
        _sha256(self.policy_measurement_sha256, code="policy_measurement_invalid")
        if observed > now or now - observed > age_limit:
            raise ReleaseBoundaryError("live_binding_stale_or_future")

    def public_dict(self) -> dict[str, Any]:
        return {
            "live_binding_sha256": self.live_binding_sha256,
            "runtime_measurement_sha256": self.runtime_measurement_sha256,
            "policy_measurement_sha256": self.policy_measurement_sha256,
            "observed_at_ms": self.observed_at_ms,
            "valid": self.valid,
        }


@dataclass(frozen=True, slots=True)
class ContinuityStateEvidenceV02:
    previous_decision_head_sha256: str
    revocation_epoch: int
    observed_at_ms: int
    valid: bool

    def validate(self, *, trusted_now_ms: int, max_age_ms: int) -> None:
        now = _uint(trusted_now_ms, code="trusted_time_invalid")
        observed = _uint(self.observed_at_ms, code="continuity_observed_at_invalid")
        _sha256(self.previous_decision_head_sha256, code="continuity_head_invalid")
        _uint(self.revocation_epoch, code="revocation_epoch_invalid")
        if self.valid is not True or observed > now or now - observed > max_age_ms:
            raise ReleaseBoundaryError("continuity_state_stale_or_invalid")


@dataclass(frozen=True, slots=True)
class EvidenceExpectationsV02:
    organ_evidence_sha256_by_role: Mapping[str, str]
    star_point_evidence_sha256_by_role: Mapping[str, str]
    epas_source_lineage_sha256: str
    epas_evidence_sha256: str
    epas_evidence_class: str

    def __post_init__(self) -> None:
        organ_evidence = freeze_mapping(
            self.organ_evidence_sha256_by_role,
            field="organ_evidence_sha256_by_role",
        )
        star_point_evidence = freeze_mapping(
            self.star_point_evidence_sha256_by_role,
            field="star_point_evidence_sha256_by_role",
        )
        object.__setattr__(
            self,
            "organ_evidence_sha256_by_role",
            organ_evidence,
        )
        object.__setattr__(
            self,
            "star_point_evidence_sha256_by_role",
            star_point_evidence,
        )
        self.validate()

    def validate(self) -> None:
        if set(self.organ_evidence_sha256_by_role) != set(ORGAN_ROLES):
            raise ReleaseBoundaryError("expected_organ_evidence_set_invalid")
        if set(self.star_point_evidence_sha256_by_role) != set(POINT_ROLES):
            raise ReleaseBoundaryError("expected_star_evidence_set_invalid")
        for value in self.organ_evidence_sha256_by_role.values():
            _sha256(value, code="expected_organ_evidence_invalid")
        for value in self.star_point_evidence_sha256_by_role.values():
            _sha256(value, code="expected_star_evidence_invalid")
        _sha256(self.epas_source_lineage_sha256, code="epas_source_lineage_invalid")
        _sha256(self.epas_evidence_sha256, code="epas_evidence_invalid")
        _identifier(self.epas_evidence_class, code="epas_evidence_class_invalid")


def _walk_result_keys(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or _FORBIDDEN_RESULT_KEY.search(key):
                raise ReleaseBoundaryError("capability_result_forbidden_field")
            _walk_result_keys(item)
    elif isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        for item in value:
            _walk_result_keys(item)


@dataclass(frozen=True, slots=True)
class CapabilityPolicyV02:
    capability_id: str
    capability_measurement_sha256: str
    allowed_output_keys: tuple[str, ...]
    required_output_keys: tuple[str, ...] = ()
    max_result_bytes: int = 16 * 1024

    def __post_init__(self) -> None:
        if not isinstance(self.allowed_output_keys, list | tuple):
            raise ReleaseBoundaryError("capability_allowed_output_invalid")
        if not isinstance(self.required_output_keys, list | tuple):
            raise ReleaseBoundaryError("capability_required_output_invalid")
        object.__setattr__(self, "allowed_output_keys", tuple(self.allowed_output_keys))
        object.__setattr__(self, "required_output_keys", tuple(self.required_output_keys))
        _identifier(self.capability_id, code="capability_id_invalid")
        _sha256(
            self.capability_measurement_sha256,
            code="capability_measurement_invalid",
        )
        if not self.allowed_output_keys or len(set(self.allowed_output_keys)) != len(
            self.allowed_output_keys
        ):
            raise ReleaseBoundaryError("capability_allowed_output_invalid")
        if len(set(self.required_output_keys)) != len(
            self.required_output_keys
        ) or not set(self.required_output_keys).issubset(self.allowed_output_keys):
            raise ReleaseBoundaryError("capability_required_output_invalid")
        for key in (*self.allowed_output_keys, *self.required_output_keys):
            _identifier(key, code="capability_output_key_invalid")
            if _FORBIDDEN_RESULT_KEY.search(key):
                raise ReleaseBoundaryError("capability_output_key_forbidden")
        maximum = _uint(self.max_result_bytes, code="capability_result_limit_invalid")
        if maximum == 0 or maximum > _MAX_RESULT_BYTES:
            raise ReleaseBoundaryError("capability_result_limit_invalid")

    @property
    def commitment(self) -> str:
        return domain_hash(
            "AUREON-PLUMBER-V02-CAPABILITY-POLICY",
            {
                "schema": CAPABILITY_POLICY_SCHEMA,
                "capability_id": self.capability_id,
                "capability_measurement_sha256": self.capability_measurement_sha256,
                "allowed_output_keys": list(self.allowed_output_keys),
                "required_output_keys": list(self.required_output_keys),
                "max_result_bytes": self.max_result_bytes,
            },
        )

    def validate_result(self, result: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
        if not isinstance(result, Mapping):
            raise ReleaseBoundaryError("capability_result_must_be_mapping")
        public_result = dict(result)
        keys = set(public_result)
        if not keys.issubset(self.allowed_output_keys) or not set(
            self.required_output_keys
        ).issubset(keys):
            raise ReleaseBoundaryError("capability_result_schema_denied")
        _walk_result_keys(public_result)
        try:
            encoded = canonical_json_bytes(public_result)
        except (TypeError, ValueError) as exc:
            raise ReleaseBoundaryError("capability_result_not_canonical") from exc
        if len(encoded) > self.max_result_bytes:
            raise ReleaseBoundaryError("capability_result_too_large")
        return public_result, domain_hash(
            "AUREON-PLUMBER-V02-CAPABILITY-RESULT", public_result
        )


@dataclass(frozen=True, slots=True)
class CapabilityReleaseResultV02:
    result: Mapping[str, Any]
    receipt: Mapping[str, Any]
    release_state: ReleaseStateSnapshot
    epas_state: EPASChainSnapshot

    def __post_init__(self) -> None:
        object.__setattr__(self, "result", freeze_mapping(self.result, field="result"))
        object.__setattr__(self, "receipt", freeze_mapping(self.receipt, field="receipt"))

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema": RELEASE_BOUNDARY_SCHEMA,
            "result": thaw_json(self.result),
            "receipt": thaw_json(self.receipt),
            "release_state": self.release_state.public_dict(),
            "epas_state": self.epas_state.public_dict(),
            "production_ready": False,
        }


def _validate_trust_constellation(
    *,
    star_trust: Mapping[str, AuthorityBindingV02],
    evidence_trust: Mapping[str, AuthorityBindingV02],
    authorization_trust: Mapping[str, AuthorityBindingV02],
    receipt_authority: AuthorityBindingV02,
    enrollment: RecipientEnrollmentV02 | None = None,
) -> None:
    combined: dict[str, AuthorityBindingV02] = {}
    required_sets = (
        (star_trust, set(POINT_ROLES) | {"EPAS", "HEART", "STAR_SEAL"}),
        (evidence_trust, set(RELEASE_EVIDENCE_ROLES)),
        (authorization_trust, set(AUTHORIZATION_ROLES)),
    )
    for trust, required in required_sets:
        if set(trust) != required:
            raise ReleaseBoundaryError("trust_constellation_role_set_invalid")
        for role, binding in trust.items():
            if not isinstance(binding, AuthorityBindingV02) or binding.role != role:
                raise ReleaseBoundaryError("trust_constellation_binding_invalid")
            existing = combined.get(role)
            if existing is not None and existing != binding:
                raise ReleaseBoundaryError("shared_authority_binding_mismatch")
            combined[role] = binding
    if receipt_authority.role != "CAPABILITY_RECEIPT":
        raise ReleaseBoundaryError("capability_receipt_authority_invalid")
    combined["CAPABILITY_RECEIPT"] = receipt_authority
    bindings = list(combined.values())
    for attribute, code in (
        ("public_key_hex", "constellation_keys_not_distinct"),
        ("key_id", "constellation_key_ids_not_distinct"),
        ("principal", "constellation_principals_not_distinct"),
        ("issuer", "constellation_issuers_not_distinct"),
    ):
        values = [getattr(binding, attribute) for binding in bindings]
        if len(values) != len(set(values)):
            raise ReleaseBoundaryError(code)
    if enrollment is not None and (
        enrollment.public_key_hex in {item.public_key_hex for item in bindings}
        or enrollment.key_id in {item.key_id for item in bindings}
        or enrollment.principal in {item.principal for item in bindings}
    ):
        raise ReleaseBoundaryError("recipient_authority_not_distinct")


def _require_exact_join(summary: Mapping[str, Any], expected: Mapping[str, Any]) -> None:
    for key, value in expected.items():
        if summary.get(key) != value:
            raise ReleaseBoundaryError(f"release_join_mismatch_{key}")


def _predicted_epas_head(
    *,
    previous: EPASChainSnapshot,
    terminal_star_sha256: str,
    session_id: str,
    authorization_sha256: str,
    outcome: str,
) -> str:
    return domain_hash(
        "AUREON-PLUMBER-V02-EPAS-MEMORY",
        {
            "previous_epoch": previous.epoch,
            "previous_head_sha256": previous.head_sha256,
            "terminal_star_sha256": terminal_star_sha256,
            "session_id": session_id,
            "authorization_sha256": authorization_sha256,
            "outcome": outcome,
            "next_epoch": previous.epoch + 1,
        },
    )


def validate_capability_release_result_v02(
    result: CapabilityReleaseResultV02,
    *,
    receipt_authority: AuthorityBindingV02,
    expected_join: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate signed result-object consistency without a durable provider query."""

    if not isinstance(result, CapabilityReleaseResultV02):
        raise ReleaseBoundaryError("capability_release_result_type_invalid")
    if (
        result.release_state.schema != STATE_SCHEMA
        or result.release_state.phase is not ReleasePhase.CONSUMED
        or result.release_state.terminal_reason is not None
        or result.epas_state.schema != EPAS_STATE_SCHEMA
    ):
        raise ReleaseBoundaryError("capability_release_state_not_consumed")
    try:
        payload = verify_component_v02(
            result.receipt,
            expected_type="CAPABILITY_RELEASE_RECEIPT",
            expected_authority=receipt_authority,
        )
    except MagicStarError as exc:
        raise ReleaseBoundaryError(exc.code) from exc
    if set(payload) != _RECEIPT_PAYLOAD_FIELDS:
        raise ReleaseBoundaryError("capability_receipt_shape_invalid")
    fixed = {
        "schema": CAPABILITY_RECEIPT_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "profile_id": PROFILE_ID,
        "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
        "state_transition": "CUSTODY_TO_CONSUMED",
        "plaintext_returned": False,
        "keys_returned": False,
        "shares_returned": False,
        "carrier_returned": False,
        "production_ready": False,
    }
    if any(payload.get(key) != value for key, value in fixed.items()):
        raise ReleaseBoundaryError("capability_receipt_contract_invalid")
    for key in (
        "packet_commitment",
        "release_context_sha256",
        "recipient_proof_commitment",
        "star_commitment",
        "epas_commitment",
        "live_binding_sha256",
        "runtime_measurement_sha256",
        "policy_measurement_sha256",
        "release_proof_commitment",
        "authorization_chain_commitment",
        "custody_authorization_commitment",
        "capability_measurement_sha256",
        "capability_policy_commitment",
        "capability_result_sha256",
        "epas_previous_head_sha256",
        "epas_next_head_sha256",
    ):
        _sha256(payload.get(key), code=f"capability_receipt_{key}_invalid")
    for key in ("packet_id", "session_id", "purpose", "capability_id"):
        _identifier(payload.get(key), code=f"capability_receipt_{key}_invalid")
    for key in (
        "result_bytes",
        "epas_previous_epoch",
        "epas_next_epoch",
        "issued_at_ms",
    ):
        _uint(payload.get(key), code=f"capability_receipt_{key}_invalid")
    _identifier(result.release_state.session_id, code="release_state_session_id_invalid")
    _identifier(result.release_state.packet_id, code="release_state_packet_id_invalid")
    _identifier(result.release_state.purpose, code="release_state_purpose_invalid")
    _sha256(
        result.release_state.live_binding_sha256,
        code="release_state_live_binding_invalid",
    )
    _uint(result.release_state.expires_at_ms, code="release_state_expiry_invalid")
    _uint(result.release_state.version, code="release_state_version_invalid")
    epas_epoch = _uint(result.epas_state.epoch, code="epas_state_epoch_invalid")
    epas_head = _sha256(result.epas_state.head_sha256, code="epas_state_head_invalid")
    previous_epoch = _uint(
        payload["epas_previous_epoch"], code="capability_receipt_epas_previous_epoch_invalid"
    )
    next_epoch = _uint(
        payload["epas_next_epoch"], code="capability_receipt_epas_next_epoch_invalid"
    )
    previous_head = _sha256(
        payload["epas_previous_head_sha256"],
        code="capability_receipt_epas_previous_head_invalid",
    )
    expected_epas_head = _predicted_epas_head(
        previous=EPASChainSnapshot(
            schema=EPAS_STATE_SCHEMA,
            epoch=previous_epoch,
            head_sha256=previous_head,
        ),
        terminal_star_sha256=payload["star_commitment"],
        session_id=payload["session_id"],
        authorization_sha256=payload["authorization_chain_commitment"],
        outcome="CONSUMED",
    )
    result_hash = domain_hash(
        "AUREON-PLUMBER-V02-CAPABILITY-RESULT", dict(result.result)
    )
    if (
        payload.get("capability_result_sha256") != result_hash
        or payload.get("result_bytes") != len(canonical_json_bytes(result.result))
        or payload.get("session_id") != result.release_state.session_id
        or payload.get("packet_id") != result.release_state.packet_id
        or payload.get("purpose") != result.release_state.purpose
        or payload.get("live_binding_sha256")
        != result.release_state.live_binding_sha256
        or next_epoch != previous_epoch + 1
        or epas_epoch != next_epoch
        or epas_head != expected_epas_head
        or payload.get("epas_next_head_sha256") != expected_epas_head
    ):
        raise ReleaseBoundaryError("capability_result_readback_mismatch")
    if expected_join is not None:
        _require_exact_join(payload, expected_join)
    return {
        "valid": True,
        "session_id": payload["session_id"],
        "packet_commitment": payload["packet_commitment"],
        "capability_id": payload["capability_id"],
        "capability_result_sha256": result_hash,
        "epas_next_head_sha256": result.epas_state.head_sha256,
        "production_ready": False,
    }


class LocalDevelopmentReleaseBoundaryV02:
    """Laboratory same-process release coordinator with pinned local trust."""

    production_ready = False

    def __init__(
        self,
        *,
        allow_insecure_same_process: bool,
        state_store: InMemoryReleaseStateStoreV02,
        epas_store: InMemoryEPASChainStoreV02,
        custody: LocalDevelopmentStarCustodyV02,
        recipient_verifier: RecipientProofVerifierV02,
        star_trust: Mapping[str, AuthorityBindingV02],
        release_evidence_trust: Mapping[str, AuthorityBindingV02],
        authorization_trust: Mapping[str, AuthorityBindingV02],
        receipt_authority: AuthorityBindingV02,
        receipt_private_key: Ed25519PrivateKey,
        capability_policies: Mapping[str, CapabilityPolicyV02],
        live_binding_probe: Callable[[], LiveBindingEvidenceV02],
        continuity_state_probe: Callable[[str, str], ContinuityStateEvidenceV02],
        evidence_expectations_probe: Callable[[str, str], EvidenceExpectationsV02],
        trusted_now_ms: Callable[[], int] = _system_now_ms,
        max_live_age_ms: int = _MAX_LIVE_AGE_MS,
    ) -> None:
        if allow_insecure_same_process is not True:
            raise ReleaseBoundaryError("explicit_insecure_same_process_opt_in_required")
        if not isinstance(state_store, InMemoryReleaseStateStoreV02):
            raise ReleaseBoundaryError("release_state_store_invalid")
        if not isinstance(epas_store, InMemoryEPASChainStoreV02):
            raise ReleaseBoundaryError("epas_state_store_invalid")
        if not isinstance(custody, LocalDevelopmentStarCustodyV02):
            raise ReleaseBoundaryError("star_custody_invalid")
        if not isinstance(recipient_verifier, RecipientProofVerifierV02):
            raise ReleaseBoundaryError("recipient_verifier_invalid")
        _validate_trust_constellation(
            star_trust=star_trust,
            evidence_trust=release_evidence_trust,
            authorization_trust=authorization_trust,
            receipt_authority=receipt_authority,
        )
        if ed25519_public_key_hex(receipt_private_key) != receipt_authority.public_key_hex:
            raise ReleaseBoundaryError("capability_receipt_signer_key_mismatch")
        if not capability_policies:
            raise ReleaseBoundaryError("capability_policy_registry_invalid")
        policies: dict[str, CapabilityPolicyV02] = {}
        for capability_id, policy in capability_policies.items():
            if (
                not isinstance(policy, CapabilityPolicyV02)
                or capability_id != policy.capability_id
                or capability_id in policies
                or custody.capability_measurement(capability_id)
                != policy.capability_measurement_sha256
                or custody.capability_policy_measurement(capability_id)
                != policy.commitment
            ):
                raise ReleaseBoundaryError("capability_policy_registry_invalid")
            policies[capability_id] = policy
        if not all(
            callable(probe)
            for probe in (
                live_binding_probe,
                continuity_state_probe,
                evidence_expectations_probe,
                trusted_now_ms,
            )
        ):
            raise ReleaseBoundaryError("release_runtime_probe_invalid")
        maximum_age = _uint(max_live_age_ms, code="live_age_policy_invalid")
        if maximum_age == 0 or maximum_age > 60_000:
            raise ReleaseBoundaryError("live_age_policy_invalid")
        self._state_store = state_store
        self._epas_store = epas_store
        self._custody = custody
        self._recipient_verifier = recipient_verifier
        self._star_trust = dict(star_trust)
        self._release_evidence_trust = dict(release_evidence_trust)
        self._authorization_trust = dict(authorization_trust)
        self._receipt_authority = receipt_authority
        self._receipt_private_key = receipt_private_key
        self._capability_policies = policies
        self._live_binding_probe = live_binding_probe
        self._continuity_state_probe = continuity_state_probe
        self._evidence_expectations_probe = evidence_expectations_probe
        self._trusted_now_ms = trusted_now_ms
        self._max_live_age_ms = maximum_age
        self._lock = threading.RLock()

    def release(
        self,
        packet: ProtectedMagicStarPacketV02,
        *,
        session_id: str,
        challenge: RecipientChallengeV02,
        recipient_proof: RecipientProofV02,
        temporal_commitment: str,
        observer_commitment: str,
        expected_channel_binding_sha256: str,
        expected_live_binding_sha256: str,
        expected_runtime_measurement_sha256: str,
        star: MagicStarV02,
        release_evidence: ReleaseEvidenceV02,
        authorization_chain: AuthorizationChainV02,
        capability_id: str,
    ) -> CapabilityReleaseResultV02:
        """Validate all joins, execute one registered capability, and consume."""

        created = False
        consumed = False
        epas_advanced = False
        epas_reservation: OpaqueEPASReservation | None = None
        original_epas: EPASChainSnapshot | None = None
        authorization_commitment = "0" * 64
        denial_code = "release_boundary_denied"
        session = _identifier(session_id, code="session_id_invalid")
        with self._lock:
            try:
                selected_id = _identifier(capability_id, code="capability_id_invalid")
                capability_policy = self._capability_policies.get(selected_id)
                if capability_policy is None:
                    raise ReleaseBoundaryError("capability_not_authorized")
                enrollment = self._recipient_verifier.enrollment_for(
                    recipient_proof.recipient_id
                )
                _validate_trust_constellation(
                    star_trust=self._star_trust,
                    evidence_trust=self._release_evidence_trust,
                    authorization_trust=self._authorization_trust,
                    receipt_authority=self._receipt_authority,
                    enrollment=enrollment,
                )
                packet_preflight = validate_magic_star_hnc_packet_v02(
                    packet,
                    source_authority=self._star_trust["SOURCE"],
                )
                heart_source_identity = build_heart_source_identity_commitment_v02(
                    source_authority=self._star_trust["SOURCE"],
                    packet_id=packet.packet_id,
                    packet_commitment=packet.packet_commitment,
                    source_signature_commitment=packet_preflight[
                        "source_signature_commitment"
                    ],
                )
                channel = _sha256(
                    expected_channel_binding_sha256, code="channel_binding_invalid"
                )
                live = _sha256(expected_live_binding_sha256, code="live_binding_invalid")
                runtime = _sha256(
                    expected_runtime_measurement_sha256,
                    code="runtime_measurement_invalid",
                )
                temporal = _sha256(
                    temporal_commitment, code="temporal_commitment_invalid"
                )
                observer = _sha256(
                    observer_commitment, code="observer_commitment_invalid"
                )
                policy = capability_policy.commitment
                expected_context = build_release_context_v02(
                    packet_id=packet.packet_id,
                    session_id=session,
                    purpose=packet.purpose,
                    channel_binding_sha256=channel,
                    temporal_commitment=temporal,
                    observer_commitment=observer,
                    live_binding_sha256=live,
                    runtime_measurement_sha256=runtime,
                    policy_measurement_sha256=policy,
                )
                if packet.release_context_sha256 != expected_context:
                    raise ReleaseBoundaryError("protected_packet_release_context_mismatch")
                self._recipient_verifier.verify_and_consume(
                    recipient_proof,
                    challenge,
                    expected_packet_commitment=packet.packet_commitment,
                    expected_purpose=packet.purpose,
                    expected_channel_binding_sha256=channel,
                )
                expectations = self._evidence_expectations_probe(
                    packet.packet_id, session
                )
                if not isinstance(expectations, EvidenceExpectationsV02):
                    raise ReleaseBoundaryError("evidence_expectations_probe_invalid")
                expectations.validate()

                epas_commitment = component_commitment_v02(star.epas_precondition)
                heart_commitment = component_commitment_v02(star.heart_precondition)
                candidate_center = build_candidate_center_v02(
                    release_context_sha256=expected_context,
                    packet_commitment=packet.packet_commitment,
                    recipient_proof_commitment=recipient_proof.commitment,
                    purpose=packet.purpose,
                    temporal_commitment=temporal,
                    observer_commitment=observer,
                    epas_commitment=epas_commitment,
                    heart_commitment=heart_commitment,
                )
                star_summary = validate_magic_star_v02(
                    star,
                    trust=self._star_trust,
                    expected_release_context_sha256=expected_context,
                    expected_candidate_center_sha256=candidate_center,
                    trusted_now_ms=self._trusted_now_ms,
                )
                original_epas = self._epas_store.snapshot()
                epas_payload = verify_component_v02(
                    star.epas_precondition,
                    expected_type="EPAS_PRECONDITION",
                    expected_authority=self._star_trust["EPAS"],
                )
                _require_exact_join(
                    epas_payload,
                    {
                        "release_context_sha256": expected_context,
                        "source_lineage_sha256": expectations.epas_source_lineage_sha256,
                        "evidence_sha256": expectations.epas_evidence_sha256,
                        "evidence_class": expectations.epas_evidence_class,
                        "previous_memory_head_sha256": original_epas.head_sha256,
                        "memory_epoch": original_epas.epoch,
                        "verdict": "CLEAR",
                        "outcome": "PROCEED",
                        "physical_effects_claimed": False,
                    },
                )
                heart_payload = verify_component_v02(
                    star.heart_precondition,
                    expected_type="HEART_PRECONDITION",
                    expected_authority=self._star_trust["HEART"],
                )
                _require_exact_join(
                    heart_payload,
                    {
                        "release_context_sha256": expected_context,
                        "packet_id": packet.packet_id,
                        "packet_commitment": packet.packet_commitment,
                        "session_id": session,
                        "purpose": packet.purpose,
                        "source_identity_commitment": heart_source_identity,
                        "temporal_commitment": temporal,
                        "observer_commitment": observer,
                        "policy_commitment": policy,
                        "runtime_measurement_sha256": runtime,
                        "verdict": "APPROVE",
                        "heart_frequency": "528",
                    },
                )
                star_share_bindings: list[str] = []
                for role, component in zip(POINT_ROLES, star.points, strict=True):
                    point_payload = verify_component_v02(
                        component,
                        expected_type="MAGIC_STAR_POINT",
                        expected_authority=self._star_trust[role],
                    )
                    if point_payload.get("evidence_sha256") != expectations.star_point_evidence_sha256_by_role[
                        role
                    ]:
                        raise ReleaseBoundaryError("star_point_evidence_substitution_detected")
                    star_share_bindings.append(
                        _sha256(
                            point_payload.get("share_binding_sha256"),
                            code="star_share_binding_invalid",
                        )
                    )
                packet_share_bindings = [
                    item["binding_sha256"] for item in packet.share_bindings
                ]
                if star_share_bindings != packet_share_bindings:
                    raise ReleaseBoundaryError("five_share_binding_join_mismatch")

                evidence_summary = validate_release_evidence_v02(
                    release_evidence,
                    trust=self._release_evidence_trust,
                    expected_evidence_sha256_by_role=expectations.organ_evidence_sha256_by_role,
                    trusted_now_ms=self._trusted_now_ms,
                )
                shared = {
                    "packet_commitment": packet.packet_commitment,
                    "session_id": session,
                    "purpose": packet.purpose,
                    "release_context_sha256": expected_context,
                    "recipient_proof_commitment": recipient_proof.commitment,
                    "star_commitment": star.commitment,
                    "epas_commitment": epas_commitment,
                    "live_binding_sha256": live,
                    "runtime_measurement_sha256": runtime,
                    "policy_measurement_sha256": policy,
                }
                _require_exact_join(evidence_summary, shared)
                continuity = self._continuity_state_probe(packet.packet_id, session)
                if not isinstance(continuity, ContinuityStateEvidenceV02):
                    raise ReleaseBoundaryError("continuity_state_probe_invalid")
                continuity.validate(
                    trusted_now_ms=_uint(
                        self._trusted_now_ms(), code="trusted_time_invalid"
                    ),
                    max_age_ms=self._max_live_age_ms,
                )
                authorization_expected = {
                    **shared,
                    "release_proof_commitment": evidence_summary[
                        "release_proof_commitment"
                    ],
                }
                authorization_summary = validate_authorization_chain_v02(
                    authorization_chain,
                    trust=self._authorization_trust,
                    expected_previous_decision_head_sha256=continuity.previous_decision_head_sha256,
                    expected_revocation_epoch=continuity.revocation_epoch,
                    expected_join=authorization_expected,
                    trusted_now_ms=self._trusted_now_ms,
                )
                if authorization_summary.get("share_bindings") != packet_share_bindings:
                    raise ReleaseBoundaryError("five_share_binding_join_mismatch")
                authorization_commitment = authorization_chain.commitment
                expiry = min(
                    challenge.expires_at_ms,
                    _uint(star_summary["expires_at_ms"], code="star_expiry_invalid"),
                    _uint(
                        evidence_summary["expires_at_ms"],
                        code="release_evidence_expiry_invalid",
                    ),
                    _uint(
                        authorization_summary["expires_at_ms"],
                        code="authorization_expiry_invalid",
                    ),
                )
                self._state_store.create(
                    session_id=session,
                    packet_id=packet.packet_id,
                    purpose=packet.purpose,
                    live_binding_sha256=live,
                    expires_at_ms=expiry,
                )
                created = True
                epas_reservation = self._epas_store.reserve(
                    expected_epoch=original_epas.epoch,
                    expected_head_sha256=original_epas.head_sha256,
                )

                sampled = self._live_binding_probe()
                if not isinstance(sampled, LiveBindingEvidenceV02):
                    raise ReleaseBoundaryError("live_binding_probe_type_invalid")
                sampled.validate(
                    trusted_now_ms=_uint(
                        self._trusted_now_ms(), code="trusted_time_invalid"
                    ),
                    max_age_ms=self._max_live_age_ms,
                )
                _require_exact_join(
                    sampled.public_dict(),
                    {
                        "live_binding_sha256": live,
                        "runtime_measurement_sha256": runtime,
                        "policy_measurement_sha256": policy,
                        "valid": True,
                    },
                )
                latest_continuity = self._continuity_state_probe(
                    packet.packet_id, session
                )
                if not isinstance(latest_continuity, ContinuityStateEvidenceV02):
                    raise ReleaseBoundaryError("continuity_state_probe_invalid")
                latest_continuity.validate(
                    trusted_now_ms=_uint(
                        self._trusted_now_ms(), code="trusted_time_invalid"
                    ),
                    max_age_ms=self._max_live_age_ms,
                )
                if (
                    latest_continuity.previous_decision_head_sha256
                    != continuity.previous_decision_head_sha256
                    or latest_continuity.revocation_epoch
                    != continuity.revocation_epoch
                    or latest_continuity.valid is not True
                ):
                    raise ReleaseBoundaryError("continuity_state_changed_at_boundary")
                now = _uint(self._trusted_now_ms(), code="trusted_time_invalid")
                if now >= expiry:
                    raise ReleaseBoundaryError("release_session_expired_before_custody")
                # Revalidate every expiring signed component at the last boundary.
                validate_magic_star_v02(
                    star,
                    trust=self._star_trust,
                    expected_release_context_sha256=expected_context,
                    expected_candidate_center_sha256=candidate_center,
                    trusted_now_ms=self._trusted_now_ms,
                )
                validate_release_evidence_v02(
                    release_evidence,
                    trust=self._release_evidence_trust,
                    expected_evidence_sha256_by_role=expectations.organ_evidence_sha256_by_role,
                    trusted_now_ms=self._trusted_now_ms,
                )
                validate_authorization_chain_v02(
                    authorization_chain,
                    trust=self._authorization_trust,
                    expected_previous_decision_head_sha256=continuity.previous_decision_head_sha256,
                    expected_revocation_epoch=continuity.revocation_epoch,
                    expected_join=authorization_expected,
                    trusted_now_ms=self._trusted_now_ms,
                )
                self._state_store.reserve(
                    session_id=session,
                    expected_live_binding_sha256=sampled.live_binding_sha256,
                )
                lease = self._state_store.claim_custody(session_id=session)
                raw_result, custody_metadata = self._custody.release_to_capability(
                    packet,
                    lease=lease,
                    authorization_chain=authorization_chain,
                    capability_id=selected_id,
                )
                result, result_sha256 = capability_policy.validate_result(raw_result)
                _require_exact_join(
                    custody_metadata,
                    {
                        "capability_result_sha256": result_sha256,
                        "capability_id": selected_id,
                        "capability_measurement_sha256": capability_policy.capability_measurement_sha256,
                        "capability_policy_commitment": capability_policy.commitment,
                    },
                )
                receipt_issued_at_ms = _uint(
                    self._trusted_now_ms(), code="trusted_time_invalid"
                )
                if receipt_issued_at_ms >= expiry:
                    raise ReleaseBoundaryError("release_session_expired_during_capability")

                predicted_head = _predicted_epas_head(
                    previous=original_epas,
                    terminal_star_sha256=star.commitment,
                    session_id=session,
                    authorization_sha256=authorization_commitment,
                    outcome="CONSUMED",
                )
                receipt_payload: dict[str, Any] = {
                    "schema": CAPABILITY_RECEIPT_SCHEMA,
                    "protocol_id": PROTOCOL_ID,
                    "profile_id": PROFILE_ID,
                    "source_profile_commitment": SOURCE_PROFILE_COMMITMENT,
                    "packet_id": packet.packet_id,
                    **shared,
                    "release_proof_commitment": evidence_summary[
                        "release_proof_commitment"
                    ],
                    "authorization_chain_commitment": authorization_commitment,
                    "custody_authorization_commitment": authorization_summary[
                        "custody_authorization_commitment"
                    ],
                    "capability_id": selected_id,
                    "capability_measurement_sha256": capability_policy.capability_measurement_sha256,
                    "capability_policy_commitment": capability_policy.commitment,
                    "capability_result_sha256": result_sha256,
                    "result_bytes": len(canonical_json_bytes(result)),
                    "state_transition": "CUSTODY_TO_CONSUMED",
                    "epas_previous_epoch": original_epas.epoch,
                    "epas_previous_head_sha256": original_epas.head_sha256,
                    "epas_next_epoch": original_epas.epoch + 1,
                    "epas_next_head_sha256": predicted_head,
                    "issued_at_ms": receipt_issued_at_ms,
                    "plaintext_returned": False,
                    "keys_returned": False,
                    "shares_returned": False,
                    "carrier_returned": False,
                    "production_ready": False,
                }
                receipt = sign_component_v02(
                    component_type="CAPABILITY_RELEASE_RECEIPT",
                    authority=self._receipt_authority,
                    payload=receipt_payload,
                    private_key=self._receipt_private_key,
                )
                try:
                    verified_receipt_payload = verify_component_v02(
                        receipt,
                        expected_type="CAPABILITY_RELEASE_RECEIPT",
                        expected_authority=self._receipt_authority,
                    )
                except MagicStarError as exc:
                    raise ReleaseBoundaryError(exc.code) from exc
                if (
                    set(verified_receipt_payload) != _RECEIPT_PAYLOAD_FIELDS
                    or verified_receipt_payload != receipt_payload
                ):
                    raise ReleaseBoundaryError("capability_receipt_precommit_mismatch")
                state_snapshot = self._state_store.consume(lease)
                consumed = True
                if state_snapshot.phase is not ReleasePhase.CONSUMED:
                    raise ReleaseBoundaryError("release_state_not_consumed")
                epas_snapshot = self._epas_store.finalize(
                    epas_reservation,
                    terminal_star_sha256=star.commitment,
                    session_id=session,
                    authorization_sha256=authorization_commitment,
                    outcome="CONSUMED",
                )
                epas_advanced = True
                if epas_snapshot.head_sha256 != predicted_head:
                    raise ReleaseBoundaryError("epas_terminal_readback_mismatch")
                release_result = CapabilityReleaseResultV02(
                    result=result,
                    receipt=receipt,
                    release_state=state_snapshot,
                    epas_state=epas_snapshot,
                )
                validate_capability_release_result_v02(
                    release_result,
                    receipt_authority=self._receipt_authority,
                    expected_join={
                        "packet_commitment": packet.packet_commitment,
                        "session_id": session,
                        "capability_id": selected_id,
                    },
                )
                return release_result
            except Exception as exc:
                code = str(getattr(exc, "code", "release_boundary_denied"))
                if created and not consumed:
                    try:
                        self._state_store.deny(session_id=session, reason=code)
                    except Exception:
                        pass
                if (
                    epas_reservation is not None
                    and not epas_advanced
                    and original_epas is not None
                ):
                    try:
                        self._epas_store.finalize(
                            epas_reservation,
                            terminal_star_sha256=star.commitment,
                            session_id=session,
                            authorization_sha256=authorization_commitment,
                            outcome="DENIED",
                        )
                    except Exception:
                        pass
                if isinstance(exc, ReleaseBoundaryError):
                    denial_code = exc.code
                elif isinstance(
                    exc,
                    (
                        AuthorizationChainError,
                        MagicStarError,
                        RecipientProofError,
                        ReleaseEvidenceError,
                        ReleaseStateError,
                        StarCustodyError,
                    ),
                ):
                    denial_code = code
        raise ReleaseBoundaryError(denial_code) from None


# Long-form compatibility name retained for callers that include the protocol
# family in the local laboratory boundary type.  Both names identify the same
# explicitly insecure, same-process implementation.
LocalDevelopmentMagicStarReleaseBoundaryV02 = LocalDevelopmentReleaseBoundaryV02


__all__ = [
    "CAPABILITY_POLICY_SCHEMA",
    "CAPABILITY_RECEIPT_SCHEMA",
    "RELEASE_BOUNDARY_SCHEMA",
    "CapabilityPolicyV02",
    "CapabilityReleaseResultV02",
    "ContinuityStateEvidenceV02",
    "EvidenceExpectationsV02",
    "LiveBindingEvidenceV02",
    "LocalDevelopmentMagicStarReleaseBoundaryV02",
    "LocalDevelopmentReleaseBoundaryV02",
    "ReleaseBoundaryError",
    "build_release_context_v02",
    "validate_capability_release_result_v02",
]
