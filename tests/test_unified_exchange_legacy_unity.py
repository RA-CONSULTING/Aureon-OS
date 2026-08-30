from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from aureon.governance.economic_boundary import EconomicIntent
from aureon.governance.legacy_economic_unity import LegacyEconomicInvocation
from aureon.governance.legacy_unity_composition import (
    LegacyUnityCompositionHold,
    LegacyUnityIntentPlan,
)
from aureon.trading.unified_exchange_client import (
    MultiExchangeClient,
    UnifiedExchangeClient,
)


def _invocation() -> LegacyEconomicInvocation:
    position = "provider:kraken:position:unified-client"
    return LegacyEconomicInvocation(
        capability_id="legacy-capability:unified-exchange:kraken:market-order",
        intent=EconomicIntent.build(
            venue="kraken",
            environment="live",
            account_id_hash="a" * 64,
            method="POST",
            path="/0/private/AddOrder",
            operation="MARKET_ORDER",
            purpose="ENTRY",
            symbol="XBTGBP",
            side="BUY",
            order_type="MARKET",
            quantity=None,
            quote_quantity="10",
            limit_price=None,
            stop_price=None,
            take_profit=None,
            reduce_only=False,
            client_order_id="unified-client-1",
            authorization_receipt_id="authorization:unified-client:1",
            cycle_id="cycle:unified-client:1",
            position_receipt_id=position,
            hnc_receipt_id="hnc:live_field:unified-client",
            auris_receipt_id="auris:cosmic_state:unified-client",
            provider_receipt_ids=(position,),
            provider_moment_digest="b" * 64,
            provider_source_timestamp="1786473600",
            body={
                "cl_ord_id": "unified-client-1",
                "ordertype": "market",
                "pair": "XBTGBP",
                "type": "buy",
                "volume": "10",
            },
            body_bindings={
                "client_order_id": "/cl_ord_id",
                "order_type": "/ordertype",
                "quote_quantity": "/volume",
                "side": "/type",
                "symbol": "/pair",
            },
        ),
    )


def _plan() -> LegacyUnityIntentPlan:
    position = "provider:kraken:position:unified-client"
    return LegacyUnityIntentPlan.create(
        capability_id="legacy-capability:unified-exchange:kraken:market-order",
        venue="kraken",
        environment="live",
        account_id_hash="a" * 64,
        method="POST",
        path="/0/private/AddOrder",
        operation="MARKET_ORDER",
        purpose="ENTRY",
        symbol="XBTGBP",
        side="BUY",
        order_type="MARKET",
        quantity=None,
        quote_quantity="10",
        limit_price=None,
        stop_price=None,
        take_profit=None,
        reduce_only=False,
        client_order_id="unified-client-1",
        authorization_receipt_id="authorization:unified-client:1",
        cycle_id="cycle:unified-client:1",
        position_receipt_id=position,
        body={
            "cl_ord_id": "unified-client-1",
            "ordertype": "market",
            "pair": "XBTGBP",
            "type": "buy",
            "volume": "10",
        },
        body_bindings={
            "client_order_id": "/cl_ord_id",
            "order_type": "/ordertype",
            "quote_quantity": "/volume",
            "side": "/type",
            "symbol": "/pair",
        },
    )


class _RawClient:
    dry_run = False

    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def place_market_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("market", args, kwargs))
        return {"status": "submitted", "provider_order_id": "K1"}

    def place_limit_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("limit", args, kwargs))
        return {"status": "submitted", "provider_order_id": "K1"}

    def place_stop_loss_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("stop", args, kwargs))
        return {"status": "submitted", "provider_order_id": "K1"}

    def place_take_profit_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("take_profit", args, kwargs))
        return {"status": "submitted", "provider_order_id": "K1"}

    def place_trailing_stop_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("trailing_stop", args, kwargs))
        return {"status": "submitted", "provider_order_id": "K1"}

    def place_order_with_tp_sl(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("tp_sl", args, kwargs))
        return {"status": "submitted", "provider_order_id": "K1"}

    def place_margin_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("margin", args, kwargs))
        return {"status": "submitted", "provider_order_id": "K1"}

    def close_margin_position(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("margin_close", args, kwargs))
        return {"status": "submitted", "provider_order_id": "K1"}

    def cancel_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("cancel", args, kwargs))
        return {"status": "submitted", "provider_order_id": "K1"}

    def cancel_all_orders(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("cancel_all", args, kwargs))
        return {"status": "submitted", "provider_order_id": "K1"}


class _Gateway:
    def __init__(self, status: str = "EXECUTED") -> None:
        self.status = status
        self.calls: list[LegacyEconomicInvocation] = []

    def execute(self, invocation: LegacyEconomicInvocation, *, transport):
        self.calls.append(invocation)
        receipt = {
            "reason": {
                "EXECUTED": "exact_boundary_accept",
                "HOLD": "council_hold",
                "AMBIGUOUS": "transport_outcome_ambiguous_reconciliation_required",
            }[self.status],
            "receipt_id": f"legacy-unity:{self.status.lower()}",
        }
        result = transport() if self.status == "EXECUTED" else None
        return SimpleNamespace(
            status=self.status,
            provider_result=result,
            receipt=receipt,
        )


