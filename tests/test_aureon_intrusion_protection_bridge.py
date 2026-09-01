from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from types import MethodType
from typing import Any, cast

import pytest

import aureon.autonomous.aureon_internal_self_coder as self_coder_module
import aureon.plumber.runtime_intrusion_ledger_v04 as ledger_module
from aureon.autonomous.aureon_internal_work_ledger import DurableInternalWorkLedger
from aureon.autonomous.aureon_intrusion_protection_bridge import (
    INTRUSION_PROTECTION_OWNER_ROUTE,
    INTRUSION_PROTECTION_PROPOSAL_OWNER,
    INTRUSION_PROTECTION_PROPOSAL_SCHEMA,
    AureonIntrusionProtectionWorkProposalV04,
    IntrusionProtectionBridgeError,
    build_runtime_intrusion_protection_proposal_v04,
)
from aureon.plumber.crypto import canonical_json_bytes, domain_hash
from aureon.plumber.os_protection import (
    OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
    LocalOSProtectionBoundary,
    QuarantinedHNC,
)
from aureon.plumber.production_release_broker_v03 import ProductionReleaseBrokerV03
from aureon.plumber.proposal_forge import LocalProposalForge
from aureon.plumber.runtime_intrusion_ledger_v04 import (
    RuntimeIntrusionLedgerError,
    SQLiteRuntimeIntrusionLedgerV04,
)
from aureon.plumber.star_custody_v02 import LocalDevelopmentStarCustodyV02

MASTER_KEY = b"runtime-intrusion-protection-bridge-test-key"
NOW = datetime(2037, 8, 9, 10, 11, 12, tzinfo=UTC)
REASON = "runtime_effect_not_magic_star_released"
PLAINTEXT_CANARY = "hostile intrusion says import os and delete everything"


def _runtime_content(caller_aad: dict[str, Any]) -> bytes:
    return canonical_json_bytes(
        {
            "schema": "aureon.plumber.runtime-intrusion.v04",
            "sequence": 1,
            "event_name": caller_aad["event_name"],
            "resource_commitment": caller_aad["resource_commitment"],
            "reason_code": caller_aad["reason_code"],
            "raw_arguments_retained": False,
            "audit_event_origin_attested": False,
            "effect_attempt_attested": False,
            "resource_commitment_confidentiality_attested": False,
            "resource_commitments_keyed": False,
            "action_eligible": False,
            "economic_eligible": False,
            "production_ready": False,
        }
    )


def _quarantined_event(
    *,
    ledger_instance_commitment: str,
    event_name: str = "os.remove",
    reason_code: str = REASON,
) -> tuple[QuarantinedHNC, dict[str, Any], str]:
    resource_commitment = hashlib.sha256(PLAINTEXT_CANARY.encode()).hexdigest()
    caller_aad = {
        "event_name": event_name,
        "resource_commitment": resource_commitment,
        "reason_code": reason_code,
    }
    boundary = LocalOSProtectionBoundary(
        boundary_id="intrusion-protection-bridge-test-boundary",
        master_key_provider=lambda: MASTER_KEY,
        max_ingress_bytes=1,
        trusted_now=lambda: NOW,
    )
    boundary._durable_evidence_ledger_instance_commitment = (
        ledger_instance_commitment
    )
    outcome = boundary.admit_external(
        _runtime_content(caller_aad),
        source_id="aureon:runtime-guard-v04",
        ingress_kind="runtime-effect-violation",
        purpose="aureon.plumber.runtime-intrusion-quarantine.v04",
        operator_aad=caller_aad,
    )
    assert isinstance(outcome, QuarantinedHNC)
    packet = dict(boundary._quarantine_packets[outcome.admission_id])
    return outcome, packet, resource_commitment


def _runtime_metadata(outcome: QuarantinedHNC) -> dict[str, Any]:
    return {
        "schema": OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
        "intrusion_id": outcome.admission_id,
        "content_sha256": outcome.content_sha256,
        "source_id_sha256": hashlib.sha256(outcome.source_id.encode()).hexdigest(),
        "ingress_kind_sha256": hashlib.sha256(outcome.ingress_kind.encode()).hexdigest(),
        "denial_code_count": len(outcome.denial_codes),
        "raw_arguments_retained": False,
        "plaintext_retained": False,
        "action_eligible": False,
        "economic_eligible": False,
        "production_ready": False,
    }


