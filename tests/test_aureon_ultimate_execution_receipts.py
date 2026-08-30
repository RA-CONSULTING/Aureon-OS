from __future__ import annotations

import importlib
import logging
import time
from typing import Any
from unittest.mock import patch

import pytest

from aureon.core import aureon_baton_link


with (
    patch.object(aureon_baton_link, "link_system", lambda *_args, **_kwargs: None),
    patch.object(logging, "FileHandler", lambda *_args, **_kwargs: logging.NullHandler()),
):
    ultimate = importlib.import_module("aureon.trading.aureon_ultimate")


AureonUltimate = ultimate.AureonUltimate
Position = ultimate.Position
QueenHive = ultimate.QueenHive


class OfflineClient:
    def __init__(
        self,
        *,
        responses: list[Any] | None = None,
        reconciliations: list[Any] | None = None,
        dry_run: bool = False,
    ) -> None:
        self.responses = list(responses or [])
        self.reconciliations = list(reconciliations or [])
        self.dry_run = dry_run
        self.place_calls = 0
        self.query_calls = 0

    def place_market_order(self, symbol: str, side: str, quantity: float) -> dict[str, Any]:
        self.place_calls += 1
        if not self.responses:
            raise AssertionError("unexpected offline order submission")
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    def get_order_status(self, order_id: str) -> dict[str, Any]:
        self.query_calls += 1
        if not self.reconciliations:
            raise AssertionError("unexpected offline order-status query")
        response = self.reconciliations.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class OfflineLotManager:
    def __init__(self) -> None:
        self.cache = {"BTCUSDT": {"base": "BTC", "quote": "USDT"}}

    def format_qty(self, _symbol: str, quantity: float) -> str:
        return f"{float(quantity):.8f}".rstrip("0").rstrip(".")

    def get_min_notional(self, _symbol: str) -> float:
        return 5.0

    def get_min_qty(self, _symbol: str) -> float:
        return 0.00001


class OfflineMemory:
    def __init__(self) -> None:
        self.hunts: list[tuple[str, float, float]] = []
        self.results: list[tuple[str, float]] = []

    def get_win_rate(self) -> float:
        return 0.5

    def record_hunt(self, symbol: str, volume: float, change: float) -> None:
        self.hunts.append((symbol, volume, change))

    def record(self, symbol: str, pnl: float) -> None:
        self.results.append((symbol, pnl))


class OfflineFire:
    def get_size_multiplier(self) -> float:
        return 1.0

    def get_status(self) -> str:
        return "offline"


class OfflineCommandos:
    def __init__(self) -> None:
        self.exits: list[tuple[str, float]] = []

    def record_exit(self, symbol: str, pnl: float) -> None:
        self.exits.append((symbol, pnl))


def make_trader(client: OfflineClient) -> AureonUltimate:
    trader = AureonUltimate.__new__(AureonUltimate)
    trader.client = client
    trader.lot_mgr = OfflineLotManager()
    trader.allowed_quotes = ["USDT"]
    trader.primary_quote = "USDT"
    trader.positions = {}
    trader.pending_executions = {}
    trader.execution_quarantine = {}
    trader.last_execution_result = None
    trader.memory = OfflineMemory()
    trader.fire = OfflineFire()
    trader.hive = QueenHive()
    trader.commandos = OfflineCommandos()
    trader.lighthouse_metrics = {}
    trader.ticker_cache = {}
    trader.trades = 0
    trader.wins = 0
    trader.harvest_total = 0.0
    trader.total_gross_pnl = 0.0
    trader.total_fees = 0.0
    trader.bridge = None
    trader.bridge_enabled = False
    return trader


def opportunity() -> dict[str, Any]:
    return {
        "symbol": "BTCUSDT",
        "price": 100.0,
        "coherence": 0.8,
        "emotion": "LOVE",
        "change": 1.2,
        "volume": 250_000.0,
    }


def binance_fill(
    *,
    order_id: int = 7001,
    side: str = "BUY",
    quantity: str = "0.5",
    quote_cost: str = "50.5",
    price: str = "101",
    commission: str = "0.05",
    commission_asset: str = "USDT",
    provider_time: float | None = None,
    status: str = "FILLED",
) -> dict[str, Any]:
    provider_time = time.time() if provider_time is None else provider_time
    return {
        "symbol": "BTCUSDT",
        "orderId": order_id,
        "side": side,
        "status": status,
        "transactTime": int(provider_time * 1000),
        "executedQty": quantity,
        "cummulativeQuoteQty": quote_cost,
        "fills": [
            {
                "tradeId": order_id + 100,
                "qty": quantity,
                "price": price,
                "commission": commission,
                "commissionAsset": commission_asset,
            }
        ],
    }


def kraken_terminal_fill(
    *,
    order_id: str,
    side: str,
    quantity: str,
    quote_cost: str,
    price: str,
    fee: str,
    status: str = "FILLED",
) -> dict[str, Any]:
    return {
        "symbol": "XBTUSDT",
        "orderId": order_id,
        "side": side,
        "status": status,
        "data_status": "live",
        "truth_status": "real_observed",
        "source_timestamp": time.time(),
        "executedQty": quantity,
        "cummulativeQuoteQty": quote_cost,
        "avgPrice": price,
        "fee": fee,
        "fee_asset": "USDT",
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "reconciliation_required": False,
        "generated_values": False,
    }


