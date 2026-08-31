from __future__ import annotations

import ast
import copy
import itertools
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Mapping, Optional, Tuple

import pytest

from aureon.queen import queen_force_trade_governance as force_governance
from scripts.validation.validate_real_data_contract import scan_text_file


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aureon" / "queen" / "queen_eternal_machine.py"
_AUTH_SEQUENCE = itertools.count(1)


def _mint_offline_authorization(plan):
    """Mint only inside this offline fixture using a deterministic fake verifier."""

    original = force_governance.validate_magic_star_v02
    sequence = next(_AUTH_SEQUENCE)

    def verified(*_args, **_kwargs):
        return {
            "valid": True,
            "production_ready": True,
            "star_commitment": f"{sequence:064x}",
            "expires_at_ms": 9_999_999_999_999,
        }

    force_governance.validate_magic_star_v02 = verified
    try:
        return force_governance._mint_magic_star_authorization(
            star=object(),
            trust={},
            plan=plan,
            trusted_now_ms=lambda: 1,
        )
    finally:
        force_governance.validate_magic_star_v02 = original


def _claim_offline_authorization(**kwargs):
    """Test-only receipt-lifecycle seam; never used by the runtime module."""

    plan = kwargs["plan"]
    return force_governance.QueenForceTradeDecision(
        allowed=True,
        reason="offline_receipt_lifecycle_fixture_only",
        plan_sha256=plan.commitment,
    )


def _load_receipt_scope():
    """Load only Queen receipt and execution nodes; never import a client."""
    tree = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))
    helper_names = {
        "_first_receipt_value",
        "_finite_receipt_number",
        "_provider_receipt_timestamp",
        "_valid_provider_identifier",
        "_pair_assets",
        "_provider_symbol_matches",
        "_classify_terminal_order_receipt",
    }
    data_class_names = {
        "Friend",
        "Breadcrumb",
        "MainPosition",
        "MarketCoin",
        "LeapOpportunity",
    }
    method_names = {
        "_order_failed",
        "_pending_order_key",
        "_pending_registry",
        "_not_submitted_receipt",
        "_remember_pending_order",
        "_commit_resolved_orders",
        "_remember_terminal_uncommitted",
        "_reuse_terminal_uncommitted",
        "_resolve_terminal_fill",
        "_record_observed_fees",
        "_net_base_quantity",
        "_extract_order_id",
        "_log_order_id",
        "_log_order_summary",
        "_place_market_order",
        "execute_quantum_leap",
        "start_journey",
        "execute_scalp",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name)
            and target.id.startswith("ORDER_RECEIPT_")
            for target in node.targets
        ):
            selected.append(copy.deepcopy(node))
        elif isinstance(node, ast.FunctionDef) and node.name in helper_names:
            selected.append(copy.deepcopy(node))
        elif isinstance(node, ast.ClassDef) and node.name in data_class_names:
            selected.append(copy.deepcopy(node))
        elif isinstance(node, ast.ClassDef) and node.name == "QueenEternalMachine":
            scoped_class = copy.deepcopy(node)
            scoped_class.body = [
                item
                for item in scoped_class.body
                if isinstance(item, ast.FunctionDef)
                and item.name in method_names
            ]
            selected.append(scoped_class)

    namespace = {
        "Any": Any,
        "Dict": Dict,
        "List": List,
        "Mapping": Mapping,
        "Optional": Optional,
        "Tuple": Tuple,
        "ForceTradePlan": force_governance.ForceTradePlan,
        "claim_queen_force_trade_authority": _claim_offline_authorization,
        "dataclass": dataclass,
        "datetime": datetime,
        "logging": logging,
        "logger": logging.getLogger("queen-receipt-offline-test"),
        "math": math,
        "time": time,
    }
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    exec(compile(module, str(TARGET), "exec"), namespace)
    return SimpleNamespace(**namespace)


def _kraken_ack(order_id: str = "OQCLML-BW3P3-BUCMWZ") -> dict:
    return {
        "provider": "kraken",
        "provider_receipt_type": "AddOrder",
        "orderId": order_id,
        "symbol": "XETHZUSD",
        "side": "SELL",
        "status": "pending_reconciliation",
        "data_status": "pending_reconciliation",
        "truth_status": "real_observed",
        "submitted": True,
        "reconciliation_required": True,
        "fill_receipt_complete": False,
        "eligible_for_accounting": False,
        "eligible_for_learning": False,
        "generated_values": False,
    }


