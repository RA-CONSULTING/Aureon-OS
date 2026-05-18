"""Exchange data capability matrix for Aureon.

This report answers which exchange gets which data, what the system can use it
for, and how the call budget should be optimized without starving execution,
position, balance, or recovery paths.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from aureon.autonomous.aureon_data_ocean import evaluate_data_ocean_sources
from aureon.autonomous.aureon_exchange_monitoring_checklist import (
    EXCHANGE_REQUIREMENTS,
    build_exchange_monitoring_checklist,
)
from aureon.autonomous.runtime_status_source import read_runtime_status
from aureon.core.exchange_rate_limit_registry import (
    build_cash_aware_rate_plan,
    get_exchange_rate_limit,
)


SCHEMA_VERSION = "aureon-exchange-data-capability-matrix-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_STATUS_PATH = Path("state/unified_runtime_status.json")
DATA_OCEAN_STATUS_PATH = Path("state/aureon_data_ocean_status.json")
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs/audits/aureon_exchange_data_capability_matrix.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs/audits/aureon_exchange_data_capability_matrix.md"
DEFAULT_PUBLIC_JSON = REPO_ROOT / "frontend/public/aureon_exchange_data_capability_matrix.json"


EXCHANGE_CAPABILITY_MAP: dict[str, dict[str, Any]] = {
    "binance": {
        "label": "Binance",
        "system_role": "Crypto breadth scanner and spot execution route.",
        "trading_modes": ["crypto_spot", "margin_route_planning_if_account_supported"],
        "data_channels": [
            ("live_ticks", "all-market stream/cache and REST gap fill", "fast-money candidate discovery"),
            ("order_book_pressure", "public order-book probes", "spread, imbalance, and momentum confirmation"),
            ("symbol_filters", "exchange info / symbol rules", "min notional, quantity step, precision validation"),
            ("balances", "private account balance where configured", "cash-aware routing and capital allocation"),
            ("orders_and_fills", "private order/fill history where configured", "execution learning and cost basis"),
            ("waveform_history", "global history database", "1h-to-1y pattern memory"),
        ],
        "leveraged_for": [
            "wide crypto market scan",
            "idle-cash market discovery",
            "cross-exchange confirmation",
            "symbol/filter validation before intent publication",
        ],
        "optimization_bias": "Prefer WebSocket/live cache for breadth; reserve REST request weight for account, order, and exchangeInfo checks.",
    },
    "kraken": {
        "label": "Kraken",
        "system_role": "Crypto spot, margin, collateral, and cost-aware execution route.",
        "trading_modes": ["crypto_spot", "crypto_margin"],
        "data_channels": [
            ("live_ticks", "public ticker/cache", "spot and margin candidate discovery"),
            ("order_book_pressure", "public order-book probes", "entry/exit pressure validation"),
            ("balances", "private Balance/TradeBalance", "collateral, available cash, and risk sizing"),
            ("margin_context", "margin pair/collateral state", "margin-only routing when spot capital is locked or negative"),
            ("fees_and_costs", "fee/cost context", "break-even and dead-man profit-capture validation"),
            ("trade_history", "private TradesHistory/Ledgers when budget permits", "real fill learning and cost-basis memory"),
            ("waveform_history", "global history database", "1h-to-1y crypto waveform memory"),
        ],
        "leveraged_for": [
            "spot versus margin route comparison",
            "collateral protection",
            "cost-aware first-profitable-exit logic",
            "cross-venue crypto confirmation",
        ],
        "optimization_bias": "Keep private history sync slow because Kraken history calls are counter-expensive; use public streams/probes for live market discovery.",
    },
    "alpaca": {
        "label": "Alpaca",
        "system_role": "US equities, ETFs, crypto snapshots, market-hours, and portfolio route.",
        "trading_modes": ["stocks", "etfs", "crypto_spot_if_enabled"],
        "data_channels": [
            ("live_ticks", "stock/ETF/crypto snapshot or stream", "equity and ETF candidate discovery"),
            ("market_hours", "clock and calendar state", "only act when the instrument is tradable"),
            ("balances", "account equity, cash, buying power", "capital-aware routing"),
            ("positions", "open positions and P/L", "quick exit and exposure control"),
            ("orders_and_fills", "orders/activities", "execution learning"),
            ("historical_bars", "market-data historical API", "1h-to-1y stock/ETF waveform memory"),
            ("news_context", "market-data news when entitled", "headline and sentiment confirmation"),
        ],
        "leveraged_for": [
            "stock/ETF volatility scan",
            "market-hours aware route selection",
            "equity-to-crypto context",
            "portfolio cash deployment when available",
        ],
        "optimization_bias": "Use one stream endpoint where possible; spend historical API budget on batch backfills, not repeated single-symbol polling.",
    },
    "capital": {
        "label": "Capital.com",
        "system_role": "CFD, FX, indices, equities, open-position P/L, and quick-profit close route.",
        "trading_modes": ["cfds", "forex", "indices", "equity_cfds"],
        "data_channels": [
            ("live_ticks", "REST/WebSocket market snapshots", "CFD/FX/index candidate discovery"),
            ("positions", "open position and deal confirmation state", "profit capture and dead-man exit decisions"),
            ("balances", "account balance/equity", "cash-aware routing and exposure control"),
            ("market_hours", "instrument hours and session state", "avoid closed-market intent"),
            ("leverage_preferences", "account preferences where available", "instrument risk and size validation"),
            ("price_history", "Capital history endpoint", "CFD/FX/index waveform memory"),
        ],
        "leveraged_for": [
            "fast profitable-position closure",
            "FX/index/equity CFD cross-asset context",
            "40-instrument WebSocket watchlist optimization",
            "market-hours-aware revenue capture",
        ],
        "optimization_bias": "Use the 40-instrument stream for active high-volatility targets; reserve REST for positions, confirmations, and session health.",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "fresh", "ready", "active"}
    return bool(value)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _source_for_exchange(data_ocean: dict[str, Any], exchange: str) -> dict[str, Any]:
    sources = data_ocean.get("sources") if isinstance(data_ocean.get("sources"), list) else []
    expected_id = f"{exchange}_live"
    for source in sources:
        if isinstance(source, dict) and source.get("source_id") == expected_id:
            return source
    return {}


def _monitor_for_exchange(checklist: dict[str, Any], exchange: str) -> dict[str, Any]:
    rows = checklist.get("rows") if isinstance(checklist.get("rows"), list) else []
    for row in rows:
        if isinstance(row, dict) and row.get("exchange") == exchange:
            return row
    return {}


def _channel_status(name: str, monitor: dict[str, Any], ocean_source: dict[str, Any]) -> str:
    monitored = {str(item) for item in monitor.get("monitored_now", []) if item}
    missing = {str(item) for item in monitor.get("missing", []) if item}
    if name == "live_ticks":
        if _as_bool(monitor.get("cache_fresh")) and _as_float(monitor.get("ticker_count"), 0.0) > 0:
            return "fresh"
        if _as_bool(monitor.get("cache_active")):
            return "active_stale"
        return "missing"
    if name == "order_book_pressure":
        if "orderbook_pressure" in monitored or "orderbook_probe" in monitored:
            return "active"
        return "held" if any("orderbook" in item for item in missing) else "available_to_probe"
    if name == "waveform_history":
        return "active" if _as_bool(monitor.get("waveform_history_active")) else "missing"
    if name in {"balances", "positions", "margin_context", "orders_and_fills", "trade_history", "fees_and_costs"}:
        if ocean_source.get("credential_state") == "configured" or _as_bool(monitor.get("connected")):
            return "configured"
        return "credential_required"
    if name in {"market_hours", "symbol_filters", "leverage_preferences", "price_history", "historical_bars", "news_context"}:
        return "available" if ocean_source.get("configured_reachable") is not False else "needs_source"
    return "mapped"


def _next_optimization(exchange: str, monitor: dict[str, Any], cash_plan: dict[str, Any], source: dict[str, Any]) -> str:
    if not _as_bool(monitor.get("connected")):
        return "Configure and validate this exchange client before assigning scan or execution budget."
    if not _as_bool(monitor.get("cache_active")):
        return "Activate the live stream/cache path so the venue contributes fresh market data."
    if not _as_bool(monitor.get("cache_fresh")):
        return "Refresh the live feed and keep execution held until the runtime says fresh."
    if cash_plan.get("data_boost_eligible"):
        return "Use this idle/no-cash venue for wider market discovery, quote probes, and cross-exchange confirmation."
    if exchange == "kraken":
        return "Reserve private calls for balances, collateral, and execution; keep history sync capped and favor public streams."
    if exchange == "capital":
        return "Prioritize open-position P/L, confirmations, and a 40-instrument high-volatility watchlist."
    if exchange == "alpaca":
        return "Use stream/snapshot data for market-hours candidates and batch historical calls for waveform memory."
    if exchange == "binance":
        return "Use stream breadth for crypto discovery and REST weight for filters, account checks, and execution recovery."
    return str(source.get("next_action") or "Maintain cash-aware call budget and source freshness.")


def _row(exchange: str, *, runtime: dict[str, Any], checklist: dict[str, Any], data_ocean: dict[str, Any]) -> dict[str, Any]:
    static = EXCHANGE_CAPABILITY_MAP[exchange]
    monitor = _monitor_for_exchange(checklist, exchange)
    source = _source_for_exchange(data_ocean, exchange)
    cash_plan = build_cash_aware_rate_plan(runtime, exchange=exchange).get(exchange, {})
    profile = get_exchange_rate_limit(exchange)
    official = profile.to_public_dict() if profile else {}
    data_channels = [
        {
            "name": name,
            "source": source_name,
            "status": _channel_status(name, monitor, source),
            "optimization_use": optimization_use,
        }
        for name, source_name, optimization_use in static["data_channels"]
    ]
    gaps = list(monitor.get("missing", []) or [])
    if _as_bool(runtime.get("stale")):
        gaps.append("runtime_stale")
    if _as_bool(runtime.get("booting")):
        gaps.append("runtime_booting")
    if runtime.get("trading_ready") is False:
        gaps.append("trading_not_ready")
    if runtime.get("data_ready") is False:
        gaps.append("data_not_ready")
    if source.get("credential_state") == "missing":
        gaps.append("live_source_credentials_missing")
    if source.get("decision_blocker"):
        gaps.append(str(source.get("decision_blocker")))
    gaps = sorted(dict.fromkeys(str(item) for item in gaps if item))
    return {
        "exchange": exchange,
        "label": static["label"],
        "system_role": static["system_role"],
        "markets": EXCHANGE_REQUIREMENTS.get(exchange, {}).get("markets", []),
        "trading_modes": static["trading_modes"],
        "data_channels": data_channels,
        "leveraged_for": static["leveraged_for"],
        "optimization_bias": static["optimization_bias"],
        "current_state": {
            "connected": _as_bool(monitor.get("connected")),
            "active_feed": _as_bool(monitor.get("cache_active")),
            "fresh_feed": _as_bool(monitor.get("cache_fresh")),
            "ticker_count": int(_as_float(monitor.get("ticker_count"), 0.0)),
            "decision_fed": _as_bool(monitor.get("feeds_decision_logic")),
            "fast_money_usable": _as_bool(monitor.get("usable_for_fast_money")),
            "waveform_history_active": _as_bool(monitor.get("waveform_history_active")),
            "credential_state": source.get("credential_state", "unknown"),
            "usable_for_mapping": _as_bool(source.get("usable_for_mapping")),
            "usable_for_decision": _as_bool(source.get("usable_for_decision")),
        },
        "official_rate_limit": official,
        "optimization_policy": {
            "safe_calls_per_min": cash_plan.get("safe_calls_per_min"),
            "execution_reserved_per_min": cash_plan.get("execution_reserved_per_min"),
            "market_data_budget_per_min": cash_plan.get("market_data_budget_per_min"),
            "cash_usd_estimate": cash_plan.get("cash_usd_estimate"),
            "position_count": cash_plan.get("position_count"),
            "cash_or_position_active": cash_plan.get("cash_or_position_active"),
            "data_boost_eligible": cash_plan.get("data_boost_eligible"),
            "stream_preferred": cash_plan.get("stream_preferred"),
            "recommended_mode": cash_plan.get("recommended_mode"),
        },
        "gaps": gaps,
        "next_optimization": _next_optimization(exchange, monitor, cash_plan, source),
        "evidence": {
            "monitoring": "docs/audits/aureon_exchange_monitoring_checklist.json",
            "data_ocean": "state/aureon_data_ocean_status.json",
            "runtime": "state/unified_runtime_status.json",
            "rate_limit_registry": "aureon/core/exchange_rate_limit_registry.py",
        },
    }


def _summary(rows: list[dict[str, Any]], runtime: dict[str, Any]) -> dict[str, Any]:
    data_boost = [row for row in rows if row.get("optimization_policy", {}).get("data_boost_eligible")]
    cash_active = [row for row in rows if row.get("optimization_policy", {}).get("cash_or_position_active")]
    return {
        "exchange_count": len(rows),
        "connected_exchange_count": sum(1 for row in rows if row["current_state"]["connected"]),
        "fresh_feed_count": sum(1 for row in rows if row["current_state"]["fresh_feed"]),
        "decision_fed_count": sum(1 for row in rows if row["current_state"]["decision_fed"]),
        "fast_money_usable_count": sum(1 for row in rows if row["current_state"]["fast_money_usable"]),
        "waveform_ready_count": sum(1 for row in rows if row["current_state"]["waveform_history_active"]),
        "cash_active_exchange_count": len(cash_active),
        "data_boost_eligible_count": len(data_boost),
        "official_rate_limit_profile_count": sum(1 for row in rows if row.get("official_rate_limit")),
        "total_ticker_count": sum(int(row["current_state"]["ticker_count"]) for row in rows),
        "runtime_stale": _as_bool(runtime.get("stale")),
        "runtime_booting": _as_bool(runtime.get("booting")),
        "trading_ready": _as_bool(runtime.get("trading_ready")),
        "data_ready": _as_bool(runtime.get("data_ready")),
        "preflight_overall": runtime.get("preflight_overall", ""),
        "stale_reason": runtime.get("stale_reason", ""),
        "top_optimizations": [
            {
                "exchange": row["exchange"],
                "mode": row.get("optimization_policy", {}).get("recommended_mode"),
                "next_optimization": row.get("next_optimization"),
            }
            for row in rows
        ],
    }


def build_exchange_data_capability_matrix(root: Optional[Path] = None) -> dict[str, Any]:
    root = (root or REPO_ROOT).resolve()
    runtime = read_runtime_status(root)
    if not isinstance(runtime, dict):
        runtime = {}
    checklist = build_exchange_monitoring_checklist(root)
    data_ocean = _read_json(root / DATA_OCEAN_STATUS_PATH, {})
    if os.getenv("AUREON_EXCHANGE_MATRIX_LIVE_DATA_OCEAN", "").strip() == "1":
        try:
            data_ocean = evaluate_data_ocean_sources(root=root, runtime=runtime, exchange_checklist=checklist)
        except Exception:
            if not isinstance(data_ocean, dict):
                data_ocean = {}
    if not isinstance(data_ocean, dict):
        data_ocean = {}
    rows = [
        _row(exchange, runtime=runtime, checklist=checklist, data_ocean=data_ocean)
        for exchange in ("binance", "kraken", "alpaca", "capital")
    ]
    summary = _summary(rows, runtime)
    status = "exchange_data_capability_matrix_ready"
    if summary["runtime_stale"]:
        status = "exchange_data_capability_matrix_connected_guarded_runtime_stale"
    elif summary["runtime_booting"] or not summary["trading_ready"] or not summary["data_ready"]:
        status = "exchange_data_capability_matrix_connected_guarded_runtime_not_ready"
    elif summary["fresh_feed_count"] < summary["exchange_count"]:
        status = "exchange_data_capability_matrix_ready_with_gaps"
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": status,
        "repo_root": str(root),
        "summary": summary,
        "contract": {
            "purpose": "Show what each exchange can see, trade, leverage for intelligence, and optimize under official provider limits.",
            "source_of_truth": "runtime status, exchange monitoring checklist, data ocean source registry, and official exchange rate-limit registry",
            "no_execution_change": "This matrix is visibility and optimization guidance only; it does not bypass exchange, runtime, credential, rate, stale-data, or order gates.",
        },
        "rows": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    lines = [
        "# Aureon Exchange Data Capability Matrix",
        "",
        f"- Generated: {report.get('generated_at', '')}",
        f"- Status: {report.get('status', '')}",
        f"- Connected exchanges: {summary.get('connected_exchange_count', 0)}/{summary.get('exchange_count', 0)}",
        f"- Fresh feeds: {summary.get('fresh_feed_count', 0)}/{summary.get('exchange_count', 0)}",
        f"- Decision-fed exchanges: {summary.get('decision_fed_count', 0)}/{summary.get('exchange_count', 0)}",
        f"- Data-boost eligible exchanges: {summary.get('data_boost_eligible_count', 0)}",
        f"- Cash/position-active exchanges: {summary.get('cash_active_exchange_count', 0)}",
        f"- Runtime booting: {summary.get('runtime_booting', False)}",
        f"- Trading/data ready: {summary.get('trading_ready', False)}/{summary.get('data_ready', False)}",
        f"- Preflight: {summary.get('preflight_overall', '')}",
        "",
        "| Exchange | Trading modes | Fresh | Decision fed | Safe calls/min | Market data/min | Optimizer | Gaps |",
        "| --- | --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in rows:
        policy = row.get("optimization_policy", {}) if isinstance(row.get("optimization_policy"), dict) else {}
        state = row.get("current_state", {}) if isinstance(row.get("current_state"), dict) else {}
        lines.append(
            "| {exchange} | {modes} | {fresh} | {fed} | {safe} | {market} | {next} | {gaps} |".format(
                exchange=row.get("label", row.get("exchange", "")),
                modes=", ".join(str(item) for item in row.get("trading_modes", [])[:4]).replace("|", "/"),
                fresh=state.get("fresh_feed", False),
                fed=state.get("decision_fed", False),
                safe=policy.get("safe_calls_per_min", ""),
                market=policy.get("market_data_budget_per_min", ""),
                next=str(row.get("next_optimization", "")).replace("|", "/"),
                gaps=", ".join(str(item) for item in row.get("gaps", [])[:5]).replace("|", "/"),
            )
        )
    lines.extend(["", "This matrix is evidence-only and does not place orders."])
    return "\n".join(lines) + "\n"


def write_exchange_data_capability_matrix(
    report: dict[str, Any],
    output_json: Path = DEFAULT_OUTPUT_JSON,
    output_md: Path = DEFAULT_OUTPUT_MD,
    public_json: Path = DEFAULT_PUBLIC_JSON,
) -> tuple[Path, Path, Path]:
    _write_json(output_json, report)
    _write_json(public_json, report)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(report), encoding="utf-8")
    return output_json, output_md, public_json


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Aureon's exchange data capability matrix.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="Audit JSON path.")
    parser.add_argument("--md", default=str(DEFAULT_OUTPUT_MD), help="Audit Markdown path.")
    parser.add_argument("--public-json", default=str(DEFAULT_PUBLIC_JSON), help="Frontend public JSON path.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    report = build_exchange_data_capability_matrix(root)
    output_json, output_md, public_json = write_exchange_data_capability_matrix(
        report,
        Path(args.json),
        Path(args.md),
        Path(args.public_json),
    )
    print(
        json.dumps(
            {
                "json": str(output_json),
                "md": str(output_md),
                "public_json": str(public_json),
                "summary": report["summary"],
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
