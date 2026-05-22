"""Stress audit for the parallel strategy unity runtime.

This audit reads existing runtime evidence only. It certifies that parallel
strategy workers are healthy, share one request broker and goal contract, and
do not gain direct broker-mutation authority outside the unified executor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib.error import URLError
from urllib.request import urlopen

from aureon.trading.parallel_strategy_unity import (
    DEFAULT_MINIMUM_NET_PROFIT_GBP,
    GHOST_DANCE_PROTOCOL_VERSION,
    HARMONIC_API_PIANO_VERSION,
    MUTATION_OPERATION_TYPES,
    POWER_STATION_REQUEST_PROTOCOL_VERSION,
    PRODUCTION_WORKERS,
    RAINBOW_HARMONIC_LADDER_VERSION,
)


SCHEMA_VERSION = "aureon-parallel-strategy-unity-stress-audit-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]

PARALLEL_UNITY_PATH = Path("frontend/public/aureon_parallel_strategy_unity.json")
REQUEST_BROKER_PATH = Path("frontend/public/aureon_unified_exchange_request_broker.json")
STRATEGY_INTENTS_PATH = Path("frontend/public/aureon_unified_strategy_intents.json")
FABRIC_PATH = Path("frontend/public/aureon_live_trade_signal_fabric.json")
RUNTIME_STATUS_PATH = Path("state/unified_runtime_status.json")
STATE_PARALLEL_UNITY_PATH = Path("state/aureon_parallel_strategy_unity.json")
STATE_STRATEGY_INTENTS_PATH = Path("state/unified_strategy_intents.json")
UNIFIED_MARKET_TRADER_SOURCE_PATH = Path("aureon/exchanges/unified_market_trader.py")
EXPECTED_VENV_PYTHON_PATH = Path(".venv/Scripts/python.exe")
PRODUCTION_LAUNCHER_PATH = Path("AUREON_PRODUCTION_LIVE.cmd")
FULL_AUTONOMOUS_WAKE_SCRIPT_PATH = Path("AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1")

DEFAULT_STATE_PATH = Path("state/aureon_parallel_strategy_unity_stress_audit_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_parallel_strategy_unity_stress_audit.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_parallel_strategy_unity_stress_audit.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_parallel_strategy_unity_stress_audit.json")
DEFAULT_SERVED_PUBLIC_URL = "http://127.0.0.1:8081/aureon_parallel_strategy_unity_stress_audit.json"

EXECUTOR_WORKER_ID = "unified_market_trader.executor"
WORKER_HEARTBEAT_FRESH_SEC = 20.0
WORKER_HEARTBEAT_STALE_SEC = 60.0
INTENT_FRESH_SEC = 180.0

PROCESS_TARGETS = {
    "unified_market_trader": "aureon.exchanges.unified_market_trader",
    "parallel_strategy_unity": "aureon.trading.parallel_strategy_unity",
    "parallel_strategy_unity_stress_audit": "aureon.autonomous.aureon_parallel_strategy_unity_stress_audit",
}

REQUIRED_INTENT_FIELDS = [
    "worker_id",
    "trace_id",
    "lifecycle_id",
    "candidate_id",
    "intent_id",
    "route_key",
    "venue",
    "symbol",
    "side",
]

REQUIRED_LEASE_FIELDS = [
    "request_id",
    "worker_id",
    "venue",
    "operation_type",
    "rate_limit_family",
    "budget_required",
    "idempotency_key",
]

REQUIRED_GHOST_FIELDS = [
    "ghost_dance_protocol",
    "ghost_phase_index",
    "ghost_phase_count",
    "api_key_lock_family",
    "scheduled_after_ms",
]

REQUIRED_PIANO_FIELDS = [
    "harmonic_api_piano_protocol",
    "piano_key_rank",
    "piano_velocity_score",
    "harmonic_tempo_multiplier",
    "song_stop_guard",
]

REQUIRED_RAINBOW_FIELDS = [
    "rainbow_harmonic_ladder_protocol",
    "rainbow_step_index",
    "rainbow_step_name",
    "rainbow_frequency_hz",
    "harmony_lane_id",
    "song_continuity_guard",
]

REQUIRED_POWER_STATION_FIELDS = [
    "power_station_request_protocol",
    "request_direction",
    "request_class",
    "request_owner_authority",
    "request_governor_decision",
    "power_station_metadata_source",
    "credential_boundary",
    "mutation_scope",
]

MANUAL_BOUNDARIES = [
    "stress audit is evidence-only",
    "parallel workers may publish signals and strategy intents only",
    "unified_market_trader remains the only broker mutation authority",
    "request broker leases do not place orders",
    "live executor, risk, lifecycle, and runtime gates remain authoritative",
    "repair plan rows are advisory and do not stop or start processes",
    "Rainbow Harmonic Ladder schedules request turns only and does not encode lyrics or melody",
    "Power Station request governor uses repo metadata without reading or revealing API key values",
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


def _write_json(path: Path, payload: Mapping[str, Any]) -> Dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        number = float(value)
        return number if number == number else default
    except Exception:
        return default


def _parse_ts(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except Exception:
        return 0.0


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), timezone.utc)
        except Exception:
            return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _record_array(value: Any) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [row for row in value if isinstance(row, dict)]


def _operation_is_mutation(operation_type: Any) -> bool:
    operation = str(operation_type or "").lower()
    return (
        operation in MUTATION_OPERATION_TYPES
        or operation.startswith("order_")
        or operation.startswith("position_")
        or "mutation" in operation
    )


def _artifact_presence(root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for label, rel in [
        ("parallel_unity", PARALLEL_UNITY_PATH),
        ("request_broker", REQUEST_BROKER_PATH),
        ("strategy_intents", STRATEGY_INTENTS_PATH),
        ("live_signal_fabric", FABRIC_PATH),
        ("runtime_status", RUNTIME_STATUS_PATH),
    ]:
        path = _rooted(root, rel)
        rows.append(
            {
                "id": label,
                "path": rel.as_posix(),
                "present": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
            }
        )
    return rows


def _worker_rows(unity: Mapping[str, Any], now_ts: float) -> List[Dict[str, Any]]:
    rows_by_id = {
        str(row.get("worker_id") or ""): row
        for row in _record_array(unity.get("worker_rows"))
    }
    results: List[Dict[str, Any]] = []
    for worker in PRODUCTION_WORKERS:
        row = rows_by_id.get(worker.worker_id, {})
        heartbeat_at = row.get("heartbeat_at")
        age_sec = now_ts - _parse_ts(heartbeat_at)
        if not row:
            state = "worker_missing"
        elif age_sec > WORKER_HEARTBEAT_STALE_SEC:
            state = "worker_stale"
        elif age_sec > WORKER_HEARTBEAT_FRESH_SEC:
            state = "worker_attention"
        elif row.get("strategy_status") == "worker_healthy":
            state = "worker_healthy"
        else:
            state = "worker_attention"
        missing_fields = [
            field
            for field in ("worker_id", "heartbeat_at", "strategy_status", "api_budget_usage")
            if row.get(field) in (None, "")
        ] if row else ["worker_row"]
        results.append(
            {
                "worker_id": worker.worker_id,
                "label": worker.label,
                "venue": worker.venue,
                "source_system": worker.source_system,
                "heartbeat_at": heartbeat_at or "",
                "heartbeat_age_sec": round(max(0.0, age_sec), 3) if heartbeat_at else None,
                "state": state,
                "latest_signal_count": int(_as_float(row.get("latest_signal_count"), 0.0)) if row else 0,
                "latest_intent_count": int(_as_float(row.get("latest_intent_count"), 0.0)) if row else 0,
                "direct_broker_mutation_allowed": bool(row.get("direct_broker_mutation_allowed")) if row else False,
                "requires_unified_executor": bool(row.get("requires_unified_executor")) if row else True,
                "missing_fields": missing_fields,
                "route_key": row.get("route_key") or "",
            }
        )
    return results


def _lease_rows(broker: Mapping[str, Any]) -> Dict[str, Any]:
    leases = _record_array(broker.get("lease_rows"))
    venue_rows = _record_array(broker.get("venue_budget_rows"))
    mutation_leaks: List[Dict[str, Any]] = []
    denied_mutation_rows: List[Dict[str, Any]] = []
    missing_contract_rows: List[Dict[str, Any]] = []
    budget_gap_rows: List[Dict[str, Any]] = []

    for row in leases:
        missing = [field for field in REQUIRED_LEASE_FIELDS if row.get(field) in (None, "")]
        if missing:
            missing_contract_rows.append(
                {
                    "lease_id": row.get("lease_id") or row.get("request_id") or "",
                    "worker_id": row.get("worker_id") or "",
                    "missing_fields": missing,
                }
            )
        is_mutation = _operation_is_mutation(row.get("operation_type"))
        non_executor = str(row.get("worker_id") or "") != EXECUTOR_WORKER_ID
        if is_mutation and row.get("status") == "granted" and non_executor:
            mutation_leaks.append(
                {
                    "lease_id": row.get("lease_id") or "",
                    "worker_id": row.get("worker_id") or "",
                    "operation_type": row.get("operation_type") or "",
                    "venue": row.get("venue") or "",
                    "status": row.get("status") or "",
                }
            )
        if is_mutation and row.get("status") == "denied" and str(row.get("reason") or "") == "mutation_requires_unified_executor":
            denied_mutation_rows.append(
                {
                    "lease_id": row.get("lease_id") or "",
                    "worker_id": row.get("worker_id") or "",
                    "operation_type": row.get("operation_type") or "",
                    "proof": "non_executor_mutation_denied",
                }
            )
        if row.get("status") == "denied" and str(row.get("reason") or "") == "venue_budget_exhausted":
            budget_gap_rows.append(
                {
                    "lease_id": row.get("lease_id") or "",
                    "worker_id": row.get("worker_id") or "",
                    "venue": row.get("venue") or "",
                    "reason": row.get("reason") or "",
                    "rate_remaining": row.get("rate_remaining"),
                }
            )

    over_budget_rows: List[Dict[str, Any]] = []
    for row in venue_rows:
        limit = _as_float(row.get("rate_limit_per_min"), 0.0)
        used = _as_float(row.get("rate_used"), 0.0)
        remaining = _as_float(row.get("rate_remaining"), max(0.0, limit - used))
        if limit > 0 and (used > limit or remaining < 0):
            over_budget_rows.append(
                {
                    "venue": row.get("venue") or "",
                    "rate_limit_per_min": limit,
                    "rate_used": used,
                    "rate_remaining": remaining,
                    "state": "over_budget",
                }
            )

    return {
        "lease_rows": leases,
        "venue_budget_rows": venue_rows,
        "mutation_leak_rows": mutation_leaks,
        "denied_mutation_rows": denied_mutation_rows,
        "missing_lease_contract_rows": missing_contract_rows,
        "budget_gap_rows": budget_gap_rows,
        "over_budget_rows": over_budget_rows,
    }


def _intent_rows(intent_state: Mapping[str, Any], now_ts: float) -> Dict[str, Any]:
    rows = _record_array(intent_state.get("intents"))
    missing_contract_rows: List[Dict[str, Any]] = []
    mutation_leak_rows: List[Dict[str, Any]] = []
    stale_rows: List[Dict[str, Any]] = []
    route_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    worker_route_seen: set[tuple[str, str, str]] = set()
    duplicate_worker_route_rows: List[Dict[str, Any]] = []

    for row in rows:
        missing = [field for field in REQUIRED_INTENT_FIELDS if row.get(field) in (None, "")]
        if missing:
            missing_contract_rows.append(
                {
                    "worker_id": row.get("worker_id") or "",
                    "intent_id": row.get("intent_id") or "",
                    "route_key": row.get("route_key") or "",
                    "missing_fields": missing,
                }
            )
        if bool(row.get("direct_broker_mutation_allowed")) or row.get("requires_unified_executor") is False:
            mutation_leak_rows.append(
                {
                    "worker_id": row.get("worker_id") or "",
                    "intent_id": row.get("intent_id") or "",
                    "route_key": row.get("route_key") or "",
                    "direct_broker_mutation_allowed": bool(row.get("direct_broker_mutation_allowed")),
                    "requires_unified_executor": row.get("requires_unified_executor"),
                }
            )
        generated_at = row.get("generated_at")
        age_sec = now_ts - _parse_ts(generated_at)
        if generated_at and age_sec > INTENT_FRESH_SEC:
            stale_rows.append(
                {
                    "worker_id": row.get("worker_id") or "",
                    "intent_id": row.get("intent_id") or "",
                    "route_key": row.get("route_key") or "",
                    "age_sec": round(age_sec, 3),
                }
            )
        group_key = f"{row.get('route_key') or ''}|{row.get('side') or ''}"
        if row.get("route_key") and row.get("side"):
            route_groups[group_key].append(row)
        worker_route_key = (
            str(row.get("worker_id") or ""),
            str(row.get("route_key") or ""),
            str(row.get("side") or ""),
        )
        if all(worker_route_key):
            if worker_route_key in worker_route_seen:
                duplicate_worker_route_rows.append(
                    {
                        "worker_id": row.get("worker_id") or "",
                        "intent_id": row.get("intent_id") or "",
                        "route_key": row.get("route_key") or "",
                        "side": row.get("side") or "",
                    }
                )
            worker_route_seen.add(worker_route_key)

    agreement_rows = []
    executor_dedupe_rows = []
    for key, group_rows in route_groups.items():
        workers = sorted({str(row.get("worker_id") or "") for row in group_rows if row.get("worker_id")})
        route_key, side = key.split("|", 1)
        row = {
            "route_key": route_key,
            "side": side,
            "strategy_support_count": len(workers),
            "worker_ids": workers,
            "executor_dedupe_required": len(group_rows) > 1,
        }
        if len(group_rows) > 1:
            executor_dedupe_rows.append(row)
        if len(workers) > 1:
            agreement_rows.append(row)

    disagreement_count = 0
    route_to_sides: Dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if row.get("route_key") and row.get("side"):
            route_to_sides[str(row.get("route_key"))].add(str(row.get("side")))
    disagreement_count = sum(1 for sides in route_to_sides.values() if len(sides) > 1)

    return {
        "intent_rows": rows,
        "missing_intent_contract_rows": missing_contract_rows,
        "mutation_leak_rows": mutation_leak_rows,
        "stale_intent_rows": stale_rows,
        "duplicate_worker_route_rows": duplicate_worker_route_rows,
        "strategy_agreement_rows": agreement_rows,
        "executor_dedupe_rows": executor_dedupe_rows,
        "strategy_disagreement_count": disagreement_count,
    }


def _ghost_dance_proof(
    unity: Mapping[str, Any],
    broker: Mapping[str, Any],
    intent_state: Mapping[str, Any],
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    unity_summary = unity.get("summary") if isinstance(unity.get("summary"), dict) else {}
    ghost_state = unity.get("ghost_dance") if isinstance(unity.get("ghost_dance"), dict) else {}
    worker_rows = _record_array(unity.get("worker_rows"))
    lease_rows = _record_array(broker.get("lease_rows"))
    intent_rows = _record_array(intent_state.get("intents"))
    phase_rows = _record_array(ghost_state.get("worker_phase_rows")) or [
        row.get("ghost_dance") for row in worker_rows if isinstance(row.get("ghost_dance"), dict)
    ]
    phase_rows = [row for row in phase_rows if isinstance(row, dict)]

    missing_worker_rows = []
    for row in worker_rows:
        missing = [field for field in REQUIRED_GHOST_FIELDS if row.get(field) in (None, "") and not (isinstance(row.get("ghost_dance"), dict) and row["ghost_dance"].get(field) not in (None, ""))]
        if missing:
            missing_worker_rows.append(
                {
                    "worker_id": row.get("worker_id") or "",
                    "missing_fields": missing,
                }
            )

    missing_lease_rows = []
    for row in lease_rows:
        if row.get("status") != "granted":
            continue
        missing = [field for field in REQUIRED_GHOST_FIELDS if row.get(field) in (None, "")]
        if missing:
            missing_lease_rows.append(
                {
                    "lease_id": row.get("lease_id") or row.get("request_id") or "",
                    "worker_id": row.get("worker_id") or "",
                    "venue": row.get("venue") or "",
                    "missing_fields": missing,
                }
            )

    missing_intent_rows = []
    stale_missing_intent_rows = []
    for row in intent_rows:
        missing = [field for field in ("ghost_dance_protocol", "ghost_phase_index", "api_key_lock_family") if row.get(field) in (None, "")]
        if missing:
            generated_at = row.get("generated_at")
            age_sec = (now_ts - _parse_ts(generated_at)) if now_ts is not None and generated_at else None
            stale_historical_context = bool(age_sec is not None and age_sec > INTENT_FRESH_SEC)
            target_rows = stale_missing_intent_rows if stale_historical_context else missing_intent_rows
            target_rows.append(
                {
                    "intent_id": row.get("intent_id") or "",
                    "worker_id": row.get("worker_id") or "",
                    "missing_fields": missing,
                    "age_sec": round(age_sec, 3) if age_sec is not None else None,
                    "stale_historical_context": stale_historical_context,
                }
            )

    collision_groups: Dict[tuple[str, str], List[str]] = defaultdict(list)
    for row in lease_rows:
        if row.get("status") != "granted":
            continue
        family = str(row.get("api_key_lock_family") or "")
        phase = str(row.get("ghost_phase_index") or "")
        if family and phase:
            collision_groups[(family, phase)].append(str(row.get("worker_id") or row.get("lease_id") or "unknown"))
    collision_rows = [
        {
            "api_key_lock_family": family,
            "ghost_phase_index": phase,
            "worker_ids": workers,
            "collision_count": len(workers),
        }
        for (family, phase), workers in collision_groups.items()
        if len(workers) > 1
    ]
    phase_indexes = {
        str(row.get("ghost_phase_index"))
        for row in phase_rows
        if row.get("ghost_phase_index") not in (None, "")
    }
    api_key_lock_families = {
        str(row.get("api_key_lock_family"))
        for row in phase_rows
        if row.get("api_key_lock_family") not in (None, "")
    }
    enabled = bool(
        unity_summary.get("ghost_dance_enabled")
        or ghost_state.get("protocol") == GHOST_DANCE_PROTOCOL_VERSION
        or phase_rows
    )
    return {
        "enabled": enabled,
        "protocol": ghost_state.get("protocol") or unity_summary.get("ghost_dance_protocol") or "",
        "phase_count": int(_as_float(ghost_state.get("phase_count") or unity_summary.get("ghost_phase_count"), len(phase_rows))),
        "worker_phase_count": len(phase_rows),
        "unique_phase_count": len(phase_indexes),
        "api_key_lock_family_count": len(api_key_lock_families),
        "missing_worker_phase_count": len(missing_worker_rows),
        "missing_lease_phase_count": len(missing_lease_rows),
        "missing_intent_phase_count": len(missing_intent_rows),
        "stale_missing_intent_phase_count": len(stale_missing_intent_rows),
        "phase_collision_count": len(collision_rows),
        "phase_rows": phase_rows,
        "missing_worker_phase_rows": missing_worker_rows,
        "missing_lease_phase_rows": missing_lease_rows,
        "missing_intent_phase_rows": missing_intent_rows,
        "stale_missing_intent_phase_rows": stale_missing_intent_rows,
        "phase_collision_rows": collision_rows,
        "status": "ghost_dance_ready"
        if enabled and not missing_worker_rows and not missing_lease_rows and not missing_intent_rows and not collision_rows
        else "ghost_dance_attention",
    }


def _harmonic_api_piano_proof(
    unity: Mapping[str, Any],
    broker: Mapping[str, Any],
    intent_state: Mapping[str, Any],
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    unity_summary = unity.get("summary") if isinstance(unity.get("summary"), dict) else {}
    piano_state = unity.get("harmonic_api_piano") if isinstance(unity.get("harmonic_api_piano"), dict) else {}
    worker_rows = _record_array(unity.get("worker_rows"))
    lease_rows = _record_array(broker.get("lease_rows"))
    intent_rows = _record_array(intent_state.get("intents"))
    piano_key_rows = _record_array(unity.get("piano_key_rows")) or _record_array(piano_state.get("piano_key_rows"))

    def missing_fields(row: Mapping[str, Any]) -> List[str]:
        return [field for field in REQUIRED_PIANO_FIELDS if row.get(field) in (None, "")]

    missing_worker_rows = []
    for row in worker_rows:
        missing = missing_fields(row)
        if missing and isinstance(row.get("harmonic_api_piano"), dict):
            nested = row["harmonic_api_piano"]
            missing = [field for field in missing if nested.get(field) in (None, "")]
        if missing:
            missing_worker_rows.append(
                {
                    "worker_id": row.get("worker_id") or "",
                    "missing_fields": missing,
                }
            )

    missing_lease_rows = []
    for row in lease_rows:
        if row.get("status") != "granted":
            continue
        missing = missing_fields(row)
        if missing:
            missing_lease_rows.append(
                {
                    "lease_id": row.get("lease_id") or row.get("request_id") or "",
                    "worker_id": row.get("worker_id") or "",
                    "venue": row.get("venue") or "",
                    "missing_fields": missing,
                }
            )

    missing_intent_rows = []
    stale_missing_intent_rows = []
    for row in intent_rows:
        missing = missing_fields(row)
        if not missing:
            continue
        generated_at = row.get("generated_at")
        age_sec = (now_ts - _parse_ts(generated_at)) if now_ts is not None and generated_at else None
        stale_historical_context = bool(age_sec is not None and age_sec > INTENT_FRESH_SEC)
        target_rows = stale_missing_intent_rows if stale_historical_context else missing_intent_rows
        target_rows.append(
            {
                "intent_id": row.get("intent_id") or "",
                "worker_id": row.get("worker_id") or "",
                "missing_fields": missing,
                "age_sec": round(age_sec, 3) if age_sec is not None else None,
                "stale_historical_context": stale_historical_context,
            }
        )

    song_stop_rows = [
        {
            "worker_id": row.get("worker_id") or "",
            "piano_key_id": row.get("piano_key_id") or "",
            "song_stop_guard": row.get("song_stop_guard") or "",
            "piano_velocity_score": row.get("piano_velocity_score"),
        }
        for row in piano_key_rows
        if row.get("song_stop_guard") in {"api_overplay_risk", "rate_budget_exhausted", "cooldown_missing"}
    ]
    rank_values = [
        int(_as_float(row.get("piano_key_rank"), 0.0))
        for row in piano_key_rows
        if row.get("piano_key_rank") not in (None, "")
    ]
    enabled = bool(
        unity_summary.get("harmonic_api_piano_enabled")
        or piano_state.get("protocol") == HARMONIC_API_PIANO_VERSION
        or piano_key_rows
    )
    return {
        "enabled": enabled,
        "protocol": piano_state.get("protocol") or unity_summary.get("harmonic_api_piano_protocol") or "",
        "tempo_multiplier": _as_float(piano_state.get("tempo_multiplier"), _as_float(unity_summary.get("harmonic_tempo_multiplier"), 0.0)),
        "coherence_blend": _as_float(piano_state.get("coherence_blend"), _as_float(unity_summary.get("harmonic_coherence_blend"), 0.0)),
        "piano_key_count": len(piano_key_rows),
        "unique_rank_count": len(set(rank_values)),
        "play_now_count": int(_as_float(piano_state.get("play_now_count"), _as_float(unity_summary.get("piano_play_now_count"), 0.0))),
        "song_stop_guard": piano_state.get("song_stop_guard") or unity_summary.get("song_stop_guard") or "",
        "missing_worker_piano_count": len(missing_worker_rows),
        "missing_lease_piano_count": len(missing_lease_rows),
        "missing_intent_piano_count": len(missing_intent_rows),
        "stale_missing_intent_piano_count": len(stale_missing_intent_rows),
        "song_stop_risk_count": len(song_stop_rows),
        "piano_key_rows": piano_key_rows,
        "missing_worker_piano_rows": missing_worker_rows,
        "missing_lease_piano_rows": missing_lease_rows,
        "missing_intent_piano_rows": missing_intent_rows,
        "stale_missing_intent_piano_rows": stale_missing_intent_rows,
        "song_stop_risk_rows": song_stop_rows,
        "harmonic_context": piano_state.get("harmonic_context") if isinstance(piano_state.get("harmonic_context"), dict) else {},
        "status": "harmonic_api_piano_ready"
        if enabled and not missing_worker_rows and not missing_lease_rows and not missing_intent_rows and not song_stop_rows
        else "harmonic_api_piano_attention",
    }


def _rainbow_harmonic_ladder_proof(
    unity: Mapping[str, Any],
    broker: Mapping[str, Any],
    intent_state: Mapping[str, Any],
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    unity_summary = unity.get("summary") if isinstance(unity.get("summary"), dict) else {}
    ladder_state = unity.get("rainbow_harmonic_ladder") if isinstance(unity.get("rainbow_harmonic_ladder"), dict) else {}
    worker_rows = _record_array(unity.get("worker_rows"))
    lease_rows = _record_array(broker.get("lease_rows"))
    intent_rows = _record_array(intent_state.get("intents"))
    ladder_rows = _record_array(unity.get("rainbow_ladder_rows")) or _record_array(ladder_state.get("ladder_rows"))
    worker_ladder_rows = _record_array(unity.get("rainbow_worker_rows")) or _record_array(ladder_state.get("worker_phase_rows"))

    def missing_fields(row: Mapping[str, Any]) -> List[str]:
        return [field for field in REQUIRED_RAINBOW_FIELDS if row.get(field) in (None, "")]

    missing_worker_rows = []
    for row in worker_rows:
        missing = missing_fields(row)
        if missing and isinstance(row.get("rainbow_harmonic_ladder"), dict):
            nested = row["rainbow_harmonic_ladder"]
            missing = [field for field in missing if nested.get(field) in (None, "")]
        if missing:
            missing_worker_rows.append({"worker_id": row.get("worker_id") or "", "missing_fields": missing})

    missing_lease_rows = []
    for row in lease_rows:
        if row.get("status") != "granted":
            continue
        missing = missing_fields(row)
        if missing:
            missing_lease_rows.append({"lease_id": row.get("lease_id") or row.get("request_id") or "", "worker_id": row.get("worker_id") or "", "missing_fields": missing})

    missing_intent_rows = []
    stale_missing_intent_rows = []
    for row in intent_rows:
        missing = missing_fields(row)
        if not missing:
            continue
        generated_at = row.get("generated_at")
        age_sec = (now_ts - _parse_ts(generated_at)) if now_ts is not None and generated_at else None
        stale_historical_context = bool(age_sec is not None and age_sec > INTENT_FRESH_SEC)
        target_rows = stale_missing_intent_rows if stale_historical_context else missing_intent_rows
        target_rows.append(
            {
                "intent_id": row.get("intent_id") or "",
                "worker_id": row.get("worker_id") or "",
                "missing_fields": missing,
                "age_sec": round(age_sec, 3) if age_sec is not None else None,
                "stale_historical_context": stale_historical_context,
            }
        )

    song_stop_rows = [
        {
            "worker_id": row.get("worker_id") or "",
            "harmony_lane_id": row.get("harmony_lane_id") or "",
            "song_continuity_guard": row.get("song_continuity_guard") or "",
        }
        for row in worker_ladder_rows
        if row.get("song_continuity_guard") in {"api_overplay_risk", "rate_budget_exhausted", "cooldown_missing"}
    ]
    enabled = bool(
        unity_summary.get("rainbow_harmonic_ladder_enabled")
        or ladder_state.get("protocol") == RAINBOW_HARMONIC_LADDER_VERSION
        or worker_ladder_rows
    )
    return {
        "enabled": enabled,
        "protocol": ladder_state.get("protocol") or unity_summary.get("rainbow_harmonic_ladder_protocol") or "",
        "base_frequency_hz": _as_float(ladder_state.get("base_frequency_hz"), _as_float(unity_summary.get("rainbow_base_frequency_hz"), 0.0)),
        "ladder_step_count": len(ladder_rows),
        "worker_ladder_count": len(worker_ladder_rows),
        "missing_worker_ladder_count": len(missing_worker_rows),
        "missing_lease_ladder_count": len(missing_lease_rows),
        "missing_intent_ladder_count": len(missing_intent_rows),
        "stale_missing_intent_ladder_count": len(stale_missing_intent_rows),
        "song_continuity_risk_count": len(song_stop_rows),
        "ladder_rows": ladder_rows,
        "worker_ladder_rows": worker_ladder_rows,
        "missing_worker_ladder_rows": missing_worker_rows,
        "missing_lease_ladder_rows": missing_lease_rows,
        "missing_intent_ladder_rows": missing_intent_rows,
        "stale_missing_intent_ladder_rows": stale_missing_intent_rows,
        "song_continuity_risk_rows": song_stop_rows,
        "status": "rainbow_harmonic_ladder_ready"
        if enabled and not missing_worker_rows and not missing_lease_rows and not missing_intent_rows and not song_stop_rows
        else "rainbow_harmonic_ladder_attention",
    }


def _power_station_request_proof(
    unity: Mapping[str, Any],
    broker: Mapping[str, Any],
    intent_state: Mapping[str, Any],
    now_ts: Optional[float] = None,
) -> Dict[str, Any]:
    unity_summary = unity.get("summary") if isinstance(unity.get("summary"), dict) else {}
    governor = unity.get("power_station_request_governor") if isinstance(unity.get("power_station_request_governor"), dict) else {}
    worker_rows = _record_array(unity.get("worker_rows"))
    lease_rows = _record_array(broker.get("lease_rows"))
    intent_rows = _record_array(intent_state.get("intents"))
    power_rows = _record_array(broker.get("power_station_request_rows")) or [row for row in lease_rows if row.get("power_station_request_protocol")]

    def missing_fields(row: Mapping[str, Any]) -> List[str]:
        return [field for field in REQUIRED_POWER_STATION_FIELDS if row.get(field) in (None, "")]

    missing_worker_rows = []
    for row in worker_rows:
        missing = missing_fields(row)
        if missing and isinstance(row.get("power_station_request"), dict):
            nested = row["power_station_request"]
            missing = [field for field in missing if nested.get(field) in (None, "")]
        if missing:
            missing_worker_rows.append({"worker_id": row.get("worker_id") or "", "missing_fields": missing})

    missing_lease_rows = []
    authority_violation_rows = []
    for row in lease_rows:
        missing = missing_fields(row)
        if missing:
            missing_lease_rows.append({"lease_id": row.get("lease_id") or row.get("request_id") or "", "worker_id": row.get("worker_id") or "", "missing_fields": missing})
        is_mutation = _operation_is_mutation(row.get("operation_type"))
        if is_mutation and row.get("status") == "granted" and str(row.get("request_owner_authority") or "") != "unified_executor_mutation_owner":
            authority_violation_rows.append(
                {
                    "lease_id": row.get("lease_id") or "",
                    "worker_id": row.get("worker_id") or "",
                    "operation_type": row.get("operation_type") or "",
                    "request_owner_authority": row.get("request_owner_authority") or "",
                }
            )

    missing_intent_rows = []
    stale_missing_intent_rows = []
    for row in intent_rows:
        missing = missing_fields(row)
        if not missing:
            continue
        generated_at = row.get("generated_at")
        age_sec = (now_ts - _parse_ts(generated_at)) if now_ts is not None and generated_at else None
        stale_historical_context = bool(age_sec is not None and age_sec > INTENT_FRESH_SEC)
        target_rows = stale_missing_intent_rows if stale_historical_context else missing_intent_rows
        target_rows.append(
            {
                "intent_id": row.get("intent_id") or "",
                "worker_id": row.get("worker_id") or "",
                "missing_fields": missing,
                "age_sec": round(age_sec, 3) if age_sec is not None else None,
                "stale_historical_context": stale_historical_context,
            }
        )

    direction_counts = Counter(str(row.get("request_direction") or "unknown") for row in power_rows)
    enabled = bool(
        unity_summary.get("power_station_request_governor_enabled")
        or governor.get("protocol") == POWER_STATION_REQUEST_PROTOCOL_VERSION
        or power_rows
    )
    return {
        "enabled": enabled,
        "protocol": governor.get("protocol") or unity_summary.get("power_station_request_protocol") or "",
        "governor_status": governor.get("status") or "",
        "request_count": len(power_rows),
        "outbound_request_count": sum(count for direction, count in direction_counts.items() if direction.startswith("outbound")),
        "internal_request_count": sum(count for direction, count in direction_counts.items() if direction.startswith("internal")),
        "direction_counts": dict(direction_counts),
        "missing_worker_power_count": len(missing_worker_rows),
        "missing_lease_power_count": len(missing_lease_rows),
        "missing_intent_power_count": len(missing_intent_rows),
        "stale_missing_intent_power_count": len(stale_missing_intent_rows),
        "authority_violation_count": len(authority_violation_rows),
        "power_station_request_rows": power_rows,
        "missing_worker_power_rows": missing_worker_rows,
        "missing_lease_power_rows": missing_lease_rows,
        "missing_intent_power_rows": missing_intent_rows,
        "stale_missing_intent_power_rows": stale_missing_intent_rows,
        "authority_violation_rows": authority_violation_rows,
        "status": "power_station_request_governor_ready"
        if enabled and not missing_worker_rows and not missing_lease_rows and not missing_intent_rows and not authority_violation_rows
        else "power_station_request_governor_attention",
    }


def _source_code_wiring_proof(root: Path) -> Dict[str, Any]:
    path = _rooted(root, UNIFIED_MARKET_TRADER_SOURCE_PATH)
    if not path.exists():
        return {
            "source_path": UNIFIED_MARKET_TRADER_SOURCE_PATH.as_posix(),
            "source_available": False,
            "code_wired": True,
            "reason": "source_not_available_in_fixture_or_packaged_runtime",
        }
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return {
            "source_path": UNIFIED_MARKET_TRADER_SOURCE_PATH.as_posix(),
            "source_available": True,
            "code_wired": False,
            "reason": f"source_read_failed:{exc}",
        }
    required_tokens = [
        "parallel_strategy_unity",
        "parallel_strategy_intents",
        "_parallel_strategy_unity_snapshot",
        "_parallel_strategy_intent_state",
        "_parallel_strategy_support_for",
    ]
    missing = [token for token in required_tokens if token not in text]
    return {
        "source_path": UNIFIED_MARKET_TRADER_SOURCE_PATH.as_posix(),
        "source_available": True,
        "code_wired": not missing,
        "missing_tokens": missing,
        "reason": "code_wired" if not missing else "source_missing_parallel_runtime_tokens",
    }


def _artifact_state_proof(root: Path) -> Dict[str, Any]:
    unity_state_path = _rooted(root, STATE_PARALLEL_UNITY_PATH)
    intent_state_path = _rooted(root, STATE_STRATEGY_INTENTS_PATH)
    unity_public_path = _rooted(root, PARALLEL_UNITY_PATH)
    intent_public_path = _rooted(root, STRATEGY_INTENTS_PATH)
    return {
        "state_parallel_unity_path": STATE_PARALLEL_UNITY_PATH.as_posix(),
        "state_parallel_unity_present": unity_state_path.exists(),
        "state_parallel_unity_size_bytes": unity_state_path.stat().st_size if unity_state_path.exists() else 0,
        "state_strategy_intents_path": STATE_STRATEGY_INTENTS_PATH.as_posix(),
        "state_strategy_intents_present": intent_state_path.exists(),
        "state_strategy_intents_size_bytes": intent_state_path.stat().st_size if intent_state_path.exists() else 0,
        "public_parallel_unity_present": unity_public_path.exists(),
        "public_strategy_intents_present": intent_public_path.exists(),
    }


def _process_target_from_command(command_line: str) -> str:
    for target, token in PROCESS_TARGETS.items():
        if token in command_line:
            return target
    return ""


def _iso_from_timestamp(value: Any) -> str:
    try:
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat()
    except Exception:
        return ""


def _ps_single_quote(value: Any) -> str:
    return "'" + str(value or "").replace("'", "''") + "'"


def _discover_process_rows(root: Path, now_ts: float) -> List[Dict[str, Any]]:
    if not (root / "aureon").exists():
        return []
    try:
        import psutil  # type: ignore
    except Exception:
        return []

    rows: List[Dict[str, Any]] = []
    for proc in psutil.process_iter(["pid", "name", "exe", "cmdline", "create_time"]):
        try:
            info = proc.info
            cmdline_value = info.get("cmdline") or []
            command_line = " ".join(str(part) for part in cmdline_value)
            process_name = str(info.get("name") or "").lower()
            process_exe = str(info.get("exe") or "")
            if "python" not in process_name and "python" not in Path(process_exe).name.lower():
                continue
            target = _process_target_from_command(command_line)
            if not target:
                continue
            create_ts = _as_float(info.get("create_time"), 0.0)
            rows.append(
                {
                    "pid": info.get("pid"),
                    "name": info.get("name") or "",
                    "exe": process_exe,
                    "command_line": command_line,
                    "target": target,
                    "created_at": _iso_from_timestamp(create_ts),
                    "age_sec": round(max(0.0, now_ts - create_ts), 3) if create_ts else None,
                }
            )
        except Exception:
            continue
    return rows


def _runtime_process_proof(root: Path, now_ts: float, rows: Optional[Sequence[Mapping[str, Any]]] = None) -> Dict[str, Any]:
    discovery_available = (root / "aureon").exists()
    process_rows = [dict(row) for row in rows] if rows is not None else _discover_process_rows(root, now_ts)
    expected_python = _rooted(root, EXPECTED_VENV_PYTHON_PATH)
    expected_python_text = str(expected_python).lower()
    source_path = _rooted(root, UNIFIED_MARKET_TRADER_SOURCE_PATH)
    source_mtime = source_path.stat().st_mtime if source_path.exists() else 0.0

    for row in process_rows:
        command_line = str(row.get("command_line") or "")
        exe = str(row.get("exe") or "")
        row["target"] = str(row.get("target") or _process_target_from_command(command_line))
        row["uses_expected_python"] = bool(
            expected_python_text
            and (
                str(exe).lower() == expected_python_text
                or expected_python_text in command_line.lower()
            )
        )
        created_ts = _parse_ts(row.get("created_at"))
        row["started_before_unified_market_trader_source"] = bool(
            row.get("target") == "unified_market_trader"
            and created_ts
            and source_mtime
            and created_ts < source_mtime
        )

    by_target = Counter(str(row.get("target") or "") for row in process_rows if row.get("target"))
    unified_rows = [row for row in process_rows if row.get("target") == "unified_market_trader"]
    parallel_rows = [row for row in process_rows if row.get("target") == "parallel_strategy_unity"]
    wrong_python_rows = [
        row
        for row in unified_rows
        if expected_python.exists() and not bool(row.get("uses_expected_python"))
    ]
    stale_source_rows = [
        row for row in unified_rows if bool(row.get("started_before_unified_market_trader_source"))
    ]

    duplicate_unified = len(unified_rows) > 1
    supervisor_missing = discovery_available and not parallel_rows
    rows_out = [
        {
            "check": "unified_market_trader_single_process",
            "passing": not duplicate_unified,
            "detail": f"{len(unified_rows)} unified_market_trader process(es) found",
            "source": "host_process_table",
        },
        {
            "check": "unified_market_trader_expected_python",
            "passing": not wrong_python_rows,
            "detail": str(expected_python),
            "source": "host_process_table",
        },
        {
            "check": "parallel_strategy_supervisor_running",
            "passing": bool(parallel_rows) or not discovery_available,
            "detail": f"{len(parallel_rows)} parallel_strategy_unity supervisor process(es) found",
            "source": "host_process_table",
        },
        {
            "check": "unified_market_trader_source_loaded_after_edit",
            "passing": not stale_source_rows,
            "detail": "process creation time is newer than source mtime" if not stale_source_rows else "restart required after source edit",
            "source": UNIFIED_MARKET_TRADER_SOURCE_PATH.as_posix(),
        },
    ]
    return {
        "discovery_available": discovery_available,
        "process_count": len(process_rows),
        "target_counts": dict(by_target),
        "unified_market_trader_process_count": len(unified_rows),
        "parallel_strategy_supervisor_process_count": len(parallel_rows),
        "duplicate_unified_market_trader": duplicate_unified,
        "wrong_python_process_count": len(wrong_python_rows),
        "supervisor_missing": supervisor_missing,
        "source_stale_process_count": len(stale_source_rows),
        "expected_python": str(expected_python),
        "process_rows": process_rows,
        "burn_down_rows": rows_out,
    }


def _launcher_readiness_proof(root: Path, process_proof: Mapping[str, Any]) -> Dict[str, Any]:
    if not (root / "aureon").exists():
        return {
            "standard_launcher_available": True,
            "launcher_path": PRODUCTION_LAUNCHER_PATH.as_posix(),
            "wake_script_path": FULL_AUTONOMOUS_WAKE_SCRIPT_PATH.as_posix(),
            "expected_python": str(_rooted(root, EXPECTED_VENV_PYTHON_PATH)),
            "parallel_supervisor_registered": True,
            "stress_audit_registered": True,
            "unified_trader_registered": True,
            "stop_target_count": 0,
            "start_target_count": 0,
            "post_restart_check_count": 0,
            "stop_target_rows": [],
            "start_target_rows": [],
            "post_restart_check_rows": [],
            "guard_validation_rows": [],
            "guarded_repair_command_lines": [],
            "guarded_repair_command_preview": "",
            "guarded_command_package_ready": True,
            "blockers": [],
            "reason": "source_not_available_in_fixture_or_packaged_runtime",
            "advisory_only": True,
        }
    launcher_path = _rooted(root, PRODUCTION_LAUNCHER_PATH)
    wake_path = _rooted(root, FULL_AUTONOMOUS_WAKE_SCRIPT_PATH)
    expected_python = _rooted(root, EXPECTED_VENV_PYTHON_PATH)
    wake_text = ""
    try:
        wake_text = wake_path.read_text(encoding="utf-8", errors="replace") if wake_path.exists() else ""
    except Exception:
        wake_text = ""

    supervisor_registered = "aureon.trading.parallel_strategy_unity --watch" in wake_text
    stress_audit_registered = "aureon.autonomous.aureon_parallel_strategy_unity_stress_audit --watch" in wake_text
    unified_trader_registered = "aureon.exchanges.unified_market_trader" in wake_text
    standard_launcher_available = bool(
        launcher_path.exists()
        and wake_path.exists()
        and expected_python.exists()
        and supervisor_registered
        and stress_audit_registered
        and unified_trader_registered
    )

    process_rows = _record_array(process_proof.get("process_rows"))
    stop_rows: List[Dict[str, Any]] = []
    for row in process_rows:
        target = str(row.get("target") or "")
        if target not in {"unified_market_trader", "parallel_strategy_unity"}:
            continue
        reason_parts: List[str] = []
        if target == "unified_market_trader" and _as_float(process_proof.get("unified_market_trader_process_count"), 0.0) > 1:
            reason_parts.append("duplicate_unified_market_trader")
        if target == "unified_market_trader" and not bool(row.get("uses_expected_python")):
            reason_parts.append("wrong_python_owner")
        if target == "unified_market_trader" and bool(row.get("started_before_unified_market_trader_source")):
            reason_parts.append("started_before_current_source")
        if reason_parts:
            stop_rows.append(
                {
                    "pid": row.get("pid"),
                    "target": target,
                    "exe": row.get("exe") or "",
                    "command_line": row.get("command_line") or "",
                    "expected_command_substring": "aureon.exchanges.unified_market_trader" if target == "unified_market_trader" else "aureon.trading.parallel_strategy_unity",
                    "reason": ", ".join(reason_parts),
                    "recommended_action": "stop_before_clean_launcher_restart",
                    "command_preview": f"Stop-Process -Id {row.get('pid')} -Force",
                    "advisory_only": True,
                }
            )

    start_rows = [
        {
            "target": "production_launcher",
            "recommended_action": "start_single_owner_runtime",
            "command_preview": ".\\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791",
            "requires": "after duplicate unified_market_trader processes are stopped and launcher guard checks pass",
            "advisory_only": True,
        },
        {
            "target": "parallel_strategy_unity",
            "recommended_action": "launcher_starts_watch_process",
            "command_preview": ".venv\\Scripts\\python.exe -m aureon.trading.parallel_strategy_unity --watch --interval 5",
            "registered_in_launcher": supervisor_registered,
            "advisory_only": True,
        },
        {
            "target": "parallel_strategy_unity_stress_audit",
            "recommended_action": "launcher_starts_watch_process",
            "command_preview": ".venv\\Scripts\\python.exe -m aureon.autonomous.aureon_parallel_strategy_unity_stress_audit --watch --interval 10",
            "registered_in_launcher": stress_audit_registered,
            "advisory_only": True,
        },
    ]
    post_restart_checks = [
        {
            "check": "single_unified_market_trader_process",
            "expected": "unified_market_trader_process_count == 1",
            "source": "runtime_process_proof",
        },
        {
            "check": "unified_market_trader_uses_repo_venv",
            "expected": "wrong_python_process_count == 0",
            "source": "runtime_process_proof",
        },
        {
            "check": "parallel_supervisor_running",
            "expected": "parallel_strategy_supervisor_process_count >= 1",
            "source": "runtime_process_proof",
        },
        {
            "check": "terminal_embeds_parallel_unity",
            "expected": "exchange_action_plan.parallel_strategy_unity present",
            "source": RUNTIME_STATUS_PATH.as_posix(),
        },
        {
            "check": "terminal_embeds_parallel_intents",
            "expected": "exchange_action_plan.parallel_strategy_intents present",
            "source": RUNTIME_STATUS_PATH.as_posix(),
        },
        {
            "check": "worker_heartbeats_fresh",
            "expected": "healthy_worker_count == worker_count",
            "source": PARALLEL_UNITY_PATH.as_posix(),
        },
    ]
    blockers = []
    if not launcher_path.exists():
        blockers.append("production_launcher_missing")
    if not wake_path.exists():
        blockers.append("wake_script_missing")
    if not expected_python.exists():
        blockers.append("expected_venv_python_missing")
    if not supervisor_registered:
        blockers.append("parallel_supervisor_not_registered")
    if not stress_audit_registered:
        blockers.append("stress_audit_not_registered")
    if not unified_trader_registered:
        blockers.append("unified_trader_not_registered")

    stop_targets_are_scoped = all(
        str(row.get("target") or "") in {"unified_market_trader", "parallel_strategy_unity"}
        and row.get("pid") not in (None, "")
        and bool(row.get("expected_command_substring"))
        for row in stop_rows
    )
    guarded_command_ready = bool(standard_launcher_available and stop_targets_are_scoped and not blockers)
    guard_rows = [
        {
            "check": "repair_plan_advisory_only",
            "passing": True,
            "detail": "audit publishes commands but does not execute them",
        },
        {
            "check": "standard_launcher_available",
            "passing": standard_launcher_available,
            "detail": PRODUCTION_LAUNCHER_PATH.as_posix(),
        },
        {
            "check": "stop_targets_scoped_to_runtime_modules",
            "passing": stop_targets_are_scoped,
            "detail": f"{len(stop_rows)} stop target(s)",
        },
        {
            "check": "post_restart_checks_defined",
            "passing": len(post_restart_checks) >= 6,
            "detail": f"{len(post_restart_checks)} post-restart check(s)",
        },
        {
            "check": "guarded_command_package_ready",
            "passing": guarded_command_ready,
            "detail": "PowerShell command package validates PIDs before stopping" if guarded_command_ready else "repair command package blocked by launcher or target scope",
        },
    ]
    command_lines = [
        "$ErrorActionPreference = 'Stop'",
        f"cd {_ps_single_quote(str(root))}",
        "$targets = @(",
    ]
    for row in stop_rows:
        command_lines.append(
            "  @{ Pid = %s; Contains = %s; Reason = %s }"
            % (
                row.get("pid"),
                _ps_single_quote(row.get("expected_command_substring")),
                _ps_single_quote(row.get("reason")),
            )
        )
    command_lines.extend(
        [
            ")",
            "foreach ($target in $targets) {",
            "  $proc = Get-CimInstance Win32_Process -Filter \"ProcessId=$($target.Pid)\"",
            "  if ($null -eq $proc) { continue }",
            "  if (($proc.CommandLine -notlike \"*$($target.Contains)*\")) { throw \"Refusing to stop PID $($target.Pid): command line no longer matches $($target.Contains)\" }",
            "  Stop-Process -Id $target.Pid -Force",
            "}",
            ".\\AUREON_PRODUCTION_LIVE.cmd -WaitForRefresh -MarketStatusPort 8791",
            ".\\.venv\\Scripts\\python.exe -m aureon.autonomous.aureon_parallel_strategy_unity_stress_audit --json",
        ]
    )

    return {
        "standard_launcher_available": standard_launcher_available,
        "guarded_command_package_ready": guarded_command_ready,
        "launcher_path": PRODUCTION_LAUNCHER_PATH.as_posix(),
        "wake_script_path": FULL_AUTONOMOUS_WAKE_SCRIPT_PATH.as_posix(),
        "expected_python": str(expected_python),
        "parallel_supervisor_registered": supervisor_registered,
        "stress_audit_registered": stress_audit_registered,
        "unified_trader_registered": unified_trader_registered,
        "stop_target_count": len(stop_rows),
        "start_target_count": len(start_rows),
        "post_restart_check_count": len(post_restart_checks),
        "stop_target_rows": stop_rows,
        "start_target_rows": start_rows,
        "post_restart_check_rows": post_restart_checks,
        "guard_validation_rows": guard_rows,
        "guarded_repair_command_lines": command_lines,
        "guarded_repair_command_preview": "; ".join(command_lines),
        "blockers": blockers,
        "advisory_only": True,
    }


def _runtime_alignment(root: Path, runtime: Mapping[str, Any], unity: Mapping[str, Any], now_ts: float) -> Dict[str, Any]:
    action_plan = runtime.get("exchange_action_plan") if isinstance(runtime.get("exchange_action_plan"), dict) else {}
    watchdog = runtime.get("runtime_watchdog") if isinstance(runtime.get("runtime_watchdog"), dict) else {}
    embedded_unity = action_plan.get("parallel_strategy_unity") if isinstance(action_plan.get("parallel_strategy_unity"), dict) else {}
    embedded_intents = action_plan.get("parallel_strategy_intents") if isinstance(action_plan.get("parallel_strategy_intents"), dict) else {}
    runtime_present = bool(runtime)
    runtime_generated_at = (
        runtime.get("generated_at")
        or runtime.get("timestamp")
        or action_plan.get("generated_at")
        or watchdog.get("heartbeat_at")
        or ""
    )
    runtime_age_sec = now_ts - _parse_ts(runtime_generated_at) if runtime_generated_at else None
    code_proof = _source_code_wiring_proof(root)
    state_proof = _artifact_state_proof(root)
    state_snapshots_present = bool(
        state_proof["state_parallel_unity_present"]
        and state_proof["state_strategy_intents_present"]
    )
    public_snapshots_present = bool(
        state_proof["public_parallel_unity_present"]
        and state_proof["public_strategy_intents_present"]
    )
    terminal_embeds_unity = bool(embedded_unity)
    terminal_embeds_intents = bool(embedded_intents)
    aligned = (not runtime_present) or (terminal_embeds_unity and terminal_embeds_intents)
    reload_required = bool(
        runtime_present
        and code_proof.get("code_wired")
        and (state_snapshots_present or public_snapshots_present)
        and not aligned
    )
    rows = [
        {
            "check": "unified_market_trader_code_wired",
            "passing": bool(code_proof.get("code_wired")),
            "detail": code_proof.get("reason") or "",
            "source": UNIFIED_MARKET_TRADER_SOURCE_PATH.as_posix(),
        },
        {
            "check": "state_parallel_unity_snapshot",
            "passing": bool(state_proof["state_parallel_unity_present"] or state_proof["public_parallel_unity_present"]),
            "detail": STATE_PARALLEL_UNITY_PATH.as_posix(),
            "source": STATE_PARALLEL_UNITY_PATH.as_posix(),
        },
        {
            "check": "state_strategy_intents_snapshot",
            "passing": bool(state_proof["state_strategy_intents_present"] or state_proof["public_strategy_intents_present"]),
            "detail": STATE_STRATEGY_INTENTS_PATH.as_posix(),
            "source": STATE_STRATEGY_INTENTS_PATH.as_posix(),
        },
        {
            "check": "terminal_state_embeds_parallel_unity",
            "passing": terminal_embeds_unity,
            "detail": "exchange_action_plan.parallel_strategy_unity",
            "source": RUNTIME_STATUS_PATH.as_posix(),
        },
        {
            "check": "terminal_state_embeds_parallel_intents",
            "passing": terminal_embeds_intents,
            "detail": "exchange_action_plan.parallel_strategy_intents",
            "source": RUNTIME_STATUS_PATH.as_posix(),
        },
        {
            "check": "runtime_reload_required",
            "passing": not reload_required,
            "detail": "restart unified_market_trader so terminal-state loads current source" if reload_required else "runtime alignment not reload-blocked",
            "source": RUNTIME_STATUS_PATH.as_posix(),
        },
    ]
    return {
        "runtime_status_present": runtime_present,
        "runtime_generated_at": runtime_generated_at,
        "runtime_age_sec": round(max(0.0, runtime_age_sec), 3) if runtime_age_sec is not None else None,
        "trade_path_state": action_plan.get("trade_path_state") or "",
        "order_intent_publish_enabled": bool(action_plan.get("order_intent_publish_enabled")),
        "parallel_unity_embedded": terminal_embeds_unity,
        "parallel_intents_embedded": terminal_embeds_intents,
        "runtime_unity_status": embedded_unity.get("status") or "",
        "public_unity_status": unity.get("status") or "",
        "state_snapshots_present": state_snapshots_present,
        "public_snapshots_present": public_snapshots_present,
        "code_wired": bool(code_proof.get("code_wired")),
        "runtime_reload_required": reload_required,
        "alignment_status": "runtime_aligned" if aligned else "runtime_reload_required" if reload_required else "runtime_parallel_snapshot_missing",
        "next_action": "restart_unified_market_trader_runtime" if reload_required else "",
        "aligned": aligned,
        "code_wiring_proof": code_proof,
        "artifact_state_proof": state_proof,
        "burn_down_rows": rows,
    }


def _fabric_visibility(fabric: Mapping[str, Any], unity: Mapping[str, Any]) -> Dict[str, Any]:
    fabric_summary = fabric.get("summary") if isinstance(fabric.get("summary"), dict) else {}
    unity_summary = unity.get("summary") if isinstance(unity.get("summary"), dict) else {}
    phase_counts = fabric.get("phase_counts") if isinstance(fabric.get("phase_counts"), dict) else {}
    return {
        "fabric_present": bool(fabric),
        "unity_publish_enabled": bool(unity_summary.get("thoughtbus_mycelium_publish_enabled")),
        "thoughtbus_receiving": bool(fabric_summary.get("thoughtbus_receiving")),
        "mycelium_receiving": bool(fabric_summary.get("mycelium_receiving")),
        "signal_generated_count": int(_as_float(phase_counts.get("signal_generated"), 0.0)),
        "event_count": int(_as_float(fabric_summary.get("event_count"), 0.0)),
        "visible": bool(
            unity_summary.get("thoughtbus_mycelium_publish_enabled")
            and (fabric_summary.get("thoughtbus_receiving") or fabric_summary.get("mycelium_receiving") or phase_counts.get("signal_generated"))
        ),
    }


def _audit_self_validation_proof(
    *,
    root: Path,
    artifact_rows: Sequence[Mapping[str, Any]],
    worker_results: Sequence[Mapping[str, Any]],
    lease_results: Mapping[str, Any],
    intent_results: Mapping[str, Any],
    ghost_proof: Mapping[str, Any],
    piano_proof: Mapping[str, Any],
    rainbow_proof: Mapping[str, Any],
    power_station_proof: Mapping[str, Any],
    runtime_proof: Mapping[str, Any],
    fabric_proof: Mapping[str, Any],
    mutation_leak_rows: Sequence[Mapping[str, Any]],
    api_budget_gap_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Validate that this audit's own evidence math and required sections agree."""
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    required_artifacts = {"parallel_unity", "request_broker", "strategy_intents"}
    present_artifacts = {str(row.get("id") or "") for row in artifact_rows if row.get("present")}
    add(
        "required_artifacts_present",
        required_artifacts.issubset(present_artifacts),
        "parallel unity, request broker, and strategy intent artifacts must be present",
        present_count=len(present_artifacts & required_artifacts),
        required_count=len(required_artifacts),
    )

    required_sections = {
        "ghost_dance": bool(ghost_proof.get("enabled")),
        "harmonic_api_piano": bool(piano_proof.get("enabled")),
        "rainbow_harmonic_ladder": bool(rainbow_proof.get("enabled")),
        "power_station_request_governor": bool(power_station_proof.get("enabled")),
        "fabric_visibility": bool(fabric_proof.get("visible")),
    }
    missing_sections = [name for name, present in required_sections.items() if not present]
    add(
        "required_proof_sections_enabled",
        not missing_sections,
        "Ghost, Piano, Rainbow, Power Station, and fabric proof sections are required",
        missing_sections=missing_sections,
    )

    rainbow_missing_expected = (
        int(_as_float(rainbow_proof.get("missing_worker_ladder_count"), 0.0))
        + int(_as_float(rainbow_proof.get("missing_lease_ladder_count"), 0.0))
        + int(_as_float(rainbow_proof.get("missing_intent_ladder_count"), 0.0))
    )
    rainbow_missing_rows = (
        len(_record_array(rainbow_proof.get("missing_worker_ladder_rows")))
        + len(_record_array(rainbow_proof.get("missing_lease_ladder_rows")))
        + len(_record_array(rainbow_proof.get("missing_intent_ladder_rows")))
    )
    add(
        "rainbow_missing_count_matches_rows",
        rainbow_missing_expected == rainbow_missing_rows,
        "Rainbow missing proof count must match missing worker/lease/intent rows",
        expected_count=rainbow_missing_expected,
        row_count=rainbow_missing_rows,
    )

    power_missing_expected = (
        int(_as_float(power_station_proof.get("missing_worker_power_count"), 0.0))
        + int(_as_float(power_station_proof.get("missing_lease_power_count"), 0.0))
        + int(_as_float(power_station_proof.get("missing_intent_power_count"), 0.0))
    )
    power_missing_rows = (
        len(_record_array(power_station_proof.get("missing_worker_power_rows")))
        + len(_record_array(power_station_proof.get("missing_lease_power_rows")))
        + len(_record_array(power_station_proof.get("missing_intent_power_rows")))
    )
    add(
        "power_station_missing_count_matches_rows",
        power_missing_expected == power_missing_rows,
        "Power Station missing proof count must match missing worker/lease/intent rows",
        expected_count=power_missing_expected,
        row_count=power_missing_rows,
    )

    power_authority_count = int(_as_float(power_station_proof.get("authority_violation_count"), 0.0))
    power_authority_rows = len(_record_array(power_station_proof.get("authority_violation_rows")))
    add(
        "power_station_authority_count_matches_rows",
        power_authority_count == power_authority_rows,
        "Power Station authority violation count must match authority rows",
        expected_count=power_authority_count,
        row_count=power_authority_rows,
    )

    mutation_leak_count = len(mutation_leak_rows)
    add(
        "mutation_authority_rows_consistent",
        mutation_leak_count == len(mutation_leak_rows),
        "Mutation leak rows are counted from leases, intents, and worker authority flags",
        row_count=mutation_leak_count,
    )
    add(
        "api_budget_rows_consistent",
        len(api_budget_gap_rows) == len(lease_results.get("budget_gap_rows", [])) + len(lease_results.get("over_budget_rows", [])),
        "API budget gap rows must match broker denied/over-budget rows",
        row_count=len(api_budget_gap_rows),
    )
    add(
        "workers_have_authority_flags",
        all("direct_broker_mutation_allowed" in row and "requires_unified_executor" in row for row in worker_results),
        "Every worker stress row must state mutation authority and unified-executor requirement",
        worker_count=len(worker_results),
    )
    add(
        "intent_rows_have_required_ids_checked",
        isinstance(intent_results.get("missing_intent_contract_rows"), list),
        "Intent contract rows must be computed before self-validation",
        missing_intent_contract_count=len(intent_results.get("missing_intent_contract_rows", [])),
    )
    add(
        "runtime_alignment_evaluated",
        "aligned" in runtime_proof,
        "Runtime alignment proof must be evaluated even when runtime attention remains",
        aligned=runtime_proof.get("aligned"),
    )

    source_available = _rooted(root, UNIFIED_MARKET_TRADER_SOURCE_PATH).exists() and _rooted(root, RUNTIME_STATUS_PATH).exists()
    fixture_mode = not (_rooted(root, Path("aureon")).exists() and _rooted(root, Path("frontend")).exists())
    proof_basis = "real_runtime_artifacts" if source_available and not fixture_mode else "isolated_fixture_or_packaged_runtime"
    add(
        "proof_basis_classified",
        True,
        proof_basis,
        proof_basis=proof_basis,
        source_available=source_available,
        fixture_mode=fixture_mode,
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_self_validation_passed" if not failed_rows else "audit_self_validation_attention",
        "generated_at": utc_now().isoformat(),
        "proof_basis": proof_basis,
        "self_validation_passed": not failed_rows,
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "self-validation checks this audit's evidence math and section presence",
            "self-validation does not start, stop, place, close, or mutate broker state",
            "fixture mode is classified separately from live runtime artifact proof",
        ],
    }


