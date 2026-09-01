"""End-to-end checks for v0.4 runtime intrusion evidence durability."""

from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from contextlib import AbstractContextManager
from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import aureon.plumber.runtime_guard_v04 as runtime_guard_module
from aureon.harmonic.hnc_quantum_packet_crypto import (
    decode_hnc_quantum_packet,
    validate_hnc_packet_contract,
)
from aureon.plumber.crypto import canonical_json_bytes, ed25519_public_key_hex
from aureon.plumber.os_protection import (
    OS_QUARANTINE_EVIDENCE_PURPOSE,
    AdmittedHNC,
    LocalOSProtectionBoundary,
    OSProtectionError,
    QuarantinedHNC,
)
from aureon.plumber.packet import bind_hnc_packet
from aureon.plumber.production_release_broker_v03 import (
    AuthorityBindingV03,
    ProductionReleaseVerifierV03,
)
from aureon.plumber.runtime_guard_v04 import (
    RUNTIME_INTRUSION_PURPOSE,
    RUNTIME_INTRUSION_SCHEMA,
    GuardedRuntimeCapabilityV04,
    HNCRuntimeViolationRecorderV04,
    RuntimeAuditGuardV04,
    RuntimeGuardError,
    RuntimeGuardViolation,
    _ActivePermit,
    audit_event_resource_commitment_v04,
)
from aureon.plumber.runtime_intrusion_ledger_v04 import (
    RuntimeIntrusionLedgerError,
    SQLiteRuntimeIntrusionLedgerV04,
)
from aureon.plumber.star_custody_v02 import (
    LocalDevelopmentStarCustodyV02,
    ProtectedMagicStarPacketV02,
)

MASTER_KEY = b"runtime-guard-durable-integration-key"
PREFLIGHT_PLAINTEXT_CANARY = b"commitment-only-hnc-quarantine"


def _oid(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _stack(
    path: Path,
    *,
    ledger_capacity: int,
    recorder_capacity: int,
) -> tuple[
    SQLiteRuntimeIntrusionLedgerV04,
    LocalOSProtectionBoundary,
    HNCRuntimeViolationRecorderV04,
]:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path.resolve(),
        ledger_id="runtime-guard-durable-integration",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=ledger_capacity,
    )
    boundary = LocalOSProtectionBoundary(
        boundary_id="runtime-guard-durable-integration",
        master_key_provider=lambda: MASTER_KEY,
        max_quarantine_evidence=recorder_capacity + 1,
        quarantine_evidence_sink=ledger,
    )
    recorder = HNCRuntimeViolationRecorderV04(
        boundary=boundary,
        max_receipts=recorder_capacity,
        require_durable_evidence=True,
    )
    return ledger, boundary, recorder


def _verifier() -> ProductionReleaseVerifierV03:
    keys = [Ed25519PrivateKey.generate() for _ in range(4)]
    roles = ("REVIEW", "DISPATCH", "EXECUTOR", "RECEIPT")
    bindings = [
        AuthorityBindingV03(
            role=role,
            authority_id=f"{role.casefold()}-authority",
            key_id=f"{role.casefold()}-key-v1",
            public_key_hex=ed25519_public_key_hex(key),
        )
        for role, key in zip(roles, keys, strict=True)
    ]
    return ProductionReleaseVerifierV03(
        review_authority=bindings[0],
        dispatch_authority=bindings[1],
        executor_authority=bindings[2],
        receipt_authority=bindings[3],
        trusted_now_ms=lambda: 2_000,
    )


def _guard_for_recorder(
    recorder: HNCRuntimeViolationRecorderV04,
    *,
    label: str,
) -> RuntimeAuditGuardV04:
    capability_id = _oid(f"{label}:capability")
    return RuntimeAuditGuardV04(
        verifier=_verifier(),
        recorder=recorder,
        runtime_measurement_sha256=_oid(f"{label}:runtime"),
        capabilities={
            capability_id: GuardedRuntimeCapabilityV04(
                capability_id=capability_id,
                capability_measurement_sha256=_oid(f"{label}:measurement"),
                handler=lambda: None,
            )
        },
    )


