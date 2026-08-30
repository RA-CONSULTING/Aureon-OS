from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable

import pytest

from aureon.governance.economic_boundary import (
    ECONOMIC_PERMIT_SCHEMA,
    EconomicGovernanceBlocked,
    EconomicGovernanceBoundary,
    EconomicIntent,
    EconomicMutationPermit,
)
from aureon.governance.legacy_economic_unity import (
    LEGACY_UNITY_TARGET,
    LegacyEconomicCapability,
    LegacyEconomicInvocation,
    LegacyEconomicUnityGateway,
    bind_legacy_economic_unity_gateway,
    validate_legacy_unity_receipt,
)

HNC = "hnc:live_field:legacy-unity"
AURIS = "auris:cosmic_state:legacy-unity"
POSITION = "provider:kraken:position:legacy-unity"
MOMENT = "provider:kraken:moment:legacy-unity"
BODY_BINDINGS = (
    ("client_order_id", "/cl_ord_id"),
    ("order_type", "/ordertype"),
    ("quantity", "/volume"),
    ("side", "/type"),
    ("symbol", "/pair"),
)


def _capability(**changes: Any) -> LegacyEconomicCapability:
    values = {
        "capability_id": "legacy-capability:unified-exchange:kraken:market-order",
        "source_file": "aureon/trading/unified_exchange_client.py",
        "source_symbol": "UnifiedExchangeClient.place_market_order",
        "venue": "kraken",
        "method": "POST",
        "path": "/0/private/AddOrder",
        "operation": "MARKET_ORDER",
        "purpose": "ENTRY",
        "body_bindings": BODY_BINDINGS,
        "preserved_operations": ("LIMIT_ORDER", "MARKET_ORDER", "STOP_ORDER"),
    }
    values.update(changes)
    return LegacyEconomicCapability(**values)


def _intent(**changes: Any) -> EconomicIntent:
    values = {
        "venue": "kraken",
        "environment": "live",
        "account_id_hash": "a" * 64,
        "method": "POST",
        "path": "/0/private/AddOrder",
        "operation": "MARKET_ORDER",
        "purpose": "ENTRY",
        "symbol": "XBTGBP",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": "0.001",
        "quote_quantity": None,
        "limit_price": None,
        "stop_price": None,
        "take_profit": None,
        "reduce_only": False,
        "client_order_id": "legacy-unity-1",
        "authorization_receipt_id": "authorization:legacy-unity:1",
        "cycle_id": "cycle:legacy-unity:1",
        "position_receipt_id": POSITION,
        "hnc_receipt_id": HNC,
        "auris_receipt_id": AURIS,
        "provider_receipt_ids": (MOMENT, POSITION),
        "provider_moment_digest": "b" * 64,
        "provider_source_timestamp": "1786473600",
        "body": {
            "cl_ord_id": "legacy-unity-1",
            "ordertype": "market",
            "pair": "XBTGBP",
            "type": "buy",
            "volume": "0.001",
        },
        "body_bindings": dict(BODY_BINDINGS),
    }
    values.update(changes)
    return EconomicIntent.build(**values)


def _permit(intent: EconomicIntent) -> EconomicMutationPermit:
    return EconomicMutationPermit(
        schema=ECONOMIC_PERMIT_SCHEMA,
        permit_id="economic-permit:legacy-unity",
        boundary_id="economic-boundary:legacy-unity",
        permit_kind="fresh_dual_accept",
        intent_digest=intent.intent_digest,
        method=intent.method,
        path=intent.path,
        body_digest=intent.body_digest,
        provider_moment_digest=intent.provider_moment_digest,
        hnc_receipt_id=intent.hnc_receipt_id,
        auris_receipt_id=intent.auris_receipt_id,
        authorization_receipt_id=intent.authorization_receipt_id,
        cycle_id=intent.cycle_id,
        position_receipt_id=intent.position_receipt_id,
        dual_receipt_id="dual-key:legacy-unity",
        proposal_digest="c" * 64,
        context_digest="d" * 64,
        issued_at="1786473600",
        expires_at="1786473602",
        contingency_warrant_id=None,
    )


