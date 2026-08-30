"""Kraken tradable asset and cost registry.

This module gives Aureon a Kraken-native version of the Capital tradable
asset book: every discovered spot pair, which pairs can use margin, what the
minimums and fee tiers look like, and which code route opens, protects, or
closes an order. It is evidence only; live orders still pass through the
runtime gates and Kraken client methods.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sqlite3
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from aureon.exchanges.kraken_client import KrakenClient


SCHEMA_VERSION = "aureon-kraken-tradable-asset-registry-v1"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_JSON = REPO_ROOT / "state/aureon_kraken_tradable_asset_registry.json"
DEFAULT_OUTPUT_JSON = REPO_ROOT / "docs/audits/aureon_kraken_tradable_asset_registry.json"
DEFAULT_OUTPUT_CSV = REPO_ROOT / "docs/audits/aureon_kraken_tradable_asset_registry.csv"
DEFAULT_OUTPUT_MD = REPO_ROOT / "docs/audits/aureon_kraken_tradable_asset_registry.md"
DEFAULT_OUTPUT_DB = REPO_ROOT / "state/kraken_tradable_asset_registry.sqlite"
DEFAULT_PUBLIC_JSON = REPO_ROOT / "frontend/public/aureon_kraken_tradable_asset_registry.json"

CSV_FIELDS = [
    "symbol",
    "internal_pair",
    "wsname",
    "base_asset",
    "quote_asset",
    "asset_class",
    "spot_trade_ready",
    "margin_trade_ready",
    "snapshot_status",
    "bid",
    "ask",
    "mid_price",
    "spread",
    "spread_pct",
    "ordermin",
    "costmin",
    "lot_decimals",
    "pair_decimals",
    "lot_step",
    "tick_size",
    "entry_maker_fee_pct",
    "entry_taker_fee_pct",
    "lowest_maker_fee_pct",
    "lowest_taker_fee_pct",
    "margin_supported",
    "leverage_buy",
    "leverage_sell",
    "max_leverage",
    "min_notional_estimate",
    "min_margin_required_estimate",
    "blockers",
    "spot_buy_call",
    "spot_sell_call",
    "limit_buy_call",
    "take_profit_call",
    "margin_long_call",
    "margin_short_call",
    "margin_close_call",
]

FIAT_QUOTES = {"USD", "USDC", "USDT", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF"}
TICKER_RECEIPT_MAX_AGE_SECONDS = 60.0


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
        return int(float(value))
    except Exception:
        return default


def _numeric_free_no_data(reason: str) -> dict[str, Any]:
    return {
        "data_status": "no_data",
        "truth_status": "no_data",
        "generated_values": False,
        "action": False,
        "accounting": False,
        "learning": False,
        "reason": reason,
    }


def _complete_ticker_receipt(receipt: Any, *, now: Optional[float] = None) -> tuple[Optional[dict[str, Any]], str]:
    """Accept only a complete fresh provider ticker receipt without defaults."""
    if not isinstance(receipt, dict):
        return None, "ticker_receipt_missing"
    if (
        receipt.get("data_status") != "live"
        or receipt.get("truth_status") != "real_observed"
        or receipt.get("generated_values") is not False
        or receipt.get("action") is not False
        or receipt.get("accounting") is not False
        or receipt.get("learning") is not False
    ):
        return None, "ticker_receipt_provenance_invalid"
    source_id = receipt.get("source_id")
    receipt_id = receipt.get("receipt_id")
    if not isinstance(source_id, str) or not source_id.strip() or not isinstance(receipt_id, str) or not receipt_id.strip():
        return None, "ticker_receipt_identifiers_missing"
    values: dict[str, float] = {}
    for field in ("price", "bid", "ask", "open_price", "volume_24h", "source_timestamp", "received_at"):
        value = _as_float(receipt.get(field), float("nan"))
        if not math.isfinite(value):
            return None, f"ticker_receipt_{field}_invalid"
        values[field] = value
    if values["price"] <= 0 or values["bid"] <= 0 or values["ask"] <= 0 or values["open_price"] <= 0 or values["volume_24h"] < 0:
        return None, "ticker_receipt_numeric_invalid"
    if values["ask"] < values["bid"]:
        return None, "ticker_receipt_crossed_book"
    checked_at = time.time() if now is None else now
    if not math.isfinite(checked_at) or values["source_timestamp"] > checked_at + 5.0:
        return None, "ticker_receipt_source_time_future"
    if checked_at - values["source_timestamp"] > TICKER_RECEIPT_MAX_AGE_SECONDS:
        return None, "ticker_receipt_source_time_stale"
    if values["received_at"] + 5.0 < values["source_timestamp"]:
        return None, "ticker_receipt_received_before_source"
    return values, ""


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_asset(value: Any) -> str:
    text = _clean_text(value).upper()
    mapping = {
        "XXBT": "BTC",
        "XBT": "BTC",
        "XETH": "ETH",
        "XLTC": "LTC",
        "XXRP": "XRP",
        "XXLM": "XLM",
        "XXDG": "DOGE",
        "ZEUR": "EUR",
        "ZUSD": "USD",
        "ZGBP": "GBP",
        "ZCAD": "CAD",
        "ZJPY": "JPY",
        "ZAUD": "AUD",
    }
    return mapping.get(text, text.lstrip("XZ") if len(text) > 3 and text[:1] in {"X", "Z"} else text)


def _asset_class(base: str, quote: str) -> str:
    quote = quote.upper()
    base = base.upper()
    if quote in FIAT_QUOTES or quote.endswith("USD"):
        return "crypto_fiat_or_stable_pair"
    if quote in {"BTC", "ETH"} or base in {"BTC", "ETH"}:
        return "crypto_cross_pair"
    return "crypto_spot_pair"


def _fee_tiers(tiers: Any) -> dict[str, Any]:
    rows: list[dict[str, float]] = []
    if isinstance(tiers, list):
        for row in tiers:
            if not isinstance(row, (list, tuple)) or len(row) < 2:
                continue
            rows.append({"volume": _as_float(row[0], 0.0), "fee_pct": _as_float(row[1], 0.0)})
    rows.sort(key=lambda item: item["volume"])
    entry_fee = rows[0]["fee_pct"] if rows else 0.0
    lowest_fee = min((row["fee_pct"] for row in rows), default=entry_fee)
    return {
        "entry_fee_pct": entry_fee,
        "lowest_fee_pct": lowest_fee,
        "tiers": rows[:12],
    }


def _first_fee_pct(asset: dict[str, Any], order_type: str = "market", post_only: bool = False) -> float:
    if post_only or order_type.lower() in {"limit_maker", "maker"}:
        return _as_float(asset.get("entry_maker_fee_pct"), 0.0)
    return _as_float(asset.get("entry_taker_fee_pct"), 0.0)


def _execution_routes(symbol: str, margin_supported: bool) -> dict[str, str]:
    return {
        "owner": "aureon.exchanges.kraken_client.KrakenClient",
        "spot_buy_code_path": "aureon.exchanges.kraken_client.KrakenClient.place_market_order",
        "spot_sell_code_path": "aureon.exchanges.kraken_client.KrakenClient.place_market_order",
        "limit_order_code_path": "aureon.exchanges.kraken_client.KrakenClient.place_limit_order",
        "take_profit_code_path": "aureon.exchanges.kraken_client.KrakenClient.place_take_profit_order",
        "margin_order_code_path": "aureon.exchanges.kraken_client.KrakenClient.place_margin_order" if margin_supported else "",
        "margin_close_code_path": "aureon.exchanges.kraken_client.KrakenClient.close_margin_position" if margin_supported else "",
        "spot_buy_call": f'client.place_market_order("{symbol}", "buy", quantity=base_qty)',
        "spot_sell_call": f'client.place_market_order("{symbol}", "sell", quantity=base_qty)',
        "limit_buy_call": f'client.place_limit_order("{symbol}", "buy", quantity=base_qty, price=limit_price, post_only=True)',
        "limit_sell_call": f'client.place_limit_order("{symbol}", "sell", quantity=base_qty, price=limit_price, post_only=True)',
        "take_profit_call": f'client.place_take_profit_order("{symbol}", close_side, quantity=base_qty, take_profit_price=target_price)',
        "margin_long_call": f'client.place_margin_order("{symbol}", "buy", quantity=base_qty, leverage=leverage, take_profit=target_price, stop_loss=stop_price)' if margin_supported else "",
        "margin_short_call": f'client.place_margin_order("{symbol}", "sell", quantity=base_qty, leverage=leverage, take_profit=target_price, stop_loss=stop_price)' if margin_supported else "",
        "margin_close_call": f'client.close_margin_position("{symbol}", close_side, volume=base_qty)' if margin_supported else "",
        "cancel_call": "client.cancel_order(order_id)",
        "rest_order_route": "POST /0/private/AddOrder",
        "rest_cancel_route": "POST /0/private/CancelOrder",
    }


def _snapshot_budget(max_tickers: Optional[int], total_pairs: int) -> int:
    if max_tickers is None:
        max_tickers = int(os.getenv("KRAKEN_ASSET_REGISTRY_MAX_TICKERS", "100") or "100")
    if max_tickers < 0:
        return total_pairs
    return max_tickers


def _ticker_snapshot(client: KrakenClient, symbol: str) -> tuple[dict[str, Any], str, str]:
    try:
        adapter = getattr(client, "get_ticker_receipt", None)
        if not callable(adapter):
            return {}, "no_data", "ticker_receipt_adapter_unavailable"
        receipt = adapter(symbol)
        values, reason = _complete_ticker_receipt(receipt)
        if values is None:
            return {}, "no_data", reason
        bid = values["bid"]
        ask = values["ask"]
        mid = (bid + ask) / 2.0
        spread = ask - bid
        return {
            "bid": bid,
            "ask": ask,
            "mid_price": mid,
            "spread": spread,
            "spread_pct": spread / mid * 100.0,
            "receipt": receipt,
        }, "fresh_ticker", ""
    except Exception as exc:
        return {}, "no_data", f"ticker_receipt_error:{exc}"


def _asset_from_pair(
    *,
    internal: str,
    info: dict[str, Any],
    ticker: dict[str, float],
    snapshot_status: str,
    snapshot_error: str = "",
) -> dict[str, Any]:
    altname = _clean_text(info.get("altname")) or internal
    wsname = _clean_text(info.get("wsname"))
    base = _normalize_asset(info.get("base"))
    quote = _normalize_asset(info.get("quote"))
    if (not base or not quote) and "/" in wsname:
        left, right = wsname.split("/", 1)
        base = base or _normalize_asset(left)
        quote = quote or _normalize_asset(right)

    leverage_buy = [_as_int(item) for item in (info.get("leverage_buy") or []) if _as_int(item) > 0]
    leverage_sell = [_as_int(item) for item in (info.get("leverage_sell") or []) if _as_int(item) > 0]
    max_leverage = max(leverage_buy + leverage_sell) if (leverage_buy or leverage_sell) else 1
    margin_supported = bool(leverage_buy or leverage_sell)
    lot_decimals = _as_int(info.get("lot_decimals"), 8)
    pair_decimals = _as_int(info.get("pair_decimals"), 8)
    lot_step = 10 ** (-lot_decimals) if lot_decimals >= 0 else 0.0
    tick_size = 10 ** (-pair_decimals) if pair_decimals >= 0 else 0.0
    ordermin = _as_float(info.get("ordermin"), lot_step)
    costmin = _as_float(info.get("costmin"), 0.0)
    maker_fees = _fee_tiers(info.get("fees_maker"))
    taker_fees = _fee_tiers(info.get("fees"))
    if maker_fees["entry_fee_pct"] <= 0 and taker_fees["entry_fee_pct"] > 0:
        maker_fees = {**maker_fees, "entry_fee_pct": taker_fees["entry_fee_pct"], "lowest_fee_pct": taker_fees["lowest_fee_pct"]}

    mid_price = ticker.get("mid_price") if snapshot_status == "fresh_ticker" else None
    min_notional = costmin if costmin > 0 else (ordermin * mid_price if ordermin > 0 and isinstance(mid_price, float) and mid_price > 0 else 0.0)
    min_margin = (min_notional / max_leverage) if margin_supported and max_leverage > 0 else 0.0

    blockers: list[str] = []
    if snapshot_status != "fresh_ticker":
        blockers.append(snapshot_status)
    if snapshot_error:
        blockers.append("ticker_error")
    if not base or not quote:
        blockers.append("base_or_quote_unknown")
    if ordermin <= 0:
        blockers.append("ordermin_unknown")
    if min_notional <= 0:
        blockers.append("min_notional_unknown")
    if taker_fees["entry_fee_pct"] <= 0:
        blockers.append("fee_tier_unknown")

    spot_trade_ready = not blockers
    margin_trade_ready = spot_trade_ready and margin_supported
    routes = _execution_routes(altname, margin_supported)
    return {
        "symbol": altname,
        "internal_pair": internal,
        "wsname": wsname,
        "base_asset": base,
        "quote_asset": quote,
        "asset_class": _asset_class(base, quote),
        "snapshot_status": snapshot_status,
        "snapshot_error": snapshot_error,
        "market_receipt": ticker.get("receipt") if snapshot_status == "fresh_ticker" else _numeric_free_no_data(snapshot_error or snapshot_status),
        "market_data_status": "live" if snapshot_status == "fresh_ticker" else "no_data",
        "bid": ticker.get("bid") if snapshot_status == "fresh_ticker" else None,
        "ask": ticker.get("ask") if snapshot_status == "fresh_ticker" else None,
        "mid_price": mid_price,
        "spread": ticker.get("spread") if snapshot_status == "fresh_ticker" else None,
        "spread_pct": ticker.get("spread_pct") if snapshot_status == "fresh_ticker" else None,
        "ordermin": ordermin,
        "costmin": costmin,
        "lot_decimals": lot_decimals,
        "pair_decimals": pair_decimals,
        "lot_step": lot_step,
        "tick_size": tick_size,
        "entry_maker_fee_pct": maker_fees["entry_fee_pct"],
        "entry_taker_fee_pct": taker_fees["entry_fee_pct"],
        "lowest_maker_fee_pct": maker_fees["lowest_fee_pct"],
        "lowest_taker_fee_pct": taker_fees["lowest_fee_pct"],
        "maker_fee_tiers": maker_fees["tiers"],
        "taker_fee_tiers": taker_fees["tiers"],
        "margin_supported": margin_supported,
        "leverage_buy": leverage_buy,
        "leverage_sell": leverage_sell,
        "max_leverage": max_leverage,
        "min_notional_estimate": min_notional,
        "min_margin_required_estimate": min_margin,
        "spot_trade_ready": spot_trade_ready,
        "margin_trade_ready": margin_trade_ready,
        "action": False,
        "accounting": False,
        "learning": False,
        "blockers": blockers,
        **routes,
    }


def build_kraken_asset_registry(
    *,
    client: Optional[KrakenClient] = None,
    force_refresh: bool = False,
    max_tickers: Optional[int] = None,
) -> dict[str, Any]:
    client = client or KrakenClient()
    generated_at = utc_now()
    errors: list[str] = []
    try:
        pairs = dict(client._load_asset_pairs(force=force_refresh) or {})  # type: ignore[attr-defined]
    except Exception as exc:
        pairs = {}
        errors.append(f"asset_pairs_error:{exc}")

    budget = _snapshot_budget(max_tickers, len(pairs))
    assets: list[dict[str, Any]] = []
    for index, (internal, info) in enumerate(sorted(pairs.items())):
        if not isinstance(info, dict):
            continue
        symbol = _clean_text(info.get("altname")) or internal
        if index < budget:
            ticker, snapshot_status, snapshot_error = _ticker_snapshot(client, symbol)
        else:
            ticker, snapshot_status, snapshot_error = (
                {},
                "no_data",
                "",
            )
        assets.append(
            _asset_from_pair(
                internal=internal,
                info=info,
                ticker=ticker,
                snapshot_status=snapshot_status,
                snapshot_error=snapshot_error,
            )
        )

    asset_class_counts = Counter(asset.get("asset_class", "unknown") for asset in assets)
    blocker_counts: Counter[str] = Counter()
    for asset in assets:
        blocker_counts.update(asset.get("blockers", []) or [])

    margin_pairs = [asset for asset in assets if asset.get("margin_supported")]
    spot_ready = [asset for asset in assets if asset.get("spot_trade_ready")]
    margin_ready = [asset for asset in assets if asset.get("margin_trade_ready")]
    summary = {
        "total_pairs": len(assets),
        "ticker_budget": budget,
        "ticker_enriched_count": sum(1 for asset in assets if asset.get("snapshot_status") == "fresh_ticker"),
        "known_but_not_sampled_count": max(0, len(assets) - min(budget, len(assets))),
        "spot_trade_ready_count": len(spot_ready),
        "margin_pair_count": len(margin_pairs),
        "margin_trade_ready_count": len(margin_ready),
        "cost_known_count": sum(1 for asset in assets if _as_float(asset.get("min_notional_estimate"), 0.0) > 0),
        "fee_known_count": sum(1 for asset in assets if _as_float(asset.get("entry_taker_fee_pct"), 0.0) > 0),
        "take_profit_route_count": sum(1 for asset in assets if asset.get("take_profit_call")),
        "asset_classes": dict(sorted(asset_class_counts.items())),
        "top_blockers": [{"name": key, "count": value} for key, value in blocker_counts.most_common(12)],
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "source": "aureon.exchanges.kraken_asset_registry",
        "catalogue_source": "Kraken /0/public/AssetPairs",
        "ticker_source": "Kraken /0/public/Ticker via KrakenClient.get_ticker",
        "official_basis": [
            "https://docs.kraken.com/api/docs/rest-api/get-tradable-asset-pairs/",
            "https://docs.kraken.com/api/docs/rest-api/add-order/",
            "https://support.kraken.com/articles/201893638-how-trading-fees-work-on-kraken",
            "https://support.kraken.com/articles/206161568-what-are-the-fees-opening-and-rollover-for-trading-using-margin-",
        ],
        "execution_contract": {
            "owner": "aureon.exchanges.kraken_client.KrakenClient",
            "spot_market_buy": 'KrakenClient.place_market_order(symbol, "buy", quantity=base_qty)',
            "spot_market_sell": 'KrakenClient.place_market_order(symbol, "sell", quantity=base_qty)',
            "limit_post_only": 'KrakenClient.place_limit_order(symbol, side, quantity, price, post_only=True)',
            "spot_take_profit": "KrakenClient.place_take_profit_order(symbol, close_side, quantity, take_profit_price)",
            "margin_long": 'KrakenClient.place_margin_order(symbol, "buy", quantity, leverage, take_profit=target, stop_loss=stop)',
            "margin_short": 'KrakenClient.place_margin_order(symbol, "sell", quantity, leverage, take_profit=target, stop_loss=stop)',
            "margin_reduce_only_close": "KrakenClient.close_margin_position(symbol, close_side, volume)",
            "rest_order_route": "POST /0/private/AddOrder",
            "note": "Registry records tradability, costs, and route evidence only; runtime gates still own live execution.",
        },
        "survival_policy": kraken_survival_policy(),
        "summary": summary,
        "errors": errors,
        "assets": assets,
        "data_status": "live" if assets and all(asset.get("market_data_status") == "live" for asset in assets) else "no_data",
        "truth_status": "real_derived" if assets and all(asset.get("market_data_status") == "live" for asset in assets) else "no_data",
        "generated_values": False,
        "action": False,
        "accounting": False,
        "learning": False,
    }
    if report["data_status"] != "live":
        report["no_data_reason"] = "incomplete_or_unobserved_ticker_receipts"
    report["audit"] = audit_kraken_asset_registry(report)
    return report


def _report_has_sensitive_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(hint in lowered for hint in ("api_key", "apikey", "secret", "token", "passphrase", "password", "private_key")):
                return True
            if _report_has_sensitive_key(nested):
                return True
    elif isinstance(value, list):
        return any(_report_has_sensitive_key(item) for item in value)
    return False


def audit_kraken_asset_registry(report: dict[str, Any]) -> dict[str, Any]:
    """Return operator-readable pass/fail checks for the Kraken registry."""
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    assets = list(report.get("assets", []) or [])
    official_basis = list(report.get("official_basis", []) or [])
    contract = report.get("execution_contract", {}) if isinstance(report.get("execution_contract"), dict) else {}
    policy = report.get("survival_policy", {}) if isinstance(report.get("survival_policy"), dict) else {}

    def check(name: str, passed: bool, detail: str) -> dict[str, Any]:
        return {"name": name, "passed": bool(passed), "detail": detail}

    route_keys = ("spot_market_buy", "spot_market_sell", "limit_post_only", "spot_take_profit", "margin_long", "margin_short")
    checks = [
        check("schema_version", report.get("schema_version") == SCHEMA_VERSION, str(report.get("schema_version") or "")),
        check("official_basis_present", len(official_basis) >= 4, f"{len(official_basis)} official/source URLs"),
        check("asset_pairs_present", _as_int(summary.get("total_pairs")) > 0, f"{summary.get('total_pairs', 0)} pairs"),
        check("ticker_budget_declared", summary.get("ticker_budget") is not None, f"budget={summary.get('ticker_budget')}"),
        check("spot_route_declared", all(contract.get(key) for key in ("spot_market_buy", "spot_market_sell")), "spot buy/sell routes"),
        check("take_profit_route_declared", bool(contract.get("spot_take_profit")), "take-profit route"),
        check("margin_route_declared", all(contract.get(key) for key in ("margin_long", "margin_short", "margin_reduce_only_close")), "margin long/short/close routes"),
        check("asset_route_fields_present", all(asset.get("spot_buy_call") and asset.get("spot_sell_call") for asset in assets[:50]), "sampled first 50 assets"),
        check("fee_evidence_present", _as_int(summary.get("fee_known_count")) > 0, f"{summary.get('fee_known_count', 0)} pairs with fees"),
        check("cost_evidence_present", _as_int(summary.get("cost_known_count")) > 0, f"{summary.get('cost_known_count', 0)} pairs with cost minimums"),
        check("margin_evidence_present", _as_int(summary.get("margin_pair_count")) > 0, f"{summary.get('margin_pair_count', 0)} margin-capable pairs"),
        check("survival_policy_present", bool(policy), "pending-order survival policy"),
        check("submission_default_guarded", policy.get("pending_order_submission_enabled") is False, "pending submission off unless explicitly enabled"),
        check("secret_key_scan", not _report_has_sensitive_key(report), "no credential-like keys emitted"),
    ]
    passed_count = sum(1 for item in checks if item["passed"])
    return {
        "schema_version": "kraken-registry-audit-v1",
        "generated_at": utc_now(),
        "status": "passed" if passed_count == len(checks) else "attention",
        "passed_count": passed_count,
        "check_count": len(checks),
        "score_pct": round((passed_count / len(checks) * 100.0), 2) if checks else 0.0,
        "checks": checks,
        "route_keys_checked": list(route_keys),
    }


def kraken_survival_policy() -> dict[str, Any]:
    return {
        "pending_order_planning_enabled": _env_bool("KRAKEN_PENDING_ORDER_PLANNING_ENABLED", True),
        "pending_order_submission_enabled": _env_bool("KRAKEN_PENDING_ORDER_SUBMIT_ENABLED", False),
        "max_pending_orders": _env_int("KRAKEN_MAX_PENDING_ORDERS", 8),
        "max_pending_per_pair": _env_int("KRAKEN_MAX_PENDING_PER_PAIR", 2),
        "spot_quote_budget_pct": _env_float("KRAKEN_PENDING_SPOT_QUOTE_BUDGET_PCT", 35.0),
        "margin_budget_pct": _env_float("KRAKEN_PENDING_MARGIN_BUDGET_PCT", 20.0),
        "min_margin_level_pct": _env_float("KRAKEN_MIN_MARGIN_LEVEL_PCT", 250.0),
        "stress_move_pct_crypto": _env_float("KRAKEN_STRESS_MOVE_PCT_CRYPTO", 5.0),
        "loss_close_policy": os.getenv("KRAKEN_LOSS_CLOSE_POLICY", "never_self_close_loss"),
        "require_who_what_where_when_how": _env_bool("KRAKEN_REQUIRE_WHO_WHAT_WHERE_WHEN_HOW", True),
        "require_cross_exchange_confirmation": _env_bool("KRAKEN_REQUIRE_CROSS_EXCHANGE_CONFIRMATION", True),
    }


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(float(raw))
    except Exception:
        return default


def _balance_amount(balances: dict[str, Any], *assets: str) -> float:
    aliases = {asset.upper() for asset in assets}
    aliases |= {f"Z{asset.upper()}" for asset in assets}
    aliases |= {"XBT" if asset.upper() == "BTC" else asset.upper() for asset in assets}
    total = 0.0
    for asset, value in (balances or {}).items():
        if str(asset).upper() in aliases:
            total += _as_float(value, 0.0)
    return total


def build_kraken_order_survival_envelope(
    *,
    planned_orders: list[dict[str, Any]],
    existing_open_orders: Optional[list[dict[str, Any]]] = None,
    balances: Optional[dict[str, Any]] = None,
    trade_balance: Optional[dict[str, Any]] = None,
    registry_assets: Optional[dict[str, dict[str, Any]]] = None,
    quote_asset: str = "USD",
    policy: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Stress pending Kraken spot/margin orders as if every order fills.

    This is deliberately conservative. It estimates spot quote consumption,
    margin collateral, maker/taker trade fees, and a stress move against all
    margin orders before any pending order ladder is allowed to submit.
    """

    policy = {**kraken_survival_policy(), **(policy or {})}
    orders = list(planned_orders or [])
    existing = list(existing_open_orders or [])
    balances = dict(balances or {})
    trade_balance = dict(trade_balance or {})
    registry_assets = dict(registry_assets or {})
    blockers: list[str] = []

    if not policy.get("pending_order_planning_enabled", True):
        blockers.append("pending_order_planning_disabled")
    if not policy.get("pending_order_submission_enabled", False):
        blockers.append("pending_order_submission_disabled")

    max_orders = int(policy.get("max_pending_orders", 8) or 8)
    max_per_pair = int(policy.get("max_pending_per_pair", 2) or 2)
    total_pending_count = len(orders) + len(existing)
    if total_pending_count > max_orders:
        blockers.append("max_pending_orders")

    per_pair: Counter[str] = Counter()
    for order in orders + existing:
        per_pair.update([_clean_text(order.get("symbol") or order.get("pair"))])
    over_pair = [pair for pair, count in per_pair.items() if pair and count > max_per_pair]
    if over_pair:
        blockers.append("max_pending_per_pair")

    free_quote = _balance_amount(balances, quote_asset, "USD", "USDC", "USDT")
    free_margin = _as_float(trade_balance.get("free_margin") or trade_balance.get("mf"), 0.0)
    equity = _as_float(trade_balance.get("equity_value") or trade_balance.get("e"), 0.0)
    margin_used = _as_float(trade_balance.get("margin_amount") or trade_balance.get("m"), 0.0)
    current_margin_level = _as_float(trade_balance.get("margin_level") or trade_balance.get("ml"), 0.0)

    spot_required = 0.0
    margin_required = 0.0
    fee_estimate = 0.0
    stress_loss = 0.0
    normalized_orders: list[dict[str, Any]] = []
    for order in orders:
        symbol = _clean_text(order.get("symbol") or order.get("pair"))
        asset = registry_assets.get(symbol) or registry_assets.get(symbol.replace("/", "")) or {}
        qty = _as_float(order.get("quantity") or order.get("volume") or order.get("base_qty"), 0.0)
        price = _as_float(order.get("price") or order.get("limit_price") or asset.get("mid_price"), 0.0)
        notional = qty * price
        side = _clean_text(order.get("side")).lower()
        order_type = _clean_text(order.get("order_type") or order.get("type") or "limit").lower()
        post_only = bool(order.get("post_only", order.get("postOnly", False)))
        margin = bool(order.get("margin")) or _as_float(order.get("leverage"), 1.0) > 1.0
        leverage = max(1.0, _as_float(order.get("leverage"), 1.0))
        fee_pct = _first_fee_pct(asset, order_type=order_type, post_only=post_only)
        fee = notional * fee_pct / 100.0
        fee_estimate += fee
        order_margin_required = 0.0
        order_spot_required = 0.0
        order_stress_loss = 0.0
        order_blockers: list[str] = []
        if qty <= 0:
            order_blockers.append("quantity_missing")
        if price <= 0:
            order_blockers.append("price_missing")
        if margin:
            order_margin_required = notional / leverage if leverage > 0 else notional
            order_stress_loss = notional * _as_float(policy.get("stress_move_pct_crypto"), 5.0) / 100.0
        elif side == "buy":
            order_spot_required = notional + fee
        elif side == "sell":
            order_blockers.append("spot_sell_requires_base_inventory_check")
        margin_required += order_margin_required
        spot_required += order_spot_required
        stress_loss += order_stress_loss
        normalized_orders.append(
            {
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "post_only": post_only,
                "margin": margin,
                "leverage": leverage,
                "quantity": qty,
                "price": price,
                "notional": notional,
                "fee_pct": fee_pct,
                "fee_estimate": fee,
                "spot_quote_required": order_spot_required,
                "margin_required": order_margin_required,
                "stress_loss_estimate": order_stress_loss,
                "blockers": order_blockers,
            }
        )
        blockers.extend(order_blockers)

    spot_budget = free_quote * _as_float(policy.get("spot_quote_budget_pct"), 35.0) / 100.0
    margin_budget = free_margin * _as_float(policy.get("margin_budget_pct"), 20.0) / 100.0 if free_margin > 0 else 0.0
    if spot_required > max(0.0, spot_budget):
        blockers.append("spot_quote_budget_would_be_breached")
    if margin_required + stress_loss > max(0.0, margin_budget) and margin_required > 0:
        blockers.append("margin_budget_would_be_breached")

    projected_margin_used = margin_used + margin_required + stress_loss
    projected_margin_level = (equity / projected_margin_used * 100.0) if projected_margin_used > 0 and equity > 0 else current_margin_level
    min_margin_level = _as_float(policy.get("min_margin_level_pct"), 250.0)
    if margin_required > 0 and projected_margin_level > 0 and projected_margin_level < min_margin_level:
        blockers.append("projected_margin_level_below_minimum")

    blockers = sorted(set(blockers))
    return {
        "schema_version": "kraken-order-survival-envelope-v1",
        "generated_at": utc_now(),
        "can_submit_pending_orders": not blockers,
        "submission_enabled": bool(policy.get("pending_order_submission_enabled", False)),
        "blockers": blockers,
        "policy": policy,
        "pending_order_count": total_pending_count,
        "planned_order_count": len(orders),
        "existing_open_order_count": len(existing),
        "per_pair_counts": dict(per_pair),
        "over_pair_limits": over_pair,
        "free_quote_estimate": free_quote,
        "spot_quote_budget": spot_budget,
        "spot_quote_required_if_all_fill": spot_required,
        "free_margin": free_margin,
        "margin_budget": margin_budget,
        "margin_required_if_all_fill": margin_required,
        "fee_estimate_if_all_fill": fee_estimate,
        "stress_loss_if_all_margin_moves_against_us": stress_loss,
        "current_margin_level_pct": current_margin_level,
        "projected_margin_level_pct": projected_margin_level,
        "orders": normalized_orders,
        "loss_close_policy": policy.get("loss_close_policy", "never_self_close_loss"),
        "note": "Pending Kraken plans are safe only if every resting order can fill together without exhausting spot quote or margin survival buffers.",
    }


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    os.replace(tmp, path)
    return path


