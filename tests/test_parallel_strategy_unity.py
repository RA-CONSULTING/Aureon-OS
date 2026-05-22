from __future__ import annotations

import json
from pathlib import Path

from aureon.trading.parallel_strategy_unity import (
    DEFAULT_MINIMUM_NET_PROFIT_GBP,
    GHOST_DANCE_PROTOCOL_VERSION,
    HARMONIC_API_PIANO_VERSION,
    POWER_STATION_REQUEST_PROTOCOL_VERSION,
    RAINBOW_HARMONIC_LADDER_VERSION,
    ParallelStrategySupervisor,
    StrategyWorkerConfig,
    UnifiedExchangeRequestBroker,
    apply_harmonic_api_piano,
    apply_rainbow_harmonic_frequency_ladder,
    build_ghost_dance_schedule,
    build_harmonic_api_piano_context,
    build_power_station_request_governor,
    build_strategy_intent_state,
    normalize_strategy_intent,
    publish_strategy_intent,
)


def test_request_broker_denies_worker_mutation_and_grants_executor(tmp_path: Path):
    broker = UnifiedExchangeRequestBroker(root=tmp_path)

    denied = broker.request_lease(
        {
            "worker_id": "capital_cfd_strategy",
            "venue": "capital",
            "operation_type": "order_submit",
            "idempotency_key": "mut-1",
            "budget_required": 1,
        }
    )
    granted = broker.request_lease(
        {
            "worker_id": "unified_market_trader.executor",
            "venue": "capital",
            "operation_type": "order_submit",
            "idempotency_key": "mut-2",
            "budget_required": 1,
        }
    )

    assert denied["status"] == "denied"
    assert denied["reason"] == "mutation_requires_unified_executor"
    assert denied["power_station_request_protocol"] == POWER_STATION_REQUEST_PROTOCOL_VERSION
    assert denied["request_owner_authority"] == "denied_non_executor_mutation"
    assert granted["status"] == "granted"
    assert granted["broker_mutation_authority"] is True
    assert granted["request_owner_authority"] == "unified_executor_mutation_owner"


def test_request_broker_idempotency_does_not_double_spend_budget(tmp_path: Path):
    broker = UnifiedExchangeRequestBroker(root=tmp_path)
    request = {
        "worker_id": "unified_market_scanner",
        "venue": "capital",
        "operation_type": "market_data",
        "idempotency_key": "same-request",
        "budget_required": 5,
    }

    first = broker.request_lease(request)
    replay = broker.request_lease(request)
    snapshot = broker.snapshot()
    capital = next(row for row in snapshot["venue_budget_rows"] if row["venue"] == "capital")

    assert first["status"] == "granted"
    assert replay["status"] == "granted"
    assert replay["idempotent_replay"] is True
    assert capital["rate_used"] == 5


def test_request_broker_blocks_over_budget(tmp_path: Path):
    broker = UnifiedExchangeRequestBroker(root=tmp_path)
    first = broker.request_lease(
        {
            "worker_id": "unified_market_scanner",
            "venue": "capital",
            "operation_type": "market_data",
            "idempotency_key": "budget-1",
            "budget_required": 44,
        }
    )
    second = broker.request_lease(
        {
            "worker_id": "capital_cfd_strategy",
            "venue": "capital",
            "operation_type": "market_data",
            "idempotency_key": "budget-2",
            "budget_required": 2,
        }
    )

    assert first["status"] == "granted"
    assert second["status"] == "denied"
    assert second["reason"] == "venue_budget_exhausted"


def test_ghost_dance_schedule_spreads_workers_out_of_phase():
    workers = [
        StrategyWorkerConfig("a", "A", "capital", "cfd", "market_data", "a", "a"),
        StrategyWorkerConfig("b", "B", "capital", "cfd", "market_data", "b", "b"),
        StrategyWorkerConfig("c", "C", "binance", "spot", "market_data", "c", "c"),
    ]

    schedule = build_ghost_dance_schedule(workers, now_ts=1_800_000_000.0, cycle_sec=30.0)
    phases = {row["ghost_phase_index"] for row in schedule["worker_phase_rows"]}

    assert schedule["protocol"] == GHOST_DANCE_PROTOCOL_VERSION
    assert schedule["collision_count"] == 0
    assert len(phases) == len(workers)
    assert all(row["api_key_lock_family"] for row in schedule["worker_phase_rows"])


