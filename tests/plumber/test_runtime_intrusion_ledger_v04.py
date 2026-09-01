from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from aureon.plumber.crypto import canonical_json_bytes, domain_hash
from aureon.plumber.os_protection import (
    OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
    LocalOSProtectionBoundary,
    QuarantinedHNC,
)
from aureon.plumber.packet import bind_hnc_packet
from aureon.plumber.runtime_intrusion_ledger_v04 import (
    RUNTIME_INTRUSION_ENTRY_SCHEMA,
    RUNTIME_INTRUSION_LEDGER_SCHEMA,
    RuntimeIntrusionLedgerError,
    SQLiteRuntimeIntrusionLedgerV04,
)

NOW = datetime(2035, 6, 7, 8, 9, 10, tzinfo=UTC)
MASTER_KEY = b"runtime-intrusion-ledger-test-key"
PLAINTEXT_CANARY = b"never-persist-this-runtime-intrusion-canary"
RUNTIME_METADATA_PLAINTEXT_CANARY = "never-persist-this-runtime-metadata-canary"


def _runtime_violation_content(
    caller_aad: dict[str, Any],
    *,
    recorder_sequence: int = 1,
) -> bytes:
    return canonical_json_bytes(
        {
            "schema": "aureon.plumber.runtime-intrusion.v04",
            "sequence": recorder_sequence,
            "event_name": caller_aad.get("event_name"),
            "resource_commitment": caller_aad.get("resource_commitment"),
            "reason_code": caller_aad.get("reason_code"),
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


def _quarantined_hnc(
    raw: bytes | None = None,
    *,
    ledger_instance_commitment: str,
    source_id: str = "aureon:runtime-guard-v04",
    ingress_kind: str = "runtime-effect-violation",
    purpose: str = "aureon.plumber.runtime-intrusion-quarantine.v04",
    operator_aad: dict[str, Any] | None = None,
    recorder_sequence: int = 1,
) -> tuple[QuarantinedHNC, dict[str, Any]]:
    caller_aad = (
        dict(operator_aad)
        if operator_aad is not None
        else {
            "event_name": "os.remove",
            "resource_commitment": "a" * 64,
            "reason_code": "runtime_effect_not_magic_star_released",
        }
    )
    if raw is None:
        raw = _runtime_violation_content(
            caller_aad,
            recorder_sequence=recorder_sequence,
        )
    boundary = LocalOSProtectionBoundary(
        boundary_id="runtime-intrusion-ledger-test-boundary",
        master_key_provider=lambda: MASTER_KEY,
        max_ingress_bytes=1,
        trusted_now=lambda: NOW,
    )
    # Unit-test packet construction is intentionally detached from persistence;
    # bind it to the exact already-created ledger instance before sealing.
    boundary._durable_evidence_ledger_instance_commitment = (
        ledger_instance_commitment
    )
    outcome = boundary.admit_external(
        raw,
        source_id=source_id,
        ingress_kind=ingress_kind,
        purpose=purpose,
        operator_aad=caller_aad,
    )
    assert isinstance(outcome, QuarantinedHNC)
    assert outcome.hnc_evidence_binding is not None
    return outcome, dict(boundary._quarantine_packets[outcome.admission_id])


def _metadata(event_id: str, outcome: QuarantinedHNC) -> dict[str, Any]:
    assert event_id
    return _os_boundary_metadata(outcome)


def _os_boundary_metadata(outcome: QuarantinedHNC) -> dict[str, Any]:
    return {
        "schema": OS_DURABLE_QUARANTINE_EVIDENCE_SCHEMA,
        "intrusion_id": outcome.admission_id,
        "content_sha256": outcome.content_sha256,
        "source_id_sha256": hashlib.sha256(outcome.source_id.encode()).hexdigest(),
        "ingress_kind_sha256": hashlib.sha256(
            outcome.ingress_kind.encode()
        ).hexdigest(),
        "denial_code_count": len(outcome.denial_codes),
        "raw_arguments_retained": False,
        "plaintext_retained": False,
        "action_eligible": False,
        "economic_eligible": False,
        "production_ready": False,
    }


def _append_one(
    ledger: SQLiteRuntimeIntrusionLedgerV04,
    *,
    event_id: str = "event-1",
) -> tuple[QuarantinedHNC, dict[str, Any], dict[str, Any]]:
    outcome, packet = _quarantined_hnc(
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        )
    )
    receipt = ledger.append_violation(
        intrusion_id=outcome.admission_id,
        runtime_metadata=_metadata(event_id, outcome),
        quarantine_summary=outcome.public_summary(),
        hnc_packet=packet,
    )
    return outcome, packet, receipt


def test_initialization_creates_one_durable_preflight_entry(tmp_path: Path) -> None:
    path = (tmp_path / "intrusions.sqlite3").resolve()

    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="initialization-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    summary = ledger.preflight()

    assert summary == {
        "schema": RUNTIME_INTRUSION_LEDGER_SCHEMA,
        "ledger_id": "initialization-test",
        "ledger_instance_commitment": summary["ledger_instance_commitment"],
        "ready": True,
        "reason_code": "ready",
        "entry_count": 1,
        "violation_count": 0,
        "max_violation_entries": 3,
        "remaining_violation_capacity": 3,
        "preopened_connection": True,
        "append_only_schema": True,
        "durability_readback": True,
        "keyed_genesis_authentication_ready": True,
        "keyed_entry_authentication_ready": True,
        "keyed_entries_authenticated": True,
        "quarantine_hnc_authentication_ready": True,
        "encrypted_hnc_packet_persistence_ready": True,
        "encrypted_hnc_packets_persisted": False,
        "encrypted_hnc_packets_authenticated": False,
        "raw_arguments_retained": False,
        "external_head_anchor_attested": False,
        "magic_star_durable_custody_attested": False,
        "production_ready": False,
    }
    assert ledger._connection.execute("PRAGMA journal_mode").fetchone() == ("wal",)
    assert ledger._connection.execute("PRAGMA synchronous").fetchone() == (2,)
    assert ledger._connection.execute("PRAGMA foreign_keys").fetchone() == (1,)
    row = ledger._connection.execute(
        "SELECT sequence, entry_kind, previous_entry_commitment, terminal_after_append "
        "FROM runtime_intrusion_entries_v04"
    ).fetchone()
    assert row == (1, "PREFLIGHT", "0" * 64, 0)
    metadata_instance = ledger._connection.execute(
        "SELECT ledger_instance_commitment "
        "FROM runtime_intrusion_metadata_v04 WHERE singleton = 1"
    ).fetchone()
    assert metadata_instance == (summary["ledger_instance_commitment"],)
    with pytest.raises(sqlite3.IntegrityError, match="metadata_immutable"):
        ledger._connection.execute(
            "UPDATE runtime_intrusion_metadata_v04 "
            "SET ledger_instance_commitment = ? WHERE singleton = 1",
            ("f" * 64,),
        )
    ledger.close()

    reopened = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="initialization-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    assert reopened.preflight()["entry_count"] == 1
    assert (
        reopened.preflight()["ledger_instance_commitment"]
        == summary["ledger_instance_commitment"]
    )
    reopened.close()


def test_key_provider_is_opened_once_and_retained_copy_is_wiped_on_close(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "key-lifetime.sqlite3").resolve()
    provider_calls: list[str] = []

    def provider() -> bytes:
        provider_calls.append("called")
        return MASTER_KEY

    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="key-lifetime-test",
        quarantine_hnc_key_provider=provider,
        max_violation_entries=3,
    )
    retained_key = ledger._quarantine_hnc_key
    retained_auth_key = ledger._ledger_auth_key
    assert bytes(retained_key) == MASTER_KEY
    assert retained_auth_key
    assert bytes(retained_auth_key) != MASTER_KEY
    assert provider_calls == ["called"]

    _outcome, _packet, receipt = _append_one(ledger)
    summary = ledger.preflight()
    assert provider_calls == ["called"]
    assert receipt["hnc_packet_authenticated"] is True
    assert summary["quarantine_hnc_authentication_ready"] is True
    assert summary["encrypted_hnc_packets_authenticated"] is True
    assert MASTER_KEY.decode("ascii") not in json.dumps(summary, sort_keys=True)
    ledger.close()

    assert retained_key
    assert set(retained_key) == {0}
    assert retained_auth_key
    assert set(retained_auth_key) == {0}


