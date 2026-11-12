"""Append-only production release ledger for operator evidence.

The ledger records release decisions and protected-action outcomes as hash-chained
JSONL rows. It is an evidence store only: appending a row never grants release
authority, never opens trading, and never calls an exchange, filing, payment, or
tool executor.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

EVENT_SCHEMA = "aureon.operator.release-ledger.event.v1"
RECEIPT_SCHEMA = "aureon.operator.release-ledger.v1"
LEDGER_PATH_ENV = "AUREON_RELEASE_LEDGER_PATH"
_ZERO_HASH = "0" * 64
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_PATH = _REPO_ROOT / "state" / "release_ledger.jsonl"
_MAX_PAYLOAD_BYTES = 32 * 1024
_MAX_LEDGER_BYTES = 8 * 1024 * 1024
_ALLOWED_EVENT_TYPES = {
    "service_integrated",
    "config_digest",
    "operator_approval",
    "release_decision",
    "protected_action_result",
    "manual_authorization_record",
}
_FORBIDDEN_KEYS = {
    "api_key",
    "apikey",
    "private_key",
    "secret",
    "password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "bearer",
}


def release_ledger_path() -> Path:
    configured = str(os.environ.get(LEDGER_PATH_ENV) or "").strip()
    if configured:
        return Path(configured)
    bus_trace = str(os.environ.get("AUREON_BUS_TRACE_DIR") or "").strip()
    if bus_trace:
        return Path(bus_trace) / "release_ledger.jsonl"
    return _DEFAULT_PATH


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _finite_time(value: float | None) -> float:
    current = time.time() if value is None else float(value)
    if not math.isfinite(current) or current <= 0:
        raise ValueError("release_ledger_time_must_be_positive_finite")
    return current


def _safe_text(value: Any, default: str = "operator") -> str:
    text = str(value or "").strip()
    return text[:160] if text else default


def _sensitive_path(value: Any, path: str = "payload") -> str | None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key).strip()
            lowered = key_text.lower().replace("-", "_")
            next_path = f"{path}.{key_text}" if key_text else path
            if (
                lowered in _FORBIDDEN_KEYS
                or lowered.endswith("_token")
                or lowered.endswith("_secret")
                or lowered.endswith("_api_key")
                or lowered.endswith("_password")
                or "private_key" in lowered
            ):
                return next_path
            found = _sensitive_path(nested, next_path)
            if found:
                return found
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            found = _sensitive_path(nested, f"{path}[{index}]")
            if found:
                return found
    return None


def _clean_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise ValueError("release_ledger_payload_must_be_object")
    sensitive = _sensitive_path(payload)
    if sensitive:
        raise ValueError(f"release_ledger_payload_contains_sensitive_key:{sensitive}")
    body = _canonical(payload)
    if len(body.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise ValueError("release_ledger_payload_too_large")
    return json.loads(body)


def _event_projection(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sequence": row.get("sequence"),
        "event_type": row.get("event_type"),
        "actor": row.get("actor"),
        "recorded_at": row.get("recorded_at"),
        "recorded_at_iso": row.get("recorded_at_iso"),
        "payload_digest_sha256": row.get("payload_digest_sha256"),
        "previous_hash": row.get("previous_hash"),
        "current_hash": row.get("current_hash"),
        "release_authority": row.get("release_authority"),
        "mutation_authority": row.get("mutation_authority"),
    }


def _causal(row: Mapping[str, Any]) -> dict[str, Any]:
    return {key: row[key] for key in sorted(row) if key != "current_hash"}


def _read_raw_rows(path: Path | None = None) -> tuple[list[dict[str, Any]], list[int], str | None]:
    ledger_path = release_ledger_path() if path is None else path
    if not ledger_path.exists():
        return [], [], None
    try:
        if ledger_path.stat().st_size > _MAX_LEDGER_BYTES:
            return [], [], "release_ledger_exceeds_read_limit"
        rows: list[dict[str, Any]] = []
        invalid: list[int] = []
        for index, line in enumerate(ledger_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                invalid.append(index)
                continue
            if isinstance(row, dict):
                rows.append(row)
            else:
                invalid.append(index)
        return rows, invalid, None
    except OSError as exc:
        return [], [], f"release_ledger_read_failed:{type(exc).__name__}"


def _validate_chain(rows: list[dict[str, Any]], invalid_lines: list[int] | None = None, read_error: str | None = None) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    previous = _ZERO_HASH
    latest = _ZERO_HASH
    if read_error:
        failures.append({"line": None, "reason": read_error})
    for line, row in enumerate(rows, start=1):
        if row.get("schema") != EVENT_SCHEMA:
            failures.append({"line": line, "reason": "schema_mismatch"})
        if row.get("sequence") != line:
            failures.append({"line": line, "reason": "sequence_mismatch"})
        if row.get("previous_hash") != previous:
            failures.append({"line": line, "reason": "previous_hash_mismatch"})
        try:
            expected = _sha(_causal(row))
        except (TypeError, ValueError):
            expected = ""
        if row.get("current_hash") != expected:
            failures.append({"line": line, "reason": "current_hash_mismatch"})
        latest = str(row.get("current_hash") or "") if len(str(row.get("current_hash") or "")) == 64 else latest
        previous = latest
    for line in invalid_lines or []:
        failures.append({"line": line, "reason": "invalid_json_line"})
    return {
        "chain_valid": not failures,
        "failure_count": len(failures),
        "failures": failures[:12],
        "latest_hash": latest if rows else None,
    }


def append_release_ledger_event(
    event_type: str,
    payload: Mapping[str, Any],
    *,
    actor: str = "operator",
    now: float | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    event = str(event_type or "").strip()
    if event not in _ALLOWED_EVENT_TYPES:
        raise ValueError("release_ledger_event_type_unavailable")
    current = _finite_time(now)
    clean = _clean_payload(payload)
    ledger_path = release_ledger_path() if path is None else path
    rows, invalid, read_error = _read_raw_rows(ledger_path)
    validation = _validate_chain(rows, invalid, read_error)
    if not validation["chain_valid"]:
        raise ValueError("release_ledger_chain_invalid")
    previous = validation.get("latest_hash") or _ZERO_HASH
    causal = {
        "schema": EVENT_SCHEMA,
        "sequence": len(rows) + 1,
        "event_type": event,
        "actor": _safe_text(actor),
        "recorded_at": current,
        "recorded_at_iso": datetime.fromtimestamp(current, UTC).isoformat().replace("+00:00", "Z"),
        "payload_digest_sha256": _sha(clean),
        "payload": clean,
        "previous_hash": previous,
        "generated_values": False,
        "release_authority": False,
        "mutation_authority": False,
    }
    row = {**causal, "current_hash": _sha(causal)}
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as handle:
        handle.write(_canonical(row) + "\n")
    return row


def read_release_ledger(*, path: Path | None = None, limit: int = 25) -> dict[str, Any]:
    ledger_path = release_ledger_path() if path is None else path
    rows, invalid, read_error = _read_raw_rows(ledger_path)
    validation = _validate_chain(rows, invalid, read_error)
    projected = [_event_projection(row) for row in rows[-max(1, min(int(limit), 100)):]]
    return {
        "path_digest_sha256": hashlib.sha256(str(ledger_path.resolve()).encode("utf-8", errors="replace")).hexdigest(),
        "storage_state": "present" if ledger_path.exists() else "empty",
        "event_count": len(rows),
        "invalid_json_line_count": len(invalid),
        "chain_valid": validation["chain_valid"],
        "failure_count": validation["failure_count"],
        "failures": validation["failures"],
        "latest_hash": validation["latest_hash"],
        "latest_event_type": rows[-1].get("event_type") if rows else None,
        "recent_events": projected,
    }


def read_operator_approval_events(*, path: Path | None = None) -> list[dict[str, Any]]:
    """Return validated approval rows for trusted in-process receipt builders.

    This helper is not an HTTP projection.  It refuses the complete result if
    any row or hash-chain link is invalid.
    """

    rows, invalid, read_error = _read_raw_rows(path)
    if not _validate_chain(rows, invalid, read_error)["chain_valid"]:
        return []
    return [dict(row) for row in rows if row.get("event_type") == "operator_approval"]


def build_release_ledger_receipt(*, path: Path | None = None, limit: int = 25, now: float | None = None) -> dict[str, Any]:
    current = _finite_time(now)
    readback = read_release_ledger(path=path, limit=limit)
    return {
        "schema": RECEIPT_SCHEMA,
        "generated_values": False,
        "observed_at": current,
        "observed_at_iso": datetime.fromtimestamp(current, UTC).isoformat().replace("+00:00", "Z"),
        "read_route": "/api/operator/release-ledger",
        "append_route": "/api/operator/release-ledger/events",
        "append_route_mode": "operator_only_hnc_protected",
        "event_schema": EVENT_SCHEMA,
        "ledger": readback,
        "available": readback["chain_valid"],
        "production_ready": False,
        "release_authority": False,
        "mutation_authority": False,
    }


__all__ = [
    "EVENT_SCHEMA",
    "RECEIPT_SCHEMA",
    "append_release_ledger_event",
    "build_release_ledger_receipt",
    "read_release_ledger",
    "read_operator_approval_events",
    "release_ledger_path",
]

