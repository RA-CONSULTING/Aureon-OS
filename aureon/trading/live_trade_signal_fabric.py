"""Active trade-flow fabric for ThoughtBus and Mycelium visibility.

The fabric does not place orders. It publishes the internal A-to-B evidence
chain so the organism can see signals, vetoes, intents, executor phases,
broker proof, positions, closes, and outcomes using one trace id.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "aureon-live-trade-signal-fabric-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = Path("state/aureon_live_trade_signal_fabric_events.jsonl")
STATE_PATH = Path("state/aureon_live_trade_signal_fabric_latest.json")
PUBLIC_PATH = Path("frontend/public/aureon_live_trade_signal_fabric.json")
DEDUPLICATION_BUCKET_SECONDS = 5
DEDUPLICATION_SCAN_LIMIT = 500

PHASE_SEQUENCE = [
    "signal_generated",
    "counter_intel_passed",
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

TERMINAL_PHASES = {
    "outcome_recorded",
    "order_blocked",
    "order_rejected",
    "order_failed",
    "order_cancelled",
    "order_expired",
    "order_rate_limited",
    "close_failed",
}

PHASE_TOPIC = {
    "signal_generated": "trading.signal.generated",
    "counter_intel_passed": "trading.counter_intel.passed",
    "counter_intel_blocked": "trading.counter_intel.blocked",
    "data_ready": "trading.data.ready",
    "candidate_ready": "trading.candidate.ready",
    "intent_published": "trading.intent.published",
    "executor_accepted": "trading.executor.accepted",
    "order_submitted": "trading.order.submitted",
    "broker_acknowledged": "trading.broker.acknowledged",
    "partial_fill": "trading.order.partial_fill",
    "position_open": "trading.position.open",
    "close_requested": "trading.close.requested",
    "close_acknowledged": "trading.close.acknowledged",
    "position_closed": "trading.position.closed",
    "outcome_recorded": "trading.outcome.recorded",
    "order_blocked": "trading.order.blocked",
    "order_rejected": "trading.order.rejected",
    "order_failed": "trading.order.failed",
    "order_cancelled": "trading.order.cancelled",
    "order_expired": "trading.order.expired",
    "order_rate_limited": "trading.rate.pressure",
    "submit_timeout_unverified": "trading.broker.timeout_unknown",
    "close_failed": "trading.close.failed",
}

RATE_BUDGET_REQUIRED_FIELDS = ("rate_limit_family", "rate_remaining", "api_budget_source")
RATE_BUDGET_CAPITAL_WS_PHASES = {"signal_generated", "candidate_ready", "broker_acknowledged", "position_open"}

RATE_BUDGET_VENUE_TAGS = {
    "capital": ["capital_rest_user_budget", "capital_order_position_throttle", "capital_session_freshness"],
    "capital.com": ["capital_rest_user_budget", "capital_order_position_throttle", "capital_session_freshness"],
    "capital_cfd": ["capital_rest_user_budget", "capital_order_position_throttle", "capital_session_freshness"],
    "alpaca": ["alpaca_order_status_budget", "alpaca_trade_sse_cursor", "alpaca_activity_sse_pairing"],
    "binance": ["binance_used_weight", "binance_order_count", "binance_retry_after_or_execution_report"],
    "kraken": ["kraken_rest_counter", "kraken_matching_engine_counter", "kraken_open_order_limit"],
}

LIFECYCLE_STATUS_TO_PHASE = {
    "runtime_started": "runtime_started",
    "data_ready": "data_ready",
    "candidate_ready": "candidate_ready",
    "intent_published": "intent_published",
    "executor_accepted": "executor_accepted",
    "order_submitted": "order_submitted",
    "broker_acknowledged": "broker_acknowledged",
    "partial_fill": "partial_fill",
    "position_open": "position_open",
    "close_requested": "close_requested",
    "close_acknowledged": "close_acknowledged",
    "position_closed": "position_closed",
    "outcome_recorded": "outcome_recorded",
    "order_blocked": "order_blocked",
    "order_rejected": "order_rejected",
    "order_failed": "order_failed",
    "order_cancelled": "order_cancelled",
    "order_expired": "order_expired",
    "order_rate_limited": "order_rate_limited",
    "submit_timeout_unverified": "submit_timeout_unverified",
    "close_failed": "close_failed",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rooted(root: Optional[Path], path: Path) -> Path:
    return (Path(root or REPO_ROOT).resolve() / path).resolve()


def _event_id(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:18]
    return f"ltf-{digest}"


def _timestamp_bucket(value: Any, bucket_seconds: int = DEDUPLICATION_BUCKET_SECONDS) -> int:
    ts = _parse_ts(value)
    if ts <= 0:
        ts = time.time()
    return int(ts // max(1, int(bucket_seconds)))


def _dedupe_identity_from_event(event: Dict[str, Any], bucket_seconds: int = DEDUPLICATION_BUCKET_SECONDS) -> str:
    phase = str(event.get("phase") or event.get("status") or event.get("event_type") or "unknown")
    lifecycle_id = str(event.get("lifecycle_id") or "")
    reference_id = str(event.get("event_ref") or event.get("event_id") or "")
    if not reference_id:
        reference_id = _event_id(
            {
                "phase": phase,
                "lifecycle_id": lifecycle_id,
                "route_key": event.get("route_key"),
                "symbol": event.get("symbol"),
                "side": event.get("side"),
                "source_system": event.get("source_system"),
            }
        )
    bucket = _timestamp_bucket(event.get("generated_at"), bucket_seconds=bucket_seconds)
    identity = f"{reference_id}|{phase}|{lifecycle_id}|{bucket}"
    return hashlib.sha256(identity.encode("utf-8", errors="replace")).hexdigest()[:32]


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _tail_jsonl(path: Path, limit: int = 1000) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                text = line.strip()
                if not text:
                    continue
                try:
                    value = json.loads(text)
                    if isinstance(value, dict):
                        rows.append(value)
                except Exception:
                    continue
    except Exception:
        return []
    return rows[-limit:]


def _write_json_atomic(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(tmp_path, path)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _confidence_from_payload(payload: Dict[str, Any]) -> float:
    for key in ("confidence", "signal_confidence", "self_confidence", "score"):
        value = payload.get(key)
        if value is not None:
            number = _as_float(value, 0.0)
            if number > 1.0:
                number = number / 100.0
            return max(0.0, min(1.0, number))
    return 0.5


def _signal_value(phase: str, payload: Dict[str, Any]) -> float:
    side = str(payload.get("side") or payload.get("direction") or "").upper()
    if phase in {"counter_intel_blocked", "order_blocked", "order_rejected", "order_failed", "close_failed"}:
        return -0.5
    if phase == "outcome_recorded":
        pnl = _as_float(payload.get("net_pnl") or payload.get("last_pnl"), 0.0)
        return 1.0 if pnl > 0 else -1.0 if pnl < 0 else 0.0
    raw = payload.get("signal_score")
    if raw is not None:
        return max(-1.0, min(1.0, _as_float(raw, 0.0)))
    if side == "BUY":
        return _confidence_from_payload(payload)
    if side == "SELL":
        return -_confidence_from_payload(payload)
    return 0.0


def _normalize_phase(phase: Any, payload: Dict[str, Any]) -> str:
    raw = str(phase or payload.get("phase") or payload.get("status") or payload.get("event_type") or "signal_generated").strip()
    return LIFECYCLE_STATUS_TO_PHASE.get(raw, raw)


def expected_rate_budget_tags(event: Dict[str, Any]) -> List[str]:
    venue = str(event.get("venue") or "").lower()
    phase = str(event.get("phase") or "").lower()
    expected = list(RATE_BUDGET_VENUE_TAGS.get(venue, ["api_budget_source"]))
    if venue in {"capital", "capital.com", "capital_cfd"} and phase in RATE_BUDGET_CAPITAL_WS_PHASES:
        expected.append("capital_40_epic_websocket_budget")
    return list(dict.fromkeys(expected))


def _rate_budget_tags_from(data: Dict[str, Any], rate_budget: Dict[str, Any]) -> List[str]:
    raw_tags = (
        data.get("api_budget_tags")
        or data.get("rate_budget_tags")
        or rate_budget.get("tags")
        or rate_budget.get("proof_tags")
        or rate_budget.get("api_budget_tags")
        or []
    )
    if isinstance(raw_tags, str):
        tags = [raw_tags]
    elif isinstance(raw_tags, list):
        tags = [str(item) for item in raw_tags]
    else:
        tags = []
    for tag in expected_rate_budget_tags(data):
        if rate_budget.get(tag) is True or data.get(tag) is True:
            tags.append(tag)
    return list(dict.fromkeys(str(tag).strip() for tag in tags if str(tag).strip()))


def normalize_rate_budget_proof(event: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(event)
    rate_budget = normalized.get("rate_budget") if isinstance(normalized.get("rate_budget"), dict) else {}
    if rate_budget:
        if not normalized.get("rate_limit_family"):
            normalized["rate_limit_family"] = rate_budget.get("family") or rate_budget.get("limit_type") or rate_budget.get("rate_limit_family")
        if normalized.get("rate_remaining") in (None, ""):
            normalized["rate_remaining"] = rate_budget.get("remaining") or rate_budget.get("rate_remaining")
        if not normalized.get("retry_after"):
            normalized["retry_after"] = rate_budget.get("retry_after") or rate_budget.get("retryAfter")
        if not normalized.get("api_budget_source"):
            normalized["api_budget_source"] = rate_budget.get("source") or rate_budget.get("api_budget_source")
    tags = _rate_budget_tags_from(normalized, rate_budget)
    expected_tags = expected_rate_budget_tags(normalized)
    missing_fields = [field for field in RATE_BUDGET_REQUIRED_FIELDS if normalized.get(field) in (None, "")]
    missing_tags = [tag for tag in expected_tags if tag not in tags]
    normalized["api_budget_tags"] = tags
    normalized["expected_api_budget_tags"] = expected_tags
    normalized["missing_rate_budget_fields"] = missing_fields
    normalized["missing_api_budget_tags"] = missing_tags
    normalized["rate_budget_certified"] = not missing_fields and not missing_tags
    normalized["rate_budget_status"] = "rate_budget_certified" if normalized["rate_budget_certified"] else "rate_budget_missing"
    return normalized


def build_api_budget_proof(
    *,
    venue: Any,
    phase: Any,
    source: str,
    family: Optional[str] = None,
    remaining: Any = None,
    retry_after: Any = None,
    tags: Optional[Iterable[Any]] = None,
    status_code: Any = None,
    rate_limited: bool = False,
    response_ok: bool = False,
    session_age_sec: Any = None,
    session_fresh: Optional[bool] = None,
    order_position_throttle_ok: bool = False,
    websocket_subscription_count: Any = None,
    websocket_limit: int = 40,
    alpaca_trade_event_seen: bool = False,
    alpaca_activity_event_id: Any = None,
    alpaca_since_id: Any = None,
    binance_execution_report_seen: bool = False,
    binance_query_reconciled: bool = False,
    kraken_rest_counter_ok: bool = False,
    kraken_order_counter_ok: bool = False,
    kraken_open_order_limit_ok: bool = False,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build normalized API-budget proof for producer fabric events.

    This helper records observed safety facts. It does not place orders or
    consume any broker budget; callers pass facts they already observed while
    producing the event.
    """

    venue_key = str(venue or "").lower()
    phase_key = str(phase or "").lower()
    observed_tags = [str(item).strip() for item in (tags or []) if str(item).strip()]
    details: Dict[str, Any] = dict(extra or {})
    if status_code not in (None, ""):
        details["status_code"] = status_code
    if retry_after not in (None, ""):
        details["retry_after"] = retry_after

    if venue_key in {"capital", "capital.com", "capital_cfd"}:
        if session_fresh is None:
            try:
                session_fresh = session_age_sec not in (None, "") and float(session_age_sec) <= 600.0
            except Exception:
                session_fresh = False
        if not rate_limited and status_code != 429:
            observed_tags.append("capital_rest_user_budget")
        if order_position_throttle_ok or response_ok:
            observed_tags.append("capital_order_position_throttle")
        if session_fresh or response_ok:
            observed_tags.append("capital_session_freshness")
        try:
            ws_count = int(websocket_subscription_count) if websocket_subscription_count not in (None, "") else None
        except Exception:
            ws_count = None
        if ws_count is not None:
            details["websocket_subscription_count"] = ws_count
            details["websocket_limit"] = websocket_limit
            if ws_count <= websocket_limit:
                observed_tags.append("capital_40_epic_websocket_budget")

    elif venue_key == "alpaca":
        if alpaca_trade_event_seen:
            observed_tags.append("alpaca_trade_sse_cursor")
            observed_tags.append("alpaca_order_status_budget")
        if alpaca_activity_event_id and alpaca_since_id:
            observed_tags.append("alpaca_activity_sse_pairing")

    elif venue_key == "binance":
        if not rate_limited and status_code not in (429, 418):
            observed_tags.append("binance_used_weight")
            observed_tags.append("binance_order_count")
        if binance_execution_report_seen or binance_query_reconciled or retry_after not in (None, ""):
            observed_tags.append("binance_retry_after_or_execution_report")
        try:
            status_number = int(status_code) if status_code not in (None, "") else 0
        except Exception:
            status_number = 0
        if status_number >= 500:
            details["execution_status"] = "unknown_until_stream_or_query_proof"

    elif venue_key == "kraken":
        if kraken_rest_counter_ok:
            observed_tags.append("kraken_rest_counter")
        if kraken_order_counter_ok:
            observed_tags.append("kraken_matching_engine_counter")
        if kraken_open_order_limit_ok:
            observed_tags.append("kraken_open_order_limit")

    observed_tags = list(dict.fromkeys(observed_tags))
    expected_tags = expected_rate_budget_tags({"venue": venue_key, "phase": phase_key})
    missing_tags = [tag for tag in expected_tags if tag not in observed_tags]
    if remaining in (None, ""):
        remaining = 1 if observed_tags and not missing_tags and not rate_limited else 0
    proof = {
        "family": family or f"{venue_key or 'unknown'}_api_budget",
        "remaining": remaining,
        "source": source,
        "tags": observed_tags,
        "expected_tags": expected_tags,
        "missing_tags": missing_tags,
        "rate_limited": bool(rate_limited),
        "status": "rate_budget_certified" if not missing_tags and not rate_limited else "rate_budget_attention",
    }
    if retry_after not in (None, ""):
        proof["retry_after"] = retry_after
    if details:
        proof["details"] = details
    return proof


