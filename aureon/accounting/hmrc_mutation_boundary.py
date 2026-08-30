"""Fail-closed HMRC mutation bridge for the canonical Aureon organism.

HMRC reads and OAuth token exchange are not economic mutations. Every HMRC
POST, PUT, or DELETE that changes filing/accounting state must match one exact
composition-root plan and pass the normal HNC/Auris/Council/Crown economic
boundary before the HTTP transport is invoked.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Collection, Mapping
from typing import Any, TypeVar

from aureon.governance.legacy_economic_unity import LegacyEconomicUnityGateway
from aureon.governance.legacy_unity_composition import (
    LegacyUnityCompositionHold,
    LegacyUnityIntentPlan,
    TrustedLegacyInvocationSupplier,
)

_T = TypeVar("_T")
_FACTORY_TOKEN = object()
_MUTATION_METHODS = frozenset({"POST", "PUT", "DELETE"})


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _reason_code(value: Any, fallback: str) -> str:
    candidate = str(value or "").strip().lower()
    if re.fullmatch(r"[a-z0-9_.:-]{1,128}", candidate):
        return candidate
    return fallback


class HMRCMutationHold(RuntimeError):
    """Machine-readable refusal before an HMRC mutation is transported."""

    def __init__(
        self,
        reason_code: str,
        *,
        receipt: Mapping[str, Any] | None = None,
    ) -> None:
        self.reason_code = _reason_code(reason_code, "hmrc_mutation_hold")
        self.receipt = None if receipt is None else dict(receipt)
        super().__init__(self.reason_code)


class HMRCMutationRegistry:
    """Composition-root registry of exact HMRC mutation plans."""

    def __init__(
        self,
        *,
        _factory_token: object,
        gateway: LegacyEconomicUnityGateway,
        invocation_supplier: TrustedLegacyInvocationSupplier,
        plans: Collection[LegacyUnityIntentPlan],
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_hmrc_mutation_registry")
        if not isinstance(gateway, LegacyEconomicUnityGateway):
            raise TypeError("legacy_economic_unity_gateway_required")
        if not isinstance(invocation_supplier, TrustedLegacyInvocationSupplier):
            raise TypeError("trusted_legacy_invocation_supplier_required")
        normalized = tuple(plans)
        if not normalized or any(
            not isinstance(item, LegacyUnityIntentPlan) for item in normalized
        ):
            raise ValueError("nonempty_hmrc_mutation_plans_required")

        capabilities = {item.capability_id: item for item in gateway.capabilities}
        by_route: dict[tuple[str, str, str, str], LegacyUnityIntentPlan] = {}
        for plan in normalized:
            if plan.venue != "hmrc" or plan.method not in _MUTATION_METHODS:
                raise ValueError("exact_hmrc_mutation_plan_required")
            capability = capabilities.get(plan.capability_id)
            if capability is None:
                raise ValueError("registered_hmrc_capability_required")
            if (
                capability.venue != plan.venue
                or capability.method != plan.method
                or capability.path != plan.path
                or capability.operation != plan.operation
                or capability.purpose != plan.purpose
                or capability.body_bindings != plan.body_bindings
            ):
                raise ValueError("hmrc_plan_capability_mismatch")
            key = (plan.environment, plan.method, plan.path, plan.body_json)
            if key in by_route:
                raise ValueError("hmrc_mutation_plans_must_be_unique")
            by_route[key] = plan

        self._gateway = gateway
        self._invocation_supplier = invocation_supplier
        self._plans = by_route

    @property
    def route_count(self) -> int:
        return len(self._plans)

    def execute(
        self,
        *,
        environment: str,
        method: str,
        path: str,
        body: Mapping[str, Any],
        transport: Callable[[], _T],
    ) -> _T:
        """Execute exactly one matching HMRC mutation or raise HOLD."""

        canonical_method = str(method or "").upper()
        if canonical_method not in _MUTATION_METHODS:
            raise HMRCMutationHold("hmrc_mutation_method_required")
        if (
            not isinstance(path, str)
            or not path.startswith("/")
            or "?" in path
            or "#" in path
        ):
            raise HMRCMutationHold("canonical_hmrc_path_required")
        if not isinstance(body, Mapping):
            raise HMRCMutationHold("canonical_hmrc_body_required")
        try:
            body_json = _canonical_json(body)
        except (TypeError, ValueError):
            raise HMRCMutationHold("canonical_hmrc_body_required") from None
        key = (
            str(environment or "").lower(),
            canonical_method,
            path,
            body_json,
        )
        plan = self._plans.get(key)
        if plan is None:
            raise HMRCMutationHold("exact_governed_hmrc_mutation_plan_required")
        if not callable(transport):
            raise TypeError("transport_callable_required")
        try:
            invocation = self._invocation_supplier.supply_legacy_invocation(plan)
        except LegacyUnityCompositionHold as exc:
            raise HMRCMutationHold(exc.reason_code) from None
        except Exception:
            raise HMRCMutationHold(
                "complete_fresh_hnc_auris_invocation_required"
            ) from None

        outcome = self._gateway.execute(invocation, transport=transport)
        if outcome.status != "EXECUTED":
            raise HMRCMutationHold(
                str(
                    outcome.receipt.get("reason")
                    or "hmrc_mutation_not_executed"
                ),
                receipt=outcome.receipt,
            )
        return outcome.provider_result


def bind_hmrc_mutation_registry(
    *,
    gateway: LegacyEconomicUnityGateway,
    invocation_supplier: TrustedLegacyInvocationSupplier,
    plans: Collection[LegacyUnityIntentPlan],
) -> HMRCMutationRegistry:
    """Bind exact HMRC routes at the trusted composition root."""

    return HMRCMutationRegistry(
        _factory_token=_FACTORY_TOKEN,
        gateway=gateway,
        invocation_supplier=invocation_supplier,
        plans=plans,
    )


__all__ = [
    "HMRCMutationHold",
    "HMRCMutationRegistry",
    "bind_hmrc_mutation_registry",
]