def test_wrong_key_rejects_genesis_only_ledger_before_any_violation(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "wrong-key-genesis.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="wrong-key-genesis",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    assert ledger.preflight()["violation_count"] == 0
    ledger.close()

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        SQLiteRuntimeIntrusionLedgerV04(
            path,
            ledger_id="wrong-key-genesis",
            quarantine_hnc_key_provider=lambda: b"wrong-genesis-key" * 2,
            max_violation_entries=3,
        )
    assert raised.value.code == "runtime_intrusion_ledger_authentication_invalid"


def test_reopen_with_wrong_quarantine_key_rejects_stored_violation(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "wrong-key.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="wrong-key-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    _append_one(ledger)
    ledger.close()

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        SQLiteRuntimeIntrusionLedgerV04(
            path,
            ledger_id="wrong-key-test",
            quarantine_hnc_key_provider=lambda: b"x" * 32,
            max_violation_entries=3,
        )
    assert raised.value.code == "runtime_intrusion_ledger_authentication_invalid"


def test_valid_hnc_violation_has_exact_readback_and_restart_chain(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "intrusions.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="restart-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )

    outcome, packet, receipt = _append_one(ledger)
    binding = bind_hnc_packet(packet)

    assert receipt["schema"] == RUNTIME_INTRUSION_ENTRY_SCHEMA
    assert receipt["sequence"] == 2
    assert receipt["intrusion_id"] == outcome.admission_id
    assert receipt["hnc_packet_commitment"] == binding.hnc_packet_commitment
    assert receipt["hnc_binding_commitment"] == binding.binding_commitment
    assert receipt["quarantine_commitment"] == outcome.quarantine_commitment
    assert receipt["durability_readback"] is True
    assert receipt["terminal_after_append"] is False
    ledger.close()

    reopened = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="restart-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    summary = reopened.preflight()
    assert summary["entry_count"] == 2
    assert summary["violation_count"] == 1
    assert summary["remaining_violation_capacity"] == 2
    _, _, second_receipt = _append_one(reopened, event_id="event-2")
    assert second_receipt["sequence"] == 3
    assert second_receipt["previous_entry_commitment"] == receipt["entry_commitment"]
    reopened.close()


def test_same_key_and_ledger_id_cannot_replay_packet_across_ledger_instances(
    tmp_path: Path,
) -> None:
    ledger_a = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "instance-a.sqlite3").resolve(),
        ledger_id="shared-human-ledger-id",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    ledger_b = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "instance-b.sqlite3").resolve(),
        ledger_id="shared-human-ledger-id",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    instance_a = str(ledger_a.preflight()["ledger_instance_commitment"])
    instance_b = str(ledger_b.preflight()["ledger_instance_commitment"])
    assert instance_a != instance_b

    outcome, packet = _quarantined_hnc(
        ledger_instance_commitment=instance_a
    )
    receipt = ledger_a.append_violation(
        intrusion_id=outcome.admission_id,
        runtime_metadata=_os_boundary_metadata(outcome),
        quarantine_summary=outcome.public_summary(),
        hnc_packet=packet,
    )
    assert receipt["ledger_instance_commitment"] == instance_a

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger_b.append_violation(
            intrusion_id=outcome.admission_id,
            runtime_metadata=_os_boundary_metadata(outcome),
            quarantine_summary=outcome.public_summary(),
            hnc_packet=packet,
        )
    assert raised.value.code == "runtime_intrusion_hnc_authentication_invalid"
    assert ledger_b._connection.execute(
        "SELECT COUNT(*) FROM runtime_intrusion_entries_v04 "
        "WHERE entry_kind = 'VIOLATION'"
    ).fetchone() == (0,)
    ledger_a.close()
    ledger_b.close()


