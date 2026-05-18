from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aureon.autonomous.aureon_capital_ecosystem_intelligence_company import score_capital_candidate
from aureon.autonomous.aureon_capital_revenue_logic_stress_audit import (
    build_and_write_capital_revenue_logic_stress_audit,
    build_capital_revenue_logic_stress_audit,
)


NOW = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _asset(symbol: str) -> dict:
    return {
        "symbol": symbol,
        "epic": symbol,
        "instrument_name": symbol,
        "asset_class": "index_cfd",
        "market_status": "TRADEABLE",
        "trade_ready": True,
        "can_buy": True,
        "can_sell": True,
        "bid": 100.0,
        "ask": 100.1,
        "mid_price": 100.05,
        "spread": 0.1,
        "spread_pct": 0.003,
        "minimum_deal_size": 0.01,
        "margin_required_for_min_deal": 20.0,
        "last_snapshot_at": NOW.isoformat(),
    }


def _candidate(symbol: str, momentum: float) -> dict:
    return score_capital_candidate(_asset(symbol), now=NOW, stream_momentum={symbol.upper(): momentum})


def _ecosystem(candidates: list[dict], *, hedge_leak: bool = False) -> dict:
    hedges = [
        {
            "hedge_candidate_id": "hedge-1",
            "source_exchange": "binance",
            "target_candidate_id": candidates[0]["candidate_id"],
            "target_symbol": candidates[0]["symbol"],
            "hedge_side": "SELL",
            "authority": "shadow_only" if not hedge_leak else "live_order",
            "mutation_allowed": hedge_leak,
            "order_intent_allowed": hedge_leak,
        }
    ]
    return {
        "generated_at": NOW.isoformat(),
        "status": "capital_ecosystem_intelligence_ready",
        "summary": {
            "candidate_count": len(candidates),
            "trade_ready_candidate_count": len(candidates),
            "active_watchlist_count": len(candidates),
            "active_watchlist_limit": 40,
            "bench_watchlist_count": len(candidates),
            "bench_watchlist_limit": 100,
            "shadow_hedge_count": len(hedges),
            "shadow_hedges_only": not hedge_leak,
            "close_first_opportunity_count": 0,
            "active_lifecycle_route_count": 0,
            "no_external_hedge_mutation": not hedge_leak,
            "existing_runtime_gates_authoritative": True,
        },
        "watchlists": {
            "active_stream_watchlist": candidates,
            "bench_watchlist": candidates,
        },
        "top_velocity_candidates": candidates,
        "shadow_hedges": hedges,
        "close_first_opportunities": [],
        "lifecycle": {"duplicate_route_blocked_count": 0, "active_route_keys": []},
        "blockers": [],
    }


def _live_dry(*, certified: bool = True) -> dict:
    return {
        "generated_at": NOW.isoformat(),
        "status": "live_dry_certified" if certified else "recovered_position_certified_attention",
        "summary": {
            "runtime_fresh": True,
            "active_watchlist_count": 1,
            "bench_watchlist_count": 1,
            "candidate_count": 1,
            "active_lifecycle_route_count": 0,
            "duplicate_routes_blocked": True,
            "duplicate_route_blocked_count": 0,
            "close_first_opportunity_count": 0,
            "shadow_hedge_count": 1,
            "shadow_hedges_only": True,
            "broker_correlation_complete": True,
            "lifecycle_continuity_complete": certified,
            "recovered_position_count": 0 if certified else 1,
            "recovered_position_close_first_covered": True,
            "recovered_close_chain_status": "not_applicable" if certified else "recovered_exit_ready_attention",
            "no_live_mutation": True,
        },
        "blockers": [] if certified else ["recovered_upstream_context_missing", "recovered_exit_ready_attention"],
    }


