"""Receipt-bound Capital GOLD evidence and walk-forward ghost validation.

This module is deliberately pure.  Callers gather observations from providers,
then pass those already-observed payloads here.  The resulting receipt binds the
target quote, price bars, account/risk state, contextual public sources,
volatility metrics, and strictly out-of-sample ghost outcomes into one causal
object.  It never opens, closes, or authorizes a trade.

The repository uses the term ``quantum probability`` for a family of derived
models.  This contract treats that output as a falsifiable probability model,
not as physical quantum evidence: only walk-forward outcomes can make it
decision-influencing, and all economic/action eligibility flags remain false.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Collection, Mapping, Sequence
from decimal import Decimal
from statistics import fmean, pstdev
from typing import Any
from urllib.parse import urlparse

CAPITAL_SOURCE_SCHEMA = "aureon.capital-market-source.v1"
CAPITAL_EVIDENCE_SCHEMA = "aureon.capital-council-evidence.v1"
CAPITAL_SOURCE_PREFIX = "capital:market-source:"
CAPITAL_EVIDENCE_PREFIX = "capital:council-evidence:"

PHI = (1.0 + math.sqrt(5.0)) / 2.0
PHI_INVERSE = 1.0 / PHI
PHI_INVERSE_SQUARED = 1.0 / (PHI * PHI)

_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED_SOURCE_KINDS = (
    "capital_account",
    "capital_positions",
    "capital_price_history",
    "capital_quote",
    "capital_working_orders",
)
_CONTEXT_SOURCE_KINDS = frozenset(
    {"cftc_cot", "cross_asset_quote", "noaa_kp", "treasury_yield"}
)
_SOURCE_KINDS = frozenset((*_REQUIRED_SOURCE_KINDS, *_CONTEXT_SOURCE_KINDS))
_DECISION_ROLES = {
    "capital_quote": "target_market",
    "capital_price_history": "target_market",
    "capital_account": "risk_state",
    "capital_positions": "risk_state",
    "capital_working_orders": "risk_state",
    "cftc_cot": "context_only",
    "treasury_yield": "context_only",
    "noaa_kp": "context_only",
    "cross_asset_quote": "context_only",
}
_MAX_SOURCE_AGES = {
    "capital_quote": 30.0,
    "capital_price_history": 180.0,
    "capital_account": 120.0,
    "capital_positions": 120.0,
    "capital_working_orders": 120.0,
    "cross_asset_quote": 300.0,
    "noaa_kp": 1_800.0,
    "treasury_yield": 345_600.0,
    "cftc_cot": 691_200.0,
}
_OFFICIAL_CONTEXT_HOSTS = {
    "cftc_cot": frozenset({"cftc.gov", "www.cftc.gov", "publicreporting.cftc.gov"}),
    "treasury_yield": frozenset({"home.treasury.gov"}),
    "noaa_kp": frozenset({"services.swpc.noaa.gov"}),
}
_FALSE_FLAGS = (
    "action_eligible",
    "accounting_eligible",
    "learning_eligible",
    "action_gate_passed",
    "actionable",
    "operational_eligible",
    "provider_eligible",
    "eligible_for_action",
    "eligible_for_accounting",
    "eligible_for_learning",
    "economic_mutation",
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _copy(value: Any) -> Any:
    return json.loads(_canonical(value))


def _sha(value: Any) -> str:
    material = value if isinstance(value, str) else _canonical(value)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _canonical_decimal_text(value: float) -> str:
    text = format(Decimal(str(value)), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if Decimal(text) == 0 else text


def _false_flags() -> dict[str, bool]:
    return dict.fromkeys(_FALSE_FLAGS, False)


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"canonical_{name}_required")
    return value


def _digest(value: Any, name: str) -> str:
    result = _text(value, name)
    if _DIGEST_RE.fullmatch(result) is None:
        raise ValueError(f"{name}_must_be_sha256")
    return result


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"finite_{name}_required")
    result = float(value)
    if not math.isfinite(result) or (positive and result <= 0.0):
        raise ValueError(f"finite_{name}_required")
    return result


def _integer(value: Any, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"valid_{name}_required")
    return value


def _sorted_unique(values: Collection[str], name: str) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{name}_must_be_collection")
    result = [_text(item, name) for item in values]
    if result != sorted(set(result)):
        raise ValueError(f"{name}_must_be_sorted_unique")
    return result


def _exact_mapping(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ValueError(f"exact_{name}_required")
    return dict(value)


def _fresh(source_timestamp: float, received_at: float, *, now: float, max_age_s: float) -> None:
    if received_at < source_timestamp:
        raise ValueError("received_before_source")
    for timestamp in (source_timestamp, received_at):
        age = now - timestamp
        if age < -5.0 or age > max_age_s:
            raise ValueError("fresh_source_required")


def _official_context_uri(kind: str, uri: str) -> None:
    hosts = _OFFICIAL_CONTEXT_HOSTS.get(kind)
    if hosts is None:
        return
    parsed = urlparse(uri)
    if parsed.scheme != "https" or parsed.hostname not in hosts:
        raise ValueError(f"official_{kind}_source_required")


def _source_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in payload if key != "receipt_id"}


def build_capital_market_source_receipt(
    *,
    source_kind: str,
    source_id: str,
    source_uri: str,
    source_timestamp: float,
    received_at: float,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one observed provider/public-source payload without granting authority."""

    kind = _text(source_kind, "source_kind")
    if kind not in _SOURCE_KINDS:
        raise ValueError("recognized_capital_evidence_source_kind_required")
    source = _text(source_id, "source_id")
    uri = _text(source_uri, "source_uri")
    _official_context_uri(kind, uri)
    observed = _number(source_timestamp, "source_timestamp")
    received = _number(received_at, "received_at")
    if received < observed:
        raise ValueError("received_before_source")
    if not isinstance(payload, Mapping):
        raise ValueError("source_payload_mapping_required")
    body = _copy(dict(payload))
    causal = {
        "schema": CAPITAL_SOURCE_SCHEMA,
        "receipt_type": "capital_market_source",
        "source_kind": kind,
        "source_id": source,
        "source_uri": uri,
        "decision_role": _DECISION_ROLES[kind],
        "source_timestamp": observed,
        "received_at": received,
        "content_digest": _sha(body),
        "payload": body,
        "truth_status": "real_observed",
        "generated_values": False,
        **_false_flags(),
    }
    return {
        **causal,
        "receipt_id": f"{CAPITAL_SOURCE_PREFIX}{_sha(causal)}",
    }


