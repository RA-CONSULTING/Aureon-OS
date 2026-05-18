"""Live dry stress audit for the Capital ecosystem.

This audit reads current runtime and evidence artifacts only. It does not
submit, close, cancel, place, or mutate any broker order.
"""

from __future__ import annotations

import argparse
import json
import math
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "aureon-capital-ecosystem-live-dry-stress-audit-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]

CAPITAL_ECOSYSTEM_PATH = Path("frontend/public/aureon_capital_ecosystem_intelligence_company.json")
ORDER_LIFECYCLE_PATH = Path("frontend/public/aureon_unified_order_lifecycle.json")
ORDER_LIFECYCLE_STRESS_PATH = Path("frontend/public/aureon_order_lifecycle_stress_audit.json")
EXCHANGE_MATRIX_PATH = Path("frontend/public/aureon_exchange_data_capability_matrix.json")
STREAM_CACHE_PATH = Path("ws_cache/ws_prices.json")

DEFAULT_STATE_PATH = Path("state/aureon_capital_ecosystem_live_dry_stress_audit_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_capital_ecosystem_live_dry_stress_audit.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_capital_ecosystem_live_dry_stress_audit.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_capital_ecosystem_live_dry_stress_audit.json")

DEFAULT_TERMINAL_ENDPOINTS = (
    "http://127.0.0.1:8791/api/terminal-state",
    "http://127.0.0.1:8790/api/terminal-state",
)