def _write_csv(path: Path, assets: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for asset in assets:
            row = {field: asset.get(field, "") for field in CSV_FIELDS}
            row["blockers"] = ";".join(asset.get("blockers", []) or [])
            row["leverage_buy"] = ";".join(str(item) for item in asset.get("leverage_buy", []) or [])
            row["leverage_sell"] = ";".join(str(item) for item in asset.get("leverage_sell", []) or [])
            writer.writerow(row)
    os.replace(tmp, path)
    return path


def _write_sqlite(path: Path, report: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=15)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS kraken_assets (
                symbol TEXT PRIMARY KEY,
                internal_pair TEXT,
                wsname TEXT,
                base_asset TEXT,
                quote_asset TEXT,
                asset_class TEXT,
                spot_trade_ready INTEGER,
                margin_trade_ready INTEGER,
                snapshot_status TEXT,
                bid REAL,
                ask REAL,
                mid_price REAL,
                spread REAL,
                spread_pct REAL,
                ordermin REAL,
                costmin REAL,
                entry_maker_fee_pct REAL,
                entry_taker_fee_pct REAL,
                margin_supported INTEGER,
                leverage_buy TEXT,
                leverage_sell TEXT,
                max_leverage REAL,
                min_notional_estimate REAL,
                min_margin_required_estimate REAL,
                blockers TEXT,
                spot_buy_call TEXT,
                margin_long_call TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS registry_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute("DELETE FROM kraken_assets")
        conn.execute("DELETE FROM registry_metadata")
        generated_at = str(report.get("generated_at") or utc_now())
        rows = []
        for asset in report.get("assets", []) or []:
            rows.append(
                (
                    asset.get("symbol", ""),
                    asset.get("internal_pair", ""),
                    asset.get("wsname", ""),
                    asset.get("base_asset", ""),
                    asset.get("quote_asset", ""),
                    asset.get("asset_class", ""),
                    1 if asset.get("spot_trade_ready") else 0,
                    1 if asset.get("margin_trade_ready") else 0,
                    asset.get("snapshot_status", ""),
                    _as_float(asset.get("bid"), 0.0),
                    _as_float(asset.get("ask"), 0.0),
                    _as_float(asset.get("mid_price"), 0.0),
                    _as_float(asset.get("spread"), 0.0),
                    _as_float(asset.get("spread_pct"), 0.0),
                    _as_float(asset.get("ordermin"), 0.0),
                    _as_float(asset.get("costmin"), 0.0),
                    _as_float(asset.get("entry_maker_fee_pct"), 0.0),
                    _as_float(asset.get("entry_taker_fee_pct"), 0.0),
                    1 if asset.get("margin_supported") else 0,
                    ";".join(str(item) for item in asset.get("leverage_buy", []) or []),
                    ";".join(str(item) for item in asset.get("leverage_sell", []) or []),
                    _as_float(asset.get("max_leverage"), 0.0),
                    _as_float(asset.get("min_notional_estimate"), 0.0),
                    _as_float(asset.get("min_margin_required_estimate"), 0.0),
                    ";".join(asset.get("blockers", []) or []),
                    asset.get("spot_buy_call", ""),
                    asset.get("margin_long_call", ""),
                    generated_at,
                )
            )
        conn.executemany(
            """
            INSERT OR REPLACE INTO kraken_assets (
                symbol, internal_pair, wsname, base_asset, quote_asset, asset_class,
                spot_trade_ready, margin_trade_ready, snapshot_status, bid, ask,
                mid_price, spread, spread_pct, ordermin, costmin, entry_maker_fee_pct,
                entry_taker_fee_pct, margin_supported, leverage_buy, leverage_sell,
                max_leverage, min_notional_estimate, min_margin_required_estimate,
                blockers, spot_buy_call, margin_long_call, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        metadata = {
            "schema_version": report.get("schema_version", ""),
            "generated_at": report.get("generated_at", ""),
            "summary": json.dumps(report.get("summary", {}), sort_keys=True),
        }
        conn.executemany("INSERT OR REPLACE INTO registry_metadata (key, value) VALUES (?, ?)", metadata.items())
        conn.commit()
    finally:
        conn.close()
    return path


def _write_markdown(path: Path, report: dict[str, Any]) -> Path:
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    audit = report.get("audit", {}) if isinstance(report.get("audit"), dict) else {}
    lines = [
        "# Aureon Kraken Tradable Asset Registry",
        "",
        f"Generated: {report.get('generated_at', '')}",
        f"Schema: {report.get('schema_version', SCHEMA_VERSION)}",
        "",
        "This registry records Kraken spot and margin pair metadata, minimum order/cost evidence, maker/taker fee tiers, leverage availability, and the Aureon code route used to buy, sell, protect, or reduce-only close crypto trades. It does not submit orders; live orders still pass through runtime gates.",
        "",
        "## Summary",
        "",
        f"- Total Kraken pairs discovered: {summary.get('total_pairs', 0)}",
        f"- Ticker enriched this run: {summary.get('ticker_enriched_count', 0)} / budget {summary.get('ticker_budget', 0)}",
        f"- Spot trade ready: {summary.get('spot_trade_ready_count', 0)}",
        f"- Margin-capable pairs: {summary.get('margin_pair_count', 0)}",
        f"- Margin trade ready: {summary.get('margin_trade_ready_count', 0)}",
        f"- Cost known: {summary.get('cost_known_count', 0)}",
        f"- Fee tier known: {summary.get('fee_known_count', 0)}",
        f"- Audit status: {audit.get('status', 'unknown')} ({audit.get('passed_count', 0)}/{audit.get('check_count', 0)})",
        "",
        "## Execution Route",
        "",
        "- SPOT BUY: `KrakenClient.place_market_order(symbol, \"buy\", quantity=base_qty)` via `POST /0/private/AddOrder`",
        "- SPOT SELL: `KrakenClient.place_market_order(symbol, \"sell\", quantity=base_qty)` via `POST /0/private/AddOrder`",
        "- LIMIT/POST-ONLY: `KrakenClient.place_limit_order(symbol, side, quantity, price, post_only=True)`",
        "- TAKE PROFIT: `KrakenClient.place_take_profit_order(symbol, close_side, quantity, take_profit_price)`",
        "- MARGIN: `KrakenClient.place_margin_order(symbol, side, quantity, leverage, take_profit=target, stop_loss=stop)`",
        "- REDUCE-ONLY CLOSE: `KrakenClient.close_margin_position(symbol, close_side, volume)`",
        "",
        "## Official Basis",
        "",
        "- Kraken AssetPairs supplies tradable pairs, precision, order minimums, and leverage evidence.",
        "- Kraken AddOrder is the REST order route for spot, margin, limit, stop, and take-profit orders.",
        "- Kraken trading fees depend on pair, 30-day volume, and maker/taker execution.",
        "- Margin trades add opening and rollover fees in addition to normal trade fees.",
        "",
        "## Audit Checks",
        "",
    ]
    for item in audit.get("checks", []) or []:
        marker = "PASS" if item.get("passed") else "ATTENTION"
        lines.append(f"- {marker} {item.get('name')}: {item.get('detail')}")
    lines.extend(
        [
            "",
            "## Top Blockers",
            "",
        ]
    )
    for blocker in summary.get("top_blockers", []) or []:
        lines.append(f"- {blocker.get('name')}: {blocker.get('count')}")
    lines.extend(["", "## Asset Class Counts", ""])
    for name, count in (summary.get("asset_classes", {}) or {}).items():
        lines.append(f"- {name}: {count}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def write_kraken_asset_registry(
    report: dict[str, Any],
    *,
    state_json: Path = DEFAULT_STATE_JSON,
    output_json: Path = DEFAULT_OUTPUT_JSON,
    output_csv: Path = DEFAULT_OUTPUT_CSV,
    output_md: Path = DEFAULT_OUTPUT_MD,
    output_db: Path = DEFAULT_OUTPUT_DB,
    public_json: Path = DEFAULT_PUBLIC_JSON,
) -> dict[str, str]:
    if (
        report.get("data_status") != "live"
        or report.get("truth_status") != "real_derived"
        or report.get("generated_values") is not False
        or report.get("action") is not False
        or report.get("accounting") is not False
        or report.get("learning") is not False
    ):
        return {
            "status": "no_data",
            "reason": str(report.get("no_data_reason") or "incomplete_ticker_receipts"),
        }
    assets = list(report.get("assets", []) or [])
    return {
        "state_json": str(_write_json(state_json, report)),
        "output_json": str(_write_json(output_json, report)),
        "output_csv": str(_write_csv(output_csv, assets)),
        "output_md": str(_write_markdown(output_md, report)),
        "output_db": str(_write_sqlite(output_db, report)),
        "public_json": str(_write_json(public_json, report)),
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build the Kraken tradable asset and cost registry")
    parser.add_argument("--force-refresh", action="store_true", help="Refresh Kraken AssetPairs instead of using cache")
    parser.add_argument(
        "--max-tickers",
        type=int,
        default=int(os.getenv("KRAKEN_ASSET_REGISTRY_MAX_TICKERS", "100") or "100"),
        help="Detailed ticker snapshots to sample this run; use -1 for all, 0 for catalogue only",
    )
    parser.add_argument("--state-json", default=str(DEFAULT_STATE_JSON))
    parser.add_argument("--output-json", default=str(DEFAULT_OUTPUT_JSON))
    parser.add_argument("--output-csv", default=str(DEFAULT_OUTPUT_CSV))
    parser.add_argument("--output-md", default=str(DEFAULT_OUTPUT_MD))
    parser.add_argument("--output-db", default=str(DEFAULT_OUTPUT_DB))
    parser.add_argument("--public-json", default=str(DEFAULT_PUBLIC_JSON))
    args = parser.parse_args(argv)

    report = build_kraken_asset_registry(force_refresh=args.force_refresh, max_tickers=args.max_tickers)
    written = write_kraken_asset_registry(
        report,
        state_json=Path(args.state_json),
        output_json=Path(args.output_json),
        output_csv=Path(args.output_csv),
        output_md=Path(args.output_md),
        output_db=Path(args.output_db),
        public_json=Path(args.public_json),
    )
    summary = report.get("summary", {})
    print(
        "Kraken asset registry: "
        f"{summary.get('total_pairs', 0)} pairs, "
        f"{summary.get('ticker_enriched_count', 0)} enriched, "
        f"{summary.get('spot_trade_ready_count', 0)} spot-ready, "
        f"{summary.get('margin_trade_ready_count', 0)} margin-ready"
    )
    print(json.dumps(written, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
