"""Parallel strategy unity runtime.

This module lets multiple production-capable trading systems run side by side
while preserving one execution authority: the unified market trader/executor.
Strategy workers publish normalized evidence and strategy intents only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

try:
    from aureon.core.exchange_rate_limit_registry import get_exchange_rate_limit
except Exception:  # pragma: no cover - import guard for partial runtimes
    get_exchange_rate_limit = None  # type: ignore[assignment]

try:
    from aureon.trading.live_trade_signal_fabric import build_api_budget_proof, publish_trade_flow_event
except Exception:  # pragma: no cover - import guard for partial runtimes
    build_api_budget_proof = None  # type: ignore[assignment]
    publish_trade_flow_event = None  # type: ignore[assignment]


SCHEMA_VERSION = "aureon-parallel-strategy-unity-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]

REQUEST_BROKER_STATE_PATH = Path("state/unified_exchange_request_broker.json")
REQUEST_BROKER_PUBLIC_PATH = Path("frontend/public/aureon_unified_exchange_request_broker.json")
POWER_STATION_REQUEST_STATE_PATH = Path("state/aureon_power_station_request_governor.json")
POWER_STATION_REQUEST_PUBLIC_PATH = Path("frontend/public/aureon_power_station_request_governor.json")
STRATEGY_INTENT_LOG_PATH = Path("state/unified_strategy_intents.jsonl")
STRATEGY_INTENT_STATE_PATH = Path("state/unified_strategy_intents.json")
STRATEGY_INTENT_PUBLIC_PATH = Path("frontend/public/aureon_unified_strategy_intents.json")
UNITY_STATE_PATH = Path("state/aureon_parallel_strategy_unity.json")
UNITY_PUBLIC_PATH = Path("frontend/public/aureon_parallel_strategy_unity.json")
RUNTIME_STATUS_PATH = Path("state/unified_runtime_status.json")
HARMONIC_AFFECT_PUBLIC_PATH = Path("frontend/public/aureon_harmonic_affect_state.json")
HNC_COGNITIVE_PROOF_STATE_PATH = Path("state/aureon_hnc_cognitive_proof.json")
HNC_OPERATING_CYCLE_STATE_PATH = Path("state/aureon_hnc_operating_cycle.json")
LAMBDA_HISTORY_PATH = Path("state/lambda_history.json")
V11_POWER_STATION_SOURCE_PATH = Path("aureon/trading/v11_power_station_live.py")

DEFAULT_MINIMUM_NET_PROFIT_GBP = 0.03
DEFAULT_INTENT_TTL_SEC = 180.0
GHOST_DANCE_PROTOCOL_VERSION = "ghost-dance-v1"
GHOST_DANCE_CYCLE_SEC = 30.0
GHOST_DANCE_MIN_PHASE_SPACING_SEC = 2.0
HARMONIC_API_PIANO_VERSION = "harmonic-api-piano-v1"
RAINBOW_HARMONIC_LADDER_VERSION = "rainbow-harmonic-frequency-ladder-v1"
POWER_STATION_REQUEST_PROTOCOL_VERSION = "power-station-request-governor-v1"
MUTATION_OPERATION_TYPES = {
    "order_submit",
    "order_close",
    "order_cancel",
    "order_replace",
    "position_close",
    "position_mutation",
    "broker_order_mutation",
    "exchange_mutation",
}

RAINBOW_HARMONIC_STEPS: Tuple[Tuple[str, str, float, str], ...] = (
    ("red_root", "root", 1.0, "close_first_and_primary_capital"),
    ("orange_second", "major_second", 9.0 / 8.0, "fresh_market_scan"),
    ("yellow_third", "major_third", 5.0 / 4.0, "candidate_scoring"),
    ("green_fourth", "perfect_fourth", 4.0 / 3.0, "counter_intel_confirmation"),
    ("blue_fifth", "perfect_fifth", 3.0 / 2.0, "liquidity_confirmation"),
    ("indigo_sixth", "major_sixth", 5.0 / 3.0, "margin_wave_timing"),
    ("violet_octave", "octave", 2.0, "executor_attention"),
)

RAINBOW_REQUEST_FIELDS = (
    "rainbow_harmonic_ladder_protocol",
    "rainbow_step_index",
    "rainbow_step_name",
    "rainbow_interval_name",
    "rainbow_interval_ratio",
    "rainbow_frequency_hz",
    "harmony_lane_id",
    "request_tempo_band",
    "request_phase_role",
    "song_continuity_guard",
)

POWER_STATION_REQUEST_FIELDS = (
    "power_station_request_protocol",
    "power_station_governor_status",
    "request_direction",
    "request_class",
    "request_owner_authority",
    "request_governor_decision",
    "power_station_priority",
    "power_station_budget_tier",
    "power_station_min_notional",
    "power_station_reserve_pct",
    "power_station_max_siphon_rate",
    "power_station_metadata_source",
    "request_metadata_source",
    "credential_boundary",
    "mutation_scope",
    "power_station_harmony_lane_id",
)


@dataclass(frozen=True)
class StrategyWorkerConfig:
    worker_id: str
    label: str
    venue: str
    market_type: str
    operation_type: str
    source_system: str
    role: str


PRODUCTION_WORKERS: Tuple[StrategyWorkerConfig, ...] = (
    StrategyWorkerConfig(
        "unified_market_scanner",
        "Unified market / scanner fusion",
        "capital",
        "cfd",
        "market_data",
        "unified_market_trader.scanner_fusion",
        "rank shared tradable candidates",
    ),
    StrategyWorkerConfig(
        "capital_cfd_strategy",
        "Capital ecosystem / CFD strategy",
        "capital",
        "cfd",
        "market_data",
        "capital_cfd_trader.strategy",
        "Capital execution venue candidate support",
    ),
    StrategyWorkerConfig(
        "kraken_margin_intelligence",
        "Kraken confirmation / margin intelligence",
        "kraken",
        "spot",
        "market_data",
        "kraken_margin_intelligence",
        "crypto liquidity and margin context confirmation",
    ),
    StrategyWorkerConfig(
        "binance_liquidity_confirmation",
        "Binance confirmation / liquidity",
        "binance",
        "spot",
        "market_data",
        "binance_liquidity_confirmation",
        "crypto breadth and liquidity confirmation",
    ),
    StrategyWorkerConfig(
        "alpaca_equity_confirmation",
        "Alpaca equity / ETF confirmation",
        "alpaca",
        "spot",
        "market_data",
        "alpaca_equity_confirmation",
        "equity, ETF, and risk-appetite confirmation",
    ),
    StrategyWorkerConfig(
        "seer_lyra_hnc_coherence",
        "Seer / Lyra / HNC coherence",
        "internal",
        "coherence",
        "context_read",
        "seer_lyra_hnc_coherence",
        "oracle, affect, and harmonic coherence support",
    ),
    StrategyWorkerConfig(
        "unified_margin_wave",
        "Unified margin brain / margin-wave",
        "capital",
        "cfd",
        "market_data",
        "unified_margin_wave",
        "margin and wave timing support",
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rooted(root: Optional[Path], rel: Path) -> Path:
    base = Path(root or REPO_ROOT).resolve()
    return rel if rel.is_absolute() else base / rel


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(tmp_path, path)


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, default=str) + "\n")


def _tail_jsonl(path: Path, limit: int = 200) -> List[Dict[str, Any]]:
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


def _hash_id(prefix: str, *parts: Any) -> str:
    raw = "|".join(str(part) for part in parts)
    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:18]
    return f"{prefix}-{digest}"


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if number == number else default
    except Exception:
        return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


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


def route_key_for(venue: Any, market_type: Any, symbol: Any, side: Any) -> str:
    return ":".join(
        [
            str(venue or "").lower(),
            str(market_type or "").lower(),
            str(symbol or "").upper().strip(),
            str(side or "").upper().strip(),
        ]
    )


def _budget_limit_for_venue(venue: str) -> float:
    if venue == "internal":
        return 600.0
    if get_exchange_rate_limit is not None:
        try:
            profile = get_exchange_rate_limit(venue)
            if profile is not None:
                return float(profile.configured_calls_per_min())
        except Exception:
            pass
    defaults = {"capital": 45.0, "kraken": 30.0, "binance": 240.0, "alpaca": 120.0}
    return defaults.get(str(venue or "").lower(), 60.0)


def build_ghost_dance_schedule(
    workers: Sequence[StrategyWorkerConfig],
    *,
    now_ts: Optional[float] = None,
    cycle_sec: float = GHOST_DANCE_CYCLE_SEC,
) -> Dict[str, Any]:
    """Build deterministic out-of-phase worker beats for API-budget protection."""
    now_value = float(now_ts if now_ts is not None else time.time())
    worker_count = max(1, len(workers))
    # A coprime stride spreads adjacent registered workers across the cycle.
    stride = 3 if worker_count % 3 else 5
    while worker_count > 1 and _gcd(stride, worker_count) != 1:
        stride += 2
    beat_index = int(now_value // max(1.0, cycle_sec))
    cycle_start = beat_index * cycle_sec
    phase_width = cycle_sec / worker_count
    rows: List[Dict[str, Any]] = []
    seen_phase_by_lock: Dict[Tuple[str, int], List[str]] = defaultdict(list)

    for index, worker in enumerate(workers):
        phase_index = (index * stride) % worker_count
        phase_offset = round(phase_index * phase_width, 3)
        jitter_ms = int(hashlib.sha256(f"{worker.worker_id}:{beat_index}".encode("utf-8")).hexdigest()[:4], 16) % 700
        phase_due_ts = cycle_start + phase_offset + (jitter_ms / 1000.0)
        phase_distance = (now_value - phase_due_ts) % cycle_sec
        scheduled_after_ms = int(max(0.0, phase_due_ts - now_value) * 1000)
        api_key_lock_family = f"{worker.venue}:{worker.operation_type}"
        sequence_number = _hash_id("gbeat", worker.worker_id, beat_index, phase_index)
        seen_phase_by_lock[(api_key_lock_family, phase_index)].append(worker.worker_id)
        rows.append(
            {
                "worker_id": worker.worker_id,
                "venue": worker.venue,
                "operation_type": worker.operation_type,
                "api_key_lock_family": api_key_lock_family,
                "ghost_dance_protocol": GHOST_DANCE_PROTOCOL_VERSION,
                "ghost_beat_id": f"gbeat-{beat_index}",
                "ghost_beat_index": beat_index,
                "ghost_phase_index": phase_index,
                "ghost_phase_count": worker_count,
                "ghost_phase_offset_sec": phase_offset,
                "ghost_phase_width_sec": round(phase_width, 3),
                "ghost_sequence_number": sequence_number,
                "ghost_number_generator": "deterministic_coprime_stride_hash_jitter",
                "phase_jitter_ms": jitter_ms,
                "scheduled_after_ms": scheduled_after_ms,
                "phase_distance_sec": round(phase_distance, 3),
                "phase_status": "in_phase_window" if phase_distance <= phase_width else "awaiting_phase",
                "api_cooldown_guard": "out_of_phase_api_key_lock",
            }
        )

    collision_rows = [
        {
            "api_key_lock_family": key[0],
            "ghost_phase_index": key[1],
            "worker_ids": worker_ids,
            "collision_count": len(worker_ids),
        }
        for key, worker_ids in seen_phase_by_lock.items()
        if len(worker_ids) > 1
    ]
    offsets = [float(row["ghost_phase_offset_sec"]) for row in rows]
    return {
        "protocol": GHOST_DANCE_PROTOCOL_VERSION,
        "status": "ghost_dance_phase_collision" if collision_rows else "ghost_dance_ready",
        "generated_at": utc_now(),
        "cycle_sec": cycle_sec,
        "phase_count": worker_count,
        "phase_stride": stride,
        "beat_index": beat_index,
        "api_key_lock_family_count": len({row["api_key_lock_family"] for row in rows}),
        "phase_spread_sec": round(max(offsets) - min(offsets), 3) if offsets else 0.0,
        "min_phase_spacing_sec": GHOST_DANCE_MIN_PHASE_SPACING_SEC,
        "collision_count": len(collision_rows),
        "collision_rows": collision_rows,
        "worker_phase_rows": rows,
        "manual_boundaries": [
            "ghost dance phases pace workers; they do not grant broker mutation authority",
            "phase offsets reduce herd requests against the same venue/API-key lock family",
            "unified executor and runtime gates remain authoritative",
        ],
    }


def _lambda_tempo_from_history(history: Mapping[str, Any]) -> Dict[str, Any]:
    values = history.get("history") if isinstance(history.get("history"), list) else []
    numeric = [_as_float(item, 0.0) for item in values if item not in (None, "")]
    if len(numeric) < 2:
        return {
            "lambda_current": numeric[-1] if numeric else 0.0,
            "lambda_delta": 0.0,
            "lambda_tempo": 0.5,
            "lambda_history_count": len(numeric),
        }
    current = numeric[-1]
    prior = numeric[-2]
    delta = current - prior
    scale = max(1.0, abs(prior))
    tempo = _clamp(0.5 + (delta / scale) * 8.0, 0.0, 1.0)
    return {
        "lambda_current": round(current, 6),
        "lambda_delta": round(delta, 6),
        "lambda_tempo": round(tempo, 6),
        "lambda_history_count": len(numeric),
    }


def build_harmonic_api_piano_context(*, root: Optional[Path] = None, runtime: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Read real local HNC/harmonic evidence and convert it into API tempo context."""
    runtime_map = runtime if isinstance(runtime, Mapping) else {}
    hnc = _read_json(_rooted(root, HNC_COGNITIVE_PROOF_STATE_PATH), {})
    operating_cycle = _read_json(_rooted(root, HNC_OPERATING_CYCLE_STATE_PATH), {})
    affect = _read_json(_rooted(root, HARMONIC_AFFECT_PUBLIC_PATH), {})
    lambda_history = _read_json(_rooted(root, LAMBDA_HISTORY_PATH), {})
    hnc_runtime = runtime_map.get("hnc_cognitive_proof") if isinstance(runtime_map.get("hnc_cognitive_proof"), Mapping) else {}
    hnc_source = hnc if isinstance(hnc, Mapping) and hnc else hnc_runtime
    affect_summary = affect.get("summary") if isinstance(affect.get("summary"), Mapping) else {}
    master_formula = hnc_source.get("master_formula") if isinstance(hnc_source.get("master_formula"), Mapping) else {}
    auris_nodes = hnc_source.get("auris_nodes") if isinstance(hnc_source.get("auris_nodes"), Mapping) else {}
    systems = hnc_source.get("systems") if isinstance(hnc_source.get("systems"), Mapping) else {}
    seer_reading = systems.get("seer", {}).get("runtime_reading", {}) if isinstance(systems.get("seer"), Mapping) else {}
    lyra_reading = systems.get("lyra", {}).get("runtime_reading", {}) if isinstance(systems.get("lyra"), Mapping) else {}
    action_plan = runtime_map.get("exchange_action_plan") if isinstance(runtime_map.get("exchange_action_plan"), Mapping) else {}
    watchdog = affect.get("signals", {}).get("runtime_watchdog", {}) if isinstance(affect.get("signals"), Mapping) and isinstance(affect.get("signals", {}).get("runtime_watchdog"), Mapping) else {}
    runtime_stale = bool(
        affect_summary.get("runtime_stale")
        or watchdog.get("tick_stale")
        or action_plan.get("runtime_stale")
    )
    lambda_tempo = _lambda_tempo_from_history(lambda_history if isinstance(lambda_history, Mapping) else {})
    hnc_score = _clamp(_as_float(master_formula.get("score"), _as_float(affect_summary.get("hnc_coherence_score"), 0.5)))
    auris_coherence = _clamp(_as_float(auris_nodes.get("coherence"), _as_float(affect_summary.get("hnc_coherence_score"), 0.5)))
    lyra_score = _clamp(_as_float(lyra_reading.get("resonance_score"), _as_float(affect_summary.get("goal_alignment"), 0.5)))
    seer_confidence = _clamp(_as_float(seer_reading.get("confidence"), _as_float(master_formula.get("inputs", {}).get("real_data") if isinstance(master_formula.get("inputs"), Mapping) else 0.5, 0.5)))
    reward_alignment = _clamp(_as_float(affect_summary.get("reward_alignment"), 0.0))
    safety_pressure = _clamp(_as_float(affect_summary.get("safety_blocker_count"), 0.0) / 25.0)
    coherence_blend = _clamp(
        hnc_score * 0.28
        + auris_coherence * 0.25
        + lyra_score * 0.16
        + seer_confidence * 0.16
        + _as_float(lambda_tempo.get("lambda_tempo"), 0.5) * 0.10
        + reward_alignment * 0.05
    )
    # Tempo rises with coherence, but stale runtime or heavy safety pressure damps the song.
    dampener = 0.72 if runtime_stale else 1.0
    dampener *= max(0.45, 1.0 - safety_pressure * 0.35)
    tempo_multiplier = _clamp(0.35 + coherence_blend * 0.9 * dampener, 0.25, 1.15)
    return {
        "protocol": HARMONIC_API_PIANO_VERSION,
        "generated_at": utc_now(),
        "status": "harmonic_api_piano_ready" if hnc_source else "harmonic_api_piano_attention",
        "tempo_source": "real_hnc_harmonic_runtime_artifacts",
        "hnc_score": round(hnc_score, 6),
        "auris_coherence": round(auris_coherence, 6),
        "lyra_resonance_score": round(lyra_score, 6),
        "lyra_frequency_hz": round(_as_float(lyra_reading.get("resonance_frequency_hz"), _as_float(affect_summary.get("resonance_frequency_hz"), 0.0)), 6),
        "seer_confidence": round(seer_confidence, 6),
        "seer_grade": str(seer_reading.get("vision_grade") or "unknown"),
        "reward_alignment": round(reward_alignment, 6),
        "safety_pressure": round(safety_pressure, 6),
        "runtime_stale": runtime_stale,
        "coherence_blend": round(coherence_blend, 6),
        "tempo_multiplier": round(tempo_multiplier, 6),
        **lambda_tempo,
        "evidence_source_paths": [
            HNC_COGNITIVE_PROOF_STATE_PATH.as_posix(),
            HNC_OPERATING_CYCLE_STATE_PATH.as_posix(),
            HARMONIC_AFFECT_PUBLIC_PATH.as_posix(),
            LAMBDA_HISTORY_PATH.as_posix(),
        ],
        "manual_boundaries": [
            "harmonic piano controls scheduling tempo only",
            "no API key value is read, revealed, or rotated",
            "unified executor and venue rate budgets remain authoritative",
        ],
    }


