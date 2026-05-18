from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aureon.autonomous.aureon_capital_revenue_live_gate_readiness_audit import (
    build_and_write_capital_revenue_live_gate_readiness_audit,
    build_capital_revenue_live_gate_readiness_audit,
)


NOW = datetime(2026, 5, 18, 12, 0, 0, tzinfo=timezone.utc)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _candidate(**overrides: object) -> dict:
    row = {
        "candidate_id": "candidate-US100-BUY",
        "proposed_lifecycle_id": "lifecycle-US100-BUY",
        "route_key": "capital:cfd:US100:BUY",
        "symbol": "US100",
        "epic": "US100",
        "instrument_name": "US Tech 100",
        "side": "BUY",
        "market_status": "TRADEABLE",
        "snapshot_age_sec": 15,
        "gross_edge": 0.55,
        "expected_net_revenue": 0.18,
        "net_revenue_positive": True,
        "lifecycle_duplicate_blocked": False,
        "blockers": [],
        "revenue_blockers": [],
    }
    row.update(overrides)
    return row


def _revenue_logic(candidates: list[dict], *, hedge_leak: bool = False) -> dict:
    return {
        "generated_at": NOW.isoformat(),
        "status": "capital_order_intent_gated",
        "summary": {
            "candidate_count": 6656,
            "trade_ready_candidate_count": 240,
            "net_positive_candidate_count": len(candidates),
            "intent_eligible_candidate_count": 0,
            "false_positive_reject_count": 2,
            "active_watchlist_count": 40,
            "bench_watchlist_count": 100,
            "close_first_opportunity_count": 15,
            "duplicate_route_blocked_count": 10,
            "shadow_confirmation_count": 1,
            "external_shadow_only": not hedge_leak,
            "live_gates_blocking": True,
            "no_live_mutation": True,
        },
        "net_positive_candidates": candidates,
        "external_confirmation_proof": {
            "hedges": [
                {
                    "hedge_candidate_id": "hedge-1",
                    "source_exchange": "binance",
                    "target_candidate_id": candidates[0]["candidate_id"] if candidates else "",
                    "target_symbol": candidates[0]["symbol"] if candidates else "",
                    "hedge_side": "SELL",
                    "authority": "live_order" if hedge_leak else "shadow_only",
                    "mutation_allowed": hedge_leak,
                    "order_intent_allowed": hedge_leak,
                }
            ]
        },
        "capital_order_intent_readiness": {
            "live_gates_blocking": True,
            "runtime_gate_blockers": [],
        },
        "blockers": ["capital_order_intent_gated"],
    }


