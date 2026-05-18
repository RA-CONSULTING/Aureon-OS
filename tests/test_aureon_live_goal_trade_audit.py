from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aureon.autonomous.aureon_live_goal_trade_audit import (
    build_and_write_live_goal_trade_audit,
    build_live_goal_trade_audit,
)


NOW = datetime(2026, 5, 18, 8, 0, 0, tzinfo=timezone.utc)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _epoch(age_seconds: int) -> float:
    return NOW.timestamp() - age_seconds


def _stream_cache(*, age_seconds: int, include_gold: bool = True) -> dict:
    ticker_cache = {
        "BTCUSDT": {
            "price": 78000.0,
            "exchange": "binance",
            "source": "binance_rest_ws_gap_fill",
            "timestamp": _epoch(age_seconds),
            "pair": "BTCUSDT",
        },
        "capital:SPYUSD": {
            "price": 73700.0,
            "exchange": "capital",
            "source": "capital_rest_snapshot",
            "timestamp": _epoch(age_seconds),
            "pair": "SPY",
        },
    }
    if include_gold:
        ticker_cache["capital:GOLDUSD"] = {
            "price": 4531.25,
            "bid": 4531.0,
            "ask": 4531.5,
            "exchange": "capital",
            "source": "capital_rest_snapshot",
            "timestamp": _epoch(age_seconds),
            "pair": "GOLD",
        }
        ticker_cache["XAUTUSDT"] = {
            "price": 4530.0,
            "exchange": "binance",
            "source": "binance_rest_ws_gap_fill",
            "timestamp": _epoch(age_seconds),
            "pair": "XAUTUSDT",
        }
    return {
        "generated_at": _epoch(age_seconds),
        "source": "multi_exchange_stream_cache",
        "source_count": 2,
        "active_source_count": 2,
        "ticker_cache": ticker_cache,
        "source_health": {
            "binance": {
                "source": "binance_rest_ws_gap_fill",
                "present": True,
                "active": True,
                "fresh": age_seconds <= 180,
                "ticker_count": 2,
                "generated_at": _epoch(age_seconds),
            },
            "capital": {
                "source": "capital_rest_snapshot",
                "present": True,
                "active": True,
                "fresh": age_seconds <= 180,
                "ticker_count": 1,
                "generated_at": _epoch(age_seconds),
            },
        },
    }


def _capital_registry(*, age_seconds: int, trade_ready: bool = True) -> dict:
    return {
        "assets": [
            {
                "symbol": "GOLD",
                "epic": "GOLD",
                "instrument_name": "Gold",
                "market_status": "TRADEABLE",
                "trade_ready": trade_ready,
                "can_buy": True,
                "can_sell": True,
                "bid": 4559.41,
                "ask": 4559.91,
                "mid_price": 4559.66,
                "spread": 0.5,
                "minimum_deal_size": 0.01,
                "margin_required_for_min_deal": 45.5966,
                "last_snapshot_at": datetime.fromtimestamp(_epoch(age_seconds), tz=timezone.utc).isoformat(),
            }
        ]
    }


def _runtime(
    *,
    stale: bool,
    blockers: list[str] | None = None,
    submitted: int = 0,
    attempted: int = 0,
    gold_candidate: bool = True,
    capital_route_visible: bool = True,
    capital_route_ready: bool = True,
) -> dict:
    return {
        "generated_at": NOW.isoformat(),
        "trading_ready": True,
        "data_ready": True,
        "stale": stale,
        "stale_reason": "tick_in_progress_stalled" if stale else "",
        "last_tick_completed_at": NOW.isoformat(),
        "gold_runtime_trade_proof": {
            "generated_at": NOW.isoformat(),
            "gold_runtime_candidate_ready": gold_candidate,
            "capital_cfd_route_visible": capital_route_visible,
            "capital_cfd_route_ready": capital_route_ready,
            "gold_intent_publish_reason": "gold_runtime_gated_intent_publishable"
            if gold_candidate and capital_route_visible and capital_route_ready
            else "gold_runtime_candidate_missing",
            "intent_publish_blockers": [],
        },
        "exchange_action_plan": {
            "executor_enabled": True,
            "real_orders_disabled": False,
            "exchange_mutations_disabled": False,
            "order_intents_published": 1,
            "venues": {
                "capital_cfd": {
                    "ready": capital_route_ready,
                    "candidate_count": 1 if capital_route_visible else 0,
                    "ready_candidate_count": 1 if capital_route_ready else 0,
                    "blockers": [] if capital_route_ready else ["capital_not_ready"],
                }
            } if capital_route_visible else {},
            "decision_self_trust": {"score": 0.82, "posture": "trust_ready_routes"},
            "latest_execution": {
                "generated_at": NOW.isoformat(),
                "executor_enabled": True,
                "trade_path_state": "runtime_clearance_hold" if blockers else "available",
                "live_action_clearance": "waiting_for_runtime_truth" if blockers else "clear",
                "runtime_clearances": blockers or [],
                "blockers": blockers or [],
                "attempted_count": attempted,
                "submitted_count": submitted,
                "delegated_count": 0,
                "held_count": 0,
                "blocked_count": len(blockers or []),
            },
        },
    }


