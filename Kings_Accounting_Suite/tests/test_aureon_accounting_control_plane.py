from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from Kings_Accounting_Suite.tools.aureon_accounting_control_plane import (
    AureonAccountingJournal,
    AureonJournalEntry,
    AureonLedgerLine,
    JournalIntegrityError,
    JournalValidationError,
)
from Kings_Accounting_Suite.tools.quickbooks_accounting_integration import MutationBlockedError

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)
EVIDENCE = "a" * 64
APPROVAL_EVIDENCE = "b" * 64
SOURCE_REFERENCE = "c" * 64


def make_entry() -> AureonJournalEntry:
    return AureonJournalEntry.create(
        entry_id="AUR-JE-2026-000001",
        effective_date="2026-07-31",
        description="Evidence-backed research software cost",
        lines=(
            AureonLedgerLine.create(
                account_code="7600",
                account_name="R&D software",
                debit="120.00",
                project_code="RND-2026-01",
            ),
            AureonLedgerLine.create(
                account_code="2100",
                account_name="Trade creditors",
                credit="120.00",
                project_code="RND-2026-01",
            ),
        ),
        evidence_sha256=(EVIDENCE,),
        source_system="aureon_evidence_vault",
        source_reference_sha256=SOURCE_REFERENCE,
        now=NOW,
    )


def qbo_payload() -> dict[str, object]:
    return {
        "TxnDate": "2026-07-31",
        "PrivateNote": "AUR-JE-2026-000001",
        "Line": [
            {"Amount": 120, "DetailType": "JournalEntryLineDetail"},
            {"Amount": 120, "DetailType": "JournalEntryLineDetail"},
        ],
    }


def test_entry_requires_balanced_double_entry_and_evidence() -> None:
    with pytest.raises(JournalValidationError, match="not balanced"):
        AureonJournalEntry.create(
            entry_id="bad",
            effective_date="2026-07-31",
            description="Unbalanced",
            lines=(
                AureonLedgerLine.create(account_code="1000", account_name="Bank", debit="1.00"),
                AureonLedgerLine.create(account_code="4000", account_name="Sales", credit="2.00"),
            ),
            evidence_sha256=(EVIDENCE,),
            source_system="test",
            source_reference_sha256=SOURCE_REFERENCE,
        )

    with pytest.raises(JournalValidationError, match="evidence"):
        AureonJournalEntry.create(
            entry_id="bad",
            effective_date="2026-07-31",
            description="No evidence",
            lines=(
                AureonLedgerLine.create(account_code="1000", account_name="Bank", debit="1.00"),
                AureonLedgerLine.create(account_code="4000", account_name="Sales", credit="1.00"),
            ),
            evidence_sha256=(),
            source_system="test",
            source_reference_sha256=SOURCE_REFERENCE,
        )


def test_projection_requires_aureon_approval_and_exact_payload(tmp_path: Path) -> None:
    journal = AureonAccountingJournal(tmp_path / "journal.jsonl")
    entry = make_entry()
    journal.record_entry(entry)

    with pytest.raises(JournalValidationError, match="approved Aureon"):
        journal.queue_quickbooks_projection(
            entry_id=entry.entry_id,
            operation="create",
            entity="JournalEntry",
            payload=qbo_payload(),
        )

    journal.approve_entry(
        entry_id=entry.entry_id,
        approved_by="company_owner",
        approval_evidence_sha256=(APPROVAL_EVIDENCE,),
    )
    projection, canonical_event = journal.queue_quickbooks_projection(
        entry_id=entry.entry_id,
        operation="create",
        entity="JournalEntry",
        payload=qbo_payload(),
        projection_id="qbo:AUR-JE-2026-000001",
    )

    assert projection["body"]["authority"] == "aureon_os"
    assert projection["body"]["projection_state"] == "queued_not_sent"
    assert len(projection["body"]["idempotency_key"]) == 32
    canonical_event.verify_projection(operation="create", entity="JournalEntry", payload=qbo_payload())
    with pytest.raises(MutationBlockedError, match="payload differs"):
        canonical_event.verify_projection(
            operation="create",
            entity="JournalEntry",
            payload={**qbo_payload(), "PrivateNote": "tampered"},
        )