def _kraken_fill(
    *,
    side: str = "SELL",
    symbol: str = "XETHZUSD",
    quantity: float = 1.25,
    price: float = 2000.0,
    fee: float = 6.5,
    timestamp: Optional[float] = None,
) -> dict:
    provider_time = time.time() if timestamp is None else timestamp
    return {
        "provider": "kraken",
        "provider_receipt_type": "QueryOrders",
        "orderId": "OQCLML-BW3P3-BUCMWZ",
        "symbol": symbol,
        "side": side,
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "executedQty": str(quantity),
        "filled_qty": str(quantity),
        "avgPrice": str(price),
        "filled_avg_price": str(price),
        "cummulativeQuoteQty": str(quantity * price),
        "filled_notional": str(quantity * price),
        "fee": str(fee),
        "fee_asset": "USD",
        "fee_currency": "USD",
        "fills": [{"tradeId": "TCCCTY-WE2O6-P3NB37"}],
        "provider_timestamp": provider_time,
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "generated_values": False,
        "reconciliation_required": False,
    }


def _binance_fill(
    *,
    order_id: int,
    trade_id: int,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    commission: float,
    commission_asset: str,
    timestamp: Optional[float] = None,
) -> dict:
    provider_time = time.time() if timestamp is None else timestamp
    return {
        "symbol": symbol,
        "orderId": order_id,
        "side": side,
        "status": "FILLED",
        "transactTime": int(provider_time * 1000),
        "executedQty": str(quantity),
        "cummulativeQuoteQty": str(quantity * price),
        "avg_fill_price": price,
        "fills": [
            {
                "tradeId": trade_id,
                "qty": str(quantity),
                "price": str(price),
                "commission": str(commission),
                "commissionAsset": commission_asset,
            }
        ],
        "fills_verified": True,
    }


class OfflineClient:
    def __init__(self, submissions: List[dict], readback: Optional[dict] = None):
        self.submissions = list(submissions)
        self.readback = readback
        self.place_calls: List[dict] = []
        self.read_calls: List[str] = []
        self.dry_run = False

    def place_market_order(
        self,
        pair,
        side,
        *,
        quantity=None,
        quote_qty=None,
    ):
        self.place_calls.append(
            {
                "pair": pair,
                "side": side,
                "quantity": quantity,
                "quote_qty": quote_qty,
            }
        )
        if not self.submissions:
            raise AssertionError("unexpected order submission")
        return self.submissions.pop(0)

    def get_order_status(self, order_id):
        self.read_calls.append(order_id)
        return copy.deepcopy(self.readback)


def _machine(module, client: OfflineClient, *, live: bool = True):
    machine = module.QueenEternalMachine.__new__(module.QueenEternalMachine)
    machine.live_trading = live
    machine.dry_run = not live
    machine.exchange = "binance"
    machine.breadcrumb_percent = 0.05
    machine._pending_orders = {}
    machine.last_execution_receipt = None
    machine.observed_fees_by_asset = {}
    machine.total_fees_paid = 0.0
    machine.total_slippage_cost = 0.0
    machine.total_leaps = 0
    machine.total_breadcrumbs = 0
    machine.total_scalps = 0
    machine.total_profit_realized = 0.0
    machine.available_cash = 0.0
    machine.breadcrumbs = {}
    machine.friends = {}
    machine.market_data = {}
    machine.main_position = None
    machine.start_time = None
    machine._order_status_reader = (
        lambda _exchange, order_id: client.get_order_status(order_id)
    )
    machine._balance_reader = lambda _exchange: {}
    machine._pair_candidates = (
        lambda symbol, exchange: [f"{symbol.upper()}USDT"]
        if exchange == "binance"
        else [f"{symbol.upper()}USD"]
    )
    machine._authorization_provider = _mint_offline_authorization

    def dispatch(plan):
        quantity = (
            float(plan.quantity) if plan.quantity_kind == "base_units" else None
        )
        quote_qty = (
            float(plan.quantity) if plan.quantity_kind == "quote_units" else None
        )
        return client.place_market_order(
            plan.symbol,
            plan.side,
            quantity=quantity,
            quote_qty=quote_qty,
        )

    machine._final_order_dispatcher = dispatch
    machine._save_calls = 0

    def save_state():
        machine._save_calls += 1

    machine._save_state = save_state
    return machine


