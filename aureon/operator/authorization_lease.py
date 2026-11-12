"""Time-bounded human operator authorization recorded in the release ledger.

An active lease is one input to the production release decision.  It never
opens an exchange, changes a runtime flag, or substitutes for credentials,
provider readback, risk limits, executor isolation, or release evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
import uuid
from datetime import UTC, datetime
from typing import Any, Final, Mapping

from aureon.operator.release_ledger import (
    append_release_ledger_event,
    read_operator_approval_events,
)

LEASE_SCHEMA: Final = "aureon.operator.authorization-lease.v1"
LEASE_CONFIRM: Final = "AUREON_72_HOUR_OPERATOR_AUTHORIZATION"
MAX_LEASE_SECONDS: Final = 72 * 60 * 60
TRADING_CONTROL_SCOPE: Final = (
    "AUREON_DEPLOYMENT_HOLD",
    "AUREON_DISABLE_REAL_ORDERS",
    "AUREON_DISABLE_EXCHANGE_MUTATIONS",
    "AUREON_LIVE_TRADING",
    "AUREON_ORDER_INTENT_PUBLISH",
    "AUREON_UNIFIED_ORDER_EXECUTOR",
)


def _finite_time(value: float | None) -> float:
    current = time.time() if value is None else float(value)
    if not math.isfinite(current) or current <= 0:
        raise ValueError("authorization_lease_time_invalid")
    return current


def _digest(value: Mapping[str, Any]) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def record_operator_authorization(
    *,
    action: str,
    duration_seconds: int | None = None,
    actor: str = "human-operator",
    now: float | None = None,
) -> dict[str, Any]:
    """Append a grant or revoke decision and return its public receipt."""

    current = _finite_time(now)
    if action not in {"grant", "revoke"}:
        raise ValueError("authorization_lease_action_invalid")
    if action == "grant":
        if (
            type(duration_seconds) is not int
            or duration_seconds < 60
            or duration_seconds > MAX_LEASE_SECONDS
        ):
            raise ValueError("authorization_lease_duration_invalid")
        expires_at = current + duration_seconds
    else:
        duration_seconds = 0
        expires_at = current
    lease_id = str(uuid.uuid4())
    payload = {
        "lease_schema": LEASE_SCHEMA,
        "lease_id": lease_id,
        "state": "active" if action == "grant" else "revoked",
        "scope": list(TRADING_CONTROL_SCOPE),
        "account_scope": "owner_cloud_account",
        "authorized_at": current,
        "expires_at": expires_at,
        "duration_seconds": duration_seconds,
        "constraints": [
            "current_exchange_credentials_required",
            "fresh_provider_readback_required",
            "risk_and_budget_limits_required",
            "isolated_executor_and_kill_switch_required",
            "production_release_evidence_required",
        ],
    }
    row = append_release_ledger_event(
        "operator_approval", payload, actor=actor, now=current
    )
    return {
        "schema": LEASE_SCHEMA,
        "lease_id": lease_id,
        "state": payload["state"],
        "active": action == "grant",
        "scope": list(TRADING_CONTROL_SCOPE),
        "account_scope": payload["account_scope"],
        "authorized_at": current,
        "authorized_at_iso": datetime.fromtimestamp(current, UTC).isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at,
        "expires_at_iso": datetime.fromtimestamp(expires_at, UTC).isoformat().replace("+00:00", "Z"),
        "duration_seconds": duration_seconds,
        "constraints": list(payload["constraints"]),
        "ledger_sequence": row["sequence"],
        "ledger_event_sha256": row["current_hash"],
        "lease_digest_sha256": _digest(payload),
        "release_authority": False,
        "mutation_authority": False,
    }


def build_operator_authorization_receipt(*, now: float | None = None) -> dict[str, Any]:
    """Read the latest valid operator lease without exposing ledger payloads."""

    current = _finite_time(now)
    events = read_operator_approval_events()
    latest: Mapping[str, Any] | None = None
    for row in events:
        payload = row.get("payload")
        if not isinstance(payload, Mapping) or payload.get("lease_schema") != LEASE_SCHEMA:
            continue
        if tuple(payload.get("scope") or ()) != TRADING_CONTROL_SCOPE:
            continue
        if payload.get("state") not in {"active", "revoked"}:
            continue
        issued = payload.get("authorized_at")
        expires = payload.get("expires_at")
        duration = payload.get("duration_seconds")
        if (
            isinstance(issued, bool)
            or not isinstance(issued, (int, float))
            or isinstance(expires, bool)
            or not isinstance(expires, (int, float))
            or type(duration) is not int
            or not math.isfinite(float(issued))
            or not math.isfinite(float(expires))
            or float(expires) < float(issued)
            or duration < 0
            or duration > MAX_LEASE_SECONDS
        ):
            continue
        latest = row
    if latest is None:
        return {
            "schema": LEASE_SCHEMA,
            "state": "unavailable",
            "active": False,
            "scope": list(TRADING_CONTROL_SCOPE),
            "account_scope": "owner_cloud_account",
            "authorized_at": None,
            "authorized_at_iso": None,
            "expires_at": None,
            "expires_at_iso": None,
            "remaining_seconds": 0,
            "ledger_sequence": None,
            "ledger_event_sha256": None,
            "reason_code": "operator_authorization_lease_missing",
            "release_authority": False,
            "mutation_authority": False,
        }
    payload = latest["payload"]
    issued = float(payload["authorized_at"])
    expires = float(payload["expires_at"])
    granted = payload["state"] == "active"
    active = granted and issued <= current < expires
    state = "active" if active else "revoked" if not granted else "expired"
    return {
        "schema": LEASE_SCHEMA,
        "state": state,
        "active": active,
        "scope": list(TRADING_CONTROL_SCOPE),
        "account_scope": "owner_cloud_account",
        "authorized_at": issued,
        "authorized_at_iso": datetime.fromtimestamp(issued, UTC).isoformat().replace("+00:00", "Z"),
        "expires_at": expires,
        "expires_at_iso": datetime.fromtimestamp(expires, UTC).isoformat().replace("+00:00", "Z"),
        "remaining_seconds": max(0, int(expires - current)) if active else 0,
        "ledger_sequence": latest["sequence"],
        "ledger_event_sha256": latest["current_hash"],
        "reason_code": "operator_authorization_active" if active else f"operator_authorization_{state}",
        "release_authority": False,
        "mutation_authority": False,
    }


__all__ = [
    "LEASE_CONFIRM",
    "LEASE_SCHEMA",
    "MAX_LEASE_SECONDS",
    "TRADING_CONTROL_SCOPE",
    "build_operator_authorization_receipt",
    "record_operator_authorization",
]