def test_final_capacity_append_is_atomic_with_sticky_terminal_marker(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "intrusions.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="capacity-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=1,
    )

    _, _, receipt = _append_one(ledger)

    assert receipt["terminal_after_append"] is True
    terminal_summary = ledger.preflight()
    assert terminal_summary == {
        "schema": RUNTIME_INTRUSION_LEDGER_SCHEMA,
        "ledger_id": "capacity-test",
        "ledger_instance_commitment": terminal_summary[
            "ledger_instance_commitment"
        ],
        "ready": False,
        "reason_code": "runtime_intrusion_ledger_capacity_exhausted",
        "entry_count": 3,
        "violation_count": 1,
        "max_violation_entries": 1,
        "remaining_violation_capacity": 0,
        "preopened_connection": True,
        "append_only_schema": True,
        "durability_readback": True,
        "keyed_genesis_authentication_ready": True,
        "keyed_entry_authentication_ready": True,
        "keyed_entries_authenticated": True,
        "quarantine_hnc_authentication_ready": True,
        "encrypted_hnc_packet_persistence_ready": True,
        "encrypted_hnc_packets_persisted": True,
        "encrypted_hnc_packets_authenticated": True,
        "raw_arguments_retained": False,
        "external_head_anchor_attested": False,
        "magic_star_durable_custody_attested": False,
        "production_ready": False,
    }
    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        _append_one(ledger, event_id="event-after-terminal")
    assert raised.value.code == "runtime_intrusion_ledger_capacity_exhausted"
    ledger.close()

    reopened = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="capacity-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=1,
    )
    assert reopened.preflight()["reason_code"] == (
        "runtime_intrusion_ledger_capacity_exhausted"
    )
    with pytest.raises(RuntimeIntrusionLedgerError) as reopened_raised:
        _append_one(reopened, event_id="event-after-restart")
    assert reopened_raised.value.code == "runtime_intrusion_ledger_capacity_exhausted"
    reopened.close()


