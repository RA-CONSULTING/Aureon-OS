from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aureon.autonomous.aureon_capital_ecosystem_intelligence_company import (
    ACTIVE_WATCHLIST_LIMIT,
    allocate_watchlists,
    build_and_write_capital_ecosystem_intelligence_company,
    build_capital_ecosystem_intelligence_company,
    build_shadow_hedges,
    score_capital_candidate,
)
from aureon.trading.order_lifecycle import append_event, lifecycle_id_for, route_key_for


NOW = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _asset(symbol: str, *, spread_pct: float, margin: float = 25.0, asset_class: str = "index_cfd") -> dict:
    return {
        "symbol": symbol,
        "epic": symbol,
        "instrument_name": symbol,
        "asset_class": asset_class,
        "market_status": "TRADEABLE",
        "trade_ready": True,
        "can_buy": True,
        "can_sell": True,
        "bid": 100.0,
        "ask": 100.1,
        "mid_price": 100.05,
        "spread": 0.1,
        "spread_pct": spread_pct,
        "minimum_deal_size": 0.01,
        "margin_required_for_min_deal": margin,
        "last_snapshot_at": NOW.isoformat(),
    }


def _exchange_matrix() -> dict:
    return {
        "rows": [
            {"exchange": "binance", "current_state": {"fresh_feed": True, "decision_fed": True}},
            {"exchange": "kraken", "current_state": {"fresh_feed": True, "decision_fed": False}},
            {"exchange": "alpaca", "current_state": {"fresh_feed": True, "decision_fed": True}},
            {"exchange": "capital", "current_state": {"fresh_feed": True, "decision_fed": True}},
        ]
    }


def test_capital_candidate_scoring_prefers_fast_profit_velocity_and_blocks_bad_inputs():
    fast = score_capital_candidate(_asset("US100", spread_pct=0.003, margin=20.0), now=NOW, stream_momentum={"US100": 5.0})
    slow = score_capital_candidate(_asset("WIDE", spread_pct=0.2, margin=220.0), now=NOW)
    blocked_asset = _asset("CLOSED", spread_pct=0.003)
    blocked_asset["market_status"] = "CLOSED"
    blocked = score_capital_candidate(blocked_asset, now=NOW)

    assert fast["fast_profit_velocity_score"] > slow["fast_profit_velocity_score"]
    assert blocked["fast_profit_velocity_score"] == 0.0
    assert fast["trade_ready"] is True
    assert fast["gross_edge"] > 0
    assert fast["net_revenue_positive"] is True
    assert fast["revenue_intent_eligible"] is True
    assert "capital_market_not_tradeable" in blocked["blockers"]
    assert blocked["order_intent_allowed"] is False


def test_capital_candidate_revenue_logic_rejects_gross_positive_net_negative():
    row = score_capital_candidate(_asset("US30", spread_pct=0.003, margin=25.0), now=NOW, stream_momentum={"US30": 2.0})

    assert row["gross_edge"] > 0
    assert row["expected_net_revenue"] < 0
    assert row["net_revenue_positive"] is False
    assert row["revenue_intent_eligible"] is False
    assert "expected_net_revenue_not_positive" in row["revenue_blockers"]


def test_watchlist_allocator_preserves_gold_and_respects_capital_stream_limit():
    candidates = [
        {"candidate_id": f"c-{idx}", "symbol": f"SYM{idx}", "fast_profit_velocity_score": 1.0 - (idx * 0.001)}
        for idx in range(60)
    ]
    candidates.append({"candidate_id": "gold", "symbol": "GOLD", "fast_profit_velocity_score": 0.01})

    watchlists = allocate_watchlists(candidates)

    assert len(watchlists["active_stream_watchlist"]) == ACTIVE_WATCHLIST_LIMIT
    assert any(row["symbol"] == "GOLD" for row in watchlists["active_stream_watchlist"])
    assert len(watchlists["bench_watchlist"]) <= 100


def test_capital_ecosystem_blocks_duplicate_active_lifecycle_route(tmp_path: Path):
    route = route_key_for("capital", "cfd", "US100", "BUY")
    append_event(
        root=tmp_path,
        event_type="position_recovered",
        status="position_open",
        lifecycle_id=lifecycle_id_for("capital", "US100", "open"),
        route_key=route,
        venue="capital",
        market_type="cfd",
        symbol="US100",
        side="BUY",
    )
    _write_json(tmp_path / "state/aureon_capital_tradable_asset_registry.json", {"assets": [_asset("US100", spread_pct=0.003)]})
    _write_json(tmp_path / "frontend/public/aureon_exchange_data_capability_matrix.json", _exchange_matrix())
    _write_json(tmp_path / "ws_cache/ws_prices.json", {"ticker_cache": {}})

    report = build_capital_ecosystem_intelligence_company(root=tmp_path, now=NOW)
    candidate = report["top_velocity_candidates"][0]

    assert candidate["route_key"] == route
    assert candidate["lifecycle_duplicate_blocked"] is True
    assert "active_lifecycle_same_route" in candidate["blockers"]
    assert candidate["revenue_intent_eligible"] is False
    assert report["lifecycle"]["duplicate_route_blocked_count"] == 1


def test_shadow_hedges_are_shadow_only_and_never_order_intents():
    candidates = [
        score_capital_candidate(_asset("US100", spread_pct=0.003, asset_class="index_cfd"), now=NOW),
        score_capital_candidate(_asset("AAPL", spread_pct=0.004, asset_class="stock_cfd"), now=NOW),
    ]

    hedges = build_shadow_hedges(candidates, _exchange_matrix())

    assert hedges
    assert all(row["authority"] == "shadow_only" for row in hedges)
    assert all(row["mutation_allowed"] is False for row in hedges)
    assert all(row["order_intent_allowed"] is False for row in hedges)
    assert all("external_hedge_order_mutation_blocked" in row["hedge_blockers"] for row in hedges)


def test_capital_ecosystem_report_writes_public_artifacts(tmp_path: Path):
    _write_json(
        tmp_path / "state/aureon_capital_tradable_asset_registry.json",
        {"assets": [_asset("GOLD", spread_pct=0.01, asset_class="commodity_cfd"), _asset("US100", spread_pct=0.003)]},
    )
    _write_json(tmp_path / "frontend/public/aureon_exchange_data_capability_matrix.json", _exchange_matrix())
    _write_json(tmp_path / "ws_cache/ws_prices.json", {"ticker_cache": {}})

    report = build_and_write_capital_ecosystem_intelligence_company(root=tmp_path)
    public_path = tmp_path / "frontend/public/aureon_capital_ecosystem_intelligence_company.json"

    assert report["status"] == "capital_ecosystem_intelligence_ready"
    assert report["summary"]["active_watchlist_count"] <= ACTIVE_WATCHLIST_LIMIT
    assert report["summary"]["gold_preserved"] is True
    assert report["summary"]["shadow_hedges_only"] is True
    assert public_path.exists()