def _intents(*, gold: bool = True, age_seconds: int = 10) -> dict:
    symbol = "GOLD" if gold else "ETHUSD"
    route_symbol = "GOLD" if gold else "ETHUSDT"
    venue = "capital" if gold else "kraken"
    return {
        "generated_at": datetime.fromtimestamp(_epoch(age_seconds), tz=timezone.utc).isoformat(),
        "intent_count": 1,
        "intents": [
            {
                "id": "intent-1",
                "generated_at": datetime.fromtimestamp(_epoch(age_seconds), tz=timezone.utc).isoformat(),
                "symbol": symbol,
                "side": "BUY",
                "confidence": 0.91,
                "authority_mode": "intent_only_runtime_gated",
                "runtime_gate": "executor_required",
                "profit_velocity_score": 0.7,
                "fast_money_score": 0.61,
                "history_validation_score": 0.55,
                "model_alignment": True,
                "cash_capable_route_count": 1,
                "sources": ["fresh_gold_interval_validation"] if gold else ["world_financial_ecosystem"],
                "routes": [
                    {
                        "venue": venue,
                        "market_type": "margin" if gold else "spot",
                        "symbol": route_symbol,
                        "ready": True,
                        "trade_clearance_state": "available",
                        "guard_state": "available",
                        "blockers": [],
                    }
                ],
                "safety": {"direct_exchange_mutation_by_cognition": False, "requires_executor": True},
            }
        ],
    }


def _gold_company() -> dict:
    return {
        "status": "gold_capital_intelligence_company_ready_with_gates",
        "generated_at": NOW.isoformat(),
        "summary": {
            "gold_action_state": "fresh_interval_validated_gold_projection_required",
            "verified_real_data_action_allowed": False,
            "hnc_auris_quantum_probability_route_passed": False,
        },
        "blockers": [{"id": "fresh_interval_validated_gold_projection_blocking"}],
    }


def _fixture(
    root: Path,
    *,
    cache_age: int,
    registry_age: int,
    stale: bool,
    gold_intent: bool,
    blockers: list[str] | None = None,
    submitted: int = 0,
    attempted: int = 0,
    gold_candidate: bool = True,
    capital_route_visible: bool = True,
    capital_route_ready: bool = True,
) -> None:
    _write_json(root / "ws_cache/ws_prices.json", _stream_cache(age_seconds=cache_age))
    _write_json(root / "state/aureon_capital_tradable_asset_registry.json", _capital_registry(age_seconds=registry_age))
    _write_json(
        root / "state/unified_runtime_status.json",
        _runtime(
            stale=stale,
            blockers=blockers,
            submitted=submitted,
            attempted=attempted,
            gold_candidate=gold_candidate,
            capital_route_visible=capital_route_visible,
            capital_route_ready=capital_route_ready,
        ),
    )
    _write_json(root / "state/unified_exchange_order_intents.json", _intents(gold=gold_intent))
    _write_json(root / "frontend/public/aureon_gold_capital_intelligence_company.json", _gold_company())


def test_stale_live_data_blocks_goal_trade_handover(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=600,
        registry_age=60,
        stale=True,
        gold_intent=True,
        blockers=["current_tick_stale"],
    )
    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)

    assert report["data_capture"]["fresh_for_order_action"] is False
    assert report["goal_trade_proof"]["gold_order_intent_ready"] is True
    assert report["goal_trade_proof"]["handover_ready"] is False
    assert report["goal_trade_proof"]["proof_state"] == "gold_goal_order_intent_ready_but_gated"
    assert "stream_cache_stale" in report["goal_trade_proof"]["blockers"]
    assert "current_tick_stale" in report["goal_trade_proof"]["blockers"]


