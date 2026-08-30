from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from aureon.exchanges.kraken_margin_penny_trader import (
    ActiveTrade,
    KrakenMarginArmyTrader,
    MarginPairInfo,
)
from scripts.validation.validate_real_data_contract import scan_text_file


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aureon" / "exchanges" / "kraken_margin_penny_trader.py"


class _Client:
    def __init__(
        self,
        *,
        open_submission: dict[str, Any] | None = None,
        close_submission: dict[str, Any] | None = None,
        readback: dict[str, Any] | None = None,
    ) -> None:
        self.open_submission = open_submission
        self.close_submission = close_submission
        self.readback = readback
        self.open_calls = 0
        self.close_calls = 0
        self.status_calls = 0

    def place_margin_order(self, **_kwargs: Any) -> dict[str, Any]:
        self.open_calls += 1
        assert self.open_submission is not None
        return dict(self.open_submission)

    def close_margin_position(self, **_kwargs: Any) -> dict[str, Any]:
        self.close_calls += 1
        assert self.close_submission is not None
        return dict(self.close_submission)

    def get_order_status(self, _order_id: str) -> dict[str, Any]:
        self.status_calls += 1
        assert self.readback is not None
        return dict(self.readback)


def _submission(order_id: str) -> dict[str, Any]:
    return {
        "status": "pending_reconciliation",
        "data_status": "pending_reconciliation",
        "truth_status": "real_observed",
        "orderId": order_id,
        "generated_values": False,
    }


def _pending(order_id: str) -> dict[str, Any]:
    return {
        **_submission(order_id),
        "status": "PENDING_RECONCILIATION",
    }


def _fill(
    order_id: str,
    side: str,
    *,
    quantity: float,
    price: float,
    fee: float,
    timestamp: float | None = None,
) -> dict[str, Any]:
    source_timestamp = time.time() if timestamp is None else timestamp
    return {
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "orderId": order_id,
        "side": side.upper(),
        "provider_timestamp": source_timestamp,
        "source_id": f"kraken_order:{order_id}",
        "executedQty": str(quantity),
        "filled_avg_price": str(price),
        "cummulativeQuoteQty": str(quantity * price),
        "fee": str(fee),
        "fee_asset": "USD",
        "fills": [{"tradeId": f"trade-{order_id}"}],
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "generated_values": False,
    }


def _pair() -> MarginPairInfo:
    return MarginPairInfo(
        pair="ETHUSD",
        internal="XETHZUSD",
        base="XETH",
        base_clean="ETH",
        quote="ZUSD",
        leverage_buy=[2],
        leverage_sell=[2],
        max_leverage=2,
        ordermin=0.01,
        costmin=1.0,
        lot_decimals=8,
        price_decimals=2,
    )


def _trader(client: _Client, *, dry_run: bool = False) -> tuple[KrakenMarginArmyTrader, list[str]]:
    trader = KrakenMarginArmyTrader.__new__(KrakenMarginArmyTrader)
    trader.client = client
    trader.dry_run = dry_run
    trader.active_long = None
    trader.active_short = None
    trader.active_trade = None
    trader.completed_trades = []
    trader.total_profit = 0.0
    trader.total_trades = 0
    trader.winning_trades = 0
    trader._unresolved_open_submissions = {}
    trader._unresolved_close_submissions = {}
    trader._last_execution_receipt = {}
    trader._goal_recorder = None
    trader._pending_scan_id = ""
    trader.orchestrator = None
    trader._fast_profit_capture_by_order = {}
    saves: list[str] = []
    trader._save_state = lambda: saves.append("save")
    trader._push_dashboard_state = lambda **_kwargs: None
    trader._start_stream_for = lambda _symbol: None
    trader._verify_trade_cognition = lambda *_args, **_kwargs: {}
    trader._build_trade_cognition_plan = lambda **_kwargs: {}
    trader._get_open_close_fee_rates = lambda _pair_name: (0.01, 0.01)
    trader._fresh_provider_quote = lambda _pair_name: {
        "price": 50.0,
        "source_id": "kraken_quote:ETHUSD",
        "source_timestamp": time.time(),
    }
    trader._get_margin_capital = lambda **_kwargs: SimpleNamespace(free_margin=1000.0)
    return trader, saves


