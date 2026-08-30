#!/usr/bin/env python3
"""Receipt-gated dual-venue order lifecycle.

Importing this module and invoking its CLI are inert. Provider clients, a
clock, and a state path must be injected by an owning composition root. An
order acknowledgement creates only a durable reconciliation latch. It never
creates a position, profit, or learning evidence. Only an exact terminal
provider fill can change economic state, and every provider receipt commits
at most once.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Protocol


TAKE_PROFIT_PCT = Decimal("0.015")
STOP_LOSS_PCT = Decimal("0.008")
MAX_HOLD_MINUTES = Decimal("30")
POSITION_SIZE_PCT = Decimal("0.90")
MAX_AGE_SECONDS = 300.0
FUTURE_SKEW_SECONDS = 5.0
STATE_SCHEMA_VERSION = 1
REAL_PROVIDER_TRUTHS = {"real_observed", "real_provider"}
REAL_ACTION_TRUTHS = REAL_PROVIDER_TRUTHS | {"real_derived", "real_operator"}
INVALID_IDS = {"", "0", "none", "null", "unknown", "n/a", "na"}


class DualVenueAdapter(Protocol):
    """Provider boundary; client construction and credentials stay external."""

    def submit_order(
        self,
        *,
        venue: str,
        symbol: str,
        side: str,
        quantity: str,
        client_order_id: str,
    ) -> Mapping[str, Any]: ...

    def read_order_receipt(
        self,
        *,
        venue: str,
        symbol: str,
        order_reference: str,
        provider_order_id: str | None,
    ) -> Mapping[str, Any]: ...


class EvidenceError(ValueError):
    """Evidence is absent, incomplete, stale, or internally inconsistent."""


class StateError(RuntimeError):
    """Durable lifecycle state is unavailable or invalid."""


def _first(row: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def _identifier(value: Any, field: str) -> str:
    if value is None or isinstance(value, bool):
        raise EvidenceError(f"{field}_required")
    text = str(value).strip()
    if text.lower() in INVALID_IDS:
        raise EvidenceError(f"{field}_required")
    return text


def _optional_identifier(value: Any) -> str | None:
    try:
        return _identifier(value, "identifier")
    except EvidenceError:
        return None


def _venue(value: Any) -> str:
    return _identifier(value, "venue").lower()


def _symbol(value: Any) -> str:
    text = "".join(
        character for character in str(value or "").upper() if character.isalnum()
    )
    if not text:
        raise EvidenceError("symbol_required")
    return text


def _asset(value: Any, field: str) -> str:
    text = "".join(
        character for character in str(value or "").upper() if character.isalnum()
    )
    if not text:
        raise EvidenceError(f"{field}_required")
    return text


def _number(
    value: Any,
    field: str,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Decimal:
    if value is None or isinstance(value, bool):
        raise EvidenceError(f"{field}_required")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise EvidenceError(f"{field}_must_be_finite") from exc
    if not result.is_finite():
        raise EvidenceError(f"{field}_must_be_finite")
    if positive and result <= 0:
        raise EvidenceError(f"{field}_must_be_positive")
    if nonnegative and result < 0:
        raise EvidenceError(f"{field}_must_be_nonnegative")
    return result


def _decimal_text(value: Decimal) -> str:
    rendered = format(value.normalize(), "f")
    return "0" if rendered in {"", "-0"} else rendered


def _timestamp(value: Any, field: str) -> float:
    if value is None or isinstance(value, bool):
        raise EvidenceError(f"{field}_required")
    if isinstance(value, (int, float, Decimal)):
        result = float(value)
    elif isinstance(value, str):
        text = value.strip()
        try:
            result = float(text)
        except ValueError:
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError as exc:
                raise EvidenceError(f"{field}_invalid") from exc
            if parsed.tzinfo is None or parsed.utcoffset() is None:
                raise EvidenceError(f"{field}_timezone_required")
            result = parsed.timestamp()
    else:
        raise EvidenceError(f"{field}_invalid")
    if result > 10_000_000_000:
        result /= 1000.0
    if not math.isfinite(result) or result <= 0:
        raise EvidenceError(f"{field}_invalid")
    return result


def _fresh_time(receipt: Mapping[str, Any], field: str, now: float) -> float:
    provider_time = _timestamp(
        _first(receipt, ("provider_timestamp", "source_timestamp")),
        f"{field}_provider_timestamp",
    )
    received_at = _timestamp(receipt.get("received_at"), f"{field}_received_at")
    if (
        provider_time < now - MAX_AGE_SECONDS
        or provider_time > now + FUTURE_SKEW_SECONDS
        or received_at < now - MAX_AGE_SECONDS
        or received_at > now + FUTURE_SKEW_SECONDS
        or provider_time > received_at + FUTURE_SKEW_SECONDS
    ):
        raise EvidenceError(f"{field}_fresh_provider_evidence_required")
    return provider_time


def _header(
    receipt: Any,
    kind: str,
    *,
    venue: str,
    symbol: str,
    account_id: str,
    now: float,
    truths: set[str] | None = None,
) -> str:
    if not isinstance(receipt, Mapping):
        raise EvidenceError(f"{kind}_receipt_required")
    receipt_id = _identifier(receipt.get("receipt_id"), f"{kind}_receipt_id")
    _identifier(
        receipt.get("provider_receipt_type"),
        f"{kind}_provider_receipt_type",
    )
    if str(receipt.get("data_status") or "").strip().lower() != "live":
        raise EvidenceError(f"{kind}_live_receipt_required")
    accepted_truths = REAL_ACTION_TRUTHS if truths is None else truths
    if str(receipt.get("truth_status") or "").strip().lower() not in accepted_truths:
        raise EvidenceError(f"{kind}_real_truth_required")
    if receipt.get("generated_values") is not False:
        raise EvidenceError(f"{kind}_generated_values_forbidden")
    if receipt.get("eligible_for_action") is not True:
        raise EvidenceError(f"{kind}_action_eligibility_required")
    if _venue(_first(receipt, ("venue", "exchange", "provider"))) != venue:
        raise EvidenceError(f"{kind}_venue_mismatch")
    if _symbol(receipt.get("symbol")) != symbol:
        raise EvidenceError(f"{kind}_symbol_mismatch")
    if _identifier(receipt.get("account_id"), f"{kind}_account_id") != account_id:
        raise EvidenceError(f"{kind}_account_mismatch")
    _fresh_time(receipt, kind, now)
    return receipt_id


def _authorization(
    receipt: Any,
    *,
    now: float,
    allow_expired: bool,
) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise EvidenceError("authorization_receipt_required")
    venue = _venue(_first(receipt, ("venue", "exchange", "provider")))
    symbol = _symbol(receipt.get("symbol"))
    account_id = _identifier(receipt.get("account_id"), "authorization_account_id")
    receipt_id = _header(
        receipt,
        "authorization",
        venue=venue,
        symbol=symbol,
        account_id=account_id,
        now=now,
        truths={"real_operator"},
    )
    if (
        receipt.get("authorized") is not True
        or receipt.get("provider_submission_authorized") is not True
    ):
        raise EvidenceError("explicit_provider_submission_authorization_required")
    expires_at = _timestamp(receipt.get("expires_at"), "authorization_expires_at")
    if not allow_expired and expires_at <= now:
        raise EvidenceError("authorization_expired")
    side = str(receipt.get("side") or "").strip().upper()
    if side not in {"BUY", "SELL"}:
        raise EvidenceError("authorized_side_required")
    return {
        "receipt_id": receipt_id,
        "authorization_id": _identifier(
            receipt.get("authorization_id"), "authorization_id"
        ),
        "cycle_id": _identifier(
            receipt.get("cycle_id"), "authorization_cycle_id"
        ),
        "intent_id": _identifier(
            receipt.get("intent_id"), "authorization_intent_id"
        ),
        "venue": venue,
        "symbol": symbol,
        "account_id": account_id,
        "side": side,
        "quantity": _number(
            receipt.get("quantity"), "authorized_quantity", positive=True
        ),
        "max_notional": _number(
            receipt.get("max_notional"),
            "authorized_max_notional",
            positive=True,
        ),
        "reason_code": str(receipt.get("reason_code") or "").strip().lower(),
    }


def _preflight(
    *,
    authorization_receipt: Any,
    account_receipt: Any,
    position_receipt: Any,
    market_receipt: Any,
    cost_receipt: Any,
    fee_receipt: Any,
    hnc_receipt: Any,
    auris_receipt: Any,
    now: float,
    allow_expired_authorization: bool,
    open_position: Mapping[str, Any] | None,
) -> dict[str, Any]:
    auth = _authorization(
        authorization_receipt,
        now=now,
        allow_expired=allow_expired_authorization,
    )
    common = {
        "venue": auth["venue"],
        "symbol": auth["symbol"],
        "account_id": auth["account_id"],
        "now": now,
    }
    receipt_ids = {"authorization": auth["receipt_id"]}
    receipt_ids["account"] = _header(account_receipt, "account", **common)
    receipt_ids["position"] = _header(position_receipt, "position", **common)
    receipt_ids["market"] = _header(market_receipt, "market", **common)
    receipt_ids["fee"] = _header(fee_receipt, "fee", **common)
    receipt_ids["hnc"] = _header(hnc_receipt, "hnc", **common)
    receipt_ids["auris"] = _header(auris_receipt, "auris", **common)
    receipt_ids["cost"] = _header(cost_receipt, "cost", **common)

    base_asset = _asset(market_receipt.get("base_asset"), "market_base_asset")
    quote_asset = _asset(market_receipt.get("quote_asset"), "market_quote_asset")
    if _asset(
        position_receipt.get("base_asset"), "position_base_asset"
    ) != base_asset:
        raise EvidenceError("position_base_asset_mismatch")
    if _asset(
        position_receipt.get("quote_asset"), "position_quote_asset"
    ) != quote_asset:
        raise EvidenceError("position_quote_asset_mismatch")
    position_quantity = _number(
        _first(position_receipt, ("position_quantity", "quantity")),
        "position_quantity",
        nonnegative=True,
    )
    account_currency = _asset(account_receipt.get("currency"), "account_currency")
    available = _number(
        _first(account_receipt, ("available_balance", "available", "cash")),
        "account_available_balance",
        nonnegative=True,
    )
    bid = _number(
        _first(market_receipt, ("bid_price", "bidPrice", "bid")),
        "market_bid",
        positive=True,
    )
    ask = _number(
        _first(market_receipt, ("ask_price", "askPrice", "ask")),
        "market_ask",
        positive=True,
    )
    if bid > ask:
        raise EvidenceError("market_bid_exceeds_ask")
    fee_rate = _number(
        _first(fee_receipt, ("taker_fee_rate", "fee_rate")),
        "taker_fee_rate",
        nonnegative=True,
    )
    if fee_rate >= 1:
        raise EvidenceError("taker_fee_rate_must_be_less_than_one")
    fee_currency = _asset(fee_receipt.get("fee_currency"), "fee_currency")
    if fee_currency != quote_asset:
        raise EvidenceError("fee_currency_must_match_quote_asset")

    for receipt, kind, signal_field in (
        (hnc_receipt, "hnc", "hnc_signal"),
        (auris_receipt, "auris", "auris_signal"),
    ):
        _identifier(receipt.get("equation_id"), f"{kind}_equation_id")
        _number(receipt.get(signal_field), f"{kind}_signal")
        if (
            receipt.get("equation_inputs_complete") is not True
            or receipt.get("action_gate_passed") is not True
            or str(receipt.get("recommended_side") or "").strip().upper()
            != auth["side"]
        ):
            raise EvidenceError(f"{kind}_equation_gate_incomplete")
        if (
            _identifier(
                receipt.get("market_receipt_id"),
                f"{kind}_market_receipt_id",
            )
            != receipt_ids["market"]
        ):
            raise EvidenceError(f"{kind}_market_dependency_mismatch")
    if (
        _identifier(
            auris_receipt.get("hnc_receipt_id"),
            "auris_hnc_receipt_id",
        )
        != receipt_ids["hnc"]
    ):
        raise EvidenceError("auris_hnc_dependency_mismatch")

    execution_price = ask if auth["side"] == "BUY" else bid
    notional = auth["quantity"] * execution_price
    estimated_fee = notional * fee_rate
    if notional > auth["max_notional"]:
        raise EvidenceError("authorized_max_notional_exceeded")
    if _asset(cost_receipt.get("currency"), "cost_currency") != quote_asset:
        raise EvidenceError("cost_currency_mismatch")
    if (
        _number(cost_receipt.get("quantity"), "cost_quantity", positive=True)
        != auth["quantity"]
    ):
        raise EvidenceError("cost_quantity_mismatch")
    if (
        _number(
            cost_receipt.get("execution_price"),
            "cost_execution_price",
            positive=True,
        )
        != execution_price
    ):
        raise EvidenceError("cost_execution_price_mismatch")
    if (
        _number(cost_receipt.get("notional"), "cost_notional", positive=True)
        != notional
    ):
        raise EvidenceError("cost_notional_mismatch")
    if (
        _number(
            cost_receipt.get("estimated_fee"),
            "cost_estimated_fee",
            nonnegative=True,
        )
        != estimated_fee
    ):
        raise EvidenceError("cost_estimated_fee_mismatch")
    dependencies = cost_receipt.get("dependency_receipt_ids")
    required_dependencies = {
        receipt_ids["authorization"],
        receipt_ids["account"],
        receipt_ids["position"],
        receipt_ids["market"],
        receipt_ids["fee"],
        receipt_ids["hnc"],
        receipt_ids["auris"],
    }
    if (
        not isinstance(dependencies, list)
        or set(map(str, dependencies)) != required_dependencies
    ):
        raise EvidenceError("cost_dependency_receipts_incomplete")

    trigger: dict[str, Any] | None = None
    if auth["side"] == "BUY":
        if open_position is not None or position_quantity != 0:
            raise EvidenceError("buy_requires_observed_flat_position")
        if account_currency != quote_asset:
            raise EvidenceError("buy_requires_quote_currency_account")
        capacity = available * POSITION_SIZE_PCT
        if notional + estimated_fee > capacity:
            raise EvidenceError("fee_complete_position_capacity_exceeded")
    else:
        if not isinstance(open_position, Mapping):
            raise EvidenceError("terminal_entry_fill_required_before_sell")
        if account_currency != base_asset:
            raise EvidenceError("sell_requires_base_currency_account")
        if available < auth["quantity"] or position_quantity != auth["quantity"]:
            raise EvidenceError(
                "fresh_position_and_balance_must_match_sell_quantity"
            )
        entry_quantity = _number(
            open_position.get("filled_qty"),
            "entry_filled_quantity",
            positive=True,
        )
        entry_price = _number(
            open_position.get("filled_avg_price"),
            "entry_filled_price",
            positive=True,
        )
        if entry_quantity != auth["quantity"]:
            raise EvidenceError(
                "sell_quantity_must_match_terminal_entry_fill"
            )
        entry_receipt_id = _identifier(
            open_position.get("receipt_id"), "entry_fill_receipt_id"
        )
        if (
            _identifier(
                position_receipt.get("entry_receipt_id"),
                "position_entry_receipt_id",
            )
            != entry_receipt_id
        ):
            raise EvidenceError("position_entry_receipt_mismatch")
        opened_at = _timestamp(
            position_receipt.get("provider_open_timestamp"),
            "position_provider_open_timestamp",
        )
        entry_time = _timestamp(
            open_position.get("provider_timestamp"),
            "entry_provider_timestamp",
        )
        if opened_at != entry_time:
            raise EvidenceError("position_open_time_must_match_entry_fill")
        gross_pnl_pct = (bid - entry_price) / entry_price
        round_trip_fee_pct = fee_rate * Decimal("2")
        net_pnl_pct = gross_pnl_pct - round_trip_fee_pct
        hold_minutes = Decimal(str((now - opened_at) / 60.0))
        if hold_minutes < 0:
            raise EvidenceError("position_open_time_in_future")
        if net_pnl_pct >= TAKE_PROFIT_PCT:
            reason_code = "take_profit"
        elif gross_pnl_pct <= -STOP_LOSS_PCT:
            reason_code = "stop_loss"
        elif hold_minutes >= MAX_HOLD_MINUTES:
            reason_code = "max_hold"
        else:
            reason_code = "hold"
        trigger = {
            "reason_code": reason_code,
            "gross_pnl_pct": _decimal_text(gross_pnl_pct),
            "round_trip_fee_pct": _decimal_text(round_trip_fee_pct),
            "net_pnl_pct": _decimal_text(net_pnl_pct),
            "hold_minutes": _decimal_text(hold_minutes),
        }
        if reason_code == "hold":
            raise EvidenceError("observed_exit_threshold_not_reached")
        if auth["reason_code"] != reason_code:
            raise EvidenceError("authorized_exit_reason_mismatch")

    return {
        **auth,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "bid": bid,
        "ask": ask,
        "fee_rate": fee_rate,
        "notional": notional,
        "estimated_fee": estimated_fee,
        "evidence_receipt_ids": receipt_ids,
        "trigger": trigger,
    }


def _terminal_fill(
    receipt: Any,
    *,
    preflight: Mapping[str, Any],
    expected_order_id: str | None,
    now: float,
) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise EvidenceError("provider_order_receipt_required")
    if receipt.get("dry_run") is True or receipt.get("dryRun") is True:
        raise EvidenceError("preview_is_not_provider_fill")
    status = str(
        _first(receipt, ("provider_status", "status")) or ""
    ).strip().upper()
    if status != "FILLED":
        raise EvidenceError("terminal_filled_provider_status_required")
    if (
        str(receipt.get("data_status") or "").strip().lower() != "live"
        or str(receipt.get("truth_status") or "").strip().lower()
        not in REAL_PROVIDER_TRUTHS
        or receipt.get("generated_values") is not False
        or receipt.get("fill_receipt_complete") is not True
        or receipt.get("eligible_for_action") is not False
        or receipt.get("eligible_for_accounting") is not True
        or receipt.get("eligible_for_learning") is not True
        or receipt.get("reconciliation_required") is not False
    ):
        raise EvidenceError("complete_terminal_provider_fill_required")
    if (
        _venue(_first(receipt, ("venue", "exchange", "provider")))
        != preflight["venue"]
    ):
        raise EvidenceError("terminal_venue_mismatch")
    if _symbol(receipt.get("symbol")) != preflight["symbol"]:
        raise EvidenceError("terminal_symbol_mismatch")
    if (
        _identifier(receipt.get("account_id"), "terminal_account_id")
        != preflight["account_id"]
    ):
        raise EvidenceError("terminal_account_mismatch")
    if str(receipt.get("side") or "").strip().upper() != preflight["side"]:
        raise EvidenceError("terminal_side_mismatch")
    receipt_id = _identifier(receipt.get("receipt_id"), "terminal_receipt_id")
    receipt_type = _identifier(
        receipt.get("provider_receipt_type"),
        "terminal_provider_receipt_type",
    )
    order_id = _identifier(
        _first(receipt, ("provider_order_id", "order_id", "orderId")),
        "terminal_provider_order_id",
    )
    if expected_order_id is not None and order_id != expected_order_id:
        raise EvidenceError("terminal_provider_order_id_mismatch")
    quantity = _number(
        _first(receipt, ("filled_qty", "executedQty", "filledQty")),
        "terminal_filled_quantity",
        positive=True,
    )
    notional = _number(
        _first(
            receipt,
            ("filled_notional", "cummulativeQuoteQty", "cumulativeQuoteQty"),
        ),
        "terminal_filled_notional",
        positive=True,
    )
    price = _number(
        _first(receipt, ("filled_avg_price", "avg_fill_price", "avgPrice")),
        "terminal_filled_price",
        positive=True,
    )
    fee = _number(
        _first(receipt, ("fee", "fees", "fee_amount")),
        "terminal_fee",
        nonnegative=True,
    )
    fee_currency = _asset(
        _first(receipt, ("fee_currency", "fee_asset")),
        "terminal_fee_currency",
    )
    if quantity != preflight["quantity"]:
        raise EvidenceError("terminal_quantity_mismatch")
    if price * quantity != notional:
        raise EvidenceError("terminal_notional_price_quantity_mismatch")
    if fee_currency != preflight["quote_asset"]:
        raise EvidenceError("terminal_fee_currency_mismatch")
    if preflight["side"] == "BUY" and notional > preflight["max_notional"]:
        raise EvidenceError("terminal_buy_notional_exceeds_authorization")

    rows = receipt.get("fills")
    if not isinstance(rows, list) or not rows:
        raise EvidenceError("provider_fill_rows_required")
    trade_ids: list[str] = []
    sum_quantity = Decimal("0")
    sum_notional = Decimal("0")
    sum_fee = Decimal("0")
    for row in rows:
        if not isinstance(row, Mapping):
            raise EvidenceError("provider_fill_row_invalid")
        trade_id = _identifier(
            _first(row, ("trade_id", "tradeId", "id")),
            "provider_trade_id",
        )
        if trade_id in trade_ids:
            raise EvidenceError("unique_provider_trade_ids_required")
        row_quantity = _number(
            _first(row, ("quantity", "qty")),
            "provider_trade_quantity",
            positive=True,
        )
        row_price = _number(
            row.get("price"), "provider_trade_price", positive=True
        )
        row_fee = _number(
            _first(row, ("fee", "commission", "fee_amount")),
            "provider_trade_fee",
            nonnegative=True,
        )
        row_currency = _asset(
            _first(
                row,
                ("fee_currency", "commissionAsset", "fee_asset"),
            ),
            "provider_trade_fee_currency",
        )
        row_time = _timestamp(
            _first(
                row,
                ("provider_timestamp", "source_timestamp", "time"),
            ),
            "provider_trade_timestamp",
        )
        if (
            row_currency != fee_currency
            or row_time < now - MAX_AGE_SECONDS
            or row_time > now + FUTURE_SKEW_SECONDS
        ):
            raise EvidenceError("fresh_same_currency_provider_trade_required")
        trade_ids.append(trade_id)
        sum_quantity += row_quantity
        sum_notional += row_quantity * row_price
        sum_fee += row_fee
    if (
        sum_quantity != quantity
        or sum_notional != notional
        or sum_fee != fee
    ):
        raise EvidenceError("exact_provider_fill_totals_required")
    provider_time = _fresh_time(receipt, "terminal", now)
    return {
        "receipt_id": receipt_id,
        "provider_receipt_type": receipt_type,
        "provider_order_id": order_id,
        "trade_ids": trade_ids,
        "venue": preflight["venue"],
        "symbol": preflight["symbol"],
        "account_id": preflight["account_id"],
        "side": preflight["side"],
        "filled_qty": _decimal_text(quantity),
        "filled_notional": _decimal_text(notional),
        "filled_avg_price": _decimal_text(price),
        "fee": _decimal_text(fee),
        "fee_currency": fee_currency,
        "provider_timestamp": provider_time,
        "truth_status": "real_provider",
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
    }


def _acknowledgement(
    receipt: Any,
    *,
    preflight: Mapping[str, Any],
    now: float,
) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise EvidenceError("provider_acknowledgement_required")
    order_id = _identifier(
        _first(
            receipt,
            ("provider_order_id", "order_id", "orderId", "id"),
        ),
        "provider_order_id",
    )
    receipt_id = _identifier(
        receipt.get("receipt_id"), "acknowledgement_receipt_id"
    )
    receipt_type = _identifier(
        receipt.get("provider_receipt_type"),
        "acknowledgement_provider_receipt_type",
    )
    status = str(
        _first(receipt, ("provider_status", "status")) or ""
    ).strip().upper()
    if not status:
        raise EvidenceError("acknowledgement_provider_status_required")
    if (
        str(receipt.get("data_status") or "").strip().lower() != "live"
        or str(receipt.get("truth_status") or "").strip().lower()
        not in REAL_PROVIDER_TRUTHS
        or receipt.get("generated_values") is not False
        or receipt.get("eligible_for_action") is not False
        or receipt.get("eligible_for_accounting") is not False
        or receipt.get("eligible_for_learning") is not False
        or receipt.get("reconciliation_required") is not True
        or _venue(_first(receipt, ("venue", "exchange", "provider")))
        != preflight["venue"]
        or _symbol(receipt.get("symbol")) != preflight["symbol"]
        or _identifier(
            receipt.get("account_id"), "acknowledgement_account_id"
        )
        != preflight["account_id"]
        or str(receipt.get("side") or "").strip().upper()
        != preflight["side"]
    ):
        raise EvidenceError(
            "complete_same_route_provider_acknowledgement_required"
        )
    provider_time = _fresh_time(receipt, "acknowledgement", now)
    return {
        "receipt_id": receipt_id,
        "provider_receipt_type": receipt_type,
        "provider_order_id": order_id,
        "provider_status": status,
        "provider_timestamp": provider_time,
    }


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": STATE_SCHEMA_VERSION,
        "pending_intents": {},
        "open_positions": {},
        "completed_intents": {},
        "committed_receipt_ids": [],
        "round_trips": {},
    }


def _validate_state(state: Any) -> dict[str, Any]:
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != STATE_SCHEMA_VERSION
    ):
        raise StateError("state_schema_invalid")
    for field in (
        "pending_intents",
        "open_positions",
        "completed_intents",
        "round_trips",
    ):
        if not isinstance(state.get(field), dict):
            raise StateError(f"state_{field}_invalid")
    receipt_ids = state.get("committed_receipt_ids")
    if (
        not isinstance(receipt_ids, list)
        or any(_optional_identifier(value) is None for value in receipt_ids)
        or len(receipt_ids) != len(set(receipt_ids))
    ):
        raise StateError("state_committed_receipt_ids_invalid")
    for intent_id, pending in state["pending_intents"].items():
        if (
            _optional_identifier(intent_id) is None
            or not isinstance(pending, dict)
        ):
            raise StateError("state_pending_intent_invalid")
        for field in (
            "intent_id",
            "authorization_receipt_id",
            "cycle_id",
            "venue",
            "symbol",
            "account_id",
            "side",
            "quantity",
            "quote_asset",
            "max_notional",
            "client_order_id",
            "phase",
        ):
            if _optional_identifier(pending.get(field)) is None:
                raise StateError(f"state_pending_{field}_invalid")
        _number(
            pending.get("quantity"),
            "stored_pending_quantity",
            positive=True,
        )
        _number(
            pending.get("max_notional"),
            "stored_pending_max_notional",
            positive=True,
        )
        if pending["phase"] not in {"reserved", "acknowledged"}:
            raise StateError("state_pending_phase_invalid")
        if pending["phase"] == "acknowledged":
            for field in (
                "provider_order_id",
                "acknowledgement_receipt_id",
                "provider_timestamp",
            ):
                if _optional_identifier(pending.get(field)) is None:
                    raise StateError(f"state_pending_{field}_invalid")
            _timestamp(
                pending.get("provider_timestamp"),
                "stored_pending_provider_timestamp",
            )
        evidence_ids = pending.get("evidence_receipt_ids")
        if (
            not isinstance(evidence_ids, dict)
            or set(evidence_ids)
            != {
                "authorization",
                "account",
                "position",
                "market",
                "fee",
                "hnc",
                "auris",
                "cost",
            }
            or any(
                _optional_identifier(value) is None
                for value in evidence_ids.values()
            )
        ):
            raise StateError("state_pending_evidence_receipts_invalid")
    for key, fill in state["open_positions"].items():
        if _optional_identifier(key) is None or not isinstance(fill, dict):
            raise StateError("state_open_position_invalid")
        for field in (
            "receipt_id",
            "provider_order_id",
            "venue",
            "symbol",
            "account_id",
            "filled_qty",
            "filled_notional",
            "filled_avg_price",
            "fee",
            "fee_currency",
            "provider_timestamp",
        ):
            if field not in fill:
                raise StateError(
                    f"state_open_position_{field}_missing"
                )
        stored_quantity = _number(
            fill["filled_qty"],
            "stored_filled_quantity",
            positive=True,
        )
        stored_notional = _number(
            fill["filled_notional"],
            "stored_filled_notional",
            positive=True,
        )
        stored_price = _number(
            fill["filled_avg_price"],
            "stored_filled_price",
            positive=True,
        )
        if stored_price * stored_quantity != stored_notional:
            raise StateError("stored_fill_totals_invalid")
        _number(fill["fee"], "stored_fee", nonnegative=True)
        _timestamp(
            fill["provider_timestamp"], "stored_provider_timestamp"
        )
        trade_ids = fill.get("trade_ids")
        if (
            not isinstance(trade_ids, list)
            or not trade_ids
            or any(_optional_identifier(value) is None for value in trade_ids)
            or len(trade_ids) != len(set(trade_ids))
        ):
            raise StateError("stored_trade_ids_invalid")
    for intent_id, receipt_id in state["completed_intents"].items():
        if (
            _optional_identifier(intent_id) is None
            or _optional_identifier(receipt_id) is None
            or receipt_id not in receipt_ids
        ):
            raise StateError("state_completed_intent_invalid")
    for cycle_id, accounting in state["round_trips"].items():
        if (
            _optional_identifier(cycle_id) is None
            or not isinstance(accounting, dict)
        ):
            raise StateError("state_round_trip_invalid")
        for field in (
            "entry_receipt_id",
            "exit_receipt_id",
            "gross_pnl",
            "fees",
            "net_pnl",
            "currency",
        ):
            if field not in accounting:
                raise StateError(f"state_round_trip_{field}_missing")
        gross = _number(accounting["gross_pnl"], "stored_gross_pnl")
        fees = _number(
            accounting["fees"], "stored_fees", nonnegative=True
        )
        net = _number(accounting["net_pnl"], "stored_net_pnl")
        if gross - fees != net:
            raise StateError("stored_round_trip_totals_invalid")
        if (
            accounting["entry_receipt_id"] not in receipt_ids
            or accounting["exit_receipt_id"] not in receipt_ids
        ):
            raise StateError("stored_round_trip_receipts_invalid")
    return state


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return _empty_state()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError("state_read_failed") from exc
    return _validate_state(raw)


def _write_state(path: Path, state: Mapping[str, Any]) -> None:
    validated = _validate_state(dict(state))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open(
            "w", encoding="utf-8", newline="\n"
        ) as handle:
            json.dump(validated, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


@contextmanager
def _state_lock(path: Path) -> Iterator[None]:
    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
    except FileExistsError as exc:
        raise StateError("state_lock_unavailable") from exc
    try:
        os.write(descriptor, str(os.getpid()).encode("ascii"))
        os.close(descriptor)
        yield
    finally:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _route_key(preflight: Mapping[str, Any]) -> str:
    return "|".join(
        (
            str(preflight["venue"]),
            str(preflight["account_id"]),
            str(preflight["symbol"]),
        )
    )


def _result(status: str, reason: str, **extra: Any) -> dict[str, Any]:
    economic_mutation = status == "filled"
    return {
        "status": status,
        "reason": reason,
        "data_status": "live" if economic_mutation else status,
        "truth_status": (
            "real_provider" if economic_mutation else "no_data"
        ),
        "generated_values": False,
        "economic_mutation": economic_mutation,
        "eligible_for_action": False,
        "eligible_for_accounting": economic_mutation,
        "eligible_for_learning": economic_mutation,
        **extra,
    }


def _pending_preflight(pending: Mapping[str, Any]) -> dict[str, Any]:
    """Rebuild only the immutable route contract needed for reconciliation."""

    return {
        "receipt_id": pending["authorization_receipt_id"],
        "cycle_id": pending["cycle_id"],
        "intent_id": pending["intent_id"],
        "venue": pending["venue"],
        "symbol": pending["symbol"],
        "account_id": pending["account_id"],
        "side": pending["side"],
        "quantity": _number(
            pending["quantity"], "pending_quantity", positive=True
        ),
        "max_notional": _number(
            pending["max_notional"],
            "pending_max_notional",
            positive=True,
        ),
        "quote_asset": pending["quote_asset"],
        "evidence_receipt_ids": pending["evidence_receipt_ids"],
        "trigger": pending.get("trigger"),
    }


class OrcaDualHunter:
    """Dual-venue lifecycle with injected providers and exact fill commits."""

    def __init__(
        self,
        *,
        adapters: Mapping[str, DualVenueAdapter] | None = None,
        clock: Callable[[], float] | None = None,
        state_path: str | Path | None = None,
        dry_run: bool = True,
    ) -> None:
        self.adapters = {
            _venue(name): adapter for name, adapter in (adapters or {}).items()
        }
        self.clock = clock
        self.state_path = (
            Path(state_path) if state_path is not None else None
        )
        self.dry_run = bool(dry_run)

    def process_action(
        self,
        *,
        authorization_receipt: Any,
        account_receipt: Any,
        position_receipt: Any,
        market_receipt: Any,
        cost_receipt: Any,
        fee_receipt: Any,
        hnc_receipt: Any,
        auris_receipt: Any,
    ) -> dict[str, Any]:
        """Submit or read back one intent; never perform both in one invocation."""

        if self.clock is None:
            return _result("no_data", "clock_required")
        if self.state_path is None:
            return _result("no_data", "state_path_required")
        try:
            now = float(self.clock())
        except (TypeError, ValueError, OverflowError):
            return _result("no_data", "finite_clock_required")
        if not math.isfinite(now) or now <= 0:
            return _result("no_data", "finite_clock_required")
        raw_intent_id = (
            authorization_receipt.get("intent_id")
            if isinstance(authorization_receipt, Mapping)
            else None
        )
        intent_id = _optional_identifier(raw_intent_id)
        try:
            with _state_lock(self.state_path):
                state = _load_state(self.state_path)
                if (
                    intent_id is not None
                    and intent_id in state["completed_intents"]
                ):
                    return _result(
                        "already_committed",
                        "intent_already_committed",
                        receipt_id=state["completed_intents"][intent_id],
                    )
                pending = (
                    state["pending_intents"].get(intent_id)
                    if intent_id is not None
                    else None
                )
                if isinstance(pending, Mapping):
                    adapter = self.adapters.get(str(pending["venue"]))
                    if adapter is None:
                        return _result(
                            "no_data",
                            "injected_venue_adapter_required",
                        )
                    return self._reconcile(
                        adapter=adapter,
                        state=state,
                        pending=pending,
                        now=now,
                    )

                auth_probe = _authorization(
                    authorization_receipt,
                    now=now,
                    allow_expired=False,
                )
                route_key = _route_key(auth_probe)
                open_position = state["open_positions"].get(route_key)
                preflight = _preflight(
                    authorization_receipt=authorization_receipt,
                    account_receipt=account_receipt,
                    position_receipt=position_receipt,
                    market_receipt=market_receipt,
                    cost_receipt=cost_receipt,
                    fee_receipt=fee_receipt,
                    hnc_receipt=hnc_receipt,
                    auris_receipt=auris_receipt,
                    now=now,
                    allow_expired_authorization=False,
                    open_position=open_position,
                )
                adapter = self.adapters.get(preflight["venue"])
                if adapter is None:
                    return _result(
                        "no_data", "injected_venue_adapter_required"
                    )
                if self.dry_run:
                    return _result("dry_run", "submission_disabled")
                client_order_id = hashlib.sha256(
                    (
                        preflight["authorization_id"]
                        + "|"
                        + preflight["cycle_id"]
                        + "|"
                        + preflight["intent_id"]
                    ).encode("utf-8")
                ).hexdigest()[:32]
                latch = {
                    "intent_id": preflight["intent_id"],
                    "authorization_receipt_id": preflight["receipt_id"],
                    "cycle_id": preflight["cycle_id"],
                    "venue": preflight["venue"],
                    "symbol": preflight["symbol"],
                    "account_id": preflight["account_id"],
                    "side": preflight["side"],
                    "quantity": _decimal_text(preflight["quantity"]),
                    "max_notional": _decimal_text(
                        preflight["max_notional"]
                    ),
                    "quote_asset": preflight["quote_asset"],
                    "client_order_id": client_order_id,
                    "phase": "reserved",
                    "evidence_receipt_ids": preflight[
                        "evidence_receipt_ids"
                    ],
                    "trigger": preflight["trigger"],
                }
                state["pending_intents"][preflight["intent_id"]] = latch
                _write_state(self.state_path, state)
                try:
                    response = adapter.submit_order(
                        venue=preflight["venue"],
                        symbol=preflight["symbol"],
                        side=preflight["side"],
                        quantity=_decimal_text(preflight["quantity"]),
                        client_order_id=client_order_id,
                    )
                except Exception:
                    return _result(
                        "pending_reconciliation",
                        "submission_outcome_unknown",
                        order_reference=client_order_id,
                    )
                try:
                    fill = _terminal_fill(
                        response,
                        preflight=preflight,
                        expected_order_id=None,
                        now=now,
                    )
                except EvidenceError:
                    try:
                        acknowledgement = _acknowledgement(
                            response,
                            preflight=preflight,
                            now=now,
                        )
                    except EvidenceError:
                        return _result(
                            "pending_reconciliation",
                            "provider_terminal_fill_required",
                            order_reference=client_order_id,
                        )
                    latch.update(
                        {
                            "phase": "acknowledged",
                            "provider_order_id": acknowledgement[
                                "provider_order_id"
                            ],
                            "acknowledgement_receipt_id": acknowledgement[
                                "receipt_id"
                            ],
                            "provider_status": acknowledgement[
                                "provider_status"
                            ],
                            "provider_timestamp": acknowledgement[
                                "provider_timestamp"
                            ],
                        }
                    )
                    state["pending_intents"][
                        preflight["intent_id"]
                    ] = latch
                    _write_state(self.state_path, state)
                    return _result(
                        "pending_reconciliation",
                        "provider_terminal_fill_required",
                        provider_order_id=acknowledgement[
                            "provider_order_id"
                        ],
                    )
                return self._commit_fill(state, preflight, fill)
        except (EvidenceError, StateError, OSError, AttributeError) as exc:
            return _result("no_data", str(exc))

    def _reconcile(
        self,
        *,
        adapter: DualVenueAdapter,
        state: dict[str, Any],
        pending: Mapping[str, Any],
        now: float,
    ) -> dict[str, Any]:
        preflight = _pending_preflight(pending)
        provider_order_id = _optional_identifier(
            pending.get("provider_order_id")
        )
        try:
            response = adapter.read_order_receipt(
                venue=preflight["venue"],
                symbol=preflight["symbol"],
                order_reference=str(pending["client_order_id"]),
                provider_order_id=provider_order_id,
            )
        except Exception:
            return _result(
                "pending_reconciliation",
                "provider_readback_unavailable",
                order_reference=str(pending["client_order_id"]),
            )
        try:
            fill = _terminal_fill(
                response,
                preflight=preflight,
                expected_order_id=provider_order_id,
                now=now,
            )
        except EvidenceError as terminal_error:
            try:
                acknowledgement = _acknowledgement(
                    response,
                    preflight=preflight,
                    now=now,
                )
            except EvidenceError:
                return _result(
                    "pending_reconciliation",
                    str(terminal_error),
                    order_reference=str(pending["client_order_id"]),
                )
            if (
                provider_order_id is not None
                and acknowledgement["provider_order_id"]
                != provider_order_id
            ):
                return _result(
                    "pending_reconciliation",
                    "provider_order_id_mismatch",
                    order_reference=str(pending["client_order_id"]),
                )
            if pending["phase"] == "reserved":
                updated = dict(pending)
                updated.update(
                    {
                        "phase": "acknowledged",
                        "provider_order_id": acknowledgement[
                            "provider_order_id"
                        ],
                        "acknowledgement_receipt_id": acknowledgement[
                            "receipt_id"
                        ],
                        "provider_status": acknowledgement[
                            "provider_status"
                        ],
                        "provider_timestamp": acknowledgement[
                            "provider_timestamp"
                        ],
                    }
                )
                state["pending_intents"][
                    preflight["intent_id"]
                ] = updated
                _write_state(self.state_path, state)
            return _result(
                "pending_reconciliation",
                str(terminal_error),
                provider_order_id=acknowledgement["provider_order_id"],
            )
        return self._commit_fill(state, preflight, fill)

    def _commit_fill(
        self,
        state: dict[str, Any],
        preflight: Mapping[str, Any],
        fill: Mapping[str, Any],
    ) -> dict[str, Any]:
        receipt_id = str(fill["receipt_id"])
        intent_id = str(preflight["intent_id"])
        if receipt_id in state["committed_receipt_ids"]:
            raise StateError("provider_fill_receipt_already_committed")
        route_key = _route_key(preflight)
        accounting: dict[str, Any] | None = None
        if preflight["side"] == "BUY":
            if route_key in state["open_positions"]:
                raise StateError("open_position_already_exists")
            state["open_positions"][route_key] = dict(fill)
            reason = "terminal_entry_fill_committed"
        else:
            entry = state["open_positions"].get(route_key)
            if not isinstance(entry, Mapping):
                raise StateError("terminal_entry_fill_missing")
            if (
                _asset(entry.get("fee_currency"), "entry_fee_currency")
                != fill["fee_currency"]
            ):
                raise StateError("round_trip_fee_currency_mismatch")
            entry_notional = _number(
                entry.get("filled_notional"),
                "entry_notional",
                positive=True,
            )
            entry_fee = _number(
                entry.get("fee"), "entry_fee", nonnegative=True
            )
            exit_notional = _number(
                fill.get("filled_notional"),
                "exit_notional",
                positive=True,
            )
            exit_fee = _number(
                fill.get("fee"), "exit_fee", nonnegative=True
            )
            gross_pnl = exit_notional - entry_notional
            total_fees = entry_fee + exit_fee
            net_pnl = gross_pnl - total_fees
            accounting = {
                "entry_receipt_id": entry["receipt_id"],
                "exit_receipt_id": receipt_id,
                "gross_pnl": _decimal_text(gross_pnl),
                "fees": _decimal_text(total_fees),
                "net_pnl": _decimal_text(net_pnl),
                "currency": fill["fee_currency"],
                "truth_status": "real_derived",
                "generated_values": False,
                "eligible_for_accounting": True,
                "eligible_for_learning": True,
            }
            if str(preflight["cycle_id"]) in state["round_trips"]:
                raise StateError("round_trip_cycle_already_committed")
            state["round_trips"][
                str(preflight["cycle_id"])
            ] = accounting
            del state["open_positions"][route_key]
            reason = "terminal_exit_fill_committed"
        state["pending_intents"].pop(intent_id, None)
        state["completed_intents"][intent_id] = receipt_id
        state["committed_receipt_ids"].append(receipt_id)
        _write_state(self.state_path, state)
        return _result(
            "filled",
            reason,
            receipt=dict(fill),
            accounting=accounting,
            trigger=preflight["trigger"],
        )


def main(argv: list[str] | None = None) -> int:
    """Inert CLI: an owning runtime must supply provider composition."""

    parser = argparse.ArgumentParser(
        description="Receipt-gated Orca dual hunter"
    )
    parser.parse_args(argv)
    print(
        json.dumps(
            _result("no_data", "provider_composition_required"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