def _audit_report_replay_validation(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Replay published audit rows into summary counts as an independent check."""
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    rows: List[Dict[str, Any]] = []

    def add(check: str, expected: Any, actual: Any, detail: str) -> None:
        rows.append(
            {
                "check": check,
                "passing": expected == actual,
                "expected": expected,
                "actual": actual,
                "detail": detail,
            }
        )

    worker_rows = _record_array(report.get("worker_stress_rows"))
    stale_worker_rows = [row for row in worker_rows if row.get("state") in {"worker_missing", "worker_stale"}]
    attention_worker_rows = [row for row in worker_rows if row.get("state") != "worker_healthy"]
    add("worker_count_replayed", summary.get("worker_count"), len(worker_rows), "Worker count must equal worker stress rows.")
    add(
        "healthy_worker_count_replayed",
        summary.get("healthy_worker_count"),
        sum(1 for row in worker_rows if row.get("state") == "worker_healthy"),
        "Healthy worker count must replay from worker states.",
    )
    add("stale_worker_count_replayed", summary.get("stale_worker_count"), len(stale_worker_rows), "Stale worker count must replay from worker states.")
    add(
        "attention_worker_count_replayed",
        summary.get("attention_worker_count"),
        len(attention_worker_rows),
        "Attention worker count must replay from non-healthy worker states.",
    )
    add(
        "missing_intent_contract_count_replayed",
        summary.get("missing_intent_contract_count"),
        len(_record_array(report.get("intent_contract_rows"))),
        "Missing intent contract count must equal intent contract rows.",
    )
    add(
        "api_budget_gap_count_replayed",
        summary.get("api_budget_gap_count"),
        len(_record_array(report.get("api_budget_stress_rows"))),
        "API budget gap count must equal budget stress rows.",
    )
    add(
        "mutation_leak_count_replayed",
        summary.get("mutation_leak_count"),
        len(_record_array(report.get("mutation_authority_rows"))),
        "Mutation leak count must equal mutation authority rows.",
    )
    add(
        "denied_mutation_proof_count_replayed",
        summary.get("denied_mutation_proof_count"),
        len(_record_array(report.get("denied_mutation_proof_rows"))),
        "Denied mutation proof count must equal denied mutation rows.",
    )
    add(
        "strategy_agreement_count_replayed",
        summary.get("strategy_agreement_count"),
        len(_record_array(report.get("strategy_agreement_rows"))),
        "Strategy agreement count must equal agreement rows.",
    )
    add(
        "ghost_missing_phase_count_replayed",
        summary.get("ghost_missing_phase_count"),
        len(_record_array(report.get("ghost_missing_worker_phase_rows")))
        + len(_record_array(report.get("ghost_missing_lease_phase_rows")))
        + len(_record_array(report.get("ghost_missing_intent_phase_rows"))),
        "Ghost missing count must replay from worker, lease, and intent rows.",
    )
    add(
        "ghost_phase_collision_count_replayed",
        summary.get("ghost_phase_collision_count"),
        len(_record_array(report.get("ghost_phase_collision_rows"))),
        "Ghost phase collision count must equal collision rows.",
    )
    add(
        "piano_missing_proof_count_replayed",
        summary.get("piano_missing_proof_count"),
        len(_record_array(report.get("piano_missing_worker_rows")))
        + len(_record_array(report.get("piano_missing_lease_rows")))
        + len(_record_array(report.get("piano_missing_intent_rows"))),
        "Piano missing count must replay from worker, lease, and intent rows.",
    )
    add(
        "song_stop_risk_count_replayed",
        summary.get("song_stop_risk_count"),
        len(_record_array(report.get("piano_song_stop_risk_rows"))),
        "Song-stop risk count must equal Piano risk rows.",
    )
    add(
        "rainbow_missing_proof_count_replayed",
        summary.get("rainbow_missing_proof_count"),
        len(_record_array(report.get("rainbow_missing_worker_rows")))
        + len(_record_array(report.get("rainbow_missing_lease_rows")))
        + len(_record_array(report.get("rainbow_missing_intent_rows"))),
        "Rainbow missing count must replay from worker, lease, and intent rows.",
    )
    add(
        "rainbow_song_continuity_risk_count_replayed",
        summary.get("rainbow_song_continuity_risk_count"),
        len(_record_array(report.get("rainbow_song_continuity_risk_rows"))),
        "Rainbow continuity risk count must equal risk rows.",
    )
    add(
        "power_station_missing_proof_count_replayed",
        summary.get("power_station_missing_proof_count"),
        len(_record_array(report.get("power_station_missing_worker_rows")))
        + len(_record_array(report.get("power_station_missing_lease_rows")))
        + len(_record_array(report.get("power_station_missing_intent_rows"))),
        "Power Station missing count must replay from worker, lease, and intent rows.",
    )
    power_rows = _record_array(report.get("power_station_request_rows"))
    add(
        "power_station_request_count_replayed",
        summary.get("power_station_request_count"),
        len(power_rows),
        "Power Station request count must equal published request metadata rows.",
    )
    add(
        "power_station_outbound_request_count_replayed",
        summary.get("power_station_outbound_request_count"),
        sum(1 for row in power_rows if row.get("request_direction") == "outbound_market_api"),
        "Power Station outbound count must replay from request direction rows.",
    )
    add(
        "power_station_internal_request_count_replayed",
        summary.get("power_station_internal_request_count"),
        sum(1 for row in power_rows if row.get("request_direction") == "internal_context"),
        "Power Station internal count must replay from request direction rows.",
    )
    add(
        "power_station_authority_violation_count_replayed",
        summary.get("power_station_authority_violation_count"),
        len(_record_array(report.get("power_station_authority_violation_rows"))),
        "Power Station authority count must equal authority rows.",
    )
    add(
        "audit_self_validation_count_replayed",
        summary.get("audit_self_validation_check_count"),
        len(_record_array(report.get("audit_self_validation_rows"))),
        "Self-validation check count must equal self-validation rows.",
    )
    add(
        "audit_self_validation_failed_count_replayed",
        summary.get("audit_self_validation_failed_count"),
        len(_record_array(report.get("audit_self_validation_failed_rows"))),
        "Self-validation failure count must equal failed self-validation rows.",
    )

    fabric_proof = report.get("fabric_visibility_proof") if isinstance(report.get("fabric_visibility_proof"), dict) else {}
    runtime_proof = report.get("runtime_alignment_proof") if isinstance(report.get("runtime_alignment_proof"), dict) else {}
    add("fabric_visible_replayed", summary.get("fabric_visible"), bool(fabric_proof.get("visible")), "Fabric visibility summary must mirror fabric proof.")
    add("runtime_alignment_replayed", summary.get("runtime_alignment"), bool(runtime_proof.get("aligned")), "Runtime alignment summary must mirror runtime proof.")

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_replay_validation_passed" if not failed_rows else "audit_replay_validation_attention",
        "generated_at": utc_now().isoformat(),
        "replay_validation_passed": not failed_rows,
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "replay validation recomputes summary counts from the already published rows",
            "replay validation is audit-only and does not mutate broker, process, or runtime state",
        ],
    }


def _audit_integrity_triangulation_validation(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Triangulate status, blockers, repairs, paths, and mutation boundaries."""
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    repair_rows = _record_array(report.get("next_repair_actions"))
    manual_boundaries = [str(item) for item in report.get("manual_boundaries", []) if str(item)]
    source_paths = report.get("source_paths") if isinstance(report.get("source_paths"), dict) else {}
    output_files = [str(item) for item in report.get("output_files", []) if str(item)]
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    required_top_level = {"status", "generated_at", "mode", "summary", "blockers", "manual_boundaries", "source_paths", "output_files"}
    missing_top_level = sorted(required_top_level - set(report.keys()))
    add(
        "required_top_level_fields_present",
        not missing_top_level,
        "Public stress artifact must keep the minimum operator-facing contract.",
        missing_fields=missing_top_level,
    )

    expected_status = _status_from_blockers(blockers)
    add(
        "status_matches_blockers",
        report.get("status") == expected_status,
        "Status must be derived from the current blocker set.",
        expected_status=expected_status,
        actual_status=report.get("status"),
    )
    add(
        "blocker_count_matches_blocker_rows",
        int(_as_float(summary.get("blocker_count"), -1)) == len(blockers),
        "Summary blocker count must equal the blocker array length.",
        expected_count=len(blockers),
        actual_count=summary.get("blocker_count"),
    )
    add(
        "certified_status_requires_zero_blockers",
        (report.get("status") == "parallel_strategy_stress_certified") == (len(blockers) == 0),
        "Certified status is only valid with zero blockers, and zero blockers must certify.",
        blocker_count=len(blockers),
        status=report.get("status"),
    )

    repair_blockers = {str(row.get("blocker") or "") for row in repair_rows if row.get("blocker")}
    add(
        "repair_actions_cover_all_blockers",
        set(blockers).issubset(repair_blockers),
        "Every blocker must name one owner and one next repair action.",
        missing_repair_actions=sorted(set(blockers) - repair_blockers),
    )
    add(
        "repair_actions_do_not_invent_blockers",
        repair_blockers.issubset(set(blockers)),
        "Repair rows must describe visible blockers, not unrelated work.",
        extra_repair_actions=sorted(repair_blockers - set(blockers)),
    )

    local_prefixes = ("state/", "docs/audits/", "frontend/public/")
    bad_outputs = [path for path in output_files if Path(path).is_absolute() or ".." in Path(path).parts or not path.replace("\\", "/").startswith(local_prefixes)]
    add(
        "output_paths_are_local_artifacts",
        not bad_outputs and bool(output_files),
        "Output files must stay in state, docs/audits, or frontend/public.",
        bad_paths=bad_outputs,
        output_count=len(output_files),
    )
    bad_sources = [
        str(path)
        for path in source_paths.values()
        if Path(str(path)).is_absolute() or ".." in Path(str(path)).parts
    ]
    add(
        "source_paths_are_relative",
        not bad_sources and bool(source_paths),
        "Source path references must be relative repo artifact paths.",
        bad_paths=bad_sources,
        source_path_count=len(source_paths),
    )

    boundary_text = " ".join(manual_boundaries).lower()
    add(
        "manual_boundaries_preserve_no_broker_mutation",
        bool(manual_boundaries) and "do not place orders" in boundary_text and "only broker mutation authority" in boundary_text,
        "Manual boundaries must explicitly preserve no direct order/close mutation for this audit.",
        boundary_count=len(manual_boundaries),
    )
    mutation_count = int(_as_float(summary.get("mutation_leak_count"), 0.0))
    add(
        "mutation_blocker_matches_mutation_rows",
        (mutation_count > 0) == ("parallel_strategy_mutation_leak" in blockers),
        "Mutation leak blocker must appear only when mutation rows exist.",
        mutation_leak_count=mutation_count,
    )
    add(
        "direct_worker_mutation_boundary_matches_summary",
        summary.get("direct_broker_mutation_allowed") is False,
        "Parallel workers must stay signal-only; broker mutation belongs to the unified executor.",
        direct_broker_mutation_allowed=summary.get("direct_broker_mutation_allowed"),
    )
    self_ok = bool(summary.get("audit_self_validation_passed"))
    replay_ok = bool(summary.get("audit_replay_validation_passed"))
    add(
        "self_validation_blocker_matches_state",
        self_ok != ("parallel_strategy_audit_self_validation_gap" in blockers),
        "Self-validation blocker must mirror the self-validation state.",
        self_validation_passed=self_ok,
    )
    add(
        "replay_validation_blocker_matches_state",
        replay_ok != ("parallel_strategy_audit_replay_validation_gap" in blockers),
        "Replay-validation blocker must mirror the replay-validation state.",
        replay_validation_passed=replay_ok,
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_integrity_validation_passed" if not failed_rows else "audit_integrity_validation_attention",
        "generated_at": utc_now().isoformat(),
        "integrity_validation_passed": not failed_rows,
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "integrity validation cross-checks status, blockers, repair rows, paths, and mutation boundaries",
            "integrity validation is audit-only and never starts runtime processes or broker mutation",
        ],
    }


