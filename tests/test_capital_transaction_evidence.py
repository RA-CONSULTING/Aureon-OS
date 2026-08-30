from __future__ import annotations

import pytest

from aureon.exchanges.capital_client import ObservationList
from aureon.trading.capital_transaction_evidence import derive_capital_fee_receipt

NOW = 1_786_632_900.0


def _transactions(*rows, truth_status="real_observed") -> ObservationList:
    return ObservationList(
        rows,
        truth_status=truth_status,
        reason="complete_provider_transaction_history",
        source_timestamp=NOW - 1.0,
        received_at=NOW,
    )


def _row(kind: str, amount: float, *, reference: str = "DEAL-1") -> dict:
    return {
        "amount": amount,
        "currency": "GBP",
        "generated_values": False,
        "instrument_name": "GOLD",
        "reference": reference,
        "source_id": f"capital_transaction:{reference}:{kind}",
        "source_timestamp": NOW - 2.0,
        "status": "PROCESSED",
        "transaction_type": kind,
        "truth_status": "real_observed",
    }


def test_exact_trade_and_commission_create_real_fee_receipt() -> None:
    receipt = derive_capital_fee_receipt(
        _transactions(_row("TRADE", 1.5), _row("TRADE_COMMISSION", -0.25)),
        provider_deal_id="DEAL-1",
        instrument_name="GOLD",
        now=NOW,
    )

    assert receipt["amount"] == 0.25
    assert receipt["currency"] == "GBP"
    assert receipt["truth_status"] == "real_observed"
    assert receipt["generated_values"] is False
    assert receipt["transaction_types"] == ["TRADE", "TRADE_COMMISSION"]


def test_complete_trade_without_commission_proves_explicit_zero() -> None:
    receipt = derive_capital_fee_receipt(
        _transactions(_row("TRADE", -1.25)),
        provider_deal_id="DEAL-1",
        instrument_name="GOLD",
        now=NOW,
    )

    assert receipt["amount"] == 0.0
    assert receipt["basis"] == "complete_provider_transaction_history"


@pytest.mark.parametrize(
    ("transactions", "message"),
    [
        (_transactions(_row("TRADE", 1.0), truth_status="incomplete"), "complete_capital"),
        (_transactions(_row("TRADE_COMMISSION", -0.2)), "processed_capital_trade"),
        (_transactions(_row("TRADE", 1.0, reference="OTHER")), "processed_capital_trade"),
    ],
)
def test_missing_or_incomplete_exact_trade_fails_closed(transactions, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        derive_capital_fee_receipt(
            transactions,
            provider_deal_id="DEAL-1",
            instrument_name="GOLD",
            now=NOW,
        )


def test_stale_complete_response_fails_closed() -> None:
    transactions = _transactions(_row("TRADE", 1.0))
    transactions.source_timestamp = NOW - 901.0
    with pytest.raises(ValueError, match="fresh_capital_transaction_observation"):
        derive_capital_fee_receipt(
            transactions,
            provider_deal_id="DEAL-1",
            instrument_name="GOLD",
            now=NOW,
        )
