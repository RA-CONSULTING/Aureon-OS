from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import aureon.bots.orca_unleashed as module


def _account(now: float, **overrides: Any) -> dict[str, Any]:
    receipt = {
        "id": "87b90bb7-88cb-43cc-8e1e-a0d7969a1bd1",
        "currency": "USD",
        "cash": "100.00",
        "buying_power": "100.00",
        "source_id": "alpaca:/v2/account",
        "source_timestamp": now,
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
    }
    receipt.update(overrides)
    return receipt


def _fill(
    now: float,
    *,
    order_id: str,
    symbol: str = "BTCUSD",
    side: str = "buy",
    quantity: float = 0.2,
    price: float = 100.0,
    fee: float = 0.04,
    trade_id: str = "700001",
) -> dict[str, Any]:
    return {
        "provider_order_id": order_id,
        "id": order_id,
        "status": "FILLED",
        "provider_status": "filled",
        "symbol": symbol,
        "side": side,
        "filled_qty": quantity,
        "filled_avg_price": price,
        "filled_notional": quantity * price,
        "fee": fee,
        "fee_currency": "USD",
        "fills": [{"trade_id": trade_id}],
        "source_id": f"alpaca:order:{order_id}",
        "source_timestamp": now,
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
    }


def _hunt(now: float, *, exchange: str = "alpaca") -> module.OrcaHunt:
    market = {
        "kind": "market_quote",
        "status": "live",
        "data_status": "live",
        "truth_status": "real_derived",
        "source_id": f"{exchange}:provider_ticker:BTCUSD",
        "source_timestamp": now,
        "received_at": now + 0.01,
        "action_eligible": True,
        "generated_values": False,
        "position_size_receipt": {
            "kind": "position_size",
            "status": "live",
            "data_status": "live",
            "truth_status": "real_derived",
            "provider": exchange,
            "currency": "USD",
            "size_usd": 20.0,
            "source_id": f"{exchange}:account",
            "source_timestamp": now,
            "received_at": now + 0.01,
            "action_eligible": True,
            "generated_values": False,
        },
    }
    return module.OrcaHunt(
        symbol="BTCUSD",
        exchange=exchange,
        direction="long",
        confidence=0.9,
        entry_price=100.0,
        target_price=101.5,
        stop_price=99.2,
        size_usd=20.0,
        reasoning=["fresh provider receipt"],
        timestamp=now,
        market_receipt=market,
        action_eligible=True,
        source_id=market["source_id"],
        source_timestamp=now,
        received_at=now + 0.01,
        truth_status="real_derived",
        generated_values=False,
    )


def _orca(tmp_path: Path) -> module.OrcaUnleashed:
    orca = module.OrcaUnleashed()
    orca.state_file = tmp_path / "orca-state.json"
    return orca


