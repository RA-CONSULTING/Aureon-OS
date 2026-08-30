from __future__ import annotations

import time

import pytest

from aureon.portfolio.aureon_profit_mesh import ProfitMeshTrader


def ticker(now: float, price: float = 100.0) -> dict:
    return {
        "symbol": "BTCUSDT",
        "lastPrice": str(price),
        "volume": "42.5",
        "highPrice": str(max(price, 105.0)),
        "lowPrice": "95.0",
        "priceChangePercent": "1.25",
        "closeTime": int(now * 1000),
    }


def order(
    now: float,
    side: str,
    price: float,
    quantity: float,
    commission: float,
    commission_asset: str,
    *,
    order_id: int,
    trade_id: int,
) -> dict:
    return {
        "symbol": "BTCUSDT",
        "side": side,
        "status": "FILLED",
        "orderId": order_id,
        "transactTime": int(now * 1000),
        "executedQty": str(quantity),
        "cummulativeQuoteQty": str(price * quantity),
        "fills": [
            {
                "tradeId": trade_id,
                "price": str(price),
                "qty": str(quantity),
                "commission": str(commission),
                "commissionAsset": commission_asset,
            }
        ],
    }


class ProviderClient:
    dry_run = False
    use_testnet = False

    def __init__(self, now: float, orders: list[dict] | None = None):
        self.now = now
        self.ticker = ticker(now)
        self.orders = list(orders or [])
        self.order_calls: list[dict] = []
        self.account_payload = {
            "balances": [
                {"asset": "USDT", "free": "100.0", "locked": "0.0"},
                {"asset": "BTC", "free": "0.0", "locked": "0.0"},
            ]
        }
        self.exchange_payload = {
            "serverTime": int(now * 1000),
            "symbols": [
                {
                    "status": "TRADING",
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                },
                {
                    "status": "TRADING",
                    "symbol": "BTCUSDC",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDC",
                },
            ],
        }

    def server_time(self):
        return {"serverTime": int(self.now * 1000)}

    def account(self):
        return self.account_payload

    def exchange_info(self):
        return self.exchange_payload

    def get_24h_ticker(self, symbol: str):
        assert symbol == "BTCUSDT"
        return self.ticker

    def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
        self.order_calls.append(
            {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "quote_qty": quote_qty,
            }
        )
        if not self.orders:
            raise AssertionError("unexpected provider order call")
        return self.orders.pop(0)


def ready_trader(
    now: float,
    *,
    dry_run: bool = False,
    orders: list[dict] | None = None,
) -> tuple[ProfitMeshTrader, ProviderClient, dict]:
    client = ProviderClient(now, orders)
    trader = ProfitMeshTrader(dry_run=dry_run, client=client)
    pairs = trader.discover_hot_pairs()
    assert len(pairs) == 1
    return trader, client, pairs[0]


def test_stale_ticker_is_explicit_no_data():
    now = time.time()
    client = ProviderClient(now)
    client.ticker = ticker(now - 121.0)
    trader = ProfitMeshTrader(client=client)

    receipt = trader.get_market_snapshot("BTCUSDT")

    assert receipt["truth_status"] == "no_data"
    assert receipt["price"] is None
    assert receipt["eligible_for_external_action"] is False
    assert receipt["generated_values"] is False


def test_malformed_balance_invalidates_complete_discovery():
    now = time.time()
    client = ProviderClient(now)
    client.account_payload["balances"][0].pop("locked")
    trader = ProfitMeshTrader(client=client)

    assert trader.discover_hot_pairs() == []
    assert trader.last_discovery_receipt["truth_status"] == "no_data"
    assert trader.last_discovery_receipt["pairs"] == []


def test_dry_run_entry_never_creates_a_position_or_fill():
    now = time.time()
    trader, client, pair = ready_trader(now, dry_run=True)

    receipt = trader.enter_position(
        pair["symbol"], pair["quote"], pair["quote_balance"]
    )

    assert receipt["status"] == "not_submitted"
    assert receipt["provider_order_id"] is None
    assert receipt["filled_base_quantity"] is None
    assert receipt["eligible_for_accounting"] is False
    assert trader.positions == {}
    assert trader.trade_count == 0
    assert client.order_calls == []


def test_acknowledgement_without_terminal_fill_is_latched_and_not_retried():
    now = time.time()
    acknowledgement = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "status": "NEW",
        "orderId": 1001,
    }
    trader, client, pair = ready_trader(now, orders=[acknowledgement])

    first = trader.enter_position(
        pair["symbol"], pair["quote"], pair["quote_balance"]
    )
    second = trader.enter_position(
        pair["symbol"], pair["quote"], pair["quote_balance"]
    )

    assert first["status"] == "pending_reconciliation"
    assert second["truth_status"] == "no_data"
    assert trader.positions == {}
    assert "BTCUSDT" in trader.pending_orders
    assert len(client.order_calls) == 1


