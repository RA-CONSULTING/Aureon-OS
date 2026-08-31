"""Pinned, one-shot, local-development release orchestration for Plumber v0.

The engine constructor pins trust, quorum policy, enclave, and replay state.
Only inspections issued by that engine instance may execute.  There is no
production release path and no raw decrypted result in any return value.
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from .crypto import domain_hash
from .enclave import (
    EnclaveDisposition,
    LocalComputationResult,
    LocalDevelopmentEnclave,
    LocalEnclaveAttestation,
    LocalEnclaveExecutionReceipt,
)
from .immune_gate import (
    GateClass,
    GateDecision,
    GateEvidence,
    GateVerdict,
    build_gate_context_commitment,
    evaluate_immune_gate,
)
from .observer_transcript import ObserverTranscriptV0
from .packet import (
    PacketDisposition,
    PacketInspection,
    PacketReplayGuard,
    PacketTrustPolicy,
    bind_hnc_packet,
    inspect_plumber_packet,
)
from .quorum import AuthorityPermit
from .schema import (
    DenialCode,
    PlumberPacketV0,
    SchemaError,
    parse_timestamp,
    require_aware_datetime,
    require_sha256,
)
from .sympathetic_identity import SympatheticIdentityV0


class ReleaseDisposition(StrEnum):
    ALLOW_LOCAL_DEVELOPMENT = "allow_local_development"
    COMPLETED_LOCAL = "completed_local"
    HOLD = "hold"
    DENY = "deny"


class ReleaseCode(StrEnum):
    PACKET_HOLD = "packet_hold"
    PACKET_DENIED = "packet_denied"
    PACKET_NOT_TRUSTED = "packet_not_trusted"
    IMMUNE_GATE_HOLD = "immune_gate_hold"
    IMMUNE_GATE_DENIED = "immune_gate_denied"
    IMMUNE_GATE_CONTEXT_MISMATCH = "immune_gate_context_mismatch"
    IMMUNE_GATE_BINDING_MISMATCH = "immune_gate_binding_mismatch"
    IMMUNE_GATE_NOT_ISSUED = "immune_gate_not_issued"
    QUORUM_NOT_VALIDATED = "quorum_not_validated"
    TRUST_POLICY_MISMATCH = "trust_policy_mismatch"
    QUORUM_POLICY_MISMATCH = "quorum_policy_mismatch"
    ENCLAVE_ATTESTATION_INVALID = "enclave_attestation_invalid"
    PURPOSE_MISMATCH = "purpose_mismatch"
    INSPECTION_NOT_ISSUED = "inspection_not_issued"
    INSPECTION_TIME_ROLLBACK = "inspection_time_rollback"
    INSPECTION_EVIDENCE_EXPIRED = "inspection_evidence_expired"
    REPLAY_DETECTED = "replay_detected"
    ENCLAVE_HOLD = "enclave_hold"
    ENCLAVE_DENIED = "enclave_denied"
    ENCLAVE_RECEIPT_MISMATCH = "enclave_receipt_mismatch"


_REFRESHABLE_GATE_CODES = {
    str(DenialCode.FUTURE_STATE),
    str(DenialCode.POLICY_RECEIPT_MISSING),
    str(DenialCode.STALE_STATE),
}


def _gate_for_inspection(packet: PacketInspection) -> GateDecision:
    """Build the only gate decision acceptable for one trusted inspection."""

    context = build_gate_context_commitment(
        packet_identity=packet.packet_identity,
        session_identity=packet.session_identity,
        purpose_commitment=packet.purpose_commitment,
    )
    evidence = tuple(
        GateEvidence(
            gate_class=gate_class,
            receipt_commitment=packet.gate_evidence_commitments[str(gate_class)],
            valid=True,
            context_commitment=context,
        )
        for gate_class in GateClass
    )
    return evaluate_immune_gate(
        evidence,
        packet_inspection_commitment=packet.inspection_commitment,
        evaluated_at=parse_timestamp(packet.inspected_at, field="inspected_at"),
        expires_at=parse_timestamp(
            packet.evidence_expires_at,
            field="evidence_expires_at",
        ),
    )


@dataclass(frozen=True, slots=True)
class ReleaseDecision:
    disposition: ReleaseDisposition
    packet_commitment: str
    purpose_commitment: str
    packet_inspection_commitment: str
    gate_decision_commitment: str
    quorum_commitment: str
    trust_policy_commitment: str
    quorum_policy_commitment: str
    enclave_attestation_commitment: str
    denial_codes: tuple[str, ...]
    production_release: bool
    decision_commitment: str

    def __post_init__(self) -> None:
        try:
            disposition = ReleaseDisposition(self.disposition)
        except ValueError as exc:
            raise SchemaError(DenialCode.INVALID_VALUE, field="disposition") from exc
        object.__setattr__(self, "disposition", disposition)
        if disposition is ReleaseDisposition.COMPLETED_LOCAL:
            raise SchemaError(DenialCode.INVALID_VALUE, field="disposition")
        for field in (
            "packet_commitment",
            "purpose_commitment",
            "packet_inspection_commitment",
            "gate_decision_commitment",
            "quorum_commitment",
            "trust_policy_commitment",
            "quorum_policy_commitment",
            "enclave_attestation_commitment",
            "decision_commitment",
        ):
            require_sha256(getattr(self, field), field=field)
        if tuple(sorted(set(self.denial_codes))) != self.denial_codes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="denial_codes")
        if (disposition is ReleaseDisposition.ALLOW_LOCAL_DEVELOPMENT) != (not self.denial_codes):
            raise SchemaError(DenialCode.INVALID_VALUE, field="disposition")
        if self.production_release is not False:
            raise SchemaError(DenialCode.INVALID_VALUE, field="production_release")
        if domain_hash("aureon.plumber.local-release-decision.v0", self.commitment_payload()) != (
            self.decision_commitment
        ):
            raise SchemaError(DenialCode.INVALID_VALUE, field="decision_commitment")

    @classmethod
    def build(
        cls,
        *,
        disposition: ReleaseDisposition,
        packet: PacketInspection,
        gate: GateDecision,
        attestation: LocalEnclaveAttestation,
        denial_codes: Sequence[ReleaseCode | str] = (),
    ) -> ReleaseDecision:
        codes = tuple(sorted({str(code) for code in denial_codes}))
        values = {
            "disposition": str(disposition),
            "packet_commitment": packet.packet_commitment,
            "purpose_commitment": packet.purpose_commitment,
            "packet_inspection_commitment": packet.inspection_commitment,
            "gate_decision_commitment": gate.decision_commitment,
            "quorum_commitment": packet.quorum_commitment,
            "trust_policy_commitment": packet.trust_policy_commitment,
            "quorum_policy_commitment": packet.quorum_policy_commitment,
            "enclave_attestation_commitment": attestation.attestation_commitment,
            "denial_codes": list(codes),
            "production_release": False,
        }
        return cls(
            disposition=disposition,
            packet_commitment=packet.packet_commitment,
            purpose_commitment=packet.purpose_commitment,
            packet_inspection_commitment=packet.inspection_commitment,
            gate_decision_commitment=gate.decision_commitment,
            quorum_commitment=packet.quorum_commitment,
            trust_policy_commitment=packet.trust_policy_commitment,
            quorum_policy_commitment=packet.quorum_policy_commitment,
            enclave_attestation_commitment=attestation.attestation_commitment,
            denial_codes=codes,
            production_release=False,
            decision_commitment=domain_hash("aureon.plumber.local-release-decision.v0", values),
        )

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "disposition": str(self.disposition),
            "packet_commitment": self.packet_commitment,
            "purpose_commitment": self.purpose_commitment,
            "packet_inspection_commitment": self.packet_inspection_commitment,
            "gate_decision_commitment": self.gate_decision_commitment,
            "quorum_commitment": self.quorum_commitment,
            "trust_policy_commitment": self.trust_policy_commitment,
            "quorum_policy_commitment": self.quorum_policy_commitment,
            "enclave_attestation_commitment": self.enclave_attestation_commitment,
            "denial_codes": list(self.denial_codes),
            "production_release": self.production_release,
        }

    def public_summary(self) -> dict[str, Any]:
        return {**self.commitment_payload(), "decision_commitment": self.decision_commitment}


def evaluate_local_release(
    packet: PacketInspection,
    gate: GateDecision,
    attestation: LocalEnclaveAttestation,
    *,
    required_trust_policy_commitment: str,
    required_quorum_policy_commitment: str,
) -> ReleaseDecision:
    """Pure decision function with explicit trust and policy pins."""

    if not isinstance(packet, PacketInspection):
        raise SchemaError(DenialCode.INVALID_TYPE, field="packet_inspection")
    if not isinstance(gate, GateDecision):
        raise SchemaError(DenialCode.INVALID_TYPE, field="gate_decision")
    if not isinstance(attestation, LocalEnclaveAttestation):
        raise SchemaError(DenialCode.INVALID_TYPE, field="enclave_attestation")
    require_sha256(required_trust_policy_commitment, field="required_trust_policy_commitment")
    require_sha256(required_quorum_policy_commitment, field="required_quorum_policy_commitment")
    hard: set[str] = set()
    holds: set[str] = set()
    if packet.disposition is PacketDisposition.DENY:
        hard.add(str(ReleaseCode.PACKET_DENIED))
    elif packet.disposition is PacketDisposition.HOLD:
        holds.add(str(ReleaseCode.PACKET_HOLD))
    if not packet.trusted:
        hard.add(str(ReleaseCode.PACKET_NOT_TRUSTED))
    if not packet.quorum_validated:
        hard.add(str(ReleaseCode.QUORUM_NOT_VALIDATED))
    expected_gate_context = build_gate_context_commitment(
        packet_identity=packet.packet_identity,
        session_identity=packet.session_identity,
        purpose_commitment=packet.purpose_commitment,
    )
    if gate.context_commitment != expected_gate_context:
        hard.add(str(ReleaseCode.IMMUNE_GATE_CONTEXT_MISMATCH))
    expected_gate = _gate_for_inspection(packet)
    if gate.decision_commitment != expected_gate.decision_commitment:
        hard.add(str(ReleaseCode.IMMUNE_GATE_BINDING_MISMATCH))
    if packet.trust_policy_commitment != required_trust_policy_commitment:
        hard.add(str(ReleaseCode.TRUST_POLICY_MISMATCH))
    if packet.quorum_policy_commitment != required_quorum_policy_commitment:
        hard.add(str(ReleaseCode.QUORUM_POLICY_MISMATCH))
    if gate.verdict is GateVerdict.DENIED:
        if gate.denial_codes and set(gate.denial_codes) <= _REFRESHABLE_GATE_CODES:
            holds.add(str(ReleaseCode.IMMUNE_GATE_HOLD))
        else:
            hard.add(str(ReleaseCode.IMMUNE_GATE_DENIED))
    if not attestation.enabled or not attestation.local_development_only or attestation.production_capable:
        hard.add(str(ReleaseCode.ENCLAVE_ATTESTATION_INVALID))
    if packet.purpose_commitment not in attestation.allowed_purpose_commitments:
        hard.add(str(ReleaseCode.PURPOSE_MISMATCH))
    if hard:
        disposition = ReleaseDisposition.DENY
        codes = tuple(sorted(hard | holds))
    elif holds:
        disposition = ReleaseDisposition.HOLD
        codes = tuple(sorted(holds))
    else:
        disposition = ReleaseDisposition.ALLOW_LOCAL_DEVELOPMENT
        codes = ()
    return ReleaseDecision.build(
        disposition=disposition,
        packet=packet,
        gate=gate,
        attestation=attestation,
        denial_codes=codes,
    )


@dataclass(frozen=True, slots=True)
class ReleaseExecutionReceipt:
    disposition: ReleaseDisposition
    packet_commitment: str
    purpose_commitment: str
    decision_commitment: str
    enclave_receipt_commitment: str
    denial_codes: tuple[str, ...]
    production_release: bool
    execution_commitment: str

    def __post_init__(self) -> None:
        try:
            disposition = ReleaseDisposition(self.disposition)
        except ValueError as exc:
            raise SchemaError(DenialCode.INVALID_VALUE, field="disposition") from exc
        object.__setattr__(self, "disposition", disposition)
        if disposition is ReleaseDisposition.ALLOW_LOCAL_DEVELOPMENT:
            raise SchemaError(DenialCode.INVALID_VALUE, field="disposition")
        for field in (
            "packet_commitment",
            "purpose_commitment",
            "decision_commitment",
            "enclave_receipt_commitment",
            "execution_commitment",
        ):
            require_sha256(getattr(self, field), field=field)
        if tuple(sorted(set(self.denial_codes))) != self.denial_codes:
            raise SchemaError(DenialCode.INVALID_VALUE, field="denial_codes")
        if (disposition is ReleaseDisposition.COMPLETED_LOCAL) != (not self.denial_codes):
            raise SchemaError(DenialCode.INVALID_VALUE, field="disposition")
        if self.production_release is not False:
            raise SchemaError(DenialCode.INVALID_VALUE, field="production_release")
        if domain_hash("aureon.plumber.local-release-execution.v0", self.commitment_payload()) != (
            self.execution_commitment
        ):
            raise SchemaError(DenialCode.INVALID_VALUE, field="execution_commitment")

    @classmethod
    def build(
        cls,
        *,
        disposition: ReleaseDisposition,
        decision: ReleaseDecision,
        enclave_receipt_commitment: str,
        denial_codes: Sequence[ReleaseCode | str] = (),
    ) -> ReleaseExecutionReceipt:
        codes = tuple(sorted({str(code) for code in denial_codes}))
        values = {
            "disposition": str(disposition),
            "packet_commitment": decision.packet_commitment,
            "purpose_commitment": decision.purpose_commitment,
            "decision_commitment": decision.decision_commitment,
            "enclave_receipt_commitment": enclave_receipt_commitment,
            "denial_codes": list(codes),
            "production_release": False,
        }
        return cls(
            disposition=disposition,
            packet_commitment=decision.packet_commitment,
            purpose_commitment=decision.purpose_commitment,
            decision_commitment=decision.decision_commitment,
            enclave_receipt_commitment=enclave_receipt_commitment,
            denial_codes=codes,
            production_release=False,
            execution_commitment=domain_hash("aureon.plumber.local-release-execution.v0", values),
        )

    def commitment_payload(self) -> dict[str, Any]:
        return {
            "disposition": str(self.disposition),
            "packet_commitment": self.packet_commitment,
            "purpose_commitment": self.purpose_commitment,
            "decision_commitment": self.decision_commitment,
            "enclave_receipt_commitment": self.enclave_receipt_commitment,
            "denial_codes": list(self.denial_codes),
            "production_release": self.production_release,
        }

    def public_summary(self) -> dict[str, Any]:
        return {**self.commitment_payload(), "execution_commitment": self.execution_commitment}


class LocalReleaseEngine:
    """One-shot engine with constructor-pinned trust, policy, and replay state."""

    def __init__(
        self,
        *,
        trust_policy: PacketTrustPolicy,
        required_quorum_policy_commitment: str,
        replay_guard: PacketReplayGuard,
        enclave: LocalDevelopmentEnclave,
    ) -> None:
        if not isinstance(trust_policy, PacketTrustPolicy):
            raise SchemaError(DenialCode.INVALID_TYPE, field="trust_policy")
        require_sha256(required_quorum_policy_commitment, field="required_quorum_policy_commitment")
        if not isinstance(replay_guard, PacketReplayGuard):
            raise SchemaError(DenialCode.INVALID_TYPE, field="replay_guard")
        if not isinstance(enclave, LocalDevelopmentEnclave):
            raise SchemaError(DenialCode.INVALID_TYPE, field="enclave")
        self._trust_policy = trust_policy
        self._required_quorum_policy_commitment = required_quorum_policy_commitment
        self._replay_guard = replay_guard
        self._enclave = enclave
        self._lock = threading.Lock()
        self._issued_inspections: set[str] = set()
        self._issued_gates: dict[str, str] = {}

    def inspect_packet(
        self,
        packet: PlumberPacketV0,
        hnc_packet: Mapping[str, Any],
        *,
        observer_transcript: ObserverTranscriptV0,
        sympathetic_identity: SympatheticIdentityV0,
        quorum_permits: Sequence[AuthorityPermit],
        now: datetime,
    ) -> PacketInspection:
        inspection = inspect_plumber_packet(
            packet,
            hnc_packet,
            now=now,
            observer_transcript=observer_transcript,
            sympathetic_identity=sympathetic_identity,
            quorum_permits=quorum_permits,
            trust_policy=self._trust_policy,
            required_quorum_policy_commitment=self._required_quorum_policy_commitment,
            replay_guard=self._replay_guard,
        )
        if inspection.disposition is PacketDisposition.VALID:
            with self._lock:
                self._issued_inspections.add(inspection.inspection_commitment)
        return inspection

    def issue_gate(self, packet: PacketInspection) -> GateDecision:
        """Issue the exact, one-use immune decision for an inspection from this engine."""

        if not isinstance(packet, PacketInspection):
            raise SchemaError(DenialCode.INVALID_TYPE, field="packet_inspection")
        with self._lock:
            issued = packet.inspection_commitment in self._issued_inspections
        if not issued or packet.disposition is not PacketDisposition.VALID:
            raise SchemaError(DenialCode.INVALID_VALUE, field="packet_inspection")
        gate = _gate_for_inspection(packet)
        with self._lock:
            if packet.inspection_commitment not in self._issued_inspections:
                raise SchemaError(DenialCode.INVALID_VALUE, field="packet_inspection")
            self._issued_gates[gate.decision_commitment] = packet.inspection_commitment
        return gate

    def evaluate(self, packet: PacketInspection, gate: GateDecision) -> ReleaseDecision:
        decision = evaluate_local_release(
            packet,
            gate,
            self._enclave.attestation(),
            required_trust_policy_commitment=self._trust_policy.trust_policy_commitment,
            required_quorum_policy_commitment=self._required_quorum_policy_commitment,
        )
        if decision.disposition is not ReleaseDisposition.ALLOW_LOCAL_DEVELOPMENT:
            return decision
        with self._lock:
            inspection_issued = packet.inspection_commitment in self._issued_inspections
            gate_issued = (
                self._issued_gates.get(gate.decision_commitment)
                == packet.inspection_commitment
            )
        if not inspection_issued:
            return ReleaseDecision.build(
                disposition=ReleaseDisposition.DENY,
                packet=packet,
                gate=gate,
                attestation=self._enclave.attestation(),
                denial_codes=(ReleaseCode.INSPECTION_NOT_ISSUED,),
            )
        if not gate_issued:
            return ReleaseDecision.build(
                disposition=ReleaseDisposition.DENY,
                packet=packet,
                gate=gate,
                attestation=self._enclave.attestation(),
                denial_codes=(ReleaseCode.IMMUNE_GATE_NOT_ISSUED,),
            )
        return decision

    def execute(
        self,
        packet: PacketInspection,
        gate: GateDecision,
        hnc_packet: Mapping[str, Any],
        *,
        master_key: bytes | str,
        expected_purpose: str,
        processor_id: str,
        processor: Callable[[memoryview], LocalComputationResult],
        now: datetime,
    ) -> tuple[ReleaseExecutionReceipt, LocalEnclaveExecutionReceipt | None]:
        current = require_aware_datetime(now, field="now")
        if not callable(processor):
            raise SchemaError(DenialCode.INVALID_TYPE, field="processor")
        decision = self.evaluate(packet, gate)
        no_receipt = domain_hash(
            "aureon.plumber.no-enclave-receipt.v0",
            {"decision_commitment": decision.decision_commitment},
        )
        if decision.disposition is not ReleaseDisposition.ALLOW_LOCAL_DEVELOPMENT:
            return (
                ReleaseExecutionReceipt.build(
                    disposition=decision.disposition,
                    decision=decision,
                    enclave_receipt_commitment=no_receipt,
                    denial_codes=decision.denial_codes,
                ),
                None,
            )
        with self._lock:
            issued = decision.packet_inspection_commitment in self._issued_inspections
            gate_issued = (
                self._issued_gates.get(gate.decision_commitment)
                == decision.packet_inspection_commitment
            )
            if issued and gate_issued:
                self._issued_inspections.remove(decision.packet_inspection_commitment)
                self._issued_gates.pop(gate.decision_commitment, None)
        if not issued:
            return self._blocked_execution(decision, no_receipt, ReleaseCode.INSPECTION_NOT_ISSUED)
        if not gate_issued:
            return self._blocked_execution(decision, no_receipt, ReleaseCode.IMMUNE_GATE_NOT_ISSUED)
        inspected_at = parse_timestamp(packet.inspected_at, field="inspected_at")
        evidence_not_before = parse_timestamp(
            packet.evidence_not_before,
            field="evidence_not_before",
        )
        evidence_expires_at = parse_timestamp(
            packet.evidence_expires_at,
            field="evidence_expires_at",
        )
        if current < inspected_at or current < evidence_not_before:
            return self._blocked_execution(
                decision,
                no_receipt,
                ReleaseCode.INSPECTION_TIME_ROLLBACK,
            )
        if current >= evidence_expires_at:
            return self._blocked_execution(
                decision,
                no_receipt,
                ReleaseCode.INSPECTION_EVIDENCE_EXPIRED,
            )
        if domain_hash("aureon.plumber.purpose.v0", expected_purpose) != decision.purpose_commitment:
            return self._blocked_execution(decision, no_receipt, ReleaseCode.PURPOSE_MISMATCH)
        try:
            live_binding = bind_hnc_packet(hnc_packet)
        except (SchemaError, TypeError, ValueError):
            return self._blocked_execution(
                decision, no_receipt, ReleaseCode.ENCLAVE_RECEIPT_MISMATCH
            )
        if (
            live_binding.hnc_packet_commitment != packet.hnc_packet_commitment
            or live_binding.purpose_commitment != packet.purpose_commitment
        ):
            return self._blocked_execution(
                decision, no_receipt, ReleaseCode.ENCLAVE_RECEIPT_MISMATCH
            )
        if not self._replay_guard.claim_for_execution(packet.replay_token):
            return self._blocked_execution(decision, no_receipt, ReleaseCode.REPLAY_DETECTED)
        try:
            def one_shot_processor(view: memoryview) -> LocalComputationResult:
                # Authentication and structural checks have completed when the
                # enclave invokes this wrapper.  Commit replay state before the
                # caller's processor can produce effects, including effects that
                # precede an exception or invalid result.
                if not self._replay_guard.commit_execution_claim(packet.replay_token):
                    raise RuntimeError("replay_execution_claim_unavailable")
                return processor(view)

            enclave_receipt = self._enclave.execute_hnc_packet(
                hnc_packet,
                master_key=master_key,
                expected_purpose=expected_purpose,
                processor_id=processor_id,
                processor=one_shot_processor,
                now=current,
            )
        finally:
            # If the processor wrapper was never reached, the claim still exists
            # and is safe to roll back.  A committed claim cannot be rolled back.
            if self._replay_guard.rollback_execution_claim(packet.replay_token):
                with self._lock:
                    if gate.decision_commitment not in self._issued_gates:
                        self._issued_inspections.add(
                            decision.packet_inspection_commitment
                        )
                        self._issued_gates[gate.decision_commitment] = (
                            decision.packet_inspection_commitment
                        )
        mismatched = (
            enclave_receipt.packet_commitment != packet.hnc_packet_commitment
            or enclave_receipt.purpose_commitment != packet.purpose_commitment
        )
        if mismatched:
            disposition = ReleaseDisposition.DENY
            codes: tuple[ReleaseCode | str, ...] = (ReleaseCode.ENCLAVE_RECEIPT_MISMATCH,)
        elif enclave_receipt.disposition is EnclaveDisposition.COMPLETED_LOCAL:
            disposition = ReleaseDisposition.COMPLETED_LOCAL
            codes = ()
        elif enclave_receipt.disposition is EnclaveDisposition.HOLD:
            disposition = ReleaseDisposition.HOLD
            codes = (ReleaseCode.ENCLAVE_HOLD, *enclave_receipt.denial_codes)
        else:
            disposition = ReleaseDisposition.DENY
            codes = (ReleaseCode.ENCLAVE_DENIED, *enclave_receipt.denial_codes)
        return (
            ReleaseExecutionReceipt.build(
                disposition=disposition,
                decision=decision,
                enclave_receipt_commitment=enclave_receipt.receipt_commitment,
                denial_codes=codes,
            ),
            enclave_receipt,
        )

    @staticmethod
    def _blocked_execution(
        decision: ReleaseDecision,
        no_receipt: str,
        code: ReleaseCode,
    ) -> tuple[ReleaseExecutionReceipt, None]:
        return (
            ReleaseExecutionReceipt.build(
                disposition=ReleaseDisposition.DENY,
                decision=decision,
                enclave_receipt_commitment=no_receipt,
                denial_codes=(code,),
            ),
            None,
        )

    def public_summary(self) -> dict[str, Any]:
        return {
            "scope": "local_development_only",
            "trust_policy_commitment": self._trust_policy.trust_policy_commitment,
            "quorum_policy_commitment": self._required_quorum_policy_commitment,
            "enclave_attestation_commitment": self._enclave.attestation().attestation_commitment,
            "production_release": False,
            "replay_guard": self._replay_guard.public_summary(),
        }


__all__ = [
    "LocalReleaseEngine",
    "ReleaseCode",
    "ReleaseDecision",
    "ReleaseDisposition",
    "ReleaseExecutionReceipt",
    "evaluate_local_release",
]