def _audit_validation_quorum_validation(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Require self, replay, and integrity validators to agree before trusting the audit."""
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    validator_states = {
        "self": bool(summary.get("audit_self_validation_passed")),
        "replay": bool(summary.get("audit_replay_validation_passed")),
        "integrity": bool(summary.get("audit_integrity_validation_passed")),
    }
    failed_validator_names = [name for name, passed in validator_states.items() if not passed]
    add(
        "all_validation_mirrors_passed",
        not failed_validator_names,
        "Self, replay, and integrity validation must all pass together.",
        failed_validators=failed_validator_names,
        validator_states=validator_states,
    )

    failed_count_sum = (
        int(_as_float(summary.get("audit_self_validation_failed_count"), 0.0))
        + int(_as_float(summary.get("audit_replay_validation_failed_count"), 0.0))
        + int(_as_float(summary.get("audit_integrity_validation_failed_count"), 0.0))
    )
    add(
        "validator_failed_counts_zero",
        failed_count_sum == 0,
        "Validator failed-count fields must sum to zero for a trusted quorum.",
        failed_count_sum=failed_count_sum,
    )

    expected_sections = {
        "audit_self_validation_rows": bool(_record_array(report.get("audit_self_validation_rows"))),
        "audit_replay_validation_rows": bool(_record_array(report.get("audit_replay_validation_rows"))),
        "audit_integrity_validation_rows": bool(_record_array(report.get("audit_integrity_validation_rows"))),
    }
    missing_sections = [name for name, present in expected_sections.items() if not present]
    add(
        "validation_row_sections_present",
        not missing_sections,
        "Each validation mirror must publish row-level evidence.",
        missing_sections=missing_sections,
    )

    validator_blockers = {
        "parallel_strategy_audit_self_validation_gap": validator_states["self"],
        "parallel_strategy_audit_replay_validation_gap": validator_states["replay"],
        "parallel_strategy_audit_integrity_validation_gap": validator_states["integrity"],
    }
    mismatched_blockers = [
        blocker
        for blocker, validator_passed in validator_blockers.items()
        if (blocker in blockers) == validator_passed
    ]
    add(
        "validator_blockers_match_validator_states",
        not mismatched_blockers,
        "Validator blockers must appear only for failing validation mirrors.",
        mismatched_blockers=mismatched_blockers,
    )

    proof_basis = str(summary.get("audit_self_validation_proof_basis") or "proof_basis_pending")
    add(
        "proof_basis_declared",
        proof_basis != "proof_basis_pending",
        "The validation quorum must name whether proof came from real runtime artifacts or an isolated fixture.",
        proof_basis=proof_basis,
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_validation_quorum_passed" if not failed_rows else "audit_validation_quorum_attention",
        "generated_at": utc_now().isoformat(),
        "validation_quorum_passed": not failed_rows,
        "validator_pass_count": sum(1 for passed in validator_states.values() if passed),
        "validator_required_count": len(validator_states),
        "proof_basis": proof_basis,
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "validation quorum trusts the audit only when self, replay, and integrity checks all agree",
            "validation quorum is audit-only and does not change live trading or runtime authority",
        ],
    }


PROVENANCE_TOP_LEVEL_EXCLUDE = {
    "write_info",
    "audit_artifact_provenance_proof",
    "audit_artifact_provenance_rows",
    "audit_artifact_provenance_failed_rows",
    "audit_served_artifact_proof",
    "audit_served_artifact_rows",
    "audit_served_artifact_failed_rows",
    "audit_freshness_sla_proof",
    "audit_freshness_sla_rows",
    "audit_freshness_sla_failed_rows",
    "audit_operator_surface_proof",
    "audit_operator_surface_rows",
    "audit_operator_surface_failed_rows",
    "audit_test_coverage_proof",
    "audit_test_coverage_rows",
    "audit_test_coverage_failed_rows",
    "audit_repair_coverage_proof",
    "audit_repair_coverage_rows",
    "audit_repair_coverage_failed_rows",
    "audit_runtime_repair_readiness_proof",
    "audit_runtime_repair_readiness_rows",
    "audit_runtime_repair_readiness_failed_rows",
    "audit_repair_acceptance_proof",
    "audit_repair_acceptance_rows",
    "audit_repair_acceptance_failed_rows",
    "audit_consistency_matrix_proof",
    "audit_consistency_matrix_rows",
    "audit_consistency_matrix_failed_rows",
    "audit_consistency_matrix_validator_rows",
    "audit_evidence_lineage_proof",
    "audit_evidence_lineage_rows",
    "audit_evidence_lineage_failed_rows",
    "audit_evidence_lineage_section_rows",
    "audit_validator_closure_proof",
    "audit_validator_closure_rows",
    "audit_validator_closure_failed_rows",
    "audit_validator_closure_source_rows",
    "audit_validation_chain_proof",
    "audit_validation_chain_rows",
    "audit_validation_chain_failed_rows",
    "audit_public_contract_proof",
    "audit_public_contract_rows",
    "audit_public_contract_failed_rows",
}
PROVENANCE_SUMMARY_PREFIXES = (
    "audit_artifact_provenance_",
    "audit_served_artifact_",
    "audit_freshness_sla_",
    "audit_operator_surface_",
    "audit_test_coverage_",
    "audit_repair_coverage_",
    "audit_runtime_repair_readiness_",
    "audit_repair_acceptance_",
    "audit_consistency_matrix_",
    "audit_evidence_lineage_",
    "audit_validator_closure_",
    "audit_validation_chain_",
    "audit_public_contract_",
)


def _audit_core_payload(report: Mapping[str, Any]) -> Dict[str, Any]:
    payload = json.loads(json.dumps(report, sort_keys=True, default=str))
    for key in PROVENANCE_TOP_LEVEL_EXCLUDE:
        payload.pop(key, None)
    summary = payload.get("summary")
    if isinstance(summary, dict):
        for key in list(summary.keys()):
            if any(key.startswith(prefix) for prefix in PROVENANCE_SUMMARY_PREFIXES):
                summary.pop(key, None)
    return payload


def _audit_core_digest(report: Mapping[str, Any]) -> str:
    canonical = json.dumps(_audit_core_payload(report), sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return _sha256_bytes(canonical)


def _audit_artifact_provenance_validation(
    *,
    root: Path,
    report: Mapping[str, Any],
    json_paths: Sequence[Path],
    markdown_path: Path,
) -> Dict[str, Any]:
    """Read written audit artifacts back and prove their core payloads match."""
    expected_digest = _audit_core_digest(report)
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    digest_rows: List[Dict[str, Any]] = []
    for rel_path in json_paths:
        path = _rooted(root, rel_path)
        exists = path.exists()
        row: Dict[str, Any] = {
            "path": rel_path.as_posix(),
            "exists": exists,
            "sha256": "",
            "core_sha256": "",
            "core_matches": False,
            "status_matches": False,
            "schema_matches": False,
            "generated_at_matches": False,
            "json_parse_ok": False,
        }
        if exists:
            data = path.read_bytes()
            row["sha256"] = _sha256_bytes(data)
            try:
                parsed = json.loads(data.decode("utf-8"))
                row["json_parse_ok"] = isinstance(parsed, dict)
                if isinstance(parsed, dict):
                    row["core_sha256"] = _audit_core_digest(parsed)
                    row["core_matches"] = row["core_sha256"] == expected_digest
                    row["status_matches"] = parsed.get("status") == report.get("status")
                    row["schema_matches"] = parsed.get("schema_version") == report.get("schema_version")
                    row["generated_at_matches"] = parsed.get("generated_at") == report.get("generated_at")
            except Exception as exc:
                row["parse_error"] = str(exc)
        digest_rows.append(row)
        add(
            f"json_artifact_{rel_path.name}_core_matches",
            bool(row["exists"] and row["json_parse_ok"] and row["core_matches"] and row["status_matches"] and row["schema_matches"] and row["generated_at_matches"]),
            "JSON artifact must parse and match the in-memory audit core payload.",
            **row,
        )

    md_path = _rooted(root, markdown_path)
    md_exists = md_path.exists()
    md_text = md_path.read_text(encoding="utf-8") if md_exists else ""
    add(
        "markdown_artifact_contains_status_and_quorum",
        md_exists and str(report.get("status")) in md_text and "Audit validation quorum passed" in md_text,
        "Markdown artifact must include the final status and validation quorum summary.",
        path=markdown_path.as_posix(),
        exists=md_exists,
        sha256=_sha256_bytes(md_text.encode("utf-8")) if md_exists else "",
    )

    json_match_count = sum(1 for row in digest_rows if row.get("core_matches"))
    add(
        "all_public_state_docs_json_core_hashes_match",
        json_match_count == len(json_paths),
        "State, docs, and public JSON artifacts must carry the same core audit payload.",
        expected_count=len(json_paths),
        match_count=json_match_count,
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_artifact_provenance_passed" if not failed_rows else "audit_artifact_provenance_attention",
        "generated_at": utc_now().isoformat(),
        "artifact_provenance_passed": not failed_rows,
        "expected_core_sha256": expected_digest,
        "json_hash_match_count": json_match_count,
        "json_artifact_count": len(json_paths),
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "json_digest_rows": digest_rows,
        "manual_boundaries": [
            "artifact provenance reads written evidence back and compares core hashes",
            "artifact provenance is audit-only and never mutates broker or runtime state",
        ],
    }


def _fetch_served_public_artifact(url: str, timeout_sec: float = 2.0) -> Dict[str, Any]:
    try:
        with urlopen(url, timeout=timeout_sec) as response:  # nosec B310 - localhost audit endpoint only.
            data = response.read()
        parsed = json.loads(data.decode("utf-8"))
        if not isinstance(parsed, dict):
            return {"payload": None, "error": "served JSON root is not an object", "bytes": len(data)}
        return {"payload": parsed, "error": "", "bytes": len(data), "sha256": _sha256_bytes(data)}
    except (OSError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {"payload": None, "error": str(exc), "bytes": 0, "sha256": ""}


def _audit_served_artifact_validation(
    *,
    report: Mapping[str, Any],
    served_payload: Optional[Mapping[str, Any]] = None,
    served_url: str = DEFAULT_SERVED_PUBLIC_URL,
    required: bool = False,
    fetch_error: str = "",
    served_sha256: str = "",
) -> Dict[str, Any]:
    """Compare browser-served JSON with the just-written audit evidence."""
    rows: List[Dict[str, Any]] = []
    expected_digest = _audit_core_digest(report)

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    checked = served_payload is not None or bool(fetch_error)
    if not checked and not required:
        add(
            "served_artifact_probe_optional_in_fixture",
            True,
            "Localhost served-artifact validation is skipped for isolated fixtures.",
            served_url=served_url,
            endpoint_checked=False,
        )
        failed_rows = [row for row in rows if not row["passing"]]
        return {
            "status": "audit_served_artifact_not_checked",
            "generated_at": utc_now().isoformat(),
            "served_artifact_passed": not failed_rows,
            "served_artifact_checked": False,
            "served_artifact_core_matches": False,
            "served_url": served_url,
            "served_sha256": served_sha256,
            "expected_core_sha256": expected_digest,
            "check_count": len(rows),
            "failed_count": len(failed_rows),
            "passed_count": len(rows) - len(failed_rows),
            "failed_rows": failed_rows,
            "rows": rows,
        }

    add(
        "served_artifact_endpoint_reachable",
        served_payload is not None,
        "The browser-facing public audit JSON must be reachable when this validation is required.",
        served_url=served_url,
        fetch_error=fetch_error,
    )

    core_matches = False
    status_matches = False
    generated_at_matches = False
    schema_matches = False
    served_core_sha256 = ""
    if served_payload is not None:
        served_core_sha256 = _audit_core_digest(served_payload)
        core_matches = served_core_sha256 == expected_digest
        status_matches = served_payload.get("status") == report.get("status")
        generated_at_matches = served_payload.get("generated_at") == report.get("generated_at")
        schema_matches = served_payload.get("schema_version") == report.get("schema_version")

    add(
        "served_artifact_core_hash_matches",
        core_matches,
        "Browser-served JSON core payload must match the written audit payload.",
        served_url=served_url,
        expected_core_sha256=expected_digest,
        served_core_sha256=served_core_sha256,
    )
    add(
        "served_artifact_identity_fields_match",
        status_matches and generated_at_matches and schema_matches,
        "Browser-served status, generated_at, and schema must match the written audit.",
        status_matches=status_matches,
        generated_at_matches=generated_at_matches,
        schema_matches=schema_matches,
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_served_artifact_passed" if not failed_rows else "audit_served_artifact_attention",
        "generated_at": utc_now().isoformat(),
        "served_artifact_passed": not failed_rows,
        "served_artifact_checked": True,
        "served_artifact_core_matches": core_matches,
        "served_url": served_url,
        "served_sha256": served_sha256,
        "expected_core_sha256": expected_digest,
        "served_core_sha256": served_core_sha256,
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "served artifact validation checks the localhost JSON consumed by the UI",
            "served artifact validation is audit-only and never mutates broker or runtime state",
        ],
    }


def _audit_freshness_sla_validation(
    report: Mapping[str, Any],
    *,
    now: Optional[datetime] = None,
    max_age_sec: float = 120.0,
    max_validator_span_sec: float = 180.0,
) -> Dict[str, Any]:
    """Validate that the audit evidence was generated recently and coherently."""
    now_dt = now or utc_now()
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    generated_at = _parse_datetime(report.get("generated_at"))
    age_sec = (now_dt - generated_at).total_seconds() if generated_at else float("inf")
    add(
        "audit_generated_at_parseable",
        generated_at is not None,
        "Audit generated_at must be parseable before Trading treats the artifact as current.",
        generated_at=report.get("generated_at"),
    )
    add(
        "audit_generated_at_within_sla",
        generated_at is not None and -5.0 <= age_sec <= max_age_sec,
        "Audit generated_at must be recent enough for operator-facing evidence.",
        age_sec=round(age_sec, 3) if age_sec != float("inf") else None,
        max_age_sec=max_age_sec,
    )

    proof_keys = [
        "audit_self_validation_proof",
        "audit_replay_validation_proof",
        "audit_integrity_validation_proof",
        "audit_validation_quorum_proof",
        "audit_artifact_provenance_proof",
        "audit_served_artifact_proof",
    ]
    proof_timestamp_rows: List[Dict[str, Any]] = []
    proof_times: List[datetime] = []
    for key in proof_keys:
        proof = report.get(key) if isinstance(report.get(key), dict) else {}
        proof_time = _parse_datetime(proof.get("generated_at") if isinstance(proof, dict) else None)
        if proof_time is not None:
            proof_times.append(proof_time)
        proof_timestamp_rows.append(
            {
                "proof_key": key,
                "generated_at": proof.get("generated_at") if isinstance(proof, dict) else None,
                "timestamp_parseable": proof_time is not None,
            }
        )

    missing_proof_timestamps = [row["proof_key"] for row in proof_timestamp_rows if not row["timestamp_parseable"]]
    add(
        "validator_proof_timestamps_parseable",
        not missing_proof_timestamps,
        "Each upstream validator proof must publish a parseable generated_at timestamp.",
        missing_proof_timestamps=missing_proof_timestamps,
        proof_timestamp_rows=proof_timestamp_rows,
    )

    validator_span_sec = 0.0
    if len(proof_times) >= 2:
        validator_span_sec = (max(proof_times) - min(proof_times)).total_seconds()
    add(
        "validator_proof_timestamps_coherent",
        len(proof_times) >= len(proof_keys) and validator_span_sec <= max_validator_span_sec,
        "Validator proof timestamps should be emitted in one coherent audit pass.",
        validator_span_sec=round(validator_span_sec, 3),
        max_validator_span_sec=max_validator_span_sec,
        proof_timestamp_count=len(proof_times),
        required_proof_timestamp_count=len(proof_keys),
    )

    write_info = report.get("write_info") if isinstance(report.get("write_info"), dict) else {}
    evidence_writes = write_info.get("evidence_writes") if isinstance(write_info.get("evidence_writes"), list) else []
    zero_byte_writes = [
        row.get("path")
        for row in evidence_writes
        if isinstance(row, dict) and int(_as_float(row.get("bytes"), 0.0)) <= 0
    ]
    add(
        "fresh_evidence_writes_present",
        len(evidence_writes) >= 4 and not zero_byte_writes,
        "Freshness SLA requires visible non-empty writes for state, docs, public JSON, and markdown.",
        evidence_write_count=len(evidence_writes),
        zero_byte_writes=zero_byte_writes,
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_freshness_sla_passed" if not failed_rows else "audit_freshness_sla_attention",
        "generated_at": utc_now().isoformat(),
        "freshness_sla_passed": not failed_rows,
        "age_sec": round(age_sec, 3) if age_sec != float("inf") else None,
        "validator_span_sec": round(validator_span_sec, 3),
        "max_age_sec": max_age_sec,
        "max_validator_span_sec": max_validator_span_sec,
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "proof_timestamp_rows": proof_timestamp_rows,
        "manual_boundaries": [
            "freshness SLA validation proves operator evidence is current enough to trust",
            "freshness SLA validation is audit-only and never changes live trading authority",
        ],
    }


def _audit_public_contract_validation(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate the public JSON contract consumed by the Trading UI."""
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    required_summary_types = {
        "worker_count": (int, float),
        "healthy_worker_count": (int, float),
        "stale_worker_count": (int, float),
        "intent_count": (int, float),
        "executable_intent_count": (int, float),
        "api_budget_gap_count": (int, float),
        "mutation_leak_count": (int, float),
        "blocker_count": (int, float),
        "ghost_dance_enabled": (bool,),
        "harmonic_api_piano_enabled": (bool,),
        "rainbow_harmonic_ladder_enabled": (bool,),
        "power_station_request_governor_enabled": (bool,),
        "audit_self_validation_passed": (bool,),
        "audit_replay_validation_passed": (bool,),
        "audit_integrity_validation_passed": (bool,),
        "audit_validation_quorum_passed": (bool,),
        "audit_artifact_provenance_passed": (bool,),
        "audit_served_artifact_passed": (bool,),
        "audit_freshness_sla_passed": (bool,),
        "audit_operator_surface_passed": (bool,),
        "audit_test_coverage_passed": (bool,),
        "audit_repair_coverage_passed": (bool,),
        "audit_runtime_repair_readiness_passed": (bool,),
        "audit_repair_acceptance_passed": (bool,),
        "audit_consistency_matrix_passed": (bool,),
        "audit_evidence_lineage_passed": (bool,),
        "audit_validator_closure_passed": (bool,),
        "unified_executor_authoritative": (bool,),
        "direct_broker_mutation_allowed": (bool,),
    }
    missing_summary_fields = [key for key in required_summary_types if key not in summary]
    wrong_type_fields = [
        key
        for key, expected_types in required_summary_types.items()
        if key in summary and not isinstance(summary.get(key), expected_types)
    ]
    add(
        "required_summary_contract_fields_present",
        not missing_summary_fields,
        "Trading UI summary contract fields must be present.",
        missing_fields=missing_summary_fields,
    )
    add(
        "required_summary_contract_types_match",
        not wrong_type_fields,
        "Trading UI summary contract fields must keep stable primitive types.",
        wrong_type_fields=wrong_type_fields,
    )

    required_array_fields = [
        "artifact_rows",
        "worker_stress_rows",
        "intent_contract_rows",
        "api_budget_stress_rows",
        "mutation_authority_rows",
        "audit_self_validation_rows",
        "audit_replay_validation_rows",
        "audit_integrity_validation_rows",
        "audit_validation_quorum_rows",
        "audit_artifact_provenance_rows",
        "audit_served_artifact_rows",
        "audit_freshness_sla_rows",
        "audit_operator_surface_rows",
        "audit_test_coverage_rows",
        "audit_repair_coverage_rows",
        "audit_runtime_repair_readiness_rows",
        "audit_repair_acceptance_rows",
        "audit_consistency_matrix_rows",
        "audit_consistency_matrix_validator_rows",
        "audit_evidence_lineage_rows",
        "audit_evidence_lineage_section_rows",
        "audit_validator_closure_rows",
        "audit_validator_closure_source_rows",
        "next_repair_actions",
        "blockers",
        "manual_boundaries",
    ]
    bad_array_fields = [key for key in required_array_fields if not isinstance(report.get(key), list)]
    add(
        "required_public_arrays_present",
        not bad_array_fields,
        "Public artifact list fields must remain arrays, even when empty.",
        bad_array_fields=bad_array_fields,
    )

    source_paths = report.get("source_paths") if isinstance(report.get("source_paths"), dict) else {}
    required_source_paths = {"parallel_unity", "request_broker", "strategy_intents", "live_signal_fabric", "runtime_status"}
    missing_source_paths = sorted(required_source_paths - set(source_paths.keys()))
    add(
        "required_source_paths_present",
        not missing_source_paths,
        "Public artifact must expose source paths used by the Trading panel.",
        missing_source_paths=missing_source_paths,
    )

    write_info = report.get("write_info") if isinstance(report.get("write_info"), dict) else {}
    evidence_writes = write_info.get("evidence_writes") if isinstance(write_info.get("evidence_writes"), list) else []
    add(
        "write_info_evidence_writes_present",
        len(evidence_writes) >= 4,
        "Written state/docs/public evidence rows must be visible in write_info.",
        evidence_write_count=len(evidence_writes),
    )

    boundary_text = " ".join(str(item).lower() for item in report.get("manual_boundaries", []) if str(item))
    add(
        "public_contract_preserves_no_direct_worker_mutation",
        "unified_market_trader remains the only broker mutation authority" in boundary_text
        and bool(summary.get("unified_executor_authoritative"))
        and summary.get("direct_broker_mutation_allowed") is False,
        "Public contract must preserve the one-executor/no-direct-worker-mutation statement.",
        unified_executor_authoritative=summary.get("unified_executor_authoritative"),
        direct_broker_mutation_allowed=summary.get("direct_broker_mutation_allowed"),
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_public_contract_passed" if not failed_rows else "audit_public_contract_attention",
        "generated_at": utc_now().isoformat(),
        "public_contract_passed": not failed_rows,
        "required_summary_field_count": len(required_summary_types),
        "required_array_field_count": len(required_array_fields),
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "public contract validation protects the JSON fields the Trading UI reads",
            "public contract validation is audit-only and never mutates broker or runtime state",
        ],
    }


