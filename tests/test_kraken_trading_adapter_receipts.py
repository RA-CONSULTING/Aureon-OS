from __future__ import annotations

import time

from aureon.exchanges.kraken_trading_adapter import KrakenTradingAdapter


def _ticker(
    symbol: str = "SOLUSD",
    *,
    price: float = 100.0,
    generated: bool = False,
    age: float = 0.0,
) -> dict:
    now = time.time()
    return {
        "symbol": symbol,
        "bid": price * 0.99,
        "ask": price * 1.01,
        "price": price,
        "provider": "kraken",
        "venue": "kraken",
        "provider_receipt_type": "Ticker+Time",
        "source_id": "kraken:/0/public/Ticker+/0/public/Time",
        "source_timestamp": now - age,
        "received_at": now,
        "receipt_id": f"kraken_ticker:{symbol.lower()}",
        "input_receipt_ids": [
            f"kraken_ticker_payload:{symbol.lower()}",
            "kraken_time:clock-1",
        ],
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": generated,
        "action": False,
        "accounting": False,
        "learning": False,
    }


def _account_receipt(
    balances: dict[str, float] | None = None,
    *,
    age: float = 0.0,
) -> dict:
    now = time.time()
    observed = {"USD": 100.0, "SOL": 2.0} if balances is None else balances
    return {
        "provider": "kraken",
        "venue": "kraken",
        "provider_receipt_type": "Balance+Time",
        "account_scope": "complete",
        "balances": dict(observed),
        "balance_text": {key: str(value) for key, value in observed.items()},
        "source_id": "kraken:/0/private/Balance+/0/public/Time",
        "source_timestamp": now - age,
        "received_at": now,
        "receipt_id": "kraken_balance:account-1",
        "input_receipt_ids": [
            "kraken_balance_payload:payload-1",
            "kraken_time:clock-1",
        ],
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "eligible_for_action": True,
        "action": False,
        "accounting": False,
        "learning": False,
    }


def _terminal_receipt() -> dict:
    now = time.time()
    return {
        "provider": "kraken",
        "venue": "kraken",
        "provider_receipt_type": "QueryOrders",
        "orderId": "OID-1",
        "symbol": "SOLUSD",
        "side": "BUY",
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "reconciliation_required": False,
        "filled_qty": 2.0,
        "filled_avg_price": 10.0,
        "filled_notional": 20.0,
        "fee": 0.02,
        "fee_asset": "USD",
        "fee_currency": "USD",
        "source_id": "kraken:/0/private/QueryOrders:OID-1",
        "source_timestamp": now,
        "received_at": now,
        "receipt_id": "kraken_order:terminal-1",
        "input_receipt_ids": ["kraken_trade:T-1"],
        "fills": [{"tradeId": "T-1", "source": "kraken_queryorders"}],
    }


class _Client:
    def __init__(self, status_receipt: dict | None = None) -> None:
        self.status_receipt = status_receipt
        self.place_calls = 0
        self.status_calls = 0
        self.ticker_receipts = {"SOLUSD": _ticker()}
        self.account_receipt = _account_receipt()
        self.ack_receipt = {
            "provider": "kraken",
            "venue": "kraken",
            "provider_receipt_type": "AddOrder",
            "orderId": "OID-1",
            "symbol": "SOLUSD",
            "side": "BUY",
            "type": "MARKET",
            "requestedQty": "2",
            "filled_qty": None,
            "filled_avg_price": None,
            "filled_notional": None,
            "fee": None,
            "fills": None,
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
            "submitted": True,
            "reconciliation_required": True,
            "fill_receipt_complete": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "source_id": "kraken:/0/private/AddOrder:OID-1",
            "received_at": time.time(),
            "receipt_id": "kraken_order_ack:ack-1",
            "input_receipt_ids": [],
        }

    def get_ticker_receipt(self, symbol: str) -> dict:
        receipt = self.ticker_receipts.get(symbol)
        if receipt is None:
            return {"data_status": "no_data", "generated_values": False}
        return dict(receipt)

    def get_account_balance_receipt(self) -> dict:
        return dict(self.account_receipt)

    def place_market_order(self, **_: object) -> dict:
        self.place_calls += 1
        return dict(self.ack_receipt)

    def get_order_status(self, order_id: str) -> dict | None:
        assert order_id == "OID-1"
        self.status_calls += 1
        return dict(self.status_receipt) if self.status_receipt else None


def _adapter(client: _Client) -> tuple[KrakenTradingAdapter, list[dict]]:
    adapter = KrakenTradingAdapter.__new__(KrakenTradingAdapter)
    adapter.client = client
    adapter.tracked_positions = {}
    adapter._pending_orders = {}
    saved: list[dict] = []
    adapter._save_positions = lambda: saved.append(dict(adapter.tracked_positions))
    return adapter, saved


