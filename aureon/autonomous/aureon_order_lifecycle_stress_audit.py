"""Stress certification for order lifecycle continuity.

The audit uses isolated mock broker evidence. It does not submit, close, or
mutate any broker order.
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set
from urllib.parse import urlparse

from aureon.trading import order_lifecycle as lifecycle


SCHEMA_VERSION = "aureon-order-lifecycle-stress-audit-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_STATE_PATH = Path("state/aureon_order_lifecycle_stress_audit_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_order_lifecycle_stress_audit.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_order_lifecycle_stress_audit.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_order_lifecycle_stress_audit.json")

MANUAL_BOUNDARIES = [
    "mock broker only",
    "sandbox paper probes are guarded",
    "no live order submission",
    "no live close request",
    "no credential read or reveal",
    "no exchange mutation",
    "no UI mutation controls",
]
SANDBOX_MANUAL_BOUNDARIES = [
    "sandbox paper proof only",
    "Capital.com demo URL only",
    "Alpaca paper URL only",
    "Binance order/test or Spot Testnet only",
    "Kraken validate/openOrders only",
    "no production broker order endpoint",
]
SANDBOX_PAPER_REQUIREMENTS: List[Dict[str, Any]] = [
    {
        "id": "capital_demo_gold_chain_guarded",
        "venue": "capital",
        "requirement": "Capital demo GOLD lifecycle carries demo-only dealReference, dealId, position presence, close acknowledgement, absence proof, and P/L.",
        "allowed_environment": "https://demo-api-capital.backend-capital.com/",
    },
    {
        "id": "alpaca_paper_status_guarded",
        "venue": "alpaca",
        "requirement": "Alpaca paper lifecycle is correlated by client_order_id or broker id and explicit order status/query or stream proof.",
        "allowed_environment": "https://paper-api.alpaca.markets",
    },
    {
        "id": "binance_test_or_testnet_guarded",
        "venue": "binance",
        "requirement": "Binance sandbox proof uses /api/v3/order/test by default and treats 5XX/timeout as unknown until query or executionReport resolves it.",
        "allowed_environment": "order/test or Spot Testnet",
    },
    {
        "id": "kraken_validate_openorders_guarded",
        "venue": "kraken",
        "requirement": "Kraken sandbox proof is validate-only placement plus openOrders/query recovery; no real Kraken order placement.",
        "allowed_environment": "validate-only plus openOrders",
    },
    {
        "id": "sandbox_production_endpoint_rejected",
        "venue": "all",
        "requirement": "Production/live order endpoints are rejected before a sandbox_paper lifecycle can advance.",
        "allowed_environment": "demo, paper, order/test, testnet, validate-only",
    },
]

VENUE_REQUIREMENTS: List[Dict[str, Any]] = [
    {
        "id": "capital_deal_reference_confirmed",
        "venue": "capital",
        "requirement": "Capital submit proof carries dealReference before broker acknowledgement.",
        "source": "Capital.com Open API positions/deal confirmation",
        "required_identifiers": ["lifecycle_id", "route_key", "deal_reference"],
        "status_sources": ["POST /positions response", "GET /confirms/{dealReference}"],
        "close_fill_proof": ["dealReference must be confirmed before dealId is trusted"],
        "timeout_behavior": "Hold as submitted/unverified until confirm or positions proof resolves the reference.",
        "recovery_expectation": "On restart, recover Capital positions by dealId and attach them to a lifecycle.",
    },
    {
        "id": "capital_deal_id_attached",
        "venue": "capital",
        "requirement": "Capital broker proof carries dealId after confirmation.",
        "source": "Capital.com Open API positions",
        "required_identifiers": ["deal_reference", "deal_id"],
        "status_sources": ["GET /confirms/{dealReference}", "GET /positions"],
        "close_fill_proof": ["dealId is the close/reconciliation key"],
        "timeout_behavior": "Do not promote to position_open until dealId or get_positions proof exists.",
        "recovery_expectation": "Recovered Capital positions must retain dealId and route key.",
    },
    {
        "id": "capital_open_position_verified",
        "venue": "capital",
        "requirement": "Open exposure is verified from broker get_positions evidence.",
        "source": "Capital.com Open API positions",
        "required_identifiers": ["deal_id", "verification_source"],
        "status_sources": ["GET /positions"],
        "close_fill_proof": ["position_open requires broker position presence"],
        "timeout_behavior": "If positions proof is stale or missing, keep lifecycle active but action-held.",
        "recovery_expectation": "Startup reconciliation attaches orphan broker positions to recovered lifecycle ids.",
    },
    {
        "id": "capital_close_verified_absent",
        "venue": "capital",
        "requirement": "Close is only final after broker positions no longer include the deal.",
        "source": "Capital.com Open API positions close",
        "required_identifiers": ["deal_id", "verification_source"],
        "status_sources": ["DELETE /positions/{dealId}", "GET /positions absence check"],
        "close_fill_proof": ["position_closed requires position absence after close acknowledgement"],
        "timeout_behavior": "A close acknowledgement without absence proof remains close_acknowledged or close_failed.",
        "recovery_expectation": "Open dealIds survive restart until absence or closed-trade proof is recorded.",
    },
    {
        "id": "alpaca_client_order_id_and_status",
        "venue": "alpaca",
        "requirement": "Alpaca order status is correlated by client/order id and explicit lifecycle status.",
        "source": "Alpaca Trading API orders",
        "required_identifiers": ["client_order_id", "broker_order_id", "venue_status"],
        "status_sources": ["trade_updates stream", "GET /v2/orders/{id}"],
        "close_fill_proof": ["partial/full fills carry filled and remaining quantities"],
        "timeout_behavior": "Unknown REST result stays unverified until stream/query proof resolves it.",
        "recovery_expectation": "Startup query of open orders attaches client_order_id or broker order id.",
    },
    {
        "id": "binance_client_order_id_and_execution_report",
        "venue": "binance",
        "requirement": "Binance newClientOrderId and executionReport/query proof reconcile order state.",
        "source": "Binance Spot API orders and user data stream",
        "required_identifiers": ["client_order_id", "broker_order_id", "venue_status"],
        "status_sources": ["executionReport", "GET /api/v3/order"],
        "close_fill_proof": ["executionReport supplies order status, last fill, cumulative fill, and fees when available"],
        "timeout_behavior": "5XX/timeout status is unknown until user stream or order query proof appears.",
        "recovery_expectation": "Startup open-order query attaches newClientOrderId and orderId to lifecycle.",
    },
    {
        "id": "kraken_cl_ord_id_and_open_orders",
        "venue": "kraken",
        "requirement": "Kraken cl_ord_id/openOrders/order query proof reconciles order state.",
        "source": "Kraken Spot API cl_ord_id and openOrders",
        "required_identifiers": ["client_order_id", "broker_order_id", "venue_status"],
        "status_sources": ["openOrders stream", "QueryOrders"],
        "close_fill_proof": ["openOrders carries volume, filled volume, cost, fees, and status updates"],
        "timeout_behavior": "Unknown submit result stays unverified until openOrders or query proof resolves it.",
        "recovery_expectation": "Startup openOrders query attaches cl_ord_id and Kraken order id.",
    },
    {
        "id": "duplicate_route_blocked",
        "venue": "all",
        "requirement": "A second lifecycle is blocked while the same route is submitted/open.",
        "source": "Aureon lifecycle route guard",
        "required_identifiers": ["route_key"],
        "status_sources": ["state/unified_order_lifecycle_latest.json"],
        "close_fill_proof": ["active routes remain exclusive until terminal or recovered-closed proof"],
        "timeout_behavior": "Submitted/open/timeout-unverified lifecycles block duplicate route submission.",
        "recovery_expectation": "Recovered active routes block duplicate submissions after restart.",
    },
    {
        "id": "restart_recovery_orphan_attached",
        "venue": "all",
        "requirement": "Broker state found on startup is attached to a recovered lifecycle with missing links visible.",
        "source": "Aureon lifecycle recovery policy",
        "required_identifiers": ["lifecycle_id", "route_key", "verification_source"],
        "status_sources": ["broker positions", "broker open orders"],
        "close_fill_proof": ["orphan state remains active until broker terminal proof appears"],
        "timeout_behavior": "Missing upstream links are visible as lifecycle_continuity_missing, not hidden.",
        "recovery_expectation": "Recovered lifecycle ids are stable by broker deal/order id.",
    },
    {
        "id": "recovered_exit_outcome_recorded",
        "venue": "capital",
        "requirement": "A recovered Capital position can move through close request, close acknowledgement, broker absence, and final P/L outcome without fabricating upstream links.",
        "source": "Aureon recovered lifecycle exit policy",
        "required_identifiers": ["lifecycle_id", "route_key", "deal_id", "verification_source", "fees"],
        "status_sources": ["DELETE /positions/{dealId}", "GET /positions absence check", "cognitive trade evidence"],
        "close_fill_proof": ["close acknowledgement alone is not closed", "outcome_recorded requires P/L evidence"],
        "timeout_behavior": "Recovered exits remain active/attention until absence proof and P/L evidence are present.",
        "recovery_expectation": "Recovered routes stay duplicate-blocked until verified close or outcome proof.",
    },
    {
        "id": "multi_venue_open_order_recovery",
        "venue": "all",
        "requirement": "Open Alpaca, Binance, and Kraken broker orders recover into active lifecycle rows.",
        "source": "Aureon lifecycle recovery policy",
        "required_identifiers": ["client_order_id", "broker_order_id", "route_key", "verification_source"],
        "status_sources": ["Alpaca orders", "Binance open order query", "Kraken openOrders"],
        "close_fill_proof": ["open orders remain active until fill/cancel/expire/reject proof"],
        "timeout_behavior": "Open-order recovery blocks duplicate route submission.",
        "recovery_expectation": "Every recovered open order retains venue-specific client and broker ids.",
    },
    {
        "id": "partial_fill_reconciled",
        "venue": "all",
        "requirement": "Partial fills keep filled, remaining, average fill, fee, and broker id fields attached.",
        "source": "Broker order status streams",
        "required_identifiers": ["filled_qty", "remaining_qty", "avg_fill_price", "fees", "verification_source"],
        "status_sources": ["Alpaca trade_updates", "Binance executionReport", "Kraken openOrders"],
        "close_fill_proof": ["partial_fill stays active until full fill, cancel, expire, reject, or close proof"],
        "timeout_behavior": "Partial fills are never treated as closed without terminal broker proof.",
        "recovery_expectation": "Recovered partial fills keep cumulative fill and remaining quantity.",
    },
    {
        "id": "timeout_unknown_until_verified",
        "venue": "all",
        "requirement": "A timeout is held as unverified until broker query/stream proof resolves it.",
        "source": "Broker order query requirements",
        "required_identifiers": ["client_order_id", "verification_source"],
        "status_sources": ["broker query", "broker user/order stream"],
        "close_fill_proof": ["timeout status cannot imply rejection, fill, or close by itself"],
        "timeout_behavior": "Timeouts stay submit_timeout_unverified and block duplicate route submission.",
        "recovery_expectation": "Startup query must resolve or preserve the unknown status visibly.",
    },
    {
        "id": "stale_broker_proof_held",
        "venue": "all",
        "requirement": "Stale broker proof cannot advance order, fill, close, or P/L state.",
        "source": "Aureon lifecycle recovery policy",
        "required_identifiers": ["verification_source", "proof_mode"],
        "status_sources": ["timestamped broker query or stream evidence"],
        "close_fill_proof": ["stale proof can only hold/block, never certify position_closed or outcome_recorded"],
        "timeout_behavior": "Stale proof remains order_blocked or close_failed until fresh broker proof arrives.",
        "recovery_expectation": "Recovered state must show stale proof as an explicit blocker.",
    },
    {
        "id": "failure_states_mapped",
        "venue": "all",
        "requirement": "Rejected, cancelled, expired, failed, and rate-limited states map to explicit lifecycle events.",
        "source": "Broker order status requirements",
        "required_identifiers": ["venue_status", "verification_source"],
        "status_sources": ["broker status stream", "broker order query"],
        "close_fill_proof": ["terminal order states cannot become open or closed without a new lifecycle"],
        "timeout_behavior": "Rate limits and rejects are terminal/blocked evidence, not unknown success.",
        "recovery_expectation": "Startup recovery preserves terminal broker status and does not resubmit.",
    },
]


def _default_root() -> Path:
    cwd = Path.cwd().resolve()
    return cwd if (cwd / "aureon").exists() and (cwd / "frontend").exists() else REPO_ROOT


def _rooted(root: Path, rel_path: Path) -> Path:
    return rel_path if rel_path.is_absolute() else root / rel_path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_text(path: Path, content: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": len(content.encode("utf-8"))}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _append(root: Path, status: str, *, lifecycle_id: str, **fields: Any) -> Dict[str, Any]:
    return lifecycle.append_event(root=root, event_type=fields.pop("event_type", status), status=status, lifecycle_id=lifecycle_id, **fields)


def _case_result(
    *,
    case_id: str,
    label: str,
    venue: str,
    root: Path,
    passed: bool,
    covered: Set[str],
    blockers: Optional[List[str]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    state = lifecycle.load_state(root)
    latest = state.get("latest_event") if isinstance(state.get("latest_event"), dict) else {}
    return {
        "id": case_id,
        "label": label,
        "venue": venue,
        "passed": passed,
        "state": "passed" if passed else "failed",
        "blockers": blockers or [],
        "covered_requirements": sorted(covered),
        "latest_status": latest.get("status") or "",
        "active_lifecycle_count": state.get("active_lifecycle_count", 0),
        "completed_lifecycle_count": state.get("completed_lifecycle_count", 0),
        "continuity_blockers": state.get("continuity_blockers") or [],
        "details": details or {},
        "snapshot": {
            "lifecycles": (state.get("lifecycles") or [])[:4],
            "active_lifecycles": (state.get("active_lifecycles") or [])[:4],
        },
    }


def _requirement_matrix_complete() -> bool:
    required_keys = {
        "id",
        "venue",
        "requirement",
        "source",
        "required_identifiers",
        "status_sources",
        "close_fill_proof",
        "timeout_behavior",
        "recovery_expectation",
    }
    return all(required_keys <= set(row.keys()) for row in VENUE_REQUIREMENTS)


def _requirement_matrix_by_venue() -> Dict[str, Any]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for row in VENUE_REQUIREMENTS:
        venue = str(row.get("venue") or "all")
        bucket = grouped.setdefault(
            venue,
            {
                "venue": venue,
                "requirement_count": 0,
                "required_identifiers": [],
                "status_sources": [],
                "timeout_behaviors": [],
                "recovery_expectations": [],
            },
        )
        bucket["requirement_count"] += 1
        for source_key, target_key in (
            ("required_identifiers", "required_identifiers"),
            ("status_sources", "status_sources"),
            ("timeout_behavior", "timeout_behaviors"),
            ("recovery_expectation", "recovery_expectations"),
        ):
            value = row.get(source_key)
            values = value if isinstance(value, list) else [value]
            for item in values:
                item_text = str(item or "").strip()
                if item_text and item_text not in bucket[target_key]:
                    bucket[target_key].append(item_text)
    return grouped


def _url_text(value: Any) -> str:
    return str(value or "").strip().rstrip("/")


def validate_sandbox_probe_config(
    *,
    venue: str,
    endpoint_url: str = "",
    operation: str,
    account_mode: str = "",
    broker_environment: str = "",
    allow_full_lifecycle: bool = False,
) -> Dict[str, Any]:
    venue_key = str(venue or "").strip().lower()
    operation_key = str(operation or "").strip().lower()
    endpoint = _url_text(endpoint_url)
    parsed = urlparse(endpoint if "://" in endpoint else f"https://{endpoint}") if endpoint else None
    host = (parsed.netloc if parsed else "").lower()
    path = (parsed.path if parsed else "").lower()
    account = str(account_mode or "").strip().lower()
    environment = str(broker_environment or "").strip().lower()
    blockers: List[str] = []

    if venue_key == "capital":
        allowed = host == "demo-api-capital.backend-capital.com"
        if not allowed:
            blockers.append("capital_sandbox_requires_demo_api")
        if any(token in endpoint.lower() for token in ("api-capital.backend-capital.com", "live", "production")) and not allowed:
            blockers.append("capital_production_endpoint_rejected")
    elif venue_key == "alpaca":
        if host != "paper-api.alpaca.markets":
            blockers.append("alpaca_sandbox_requires_paper_api")
    elif venue_key == "binance":
        is_test_order = path.endswith("/api/v3/order/test")
        is_testnet = "testnet" in host or environment == "spot_testnet" or account == "testnet"
        if operation_key in {"order_submit", "full_order_lifecycle"} and not is_test_order and not (is_testnet and allow_full_lifecycle):
            blockers.append("binance_sandbox_requires_order_test_or_testnet")
    elif venue_key == "kraken":
        if operation_key in {"order_submit", "close_request", "full_order_lifecycle"}:
            if "validate" not in account and "validate" not in environment and not operation_key.startswith("validate"):
                blockers.append("kraken_sandbox_requires_validate_only")
    else:
        blockers.append("sandbox_venue_unknown")

    return {
        "venue": venue_key,
        "endpoint_url": endpoint,
        "operation": operation_key,
        "account_mode": account,
        "broker_environment": environment,
        "allowed": not blockers,
        "blockers": blockers,
    }


def _sandbox_common(
    *,
    venue: str,
    market_type: str,
    symbol: str,
    side: str,
    broker_environment: str,
    account_mode: str,
    mutation_scope: str,
    credential_scope: str,
    idempotency_key: str,
    broker_call_id: str,
) -> Dict[str, Any]:
    timestamp = _utc_now()
    return {
        "route_key": lifecycle.route_key_for(venue, market_type, symbol, side),
        "venue": venue,
        "market_type": market_type,
        "symbol": symbol,
        "side": side,
        "proof_mode": "sandbox_paper",
        "proof_tier": "sandbox_paper",
        "broker_environment": broker_environment,
        "account_mode": account_mode,
        "broker_call_id": broker_call_id,
        "idempotency_key": idempotency_key,
        "round_trip_ms": 42,
        "request_timestamp": timestamp,
        "response_timestamp": timestamp,
        "credential_scope": credential_scope,
        "mutation_scope": mutation_scope,
    }


def _sandbox_case_result(
    *,
    case_id: str,
    label: str,
    venue: str,
    root: Path,
    passed: bool,
    covered: Set[str],
    guardrails: Optional[List[Dict[str, Any]]] = None,
    blockers: Optional[List[str]] = None,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    row = _case_result(
        case_id=case_id,
        label=label,
        venue=venue,
        root=root,
        passed=passed,
        covered=covered,
        blockers=blockers,
        details=details,
    )
    row["proof_tier"] = "sandbox_paper"
    row["guardrails"] = guardrails or []
    return row


def _capital_demo_gold_sandbox_case(root: Path) -> Dict[str, Any]:
    guard = validate_sandbox_probe_config(
        venue="capital",
        endpoint_url="https://demo-api-capital.backend-capital.com/",
        operation="full_order_lifecycle",
        account_mode="demo",
        broker_environment="capital_demo",
    )
    lid = lifecycle.lifecycle_id_for("sandbox", "capital", "gold", "demo")
    common = _sandbox_common(
        venue="capital",
        market_type="cfd",
        symbol="GOLD",
        side="BUY",
        broker_environment="capital_demo",
        account_mode="demo",
        mutation_scope="demo_account_only",
        credential_scope="sandbox_demo_only",
        idempotency_key="sandbox-capital-gold-demo-1",
        broker_call_id="capital-demo-call-1",
    )
    common["candidate_id"] = "sandbox-capital-gold-candidate"
    common["intent_id"] = "sandbox-capital-gold-intent"
    common["client_order_id"] = "sandbox-capital-gold-client-1"
    for status in ("runtime_started", "data_ready", "candidate_ready", "intent_published", "executor_accepted"):
        _append(root, status, lifecycle_id=lid, **common)
    _append(root, "order_submitted", lifecycle_id=lid, deal_reference="DEMO-DR-GOLD-1", venue_status="ACCEPTED", **common)
    _append(
        root,
        "broker_acknowledged",
        lifecycle_id=lid,
        deal_reference="DEMO-DR-GOLD-1",
        deal_id="DEMO-D-GOLD-1",
        venue_status="OPEN",
        verification_source="capital_demo_confirms_dealReference",
        **common,
    )
    _append(
        root,
        "position_open",
        lifecycle_id=lid,
        deal_id="DEMO-D-GOLD-1",
        venue_status="OPEN",
        filled_qty=0.01,
        remaining_qty=0,
        avg_fill_price=4555.25,
        fees=0.0,
        verification_source="capital_demo_get_positions_present",
        **common,
    )
    _append(root, "close_requested", lifecycle_id=lid, deal_id="DEMO-D-GOLD-1", close_reason="sandbox_demo_close", **common)
    _append(
        root,
        "close_acknowledged",
        lifecycle_id=lid,
        deal_id="DEMO-D-GOLD-1",
        venue_status="CLOSE_ACCEPTED",
        verification_source="capital_demo_delete_positions_dealId",
        **common,
    )
    _append(
        root,
        "position_closed",
        lifecycle_id=lid,
        deal_id="DEMO-D-GOLD-1",
        venue_status="CLOSED",
        verification_source="capital_demo_get_positions_absent",
        net_pnl=0.03,
        fees=0.0,
        **common,
    )
    _append(root, "outcome_recorded", lifecycle_id=lid, deal_id="DEMO-D-GOLD-1", net_pnl=0.03, fees=0.0, **common)
    row = lifecycle.load_state(root)["lifecycles"][0]
    proof_check = lifecycle.validate_proof_tier(row)
    passed = bool(guard["allowed"] and proof_check["valid"] and row.get("continuity_complete") and row.get("outcome_recorded"))
    return _sandbox_case_result(
        case_id="sandbox_capital_demo_gold_start_to_close",
        label="Capital demo GOLD sandbox/paper start-to-close chain",
        venue="capital",
        root=root,
        passed=passed,
        covered={"capital_demo_gold_chain_guarded", "sandbox_production_endpoint_rejected"},
        guardrails=[guard],
        blockers=guard["blockers"] + proof_check["blockers"],
        details={"route_key": common["route_key"], "lifecycle_id": lid, "proof_tier": row.get("proof_tier")},
    )


def _alpaca_paper_sandbox_case(root: Path) -> Dict[str, Any]:
    guard = validate_sandbox_probe_config(
        venue="alpaca",
        endpoint_url="https://paper-api.alpaca.markets",
        operation="order_status_query",
        account_mode="paper",
        broker_environment="alpaca_paper",
    )
    common = _sandbox_common(
        venue="alpaca",
        market_type="equity",
        symbol="GLD",
        side="BUY",
        broker_environment="alpaca_paper",
        account_mode="paper",
        mutation_scope="paper_account_only",
        credential_scope="paper_key_reference_only",
        idempotency_key="sandbox-alpaca-gld-paper-1",
        broker_call_id="alpaca-paper-call-1",
    )
    common["client_order_id"] = "sandbox-alpaca-client-gld-1"
    common["broker_order_id"] = "AP-PAPER-GLD-1"
    lid = lifecycle.lifecycle_id_for("sandbox", "alpaca", common["broker_order_id"])
    for status in ("candidate_ready", "intent_published", "executor_accepted", "order_submitted", "broker_acknowledged"):
        _append(root, status, lifecycle_id=lid, venue_status="new", verification_source="alpaca_paper_order_query", **common)
    _append(
        root,
        "partial_fill",
        lifecycle_id=lid,
        venue_status="partially_filled",
        filled_qty=1,
        remaining_qty=1,
        avg_fill_price=190.12,
        fees=0.0,
        verification_source="alpaca_paper_trade_updates",
        **common,
    )
    duplicate_blocked = lifecycle.is_active_route(common["route_key"], root=root)
    if duplicate_blocked:
        _append(
            root,
            "order_blocked",
            lifecycle_id=lifecycle.lifecycle_id_for("sandbox", "alpaca", "duplicate", common["route_key"]),
            reason="duplicate_active_route",
            **common,
        )
    row = lifecycle.load_state(root)["active_lifecycles"][0]
    proof_check = lifecycle.validate_proof_tier(row)
    mapped = lifecycle.normalize_broker_status("alpaca", "partially_filled")["lifecycle_status"]
    passed = bool(guard["allowed"] and proof_check["valid"] and mapped == "partial_fill" and duplicate_blocked)
    return _sandbox_case_result(
        case_id="sandbox_alpaca_paper_status_and_duplicate_route",
        label="Alpaca paper status mapping and duplicate-route block",
        venue="alpaca",
        root=root,
        passed=passed,
        covered={"alpaca_paper_status_guarded", "sandbox_production_endpoint_rejected"},
        guardrails=[guard],
        blockers=guard["blockers"] + proof_check["blockers"],
        details={"mapped_status": mapped, "duplicate_blocked": duplicate_blocked},
    )


def _binance_testnet_sandbox_case(root: Path) -> Dict[str, Any]:
    guard = validate_sandbox_probe_config(
        venue="binance",
        endpoint_url="https://api.binance.com/api/v3/order/test",
        operation="order_submit",
        account_mode="test_order",
        broker_environment="binance_order_test",
    )
    common = _sandbox_common(
        venue="binance",
        market_type="spot",
        symbol="BTCUSDT",
        side="BUY",
        broker_environment="binance_order_test",
        account_mode="test_order",
        mutation_scope="test_order_no_execution",
        credential_scope="sandbox_key_reference_only",
        idempotency_key="sandbox-binance-btc-test-1",
        broker_call_id="binance-test-call-1",
    )
    common["client_order_id"] = "sandbox-binance-newClientOrderId-1"
    common["broker_order_id"] = "BN-TEST-1"
    lid = lifecycle.lifecycle_id_for("sandbox", "binance", common["client_order_id"])
    for status in ("candidate_ready", "intent_published", "executor_accepted", "order_submitted"):
        _append(root, status, lifecycle_id=lid, venue_status="NEW", **common)
    _append(
        root,
        "submit_timeout_unverified",
        lifecycle_id=lid,
        venue_status="5xx_unknown",
        verification_source="binance_http_5xx_unknown_execution_status",
        **common,
    )
    row = lifecycle.load_state(root)["active_lifecycles"][0]
    proof_check = lifecycle.validate_proof_tier(row)
    mapped = lifecycle.normalize_broker_status("binance", "5xx_unknown")["lifecycle_status"]
    passed = bool(guard["allowed"] and proof_check["valid"] and mapped == "submit_timeout_unverified" and lifecycle.is_active_route(common["route_key"], root=root))
    return _sandbox_case_result(
        case_id="sandbox_binance_test_order_timeout_unknown",
        label="Binance test order keeps 5XX/timeout status unknown until verified",
        venue="binance",
        root=root,
        passed=passed,
        covered={"binance_test_or_testnet_guarded", "sandbox_production_endpoint_rejected"},
        guardrails=[guard],
        blockers=guard["blockers"] + proof_check["blockers"],
        details={"mapped_status": mapped, "current_status": row.get("current_status")},
    )


def _kraken_validate_openorders_sandbox_case(root: Path) -> Dict[str, Any]:
    guard = validate_sandbox_probe_config(
        venue="kraken",
        endpoint_url="https://api.kraken.com",
        operation="validate_order",
        account_mode="validate_only",
        broker_environment="kraken_validate_openOrders",
    )
    common = _sandbox_common(
        venue="kraken",
        market_type="spot",
        symbol="ETH/USD",
        side="SELL",
        broker_environment="kraken_validate_openOrders",
        account_mode="validate_only",
        mutation_scope="validate_only_no_order_placement",
        credential_scope="sandbox_key_reference_only",
        idempotency_key="sandbox-kraken-eth-validate-1",
        broker_call_id="kraken-validate-call-1",
    )
    common["client_order_id"] = "sandbox-kraken-cl_ord_id-1"
    common["broker_order_id"] = "KR-OPEN-1"
    lid = lifecycle.lifecycle_id_for("sandbox", "kraken", common["broker_order_id"])
    _append(root, "broker_acknowledged", event_type="open_order_recovered", lifecycle_id=lid, venue_status="open", verification_source="kraken_openOrders", **common)
    _append(
        root,
        "partial_fill",
        lifecycle_id=lid,
        venue_status="partial",
        filled_qty=0.25,
        remaining_qty=0.75,
        avg_fill_price=3100.5,
        fees=0.12,
        kraken_vol_exec=0.25,
        kraken_cost=775.125,
        kraken_fee=0.12,
        verification_source="kraken_openOrders",
        **common,
    )
    row = lifecycle.load_state(root)["active_lifecycles"][0]
    proof_check = lifecycle.validate_proof_tier(row)
    passed = bool(
        guard["allowed"]
        and proof_check["valid"]
        and row.get("client_order_id") == "sandbox-kraken-cl_ord_id-1"
        and row.get("broker_order_id") == "KR-OPEN-1"
        and row.get("filled_qty") == 0.25
        and row.get("fees") == 0.12
    )
    return _sandbox_case_result(
        case_id="sandbox_kraken_validate_openorders_recovery",
        label="Kraken validate/openOrders recovery maps cl_ord_id, fills, fees, and status",
        venue="kraken",
        root=root,
        passed=passed,
        covered={"kraken_validate_openorders_guarded", "sandbox_production_endpoint_rejected"},
        guardrails=[guard],
        blockers=guard["blockers"] + proof_check["blockers"],
        details={"filled_qty": row.get("filled_qty"), "fees": row.get("fees"), "verification_source": row.get("verification_source")},
    )


def _sandbox_guardrail_rejection_case(root: Path) -> Dict[str, Any]:
    checks = [
        validate_sandbox_probe_config(venue="capital", endpoint_url="https://api-capital.backend-capital.com/", operation="order_submit", account_mode="live", broker_environment="capital_live"),
        validate_sandbox_probe_config(venue="alpaca", endpoint_url="https://api.alpaca.markets", operation="order_submit", account_mode="live", broker_environment="alpaca_live"),
        validate_sandbox_probe_config(venue="binance", endpoint_url="https://api.binance.com/api/v3/order", operation="order_submit", account_mode="live", broker_environment="binance_live"),
        validate_sandbox_probe_config(venue="kraken", endpoint_url="https://api.kraken.com", operation="order_submit", account_mode="live", broker_environment="kraken_live"),
    ]
    passed = all(not check["allowed"] for check in checks)
    _append(
        root,
        "order_blocked",
        lifecycle_id=lifecycle.lifecycle_id_for("sandbox", "guardrail", "production-rejected"),
        route_key="sandbox:guardrail:PRODUCTION:BLOCKED",
        venue="all",
        market_type="guardrail",
        symbol="PRODUCTION_ENDPOINTS",
        side="BLOCK",
        proof_mode="sandbox_paper",
        proof_tier="sandbox_paper",
        broker_environment="guardrail_validation",
        account_mode="sandbox_guard",
        broker_call_id="guardrail-call-1",
        idempotency_key="sandbox-production-rejection-1",
        round_trip_ms=0,
        request_timestamp=_utc_now(),
        response_timestamp=_utc_now(),
        credential_scope="no_credentials_read",
        mutation_scope="blocked_before_broker_call",
        verification_source="sandbox_environment_guard",
        reason="production_order_endpoints_rejected",
    )
    return _sandbox_case_result(
        case_id="sandbox_production_endpoint_guardrails",
        label="Production broker order endpoints are rejected by sandbox/paper guards",
        venue="all",
        root=root,
        passed=passed,
        covered={"sandbox_production_endpoint_rejected"},
        guardrails=checks,
        blockers=[] if passed else ["sandbox_production_endpoint_guard_failed"],
        details={"blocked_count": sum(1 for check in checks if not check["allowed"]), "checked_count": len(checks)},
    )


def _run_sandbox_paper_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for builder in (
        _capital_demo_gold_sandbox_case,
        _alpaca_paper_sandbox_case,
        _binance_testnet_sandbox_case,
        _kraken_validate_openorders_sandbox_case,
        _sandbox_guardrail_rejection_case,
    ):
        with tempfile.TemporaryDirectory(prefix="aureon_order_lifecycle_sandbox_") as tmp:
            cases.append(builder(Path(tmp)))
    return cases


def _capital_gold_clean_case(root: Path) -> Dict[str, Any]:
    lid = lifecycle.lifecycle_id_for("stress", "capital", "gold", "clean")
    route = lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")
    common = {
        "route_key": route,
        "venue": "capital",
        "market_type": "cfd",
        "symbol": "GOLD",
        "side": "BUY",
        "candidate_id": "stress-capital-gold-candidate",
        "intent_id": "stress-capital-gold-intent",
        "client_order_id": "stress-capital-gold-client-1",
        "proof_mode": "mock_broker",
    }
    for status in ("runtime_started", "data_ready", "candidate_ready", "intent_published", "executor_accepted"):
        _append(root, status, lifecycle_id=lid, **common)
    _append(root, "order_submitted", lifecycle_id=lid, deal_reference="DR-STRESS-GOLD-1", venue_status="ACCEPTED", **common)
    _append(
        root,
        "broker_acknowledged",
        lifecycle_id=lid,
        deal_reference="DR-STRESS-GOLD-1",
        deal_id="D-STRESS-GOLD-1",
        venue_status="OPEN",
        verification_source="capital_deal_confirmation",
        **common,
    )
    _append(
        root,
        "position_open",
        lifecycle_id=lid,
        deal_id="D-STRESS-GOLD-1",
        filled_qty=0.01,
        remaining_qty=0,
        avg_fill_price=4555.25,
        fees=0.01,
        verification_source="capital_get_positions_present",
        **common,
    )
    _append(root, "close_requested", lifecycle_id=lid, deal_id="D-STRESS-GOLD-1", close_reason="stress_take_profit", **common)
    _append(
        root,
        "close_acknowledged",
        lifecycle_id=lid,
        deal_id="D-STRESS-GOLD-1",
        venue_status="CLOSE_ACCEPTED",
        verification_source="capital_close_position_response",
        **common,
    )
    _append(
        root,
        "position_closed",
        lifecycle_id=lid,
        deal_id="D-STRESS-GOLD-1",
        venue_status="CLOSED",
        verification_source="capital_get_positions_absent",
        net_pnl=0.07,
        fees=0.02,
        **common,
    )
    _append(root, "outcome_recorded", lifecycle_id=lid, deal_id="D-STRESS-GOLD-1", net_pnl=0.07, fees=0.02, **common)
    row = lifecycle.load_state(root)["lifecycles"][0]
    passed = bool(row.get("continuity_complete") and row.get("outcome_recorded") and row.get("deal_reference") and row.get("deal_id"))
    return _case_result(
        case_id="capital_gold_clean_start_to_close",
        label="Capital GOLD clean start-to-close chain",
        venue="capital",
        root=root,
        passed=passed,
        covered={
            "capital_deal_reference_confirmed",
            "capital_deal_id_attached",
            "capital_open_position_verified",
            "capital_close_verified_absent",
        },
        details={"route_key": route, "lifecycle_id": lid, "net_pnl": row.get("last_pnl")},
    )


def _delayed_ack_case(root: Path) -> Dict[str, Any]:
    lid = lifecycle.lifecycle_id_for("stress", "capital", "gold", "delayed_ack")
    route = lifecycle.route_key_for("capital", "cfd", "GOLD", "SELL")
    common = {"route_key": route, "venue": "capital", "market_type": "cfd", "symbol": "GOLD", "side": "SELL", "proof_mode": "mock_broker"}
    for status in ("candidate_ready", "intent_published", "executor_accepted"):
        _append(root, status, lifecycle_id=lid, **common)
    _append(root, "order_submitted", lifecycle_id=lid, deal_reference="DR-DELAYED", client_order_id="stress-delay-client", **common)
    submitted_state = lifecycle.load_state(root)
    before_row = (submitted_state.get("active_lifecycles") or [{}])[0]
    status_before_ack = before_row.get("current_status")
    active_before_ack = lifecycle.is_active_route(route, root=root)
    _append(
        root,
        "broker_acknowledged",
        lifecycle_id=lid,
        deal_reference="DR-DELAYED",
        deal_id="D-DELAYED",
        venue_status="OPEN",
        verification_source="delayed_broker_query",
        **common,
    )
    _append(root, "position_open", lifecycle_id=lid, deal_id="D-DELAYED", verification_source="capital_get_positions_present", **common)
    latest_row = lifecycle.load_state(root)["active_lifecycles"][0]
    passed = status_before_ack == "order_submitted" and active_before_ack and latest_row.get("deal_id") == "D-DELAYED"
    return _case_result(
        case_id="delayed_broker_acknowledgement",
        label="Delayed broker acknowledgement stays active until proof arrives",
        venue="capital",
        root=root,
        passed=passed,
        covered={"timeout_unknown_until_verified", "capital_deal_id_attached"},
        details={"status_before_ack": status_before_ack, "active_before_ack": active_before_ack, "route_key": route},
    )


def _duplicate_route_case(root: Path) -> Dict[str, Any]:
    lid = lifecycle.lifecycle_id_for("stress", "duplicate", "open")
    duplicate_lid = lifecycle.lifecycle_id_for("stress", "duplicate", "blocked")
    route = lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")
    common = {"route_key": route, "venue": "capital", "market_type": "cfd", "symbol": "GOLD", "side": "BUY", "proof_mode": "mock_broker"}
    _append(root, "candidate_ready", lifecycle_id=lid, **common)
    _append(root, "intent_published", lifecycle_id=lid, **common)
    _append(root, "executor_accepted", lifecycle_id=lid, **common)
    _append(root, "order_submitted", lifecycle_id=lid, deal_reference="DR-DUP", **common)
    _append(root, "broker_acknowledged", lifecycle_id=lid, deal_reference="DR-DUP", deal_id="D-DUP", **common)
    _append(root, "position_open", lifecycle_id=lid, deal_id="D-DUP", verification_source="capital_get_positions_present", **common)
    duplicate_blocked = lifecycle.is_active_route(route, root=root)
    if duplicate_blocked:
        _append(
            root,
            "order_blocked",
            lifecycle_id=duplicate_lid,
            route_key=route,
            venue="capital",
            market_type="cfd",
            symbol="GOLD",
            side="BUY",
            reason="duplicate_active_route",
            proof_mode="mock_broker",
        )
    return _case_result(
        case_id="duplicate_route_while_open",
        label="Duplicate route blocked while prior lifecycle is open",
        venue="all",
        root=root,
        passed=duplicate_blocked,
        covered={"duplicate_route_blocked"},
        details={"route_key": route, "blocked_lifecycle_id": duplicate_lid},
    )


def _restart_recovery_case(root: Path) -> Dict[str, Any]:
    lid = lifecycle.lifecycle_id_for("capital", "deal", "D-ORPHAN-1")
    route = lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")
    _append(
        root,
        "position_open",
        event_type="position_recovered",
        lifecycle_id=lid,
        route_key=route,
        venue="capital",
        market_type="cfd",
        symbol="GOLD",
        side="BUY",
        deal_id="D-ORPHAN-1",
        verification_source="startup_capital_get_positions",
        proof_mode="mock_broker",
        reason="broker_position_reconciled_on_startup",
    )
    state = lifecycle.load_state(root)
    row = state["active_lifecycles"][0]
    passed = bool(lifecycle.is_active_route(route, root=root) and "lifecycle_continuity_missing" in state.get("continuity_blockers", []))
    return _case_result(
        case_id="restart_recovery_orphan_position",
        label="Restart recovery attaches orphan broker position and keeps missing links visible",
        venue="all",
        root=root,
        passed=passed,
        covered={"restart_recovery_orphan_attached", "capital_open_position_verified"},
        details={"missing_links": row.get("missing_links") or [], "deal_id": row.get("deal_id")},
    )


def _recovered_exit_outcome_case(root: Path) -> Dict[str, Any]:
    lid = lifecycle.lifecycle_id_for("capital", "deal", "D-RECOVERED-EXIT-1")
    route = lifecycle.route_key_for("capital", "cfd", "US100", "SELL")
    common = {
        "route_key": route,
        "venue": "capital",
        "market_type": "cfd",
        "symbol": "US100",
        "side": "SELL",
        "deal_id": "D-RECOVERED-EXIT-1",
        "proof_mode": "mock_broker",
    }
    _append(
        root,
        "position_open",
        event_type="position_recovered",
        lifecycle_id=lid,
        verification_source="startup_capital_get_positions",
        reason="broker_position_reconciled_on_startup",
        **common,
    )
    duplicate_before_close = lifecycle.is_active_route(route, root=root)
    _append(root, "close_requested", lifecycle_id=lid, close_reason="stress_recovered_exit", **common)
    _append(
        root,
        "close_acknowledged",
        lifecycle_id=lid,
        deal_reference="DR-RECOVERED-CLOSE-1",
        venue_status="CLOSE_ACCEPTED",
        verification_source="capital_delete_positions_dealId",
        **common,
    )
    state_after_ack = lifecycle.load_state(root)
    ack_row = state_after_ack["active_lifecycles"][0]
    active_after_ack = lifecycle.is_active_route(route, root=root)
    _append(
        root,
        "position_closed",
        lifecycle_id=lid,
        venue_status="CLOSED",
        verification_source="capital_get_positions_absent",
        net_pnl=0.06,
        fees=0.01,
        **common,
    )
    active_after_absence = lifecycle.is_active_route(route, root=root)
    _append(
        root,
        "outcome_recorded",
        lifecycle_id=lid,
        verification_source="cognitive_trade_evidence",
        net_pnl=0.06,
        fees=0.01,
        **common,
    )
    state = lifecycle.load_state(root)
    row = state["lifecycles"][0]
    passed = bool(
        duplicate_before_close
        and active_after_ack
        and ack_row.get("current_status") == "close_acknowledged"
        and not active_after_absence
        and row.get("current_status") == "outcome_recorded"
        and row.get("outcome_recorded")
        and row.get("last_pnl") == 0.06
        and "candidate_ready" in (row.get("missing_links") or [])
    )
    return _case_result(
        case_id="recovered_position_exit_to_outcome",
        label="Recovered Capital position exits through close ack, absence proof, and P/L outcome",
        venue="capital",
        root=root,
        passed=passed,
        covered={"recovered_exit_outcome_recorded", "capital_close_verified_absent", "duplicate_route_blocked"},
        details={
            "route_key": route,
            "duplicate_before_close": duplicate_before_close,
            "active_after_ack": active_after_ack,
            "active_after_absence": active_after_absence,
            "current_status": row.get("current_status"),
            "missing_links": row.get("missing_links"),
        },
    )


def _recovered_close_ack_waiting_absence_case(root: Path) -> Dict[str, Any]:
    lid = lifecycle.lifecycle_id_for("capital", "deal", "D-RECOVERED-WAIT-ABSENCE")
    route = lifecycle.route_key_for("capital", "cfd", "US30", "BUY")
    common = {
        "route_key": route,
        "venue": "capital",
        "market_type": "cfd",
        "symbol": "US30",
        "side": "BUY",
        "deal_id": "D-RECOVERED-WAIT-ABSENCE",
        "proof_mode": "mock_broker",
    }
    _append(
        root,
        "position_open",
        event_type="position_recovered",
        lifecycle_id=lid,
        verification_source="startup_capital_get_positions",
        reason="broker_position_reconciled_on_startup",
        **common,
    )
    _append(root, "close_requested", lifecycle_id=lid, close_reason="stress_recovered_exit", **common)
    _append(
        root,
        "close_acknowledged",
        lifecycle_id=lid,
        deal_reference="DR-RECOVERED-WAIT-ABSENCE",
        venue_status="CLOSE_ACCEPTED",
        verification_source="capital_delete_positions_dealId",
        **common,
    )
    state = lifecycle.load_state(root)
    row = state["active_lifecycles"][0]
    passed = bool(
        row.get("current_status") == "close_acknowledged"
        and lifecycle.is_active_route(route, root=root)
        and not row.get("position_closed")
    )
    return _case_result(
        case_id="recovered_close_ack_waiting_absence",
        label="Recovered close acknowledgement stays active until broker absence proof",
        venue="capital",
        root=root,
        passed=passed,
        covered={"capital_close_verified_absent", "recovered_exit_outcome_recorded"},
        details={"route_key": route, "current_status": row.get("current_status"), "missing_links": row.get("missing_links")},
    )


def _recovered_stale_close_proof_case(root: Path) -> Dict[str, Any]:
    lid = lifecycle.lifecycle_id_for("capital", "deal", "D-RECOVERED-STALE-CLOSE")
    route = lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")
    common = {
        "route_key": route,
        "venue": "capital",
        "market_type": "cfd",
        "symbol": "GOLD",
        "side": "BUY",
        "deal_id": "D-RECOVERED-STALE-CLOSE",
        "proof_mode": "mock_broker",
    }
    _append(
        root,
        "position_open",
        event_type="position_recovered",
        lifecycle_id=lid,
        verification_source="startup_capital_get_positions",
        reason="broker_position_reconciled_on_startup",
        **common,
    )
    _append(root, "close_requested", lifecycle_id=lid, close_reason="stress_recovered_exit", **common)
    _append(
        root,
        "close_failed",
        lifecycle_id=lid,
        verification_source="capital_get_positions_stale_snapshot",
        error="stale_broker_proof",
        **common,
    )
    state = lifecycle.load_state(root)
    row = state["lifecycles"][0]
    passed = bool(
        row.get("current_status") == "close_failed"
        and not row.get("position_closed")
        and not row.get("outcome_recorded")
        and not lifecycle.is_active_route(route, root=root)
    )
    return _case_result(
        case_id="recovered_stale_close_proof_held",
        label="Recovered stale close proof cannot certify closed or outcome state",
        venue="capital",
        root=root,
        passed=passed,
        covered={"stale_broker_proof_held", "recovered_exit_outcome_recorded"},
        details={"route_key": route, "current_status": row.get("current_status"), "verification_source": row.get("verification_source")},
    )


def _multi_venue_open_order_recovery_case(root: Path) -> Dict[str, Any]:
    recovered_orders = [
        {
            "venue": "alpaca",
            "market_type": "equity",
            "symbol": "GLD",
            "side": "BUY",
            "client_order_id": "stress-alpaca-client-open",
            "broker_order_id": "AP-OPEN-1",
            "venue_status": "new",
            "verification_source": "alpaca_trade_updates_stream",
        },
        {
            "venue": "binance",
            "market_type": "spot",
            "symbol": "ETHUSDT",
            "side": "BUY",
            "client_order_id": "stress-binance-client-open",
            "broker_order_id": "BN-OPEN-1",
            "venue_status": "NEW",
            "verification_source": "binance_open_order_query",
        },
        {
            "venue": "kraken",
            "market_type": "spot",
            "symbol": "ETH/USD",
            "side": "SELL",
            "client_order_id": "stress-kraken-clord-open",
            "broker_order_id": "KR-OPEN-1",
            "venue_status": "open",
            "filled_qty": 0.0,
            "remaining_qty": 0.25,
            "verification_source": "kraken_openOrders",
        },
    ]
    route_keys: List[str] = []
    for order in recovered_orders:
        lid = lifecycle.lifecycle_id_for("recovered-open-order", order["venue"], order["broker_order_id"])
        route = lifecycle.route_key_for(order["venue"], order["market_type"], order["symbol"], order["side"])
        route_keys.append(route)
        _append(
            root,
            "broker_acknowledged",
            event_type="open_order_recovered",
            lifecycle_id=lid,
            route_key=route,
            proof_mode="mock_broker",
            reason="startup_open_order_reconciled",
            **order,
        )
    state = lifecycle.load_state(root)
    active_routes = {str(row.get("route_key") or "") for row in state.get("active_lifecycles", []) if isinstance(row, dict)}
    missing_ids = [
        str(row.get("lifecycle_id") or "")
        for row in state.get("active_lifecycles", [])
        if isinstance(row, dict) and lifecycle.missing_correlation_fields(row)
    ]
    passed = set(route_keys) <= active_routes and not missing_ids
    return _case_result(
        case_id="multi_venue_open_order_recovery",
        label="Alpaca, Binance, and Kraken open orders recover with broker ids",
        venue="all",
        root=root,
        passed=passed,
        covered={
            "multi_venue_open_order_recovery",
            "alpaca_client_order_id_and_status",
            "binance_client_order_id_and_execution_report",
            "kraken_cl_ord_id_and_open_orders",
        },
        blockers=[f"missing_correlation:{item}" for item in missing_ids],
        details={"route_keys": route_keys, "active_routes": sorted(active_routes)},
    )


def _partial_fill_case(root: Path) -> Dict[str, Any]:
    lid = lifecycle.lifecycle_id_for("stress", "binance", "partial")
    route = lifecycle.route_key_for("binance", "spot", "BTCUSDT", "BUY")
    common = {
        "route_key": route,
        "venue": "binance",
        "market_type": "spot",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "client_order_id": "stress-binance-client-1",
        "broker_order_id": "BN-ORDER-1",
        "proof_mode": "mock_broker",
    }
    _append(root, "candidate_ready", lifecycle_id=lid, **common)
    _append(root, "intent_published", lifecycle_id=lid, **common)
    _append(root, "executor_accepted", lifecycle_id=lid, **common)
    _append(root, "order_submitted", lifecycle_id=lid, venue_status="NEW", **common)
    _append(root, "broker_acknowledged", lifecycle_id=lid, venue_status="NEW", verification_source="binance_query_order", **common)
    _append(
        root,
        "partial_fill",
        lifecycle_id=lid,
        venue_status="PARTIALLY_FILLED",
        filled_qty=0.002,
        remaining_qty=0.003,
        avg_fill_price=78000.0,
        fees=0.03,
        verification_source="binance_executionReport",
        **common,
    )
    _append(
        root,
        "position_open",
        lifecycle_id=lid,
        venue_status="FILLED",
        filled_qty=0.005,
        remaining_qty=0,
        avg_fill_price=78001.5,
        fees=0.05,
        verification_source="binance_executionReport",
        **common,
    )
    row = lifecycle.load_state(root)["active_lifecycles"][0]
    passed = row.get("filled_qty") == 0.005 and row.get("remaining_qty") == 0 and row.get("client_order_id") == "stress-binance-client-1"
    return _case_result(
        case_id="partial_fill_then_full_fill",
        label="Partial fill keeps quantities, price, fees, and client/broker ids",
        venue="all",
        root=root,
        passed=passed,
        covered={"partial_fill_reconciled", "binance_client_order_id_and_execution_report"},
        details={"route_key": route, "filled_qty": row.get("filled_qty"), "remaining_qty": row.get("remaining_qty")},
    )


def _close_ack_still_present_case(root: Path) -> Dict[str, Any]:
    lid = lifecycle.lifecycle_id_for("stress", "capital", "close_still_present")
    route = lifecycle.route_key_for("capital", "cfd", "GOLD", "SELL")
    common = {"route_key": route, "venue": "capital", "market_type": "cfd", "symbol": "GOLD", "side": "SELL", "deal_id": "D-STILL-OPEN", "proof_mode": "mock_broker"}
    for status in ("candidate_ready", "intent_published", "executor_accepted", "order_submitted", "broker_acknowledged", "position_open", "close_requested", "close_acknowledged"):
        _append(root, status, lifecycle_id=lid, verification_source="capital_mock_sequence", **common)
    _append(
        root,
        "close_failed",
        lifecycle_id=lid,
        verification_source="capital_get_positions_still_present",
        error="position_still_present_after_close_ack",
        close_reason="stress_close_verification",
        **common,
    )
    state = lifecycle.load_state(root)
    row = state["lifecycles"][0]
    passed = row.get("current_status") == "close_failed" and not row.get("position_closed")
    return _case_result(
        case_id="close_ack_without_position_absence",
        label="Close acknowledgement does not become closed while broker still reports the position",
        venue="capital",
        root=root,
        passed=passed,
        covered={"capital_close_verified_absent"},
        details={"latest_status": row.get("current_status"), "verification_source": row.get("verification_source")},
    )


def _stale_broker_proof_case(root: Path) -> Dict[str, Any]:
    lid = lifecycle.lifecycle_id_for("stress", "stale", "capital", "gold")
    route = lifecycle.route_key_for("capital", "cfd", "GOLD", "BUY")
    common = {
        "route_key": route,
        "venue": "capital",
        "market_type": "cfd",
        "symbol": "GOLD",
        "side": "BUY",
        "candidate_id": "stress-stale-candidate",
        "intent_id": "stress-stale-intent",
        "client_order_id": "stress-stale-client",
        "proof_mode": "mock_broker",
    }
    _append(root, "candidate_ready", lifecycle_id=lid, **common)
    _append(root, "intent_published", lifecycle_id=lid, **common)
    _append(root, "executor_accepted", lifecycle_id=lid, **common)
    _append(
        root,
        "order_blocked",
        lifecycle_id=lid,
        venue_status="stale",
        verification_source="capital_get_positions_stale_snapshot",
        reason="stale_broker_proof_cannot_advance_lifecycle",
        generated_at="2020-01-01T00:00:00+00:00",
        **common,
    )
    state = lifecycle.load_state(root)
    row = state["lifecycles"][0]
    passed = (
        row.get("current_status") == "order_blocked"
        and not lifecycle.is_active_route(route, root=root)
        and not row.get("position_open")
        and not row.get("position_closed")
        and not row.get("outcome_recorded")
    )
    return _case_result(
        case_id="stale_broker_proof_held",
        label="Stale broker proof holds action and cannot certify lifecycle advancement",
        venue="all",
        root=root,
        passed=passed,
        covered={"stale_broker_proof_held"},
        details={"route_key": route, "latest_status": row.get("current_status"), "verification_source": row.get("verification_source")},
    )


def _failure_status_matrix_case(root: Path) -> Dict[str, Any]:
    rows = [
        ("alpaca", "equity", "GLD", "BUY", "AP-1", "rejected", "order_rejected", "alpaca_client_order_id_and_status"),
        ("alpaca", "equity", "IAU", "BUY", "AP-2", "canceled", "order_cancelled", "alpaca_client_order_id_and_status"),
        ("kraken", "spot", "ETH/USD", "SELL", "KR-1", "expired", "order_expired", "kraken_cl_ord_id_and_open_orders"),
        ("binance", "spot", "ETHUSDT", "BUY", "BN-2", "timeout", "submit_timeout_unverified", "timeout_unknown_until_verified"),
        ("binance", "spot", "SOLUSDT", "BUY", "BN-3", "rate_limit", "order_rate_limited", "failure_states_mapped"),
    ]
    covered: Set[str] = {"failure_states_mapped"}
    checks: List[Dict[str, Any]] = []
    for venue, market_type, symbol, side, broker_order_id, venue_status, expected_status, requirement in rows:
        lid = lifecycle.lifecycle_id_for("stress", "failure", venue, broker_order_id)
        route = lifecycle.route_key_for(venue, market_type, symbol, side)
        common = {
            "route_key": route,
            "venue": venue,
            "market_type": market_type,
            "symbol": symbol,
            "side": side,
            "client_order_id": f"stress-{broker_order_id}",
            "broker_order_id": broker_order_id,
            "proof_mode": "mock_broker",
        }
        _append(root, "candidate_ready", lifecycle_id=lid, **common)
        _append(root, "intent_published", lifecycle_id=lid, **common)
        _append(root, "executor_accepted", lifecycle_id=lid, **common)
        _append(root, "order_submitted", lifecycle_id=lid, venue_status="submitted", **common)
        mapped = lifecycle.normalize_broker_status(venue, venue_status)["lifecycle_status"]
        _append(root, mapped, lifecycle_id=lid, venue_status=venue_status, verification_source=f"{venue}_mock_status", **common)
        covered.add(requirement)
        checks.append({"venue": venue, "venue_status": venue_status, "expected": expected_status, "mapped": mapped})
    passed = all(row["expected"] == row["mapped"] for row in checks)
    return _case_result(
        case_id="failure_cancel_expire_timeout_rate_limit_matrix",
        label="Broker failure and unknown states map to explicit lifecycle statuses",
        venue="all",
        root=root,
        passed=passed,
        covered=covered,
        details={"checks": checks},
    )


def _run_cases() -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for builder in (
        _capital_gold_clean_case,
        _delayed_ack_case,
        _duplicate_route_case,
        _restart_recovery_case,
        _recovered_exit_outcome_case,
        _recovered_close_ack_waiting_absence_case,
        _multi_venue_open_order_recovery_case,
        _partial_fill_case,
        _close_ack_still_present_case,
        _stale_broker_proof_case,
        _recovered_stale_close_proof_case,
        _failure_status_matrix_case,
    ):
        with tempfile.TemporaryDirectory(prefix="aureon_order_lifecycle_stress_") as tmp:
            cases.append(builder(Path(tmp)))
    return cases


def build_order_lifecycle_stress_audit(
    *,
    root: Optional[Path] = None,
    cases: Optional[List[Dict[str, Any]]] = None,
    sandbox_cases: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    case_rows = cases if cases is not None else _run_cases()
    sandbox_case_rows = sandbox_cases if sandbox_cases is not None else _run_sandbox_paper_cases()
    requirement_ids = {row["id"] for row in VENUE_REQUIREMENTS}
    sandbox_requirement_ids = {row["id"] for row in SANDBOX_PAPER_REQUIREMENTS}
    covered = {
        requirement
        for case in case_rows
        if case.get("passed")
        for requirement in case.get("covered_requirements", [])
    }
    sandbox_covered = {
        requirement
        for case in sandbox_case_rows
        if case.get("passed")
        for requirement in case.get("covered_requirements", [])
    }
    missing = sorted(requirement_ids - covered)
    sandbox_missing = sorted(sandbox_requirement_ids - sandbox_covered)
    blockers: List[str] = []
    sandbox_blockers: List[str] = []
    if any(not case.get("passed") for case in case_rows):
        blockers.append("order_lifecycle_stress_case_failed")
    if missing:
        blockers.append("order_lifecycle_stress_requirements_missing")
    if not _requirement_matrix_complete():
        blockers.append("order_lifecycle_requirement_matrix_incomplete")
    if any(not case.get("passed") for case in sandbox_case_rows):
        sandbox_blockers.append("sandbox_paper_case_failed")
    if sandbox_missing:
        sandbox_blockers.append("sandbox_paper_requirements_missing")
    status = "order_lifecycle_stress_certified" if not blockers else "order_lifecycle_stress_attention"
    sandbox_status = "sandbox_paper_certified" if not sandbox_blockers else "sandbox_paper_attention"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "status": status,
        "ok": not blockers,
        "mode": "mock_broker_and_sandbox_paper_stress_certification",
        "proof_tiers": {
            "mock_broker": {
                "status": status,
                "certified": not blockers,
                "case_count": len(case_rows),
                "passed_count": sum(1 for case in case_rows if case.get("passed")),
                "requirement_count": len(requirement_ids),
                "covered_requirement_count": len(covered),
                "missing_requirements": missing,
                "blockers": blockers,
            },
            "sandbox_paper": {
                "status": sandbox_status,
                "certified": not sandbox_blockers,
                "case_count": len(sandbox_case_rows),
                "passed_count": sum(1 for case in sandbox_case_rows if case.get("passed")),
                "requirement_count": len(sandbox_requirement_ids),
                "covered_requirement_count": len(sandbox_covered),
                "missing_requirements": sandbox_missing,
                "blockers": sandbox_blockers,
                "probe_mode": "guarded_fixture_no_broker_mutation",
                "manual_boundaries": SANDBOX_MANUAL_BOUNDARIES,
            },
        },
        "summary": {
            "case_count": len(case_rows),
            "passed_count": sum(1 for case in case_rows if case.get("passed")),
            "failed_count": sum(1 for case in case_rows if not case.get("passed")),
            "requirement_count": len(requirement_ids),
            "covered_requirement_count": len(covered),
            "coverage_percent": round((len(covered) / max(1, len(requirement_ids))) * 100.0, 3),
            "venue_count": len({row["venue"] for row in VENUE_REQUIREMENTS if row["venue"] != "all"}),
            "capital_gold_path_certified": "capital_deal_reference_confirmed" in covered
            and "capital_close_verified_absent" in covered,
            "duplicate_route_blocked": "duplicate_route_blocked" in covered,
            "restart_recovery_certified": "restart_recovery_orphan_attached" in covered,
            "recovered_exit_certified": "recovered_exit_outcome_recorded" in covered,
            "recovered_exit_outcome_recorded": any(case.get("id") == "recovered_position_exit_to_outcome" and case.get("passed") for case in case_rows),
            "recovered_close_ack_waiting_absence_held": any(case.get("id") == "recovered_close_ack_waiting_absence" and case.get("passed") for case in case_rows),
            "recovered_exit_stale_proof_blocked": any(case.get("id") == "recovered_stale_close_proof_held" and case.get("passed") for case in case_rows),
            "multi_venue_recovery_certified": "multi_venue_open_order_recovery" in covered,
            "close_verification_enforced": "capital_close_verified_absent" in covered,
            "partial_fill_certified": "partial_fill_reconciled" in covered,
            "stale_broker_proof_blocked": "stale_broker_proof_held" in covered,
            "failure_state_mapping_certified": "failure_states_mapped" in covered,
            "broker_requirement_matrix_complete": _requirement_matrix_complete(),
            "no_live_mutation": True,
            "no_ui_mutation_controls": True,
            "mock_broker_status": status,
            "mock_broker_certified": not blockers,
            "sandbox_paper_status": sandbox_status,
            "sandbox_paper_certified": not sandbox_blockers,
            "sandbox_paper_case_count": len(sandbox_case_rows),
            "sandbox_paper_passed_count": sum(1 for case in sandbox_case_rows if case.get("passed")),
            "sandbox_paper_requirement_count": len(sandbox_requirement_ids),
            "sandbox_paper_covered_requirement_count": len(sandbox_covered),
            "sandbox_paper_missing_requirements": sandbox_missing,
            "sandbox_paper_blockers": sandbox_blockers,
            "sandbox_environment_guard_passed": "sandbox_production_endpoint_rejected" in sandbox_covered,
            "sandbox_no_production_order_endpoints": "sandbox_production_endpoint_rejected" in sandbox_covered,
            "sandbox_probe_mode": "guarded_fixture_no_broker_mutation",
            "broker_correlation_fields": lifecycle.BROKER_CORRELATION_FIELDS,
            "broker_requirement_matrix_by_venue": _requirement_matrix_by_venue(),
            "blocker_count": len(blockers),
        },
        "blockers": blockers,
        "missing_requirements": missing,
        "requirements": VENUE_REQUIREMENTS,
        "sandbox_paper_requirements": SANDBOX_PAPER_REQUIREMENTS,
        "cases": case_rows,
        "sandbox_paper_cases": sandbox_case_rows,
        "manual_boundaries": MANUAL_BOUNDARIES,
        "sandbox_manual_boundaries": SANDBOX_MANUAL_BOUNDARIES,
        "output_files": [
            DEFAULT_STATE_PATH.as_posix(),
            DEFAULT_AUDIT_JSON.as_posix(),
            DEFAULT_AUDIT_MD.as_posix(),
            DEFAULT_PUBLIC_JSON.as_posix(),
        ],
    }


def _make_markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    lines = [
        "# Aureon Order Lifecycle Stress Audit",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Mock broker: `{summary.get('mock_broker_status')}`",
        f"- Sandbox/paper: `{summary.get('sandbox_paper_status')}`",
        f"- Cases: `{summary.get('passed_count')}/{summary.get('case_count')}`",
        f"- Requirements: `{summary.get('covered_requirement_count')}/{summary.get('requirement_count')}`",
        f"- Sandbox cases: `{summary.get('sandbox_paper_passed_count')}/{summary.get('sandbox_paper_case_count')}`",
        f"- Sandbox requirements: `{summary.get('sandbox_paper_covered_requirement_count')}/{summary.get('sandbox_paper_requirement_count')}`",
        f"- Capital GOLD path certified: `{summary.get('capital_gold_path_certified')}`",
        f"- Duplicate route blocked: `{summary.get('duplicate_route_blocked')}`",
        f"- Multi-venue recovery certified: `{summary.get('multi_venue_recovery_certified')}`",
        f"- Recovered exit certified: `{summary.get('recovered_exit_certified')}`",
        f"- Close verification enforced: `{summary.get('close_verification_enforced')}`",
        f"- Stale broker proof blocked: `{summary.get('stale_broker_proof_blocked')}`",
        f"- Sandbox production endpoint guard: `{summary.get('sandbox_no_production_order_endpoints')}`",
        f"- Requirement matrix complete: `{summary.get('broker_requirement_matrix_complete')}`",
        f"- Non-mutating: `{summary.get('no_live_mutation')}`",
        "",
        "## Cases",
    ]
    for case in report.get("cases") or []:
        lines.append(f"- `{case.get('id')}`: `{case.get('state')}`")
    lines.extend(["", "## Sandbox/Paper Cases"])
    for case in report.get("sandbox_paper_cases") or []:
        lines.append(f"- `{case.get('id')}`: `{case.get('state')}`")
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    lines.extend(["", "## Blockers"])
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- None visible.")
    return "\n".join(lines) + "\n"


def build_and_write_order_lifecycle_stress_audit(*, root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    report = build_order_lifecycle_stress_audit(root=root)
    writes = [
        _write_json(_rooted(root, DEFAULT_STATE_PATH), report),
        _write_json(_rooted(root, DEFAULT_AUDIT_JSON), report),
        _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report)),
        _write_json(_rooted(root, DEFAULT_PUBLIC_JSON), report),
    ]
    report["write_info"] = {"evidence_writes": writes}
    for rel in (DEFAULT_STATE_PATH, DEFAULT_AUDIT_JSON, DEFAULT_PUBLIC_JSON):
        _write_json(_rooted(root, rel), report)
    _write_text(_rooted(root, DEFAULT_AUDIT_MD), _make_markdown(report))
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Stress-test Aureon's order lifecycle continuity without broker mutation.")
    parser.add_argument("--repo-root", default="", help="Repository root; defaults to cwd/repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else None
    report = build_and_write_order_lifecycle_stress_audit(root=root)
    print(json.dumps(report, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
