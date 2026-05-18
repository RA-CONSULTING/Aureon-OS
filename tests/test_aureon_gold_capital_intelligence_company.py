from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aureon.autonomous.aureon_gold_capital_intelligence_company import (
    COGNITIVE_ROUTE_SURFACES,
    GOLD_INTELLIGENCE_SURFACES,
    GOLD_AGENT_SUPPORT_SURFACES,
    GOLD_MARGIN_TRADER_UNITY_SURFACES,
    GOLD_LOCAL_RESEARCH_PACKETS,
    HISTORICAL_STRESS_SURFACES,
    HFT_SPEED_PREDICTION_SURFACES,
    build_and_write_gold_capital_intelligence_company,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _fixture_repo(root: Path, *, include_gold: bool = True, runtime_stale: bool = True) -> None:
    now = datetime.now(timezone.utc).isoformat()
    assets = []
    if include_gold:
        assets.append(
            {
                "symbol": "GOLD",
                "epic": "GOLD",
                "instrument_name": "Gold",
                "asset_class": "commodity_cfd",
                "instrument_type": "COMMODITIES",
                "market_status": "TRADEABLE",
                "trade_ready": True,
                "bid": 4559.41,
                "ask": 4559.91,
                "mid_price": 4559.66,
                "spread": 0.5,
                "spread_pct": 0.01096573,
                "currency": "USD",
                "minimum_deal_size": 0.01,
                "leverage_estimate": 1.0,
                "margin_factor_pct": 100.0,
                "margin_required_for_min_deal": 45.5966,
                "min_notional_estimate": 45.5966,
                "can_buy": True,
                "can_sell": True,
                "last_snapshot_at": now,
            }
        )
    _write_json(
        root / "state" / "aureon_capital_tradable_asset_registry.json",
        {"assets": assets, "summary": {"total_markets": len(assets), "trade_ready_count": len(assets)}},
    )
    _write_json(
        root / "state" / "unified_runtime_status.json",
        {
            "generated_at": now,
            "trading_ready": True,
            "data_ready": True,
            "stale": runtime_stale,
            "stale_reason": "tick_in_progress_stalled",
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_global_financial_coverage_map.json",
        {
            "status": "global_financial_map_complete_for_configured_registry",
            "generated_at": now,
            "summary": {
                "coverage_percent": 100,
                "active_live_source_count": 4,
                "fresh_exchange_count": 4,
                "usable_domain_count": 1,
                "domain_count": 6,
                "fresh_source_count": 10,
            },
            "rows": [
                {
                    "domain": "historical_waveform_memory",
                    "fresh": True,
                    "usable": True,
                    "live_count": 3026,
                    "history_count": 1_749_962,
                    "missing": [],
                },
                {
                    "domain": "cfd_fx_indices_equities",
                    "fresh": True,
                    "usable": True,
                    "live_count": 18,
                    "history_count": 3291,
                    "missing": [],
                },
                {
                    "domain": "equity_and_etf_live_market",
                    "fresh": True,
                    "usable": True,
                    "live_count": 6,
                    "history_count": 0,
                    "missing": [],
                },
                {
                    "domain": "crypto_live_market",
                    "fresh": True,
                    "usable": True,
                    "live_count": 3026,
                    "history_count": 1_441_738,
                    "missing": [],
                },
                {
                    "domain": "macro_events_context",
                    "fresh": False,
                    "usable": False,
                    "live_count": 0,
                    "history_count": 0,
                    "missing": ["fresh_economic_calendar"],
                },
                {
                    "domain": "sentiment_onchain_forecast_context",
                    "fresh": True,
                    "usable": True,
                    "live_count": 392,
                    "history_count": 669,
                    "missing": [],
                },
            ],
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_exchange_data_capability_matrix.json",
        {
            "status": "exchange_data_capability_matrix_connected_guarded_runtime_stale",
            "generated_at": now,
            "summary": {
                "connected_exchange_count": 4,
                "exchange_count": 4,
                "fresh_feed_count": 4,
                "data_ready": True,
                "runtime_stale": runtime_stale,
                "preflight_overall": "yellow",
            },
            "rows": [
                {
                    "exchange": "capital",
                    "label": "Capital.com",
                    "current_state": {
                        "fresh_feed": True,
                        "usable_for_mapping": True,
                        "usable_for_decision": False,
                        "waveform_history_active": True,
                    },
                    "data_channels": [
                        {"name": "live_ticks", "status": "fresh"},
                        {"name": "market_hours", "status": "available"},
                        {"name": "price_history", "status": "available"},
                    ],
                    "gaps": ["runtime_stale_blocks_fresh_live_decision_use"] if runtime_stale else [],
                    "optimization_policy": {"stream_preferred": True},
                },
                {
                    "exchange": "binance",
                    "label": "Binance",
                    "current_state": {"fresh_feed": True, "usable_for_mapping": True},
                    "data_channels": [{"name": "live_ticks", "status": "fresh"}],
                    "gaps": [],
                },
                {
                    "exchange": "kraken",
                    "label": "Kraken",
                    "current_state": {"fresh_feed": True, "usable_for_mapping": True},
                    "data_channels": [{"name": "live_ticks", "status": "fresh"}],
                    "gaps": [],
                },
                {
                    "exchange": "alpaca",
                    "label": "Alpaca",
                    "current_state": {"fresh_feed": True, "usable_for_mapping": True},
                    "data_channels": [
                        {"name": "live_ticks", "status": "fresh"},
                        {"name": "market_hours", "status": "available"},
                    ],
                    "gaps": [],
                },
            ],
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_exchange_monitoring_checklist.json",
        {
            "status": "exchange_monitoring_connected_guarded_runtime_stale",
            "generated_at": now,
            "summary": {"fresh_exchange_count": 4, "exchange_count": 4, "runtime_stale": runtime_stale},
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_trading_intelligence_checklist.json",
        {
            "status": "connected_guarded",
            "generated_at": now,
            "summary": {
                "runtime_stale": runtime_stale,
                "stale_reason": "tick_in_progress_stalled" if runtime_stale else "",
                "decision_self_trust_score": 0.33,
                "trust_to_decide": True,
                "trust_to_shadow": True,
                "trust_to_act": False,
                "decision_posture": "trust_decision_shadow_until_runtime_fresh",
            },
        },
    )
    _write_json(
        root / "docs" / "audits" / "aureon_harmonic_affect_state.json",
        {
            "status": "harmonic_affect_state_ready",
            "generated_at": now,
            "summary": {
                "hnc_coherence_score": 0.5,
                "goal_alignment": 0.6,
                "reward_alignment": 0.55,
                "anchor_readiness": 1.0,
                "runtime_stale": runtime_stale,
                "safety_blocker_count": 2,
                "blind_spot_count": 3,
                "affect_phase": "protective_recalibration",
            },
        },
    )
    _write_json(
        root / "state" / "aureon_hnc_cognitive_proof.json",
        {
            "generated_at": now,
            "status": "passing",
            "passed": True,
            "real_data": {
                "passed": True,
                "source_count": 5,
                "source_names": ["capital", "live_stream_cache", "world_financial_ecosystem", "historical_waveform_models"],
            },
            "master_formula": {"evaluated": True, "score": 0.82, "passed": True},
            "auris_nodes": {
                "evaluated": True,
                "passed": True,
                "node_count": 9,
                "coherence": 0.61,
                "status": "coherent_shadow_gate",
                "nodes": {f"Node{i}": {"value": 0.5, "role": "fixture"} for i in range(1, 10)},
            },
        },
    )
    _write_json(
        root / "state" / "aureon_hnc_operating_cycle.json",
        {"generated_at": now, "status": "hnc_operating_cycle_ready", "passed": True},
    )
    _write_json(
        root / "state" / "aureon_hnc_quantum_packet_last_run.json",
        {
            "generated_at": now,
            "schema_version": 1,
            "secret_policy": "metadata_only_no_values_returned",
            "evidence": {"packet_format": "hncqp1", "packet_summaries": {}},
        },
    )
    _write_json(
        root / "state" / "lambda_history.json",
        {
            "history": [0.2, 0.3, 0.42],
            "psi_history": [0.6, 0.65, 0.7],
            "step_count": 3,
            "saved_at": datetime.now(timezone.utc).timestamp(),
            "version": 2,
        },
    )
    probability_dir = root / "data"
    probability_dir.mkdir(parents=True, exist_ok=True)
    (probability_dir / "probability_predictions.jsonl").write_text(
        "\n".join(
            json.dumps(row)
            for row in [
                {
                    "prediction_id": "GOLD_20260517_fixture_1",
                    "symbol": "GOLD",
                    "interval": "tick",
                    "source_tickers": ["GOLD", "XAUUSD", "DXY"],
                    "timestamp": now,
                    "predicted_direction": "BULLISH",
                    "actual_direction": "UP",
                    "predicted_probability": 0.67,
                    "predicted_confidence": 0.62,
                    "predicted_action": "BUY",
                    "forecast_level": 4560.0,
                    "shadow_p_l_effect": 0.012,
                    "validated": True,
                    "direction_correct": True,
                    "outcome_score": 1.0,
                },
                {
                    "prediction_id": "XAUUSD_20260517_fixture_2",
                    "symbol": "XAUUSD",
                    "interval": "1m",
                    "source_tickers": ["XAUUSD", "GLD", "DXY"],
                    "timestamp": now,
                    "predicted_direction": "BEARISH",
                    "actual_direction": "DOWN",
                    "predicted_probability": 0.61,
                    "predicted_confidence": 0.59,
                    "predicted_action": "SELL",
                    "forecast_level": 4558.8,
                    "shadow_p_l_effect": 0.01,
                    "validated": True,
                    "direction_correct": True,
                    "outcome_score": 0.8,
                },
                {
                    "prediction_id": "GOLD_20260517_fixture_3",
                    "symbol": "GOLD",
                    "interval": "5m",
                    "source_tickers": ["GOLD", "GC=F", "USOIL"],
                    "timestamp": now,
                    "predicted_direction": "BULLISH",
                    "actual_direction": "UP",
                    "predicted_probability": 0.58,
                    "predicted_confidence": 0.55,
                    "predicted_action": "BUY",
                    "forecast_level": 4561.2,
                    "shadow_p_l_effect": 0.008,
                    "validated": True,
                    "direction_correct": True,
                    "outcome_score": 0.6,
                },
                {
                    "prediction_id": "GOLD_20260517_fixture_4",
                    "symbol": "GOLD",
                    "interval": "15m",
                    "source_tickers": ["GOLD", "VIX", "BTCUSDT"],
                    "timestamp": now,
                    "predicted_direction": "BULLISH",
                    "actual_direction": "DOWN",
                    "predicted_probability": 0.52,
                    "predicted_confidence": 0.5,
                    "predicted_action": "BUY",
                    "forecast_level": 4562.4,
                    "shadow_p_l_effect": -0.004,
                    "validated": True,
                    "direction_correct": False,
                    "outcome_score": -0.2,
                },
                {
                    "prediction_id": "GOLD_20260517_fixture_5",
                    "symbol": "GOLD",
                    "interval": "1h",
                    "source_tickers": ["GOLD", "GLD", "US10Y"],
                    "timestamp": now,
                    "predicted_direction": "BULLISH",
                    "actual_direction": "UP",
                    "predicted_probability": 0.63,
                    "predicted_confidence": 0.57,
                    "predicted_action": "BUY",
                    "forecast_level": 4564.1,
                    "shadow_p_l_effect": 0.011,
                    "validated": True,
                    "direction_correct": True,
                    "outcome_score": 0.7,
                },
                {
                    "prediction_id": "GOLD_20260517_fixture_6",
                    "symbol": "GOLD",
                    "interval": "session",
                    "source_tickers": ["GOLD", "DXY", "GDX"],
                    "timestamp": now,
                    "predicted_direction": "BULLISH",
                    "actual_direction": "UP",
                    "predicted_probability": 0.66,
                    "predicted_confidence": 0.6,
                    "predicted_action": "BUY",
                    "forecast_level": 4568.5,
                    "shadow_p_l_effect": 0.014,
                    "validated": True,
                    "direction_correct": True,
                    "outcome_score": 0.9,
                },
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (probability_dir / "probability_matrix_data.jsonl").write_text(
        json.dumps(
            {
                "timestamp": now,
                "symbol": "XAUUSD",
                "exchange": "CAPITAL",
                "price": 4559.66,
                "probability_score": 0.64,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        root / "state" / "aureon_data_ocean_status.json",
        {
            "status": "data_ocean_complete",
            "generated_at": now,
            "summary": {
                "runtime_stale": runtime_stale,
                "top_gaps": [
                    {
                        "source_id": "fred_macro",
                        "reason": "required_credentials_missing",
                        "next_action": "Configure FRED_API_KEY and refresh rates context.",
                    }
                ],
            },
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_world_financial_ecosystem_intelligence.json",
        {
            "status": "world_financial_ecosystem_intelligence_mesh",
            "generated_at": now,
            "fed_to_decision_logic": True,
            "decision_symbols": {
                "GOLDUSD": {
                    "symbol": "GOLDUSD",
                    "leader": "DXY",
                    "follower": "GOLD",
                    "correlation": -0.68,
                    "lag_seconds": 300,
                    "confidence": 0.71,
                    "change_pct": 0.44,
                    "reason": "cross_asset_presignal",
                    "category": "macro_fx",
                },
                "BTCUSD": {
                    "symbol": "BTCUSD",
                    "leader": "BTC",
                    "follower": "GOLD",
                    "correlation": 0.41,
                    "lag_seconds": 600,
                    "confidence": 0.38,
                    "change_pct": -0.12,
                    "reason": "liquidity_proxy",
                    "category": "crypto",
                },
            },
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_unified_shadow_trade_report.json",
        {
            "status": "shadow_reporting_active",
            "generated_at": now,
            "shadows": [
                {
                    "symbol": "GOLD",
                    "venue": "capital",
                    "side": "BUY",
                    "confidence": 0.66,
                    "orderbook_pressure": {
                        "available": True,
                        "symbol": "GOLD",
                        "pressure_side": "BUY",
                        "score": 0.72,
                        "reason": "fixture_gold_quote_pressure",
                    },
                    "fast_money_profile": {"orderbook_alignment": "aligned", "orderbook_score": 0.72},
                },
                {
                    "symbol": "USOIL",
                    "venue": "capital",
                    "side": "CONTEXT",
                    "confidence": 0.44,
                    "selection_basis": "oil_energy_inflation_context",
                    "orderbook_pressure": {
                        "available": True,
                        "symbol": "USOIL",
                        "pressure_side": "BUY",
                        "score": 0.51,
                        "reason": "fixture_energy_pressure_context",
                    },
                },
                {
                    "symbol": "RANDOMABC",
                    "venue": "test",
                    "side": "BUY",
                    "confidence": 0.31,
                    "selection_basis": "fixture_generic_shadow_unrelated",
                    "orderbook_pressure": {
                        "available": True,
                        "symbol": "RANDOMABC",
                        "pressure_side": "BUY",
                        "score": 0.4,
                        "reason": "fixture_generic_shadow_excluded",
                    },
                },
            ],
        },
    )
    _write_json(
        root / "frontend" / "public" / "aureon_scanner_fusion_matrix.json",
        {
            "status": "scanner_fusion_ready",
            "generated_at": now,
            "fresh": True,
            "fed_to_decision_logic": True,
            "systems": [
                {
                    "name": "MultiHorizonWaveformMemory",
                    "facet": "historical_waveform_memory",
                    "fresh": True,
                    "usable_for_decision": True,
                    "reason": "fixture waveform symbols",
                    "repo_path": "aureon/analytics/aureon_multi_horizon_waveform_model.py",
                }
            ],
            "candidates": [
                {
                    "symbol": "GOLD",
                    "side": "BUY",
                    "selection_rank": 1,
                    "scanner_fusion_score": 0.78,
                    "profit_velocity_score": 0.62,
                    "fast_money_score": 0.58,
                    "cross_reference_count": 6,
                    "usable_for_decision": True,
                    "orderbook_alignment": "aligned",
                    "active_scanners": ["MultiHorizonWaveformMemory", "UnifiedSignalEngine", "WorldFinancialEcosystemFeed"],
                    "blockers": [],
                },
                {
                    "symbol": "WTI",
                    "side": "CONTEXT",
                    "selection_rank": 2,
                    "scanner_fusion_score": 0.54,
                    "profit_velocity_score": 0.36,
                    "fast_money_score": 0.41,
                    "cross_reference_count": 3,
                    "usable_for_decision": False,
                    "orderbook_alignment": "context",
                    "active_scanners": ["WorldFinancialEcosystemFeed", "MacroRatesReader"],
                    "blockers": ["context_only_for_gold"],
                },
            ],
        },
    )
    support_payloads = {
        "aureon_coding_organism_bridge.json": {
            "status": "coding_organism_ready",
            "generated_at": now,
            "handover_ready": True,
            "summary": {"scope_status": "ready_for_client", "route_clean": True},
        },
        "aureon_capability_forge.json": {
            "status": "capability_forge_ready",
            "generated_at": now,
            "handover_ready": True,
            "summary": {"quality_gate": "passing"},
        },
        "aureon_autonomous_job_executor.json": {
            "status": "autonomous_jobs_ready",
            "generated_at": now,
            "queue_depth": 1,
            "active_job": {"id": "gold_fixture_job"},
            "jobs": [{"id": "gold_fixture_job", "state": "handover_ready"}],
        },
        "aureon_autonomous_self_run_loop.json": {
            "status": "self_run_loop_ready",
            "generated_at": now,
            "summary": {"last_job_advanced": "gold_fixture_job"},
        },
        "aureon_dynamic_prompt_filter.json": {
            "status": "dynamic_prompt_filter_ready",
            "generated_at": now,
            "filter_mode": "clear_operator",
            "handover_ready": True,
        },
    }
    for name, payload in support_payloads.items():
        _write_json(root / "frontend" / "public" / name, payload)
    _write_json(
        root / "state" / "aureon_agent_company_last_run.json",
        {
            "status": "agent_company_registry_ready",
            "generated_at": now,
            "summary": {"roles": 41, "tools_enabled": True},
        },
    )
    for surface in GOLD_INTELLIGENCE_SURFACES:
        path = root / surface["path"]
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        terms = " ".join(str(term) for term in surface.get("terms", []))
        path.write_text(f"# {surface['id']}\nGold intelligence fixture {terms}\n", encoding="utf-8")
    for surface in COGNITIVE_ROUTE_SURFACES:
        path = root / surface["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        markers = "\n".join(str(marker) for marker in surface.get("required_markers", []))
        path.write_text(f"# {surface['id']}\n{markers}\n", encoding="utf-8")
    for surface in HFT_SPEED_PREDICTION_SURFACES:
        path = root / surface["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        markers = "\n".join(str(marker) for marker in surface.get("required_markers", []))
        path.write_text(f"# {surface['id']}\n{markers}\n", encoding="utf-8")
    for surface in HISTORICAL_STRESS_SURFACES:
        path = root / surface["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        markers = "\n".join(str(marker) for marker in surface.get("required_markers", []))
        path.write_text(f"# {surface['id']}\n{markers}\n", encoding="utf-8")
    for surface in GOLD_AGENT_SUPPORT_SURFACES:
        path = root / surface["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        markers = "\n".join(str(marker) for marker in surface.get("required_markers", []))
        path.write_text(f"# {surface['id']}\n{markers}\n", encoding="utf-8")
    for surface in GOLD_MARGIN_TRADER_UNITY_SURFACES:
        path = root / surface["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        markers = "\n".join(str(marker) for marker in surface.get("required_markers", []))
        path.write_text(f"# {surface['id']}\n{markers}\n", encoding="utf-8")
    for packet in GOLD_LOCAL_RESEARCH_PACKETS:
        path = root / packet["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        terms = " ".join(str(term) for term in packet.get("terms", []))
        path.write_text(f"# {packet['id']}\nGold research fixture {terms}\n", encoding="utf-8")


def test_gold_capital_company_builds_shadow_only_gold_packet(tmp_path: Path) -> None:
    _fixture_repo(tmp_path, include_gold=True, runtime_stale=True)

    report = build_and_write_gold_capital_intelligence_company(root=tmp_path)

    assert report["status"] == "gold_capital_intelligence_ready"
    assert report["target"]["epic"] == "GOLD"
    assert report["summary"]["target_symbol"] == "GOLD"
    assert report["decision"]["live_trade_allowed"] is False
    assert report["decision"]["shadow_observation_allowed"] is True
    assert report["summary"]["direction_guess"] == "OBSERVE_STALE"
    assert report["price_energy_hypothesis"]["mid_price"] == 4559.66
    assert report["who_what_where_when_how_act"]["act"] == "shadow_observe_refresh_before_live"
    assert len(report["company_roles"]) >= 8
    assert report["summary"]["gold_intelligence_surface_count"] >= 10
    assert report["summary"]["gold_intelligence_surface_ready_count"] == report["summary"]["gold_intelligence_surface_count"]
    assert report["summary"]["local_research_packet_count"] == len(GOLD_LOCAL_RESEARCH_PACKETS)
    assert report["summary"]["market_universe_bucket_counts"]["capital_gold_core"] == 1
    assert report["summary"]["cross_market_driver_count"] >= 10
    assert report["summary"]["cross_market_driver_score"] > 0
    assert report["summary"]["gold_exchange_optimization_status"] == "gold_exchange_optimization_attention"
    assert report["summary"]["gold_exchange_optimization_score"] > 0.7
    assert report["summary"]["gold_exchange_ready_venue_count"] == report["summary"]["gold_exchange_venue_count"]
    assert report["summary"]["gold_exchange_watchlist_bucket_count"] >= 6
    assert report["summary"]["gold_exchange_optimization_blocker_count"] >= 1
    assert report["gold_exchange_optimization"]["primary_target_venue"] == "Capital.com"
    assert report["gold_exchange_optimization"]["live_order_allowed"] is False
    assert report["gold_exchange_optimization"]["order_mutation_allowed"] is False
    assert any(venue["id"] == "capital" and venue["role"] == "primary_gold_target_venue" for venue in report["gold_exchange_optimization"]["venues"])
    assert any(item["bucket"] == "crypto_liquidity" for item in report["gold_exchange_optimization"]["related_asset_watchlist"])
    assert any(contract["id"] == "capital_gold_micro_monitor" for contract in report["gold_exchange_optimization"]["monitoring_contract"])
    assert report["summary"]["gold_margin_trader_unity_status"] == "gold_margin_trader_unity_attention"
    assert report["summary"]["gold_margin_unity_state"] == "gold_margin_unity_held"
    assert report["summary"]["gold_margin_unity_present_surface_count"] == report["summary"]["gold_margin_unity_surface_count"]
    assert report["summary"]["gold_margin_unity_blocker_count"] >= 1
    assert report["summary"]["gold_margin_live_order_allowed"] is False
    assert report["summary"]["gold_margin_order_allowed"] is False
    assert report["gold_margin_trader_unity"]["target_venue"] == "Capital.com"
    assert report["gold_margin_trader_unity"]["target_symbol"] == "GOLD"
    assert report["gold_margin_trader_unity"]["margin_command"]["live_order_allowed"] is False
    assert report["gold_margin_trader_unity"]["margin_command"]["margin_order_allowed"] is False
    assert any(role["surface_id"] == "unified_margin_brain" for role in report["gold_margin_trader_unity"]["margin_roles"])
    assert any(directive["id"] == "shadow_before_live" for directive in report["gold_margin_trader_unity"]["mission_directives"])
    assert any(surface["id"] == "capital_margin_runner" and surface["present"] for surface in report["gold_margin_trader_unity"]["route_surfaces"])
    assert any(item["id"] == "unify_margin_trader_for_gold" for item in report["tool_activation_plan"])
    assert report["summary"]["gold_swarm_agent_count"] >= 8
    assert report["summary"]["gold_swarm_compile_state"] == "held_for_fresh_evidence"
    assert report["summary"]["historical_signal_lane_count"] >= 6
    assert report["summary"]["historical_signal_ready_count"] >= 3
    assert report["summary"]["lead_lag_candidate_count"] >= 1
    assert report["summary"]["orderbook_signal_state"] in {"ready_shadow_replay", "attention_needs_fresh_proof", "attention_mapped_not_proven"}
    assert report["summary"]["chart_replay_state"] in {"ready_shadow_replay", "attention_needs_fresh_proof"}
    assert report["summary"]["gold_priority_data_queue_count"] >= 5
    assert report["summary"]["gold_priority_artifact_count"] == 2
    assert report["summary"]["three_p_floor_state"] == "hold_until_3p_floor_proven"
    assert report["summary"]["three_p_floor_side"] == "HOLD"
    assert report["summary"]["three_p_floor_minimum_move"] > 0
    assert report["three_p_profit_floor_gate"]["profit_floor_account_currency"] == 0.03
    assert report["three_p_profit_floor_gate"]["live_order_allowed"] is False
    assert report["three_p_profit_floor_gate"]["order_mutation_allowed"] is False
    assert report["three_p_profit_floor_gate"]["suggested_shadow_size"] >= 0.01
    assert any(blocker["id"] == "runtime_stale_blocks_3p_floor" for blocker in report["three_p_profit_floor_gate"]["blockers"])
    assert "target_formula" in report["three_p_profit_floor_gate"]["buy_contract"]
    assert report["summary"]["verified_real_data_gate_status"] == "verified_real_data_gate_blocking"
    assert report["summary"]["verified_real_data_action_allowed"] is False
    assert report["summary"]["verified_real_data_blocker_count"] >= 1
    assert report["verified_real_data_gate"]["action_allowed_by_data"] is False
    assert any(check["data_class"] == "shadow_derived_artifact" for check in report["verified_real_data_gate"]["shadow_artifact_checks"])
    assert any(item["id"] == "verified_real_data" for item in report["gold_action_command"]["proof_chain"])
    assert report["summary"]["gold_ticker_source_lane_count"] == 8
    assert report["summary"]["gold_ticker_source_fresh_lane_count"] >= 1
    assert report["summary"]["gold_signal_freshness_status"] == "gold_signal_freshness_matrix_blocking"
    assert report["summary"]["gold_signal_action_influence_allowed"] is False
    assert report["summary"]["gold_projection_required_interval_count"] == 6
    assert report["summary"]["gold_projection_validated_interval_count"] == 6
    assert report["summary"]["gold_projection_interval_status"] == "gold_projection_interval_validation_blocking"
    assert report["summary"]["gold_projection_interval_hit_rate"] >= 0.55
    assert report["summary"]["gold_projection_interval_shadow_pl"] > 0
    assert report["summary"]["gold_evolving_projection_path_status"] == "gold_evolving_projection_path_attention"
    assert report["summary"]["gold_evolving_projection_horizon_count"] >= 15
    assert report["summary"]["gold_evolving_projection_fresh_horizon_count"] >= 6
    assert report["summary"]["gold_evolving_projection_validated_horizon_count"] >= 6
    assert report["summary"]["gold_evolving_projection_hit_rate"] >= 0.55
    assert report["summary"]["gold_evolving_projection_live_ready"] is False
    assert report["summary"]["gold_evolving_projection_blocker_count"] >= 1
    assert {item["id"] for item in report["gold_evolving_projection_path"]["horizons"]} >= {"1s", "5s", "15s", "30s", "tick", "1m", "5m", "15m", "1h", "4h", "session", "1d", "1w", "1mo", "3mo"}
    assert any(item["id"] == "1s" and item["validation_state"] == "missing_projection" for item in report["gold_evolving_projection_path"]["horizons"])
    assert any(item["id"] == "3mo" for item in report["gold_evolving_projection_path"]["horizons"])
    assert report["summary"]["gold_dynamic_market_edge_stream_status"] == "gold_dynamic_market_edge_stream_attention"
    assert report["summary"]["gold_dynamic_market_edge_state"] == "gold_dynamic_market_edge_watch_refreshing"
    assert report["summary"]["gold_dynamic_market_edge_stream_lane_count"] == 8
    assert report["summary"]["gold_dynamic_market_edge_fresh_stream_count"] >= 1
    assert report["summary"]["gold_dynamic_market_edge_score"] >= 0
    assert report["summary"]["gold_dynamic_market_edge_shadow_intent_allowed"] is False
    assert report["summary"]["gold_dynamic_market_edge_blocker_count"] >= 1
    assert report["gold_dynamic_market_edge_stream"]["action_candidate"]["candidate"] == "GOLD"
    assert report["gold_dynamic_market_edge_stream"]["action_candidate"]["live_order_allowed"] is False
    assert report["gold_dynamic_market_edge_stream"]["action_candidate"]["margin_order_allowed"] is False
    assert any(row["id"] == "capital_gold_xau" and row["edge_use"] == "target_trigger" for row in report["gold_dynamic_market_edge_stream"]["stream_rows"])
    assert any(blocker["id"] == "evolving_projection_path_blocking" for blocker in report["gold_dynamic_market_edge_stream"]["blockers"])
    assert report["summary"]["gold_hnc_history_future_bridge_status"] == "gold_hnc_history_future_bridge_attention"
    assert report["summary"]["gold_hnc_history_future_bridge_ready"] is False
    assert report["summary"]["gold_hnc_history_future_memory_score"] >= 0
    assert report["summary"]["gold_hnc_history_future_validated_count"] >= 4
    assert report["summary"]["gold_hnc_history_future_hit_rate"] >= 0.55
    assert report["summary"]["gold_hnc_history_future_window_count"] >= 15
    assert report["summary"]["gold_hnc_history_future_claim_state"] == "history_informs_but_does_not_unlock_action"
    assert report["summary"]["gold_hnc_history_future_blocker_count"] >= 1
    assert report["gold_hnc_history_future_bridge"]["live_order_allowed"] is False
    assert report["gold_hnc_history_future_bridge"]["margin_order_allowed"] is False
    assert any(item["id"] == "historical_waveform_replay" for item in report["gold_hnc_history_future_bridge"]["historical_analogs"])
    assert any(item["id"] == "1s" for item in report["gold_hnc_history_future_bridge"]["future_windows"])
    assert report["summary"]["gold_creative_dream_count"] >= 12
    assert report["summary"]["gold_creative_dream_ready_count"] >= 0
    assert report["summary"]["gold_creative_average_score"] > 0
    assert report["summary"]["gold_creative_average_evidence_score"] >= 0
    assert report["summary"]["gold_creative_action_influence_allowed"] is False
    assert report["gold_creative_dream_hypothesis_engine"]["live_order_allowed"] is False
    assert report["gold_creative_dream_hypothesis_engine"]["margin_order_allowed"] is False
    assert report["gold_creative_dream_hypothesis_engine"]["order_mutation_allowed"] is False
    assert any(dream["id"] == "waveform_stretch_reversal" for dream in report["gold_creative_dream_hypothesis_engine"]["dreams"])
    assert any(item["dream_id"] == "gold_liquidity_snap" for item in report["gold_creative_dream_hypothesis_engine"]["validation_queue"])
    assert report["summary"]["gold_probability_projection_forecast_status"] == "gold_probability_projection_forecast_blocking"
    assert report["summary"]["gold_probability_forecast_truth_claim_allowed"] is False
    assert report["summary"]["gold_probability_forecast_truth_status"] == "hypothesis_until_validated"
    assert report["summary"]["gold_probability_forecast_direction"] in {"BUY", "SELL", "HOLD"}
    assert report["summary"]["gold_probability_forecast_calibrated_confidence"] >= 0
    assert report["summary"]["gold_probability_forecast_validated_claim_count"] >= 6
    assert report["summary"]["gold_probability_forecast_hit_rate"] >= 0.55
    assert report["summary"]["gold_probability_forecast_contradiction_count"] >= 1
    assert report["summary"]["gold_probability_forecast_blocker_count"] >= 1
    assert report["summary"]["gold_probability_forecast_action_influence_allowed"] is False
    assert report["gold_probability_projection_forecast"]["truth_discipline"]["no_fake_certainty"] is True
    assert report["gold_probability_projection_forecast"]["validated_forecast"]["action_influence_allowed"] is False
    assert any(claim["truth_status"] == "validated_outcome_hit" for claim in report["gold_probability_projection_forecast"]["forecast_claims"])
    assert any(claim["truth_status"] == "validated_outcome_miss" for claim in report["gold_probability_projection_forecast"]["forecast_claims"])
    assert any(item["id"] == "validated_interval_contradictions_present" for item in report["gold_probability_projection_forecast"]["blockers"])
    assert report["summary"]["gold_hnc_action_coherence_status"] == "gold_hnc_action_coherence_gate_blocking"
    assert report["summary"]["gold_hnc_action_coherence_allowed"] is False
    assert report["summary"]["gold_portfolio_uplift_status"] == "gold_portfolio_uplift_guard_blocking"
    assert report["summary"]["gold_portfolio_uplift_order_intent_allowed"] is False
    assert any(lane["id"] == "capital_gold_xau" and lane["role"] == "target_action_lane" for lane in report["gold_ticker_source_mesh"]["lanes"])
    assert {item["id"] for item in report["gold_projection_interval_validation"]["intervals"]} == {"tick", "1m", "5m", "15m", "1h", "session"}
    assert any(blocker["id"] == "fresh_signal_matrix_blocking" for blocker in report["gold_projection_interval_validation"]["blockers"])
    assert any(blocker["id"] == "projection_intervals_not_validated" for blocker in report["gold_portfolio_uplift_guard"]["blockers"])
    assert report["summary"]["gold_action_command_status"] == "gold_action_command_attention"
    assert report["summary"]["gold_action_state"] == "hold_gather_replay"
    assert report["summary"]["gold_action_blocking_count"] >= 1
    assert report["summary"]["gold_command_system_count"] >= 5
    assert report["summary"]["gold_shadow_focus_status"] == "gold_energy_shadow_focus_blocked_for_fresh_data"
    assert report["summary"]["gold_shadow_focus_candidate_count"] >= 1
    assert report["summary"]["gold_shadow_focus_context_count"] >= 1
    assert report["summary"]["gold_shadow_focus_energy_lane_count"] >= 8
    assert report["summary"]["gold_shadow_focus_excluded_shadow_count"] >= 1
    assert report["summary"]["gold_shadow_focus_promotion_state"] == "held_until_verified_real_data"
    assert report["gold_shadow_trading_focus"]["mode"] == "gold_and_gold_energy_only_shadow_validation"
    assert report["gold_shadow_trading_focus"]["target_symbol"] == "GOLD"
    assert report["gold_shadow_trading_focus"]["promotion_gate"]["live_order_allowed"] is False
    assert report["gold_shadow_trading_focus"]["promotion_gate"]["order_mutation_allowed"] is False
    assert report["summary"]["gold_live_stream_command_deck_status"] == "gold_live_stream_command_deck_attention"
    assert report["summary"]["gold_live_stream_channel_count"] >= 6
    assert report["summary"]["gold_live_chart_stream_count"] >= 4
    assert report["summary"]["gold_live_deck_targeting_state"] in {
        "refresh_gold_ticker_source_mesh",
        "validate_gold_projection_intervals",
        "feed_fresh_proof_back_to_hnc",
        "prove_portfolio_uplift_and_3p_floor",
        "shadow_validate_capital_gold_candidate",
    }
    assert report["summary"]["capital_gold_leverage_estimate"] == 1.0
    assert report["summary"]["capital_gold_margin_factor_pct"] == 100.0
    assert report["summary"]["capital_gold_margin_required_for_min_deal"] == 45.5966
    assert report["gold_live_stream_command_deck"]["target"]["symbol"] == "GOLD"
    assert report["gold_live_stream_command_deck"]["what_will_i_act_on"]["live_order_allowed"] is False
    assert report["gold_live_stream_command_deck"]["what_will_i_act_on"]["order_mutation_allowed"] is False
    assert report["gold_live_stream_command_deck"]["leverage_margin_status"]["margin_order_allowed"] is False
    assert report["gold_live_stream_command_deck"]["leverage_margin_status"]["leverage_change_allowed"] is False
    assert any(channel["id"] == "capital_gold_profile" for channel in report["gold_live_stream_command_deck"]["stream_channels"])
    assert any(chart["id"] == "capital_price_band" for chart in report["gold_live_stream_command_deck"]["chart_streams"])
    assert report["gold_live_stream_command_deck"]["hnc_feedback_loop"]["act"] in {"feed_hnc_blockers", "feed_hnc_shadow_ready_state"}
    assert report["summary"]["gold_margin_signal_action_loop_status"] == "gold_margin_signal_action_loop_blocking"
    assert report["summary"]["gold_margin_signal_pipeline_stage_count"] >= 7
    assert report["summary"]["gold_margin_signal_ready_stage_count"] < report["summary"]["gold_margin_signal_pipeline_stage_count"]
    assert report["summary"]["gold_margin_signal_shadow_intent_allowed"] is False
    assert report["summary"]["gold_margin_signal_live_order_allowed"] is False
    assert report["summary"]["gold_margin_signal_margin_order_allowed"] is False
    assert report["summary"]["gold_margin_signal_blocker_count"] >= 1
    assert report["gold_margin_signal_action_loop"]["margin_intent"]["target_symbol"] == "GOLD"
    assert report["gold_margin_signal_action_loop"]["margin_intent"]["target_venue"] == "Capital.com"
    assert report["gold_margin_signal_action_loop"]["margin_intent"]["margin_order_allowed"] is False
    assert report["gold_margin_signal_action_loop"]["action_authority"]["live_order_allowed"] is False
    assert report["gold_margin_signal_action_loop"]["action_authority"]["leverage_change_allowed"] is False
    assert any(stage["id"] == "hnc_auris_nodes" for stage in report["gold_margin_signal_action_loop"]["signal_to_action_pipeline"])
    assert report["gold_margin_signal_action_loop"]["hnc_auris_node_feedback"]["feedback_action"] in {"feed_blockers_to_hnc", "feed_shadow_intent_to_hnc"}
    assert report["summary"]["gold_process_logic_flow_guard_status"] == "gold_process_logic_flow_guard_passing"
    assert report["summary"]["gold_process_flow_state"] == "flow_correct_action_held"
    assert report["summary"]["gold_process_flow_correct"] is True
    assert report["summary"]["gold_process_flow_all_gates_ready"] is False
    assert report["summary"]["gold_process_flow_ready_gate_count"] < report["summary"]["gold_process_flow_gate_count"]
    assert report["summary"]["gold_process_flow_fake_pass_count"] == 0
    assert report["summary"]["gold_process_flow_first_blocked_gate"] == "verified_real_data_gate"
    assert report["gold_process_logic_flow_guard"]["first_blocked_gate"]["id"] == "verified_real_data_gate"
    assert report["gold_process_logic_flow_guard"]["violations"] == []
    assert any(gate["id"] == "dynamic_market_edge_stream" for gate in report["gold_process_logic_flow_guard"]["gate_sequence"])
    assert any(gate["id"] == "hnc_history_future_bridge" for gate in report["gold_process_logic_flow_guard"]["gate_sequence"])
    assert any(gate["id"] == "creative_dream_hypothesis_engine" for gate in report["gold_process_logic_flow_guard"]["gate_sequence"])
    assert any(gate["id"] == "probability_projection_forecast" for gate in report["gold_process_logic_flow_guard"]["gate_sequence"])
    assert all(check["allowed"] is False for check in report["gold_process_logic_flow_guard"]["action_authority_checks"])
    assert report["summary"]["gold_data_sensemaking_router_status"] == "gold_data_sensemaking_router_attention"
    assert report["summary"]["gold_data_sensemaking_state"] == "read_classified_routed_with_blockers"
    assert report["summary"]["gold_data_present_source_count"] == report["summary"]["gold_data_source_count"]
    assert report["summary"]["gold_data_routed_source_count"] == report["summary"]["gold_data_source_count"]
    assert report["summary"]["gold_data_destination_count"] >= 8
    assert report["summary"]["gold_data_sensemaking_blocker_count"] >= 1
    assert any(route["id"] == "capital_asset_registry" and "gold_ticker_source_mesh" in route["destinations"] for route in report["gold_data_sensemaking_router"]["source_routes"])
    assert any(route["id"] == "runtime_status" and "gold_process_logic_flow_guard" in route["destinations"] for route in report["gold_data_sensemaking_router"]["source_routes"])
    assert any(packet["id"] == "probability_projection_forecast" for packet in report["gold_data_sensemaking_router"]["meaning_packets"])
    assert any(packet["id"] == "evolving_projection_path" for packet in report["gold_data_sensemaking_router"]["meaning_packets"])
    assert any(packet["id"] == "dynamic_market_edge_stream" for packet in report["gold_data_sensemaking_router"]["meaning_packets"])
    assert any(packet["id"] == "hnc_history_future_bridge" for packet in report["gold_data_sensemaking_router"]["meaning_packets"])
    assert any(packet["id"] == "creative_dream_hypothesis_engine" for packet in report["gold_data_sensemaking_router"]["meaning_packets"])
    assert any(driver["destination"] in {"gold_probability_projection_forecast", "contradiction_matrix"} for driver in report["gold_data_sensemaking_router"]["driver_routes"])
    assert any(lane["id"] == "oil_energy_inflation" for lane in report["gold_shadow_trading_focus"]["energy_context_lanes"])
    assert any(item["symbol"] == "GOLD" for item in report["gold_shadow_trading_focus"]["shadow_candidates"])
    assert any(item["symbol"] == "RANDOMABC" for item in report["gold_shadow_trading_focus"]["excluded_shadow_items"])
    assert report["summary"]["hnc_auris_quantum_probability_route_status"] == "hnc_auris_quantum_probability_route_passing"
    assert report["summary"]["hnc_auris_quantum_probability_route_passed"] is True
    assert report["summary"]["auris_node_count"] == 9
    assert report["summary"]["lambda_history_fresh"] is True
    assert report["summary"]["quantum_route_present_surface_count"] == report["summary"]["quantum_route_surface_count"]
    assert report["summary"]["probability_route_present_surface_count"] == report["summary"]["probability_route_surface_count"]
    assert report["summary"]["gold_probability_row_count"] >= 2
    assert report["hnc_auris_quantum_probability_route"]["route_passed"] is True
    assert report["hnc_auris_quantum_probability_route"]["auris_nodes"]["passed"] is True
    assert report["hnc_auris_quantum_probability_route"]["lambda_system"]["fresh"] is True
    assert report["hnc_auris_quantum_probability_route"]["probability_systems"]["gold_row_count"] >= 2
    assert any(item["id"] == "hnc_auris_quantum_probability_route" for item in report["gold_action_command"]["proof_chain"])
    assert report["summary"]["hft_speed_prediction_gate_status"] == "hft_speed_prediction_gate_blocking"
    assert report["summary"]["hft_speed_prediction_gate_passed"] is False
    assert report["summary"]["hft_fresh_gold_prediction_count"] >= 2
    assert report["summary"]["hft_validated_gold_prediction_count"] >= 1
    assert report["summary"]["hft_validated_correct_gold_prediction_count"] >= 1
    assert report["summary"]["hft_prediction_blocker_count"] >= 1
    assert report["hft_speed_prediction_gate"]["prediction_validation"]["validated_correct_gold_prediction_count"] >= 1
    assert report["hft_speed_prediction_gate"]["live_order_allowed"] is False
    assert any(item["id"] == "hft_speed_validated_predictions" for item in report["gold_action_command"]["proof_chain"])
    assert report["summary"]["gold_historical_stress_status"] == "gold_historical_stress_passed"
    assert report["summary"]["gold_historical_stress_passed"] is True
    assert report["summary"]["gold_historical_stress_prediction_count"] >= 4
    assert report["summary"]["gold_historical_stress_validated_count"] >= 4
    assert report["summary"]["gold_historical_stress_hit_rate"] >= 0.55
    assert report["summary"]["gold_historical_stress_present_surface_count"] == report["summary"]["gold_historical_stress_surface_count"]
    assert report["summary"]["gold_historical_stress_blocker_count"] == 0
    assert report["gold_historical_stress_test"]["live_order_allowed"] is False
    assert report["gold_historical_stress_test"]["order_mutation_allowed"] is False
    assert any(scenario["id"] == "validated_hit_rate" and scenario["state"] == "passed" for scenario in report["gold_historical_stress_test"]["scenarios"])
    assert any(item["id"] == "gold_historical_stress_test" for item in report["gold_action_command"]["proof_chain"])
    assert report["gold_action_command"]["who"]["commander"] == "Gold Strategy Steward"
    assert report["gold_action_command"]["what"]["mission"].startswith("Answer one question")
    assert report["gold_action_command"]["act"]["live_order_allowed"] is False
    assert any(item["id"] == "three_p_floor" for item in report["gold_action_command"]["proof_chain"])
    assert any(item["id"] == "gold_margin_trader_unity" for item in report["gold_action_command"]["proof_chain"])
    assert any(item["id"] == "fresh_interval_validated_gold_projection" for item in report["gold_action_command"]["proof_chain"])
    assert any(item["id"] == "dynamic_gold_market_edge_stream" for item in report["gold_action_command"]["proof_chain"])
    assert any(item["id"] == "gold_hnc_history_future_bridge" for item in report["gold_action_command"]["proof_chain"])
    assert any(item["id"] == "gold_creative_dream_hypothesis_engine" for item in report["gold_action_command"]["proof_chain"])
    assert any(item["id"] == "gold_probability_projection_forecast" for item in report["gold_action_command"]["proof_chain"])
    assert any(item["id"] == "gold_portfolio_uplift_guard" for item in report["gold_action_command"]["proof_chain"])
    assert any(system["id"] == "war_strategy" for system in report["gold_action_command"]["command_systems"])
    assert report["summary"]["gold_agent_coding_support_status"] == "gold_agent_coding_support_ready"
    assert report["summary"]["gold_agent_support_ready"] is True
    assert report["summary"]["gold_agent_chat_lane_count"] >= 2
    assert report["summary"]["gold_agent_tool_lane_count"] >= 3
    assert report["summary"]["gold_agent_monitor_target_count"] >= 4
    assert report["summary"]["gold_agent_support_present_surface_count"] == report["summary"]["gold_agent_support_surface_count"]
    assert report["summary"]["gold_agent_support_present_artifact_count"] == report["summary"]["gold_agent_support_artifact_count"]
    assert report["summary"]["gold_agent_support_blocker_count"] == 0
    assert any(lane["id"] == "coding_organism_jobs" for lane in report["gold_agent_coding_support"]["tool_lanes"])
    assert any(lane["id"] == "phi_operator_chat" for lane in report["gold_agent_coding_support"]["chat_lanes"])
    assert any(target["id"] == "gold_historical_stress_test" for target in report["gold_agent_coding_support"]["monitor_targets"])
    assert report["gold_priority_workbench"]["priority_focus"] == "Capital GOLD"
    assert len(report["gold_priority_workbench"]["forecast_points"]) >= 6
    assert any(item["id"] == "draw_gold_forecast_dashboard" for item in report["gold_priority_workbench"]["data_priority_queue"])
    assert report["gold_priority_workbench"]["artifact_manifest"]["html_url"].endswith("gold_priority_forecast.html")
    assert report["swarm_intelligence"]["data_gathering_contract"]["no_reinvention"] is True
    assert report["swarm_intelligence"]["sensemaking_contract"]["no_single_agent_final_authority"] is True
    assert report["historical_signal_lab"]["status"] in {
        "gold_historical_signal_lab_ready",
        "gold_historical_signal_lab_attention",
    }
    assert any(lane["id"] == "gold_ohlc_replay" for lane in report["historical_signal_lab"]["replay_lanes"])
    assert any(lane["id"] == "cross_asset_lead_lag" for lane in report["historical_signal_lab"]["replay_lanes"])
    assert any(lane["id"] == "orderbook_pressure_replay" for lane in report["historical_signal_lab"]["replay_lanes"])
    assert any(candidate["follower"] == "GOLD" for candidate in report["historical_signal_lab"]["lead_lag_candidates"])
    assert report["historical_signal_lab"]["orderbook_evidence"]["gold_sample_count"] == 1
    assert any(test["id"] == "gold_waveform_regime_replay_test" for test in report["historical_signal_lab"]["hypothesis_tests"])
    assert any(agent["id"] == "crypto_rotation_reader" for agent in report["swarm_intelligence"]["agents"])
    assert any(agent["id"] == "geopolitical_sentiment_reader" for agent in report["swarm_intelligence"]["agents"])
    assert any(driver["id"] == "crypto_liquidity_safe_haven" for driver in report["cross_market_driver_matrix"])
    assert any(driver["id"] == "gold_etfs_miners" for driver in report["cross_market_driver_matrix"])
    assert any(driver["id"] == "geopolitical_news_sentiment" for driver in report["cross_market_driver_matrix"])
    assert report["gold_market_universe"]["trade_ready_count"] == 1
    assert any(surface["id"] == "universal_forecast" for surface in report["gold_intelligence_map"])
    assert any(packet["id"] == "hnc_gold_verification_audit" for packet in report["local_research_packets"])
    assert any(action["id"] == "run_gold_forecast_fusion" for action in report["tool_activation_plan"])
    assert any(action["id"] == "run_dynamic_gold_edge_stream" for action in report["tool_activation_plan"])
    assert any(action["id"] == "compile_hnc_history_future_bridge" for action in report["tool_activation_plan"])
    assert any(action["id"] == "generate_gold_creative_dream_hypotheses" for action in report["tool_activation_plan"])
    assert any(packet["source_url"] == "https://open-api.capital.com/" for packet in report["source_packets"])
    assert (tmp_path / "frontend" / "public" / "aureon_gold_capital_intelligence_company.json").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_gold_intelligence" / "gold_priority_forecast.svg").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_gold_intelligence" / "gold_priority_forecast.html").exists()
    assert (tmp_path / "docs" / "audits" / "aureon_gold_capital_intelligence_company.md").exists()


def test_gold_capital_company_blocks_when_gold_asset_missing(tmp_path: Path) -> None:
    _fixture_repo(tmp_path, include_gold=False)

    report = build_and_write_gold_capital_intelligence_company(root=tmp_path)

    assert report["ok"] is False
    assert report["status"] == "gold_capital_intelligence_blocked_missing_gold_asset"
    assert any(blocker["id"] == "capital_gold_asset_missing" for blocker in report["blockers"])
