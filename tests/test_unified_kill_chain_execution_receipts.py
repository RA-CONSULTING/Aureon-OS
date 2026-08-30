from __future__ import annotations

import ast
import copy
import math
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.validation.validate_real_data_contract import scan_text_file


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "aureon" / "trading" / "unified_kill_chain.py"


def _load_scoped_module():
    """Load only pure receipt helpers and execution methods; never import clients."""
    tree = ast.parse(TARGET.read_text(encoding="utf-8"), filename=str(TARGET))
    helper_names = {
        "_finite_provider_number",
        "_parse_provider_timestamp",
        "_valid_provider_identifier",
        "_first_present",
        "_provider_order_identifier",
        "_provider_trade_identifiers",
        "_execution_result",
        "_normalized_venue",
        "_normalized_symbol",
        "_same_observed_number",
        "_classify_action_evidence",
        "_classify_terminal_fill_receipt",
    }
    method_names = {
        "_evaluate_and_kill",
        "_close_capital",
        "_close_alpaca",
        "_close_binance",
        "_close_kraken",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name)
            and target.id.startswith(
                ("EXECUTION_RECEIPT_", "ACTION_EVIDENCE_")
            )
            for target in node.targets
        ):
            selected.append(copy.deepcopy(node))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in helper_names:
            selected.append(copy.deepcopy(node))
        elif isinstance(node, ast.ClassDef) and node.name == "UnifiedKillChain":
            scoped_class = copy.deepcopy(node)
            scoped_class.decorator_list = []
            scoped_class.body = [
                item
                for item in scoped_class.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name in method_names
            ]
            selected.append(scoped_class)

    logs = []
    namespace = {
        "math": math,
        "time": time,
        "datetime": datetime,
        "log_queen": lambda message: logs.append(("queen", message)),
        "log_auris": lambda message: logs.append(("auris", message)),
        "log_sniper": lambda message: logs.append(("sniper", message)),
        "log_warn": lambda message: logs.append(("warn", message)),
    }
    module = ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[]))
    exec(compile(module, str(TARGET), "exec"), namespace)
    return SimpleNamespace(**namespace), logs


def _live_receipt(
    now: float,
    *,
    venue: str = "kraken",
    symbol: str | None = None,
    filled_qty: float = 2.5,
):
    symbol = symbol or ("BTCUSD" if venue == "kraken" else "ETHUSDT")
    receipt = {
        "status": "FILLED",
        "data_status": "live",
        "truth_status": "real_observed",
        "orderId": "ORDER-982374",
        "fills": [{"tradeId": "TRADE-782346"}],
        "filled_qty": str(filled_qty),
        "filled_avg_price": "41.25",
        "fee": "0.18",
        "fee_currency": "USD",
        "provider_timestamp": now,
        "receipt_id": f"{venue}-terminal-receipt-982374",
        "provider_receipt_type": "QueryOrders" if venue == "kraken" else "OrderStatus",
        "venue": venue,
        "symbol": symbol,
        "side": "SELL",
        "fill_receipt_complete": True,
        "eligible_for_accounting": True,
        "eligible_for_learning": True,
        "generated_values": False,
        "reconciliation_required": False,
    }
    return receipt


def _action_receipts(
    now: float,
    *,
    venue: str,
    symbol: str,
    position_id: str,
    quantity: float,
    pnl: float,
    entry_price: float,
    current_price: float,
):
    position_receipt_id = f"{venue}-position-receipt-24711"
    position = {
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "eligible_for_action": True,
        "venue": venue,
        "symbol": symbol,
        "source_id": f"{venue}:positions",
        "source_timestamp": now,
        "received_at": now,
        "receipt_id": position_receipt_id,
        "position_id": position_id,
        "quantity": quantity,
    }
    opportunity = {
        "data_status": "live",
        "truth_status": "real_derived",
        "generated_values": False,
        "eligible_for_action": True,
        "venue": venue,
        "symbol": symbol,
        "source_id": "aureon:unified_kill_chain",
        "source_timestamp": now,
        "received_at": now,
        "receipt_id": f"{venue}-opportunity-receipt-98273",
        "position_receipt_id": position_receipt_id,
        "pnl": pnl,
        "entry_price": entry_price,
        "current_price": current_price,
    }
    return position, opportunity


def _approved_validation():
    return {
        "approved": True,
        "timestamp": "2026-08-10T12:00:00+00:00",
        "reasoning": "two provider-backed votes",
        "confidence": 0.91,
        "votes_for": 2,
    }


