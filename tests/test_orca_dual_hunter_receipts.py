from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

import aureon.bots.orca_dual_hunter as subject


VENUE = "kraken"
SYMBOL = "DOGEUSD"
ACCOUNT_ID = "acct-verified"
BASE_ASSET = "DOGE"
QUOTE_ASSET = "USD"


def _header(
    kind: str,
    now: float,
    *,
    truth_status: str = "real_observed",
) -> dict[str, Any]:
    return {
        "receipt_id": f"{kind}-receipt",
        "provider_receipt_type": kind,
        "venue": VENUE,
        "symbol": SYMBOL,
        "account_id": ACCOUNT_ID,
        "provider_timestamp": now - 1,
        "received_at": now,
        "data_status": "live",
        "truth_status": truth_status,
        "generated_values": False,
        "eligible_for_action": True,
    }


def _bundle(
    now: float,
    *,
    side: str,
    intent_id: str,
    bid: str,
    ask: str,
    account_currency: str,
    available: str,
    position_quantity: str,
    entry_receipt_id: str | None = None,
    opened_at: float | None = None,
    reason_code: str = "",
) -> dict[str, Any]:
    normalized_side = side.upper()
    authorization = _header(
        f"authorization-{intent_id}",
        now,
        truth_status="real_operator",
    )
    execution_price = Decimal(ask if normalized_side == "BUY" else bid)
    quantity = Decimal("1")
    notional = execution_price * quantity
    fee = notional * Decimal("0.001")
    authorization.update(
        {
            "authorization_id": f"operator-{intent_id}",
            "cycle_id": "cycle-round-trip",
            "intent_id": intent_id,
            "side": normalized_side,
            "quantity": "1",
            "max_notional": str(notional + Decimal("1")),
            "reason_code": reason_code,
            "authorized": True,
            "provider_submission_authorized": True,
            "expires_at": now + 120,
        }
    )
    account = _header(f"account-{intent_id}", now)
    account.update(
        {
            "currency": account_currency,
            "available_balance": available,
        }
    )
    position = _header(f"position-{intent_id}", now)
    position.update(
        {
            "base_asset": BASE_ASSET,
            "quote_asset": QUOTE_ASSET,
            "position_quantity": position_quantity,
        }
    )
    if entry_receipt_id is not None:
        position["entry_receipt_id"] = entry_receipt_id
    if opened_at is not None:
        position["provider_open_timestamp"] = opened_at
    market = _header(f"market-{intent_id}", now)
    market.update(
        {
            "base_asset": BASE_ASSET,
            "quote_asset": QUOTE_ASSET,
            "bid_price": bid,
            "ask_price": ask,
        }
    )
    fee_receipt = _header(f"fee-{intent_id}", now)
    fee_receipt.update(
        {
            "taker_fee_rate": "0.001",
            "fee_currency": QUOTE_ASSET,
        }
    )
    hnc = _header(
        f"hnc-{intent_id}",
        now,
        truth_status="real_derived",
    )
    hnc.update(
        {
            "equation_id": "hnc-canonical-v1",
            "hnc_signal": "0.81",
            "equation_inputs_complete": True,
            "action_gate_passed": True,
            "recommended_side": normalized_side,
            "market_receipt_id": market["receipt_id"],
        }
    )
    auris = _header(
        f"auris-{intent_id}",
        now,
        truth_status="real_derived",
    )
    auris.update(
        {
            "equation_id": "auris-canonical-v1",
            "auris_signal": "0.77",
            "equation_inputs_complete": True,
            "action_gate_passed": True,
            "recommended_side": normalized_side,
            "market_receipt_id": market["receipt_id"],
            "hnc_receipt_id": hnc["receipt_id"],
        }
    )
    cost = _header(
        f"cost-{intent_id}",
        now,
        truth_status="real_derived",
    )
    cost.update(
        {
            "quantity": "1",
            "execution_price": str(execution_price),
            "notional": str(notional),
            "estimated_fee": str(fee),
            "currency": QUOTE_ASSET,
            "dependency_receipt_ids": [
                authorization["receipt_id"],
                account["receipt_id"],
                position["receipt_id"],
                market["receipt_id"],
                fee_receipt["receipt_id"],
                hnc["receipt_id"],
                auris["receipt_id"],
            ],
        }
    )
    return {
        "authorization_receipt": authorization,
        "account_receipt": account,
        "position_receipt": position,
        "market_receipt": market,
        "cost_receipt": cost,
        "fee_receipt": fee_receipt,
        "hnc_receipt": hnc,
        "auris_receipt": auris,
    }


