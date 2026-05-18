"""Read-only stress audit for Capital-wide revenue logic.

This audit proves that Aureon can search the Capital ecosystem for positive
net revenue candidates without bypassing runtime, lifecycle, broker, or
exchange-mutation gates. It reads existing evidence only.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


SCHEMA_VERSION = "aureon-capital-revenue-logic-stress-audit-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]

CAPITAL_ECOSYSTEM_PATH = Path("frontend/public/aureon_capital_ecosystem_intelligence_company.json")
CAPITAL_LIVE_DRY_STRESS_PATH = Path("frontend/public/aureon_capital_ecosystem_live_dry_stress_audit.json")
RUNTIME_STATUS_PATH = Path("state/unified_runtime_status.json")
EXCHANGE_MATRIX_PATH = Path("frontend/public/aureon_exchange_data_capability_matrix.json")

DEFAULT_STATE_PATH = Path("state/aureon_capital_revenue_logic_stress_audit_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_capital_revenue_logic_stress_audit.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_capital_revenue_logic_stress_audit.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_capital_revenue_logic_stress_audit.json")

REVENUE_PROOF_FIELDS = [
    "gross_edge",
    "spread_cost",
    "slippage_buffer",
    "fee_estimate",
    "financing_fee_estimate",
    "margin_required_for_min_deal",
    "minimum_deal_size",
    "expected_time_to_profit_sec",
    "risk_buffer",
    "expected_net_revenue",
    "net_revenue_positive",
    "revenue_intent_eligible",
    "revenue_blockers",
]

MANUAL_BOUNDARIES = [
    "read-only revenue logic stress",
    "no live order submission",
    "no live close request",
    "no cancel request",
    "no external hedge order",
    "no credential read or reveal",
    "existing runtime and lifecycle gates remain authoritative",
]


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


def _candidate_rows(ecosystem: Dict[str, Any]) -> List[Dict[str, Any]]:
    seen: set[str] = set()
    rows: List[Dict[str, Any]] = []
    watchlists = ecosystem.get("watchlists") if isinstance(ecosystem.get("watchlists"), dict) else {}
    sources = [
        ecosystem.get("top_velocity_candidates"),
        watchlists.get("active_stream_watchlist"),
        watchlists.get("bench_watchlist"),
    ]
    for source in sources:
        if not isinstance(source, list):
            continue
        for row in source:
            if not isinstance(row, dict):
                continue
            key = str(row.get("candidate_id") or row.get("route_key") or row.get("symbol") or len(rows))
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
    return rows


def _missing_revenue_fields(row: Dict[str, Any]) -> List[str]:
    return [field for field in REVENUE_PROOF_FIELDS if field not in row]


def _safe_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": row.get("candidate_id") or "",
        "proposed_lifecycle_id": row.get("proposed_lifecycle_id") or "",
        "route_key": row.get("route_key") or "",
        "symbol": row.get("symbol") or row.get("epic") or "",
        "epic": row.get("epic") or "",
        "instrument_name": row.get("instrument_name") or "",
        "asset_class": row.get("asset_class") or "",
        "side": row.get("side") or "",
        "market_status": row.get("market_status") or "",
        "trade_ready": bool(row.get("trade_ready")),
        "snapshot_age_sec": row.get("snapshot_age_sec"),
        "fast_profit_velocity_score": row.get("fast_profit_velocity_score"),
        "gross_edge": row.get("gross_edge"),
        "spread_cost": row.get("spread_cost"),
        "slippage_buffer": row.get("slippage_buffer"),
        "fee_estimate": row.get("fee_estimate"),
        "financing_fee_estimate": row.get("financing_fee_estimate"),
        "risk_buffer": row.get("risk_buffer"),
        "expected_net_revenue": row.get("expected_net_revenue"),
        "expected_time_to_profit_sec": row.get("expected_time_to_profit_sec"),
        "net_revenue_positive": bool(row.get("net_revenue_positive")),
        "revenue_intent_eligible": bool(row.get("revenue_intent_eligible")),
        "lifecycle_duplicate_blocked": bool(row.get("lifecycle_duplicate_blocked")),
        "revenue_blockers": [str(item) for item in (row.get("revenue_blockers") or []) if str(item)],
        "blockers": [str(item) for item in (row.get("blockers") or []) if str(item)],
    }


def _build_candidate_revenue_proof(ecosystem: Dict[str, Any]) -> Dict[str, Any]:
    rows = _candidate_rows(ecosystem)
    missing_rows = []
    safe_rows = [_safe_row(row) for row in rows]
    for row in rows:
        missing = _missing_revenue_fields(row)
        if missing:
            missing_rows.append(
                {
                    "candidate_id": row.get("candidate_id") or "",
                    "symbol": row.get("symbol") or row.get("epic") or "",
                    "route_key": row.get("route_key") or "",
                    "missing_fields": missing,
                }
            )
    net_positive = sorted(
        [row for row in safe_rows if bool(row.get("net_revenue_positive"))],
        key=lambda row: _as_float(row.get("expected_net_revenue"), 0.0),
        reverse=True,
    )
    false_positive = sorted(
        [
            row
            for row in safe_rows
            if _as_float(row.get("gross_edge"), 0.0) > 0
            and (
                not bool(row.get("net_revenue_positive"))
                or bool(row.get("revenue_blockers"))
                or bool(row.get("lifecycle_duplicate_blocked"))
            )
        ],
        key=lambda row: _as_float(row.get("gross_edge"), 0.0),
        reverse=True,
    )
    candidate_level_eligible = [
        row
        for row in safe_rows
        if bool(row.get("revenue_intent_eligible")) and str(row.get("side") or "") in {"BUY", "SELL"}
    ]
    blockers: List[str] = []
    if not ecosystem:
        blockers.append("capital_ecosystem_intelligence_missing")
    if rows and missing_rows:
        blockers.append("candidate_revenue_fields_missing")
    if rows and not net_positive:
        blockers.append("no_net_positive_candidates")
    if net_positive and not candidate_level_eligible:
        blockers.append("no_revenue_intent_eligible_candidates")
    return {
        "checked_candidate_count": len(rows),
        "trade_ready_candidate_count": sum(1 for row in safe_rows if row.get("trade_ready")),
        "candidate_revenue_fields_complete": not missing_rows,
        "missing_revenue_field_rows": missing_rows[:20],
        "net_positive_candidate_count": len(net_positive),
        "candidate_level_intent_eligible_count": len(candidate_level_eligible),
        "false_positive_reject_count": len(false_positive),
        "top_net_positive_candidates": net_positive[:20],
        "candidate_level_intent_eligible_candidates": candidate_level_eligible[:20],
        "rejected_false_positives": false_positive[:20],
        "blockers": blockers,
    }


def _build_runtime_gate_proof(runtime_status: Dict[str, Any], live_dry: Dict[str, Any]) -> Dict[str, Any]:
    live_dry_summary = live_dry.get("summary") if isinstance(live_dry.get("summary"), dict) else {}
    live_dry_blockers = [str(item) for item in (live_dry.get("blockers") or []) if str(item)]
    runtime_clearances = [str(item) for item in (runtime_status.get("runtime_clearances") or []) if str(item)]
    live_dry_runtime_fresh = bool(live_dry_summary.get("runtime_fresh"))
    blockers: List[str] = []
    if not runtime_status and not live_dry_runtime_fresh:
        blockers.append("runtime_status_missing")
    if runtime_status.get("stale") or runtime_status.get("stale_reason"):
        blockers.append(str(runtime_status.get("stale_reason") or "runtime_stale"))
    if runtime_status.get("executor_enabled") is False or "unified_order_executor_disabled" in runtime_clearances:
        blockers.append("unified_order_executor_disabled")
    if runtime_status.get("exchange_mutations_disabled") or "exchange_mutations_disabled" in runtime_clearances:
        blockers.append("exchange_mutations_disabled")
    if runtime_status.get("live_trading_enabled") is False or "live_trading_not_enabled" in runtime_clearances:
        blockers.append("live_trading_not_enabled")
    if runtime_status.get("real_orders_disabled") or "real_orders_disabled" in runtime_clearances:
        blockers.append("real_orders_disabled")
    if runtime_status.get("real_orders_allowed_by_runtime") is False or "real_orders_not_allowed_by_runtime" in runtime_clearances:
        blockers.append("real_orders_not_allowed_by_runtime")
    if runtime_status.get("order_intent_publish_disabled") or "order_intent_publish_disabled" in runtime_clearances:
        blockers.append("order_intent_publish_disabled")
    if live_dry and live_dry.get("status") != "live_dry_certified":
        blockers.append("capital_live_dry_not_certified")
    blockers.extend(live_dry_blockers)
    broker_complete = bool(live_dry_summary.get("broker_correlation_complete"))
    close_first_covered = bool(
        live_dry_summary.get("recovered_position_close_first_covered")
        or _as_int(live_dry_summary.get("recovered_position_count"), 0) == 0
    )
    if live_dry and not broker_complete:
        blockers.append("broker_correlation_missing")
    if live_dry and not close_first_covered:
        blockers.append("close_first_not_prioritized")
    return {
        "runtime_status_present": bool(runtime_status),
        "runtime_fresh_from_live_dry": live_dry_runtime_fresh,
        "runtime_generated_at": runtime_status.get("generated_at") or "",
        "executor_enabled": bool(runtime_status.get("executor_enabled")),
        "exchange_mutations_disabled": bool(runtime_status.get("exchange_mutations_disabled")),
        "real_orders_disabled": bool(runtime_status.get("real_orders_disabled")),
        "live_trading_enabled": bool(runtime_status.get("live_trading_enabled")),
        "runtime_clearances": runtime_clearances,
        "live_dry_status": live_dry.get("status") or "",
        "live_dry_certified": live_dry.get("status") == "live_dry_certified",
        "broker_correlation_complete": broker_complete,
        "close_first_covered": close_first_covered,
        "live_gates_clear": not blockers,
        "blockers": list(dict.fromkeys(blockers)),
    }


def _build_order_intent_readiness(candidate_proof: Dict[str, Any], runtime_gate: Dict[str, Any]) -> Dict[str, Any]:
    candidate_level_rows = candidate_proof.get("candidate_level_intent_eligible_candidates")
    if not isinstance(candidate_level_rows, list):
        candidate_level_rows = []
    live_gates_clear = bool(runtime_gate.get("live_gates_clear"))
    intent_eligible = candidate_level_rows if live_gates_clear else []
    blockers = []
    if candidate_level_rows and not live_gates_clear:
        blockers.append("capital_order_intent_gated")
    blockers.extend(str(item) for item in runtime_gate.get("blockers", []) if str(item))
    return {
        "candidate_level_eligible_count": len(candidate_level_rows),
        "intent_eligible_candidate_count": len(intent_eligible),
        "intent_eligible_candidates": intent_eligible[:10],
        "live_gates_blocking": not live_gates_clear,
        "runtime_gate_blockers": runtime_gate.get("blockers", []),
        "required_conditions": {
            "fresh_capital_snapshot": "candidate_revenue_blockers must not contain capital_snapshot_not_fresh",
            "tradeable_market": "market_status must be TRADEABLE",
            "buy_or_sell_side": "side must be BUY or SELL",
            "net_revenue_positive": "expected_net_revenue must be positive after costs and buffers",
            "route_not_active": "lifecycle_duplicate_blocked must be false",
            "close_first_positions_covered": bool(runtime_gate.get("close_first_covered")),
            "broker_correlation_complete": bool(runtime_gate.get("broker_correlation_complete")),
            "runtime_gates_clear": live_gates_clear,
        },
        "blockers": list(dict.fromkeys(blockers)),
    }


def _build_external_confirmation_proof(ecosystem: Dict[str, Any], exchange_matrix: Dict[str, Any]) -> Dict[str, Any]:
    rows = ecosystem.get("shadow_hedges") if isinstance(ecosystem.get("shadow_hedges"), list) else []
    hedges = [row for row in rows if isinstance(row, dict)]
    leaks = [
        row
        for row in hedges
        if row.get("authority") != "shadow_only" or bool(row.get("mutation_allowed")) or bool(row.get("order_intent_allowed"))
    ]
    matrix_rows = exchange_matrix.get("rows") if isinstance(exchange_matrix.get("rows"), list) else []
    return {
        "shadow_confirmation_count": len(hedges),
        "external_shadow_only": not leaks,
        "leak_count": len(leaks),
        "leak_rows": leaks[:10],
        "exchange_matrix_rows": len(matrix_rows),
        "hedges": hedges[:12],
        "blockers": ["external_shadow_mutation_leak"] if leaks else [],
    }


def _build_close_first_proof(ecosystem: Dict[str, Any], live_dry: Dict[str, Any]) -> Dict[str, Any]:
    rows = ecosystem.get("close_first_opportunities") if isinstance(ecosystem.get("close_first_opportunities"), list) else []
    live_dry_summary = live_dry.get("summary") if isinstance(live_dry.get("summary"), dict) else {}
    close_rows = [row for row in rows if isinstance(row, dict)]
    return {
        "close_first_opportunity_count": len(close_rows),
        "recovered_position_count": _as_int(live_dry_summary.get("recovered_position_count"), 0),
        "recovered_position_close_first_covered": bool(live_dry_summary.get("recovered_position_close_first_covered")),
        "recovered_close_chain_status": live_dry_summary.get("recovered_close_chain_status") or "",
        "recovered_exit_blockers": live_dry_summary.get("recovered_exit_blockers") if isinstance(live_dry_summary.get("recovered_exit_blockers"), list) else [],
        "opportunities": close_rows[:12],
        "blockers": [] if close_rows or _as_int(live_dry_summary.get("recovered_position_count"), 0) == 0 else ["close_first_not_prioritized"],
    }


def _build_lifecycle_proof(ecosystem: Dict[str, Any], live_dry: Dict[str, Any]) -> Dict[str, Any]:
    lifecycle = ecosystem.get("lifecycle") if isinstance(ecosystem.get("lifecycle"), dict) else {}
    live_dry_summary = live_dry.get("summary") if isinstance(live_dry.get("summary"), dict) else {}
    return {
        "active_lifecycle_route_count": _as_int(live_dry_summary.get("active_lifecycle_route_count"), 0),
        "duplicate_route_blocked_count": _as_int(lifecycle.get("duplicate_route_blocked_count"), _as_int(live_dry_summary.get("duplicate_route_blocked_count"), 0)),
        "duplicate_routes_blocked": bool(live_dry_summary.get("duplicate_routes_blocked")) or _as_int(lifecycle.get("duplicate_route_blocked_count"), 0) > 0,
        "broker_correlation_complete": bool(live_dry_summary.get("broker_correlation_complete")),
        "lifecycle_continuity_complete": bool(live_dry_summary.get("lifecycle_continuity_complete")),
        "continuity_blockers": lifecycle.get("continuity_blockers") if isinstance(lifecycle.get("continuity_blockers"), list) else [],
        "active_route_keys": lifecycle.get("active_route_keys") if isinstance(lifecycle.get("active_route_keys"), list) else [],
    }


def _status_from_blockers(blockers: List[str], intent_ready_count: int) -> str:
    priority = [
        "external_shadow_mutation_leak",
        "capital_ecosystem_intelligence_missing",
        "candidate_revenue_fields_missing",
        "no_net_positive_candidates",
        "no_revenue_intent_eligible_candidates",
        "capital_order_intent_gated",
    ]
    for status in priority:
        if status in blockers:
            return status
    return "capital_revenue_logic_certified" if intent_ready_count > 0 and not blockers else "capital_revenue_logic_attention"


def build_capital_revenue_logic_stress_audit(
    *,
    root: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    now_dt = now or utc_now()
    ecosystem = _read_json(_rooted(root_path, CAPITAL_ECOSYSTEM_PATH), {})
    live_dry = _read_json(_rooted(root_path, CAPITAL_LIVE_DRY_STRESS_PATH), {})
    runtime_status = _read_json(_rooted(root_path, RUNTIME_STATUS_PATH), {})
    exchange_matrix = _read_json(_rooted(root_path, EXCHANGE_MATRIX_PATH), {})
    if not isinstance(ecosystem, dict):
        ecosystem = {}
    if not isinstance(live_dry, dict):
        live_dry = {}
    if not isinstance(runtime_status, dict):
        runtime_status = {}
    if not isinstance(exchange_matrix, dict):
        exchange_matrix = {}

    candidate_proof = _build_candidate_revenue_proof(ecosystem)
    runtime_gate = _build_runtime_gate_proof(runtime_status, live_dry)
    order_intent_readiness = _build_order_intent_readiness(candidate_proof, runtime_gate)
    external_confirmation = _build_external_confirmation_proof(ecosystem, exchange_matrix)
    close_first = _build_close_first_proof(ecosystem, live_dry)
    lifecycle = _build_lifecycle_proof(ecosystem, live_dry)

    blockers: List[str] = []
    for proof in (candidate_proof, order_intent_readiness, external_confirmation, close_first):
        blockers.extend(str(item) for item in proof.get("blockers", []) if str(item))
    blockers = list(dict.fromkeys(blockers))
    status = _status_from_blockers(blockers, _as_int(order_intent_readiness.get("intent_eligible_candidate_count"), 0))
    ecosystem_summary = ecosystem.get("summary") if isinstance(ecosystem.get("summary"), dict) else {}
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_dt.isoformat(),
        "status": status,
        "ok": status == "capital_revenue_logic_certified",
        "mode": "read_only_capital_revenue_logic_stress",
        "summary": {
            "candidate_count": _as_int(ecosystem_summary.get("candidate_count"), candidate_proof.get("checked_candidate_count", 0)),
            "trade_ready_candidate_count": _as_int(ecosystem_summary.get("trade_ready_candidate_count"), candidate_proof.get("trade_ready_candidate_count", 0)),
            "net_positive_candidate_count": candidate_proof.get("net_positive_candidate_count", 0),
            "intent_eligible_candidate_count": order_intent_readiness.get("intent_eligible_candidate_count", 0),
            "candidate_level_intent_eligible_count": order_intent_readiness.get("candidate_level_eligible_count", 0),
            "false_positive_reject_count": candidate_proof.get("false_positive_reject_count", 0),
            "active_watchlist_count": _as_int(ecosystem_summary.get("active_watchlist_count"), 0),
            "bench_watchlist_count": _as_int(ecosystem_summary.get("bench_watchlist_count"), 0),
            "close_first_opportunity_count": close_first.get("close_first_opportunity_count", 0),
            "duplicate_route_blocked_count": lifecycle.get("duplicate_route_blocked_count", 0),
            "shadow_confirmation_count": external_confirmation.get("shadow_confirmation_count", 0),
            "external_shadow_only": bool(external_confirmation.get("external_shadow_only")),
            "live_gates_blocking": bool(order_intent_readiness.get("live_gates_blocking")),
            "no_live_mutation": True,
        },
        "candidate_revenue_proof": candidate_proof,
        "net_positive_candidates": candidate_proof.get("top_net_positive_candidates", []),
        "rejected_false_positives": candidate_proof.get("rejected_false_positives", []),
        "capital_order_intent_readiness": order_intent_readiness,
        "external_confirmation_proof": external_confirmation,
        "close_first_proof": close_first,
        "lifecycle_proof": lifecycle,
        "runtime_gate_proof": runtime_gate,
        "blockers": blockers,
        "manual_boundaries": MANUAL_BOUNDARIES,
        "source_paths": {
            "capital_ecosystem": CAPITAL_ECOSYSTEM_PATH.as_posix(),
            "capital_live_dry_stress": CAPITAL_LIVE_DRY_STRESS_PATH.as_posix(),
            "runtime_status": RUNTIME_STATUS_PATH.as_posix(),
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
        "# Aureon Capital Revenue Logic Stress Audit",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Candidates: `{summary.get('candidate_count')}` trade-ready `{summary.get('trade_ready_candidate_count')}`",
        f"- Net-positive: `{summary.get('net_positive_candidate_count')}`",
        f"- Intent-eligible after gates: `{summary.get('intent_eligible_candidate_count')}`",
        f"- False-positive rejects: `{summary.get('false_positive_reject_count')}`",
        f"- Active/bench watchlist: `{summary.get('active_watchlist_count')}` / `{summary.get('bench_watchlist_count')}`",
        f"- Duplicate routes blocked: `{summary.get('duplicate_route_blocked_count')}`",
        f"- Shadow confirmations: `{summary.get('shadow_confirmation_count')}` external shadow-only `{summary.get('external_shadow_only')}`",
        f"- No live mutation: `{summary.get('no_live_mutation')}`",
        "",
        "## Top Net-Positive Candidates",
    ]
    for row in report.get("net_positive_candidates") or []:
        lines.append(
            f"- `{row.get('symbol')}` `{row.get('side')}` net `{row.get('expected_net_revenue')}` "
            f"blockers `{','.join(row.get('revenue_blockers') or []) or 'none'}`"
        )
    if not report.get("net_positive_candidates"):
        lines.append("- None visible.")
    lines.extend(["", "## Blockers"])
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- None visible.")
    return "\n".join(lines) + "\n"


def build_and_write_capital_revenue_logic_stress_audit(*, root: Optional[Path] = None) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    report = build_capital_revenue_logic_stress_audit(root=root_path)
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
    parser = argparse.ArgumentParser(description="Build Capital revenue logic stress evidence without broker mutation.")
    parser.add_argument("--repo-root", default="", help="Repository root; defaults to cwd/repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else None
    report = build_and_write_capital_revenue_logic_stress_audit(root=root)
    print(json.dumps(report, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
