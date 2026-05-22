from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aureon.autonomous.aureon_parallel_strategy_unity_stress_audit import (
    _audit_artifact_provenance_validation,
    _audit_consistency_matrix_validation,
    _audit_evidence_lineage_validation,
    _audit_freshness_sla_validation,
    _audit_integrity_triangulation_validation,
    _audit_operator_surface_validation,
    _audit_public_contract_validation,
    _audit_repair_acceptance_validation,
    _audit_repair_coverage_validation,
    _audit_report_replay_validation,
    _audit_runtime_repair_readiness_validation,
    _audit_served_artifact_validation,
    _audit_test_coverage_validation,
    _audit_validator_closure_validation,
    _audit_validation_chain_validation,
    _audit_validation_quorum_validation,
    _launcher_readiness_proof,
    _runtime_process_proof,
    build_and_write_parallel_strategy_unity_stress_audit,
    build_parallel_strategy_unity_stress_audit,
)
from aureon.trading.parallel_strategy_unity import DEFAULT_MINIMUM_NET_PROFIT_GBP, PRODUCTION_WORKERS
from aureon.trading.parallel_strategy_unity import (
    GHOST_DANCE_PROTOCOL_VERSION,
    HARMONIC_API_PIANO_VERSION,
    POWER_STATION_REQUEST_PROTOCOL_VERSION,
    RAINBOW_HARMONIC_LADDER_VERSION,
)


NOW = datetime(2026, 5, 22, 8, 0, 0, tzinfo=timezone.utc)


