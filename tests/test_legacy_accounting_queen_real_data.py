import ast
import math
import time
from datetime import datetime
from pathlib import Path
from types import MethodType
from typing import Any, Dict, Optional


SOURCE = (
    Path(__file__).parents[1]
    / "Kings_Accounting_Suite"
    / "aureon_systems"
    / "queen_quantum_frog.py"
)


def _load_bounded_contract():
    """Load only pure receipt helpers/methods; never import the legacy runtime."""
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    helper_names = {
        "_finite_observed_number",
        "_provider_clock_seconds",
        "_fresh_provider_payload",
        "_strict_ticker_number",
        "_blocked_order_receipt",
    }
    method_names = {
        "_get_binance_ticker",
        "normalize_order_response",
        "is_order_successful",
    }
    selected = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in helper_names:
            selected.append(node)
        if isinstance(node, ast.ClassDef) and node.name == "OrcaKillCycle":
            selected.extend(
                child
                for child in node.body
                if isinstance(child, ast.FunctionDef) and child.name in method_names
            )
    namespace = {
        "Any": Any,
        "Dict": Dict,
        "Optional": Optional,
        "datetime": datetime,
        "math": math,
        "time": time,
        "_READY_PROVIDER_TRUTH": frozenset(
            {"live", "observed", "real_observed", "real_derived"}
        ),
        "_FINAL_FILL_STATUSES": frozenset({"FILLED", "CLOSED", "EXECUTED"}),
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


def test_legacy_queen_blocks_missing_stale_and_price_only_market_payloads():
    contract = _load_bounded_contract()
    strict_number = contract["_strict_ticker_number"]
    now_ms = int(time.time() * 1000)

    assert strict_number({"price": "10.5", "closeTime": now_ms}, "price") == 10.5
    assert strict_number({"price": "10.5"}, "price") is None
    assert (
        strict_number(
            {"price": "10.5", "closeTime": int((time.time() - 3600) * 1000)},
            "price",
        )
        is None
    )

    cycle = object()
    get_ticker = MethodType(contract["_get_binance_ticker"], cycle)

    class Complete:
        def get_24h_ticker(self, symbol):
            return {
                "symbol": symbol,
                "lastPrice": "100",
                "bidPrice": "99",
                "askPrice": "101",
                "closeTime": now_ms,
            }

    class PriceOnly:
        def get_ticker_price(self, _symbol):
            raise AssertionError("price-only fallback must never be used")

    ready = get_ticker(Complete(), "BTC/USDT")
    blocked = get_ticker(PriceOnly(), "BTC/USDT")

    assert ready["decision_status"] == "ready"
    assert ready["bid"] == 99.0
    assert ready["ask"] == 101.0
    assert blocked["decision_status"] == "blocked"
    assert blocked["action_eligible"] is False


def test_legacy_queen_requires_final_complete_fill_before_accounting():
    contract = _load_bounded_contract()
    cycle = object()
    normalize = MethodType(contract["normalize_order_response"], cycle)
    cycle = type("Cycle", (), {})()
    cycle.normalize_order_response = MethodType(
        contract["normalize_order_response"], cycle
    )
    successful = MethodType(contract["is_order_successful"], cycle)

    acknowledged = {
        "status": "NEW",
        "orderId": "ack-1",
        "executedQty": "1",
        "cummulativeQuoteQty": "100",
    }
    incomplete_final = {
        "status": "FILLED",
        "orderId": "fill-1",
        "executedQty": "1",
    }
    complete_final = {
        "status": "FILLED",
        "orderId": "fill-2",
        "executedQty": "1",
        "cummulativeQuoteQty": "100",
        "fee": "0.1",
    }

    assert normalize(acknowledged, "binance")["decision_status"] == "blocked"
    assert normalize(incomplete_final, "binance")["fill_verified"] is False
    receipt = normalize(complete_final, "binance")
    assert receipt["decision_status"] == "ready"
    assert receipt["filled_avg_price"] == 100.0
    assert receipt["accounting_eligible"] is True
    assert successful(acknowledged, "binance") is False
    assert successful(complete_final, "binance") is True