def test_live_goal_audit_reports_lifecycle_continuity_missing(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=10,
        registry_age=10,
        stale=False,
        gold_intent=True,
        submitted=1,
        blockers=[],
    )
    lifecycle_row = {
        "lifecycle_id": "olife-test",
        "current_status": "order_submitted",
        "symbol": "GOLD",
        "side": "BUY",
        "venue": "capital",
        "market_type": "cfd",
        "route_key": "capital:cfd:GOLD:BUY",
        "missing_links": ["candidate_ready", "intent_published"],
    }
    _write_json(
        tmp_path / "state/unified_order_lifecycle_latest.json",
        {
            "generated_at": NOW.isoformat(),
            "event_count": 1,
            "lifecycle_count": 1,
            "active_lifecycle_count": 1,
            "completed_lifecycle_count": 0,
            "continuity_blockers": ["lifecycle_continuity_missing"],
            "latest_event": {
                "status": "order_submitted",
                "lifecycle_id": "olife-test",
                "symbol": "GOLD",
                "route_key": "capital:cfd:GOLD:BUY",
            },
            "lifecycles": [lifecycle_row],
            "active_lifecycles": [lifecycle_row],
            "events": [],
        },
    )

    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)

    assert "lifecycle_continuity_missing" in report["order_lifecycle_proof"]["blockers"]
    assert "lifecycle_continuity_missing" in report["goal_trade_proof"]["blockers"]


def test_live_goal_audit_reports_lifecycle_stress_certification(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=10,
        registry_age=10,
        stale=False,
        gold_intent=True,
    )
    _write_json(
        tmp_path / "frontend/public/aureon_order_lifecycle_stress_audit.json",
        {
            "generated_at": NOW.isoformat(),
            "status": "order_lifecycle_stress_certified",
            "summary": {
                "case_count": 9,
                "passed_count": 9,
                "failed_count": 0,
                "requirement_count": 14,
                "covered_requirement_count": 14,
                "coverage_percent": 100.0,
                "capital_gold_path_certified": True,
                "duplicate_route_blocked": True,
                "restart_recovery_certified": True,
                "multi_venue_recovery_certified": True,
                "close_verification_enforced": True,
                "partial_fill_certified": True,
                "stale_broker_proof_blocked": True,
                "failure_state_mapping_certified": True,
                "broker_requirement_matrix_complete": True,
                "no_live_mutation": True,
                "no_ui_mutation_controls": True,
                "mock_broker_status": "order_lifecycle_stress_certified",
                "mock_broker_certified": True,
                "sandbox_paper_status": "sandbox_paper_certified",
                "sandbox_paper_certified": True,
                "sandbox_paper_case_count": 5,
                "sandbox_paper_passed_count": 5,
                "sandbox_paper_requirement_count": 5,
                "sandbox_paper_covered_requirement_count": 5,
                "sandbox_environment_guard_passed": True,
                "sandbox_no_production_order_endpoints": True,
                "sandbox_probe_mode": "guarded_fixture_no_broker_mutation",
            },
            "proof_tiers": {
                "mock_broker": {"status": "order_lifecycle_stress_certified", "certified": True},
                "sandbox_paper": {"status": "sandbox_paper_certified", "certified": True},
            },
            "blockers": [],
            "missing_requirements": [],
            "sandbox_paper_cases": [],
            "sandbox_paper_requirements": [],
            "cases": [],
        },
    )

    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)
    stress = report["order_lifecycle_stress_proof"]

    assert stress["state"] == "order_lifecycle_stress_certified"
    assert stress["passed_count"] == 9
    assert stress["covered_requirement_count"] == 14
    assert stress["capital_gold_path_certified"] is True
    assert stress["multi_venue_recovery_certified"] is True
    assert stress["stale_broker_proof_blocked"] is True
    assert stress["broker_requirement_matrix_complete"] is True
    assert stress["no_live_mutation"] is True
    assert stress["mock_broker_certified"] is True
    assert stress["sandbox_paper_certified"] is True
    assert stress["sandbox_paper_passed_count"] == 5
    assert stress["sandbox_paper_covered_requirement_count"] == 5
    assert stress["sandbox_no_production_order_endpoints"] is True
    assert stress["proof_tiers"]["sandbox_paper"]["status"] == "sandbox_paper_certified"


