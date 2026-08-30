"""Aureon-owned canonical accounting journal and QuickBooks projection queue.

The journal is the authority. QuickBooks is a downstream projection and
read-back surface. QBO observations can create reconciliation tasks, but they
cannot create, approve, amend, or replace an Aureon journal entry.

The private runtime journal is an append-only JSONL hash chain. Every posting is
balanced, evidence-bound, and separately approved before a projection intent
can be created. Projection read-back records contain provider metadata and
digests only; they never change the canonical posting.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

from Kings_Accounting_Suite.tools.quickbooks_accounting_integration import (
    AureonCanonicalAccountingEvent,
    payload_sha256,
)

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
OBSERVATION_SLUG_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,63}")
EVIDENCE_SOURCE_SYSTEMS = frozenset(
    {
        "aureon_grant_ledger",
        "bank_statement",
        "companies_house",
        "gmail",
        "google_drive",
        "hmrc",
        "intuit_developer",
        "quickbooks_online",
        "xero",
    }
)
MONEY_QUANTUM = Decimal("0.01")
ZERO = Decimal("0.00")


class AccountingControlError(RuntimeError):
    """Base error for the Aureon canonical accounting control plane."""


class JournalValidationError(AccountingControlError):
    """A posting or transition is invalid."""


class JournalIntegrityError(AccountingControlError):
    """The append-only journal hash chain cannot be verified."""


class JournalLockedError(AccountingControlError):
    """Another writer owns the journal lock."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(instant: datetime) -> str:
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    return instant.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _require_text(label: str, value: str) -> str:
    clean = str(value).strip()
    if not clean:
        raise JournalValidationError(f"{label} is required")
    return clean


def _require_digest(label: str, value: str) -> str:
    clean = str(value).strip().lower()
    if not SHA256_PATTERN.fullmatch(clean):
        raise JournalValidationError(f"{label} must be a SHA-256 digest")
    return clean


def _require_observation_slug(label: str, value: str) -> str:
    clean = str(value).strip().lower()
    if not OBSERVATION_SLUG_PATTERN.fullmatch(clean):
        raise JournalValidationError(f"{label} must be a lowercase accounting evidence slug")
    return clean


def _money(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value)).quantize(MONEY_QUANTUM)
    except (InvalidOperation, ValueError) as exc:
        raise JournalValidationError(f"Invalid monetary amount: {value!r}") from exc
    if not amount.is_finite() or amount < ZERO:
        raise JournalValidationError("Monetary amounts must be finite and non-negative")
    return amount


def _money_text(value: Decimal) -> str:
    return f"{value.quantize(MONEY_QUANTUM):.2f}"


