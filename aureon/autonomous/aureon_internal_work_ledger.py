"""Restart-durable, single-writer ledger for Aureon coding work receipts."""

from __future__ import annotations

import errno
import hashlib
import json
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from aureon.autonomous.aureon_internal_coding_workforce import (
    INTERNAL_ACTOR,
    TRUTH_GATED_THOUGHT_RECEIPT_PREFIX,
    WORK_SCHEMA_VERSION,
    BrainResolver,
    CodingThoughtPath,
    InternalCodingWorkforce,
    WorkReceipt,
    provision_internal_coding_workforce,
    validate_work_receipt,
)

STATE_SCHEMA = "aureon-internal-work-ledger-v1"
ENTRY_SCHEMA = "aureon-internal-work-ledger-entry-v1"


class WorkLedgerError(RuntimeError):
    """The durable work ledger is unavailable, corrupt, busy, or divergent."""


class WorkLedgerBusy(WorkLedgerError):
    """Another thread or process owns the single-writer lease."""


_THREAD_LOCKS_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.Lock] = {}


def _canonical_json(value: Any, *, newline: bool = False) -> bytes:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return encoded + (b"\n" if newline else b"")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _parse_canonical(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise WorkLedgerError("work_ledger_json_invalid") from exc
    if not isinstance(payload, dict) or raw != _canonical_json(payload, newline=True):
        raise WorkLedgerError("work_ledger_not_canonical")
    return payload


def _thread_lock_for(path: Path) -> threading.Lock:
    key = os.path.normcase(str(path.resolve(strict=False)))
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.Lock())


def _try_lock(handle: Any) -> None:
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
        os.fsync(handle.fileno())
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _writer_lease(lock_path: Path) -> Iterator[None]:
    thread_lock = _thread_lock_for(lock_path)
    if not thread_lock.acquire(blocking=False):
        raise WorkLedgerBusy("work_ledger_writer_busy")
    handle = None
    locked = False
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+b")
        try:
            _try_lock(handle)
            locked = True
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK, errno.EPERM}:
                raise WorkLedgerError("work_ledger_lock_failed") from exc
            raise WorkLedgerBusy("work_ledger_writer_busy") from None
        yield
    finally:
        if handle is not None:
            if locked:
                try:
                    _unlock(handle)
                except OSError:
                    pass
            handle.close()
        thread_lock.release()


def _private_path(path: Path) -> Path:
    resolved = Path(path)
    lowered = {part.casefold() for part in resolved.parts}
    if lowered.intersection({"frontend", "public"}) or resolved.suffix.casefold() != ".json":
        raise ValueError("private_json_work_ledger_path_required")
    return resolved


