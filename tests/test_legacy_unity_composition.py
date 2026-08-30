from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from aureon.governance import legacy_unity_composition as composition_module
from aureon.governance.legacy_unity_composition import (
    HncAurisLegacyInvocationSupplier,
    LegacyUnityCompositionHold,
    LegacyUnityIntentPlan,
    bind_hnc_auris_legacy_invocation_supplier,
)
from aureon.swarm.auris_node_receipts import ProviderMoment

POSITION_ID = "provider:kraken:position:legacy-unity"


def _plan(**overrides: Any) -> LegacyUnityIntentPlan:
    values = {
        "capability_id": "legacy-capability:unified-exchange:kraken:market-order",
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
        "quantity": None,
        "quote_quantity": "10",
        "limit_price": None,
        "stop_price": None,
        "take_profit": None,
        "reduce_only": False,
        "client_order_id": "legacy-unity-1",
        "authorization_receipt_id": "authorization:legacy-unity:1",
        "cycle_id": "cycle:legacy-unity:1",
        "position_receipt_id": POSITION_ID,
        "body": {
            "cl_ord_id": "legacy-unity-1",
            "ordertype": "market",
            "pair": "XBTGBP",
            "type": "buy",
            "volume": "10",
        },
        "body_bindings": {
            "client_order_id": "/cl_ord_id",
            "order_type": "/ordertype",
            "quote_quantity": "/volume",
            "side": "/type",
            "symbol": "/pair",
        },
    }
    values.update(overrides)
    return LegacyUnityIntentPlan.create(**values)


class _Resolver:
    resolver_id = "aureon:test:legacy-unity-evidence"

    def __init__(
        self,
        *,
        gate_open: bool = True,
        gamma: float = 0.9,
        fail: Exception | None = None,
    ) -> None:
        self.gate_open = gate_open
        self.gamma = gamma
        self.fail = fail
        self.hnc_requests: list[Any] = []
        self.auris_requests: list[tuple[Any, str, str]] = []

    def resolve_hnc_evidence(self, request):
        self.hnc_requests.append(request)
        if self.fail is not None:
            raise self.fail
        return {"receipt_id": "hnc:live_field:legacy-unity"}

    def resolve_auris_evidence(
        self,
        request,
        *,
        answer_digest: str,
        hnc_receipt_id: str,
    ):
        self.auris_requests.append((request, answer_digest, hnc_receipt_id))
        return {
            "receipt_id": "auris:cosmic_state:legacy-unity",
            "hnc_receipt_id": hnc_receipt_id,
            "gate_open": self.gate_open,
            "coherence_gamma": self.gamma,
        }


def _supplier(resolver: _Resolver) -> HncAurisLegacyInvocationSupplier:
    return bind_hnc_auris_legacy_invocation_supplier(
        resolver=resolver,
        trusted_resolver_ids=frozenset({resolver.resolver_id}),
        clock=lambda: 1_786_473_601.0,
    )


def _patch_moment(monkeypatch, *, provider_ids=(POSITION_ID,)) -> None:
    monkeypatch.setattr(
        composition_module,
        "validate_provider_moment",
        lambda *_args, **_kwargs: ProviderMoment(
            hnc_receipt_id="hnc:live_field:legacy-unity",
            auris_receipt_id="auris:cosmic_state:legacy-unity",
            source_timestamp=1_786_473_600.0,
            provider_receipt_ids=tuple(provider_ids),
            provider_moment_digest="b" * 64,
        ),
    )


def test_supplier_selects_exact_hnc_auris_moment_not_the_caller(monkeypatch) -> None:
    resolver = _Resolver()
    _patch_moment(monkeypatch)
    plan = _plan()

    invocation = _supplier(resolver).supply_legacy_invocation(plan)

    assert invocation.capability_id == plan.capability_id
    assert invocation.intent.hnc_receipt_id == "hnc:live_field:legacy-unity"
    assert invocation.intent.auris_receipt_id == "auris:cosmic_state:legacy-unity"
    assert invocation.intent.provider_receipt_ids == (POSITION_ID,)
    assert invocation.intent.provider_source_timestamp == "1786473600"
    assert invocation.intent.body_json == plan.body_json
    assert len(resolver.hnc_requests) == 1
    assert len(resolver.auris_requests) == 1
    request, answer_digest, hnc_id = resolver.auris_requests[0]
    assert request.prompt_digest == plan.plan_digest
    assert answer_digest == plan.plan_digest
    assert hnc_id == "hnc:live_field:legacy-unity"


def test_resolver_must_be_explicitly_allowlisted() -> None:
    resolver = _Resolver()

    with pytest.raises(ValueError, match="resolver_not_allowlisted"):
        bind_hnc_auris_legacy_invocation_supplier(
            resolver=resolver,
            trusted_resolver_ids=frozenset({"aureon:other"}),
        )


def test_supplier_direct_construction_is_blocked() -> None:
    resolver = _Resolver()

    with pytest.raises(TypeError, match="use_bind"):
        HncAurisLegacyInvocationSupplier(
            _factory_token=object(),
            resolver=resolver,
            max_age_s=30.0,
            clock=lambda: 1.0,
        )


@pytest.mark.parametrize(
    ("resolver", "reason"),
    (
        (_Resolver(gate_open=False), "auris_gate_open_required"),
        (_Resolver(gamma=0.79), "active_auris_coherence_required"),
        (_Resolver(gamma=float("nan")), "finite_auris_coherence_required"),
    ),
)
def test_auris_gate_and_active_coherence_are_mandatory(
    monkeypatch,
    resolver: _Resolver,
    reason: str,
) -> None:
    _patch_moment(monkeypatch)

    with pytest.raises(LegacyUnityCompositionHold, match=reason):
        _supplier(resolver).supply_legacy_invocation(_plan())


def test_position_receipt_must_be_inside_exact_provider_moment(monkeypatch) -> None:
    resolver = _Resolver()
    _patch_moment(monkeypatch, provider_ids=("provider:kraken:other",))

    with pytest.raises(
        LegacyUnityCompositionHold,
        match="provider_position_receipt_not_in_hnc_auris_moment",
    ):
        _supplier(resolver).supply_legacy_invocation(_plan())


def test_malformed_raw_evidence_holds_through_real_validator() -> None:
    resolver = _Resolver()

    with pytest.raises(
        LegacyUnityCompositionHold,
        match="complete_fresh_matching_hnc_auris_provider_moment_required",
    ):
        _supplier(resolver).supply_legacy_invocation(_plan())


def test_resolver_exception_detail_is_not_exposed() -> None:
    resolver = _Resolver(fail=RuntimeError("secret=do-not-log"))

    with pytest.raises(LegacyUnityCompositionHold) as captured:
        _supplier(resolver).supply_legacy_invocation(_plan())

    assert captured.value.reason_code == (
        "complete_fresh_matching_hnc_auris_provider_moment_required"
    )
    assert "secret" not in str(captured.value)


def test_composition_hold_never_copies_untrusted_detail() -> None:
    hold = LegacyUnityCompositionHold("provider said secret=do-not-log")

    assert hold.reason_code == "legacy_unity_composition_hold"
    assert "secret" not in str(hold)


def test_plan_is_deterministic_and_tamper_changes_digest() -> None:
    plan = _plan()
    changed = replace(plan, cycle_id="cycle:legacy-unity:2")

    assert _plan().plan_digest == plan.plan_digest
    assert changed.plan_digest != plan.plan_digest


def test_plan_rejects_float_request_values() -> None:
    with pytest.raises(ValueError, match="without_floats"):
        _plan(body={"pair": "XBTGBP", "volume": 10.0})
