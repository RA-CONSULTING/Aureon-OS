from __future__ import annotations

import ast
import copy
import hashlib
import json
import math
import os
import time
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aureon" / "bots" / "orca_unified_kill_chain.py"
VENUE = "kraken"
SYMBOL = "BTCUSD"
ACCOUNT_ID = "account-24711"


def _load_subject():
    tree = ast.parse(
        TARGET.read_text(encoding="utf-8"),
        filename=str(TARGET),
    )
    helper_names = {
        "_finite_provider_number",
        "_provider_decimal",
        "_decimal_text",
        "_parse_provider_timestamp",
        "_valid_provider_identifier",
        "_first_present",
        "_provider_order_identifier",
        "_provider_trade_identifiers",
        "_normalized_venue",
        "_normalized_symbol",
        "_same_observed_number",
        "_no_data_decision",
        "_execution_result",
        "_action_receipt_header",
        "_classify_action_evidence",
        "_complete_position_target_evidence",
        "_complete_opportunity_evidence",
        "_classify_terminal_fill_receipt",
        "_empty_execution_state",
        "_validate_execution_state",
        "_load_execution_state",
        "_write_execution_state",
        "_execution_state_lock",
        "_pending_action",
    }
    method_names = {
        "_submit_and_reconcile",
        "_commit_terminal_execution",
        "execute_kill_chain",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name)
            and target.id.startswith(
                (
                    "EXECUTION_RECEIPT_",
                    "ACTION_EVIDENCE_",
                    "EXECUTION_STATE_",
                )
            )
            for target in node.targets
        ):
            selected.append(copy.deepcopy(node))
        elif isinstance(node, ast.FunctionDef) and node.name in helper_names:
            selected.append(copy.deepcopy(node))
        elif isinstance(node, ast.ClassDef) and node.name == "UnifiedKillChain":
            scoped = copy.deepcopy(node)
            scoped.decorator_list = []
            scoped.body = [
                item
                for item in scoped.body
                if isinstance(item, ast.FunctionDef)
                and item.name in method_names
            ]
            selected.append(scoped)
    logs: list[tuple[str, str]] = []
    namespace = {
        "hashlib": hashlib,
        "json": json,
        "math": math,
        "os": os,
        "time": time,
        "contextmanager": contextmanager,
        "datetime": datetime,
        "Decimal": Decimal,
        "InvalidOperation": InvalidOperation,
        "Path": Path,
        "log_queen": lambda message: logs.append(("queen", message)),
        "log_auris": lambda message: logs.append(("auris", message)),
        "log_sniper": lambda message: logs.append(("sniper", message)),
    }
    module = ast.fix_missing_locations(
        ast.Module(body=selected, type_ignores=[])
    )
    exec(compile(module, str(TARGET), "exec"), namespace)
    return SimpleNamespace(**namespace), logs


def _header(
    kind: str,
    now: float,
    *,
    truth_status: str = "real_observed",
) -> dict[str, Any]:
    return {
        "receipt_id": f"{kind}-receipt",
        "provider_receipt_type": kind,
        "source_id": f"{VENUE}:{kind}",
        "venue": VENUE,
        "symbol": SYMBOL,
        "account_id": ACCOUNT_ID,
        "source_timestamp": now - 1,
        "received_at": now,
        "data_status": "live",
        "truth_status": truth_status,
        "generated_values": False,
        "eligible_for_action": True,
    }