def test_constructor_is_inert(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def forbidden(name: str):
        def invoke(*_args: Any, **_kwargs: Any) -> Any:
            calls.append(name)
            raise AssertionError(f"constructor invoked {name}")

        return invoke

    monkeypatch.setattr(module, "AureonProbabilityNexus", forbidden("nexus"))
    monkeypatch.setattr(module, "OrcaHuntingGrounds", forbidden("grounds"))
    monkeypatch.setattr(module, "get_real_portfolio_tracker", forbidden("portfolio"))
    monkeypatch.setattr(module, "AlpacaClient", forbidden("alpaca"))
    monkeypatch.setattr(module, "get_kraken_client", forbidden("kraken"))
    monkeypatch.setattr(module, "get_binance_client", forbidden("binance"))
    monkeypatch.chdir(tmp_path)

    orca = module.OrcaUnleashed()

    assert calls == []
    assert orca.alpaca is None
    assert orca.kraken is None
    assert orca.binance is None
    assert not (tmp_path / "orca_unleashed_state.json").exists()


def test_account_and_sizing_require_fresh_currency_specific_receipt(tmp_path: Path) -> None:
    now = time.time()
    orca = _orca(tmp_path)
    orca.alpaca = SimpleNamespace(
        get_account=lambda: _account(now, source_timestamp=None)
    )
    orca.portfolio_tracker = SimpleNamespace(
        get_real_portfolio=lambda: pytest.fail("portfolio fallback is forbidden")
    )

    cash = orca.get_available_cash()
    size = orca.calculate_position_size()

    assert cash["status"] == "no_data"
    assert cash["amount"] is None
    assert cash["action_eligible"] is False
    assert size["status"] == "no_data"
    assert size["size_usd"] is None


def test_cross_venue_or_cross_currency_cash_is_never_reused(tmp_path: Path) -> None:
    now = time.time()
    orca = _orca(tmp_path)
    orca.alpaca = SimpleNamespace(get_account=lambda: _account(now))

    binance_cash = orca.get_available_cash("binance", "USDT")
    kraken_cash = orca.get_available_cash("kraken", "USD")

    assert binance_cash["status"] == "no_data"
    assert binance_cash["amount"] is None
    assert kraken_cash["status"] == "no_data"
    assert kraken_cash["amount"] is None


def test_quote_receipt_separates_source_time_and_labels_midpoint() -> None:
    now = time.time()
    orca = module.OrcaUnleashed()
    quote = orca._normalize_quote_receipt(
        "alpaca",
        "BTC/USD",
        {
            "bid": 99.0,
            "ask": 101.0,
            "last": {"price": 100.0, "source": "provider_quote_midpoint"},
            "source_timestamp": now - 1.0,
            "data_status": "live",
            "truth_status": "real_derived",
            "generated_values": False,
        },
        now=now,
    )

    assert quote["status"] == "live"
    assert quote["price_kind"] == "derived_midpoint"
    assert quote["source_timestamp"] == pytest.approx(now - 1.0)
    assert quote["received_at"] == pytest.approx(now)
    assert quote["source_timestamp"] != quote["received_at"]
    assert quote["confidence_formula"].startswith("sqrt(")
    assert quote["generated_values"] is False


@pytest.mark.parametrize(
    "ticker, reason",
    [
        (
            {
                "bid": 99.0,
                "ask": 101.0,
                "source_timestamp": time.time(),
                "data_status": "live",
                "truth_status": "real_observed",
                "generated_values": False,
            },
            "missing_last",
        ),
        (
            {
                "bid": 99.0,
                "ask": 101.0,
                "price": 100.0,
                "source_timestamp": time.time() - 600.0,
                "data_status": "live",
                "truth_status": "real_observed",
                "generated_values": False,
            },
            "stale",
        ),
    ],
)
def test_quote_missing_or_stale_evidence_is_no_data(
    ticker: dict[str, Any], reason: str
) -> None:
    del reason
    quote = module.OrcaUnleashed()._normalize_quote_receipt(
        "kraken", "XBTUSD", ticker
    )

    assert quote["status"] == "no_data"
    assert quote["action_eligible"] is False
    assert quote["source_timestamp"] is None


class _PendingAlpaca:
    def __init__(self, now: float):
        self.now = now
        self.place_calls = 0
        self.read_calls = 0
        self.reconciled: dict[str, Any] | None = None

    def get_account(self) -> dict[str, Any]:
        return _account(self.now)

    def place_order(self, **_kwargs: Any) -> dict[str, Any]:
        self.place_calls += 1
        return {
            "id": "f0418320-b70d-4ab7-bd65-737f2e8d2af1",
            "status": "accepted",
            "symbol": "BTCUSD",
            "side": "buy",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
        }

    def get_order_with_fees(self, _order_id: str) -> dict[str, Any]:
        self.read_calls += 1
        return self.reconciled or self.place_order_without_count()

    def place_order_without_count(self) -> dict[str, Any]:
        return {
            "id": "f0418320-b70d-4ab7-bd65-737f2e8d2af1",
            "status": "accepted",
            "symbol": "BTCUSD",
            "side": "buy",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "generated_values": False,
        }


def test_pending_ack_is_durable_and_duplicate_submission_is_suppressed(
    tmp_path: Path,
) -> None:
    now = time.time()
    client = _PendingAlpaca(now)
    orca = _orca(tmp_path)
    orca.alpaca = client
    hunt = _hunt(now)

    pending = orca.execute_hunt(hunt, dry_run=False)

    assert pending["status"] == "pending_reconciliation"
    assert pending["eligible_for_learning"] is False
    assert orca.session_trades == 0
    assert orca.trades_this_hour == 0
    assert orca.entry_fill_receipts == {}
    assert client.place_calls == 1
    persisted = json.loads(orca.state_file.read_text(encoding="utf-8"))
    assert persisted["pending_orders"]
    assert "raw_receipt" not in next(iter(persisted["pending_orders"].values()))
    restarted = module.OrcaUnleashed()
    restarted.state_file = orca.state_file
    restarted._load_state()
    assert set(restarted.pending_orders) == set(orca.pending_orders)
    reloaded_pending = next(iter(restarted.pending_orders.values()))
    assert reloaded_pending["status"] == "pending_reconciliation"
    assert reloaded_pending["provider_order_id"] == pending["provider_order_id"]

    client.reconciled = _fill(
        now,
        order_id="f0418320-b70d-4ab7-bd65-737f2e8d2af1",
    )
    filled = orca.execute_hunt(hunt, dry_run=False)

    assert filled["status"] == "FILLED"
    assert client.place_calls == 1
    assert client.read_calls == 2
    assert orca.pending_orders == {}
    assert orca.session_trades == 1
    assert orca.trades_this_hour == 1
    assert orca.entry_fill_receipts["BTCUSD"]["fee"] == pytest.approx(0.04)


def test_stale_or_mismatched_terminal_fill_never_mutates_trade_state(
    tmp_path: Path,
) -> None:
    now = time.time()
    stale = _fill(
        now - 600.0,
        order_id="d1cc34b2-af11-4827-9617-65af1159d7ee",
        symbol="ETHUSD",
    )

    class Client:
        def get_account(self) -> dict[str, Any]:
            return _account(now)

        def place_order(self, **_kwargs: Any) -> dict[str, Any]:
            return stale

        def get_order_with_fees(self, _order_id: str) -> dict[str, Any]:
            return stale

    orca = _orca(tmp_path)
    orca.alpaca = Client()
    receipt = orca.execute_hunt(_hunt(now), dry_run=False)

    assert receipt["status"] == "pending_reconciliation"
    assert orca.session_trades == 0
    assert orca.trades_this_hour == 0
    assert orca.entry_fill_receipts == {}


def test_binance_full_fill_requires_observed_commissions_and_trade_ids(
    tmp_path: Path,
) -> None:
    now = time.time()

    class Binance:
        def place_market_order(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "orderId": 99117,
                "status": "FILLED",
                "symbol": "BTCUSD",
                "side": "BUY",
                "origQty": "0.2",
                "executedQty": "0.2",
                "avg_fill_price": "100",
                "cummulativeQuoteQty": "20",
                "transactTime": int(now * 1000),
                "fills": [
                    {
                        "tradeId": 8081,
                        "commission": "0.04",
                        "commissionAsset": "USD",
                    }
                ],
            }

    orca = _orca(tmp_path)
    orca.alpaca = SimpleNamespace(get_account=lambda: _account(now))
    orca.binance = Binance()

    receipt = orca.execute_hunt(_hunt(now, exchange="binance"), dry_run=False)

    assert receipt["status"] == "FILLED"
    assert receipt["fee"] == pytest.approx(0.04)
    assert receipt["fee_currency"] == "USD"
    assert receipt["trade_ids"] == ["8081"]
    assert orca.session_trades == 1


def test_close_books_only_entry_and_exit_provider_receipts(tmp_path: Path) -> None:
    now = time.time()
    entry = _fill(
        now - 60.0,
        order_id="1256d475-cf44-4bd0-9580-f63ca4400b49",
        fee=0.04,
    )
    exit_fill = _fill(
        now,
        order_id="c7278877-9186-4772-8114-ed7883a4d6c6",
        side="sell",
        price=102.0,
        fee=0.05,
        trade_id="700002",
    )
    position = {
        "asset_id": "f7d0ebfb-369e-46ab-a335-24ad940f9bbc",
        "symbol": "BTCUSD",
        "qty": "0.2",
        "avg_entry_price": "100",
        "current_price": "102",
        "unrealized_pl": "999999",
        "market_value": "999999",
        "source_id": "alpaca:/v2/positions:BTCUSD",
        "source_timestamp": now,
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
    }

    class Client:
        def get_positions(self) -> list[dict[str, Any]]:
            return [position]

        def place_order(self, **_kwargs: Any) -> dict[str, Any]:
            return exit_fill

    orca = _orca(tmp_path)
    orca.alpaca = Client()
    orca.entry_fill_receipts["BTCUSD"] = entry
    orca.accounted_order_ids.add(entry["provider_order_id"])

    kills = orca.check_and_close_positions()

    assert len(kills) == 1
    kill = kills[0]
    assert kill.pnl_usd == pytest.approx(20.4 - 0.05 - 20.0 - 0.04)
    assert kill.entry_order_id == entry["provider_order_id"]
    assert kill.exit_order_id == exit_fill["provider_order_id"]
    assert kill.fee_currency == "USD"
    assert kill.truth_status == "real_derived"
    assert kill.eligible_for_learning is True
    assert "BTCUSD" not in orca.entry_fill_receipts


def test_close_ack_does_not_book_or_clear_entry(tmp_path: Path) -> None:
    now = time.time()
    entry = _fill(
        now - 60.0,
        order_id="ca4995de-8334-48dd-a087-c9df924a3d6d",
    )
    pending = {
        "id": "6cf7fe71-63da-40e7-870d-7d3381fc4d62",
        "status": "accepted",
        "symbol": "BTCUSD",
        "side": "sell",
        "data_status": "pending_reconciliation",
        "truth_status": "real_observed",
        "generated_values": False,
    }
    position = {
        "asset_id": "82f46f8f-e9e4-466a-8c24-9a365989f7cc",
        "symbol": "BTCUSD",
        "qty": "0.2",
        "avg_entry_price": "100",
        "current_price": "102",
        "source_timestamp": now,
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
    }

    class Client:
        def get_positions(self) -> list[dict[str, Any]]:
            return [position]

        def place_order(self, **_kwargs: Any) -> dict[str, Any]:
            return pending

        def get_order_with_fees(self, _order_id: str) -> dict[str, Any]:
            return pending

    orca = _orca(tmp_path)
    orca.alpaca = Client()
    orca.entry_fill_receipts["BTCUSD"] = entry
    orca.accounted_order_ids.add(entry["provider_order_id"])
    original_pnl = orca.session_pnl

    assert orca.check_and_close_positions() == []
    assert orca.session_pnl == original_pnl
    assert orca.session_wins == 0
    assert orca.session_losses == 0
    assert orca.entry_fill_receipts["BTCUSD"] == entry
    assert orca.pending_orders
