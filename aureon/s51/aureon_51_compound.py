#!/usr/bin/env python3
"""Aureon 51% observed compounding report.

This module never generates wins, losses, balances, or fills. It summarizes
provider-receipted closed trades supplied by the caller. Missing receipts are
reported as no_data.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from aureon.core.aureon_baton_link import link_system as _baton_link

_baton_link(__name__)


@dataclass(frozen=True)
class ClosedTradeReceipt:
    """Normalized closed trade read back from an execution provider."""

    receipt_id: str
    provider: str
    symbol: str
    closed_at: str
    realized_pnl: float
    fees: float
    balance_after: float
    source_timestamp: str
    truth_status: str = "observed"

    @classmethod
    def from_mapping(cls, value: Dict[str, Any]) -> "ClosedTradeReceipt":
        required = (
            "receipt_id",
            "provider",
            "symbol",
            "closed_at",
            "realized_pnl",
            "fees",
            "balance_after",
            "source_timestamp",
        )
        missing = [key for key in required if value.get(key) is None]
        if missing:
            raise ValueError(f"no_data: closed-trade receipt missing {missing}")
        if value.get("truth_status", "observed") != "observed":
            raise ValueError("closed-trade receipt must be provider-observed")
        return cls(
            receipt_id=str(value["receipt_id"]),
            provider=str(value["provider"]),
            symbol=str(value["symbol"]),
            closed_at=str(value["closed_at"]),
            realized_pnl=float(value["realized_pnl"]),
            fees=float(value["fees"]),
            balance_after=float(value["balance_after"]),
            source_timestamp=str(value["source_timestamp"]),
        )


def summarize_compounding(
    receipts: Iterable[ClosedTradeReceipt | Dict[str, Any]],
) -> Dict[str, Any]:
    """Summarize actual closed-trade receipts without projecting outcomes."""

    normalized: List[ClosedTradeReceipt] = [
        item if isinstance(item, ClosedTradeReceipt) else ClosedTradeReceipt.from_mapping(item)
        for item in receipts
    ]
    generated_at = datetime.now(timezone.utc).isoformat()
    if not normalized:
        return {
            "status": "no_data",
            "truth_status": "no_data",
            "generated_at": generated_at,
            "reason": "No provider-observed closed-trade receipts were supplied.",
            "trade_count": 0,
            "win_count": None,
            "loss_count": None,
            "win_rate": None,
            "net_pnl": None,
            "fees": None,
            "ending_balance": None,
            "receipt_ids": [],
        }

    wins = sum(receipt.realized_pnl > 0 for receipt in normalized)
    losses = sum(receipt.realized_pnl <= 0 for receipt in normalized)
    latest = max(normalized, key=lambda receipt: receipt.closed_at)
    return {
        "status": "ok",
        "truth_status": "real_derived",
        "generated_at": generated_at,
        "source": "provider closed-trade receipts",
        "providers": sorted({receipt.provider for receipt in normalized}),
        "trade_count": len(normalized),
        "win_count": wins,
        "loss_count": losses,
        "win_rate": wins / len(normalized),
        "net_pnl": sum(receipt.realized_pnl for receipt in normalized),
        "fees": sum(receipt.fees for receipt in normalized),
        "ending_balance": latest.balance_after,
        "latest_source_timestamp": max(receipt.source_timestamp for receipt in normalized),
        "receipt_ids": [receipt.receipt_id for receipt in normalized],
    }


def run_compound_sim() -> None:
    """Compatibility entry point retained as an explicit retired path."""

    raise RuntimeError(
        "Synthetic compounding is retired. Supply provider-observed closed "
        "trade receipts to summarize_compounding()."
    )


if __name__ == "__main__":
    report = summarize_compounding([])
    print(report)
