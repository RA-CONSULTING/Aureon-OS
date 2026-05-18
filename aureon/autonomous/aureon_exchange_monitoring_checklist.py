"""Exchange monitoring checklist for live trading evidence.

This report answers a practical operator question: for each exchange, what
market evidence is Aureon monitoring right now, and what is still missing
before that venue is useful in the trading decision path.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

from aureon.autonomous.runtime_status_source import read_runtime_status


SCHEMA_VERSION = "aureon-exchange-monitoring-checklist-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_STATUS_PATH = Path("state/unified_runtime_status.json")
STREAM_CACHE_PATH = Path("ws_cache/ws_prices.json")
WAVEFORM_RECORDER_PATH = Path("state/aureon_live_waveform_recorder.json")
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs/audits/aureon_exchange_monitoring_checklist.json"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs/audits/aureon_exchange_monitoring_checklist.md"
DEFAULT_PUBLIC_JSON = REPO_ROOT / "frontend/public/aureon_exchange_monitoring_checklist.json"


EXCHANGE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "binance": {
        "label": "Binance",
        "ready_key": "binance_ready",
        "markets": ["crypto_spot", "crypto_quote_universe"],
        "expected_channels": [
            "all_market_24h_tickers",
            "ticker_cache",
            "price_cache",
            "volume_and_change",
            "live_stream_or_rest_gap_fill",
            "waveform_history",
        ],
        "required_for_fast_money": ["fresh_tickers", "volume", "change24h", "decision_cache"],
    },
    "kraken": {
        "label": "Kraken",
        "ready_key": "kraken_ready",
        "markets": ["crypto_spot", "crypto_margin", "portfolio_balance"],
        "expected_channels": [
            "public_ticker_snapshot",
            "spot_pair_quotes",
            "margin_pair_quotes",
            "portfolio_balance",
            "cost_and_fee_context",
            "waveform_history",
        ],
        "required_for_fast_money": ["fresh_tickers", "spot_margin_context", "fees", "collateral_context"],
    },
    "alpaca": {
        "label": "Alpaca",
        "ready_key": "alpaca_ready",
        "markets": ["stocks", "etfs", "crypto_if_enabled", "portfolio_balance"],
        "expected_channels": [
            "stock_snapshot",
            "latest_trade_or_quote",
            "market_hours_state",
            "portfolio_balance",
            "news_context_if_available",
            "waveform_history",
        ],
        "required_for_fast_money": ["fresh_equity_quotes", "market_hours", "tradability_state"],
    },
    "capital": {
        "label": "Capital.com",
        "ready_key": "capital_ready",
        "markets": ["cfd_indices", "cfd_fx", "cfd_equities", "open_positions"],
        "expected_channels": [
            "capital_market_snapshot",
            "open_position_context",
            "profit_loss_context",
            "market_hours_state",
            "portfolio_balance",
            "waveform_history",
        ],
        "required_for_fast_money": ["fresh_cfd_quotes", "position_profit_state", "market_hours"],
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


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isfinite(number):
            return number
    except Exception:
        pass
    return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(_as_float(value, default))
    except Exception:
        return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "ready", "fresh"}
    return bool(value)


def _timestamp_age_sec(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return max(0.0, time.time() - _as_float(value))
    if isinstance(value, str):
        try:
            text = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return max(0.0, (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds())
        except Exception:
            return None
    return None


def _cache_source_health(stream_cache: dict[str, Any]) -> dict[str, Any]:
    health = stream_cache.get("source_health")
    if isinstance(health, dict):
        return health
    return {}


def _runtime_source_health(runtime: dict[str, Any]) -> dict[str, Any]:
    live_cache = runtime.get("live_stream_cache")
    if not isinstance(live_cache, dict):
        return {}
    health = live_cache.get("exchange_source_health")
    if isinstance(health, dict):
        return health
    return {}


def _recorder_source_health(recorder: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(recorder, dict) or not _as_bool(recorder.get("usable_for_waveform_memory")):
        return {}
    age = _timestamp_age_sec(recorder.get("cache_generated_at") or recorder.get("generated_at"))
    if age is not None and age > 300:
        return {}
    health = recorder.get("source_health")
    if isinstance(health, dict):
        return health
    return {}


def _best_source_health(*sources: dict[str, Any], exchange: str) -> dict[str, Any]:
    selected: dict[str, Any] = {}
    for source in sources:
        candidate = source.get(exchange) if isinstance(source, dict) else None
        if not isinstance(candidate, dict):
            continue
        if not selected:
            selected.update(candidate)
            continue
        candidate_active = _as_bool(candidate.get("active"))
        candidate_fresh = _as_bool(candidate.get("fresh"))
        selected_active = _as_bool(selected.get("active"))
        selected_fresh = _as_bool(selected.get("fresh"))
        if (candidate_active and not selected_active) or (candidate_fresh and not selected_fresh):
            selected.update(candidate)
            continue
        for key, value in candidate.items():
            selected.setdefault(key, value)
    return selected


def _ticker_count_from_cache(stream_cache: dict[str, Any], exchange: str) -> int:
    ticker_cache = stream_cache.get("ticker_cache")
    if not isinstance(ticker_cache, dict):
        return 0
    count = 0
    for item in ticker_cache.values():
        if not isinstance(item, dict):
            continue
        if str(item.get("exchange", "")).lower() == exchange:
            count += 1
    return count


def _market_count_from_runtime(runtime: dict[str, Any], exchange: str) -> int:
    action_plan = runtime.get("exchange_action_plan")
    if not isinstance(action_plan, dict):
        return 0
    venues = action_plan.get("venues")
    if not isinstance(venues, dict):
        return 0
    count = 0
    for venue_name, venue in venues.items():
        if exchange not in str(venue_name).lower():
            continue
        if isinstance(venue, dict) and _as_bool(venue.get("ready", True)):
            count += 1
    return count


def _known_venue_names(runtime: dict[str, Any], exchange: str) -> list[str]:
    action_plan = runtime.get("exchange_action_plan")
    if not isinstance(action_plan, dict):
        return []
    venues = action_plan.get("venues")
    if not isinstance(venues, dict):
        return []
    return sorted(str(name) for name in venues if exchange in str(name).lower())


def _waveform_active_for_exchange(recorder: dict[str, Any], exchange: str, source_health: dict[str, Any]) -> bool:
    if not isinstance(recorder, dict):
        return False
    inserted = _as_int(recorder.get("inserted_bar_count"), 0) > 0
    usable = _as_bool(recorder.get("usable_for_waveform_memory", inserted))
    if not inserted or not usable:
        return False
    recorder_health = recorder.get("source_health")
    if isinstance(recorder_health, dict):
        exchange_health = recorder_health.get(exchange)
        if isinstance(exchange_health, dict):
            return _as_bool(exchange_health.get("active")) and _as_bool(exchange_health.get("fresh", True))
    return exchange in source_health and _as_bool(source_health.get(exchange, {}).get("active"))


def _monitored_channels(
    *,
    exchange: str,
    config: dict[str, Any],
    connected: bool,
    source_present: bool,
    active: bool,
    fresh: bool,
    ticker_count: int,
    venue_count: int,
    waveform_active: bool,
    runtime: dict[str, Any],
) -> list[str]:
    monitored: list[str] = []
    if connected:
        monitored.append("exchange_client_ready")
    if source_present:
        monitored.append("source_health")
    if active:
        monitored.append("live_market_cache")
    if fresh and ticker_count:
        monitored.append("fresh_tickers")
    if ticker_count:
        monitored.append("ticker_universe")
    if venue_count:
        monitored.append("exchange_action_plan_venues")
    if waveform_active:
        monitored.append("waveform_history")

    if exchange == "binance" and active and ticker_count:
        monitored.extend(["all_market_24h_tickers", "ticker_cache", "price_cache", "volume_and_change", "live_stream_or_rest_gap_fill"])
    elif exchange == "kraken" and active and ticker_count:
        monitored.extend(["public_ticker_snapshot", "spot_pair_quotes", "ticker_cache", "price_cache"])
    elif exchange == "alpaca" and active and ticker_count:
        monitored.extend(["stock_snapshot", "latest_trade_or_quote", "ticker_cache", "price_cache"])
    elif exchange == "capital" and active and ticker_count:
        monitored.extend(["capital_market_snapshot", "ticker_cache", "price_cache"])

    if exchange == "capital" and isinstance(runtime.get("combined"), dict):
        if _as_float(runtime["combined"].get("capital_equity_gbp"), 0.0) > 0:
            monitored.extend(["capital_equity_context", "portfolio_balance", "open_position_context", "profit_loss_context"])
    if exchange == "kraken" and isinstance(runtime.get("combined"), dict):
        if "kraken_equity" in runtime["combined"]:
            monitored.extend(["kraken_equity_context", "portfolio_balance"])

    return sorted(dict.fromkeys(monitored))


def _missing_channels(
    *,
    exchange: str,
    config: dict[str, Any],
    connected: bool,
    source_present: bool,
    active: bool,
    fresh: bool,
    ticker_count: int,
    venue_count: int,
    waveform_active: bool,
    runtime_stale: bool,
    source_reason: str,
    monitored: list[str],
) -> list[str]:
    missing: list[str] = []
    if not connected:
        missing.append("exchange_client_not_ready_or_credentials_missing")
    if not source_present:
        missing.append("no_live_cache_source_health")
    if source_present and not active:
        missing.append("source_not_active_this_cycle")
    if source_present and active and not fresh:
        missing.append("source_not_fresh")
    if ticker_count <= 0:
        missing.append("no_tickers_in_live_cache")
    if venue_count <= 0:
        missing.append("no_exchange_action_plan_venue")
    if not waveform_active:
        missing.append("not_recording_waveform_history_this_cycle")
    if runtime_stale:
        missing.append("runtime_stale_blocks_fresh_live_decision_use")
    if source_reason:
        missing.append(source_reason)

    if exchange == "kraken":
        missing.append("per_exchange_orderbook_depth_not_proven")
        missing.append("spot_margin_fee_and_collateral_live_probe_not_proven")
    elif exchange == "binance":
        missing.append("per_exchange_orderbook_depth_not_proven")
    elif exchange == "alpaca":
        missing.append("authenticated_market_data_entitlement_not_proven")
    elif exchange == "capital":
        missing.append("capital_market_hours_and_position_close_speed_not_proven")

    expected = [str(item) for item in config.get("expected_channels", [])]
    monitored_base = set(monitored)
    for item in expected:
        if item == "waveform_history" and not waveform_active:
            continue
        if item not in monitored_base and item not in missing:
            missing.append(f"{item}_not_confirmed")

    return sorted(dict.fromkeys(item for item in missing if item))


def _exchange_row(
    exchange: str,
    config: dict[str, Any],
    runtime: dict[str, Any],
    stream_cache: dict[str, Any],
    recorder: dict[str, Any],
) -> dict[str, Any]:
    exchanges = runtime.get("exchanges") if isinstance(runtime.get("exchanges"), dict) else {}
    runtime_health = _runtime_source_health(runtime)
    stream_health = _cache_source_health(stream_cache)
    recorder_health = _recorder_source_health(recorder)
    source_health = _best_source_health(runtime_health, recorder_health, stream_health, exchange=exchange)

    connected = _as_bool(exchanges.get(config["ready_key"]))
    source_present = bool(source_health)
    active = _as_bool(source_health.get("active"))
    fresh = _as_bool(source_health.get("fresh")) and active
    ticker_count = max(_as_int(source_health.get("ticker_count"), 0), _ticker_count_from_cache(stream_cache, exchange))
    venue_count = _market_count_from_runtime(runtime, exchange)
    waveform_active = _waveform_active_for_exchange(recorder, exchange, stream_health)
    runtime_stale = _as_bool(runtime.get("stale")) or _as_bool(
        runtime.get("runtime_watchdog", {}).get("tick_stale") if isinstance(runtime.get("runtime_watchdog"), dict) else False
    )
    source_reason = str(source_health.get("reason", "") or "")
    generated_at = source_health.get("generated_at") or source_health.get("timestamp") or stream_cache.get("generated_at")
    age_sec = source_health.get("age_sec")
    if age_sec in (None, ""):
        age_sec = _timestamp_age_sec(generated_at)

    monitored = _monitored_channels(
        exchange=exchange,
        config=config,
        connected=connected,
        source_present=source_present,
        active=active,
        fresh=fresh,
        ticker_count=ticker_count,
        venue_count=venue_count,
        waveform_active=waveform_active,
        runtime=runtime,
    )
    missing = _missing_channels(
        exchange=exchange,
        config=config,
        connected=connected,
        source_present=source_present,
        active=active,
        fresh=fresh,
        ticker_count=ticker_count,
        venue_count=venue_count,
        waveform_active=waveform_active,
        runtime_stale=runtime_stale,
        source_reason=source_reason,
        monitored=monitored,
    )
    feeds_decision_logic = connected and active and fresh and ticker_count > 0 and venue_count > 0 and not runtime_stale
    usable_for_fast_money = feeds_decision_logic and not any(
        item.startswith("per_exchange_orderbook") or item.startswith("no_tickers") for item in missing
    )
    return {
        "exchange": exchange,
        "label": str(config["label"]),
        "markets": config.get("markets", []),
        "connected": connected,
        "cache_present": source_present,
        "cache_active": active,
        "cache_fresh": fresh,
        "ticker_count": ticker_count,
        "action_plan_venue_count": venue_count,
        "known_venues": _known_venue_names(runtime, exchange),
        "waveform_history_active": waveform_active,
        "feeds_decision_logic": feeds_decision_logic,
        "usable_for_fast_money": usable_for_fast_money,
        "monitored_now": monitored,
        "missing": missing,
        "required_for_fast_money": config.get("required_for_fast_money", []),
        "last_timestamp": generated_at,
        "age_sec": round(_as_float(age_sec, 0.0), 3) if age_sec is not None else None,
        "evidence": {
            "runtime_ready_key": f"state/unified_runtime_status.json#exchanges.{config['ready_key']}",
            "stream_cache": f"{STREAM_CACHE_PATH.as_posix()}#source_health.{exchange}",
            "action_plan": f"{RUNTIME_STATUS_PATH.as_posix()}#exchange_action_plan.venues",
            "waveform_recorder": WAVEFORM_RECORDER_PATH.as_posix(),
        },
    }


def _summary(rows: list[dict[str, Any]], runtime: dict[str, Any], stream_cache: dict[str, Any]) -> dict[str, Any]:
    active = [row for row in rows if row["cache_active"]]
    fresh = [row for row in rows if row["cache_fresh"]]
    decision_fed = [row for row in rows if row["feeds_decision_logic"]]
    fast_money = [row for row in rows if row["usable_for_fast_money"]]
    missing: list[dict[str, str]] = []
    for row in rows:
        for item in row.get("missing", [])[:5]:
            missing.append({"exchange": row["exchange"], "missing": str(item)})
    runtime_stale = _as_bool(runtime.get("stale"))
    status = "exchange_monitoring_ready"
    if runtime_stale:
        status = "exchange_monitoring_connected_guarded_runtime_stale"
    if len(fresh) < len(rows):
        status = "exchange_monitoring_ready_with_gaps" if fresh else "exchange_monitoring_guarded_missing_sources"
    if runtime_stale and fresh:
        status = "exchange_monitoring_connected_guarded_runtime_stale"
    return {
        "runtime_stale": runtime_stale,
        "stale_reason": runtime.get("stale_reason") or (
            runtime.get("runtime_watchdog", {}).get("tick_stale_reason")
            if isinstance(runtime.get("runtime_watchdog"), dict)
            else ""
        ),
        "exchange_count": len(rows),
        "connected_exchange_count": sum(1 for row in rows if row["connected"]),
        "active_exchange_count": len(active),
        "fresh_exchange_count": len(fresh),
        "decision_fed_exchange_count": len(decision_fed),
        "fast_money_usable_exchange_count": len(fast_money),
        "waveform_history_exchange_count": sum(1 for row in rows if row["waveform_history_active"]),
        "total_tickers_monitored": sum(_as_int(row.get("ticker_count"), 0) for row in rows),
        "stream_cache_source": stream_cache.get("source", ""),
        "stream_cache_generated_at": stream_cache.get("generated_at"),
        "top_missing": missing[:12],
        "status": status,
    }


def build_exchange_monitoring_checklist(root: Optional[Path] = None) -> dict[str, Any]:
    root = (root or REPO_ROOT).resolve()
    runtime = read_runtime_status(root)
    stream_cache = _read_json(root / STREAM_CACHE_PATH, {})
    recorder = _read_json(root / WAVEFORM_RECORDER_PATH, {})
    if not isinstance(runtime, dict):
        runtime = {}
    if not isinstance(stream_cache, dict):
        stream_cache = {}
    if not isinstance(recorder, dict):
        recorder = {}
    rows = [
        _exchange_row(exchange, config, runtime, stream_cache, recorder)
        for exchange, config in EXCHANGE_REQUIREMENTS.items()
    ]
    summary = _summary(rows, runtime, stream_cache)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": summary["status"],
        "repo_root": str(root),
        "summary": summary,
        "contract": {
            "purpose": "Show what each exchange is monitoring and what is missing before its evidence can feed fast-profit trading decisions.",
            "source_of_truth": "state/unified_runtime_status.json plus ws_cache/ws_prices.json source_health and waveform recorder evidence",
            "no_execution_change": "This checklist changes no exchange orders, credentials, payments, filings, or live mutation gates.",
        },
        "rows": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    rows = report.get("rows") if isinstance(report.get("rows"), list) else []
    lines = [
        "# Aureon Exchange Monitoring Checklist",
        "",
        f"- Generated: {report.get('generated_at', '')}",
        f"- Status: {report.get('status', '')}",
        f"- Connected exchanges: {summary.get('connected_exchange_count', 0)}/{summary.get('exchange_count', 0)}",
        f"- Fresh exchange sources: {summary.get('fresh_exchange_count', 0)}/{summary.get('exchange_count', 0)}",
        f"- Decision-fed exchanges: {summary.get('decision_fed_exchange_count', 0)}/{summary.get('exchange_count', 0)}",
        f"- Fast-money usable exchanges: {summary.get('fast_money_usable_exchange_count', 0)}/{summary.get('exchange_count', 0)}",
        f"- Waveform history exchanges: {summary.get('waveform_history_exchange_count', 0)}/{summary.get('exchange_count', 0)}",
        f"- Total tickers monitored: {summary.get('total_tickers_monitored', 0)}",
        f"- Runtime stale: {summary.get('runtime_stale', False)} {summary.get('stale_reason') or ''}",
        "",
        "| Exchange | Connected | Fresh Cache | Tickers | Venues | Decision Fed | Fast Money | Missing |",
        "| --- | --- | --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in rows:
        missing = ", ".join(str(item) for item in row.get("missing", [])[:4])
        lines.append(
            "| {label} | {connected} | {fresh} | {tickers} | {venues} | {fed} | {fast} | {missing} |".format(
                label=row.get("label", row.get("exchange", "")),
                connected=row.get("connected", False),
                fresh=row.get("cache_fresh", False),
                tickers=row.get("ticker_count", 0),
                venues=row.get("action_plan_venue_count", 0),
                fed=row.get("feeds_decision_logic", False),
                fast=row.get("usable_for_fast_money", False),
                missing=missing.replace("|", "/"),
            )
        )
    lines.extend(
        [
            "",
            "This checklist is evidence-only. It does not place orders or bypass live runtime checks.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_exchange_monitoring_checklist(
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
    parser = argparse.ArgumentParser(description="Build Aureon's per-exchange monitoring checklist.")
    parser.add_argument("--repo-root", default="", help="Repo root; defaults to current Aureon repo.")
    parser.add_argument("--json", default=str(DEFAULT_OUTPUT_JSON), help="Audit JSON path.")
    parser.add_argument("--md", default=str(DEFAULT_OUTPUT_MD), help="Audit Markdown path.")
    parser.add_argument("--public-json", default=str(DEFAULT_PUBLIC_JSON), help="Frontend public JSON path.")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else REPO_ROOT
    report = build_exchange_monitoring_checklist(root)
    output_json, output_md, public_json = write_exchange_monitoring_checklist(
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