def test_reopen_rejects_row_tamper_even_when_expected_trigger_is_restored(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "intrusions.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="row-tamper-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    _append_one(ledger)
    ledger.close()

    connection = sqlite3.connect(path)
    connection.execute("DROP TRIGGER runtime_intrusion_entries_v04_no_update")
    connection.execute(
        "UPDATE runtime_intrusion_entries_v04 SET runtime_metadata_json = ? "
        "WHERE sequence = 2",
        (b'{"event_id":"tampered","raw_material_retained":false,"schema":"x"}',),
    )
    connection.execute(
        """
        CREATE TRIGGER runtime_intrusion_entries_v04_no_update
        BEFORE UPDATE ON runtime_intrusion_entries_v04
        BEGIN
            SELECT RAISE(ABORT, 'runtime_intrusion_append_only');
        END
        """
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        SQLiteRuntimeIntrusionLedgerV04(
            path,
            ledger_id="row-tamper-test",
            quarantine_hnc_key_provider=lambda: MASTER_KEY,
            max_violation_entries=3,
        )
    assert raised.value.code == "runtime_intrusion_entry_authentication_invalid"


def test_reopen_rejects_mutated_full_quarantine_summary_field(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "intrusions.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="quarantine-summary-tamper-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    _append_one(ledger)
    ledger.close()

    connection = sqlite3.connect(path)
    connection.execute("DROP TRIGGER runtime_intrusion_entries_v04_no_update")
    row = connection.execute(
        "SELECT quarantine_summary_json FROM runtime_intrusion_entries_v04 "
        "WHERE sequence = 2"
    ).fetchone()
    assert row is not None
    summary = json.loads(bytes(row[0]))
    summary["source_id"] = "mutated-source-id"
    connection.execute(
        "UPDATE runtime_intrusion_entries_v04 SET quarantine_summary_json = ? "
        "WHERE sequence = 2",
        (canonical_json_bytes(summary),),
    )
    connection.execute(
        """
        CREATE TRIGGER runtime_intrusion_entries_v04_no_update
        BEFORE UPDATE ON runtime_intrusion_entries_v04
        BEGIN
            SELECT RAISE(ABORT, 'runtime_intrusion_append_only');
        END
        """
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        SQLiteRuntimeIntrusionLedgerV04(
            path,
            ledger_id="quarantine-summary-tamper-test",
            quarantine_hnc_key_provider=lambda: MASTER_KEY,
            max_violation_entries=3,
        )
    assert raised.value.code == "runtime_intrusion_entry_authentication_invalid"


def test_authenticated_payload_rejects_full_public_rehash_source_id_forgery(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "full-rehash-source-forgery.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="full-rehash-source-forgery",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    outcome, _packet, _receipt = _append_one(ledger)
    ledger.close()

    connection = sqlite3.connect(path)
    connection.execute("DROP TRIGGER runtime_intrusion_entries_v04_no_update")
    row = connection.execute(
        "SELECT previous_entry_commitment, runtime_metadata_json, "
        "quarantine_summary_json, quarantine_record_commitment, "
        "hnc_packet_sha256, hnc_packet_commitment, hnc_binding_commitment, "
        "terminal_after_append, recorded_at "
        "FROM runtime_intrusion_entries_v04 WHERE sequence = 2"
    ).fetchone()
    assert row is not None
    forged_source_id = "runtime-audit:forged-rehashed-source"
    metadata = json.loads(bytes(row[1]))
    metadata["source_id_sha256"] = hashlib.sha256(
        forged_source_id.encode("utf-8")
    ).hexdigest()
    metadata_bytes = canonical_json_bytes(metadata)
    metadata_sha256 = hashlib.sha256(metadata_bytes).hexdigest()
    summary = json.loads(bytes(row[2]))
    summary["source_id"] = forged_source_id
    commitment_payload = dict(summary)
    commitment_payload.pop("quarantine_commitment")
    quarantine_commitment = domain_hash(
        "aureon.plumber.os-quarantine.v0",
        commitment_payload,
    )
    summary["quarantine_commitment"] = quarantine_commitment
    summary_bytes = canonical_json_bytes(summary)
    causal = {
        "schema": RUNTIME_INTRUSION_ENTRY_SCHEMA,
        "ledger_id": "full-rehash-source-forgery",
        "sequence": 2,
        "entry_kind": "VIOLATION",
        "intrusion_id": outcome.admission_id,
        "previous_entry_commitment": str(row[0]),
        "runtime_metadata_sha256": metadata_sha256,
        "quarantine_commitment": quarantine_commitment,
        "quarantine_record_commitment": str(row[3]),
        "hnc_packet_sha256": str(row[4]),
        "hnc_packet_commitment": str(row[5]),
        "hnc_binding_commitment": str(row[6]),
        "terminal_after_append": row[7] == 1,
        "recorded_at": str(row[8]),
    }
    entry_commitment = domain_hash(
        "aureon.plumber.runtime-intrusion-entry.v04",
        causal,
    )
    connection.execute(
        "UPDATE runtime_intrusion_entries_v04 SET runtime_metadata_json = ?, "
        "runtime_metadata_sha256 = ?, quarantine_summary_json = ?, "
        "quarantine_commitment = ?, entry_commitment = ? WHERE sequence = 2",
        (
            metadata_bytes,
            metadata_sha256,
            summary_bytes,
            quarantine_commitment,
            entry_commitment,
        ),
    )
    connection.execute(
        """
        CREATE TRIGGER runtime_intrusion_entries_v04_no_update
        BEFORE UPDATE ON runtime_intrusion_entries_v04
        BEGIN
            SELECT RAISE(ABORT, 'runtime_intrusion_append_only');
        END
        """
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        SQLiteRuntimeIntrusionLedgerV04(
            path,
            ledger_id="full-rehash-source-forgery",
            quarantine_hnc_key_provider=lambda: MASTER_KEY,
            max_violation_entries=3,
        )
    assert raised.value.code == "runtime_intrusion_entry_authentication_invalid"


@pytest.mark.parametrize("mismatch", ["content_sha256", "denial_code_count"])
def test_os_runtime_metadata_must_exactly_join_quarantine_summary(
    tmp_path: Path,
    mismatch: str,
) -> None:
    path = (tmp_path / f"metadata-{mismatch}.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id=f"metadata-{mismatch}",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    outcome, packet = _quarantined_hnc(
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        )
    )
    metadata = _os_boundary_metadata(outcome)
    metadata[mismatch] = (
        "f" * 64
        if mismatch == "content_sha256"
        else len(outcome.denial_codes) + 1
    )

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger.append_violation(
            intrusion_id=outcome.admission_id,
            runtime_metadata=metadata,
            quarantine_summary=outcome.public_summary(),
            hnc_packet=packet,
        )
    assert raised.value.code == "runtime_intrusion_metadata_join_invalid"
    assert ledger._connection.execute(
        "SELECT COUNT(*) FROM runtime_intrusion_entries_v04"
    ).fetchone() == (1,)
    ledger.close()


def test_runtime_metadata_extra_plaintext_field_is_rejected_before_sqlite_write(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "metadata-plaintext.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="metadata-plaintext-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    outcome, packet = _quarantined_hnc(
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        )
    )
    metadata = _metadata("metadata-plaintext", outcome)
    metadata["diagnostic_note"] = RUNTIME_METADATA_PLAINTEXT_CANARY

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger.append_violation(
            intrusion_id=outcome.admission_id,
            runtime_metadata=metadata,
            quarantine_summary=outcome.public_summary(),
            hnc_packet=packet,
        )
    assert raised.value.code == "runtime_intrusion_metadata_contract_invalid"
    assert ledger._connection.execute(
        "SELECT COUNT(*) FROM runtime_intrusion_entries_v04"
    ).fetchone() == (1,)
    ledger.close()
    for candidate in path.parent.iterdir():
        if candidate.is_file():
            assert RUNTIME_METADATA_PLAINTEXT_CANARY.encode() not in candidate.read_bytes()


@pytest.mark.parametrize(
    ("route_field", "route_value"),
    [
        ("source_id", "attacker:runtime-guard-v04"),
        ("ingress_kind", "runtime-effect-attacker"),
        ("purpose", "attacker.runtime-purpose"),
        ("event_name", "plaintext_canary_event"),
        ("reason_code", "attacker_reason"),
        ("resource_commitment", "not-a-sha256"),
    ],
)
def test_only_exact_runtime_guard_commitment_route_is_durable(
    tmp_path: Path,
    route_field: str,
    route_value: str,
) -> None:
    route = {
        "source_id": "aureon:runtime-guard-v04",
        "ingress_kind": "runtime-effect-violation",
        "purpose": "aureon.plumber.runtime-intrusion-quarantine.v04",
    }
    caller_aad = {
        "event_name": "os.remove",
        "resource_commitment": "a" * 64,
        "reason_code": "runtime_effect_not_magic_star_released",
    }
    if route_field in route:
        route[route_field] = route_value
    else:
        caller_aad[route_field] = route_value
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / f"route-{route_field}.sqlite3").resolve(),
        ledger_id=f"route-{route_field}",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    outcome, packet = _quarantined_hnc(
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        ),
        source_id=route["source_id"],
        ingress_kind=route["ingress_kind"],
        purpose=route["purpose"],
        operator_aad=caller_aad,
    )

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger.append_violation(
            intrusion_id=outcome.admission_id,
            runtime_metadata=_os_boundary_metadata(outcome),
            quarantine_summary=outcome.public_summary(),
            hnc_packet=packet,
        )
    assert raised.value.code == "runtime_intrusion_hnc_authentication_invalid"
    assert ledger._connection.execute(
        "SELECT COUNT(*) FROM runtime_intrusion_entries_v04"
    ).fetchone() == (1,)
    ledger.close()


def test_exact_runtime_guard_preflight_route_is_accepted(tmp_path: Path) -> None:
    probe = canonical_json_bytes(
        {
            "schema": "aureon.plumber.runtime-guard-preflight.v04",
            "probe": "commitment-only-hnc-quarantine",
            "production_ready": False,
        }
    )
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "runtime-preflight-route.sqlite3").resolve(),
        ledger_id="runtime-preflight-route",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    outcome, packet = _quarantined_hnc(
        probe,
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        ),
        ingress_kind="runtime-guard-preflight",
        operator_aad={"preflight": True},
    )
    receipt = ledger.append_violation(
        intrusion_id=outcome.admission_id,
        runtime_metadata=_os_boundary_metadata(outcome),
        quarantine_summary=outcome.public_summary(),
        hnc_packet=packet,
    )
    assert receipt["keyed_entry_authenticated"] is True
    ledger.close()


def test_exact_caller_aad_rejects_unrelated_plaintext_content(tmp_path: Path) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "caller-aad-content-join.sqlite3").resolve(),
        ledger_id="caller-aad-content-join",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    outcome, packet = _quarantined_hnc(
        raw=PLAINTEXT_CANARY,
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        ),
    )

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger.append_violation(
            intrusion_id=outcome.admission_id,
            runtime_metadata=_os_boundary_metadata(outcome),
            quarantine_summary=outcome.public_summary(),
            hnc_packet=packet,
        )
    assert raised.value.code == "runtime_intrusion_hnc_authentication_invalid"
    assert ledger._connection.execute(
        "SELECT COUNT(*) FROM runtime_intrusion_entries_v04"
    ).fetchone() == (1,)
    ledger.close()


