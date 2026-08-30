"""Strict Capital transaction evidence for fill settlement.

Capital confirmations establish that a position was opened or closed.  They do
not, by themselves, establish the provider-booked commission.  This module
derives a fee receipt only from a complete, fresh transaction-history
observation containing an exact processed ``TRADE`` row for the provider deal.
No spread, commission, financing, or zero value is estimated.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

FEE_TRANSACTION_TYPES = frozenset(
    {
        "FX_COMMISSION",
        "SWAP",
        "TRADE_COMMISSION",
        "TRADE_COMMISSION_GSL",
    }
)


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _number(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name}_must_be_finite")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name}_must_be_finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name}_must_be_finite")
    return result


def derive_capital_fee_receipt(
    transactions: Sequence[Mapping[str, Any]],
    *,
    provider_deal_id: str,
    instrument_name: str,
    now: float,
    max_age_s: float = 900.0,
) -> dict[str, Any]:
    """Return an exact provider fee receipt or raise a fail-closed reason.

    A matching processed trade row proves that the provider's transaction
    ledger covers the deal.  Matching explicit commission/swap rows are summed
    by absolute booked amount.  If no such fee row exists in that complete
    response, the explicit fee amount is zero; the bid/ask spread remains bound
    separately through the confirmed fill prices and is never labelled a fee.
    """

    deal_id = _text(provider_deal_id, "provider_deal_id")
    instrument = _text(instrument_name, "instrument_name").upper()
    current = _number(now, "now")
    max_age = _number(max_age_s, "max_age_s")
    if max_age <= 0:
        raise ValueError("max_age_s_must_be_positive")
    if isinstance(transactions, (str, bytes, bytearray)) or not isinstance(
        transactions, Sequence
    ):
        raise ValueError("capital_transaction_observation_required")
    if getattr(transactions, "truth_status", None) != "real_observed":
        raise ValueError("complete_capital_transaction_observation_required")
    if getattr(transactions, "generated_values", None) is not False:
        raise ValueError("real_capital_transaction_observation_required")
    observation_time = _number(
        getattr(transactions, "source_timestamp", None),
        "transaction_observation_source_timestamp",
    )
    if observation_time > current + 5.0 or current - observation_time > max_age:
        raise ValueError("fresh_capital_transaction_observation_required")

    matched: list[dict[str, Any]] = []
    for raw in transactions:
        if not isinstance(raw, Mapping):
            raise ValueError("complete_capital_transaction_rows_required")
        if raw.get("truth_status") != "real_observed" or raw.get("generated_values") is not False:
            raise ValueError("real_capital_transaction_rows_required")
        reference = _text(raw.get("reference"), "transaction_reference")
        row_instrument = _text(raw.get("instrument_name"), "transaction_instrument").upper()
        if reference != deal_id or row_instrument != instrument:
            continue
        transaction_type = _text(raw.get("transaction_type"), "transaction_type").upper()
        status = _text(raw.get("status"), "transaction_status").upper()
        source_id = _text(raw.get("source_id"), "transaction_source_id")
        source_timestamp = _number(raw.get("source_timestamp"), "transaction_source_timestamp")
        amount = _number(raw.get("amount"), "transaction_amount")
        currency = _text(raw.get("currency"), "transaction_currency").upper()
        if source_timestamp > current + 5.0 or current - source_timestamp > max_age:
            raise ValueError("fresh_capital_transaction_rows_required")
        matched.append(
            {
                "amount": amount,
                "currency": currency,
                "source_id": source_id,
                "source_timestamp": source_timestamp,
                "status": status,
                "transaction_type": transaction_type,
            }
        )

    trade_rows = [
        row
        for row in matched
        if row["transaction_type"] == "TRADE" and row["status"] == "PROCESSED"
    ]
    if not trade_rows:
        raise ValueError("processed_capital_trade_transaction_required")
    currencies = {row["currency"] for row in trade_rows}
    if len(currencies) != 1:
        raise ValueError("single_capital_transaction_currency_required")
    currency = next(iter(currencies))
    fee_rows = [
        row
        for row in matched
        if row["transaction_type"] in FEE_TRANSACTION_TYPES
        and row["status"] == "PROCESSED"
    ]
    if any(row["currency"] != currency for row in fee_rows):
        raise ValueError("capital_fee_currency_mismatch")
    source_rows = sorted(
        [*trade_rows, *fee_rows],
        key=lambda row: (row["source_timestamp"], row["source_id"]),
    )
    fee_amount = sum(abs(row["amount"]) for row in fee_rows)
    payload = {
        "amount": fee_amount,
        "basis": "complete_provider_transaction_history",
        "currency": currency,
        "provider_deal_id": deal_id,
        "source_ids": [row["source_id"] for row in source_rows],
        "source_timestamp": max(
            observation_time,
            *(row["source_timestamp"] for row in source_rows),
        ),
        "transaction_types": sorted({row["transaction_type"] for row in source_rows}),
    }
    return {
        **payload,
        "generated_values": False,
        "received_at": current,
        "source_id": f"capital_transaction_fee:{deal_id}:{_sha(payload)}",
        "truth_status": "real_observed",
    }


__all__ = ["FEE_TRANSACTION_TYPES", "derive_capital_fee_receipt"]