def _live_dry(*, certified: bool = True, broker_complete: bool = True, recovered_exit_clear: bool = True) -> dict:
    recovered_count = 0 if recovered_exit_clear else 15
    return {
        "generated_at": NOW.isoformat(),
        "status": "live_dry_certified" if certified else "recovered_position_certified_attention",
        "summary": {
            "runtime_fresh": True,
            "active_watchlist_count": 40,
            "bench_watchlist_count": 100,
            "candidate_count": 6656,
            "active_lifecycle_route_count": recovered_count,
            "duplicate_routes_blocked": True,
            "duplicate_route_blocked_count": recovered_count,
            "close_first_opportunity_count": recovered_count,
            "broker_correlation_complete": broker_complete,
            "lifecycle_continuity_complete": certified,
            "recovered_position_count": recovered_count,
            "recovered_positions_certified": recovered_count > 0,
            "recovered_position_close_first_covered": True,
            "recovered_close_chain_status": "not_applicable" if recovered_exit_clear else "recovered_exit_ready_attention",
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


def _write_fixture(
    tmp_path: Path,
    *,
    candidates: list[dict],
    runtime_clear: bool = True,
    live_dry_certified: bool = True,
    broker_complete: bool = True,
    recovered_exit_clear: bool = True,
    hedge_leak: bool = False,
) -> None:
    _write_json(tmp_path / "frontend/public/aureon_capital_revenue_logic_stress_audit.json", _revenue_logic(candidates, hedge_leak=hedge_leak))
    _write_json(
        tmp_path / "frontend/public/aureon_capital_ecosystem_intelligence_company.json",
        {"shadow_hedges": _revenue_logic(candidates, hedge_leak=hedge_leak)["external_confirmation_proof"]["hedges"], "lifecycle": {"duplicate_route_blocked_count": 10}},
    )
    _write_json(
        tmp_path / "frontend/public/aureon_capital_ecosystem_live_dry_stress_audit.json",
        _live_dry(certified=live_dry_certified, broker_complete=broker_complete, recovered_exit_clear=recovered_exit_clear),
    )
    _write_json(tmp_path / "state/unified_order_lifecycle_latest.json", {"continuity_blockers": []})
    _write_json(tmp_path / "state/unified_exchange_order_intents.json", {"status": "fresh_order_intent_packet"})
    _write_json(tmp_path / "state/unified_runtime_status.json", _runtime(clear=runtime_clear))
    _write_json(tmp_path / "frontend/public/aureon_order_lifecycle_stress_audit.json", {"status": "order_lifecycle_stress_certified"})
    _write_json(tmp_path / "frontend/public/aureon_exchange_data_capability_matrix.json", {"rows": []})


def test_live_gate_readiness_certifies_only_when_all_gates_clear(tmp_path: Path) -> None:
    _write_fixture(tmp_path, candidates=[_candidate()])

    report = build_capital_revenue_live_gate_readiness_audit(root=tmp_path, now=NOW)
    row = report["candidate_readiness_rows"][0]

    assert report["status"] == "live_gate_ready"
    assert report["ok"] is True
    assert report["summary"]["net_positive_candidate_count"] == 1
    assert report["summary"]["ready_now_candidate_count"] == 1
    assert row["readiness_state"] == "ready_for_existing_executor_intent"
    assert row["missing_live_gate_ids"] == []
    assert all(case["passed"] for case in report["gate_clear_stress_cases"])


def test_live_gate_readiness_reports_current_attention_gates(tmp_path: Path) -> None:
    stale_duplicate = _candidate(
        snapshot_age_sec=1200,
        lifecycle_duplicate_blocked=True,
        blockers=["capital_snapshot_not_fresh", "active_lifecycle_same_route"],
        revenue_blockers=["capital_snapshot_not_fresh", "active_lifecycle_same_route"],
    )
    _write_fixture(
        tmp_path,
        candidates=[stale_duplicate, _candidate(candidate_id="candidate-US30-SELL", route_key="capital:cfd:US30:SELL", symbol="US30", epic="US30", side="SELL")],
        runtime_clear=False,
        live_dry_certified=False,
        recovered_exit_clear=False,
    )

    report = build_capital_revenue_live_gate_readiness_audit(root=tmp_path, now=NOW)
    missing = set(report["current_live_gate_readiness"]["missing_gate_ids"])

    assert report["status"] == "live_gate_attention"
    assert report["summary"]["net_positive_candidate_count"] == 2
    assert report["summary"]["ready_now_candidate_count"] == 0
    assert "fresh_capital_snapshot" in missing
    assert "no_duplicate_active_route" in missing
    assert "recovered_exit_readiness_clear" in missing
    assert "executor_enabled" in missing
    assert "exchange_mutations_allowed" in missing
    assert report["summary"]["no_live_mutation"] is True


def test_live_gate_readiness_blocks_missing_broker_correlation(tmp_path: Path) -> None:
    _write_fixture(tmp_path, candidates=[_candidate()], broker_complete=False)

    report = build_capital_revenue_live_gate_readiness_audit(root=tmp_path, now=NOW)

    assert report["status"] == "broker_correlation_missing"
    assert report["summary"]["broker_correlation_complete"] is False
    assert "broker_correlation_complete" in report["blockers"]


def test_live_gate_readiness_blocks_external_shadow_mutation_leak(tmp_path: Path) -> None:
    _write_fixture(tmp_path, candidates=[_candidate()], hedge_leak=True)

    report = build_capital_revenue_live_gate_readiness_audit(root=tmp_path, now=NOW)

    assert report["status"] == "external_shadow_mutation_leak"
    assert report["summary"]["external_shadow_only"] is False
    assert "external_shadow_mutation_leak" in report["blockers"]


def test_live_gate_readiness_writes_public_artifacts(tmp_path: Path) -> None:
    _write_fixture(tmp_path, candidates=[_candidate()])

    report = build_and_write_capital_revenue_live_gate_readiness_audit(root=tmp_path)

    assert report["schema_version"] == "aureon-capital-revenue-live-gate-readiness-audit-v1"
    assert (tmp_path / "state/aureon_capital_revenue_live_gate_readiness_audit_last_run.json").exists()
    assert (tmp_path / "docs/audits/aureon_capital_revenue_live_gate_readiness_audit.json").exists()
    assert (tmp_path / "docs/audits/aureon_capital_revenue_live_gate_readiness_audit.md").exists()
    assert (tmp_path / "frontend/public/aureon_capital_revenue_live_gate_readiness_audit.json").exists()
