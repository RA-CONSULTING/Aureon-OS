"""Capital-wide revenue intelligence built from the GOLD company pattern.

This module is evidence-only. It ranks Capital.com candidates, allocates a
rate-limit-aware watchlist, and publishes shadow hedge context from supporting
exchanges without placing orders or mutating broker state.
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from aureon.trading.order_lifecycle import candidate_id_for, lifecycle_id_for, route_key_for


SCHEMA_VERSION = "aureon-capital-ecosystem-intelligence-company-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]

CAPITAL_ASSET_REGISTRY_PATH = Path("state/aureon_capital_tradable_asset_registry.json")
EXCHANGE_DATA_MATRIX_PATH = Path("frontend/public/aureon_exchange_data_capability_matrix.json")
ORDER_LIFECYCLE_PATH = Path("state/unified_order_lifecycle_latest.json")
STREAM_CACHE_PATH = Path("ws_cache/ws_prices.json")
DEFAULT_STATE_PATH = Path("state/aureon_capital_ecosystem_intelligence_company_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_capital_ecosystem_intelligence_company.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_capital_ecosystem_intelligence_company.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_capital_ecosystem_intelligence_company.json")

ACTIVE_WATCHLIST_LIMIT = 40
BENCH_WATCHLIST_LIMIT = 100
MINIMUM_REVENUE_FLOOR = 0.03
MINIMUM_RISK_BUFFER = 0.01
SUPPORTED_ASSET_CLASSES = {"commodity_cfd", "index_cfd", "stock_cfd", "forex", "unknown"}
MANUAL_BOUNDARIES = [
    "evidence only",
    "no forced live order",
    "no external hedge order",
    "no credential read or reveal",
    "existing runtime gates remain authoritative",
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


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    try:
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        text = str(value).strip()
        if text.isdigit():
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _age_seconds(value: Any, now: datetime) -> Optional[float]:
    parsed = _parse_timestamp(value)
    if not parsed:
        return None
    return round(max(0.0, (now - parsed).total_seconds()), 3)


def _fresh_score(age_sec: Optional[float], budget_sec: float = 900.0) -> float:
    if age_sec is None:
        return 0.0
    if age_sec <= 0:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (age_sec / budget_sec)))


def _symbol_key(asset: Dict[str, Any]) -> str:
    return str(asset.get("symbol") or asset.get("epic") or "").strip()


def _active_route_keys(lifecycle_state: Dict[str, Any]) -> set[str]:
    rows = lifecycle_state.get("active_lifecycles") if isinstance(lifecycle_state.get("active_lifecycles"), list) else []
    return {
        str(row.get("route_key") or "")
        for row in rows
        if isinstance(row, dict) and str(row.get("route_key") or "")
    }


def _stream_momentum_by_symbol(stream_cache: Dict[str, Any]) -> Dict[str, float]:
    ticker_cache = stream_cache.get("ticker_cache") if isinstance(stream_cache.get("ticker_cache"), dict) else {}
    result: Dict[str, float] = {}
    for key, row in ticker_cache.items():
        if not isinstance(row, dict):
            continue
        symbol = str(row.get("symbol") or row.get("pair") or key or "").upper().replace(" ", "")
        change = _as_float(row.get("change24h"), 0.0)
        if symbol:
            result[symbol] = change
    return result


def _candidate_side(asset: Dict[str, Any], momentum: float) -> str:
    if momentum < -0.1 and bool(asset.get("can_sell", True)):
        return "SELL"
    if bool(asset.get("can_buy", True)):
        return "BUY"
    return "SELL" if bool(asset.get("can_sell", False)) else "WATCH"


def _class_bonus(asset_class: str) -> float:
    return {
        "index_cfd": 0.18,
        "commodity_cfd": 0.15,
        "forex": 0.12,
        "stock_cfd": 0.08,
        "unknown": 0.02,
    }.get(asset_class, 0.0)


def score_capital_candidate(
    asset: Dict[str, Any],
    *,
    now: Optional[datetime] = None,
    active_routes: Optional[set[str]] = None,
    stream_momentum: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    now_dt = now or utc_now()
    symbol = _symbol_key(asset)
    epic = str(asset.get("epic") or symbol).strip()
    asset_class = str(asset.get("asset_class") or "unknown").strip().lower()
    age_sec = _age_seconds(asset.get("last_snapshot_at"), now_dt)
    spread_pct = max(0.0, _as_float(asset.get("spread_pct"), 0.0))
    margin = _as_float(asset.get("margin_required_for_min_deal"), 0.0)
    min_deal = _as_float(asset.get("minimum_deal_size"), 0.0)
    mid_price = _as_float(asset.get("mid_price"), 0.0)
    trade_ready = bool(asset.get("trade_ready"))
    market_status = str(asset.get("market_status") or "").upper()
    normalized_symbol = symbol.upper().replace(" ", "")
    momentum = (stream_momentum or {}).get(normalized_symbol, 0.0)
    side = _candidate_side(asset, momentum)
    route = route_key_for("capital", "cfd", symbol, side)
    blockers: List[str] = []
    if not trade_ready:
        blockers.append("capital_asset_not_trade_ready")
    if market_status != "TRADEABLE":
        blockers.append("capital_market_not_tradeable")
    if not symbol:
        blockers.append("capital_symbol_missing")
    if mid_price <= 0:
        blockers.append("capital_price_missing")
    if min_deal <= 0:
        blockers.append("capital_minimum_deal_size_missing")
    if margin <= 0:
        blockers.append("capital_margin_unknown")
    if age_sec is None or age_sec > 900:
        blockers.append("capital_snapshot_not_fresh")
    if route in (active_routes or set()):
        blockers.append("active_lifecycle_same_route")

    freshness = _fresh_score(age_sec)
    spread_score = max(0.0, min(1.0, 1.0 - (spread_pct / 0.25)))
    margin_score = 1.0 / (1.0 + max(0.0, margin) / 250.0)
    momentum_score = min(1.0, abs(momentum) / 5.0)
    soft_rank_blockers = {"active_lifecycle_same_route", "capital_snapshot_not_fresh"}
    hard_blockers = [blocker for blocker in blockers if blocker not in soft_rank_blockers]
    readiness = 1.0 if not blockers else 0.65 if not hard_blockers else 0.0
    velocity_score = max(
        0.0,
        min(
            1.0,
            (0.38 * spread_score)
            + (0.22 * freshness)
            + (0.18 * margin_score)
            + (0.14 * momentum_score)
            + _class_bonus(asset_class),
        )
        * readiness,
    )
    minimum_move = _as_float(asset.get("spread"), 0.0) + 0.03 / max(min_deal, 0.000001)
    notional = max(0.0, mid_price * max(min_deal, 0.0))
    gross_edge = notional * min(abs(momentum), 10.0) / 100.0
    spread_cost = max(0.0, _as_float(asset.get("spread"), 0.0) * max(min_deal, 0.0))
    slippage_buffer = max(spread_cost * 0.5, notional * 0.0001)
    fee_estimate = notional * 0.00005
    financing_fee_estimate = max(margin * 0.0002, notional * 0.00005)
    risk_buffer = max(MINIMUM_RISK_BUFFER, gross_edge * 0.10)
    expected_net_revenue = (
        gross_edge
        - spread_cost
        - slippage_buffer
        - fee_estimate
        - financing_fee_estimate
        - risk_buffer
        - MINIMUM_REVENUE_FLOOR
    )
    expected_time_to_profit_sec = max(5.0, 300.0 / (1.0 + abs(momentum)))
    revenue_blockers = list(blockers)
    if side not in {"BUY", "SELL"}:
        revenue_blockers.append("order_side_not_buy_or_sell")
    if gross_edge <= 0:
        revenue_blockers.append("gross_edge_missing")
    if expected_net_revenue <= 0:
        revenue_blockers.append("expected_net_revenue_not_positive")
    net_revenue_positive = expected_net_revenue > 0
    revenue_intent_eligible = bool(net_revenue_positive and not revenue_blockers and side in {"BUY", "SELL"})
    generated_hint = asset.get("last_snapshot_at") or now_dt.isoformat()
    candidate_id = candidate_id_for(symbol, side, generated_hint, "capital_ecosystem")
    return {
        "candidate_id": candidate_id,
        "proposed_lifecycle_id": lifecycle_id_for("capital-ecosystem", route, candidate_id),
        "route_key": route,
        "symbol": symbol,
        "epic": epic,
        "instrument_name": asset.get("instrument_name") or symbol,
        "asset_class": asset_class,
        "side": side,
        "authority": "runtime_gated_capital_candidate",
        "trade_ready": trade_ready,
        "market_status": market_status,
        "snapshot_age_sec": age_sec,
        "freshness_score": round(freshness, 6),
        "fast_profit_velocity_score": round(velocity_score, 6),
        "spread_pct": round(spread_pct, 8),
        "spread": _as_float(asset.get("spread"), 0.0),
        "minimum_deal_size": min_deal,
        "margin_required_for_min_deal": margin,
        "minimum_move_for_3p": round(minimum_move, 6),
        "mid_price": mid_price,
        "momentum_proxy_change24h": round(momentum, 6),
        "gross_edge": round(gross_edge, 8),
        "spread_cost": round(spread_cost, 8),
        "slippage_buffer": round(slippage_buffer, 8),
        "fee_estimate": round(fee_estimate, 8),
        "financing_fee_estimate": round(financing_fee_estimate, 8),
        "risk_buffer": round(risk_buffer, 8),
        "minimum_revenue_floor": MINIMUM_REVENUE_FLOOR,
        "expected_time_to_profit_sec": round(expected_time_to_profit_sec, 3),
        "expected_net_revenue": round(expected_net_revenue, 8),
        "net_revenue_positive": net_revenue_positive,
        "revenue_intent_eligible": revenue_intent_eligible,
        "revenue_blockers": list(dict.fromkeys(revenue_blockers)),
        "lifecycle_duplicate_blocked": route in (active_routes or set()),
        "blockers": blockers,
        "order_intent_allowed": False,
        "order_intent_blocker": "existing_runtime_gate_required",
    }


def allocate_watchlists(candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    ranked = sorted(candidates, key=lambda row: _as_float(row.get("fast_profit_velocity_score"), 0.0), reverse=True)
    active = ranked[:ACTIVE_WATCHLIST_LIMIT]
    gold = next((row for row in ranked if str(row.get("symbol") or "").upper() == "GOLD"), None)
    if gold and all(row.get("candidate_id") != gold.get("candidate_id") for row in active):
        active = ([gold] + active)[:ACTIVE_WATCHLIST_LIMIT]
    bench = ranked[:BENCH_WATCHLIST_LIMIT]
    return {
        "active_stream_watchlist": active,
        "bench_watchlist": bench,
        "active_symbols": [row.get("symbol") for row in active],
        "bench_symbols": [row.get("symbol") for row in bench],
        "active_limit": ACTIVE_WATCHLIST_LIMIT,
        "bench_limit": BENCH_WATCHLIST_LIMIT,
    }


def build_shadow_hedges(candidates: List[Dict[str, Any]], exchange_matrix: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = exchange_matrix.get("rows") if isinstance(exchange_matrix.get("rows"), list) else []
    exchange_state = {
        str(row.get("exchange") or ""): row.get("current_state") if isinstance(row, dict) and isinstance(row.get("current_state"), dict) else {}
        for row in rows
        if isinstance(row, dict)
    }
    hedges: List[Dict[str, Any]] = []
    for candidate in candidates[:12]:
        asset_class = str(candidate.get("asset_class") or "")
        if asset_class == "stock_cfd":
            source = "alpaca"
            rationale = "equity and ETF confirmation hedge pressure"
        elif asset_class in {"commodity_cfd", "index_cfd", "forex"}:
            source = "binance"
            rationale = "crypto liquidity and risk-on/risk-off hedge pressure"
        else:
            source = "kraken"
            rationale = "cross-venue liquidity hedge pressure"
        state = exchange_state.get(source, {})
        confidence = min(1.0, 0.35 + (0.35 if state.get("fresh_feed") else 0.0) + (0.15 if state.get("decision_fed") else 0.0))
        blockers = ["external_hedge_order_mutation_blocked"]
        if not state.get("fresh_feed"):
            blockers.append(f"{source}_feed_not_fresh")
        hedges.append(
            {
                "hedge_candidate_id": f"hedge-{candidate.get('candidate_id')}",
                "source_exchange": source,
                "target_candidate_id": candidate.get("candidate_id"),
                "target_symbol": candidate.get("symbol"),
                "target_route_key": candidate.get("route_key"),
                "hedge_side": "SELL" if candidate.get("side") == "BUY" else "BUY",
                "hedge_confidence": round(confidence, 6),
                "hedge_rationale": rationale,
                "authority": "shadow_only",
                "mutation_allowed": False,
                "order_intent_allowed": False,
                "hedge_blockers": blockers,
            }
        )
    return hedges


def build_close_first_opportunities(lifecycle_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = lifecycle_state.get("active_lifecycles") if isinstance(lifecycle_state.get("active_lifecycles"), list) else []
    opportunities: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or str(row.get("venue") or "").lower() != "capital":
            continue
        opportunities.append(
            {
                "lifecycle_id": row.get("lifecycle_id"),
                "route_key": row.get("route_key"),
                "symbol": row.get("symbol"),
                "deal_id": row.get("deal_id"),
                "current_status": row.get("current_status"),
                "last_pnl": row.get("last_pnl"),
                "close_priority": "monitor_existing_position",
                "close_allowed": False,
                "blockers": ["existing_runtime_close_gate_required"],
            }
        )
    return opportunities[:20]


def build_capital_ecosystem_intelligence_company(
    *,
    root: Optional[Path] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    now_dt = now or utc_now()
    registry = _read_json(_rooted(root_path, CAPITAL_ASSET_REGISTRY_PATH), {})
    exchange_matrix = _read_json(_rooted(root_path, EXCHANGE_DATA_MATRIX_PATH), {})
    lifecycle_state = _read_json(_rooted(root_path, ORDER_LIFECYCLE_PATH), {})
    stream_cache = _read_json(_rooted(root_path, STREAM_CACHE_PATH), {})
    assets = registry.get("assets") if isinstance(registry.get("assets"), list) else []
    active_routes = _active_route_keys(lifecycle_state if isinstance(lifecycle_state, dict) else {})
    momentum = _stream_momentum_by_symbol(stream_cache if isinstance(stream_cache, dict) else {})
    candidates = [
        score_capital_candidate(asset, now=now_dt, active_routes=active_routes, stream_momentum=momentum)
        for asset in assets
        if isinstance(asset, dict) and str(asset.get("asset_class") or "unknown").lower() in SUPPORTED_ASSET_CLASSES
    ]
    candidates = sorted(candidates, key=lambda row: _as_float(row.get("fast_profit_velocity_score"), 0.0), reverse=True)
    watchlists = allocate_watchlists(candidates)
    active = watchlists["active_stream_watchlist"]
    hedges = build_shadow_hedges(active, exchange_matrix if isinstance(exchange_matrix, dict) else {})
    close_first = build_close_first_opportunities(lifecycle_state if isinstance(lifecycle_state, dict) else {})
    blockers: List[str] = []
    if not assets:
        blockers.append("capital_asset_registry_missing")
    if not active:
        blockers.append("capital_watchlist_empty")
    if len(active) > ACTIVE_WATCHLIST_LIMIT:
        blockers.append("capital_active_watchlist_over_limit")
    if any(row.get("mutation_allowed") for row in hedges):
        blockers.append("external_hedge_mutation_leak")
    net_positive_count = sum(1 for row in candidates if row.get("net_revenue_positive"))
    revenue_intent_count = sum(1 for row in candidates if row.get("revenue_intent_eligible"))
    false_positive_reject_count = sum(
        1
        for row in candidates
        if _as_float(row.get("gross_edge"), 0.0) > 0
        and (
            not bool(row.get("net_revenue_positive"))
            or bool(row.get("revenue_blockers"))
            or bool(row.get("lifecycle_duplicate_blocked"))
        )
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_dt.isoformat(),
        "status": "capital_ecosystem_intelligence_ready" if not blockers else "capital_ecosystem_intelligence_attention",
        "mode": "read_only_capital_ecosystem_revenue_intelligence",
        "goal": {
            "primary_execution_venue": "Capital.com",
            "ranking": "fast_profit_velocity",
            "universe": "ranked_capital_watchlist",
            "hedge_authority": "shadow_only",
        },
        "summary": {
            "candidate_count": len(candidates),
            "trade_ready_candidate_count": sum(1 for row in candidates if row.get("trade_ready")),
            "net_positive_candidate_count": net_positive_count,
            "revenue_intent_candidate_count": revenue_intent_count,
            "false_positive_reject_count": false_positive_reject_count,
            "active_watchlist_count": len(active),
            "active_watchlist_limit": ACTIVE_WATCHLIST_LIMIT,
            "bench_watchlist_count": len(watchlists["bench_watchlist"]),
            "bench_watchlist_limit": BENCH_WATCHLIST_LIMIT,
            "gold_preserved": any(str(row.get("symbol") or "").upper() == "GOLD" for row in active),
            "shadow_hedge_count": len(hedges),
            "shadow_hedges_only": all(row.get("authority") == "shadow_only" and not row.get("mutation_allowed") for row in hedges),
            "close_first_opportunity_count": len(close_first),
            "active_lifecycle_route_count": len(active_routes),
            "top_velocity_score": active[0].get("fast_profit_velocity_score") if active else 0.0,
            "blocker_count": len(blockers),
            "no_external_hedge_mutation": True,
            "existing_runtime_gates_authoritative": True,
        },
        "watchlists": watchlists,
        "top_velocity_candidates": active[:20],
        "shadow_hedges": hedges,
        "close_first_opportunities": close_first,
        "lifecycle": {
            "path": ORDER_LIFECYCLE_PATH.as_posix(),
            "active_route_keys": sorted(active_routes),
            "duplicate_route_blocked_count": sum(1 for row in candidates if row.get("lifecycle_duplicate_blocked")),
            "continuity_blockers": lifecycle_state.get("continuity_blockers", []) if isinstance(lifecycle_state, dict) else [],
        },
        "source_paths": {
            "capital_asset_registry": CAPITAL_ASSET_REGISTRY_PATH.as_posix(),
            "exchange_data_matrix": EXCHANGE_DATA_MATRIX_PATH.as_posix(),
            "order_lifecycle": ORDER_LIFECYCLE_PATH.as_posix(),
            "stream_cache": STREAM_CACHE_PATH.as_posix(),
        },
        "blockers": blockers,
        "manual_boundaries": MANUAL_BOUNDARIES,
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
        "# Aureon Capital Ecosystem Intelligence Company",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Candidates: `{summary.get('candidate_count')}`",
        f"- Net-positive candidates: `{summary.get('net_positive_candidate_count')}`",
        f"- Revenue-intent candidates: `{summary.get('revenue_intent_candidate_count')}`",
        f"- False-positive rejects: `{summary.get('false_positive_reject_count')}`",
        f"- Active watchlist: `{summary.get('active_watchlist_count')}/{summary.get('active_watchlist_limit')}`",
        f"- Bench watchlist: `{summary.get('bench_watchlist_count')}/{summary.get('bench_watchlist_limit')}`",
        f"- Shadow hedges: `{summary.get('shadow_hedge_count')}`",
        f"- Close-first opportunities: `{summary.get('close_first_opportunity_count')}`",
        f"- No external hedge mutation: `{summary.get('no_external_hedge_mutation')}`",
        "",
        "## Top Candidates",
    ]
    for row in report.get("top_velocity_candidates") or []:
        lines.append(
            f"- `{row.get('symbol')}` `{row.get('side')}` score `{row.get('fast_profit_velocity_score')}` "
            f"net `{row.get('expected_net_revenue')}`"
        )
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    lines.extend(["", "## Blockers"])
    lines.extend(f"- `{blocker}`" for blocker in blockers) if blockers else lines.append("- None visible.")
    return "\n".join(lines) + "\n"


def build_and_write_capital_ecosystem_intelligence_company(*, root: Optional[Path] = None) -> Dict[str, Any]:
    root_path = Path(root or _default_root()).resolve()
    report = build_capital_ecosystem_intelligence_company(root=root_path)
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
    parser = argparse.ArgumentParser(description="Build Capital-wide ecosystem intelligence without broker mutation.")
    parser.add_argument("--repo-root", default="", help="Repository root; defaults to cwd/repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else None
    report = build_and_write_capital_ecosystem_intelligence_company(root=root)
    print(json.dumps(report, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