def _validate_quote(payload: Mapping[str, Any]) -> dict[str, Any]:
    quote = _exact_mapping(
        payload,
        {"ask", "bid", "change_pct", "epic", "high", "low", "market_status", "symbol"},
        "capital_quote_payload",
    )
    bid = _number(quote["bid"], "bid", positive=True)
    ask = _number(quote["ask"], "ask", positive=True)
    if ask < bid:
        raise ValueError("capital_quote_crossed_market")
    high = _number(quote["high"], "high", positive=True)
    low = _number(quote["low"], "low", positive=True)
    if high < low:
        raise ValueError("capital_quote_high_below_low")
    _number(quote["change_pct"], "change_pct")
    if _text(quote["symbol"], "symbol").upper() != "GOLD":
        raise ValueError("capital_gold_symbol_required")
    _text(quote["epic"], "epic")
    _text(quote["market_status"], "market_status")
    return quote


_BAR_KEYS = {
    "close_ask",
    "close_bid",
    "high_ask",
    "high_bid",
    "low_ask",
    "low_bid",
    "open_ask",
    "open_bid",
    "timestamp",
    "volume",
}


def _validate_bars(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    history = _exact_mapping(payload, {"bars", "epic", "resolution"}, "capital_price_history_payload")
    if _text(history["resolution"], "resolution") != "MINUTE":
        raise ValueError("capital_minute_history_required")
    _text(history["epic"], "epic")
    raw_bars = history["bars"]
    if not isinstance(raw_bars, list) or len(raw_bars) < 16:
        raise ValueError("minimum_capital_price_history_required")
    bars: list[dict[str, Any]] = []
    previous = -math.inf
    for raw in raw_bars:
        bar = _exact_mapping(raw, _BAR_KEYS, "capital_price_bar")
        timestamp = _number(bar["timestamp"], "bar_timestamp")
        if timestamp <= previous:
            raise ValueError("strictly_increasing_bar_timestamps_required")
        previous = timestamp
        for prefix in ("open", "high", "low", "close"):
            bid = _number(bar[f"{prefix}_bid"], f"{prefix}_bid", positive=True)
            ask = _number(bar[f"{prefix}_ask"], f"{prefix}_ask", positive=True)
            if ask < bid:
                raise ValueError("capital_bar_crossed_market")
        if bar["high_bid"] < bar["low_bid"] or bar["high_ask"] < bar["low_ask"]:
            raise ValueError("capital_bar_high_below_low")
        _number(bar["volume"], "volume")
        bars.append(bar)
    return bars


def _validate_account(payload: Mapping[str, Any]) -> dict[str, Any]:
    account = _exact_mapping(payload, {"available", "balance", "currency"}, "capital_account_payload")
    _number(account["available"], "available")
    _number(account["balance"], "balance")
    if _text(account["currency"], "currency").upper() != "GBP":
        raise ValueError("capital_gbp_account_required")
    return account


def _validate_count(payload: Mapping[str, Any], *, key: str, name: str) -> dict[str, Any]:
    result = _exact_mapping(payload, {key}, name)
    _integer(result[key], key)
    return result


def validate_capital_market_source_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float,
) -> dict[str, Any]:
    """Validate one exact source receipt, including its source-specific payload."""

    if not isinstance(receipt, Mapping) or receipt.get("schema") != CAPITAL_SOURCE_SCHEMA:
        raise ValueError("capital_market_source_receipt_required")
    required = {
        "schema",
        "receipt_type",
        "receipt_id",
        "source_kind",
        "source_id",
        "source_uri",
        "decision_role",
        "source_timestamp",
        "received_at",
        "content_digest",
        "payload",
        "truth_status",
        "generated_values",
        *_FALSE_FLAGS,
    }
    if set(receipt) != required or receipt.get("receipt_type") != "capital_market_source":
        raise ValueError("exact_capital_market_source_receipt_required")
    kind = _text(receipt.get("source_kind"), "source_kind")
    if kind not in _SOURCE_KINDS or receipt.get("decision_role") != _DECISION_ROLES[kind]:
        raise ValueError("capital_source_role_mismatch")
    _text(receipt.get("source_id"), "source_id")
    uri = _text(receipt.get("source_uri"), "source_uri")
    _official_context_uri(kind, uri)
    source_timestamp = _number(receipt.get("source_timestamp"), "source_timestamp")
    received_at = _number(receipt.get("received_at"), "received_at")
    current = _number(now, "now")
    _fresh(source_timestamp, received_at, now=current, max_age_s=_MAX_SOURCE_AGES[kind])
    if receipt.get("truth_status") != "real_observed" or receipt.get("generated_values") is not False:
        raise ValueError("real_observed_capital_source_required")
    if any(receipt.get(name) is not False for name in _FALSE_FLAGS):
        raise ValueError("capital_source_must_be_evidence_only")
    payload = receipt.get("payload")
    if not isinstance(payload, Mapping) or receipt.get("content_digest") != _sha(dict(payload)):
        raise ValueError("capital_source_content_digest_mismatch")
    if kind == "capital_quote":
        _validate_quote(payload)
    elif kind == "capital_price_history":
        _validate_bars(payload)
    elif kind == "capital_account":
        _validate_account(payload)
    elif kind == "capital_positions":
        _validate_count(payload, key="open_position_count", name="capital_positions_payload")
    elif kind == "capital_working_orders":
        _validate_count(payload, key="working_order_count", name="capital_working_orders_payload")
    elif not isinstance(payload, Mapping) or not payload:
        raise ValueError("nonempty_context_payload_required")
    _digest(receipt.get("content_digest"), "content_digest")
    expected = f"{CAPITAL_SOURCE_PREFIX}{_sha(_source_causal(receipt))}"
    if receipt.get("receipt_id") != expected:
        raise ValueError("capital_source_receipt_hash_mismatch")
    return copy.deepcopy(dict(receipt))