def tracked_position(*, quantity: float = 2.0, fees_quote: float = 0.2) -> Position:
    return Position(
        symbol="BTCUSDT",
        entry_price=100.0,
        quantity=quantity,
        entry_time=time.time() - 60,
        coherence=0.8,
        notional_usd=quantity * 100.0,
        fees_quote=fees_quote,
        entry_order_id="ENTRY-1",
        entry_source_timestamp=time.time() - 60,
    )


def test_dry_run_entry_is_not_submitted_and_mutation_free() -> None:
    client = OfflineClient(dry_run=True)
    trader = make_trader(client)

    receipt = trader.enter_position(opportunity(), 1_000.0)

    assert receipt["status"] == "not_submitted"
    assert receipt["data_status"] == "not_submitted"
    assert receipt["truth_status"] == "dry_run"
    assert receipt["eligible_for_accounting"] is False
    assert client.place_calls == 0
    assert trader.positions == {}
    assert trader.total_fees == 0.0
    assert trader.trades == 0
    assert trader.memory.hunts == []


def test_pending_kraken_entry_reconciles_without_duplicate_submission() -> None:
    acknowledgement = {
        "symbol": "BTCUSDT",
        "side": "BUY",
        "orderId": "K-ENTRY-1",
        "status": "pending_reconciliation",
        "data_status": "pending_reconciliation",
        "reconciliation_required": True,
        "generated_values": False,
    }
    client = OfflineClient(
        responses=[acknowledgement],
        reconciliations=[
            kraken_terminal_fill(
                order_id="K-ENTRY-1",
                side="buy",
                quantity="0.5",
                quote_cost="50.5",
                price="101",
                fee="0.05",
            )
        ],
    )
    trader = make_trader(client)

    first = trader.enter_position(opportunity(), 1_000.0)

    assert first["status"] == "pending_reconciliation"
    assert client.place_calls == 1
    assert trader.positions == {}
    assert trader.total_fees == 0.0
    assert trader.memory.hunts == []

    second = trader.enter_position(opportunity(), 1_000.0)

    assert second is True
    assert client.place_calls == 1
    assert client.query_calls == 1
    assert trader.positions["BTCUSDT"].entry_price == pytest.approx(101.0)
    assert trader.positions["BTCUSDT"].quantity == pytest.approx(0.5)
    assert trader.positions["BTCUSDT"].notional_usd == pytest.approx(50.5)
    assert trader.positions["BTCUSDT"].fees_quote == pytest.approx(0.05)
    assert trader.positions["BTCUSDT"].entry_order_id == "K-ENTRY-1"
    assert trader.total_fees == pytest.approx(0.05)
    assert trader.trades == 1
    assert len(trader.memory.hunts) == 1


def test_ambiguous_submission_suppresses_all_duplicate_attempts() -> None:
    client = OfflineClient(responses=[TimeoutError("offline ambiguous timeout")])
    trader = make_trader(client)

    first = trader.enter_position(opportunity(), 1_000.0)
    second = trader.enter_position(opportunity(), 1_000.0)

    assert first["status"] == "pending_reconciliation"
    assert first["reason"] == "submission_outcome_ambiguous"
    assert second["status"] == "pending_reconciliation"
    assert client.place_calls == 1
    assert client.query_calls == 0
    assert trader.positions == {}
    assert trader.total_fees == 0.0
    assert trader.memory.hunts == []


@pytest.mark.parametrize(
    "provider_receipt, expected_reason",
    [
        (
            binance_fill(provider_time=time.time() - 600),
            "missing_stale_or_future_provider_fill_timestamp",
        ),
        (
            binance_fill(commission_asset="BNB"),
            "provider_fee_conversion_receipt_required",
        ),
    ],
)
def test_stale_or_unconvertible_entry_receipt_is_quarantined_without_mutation(
    provider_receipt: dict[str, Any],
    expected_reason: str,
) -> None:
    client = OfflineClient(responses=[provider_receipt])
    trader = make_trader(client)

    receipt = trader.enter_position(opportunity(), 1_000.0)

    assert receipt["status"] == "pending_reconciliation"
    assert receipt["reason"] == expected_reason
    assert receipt["eligible_for_accounting"] is False
    assert trader.positions == {}
    assert trader.total_fees == 0.0
    assert trader.trades == 0
    assert trader.memory.hunts == []
    assert "BTCUSDT:BUY" in trader.execution_quarantine


def test_binance_terminal_entry_uses_provider_fill_not_requested_values() -> None:
    client = OfflineClient(
        responses=[
            binance_fill(
                order_id=7123,
                quantity="0.4",
                quote_cost="42",
                price="105",
                commission="0.04",
            )
        ]
    )
    trader = make_trader(client)

    entered = trader.enter_position(opportunity(), 1_000.0)

    assert entered is True
    position = trader.positions["BTCUSDT"]
    assert position.entry_price == pytest.approx(105.0)
    assert position.quantity == pytest.approx(0.4)
    assert position.notional_usd == pytest.approx(42.0)
    assert position.fees_quote == pytest.approx(0.04)
    assert position.entry_order_id == "7123"
    assert trader.total_fees == pytest.approx(0.04)