def _target(
    now: float,
    *,
    intent_id: str,
    position_id: str,
) -> dict[str, Any]:
    position = _header(f"position-{intent_id}", now)
    position.update(
        {
            "position_id": position_id,
            "quantity": "2",
            "base_asset": "BTC",
            "quote_asset": "USD",
        }
    )
    opportunity = _header(
        f"opportunity-{intent_id}",
        now,
        truth_status="real_derived",
    )
    opportunity.update(
        {
            "position_receipt_id": position["receipt_id"],
            "pnl": "20",
            "entry_price": "100",
            "current_price": "110",
        }
    )
    market = _header(f"market-{intent_id}", now)
    market.update(
        {
            "base_asset": "BTC",
            "quote_asset": "USD",
            "price": "110",
            "bid": "110",
            "ask": "110.1",
        }
    )
    account = _header(f"account-{intent_id}", now)
    account.update({"asset": "BTC", "available_balance": "2"})
    fee = _header(f"fee-{intent_id}", now)
    fee.update({"taker_fee_rate": "0.001", "fee_currency": "USD"})
    hnc = _header(
        f"hnc-{intent_id}",
        now,
        truth_status="real_derived",
    )
    hnc.update(
        {
            "equation_id": "hnc-canonical-v1",
            "hnc_signal": "0.82",
            "equation_inputs_complete": True,
            "action_gate_passed": True,
            "recommended_side": "SELL",
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
            "auris_signal": "0.79",
            "equation_inputs_complete": True,
            "action_gate_passed": True,
            "recommended_side": "SELL",
            "market_receipt_id": market["receipt_id"],
            "hnc_receipt_id": hnc["receipt_id"],
        }
    )
    authorization = _header(
        f"authorization-{intent_id}",
        now,
        truth_status="real_operator",
    )
    authorization.update(
        {
            "authorization_id": f"authorization-id-{intent_id}",
            "intent_id": intent_id,
            "side": "SELL",
            "quantity": "2",
            "authorized": True,
            "provider_submission_authorized": True,
            "expires_at": now + 120,
        }
    )
    cost = _header(
        f"cost-{intent_id}",
        now,
        truth_status="real_derived",
    )
    cost.update(
        {
            "quantity": "2",
            "entry_price": "100",
            "entry_notional": "200",
            "entry_fee": "0.2",
            "currency": "USD",
            "dependency_receipt_ids": [
                authorization["receipt_id"],
                account["receipt_id"],
                position["receipt_id"],
                market["receipt_id"],
                fee["receipt_id"],
                hnc["receipt_id"],
                auris["receipt_id"],
            ],
        }
    )
    return {
        "exchange": VENUE,
        "symbol": SYMBOL,
        "id": position_id,
        "qty": "2",
        "pnl": "20",
        "entry_price": "100",
        "current_price": "110",
        "position_receipt": position,
        "opportunity_receipt": opportunity,
        "market_receipt": market,
        "account_receipt": account,
        "fee_receipt": fee,
        "cost_receipt": cost,
        "hnc_receipt": hnc,
        "auris_receipt": auris,
        "authorization_receipt": authorization,
    }


def _ack(
    now: float,
    *,
    order_id: str,
    status: str,
) -> dict[str, Any]:
    return {
        "receipt_id": f"ack-{order_id}-{status.lower()}",
        "provider_receipt_type": "AddOrder",
        "orderId": order_id,
        "status": status,
        "data_status": "pending_reconciliation",
        "venue": VENUE,
        "symbol": SYMBOL,
        "side": "SELL",
        "submitted": True,
        "submission_acknowledged": True,
        "reconciliation_required": True,
        "generated_values": False,
    }