def _ledger_with_violation(
    path: Path,
) -> tuple[SQLiteRuntimeIntrusionLedgerV04, dict[str, Any], QuarantinedHNC, str]:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path.resolve(),
        ledger_id="aureon-intrusion-protection-bridge",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=8,
    )
    outcome, packet, resource_commitment = _quarantined_event(
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        )
    )
    receipt = ledger.append_violation(
        intrusion_id=outcome.admission_id,
        runtime_metadata=_runtime_metadata(outcome),
        quarantine_summary=outcome.public_summary(),
        hnc_packet=packet,
    )
    return ledger, receipt, outcome, resource_commitment


def test_builds_commitment_only_aureon_owned_hold_without_plaintext(
    tmp_path: Path,
) -> None:
    ledger, receipt, outcome, resource_commitment = _ledger_with_violation(tmp_path / "intrusions.sqlite3")
    before = ledger.preflight()

    proposal = build_runtime_intrusion_protection_proposal_v04(
        ledger=ledger,
        sequence=int(receipt["sequence"]),
        entry_commitment=str(receipt["entry_commitment"]),
    )
    summary = proposal.public_summary()
    after = ledger.preflight()

    assert summary["schema"] == INTRUSION_PROTECTION_PROPOSAL_SCHEMA
    assert summary["proposal_owner"] == INTRUSION_PROTECTION_PROPOSAL_OWNER
    assert summary["owner_route"] == INTRUSION_PROTECTION_OWNER_ROUTE
    assert summary["disposition"] == "HOLD"
    assert summary["review_required"] is True
    assert summary["commitment_only"] is True
    assert summary["intrusion_evidence"]["event_name"] == "os.remove"
    assert summary["intrusion_evidence"]["reason_code"] == REASON
    assert summary["intrusion_evidence"]["keyed_chain_authenticated"] is True
    assert summary["intrusion_evidence"]["hnc_packet_authenticated"] is True
    assert (
        summary["intrusion_evidence"]["ledger_instance_commitment"]
        == before["ledger_instance_commitment"]
    )
    for field in (
        "duplicate_queue_created",
        "proposal_persisted",
        "work_ledger_appended",
        "proposal_forge_invoked",
        "source_request_generated",
        "code_generation_invoked",
        "target_path_present",
        "unified_diff_present",
        "patch_applied",
        "repository_mutation_authorized",
        "release_broker_invoked",
        "magic_star_invoked",
        "external_action_authorized",
        "action_eligible",
        "economic_eligible",
        "production_ready",
    ):
        assert summary[field] is False
    encoded = json.dumps(summary, sort_keys=True)
    assert PLAINTEXT_CANARY not in encoded
    assert outcome.admission_id not in encoded
    assert resource_commitment not in encoded
    assert before["entry_count"] == after["entry_count"]
    assert before["violation_count"] == after["violation_count"]
    ledger.close()


def test_replay_is_idempotent_and_creates_no_duplicate_queue(tmp_path: Path) -> None:
    ledger, receipt, _outcome, _resource = _ledger_with_violation(tmp_path / "replay.sqlite3")
    before = ledger.preflight()
    first = build_runtime_intrusion_protection_proposal_v04(
        ledger=ledger,
        sequence=int(receipt["sequence"]),
        entry_commitment=str(receipt["entry_commitment"]),
    )
    later_outcome, later_packet, _later_resource = _quarantined_event(
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        ),
        event_name="os.rmdir",
    )
    ledger.append_violation(
        intrusion_id=later_outcome.admission_id,
        runtime_metadata=_runtime_metadata(later_outcome),
        quarantine_summary=later_outcome.public_summary(),
        hnc_packet=later_packet,
    )
    after_later_append = ledger.preflight()
    second = build_runtime_intrusion_protection_proposal_v04(
        ledger=ledger,
        sequence=int(receipt["sequence"]),
        entry_commitment=str(receipt["entry_commitment"]),
    )
    after = ledger.preflight()

    assert first.public_summary() == second.public_summary()
    assert first.proposal_id == second.proposal_id
    assert first.proposal_commitment == second.proposal_commitment
    assert first.public_summary()["duplicate_queue_created"] is False
    assert after_later_append["entry_count"] == before["entry_count"] + 1
    assert after["entry_count"] == after_later_append["entry_count"]
    ledger.close()


