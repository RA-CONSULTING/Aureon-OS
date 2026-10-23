from __future__ import annotations

import copy
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from aureon.exchanges.kraken_client import (
    KRAKEN_FILL_RECEIPT_MAX_AGE_SECONDS,
    KrakenClient,
)
from scripts.validation.validate_real_data_contract import scan_text_file


ROOT = Path(__file__).resolve().parents[1]
KRAKEN_PATH = ROOT / "aureon" / "exchanges" / "kraken_client.py"
ORDER_ID = "OQCLML-BW3P3-BUCMWZ"
TRADE_ID = "TCCCTY-WE2O6-P3NB37"
FILL_FIELDS = (
    "executedQty",
    "filled_qty",
    "avgPrice",
    "filled_avg_price",
    "cummulativeQuoteQty",
    "filled_notional",
    "fee",
    "fills",
    "provider_timestamp",
    "source_timestamp",
)


def _client(*, dry_run: bool = False) -> KrakenClient:
    client = KrakenClient.__new__(KrakenClient)
    client.dry_run = dry_run
    client._pairs_cache = {}
    client._alt_to_int = {}
    client._int_to_alt = {}
    return client


def _assert_no_fill(receipt: dict) -> None:
    for field in FILL_FIELDS:
        assert receipt[field] is None
    assert receipt["fill_receipt_complete"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False
    assert receipt["generated_values"] is False


def _terminal_order(*, close_time: float | None = None) -> dict:
    return {
        "status": "closed",
        "vol": "1.25",
        "vol_exec": "1.25",
        "price": "2000",
        "cost": "2500",
        "fee": "6.5",
        "closetm": time.time() if close_time is None else close_time,
        "trades": [TRADE_ID],
        "descr": {
            "pair": "XETHZUSD",
            "type": "sell",
            "ordertype": "market",
            "price": "0",
        },
    }


def _market_client(add_order_result: dict, *, dry_run: bool = False) -> KrakenClient:
    client = _client(dry_run=dry_run)
    client._resolve_pair = Mock(
        return_value=(
            "XETHZUSD",
            {"ordermin": "0.001", "lot_decimals": 8},
        )
    )
    client.best_price = Mock(side_effect=AssertionError("price lookup not expected"))
    client._private = Mock(return_value=add_order_result)
    return client


def test_add_order_acknowledgement_is_pending_and_has_no_fill_values() -> None:
    client = _market_client({"txid": [ORDER_ID]})

    receipt = client.place_market_order("ETHUSD", "sell", quantity="1.25")

    assert receipt["orderId"] == ORDER_ID
    assert receipt["status"] == "pending_reconciliation"
    assert receipt["data_status"] == "pending_reconciliation"
    assert receipt["submitted"] is True
    assert receipt["reconciliation_required"] is True
    assert receipt["receipt_id"].startswith("kraken_order_ack:")
    assert receipt["input_receipt_ids"] == []
    _assert_no_fill(receipt)
    client._private.assert_called_once_with(
        "/0/private/AddOrder",
        {
            "pair": "XETHZUSD",
            "type": "sell",
            "ordertype": "market",
            "volume": "1.25",
        },
    )
    client.best_price.assert_not_called()


def test_missing_add_order_txid_is_ambiguous_and_blocks_fill_claims() -> None:
    client = _market_client({})

    receipt = client.place_market_order("ETHUSD", "sell", quantity="1.25")

    assert receipt["orderId"] is None
    assert receipt["status"] == "pending_reconciliation"
    assert receipt["truth_status"] == "no_data"
    assert receipt["submitted"] is None
    assert receipt["reconciliation_required"] is True
    assert receipt["reason"] == "missing_or_ambiguous_provider_txid"
    _assert_no_fill(receipt)


def test_ambiguous_entry_ack_blocks_dependent_take_profit_submission() -> None:
    client = _client()
    client._load_asset_pairs = Mock(return_value={})
    client._alt_to_int = {"ETHUSD": "XETHZUSD"}
    client._private = Mock(return_value={})

    receipt = client.place_order_with_tp_sl(
        "ETHUSD",
        "buy",
        quantity="1.25",
        take_profit="2200",
        stop_loss="1800",
    )

    assert receipt["status"] == "pending_reconciliation"
    assert receipt["orderId"] is None
    assert receipt["takeProfitOrderId"] is None
    assert receipt["reason"] == "entry_submission_receipt_unproven"
    _assert_no_fill(receipt)
    client._private.assert_called_once()


def test_dry_run_is_not_submitted_and_never_calls_provider() -> None:
    client = _market_client({"txid": [ORDER_ID]}, dry_run=True)

    receipt = client.place_market_order("ETHUSD", "sell", quantity="1.25")

    assert receipt["status"] == "not_submitted"
    assert receipt["data_status"] == "not_submitted"
    assert receipt["submitted"] is False
    assert receipt["orderId"] is None
    _assert_no_fill(receipt)
    client._private.assert_not_called()


def test_dry_run_order_query_is_explicit_no_data_not_a_state_claim() -> None:
    client = _client(dry_run=True)
    client._private = Mock(side_effect=AssertionError("provider query not expected"))

    receipt = client.get_order_status(ORDER_ID)

    assert receipt["orderId"] == ORDER_ID
    assert receipt["status"] == "no_data"
    assert receipt["data_status"] == "no_data"
    assert receipt["reconciliation_required"] is True
    _assert_no_fill(receipt)
    client._private.assert_not_called()


def test_fresh_terminal_query_orders_receipt_exposes_only_observed_fill() -> None:
    provider_close_time = time.time()
    client = _client()
    client._private = Mock(
        return_value={ORDER_ID: _terminal_order(close_time=provider_close_time)}
    )
    client._pair_base_quote = Mock(return_value=("ETH", "USD"))

    receipt = client.get_order_status(ORDER_ID)

    assert receipt["status"] == "FILLED"
    assert receipt["data_status"] == "live"
    assert receipt["truth_status"] == "real_observed"
    assert receipt["executedQty"] == "1.25"
    assert receipt["filled_avg_price"] == "2000"
    assert receipt["cummulativeQuoteQty"] == "2500"
    assert receipt["fee"] == "6.5"
    assert receipt["fee_asset"] == "USD"
    assert receipt["fee_currency"] == "USD"
    assert receipt["fills"] == [
        {"tradeId": TRADE_ID, "source": "kraken_queryorders"}
    ]
    assert receipt["provider_timestamp"] == pytest.approx(provider_close_time)
    assert receipt["receipt_id"].startswith("kraken_order:")
    assert receipt["input_receipt_ids"] == [f"kraken_trade:{TRADE_ID}"]
    assert receipt["fill_receipt_complete"] is True
    assert receipt["eligible_for_accounting"] is True
    assert receipt["eligible_for_learning"] is True
    client._private.assert_called_once_with(
        "/0/private/QueryOrders",
        {"txid": ORDER_ID, "trades": True},
    )


def test_closed_orders_uses_the_same_terminal_fill_gate() -> None:
    client = _client()
    client._private = Mock(
        return_value={"closed": {ORDER_ID: _terminal_order()}}
    )
    client._pair_base_quote = Mock(return_value=("ETH", "USD"))

    receipts = client.get_closed_orders()

    assert len(receipts) == 1
    assert receipts[0]["status"] == "FILLED"
    assert receipts[0]["provider_receipt_type"] == "ClosedOrders"
    assert receipts[0]["fill_receipt_complete"] is True
    client._private.assert_called_once_with(
        "/0/private/ClosedOrders",
        {"trades": True},
    )


def test_open_query_orders_receipt_cannot_leak_partial_fill_values() -> None:
    order = _terminal_order()
    order["status"] = "open"
    client = _client()
    client._private = Mock(return_value={ORDER_ID: order})
    client._pair_base_quote = Mock(side_effect=AssertionError("not terminal"))

    receipt = client.get_order_status(ORDER_ID)

    assert receipt["status"] == "pending_reconciliation"
    assert receipt["data_status"] == "pending_reconciliation"
    _assert_no_fill(receipt)
    client._pair_base_quote.assert_not_called()


def test_terminal_short_fill_is_not_labeled_fully_filled() -> None:
    order = _terminal_order()
    order.update({"vol": "2", "vol_exec": "1", "cost": "2000"})
    client = _client()
    client._private = Mock(return_value={ORDER_ID: order})
    client._pair_base_quote = Mock(return_value=("ETH", "USD"))

    receipt = client.get_order_status(ORDER_ID)

    assert receipt["status"] == "PARTIALLY_FILLED"
    assert receipt["data_status"] == "live"
    assert receipt["executedQty"] == "1"
    assert receipt["fill_receipt_complete"] is False
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False
    assert receipt["reconciliation_required"] is True


def test_balance_receipt_uses_private_balance_and_separate_kraken_time() -> None:
    provider_time = time.time() - 0.25
    client = _client()
    client._private = Mock(return_value={"XXBT": "0.25", "ZUSD": "125.50"})
    client._public_get = Mock(return_value={"unixtime": provider_time})

    first = client.get_account_balance_receipt()
    second = client.get_account_balance_receipt()

    assert first["account_scope"] == "complete"
    assert first["balances"] == {"BTC": 0.25, "USD": 125.5}
    assert first["balance_text"] == {"BTC": "0.25", "USD": "125.50"}
    assert first["source_timestamp"] == pytest.approx(provider_time)
    assert first["received_at"] >= first["source_timestamp"]
    assert first["data_status"] == "live"
    assert first["truth_status"] == "real_observed"
    assert first["generated_values"] is False
    assert first["receipt_id"].startswith("kraken_balance:")
    assert first["receipt_id"] == second["receipt_id"]
    assert len(first["input_receipt_ids"]) == 2
    assert client._private.call_count == 2
    assert client._public_get.call_count == 2
    client._private.assert_called_with("/0/private/Balance", {})
    client._public_get.assert_called_with("/0/public/Time")


def test_balance_receipt_rejects_stale_clock_and_dry_run_without_provider() -> None:
    client = _client()
    client._private = Mock(return_value={"ZUSD": "10"})
    client._public_get = Mock(return_value={"unixtime": time.time() - 61.0})

    stale = client.get_account_balance_receipt()

    assert stale["data_status"] == "no_data"
    assert stale["source_timestamp"] is None
    assert stale["balances"] is None
    assert stale["receipt_id"] is None

    dry_run = _client(dry_run=True)
    dry_run._private = Mock(side_effect=AssertionError("private call not expected"))
    dry_run._public_get = Mock(side_effect=AssertionError("public call not expected"))

    blocked = dry_run.get_account_balance_receipt()

    assert blocked["data_status"] == "no_data"
    assert blocked["reason"] == "live_private_balance_receipt_required"
    dry_run._private.assert_not_called()
    dry_run._public_get.assert_not_called()


def test_terminal_order_receipt_id_is_deterministic_from_provider_evidence() -> None:
    provider_time = time.time()
    order = _terminal_order(close_time=provider_time)
    client = _client()
    client._pair_base_quote = Mock(return_value=("ETH", "USD"))

    first = client._normalize_order_receipt(
        ORDER_ID,
        copy.deepcopy(order),
        provider_receipt_type="QueryOrders",
        now=provider_time,
    )
    second = client._normalize_order_receipt(
        ORDER_ID,
        copy.deepcopy(order),
        provider_receipt_type="QueryOrders",
        now=provider_time,
    )

    assert first["receipt_id"] == second["receipt_id"]
    assert first["receipt_id"].startswith("kraken_order:")
    assert first["input_receipt_ids"] == [f"kraken_trade:{TRADE_ID}"]


def test_stale_terminal_receipt_is_no_data_with_no_fill_values() -> None:
    stale_time = time.time() - KRAKEN_FILL_RECEIPT_MAX_AGE_SECONDS - 1
    client = _client()
    client._private = Mock(
        return_value={ORDER_ID: _terminal_order(close_time=stale_time)}
    )
    client._pair_base_quote = Mock(side_effect=AssertionError("stale receipt"))

    receipt = client.get_order_status(ORDER_ID)

    assert receipt["status"] == "no_data"
    assert receipt["data_status"] == "no_data"
    assert receipt["reason"] == "missing_or_stale_provider_close_timestamp"
    _assert_no_fill(receipt)
    client._pair_base_quote.assert_not_called()


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    (
        ("price", None, "missing_or_malformed_provider_average_price"),
        ("cost", "NaN", "missing_or_malformed_provider_filled_cost"),
        ("fee", None, "missing_or_malformed_provider_fee"),
        ("trades", [], "missing_or_ambiguous_provider_trade_ids"),
        ("vol", None, "missing_or_malformed_provider_requested_quantity"),
    ),
)
def test_malformed_terminal_receipt_is_no_data(
    field: str,
    value: object,
    reason: str,
) -> None:
    order = copy.deepcopy(_terminal_order())
    order[field] = value
    client = _client()
    client._private = Mock(return_value={ORDER_ID: order})
    client._pair_base_quote = Mock(return_value=("ETH", "USD"))

    receipt = client.get_order_status(ORDER_ID)

    assert receipt["data_status"] == "no_data"
    assert receipt["reason"] == reason
    _assert_no_fill(receipt)