def test_terminal_buy_uses_observed_quantity_price_fee_and_timestamp():
    now = time.time()
    buy = order(now, "BUY", 100.0, 0.2, 0.02, "USDT", order_id=11, trade_id=21)
    trader, _, pair = ready_trader(now, orders=[buy])

    receipt = trader.enter_position(
        pair["symbol"], pair["quote"], pair["quote_balance"]
    )
    position = trader.positions["BTCUSDT"]

    assert receipt["status"] == "filled"
    assert receipt["position_recorded"] is True
    assert position["qty"] == pytest.approx(0.2)
    assert position["entry_price"] == pytest.approx(100.0)
    assert position["entry_total_cost_quote"] == pytest.approx(20.02)
    assert position["entry_time"] == pytest.approx(now, abs=0.001)
    assert position["provider_order_id"] == "11"


def test_stale_terminal_buy_is_quarantined_without_position():
    now = time.time()
    stale_buy = order(
        now - 301.0,
        "BUY",
        100.0,
        0.2,
        0.02,
        "USDT",
        order_id=12,
        trade_id=22,
    )
    trader, _, pair = ready_trader(now, orders=[stale_buy])

    receipt = trader.enter_position(
        pair["symbol"], pair["quote"], pair["quote_balance"]
    )

    assert receipt["status"] == "pending_reconciliation"
    assert receipt["fill_receipt_complete"] is False
    assert trader.positions == {}


def test_dry_run_exit_never_closes_or_accounts():
    now = time.time()
    trader, _, pair = ready_trader(
        now,
        dry_run=True,
    )
    trader.positions["BTCUSDT"] = {
        "entry_price": 100.0,
        "entry_time": now,
        "size": 20.0,
        "qty": 0.2,
        "base": "BTC",
        "quote": "USDT",
        "entry_quote_commission": 0.02,
        "entry_total_cost_quote": 20.02,
        "eligible_for_accounting": True,
    }

    receipt = trader.exit_position("BTCUSDT", 110.0, "policy")

    assert receipt["status"] == "not_submitted"
    assert receipt["realised_pnl_quote"] is None
    assert "BTCUSDT" in trader.positions
    assert trader.total_profit is None
    assert trader.trade_count == 0


def test_sell_acknowledgement_leaves_position_and_profit_untouched():
    now = time.time()
    buy = order(now, "BUY", 100.0, 0.2, 0.02, "USDT", order_id=31, trade_id=41)
    acknowledgement = {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "status": "NEW",
        "orderId": 32,
    }
    trader, client, pair = ready_trader(now, orders=[buy, acknowledgement])
    trader.enter_position(pair["symbol"], pair["quote"], pair["quote_balance"])
    client.ticker = ticker(now, 110.0)

    receipt = trader.exit_position("BTCUSDT", 110.0, "policy")

    assert receipt["status"] == "pending_reconciliation"
    assert "BTCUSDT" in trader.positions
    assert trader.total_profit is None
    assert trader.trade_count == 0


def test_terminal_exit_accounts_exact_observed_usdt_result():
    now = time.time()
    buy = order(now, "BUY", 100.0, 0.2, 0.02, "USDT", order_id=51, trade_id=61)
    sell = order(now, "SELL", 110.0, 0.2, 0.022, "USDT", order_id=52, trade_id=62)
    trader, client, pair = ready_trader(now, orders=[buy, sell])
    trader.enter_position(pair["symbol"], pair["quote"], pair["quote_balance"])
    client.ticker = ticker(now, 110.0)

    receipt = trader.exit_position("BTCUSDT", 110.0, "policy")

    assert receipt["status"] == "filled"
    assert receipt["accounting_status"] == "accounted"
    assert receipt["realised_pnl_quote"] == pytest.approx(1.958)
    assert trader.total_profit == pytest.approx(1.958)
    assert trader.trade_count == 1
    assert trader.win_count == 1
    assert trader.positions == {}


def test_unconvertible_commission_never_creates_realised_pnl():
    now = time.time()
    buy = order(now, "BUY", 100.0, 0.2, 0.0001, "BNB", order_id=71, trade_id=81)
    sell = order(now, "SELL", 110.0, 0.2, 0.022, "USDT", order_id=72, trade_id=82)
    trader, client, pair = ready_trader(now, orders=[buy, sell])
    entry = trader.enter_position(
        pair["symbol"], pair["quote"], pair["quote_balance"]
    )
    client.ticker = ticker(now, 110.0)

    receipt = trader.exit_position("BTCUSDT", 110.0, "policy")

    assert entry["eligible_for_accounting"] is False
    assert receipt["accounting_status"] == "no_data"
    assert receipt["realised_pnl_quote"] is None
    assert trader.total_profit is None
    assert trader.trade_count == 0
    assert len(trader.unaccounted_exits) == 1