def _runtime_violation_material(
    *,
    label: str,
    sequence: int,
) -> tuple[bytes, dict[str, str]]:
    resource_commitment = _oid(f"terminal-resource:{label}")
    reason_code = "runtime_effect_not_magic_star_released"
    metadata = {
        "schema": RUNTIME_INTRUSION_SCHEMA,
        "sequence": sequence,
        "event_name": "os.remove",
        "resource_commitment": resource_commitment,
        "reason_code": reason_code,
        "raw_arguments_retained": False,
        "audit_event_origin_attested": False,
        "effect_attempt_attested": False,
        "resource_commitment_confidentiality_attested": False,
        "resource_commitments_keyed": False,
        "action_eligible": False,
        "economic_eligible": False,
        "production_ready": False,
    }
    return canonical_json_bytes(metadata), {
        "event_name": "os.remove",
        "resource_commitment": resource_commitment,
        "reason_code": reason_code,
    }


def _record_terminal_runtime_violation(
    boundary: LocalOSProtectionBoundary,
    *,
    label: str,
) -> QuarantinedHNC:
    payload, operator_aad = _runtime_violation_material(
        label=label,
        sequence=1,
    )
    outcome = boundary.admit_external(
        payload,
        source_id="aureon:runtime-guard-v04",
        ingress_kind="runtime-effect-violation",
        purpose=RUNTIME_INTRUSION_PURPOSE,
        operator_aad=operator_aad,
        content_validator=lambda _view: False,
    )
    assert isinstance(outcome, QuarantinedHNC)
    return outcome


def _stored_violation_packet(
    ledger: SQLiteRuntimeIntrusionLedgerV04,
    *,
    sequence: int,
) -> tuple[dict[str, Any], tuple[str, str]]:
    row = ledger._connection.execute(
        "SELECT hnc_packet_json, hnc_packet_commitment, hnc_binding_commitment "
        "FROM runtime_intrusion_entries_v04 WHERE sequence = ? AND entry_kind = 'VIOLATION'",
        (sequence,),
    ).fetchone()
    assert row is not None
    packet = json.loads(bytes(row[0]).decode("utf-8"))
    assert isinstance(packet, dict)
    return packet, (str(row[1]), str(row[2]))


