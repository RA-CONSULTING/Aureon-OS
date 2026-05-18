from __future__ import annotations

import json

from aureon.trading import order_lifecycle as lifecycle


def test_order_lifecycle_valid_transition_chain(tmp_path):
    lifecycle_id = lifecycle.lifecycle_id_for("test", "gold", "buy")
    route_key = lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")
    common = {
        "root": tmp_path,
        "lifecycle_id": lifecycle_id,
        "candidate_id": "candidate-1",
        "intent_id": "intent-1",
        "route_key": route_key,
        "venue": "capital",
        "market_type": "cfd",
        "symbol": "GOLD",
        "side": "BUY",
    }
    for status in (
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
    ):
        lifecycle.append_event(event_type=status, status=status, **common)

    state = lifecycle.load_state(tmp_path)
    row = state["lifecycles"][0]

    assert row["continuity_complete"] is True
    assert row["missing_links"] == []
    assert row["current_status"] == "outcome_recorded"
    assert state["continuity_blockers"] == []
    assert (tmp_path / "state" / "unified_order_lifecycle_events.jsonl").exists()
    assert (tmp_path / "frontend" / "public" / "aureon_unified_order_lifecycle.json").exists()


def test_order_lifecycle_transition_and_broker_status_mapping():
    assert lifecycle.transition_allowed("candidate_ready", "intent_published") is True
    assert lifecycle.transition_allowed("candidate_ready", "position_closed") is False
    assert lifecycle.transition_allowed("position_closed", "outcome_recorded") is True
    assert lifecycle.transition_allowed("order_rejected", "position_open") is False

    assert lifecycle.normalize_broker_status("alpaca", "partially_filled")["lifecycle_status"] == "partial_fill"
    assert lifecycle.normalize_broker_status("binance", "FILLED")["lifecycle_status"] == "position_open"
    assert lifecycle.normalize_broker_status("binance", "timeout")["lifecycle_status"] == "submit_timeout_unverified"
    assert lifecycle.normalize_broker_status("binance", "rate_limit")["lifecycle_status"] == "order_rate_limited"
    assert lifecycle.normalize_broker_status("kraken", "canceled")["lifecycle_status"] == "order_cancelled"


def test_order_lifecycle_required_correlation_fields():
    capital_fields = lifecycle.required_correlation_fields("capital", "broker_acknowledged")
    assert "deal_reference" in capital_fields
    assert "deal_id" in capital_fields
    assert "verification_source" in capital_fields

    missing = lifecycle.missing_correlation_fields(
        {
            "current_status": "broker_acknowledged",
            "venue": "capital",
            "lifecycle_id": "olife-1",
            "route_key": "capital:cfd:GOLD:BUY",
            "symbol": "GOLD",
            "side": "BUY",
            "proof_mode": "mock_broker",
            "deal_reference": "DR1",
        }
    )

    assert "deal_id" in missing
    assert "verification_source" in missing


def test_order_lifecycle_surfaces_missing_links_and_active_route(tmp_path):
    lifecycle_id = lifecycle.lifecycle_id_for("test", "submitted-only")
    route_key = lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")
    lifecycle.append_event(
        root=tmp_path,
        event_type="order_submitted",
        status="order_submitted",
        lifecycle_id=lifecycle_id,
        route_key=route_key,
        venue="capital",
        market_type="cfd",
        symbol="GOLD",
        side="BUY",
    )

    state = lifecycle.load_state(tmp_path)
    row = state["active_lifecycles"][0]

    assert "lifecycle_continuity_missing" in state["continuity_blockers"]
    assert "candidate_ready" in row["missing_links"]
    assert lifecycle.is_active_route(route_key, root=tmp_path) is True

    lifecycle.append_event(
        root=tmp_path,
        event_type="position_closed",
        status="position_closed",
        lifecycle_id=lifecycle_id,
        route_key=route_key,
        symbol="GOLD",
        side="BUY",
    )

    assert lifecycle.is_active_route(route_key, root=tmp_path) is False