def _close_mid(bar: Mapping[str, Any]) -> float:
    return (float(bar["close_bid"]) + float(bar["close_ask"])) / 2.0


def _walk_forward_probability(prices: Sequence[float]) -> float:
    if len(prices) < 8:
        return 0.5
    fast = fmean(prices[-3:])
    slow = fmean(prices[-8:])
    returns = [math.log(prices[index] / prices[index - 1]) for index in range(1, len(prices))]
    sigma = max(pstdev(returns[-7:]), 1e-9)
    normalized_trend = ((fast - slow) / slow) / sigma
    phi_blend = (PHI_INVERSE * normalized_trend) + (
        PHI_INVERSE_SQUARED * math.tanh(normalized_trend)
    )
    return min(0.95, max(0.05, 0.5 + 0.45 * math.tanh(phi_blend / PHI)))


def _ghost_validation(bars: Sequence[Mapping[str, Any]], *, horizon: int) -> dict[str, Any]:
    if not 1 <= horizon <= 12:
        raise ValueError("ghost_horizon_must_be_between_1_and_12")
    mids = [_close_mid(bar) for bar in bars]
    outcomes: list[dict[str, Any]] = []
    gross_profit = 0.0
    gross_loss = 0.0
    for index in range(7, len(bars) - horizon):
        probability_buy = _walk_forward_probability(mids[: index + 1])
        if probability_buy >= 0.55:
            side = "BUY"
            confidence = probability_buy
            entry = float(bars[index]["close_ask"])
            exit_price = float(bars[index + horizon]["close_bid"])
            pnl_points = exit_price - entry
        elif probability_buy <= 0.45:
            side = "SELL"
            confidence = 1.0 - probability_buy
            entry = float(bars[index]["close_bid"])
            exit_price = float(bars[index + horizon]["close_ask"])
            pnl_points = entry - exit_price
        else:
            continue
        success = pnl_points > 0.0
        if success:
            gross_profit += pnl_points
        else:
            gross_loss += abs(pnl_points)
        outcomes.append(
            {
                "brier": round((confidence - (1.0 if success else 0.0)) ** 2, 12),
                "entry_index": index,
                "entry_price": round(entry, 10),
                "entry_timestamp": bars[index]["timestamp"],
                "exit_index": index + horizon,
                "exit_price": round(exit_price, 10),
                "exit_timestamp": bars[index + horizon]["timestamp"],
                "horizon_bars": horizon,
                "model_probability": round(confidence, 12),
                "pnl_points_after_spread": round(pnl_points, 10),
                "side": side,
                "success": success,
            }
        )
    sample_count = len(outcomes)
    wins = sum(1 for item in outcomes if item["success"])
    latest_probability_buy = _walk_forward_probability(mids)
    if latest_probability_buy >= 0.55:
        latest_side = "BUY"
        latest_confidence = latest_probability_buy
    elif latest_probability_buy <= 0.45:
        latest_side = "SELL"
        latest_confidence = 1.0 - latest_probability_buy
    else:
        latest_side = "HOLD"
        latest_confidence = max(latest_probability_buy, 1.0 - latest_probability_buy)
    brier = fmean(item["brier"] for item in outcomes) if outcomes else None
    profit_factor = (
        gross_profit / gross_loss
        if gross_loss > 0.0
        else (math.inf if gross_profit > 0.0 else 0.0)
    )
    net_points = gross_profit - gross_loss
    calibrated = bool(
        sample_count >= 12
        and brier is not None
        and brier <= 0.30
        and wins / sample_count >= 0.50
        and profit_factor > 1.0
        and net_points > 0.0
        and latest_side in {"BUY", "SELL"}
    )
    return {
        "model_id": "aureon:phi-hnc-walk-forward-probability:v1",
        "model_class": "derived_probability_not_physical_quantum_evidence",
        "phi": PHI,
        "phi_fast_weight": PHI_INVERSE,
        "phi_slow_weight": PHI_INVERSE_SQUARED,
        "horizon_bars": horizon,
        "sample_count": sample_count,
        "win_count": wins,
        "loss_count": sample_count - wins,
        "hit_rate": None if not outcomes else round(wins / sample_count, 12),
        "brier_score": None if brier is None else round(brier, 12),
        "gross_profit_points": round(gross_profit, 10),
        "gross_loss_points": round(gross_loss, 10),
        "net_points_after_spread": round(net_points, 10),
        "profit_factor": None if not math.isfinite(profit_factor) else round(profit_factor, 12),
        "latest_probability_buy": round(latest_probability_buy, 12),
        "latest_side": latest_side,
        "latest_confidence": round(latest_confidence, 12),
        "calibration_status": "validated" if calibrated else "insufficient_or_unprofitable",
        "outcomes": outcomes,
    }