class _BoundaryHarness(EconomicGovernanceBoundary):
    def __init__(self, *, hold: str | None = None) -> None:
        self.hold = hold
        self.prepare_calls: list[EconomicIntent] = []
        self.consume_calls: list[tuple[Any, str, str, dict[str, Any]]] = []

    def prepare_mutation(self, intent: EconomicIntent) -> EconomicMutationPermit:
        self.prepare_calls.append(intent)
        if self.hold:
            raise EconomicGovernanceBlocked(self.hold)
        return _permit(intent)

    def consume_and_call(
        self,
        permit: EconomicMutationPermit,
        *,
        method: str,
        path: str,
        body: dict[str, Any],
        transport: Callable[[], Any],
    ) -> Any:
        self.consume_calls.append((permit, method, path, body))
        return transport()


def _gateway(boundary: EconomicGovernanceBoundary | None = None):
    return bind_legacy_economic_unity_gateway(
        boundary=boundary or _BoundaryHarness(),
        capabilities=(_capability(),),
    )


def _invocation(intent: EconomicIntent | None = None) -> LegacyEconomicInvocation:
    return LegacyEconomicInvocation(_capability().capability_id, intent or _intent())


def test_exact_legacy_route_executes_once_through_existing_boundary() -> None:
    boundary = _BoundaryHarness()
    gateway = _gateway(boundary)
    transport_calls = 0

    def transport() -> dict[str, Any]:
        nonlocal transport_calls
        transport_calls += 1
        return {"status": "submitted", "txid": ["T1"]}

    outcome = gateway.execute(_invocation(), transport=transport)

    assert outcome.status == "EXECUTED"
    assert outcome.provider_result == {"status": "submitted", "txid": ["T1"]}
    assert transport_calls == 1
    assert len(boundary.prepare_calls) == 1
    assert len(boundary.consume_calls) == 1
    assert outcome.receipt["legacy_capability_preserved"] is True
    assert outcome.receipt["hnc_receipt_id"] == HNC
    assert outcome.receipt["auris_receipt_id"] == AURIS
    assert outcome.receipt["dual_receipt_id"] == "dual-key:legacy-unity"
    assert outcome.receipt["action_eligible"] is False
    assert validate_legacy_unity_receipt(outcome.receipt) == dict(outcome.receipt)


@pytest.mark.parametrize(
    "intent",
    [
        _intent(method="DELETE"),
        _intent(path="/0/private/CancelOrder"),
        _intent(operation="CANCEL_ORDER"),
        _intent(purpose="CONTAINMENT"),
        _intent(body_bindings={"quantity": "/volume"}),
    ],
)
def test_route_drift_holds_before_boundary_and_transport(intent: EconomicIntent) -> None:
    boundary = _BoundaryHarness()
    transport_calls = 0

    def transport() -> None:
        nonlocal transport_calls
        transport_calls += 1

    outcome = _gateway(boundary).execute(_invocation(intent), transport=transport)

    assert outcome.status == "HOLD"
    assert outcome.receipt["reason"] == "registered_exact_legacy_capability_required"
    assert boundary.prepare_calls == []
    assert boundary.consume_calls == []
    assert transport_calls == 0


def test_unknown_legacy_capability_holds_without_discarding_known_routes() -> None:
    boundary = _BoundaryHarness()
    invocation = LegacyEconomicInvocation("legacy-capability:unknown", _intent())
    outcome = _gateway(boundary).execute(invocation, transport=lambda: None)

    assert outcome.status == "HOLD"
    assert outcome.receipt["legacy_capability_preserved"] is False
    assert _gateway(boundary).capabilities == (_capability(),)
    assert boundary.prepare_calls == []


