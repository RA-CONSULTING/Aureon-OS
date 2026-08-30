"""Trusted 10-9-1 composition for preserved legacy economic capabilities.

Legacy callers describe the exact provider mutation but never choose their HNC
or Auris evidence.  This module resolves one already-published, linked 10-9-1
moment through an allowlisted local resolver and turns it into the immutable
``EconomicIntent`` consumed by :mod:`legacy_economic_unity`.

The supplier grants no authority.  Council plus Crown still have to accept the
resulting intent inside ``EconomicGovernanceBoundary`` before transport.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Protocol, runtime_checkable

from aureon.autonomous.aureon_ten_nine_one_thought_path import (
    TenNineOneEvidenceResolver,
    ThoughtPathRequest,
)
from aureon.governance.economic_boundary import EconomicIntent
from aureon.governance.legacy_economic_unity import LegacyEconomicInvocation
from aureon.swarm.auris_node_receipts import (
    DEFAULT_MAX_AGE_S,
    validate_provider_moment,
)
from aureon.swarm.druidic_council import ACTIVE_THRESHOLD

LEGACY_UNITY_PLAN_SCHEMA = "aureon.legacy-economic-unity-plan.v1"

_FACTORY_TOKEN = object()
_HEX_64 = frozenset("0123456789abcdef")


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}_required")
    result = value.strip()
    if len(result) > 65_536:
        raise ValueError(f"{label}_too_large")
    return result


def _digest(value: Any, label: str) -> str:
    result = _nonblank(value, label).lower()
    if len(result) != 64 or any(char not in _HEX_64 for char in result):
        raise ValueError(f"{label}_must_be_sha256")
    return result


def _json_value(value: Any, path: str) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}_keys_must_be_strings")
            normalized[key] = _json_value(nested, f"{path}.{key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_value(item, f"{path}[]") for item in value]
    raise ValueError(f"{path}_must_be_exact_json_without_floats")


def _canonical_json(value: Mapping[str, Any]) -> str:
    normalized = _json_value(value, "request_body")
    if not isinstance(normalized, dict):
        raise ValueError("request_body_must_be_an_object")
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_timestamp_text(value: float) -> str:
    result = format(Decimal(str(value)), "f")
    if "." in result:
        result = result.rstrip("0").rstrip(".")
    return "0" if Decimal(result) == 0 else result


class LegacyUnityCompositionHold(RuntimeError):
    """A safe, machine-readable refusal before Council/Crown evaluation."""

    def __init__(self, reason_code: str) -> None:
        candidate = str(reason_code or "").strip().lower()
        self.reason_code = (
            candidate
            if re.fullmatch(r"[a-z0-9_.:-]{1,128}", candidate)
            else "legacy_unity_composition_hold"
        )
        super().__init__(self.reason_code)


@dataclass(frozen=True, slots=True)
class LegacyUnityIntentPlan:
    """Exact legacy route material without caller-selected HNC/Auris evidence."""

    capability_id: str
    venue: str
    environment: str
    account_id_hash: str
    method: str
    path: str
    operation: str
    purpose: str
    symbol: str
    side: str
    order_type: str
    quantity: str | None
    quote_quantity: str | None
    limit_price: str | None
    stop_price: str | None
    take_profit: str | None
    reduce_only: bool
    client_order_id: str
    authorization_receipt_id: str
    cycle_id: str
    position_receipt_id: str
    body_json: str
    body_bindings: tuple[tuple[str, str], ...]
    parent_intent_digest: str | None = None
    entry_receipt_id: str | None = None
    position_side: str | None = None
    observed_exposure_quantity: str | None = None

    def __post_init__(self) -> None:
        if not _nonblank(self.capability_id, "capability_id").startswith("legacy-capability:"):
            raise ValueError("legacy_capability_id_required")
        if self.venue != _nonblank(self.venue, "venue").lower():
            raise ValueError("venue_must_be_lowercase")
        if self.environment != _nonblank(self.environment, "environment").lower():
            raise ValueError("environment_must_be_lowercase")
        _digest(self.account_id_hash, "account_id_hash")
        if self.method != _nonblank(self.method, "method").upper():
            raise ValueError("method_must_be_uppercase")
        if not self.path.startswith("/") or "?" in self.path or "#" in self.path:
            raise ValueError("canonical_provider_path_required")
        if self.operation != _nonblank(self.operation, "operation").upper():
            raise ValueError("operation_must_be_uppercase")
        if self.purpose != _nonblank(self.purpose, "purpose").upper():
            raise ValueError("purpose_must_be_uppercase")
        for label in (
            "symbol",
            "side",
            "order_type",
            "client_order_id",
            "authorization_receipt_id",
            "cycle_id",
            "position_receipt_id",
        ):
            _nonblank(getattr(self, label), label)
        if type(self.reduce_only) is not bool:
            raise ValueError("reduce_only_must_be_boolean")
        try:
            body = json.loads(self.body_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("canonical_request_body_required") from exc
        if not isinstance(body, Mapping) or _canonical_json(body) != self.body_json:
            raise ValueError("canonical_request_body_required")
        if self.body_bindings != tuple(sorted(self.body_bindings)):
            raise ValueError("body_bindings_must_be_sorted")
        names = [name for name, _ in self.body_bindings]
        if len(names) != len(set(names)):
            raise ValueError("body_bindings_must_be_unique")
        if self.parent_intent_digest is not None:
            _digest(self.parent_intent_digest, "parent_intent_digest")

    @classmethod
    def create(
        cls,
        *,
        capability_id: str,
        venue: str,
        environment: str,
        account_id_hash: str,
        method: str,
        path: str,
        operation: str,
        purpose: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str | None,
        quote_quantity: str | None,
        limit_price: str | None,
        stop_price: str | None,
        take_profit: str | None,
        reduce_only: bool,
        client_order_id: str,
        authorization_receipt_id: str,
        cycle_id: str,
        position_receipt_id: str,
        body: Mapping[str, Any],
        body_bindings: Mapping[str, str] | None = None,
        parent_intent_digest: str | None = None,
        entry_receipt_id: str | None = None,
        position_side: str | None = None,
        observed_exposure_quantity: str | None = None,
    ) -> LegacyUnityIntentPlan:
        return cls(
            capability_id=capability_id,
            venue=venue,
            environment=environment,
            account_id_hash=account_id_hash,
            method=method,
            path=path,
            operation=operation,
            purpose=purpose,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            quote_quantity=quote_quantity,
            limit_price=limit_price,
            stop_price=stop_price,
            take_profit=take_profit,
            reduce_only=reduce_only,
            client_order_id=client_order_id,
            authorization_receipt_id=authorization_receipt_id,
            cycle_id=cycle_id,
            position_receipt_id=position_receipt_id,
            body_json=_canonical_json(body),
            body_bindings=tuple(sorted((body_bindings or {}).items())),
            parent_intent_digest=parent_intent_digest,
            entry_receipt_id=entry_receipt_id,
            position_side=position_side,
            observed_exposure_quantity=observed_exposure_quantity,
        )

    def payload(self) -> dict[str, Any]:
        return {
            "schema": LEGACY_UNITY_PLAN_SCHEMA,
            "capability_id": self.capability_id,
            "venue": self.venue,
            "environment": self.environment,
            "account_id_hash": self.account_id_hash,
            "method": self.method,
            "path": self.path,
            "operation": self.operation,
            "purpose": self.purpose,
            "symbol": self.symbol,
            "side": self.side,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "quote_quantity": self.quote_quantity,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "take_profit": self.take_profit,
            "reduce_only": self.reduce_only,
            "client_order_id": self.client_order_id,
            "authorization_receipt_id": self.authorization_receipt_id,
            "cycle_id": self.cycle_id,
            "position_receipt_id": self.position_receipt_id,
            "parent_intent_digest": self.parent_intent_digest,
            "entry_receipt_id": self.entry_receipt_id,
            "position_side": self.position_side,
            "observed_exposure_quantity": self.observed_exposure_quantity,
            "request_body": json.loads(self.body_json),
            "body_bindings": dict(self.body_bindings),
        }

    @property
    def plan_digest(self) -> str:
        return _sha256(self.payload())


@runtime_checkable
class TrustedLegacyInvocationSupplier(Protocol):
    """Composition-root-only supplier for one HNC/Auris-bound invocation."""

    supplier_id: str

    def supply_legacy_invocation(
        self,
        plan: LegacyUnityIntentPlan,
    ) -> LegacyEconomicInvocation:
        """Resolve a fresh 10-9-1 provider moment and bind it to ``plan``."""


class HncAurisLegacyInvocationSupplier:
    """Use an allowlisted 10-9-1 resolver without constructing producers."""

    def __init__(
        self,
        *,
        _factory_token: object,
        resolver: TenNineOneEvidenceResolver,
        max_age_s: float,
        clock: Callable[[], float],
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_hnc_auris_legacy_invocation_supplier")
        self._resolver = resolver
        self._max_age_s = max_age_s
        self._clock = clock
        self.supplier_id = f"aureon:legacy-unity-invocation:{resolver.resolver_id}"

    @staticmethod
    def _request(plan: LegacyUnityIntentPlan) -> ThoughtPathRequest:
        return ThoughtPathRequest(
            subject_type="legacy-capability",
            subject_id=plan.capability_id,
            process_id="aureon:legacy-economic-unity",
            stage="10-9-1-evidence-resolution",
            work_kind=plan.operation.lower(),
            prompt_digest=plan.plan_digest,
            brain_passport_id="evidence-only:no-model-authority",
        )

    def supply_legacy_invocation(
        self,
        plan: LegacyUnityIntentPlan,
    ) -> LegacyEconomicInvocation:
        if not isinstance(plan, LegacyUnityIntentPlan):
            raise TypeError("legacy_unity_intent_plan_required")
        request = self._request(plan)
        try:
            hnc = self._resolver.resolve_hnc_evidence(request)
            if not isinstance(hnc, Mapping):
                raise LegacyUnityCompositionHold("complete_fresh_hnc_evidence_required")
            hnc_id = str(hnc.get("receipt_id") or "")
            if not hnc_id.startswith("hnc:live_field:"):
                raise LegacyUnityCompositionHold("complete_fresh_hnc_evidence_required")
            auris = self._resolver.resolve_auris_evidence(
                request,
                answer_digest=plan.plan_digest,
                hnc_receipt_id=hnc_id,
            )
            if not isinstance(auris, Mapping):
                raise LegacyUnityCompositionHold("complete_fresh_auris_evidence_required")
            if auris.get("gate_open") is not True:
                raise LegacyUnityCompositionHold("auris_gate_open_required")
            gamma = auris.get("coherence_gamma")
            if type(gamma) not in {int, float} or not math.isfinite(float(gamma)):
                raise LegacyUnityCompositionHold("finite_auris_coherence_required")
            if float(gamma) < ACTIVE_THRESHOLD:
                raise LegacyUnityCompositionHold("active_auris_coherence_required")
            moment = validate_provider_moment(
                hnc,
                auris,
                now=self._clock(),
                max_age_s=self._max_age_s,
            )
            if plan.position_receipt_id not in moment.provider_receipt_ids:
                raise LegacyUnityCompositionHold(
                    "provider_position_receipt_not_in_hnc_auris_moment"
                )
            intent = EconomicIntent.build(
                venue=plan.venue,
                environment=plan.environment,
                account_id_hash=plan.account_id_hash,
                method=plan.method,
                path=plan.path,
                operation=plan.operation,
                purpose=plan.purpose,
                symbol=plan.symbol,
                side=plan.side,
                order_type=plan.order_type,
                quantity=plan.quantity,
                quote_quantity=plan.quote_quantity,
                limit_price=plan.limit_price,
                stop_price=plan.stop_price,
                take_profit=plan.take_profit,
                reduce_only=plan.reduce_only,
                client_order_id=plan.client_order_id,
                authorization_receipt_id=plan.authorization_receipt_id,
                cycle_id=plan.cycle_id,
                position_receipt_id=plan.position_receipt_id,
                parent_intent_digest=plan.parent_intent_digest,
                entry_receipt_id=plan.entry_receipt_id,
                position_side=plan.position_side,
                observed_exposure_quantity=plan.observed_exposure_quantity,
                hnc_receipt_id=moment.hnc_receipt_id,
                auris_receipt_id=moment.auris_receipt_id,
                provider_receipt_ids=moment.provider_receipt_ids,
                provider_moment_digest=moment.provider_moment_digest,
                provider_source_timestamp=_source_timestamp_text(moment.source_timestamp),
                body=json.loads(plan.body_json),
                body_bindings=dict(plan.body_bindings),
            )
        except LegacyUnityCompositionHold:
            raise
        except Exception:
            raise LegacyUnityCompositionHold(
                "complete_fresh_matching_hnc_auris_provider_moment_required"
            ) from None
        return LegacyEconomicInvocation(
            capability_id=plan.capability_id,
            intent=intent,
        )


def bind_hnc_auris_legacy_invocation_supplier(
    *,
    resolver: TenNineOneEvidenceResolver,
    trusted_resolver_ids: Collection[str],
    max_age_s: float = DEFAULT_MAX_AGE_S,
    clock: Callable[[], float] = time.time,
) -> HncAurisLegacyInvocationSupplier:
    """Bind one preconfigured local 10-9-1 resolver at the composition root."""

    if not isinstance(resolver, TenNineOneEvidenceResolver):
        raise TypeError("ten_nine_one_evidence_resolver_required")
    resolver_id = _nonblank(resolver.resolver_id, "resolver_id")
    allowlist = {
        _nonblank(item, "trusted_resolver_id").casefold()
        for item in trusted_resolver_ids
    }
    if not allowlist or resolver_id.casefold() not in allowlist:
        raise ValueError("legacy_unity_evidence_resolver_not_allowlisted")
    if isinstance(max_age_s, bool) or not isinstance(max_age_s, (int, float)):
        raise ValueError("positive_finite_max_age_required")
    age = float(max_age_s)
    if not math.isfinite(age) or age <= 0.0:
        raise ValueError("positive_finite_max_age_required")
    if not callable(clock):
        raise TypeError("clock_callable_required")
    return HncAurisLegacyInvocationSupplier(
        _factory_token=_FACTORY_TOKEN,
        resolver=resolver,
        max_age_s=age,
        clock=clock,
    )


__all__ = [
    "HncAurisLegacyInvocationSupplier",
    "LEGACY_UNITY_PLAN_SCHEMA",
    "LegacyUnityCompositionHold",
    "LegacyUnityIntentPlan",
    "TrustedLegacyInvocationSupplier",
    "bind_hnc_auris_legacy_invocation_supplier",
]