def normalize_trade_flow_event(
    phase: Any,
    payload: Optional[Dict[str, Any]] = None,
    *,
    source_system: str = "unknown",
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    data = dict(payload or {})
    phase_key = _normalize_phase(phase, data)
    timestamp = str(generated_at or data.get("generated_at") or data.get("event_time") or utc_now())
    lifecycle_id = str(data.get("lifecycle_id") or "")
    candidate_id = str(data.get("candidate_id") or "")
    intent_id = str(data.get("intent_id") or data.get("id") or "")
    route_key = str(data.get("route_key") or "")
    trace_id = str(data.get("trace_id") or lifecycle_id or intent_id or candidate_id or route_key or "")
    if not trace_id:
        trace_id = _event_id({"phase": phase_key, "generated_at": timestamp, "source": source_system})
    event: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": timestamp,
        "phase": phase_key,
        "topic": PHASE_TOPIC.get(phase_key, f"trading.{phase_key}"),
        "source_system": str(data.get("source") or source_system or "unknown"),
        "publisher_owner": str(data.get("publisher_owner") or source_system or "unknown"),
        "trace_id": trace_id,
        "lifecycle_id": lifecycle_id,
        "candidate_id": candidate_id,
        "intent_id": intent_id,
        "route_key": route_key,
        "venue": str(data.get("venue") or ""),
        "market_type": str(data.get("market_type") or ""),
        "symbol": str(data.get("symbol") or data.get("epic") or ""),
        "side": str(data.get("side") or data.get("direction") or "").upper(),
        "authority_mode": str(data.get("authority_mode") or data.get("runtime_gate") or ""),
        "expected_net_revenue": data.get("expected_net_revenue"),
        "three_p_floor_passed": bool(data.get("three_p_floor_passed")) if "three_p_floor_passed" in data else None,
        "confidence": data.get("confidence"),
        "signal_score": data.get("signal_score"),
        "blockers": list(data.get("blockers") or data.get("intent_publish_blockers") or []),
        "deal_reference": data.get("deal_reference") or data.get("dealReference"),
        "deal_id": data.get("deal_id") or data.get("dealId"),
        "broker_order_id": data.get("broker_order_id") or data.get("order_id") or data.get("orderId") or data.get("kraken_order_id") or data.get("txid"),
        "client_order_id": data.get("client_order_id") or data.get("clientOrderId") or data.get("newClientOrderId") or data.get("cl_ord_id") or data.get("clOrdId"),
        "cl_ord_id": data.get("cl_ord_id") or data.get("clOrdId"),
        "venue_status": data.get("venue_status"),
        "filled_qty": data.get("filled_qty"),
        "remaining_qty": data.get("remaining_qty"),
        "avg_fill_price": data.get("avg_fill_price"),
        "fees": data.get("fees"),
        "verification_source": data.get("verification_source") or data.get("source"),
        "proof_mode": data.get("proof_mode"),
        "rate_budget": data.get("rate_budget") or data.get("api_governor") or {},
        "phase_latency_ms": data.get("phase_latency_ms"),
        "rate_limit_family": data.get("rate_limit_family"),
        "rate_remaining": data.get("rate_remaining"),
        "retry_after": data.get("retry_after"),
        "api_budget_source": data.get("api_budget_source"),
        "bus_delivery_count": data.get("bus_delivery_count"),
        "mycelium_delivery_count": data.get("mycelium_delivery_count"),
        "trace_health": data.get("trace_health"),
        "next_required_phase": data.get("next_required_phase"),
        "stream_event_type": data.get("stream_event_type"),
        "activity_event_id": data.get("activity_event_id"),
        "sse_replay_cursor": data.get("sse_replay_cursor") or data.get("since_id"),
        "position_present": data.get("position_present"),
        "position_absence_verified": data.get("position_absence_verified"),
        "net_pnl": data.get("net_pnl"),
        "event_ref": data.get("event_id"),
    }
    event = normalize_rate_budget_proof(event)
    if not event.get("next_required_phase") and phase_key in PHASE_SEQUENCE:
        next_index = PHASE_SEQUENCE.index(phase_key) + 1
        event["next_required_phase"] = PHASE_SEQUENCE[next_index] if next_index < len(PHASE_SEQUENCE) else ""
    if not event.get("trace_health"):
        event["trace_health"] = "complete" if phase_key == "outcome_recorded" else "in_progress"
    event = {key: value for key, value in event.items() if value is not None and value != ""}
    event["event_id"] = _event_id(event)
    event["dedupe_bucket"] = _timestamp_bucket(event.get("generated_at"))
    event["dedupe_identity"] = _dedupe_identity_from_event(event)
    event["dedupe_applied"] = False
    return event