def _terminal(
    now: float,
    *,
    receipt_id: str,
    order_id: str,
    trade_id: str,
) -> dict[str, Any]:
    return {
        "receipt_id": receipt_id,
        "provider_receipt_type": "QueryOrders",
        "orderId": order_id,
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_provider",
        "venue": VENUE,
        "symbol": SYMBOL,
        "side": "SELL",
        "filled_qty": "2",
        "filled_avg_price": "110",
        "filled_notional": "220",
        "fee": "0.22",
        "fee_currency": "USD",
        "fills": [
            {
                "tradeId": trade_id,
                "quantity": "2",
                "price": "110",
                "fee": "0.22",
                "fee_currency": "USD",
                "provider_timestamp": now - 1,
            }
        ],
        "provider_timestamp": now - 1,
        "received_at": now,
        "fill_receipt_complete": True,
        "eligible_for_action": False,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "generated_values": False,
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

    def submit_close(self, **kwargs: Any) -> Mapping[str, Any]:
        self.submit_calls.append(kwargs)
        result = self.submissions.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def read_order_receipt(self, **kwargs: Any) -> Mapping[str, Any]:
        self.read_calls.append(kwargs)
        result = self.readbacks.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def _chain(
    module: SimpleNamespace,
    *,
    adapter: _Adapter,
    state_path: Path,
    now: float,
    enabled: bool = True,
):
    chain = module.UnifiedKillChain.__new__(module.UnifiedKillChain)
    chain.execution_state_path = state_path
    chain.clock = lambda: now
    chain.execution_adapters = {VENUE: adapter}
    chain.execution_enabled = enabled
    chain.last_no_data = []
    chain.wins_executed = []
    chain.total_pnl = 0.0
    return chain


def test_linked_evidence_pending_readback_and_terminal_only_accounting(
    tmp_path: Path,
) -> None:
    module, logs = _load_subject()
    now = 1_800_000_000.0
    target = _target(
        now,
        intent_id="intent-close-1",
        position_id="BTC-POSITION-1",
    )
    terminal = _terminal(
        now,
        receipt_id="terminal-close-1",
        order_id="provider-order-1",
        trade_id="provider-trade-1",
    )
    adapter = _Adapter(
        submissions=[
            _ack(
                now,
                order_id="provider-order-1",
                status="ACCEPTED",
            ),
            _ack(
                now,
                order_id="provider-order-2",
                status="ACCEPTED",
            ),
        ],
        readbacks=[
            _ack(
                now,
                order_id="provider-order-1",
                status="PARTIALLY_FILLED",
            ),
            terminal,
            _ack(
                now,
                order_id="provider-order-2",
                status="REJECTED",
            ),
        ],
    )
    state_path = tmp_path / "unified-kill-state.json"
    chain = _chain(
        module,
        adapter=adapter,
        state_path=state_path,
        now=now,
    )

    missing_hnc = copy.deepcopy(target)
    missing_hnc["hnc_receipt"]["action_gate_passed"] = False
    withheld = chain.execute_kill_chain(missing_hnc)
    assert withheld["status"] == "no_data"
    assert withheld["reason"] == "hnc_equation_gate_incomplete"
    assert withheld["economic_mutation"] is False
    assert not any(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in withheld.values()
    )
    assert adapter.submit_calls == []
    assert not state_path.exists()

    disabled_path = tmp_path / "disabled-state.json"
    disabled = _chain(
        module,
        adapter=adapter,
        state_path=disabled_path,
        now=now,
        enabled=False,
    )
    not_submitted = disabled.execute_kill_chain(target)
    assert not_submitted["status"] == "not_submitted"
    assert not_submitted["economic_mutation"] is False
    assert adapter.submit_calls == []
    assert not disabled_path.exists()

    acknowledged = chain.execute_kill_chain(target)
    assert acknowledged["status"] == "pending_reconciliation"
    assert acknowledged["success"] is False
    assert acknowledged["economic_mutation"] is False
    assert len(adapter.submit_calls) == 1
    assert adapter.read_calls == []
    state_after_ack = state_path.read_bytes()
    ack_state = json.loads(state_after_ack)
    pending = ack_state["pending"]["intent-close-1"]
    assert pending["phase"] == "acknowledged"
    assert pending["provider_order_id"] == "provider-order-1"
    assert ack_state["accounting"] == []
    assert ack_state["committed_receipt_ids"] == []
    assert chain.total_pnl == 0.0
    assert chain.wins_executed == []

    restarted = _chain(
        module,
        adapter=adapter,
        state_path=state_path,
        now=now,
    )
    read_count = len(adapter.read_calls)
    partial = restarted.execute_kill_chain(target)
    assert partial["status"] == "pending_reconciliation"
    assert partial["economic_mutation"] is False
    assert len(adapter.read_calls) == read_count + 1
    assert len(adapter.submit_calls) == 1
    assert state_path.read_bytes() == state_after_ack
    assert restarted.total_pnl == 0.0
    assert restarted.wins_executed == []

    read_count = len(adapter.read_calls)
    filled = restarted.execute_kill_chain(target)
    assert filled["status"] == "filled"
    assert filled["success"] is True
    assert filled["economic_mutation"] is True
    assert filled["filled_qty"] == "2"
    assert filled["filled_price"] == "110"
    assert filled["filled_notional"] == "220"
    assert filled["fee"] == "0.22"
    assert filled["fee_currency"] == "USD"
    assert filled["accounting"]["gross_pnl"] == "20"
    assert filled["accounting"]["fees"] == "0.42"
    assert filled["accounting"]["net_pnl"] == "19.58"
    assert len(adapter.read_calls) == read_count + 1
    assert restarted.total_pnl == 19.58
    assert len(restarted.wins_executed) == 1
    final_first = state_path.read_bytes()
    first_state = json.loads(final_first)
    assert first_state["pending"] == {}
    assert first_state["completed_actions"] == {
        "intent-close-1": "terminal-close-1"
    }
    assert first_state["committed_receipt_ids"] == [
        "terminal-close-1"
    ]
    assert first_state["accounting"][0]["net_pnl"] == "19.58"
    assert any("HNC/Auris receipt gates complete" in message for _, message in logs)
    assert any("Harvest complete" in message for _, message in logs)

    submit_count = len(adapter.submit_calls)
    read_count = len(adapter.read_calls)
    duplicate = restarted.execute_kill_chain(target)
    assert duplicate["status"] == "already_committed"
    assert duplicate["economic_mutation"] is False
    assert len(adapter.submit_calls) == submit_count
    assert len(adapter.read_calls) == read_count
    assert state_path.read_bytes() == final_first

    target_two = _target(
        now,
        intent_id="intent-close-2",
        position_id="BTC-POSITION-2",
    )
    second_ack = restarted.execute_kill_chain(target_two)
    assert second_ack["status"] == "pending_reconciliation"
    assert len(adapter.submit_calls) == submit_count + 1
    state_after_second_ack = state_path.read_bytes()
    accounting_before_rejection = list(
        json.loads(state_after_second_ack)["accounting"]
    )

    read_count = len(adapter.read_calls)
    rejected = restarted.execute_kill_chain(target_two)
    assert rejected["status"] == "pending_reconciliation"
    assert rejected["economic_mutation"] is False
    assert len(adapter.read_calls) == read_count + 1
    assert state_path.read_bytes() == state_after_second_ack
    assert json.loads(state_path.read_text(encoding="utf-8"))[
        "accounting"
    ] == accounting_before_rejection
    assert restarted.total_pnl == 19.58
    assert len(restarted.wins_executed) == 1
    assert not list(tmp_path.glob("*.tmp"))
    assert not list(tmp_path.glob("*.lock"))