def _ack(
    now: float,
    *,
    order_id: str,
    side: str,
    status: str,
) -> dict[str, Any]:
    return {
        "receipt_id": f"ack-{order_id}-{status.lower()}",
        "provider_receipt_type": "provider_order_acknowledgement",
        "provider_order_id": order_id,
        "provider_status": status,
        "venue": VENUE,
        "symbol": SYMBOL,
        "account_id": ACCOUNT_ID,
        "side": side,
        "provider_timestamp": now - 1,
        "received_at": now,
        "data_status": "live",
        "truth_status": "real_provider",
        "generated_values": False,
        "eligible_for_action": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "reconciliation_required": True,
    }


def _fill(
    now: float,
    *,
    receipt_id: str,
    order_id: str,
    trade_id: str,
    side: str,
    price: str,
    fee: str,
    provider_timestamp: float,
) -> dict[str, Any]:
    quantity = Decimal("1")
    fill_price = Decimal(price)
    return {
        "receipt_id": receipt_id,
        "provider_receipt_type": "provider_terminal_fill",
        "provider_order_id": order_id,
        "provider_status": "FILLED",
        "venue": VENUE,
        "symbol": SYMBOL,
        "account_id": ACCOUNT_ID,
        "side": side,
        "filled_qty": "1",
        "filled_notional": str(quantity * fill_price),
        "filled_avg_price": price,
        "fee": fee,
        "fee_currency": QUOTE_ASSET,
        "fills": [
            {
                "trade_id": trade_id,
                "quantity": "1",
                "price": price,
                "fee": fee,
                "fee_currency": QUOTE_ASSET,
                "provider_timestamp": provider_timestamp,
            }
        ],
        "provider_timestamp": provider_timestamp,
        "received_at": now,
        "data_status": "live",
        "truth_status": "real_provider",
        "generated_values": False,
        "fill_receipt_complete": True,
        "eligible_for_action": False,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "reconciliation_required": False,
    }