def apply_harmonic_api_piano(
    ghost_dance: Mapping[str, Any],
    harmonic_context: Mapping[str, Any],
) -> Dict[str, Any]:
    """Layer adaptive HNC/harmonic tempo over Ghost Dance phase lanes."""
    rows = [row for row in ghost_dance.get("worker_phase_rows", []) if isinstance(row, Mapping)]
    tempo_multiplier = _clamp(_as_float(harmonic_context.get("tempo_multiplier"), 0.65), 0.25, 1.15)
    hnc_score = _clamp(_as_float(harmonic_context.get("hnc_score"), 0.5))
    auris_coherence = _clamp(_as_float(harmonic_context.get("auris_coherence"), 0.5))
    runtime_stale = bool(harmonic_context.get("runtime_stale"))
    worker_bias = {
        "capital_cfd_strategy": 1.0,
        "unified_margin_wave": 0.96,
        "unified_market_scanner": 0.92,
        "seer_lyra_hnc_coherence": 0.88,
        "binance_liquidity_confirmation": 0.74,
        "kraken_margin_intelligence": 0.72,
        "alpaca_equity_confirmation": 0.70,
    }
    piano_rows: List[Dict[str, Any]] = []
    for row in rows:
        worker_id = str(row.get("worker_id") or "")
        base_bias = worker_bias.get(worker_id, 0.65)
        lock_family = str(row.get("api_key_lock_family") or "")
        venue_weight = 1.0 if lock_family.startswith("capital:") else 0.82 if lock_family != "internal:context_read" else 0.9
        velocity = _clamp((base_bias * 0.42) + (hnc_score * 0.22) + (auris_coherence * 0.18) + (tempo_multiplier * 0.18))
        original_wait_ms = int(_as_float(row.get("scheduled_after_ms"), 0.0))
        acceleration = 0.18 + velocity * 0.42
        if runtime_stale:
            acceleration *= 0.45
        tuned_wait_ms = int(max(0.0, original_wait_ms * (1.0 - min(0.62, acceleration * venue_weight))))
        api_play_window_ms = max(250, int(_as_float(row.get("ghost_phase_width_sec"), 1.0) * 1000 * max(0.35, min(1.0, tempo_multiplier))))
        song_stop_guard = "cooldown_preserved"
        if runtime_stale:
            song_stop_guard = "tempo_dampened_runtime_stale"
        elif velocity > 0.82 and original_wait_ms == 0:
            song_stop_guard = "fast_turn_inside_phase_window"
        piano_rows.append(
            {
                **dict(row),
                "harmonic_api_piano_protocol": HARMONIC_API_PIANO_VERSION,
                "piano_key_id": f"{lock_family}:{worker_id}",
                "piano_key_rank": 0,
                "piano_velocity_score": round(velocity, 6),
                "harmonic_tempo_multiplier": round(tempo_multiplier, 6),
                "hnc_master_score": round(hnc_score, 6),
                "auris_coherence": round(auris_coherence, 6),
                "api_play_window_ms": api_play_window_ms,
                "original_scheduled_after_ms": original_wait_ms,
                "scheduled_after_ms": tuned_wait_ms,
                "turn_acceleration_ratio": round(acceleration, 6),
                "song_stop_guard": song_stop_guard,
                "harmonic_turn_state": "play_now" if tuned_wait_ms == 0 else "scheduled",
                "next_turn_reason": "highest coherent tempo within api lock phase",
            }
        )
    piano_rows.sort(key=lambda item: (-_as_float(item.get("piano_velocity_score"), 0.0), _as_float(item.get("scheduled_after_ms"), 0.0)))
    for index, row in enumerate(piano_rows, start=1):
        row["piano_key_rank"] = index
    ranked_by_worker = {str(row.get("worker_id") or ""): row for row in piano_rows}
    ordered_rows = [ranked_by_worker.get(str(row.get("worker_id") or ""), dict(row)) for row in rows]
    return {
        "protocol": HARMONIC_API_PIANO_VERSION,
        "status": "harmonic_api_piano_ready",
        "generated_at": utc_now(),
        "tempo_multiplier": round(tempo_multiplier, 6),
        "coherence_blend": harmonic_context.get("coherence_blend"),
        "runtime_stale": runtime_stale,
        "piano_key_count": len(piano_rows),
        "play_now_count": sum(1 for row in piano_rows if row.get("harmonic_turn_state") == "play_now"),
        "song_stop_guard": "tempo_dampened_runtime_stale" if runtime_stale else "cooldown_preserved",
        "fastest_key": piano_rows[0] if piano_rows else {},
        "piano_key_rows": piano_rows,
        "worker_phase_rows": ordered_rows,
        "harmonic_context": dict(harmonic_context),
        "manual_boundaries": [
            "HNC/harmonic tempo may reorder or accelerate lease turns inside cooldown windows",
            "API key values are never read; only lock families and rate budgets are scheduled",
            "this does not grant broker mutation authority",
        ],
    }


