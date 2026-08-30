from __future__ import annotations

import contextvars
import inspect
import json
from dataclasses import replace
from typing import Any
from unittest.mock import Mock

import pytest

import aureon.governance.crown_voice as crown_module
import aureon.governance.economic_boundary as boundary_module
from aureon.exchanges.binance_client import (
    BINANCE_MAINNET,
    BINANCE_TESTNET,
    BinanceClient,
)
from aureon.governance.capital_owner_authorization import (
    issue_capital_owner_live_authorization_from_approval,
)
from aureon.governance.cognition_gate import (
    CognitionGovernanceRequest,
    build_cognition_governance_request,
)
from aureon.governance.crown_voice import (
    ResolvedCrownVoiceEvidence,
    issue_crown_voice_receipt,
)
from aureon.governance.dual_key import join_dual_key, validate_dual_key_receipt
from aureon.governance.durable_contingency import (
    bind_durable_contingency_recovery,
)
from aureon.governance.economic_boundary import (
    ContingencyWarrantScope,
    EconomicGovernanceBlocked,
    EconomicGovernanceBoundary,
    EconomicIntent,
    bind_economic_governance_boundary,
)
from aureon.swarm.auris_node_receipts import ProviderMoment
from aureon.swarm.druidic_council import (
    REQUIRED_SEATS,
    build_seat_receipt,
    convene_druidic_council,
)
from aureon.trading.bounded_capital_live_trade import (
    BoundedCapitalLiveTrade,
    CapitalTradePlan,
)
from aureon.trading.bounded_capital_live_trade import (
    FieldMoment as CapitalFieldMoment,
)
from aureon.trading.bounded_capital_live_trade import (
    ProviderMoment as CapitalProviderMoment,
)
from aureon.trading.capital_market_evidence import (
    build_capital_market_evidence_receipt,
    build_capital_market_source_receipt,
    capital_market_provider_moment,
)

NOW = 1_786_473_600.0
HNC = "hnc:live_field:economic-boundary"
AURIS = "auris:cosmic_state:economic-boundary"
ACCOUNT_HASH = "a" * 64
PROVIDER_DIGEST = "b" * 64
CURRENT_PROVIDER_DIGEST = "c" * 64
FIELD_PROVIDER_DIGEST = "d" * 64
FIELD_PROVIDERS = (
    "provider:cosmic:schumann:field",
    "provider:cosmic:space-weather:field",
)
POSITION_BEFORE = "provider:binance:position:before"
POSITION_CURRENT = "provider:binance:position:current"
ENTRY_RECEIPT = "provider:binance:fill:entry"
COUNCIL_ID = "resolver:trusted-economic-council:v1"
CROWN_ID = "resolver:trusted-economic-crown:v1"


class _Clock:
    def __init__(self) -> None:
        self.value = NOW

    def __call__(self) -> float:
        return self.value


class _CouncilSupplier:
    supplier_id = COUNCIL_ID

    def supply_council_evidence(self, request: CognitionGovernanceRequest) -> Any:
        raise AssertionError("the patched dual evaluator owns this isolated fixture")


class _CrownSupplier:
    supplier_id = CROWN_ID

    def supply_crown_receipt(self, request: CognitionGovernanceRequest) -> Any:
        raise AssertionError("the patched dual evaluator owns this isolated fixture")


class _ProviderBoundCrownResolver:
    def __init__(
        self,
        request: CognitionGovernanceRequest,
        moment: ProviderMoment,
        decision: str,
    ) -> None:
        self.request = request
        self.moment = moment
        self.decision = decision

    def resolve_crown_voice_evidence(
        self,
        proposal_digest: str,
        prompt_digest: str,
    ) -> ResolvedCrownVoiceEvidence:
        assert proposal_digest == self.request.proposal_digest
        assert prompt_digest == self.request.prompt_digest
        queen_verdict = {
            "ACCEPT": "APPROVED",
            "HOLD": "CONCERNED",
            "ABORT": "VETO",
        }[self.decision]
        evidence = {"provider_moment": self.moment}
        return ResolvedCrownVoiceEvidence(
            resolver_id=CROWN_ID,
            issuer_id="issuer:independent-economic-crown",
            crown_identity="queen:economic-conscience",
            verdict_source_id="queen:economic-conscience:evaluation",
            queen_verdict=queen_verdict,
            queen_evaluated=True,
            reason="Crown checked the exact economic proposal",
            proposal_digest=proposal_digest,
            prompt_digest=prompt_digest,
            hnc_evidence=evidence,
            auris_evidence=evidence,
        )


def _request_from_evaluator_kwargs(kwargs: dict[str, Any]) -> CognitionGovernanceRequest:
    return build_cognition_governance_request(
        prompt=kwargs["prompt"],
        answer=kwargs["answer"],
        tool_calls=kwargs["tool_calls"],
        capability=kwargs["capability"],
        bake=kwargs["bake"],
        acquisition=kwargs["acquisition"],
        queen_verdict=kwargs["queen_verdict"],
    )


def _dual_receipt(
    request: CognitionGovernanceRequest,
    *,
    now: float,
    decision: str = "ACCEPT",
    hnc_receipt_id: str = HNC,
    auris_receipt_id: str = AURIS,
    provider_receipt_ids: tuple[str, ...] | None = None,
    provider_moment_digest: str | None = None,
    provider_source_timestamp: str | None = None,
) -> dict[str, Any]:
    provider_ids = provider_receipt_ids or request.provider_receipt_ids
    provider_digest = provider_moment_digest or request.provider_moment_digest
    provider_timestamp = (
        provider_source_timestamp or request.provider_source_timestamp
    )
    source_timestamp = float(provider_timestamp)
    seats = [
        build_seat_receipt(
            seat=seat,
            agent_id=f"economic-agent-{seat}",
            decision=decision,
            reason=f"{seat} checked the exact economic proposal",
            gamma=0.95,
            proposal_digest=request.proposal_digest,
            prompt_digest=request.prompt_digest,
            hnc_receipt_id=hnc_receipt_id,
            auris_receipt_id=auris_receipt_id,
            auris_node_receipt_id=f"auris:node:economic:{seat}",
            source_timestamp=source_timestamp,
            derived_at=now,
        )
        for seat in REQUIRED_SEATS
    ]
    council = convene_druidic_council(
        proposal_digest=request.proposal_digest,
        prompt_digest=request.prompt_digest,
        hnc_receipt_id=hnc_receipt_id,
        auris_receipt_id=auris_receipt_id,
        seat_receipts=seats,
        now=now,
    )
    moment = ProviderMoment(
        hnc_receipt_id=hnc_receipt_id,
        auris_receipt_id=auris_receipt_id,
        source_timestamp=source_timestamp,
        provider_receipt_ids=provider_ids,
        provider_moment_digest=provider_digest,
    )
    queen = issue_crown_voice_receipt(
        proposal_digest=request.proposal_digest,
        prompt_digest=request.prompt_digest,
        resolver=_ProviderBoundCrownResolver(request, moment, decision),
        now=now,
    )
    return join_dual_key(council, queen, now=now)


