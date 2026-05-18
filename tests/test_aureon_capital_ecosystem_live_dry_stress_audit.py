from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aureon.autonomous.aureon_capital_ecosystem_live_dry_stress_audit import (
    build_and_write_capital_ecosystem_live_dry_stress_audit,
    build_capital_ecosystem_live_dry_stress_audit,
)


NOW = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _fresh_runtime() -> dict:
    return {
        "ok": True,
        "generated_at": NOW.isoformat(),
        "stale": False,
        "stale_reason": "",
        "exchange_action_plan": {"gold_runtime_trade_proof": {"gold_runtime_candidate_ready": True}},
    }


def _capital_ecosystem(*, shadow_leak: bool = False, close_first: bool = True, over_limit: bool = False) -> dict:
    hedge = {
        "hedge_candidate_id": "hedge-1",
        "source_exchange": "binance",
        "target_symbol": "US100",
        "authority": "shadow_only",
        "mutation_allowed": False,
        "order_intent_allowed": False,
    }
    if shadow_leak:
        hedge["authority"] = "live_order"
        hedge["mutation_allowed"] = True
    return {
        "status": "capital_ecosystem_intelligence_ready",
        "generated_at": NOW.isoformat(),
        "summary": {
            "candidate_count": 120,
            "trade_ready_candidate_count": 40,
            "active_watchlist_count": 41 if over_limit else 40,
            "active_watchlist_limit": 40,
            "bench_watchlist_count": 100,
            "bench_watchlist_limit": 100,
            "gold_preserved": True,
            "shadow_hedge_count": 1,
            "shadow_hedges_only": not shadow_leak,
            "close_first_opportunity_count": 1 if close_first else 0,
            "active_lifecycle_route_count": 1,
            "no_external_hedge_mutation": not shadow_leak,
        },
        "lifecycle": {
            "active_route_keys": ["capital:cfd:US100:BUY"],
            "duplicate_route_blocked_count": 1,
            "continuity_blockers": [],
        },
        "top_velocity_candidates": [{"candidate_id": "cand-1", "symbol": "US100", "route_key": "capital:cfd:US100:BUY"}],
        "shadow_hedges": [hedge],
        "close_first_opportunities": [
            {
                "lifecycle_id": "life-1",
                "route_key": "capital:cfd:US100:BUY",
                "symbol": "US100",
                "deal_id": "deal-1",
                "current_status": "position_open",
                "close_allowed": False,
            }
        ]
        if close_first
        else [],
        "blockers": [],
    }


def _lifecycle(
    *,
    missing_links: bool = False,
    missing_broker_id: bool = False,
    recovered: bool = False,
    missing_deal_id: bool = False,
    missing_source: bool = False,
) -> dict:
    row = {
        "lifecycle_id": "" if missing_broker_id else "life-1",
        "route_key": "capital:cfd:US100:BUY",
        "venue": "capital",
        "market_type": "cfd",
        "symbol": "US100",
        "side": "BUY",
        "current_status": "position_open",
        "deal_id": "" if missing_deal_id else "deal-1",
        "missing_links": ["candidate_ready"] if missing_links else [],
        "last_event": {
            "event_type": "position_recovered" if recovered else "position_open",
            "reason": "broker_position_reconciled_on_startup" if recovered else "",
            "source": "" if missing_source else "capital_cfd_trader.reconcile",
            "verification_source": "" if missing_source else "get_positions",
            "deal_id": "" if missing_deal_id else "deal-1",
            "status": "position_open",
        },
    }
    return {
        "status": "order_lifecycle_ready",
        "active_lifecycle_count": 1,
        "completed_lifecycle_count": 0,
        "continuity_blockers": ["lifecycle_continuity_missing"] if missing_links else [],
        "active_lifecycles": [row],
    }


