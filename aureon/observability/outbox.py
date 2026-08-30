"""Bounded, local-only durable outbox for sanitized observability events.

The outbox deliberately has no exporter or provider integration. Callers may
read pending envelopes and later supply a receipt, but only an exact receipt
for the stored event can change its delivery state.
"""

from __future__ import annotations

import errno
import hashlib
import json
import math
import os
import re
import tempfile
import threading
import time
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .runtime import current_correlation_id, redact_observability_value, safe_observability_event

STATE_SCHEMA = "aureon.observability.outbox.v1"
ITEM_SCHEMA = "aureon.observability.outbox-item.v1"
RECEIPT_SCHEMA = "aureon.observability.delivery-receipt.v1"

_HEX_64_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX_16_RE = re.compile(r"^[0-9a-f]{16}$")
_EVENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_CORRELATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,63}$")
_RECEIPT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_KEY_SEP_RE = re.compile(r"[^a-z0-9]+")
_DIAGNOSTIC_KEYS = {
    "error_message",
    "exc_info",
    "exception",
    "exception_message",
    "local_variables",
    "locals",
    "message",
    "messages",
    "stack",
    "stack_trace",
    "stacktrace",
    "traceback",
}
_SENSITIVE_KEY_PARTS = {
    "auth",
    "authorization",
    "cookie",
    "credential",
    "credentials",
    "jwt",
    "passwd",
    "password",
    "secret",
    "session",
    "token",
}
_SENSITIVE_KEY_PHRASES = {
    "access_key",
    "api_key",
    "encryption_key",
    "private_key",
    "signing_key",
}
_RESERVED_PAYLOAD_KEYS = {
    "correlation_id",
    "event",
    "exception_fingerprint",
    "exception_type",
    "schema",
}
_RECEIPT_KEYS = {
    "schema",
    "event_id",
    "payload_sha256",
    "receipt_id",
    "delivered_at_unix_ns",
}


class OutboxError(RuntimeError):
    """Base error for durable outbox operations."""


class OutboxBusyError(OutboxError):
    """Raised immediately when another writer owns the single-writer lease."""


class OutboxCorruptionError(OutboxError):
    """Raised when persisted state cannot be verified exactly."""


class OutboxUnavailableError(OutboxError):
    """Raised when local state storage cannot be accessed."""


class OutboxCapacityError(OutboxError):
    """Raised when one event cannot fit inside the configured byte bound."""


class OutboxIdempotencyConflictError(OutboxError):
    """Raised when one idempotency identity is reused for different payloads."""


class OutboxReceiptError(OutboxError):
    """Raised when a delivery receipt does not exactly match a stored event."""


@dataclass(frozen=True)
class OutboxHealth:
    """Secret-free health snapshot suitable for readiness reporting."""

    healthy: bool
    code: str
    generation: int | None
    pending_count: int
    delivered_count: int
    state_bytes: int
    dropped_age: int
    dropped_count: int
    dropped_bytes: int


_THREAD_LOCKS_GUARD = threading.Lock()
_THREAD_LOCKS: dict[str, threading.Lock] = {}


def _thread_lock_for(path: Path) -> threading.Lock:
    key = os.path.normcase(str(path.resolve(strict=False)))
    with _THREAD_LOCKS_GUARD:
        return _THREAD_LOCKS.setdefault(key, threading.Lock())


def _try_lock_file(handle: Any) -> None:
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"\0")
        handle.flush()
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_file(handle: Any) -> None:
    handle.seek(0)
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def _writer_lease(lock_path: Path) -> Iterator[None]:
    """Acquire the thread and process writer locks without waiting."""
    thread_lock = _thread_lock_for(lock_path)
    if not thread_lock.acquire(blocking=False):
        raise OutboxBusyError("observability outbox writer is busy")
    handle = None
    locked = False
    try:
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = lock_path.open("a+b")
        except OSError as exc:
            raise OutboxUnavailableError("observability outbox lock is unavailable") from exc
        try:
            _try_lock_file(handle)
            locked = True
        except OSError as exc:
            if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK, errno.EPERM}:
                raise OutboxUnavailableError("observability outbox lock failed") from exc
            raise OutboxBusyError("observability outbox writer is busy") from None
        yield
    finally:
        if handle is not None:
            if locked:
                try:
                    _unlock_file(handle)
                except OSError:
                    pass
            handle.close()
        thread_lock.release()