def _opportunity(module):
    return module.LeapOpportunity(
        from_symbol="ETH",
        to_symbol="BTC",
        from_price=100.0,
        to_price=50_000.0,
        from_change=-2.0,
        to_change=-8.0,
        dip_advantage=6.0,
        quantity_multiplier=1.1,
        recovery_advantage=6.0,
        gross_value=950.0,
        sell_fee_cost=1.0,
        buy_fee_cost=1.0,
        slippage_cost=1.0,
        total_fees=3.0,
        net_value_after_fees=947.0,
        fee_adjusted_multiplier=1.01,
    )


def test_add_order_ack_is_pending_and_never_accounting_eligible():
    module = _load_receipt_scope()

    receipt = module._classify_terminal_order_receipt(
        _kraken_ack(),
        "kraken",
        expected_side="SELL",
        expected_symbol="ETH",
    )

    assert receipt["success"] is False
    assert receipt["status"] == "pending_reconciliation"
    assert receipt["filled_qty"] is None
    assert receipt["eligible_for_accounting"] is False
    assert receipt["eligible_for_learning"] is False


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        ({"provider_timestamp": 1_700_000_000.0}, "stale"),
        ({"fee": None}, "fee"),
        ({"status": "PARTIALLY_FILLED"}, "terminal"),
        ({"provider_receipt_type": "AddOrder"}, "terminal"),
    ],
)
def test_stale_or_incomplete_receipts_fail_closed(change, reason):
    module = _load_receipt_scope()
    receipt = _kraken_fill()
    for key, value in change.items():
        receipt[key] = value

    classified = module._classify_terminal_order_receipt(
        receipt,
        "kraken",
        expected_side="SELL",
        expected_symbol="ETH",
    )

    assert classified["success"] is False
    assert reason in classified["reason"]
    assert classified["eligible_for_accounting"] is False


def test_terminal_receipt_for_another_symbol_fails_closed():
    module = _load_receipt_scope()
    receipt = _kraken_fill(symbol="XXBTZUSD")

    classified = module._classify_terminal_order_receipt(
        receipt,
        "kraken",
        expected_side="SELL",
        expected_symbol="ETH",
    )

    assert classified["success"] is False
    assert classified["reason"] == "provider_order_symbol_mismatch"


def test_pending_submission_blocks_duplicate_and_uses_readback_only():
    module = _load_receipt_scope()
    client = OfflineClient([_kraken_ack()], readback=_kraken_ack())
    machine = _machine(module, client)
    machine.exchange = "kraken"

    first = machine._place_market_order(
        "kraken", "ETH", "SELL", quantity=1.25
    )
    second = machine._place_market_order(
        "kraken", "ETH", "SELL", quantity=1.25
    )
    resolved = machine._resolve_terminal_fill(
        "kraken", "ETH", "SELL", second, quantity=1.25
    )

    assert first["status"] == "pending_reconciliation"
    assert second["reason"] == "existing_order_requires_terminal_reconciliation"
    assert resolved["success"] is False
    assert len(client.place_calls) == 1
    assert client.read_calls == ["OQCLML-BW3P3-BUCMWZ"]


def test_terminal_readback_keeps_duplicate_block_until_state_commit():
    module = _load_receipt_scope()
    client = OfflineClient([_kraken_ack()], readback=_kraken_fill())
    machine = _machine(module, client)
    machine.exchange = "kraken"

    submitted = machine._place_market_order(
        "kraken", "ETH", "SELL", quantity=1.25
    )
    resolved = machine._resolve_terminal_fill(
        "kraken", "ETH", "SELL", submitted, quantity=1.25
    )
    key = machine._pending_order_key("kraken", "ETH", "SELL")

    assert resolved["success"] is True
    assert key in machine._pending_orders
    assert len(client.place_calls) == 1

    machine._commit_resolved_orders(("kraken", "ETH", "SELL"))

    assert key not in machine._pending_orders
    assert len(client.place_calls) == 1