ACTIVE_LIFECYCLE_STATUSES = {
    "order_submitted",
    "submit_timeout_unverified",
    "broker_acknowledged",
    "partial_fill",
    "position_open",
    "close_requested",
    "close_acknowledged",
    "position_closed",
    "outcome_recorded",
}
MANUAL_BOUNDARIES = [
    "live dry audit only",
    "no live order submission",
    "no live close request",
    "no cancel request",
    "no external hedge order",
    "no credential read or reveal",
    "existing runtime gates remain authoritative",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_root() -> Path:
    cwd = Path.cwd().resolve()
    return cwd if (cwd / "aureon").exists() and (cwd / "frontend").exists() else REPO_ROOT


def _rooted(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _write_text(path: Path, content: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": len(content.encode("utf-8"))}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except Exception:
        return default


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _age_seconds(value: Any, now: datetime) -> Optional[float]:
    parsed = _parse_timestamp(value)
    if not parsed:
        return None
    return round(max(0.0, (now - parsed).total_seconds()), 3)


def _fetch_terminal_state(endpoints: Sequence[str], timeout_sec: float = 3.0) -> Tuple[Dict[str, Any], str, str]:
    last_error = ""
    for endpoint in endpoints:
        try:
            with urllib.request.urlopen(endpoint, timeout=timeout_sec) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict):
                return payload, endpoint, ""
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = str(exc)
    return {}, "", last_error


def _build_runtime_proof(
    *,
    terminal_state: Optional[Dict[str, Any]],
    endpoint: str,
    error: str,
    now: datetime,
) -> Dict[str, Any]:
    payload = terminal_state if isinstance(terminal_state, dict) else {}
    generated_at = (
        payload.get("generated_at")
        or payload.get("dashboard_generated_at")
        or payload.get("latest_execution_generated_at")
        or payload.get("last_tick_completed_at")
    )
    watchdog = payload.get("runtime_watchdog") if isinstance(payload.get("runtime_watchdog"), dict) else {}
    action_plan = payload.get("exchange_action_plan") if isinstance(payload.get("exchange_action_plan"), dict) else {}
    gold_proof_present = isinstance(payload.get("gold_runtime_trade_proof"), dict) or isinstance(
        action_plan.get("gold_runtime_trade_proof"),
        dict,
    )
    stale = bool(payload.get("stale") or watchdog.get("tick_stale"))
    stale_reason = str(payload.get("stale_reason") or watchdog.get("tick_stale_reason") or "")
    blockers: List[str] = []
    if not payload:
        blockers.append("runtime_unavailable")
    elif stale or stale_reason:
        blockers.append("runtime_stale")
    return {
        "present": bool(payload),
        "endpoint": endpoint,
        "error": error,
        "generated_at": generated_at or "",
        "age_sec": _age_seconds(generated_at, now),
        "runtime_fresh": bool(payload and not blockers),
        "stale": stale,
        "stale_reason": stale_reason,
        "exchange_action_plan_present": bool(action_plan),
        "gold_runtime_trade_proof_present": gold_proof_present,
        "blockers": blockers,
    }


def _build_capital_watchlist_proof(ecosystem: Dict[str, Any]) -> Dict[str, Any]:
    summary = ecosystem.get("summary") if isinstance(ecosystem.get("summary"), dict) else {}
    lifecycle = ecosystem.get("lifecycle") if isinstance(ecosystem.get("lifecycle"), dict) else {}
    blockers = [str(item) for item in ecosystem.get("blockers") or [] if str(item)]
    active_count = int(_as_float(summary.get("active_watchlist_count"), 0))
    active_limit = int(_as_float(summary.get("active_watchlist_limit"), 40))
    bench_count = int(_as_float(summary.get("bench_watchlist_count"), 0))
    bench_limit = int(_as_float(summary.get("bench_watchlist_limit"), 100))
    if not ecosystem:
        blockers.append("capital_ecosystem_intelligence_missing")
    if active_count > active_limit:
        blockers.append("capital_watchlist_over_limit")
    if bench_count > bench_limit:
        blockers.append("capital_bench_watchlist_over_limit")
    if active_count <= 0:
        blockers.append("capital_watchlist_empty")
    return {
        "present": bool(ecosystem),
        "status": ecosystem.get("status") or "",
        "candidate_count": int(_as_float(summary.get("candidate_count"), 0)),
        "trade_ready_candidate_count": int(_as_float(summary.get("trade_ready_candidate_count"), 0)),
        "active_watchlist_count": active_count,
        "active_watchlist_limit": active_limit,
        "bench_watchlist_count": bench_count,
        "bench_watchlist_limit": bench_limit,
        "gold_preserved": bool(summary.get("gold_preserved")),
        "duplicate_route_blocked_count": int(_as_float(lifecycle.get("duplicate_route_blocked_count"), 0)),
        "active_route_keys": lifecycle.get("active_route_keys") if isinstance(lifecycle.get("active_route_keys"), list) else [],
        "blockers": list(dict.fromkeys(blockers)),
    }


def _normalize_route_value(row: Dict[str, Any], field: str) -> str:
    value = str(row.get(field) or "")
    if value:
        return value
    route = str(row.get("route_key") or "")
    parts = route.split(":")
    if field == "venue" and len(parts) >= 1:
        return parts[0]
    if field == "symbol" and len(parts) >= 3:
        return parts[2]
    if field == "side" and len(parts) >= 4:
        return parts[3]
    return ""


def _active_lifecycle_rows(lifecycle_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = lifecycle_state.get("active_lifecycles") if isinstance(lifecycle_state.get("active_lifecycles"), list) else []
    return [row for row in rows if isinstance(row, dict)]


def _all_lifecycle_rows(lifecycle_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for source_rows in (
        lifecycle_state.get("lifecycles") if isinstance(lifecycle_state.get("lifecycles"), list) else [],
        lifecycle_state.get("active_lifecycles") if isinstance(lifecycle_state.get("active_lifecycles"), list) else [],
    ):
        for row in source_rows:
            if not isinstance(row, dict):
                continue
            lifecycle_id = str(row.get("lifecycle_id") or "")
            dedupe_key = lifecycle_id or f"row:{len(rows)}"
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            rows.append(row)
    return rows


def _event_rows(lifecycle_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = lifecycle_state.get("events") if isinstance(lifecycle_state.get("events"), list) else []
    return [row for row in rows if isinstance(row, dict)]


def _last_event(row: Dict[str, Any]) -> Dict[str, Any]:
    event = row.get("last_event") if isinstance(row.get("last_event"), dict) else {}
    return event


def _verification_source(row: Dict[str, Any]) -> str:
    event = _last_event(row)
    return str(
        row.get("verification_source")
        or row.get("source")
        or event.get("verification_source")
        or event.get("source")
        or ""
    )


def _is_recovered_capital_position(row: Dict[str, Any]) -> bool:
    event = _last_event(row)
    status = str(row.get("current_status") or row.get("status") or event.get("status") or "")
    venue = _normalize_route_value(row, "venue").lower()
    event_type = str(event.get("event_type") or row.get("event_type") or "")
    reason = str(event.get("reason") or row.get("reason") or "")
    return (
        venue == "capital"
        and status == "position_open"
        and (
            event_type == "position_recovered"
            or reason == "broker_position_reconciled_on_startup"
        )
    )


def _recovered_lifecycle_ids(lifecycle_state: Dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for row in _event_rows(lifecycle_state):
        lifecycle_id = str(row.get("lifecycle_id") or "")
        event_type = str(row.get("event_type") or "")
        reason = str(row.get("reason") or "")
        if lifecycle_id and (event_type == "position_recovered" or reason == "broker_position_reconciled_on_startup"):
            ids.add(lifecycle_id)
    for row in _all_lifecycle_rows(lifecycle_state):
        lifecycle_id = str(row.get("lifecycle_id") or "")
        if lifecycle_id and _is_recovered_capital_position(row):
            ids.add(lifecycle_id)
    return ids


def _is_recovered_capital_lifecycle(row: Dict[str, Any], recovered_ids: set[str]) -> bool:
    lifecycle_id = str(row.get("lifecycle_id") or "")
    if lifecycle_id and lifecycle_id in recovered_ids:
        return True
    return _is_recovered_capital_position(row)


def _recovered_identity(row: Dict[str, Any]) -> Dict[str, str]:
    event = _last_event(row)
    return {
        "lifecycle_id": str(row.get("lifecycle_id") or event.get("lifecycle_id") or ""),
        "route_key": str(row.get("route_key") or event.get("route_key") or ""),
        "venue": _normalize_route_value({**event, **row}, "venue"),
        "symbol": _normalize_route_value({**event, **row}, "symbol"),
        "side": _normalize_route_value({**event, **row}, "side"),
        "deal_id": str(row.get("deal_id") or event.get("deal_id") or ""),
        "source": _verification_source(row),
    }


def _missing_recovered_broker_fields(row: Dict[str, Any]) -> List[str]:
    identity = _recovered_identity(row)
    missing = [field for field in ("deal_id", "route_key", "symbol", "side", "source") if not identity.get(field)]
    if str(row.get("current_status") or row.get("status") or "") != "position_open":
        missing.append("position_presence_proof")
    return missing


def _close_first_covers(row: Dict[str, Any], close_rows: List[Dict[str, Any]]) -> bool:
    identity = _recovered_identity(row)
    lifecycle_id = identity.get("lifecycle_id")
    deal_id = identity.get("deal_id")
    route_key = identity.get("route_key")
    for close_row in close_rows:
        if lifecycle_id and str(close_row.get("lifecycle_id") or "") == lifecycle_id:
            return True
        if deal_id and str(close_row.get("deal_id") or "") == deal_id:
            return True
        if route_key and str(close_row.get("route_key") or "") == route_key:
            return True
    return False


def _build_lifecycle_route_proof(lifecycle_state: Dict[str, Any], ecosystem: Dict[str, Any]) -> Dict[str, Any]:
    rows = _active_lifecycle_rows(lifecycle_state)
    recovered_ids = _recovered_lifecycle_ids(lifecycle_state)
    ecosystem_lifecycle = ecosystem.get("lifecycle") if isinstance(ecosystem.get("lifecycle"), dict) else {}
    continuity_blockers = [
        str(item)
        for item in (lifecycle_state.get("continuity_blockers") or ecosystem_lifecycle.get("continuity_blockers") or [])
        if str(item)
    ]
    missing_rows = []
    recovered_upstream_rows = []
    active_route_keys = sorted({str(row.get("route_key") or "") for row in rows if row.get("route_key")})
    for row in rows:
        status = str(row.get("current_status") or row.get("status") or "")
        missing_links = [str(item) for item in row.get("missing_links") or [] if str(item)]
        if status in ACTIVE_LIFECYCLE_STATUSES and missing_links:
            target = recovered_upstream_rows if _is_recovered_capital_lifecycle(row, recovered_ids) else missing_rows
            target.append(
                {
                    "lifecycle_id": row.get("lifecycle_id") or "",
                    "route_key": row.get("route_key") or "",
                    "current_status": status,
                    "missing_links": missing_links,
                }
            )
    blockers = []
    for blocker in continuity_blockers:
        if blocker == "lifecycle_continuity_missing" and recovered_upstream_rows and not missing_rows:
            continue
        blockers.append(blocker)
    blockers = list(dict.fromkeys(blockers))
    if missing_rows and "lifecycle_continuity_missing" not in blockers:
        blockers.append("lifecycle_continuity_missing")
    return {
        "present": bool(lifecycle_state),
        "status": lifecycle_state.get("status") or "",
        "active_lifecycle_count": int(_as_float(lifecycle_state.get("active_lifecycle_count"), len(rows))),
        "completed_lifecycle_count": int(_as_float(lifecycle_state.get("completed_lifecycle_count"), 0)),
        "active_lifecycle_route_count": len(active_route_keys),
        "active_route_keys": active_route_keys,
        "duplicate_routes_blocked": int(_as_float(ecosystem_lifecycle.get("duplicate_route_blocked_count"), 0)) > 0,
        "duplicate_route_blocked_count": int(_as_float(ecosystem_lifecycle.get("duplicate_route_blocked_count"), 0)),
        "missing_link_rows": missing_rows[:20],
        "recovered_upstream_context_rows": recovered_upstream_rows[:20],
        "blockers": blockers,
    }


def _events_for_lifecycle(lifecycle_state: Dict[str, Any], lifecycle_id: str) -> List[Dict[str, Any]]:
    return [row for row in _event_rows(lifecycle_state) if str(row.get("lifecycle_id") or "") == lifecycle_id]


def _status_seen(row: Dict[str, Any], events: List[Dict[str, Any]], *statuses: str) -> bool:
    wanted = set(statuses)
    current = str(row.get("current_status") or row.get("status") or "")
    if current in wanted:
        return True
    return any(str(event.get("status") or event.get("event_type") or "") in wanted for event in events)


def _row_has_pnl(row: Dict[str, Any], events: List[Dict[str, Any]]) -> bool:
    for candidate in [row, _last_event(row), *reversed(events)]:
        if candidate.get("net_pnl") not in (None, "") or candidate.get("pnl_gbp") not in (None, "") or candidate.get("last_pnl") not in (None, ""):
            return True
    return False


def _row_has_stale_close_proof(row: Dict[str, Any], events: List[Dict[str, Any]]) -> bool:
    text_parts = [
        str(row.get("current_status") or ""),
        str(row.get("last_reason") or ""),
        str(row.get("last_error") or ""),
        str(row.get("verification_source") or ""),
        str(_last_event(row).get("reason") or ""),
        str(_last_event(row).get("error") or ""),
        str(_last_event(row).get("verification_source") or ""),
    ]
    for event in events[-4:]:
        text_parts.extend(
            [
                str(event.get("reason") or ""),
                str(event.get("error") or ""),
                str(event.get("verification_source") or ""),
                str(event.get("venue_status") or ""),
            ]
        )
    return "stale" in " ".join(text_parts).lower()


def _build_recovered_exit_readiness_proof(lifecycle_state: Dict[str, Any]) -> Dict[str, Any]:
    recovered_ids = _recovered_lifecycle_ids(lifecycle_state)
    rows = [
        row
        for row in _all_lifecycle_rows(lifecycle_state)
        if _is_recovered_capital_lifecycle(row, recovered_ids)
    ]
    exit_rows = []
    missing_upstream_rows = []
    close_requested_ids: set[str] = set()
    close_ack_ids: set[str] = set()
    absence_verified_ids: set[str] = set()
    outcome_ids: set[str] = set()
    stale_rows = []
    waiting_absence_rows = []
    missing_pnl_rows = []
    open_ready_rows = []
    absence_verified_rows = []
    outcome_rows = []

    for row in rows:
        lifecycle_id = str(row.get("lifecycle_id") or "")
        events = _events_for_lifecycle(lifecycle_state, lifecycle_id)
        identity = _recovered_identity(row)
        status = str(row.get("current_status") or row.get("status") or "")
        missing_links = [str(item) for item in row.get("missing_links") or [] if str(item)]
        if missing_links:
            missing_upstream_rows.append({**identity, "current_status": status, "missing_links": missing_links})
        if _status_seen(row, events, "close_requested"):
            close_requested_ids.add(lifecycle_id)
        if _status_seen(row, events, "close_acknowledged"):
            close_ack_ids.add(lifecycle_id)
        if _status_seen(row, events, "position_closed", "outcome_recorded"):
            absence_verified_ids.add(lifecycle_id)
        if _status_seen(row, events, "outcome_recorded"):
            outcome_ids.add(lifecycle_id)

        row_summary = {
            **identity,
            "current_status": status,
            "close_requested": _status_seen(row, events, "close_requested"),
            "close_acknowledged": _status_seen(row, events, "close_acknowledged"),
            "position_absence_verified": _status_seen(row, events, "position_closed", "outcome_recorded"),
            "outcome_recorded": _status_seen(row, events, "outcome_recorded"),
            "pnl_present": _row_has_pnl(row, events),
            "verification_source": _verification_source(row),
        }
        exit_rows.append(row_summary)

        if _row_has_stale_close_proof(row, events):
            stale_rows.append(row_summary)
        elif status == "close_acknowledged" and not row_summary["position_absence_verified"]:
            waiting_absence_rows.append(row_summary)
        elif status == "position_closed" and not row_summary["outcome_recorded"] and not row_summary["pnl_present"]:
            missing_pnl_rows.append(row_summary)
        elif status == "position_open":
            open_ready_rows.append(row_summary)
        elif row_summary["position_absence_verified"] and not row_summary["outcome_recorded"]:
            absence_verified_rows.append(row_summary)
        elif row_summary["outcome_recorded"]:
            outcome_rows.append(row_summary)

    blockers: List[str] = []
    if stale_rows:
        blockers.append("recovered_exit_stale_broker_proof")
    if waiting_absence_rows:
        blockers.append("recovered_close_ack_waiting_absence")
    if missing_pnl_rows:
        blockers.append("recovered_exit_missing_pnl")
    if open_ready_rows:
        blockers.append("recovered_exit_ready_attention")
    if missing_upstream_rows:
        blockers.append("recovered_upstream_context_missing")

    if not rows:
        status = "not_applicable"
    elif stale_rows:
        status = "recovered_exit_stale_broker_proof"
    elif waiting_absence_rows:
        status = "recovered_close_ack_waiting_absence"
    elif missing_pnl_rows:
        status = "recovered_exit_missing_pnl"
    elif open_ready_rows:
        status = "recovered_exit_ready_attention"
    elif absence_verified_rows:
        status = "recovered_close_absence_verified"
    elif outcome_rows and len(outcome_rows) == len(rows):
        status = "recovered_outcome_recorded"
    else:
        status = "recovered_exit_ready_attention"

    return {
        "recovered_close_chain_status": status,
        "recovered_exit_row_count": len(rows),
        "recovered_close_request_count": len(close_requested_ids),
        "recovered_close_acknowledged_count": len(close_ack_ids),
        "recovered_position_absence_verified_count": len(absence_verified_ids),
        "recovered_outcome_recorded_count": len(outcome_ids),
        "ready_rows": open_ready_rows[:20],
        "waiting_absence_rows": waiting_absence_rows[:20],
        "absence_verified_rows": absence_verified_rows[:20],
        "outcome_rows": outcome_rows[:20],
        "missing_pnl_rows": missing_pnl_rows[:20],
        "stale_proof_rows": stale_rows[:20],
        "missing_upstream_context_rows": missing_upstream_rows[:20],
        "exit_rows": exit_rows[:20],
        "recovered_exit_blockers": blockers,
        "blockers": blockers,
    }


def _build_recovered_position_proof(lifecycle_state: Dict[str, Any], ecosystem: Dict[str, Any]) -> Dict[str, Any]:
    rows = [row for row in _active_lifecycle_rows(lifecycle_state) if _is_recovered_capital_position(row)]
    close_rows = [
        row
        for row in (ecosystem.get("close_first_opportunities") if isinstance(ecosystem.get("close_first_opportunities"), list) else [])
        if isinstance(row, dict)
    ]
    ecosystem_lifecycle = ecosystem.get("lifecycle") if isinstance(ecosystem.get("lifecycle"), dict) else {}
    duplicate_count = int(_as_float(ecosystem_lifecycle.get("duplicate_route_blocked_count"), 0))
    missing_broker_rows = []
    close_missing_rows = []
    missing_upstream_context_rows = []
    recovered_routes = []
    for row in rows:
        identity = _recovered_identity(row)
        recovered_routes.append(identity)
        missing_fields = _missing_recovered_broker_fields(row)
        if missing_fields:
            missing_broker_rows.append({**identity, "missing_fields": missing_fields})
        if not _close_first_covers(row, close_rows):
            close_missing_rows.append(identity)
        missing_links = [str(item) for item in row.get("missing_links") or [] if str(item)]
        if missing_links:
            missing_upstream_context_rows.append({**identity, "missing_links": missing_links})

    duplicate_route_blocking_active = not rows or duplicate_count > 0
    blockers: List[str] = []
    if missing_broker_rows:
        blockers.append("recovered_position_missing_broker_proof")
    if close_missing_rows:
        blockers.append("recovered_position_close_first_missing")
    if rows and not duplicate_route_blocking_active:
        blockers.append("recovered_position_duplicate_route_block_missing")
    recovered_positions_certified = bool(rows) and not missing_broker_rows and not close_missing_rows and duplicate_route_blocking_active
    if recovered_positions_certified and missing_upstream_context_rows:
        blockers.append("recovered_upstream_context_missing")

    if not rows:
        status = "not_applicable"
    elif missing_broker_rows:
        status = "recovered_position_missing_broker_proof"
    elif close_missing_rows:
        status = "recovered_position_close_first_missing"
    elif recovered_positions_certified and missing_upstream_context_rows:
        status = "recovered_position_certified_attention"
    elif recovered_positions_certified:
        status = "recovered_position_certified"
    else:
        status = "recovered_position_attention"

    return {
        "recovered_position_count": len(rows),
        "recovered_positions_certified": bool(not rows or recovered_positions_certified),
        "recovered_routes": recovered_routes[:20],
        "missing_broker_proof_rows": missing_broker_rows[:20],
        "missing_upstream_context_rows": missing_upstream_context_rows[:20],
        "close_first_missing_rows": close_missing_rows[:20],
        "recovery_certification_status": status,
        "requires_close_first": bool(rows),
        "close_first_covered": not close_missing_rows,
        "duplicate_route_blocking_active": duplicate_route_blocking_active,
        "duplicate_route_blocked_count": duplicate_count,
        "blockers": blockers,
    }


def _missing_broker_fields(row: Dict[str, Any]) -> List[str]:
    status = str(row.get("current_status") or row.get("status") or "")
    venue = _normalize_route_value(row, "venue").lower()
    fields = ["lifecycle_id", "route_key", "symbol", "side"]
    if status in ACTIVE_LIFECYCLE_STATUSES:
        fields.append("venue")
    if venue == "capital" and status in {"broker_acknowledged", "position_open", "close_requested", "close_acknowledged", "position_closed", "outcome_recorded"}:
        fields.append("deal_id")
    last_event = row.get("last_event") if isinstance(row.get("last_event"), dict) else {}
    missing: List[str] = []
    for field in fields:
        value = row.get(field) or last_event.get(field)
        if field in {"venue", "symbol", "side"}:
            value = value or _normalize_route_value(row, field)
        if value in (None, "", []):
            missing.append(field)
    verification_source = row.get("verification_source") or row.get("source") or last_event.get("verification_source") or last_event.get("source")
    if status in ACTIVE_LIFECYCLE_STATUSES and not verification_source:
        missing.append("verification_source")
    return missing


def _build_broker_correlation_proof(lifecycle_state: Dict[str, Any]) -> Dict[str, Any]:
    rows = _active_lifecycle_rows(lifecycle_state)
    checked = [row for row in rows if str(row.get("current_status") or row.get("status") or "") in ACTIVE_LIFECYCLE_STATUSES]
    missing_rows = []
    recovered_missing_rows = []
    normal_missing_rows = []
    for row in checked:
        missing = _missing_broker_fields(row)
        if missing:
            entry = {
                "lifecycle_id": row.get("lifecycle_id") or "",
                "route_key": row.get("route_key") or "",
                "current_status": row.get("current_status") or row.get("status") or "",
                "missing_fields": missing,
            }
            missing_rows.append(entry)
            if _is_recovered_capital_position(row):
                recovered_missing_rows.append(entry)
            else:
                normal_missing_rows.append(entry)
    blockers = ["broker_correlation_missing"] if normal_missing_rows else []
    return {
        "checked_lifecycle_count": len(checked),
        "broker_correlation_complete": not missing_rows,
        "missing_rows": missing_rows[:20],
        "recovered_missing_rows": recovered_missing_rows[:20],
        "required_field_families": [
            "lifecycle_id",
            "route_key",
            "broker/deal id when applicable",
            "venue status or current status",
            "verification source",
        ],
        "blockers": blockers,
    }


def _build_close_first_proof(lifecycle_state: Dict[str, Any], ecosystem: Dict[str, Any]) -> Dict[str, Any]:
    rows = _active_lifecycle_rows(lifecycle_state)
    capital_open = [
        row
        for row in rows
        if _normalize_route_value(row, "venue").lower() == "capital"
        and str(row.get("current_status") or row.get("status") or "") == "position_open"
    ]
    close_first = ecosystem.get("close_first_opportunities") if isinstance(ecosystem.get("close_first_opportunities"), list) else []
    blockers: List[str] = []
    if capital_open and not close_first:
        blockers.append("close_first_not_prioritized")
    if any(isinstance(row, dict) and row.get("close_allowed") for row in close_first):
        blockers.append("close_first_mutation_leak")
    return {
        "capital_active_position_count": len(capital_open),
        "close_first_opportunity_count": len(close_first),
        "close_first_prioritized": not capital_open or bool(close_first),
        "close_mutation_allowed": any(isinstance(row, dict) and bool(row.get("close_allowed")) for row in close_first),
        "opportunities": [row for row in close_first if isinstance(row, dict)][:12],
        "blockers": blockers,
    }


def _build_shadow_hedge_proof(ecosystem: Dict[str, Any]) -> Dict[str, Any]:
    hedges = ecosystem.get("shadow_hedges") if isinstance(ecosystem.get("shadow_hedges"), list) else []
    rows = [row for row in hedges if isinstance(row, dict)]
    leaks = [
        row
        for row in rows
        if row.get("authority") != "shadow_only" or bool(row.get("mutation_allowed")) or bool(row.get("order_intent_allowed"))
    ]
    blockers = ["shadow_hedge_mutation_leak"] if leaks else []
    return {
        "shadow_hedge_count": len(rows),
        "shadow_hedges_only": not leaks,
        "leak_count": len(leaks),
        "hedges": rows[:12],
        "blockers": blockers,
    }


def _status_from_blockers(blockers: List[str]) -> str:
    priority = [
        "runtime_unavailable",
        "runtime_stale",
        "recovered_position_missing_broker_proof",
        "recovered_position_close_first_missing",
        "recovered_exit_stale_broker_proof",
        "recovered_close_ack_waiting_absence",
        "recovered_exit_missing_pnl",
        "lifecycle_continuity_missing",
        "capital_watchlist_over_limit",
        "broker_correlation_missing",
        "shadow_hedge_mutation_leak",
        "close_first_not_prioritized",
    ]
    for status in priority:
        if status in blockers:
            return status
    if "recovered_upstream_context_missing" in blockers:
        return "recovered_position_certified_attention"
    if "recovered_exit_ready_attention" in blockers:
        return "recovered_exit_ready_attention"
    return "live_dry_attention" if blockers else "live_dry_certified"


def build_capital_ecosystem_live_dry_stress_audit(
    *,
    root: Optional[Path] = None,
    now: Optional[datetime] = None,
    terminal_state: Optional[Dict[str, Any]] = None,
    terminal_endpoints: Sequence[str] = DEFAULT_TERMINAL_ENDPOINTS,
) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    now_dt = now or utc_now()
    endpoint = ""
    error = ""
    if terminal_state is None:
        terminal_state, endpoint, error = _fetch_terminal_state(terminal_endpoints)
    else:
        endpoint = "injected_terminal_state"
    ecosystem = _read_json(_rooted(root_path, CAPITAL_ECOSYSTEM_PATH), {})
    lifecycle_state = _read_json(_rooted(root_path, ORDER_LIFECYCLE_PATH), {})
    lifecycle_stress = _read_json(_rooted(root_path, ORDER_LIFECYCLE_STRESS_PATH), {})
    exchange_matrix = _read_json(_rooted(root_path, EXCHANGE_MATRIX_PATH), {})
    stream_cache = _read_json(_rooted(root_path, STREAM_CACHE_PATH), {})
    if not isinstance(ecosystem, dict):
        ecosystem = {}
    if not isinstance(lifecycle_state, dict):
        lifecycle_state = {}
    if not isinstance(lifecycle_stress, dict):
        lifecycle_stress = {}
    if not isinstance(exchange_matrix, dict):
        exchange_matrix = {}
    if not isinstance(stream_cache, dict):
        stream_cache = {}

    runtime_proof = _build_runtime_proof(terminal_state=terminal_state, endpoint=endpoint, error=error, now=now_dt)
    watchlist_proof = _build_capital_watchlist_proof(ecosystem)
    lifecycle_route_proof = _build_lifecycle_route_proof(lifecycle_state, ecosystem)
    recovered_position_proof = _build_recovered_position_proof(lifecycle_state, ecosystem)
    recovered_exit_readiness_proof = _build_recovered_exit_readiness_proof(lifecycle_state)
    broker_correlation_proof = _build_broker_correlation_proof(lifecycle_state)
    close_first_proof = _build_close_first_proof(lifecycle_state, ecosystem)
    shadow_hedge_proof = _build_shadow_hedge_proof(ecosystem)
    lifecycle_stress_summary = lifecycle_stress.get("summary") if isinstance(lifecycle_stress.get("summary"), dict) else {}
    exchange_rows = exchange_matrix.get("rows") if isinstance(exchange_matrix.get("rows"), list) else []
    ticker_cache = stream_cache.get("ticker_cache") if isinstance(stream_cache.get("ticker_cache"), dict) else {}

    blockers: List[str] = []
    for proof in (
        runtime_proof,
        watchlist_proof,
        lifecycle_route_proof,
        recovered_position_proof,
        recovered_exit_readiness_proof,
        broker_correlation_proof,
        close_first_proof,
        shadow_hedge_proof,
    ):
        blockers.extend(str(item) for item in proof.get("blockers", []) if str(item))
    if not lifecycle_stress:
        blockers.append("order_lifecycle_stress_audit_missing")
    status = _status_from_blockers(list(dict.fromkeys(blockers)))

    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_dt.isoformat(),
        "status": status,
        "ok": status == "live_dry_certified",
        "mode": "read_only_capital_ecosystem_live_dry_stress",
        "summary": {
            "runtime_fresh": bool(runtime_proof.get("runtime_fresh")),
            "active_watchlist_count": watchlist_proof.get("active_watchlist_count", 0),
            "bench_watchlist_count": watchlist_proof.get("bench_watchlist_count", 0),
            "candidate_count": watchlist_proof.get("candidate_count", 0),
            "active_lifecycle_route_count": lifecycle_route_proof.get("active_lifecycle_route_count", 0),
            "duplicate_routes_blocked": bool(lifecycle_route_proof.get("duplicate_routes_blocked")),
            "duplicate_route_blocked_count": lifecycle_route_proof.get("duplicate_route_blocked_count", 0),
            "close_first_opportunity_count": close_first_proof.get("close_first_opportunity_count", 0),
            "shadow_hedge_count": shadow_hedge_proof.get("shadow_hedge_count", 0),
            "shadow_hedges_only": bool(shadow_hedge_proof.get("shadow_hedges_only")),
            "broker_correlation_complete": bool(broker_correlation_proof.get("broker_correlation_complete")),
            "lifecycle_continuity_complete": not bool(lifecycle_route_proof.get("missing_link_rows")),
            "recovered_position_count": recovered_position_proof.get("recovered_position_count", 0),
            "recovered_positions_certified": bool(recovered_position_proof.get("recovered_positions_certified")),
            "recovery_certification_status": recovered_position_proof.get("recovery_certification_status") or "",
            "recovered_upstream_context_missing_count": len(recovered_position_proof.get("missing_upstream_context_rows") or []),
            "recovered_position_close_first_covered": bool(recovered_position_proof.get("close_first_covered")),
            "recovered_duplicate_route_blocking_active": bool(recovered_position_proof.get("duplicate_route_blocking_active")),
            "recovered_close_chain_status": recovered_exit_readiness_proof.get("recovered_close_chain_status") or "",
            "recovered_close_request_count": recovered_exit_readiness_proof.get("recovered_close_request_count", 0),
            "recovered_close_acknowledged_count": recovered_exit_readiness_proof.get("recovered_close_acknowledged_count", 0),
            "recovered_position_absence_verified_count": recovered_exit_readiness_proof.get("recovered_position_absence_verified_count", 0),
            "recovered_outcome_recorded_count": recovered_exit_readiness_proof.get("recovered_outcome_recorded_count", 0),
            "recovered_exit_blockers": recovered_exit_readiness_proof.get("recovered_exit_blockers") or [],
            "capital_watchlist_within_limit": not any(
                item in watchlist_proof.get("blockers", [])
                for item in ("capital_watchlist_over_limit", "capital_bench_watchlist_over_limit")
            ),
            "lifecycle_stress_certified": lifecycle_stress.get("status") == "order_lifecycle_stress_certified",
            "exchange_matrix_rows": len(exchange_rows),
            "stream_cache_ticker_count": len(ticker_cache),
            "no_live_mutation": True,
        },
        "runtime_proof": runtime_proof,
        "capital_watchlist_proof": watchlist_proof,
        "lifecycle_route_proof": lifecycle_route_proof,
        "recovered_position_proof": recovered_position_proof,
        "recovered_exit_readiness_proof": recovered_exit_readiness_proof,
        "broker_correlation_proof": broker_correlation_proof,
        "close_first_proof": close_first_proof,
        "shadow_hedge_proof": shadow_hedge_proof,
        "lifecycle_stress_proof": {
            "present": bool(lifecycle_stress),
            "status": lifecycle_stress.get("status") or "",
            "mock_broker_certified": bool(lifecycle_stress_summary.get("mock_broker_certified")),
            "sandbox_paper_certified": bool(lifecycle_stress_summary.get("sandbox_paper_certified")),
            "broker_requirement_matrix_complete": bool(lifecycle_stress_summary.get("broker_requirement_matrix_complete")),
        },
        "blockers": list(dict.fromkeys(blockers)),
        "manual_boundaries": MANUAL_BOUNDARIES,
        "source_paths": {
            "terminal_state": endpoint or ",".join(terminal_endpoints),
            "capital_ecosystem": CAPITAL_ECOSYSTEM_PATH.as_posix(),
            "order_lifecycle": ORDER_LIFECYCLE_PATH.as_posix(),
            "order_lifecycle_stress": ORDER_LIFECYCLE_STRESS_PATH.as_posix(),
            "exchange_matrix": EXCHANGE_MATRIX_PATH.as_posix(),
            "stream_cache": STREAM_CACHE_PATH.as_posix(),
        },
        "output_files": [
            DEFAULT_STATE_PATH.as_posix(),
            DEFAULT_AUDIT_JSON.as_posix(),
            DEFAULT_AUDIT_MD.as_posix(),
            DEFAULT_PUBLIC_JSON.as_posix(),
        ],
    }
    return report


def _make_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    lines = [
        "# Aureon Capital Ecosystem Live Dry Stress Audit",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Runtime fresh: `{summary.get('runtime_fresh')}`",
        f"- Capital watchlist: `{summary.get('active_watchlist_count')}/40` active, `{summary.get('bench_watchlist_count')}/100` bench",
        f"- Candidates: `{summary.get('candidate_count')}`",
        f"- Active lifecycle routes: `{summary.get('active_lifecycle_route_count')}`",
        f"- Duplicate routes blocked: `{summary.get('duplicate_routes_blocked')}`",
        f"- Recovered Capital positions: `{summary.get('recovered_position_count')}` status `{summary.get('recovery_certification_status')}`",
        f"- Recovered exit chain: `{summary.get('recovered_close_chain_status')}` close ack `{summary.get('recovered_close_acknowledged_count')}` absence `{summary.get('recovered_position_absence_verified_count')}` outcomes `{summary.get('recovered_outcome_recorded_count')}`",
        f"- Broker correlation complete: `{summary.get('broker_correlation_complete')}`",
        f"- Shadow hedges only: `{summary.get('shadow_hedges_only')}`",
        f"- No live mutation: `{summary.get('no_live_mutation')}`",
        "",
        "## Blockers",
    ]
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    lines.extend(f"- `{blocker}`" for blocker in blockers) if blockers else lines.append("- None visible.")
    return "\n".join(lines) + "\n"


def build_and_write_capital_ecosystem_live_dry_stress_audit(
    *,
    root: Optional[Path] = None,
    terminal_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    report = build_capital_ecosystem_live_dry_stress_audit(root=root_path, terminal_state=terminal_state)
    writes = [
        _write_json(_rooted(root_path, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root_path, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root_path, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_rooted(root_path, DEFAULT_PUBLIC_JSON), report),
    ]
    report["write_info"] = {"evidence_writes": writes}
    for rel_path in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root_path, rel_path), report)
    _write_text(_rooted(root_path, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Capital ecosystem live dry stress proof without broker mutation.")
    parser.add_argument("--repo-root", default="", help="Repository root; defaults to cwd/repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else None
    report = build_and_write_capital_ecosystem_live_dry_stress_audit(root=root)
    print(json.dumps(report, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
