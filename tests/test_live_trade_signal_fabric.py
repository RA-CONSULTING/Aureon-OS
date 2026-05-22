from __future__ import annotations

import json

from aureon.trading import order_lifecycle
from aureon.trading.live_trade_signal_fabric import (
    build_state_from_events,
    build_api_budget_proof,
    latest_for_ui,
    normalize_rate_budget_proof,
    normalize_trade_flow_event,
    publish_trade_flow_event,
)


class FakeThoughtBus:
    def __init__(self) -> None:
        self.published = []

    def publish(self, *args, **kwargs):
        self.published.append((args, kwargs))


class FakeMycelium:
    def __init__(self) -> None:
        self.signals = []
        self.messages = []
        self.connection_map = {}

    def receive_external_signal(self, source: str, signal: float, confidence: float = 0.5) -> None:
        self.signals.append({"source": source, "signal": signal, "confidence": confidence})

    def propagate_to_all(self, message_type: str, payload: dict) -> int:
        self.messages.append({"message_type": message_type, "payload": payload})
        return 1


def test_live_trade_signal_fabric_normalizes_trade_event():
    event = normalize_trade_flow_event(
        "intent_published",
        {
            "lifecycle_id": "olife-1",
            "candidate_id": "ocand-1",
            "intent_id": "intent-1",
            "route_key": "capital:cfd:GOLD:BUY",
            "venue": "capital",
            "symbol": "GOLD",
            "side": "BUY",
            "confidence": 0.91,
            "expected_net_revenue": 0.05,
            "three_p_floor_passed": True,
        },
        source_system="test",
    )

    assert event["phase"] == "intent_published"
    assert event["topic"] == "trading.intent.published"
    assert event["trace_id"] == "olife-1"
    assert event["expected_net_revenue"] == 0.05
    assert event["three_p_floor_passed"] is True
    assert event["event_id"].startswith("ltf-")


def test_live_trade_signal_fabric_normalizes_stress_fields():
    event = normalize_trade_flow_event(
        "order_submitted",
        {
            "lifecycle_id": "olife-rate",
            "candidate_id": "ocand-rate",
            "intent_id": "intent-rate",
            "route_key": "capital:cfd:GOLD:BUY",
            "venue": "capital",
            "symbol": "GOLD",
            "side": "BUY",
            "dealReference": "DR-1",
            "rate_budget": {"family": "capital_rest", "remaining": 7, "source": "capital_rate_governor"},
            "phase_latency_ms": 42.5,
            "bus_delivery_count": 2,
            "mycelium_delivery_count": 3,
            "next_required_phase": "broker_acknowledged",
        },
        source_system="test",
    )

    assert event["deal_reference"] == "DR-1"
    assert event["rate_limit_family"] == "capital_rest"
    assert event["rate_remaining"] == 7
    assert event["api_budget_source"] == "capital_rate_governor"
    assert event["phase_latency_ms"] == 42.5
    assert event["bus_delivery_count"] == 2
    assert event["mycelium_delivery_count"] == 3
    assert event["next_required_phase"] == "broker_acknowledged"
    assert event["rate_budget_certified"] is False
    assert "capital_rest_user_budget" in event["missing_api_budget_tags"]


def test_live_trade_signal_fabric_certifies_full_rate_budget_proof():
    proof = normalize_rate_budget_proof(
        {
            "phase": "order_submitted",
            "venue": "capital",
            "rate_budget": {
                "family": "capital_rest",
                "remaining": 9,
                "source": "unit_rate_governor",
                "tags": ["capital_rest_user_budget", "capital_order_position_throttle", "capital_session_freshness"],
            },
        }
    )

    assert proof["rate_budget_certified"] is True
    assert proof["missing_rate_budget_fields"] == []
    assert proof["missing_api_budget_tags"] == []


def test_live_trade_signal_fabric_builds_capital_api_budget_proof():
    proof = build_api_budget_proof(
        venue="capital",
        phase="order_submitted",
        source="unit_rate_governor",
        session_age_sec=30,
        order_position_throttle_ok=True,
        websocket_subscription_count=40,
    )
    normalized = normalize_rate_budget_proof({"venue": "capital", "phase": "order_submitted", "rate_budget": proof})

    assert normalized["rate_budget_certified"] is True
    assert "capital_rest_user_budget" in normalized["api_budget_tags"]
    assert "capital_order_position_throttle" in normalized["api_budget_tags"]
    assert "capital_session_freshness" in normalized["api_budget_tags"]


def test_live_trade_signal_fabric_keeps_binance_5xx_unknown_in_budget_proof():
    proof = build_api_budget_proof(
        venue="binance",
        phase="submit_timeout_unverified",
        source="binance_headers",
        status_code=500,
        retry_after=3,
    )

    assert proof["details"]["execution_status"] == "unknown_until_stream_or_query_proof"
    assert "binance_retry_after_or_execution_report" in proof["tags"]