def test_complete_fresh_kraken_query_receipt_is_the_only_success_path():
    module, _ = _load_scoped_module()
    now = time.time()

    result = module._classify_terminal_fill_receipt(
        _live_receipt(now),
        "kraken",
        now=now,
    )

    assert result["success"] is True
    assert result["status"] == "filled"
    assert result["order_id"] == "ORDER-982374"
    assert result["trade_ids"] == ["TRADE-782346"]
    assert result["filled_qty"] == 2.5
    assert result["filled_price"] == 41.25
    assert result["fee"] == 0.18


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("data_status", "pending_reconciliation"),
        ("status", "PARTIALLY_FILLED"),
        ("fill_receipt_complete", False),
        ("eligible_for_accounting", False),
        ("eligible_for_learning", False),
        ("filled_qty", None),
        ("filled_avg_price", "not-a-number"),
        ("fee", None),
        ("provider_timestamp", None),
    ],
)
def test_incomplete_terminal_fields_never_become_success(field, value):
    module, _ = _load_scoped_module()
    now = time.time()
    receipt = _live_receipt(now)
    receipt[field] = value

    result = module._classify_terminal_fill_receipt(receipt, "kraken", now=now)

    assert result["success"] is False
    assert result["status"] == "pending_reconciliation"
    assert result["eligible_for_accounting"] is False


def test_stale_timestamp_and_sentinel_ids_fail_closed():
    module, _ = _load_scoped_module()
    now = time.time()
    stale = _live_receipt(now - 301)
    bad_order = _live_receipt(now)
    bad_order["orderId"] = "unknown"
    bad_trade = _live_receipt(now)
    bad_trade["fills"] = [{"tradeId": "fake-trade-1"}]

    for receipt in (stale, bad_order, bad_trade):
        result = module._classify_terminal_fill_receipt(receipt, "kraken", now=now)
        assert result["success"] is False
        assert result["status"] in {"no_data", "pending_reconciliation"}


def test_add_order_acknowledgement_is_pending_not_a_fill():
    module, _ = _load_scoped_module()
    acknowledgement = {
        "provider": "kraken",
        "provider_receipt_type": "AddOrder",
        "orderId": "ORDER-552211",
        "status": "pending_reconciliation",
        "data_status": "pending_reconciliation",
        "submitted": True,
        "reconciliation_required": True,
        "fill_receipt_complete": False,
        "eligible_for_accounting": False,
        "generated_values": False,
    }

    result = module._classify_terminal_fill_receipt(
        acknowledgement,
        "kraken",
        submission_attempted=True,
    )

    assert result["success"] is False
    assert result["status"] == "pending_reconciliation"
    assert result["filled_qty"] is None
    assert result["filled_price"] is None
    assert result["fee"] is None


def test_kraken_closer_performs_one_readback_and_never_resubmits():
    module, _ = _load_scoped_module()
    now = time.time()
    terminal = _live_receipt(now)

    class Kraken:
        def __init__(self):
            self.submit_calls = 0
            self.query_calls = 0

        def place_market_order(self, symbol, side, qty):
            self.submit_calls += 1
            return {
                "provider_receipt_type": "AddOrder",
                "orderId": "ORDER-982374",
                "status": "pending_reconciliation",
                "data_status": "pending_reconciliation",
                "submitted": True,
                "reconciliation_required": True,
                "fill_receipt_complete": False,
                "eligible_for_accounting": False,
                "generated_values": False,
            }

        def get_order_status(self, order_id):
            self.query_calls += 1
            assert order_id == "ORDER-982374"
            return terminal

    chain = module.UnifiedKillChain.__new__(module.UnifiedKillChain)
    chain.kraken = Kraken()

    receipt = chain._close_kraken("BTC", 2.5, "BTCUSD")
    result = module._classify_terminal_fill_receipt(receipt, "kraken", now=now)

    assert result["success"] is True
    assert chain.kraken.submit_calls == 1
    assert chain.kraken.query_calls == 1


def test_kraken_dry_run_receipt_is_not_submitted_and_not_queried():
    module, _ = _load_scoped_module()

    class Kraken:
        def __init__(self):
            self.query_calls = 0

        def place_market_order(self, symbol, side, qty):
            return {
                "dryRun": True,
                "submitted": False,
                "status": "not_submitted",
                "data_status": "not_submitted",
                "generated_values": False,
            }

        def get_order_status(self, order_id):
            self.query_calls += 1
            raise AssertionError("dry run must not query an order")

    chain = module.UnifiedKillChain.__new__(module.UnifiedKillChain)
    chain.kraken = Kraken()
    receipt = chain._close_kraken("BTC", 2.5, "BTCUSD")
    result = module._classify_terminal_fill_receipt(
        receipt,
        "kraken",
        submission_attempted=True,
    )

    assert result["status"] == "not_submitted"
    assert result["success"] is False
    assert chain.kraken.query_calls == 0


@pytest.mark.parametrize(
    ("venue", "acknowledgement"),
    [
        (
            "capital",
            {
                "status": "submitted",
                "dealReference": "DEAL-12773",
                "submission_acknowledged": True,
                "generated_values": False,
            },
        ),
        ("alpaca", {"id": "ORDER-27334", "status": "accepted"}),
        ("binance", {"orderId": 982374, "status": "FILLED", "fills": []}),
    ],
)
def test_other_venue_acknowledgements_never_count_as_fills(venue, acknowledgement):
    module, _ = _load_scoped_module()

    result = module._classify_terminal_fill_receipt(
        acknowledgement,
        venue,
        submission_attempted=True,
    )

    assert result["success"] is False
    assert result["status"] == "pending_reconciliation"
    assert result["eligible_for_accounting"] is False