def test_ticker_requires_complete_fresh_provider_receipt() -> None:
    client = _Client()
    adapter, _ = _adapter(client)

    assert adapter.get_ticker("SOL/USD")["price"] == 100.0

    client.ticker_receipts["SOLUSD"] = _ticker(generated=True)
    assert adapter.get_ticker("SOL/USD") is None

    client.ticker_receipts["SOLUSD"] = _ticker(age=301.0)
    assert adapter.get_ticker("SOL/USD") is None


def test_account_requires_complete_balance_and_every_non_usd_quote() -> None:
    client = _Client()
    client.account_receipt = _account_receipt(
        {"USD": 50.0, "USDT": 10.0, "SOL": 2.0}
    )
    client.ticker_receipts["USDTUSD"] = _ticker("USDTUSD", price=0.999)
    adapter, _ = _adapter(client)

    account = adapter.get_account()

    assert account["data_status"] == "live"
    assert account["cash"] == 50.0
    assert account["equity"] == 50.0 + 10.0 * 0.999 + 2.0 * 100.0
    assert account["receipt_id"].startswith("kraken_adapter_account:")
    assert set(account["input_receipt_ids"]) == {
        "kraken_balance:account-1",
        "kraken_ticker:usdtusd",
        "kraken_ticker:solusd",
    }

    client.ticker_receipts.pop("USDTUSD")
    blocked = adapter.get_account()
    assert blocked["data_status"] == "no_data"
    assert "equity" not in blocked


def test_positions_never_fabricate_or_write_first_seen_cost_basis() -> None:
    client = _Client()
    adapter, saved = _adapter(client)

    assert adapter.get_positions() == []
    assert adapter.tracked_positions == {}
    assert saved == []


def test_ack_is_pending_and_terminal_readback_is_the_only_mutation() -> None:
    client = _Client(_terminal_receipt())
    adapter, saved = _adapter(client)

    pending = adapter.place_order("SOL/USD", 2.0, "buy")
    assert pending["status"] == "pending_reconciliation"
    assert client.place_calls == 1
    assert client.status_calls == 0
    assert adapter.tracked_positions == {}
    assert saved == []

    filled = adapter.place_order("SOL/USD", 2.0, "buy")
    assert filled["status"] == "FILLED"
    assert client.place_calls == 1
    assert client.status_calls == 1
    assert adapter.tracked_positions["SOL"]["entry_order_id"] == "OID-1"
    assert adapter.tracked_positions["SOL"]["entry_trade_ids"] == ["T-1"]
    assert filled["receipt_id"].startswith("kraken_adapter_terminal_order:")
    assert filled["provider_receipt_id"] == "kraken_order:terminal-1"
    assert filled["input_receipt_ids"] == [
        "kraken_order_ack:ack-1",
        "kraken_order:terminal-1",
        "kraken_trade:T-1",
    ]
    assert len(saved) == 1

    positions = adapter.get_positions()
    assert len(positions) == 1
    assert positions[0]["avg_entry_price"] == 10.0
    assert positions[0]["receipt_id"].startswith("kraken_adapter_position:")
    assert len(saved) == 1


def test_incomplete_readback_stays_pending_without_mutation_or_resubmit() -> None:
    client = _Client({"orderId": "OID-1", "status": "open"})
    adapter, saved = _adapter(client)

    adapter.place_order("SOL/USD", 2.0, "buy")
    result = adapter.place_order("SOL/USD", 2.0, "buy")

    assert result["status"] == "pending_reconciliation"
    assert client.place_calls == 1
    assert client.status_calls == 1
    assert adapter.tracked_positions == {}
    assert saved == []

    again = adapter.place_order("SOL/USD", 2.0, "buy")
    assert again["reason"] == "single_provider_readback_exhausted_external_reconciliation_required"
    assert client.place_calls == 1
    assert client.status_calls == 1
    assert saved == []


def test_terminal_shaped_ack_cannot_mutate_or_trigger_same_call_readback() -> None:
    client = _Client(_terminal_receipt())
    client.ack_receipt = _terminal_receipt()
    adapter, saved = _adapter(client)

    pending = adapter.place_order("SOL/USD", 2.0, "buy")

    assert pending["status"] == "pending_reconciliation"
    assert pending["reason"] == "submission_ack_receipt_incomplete"
    assert client.place_calls == 1
    assert client.status_calls == 0
    assert adapter.tracked_positions == {}
    assert saved == []
