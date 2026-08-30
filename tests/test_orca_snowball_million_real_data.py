from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from aureon.bots.orca_snowball_million import QueenSnowball
from scripts.validation.validate_real_data_contract import scan_text_file


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aureon" / "bots" / "orca_snowball_million.py"


def _opportunity(exchange: str, symbol: str, price: float = 10.0) -> dict[str, Any]:
    return {
        "exchange": exchange,
        "symbol": symbol,
        "action": "BUY",
        "price": price,
        "score": 4.0,
        "source_id": f"{exchange}:ticker:{symbol}",
        "source_timestamp": time.time(),
        "data_status": "live",
        "generated_values": False,
        "eligible_for_action": True,
    }


class _Kraken:
    def __init__(self) -> None:
        self.balances: dict[str, float] = {"USD": 100.0}
        self.submission: dict[str, Any] = {
            "status": "pending_reconciliation",
            "orderId": "K-1",
        }
        self.terminal: dict[str, Any] = dict(self.submission)
        self.orders: list[tuple[str, str, float]] = []

    def get_balance(self) -> dict[str, float]:
        return dict(self.balances)

    def get_24h_ticker(self, symbol: str) -> dict[str, Any]:
        return {}

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
    ) -> dict[str, Any]:
        self.orders.append((symbol, side, quantity))
        return dict(self.submission)

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        assert order_id == "K-1"
        return dict(self.terminal)


class _Binance:
    def __init__(self) -> None:
        self.allowed = False
        self.orders: list[tuple[str, str, float]] = []

    def get_balance(self) -> dict[str, float]:
        return {"USDT": 100.0}

    def get_asset_balance(self, asset: str) -> dict[str, Any]:
        assert asset == "USDT"
        return {
            "asset": "USDT",
            "free": 100.0,
            "locked": 0.0,
            "source_timestamp": time.time(),
            "data_status": "live",
            "generated_values": False,
            "eligible_for_action": True,
        }

    def get_24h_tickers(self) -> list[dict[str, Any]]:
        return [
            {
                "symbol": "TESTUSDT",
                "lastPrice": "10",
                "priceChangePercent": "20",
                "quoteVolume": "2000000",
                "closeTime": int(time.time() * 1000),
            }
        ]

    def can_trade_symbol(self, symbol: str) -> tuple[bool, str]:
        return self.allowed, "provider permission"

    def adjust_quantity(self, symbol: str, quantity: float) -> float:
        return quantity

    def place_market_order(
        self,
        symbol: str,
        side: str,
        *,
        quantity: float,
    ) -> dict[str, Any]:
        self.orders.append((symbol, side, quantity))
        return {
            "symbol": symbol,
            "side": side,
            "status": "FILLED",
            "orderId": 77,
            "transactTime": int(time.time() * 1000),
            "executedQty": str(quantity),
            "cummulativeQuoteQty": str(quantity * 10.0),
            "fills": [
                {
                    "price": "10",
                    "qty": str(quantity),
                    "commission": "0.05",
                    "commissionAsset": "USDT",
                }
            ],
        }


def _snowball(kraken: _Kraken, binance: _Binance | None = None) -> QueenSnowball:
    return QueenSnowball(
        kraken=kraken,
        binance=binance,
        connect_clients=False,
        wire_queen=False,
    )


def test_missing_fx_receipt_is_no_data_not_fixed_conversion() -> None:
    kraken = _Kraken()
    kraken.balances = {"GBP": 100.0}
    snowball = _snowball(kraken)

    assert snowball.get_total_portfolio_usd() is None
    assert snowball.data_status == "no_data"
    assert "valuation_receipt_unavailable" in snowball.no_data_reason


def test_permission_tuple_and_fresh_ticker_gate_binance_scan() -> None:
    kraken = _Kraken()
    binance = _Binance()
    snowball = _snowball(kraken, binance)

    assert snowball.scan_binance_momentum() == []
    binance.allowed = True
    opportunities = snowball.scan_binance_momentum()

    assert len(opportunities) == 1
    assert opportunities[0]["source_timestamp"] <= time.time()
    assert opportunities[0]["generated_values"] is False


def test_kraken_submission_ack_is_pending_and_cannot_mutate_state() -> None:
    kraken = _Kraken()
    snowball = _snowball(kraken)

    receipt = snowball.execute_trade(_opportunity("kraken", "ETHUSD", 50.0))

    assert receipt["status"] == "PENDING_RECONCILIATION"
    assert snowball.state.trades_executed == 0
    assert snowball.state.wins == 0
    assert snowball.state.total_profit == 0
    assert len(snowball.reconciliation_required) == 1

    kraken.submission = {
        "status": "not_submitted",
        "dryRun": True,
    }
    not_submitted = _snowball(kraken)
    dry_receipt = not_submitted.execute_trade(
        _opportunity("kraken", "ETHUSD", 50.0)
    )
    assert dry_receipt["status"] == "NOT_SUBMITTED"
    assert not_submitted.reconciliation_required == []
    assert not_submitted.state.trades_executed == 0


def test_complete_kraken_fill_records_execution_but_not_unproved_profit() -> None:
    kraken = _Kraken()
    kraken.terminal = {
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "generated_values": False,
        "provider_timestamp": time.time(),
        "executedQty": "1",
        "filled_avg_price": "50",
        "cummulativeQuoteQty": "50",
        "fee": "0.10",
        "fee_asset": "USD",
        "side": "BUY",
        "orderId": "K-1",
    }
    snowball = _snowball(kraken)

    receipt = snowball.execute_trade(_opportunity("kraken", "ETHUSD", 50.0))

    assert receipt["status"] == "FILLED"
    assert receipt["fees_by_asset"] == {"USD": pytest.approx(0.10)}
    assert snowball.state.trades_executed == 1
    assert snowball.state.wins == 0
    assert snowball.state.total_profit == 0
    assert snowball.state.last_trade


def test_binance_fill_is_complete_and_profit_branch_is_inert() -> None:
    kraken = _Kraken()
    binance = _Binance()
    binance.allowed = True
    snowball = _snowball(kraken, binance)

    receipt = snowball.execute_trade(_opportunity("binance", "TESTUSDT"))
    profit_result = snowball.check_positions_for_profit()

    assert receipt["status"] == "FILLED"
    assert receipt["fees_by_asset"] == {"USDT": pytest.approx(0.05)}
    assert snowball.state.trades_executed == 1
    assert snowball.state.wins == 0
    assert snowball.state.total_profit == 0
    assert profit_result["status"] == "NO_DATA"
    assert len(binance.orders) == 1
    assert kraken.orders == []


def test_scoped_runtime_file_has_no_real_data_validator_findings() -> None:
    assert scan_text_file(TARGET, ROOT) == []
