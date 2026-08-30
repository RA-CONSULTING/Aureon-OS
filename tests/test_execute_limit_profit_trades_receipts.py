from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from aureon.trading import execute_limit_profit_trades as subject


def test_limit_profit_lifecycle_is_inert_and_terminal_receipt_gated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    now = 1_800_000_000.0

    monkeypatch.setenv("LIVE", "operator-owned")
    monkeypatch.setenv("DRY_RUN", "operator-owned")
    importlib.reload(subject)
    assert subject.main([]) == 2
    cli = json.loads(capsys.readouterr().out)
    assert cli["status"] == "not_submitted"
    assert cli["eligible_for_action"] is False
    assert cli["eligible_for_accounting"] is False
    assert cli["eligible_for_learning"] is False
    assert os.environ["LIVE"] == "operator-owned"
    assert os.environ["DRY_RUN"] == "operator-owned"
    source = Path(subject.__file__).read_text(encoding="utf-8")
    assert "get_binance_client" not in source
    assert "place_market_order" not in source
    assert "time.sleep" not in source
    assert "os.environ" not in source

    def header(
        receipt_id: str,
        *,
        truth_status: str = "real_provider",
        venue: str = "binance",
    ) -> dict[str, Any]:
        return {
            "receipt_id": receipt_id,
            "venue": venue,
            "symbol": "ADAUSDT",
            "account_id": "acct-1",
            "data_status": "live",
            "truth_status": truth_status,
            "generated_values": False,
            "eligible_for_action": True,
            "provider_timestamp": now,
            "received_at": now,
        }

    def authorization(
        *,
        side: str,
        intent_id: str,
        limit_price: str,
        max_notional: str,
    ) -> dict[str, Any]:
        return {
            **header(f"auth-receipt-{intent_id}", truth_status="real_operator"),
            "authorization_id": f"authorization-{intent_id}",
            "cycle_id": "cycle-1",
            "intent_id": intent_id,
            "side": side,
            "quantity": "2",
            "limit_price": limit_price,
            "max_notional": max_notional,
            "minimum_net_profit_rate": "0.001",
            "authorized": True,
            "provider_submission_authorized": True,
            "expires_at": now + 60,
        }

    def quote(*, bid: str, ask: str) -> dict[str, Any]:
        return {
            **header(f"quote-{bid}-{ask}"),
            "base_asset": "ADA",
            "quote_asset": "USDT",
            "bid_price": bid,
            "ask_price": ask,
        }

    def position(quantity: str, *, venue: str = "binance") -> dict[str, Any]:
        return {
            **header(f"position-{quantity}-{venue}", venue=venue),
            "base_asset": "ADA",
            "position_quantity": quantity,
        }

    def account(asset: str, available: str) -> dict[str, Any]:
        return {
            **header(f"account-{asset}-{available}"),
            "asset": asset,
            "available_balance": available,
        }

    fee = {
        **header("fee-1"),
        "maker_fee_rate": "0.001",
        "fee_currency": "USDT",
    }

    def acknowledgement(side: str, order_id: str) -> dict[str, Any]:
        return {
            "receipt_id": f"ack-{order_id}",
            "venue": "binance",
            "symbol": "ADAUSDT",
            "side": side,
            "provider_order_id": order_id,
            "status": "NEW",
            "submitted": True,
            "data_status": "live",
            "truth_status": "real_provider",
            "generated_values": False,
            "provider_timestamp": now,
            "received_at": now,
        }

    def nonterminal(side: str, order_id: str, status: str) -> dict[str, Any]:
        return {
            **acknowledgement(side, order_id),
            "status": status,
        }

    def terminal(
        *,
        side: str,
        order_id: str,
        trade_id: str,
        price: str,
        notional: str,
        fee_amount: str,
    ) -> dict[str, Any]:
        return {
            "receipt_id": f"fill-{order_id}",
            "provider_receipt_type": "BinanceFullOrderAndTrades",
            "venue": "binance",
            "symbol": "ADAUSDT",
            "side": side,
            "provider_order_id": order_id,
            "status": "FILLED",
            "provider_status": "FILLED",
            "data_status": "live",
            "truth_status": "real_provider",
            "generated_values": False,
            "fill_receipt_complete": True,
            "eligible_for_action": False,
            "eligible_for_accounting": True,
            "eligible_for_learning": True,
            "reconciliation_required": False,
            "filled_qty": "2",
            "filled_notional": notional,
            "filled_avg_price": price,
            "fee": fee_amount,
            "fee_currency": "USDT",
            "provider_timestamp": now,
            "received_at": now,
            "fills": [
                {
                    "tradeId": trade_id,
                    "qty": "2",
                    "price": price,
                    "commission": fee_amount,
                    "commissionAsset": "USDT",
                    "provider_timestamp": now,
                }
            ],
        }

    class TrapAdapter:
        def __init__(self) -> None:
            self.calls = 0

        def submit_limit_order(self, **_: Any) -> dict[str, Any]:
            self.calls += 1
            raise AssertionError("submission must remain unreachable")

        def read_order_receipt(self, **_: Any) -> dict[str, Any]:
            self.calls += 1
            raise AssertionError("read-back must remain unreachable")

    blocked_state = tmp_path / "blocked.json"
    trap = TrapAdapter()
    stale_quote = quote(bid="100", ask="100.1")
    stale_quote["provider_timestamp"] = now - subject.MAX_AGE_SECONDS - 1
    blocked = subject.execute_profit_trade(
        trap,
        "ADAUSDT",
        "200",
        authorization_receipt=authorization(
            side="BUY",
            intent_id="buy-1",
            limit_price="100",
            max_notional="200",
        ),
        position_receipt=position("0"),
        account_receipt=account("USDT", "1000"),
        quote_receipt=stale_quote,
        fee_receipt=fee,
        state_path=blocked_state,
        now=now,
    )
    assert blocked["status"] == "no_data"
    assert "fresh_provider_evidence_required" in blocked["reason"]
    assert trap.calls == 0
    assert not blocked_state.exists()

    wrong_venue = subject.execute_profit_trade(
        trap,
        "ADAUSDT",
        "200",
        authorization_receipt=authorization(
            side="BUY",
            intent_id="buy-1",
            limit_price="100",
            max_notional="200",
        ),
        position_receipt=position("0", venue="kraken"),
        account_receipt=account("USDT", "1000"),
        quote_receipt=quote(bid="100", ask="100.1"),
        fee_receipt=fee,
        state_path=blocked_state,
        now=now,
    )
    assert wrong_venue["status"] == "no_data"
    assert wrong_venue["reason"] == "position_venue_mismatch"
    assert trap.calls == 0
    assert not blocked_state.exists()

    class DryAdapter:
        calls = 0

        def submit_limit_order(self, **_: Any) -> dict[str, Any]:
            self.calls += 1
            return {
                "status": "not_submitted",
                "submitted": False,
                "dryRun": True,
            }

    dry_state = tmp_path / "dry.json"
    dry = DryAdapter()
    dry_result = subject.execute_profit_trade(
        dry,
        "ADAUSDT",
        "200",
        authorization_receipt=authorization(
            side="BUY",
            intent_id="buy-1",
            limit_price="100",
            max_notional="200",
        ),
        position_receipt=position("0"),
        account_receipt=account("USDT", "1000"),
        quote_receipt=quote(bid="100", ask="100.1"),
        fee_receipt=fee,
        state_path=dry_state,
        now=now,
    )
    assert dry_result["status"] == "not_submitted"
    assert dry.calls == 1
    assert not dry_state.exists()

    buy_fill = terminal(
        side="BUY",
        order_id="buy-order-1",
        trade_id="buy-trade-1",
        price="100",
        notional="200",
        fee_amount="0.2",
    )
    incomplete_buy = dict(buy_fill)
    incomplete_buy.pop("fee")
    readbacks = {
        "buy-order-1": [
            nonterminal("BUY", "buy-order-1", "PARTIALLY_FILLED"),
            incomplete_buy,
            buy_fill,
        ],
        "sell-order-1": [
            nonterminal("SELL", "sell-order-1", "REJECTED"),
            terminal(
                side="SELL",
                order_id="sell-order-1",
                trade_id="sell-trade-1",
                price="101",
                notional="202",
                fee_amount="0.202",
            ),
        ],
    }

    class ScriptedAdapter:
        def __init__(self) -> None:
            self.submit_calls: list[dict[str, Any]] = []
            self.read_calls: list[dict[str, Any]] = []

        def submit_limit_order(self, **request: Any) -> dict[str, Any]:
            self.submit_calls.append(request)
            order_id = "buy-order-1" if request["side"] == "BUY" else "sell-order-1"
            return acknowledgement(request["side"], order_id)

        def read_order_receipt(self, **request: Any) -> dict[str, Any]:
            self.read_calls.append(request)
            return readbacks[request["provider_order_id"]].pop(0)

    adapter = ScriptedAdapter()
    state_path = tmp_path / "limit-profit-state.json"
    buy_auth = authorization(
        side="BUY",
        intent_id="buy-1",
        limit_price="100",
        max_notional="200",
    )
    buy_args = {
        "authorization_receipt": buy_auth,
        "position_receipt": position("0"),
        "account_receipt": account("USDT", "1000"),
        "quote_receipt": quote(bid="100", ask="100.1"),
        "fee_receipt": fee,
        "state_path": state_path,
        "now": now,
    }
    acknowledged = subject.execute_profit_trade(
        adapter,
        "ADAUSDT",
        "200",
        **buy_args,
    )
    assert acknowledged["status"] == "pending_reconciliation"
    assert acknowledged["submission_count"] == 1
    assert acknowledged["readback_count"] == 0
    assert len(adapter.submit_calls) == 1
    state_after_ack = state_path.read_bytes()
    pending_cycle = json.loads(state_after_ack)["cycles"]["cycle-1"]
    assert pending_cycle["entry_fill"] is None
    assert pending_cycle["accounting"] is None

    partial = subject.execute_profit_trade(adapter, "ADAUSDT", "200", **buy_args)
    assert partial["status"] == "pending_reconciliation"
    assert partial["readback_count"] == 1
    assert state_path.read_bytes() == state_after_ack
    assert len(adapter.submit_calls) == 1
    assert len(adapter.read_calls) == 1

    incomplete = subject.execute_profit_trade(adapter, "ADAUSDT", "200", **buy_args)
    assert incomplete["status"] == "pending_reconciliation"
    assert incomplete["reason"] == "terminal_fee_required"
    assert state_path.read_bytes() == state_after_ack
    assert len(adapter.read_calls) == 2

    entry = subject.execute_profit_trade(adapter, "ADAUSDT", "200", **buy_args)
    assert entry["status"] == "filled"
    assert entry["reason"] == "terminal_entry_fill_committed"
    assert entry["mutated"] is True
    assert entry["accounting_committed"] is False
    after_entry = json.loads(state_path.read_text(encoding="utf-8"))["cycles"]["cycle-1"]
    assert after_entry["phase"] == "entry_filled"
    assert after_entry["entry_fill"]["receipt_id"] == "fill-buy-order-1"
    assert after_entry["accounting"] is None

    sell_auth = authorization(
        side="SELL",
        intent_id="sell-1",
        limit_price="101",
        max_notional="202",
    )
    sell_args = {
        "authorization_receipt": sell_auth,
        "position_receipt": position("2"),
        "account_receipt": account("ADA", "2"),
        "quote_receipt": quote(bid="100.8", ask="101"),
        "fee_receipt": fee,
        "state_path": state_path,
        "now": now,
    }
    sell_ack = subject.execute_profit_trade(
        adapter,
        "ADAUSDT",
        "200",
        **sell_args,
    )
    assert sell_ack["status"] == "pending_reconciliation"
    assert len(adapter.submit_calls) == 2
    state_after_sell_ack = state_path.read_bytes()

    rejected = subject.execute_profit_trade(adapter, "ADAUSDT", "200", **sell_args)
    assert rejected["status"] == "pending_reconciliation"
    assert rejected["reason"] == "terminal_filled_provider_status_required"
    assert state_path.read_bytes() == state_after_sell_ack
    assert len(adapter.submit_calls) == 2

    settled = subject.execute_profit_trade(adapter, "ADAUSDT", "200", **sell_args)
    assert settled["status"] == "filled"
    assert settled["accounting_committed"] is True
    assert settled["gross_pnl"] == "2"
    assert settled["fees"] == "0.402"
    assert settled["net_pnl"] == "1.598"
    final_state = state_path.read_bytes()
    cycle = json.loads(final_state)["cycles"]["cycle-1"]
    assert cycle["phase"] == "complete"
    assert cycle["committed_receipt_ids"] == [
        "fill-buy-order-1",
        "fill-sell-order-1",
    ]

    submit_count = len(adapter.submit_calls)
    read_count = len(adapter.read_calls)
    repeated = subject.execute_profit_trade(
        adapter,
        "ADAUSDT",
        "200",
        **sell_args,
    )
    assert repeated["reason"] == "round_trip_already_complete"
    assert repeated["mutated"] is False
    assert len(adapter.submit_calls) == submit_count
    assert len(adapter.read_calls) == read_count
    assert state_path.read_bytes() == final_state
