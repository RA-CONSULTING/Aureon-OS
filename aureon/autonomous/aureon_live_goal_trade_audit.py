"""Read-only proof chain for live goal-trade readiness.

This audit proves whether live market data is reaching the organism, whether
the organism is producing a GOLD-focused order intent, and whether the runtime
executor has cleared the live-action gate. It never places orders, alters
credentials, or weakens trading safety gates.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


SCHEMA_VERSION = "aureon-live-goal-trade-audit-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_STATE_PATH = Path("state/aureon_live_goal_trade_audit_last_run.json")
DEFAULT_AUDIT_JSON = Path("docs/audits/aureon_live_goal_trade_audit.json")
DEFAULT_AUDIT_MD = Path("docs/audits/aureon_live_goal_trade_audit.md")
DEFAULT_PUBLIC_JSON = Path("frontend/public/aureon_live_goal_trade_audit.json")

RUNTIME_STATUS_PATH = Path("state/unified_runtime_status.json")
RUNTIME_STATUS_API_URL = os.getenv("AUREON_MARKET_STATUS_URL", "http://127.0.0.1:8791/api/terminal-state")
RUNTIME_STATUS_API_TIMEOUT_SEC = max(1.0, float(os.getenv("AUREON_MARKET_STATUS_TIMEOUT_SEC", "10") or "10"))
STREAM_CACHE_PATH = Path("ws_cache/ws_prices.json")
ORDER_INTENTS_PATH = Path("state/unified_exchange_order_intents.json")
ORDER_INTENTS_JSONL_PATH = Path("state/unified_exchange_order_intents.jsonl")
ORDER_LIFECYCLE_PATH = Path("state/unified_order_lifecycle_latest.json")
ORDER_LIFECYCLE_STRESS_PATH = Path("frontend/public/aureon_order_lifecycle_stress_audit.json")
CAPITAL_ECOSYSTEM_PUBLIC_PATH = Path("frontend/public/aureon_capital_ecosystem_intelligence_company.json")
CAPITAL_LIVE_DRY_STRESS_PATH = Path("frontend/public/aureon_capital_ecosystem_live_dry_stress_audit.json")
CAPITAL_REVENUE_LOGIC_STRESS_PATH = Path("frontend/public/aureon_capital_revenue_logic_stress_audit.json")
CAPITAL_REVENUE_LIVE_GATE_READINESS_PATH = Path("frontend/public/aureon_capital_revenue_live_gate_readiness_audit.json")
CAPITAL_ASSET_REGISTRY_PATH = Path("state/aureon_capital_tradable_asset_registry.json")
GOLD_COMPANY_PUBLIC_PATH = Path("frontend/public/aureon_gold_capital_intelligence_company.json")
TRADING_CHECKLIST_PUBLIC_PATH = Path("frontend/public/aureon_trading_intelligence_checklist.json")

LIVE_DATA_FRESH_SECONDS = 180
GOLD_REGISTRY_FRESH_SECONDS = 900
ORDER_INTENT_FRESH_SECONDS = 120
GOLD_TERMS = ("GOLD", "XAU", "XAUT", "PAXG", "GC=F", "GLD", "IAU", "GDX")
SUPPORTING_TERMS = (
    "BTC",
    "ETH",
    "DXY",
    "USD",
    "US10Y",
    "VIX",
    "SPY",
    "QQQ",
    "OIL",
    "BRENT",
    "WTI",
    "XLE",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "aureon").exists() and (cwd / "frontend").exists():
        return cwd
    return REPO_ROOT


def _rooted(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _read_runtime_status(root: Path) -> Dict[str, Any]:
    file_payload = _read_json(_rooted(root, RUNTIME_STATUS_PATH), {})
    if not isinstance(file_payload, dict):
        file_payload = {}
    try:
        if root.resolve() != _default_root().resolve():
            return file_payload
    except Exception:
        return file_payload
    if not RUNTIME_STATUS_API_URL:
        return file_payload
    try:
        request = urllib.request.Request(
            RUNTIME_STATUS_API_URL,
            headers={"Accept": "application/json", "User-Agent": "AureonLiveGoalTradeAudit/1.0"},
        )
        with urllib.request.urlopen(request, timeout=RUNTIME_STATUS_API_TIMEOUT_SEC) as response:  # nosec B310 - local runtime status endpoint
            api_payload = json.loads(response.read().decode("utf-8", errors="replace"))
        if isinstance(api_payload, dict):
            merged = dict(file_payload)
            merged.update(api_payload)
            merged["runtime_status_source"] = "local_terminal_state_api"
            return merged
    except Exception:
        pass
    return file_payload


def _write_text(path: Path, content: str) -> Dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": len(content.encode("utf-8"))}


def _write_json(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    return _write_text(path, json.dumps(payload, indent=2, sort_keys=True, default=str))


def _as_number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        if math.isfinite(number):
            return number
    except Exception:
        pass
    return default


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.isdigit():
            return datetime.fromtimestamp(float(text), tz=timezone.utc)
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except Exception:
        return None


def _iso(value: Any) -> str:
    parsed = _parse_timestamp(value)
    return parsed.isoformat() if parsed else ""


def _age_seconds(value: Any, now: datetime) -> Optional[float]:
    parsed = _parse_timestamp(value)
    if not parsed:
        return None
    return round(max(0.0, (now - parsed).total_seconds()), 3)


def _contains_any(text: str, terms: Iterable[str]) -> bool:
    upper = text.upper()
    return any(term.upper() in upper for term in terms)


def _symbol_text(item: Dict[str, Any]) -> str:
    values = [
        item.get("symbol"),
        item.get("pair"),
        item.get("epic"),
        item.get("base"),
        item.get("quote"),
        item.get("instrument_name"),
    ]
    return " ".join(str(value) for value in values if value not in (None, ""))


def _source_health(cache: Dict[str, Any], now: datetime) -> List[Dict[str, Any]]:
    health = cache.get("source_health") if isinstance(cache.get("source_health"), dict) else {}
    rows: List[Dict[str, Any]] = []
    for source, payload in sorted(health.items()):
        if not isinstance(payload, dict):
            continue
        true_age = _age_seconds(payload.get("generated_at"), now)
        data_age = _age_seconds(payload.get("last_success_at") or payload.get("generated_at"), now)
        rows.append(
            {
                "source": source,
                "mode": payload.get("mode") or "",
                "present": bool(payload.get("present", True)),
                "active": bool(payload.get("active", False)),
                "embedded_fresh_flag": bool(payload.get("fresh", False)),
                "generated_at": _iso(payload.get("generated_at")),
                "true_age_sec": true_age,
                "data_age_sec": data_age,
                "ticker_count": int(_as_number(payload.get("ticker_count"), 0)),
                "fresh_for_order_action": true_age is not None and true_age <= LIVE_DATA_FRESH_SECONDS,
                "reason": payload.get("reason") or "",
            }
        )
    return rows


def _ticker_rows(cache: Dict[str, Any], now: datetime) -> List[Dict[str, Any]]:
    ticker_cache = cache.get("ticker_cache") if isinstance(cache.get("ticker_cache"), dict) else {}
    rows: List[Dict[str, Any]] = []
    for key, value in ticker_cache.items():
        if not isinstance(value, dict):
            continue
        text = f"{key} {_symbol_text(value)}"
        if not (_contains_any(text, GOLD_TERMS) or _contains_any(text, SUPPORTING_TERMS)):
            continue
        rows.append(
            {
                "key": key,
                "symbol": value.get("symbol") or value.get("pair") or key,
                "exchange": value.get("exchange") or "",
                "source": value.get("source") or "",
                "price": value.get("price"),
                "bid": value.get("bid"),
                "ask": value.get("ask"),
                "change24h": value.get("change24h"),
                "timestamp": _iso(value.get("timestamp")),
                "age_sec": _age_seconds(value.get("timestamp"), now),
                "role": "gold_target_or_proxy" if _contains_any(text, GOLD_TERMS) else "supporting_context",
            }
        )
    rows.sort(key=lambda row: (row["role"] != "gold_target_or_proxy", row.get("age_sec") is None, row.get("age_sec") or 10**9, str(row["key"])))
    return rows


def _build_data_capture(root: Path, now: datetime) -> Dict[str, Any]:
    cache_path = _rooted(root, STREAM_CACHE_PATH)
    cache = _read_json(cache_path, {})
    if not isinstance(cache, dict) or not cache:
        return {
            "state": "missing_stream_cache",
            "path": STREAM_CACHE_PATH.as_posix(),
            "present": False,
            "fresh_for_order_action": False,
            "blockers": ["stream_cache_missing"],
            "source_health": [],
            "gold_related_tickers": [],
        }
    generated_at = cache.get("generated_at")
    age = _age_seconds(generated_at, now)
    ticker_cache = cache.get("ticker_cache") if isinstance(cache.get("ticker_cache"), dict) else {}
    prices = cache.get("prices") if isinstance(cache.get("prices"), dict) else {}
    source_health = _source_health(cache, now)
    ticker_rows = _ticker_rows(cache, now)
    fresh = age is not None and age <= LIVE_DATA_FRESH_SECONDS and bool(source_health) and all(
        row.get("fresh_for_order_action") for row in source_health if row.get("active")
    )
    blockers: List[str] = []
    if age is None:
        blockers.append("stream_cache_missing_timestamp")
    elif age > LIVE_DATA_FRESH_SECONDS:
        blockers.append("stream_cache_stale")
    if not ticker_rows:
        blockers.append("no_gold_or_supporting_tickers_in_stream_cache")
    stale_sources = [row["source"] for row in source_health if row.get("active") and not row.get("fresh_for_order_action")]
    if stale_sources:
        blockers.append("stale_active_sources:" + ",".join(stale_sources[:4]))
    return {
        "state": "fresh_live_data" if fresh else "live_data_not_action_fresh",
        "path": STREAM_CACHE_PATH.as_posix(),
        "present": True,
        "generated_at": _iso(generated_at),
        "age_sec": age,
        "fresh_seconds_budget": LIVE_DATA_FRESH_SECONDS,
        "fresh_for_order_action": fresh,
        "source": cache.get("source") or "",
        "source_count": int(_as_number(cache.get("source_count"), len(source_health))),
        "active_source_count": int(_as_number(cache.get("active_source_count"), len([row for row in source_health if row.get("active")]))),
        "ticker_count": len(ticker_cache) or len(prices),
        "gold_related_ticker_count": len([row for row in ticker_rows if row["role"] == "gold_target_or_proxy"]),
        "supporting_ticker_count": len([row for row in ticker_rows if row["role"] == "supporting_context"]),
        "gold_related_tickers": ticker_rows[:16],
        "source_health": source_health,
        "blockers": blockers,
    }


def _capital_gold_live_quote(root: Path, now: datetime) -> Dict[str, Any]:
    cache = _read_json(_rooted(root, STREAM_CACHE_PATH), {})
    ticker_cache = cache.get("ticker_cache") if isinstance(cache, dict) and isinstance(cache.get("ticker_cache"), dict) else {}
    candidates: List[Dict[str, Any]] = []
    for key, value in ticker_cache.items():
        if not isinstance(value, dict):
            continue
        text = f"{key} {_symbol_text(value)}".upper()
        exchange = str(value.get("exchange") or "").lower()
        direct_capital_gold = exchange == "capital" and (
            "GOLD" in text or "XAU" in text or str(value.get("pair") or "").upper() == "GOLD"
        )
        if not direct_capital_gold:
            continue
        age = _age_seconds(value.get("timestamp"), now)
        price = _as_number(value.get("price"), 0.0)
        bid = _as_number(value.get("bid"), 0.0)
        ask = _as_number(value.get("ask"), 0.0)
        if price <= 0 and bid <= 0 and ask <= 0:
            continue
        if bid <= 0:
            bid = price
        if ask <= 0:
            ask = price
        mid = price if price > 0 else (bid + ask) / 2.0
        spread = max(0.0, ask - bid) if ask > 0 and bid > 0 else 0.0
        candidates.append(
            {
                "key": key,
                "symbol": value.get("symbol") or value.get("pair") or "GOLD",
                "source": value.get("source") or "",
                "timestamp": _iso(value.get("timestamp")),
                "age_sec": age,
                "fresh_for_order_action": age is not None and age <= LIVE_DATA_FRESH_SECONDS,
                "price": round(mid, 8),
                "bid": round(bid, 8),
                "ask": round(ask, 8),
                "spread": round(spread, 8),
                "spread_pct": round((spread / mid) * 100.0, 8) if mid > 0 and spread >= 0 else 0.0,
                "source_path": f"{STREAM_CACHE_PATH.as_posix()}#ticker_cache.{key}",
            }
        )
    candidates.sort(key=lambda row: (not row.get("fresh_for_order_action"), row.get("age_sec") is None, row.get("age_sec") or 10**9))
    return candidates[0] if candidates else {}


def _capital_gold_registry(root: Path, now: datetime) -> Dict[str, Any]:
    registry = _read_json(_rooted(root, CAPITAL_ASSET_REGISTRY_PATH), {})
    assets = registry.get("assets") if isinstance(registry, dict) and isinstance(registry.get("assets"), list) else []
    gold_assets: List[Dict[str, Any]] = []
    live_quote = _capital_gold_live_quote(root, now)
    for item in assets:
        if not isinstance(item, dict):
            continue
        text = _symbol_text(item)
        if not _contains_any(text, ("GOLD", "XAU")):
            continue
        symbol = str(item.get("symbol") or "").upper()
        epic = str(item.get("epic") or "").upper()
        direct_target = symbol == "GOLD" or epic == "GOLD" or symbol == "XAUUSD" or epic == "XAUUSD"
        age = _age_seconds(item.get("last_snapshot_at"), now)
        live_quote_applied = bool(direct_target and live_quote.get("fresh_for_order_action"))
        bid = live_quote.get("bid") if live_quote_applied else item.get("bid")
        ask = live_quote.get("ask") if live_quote_applied else item.get("ask")
        mid_price = live_quote.get("price") if live_quote_applied else item.get("mid_price")
        spread = live_quote.get("spread") if live_quote_applied else item.get("spread")
        spread_pct = live_quote.get("spread_pct") if live_quote_applied else item.get("spread_pct")
        quote_age = live_quote.get("age_sec") if live_quote_applied else age
        quote_timestamp = live_quote.get("timestamp") if live_quote_applied else _iso(item.get("last_snapshot_at"))
        gold_assets.append(
            {
                "symbol": item.get("symbol") or "",
                "epic": item.get("epic") or "",
                "target_role": "capital_gold_target" if direct_target else "gold_context_or_proxy",
                "instrument_name": item.get("instrument_name") or "",
                "market_status": item.get("market_status") or "",
                "trade_ready": bool(item.get("trade_ready")),
                "can_buy": bool(item.get("can_buy")),
                "can_sell": bool(item.get("can_sell")),
                "bid": bid,
                "ask": ask,
                "mid_price": mid_price,
                "spread": spread,
                "spread_pct": spread_pct,
                "minimum_deal_size": item.get("minimum_deal_size"),
                "margin_required_for_min_deal": item.get("margin_required_for_min_deal"),
                "last_snapshot_at": quote_timestamp,
                "snapshot_age_sec": quote_age,
                "metadata_snapshot_at": _iso(item.get("last_snapshot_at")),
                "metadata_snapshot_age_sec": age,
                "fresh_for_order_action": live_quote_applied or (age is not None and age <= GOLD_REGISTRY_FRESH_SECONDS),
                "live_quote_overlay_applied": live_quote_applied,
                "live_quote_source_path": live_quote.get("source_path") or "",
                "source_path": CAPITAL_ASSET_REGISTRY_PATH.as_posix(),
            }
        )
    gold_assets.sort(
        key=lambda item: (
            item.get("target_role") != "capital_gold_target",
            not item["trade_ready"],
            item.get("snapshot_age_sec") is None,
            item.get("snapshot_age_sec") or 10**9,
        )
    )
    best = gold_assets[0] if gold_assets else None
    blockers: List[str] = []
    if not gold_assets:
        blockers.append("capital_gold_registry_missing")
    elif not best or not best.get("trade_ready"):
        blockers.append("capital_gold_not_trade_ready")
    elif not best.get("fresh_for_order_action"):
        blockers.append("capital_gold_live_quote_missing_or_stale")
    return {
        "state": "capital_gold_fresh" if best and best.get("fresh_for_order_action") and best.get("trade_ready") else "capital_gold_not_action_fresh",
        "path": CAPITAL_ASSET_REGISTRY_PATH.as_posix(),
        "live_quote_overlay": live_quote,
        "gold_asset_count": len(gold_assets),
        "best_gold_asset": best or {},
        "gold_assets": gold_assets[:8],
        "fresh_seconds_budget": GOLD_REGISTRY_FRESH_SECONDS,
        "blockers": blockers,
    }


def _read_latest_intents(root: Path) -> Dict[str, Any]:
    payload = _read_json(_rooted(root, ORDER_INTENTS_PATH), {})
    if not isinstance(payload, dict):
        payload = {}
    intents = payload.get("intents") if isinstance(payload.get("intents"), list) else []
    jsonl_tail: List[Dict[str, Any]] = []
    path = _rooted(root, ORDER_INTENTS_JSONL_PATH)
    try:
        if path.exists():
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
            for line in lines:
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        jsonl_tail.append(item)
                except Exception:
                    continue
    except Exception:
        jsonl_tail = []
    return {
        "packet": payload,
        "intents": [item for item in intents if isinstance(item, dict)],
        "jsonl_tail": jsonl_tail,
    }


def _intent_is_gold_related(intent: Dict[str, Any]) -> bool:
    parts: List[str] = [str(intent.get("symbol") or ""), str(intent.get("side") or "")]
    for route in intent.get("routes") or []:
        if isinstance(route, dict):
            parts.extend([str(route.get("symbol") or ""), str(route.get("venue") or "")])
    for source in intent.get("sources") or []:
        parts.append(str(source))
    return _contains_any(" ".join(parts), GOLD_TERMS)


def _summarize_intent(intent: Dict[str, Any], now: datetime) -> Dict[str, Any]:
    routes = [route for route in intent.get("routes") or [] if isinstance(route, dict)]
    blockers: List[str] = []
    for route in routes:
        for blocker in route.get("blockers") or []:
            blockers.append(str(blocker))
    return {
        "id": intent.get("id") or "",
        "symbol": intent.get("symbol") or "",
        "side": intent.get("side") or "",
        "confidence": intent.get("confidence"),
        "generated_at": _iso(intent.get("generated_at")),
        "age_sec": _age_seconds(intent.get("generated_at"), now),
        "authority_mode": intent.get("authority_mode") or intent.get("mode") or "",
        "runtime_gate": intent.get("runtime_gate") or "",
        "profit_velocity_score": intent.get("profit_velocity_score"),
        "fast_money_score": intent.get("fast_money_score"),
        "history_validation_score": intent.get("history_validation_score"),
        "model_alignment": bool(intent.get("model_alignment")),
        "cash_capable_route_count": intent.get("cash_capable_route_count"),
        "route_count": len(routes),
        "routes": [
            {
                "venue": route.get("venue") or "",
                "market_type": route.get("market_type") or "",
                "symbol": route.get("symbol") or "",
                "ready": bool(route.get("ready")),
                "trade_clearance_state": route.get("trade_clearance_state") or "",
                "guard_state": route.get("guard_state") or "",
                "blockers": route.get("blockers") or [],
            }
            for route in routes[:6]
        ],
        "route_blockers": blockers[:8],
        "safety": intent.get("safety") if isinstance(intent.get("safety"), dict) else {},
        "sources": intent.get("sources") or [],
    }


def _build_order_intent_proof(root: Path, now: datetime) -> Dict[str, Any]:
    latest = _read_latest_intents(root)
    packet = latest["packet"]
    intents = latest["intents"]
    gold_intents = [intent for intent in intents if _intent_is_gold_related(intent)]
    fresh_intents = [
        intent
        for intent in intents
        if (_age_seconds(intent.get("generated_at"), now) is not None and (_age_seconds(intent.get("generated_at"), now) or 10**9) <= ORDER_INTENT_FRESH_SECONDS)
    ]
    best_gold = gold_intents[0] if gold_intents else None
    blockers: List[str] = []
    packet_age = _age_seconds(packet.get("generated_at"), now)
    intent_packet_fresh = packet_age is not None and packet_age <= ORDER_INTENT_FRESH_SECONDS
    if packet_age is None:
        blockers.append("order_intent_packet_missing_timestamp")
    elif packet_age > ORDER_INTENT_FRESH_SECONDS:
        blockers.append("order_intent_packet_stale")
    if not intents:
        blockers.append("no_order_intents_published")
    if not gold_intents:
        blockers.append("no_gold_order_intent_published")
    return {
        "state": "gold_order_intent_ready" if best_gold and not blockers else "gold_order_intent_not_ready",
        "path": ORDER_INTENTS_PATH.as_posix(),
        "jsonl_path": ORDER_INTENTS_JSONL_PATH.as_posix(),
        "packet_generated_at": _iso(packet.get("generated_at")),
        "packet_age_sec": packet_age,
        "intent_packet_fresh": intent_packet_fresh,
        "fresh_seconds_budget": ORDER_INTENT_FRESH_SECONDS,
        "intent_count": len(intents),
        "fresh_intent_count": len(fresh_intents),
        "gold_intent_count": len(gold_intents),
        "non_gold_intents_rejected_for_gold_proof": bool(intents and not gold_intents),
        "best_gold_intent": _summarize_intent(best_gold, now) if best_gold else {},
        "latest_intents": [_summarize_intent(intent, now) for intent in intents[:6]],
        "recent_jsonl_count": len(latest["jsonl_tail"]),
        "blockers": blockers,
    }


def _build_runtime_gate(root: Path, now: datetime) -> Dict[str, Any]:
    runtime = _read_runtime_status(root)
    if not isinstance(runtime, dict):
        runtime = {}
    action_plan = runtime.get("exchange_action_plan") if isinstance(runtime.get("exchange_action_plan"), dict) else {}
    latest_execution = action_plan.get("latest_execution") if isinstance(action_plan.get("latest_execution"), dict) else {}
    gold_runtime_proof = (
        runtime.get("gold_runtime_trade_proof")
        if isinstance(runtime.get("gold_runtime_trade_proof"), dict)
        else action_plan.get("gold_runtime_trade_proof")
        if isinstance(action_plan.get("gold_runtime_trade_proof"), dict)
        else {}
    )
    shared_order_flow = runtime.get("shared_order_flow") if isinstance(runtime.get("shared_order_flow"), dict) else {}
    if not gold_runtime_proof and shared_order_flow:
        active = shared_order_flow.get("active_order_flow") if isinstance(shared_order_flow.get("active_order_flow"), list) else []
        gold_rows = [
            row
            for row in active
            if isinstance(row, dict)
            and (
                bool(row.get("gold_priority_candidate"))
                or _contains_any(str(row.get("symbol") or ""), ("GOLD", "XAU"))
            )
        ]
        row = gold_rows[0] if gold_rows else {}
        routes = row.get("execution_routes") if isinstance(row.get("execution_routes"), list) else []
        capital_routes = [
            route
            for route in routes
            if isinstance(route, dict)
            and str(route.get("venue") or "").lower() == "capital"
            and str(route.get("market_type") or "").lower() == "cfd"
        ]
        route = capital_routes[0] if capital_routes else {}
        gold_runtime_proof = {
            "gold_runtime_candidate_ready": bool(row),
            "capital_cfd_route_visible": bool(route),
            "capital_cfd_route_ready": bool(route.get("ready")) if isinstance(route, dict) else False,
            "gold_intent_publish_reason": (
                "gold_runtime_candidate_from_shared_order_flow"
                if row and route
                else "gold_runtime_candidate_missing"
            ),
            "intent_publish_blockers": row.get("intent_publish_blockers") if isinstance(row.get("intent_publish_blockers"), list) else [],
        }
    runtime_clearances = latest_execution.get("runtime_clearances") or runtime.get("runtime_clearances") or []
    if isinstance(runtime_clearances, str):
        runtime_clearances = [runtime_clearances] if runtime_clearances else []
    blockers = latest_execution.get("blockers") or []
    if isinstance(blockers, str):
        blockers = [blockers] if blockers else []
    if runtime.get("stale") and "current_tick_stale" not in blockers:
        blockers.append("current_tick_stale")
    return {
        "state": "executor_submitted" if _as_number(latest_execution.get("submitted_count")) > 0 else "executor_gated",
        "path": RUNTIME_STATUS_PATH.as_posix(),
        "generated_at": _iso(runtime.get("generated_at") or runtime.get("dashboard_generated_at")),
        "runtime_age_sec": _age_seconds(runtime.get("generated_at") or runtime.get("dashboard_generated_at"), now),
        "trading_ready": bool(runtime.get("trading_ready")),
        "data_ready": bool(runtime.get("data_ready")),
        "stale": bool(runtime.get("stale")),
        "stale_reason": runtime.get("stale_reason") or "",
        "tick_phase": runtime.get("tick_phase") or "",
        "last_tick_started_at": _iso(runtime.get("last_tick_started_at")),
        "last_tick_completed_at": _iso(runtime.get("last_tick_completed_at")),
        "last_tick_age_sec": runtime.get("last_tick_age_sec"),
        "last_tick_running_sec": runtime.get("last_tick_running_sec"),
        "tick_phase_running_sec": runtime.get("tick_phase_running_sec"),
        "trade_path_state": runtime.get("trade_path_state") or latest_execution.get("trade_path_state") or "",
        "executor_enabled": bool(latest_execution.get("executor_enabled", action_plan.get("executor_enabled", False))),
        "real_orders_disabled": bool(action_plan.get("real_orders_disabled", runtime.get("real_orders_disabled", False))),
        "exchange_mutations_disabled": bool(action_plan.get("exchange_mutations_disabled", runtime.get("exchange_mutations_disabled", False))),
        "live_action_clearance": latest_execution.get("live_action_clearance") or "",
        "runtime_clearances": runtime_clearances,
        "blockers": blockers,
        "attempted_count": int(_as_number(latest_execution.get("attempted_count"), 0)),
        "submitted_count": int(_as_number(latest_execution.get("submitted_count"), 0)),
        "delegated_count": int(_as_number(latest_execution.get("delegated_count"), 0)),
        "held_count": int(_as_number(latest_execution.get("held_count"), 0)),
        "blocked_count": int(_as_number(latest_execution.get("blocked_count"), 0)),
        "latest_execution_generated_at": _iso(latest_execution.get("generated_at")),
        "order_intents_published": action_plan.get("order_intents_published") or (action_plan.get("latest_published") or {}).get("intent_count") or 0,
        "decision_self_trust": action_plan.get("decision_self_trust") or {},
        "gold_runtime_candidate_ready": bool(gold_runtime_proof.get("gold_runtime_candidate_ready")),
        "capital_cfd_route_visible": bool(gold_runtime_proof.get("capital_cfd_route_visible")),
        "capital_cfd_route_ready": bool(gold_runtime_proof.get("capital_cfd_route_ready")),
        "gold_intent_publish_reason": gold_runtime_proof.get("gold_intent_publish_reason") or "",
        "gold_runtime_trade_proof": gold_runtime_proof,
        "runtime_stall_diagnostic": runtime.get("runtime_stall_diagnostic") if isinstance(runtime.get("runtime_stall_diagnostic"), dict) else {},
    }


def _build_gold_company_summary(root: Path) -> Dict[str, Any]:
    report = _read_json(_rooted(root, GOLD_COMPANY_PUBLIC_PATH), {})
    if not isinstance(report, dict):
        report = {}
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    blockers = report.get("blockers") if isinstance(report.get("blockers"), list) else []
    return {
        "path": GOLD_COMPANY_PUBLIC_PATH.as_posix(),
        "status": report.get("status") or "",
        "generated_at": report.get("generated_at") or "",
        "action_state": summary.get("gold_action_state") or "",
        "action_status": summary.get("gold_action_command_status") or "",
        "verified_real_data_gate_status": summary.get("verified_real_data_gate_status") or "",
        "verified_real_data_action_allowed": bool(summary.get("verified_real_data_action_allowed")),
        "fresh_interval_gate": summary.get("gold_freshness_action_influence_state") or "",
        "hnc_route_passed": bool(summary.get("hnc_auris_quantum_probability_route_passed")),
        "hft_gate_passed": bool(summary.get("hft_speed_prediction_gate_passed")),
        "historical_stress_passed": bool(summary.get("gold_historical_stress_passed")),
        "blocker_count": len(blockers),
        "top_blockers": blockers[:8],
    }


def _build_order_lifecycle_proof(root: Path, runtime_gate: Dict[str, Any]) -> Dict[str, Any]:
    path = _rooted(root, ORDER_LIFECYCLE_PATH)
    payload = _read_json(path, {})
    if not isinstance(payload, dict):
        payload = {}
    lifecycles = payload.get("lifecycles") if isinstance(payload.get("lifecycles"), list) else []
    active = payload.get("active_lifecycles") if isinstance(payload.get("active_lifecycles"), list) else []
    blockers = [str(item) for item in (payload.get("continuity_blockers") or []) if str(item)]

    submitted_or_delegated = (
        _as_number(runtime_gate.get("submitted_count"), 0) > 0
        or _as_number(runtime_gate.get("delegated_count"), 0) > 0
        or _as_number(runtime_gate.get("attempted_count"), 0) > 0
    )
    missing_links: List[str] = []
    for row in active[:10]:
        if not isinstance(row, dict):
            continue
        missing = row.get("missing_links") if isinstance(row.get("missing_links"), list) else []
        missing_links.extend(str(item) for item in missing if str(item))
    if submitted_or_delegated and not lifecycles:
        blockers.append("lifecycle_continuity_missing")
        missing_links.append("lifecycle_record")
    if submitted_or_delegated and missing_links:
        blockers.append("lifecycle_continuity_missing")

    latest = payload.get("latest_event") if isinstance(payload.get("latest_event"), dict) else {}
    return {
        "state": "order_lifecycle_ready" if payload and not blockers else "order_lifecycle_attention",
        "path": ORDER_LIFECYCLE_PATH.as_posix(),
        "present": bool(payload),
        "generated_at": payload.get("generated_at") or "",
        "event_count": int(_as_number(payload.get("event_count"), 0)),
        "lifecycle_count": int(_as_number(payload.get("lifecycle_count"), 0)),
        "active_lifecycle_count": int(_as_number(payload.get("active_lifecycle_count"), 0)),
        "completed_lifecycle_count": int(_as_number(payload.get("completed_lifecycle_count"), 0)),
        "latest_status": latest.get("status") or latest.get("event_type") or "",
        "latest_lifecycle_id": latest.get("lifecycle_id") or "",
        "latest_deal_id": latest.get("deal_id") or "",
        "active_lifecycles": active[:6],
        "missing_links": list(dict.fromkeys(missing_links))[:20],
        "blockers": list(dict.fromkeys(blockers))[:20],
        "snapshot": payload,
    }


def _build_order_lifecycle_stress_proof(root: Path) -> Dict[str, Any]:
    payload = _read_json(_rooted(root, ORDER_LIFECYCLE_STRESS_PATH), {})
    if not isinstance(payload, dict):
        payload = {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    proof_tiers = payload.get("proof_tiers") if isinstance(payload.get("proof_tiers"), dict) else {}
    blockers = [str(item) for item in (payload.get("blockers") or []) if str(item)]
    if not payload:
        blockers.append("order_lifecycle_stress_audit_missing")
    certified = bool(payload and payload.get("status") == "order_lifecycle_stress_certified" and not blockers)
    return {
        "state": "order_lifecycle_stress_certified" if certified else "order_lifecycle_stress_attention",
        "path": ORDER_LIFECYCLE_STRESS_PATH.as_posix(),
        "present": bool(payload),
        "generated_at": payload.get("generated_at") or "",
        "status": payload.get("status") or "",
        "case_count": int(_as_number(summary.get("case_count"), 0)),
        "passed_count": int(_as_number(summary.get("passed_count"), 0)),
        "failed_count": int(_as_number(summary.get("failed_count"), 0)),
        "requirement_count": int(_as_number(summary.get("requirement_count"), 0)),
        "covered_requirement_count": int(_as_number(summary.get("covered_requirement_count"), 0)),
        "coverage_percent": summary.get("coverage_percent"),
        "capital_gold_path_certified": bool(summary.get("capital_gold_path_certified")),
        "duplicate_route_blocked": bool(summary.get("duplicate_route_blocked")),
        "restart_recovery_certified": bool(summary.get("restart_recovery_certified")),
        "multi_venue_recovery_certified": bool(summary.get("multi_venue_recovery_certified")),
        "close_verification_enforced": bool(summary.get("close_verification_enforced")),
        "partial_fill_certified": bool(summary.get("partial_fill_certified")),
        "stale_broker_proof_blocked": bool(summary.get("stale_broker_proof_blocked")),
        "failure_state_mapping_certified": bool(summary.get("failure_state_mapping_certified")),
        "broker_requirement_matrix_complete": bool(summary.get("broker_requirement_matrix_complete")),
        "mock_broker_status": summary.get("mock_broker_status") or "",
        "mock_broker_certified": bool(summary.get("mock_broker_certified")),
        "sandbox_paper_status": summary.get("sandbox_paper_status") or "",
        "sandbox_paper_certified": bool(summary.get("sandbox_paper_certified")),
        "sandbox_paper_case_count": int(_as_number(summary.get("sandbox_paper_case_count"), 0)),
        "sandbox_paper_passed_count": int(_as_number(summary.get("sandbox_paper_passed_count"), 0)),
        "sandbox_paper_requirement_count": int(_as_number(summary.get("sandbox_paper_requirement_count"), 0)),
        "sandbox_paper_covered_requirement_count": int(_as_number(summary.get("sandbox_paper_covered_requirement_count"), 0)),
        "sandbox_environment_guard_passed": bool(summary.get("sandbox_environment_guard_passed")),
        "sandbox_no_production_order_endpoints": bool(summary.get("sandbox_no_production_order_endpoints")),
        "sandbox_probe_mode": summary.get("sandbox_probe_mode") or "",
        "no_live_mutation": bool(summary.get("no_live_mutation")),
        "no_ui_mutation_controls": bool(summary.get("no_ui_mutation_controls")),
        "proof_tiers": proof_tiers,
        "sandbox_paper_missing_requirements": summary.get("sandbox_paper_missing_requirements") if isinstance(summary.get("sandbox_paper_missing_requirements"), list) else [],
        "sandbox_paper_blockers": summary.get("sandbox_paper_blockers") if isinstance(summary.get("sandbox_paper_blockers"), list) else [],
        "missing_requirements": payload.get("missing_requirements") if isinstance(payload.get("missing_requirements"), list) else [],
        "blockers": list(dict.fromkeys(blockers))[:20],
        "requirements": payload.get("requirements") if isinstance(payload.get("requirements"), list) else [],
        "cases": payload.get("cases") if isinstance(payload.get("cases"), list) else [],
        "sandbox_paper_requirements": payload.get("sandbox_paper_requirements") if isinstance(payload.get("sandbox_paper_requirements"), list) else [],
        "sandbox_paper_cases": payload.get("sandbox_paper_cases") if isinstance(payload.get("sandbox_paper_cases"), list) else [],
        "snapshot": payload,
    }


def _build_capital_ecosystem_proof(root: Path) -> Dict[str, Any]:
    payload = _read_json(_rooted(root, CAPITAL_ECOSYSTEM_PUBLIC_PATH), {})
    if not isinstance(payload, dict):
        payload = {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    blockers = [str(item) for item in (payload.get("blockers") or []) if str(item)]
    if not payload:
        blockers.append("capital_ecosystem_intelligence_missing")
    ready = bool(payload and payload.get("status") == "capital_ecosystem_intelligence_ready" and not blockers)
    return {
        "state": "capital_ecosystem_intelligence_ready" if ready else "capital_ecosystem_intelligence_attention",
        "path": CAPITAL_ECOSYSTEM_PUBLIC_PATH.as_posix(),
        "present": bool(payload),
        "generated_at": payload.get("generated_at") or "",
        "status": payload.get("status") or "",
        "candidate_count": int(_as_number(summary.get("candidate_count"), 0)),
        "trade_ready_candidate_count": int(_as_number(summary.get("trade_ready_candidate_count"), 0)),
        "active_watchlist_count": int(_as_number(summary.get("active_watchlist_count"), 0)),
        "active_watchlist_limit": int(_as_number(summary.get("active_watchlist_limit"), 0)),
        "bench_watchlist_count": int(_as_number(summary.get("bench_watchlist_count"), 0)),
        "bench_watchlist_limit": int(_as_number(summary.get("bench_watchlist_limit"), 0)),
        "gold_preserved": bool(summary.get("gold_preserved")),
        "shadow_hedge_count": int(_as_number(summary.get("shadow_hedge_count"), 0)),
        "shadow_hedges_only": bool(summary.get("shadow_hedges_only")),
        "close_first_opportunity_count": int(_as_number(summary.get("close_first_opportunity_count"), 0)),
        "active_lifecycle_route_count": int(_as_number(summary.get("active_lifecycle_route_count"), 0)),
        "top_velocity_score": summary.get("top_velocity_score"),
        "no_external_hedge_mutation": bool(summary.get("no_external_hedge_mutation")),
        "existing_runtime_gates_authoritative": bool(summary.get("existing_runtime_gates_authoritative")),
        "top_velocity_candidates": payload.get("top_velocity_candidates") if isinstance(payload.get("top_velocity_candidates"), list) else [],
        "shadow_hedges": payload.get("shadow_hedges") if isinstance(payload.get("shadow_hedges"), list) else [],
        "close_first_opportunities": payload.get("close_first_opportunities") if isinstance(payload.get("close_first_opportunities"), list) else [],
        "blockers": list(dict.fromkeys(blockers))[:20],
        "snapshot": payload,
    }


def _build_capital_live_dry_stress_proof(root: Path) -> Dict[str, Any]:
    payload = _read_json(_rooted(root, CAPITAL_LIVE_DRY_STRESS_PATH), {})
    if not isinstance(payload, dict):
        payload = {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    blockers = [str(item) for item in (payload.get("blockers") or []) if str(item)]
    if not payload:
        blockers.append("capital_live_dry_stress_audit_missing")
    certified = bool(payload and payload.get("status") == "live_dry_certified" and not blockers)
    return {
        "state": "live_dry_certified" if certified else "live_dry_attention",
        "path": CAPITAL_LIVE_DRY_STRESS_PATH.as_posix(),
        "present": bool(payload),
        "generated_at": payload.get("generated_at") or "",
        "status": payload.get("status") or "",
        "runtime_fresh": bool(summary.get("runtime_fresh")),
        "active_watchlist_count": int(_as_number(summary.get("active_watchlist_count"), 0)),
        "bench_watchlist_count": int(_as_number(summary.get("bench_watchlist_count"), 0)),
        "candidate_count": int(_as_number(summary.get("candidate_count"), 0)),
        "active_lifecycle_route_count": int(_as_number(summary.get("active_lifecycle_route_count"), 0)),
        "duplicate_routes_blocked": bool(summary.get("duplicate_routes_blocked")),
        "close_first_opportunity_count": int(_as_number(summary.get("close_first_opportunity_count"), 0)),
        "shadow_hedge_count": int(_as_number(summary.get("shadow_hedge_count"), 0)),
        "shadow_hedges_only": bool(summary.get("shadow_hedges_only")),
        "broker_correlation_complete": bool(summary.get("broker_correlation_complete")),
        "lifecycle_continuity_complete": bool(summary.get("lifecycle_continuity_complete")),
        "recovered_position_count": int(_as_number(summary.get("recovered_position_count"), 0)),
        "recovered_positions_certified": bool(summary.get("recovered_positions_certified")),
        "recovery_certification_status": summary.get("recovery_certification_status") or "",
        "recovered_upstream_context_missing_count": int(_as_number(summary.get("recovered_upstream_context_missing_count"), 0)),
        "recovered_position_close_first_covered": bool(summary.get("recovered_position_close_first_covered")),
        "recovered_duplicate_route_blocking_active": bool(summary.get("recovered_duplicate_route_blocking_active")),
        "recovered_close_chain_status": summary.get("recovered_close_chain_status") or "",
        "recovered_close_request_count": int(_as_number(summary.get("recovered_close_request_count"), 0)),
        "recovered_close_acknowledged_count": int(_as_number(summary.get("recovered_close_acknowledged_count"), 0)),
        "recovered_position_absence_verified_count": int(_as_number(summary.get("recovered_position_absence_verified_count"), 0)),
        "recovered_outcome_recorded_count": int(_as_number(summary.get("recovered_outcome_recorded_count"), 0)),
        "recovered_exit_blockers": summary.get("recovered_exit_blockers") if isinstance(summary.get("recovered_exit_blockers"), list) else [],
        "no_live_mutation": bool(summary.get("no_live_mutation")),
        "blockers": list(dict.fromkeys(blockers))[:20],
        "snapshot": payload,
    }


def _build_capital_revenue_logic_proof(root: Path) -> Dict[str, Any]:
    payload = _read_json(_rooted(root, CAPITAL_REVENUE_LOGIC_STRESS_PATH), {})
    if not isinstance(payload, dict):
        payload = {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    readiness = payload.get("capital_order_intent_readiness") if isinstance(payload.get("capital_order_intent_readiness"), dict) else {}
    blockers = [str(item) for item in (payload.get("blockers") or []) if str(item)]
    if not payload:
        blockers.append("capital_revenue_logic_stress_audit_missing")
    certified = bool(payload and payload.get("status") == "capital_revenue_logic_certified" and not blockers)
    net_positive = payload.get("net_positive_candidates") if isinstance(payload.get("net_positive_candidates"), list) else []
    top_candidate = net_positive[0] if net_positive and isinstance(net_positive[0], dict) else {}
    return {
        "state": "capital_revenue_logic_certified" if certified else "capital_revenue_logic_attention",
        "path": CAPITAL_REVENUE_LOGIC_STRESS_PATH.as_posix(),
        "present": bool(payload),
        "generated_at": payload.get("generated_at") or "",
        "status": payload.get("status") or "",
        "candidate_count": int(_as_number(summary.get("candidate_count"), 0)),
        "trade_ready_candidate_count": int(_as_number(summary.get("trade_ready_candidate_count"), 0)),
        "net_positive_candidate_count": int(_as_number(summary.get("net_positive_candidate_count"), 0)),
        "intent_eligible_candidate_count": int(_as_number(summary.get("intent_eligible_candidate_count"), 0)),
        "candidate_level_intent_eligible_count": int(_as_number(summary.get("candidate_level_intent_eligible_count"), 0)),
        "false_positive_reject_count": int(_as_number(summary.get("false_positive_reject_count"), 0)),
        "active_watchlist_count": int(_as_number(summary.get("active_watchlist_count"), 0)),
        "bench_watchlist_count": int(_as_number(summary.get("bench_watchlist_count"), 0)),
        "close_first_opportunity_count": int(_as_number(summary.get("close_first_opportunity_count"), 0)),
        "duplicate_route_blocked_count": int(_as_number(summary.get("duplicate_route_blocked_count"), 0)),
        "shadow_confirmation_count": int(_as_number(summary.get("shadow_confirmation_count"), 0)),
        "external_shadow_only": bool(summary.get("external_shadow_only")),
        "live_gates_blocking": bool(summary.get("live_gates_blocking") or readiness.get("live_gates_blocking")),
        "no_live_mutation": bool(summary.get("no_live_mutation")),
        "top_candidate": top_candidate,
        "top_expected_net_revenue": top_candidate.get("expected_net_revenue") if top_candidate else None,
        "order_intent_readiness": readiness,
        "blockers": list(dict.fromkeys(blockers))[:20],
        "snapshot": payload,
    }


def _build_capital_revenue_live_gate_readiness_proof(root: Path) -> Dict[str, Any]:
    payload = _read_json(_rooted(root, CAPITAL_REVENUE_LIVE_GATE_READINESS_PATH), {})
    if not isinstance(payload, dict):
        payload = {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    readiness = payload.get("current_live_gate_readiness") if isinstance(payload.get("current_live_gate_readiness"), dict) else {}
    runtime = payload.get("runtime_gate_proof") if isinstance(payload.get("runtime_gate_proof"), dict) else {}
    lifecycle = payload.get("lifecycle_gate_proof") if isinstance(payload.get("lifecycle_gate_proof"), dict) else {}
    close_first = payload.get("close_first_exit_proof") if isinstance(payload.get("close_first_exit_proof"), dict) else {}
    external = payload.get("external_confirmation_proof") if isinstance(payload.get("external_confirmation_proof"), dict) else {}
    blockers = [str(item) for item in (payload.get("blockers") or []) if str(item)]
    if not payload:
        blockers.append("capital_revenue_live_gate_readiness_audit_missing")
    rows = payload.get("candidate_readiness_rows") if isinstance(payload.get("candidate_readiness_rows"), list) else []
    top_row = rows[0] if rows and isinstance(rows[0], dict) else {}
    ready = bool(payload and payload.get("status") == "live_gate_ready" and not blockers)
    return {
        "state": "capital_revenue_live_gate_ready" if ready else "capital_revenue_live_gate_attention",
        "path": CAPITAL_REVENUE_LIVE_GATE_READINESS_PATH.as_posix(),
        "present": bool(payload),
        "generated_at": payload.get("generated_at") or "",
        "status": payload.get("status") or "",
        "net_positive_candidate_count": int(_as_number(summary.get("net_positive_candidate_count"), 0)),
        "ready_now_candidate_count": int(_as_number(summary.get("ready_now_candidate_count"), 0)),
        "blocked_candidate_count": int(_as_number(summary.get("blocked_candidate_count"), 0)),
        "missing_gate_count": int(_as_number(summary.get("missing_gate_count"), 0)),
        "runtime_gates_clear": bool(summary.get("runtime_gates_clear")),
        "recovered_exit_clear": bool(summary.get("recovered_exit_clear")),
        "duplicate_routes_blocked": bool(summary.get("duplicate_routes_blocked")),
        "broker_correlation_complete": bool(summary.get("broker_correlation_complete")),
        "external_shadow_only": bool(summary.get("external_shadow_only")),
        "no_live_mutation": bool(summary.get("no_live_mutation")),
        "missing_gate_ids": readiness.get("missing_gate_ids") if isinstance(readiness.get("missing_gate_ids"), list) else [],
        "top_candidate": top_row,
        "top_expected_net_revenue": top_row.get("expected_net_revenue") if top_row else None,
        "runtime_gate_ids": runtime.get("runtime_gate_ids") if isinstance(runtime.get("runtime_gate_ids"), list) else [],
        "lifecycle_continuity_resolved": bool(lifecycle.get("lifecycle_continuity_resolved")),
        "recovered_close_chain_status": close_first.get("recovered_close_chain_status") or "",
        "external_live_order_intent_count": int(_as_number(external.get("external_live_order_intent_count"), 0)),
        "blockers": list(dict.fromkeys(blockers))[:20],
        "snapshot": payload,
    }


def _goal_trade_state(
    data_capture: Dict[str, Any],
    capital_gold: Dict[str, Any],
    order_intent: Dict[str, Any],
    runtime_gate: Dict[str, Any],
    order_lifecycle: Dict[str, Any],
) -> Dict[str, Any]:
    blockers: List[str] = []
    blockers.extend(data_capture.get("blockers") or [])
    blockers.extend(capital_gold.get("blockers") or [])
    blockers.extend(order_intent.get("blockers") or [])
    blockers.extend(runtime_gate.get("blockers") or [])
    blockers.extend(order_lifecycle.get("blockers") or [])
    submitted = _as_number(runtime_gate.get("submitted_count"), 0) > 0 or _as_number(runtime_gate.get("delegated_count"), 0) > 0
    attempted = _as_number(runtime_gate.get("attempted_count"), 0) > 0
    gold_intent_ready = order_intent.get("state") == "gold_order_intent_ready"
    intent_packet_fresh = bool(order_intent.get("intent_packet_fresh"))
    fresh_data = bool(data_capture.get("fresh_for_order_action")) and not capital_gold.get("blockers")
    executor_ready = bool(runtime_gate.get("executor_enabled")) and not runtime_gate.get("blockers")
    gold_runtime_candidate_ready = bool(runtime_gate.get("gold_runtime_candidate_ready"))
    capital_cfd_route_visible = bool(runtime_gate.get("capital_cfd_route_visible"))
    dry_run_executor_proof_ready = bool(
        gold_intent_ready
        and intent_packet_fresh
        and fresh_data
        and gold_runtime_candidate_ready
        and capital_cfd_route_visible
        and runtime_gate.get("executor_enabled")
        and not runtime_gate.get("stale")
    )
    if fresh_data and not gold_runtime_candidate_ready:
        blockers.append("gold_runtime_candidate_missing")
    if gold_runtime_candidate_ready and not capital_cfd_route_visible:
        blockers.append("capital_cfd_route_missing_for_gold")
    if submitted and gold_intent_ready:
        proof_state = "live_gold_goal_trade_submitted"
    elif attempted and gold_intent_ready:
        proof_state = "live_gold_goal_trade_attempted"
    elif dry_run_executor_proof_ready:
        proof_state = "gold_runtime_gated_intent_proof_ready"
    elif gold_intent_ready and fresh_data and executor_ready:
        proof_state = "gold_goal_order_intent_ready_executor_clear"
    elif gold_intent_ready:
        proof_state = "gold_goal_order_intent_ready_but_gated"
    elif not fresh_data:
        proof_state = "blocked_live_gold_data_not_fresh"
    else:
        proof_state = "blocked_no_gold_order_intent_ready"
    if proof_state == "live_gold_goal_trade_submitted":
        next_action = "Audit live execution evidence, fills, fees, and post-trade risk before claiming profit quality."
    elif proof_state == "blocked_live_gold_data_not_fresh":
        next_action = "Refresh live stream cache and Capital GOLD quote proof before promoting any GOLD order-intent."
    elif proof_state == "blocked_no_gold_order_intent_ready":
        if gold_runtime_candidate_ready:
            reason = str(runtime_gate.get("gold_intent_publish_reason") or "fresh_interval_projection_not_validated")
            next_action = (
                "Keep the fresh Capital GOLD runtime candidate held while resolving "
                f"{reason}; publish a GOLD order-intent only through the existing runtime gate."
            )
        else:
            next_action = "Promote fresh Capital GOLD evidence into the runtime order-flow candidate set, then publish a runtime-gated GOLD order-intent."
    elif proof_state == "gold_runtime_gated_intent_proof_ready":
        next_action = "Runtime-gated GOLD intent proof is ready; audit executor dry-run evidence before any separate live execution step."
    elif proof_state == "gold_goal_order_intent_ready_executor_clear":
        next_action = "Executor is clear for a GOLD intent; require runtime risk/execution proof before claiming a live trade."
    else:
        next_action = "Clear runtime/executor blockers for the existing GOLD order-intent without forcing exchange mutation."
    return {
        "goal_symbol": "GOLD",
        "target_venue": "Capital.com",
        "proof_state": proof_state,
        "live_trade_produced": proof_state == "live_gold_goal_trade_submitted",
        "live_trade_attempted": proof_state in {"live_gold_goal_trade_submitted", "live_gold_goal_trade_attempted"},
        "gold_order_intent_ready": gold_intent_ready,
        "intent_packet_fresh": intent_packet_fresh,
        "gold_runtime_candidate_ready": gold_runtime_candidate_ready,
        "capital_cfd_route_visible": capital_cfd_route_visible,
        "capital_cfd_route_ready": bool(runtime_gate.get("capital_cfd_route_ready")),
        "gold_intent_publish_reason": runtime_gate.get("gold_intent_publish_reason") or "",
        "fresh_data_ready": fresh_data,
        "executor_ready": executor_ready,
        "order_lifecycle_ready": not bool(order_lifecycle.get("blockers")),
        "order_lifecycle_state": order_lifecycle.get("state") or "",
        "order_lifecycle_active_count": order_lifecycle.get("active_lifecycle_count", 0),
        "order_lifecycle_latest_status": order_lifecycle.get("latest_status") or "",
        "dry_run_executor_proof_ready": dry_run_executor_proof_ready,
        "handover_ready": proof_state in {"gold_runtime_gated_intent_proof_ready", "live_gold_goal_trade_submitted"},
        "blocking_count": len([item for item in blockers if item]),
        "blockers": list(dict.fromkeys(str(item) for item in blockers if item))[:20],
        "next_action": next_action,
    }


def build_live_goal_trade_audit(*, root: Optional[Path] = None, now: Optional[datetime] = None) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    now_dt = now or utc_now()
    data_capture = _build_data_capture(root, now_dt)
    capital_gold = _capital_gold_registry(root, now_dt)
    order_intent = _build_order_intent_proof(root, now_dt)
    runtime_gate = _build_runtime_gate(root, now_dt)
    gold_company = _build_gold_company_summary(root)
    order_lifecycle = _build_order_lifecycle_proof(root, runtime_gate)
    order_lifecycle_stress = _build_order_lifecycle_stress_proof(root)
    capital_ecosystem = _build_capital_ecosystem_proof(root)
    capital_live_dry_stress = _build_capital_live_dry_stress_proof(root)
    capital_revenue_logic = _build_capital_revenue_logic_proof(root)
    capital_revenue_live_gate = _build_capital_revenue_live_gate_readiness_proof(root)
    goal_trade = _goal_trade_state(data_capture, capital_gold, order_intent, runtime_gate, order_lifecycle)
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_dt.isoformat(),
        "status": f"live_goal_trade_audit_{goal_trade['proof_state']}",
        "ok": True,
        "mode": "read_only_live_trade_proof",
        "goal": {
            "symbol": "GOLD",
            "venue": "Capital.com",
            "policy": "prove data capture, organism decision, order intent, and executor gate without forcing orders",
        },
        "data_capture": data_capture,
        "capital_gold_profile": capital_gold,
        "organism_decision": {
            "gold_company": gold_company,
            "runtime_decision_self_trust": runtime_gate.get("decision_self_trust") or {},
            "trading_intelligence_path": TRADING_CHECKLIST_PUBLIC_PATH.as_posix(),
        },
        "order_intent_proof": order_intent,
        "order_lifecycle_proof": order_lifecycle,
        "order_lifecycle_stress_proof": order_lifecycle_stress,
        "capital_ecosystem_proof": capital_ecosystem,
        "capital_live_dry_stress_proof": capital_live_dry_stress,
        "capital_revenue_logic_proof": capital_revenue_logic,
        "capital_revenue_live_gate_readiness_proof": capital_revenue_live_gate,
        "runtime_candidate_proof": {
            "gold_runtime_candidate_ready": runtime_gate.get("gold_runtime_candidate_ready"),
            "capital_cfd_route_visible": runtime_gate.get("capital_cfd_route_visible"),
            "capital_cfd_route_ready": runtime_gate.get("capital_cfd_route_ready"),
            "gold_intent_publish_reason": runtime_gate.get("gold_intent_publish_reason") or "",
            "intent_packet_fresh": order_intent.get("intent_packet_fresh"),
            "gold_runtime_trade_proof": runtime_gate.get("gold_runtime_trade_proof") or {},
            "runtime_stall_diagnostic": runtime_gate.get("runtime_stall_diagnostic") or {},
        },
        "executor_gate": runtime_gate,
        "goal_trade_proof": goal_trade,
        "manual_boundaries": [
            "no forced live order",
            "no exchange mutation from this audit",
            "no credential reveal",
            "no payment or filing action",
            "no destructive OS action",
        ],
        "output_files": [
            DEFAULT_STATE_PATH.as_posix(),
            DEFAULT_AUDIT_JSON.as_posix(),
            DEFAULT_AUDIT_MD.as_posix(),
            DEFAULT_PUBLIC_JSON.as_posix(),
        ],
    }
    return report


def _make_markdown(report: Dict[str, Any]) -> str:
    goal = report.get("goal_trade_proof") if isinstance(report.get("goal_trade_proof"), dict) else {}
    data = report.get("data_capture") if isinstance(report.get("data_capture"), dict) else {}
    capital = report.get("capital_gold_profile") if isinstance(report.get("capital_gold_profile"), dict) else {}
    intent = report.get("order_intent_proof") if isinstance(report.get("order_intent_proof"), dict) else {}
    executor = report.get("executor_gate") if isinstance(report.get("executor_gate"), dict) else {}
    stress = report.get("order_lifecycle_stress_proof") if isinstance(report.get("order_lifecycle_stress_proof"), dict) else {}
    ecosystem = report.get("capital_ecosystem_proof") if isinstance(report.get("capital_ecosystem_proof"), dict) else {}
    live_dry = report.get("capital_live_dry_stress_proof") if isinstance(report.get("capital_live_dry_stress_proof"), dict) else {}
    revenue = report.get("capital_revenue_logic_proof") if isinstance(report.get("capital_revenue_logic_proof"), dict) else {}
    live_gate = report.get("capital_revenue_live_gate_readiness_proof") if isinstance(report.get("capital_revenue_live_gate_readiness_proof"), dict) else {}
    lines = [
        "# Aureon Live Goal Trade Audit",
        "",
        f"- Status: `{report.get('status')}`",
        f"- Proof state: `{goal.get('proof_state')}`",
        f"- Live trade produced: `{goal.get('live_trade_produced')}`",
        f"- GOLD order intent ready: `{goal.get('gold_order_intent_ready')}`",
        f"- Fresh data ready: `{goal.get('fresh_data_ready')}`",
        f"- Executor ready: `{goal.get('executor_ready')}`",
        "",
        "## Data Capture",
        f"- Stream cache: `{data.get('state')}` age `{data.get('age_sec')}` sec, tickers `{data.get('ticker_count')}`",
        f"- Capital GOLD: `{capital.get('state')}` assets `{capital.get('gold_asset_count')}`",
        "",
        "## Intent And Executor",
        f"- Intent packet: `{intent.get('state')}` total `{intent.get('intent_count')}` GOLD `{intent.get('gold_intent_count')}`",
        f"- Executor: `{executor.get('state')}` attempted `{executor.get('attempted_count')}` submitted `{executor.get('submitted_count')}`",
        f"- Lifecycle stress: `{stress.get('state')}` cases `{stress.get('passed_count')}/{stress.get('case_count')}` requirements `{stress.get('covered_requirement_count')}/{stress.get('requirement_count')}`",
        f"- Capital ecosystem: `{ecosystem.get('state')}` active watchlist `{ecosystem.get('active_watchlist_count')}/{ecosystem.get('active_watchlist_limit')}` shadow hedges `{ecosystem.get('shadow_hedge_count')}`",
        f"- Capital live dry stress: `{live_dry.get('state')}` status `{live_dry.get('status')}` blockers `{len(live_dry.get('blockers') or [])}`",
        f"- Capital revenue logic: `{revenue.get('state')}` net-positive `{revenue.get('net_positive_candidate_count')}` intent-eligible `{revenue.get('intent_eligible_candidate_count')}` blockers `{len(revenue.get('blockers') or [])}`",
        f"- Capital live-gate readiness: `{live_gate.get('state')}` ready-now `{live_gate.get('ready_now_candidate_count')}` missing gates `{live_gate.get('missing_gate_count')}` blockers `{len(live_gate.get('blockers') or [])}`",
        "",
        "## Blockers",
    ]
    blockers = goal.get("blockers") if isinstance(goal.get("blockers"), list) else []
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- None visible.")
    lines.extend(["", "## Next Action", str(goal.get("next_action") or "")])
    return "\n".join(lines) + "\n"


def build_and_write_live_goal_trade_audit(*, root: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(root or _default_root()).resolve()
    report = build_live_goal_trade_audit(root=root)
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
    parser = argparse.ArgumentParser(description="Audit live GOLD goal-trade proof through Aureon's organism gates.")
    parser.add_argument("--repo-root", default="", help="Repository root; defaults to cwd/repo.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    args = parser.parse_args(argv)
    root = Path(args.repo_root).resolve() if args.repo_root else None
    report = build_and_write_live_goal_trade_audit(root=root)
    print(json.dumps(report, indent=2, sort_keys=True, default=str) if args.json else _make_markdown(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