def test_pending_ack_is_latched_before_a_second_vote_or_close_attempt():
    module, logs = _load_scoped_module()
    now = time.time()
    chain = module.UnifiedKillChain.__new__(module.UnifiedKillChain)
    chain._pending_reconciliations = {}
    vote_calls = []
    close_calls = []
    chain._validate_with_dr_auris = lambda **kwargs: vote_calls.append(kwargs) or _approved_validation()

    def close_once(*args):
        close_calls.append(args)
        return {
            "orderId": "ORDER-55128",
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "submitted": True,
            "reconciliation_required": True,
            "fill_receipt_complete": False,
            "eligible_for_accounting": False,
            "generated_values": False,
        }

    position, opportunity = _action_receipts(
        now,
        venue="kraken",
        symbol="BTCUSD",
        position_id="BTC",
        quantity=0.25,
        pnl=8.5,
        entry_price=100.0,
        current_price=134.0,
    )
    first = chain._evaluate_and_kill(
        "Kraken",
        "BTCUSD",
        8.5,
        "BTC",
        0.25,
        None,
        close_once,
        100.0,
        134.0,
        position_receipt=position,
        opportunity_receipt=opportunity,
        now=now,
    )
    second = chain._evaluate_and_kill(
        "Kraken",
        "BTCUSD",
        8.5,
        "BTC",
        0.25,
        None,
        close_once,
        100.0,
        134.0,
        position_receipt=position,
        opportunity_receipt=opportunity,
        now=now,
    )

    assert first["status"] == "pending_reconciliation"
    assert second is first
    assert len(close_calls) == 1
    assert len(vote_calls) == 1
    assert not any("Profit Realized" in message for _, message in logs)
    assert not any("Harvest complete" in message for _, message in logs)


def test_boolean_acknowledgement_cannot_trigger_realized_profit_logging():
    module, logs = _load_scoped_module()
    now = time.time()
    chain = module.UnifiedKillChain.__new__(module.UnifiedKillChain)
    chain._pending_reconciliations = {}
    chain._validate_with_dr_auris = lambda **kwargs: _approved_validation()

    position, opportunity = _action_receipts(
        now,
        venue="binance",
        symbol="ETHUSDT",
        position_id="ETH",
        quantity=0.5,
        pnl=5.0,
        entry_price=100.0,
        current_price=110.0,
    )
    result = chain._evaluate_and_kill(
        "Binance",
        "ETHUSDT",
        5.0,
        "ETH",
        0.5,
        None,
        lambda *args: True,
        100.0,
        110.0,
        position_receipt=position,
        opportunity_receipt=opportunity,
        now=now,
    )

    assert result["success"] is False
    assert result["status"] == "pending_reconciliation"
    assert not any("Profit Realized" in message for _, message in logs)


def test_realized_profit_logging_requires_complete_terminal_receipt():
    module, logs = _load_scoped_module()
    now = time.time()
    chain = module.UnifiedKillChain.__new__(module.UnifiedKillChain)
    chain._pending_reconciliations = {}
    chain._validate_with_dr_auris = lambda **kwargs: _approved_validation()

    position, opportunity = _action_receipts(
        now,
        venue="binance",
        symbol="ETHUSDT",
        position_id="ETH",
        quantity=0.5,
        pnl=5.0,
        entry_price=100.0,
        current_price=110.0,
    )
    result = chain._evaluate_and_kill(
        "Binance",
        "ETHUSDT",
        5.0,
        "ETH",
        0.5,
        None,
        lambda *args: _live_receipt(
            now,
            venue="binance",
            symbol="ETHUSDT",
            filled_qty=0.5,
        ),
        100.0,
        110.0,
        position_receipt=position,
        opportunity_receipt=opportunity,
        now=now,
    )

    assert result["success"] is True
    assert any("Profit Realized" in message for _, message in logs)
    assert any("Harvest complete" in message for _, message in logs)


def test_missing_action_receipts_never_reach_auris_or_order_submission():
    module, _ = _load_scoped_module()
    chain = module.UnifiedKillChain.__new__(module.UnifiedKillChain)
    chain._pending_reconciliations = {}
    chain._validate_with_dr_auris = lambda **kwargs: pytest.fail(
        "Auris must not receive unproven action evidence"
    )

    result = chain._evaluate_and_kill(
        "Binance",
        "ETHUSDT",
        5.0,
        "ETH",
        0.5,
        None,
        lambda *args: pytest.fail("order submission must remain unreachable"),
        100.0,
        110.0,
        now=time.time(),
    )

    assert result["success"] is False
    assert result["status"] == "no_data"
    assert result["reason"] == "fresh_position_receipt_required"


def test_strict_real_data_validator_accepts_unified_kill_chain():
    assert scan_text_file(TARGET, ROOT) == []
