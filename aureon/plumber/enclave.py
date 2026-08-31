"""Explicitly insecure, local-development-only Plumber execution boundary.

This is not a secure enclave and must never be represented as one.  It exists
only to exercise purpose binding and fail-closed orchestration on a developer
machine.  Decrypted bytes are passed to one in-process callback, overwritten
afterward where Python permits, and are never returned by this module.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from .crypto import domain_hash
from .packet import PacketContractError, bind_hnc_packet
from .schema import (
    DenialCode,
    SchemaError,
    format_timestamp,
    freeze_mapping,
    require_aware_datetime,
    require_nonblank,
    require_sha256,
)

LOCAL_DEVELOPMENT_MODE = "local-development"
INSECURE_OPT_IN_ACK = "I_ACKNOWLEDGE_INSECURE_LOCAL_DEVELOPMENT_ONLY"
_SAFE_CODE_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")


class EnclaveConfigurationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class EnclaveDisposition(StrEnum):
    COMPLETED_LOCAL = "completed_local"
    HOLD = "hold"
    DENY = "deny"


class EnclaveCode(StrEnum):
    PURPOSE_NOT_ALLOWED = "purpose_not_allowed"
    HNC_PACKET_INVALID = "hnc_packet_invalid"
    HNC_DECODE_DENIED = "hnc_decode_denied"
    PROCESSOR_FAILED = "processor_failed"
    PROCESSOR_RESULT_INVALID = "processor_result_invalid"


@dataclass(frozen=True, slots=True)
class LocalComputationResult:
    """The only callback result accepted across the local enclave boundary."""

    outcome_code: str
    result_commitment: str
    evidence_commitments: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.outcome_code, str) or _SAFE_CODE_RE.fullmatch(self.outcome_code) is None:
            raise SchemaError(DenialCode.INVALID_VALUE, field="outcome_code")
        require_sha256(self.result_commitment, field="result_commitment")
        frozen = freeze_mapping(
            self.evidence_commitments,
            field="evidence_commitments",
            nonempty=False,
        )
        for name, commitment in frozen.items():
            require_nonblank(name, field="evidence_commitments.key")
            require_sha256(commitment, field="evidence_commitments.value")
        object.__setattr__(self, "evidence_commitments", frozen)


@dataclass(frozen=True, slots=True)
class LocalEnclaveAttestation:
    mode: str
    enabled: bool
    allowed_purpose_commitments: tuple[str, ...]
    local_development_only: bool
    production_capable: bool
    attestation_commitment: str

    def __post_init__(self) -> None:
        if self.mode != LOCAL_DEVELOPMENT_MODE or self.enabled is not True:
            raise SchemaError(DenialCode.INVALID_VALUE, field="enclave_attestation")
        if self.local_development_only is not True or self.production_capable is not False:
            raise SchemaError(DenialCode.INVALID_VALUE, field="enclave_attestation")
        if not self.allowed_purpose_commitments or tuple(sorted(set(self.allowed_purpose_commitments))) != (
            self.allowed_purpose_commitments
        ):
            raise SchemaError(DenialCode.INVALID_VALUE, field="allowed_purpose_commitments")
        for commitment in self.allowed_purpose_commitments:
            require_sha256(commitment, field="allowed_purpose_commitments")
        require_sha256(self.attestation_commitment, field="attestation_commitment")
        if domain_hash("aureon.plumber.local-enclave-attestation.v0", self.commitment_payload()) != (
            self.attestation_commitment
        ):
            raise SchemaError(DenialCode.INVALID_VALUE, field="attestation_commitment")

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "enabled": self.enabled,
            "allowed_purpose_commitments": list(self.allowed_purpose_commitments),
            "local_development_only": self.local_development_only,
            "production_capable": self.production_capable,
        }

    def public_summary(self) -> dict[str, Any]:
        return {**self.commitment_payload(), "attestation_commitment": self.attestation_commitment}


@dataclass(frozen=True, slots=True)
class LocalEnclaveExecutionReceipt:
    disposition: EnclaveDisposition
    packet_commitment: str
    purpose_commitment: str
    processor_id: str
    outcome_code: str
    result_commitment: str
    evidence_commitment: str
    executed_at: str
    denial_codes: tuple[str, ...]
    local_development_only: bool
    production_release: bool
    receipt_commitment: str

    def __post_init__(self) -> None:
        try:
            disposition = EnclaveDisposition(self.disposition)
        except ValueError as exc:
            raise SchemaError(DenialCode.INVALID_VALUE, field="disposition") from exc
        object.__setattr__(self, "disposition", disposition)
        if not isinstance(self.processor_id, str) or _SAFE_CODE_RE.fullmatch(self.processor_id) is None:
            raise SchemaError(DenialCode.INVALID_VALUE, field="processor_id")
        if not isinstance(self.outcome_code, str) or _SAFE_CODE_RE.fullmatch(self.outcome_code) is None:
            raise SchemaError(DenialCode.INVALID_VALUE, field="outcome_code")
        for field in (
            "packet_commitment",
            "purpose_commitment",
            "result_commitment",
            "evidence_commitment",
            "receipt_commitment",
        ):
            require_sha256(getattr(self, field), field=field)
        if tuple(sorted(set(self.denial_codes))) != self.denial_codes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="denial_codes")
        if (disposition is EnclaveDisposition.COMPLETED_LOCAL) != (not self.denial_codes):
            raise SchemaError(DenialCode.INVALID_VALUE, field="disposition")
        if self.local_development_only is not True or self.production_release is not False:
            raise SchemaError(DenialCode.INVALID_VALUE, field="execution_scope")
        from .schema import parse_timestamp

        parse_timestamp(self.executed_at, field="executed_at")
        if domain_hash("aureon.plumber.local-enclave-receipt.v0", self.commitment_payload()) != (
            self.receipt_commitment
        ):
            raise SchemaError(DenialCode.INVALID_VALUE, field="receipt_commitment")

    @classmethod
    def build(
        cls,
        *,
        disposition: EnclaveDisposition,
        packet_commitment: str,
        purpose_commitment: str,
        processor_id: str,
        outcome_code: str,
        result_commitment: str,
        evidence_commitment: str,
        executed_at: datetime,
        denial_codes: Sequence[EnclaveCode | str] = (),
    ) -> LocalEnclaveExecutionReceipt:
        codes = tuple(sorted({str(code) for code in denial_codes}))
        executed_at_text = format_timestamp(executed_at)
        values = {
            "disposition": str(disposition),
            "packet_commitment": packet_commitment,
            "purpose_commitment": purpose_commitment,
            "processor_id": processor_id,
            "outcome_code": outcome_code,
            "result_commitment": result_commitment,
            "evidence_commitment": evidence_commitment,
            "executed_at": executed_at_text,
            "denial_codes": list(codes),
            "local_development_only": True,
            "production_release": False,
        }
        return cls(
            disposition=disposition,
            packet_commitment=packet_commitment,
            purpose_commitment=purpose_commitment,
            processor_id=processor_id,
            outcome_code=outcome_code,
            result_commitment=result_commitment,
            evidence_commitment=evidence_commitment,
            executed_at=executed_at_text,
            denial_codes=codes,
            local_development_only=True,
            production_release=False,
            receipt_commitment=domain_hash("aureon.plumber.local-enclave-receipt.v0", values),
        )

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "disposition": str(self.disposition),
            "packet_commitment": self.packet_commitment,
            "purpose_commitment": self.purpose_commitment,
            "processor_id": self.processor_id,
            "outcome_code": self.outcome_code,
            "result_commitment": self.result_commitment,
            "evidence_commitment": self.evidence_commitment,
            "executed_at": self.executed_at,
            "denial_codes": list(self.denial_codes),
            "local_development_only": self.local_development_only,
            "production_release": self.production_release,
        }

    def public_summary(self) -> dict[str, Any]:
        return {**self.commitment_payload(), "receipt_commitment": self.receipt_commitment}


class LocalDevelopmentEnclave:
    """Opt-in local callback runner; deliberately not a production enclave."""

    def __init__(
        self,
        *,
        allowed_purposes: Sequence[str],
        insecure_opt_in: str,
        mode: str = LOCAL_DEVELOPMENT_MODE,
    ) -> None:
        if mode != LOCAL_DEVELOPMENT_MODE:
            raise EnclaveConfigurationError("local_development_mode_required")
        if insecure_opt_in != INSECURE_OPT_IN_ACK:
            raise EnclaveConfigurationError("insecure_opt_in_required")
        if isinstance(allowed_purposes, (str, bytes, bytearray)) or not isinstance(allowed_purposes, Sequence):
            raise EnclaveConfigurationError("allowed_purposes_invalid")
        parsed = tuple(sorted({require_nonblank(item, field="allowed_purpose") for item in allowed_purposes}))
        if not parsed:
            raise EnclaveConfigurationError("allowed_purposes_invalid")
        self._allowed_purposes = parsed

    def attestation(self) -> LocalEnclaveAttestation:
        commitments = tuple(
            sorted(domain_hash("aureon.plumber.purpose.v0", purpose) for purpose in self._allowed_purposes)
        )
        values = {
            "mode": LOCAL_DEVELOPMENT_MODE,
            "enabled": True,
            "allowed_purpose_commitments": list(commitments),
            "local_development_only": True,
            "production_capable": False,
        }
        return LocalEnclaveAttestation(
            mode=LOCAL_DEVELOPMENT_MODE,
            enabled=True,
            allowed_purpose_commitments=commitments,
            local_development_only=True,
            production_capable=False,
            attestation_commitment=domain_hash(
                "aureon.plumber.local-enclave-attestation.v0",
                values,
            ),
        )

    def execute_hnc_packet(
        self,
        hnc_packet: Mapping[str, Any],
        *,
        master_key: bytes | str,
        expected_purpose: str,
        processor_id: str,
        processor: Callable[[memoryview], LocalComputationResult],
        now: datetime,
    ) -> LocalEnclaveExecutionReceipt:
        current = require_aware_datetime(now, field="now")
        require_nonblank(expected_purpose, field="expected_purpose", max_length=1024)
        if not isinstance(processor_id, str) or _SAFE_CODE_RE.fullmatch(processor_id) is None:
            raise SchemaError(DenialCode.INVALID_VALUE, field="processor_id")
        if not callable(processor):
            raise SchemaError(DenialCode.INVALID_TYPE, field="processor")
        purpose_commitment = domain_hash("aureon.plumber.purpose.v0", expected_purpose)
        fallback_packet_commitment = domain_hash(
            "aureon.plumber.invalid-local-input.v0",
            {"purpose_commitment": purpose_commitment},
        )
        try:
            binding = bind_hnc_packet(hnc_packet)
            fallback_packet_commitment = binding.hnc_packet_commitment
        except PacketContractError:
            return self._denied_receipt(
                disposition=EnclaveDisposition.DENY,
                code=EnclaveCode.HNC_PACKET_INVALID,
                packet_commitment=fallback_packet_commitment,
                purpose_commitment=purpose_commitment,
                processor_id=processor_id,
                now=current,
            )
        if expected_purpose not in self._allowed_purposes or binding.purpose_commitment != purpose_commitment:
            return self._denied_receipt(
                disposition=EnclaveDisposition.DENY,
                code=EnclaveCode.PURPOSE_NOT_ALLOWED,
                packet_commitment=binding.hnc_packet_commitment,
                purpose_commitment=purpose_commitment,
                processor_id=processor_id,
                now=current,
            )
        try:
            from aureon.harmonic.hnc_quantum_packet_crypto import (
                HNCPacketError,
                decode_hnc_quantum_packet,
            )

            try:
                decoded = decode_hnc_quantum_packet(
                    hnc_packet,
                    master_key,
                    expected_purpose=expected_purpose,
                )
            except HNCPacketError:
                return self._denied_receipt(
                    disposition=EnclaveDisposition.DENY,
                    code=EnclaveCode.HNC_DECODE_DENIED,
                    packet_commitment=binding.hnc_packet_commitment,
                    purpose_commitment=purpose_commitment,
                    processor_id=processor_id,
                    now=current,
                )
            buffer = bytearray(decoded.plaintext)
            del decoded
            view = memoryview(buffer)
            try:
                result = processor(view)
            except Exception:
                return self._denied_receipt(
                    disposition=EnclaveDisposition.HOLD,
                    code=EnclaveCode.PROCESSOR_FAILED,
                    packet_commitment=binding.hnc_packet_commitment,
                    purpose_commitment=purpose_commitment,
                    processor_id=processor_id,
                    now=current,
                )
            finally:
                view.release()
                buffer[:] = b"\x00" * len(buffer)
        except Exception:
            return self._denied_receipt(
                disposition=EnclaveDisposition.HOLD,
                code=EnclaveCode.PROCESSOR_FAILED,
                packet_commitment=binding.hnc_packet_commitment,
                purpose_commitment=purpose_commitment,
                processor_id=processor_id,
                now=current,
            )
        if not isinstance(result, LocalComputationResult):
            return self._denied_receipt(
                disposition=EnclaveDisposition.DENY,
                code=EnclaveCode.PROCESSOR_RESULT_INVALID,
                packet_commitment=binding.hnc_packet_commitment,
                purpose_commitment=purpose_commitment,
                processor_id=processor_id,
                now=current,
            )
        evidence_commitment = domain_hash(
            "aureon.plumber.local-computation-evidence.v0",
            dict(result.evidence_commitments),
        )
        return LocalEnclaveExecutionReceipt.build(
            disposition=EnclaveDisposition.COMPLETED_LOCAL,
            packet_commitment=binding.hnc_packet_commitment,
            purpose_commitment=purpose_commitment,
            processor_id=processor_id,
            outcome_code=result.outcome_code,
            result_commitment=result.result_commitment,
            evidence_commitment=evidence_commitment,
            executed_at=current,
        )

    @staticmethod
    def _denied_receipt(
        *,
        disposition: EnclaveDisposition,
        code: EnclaveCode,
        packet_commitment: str,
        purpose_commitment: str,
        processor_id: str,
        now: datetime,
    ) -> LocalEnclaveExecutionReceipt:
        result_commitment = domain_hash(
            "aureon.plumber.no-local-result.v0",
            {
                "packet_commitment": packet_commitment,
                "purpose_commitment": purpose_commitment,
                "code": str(code),
            },
        )
        return LocalEnclaveExecutionReceipt.build(
            disposition=disposition,
            packet_commitment=packet_commitment,
            purpose_commitment=purpose_commitment,
            processor_id=processor_id,
            outcome_code=str(code),
            result_commitment=result_commitment,
            evidence_commitment=domain_hash(
                "aureon.plumber.no-local-evidence.v0",
                {"result_commitment": result_commitment},
            ),
            executed_at=now,
            denial_codes=(code,),
        )


__all__ = [
    "INSECURE_OPT_IN_ACK",
    "LOCAL_DEVELOPMENT_MODE",
    "EnclaveCode",
    "EnclaveConfigurationError",
    "EnclaveDisposition",
    "LocalComputationResult",
    "LocalDevelopmentEnclave",
    "LocalEnclaveAttestation",
    "LocalEnclaveExecutionReceipt",
]
