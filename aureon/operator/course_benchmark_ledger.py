"""Append-only, hash-chained evidence ledger for authorized course benchmarks."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Mapping, Sequence

SCHEMA_VERSION = "aureon-course-benchmark-ledger-v1"
GENESIS_HASH = "0" * 64
AUTHORIZED_ARTIFACT_LABELS = frozenset(
    {"provider_authorized_test", "sandbox_test"}
)
AUTHORIZED_RUNTIME_LABELS = frozenset(
    {*AUTHORIZED_ARTIFACT_LABELS, "owner_benchmark_test"}
)
ARTIFACT_KINDS = frozenset({"certificate", "download"})
_TEXT_PREDICATE_KINDS = frozenset({"ocr_contains", "ocr_absent", "vision_contains"})

_SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "credential",
    "cookie",
    "authorization",
    "otp",
    "one_time_code",
    "assessment_answer",
    "quiz_answer",
    "answer_text",
)


class LedgerIntegrityError(RuntimeError):
    """Raised when an existing ledger does not verify exactly."""


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _sensitive_key(key: str) -> bool:
    lowered = key.casefold()
    if lowered == "authorization_label":
        return False
    return lowered == "answer" or any(fragment in lowered for fragment in _SENSITIVE_KEY_FRAGMENTS)


def redact_evidence(value: object) -> object:
    """Recursively remove secrets, credentials, assessment answers, and typed text."""

    if isinstance(value, Mapping):
        source = {str(key): item for key, item in value.items()}
        action_name = str(source.get("name") or source.get("action") or "")
        redacted: dict[str, object] = {}
        for key, item in source.items():
            if _sensitive_key(key):
                redacted[key] = "[REDACTED:SENSITIVE]"
            else:
                redacted[key] = redact_evidence(item)

        if action_name == "type_text" and isinstance(source.get("params"), Mapping):
            raw_params = {str(key): item for key, item in source["params"].items()}
            raw_text = raw_params.get("text", "")
            redacted_params = redacted.get("params")
            params = dict(redacted_params) if isinstance(redacted_params, Mapping) else {}
            params["text"] = "[REDACTED:TYPED_TEXT]"
            if isinstance(raw_text, str) and not raw_text.startswith("[REDACTED:"):
                params["text_length"] = len(raw_text)
            params["redacted"] = True
            redacted["params"] = params
        predicate_kind = str(source.get("kind") or "")
        predicate_value = source.get("value")
        if predicate_kind in _TEXT_PREDICATE_KINDS and isinstance(predicate_value, str):
            encoded = predicate_value.encode("utf-8")
            redacted["value"] = "[REDACTED:PREDICATE_TEXT]"
            redacted["value_sha256"] = hashlib.sha256(encoded).hexdigest()
            redacted["value_length"] = len(predicate_value)
        return redacted
    if isinstance(value, (list, tuple)):
        return [redact_evidence(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported evidence value: {type(value).__name__}")


class CourseBenchmarkLedger:
    """Write one fsync'd JSON object per line, chained to the previous hash."""

    def __init__(
        self,
        path: str | Path,
        *,
        actor: str,
        runtime_id: str,
        build_id: str,
        run_id: str | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = Path(path)
        self.actor = self._required_label("actor", actor)
        self.runtime_id = self._required_label("runtime_id", runtime_id)
        self.build_id = self._required_label("build_id", build_id)
        self.run_id = self._required_label("run_id", run_id or uuid.uuid4().hex)
        self._now = now or (lambda: datetime.now(UTC))
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        entries = self.verify(self.path) if self.path.exists() else []
        if entries:
            expected_identity = {
                "actor": self.actor,
                "runtime_id": self.runtime_id,
                "build_id": self.build_id,
                "run_id": self.run_id,
            }
            for field_name, expected_value in expected_identity.items():
                if any(entry.get(field_name) != expected_value for entry in entries):
                    raise LedgerIntegrityError(
                        f"existing ledger {field_name} does not match this run"
                    )
        self._sequence = len(entries)
        self._previous_hash = str(entries[-1]["entry_hash"]) if entries else GENESIS_HASH

    @staticmethod
    def _required_label(name: str, value: object) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError(f"{name} is required")
        return text

    def append(self, event_type: str, payload: Mapping[str, object]) -> dict[str, object]:
        """Redact and append one event; never rewrite an existing byte."""

        event = self._required_label("event_type", event_type)
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")
        sanitized = redact_evidence(payload)
        assert isinstance(sanitized, dict)

        with self._lock:
            timestamp = self._now()
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=UTC)
            timestamp = timestamp.astimezone(UTC)
            base: dict[str, object] = {
                "schema_version": SCHEMA_VERSION,
                "sequence": self._sequence + 1,
                "timestamp_utc": timestamp.isoformat().replace("+00:00", "Z"),
                "run_id": self.run_id,
                "event_type": event,
                "actor": self.actor,
                "runtime_id": self.runtime_id,
                "build_id": self.build_id,
                "previous_hash": self._previous_hash,
                "payload": sanitized,
            }
            entry_hash = hashlib.sha256(_canonical_json(base).encode("utf-8")).hexdigest()
            entry = {**base, "entry_hash": entry_hash}
            line = _canonical_json(entry) + "\n"
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.flush()
                os.fsync(handle.fileno())
            self._sequence += 1
            self._previous_hash = entry_hash
            return entry

    def record_transition(self, record: Mapping[str, object]) -> dict[str, object]:
        """Append a GUI transition containing both pre- and post-action evidence hashes."""

        if not isinstance(record, Mapping):
            raise TypeError("transition record must be a mapping")
        before_hash = record.get("before_sha256")
        after_hash = record.get("after_sha256")
        if not _valid_sha256(before_hash) or not _valid_sha256(after_hash):
            raise ValueError("transition requires valid before_sha256 and after_sha256")
        if not isinstance(record.get("action"), Mapping):
            raise ValueError("transition requires an action mapping")
        if not isinstance(record.get("result"), Mapping):
            raise ValueError("transition requires a result mapping")
        return self.append("gui_transition", dict(record))

    def record_terminal(
        self,
        *,
        status: str,
        reason: str,
        verified_changed_transitions: int,
        success_predicate: Mapping[str, object] | None = None,
    ) -> dict[str, object]:
        """Record a terminal state without allowing unsupported completion claims."""

        terminal_status = self._required_label("status", status)
        if (
            isinstance(verified_changed_transitions, bool)
            or not isinstance(verified_changed_transitions, int)
            or verified_changed_transitions < 0
        ):
            raise ValueError("verified_changed_transitions must be a non-negative integer")
        if terminal_status == "completed":
            if not isinstance(success_predicate, Mapping) or not str(success_predicate.get("kind") or "").strip():
                raise ValueError("completed status requires an explicit success predicate")
            if verified_changed_transitions <= 0:
                raise ValueError("completed status requires verified changed-state evidence")
        return self.append(
            "runtime_terminal",
            {
                "status": terminal_status,
                "reason": str(reason or ""),
                "verified_changed_transitions": verified_changed_transitions,
                "success_predicate": dict(success_predicate or {}),
            },
        )

    def record_artifact_proof(
        self,
        file_path: str | Path,
        *,
        artifact_kind: str,
        authorization_label: str,
        provider: str,
    ) -> dict[str, object]:
        """Bind a certificate/download claim to a real, authorized local file."""

        if artifact_kind not in ARTIFACT_KINDS:
            raise ValueError(f"artifact_kind must be one of {sorted(ARTIFACT_KINDS)}")
        if authorization_label not in AUTHORIZED_ARTIFACT_LABELS:
            raise ValueError(
                "authorization_label must be an approved benchmark provenance label"
            )
        provider_name = self._required_label("provider", provider)
        path = Path(file_path).expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValueError("artifact proof requires an actual local file")
        size = path.stat().st_size
        if size <= 0:
            raise ValueError("artifact proof file must be non-empty")
        digest = _sha256_file(path)
        return self.append(
            "artifact_proof",
            {
                "artifact_kind": artifact_kind,
                "authorization_label": authorization_label,
                "provider": provider_name,
                "local_path": str(path),
                "file_name": path.name,
                "size_bytes": size,
                "sha256": digest,
                "proof_status": "verified_authorized_local_file",
            },
        )

    @staticmethod
    def verify(path: str | Path) -> list[dict[str, object]]:
        """Verify sequence numbers and every link in an existing JSONL chain."""

        ledger_path = Path(path)
        if not ledger_path.exists():
            return []
        previous_hash = GENESIS_HASH
        entries: list[dict[str, object]] = []
        with ledger_path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.endswith("\n"):
                    raise LedgerIntegrityError(f"line {line_number} is not newline-terminated")
                if not raw_line.strip():
                    raise LedgerIntegrityError(f"line {line_number} is blank")
                try:
                    parsed = json.loads(raw_line)
                except json.JSONDecodeError as exc:
                    raise LedgerIntegrityError(f"line {line_number} is invalid JSON") from exc
                if not isinstance(parsed, dict):
                    raise LedgerIntegrityError(f"line {line_number} is not a JSON object")
                if parsed.get("schema_version") != SCHEMA_VERSION:
                    raise LedgerIntegrityError(f"line {line_number} has the wrong schema")
                if parsed.get("sequence") != line_number:
                    raise LedgerIntegrityError(f"line {line_number} has a broken sequence")
                if parsed.get("previous_hash") != previous_hash:
                    raise LedgerIntegrityError(f"line {line_number} has a broken previous_hash")
                claimed_hash = parsed.get("entry_hash")
                if not _valid_sha256(claimed_hash):
                    raise LedgerIntegrityError(f"line {line_number} has an invalid entry_hash")
                base = {key: value for key, value in parsed.items() if key != "entry_hash"}
                actual_hash = hashlib.sha256(_canonical_json(base).encode("utf-8")).hexdigest()
                if claimed_hash != actual_hash:
                    raise LedgerIntegrityError(f"line {line_number} hash does not match content")
                previous_hash = str(claimed_hash)
                entries.append(parsed)
        return entries


def verify_ledger(path: str | Path) -> Sequence[Mapping[str, object]]:
    """Public convenience wrapper used by audit/read-back code."""

    return CourseBenchmarkLedger.verify(path)


__all__ = [
    "ARTIFACT_KINDS",
    "AUTHORIZED_ARTIFACT_LABELS",
    "AUTHORIZED_RUNTIME_LABELS",
    "CourseBenchmarkLedger",
    "GENESIS_HASH",
    "LedgerIntegrityError",
    "SCHEMA_VERSION",
    "redact_evidence",
    "verify_ledger",
]