@dataclass(frozen=True)
class AureonLedgerLine:
    account_code: str
    account_name: str
    debit: Decimal = ZERO
    credit: Decimal = ZERO
    tax_code: str = ""
    project_code: str = ""

    @classmethod
    def create(
        cls,
        *,
        account_code: str,
        account_name: str,
        debit: Any = "0",
        credit: Any = "0",
        tax_code: str = "",
        project_code: str = "",
    ) -> AureonLedgerLine:
        debit_amount = _money(debit)
        credit_amount = _money(credit)
        if (debit_amount == ZERO) == (credit_amount == ZERO):
            raise JournalValidationError("Each ledger line must have exactly one positive debit or credit")
        return cls(
            account_code=_require_text("account_code", account_code),
            account_name=_require_text("account_name", account_name),
            debit=debit_amount,
            credit=credit_amount,
            tax_code=str(tax_code).strip(),
            project_code=str(project_code).strip(),
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> AureonLedgerLine:
        return cls.create(
            account_code=str(value.get("account_code", "")),
            account_name=str(value.get("account_name", "")),
            debit=value.get("debit", "0"),
            credit=value.get("credit", "0"),
            tax_code=str(value.get("tax_code", "")),
            project_code=str(value.get("project_code", "")),
        )

    def serialise(self) -> dict[str, str]:
        return {
            "account_code": self.account_code,
            "account_name": self.account_name,
            "debit": _money_text(self.debit),
            "credit": _money_text(self.credit),
            "tax_code": self.tax_code,
            "project_code": self.project_code,
        }


@dataclass(frozen=True)
class AureonJournalEntry:
    entry_id: str
    effective_date: str
    description: str
    currency: str
    lines: tuple[AureonLedgerLine, ...]
    evidence_sha256: tuple[str, ...]
    source_system: str
    source_reference_sha256: str
    created_at: str

    @classmethod
    def create(
        cls,
        *,
        entry_id: str,
        effective_date: str,
        description: str,
        lines: Sequence[AureonLedgerLine | Mapping[str, Any]],
        evidence_sha256: Sequence[str],
        source_system: str,
        source_reference_sha256: str,
        currency: str = "GBP",
        now: datetime | None = None,
    ) -> AureonJournalEntry:
        try:
            date.fromisoformat(effective_date)
        except ValueError as exc:
            raise JournalValidationError("effective_date must use YYYY-MM-DD") from exc
        clean_currency = currency.strip().upper()
        if clean_currency != "GBP":
            raise JournalValidationError("The company canonical ledger currently supports GBP only")
        clean_lines = tuple(
            line if isinstance(line, AureonLedgerLine) else AureonLedgerLine.from_mapping(line)
            for line in lines
        )
        if len(clean_lines) < 2:
            raise JournalValidationError("A journal entry requires at least two ledger lines")
        debits = sum((line.debit for line in clean_lines), ZERO)
        credits = sum((line.credit for line in clean_lines), ZERO)
        if debits == ZERO or debits != credits:
            raise JournalValidationError(
                f"Journal entry is not balanced: debit={_money_text(debits)} credit={_money_text(credits)}"
            )
        evidence = tuple(sorted({_require_digest("evidence", item) for item in evidence_sha256}))
        if not evidence:
            raise JournalValidationError("A journal entry requires at least one evidence digest")
        return cls(
            entry_id=_require_text("entry_id", entry_id),
            effective_date=effective_date,
            description=_require_text("description", description),
            currency=clean_currency,
            lines=clean_lines,
            evidence_sha256=evidence,
            source_system=_require_text("source_system", source_system),
            source_reference_sha256=_require_digest("source_reference_sha256", source_reference_sha256),
            created_at=_iso(now or _utc_now()),
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> AureonJournalEntry:
        return cls.create(
            entry_id=str(payload.get("entry_id", "")),
            effective_date=str(payload.get("effective_date", "")),
            description=str(payload.get("description", "")),
            currency=str(payload.get("currency", "GBP")),
            lines=tuple(payload.get("lines") or ()),
            evidence_sha256=tuple(payload.get("evidence_sha256") or ()),
            source_system=str(payload.get("source_system", "")),
            source_reference_sha256=str(payload.get("source_reference_sha256", "")),
            now=datetime.fromisoformat(str(payload.get("created_at", "")).replace("Z", "+00:00")),
        )

    def serialise(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "effective_date": self.effective_date,
            "description": self.description,
            "currency": self.currency,
            "lines": [line.serialise() for line in self.lines],
            "evidence_sha256": list(self.evidence_sha256),
            "source_system": self.source_system,
            "source_reference_sha256": self.source_reference_sha256,
            "created_at": self.created_at,
        }

    def digest(self) -> str:
        return payload_sha256(self.serialise())


class _JournalLock:
    def __init__(self, path: Path):
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> _JournalLock:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise JournalLockedError(f"Canonical journal is locked: {self.path}") from exc
        os.write(self.fd, f"pid={os.getpid()}\n".encode("ascii"))
        os.fsync(self.fd)
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.fd is not None:
            os.close(self.fd)
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


class AureonAccountingJournal:
    """Append-only hash-chained journal, approvals, and projection receipts."""

    SCHEMA_VERSION = "aureon-canonical-accounting-journal-v1"

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.lock_path = self.path.with_suffix(f"{self.path.suffix}.lock")

    def read_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        previous = "0" * 64
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, raw in enumerate(handle, start=1):
                if not raw.strip():
                    continue
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise JournalIntegrityError(f"Journal line {line_number} is not valid JSON") from exc
                if not isinstance(record, dict):
                    raise JournalIntegrityError(f"Journal line {line_number} is not an object")
                if record.get("schema_version") != self.SCHEMA_VERSION:
                    raise JournalIntegrityError(f"Journal line {line_number} has an unsupported schema")
                if record.get("sequence") != len(records) + 1:
                    raise JournalIntegrityError(f"Journal sequence breaks at line {line_number}")
                if record.get("previous_record_sha256") != previous:
                    raise JournalIntegrityError(f"Journal hash chain breaks at line {line_number}")
                supplied = str(record.get("record_sha256", ""))
                unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
                expected = hashlib.sha256(_canonical_json(unsigned)).hexdigest()
                if not SHA256_PATTERN.fullmatch(supplied) or supplied != expected:
                    raise JournalIntegrityError(f"Journal record digest fails at line {line_number}")
                previous = supplied
                records.append(record)
        return records

    def verify(self) -> dict[str, Any]:
        records = self.read_records()
        return {
            "verified": True,
            "record_count": len(records),
            "journal_head_sha256": records[-1]["record_sha256"] if records else "0" * 64,
        }

    def _append(self, *, event_type: str, event_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
        with _JournalLock(self.lock_path):
            records = self.read_records()
            unsigned: dict[str, Any] = {
                "schema_version": self.SCHEMA_VERSION,
                "sequence": len(records) + 1,
                "previous_record_sha256": records[-1]["record_sha256"] if records else "0" * 64,
                "event_type": _require_text("event_type", event_type),
                "event_id": _require_text("event_id", event_id),
                "recorded_at": _iso(_utc_now()),
                "body": dict(body),
            }
            record = {**unsigned, "record_sha256": hashlib.sha256(_canonical_json(unsigned)).hexdigest()}
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            return record

    def _entry_record(self, entry_id: str) -> dict[str, Any]:
        matches = [
            record
            for record in self.read_records()
            if record["event_type"] == "journal_entry_recorded" and record["event_id"] == entry_id
        ]
        if not matches:
            raise JournalValidationError(f"Unknown Aureon journal entry: {entry_id}")
        return matches[0]

    def record_entry(self, entry: AureonJournalEntry) -> dict[str, Any]:
        if any(record["event_id"] == entry.entry_id for record in self.read_records()):
            raise JournalValidationError(f"Duplicate Aureon accounting event ID: {entry.entry_id}")
        return self._append(
            event_type="journal_entry_recorded",
            event_id=entry.entry_id,
            body={"authority": "aureon_os", "entry": entry.serialise(), "entry_sha256": entry.digest()},
        )

    def approve_entry(
        self,
        *,
        entry_id: str,
        approved_by: str,
        approval_evidence_sha256: Sequence[str],
    ) -> dict[str, Any]:
        entry_record = self._entry_record(entry_id)
        records = self.read_records()
        if any(
            record["event_type"] == "journal_entry_approved" and record["body"].get("entry_id") == entry_id
            for record in records
        ):
            raise JournalValidationError(f"Aureon journal entry is already approved: {entry_id}")
        evidence = sorted({_require_digest("approval evidence", item) for item in approval_evidence_sha256})
        if not evidence:
            raise JournalValidationError("Approval requires an evidence digest")
        return self._append(
            event_type="journal_entry_approved",
            event_id=f"approval:{entry_id}",
            body={
                "entry_id": entry_id,
                "entry_record_sha256": entry_record["record_sha256"],
                "approved_by": _require_text("approved_by", approved_by),
                "approval_evidence_sha256": evidence,
                "authority": "aureon_os",
            },
        )

    def queue_quickbooks_projection(
        self,
        *,
        entry_id: str,
        operation: str,
        entity: str,
        payload: Mapping[str, Any],
        projection_id: str | None = None,
    ) -> tuple[dict[str, Any], AureonCanonicalAccountingEvent]:
        entry_record = self._entry_record(entry_id)
        records = self.read_records()
        approvals = [
            record
            for record in records
            if record["event_type"] == "journal_entry_approved" and record["body"].get("entry_id") == entry_id
        ]
        if not approvals:
            raise JournalValidationError("QuickBooks projection requires an approved Aureon journal entry")
        approval = approvals[-1]
        entry = AureonJournalEntry.from_payload(entry_record["body"]["entry"])
        projection_event_id = projection_id or f"qbo:{uuid.uuid4()}"
        if any(record["event_id"] == projection_event_id for record in records):
            raise JournalValidationError(f"Duplicate projection ID: {projection_event_id}")
        evidence = [
            *entry.evidence_sha256,
            entry_record["record_sha256"],
            approval["record_sha256"],
        ]
        canonical_event = AureonCanonicalAccountingEvent.create(
            event_id=projection_event_id,
            operation=operation,
            entity=entity,
            payload=payload,
            evidence_sha256=evidence,
        )
        idempotency_key = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"aureon-quickbooks:{canonical_event.digest()}",
        ).hex
        record = self._append(
            event_type="quickbooks_projection_queued",
            event_id=projection_event_id,
            body={
                "entry_id": entry_id,
                "approval_record_sha256": approval["record_sha256"],
                "canonical_event": asdict(canonical_event),
                "canonical_event_sha256": canonical_event.digest(),
                "payload_sha256": payload_sha256(payload),
                "idempotency_key": idempotency_key,
                "projection_state": "queued_not_sent",
                "authority": "aureon_os",
                "target": "quickbooks_online",
            },
        )
        return record, canonical_event

    def record_quickbooks_readback(
        self,
        *,
        projection_id: str,
        projected_payload: Mapping[str, Any],
        response_payload: Mapping[str, Any],
        qbo_object_id: str,
        qbo_sync_token: str,
    ) -> dict[str, Any]:
        records = self.read_records()
        queued = [
            record
            for record in records
            if record["event_type"] == "quickbooks_projection_queued" and record["event_id"] == projection_id
        ]
        if not queued:
            raise JournalValidationError(f"Unknown QuickBooks projection: {projection_id}")
        if any(
            record["event_type"] == "quickbooks_projection_readback_verified"
            and record["body"].get("projection_id") == projection_id
            for record in records
        ):
            raise JournalValidationError(f"QuickBooks projection already has a verified read-back: {projection_id}")
        projection = queued[-1]
        if payload_sha256(projected_payload) != projection["body"]["payload_sha256"]:
            raise JournalValidationError("Read-back payload does not match the queued Aureon projection")
        entity = str(projection["body"]["canonical_event"]["entity"])
        qbo_object = response_payload.get(entity)
        if not isinstance(qbo_object, Mapping):
            raise JournalValidationError(f"QuickBooks read-back does not contain the projected {entity}")
        clean_object_id = _require_text("qbo_object_id", qbo_object_id)
        clean_sync_token = _require_text("qbo_sync_token", qbo_sync_token)
        if str(qbo_object.get("Id", "")) != clean_object_id:
            raise JournalValidationError("QuickBooks read-back object ID does not match the provider response")
        if str(qbo_object.get("SyncToken", "")) != clean_sync_token:
            raise JournalValidationError("QuickBooks read-back SyncToken does not match the provider response")
        return self._append(
            event_type="quickbooks_projection_readback_verified",
            event_id=f"readback:{projection_id}",
            body={
                "projection_id": projection_id,
                "projection_record_sha256": projection["record_sha256"],
                "canonical_event_sha256": projection["body"]["canonical_event_sha256"],
                "response_payload_sha256": payload_sha256(response_payload),
                "qbo_object_id": clean_object_id,
                "qbo_sync_token": clean_sync_token,
                "reconciliation_state": "verified_against_aureon_projection",
                "canonical_entry_mutated": False,
            },
        )

    def record_quickbooks_observation(
        self,
        *,
        observation_type: str,
        external_reference: str,
        observed_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        observation_type = _require_text("observation_type", observation_type)
        external_reference = _require_text("external_reference", external_reference)
        observed_digest = payload_sha256(observed_payload)
        task_id = "qbo-observation:" + hashlib.sha256(
            f"{observation_type}|{external_reference}|{observed_digest}".encode()
        ).hexdigest()[:32]
        existing = next(
            (record for record in self.read_records() if record["event_id"] == task_id),
            None,
        )
        if existing is not None:
            return existing
        return self._append(
            event_type="quickbooks_observation_received",
            event_id=task_id,
            body={
                "observation_type": observation_type,
                "external_reference_sha256": hashlib.sha256(
                    external_reference.encode("utf-8")
                ).hexdigest(),
                "observed_payload_sha256": observed_digest,
                "effect": "reconciliation_task_only",
                "canonical_entry_created": False,
                "canonical_entry_mutated": False,
                "source": "quickbooks_online",
            },
        )

    def record_evidence_observation(
        self,
        *,
        source_system: str,
        observation_type: str,
        external_reference: str,
        observed_payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Bind external evidence by digest without creating an accounting fact."""

        clean_source = _require_observation_slug("source_system", source_system)
        if clean_source not in EVIDENCE_SOURCE_SYSTEMS:
            raise JournalValidationError(f"Unsupported accounting evidence source: {clean_source}")
        clean_type = _require_observation_slug("observation_type", observation_type)
        clean_reference = _require_text("external_reference", external_reference)
        observed_digest = payload_sha256(observed_payload)
        event_id = "evidence-observation:" + hashlib.sha256(
            f"{clean_source}|{clean_type}|{clean_reference}|{observed_digest}".encode()
        ).hexdigest()[:32]
        existing = next(
            (record for record in self.read_records() if record["event_id"] == event_id),
            None,
        )
        if existing is not None:
            return existing
        return self._append(
            event_type="external_evidence_observation_received",
            event_id=event_id,
            body={
                "source_system": clean_source,
                "observation_type": clean_type,
                "external_reference_sha256": hashlib.sha256(
                    clean_reference.encode("utf-8")
                ).hexdigest(),
                "observed_payload_sha256": observed_digest,
                "effect": "reconciliation_evidence_only",
                "canonical_entry_created": False,
                "canonical_entry_mutated": False,
                "compliance_state_changed": False,
                "projection_queued": False,
            },
        )

    def summary(self) -> dict[str, Any]:
        records = self.read_records()
        counts: dict[str, int] = {}
        for record in records:
            event_type = str(record["event_type"])
            counts[event_type] = counts.get(event_type, 0) + 1
        queued_ids = {
            record["event_id"] for record in records if record["event_type"] == "quickbooks_projection_queued"
        }
        reconciled_ids = {
            record["body"]["projection_id"]
            for record in records
            if record["event_type"] == "quickbooks_projection_readback_verified"
        }
        evidence_source_counts: dict[str, int] = {}
        for record in records:
            if record["event_type"] != "external_evidence_observation_received":
                continue
            source_system = str(record["body"]["source_system"])
            evidence_source_counts[source_system] = evidence_source_counts.get(source_system, 0) + 1
        summary: dict[str, Any] = {
            "schema_version": "aureon-accounting-control-status-v1",
            "authority": {
                "canonical_system": "aureon_os",
                "quickbooks_role": "downstream_projection_and_readback",
                "quickbooks_may_create_or_mutate_canonical_entries": False,
            },
            "journal": {
                "integrity_verified": True,
                "record_count": len(records),
                "journal_head_sha256": records[-1]["record_sha256"] if records else "0" * 64,
                "entry_count": counts.get("journal_entry_recorded", 0),
                "approved_entry_count": counts.get("journal_entry_approved", 0),
            },
            "quickbooks_projection": {
                "queued_count": len(queued_ids),
                "readback_verified_count": len(reconciled_ids),
                "outstanding_readback_count": len(queued_ids - reconciled_ids),
                "observation_task_count": counts.get("quickbooks_observation_received", 0),
            },
            "evidence_observations": {
                "count": counts.get("external_evidence_observation_received", 0),
                "by_source": dict(sorted(evidence_source_counts.items())),
                "may_create_or_mutate_canonical_entries": False,
                "may_change_compliance_state": False,
            },
            "controls": {
                "double_entry_required": True,
                "evidence_digest_required": True,
                "explicit_aureon_approval_required": True,
                "provider_observations_are_non_authoritative": True,
            },
            "updated_at": _iso(_utc_now()),
        }
        summary["status_sha256"] = payload_sha256(summary)
        return summary

    def write_status(self, path: str | Path) -> Path:
        destination = Path(path)
        payload = self.summary()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            temporary = Path(handle.name)
        os.replace(temporary, destination)
        return destination


def _default_journal_path() -> Path:
    configured = os.environ.get("AUREON_ACCOUNTING_JOURNAL_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "output" / "accounting_control" / "journal.jsonl"


def _default_status_path() -> Path:
    configured = os.environ.get("AUREON_ACCOUNTING_CONTROL_STATUS_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "output" / "accounting_control" / "status.json"


def _default_quickbooks_status_path() -> Path:
    configured = os.environ.get("QUICKBOOKS_STATUS_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "output" / "quickbooks" / "status.json"


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("verify", "status", "observe-quickbooks-status", "observe-evidence-file"),
    )
    parser.add_argument("--journal", type=Path, default=_default_journal_path())
    parser.add_argument("--status-path", type=Path, default=_default_status_path())
    parser.add_argument("--quickbooks-status", type=Path, default=_default_quickbooks_status_path())
    parser.add_argument("--evidence-payload", type=Path)
    args = parser.parse_args()
    journal = AureonAccountingJournal(args.journal)
    if args.command == "verify":
        print(json.dumps(journal.verify(), indent=2))
        return 0
    if args.command == "observe-quickbooks-status":
        try:
            quickbooks_status = json.loads(args.quickbooks_status.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"QuickBooks status is unavailable or invalid: {args.quickbooks_status}") from exc
        if quickbooks_status.get("schema_version") != "aureon-quickbooks-status-v1":
            raise SystemExit("QuickBooks status schema is not supported")
        reference = str(
            quickbooks_status.get("status_sha256")
            or quickbooks_status.get("updated_at")
            or args.quickbooks_status.resolve()
        )
        record = journal.record_quickbooks_observation(
            observation_type="quickbooks_control_plane_status",
            external_reference=reference,
            observed_payload=quickbooks_status,
        )
        status_path = journal.write_status(args.status_path)
        print(
            json.dumps(
                {
                    "recorded_or_verified_existing": True,
                    "event_id": record["event_id"],
                    "record_sha256": record["record_sha256"],
                    "status_path": str(status_path),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "observe-evidence-file":
        if args.evidence_payload is None:
            raise SystemExit("--evidence-payload is required for observe-evidence-file")
        try:
            receipt = json.loads(args.evidence_payload.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Evidence receipt is unavailable or invalid: {args.evidence_payload}") from exc
        if receipt.get("schema_version") != "aureon-evidence-observation-v1":
            raise SystemExit("Evidence observation schema is not supported")
        observed_payload = receipt.get("observed_payload")
        if not isinstance(observed_payload, Mapping):
            raise SystemExit("Evidence observation payload must be an object")
        record = journal.record_evidence_observation(
            source_system=str(receipt.get("source_system", "")),
            observation_type=str(receipt.get("observation_type", "")),
            external_reference=str(receipt.get("external_reference", "")),
            observed_payload=observed_payload,
        )
        status_path = journal.write_status(args.status_path)
        print(
            json.dumps(
                {
                    "recorded_or_verified_existing": True,
                    "event_id": record["event_id"],
                    "record_sha256": record["record_sha256"],
                    "status_path": str(status_path),
                },
                indent=2,
            )
        )
        return 0
    status_path = journal.write_status(args.status_path)
    print(json.dumps({"status_path": str(status_path), "status": journal.summary()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