class _Supplier:
    supplier_id = "aureon:test:legacy-unity-invocation"

    def __init__(self, *, hold: str = "") -> None:
        self.hold = hold
        self.calls: list[LegacyUnityIntentPlan] = []

    def supply_legacy_invocation(
        self,
        plan: LegacyUnityIntentPlan,
    ) -> LegacyEconomicInvocation:
        self.calls.append(plan)
        if self.hold:
            raise LegacyUnityCompositionHold(self.hold)
        return _invocation()


def _client(
    gateway: Any,
    supplier: Any = None,
) -> tuple[UnifiedExchangeClient, _RawClient]:
    client = object.__new__(UnifiedExchangeClient)
    raw = _RawClient()
    client.exchange_id = "kraken"
    client.client = raw
    client.available = True
    client.dry_run = False
    client.kraken_min_notional = 5.0
    client._legacy_unity_gateway = gateway
    client._legacy_invocation_supplier = supplier
    return client, raw


def test_configured_unity_gateway_holds_missing_hnc_auris_invocation() -> None:
    gateway = _Gateway()
    client, raw = _client(gateway)

    result = client.place_market_order("XBTGBP", "buy", quote_qty=10)

    assert result["status"] == "no_data"
    assert result["reason"] == "hnc_auris_legacy_unity_invocation_required"
    assert gateway.calls == []
    assert raw.calls == []


def test_exact_unity_invocation_runs_original_legacy_transport_once() -> None:
    gateway = _Gateway()
    client, raw = _client(gateway)
    invocation = _invocation()

    result = client.place_market_order(
        "XBTGBP",
        "buy",
        quote_qty=10,
        unity_invocation=invocation,
    )

    assert result["status"] == "submitted"
    assert result["provider_order_id"] == "K1"
    assert result["aureon_legacy_unity_receipt"]["reason"] == "exact_boundary_accept"
    assert gateway.calls == [invocation]
    assert len(raw.calls) == 1


def test_council_or_crown_hold_never_calls_original_transport() -> None:
    gateway = _Gateway("HOLD")
    client, raw = _client(gateway)

    result = client.place_market_order(
        "XBTGBP",
        "buy",
        quote_qty=10,
        unity_invocation=_invocation(),
    )

    assert result["status"] == "not_submitted"
    assert result["reason"] == "council_hold"
    assert result["rejected"] is True
    assert raw.calls == []


def test_ambiguous_result_is_reconciled_and_never_retried() -> None:
    gateway = _Gateway("AMBIGUOUS")
    client, raw = _client(gateway)

    result = client.place_market_order(
        "XBTGBP",
        "buy",
        quote_qty=10,
        unity_invocation=_invocation(),
    )

    assert result["status"] == "pending_reconciliation"
    assert result["reason"] == "transport_outcome_ambiguous_reconciliation_required"
    assert raw.calls == []


def test_unconfigured_compatibility_path_holds_without_raw_transport() -> None:
    client, raw = _client(None)

    result = client.place_market_order("XBTGBP", "buy", quote_qty=10)

    assert result["status"] == "no_data"
    assert result["reason"] == "canonical_legacy_unity_composition_required"
    assert raw.calls == []


def test_invocation_without_composition_root_gateway_holds() -> None:
    client, raw = _client(None)

    result = client.place_market_order(
        "XBTGBP",
        "buy",
        quote_qty=10,
        unity_invocation=_invocation(),
    )

    assert result["status"] == "no_data"
    assert result["reason"] == "legacy_unity_gateway_required"
    assert raw.calls == []


def test_exact_route_plan_is_resolved_by_aureon_10_9_1_supplier() -> None:
    gateway = _Gateway()
    supplier = _Supplier()
    client, raw = _client(gateway, supplier)
    plan = _plan()

    result = client.place_market_order(
        "XBTGBP",
        "buy",
        quote_qty=10,
        unity_plan=plan,
    )

    assert result["status"] == "submitted"
    assert supplier.calls == [plan]
    assert gateway.calls == [_invocation()]
    assert len(raw.calls) == 1


def test_hnc_auris_composition_hold_never_reaches_gateway_or_provider() -> None:
    gateway = _Gateway()
    supplier = _Supplier(hold="active_auris_coherence_required")
    client, raw = _client(gateway, supplier)

    result = client.place_market_order(
        "XBTGBP",
        "buy",
        quote_qty=10,
        unity_plan=_plan(),
    )

    assert result["status"] == "no_data"
    assert result["reason"] == "active_auris_coherence_required"
    assert gateway.calls == []
    assert raw.calls == []


