from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
from typing import Any

from aureon.governance.legacy_unity_composition import LegacyUnityIntentPlan
from aureon.trading.unified_exchange_client import MultiExchangeClient
from Kings_Accounting_Suite.aureon_systems import (
    queen_profit_dashboard as dashboard,
)

SOURCE = (
    Path(__file__).resolve().parents[1]
    / "Kings_Accounting_Suite"
    / "aureon_systems"
    / "queen_profit_dashboard.py"
)


def _plan(*, quantity: str = "1.25") -> LegacyUnityIntentPlan:
    return LegacyUnityIntentPlan.create(
        capability_id="legacy-capability:queen-profit-dashboard:kraken-exit",
        venue="kraken",
        environment="live",
        account_id_hash="a" * 64,
        method="POST",
        path="/0/private/AddOrder",
        operation="MARKET_ORDER",
        purpose="EXIT",
        symbol="XBTUSD",
        side="SELL",
        order_type="MARKET",
        quantity=quantity,
        quote_quantity=None,
        limit_price=None,
        stop_price=None,
        take_profit=None,
        reduce_only=True,
        client_order_id="queen-profit-exit-1",
        authorization_receipt_id="authorization:queen-profit-exit:1",
        cycle_id="cycle:queen-profit-exit:1",
        position_receipt_id="provider:kraken:position:xbt",
        parent_intent_digest="b" * 64,
        entry_receipt_id="provider:kraken:fill:xbt-entry",
        position_side="LONG",
        observed_exposure_quantity="1.25",
        body={
            "ordertype": "market",
            "pair": "XBTUSD",
            "type": "sell",
            "volume": quantity,
        },
        body_bindings={
            "order_type": "/ordertype",
            "quantity": "/volume",
            "side": "/type",
            "symbol": "/pair",
        },
    )


class _CanonicalClient(MultiExchangeClient):
    def __init__(self, result: dict[str, Any] | None = None) -> None:
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
        self.result = result or {
            "status": "pending_reconciliation",
            "submitted": True,
            "provider_order_id": "K-EXIT-1",
            "aureon_legacy_unity_receipt": {
                "status": "EXECUTED",
                "reason": "legacy_capability_executed_through_exact_economic_boundary",
            },
        }

    def place_market_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append((args, kwargs))
        return dict(self.result)


def test_missing_canonical_composition_holds_before_plan_or_transport() -> None:
    supplier_calls = 0

    def supplier(symbol: str, quantity: float) -> LegacyUnityIntentPlan:
        nonlocal supplier_calls
        supplier_calls += 1
        return _plan(quantity=str(quantity))

    result = dashboard.execute_governed_profit_sell(
        mutation_client=None,
        unity_plan_supplier=supplier,
        symbol="XBTUSD",
        quantity=1.25,
    )

    assert result["status"] == "HOLD"
    assert result["reason"] == "canonical_profit_exit_client_required"
    assert result["economic_mutation"] is False
    assert result["action_eligible"] is False
    assert supplier_calls == 0


def test_mismatched_plan_holds_before_canonical_client() -> None:
    client = _CanonicalClient()
    mismatched = replace(_plan(), side="BUY")

    result = dashboard.execute_governed_profit_sell(
        mutation_client=client,
        unity_plan_supplier=lambda _symbol, _quantity: mismatched,
        symbol="XBTUSD",
        quantity=1.25,
    )

    assert result["status"] == "HOLD"
    assert result["reason"] == "canonical_profit_exit_plan_mismatch"
    assert client.calls == []


def test_exact_exit_plan_reaches_only_canonical_client_once() -> None:
    client = _CanonicalClient()
    plan = _plan()

    result = dashboard.execute_governed_profit_sell(
        mutation_client=client,
        unity_plan_supplier=lambda symbol, quantity: (
            plan if (symbol, quantity) == ("XBTUSD", 1.25) else None
        ),
        symbol="XBTUSD",
        quantity=1.25,
    )

    assert result["submitted"] is True
    assert dashboard._governed_profit_sell_submitted(result) is True
    assert client.calls == [
        (
            ("kraken", "XBTUSD", "sell"),
            {"quantity": 1.25, "unity_plan": plan},
        )
    ]


def test_hold_receipt_is_never_counted_as_a_sell() -> None:
    client = _CanonicalClient(
        {
            "status": "no_data",
            "truth_status": "no_data",
            "reason": "council_hold",
            "submitted": False,
        }
    )

    result = dashboard.execute_governed_profit_sell(
        mutation_client=client,
        unity_plan_supplier=lambda _symbol, _quantity: _plan(),
        symbol="XBTUSD",
        quantity=1.25,
    )

    assert dashboard._governed_profit_sell_submitted(result) is False
    assert len(client.calls) == 1


def test_dashboard_contains_no_raw_kraken_mutation_call() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    raw_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "place_market_order"
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "kraken"
    ]

    assert raw_calls == []