def _publish_to_thought_bus(event: Dict[str, Any], thought_bus: Any = None, emit_external: bool = True) -> Dict[str, Any]:
    if not emit_external:
        return {"attempted": False, "ok": False, "reason": "external_emit_disabled"}
    try:
        bus = thought_bus
        Thought = None
        if bus is None:
            from aureon.core.aureon_thought_bus import Thought as ThoughtClass, get_thought_bus

            Thought = ThoughtClass
            bus = get_thought_bus()
        else:
            try:
                from aureon.core.aureon_thought_bus import Thought as ThoughtClass

                Thought = ThoughtClass
            except Exception:
                Thought = None
        if bus is None:
            return {"attempted": True, "ok": False, "reason": "thought_bus_unavailable"}
        if Thought is not None:
            bus.publish(
                Thought(
                    source="live_trade_signal_fabric",
                    topic=str(event.get("topic") or "trading.signal.generated"),
                    trace_id=str(event.get("trace_id") or event.get("event_id")),
                    payload=event,
                    meta={"mode": "active_trade_flow_fabric"},
                )
            )
        else:
            bus.publish(str(event.get("topic") or "trading.signal.generated"), event, source="live_trade_signal_fabric")
        return {"attempted": True, "ok": True, "reason": ""}
    except Exception as exc:
        return {"attempted": True, "ok": False, "reason": str(exc)}