def test_durable_preflight_commits_encrypted_hnc_probe_on_preopened_connection(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-intrusions.sqlite3"
    ledger, boundary, recorder = _stack(
        path,
        ledger_capacity=3,
        recorder_capacity=2,
    )
    preopened_connection = ledger._connection

    preflight = recorder.preflight()

    assert ledger._connection is preopened_connection
    assert preflight["ready"] is True
    assert preflight["durable_evidence_required"] is True
    assert preflight["durable_hnc_evidence_ready"] is True
    assert preflight["durable_hnc_capacity_before_probe"] == 3
    assert preflight["durable_hnc_capacity_after_probe"] == 2
    assert boundary.public_summary()["durable_quarantine_evidence_count"] == 1
    assert ledger.preflight()["violation_count"] == 1

    packet, stored_commitments = _stored_violation_packet(ledger, sequence=2)
    binding = bind_hnc_packet(packet)
    assert validate_hnc_packet_contract(packet)["valid"] is True
    assert (
        packet["operator_aad"]["ledger_instance_commitment"]
        == ledger.preflight()["ledger_instance_commitment"]
    )
    assert stored_commitments == (
        binding.hnc_packet_commitment,
        binding.binding_commitment,
    )
    decoded = decode_hnc_quantum_packet(
        packet,
        MASTER_KEY,
        expected_purpose=OS_QUARANTINE_EVIDENCE_PURPOSE,
    )
    evidence = json.loads(decoded.plaintext)
    assert evidence["raw_material_retained"] is False
    assert evidence["source_truth_established_by_local_wrapping"] is False

    for candidate in path.parent.iterdir():
        if candidate.is_file():
            assert PREFLIGHT_PLAINTEXT_CANARY not in candidate.read_bytes()
    ledger.close()


def test_cached_preflight_revalidates_closed_sink_before_guard_install(
    tmp_path: Path,
) -> None:
    ledger, _boundary, recorder = _stack(
        tmp_path / "closed-before-install.sqlite3",
        ledger_capacity=3,
        recorder_capacity=1,
    )
    assert recorder.preflight()["ready"] is True
    guard = _guard_for_recorder(recorder, label="closed-before-install")
    ledger.close()

    refreshed = recorder.preflight()
    assert refreshed["ready"] is False
    assert recorder.terminal_failure_code() is not None
    with pytest.raises(RuntimeGuardError) as raised:
        guard.install()
    assert raised.value.code == "runtime_hnc_violation_recorder_not_ready"
    assert guard.public_summary()["installed"] is False


def test_cached_preflight_revalidates_tampered_sink_before_guard_install(
    tmp_path: Path,
) -> None:
    ledger, _boundary, recorder = _stack(
        tmp_path / "tampered-before-install.sqlite3",
        ledger_capacity=3,
        recorder_capacity=1,
    )
    assert recorder.preflight()["ready"] is True
    guard = _guard_for_recorder(recorder, label="tampered-before-install")
    ledger._connection.execute(
        "DROP INDEX runtime_intrusion_entries_v04_commitment_uq"
    )

    refreshed = recorder.preflight()
    assert refreshed["ready"] is False
    assert recorder.terminal_failure_code() is not None
    with pytest.raises(RuntimeGuardError) as raised:
        guard.install()
    assert raised.value.code == "runtime_hnc_violation_recorder_not_ready"
    assert guard.public_summary()["installed"] is False
    ledger.close()


def test_guard_seals_sink_before_irreversible_hook_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, _boundary, recorder = _stack(
        tmp_path / "sealed-before-hook.sqlite3",
        ledger_capacity=3,
        recorder_capacity=1,
    )
    guard = _guard_for_recorder(recorder, label="sealed-before-hook")
    installed_hook: dict[str, Any] = {}
    close_codes: list[str] = []

    def fake_addaudithook(hook: Any) -> None:
        try:
            ledger.close()
        except RuntimeIntrusionLedgerError as exc:
            close_codes.append(exc.code)
        else:  # pragma: no cover - regression would make this branch fail
            close_codes.append("close_was_not_rejected")
        installed_hook["hook"] = hook

    def fake_audit(event_name: str, *arguments: Any) -> None:
        installed_hook["hook"](event_name, arguments)

    monkeypatch.setattr(runtime_guard_module, "_GLOBAL_GUARD", None)
    monkeypatch.setattr(runtime_guard_module.sys, "addaudithook", fake_addaudithook)
    monkeypatch.setattr(runtime_guard_module.sys, "audit", fake_audit)

    summary = guard.install()

    assert summary["installed"] is True
    assert summary["runtime_guard_lifecycle_sealed"] is True
    assert close_codes == ["runtime_intrusion_ledger_runtime_guard_sealed"]
    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger.close()
    assert raised.value.code == "runtime_intrusion_ledger_runtime_guard_sealed"
    # The public API deliberately has no unseal.  Close only the isolated test
    # connection directly, then wipe its retained test keys, so the Windows
    # temporary file is releasable without adding a production unseal path.
    ledger._connection.close()
    ledger._wipe_retained_keys()
    ledger._closed = True


def test_boundary_durable_receipt_head_is_monotonic_under_concurrency(
    tmp_path: Path,
) -> None:
    ledger, boundary, recorder = _stack(
        tmp_path / "concurrent-boundary-head.sqlite3",
        ledger_capacity=8,
        recorder_capacity=4,
    )
    assert recorder.preflight()["ready"] is True

    def record(index: int) -> dict[str, Any]:
        return recorder.record(
            event_name="os.remove",
            resource_commitment=_oid(f"concurrent-resource:{index}"),
            reason_code="runtime_effect_not_magic_star_released",
        )

    with ThreadPoolExecutor(max_workers=4) as pool:
        receipts = list(pool.map(record, range(4)))

    assert len(receipts) == 4
    boundary_summary = boundary.public_summary()
    ledger_summary = ledger.preflight()
    stored_head = ledger._connection.execute(
        "SELECT entry_commitment FROM runtime_intrusion_entries_v04 "
        "WHERE sequence = 6"
    ).fetchone()
    assert stored_head is not None
    assert boundary_summary["durable_quarantine_evidence_count"] == 5
    assert boundary_summary[
        "durable_quarantine_evidence_last_receipt_sequence"
    ] == 6
    assert boundary_summary["durable_quarantine_evidence_ledger_entry_count"] == 6
    assert boundary_summary[
        "durable_quarantine_evidence_ledger_violation_count"
    ] == 5
    assert boundary_summary["durable_quarantine_evidence_head_commitment"] == str(
        stored_head[0]
    )
    assert ledger_summary["entry_count"] == 6
    assert ledger_summary["violation_count"] == 5
    exhausted = recorder.preflight()
    assert exhausted["ready"] is False
    assert exhausted["reason_code"] == "runtime_violation_capacity_exhausted"
    ledger.close()


@pytest.mark.parametrize(
    ("terminal", "violation_generation", "expected_code"),
    [
        (True, 0, "runtime_intrusion_evidence_terminal"),
        (False, 1, "runtime_active_permit_revoked"),
    ],
)
def test_terminal_or_generation_change_revokes_active_permit_before_authorized_event(
    terminal: bool,
    violation_generation: int,
    expected_code: str,
    tmp_path: Path,
) -> None:
    recorder = HNCRuntimeViolationRecorderV04(
        boundary=LocalOSProtectionBoundary(
            boundary_id=f"permit-revocation:{expected_code}",
            master_key_provider=lambda: MASTER_KEY,
        ),
        max_receipts=2,
    )
    guard = _guard_for_recorder(recorder, label=expected_code)
    target = (tmp_path / f"{expected_code}-must-not-exist").resolve()
    arguments = (str(target), 511, -1)
    resource_commitment = audit_event_resource_commitment_v04(
        "os.mkdir",
        arguments,
    )
    permit = _ActivePermit(
        dispatch_commitment=_oid(f"{expected_code}:dispatch"),
        owner_thread_id=threading.get_ident(),
        remaining={("os.mkdir", resource_commitment): 1},
        violation_generation_at_start=0,
    )
    guard._thread_state.active_permit = permit
    guard._evidence_terminal = terminal
    guard._violation_count = violation_generation

    with pytest.raises(RuntimeGuardViolation) as raised:
        guard._audit_hook("os.mkdir", arguments)
    assert raised.value.code == expected_code
    assert permit.revoked is True
    assert permit.remaining[("os.mkdir", resource_commitment)] == 1
    assert not target.exists()


def test_terminal_transition_cannot_complete_inside_permit_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorder = HNCRuntimeViolationRecorderV04(
        boundary=LocalOSProtectionBoundary(
            boundary_id="permit-terminal-linearization",
            master_key_provider=lambda: MASTER_KEY,
        ),
        max_receipts=2,
    )
    assert recorder.preflight()["ready"] is True
    recorder.seal_for_runtime_guard_install()
    owner_token, lifecycle_generation = recorder._runtime_guard_lease_identity()
    guard = _guard_for_recorder(recorder, label="permit-terminal-linearization")
    guard._recorder_owner_token = owner_token
    guard._recorder_lifecycle_generation = lifecycle_generation

    target = (tmp_path / "permit-terminal-must-not-exist").resolve()
    arguments = (str(target), 511, -1)
    resource_commitment = audit_event_resource_commitment_v04(
        "os.mkdir",
        arguments,
    )
    permit = _ActivePermit(
        dispatch_commitment=_oid("permit-terminal:dispatch"),
        owner_thread_id=threading.get_ident(),
        remaining={("os.mkdir", resource_commitment): 2},
        violation_generation_at_start=0,
    )
    guard._thread_state.active_permit = permit
    decision_entered = threading.Event()
    transition_attempted = threading.Event()
    transition_completed = threading.Event()
    original_decision = guard._audit_authorization_decision

    def blocking_decision(**kwargs: Any) -> tuple[bool, str | None]:
        decision_entered.set()
        assert transition_attempted.wait(5)
        assert transition_completed.is_set() is False
        return original_decision(**kwargs)

    monkeypatch.setattr(guard, "_audit_authorization_decision", blocking_decision)

    def complete_terminal_transition() -> None:
        assert decision_entered.wait(5)
        transition_attempted.set()
        recorder.record(
            event_name="os.remove",
            resource_commitment=_oid("permit-terminal:violation"),
            reason_code="runtime_effect_not_magic_star_released",
        )
        transition_completed.set()

    worker = threading.Thread(target=complete_terminal_transition)
    worker.start()
    guard._audit_hook("os.mkdir", arguments)
    assert permit.remaining[("os.mkdir", resource_commitment)] == 1
    assert transition_completed.wait(5)
    worker.join(timeout=5)
    assert worker.is_alive() is False

    with pytest.raises(RuntimeGuardViolation) as raised:
        guard._audit_hook("os.mkdir", arguments)
    assert raised.value.code == "runtime_intrusion_evidence_terminal"
    assert permit.revoked is True
    assert permit.remaining[("os.mkdir", resource_commitment)] == 1
    assert target.exists() is False
    guard._thread_state.active_permit = None


def test_denied_runtime_audit_commitment_persists_and_validates_after_restart(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-intrusions.sqlite3"
    ledger, _boundary, recorder = _stack(
        path,
        ledger_capacity=4,
        recorder_capacity=2,
    )
    assert recorder.preflight()["ready"] is True
    resource_commitment = _oid("denied-runtime-resource")

    receipt = recorder.record(
        event_name="os.remove",
        resource_commitment=resource_commitment,
        reason_code="runtime_effect_not_magic_star_released",
    )
    denied_metadata = {
        "schema": RUNTIME_INTRUSION_SCHEMA,
        "sequence": 1,
        "event_name": "os.remove",
        "resource_commitment": resource_commitment,
        "reason_code": "runtime_effect_not_magic_star_released",
        "raw_arguments_retained": False,
        "audit_event_origin_attested": False,
        "effect_attempt_attested": False,
        "resource_commitment_confidentiality_attested": False,
        "resource_commitments_keyed": False,
        "action_eligible": False,
        "economic_eligible": False,
        "production_ready": False,
    }
    expected_content_sha256 = hashlib.sha256(
        canonical_json_bytes(denied_metadata)
    ).hexdigest()
    packet, _stored_commitments = _stored_violation_packet(ledger, sequence=3)
    evidence = json.loads(
        decode_hnc_quantum_packet(
            packet,
            MASTER_KEY,
            expected_purpose=OS_QUARANTINE_EVIDENCE_PURPOSE,
        ).plaintext
    )
    assert receipt["event_name"] == "os.remove"
    assert evidence["content_sha256"] == expected_content_sha256
    assert ledger.preflight()["violation_count"] == 2
    ledger.close()

    reopened = SQLiteRuntimeIntrusionLedgerV04(
        path.resolve(),
        ledger_id="runtime-guard-durable-integration",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=4,
    )
    restarted = reopened.preflight()
    assert restarted["ready"] is True
    assert restarted["entry_count"] == 3
    assert restarted["violation_count"] == 2
    restarted_packet, _ = _stored_violation_packet(reopened, sequence=3)
    restarted_evidence = json.loads(
        decode_hnc_quantum_packet(
            restarted_packet,
            MASTER_KEY,
            expected_purpose=OS_QUARANTINE_EVIDENCE_PURPOSE,
        ).plaintext
    )
    assert restarted_evidence["content_sha256"] == expected_content_sha256
    reopened.close()


def test_final_durable_capacity_is_sticky_in_boundary_and_recorder(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-intrusions.sqlite3"
    ledger, boundary, recorder = _stack(
        path,
        ledger_capacity=2,
        recorder_capacity=1,
    )
    assert recorder.preflight()["ready"] is True

    recorder.record(
        event_name="os.remove",
        resource_commitment=_oid("last-durable-slot"),
        reason_code="runtime_effect_not_magic_star_released",
    )

    ledger_summary = ledger.preflight()
    boundary_summary = boundary.public_summary()
    assert ledger_summary["ready"] is False
    assert ledger_summary["reason_code"] == (
        "runtime_intrusion_ledger_capacity_exhausted"
    )
    assert ledger_summary["remaining_violation_capacity"] == 0
    assert boundary_summary["durable_quarantine_evidence_terminal"] is True
    assert boundary_summary["durable_quarantine_evidence_failure_code"] == (
        "runtime_intrusion_ledger_capacity_exhausted"
    )
    assert recorder.terminal_failure_code() == (
        "runtime_intrusion_ledger_capacity_exhausted"
    )
    with pytest.raises(RuntimeGuardError) as raised:
        recorder.record(
            event_name="os.remove",
            resource_commitment=_oid("after-durable-terminal"),
            reason_code="runtime_effect_not_magic_star_released",
        )
    assert raised.value.code == "runtime_intrusion_ledger_capacity_exhausted"
    assert len(recorder.receipts()) == 1
    ledger.close()


class _ToggleAppendFailureSink:
    def __init__(self, delegate: SQLiteRuntimeIntrusionLedgerV04) -> None:
        self.delegate = delegate
        self.fail_appends = False

    def preflight(self) -> Mapping[str, Any]:
        return self.delegate.preflight()

    def seal_for_runtime_guard(self, owner_token: str) -> Mapping[str, Any]:
        return self.delegate.seal_for_runtime_guard(owner_token)

    def validate_runtime_guard_seal(
        self,
        owner_token: str,
        lifecycle_generation: int,
    ) -> Mapping[str, Any]:
        return self.delegate.validate_runtime_guard_seal(
            owner_token,
            lifecycle_generation,
        )

    def runtime_guard_lifecycle_lease(
        self,
        owner_token: str,
        lifecycle_generation: int,
    ) -> AbstractContextManager[Mapping[str, Any]]:
        return self.delegate.runtime_guard_lifecycle_lease(
            owner_token,
            lifecycle_generation,
        )

    def append_violation(
        self,
        *,
        intrusion_id: str,
        runtime_metadata: Mapping[str, Any],
        quarantine_summary: Mapping[str, Any],
        hnc_packet: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if self.fail_appends:
            raise OSError("simulated durable sink failure")
        return self.delegate.append_violation(
            intrusion_id=intrusion_id,
            runtime_metadata=runtime_metadata,
            quarantine_summary=quarantine_summary,
            hnc_packet=hnc_packet,
        )


class _ToggleReceiptSequenceTamperSink(_ToggleAppendFailureSink):
    def __init__(self, delegate: SQLiteRuntimeIntrusionLedgerV04) -> None:
        super().__init__(delegate)
        self.tamper_receipt = False

    def append_violation(
        self,
        *,
        intrusion_id: str,
        runtime_metadata: Mapping[str, Any],
        quarantine_summary: Mapping[str, Any],
        hnc_packet: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        receipt = dict(
            super().append_violation(
                intrusion_id=intrusion_id,
                runtime_metadata=runtime_metadata,
                quarantine_summary=quarantine_summary,
                hnc_packet=hnc_packet,
            )
        )
        if self.tamper_receipt:
            receipt["sequence"] = int(receipt["sequence"]) + 1
        return receipt


def test_boundary_terminals_on_durable_receipt_sequence_join_mismatch(
    tmp_path: Path,
) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "receipt-sequence-tamper.sqlite3").resolve(),
        ledger_id="runtime-guard-receipt-sequence-tamper",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    sink = _ToggleReceiptSequenceTamperSink(ledger)
    boundary = LocalOSProtectionBoundary(
        boundary_id="runtime-guard-receipt-sequence-tamper",
        master_key_provider=lambda: MASTER_KEY,
        max_quarantine_evidence=2,
        quarantine_evidence_sink=sink,
    )
    recorder = HNCRuntimeViolationRecorderV04(
        boundary=boundary,
        max_receipts=1,
        require_durable_evidence=True,
    )
    assert recorder.preflight()["ready"] is True
    sink.tamper_receipt = True
    payload, operator_aad = _runtime_violation_material(
        label="receipt-sequence-tamper",
        sequence=2,
    )

    with pytest.raises(OSProtectionError) as raised:
        boundary.admit_external(
            payload,
            source_id="aureon:runtime-guard-v04",
            ingress_kind="runtime-effect-violation",
            purpose=RUNTIME_INTRUSION_PURPOSE,
            operator_aad=operator_aad,
            content_validator=lambda _view: False,
        )
    assert raised.value.code == "durable_quarantine_evidence_append_failed"
    summary = boundary.public_summary()
    assert summary["durable_quarantine_evidence_terminal"] is True
    assert summary["durable_quarantine_evidence_failure_code"] == (
        "durable_quarantine_evidence_readback_invalid"
    )
    ledger.close()


def test_durable_terminal_blocks_valid_admission_and_magic_star_release(
    tmp_path: Path,
) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "terminal-admission-release.sqlite3").resolve(),
        ledger_id="terminal-admission-release",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=1,
    )
    boundary = LocalOSProtectionBoundary(
        boundary_id="terminal-admission-release",
        master_key_provider=lambda: MASTER_KEY,
        max_quarantine_evidence=3,
        quarantine_evidence_sink=ledger,
    )
    initial = boundary.durable_quarantine_evidence_preflight()
    assert initial["ready"] is True
    assert initial["encrypted_hnc_packets_persisted"] is False
    admitted = boundary.admit_external(
        b"admitted-before-terminal",
        source_id="terminal-admission-release:admitted",
        ingress_kind="document/octet-stream",
        purpose="terminal-admission-release",
        content_validator=lambda _view: True,
    )
    assert isinstance(admitted, AdmittedHNC)
    payload, operator_aad = _runtime_violation_material(
        label="terminal-admission-release",
        sequence=1,
    )
    quarantined = boundary.admit_external(
        payload,
        source_id="aureon:runtime-guard-v04",
        ingress_kind="runtime-effect-violation",
        purpose=RUNTIME_INTRUSION_PURPOSE,
        operator_aad=operator_aad,
        content_validator=lambda _view: False,
    )
    assert isinstance(quarantined, QuarantinedHNC)
    assert boundary.public_summary()["durable_quarantine_evidence_terminal"] is True

    with pytest.raises(OSProtectionError):
        boundary.admit_external(
            b"must-not-admit-after-terminal",
            source_id="terminal-admission-release:after-terminal",
            ingress_kind="document/octet-stream",
            purpose="terminal-admission-release",
            content_validator=lambda _view: True,
        )
    custody = object.__new__(LocalDevelopmentStarCustodyV02)
    with pytest.raises(OSProtectionError):
        boundary.protect_for_magic_star(
            admitted.handle,
            custody=custody,
            release_context_sha256=_oid("terminal-release-context"),
        )
    assert boundary.public_summary()["active_opaque_handle_count"] == 1
    ledger.close()


def test_inflight_admission_cannot_commit_after_completed_terminal(
    tmp_path: Path,
) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "inflight-admission-terminal.sqlite3").resolve(),
        ledger_id="inflight-admission-terminal",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=1,
    )
    boundary = LocalOSProtectionBoundary(
        boundary_id="inflight-admission-terminal",
        master_key_provider=lambda: MASTER_KEY,
        max_quarantine_evidence=3,
        quarantine_evidence_sink=ledger,
    )
    validator_entered = threading.Event()
    release_validator = threading.Event()

    def blocking_validator(_view: memoryview) -> bool:
        validator_entered.set()
        assert release_validator.wait(5)
        return True

    def admit_valid() -> AdmittedHNC | QuarantinedHNC:
        return boundary.admit_external(
            b"valid-but-inflight-at-terminal",
            source_id="inflight-admission-terminal:valid",
            ingress_kind="document/octet-stream",
            purpose="inflight-admission-terminal",
            content_validator=blocking_validator,
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(admit_valid)
        assert validator_entered.wait(5)
        _record_terminal_runtime_violation(boundary, label="inflight-admission")
        assert boundary.public_summary()[
            "durable_quarantine_evidence_terminal"
        ] is True
        release_validator.set()
        with pytest.raises(OSProtectionError) as raised:
            future.result(timeout=5)
    assert raised.value.code == "durable_quarantine_evidence_terminal"
    assert boundary.public_summary()["active_opaque_handle_count"] == 0
    ledger.close()


def test_inflight_magic_star_custody_cannot_return_after_completed_terminal(
    tmp_path: Path,
) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "inflight-magic-star-terminal.sqlite3").resolve(),
        ledger_id="inflight-magic-star-terminal",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=1,
    )
    boundary = LocalOSProtectionBoundary(
        boundary_id="inflight-magic-star-terminal",
        master_key_provider=lambda: MASTER_KEY,
        max_quarantine_evidence=3,
        quarantine_evidence_sink=ledger,
    )
    admitted = boundary.admit_external(
        b"magic-star-inflight-at-terminal",
        source_id="inflight-magic-star-terminal:valid",
        ingress_kind="document/octet-stream",
        purpose="inflight-magic-star-terminal",
        content_validator=lambda _view: True,
    )
    assert isinstance(admitted, AdmittedHNC)
    custody_entered = threading.Event()
    release_custody = threading.Event()

    class BlockingCustody(LocalDevelopmentStarCustodyV02):
        def protect_carrier(self, **_kwargs: Any) -> ProtectedMagicStarPacketV02:
            custody_entered.set()
            assert release_custody.wait(5)
            return object.__new__(ProtectedMagicStarPacketV02)

    custody = object.__new__(BlockingCustody)

    def protect() -> ProtectedMagicStarPacketV02:
        return boundary.protect_for_magic_star(
            admitted.handle,
            custody=custody,
            release_context_sha256=_oid("inflight-magic-star:release"),
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(protect)
        assert custody_entered.wait(5)
        _record_terminal_runtime_violation(boundary, label="inflight-magic-star")
        assert boundary.public_summary()[
            "durable_quarantine_evidence_terminal"
        ] is True
        release_custody.set()
        with pytest.raises(OSProtectionError) as raised:
            future.result(timeout=5)
    assert raised.value.code == "durable_quarantine_evidence_terminal"
    assert boundary.public_summary()["active_opaque_handle_count"] == 0
    ledger.close()


def test_sink_append_failure_terminals_guard_before_future_handler(
    tmp_path: Path,
) -> None:
    path = tmp_path / "runtime-intrusions.sqlite3"
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path.resolve(),
        ledger_id="runtime-guard-append-failure",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    sink = _ToggleAppendFailureSink(ledger)
    boundary = LocalOSProtectionBoundary(
        boundary_id="runtime-guard-append-failure",
        master_key_provider=lambda: MASTER_KEY,
        max_quarantine_evidence=2,
        quarantine_evidence_sink=sink,
    )
    recorder = HNCRuntimeViolationRecorderV04(
        boundary=boundary,
        max_receipts=1,
        require_durable_evidence=True,
    )
    assert recorder.preflight()["ready"] is True

    handler_calls: list[str] = []
    capability_id = _oid("append-failure-capability")
    guard = RuntimeAuditGuardV04(
        verifier=_verifier(),
        recorder=recorder,
        runtime_measurement_sha256=_oid("append-failure-runtime"),
        capabilities={
            capability_id: GuardedRuntimeCapabilityV04(
                capability_id=capability_id,
                capability_measurement_sha256=_oid("append-failure-measurement"),
                handler=lambda: handler_calls.append("called"),
            )
        },
    )
    sink.fail_appends = True

    guard._record_violation(
        event_name="os.remove",
        resource_commitment=_oid("append-failure-resource"),
        permit=None,
    )

    summary = guard.public_summary()
    assert summary["evidence_terminal"] is True
    assert summary["evidence_failure_count"] == 1
    assert recorder.terminal_failure_code() == (
        "runtime_intrusion_evidence_recording_failed"
    )
    assert boundary.public_summary()["durable_quarantine_evidence_terminal"] is True
    assert ledger.preflight()["violation_count"] == 1
    with pytest.raises(RuntimeGuardError) as raised:
        guard.execute_released(b"not-a-command", b"not-a-review", b"not-a-dispatch", b"not-a-manifest")
    assert raised.value.code == "runtime_intrusion_evidence_terminal"
    assert handler_calls == []
    ledger.close()