def _volatility(bars: Sequence[Mapping[str, Any]], quote: Mapping[str, Any]) -> dict[str, Any]:
    mids = [_close_mid(bar) for bar in bars]
    returns = [math.log(mids[index] / mids[index - 1]) for index in range(1, len(mids))]
    ranges = [
        ((float(bar["high_bid"]) + float(bar["high_ask"])) / 2.0)
        - ((float(bar["low_bid"]) + float(bar["low_ask"])) / 2.0)
        for bar in bars
    ]
    latest_mid = (float(quote["bid"]) + float(quote["ask"])) / 2.0
    spread = float(quote["ask"]) - float(quote["bid"])
    return {
        "bar_count": len(bars),
        "latest_mid": round(latest_mid, 10),
        "spread_points": round(spread, 10),
        "spread_pct": round(spread / latest_mid * 100.0, 12),
        "realized_log_return_std_1m": round(pstdev(returns), 12),
        "mean_range_points_1m": round(fmean(ranges), 10),
        "max_range_points_1m": round(max(ranges), 10),
        "window_return_pct": round((mids[-1] / mids[0] - 1.0) * 100.0, 12),
    }


def _evidence_causal(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: payload[key]
        for key in payload
        if key not in {"receipt_id", "derived_at"}
    }


def build_capital_market_evidence_receipt(
    *,
    source_receipts: Sequence[Mapping[str, Any]],
    now: float,
    ghost_horizon_bars: int = 3,
) -> dict[str, Any]:
    """Build one exact Council-readable evidence packet from observed sources."""

    current = _number(now, "now")
    if not isinstance(source_receipts, Sequence) or isinstance(source_receipts, (str, bytes)):
        raise ValueError("capital_source_receipt_sequence_required")
    sources = [validate_capital_market_source_receipt(item, now=current) for item in source_receipts]
    ids = [item["receipt_id"] for item in sources]
    if ids != sorted(set(ids)):
        raise ValueError("source_receipts_must_be_sorted_unique_by_id")
    by_kind: dict[str, list[dict[str, Any]]] = {}
    for item in sources:
        by_kind.setdefault(item["source_kind"], []).append(item)
    if any(len(by_kind.get(kind, [])) != 1 for kind in _REQUIRED_SOURCE_KINDS):
        raise ValueError("exact_five_required_capital_sources_required")
    quote_source = by_kind["capital_quote"][0]
    history_source = by_kind["capital_price_history"][0]
    account_source = by_kind["capital_account"][0]
    positions_source = by_kind["capital_positions"][0]
    orders_source = by_kind["capital_working_orders"][0]
    quote = _validate_quote(quote_source["payload"])
    bars = _validate_bars(history_source["payload"])
    account = _validate_account(account_source["payload"])
    positions = _validate_count(
        positions_source["payload"],
        key="open_position_count",
        name="capital_positions_payload",
    )
    orders = _validate_count(
        orders_source["payload"],
        key="working_order_count",
        name="capital_working_orders_payload",
    )
    if history_source["payload"]["epic"] != quote["epic"]:
        raise ValueError("capital_quote_history_epic_mismatch")
    if bars[-1]["timestamp"] > quote_source["source_timestamp"] + 60.0:
        raise ValueError("capital_history_ahead_of_quote")

    volatility = _volatility(bars, quote)
    ghost = _ghost_validation(bars, horizon=ghost_horizon_bars)
    context_kinds = sorted(kind for kind in by_kind if kind in _CONTEXT_SOURCE_KINDS)
    context_ready = "cftc_cot" in context_kinds and "treasury_yield" in context_kinds
    target_ready = bool(
        quote["market_status"].upper() == "TRADEABLE"
        and account["available"] > 0.0
        and positions["open_position_count"] == 0
        and orders["working_order_count"] == 0
        and volatility["spread_pct"] <= 0.10
    )
    probability_ready = ghost["calibration_status"] == "validated"
    action_influence_allowed = target_ready and context_ready and probability_ready
    blockers: list[str] = []
    if not target_ready:
        blockers.append("capital_target_or_risk_state_not_ready")
    if not context_ready:
        blockers.append("official_cftc_and_treasury_context_required")
    if not probability_ready:
        blockers.append("walk_forward_ghost_probability_not_validated")
    recommended_side = ghost["latest_side"] if action_influence_allowed else "HOLD"
    component_ids = sorted(ids)
    target_source_timestamp = float(quote_source["source_timestamp"])
    target_moment_digest = _sha(
        {
            "component_receipt_ids": component_ids,
            "source_timestamp": target_source_timestamp,
        }
    )
    causal = {
        "schema": CAPITAL_EVIDENCE_SCHEMA,
        "receipt_type": "capital_council_market_evidence",
        "venue": "capital",
        "environment": "live_cfd",
        "symbol": "GOLD",
        "epic": quote["epic"],
        "source_receipts": sources,
        "component_receipt_ids": component_ids,
        "position_receipt_id": positions_source["receipt_id"],
        "target_provider_moment_digest": target_moment_digest,
        "target_provider_source_timestamp": target_source_timestamp,
        "volatility": volatility,
        "quantum_probability_validation": ghost,
        "context_source_kinds": context_kinds,
        "context_ready": context_ready,
        "target_ready": target_ready,
        "action_influence_allowed": action_influence_allowed,
        "recommended_side": recommended_side,
        "blockers": blockers,
        "data_status": "live",
        "truth_status": "real_observed_and_derived",
        "freshness_status": "fresh",
        "generated_values": False,
        **_false_flags(),
    }
    receipt = {
        **causal,
        "receipt_id": f"{CAPITAL_EVIDENCE_PREFIX}{_sha(causal)}",
        "derived_at": current,
    }
    return validate_capital_market_evidence_receipt(receipt, now=current)