def _ingest_mycelium(event: Dict[str, Any], mycelium: Any = None, emit_external: bool = True) -> Dict[str, Any]:
    if not emit_external:
        return {"attempted": False, "ok": False, "reason": "external_emit_disabled"}
    try:
        mesh = mycelium
        if mesh is None:
            from aureon.core.aureon_mycelium import get_mycelium

            mesh = get_mycelium()
        if mesh is None:
            return {"attempted": True, "ok": False, "reason": "mycelium_unavailable"}
        signal = _signal_value(str(event.get("phase") or ""), event)
        confidence = _confidence_from_payload(event)
        if hasattr(mesh, "receive_external_signal"):
            mesh.receive_external_signal("live_trade_signal_fabric", signal, confidence=confidence)
        if hasattr(mesh, "connection_map"):
            connection_map = getattr(mesh, "connection_map")
            if isinstance(connection_map, dict):
                proof = connection_map.setdefault(
                    "live_trade_signal_fabric",
                    {
                        "connected_at": time.time(),
                        "signals_received": 0,
                        "last_event": {},
                        "phase_counts": {},
                    },
                )
                if isinstance(proof, dict):
                    proof["signals_received"] = int(proof.get("signals_received", 0) or 0) + 1
                    proof["last_event"] = {
                        "event_id": event.get("event_id"),
                        "phase": event.get("phase"),
                        "trace_id": event.get("trace_id"),
                        "route_key": event.get("route_key"),
                        "symbol": event.get("symbol"),
                        "generated_at": event.get("generated_at"),
                    }
                    phase_counts = proof.setdefault("phase_counts", {})
                    if isinstance(phase_counts, dict):
                        phase = str(event.get("phase") or "unknown")
                        phase_counts[phase] = int(phase_counts.get(phase, 0) or 0) + 1
        if hasattr(mesh, "propagate_to_all"):
            try:
                delivered = mesh.propagate_to_all("trade_flow_event", event)
            except Exception:
                delivered = 0
        else:
            delivered = 0
        return {"attempted": True, "ok": True, "reason": "", "propagated_count": delivered}
    except Exception as exc:
        return {"attempted": True, "ok": False, "reason": str(exc)}