class _DualHarness:
    def __init__(self, outcome: str = "ACCEPT") -> None:
        self.outcome = outcome
        self.calls: list[dict[str, Any]] = []
        self.receipts: list[dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        assert kwargs["queen_verdict"] == "APPROVED"
        assert kwargs["queen_evaluated"] is True
        assert kwargs["council_receipt_supplier"].supplier_id == COUNCIL_ID
        assert kwargs["crown_receipt_supplier"].supplier_id == CROWN_ID
        if self.outcome == "NO_DATA":
            return {
                "schema": "aureon.dual_key_governance.v1",
                "receipt_type": "druid_queen_dual_key",
                "receipt_id": None,
                "decision": "HOLD",
                "data_status": "no_data",
            }
        request_kwargs = dict(kwargs)
        hnc_receipt_id = kwargs["acquisition"]["hnc_receipt_id"]
        auris_receipt_id = kwargs["acquisition"]["auris_receipt_id"]
        if self.outcome == "PROPOSAL_MISMATCH":
            request_kwargs["answer"] = f"{kwargs['answer']} altered"
        if self.outcome == "PROVIDER_MISMATCH":
            acquisition = dict(kwargs["acquisition"])
            acquisition["provider_moment_digest"] = "f" * 64
            request_kwargs["acquisition"] = acquisition
        request = _request_from_evaluator_kwargs(request_kwargs)
        if self.outcome == "HNC_MISMATCH":
            hnc_receipt_id = "hnc:live_field:different-economic-boundary"
        provider_ids = request.provider_receipt_ids
        provider_digest = request.provider_moment_digest
        provider_timestamp = request.provider_source_timestamp
        if self.outcome == "SHARED_WRONG_PROVIDER_IDS":
            provider_ids = ("provider:wrong:mutually-agreed",)
        elif self.outcome == "SHARED_WRONG_PROVIDER_DIGEST":
            provider_digest = "8" * 64
        elif self.outcome == "SHARED_WRONG_PROVIDER_TIMESTAMP":
            provider_timestamp = str(int(kwargs["now"] - 2.0))
        receipt = _dual_receipt(
            request,
            now=kwargs["now"],
            decision=self.outcome if self.outcome in {"HOLD", "ABORT"} else "ACCEPT",
            hnc_receipt_id=hnc_receipt_id,
            auris_receipt_id=auris_receipt_id,
            provider_receipt_ids=provider_ids,
            provider_moment_digest=provider_digest,
            provider_source_timestamp=provider_timestamp,
        )
        if self.outcome == "TAMPERED":
            receipt["proposal_digest"] = "0" * 64
        elif self.outcome == "MISSING_PROVIDER_IDS":
            receipt.pop("provider_receipt_ids")
        elif self.outcome == "MISSING_PROVIDER_DIGEST":
            receipt.pop("provider_moment_digest")
        elif self.outcome == "MISSING_PROVIDER_TIMESTAMP":
            receipt.pop("provider_source_timestamp")
        self.receipts.append(receipt)
        return receipt


def _boundary(
    monkeypatch: pytest.MonkeyPatch,
    *,
    outcome: str = "ACCEPT",
    clock: _Clock | None = None,
) -> tuple[EconomicGovernanceBoundary, _DualHarness, _Clock]:
    runtime_clock = clock or _Clock()
    harness = _DualHarness(outcome)
    monkeypatch.setattr(
        crown_module,
        "validate_provider_moment",
        lambda hnc, auris, **kwargs: hnc["provider_moment"],
    )
    monkeypatch.setattr(
        boundary_module,
        "evaluate_cognition_governance",
        harness,
    )
    boundary = bind_economic_governance_boundary(
        council_receipt_supplier=_CouncilSupplier(),
        crown_receipt_supplier=_CrownSupplier(),
        trusted_council_supplier_ids=frozenset({COUNCIL_ID}),
        trusted_crown_supplier_ids=frozenset({CROWN_ID}),
        clock=runtime_clock,
        permit_ttl_s=2.0,
        warrant_ttl_s=30.0,
        provider_max_age_s=10.0,
    )
    return boundary, harness, runtime_clock


def _entry_intent(clock: _Clock, **overrides: Any) -> EconomicIntent:
    body = {
        "newClientOrderId": "cycle-1-entry",
        "quantity": "0.002",
        "side": "BUY",
        "symbol": "BTCUSDT",
        "type": "MARKET",
    }
    body.update(overrides.pop("body", {}))
    values: dict[str, Any] = {
        "venue": "binance",
        "environment": "live",
        "account_id_hash": ACCOUNT_HASH,
        "method": "POST",
        "path": "/api/v3/order",
        "operation": "MARKET_ORDER",
        "purpose": "ENTRY",
        "symbol": "BTCUSDT",
        "side": "BUY",
        "order_type": "MARKET",
        "quantity": "0.002",
        "quote_quantity": None,
        "limit_price": None,
        "stop_price": None,
        "take_profit": None,
        "reduce_only": False,
        "client_order_id": "cycle-1-entry",
        "authorization_receipt_id": "authorization:bounded-binance:cycle-1",
        "cycle_id": "cycle-1",
        "position_receipt_id": POSITION_BEFORE,
        "hnc_receipt_id": HNC,
        "auris_receipt_id": AURIS,
        "provider_receipt_ids": {
            POSITION_BEFORE,
            "provider:binance:account:1",
            "provider:binance:fee:1",
            "provider:binance:market:1",
        },
        "provider_moment_digest": PROVIDER_DIGEST,
        "provider_source_timestamp": str(int(clock.value - 1)),
        "body": body,
        "body_bindings": {
            "client_order_id": "/newClientOrderId",
            "order_type": "/type",
            "quantity": "/quantity",
            "side": "/side",
            "symbol": "/symbol",
        },
    }
    values.update(overrides)
    return EconomicIntent.build(**values)


def _scope(clock: _Clock, entry: EconomicIntent) -> ContingencyWarrantScope:
    return ContingencyWarrantScope.build(
        venue="binance",
        environment="live",
        account_id_hash=ACCOUNT_HASH,
        symbol="BTCUSDT",
        exposure_side="LONG",
        reduction_side="SELL",
        method="POST",
        path="/api/v3/order",
        order_type="MARKET",
        max_reduce_quantity="0.002",
        entry_intent_digest=entry.intent_digest,
        entry_client_order_id=entry.client_order_id,
        containment_client_order_id="cycle-1-containment",
        authorization_receipt_id=entry.authorization_receipt_id,
        cycle_id=entry.cycle_id,
        pre_entry_position_receipt_id=entry.position_receipt_id,
        provider_reduce_only_supported=True,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        provider_receipt_ids=entry.provider_receipt_ids,
        provider_moment_digest=entry.provider_moment_digest,
        provider_source_timestamp=str(int(clock.value - 1)),
    )


def _reduction_intent(
    clock: _Clock,
    entry: EconomicIntent,
    **overrides: Any,
) -> EconomicIntent:
    body = {
        "newClientOrderId": "cycle-1-containment",
        "quantity": "0.002",
        "reduceOnly": True,
        "side": "SELL",
        "symbol": "BTCUSDT",
        "type": "MARKET",
    }
    body.update(overrides.pop("body", {}))
    values: dict[str, Any] = {
        "venue": "binance",
        "environment": "live",
        "account_id_hash": ACCOUNT_HASH,
        "method": "POST",
        "path": "/api/v3/order",
        "operation": "MARKET_ORDER",
        "purpose": "CONTAINMENT_REDUCTION",
        "symbol": "BTCUSDT",
        "side": "SELL",
        "order_type": "MARKET",
        "quantity": "0.002",
        "quote_quantity": None,
        "limit_price": None,
        "stop_price": None,
        "take_profit": None,
        "reduce_only": True,
        "client_order_id": "cycle-1-containment",
        "authorization_receipt_id": entry.authorization_receipt_id,
        "cycle_id": entry.cycle_id,
        "position_receipt_id": POSITION_CURRENT,
        "parent_intent_digest": entry.intent_digest,
        "entry_receipt_id": ENTRY_RECEIPT,
        "position_side": "LONG",
        "observed_exposure_quantity": "0.002",
        "hnc_receipt_id": HNC,
        "auris_receipt_id": AURIS,
        "provider_receipt_ids": {
            POSITION_CURRENT,
            ENTRY_RECEIPT,
            "provider:binance:account:current",
            "provider:binance:market:current",
        },
        "provider_moment_digest": CURRENT_PROVIDER_DIGEST,
        "provider_source_timestamp": str(int(clock.value - 1)),
        "body": body,
        "body_bindings": {
            "client_order_id": "/newClientOrderId",
            "order_type": "/type",
            "quantity": "/quantity",
            "reduce_only": "/reduceOnly",
            "side": "/side",
            "symbol": "/symbol",
        },
    }
    values.update(overrides)
    return EconomicIntent.build(**values)


def _capital_close_scope(
    clock: _Clock,
    entry: EconomicIntent,
) -> ContingencyWarrantScope:
    return ContingencyWarrantScope.build(
        venue="capital",
        environment="live",
        account_id_hash=ACCOUNT_HASH,
        symbol="GOLD",
        exposure_side="LONG",
        reduction_side="SELL",
        method="DELETE",
        path="/positions/{provider_deal_id}",
        order_type="MARKET_CLOSE_BY_DEAL",
        max_reduce_quantity="0.01",
        entry_intent_digest=entry.intent_digest,
        entry_client_order_id=entry.client_order_id,
        containment_client_order_id="capital-cycle-1-close",
        authorization_receipt_id=entry.authorization_receipt_id,
        cycle_id=entry.cycle_id,
        pre_entry_position_receipt_id=entry.position_receipt_id,
        provider_reduce_only_supported=False,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        provider_receipt_ids=entry.provider_receipt_ids,
        provider_moment_digest=entry.provider_moment_digest,
        provider_source_timestamp=str(int(clock.value - 1)),
    )


def _capital_entry_intent(clock: _Clock) -> EconomicIntent:
    return EconomicIntent.build(
        venue="capital",
        environment="live",
        account_id_hash=ACCOUNT_HASH,
        method="POST",
        path="/positions",
        operation="MARKET_ORDER",
        purpose="ENTRY",
        symbol="GOLD",
        side="BUY",
        order_type="MARKET",
        quantity="0.01",
        quote_quantity=None,
        limit_price=None,
        stop_price=None,
        take_profit=None,
        reduce_only=False,
        client_order_id="capital-cycle-1-entry",
        authorization_receipt_id="authorization:capital:cycle-1",
        cycle_id="capital-cycle-1",
        position_receipt_id=POSITION_BEFORE,
        hnc_receipt_id=HNC,
        auris_receipt_id=AURIS,
        provider_receipt_ids={
            POSITION_BEFORE,
            "provider:capital:account:1",
            "provider:capital:market:1",
        },
        provider_moment_digest=PROVIDER_DIGEST,
        provider_source_timestamp=str(int(clock.value - 1)),
        body={
            "direction": "BUY",
            "epic": "GOLD",
            "forceOpen": True,
            "guaranteedStop": False,
            "orderType": "MARKET",
            "size": 0.01,
        },
        body_bindings={
            "order_type": "/orderType",
            "quantity": "/size",
            "side": "/direction",
            "symbol": "/epic",
        },
        body_requires_json_numbers=True,
    )


def _capital_close_intent(
    clock: _Clock,
    entry: EconomicIntent,
    **overrides: Any,
) -> EconomicIntent:
    deal_id = overrides.pop("provider_position_id", "CAPITAL-DEAL-1")
    values: dict[str, Any] = {
        "venue": "capital",
        "environment": "live",
        "account_id_hash": ACCOUNT_HASH,
        "method": "DELETE",
        "path": f"/positions/{deal_id}",
        "operation": "MARKET_ORDER",
        "purpose": "CONTAINMENT_REDUCTION",
        "symbol": "GOLD",
        "side": "SELL",
        "order_type": "MARKET_CLOSE_BY_DEAL",
        "quantity": "0.01",
        "quote_quantity": None,
        "limit_price": None,
        "stop_price": None,
        "take_profit": None,
        "reduce_only": True,
        "client_order_id": "capital-cycle-1-close",
        "authorization_receipt_id": entry.authorization_receipt_id,
        "cycle_id": entry.cycle_id,
        "position_receipt_id": POSITION_CURRENT,
        "parent_intent_digest": entry.intent_digest,
        "entry_receipt_id": ENTRY_RECEIPT,
        "position_side": "LONG",
        "observed_exposure_quantity": "0.01",
        "hnc_receipt_id": HNC,
        "auris_receipt_id": AURIS,
        "provider_receipt_ids": {
            POSITION_CURRENT,
            ENTRY_RECEIPT,
            "provider:capital:account:current",
            "provider:capital:market:current",
        },
        "provider_moment_digest": CURRENT_PROVIDER_DIGEST,
        "provider_source_timestamp": str(int(clock.value - 1)),
        "body": {},
        "body_bindings": {},
        "provider_position_id": deal_id,
    }
    values.update(overrides)
    return EconomicIntent.build(**values)


def test_intent_uses_canonical_decimal_text_and_binds_exact_wire_body() -> None:
    clock = _Clock()
    intent = _entry_intent(clock)
    reordered = _entry_intent(
        clock,
        body={
            "type": "MARKET",
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": "0.002",
            "newClientOrderId": "cycle-1-entry",
        },
    )
    changed_provider = _entry_intent(clock, provider_moment_digest="d" * 64)

    assert intent.body_json == reordered.body_json
    assert intent.intent_digest == reordered.intent_digest
    assert intent.intent_digest != changed_provider.intent_digest
    assert intent.payload()["request_body_digest"] == intent.body_digest

    with pytest.raises(ValueError, match="canonical_decimal_text"):
        _entry_intent(clock, quantity="0.0020")
    with pytest.raises(ValueError, match="without_floats"):
        _entry_intent(clock, body={"quantity": 0.002})


def test_only_allowlisted_composition_root_suppliers_can_bind_boundary() -> None:
    with pytest.raises(ValueError, match="council_supplier_not_allowlisted"):
        bind_economic_governance_boundary(
            council_receipt_supplier=_CouncilSupplier(),
            crown_receipt_supplier=_CrownSupplier(),
            trusted_council_supplier_ids=frozenset({"resolver:not-this-one"}),
            trusted_crown_supplier_ids=frozenset({CROWN_ID}),
        )
    with pytest.raises(ValueError, match="frozenset"):
        bind_economic_governance_boundary(
            council_receipt_supplier=_CouncilSupplier(),
            crown_receipt_supplier=_CrownSupplier(),
            trusted_council_supplier_ids={COUNCIL_ID},  # type: ignore[arg-type]
            trusted_crown_supplier_ids=frozenset({CROWN_ID}),
        )

    parameters = inspect.signature(EconomicGovernanceBoundary.prepare_mutation).parameters
    assert not {"approved", "decision", "queen_evaluated", "receipt"}.intersection(parameters)


def test_strict_accept_mints_evidence_only_then_calls_transport_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, harness, clock = _boundary(monkeypatch)
    intent = _entry_intent(clock)
    transport = Mock(return_value={"provider_order_id": "123"})

    permit = boundary.prepare_mutation(intent)
    result = boundary.consume_and_call(
        permit,
        method=intent.method,
        path=intent.path,
        body=json.loads(intent.body_json),
        transport=transport,
    )

    assert result == {"provider_order_id": "123"}
    assert permit.route_authorization_required is True
    assert permit.economic_mutation is False
    assert permit.action_eligible is False
    assert permit.intent_digest == intent.intent_digest
    assert permit.body_digest == intent.body_digest
    assert len(harness.calls) == 1
    transport.assert_called_once_with()


@pytest.mark.parametrize(
    "outcome",
    [
        "HOLD",
        "ABORT",
        "NO_DATA",
        "TAMPERED",
        "PROPOSAL_MISMATCH",
        "PROVIDER_MISMATCH",
        "HNC_MISMATCH",
        "MISSING_PROVIDER_IDS",
        "MISSING_PROVIDER_DIGEST",
        "MISSING_PROVIDER_TIMESTAMP",
    ],
)
def test_non_accept_or_inexact_dual_never_reaches_transport(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    boundary, _, clock = _boundary(monkeypatch, outcome=outcome)
    transport = Mock()

    with pytest.raises(EconomicGovernanceBlocked):
        boundary.prepare_mutation(_entry_intent(clock))

    transport.assert_not_called()


@pytest.mark.parametrize(
    "outcome",
    [
        "SHARED_WRONG_PROVIDER_IDS",
        "SHARED_WRONG_PROVIDER_DIGEST",
        "SHARED_WRONG_PROVIDER_TIMESTAMP",
    ],
)
def test_valid_dual_with_mutually_agreed_wrong_provider_moment_never_calls_transport(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    boundary, harness, clock = _boundary(monkeypatch, outcome=outcome)
    intent = _entry_intent(clock)
    transport = Mock()

    def governed_call() -> Any:
        permit = boundary.prepare_mutation(intent)
        return boundary.consume_and_call(
            permit,
            method=intent.method,
            path=intent.path,
            body=json.loads(intent.body_json),
            transport=transport,
        )

    with pytest.raises(
        EconomicGovernanceBlocked,
        match="exact_council_crown_accept_required",
    ):
        governed_call()

    wrong_but_valid = validate_dual_key_receipt(
        harness.receipts[-1],
        now=clock.value,
    )
    assert wrong_but_valid["decision"] == "ACCEPT"
    assert (
        tuple(wrong_but_valid["provider_receipt_ids"]),
        wrong_but_valid["provider_moment_digest"],
        wrong_but_valid["provider_source_timestamp"],
    ) != (
        intent.provider_receipt_ids,
        intent.provider_moment_digest,
        intent.provider_source_timestamp,
    )
    transport.assert_not_called()


def test_contingency_scope_cannot_mint_warrant_for_wrong_shared_provider_moment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, harness, clock = _boundary(
        monkeypatch,
        outcome="SHARED_WRONG_PROVIDER_DIGEST",
    )
    entry = _entry_intent(clock)
    transport = Mock()

    with pytest.raises(
        EconomicGovernanceBlocked,
        match="exact_council_crown_accept_required",
    ):
        boundary.approve_contingency_warrant(_scope(clock, entry))

    wrong_but_valid = validate_dual_key_receipt(
        harness.receipts[-1],
        now=clock.value,
    )
    assert wrong_but_valid["decision"] == "ACCEPT"
    assert wrong_but_valid["provider_moment_digest"] != entry.provider_moment_digest
    transport.assert_not_called()


def test_distinct_field_and_target_provider_moments_are_both_bound(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, harness, clock = _boundary(monkeypatch)
    intent = _entry_intent(
        clock,
        field_provider_receipt_ids=FIELD_PROVIDERS,
        field_provider_moment_digest=FIELD_PROVIDER_DIGEST,
        field_provider_source_timestamp=str(int(clock.value - 1)),
    )
    permit = boundary.prepare_mutation(intent)
    request = _request_from_evaluator_kwargs(harness.calls[-1])

    assert request.provider_receipt_ids == FIELD_PROVIDERS
    assert request.provider_moment_digest == FIELD_PROVIDER_DIGEST
    assert request.target_provider_receipt_ids == intent.provider_receipt_ids
    assert request.target_provider_moment_digest == intent.provider_moment_digest
    assert permit.provider_moment_digest == intent.provider_moment_digest
    assert harness.receipts[-1]["provider_receipt_ids"] == list(FIELD_PROVIDERS)


def test_partial_field_provider_moment_fails_before_either_voice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, harness, clock = _boundary(monkeypatch)

    with pytest.raises(ValueError, match="complete_field_provider_moment_required"):
        _entry_intent(
            clock,
            field_provider_receipt_ids=FIELD_PROVIDERS,
        )

    assert harness.calls == []


@pytest.mark.parametrize(
    ("method", "path", "body_change"),
    [
        ("PUT", "/api/v3/order", {}),
        ("POST", "/api/v3/other", {}),
        ("POST", "/api/v3/order", {"quantity": "0.003"}),
    ],
)
def test_method_path_or_body_drift_burns_permit_without_transport(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    body_change: dict[str, Any],
) -> None:
    boundary, _, clock = _boundary(monkeypatch)
    intent = _entry_intent(clock)
    permit = boundary.prepare_mutation(intent)
    body = json.loads(intent.body_json)
    body.update(body_change)
    transport = Mock()

    with pytest.raises(EconomicGovernanceBlocked, match="method_path_body"):
        boundary.consume_and_call(
            permit,
            method=method,
            path=path,
            body=body,
            transport=transport,
        )
    with pytest.raises(EconomicGovernanceBlocked, match="replayed"):
        boundary.consume_and_call(
            permit,
            method=intent.method,
            path=intent.path,
            body=json.loads(intent.body_json),
            transport=transport,
        )

    transport.assert_not_called()


def test_permit_tamper_replay_expiry_and_context_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = Mock()

    boundary, _, clock = _boundary(monkeypatch)
    intent = _entry_intent(clock)
    permit = boundary.prepare_mutation(intent)
    tampered = replace(permit, body_digest="f" * 64)
    with pytest.raises(EconomicGovernanceBlocked, match="tampered"):
        boundary.consume_and_call(
            tampered,
            method=intent.method,
            path=intent.path,
            body=json.loads(intent.body_json),
            transport=transport,
        )

    boundary, _, clock = _boundary(monkeypatch)
    intent = _entry_intent(clock)
    permit = boundary.prepare_mutation(intent)
    boundary.consume_and_call(
        permit,
        method=intent.method,
        path=intent.path,
        body=json.loads(intent.body_json),
        transport=transport,
    )
    with pytest.raises(EconomicGovernanceBlocked, match="replayed"):
        boundary.consume_and_call(
            permit,
            method=intent.method,
            path=intent.path,
            body=json.loads(intent.body_json),
            transport=transport,
        )

    boundary, _, clock = _boundary(monkeypatch)
    intent = _entry_intent(clock)
    permit = boundary.prepare_mutation(intent)
    clock.value += 3.0
    with pytest.raises(EconomicGovernanceBlocked, match="expired"):
        boundary.consume_and_call(
            permit,
            method=intent.method,
            path=intent.path,
            body=json.loads(intent.body_json),
            transport=transport,
        )

    boundary, _, clock = _boundary(monkeypatch)
    intent = _entry_intent(clock)
    permit = boundary.prepare_mutation(intent)
    with pytest.raises(EconomicGovernanceBlocked, match="context"):
        contextvars.Context().run(
            lambda: boundary.consume_and_call(
                permit,
                method=intent.method,
                path=intent.path,
                body=json.loads(intent.body_json),
                transport=transport,
            )
        )

    assert transport.call_count == 1


def test_contingency_warrant_only_mints_exact_deterministic_reduction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, harness, clock = _boundary(monkeypatch)
    entry = _entry_intent(clock)
    warrant = boundary.approve_contingency_warrant(_scope(clock, entry))
    reduction = _reduction_intent(clock, entry)
    transport = Mock(return_value={"closed": True})

    permit = boundary.prepare_contingency_reduction(warrant, reduction)
    result = boundary.consume_and_call(
        permit,
        method=reduction.method,
        path=reduction.path,
        body=json.loads(reduction.body_json),
        transport=transport,
    )

    assert result == {"closed": True}
    assert warrant.economic_mutation is False
    assert permit.permit_kind == "contingency_reduction"
    assert permit.contingency_warrant_id == warrant.warrant_id
    assert len(harness.calls) == 1
    transport.assert_called_once_with()
    with pytest.raises(EconomicGovernanceBlocked, match="already_used"):
        boundary.prepare_contingency_reduction(warrant, reduction)


@pytest.mark.parametrize(
    "mutation",
    ["over_quantity", "wrong_side", "not_reduce_only", "quote_quantity", "wrong_cycle", "missing_body_binding"],
)
def test_contingency_scope_rejects_any_non_reducing_variant(
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    boundary, _, clock = _boundary(monkeypatch)
    entry = _entry_intent(clock)
    warrant = boundary.approve_contingency_warrant(_scope(clock, entry))
    if mutation == "over_quantity":
        intent = _reduction_intent(
            clock,
            entry,
            quantity="0.003",
            observed_exposure_quantity="0.003",
            body={"quantity": "0.003"},
        )
    elif mutation == "wrong_side":
        intent = _reduction_intent(clock, entry, side="BUY", body={"side": "BUY"})
    elif mutation == "not_reduce_only":
        intent = _reduction_intent(
            clock,
            entry,
            reduce_only=False,
            body={"reduceOnly": False},
        )
    elif mutation == "quote_quantity":
        intent = _reduction_intent(clock, entry, quote_quantity="10")
    elif mutation == "wrong_cycle":
        intent = _reduction_intent(clock, entry, cycle_id="cycle-other")
    else:
        intent = _reduction_intent(
            clock,
            entry,
            body_bindings={
                "client_order_id": "/newClientOrderId",
                "order_type": "/type",
                "quantity": "/quantity",
                "side": "/side",
                "symbol": "/symbol",
            },
        )
    transport = Mock()

    with pytest.raises(EconomicGovernanceBlocked):
        boundary.prepare_contingency_reduction(warrant, intent)

    transport.assert_not_called()


def test_contingency_permit_still_requires_exact_last_mile_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, _, clock = _boundary(monkeypatch)
    entry = _entry_intent(clock)
    warrant = boundary.approve_contingency_warrant(_scope(clock, entry))
    reduction = _reduction_intent(clock, entry)
    permit = boundary.prepare_contingency_reduction(warrant, reduction)
    body = json.loads(reduction.body_json)
    body["quantity"] = "0.001"
    transport = Mock()

    with pytest.raises(EconomicGovernanceBlocked, match="method_path_body"):
        boundary.consume_and_call(
            permit,
            method=reduction.method,
            path=reduction.path,
            body=body,
            transport=transport,
        )

    transport.assert_not_called()


def test_capital_contingency_closes_only_the_exact_provider_deal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, _, clock = _boundary(monkeypatch)
    entry = _capital_entry_intent(clock)
    warrant = boundary.approve_contingency_warrant(
        _capital_close_scope(clock, entry)
    )
    close = _capital_close_intent(clock, entry)
    permit = boundary.prepare_contingency_reduction(warrant, close)
    transport = Mock(return_value={"dealReference": "CLOSE-REF-1"})

    result = boundary.consume_and_call(
        permit,
        method="DELETE",
        path="/positions/CAPITAL-DEAL-1",
        body={},
        transport=transport,
    )

    assert result == {"dealReference": "CLOSE-REF-1"}
    transport.assert_called_once_with()


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"path": "/positions/OTHER-DEAL"}, "exact_capital_provider_deal_close"),
        ({"body": {"dealId": "CAPITAL-DEAL-1"}}, "exact_capital_provider_deal_close"),
        (
            {
                "provider_position_id": "OTHER-DEAL",
                "path": "/positions/CAPITAL-DEAL-1",
            },
            "exact_capital_provider_deal_close",
        ),
    ],
)
def test_capital_contingency_rejects_path_body_or_deal_drift(
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, Any],
    reason: str,
) -> None:
    boundary, _, clock = _boundary(monkeypatch)
    entry = _capital_entry_intent(clock)
    warrant = boundary.approve_contingency_warrant(
        _capital_close_scope(clock, entry)
    )
    close = _capital_close_intent(clock, entry, **overrides)

    with pytest.raises(EconomicGovernanceBlocked, match=reason):
        boundary.prepare_contingency_reduction(warrant, close)