def test_dry_run_force_exit_keeps_position_and_learning_unchanged() -> None:
    client = OfflineClient(dry_run=True)
    trader = make_trader(client)
    trader.positions["BTCUSDT"] = tracked_position()
    trader.ticker_cache["BTCUSDT"] = {"lastPrice": "999"}
    trader.total_fees = 0.2

    receipt = trader.force_exit_position("BTCUSDT", "offline_check")

    assert receipt["status"] == "not_submitted"
    assert client.place_calls == 0
    assert trader.positions["BTCUSDT"].quantity == pytest.approx(2.0)
    assert trader.total_gross_pnl == 0.0
    assert trader.total_fees == pytest.approx(0.2)
    assert trader.memory.results == []
    assert trader.hive.total_profit == 0.0


def test_pending_exit_reconciles_once_then_accounts_only_provider_fill() -> None:
    acknowledgement = {
        "symbol": "BTCUSDT",
        "side": "SELL",
        "orderId": "K-EXIT-1",
        "status": "pending_reconciliation",
        "data_status": "pending_reconciliation",
        "reconciliation_required": True,
        "generated_values": False,
    }
    client = OfflineClient(
        responses=[acknowledgement],
        reconciliations=[
            kraken_terminal_fill(
                order_id="K-EXIT-1",
                side="sell",
                quantity="2",
                quote_cost="220",
                price="110",
                fee="0.22",
            )
        ],
    )
    trader = make_trader(client)
    trader.positions["BTCUSDT"] = tracked_position()
    # Deliberately unrelated ticker price: accounting must use the receipt.
    trader.ticker_cache["BTCUSDT"] = {"lastPrice": "999"}
    trader.total_fees = 0.2

    first = trader.force_exit_position("BTCUSDT", "bridge_force_exit")

    assert first["status"] == "pending_reconciliation"
    assert client.place_calls == 1
    assert trader.positions["BTCUSDT"].quantity == pytest.approx(2.0)
    assert trader.total_gross_pnl == 0.0
    assert trader.total_fees == pytest.approx(0.2)
    assert trader.memory.results == []

    second = trader.force_exit_position("BTCUSDT", "bridge_force_exit")

    assert second is True
    assert client.place_calls == 1
    assert client.query_calls == 1
    assert "BTCUSDT" not in trader.positions
    assert trader.total_gross_pnl == pytest.approx(20.0)
    assert trader.total_fees == pytest.approx(0.42)
    assert trader.hive.total_profit == pytest.approx(19.58)
    assert trader.memory.results == [("BTCUSDT", pytest.approx(19.58))]
    assert trader.wins == 1
    assert len(trader.commandos.exits) == 1


def test_raw_nonterminal_partial_fill_does_not_mutate_position() -> None:
    client = OfflineClient(
        responses=[
            binance_fill(
                order_id=7444,
                side="SELL",
                quantity="1",
                quote_cost="110",
                price="110",
                commission="0.11",
                status="PARTIALLY_FILLED",
            )
        ]
    )
    trader = make_trader(client)
    trader.positions["BTCUSDT"] = tracked_position()
    trader.ticker_cache["BTCUSDT"] = {"lastPrice": "110"}
    trader.total_fees = 0.2

    receipt = trader.force_exit_position("BTCUSDT", "partial_provider_state")

    assert receipt["status"] == "pending_reconciliation"
    assert receipt["reason"] == "nonterminal_partial_fill_requires_reconciliation"
    assert trader.positions["BTCUSDT"].quantity == pytest.approx(2.0)
    assert trader.total_gross_pnl == 0.0
    assert trader.total_fees == pytest.approx(0.2)
    assert trader.memory.results == []


def test_hardened_terminal_partial_fill_accounts_only_observed_quantity() -> None:
    client = OfflineClient(
        responses=[
            kraken_terminal_fill(
                order_id="K-PARTIAL-1",
                side="sell",
                quantity="1",
                quote_cost="110",
                price="110",
                fee="0.11",
                status="PARTIALLY_FILLED",
            )
        ]
    )
    trader = make_trader(client)
    trader.positions["BTCUSDT"] = tracked_position()
    trader.ticker_cache["BTCUSDT"] = {"lastPrice": "999"}
    trader.total_fees = 0.2

    receipt = trader.force_exit_position("BTCUSDT", "terminal_partial")

    assert receipt["status"] == "partially_filled"
    assert receipt["fully_closed"] is False
    assert trader.positions["BTCUSDT"].quantity == pytest.approx(1.0)
    assert trader.positions["BTCUSDT"].fees_quote == pytest.approx(0.1)
    assert trader.total_gross_pnl == pytest.approx(10.0)
    assert trader.total_fees == pytest.approx(0.31)
    assert trader.hive.total_profit == pytest.approx(9.79)
    assert trader.memory.results == [("BTCUSDT", pytest.approx(9.79))]