def test_order_lifecycle_summary_exposes_broker_correlation_fields(tmp_path):
    lifecycle_id = lifecycle.lifecycle_id_for("test", "broker-fields")
    route_key = lifecycle.route_key_for("binance", "spot", "BTCUSDT", "BUY")
    common = {
        "root": tmp_path,
        "lifecycle_id": lifecycle_id,
        "route_key": route_key,
        "venue": "binance",
        "market_type": "spot",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "client_order_id": "client-123",
        "broker_order_id": "broker-456",
    }
    lifecycle.append_event(event_type="order_submitted", status="order_submitted", venue_status="NEW", **common)
    lifecycle.append_event(
        event_type="partial_fill",
        status="partial_fill",
        venue_status="PARTIALLY_FILLED",
        filled_qty=0.01,
        remaining_qty=0.02,
        avg_fill_price=78000.5,
        fees=0.03,
        verification_source="binance_executionReport",
        proof_mode="mock_broker",
        **common,
    )

    row = lifecycle.load_state(tmp_path)["active_lifecycles"][0]

    assert row["client_order_id"] == "client-123"
    assert row["broker_order_id"] == "broker-456"
    assert row["venue_status"] == "PARTIALLY_FILLED"
    assert row["filled_qty"] == 0.01
    assert row["remaining_qty"] == 0.02
    assert row["avg_fill_price"] == 78000.5
    assert row["fees"] == 0.03
    assert row["verification_source"] == "binance_executionReport"
    assert row["proof_mode"] == "mock_broker"


def test_order_lifecycle_validates_sandbox_paper_proof_fields():
    payload = {
        "proof_tier": "sandbox_paper",
        "broker_environment": "capital_demo",
        "account_mode": "demo",
        "broker_call_id": "call-1",
        "idempotency_key": "idem-1",
        "round_trip_ms": 42,
        "request_timestamp": "2026-05-18T00:00:00+00:00",
        "response_timestamp": "2026-05-18T00:00:01+00:00",
        "credential_scope": "sandbox_demo_only",
        "mutation_scope": "demo_account_only",
    }

    assert lifecycle.validate_proof_tier(payload)["valid"] is True
    assert "proof_tier" in lifecycle.BROKER_CORRELATION_FIELDS
    assert "broker_environment" in lifecycle.BROKER_CORRELATION_FIELDS
    assert "idempotency_key" in lifecycle.BROKER_CORRELATION_FIELDS

    unsafe = dict(payload)
    unsafe["broker_environment"] = "capital_live_production"
    unsafe["mutation_scope"] = "live_real_capital_order"

    result = lifecycle.validate_proof_tier(unsafe)
    assert result["valid"] is False
    assert "sandbox_paper_environment_not_safe" in result["blockers"]
    assert "sandbox_paper_mutation_scope_not_safe" in result["blockers"]


def test_order_lifecycle_summary_exposes_sandbox_paper_fields(tmp_path):
    lifecycle_id = lifecycle.lifecycle_id_for("test", "sandbox-fields")
    route_key = lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")
    lifecycle.append_event(
        root=tmp_path,
        event_type="broker_acknowledged",
        status="broker_acknowledged",
        lifecycle_id=lifecycle_id,
        route_key=route_key,
        venue="capital",
        market_type="cfd",
        symbol="GOLD",
        side="BUY",
        client_order_id="sandbox-client",
        broker_order_id="sandbox-broker",
        deal_reference="DEMO-DR1",
        deal_id="DEMO-D1",
        venue_status="OPEN",
        verification_source="capital_demo_confirms",
        proof_mode="sandbox_paper",
        proof_tier="sandbox_paper",
        broker_environment="capital_demo",
        account_mode="demo",
        broker_call_id="call-1",
        idempotency_key="idem-1",
        round_trip_ms=35,
        request_timestamp="2026-05-18T00:00:00+00:00",
        response_timestamp="2026-05-18T00:00:01+00:00",
        credential_scope="sandbox_demo_only",
        mutation_scope="demo_account_only",
    )

    row = lifecycle.load_state(tmp_path)["active_lifecycles"][0]

    assert row["proof_tier"] == "sandbox_paper"
    assert row["broker_environment"] == "capital_demo"
    assert row["account_mode"] == "demo"
    assert row["broker_call_id"] == "call-1"
    assert row["idempotency_key"] == "idem-1"
    assert row["round_trip_ms"] == 35
    assert row["credential_scope"] == "sandbox_demo_only"
    assert row["mutation_scope"] == "demo_account_only"