def test_live_goal_audit_reports_capital_ecosystem_proof(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=10,
        registry_age=10,
        stale=False,
        gold_intent=True,
    )
    _write_json(
        tmp_path / "frontend/public/aureon_capital_ecosystem_intelligence_company.json",
        {
            "generated_at": NOW.isoformat(),
            "status": "capital_ecosystem_intelligence_ready",
            "summary": {
                "candidate_count": 120,
                "trade_ready_candidate_count": 90,
                "active_watchlist_count": 40,
                "active_watchlist_limit": 40,
                "bench_watchlist_count": 100,
                "bench_watchlist_limit": 100,
                "gold_preserved": True,
                "shadow_hedge_count": 12,
                "shadow_hedges_only": True,
                "close_first_opportunity_count": 2,
                "active_lifecycle_route_count": 1,
                "top_velocity_score": 0.91,
                "no_external_hedge_mutation": True,
                "existing_runtime_gates_authoritative": True,
            },
            "top_velocity_candidates": [{"symbol": "US100", "fast_profit_velocity_score": 0.91}],
            "shadow_hedges": [{"authority": "shadow_only", "mutation_allowed": False}],
            "close_first_opportunities": [],
            "blockers": [],
        },
    )

    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)
    proof = report["capital_ecosystem_proof"]

    assert proof["state"] == "capital_ecosystem_intelligence_ready"
    assert proof["active_watchlist_count"] == 40
    assert proof["active_watchlist_limit"] == 40
    assert proof["bench_watchlist_count"] == 100
    assert proof["shadow_hedge_count"] == 12
    assert proof["no_external_hedge_mutation"] is True


def test_live_goal_audit_reports_capital_live_dry_stress_proof(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=10,
        registry_age=10,
        stale=False,
        gold_intent=True,
    )
    _write_json(
        tmp_path / "frontend/public/aureon_capital_ecosystem_live_dry_stress_audit.json",
        {
            "generated_at": NOW.isoformat(),
            "status": "live_dry_certified",
            "summary": {
                "runtime_fresh": True,
                "active_watchlist_count": 40,
                "bench_watchlist_count": 100,
                "candidate_count": 120,
                "active_lifecycle_route_count": 2,
                "duplicate_routes_blocked": True,
                "close_first_opportunity_count": 1,
                "shadow_hedge_count": 12,
                "shadow_hedges_only": True,
                "broker_correlation_complete": True,
                "lifecycle_continuity_complete": True,
                "recovered_position_count": 0,
                "recovered_positions_certified": True,
                "recovery_certification_status": "not_applicable",
                "recovered_close_chain_status": "not_applicable",
                "recovered_close_request_count": 0,
                "recovered_close_acknowledged_count": 0,
                "recovered_position_absence_verified_count": 0,
                "recovered_outcome_recorded_count": 0,
                "recovered_exit_blockers": [],
                "no_live_mutation": True,
            },
            "blockers": [],
        },
    )

    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)
    proof = report["capital_live_dry_stress_proof"]

    assert proof["state"] == "live_dry_certified"
    assert proof["status"] == "live_dry_certified"
    assert proof["runtime_fresh"] is True
    assert proof["active_watchlist_count"] == 40
    assert proof["bench_watchlist_count"] == 100
    assert proof["duplicate_routes_blocked"] is True
    assert proof["broker_correlation_complete"] is True
    assert proof["recovery_certification_status"] == "not_applicable"
    assert proof["recovered_close_chain_status"] == "not_applicable"
    assert proof["no_live_mutation"] is True


def test_live_goal_audit_reports_capital_revenue_logic_proof(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=10,
        registry_age=10,
        stale=False,
        gold_intent=True,
    )
    _write_json(
        tmp_path / "frontend/public/aureon_capital_revenue_logic_stress_audit.json",
        {
            "generated_at": NOW.isoformat(),
            "status": "capital_order_intent_gated",
            "summary": {
                "candidate_count": 120,
                "trade_ready_candidate_count": 90,
                "net_positive_candidate_count": 7,
                "intent_eligible_candidate_count": 0,
                "candidate_level_intent_eligible_count": 3,
                "false_positive_reject_count": 14,
                "active_watchlist_count": 40,
                "bench_watchlist_count": 100,
                "close_first_opportunity_count": 2,
                "duplicate_route_blocked_count": 10,
                "shadow_confirmation_count": 12,
                "external_shadow_only": True,
                "live_gates_blocking": True,
                "no_live_mutation": True,
            },
            "capital_order_intent_readiness": {
                "candidate_level_eligible_count": 3,
                "intent_eligible_candidate_count": 0,
                "live_gates_blocking": True,
                "runtime_gate_blockers": ["exchange_mutations_disabled"],
            },
            "net_positive_candidates": [
                {
                    "symbol": "US100",
                    "side": "BUY",
                    "expected_net_revenue": 0.12,
                    "revenue_blockers": [],
                }
            ],
            "blockers": ["capital_order_intent_gated"],
        },
    )

    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)
    proof = report["capital_revenue_logic_proof"]

    assert proof["state"] == "capital_revenue_logic_attention"
    assert proof["status"] == "capital_order_intent_gated"
    assert proof["net_positive_candidate_count"] == 7
    assert proof["intent_eligible_candidate_count"] == 0
    assert proof["candidate_level_intent_eligible_count"] == 3
    assert proof["false_positive_reject_count"] == 14
    assert proof["top_candidate"]["symbol"] == "US100"
    assert proof["top_expected_net_revenue"] == 0.12
    assert proof["live_gates_blocking"] is True
    assert "capital_order_intent_gated" in proof["blockers"]