def test_batched_authenticated_projections_match_exact_single_reads(
    tmp_path: Path,
) -> None:
    ledger, first_receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "batched-projections.sqlite3"
    )
    ledger_instance = str(ledger.preflight()["ledger_instance_commitment"])
    later_outcome, later_packet, _later_resource = _quarantined_event(
        ledger_instance_commitment=ledger_instance,
        event_name="os.mkdir",
    )
    later_receipt = ledger.append_violation(
        intrusion_id=later_outcome.admission_id,
        runtime_metadata=_runtime_metadata(later_outcome),
        quarantine_summary=later_outcome.public_summary(),
        hnc_packet=later_packet,
    )
    selections = (
        (int(first_receipt["sequence"]), str(first_receipt["entry_commitment"])),
        (int(later_receipt["sequence"]), str(later_receipt["entry_commitment"])),
    )
    batched = ledger.authenticated_violation_projections(
        selections=selections,
    )
    singles = tuple(
        ledger.authenticated_violation_projection(
            sequence=sequence,
            entry_commitment=commitment,
        )
        for sequence, commitment in selections
    )
    assert batched == singles
    assert [projection["event_name"] for projection in batched] == [
        "os.remove",
        "os.mkdir",
    ]
    with pytest.raises(
        RuntimeIntrusionLedgerError,
        match="runtime_intrusion_projection_batch_invalid",
    ):
        ledger.authenticated_violation_projections(
            selections=(selections[0], selections[0]),
        )
    ledger.close()