class _FakeCapitalLiveClient:
    enabled = True
    dry_run = False
    demo_mode = False

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        *,
        profit_distance: float,
        stop_distance: float,
    ) -> dict[str, Any]:
        self.calls.append(
            (
                "entry",
                symbol,
                side,
                quantity,
                profit_distance,
                stop_distance,
            )
        )
        return {"dealReference": "CAPITAL-ENTRY-REF"}

    def close_position(self, deal_id: str) -> dict[str, Any]:
        self.calls.append(("close", deal_id))
        return {"dealReference": "CAPITAL-CLOSE-REF"}


def _capital_market_evidence(
    clock: _Clock,
    *,
    include_context: bool = True,
) -> dict[str, Any]:
    now = clock.value
    bars = []
    for index in range(30):
        mid = 4_300.0 + index
        bars.append(
            {
                "timestamp": now - (30 - index) * 60.0,
                "open_bid": mid - 0.1,
                "open_ask": mid + 0.1,
                "high_bid": mid + 0.3,
                "high_ask": mid + 0.5,
                "low_bid": mid - 0.5,
                "low_ask": mid - 0.3,
                "close_bid": mid - 0.1,
                "close_ask": mid + 0.1,
                "volume": 100 + index,
            }
        )
    payloads = {
        "capital_quote": {
            "ask": 4_329.1,
            "bid": 4_328.9,
            "change_pct": 0.25,
            "epic": "GOLD",
            "high": 4_331.0,
            "low": 4_327.0,
            "market_status": "TRADEABLE",
            "symbol": "GOLD",
        },
        "capital_price_history": {"bars": bars, "epic": "GOLD", "resolution": "MINUTE"},
        "capital_account": {"available": 226.88, "balance": 226.88, "currency": "GBP"},
        "capital_positions": {"open_position_count": 0},
        "capital_working_orders": {"working_order_count": 0},
        "cftc_cot": {"market": "GOLD", "net_contracts": 1},
        "treasury_yield": {"ten_year_yield_pct": 4.2},
    }
    uris = {
        "capital_quote": "https://api-capital.backend-capital.com/api/v1/markets/GOLD",
        "capital_price_history": "https://api-capital.backend-capital.com/api/v1/prices/GOLD",
        "capital_account": "https://api-capital.backend-capital.com/api/v1/accounts",
        "capital_positions": "https://api-capital.backend-capital.com/api/v1/positions",
        "capital_working_orders": "https://api-capital.backend-capital.com/api/v1/workingorders",
        "cftc_cot": "https://publicreporting.cftc.gov/resource/6dca-aqww.json",
        "treasury_yield": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates",
    }
    receipts = []
    for kind, payload in payloads.items():
        if not include_context and kind in {"cftc_cot", "treasury_yield"}:
            continue
        observed = now - (86_400.0 if kind in {"cftc_cot", "treasury_yield"} else 1.0)
        receipts.append(
            build_capital_market_source_receipt(
                source_kind=kind,
                source_id=f"source:{kind}:test",
                source_uri=uris[kind],
                source_timestamp=observed,
                received_at=now - 0.5,
                payload=payload,
            )
        )
    return build_capital_market_evidence_receipt(
        source_receipts=sorted(receipts, key=lambda item: item["receipt_id"]),
        now=now,
    )