def validate_capital_market_evidence_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float,
) -> dict[str, Any]:
    """Recompute the complete evidence receipt and reject any causal drift."""

    if not isinstance(receipt, Mapping) or receipt.get("schema") != CAPITAL_EVIDENCE_SCHEMA:
        raise ValueError("capital_market_evidence_receipt_required")
    required = {
        "schema",
        "receipt_type",
        "receipt_id",
        "venue",
        "environment",
        "symbol",
        "epic",
        "source_receipts",
        "component_receipt_ids",
        "position_receipt_id",
        "target_provider_moment_digest",
        "target_provider_source_timestamp",
        "volatility",
        "quantum_probability_validation",
        "context_source_kinds",
        "context_ready",
        "target_ready",
        "action_influence_allowed",
        "recommended_side",
        "blockers",
        "data_status",
        "truth_status",
        "freshness_status",
        "generated_values",
        "derived_at",
        *_FALSE_FLAGS,
    }
    if set(receipt) != required:
        raise ValueError("exact_capital_market_evidence_schema_required")
    if (
        receipt.get("receipt_type") != "capital_council_market_evidence"
        or receipt.get("venue") != "capital"
        or receipt.get("environment") != "live_cfd"
        or receipt.get("symbol") != "GOLD"
        or receipt.get("data_status") != "live"
        or receipt.get("truth_status") != "real_observed_and_derived"
        or receipt.get("freshness_status") != "fresh"
        or receipt.get("generated_values") is not False
    ):
        raise ValueError("live_capital_gold_evidence_required")
    if any(receipt.get(name) is not False for name in _FALSE_FLAGS):
        raise ValueError("capital_market_evidence_must_remain_ineligible")
    current = _number(now, "now")
    source_receipts = receipt.get("source_receipts")
    if not isinstance(source_receipts, list):
        raise ValueError("capital_source_receipts_required")
    sources = [validate_capital_market_source_receipt(item, now=current) for item in source_receipts]
    ids = [item["receipt_id"] for item in sources]
    if ids != receipt.get("component_receipt_ids") or ids != sorted(set(ids)):
        raise ValueError("capital_component_lineage_mismatch")
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in sources:
        grouped.setdefault(item["source_kind"], []).append(item)
    if any(len(grouped.get(kind, [])) != 1 for kind in _REQUIRED_SOURCE_KINDS):
        raise ValueError("exact_five_required_capital_sources_required")
    by_kind = {kind: values[0] for kind, values in grouped.items()}
    quote = _validate_quote(by_kind["capital_quote"]["payload"])
    bars = _validate_bars(by_kind["capital_price_history"]["payload"])
    account = _validate_account(by_kind["capital_account"]["payload"])
    positions = _validate_count(
        by_kind["capital_positions"]["payload"],
        key="open_position_count",
        name="capital_positions_payload",
    )
    orders = _validate_count(
        by_kind["capital_working_orders"]["payload"],
        key="working_order_count",
        name="capital_working_orders_payload",
    )
    if by_kind["capital_price_history"]["payload"]["epic"] != quote["epic"]:
        raise ValueError("capital_quote_history_epic_mismatch")
    expected_volatility = _volatility(bars, quote)
    horizon = _integer(
        receipt.get("quantum_probability_validation", {}).get("horizon_bars"),
        "ghost_horizon_bars",
        minimum=1,
    )
    expected_ghost = _ghost_validation(bars, horizon=horizon)
    if _canonical(receipt.get("volatility")) != _canonical(expected_volatility):
        raise ValueError("capital_volatility_recomputation_mismatch")
    if _canonical(receipt.get("quantum_probability_validation")) != _canonical(expected_ghost):
        raise ValueError("capital_ghost_probability_recomputation_mismatch")
    context_kinds = sorted(kind for kind in grouped if kind in _CONTEXT_SOURCE_KINDS)
    context_ready = "cftc_cot" in context_kinds and "treasury_yield" in context_kinds
    target_ready = bool(
        quote["market_status"].upper() == "TRADEABLE"
        and account["available"] > 0.0
        and positions["open_position_count"] == 0
        and orders["working_order_count"] == 0
        and expected_volatility["spread_pct"] <= 0.10
    )
    probability_ready = expected_ghost["calibration_status"] == "validated"
    action_influence_allowed = target_ready and context_ready and probability_ready
    blockers: list[str] = []
    if not target_ready:
        blockers.append("capital_target_or_risk_state_not_ready")
    if not context_ready:
        blockers.append("official_cftc_and_treasury_context_required")
    if not probability_ready:
        blockers.append("walk_forward_ghost_probability_not_validated")
    expected_side = expected_ghost["latest_side"] if action_influence_allowed else "HOLD"
    if (
        receipt.get("epic") != quote["epic"]
        or receipt.get("symbol") != quote["symbol"].upper()
        or receipt.get("venue") != "capital"
        or receipt.get("environment") != "live_cfd"
    ):
        raise ValueError("capital_target_identity_recomputation_mismatch")
    if (
        receipt.get("context_source_kinds") != context_kinds
        or receipt.get("context_ready") is not context_ready
        or receipt.get("target_ready") is not target_ready
        or receipt.get("action_influence_allowed") is not action_influence_allowed
        or receipt.get("recommended_side") != expected_side
        or receipt.get("blockers") != blockers
    ):
        raise ValueError("capital_decision_recomputation_mismatch")
    source_timestamp = _number(
        receipt.get("target_provider_source_timestamp"),
        "target_provider_source_timestamp",
    )
    if source_timestamp != by_kind["capital_quote"]["source_timestamp"]:
        raise ValueError("capital_target_timestamp_mismatch")
    expected_moment_digest = _sha(
        {"component_receipt_ids": ids, "source_timestamp": source_timestamp}
    )
    if receipt.get("target_provider_moment_digest") != expected_moment_digest:
        raise ValueError("capital_target_moment_digest_mismatch")
    _digest(receipt.get("target_provider_moment_digest"), "target_provider_moment_digest")
    if receipt.get("position_receipt_id") != by_kind["capital_positions"]["receipt_id"]:
        raise ValueError("capital_position_receipt_mismatch")
    derived_at = _number(receipt.get("derived_at"), "derived_at")
    if (
        type(receipt.get("derived_at")) is not float
        or derived_at < max(item["received_at"] for item in sources)
        or derived_at > current + 5.0
        or current - derived_at > _MAX_SOURCE_AGES["capital_quote"]
    ):
        raise ValueError("fresh_capital_evidence_derivation_required")
    expected_id = f"{CAPITAL_EVIDENCE_PREFIX}{_sha(_evidence_causal(receipt))}"
    if receipt.get("receipt_id") != expected_id:
        raise ValueError("capital_market_evidence_hash_mismatch")
    return copy.deepcopy(dict(receipt))