def test_ambiguous_provider_error_blocks_resubmission():
    module = _load_receipt_scope()
    client = OfflineClient([{"error": "provider_transport_uncertain"}])
    machine = _machine(module, client)

    first = machine._place_market_order(
        "binance", "ETH", "SELL", quantity=1.25
    )
    second = machine._place_market_order(
        "binance", "ETH", "SELL", quantity=1.25
    )

    assert first["status"] == "pending_reconciliation"
    assert first["reason"] == "ambiguous_provider_error_response"
    assert second["reason"] == "existing_order_requires_terminal_reconciliation"
    assert len(client.place_calls) == 1


def test_pending_sell_never_submits_dependent_buy_or_mutates_state():
    module = _load_receipt_scope()
    client = OfflineClient([_kraken_ack()], readback=_kraken_ack())
    machine = _machine(module, client)
    machine.exchange = "kraken"
    position = module.MainPosition(
        symbol="ETH",
        quantity=10.0,
        cost_basis=1000.0,
        entry_price=100.0,
        entry_time=datetime.fromtimestamp(time.time() - 60),
        current_price=110.0,
        change_24h=-2.0,
    )
    machine.main_position = position

    result = machine.execute_quantum_leap(_opportunity(module))

    assert result is False
    assert machine.main_position is position
    assert machine.breadcrumbs == {}
    assert machine.total_leaps == 0
    assert machine.total_breadcrumbs == 0
    assert machine.observed_fees_by_asset == {}
    assert machine._save_calls >= 1
    assert len(client.place_calls) == 1
    assert all(call["side"] == "SELL" for call in client.place_calls)


def test_terminal_sell_then_pending_buy_cannot_resubmit_sell():
    module = _load_receipt_scope()
    sell = _binance_fill(
        order_id=812345,
        trade_id=612345,
        symbol="ETHUSDT",
        side="SELL",
        quantity=9.5,
        price=100.0,
        commission=0.95,
        commission_asset="USDT",
    )
    buy_ack = {
        "symbol": "BTCUSDT",
        "orderId": 812346,
        "side": "BUY",
        "status": "NEW",
        "transactTime": int(time.time() * 1000),
    }
    client = OfflineClient([sell, buy_ack])
    machine = _machine(module, client)
    position = module.MainPosition(
        symbol="ETH",
        quantity=10.0,
        cost_basis=1000.0,
        entry_price=100.0,
        entry_time=datetime.fromtimestamp(time.time() - 60),
        current_price=110.0,
        change_24h=-2.0,
    )
    machine.main_position = position

    first = machine.execute_quantum_leap(_opportunity(module))
    second = machine.execute_quantum_leap(_opportunity(module))

    assert first is False
    assert second is False
    assert machine.main_position is position
    assert len(client.place_calls) == 2
    assert [call["side"] for call in client.place_calls] == ["SELL", "BUY"]
    sell_key = machine._pending_order_key("binance", "ETH", "SELL")
    buy_key = machine._pending_order_key("binance", "BTC", "BUY")
    assert machine._pending_orders[sell_key]["status"] == (
        "terminal_fill_uncommitted"
    )
    assert machine._pending_orders[buy_key]["status"] == (
        "pending_reconciliation"
    )