@pytest.mark.parametrize("projection_route", ("single", "batch"))
def test_projection_helper_global_replacement_is_rejected_before_use(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    projection_route: str,
) -> None:
    ledger, receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / f"projection-helper-{projection_route}.sqlite3"
    )
    called = False

    def forged_projection(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        return {}

    try:
        with monkeypatch.context() as patch:
            patch.setattr(
                ledger_module,
                "_authenticated_projection_from_entry",
                forged_projection,
            )
            with pytest.raises(
                RuntimeIntrusionLedgerError,
                match="runtime_intrusion_projection_code_identity_invalid",
            ):
                if projection_route == "single":
                    ledger.authenticated_violation_projection(
                        sequence=int(receipt["sequence"]),
                        entry_commitment=str(receipt["entry_commitment"]),
                    )
                else:
                    ledger.authenticated_violation_projections(
                        selections=(
                            (
                                int(receipt["sequence"]),
                                str(receipt["entry_commitment"]),
                            ),
                        ),
                    )
        assert called is False
    finally:
        ledger.close()


def test_forged_or_tampered_projection_cannot_enter_the_bridge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, receipt, _outcome, _resource = _ledger_with_violation(tmp_path / "forgery.sqlite3")
    with pytest.raises(
        RuntimeIntrusionLedgerError,
        match="runtime_intrusion_projection_entry_join_invalid",
    ):
        build_runtime_intrusion_protection_proposal_v04(
            ledger=ledger,
            sequence=int(receipt["sequence"]),
            entry_commitment="0" * 64,
        )

    projection = ledger.authenticated_violation_projection(
        sequence=int(receipt["sequence"]),
        entry_commitment=str(receipt["entry_commitment"]),
    )
    # Recompute every unkeyed public hash exactly as an attacker can.  Those
    # hashes remain useful deterministic commitments, but are never accepted as
    # ledger authentication or as a proposal-constructor input.
    forged_projection = dict(projection)
    forged_projection["event_name"] = "os.mkdir"
    forged_projection_core = {
        key: value
        for key, value in forged_projection.items()
        if key != "projection_commitment"
    }
    forged_projection["projection_commitment"] = domain_hash(
        "aureon.plumber.runtime-intrusion-authenticated-projection.v04",
        forged_projection_core,
    )
    valid_proposal = build_runtime_intrusion_protection_proposal_v04(
        ledger=ledger,
        sequence=int(receipt["sequence"]),
        entry_commitment=str(receipt["entry_commitment"]),
    )
    forged_proposal_payload = valid_proposal.commitment_payload()
    forged_proposal_payload["intrusion_evidence"] = forged_projection
    forged_proposal_commitment = domain_hash(
        "aureon.autonomous.intrusion-protection-work-proposal.v04",
        forged_proposal_payload,
    )
    with pytest.raises(TypeError):
        AureonIntrusionProtectionWorkProposalV04(  # type: ignore[call-arg]
            intrusion_evidence=forged_projection,
            proposal_id=f"remediation-{forged_proposal_commitment[:32]}",
            proposal_commitment=forged_proposal_commitment,
        )
    with pytest.raises(
        IntrusionProtectionBridgeError,
        match="exact_runtime_intrusion_ledger_required",
    ):
        AureonIntrusionProtectionWorkProposalV04(
            ledger=cast(Any, forged_projection),
            sequence=int(receipt["sequence"]),
            entry_commitment=str(receipt["entry_commitment"]),
        )

    class ForgedLedger:
        pass

    with pytest.raises(
        IntrusionProtectionBridgeError,
        match="exact_runtime_intrusion_ledger_required",
    ):
        build_runtime_intrusion_protection_proposal_v04(
            ledger=cast(Any, ForgedLedger()),
            sequence=int(receipt["sequence"]),
            entry_commitment=str(receipt["entry_commitment"]),
        )

    monkeypatch.setattr(
        SQLiteRuntimeIntrusionLedgerV04,
        "authenticated_violation_projection",
        lambda *_args, **_kwargs: forged_projection,
    )
    with pytest.raises(
        IntrusionProtectionBridgeError,
        match="runtime_intrusion_ledger_code_identity_invalid",
    ):
        build_runtime_intrusion_protection_proposal_v04(
            ledger=ledger,
            sequence=int(receipt["sequence"]),
            entry_commitment=str(receipt["entry_commitment"]),
        )
    ledger.close()


def test_same_function_object_with_replaced_bytecode_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "bytecode-forgery.sqlite3"
    )
    exact_method = SQLiteRuntimeIntrusionLedgerV04.authenticated_violation_projection

    def forged_method(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("forged ledger method must never be called")

    monkeypatch.setattr(exact_method, "__code__", forged_method.__code__)
    assert SQLiteRuntimeIntrusionLedgerV04.authenticated_violation_projection is exact_method
    with pytest.raises(
        IntrusionProtectionBridgeError,
        match="runtime_intrusion_ledger_code_identity_invalid",
    ):
        build_runtime_intrusion_protection_proposal_v04(
            ledger=ledger,
            sequence=int(receipt["sequence"]),
            entry_commitment=str(receipt["entry_commitment"]),
        )
    ledger.close()


def test_source_authentication_instance_shadow_is_rejected(
    tmp_path: Path,
) -> None:
    ledger, receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "instance-shadow.sqlite3"
    )
    called = False

    def forged_entries(_self: Any) -> list[dict[str, Any]]:
        nonlocal called
        called = True
        return []

    ledger._validated_entries = MethodType(forged_entries, ledger)  # type: ignore[method-assign]
    with pytest.raises(
        IntrusionProtectionBridgeError,
        match="runtime_intrusion_ledger_code_identity_invalid",
    ):
        build_runtime_intrusion_protection_proposal_v04(
            ledger=ledger,
            sequence=int(receipt["sequence"]),
            entry_commitment=str(receipt["entry_commitment"]),
        )
    assert called is False
    ledger.close()