def _write_json(root: Path, rel: str, payload: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _clean_fixture(root: Path, *, now: datetime = NOW, embed_runtime_parallel: bool = True) -> None:
    workers = []
    intents = []
    leases = []
    venues = {}
    for index, worker in enumerate(PRODUCTION_WORKERS):
        route_key = f"{worker.venue}:{worker.market_type}:GOLD:BUY"
        ghost = {
            "ghost_dance_protocol": GHOST_DANCE_PROTOCOL_VERSION,
            "ghost_beat_id": "gbeat-test",
            "ghost_beat_index": 1,
            "ghost_phase_index": index,
            "ghost_phase_count": len(PRODUCTION_WORKERS),
            "ghost_phase_offset_sec": round(index * 4.0, 3),
            "ghost_phase_width_sec": 4.0,
            "ghost_sequence_number": f"gbeat-test-{index}",
            "api_key_lock_family": f"{worker.venue}:{worker.operation_type}",
            "scheduled_after_ms": index * 100,
            "phase_jitter_ms": index,
            "phase_status": "in_phase_window",
            "harmonic_api_piano_protocol": HARMONIC_API_PIANO_VERSION,
            "piano_key_id": f"{worker.venue}:{worker.operation_type}:{worker.worker_id}",
            "piano_key_rank": index + 1,
            "piano_velocity_score": round(0.8 - index * 0.01, 6),
            "harmonic_tempo_multiplier": 0.85,
            "hnc_master_score": 0.61,
            "auris_coherence": 0.44,
            "api_play_window_ms": 2000,
            "original_scheduled_after_ms": index * 100,
            "turn_acceleration_ratio": 0.4,
            "song_stop_guard": "cooldown_preserved",
            "harmonic_turn_state": "play_now" if index == 0 else "scheduled",
            "next_turn_reason": "fixture harmonic turn",
            "rainbow_harmonic_ladder_protocol": RAINBOW_HARMONIC_LADDER_VERSION,
            "rainbow_step_index": index % 7,
            "rainbow_step_name": f"step-{index % 7}",
            "rainbow_interval_name": "fixture_interval",
            "rainbow_interval_ratio": 1.0 + index * 0.05,
            "rainbow_frequency_hz": 528.0 + index,
            "harmony_lane_id": f"{worker.venue}:{worker.operation_type}:step-{index % 7}",
            "request_tempo_band": "steady",
            "request_phase_role": "fixture_request_pacing",
            "song_continuity_guard": "phase_window_preserved",
            "power_station_request_protocol": POWER_STATION_REQUEST_PROTOCOL_VERSION,
            "power_station_governor_status": "power_station_request_governor_ready",
            "request_direction": "internal_context" if worker.venue == "internal" else "outbound_market_api",
            "request_class": worker.operation_type,
            "request_owner_authority": "strategy_request_lease_only",
            "request_governor_decision": "lease_granted",
            "power_station_priority": "normal",
            "power_station_budget_tier": "local_context" if worker.venue == "internal" else "shared_market_budget",
            "power_station_min_notional": 0.03 if worker.venue == "capital" else 1.0,
            "power_station_reserve_pct": 0.1,
            "power_station_max_siphon_rate": 0.5,
            "power_station_metadata_source": "aureon/trading/v11_power_station_live.py",
            "request_metadata_source": "v11_power_station_metadata_plus_parallel_request_broker",
            "credential_boundary": "metadata_only_no_secret_values_read_or_revealed",
            "mutation_scope": "none",
            "power_station_harmony_lane_id": f"{worker.venue}:{worker.operation_type}:step-{index % 7}",
        }
        workers.append(
            {
                "worker_id": worker.worker_id,
                "label": worker.label,
                "venue": worker.venue,
                "pid": 1000 + index,
                "heartbeat_at": now.isoformat(),
                "strategy_status": "worker_healthy",
                "latest_signal_count": 1,
                "latest_intent_count": 1,
                "api_budget_usage": {"lease_status": "granted", "rate_remaining": 10},
                "trace_id": f"trace-{index}",
                "lifecycle_id": f"life-{index}",
                "route_key": route_key,
                "direct_broker_mutation_allowed": False,
                "requires_unified_executor": True,
                "ghost_dance": ghost,
                **ghost,
            }
        )
        intents.append(
            {
                "worker_id": worker.worker_id,
                "trace_id": f"trace-{index}",
                "lifecycle_id": f"life-{index}",
                "candidate_id": f"cand-{index}",
                "intent_id": f"intent-{index}",
                "route_key": route_key,
                "venue": worker.venue,
                "market_type": worker.market_type,
                "symbol": "GOLD",
                "side": "BUY",
                "generated_at": now.isoformat(),
                "confidence": 0.75,
                "expected_net_revenue": 0.05,
                "three_p_floor_passed": True,
                "requires_unified_executor": True,
                "direct_broker_mutation_allowed": False,
                "blockers": [],
                **ghost,
            }
        )
        leases.append(
            {
                "lease_id": f"lease-{index}",
                "request_id": f"req-{index}",
                "requested_at": now.isoformat(),
                "worker_id": worker.worker_id,
                "venue": worker.venue,
                "operation_type": worker.operation_type,
                "rate_limit_family": f"{worker.venue}_api_budget",
                "budget_required": 1,
                "idempotency_key": f"idem-{index}",
                "status": "granted",
                "reason": "lease_granted",
                "broker_mutation_authority": False,
                "rate_limit_per_min": 60,
                "rate_used": 1,
                "rate_remaining": 59,
                **ghost,
            }
        )
        venues.setdefault(worker.venue, {"venue": worker.venue, "rate_limit_per_min": 60, "rate_used": 0, "rate_remaining": 60, "lease_count": 0})
        venues[worker.venue]["rate_used"] += 1
        venues[worker.venue]["rate_remaining"] -= 1
        venues[worker.venue]["lease_count"] += 1

    unity = {
        "status": "parallel_strategy_unity_active",
        "generated_at": now.isoformat(),
        "summary": {
            "worker_count": len(workers),
            "healthy_worker_count": len(workers),
            "latest_signal_count": len(workers),
            "latest_intent_count": len(workers),
            "request_lease_count": len(leases),
            "request_denied_count": 0,
            "intent_queue_count": len(intents),
            "executable_intent_count": len(intents),
            "minimum_net_profit_gbp": DEFAULT_MINIMUM_NET_PROFIT_GBP,
            "unified_executor_authoritative": True,
            "direct_broker_mutation_allowed": False,
            "thoughtbus_mycelium_publish_enabled": True,
            "ghost_dance_enabled": True,
            "ghost_dance_protocol": GHOST_DANCE_PROTOCOL_VERSION,
            "ghost_phase_count": len(workers),
            "ghost_phase_collision_count": 0,
            "api_key_lock_family_count": len({f"{worker.venue}:{worker.operation_type}" for worker in PRODUCTION_WORKERS}),
            "harmonic_api_piano_enabled": True,
            "harmonic_api_piano_protocol": HARMONIC_API_PIANO_VERSION,
            "harmonic_tempo_multiplier": 0.85,
            "harmonic_coherence_blend": 0.61,
            "piano_key_count": len(workers),
            "piano_play_now_count": 1,
            "song_stop_guard": "cooldown_preserved",
            "rainbow_harmonic_ladder_enabled": True,
            "rainbow_harmonic_ladder_protocol": RAINBOW_HARMONIC_LADDER_VERSION,
            "rainbow_ladder_step_count": 7,
            "rainbow_worker_ladder_count": len(workers),
            "rainbow_base_frequency_hz": 528.0,
            "rainbow_song_continuity_guard": "phase_window_preserved",
            "power_station_request_governor_enabled": True,
            "power_station_request_protocol": POWER_STATION_REQUEST_PROTOCOL_VERSION,
            "power_station_request_count": len(leases),
            "power_station_outbound_request_count": len([row for row in leases if row["venue"] != "internal"]),
            "power_station_internal_request_count": len([row for row in leases if row["venue"] == "internal"]),
            "power_station_authority_violation_count": 0,
        },
        "ghost_dance": {
            "protocol": GHOST_DANCE_PROTOCOL_VERSION,
            "status": "ghost_dance_ready",
            "phase_count": len(workers),
            "api_key_lock_family_count": len({f"{worker.venue}:{worker.operation_type}" for worker in PRODUCTION_WORKERS}),
            "collision_count": 0,
            "worker_phase_rows": [row["ghost_dance"] for row in workers],
        },
        "harmonic_api_piano": {
            "protocol": HARMONIC_API_PIANO_VERSION,
            "status": "harmonic_api_piano_ready",
            "tempo_multiplier": 0.85,
            "coherence_blend": 0.61,
            "piano_key_count": len(workers),
            "play_now_count": 1,
            "song_stop_guard": "cooldown_preserved",
            "piano_key_rows": [row["ghost_dance"] for row in workers],
            "worker_phase_rows": [row["ghost_dance"] for row in workers],
        },
        "rainbow_harmonic_ladder": {
            "protocol": RAINBOW_HARMONIC_LADDER_VERSION,
            "status": "rainbow_harmonic_ladder_ready",
            "base_frequency_hz": 528.0,
            "ladder_step_count": 7,
            "worker_ladder_count": len(workers),
            "ladder_rows": [
                {"rainbow_step_index": idx, "rainbow_step_name": f"step-{idx}", "rainbow_frequency_hz": 528.0 + idx}
                for idx in range(7)
            ],
            "worker_phase_rows": [row["ghost_dance"] for row in workers],
        },
        "power_station_request_governor": {
            "protocol": POWER_STATION_REQUEST_PROTOCOL_VERSION,
            "status": "power_station_request_governor_ready",
            "source_path": "aureon/trading/v11_power_station_live.py",
            "credential_boundary": "metadata_only_no_secret_values_read_or_revealed",
        },
        "piano_key_rows": [row["ghost_dance"] for row in workers],
        "rainbow_ladder_rows": [
            {"rainbow_step_index": idx, "rainbow_step_name": f"step-{idx}", "rainbow_frequency_hz": 528.0 + idx}
            for idx in range(7)
        ],
        "rainbow_worker_rows": [row["ghost_dance"] for row in workers],
        "worker_rows": workers,
        "api_lease_rows": leases,
        "power_station_request_rows": leases,
        "venue_budget_rows": list(venues.values()),
        "strategy_intent_rows": intents,
    }
    broker = {
        "status": "request_broker_ready",
        "generated_at": now.isoformat(),
        "summary": {
            "lease_count": len(leases),
            "granted_count": len(leases),
            "denied_count": 0,
            "power_station_request_governor_enabled": True,
            "power_station_request_count": len(leases),
            "power_station_authority_violation_count": 0,
        },
        "lease_rows": leases,
        "ghost_dance_lease_rows": leases,
        "rainbow_harmonic_lease_rows": leases,
        "power_station_request_rows": leases,
        "venue_budget_rows": list(venues.values()),
    }
    intent_state = {
        "status": "strategy_intents_ready",
        "generated_at": now.isoformat(),
        "summary": {
            "intent_count": len(intents),
            "executable_intent_count": len(intents),
            "minimum_net_profit_gbp": DEFAULT_MINIMUM_NET_PROFIT_GBP,
            "direct_broker_mutation_allowed": False,
        },
        "intents": intents,
    }
    fabric = {
        "status": "trade_flow_active",
        "generated_at": now.isoformat(),
        "summary": {"event_count": 7, "thoughtbus_receiving": True, "mycelium_receiving": True},
        "phase_counts": {"signal_generated": 7},
    }
    action_plan = {
        "trade_path_state": "runtime_gated_order_intent",
        "order_intent_publish_enabled": True,
    }
    if embed_runtime_parallel:
        action_plan.update(
            {
                "parallel_strategy_unity": {"status": "parallel_strategy_unity_active"},
                "parallel_strategy_intents": {"status": "strategy_intents_ready"},
            }
        )
    runtime = {
        "generated_at": now.isoformat(),
        "exchange_action_plan": action_plan,
    }

    _write_json(root, "frontend/public/aureon_parallel_strategy_unity.json", unity)
    _write_json(root, "frontend/public/aureon_unified_exchange_request_broker.json", broker)
    _write_json(root, "frontend/public/aureon_unified_strategy_intents.json", intent_state)
    _write_json(root, "frontend/public/aureon_live_trade_signal_fabric.json", fabric)
    _write_json(root, "state/unified_runtime_status.json", runtime)
    _write_json(root, "state/aureon_parallel_strategy_unity.json", unity)
    _write_json(root, "state/unified_strategy_intents.json", intent_state)


def test_parallel_strategy_unity_stress_audit_certifies_clean_fixture(tmp_path: Path):
    _clean_fixture(tmp_path)

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_stress_certified"
    assert report["summary"]["healthy_worker_count"] == len(PRODUCTION_WORKERS)
    assert report["summary"]["mutation_leak_count"] == 0
    assert report["summary"]["api_budget_gap_count"] == 0
    assert report["summary"]["fabric_visible"] is True
    assert report["summary"]["audit_self_validation_passed"] is True
    assert report["summary"]["audit_self_validation_failed_count"] == 0
    assert report["audit_self_validation_rows"]
    assert report["summary"]["audit_replay_validation_passed"] is True
    assert report["summary"]["audit_replay_validation_failed_count"] == 0
    assert report["audit_replay_validation_rows"]
    assert report["summary"]["audit_integrity_validation_passed"] is True
    assert report["summary"]["audit_integrity_validation_failed_count"] == 0
    assert report["audit_integrity_validation_rows"]
    assert report["summary"]["audit_validation_quorum_passed"] is True
    assert report["summary"]["audit_validation_quorum_failed_count"] == 0
    assert report["summary"]["audit_validation_quorum_pass_count"] == 3
    assert report["audit_validation_quorum_rows"]
    assert report["blockers"] == []


def test_parallel_strategy_unity_stress_audit_replay_validation_flags_corrupt_summary(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["summary"]["power_station_request_count"] = 999

    replay = _audit_report_replay_validation(report)

    assert replay["replay_validation_passed"] is False
    assert any(row["check"] == "power_station_request_count_replayed" for row in replay["failed_rows"])
    assert any(row["check"] == "worker_count_replayed" for row in replay["rows"])


def test_parallel_strategy_unity_stress_audit_integrity_validation_flags_corrupt_blocker_count(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["summary"]["blocker_count"] = 999

    integrity = _audit_integrity_triangulation_validation(report)

    assert integrity["integrity_validation_passed"] is False
    assert any(row["check"] == "blocker_count_matches_blocker_rows" for row in integrity["failed_rows"])
    assert any(row["check"] == "repair_actions_cover_all_blockers" for row in integrity["rows"])


def test_parallel_strategy_unity_stress_audit_validation_quorum_flags_failed_mirror(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["summary"]["audit_replay_validation_passed"] = False
    report["summary"]["audit_replay_validation_failed_count"] = 1

    quorum = _audit_validation_quorum_validation(report)

    assert quorum["validation_quorum_passed"] is False
    assert quorum["validator_pass_count"] == 2
    assert any(row["check"] == "all_validation_mirrors_passed" for row in quorum["failed_rows"])


def test_parallel_strategy_unity_stress_audit_artifact_provenance_flags_tampered_public_json(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    public_path = tmp_path / "frontend/public/aureon_parallel_strategy_unity_stress_audit.json"
    public_payload = json.loads(public_path.read_text(encoding="utf-8"))
    public_payload["status"] = "tampered_status"
    public_path.write_text(json.dumps(public_payload), encoding="utf-8")

    provenance = _audit_artifact_provenance_validation(
        root=tmp_path,
        report=report,
        json_paths=[
            Path("state/aureon_parallel_strategy_unity_stress_audit_last_run.json"),
            Path("docs/audits/aureon_parallel_strategy_unity_stress_audit.json"),
            Path("frontend/public/aureon_parallel_strategy_unity_stress_audit.json"),
        ],
        markdown_path=Path("docs/audits/aureon_parallel_strategy_unity_stress_audit.md"),
    )

    assert provenance["artifact_provenance_passed"] is False
    assert any("public" in row.get("path", "") for row in provenance["failed_rows"])


def test_parallel_strategy_unity_stress_audit_served_artifact_validation_flags_tampered_payload(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    served_payload = json.loads(json.dumps(report))
    served_payload["status"] = "tampered_status"

    served = _audit_served_artifact_validation(
        report=report,
        served_payload=served_payload,
        served_url="http://127.0.0.1:8081/aureon_parallel_strategy_unity_stress_audit.json",
        required=True,
    )

    assert served["served_artifact_passed"] is False
    assert any(row["check"] == "served_artifact_core_hash_matches" for row in served["failed_rows"])


def test_parallel_strategy_unity_stress_audit_validation_chain_flags_missing_validator_rows(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["audit_replay_validation_rows"] = []

    chain = _audit_validation_chain_validation(report)

    assert chain["validation_chain_passed"] is False
    assert any(row["check"] == "all_validators_row_backed" for row in chain["failed_rows"])


def test_parallel_strategy_unity_stress_audit_public_contract_flags_missing_summary_field(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["summary"].pop("worker_count")

    contract = _audit_public_contract_validation(report)

    assert contract["public_contract_passed"] is False
    assert any(row["check"] == "required_summary_contract_fields_present" for row in contract["failed_rows"])


def test_parallel_strategy_unity_stress_audit_freshness_sla_flags_stale_report(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["generated_at"] = (NOW - timedelta(hours=2)).isoformat()

    freshness = _audit_freshness_sla_validation(report, now=NOW, max_age_sec=60)

    assert freshness["freshness_sla_passed"] is False
    assert any(row["check"] == "audit_generated_at_within_sla" for row in freshness["failed_rows"])


def test_parallel_strategy_unity_stress_audit_operator_surface_flags_missing_panel(tmp_path: Path):
    _clean_fixture(tmp_path)
    app_path = tmp_path / "frontend/src/App.tsx"
    app_path.parent.mkdir(parents=True, exist_ok=True)
    app_path.write_text(
        "function ParallelTradingSystemsPanel(){return <div>Parallel Trading Systems</div>}\n"
        "function LiveSignalFabricPanel(){return null}\n",
        encoding="utf-8",
    )
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    surface = _audit_operator_surface_validation(tmp_path, report)

    assert surface["operator_surface_passed"] is False
    assert any(row["check"] == "required_parallel_operator_panels_present" for row in surface["failed_rows"])


def test_parallel_strategy_unity_stress_audit_test_coverage_flags_missing_validator_test(tmp_path: Path):
    _clean_fixture(tmp_path)
    test_path = tmp_path / "tests/test_parallel_strategy_unity_stress_audit.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(
        "from aureon.autonomous.aureon_parallel_strategy_unity_stress_audit import _audit_test_coverage_validation\n"
        "def test_placeholder():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    coverage = _audit_test_coverage_validation(tmp_path, report)

    assert coverage["test_coverage_passed"] is False
    assert any(row["check"] == "validator_negative_path_tests_present" for row in coverage["failed_rows"])


def test_parallel_strategy_unity_stress_audit_repair_coverage_flags_generic_repair_action(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["blockers"] = ["parallel_strategy_unknown_blocker"]
    report["summary"]["blocker_count"] = 1
    report["next_repair_actions"] = [
        {"blocker": "parallel_strategy_unknown_blocker", "owner": "parallel_strategy_unity", "action": "Inspect artifact rows."}
    ]

    repair = _audit_repair_coverage_validation(report)

    assert repair["repair_coverage_passed"] is False
    assert any(row["check"] == "repair_actions_are_specific" for row in repair["failed_rows"])


def test_parallel_strategy_unity_stress_audit_runtime_repair_readiness_flags_unsafe_command(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["guarded_repair_command_lines"] = ["Remove-Item -Recurse C:\\\\Users\\\\user\\\\aureon-trading"]

    readiness = _audit_runtime_repair_readiness_validation(report)

    assert readiness["runtime_repair_readiness_passed"] is False
    assert any(row["check"] == "guarded_command_is_scoped_and_non_destructive" for row in readiness["failed_rows"])


def test_parallel_strategy_unity_stress_audit_repair_acceptance_flags_missing_post_restart_check(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["blockers"] = ["parallel_strategy_worker_stale_or_missing"]
    report["summary"]["blocker_count"] = 1
    report["next_repair_actions"] = [
        {
            "blocker": "parallel_strategy_worker_stale_or_missing",
            "owner": "parallel_strategy_unity",
            "action": "Start the parallel_strategy_unity watch process through AUREON_PRODUCTION_LIVE.cmd so worker heartbeats stay fresh.",
        }
    ]
    report["post_restart_check_rows"] = [
        row for row in report.get("post_restart_check_rows", []) if row.get("check") != "worker_heartbeats_fresh"
    ]

    acceptance = _audit_repair_acceptance_validation(report)

    assert acceptance["repair_acceptance_passed"] is False
    assert any(row["check"] == "acceptance_checks_present_for_active_blockers" for row in acceptance["failed_rows"])


def test_parallel_strategy_unity_stress_audit_evidence_lineage_flags_missing_source_path(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["source_paths"].pop("runtime_status", None)

    lineage = _audit_evidence_lineage_validation(report)

    assert lineage["evidence_lineage_passed"] is False
    assert any(row["check"] == "required_source_paths_present" for row in lineage["failed_rows"])


def test_parallel_strategy_unity_stress_audit_validator_closure_flags_missing_validator_summary(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["summary"].pop("audit_evidence_lineage_passed", None)

    closure = _audit_validator_closure_validation(tmp_path, report)

    assert closure["validator_closure_passed"] is False
    assert any(row["check"] == "validator_summary_fields_present" for row in closure["failed_rows"])


def test_parallel_strategy_unity_stress_audit_consistency_matrix_flags_corrupt_validator_count(tmp_path: Path):
    _clean_fixture(tmp_path)
    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)
    report["summary"]["audit_repair_acceptance_failed_count"] = 99

    matrix = _audit_consistency_matrix_validation(report)

    assert matrix["consistency_matrix_passed"] is False
    assert any(row["check"] == "validator_failed_counts_match_rows" for row in matrix["failed_rows"])


def test_parallel_strategy_unity_stress_audit_self_validation_flags_missing_core_artifact(tmp_path: Path):
    _clean_fixture(tmp_path)
    (tmp_path / "frontend/public/aureon_unified_exchange_request_broker.json").unlink()

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert "parallel_strategy_artifact_missing" in report["blockers"]
    assert "parallel_strategy_audit_self_validation_gap" in report["blockers"]
    assert report["summary"]["audit_self_validation_passed"] is False
    assert any(row["check"] == "required_artifacts_present" for row in report["audit_self_validation_failed_rows"])


def test_parallel_strategy_unity_stress_audit_flags_mutation_leak(tmp_path: Path):
    _clean_fixture(tmp_path)
    broker_path = tmp_path / "frontend/public/aureon_unified_exchange_request_broker.json"
    broker = json.loads(broker_path.read_text(encoding="utf-8"))
    broker["lease_rows"].append(
        {
            "lease_id": "leak-1",
            "request_id": "leak-req",
            "worker_id": "capital_cfd_strategy",
            "venue": "capital",
            "operation_type": "order_submit",
            "rate_limit_family": "capital_api_budget",
            "budget_required": 1,
            "idempotency_key": "leak",
            "status": "granted",
        }
    )
    broker_path.write_text(json.dumps(broker), encoding="utf-8")

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_mutation_leak"
    assert "parallel_strategy_mutation_leak" in report["blockers"]
    assert report["summary"]["mutation_leak_count"] == 1


def test_parallel_strategy_unity_stress_audit_flags_missing_intent_contract(tmp_path: Path):
    _clean_fixture(tmp_path)
    intent_path = tmp_path / "frontend/public/aureon_unified_strategy_intents.json"
    intents = json.loads(intent_path.read_text(encoding="utf-8"))
    intents["intents"][0].pop("trace_id")
    intent_path.write_text(json.dumps(intents), encoding="utf-8")

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_intent_contract_attention"
    assert "parallel_strategy_intent_contract_missing" in report["blockers"]
    assert report["summary"]["missing_intent_contract_count"] == 1


def test_parallel_strategy_unity_stress_audit_flags_current_ghost_intent_gap(tmp_path: Path):
    _clean_fixture(tmp_path)
    intent_path = tmp_path / "frontend/public/aureon_unified_strategy_intents.json"
    intents = json.loads(intent_path.read_text(encoding="utf-8"))
    for field in ("ghost_dance_protocol", "ghost_phase_index", "api_key_lock_family"):
        intents["intents"][0].pop(field)
    intent_path.write_text(json.dumps(intents), encoding="utf-8")

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_ghost_dance_attention"
    assert "parallel_strategy_ghost_dance_missing" in report["blockers"]
    assert report["summary"]["ghost_missing_phase_count"] == 1
    assert report["ghost_missing_intent_phase_rows"]


def test_parallel_strategy_unity_stress_audit_classifies_stale_ghost_intent_gap_as_historical(tmp_path: Path):
    _clean_fixture(tmp_path)
    intent_path = tmp_path / "frontend/public/aureon_unified_strategy_intents.json"
    intents = json.loads(intent_path.read_text(encoding="utf-8"))
    intents["intents"][0]["generated_at"] = (NOW - timedelta(hours=1)).isoformat()
    for field in ("ghost_dance_protocol", "ghost_phase_index", "api_key_lock_family"):
        intents["intents"][0].pop(field)
    intent_path.write_text(json.dumps(intents), encoding="utf-8")

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_stress_certified"
    assert "parallel_strategy_ghost_dance_missing" not in report["blockers"]
    assert report["summary"]["ghost_missing_phase_count"] == 0
    assert report["summary"]["ghost_stale_historical_intent_phase_count"] == 1
    assert report["ghost_stale_historical_intent_phase_rows"][0]["stale_historical_context"] is True


def test_parallel_strategy_unity_stress_audit_flags_current_piano_intent_gap(tmp_path: Path):
    _clean_fixture(tmp_path)
    intent_path = tmp_path / "frontend/public/aureon_unified_strategy_intents.json"
    intents = json.loads(intent_path.read_text(encoding="utf-8"))
    for field in ("harmonic_api_piano_protocol", "piano_key_rank", "piano_velocity_score", "harmonic_tempo_multiplier", "song_stop_guard"):
        intents["intents"][0].pop(field)
    intent_path.write_text(json.dumps(intents), encoding="utf-8")

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_harmonic_api_piano_attention"
    assert "parallel_strategy_harmonic_api_piano_missing" in report["blockers"]
    assert report["summary"]["piano_missing_proof_count"] == 1
    assert report["piano_missing_intent_rows"]


def test_parallel_strategy_unity_stress_audit_classifies_stale_piano_intent_gap_as_historical(tmp_path: Path):
    _clean_fixture(tmp_path)
    intent_path = tmp_path / "frontend/public/aureon_unified_strategy_intents.json"
    intents = json.loads(intent_path.read_text(encoding="utf-8"))
    intents["intents"][0]["generated_at"] = (NOW - timedelta(hours=1)).isoformat()
    for field in ("harmonic_api_piano_protocol", "piano_key_rank", "piano_velocity_score", "harmonic_tempo_multiplier", "song_stop_guard"):
        intents["intents"][0].pop(field)
    intent_path.write_text(json.dumps(intents), encoding="utf-8")

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_stress_certified"
    assert "parallel_strategy_harmonic_api_piano_missing" not in report["blockers"]
    assert report["summary"]["piano_missing_proof_count"] == 0
    assert report["summary"]["piano_stale_historical_intent_count"] == 1
    assert report["piano_stale_historical_intent_rows"][0]["stale_historical_context"] is True


def test_parallel_strategy_unity_stress_audit_flags_song_stop_risk(tmp_path: Path):
    _clean_fixture(tmp_path)
    unity_path = tmp_path / "frontend/public/aureon_parallel_strategy_unity.json"
    unity = json.loads(unity_path.read_text(encoding="utf-8"))
    unity["piano_key_rows"][0]["song_stop_guard"] = "api_overplay_risk"
    unity["harmonic_api_piano"]["piano_key_rows"][0]["song_stop_guard"] = "api_overplay_risk"
    unity_path.write_text(json.dumps(unity), encoding="utf-8")

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_harmonic_api_piano_attention"
    assert "parallel_strategy_harmonic_api_piano_song_stop_risk" in report["blockers"]
    assert report["summary"]["song_stop_risk_count"] == 1


def test_parallel_strategy_unity_stress_audit_flags_stale_worker(tmp_path: Path):
    _clean_fixture(tmp_path, now=NOW - timedelta(minutes=10))

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_workers_attention"
    assert "parallel_strategy_worker_stale_or_missing" in report["blockers"]
    assert report["summary"]["stale_worker_count"] == len(PRODUCTION_WORKERS)


def test_parallel_strategy_unity_stress_audit_classifies_runtime_reload_required(tmp_path: Path):
    _clean_fixture(tmp_path, embed_runtime_parallel=False)

    report = build_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_runtime_reload_required"
    assert "parallel_strategy_runtime_reload_required" in report["blockers"]
    assert report["summary"]["runtime_reload_required"] is True
    assert report["summary"]["runtime_code_wired"] is True
    assert report["summary"]["state_snapshots_present"] is True
    assert report["runtime_alignment_proof"]["alignment_status"] == "runtime_reload_required"
    assert report["runtime_alignment_burndown_rows"]


def test_parallel_strategy_unity_stress_audit_classifies_duplicate_runtime_processes(tmp_path: Path):
    (tmp_path / "aureon").mkdir()
    (tmp_path / ".venv/Scripts").mkdir(parents=True)
    (tmp_path / ".venv/Scripts/python.exe").write_text("", encoding="utf-8")
    rows = [
        {
            "pid": 11,
            "exe": str(tmp_path / ".venv/Scripts/python.exe"),
            "command_line": f'"{tmp_path / ".venv/Scripts/python.exe"}" -m aureon.exchanges.unified_market_trader --interval 1',
            "target": "unified_market_trader",
            "created_at": NOW.isoformat(),
        },
        {
            "pid": 12,
            "exe": "C:/Python312/python.exe",
            "command_line": "C:/Python312/python.exe -m aureon.exchanges.unified_market_trader --interval 1",
            "target": "unified_market_trader",
            "created_at": NOW.isoformat(),
        },
    ]

    proof = _runtime_process_proof(tmp_path, NOW.timestamp(), rows)

    assert proof["duplicate_unified_market_trader"] is True
    assert proof["wrong_python_process_count"] == 1
    assert proof["supervisor_missing"] is True
    assert proof["unified_market_trader_process_count"] == 2
    assert any(row["check"] == "unified_market_trader_single_process" and row["passing"] is False for row in proof["burn_down_rows"])


def test_parallel_strategy_unity_stress_audit_builds_single_owner_repair_plan(tmp_path: Path):
    (tmp_path / "aureon").mkdir()
    (tmp_path / ".venv/Scripts").mkdir(parents=True)
    (tmp_path / ".venv/Scripts/python.exe").write_text("", encoding="utf-8")
    (tmp_path / "AUREON_PRODUCTION_LIVE.cmd").write_text("@echo off", encoding="utf-8")
    (tmp_path / "AUREON_WAKE_UP_FULL_AUTONOMOUS.ps1").write_text(
        "\n".join(
            [
                "aureon.exchanges.unified_market_trader",
                "aureon.trading.parallel_strategy_unity --watch",
                "aureon.autonomous.aureon_parallel_strategy_unity_stress_audit --watch",
            ]
        ),
        encoding="utf-8",
    )
    rows = [
        {
            "pid": 11,
            "exe": str(tmp_path / ".venv/Scripts/python.exe"),
            "command_line": f'"{tmp_path / ".venv/Scripts/python.exe"}" -m aureon.exchanges.unified_market_trader --interval 1',
            "target": "unified_market_trader",
            "created_at": NOW.isoformat(),
        },
        {
            "pid": 12,
            "exe": "C:/Python312/python.exe",
            "command_line": "C:/Python312/python.exe -m aureon.exchanges.unified_market_trader --interval 1",
            "target": "unified_market_trader",
            "created_at": NOW.isoformat(),
        },
    ]
    process_proof = _runtime_process_proof(tmp_path, NOW.timestamp(), rows)

    repair = _launcher_readiness_proof(tmp_path, process_proof)

    assert repair["standard_launcher_available"] is True
    assert repair["guarded_command_package_ready"] is True
    assert repair["stop_target_count"] == 2
    assert repair["start_target_count"] == 3
    assert repair["post_restart_check_count"] == 6
    assert repair["blockers"] == []
    assert all(row["advisory_only"] for row in repair["stop_target_rows"])
    assert any(row["check"] == "guarded_command_package_ready" and row["passing"] is True for row in repair["guard_validation_rows"])
    assert any("Get-CimInstance Win32_Process" in line for line in repair["guarded_repair_command_lines"])
    assert any("AUREON_PRODUCTION_LIVE.cmd" in line for line in repair["guarded_repair_command_lines"])


def test_parallel_strategy_unity_stress_audit_writes_all_artifacts(tmp_path: Path):
    _clean_fixture(tmp_path)

    report = build_and_write_parallel_strategy_unity_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "parallel_strategy_stress_certified"
    assert report["summary"]["audit_artifact_provenance_passed"] is True
    assert report["summary"]["audit_artifact_provenance_failed_count"] == 0
    assert report["summary"]["audit_artifact_provenance_json_match_count"] == 3
    assert report["summary"]["audit_served_artifact_passed"] is True
    assert report["summary"]["audit_served_artifact_checked"] is False
    assert report["summary"]["audit_served_artifact_failed_count"] == 0
    assert report["summary"]["audit_freshness_sla_passed"] is True
    assert report["summary"]["audit_freshness_sla_failed_count"] == 0
    assert report["summary"]["audit_operator_surface_passed"] is True
    assert report["summary"]["audit_operator_surface_failed_count"] == 0
    assert report["summary"]["audit_test_coverage_passed"] is True
    assert report["summary"]["audit_test_coverage_failed_count"] == 0
    assert report["summary"]["audit_repair_coverage_passed"] is True
    assert report["summary"]["audit_repair_coverage_failed_count"] == 0
    assert report["summary"]["audit_runtime_repair_readiness_passed"] is True
    assert report["summary"]["audit_runtime_repair_readiness_failed_count"] == 0
    assert report["summary"]["audit_repair_acceptance_passed"] is True
    assert report["summary"]["audit_repair_acceptance_failed_count"] == 0
    assert report["summary"]["audit_consistency_matrix_passed"] is True
    assert report["summary"]["audit_consistency_matrix_failed_count"] == 0
    assert report["summary"]["audit_evidence_lineage_passed"] is True
    assert report["summary"]["audit_evidence_lineage_failed_count"] == 0
    assert report["summary"]["audit_validator_closure_passed"] is True
    assert report["summary"]["audit_validator_closure_failed_count"] == 0
    assert report["summary"]["audit_public_contract_passed"] is True
    assert report["summary"]["audit_public_contract_failed_count"] == 0
    assert report["summary"]["audit_validation_chain_passed"] is True
    assert report["summary"]["audit_validation_chain_validator_pass_count"] == 16
    assert (tmp_path / "state/aureon_parallel_strategy_unity_stress_audit_last_run.json").exists()
    assert (tmp_path / "docs/audits/aureon_parallel_strategy_unity_stress_audit.json").exists()
    assert (tmp_path / "docs/audits/aureon_parallel_strategy_unity_stress_audit.md").exists()
    assert (tmp_path / "frontend/public/aureon_parallel_strategy_unity_stress_audit.json").exists()