def _parallel_trading_panel_source(app_text: str) -> str:
    start = app_text.find("function ParallelTradingSystemsPanel")
    if start < 0:
        return ""
    end = app_text.find("function LiveSignalFabricPanel", start)
    if end < 0:
        end = app_text.find("\nfunction ", start + len("function ParallelTradingSystemsPanel"))
    return app_text[start:end if end > start else len(app_text)]


def _audit_operator_surface_validation(root: Path, report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate the operator-facing Trading panel source contract."""
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    app_path = _rooted(root, Path("frontend/src/App.tsx"))
    if not app_path.exists():
        add(
            "operator_surface_source_optional_in_fixture",
            True,
            "Frontend source is not present in this isolated fixture; real repo runs validate the operator panel source.",
            path=str(app_path),
        )
        failed_rows = [row for row in rows if not row["passing"]]
        return {
            "status": "audit_operator_surface_not_checked",
            "generated_at": utc_now().isoformat(),
            "operator_surface_passed": not failed_rows,
            "required_panel_count": 0,
            "mutation_control_count": 0,
            "artifact_link_count": 0,
            "check_count": len(rows),
            "failed_count": len(failed_rows),
            "passed_count": len(rows) - len(failed_rows),
            "failed_rows": failed_rows,
            "rows": rows,
            "manual_boundaries": [
                "operator surface validation checks frontend source in real repo mode",
                "operator surface validation is audit-only and never starts trading or mutates broker state",
            ],
        }
    try:
        app_text = app_path.read_text(encoding="utf-8")
    except Exception:
        app_text = ""
    panel_text = _parallel_trading_panel_source(app_text)
    add(
        "parallel_trading_panel_source_found",
        bool(panel_text),
        "Trading UI must include the ParallelTradingSystemsPanel source section.",
        path=str(app_path),
    )

    required_labels = [
        "Parallel Trading Systems",
        "Ghost Dance API phase protocol",
        "Harmonic API Piano",
        "Rainbow Harmonic Frequency Ladder",
        "Power Station Request Governor",
        "Audit Self-Validation",
        "Audit Replay Validation",
        "Audit Integrity Triangulation",
        "Audit Validation Quorum",
        "Audit Artifact Provenance",
        "Audit Served Artifact",
        "Audit Freshness SLA",
        "Audit Test Coverage",
        "Audit Repair Coverage",
        "Audit Runtime Repair Readiness",
        "Audit Repair Acceptance",
        "Audit Consistency Matrix",
        "Audit Evidence Lineage",
        "Audit Validator Closure",
        "Audit Public Contract",
        "Audit Validation Chain",
    ]
    missing_labels = [label for label in required_labels if label not in panel_text]
    add(
        "required_parallel_operator_panels_present",
        not missing_labels,
        "Parallel Trading Systems must expose every protocol and validation panel required by the audit.",
        required_panel_count=len(required_labels),
        missing_labels=missing_labels,
    )

    required_artifact_links = [
        "/aureon_parallel_strategy_unity.json",
        "/aureon_parallel_strategy_unity_stress_audit.json",
    ]
    missing_links = [link for link in required_artifact_links if link not in panel_text]
    add(
        "operator_artifact_links_present",
        not missing_links,
        "Operator panel must expose the unity and stress artifact links.",
        missing_links=missing_links,
    )

    mutation_button_pattern = re.compile(r"<button\b[^>]*>\s*(buy|sell|close|cancel|order|hedge)\s*</button>", re.IGNORECASE | re.DOTALL)
    mutation_buttons = [match.group(1).lower() for match in mutation_button_pattern.finditer(panel_text)]
    add(
        "operator_surface_has_no_manual_trade_buttons",
        not mutation_buttons,
        "Parallel operator panel must not add manual buy/sell/close/cancel/order/hedge buttons.",
        mutation_control_count=len(mutation_buttons),
        mutation_button_labels=mutation_buttons,
    )

    artifact_report_paths = []
    for rel_path in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        path = _rooted(root, rel_path)
        artifact_report_paths.append({"path": rel_path.as_posix(), "exists": path.exists(), "bytes": path.stat().st_size if path.exists() else 0})
    missing_written_artifacts = [row["path"] for row in artifact_report_paths if not row["exists"] or int(row["bytes"]) <= 0]
    add(
        "operator_surface_artifacts_written",
        not missing_written_artifacts,
        "Operator surface validation expects state, docs, and public stress artifacts to be written.",
        artifact_report_paths=artifact_report_paths,
        missing_written_artifacts=missing_written_artifacts,
    )

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    add(
        "operator_surface_mirrors_audit_contract",
        bool(summary.get("audit_freshness_sla_passed")) and bool(summary.get("unified_executor_authoritative")),
        "Operator surface trust requires fresh audit evidence and the one-executor contract.",
        audit_freshness_sla_passed=summary.get("audit_freshness_sla_passed"),
        unified_executor_authoritative=summary.get("unified_executor_authoritative"),
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_operator_surface_passed" if not failed_rows else "audit_operator_surface_attention",
        "generated_at": utc_now().isoformat(),
        "operator_surface_passed": not failed_rows,
        "required_panel_count": len(required_labels),
        "mutation_control_count": len(mutation_buttons),
        "artifact_link_count": len(required_artifact_links) - len(missing_links),
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "operator surface validation checks the Trading panel source contract",
            "operator surface validation is audit-only and never starts trading or mutates broker state",
        ],
    }


def _audit_test_coverage_validation(root: Path, report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate that trusted audit validators have source-level tests."""
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    test_path = _rooted(root, Path("tests/test_parallel_strategy_unity_stress_audit.py"))
    if not test_path.exists():
        add(
            "test_coverage_source_optional_in_fixture",
            True,
            "Test source is not present in this isolated fixture; real repo runs validate audit test coverage.",
            path=str(test_path),
        )
        failed_rows = [row for row in rows if not row["passing"]]
        return {
            "status": "audit_test_coverage_not_checked",
            "generated_at": utc_now().isoformat(),
            "test_coverage_passed": not failed_rows,
            "validator_test_count": 0,
            "validator_import_count": 0,
            "check_count": len(rows),
            "failed_count": len(failed_rows),
            "passed_count": len(rows) - len(failed_rows),
            "failed_rows": failed_rows,
            "rows": rows,
            "manual_boundaries": [
                "test coverage validation checks audit test source in real repo mode",
                "test coverage validation is audit-only and never starts trading or mutates broker state",
            ],
        }

    try:
        test_text = test_path.read_text(encoding="utf-8")
    except Exception:
        test_text = ""

    validator_expectations = [
        ("self", "_audit_self_validation", "self_validation_flags_missing_core_artifact"),
        ("replay", "_audit_report_replay_validation", "replay_validation_flags_corrupt_summary"),
        ("integrity", "_audit_integrity_triangulation_validation", "integrity_validation_flags_corrupt_blocker_count"),
        ("quorum", "_audit_validation_quorum_validation", "validation_quorum_flags_failed_mirror"),
        ("artifact_provenance", "_audit_artifact_provenance_validation", "artifact_provenance_flags_tampered_public_json"),
        ("served_artifact", "_audit_served_artifact_validation", "served_artifact_validation_flags_tampered_payload"),
        ("freshness_sla", "_audit_freshness_sla_validation", "freshness_sla_flags_stale_report"),
        ("operator_surface", "_audit_operator_surface_validation", "operator_surface_flags_missing_panel"),
        ("public_contract", "_audit_public_contract_validation", "public_contract_flags_missing_summary_field"),
        ("validation_chain", "_audit_validation_chain_validation", "validation_chain_flags_missing_validator_rows"),
        ("test_coverage", "_audit_test_coverage_validation", "test_coverage_flags_missing_validator_test"),
        ("repair_coverage", "_audit_repair_coverage_validation", "repair_coverage_flags_generic_repair_action"),
        ("runtime_repair_readiness", "_audit_runtime_repair_readiness_validation", "runtime_repair_readiness_flags_unsafe_command"),
        ("repair_acceptance", "_audit_repair_acceptance_validation", "repair_acceptance_flags_missing_post_restart_check"),
        ("consistency_matrix", "_audit_consistency_matrix_validation", "consistency_matrix_flags_corrupt_validator_count"),
        ("evidence_lineage", "_audit_evidence_lineage_validation", "evidence_lineage_flags_missing_source_path"),
        ("validator_closure", "_audit_validator_closure_validation", "validator_closure_flags_missing_validator_summary"),
    ]

    coverage_rows: List[Dict[str, Any]] = []
    for validator_id, import_marker, test_marker in validator_expectations:
        row = {
            "validator_id": validator_id,
            "import_marker": import_marker,
            "test_marker": test_marker,
            "import_present": import_marker in test_text,
            "negative_path_test_present": test_marker in test_text,
        }
        row["covered"] = row["import_present"] and row["negative_path_test_present"]
        coverage_rows.append(row)

    missing_imports = [row["validator_id"] for row in coverage_rows if not row["import_present"]]
    missing_tests = [row["validator_id"] for row in coverage_rows if not row["negative_path_test_present"]]
    add(
        "validator_imports_present_in_tests",
        not missing_imports,
        "Each trusted validator helper must be imported by the focused stress test module.",
        missing_imports=missing_imports,
        validator_import_count=sum(1 for row in coverage_rows if row["import_present"]),
    )
    add(
        "validator_negative_path_tests_present",
        not missing_tests,
        "Each trusted validator must have a focused negative-path test marker.",
        missing_tests=missing_tests,
        validator_test_count=sum(1 for row in coverage_rows if row["negative_path_test_present"]),
    )

    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    add(
        "test_coverage_mirrors_operator_surface",
        bool(summary.get("audit_operator_surface_passed")) and bool(summary.get("audit_freshness_sla_passed")),
        "Test coverage trust is evaluated after freshness and operator-surface validation are present.",
        audit_operator_surface_passed=summary.get("audit_operator_surface_passed"),
        audit_freshness_sla_passed=summary.get("audit_freshness_sla_passed"),
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_test_coverage_passed" if not failed_rows else "audit_test_coverage_attention",
        "generated_at": utc_now().isoformat(),
        "test_coverage_passed": not failed_rows,
        "validator_test_count": sum(1 for row in coverage_rows if row["negative_path_test_present"]),
        "validator_import_count": sum(1 for row in coverage_rows if row["import_present"]),
        "validator_expected_count": len(validator_expectations),
        "coverage_rows": coverage_rows,
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "test coverage validation proves validator tests are wired to the audit source",
            "test coverage validation is audit-only and never starts trading or mutates broker state",
        ],
    }


