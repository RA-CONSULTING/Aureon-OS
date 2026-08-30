#!/usr/bin/env python3
"""Receipt-gated penny-profit screening.

The legacy Auto Sniper name is retained for compatibility.  This module is
inert on import and on a default CLI invocation; it will only submit a sell
after complete, fresh provider receipts prove both the open position and a
two-sided quote.  A submission acknowledgement is never accounting evidence.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


STATE_FILE = os.getenv("AUREON_STATE_FILE", "aureon_kraken_state.json")
CHECK_INTERVAL = 30
MAX_RECEIPT_AGE_SECONDS = 60.0


def _finite(value: Any, *, positive: bool = False, nonnegative: bool = False) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or (positive and number <= 0) or (nonnegative and number < 0):
        return None
    return number


def _no_data(reason: str) -> Dict[str, Any]:
    return {
        "data_status": "no_data",
        "truth_status": "no_data",
        "generated_values": False,
        "action": False,
        "accounting": False,
        "learning": False,
        "reason": reason,
    }


def _fresh_receipt(receipt: Any, *, now: float, truth_status: str = "real_observed") -> Optional[str]:
    if not isinstance(receipt, Mapping):
        return "receipt_not_mapping"
    if receipt.get("data_status") != "live" or receipt.get("truth_status") != truth_status:
        return "receipt_not_real_observed"
    if receipt.get("generated_values") is not False:
        return "receipt_generated_or_unknown"
    for field in ("source_id", "receipt_id"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            return f"receipt_{field}_missing"
    source_timestamp = _finite(receipt.get("source_timestamp"), positive=True)
    received_at = _finite(receipt.get("received_at"), positive=True)
    if source_timestamp is None or received_at is None:
        return "receipt_timestamps_missing"
    if source_timestamp > now + 5.0:
        return "receipt_source_time_future"
    if now - source_timestamp > MAX_RECEIPT_AGE_SECONDS:
        return "receipt_source_time_stale"
    if received_at + 5.0 < source_timestamp:
        return "receipt_received_before_source"
    return None


def _complete_position(position: Any, *, now: float) -> Optional[str]:
    problem = _fresh_receipt(position, now=now)
    if problem:
        return problem
    if not isinstance(position, Mapping):
        return "position_not_mapping"
    if str(position.get("position_status") or "").upper() != "OPEN":
        return "position_not_open"
    if not isinstance(position.get("provider_position_id"), str) or not position["provider_position_id"].strip():
        return "provider_position_id_missing"
    if _finite(position.get("quantity"), positive=True) is None:
        return "position_quantity_invalid"
    if _finite(position.get("entry_value"), positive=True) is None:
        return "position_entry_value_invalid"
    if _finite(position.get("entry_fee"), nonnegative=True) is None:
        return "position_entry_fee_invalid"
    if not isinstance(position.get("fee_currency"), str) or not position["fee_currency"].strip():
        return "position_fee_currency_missing"
    return None


def _complete_quote(quote: Any, *, now: float) -> Optional[str]:
    problem = _fresh_receipt(quote, now=now)
    if problem:
        return problem
    if not isinstance(quote, Mapping):
        return "quote_not_mapping"
    if quote.get("action") is not False or quote.get("accounting") is not False or quote.get("learning") is not False:
        return "quote_controls_invalid"
    price = _finite(quote.get("price"), positive=True)
    bid = _finite(quote.get("bid"), positive=True)
    ask = _finite(quote.get("ask"), positive=True)
    if price is None or bid is None or ask is None:
        return "quote_price_or_book_missing"
    if ask < bid:
        return "quote_crossed_book"
    return None


def _terminal_fill(receipt: Any, *, now: float, required_quantity: float) -> Optional[str]:
    problem = _fresh_receipt(receipt, now=now)
    if problem:
        return problem
    if not isinstance(receipt, Mapping):
        return "fill_not_mapping"
    if str(receipt.get("status") or "").upper() != "FILLED":
        return "fill_not_terminal"
    if receipt.get("fill_receipt_complete") is not True or receipt.get("eligible_for_accounting") is not True:
        return "fill_not_accounting_eligible"
    if receipt.get("reconciliation_required") is True:
        return "fill_requires_reconciliation"
    if not isinstance(receipt.get("provider_order_id"), str) or not receipt["provider_order_id"].strip():
        return "provider_order_id_missing"
    trade_ids = receipt.get("provider_trade_ids") or receipt.get("provider_fill_ids") or receipt.get("fills")
    if not isinstance(trade_ids, (list, tuple)) or not trade_ids or not all(str(item).strip() for item in trade_ids):
        return "provider_trade_ids_missing"
    executed_quantity = _finite(receipt.get("executed_quantity"), positive=True)
    average_price = _finite(receipt.get("average_price"), positive=True)
    fee = _finite(receipt.get("total_fee"), nonnegative=True)
    if executed_quantity is None or average_price is None or fee is None:
        return "fill_observed_numbers_invalid"
    if executed_quantity + 1e-12 < required_quantity:
        return "fill_quantity_incomplete"
    if not isinstance(receipt.get("fee_currency"), str) or not receipt["fee_currency"].strip():
        return "fill_fee_currency_missing"
    return None


def load_state(state_file: str | os.PathLike[str] = STATE_FILE) -> Dict[str, Any]:
    try:
        with Path(state_file).open(encoding="utf-8") as handle:
            loaded = json.load(handle)
        return loaded if isinstance(loaded, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_state(state: Mapping[str, Any], state_file: str | os.PathLike[str] = STATE_FILE) -> bool:
    """Atomically persist a terminally reconciled state; never write in place."""
    destination = Path(state_file)
    temp_name: Optional[str] = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as handle:
            temp_name = handle.name
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, destination)
        return True
    except (OSError, TypeError, ValueError):
        if temp_name:
            try:
                Path(temp_name).unlink(missing_ok=True)
            except OSError:
                pass
        return False


def get_fee_rate(exchange: str) -> float:
    """Existing screening equation: fee + slippage + spread."""
    base_fees = {"binance": 0.001, "kraken": 0.0026, "alpaca": 0.0025, "capital": 0.001}
    return base_fees.get(exchange.lower(), 0.002) + 0.002 + 0.001


def _deduplicated(state: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    settled_receipts = set(state.get("settled_terminal_receipt_ids", []) or [])
    settled_trades = set(state.get("settled_provider_trade_ids", []) or [])
    receipt_id = receipt.get("receipt_id")
    trade_ids = receipt.get("provider_trade_ids") or receipt.get("provider_fill_ids") or receipt.get("fills") or []
    return receipt_id in settled_receipts or any(item in settled_trades for item in trade_ids)


def check_and_kill(client: Any, state: Dict[str, Any], *, state_file: str | os.PathLike[str] = STATE_FILE, now: Optional[float] = None) -> Dict[str, Any]:
    """Screen receipts and account only a complete, unique terminal provider fill."""
    current = time.time() if now is None else now
    if not math.isfinite(current):
        return _no_data("clock_invalid")
    positions = state.get("positions")
    if not isinstance(positions, dict) or not positions:
        return _no_data("positions_missing")

    quotes: Dict[str, Mapping[str, Any]] = {}
    for symbol, position in positions.items():
        problem = _complete_position(position, now=current)
        if problem:
            return _no_data(f"position_{symbol}_{problem}")
        try:
            quote = client.get_ticker(position["exchange"], symbol)
        except Exception:
            return _no_data(f"quote_{symbol}_unavailable")
        problem = _complete_quote(quote, now=current)
        if problem:
            return _no_data(f"quote_{symbol}_{problem}")
        quotes[symbol] = quote

    candidates: list[tuple[str, Mapping[str, Any], Mapping[str, Any], float]] = []
    for symbol, position in positions.items():
        quantity = float(position["quantity"])
        entry_value = float(position["entry_value"])
        current_value = quantity * float(quotes[symbol]["price"])
        gross_pnl = current_value - entry_value
        # Preserve the existing screening equation; it is not accounting evidence.
        net_pnl = gross_pnl - float(position["entry_fee"]) - current_value * get_fee_rate(str(position["exchange"]))
        if net_pnl >= 0.0001:
            candidates.append((symbol, position, quotes[symbol], net_pnl))

    if not candidates:
        return {"data_status": "live", "truth_status": "real_derived", "generated_values": False, "action": False, "accounting": False, "learning": False, "status": "screened"}

    fills: list[tuple[str, Mapping[str, Any]]] = []
    for symbol, position, _quote, _screened_net in candidates:
        try:
            receipt = client.place_market_order(str(position["exchange"]), symbol, "SELL", quantity=float(position["quantity"]))
        except Exception:
            return _no_data(f"terminal_fill_{symbol}_unavailable")
        problem = _terminal_fill(receipt, now=current, required_quantity=float(position["quantity"]))
        if problem:
            return _no_data(f"terminal_fill_{symbol}_{problem}")
        if _deduplicated(state, receipt):
            return _no_data(f"terminal_fill_{symbol}_duplicate")
        fills.append((symbol, receipt))

    updated = copy.deepcopy(state)
    updated_positions = updated.get("positions", {})
    total_net = 0.0
    receipt_ids = list(updated.get("settled_terminal_receipt_ids", []) or [])
    trade_ids = list(updated.get("settled_provider_trade_ids", []) or [])
    for symbol, receipt in fills:
        position = positions[symbol]
        realized = float(receipt["executed_quantity"]) * float(receipt["average_price"]) - float(position["entry_value"]) - float(position["entry_fee"]) - float(receipt["total_fee"])
        total_net += realized
        del updated_positions[symbol]
        receipt_ids.append(receipt["receipt_id"])
        trade_ids.extend(receipt.get("provider_trade_ids") or receipt.get("provider_fill_ids") or receipt.get("fills") or [])
    updated["settled_terminal_receipt_ids"] = receipt_ids[-1000:]
    updated["settled_provider_trade_ids"] = trade_ids[-5000:]
    updated["wins"] = int(updated.get("wins", 0)) + len(fills)
    updated["total_trades"] = int(updated.get("total_trades", 0)) + len(fills)
    updated["harvested"] = float(updated.get("harvested", 0.0)) + total_net
    updated["balance"] = float(updated.get("balance", 0.0)) + total_net
    if not save_state(updated, state_file):
        return _no_data("atomic_state_write_failed")
    state.clear()
    state.update(updated)
    return {"data_status": "live", "truth_status": "real_derived", "generated_values": False, "action": True, "accounting": True, "learning": False, "status": "terminal_fills_accounted", "kills": len(fills), "total_net_pnl": total_net}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="explicitly enable the receipt-gated scan loop")
    parser.add_argument("--state-file", default=STATE_FILE)
    args = parser.parse_args(argv)
    if not args.run:
        print("Auto Sniper is inert by default; pass --run to enable receipt-gated scanning.")
        return 0
    try:
        from aureon.trading.unified_exchange_client import MultiExchangeClient
    except ImportError as exc:
        print(f"Cannot import MultiExchangeClient: {exc}")
        return 1
    client = MultiExchangeClient()
    try:
        while True:
            state = load_state(args.state_file)
            outcome = check_and_kill(client, state, state_file=args.state_file)
            print(json.dumps(outcome, sort_keys=True))
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