def _capital_plan(clock: _Clock) -> CapitalTradePlan:
    evidence = _capital_market_evidence(clock)
    moment = capital_market_provider_moment(evidence, now=clock.value)
    approval = {
        "event": "decided",
        "id": "capital-approval-1",
        "kind": "trade",
        "summary": "one minimum-size live Capital GOLD proof",
        "params": {
            "venue": "capital",
            "account_environment": "live_cfd",
            "account_id_hash": ACCOUNT_HASH,
            "symbol": "GOLD",
            "epic": "GOLD",
            "side_scope": ["BUY", "SELL"],
            "quantity": "0.01",
            "stop_distance": "5",
            "profit_distance": "5",
            "max_margin_gbp": "5",
            "one_cycle": True,
            "max_open_positions": 1,
            "containment_exit_authorized": True,
            "margin_product_authorized": True,
            "protective_stop_required": True,
            "guaranteed_stop": False,
            "transfers_allowed": False,
            "economic_mutation": False,
            "provider_submission_authorized": False,
            "intent_id": "intent:capital:minimum-gold-proof",
        },
        "prepared_by": "aureon-druid-council-live-proof",
        "risk": "high",
        "requires_human": True,
        "status": "approved",
        "note": "approved",
        "approver": "gary-operator-admin",
        "created_at": clock.value - 20.0,
        "decided_at": clock.value - 10.0,
        "approval_auth": {
            "authenticated": True,
            "identity_kind": "admin",
            "authn_method": "operator_static_bearer",
        },
    }
    authorization = issue_capital_owner_live_authorization_from_approval(
        approval,
        now=clock.value,
    )
    return CapitalTradePlan(
        cycle_id="capital-cycle-1",
        authorization_receipt_id=authorization["receipt_id"],
        authorization_receipt=authorization,
        account_id_hash=ACCOUNT_HASH,
        symbol="GOLD",
        epic="GOLD",
        side="BUY",
        quantity="0.01",
        stop_distance="5",
        profit_distance="5",
        entry_client_order_id="capital-cycle-1-entry",
        close_client_order_id="capital-cycle-1-close",
        target_moment=CapitalProviderMoment(
            receipt_ids=moment["receipt_ids"],
            moment_digest=moment["moment_digest"],
            source_timestamp=moment["source_timestamp"],
            position_receipt_id=moment["position_receipt_id"],
        ),
        field_moment=CapitalFieldMoment(
            hnc_receipt_id=HNC,
            auris_receipt_id=AURIS,
            provider_receipt_ids=FIELD_PROVIDERS,
            provider_moment_digest=FIELD_PROVIDER_DIGEST,
            provider_source_timestamp=str(int(clock.value - 1)),
        ),
        market_evidence_receipt=evidence,
    )