@pytest.mark.parametrize(
    "sabotage_sql",
    [
        "PRAGMA synchronous=OFF",
        "PRAGMA foreign_keys=OFF",
        "PRAGMA busy_timeout=7",
        "PRAGMA trusted_schema=ON",
        "PRAGMA query_only=ON",
        "PRAGMA writable_schema=ON",
        "PRAGMA ignore_check_constraints=ON",
    ],
)
def test_every_operation_revalidates_connection_pragmas(
    tmp_path: Path,
    sabotage_sql: str,
) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / f"pragma-{abs(hash(sabotage_sql))}.sqlite3").resolve(),
        ledger_id="pragma-validation",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    ledger._connection.execute(sabotage_sql)

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger.preflight()
    assert raised.value.code == "runtime_intrusion_ledger_durability_pragmas_invalid"
    ledger.close()


def test_exact_schema_census_allows_only_expected_sqlite_autoindexes(
    tmp_path: Path,
) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "internal-census.sqlite3").resolve(),
        ledger_id="internal-census",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    internal = ledger._connection.execute(
        "SELECT type, name, tbl_name, sql FROM sqlite_schema "
        "WHERE name LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    assert internal == [
        (
            "index",
            "sqlite_autoindex_runtime_intrusion_entries_v04_1",
            "runtime_intrusion_entries_v04",
            None,
        ),
        (
            "index",
            "sqlite_autoindex_runtime_intrusion_entries_v04_2",
            "runtime_intrusion_entries_v04",
            None,
        ),
    ]
    assert ledger.preflight()["ready"] is True
    ledger.close()