def _runtime(*, clear: bool = True) -> dict:
    if clear:
        return {
            "generated_at": NOW.isoformat(),
            "executor_enabled": True,
            "exchange_mutations_disabled": False,
            "live_trading_enabled": True,
            "real_orders_disabled": False,
            "real_orders_allowed_by_runtime": True,
            "order_intent_publish_disabled": False,
            "runtime_clearances": [],
        }
    return {
        "generated_at": NOW.isoformat(),
        "executor_enabled": False,
        "exchange_mutations_disabled": True,
        "live_trading_enabled": False,
        "real_orders_disabled": True,
        "real_orders_allowed_by_runtime": False,
        "order_intent_publish_disabled": True,
        "runtime_clearances": [
            "exchange_mutations_disabled",
            "live_trading_not_enabled",
            "real_orders_disabled",
            "real_orders_not_allowed_by_runtime",
            "unified_order_executor_disabled",
            "order_intent_publish_disabled",
        ],
    }


def _write_fixture(tmp_path: Path, *, candidates: list[dict], live_dry_certified: bool = True, runtime_clear: bool = True, hedge_leak: bool = False) -> None:
    _write_json(tmp_path / "frontend/public/aureon_capital_ecosystem_intelligence_company.json", _ecosystem(candidates, hedge_leak=hedge_leak))
    _write_json(tmp_path / "frontend/public/aureon_capital_ecosystem_live_dry_stress_audit.json", _live_dry(certified=live_dry_certified))
    _write_json(tmp_path / "state/unified_runtime_status.json", _runtime(clear=runtime_clear))
    _write_json(tmp_path / "frontend/public/aureon_exchange_data_capability_matrix.json", {"rows": []})


def test_revenue_logic_certifies_clean_net_positive_candidate(tmp_path: Path) -> None:
    _write_fixture(tmp_path, candidates=[_candidate("US100", 5.0)])

    report = build_capital_revenue_logic_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "capital_revenue_logic_certified"
    assert report["summary"]["net_positive_candidate_count"] == 1
    assert report["summary"]["intent_eligible_candidate_count"] == 1
    assert report["summary"]["false_positive_reject_count"] == 0
    assert report["summary"]["external_shadow_only"] is True
    assert report["summary"]["no_live_mutation"] is True


def test_revenue_logic_rejects_gross_positive_false_positive(tmp_path: Path) -> None:
    _write_fixture(tmp_path, candidates=[_candidate("US30", 2.0)])

    report = build_capital_revenue_logic_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "no_net_positive_candidates"
    assert report["summary"]["net_positive_candidate_count"] == 0
    assert report["summary"]["false_positive_reject_count"] == 1
    assert "expected_net_revenue_not_positive" in report["rejected_false_positives"][0]["revenue_blockers"]


def test_revenue_logic_keeps_net_positive_candidate_gated_when_runtime_blocks(tmp_path: Path) -> None:
    _write_fixture(tmp_path, candidates=[_candidate("US100", 5.0)], live_dry_certified=False, runtime_clear=False)

    report = build_capital_revenue_logic_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "capital_order_intent_gated"
    assert report["summary"]["net_positive_candidate_count"] == 1
    assert report["summary"]["candidate_level_intent_eligible_count"] == 1
    assert report["summary"]["intent_eligible_candidate_count"] == 0
    assert report["summary"]["live_gates_blocking"] is True
    assert "exchange_mutations_disabled" in report["capital_order_intent_readiness"]["runtime_gate_blockers"]


def test_revenue_logic_blocks_external_shadow_mutation_leak(tmp_path: Path) -> None:
    _write_fixture(tmp_path, candidates=[_candidate("US100", 5.0)], hedge_leak=True)

    report = build_capital_revenue_logic_stress_audit(root=tmp_path, now=NOW)

    assert report["status"] == "external_shadow_mutation_leak"
    assert report["summary"]["external_shadow_only"] is False
    assert "external_shadow_mutation_leak" in report["blockers"]


def test_revenue_logic_writes_public_artifacts(tmp_path: Path) -> None:
    _write_fixture(tmp_path, candidates=[_candidate("US100", 5.0)])

    report = build_and_write_capital_revenue_logic_stress_audit(root=tmp_path)
    public_path = tmp_path / "frontend/public/aureon_capital_revenue_logic_stress_audit.json"

    assert report["schema_version"] == "aureon-capital-revenue-logic-stress-audit-v1"
    assert public_path.exists()