def test_live_goal_audit_reports_capital_revenue_live_gate_readiness(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=10,
        registry_age=10,
        stale=False,
        gold_intent=True,
    )
    _write_json(
        tmp_path / "frontend/public/aureon_capital_revenue_live_gate_readiness_audit.json",
        {
            "generated_at": NOW.isoformat(),
            "status": "live_gate_attention",
            "summary": {
                "net_positive_candidate_count": 2,
                "ready_now_candidate_count": 0,
                "blocked_candidate_count": 2,
                "missing_gate_count": 4,
                "runtime_gates_clear": False,
                "recovered_exit_clear": False,
                "duplicate_routes_blocked": True,
                "broker_correlation_complete": True,
                "external_shadow_only": True,
                "no_live_mutation": True,
            },
            "current_live_gate_readiness": {
                "missing_gate_ids": [
                    "fresh_capital_snapshot",
                    "no_duplicate_active_route",
                    "recovered_exit_readiness_clear",
                    "executor_enabled",
                ]
            },
            "candidate_readiness_rows": [
                {
                    "candidate_id": "candidate-US100-BUY",
                    "route_key": "capital:cfd:US100:BUY",
                    "symbol": "US100",
                    "side": "BUY",
                    "expected_net_revenue": 0.18,
                    "ready_now": False,
                    "missing_live_gate_ids": ["executor_enabled"],
                }
            ],
            "runtime_gate_proof": {"runtime_gate_ids": ["executor_enabled"]},
            "lifecycle_gate_proof": {"lifecycle_continuity_resolved": False},
            "close_first_exit_proof": {"recovered_close_chain_status": "recovered_exit_ready_attention"},
            "external_confirmation_proof": {"external_live_order_intent_count": 0},
            "blockers": ["executor_enabled", "recovered_exit_readiness_clear"],
        },
    )

    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)
    proof = report["capital_revenue_live_gate_readiness_proof"]

    assert proof["state"] == "capital_revenue_live_gate_attention"
    assert proof["status"] == "live_gate_attention"
    assert proof["net_positive_candidate_count"] == 2
    assert proof["ready_now_candidate_count"] == 0
    assert proof["top_candidate"]["symbol"] == "US100"
    assert proof["top_expected_net_revenue"] == 0.18
    assert "executor_enabled" in proof["missing_gate_ids"]
    assert proof["external_shadow_only"] is True
    assert proof["no_live_mutation"] is True


