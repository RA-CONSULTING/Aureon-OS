"""Live-gate readiness audit for Capital revenue candidates.

This audit is read-only. It explains which live gates still block each
net-positive Capital candidate before the existing executor may publish an
order intent.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "aureon-capital-revenue-live-gate-readiness-audit-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]

CAPITAL_REVENUE_LOGIC_PATH = Path("frontend/public/aureon_capital_revenue_logic_stress_audit.json")
CAPITAL_ECOSYSTEM_PATH = Path("frontend/public/aureon_capital_ecosystem_intelligence_company.json")
CAPITAL_LIVE_DRY_STRESS_PATH = Path("frontend/public/aureon_capital_ecosystem_live_dry_stress_audit.json")
ORDER_LIFECYCLE_PATH = Path("state/unified_order_lifecycle_latest.json")
ORDER_INTENTS_PATH = Path("state/unified_exchange_order_intents.json")
RUNTIME_STATUS_PATH = Path("state/unified_runtime_status.json")
ORDER_LIFECYCLE_STRESS_PATH = Path("frontend/public/aureon_order_lifecycle_stress_audit.json")
EXCHANGE_MATRIX_PATH = Path("frontend/public/aureon_exchange_data_capability_matrix.json")

DEFAULT_STATE_PATH = Path("state/aureon_capital_revenue_live_gate_readiness_audit_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_capital_revenue_live_gate_readiness_audit.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_capital_revenue_live_gate_readiness_audit.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_capital_revenue_live_gate_readiness_audit.json")

MANUAL_BOUNDARIES = [
    "read-only live-gate readiness certification",
    "no live order submission",
    "no live close request",
    "no cancel request",
    "no external hedge order",
    "no credential read or reveal",
    "existing runtime, operator, risk, lifecycle, real-order, and exchange-mutation gates remain authoritative",
]

LIVE_GATE_DEFINITIONS = [
    ("fresh_capital_snapshot", "Capital candidate snapshot is fresh enough for live use."),
    ("tradeable_market", "Capital market status is TRADEABLE."),
    ("buy_or_sell_side", "Candidate side is BUY or SELL."),
    ("positive_expected_net_revenue", "Expected net revenue is positive after costs and buffers."),
    ("no_duplicate_active_route", "No submitted/open lifecycle already owns the same route."),
    ("close_first_positions_covered", "Recovered/open Capital positions are covered by close-first rows."),
    ("recovered_exit_readiness_clear", "Recovered positions are absent, closed, or outcome-recorded before new entries."),
    ("broker_correlation_complete", "Broker correlation fields are complete for active lifecycle proof."),
    ("lifecycle_continuity_resolved", "Lifecycle continuity is complete or recovered context is explicitly resolved."),
    ("order_intent_publishing_enabled", "Runtime allows order-intent publication."),
    ("executor_enabled", "Unified order executor is enabled."),
    ("live_trading_enabled", "Live-trading mode is enabled by runtime."),
    ("real_orders_allowed", "Runtime allows real orders."),
    ("exchange_mutations_allowed", "Exchange mutations are enabled by runtime."),
    ("operator_risk_clear", "Operator and runtime risk clearances are clear."),
]

BROKER_REQUIREMENT_BASELINE = {
    "capital": {
        "required_identifiers": ["dealReference", "dealId", "route_key", "lifecycle_id"],
        "status_sources": ["GET /confirms/{dealReference}", "GET /positions", "DELETE /positions/{dealId} acknowledgement"],
        "readiness_rule": "Capital is the only live-capable execution venue; broker position absence is required before close completion.",
    },
    "alpaca": {
        "required_identifiers": ["client_order_id", "broker_order_id"],
        "status_sources": ["order query", "trade/activity event stream"],
        "readiness_rule": "Confirmation-only in this pass; statuses may inform confidence but cannot submit external orders.",
    },
    "binance": {
        "required_identifiers": ["newClientOrderId", "orderId"],
        "status_sources": ["executionReport", "order query", "test order response"],
        "readiness_rule": "Confirmation-only; 5XX/timeout remains unknown until stream or query proof resolves it.",
    },
    "kraken": {
        "required_identifiers": ["cl_ord_id", "broker_order_id"],
        "status_sources": ["openOrders stream/query", "avg_price", "fee", "vol_exec"],
        "readiness_rule": "Confirmation-only; no Kraken placement authority in this pass.",
    },
}

RUNTIME_GATE_IDS = {
    "order_intent_publish_disabled": "order_intent_publishing_enabled",
    "unified_order_executor_disabled": "executor_enabled",
    "live_trading_not_enabled": "live_trading_enabled",
    "real_orders_disabled": "real_orders_allowed",
    "real_orders_not_allowed_by_runtime": "real_orders_allowed",
    "exchange_mutations_disabled": "exchange_mutations_allowed",
    "risk_gate_blocking": "operator_risk_clear",
    "operator_confirmation_missing": "operator_risk_clear",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_root() -> Path:
    cwd = Path.cwd().resolve()
    return cwd if (cwd / "aureon").exists() and (cwd / "frontend").exists() else REPO_ROOT


def _rooted(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _write_text(path: Path, content: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": len(content.encode("utf-8"))}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except Exception:
        return default


def _as_int(value: Any, default: int = 0) -> int:
    return int(_as_float(value, float(default)))


def _strings(value: Any) -> List[str]:
    return [str(item) for item in value if str(item)] if isinstance(value, list) else []


def _unique(items: Sequence[str]) -> List[str]:
    return list(dict.fromkeys(str(item) for item in items if str(item)))


def _runtime_clearances(runtime_status: Dict[str, Any], revenue_logic: Dict[str, Any]) -> List[str]:
    clearances = _strings(runtime_status.get("runtime_clearances"))
    readiness = revenue_logic.get("capital_order_intent_readiness") if isinstance(revenue_logic.get("capital_order_intent_readiness"), dict) else {}
    clearances.extend(_strings(readiness.get("runtime_gate_blockers")))
    return _unique(clearances)


def _build_shared_gate_state(
    revenue_logic: Dict[str, Any],
    live_dry: Dict[str, Any],
    lifecycle_state: Dict[str, Any],
    runtime_status: Dict[str, Any],
    order_intents: Dict[str, Any],
    lifecycle_stress: Dict[str, Any],
) -> Dict[str, Any]:
    live_dry_summary = live_dry.get("summary") if isinstance(live_dry.get("summary"), dict) else {}
    revenue_summary = revenue_logic.get("summary") if isinstance(revenue_logic.get("summary"), dict) else {}
    lifecycle_blockers = _strings(lifecycle_state.get("continuity_blockers"))
    live_dry_blockers = _strings(live_dry.get("blockers"))
    runtime_clearances = _runtime_clearances(runtime_status, revenue_logic)
    recovered_count = _as_int(live_dry_summary.get("recovered_position_count"), 0)
    recovered_close_status = str(live_dry_summary.get("recovered_close_chain_status") or "")
    recovered_exit_clear = recovered_count == 0 or recovered_close_status in {"not_applicable", "recovered_outcome_recorded", "recovered_close_absence_verified"}
    lifecycle_resolved = bool(live_dry_summary.get("lifecycle_continuity_complete")) and "recovered_upstream_context_missing" not in live_dry_blockers
    if recovered_count and live_dry_summary.get("recovered_positions_certified") and not lifecycle_resolved:
        lifecycle_resolved = False

    runtime_status_present = bool(runtime_status)
    order_intent_publish_enabled = runtime_status_present and not (
        bool(runtime_status.get("order_intent_publish_disabled")) or "order_intent_publish_disabled" in runtime_clearances
    )
    executor_enabled = bool(runtime_status.get("executor_enabled")) and "unified_order_executor_disabled" not in runtime_clearances
    live_trading_enabled = bool(runtime_status.get("live_trading_enabled")) and "live_trading_not_enabled" not in runtime_clearances
    real_orders_allowed = (
        runtime_status_present
        and not bool(runtime_status.get("real_orders_disabled"))
        and runtime_status.get("real_orders_allowed_by_runtime") is not False
        and "real_orders_disabled" not in runtime_clearances
        and "real_orders_not_allowed_by_runtime" not in runtime_clearances
    )
    exchange_mutations_allowed = runtime_status_present and not (
        bool(runtime_status.get("exchange_mutations_disabled")) or "exchange_mutations_disabled" in runtime_clearances
    )
    operator_risk_clear = runtime_status_present and not any(
        "risk" in item or "operator" in item or "credential" in item for item in runtime_clearances
    )

    gate_values = {
        "close_first_positions_covered": bool(
            live_dry_summary.get("recovered_position_close_first_covered") or recovered_count == 0
        ),
        "recovered_exit_readiness_clear": recovered_exit_clear,
        "broker_correlation_complete": bool(live_dry_summary.get("broker_correlation_complete")),
        "lifecycle_continuity_resolved": lifecycle_resolved and "lifecycle_continuity_missing" not in lifecycle_blockers,
        "order_intent_publishing_enabled": order_intent_publish_enabled,
        "executor_enabled": executor_enabled,
        "live_trading_enabled": live_trading_enabled,
        "real_orders_allowed": real_orders_allowed,
        "exchange_mutations_allowed": exchange_mutations_allowed,
        "operator_risk_clear": operator_risk_clear,
    }
    runtime_gate_ids = [
        mapped
        for clearance, mapped in RUNTIME_GATE_IDS.items()
        if clearance in runtime_clearances or runtime_status.get(clearance)
    ]
    if not runtime_status_present:
        runtime_gate_ids.extend(
            [
                "order_intent_publishing_enabled",
                "executor_enabled",
                "live_trading_enabled",
                "real_orders_allowed",
                "exchange_mutations_allowed",
                "operator_risk_clear",
            ]
        )
    return {
        "gate_values": gate_values,
        "runtime_status_present": runtime_status_present,
        "runtime_clearances": runtime_clearances,
        "runtime_gate_ids": _unique(runtime_gate_ids),
        "runtime_gates_clear": all(gate_values[key] for key in (
            "order_intent_publishing_enabled",
            "executor_enabled",
            "live_trading_enabled",
            "real_orders_allowed",
            "exchange_mutations_allowed",
            "operator_risk_clear",
        )),
        "recovered_position_count": recovered_count,
        "recovered_close_chain_status": recovered_close_status,
        "recovered_exit_clear": recovered_exit_clear,
        "live_dry_status": live_dry.get("status") or "",
        "live_dry_blockers": live_dry_blockers,
        "lifecycle_blockers": lifecycle_blockers,
        "order_intent_packet_present": bool(order_intents),
        "order_intent_packet_status": order_intents.get("status") or "",
        "lifecycle_stress_certified": lifecycle_stress.get("status") == "order_lifecycle_stress_certified",
        "revenue_status": revenue_logic.get("status") or "",
        "revenue_summary": revenue_summary,
    }


def _candidate_gate_values(candidate: Dict[str, Any], shared: Dict[str, Any]) -> Dict[str, bool]:
    blockers = set(_strings(candidate.get("blockers")) + _strings(candidate.get("revenue_blockers")))
    snapshot_age = candidate.get("snapshot_age_sec")
    shared_values = shared.get("gate_values") if isinstance(shared.get("gate_values"), dict) else {}
    return {
        "fresh_capital_snapshot": snapshot_age is not None and _as_float(snapshot_age, 999999.0) <= 900 and "capital_snapshot_not_fresh" not in blockers,
        "tradeable_market": str(candidate.get("market_status") or "").upper() == "TRADEABLE",
        "buy_or_sell_side": str(candidate.get("side") or "") in {"BUY", "SELL"},
        "positive_expected_net_revenue": bool(candidate.get("net_revenue_positive")) and _as_float(candidate.get("expected_net_revenue"), 0.0) > 0,
        "no_duplicate_active_route": not bool(candidate.get("lifecycle_duplicate_blocked")) and "active_lifecycle_same_route" not in blockers,
        "close_first_positions_covered": bool(shared_values.get("close_first_positions_covered")),
        "recovered_exit_readiness_clear": bool(shared_values.get("recovered_exit_readiness_clear")),
        "broker_correlation_complete": bool(shared_values.get("broker_correlation_complete")),
        "lifecycle_continuity_resolved": bool(shared_values.get("lifecycle_continuity_resolved")),
        "order_intent_publishing_enabled": bool(shared_values.get("order_intent_publishing_enabled")),
        "executor_enabled": bool(shared_values.get("executor_enabled")),
        "live_trading_enabled": bool(shared_values.get("live_trading_enabled")),
        "real_orders_allowed": bool(shared_values.get("real_orders_allowed")),
        "exchange_mutations_allowed": bool(shared_values.get("exchange_mutations_allowed")),
        "operator_risk_clear": bool(shared_values.get("operator_risk_clear")),
    }


def _next_evidence_for(gate_id: str) -> str:
    return {
        "fresh_capital_snapshot": "Refresh Capital market snapshot/stream proof for this candidate.",
        "tradeable_market": "Wait for Capital market status TRADEABLE.",
        "buy_or_sell_side": "Publish a directional BUY/SELL candidate, not WATCH/HOLD.",
        "positive_expected_net_revenue": "Recompute net revenue after spread, slippage, fees, financing, floor, and risk buffer.",
        "no_duplicate_active_route": "Recover, verify absent, or close the active lifecycle for the same route.",
        "close_first_positions_covered": "Publish close-first coverage for every recovered/open Capital position.",
        "recovered_exit_readiness_clear": "Record recovered close acknowledgement, broker absence, and outcome/P&L proof.",
        "broker_correlation_complete": "Attach broker identifiers and verification source to active lifecycle rows.",
        "lifecycle_continuity_resolved": "Resolve recovered upstream context or explicitly certify it as historical/unrecoverable.",
        "order_intent_publishing_enabled": "Enable order-intent publication through the existing runtime gate.",
        "executor_enabled": "Enable the unified executor through reviewed runtime configuration.",
        "live_trading_enabled": "Enable live-trading mode through existing operator/runtime gates.",
        "real_orders_allowed": "Allow real orders through the reviewed runtime risk gate.",
        "exchange_mutations_allowed": "Allow exchange mutation through the reviewed runtime authority gate.",
        "operator_risk_clear": "Clear operator, risk, credential, and safety clearances.",
    }.get(gate_id, "Clear this gate through existing runtime evidence.")


def _candidate_readiness_row(candidate: Dict[str, Any], shared: Dict[str, Any]) -> Dict[str, Any]:
    gate_values = _candidate_gate_values(candidate, shared)
    missing = [gate_id for gate_id, _description in LIVE_GATE_DEFINITIONS if not gate_values.get(gate_id)]
    ready = not missing
    return {
        "candidate_id": candidate.get("candidate_id") or "",
        "proposed_lifecycle_id": candidate.get("proposed_lifecycle_id") or "",
        "route_key": candidate.get("route_key") or "",
        "symbol": candidate.get("symbol") or candidate.get("epic") or "",
        "epic": candidate.get("epic") or "",
        "instrument_name": candidate.get("instrument_name") or "",
        "side": candidate.get("side") or "",
        "expected_net_revenue": candidate.get("expected_net_revenue"),
        "snapshot_age_sec": candidate.get("snapshot_age_sec"),
        "lifecycle_duplicate_blocked": bool(candidate.get("lifecycle_duplicate_blocked")),
        "ready_now": ready,
        "readiness_state": "ready_for_existing_executor_intent" if ready else "blocked_by_live_gates",
        "missing_live_gate_ids": missing,
        "next_required_evidence": _next_evidence_for(missing[0]) if missing else "All required live gates are clear for existing executor intent publication.",
        "gate_values": gate_values,
        "revenue_blockers": _strings(candidate.get("revenue_blockers")),
    }


def _build_current_readiness(revenue_logic: Dict[str, Any], shared: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    candidates = revenue_logic.get("net_positive_candidates") if isinstance(revenue_logic.get("net_positive_candidates"), list) else []
    rows = [_candidate_readiness_row(row, shared) for row in candidates if isinstance(row, dict)]
    missing_gate_ids = _unique(gate_id for row in rows for gate_id in row.get("missing_live_gate_ids", []))
    gate_status = []
    for gate_id, description in LIVE_GATE_DEFINITIONS:
        gate_status.append(
            {
                "id": gate_id,
                "description": description,
                "passed_for_all_net_positive_candidates": gate_id not in missing_gate_ids and bool(rows),
                "blocked_candidate_count": sum(1 for row in rows if gate_id in row.get("missing_live_gate_ids", [])),
            }
        )
    return (
        {
            "gate_count": len(LIVE_GATE_DEFINITIONS),
            "missing_gate_count": len(missing_gate_ids),
            "missing_gate_ids": missing_gate_ids,
            "ready_now_candidate_count": sum(1 for row in rows if row.get("ready_now")),
            "blocked_candidate_count": sum(1 for row in rows if not row.get("ready_now")),
            "gate_status": gate_status,
        },
        rows,
    )


def _fixture_candidate(**overrides: Any) -> Dict[str, Any]:
    candidate = {
        "candidate_id": "fixture-capital-candidate",
        "proposed_lifecycle_id": "fixture-capital-lifecycle",
        "route_key": "capital:cfd:US100:BUY",
        "symbol": "US100",
        "epic": "US100",
        "instrument_name": "US Tech 100",
        "side": "BUY",
        "market_status": "TRADEABLE",
        "snapshot_age_sec": 30,
        "expected_net_revenue": 0.15,
        "net_revenue_positive": True,
        "lifecycle_duplicate_blocked": False,
        "blockers": [],
        "revenue_blockers": [],
    }
    candidate.update(overrides)
    return candidate


def _fixture_shared(**overrides: Any) -> Dict[str, Any]:
    values = {
        "close_first_positions_covered": True,
        "recovered_exit_readiness_clear": True,
        "broker_correlation_complete": True,
        "lifecycle_continuity_resolved": True,
        "order_intent_publishing_enabled": True,
        "executor_enabled": True,
        "live_trading_enabled": True,
        "real_orders_allowed": True,
        "exchange_mutations_allowed": True,
        "operator_risk_clear": True,
    }
    values.update(overrides)
    return {"gate_values": values}


def _stress_case(case_id: str, label: str, candidate: Dict[str, Any], shared: Dict[str, Any], expected_missing: Sequence[str], expected_ready: bool) -> Dict[str, Any]:
    row = _candidate_readiness_row(candidate, shared)
    missing = row["missing_live_gate_ids"]
    passed = bool(row["ready_now"]) == expected_ready and all(item in missing for item in expected_missing)
    return {
        "id": case_id,
        "label": label,
        "passed": passed,
        "readiness_state": row["readiness_state"],
        "ready_now": row["ready_now"],
        "expected_missing_gate_ids": list(expected_missing),
        "actual_missing_gate_ids": missing,
        "proof_mode": "fixture_only_no_broker_mutation",
    }


def _gate_clear_stress_cases() -> List[Dict[str, Any]]:
    return [
        _stress_case(
            "stale_snapshot_blocks",
            "Stale Capital snapshot blocks a net-positive candidate",
            _fixture_candidate(snapshot_age_sec=1200, blockers=["capital_snapshot_not_fresh"], revenue_blockers=["capital_snapshot_not_fresh"]),
            _fixture_shared(),
            ["fresh_capital_snapshot"],
            False,
        ),
        _stress_case(
            "fresh_snapshot_unblocks_snapshot_gate",
            "Fresh Capital snapshot clears the snapshot gate",
            _fixture_candidate(),
            _fixture_shared(),
            [],
            True,
        ),
        _stress_case(
            "duplicate_route_blocks",
            "Duplicate active route blocks new Capital submission",
            _fixture_candidate(lifecycle_duplicate_blocked=True, blockers=["active_lifecycle_same_route"], revenue_blockers=["active_lifecycle_same_route"]),
            _fixture_shared(),
            ["no_duplicate_active_route"],
            False,
        ),
        _stress_case(
            "closed_route_unblocks_duplicate_gate",
            "Recovered or closed route clears duplicate-route gate",
            _fixture_candidate(lifecycle_duplicate_blocked=False),
            _fixture_shared(),
            [],
            True,
        ),
        _stress_case(
            "recovered_exit_held_blocks",
            "Recovered exit readiness blocks new entries until close/outcome proof",
            _fixture_candidate(),
            _fixture_shared(recovered_exit_readiness_clear=False),
            ["recovered_exit_readiness_clear"],
            False,
        ),
        _stress_case(
            "recovered_outcome_unblocks_exit_gate",
            "Recovered outcome proof clears exit readiness",
            _fixture_candidate(),
            _fixture_shared(recovered_exit_readiness_clear=True),
            [],
            True,
        ),
        _stress_case(
            "runtime_gates_disabled_block",
            "Disabled runtime gates block executor intent readiness",
            _fixture_candidate(),
            _fixture_shared(
                order_intent_publishing_enabled=False,
                executor_enabled=False,
                live_trading_enabled=False,
                real_orders_allowed=False,
                exchange_mutations_allowed=False,
                operator_risk_clear=False,
            ),
            [
                "order_intent_publishing_enabled",
                "executor_enabled",
                "live_trading_enabled",
                "real_orders_allowed",
                "exchange_mutations_allowed",
                "operator_risk_clear",
            ],
            False,
        ),
        _stress_case(
            "all_gates_clear_ready_for_existing_executor",
            "All gates clear before existing executor intent publication",
            _fixture_candidate(),
            _fixture_shared(),
            [],
            True,
        ),
    ]


def _build_external_confirmation_proof(revenue_logic: Dict[str, Any], ecosystem: Dict[str, Any], exchange_matrix: Dict[str, Any]) -> Dict[str, Any]:
    source = revenue_logic.get("external_confirmation_proof") if isinstance(revenue_logic.get("external_confirmation_proof"), dict) else {}
    hedges = source.get("hedges") if isinstance(source.get("hedges"), list) else ecosystem.get("shadow_hedges")
    rows = [row for row in hedges if isinstance(row, dict)] if isinstance(hedges, list) else []
    leaks = [
        row
        for row in rows
        if row.get("authority") != "shadow_only" or bool(row.get("mutation_allowed")) or bool(row.get("order_intent_allowed"))
    ]
    matrix_rows = exchange_matrix.get("rows") if isinstance(exchange_matrix.get("rows"), list) else []
    return {
        "shadow_confirmation_count": len(rows),
        "external_shadow_only": not leaks,
        "external_live_order_intent_count": sum(1 for row in rows if bool(row.get("order_intent_allowed"))),
        "leak_rows": leaks[:10],
        "exchange_matrix_rows": len(matrix_rows),
        "blockers": ["external_shadow_mutation_leak"] if leaks else [],
    }


def _status_from(readiness: Dict[str, Any], rows: List[Dict[str, Any]], external: Dict[str, Any], shared: Dict[str, Any]) -> str:
    if external.get("blockers"):
        return "external_shadow_mutation_leak"
    if not rows:
        return "no_net_positive_candidates"
    if not shared.get("gate_values", {}).get("broker_correlation_complete"):
        return "broker_correlation_missing"
    if readiness.get("ready_now_candidate_count"):
        return "live_gate_ready"
    missing = set(readiness.get("missing_gate_ids") or [])
    if missing and missing <= {"fresh_capital_snapshot"}:
        return "candidate_snapshot_not_fresh"
    if missing and missing <= {"no_duplicate_active_route"}:
        return "duplicate_route_active"
    if missing and missing <= {"recovered_exit_readiness_clear", "lifecycle_continuity_resolved"}:
        return "recovered_exit_not_clear"
    runtime_missing = {
        "order_intent_publishing_enabled",
        "executor_enabled",
        "live_trading_enabled",
        "real_orders_allowed",
        "exchange_mutations_allowed",
        "operator_risk_clear",
    }
    if missing and missing <= runtime_missing:
        return "runtime_gate_blocking"
    return "live_gate_attention"


def build_capital_revenue_live_gate_readiness_audit(
    *,
    root: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    now_dt = now or utc_now()
    revenue_logic = _read_json(_rooted(root_path, CAPITAL_REVENUE_LOGIC_PATH), {})
    ecosystem = _read_json(_rooted(root_path, CAPITAL_ECOSYSTEM_PATH), {})
    live_dry = _read_json(_rooted(root_path, CAPITAL_LIVE_DRY_STRESS_PATH), {})
    lifecycle_state = _read_json(_rooted(root_path, ORDER_LIFECYCLE_PATH), {})
    order_intents = _read_json(_rooted(root_path, ORDER_INTENTS_PATH), {})
    runtime_status = _read_json(_rooted(root_path, RUNTIME_STATUS_PATH), {})
    lifecycle_stress = _read_json(_rooted(root_path, ORDER_LIFECYCLE_STRESS_PATH), {})
    exchange_matrix = _read_json(_rooted(root_path, EXCHANGE_MATRIX_PATH), {})
    if not isinstance(revenue_logic, dict):
        revenue_logic = {}
    if not isinstance(ecosystem, dict):
        ecosystem = {}
    if not isinstance(live_dry, dict):
        live_dry = {}
    if not isinstance(lifecycle_state, dict):
        lifecycle_state = {}
    if not isinstance(order_intents, dict):
        order_intents = {}
    if not isinstance(runtime_status, dict):
        runtime_status = {}
    if not isinstance(lifecycle_stress, dict):
        lifecycle_stress = {}
    if not isinstance(exchange_matrix, dict):
        exchange_matrix = {}

    shared = _build_shared_gate_state(revenue_logic, live_dry, lifecycle_state, runtime_status, order_intents, lifecycle_stress)
    current_readiness, candidate_rows = _build_current_readiness(revenue_logic, shared)
    external = _build_external_confirmation_proof(revenue_logic, ecosystem, exchange_matrix)
    stress_cases = _gate_clear_stress_cases()
    missing_gate_ids = current_readiness["missing_gate_ids"]
    blockers = _unique(list(missing_gate_ids) + _strings(external.get("blockers")))
    status = _status_from(current_readiness, candidate_rows, external, shared)
    summary = {
        "net_positive_candidate_count": len(candidate_rows),
        "ready_now_candidate_count": current_readiness["ready_now_candidate_count"],
        "blocked_candidate_count": current_readiness["blocked_candidate_count"],
        "missing_gate_count": current_readiness["missing_gate_count"],
        "runtime_gates_clear": bool(shared.get("runtime_gates_clear")),
        "recovered_exit_clear": bool(shared.get("recovered_exit_clear")),
        "duplicate_routes_blocked": any("no_duplicate_active_route" in row.get("missing_live_gate_ids", []) for row in candidate_rows)
        or bool((ecosystem.get("lifecycle") if isinstance(ecosystem.get("lifecycle"), dict) else {}).get("duplicate_route_blocked_count")),
        "broker_correlation_complete": bool(shared.get("gate_values", {}).get("broker_correlation_complete")),
        "external_shadow_only": bool(external.get("external_shadow_only")),
        "no_live_mutation": True,
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_dt.isoformat(),
        "status": status,
        "ok": status == "live_gate_ready",
        "mode": "read_only_capital_revenue_live_gate_readiness",
        "summary": summary,
        "current_live_gate_readiness": current_readiness,
        "candidate_readiness_rows": candidate_rows,
        "gate_clear_stress_cases": stress_cases,
        "broker_requirement_baseline": BROKER_REQUIREMENT_BASELINE,
        "runtime_gate_proof": {
            "runtime_status_present": shared.get("runtime_status_present"),
            "runtime_clearances": shared.get("runtime_clearances"),
            "runtime_gate_ids": shared.get("runtime_gate_ids"),
            "runtime_gates_clear": shared.get("runtime_gates_clear"),
            "order_intent_packet_present": shared.get("order_intent_packet_present"),
            "order_intent_packet_status": shared.get("order_intent_packet_status"),
        },
        "lifecycle_gate_proof": {
            "lifecycle_blockers": shared.get("lifecycle_blockers"),
            "lifecycle_stress_certified": shared.get("lifecycle_stress_certified"),
            "lifecycle_continuity_resolved": shared.get("gate_values", {}).get("lifecycle_continuity_resolved"),
        },
        "close_first_exit_proof": {
            "recovered_position_count": shared.get("recovered_position_count"),
            "recovered_close_chain_status": shared.get("recovered_close_chain_status"),
            "recovered_exit_clear": shared.get("recovered_exit_clear"),
            "close_first_positions_covered": shared.get("gate_values", {}).get("close_first_positions_covered"),
        },
        "external_confirmation_proof": external,
        "blockers": blockers,
        "manual_boundaries": MANUAL_BOUNDARIES,
        "source_paths": {
            "capital_revenue_logic": CAPITAL_REVENUE_LOGIC_PATH.as_posix(),
            "capital_ecosystem": CAPITAL_ECOSYSTEM_PATH.as_posix(),
            "capital_live_dry_stress": CAPITAL_LIVE_DRY_STRESS_PATH.as_posix(),
            "order_lifecycle": ORDER_LIFECYCLE_PATH.as_posix(),
            "order_intents": ORDER_INTENTS_PATH.as_posix(),
            "runtime_status": RUNTIME_STATUS_PATH.as_posix(),
            "order_lifecycle_stress": ORDER_LIFECYCLE_STRESS_PATH.as_posix(),
            "exchange_matrix": EXCHANGE_MATRIX_PATH.as_posix(),
        },
        "output_files": [
            DEFAULT_STATE_PATH.as_posix(),
            DEFAULT_AUDIT_JSON.as_posix(),
            DEFAULT_AUDIT_MD.as_posix(),
            DEFAULT_PUBLIC_JSON.as_posix(),
        ],
    }
    return report


def _make_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    lines = [
        "# Aureon Capital Revenue Live-Gate Readiness Audit",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Net-positive candidates: `{summary.get('net_positive_candidate_count')}`",
        f"- Ready now: `{summary.get('ready_now_candidate_count')}`",
        f"- Blocked candidates: `{summary.get('blocked_candidate_count')}`",
        f"- Missing gates: `{summary.get('missing_gate_count')}`",
        f"- Runtime gates clear: `{summary.get('runtime_gates_clear')}`",
        f"- Recovered exit clear: `{summary.get('recovered_exit_clear')}`",
        f"- External shadow only: `{summary.get('external_shadow_only')}`",
        f"- No live mutation: `{summary.get('no_live_mutation')}`",
        "",
        "## Candidate Readiness",
    ]
    for row in report.get("candidate_readiness_rows") or []:
        lines.append(
            f"- `{row.get('symbol')}` `{row.get('side')}` net `{row.get('expected_net_revenue')}` "
            f"ready `{row.get('ready_now')}` missing `{','.join(row.get('missing_live_gate_ids') or []) or 'none'}`"
        )
    if not report.get("candidate_readiness_rows"):
        lines.append("- None visible.")
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    lines.extend(["", "## Blockers"])
    lines.extend(f"- `{blocker}`" for blocker in blockers) if blockers else lines.append("- None visible.")
    return "\n".join(lines) + "\n"


def build_and_write_capital_revenue_live_gate_readiness_audit(*, root: Optional[Path] = None) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    report = build_capital_revenue_live_gate_readiness_audit(root=root_path)
    writes = [
        _write_json(_rooted(root_path, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root_path, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root_path, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_rooted(root_path, DEFAULT_PUBLIC_JSON), report),
    ]
    report["write_info"] = {"evidence_writes": writes}
    for rel in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root_path, rel), report)
    _write_text(_rooted(root_path, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build Capital revenue live-gate readiness evidence without broker mutation.")
    parser.add_argument("--repo-root", default="", help="Repository root; defaults to cwd/repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else None
    report = build_and_write_capital_revenue_live_gate_readiness_audit(root=root)
    print(json.dumps(report, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