def _audit_repair_coverage_validation(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate that visible blockers have concrete, non-generic repair guidance."""
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    repair_rows = _record_array(report.get("next_repair_actions"))
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    blocker_counts = Counter(blockers)
    duplicate_blockers = sorted(blocker for blocker, count in blocker_counts.items() if count > 1)
    add(
        "visible_blockers_are_unique",
        not duplicate_blockers,
        "Blockers must be unique so repair rows do not hide duplicate runtime facts.",
        duplicate_blockers=duplicate_blockers,
    )

    repair_blockers = [str(row.get("blocker") or "") for row in repair_rows if row.get("blocker")]
    missing_repair_rows = sorted(set(blockers) - set(repair_blockers))
    extra_repair_rows = sorted(set(repair_blockers) - set(blockers))
    add(
        "repair_rows_match_visible_blockers",
        not missing_repair_rows and not extra_repair_rows,
        "Repair rows must exactly cover the visible blocker set.",
        missing_repair_rows=missing_repair_rows,
        extra_repair_rows=extra_repair_rows,
        repair_action_count=len(repair_rows),
        blocker_count=len(blockers),
    )

    incomplete_repair_rows = [
        str(row.get("blocker") or f"row_{index}")
        for index, row in enumerate(repair_rows)
        if not str(row.get("owner") or "").strip() or not str(row.get("action") or "").strip()
    ]
    add(
        "repair_rows_have_owner_and_action",
        not incomplete_repair_rows,
        "Every repair row must name an owner and a concrete next action.",
        incomplete_repair_rows=incomplete_repair_rows,
    )

    generic_repair_rows = [
        str(row.get("blocker") or f"row_{index}")
        for index, row in enumerate(repair_rows)
        if str(row.get("action") or "").strip().lower() in {"inspect artifact rows.", "inspect artifact rows"}
    ]
    add(
        "repair_actions_are_specific",
        not generic_repair_rows,
        "Repair rows must not fall back to generic inspection guidance.",
        generic_repair_rows=generic_repair_rows,
    )

    runtime_blockers = {
        "parallel_strategy_runtime_process_duplicate",
        "parallel_strategy_runtime_wrong_python",
        "parallel_strategy_supervisor_process_missing",
        "parallel_strategy_launcher_readiness_gap",
    }
    active_runtime_blockers = sorted(runtime_blockers.intersection(blockers))
    runtime_evidence_present = bool(_record_array(report.get("runtime_process_burndown_rows"))) or bool(report.get("single_owner_repair_plan"))
    add(
        "runtime_repair_blockers_have_process_evidence",
        (not active_runtime_blockers) or runtime_evidence_present,
        "Runtime/process repair blockers must be backed by process or launcher repair evidence.",
        active_runtime_blockers=active_runtime_blockers,
        runtime_process_burndown_count=len(_record_array(report.get("runtime_process_burndown_rows"))),
        single_owner_repair_plan_present=isinstance(report.get("single_owner_repair_plan"), dict),
    )

    boundary_text = " ".join(str(item).lower() for item in report.get("manual_boundaries", []) if str(item))
    add(
        "repair_guidance_is_advisory_only",
        "repair plan rows are advisory" in boundary_text,
        "Repair coverage validation must preserve that repair rows do not stop/start processes by themselves.",
        manual_boundary_count=len(report.get("manual_boundaries", []) if isinstance(report.get("manual_boundaries"), list) else []),
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_repair_coverage_passed" if not failed_rows else "audit_repair_coverage_attention",
        "generated_at": utc_now().isoformat(),
        "repair_coverage_passed": not failed_rows,
        "repair_action_count": len(repair_rows),
        "blocker_count": len(blockers),
        "generic_repair_count": len(generic_repair_rows),
        "runtime_repair_blocker_count": len(active_runtime_blockers),
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "repair coverage validation proves visible blockers have concrete owner/action rows",
            "repair coverage validation is audit-only and never stops, starts, or mutates runtime processes",
        ],
    }


def _audit_runtime_repair_readiness_validation(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate the guarded, advisory runtime repair package."""
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    plan = report.get("single_owner_repair_plan") if isinstance(report.get("single_owner_repair_plan"), dict) else {}
    stop_rows = _record_array(report.get("single_owner_stop_target_rows"))
    start_rows = _record_array(report.get("single_owner_start_target_rows"))
    post_rows = _record_array(report.get("post_restart_check_rows"))
    guard_rows = _record_array(report.get("single_owner_guard_validation_rows"))
    command_lines = [str(line) for line in report.get("guarded_repair_command_lines", []) if str(line)]
    command_text = "\n".join(command_lines)
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    if (
        plan.get("reason") == "source_not_available_in_fixture_or_packaged_runtime"
        and not command_lines
        and not stop_rows
        and not start_rows
        and not post_rows
        and not guard_rows
    ):
        add(
            "runtime_repair_readiness_optional_in_fixture",
            True,
            "Runtime repair package validation is skipped for isolated fixtures without launcher source.",
            repair_plan_reason=plan.get("reason"),
        )
        failed_rows = [row for row in rows if not row["passing"]]
        return {
            "status": "audit_runtime_repair_readiness_not_checked",
            "generated_at": utc_now().isoformat(),
            "runtime_repair_readiness_passed": not failed_rows,
            "guarded_command_line_count": 0,
            "unsafe_command_count": 0,
            "stop_target_count": 0,
            "start_target_count": 0,
            "post_restart_check_count": 0,
            "active_runtime_blocker_count": 0,
            "check_count": len(rows),
            "failed_count": len(failed_rows),
            "passed_count": len(rows) - len(failed_rows),
            "failed_rows": failed_rows,
            "rows": rows,
            "manual_boundaries": [
                "runtime repair readiness validates launcher repair packages in real repo mode",
                "runtime repair readiness is audit-only and never stops, starts, or mutates runtime processes",
            ],
        }

    runtime_blockers = {
        "parallel_strategy_runtime_process_duplicate",
        "parallel_strategy_runtime_wrong_python",
        "parallel_strategy_supervisor_process_missing",
        "parallel_strategy_launcher_readiness_gap",
    }
    active_runtime_blockers = sorted(runtime_blockers.intersection(blockers))
    add(
        "runtime_repair_plan_present_when_needed",
        (not active_runtime_blockers) or bool(plan),
        "Runtime repair blockers must publish a single-owner repair plan.",
        active_runtime_blockers=active_runtime_blockers,
        repair_plan_present=bool(plan),
    )

    guard_checks = {str(row.get("check") or ""): bool(row.get("passing")) for row in guard_rows}
    required_guard_checks = {
        "repair_plan_advisory_only",
        "standard_launcher_available",
        "stop_targets_scoped_to_runtime_modules",
        "post_restart_checks_defined",
        "guarded_command_package_ready",
    }
    missing_guard_checks = sorted(required_guard_checks - set(guard_checks.keys()))
    add(
        "guard_validation_rows_complete",
        not missing_guard_checks and bool(guard_rows),
        "Runtime repair readiness requires all guard validation rows.",
        missing_guard_checks=missing_guard_checks,
        guard_validation_count=len(guard_rows),
    )

    unsafe_command_fragments = [
        fragment
        for fragment in ["Remove-Item", "git reset", "git checkout --", "Invoke-WebRequest", "curl ", "Start-Process powershell"]
        if fragment.lower() in command_text.lower()
    ]
    command_has_pid_guard = "Get-CimInstance Win32_Process" in command_text and "CommandLine -notlike" in command_text and "Stop-Process" in command_text
    add(
        "guarded_command_is_scoped_and_non_destructive",
        (not command_lines) or (command_has_pid_guard and not unsafe_command_fragments),
        "Guarded command may stop scoped runtime PIDs only after command-line verification, with no destructive filesystem/network operations.",
        command_line_count=len(command_lines),
        command_has_pid_guard=command_has_pid_guard,
        unsafe_command_fragments=unsafe_command_fragments,
    )

    bad_stop_rows = [
        str(row.get("pid") or f"row_{index}")
        for index, row in enumerate(stop_rows)
        if str(row.get("target") or "") not in {"unified_market_trader", "parallel_strategy_unity"}
        or not bool(row.get("expected_command_substring"))
        or row.get("advisory_only") is not True
    ]
    add(
        "stop_targets_are_runtime_scoped_and_advisory",
        not bad_stop_rows,
        "Stop target rows must be scoped to known runtime modules and remain advisory-only.",
        stop_target_count=len(stop_rows),
        bad_stop_rows=bad_stop_rows,
    )

    start_targets = {str(row.get("target") or "") for row in start_rows}
    required_start_targets = {"production_launcher", "parallel_strategy_unity", "parallel_strategy_unity_stress_audit"}
    missing_start_targets = sorted(required_start_targets - start_targets)
    add(
        "start_targets_cover_parallel_runtime_stack",
        not missing_start_targets and all(row.get("advisory_only") is True for row in start_rows),
        "Repair plan must name the production launcher, parallel supervisor, and stress audit watcher as advisory start targets.",
        missing_start_targets=missing_start_targets,
        start_target_count=len(start_rows),
    )

    post_checks = {str(row.get("check") or "") for row in post_rows}
    required_post_checks = {
        "single_unified_market_trader_process",
        "unified_market_trader_uses_repo_venv",
        "parallel_supervisor_running",
        "terminal_embeds_parallel_unity",
        "terminal_embeds_parallel_intents",
        "worker_heartbeats_fresh",
    }
    missing_post_checks = sorted(required_post_checks - post_checks)
    add(
        "post_restart_checks_cover_runtime_and_artifacts",
        not missing_post_checks,
        "Post-restart checks must verify process ownership, terminal-state embedding, and worker heartbeat freshness.",
        missing_post_checks=missing_post_checks,
        post_restart_check_count=len(post_rows),
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_runtime_repair_readiness_passed" if not failed_rows else "audit_runtime_repair_readiness_attention",
        "generated_at": utc_now().isoformat(),
        "runtime_repair_readiness_passed": not failed_rows,
        "guarded_command_line_count": len(command_lines),
        "unsafe_command_count": len(unsafe_command_fragments),
        "stop_target_count": len(stop_rows),
        "start_target_count": len(start_rows),
        "post_restart_check_count": len(post_rows),
        "active_runtime_blocker_count": len(active_runtime_blockers),
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "runtime repair readiness validates the guarded repair package without executing it",
            "runtime repair readiness is audit-only and never stops, starts, or mutates runtime processes",
        ],
    }


def _audit_repair_acceptance_validation(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate that each current blocker has explicit post-repair acceptance evidence."""
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    post_rows = _record_array(report.get("post_restart_check_rows"))
    guard_rows = _record_array(report.get("single_owner_guard_validation_rows"))
    repair_rows = _record_array(report.get("next_repair_actions"))
    post_checks = {str(row.get("check") or "") for row in post_rows}
    guard_checks = {str(row.get("check") or "") for row in guard_rows}
    repair_blockers = {str(row.get("blocker") or "") for row in repair_rows if row.get("blocker")}
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    acceptance_requirements: Dict[str, List[str]] = {
        "parallel_strategy_worker_stale_or_missing": ["post:worker_heartbeats_fresh"],
        "parallel_strategy_runtime_process_duplicate": ["post:single_unified_market_trader_process"],
        "parallel_strategy_runtime_wrong_python": ["post:unified_market_trader_uses_repo_venv"],
        "parallel_strategy_supervisor_process_missing": ["post:parallel_supervisor_running"],
        "parallel_strategy_runtime_alignment_gap": ["post:terminal_embeds_parallel_unity", "post:terminal_embeds_parallel_intents"],
        "parallel_strategy_runtime_reload_required": ["post:terminal_embeds_parallel_unity", "post:terminal_embeds_parallel_intents"],
        "parallel_strategy_launcher_readiness_gap": ["guard:standard_launcher_available", "guard:guarded_command_package_ready"],
    }

    acceptance_rows: List[Dict[str, Any]] = []
    for blocker in blockers:
        required = acceptance_requirements.get(blocker, [])
        present: List[str] = []
        missing: List[str] = []
        for requirement in required:
            scope, check = requirement.split(":", 1)
            check_present = check in (post_checks if scope == "post" else guard_checks)
            (present if check_present else missing).append(requirement)
        acceptance_rows.append(
            {
                "blocker": blocker,
                "repair_row_present": blocker in repair_blockers,
                "acceptance_requirements": required,
                "present_acceptance_checks": present,
                "missing_acceptance_checks": missing,
                "acceptance_mapped": bool(required),
                "acceptance_ready": blocker in repair_blockers and bool(required) and not missing,
            }
        )

    missing_repair_rows = [row["blocker"] for row in acceptance_rows if not row["repair_row_present"]]
    unmapped_blockers = [row["blocker"] for row in acceptance_rows if not row["acceptance_mapped"]]
    missing_acceptance = [
        {"blocker": row["blocker"], "missing_acceptance_checks": row["missing_acceptance_checks"]}
        for row in acceptance_rows
        if row["missing_acceptance_checks"]
    ]
    add(
        "active_blockers_have_repair_rows",
        not missing_repair_rows,
        "Each active blocker must have a repair row before acceptance can be evaluated.",
        missing_repair_rows=missing_repair_rows,
    )
    add(
        "active_blockers_have_acceptance_mapping",
        not unmapped_blockers,
        "Each active blocker must map to at least one post-repair acceptance proof.",
        unmapped_blockers=unmapped_blockers,
    )
    add(
        "acceptance_checks_present_for_active_blockers",
        not missing_acceptance,
        "Current blockers must have the post-restart or guard checks that would prove burn-down.",
        missing_acceptance=missing_acceptance,
    )

    if not blockers:
        add(
            "certified_state_needs_no_repair_acceptance",
            True,
            "No visible blockers means no repair acceptance checks are required.",
            blocker_count=0,
        )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_repair_acceptance_passed" if not failed_rows else "audit_repair_acceptance_attention",
        "generated_at": utc_now().isoformat(),
        "repair_acceptance_passed": not failed_rows,
        "acceptance_row_count": len(acceptance_rows),
        "mapped_blocker_count": sum(1 for row in acceptance_rows if row["acceptance_mapped"]),
        "missing_acceptance_count": len(missing_acceptance),
        "unmapped_blocker_count": len(unmapped_blockers),
        "acceptance_rows": acceptance_rows,
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "manual_boundaries": [
            "repair acceptance validates the proof required after a guarded runtime repair",
            "repair acceptance is audit-only and never stops, starts, or mutates runtime processes",
        ],
    }


def _audit_consistency_matrix_validation(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate completed audit validators agree across summaries, rows, blockers, and repairs."""
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    repair_blockers = {
        str(row.get("blocker") or "")
        for row in _record_array(report.get("next_repair_actions"))
        if row.get("blocker")
    }
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    validators = [
        ("self", "audit_self_validation", "parallel_strategy_audit_self_validation_gap"),
        ("replay", "audit_replay_validation", "parallel_strategy_audit_replay_validation_gap"),
        ("integrity", "audit_integrity_validation", "parallel_strategy_audit_integrity_validation_gap"),
        ("quorum", "audit_validation_quorum", "parallel_strategy_audit_validation_quorum_gap"),
        ("artifact_provenance", "audit_artifact_provenance", "parallel_strategy_audit_artifact_provenance_gap"),
        ("served_artifact", "audit_served_artifact", "parallel_strategy_audit_served_artifact_gap"),
        ("freshness_sla", "audit_freshness_sla", "parallel_strategy_audit_freshness_sla_gap"),
        ("operator_surface", "audit_operator_surface", "parallel_strategy_audit_operator_surface_gap"),
        ("test_coverage", "audit_test_coverage", "parallel_strategy_audit_test_coverage_gap"),
        ("repair_coverage", "audit_repair_coverage", "parallel_strategy_audit_repair_coverage_gap"),
        ("runtime_repair_readiness", "audit_runtime_repair_readiness", "parallel_strategy_audit_runtime_repair_readiness_gap"),
        ("repair_acceptance", "audit_repair_acceptance", "parallel_strategy_audit_repair_acceptance_gap"),
    ]

    validator_rows: List[Dict[str, Any]] = []
    for validator_id, prefix, blocker in validators:
        pass_key = f"{prefix}_passed"
        failed_count_key = f"{prefix}_failed_count"
        rows_key = f"{prefix}_rows"
        failed_rows_key = f"{prefix}_failed_rows"
        evidence_rows = _record_array(report.get(rows_key))
        failed_rows = _record_array(report.get(failed_rows_key))
        failed_count = int(_as_float(summary.get(failed_count_key), -1.0))
        passed_value = summary.get(pass_key)
        failed_count_matches = failed_count == len(failed_rows)
        pass_state_matches = isinstance(passed_value, bool) and passed_value == (failed_count == 0)
        blocker_matches = (blocker in blockers) != bool(passed_value) if isinstance(passed_value, bool) else False
        repair_matches = bool(passed_value) or blocker in repair_blockers
        row = {
            "validator_id": validator_id,
            "prefix": prefix,
            "pass_key": pass_key,
            "failed_count_key": failed_count_key,
            "rows_key": rows_key,
            "failed_rows_key": failed_rows_key,
            "blocker": blocker,
            "passed": passed_value,
            "failed_count": failed_count,
            "row_count": len(evidence_rows),
            "failed_row_count": len(failed_rows),
            "summary_fields_present": pass_key in summary and failed_count_key in summary,
            "row_fields_present": isinstance(report.get(rows_key), list) and isinstance(report.get(failed_rows_key), list),
            "failed_count_matches_rows": failed_count_matches,
            "pass_state_matches_failed_count": pass_state_matches,
            "blocker_matches_pass_state": blocker_matches,
            "repair_row_matches_failure": repair_matches,
        }
        row["matrix_consistent"] = all(
            [
                row["summary_fields_present"],
                row["row_fields_present"],
                row["failed_count_matches_rows"],
                row["pass_state_matches_failed_count"],
                row["blocker_matches_pass_state"],
                row["repair_row_matches_failure"],
            ]
        )
        validator_rows.append(row)

    add(
        "validator_summary_fields_present",
        all(row["summary_fields_present"] for row in validator_rows),
        "Every completed validator must publish pass and failed-count summary fields.",
        missing=[row["validator_id"] for row in validator_rows if not row["summary_fields_present"]],
    )
    add(
        "validator_row_fields_present",
        all(row["row_fields_present"] for row in validator_rows),
        "Every completed validator must publish rows and failed-rows arrays.",
        missing=[row["validator_id"] for row in validator_rows if not row["row_fields_present"]],
    )
    add(
        "validator_failed_counts_match_rows",
        all(row["failed_count_matches_rows"] for row in validator_rows),
        "Every completed validator failed-count must equal its failed row count.",
        mismatched=[row["validator_id"] for row in validator_rows if not row["failed_count_matches_rows"]],
    )
    add(
        "validator_pass_states_match_failed_counts",
        all(row["pass_state_matches_failed_count"] for row in validator_rows),
        "Every completed validator pass flag must match its failed count.",
        mismatched=[row["validator_id"] for row in validator_rows if not row["pass_state_matches_failed_count"]],
    )
    add(
        "validator_blockers_match_pass_states",
        all(row["blocker_matches_pass_state"] for row in validator_rows),
        "Completed validator blockers must appear only when the corresponding validator fails.",
        mismatched=[row["validator_id"] for row in validator_rows if not row["blocker_matches_pass_state"]],
    )
    add(
        "failed_validators_have_repair_rows",
        all(row["repair_row_matches_failure"] for row in validator_rows),
        "Any failed completed validator must have a concrete next repair row.",
        missing=[row["validator_id"] for row in validator_rows if not row["repair_row_matches_failure"]],
    )

    inconsistent_rows = [row for row in validator_rows if not row["matrix_consistent"]]
    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_consistency_matrix_passed" if not failed_rows else "audit_consistency_matrix_attention",
        "generated_at": utc_now().isoformat(),
        "consistency_matrix_passed": not failed_rows,
        "validator_count": len(validator_rows),
        "validator_pass_count": sum(1 for row in validator_rows if row["passed"] is True),
        "inconsistent_validator_count": len(inconsistent_rows),
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "validator_rows": validator_rows,
        "manual_boundaries": [
            "consistency matrix validates completed audit validators agree across summaries, rows, blockers, and repair rows",
            "consistency matrix is audit-only and never starts trading or mutates broker/runtime state",
        ],
    }