def test_live_trade_signal_fabric_publishes_to_thoughtbus_and_mycelium(tmp_path):
    bus = FakeThoughtBus()
    mesh = FakeMycelium()

    event = publish_trade_flow_event(
        "signal_generated",
        {
            "lifecycle_id": "olife-signal",
            "candidate_id": "ocand-signal",
            "route_key": "capital:cfd:GOLD:BUY",
            "venue": "capital",
            "symbol": "GOLD",
            "side": "BUY",
            "confidence": 0.8,
        },
        source_system="unit_test",
        root=tmp_path,
        thought_bus=bus,
        mycelium=mesh,
    )

    assert event["thoughtbus_publish_ok"] is True
    assert event["mycelium_ingest_ok"] is True
    assert bus.published
    assert mesh.signals
    assert mesh.connection_map["live_trade_signal_fabric"]["signals_received"] == 1

    public_path = tmp_path / "frontend" / "public" / "aureon_live_trade_signal_fabric.json"
    state = json.loads(public_path.read_text(encoding="utf-8"))
    assert state["summary"]["thoughtbus_receiving"] is True
    assert state["summary"]["mycelium_receiving"] is True


def test_live_trade_signal_fabric_complete_capital_trace(tmp_path):
    bus = FakeThoughtBus()
    mesh = FakeMycelium()
    common = {
        "lifecycle_id": "olife-complete",
        "candidate_id": "ocand-complete",
        "intent_id": "intent-complete",
        "route_key": "capital:cfd:GOLD:BUY",
        "venue": "capital",
        "market_type": "cfd",
        "symbol": "GOLD",
        "side": "BUY",
        "confidence": 0.88,
    }
    for phase in (
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
    ):
        payload = dict(common)
        if phase in {"broker_acknowledged", "position_open", "close_requested", "close_acknowledged", "position_closed"}:
            payload["deal_id"] = "D-1"
            payload["deal_reference"] = "DR-1"
        if phase == "outcome_recorded":
            payload["net_pnl"] = 0.07
        publish_trade_flow_event(phase, payload, root=tmp_path, thought_bus=bus, mycelium=mesh)

    state = latest_for_ui(tmp_path)
    assert state["status"] == "trade_flow_active"
    assert state["summary"]["complete_trace_count"] == 1
    assert state["summary"]["broken_trace_count"] == 0
    assert state["summary"]["outcome_recorded_count"] == 1
    assert state["active_traces"][0]["complete"] is True


def test_live_trade_signal_fabric_detects_broken_chain():
    events = [
        normalize_trade_flow_event(
            "order_submitted",
            {
                "lifecycle_id": "olife-broken",
                "route_key": "capital:cfd:GOLD:BUY",
                "venue": "capital",
                "symbol": "GOLD",
                "side": "BUY",
                "thoughtbus_publish_ok": True,
                "mycelium_ingest_ok": True,
            },
        )
    ]
    events[0]["thoughtbus_publish_ok"] = True
    events[0]["mycelium_ingest_ok"] = True

    state = build_state_from_events(events)

    assert state["status"] == "trade_flow_broken"
    assert state["summary"]["broken_trace_count"] == 1
    assert "candidate_ready" in state["broken_chains"][0]["missing_phases"]


def test_order_lifecycle_bridges_to_signal_fabric_artifact(tmp_path):
    lifecycle_id = order_lifecycle.lifecycle_id_for("fabric", "bridge")
    route_key = order_lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")

    order_lifecycle.append_event(
        root=tmp_path,
        event_type="candidate_ready",
        status="candidate_ready",
        lifecycle_id=lifecycle_id,
        candidate_id="ocand-bridge",
        route_key=route_key,
        venue="capital",
        market_type="cfd",
        symbol="GOLD",
        side="BUY",
    )

    fabric_public = tmp_path / "frontend" / "public" / "aureon_live_trade_signal_fabric.json"
    assert fabric_public.exists()
    state = json.loads(fabric_public.read_text(encoding="utf-8"))
    assert state["events"][-1]["phase"] == "candidate_ready"
    assert isinstance(state["events"][-1].get("thoughtbus_publish_attempted"), bool)


def test_live_trade_signal_fabric_deduplicates_same_lifecycle_event_bucket(tmp_path):
    bus = FakeThoughtBus()
    mesh = FakeMycelium()
    payload = {
        "generated_at": "2026-05-21T16:00:05+00:00",
        "event_id": "olife-event-1",
        "lifecycle_id": "olife-dedupe",
        "candidate_id": "ocand-dedupe",
        "intent_id": "intent-dedupe",
        "route_key": "capital:cfd:GOLD:BUY",
        "venue": "capital",
        "symbol": "GOLD",
        "side": "BUY",
        "rate_limit_family": "capital_rest",
        "rate_remaining": 5,
        "api_budget_source": "unit_rate",
    }
    event1 = publish_trade_flow_event(
        "intent_published",
        dict(payload),
        source_system="unit_test",
        root=tmp_path,
        thought_bus=bus,
        mycelium=mesh,
    )
    event2 = publish_trade_flow_event(
        "intent_published",
        dict(payload),
        source_system="unit_test",
        root=tmp_path,
        thought_bus=bus,
        mycelium=mesh,
    )
    assert event1["dedupe_applied"] is False
    assert event2["dedupe_applied"] is True
    events = []
    log_path = tmp_path / "state" / "aureon_live_trade_signal_fabric_events.jsonl"
    with log_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    assert len(events) == 1