def test_terminal_two_leg_receipts_commit_actual_fills_only():
    module = _load_receipt_scope()
    sell = _binance_fill(
        order_id=812345,
        trade_id=612345,
        symbol="ETHUSDT",
        side="SELL",
        quantity=9.5,
        price=100.0,
        commission=0.95,
        commission_asset="USDT",
    )
    buy = _binance_fill(
        order_id=812346,
        trade_id=612346,
        symbol="BTCUSDT",
        side="BUY",
        quantity=0.018981,
        price=50_000.0,
        commission=0.000001,
        commission_asset="BTC",
    )
    client = OfflineClient([sell, buy])
    machine = _machine(module, client)
    machine.main_position = module.MainPosition(
        symbol="ETH",
        quantity=10.0,
        cost_basis=1000.0,
        entry_price=100.0,
        entry_time=datetime.fromtimestamp(time.time() - 60),
        current_price=110.0,
        change_24h=-2.0,
    )

    result = machine.execute_quantum_leap(_opportunity(module))

    assert result is True
    assert len(client.place_calls) == 2
    assert client.place_calls[0]["side"] == "SELL"
    assert client.place_calls[1]["side"] == "BUY"
    assert client.place_calls[1]["quote_qty"] == pytest.approx(949.05)
    assert machine.main_position.symbol == "BTC"
    assert machine.main_position.quantity == pytest.approx(0.01898)
    assert machine.main_position.entry_price == pytest.approx(50_000.0)
    assert machine.main_position.cost_basis == pytest.approx(949.05)
    assert machine.breadcrumbs["ETH"].quantity == pytest.approx(0.5)
    assert machine.breadcrumbs["ETH"].cost_basis == pytest.approx(50.0)
    assert machine.observed_fees_by_asset == pytest.approx(
        {"USDT": 0.95, "BTC": 0.000001}
    )
    assert machine.total_fees_paid == 0.0
    assert machine.total_slippage_cost == 0.0
    assert machine.total_leaps == 1
    assert machine._save_calls == 3


def test_dry_run_quantum_leap_is_not_submitted_and_mutation_free():
    module = _load_receipt_scope()
    client = OfflineClient([])
    machine = _machine(module, client, live=False)
    position = module.MainPosition(
        symbol="ETH",
        quantity=10.0,
        cost_basis=1000.0,
        entry_price=100.0,
        entry_time=datetime.fromtimestamp(time.time() - 60),
        current_price=110.0,
        change_24h=-2.0,
    )
    machine.main_position = position

    result = machine.execute_quantum_leap(_opportunity(module))

    assert result is False
    assert client.place_calls == []
    assert machine.main_position is position
    assert machine.breadcrumbs == {}
    assert machine.last_execution_receipt["status"] == "not_submitted"
    assert machine.last_execution_receipt["submitted"] is False
    assert machine._save_calls == 0


def test_pending_journey_buy_does_not_create_position_or_spend_cash():
    module = _load_receipt_scope()
    ack = _kraken_ack()
    ack["side"] = "BUY"
    client = OfflineClient([ack], readback=ack)
    machine = _machine(module, client)
    machine.exchange = "kraken"
    machine.available_cash = 1000.0
    machine.initial_vault = 1000.0
    machine.market_data["ETH"] = module.MarketCoin(
        symbol="ETH",
        price=2000.0,
        change_24h=-3.0,
        volume_24h=1_000_000.0,
    )
    machine.fetch_market_data = lambda: None

    result = machine.start_journey("ETH")

    assert result is False
    assert machine.main_position is None
    assert machine.available_cash == 1000.0
    assert machine.start_time is None
    assert machine._save_calls >= 1
    assert len(client.place_calls) == 1


def test_pending_scalp_does_not_advance_pnl_learning_or_breadcrumb():
    module = _load_receipt_scope()
    client = OfflineClient([_kraken_ack()], readback=_kraken_ack())
    machine = _machine(module, client)
    machine.exchange = "kraken"
    crumb = module.Breadcrumb(
        symbol="ETH",
        quantity=2.0,
        cost_basis=200.0,
        entry_price=100.0,
        entry_time=datetime.fromtimestamp(time.time() - 60),
        current_price=120.0,
        exchange="kraken",
    )
    machine.breadcrumbs["ETH"] = crumb
    machine._get_available_base_quantity = lambda exchange, symbol: 2.0

    result = machine.execute_scalp("ETH", 0.5)

    assert result == 0.0
    assert crumb.quantity == 2.0
    assert crumb.cost_basis == 200.0
    assert machine.available_cash == 0.0
    assert machine.total_profit_realized == 0.0
    assert machine.total_scalps == 0
    assert machine._save_calls >= 1


def test_hardened_validator_accepts_queen_receipt_changes():
    findings = scan_text_file(TARGET, ROOT)
    assert [
        (finding.severity, finding.code, finding.line)
        for finding in findings
        if finding.severity == "error"
    ] == []
