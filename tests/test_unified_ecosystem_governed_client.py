from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from aureon.governance.legacy_unity_composition import LegacyUnityIntentPlan
from aureon.trading.unified_exchange_client import (
    GovernedMultiExchangeClient,
    MultiExchangeClient,
    UnifiedEcosystemMutationRequest,
)

ROOT = Path(__file__).resolve().parents[1]
ECOSYSTEM_SOURCE = ROOT / "aureon" / "trading" / "aureon_unified_ecosystem.py"


def _plan(request: UnifiedEcosystemMutationRequest) -> LegacyUnityIntentPlan:
    if request.operation == "CANCEL_ORDER":
        body = {"txid": request.provider_order_id}
        bindings: dict[str, str] = {}
        path = "/0/private/CancelOrder"
    else:
        amount_field = (
            "quote_quantity"
            if request.quote_quantity is not None
            else "quantity"
        )
        body = {
            "cl_ord_id": "ecosystem-order-1",
            "ordertype": request.order_type.lower().replace("_", "-"),
            "pair": request.symbol,
            "type": request.side.lower(),
            "volume": request.quote_quantity or request.quantity,
        }
        bindings = {
            "client_order_id": "/cl_ord_id",
            amount_field: "/volume",
            "order_type": "/ordertype",
            "side": "/type",
            "symbol": "/pair",
        }
        path = "/0/private/AddOrder"
    return LegacyUnityIntentPlan.create(
        capability_id=(
            "legacy-capability:unified-exchange:kraken:"
            f"{request.operation.lower()}"
        ),
        venue=request.exchange,
        environment="live",
        account_id_hash="a" * 64,
        method="POST",
        path=path,
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
        client_order_id="ecosystem-order-1",
        authorization_receipt_id="authorization:ecosystem:1",
        cycle_id="cycle:ecosystem:1",
        position_receipt_id="provider:kraken:position:ecosystem",
        body=body,
        body_bindings=bindings,
    )


class _Supplier:
    supplier_id = "aureon:test:unified-ecosystem-plan"

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
            raise RuntimeError("supplier detail must remain private")
        plan = _plan(request)
        return self.transform(plan) if self.transform else plan


class _ExchangeBrain:
    dry_run = False

    def __init__(self, gateway: object, invocation_supplier: object) -> None:
        self._legacy_unity_gateway = gateway
        self._legacy_invocation_supplier = invocation_supplier
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def place_market_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("market", args, kwargs))
        return {
            "status": "submitted",
            "aureon_legacy_unity_receipt": {"status": "EXECUTED"},
        }

    def cancel_order(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("cancel", args, kwargs))
        return {
            "status": "submitted",
            "aureon_legacy_unity_receipt": {"status": "EXECUTED"},
        }


def _base() -> tuple[MultiExchangeClient, _ExchangeBrain]:
    gateway = object()
    invocation_supplier = object()
    brain = _ExchangeBrain(gateway, invocation_supplier)
    base = object.__new__(MultiExchangeClient)
    base.clients = {"kraken": brain}
    base.dry_run = False
    return base, brain


def _governed(
    supplier: _Supplier,
) -> tuple[GovernedMultiExchangeClient, _ExchangeBrain]:
    base, brain = _base()
    client = GovernedMultiExchangeClient(
        base_client=base,
        plan_supplier=supplier,
        trusted_plan_supplier_ids=frozenset({supplier.supplier_id}),
    )
    return client, brain


def test_exact_market_request_uses_one_plan_and_one_unified_dispatch() -> None:
    supplier = _Supplier()
    client, brain = _governed(supplier)

    result = client.place_market_order(
        "kraken",
        "XBTGBP",
        "BUY",
        quote_qty=10,
    )

    assert result["status"] == "submitted"
    assert len(supplier.calls) == 1
    assert supplier.calls[0].quote_quantity == "10"
    assert supplier.calls[0].purpose == "ENTRY"
    assert len(brain.calls) == 1
    assert isinstance(brain.calls[0][2]["unity_plan"], LegacyUnityIntentPlan)