def _parse_ts(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0.0


def build_state_from_events(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = [dict(event) for event in events if isinstance(event, dict)]
    rows.sort(key=lambda event: _parse_ts(event.get("generated_at")))
    phase_counts = Counter(str(event.get("phase") or "unknown") for event in rows)
    trace_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for event in rows:
        trace_key = str(event.get("trace_id") or event.get("lifecycle_id") or event.get("event_id") or "unknown")
        trace_events[trace_key].append(event)

    traces: List[Dict[str, Any]] = []
    broken: List[Dict[str, Any]] = []
    complete_count = 0
    p95_samples: List[float] = []
    for trace_id, trace_rows in trace_events.items():
        phases = [str(event.get("phase") or "unknown") for event in trace_rows]
        latest = trace_rows[-1] if trace_rows else {}
        highest_index = max((PHASE_SEQUENCE.index(phase) for phase in phases if phase in PHASE_SEQUENCE), default=-1)
        missing_before_latest = [
            phase for phase in PHASE_SEQUENCE[: max(0, highest_index + 1)] if phase not in phases
        ]
        start_ts = _parse_ts(trace_rows[0].get("generated_at")) if trace_rows else 0.0
        end_ts = _parse_ts(latest.get("generated_at")) if latest else 0.0
        duration_ms = max(0.0, (end_ts - start_ts) * 1000.0) if start_ts and end_ts else 0.0
        if duration_ms:
            p95_samples.append(duration_ms)
        complete = "outcome_recorded" in phases
        if complete:
            complete_count += 1
        trace = {
            "trace_id": trace_id,
            "lifecycle_id": latest.get("lifecycle_id") or "",
            "route_key": latest.get("route_key") or "",
            "venue": latest.get("venue") or "",
            "symbol": latest.get("symbol") or "",
            "side": latest.get("side") or "",
            "latest_phase": latest.get("phase") or "",
            "latest_generated_at": latest.get("generated_at") or "",
            "phase_count": len(phases),
            "phases": phases[-16:],
            "missing_phases": missing_before_latest,
            "complete": complete,
            "active": not complete and str(latest.get("phase") or "") not in TERMINAL_PHASES,
            "duration_ms": round(duration_ms, 3),
            "last_broker_proof": latest.get("deal_id") or latest.get("broker_order_id") or latest.get("deal_reference") or "",
            "last_net_pnl": latest.get("net_pnl"),
            "events": trace_rows[-8:],
        }
        traces.append(trace)
        if missing_before_latest:
            broken.append({
                "trace_id": trace_id,
                "latest_phase": trace["latest_phase"],
                "missing_phases": missing_before_latest,
                "route_key": trace["route_key"],
                "symbol": trace["symbol"],
            })
    traces.sort(key=lambda row: str(row.get("latest_generated_at") or ""), reverse=True)
    thoughtbus_ok = any(bool(event.get("thoughtbus_publish_ok")) for event in rows)
    mycelium_ok = any(bool(event.get("mycelium_ingest_ok")) for event in rows)
    rate_pressure = [
        event for event in rows
        if str(event.get("phase") or "").lower() in {"order_rate_limited", "rate_limited", "api_rate_pressure"}
        or str(event.get("topic") or "").lower() == "trading.rate.pressure"
        or any("rate_limit" in str(blocker).lower() or "too_many" in str(blocker).lower() for blocker in (event.get("blockers") or []))
    ]
    active_count = sum(1 for trace in traces if trace.get("active"))
    if not rows:
        status = "trade_flow_waiting_for_signal"
    elif rate_pressure:
        status = "trade_flow_rate_limited"
    elif not thoughtbus_ok:
        status = "thoughtbus_not_receiving"
    elif not mycelium_ok:
        status = "mycelium_not_receiving"
    elif broken:
        status = "trade_flow_broken"
    elif any(trace.get("latest_phase") == "order_submitted" for trace in traces):
        status = "trade_flow_waiting_for_broker_ack"
    elif any(trace.get("latest_phase") == "intent_published" for trace in traces):
        status = "trade_flow_waiting_for_executor"
    else:
        status = "trade_flow_active"

    p95 = 0.0
    if p95_samples:
        ordered = sorted(p95_samples)
        index = min(len(ordered) - 1, int(round((len(ordered) - 1) * 0.95)))
        p95 = ordered[index]
    latest = rows[-1] if rows else {}
    state = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": status,
        "mode": "active_internal_trade_flow_fabric",
        "summary": {
            "event_count": len(rows),
            "thoughtbus_receiving": thoughtbus_ok,
            "mycelium_receiving": mycelium_ok,
            "active_trace_count": active_count,
            "complete_trace_count": complete_count,
            "broken_trace_count": len(broken),
            "live_order_submitted_count": phase_counts.get("order_submitted", 0),
            "broker_ack_count": phase_counts.get("broker_acknowledged", 0),
            "position_open_count": phase_counts.get("position_open", 0),
            "outcome_recorded_count": phase_counts.get("outcome_recorded", 0),
            "p95_phase_latency_ms": round(p95, 3),
            "api_rate_pressure_count": len(rate_pressure),
        },
        "thoughtbus_proof": {
            "receiving": thoughtbus_ok,
            "published_count": sum(1 for event in rows if event.get("thoughtbus_publish_ok")),
            "latest_reason": latest.get("thoughtbus_publish_reason") or "",
        },
        "mycelium_proof": {
            "receiving": mycelium_ok,
            "ingested_count": sum(1 for event in rows if event.get("mycelium_ingest_ok")),
            "latest_reason": latest.get("mycelium_ingest_reason") or "",
        },
        "active_traces": traces[:20],
        "phase_counts": dict(sorted(phase_counts.items())),
        "broken_chains": broken[:20],
        "rate_pressure": rate_pressure[-20:],
        "latest_live_trade_trace": traces[0] if traces else {},
        "events": rows[-80:],
        "source_paths": {
            "jsonl": LOG_PATH.as_posix(),
            "state": STATE_PATH.as_posix(),
            "public": PUBLIC_PATH.as_posix(),
            "thoughtbus": "aureon_thought_bus.jsonl",
            "mycelium": "aureon.core.aureon_mycelium.get_mycelium",
        },
    }
    return state


def _write_state_for_event(event: Dict[str, Any], root: Optional[Path]) -> Dict[str, Any]:
    log_path = rooted(root, LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    tail = _tail_jsonl(log_path, DEDUPLICATION_SCAN_LIMIT)
    dedupe_identity = str(event.get("dedupe_identity") or "")
    duplicate = bool(
        dedupe_identity
        and any(str(row.get("dedupe_identity") or "") == dedupe_identity for row in tail if isinstance(row, dict))
    )
    event["dedupe_applied"] = duplicate
    if not duplicate:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
        tail = _tail_jsonl(log_path, 1000)
    else:
        tail = tail[-1000:]
    state = build_state_from_events(tail)
    summary = state.get("summary") if isinstance(state.get("summary"), dict) else {}
    if isinstance(summary, dict):
        summary["dedupe_applied_count"] = int(summary.get("dedupe_applied_count", 0) or 0) + int(1 if duplicate else 0)
        summary["dedupe_last_identity"] = dedupe_identity
        state["summary"] = summary
    for rel in (STATE_PATH, PUBLIC_PATH):
        _write_json_atomic(rooted(root, rel), state)
    return state


def publish_trade_flow_event(
    phase: Any,
    payload: Optional[Dict[str, Any]] = None,
    *,
    source_system: str = "unknown",
    root: Optional[Path] = None,
    thought_bus: Any = None,
    mycelium: Any = None,
    emit_external: bool = True,
    write_artifacts: bool = True,
) -> Dict[str, Any]:
    event = normalize_trade_flow_event(phase, payload, source_system=source_system)
    thought_result = _publish_to_thought_bus(event, thought_bus=thought_bus, emit_external=emit_external)
    mycelium_result = _ingest_mycelium(event, mycelium=mycelium, emit_external=emit_external)
    event["thoughtbus_publish_attempted"] = bool(thought_result.get("attempted"))
    event["thoughtbus_publish_ok"] = bool(thought_result.get("ok"))
    event["thoughtbus_publish_reason"] = str(thought_result.get("reason") or "")
    event["mycelium_ingest_attempted"] = bool(mycelium_result.get("attempted"))
    event["mycelium_ingest_ok"] = bool(mycelium_result.get("ok"))
    event["mycelium_ingest_reason"] = str(mycelium_result.get("reason") or "")
    event["mycelium_propagated_count"] = int(mycelium_result.get("propagated_count", 0) or 0)
    event["bus_delivery_count"] = int(event.get("bus_delivery_count") or (1 if event["thoughtbus_publish_ok"] else 0))
    event["mycelium_delivery_count"] = int(
        event.get("mycelium_delivery_count")
        or event["mycelium_propagated_count"]
        or (1 if event["mycelium_ingest_ok"] else 0)
    )
    if write_artifacts:
        _write_state_for_event(event, root)
    return event


def publish_lifecycle_event(
    lifecycle_event: Dict[str, Any],
    *,
    root: Optional[Path] = None,
    emit_external: bool = True,
) -> Dict[str, Any]:
    phase = _normalize_phase(lifecycle_event.get("status") or lifecycle_event.get("event_type"), lifecycle_event)
    return publish_trade_flow_event(
        phase,
        lifecycle_event,
        source_system=str(lifecycle_event.get("source") or "order_lifecycle"),
        root=root,
        emit_external=emit_external,
    )


def rebuild_latest(root: Optional[Path] = None) -> Dict[str, Any]:
    state = build_state_from_events(_tail_jsonl(rooted(root, LOG_PATH), 1000))
    for rel in (STATE_PATH, PUBLIC_PATH):
        _write_json_atomic(rooted(root, rel), state)
    return state


def latest_for_ui(root: Optional[Path] = None) -> Dict[str, Any]:
    state = _read_json(rooted(root, STATE_PATH), {})
    if isinstance(state, dict) and state:
        return state
    return rebuild_latest(root)


__all__ = [
    "SCHEMA_VERSION",
    "PHASE_SEQUENCE",
    "LOG_PATH",
    "STATE_PATH",
    "PUBLIC_PATH",
    "build_state_from_events",
    "build_api_budget_proof",
    "expected_rate_budget_tags",
    "latest_for_ui",
    "normalize_rate_budget_proof",
    "normalize_trade_flow_event",
    "publish_lifecycle_event",
    "publish_trade_flow_event",
    "rebuild_latest",
]