def test_caller_cannot_supply_plan_and_prebuilt_invocation_together() -> None:
    gateway = _Gateway()
    client, raw = _client(gateway, _Supplier())

    result = client.place_market_order(
        "XBTGBP",
        "buy",
        quote_qty=10,
        unity_invocation=_invocation(),
        unity_plan=_plan(),
    )

    assert result["status"] == "no_data"
    assert result["reason"] == "exactly_one_legacy_unity_invocation_or_plan_required"
    assert gateway.calls == []
    assert raw.calls == []


def test_all_single_call_order_and_cancel_operations_use_same_unity_seam() -> None:
    operations = (
        ("limit", lambda client, invocation: client.place_limit_order(
            "XBTGBP", "buy", 1, 10, unity_invocation=invocation
        )),
        ("stop", lambda client, invocation: client.place_stop_loss_order(
            "XBTGBP", "sell", 1, 9, unity_invocation=invocation
        )),
        ("take_profit", lambda client, invocation: client.place_take_profit_order(
            "XBTGBP", "sell", 1, 11, unity_invocation=invocation
        )),
        ("trailing_stop", lambda client, invocation: client.place_trailing_stop_order(
            "XBTGBP", "sell", 1, 2, unity_invocation=invocation
        )),
        ("cancel", lambda client, invocation: client.cancel_order(
            "O1", unity_invocation=invocation
        )),
        ("cancel_all", lambda client, invocation: client.cancel_all_orders(
            "XBTGBP", unity_invocation=invocation
        )),
    )

    for expected_operation, call in operations:
        gateway = _Gateway()
        client, raw = _client(gateway)
        result = call(client, _invocation())

        assert result["status"] == "submitted"
        assert len(gateway.calls) == 1
        assert len(raw.calls) == 1
        assert raw.calls[0][0] == expected_operation


def test_single_call_operations_hold_together_when_council_holds() -> None:
    operations = (
        lambda client, invocation: client.place_limit_order(
            "XBTGBP", "buy", 1, 10, unity_invocation=invocation
        ),
        lambda client, invocation: client.place_stop_loss_order(
            "XBTGBP", "sell", 1, 9, unity_invocation=invocation
        ),
        lambda client, invocation: client.place_take_profit_order(
            "XBTGBP", "sell", 1, 11, unity_invocation=invocation
        ),
        lambda client, invocation: client.place_trailing_stop_order(
            "XBTGBP", "sell", 1, 2, unity_invocation=invocation
        ),
        lambda client, invocation: client.cancel_order(
            "O1", unity_invocation=invocation
        ),
        lambda client, invocation: client.cancel_all_orders(
            "XBTGBP", unity_invocation=invocation
        ),
    )

    for call in operations:
        client, raw = _client(_Gateway("HOLD"))
        result = call(client, _invocation())

        assert result["status"] == "not_submitted"
        assert result["reason"] == "council_hold"
        assert raw.calls == []


def test_multi_exchange_passes_same_invocation_to_selected_brain() -> None:
    invocation = _invocation()
    calls: list[tuple[Any, ...]] = []

    class _Selected:
        def place_market_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            calls.append((args, kwargs))
            return {"status": "submitted"}

    multi = object.__new__(MultiExchangeClient)
    multi.clients = {"kraken": _Selected()}

    result = multi.place_market_order(
        "kraken",
        "XBTGBP",
        "buy",
        quote_qty=10,
        unity_invocation=invocation,
    )

    assert result["status"] == "submitted"
    assert calls[0][1]["unity_invocation"] is invocation


def test_composite_and_margin_mutations_use_the_same_unity_seam() -> None:
    operations = (
        ("tp_sl", lambda client, invocation: client.place_order_with_tp_sl(
            "XBTGBP",
            "buy",
            1,
            take_profit=11,
            stop_loss=9,
            unity_invocation=invocation,
        )),
        ("margin", lambda client, invocation: client.place_margin_order(
            "XBTGBP",
            "buy",
            1,
            2,
            order_type="limit",
            price=10,
            unity_invocation=invocation,
        )),
        ("margin_close", lambda client, invocation: client.close_margin_position(
            "XBTGBP",
            "sell",
            volume=1,
            unity_invocation=invocation,
        )),
    )

    for expected_operation, call in operations:
        gateway = _Gateway()
        client, raw = _client(gateway)

        result = call(client, _invocation())

        assert result["status"] == "submitted"
        assert len(gateway.calls) == 1
        assert len(raw.calls) == 1
        assert raw.calls[0][0] == expected_operation


def test_composite_and_margin_hold_never_reach_raw_transport() -> None:
    operations = (
        lambda client: client.place_order_with_tp_sl(
            "XBTGBP",
            "buy",
            1,
            take_profit=11,
            stop_loss=9,
        ),
        lambda client: client.place_margin_order(
            "XBTGBP",
            "buy",
            1,
            2,
            order_type="limit",
            price=10,
        ),
        lambda client: client.close_margin_position(
            "XBTGBP",
            "sell",
            volume=1,
        ),
    )

    for call in operations:
        client, raw = _client(_Gateway())

        result = call(client)

        assert result["status"] == "no_data"
        assert result["reason"] == "hnc_auris_legacy_unity_invocation_required"
        assert raw.calls == []
