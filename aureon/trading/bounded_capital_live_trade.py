"""One-shot Capital CFD route behind exact dual-key economic governance.

The route is deliberately inert until its caller supplies independently
validated Council/Crown suppliers through ``EconomicGovernanceBoundary``.
It prepares the entry permit and durable exact-deal close warrant before the
entry transport is callable.  Submission acknowledgements never count as
fills; provider confirmation and position read-back remain mandatory.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Protocol

from aureon.governance.capital_owner_authorization import (
    validate_capital_owner_live_authorization_receipt,
)
from aureon.governance.durable_contingency import (
    DurableContingencyRecordRef,
    DurableContingencyRecovery,
)
from aureon.governance.economic_boundary import (
    ContingencyWarrant,
    ContingencyWarrantScope,
    EconomicGovernanceBlocked,
    EconomicGovernanceBoundary,
    EconomicIntent,
    EconomicMutationPermit,
)
from aureon.trading.capital_market_evidence import (
    capital_market_decision_summary,
    capital_market_provider_moment,
    validate_capital_market_evidence_receipt,
)

VENUE = "capital"
ENVIRONMENT = "live"
ENTRY_PATH = "/positions"
CLOSE_PATH_TEMPLATE = "/positions/{provider_deal_id}"
ENTRY_ORDER_TYPE = "MARKET"
CLOSE_ORDER_TYPE = "MARKET_CLOSE_BY_DEAL"


class CapitalLiveClient(Protocol):
    enabled: bool
    dry_run: bool
    demo_mode: bool

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        *,
        profit_distance: float,
        stop_distance: float,
    ) -> Mapping[str, Any]: ...

    def close_position(self, deal_id: str) -> Mapping[str, Any]: ...


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _digest(value: Any, name: str) -> str:
    result = _text(value, name).lower()
    if len(result) != 64 or any(char not in "0123456789abcdef" for char in result):
        raise ValueError(f"{name}_must_be_sha256")
    return result


def _decimal(value: Any, name: str, *, positive: bool = True) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name}_must_be_decimal") from exc
    if not result.is_finite() or (positive and result <= 0):
        raise ValueError(f"{name}_must_be_positive_finite")
    return result


def _decimal_text(value: Any, name: str) -> str:
    result = _decimal(value, name)
    text = format(result, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _receipt_ids(values: tuple[str, ...], position_receipt_id: str) -> tuple[str, ...]:
    result = tuple(sorted({_text(value, "provider_receipt_id") for value in values}))
    if not result or position_receipt_id not in result:
        raise ValueError("position_receipt_must_be_in_provider_lineage")
    return result


@dataclass(frozen=True, slots=True)
class ProviderMoment:
    receipt_ids: tuple[str, ...]
    moment_digest: str
    source_timestamp: str
    position_receipt_id: str

    def __post_init__(self) -> None:
        _receipt_ids(self.receipt_ids, self.position_receipt_id)
        _digest(self.moment_digest, "provider_moment_digest")
        _decimal(self.source_timestamp, "provider_source_timestamp")


@dataclass(frozen=True, slots=True)
class FieldMoment:
    hnc_receipt_id: str
    auris_receipt_id: str
    provider_receipt_ids: tuple[str, ...]
    provider_moment_digest: str
    provider_source_timestamp: str

    def __post_init__(self) -> None:
        if not self.hnc_receipt_id.startswith("hnc:live_field:"):
            raise ValueError("live_hnc_receipt_required")
        if not self.auris_receipt_id.startswith("auris:cosmic_state:"):
            raise ValueError("live_auris_receipt_required")
        if not self.provider_receipt_ids:
            raise ValueError("field_provider_receipt_ids_required")
        _digest(self.provider_moment_digest, "field_provider_moment_digest")
        _decimal(self.provider_source_timestamp, "field_provider_source_timestamp")


@dataclass(frozen=True, slots=True)
class CapitalTradePlan:
    cycle_id: str
    authorization_receipt_id: str
    authorization_receipt: Mapping[str, Any]
    account_id_hash: str
    symbol: str
    epic: str
    side: str
    quantity: str
    stop_distance: str
    profit_distance: str
    entry_client_order_id: str
    close_client_order_id: str
    target_moment: ProviderMoment
    field_moment: FieldMoment
    market_evidence_receipt: Mapping[str, Any]

    def __post_init__(self) -> None:
        _text(self.cycle_id, "cycle_id")
        _text(self.authorization_receipt_id, "authorization_receipt_id")
        if not isinstance(self.authorization_receipt, Mapping):
            raise ValueError("capital_owner_authorization_receipt_required")
        if not isinstance(self.market_evidence_receipt, Mapping):
            raise ValueError("capital_market_evidence_receipt_required")
        _digest(self.account_id_hash, "account_id_hash")
        _text(self.symbol, "symbol")
        _text(self.epic, "epic")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("capital_side_must_be_buy_or_sell")
        if _decimal(self.quantity, "quantity") != Decimal("0.01"):
            raise ValueError("capital_minimum_gold_size_required")
        _decimal(self.stop_distance, "stop_distance")
        _decimal(self.profit_distance, "profit_distance")
        if self.entry_client_order_id == self.close_client_order_id:
            raise ValueError("distinct_entry_and_close_ids_required")

    @property
    def exposure_side(self) -> str:
        return "LONG" if self.side == "BUY" else "SHORT"

    @property
    def close_side(self) -> str:
        return "SELL" if self.side == "BUY" else "BUY"

    @property
    def entry_body(self) -> dict[str, Any]:
        return {
            "direction": self.side,
            "epic": self.epic,
            "forceOpen": True,
            "guaranteedStop": False,
            "orderType": ENTRY_ORDER_TYPE,
            "profitDistance": float(Decimal(self.profit_distance)),
            "size": float(Decimal(self.quantity)),
            "stopDistance": float(Decimal(self.stop_distance)),
        }

    @property
    def entry_state_anchor(self) -> str:
        return _sha(
            {
                "account_id_hash": self.account_id_hash,
                "authorization_receipt_id": self.authorization_receipt_id,
                "cycle_id": self.cycle_id,
                "entry_body": self.entry_body,
                "field_provider_moment_digest": self.field_moment.provider_moment_digest,
                "target_provider_moment_digest": self.target_moment.moment_digest,
            }
        )

    def build_entry_intent(self, *, decision_evidence: Mapping[str, Any]) -> EconomicIntent:
        body = self.entry_body
        return EconomicIntent.build(
            venue=VENUE,
            environment=ENVIRONMENT,
            account_id_hash=self.account_id_hash,
            method="POST",
            path=ENTRY_PATH,
            operation="MARKET_ORDER",
            purpose="ENTRY",
            symbol=self.epic,
            side=self.side,
            order_type=ENTRY_ORDER_TYPE,
            quantity=self.quantity,
            quote_quantity=None,
            limit_price=None,
            stop_price=self.stop_distance,
            take_profit=self.profit_distance,
            reduce_only=False,
            client_order_id=self.entry_client_order_id,
            authorization_receipt_id=self.authorization_receipt_id,
            cycle_id=self.cycle_id,
            position_receipt_id=self.target_moment.position_receipt_id,
            hnc_receipt_id=self.field_moment.hnc_receipt_id,
            auris_receipt_id=self.field_moment.auris_receipt_id,
            provider_receipt_ids=self.target_moment.receipt_ids,
            provider_moment_digest=self.target_moment.moment_digest,
            provider_source_timestamp=self.target_moment.source_timestamp,
            body=body,
            body_bindings={
                "order_type": "/orderType",
                "quantity": "/size",
                "side": "/direction",
                "symbol": "/epic",
            },
            field_provider_receipt_ids=self.field_moment.provider_receipt_ids,
            field_provider_moment_digest=self.field_moment.provider_moment_digest,
            field_provider_source_timestamp=self.field_moment.provider_source_timestamp,
            body_requires_json_numbers=True,
            decision_evidence=decision_evidence,
        )

    def build_close_scope(
        self,
        entry: EconomicIntent,
        *,
        decision_evidence: Mapping[str, Any],
    ) -> ContingencyWarrantScope:
        return ContingencyWarrantScope.build(
            venue=VENUE,
            environment=ENVIRONMENT,
            account_id_hash=self.account_id_hash,
            symbol=self.epic,
            exposure_side=self.exposure_side,
            reduction_side=self.close_side,
            method="DELETE",
            path=CLOSE_PATH_TEMPLATE,
            order_type=CLOSE_ORDER_TYPE,
            max_reduce_quantity=self.quantity,
            entry_intent_digest=entry.intent_digest,
            entry_client_order_id=self.entry_client_order_id,
            containment_client_order_id=self.close_client_order_id,
            authorization_receipt_id=self.authorization_receipt_id,
            cycle_id=self.cycle_id,
            pre_entry_position_receipt_id=self.target_moment.position_receipt_id,
            provider_reduce_only_supported=False,
            hnc_receipt_id=self.field_moment.hnc_receipt_id,
            auris_receipt_id=self.field_moment.auris_receipt_id,
            provider_receipt_ids=self.target_moment.receipt_ids,
            provider_moment_digest=self.target_moment.moment_digest,
            provider_source_timestamp=self.target_moment.source_timestamp,
            field_provider_receipt_ids=self.field_moment.provider_receipt_ids,
            field_provider_moment_digest=self.field_moment.provider_moment_digest,
            field_provider_source_timestamp=self.field_moment.provider_source_timestamp,
            decision_evidence=decision_evidence,
        )

    def build_close_intent(
        self,
        *,
        entry: EconomicIntent,
        provider_deal_id: str,
        entry_receipt_id: str,
        post_entry_moment: ProviderMoment,
    ) -> EconomicIntent:
        deal_id = _text(provider_deal_id, "provider_deal_id")
        if any(token in deal_id for token in ("/", "?", "#", "{")):
            raise ValueError("canonical_provider_deal_id_required")
        return EconomicIntent.build(
            venue=VENUE,
            environment=ENVIRONMENT,
            account_id_hash=self.account_id_hash,
            method="DELETE",
            path=f"/positions/{deal_id}",
            operation="MARKET_ORDER",
            purpose="CONTAINMENT_REDUCTION",
            symbol=self.epic,
            side=self.close_side,
            order_type=CLOSE_ORDER_TYPE,
            quantity=self.quantity,
            quote_quantity=None,
            limit_price=None,
            stop_price=None,
            take_profit=None,
            reduce_only=True,
            client_order_id=self.close_client_order_id,
            authorization_receipt_id=self.authorization_receipt_id,
            cycle_id=self.cycle_id,
            position_receipt_id=post_entry_moment.position_receipt_id,
            parent_intent_digest=entry.intent_digest,
            entry_receipt_id=_text(entry_receipt_id, "entry_receipt_id"),
            position_side=self.exposure_side,
            observed_exposure_quantity=self.quantity,
            hnc_receipt_id=self.field_moment.hnc_receipt_id,
            auris_receipt_id=self.field_moment.auris_receipt_id,
            provider_receipt_ids=post_entry_moment.receipt_ids,
            provider_moment_digest=post_entry_moment.moment_digest,
            provider_source_timestamp=post_entry_moment.source_timestamp,
            body={},
            body_bindings={},
            field_provider_receipt_ids=self.field_moment.provider_receipt_ids,
            field_provider_moment_digest=self.field_moment.provider_moment_digest,
            field_provider_source_timestamp=self.field_moment.provider_source_timestamp,
            provider_position_id=deal_id,
        )


@dataclass(frozen=True, slots=True)
class PreparedCapitalTrade:
    plan: CapitalTradePlan
    entry_intent: EconomicIntent
    entry_permit: EconomicMutationPermit
    close_scope: ContingencyWarrantScope
    close_warrant: ContingencyWarrant
    recovery_reference: DurableContingencyRecordRef


class BoundedCapitalLiveTrade:
    """Prepare first, then submit exactly once through the guarded client."""

    def __init__(
        self,
        *,
        client: CapitalLiveClient,
        boundary: EconomicGovernanceBoundary,
        recovery: DurableContingencyRecovery,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if not isinstance(boundary, EconomicGovernanceBoundary):
            raise TypeError("economic_governance_boundary_required")
        if not isinstance(recovery, DurableContingencyRecovery):
            raise TypeError("durable_contingency_recovery_required")
        if recovery.boundary is not boundary:
            raise ValueError("capital_recovery_boundary_mismatch")
        if not callable(clock):
            raise TypeError("capital_route_clock_callable_required")
        self.client = client
        self.boundary = boundary
        self.recovery = recovery
        self.clock = clock

    def _require_live_client(self) -> None:
        if (
            self.client.enabled is not True
            or self.client.dry_run is not False
            or self.client.demo_mode is not False
        ):
            raise EconomicGovernanceBlocked("enabled_live_capital_client_required")

    def prepare(self, plan: CapitalTradePlan) -> PreparedCapitalTrade:
        self._require_live_client()
        current = float(self.clock())
        evidence = validate_capital_market_evidence_receipt(
            plan.market_evidence_receipt,
            now=current,
        )
        expected_moment = capital_market_provider_moment(evidence, now=current)
        observed_moment = {
            "receipt_ids": plan.target_moment.receipt_ids,
            "moment_digest": plan.target_moment.moment_digest,
            "source_timestamp": plan.target_moment.source_timestamp,
            "position_receipt_id": plan.target_moment.position_receipt_id,
        }
        if observed_moment != expected_moment:
            raise EconomicGovernanceBlocked("capital_market_evidence_provider_moment_mismatch")
        if evidence["action_influence_allowed"] is not True:
            raise EconomicGovernanceBlocked("capital_market_evidence_action_hold")
        if plan.side != evidence["recommended_side"]:
            raise EconomicGovernanceBlocked("capital_plan_side_evidence_mismatch")
        if plan.epic != evidence["epic"] or plan.symbol != evidence["symbol"]:
            raise EconomicGovernanceBlocked("capital_plan_target_evidence_mismatch")
        decision_evidence = capital_market_decision_summary(evidence, now=current)
        plan = replace(plan, market_evidence_receipt=evidence)
        authorization = validate_capital_owner_live_authorization_receipt(
            plan.authorization_receipt,
            now=current,
            expected_account_id_hash=plan.account_id_hash,
            expected_side=plan.side,
            expected_stop_distance=Decimal(plan.stop_distance),
            expected_profit_distance=Decimal(plan.profit_distance),
        )
        if authorization["receipt_id"] != plan.authorization_receipt_id:
            raise EconomicGovernanceBlocked("capital_owner_authorization_id_mismatch")
        entry = plan.build_entry_intent(decision_evidence=decision_evidence)
        entry_permit = self.boundary.prepare_mutation(entry)
        close_scope = plan.build_close_scope(
            entry,
            decision_evidence=decision_evidence,
        )
        close_warrant = self.boundary.approve_contingency_warrant(close_scope)
        reference = self.recovery.register(
            close_warrant,
            close_scope,
            entry_state_anchor=plan.entry_state_anchor,
        )
        reference = self.recovery.bind_route_state(reference)
        self.recovery.verify_route_binding(reference)
        return PreparedCapitalTrade(
            plan=plan,
            entry_intent=entry,
            entry_permit=entry_permit,
            close_scope=close_scope,
            close_warrant=close_warrant,
            recovery_reference=reference,
        )

    def submit_entry(self, prepared: PreparedCapitalTrade) -> Mapping[str, Any]:
        self._require_live_client()
        plan = prepared.plan
        return self.boundary.consume_capital_and_call(
            prepared.entry_permit,
            method="POST",
            path=ENTRY_PATH,
            body=plan.entry_body,
            transport=lambda: self.client.place_market_order(
                plan.symbol,
                plan.side,
                float(Decimal(plan.quantity)),
                profit_distance=float(Decimal(plan.profit_distance)),
                stop_distance=float(Decimal(plan.stop_distance)),
            ),
        )

    def close_recovered(
        self,
        prepared: PreparedCapitalTrade,
        *,
        provider_deal_id: str,
        entry_receipt_id: str,
        post_entry_moment: ProviderMoment,
    ) -> Mapping[str, Any]:
        return self.close_from_recovery(
            plan=prepared.plan,
            entry_intent=prepared.entry_intent,
            recovery_reference=prepared.recovery_reference,
            provider_deal_id=provider_deal_id,
            entry_receipt_id=entry_receipt_id,
            post_entry_moment=post_entry_moment,
        )

    def close_from_recovery(
        self,
        *,
        plan: CapitalTradePlan,
        entry_intent: EconomicIntent,
        recovery_reference: DurableContingencyRecordRef,
        provider_deal_id: str,
        entry_receipt_id: str,
        post_entry_moment: ProviderMoment,
    ) -> Mapping[str, Any]:
        """Use the pre-entry durable warrant after a process restart.

        This path cannot mint a new entry permit or call Council/Crown again.
        It accepts only the original exact entry intent plus the reciprocal
        durable record reference and fresh provider position evidence.
        """

        self._require_live_client()
        if not isinstance(plan, CapitalTradePlan):
            raise TypeError("capital_trade_plan_required")
        if not isinstance(entry_intent, EconomicIntent):
            raise TypeError("capital_entry_intent_required")
        if not isinstance(recovery_reference, DurableContingencyRecordRef):
            raise TypeError("capital_recovery_reference_required")
        if entry_intent.purpose != "ENTRY" or entry_intent.cycle_id != plan.cycle_id:
            raise EconomicGovernanceBlocked("capital_entry_intent_lineage_mismatch")
        if recovery_reference.entry_state_anchor != plan.entry_state_anchor:
            raise EconomicGovernanceBlocked("capital_recovery_plan_anchor_mismatch")
        close_intent = plan.build_close_intent(
            entry=entry_intent,
            provider_deal_id=provider_deal_id,
            entry_receipt_id=entry_receipt_id,
            post_entry_moment=post_entry_moment,
        )
        recovered = self.recovery.prepare_reduction(
            recovery_reference,
            close_intent,
        )
        return self.recovery.consume_and_call(
            recovered,
            method="DELETE",
            path=close_intent.path,
            body={},
            transport=lambda: self.client.close_position(provider_deal_id),
        )


__all__ = [
    "BoundedCapitalLiveTrade",
    "CapitalTradePlan",
    "FieldMoment",
    "PreparedCapitalTrade",
    "ProviderMoment",
]