def test_request_broker_preserves_ghost_dance_proof(tmp_path: Path):
    broker = UnifiedExchangeRequestBroker(root=tmp_path)

    lease = broker.request_lease(
        {
            "worker_id": "unified_market_scanner",
            "venue": "capital",
            "operation_type": "market_data",
            "idempotency_key": "ghost-lease",
            "budget_required": 1,
            "ghost_dance_protocol": GHOST_DANCE_PROTOCOL_VERSION,
            "ghost_beat_id": "gbeat-1",
            "ghost_phase_index": 2,
            "ghost_phase_count": 7,
            "api_key_lock_family": "capital:market_data",
            "scheduled_after_ms": 500,
        }
    )
    snapshot = broker.snapshot()

    assert lease["status"] == "granted"
    assert lease["ghost_dance_protocol"] == GHOST_DANCE_PROTOCOL_VERSION
    assert snapshot["summary"]["ghost_dance_enabled"] is True
    assert snapshot["summary"]["ghost_phase_collision_count"] == 0


def test_harmonic_api_piano_layers_hnc_tempo_over_ghost_schedule():
    workers = [
        StrategyWorkerConfig("unified_market_scanner", "Scanner", "capital", "cfd", "market_data", "scanner", "scan"),
        StrategyWorkerConfig("capital_cfd_strategy", "Capital", "capital", "cfd", "market_data", "capital", "capital"),
        StrategyWorkerConfig("binance_liquidity_confirmation", "Binance", "binance", "spot", "market_data", "binance", "confirm"),
    ]
    ghost = build_ghost_dance_schedule(workers, now_ts=1_800_000_000.0, cycle_sec=30.0)
    piano = apply_harmonic_api_piano(
        ghost,
        {
            "tempo_multiplier": 0.9,
            "coherence_blend": 0.8,
            "hnc_score": 0.7,
            "auris_coherence": 0.6,
            "runtime_stale": False,
        },
    )

    assert piano["protocol"] == HARMONIC_API_PIANO_VERSION
    assert piano["piano_key_count"] == len(workers)
    assert piano["song_stop_guard"] == "cooldown_preserved"
    assert {row["piano_key_rank"] for row in piano["piano_key_rows"]} == {1, 2, 3}
    assert all(row["harmonic_api_piano_protocol"] == HARMONIC_API_PIANO_VERSION for row in piano["worker_phase_rows"])


def test_rainbow_harmonic_ladder_layers_frequency_steps_over_piano():
    workers = [
        StrategyWorkerConfig("unified_market_scanner", "Scanner", "capital", "cfd", "market_data", "scanner", "scan"),
        StrategyWorkerConfig("capital_cfd_strategy", "Capital", "capital", "cfd", "market_data", "capital", "capital"),
    ]
    ghost = build_ghost_dance_schedule(workers, now_ts=1_800_000_000.0, cycle_sec=30.0)
    piano = apply_harmonic_api_piano(ghost, {"tempo_multiplier": 0.9, "hnc_score": 0.7, "auris_coherence": 0.6})
    ladder = apply_rainbow_harmonic_frequency_ladder(piano, {"lyra_frequency_hz": 528.0})

    assert ladder["protocol"] == RAINBOW_HARMONIC_LADDER_VERSION
    assert ladder["ladder_step_count"] == 7
    assert ladder["worker_ladder_count"] == len(workers)
    assert all(row["rainbow_harmonic_ladder_protocol"] == RAINBOW_HARMONIC_LADDER_VERSION for row in ladder["worker_phase_rows"])
    assert all(row["harmony_lane_id"] for row in ladder["worker_phase_rows"])


def test_power_station_request_governor_reads_repo_metadata():
    governor = build_power_station_request_governor()

    assert governor["protocol"] == POWER_STATION_REQUEST_PROTOCOL_VERSION
    assert "capital" in governor["enabled_exchanges"]
    assert governor["exchange_min_notional"]["binance"] >= 5
    assert governor["credential_boundary"] == "metadata_only_no_secret_values_read_or_revealed"