def test_bounded_capital_prepares_entry_and_durable_close_before_transport(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    boundary, harness, clock = _boundary(monkeypatch)
    recovery = bind_durable_contingency_recovery(
        adapter_id="aureon:capital:durable-close",
        trusted_adapter_ids=frozenset({"aureon:capital:durable-close"}),
        boundary=boundary,
        store_path=tmp_path / "capital-close.json",
        clock=clock,
        claim_ttl_s=5.0,
    )
    client = _FakeCapitalLiveClient()
    route = BoundedCapitalLiveTrade(
        client=client,
        boundary=boundary,
        recovery=recovery,
        clock=clock,
    )

    prepared = route.prepare(_capital_plan(clock))

    assert client.calls == []
    assert recovery.status(prepared.recovery_reference) == "AVAILABLE"
    assert len(harness.calls) == 2
    for call in harness.calls:
        payload = next(iter(call["tool_calls"][0]["arguments"].values()))
        evidence = json.loads(payload["decision_evidence_json"])
        assert evidence["recommended_side"] == "BUY"
        assert evidence["action_influence_allowed"] is True
        assert "available" not in payload["decision_evidence_json"]
        assert ACCOUNT_HASH not in payload["decision_evidence_json"]
    entry_ack = route.submit_entry(prepared)
    post_entry = CapitalProviderMoment(
        receipt_ids=tuple(
            sorted(
                {
                    POSITION_CURRENT,
                    ENTRY_RECEIPT,
                    "provider:capital:account:current",
                    "provider:capital:market:current",
                }
            )
        ),
        moment_digest=CURRENT_PROVIDER_DIGEST,
        source_timestamp=str(int(clock.value - 1)),
        position_receipt_id=POSITION_CURRENT,
    )
    close_ack = route.close_recovered(
        prepared,
        provider_deal_id="CAPITAL-DEAL-1",
        entry_receipt_id=ENTRY_RECEIPT,
        post_entry_moment=post_entry,
    )

    assert entry_ack == {"dealReference": "CAPITAL-ENTRY-REF"}
    assert close_ack == {"dealReference": "CAPITAL-CLOSE-REF"}
    assert client.calls == [
        ("entry", "GOLD", "BUY", 0.01, 5.0, 5.0),
        ("close", "CAPITAL-DEAL-1"),
    ]
    assert recovery.status(prepared.recovery_reference) == "RETURNED"
    assert len(harness.calls) == 2


def test_bounded_capital_rejects_non_minimum_size_before_any_voice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, harness, clock = _boundary(monkeypatch)

    with pytest.raises(ValueError, match="minimum_gold_size"):
        replace(_capital_plan(clock), quantity="0.02")

    assert harness.calls == []


def test_bounded_capital_evidence_hold_blocks_before_any_voice(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    boundary, harness, clock = _boundary(monkeypatch)
    recovery = bind_durable_contingency_recovery(
        adapter_id="aureon:capital:evidence-hold",
        trusted_adapter_ids=frozenset({"aureon:capital:evidence-hold"}),
        boundary=boundary,
        store_path=tmp_path / "capital-evidence-hold.json",
        clock=clock,
    )
    held = _capital_market_evidence(clock, include_context=False)
    moment = capital_market_provider_moment(held, now=clock.value)
    plan = replace(
        _capital_plan(clock),
        market_evidence_receipt=held,
        target_moment=CapitalProviderMoment(
            receipt_ids=moment["receipt_ids"],
            moment_digest=moment["moment_digest"],
            source_timestamp=moment["source_timestamp"],
            position_receipt_id=moment["position_receipt_id"],
        ),
    )
    route = BoundedCapitalLiveTrade(
        client=_FakeCapitalLiveClient(),
        boundary=boundary,
        recovery=recovery,
        clock=clock,
    )

    with pytest.raises(EconomicGovernanceBlocked, match="capital_market_evidence_action_hold"):
        route.prepare(plan)

    assert harness.calls == []


class _FakeBinanceResponse:
    status_code = 200
    headers: dict[str, str] = {}
    text = ""

    @staticmethod
    def json() -> dict[str, Any]:
        return {"provider": "fake-binance"}


class _FakeBinanceSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None,
        data: dict[str, Any] | None,
        timeout: int,
    ) -> _FakeBinanceResponse:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "params": dict(params or {}),
                "data": dict(data or {}),
                "timeout": timeout,
            }
        )
        return _FakeBinanceResponse()