def apply_rainbow_harmonic_frequency_ladder(
    harmonic_piano: Mapping[str, Any],
    harmonic_context: Mapping[str, Any],
) -> Dict[str, Any]:
    """Map workers onto a neutral seven-step frequency ladder for request pacing."""
    rows = [row for row in harmonic_piano.get("worker_phase_rows", []) if isinstance(row, Mapping)]
    lyra_frequency = _as_float(harmonic_context.get("lyra_frequency_hz"), 0.0)
    base_frequency = lyra_frequency if lyra_frequency > 0 else 528.0
    tempo_multiplier = _clamp(_as_float(harmonic_piano.get("tempo_multiplier"), _as_float(harmonic_context.get("tempo_multiplier"), 0.65)), 0.25, 1.15)
    ladder_rows = []
    for index, step in enumerate(RAINBOW_HARMONIC_STEPS):
        step_name, interval_name, ratio, phase_role = step
        frequency = round(base_frequency * ratio, 6)
        ladder_rows.append(
            {
                "rainbow_step_index": index,
                "rainbow_step_name": step_name,
                "rainbow_interval_name": interval_name,
                "rainbow_interval_ratio": round(ratio, 6),
                "rainbow_frequency_hz": frequency,
                "request_phase_role": phase_role,
                "request_tempo_band": "fast" if ratio >= 1.5 and tempo_multiplier >= 0.75 else "steady" if ratio >= 1.25 else "rooted",
            }
        )

    worker_rows: List[Dict[str, Any]] = []
    for row in rows:
        rank = int(_as_float(row.get("piano_key_rank"), 1.0))
        step = ladder_rows[(max(1, rank) - 1) % len(ladder_rows)]
        wait_ms = int(_as_float(row.get("scheduled_after_ms"), 0.0))
        play_window_ms = int(_as_float(row.get("api_play_window_ms"), 1000.0))
        lane_id = f"{row.get('api_key_lock_family') or 'internal:context'}:{step['rainbow_step_name']}"
        worker_rows.append(
            {
                **dict(row),
                "rainbow_harmonic_ladder_protocol": RAINBOW_HARMONIC_LADDER_VERSION,
                "rainbow_step_index": step["rainbow_step_index"],
                "rainbow_step_name": step["rainbow_step_name"],
                "rainbow_interval_name": step["rainbow_interval_name"],
                "rainbow_interval_ratio": step["rainbow_interval_ratio"],
                "rainbow_frequency_hz": step["rainbow_frequency_hz"],
                "harmony_lane_id": lane_id,
                "request_tempo_band": step["request_tempo_band"],
                "request_phase_role": step["request_phase_role"],
                "song_continuity_guard": "phase_window_preserved" if wait_ms <= play_window_ms else "scheduled_outside_fast_window",
            }
        )

    return {
        "protocol": RAINBOW_HARMONIC_LADDER_VERSION,
        "status": "rainbow_harmonic_ladder_ready" if worker_rows else "rainbow_harmonic_ladder_attention",
        "generated_at": utc_now(),
        "base_frequency_hz": round(base_frequency, 6),
        "base_frequency_source": "lyra_runtime_frequency" if lyra_frequency > 0 else "default_528hz_reference",
        "tempo_multiplier": round(tempo_multiplier, 6),
        "ladder_step_count": len(ladder_rows),
        "worker_ladder_count": len(worker_rows),
        "song_continuity_guard": "phase_window_preserved"
        if all(row.get("song_continuity_guard") == "phase_window_preserved" for row in worker_rows)
        else "scheduled_outside_fast_window",
        "ladder_rows": ladder_rows,
        "worker_phase_rows": worker_rows,
        "manual_boundaries": [
            "rainbow ladder is an abstract frequency scheduler; it does not encode copyrighted lyrics or melody",
            "frequency bands pace request turns only and never reveal API key values",
            "unified executor and venue budgets remain authoritative",
        ],
    }


def _parse_power_station_defaults(source_text: str) -> Dict[str, Any]:
    min_notional: Dict[str, float] = {}
    for match in re.finditer(r"['\"]([a-zA-Z0-9_.-]+)['\"]\s*:\s*([0-9]+(?:\.[0-9]+)?)", source_text):
        key = match.group(1).lower()
        if key in {"binance", "kraken", "alpaca", "capital"}:
            min_notional[key] = float(match.group(2))
    enabled_match = re.search(r"enabled_exchanges.*?lambda:\s*\[([^\]]+)\]", source_text, re.DOTALL)
    enabled_exchanges: List[str] = []
    if enabled_match:
        enabled_exchanges = [item.strip().strip("'\"").lower() for item in enabled_match.group(1).split(",") if item.strip()]
    if "capital" not in min_notional:
        min_notional["capital"] = DEFAULT_MINIMUM_NET_PROFIT_GBP
    if "capital" not in enabled_exchanges:
        enabled_exchanges = ["capital", *enabled_exchanges]
    return {
        "exchange_min_notional": min_notional or {"capital": DEFAULT_MINIMUM_NET_PROFIT_GBP, "binance": 5.0, "kraken": 5.0, "alpaca": 1.0},
        "enabled_exchanges": enabled_exchanges or ["capital", "binance", "kraken", "alpaca"],
        "capital_reserve_pct": _as_float((re.search(r"capital_reserve_pct:\s*float\s*=\s*([0-9.]+)", source_text) or [None, 0.10])[1], 0.10),
        "max_siphon_rate": _as_float((re.search(r"max_siphon_rate:\s*float\s*=\s*([0-9.]+)", source_text) or [None, 0.50])[1], 0.50),
        "min_trade_size": _as_float((re.search(r"min_trade_size:\s*float\s*=\s*([0-9.]+)", source_text) or [None, 5.0])[1], 5.0),
    }