def test_margin_market_add_order_is_pending_not_filled() -> None:
    client = _client()
    client._resolve_pair = Mock(
        return_value=(
            "XETHZUSD",
            {
                "ordermin": "0.001",
                "lot_decimals": 8,
                "leverage_buy": [],
                "leverage_sell": [2],
            },
        )
    )
    client._private = Mock(return_value={"txid": [ORDER_ID]})

    receipt = client.place_margin_order(
        "ETHUSD",
        "sell",
        quantity="1.25",
        leverage=2,
    )

    assert receipt["status"] == "pending_reconciliation"
    assert receipt["margin"] is True
    _assert_no_fill(receipt)


def test_conversion_stops_after_submission_ack_and_never_advances_amount() -> None:
    client = _client()
    client.find_conversion_path = Mock(
        return_value=[
            {"pair": "ETHUSD", "side": "sell"},
            {"pair": "SOLUSD", "side": "buy"},
        ]
    )
    client.get_symbol_filters = Mock(
        return_value={"min_qty": 0.001, "min_notional": 1.0}
    )
    client.best_price = Mock(return_value={"price": 10.0})
    pending = client._submission_order_receipt(
        {"txid": [ORDER_ID]},
        symbol="ETHUSD",
        side="sell",
        order_type="market",
        requested_quantity="2",
    )
    client.place_market_order = Mock(return_value=pending)

    result = client.convert_crypto("ETH", "SOL", 2.0)

    assert result["error"] == "terminal_fill_receipt_required"
    assert result["data_status"] == "pending_reconciliation"
    assert result["reconciliation_required"] is True
    assert "receivedQty" not in result["partial_results"][0]["result"]
    client.place_market_order.assert_called_once()


def test_fee_accounting_requires_verified_currency_matched_receipt() -> None:
    client = _client()
    pending = client._submission_order_receipt(
        {"txid": [ORDER_ID]},
        symbol="ETHUSD",
        side="sell",
        order_type="market",
        requested_quantity="1",
    )
    assert client.compute_order_fees_in_quote(pending, "USD") is None

    live = {
        "data_status": "live",
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "fee": "6.5",
        "fee_asset": "USD",
    }
    assert client.compute_order_fees_in_quote(live, "USD") == pytest.approx(6.5)
    assert client.compute_order_fees_in_quote(live, "GBP") is None


def test_dry_run_trade_balance_contains_no_fabricated_account_values() -> None:
    client = _client(dry_run=True)

    receipt = client.get_trade_balance()

    assert receipt["data_status"] == "not_submitted"
    for field in (
        "equity_value",
        "trade_balance",
        "margin_amount",
        "unrealized_pnl",
        "cost_basis",
        "floating_valuation",
        "free_margin",
        "margin_level",
    ):
        assert receipt[field] is None


def test_scoped_runtime_file_has_no_real_data_validator_findings() -> None:
    assert scan_text_file(KRAKEN_PATH, ROOT) == []