class DurableInternalWorkLedger:
    """Canonical hash-chained coding receipt store with nonblocking writes."""

    def __init__(self, path: Path) -> None:
        self.path = _private_path(path)
        self.lock_path = self.path.with_suffix(".lock")

    @staticmethod
    def _empty() -> dict[str, Any]:
        return {"schema_version": STATE_SCHEMA, "generation": 0, "entries": []}

    def _validate(self, payload: dict[str, Any]) -> tuple[WorkReceipt, ...]:
        if payload.get("schema_version") != STATE_SCHEMA:
            raise WorkLedgerError("work_ledger_schema_invalid")
        generation = payload.get("generation")
        entries = payload.get("entries")
        if type(generation) is not int or generation < 0 or not isinstance(entries, list):
            raise WorkLedgerError("work_ledger_shape_invalid")
        if generation != len(entries):
            raise WorkLedgerError("work_ledger_generation_mismatch")
        observed_hash = payload.get("state_hash")
        core = {key: value for key, value in payload.items() if key != "state_hash"}
        if generation and observed_hash != _digest(core):
            raise WorkLedgerError("work_ledger_state_hash_mismatch")
        if not generation and observed_hash not in {None, _digest(core)}:
            raise WorkLedgerError("work_ledger_state_hash_mismatch")
        receipts: list[WorkReceipt] = []
        previous_entry_id = ""
        for sequence, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict) or entry.get("schema_version") != ENTRY_SCHEMA:
                raise WorkLedgerError("work_ledger_entry_schema_invalid")
            if (
                entry.get("ledger_sequence") != sequence
                or entry.get("previous_entry_id") != previous_entry_id
            ):
                raise WorkLedgerError("work_ledger_chain_invalid")
            receipt_payload = entry.get("work_receipt")
            if not isinstance(receipt_payload, dict):
                raise WorkLedgerError("work_ledger_receipt_missing")
            try:
                receipt = WorkReceipt(**receipt_payload)
            except (TypeError, ValueError) as exc:
                raise WorkLedgerError("work_ledger_receipt_shape_invalid") from exc
            if not validate_work_receipt(receipt) or receipt.sequence != sequence:
                raise WorkLedgerError("work_ledger_receipt_invalid")
            entry_core = {key: value for key, value in entry.items() if key != "entry_id"}
            expected_entry_id = f"ledger:{_digest(entry_core)}"
            if entry.get("entry_id") != expected_entry_id:
                raise WorkLedgerError("work_ledger_entry_hash_mismatch")
            previous_entry_id = expected_entry_id
            receipts.append(receipt)
        return tuple(receipts)

    def _read_unlocked(self) -> tuple[dict[str, Any], tuple[WorkReceipt, ...]]:
        if not self.path.exists():
            empty = self._empty()
            return empty, ()
        try:
            raw = self.path.read_bytes()
        except OSError as exc:
            raise WorkLedgerError("work_ledger_unreadable") from exc
        payload = _parse_canonical(raw)
        return payload, self._validate(payload)

    def _write_unlocked(self, payload: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        core = {key: value for key, value in payload.items() if key != "state_hash"}
        final = {**core, "state_hash": _digest(core)}
        encoded = _canonical_json(final, newline=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                pass
            os.replace(temp_path, self.path)
            temp_path = None
        except OSError as exc:
            raise WorkLedgerError("work_ledger_atomic_write_failed") from exc
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def receipts(self) -> tuple[WorkReceipt, ...]:
        _payload, receipts = self._read_unlocked()
        return receipts

    def append(self, receipt: WorkReceipt) -> None:
        if not validate_work_receipt(receipt):
            raise WorkLedgerError("work_ledger_append_receipt_invalid")
        with _writer_lease(self.lock_path):
            payload, receipts = self._read_unlocked()
            expected_sequence = len(receipts) + 1
            if receipt.sequence != expected_sequence:
                raise WorkLedgerError("work_ledger_append_sequence_mismatch")
            if any(item.receipt_id == receipt.receipt_id for item in receipts):
                raise WorkLedgerError("work_ledger_append_replay")
            previous_entry_id = payload["entries"][-1]["entry_id"] if payload["entries"] else ""
            entry_core = {
                "schema_version": ENTRY_SCHEMA,
                "ledger_sequence": expected_sequence,
                "previous_entry_id": previous_entry_id,
                "work_receipt": receipt.to_dict(),
            }
            entry = {**entry_core, "entry_id": f"ledger:{_digest(entry_core)}"}
            updated = {
                "schema_version": STATE_SCHEMA,
                "generation": expected_sequence,
                "entries": [*payload["entries"], entry],
            }
            self._write_unlocked(updated)

    def bind_workforce(
        self,
        resolver: BrainResolver | None = None,
        *,
        thought_path: CodingThoughtPath | None = None,
    ) -> InternalCodingWorkforce:
        receipts = self.receipts()
        return provision_internal_coding_workforce(
            resolver,
            prior_work_receipts=receipts,
            receipt_sink=self.append,
            thought_path=thought_path,
        )

    def bind_agent_company_workforce(
        self,
        resolver: BrainResolver | None = None,
        *,
        thought_path: CodingThoughtPath | None = None,
    ) -> InternalCodingWorkforce:
        """Bind the canonical 41-agent/41-process fabric to this exact ledger."""

        from aureon.autonomous.aureon_agent_company_brain_fabric import (
            provision_agent_company_brain_fabric,
        )

        return provision_agent_company_brain_fabric(
            resolver,
            prior_work_receipts=self.receipts(),
            receipt_sink=self.append,
            thought_path=thought_path,
        )

    def status(self) -> dict[str, Any]:
        payload, receipts = self._read_unlocked()
        internal = [item for item in receipts if item.actor_class == INTERNAL_ACTOR]
        ten_nine_one = [
            item
            for item in internal
            if item.schema_version == WORK_SCHEMA_VERSION
            and item.thought_path_receipt_id.startswith(TRUTH_GATED_THOUGHT_RECEIPT_PREFIX)
        ]
        return {
            "schema_version": STATE_SCHEMA,
            "healthy": True,
            "generation": payload.get("generation", 0),
            "receipt_count": len(receipts),
            "last_receipt_id": receipts[-1].receipt_id if receipts else "",
            "state_hash": payload.get("state_hash", ""),
            "ten_nine_one_internal_count": len(ten_nine_one),
            "ten_nine_one_complete": len(ten_nine_one) == len(internal),
            "action_eligible": False,
            "economic_eligible": False,
        }


__all__ = [
    "DurableInternalWorkLedger",
    "ENTRY_SCHEMA",
    "STATE_SCHEMA",
    "WorkLedgerBusy",
    "WorkLedgerError",
]