def _recovered_exit_lifecycle(*, status: str, pnl: bool = False, stale: bool = False) -> dict:
    lifecycle_id = "life-exit-1"
    route_key = "capital:cfd:US100:BUY"
    base = {
        "lifecycle_id": lifecycle_id,
        "route_key": route_key,
        "venue": "capital",
        "market_type": "cfd",
        "symbol": "US100",
        "side": "BUY",
        "deal_id": "deal-exit-1",
        "proof_mode": "mock_broker",
    }
    events = [
        {
            **base,
            "event_type": "position_recovered",
            "status": "position_open",
            "reason": "broker_position_reconciled_on_startup",
            "verification_source": "capital_get_positions_present",
            "source": "capital_cfd_trader.reconcile",
        }
    ]
    if status in {"close_requested", "close_acknowledged", "position_closed", "outcome_recorded", "close_failed"}:
        events.append({**base, "event_type": "close_requested", "status": "close_requested", "close_reason": "test_close"})
    if status in {"close_acknowledged", "position_closed", "outcome_recorded", "close_failed"}:
        events.append(
            {
                **base,
                "event_type": "close_acknowledged",
                "status": "close_acknowledged",
                "deal_reference": "close-ref-1",
                "verification_source": "capital_delete_positions_dealId",
            }
        )
    if status in {"position_closed", "outcome_recorded"}:
        closed = {
            **base,
            "event_type": "position_closed",
            "status": "position_closed",
            "verification_source": "capital_get_positions_absent",
        }
        if pnl:
            closed["net_pnl"] = 0.04
            closed["fees"] = 0.01
        events.append(closed)
    if status == "outcome_recorded":
        events.append(
            {
                **base,
                "event_type": "outcome_recorded",
                "status": "outcome_recorded",
                "verification_source": "cognitive_trade_evidence",
                "net_pnl": 0.04,
                "fees": 0.01,
            }
        )
    if stale:
        events.append(
            {
                **base,
                "event_type": "close_failed",
                "status": "close_failed",
                "error": "stale_broker_proof",
                "verification_source": "capital_get_positions_stale_snapshot",
            }
        )
        status = "close_failed"

    last = events[-1]
    row = {
        **base,
        "current_status": status,
        "missing_links": ["candidate_ready", "intent_published", "executor_accepted", "order_submitted", "broker_acknowledged"],
        "last_event": last,
        "last_reason": last.get("reason", ""),
        "last_error": last.get("error", ""),
        "last_pnl": last.get("net_pnl"),
        "position_open": status in {"position_open", "close_requested", "close_acknowledged"},
        "position_closed": status in {"position_closed", "outcome_recorded"},
        "outcome_recorded": status == "outcome_recorded",
    }
    active_statuses = {"position_open", "close_requested", "close_acknowledged"}
    return {
        "status": "order_lifecycle_ready",
        "active_lifecycle_count": 1 if status in active_statuses else 0,
        "completed_lifecycle_count": 1 if status in {"position_closed", "outcome_recorded"} else 0,
        "continuity_blockers": ["lifecycle_continuity_missing"] if status in active_statuses else [],
        "active_lifecycles": [row] if status in active_statuses else [],
        "lifecycles": [row],
        "events": events,
    }


def _write_base(root: Path, **overrides) -> None:
    _write_json(
        root / "frontend/public/aureon_capital_ecosystem_intelligence_company.json",
        overrides.get("ecosystem") or _capital_ecosystem(),
    )
    _write_json(
        root / "frontend/public/aureon_unified_order_lifecycle.json",
        overrides.get("lifecycle") or _lifecycle(),
    )
    _write_json(
        root / "frontend/public/aureon_order_lifecycle_stress_audit.json",
        {
            "status": "order_lifecycle_stress_certified",
            "summary": {
                "mock_broker_certified": True,
                "sandbox_paper_certified": True,
                "broker_requirement_matrix_complete": True,
            },
        },
    )
    _write_json(root / "frontend/public/aureon_exchange_data_capability_matrix.json", {"rows": [{"exchange": "capital"}]})
    _write_json(root / "ws_cache/ws_prices.json", {"ticker_cache": {"US100": {"price": 100.0}}})