def test_readback_and_observation_never_mutate_canonical_entry(tmp_path: Path) -> None:
    journal = AureonAccountingJournal(tmp_path / "journal.jsonl")
    entry = make_entry()
    journal.record_entry(entry)
    journal.approve_entry(
        entry_id=entry.entry_id,
        approved_by="company_owner",
        approval_evidence_sha256=(APPROVAL_EVIDENCE,),
    )
    journal.queue_quickbooks_projection(
        entry_id=entry.entry_id,
        operation="create",
        entity="JournalEntry",
        payload=qbo_payload(),
        projection_id="qbo:AUR-JE-2026-000001",
    )
    readback = journal.record_quickbooks_readback(
        projection_id="qbo:AUR-JE-2026-000001",
        projected_payload=qbo_payload(),
        response_payload={"JournalEntry": {"Id": "987", "SyncToken": "0"}},
        qbo_object_id="987",
        qbo_sync_token="0",
    )
    observation = journal.record_quickbooks_observation(
        observation_type="bank_feed_item",
        external_reference="sensitive-provider-reference",
        observed_payload={"amount": "42.00", "description": "private transaction"},
    )
    repeated_observation = journal.record_quickbooks_observation(
        observation_type="bank_feed_item",
        external_reference="sensitive-provider-reference",
        observed_payload={"amount": "42.00", "description": "private transaction"},
    )

    assert readback["body"]["canonical_entry_mutated"] is False
    assert observation["body"]["canonical_entry_created"] is False
    assert observation["body"]["canonical_entry_mutated"] is False
    assert repeated_observation["record_sha256"] == observation["record_sha256"]
    assert "sensitive-provider-reference" not in json.dumps(observation)
    assert "private transaction" not in json.dumps(observation)

    summary = journal.summary()
    assert summary["authority"]["canonical_system"] == "aureon_os"
    assert summary["authority"]["quickbooks_may_create_or_mutate_canonical_entries"] is False
    assert summary["journal"]["entry_count"] == 1
    assert summary["journal"]["approved_entry_count"] == 1
    assert summary["quickbooks_projection"]["queued_count"] == 1
    assert summary["quickbooks_projection"]["readback_verified_count"] == 1
    assert summary["quickbooks_projection"]["outstanding_readback_count"] == 0
    assert summary["quickbooks_projection"]["observation_task_count"] == 1


def test_external_evidence_is_digest_only_idempotent_and_non_authoritative(tmp_path: Path) -> None:
    journal = AureonAccountingJournal(tmp_path / "journal.jsonl")
    private_payload = {
        "provider_state": "received_pending_acceptance",
        "private_detail": "must not enter the journal",
    }
    observation = journal.record_evidence_observation(
        source_system="companies_house",
        observation_type="confirmation_statement_receipt",
        external_reference="private-provider-reference",
        observed_payload=private_payload,
    )
    repeated = journal.record_evidence_observation(
        source_system="companies_house",
        observation_type="confirmation_statement_receipt",
        external_reference="private-provider-reference",
        observed_payload=private_payload,
    )

    serialised = json.dumps(observation)
    assert observation["body"]["effect"] == "reconciliation_evidence_only"
    assert observation["body"]["canonical_entry_created"] is False
    assert observation["body"]["canonical_entry_mutated"] is False
    assert observation["body"]["compliance_state_changed"] is False
    assert observation["body"]["projection_queued"] is False
    assert repeated["record_sha256"] == observation["record_sha256"]
    assert "private-provider-reference" not in serialised
    assert "must not enter the journal" not in serialised
    assert journal.summary()["evidence_observations"] == {
        "count": 1,
        "by_source": {"companies_house": 1},
        "may_create_or_mutate_canonical_entries": False,
        "may_change_compliance_state": False,
    }


def test_external_evidence_rejects_uncontrolled_source(tmp_path: Path) -> None:
    journal = AureonAccountingJournal(tmp_path / "journal.jsonl")
    with pytest.raises(JournalValidationError, match="Unsupported accounting evidence source"):
        journal.record_evidence_observation(
            source_system="unknown_provider",
            observation_type="status",
            external_reference="reference",
            observed_payload={"status": "unknown"},
        )


def test_readback_rejects_changed_projection_or_wrong_provider_identity(tmp_path: Path) -> None:
    journal = AureonAccountingJournal(tmp_path / "journal.jsonl")
    entry = make_entry()
    journal.record_entry(entry)
    journal.approve_entry(
        entry_id=entry.entry_id,
        approved_by="company_owner",
        approval_evidence_sha256=(APPROVAL_EVIDENCE,),
    )
    journal.queue_quickbooks_projection(
        entry_id=entry.entry_id,
        operation="create",
        entity="JournalEntry",
        payload=qbo_payload(),
        projection_id="qbo:AUR-JE-2026-000001",
    )

    with pytest.raises(JournalValidationError, match="does not match the queued"):
        journal.record_quickbooks_readback(
            projection_id="qbo:AUR-JE-2026-000001",
            projected_payload={**qbo_payload(), "PrivateNote": "changed"},
            response_payload={"JournalEntry": {"Id": "987", "SyncToken": "0"}},
            qbo_object_id="987",
            qbo_sync_token="0",
        )
    with pytest.raises(JournalValidationError, match="object ID"):
        journal.record_quickbooks_readback(
            projection_id="qbo:AUR-JE-2026-000001",
            projected_payload=qbo_payload(),
            response_payload={"JournalEntry": {"Id": "different", "SyncToken": "0"}},
            qbo_object_id="987",
            qbo_sync_token="0",
        )


def test_journal_hash_chain_detects_tampering_and_writes_status(tmp_path: Path) -> None:
    path = tmp_path / "journal.jsonl"
    status_path = tmp_path / "status.json"
    journal = AureonAccountingJournal(path)
    journal.record_entry(make_entry())
    verified = journal.verify()
    assert verified["verified"] is True
    assert verified["record_count"] == 1
    assert len(verified["journal_head_sha256"]) == 64

    journal.write_status(status_path)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["journal"]["integrity_verified"] is True
    assert len(status["status_sha256"]) == 64

    path.write_text(path.read_text(encoding="utf-8").replace("research software", "other software"), encoding="utf-8")
    with pytest.raises(JournalIntegrityError, match="digest fails"):
        journal.verify()