def capital_market_provider_moment(receipt: Mapping[str, Any], *, now: float) -> dict[str, Any]:
    """Return the exact ProviderMoment material for the bounded Capital route."""

    evidence = validate_capital_market_evidence_receipt(receipt, now=now)
    return {
        "receipt_ids": tuple(sorted({evidence["receipt_id"], *evidence["component_receipt_ids"]})),
        "moment_digest": evidence["target_provider_moment_digest"],
        "source_timestamp": _canonical_decimal_text(
            evidence["target_provider_source_timestamp"]
        ),
        "position_receipt_id": evidence["position_receipt_id"],
    }


def capital_market_decision_summary(receipt: Mapping[str, Any], *, now: float) -> dict[str, Any]:
    """Return bounded Council/Crown context; full receipt stays in trusted storage."""

    evidence = validate_capital_market_evidence_receipt(receipt, now=now)
    probability = evidence["quantum_probability_validation"]
    return {
        "capital_market_evidence_receipt_id": evidence["receipt_id"],
        "target_provider_moment_digest": evidence["target_provider_moment_digest"],
        "target_provider_source_timestamp": evidence["target_provider_source_timestamp"],
        "context_source_kinds": evidence["context_source_kinds"],
        "context_ready": evidence["context_ready"],
        "target_ready": evidence["target_ready"],
        "action_influence_allowed": evidence["action_influence_allowed"],
        "recommended_side": evidence["recommended_side"],
        "blockers": evidence["blockers"],
        "volatility": evidence["volatility"],
        "probability": {
            key: probability[key]
            for key in (
                "model_id",
                "model_class",
                "sample_count",
                "hit_rate",
                "brier_score",
                "net_points_after_spread",
                "profit_factor",
                "latest_probability_buy",
                "latest_side",
                "latest_confidence",
                "calibration_status",
            )
        },
    }


__all__ = [
    "CAPITAL_EVIDENCE_PREFIX",
    "CAPITAL_EVIDENCE_SCHEMA",
    "CAPITAL_SOURCE_PREFIX",
    "CAPITAL_SOURCE_SCHEMA",
    "build_capital_market_evidence_receipt",
    "build_capital_market_source_receipt",
    "capital_market_decision_summary",
    "capital_market_provider_moment",
    "validate_capital_market_evidence_receipt",
    "validate_capital_market_source_receipt",
]