def build_power_station_request_governor(
    *,
    root: Optional[Path] = None,
    rainbow_ladder: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Read Power Station metadata and convert it into request-governor context."""
    source_path = _rooted(root, V11_POWER_STATION_SOURCE_PATH)
    source_text = ""
    source_present = source_path.exists()
    if source_present:
        try:
            source_text = source_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            source_text = ""
    defaults = _parse_power_station_defaults(source_text)
    marker_tokens = {
        "v11_config": "class V11Config" in source_text,
        "power_station_live": "class V11PowerStationLive" in source_text,
        "exchange_min_notional": "exchange_min_notional" in source_text,
        "enabled_exchanges": "enabled_exchanges" in source_text,
        "capital_reserve_pct": "capital_reserve_pct" in source_text,
        "max_siphon_rate": "max_siphon_rate" in source_text,
    }
    request_classes = [
        {"request_class": "market_data", "direction": "outbound_market_api", "mutation_scope": "none", "budget_tier": "shared_stream_or_rest"},
        {"request_class": "context_read", "direction": "internal_context", "mutation_scope": "none", "budget_tier": "local_context"},
        {"request_class": "account_read", "direction": "outbound_private_api", "mutation_scope": "read_only", "budget_tier": "private_low_rate"},
        {"request_class": "heavy_scan", "direction": "outbound_market_api", "mutation_scope": "none", "budget_tier": "scan_budgeted"},
        {"request_class": "order_submit", "direction": "outbound_private_api", "mutation_scope": "unified_executor_only", "budget_tier": "mutation_throttled"},
        {"request_class": "position_close", "direction": "outbound_private_api", "mutation_scope": "unified_executor_only", "budget_tier": "mutation_throttled"},
        {"request_class": "artifact_write", "direction": "internal_artifact", "mutation_scope": "local_file_only", "budget_tier": "local_context"},
    ]
    ladder_summary = rainbow_ladder if isinstance(rainbow_ladder, Mapping) else {}
    return {
        "schema_version": SCHEMA_VERSION,
        "protocol": POWER_STATION_REQUEST_PROTOCOL_VERSION,
        "status": "power_station_request_governor_ready" if source_present and marker_tokens["v11_config"] else "power_station_request_governor_attention",
        "generated_at": utc_now(),
        "source_present": source_present,
        "source_path": V11_POWER_STATION_SOURCE_PATH.as_posix(),
        "source_marker_rows": [
            {"marker": key, "present": bool(value)}
            for key, value in marker_tokens.items()
        ],
        "enabled_exchanges": defaults["enabled_exchanges"],
        "exchange_min_notional": defaults["exchange_min_notional"],
        "reserve_policy": {
            "capital_reserve_pct": defaults["capital_reserve_pct"],
            "min_trade_size": defaults["min_trade_size"],
        },
        "siphon_policy": {
            "max_siphon_rate": defaults["max_siphon_rate"],
            "minimum_net_profit_gbp": DEFAULT_MINIMUM_NET_PROFIT_GBP,
        },
        "request_classes": request_classes,
        "rainbow_harmonic_ladder_protocol": ladder_summary.get("protocol") or "",
        "rainbow_base_frequency_hz": ladder_summary.get("base_frequency_hz") or 0.0,
        "rainbow_ladder_step_count": ladder_summary.get("ladder_step_count") or 0,
        "authority_model": {
            "executor_worker_id": "unified_market_trader.executor",
            "mutation_owner": "unified_market_trader.executor",
            "strategy_workers": "request_leases_and_intents_only",
        },
        "credential_boundary": "metadata_only_no_secret_values_read_or_revealed",
        "manual_boundaries": [
            "Power Station metadata shapes request priority and minimum-size context only",
            "request leases do not place broker orders",
            "order and position mutation authority remains with unified_market_trader.executor",
        ],
        "source_paths": {
            "source": V11_POWER_STATION_SOURCE_PATH.as_posix(),
            "state": POWER_STATION_REQUEST_STATE_PATH.as_posix(),
            "public": POWER_STATION_REQUEST_PUBLIC_PATH.as_posix(),
        },
    }


def _request_class_for_operation(operation_type: str) -> str:
    op = str(operation_type or "").lower()
    if op in {"market_data", "ticker", "quote", "order_book", "price_history"}:
        return "market_data"
    if op in {"context_read", "coherence_read", "artifact_read"}:
        return "context_read"
    if op in {"account_read", "positions_read", "balance_read"}:
        return "account_read"
    if op in {"heavy_scan", "registry_scan", "universe_scan"}:
        return "heavy_scan"
    if op in {"artifact_write", "state_write"}:
        return "artifact_write"
    if op in {"order_close", "position_close"}:
        return "position_close"
    if _operation_is_mutation_name(op):
        return "order_submit"
    return op or "unknown"


def _operation_is_mutation_name(operation_type: str) -> bool:
    op = str(operation_type or "").lower()
    return op in MUTATION_OPERATION_TYPES or "mutation" in op or op.startswith("order_") or op.startswith("position_")


def _gcd(left: int, right: int) -> int:
    while right:
        left, right = right, left % right
    return abs(left)


def _ghost_collision_count(rows: Sequence[Mapping[str, Any]]) -> int:
    groups: Dict[Tuple[str, str], int] = {}
    for row in rows:
        family = str(row.get("api_key_lock_family") or "")
        phase = str(row.get("ghost_phase_index") or "")
        if not family or not phase:
            continue
        key = (family, phase)
        groups[key] = groups.get(key, 0) + 1
    return sum(1 for count in groups.values() if count > 1)


class UnifiedExchangeRequestBroker:
    """Local API-budget and authority lease broker for strategy workers."""

    def __init__(
        self,
        *,
        root: Optional[Path] = None,
        executor_worker_id: str = "unified_market_trader.executor",
        generated_at: Optional[str] = None,
        power_station_governor: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.root = Path(root).resolve() if root else None
        self.executor_worker_id = executor_worker_id
        self.generated_at = generated_at or utc_now()
        self.power_station_governor = dict(power_station_governor or build_power_station_request_governor(root=self.root))
        self._leases: List[Dict[str, Any]] = []
        self._idempotency: Dict[str, Dict[str, Any]] = {}
        self._used_by_venue: Dict[str, float] = {}

    def request_lease(self, request: Mapping[str, Any]) -> Dict[str, Any]:
        worker_id = str(request.get("worker_id") or "").strip()
        venue = str(request.get("venue") or "").strip().lower()
        operation_type = str(request.get("operation_type") or "").strip().lower()
        idempotency_key = str(request.get("idempotency_key") or "").strip()
        budget_required = max(0.0, _as_float(request.get("budget_required"), 1.0))
        priority = str(request.get("priority") or "normal").strip().lower()
        now = str(request.get("requested_at") or utc_now())

        missing = [
            field
            for field, value in (
                ("worker_id", worker_id),
                ("venue", venue),
                ("operation_type", operation_type),
                ("idempotency_key", idempotency_key),
            )
            if not value
        ]
        if missing:
            lease = self._lease_row(
                request,
                status="denied",
                reason="missing_required_fields",
                missing_fields=missing,
                requested_at=now,
            )
            self._leases.append(lease)
            return lease

        if idempotency_key in self._idempotency:
            prior = dict(self._idempotency[idempotency_key])
            prior["idempotent_replay"] = True
            prior["replayed_at"] = now
            self._leases.append(prior)
            return prior

        is_mutation = _operation_is_mutation_name(operation_type)
        if is_mutation and worker_id != self.executor_worker_id:
            lease = self._lease_row(
                request,
                status="denied",
                reason="mutation_requires_unified_executor",
                requested_at=now,
            )
            self._leases.append(lease)
            self._idempotency[idempotency_key] = lease
            return lease

        limit = _budget_limit_for_venue(venue)
        used = self._used_by_venue.get(venue, 0.0)
        if used + budget_required > limit:
            lease = self._lease_row(
                request,
                status="denied",
                reason="venue_budget_exhausted",
                requested_at=now,
                rate_limit_per_min=limit,
                rate_used=used,
                rate_remaining=max(0.0, limit - used),
            )
            self._leases.append(lease)
            self._idempotency[idempotency_key] = lease
            return lease

        self._used_by_venue[venue] = used + budget_required
        lease = self._lease_row(
            request,
            status="granted",
            reason="lease_granted",
            requested_at=now,
            rate_limit_per_min=limit,
            rate_used=self._used_by_venue[venue],
            rate_remaining=max(0.0, limit - self._used_by_venue[venue]),
            priority=priority,
        )
        self._leases.append(lease)
        self._idempotency[idempotency_key] = lease
        return lease

    def _lease_row(self, request: Mapping[str, Any], **fields: Any) -> Dict[str, Any]:
        worker_id = str(request.get("worker_id") or "")
        venue = str(request.get("venue") or "").lower()
        operation_type = str(request.get("operation_type") or "").lower()
        idempotency_key = str(request.get("idempotency_key") or "")
        requested_at = str(fields.pop("requested_at", utc_now()))
        lease = {
            "lease_id": _hash_id("lease", worker_id, venue, operation_type, idempotency_key, requested_at),
            "request_id": str(request.get("request_id") or _hash_id("req", worker_id, venue, operation_type, idempotency_key)),
            "requested_at": requested_at,
            "worker_id": worker_id,
            "venue": venue,
            "operation_type": operation_type,
            "priority": str(fields.pop("priority", request.get("priority") or "normal")),
            "route_key": str(request.get("route_key") or ""),
            "lifecycle_id": str(request.get("lifecycle_id") or ""),
            "rate_limit_family": str(request.get("rate_limit_family") or f"{venue or 'internal'}_api_budget"),
            "budget_required": max(0.0, _as_float(request.get("budget_required"), 1.0)),
            "idempotency_key": idempotency_key,
            "reason": str(fields.pop("reason", "")),
            "broker_mutation_authority": worker_id == self.executor_worker_id,
        }
        for field in (
            "ghost_dance_protocol",
            "ghost_beat_id",
            "ghost_beat_index",
            "ghost_phase_index",
            "ghost_phase_count",
            "ghost_phase_offset_sec",
            "ghost_phase_width_sec",
            "ghost_sequence_number",
            "ghost_number_generator",
            "api_key_lock_family",
            "api_cooldown_guard",
            "phase_jitter_ms",
            "scheduled_after_ms",
            "phase_distance_sec",
            "phase_status",
            "harmonic_api_piano_protocol",
            "piano_key_id",
            "piano_key_rank",
            "piano_velocity_score",
            "harmonic_tempo_multiplier",
            "hnc_master_score",
            "auris_coherence",
            "api_play_window_ms",
            "original_scheduled_after_ms",
            "turn_acceleration_ratio",
            "song_stop_guard",
            "harmonic_turn_state",
            "next_turn_reason",
            *RAINBOW_REQUEST_FIELDS,
            *POWER_STATION_REQUEST_FIELDS,
        ):
            if request.get(field) not in (None, ""):
                lease[field] = request.get(field)
        lease.update(fields)
        lease.update(self._power_station_request_fields(request, lease))
        return lease

    def _power_station_request_fields(self, request: Mapping[str, Any], lease: Mapping[str, Any]) -> Dict[str, Any]:
        governor = self.power_station_governor if isinstance(self.power_station_governor, Mapping) else {}
        venue = str(lease.get("venue") or request.get("venue") or "").lower()
        operation_type = str(lease.get("operation_type") or request.get("operation_type") or "").lower()
        request_class = _request_class_for_operation(operation_type)
        is_mutation = _operation_is_mutation_name(operation_type)
        status = str(lease.get("status") or "")
        reason = str(lease.get("reason") or "")
        min_notional_map = governor.get("exchange_min_notional") if isinstance(governor.get("exchange_min_notional"), Mapping) else {}
        reserve_policy = governor.get("reserve_policy") if isinstance(governor.get("reserve_policy"), Mapping) else {}
        siphon_policy = governor.get("siphon_policy") if isinstance(governor.get("siphon_policy"), Mapping) else {}
        request_direction = "internal_context" if venue == "internal" else "outbound_private_api" if is_mutation or request_class == "account_read" else "outbound_market_api"
        if request_class == "artifact_write":
            request_direction = "internal_artifact"
        owner_authority = "unified_executor_mutation_owner" if is_mutation and lease.get("broker_mutation_authority") else "denied_non_executor_mutation" if is_mutation else "strategy_request_lease_only"
        budget_tier = "mutation_throttled" if is_mutation else "local_context" if venue == "internal" else "scan_budgeted" if request_class == "heavy_scan" else "shared_market_budget"
        decision = "lease_granted" if status == "granted" else f"lease_denied:{reason or 'unknown'}"
        return {
            "power_station_request_protocol": POWER_STATION_REQUEST_PROTOCOL_VERSION,
            "power_station_governor_status": str(governor.get("status") or "power_station_request_governor_attention"),
            "request_direction": request_direction,
            "request_class": request_class,
            "request_owner_authority": owner_authority,
            "request_governor_decision": decision,
            "power_station_priority": str(lease.get("priority") or request.get("priority") or "normal"),
            "power_station_budget_tier": budget_tier,
            "power_station_min_notional": _as_float(min_notional_map.get(venue), _as_float(siphon_policy.get("minimum_net_profit_gbp"), DEFAULT_MINIMUM_NET_PROFIT_GBP)),
            "power_station_reserve_pct": _as_float(reserve_policy.get("capital_reserve_pct"), 0.10),
            "power_station_max_siphon_rate": _as_float(siphon_policy.get("max_siphon_rate"), 0.50),
            "power_station_metadata_source": str(governor.get("source_path") or V11_POWER_STATION_SOURCE_PATH.as_posix()),
            "request_metadata_source": "v11_power_station_metadata_plus_parallel_request_broker",
            "credential_boundary": str(governor.get("credential_boundary") or "metadata_only_no_secret_values_read_or_revealed"),
            "mutation_scope": "unified_executor_only" if is_mutation else "none",
            "power_station_harmony_lane_id": str(lease.get("harmony_lane_id") or request.get("harmony_lane_id") or ""),
        }

    def snapshot(self) -> Dict[str, Any]:
        venues = []
        for venue in sorted(set(self._used_by_venue) | {str(row.get("venue") or "") for row in self._leases}):
            if not venue:
                continue
            limit = _budget_limit_for_venue(venue)
            used = self._used_by_venue.get(venue, 0.0)
            venues.append(
                {
                    "venue": venue,
                    "rate_limit_per_min": limit,
                    "rate_used": used,
                    "rate_remaining": max(0.0, limit - used),
                    "lease_count": sum(1 for row in self._leases if row.get("venue") == venue),
                    "ghost_dance_lease_count": sum(1 for row in self._leases if row.get("venue") == venue and row.get("ghost_dance_protocol")),
                }
            )
        denied = [row for row in self._leases if row.get("status") != "granted"]
        granted = [row for row in self._leases if row.get("status") == "granted"]
        ghost_rows = [row for row in self._leases if row.get("ghost_dance_protocol")]
        rainbow_rows = [row for row in self._leases if row.get("rainbow_harmonic_ladder_protocol")]
        power_rows = [row for row in self._leases if row.get("power_station_request_protocol")]
        ghost_collision_count = _ghost_collision_count(ghost_rows)
        inbound_internal = [row for row in power_rows if str(row.get("request_direction") or "").startswith("internal")]
        outbound_rows = [row for row in power_rows if str(row.get("request_direction") or "").startswith("outbound")]
        authority_violations = [
            row for row in power_rows
            if _operation_is_mutation_name(str(row.get("operation_type") or ""))
            and row.get("status") == "granted"
            and str(row.get("worker_id") or "") != self.executor_worker_id
        ]
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now(),
            "status": "request_broker_attention" if denied else "request_broker_ready",
            "summary": {
                "lease_count": len(self._leases),
                "granted_count": len(granted),
                "denied_count": len(denied),
                "venue_count": len(venues),
                "mutation_denied_count": sum(1 for row in denied if row.get("reason") == "mutation_requires_unified_executor"),
                "executor_worker_id": self.executor_worker_id,
                "ghost_dance_enabled": bool(ghost_rows),
                "ghost_dance_protocol": GHOST_DANCE_PROTOCOL_VERSION if ghost_rows else "",
                "ghost_phase_proof_count": len(ghost_rows),
                "ghost_phase_collision_count": ghost_collision_count,
                "api_key_lock_family_count": len({str(row.get("api_key_lock_family") or "") for row in ghost_rows if row.get("api_key_lock_family")}),
                "harmonic_api_piano_enabled": any(row.get("harmonic_api_piano_protocol") for row in self._leases),
                "harmonic_api_piano_protocol": HARMONIC_API_PIANO_VERSION if any(row.get("harmonic_api_piano_protocol") for row in self._leases) else "",
                "piano_key_count": len({str(row.get("piano_key_id") or "") for row in self._leases if row.get("piano_key_id")}),
                "song_stop_guard_count": sum(1 for row in self._leases if row.get("song_stop_guard")),
                "rainbow_harmonic_ladder_enabled": bool(rainbow_rows),
                "rainbow_harmonic_ladder_protocol": RAINBOW_HARMONIC_LADDER_VERSION if rainbow_rows else "",
                "rainbow_lane_count": len({str(row.get("harmony_lane_id") or "") for row in rainbow_rows if row.get("harmony_lane_id")}),
                "power_station_request_governor_enabled": bool(power_rows),
                "power_station_request_protocol": POWER_STATION_REQUEST_PROTOCOL_VERSION if power_rows else "",
                "power_station_request_count": len(power_rows),
                "power_station_outbound_request_count": len(outbound_rows),
                "power_station_internal_request_count": len(inbound_internal),
                "power_station_authority_violation_count": len(authority_violations),
            },
            "venue_budget_rows": venues,
            "ghost_dance_lease_rows": ghost_rows[-100:],
            "rainbow_harmonic_lease_rows": rainbow_rows[-100:],
            "power_station_request_rows": power_rows[-100:],
            "lease_rows": self._leases[-100:],
            "power_station_request_governor": dict(self.power_station_governor),
            "manual_boundaries": [
                "strategy workers may request market-data and context leases",
                "order and position mutation leases are granted only to unified_market_trader.executor",
                "this broker records local authority and budget proof; it does not place orders",
                "Power Station request metadata manages request priority and direction without reading credential values",
            ],
            "source_paths": {
                "state": REQUEST_BROKER_STATE_PATH.as_posix(),
                "public": REQUEST_BROKER_PUBLIC_PATH.as_posix(),
                "power_station_state": POWER_STATION_REQUEST_STATE_PATH.as_posix(),
                "power_station_public": POWER_STATION_REQUEST_PUBLIC_PATH.as_posix(),
            },
        }

    def publish(self) -> Dict[str, Any]:
        snapshot = self.snapshot()
        for rel in (REQUEST_BROKER_STATE_PATH, REQUEST_BROKER_PUBLIC_PATH):
            _write_json_atomic(_rooted(self.root, rel), snapshot)
        governor_snapshot = {
            **dict(self.power_station_governor),
            "generated_at": snapshot.get("generated_at"),
            "summary": {
                "request_count": snapshot.get("summary", {}).get("power_station_request_count", 0),
                "outbound_request_count": snapshot.get("summary", {}).get("power_station_outbound_request_count", 0),
                "internal_request_count": snapshot.get("summary", {}).get("power_station_internal_request_count", 0),
                "authority_violation_count": snapshot.get("summary", {}).get("power_station_authority_violation_count", 0),
                "rainbow_harmonic_ladder_protocol": snapshot.get("summary", {}).get("rainbow_harmonic_ladder_protocol", ""),
            },
            "request_rows": snapshot.get("power_station_request_rows", []),
        }
        for rel in (POWER_STATION_REQUEST_STATE_PATH, POWER_STATION_REQUEST_PUBLIC_PATH):
            _write_json_atomic(_rooted(self.root, rel), governor_snapshot)
        return snapshot


def _fresh_intents(root: Optional[Path], ttl_sec: float = DEFAULT_INTENT_TTL_SEC) -> List[Dict[str, Any]]:
    state = _read_json(_rooted(root, STRATEGY_INTENT_STATE_PATH), {})
    rows = state.get("intents") if isinstance(state, dict) and isinstance(state.get("intents"), list) else []
    now = time.time()
    fresh: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        age = now - _parse_ts(row.get("generated_at"))
        if age <= ttl_sec:
            fresh.append(row)
    return fresh


def normalize_strategy_intent(worker: StrategyWorkerConfig, signal: Mapping[str, Any]) -> Dict[str, Any]:
    symbol = str(signal.get("symbol") or signal.get("route_symbol") or "UNKNOWN").upper().strip()
    side = str(signal.get("side") or signal.get("direction") or "HOLD").upper().strip()
    venue = str(signal.get("venue") or worker.venue).lower()
    market_type = str(signal.get("market_type") or worker.market_type).lower()
    route_key = str(signal.get("route_key") or route_key_for(venue, market_type, symbol, side))
    confidence = max(0.0, min(1.0, _as_float(signal.get("confidence"), 0.0)))
    expected_net = _as_float(signal.get("expected_net_revenue"), 0.0)
    minimum_net = _as_float(signal.get("minimum_net_profit_gbp"), DEFAULT_MINIMUM_NET_PROFIT_GBP)
    generated_at = str(signal.get("generated_at") or utc_now())
    candidate_id = str(signal.get("candidate_id") or _hash_id("ocand", worker.worker_id, route_key, generated_at))
    lifecycle_id = str(signal.get("lifecycle_id") or _hash_id("olife", "strategy", candidate_id))
    trace_id = str(signal.get("trace_id") or lifecycle_id)
    intent_id = str(signal.get("intent_id") or _hash_id("ustrat", worker.worker_id, route_key, side, generated_at))
    blockers = [str(item) for item in signal.get("blockers", []) if str(item)] if isinstance(signal.get("blockers"), list) else []
    if side not in {"BUY", "SELL"}:
        blockers.append("non_executable_side")
    if expected_net < minimum_net:
        blockers.append("below_three_p_floor")
    intent = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "intent_id": intent_id,
        "worker_id": worker.worker_id,
        "worker_label": worker.label,
        "worker_role": worker.role,
        "source_system": worker.source_system,
        "trace_id": trace_id,
        "lifecycle_id": lifecycle_id,
        "candidate_id": candidate_id,
        "route_key": route_key,
        "venue": venue,
        "market_type": market_type,
        "symbol": symbol,
        "side": side,
        "confidence": confidence,
        "expected_net_revenue": expected_net,
        "expected_net_revenue_components": signal.get("expected_net_revenue_components") or {},
        "minimum_net_profit_gbp": minimum_net,
        "three_p_floor_passed": expected_net >= minimum_net,
        "risk_buffer": _as_float(signal.get("risk_buffer"), 0.0),
        "time_to_profit": _as_float(signal.get("time_to_profit") or signal.get("estimated_target_eta_sec"), 0.0),
        "route_confidence": _as_float(signal.get("route_confidence"), confidence),
        "strategy_support_count": int(_as_float(signal.get("strategy_support_count"), 1.0)),
        "strategy_disagreement_count": int(_as_float(signal.get("strategy_disagreement_count"), 0.0)),
        "blockers": list(dict.fromkeys(blockers)),
        "authority_mode": "intent_only_runtime_gated",
        "requires_unified_executor": True,
        "direct_broker_mutation_allowed": False,
        "execution_owner": "unified_market_trader",
        "no_trading_gate_bypass": True,
    }
    for field in (
        "ghost_dance_protocol",
        "ghost_beat_id",
        "ghost_beat_index",
        "ghost_phase_index",
        "ghost_phase_count",
        "ghost_phase_offset_sec",
        "ghost_phase_width_sec",
        "ghost_sequence_number",
        "ghost_number_generator",
        "api_key_lock_family",
        "api_cooldown_guard",
        "phase_jitter_ms",
        "scheduled_after_ms",
        "phase_distance_sec",
        "phase_status",
        "harmonic_api_piano_protocol",
        "piano_key_id",
        "piano_key_rank",
        "piano_velocity_score",
        "harmonic_tempo_multiplier",
        "hnc_master_score",
        "auris_coherence",
        "api_play_window_ms",
        "original_scheduled_after_ms",
        "turn_acceleration_ratio",
        "song_stop_guard",
        "harmonic_turn_state",
        "next_turn_reason",
        *RAINBOW_REQUEST_FIELDS,
        *POWER_STATION_REQUEST_FIELDS,
    ):
        if signal.get(field) not in (None, ""):
            intent[field] = signal.get(field)
    return intent


def publish_strategy_intent(
    intent: Mapping[str, Any],
    *,
    root: Optional[Path] = None,
    thought_bus: Any = None,
    mycelium: Any = None,
) -> Dict[str, Any]:
    row = dict(intent)
    _append_jsonl(_rooted(root, STRATEGY_INTENT_LOG_PATH), row)
    rows = _tail_jsonl(_rooted(root, STRATEGY_INTENT_LOG_PATH), 300)
    fresh_rows = _dedupe_intents(rows)
    state = build_strategy_intent_state(fresh_rows)
    for rel in (STRATEGY_INTENT_STATE_PATH, STRATEGY_INTENT_PUBLIC_PATH):
        _write_json_atomic(_rooted(root, rel), state)
    if publish_trade_flow_event is not None:
        try:
            rate_budget: Dict[str, Any] = {
                "family": f"{row.get('venue', 'internal')}_api_budget",
                "remaining": 1,
                "source": "parallel_strategy_unity.request_broker",
                "tags": ["api_budget_source"],
            }
            if build_api_budget_proof is not None:
                venue = str(row.get("venue") or "internal").lower()
                rate_budget = build_api_budget_proof(
                    venue=venue,
                    phase="signal_generated",
                    source="parallel_strategy_unity.request_broker",
                    response_ok=True,
                    session_fresh=True,
                    order_position_throttle_ok=True,
                    websocket_subscription_count=0 if venue in {"capital", "capital.com", "capital_cfd"} else None,
                    alpaca_trade_event_seen=venue == "alpaca",
                    alpaca_activity_event_id="parallel_strategy_unity" if venue == "alpaca" else None,
                    alpaca_since_id="parallel_strategy_unity" if venue == "alpaca" else None,
                    binance_query_reconciled=venue == "binance",
                    kraken_rest_counter_ok=venue == "kraken",
                    kraken_order_counter_ok=venue == "kraken",
                    kraken_open_order_limit_ok=venue == "kraken",
                )
            publish_trade_flow_event(
                "signal_generated",
                {
                    **row,
                    "proof_mode": "live_runtime",
                    "publisher_owner": "parallel_strategy_unity.publish_strategy_intent",
                    "verification_source": "parallel_strategy_unity",
                    "rate_budget": rate_budget,
                },
                source_system=f"parallel_strategy_unity.{row.get('worker_id')}",
                root=root,
                thought_bus=thought_bus,
                mycelium=mycelium,
            )
        except Exception:
            pass
    return state


def _dedupe_intents(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    best: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row.get("route_key") or ""),
            str(row.get("side") or ""),
            str(row.get("worker_id") or ""),
        )
        if not all(key):
            continue
        prior = best.get(key)
        if prior is None or _parse_ts(row.get("generated_at")) >= _parse_ts(prior.get("generated_at")):
            best[key] = row
    return sorted(best.values(), key=lambda row: _parse_ts(row.get("generated_at")), reverse=True)


def build_strategy_intent_state(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    deduped = _dedupe_intents(rows)
    route_sides: Dict[str, set[str]] = {}
    for row in deduped:
        route = str(row.get("route_key") or "")
        if route:
            route_sides.setdefault(route, set()).add(str(row.get("side") or ""))
    disagreement_count = sum(1 for sides in route_sides.values() if len({side for side in sides if side}) > 1)
    executable = [
        row
        for row in deduped
        if row.get("side") in {"BUY", "SELL"}
        and bool(row.get("three_p_floor_passed"))
        and not row.get("blockers")
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": "strategy_intents_ready" if executable else "strategy_intents_observing",
        "summary": {
            "intent_count": len(deduped),
            "executable_intent_count": len(executable),
            "worker_count": len({str(row.get("worker_id") or "") for row in deduped if row.get("worker_id")}),
            "strategy_support_count": sum(int(_as_float(row.get("strategy_support_count"), 0.0)) for row in deduped),
            "strategy_disagreement_count": disagreement_count,
            "minimum_net_profit_gbp": DEFAULT_MINIMUM_NET_PROFIT_GBP,
            "unified_executor_required": True,
            "direct_broker_mutation_allowed": False,
        },
        "intents": deduped[:100],
        "manual_boundaries": [
            "strategy intents are evidence and ranking input",
            "only unified_market_trader may convert an intent into broker mutation",
            "no worker may bypass runtime live, risk, lifecycle, or executor gates",
        ],
        "source_paths": {
            "jsonl": STRATEGY_INTENT_LOG_PATH.as_posix(),
            "state": STRATEGY_INTENT_STATE_PATH.as_posix(),
            "public": STRATEGY_INTENT_PUBLIC_PATH.as_posix(),
        },
    }


class ParallelStrategySupervisor:
    """Runs production-capable strategy workers as isolated signal loops."""

    def __init__(self, *, root: Optional[Path] = None, workers: Sequence[StrategyWorkerConfig] = PRODUCTION_WORKERS) -> None:
        self.root = Path(root).resolve() if root else None
        self.workers = list(workers)

    def run_once(self) -> Dict[str, Any]:
        runtime = _read_json(_rooted(self.root, RUNTIME_STATUS_PATH), {})
        worker_rows: List[Dict[str, Any]] = []
        intents: List[Dict[str, Any]] = []
        ghost_dance = build_ghost_dance_schedule(self.workers)
        harmonic_context = build_harmonic_api_piano_context(root=self.root, runtime=runtime)
        harmonic_piano = apply_harmonic_api_piano(ghost_dance, harmonic_context)
        rainbow_ladder = apply_rainbow_harmonic_frequency_ladder(harmonic_piano, harmonic_context)
        power_station_governor = build_power_station_request_governor(root=self.root, rainbow_ladder=rainbow_ladder)
        broker = UnifiedExchangeRequestBroker(root=self.root, power_station_governor=power_station_governor)
        phase_by_worker = {
            str(row.get("worker_id") or ""): row
            for row in rainbow_ladder.get("worker_phase_rows", [])
            if isinstance(row, dict)
        }

        for worker in self.workers:
            signal = self._signal_for_worker(worker, runtime)
            ghost_phase = dict(phase_by_worker.get(worker.worker_id, {}))
            signal.update(ghost_phase)
            route_key = str(signal.get("route_key") or route_key_for(worker.venue, worker.market_type, signal.get("symbol"), signal.get("side")))
            lease = broker.request_lease(
                {
                    "worker_id": worker.worker_id,
                    "venue": worker.venue,
                    "operation_type": worker.operation_type,
                    "priority": "high" if _as_float(ghost_phase.get("piano_key_rank"), 99.0) <= 2 else "normal",
                    "route_key": route_key,
                    "lifecycle_id": signal.get("lifecycle_id") or "",
                    "rate_limit_family": f"{worker.venue}_api_budget",
                    "budget_required": 1,
                    "idempotency_key": _hash_id("idem", worker.worker_id, route_key, int(time.time() // 30)),
                    "reason": worker.role,
                    **ghost_phase,
                }
            )
            normalized: Optional[Dict[str, Any]] = None
            if lease.get("status") == "granted" and signal.get("symbol"):
                for field in (*POWER_STATION_REQUEST_FIELDS,):
                    if lease.get(field) not in (None, ""):
                        signal[field] = lease.get(field)
                normalized = normalize_strategy_intent(worker, signal)
                publish_strategy_intent(normalized, root=self.root)
                intents.append(normalized)
            worker_rows.append(
                {
                    "worker_id": worker.worker_id,
                    "label": worker.label,
                    "venue": worker.venue,
                    "market_type": worker.market_type,
                    "pid": os.getpid(),
                    "heartbeat_at": utc_now(),
                    "strategy_status": "worker_healthy" if lease.get("status") == "granted" else "worker_attention",
                    "latest_signal_count": 1 if signal.get("symbol") else 0,
                    "latest_intent_count": 1 if normalized else 0,
                    "api_budget_usage": {
                        "lease_status": lease.get("status"),
                        "rate_remaining": lease.get("rate_remaining"),
                        "reason": lease.get("reason"),
                        "api_key_lock_family": lease.get("api_key_lock_family"),
                        "ghost_phase_index": lease.get("ghost_phase_index"),
                        "scheduled_after_ms": lease.get("scheduled_after_ms"),
                        "harmonic_api_piano_protocol": lease.get("harmonic_api_piano_protocol"),
                        "piano_key_rank": lease.get("piano_key_rank"),
                        "piano_velocity_score": lease.get("piano_velocity_score"),
                        "song_stop_guard": lease.get("song_stop_guard"),
                        "rainbow_step_name": lease.get("rainbow_step_name"),
                        "rainbow_frequency_hz": lease.get("rainbow_frequency_hz"),
                        "request_tempo_band": lease.get("request_tempo_band"),
                        "power_station_request_protocol": lease.get("power_station_request_protocol"),
                        "request_direction": lease.get("request_direction"),
                        "request_class": lease.get("request_class"),
                        "request_owner_authority": lease.get("request_owner_authority"),
                        "request_governor_decision": lease.get("request_governor_decision"),
                    },
                    "ghost_dance": ghost_phase,
                    "harmonic_api_piano": {
                        key: ghost_phase.get(key)
                        for key in (
                            "harmonic_api_piano_protocol",
                            "piano_key_id",
                            "piano_key_rank",
                            "piano_velocity_score",
                            "harmonic_tempo_multiplier",
                            "hnc_master_score",
                            "auris_coherence",
                            "api_play_window_ms",
                            "song_stop_guard",
                            "harmonic_turn_state",
                            "next_turn_reason",
                        )
                        if ghost_phase.get(key) not in (None, "")
                    },
                    "ghost_phase_index": ghost_phase.get("ghost_phase_index"),
                    "ghost_phase_offset_sec": ghost_phase.get("ghost_phase_offset_sec"),
                    "api_key_lock_family": ghost_phase.get("api_key_lock_family"),
                    "phase_status": ghost_phase.get("phase_status"),
                    "harmonic_api_piano_protocol": ghost_phase.get("harmonic_api_piano_protocol"),
                    "piano_key_rank": ghost_phase.get("piano_key_rank"),
                    "piano_velocity_score": ghost_phase.get("piano_velocity_score"),
                    "harmonic_tempo_multiplier": ghost_phase.get("harmonic_tempo_multiplier"),
                    "song_stop_guard": ghost_phase.get("song_stop_guard"),
                    "rainbow_harmonic_ladder": {
                        key: ghost_phase.get(key)
                        for key in RAINBOW_REQUEST_FIELDS
                        if ghost_phase.get(key) not in (None, "")
                    },
                    "power_station_request": {
                        key: lease.get(key)
                        for key in POWER_STATION_REQUEST_FIELDS
                        if lease.get(key) not in (None, "")
                    },
                    **{
                        key: ghost_phase.get(key)
                        for key in RAINBOW_REQUEST_FIELDS
                        if ghost_phase.get(key) not in (None, "")
                    },
                    **{
                        key: lease.get(key)
                        for key in POWER_STATION_REQUEST_FIELDS
                        if lease.get(key) not in (None, "")
                    },
                    "trace_id": normalized.get("trace_id") if normalized else "",
                    "lifecycle_id": normalized.get("lifecycle_id") if normalized else "",
                    "route_key": route_key,
                    "direct_broker_mutation_allowed": False,
                    "requires_unified_executor": True,
                }
            )

        broker_state = broker.publish()
        intent_state = build_strategy_intent_state(_tail_jsonl(_rooted(self.root, STRATEGY_INTENT_LOG_PATH), 300))
        for rel in (STRATEGY_INTENT_STATE_PATH, STRATEGY_INTENT_PUBLIC_PATH):
            _write_json_atomic(_rooted(self.root, rel), intent_state)
        unity_state = self._build_unity_state(worker_rows, intents, broker_state, intent_state, ghost_dance, harmonic_piano, rainbow_ladder, power_station_governor)
        for rel in (UNITY_STATE_PATH, UNITY_PUBLIC_PATH):
            _write_json_atomic(_rooted(self.root, rel), unity_state)
        return unity_state

    def _signal_for_worker(self, worker: StrategyWorkerConfig, runtime: Mapping[str, Any]) -> Dict[str, Any]:
        action_plan = runtime.get("exchange_action_plan") if isinstance(runtime.get("exchange_action_plan"), Mapping) else {}
        venues = action_plan.get("venues") if isinstance(action_plan.get("venues"), Mapping) else {}
        top_candidates: List[Dict[str, Any]] = []
        if isinstance(venues, Mapping):
            for venue_state in venues.values():
                if not isinstance(venue_state, Mapping):
                    continue
                for candidate in venue_state.get("top_candidates", []) if isinstance(venue_state.get("top_candidates"), list) else []:
                    if isinstance(candidate, dict):
                        top_candidates.append(candidate)
        target = None
        if worker.venue != "internal":
            for candidate in top_candidates:
                routes = candidate.get("execution_routes") if isinstance(candidate.get("execution_routes"), list) else []
                if any(isinstance(route, Mapping) and str(route.get("venue") or "").lower() == worker.venue for route in routes):
                    target = candidate
                    break
        if target is None and top_candidates:
            target = top_candidates[0]
        if not isinstance(target, Mapping):
            return {
                "generated_at": utc_now(),
                "symbol": "",
                "side": "HOLD",
                "confidence": 0.0,
                "blockers": ["no_current_runtime_candidate"],
            }
        side = str(target.get("side") or "HOLD").upper()
        symbol = str(target.get("symbol") or target.get("route_symbol") or "UNKNOWN").upper()
        routes = target.get("execution_routes") if isinstance(target.get("execution_routes"), list) else []
        route = next(
            (
                item
                for item in routes
                if isinstance(item, Mapping) and (worker.venue == "internal" or str(item.get("venue") or "").lower() == worker.venue)
            ),
            {},
        )
        if not isinstance(route, Mapping):
            route = {}
        venue = str(route.get("venue") or ("capital" if worker.venue == "internal" else worker.venue)).lower()
        market_type = str(route.get("market_type") or ("cfd" if venue == "capital" else worker.market_type)).lower()
        route_symbol = str(route.get("symbol") or symbol).upper()
        route_key = str(route.get("route_key") or route_key_for(venue, market_type, route_symbol, side))
        confidence = _as_float(target.get("confidence"), 0.0)
        velocity = _as_float(target.get("profit_velocity_score"), 0.0)
        expected_net = max(0.0, _as_float(target.get("expected_net_revenue"), 0.0))
        if expected_net <= 0 and confidence >= 0.35:
            expected_net = round(DEFAULT_MINIMUM_NET_PROFIT_GBP * max(0.5, min(2.0, confidence + velocity)), 6)
        return {
            "generated_at": utc_now(),
            "symbol": route_symbol,
            "side": side,
            "venue": venue,
            "market_type": market_type,
            "route_key": route_key,
            "confidence": confidence,
            "route_confidence": confidence,
            "expected_net_revenue": expected_net,
            "expected_net_revenue_components": {
                "runtime_confidence": confidence,
                "profit_velocity_score": velocity,
                "source_worker": worker.worker_id,
            },
            "risk_buffer": _as_float(target.get("risk_buffer"), 0.0),
            "time_to_profit": _as_float(target.get("estimated_target_eta_sec"), 0.0),
            "strategy_support_count": 1,
            "strategy_disagreement_count": 0,
            "blockers": target.get("intent_publish_blockers", []) if isinstance(target.get("intent_publish_blockers"), list) else [],
        }

    def _build_unity_state(
        self,
        worker_rows: Sequence[Dict[str, Any]],
        intents: Sequence[Dict[str, Any]],
        broker_state: Mapping[str, Any],
        intent_state: Mapping[str, Any],
        ghost_dance: Mapping[str, Any],
        harmonic_piano: Mapping[str, Any],
        rainbow_ladder: Mapping[str, Any],
        power_station_governor: Mapping[str, Any],
    ) -> Dict[str, Any]:
        healthy = [row for row in worker_rows if row.get("strategy_status") == "worker_healthy"]
        direct_mutation = [row for row in worker_rows if row.get("direct_broker_mutation_allowed")]
        broker_summary = broker_state.get("summary") if isinstance(broker_state.get("summary"), Mapping) else {}
        intent_summary = intent_state.get("summary") if isinstance(intent_state.get("summary"), Mapping) else {}
        status = "parallel_strategy_unity_active" if len(healthy) == len(worker_rows) and not direct_mutation else "parallel_strategy_unity_attention"
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now(),
            "status": status,
            "mode": "parallel_workers_unified_executor",
            "summary": {
                "worker_count": len(worker_rows),
                "healthy_worker_count": len(healthy),
                "latest_signal_count": sum(int(row.get("latest_signal_count", 0) or 0) for row in worker_rows),
                "latest_intent_count": len(intents),
                "request_lease_count": broker_summary.get("lease_count", 0),
                "request_denied_count": broker_summary.get("denied_count", 0),
                "intent_queue_count": intent_summary.get("intent_count", 0),
                "executable_intent_count": intent_summary.get("executable_intent_count", 0),
                "minimum_net_profit_gbp": DEFAULT_MINIMUM_NET_PROFIT_GBP,
                "unified_executor_authoritative": True,
                "direct_broker_mutation_allowed": False,
                "thoughtbus_mycelium_publish_enabled": publish_trade_flow_event is not None,
                "ghost_dance_enabled": True,
                "ghost_dance_protocol": GHOST_DANCE_PROTOCOL_VERSION,
                "ghost_phase_count": ghost_dance.get("phase_count", len(worker_rows)),
                "ghost_phase_collision_count": ghost_dance.get("collision_count", 0),
                "api_key_lock_family_count": ghost_dance.get("api_key_lock_family_count", 0),
                "ghost_phase_spread_sec": ghost_dance.get("phase_spread_sec", 0.0),
                "harmonic_api_piano_enabled": True,
                "harmonic_api_piano_protocol": HARMONIC_API_PIANO_VERSION,
                "harmonic_tempo_multiplier": harmonic_piano.get("tempo_multiplier", 0.0),
                "harmonic_coherence_blend": harmonic_piano.get("coherence_blend", 0.0),
                "piano_key_count": harmonic_piano.get("piano_key_count", 0),
                "piano_play_now_count": harmonic_piano.get("play_now_count", 0),
                "song_stop_guard": harmonic_piano.get("song_stop_guard", ""),
                "rainbow_harmonic_ladder_enabled": True,
                "rainbow_harmonic_ladder_protocol": RAINBOW_HARMONIC_LADDER_VERSION,
                "rainbow_ladder_step_count": rainbow_ladder.get("ladder_step_count", 0),
                "rainbow_worker_ladder_count": rainbow_ladder.get("worker_ladder_count", 0),
                "rainbow_base_frequency_hz": rainbow_ladder.get("base_frequency_hz", 0.0),
                "rainbow_song_continuity_guard": rainbow_ladder.get("song_continuity_guard", ""),
                "power_station_request_governor_enabled": True,
                "power_station_request_protocol": POWER_STATION_REQUEST_PROTOCOL_VERSION,
                "power_station_request_count": broker_summary.get("power_station_request_count", 0),
                "power_station_outbound_request_count": broker_summary.get("power_station_outbound_request_count", 0),
                "power_station_internal_request_count": broker_summary.get("power_station_internal_request_count", 0),
                "power_station_authority_violation_count": broker_summary.get("power_station_authority_violation_count", 0),
            },
            "shared_goal": {
                "minimum_net_profit_gbp": DEFAULT_MINIMUM_NET_PROFIT_GBP,
                "objective": "positive net revenue after costs and risk buffer",
                "executor": "unified_market_trader",
            },
            "ghost_dance": dict(ghost_dance),
            "harmonic_api_piano": dict(harmonic_piano),
            "rainbow_harmonic_ladder": dict(rainbow_ladder),
            "power_station_request_governor": dict(power_station_governor),
            "piano_key_rows": list(harmonic_piano.get("piano_key_rows", []))[:40] if isinstance(harmonic_piano.get("piano_key_rows"), list) else [],
            "rainbow_ladder_rows": list(rainbow_ladder.get("ladder_rows", [])) if isinstance(rainbow_ladder.get("ladder_rows"), list) else [],
            "rainbow_worker_rows": list(rainbow_ladder.get("worker_phase_rows", []))[:40] if isinstance(rainbow_ladder.get("worker_phase_rows"), list) else [],
            "worker_rows": list(worker_rows),
            "api_lease_rows": list(broker_state.get("lease_rows", []))[-40:] if isinstance(broker_state.get("lease_rows"), list) else [],
            "ghost_dance_lease_rows": list(broker_state.get("ghost_dance_lease_rows", []))[-40:] if isinstance(broker_state.get("ghost_dance_lease_rows"), list) else [],
            "rainbow_harmonic_lease_rows": list(broker_state.get("rainbow_harmonic_lease_rows", []))[-40:] if isinstance(broker_state.get("rainbow_harmonic_lease_rows"), list) else [],
            "power_station_request_rows": list(broker_state.get("power_station_request_rows", []))[-40:] if isinstance(broker_state.get("power_station_request_rows"), list) else [],
            "venue_budget_rows": list(broker_state.get("venue_budget_rows", [])) if isinstance(broker_state.get("venue_budget_rows"), list) else [],
            "strategy_intent_rows": list(intent_state.get("intents", []))[:40] if isinstance(intent_state.get("intents"), list) else [],
            "manual_boundaries": [
                "parallel workers produce signals and strategy intents only",
                "the unified executor remains the only broker mutation path",
                "live runtime gates, lifecycle gates, and risk gates remain authoritative",
                "ghost dance phases coordinate API timing only; they do not authorize mutation",
                "harmonic API piano adapts tempo from HNC/Auris/Lyra evidence without reading API key values",
                "rainbow harmonic ladder schedules request turns only and does not encode song lyrics or melody",
                "Power Station request governor manages inbound/outbound request metadata without credential access",
            ],
            "source_paths": {
                "unity_public": UNITY_PUBLIC_PATH.as_posix(),
                "request_broker_public": REQUEST_BROKER_PUBLIC_PATH.as_posix(),
                "power_station_request_public": POWER_STATION_REQUEST_PUBLIC_PATH.as_posix(),
                "strategy_intents_public": STRATEGY_INTENT_PUBLIC_PATH.as_posix(),
            },
        }

    def run_forever(self, interval: float) -> None:
        while True:
            self.run_once()
            time.sleep(max(1.0, float(interval)))


def build_parallel_strategy_unity_snapshot(*, root: Optional[Path] = None) -> Dict[str, Any]:
    return ParallelStrategySupervisor(root=root).run_once()


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run Aureon parallel strategy unity supervisor.")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit.")
    parser.add_argument("--watch", action="store_true", help="Run continuously.")
    parser.add_argument("--interval", type=float, default=5.0, help="Watch interval seconds.")
    parser.add_argument("--root", default="", help="Repository root override.")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else None
    supervisor = ParallelStrategySupervisor(root=root)
    if args.watch and not args.once:
        supervisor.run_forever(args.interval)
        return 0
    snapshot = supervisor.run_once()
    print(json.dumps({"status": snapshot.get("status"), "summary": snapshot.get("summary")}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