def test_unexpected_hidden_sqlite_stat_object_is_rejected(tmp_path: Path) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "hidden-sqlite-object.sqlite3").resolve(),
        ledger_id="hidden-sqlite-object",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    ledger._connection.execute("ANALYZE")
    assert ledger._connection.execute(
        "SELECT COUNT(*) FROM sqlite_schema WHERE name = 'sqlite_stat1'"
    ).fetchone() == (1,)

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger.preflight()
    assert raised.value.code == "runtime_intrusion_ledger_schema_invalid"
    ledger.close()


def test_oversized_tampered_blob_is_rejected_before_row_authentication(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "oversized-row.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="oversized-row",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
        max_entry_bytes=1024,
    )
    connection = sqlite3.connect(path)
    trigger_sql = connection.execute(
        "SELECT sql FROM sqlite_schema "
        "WHERE type = 'trigger' AND name = 'runtime_intrusion_entries_v04_no_update'"
    ).fetchone()
    assert trigger_sql is not None and isinstance(trigger_sql[0], str)
    connection.execute("DROP TRIGGER runtime_intrusion_entries_v04_no_update")
    connection.execute(
        "UPDATE runtime_intrusion_entries_v04 SET runtime_metadata_json = zeroblob(1025) "
        "WHERE sequence = 1"
    )
    connection.execute(trigger_sql[0])
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger.preflight()
    assert raised.value.code == "runtime_intrusion_entry_capacity_exceeded"
    ledger.close()


def test_keyed_entry_authentication_rejects_public_row_reorder(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "public-row-reorder.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="public-row-reorder",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=4,
    )
    _append_one(ledger, event_id="reorder-1")
    _append_one(ledger, event_id="reorder-2")
    ledger.close()

    connection = sqlite3.connect(path)
    connection.execute("DROP TRIGGER runtime_intrusion_entries_v04_no_update")
    connection.execute(
        "UPDATE runtime_intrusion_entries_v04 SET sequence = 100 WHERE sequence = 2"
    )
    connection.execute(
        "UPDATE runtime_intrusion_entries_v04 SET sequence = 2 WHERE sequence = 3"
    )
    connection.execute(
        "UPDATE runtime_intrusion_entries_v04 SET sequence = 3 WHERE sequence = 100"
    )
    connection.execute(
        """
        CREATE TRIGGER runtime_intrusion_entries_v04_no_update
        BEFORE UPDATE ON runtime_intrusion_entries_v04
        BEGIN
            SELECT RAISE(ABORT, 'runtime_intrusion_append_only');
        END
        """
    )
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        SQLiteRuntimeIntrusionLedgerV04(
            path,
            ledger_id="public-row-reorder",
            quarantine_hnc_key_provider=lambda: MASTER_KEY,
            max_violation_entries=4,
        )
    assert raised.value.code == "runtime_intrusion_entry_authentication_invalid"


def test_valid_prefix_rollback_remains_explicitly_unattested(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "valid-prefix-rollback.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="valid-prefix-rollback",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=4,
    )
    _append_one(ledger, event_id="prefix-1")
    _append_one(ledger, event_id="prefix-2")
    ledger.close()

    connection = sqlite3.connect(path)
    connection.execute("DROP TRIGGER runtime_intrusion_entries_v04_no_delete")
    connection.execute(
        "DELETE FROM runtime_intrusion_entries_v04 WHERE sequence = 3"
    )
    connection.execute(
        """
        CREATE TRIGGER runtime_intrusion_entries_v04_no_delete
        BEFORE DELETE ON runtime_intrusion_entries_v04
        BEGIN
            SELECT RAISE(ABORT, 'runtime_intrusion_append_only');
        END
        """
    )
    connection.commit()
    connection.close()

    reopened = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="valid-prefix-rollback",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=4,
    )
    summary = reopened.preflight()
    assert summary["ready"] is True
    assert summary["entry_count"] == 2
    assert summary["violation_count"] == 1
    assert summary["external_head_anchor_attested"] is False
    reopened.close()


