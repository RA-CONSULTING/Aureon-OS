#!/usr/bin/env python3
"""Receipt-gated limit-profit lifecycle.

Importing this module and running its CLI are inert. The composition root must
inject an order adapter and fresh authorization, position, account, quote, and
fee receipts. Each invocation submits at most one order or performs at most one
status read-back. Only an exact, fresh terminal provider fill may change the
durable lifecycle or create accounting and learning evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol


MAX_AGE_SECONDS = 300.0
FUTURE_SKEW_SECONDS = 5.0
STATE_SCHEMA_VERSION = 1
REAL_TRUTH = {"real_observed", "real_provider", "real_operator"}
INVALID_IDS = {"", "0", "none", "null", "unknown", "n/a", "na"}


class LimitOrderAdapter(Protocol):
    """The explicit adapter boundary; client construction remains external."""

    def submit_limit_order(
        self,
        *,
        symbol: str,
        side: str,
        quantity: str,
        limit_price: str,
        client_order_id: str,
    ) -> Mapping[str, Any]: ...

    def read_order_receipt(
        self,
        *,
        symbol: str,
        provider_order_id: str,
    ) -> Mapping[str, Any]: ...


class EvidenceError(ValueError):
    pass


class StateError(RuntimeError):
    pass


def _first(row: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in row:
            return row[name]
    return None


def _id(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    text = str(value).strip()
    return None if text.lower() in INVALID_IDS else text


def _name(value: Any, field: str) -> str:
    text = "".join(char for char in str(value or "").upper() if char.isalnum())
    if not text:
        raise EvidenceError(f"{field}_required")
    return text


def _venue(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        raise EvidenceError("venue_required")
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


def _text(value: Decimal) -> str:
    rendered = format(value.normalize(), "f")
    return "0" if rendered in {"", "-0"} else rendered


def _timestamp(value: Any, field: str) -> float:
    if value is None or isinstance(value, bool):
        raise EvidenceError(f"{field}_required")
    if isinstance(value, (int, float, Decimal)):
        result = float(value)
    elif isinstance(value, str):
        try:
            result = float(value.strip())
        except ValueError:
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
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
    receipt_id = _id(receipt.get("receipt_id"))
    if receipt_id is None:
        raise EvidenceError(f"{kind}_receipt_id_required")
    if str(receipt.get("data_status") or "").lower() != "live":
        raise EvidenceError(f"{kind}_live_receipt_required")
    accepted_truths = REAL_TRUTH if truths is None else truths
    if str(receipt.get("truth_status") or "").lower() not in accepted_truths:
        raise EvidenceError(f"{kind}_real_truth_required")
    if receipt.get("generated_values") is not False:
        raise EvidenceError(f"{kind}_generated_values_forbidden")
    if receipt.get("eligible_for_action") is not True:
        raise EvidenceError(f"{kind}_action_eligibility_required")
    if _venue(_first(receipt, ("venue", "exchange", "provider"))) != venue:
        raise EvidenceError(f"{kind}_venue_mismatch")
    if _name(receipt.get("symbol"), "symbol") != symbol:
        raise EvidenceError(f"{kind}_symbol_mismatch")
    if _id(receipt.get("account_id")) != account_id:
        raise EvidenceError(f"{kind}_account_mismatch")
    source_time = _timestamp(
        _first(receipt, ("provider_timestamp", "source_timestamp")),
        f"{kind}_provider_timestamp",
    )
    received_at = _timestamp(receipt.get("received_at"), f"{kind}_received_at")
    if (
        source_time < now - MAX_AGE_SECONDS
        or source_time > now + FUTURE_SKEW_SECONDS
        or received_at < now - MAX_AGE_SECONDS
        or received_at > now + FUTURE_SKEW_SECONDS
        or source_time > received_at + FUTURE_SKEW_SECONDS
    ):
        raise EvidenceError(f"{kind}_fresh_provider_evidence_required")
    return receipt_id


def _authorize(receipt: Any, now: float) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise EvidenceError("authorization_receipt_required")
    venue = _venue(_first(receipt, ("venue", "exchange", "provider")))
    symbol = _name(receipt.get("symbol"), "symbol")
    account_id = _id(receipt.get("account_id"))
    if account_id is None:
        raise EvidenceError("authorization_account_id_required")
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
    authorization_id = _id(receipt.get("authorization_id"))
    cycle_id = _id(receipt.get("cycle_id"))
    intent_id = _id(receipt.get("intent_id"))
    if authorization_id is None or cycle_id is None or intent_id is None:
        raise EvidenceError("authorization_cycle_and_intent_ids_required")
    side = str(receipt.get("side") or "").strip().upper()
    if side not in {"BUY", "SELL"}:
        raise EvidenceError("authorized_side_required")
    if _timestamp(receipt.get("expires_at"), "authorization_expires_at") <= now:
        raise EvidenceError("authorization_expired")
    return {
        "receipt_id": receipt_id,
        "authorization_id": authorization_id,
        "cycle_id": cycle_id,
        "intent_id": intent_id,
        "venue": venue,
        "symbol": symbol,
        "account_id": account_id,
        "side": side,
        "quantity": _number(receipt.get("quantity"), "authorized_quantity", positive=True),
        "limit_price": _number(receipt.get("limit_price"), "authorized_limit_price", positive=True),
        "max_notional": _number(receipt.get("max_notional"), "authorized_max_notional", positive=True),
        "minimum_net_profit_rate": _number(
            receipt.get("minimum_net_profit_rate"),
            "authorized_minimum_net_profit_rate",
            nonnegative=True,
        ),
    }


def _preflight(
    *,
    authorization_receipt: Any,
    position_receipt: Any,
    account_receipt: Any,
    quote_receipt: Any,
    fee_receipt: Any,
    amount_quote: Any,
    entry_fill: Mapping[str, Any] | None,
    now: float,
) -> dict[str, Any]:
    auth = _authorize(authorization_receipt, now)
    common = {
        "venue": auth["venue"],
        "symbol": auth["symbol"],
        "account_id": auth["account_id"],
        "now": now,
    }
    receipt_ids = {"authorization": auth["receipt_id"]}
    receipt_ids["position"] = _header(position_receipt, "position", **common)
    receipt_ids["account"] = _header(account_receipt, "account", **common)
    receipt_ids["quote"] = _header(quote_receipt, "quote", **common)
    receipt_ids["fee"] = _header(fee_receipt, "fee", **common)
    base_asset = _name(quote_receipt.get("base_asset"), "quote_base_asset")
    quote_asset = _name(quote_receipt.get("quote_asset"), "quote_asset")
    if _name(position_receipt.get("base_asset"), "position_base_asset") != base_asset:
        raise EvidenceError("position_base_asset_mismatch")
    position_quantity = _number(
        _first(position_receipt, ("position_quantity", "quantity")),
        "position_quantity",
        nonnegative=True,
    )
    account_asset = _name(account_receipt.get("asset"), "account_asset")
    available = _number(
        _first(account_receipt, ("available_balance", "available", "free")),
        "account_available_balance",
        nonnegative=True,
    )
    bid = _number(
        _first(quote_receipt, ("bid_price", "bidPrice", "bid")),
        "quote_bid",
        positive=True,
    )
    ask = _number(
        _first(quote_receipt, ("ask_price", "askPrice", "ask")),
        "quote_ask",
        positive=True,
    )
    if bid > ask:
        raise EvidenceError("quote_bid_exceeds_ask")
    fee_rate = _number(
        _first(fee_receipt, ("maker_fee_rate", "fee_rate")),
        "maker_fee_rate",
        nonnegative=True,
    )
    if fee_rate >= 1:
        raise EvidenceError("maker_fee_rate_must_be_less_than_one")
    if _name(fee_receipt.get("fee_currency"), "fee_currency") != quote_asset:
        raise EvidenceError("fee_currency_must_match_quote_asset")
    quantity = auth["quantity"]
    limit_price = auth["limit_price"]
    order_notional = quantity * limit_price
    if order_notional > auth["max_notional"]:
        raise EvidenceError("authorized_max_notional_exceeded")
    if auth["side"] == "BUY":
        if entry_fill is not None:
            raise EvidenceError("sell_authorization_required_after_entry_fill")
        if order_notional > _number(amount_quote, "amount_quote", positive=True):
            raise EvidenceError("quote_budget_exceeded")
        if limit_price != bid:
            raise EvidenceError("authorized_buy_limit_must_equal_observed_bid")
        required_balance = order_notional * (Decimal("1") + fee_rate)
        if account_asset != quote_asset or available < required_balance:
            raise EvidenceError("fresh_quote_balance_insufficient")
        target = (
            limit_price
            * (Decimal("1") + fee_rate + auth["minimum_net_profit_rate"])
            / (Decimal("1") - fee_rate)
        )
    else:
        if not isinstance(entry_fill, Mapping):
            raise EvidenceError("terminal_entry_fill_required_before_sell")
        entry_qty = _number(entry_fill.get("filled_qty"), "entry_filled_qty", positive=True)
        entry_notional = _number(
            entry_fill.get("filled_notional"),
            "entry_notional",
            positive=True,
        )
        entry_fee = _number(entry_fill.get("fee"), "entry_fee", nonnegative=True)
        if quantity != entry_qty:
            raise EvidenceError("sell_quantity_must_equal_terminal_entry_quantity")
        if _name(entry_fill.get("fee_currency"), "entry_fee_currency") != quote_asset:
            raise EvidenceError("entry_fee_currency_must_match_quote_asset")
        if position_quantity < quantity or account_asset != base_asset or available < quantity:
            raise EvidenceError("fresh_position_and_base_balance_insufficient")
        desired_profit = entry_notional * auth["minimum_net_profit_rate"]
        target = (
            (entry_notional + entry_fee + desired_profit)
            / (Decimal("1") - fee_rate)
            / quantity
        )
        if limit_price < target:
            raise EvidenceError("sell_limit_below_fee_complete_profit_target")
    return {
        **auth,
        "base_asset": base_asset,
        "quote_asset": quote_asset,
        "fee_rate": fee_rate,
        "order_notional": order_notional,
        "target_exit_price": target,
        "evidence_receipt_ids": receipt_ids,
    }


def _terminal_fill(
    receipt: Any,
    *,
    preflight: Mapping[str, Any],
    expected_order_id: str | None,
    now: float,
) -> dict[str, Any]:
    if not isinstance(receipt, Mapping):
        raise EvidenceError("provider_receipt_required")
    if receipt.get("dryRun") is True or receipt.get("dry_run") is True:
        raise EvidenceError("dry_run_is_not_provider_fill")
    if str(_first(receipt, ("provider_status", "status")) or "").upper() != "FILLED":
        raise EvidenceError("terminal_filled_provider_status_required")
    if (
        str(receipt.get("data_status") or "").lower() != "live"
        or str(receipt.get("truth_status") or "").lower()
        not in {"real_observed", "real_provider"}
        or receipt.get("generated_values") is not False
        or receipt.get("fill_receipt_complete") is not True
        or receipt.get("eligible_for_action") is not False
        or receipt.get("eligible_for_accounting") is not True
        or receipt.get("eligible_for_learning") is not True
        or receipt.get("reconciliation_required") is not False
    ):
        raise EvidenceError("complete_action_safe_terminal_fill_required")
    if (
        _venue(_first(receipt, ("venue", "exchange", "provider"))) != preflight["venue"]
        or _name(receipt.get("symbol"), "symbol") != preflight["symbol"]
        or str(receipt.get("side") or "").upper() != preflight["side"]
    ):
        raise EvidenceError("terminal_venue_symbol_or_side_mismatch")
    order_id = _id(_first(receipt, ("provider_order_id", "orderId", "order_id")))
    if order_id is None or (
        expected_order_id is not None and order_id != expected_order_id
    ):
        raise EvidenceError("terminal_provider_order_id_mismatch")
    receipt_id = _id(receipt.get("receipt_id"))
    receipt_type = _id(receipt.get("provider_receipt_type"))
    if receipt_id is None or receipt_type is None:
        raise EvidenceError("terminal_provider_receipt_identity_required")
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
    fee_currency = _name(
        _first(receipt, ("fee_currency", "fee_asset")),
        "terminal_fee_currency",
    )
    if quantity != preflight["quantity"] or fee_currency != preflight["quote_asset"]:
        raise EvidenceError("terminal_quantity_or_fee_currency_mismatch")
    raw_fills = receipt.get("fills")
    if not isinstance(raw_fills, list) or not raw_fills:
        raise EvidenceError("provider_fill_rows_required")
    trade_ids: list[str] = []
    sum_quantity = Decimal("0")
    sum_notional = Decimal("0")
    sum_fee = Decimal("0")
    for row in raw_fills:
        if not isinstance(row, Mapping):
            raise EvidenceError("provider_fill_row_invalid")
        trade_id = _id(_first(row, ("tradeId", "trade_id", "id")))
        if trade_id is None or trade_id in trade_ids:
            raise EvidenceError("unique_provider_trade_ids_required")
        row_quantity = _number(
            _first(row, ("qty", "quantity")),
            "provider_trade_quantity",
            positive=True,
        )
        row_price = _number(row.get("price"), "provider_trade_price", positive=True)
        row_fee = _number(
            _first(row, ("commission", "fee", "fee_amount")),
            "provider_trade_fee",
            nonnegative=True,
        )
        row_currency = _name(
            _first(row, ("commissionAsset", "fee_currency", "fee_asset")),
            "provider_trade_fee_currency",
        )
        row_time = _timestamp(
            _first(row, ("provider_timestamp", "source_timestamp", "time")),
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
        or price * quantity != notional
    ):
        raise EvidenceError("exact_provider_fill_totals_required")
    provider_time = _timestamp(
        _first(receipt, ("provider_timestamp", "source_timestamp")),
        "terminal_provider_timestamp",
    )
    received_at = _timestamp(receipt.get("received_at"), "terminal_received_at")
    if (
        provider_time < now - MAX_AGE_SECONDS
        or provider_time > now + FUTURE_SKEW_SECONDS
        or received_at < now - MAX_AGE_SECONDS
        or received_at > now + FUTURE_SKEW_SECONDS
        or provider_time > received_at + FUTURE_SKEW_SECONDS
    ):
        raise EvidenceError("fresh_terminal_provider_fill_required")
    return {
        "receipt_id": receipt_id,
        "provider_receipt_type": receipt_type,
        "provider_order_id": order_id,
        "trade_ids": trade_ids,
        "venue": preflight["venue"],
        "symbol": preflight["symbol"],
        "side": preflight["side"],
        "filled_qty": _text(quantity),
        "filled_notional": _text(notional),
        "filled_avg_price": _text(price),
        "fee": _text(fee),
        "fee_currency": fee_currency,
        "provider_timestamp": provider_time,
        "truth_status": "real_provider",
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
    }


def _result(status: str, reason: str, **extra: Any) -> dict[str, Any]:
    eligible = status == "filled"
    return {
        "status": status,
        "data_status": "live" if eligible else status,
        "truth_status": "real_provider" if eligible else "no_data",
        "reason": reason,
        "mutated": False,
        "accounting_committed": False,
        "eligible_for_action": False,
        "eligible_for_accounting": eligible,
        "eligible_for_learning": eligible,
        "generated_values": False,
        **extra,
    }


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": STATE_SCHEMA_VERSION, "cycles": {}}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StateError("durable_state_unreadable") from exc
    if (
        not isinstance(state, dict)
        or state.get("schema_version") != STATE_SCHEMA_VERSION
        or not isinstance(state.get("cycles"), dict)
    ):
        raise StateError("durable_state_schema_invalid")
    return state


def _save(path: Path, state: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.pending")
    with pending.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(state, handle, indent=2, sort_keys=True, ensure_ascii=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(pending, path)


@contextmanager
def _state_lock(path: Path) -> Iterator[None]:
    """Serialize the load-submit-latch transaction across local processes."""

    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    handle = lock_path.open("a+b")
    acquired = False
    try:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise StateError("durable_state_busy") from exc
        else:
            import fcntl

            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise StateError("durable_state_busy") from exc
        acquired = True
        yield
    finally:
        if acquired:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def _new_cycle(preflight: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "cycle_id": preflight["cycle_id"],
        "venue": preflight["venue"],
        "symbol": preflight["symbol"],
        "account_id": preflight["account_id"],
        "base_asset": preflight["base_asset"],
        "quote_asset": preflight["quote_asset"],
        "phase": "awaiting_entry_fill",
        "entry_fill": None,
        "exit_fill": None,
        "unresolved": None,
        "committed_receipt_ids": [],
        "accounting": None,
    }


def _commit(
    path: Path,
    state: dict[str, Any],
    cycle: dict[str, Any],
    fill: Mapping[str, Any],
) -> dict[str, Any]:
    committed = cycle.get("committed_receipt_ids")
    if not isinstance(committed, list):
        raise StateError("durable_committed_receipts_invalid")
    if fill["receipt_id"] in committed:
        return _result("already_committed", "terminal_fill_already_committed")
    if fill["side"] == "BUY":
        if cycle.get("entry_fill") is not None:
            raise StateError("duplicate_entry_fill_conflict")
        cycle["entry_fill"] = dict(fill)
        cycle["phase"] = "entry_filled"
        cycle["unresolved"] = None
        committed.append(fill["receipt_id"])
        _save(path, state)
        outcome = _result(
            "filled",
            "terminal_entry_fill_committed",
            receipt_id=fill["receipt_id"],
            provider_order_id=fill["provider_order_id"],
        )
        outcome["mutated"] = True
        return outcome
    entry = cycle.get("entry_fill")
    if not isinstance(entry, Mapping):
        raise StateError("terminal_entry_fill_missing")
    if entry.get("filled_qty") != fill.get("filled_qty"):
        raise StateError("terminal_exit_quantity_conflict")
    entry_notional = _number(
        entry.get("filled_notional"),
        "entry_notional",
        positive=True,
    )
    exit_notional = _number(
        fill.get("filled_notional"),
        "exit_notional",
        positive=True,
    )
    entry_fee = _number(entry.get("fee"), "entry_fee", nonnegative=True)
    exit_fee = _number(fill.get("fee"), "exit_fee", nonnegative=True)
    if entry.get("fee_currency") != fill.get("fee_currency"):
        raise StateError("terminal_fee_currency_conflict")
    gross_pnl = exit_notional - entry_notional
    fees = entry_fee + exit_fee
    net_pnl = gross_pnl - fees
    accounting = {
        "currency": fill["fee_currency"],
        "entry_receipt_id": entry["receipt_id"],
        "exit_receipt_id": fill["receipt_id"],
        "entry_notional": _text(entry_notional),
        "exit_notional": _text(exit_notional),
        "gross_pnl": _text(gross_pnl),
        "fees": _text(fees),
        "net_pnl": _text(net_pnl),
        "generated_values": False,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
    }
    cycle["exit_fill"] = dict(fill)
    cycle["accounting"] = accounting
    cycle["phase"] = "complete"
    cycle["unresolved"] = None
    committed.append(fill["receipt_id"])
    _save(path, state)
    outcome = _result(
        "filled",
        "terminal_round_trip_fill_accounted",
        **accounting,
    )
    outcome["mutated"] = True
    outcome["accounting_committed"] = True
    return outcome


def _ack_id(receipt: Any, preflight: Mapping[str, Any]) -> str | None:
    if not isinstance(receipt, Mapping):
        return None
    try:
        coherent = (
            _venue(_first(receipt, ("venue", "exchange", "provider")))
            == preflight["venue"]
            and _name(receipt.get("symbol"), "symbol") == preflight["symbol"]
            and str(receipt.get("side") or "").upper() == preflight["side"]
        )
    except EvidenceError:
        return None
    if not coherent:
        return None
    return _id(_first(receipt, ("provider_order_id", "orderId", "order_id")))


def _not_submitted(receipt: Any) -> bool:
    return isinstance(receipt, Mapping) and (
        receipt.get("dryRun") is True
        or receipt.get("dry_run") is True
        or receipt.get("submitted") is False
        or str(receipt.get("status") or "").lower() == "not_submitted"
    )


def _execute_profit_trade_unlocked(
    client: LimitOrderAdapter,
    symbol: str,
    amount_quote: Any,
    *,
    authorization_receipt: Mapping[str, Any],
    position_receipt: Mapping[str, Any],
    account_receipt: Mapping[str, Any],
    quote_receipt: Mapping[str, Any],
    fee_receipt: Mapping[str, Any],
    state_path: str | Path,
    now: float | None = None,
) -> dict[str, Any]:
    """Advance one phase; never poll, sleep, cancel, or submit a fallback order."""

    clock = time.time() if now is None else float(now)
    if not math.isfinite(clock) or clock <= 0:
        return _result("no_data", "valid_comparison_clock_required")
    try:
        requested_symbol = _name(symbol, "symbol")
        path = Path(state_path).expanduser().resolve()
        state = _load(path)
        auth = _authorize(authorization_receipt, clock)
        if auth["symbol"] != requested_symbol:
            return _result(
                "no_data",
                "requested_symbol_and_authorization_mismatch",
            )
        cycle = state["cycles"].get(auth["cycle_id"])
        if cycle is not None and not isinstance(cycle, dict):
            raise StateError("durable_cycle_state_invalid")
        entry_fill = cycle.get("entry_fill") if isinstance(cycle, dict) else None
        preflight = _preflight(
            authorization_receipt=authorization_receipt,
            position_receipt=position_receipt,
            account_receipt=account_receipt,
            quote_receipt=quote_receipt,
            fee_receipt=fee_receipt,
            amount_quote=amount_quote,
            entry_fill=entry_fill if isinstance(entry_fill, Mapping) else None,
            now=clock,
        )
        if cycle is None:
            cycle = _new_cycle(preflight)
        identity = (
            "cycle_id",
            "venue",
            "symbol",
            "account_id",
            "base_asset",
            "quote_asset",
        )
        if any(cycle.get(field) != preflight[field] for field in identity):
            return _result(
                "no_data",
                "authorization_conflicts_with_durable_cycle",
            )
        if cycle.get("phase") == "complete":
            return _result(
                "already_committed",
                "round_trip_already_complete",
                accounting=cycle.get("accounting"),
            )
        expected_side = (
            "SELL" if isinstance(cycle.get("entry_fill"), Mapping) else "BUY"
        )
        if preflight["side"] != expected_side:
            return _result(
                "no_data",
                f"{expected_side.lower()}_authorization_required_for_cycle_phase",
            )

        unresolved = cycle.get("unresolved")
        if unresolved is not None:
            if not isinstance(unresolved, Mapping):
                raise StateError("durable_unresolved_state_invalid")
            if (
                unresolved.get("intent_id") != preflight["intent_id"]
                or unresolved.get("side") != preflight["side"]
                or unresolved.get("quantity") != _text(preflight["quantity"])
                or unresolved.get("limit_price") != _text(preflight["limit_price"])
            ):
                return _result(
                    "pending_reconciliation",
                    "existing_unresolved_intent_blocks_new_submission",
                    reconciliation_required=True,
                )
            order_id = _id(unresolved.get("provider_order_id"))
            if order_id is None:
                return _result(
                    "pending_reconciliation",
                    "submission_outcome_requires_manual_provider_reconciliation",
                    reconciliation_required=True,
                    readback_count=0,
                )
            read_order = getattr(client, "read_order_receipt", None)
            if not callable(read_order):
                return _result(
                    "pending_reconciliation",
                    "adapter_read_order_receipt_required",
                    reconciliation_required=True,
                    readback_count=0,
                )
            try:
                receipt = read_order(
                    symbol=preflight["symbol"],
                    provider_order_id=order_id,
                )
            except Exception:
                return _result(
                    "pending_reconciliation",
                    "provider_status_readback_failed",
                    reconciliation_required=True,
                    readback_count=1,
                )
            try:
                fill = _terminal_fill(
                    receipt,
                    preflight=preflight,
                    expected_order_id=order_id,
                    now=clock,
                )
            except EvidenceError as exc:
                return _result(
                    "pending_reconciliation",
                    str(exc),
                    reconciliation_required=True,
                    readback_count=1,
                )
            outcome = _commit(path, state, cycle, fill)
            outcome["readback_count"] = 1
            return outcome

        submit = getattr(client, "submit_limit_order", None)
        if not callable(submit):
            return _result("no_data", "adapter_submit_limit_order_required")
        client_order_id = hashlib.sha256(
            (
                f"{preflight['venue']}|{preflight['account_id']}|"
                f"{preflight['cycle_id']}|{preflight['intent_id']}"
            ).encode("utf-8")
        ).hexdigest()
        try:
            receipt = submit(
                symbol=preflight["symbol"],
                side=preflight["side"],
                quantity=_text(preflight["quantity"]),
                limit_price=_text(preflight["limit_price"]),
                client_order_id=client_order_id,
            )
        except Exception:
            receipt = None
        try:
            fill = _terminal_fill(
                receipt,
                preflight=preflight,
                expected_order_id=None,
                now=clock,
            )
        except EvidenceError as exc:
            if _not_submitted(receipt):
                return _result(
                    "not_submitted",
                    str(exc),
                    submission_count=1,
                    readback_count=0,
                )
            cycle["unresolved"] = {
                "intent_id": preflight["intent_id"],
                "authorization_id": preflight["authorization_id"],
                "side": preflight["side"],
                "quantity": _text(preflight["quantity"]),
                "limit_price": _text(preflight["limit_price"]),
                "provider_order_id": _ack_id(receipt, preflight),
                "evidence_receipt_ids": dict(
                    preflight["evidence_receipt_ids"]
                ),
            }
            state["cycles"][preflight["cycle_id"]] = cycle
            _save(path, state)
            return _result(
                "pending_reconciliation",
                str(exc),
                reconciliation_required=True,
                submission_count=1,
                readback_count=0,
            )
        state["cycles"][preflight["cycle_id"]] = cycle
        outcome = _commit(path, state, cycle, fill)
        outcome["submission_count"] = 1
        outcome["readback_count"] = 0
        return outcome
    except (EvidenceError, StateError) as exc:
        return _result("no_data", str(exc))


def execute_profit_trade(
    client: LimitOrderAdapter,
    symbol: str,
    amount_quote: Any,
    *,
    authorization_receipt: Mapping[str, Any],
    position_receipt: Mapping[str, Any],
    account_receipt: Mapping[str, Any],
    quote_receipt: Mapping[str, Any],
    fee_receipt: Mapping[str, Any],
    state_path: str | Path,
    now: float | None = None,
) -> dict[str, Any]:
    """Serialize and advance one submission or one bounded read-back."""

    path = Path(state_path).expanduser().resolve()
    try:
        with _state_lock(path):
            return _execute_profit_trade_unlocked(
                client,
                symbol,
                amount_quote,
                authorization_receipt=authorization_receipt,
                position_receipt=position_receipt,
                account_receipt=account_receipt,
                quote_receipt=quote_receipt,
                fee_receipt=fee_receipt,
                state_path=path,
                now=now,
            )
    except StateError as exc:
        return _result("no_data", str(exc))


def main(argv: list[str] | None = None) -> int:
    """Expose only the inert boundary; never discover or construct a client."""

    parser = argparse.ArgumentParser(
        description=(
            "Receipt-gated limit-profit lifecycle; injected adapter required."
        )
    )
    parser.parse_args(argv)
    print(
        json.dumps(
            {
                "status": "not_submitted",
                "data_status": "not_submitted",
                "truth_status": "no_data",
                "reason": (
                    "inert_cli_requires_injected_adapter_and_explicit_receipts"
                ),
                "eligible_for_action": False,
                "eligible_for_accounting": False,
                "eligible_for_learning": False,
                "generated_values": False,
            },
            sort_keys=True,
        )
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