def _live_binance_client(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[BinanceClient, _FakeBinanceSession]:
    monkeypatch.setenv("BINANCE_API_KEY", "test-key-not-a-provider-secret")
    monkeypatch.setenv("BINANCE_API_SECRET", "test-secret-not-a-provider-secret")
    monkeypatch.setenv("BINANCE_DRY_RUN", "false")
    monkeypatch.setenv("BINANCE_USE_TESTNET", "false")
    monkeypatch.setenv("BINANCE_TESTNET", "false")
    monkeypatch.setenv("BINANCE_UK_MODE", "false")
    client = BinanceClient()
    session = _FakeBinanceSession()
    client.session = session
    client._rate_limiter = None
    client.max_retries = 0
    monkeypatch.setattr(client, "_get_server_timestamp", lambda: 1_786_473_600_000)
    return client, session


def test_binance_live_signed_mutation_consumes_exact_transport_context_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, _, clock = _boundary(monkeypatch)
    intent = _entry_intent(clock)
    permit = boundary.prepare_mutation(intent)
    body = json.loads(intent.body_json)
    client, session = _live_binance_client(monkeypatch)

    def transport() -> dict[str, Any]:
        first = client._signed_request(intent.method, intent.path, dict(body))
        with pytest.raises(EconomicGovernanceBlocked, match="replayed"):
            client._signed_request(intent.method, intent.path, dict(body))
        return first

    result = boundary.consume_and_call(
        permit,
        method=intent.method,
        path=intent.path,
        body=body,
        transport=transport,
    )

    assert result == {"provider": "fake-binance"}
    assert len(session.calls) == 1
    sent = session.calls[0]
    assert sent["method"] == "POST"
    assert sent["url"] == f"{BINANCE_MAINNET}/api/v3/order"
    assert sent["data"] == {}
    assert {
        key: value
        for key, value in sent["params"].items()
        if key not in {"recvWindow", "signature", "timestamp"}
    } == body
    with pytest.raises(EconomicGovernanceBlocked, match="context_required"):
        client._signed_request(intent.method, intent.path, dict(body))
    assert len(session.calls) == 1


@pytest.mark.parametrize("tamper", ["body", "path"])
def test_binance_live_signed_mutation_rejects_tampered_wire_binding_before_http(
    monkeypatch: pytest.MonkeyPatch,
    tamper: str,
) -> None:
    boundary, _, clock = _boundary(monkeypatch)
    intent = _entry_intent(clock)
    permit = boundary.prepare_mutation(intent)
    body = json.loads(intent.body_json)
    client, session = _live_binance_client(monkeypatch)
    sent_body = {**body, "side": "SELL"} if tamper == "body" else body
    sent_path = "/api/v3/order/amend/keepPriority" if tamper == "path" else intent.path

    with pytest.raises(EconomicGovernanceBlocked, match="method_path_body"):
        boundary.consume_and_call(
            permit,
            method=intent.method,
            path=intent.path,
            body=body,
            transport=lambda: client._signed_request(
                intent.method,
                sent_path,
                dict(sent_body),
            ),
        )

    assert session.calls == []


def test_binance_signed_mutation_rejects_alternate_parameter_location(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    boundary, _, clock = _boundary(monkeypatch)
    intent = _entry_intent(clock)
    permit = boundary.prepare_mutation(intent)
    body = json.loads(intent.body_json)
    client, session = _live_binance_client(monkeypatch)
    guarded_do_request = client._do_request

    def move_symbol_to_body(
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        timeout: int = 15,
        *,
        _economic_dispatch: object | None = None,
    ) -> Any:
        assert data is None
        altered_query = dict(params or {})
        altered_body = {"symbol": altered_query.pop("symbol")}
        return guarded_do_request(
            method,
            path,
            params=altered_query,
            data=altered_body,
            timeout=timeout,
            _economic_dispatch=_economic_dispatch,
        )

    monkeypatch.setattr(client, "_do_request", move_symbol_to_body)
    with pytest.raises(EconomicGovernanceBlocked, match="query_and_body"):
        boundary.consume_and_call(
            permit,
            method=intent.method,
            path=intent.path,
            body=body,
            transport=lambda: client._signed_request(
                intent.method,
                intent.path,
                dict(body),
            ),
        )

    assert session.calls == []


def test_binance_direct_request_helper_cannot_bypass_signed_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session = _live_binance_client(monkeypatch)

    with pytest.raises(EconomicGovernanceBlocked, match="dispatch_capability"):
        client._do_request(
            "POST",
            "/api/v3/order",
            params={"symbol": "BTCUSDT", "side": "BUY"},
        )

    assert session.calls == []


def test_binance_dry_run_and_testnet_cannot_mutate_the_live_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session = _live_binance_client(monkeypatch)
    body = {"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET"}

    client.dry_run = True
    with pytest.raises(EconomicGovernanceBlocked, match="dry_run"):
        client._signed_request("POST", "/api/v3/order", dict(body))
    assert session.calls == []

    client.dry_run = False
    client.use_testnet = True
    client.base = BINANCE_MAINNET
    with pytest.raises(EconomicGovernanceBlocked, match="testnet_endpoint"):
        client._signed_request("POST", "/api/v3/order", dict(body))
    assert session.calls == []

    client.base = BINANCE_TESTNET
    result = client._signed_request("POST", "/api/v3/order", dict(body))
    assert result == {"provider": "fake-binance"}
    assert len(session.calls) == 1
    assert session.calls[0]["url"] == f"{BINANCE_TESTNET}/api/v3/order"
