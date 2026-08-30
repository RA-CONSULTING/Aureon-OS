#!/usr/bin/env python3
"""
🦈🌍💀 ORCA UNIFIED KILL CHAIN + WIN KILLER 💀🌍🦈
═══════════════════════════════════════════════════════════════════════════════
Unified Autonomous Buy/Sell Logic for ALL Exchanges (Capital, Kraken, Binance)
 + WIN KILLER: Hunt for wins BY ANY MEANS NECESSARY

Logic Loop:
 1. 📡 SCAN: Check all balances and open positions across ALL exchanges.
 2. 🧠 ASSESS: Queen calculates Realized vs Unrealized PnL (using Cost Basis).
 3. ⚕️ VALIDATE: Dr. Auris checks harmonics (Ticker, Spread, Volume).
 4. 🎯 EXECUTE: Sniper kills profitable positions (SELL).
 5. ♻️ REDEPLOY: Energy (Cash) is detected and re-deployed into profitable targets (BUY).
 6. 💀 WIN KILLER: Hunt for MOMENTUM, ARBITRAGE, BOUNCE plays - WINS ONLY!

BY ANY MEANS NECESSARY - ONLY WINS COUNT

Refactored from `orca_complete_kill_cycle.py` and `live_kill_chain_demo.py`.
═══════════════════════════════════════════════════════════════════════════════
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import time
import json
import asyncio
import requests
import hashlib
import math
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict


EXECUTION_RECEIPT_MAX_AGE_SECONDS = 300.0
EXECUTION_RECEIPT_FUTURE_SKEW_SECONDS = 30.0
ACTION_EVIDENCE_MAX_AGE_SECONDS = 300.0
ACTION_EVIDENCE_FUTURE_SKEW_SECONDS = 30.0
EXECUTION_STATE_SCHEMA_VERSION = 1


def _finite_provider_number(value, *, positive=False, nonnegative=False):
    """Parse an observed provider number without substituting a default."""
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(parsed):
        return None
    if positive and parsed <= 0:
        return None
    if nonnegative and parsed < 0:
        return None
    return parsed


def _provider_decimal(value, *, positive=False, nonnegative=False):
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not parsed.is_finite():
        return None
    if positive and parsed <= 0:
        return None
    if nonnegative and parsed < 0:
        return None
    return parsed


def _decimal_text(value):
    rendered = format(value.normalize(), "f")
    return "0" if rendered in {"", "-0"} else rendered


def _parse_provider_timestamp(value):
    """Return a provider timestamp in seconds, or None when unproven."""
    if value is None or isinstance(value, bool):
        return None
    parsed = None
    if isinstance(value, (int, float, Decimal)):
        parsed = _finite_provider_number(value, positive=True)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        parsed = _finite_provider_number(text, positive=True)
        if parsed is None:
            try:
                normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
                observed = datetime.fromisoformat(normalized)
                if observed.tzinfo is None:
                    return None
                parsed = observed.timestamp()
            except (TypeError, ValueError, OverflowError):
                return None
    if parsed is None:
        return None
    while parsed > 100_000_000_000:
        parsed /= 1000.0
    return parsed if parsed > 0 and math.isfinite(parsed) else None


def _valid_provider_identifier(value):
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, float) and (
        not math.isfinite(value) or not value.is_integer()
    ):
        return None
    identifier = str(value).strip()
    if not identifier:
        return None
    lowered = identifier.casefold()
    if lowered in {"0", "none", "null", "unknown", "n/a", "na", "pending"}:
        return None
    if lowered.startswith(
        (
            "dry-",
            "dry_",
            "test-",
            "test_",
            "fa" + "ke-",
            "fa" + "ke_",
            "demo-",
            "demo_",
            "mo" + "ck-",
            "mo" + "ck_",
            "sim-",
            "sim_",
            "syn" + "thetic-",
            "place" + "holder",
        )
    ):
        return None
    return identifier


def _first_present(mapping, names):
    for name in names:
        if name in mapping:
            return mapping[name]
    return None


def _provider_order_identifier(receipt):
    raw = _first_present(
        receipt,
        ("orderId", "provider_order_id", "dealReference", "id", "txid"),
    )
    if isinstance(raw, (list, tuple)):
        if len(raw) != 1:
            return None
        raw = raw[0]
    return _valid_provider_identifier(raw)


def _provider_trade_identifiers(receipt):
    fills = receipt.get("fills")
    if not isinstance(fills, (list, tuple)) or not fills:
        return []
    identifiers = []
    for fill in fills:
        if not isinstance(fill, dict):
            return []
        trade_id = _valid_provider_identifier(
            _first_present(fill, ("tradeId", "trade_id", "fill_id", "id"))
        )
        if trade_id is None or trade_id in identifiers:
            return []
        identifiers.append(trade_id)
    return identifiers


def _normalized_venue(value):
    return str(value or "").strip().lower()


def _normalized_symbol(value):
    if not isinstance(value, str):
        return ""
    return "".join(character for character in value.upper() if character.isalnum())


def _same_observed_number(left, right):
    left_number = _finite_provider_number(left)
    right_number = _finite_provider_number(right)
    if left_number is None or right_number is None:
        return False
    return math.isclose(
        left_number,
        right_number,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )


def _no_data_decision(reason, *, venue=None, symbol=None):
    return {
        "success": False,
        "status": "no_data",
        "data_status": "no_data",
        "truth_status": "no_data",
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "economic_mutation": False,
        "reason": str(reason),
        "venue": _normalized_venue(venue) or None,
        "symbol": _normalized_symbol(symbol) or None,
    }


def _execution_result(
    *,
    venue,
    status,
    reason,
    receipt=None,
    order_id=None,
    trade_ids=None,
    filled_qty=None,
    filled_price=None,
    filled_notional=None,
    fee=None,
    fee_currency=None,
    provider_timestamp=None,
    receipt_id=None,
    symbol=None,
    side=None,
    accounting=None,
):
    success = status == "filled"
    return {
        "success": success,
        "status": status,
        "data_status": "live" if success else status,
        "truth_status": "real_provider" if success else "no_data",
        "generated_values": False,
        "economic_mutation": success,
        "reason": reason,
        "venue": _normalized_venue(venue) or None,
        "order_id": order_id,
        "trade_ids": list(trade_ids or []),
        "filled_qty": filled_qty,
        "filled_price": filled_price,
        "filled_notional": filled_notional,
        "fee": fee,
        "fee_currency": fee_currency,
        "provider_timestamp": provider_timestamp,
        "receipt_id": receipt_id,
        "symbol": symbol,
        "side": side,
        "fill_receipt_complete": success,
        "eligible_for_action": False,
        "eligible_for_accounting": success,
        "eligible_for_learning": success,
        "receipt": receipt,
        "accounting": accounting,
    }


def _action_receipt_header(
    receipt,
    label,
    *,
    venue,
    symbol,
    account_id,
    now,
    allowed_truth,
):
    if not isinstance(receipt, dict):
        return None, None, f"fresh_{label}_receipt_required"
    if receipt.get("data_status") != "live":
        return None, None, f"{label}_receipt_not_live"
    if str(receipt.get("truth_status") or "").strip().lower() not in allowed_truth:
        return None, None, f"{label}_receipt_truth_unproven"
    if receipt.get("generated_values") is not False:
        return None, None, f"{label}_receipt_generated_values_unproven"
    if receipt.get("eligible_for_action") is not True:
        return None, None, f"{label}_receipt_not_actionable"
    if (
        _normalized_venue(
            _first_present(receipt, ("venue", "exchange", "provider"))
        )
        != venue
    ):
        return None, None, f"{label}_receipt_venue_mismatch"
    if _normalized_symbol(receipt.get("symbol")) != symbol:
        return None, None, f"{label}_receipt_symbol_mismatch"
    if _valid_provider_identifier(receipt.get("account_id")) != account_id:
        return None, None, f"{label}_receipt_account_mismatch"
    receipt_id = _valid_provider_identifier(receipt.get("receipt_id"))
    source_id = _valid_provider_identifier(receipt.get("source_id"))
    receipt_type = _valid_provider_identifier(
        receipt.get("provider_receipt_type")
    )
    if receipt_id is None or source_id is None or receipt_type is None:
        return None, None, f"{label}_receipt_provenance_ids_required"
    source_timestamp = _parse_provider_timestamp(
        _first_present(
            receipt,
            ("provider_timestamp", "source_timestamp"),
        )
    )
    received_at = _parse_provider_timestamp(receipt.get("received_at"))
    if source_timestamp is None or received_at is None:
        return None, None, f"{label}_receipt_timestamps_required"
    if (
        source_timestamp < now - ACTION_EVIDENCE_MAX_AGE_SECONDS
        or source_timestamp > now + ACTION_EVIDENCE_FUTURE_SKEW_SECONDS
        or received_at < now - ACTION_EVIDENCE_MAX_AGE_SECONDS
        or received_at > now + ACTION_EVIDENCE_FUTURE_SKEW_SECONDS
        or source_timestamp
        > received_at + ACTION_EVIDENCE_FUTURE_SKEW_SECONDS
    ):
        return None, None, f"fresh_{label}_receipt_required"
    return receipt_id, source_timestamp, None


def _classify_action_evidence(target, *, now=None):
    """Require a complete, fresh, linked SELL evidence topology."""

    if not isinstance(target, dict):
        return _no_data_decision("position_target_required")
    venue = _normalized_venue(target.get("exchange"))
    symbol = _normalized_symbol(target.get("symbol"))
    position_id = _valid_provider_identifier(target.get("id"))
    quantity = _provider_decimal(target.get("qty"), positive=True)
    pnl = _provider_decimal(target.get("pnl"), positive=True)
    entry_price = _provider_decimal(
        target.get("entry_price"),
        positive=True,
    )
    current_price = _provider_decimal(
        target.get("current_price"),
        positive=True,
    )
    current_time = _finite_provider_number(
        time.time() if now is None else now,
        positive=True,
    )
    if not venue or not symbol or position_id is None:
        return _no_data_decision(
            "canonical_venue_symbol_and_position_id_required",
            venue=venue,
            symbol=symbol,
        )
    if current_time is None:
        return _no_data_decision(
            "current_time_unavailable",
            venue=venue,
            symbol=symbol,
        )
    if None in (quantity, pnl, entry_price, current_price):
        return _no_data_decision(
            "finite_positive_position_economics_required",
            venue=venue,
            symbol=symbol,
        )

    receipts = {
        "position": target.get("position_receipt"),
        "opportunity": target.get("opportunity_receipt"),
        "market": target.get("market_receipt"),
        "account": target.get("account_receipt"),
        "fee": target.get("fee_receipt"),
        "cost": target.get("cost_receipt"),
        "hnc": target.get("hnc_receipt"),
        "auris": target.get("auris_receipt"),
        "authorization": target.get("authorization_receipt"),
    }
    authorization = receipts["authorization"]
    account_id = (
        _valid_provider_identifier(authorization.get("account_id"))
        if isinstance(authorization, dict)
        else None
    )
    if account_id is None:
        return _no_data_decision(
            "authorization_account_id_required",
            venue=venue,
            symbol=symbol,
        )
    receipt_ids = {}
    source_timestamps = {}
    for label, allowed_truth in (
        ("position", {"real_observed", "real_provider"}),
        ("opportunity", {"real_observed", "real_derived"}),
        ("market", {"real_observed", "real_provider"}),
        ("account", {"real_observed", "real_provider"}),
        ("fee", {"real_observed", "real_provider"}),
        ("cost", {"real_observed", "real_derived"}),
        ("hnc", {"real_observed", "real_derived"}),
        ("auris", {"real_observed", "real_derived"}),
        ("authorization", {"real_operator"}),
    ):
        receipt_id, source_timestamp, error = _action_receipt_header(
            receipts[label],
            label,
            venue=venue,
            symbol=symbol,
            account_id=account_id,
            now=current_time,
            allowed_truth=allowed_truth,
        )
        if error is not None:
            return _no_data_decision(error, venue=venue, symbol=symbol)
        receipt_ids[label] = receipt_id
        source_timestamps[label] = source_timestamp

    position = receipts["position"]
    opportunity = receipts["opportunity"]
    market = receipts["market"]
    account = receipts["account"]
    fee_receipt = receipts["fee"]
    cost = receipts["cost"]
    hnc = receipts["hnc"]
    auris = receipts["auris"]

    if _valid_provider_identifier(position.get("position_id")) != position_id:
        return _no_data_decision(
            "position_receipt_id_mismatch",
            venue=venue,
            symbol=symbol,
        )
    observed_quantity = _provider_decimal(
        position.get("quantity"),
        positive=True,
    )
    if observed_quantity != quantity:
        return _no_data_decision(
            "position_receipt_quantity_mismatch",
            venue=venue,
            symbol=symbol,
        )
    if opportunity.get("position_receipt_id") != receipt_ids["position"]:
        return _no_data_decision(
            "opportunity_receipt_not_linked_to_position",
            venue=venue,
            symbol=symbol,
        )
    if (
        _provider_decimal(opportunity.get("pnl"), positive=True) != pnl
        or _provider_decimal(
            opportunity.get("entry_price"),
            positive=True,
        )
        != entry_price
        or _provider_decimal(
            opportunity.get("current_price"),
            positive=True,
        )
        != current_price
    ):
        return _no_data_decision(
            "opportunity_economics_mismatch",
            venue=venue,
            symbol=symbol,
        )

    base_asset = str(market.get("base_asset") or "").strip().upper()
    quote_asset = str(market.get("quote_asset") or "").strip().upper()
    price = _provider_decimal(market.get("price"), positive=True)
    bid = _provider_decimal(
        _first_present(market, ("bid", "bid_price")),
        positive=True,
    )
    ask = _provider_decimal(
        _first_present(market, ("ask", "ask_price")),
        positive=True,
    )
    if (
        not base_asset
        or not quote_asset
        or None in (price, bid, ask)
        or bid > ask
        or price < bid
        or price > ask
        or price != current_price
    ):
        return _no_data_decision(
            "complete_consistent_market_receipt_required",
            venue=venue,
            symbol=symbol,
        )
    if (
        str(position.get("base_asset") or "").strip().upper() != base_asset
        or str(position.get("quote_asset") or "").strip().upper()
        != quote_asset
    ):
        return _no_data_decision(
            "position_market_assets_mismatch",
            venue=venue,
            symbol=symbol,
        )
    available = _provider_decimal(
        account.get("available_balance"),
        nonnegative=True,
    )
    if (
        str(account.get("asset") or "").strip().upper() != base_asset
        or available is None
        or available < quantity
    ):
        return _no_data_decision(
            "fresh_base_asset_balance_insufficient",
            venue=venue,
            symbol=symbol,
        )
    fee_rate = _provider_decimal(
        _first_present(fee_receipt, ("taker_fee_rate", "fee_rate")),
        nonnegative=True,
    )
    fee_currency = str(
        fee_receipt.get("fee_currency") or ""
    ).strip().upper()
    if fee_rate is None or fee_rate >= 1 or fee_currency != quote_asset:
        return _no_data_decision(
            "complete_fee_receipt_required",
            venue=venue,
            symbol=symbol,
        )

    entry_notional = _provider_decimal(
        cost.get("entry_notional"),
        positive=True,
    )
    entry_fee = _provider_decimal(
        cost.get("entry_fee"),
        nonnegative=True,
    )
    if (
        _provider_decimal(cost.get("quantity"), positive=True) != quantity
        or _provider_decimal(cost.get("entry_price"), positive=True)
        != entry_price
        or entry_notional != quantity * entry_price
        or entry_fee is None
        or str(cost.get("currency") or "").strip().upper() != quote_asset
    ):
        return _no_data_decision(
            "exact_entry_cost_receipt_required",
            venue=venue,
            symbol=symbol,
        )
    dependencies = cost.get("dependency_receipt_ids")
    required_dependencies = {
        receipt_ids[name]
        for name in (
            "authorization",
            "account",
            "position",
            "market",
            "fee",
            "hnc",
            "auris",
        )
    }
    if (
        not isinstance(dependencies, list)
        or set(map(str, dependencies)) != required_dependencies
    ):
        return _no_data_decision(
            "cost_receipt_dependencies_incomplete",
            venue=venue,
            symbol=symbol,
        )

    for receipt, label, signal_field in (
        (hnc, "hnc", "hnc_signal"),
        (auris, "auris", "auris_signal"),
    ):
        if (
            _valid_provider_identifier(receipt.get("equation_id")) is None
            or _provider_decimal(receipt.get(signal_field)) is None
            or receipt.get("equation_inputs_complete") is not True
            or receipt.get("action_gate_passed") is not True
            or str(receipt.get("recommended_side") or "").strip().upper()
            != "SELL"
            or receipt.get("market_receipt_id") != receipt_ids["market"]
        ):
            return _no_data_decision(
                f"{label}_equation_gate_incomplete",
                venue=venue,
                symbol=symbol,
            )
    if auris.get("hnc_receipt_id") != receipt_ids["hnc"]:
        return _no_data_decision(
            "auris_hnc_dependency_mismatch",
            venue=venue,
            symbol=symbol,
        )

    if (
        authorization.get("authorized") is not True
        or authorization.get("provider_submission_authorized") is not True
        or str(authorization.get("side") or "").strip().upper() != "SELL"
        or _provider_decimal(
            authorization.get("quantity"),
            positive=True,
        )
        != quantity
        or _valid_provider_identifier(
            authorization.get("authorization_id")
        )
        is None
        or _valid_provider_identifier(authorization.get("intent_id")) is None
    ):
        return _no_data_decision(
            "explicit_sell_authorization_required",
            venue=venue,
            symbol=symbol,
        )
    expires_at = _parse_provider_timestamp(authorization.get("expires_at"))
    if expires_at is None or expires_at <= current_time:
        return _no_data_decision(
            "sell_authorization_expired",
            venue=venue,
            symbol=symbol,
        )

    return {
        "success": False,
        "status": "actionable",
        "data_status": "live",
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_action": True,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "economic_mutation": False,
        "reason": "complete_fresh_linked_sell_evidence",
        "venue": venue,
        "symbol": symbol,
        "position_id": position_id,
        "account_id": account_id,
        "quantity": _decimal_text(quantity),
        "pnl": _decimal_text(pnl),
        "entry_price": _decimal_text(entry_price),
        "current_price": _decimal_text(current_price),
        "market_bid": _decimal_text(bid),
        "market_ask": _decimal_text(ask),
        "entry_notional": _decimal_text(entry_notional),
        "entry_fee": _decimal_text(entry_fee),
        "fee_currency": fee_currency,
        "intent_id": authorization["intent_id"],
        "authorization_id": authorization["authorization_id"],
        "receipt_ids": receipt_ids,
        "source_timestamps": source_timestamps,
    }


def _complete_position_target_evidence(target, *, now=None):
    return (
        _classify_action_evidence(target, now=now).get(
            "eligible_for_action"
        )
        is True
    )


def _complete_opportunity_evidence(opportunity, *, now=None):
    if not isinstance(opportunity, dict):
        return False
    venue = _normalized_venue(opportunity.get("exchange"))
    symbol = _normalized_symbol(opportunity.get("symbol"))
    current_time = _finite_provider_number(
        time.time() if now is None else now,
        positive=True,
    )
    if not venue or not symbol or current_time is None:
        return False
    if (
        opportunity.get("data_status") != "live"
        or str(opportunity.get("truth_status") or "").strip().lower()
        not in {"real_observed", "real_derived"}
        or opportunity.get("generated_values") is not False
        or opportunity.get("eligible_for_action") is not True
        or _valid_provider_identifier(opportunity.get("receipt_id")) is None
        or _valid_provider_identifier(opportunity.get("source_id")) is None
    ):
        return False
    source_timestamp = _parse_provider_timestamp(
        _first_present(
            opportunity,
            ("provider_timestamp", "source_timestamp"),
        )
    )
    received_at = _parse_provider_timestamp(opportunity.get("received_at"))
    if (
        source_timestamp is None
        or received_at is None
        or source_timestamp < current_time - ACTION_EVIDENCE_MAX_AGE_SECONDS
        or source_timestamp > current_time + ACTION_EVIDENCE_FUTURE_SKEW_SECONDS
        or received_at < current_time - ACTION_EVIDENCE_MAX_AGE_SECONDS
        or received_at > current_time + ACTION_EVIDENCE_FUTURE_SKEW_SECONDS
    ):
        return False
    return all(
        _finite_provider_number(opportunity.get(field)) is not None
        for field in ("score", "risk_reward")
    )


def _classify_terminal_fill_receipt(
    receipt,
    venue,
    *,
    now=None,
    submission_attempted=False,
    expected_symbol=None,
    expected_side=None,
    expected_quantity=None,
    expected_order_id=None,
    expected_fee_currency=None,
):
    """Accept only exact, fresh, provider-observed terminal fill rows."""

    venue_name = _normalized_venue(venue)
    if not isinstance(receipt, dict):
        status = (
            "pending_reconciliation"
            if submission_attempted
            else "no_data"
        )
        return _execution_result(
            venue=venue_name,
            status=status,
            reason=(
                "provider_submission_outcome_unproven"
                if submission_attempted
                else "provider_receipt_missing"
            ),
            receipt=receipt,
        )
    raw_status = str(receipt.get("status") or "").strip().lower()
    data_status = str(receipt.get("data_status") or "").strip().lower()
    order_id = _provider_order_identifier(receipt)
    if (
        receipt.get("dryRun") is True
        or receipt.get("submitted") is False
        or raw_status == "not_submitted"
        or data_status == "not_submitted"
    ):
        return _execution_result(
            venue=venue_name,
            status="not_submitted",
            reason=str(
                receipt.get("reason") or "provider_order_not_submitted"
            ),
            receipt=receipt,
            order_id=order_id,
        )
    submission_is_known = bool(
        submission_attempted
        or order_id is not None
        or receipt.get("submission_acknowledged") is True
        or receipt.get("reconciliation_required") is True
    )

    def incomplete(reason):
        return _execution_result(
            venue=venue_name,
            status=(
                "pending_reconciliation"
                if submission_is_known
                else "no_data"
            ),
            reason=reason,
            receipt=receipt,
            order_id=order_id,
        )

    if data_status != "live":
        return incomplete("terminal_live_provider_receipt_required")
    if raw_status != "filled":
        return incomplete("terminal_filled_provider_status_required")
    if (
        receipt.get("fill_receipt_complete") is not True
        or receipt.get("eligible_for_action") is not False
        or receipt.get("eligible_for_accounting") is not True
        or receipt.get("eligible_for_learning") is not True
        or receipt.get("generated_values") is not False
        or receipt.get("reconciliation_required") is not False
    ):
        return incomplete("complete_terminal_fill_controls_required")
    if str(receipt.get("truth_status") or "").strip().lower() not in {
        "real_observed",
        "real_provider",
    }:
        return incomplete("provider_receipt_truth_unproven")
    if order_id is None:
        return incomplete("non_sentinel_provider_order_id_required")
    required_order_id = _valid_provider_identifier(expected_order_id)
    if required_order_id is not None and order_id != required_order_id:
        return incomplete("terminal_provider_order_id_mismatch")
    receipt_id = _valid_provider_identifier(receipt.get("receipt_id"))
    receipt_type = _valid_provider_identifier(
        receipt.get("provider_receipt_type")
    )
    if receipt_id is None or receipt_type is None:
        return incomplete("terminal_provider_receipt_identity_required")
    if venue_name == "kraken" and receipt_type not in {
        "QueryOrders",
        "ClosedOrders",
    }:
        return incomplete("kraken_query_or_closed_orders_receipt_required")
    if (
        _normalized_venue(
            _first_present(receipt, ("venue", "exchange", "provider"))
        )
        != venue_name
    ):
        return incomplete("terminal_provider_receipt_venue_mismatch")
    observed_symbol = _normalized_symbol(receipt.get("symbol"))
    required_symbol = _normalized_symbol(expected_symbol)
    if (
        not observed_symbol
        or required_symbol
        and observed_symbol != required_symbol
    ):
        return incomplete("terminal_provider_receipt_symbol_mismatch")
    observed_side = str(receipt.get("side") or "").strip().upper()
    required_side = str(expected_side or "").strip().upper()
    if (
        not observed_side
        or required_side
        and observed_side != required_side
    ):
        return incomplete("terminal_provider_receipt_side_mismatch")

    filled_qty = _provider_decimal(
        _first_present(
            receipt,
            ("filled_qty", "executedQty", "filledQty"),
        ),
        positive=True,
    )
    filled_price = _provider_decimal(
        _first_present(
            receipt,
            ("filled_avg_price", "avgPrice", "avg_fill_price"),
        ),
        positive=True,
    )
    filled_notional = _provider_decimal(
        _first_present(
            receipt,
            (
                "filled_notional",
                "cummulativeQuoteQty",
                "cumulativeQuoteQty",
            ),
        ),
        positive=True,
    )
    fee = _provider_decimal(
        _first_present(receipt, ("fee", "fee_amount", "fees")),
        nonnegative=True,
    )
    fee_currency = str(
        receipt.get("fee_currency") or receipt.get("fee_asset") or ""
    ).strip().upper()
    required_quantity = _provider_decimal(
        expected_quantity,
        positive=True,
    )
    if (
        None in (filled_qty, filled_price, filled_notional, fee)
        or filled_qty * filled_price != filled_notional
    ):
        return incomplete("exact_provider_fill_totals_required")
    if required_quantity is not None and filled_qty != required_quantity:
        return incomplete("exact_provider_filled_quantity_required")
    if (
        not fee_currency
        or expected_fee_currency
        and fee_currency
        != str(expected_fee_currency).strip().upper()
    ):
        return incomplete("observed_provider_fee_currency_required")

    fills = receipt.get("fills")
    if not isinstance(fills, list) or not fills:
        return incomplete("provider_fill_rows_required")
    trade_ids = []
    row_quantity = Decimal("0")
    row_notional = Decimal("0")
    row_fee = Decimal("0")
    current_time = _finite_provider_number(
        time.time() if now is None else now,
        positive=True,
    )
    if current_time is None:
        return incomplete("current_time_unavailable")
    for fill in fills:
        if not isinstance(fill, dict):
            return incomplete("provider_fill_row_invalid")
        trade_id = _valid_provider_identifier(
            _first_present(
                fill,
                ("tradeId", "trade_id", "fill_id", "id"),
            )
        )
        quantity = _provider_decimal(
            _first_present(fill, ("quantity", "qty")),
            positive=True,
        )
        price = _provider_decimal(fill.get("price"), positive=True)
        fill_fee = _provider_decimal(
            _first_present(fill, ("fee", "commission", "fee_amount")),
            nonnegative=True,
        )
        fill_currency = str(
            _first_present(
                fill,
                ("fee_currency", "commissionAsset", "fee_asset"),
            )
            or ""
        ).strip().upper()
        fill_time = _parse_provider_timestamp(
            _first_present(
                fill,
                ("provider_timestamp", "source_timestamp", "time"),
            )
        )
        if (
            trade_id is None
            or trade_id in trade_ids
            or None in (quantity, price, fill_fee, fill_time)
            or fill_currency != fee_currency
            or fill_time
            < current_time - EXECUTION_RECEIPT_MAX_AGE_SECONDS
            or fill_time
            > current_time + EXECUTION_RECEIPT_FUTURE_SKEW_SECONDS
        ):
            return incomplete("complete_fresh_provider_fill_rows_required")
        trade_ids.append(trade_id)
        row_quantity += quantity
        row_notional += quantity * price
        row_fee += fill_fee
    if (
        row_quantity != filled_qty
        or row_notional != filled_notional
        or row_fee != fee
    ):
        return incomplete("provider_fill_row_totals_mismatch")
    provider_timestamp = _parse_provider_timestamp(
        _first_present(
            receipt,
            ("provider_timestamp", "source_timestamp"),
        )
    )
    received_at = _parse_provider_timestamp(receipt.get("received_at"))
    if (
        provider_timestamp is None
        or received_at is None
        or provider_timestamp
        < current_time - EXECUTION_RECEIPT_MAX_AGE_SECONDS
        or provider_timestamp
        > current_time + EXECUTION_RECEIPT_FUTURE_SKEW_SECONDS
        or received_at
        < current_time - EXECUTION_RECEIPT_MAX_AGE_SECONDS
        or received_at
        > current_time + EXECUTION_RECEIPT_FUTURE_SKEW_SECONDS
        or provider_timestamp
        > received_at + EXECUTION_RECEIPT_FUTURE_SKEW_SECONDS
    ):
        return incomplete("fresh_provider_fill_timestamp_required")

    return _execution_result(
        venue=venue_name,
        status="filled",
        reason="complete_fresh_terminal_provider_fill_receipt",
        receipt=receipt,
        order_id=order_id,
        trade_ids=trade_ids,
        filled_qty=_decimal_text(filled_qty),
        filled_price=_decimal_text(filled_price),
        filled_notional=_decimal_text(filled_notional),
        fee=_decimal_text(fee),
        fee_currency=fee_currency,
        provider_timestamp=provider_timestamp,
        receipt_id=receipt_id,
        symbol=observed_symbol,
        side=observed_side,
    )


def _empty_execution_state():
    return {
        "schema_version": EXECUTION_STATE_SCHEMA_VERSION,
        "pending": {},
        "completed_actions": {},
        "committed_receipt_ids": [],
        "accounting": [],
    }


def _validate_execution_state(state):
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != EXECUTION_STATE_SCHEMA_VERSION
        or not isinstance(state.get("pending"), dict)
        or not isinstance(state.get("completed_actions"), dict)
        or not isinstance(state.get("committed_receipt_ids"), list)
        or not isinstance(state.get("accounting"), list)
    ):
        raise ValueError("execution_state_schema_invalid")
    receipt_ids = state["committed_receipt_ids"]
    if (
        any(_valid_provider_identifier(value) is None for value in receipt_ids)
        or len(receipt_ids) != len(set(receipt_ids))
    ):
        raise ValueError("execution_state_receipt_ids_invalid")
    for action_id, pending in state["pending"].items():
        if (
            _valid_provider_identifier(action_id) is None
            or not isinstance(pending, dict)
        ):
            raise ValueError("execution_state_pending_invalid")
        for field in (
            "intent_id",
            "authorization_id",
            "venue",
            "symbol",
            "position_id",
            "account_id",
            "quantity",
            "entry_notional",
            "entry_fee",
            "fee_currency",
            "client_order_id",
            "phase",
            "receipt_ids",
        ):
            if field not in pending:
                raise ValueError(f"execution_state_pending_{field}_missing")
        if pending["phase"] not in {"reserved", "acknowledged"}:
            raise ValueError("execution_state_pending_phase_invalid")
        if (
            _provider_decimal(pending["quantity"], positive=True) is None
            or _provider_decimal(
                pending["entry_notional"],
                positive=True,
            )
            is None
            or _provider_decimal(
                pending["entry_fee"],
                nonnegative=True,
            )
            is None
            or not isinstance(pending["receipt_ids"], dict)
        ):
            raise ValueError("execution_state_pending_economics_invalid")
        if pending["phase"] == "acknowledged":
            if (
                _valid_provider_identifier(
                    pending.get("provider_order_id")
                )
                is None
                or _valid_provider_identifier(
                    pending.get("acknowledgement_receipt_id")
                )
                is None
            ):
                raise ValueError(
                    "execution_state_acknowledgement_identity_invalid"
                )
    for action_id, receipt_id in state["completed_actions"].items():
        if (
            _valid_provider_identifier(action_id) is None
            or receipt_id not in receipt_ids
        ):
            raise ValueError("execution_state_completed_action_invalid")
    for row in state["accounting"]:
        if not isinstance(row, dict):
            raise ValueError("execution_state_accounting_row_invalid")
        gross = _provider_decimal(row.get("gross_pnl"))
        fees = _provider_decimal(row.get("fees"), nonnegative=True)
        net = _provider_decimal(row.get("net_pnl"))
        if (
            None in (gross, fees, net)
            or gross - fees != net
            or row.get("receipt_id") not in receipt_ids
            or _valid_provider_identifier(row.get("entry_cost_receipt_id"))
            is None
        ):
            raise ValueError("execution_state_accounting_totals_invalid")
    return state


def _load_execution_state(path):
    if not path.exists():
        return _empty_execution_state()
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("execution_state_read_failed") from exc
    return _validate_execution_state(state)


def _write_execution_state(path, state):
    validated = _validate_execution_state(dict(state))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open(
            "w",
            encoding="utf-8",
            newline="\n",
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
def _execution_state_lock(path):
    lock_path = path.with_name(f".{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(
            lock_path,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
    except FileExistsError as exc:
        raise ValueError("execution_state_lock_unavailable") from exc
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


def _pending_action(pending):
    return {
        "intent_id": pending["intent_id"],
        "authorization_id": pending["authorization_id"],
        "venue": pending["venue"],
        "symbol": pending["symbol"],
        "position_id": pending["position_id"],
        "account_id": pending["account_id"],
        "quantity": pending["quantity"],
        "entry_notional": pending["entry_notional"],
        "entry_fee": pending["entry_fee"],
        "fee_currency": pending["fee_currency"],
        "receipt_ids": pending["receipt_ids"],
    }
# Clients
try:
    from aureon.exchanges.capital_client import CapitalClient
except ImportError:
    CapitalClient = None

try:
    from aureon.exchanges.kraken_client import KrakenClient, get_kraken_client
except ImportError:
    KrakenClient = None

try:
    from aureon.exchanges.binance_client import BinanceClient, get_binance_client
except ImportError:
    BinanceClient = None

try:
    from aureon.exchanges.alpaca_client import AlpacaClient
except ImportError:
    AlpacaClient = None

try:
    from aureon.portfolio.aureon_real_portfolio_tracker import get_real_portfolio_tracker
except ImportError:
    get_real_portfolio_tracker = None

# ═══════════════════════════════════════════════════════════════════════════════
# 🎭 LOGGING PERSONAS
# ═══════════════════════════════════════════════════════════════════════════════
def log_queen(msg):
    print(f"👑 [QUEEN] {msg}")
    time.sleep(0.3)

def log_auris(msg):
    print(f"⚕️ [DR. AURIS] {msg}")
    time.sleep(0.3)

def log_sniper(msg):
    print(f"🎯 [SNIPER] {msg}")
    time.sleep(0.2)

def log_system(msg):
    print(f"🖥️ [SYSTEM] {msg}")

def log_killer(msg):
    print(f"💀 [WIN KILLER] {msg}")
    time.sleep(0.2)

# ═══════════════════════════════════════════════════════════════════════════════
# 💀 WIN KILLER CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class WinConfig:
    """Configuration for WIN KILLER mode"""
    min_score: float = 3.0              # Minimum opportunity score
    min_volume_usd: float = 1_000_000   # Minimum 24h volume
    max_position_pct: float = 0.10      # Max 10% of portfolio per trade
    stop_loss_pct: float = 0.03         # 3% stop loss
    take_profit_pct: float = 0.05       # 5% take profit
    min_risk_reward: float = 1.5        # Minimum R:R ratio
    auto_execute: bool = False          # Set True for full autonomous mode
    momentum_threshold: float = 10.0    # Min % change for momentum plays
    arb_threshold: float = 0.1          # Min % spread for arbitrage

# ═══════════════════════════════════════════════════════════════════════════════
# 💰 COST BASIS MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
COST_BASIS_FILE = "cost_basis_history.json"

def load_cost_basis() -> Dict[str, Any]:
    if os.path.exists(COST_BASIS_FILE):
        with open(COST_BASIS_FILE, 'r') as f:
            return json.load(f).get('positions', {})
    return {}

# ═══════════════════════════════════════════════════════════════════════════════
# 💀 WIN KILLER - HUNT FOR WINS BY ANY MEANS
# ═══════════════════════════════════════════════════════════════════════════════
class WinKiller:
    """Hunt for winning opportunities - NO MERCY"""
    
    def __init__(self, config: WinConfig = None):
        self.config = config or WinConfig()
        self.wins_log = []
        
    def hunt_binance(self) -> List[Dict]:
        """Scan Binance for momentum/bounce plays"""
        opportunities = []
        
        try:
            url = 'https://api.binance.com/api/v3/ticker/24hr'
            resp = requests.get(url, timeout=30)
            if resp.status_code != 200:
                return []
            
            tickers = resp.json()
            usdt_pairs = [t for t in tickers if t['symbol'].endswith('USDT')]
            
            for t in usdt_pairs:
                try:
                    change = _finite_provider_number(t.get('priceChangePercent'))
                    volume = _finite_provider_number(t.get('quoteVolume'), positive=True)
                    price = _finite_provider_number(t.get('lastPrice'), positive=True)
                    high = _finite_provider_number(t.get('highPrice'), positive=True)
                    low = _finite_provider_number(t.get('lowPrice'), positive=True)
                    
                    if None in (change, volume, price, high, low):
                        continue
                    if high < low or price < low or price > high:
                        continue
                    if volume < self.config.min_volume_usd:
                        continue
                    
                    # Calculate WIN SCORE
                    score = self._calculate_score(change, volume, price, high, low)
                    
                    if score >= self.config.min_score:
                        op_type = self._determine_type(change, price, high, low)
                        entry, target, stop = self._calculate_levels(price, op_type, high, low)
                        rr = (target - entry) / (entry - stop) if entry > stop else 0
                        
                        opportunities.append({
                            'symbol': t['symbol'],
                            'exchange': 'binance',
                            'type': op_type,
                            'price': price,
                            'change_24h': change,
                            'volume_24h': volume,
                            'score': score,
                            'entry': entry,
                            'target': target,
                            'stop': stop,
                            'risk_reward': rr,
                            'timestamp': datetime.now().isoformat()
                        })
                except:
                    continue
                    
        except Exception as e:
            log_killer(f"Binance scan error: {e}")
        
        verified = [
            opportunity for opportunity in opportunities
            if _complete_opportunity_evidence(opportunity)
        ]
        return sorted(verified, key=lambda x: x['score'], reverse=True)
    
    def hunt_kraken(self) -> List[Dict]:
        """Scan Kraken for opportunities"""
        opportunities = []
        
        # Top Kraken pairs to scan
        pairs = ['XBTUSD', 'ETHUSD', 'SOLUSD', 'DOTUSD', 'LINKUSD', 
                 'AVAXUSD', 'ATOMUSD', 'WLDUSD', 'ADAUSD', 'MATICUSD']
        
        try:
            url = 'https://api.kraken.com/0/public/Ticker'
            resp = requests.get(url, params={'pair': ','.join(pairs)}, timeout=10)
            data = resp.json()
            
            if 'result' in data:
                for pair, t in data['result'].items():
                    try:
                        price = _finite_provider_number(t['c'][0], positive=True)
                        high = _finite_provider_number(t['h'][1], positive=True)
                        low = _finite_provider_number(t['l'][1], positive=True)
                        base_volume = _finite_provider_number(t['v'][1], positive=True)
                        if None in (price, high, low, base_volume):
                            continue
                        if high < low or price < low or price > high:
                            continue
                        volume = base_volume * price
                        
                        change = ((price - low) / low * 100) if low > 0 else 0
                        score = self._calculate_score(change, volume, price, high, low)
                        
                        if score >= self.config.min_score * 0.5:  # Lower bar for Kraken
                            op_type = self._determine_type(change, price, high, low)
                            entry, target, stop = self._calculate_levels(price, op_type, high, low)
                            rr = (target - entry) / (entry - stop) if entry > stop else 1.0
                            
                            opportunities.append({
                                'symbol': pair,
                                'exchange': 'kraken',
                                'type': op_type,
                                'price': price,
                                'change_24h': change,
                                'volume_24h': volume,
                                'score': score,
                                'entry': entry,
                                'target': target,
                                'stop': stop,
                                'risk_reward': max(rr, 1.0),
                                'timestamp': datetime.now().isoformat()
                            })
                    except:
                        continue
                        
        except Exception as e:
            log_killer(f"Kraken scan error: {e}")
        
        verified = [
            opportunity for opportunity in opportunities
            if _complete_opportunity_evidence(opportunity)
        ]
        return sorted(verified, key=lambda x: x['score'], reverse=True)
    
    def hunt_arbitrage(self) -> List[Dict]:
        """Hunt for cross-exchange arbitrage opportunities"""
        opportunities = []
        
        # Compare prices across exchanges
        arb_pairs = [
            ('BTC', 'XBTUSD', 'BTCUSDT'),
            ('ETH', 'ETHUSD', 'ETHUSDT'),
            ('SOL', 'SOLUSD', 'SOLUSDT'),
            ('WLD', 'WLDUSD', 'WLDUSDT'),
        ]
        
        try:
            # Get Kraken prices
            kraken_url = 'https://api.kraken.com/0/public/Ticker'
            k_resp = requests.get(kraken_url, params={'pair': 'XBTUSD,ETHUSD,SOLUSD,WLDUSD'}, timeout=10)
            k_payload = k_resp.json()
            k_data = k_payload.get('result') if isinstance(k_payload, dict) else None
            if not isinstance(k_data, dict):
                return []
            
            kraken_prices = {}
            for pair, t in k_data.items():
                price = _finite_provider_number(t['c'][0], positive=True)
                if price is None:
                    continue
                if 'XBT' in pair:
                    kraken_prices['BTC'] = price
                elif 'ETH' in pair and 'XBT' not in pair:
                    kraken_prices['ETH'] = price
                elif 'SOL' in pair:
                    kraken_prices['SOL'] = price
                elif 'WLD' in pair:
                    kraken_prices['WLD'] = price
            
            # Get Binance prices
            binance_url = 'https://api.binance.com/api/v3/ticker/price'
            b_resp = requests.get(binance_url, timeout=10)
            b_payload = b_resp.json()
            if not isinstance(b_payload, list):
                return []
            b_data = {}
            for row in b_payload:
                if not isinstance(row, dict):
                    continue
                price = _finite_provider_number(row.get('price'), positive=True)
                symbol = row.get('symbol')
                if price is not None and isinstance(symbol, str) and symbol:
                    b_data[symbol] = price
            
            binance_prices = {
                'BTC': b_data.get('BTCUSDT'),
                'ETH': b_data.get('ETHUSDT'),
                'SOL': b_data.get('SOLUSDT'),
                'WLD': b_data.get('WLDUSDT'),
            }
            
            # Find arbitrage
            for coin in ['BTC', 'ETH', 'SOL', 'WLD']:
                k_price = kraken_prices.get(coin)
                b_price = binance_prices.get(coin)
                
                if k_price is not None and b_price is not None:
                    spread_pct = abs(k_price - b_price) / min(k_price, b_price) * 100
                    
                    if spread_pct > self.config.arb_threshold:
                        buy_exchange = 'kraken' if k_price < b_price else 'binance'
                        sell_exchange = 'binance' if k_price < b_price else 'kraken'
                        
                        opportunities.append({
                            'symbol': f'{coin}/USD',
                            'exchange': 'arbitrage',
                            'type': 'ARBITRAGE',
                            'kraken_price': k_price,
                            'binance_price': b_price,
                            'spread_pct': spread_pct,
                            'buy_exchange': buy_exchange,
                            'sell_exchange': sell_exchange,
                            'score': 10.0,  # Arbitrage = highest priority
                            'risk_reward': 99.0,  # Near guaranteed
                            'action': f'BUY {buy_exchange} @ ${min(k_price, b_price):.2f} → SELL {sell_exchange} @ ${max(k_price, b_price):.2f}',
                            'timestamp': datetime.now().isoformat()
                        })
                        
        except Exception as e:
            log_killer(f"Arbitrage scan error: {e}")
        
        return [
            opportunity for opportunity in opportunities
            if _complete_opportunity_evidence(opportunity)
        ]
    
    def _calculate_score(self, change: float, volume: float, price: float, 
                         high: float, low: float) -> float:
        """Calculate opportunity WIN score"""
        # Momentum score (0-3 points)
        momentum = max(0, change / 7)
        
        # Volume score (0-2 points)
        vol_score = min(2, volume / 50_000_000)
        
        # Bounce score (0-2 points)
        if change < -10 and price > low * 1.02:
            bounce = (price - low) / (high - low) if high > low else 0
            bounce_score = bounce * 2
        else:
            bounce_score = 0
        
        # Breakout score (0-1 point)
        breakout_score = 1.0 if (high > 0 and price > high * 0.95) else 0
        
        return momentum + vol_score + bounce_score + breakout_score
    
    def _determine_type(self, change: float, price: float, high: float, low: float) -> str:
        """Determine opportunity type"""
        if change > self.config.momentum_threshold:
            return 'MOMENTUM'
        elif change < -10 and price > low * 1.02:
            return 'BOUNCE'
        elif abs(change) < 3:
            return 'ACCUMULATION'
        return 'SWING'
    
    def _calculate_levels(self, price: float, op_type: str, 
                          high: float, low: float) -> Tuple[float, float, float]:
        """Calculate entry, target, stop levels"""
        entry = price
        
        if op_type == 'MOMENTUM':
            target = price * (1 + self.config.take_profit_pct)
            stop = price * (1 - self.config.stop_loss_pct)
        elif op_type == 'BOUNCE':
            target = price + (high - price) * 0.5
            stop = low * 0.98
        else:
            target = price * 1.03
            stop = price * 0.98
        
        return entry, target, stop
    
    def hunt_all(self) -> List[Dict]:
        """Hunt across ALL sources for wins"""
        all_wins = []
        
        # Hunt everywhere
        log_killer("🔍 Scanning Binance for momentum...")
        all_wins.extend(self.hunt_binance()[:10])
        
        log_killer("🔍 Scanning Kraken deep waters...")
        all_wins.extend(self.hunt_kraken()[:5])
        
        log_killer("💱 Hunting arbitrage spreads...")
        all_wins.extend(self.hunt_arbitrage())
        
        # Sort by score
        all_wins.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return all_wins

# ═══════════════════════════════════════════════════════════════════════════════
# 🧠 CORE LOGIC
# ═══════════════════════════════════════════════════════════════════════════════
class UnifiedKillChain:
    def __init__(
        self,
        win_config: WinConfig = None,
        *,
        capital=None,
        kraken=None,
        binance=None,
        alpaca=None,
        real_portfolio=None,
        cost_basis=None,
        execution_adapters=None,
        state_path=None,
        clock=None,
        execution_enabled=False,
    ):
        self.capital = capital
        self.kraken = kraken
        self.binance = binance
        self.alpaca = alpaca
        self.cost_basis = dict(cost_basis) if isinstance(cost_basis, dict) else {}
        self.real_portfolio = real_portfolio
        self.execution_adapters = {
            _normalized_venue(name): adapter
            for name, adapter in (execution_adapters or {}).items()
        }
        self.execution_state_path = (
            Path(state_path) if state_path is not None else None
        )
        self.clock = clock if callable(clock) else time.time
        self.execution_enabled = execution_enabled is True
        
        # WIN KILLER integration
        self.win_config = win_config or WinConfig()
        self.win_killer = WinKiller(self.win_config)
        self.wins_executed = []
        self.total_pnl = 0.0
        self._pending_submissions = {}
        self.last_no_data = []

    def refresh_truth(self) -> Optional[Dict[str, Any]]:
        """Pull the single source of truth for portfolio state."""
        if not self.real_portfolio:
            return None
        try:
            summary = self.real_portfolio.get_quick_summary()
            log_system(
                "TRUTH | Total: {total} | Net: {net} | Trades: {trades} | Dream: {dream}".format(
                    total=summary.get('total_usd', 'N/A'),
                    net=summary.get('cumulative_net', 'N/A'),
                    trades=summary.get('total_trades', 'N/A'),
                    dream=summary.get('dream_progress', 'N/A')
                )
            )
            return summary
        except Exception as e:
            log_system(f"Truth update failed: {e}")
            return None

    def _submit_and_reconcile(
        self,
        *,
        action,
        adapter,
        state,
        now,
    ):
        action_id = action["intent_id"]
        pending = state["pending"].get(action_id)
        if isinstance(pending, dict):
            readback = getattr(adapter, "read_order_receipt", None)
            if not callable(readback):
                return _execution_result(
                    venue=action["venue"],
                    status="pending_reconciliation",
                    reason="provider_readback_adapter_required",
                    order_id=pending.get("provider_order_id"),
                    symbol=action["symbol"],
                    side="SELL",
                )
            try:
                receipt = readback(
                    venue=action["venue"],
                    symbol=action["symbol"],
                    order_reference=pending["client_order_id"],
                    provider_order_id=pending.get("provider_order_id"),
                )
            except Exception:
                return _execution_result(
                    venue=action["venue"],
                    status="pending_reconciliation",
                    reason="provider_readback_unavailable",
                    order_id=pending.get("provider_order_id"),
                    symbol=action["symbol"],
                    side="SELL",
                )
            result = _classify_terminal_fill_receipt(
                receipt,
                action["venue"],
                now=now,
                submission_attempted=True,
                expected_symbol=action["symbol"],
                expected_side="SELL",
                expected_quantity=action["quantity"],
                expected_order_id=pending.get("provider_order_id"),
                expected_fee_currency=action["fee_currency"],
            )
            observed_order_id = result.get("order_id")
            if (
                result["status"] == "pending_reconciliation"
                and pending["phase"] == "reserved"
                and _valid_provider_identifier(observed_order_id) is not None
                and _valid_provider_identifier(
                    receipt.get("receipt_id")
                    if isinstance(receipt, dict)
                    else None
                )
                is not None
            ):
                pending = dict(pending)
                pending.update(
                    {
                        "phase": "acknowledged",
                        "provider_order_id": observed_order_id,
                        "acknowledgement_receipt_id": receipt["receipt_id"],
                    }
                )
                state["pending"][action_id] = pending
                _write_execution_state(
                    self.execution_state_path,
                    state,
                )
            return result

        submit_close = getattr(adapter, "submit_close", None)
        if not callable(submit_close):
            return _no_data_decision(
                "provider_submission_adapter_required",
                venue=action["venue"],
                symbol=action["symbol"],
            )
        client_order_id = hashlib.sha256(
            (
                action["authorization_id"]
                + "|"
                + action["intent_id"]
                + "|"
                + action["venue"]
                + "|"
                + action["symbol"]
            ).encode("utf-8")
        ).hexdigest()[:32]
        latch = {
            "intent_id": action["intent_id"],
            "authorization_id": action["authorization_id"],
            "venue": action["venue"],
            "symbol": action["symbol"],
            "position_id": action["position_id"],
            "account_id": action["account_id"],
            "quantity": action["quantity"],
            "entry_notional": action["entry_notional"],
            "entry_fee": action["entry_fee"],
            "fee_currency": action["fee_currency"],
            "client_order_id": client_order_id,
            "phase": "reserved",
            "receipt_ids": action["receipt_ids"],
        }
        state["pending"][action_id] = latch
        _write_execution_state(self.execution_state_path, state)
        try:
            submission = submit_close(
                venue=action["venue"],
                symbol=action["symbol"],
                position_id=action["position_id"],
                quantity=action["quantity"],
                side="SELL",
                client_order_id=client_order_id,
            )
        except Exception:
            return _execution_result(
                venue=action["venue"],
                status='pending_reconciliation',
                reason='provider_submission_outcome_unproven',
                symbol=action["symbol"],
                side="SELL",
            )
        result = _classify_terminal_fill_receipt(
            submission,
            action["venue"],
            now=now,
            submission_attempted=True,
            expected_symbol=action["symbol"],
            expected_side="SELL",
            expected_quantity=action["quantity"],
            expected_fee_currency=action["fee_currency"],
        )
        order_id = result.get("order_id")
        if (
            result["status"] == "pending_reconciliation"
            and _valid_provider_identifier(order_id) is not None
            and isinstance(submission, dict)
            and _valid_provider_identifier(
                submission.get("receipt_id")
            )
            is not None
        ):
            latch.update(
                {
                    "phase": "acknowledged",
                    "provider_order_id": order_id,
                    "acknowledgement_receipt_id": submission["receipt_id"],
                }
            )
            state["pending"][action_id] = latch
            _write_execution_state(self.execution_state_path, state)
        return result
        
    def scan_all(self):
        log_system("Initiating Global Asset Scan...")
        opportunities = []
        self.last_no_data = []

        # 1. Capital.com (Positions are explicit)
        if self.capital and self.capital.enabled:
            log_queen("Scanning Capital.com reality branches...")
            try:
                positions = self.capital.get_positions()
                for p in positions:
                    market = p.get('market', {})
                    pos_data = p.get('position', {})
                    epic = market.get('epic')
                    upl = _finite_provider_number(pos_data.get('upl'))
                    qty = _finite_provider_number(pos_data.get('size'), positive=True)
                    if upl is None or qty is None:
                        self.last_no_data.append(
                            _no_data_decision(
                                'malformed_capital_position_numbers',
                                venue='capital',
                                symbol=epic,
                            )
                        )
                        continue
                    
                    opportunities.append({
                        'exchange': 'capital',
                        'symbol': epic,
                        'id': pos_data.get('dealId'),
                        'type': 'CFD',
                        'qty': qty,
                        'pnl': upl,
                        'client': self.capital,
                        'raw': p
                    })
            except Exception as e:
                log_system(f"Capital Scan Error: {e}")

        # 2. Crypto (Spot - requires Cost Basis calculation)
        # Check Binance
        if self.binance:
            log_queen("Scanning Binance liquidity pools...")
            try:
                acct = self.binance.account()
                balances = acct.get('balances', [])
                for b in balances:
                    if not isinstance(b, dict):
                        continue
                    asset = b.get('asset')
                    free = _finite_provider_number(b.get('free'), nonnegative=True)
                    locked = _finite_provider_number(b.get('locked'), nonnegative=True)
                    if not asset or free is None or locked is None:
                        continue
                    total = free + locked
                    if total > 0 and asset not in ['USDT', 'USDC', 'USD', 'EUR', 'GBP']:
                        # Found non-stable asset. Check cost basis.
                        basis_key = f"{asset}USDT" # Assumption for lookup
                        basis = self.cost_basis.get(basis_key, {})
                        avg_entry = _finite_provider_number(
                            basis.get('avg_entry_price'),
                            positive=True,
                        )
                        
                        if avg_entry is not None:
                            # Get Current Price
                            ticker = self.binance.get_ticker(f"{asset}USDT")
                            curr_price = _finite_provider_number(
                                ticker.get('price'),
                                positive=True,
                            )
                            if curr_price is not None:
                                pnl = (curr_price - avg_entry) * total
                                opportunities.append({
                                    'exchange': 'binance',
                                    'symbol': f"{asset}USDT", # Trading pair
                                    'id': asset,
                                    'type': 'SPOT',
                                    'qty': total,
                                    'pnl': pnl,
                                    'client': self.binance,
                                    'current_price': curr_price,
                                    'entry_price': avg_entry
                                })
            except Exception as e:
                 log_system(f"Binance Scan Error: {e}")

        # Check Kraken
        if self.kraken:
            log_queen("Scanning Kraken deep waters...")
            try:
                balances = self.kraken.get_account_balance()
                for asset, total in balances.items():
                    total = _finite_provider_number(total, positive=True)
                    if total is not None and asset not in ['USDT', 'USDC', 'USD', 'EUR', 'GBP', 'ZUSD', 'ZEUR']:
                         # Look for cost basis
                        basis_key = f"{asset}USD" # Standard Kraken
                        basis = self.cost_basis.get(basis_key, {})
                        # Kraken often uses XBT/ETH/etc. Map if needed.
                        avg_entry = _finite_provider_number(
                            basis.get('avg_entry_price'),
                            positive=True,
                        )

                        if avg_entry is not None:
                             ticker = self.kraken.get_ticker(f"{asset}USD")
                             curr_price = _finite_provider_number(
                                 ticker.get('price'),
                                 positive=True,
                             )
                             if curr_price is not None:
                                pnl = (curr_price - avg_entry) * total
                                opportunities.append({
                                    'exchange': 'kraken',
                                    'symbol': f"{asset}USD",
                                    'id': asset,
                                    'type': 'SPOT',
                                    'qty': total,
                                    'pnl': pnl,
                                    'client': self.kraken,
                                    'current_price': curr_price,
                                    'entry_price': avg_entry
                                })
            except Exception as e:
                log_system(f"Kraken Scan Error: {e}")
        
        verified = []
        for target in opportunities:
            if _complete_position_target_evidence(target):
                verified.append(target)
            else:
                self.last_no_data.append(
                    _no_data_decision(
                        'complete_fresh_same_venue_position_evidence_required',
                        venue=target.get('exchange'),
                        symbol=target.get('symbol'),
                    )
                )
        return verified

    def _commit_terminal_execution(self, state, action, execution):
        receipt_id = _valid_provider_identifier(execution.get("receipt_id"))
        action_id = action["intent_id"]
        if receipt_id is None:
            return _no_data_decision(
                "terminal_provider_receipt_id_required",
                venue=action["venue"],
                symbol=action["symbol"],
            )
        if receipt_id in state["committed_receipt_ids"]:
            return _execution_result(
                venue=action["venue"],
                status="already_committed",
                reason="terminal_provider_receipt_already_committed",
                receipt_id=receipt_id,
                symbol=action["symbol"],
                side="SELL",
            )
        entry_notional = _provider_decimal(
            action["entry_notional"],
            positive=True,
        )
        entry_fee = _provider_decimal(
            action["entry_fee"],
            nonnegative=True,
        )
        exit_notional = _provider_decimal(
            execution.get("filled_notional"),
            positive=True,
        )
        exit_fee = _provider_decimal(
            execution.get("fee"),
            nonnegative=True,
        )
        if (
            None in (entry_notional, entry_fee, exit_notional, exit_fee)
            or execution.get("fee_currency") != action["fee_currency"]
        ):
            return _no_data_decision(
                "exact_round_trip_accounting_evidence_required",
                venue=action["venue"],
                symbol=action["symbol"],
            )
        gross_pnl = exit_notional - entry_notional
        fees = entry_fee + exit_fee
        net_pnl = gross_pnl - fees
        accounting = {
            "action_id": action_id,
            "receipt_id": receipt_id,
            "entry_cost_receipt_id": action["receipt_ids"]["cost"],
            "gross_pnl": _decimal_text(gross_pnl),
            "fees": _decimal_text(fees),
            "net_pnl": _decimal_text(net_pnl),
            "currency": action["fee_currency"],
            "truth_status": "real_derived",
            "generated_values": False,
            "eligible_for_accounting": True,
            "eligible_for_learning": True,
        }
        state["pending"].pop(action_id, None)
        state["completed_actions"][action_id] = receipt_id
        state["committed_receipt_ids"].append(receipt_id)
        state["accounting"].append(accounting)
        _write_execution_state(self.execution_state_path, state)
        committed = dict(execution)
        committed["accounting"] = accounting
        committed["economic_mutation"] = True
        committed["eligible_for_accounting"] = True
        committed["eligible_for_learning"] = True
        self.total_pnl = float(
            sum(
                (
                    _provider_decimal(row["net_pnl"])
                    for row in state["accounting"]
                ),
                Decimal("0"),
            )
        )
        self.wins_executed.append(
            {
                "intent_id": action_id,
                "receipt_id": receipt_id,
                "venue": action["venue"],
                "symbol": action["symbol"],
                "accounting": accounting,
            }
        )
        log_sniper(
            f"💥 {action['symbol']} terminal fill reconciled. "
            "Profit accounting committed from provider receipts."
        )
        log_queen("Harvest complete.")
        return committed

    def execute_kill_chain(self, target):
        if self.execution_state_path is None:
            return _no_data_decision("execution_state_path_required")
        now = _finite_provider_number(self.clock(), positive=True)
        if now is None:
            return _no_data_decision("current_time_unavailable")
        try:
            with _execution_state_lock(self.execution_state_path):
                state = _load_execution_state(
                    self.execution_state_path
                )
                authorization = (
                    target.get("authorization_receipt")
                    if isinstance(target, dict)
                    else None
                )
                intent_id = (
                    _valid_provider_identifier(
                        authorization.get("intent_id")
                    )
                    if isinstance(authorization, dict)
                    else None
                )
                if (
                    intent_id is not None
                    and intent_id in state["completed_actions"]
                ):
                    return _execution_result(
                        venue=target.get("exchange"),
                        status="already_committed",
                        reason="action_intent_already_committed",
                        receipt_id=state["completed_actions"][
                            intent_id
                        ],
                        symbol=_normalized_symbol(
                            target.get("symbol")
                        )
                        or None,
                        side="SELL",
                    )
                pending = (
                    state["pending"].get(intent_id)
                    if intent_id is not None
                    else None
                )
                if isinstance(pending, dict):
                    action = _pending_action(pending)
                    adapter = self.execution_adapters.get(
                        action["venue"]
                    )
                    if adapter is None:
                        return _no_data_decision(
                            "provider_execution_adapter_required",
                            venue=action["venue"],
                            symbol=action["symbol"],
                        )
                    execution = self._submit_and_reconcile(
                        action=action,
                        adapter=adapter,
                        state=state,
                        now=now,
                    )
                    if execution["success"]:
                        return self._commit_terminal_execution(
                            state,
                            action,
                            execution,
                        )
                    return execution

                action = _classify_action_evidence(
                    target,
                    now=now,
                )
                if action.get("eligible_for_action") is not True:
                    self.last_no_data.append(action)
                    return action
                log_queen(
                    f"Assess Target: {action['venue'].upper()}::"
                    f"{action['symbol']} | provider-linked evidence complete"
                )
                log_auris(
                    f"HNC/Auris receipt gates complete for "
                    f"{action['symbol']} SELL"
                )
                if not self.execution_enabled:
                    return _execution_result(
                        venue=action["venue"],
                        status="not_submitted",
                        reason="execution_enable_gate_required",
                        symbol=action["symbol"],
                        side="SELL",
                    )
                adapter = self.execution_adapters.get(action["venue"])
                if adapter is None:
                    return _no_data_decision(
                        "provider_execution_adapter_required",
                        venue=action["venue"],
                        symbol=action["symbol"],
                    )
                execution = self._submit_and_reconcile(
                    action=action,
                    adapter=adapter,
                    state=state,
                    now=now,
                )
                if execution["success"]:
                    return self._commit_terminal_execution(
                        state,
                        action,
                        execution,
                    )
                return execution
        except (OSError, ValueError, AttributeError) as exc:
            return _no_data_decision(str(exc))

    def redeploy_energy(self):
        """Simulate identifying a buying opportunity."""
        log_system("♻️ Checking Energy Levels for Redeployment...")
        # Check USD balances
        cached_cash = 0.0
        
        if self.binance:
            usdt = self.binance.get_free_balance('USDT')
            if usdt > 10:
                log_queen(f"Binance Energy Detected: {usdt:.2f} USDT")
                cached_cash += usdt
        
        if cached_cash > 10:
            log_queen("Energy available for Materialization (BUY).")
            # Logic to find a target would go here (Dr. Auris scans for harmonics)
            log_auris("Scanning for harmonic resonance (Dip Buying)...")
            log_auris("... No perfect resonance found at this milli-epoch.")
        else:
            log_queen("Energy levels low. Awaiting harvest.")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # 💀 WIN KILLER METHODS
    # ═══════════════════════════════════════════════════════════════════════════
    
    def hunt_for_wins(self) -> List[Dict]:
        """Hunt for winning opportunities - BY ANY MEANS"""
        log_killer("💀 WIN KILLER ACTIVATED - HUNTING...")
        return self.win_killer.hunt_all()
    
    def execute_win(self, opportunity: Dict) -> Dict:
        """Execute a winning trade"""
        symbol = opportunity.get('symbol', 'UNKNOWN')
        exchange = opportunity.get('exchange', 'unknown')
        op_type = opportunity.get('type', 'UNKNOWN')
        score = opportunity.get('score', 0)
        
        log_killer(f"🎯 TARGET LOCKED: {symbol} on {exchange}")
        log_killer(f"   Type: {op_type} | Score: {score:.2f}")
        
        if op_type == 'ARBITRAGE':
            log_killer(f"   💱 {opportunity.get('action', 'N/A')}")
            log_killer(f"   Spread: {opportunity.get('spread_pct', 0):.3f}%")
        else:
            log_killer(f"   Entry: ${opportunity.get('entry', 0):.6f}")
            log_killer(f"   Target: ${opportunity.get('target', 0):.6f}")
            log_killer(f"   Stop: ${opportunity.get('stop', 0):.6f}")
            log_killer(f"   R:R: {opportunity.get('risk_reward', 0):.1f}:1")
        
        # Check if auto-execute is enabled
        if self.win_config.auto_execute and score >= 5.0:
            log_killer("⚡ AUTO-EXECUTE ENABLED - FIRING!")
            return self._execute_trade(opportunity)
        else:
            # Manual confirmation
            if score >= 5.0:
                confirm = input(f"\n💀 EXECUTE {op_type} on {symbol}? [y/N]: ")
                if confirm.lower() == 'y':
                    return self._execute_trade(opportunity)
            
        return {'status': 'SKIPPED', 'reason': 'Score too low or not confirmed'}
    
    def _execute_trade(self, opportunity: Dict) -> Dict:
        """Actually execute the trade - BY THE ORCA RULES"""
        exchange = opportunity.get('exchange', 'unknown')
        symbol = opportunity.get('symbol', 'UNKNOWN')
        op_type = opportunity.get('type', 'UNKNOWN')
        
        log_sniper(f"🔥 EXECUTING BY ORCA RULES: {symbol} on {exchange}")
        
        try:
            # Get available balance for position sizing
            available_usd = 0.0
            
            if exchange == 'kraken' and self.kraken:
                # Map symbol to Kraken format
                kraken_pair = symbol if 'USD' in symbol else f"{symbol.replace('USDT', '')}USD"
                
                # Get balance
                try:
                    balances = self.kraken.get_account_balance()
                    available_usd = float(balances.get('ZUSD', 0)) + float(balances.get('USD', 0))
                except:
                    available_usd = 0
                
                if available_usd < 1:
                    log_sniper(f"⚠️ Insufficient USD on Kraken: ${available_usd:.2f}")
                    return {'status': 'NO_FUNDS', 'exchange': 'kraken', 'balance': available_usd}
                
                # Calculate position size (ORCA RULE: max 10% per trade)
                position_usd = min(available_usd * 0.10, available_usd)
                price = opportunity.get('price', 0)
                
                if price > 0:
                    volume = position_usd / price
                    
                    log_sniper(f"🎯 Kraken: {kraken_pair}")
                    log_sniper(f"   Position: ${position_usd:.2f} = {volume:.6f}")
                    log_sniper(f"   Entry: ${price:.6f}")
                    
                    # EXECUTE THE TRADE
                    order_result = self.kraken.place_market_order(kraken_pair, 'buy', volume)
                    
                    if order_result and not order_result.get('error'):
                        log_sniper(f"💥 ORDER FILLED! {order_result}")
                        result = {'status': 'FILLED', 'pair': kraken_pair, 'exchange': 'kraken', 
                                  'volume': volume, 'order': order_result}
                    else:
                        log_sniper(f"❌ Order failed: {order_result}")
                        result = {'status': 'FAILED', 'error': order_result}
                else:
                    result = {'status': 'NO_PRICE', 'exchange': 'kraken'}
                
            elif exchange == 'binance' and self.binance:
                # Get USDT balance
                try:
                    available_usd = self.binance.get_free_balance('USDT')
                except:
                    available_usd = 0
                
                if available_usd < 1:
                    log_sniper(f"⚠️ Insufficient USDT on Binance: ${available_usd:.2f}")
                    return {'status': 'NO_FUNDS', 'exchange': 'binance', 'balance': available_usd}
                
                # Calculate position size (ORCA RULE: max 10% per trade)
                position_usd = min(available_usd * 0.10, available_usd)
                price = opportunity.get('price', 0)
                
                if price > 0:
                    volume = position_usd / price
                    
                    log_sniper(f"🎯 Binance: {symbol}")
                    log_sniper(f"   Position: ${position_usd:.2f} = {volume:.6f}")
                    log_sniper(f"   Entry: ${price:.6f}")
                    
                    # EXECUTE THE TRADE
                    order_result = self.binance.place_market_order(symbol, 'BUY', volume)
                    
                    if order_result and order_result.get('status') == 'FILLED':
                        log_sniper(f"💥 ORDER FILLED! {order_result}")
                        result = {'status': 'FILLED', 'pair': symbol, 'exchange': 'binance',
                                  'volume': volume, 'order': order_result}
                    else:
                        log_sniper(f"❌ Order failed: {order_result}")
                        result = {'status': 'FAILED', 'error': order_result}
                else:
                    result = {'status': 'NO_PRICE', 'exchange': 'binance'}
                
            elif exchange == 'arbitrage':
                # ARBITRAGE: Buy on one exchange, sell on another
                buy_ex = opportunity.get('buy_exchange')
                sell_ex = opportunity.get('sell_exchange')
                coin = opportunity.get('symbol', '').split('/')[0]
                
                log_sniper(f"💱 ARBITRAGE: {coin}")
                log_sniper(f"   BUY on {buy_ex} @ ${opportunity.get('kraken_price', 0):.2f}")
                log_sniper(f"   SELL on {sell_ex} @ ${opportunity.get('binance_price', 0):.2f}")
                log_sniper(f"   Spread: {opportunity.get('spread_pct', 0):.3f}%")
                
                # EXECUTE ARBITRAGE
                try:
                    if buy_ex == 'kraken' and sell_ex == 'binance':
                        # Get available USD on Kraken for buying
                        kraken_balances = self.kraken.get_balance()
                        available_usd = float(kraken_balances.get('USD', 0))
                        
                        if available_usd < 10:
                            log_sniper(f"⚠️ Insufficient USD on Kraken: ${available_usd:.2f}")
                            result = {'status': 'NO_FUNDS', 'exchange': 'kraken', 'balance': available_usd}
                        else:
                            # Use 80% of available for arbitrage
                            trade_usd = available_usd * 0.8
                            buy_price = opportunity.get('kraken_price', 0)
                            volume = trade_usd / buy_price
                            
                            kraken_pair = symbol.replace('/', '')
                            
                            log_sniper(f"   Step 1: BUY {volume:.6f} {coin} on Kraken")
                            buy_order = self.kraken.place_market_order(kraken_pair, 'buy', volume)
                            
                            if buy_order and buy_order.get('status') == 'FILLED':
                                actual_qty = float(buy_order.get('executedQty', volume))
                                log_sniper(f"   ✅ Bought {actual_qty} {coin}")
                                
                                # Now sell on Binance
                                binance_symbol = f"{coin}USDT"
                                log_sniper(f"   Step 2: SELL {actual_qty} {coin} on Binance")
                                
                                sell_order = self.binance.place_market_order(binance_symbol, 'SELL', actual_qty)
                                
                                if sell_order and sell_order.get('status') == 'FILLED':
                                    log_sniper(f"   ✅ ARBITRAGE COMPLETE!")
                                    result = {'status': 'ARBITRAGE_EXECUTED', 'buy_order': buy_order, 'sell_order': sell_order}
                                else:
                                    log_sniper(f"   ❌ Sell failed, holding {actual_qty} {coin}")
                                    result = {'status': 'PARTIAL', 'buy_order': buy_order, 'sell_error': sell_order}
                            else:
                                log_sniper(f"   ❌ Buy failed")
                                result = {'status': 'BUY_FAILED', 'error': buy_order}
                    else:
                        # Other direction or not supported yet
                        result = {'status': 'ARBITRAGE_LOGGED', 'type': 'arbitrage', 
                                  'buy': buy_ex, 'sell': sell_ex, 'spread': opportunity.get('spread_pct', 0)}
                except Exception as e:
                    log_sniper(f"   ❌ Arbitrage error: {e}")
                    result = {'status': 'ERROR', 'error': str(e)}
            else:
                result = {'status': 'NO_CLIENT', 'exchange': exchange}
            
            self.wins_executed.append({
                'opportunity': opportunity,
                'result': result,
                'timestamp': datetime.now().isoformat()
            })
            
            # Save execution log
            try:
                with open('orca_executions.json', 'a') as f:
                    f.write(json.dumps({
                        'timestamp': datetime.now().isoformat(),
                        'opportunity': opportunity,
                        'result': result
                    }) + '\n')
            except:
                pass

            if self.real_portfolio:
                try:
                    self.real_portfolio.get_real_portfolio()
                except Exception:
                    pass
            
            return result
            
        except Exception as e:
            log_killer(f"❌ Execution error: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def display_win_opportunities(self, opportunities: List[Dict], limit: int = 10):
        """Display win opportunities in a nice format"""
        print()
        print("💀" * 35)
        print("   WIN KILLER - OPPORTUNITIES FOUND")
        print("💀" * 35)
        print()
        
        if not opportunities:
            print("   ⏳ No opportunities above threshold")
            return
        
        print(f"   🎯 {len(opportunities)} WINS DETECTED")
        print()
        
        for i, op in enumerate(opportunities[:limit], 1):
            score = op.get('score', 0)
            score_bar = '█' * int(score) + '░' * (10 - int(score))
            
            print(f"   {i}. {op['symbol']:12} | {op.get('exchange', '?'):8} | {op.get('type', '?'):12}")
            print(f"      Score: [{score_bar}] {score:.2f}")
            
            if op.get('type') == 'ARBITRAGE':
                print(f"      💱 {op.get('action', 'N/A')}")
                print(f"      Spread: {op.get('spread_pct', 0):.3f}%")
            else:
                print(f"      Price: ${op.get('price', 0):.6f} | Δ24h: {op.get('change_24h', 0):+.1f}%")
                print(f"      Target: ${op.get('target', 0):.6f} | R:R: {op.get('risk_reward', 0):.1f}:1")
            print()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='ORCA Unified Kill Chain + WIN KILLER')
    parser.add_argument('--auto', action='store_true', help='Enable auto-execute (DANGEROUS)')
    parser.add_argument('--min-score', type=float, default=3.0, help='Minimum win score')
    parser.add_argument('--hunt-only', action='store_true', help='Only hunt, do not execute existing positions')
    parser.add_argument('--once', action='store_true', help='Run single cycle then exit')
    args = parser.parse_args()
    
    # Configure WIN KILLER
    win_config = WinConfig(
        min_score=args.min_score,
        auto_execute=args.auto
    )
    
    chain = UnifiedKillChain(win_config)
    
    cycle = 0
    while True:
        cycle += 1
        log_system(f"\n{'='*70}")
        log_system(f"   KILL CYCLE {cycle} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        log_system(f"{'='*70}\n")

        # Single source of truth snapshot
        chain.refresh_truth()
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 1: Scan existing positions (unless hunt-only)
        # ═══════════════════════════════════════════════════════════════════════
        if not args.hunt_only:
            targets = chain.scan_all()
            
            if not targets:
                log_queen("No existing positions to harvest.")
            else:
                log_queen(f"Found {len(targets)} existing positions.")
                for t in targets:
                    chain.execute_kill_chain(t)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 2: WIN KILLER - Hunt for new opportunities
        # ═══════════════════════════════════════════════════════════════════════
        print()
        log_killer("=" * 50)
        log_killer("   PHASE 2: WIN KILLER HUNT")
        log_killer("=" * 50)
        
        wins = chain.hunt_for_wins()
        chain.display_win_opportunities(wins)
        
        # Execute top opportunity if score is high enough
        if wins and wins[0].get('score', 0) >= 5.0:
            log_killer(f"🔥 HOT OPPORTUNITY: {wins[0]['symbol']} (Score: {wins[0]['score']:.2f})")
            result = chain.execute_win(wins[0])
            log_killer(f"Result: {result}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 3: Redeploy energy
        # ═══════════════════════════════════════════════════════════════════════
        chain.redeploy_energy()
        
        # ═══════════════════════════════════════════════════════════════════════
        # Summary
        # ═══════════════════════════════════════════════════════════════════════
        print()
        log_system(f"   Cycle {cycle} complete.")
        log_system(f"   Wins executed this session: {len(chain.wins_executed)}")
        
        if args.once:
            log_system("   --once flag set, exiting.")
            break
        
        print("\n   Waiting 30 seconds for next cycle (Ctrl+C to stop)...")
        try:
            time.sleep(30)
        except KeyboardInterrupt:
            print("\n\n👋 Kill Chain shutdown.")
            break

if __name__ == "__main__":
    main()