@pytest.mark.parametrize("reason", ["council_hold", "crown_abort", "auris_no_data"])
def test_hnc_auris_or_dual_hold_never_calls_legacy_transport(reason: str) -> None:
    boundary = _BoundaryHarness(hold=reason)
    calls = 0

    def transport() -> None:
        nonlocal calls
        calls += 1

    outcome = _gateway(boundary).execute(_invocation(), transport=transport)

    assert outcome.status == "HOLD"
    assert outcome.receipt["reason"] == reason
    assert len(boundary.prepare_calls) == 1
    assert boundary.consume_calls == []
    assert calls == 0


def test_transport_uncertainty_is_not_retried_or_treated_as_success() -> None:
    boundary = _BoundaryHarness()
    calls = 0

    def transport() -> None:
        nonlocal calls
        calls += 1
        raise TimeoutError("provider result unknown")

    outcome = _gateway(boundary).execute(_invocation(), transport=transport)

    assert outcome.status == "AMBIGUOUS"
    assert outcome.provider_result is None
    assert calls == 1
    assert len(boundary.consume_calls) == 1
    assert outcome.receipt["reason"] == "transport_outcome_ambiguous_reconciliation_required"
    assert outcome.receipt["permit_id"] == "economic-permit:legacy-unity"


def test_receipt_cannot_be_rewritten_into_economic_authority() -> None:
    outcome = _gateway().execute(_invocation(), transport=lambda: {"ok": True})
    forged = dict(outcome.receipt)
    forged["action_eligible"] = True

    with pytest.raises(ValueError, match="hash_mismatch"):
        validate_legacy_unity_receipt(forged)


def test_capability_manifest_preserves_every_declared_operation() -> None:
    capability = _capability()
    assert capability.migration_target == LEGACY_UNITY_TARGET
    assert capability.preserved_operations == (
        "LIMIT_ORDER",
        "MARKET_ORDER",
        "STOP_ORDER",
    )
    assert capability.operation in capability.preserved_operations
    assert len(capability.capability_digest) == 64


def test_capability_source_path_is_canonical_repo_relative_posix() -> None:
    with pytest.raises(ValueError, match="repo_relative_posix"):
        _capability(source_file="aureon\\trading\\legacy.py")
    with pytest.raises(ValueError, match="repo_relative_posix"):
        _capability(source_file="../legacy.py")


def test_untrusted_block_detail_is_not_copied_into_receipt() -> None:
    boundary = _BoundaryHarness(hold="provider said secret=do-not-log")

    outcome = _gateway(boundary).execute(_invocation(), transport=lambda: None)

    assert outcome.status == "HOLD"
    assert outcome.receipt["reason"] == "economic_governance_hold"
    assert "secret" not in str(outcome.receipt)


def test_duplicate_capability_ids_and_source_routes_are_rejected() -> None:
    first = _capability()
    duplicate_id = replace(first, source_symbol="Other.place_market_order")
    duplicate_route = replace(first, capability_id="legacy-capability:other")

    with pytest.raises(ValueError, match="ids_must_be_unique"):
        bind_legacy_economic_unity_gateway(
            boundary=_BoundaryHarness(),
            capabilities=(first, duplicate_id),
        )
    with pytest.raises(ValueError, match="source_routes_must_be_unique"):
        bind_legacy_economic_unity_gateway(
            boundary=_BoundaryHarness(),
            capabilities=(first, duplicate_route),
        )


def test_direct_gateway_construction_and_non_boundary_binding_are_rejected() -> None:
    with pytest.raises(TypeError, match="use_bind"):
        LegacyEconomicUnityGateway(
            _factory_token=object(),
            boundary=_BoundaryHarness(),
            capabilities=(_capability(),),
        )
    with pytest.raises(TypeError, match="economic_governance_boundary_required"):
        bind_legacy_economic_unity_gateway(
            boundary=object(),  # type: ignore[arg-type]
            capabilities=(_capability(),),
        )


def test_intent_requires_live_hnc_and_auris_receipts() -> None:
    with pytest.raises(ValueError, match="live_hnc"):
        _intent(hnc_receipt_id="hnc:synthetic")
    with pytest.raises(ValueError, match="live_auris"):
        _intent(auris_receipt_id="auris:synthetic")
