"""Durable order lifecycle evidence for live trading continuity.

This module does not place orders. It records the proof chain that ties a
runtime candidate to an intent, an executor attempt, a broker acknowledgement,
an open position, a verified close, and the final outcome evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "aureon-order-lifecycle-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = Path("state/unified_order_lifecycle_latest.json")
LOG_PATH = Path("state/unified_order_lifecycle_events.jsonl")
PUBLIC_PATH = Path("frontend/public/aureon_unified_order_lifecycle.json")

TERMINAL_STATUSES = {
    "position_closed",
    "outcome_recorded",
    "order_blocked",
    "order_cancelled",
    "order_expired",
    "order_rate_limited",
    "order_rejected",
    "order_failed",
    "close_failed",
    "lifecycle_cancelled",
}
ACTIVE_ORDER_STATUSES = {
    "order_submitted",
    "submit_timeout_unverified",
    "broker_acknowledged",
    "partial_fill",
    "position_open",
    "close_requested",
    "close_acknowledged",
}
CONTINUITY_CHAIN = [
    "candidate_ready",
    "intent_published",
    "executor_accepted",
    "order_submitted",
    "broker_acknowledged",
    "position_open",
    "close_requested",
    "close_acknowledged",
    "position_closed",
    "outcome_recorded",
]
BROKER_CORRELATION_FIELDS = [
    "lifecycle_id",
    "candidate_id",
    "intent_id",
    "route_key",
    "client_order_id",
    "broker_order_id",
    "deal_reference",
    "deal_id",
    "venue_status",
    "filled_qty",
    "remaining_qty",
    "avg_fill_price",
    "fees",
    "verification_source",
    "proof_mode",
    "proof_tier",
    "broker_environment",
    "account_mode",
    "broker_call_id",
    "idempotency_key",
    "round_trip_ms",
    "request_timestamp",
    "response_timestamp",
    "credential_scope",
    "mutation_scope",
]
PROOF_TIERS = {"mock_broker", "sandbox_paper"}
SANDBOX_PAPER_FIELDS = [
    "proof_tier",
    "broker_environment",
    "account_mode",
    "broker_call_id",
    "idempotency_key",
    "round_trip_ms",
    "request_timestamp",
    "response_timestamp",
    "credential_scope",
    "mutation_scope",
]
ALLOWED_STATUS_TRANSITIONS = {
    "runtime_started": {"data_ready", "order_blocked"},
    "data_ready": {"candidate_ready", "order_blocked"},
    "candidate_ready": {"intent_published", "order_blocked"},
    "intent_published": {"executor_accepted", "order_blocked"},
    "executor_accepted": {"order_submitted", "order_blocked"},
    "order_submitted": {
        "broker_acknowledged",
        "submit_timeout_unverified",
        "order_rejected",
        "order_failed",
        "order_cancelled",
        "order_expired",
        "order_rate_limited",
    },
    "submit_timeout_unverified": {"broker_acknowledged", "order_rejected", "order_failed", "order_cancelled", "order_expired"},
    "broker_acknowledged": {"partial_fill", "position_open", "order_rejected", "order_cancelled", "order_expired", "order_failed"},
    "partial_fill": {"partial_fill", "position_open", "order_cancelled", "order_expired", "order_failed"},
    "position_open": {"close_requested", "position_closed"},
    "close_requested": {"close_acknowledged", "close_failed"},
    "close_acknowledged": {"position_closed", "close_failed"},
    "position_closed": {"outcome_recorded"},
}
BROKER_STATUS_MAP = {
    "capital": {
        "accepted": "broker_acknowledged",
        "open": "position_open",
        "position_open": "position_open",
        "closed": "position_closed",
        "position_closed": "position_closed",
        "close_accepted": "close_acknowledged",
        "close_acknowledged": "close_acknowledged",
        "rejected": "order_rejected",
        "failed": "order_failed",
        "stale": "order_blocked",
    },
    "alpaca": {
        "accepted": "broker_acknowledged",
        "new": "broker_acknowledged",
        "partially_filled": "partial_fill",
        "filled": "position_open",
        "done_for_day": "order_cancelled",
        "canceled": "order_cancelled",
        "expired": "order_expired",
        "rejected": "order_rejected",
        "suspended": "order_failed",
        "stale": "order_blocked",
    },
    "binance": {
        "new": "broker_acknowledged",
        "partially_filled": "partial_fill",
        "filled": "position_open",
        "canceled": "order_cancelled",
        "expired": "order_expired",
        "rejected": "order_rejected",
        "timeout": "submit_timeout_unverified",
        "5xx_unknown": "submit_timeout_unverified",
        "rate_limit": "order_rate_limited",
        "too_many_orders": "order_rate_limited",
        "stale": "order_blocked",
    },
    "kraken": {
        "pending": "broker_acknowledged",
        "open": "broker_acknowledged",
        "partial": "partial_fill",
        "partially_filled": "partial_fill",
        "closed": "position_open",
        "filled": "position_open",
        "canceled": "order_cancelled",
        "expired": "order_expired",
        "rejected": "order_rejected",
        "stale": "order_blocked",
    },
}
CORE_CORRELATION_FIELDS = ["lifecycle_id", "route_key", "venue", "symbol", "side", "proof_mode"]
STATUS_CORRELATION_FIELDS = {
    "candidate_ready": ["candidate_id"],
    "intent_published": ["candidate_id", "intent_id"],
    "executor_accepted": ["intent_id", "route_key"],
    "order_submitted": ["client_order_id"],
    "submit_timeout_unverified": ["client_order_id", "verification_source"],
    "broker_acknowledged": ["client_order_id", "broker_order_id", "venue_status", "verification_source"],
    "partial_fill": ["client_order_id", "broker_order_id", "filled_qty", "remaining_qty", "avg_fill_price", "verification_source"],
    "position_open": ["verification_source"],
    "close_requested": ["close_reason"],
    "close_acknowledged": ["verification_source"],
    "position_closed": ["verification_source"],
    "outcome_recorded": ["fees"],
}
VENUE_CORRELATION_FIELDS = {
    "capital": {
        "order_submitted": ["deal_reference"],
        "broker_acknowledged": ["deal_reference", "deal_id"],
        "position_open": ["deal_id"],
        "close_requested": ["deal_id"],
        "close_acknowledged": ["deal_id"],
        "position_closed": ["deal_id"],
    },
    "alpaca": {
        "order_submitted": ["client_order_id"],
        "broker_acknowledged": ["client_order_id", "broker_order_id"],
        "partial_fill": ["client_order_id", "broker_order_id"],
        "position_open": ["client_order_id", "broker_order_id"],
    },
    "binance": {
        "order_submitted": ["client_order_id"],
        "broker_acknowledged": ["client_order_id", "broker_order_id"],
        "partial_fill": ["client_order_id", "broker_order_id"],
        "position_open": ["client_order_id", "broker_order_id"],
        "submit_timeout_unverified": ["client_order_id"],
    },
    "kraken": {
        "order_submitted": ["client_order_id"],
        "broker_acknowledged": ["client_order_id", "broker_order_id"],
        "partial_fill": ["client_order_id", "broker_order_id"],
        "position_open": ["client_order_id", "broker_order_id"],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rooted(root: Optional[Path], path: Path) -> Path:
    return (Path(root or REPO_ROOT).resolve() / path).resolve()


def stable_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part or "") for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:18]
    return f"{prefix}-{digest}"


def lifecycle_id_for(*parts: Any) -> str:
    return stable_id("olife", *parts)


def candidate_id_for(symbol: Any, side: Any, generated_at: Any = "", source: Any = "") -> str:
    return stable_id("ocand", symbol, side, generated_at, source)


def route_key_for(venue: Any, market_type: Any, symbol: Any, side: Any) -> str:
    return ":".join(
        [
            str(venue or "").lower(),
            str(market_type or "").lower(),
            str(symbol or "").upper().strip(),
            str(side or "").upper().strip(),
        ]
    )


def transition_allowed(previous_status: Any, next_status: Any) -> bool:
    previous = str(previous_status or "").strip()
    next_value = str(next_status or "").strip()
    if not previous:
        return next_value in {"runtime_started", "data_ready", "candidate_ready", "position_open", "order_submitted", "order_blocked"}
    allowed = ALLOWED_STATUS_TRANSITIONS.get(previous)
    if allowed is not None:
        return next_value in allowed
    if previous in TERMINAL_STATUSES:
        return False
    return True


def normalize_broker_status(venue: Any, venue_status: Any) -> Dict[str, Any]:
    venue_key = str(venue or "").strip().lower()
    status_key = str(venue_status or "").strip().lower()
    lifecycle_status = BROKER_STATUS_MAP.get(venue_key, {}).get(status_key, status_key or "unknown")
    return {
        "venue": venue_key,
        "venue_status": status_key,
        "lifecycle_status": lifecycle_status,
        "active": lifecycle_status in ACTIVE_ORDER_STATUSES,
        "terminal": lifecycle_status in TERMINAL_STATUSES,
        "known": bool(lifecycle_status and lifecycle_status != "unknown"),
    }


def proof_tier_for(payload: Dict[str, Any]) -> str:
    tier = str(payload.get("proof_tier") or payload.get("proof_mode") or "").strip().lower()
    if tier in PROOF_TIERS:
        return tier
    if tier in {"mock", "mocked"}:
        return "mock_broker"
    if tier in {"sandbox", "paper", "testnet", "demo"}:
        return "sandbox_paper"
    return tier or "mock_broker"


def validate_proof_tier(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "valid": False,
            "proof_tier": "unknown",
            "missing_fields": list(SANDBOX_PAPER_FIELDS),
            "blockers": ["proof_tier_payload_invalid"],
        }

    tier = proof_tier_for(payload)
    blockers: List[str] = []
    missing: List[str] = []
    if tier not in PROOF_TIERS:
        blockers.append("proof_tier_unknown")

    if tier == "sandbox_paper":
        for field in SANDBOX_PAPER_FIELDS:
            if payload.get(field) in (None, "", []):
                missing.append(field)
        mutation_scope = str(payload.get("mutation_scope") or "").strip().lower()
        broker_environment = str(payload.get("broker_environment") or "").strip().lower()
        credential_scope = str(payload.get("credential_scope") or "").strip().lower()
        if any(token in mutation_scope for token in ("live", "production", "real_capital")):
            blockers.append("sandbox_paper_mutation_scope_not_safe")
        if any(token in broker_environment for token in ("production", "live")):
            blockers.append("sandbox_paper_environment_not_safe")
        if any(token in credential_scope for token in ("live", "production", "plaintext_secret")):
            blockers.append("sandbox_paper_credential_scope_not_safe")
        if missing:
            blockers.append("sandbox_paper_required_fields_missing")

    return {
        "valid": not blockers,
        "proof_tier": tier,
        "missing_fields": missing,
        "blockers": blockers,
    }


def required_correlation_fields(venue: Any, status: Any) -> List[str]:
    venue_key = str(venue or "").strip().lower()
    status_key = str(status or "").strip()
    fields = list(CORE_CORRELATION_FIELDS)
    fields.extend(STATUS_CORRELATION_FIELDS.get(status_key, []))
    fields.extend(VENUE_CORRELATION_FIELDS.get(venue_key, {}).get(status_key, []))
    return list(dict.fromkeys(fields))


def missing_correlation_fields(payload: Dict[str, Any]) -> List[str]:
    if not isinstance(payload, dict):
        return list(CORE_CORRELATION_FIELDS)
    status = str(payload.get("current_status") or payload.get("status") or payload.get("event_type") or "")
    venue = str(payload.get("venue") or "")
    required = required_correlation_fields(venue, status)
    missing: List[str] = []
    for field in required:
        if payload.get(field) in (None, "", []):
            missing.append(field)
    return missing


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _tail_jsonl(path: Path, limit: int = 500) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if isinstance(item, dict):
                    rows.append(item)
                    if len(rows) > limit:
                        rows = rows[-limit:]
    except Exception:
        return rows[-limit:]
    return rows[-limit:]


def _event_identity(event: Dict[str, Any]) -> str:
    payload = {
        key: value
        for key, value in event.items()
        if key not in {"event_id", "sequence"}
    }
    return stable_id("olev", json.dumps(payload, sort_keys=True, default=str))


def _compact_event(event: Dict[str, Any]) -> Dict[str, Any]:
    compact = dict(event)
    for key in ("broker_response", "positions_snapshot", "raw"):
        value = compact.get(key)
        if isinstance(value, list) and len(value) > 3:
            compact[key] = value[:3]
            compact[f"{key}_truncated_count"] = len(value) - 3
    return compact


def _summarize_lifecycle(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [row for row in events if isinstance(row, dict)]
    if not rows:
        return {}
    first = rows[0]
    last = rows[-1]
    seen = {str(row.get("status") or row.get("event_type") or "") for row in rows}
    deal_ids = [
        str(row.get("deal_id") or "")
        for row in rows
        if str(row.get("deal_id") or "")
    ]
    deal_refs = [
        str(row.get("deal_reference") or "")
        for row in rows
        if str(row.get("deal_reference") or "")
    ]
    client_order_ids = [
        str(row.get("client_order_id") or "")
        for row in rows
        if str(row.get("client_order_id") or "")
    ]
    broker_order_ids = [
        str(row.get("broker_order_id") or row.get("order_id") or "")
        for row in rows
        if str(row.get("broker_order_id") or row.get("order_id") or "")
    ]
    venue_statuses = [
        str(row.get("venue_status") or "")
        for row in rows
        if str(row.get("venue_status") or "")
    ]
    def last_value(*keys: str) -> Any:
        for row in reversed(rows):
            for key in keys:
                value = row.get(key)
                if value not in (None, ""):
                    return value
        return None

    current_status = str(last.get("status") or last.get("event_type") or "unknown")
    required_until = []
    if current_status in CONTINUITY_CHAIN:
        required_until = CONTINUITY_CHAIN[: CONTINUITY_CHAIN.index(current_status) + 1]
    elif seen & ACTIVE_ORDER_STATUSES:
        required_until = CONTINUITY_CHAIN[:6]
    missing = [status for status in required_until if status not in seen]
    return {
        "lifecycle_id": first.get("lifecycle_id"),
        "current_status": current_status,
        "started_at": first.get("generated_at"),
        "updated_at": last.get("generated_at"),
        "symbol": last.get("symbol") or first.get("symbol"),
        "side": last.get("side") or first.get("side"),
        "venue": last.get("venue") or first.get("venue"),
        "market_type": last.get("market_type") or first.get("market_type"),
        "route_key": last.get("route_key") or first.get("route_key"),
        "candidate_id": last.get("candidate_id") or first.get("candidate_id"),
        "intent_id": last.get("intent_id") or first.get("intent_id"),
        "client_order_id": client_order_ids[-1] if client_order_ids else "",
        "broker_order_id": broker_order_ids[-1] if broker_order_ids else "",
        "deal_id": deal_ids[-1] if deal_ids else "",
        "deal_reference": deal_refs[-1] if deal_refs else "",
        "venue_status": venue_statuses[-1] if venue_statuses else "",
        "filled_qty": last_value("filled_qty"),
        "remaining_qty": last_value("remaining_qty"),
        "avg_fill_price": last_value("avg_fill_price"),
        "fees": last_value("fees"),
        "verification_source": last_value("verification_source") or "",
        "proof_mode": last_value("proof_mode") or "",
        "proof_tier": proof_tier_for(last),
        "broker_environment": last_value("broker_environment") or "",
        "account_mode": last_value("account_mode") or "",
        "broker_call_id": last_value("broker_call_id") or "",
        "idempotency_key": last_value("idempotency_key") or "",
        "round_trip_ms": last_value("round_trip_ms"),
        "request_timestamp": last_value("request_timestamp") or "",
        "response_timestamp": last_value("response_timestamp") or "",
        "credential_scope": last_value("credential_scope") or "",
        "mutation_scope": last_value("mutation_scope") or "",
        "close_reason": last_value("close_reason") or "",
        "event_count": len(rows),
        "position_open": "position_open" in seen and "position_closed" not in seen,
        "position_closed": "position_closed" in seen,
        "outcome_recorded": "outcome_recorded" in seen,
        "continuity_complete": all(status in seen for status in CONTINUITY_CHAIN),
        "missing_links": missing,
        "last_reason": last.get("reason") or "",
        "last_error": last.get("error") or "",
        "last_pnl": last.get("net_pnl", last.get("pnl_gbp")),
        "last_event": _compact_event(last),
    }


def build_state_from_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for event in events:
        lifecycle_id = str(event.get("lifecycle_id") or "")
        if lifecycle_id:
            grouped.setdefault(lifecycle_id, []).append(event)
    lifecycles = [
        _summarize_lifecycle(rows)
        for rows in grouped.values()
    ]
    lifecycles = [row for row in lifecycles if row]
    lifecycles.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    active = [
        row
        for row in lifecycles
        if str(row.get("current_status") or "") in ACTIVE_ORDER_STATUSES
        or bool(row.get("position_open"))
    ]
    continuity_blockers: List[str] = []
    for row in active[:20]:
        missing = row.get("missing_links") if isinstance(row.get("missing_links"), list) else []
        if missing:
            continuity_blockers.append("lifecycle_continuity_missing")
            break
    latest_event = events[-1] if events else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": "order_lifecycle_ready",
        "event_count": len(events),
        "lifecycle_count": len(lifecycles),
        "active_lifecycle_count": len(active),
        "completed_lifecycle_count": sum(1 for row in lifecycles if row.get("outcome_recorded") or row.get("position_closed")),
        "continuity_blockers": sorted(set(continuity_blockers)),
        "latest_event": _compact_event(latest_event) if latest_event else {},
        "lifecycles": lifecycles[:40],
        "active_lifecycles": active[:20],
        "events": [_compact_event(event) for event in events[-120:]],
        "paths": {
            "state": STATE_PATH.as_posix(),
            "jsonl": LOG_PATH.as_posix(),
            "public": PUBLIC_PATH.as_posix(),
        },
    }


def _active_lifecycle_rows(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = state.get("active_lifecycles") if isinstance(state, dict) else []
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _has_missing_links(row: Dict[str, Any]) -> bool:
    missing = row.get("missing_links")
    return isinstance(missing, list) and bool(missing)


def _merge_preserved_active_lifecycles(
    state: Dict[str, Any],
    previous_state: Dict[str, Any],
    latest_event: Dict[str, Any],
) -> Dict[str, Any]:
    """Keep active broker/open lifecycles visible when noisy candidates roll the JSONL tail.

    The ledger stays append-only, but the UI/runtime snapshot is rebuilt from a bounded
    tail for speed. Active position lifecycles are safety-critical, so preserve their
    latest summary until a newer event for the same lifecycle appears in the tail.
    """

    if not isinstance(previous_state, dict) or not previous_state:
        return state

    latest_lifecycle_id = str(latest_event.get("lifecycle_id") or "")
    latest_status = str(latest_event.get("status") or latest_event.get("event_type") or "")
    latest_terminal = latest_lifecycle_id and latest_status in TERMINAL_STATUSES

    lifecycles = state.get("lifecycles") if isinstance(state.get("lifecycles"), list) else []
    active = state.get("active_lifecycles") if isinstance(state.get("active_lifecycles"), list) else []
    current_ids = {
        str(row.get("lifecycle_id") or "")
        for row in lifecycles
        if isinstance(row, dict) and str(row.get("lifecycle_id") or "")
    }
    current_ids.update(
        str(row.get("lifecycle_id") or "")
        for row in active
        if isinstance(row, dict) and str(row.get("lifecycle_id") or "")
    )

    preserved: List[Dict[str, Any]] = []
    preserved_ids: set[str] = set()
    for row in _active_lifecycle_rows(previous_state):
        lifecycle_id = str(row.get("lifecycle_id") or "")
        if not lifecycle_id or lifecycle_id in current_ids:
            continue
        if lifecycle_id in preserved_ids:
            continue
        if latest_terminal and lifecycle_id == latest_lifecycle_id:
            continue
        preserved_row = dict(row)
        preserved_row["preserved_from_previous_snapshot"] = True
        preserved.append(preserved_row)
        preserved_ids.add(lifecycle_id)

    if not preserved:
        return state

    merged_lifecycles = list(lifecycles) + preserved
    merged_lifecycles.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)
    merged_active = list(active) + preserved
    merged_active.sort(key=lambda row: str(row.get("updated_at") or ""), reverse=True)

    blockers = set(state.get("continuity_blockers") if isinstance(state.get("continuity_blockers"), list) else [])
    if any(_has_missing_links(row) for row in merged_active):
        blockers.add("lifecycle_continuity_missing")

    updated = dict(state)
    updated["lifecycles"] = merged_lifecycles[:40]
    updated["active_lifecycles"] = merged_active[:20]
    updated["lifecycle_count"] = len(merged_lifecycles)
    updated["active_lifecycle_count"] = len(merged_active)
    updated["completed_lifecycle_count"] = sum(
        1 for row in merged_lifecycles if row.get("outcome_recorded") or row.get("position_closed")
    )
    updated["continuity_blockers"] = sorted(blockers)
    return updated


def load_state(root: Optional[Path] = None) -> Dict[str, Any]:
    data = _read_json(rooted(root, STATE_PATH), {})
    if isinstance(data, dict) and data:
        return data
    events = _tail_jsonl(rooted(root, LOG_PATH), 500)
    return build_state_from_events(events) if events else {}


def _write_state(state: Dict[str, Any], root: Optional[Path]) -> None:
    for rel in (STATE_PATH, PUBLIC_PATH):
        path = rooted(root, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        tmp_path.write_text(json.dumps(state, indent=2, sort_keys=True, default=str), encoding="utf-8")
        os.replace(tmp_path, path)


def append_event(
    *,
    event_type: str,
    status: str,
    lifecycle_id: str,
    root: Optional[Path] = None,
    **fields: Any,
) -> Dict[str, Any]:
    generated_at = str(fields.pop("generated_at", "") or utc_now())
    event: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "event_type": str(event_type or status or "lifecycle_event"),
        "status": str(status or event_type or "unknown"),
        "lifecycle_id": lifecycle_id,
    }
    for key, value in fields.items():
        if value is not None and value != "":
            event[key] = value
    event["event_id"] = _event_identity(event)

    log_path = rooted(root, LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")

    previous_state = _read_json(rooted(root, STATE_PATH), {})
    events = _tail_jsonl(log_path, 500)
    state = build_state_from_events(events[-500:])
    state = _merge_preserved_active_lifecycles(
        state,
        previous_state if isinstance(previous_state, dict) else {},
        event,
    )
    _write_state(state, root)
    return event


def is_active_route(route_key: str, root: Optional[Path] = None) -> bool:
    if not route_key:
        return False
    state = load_state(root)
    lifecycles = state.get("active_lifecycles") if isinstance(state.get("active_lifecycles"), list) else []
    for row in lifecycles:
        if not isinstance(row, dict):
            continue
        if str(row.get("route_key") or "") == route_key and str(row.get("current_status") or "") in ACTIVE_ORDER_STATUSES:
            return True
    return False


def lifecycle_for_deal(deal_id: str, root: Optional[Path] = None) -> str:
    deal = str(deal_id or "").strip()
    if not deal:
        return ""
    state = load_state(root)
    lifecycles = state.get("lifecycles") if isinstance(state.get("lifecycles"), list) else []
    for row in lifecycles:
        if isinstance(row, dict) and str(row.get("deal_id") or "") == deal:
            return str(row.get("lifecycle_id") or "")
    return lifecycle_id_for("capital", "deal", deal)


def latest_for_ui(root: Optional[Path] = None) -> Dict[str, Any]:
    state = load_state(root)
    if state:
        return state
    return build_state_from_events([])