def test_harmonic_api_piano_context_reads_real_artifacts(tmp_path: Path):
    (tmp_path / "state").mkdir(parents=True)
    (tmp_path / "frontend/public").mkdir(parents=True)
    (tmp_path / "state/aureon_hnc_cognitive_proof.json").write_text(
        json.dumps(
            {
                "master_formula": {"score": 0.61},
                "auris_nodes": {"coherence": 0.44},
                "systems": {
                    "seer": {"runtime_reading": {"confidence": 0.73, "vision_grade": "clear"}},
                    "lyra": {"runtime_reading": {"resonance_score": 0.4, "resonance_frequency_hz": 647.0}},
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "frontend/public/aureon_harmonic_affect_state.json").write_text(
        json.dumps({"summary": {"runtime_stale": False, "safety_blocker_count": 0, "reward_alignment": 0.1}}),
        encoding="utf-8",
    )
    (tmp_path / "state/lambda_history.json").write_text(json.dumps({"history": [10, 10.5]}), encoding="utf-8")

    context = build_harmonic_api_piano_context(root=tmp_path, runtime={})

    assert context["protocol"] == HARMONIC_API_PIANO_VERSION
    assert context["hnc_score"] == 0.61
    assert context["auris_coherence"] == 0.44
    assert context["lyra_frequency_hz"] == 647.0
    assert context["runtime_stale"] is False
    assert context["tempo_multiplier"] > 0.35


def test_strategy_intent_normalization_requires_unified_executor():
    worker = StrategyWorkerConfig(
        "capital_cfd_strategy",
        "Capital",
        "capital",
        "cfd",
        "market_data",
        "capital_cfd_trader.strategy",
        "Capital support",
    )

    intent = normalize_strategy_intent(
        worker,
        {
            "symbol": "GOLD",
            "side": "BUY",
            "confidence": 0.8,
            "expected_net_revenue": 0.05,
            "ghost_dance_protocol": GHOST_DANCE_PROTOCOL_VERSION,
            "ghost_phase_index": 1,
            "api_key_lock_family": "capital:market_data",
            "harmonic_api_piano_protocol": HARMONIC_API_PIANO_VERSION,
            "piano_key_rank": 1,
            "piano_velocity_score": 0.8,
            "harmonic_tempo_multiplier": 0.9,
            "song_stop_guard": "cooldown_preserved",
            "rainbow_harmonic_ladder_protocol": RAINBOW_HARMONIC_LADDER_VERSION,
            "rainbow_step_index": 0,
            "rainbow_step_name": "red_root",
            "rainbow_interval_name": "root",
            "rainbow_interval_ratio": 1.0,
            "rainbow_frequency_hz": 528.0,
            "harmony_lane_id": "capital:market_data:red_root",
            "request_tempo_band": "rooted",
            "request_phase_role": "fresh_market_scan",
            "song_continuity_guard": "phase_window_preserved",
            "power_station_request_protocol": POWER_STATION_REQUEST_PROTOCOL_VERSION,
            "power_station_governor_status": "power_station_request_governor_ready",
            "request_direction": "outbound_market_api",
            "request_class": "market_data",
            "request_owner_authority": "strategy_request_lease_only",
            "request_governor_decision": "lease_granted",
            "power_station_priority": "high",
            "power_station_budget_tier": "shared_market_budget",
            "power_station_min_notional": 0.03,
            "power_station_reserve_pct": 0.1,
            "power_station_max_siphon_rate": 0.5,
            "power_station_metadata_source": "aureon/trading/v11_power_station_live.py",
            "request_metadata_source": "v11_power_station_metadata_plus_parallel_request_broker",
            "credential_boundary": "metadata_only_no_secret_values_read_or_revealed",
            "mutation_scope": "none",
            "power_station_harmony_lane_id": "capital:market_data:red_root",
        },
    )

    assert intent["worker_id"] == "capital_cfd_strategy"
    assert intent["route_key"] == "capital:cfd:GOLD:BUY"
    assert intent["three_p_floor_passed"] is True
    assert intent["requires_unified_executor"] is True
    assert intent["direct_broker_mutation_allowed"] is False
    assert intent["ghost_dance_protocol"] == GHOST_DANCE_PROTOCOL_VERSION
    assert intent["harmonic_api_piano_protocol"] == HARMONIC_API_PIANO_VERSION
    assert intent["rainbow_harmonic_ladder_protocol"] == RAINBOW_HARMONIC_LADDER_VERSION
    assert intent["power_station_request_protocol"] == POWER_STATION_REQUEST_PROTOCOL_VERSION


def test_strategy_intent_state_dedupes_and_counts_disagreement():
    rows = [
        {"worker_id": "a", "route_key": "capital:cfd:GOLD:BUY", "side": "BUY", "generated_at": "2026-05-22T08:00:00+00:00", "three_p_floor_passed": True, "blockers": []},
        {"worker_id": "a", "route_key": "capital:cfd:GOLD:BUY", "side": "BUY", "generated_at": "2026-05-22T08:00:10+00:00", "three_p_floor_passed": True, "blockers": []},
        {"worker_id": "b", "route_key": "capital:cfd:GOLD:BUY", "side": "SELL", "generated_at": "2026-05-22T08:00:11+00:00", "three_p_floor_passed": True, "blockers": []},
    ]

    state = build_strategy_intent_state(rows)

    assert state["summary"]["intent_count"] == 2
    assert state["summary"]["strategy_disagreement_count"] == 1
    assert state["summary"]["minimum_net_profit_gbp"] == DEFAULT_MINIMUM_NET_PROFIT_GBP


def test_publish_strategy_intent_writes_state_public_and_log(tmp_path: Path):
    worker = StrategyWorkerConfig("w", "Worker", "capital", "cfd", "market_data", "worker", "test")
    intent = normalize_strategy_intent(worker, {"symbol": "GOLD", "side": "BUY", "expected_net_revenue": 0.04, "confidence": 0.7})

    publish_strategy_intent(intent, root=tmp_path)

    assert (tmp_path / "state" / "unified_strategy_intents.jsonl").exists()
    public_state = json.loads((tmp_path / "frontend" / "public" / "aureon_unified_strategy_intents.json").read_text(encoding="utf-8"))
    assert public_state["summary"]["intent_count"] == 1
    assert public_state["intents"][0]["worker_id"] == "w"


def test_parallel_strategy_supervisor_runs_registered_workers_from_runtime_fixture(tmp_path: Path):
    state_dir = tmp_path / "state"
    state_dir.mkdir(parents=True)
    runtime = {
        "exchange_action_plan": {
            "venues": {
                "capital_cfd": {
                    "top_candidates": [
                        {
                            "symbol": "GOLD",
                            "side": "BUY",
                            "confidence": 0.72,
                            "profit_velocity_score": 0.61,
                            "execution_routes": [
                                {"venue": "capital", "market_type": "cfd", "symbol": "GOLD", "ready": True}
                            ],
                        }
                    ]
                }
            }
        }
    }
    (state_dir / "unified_runtime_status.json").write_text(json.dumps(runtime), encoding="utf-8")

    snapshot = ParallelStrategySupervisor(root=tmp_path).run_once()

    assert snapshot["summary"]["worker_count"] == 7
    assert snapshot["summary"]["healthy_worker_count"] == 7
    assert snapshot["summary"]["latest_intent_count"] >= 1
    assert snapshot["summary"]["direct_broker_mutation_allowed"] is False
    assert snapshot["summary"]["ghost_dance_enabled"] is True
    assert snapshot["summary"]["harmonic_api_piano_enabled"] is True
    assert snapshot["summary"]["rainbow_harmonic_ladder_enabled"] is True
    assert snapshot["summary"]["power_station_request_governor_enabled"] is True
    assert snapshot["summary"]["ghost_phase_collision_count"] == 0
    assert snapshot["ghost_dance"]["protocol"] == GHOST_DANCE_PROTOCOL_VERSION
    assert snapshot["harmonic_api_piano"]["protocol"] == HARMONIC_API_PIANO_VERSION
    assert snapshot["rainbow_harmonic_ladder"]["protocol"] == RAINBOW_HARMONIC_LADDER_VERSION
    assert all("ghost_dance" in row for row in snapshot["worker_rows"])
    assert all("harmonic_api_piano" in row for row in snapshot["worker_rows"])
    assert all("rainbow_harmonic_ladder" in row for row in snapshot["worker_rows"])
    assert all("power_station_request" in row for row in snapshot["worker_rows"])
    assert (tmp_path / "frontend" / "public" / "aureon_parallel_strategy_unity.json").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_unified_exchange_request_broker.json").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_power_station_request_governor.json").exists()