def test_live_goal_audit_exposes_recovered_position_live_dry_attention(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=10,
        registry_age=10,
        stale=False,
        gold_intent=True,
    )
    _write_json(
        tmp_path / "frontend/public/aureon_capital_ecosystem_live_dry_stress_audit.json",
        {
            "generated_at": NOW.isoformat(),
            "status": "recovered_position_certified_attention",
            "summary": {
                "runtime_fresh": True,
                "active_watchlist_count": 40,
                "bench_watchlist_count": 100,
                "candidate_count": 120,
                "active_lifecycle_route_count": 2,
                "duplicate_routes_blocked": True,
                "close_first_opportunity_count": 2,
                "shadow_hedge_count": 12,
                "shadow_hedges_only": True,
                "broker_correlation_complete": True,
                "lifecycle_continuity_complete": True,
                "recovered_position_count": 2,
                "recovered_positions_certified": True,
                "recovery_certification_status": "recovered_position_certified_attention",
                "recovered_upstream_context_missing_count": 2,
                "recovered_position_close_first_covered": True,
                "recovered_duplicate_route_blocking_active": True,
                "recovered_close_chain_status": "recovered_exit_ready_attention",
                "recovered_close_request_count": 0,
                "recovered_close_acknowledged_count": 0,
                "recovered_position_absence_verified_count": 0,
                "recovered_outcome_recorded_count": 0,
                "recovered_exit_blockers": ["recovered_exit_ready_attention", "recovered_upstream_context_missing"],
                "no_live_mutation": True,
            },
            "blockers": ["recovered_upstream_context_missing"],
        },
    )

    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)
    proof = report["capital_live_dry_stress_proof"]

    assert proof["state"] == "live_dry_attention"
    assert proof["status"] == "recovered_position_certified_attention"
    assert proof["recovered_position_count"] == 2
    assert proof["recovered_positions_certified"] is True
    assert proof["recovered_upstream_context_missing_count"] == 2
    assert proof["recovered_close_chain_status"] == "recovered_exit_ready_attention"
    assert proof["recovered_exit_blockers"] == ["recovered_exit_ready_attention", "recovered_upstream_context_missing"]
    assert "recovered_upstream_context_missing" in proof["blockers"]


def test_non_gold_intents_do_not_count_as_goal_trade(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=30,
        registry_age=60,
        stale=False,
        gold_intent=False,
    )
    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)

    assert report["data_capture"]["fresh_for_order_action"] is True
    assert report["order_intent_proof"]["intent_count"] == 1
    assert report["order_intent_proof"]["gold_intent_count"] == 0
    assert report["goal_trade_proof"]["proof_state"] == "blocked_no_gold_order_intent_ready"
    assert report["goal_trade_proof"]["live_trade_produced"] is False


def test_fresh_capital_stream_overlay_unblocks_stale_registry_snapshot(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=30,
        registry_age=222_000,
        stale=False,
        gold_intent=False,
    )
    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)

    best = report["capital_gold_profile"]["best_gold_asset"]
    assert report["capital_gold_profile"]["state"] == "capital_gold_fresh"
    assert best["live_quote_overlay_applied"] is True
    assert best["bid"] == 4531.0
    assert "capital_gold_registry_snapshot_stale" not in report["goal_trade_proof"]["blockers"]
    assert report["goal_trade_proof"]["fresh_data_ready"] is True
    assert report["goal_trade_proof"]["proof_state"] == "blocked_no_gold_order_intent_ready"


def test_fresh_gold_intent_reaches_runtime_gated_proof_ready(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=30,
        registry_age=60,
        stale=False,
        gold_intent=True,
    )
    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)

    assert report["runtime_candidate_proof"]["gold_runtime_candidate_ready"] is True
    assert report["runtime_candidate_proof"]["capital_cfd_route_visible"] is True
    assert report["runtime_candidate_proof"]["intent_packet_fresh"] is True
    assert report["goal_trade_proof"]["proof_state"] == "gold_runtime_gated_intent_proof_ready"
    assert report["goal_trade_proof"]["live_trade_produced"] is False
    assert report["goal_trade_proof"]["handover_ready"] is True


def test_submitted_fresh_gold_intent_is_live_goal_trade_proof(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=30,
        registry_age=60,
        stale=False,
        gold_intent=True,
        submitted=1,
        attempted=1,
    )
    report = build_live_goal_trade_audit(root=tmp_path, now=NOW)

    assert report["goal_trade_proof"]["proof_state"] == "live_gold_goal_trade_submitted"
    assert report["goal_trade_proof"]["live_trade_produced"] is True
    assert report["goal_trade_proof"]["handover_ready"] is True


def test_write_live_goal_trade_audit_artifacts(tmp_path: Path) -> None:
    _fixture(
        tmp_path,
        cache_age=30,
        registry_age=60,
        stale=False,
        gold_intent=True,
        submitted=1,
        attempted=1,
    )
    report = build_and_write_live_goal_trade_audit(root=tmp_path)

    assert report["write_info"]["evidence_writes"]
    assert (tmp_path / "state/aureon_live_goal_trade_audit_last_run.json").exists()
    assert (tmp_path / "docs/audits/aureon_live_goal_trade_audit.json").exists()
    assert (tmp_path / "docs/audits/aureon_live_goal_trade_audit.md").exists()
    assert (tmp_path / "frontend/public/aureon_live_goal_trade_audit.json").exists()