def _canonical_json(value: Any, *, newline: bool = False) -> bytes:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return encoded + (b"\n" if newline else b"")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    raise ValueError("non-finite JSON constant")


def _parse_canonical_json(raw: bytes) -> dict[str, Any]:
    try:
        parsed = json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, ValueError, TypeError) as exc:
        raise OutboxCorruptionError("observability outbox state is corrupt") from exc
    if not isinstance(parsed, dict) or raw != _canonical_json(parsed, newline=True):
        raise OutboxCorruptionError("observability outbox state is not canonical")
    return parsed


def _normalized_key(key: str) -> str:
    value = _CAMEL_BOUNDARY_RE.sub("_", key).lower()
    return _KEY_SEP_RE.sub("_", value).strip("_")


def _strip_diagnostics(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            normalized = _normalized_key(key)
            if normalized in _DIAGNOSTIC_KEYS:
                continue
            parts = set(normalized.split("_"))
            if parts.intersection(_SENSITIVE_KEY_PARTS) or any(
                phrase in normalized for phrase in _SENSITIVE_KEY_PHRASES
            ):
                result[key] = "[REDACTED]"
            else:
                result[key] = _strip_diagnostics(item)
        return result
    if isinstance(value, list):
        return [_strip_diagnostics(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return "[NON_FINITE]"
    return value


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_plain_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _empty_body() -> dict[str, Any]:
    return {
        "schema": STATE_SCHEMA,
        "generation": 0,
        "retention": {"dropped_age": 0, "dropped_count": 0, "dropped_bytes": 0},
        "items": [],
    }


def _sealed_state(body: Mapping[str, Any]) -> dict[str, Any]:
    checksum = _sha256(_canonical_json(body))
    return {**body, "checksum_sha256": checksum}


def _state_bytes(body: Mapping[str, Any]) -> bytes:
    return _canonical_json(_sealed_state(body), newline=True)


def _validated_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise OutboxReceiptError("delivery receipt must be a mapping")
    if any(not isinstance(key, str) for key in receipt):
        raise OutboxReceiptError("delivery receipt has invalid keys")
    result = dict(receipt)
    if set(result) != _RECEIPT_KEYS:
        raise OutboxReceiptError("delivery receipt fields do not match the contract")
    if result["schema"] != RECEIPT_SCHEMA:
        raise OutboxReceiptError("delivery receipt schema does not match")
    if not isinstance(result["event_id"], str) or not _HEX_64_RE.fullmatch(result["event_id"]):
        raise OutboxReceiptError("delivery receipt event identity is invalid")
    if not isinstance(result["payload_sha256"], str) or not _HEX_64_RE.fullmatch(
        result["payload_sha256"]
    ):
        raise OutboxReceiptError("delivery receipt payload identity is invalid")
    if not isinstance(result["receipt_id"], str) or not _RECEIPT_ID_RE.fullmatch(
        result["receipt_id"]
    ):
        raise OutboxReceiptError("delivery receipt identity is invalid")
    if not _is_plain_int(result["delivered_at_unix_ns"]) or result["delivered_at_unix_ns"] < 0:
        raise OutboxReceiptError("delivery receipt time is invalid")
    return result


def _validate_item(item: Any, seen_ids: set[str]) -> None:
    expected_keys = {
        "schema",
        "event_id",
        "payload_sha256",
        "created_at_unix_ns",
        "payload",
        "delivery",
    }
    if not isinstance(item, dict) or set(item) != expected_keys:
        raise OutboxCorruptionError("observability outbox item is malformed")
    event_id = item["event_id"]
    if item["schema"] != ITEM_SCHEMA or not isinstance(event_id, str) or not _HEX_64_RE.fullmatch(
        event_id
    ):
        raise OutboxCorruptionError("observability outbox item identity is invalid")
    if event_id in seen_ids:
        raise OutboxCorruptionError("observability outbox contains duplicate identities")
    seen_ids.add(event_id)
    if not _is_plain_int(item["created_at_unix_ns"]) or item["created_at_unix_ns"] < 0:
        raise OutboxCorruptionError("observability outbox item time is invalid")

    payload = item["payload"]
    if not isinstance(payload, dict):
        raise OutboxCorruptionError("observability outbox payload is malformed")
    if payload.get("schema") != "aureon.observability.v1":
        raise OutboxCorruptionError("observability outbox payload schema is invalid")
    if not isinstance(payload.get("event"), str) or not _EVENT_RE.fullmatch(payload["event"]):
        raise OutboxCorruptionError("observability outbox event name is invalid")
    if not isinstance(payload.get("correlation_id"), str) or not _CORRELATION_RE.fullmatch(
        payload["correlation_id"]
    ):
        raise OutboxCorruptionError("observability outbox correlation identity is invalid")
    if payload != _strip_diagnostics(redact_observability_value(payload)):
        raise OutboxCorruptionError("observability outbox payload is not sanitized")
    exception_type = payload.get("exception_type")
    exception_fingerprint = payload.get("exception_fingerprint")
    if (exception_type is None) != (exception_fingerprint is None):
        raise OutboxCorruptionError("observability outbox exception identity is incomplete")
    if exception_type is not None and (
        not isinstance(exception_type, str)
        or not exception_type
        or len(exception_type) > 128
        or not isinstance(exception_fingerprint, str)
        or not _HEX_16_RE.fullmatch(exception_fingerprint)
    ):
        raise OutboxCorruptionError("observability outbox exception identity is invalid")

    payload_sha256 = item["payload_sha256"]
    if not isinstance(payload_sha256, str) or payload_sha256 != _sha256(_canonical_json(payload)):
        raise OutboxCorruptionError("observability outbox payload checksum does not match")

    delivery = item["delivery"]
    if delivery is not None:
        try:
            verified = _validated_receipt(delivery)
        except OutboxReceiptError as exc:
            raise OutboxCorruptionError("observability outbox receipt is malformed") from exc
        if verified["event_id"] != event_id or verified["payload_sha256"] != payload_sha256:
            raise OutboxCorruptionError("observability outbox receipt does not match its item")
        if verified["delivered_at_unix_ns"] < item["created_at_unix_ns"]:
            raise OutboxCorruptionError("observability outbox receipt predates its item")


def _validated_body(parsed: dict[str, Any]) -> dict[str, Any]:
    expected_keys = {"schema", "generation", "retention", "items", "checksum_sha256"}
    if set(parsed) != expected_keys:
        raise OutboxCorruptionError("observability outbox state shape is invalid")
    checksum = parsed["checksum_sha256"]
    if not isinstance(checksum, str) or not _HEX_64_RE.fullmatch(checksum):
        raise OutboxCorruptionError("observability outbox state checksum is invalid")
    body = {key: value for key, value in parsed.items() if key != "checksum_sha256"}
    if checksum != _sha256(_canonical_json(body)):
        raise OutboxCorruptionError("observability outbox state checksum does not match")
    if body["schema"] != STATE_SCHEMA:
        raise OutboxCorruptionError("observability outbox state schema is invalid")
    if not _is_plain_int(body["generation"]) or body["generation"] < 0:
        raise OutboxCorruptionError("observability outbox generation is invalid")

    retention = body["retention"]
    retention_keys = {"dropped_age", "dropped_count", "dropped_bytes"}
    if not isinstance(retention, dict) or set(retention) != retention_keys:
        raise OutboxCorruptionError("observability outbox retention state is invalid")
    if any(not _is_plain_int(value) or value < 0 for value in retention.values()):
        raise OutboxCorruptionError("observability outbox retention counters are invalid")

    items = body["items"]
    if not isinstance(items, list):
        raise OutboxCorruptionError("observability outbox items are invalid")
    seen_ids: set[str] = set()
    previous_created_at = -1
    for item in items:
        _validate_item(item, seen_ids)
        if item["created_at_unix_ns"] < previous_created_at:
            raise OutboxCorruptionError("observability outbox items are out of order")
        previous_created_at = item["created_at_unix_ns"]
    return body


def _atomic_replace(path: Path, content: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
        )
    except OSError as exc:
        raise OutboxUnavailableError("observability outbox state is unavailable") from exc
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if os.name != "nt" and hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except OSError as exc:
        raise OutboxUnavailableError("observability outbox atomic replace failed") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


class DurableObservabilityOutbox:
    """Canonical local outbox with bounded retention and exact acknowledgements."""

    def __init__(
        self,
        state_path: str | os.PathLike[str],
        *,
        max_events: int = 1_000,
        max_bytes: int = 4 * 1024 * 1024,
        max_age_seconds: float = 7 * 24 * 60 * 60,
        clock_ns: Callable[[], int] = time.time_ns,
    ) -> None:
        if not _is_plain_int(max_events) or max_events < 1:
            raise ValueError("max_events must be a positive integer")
        if not _is_plain_int(max_bytes) or max_bytes < 512:
            raise ValueError("max_bytes must be an integer of at least 512")
        if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, (int, float)):
            raise ValueError("max_age_seconds must be a positive finite number")
        if not math.isfinite(float(max_age_seconds)) or max_age_seconds <= 0:
            raise ValueError("max_age_seconds must be a positive finite number")
        if not callable(clock_ns):
            raise TypeError("clock_ns must be callable")

        self.state_path = Path(state_path)
        if not self.state_path.name:
            raise ValueError("state_path must name a file")
        self.lock_path = self.state_path.with_name(f"{self.state_path.name}.lock")
        self.max_events = max_events
        self.max_bytes = max_bytes
        self.max_age_ns = int(float(max_age_seconds) * 1_000_000_000)
        self._clock_ns = clock_ns

    def _now_ns(self) -> int:
        value = self._clock_ns()
        if not _is_plain_int(value) or value < 0:
            raise OutboxUnavailableError("observability outbox clock is invalid")
        return value

    def _read_body(self) -> tuple[dict[str, Any], int]:
        try:
            raw = self.state_path.read_bytes()
        except FileNotFoundError:
            return _empty_body(), 0
        except OSError as exc:
            raise OutboxUnavailableError("observability outbox state is unavailable") from exc
        parsed = _parse_canonical_json(raw)
        return _validated_body(parsed), len(raw)

    @contextmanager
    def _exclusive_writer(self) -> Iterator[None]:
        with _writer_lease(self.lock_path):
            yield

    @staticmethod
    def _copy(value: Any) -> Any:
        return json.loads(_canonical_json(value).decode("utf-8"))

    @staticmethod
    def _idempotency_identity(idempotency_key: str | bytes) -> str:
        if isinstance(idempotency_key, str):
            raw_key = idempotency_key.encode("utf-8")
        elif isinstance(idempotency_key, bytes):
            raw_key = idempotency_key
        else:
            raise TypeError("idempotency_key must be text or bytes")
        if not raw_key or len(raw_key) > 4_096:
            raise ValueError("idempotency_key must contain between 1 and 4096 bytes")
        return _sha256(ITEM_SCHEMA.encode("ascii") + b"\0" + raw_key)

    def _build_item(
        self,
        event: str,
        *,
        idempotency_key: str | bytes,
        correlation_id: Any,
        fields: Mapping[str, Any] | None,
        exception: BaseException | None,
        created_at_unix_ns: int,
    ) -> dict[str, Any]:
        if not isinstance(event, str) or not _EVENT_RE.fullmatch(event):
            raise ValueError("event must be a conservative name of at most 128 characters")
        if fields is not None and not isinstance(fields, Mapping):
            raise TypeError("fields must be a mapping")

        event_id = self._idempotency_identity(idempotency_key)
        requested_id = correlation_id if correlation_id is not None else current_correlation_id()
        if not isinstance(requested_id, str) or not _CORRELATION_RE.fullmatch(requested_id):
            requested_id = f"obs-{event_id[:32]}"

        safe_fields = redact_observability_value(dict(fields or {}))
        if not isinstance(safe_fields, dict):
            safe_fields = {}
        safe_fields = _strip_diagnostics(safe_fields)
        safe_fields = {
            key: value
            for key, value in safe_fields.items()
            if _normalized_key(key) not in _RESERVED_PAYLOAD_KEYS
        }
        payload = safe_observability_event(
            event,
            correlation_id=requested_id,
            fields=safe_fields,
            exception=exception,
        )
        payload = _strip_diagnostics(payload)
        payload_sha256 = _sha256(_canonical_json(payload))
        return {
            "schema": ITEM_SCHEMA,
            "event_id": event_id,
            "payload_sha256": payload_sha256,
            "created_at_unix_ns": created_at_unix_ns,
            "payload": payload,
            "delivery": None,
        }

    def _apply_retention(
        self,
        body: dict[str, Any],
        *,
        now_ns: int,
        protected_event_id: str | None = None,
    ) -> int:
        removed = 0
        cutoff = max(0, now_ns - self.max_age_ns)
        retained = [item for item in body["items"] if item["created_at_unix_ns"] >= cutoff]
        dropped_age = len(body["items"]) - len(retained)
        if dropped_age:
            body["items"] = retained
            body["retention"]["dropped_age"] += dropped_age
            removed += dropped_age

        dropped_count = max(0, len(body["items"]) - self.max_events)
        if dropped_count:
            del body["items"][:dropped_count]
            body["retention"]["dropped_count"] += dropped_count
            removed += dropped_count

        while body["items"] and len(_state_bytes(body)) > self.max_bytes:
            del body["items"][0]
            body["retention"]["dropped_bytes"] += 1
            removed += 1

        if len(_state_bytes(body)) > self.max_bytes:
            raise OutboxCapacityError("observability outbox metadata exceeds its byte bound")
        if protected_event_id is not None and not any(
            item["event_id"] == protected_event_id for item in body["items"]
        ):
            raise OutboxCapacityError("observability event exceeds its retention byte bound")
        return removed

    def enqueue(
        self,
        event: str,
        *,
        idempotency_key: str | bytes,
        correlation_id: Any = None,
        fields: Mapping[str, Any] | None = None,
        exception: BaseException | None = None,
    ) -> dict[str, Any]:
        """Persist one sanitized event or return its exact prior replay."""
        now_ns = self._now_ns()
        candidate = self._build_item(
            event,
            idempotency_key=idempotency_key,
            correlation_id=correlation_id,
            fields=fields,
            exception=exception,
            created_at_unix_ns=now_ns,
        )
        with self._exclusive_writer():
            body, _ = self._read_body()
            existing = next(
                (item for item in body["items"] if item["event_id"] == candidate["event_id"]),
                None,
            )
            if existing is not None:
                if existing["payload_sha256"] != candidate["payload_sha256"]:
                    raise OutboxIdempotencyConflictError(
                        "idempotency identity is already bound to another payload"
                    )
                return self._copy(existing)

            if body["items"] and candidate["created_at_unix_ns"] < body["items"][-1][
                "created_at_unix_ns"
            ]:
                candidate["created_at_unix_ns"] = body["items"][-1]["created_at_unix_ns"]
            body["items"].append(candidate)
            body["generation"] += 1
            self._apply_retention(body, now_ns=now_ns, protected_event_id=candidate["event_id"])
            _atomic_replace(self.state_path, _state_bytes(body))
            return self._copy(candidate)

    def pending(self, *, limit: int | None = None) -> tuple[dict[str, Any], ...]:
        """Read verified pending envelopes without taking the writer lease."""
        if limit is not None and (not _is_plain_int(limit) or limit < 0):
            raise ValueError("limit must be a non-negative integer or None")
        body, _ = self._read_body()
        items = [item for item in body["items"] if item["delivery"] is None]
        if limit is not None:
            items = items[:limit]
        return tuple(self._copy(item) for item in items)

    def items(self) -> tuple[dict[str, Any], ...]:
        """Read every verified envelope, including retained delivery receipts."""
        body, _ = self._read_body()
        return tuple(self._copy(item) for item in body["items"])

    def deliver(
        self,
        event_id: str,
        sink: Callable[[dict[str, Any]], Mapping[str, Any]],
    ) -> dict[str, Any]:
        """Call a caller-owned sink, then accept only its exact returned receipt.

        The sink is intentionally injected: this module has no network client or
        provider implementation. A raised sink exception or invalid receipt occurs
        before any delivery-state mutation, so the event remains pending.
        """
        if not isinstance(event_id, str) or not _HEX_64_RE.fullmatch(event_id):
            raise ValueError("event_id must be a lowercase SHA-256 identity")
        if not callable(sink):
            raise TypeError("sink must be callable")
        item = next((candidate for candidate in self.pending() if candidate["event_id"] == event_id), None)
        if item is None:
            raise OutboxReceiptError("delivery target is not pending")
        receipt = sink(self._copy(item))
        if not isinstance(receipt, Mapping):
            raise OutboxReceiptError("delivery sink did not return a receipt mapping")
        return self.mark_delivered(receipt)

    def mark_delivered(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        """Mark one item delivered only when every receipt binding matches."""
        verified_receipt = _validated_receipt(receipt)
        with self._exclusive_writer():
            body, _ = self._read_body()
            item = next(
                (
                    candidate
                    for candidate in body["items"]
                    if candidate["event_id"] == verified_receipt["event_id"]
                ),
                None,
            )
            if item is None:
                raise OutboxReceiptError("delivery receipt references an unknown event")
            if item["payload_sha256"] != verified_receipt["payload_sha256"]:
                raise OutboxReceiptError("delivery receipt payload does not match")
            if verified_receipt["delivered_at_unix_ns"] < item["created_at_unix_ns"]:
                raise OutboxReceiptError("delivery receipt predates its event")
            if item["delivery"] is not None:
                if item["delivery"] != verified_receipt:
                    raise OutboxReceiptError("event is already bound to another receipt")
                return self._copy(item)
            if any(
                candidate["delivery"] is not None
                and candidate["delivery"]["receipt_id"] == verified_receipt["receipt_id"]
                for candidate in body["items"]
                if candidate["event_id"] != item["event_id"]
            ):
                raise OutboxReceiptError("delivery receipt identity is already bound")

            item["delivery"] = verified_receipt
            delivered_item = self._copy(item)
            body["generation"] += 1
            self._apply_retention(body, now_ns=self._now_ns())
            _atomic_replace(self.state_path, _state_bytes(body))
            return delivered_item

    def prune(self) -> OutboxHealth:
        """Apply age, count, and byte bounds under the single-writer lease."""
        now_ns = self._now_ns()
        with self._exclusive_writer():
            body, prior_bytes = self._read_body()
            candidate = self._copy(body)
            candidate["generation"] += 1
            removed = self._apply_retention(candidate, now_ns=now_ns)
            if removed:
                content = _state_bytes(candidate)
                _atomic_replace(self.state_path, content)
                return self._health_from_body(candidate, len(content), now_ns=now_ns)
            return self._health_from_body(body, prior_bytes, now_ns=now_ns)

    def _health_from_body(
        self, body: dict[str, Any], state_bytes: int, *, now_ns: int
    ) -> OutboxHealth:
        pending_count = sum(item["delivery"] is None for item in body["items"])
        delivered_count = len(body["items"]) - pending_count
        cutoff = max(0, now_ns - self.max_age_ns)
        retention_due = (
            len(body["items"]) > self.max_events
            or state_bytes > self.max_bytes
            or any(item["created_at_unix_ns"] < cutoff for item in body["items"])
        )
        retention = body["retention"]
        return OutboxHealth(
            healthy=not retention_due,
            code="retention_due" if retention_due else "ok",
            generation=body["generation"],
            pending_count=pending_count,
            delivered_count=delivered_count,
            state_bytes=state_bytes,
            dropped_age=retention["dropped_age"],
            dropped_count=retention["dropped_count"],
            dropped_bytes=retention["dropped_bytes"],
        )

    def health(self) -> OutboxHealth:
        """Return a secret-free health result; corruption is never overwritten."""
        try:
            body, state_bytes = self._read_body()
            return self._health_from_body(body, state_bytes, now_ns=self._now_ns())
        except OutboxCorruptionError:
            return OutboxHealth(False, "corrupt_state", None, 0, 0, 0, 0, 0, 0)
        except OutboxUnavailableError:
            return OutboxHealth(False, "unavailable_state", None, 0, 0, 0, 0, 0, 0)


__all__ = [
    "DurableObservabilityOutbox",
    "ITEM_SCHEMA",
    "OutboxBusyError",
    "OutboxCapacityError",
    "OutboxCorruptionError",
    "OutboxError",
    "OutboxHealth",
    "OutboxIdempotencyConflictError",
    "OutboxReceiptError",
    "OutboxUnavailableError",
    "RECEIPT_SCHEMA",
    "STATE_SCHEMA",
]