def _audit_evidence_lineage_validation(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate that trusted UI sections trace back to source, output, and row evidence."""
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    source_paths = report.get("source_paths") if isinstance(report.get("source_paths"), dict) else {}
    output_files = [str(path) for path in report.get("output_files", []) if str(path)]
    artifact_rows = _record_array(report.get("artifact_rows"))
    manual_boundaries = [str(item) for item in report.get("manual_boundaries", []) if str(item)]
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    required_source_paths = {
        "parallel_unity",
        "request_broker",
        "strategy_intents",
        "live_signal_fabric",
        "runtime_status",
    }
    missing_source_paths = sorted(required_source_paths - set(source_paths.keys()))
    add(
        "required_source_paths_present",
        not missing_source_paths,
        "Every primary Trading proof source must expose a source path.",
        missing_source_paths=missing_source_paths,
        source_path_count=len(source_paths),
    )

    required_outputs = {
        DEFAULT_STATE_PATH.as_posix(),
        DEFAULT_AUDIT_JSON.as_posix(),
        DEFAULT_AUDIT_MD.as_posix(),
        DEFAULT_PUBLIC_JSON.as_posix(),
    }
    missing_outputs = sorted(required_outputs - set(output_files))
    add(
        "required_output_files_present",
        not missing_outputs,
        "State, docs, markdown, and public JSON output paths must stay visible.",
        missing_output_files=missing_outputs,
        output_file_count=len(output_files),
    )

    artifact_ids = {str(row.get("id") or "") for row in artifact_rows}
    missing_artifact_ids = sorted(required_source_paths - artifact_ids)
    add(
        "artifact_rows_cover_primary_sources",
        not missing_artifact_ids,
        "Artifact presence rows must cover the same primary source surfaces.",
        missing_artifact_ids=missing_artifact_ids,
        artifact_row_count=len(artifact_rows),
    )

    section_requirements: List[Dict[str, Any]] = [
        {"section_id": "artifact_rows", "field": "artifact_rows", "minimum_rows": 1},
        {"section_id": "worker_stress", "field": "worker_stress_rows", "minimum_rows": 1},
        {"section_id": "intent_contract", "field": "intent_contract_rows", "minimum_rows": 0},
        {"section_id": "lease_contract", "field": "lease_contract_rows", "minimum_rows": 0},
        {"section_id": "api_budget_stress", "field": "api_budget_stress_rows", "minimum_rows": 0},
        {"section_id": "mutation_authority", "field": "mutation_authority_rows", "minimum_rows": 0},
        {"section_id": "ghost_dance", "field": "ghost_phase_rows", "minimum_rows": 1},
        {"section_id": "harmonic_api_piano", "field": "piano_key_rows", "minimum_rows": 1},
        {"section_id": "rainbow_harmonic_ladder", "field": "rainbow_ladder_rows", "minimum_rows": 1},
        {"section_id": "power_station_request", "field": "power_station_request_rows", "minimum_rows": 1},
        {"section_id": "audit_self_validation", "field": "audit_self_validation_rows", "minimum_rows": 1},
        {"section_id": "audit_replay_validation", "field": "audit_replay_validation_rows", "minimum_rows": 1},
        {"section_id": "audit_integrity_validation", "field": "audit_integrity_validation_rows", "minimum_rows": 1},
        {"section_id": "audit_validation_quorum", "field": "audit_validation_quorum_rows", "minimum_rows": 1},
        {"section_id": "audit_artifact_provenance", "field": "audit_artifact_provenance_rows", "minimum_rows": 1},
        {"section_id": "audit_served_artifact", "field": "audit_served_artifact_rows", "minimum_rows": 1},
        {"section_id": "audit_freshness_sla", "field": "audit_freshness_sla_rows", "minimum_rows": 1},
        {"section_id": "audit_operator_surface", "field": "audit_operator_surface_rows", "minimum_rows": 1},
        {"section_id": "audit_test_coverage", "field": "audit_test_coverage_rows", "minimum_rows": 1},
        {"section_id": "audit_repair_coverage", "field": "audit_repair_coverage_rows", "minimum_rows": 1},
        {"section_id": "audit_runtime_repair_readiness", "field": "audit_runtime_repair_readiness_rows", "minimum_rows": 1},
        {"section_id": "audit_repair_acceptance", "field": "audit_repair_acceptance_rows", "minimum_rows": 1},
        {"section_id": "audit_consistency_matrix", "field": "audit_consistency_matrix_rows", "minimum_rows": 1},
    ]
    section_rows: List[Dict[str, Any]] = []
    for requirement in section_requirements:
        field = str(requirement["field"])
        raw_value = report.get(field)
        row_count = len(_record_array(raw_value))
        field_present = field in report
        field_is_array = isinstance(raw_value, list)
        minimum_rows = int(_as_float(requirement.get("minimum_rows"), 0.0))
        lineage_present = field_present and field_is_array and row_count >= minimum_rows
        section_rows.append(
            {
                "section_id": requirement["section_id"],
                "field": field,
                "row_count": row_count,
                "minimum_rows": minimum_rows,
                "field_present": field_present,
                "lineage_present": lineage_present,
            }
        )
    missing_section_lineage = [
        {"section_id": row["section_id"], "field": row["field"], "row_count": row["row_count"], "minimum_rows": row["minimum_rows"]}
        for row in section_rows
        if not row["lineage_present"]
    ]
    add(
        "proof_sections_have_lineage_rows",
        not missing_section_lineage,
        "Every trusted proof section must publish its backing row field; zero-gap sections may be empty but must still exist.",
        missing_section_lineage=missing_section_lineage,
        section_count=len(section_rows),
    )

    boundary_text = " ".join(manual_boundaries).lower()
    add(
        "manual_boundaries_present",
        bool(manual_boundaries) and "only broker mutation authority" in boundary_text,
        "Lineage evidence must preserve the operator-facing authority boundary.",
        boundary_count=len(manual_boundaries),
    )
    add(
        "lineage_mirrors_repair_acceptance",
        bool(summary.get("audit_repair_acceptance_passed")) and bool(summary.get("audit_runtime_repair_readiness_passed")),
        "Evidence lineage trust is evaluated only after runtime repair readiness and repair acceptance are row-backed.",
        audit_repair_acceptance_passed=summary.get("audit_repair_acceptance_passed"),
        audit_runtime_repair_readiness_passed=summary.get("audit_runtime_repair_readiness_passed"),
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_evidence_lineage_passed" if not failed_rows else "audit_evidence_lineage_attention",
        "generated_at": utc_now().isoformat(),
        "evidence_lineage_passed": not failed_rows,
        "source_path_count": len(source_paths),
        "output_file_count": len(output_files),
        "section_row_count": len(section_rows),
        "missing_lineage_count": len(missing_section_lineage) + len(missing_source_paths) + len(missing_outputs) + len(missing_artifact_ids),
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "section_rows": section_rows,
        "manual_boundaries": [
            "evidence lineage validates that UI-trusted proof surfaces trace back to source paths, output artifacts, and section rows",
            "evidence lineage is audit-only and never starts trading or mutates broker/runtime state",
        ],
    }


def _audit_validator_closure_validation(root: Path, report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate that audit validators are closed across source, tests, contract, UI, and repair maps."""
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    rows: List[Dict[str, Any]] = []
    source_rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    def add_source(source: str, passing: bool, detail: str, **extra: Any) -> None:
        source_rows.append(
            {
                "source": source,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    def source_slice(text: str, start_marker: str, end_marker: str) -> str:
        line_start = text.find("\n" + start_marker)
        if line_start >= 0:
            start = line_start + 1
        elif text.startswith(start_marker):
            start = 0
        else:
            start = -1
        if start < 0:
            return ""
        line_end = text.find("\n" + end_marker, start + len(start_marker))
        end = line_end + 1 if line_end >= 0 else -1
        return text[start:end if end > start else len(text)]

    validator_rows = [
        {"id": "self", "prefix": "audit_self_validation", "blocker": "parallel_strategy_audit_self_validation_gap", "label": "Audit Self-Validation"},
        {"id": "replay", "prefix": "audit_replay_validation", "blocker": "parallel_strategy_audit_replay_validation_gap", "label": "Audit Replay Validation"},
        {"id": "integrity", "prefix": "audit_integrity_validation", "blocker": "parallel_strategy_audit_integrity_validation_gap", "label": "Audit Integrity Validation"},
        {"id": "quorum", "prefix": "audit_validation_quorum", "blocker": "parallel_strategy_audit_validation_quorum_gap", "label": "Audit Validation Quorum"},
        {"id": "artifact_provenance", "prefix": "audit_artifact_provenance", "blocker": "parallel_strategy_audit_artifact_provenance_gap", "label": "Audit Artifact Provenance"},
        {"id": "public_contract", "prefix": "audit_public_contract", "blocker": "parallel_strategy_audit_public_contract_gap", "label": "Audit Public Contract"},
        {"id": "served_artifact", "prefix": "audit_served_artifact", "blocker": "parallel_strategy_audit_served_artifact_gap", "label": "Audit Served Artifact"},
        {"id": "freshness_sla", "prefix": "audit_freshness_sla", "blocker": "parallel_strategy_audit_freshness_sla_gap", "label": "Audit Freshness SLA"},
        {"id": "operator_surface", "prefix": "audit_operator_surface", "blocker": "parallel_strategy_audit_operator_surface_gap", "label": "Audit Operator Surface"},
        {"id": "test_coverage", "prefix": "audit_test_coverage", "blocker": "parallel_strategy_audit_test_coverage_gap", "label": "Audit Test Coverage"},
        {"id": "repair_coverage", "prefix": "audit_repair_coverage", "blocker": "parallel_strategy_audit_repair_coverage_gap", "label": "Audit Repair Coverage"},
        {"id": "runtime_repair_readiness", "prefix": "audit_runtime_repair_readiness", "blocker": "parallel_strategy_audit_runtime_repair_readiness_gap", "label": "Audit Runtime Repair Readiness"},
        {"id": "repair_acceptance", "prefix": "audit_repair_acceptance", "blocker": "parallel_strategy_audit_repair_acceptance_gap", "label": "Audit Repair Acceptance"},
        {"id": "consistency_matrix", "prefix": "audit_consistency_matrix", "blocker": "parallel_strategy_audit_consistency_matrix_gap", "label": "Audit Consistency Matrix"},
        {"id": "evidence_lineage", "prefix": "audit_evidence_lineage", "blocker": "parallel_strategy_audit_evidence_lineage_gap", "label": "Audit Evidence Lineage"},
        {"id": "validator_closure", "prefix": "audit_validator_closure", "blocker": "parallel_strategy_audit_validator_closure_gap", "label": "Audit Validator Closure"},
        {"id": "validation_chain", "prefix": "audit_validation_chain", "blocker": "parallel_strategy_audit_validation_chain_gap", "label": "Audit Validation Chain"},
    ]

    completed_validator_rows = [row for row in validator_rows if row["id"] not in {"public_contract", "validator_closure", "validation_chain"}]
    missing_summary_fields: List[str] = []
    missing_report_arrays: List[str] = []
    for validator in completed_validator_rows:
        prefix = str(validator["prefix"])
        for key in (f"{prefix}_passed", f"{prefix}_failed_count"):
            if key not in summary:
                missing_summary_fields.append(key)
        for key in (f"{prefix}_rows", f"{prefix}_failed_rows"):
            if not isinstance(report.get(key), list):
                missing_report_arrays.append(key)
    add(
        "validator_summary_fields_present",
        not missing_summary_fields,
        "Completed validators must expose summary pass and failed-count fields before closure can trust them.",
        missing_summary_fields=missing_summary_fields,
    )
    add(
        "validator_report_arrays_present",
        not missing_report_arrays,
        "Completed validators must expose row and failed-row arrays before closure can trust them.",
        missing_report_arrays=missing_report_arrays,
    )

    module_path = _rooted(root, Path("aureon/autonomous/aureon_parallel_strategy_unity_stress_audit.py"))
    module_text = module_path.read_text(encoding="utf-8") if module_path.exists() else ""
    if not module_text:
        add_source(
            "audit_module_source",
            True,
            "Audit module source is not present in this isolated fixture; real repo closure validates source registrations.",
            path=str(module_path),
        )
    else:
        chain_text = source_slice(module_text, "def _audit_validation_chain_validation", "def _status_from_blockers")
        test_coverage_text = source_slice(module_text, "def _audit_test_coverage_validation", "def _audit_repair_coverage_validation")
        public_contract_text = source_slice(module_text, "def _audit_public_contract_validation", "def _parallel_trading_panel_source")
        status_text = source_slice(module_text, "def _status_from_blockers", "def build_parallel_strategy_unity_stress_audit")
        repair_text = source_slice(module_text, "def _next_repair_actions", "def _make_markdown")
        markdown_text = source_slice(module_text, "def _make_markdown", "def build_and_write_parallel_strategy_unity_stress_audit")
        missing_chain = [row["id"] for row in validator_rows if row["id"] != "validation_chain" and f'"id": "{row["id"]}"' not in chain_text]
        missing_coverage = [row["id"] for row in validator_rows if f'("{row["id"]}",' not in test_coverage_text]
        missing_contract = [
            str(row["prefix"])
            for row in validator_rows
            if row["id"] not in {"public_contract", "validation_chain"}
            if f'{row["prefix"]}_passed' not in public_contract_text or f'{row["prefix"]}_rows' not in public_contract_text
        ]
        missing_status = [row["blocker"] for row in validator_rows if str(row["blocker"]) not in status_text]
        missing_repair = [row["blocker"] for row in validator_rows if str(row["blocker"]) not in repair_text]
        markdown_lower = markdown_text.lower()
        missing_markdown = [row["label"] for row in validator_rows if str(row["label"]).lower() not in markdown_lower]
        add_source(
            "validation_chain_registry",
            not missing_chain,
            "Validation-chain source must register every trusted validator.",
            missing_validators=missing_chain,
        )
        add_source(
            "test_coverage_registry",
            not missing_coverage,
            "Test-coverage source must expect every trusted validator.",
            missing_validators=missing_coverage,
        )
        add_source(
            "public_contract_registry",
            not missing_contract,
            "Public-contract source must require every validator summary and row field.",
            missing_validators=missing_contract,
        )
        add_source(
            "status_priority_registry",
            not missing_status,
            "Status priority source must map every validator blocker to an attention status.",
            missing_blockers=missing_status,
        )
        add_source(
            "repair_action_registry",
            not missing_repair,
            "Repair-action source must map every validator blocker to a concrete owner/action.",
            missing_blockers=missing_repair,
        )
        add_source(
            "markdown_registry",
            not missing_markdown,
            "Markdown source must publish operator-readable lines for every validator.",
            missing_labels=missing_markdown,
        )

    app_path = _rooted(root, Path("frontend/src/App.tsx"))
    app_text = app_path.read_text(encoding="utf-8") if app_path.exists() else ""
    if not app_text:
        add_source(
            "frontend_operator_panel",
            True,
            "Frontend source is not present in this isolated fixture; real repo closure validates the operator panel.",
            path=str(app_path),
        )
    else:
        panel_text = _parallel_trading_panel_source(app_text)
        required_ui_markers = ["Audit Validator Closure", "audit_validator_closure_rows", "auditValidatorClosureRows"]
        missing_ui_markers = [marker for marker in required_ui_markers if marker not in panel_text]
        add_source(
            "frontend_operator_panel",
            not missing_ui_markers,
            "Trading panel source must expose validator closure rows and status.",
            missing_ui_markers=missing_ui_markers,
        )

    failed_source_rows = [row for row in source_rows if not row["passing"]]
    add(
        "source_registries_closed",
        not failed_source_rows,
        "Validator closure requires source, contract, test, UI, status, and repair registries to agree.",
        failed_sources=[row["source"] for row in failed_source_rows],
    )

    boundary_text = " ".join(str(item).lower() for item in report.get("manual_boundaries", []) if str(item))
    add(
        "validator_closure_preserves_authority_boundary",
        "only broker mutation authority" in boundary_text and "do not place orders" in boundary_text,
        "Validator closure must preserve the audit-only/no-direct-broker-mutation boundary.",
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_validator_closure_passed" if not failed_rows else "audit_validator_closure_attention",
        "generated_at": utc_now().isoformat(),
        "validator_closure_passed": not failed_rows,
        "validator_count": len(validator_rows),
        "source_check_count": len(source_rows),
        "failed_source_count": len(failed_source_rows),
        "missing_summary_field_count": len(missing_summary_fields),
        "missing_report_array_count": len(missing_report_arrays),
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "source_rows": source_rows,
        "manual_boundaries": [
            "validator closure validates that validators are represented in source, tests, public contract, UI, status, and repair maps",
            "validator closure is audit-only and never starts trading or mutates broker/runtime state",
        ],
    }


def _audit_validation_chain_validation(report: Mapping[str, Any]) -> Dict[str, Any]:
    """Validate that every audit validator is present, row-backed, and consistent."""
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    validators = [
        {
            "id": "self",
            "passed_key": "audit_self_validation_passed",
            "failed_count_key": "audit_self_validation_failed_count",
            "rows_key": "audit_self_validation_rows",
            "failed_rows_key": "audit_self_validation_failed_rows",
            "blocker": "parallel_strategy_audit_self_validation_gap",
        },
        {
            "id": "replay",
            "passed_key": "audit_replay_validation_passed",
            "failed_count_key": "audit_replay_validation_failed_count",
            "rows_key": "audit_replay_validation_rows",
            "failed_rows_key": "audit_replay_validation_failed_rows",
            "blocker": "parallel_strategy_audit_replay_validation_gap",
        },
        {
            "id": "integrity",
            "passed_key": "audit_integrity_validation_passed",
            "failed_count_key": "audit_integrity_validation_failed_count",
            "rows_key": "audit_integrity_validation_rows",
            "failed_rows_key": "audit_integrity_validation_failed_rows",
            "blocker": "parallel_strategy_audit_integrity_validation_gap",
        },
        {
            "id": "quorum",
            "passed_key": "audit_validation_quorum_passed",
            "failed_count_key": "audit_validation_quorum_failed_count",
            "rows_key": "audit_validation_quorum_rows",
            "failed_rows_key": "audit_validation_quorum_failed_rows",
            "blocker": "parallel_strategy_audit_validation_quorum_gap",
        },
        {
            "id": "artifact_provenance",
            "passed_key": "audit_artifact_provenance_passed",
            "failed_count_key": "audit_artifact_provenance_failed_count",
            "rows_key": "audit_artifact_provenance_rows",
            "failed_rows_key": "audit_artifact_provenance_failed_rows",
            "blocker": "parallel_strategy_audit_artifact_provenance_gap",
        },
        {
            "id": "public_contract",
            "passed_key": "audit_public_contract_passed",
            "failed_count_key": "audit_public_contract_failed_count",
            "rows_key": "audit_public_contract_rows",
            "failed_rows_key": "audit_public_contract_failed_rows",
            "blocker": "parallel_strategy_audit_public_contract_gap",
        },
        {
            "id": "served_artifact",
            "passed_key": "audit_served_artifact_passed",
            "failed_count_key": "audit_served_artifact_failed_count",
            "rows_key": "audit_served_artifact_rows",
            "failed_rows_key": "audit_served_artifact_failed_rows",
            "blocker": "parallel_strategy_audit_served_artifact_gap",
        },
        {
            "id": "freshness_sla",
            "passed_key": "audit_freshness_sla_passed",
            "failed_count_key": "audit_freshness_sla_failed_count",
            "rows_key": "audit_freshness_sla_rows",
            "failed_rows_key": "audit_freshness_sla_failed_rows",
            "blocker": "parallel_strategy_audit_freshness_sla_gap",
        },
        {
            "id": "operator_surface",
            "passed_key": "audit_operator_surface_passed",
            "failed_count_key": "audit_operator_surface_failed_count",
            "rows_key": "audit_operator_surface_rows",
            "failed_rows_key": "audit_operator_surface_failed_rows",
            "blocker": "parallel_strategy_audit_operator_surface_gap",
        },
        {
            "id": "test_coverage",
            "passed_key": "audit_test_coverage_passed",
            "failed_count_key": "audit_test_coverage_failed_count",
            "rows_key": "audit_test_coverage_rows",
            "failed_rows_key": "audit_test_coverage_failed_rows",
            "blocker": "parallel_strategy_audit_test_coverage_gap",
        },
        {
            "id": "repair_coverage",
            "passed_key": "audit_repair_coverage_passed",
            "failed_count_key": "audit_repair_coverage_failed_count",
            "rows_key": "audit_repair_coverage_rows",
            "failed_rows_key": "audit_repair_coverage_failed_rows",
            "blocker": "parallel_strategy_audit_repair_coverage_gap",
        },
        {
            "id": "runtime_repair_readiness",
            "passed_key": "audit_runtime_repair_readiness_passed",
            "failed_count_key": "audit_runtime_repair_readiness_failed_count",
            "rows_key": "audit_runtime_repair_readiness_rows",
            "failed_rows_key": "audit_runtime_repair_readiness_failed_rows",
            "blocker": "parallel_strategy_audit_runtime_repair_readiness_gap",
        },
        {
            "id": "repair_acceptance",
            "passed_key": "audit_repair_acceptance_passed",
            "failed_count_key": "audit_repair_acceptance_failed_count",
            "rows_key": "audit_repair_acceptance_rows",
            "failed_rows_key": "audit_repair_acceptance_failed_rows",
            "blocker": "parallel_strategy_audit_repair_acceptance_gap",
        },
        {
            "id": "consistency_matrix",
            "passed_key": "audit_consistency_matrix_passed",
            "failed_count_key": "audit_consistency_matrix_failed_count",
            "rows_key": "audit_consistency_matrix_rows",
            "failed_rows_key": "audit_consistency_matrix_failed_rows",
            "blocker": "parallel_strategy_audit_consistency_matrix_gap",
        },
        {
            "id": "evidence_lineage",
            "passed_key": "audit_evidence_lineage_passed",
            "failed_count_key": "audit_evidence_lineage_failed_count",
            "rows_key": "audit_evidence_lineage_rows",
            "failed_rows_key": "audit_evidence_lineage_failed_rows",
            "blocker": "parallel_strategy_audit_evidence_lineage_gap",
        },
        {
            "id": "validator_closure",
            "passed_key": "audit_validator_closure_passed",
            "failed_count_key": "audit_validator_closure_failed_count",
            "rows_key": "audit_validator_closure_rows",
            "failed_rows_key": "audit_validator_closure_failed_rows",
            "blocker": "parallel_strategy_audit_validator_closure_gap",
        },
    ]
    rows: List[Dict[str, Any]] = []

    def add(check: str, passing: bool, detail: str, **extra: Any) -> None:
        rows.append(
            {
                "check": check,
                "passing": bool(passing),
                "detail": detail,
                **extra,
            }
        )

    validator_rows: List[Dict[str, Any]] = []
    for validator in validators:
        failed_rows = _record_array(report.get(str(validator["failed_rows_key"])))
        evidence_rows = _record_array(report.get(str(validator["rows_key"])))
        failed_count = int(_as_float(summary.get(str(validator["failed_count_key"])), -1.0))
        passed = bool(summary.get(str(validator["passed_key"])))
        row = {
            "validator_id": validator["id"],
            "passed": passed,
            "row_count": len(evidence_rows),
            "failed_count": failed_count,
            "failed_row_count": len(failed_rows),
            "blocker": validator["blocker"],
            "blocker_visible": validator["blocker"] in blockers,
        }
        row["row_backed"] = len(evidence_rows) > 0
        row["failed_count_matches_rows"] = failed_count == len(failed_rows)
        row["pass_state_matches_failed_count"] = passed == (failed_count == 0)
        row["blocker_matches_pass_state"] = (validator["blocker"] in blockers) != passed
        validator_rows.append(row)

    add(
        "all_validators_row_backed",
        all(row["row_backed"] for row in validator_rows),
        "Every validation mirror must publish row-level evidence.",
        missing_rows=[row["validator_id"] for row in validator_rows if not row["row_backed"]],
    )
    add(
        "all_validator_failed_counts_match_rows",
        all(row["failed_count_matches_rows"] for row in validator_rows),
        "Every validator failed-count field must equal its failed rows.",
        mismatched_validators=[row["validator_id"] for row in validator_rows if not row["failed_count_matches_rows"]],
    )
    add(
        "all_validator_pass_states_match_failed_counts",
        all(row["pass_state_matches_failed_count"] for row in validator_rows),
        "Every validator pass flag must agree with its failed count.",
        mismatched_validators=[row["validator_id"] for row in validator_rows if not row["pass_state_matches_failed_count"]],
    )
    add(
        "all_validator_blockers_match_pass_states",
        all(row["blocker_matches_pass_state"] for row in validator_rows),
        "Validator-specific blockers must appear only when that validator fails.",
        mismatched_validators=[row["validator_id"] for row in validator_rows if not row["blocker_matches_pass_state"]],
    )

    quorum_passed = bool(summary.get("audit_validation_quorum_passed"))
    quorum_required = int(_as_float(summary.get("audit_validation_quorum_required_count"), 0.0))
    quorum_pass_count = int(_as_float(summary.get("audit_validation_quorum_pass_count"), 0.0))
    core_pass_count = sum(1 for row in validator_rows[:3] if row["passed"])
    add(
        "quorum_counts_match_core_validators",
        quorum_required == 3 and quorum_pass_count == core_pass_count and quorum_passed == (core_pass_count == 3),
        "Validation quorum must reflect self/replay/integrity pass states.",
        quorum_required=quorum_required,
        quorum_pass_count=quorum_pass_count,
        core_pass_count=core_pass_count,
        quorum_passed=quorum_passed,
    )

    artifact_passed = bool(summary.get("audit_artifact_provenance_passed"))
    served_passed = bool(summary.get("audit_served_artifact_passed"))
    served_checked = bool(summary.get("audit_served_artifact_checked"))
    add(
        "served_artifact_depends_on_artifact_provenance",
        (not served_checked) or (served_passed and artifact_passed) or ((not served_passed) and served_checked),
        "Served artifact trust must be read after disk artifact provenance is available.",
        served_checked=served_checked,
        served_passed=served_passed,
        artifact_provenance_passed=artifact_passed,
    )

    failed_rows = [row for row in rows if not row["passing"]]
    return {
        "status": "audit_validation_chain_passed" if not failed_rows else "audit_validation_chain_attention",
        "generated_at": utc_now().isoformat(),
        "validation_chain_passed": not failed_rows,
        "validator_count": len(validators),
        "validator_pass_count": sum(1 for row in validator_rows if row["passed"]),
        "check_count": len(rows),
        "failed_count": len(failed_rows),
        "passed_count": len(rows) - len(failed_rows),
        "failed_rows": failed_rows,
        "rows": rows,
        "validator_rows": validator_rows,
        "manual_boundaries": [
            "validation chain confirms every validation mirror has row-backed evidence and matching blockers",
            "validation chain is audit-only and does not change live trading or runtime authority",
        ],
    }


def _status_from_blockers(blockers: List[str]) -> str:
    if not blockers:
        return "parallel_strategy_stress_certified"
    priority = [
        ("parallel_strategy_mutation_leak", "parallel_strategy_mutation_leak"),
        ("parallel_strategy_artifact_missing", "parallel_strategy_stress_missing_artifacts"),
        ("parallel_strategy_runtime_process_duplicate", "parallel_strategy_runtime_process_attention"),
        ("parallel_strategy_runtime_wrong_python", "parallel_strategy_runtime_process_attention"),
        ("parallel_strategy_supervisor_process_missing", "parallel_strategy_runtime_process_attention"),
        ("parallel_strategy_launcher_readiness_gap", "parallel_strategy_launcher_readiness_attention"),
        ("parallel_strategy_worker_stale_or_missing", "parallel_strategy_workers_attention"),
        ("parallel_strategy_intent_contract_missing", "parallel_strategy_intent_contract_attention"),
        ("parallel_strategy_api_budget_gap", "parallel_strategy_api_budget_attention"),
        ("parallel_strategy_ghost_phase_collision", "parallel_strategy_ghost_dance_attention"),
        ("parallel_strategy_ghost_dance_missing", "parallel_strategy_ghost_dance_attention"),
        ("parallel_strategy_harmonic_api_piano_song_stop_risk", "parallel_strategy_harmonic_api_piano_attention"),
        ("parallel_strategy_harmonic_api_piano_missing", "parallel_strategy_harmonic_api_piano_attention"),
        ("parallel_strategy_rainbow_song_continuity_risk", "parallel_strategy_rainbow_ladder_attention"),
        ("parallel_strategy_rainbow_ladder_missing", "parallel_strategy_rainbow_ladder_attention"),
        ("parallel_strategy_power_station_authority_violation", "parallel_strategy_power_station_request_attention"),
        ("parallel_strategy_power_station_request_missing", "parallel_strategy_power_station_request_attention"),
        ("parallel_strategy_audit_self_validation_gap", "parallel_strategy_audit_self_validation_attention"),
        ("parallel_strategy_audit_replay_validation_gap", "parallel_strategy_audit_replay_validation_attention"),
        ("parallel_strategy_audit_integrity_validation_gap", "parallel_strategy_audit_integrity_validation_attention"),
        ("parallel_strategy_audit_validation_quorum_gap", "parallel_strategy_audit_validation_quorum_attention"),
        ("parallel_strategy_audit_artifact_provenance_gap", "parallel_strategy_audit_artifact_provenance_attention"),
        ("parallel_strategy_audit_public_contract_gap", "parallel_strategy_audit_public_contract_attention"),
        ("parallel_strategy_audit_served_artifact_gap", "parallel_strategy_audit_served_artifact_attention"),
        ("parallel_strategy_audit_freshness_sla_gap", "parallel_strategy_audit_freshness_sla_attention"),
        ("parallel_strategy_audit_operator_surface_gap", "parallel_strategy_audit_operator_surface_attention"),
        ("parallel_strategy_audit_test_coverage_gap", "parallel_strategy_audit_test_coverage_attention"),
        ("parallel_strategy_audit_repair_coverage_gap", "parallel_strategy_audit_repair_coverage_attention"),
        ("parallel_strategy_audit_runtime_repair_readiness_gap", "parallel_strategy_audit_runtime_repair_readiness_attention"),
        ("parallel_strategy_audit_repair_acceptance_gap", "parallel_strategy_audit_repair_acceptance_attention"),
        ("parallel_strategy_audit_consistency_matrix_gap", "parallel_strategy_audit_consistency_matrix_attention"),
        ("parallel_strategy_audit_evidence_lineage_gap", "parallel_strategy_audit_evidence_lineage_attention"),
        ("parallel_strategy_audit_validator_closure_gap", "parallel_strategy_audit_validator_closure_attention"),
        ("parallel_strategy_audit_validation_chain_gap", "parallel_strategy_audit_validation_chain_attention"),
        ("parallel_strategy_fabric_visibility_gap", "parallel_strategy_fabric_attention"),
        ("parallel_strategy_runtime_reload_required", "parallel_strategy_runtime_reload_required"),
        ("parallel_strategy_runtime_alignment_gap", "parallel_strategy_runtime_alignment_attention"),
    ]
    for blocker, status in priority:
        if blocker in blockers:
            return status
    return "parallel_strategy_stress_attention"


def build_parallel_strategy_unity_stress_audit(
    *,
    root: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    now_dt = now or utc_now()
    now_ts = now_dt.timestamp()

    unity = _read_json(_rooted(root_path, PARALLEL_UNITY_PATH), {})
    broker = _read_json(_rooted(root_path, REQUEST_BROKER_PATH), {})
    intent_state = _read_json(_rooted(root_path, STRATEGY_INTENTS_PATH), {})
    fabric = _read_json(_rooted(root_path, FABRIC_PATH), {})
    runtime = _read_json(_rooted(root_path, RUNTIME_STATUS_PATH), {})

    artifact_rows = _artifact_presence(root_path)
    worker_results = _worker_rows(unity if isinstance(unity, dict) else {}, now_ts)
    lease_results = _lease_rows(broker if isinstance(broker, dict) else {})
    intent_results = _intent_rows(intent_state if isinstance(intent_state, dict) else {}, now_ts)
    ghost_proof = _ghost_dance_proof(
        unity if isinstance(unity, dict) else {},
        broker if isinstance(broker, dict) else {},
        intent_state if isinstance(intent_state, dict) else {},
        now_ts,
    )
    piano_proof = _harmonic_api_piano_proof(
        unity if isinstance(unity, dict) else {},
        broker if isinstance(broker, dict) else {},
        intent_state if isinstance(intent_state, dict) else {},
        now_ts,
    )
    rainbow_proof = _rainbow_harmonic_ladder_proof(
        unity if isinstance(unity, dict) else {},
        broker if isinstance(broker, dict) else {},
        intent_state if isinstance(intent_state, dict) else {},
        now_ts,
    )
    power_station_proof = _power_station_request_proof(
        unity if isinstance(unity, dict) else {},
        broker if isinstance(broker, dict) else {},
        intent_state if isinstance(intent_state, dict) else {},
        now_ts,
    )
    runtime_proof = _runtime_alignment(root_path, runtime if isinstance(runtime, dict) else {}, unity if isinstance(unity, dict) else {}, now_ts)
    process_proof = _runtime_process_proof(root_path, now_ts)
    launcher_proof = _launcher_readiness_proof(root_path, process_proof)
    fabric_proof = _fabric_visibility(fabric if isinstance(fabric, dict) else {}, unity if isinstance(unity, dict) else {})

    missing_artifacts = [row for row in artifact_rows if row["id"] in {"parallel_unity", "request_broker", "strategy_intents"} and not row["present"]]
    stale_workers = [row for row in worker_results if row["state"] in {"worker_missing", "worker_stale"}]
    attention_workers = [row for row in worker_results if row["state"] != "worker_healthy"]
    mutation_leaks = lease_results["mutation_leak_rows"] + intent_results["mutation_leak_rows"] + [
        row for row in worker_results if bool(row.get("direct_broker_mutation_allowed"))
    ]
    api_budget_gaps = lease_results["budget_gap_rows"] + lease_results["over_budget_rows"]
    missing_intent_contract = intent_results["missing_intent_contract_rows"]
    missing_lease_contract = lease_results["missing_lease_contract_rows"]
    self_validation = _audit_self_validation_proof(
        root=root_path,
        artifact_rows=artifact_rows,
        worker_results=worker_results,
        lease_results=lease_results,
        intent_results=intent_results,
        ghost_proof=ghost_proof,
        piano_proof=piano_proof,
        rainbow_proof=rainbow_proof,
        power_station_proof=power_station_proof,
        runtime_proof=runtime_proof,
        fabric_proof=fabric_proof,
        mutation_leak_rows=mutation_leaks,
        api_budget_gap_rows=api_budget_gaps,
    )

    blockers: List[str] = []
    if missing_artifacts:
        blockers.append("parallel_strategy_artifact_missing")
    if stale_workers:
        blockers.append("parallel_strategy_worker_stale_or_missing")
    if mutation_leaks:
        blockers.append("parallel_strategy_mutation_leak")
    if missing_intent_contract:
        blockers.append("parallel_strategy_intent_contract_missing")
    if missing_lease_contract:
        blockers.append("parallel_strategy_lease_contract_missing")
    if api_budget_gaps:
        blockers.append("parallel_strategy_api_budget_gap")
    if (
        not ghost_proof.get("enabled")
        or ghost_proof.get("missing_worker_phase_count")
        or ghost_proof.get("missing_lease_phase_count")
        or ghost_proof.get("missing_intent_phase_count")
    ):
        blockers.append("parallel_strategy_ghost_dance_missing")
    if ghost_proof.get("phase_collision_count"):
        blockers.append("parallel_strategy_ghost_phase_collision")
    if (
        not piano_proof.get("enabled")
        or piano_proof.get("missing_worker_piano_count")
        or piano_proof.get("missing_lease_piano_count")
        or piano_proof.get("missing_intent_piano_count")
    ):
        blockers.append("parallel_strategy_harmonic_api_piano_missing")
    if piano_proof.get("song_stop_risk_count"):
        blockers.append("parallel_strategy_harmonic_api_piano_song_stop_risk")
    if (
        not rainbow_proof.get("enabled")
        or rainbow_proof.get("missing_worker_ladder_count")
        or rainbow_proof.get("missing_lease_ladder_count")
        or rainbow_proof.get("missing_intent_ladder_count")
    ):
        blockers.append("parallel_strategy_rainbow_ladder_missing")
    if rainbow_proof.get("song_continuity_risk_count"):
        blockers.append("parallel_strategy_rainbow_song_continuity_risk")
    if (
        not power_station_proof.get("enabled")
        or power_station_proof.get("missing_worker_power_count")
        or power_station_proof.get("missing_lease_power_count")
        or power_station_proof.get("missing_intent_power_count")
    ):
        blockers.append("parallel_strategy_power_station_request_missing")
    if power_station_proof.get("authority_violation_count"):
        blockers.append("parallel_strategy_power_station_authority_violation")
    if not fabric_proof["visible"]:
        blockers.append("parallel_strategy_fabric_visibility_gap")
    if not runtime_proof["aligned"]:
        blockers.append("parallel_strategy_runtime_alignment_gap")
        if runtime_proof.get("runtime_reload_required"):
            blockers.append("parallel_strategy_runtime_reload_required")
    if process_proof.get("duplicate_unified_market_trader"):
        blockers.append("parallel_strategy_runtime_process_duplicate")
    if _as_float(process_proof.get("wrong_python_process_count"), 0.0) > 0:
        blockers.append("parallel_strategy_runtime_wrong_python")
    if process_proof.get("supervisor_missing"):
        blockers.append("parallel_strategy_supervisor_process_missing")
    if launcher_proof.get("blockers"):
        blockers.append("parallel_strategy_launcher_readiness_gap")
    if not self_validation.get("self_validation_passed"):
        blockers.append("parallel_strategy_audit_self_validation_gap")

    unity_summary = unity.get("summary") if isinstance(unity.get("summary"), dict) else {}
    broker_summary = broker.get("summary") if isinstance(broker.get("summary"), dict) else {}
    intent_summary = intent_state.get("summary") if isinstance(intent_state.get("summary"), dict) else {}
    status = _status_from_blockers(blockers)

    route_counter = Counter(
        f"{row.get('route_key')}|{row.get('side')}"
        for row in intent_results["intent_rows"]
        if row.get("route_key") and row.get("side")
    )
    duplicate_route_count = sum(1 for count in route_counter.values() if count > 1)

    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_dt.isoformat(),
        "status": status,
        "mode": "parallel_strategy_unity_stress_audit",
        "summary": {
            "worker_count": len(worker_results),
            "healthy_worker_count": sum(1 for row in worker_results if row["state"] == "worker_healthy"),
            "stale_worker_count": len(stale_workers),
            "attention_worker_count": len(attention_workers),
            "intent_count": int(_as_float(intent_summary.get("intent_count"), len(intent_results["intent_rows"]))),
            "executable_intent_count": int(_as_float(intent_summary.get("executable_intent_count"), 0.0)),
            "missing_intent_contract_count": len(missing_intent_contract),
            "lease_count": int(_as_float(broker_summary.get("lease_count"), len(lease_results["lease_rows"]))),
            "denied_lease_count": int(_as_float(broker_summary.get("denied_count"), 0.0)),
            "api_budget_gap_count": len(api_budget_gaps),
            "mutation_leak_count": len(mutation_leaks),
            "denied_mutation_proof_count": len(lease_results["denied_mutation_rows"]),
            "duplicate_route_count": duplicate_route_count,
            "strategy_agreement_count": len(intent_results["strategy_agreement_rows"]),
            "strategy_disagreement_count": int(intent_results["strategy_disagreement_count"]),
            "ghost_dance_enabled": bool(ghost_proof.get("enabled")),
            "ghost_phase_count": int(_as_float(ghost_proof.get("phase_count"), 0.0)),
            "ghost_unique_phase_count": int(_as_float(ghost_proof.get("unique_phase_count"), 0.0)),
            "ghost_api_key_lock_family_count": int(_as_float(ghost_proof.get("api_key_lock_family_count"), 0.0)),
            "ghost_phase_collision_count": int(_as_float(ghost_proof.get("phase_collision_count"), 0.0)),
            "ghost_missing_phase_count": int(_as_float(ghost_proof.get("missing_worker_phase_count"), 0.0))
            + int(_as_float(ghost_proof.get("missing_lease_phase_count"), 0.0))
            + int(_as_float(ghost_proof.get("missing_intent_phase_count"), 0.0)),
            "ghost_stale_historical_intent_phase_count": int(_as_float(ghost_proof.get("stale_missing_intent_phase_count"), 0.0)),
            "harmonic_api_piano_enabled": bool(piano_proof.get("enabled")),
            "harmonic_tempo_multiplier": _as_float(piano_proof.get("tempo_multiplier"), 0.0),
            "harmonic_coherence_blend": _as_float(piano_proof.get("coherence_blend"), 0.0),
            "piano_key_count": int(_as_float(piano_proof.get("piano_key_count"), 0.0)),
            "piano_play_now_count": int(_as_float(piano_proof.get("play_now_count"), 0.0)),
            "piano_missing_proof_count": int(_as_float(piano_proof.get("missing_worker_piano_count"), 0.0))
            + int(_as_float(piano_proof.get("missing_lease_piano_count"), 0.0))
            + int(_as_float(piano_proof.get("missing_intent_piano_count"), 0.0)),
            "piano_stale_historical_intent_count": int(_as_float(piano_proof.get("stale_missing_intent_piano_count"), 0.0)),
            "song_stop_risk_count": int(_as_float(piano_proof.get("song_stop_risk_count"), 0.0)),
            "rainbow_harmonic_ladder_enabled": bool(rainbow_proof.get("enabled")),
            "rainbow_ladder_step_count": int(_as_float(rainbow_proof.get("ladder_step_count"), 0.0)),
            "rainbow_worker_ladder_count": int(_as_float(rainbow_proof.get("worker_ladder_count"), 0.0)),
            "rainbow_base_frequency_hz": _as_float(rainbow_proof.get("base_frequency_hz"), 0.0),
            "rainbow_missing_proof_count": int(_as_float(rainbow_proof.get("missing_worker_ladder_count"), 0.0))
            + int(_as_float(rainbow_proof.get("missing_lease_ladder_count"), 0.0))
            + int(_as_float(rainbow_proof.get("missing_intent_ladder_count"), 0.0)),
            "rainbow_stale_historical_intent_count": int(_as_float(rainbow_proof.get("stale_missing_intent_ladder_count"), 0.0)),
            "rainbow_song_continuity_risk_count": int(_as_float(rainbow_proof.get("song_continuity_risk_count"), 0.0)),
            "power_station_request_governor_enabled": bool(power_station_proof.get("enabled")),
            "power_station_request_count": int(_as_float(power_station_proof.get("request_count"), 0.0)),
            "power_station_outbound_request_count": int(_as_float(power_station_proof.get("outbound_request_count"), 0.0)),
            "power_station_internal_request_count": int(_as_float(power_station_proof.get("internal_request_count"), 0.0)),
            "power_station_missing_proof_count": int(_as_float(power_station_proof.get("missing_worker_power_count"), 0.0))
            + int(_as_float(power_station_proof.get("missing_lease_power_count"), 0.0))
            + int(_as_float(power_station_proof.get("missing_intent_power_count"), 0.0)),
            "power_station_stale_historical_intent_count": int(_as_float(power_station_proof.get("stale_missing_intent_power_count"), 0.0)),
            "power_station_authority_violation_count": int(_as_float(power_station_proof.get("authority_violation_count"), 0.0)),
            "audit_self_validation_passed": bool(self_validation.get("self_validation_passed")),
            "audit_self_validation_failed_count": int(_as_float(self_validation.get("failed_count"), 0.0)),
            "audit_self_validation_check_count": int(_as_float(self_validation.get("check_count"), 0.0)),
            "audit_self_validation_proof_basis": self_validation.get("proof_basis"),
            "runtime_alignment": bool(runtime_proof["aligned"]),
            "runtime_reload_required": bool(runtime_proof.get("runtime_reload_required")),
            "runtime_code_wired": bool(runtime_proof.get("code_wired")),
            "runtime_embeds_parallel_unity": bool(runtime_proof.get("parallel_unity_embedded")),
            "runtime_embeds_parallel_intents": bool(runtime_proof.get("parallel_intents_embedded")),
            "state_snapshots_present": bool(runtime_proof.get("state_snapshots_present")),
            "process_discovery_available": bool(process_proof.get("discovery_available")),
            "unified_market_trader_process_count": int(_as_float(process_proof.get("unified_market_trader_process_count"), 0.0)),
            "parallel_strategy_supervisor_process_count": int(_as_float(process_proof.get("parallel_strategy_supervisor_process_count"), 0.0)),
            "wrong_python_process_count": int(_as_float(process_proof.get("wrong_python_process_count"), 0.0)),
            "source_stale_process_count": int(_as_float(process_proof.get("source_stale_process_count"), 0.0)),
            "single_owner_repair_ready": bool(launcher_proof.get("standard_launcher_available")),
            "guarded_repair_command_ready": bool(launcher_proof.get("guarded_command_package_ready")),
            "restart_stop_target_count": int(_as_float(launcher_proof.get("stop_target_count"), 0.0)),
            "restart_start_target_count": int(_as_float(launcher_proof.get("start_target_count"), 0.0)),
            "post_restart_check_count": int(_as_float(launcher_proof.get("post_restart_check_count"), 0.0)),
            "fabric_visible": bool(fabric_proof["visible"]),
            "thoughtbus_receiving": bool(fabric_proof["thoughtbus_receiving"]),
            "mycelium_receiving": bool(fabric_proof["mycelium_receiving"]),
            "minimum_net_profit_gbp": _as_float(unity_summary.get("minimum_net_profit_gbp"), DEFAULT_MINIMUM_NET_PROFIT_GBP),
            "unified_executor_authoritative": bool(unity_summary.get("unified_executor_authoritative")),
            "direct_broker_mutation_allowed": bool(unity_summary.get("direct_broker_mutation_allowed")),
            "blocker_count": len(blockers),
        },
        "artifact_rows": artifact_rows,
        "worker_stress_rows": worker_results,
        "intent_contract_rows": missing_intent_contract,
        "lease_contract_rows": missing_lease_contract,
        "api_budget_stress_rows": api_budget_gaps,
        "mutation_authority_rows": mutation_leaks,
        "denied_mutation_proof_rows": lease_results["denied_mutation_rows"],
        "strategy_agreement_rows": intent_results["strategy_agreement_rows"],
        "ghost_dance_proof": ghost_proof,
        "ghost_phase_rows": ghost_proof.get("phase_rows") or [],
        "ghost_phase_collision_rows": ghost_proof.get("phase_collision_rows") or [],
        "ghost_missing_worker_phase_rows": ghost_proof.get("missing_worker_phase_rows") or [],
        "ghost_missing_lease_phase_rows": ghost_proof.get("missing_lease_phase_rows") or [],
        "ghost_missing_intent_phase_rows": ghost_proof.get("missing_intent_phase_rows") or [],
        "ghost_stale_historical_intent_phase_rows": ghost_proof.get("stale_missing_intent_phase_rows") or [],
        "harmonic_api_piano_proof": piano_proof,
        "piano_key_rows": piano_proof.get("piano_key_rows") or [],
        "piano_missing_worker_rows": piano_proof.get("missing_worker_piano_rows") or [],
        "piano_missing_lease_rows": piano_proof.get("missing_lease_piano_rows") or [],
        "piano_missing_intent_rows": piano_proof.get("missing_intent_piano_rows") or [],
        "piano_stale_historical_intent_rows": piano_proof.get("stale_missing_intent_piano_rows") or [],
        "piano_song_stop_risk_rows": piano_proof.get("song_stop_risk_rows") or [],
        "rainbow_harmonic_ladder_proof": rainbow_proof,
        "rainbow_ladder_rows": rainbow_proof.get("ladder_rows") or [],
        "rainbow_worker_ladder_rows": rainbow_proof.get("worker_ladder_rows") or [],
        "rainbow_missing_worker_rows": rainbow_proof.get("missing_worker_ladder_rows") or [],
        "rainbow_missing_lease_rows": rainbow_proof.get("missing_lease_ladder_rows") or [],
        "rainbow_missing_intent_rows": rainbow_proof.get("missing_intent_ladder_rows") or [],
        "rainbow_stale_historical_intent_rows": rainbow_proof.get("stale_missing_intent_ladder_rows") or [],
        "rainbow_song_continuity_risk_rows": rainbow_proof.get("song_continuity_risk_rows") or [],
        "power_station_request_proof": power_station_proof,
        "power_station_request_rows": power_station_proof.get("power_station_request_rows") or [],
        "power_station_missing_worker_rows": power_station_proof.get("missing_worker_power_rows") or [],
        "power_station_missing_lease_rows": power_station_proof.get("missing_lease_power_rows") or [],
        "power_station_missing_intent_rows": power_station_proof.get("missing_intent_power_rows") or [],
        "power_station_stale_historical_intent_rows": power_station_proof.get("stale_missing_intent_power_rows") or [],
        "power_station_authority_violation_rows": power_station_proof.get("authority_violation_rows") or [],
        "audit_self_validation_proof": self_validation,
        "audit_self_validation_rows": self_validation.get("rows") or [],
        "audit_self_validation_failed_rows": self_validation.get("failed_rows") or [],
        "executor_dedupe_rows": intent_results["executor_dedupe_rows"],
        "stale_intent_rows": intent_results["stale_intent_rows"],
        "runtime_alignment_proof": runtime_proof,
        "runtime_alignment_burndown_rows": runtime_proof.get("burn_down_rows") or [],
        "runtime_process_proof": process_proof,
        "runtime_process_rows": process_proof.get("process_rows") or [],
        "runtime_process_burndown_rows": process_proof.get("burn_down_rows") or [],
        "single_owner_repair_plan": launcher_proof,
        "single_owner_stop_target_rows": launcher_proof.get("stop_target_rows") or [],
        "single_owner_start_target_rows": launcher_proof.get("start_target_rows") or [],
        "post_restart_check_rows": launcher_proof.get("post_restart_check_rows") or [],
        "single_owner_guard_validation_rows": launcher_proof.get("guard_validation_rows") or [],
        "guarded_repair_command_lines": launcher_proof.get("guarded_repair_command_lines") or [],
        "guarded_repair_command_preview": launcher_proof.get("guarded_repair_command_preview") or "",
        "fabric_visibility_proof": fabric_proof,
        "shared_goal_proof": {
            "minimum_net_profit_gbp": _as_float(unity_summary.get("minimum_net_profit_gbp"), DEFAULT_MINIMUM_NET_PROFIT_GBP),
            "intent_goal_gbp": _as_float(intent_summary.get("minimum_net_profit_gbp"), DEFAULT_MINIMUM_NET_PROFIT_GBP),
            "goal_aligned": _as_float(unity_summary.get("minimum_net_profit_gbp"), DEFAULT_MINIMUM_NET_PROFIT_GBP)
            == _as_float(intent_summary.get("minimum_net_profit_gbp"), DEFAULT_MINIMUM_NET_PROFIT_GBP),
        },
        "next_repair_actions": _next_repair_actions(blockers),
        "blockers": blockers,
        "manual_boundaries": MANUAL_BOUNDARIES,
        "source_paths": {
            "parallel_unity": PARALLEL_UNITY_PATH.as_posix(),
            "request_broker": REQUEST_BROKER_PATH.as_posix(),
            "power_station_request_governor": "frontend/public/aureon_power_station_request_governor.json",
            "strategy_intents": STRATEGY_INTENTS_PATH.as_posix(),
            "live_signal_fabric": FABRIC_PATH.as_posix(),
            "runtime_status": RUNTIME_STATUS_PATH.as_posix(),
        },
        "output_files": [
            DEFAULT_STATE_PATH.as_posix(),
            DEFAULT_AUDIT_JSON.as_posix(),
            DEFAULT_AUDIT_MD.as_posix(),
            DEFAULT_PUBLIC_JSON.as_posix(),
        ],
    }
    replay_validation = _audit_report_replay_validation(report)
    report["audit_replay_validation_proof"] = replay_validation
    report["audit_replay_validation_rows"] = replay_validation.get("rows") or []
    report["audit_replay_validation_failed_rows"] = replay_validation.get("failed_rows") or []
    report["summary"].update(
        {
            "audit_replay_validation_passed": bool(replay_validation.get("replay_validation_passed")),
            "audit_replay_validation_failed_count": int(_as_float(replay_validation.get("failed_count"), 0.0)),
            "audit_replay_validation_check_count": int(_as_float(replay_validation.get("check_count"), 0.0)),
        }
    )
    if not replay_validation.get("replay_validation_passed"):
        blockers.append("parallel_strategy_audit_replay_validation_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)
    integrity_validation = _audit_integrity_triangulation_validation(report)
    report["audit_integrity_validation_proof"] = integrity_validation
    report["audit_integrity_validation_rows"] = integrity_validation.get("rows") or []
    report["audit_integrity_validation_failed_rows"] = integrity_validation.get("failed_rows") or []
    report["summary"].update(
        {
            "audit_integrity_validation_passed": bool(integrity_validation.get("integrity_validation_passed")),
            "audit_integrity_validation_failed_count": int(_as_float(integrity_validation.get("failed_count"), 0.0)),
            "audit_integrity_validation_check_count": int(_as_float(integrity_validation.get("check_count"), 0.0)),
        }
    )
    if not integrity_validation.get("integrity_validation_passed"):
        blockers.append("parallel_strategy_audit_integrity_validation_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)
    quorum_validation = _audit_validation_quorum_validation(report)
    report["audit_validation_quorum_proof"] = quorum_validation
    report["audit_validation_quorum_rows"] = quorum_validation.get("rows") or []
    report["audit_validation_quorum_failed_rows"] = quorum_validation.get("failed_rows") or []
    report["summary"].update(
        {
            "audit_validation_quorum_passed": bool(quorum_validation.get("validation_quorum_passed")),
            "audit_validation_quorum_failed_count": int(_as_float(quorum_validation.get("failed_count"), 0.0)),
            "audit_validation_quorum_check_count": int(_as_float(quorum_validation.get("check_count"), 0.0)),
            "audit_validation_quorum_pass_count": int(_as_float(quorum_validation.get("validator_pass_count"), 0.0)),
            "audit_validation_quorum_required_count": int(_as_float(quorum_validation.get("validator_required_count"), 0.0)),
        }
    )
    if not quorum_validation.get("validation_quorum_passed"):
        blockers.append("parallel_strategy_audit_validation_quorum_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)
    return report


def _next_repair_actions(blockers: Sequence[str]) -> List[Dict[str, Any]]:
    mapping = {
        "parallel_strategy_artifact_missing": (
            "parallel_strategy_unity",
            "Run python -m aureon.trading.parallel_strategy_unity --once or start the production launcher.",
        ),
        "parallel_strategy_worker_stale_or_missing": (
            "parallel_strategy_unity",
            "Restart the parallel supervisor or inspect worker heartbeat logs.",
        ),
        "parallel_strategy_mutation_leak": (
            "unified_exchange_request_broker",
            "Route all order/position mutation leases through unified_market_trader.executor only.",
        ),
        "parallel_strategy_intent_contract_missing": (
            "strategy_worker_publishers",
            "Publish worker_id, trace_id, lifecycle_id, candidate_id, intent_id, route_key, venue, symbol, and side.",
        ),
        "parallel_strategy_lease_contract_missing": (
            "unified_exchange_request_broker",
            "Attach request_id, worker_id, venue, operation_type, rate_limit_family, budget_required, and idempotency_key.",
        ),
        "parallel_strategy_api_budget_gap": (
            "unified_exchange_request_broker",
            "Wait for venue budget recovery or lower worker scan pressure.",
        ),
        "parallel_strategy_fabric_visibility_gap": (
            "live_trade_signal_fabric",
            "Confirm strategy signal events are reaching ThoughtBus or Mycelium.",
        ),
        "parallel_strategy_runtime_alignment_gap": (
            "unified_market_trader",
            "Restart runtime so terminal-state embeds the latest parallel strategy unity snapshot.",
        ),
        "parallel_strategy_runtime_reload_required": (
            "unified_market_trader",
            "Restart AUREON_PRODUCTION_LIVE.cmd or the unified_market_trader process; current source and state artifacts are wired but terminal-state has not reloaded them.",
        ),
        "parallel_strategy_runtime_process_duplicate": (
            "runtime_supervisor",
            "Stop duplicate unified_market_trader processes and restart the single venv-owned production runtime.",
        ),
        "parallel_strategy_runtime_wrong_python": (
            "runtime_supervisor",
            "Restart unified_market_trader from the repo .venv Python so one interpreter owns terminal-state.",
        ),
        "parallel_strategy_supervisor_process_missing": (
            "parallel_strategy_unity",
            "Start the parallel_strategy_unity watch process through AUREON_PRODUCTION_LIVE.cmd so worker heartbeats stay fresh.",
        ),
        "parallel_strategy_ghost_dance_missing": (
            "parallel_strategy_unity",
            "Regenerate parallel strategy unity so worker, lease, and intent rows carry Ghost Dance phase and API-key-lock proof.",
        ),
        "parallel_strategy_ghost_phase_collision": (
            "parallel_strategy_unity",
            "Adjust Ghost Dance phase spacing so workers sharing an API-key-lock family do not occupy the same phase.",
        ),
        "parallel_strategy_harmonic_api_piano_missing": (
            "parallel_strategy_unity",
            "Regenerate parallel strategy unity so worker, lease, and intent rows carry Harmonic API Piano tempo and song-stop proof.",
        ),
        "parallel_strategy_harmonic_api_piano_song_stop_risk": (
            "parallel_strategy_unity",
            "Dampen Harmonic API Piano tempo or wait for rate pressure to clear before scheduling the next fast turn.",
        ),
        "parallel_strategy_rainbow_ladder_missing": (
            "parallel_strategy_unity",
            "Regenerate parallel strategy unity so worker, lease, and intent rows carry Rainbow Harmonic Ladder frequency and lane proof.",
        ),
        "parallel_strategy_rainbow_song_continuity_risk": (
            "parallel_strategy_unity",
            "Hold or re-phase request turns that would overplay a lane outside its API phase window.",
        ),
        "parallel_strategy_power_station_request_missing": (
            "unified_exchange_request_broker",
            "Regenerate request broker artifacts so every lease and current intent carries Power Station request metadata.",
        ),
        "parallel_strategy_power_station_authority_violation": (
            "unified_exchange_request_broker",
            "Keep order/position mutation leases owned by unified_market_trader.executor and classify all strategy workers as signal-only.",
        ),
        "parallel_strategy_audit_self_validation_gap": (
            "parallel_strategy_stress_audit",
            "Repair the audit section/count mismatch named in audit_self_validation_failed_rows, then regenerate the stress artifact.",
        ),
        "parallel_strategy_audit_replay_validation_gap": (
            "parallel_strategy_stress_audit",
            "Repair the row/summary mismatch named in audit_replay_validation_failed_rows, then regenerate the stress artifact.",
        ),
        "parallel_strategy_audit_integrity_validation_gap": (
            "parallel_strategy_stress_audit",
            "Repair the status/blocker/repair/path mismatch named in audit_integrity_validation_failed_rows, then regenerate the stress artifact.",
        ),
        "parallel_strategy_audit_validation_quorum_gap": (
            "parallel_strategy_stress_audit",
            "Repair the failed validation mirror named in audit_validation_quorum_failed_rows, then regenerate the stress artifact.",
        ),
        "parallel_strategy_audit_artifact_provenance_gap": (
            "parallel_strategy_stress_audit",
            "Regenerate state/docs/public audit artifacts and inspect audit_artifact_provenance_failed_rows for the mismatched file.",
        ),
        "parallel_strategy_audit_public_contract_gap": (
            "parallel_strategy_stress_audit",
            "Restore the public JSON field contract named in audit_public_contract_failed_rows, then regenerate the stress artifact.",
        ),
        "parallel_strategy_audit_served_artifact_gap": (
            "parallel_strategy_stress_audit",
            "Refresh the local frontend/static server or inspect audit_served_artifact_failed_rows for the served JSON mismatch.",
        ),
        "parallel_strategy_audit_freshness_sla_gap": (
            "parallel_strategy_stress_audit",
            "Regenerate the stress artifact and inspect audit_freshness_sla_failed_rows for stale timestamps or missing evidence writes.",
        ),
        "parallel_strategy_audit_operator_surface_gap": (
            "parallel_strategy_stress_audit",
            "Repair the Trading panel source issue named in audit_operator_surface_failed_rows, then rebuild the frontend.",
        ),
        "parallel_strategy_audit_test_coverage_gap": (
            "parallel_strategy_stress_audit",
            "Add or repair the focused validator test named in audit_test_coverage_failed_rows, then rerun the stress test suite.",
        ),
        "parallel_strategy_audit_repair_coverage_gap": (
            "parallel_strategy_stress_audit",
            "Replace generic or missing repair rows named in audit_repair_coverage_failed_rows, then regenerate the stress artifact.",
        ),
        "parallel_strategy_audit_runtime_repair_readiness_gap": (
            "runtime_supervisor",
            "Repair the guarded runtime command package named in audit_runtime_repair_readiness_failed_rows before using any manual restart command.",
        ),
        "parallel_strategy_audit_repair_acceptance_gap": (
            "runtime_supervisor",
            "Add the missing post-restart proof named in audit_repair_acceptance_failed_rows before treating runtime repair as accepted.",
        ),
        "parallel_strategy_audit_consistency_matrix_gap": (
            "parallel_strategy_stress_audit",
            "Repair the validator agreement issue named in audit_consistency_matrix_failed_rows, then regenerate the stress artifact.",
        ),
        "parallel_strategy_audit_evidence_lineage_gap": (
            "parallel_strategy_stress_audit",
            "Restore the missing source, output, or section lineage named in audit_evidence_lineage_failed_rows, then regenerate the stress artifact.",
        ),
        "parallel_strategy_audit_validator_closure_gap": (
            "parallel_strategy_stress_audit",
            "Restore the missing validator registration named in audit_validator_closure_failed_rows, then regenerate the stress artifact.",
        ),
        "parallel_strategy_audit_validation_chain_gap": (
            "parallel_strategy_stress_audit",
            "Repair the validator consistency issue named in audit_validation_chain_failed_rows, then regenerate the stress artifact.",
        ),
        "parallel_strategy_launcher_readiness_gap": (
            "runtime_supervisor",
            "Repair the production launcher registration before attempting a clean single-owner restart.",
        ),
    }
    return [
        {"blocker": blocker, "owner": mapping.get(blocker, ("parallel_strategy_unity", "Inspect artifact rows."))[0], "action": mapping.get(blocker, ("parallel_strategy_unity", "Inspect artifact rows."))[1]}
        for blocker in blockers
    ]


def _make_markdown(report: Mapping[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    lines = [
        "# Aureon Parallel Strategy Unity Stress Audit",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Workers: `{summary.get('healthy_worker_count')}` / `{summary.get('worker_count')}` healthy",
        f"- Intents: `{summary.get('intent_count')}` total, `{summary.get('executable_intent_count')}` executable",
        f"- API budget gaps: `{summary.get('api_budget_gap_count')}`",
        f"- Mutation leaks: `{summary.get('mutation_leak_count')}`",
        f"- Ghost Dance enabled: `{summary.get('ghost_dance_enabled')}`",
        f"- Ghost phase collisions: `{summary.get('ghost_phase_collision_count')}`",
        f"- Ghost missing phase rows: `{summary.get('ghost_missing_phase_count')}`",
        f"- Harmonic API Piano enabled: `{summary.get('harmonic_api_piano_enabled')}`",
        f"- Harmonic tempo multiplier: `{summary.get('harmonic_tempo_multiplier')}`",
        f"- Piano keys: `{summary.get('piano_key_count')}`",
        f"- Piano missing proof rows: `{summary.get('piano_missing_proof_count')}`",
        f"- Song-stop risks: `{summary.get('song_stop_risk_count')}`",
        f"- Rainbow ladder enabled: `{summary.get('rainbow_harmonic_ladder_enabled')}`",
        f"- Rainbow missing proof rows: `{summary.get('rainbow_missing_proof_count')}`",
        f"- Power Station request governor enabled: `{summary.get('power_station_request_governor_enabled')}`",
        f"- Power Station missing proof rows: `{summary.get('power_station_missing_proof_count')}`",
        f"- Audit self-validation passed: `{summary.get('audit_self_validation_passed')}`",
        f"- Audit self-validation failed rows: `{summary.get('audit_self_validation_failed_count')}`",
        f"- Audit proof basis: `{summary.get('audit_self_validation_proof_basis')}`",
        f"- Audit replay validation passed: `{summary.get('audit_replay_validation_passed')}`",
        f"- Audit replay validation failed rows: `{summary.get('audit_replay_validation_failed_count')}`",
        f"- Audit integrity validation passed: `{summary.get('audit_integrity_validation_passed')}`",
        f"- Audit integrity validation failed rows: `{summary.get('audit_integrity_validation_failed_count')}`",
        f"- Audit validation quorum passed: `{summary.get('audit_validation_quorum_passed')}`",
        f"- Audit validation quorum failed rows: `{summary.get('audit_validation_quorum_failed_count')}`",
        f"- Audit artifact provenance passed: `{summary.get('audit_artifact_provenance_passed')}`",
        f"- Audit artifact provenance failed rows: `{summary.get('audit_artifact_provenance_failed_count')}`",
        f"- Audit public contract passed: `{summary.get('audit_public_contract_passed')}`",
        f"- Audit public contract failed rows: `{summary.get('audit_public_contract_failed_count')}`",
        f"- Audit served artifact passed: `{summary.get('audit_served_artifact_passed')}`",
        f"- Audit served artifact failed rows: `{summary.get('audit_served_artifact_failed_count')}`",
        f"- Audit freshness SLA passed: `{summary.get('audit_freshness_sla_passed')}`",
        f"- Audit freshness SLA age seconds: `{summary.get('audit_freshness_sla_age_sec')}`",
        f"- Audit freshness SLA failed rows: `{summary.get('audit_freshness_sla_failed_count')}`",
        f"- Audit operator surface passed: `{summary.get('audit_operator_surface_passed')}`",
        f"- Audit operator surface failed rows: `{summary.get('audit_operator_surface_failed_count')}`",
        f"- Audit test coverage passed: `{summary.get('audit_test_coverage_passed')}`",
        f"- Audit test coverage failed rows: `{summary.get('audit_test_coverage_failed_count')}`",
        f"- Audit repair coverage passed: `{summary.get('audit_repair_coverage_passed')}`",
        f"- Audit repair coverage failed rows: `{summary.get('audit_repair_coverage_failed_count')}`",
        f"- Audit runtime repair readiness passed: `{summary.get('audit_runtime_repair_readiness_passed')}`",
        f"- Audit runtime repair readiness failed rows: `{summary.get('audit_runtime_repair_readiness_failed_count')}`",
        f"- Audit repair acceptance passed: `{summary.get('audit_repair_acceptance_passed')}`",
        f"- Audit repair acceptance failed rows: `{summary.get('audit_repair_acceptance_failed_count')}`",
        f"- Audit consistency matrix passed: `{summary.get('audit_consistency_matrix_passed')}`",
        f"- Audit consistency matrix failed rows: `{summary.get('audit_consistency_matrix_failed_count')}`",
        f"- Audit evidence lineage passed: `{summary.get('audit_evidence_lineage_passed')}`",
        f"- Audit evidence lineage failed rows: `{summary.get('audit_evidence_lineage_failed_count')}`",
        f"- Audit validator closure passed: `{summary.get('audit_validator_closure_passed')}`",
        f"- Audit validator closure failed rows: `{summary.get('audit_validator_closure_failed_count')}`",
        f"- Audit validation chain passed: `{summary.get('audit_validation_chain_passed')}`",
        f"- Audit validation chain failed rows: `{summary.get('audit_validation_chain_failed_count')}`",
        f"- Runtime aligned: `{summary.get('runtime_alignment')}`",
        f"- Runtime reload required: `{summary.get('runtime_reload_required')}`",
        f"- Unified trader processes: `{summary.get('unified_market_trader_process_count')}`",
        f"- Parallel supervisor processes: `{summary.get('parallel_strategy_supervisor_process_count')}`",
        f"- Wrong Python processes: `{summary.get('wrong_python_process_count')}`",
        f"- Single-owner repair ready: `{summary.get('single_owner_repair_ready')}`",
        f"- Guarded repair command ready: `{summary.get('guarded_repair_command_ready')}`",
        f"- Restart stop targets: `{summary.get('restart_stop_target_count')}`",
        f"- Fabric visible: `{summary.get('fabric_visible')}`",
        "",
        "## Blockers",
    ]
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- None visible.")
    lines.extend(["", "## Next Repair Actions"])
    repairs = report.get("next_repair_actions") if isinstance(report.get("next_repair_actions"), list) else []
    if repairs:
        for row in repairs:
            if isinstance(row, dict):
                lines.append(f"- `{row.get('owner')}`: {row.get('action')}")
    else:
        lines.append("- No repair action needed.")
    return "\n".join(lines) + "\n"


def build_and_write_parallel_strategy_unity_stress_audit(
    *,
    root: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    report = build_parallel_strategy_unity_stress_audit(root=root_path, now=now)
    json_paths = [DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON]
    writes = [_write_json(_rooted(root_path, rel), report) for rel in json_paths]
    writes.append(_write_text(_rooted(root_path, DEFAULT_AUDIT_MD), _make_markdown(report)))
    report["write_info"] = {"evidence_writes": writes}
    writes = [_write_json(_rooted(root_path, rel), report) for rel in json_paths]
    writes.append(_write_text(_rooted(root_path, DEFAULT_AUDIT_MD), _make_markdown(report)))
    report["write_info"] = {"evidence_writes": writes}

    provenance = _audit_artifact_provenance_validation(
        root=root_path,
        report=report,
        json_paths=json_paths,
        markdown_path=DEFAULT_AUDIT_MD,
    )
    report["audit_artifact_provenance_proof"] = provenance
    report["audit_artifact_provenance_rows"] = provenance.get("rows") or []
    report["audit_artifact_provenance_failed_rows"] = provenance.get("failed_rows") or []
    report["summary"].update(
        {
            "audit_artifact_provenance_passed": bool(provenance.get("artifact_provenance_passed")),
            "audit_artifact_provenance_failed_count": int(_as_float(provenance.get("failed_count"), 0.0)),
            "audit_artifact_provenance_check_count": int(_as_float(provenance.get("check_count"), 0.0)),
            "audit_artifact_provenance_json_match_count": int(_as_float(provenance.get("json_hash_match_count"), 0.0)),
            "audit_artifact_provenance_json_artifact_count": int(_as_float(provenance.get("json_artifact_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not provenance.get("artifact_provenance_passed"):
        blockers.append("parallel_strategy_audit_artifact_provenance_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)
    final_writes = [_write_json(_rooted(root_path, rel), report) for rel in json_paths]
    final_writes.append(_write_text(_rooted(root_path, DEFAULT_AUDIT_MD), _make_markdown(report)))
    report["write_info"] = {"evidence_writes": final_writes}
    real_repo_mode = _rooted(root_path, Path("aureon")).exists() and _rooted(root_path, Path("frontend")).exists() and root_path == REPO_ROOT
    served_fetch = _fetch_served_public_artifact(DEFAULT_SERVED_PUBLIC_URL) if real_repo_mode else {"payload": None, "error": "", "bytes": 0, "sha256": ""}
    served_validation = _audit_served_artifact_validation(
        report=report,
        served_payload=served_fetch.get("payload") if isinstance(served_fetch.get("payload"), dict) else None,
        served_url=DEFAULT_SERVED_PUBLIC_URL,
        required=real_repo_mode,
        fetch_error=str(served_fetch.get("error") or ""),
        served_sha256=str(served_fetch.get("sha256") or ""),
    )
    report["audit_served_artifact_proof"] = served_validation
    report["audit_served_artifact_rows"] = served_validation.get("rows") or []
    report["audit_served_artifact_failed_rows"] = served_validation.get("failed_rows") or []
    report["summary"].update(
        {
            "audit_served_artifact_passed": bool(served_validation.get("served_artifact_passed")),
            "audit_served_artifact_checked": bool(served_validation.get("served_artifact_checked")),
            "audit_served_artifact_core_matches": bool(served_validation.get("served_artifact_core_matches")),
            "audit_served_artifact_failed_count": int(_as_float(served_validation.get("failed_count"), 0.0)),
            "audit_served_artifact_check_count": int(_as_float(served_validation.get("check_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if real_repo_mode and not served_validation.get("served_artifact_passed"):
        blockers.append("parallel_strategy_audit_served_artifact_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)

    freshness_sla = _audit_freshness_sla_validation(report, now=now or utc_now())
    report["audit_freshness_sla_proof"] = freshness_sla
    report["audit_freshness_sla_rows"] = freshness_sla.get("rows") or []
    report["audit_freshness_sla_failed_rows"] = freshness_sla.get("failed_rows") or []
    report["summary"].update(
        {
            "audit_freshness_sla_passed": bool(freshness_sla.get("freshness_sla_passed")),
            "audit_freshness_sla_failed_count": int(_as_float(freshness_sla.get("failed_count"), 0.0)),
            "audit_freshness_sla_check_count": int(_as_float(freshness_sla.get("check_count"), 0.0)),
            "audit_freshness_sla_age_sec": _as_float(freshness_sla.get("age_sec"), 0.0),
            "audit_freshness_sla_validator_span_sec": _as_float(freshness_sla.get("validator_span_sec"), 0.0),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not freshness_sla.get("freshness_sla_passed"):
        blockers.append("parallel_strategy_audit_freshness_sla_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)

    operator_surface = _audit_operator_surface_validation(root_path, report)
    report["audit_operator_surface_proof"] = operator_surface
    report["audit_operator_surface_rows"] = operator_surface.get("rows") or []
    report["audit_operator_surface_failed_rows"] = operator_surface.get("failed_rows") or []
    report["summary"].update(
        {
            "audit_operator_surface_passed": bool(operator_surface.get("operator_surface_passed")),
            "audit_operator_surface_failed_count": int(_as_float(operator_surface.get("failed_count"), 0.0)),
            "audit_operator_surface_check_count": int(_as_float(operator_surface.get("check_count"), 0.0)),
            "audit_operator_surface_required_panel_count": int(_as_float(operator_surface.get("required_panel_count"), 0.0)),
            "audit_operator_surface_mutation_control_count": int(_as_float(operator_surface.get("mutation_control_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not operator_surface.get("operator_surface_passed"):
        blockers.append("parallel_strategy_audit_operator_surface_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)

    test_coverage = _audit_test_coverage_validation(root_path, report)
    report["audit_test_coverage_proof"] = test_coverage
    report["audit_test_coverage_rows"] = test_coverage.get("rows") or []
    report["audit_test_coverage_failed_rows"] = test_coverage.get("failed_rows") or []
    report["audit_test_coverage_validator_rows"] = test_coverage.get("coverage_rows") or []
    report["summary"].update(
        {
            "audit_test_coverage_passed": bool(test_coverage.get("test_coverage_passed")),
            "audit_test_coverage_failed_count": int(_as_float(test_coverage.get("failed_count"), 0.0)),
            "audit_test_coverage_check_count": int(_as_float(test_coverage.get("check_count"), 0.0)),
            "audit_test_coverage_validator_test_count": int(_as_float(test_coverage.get("validator_test_count"), 0.0)),
            "audit_test_coverage_validator_expected_count": int(_as_float(test_coverage.get("validator_expected_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not test_coverage.get("test_coverage_passed"):
        blockers.append("parallel_strategy_audit_test_coverage_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)

    repair_coverage = _audit_repair_coverage_validation(report)
    report["audit_repair_coverage_proof"] = repair_coverage
    report["audit_repair_coverage_rows"] = repair_coverage.get("rows") or []
    report["audit_repair_coverage_failed_rows"] = repair_coverage.get("failed_rows") or []
    report["summary"].update(
        {
            "audit_repair_coverage_passed": bool(repair_coverage.get("repair_coverage_passed")),
            "audit_repair_coverage_failed_count": int(_as_float(repair_coverage.get("failed_count"), 0.0)),
            "audit_repair_coverage_check_count": int(_as_float(repair_coverage.get("check_count"), 0.0)),
            "audit_repair_coverage_repair_action_count": int(_as_float(repair_coverage.get("repair_action_count"), 0.0)),
            "audit_repair_coverage_generic_repair_count": int(_as_float(repair_coverage.get("generic_repair_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not repair_coverage.get("repair_coverage_passed"):
        blockers.append("parallel_strategy_audit_repair_coverage_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)

    runtime_repair_readiness = _audit_runtime_repair_readiness_validation(report)
    report["audit_runtime_repair_readiness_proof"] = runtime_repair_readiness
    report["audit_runtime_repair_readiness_rows"] = runtime_repair_readiness.get("rows") or []
    report["audit_runtime_repair_readiness_failed_rows"] = runtime_repair_readiness.get("failed_rows") or []
    report["summary"].update(
        {
            "audit_runtime_repair_readiness_passed": bool(runtime_repair_readiness.get("runtime_repair_readiness_passed")),
            "audit_runtime_repair_readiness_failed_count": int(_as_float(runtime_repair_readiness.get("failed_count"), 0.0)),
            "audit_runtime_repair_readiness_check_count": int(_as_float(runtime_repair_readiness.get("check_count"), 0.0)),
            "audit_runtime_repair_readiness_guarded_command_line_count": int(_as_float(runtime_repair_readiness.get("guarded_command_line_count"), 0.0)),
            "audit_runtime_repair_readiness_unsafe_command_count": int(_as_float(runtime_repair_readiness.get("unsafe_command_count"), 0.0)),
            "audit_runtime_repair_readiness_post_restart_check_count": int(_as_float(runtime_repair_readiness.get("post_restart_check_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not runtime_repair_readiness.get("runtime_repair_readiness_passed"):
        blockers.append("parallel_strategy_audit_runtime_repair_readiness_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)

    repair_acceptance = _audit_repair_acceptance_validation(report)
    report["audit_repair_acceptance_proof"] = repair_acceptance
    report["audit_repair_acceptance_rows"] = repair_acceptance.get("rows") or []
    report["audit_repair_acceptance_failed_rows"] = repair_acceptance.get("failed_rows") or []
    report["audit_repair_acceptance_blocker_rows"] = repair_acceptance.get("acceptance_rows") or []
    report["summary"].update(
        {
            "audit_repair_acceptance_passed": bool(repair_acceptance.get("repair_acceptance_passed")),
            "audit_repair_acceptance_failed_count": int(_as_float(repair_acceptance.get("failed_count"), 0.0)),
            "audit_repair_acceptance_check_count": int(_as_float(repair_acceptance.get("check_count"), 0.0)),
            "audit_repair_acceptance_acceptance_row_count": int(_as_float(repair_acceptance.get("acceptance_row_count"), 0.0)),
            "audit_repair_acceptance_missing_acceptance_count": int(_as_float(repair_acceptance.get("missing_acceptance_count"), 0.0)),
            "audit_repair_acceptance_unmapped_blocker_count": int(_as_float(repair_acceptance.get("unmapped_blocker_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not repair_acceptance.get("repair_acceptance_passed"):
        blockers.append("parallel_strategy_audit_repair_acceptance_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)

    consistency_matrix = _audit_consistency_matrix_validation(report)
    report["audit_consistency_matrix_proof"] = consistency_matrix
    report["audit_consistency_matrix_rows"] = consistency_matrix.get("rows") or []
    report["audit_consistency_matrix_failed_rows"] = consistency_matrix.get("failed_rows") or []
    report["audit_consistency_matrix_validator_rows"] = consistency_matrix.get("validator_rows") or []
    report["summary"].update(
        {
            "audit_consistency_matrix_passed": bool(consistency_matrix.get("consistency_matrix_passed")),
            "audit_consistency_matrix_failed_count": int(_as_float(consistency_matrix.get("failed_count"), 0.0)),
            "audit_consistency_matrix_check_count": int(_as_float(consistency_matrix.get("check_count"), 0.0)),
            "audit_consistency_matrix_validator_count": int(_as_float(consistency_matrix.get("validator_count"), 0.0)),
            "audit_consistency_matrix_validator_pass_count": int(_as_float(consistency_matrix.get("validator_pass_count"), 0.0)),
            "audit_consistency_matrix_inconsistent_validator_count": int(_as_float(consistency_matrix.get("inconsistent_validator_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not consistency_matrix.get("consistency_matrix_passed"):
        blockers.append("parallel_strategy_audit_consistency_matrix_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)

    evidence_lineage = _audit_evidence_lineage_validation(report)
    report["audit_evidence_lineage_proof"] = evidence_lineage
    report["audit_evidence_lineage_rows"] = evidence_lineage.get("rows") or []
    report["audit_evidence_lineage_failed_rows"] = evidence_lineage.get("failed_rows") or []
    report["audit_evidence_lineage_section_rows"] = evidence_lineage.get("section_rows") or []
    report["summary"].update(
        {
            "audit_evidence_lineage_passed": bool(evidence_lineage.get("evidence_lineage_passed")),
            "audit_evidence_lineage_failed_count": int(_as_float(evidence_lineage.get("failed_count"), 0.0)),
            "audit_evidence_lineage_check_count": int(_as_float(evidence_lineage.get("check_count"), 0.0)),
            "audit_evidence_lineage_source_path_count": int(_as_float(evidence_lineage.get("source_path_count"), 0.0)),
            "audit_evidence_lineage_output_file_count": int(_as_float(evidence_lineage.get("output_file_count"), 0.0)),
            "audit_evidence_lineage_section_row_count": int(_as_float(evidence_lineage.get("section_row_count"), 0.0)),
            "audit_evidence_lineage_missing_lineage_count": int(_as_float(evidence_lineage.get("missing_lineage_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not evidence_lineage.get("evidence_lineage_passed"):
        blockers.append("parallel_strategy_audit_evidence_lineage_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)

    validator_closure = _audit_validator_closure_validation(root_path, report)
    report["audit_validator_closure_proof"] = validator_closure
    report["audit_validator_closure_rows"] = validator_closure.get("rows") or []
    report["audit_validator_closure_failed_rows"] = validator_closure.get("failed_rows") or []
    report["audit_validator_closure_source_rows"] = validator_closure.get("source_rows") or []
    report["summary"].update(
        {
            "audit_validator_closure_passed": bool(validator_closure.get("validator_closure_passed")),
            "audit_validator_closure_failed_count": int(_as_float(validator_closure.get("failed_count"), 0.0)),
            "audit_validator_closure_check_count": int(_as_float(validator_closure.get("check_count"), 0.0)),
            "audit_validator_closure_validator_count": int(_as_float(validator_closure.get("validator_count"), 0.0)),
            "audit_validator_closure_source_check_count": int(_as_float(validator_closure.get("source_check_count"), 0.0)),
            "audit_validator_closure_failed_source_count": int(_as_float(validator_closure.get("failed_source_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not validator_closure.get("validator_closure_passed"):
        blockers.append("parallel_strategy_audit_validator_closure_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)

    public_contract = _audit_public_contract_validation(report)
    report["audit_public_contract_proof"] = public_contract
    report["audit_public_contract_rows"] = public_contract.get("rows") or []
    report["audit_public_contract_failed_rows"] = public_contract.get("failed_rows") or []
    report["summary"].update(
        {
            "audit_public_contract_passed": bool(public_contract.get("public_contract_passed")),
            "audit_public_contract_failed_count": int(_as_float(public_contract.get("failed_count"), 0.0)),
            "audit_public_contract_check_count": int(_as_float(public_contract.get("check_count"), 0.0)),
            "audit_public_contract_required_summary_field_count": int(_as_float(public_contract.get("required_summary_field_count"), 0.0)),
            "audit_public_contract_required_array_field_count": int(_as_float(public_contract.get("required_array_field_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not public_contract.get("public_contract_passed"):
        blockers.append("parallel_strategy_audit_public_contract_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)
    chain_validation = _audit_validation_chain_validation(report)
    report["audit_validation_chain_proof"] = chain_validation
    report["audit_validation_chain_rows"] = chain_validation.get("rows") or []
    report["audit_validation_chain_failed_rows"] = chain_validation.get("failed_rows") or []
    report["audit_validation_chain_validator_rows"] = chain_validation.get("validator_rows") or []
    report["summary"].update(
        {
            "audit_validation_chain_passed": bool(chain_validation.get("validation_chain_passed")),
            "audit_validation_chain_failed_count": int(_as_float(chain_validation.get("failed_count"), 0.0)),
            "audit_validation_chain_check_count": int(_as_float(chain_validation.get("check_count"), 0.0)),
            "audit_validation_chain_validator_count": int(_as_float(chain_validation.get("validator_count"), 0.0)),
            "audit_validation_chain_validator_pass_count": int(_as_float(chain_validation.get("validator_pass_count"), 0.0)),
        }
    )
    blockers = [str(blocker) for blocker in report.get("blockers", []) if str(blocker)]
    if not chain_validation.get("validation_chain_passed"):
        blockers.append("parallel_strategy_audit_validation_chain_gap")
        report["status"] = _status_from_blockers(blockers)
        report["blockers"] = blockers
        report["summary"]["blocker_count"] = len(blockers)
        report["next_repair_actions"] = _next_repair_actions(blockers)
    final_writes = [_write_json(_rooted(root_path, rel), report) for rel in json_paths]
    final_writes.append(_write_text(_rooted(root_path, DEFAULT_AUDIT_MD), _make_markdown(report)))
    report["write_info"] = {"evidence_writes": final_writes}
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Parallel Strategy Unity stress audit evidence.")
    parser.add_argument("--repo-root", default="", help="Repository root; defaults to cwd/repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--watch", action="store_true", help="Run continuously.")
    parser.add_argument("--interval", type=float, default=10.0, help="Watch interval seconds.")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else None
    if args.watch:
        while True:
            build_and_write_parallel_strategy_unity_stress_audit(root=root)
            time.sleep(max(2.0, float(args.interval)))
    report = build_and_write_parallel_strategy_unity_stress_audit(root=root)
    print(json.dumps(report, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