def test_source_class_getattribute_interception_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, receipt, _outcome, _resource = _ledger_with_violation(
        tmp_path / "getattribute-shadow.sqlite3"
    )
    called = False

    def hostile_getattribute(self: Any, name: str) -> Any:
        nonlocal called
        called = True
        return object.__getattribute__(self, name)

    with monkeypatch.context() as patch:
        patch.setattr(
            SQLiteRuntimeIntrusionLedgerV04,
            "__getattribute__",
            hostile_getattribute,
            raising=False,
        )
        with pytest.raises(
            IntrusionProtectionBridgeError,
            match="runtime_intrusion_ledger_code_identity_invalid",
        ):
            build_runtime_intrusion_protection_proposal_v04(
                ledger=ledger,
                sequence=int(receipt["sequence"]),
                entry_commitment=str(receipt["entry_commitment"]),
            )
    assert called is False
    ledger.close()


@pytest.mark.parametrize(
    ("event_name", "reason_code"),
    [
        ("attacker.unsupported", REASON),
        ("os.remove", "attacker_selected_reason"),
    ],
)
def test_wrong_event_or_reason_cannot_become_authenticated_work(
    tmp_path: Path,
    event_name: str,
    reason_code: str,
) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / f"wrong-{hashlib.sha256(event_name.encode()).hexdigest()}.sqlite3").resolve(),
        ledger_id="aureon-intrusion-protection-wrong-route",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=4,
    )
    outcome, packet, _resource = _quarantined_event(
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        ),
        event_name=event_name,
        reason_code=reason_code,
    )
    with pytest.raises(
        RuntimeIntrusionLedgerError,
        match="runtime_intrusion_hnc_authentication_invalid",
    ):
        ledger.append_violation(
            intrusion_id=outcome.admission_id,
            runtime_metadata=_runtime_metadata(outcome),
            quarantine_summary=outcome.public_summary(),
            hnc_packet=packet,
        )
    stored = ledger._connection.execute(
        "SELECT COUNT(*) FROM runtime_intrusion_entries_v04 WHERE entry_kind='VIOLATION'"
    ).fetchone()
    assert stored == (0,)
    ledger.close()


def test_schema_tamper_fails_before_proposal_construction(tmp_path: Path) -> None:
    ledger, receipt, _outcome, _resource = _ledger_with_violation(tmp_path / "tamper.sqlite3")
    ledger._connection.execute("DROP INDEX runtime_intrusion_entries_v04_commitment_uq")
    with pytest.raises(
        RuntimeIntrusionLedgerError,
        match="runtime_intrusion_ledger_schema_invalid",
    ):
        build_runtime_intrusion_protection_proposal_v04(
            ledger=ledger,
            sequence=int(receipt["sequence"]),
            entry_commitment=str(receipt["entry_commitment"]),
        )
    ledger.close()


def test_bridge_never_invokes_downstream_authorities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger, receipt, _outcome, _resource = _ledger_with_violation(tmp_path / "no-downstream.sqlite3")
    calls: list[str] = []

    def forbidden(label: str):
        def reject(*_args: Any, **_kwargs: Any) -> None:
            calls.append(label)
            raise AssertionError(label)

        return reject

    monkeypatch.setattr(LocalProposalForge, "forge_proposal", forbidden("forge"))
    monkeypatch.setattr(DurableInternalWorkLedger, "append", forbidden("ledger"))
    monkeypatch.setattr(
        self_coder_module,
        "run_autonomous_self_coding",
        forbidden("codegen"),
    )
    monkeypatch.setattr(
        ProductionReleaseBrokerV03,
        "execute_release",
        forbidden("release-broker"),
    )
    monkeypatch.setattr(
        LocalDevelopmentStarCustodyV02,
        "release_to_capability",
        forbidden("magic-star-custody"),
    )

    proposal = build_runtime_intrusion_protection_proposal_v04(
        ledger=ledger,
        sequence=int(receipt["sequence"]),
        entry_commitment=str(receipt["entry_commitment"]),
    )
    assert calls == []
    assert proposal.public_summary()["disposition"] == "HOLD"
    ledger.close()
