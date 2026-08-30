#!/usr/bin/env python3
"""
Receipt-only exchange execution verifier.

This command validates already-produced provider execution receipts. It never
initializes exchange clients, changes live-mode environment variables, calls a
provider, or submits an order. Missing, stale, generated, or incomplete evidence
returns explicit no_data and cannot become action, accounting, or learning proof.
"""

import json
import time
import argparse
import math
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional


MAX_RECEIPT_AGE_SECONDS = 300.0


def _finite_number(value: Any, *, positive: bool = False) -> Optional[float]:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or (positive and number <= 0):
        return None
    return number


def _receipt_timestamp(value: Any) -> Optional[float]:
    number = _finite_number(value, positive=True)
    if number is not None:
        return number / 1000.0 if number > 10_000_000_000 else number
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


def _identifier(value: Any) -> Optional[str]:
    if value is None or isinstance(value, bool):
        return None
    identifier = str(value).strip()
    if identifier.upper() in {"", "N/A", "NONE", "NULL", "UNKNOWN", "DRY_RUN"}:
        return None
    return identifier


def _terminal_fill(receipt: Any, *, now: Optional[float] = None) -> bool:
    """Return True only for a complete fresh terminal provider fill receipt."""
    if not isinstance(receipt, Mapping):
        return False
    current = time.time() if now is None else _finite_number(now, positive=True)
    source_timestamp = _receipt_timestamp(
        receipt.get("source_timestamp") or receipt.get("provider_timestamp")
    )
    received_at = _receipt_timestamp(receipt.get("received_at"))
    source_id = _identifier(receipt.get("source_id") or receipt.get("provider_id"))
    receipt_id = _identifier(
        receipt.get("receipt_id") or receipt.get("provider_receipt_id")
    )
    order_id = _identifier(
        receipt.get("provider_order_id")
        or receipt.get("orderId")
        or receipt.get("order_id")
    )
    trade_ids = (
        receipt.get("provider_trade_ids")
        or receipt.get("provider_fill_ids")
        or receipt.get("trade_ids")
        or receipt.get("fills")
    )
    quantity = _finite_number(
        receipt.get("executed_quantity")
        or receipt.get("executedQty")
        or receipt.get("filled_qty"),
        positive=True,
    )
    price = _finite_number(
        receipt.get("average_price")
        or receipt.get("avg_fill_price")
        or receipt.get("avgPrice"),
        positive=True,
    )
    notional = _finite_number(
        receipt.get("quote_quantity")
        or receipt.get("cost")
        or receipt.get("cummulativeQuoteQty")
        or receipt.get("filled_notional"),
        positive=True,
    )
    fee = _finite_number(receipt.get("total_fee") if "total_fee" in receipt else receipt.get("fee"))
    fee_currency = _identifier(
        receipt.get("fee_currency") or receipt.get("commission_asset")
    )
    normalized_trade_ids = (
        [
            _identifier(item.get("id") if isinstance(item, Mapping) else item)
            for item in trade_ids
        ]
        if isinstance(trade_ids, (list, tuple))
        else []
    )
    notional_consistent = bool(
        quantity is not None
        and price is not None
        and notional is not None
        and abs((quantity * price) - notional) <= max(1e-8, notional * 0.01)
    )
    return bool(
        current is not None
        and receipt.get("data_status") == "live"
        and receipt.get("truth_status") in {"real_observed", "real_derived"}
        and receipt.get("generated_values") is False
        and str(receipt.get("status") or "").upper() == "FILLED"
        and receipt.get("fill_receipt_complete") is True
        and receipt.get("eligible_for_accounting") is True
        and receipt.get("reconciliation_required") is not True
        and source_timestamp is not None
        and received_at is not None
        and -5.0 <= received_at - source_timestamp <= MAX_RECEIPT_AGE_SECONDS
        and -5.0 <= current - received_at <= MAX_RECEIPT_AGE_SECONDS
        and source_id is not None
        and receipt_id is not None
        and order_id is not None
        and normalized_trade_ids
        and all(item is not None for item in normalized_trade_ids)
        and quantity is not None
        and price is not None
        and notional is not None
        and notional_consistent
        and fee is not None
        and fee >= 0
        and fee_currency is not None
    )


