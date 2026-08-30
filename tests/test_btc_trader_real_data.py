from __future__ import annotations

import time
from typing import Any

import pytest

import aureon.trading.aureon_btc_trader as btc_module
from aureon.trading.aureon_btc_trader import AureonBTCTrader


class _Provider:
    def __init__(self) -> None:
        self.now = time.time()
        self.test_price = 0.01
        self.account_timestamp = self.now
        self.ticker_timestamp = self.now
        self.order_responses: list[dict[str, Any]] = []
        self.order_calls: list[tuple[str, str, float]] = []

    def exchange_info(self) -> dict[str, Any]:
        return {
            "symbols": [
                {
                    "symbol": "TESTBTC",
                    "status": "TRADING",
                    "baseAsset": "TEST",
                    "quoteAsset": "BTC",
                    "permissionSets": [["TRD_GRP_039"]],
                    "filters": [
                        {
                            "filterType": "LOT_SIZE",
                            "stepSize": "0.001",
                            "minQty": "0.001",
                        }
                    ],
                }
            ]
        }

    def get_24h_tickers(self) -> list[dict[str, Any]]:
        close_time = int(self.ticker_timestamp * 1000)
        return [
            {
                "symbol": "BTCUSDT",
                "lastPrice": "100000",
                "priceChangePercent": "1",
                "quoteVolume": "1000",
                "closeTime": close_time,
            },
            {
                "symbol": "TESTBTC",
                "lastPrice": str(self.test_price),
                "priceChangePercent": "6",
                "quoteVolume": "3",
                "closeTime": close_time,
            },
        ]

    def account(self) -> dict[str, Any]:
        return {
            "updateTime": int(self.account_timestamp * 1000),
            "balances": [
                {"asset": "BTC", "free": "1", "locked": "0"},
                {"asset": "TEST", "free": "0", "locked": "0"},
            ],
        }

    def place_market_order(
        self,
        symbol: str,
        side: str,
        *,
        quantity: float,
    ) -> dict[str, Any]:
        self.order_calls.append((symbol, side, quantity))
        return self.order_responses.pop(0)


def _fill(
    *,
    side: str,
    qty: float,
    price: float,
    order_id: int,
    commission: float,
    commission_asset: str,
) -> dict[str, Any]:
    return {
        "symbol": "TESTBTC",
        "side": side,
        "status": "FILLED",
        "orderId": order_id,
        "transactTime": int(time.time() * 1000),
        "executedQty": str(qty),
        "cummulativeQuoteQty": str(qty * price),
        "fills": [
            {
                "price": str(price),
                "qty": str(qty),
                "commission": str(commission),
                "commissionAsset": commission_asset,
            }
        ],
    }


def test_stale_provider_data_is_explicit_no_data() -> None:
    provider = _Provider()
    provider.ticker_timestamp = time.time() - 1000
    provider.account_timestamp = time.time() - 1000
    trader = AureonBTCTrader(client=provider)

    assert trader.update_tickers() is False
    assert trader.ticker_cache == {}
    assert trader.get_balances() is None
    assert trader.data_status == "no_data"


def test_dry_run_and_pending_ack_do_not_create_positions() -> None:
    provider = _Provider()
    dry_run = AureonBTCTrader(dry_run=True, client=provider)
    assert dry_run.update_tickers() is True
    pairs = dry_run.scan_btc_pairs()

    assert dry_run.trade_btc_pairs(pairs) == []
    assert provider.order_calls == []
    assert dry_run.positions == {}
    assert dry_run.total_profit_btc == 0.0
    assert dry_run.execution_receipts[-1]["status"] == "NOT_SUBMITTED"

    provider.order_responses.append(
        {
            "symbol": "TESTBTC",
            "side": "BUY",
            "status": "NEW",
            "orderId": 99,
            "transactTime": int(time.time() * 1000),
        }
    )
    pending = AureonBTCTrader(client=provider)
    assert pending.update_tickers() is True
    assert pending.trade_btc_pairs(pending.scan_btc_pairs()) == []
    assert pending.positions == {}
    assert pending.total_profit_btc == 0.0
    assert pending.reconciliation_required[-1]["status"] == "PENDING_RECONCILIATION"


def test_verified_fills_drive_position_and_exact_btc_pnl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(btc_module, "PENNY_PROFIT_AVAILABLE", False)
    provider = _Provider()
    provider.order_responses.append(
        _fill(
            side="BUY",
            qty=25.0,
            price=0.01,
            order_id=101,
            commission=0.025,
            commission_asset="TEST",
        )
    )
    trader = AureonBTCTrader(client=provider)
    assert trader.update_tickers() is True

    entries = trader.trade_btc_pairs(trader.scan_btc_pairs())

    assert len(entries) == 1
    assert trader.positions["TESTBTC"]["qty"] == pytest.approx(24.975)
    assert trader.positions["TESTBTC"]["entry_value"] == pytest.approx(0.25)

    provider.test_price = 0.011
    provider.ticker_timestamp = time.time()
    trader.last_ticker_update = 0
    assert trader.update_tickers() is True
    provider.order_responses.append(
        _fill(
            side="SELL",
            qty=24.975,
            price=0.011,
            order_id=102,
            commission=0.0001,
            commission_asset="BTC",
        )
    )

    exits = trader.check_exits()

    assert len(exits) == 1
    assert trader.positions == {}
    assert trader.total_profit_btc == pytest.approx(0.024625)
    assert trader.last_realized_pnl["data_status"] == "live"
    assert trader.last_realized_pnl["generated_values"] is False