def test_live_dry_stress_certifies_consistent_read_only_evidence(tmp_path: Path) -> None:
    _write_base(tmp_path)

    report = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    assert report["status"] == "live_dry_certified"
    assert report["summary"]["runtime_fresh"] is True
    assert report["summary"]["active_watchlist_count"] == 40
    assert report["summary"]["bench_watchlist_count"] == 100
    assert report["summary"]["duplicate_routes_blocked"] is True
    assert report["summary"]["broker_correlation_complete"] is True
    assert report["summary"]["shadow_hedges_only"] is True
    assert report["summary"]["no_live_mutation"] is True


def test_live_dry_stress_reports_runtime_stale_or_unavailable(tmp_path: Path) -> None:
    _write_base(tmp_path)

    stale = build_capital_ecosystem_live_dry_stress_audit(
        root=tmp_path,
        now=NOW,
        terminal_state={**_fresh_runtime(), "stale": True, "stale_reason": "tick_in_progress_stalled"},
    )
    unavailable = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state={})

    assert stale["status"] == "runtime_stale"
    assert "runtime_stale" in stale["blockers"]
    assert unavailable["status"] == "runtime_unavailable"
    assert "runtime_unavailable" in unavailable["blockers"]


def test_live_dry_stress_blocks_lifecycle_and_broker_correlation_gaps(tmp_path: Path) -> None:
    _write_base(tmp_path, lifecycle=_lifecycle(missing_links=True))
    missing_links = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    _write_base(tmp_path, lifecycle=_lifecycle(missing_broker_id=True))
    missing_broker = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    assert missing_links["status"] == "lifecycle_continuity_missing"
    assert "lifecycle_continuity_missing" in missing_links["blockers"]
    assert missing_broker["status"] == "broker_correlation_missing"
    assert "broker_correlation_missing" in missing_broker["blockers"]


def test_live_dry_stress_certifies_recovered_positions_without_faking_upstream_links(tmp_path: Path) -> None:
    lifecycle = _lifecycle(missing_links=True, recovered=True)
    lifecycle["lifecycles"] = [
        {
            "lifecycle_id": "historical-life-1",
            "route_key": "kraken:spot:ETHUSD:SELL",
            "current_status": "data_ready",
            "last_event": {"event_type": "market_snapshot", "status": "data_ready"},
        }
    ]
    _write_base(tmp_path, lifecycle=lifecycle)

    report = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())
    recovery = report["recovered_position_proof"]

    assert report["status"] == "recovered_position_certified_attention"
    assert "lifecycle_continuity_missing" not in report["blockers"]
    assert "recovered_upstream_context_missing" in report["blockers"]
    assert report["summary"]["lifecycle_continuity_complete"] is True
    assert report["summary"]["recovered_position_count"] == 1
    assert report["summary"]["recovered_positions_certified"] is True
    assert report["summary"]["recovery_certification_status"] == "recovered_position_certified_attention"
    assert recovery["requires_close_first"] is True
    assert recovery["close_first_covered"] is True
    assert recovery["duplicate_route_blocking_active"] is True
    assert recovery["missing_upstream_context_rows"][0]["missing_links"] == ["candidate_ready"]
    assert report["summary"]["recovered_close_chain_status"] == "recovered_exit_ready_attention"
    assert "recovered_exit_ready_attention" in report["summary"]["recovered_exit_blockers"]


def test_live_dry_stress_blocks_recovered_positions_missing_broker_proof(tmp_path: Path) -> None:
    _write_base(tmp_path, lifecycle=_lifecycle(missing_links=True, recovered=True, missing_deal_id=True))
    missing_deal = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    _write_base(tmp_path, lifecycle=_lifecycle(missing_links=True, recovered=True, missing_source=True))
    missing_source = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    assert missing_deal["status"] == "recovered_position_missing_broker_proof"
    assert "deal_id" in missing_deal["recovered_position_proof"]["missing_broker_proof_rows"][0]["missing_fields"]
    assert missing_source["status"] == "recovered_position_missing_broker_proof"
    assert "source" in missing_source["recovered_position_proof"]["missing_broker_proof_rows"][0]["missing_fields"]