def test_supplier_exception_holds_before_unified_dispatch() -> None:
    supplier = _Supplier(raises=True)
    client, brain = _governed(supplier)

    result = client.place_market_order(
        "kraken", "XBTGBP", "BUY", quote_qty=10
    )

    assert result["status"] == "no_data"
    assert result["reason"] == "trusted_unified_ecosystem_plan_resolution_failed"
    assert len(supplier.calls) == 1
    assert brain.calls == []


def test_mismatched_plan_holds_before_unified_dispatch() -> None:
    supplier = _Supplier(lambda plan: replace(plan, side="SELL"))
    client, brain = _governed(supplier)

    result = client.place_market_order(
        "kraken", "XBTGBP", "BUY", quote_qty=10
    )

    assert result["status"] == "no_data"
    assert result["reason"] == "exact_unified_ecosystem_plan_required"
    assert brain.calls == []


def test_one_plan_digest_cannot_be_replayed() -> None:
    supplier = _Supplier()
    client, brain = _governed(supplier)

    first = client.place_market_order(
        "kraken", "XBTGBP", "BUY", quote_qty=10
    )
    second = client.place_market_order(
        "kraken", "XBTGBP", "BUY", quote_qty=10
    )

    assert first["status"] == "submitted"
    assert second["status"] == "no_data"
    assert second["reason"] == "unified_ecosystem_plan_replay_blocked"
    assert len(supplier.calls) == 2
    assert len(brain.calls) == 1


def test_exact_cancel_plan_binds_provider_order_id() -> None:
    supplier = _Supplier()
    client, brain = _governed(supplier)

    result = client.cancel_order("kraken", "ORDER-1")

    assert result["status"] == "submitted"
    assert len(supplier.calls) == 1
    assert supplier.calls[0].operation == "CANCEL_ORDER"
    assert supplier.calls[0].provider_order_id == "ORDER-1"
    assert len(brain.calls) == 1
    assert brain.calls[0][0] == "cancel"


def test_caller_cannot_inject_a_prebuilt_plan() -> None:
    supplier = _Supplier()
    client, brain = _governed(supplier)
    request = UnifiedEcosystemMutationRequest.build(
        exchange="kraken",
        operation="MARKET_ORDER",
        purpose="ENTRY",
        symbol="XBTGBP",
        side="BUY",
        order_type="MARKET",
        quote_quantity=10,
        reduce_only=False,
    )

    result = client.place_market_order(
        "kraken",
        "XBTGBP",
        "BUY",
        quote_qty=10,
        unity_plan=_plan(request),
    )

    assert result["reason"] == "caller_supplied_unity_authority_forbidden"
    assert supplier.calls == []
    assert brain.calls == []


def test_untrusted_plan_supplier_is_rejected_at_composition_time() -> None:
    base, _brain = _base()
    supplier = _Supplier()

    with pytest.raises(
        ValueError,
        match="unified_ecosystem_plan_supplier_not_allowlisted",
    ):
        GovernedMultiExchangeClient(
            base_client=base,
            plan_supplier=supplier,
            trusted_plan_supplier_ids=frozenset({"aureon:other:supplier"}),
        )


def test_ecosystem_constructor_requires_the_full_composition_pair() -> None:
    source = ECOSYSTEM_SOURCE.read_text(encoding="utf-8")
    constructor = source[
        source.index("class AureonKrakenEcosystem:"):
        source.index("        # Positions must exist", source.index("class AureonKrakenEcosystem:"))
    ]

    assert "unity_composition: Any = None" in constructor
    assert "unity_plan_supplier: Any = None" in constructor
    assert "trusted_unity_plan_supplier_ids" in constructor
    assert "self.client = GovernedMultiExchangeClient(" in constructor
    assert "base_client=getattr(unity_composition, \"client\", None)" in constructor
    assert "canonical_unified_exchange_unity_composition_required" in constructor
    assert "unity_composition_plan_supplier_and_allowlist_required_together" in constructor
