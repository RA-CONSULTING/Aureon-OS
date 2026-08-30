from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from aureon.governance.legacy_unity_composition import LegacyUnityIntentPlan
from aureon.queen.unity_exchange_brain import (
    QueenGovernedExchangeBrain,
    build_queen_exchange_brains,
)
from aureon.trading.unified_exchange_client import (
    MultiExchangeClient,
    UnifiedEcosystemMutationRequest,
)

ROOT = Path(__file__).resolve().parents[1]
QUEEN_SOURCES = (
    ROOT / "aureon" / "queen" / "queen_quantum_frog.py",
    ROOT
    / "Kings_Accounting_Suite"
    / "aureon_systems"
    / "queen_quantum_frog.py",
)


def _plan(request: UnifiedEcosystemMutationRequest) -> LegacyUnityIntentPlan:
    body = {
        "cl_ord_id": "queen-order-1",
        "ordertype": request.order_type.lower(),
        "pair": request.symbol,
        "type": request.side.lower(),
        "volume": request.quote_quantity or request.quantity,
    }
    amount_field = (
        "quote_quantity" if request.quote_quantity is not None else "quantity"
    )
    return LegacyUnityIntentPlan.create(
        capability_id="legacy-capability:queen:kraken:market-order",
        venue=request.exchange,
        environment="live",
        account_id_hash="b" * 64,
        method="POST",
        path="/0/private/AddOrder",
        operation=request.operation,
        purpose=request.purpose,
        symbol=request.symbol,
        side=request.side,
        order_type=request.order_type,
        quantity=request.quantity,
        quote_quantity=request.quote_quantity,
        limit_price=request.limit_price,
        stop_price=request.stop_price,
        take_profit=request.take_profit,
        reduce_only=request.reduce_only,
        client_order_id="queen-order-1",
        authorization_receipt_id="authorization:queen:1",
        cycle_id="cycle:queen:1",
        position_receipt_id="provider:kraken:position:queen",
        body=body,
        body_bindings={
            "client_order_id": "/cl_ord_id",
            amount_field: "/volume",
            "order_type": "/ordertype",
            "side": "/type",
            "symbol": "/pair",
        },
    )


class _Supplier:
    supplier_id = "aureon:test:queen-plan"

    def __init__(self, transform=None, *, raises: bool = False) -> None:
        self.transform = transform
        self.raises = raises
        self.calls: list[UnifiedEcosystemMutationRequest] = []

    def supply_unity_plan(
        self,
        request: UnifiedEcosystemMutationRequest,
    ) -> LegacyUnityIntentPlan:
        self.calls.append(request)
        if self.raises:
            raise RuntimeError("private supplier failure")
        plan = _plan(request)
        return self.transform(plan) if self.transform else plan