class _Adapter:
    def __init__(
        self,
        *,
        submissions: list[Mapping[str, Any] | Exception],
        readbacks: list[Mapping[str, Any] | Exception],
    ) -> None:
        self.submissions = list(submissions)
        self.readbacks = list(readbacks)
        self.submit_calls: list[dict[str, Any]] = []
        self.read_calls: list[dict[str, Any]] = []

    def submit_order(self, **kwargs: Any) -> Mapping[str, Any]:
        self.submit_calls.append(kwargs)
        response = self.submissions.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    def read_order_receipt(self, **kwargs: Any) -> Mapping[str, Any]:
        self.read_calls.append(kwargs)
        response = self.readbacks.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_fail_closed_dual_venue_terminal_fill_lifecycle(
    tmp_path: Path,
) -> None:
    now = 1_800_000_000.0
    buy = _bundle(
        now,
        side="BUY",
        intent_id="intent-buy",
        bid="99.9",
        ask="100",
        account_currency=QUOTE_ASSET,
        available="1000",
        position_quantity="0",
    )
    buy_ack = _ack(
        now,
        order_id="provider-buy-1",
        side="BUY",
        status="ACCEPTED",
    )
    partial_buy = _ack(
        now,
        order_id="provider-buy-1",
        side="BUY",
        status="PARTIALLY_FILLED",
    )
    terminal_buy = _fill(
        now,
        receipt_id="terminal-buy-1",
        order_id="provider-buy-1",
        trade_id="trade-buy-1",
        side="BUY",
        price="100",
        fee="0.1",
        provider_timestamp=now - 60,
    )
    incomplete_buy = dict(terminal_buy)
    incomplete_buy.pop("fee")

    dry_adapter = _Adapter(submissions=[buy_ack], readbacks=[])
    dry_path = tmp_path / "dry-state.json"
    dry_hunter = subject.OrcaDualHunter(
        adapters={VENUE: dry_adapter},
        clock=lambda: now,
        state_path=dry_path,
    )
    dry_result = dry_hunter.process_action(**buy)
    assert dry_result["status"] == "dry_run"
    assert dry_result["economic_mutation"] is False
    assert dry_adapter.submit_calls == []
    assert dry_adapter.read_calls == []
    assert not dry_path.exists()

    uncertain = _bundle(
        now,
        side="BUY",
        intent_id="intent-uncertain",
        bid="99.9",
        ask="100",
        account_currency=QUOTE_ASSET,
        available="1000",
        position_quantity="0",
    )
    uncertain_fill = _fill(
        now,
        receipt_id="terminal-uncertain-1",
        order_id="provider-uncertain-1",
        trade_id="trade-uncertain-1",
        side="BUY",
        price="100",
        fee="0.1",
        provider_timestamp=now - 1,
    )
    uncertain_adapter = _Adapter(
        submissions=[RuntimeError("transport interrupted")],
        readbacks=[uncertain_fill],
    )
    uncertain_path = tmp_path / "uncertain-state.json"
    uncertain_hunter = subject.OrcaDualHunter(
        adapters={VENUE: uncertain_adapter},
        clock=lambda: now,
        state_path=uncertain_path,
        dry_run=False,
    )
    unresolved = uncertain_hunter.process_action(**uncertain)
    assert unresolved["status"] == "pending_reconciliation"
    assert unresolved["reason"] == "submission_outcome_unknown"
    assert unresolved["economic_mutation"] is False
    unresolved_state = json.loads(
        uncertain_path.read_text(encoding="utf-8")
    )
    assert unresolved_state["pending_intents"]["intent-uncertain"][
        "phase"
    ] == "reserved"
    assert unresolved_state["open_positions"] == {}
    uncertain_restart = subject.OrcaDualHunter(
        adapters={VENUE: uncertain_adapter},
        clock=lambda: now,
        state_path=uncertain_path,
        dry_run=False,
    )
    resolved = uncertain_restart.process_action(**uncertain)
    assert resolved["status"] == "filled"
    assert len(uncertain_adapter.submit_calls) == 1
    assert len(uncertain_adapter.read_calls) == 1

    sell_ack = _ack(
        now,
        order_id="provider-sell-1",
        side="SELL",
        status="ACCEPTED",
    )
    rejected_sell = _ack(
        now,
        order_id="provider-sell-1",
        side="SELL",
        status="REJECTED",
    )
    terminal_sell = _fill(
        now,
        receipt_id="terminal-sell-1",
        order_id="provider-sell-1",
        trade_id="trade-sell-1",
        side="SELL",
        price="102",
        fee="0.102",
        provider_timestamp=now - 1,
    )
    adapter = _Adapter(
        submissions=[buy_ack, sell_ack],
        readbacks=[
            partial_buy,
            incomplete_buy,
            terminal_buy,
            rejected_sell,
            terminal_sell,
        ],
    )
    state_path = tmp_path / "orca-dual-state.json"
    hunter = subject.OrcaDualHunter(
        adapters={VENUE: adapter},
        clock=lambda: now,
        state_path=state_path,
        dry_run=False,
    )

    missing_market = {
        name: dict(receipt) for name, receipt in buy.items()
    }
    missing_market["market_receipt"]["bid_price"] = None
    absent = hunter.process_action(**missing_market)
    assert absent["status"] == "no_data"
    assert absent["truth_status"] == "no_data"
    assert absent["economic_mutation"] is False
    assert not any(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in absent.values()
    )
    assert adapter.submit_calls == []
    assert not state_path.exists()

    cross_venue = {
        name: dict(receipt) for name, receipt in buy.items()
    }
    cross_venue["market_receipt"]["venue"] = "alpaca"
    refused_route = hunter.process_action(**cross_venue)
    assert refused_route["status"] == "no_data"
    assert "market_venue_mismatch" in refused_route["reason"]
    assert adapter.submit_calls == []

    blocked_hnc = {
        name: dict(receipt) for name, receipt in buy.items()
    }
    blocked_hnc["hnc_receipt"]["action_gate_passed"] = False
    refused_hnc = hunter.process_action(**blocked_hnc)
    assert refused_hnc["status"] == "no_data"
    assert refused_hnc["reason"] == "hnc_equation_gate_incomplete"
    assert adapter.submit_calls == []

    acknowledged = hunter.process_action(**buy)
    assert acknowledged["status"] == "pending_reconciliation"
    assert acknowledged["economic_mutation"] is False
    assert len(adapter.submit_calls) == 1
    assert adapter.read_calls == []
    state_after_ack = state_path.read_bytes()
    ack_state = json.loads(state_after_ack)
    pending = ack_state["pending_intents"]["intent-buy"]
    assert pending["phase"] == "acknowledged"
    assert pending["provider_order_id"] == "provider-buy-1"
    assert ack_state["open_positions"] == {}
    assert ack_state["round_trips"] == {}
    assert ack_state["committed_receipt_ids"] == []

    restarted = subject.OrcaDualHunter(
        adapters={VENUE: adapter},
        clock=lambda: now,
        state_path=state_path,
        dry_run=False,
    )
    read_count = len(adapter.read_calls)
    partial = restarted.process_action(**buy)
    assert partial["status"] == "pending_reconciliation"
    assert partial["economic_mutation"] is False
    assert len(adapter.read_calls) == read_count + 1
    assert len(adapter.submit_calls) == 1
    assert state_path.read_bytes() == state_after_ack

    read_count = len(adapter.read_calls)
    incomplete = restarted.process_action(**buy)
    assert incomplete["status"] == "pending_reconciliation"
    assert incomplete["economic_mutation"] is False
    assert len(adapter.read_calls) == read_count + 1
    assert state_path.read_bytes() == state_after_ack

    read_count = len(adapter.read_calls)
    entered = restarted.process_action(**buy)
    assert entered["status"] == "filled"
    assert entered["reason"] == "terminal_entry_fill_committed"
    assert entered["economic_mutation"] is True
    assert entered["receipt"]["filled_qty"] == "1"
    assert entered["receipt"]["filled_notional"] == "100"
    assert entered["receipt"]["fee"] == "0.1"
    assert len(adapter.read_calls) == read_count + 1
    entry_state = json.loads(state_path.read_text(encoding="utf-8"))
    route_key = f"{VENUE}|{ACCOUNT_ID}|{SYMBOL}"
    assert entry_state["open_positions"][route_key]["receipt_id"] == (
        "terminal-buy-1"
    )
    assert entry_state["round_trips"] == {}

    submit_count = len(adapter.submit_calls)
    read_count = len(adapter.read_calls)
    duplicate_entry = restarted.process_action(**buy)
    assert duplicate_entry["status"] == "already_committed"
    assert duplicate_entry["economic_mutation"] is False
    assert len(adapter.submit_calls) == submit_count
    assert len(adapter.read_calls) == read_count

    sell = _bundle(
        now,
        side="SELL",
        intent_id="intent-sell",
        bid="102",
        ask="102.1",
        account_currency=BASE_ASSET,
        available="1",
        position_quantity="1",
        entry_receipt_id="terminal-buy-1",
        opened_at=now - 60,
        reason_code="take_profit",
    )
    exit_acknowledged = restarted.process_action(**sell)
    assert exit_acknowledged["status"] == "pending_reconciliation"
    assert exit_acknowledged["economic_mutation"] is False
    assert len(adapter.submit_calls) == submit_count + 1
    state_after_exit_ack = state_path.read_bytes()
    exit_ack_state = json.loads(state_after_exit_ack)
    assert route_key in exit_ack_state["open_positions"]
    assert exit_ack_state["round_trips"] == {}

    read_count = len(adapter.read_calls)
    rejected = restarted.process_action(**sell)
    assert rejected["status"] == "pending_reconciliation"
    assert rejected["economic_mutation"] is False
    assert len(adapter.read_calls) == read_count + 1
    assert state_path.read_bytes() == state_after_exit_ack

    read_count = len(adapter.read_calls)
    exited = restarted.process_action(**sell)
    assert exited["status"] == "filled"
    assert exited["reason"] == "terminal_exit_fill_committed"
    assert exited["trigger"]["reason_code"] == "take_profit"
    assert exited["trigger"]["gross_pnl_pct"] == "0.02"
    assert exited["trigger"]["round_trip_fee_pct"] == "0.002"
    assert exited["trigger"]["net_pnl_pct"] == "0.018"
    assert exited["accounting"]["gross_pnl"] == "2"
    assert exited["accounting"]["fees"] == "0.202"
    assert exited["accounting"]["net_pnl"] == "1.798"
    assert exited["accounting"]["currency"] == QUOTE_ASSET
    assert len(adapter.read_calls) == read_count + 1

    final_bytes = state_path.read_bytes()
    final_state = json.loads(final_bytes)
    assert final_state["open_positions"] == {}
    assert final_state["pending_intents"] == {}
    assert final_state["committed_receipt_ids"] == [
        "terminal-buy-1",
        "terminal-sell-1",
    ]
    assert final_state["round_trips"]["cycle-round-trip"]["net_pnl"] == (
        "1.798"
    )

    submit_count = len(adapter.submit_calls)
    read_count = len(adapter.read_calls)
    duplicate_exit = restarted.process_action(**sell)
    assert duplicate_exit["status"] == "already_committed"
    assert len(adapter.submit_calls) == submit_count
    assert len(adapter.read_calls) == read_count
    assert state_path.read_bytes() == final_bytes
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob("*.lock"))