def test_runtime_guard_seal_is_pinned_and_close_is_rejected(tmp_path: Path) -> None:
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        (tmp_path / "runtime-guard-seal.sqlite3").resolve(),
        ledger_id="runtime-guard-seal",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    owner_token = "runtime-guard-owner-token"
    sealed = ledger.seal_for_runtime_guard(owner_token)
    assert sealed["sealed"] is True
    assert sealed["lifecycle_generation"] == 1
    assert sealed["close_rejected_while_sealed"] is True
    with ledger.runtime_guard_lifecycle_lease(owner_token, 1) as leased:
        assert leased["owner_token_sha256"] == sealed["owner_token_sha256"]
        assert leased["ready"] is True
    assert ledger.validate_runtime_guard_seal(owner_token, 1)["ready"] is True

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger.close()
    assert raised.value.code == "runtime_intrusion_ledger_runtime_guard_sealed"
    ledger._connection.close()
    ledger._wipe_retained_keys()
    ledger._closed = True


def test_runtime_guard_lifecycle_lease_blocks_external_ddl(tmp_path: Path) -> None:
    path = (tmp_path / "runtime-guard-lease-ddl.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="runtime-guard-lease-ddl",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    owner_token = "runtime-guard-owner-token"
    sealed = ledger.seal_for_runtime_guard(owner_token)
    ddl_result: dict[str, Any] = {}

    def attack_schema() -> None:
        connection = sqlite3.connect(path, timeout=0.1, isolation_level=None)
        try:
            connection.execute("CREATE TABLE runtime_guard_rogue(value TEXT)")
            ddl_result["committed"] = True
        except sqlite3.OperationalError as exc:
            ddl_result["error"] = exc
        finally:
            connection.close()

    with ledger.runtime_guard_lifecycle_lease(
        owner_token,
        int(sealed["lifecycle_generation"]),
    ):
        ddl_thread = threading.Thread(target=attack_schema)
        ddl_thread.start()
        ddl_thread.join(timeout=5)
        assert not ddl_thread.is_alive()
        assert "committed" not in ddl_result
        assert "locked" in str(ddl_result["error"]).casefold()

    assert ledger.validate_runtime_guard_seal(owner_token, 1)["ready"] is True
    ledger._connection.close()
    ledger._wipe_retained_keys()
    ledger._closed = True


class _CoordinatedPostCommitLedger(SQLiteRuntimeIntrusionLedgerV04):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.coordinate_post_commit = False
        self.insert_committed = threading.Event()
        self.allow_readback = threading.Event()
        super().__init__(*args, **kwargs)

    def _readback_rows_in_atomic_snapshot(
        self,
        rows: list[tuple[Any, ...]],
    ) -> list[dict[str, Any]]:
        if self.coordinate_post_commit:
            self.insert_committed.set()
            if not self.allow_readback.wait(timeout=5):
                raise RuntimeError("test_readback_coordination_timeout")
        return super()._readback_rows_in_atomic_snapshot(rows)


def test_concurrent_ddl_in_post_commit_gap_prevents_truthy_receipt(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "post-commit-ddl-race.sqlite3").resolve()
    ledger = _CoordinatedPostCommitLedger(
        path,
        ledger_id="post-commit-ddl-race",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    outcome, packet = _quarantined_hnc(
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        )
    )
    result: dict[str, Any] = {}
    ledger.coordinate_post_commit = True

    def append() -> None:
        try:
            result["receipt"] = ledger.append_violation(
                intrusion_id=outcome.admission_id,
                runtime_metadata=_metadata("post-commit-ddl-race", outcome),
                quarantine_summary=outcome.public_summary(),
                hnc_packet=packet,
            )
        except BaseException as exc:
            result["error"] = exc

    append_thread = threading.Thread(target=append)
    append_thread.start()
    assert ledger.insert_committed.wait(timeout=5)
    attacker = sqlite3.connect(path, timeout=1)
    attacker.execute("DROP TRIGGER runtime_intrusion_entries_v04_no_update")
    attacker.commit()
    attacker.close()
    ledger.allow_readback.set()
    append_thread.join(timeout=5)

    assert not append_thread.is_alive()
    assert "receipt" not in result
    assert isinstance(result.get("error"), RuntimeIntrusionLedgerError)
    assert result["error"].code == "runtime_intrusion_ledger_schema_invalid"
    assert ledger._connection.execute(
        "SELECT COUNT(*) FROM runtime_intrusion_entries_v04"
    ).fetchone() == (2,)
    assert ledger.public_summary()["ready"] is False
    ledger.close()


def test_atomic_post_commit_readback_blocks_interleaved_ddl(
    tmp_path: Path,
) -> None:
    path = (tmp_path / "atomic-readback-ddl-race.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="atomic-readback-ddl-race",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    outcome, packet = _quarantined_hnc(
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        )
    )
    snapshot_locked = threading.Event()
    ddl_finished = threading.Event()
    begin_count = 0

    def trace(statement: str) -> None:
        nonlocal begin_count
        normalized = " ".join(statement.split()).casefold()
        if normalized == "begin immediate":
            begin_count += 1
        elif (
            begin_count == 2
            and normalized.startswith("select type, name, tbl_name, sql from sqlite_schema")
        ):
            snapshot_locked.set()
            ddl_finished.wait(timeout=5)

    ledger._connection.set_trace_callback(trace)
    append_result: dict[str, Any] = {}

    def append() -> None:
        try:
            append_result["receipt"] = ledger.append_violation(
                intrusion_id=outcome.admission_id,
                runtime_metadata=_metadata("atomic-readback-ddl-race", outcome),
                quarantine_summary=outcome.public_summary(),
                hnc_packet=packet,
            )
        except BaseException as exc:
            append_result["error"] = exc

    append_thread = threading.Thread(target=append)
    append_thread.start()
    assert snapshot_locked.wait(timeout=5)
    ddl_result: dict[str, Any] = {}

    def attack_schema() -> None:
        connection = sqlite3.connect(path, timeout=0.1, isolation_level=None)
        try:
            connection.execute(
                "DROP TRIGGER runtime_intrusion_entries_v04_no_update"
            )
            ddl_result["committed"] = True
        except sqlite3.OperationalError as exc:
            ddl_result["error"] = exc
        finally:
            connection.close()
            ddl_finished.set()

    ddl_thread = threading.Thread(target=attack_schema)
    ddl_thread.start()
    ddl_thread.join(timeout=5)
    append_thread.join(timeout=5)
    ledger._connection.set_trace_callback(None)

    assert not ddl_thread.is_alive()
    assert not append_thread.is_alive()
    assert "error" in ddl_result
    assert "locked" in str(ddl_result["error"]).casefold()
    assert "error" not in append_result
    assert append_result["receipt"]["durability_readback"] is True
    assert append_result["receipt"]["hnc_packet_authenticated"] is True
    ledger.close()