def test_pending_open_is_latched_and_duplicate_submission_is_suppressed() -> None:
    client = _Client(
        open_submission=_submission("K-OPEN"),
        readback=_pending("K-OPEN"),
    )
    trader, saves = _trader(client)

    assert trader.open_position(_pair(), "buy", 2.0, 2, profit_target_usd=1.0) is None
    assert trader.open_position(_pair(), "buy", 2.0, 2, profit_target_usd=1.0) is None

    assert client.open_calls == 1
    assert client.status_calls == 2
    assert trader.active_long is None
    assert trader.total_trades == 0
    assert trader.total_profit == 0.0
    assert saves == []
    assert trader._last_execution_receipt["data_status"] == "pending_reconciliation"


def test_terminal_open_fill_commits_exact_provider_values() -> None:
    provider_time = time.time()
    client = _Client(
        open_submission=_submission("K-OPEN"),
        readback=_fill(
            "K-OPEN",
            "buy",
            quantity=2.0,
            price=50.0,
            fee=0.2,
            timestamp=provider_time,
        ),
    )
    trader, saves = _trader(client)

    trade = trader.open_position(_pair(), "buy", 2.0, 2, profit_target_usd=1.0)

    assert trade is trader.active_long
    assert trade is not None
    assert trade.entry_price == pytest.approx(50.0)
    assert trade.cost == pytest.approx(100.0)
    assert trade.entry_fee == pytest.approx(0.2)
    assert trade.entry_fee_asset == "USD"
    assert trade.entry_source_timestamp == pytest.approx(provider_time)
    assert trade.entry_fill_receipt_complete is True
    assert client.open_calls == 1
    assert client.status_calls == 1
    assert saves == ["save"]


def test_pending_close_never_clears_or_accounts_and_is_not_resubmitted() -> None:
    client = _Client(
        close_submission=_submission("K-CLOSE"),
        readback=_pending("K-CLOSE"),
    )
    trader, saves = _trader(client)
    trade = ActiveTrade(
        pair="ETHUSD",
        side="buy",
        volume=2.0,
        entry_price=50.0,
        leverage=2,
        entry_fee=0.2,
        entry_time=time.time() - 10,
        order_id="K-OPEN",
        cost=100.0,
    )
    trader.active_long = trade
    trader.active_trade = trade

    assert trader.close_position(trade=trade) is None
    assert trader.close_position(trade=trade) is None

    assert client.close_calls == 1
    assert client.status_calls == 2
    assert trader.active_long is trade
    assert trader.completed_trades == []
    assert trader.total_trades == 0
    assert trader.total_profit == 0.0
    assert saves == []


def test_terminal_close_fill_is_the_only_accounting_boundary() -> None:
    entry_time = time.time() - 10
    client = _Client(
        close_submission=_submission("K-CLOSE"),
        readback=_fill("K-CLOSE", "sell", quantity=2.0, price=55.0, fee=0.3),
    )
    trader, saves = _trader(client)
    trade = ActiveTrade(
        pair="ETHUSD",
        side="buy",
        volume=2.0,
        entry_price=50.0,
        leverage=2,
        entry_fee=0.2,
        entry_time=entry_time,
        order_id="K-OPEN",
        cost=100.0,
        entry_source_id="kraken_order:K-OPEN",
        entry_source_timestamp=entry_time,
        entry_fee_asset="USD",
        entry_fill_receipt_complete=True,
    )
    trader.active_long = trade
    trader.active_trade = trade

    completed = trader.close_position(trade=trade)

    assert completed is not None
    assert completed["accounting_status"] == "live"
    assert completed["net_pnl"] == pytest.approx(9.5)
    assert trader.active_long is None
    assert trader.total_trades == 1
    assert trader.winning_trades == 1
    assert trader.total_profit == pytest.approx(9.5)
    assert saves == ["save"]


def test_dry_run_is_not_submitted_and_mutates_nothing() -> None:
    client = _Client()
    trader, saves = _trader(client, dry_run=True)

    assert trader.open_position(_pair(), "buy", 2.0, 2) is None

    assert client.open_calls == 0
    assert client.status_calls == 0
    assert trader.active_long is None
    assert trader._last_execution_receipt["data_status"] == "not_submitted"
    assert saves == []


def test_runtime_target_has_no_hardened_validator_findings() -> None:
    assert scan_text_file(TARGET, ROOT) == []