def test_order_lifecycle_preserves_active_rows_beyond_jsonl_tail(tmp_path):
    active_lifecycle_id = lifecycle.lifecycle_id_for("capital", "open", "gold", "tail")
    active_route = lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")
    lifecycle.append_event(
        root=tmp_path,
        event_type="position_recovered",
        status="position_open",
        lifecycle_id=active_lifecycle_id,
        route_key=active_route,
        venue="capital",
        market_type="cfd",
        symbol="GOLD",
        side="BUY",
        deal_id="D-TAIL",
        reason="broker_position_reconciled_on_startup",
    )

    for index in range(520):
        candidate_lifecycle_id = lifecycle.lifecycle_id_for("candidate", index)
        lifecycle.append_event(
            root=tmp_path,
            event_type="candidate_ready",
            status="candidate_ready",
            lifecycle_id=candidate_lifecycle_id,
            route_key=lifecycle.route_key_for("kraken", "spot", f"ETH{index}", "SELL"),
            symbol=f"ETH{index}",
            side="SELL",
        )

    state = lifecycle.load_state(tmp_path)

    assert state["event_count"] == 500
    assert state["active_lifecycle_count"] == 1
    assert state["active_lifecycles"][0]["lifecycle_id"] == active_lifecycle_id
    assert state["active_lifecycles"][0]["preserved_from_previous_snapshot"] is True
    assert "lifecycle_continuity_missing" in state["continuity_blockers"]
    assert lifecycle.is_active_route(active_route, root=tmp_path) is True


def test_order_lifecycle_does_not_duplicate_active_row_outside_top_summaries(tmp_path):
    active_lifecycle_id = lifecycle.lifecycle_id_for("capital", "open", "gold", "top-summary")
    active_route = lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")
    lifecycle.append_event(
        root=tmp_path,
        event_type="position_recovered",
        status="position_open",
        lifecycle_id=active_lifecycle_id,
        route_key=active_route,
        venue="capital",
        market_type="cfd",
        symbol="GOLD",
        side="BUY",
        deal_id="D-TOP",
        reason="broker_position_reconciled_on_startup",
    )

    for index in range(60):
        candidate_lifecycle_id = lifecycle.lifecycle_id_for("top-candidate", index)
        lifecycle.append_event(
            root=tmp_path,
            event_type="candidate_ready",
            status="candidate_ready",
            lifecycle_id=candidate_lifecycle_id,
            route_key=lifecycle.route_key_for("kraken", "spot", f"XRP{index}", "SELL"),
            symbol=f"XRP{index}",
            side="SELL",
        )

    state = lifecycle.load_state(tmp_path)

    assert state["active_lifecycle_count"] == 1
    assert [row["lifecycle_id"] for row in state["active_lifecycles"]] == [active_lifecycle_id]
    assert lifecycle.is_active_route(active_route, root=tmp_path) is True


def test_capital_close_requires_absent_position_before_position_closed(monkeypatch, tmp_path):
    from aureon.exchanges.capital_cfd_trader import CFDPosition, CapitalCFDTrader

    monkeypatch.setattr(lifecycle, "REPO_ROOT", tmp_path)

    class StillOpenClient:
        def close_position(self, deal_id):
            return {"success": True, "dealId": deal_id}

        def get_positions(self):
            return [{"position": {"dealId": "D1"}}]

    trader = CapitalCFDTrader.__new__(CapitalCFDTrader)
    trader.client = StillOpenClient()
    trader.stats = {
        "trades_closed": 0.0,
        "total_pnl_gbp": 0.0,
        "winning_trades": 0.0,
        "losing_trades": 0.0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
    }
    trader._latest_monitor_line = ""
    trader._recent_closed_trades = []
    trader._fast_profit_capture_by_deal = {}
    trader._signal_brain = None
    trader._publish_learning_update = lambda record: None  # type: ignore[method-assign]

    pos = CFDPosition(
        symbol="GOLD",
        deal_id="D1",
        epic="GOLD",
        direction="BUY",
        size=0.01,
        entry_price=4500.0,
        tp_price=4510.0,
        sl_price=4490.0,
        asset_class="commodities",
        current_price=4501.0,
        lifecycle_id=lifecycle.lifecycle_id_for("capital", "deal", "D1"),
    )

    result = trader._close_position(pos, "test_close")
    state = json.loads((tmp_path / "state" / "unified_order_lifecycle_latest.json").read_text(encoding="utf-8"))

    assert result["error"] == "close_failed"
    assert state["latest_event"]["status"] == "close_failed"
    assert all(row.get("current_status") != "position_closed" for row in state["lifecycles"])