def test_live_dry_stress_blocks_recovered_positions_without_close_first_rows(tmp_path: Path) -> None:
    _write_base(
        tmp_path,
        ecosystem=_capital_ecosystem(close_first=False),
        lifecycle=_lifecycle(missing_links=True, recovered=True),
    )

    report = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    assert report["status"] == "recovered_position_close_first_missing"
    assert "recovered_position_close_first_missing" in report["blockers"]
    assert report["recovered_position_proof"]["close_first_covered"] is False


def test_live_dry_stress_reports_recovered_close_ack_waiting_for_absence(tmp_path: Path) -> None:
    _write_base(tmp_path, lifecycle=_recovered_exit_lifecycle(status="close_acknowledged"))

    report = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    assert report["status"] == "recovered_close_ack_waiting_absence"
    assert report["summary"]["recovered_close_chain_status"] == "recovered_close_ack_waiting_absence"
    assert report["summary"]["recovered_close_request_count"] == 1
    assert report["summary"]["recovered_close_acknowledged_count"] == 1
    assert report["summary"]["recovered_position_absence_verified_count"] == 0
    assert "recovered_close_ack_waiting_absence" in report["blockers"]


def test_live_dry_stress_requires_pnl_before_recovered_outcome(tmp_path: Path) -> None:
    _write_base(tmp_path, lifecycle=_recovered_exit_lifecycle(status="position_closed", pnl=False))

    report = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    assert report["status"] == "recovered_exit_missing_pnl"
    assert report["summary"]["recovered_close_chain_status"] == "recovered_exit_missing_pnl"
    assert report["summary"]["recovered_position_absence_verified_count"] == 1
    assert report["summary"]["recovered_outcome_recorded_count"] == 0


def test_live_dry_stress_reports_recovered_outcome_recorded(tmp_path: Path) -> None:
    _write_base(tmp_path, lifecycle=_recovered_exit_lifecycle(status="outcome_recorded", pnl=True))

    report = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    assert report["summary"]["recovered_close_chain_status"] == "recovered_outcome_recorded"
    assert report["summary"]["recovered_position_absence_verified_count"] == 1
    assert report["summary"]["recovered_outcome_recorded_count"] == 1
    assert "recovered_exit_missing_pnl" not in report["blockers"]


def test_live_dry_stress_blocks_recovered_stale_close_proof(tmp_path: Path) -> None:
    _write_base(tmp_path, lifecycle=_recovered_exit_lifecycle(status="close_failed", stale=True))

    report = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    assert report["status"] == "recovered_exit_stale_broker_proof"
    assert report["summary"]["recovered_close_chain_status"] == "recovered_exit_stale_broker_proof"
    assert "recovered_exit_stale_broker_proof" in report["blockers"]


def test_live_dry_stress_blocks_watchlist_shadow_and_close_first_gaps(tmp_path: Path) -> None:
    _write_base(tmp_path, ecosystem=_capital_ecosystem(over_limit=True))
    over_limit = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    _write_base(tmp_path, ecosystem=_capital_ecosystem(shadow_leak=True))
    shadow_leak = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    _write_base(tmp_path, ecosystem=_capital_ecosystem(close_first=False))
    close_missing = build_capital_ecosystem_live_dry_stress_audit(root=tmp_path, now=NOW, terminal_state=_fresh_runtime())

    assert over_limit["status"] == "capital_watchlist_over_limit"
    assert shadow_leak["status"] == "shadow_hedge_mutation_leak"
    assert close_missing["status"] == "close_first_not_prioritized"


def test_live_dry_stress_report_writes_public_artifacts(tmp_path: Path) -> None:
    _write_base(tmp_path)

    report = build_and_write_capital_ecosystem_live_dry_stress_audit(root=tmp_path, terminal_state=_fresh_runtime())
    public_path = tmp_path / "frontend/public/aureon_capital_ecosystem_live_dry_stress_audit.json"

    assert report["write_info"]["evidence_writes"]
    assert public_path.exists()
    public = json.loads(public_path.read_text(encoding="utf-8"))
    assert public["schema_version"] == "aureon-capital-ecosystem-live-dry-stress-audit-v1"
    assert public["status"] == "live_dry_certified"