def _terminal_conversion(receipt: Any, *, now: Optional[float] = None) -> bool:
    if not isinstance(receipt, Mapping) or receipt.get("status") != "success":
        return False
    trades = receipt.get("trades")
    if not isinstance(trades, list) or not trades:
        return False
    return all(
        _terminal_fill(trade.get("result", trade), now=now)
        for trade in trades
        if isinstance(trade, Mapping)
    ) and all(isinstance(trade, Mapping) for trade in trades)




def _no_data_report(
    reason: str, *, received_at: Optional[float] = None
) -> dict[str, Any]:
    return {
        "status": "no_data",
        "data_status": "no_data",
        "truth_status": "no_data",
        "source_id": None,
        "source_timestamp": None,
        "received_at": time.time() if received_at is None else received_at,
        "receipt_id": None,
        "generated_values": False,
        "actionable": False,
        "action_enabled": False,
        "eligible_for_external_action": False,
        "accounting_enabled": False,
        "eligible_for_accounting": False,
        "learning_enabled": False,
        "eligible_for_learning": False,
        "reason": reason,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Receipt-only verifier; it never calls exchanges or submits orders."
    )
    parser.add_argument("--receipts", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    received_at = time.time()

    if args.live:
        report = _no_data_report("live_submission_disabled", received_at=received_at)
    elif args.receipts is None:
        report = _no_data_report("receipt_file_required", received_at=received_at)
    else:
        try:
            document = json.loads(args.receipts.read_text(encoding="utf-8"))
            receipts = (
                document
                if isinstance(document, list)
                else document.get("receipts")
                if isinstance(document, Mapping) and isinstance(document.get("receipts"), list)
                else [document]
                if isinstance(document, Mapping)
                else None
            )
            if not isinstance(receipts, list) or not receipts:
                report = _no_data_report(
                    "provider_receipts_missing", received_at=received_at
                )
            else:
                valid = all(
                    _terminal_conversion(receipt, now=received_at)
                    if isinstance(receipt, Mapping) and isinstance(receipt.get("trades"), list)
                    else _terminal_fill(receipt, now=received_at)
                    for receipt in receipts
                )
                evidence_receipts: list[Mapping[str, Any]] = []
                for receipt in receipts:
                    if not isinstance(receipt, Mapping):
                        continue
                    trades = receipt.get("trades")
                    if isinstance(trades, list):
                        evidence_receipts.extend(
                            trade.get("result", trade)
                            for trade in trades
                            if isinstance(trade, Mapping)
                            and isinstance(trade.get("result", trade), Mapping)
                        )
                    else:
                        evidence_receipts.append(receipt)
                source_timestamps = [
                    _receipt_timestamp(
                        receipt.get("source_timestamp")
                        or receipt.get("provider_timestamp")
                    )
                    for receipt in evidence_receipts
                ]
                receipt_ids = [
                    _identifier(
                        receipt.get("receipt_id")
                        or receipt.get("provider_receipt_id")
                    )
                    for receipt in evidence_receipts
                ]
                source_timestamps = [
                    timestamp for timestamp in source_timestamps if timestamp is not None
                ]
                receipt_ids = [
                    receipt_id for receipt_id in receipt_ids if receipt_id is not None
                ]
                audit_receipt_id = (
                    "exchange-receipt-audit:"
                    + hashlib.sha256(
                        json.dumps(receipt_ids, sort_keys=True).encode("utf-8")
                    ).hexdigest()
                    if valid
                    else None
                )
                report = {
                    **_no_data_report(
                        "verified_terminal_provider_receipts"
                        if valid
                        else "one_or_more_receipts_unverified",
                        received_at=received_at,
                    ),
                    "status": "verified" if valid else "no_data",
                    "data_status": "live" if valid else "no_data",
                    "truth_status": "real_derived" if valid else "no_data",
                    "source_id": "exchange_receipt_contract_audit" if valid else None,
                    "source_timestamp": max(source_timestamps) if valid else None,
                    "receipt_id": audit_receipt_id,
                    "input_receipt_ids": receipt_ids if valid else [],
                    "receipt_count": len(receipts),
                    "reason": None if valid else "one_or_more_receipts_unverified",
                }
        except (OSError, UnicodeError, json.JSONDecodeError, AttributeError) as exc:
            report = _no_data_report(
                f"receipt_file_unavailable:{type(exc).__name__}",
                received_at=received_at,
            )

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_name(f".{args.output.name}.tmp")
        temporary.write_text(rendered + "\n", encoding="utf-8")
        temporary.replace(args.output)
    return 0 if report["status"] == "verified" else 2


if __name__ == "__main__":
    raise SystemExit(main())