@pytest.mark.parametrize(
    "sabotage_sql",
    [
        "DROP TRIGGER runtime_intrusion_entries_v04_no_update",
        "DROP INDEX runtime_intrusion_entries_v04_commitment_uq",
        "CREATE TABLE runtime_intrusion_attacker_shadow(value TEXT)",
    ],
)
def test_live_schema_sabotage_cannot_return_durability_readback(
    tmp_path: Path,
    sabotage_sql: str,
) -> None:
    path = (tmp_path / f"schema-live-{abs(hash(sabotage_sql))}.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="live-schema-sabotage-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    outcome, packet = _quarantined_hnc(
        ledger_instance_commitment=str(
            ledger.preflight()["ledger_instance_commitment"]
        )
    )
    ledger._connection.execute(sabotage_sql)

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        ledger.append_violation(
            intrusion_id=outcome.admission_id,
            runtime_metadata=_metadata("live-schema-sabotage", outcome),
            quarantine_summary=outcome.public_summary(),
            hnc_packet=packet,
        )
    assert raised.value.code == "runtime_intrusion_ledger_schema_invalid"
    assert ledger._connection.execute(
        "SELECT COUNT(*) FROM runtime_intrusion_entries_v04"
    ).fetchone() == (1,)
    summary = ledger.public_summary()
    assert summary["ready"] is False
    assert summary["reason_code"] == "runtime_intrusion_ledger_schema_invalid"
    ledger.close()


def test_reopen_rejects_missing_or_rogue_schema_objects(tmp_path: Path) -> None:
    path = (tmp_path / "intrusions.sqlite3").resolve()
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="schema-tamper-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    ledger.close()

    connection = sqlite3.connect(path)
    connection.execute("DROP TRIGGER runtime_intrusion_entries_v04_no_delete")
    connection.execute("CREATE TABLE attacker_shadow(value TEXT)")
    connection.commit()
    connection.close()

    with pytest.raises(RuntimeIntrusionLedgerError) as raised:
        SQLiteRuntimeIntrusionLedgerV04(
            path,
            ledger_id="schema-tamper-test",
            quarantine_hnc_key_provider=lambda: MASTER_KEY,
            max_violation_entries=3,
        )
    assert raised.value.code == "runtime_intrusion_ledger_schema_invalid"


def test_plaintext_canary_never_appears_in_sqlite_storage(tmp_path: Path) -> None:
    path = (tmp_path / "intrusions.sqlite3").resolve()
    runtime_plaintext = _runtime_violation_content(
        {
            "event_name": "os.remove",
            "resource_commitment": "a" * 64,
            "reason_code": "runtime_effect_not_magic_star_released",
        }
    )
    ledger = SQLiteRuntimeIntrusionLedgerV04(
        path,
        ledger_id="plaintext-test",
        quarantine_hnc_key_provider=lambda: MASTER_KEY,
        max_violation_entries=3,
    )
    outcome, packet, _receipt = _append_one(ledger)

    stored_packet = ledger._connection.execute(
        "SELECT hnc_packet_json FROM runtime_intrusion_entries_v04 WHERE sequence = 2"
    ).fetchone()
    assert stored_packet is not None
    assert json.loads(bytes(stored_packet[0])) == packet
    assert runtime_plaintext not in bytes(stored_packet[0])
    assert outcome.public_summary()["raw_material_retained"] is False
    ledger.close()

    storage_files = [candidate for candidate in path.parent.iterdir() if candidate.is_file()]
    assert storage_files
    for candidate in storage_files:
        assert runtime_plaintext not in candidate.read_bytes(), candidate.name