class _ReadAndMutationClient:
    dry_run = False

    def __init__(self, gateway: object, invocation_supplier: object) -> None:
        self._legacy_unity_gateway = gateway
        self._legacy_invocation_supplier = invocation_supplier
        self.order_calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def get_ticker(self, symbol: str) -> dict[str, Any]:
        return {"symbol": symbol, "price": 100.0}

    def place_market_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.order_calls.append((args, kwargs))
        return {
            "status": "submitted",
            "aureon_legacy_unity_receipt": {"status": "EXECUTED"},
        }

    def place_margin_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.place_market_order(*args, **kwargs)

    def close_margin_position(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.place_market_order(*args, **kwargs)

    def place_take_profit_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.place_market_order(*args, **kwargs)

    def place_trailing_stop_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.place_market_order(*args, **kwargs)


class _UnifiedSeat:
    dry_run = False

    def __init__(
        self,
        raw: _ReadAndMutationClient,
        gateway: object,
        invocation_supplier: object,
    ) -> None:
        self.client = raw
        self._legacy_unity_gateway = gateway
        self._legacy_invocation_supplier = invocation_supplier

    def place_market_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.client.place_market_order(*args, **kwargs)

    def place_margin_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.client.place_margin_order(*args, **kwargs)

    def close_margin_position(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.client.close_margin_position(*args, **kwargs)

    def place_take_profit_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.client.place_take_profit_order(*args, **kwargs)

    def place_trailing_stop_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.client.place_trailing_stop_order(*args, **kwargs)


def _base() -> tuple[MultiExchangeClient, _ReadAndMutationClient]:
    gateway = object()
    invocation_supplier = object()
    raw = _ReadAndMutationClient(gateway, invocation_supplier)
    seat = _UnifiedSeat(raw, gateway, invocation_supplier)
    base = object.__new__(MultiExchangeClient)
    base.clients = dict.fromkeys(("alpaca", "binance", "capital", "kraken"), seat)
    base.dry_run = False
    return base, raw


def _configured(
    supplier: _Supplier,
    outcome_observer=None,
) -> tuple[QueenGovernedExchangeBrain, _ReadAndMutationClient]:
    base, raw = _base()
    brains, governed, status = build_queen_exchange_brains(
        unity_composition=SimpleNamespace(client=base),
        unity_plan_supplier=supplier,
        trusted_unity_plan_supplier_ids={supplier.supplier_id},
        outcome_observer=outcome_observer,
    )
    assert governed is not None
    assert status["status"] == "READY"
    assert brains["kraken"].read_client is raw
    return brains["kraken"], raw


def test_missing_composition_preserves_reads_but_holds_mutations() -> None:
    base, raw = _base()
    brains, governed, status = build_queen_exchange_brains(
        fallback_read_clients={"kraken": raw},
    )

    assert governed is None
    assert status["status"] == "HOLD"
    assert brains["kraken"].get_ticker("XBTGBP")["price"] == 100.0

    result = brains["kraken"].place_market_order(
        "XBTGBP",
        "buy",
        quote_qty=10,
    )

    assert result["decision"] == "HOLD"
    assert result["reason"] == "canonical_queen_unity_composition_required"
    assert raw.order_calls == []


def test_configured_queen_uses_one_plan_and_one_unified_dispatch() -> None:
    supplier = _Supplier()
    brain, raw = _configured(supplier)

    result = brain.place_market_order("XBTGBP", "buy", quote_qty=10)

    assert result["status"] == "submitted"
    assert len(supplier.calls) == 1
    assert supplier.calls[0].purpose == "ENTRY"
    assert supplier.calls[0].quote_quantity == "10"
    assert len(raw.order_calls) == 1


def test_configured_margin_entry_and_close_are_each_observed_once() -> None:
    supplier = _Supplier()
    observed: list[tuple[str, dict[str, Any]]] = []
    brain, raw = _configured(
        supplier,
        lambda operation, receipt: observed.append((operation, dict(receipt))),
    )

    opened = brain.place_margin_order(
        "XBTGBP",
        "buy",
        1,
        leverage=2,
    )
    closed = brain.close_margin_position(
        "XBTGBP",
        "sell",
        volume=1,
        leverage=2,
    )

    assert opened["status"] == "submitted"
    assert closed["status"] == "submitted"
    assert [request.operation for request in supplier.calls] == [
        "MARGIN_ORDER",
        "MARGIN_CLOSE",
    ]
    assert len(raw.order_calls) == 2
    assert [operation for operation, _ in observed] == [
        "place_margin_order",
        "close_margin_position",
    ]


def test_configured_protective_orders_are_each_observed_once() -> None:
    supplier = _Supplier()
    observed: list[tuple[str, dict[str, Any]]] = []
    brain, raw = _configured(
        supplier,
        outcome_observer=lambda operation, receipt: observed.append(
            (operation, dict(receipt))
        ),
    )

    take_profit = brain.place_take_profit_order(
        "XBTGBP", "sell", 1, take_profit_price=101
    )
    trailing = brain.place_trailing_stop_order(
        "XBTGBP", "sell", 1, trailing_offset=0.5
    )

    assert take_profit["status"] == "submitted"
    assert trailing["status"] == "submitted"
    assert [request.operation for request in supplier.calls] == [
        "TAKE_PROFIT_ORDER",
        "TRAILING_STOP_ORDER",
    ]
    assert len(raw.order_calls) == 2
    assert [operation for operation, _ in observed] == [
        "place_take_profit_order",
        "place_trailing_stop_order",
    ]


def test_supplier_failure_holds_before_provider_client() -> None:
    supplier = _Supplier(raises=True)
    brain, raw = _configured(supplier)

    result = brain.place_market_order("XBTGBP", "buy", quote_qty=10)

    assert result["status"] == "no_data"
    assert result["reason"] == "trusted_unified_ecosystem_plan_resolution_failed"
    assert raw.order_calls == []


def test_mismatched_plan_holds_before_provider_client() -> None:
    supplier = _Supplier(lambda plan: replace(plan, symbol="ETHGBP"))
    brain, raw = _configured(supplier)

    result = brain.place_market_order("XBTGBP", "buy", quote_qty=10)

    assert result["reason"] == "exact_unified_ecosystem_plan_required"
    assert raw.order_calls == []


def test_replayed_plan_is_burned_before_second_dispatch() -> None:
    supplier = _Supplier()
    brain, raw = _configured(supplier)

    first = brain.place_market_order("XBTGBP", "buy", quote_qty=10)
    second = brain.place_market_order("XBTGBP", "buy", quote_qty=10)

    assert first["status"] == "submitted"
    assert second["reason"] == "unified_ecosystem_plan_replay_blocked"
    assert len(raw.order_calls) == 1


def test_unimplemented_mutation_never_falls_through_to_read_client() -> None:
    supplier = _Supplier()
    brain, raw = _configured(supplier)

    result = brain.place_limit_order("XBTGBP", "buy", 1, 100)

    assert result["decision"] == "HOLD"
    assert result["reason"] == "queen_mutation_route_not_yet_unified"
    assert raw.order_calls == []


def test_provider_specific_arguments_require_an_exact_route() -> None:
    supplier = _Supplier()
    brain, raw = _configured(supplier)

    result = brain.place_market_order(
        "XBTGBP",
        "buy",
        quote_qty=10,
        time_in_force="IOC",
    )

    assert result["decision"] == "HOLD"
    assert (
        result["reason"]
        == "provider_specific_mutation_arguments_require_exact_unity_route"
    )
    assert supplier.calls == []
    assert raw.order_calls == []


def test_lazy_read_binding_cannot_replace_mutation_authority() -> None:
    brain = QueenGovernedExchangeBrain(
        exchange="capital",
        read_client=None,
        governed_client=None,
    )
    reader = object()
    brain.bind_read_client(reader)

    assert brain.read_client is reader
    with pytest.raises(RuntimeError, match="queen_read_client_already_bound"):
        brain.bind_read_client(object())
    assert brain.place_market_order("SILVER", "buy", quantity=1)["decision"] == "HOLD"


def test_partial_composition_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="queen_unity_composition_plan_supplier_and_allowlist_required_together",
    ):
        build_queen_exchange_brains(
            unity_composition=SimpleNamespace(client=object()),
        )


def test_both_active_queen_copies_use_the_shared_exchange_brain() -> None:
    for path in QUEEN_SOURCES:
        source = path.read_text(encoding="utf-8")
        queen = source[source.index("class OrcaKillCycle:") :]
        constructor = queen[
            queen.index("    def __init__(") : queen.index("        self.exchange = exchange")
        ]
        lazy_capital = queen[
            queen.index("    def _ensure_capital_client(") : queen.index(
                "    def emit_position_signal(",
                queen.index("    def _ensure_capital_client("),
            )
        ]

        assert "unity_composition=None" in constructor
        assert "build_queen_exchange_brains" in constructor
        assert "fallback_read_clients" in constructor
        assert "self.client = self.clients[exchange]" in constructor
        assert "brain.bind_read_client(CapitalClient())" in lazy_capital
        assert "self.clients['capital'] = CapitalClient()" not in lazy_capital
