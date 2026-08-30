"""Last-mile, evidence-bound governance for economic mutations.

The Council/Crown receipts used here remain evidence-only.  A transport call is
possible only when this boundary atomically consumes a short-lived, one-use
permit whose method, path, and canonical body still match the exact proposal
approved by both independent voices.

Production code must create this object once at its composition root with
allowlisted suppliers.  Request data never selects a supplier, passes a receipt,
or supplies an ``approved`` boolean.
"""

from __future__ import annotations

import asyncio
import contextvars
import hashlib
import json
import math
import secrets
import threading
import time
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from decimal import Decimal, InvalidOperation
from typing import Any, TypeVar

from aureon.governance.cognition_gate import (
    CognitionGovernanceRequest,
    TrustedCouncilReceiptSupplier,
    TrustedCrownReceiptSupplier,
    build_cognition_governance_request,
    evaluate_cognition_governance,
)
from aureon.governance.dual_key import validate_dual_key_receipt
from aureon.swarm.druidic_council import DEFAULT_MAX_AGE_S

ECONOMIC_INTENT_SCHEMA = "aureon.economic_intent.v1"
ECONOMIC_PERMIT_SCHEMA = "aureon.economic_mutation_permit.v1"
CONTINGENCY_SCOPE_SCHEMA = "aureon.economic_contingency_scope.v1"
CONTINGENCY_WARRANT_SCHEMA = "aureon.economic_contingency_warrant.v2"

_DIGEST_LENGTH = 64
_FUTURE_SKEW_S = Decimal("5")
_MAX_DECISION_EVIDENCE_BYTES = 32 * 1024
_CONTAINMENT_PURPOSE = "CONTAINMENT_REDUCTION"
_CONTAINMENT_OPERATION = "MARKET_ORDER"
_BODY_BINDING_FIELDS = frozenset(
    {
        "client_order_id",
        "order_type",
        "quantity",
        "quote_quantity",
        "reduce_only",
        "side",
        "symbol",
    }
)
_BOUNDARY_FACTORY_TOKEN = object()
_RECOVERY_CLAIM_TOKEN = object()
_EXECUTION_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "aureon_economic_execution_context",
    default=None,
)
_TRANSPORT_CONTEXT: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "aureon_economic_transport_context",
    default=None,
)

_T = TypeVar("_T")


class EconomicGovernanceBlocked(RuntimeError):
    """The exact economic mutation did not obtain consumable authority."""


def _nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name}_must_be_nonblank_canonical_text")
    return value


def _optional_nonblank(value: Any, name: str) -> str | None:
    if value is None:
        return None
    return _nonblank(value, name)


def _upper(value: Any, name: str) -> str:
    text = _nonblank(value, name)
    if text != text.upper():
        raise ValueError(f"{name}_must_be_uppercase")
    return text


def _lower(value: Any, name: str) -> str:
    text = _nonblank(value, name)
    if text != text.lower():
        raise ValueError(f"{name}_must_be_lowercase")
    return text


def _digest(value: Any, name: str) -> str:
    text = _nonblank(value, name)
    if len(text) != _DIGEST_LENGTH or any(char not in "0123456789abcdef" for char in text):
        raise ValueError(f"{name}_must_be_sha256")
    return text


def _canonical_decimal_text(
    value: Any,
    name: str,
    *,
    positive: bool = False,
) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name}_must_be_canonical_decimal_text")
    if "e" in value.lower() or value.startswith("+"):
        raise ValueError(f"{name}_must_be_canonical_decimal_text")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{name}_must_be_canonical_decimal_text") from exc
    if not number.is_finite():
        raise ValueError(f"{name}_must_be_finite")
    canonical = format(number, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    if Decimal(canonical) == 0:
        canonical = "0"
    if value != canonical:
        raise ValueError(f"{name}_must_be_canonical_decimal_text")
    if positive and number <= 0:
        raise ValueError(f"{name}_must_be_positive")
    return canonical


def _optional_decimal(value: Any, name: str, *, positive: bool = False) -> str | None:
    if value is None:
        return None
    return _canonical_decimal_text(value, name, positive=positive)


def _json_value(value: Any, path: str) -> Any:
    """Return exact JSON material while rejecting ambiguous float conversion."""

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
        return [
            _json_value(nested, f"{path}[{index}]")
            for index, nested in enumerate(value)
        ]
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


def _transport_json_value(value: Any, path: str) -> Any:
    """Return deterministic transport JSON, including required finite numbers."""

    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path}_must_be_finite")
        return value
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}_keys_must_be_strings")
            normalized[key] = _transport_json_value(nested, f"{path}.{key}")
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            _transport_json_value(nested, f"{path}[{index}]")
            for index, nested in enumerate(value)
        ]
    raise ValueError(f"{path}_must_be_exact_json")


def _canonical_transport_json(value: Mapping[str, Any]) -> str:
    normalized = _transport_json_value(value, "request_body")
    if not isinstance(normalized, dict):
        raise ValueError("request_body_must_be_an_object")
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _canonical_receipt_json(value: Mapping[str, Any]) -> str:
    """Serialize validated receipt evidence with round-trip-exact floats."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _validate_decision_evidence_json(value: str | None) -> None:
    if value is None:
        return
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > _MAX_DECISION_EVIDENCE_BYTES
    ):
        raise ValueError("bounded_decision_evidence_json_required")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("canonical_decision_evidence_json_required") from exc
    if (
        not isinstance(parsed, dict)
        or not parsed
        or _canonical_transport_json(parsed) != value
    ):
        raise ValueError("canonical_decision_evidence_json_required")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_payload(value: Mapping[str, Any]) -> str:
    return _sha256_text(_canonical_json(value))


def _receipt_ids(values: Collection[str], name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes, bytearray)):
        raise ValueError(f"{name}_must_be_a_collection")
    normalized = tuple(sorted(_nonblank(value, name[:-1]) for value in values))
    if not normalized:
        raise ValueError(f"{name}_required")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{name}_must_be_unique")
    return normalized


def _field_provider_moment(
    provider_receipt_ids: Collection[str] | None,
    provider_moment_digest: str | None,
    provider_source_timestamp: str | None,
) -> tuple[tuple[str, ...], str, str] | None:
    values = (
        provider_receipt_ids,
        provider_moment_digest,
        provider_source_timestamp,
    )
    if all(value is None for value in values):
        return None
    if any(value is None for value in values):
        raise ValueError("complete_field_provider_moment_required")
    assert provider_receipt_ids is not None
    assert provider_moment_digest is not None
    assert provider_source_timestamp is not None
    return (
        _receipt_ids(provider_receipt_ids, "field_provider_receipt_ids"),
        _digest(provider_moment_digest, "field_provider_moment_digest"),
        _canonical_decimal_text(
            provider_source_timestamp,
            "field_provider_source_timestamp",
        ),
    )


def _canonical_method(value: Any) -> str:
    method = _upper(value, "method")
    if method not in {"DELETE", "PATCH", "POST", "PUT"}:
        raise ValueError("economic_mutation_method_required")
    return method


def _canonical_path(value: Any) -> str:
    path = _nonblank(value, "path")
    if not path.startswith("/") or "#" in path or "?" in path:
        raise ValueError("canonical_endpoint_path_required")
    return path


def _json_pointer_value(document: Any, pointer: str) -> Any:
    pointer = _nonblank(pointer, "body_binding_pointer")
    if not pointer.startswith("/"):
        raise ValueError("body_binding_must_be_json_pointer")
    current = document
    for raw_token in pointer[1:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            if token not in current:
                raise ValueError("body_binding_pointer_missing")
            current = current[token]
        elif isinstance(current, list):
            if not token.isdigit() or int(token) >= len(current):
                raise ValueError("body_binding_pointer_missing")
            current = current[int(token)]
        else:
            raise ValueError("body_binding_pointer_missing")
    return current


def _binding_matches(field: str, observed: Any, expected: Any) -> bool:
    if field in {"quantity", "quote_quantity"}:
        if isinstance(observed, bool) or not isinstance(observed, (str, int)):
            return False
        try:
            return Decimal(str(observed)) == Decimal(str(expected))
        except InvalidOperation:
            return False
    if field in {"side", "order_type"}:
        return isinstance(observed, str) and observed.upper() == expected
    return observed == expected


@dataclass(frozen=True, slots=True)
class EconomicIntent:
    """Exact route intent; every economic amount is canonical Decimal text."""

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
    parent_intent_digest: str | None
    entry_receipt_id: str | None
    position_side: str | None
    observed_exposure_quantity: str | None
    hnc_receipt_id: str
    auris_receipt_id: str
    provider_receipt_ids: tuple[str, ...]
    provider_moment_digest: str
    provider_source_timestamp: str
    body_json: str
    body_bindings: tuple[tuple[str, str], ...]
    field_provider_receipt_ids: tuple[str, ...] | None = None
    field_provider_moment_digest: str | None = None
    field_provider_source_timestamp: str | None = None
    provider_position_id: str | None = None
    body_requires_json_numbers: bool = False
    decision_evidence_json: str | None = None

    def __post_init__(self) -> None:
        _lower(self.venue, "venue")
        _lower(self.environment, "environment")
        _digest(self.account_id_hash, "account_id_hash")
        _canonical_method(self.method)
        _canonical_path(self.path)
        _upper(self.operation, "operation")
        _upper(self.purpose, "purpose")
        _nonblank(self.symbol, "symbol")
        _upper(self.side, "side")
        _upper(self.order_type, "order_type")
        _optional_decimal(self.quantity, "quantity", positive=True)
        _optional_decimal(self.quote_quantity, "quote_quantity", positive=True)
        _optional_decimal(self.limit_price, "limit_price", positive=True)
        _optional_decimal(self.stop_price, "stop_price", positive=True)
        _optional_decimal(self.take_profit, "take_profit", positive=True)
        if type(self.reduce_only) is not bool:
            raise ValueError("reduce_only_must_be_boolean")
        _nonblank(self.client_order_id, "client_order_id")
        _nonblank(self.authorization_receipt_id, "authorization_receipt_id")
        _nonblank(self.cycle_id, "cycle_id")
        _nonblank(self.position_receipt_id, "position_receipt_id")
        if self.parent_intent_digest is not None:
            _digest(self.parent_intent_digest, "parent_intent_digest")
        _optional_nonblank(self.entry_receipt_id, "entry_receipt_id")
        if self.position_side is not None and _upper(self.position_side, "position_side") not in {
            "LONG",
            "SHORT",
        }:
            raise ValueError("position_side_must_be_long_or_short")
        _optional_decimal(
            self.observed_exposure_quantity,
            "observed_exposure_quantity",
            positive=True,
        )
        if not self.hnc_receipt_id.startswith("hnc:live_field:"):
            raise ValueError("live_hnc_receipt_required")
        if not self.auris_receipt_id.startswith("auris:cosmic_state:"):
            raise ValueError("live_auris_receipt_required")
        provider_ids = _receipt_ids(self.provider_receipt_ids, "provider_receipt_ids")
        if provider_ids != self.provider_receipt_ids:
            raise ValueError("provider_receipt_ids_must_be_sorted_unique")
        if self.position_receipt_id not in provider_ids:
            raise ValueError("position_receipt_must_be_in_provider_lineage")
        _digest(self.provider_moment_digest, "provider_moment_digest")
        _canonical_decimal_text(self.provider_source_timestamp, "provider_source_timestamp")
        _field_provider_moment(
            self.field_provider_receipt_ids,
            self.field_provider_moment_digest,
            self.field_provider_source_timestamp,
        )
        if self.provider_position_id is not None:
            provider_position_id = _nonblank(
                self.provider_position_id,
                "provider_position_id",
            )
            if any(token in provider_position_id for token in ("/", "?", "#", "{")):
                raise ValueError("canonical_provider_position_id_required")
        if type(self.body_requires_json_numbers) is not bool:
            raise ValueError("body_requires_json_numbers_must_be_boolean")
        if self.body_requires_json_numbers and self.venue != "capital":
            raise ValueError("capital_only_numeric_json_body_mode")
        _validate_decision_evidence_json(self.decision_evidence_json)
        try:
            parsed_body = json.loads(self.body_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("canonical_request_body_required") from exc
        canonical_body = (
            _canonical_transport_json(parsed_body)
            if self.body_requires_json_numbers
            else _canonical_json(parsed_body)
        )
        if not isinstance(parsed_body, dict) or canonical_body != self.body_json:
            raise ValueError("canonical_request_body_required")
        if tuple(sorted(self.body_bindings)) != self.body_bindings:
            raise ValueError("body_bindings_must_be_sorted")
        names = [name for name, _ in self.body_bindings]
        if len(names) != len(set(names)) or not set(names).issubset(_BODY_BINDING_FIELDS):
            raise ValueError("valid_unique_body_bindings_required")
        expected = {
            "client_order_id": self.client_order_id,
            "order_type": self.order_type,
            "quantity": self.quantity,
            "quote_quantity": self.quote_quantity,
            "reduce_only": self.reduce_only,
            "side": self.side,
            "symbol": self.symbol,
        }
        for field, pointer in self.body_bindings:
            observed = _json_pointer_value(parsed_body, pointer)
            matches = _binding_matches(field, observed, expected[field])
            if (
                self.body_requires_json_numbers
                and field in {"quantity", "quote_quantity"}
                and isinstance(observed, float)
                and math.isfinite(observed)
                and expected[field] is not None
            ):
                matches = Decimal(str(observed)) == Decimal(str(expected[field]))
            if expected[field] is None or not matches:
                raise ValueError(f"request_body_{field}_binding_mismatch")

    @classmethod
    def build(
        cls,
        *,
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
        hnc_receipt_id: str,
        auris_receipt_id: str,
        provider_receipt_ids: Collection[str],
        provider_moment_digest: str,
        provider_source_timestamp: str,
        body: Mapping[str, Any],
        body_bindings: Mapping[str, str] | None = None,
        parent_intent_digest: str | None = None,
        entry_receipt_id: str | None = None,
        position_side: str | None = None,
        observed_exposure_quantity: str | None = None,
        field_provider_receipt_ids: Collection[str] | None = None,
        field_provider_moment_digest: str | None = None,
        field_provider_source_timestamp: str | None = None,
        provider_position_id: str | None = None,
        body_requires_json_numbers: bool = False,
        decision_evidence: Mapping[str, Any] | None = None,
    ) -> EconomicIntent:
        return cls(
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
            parent_intent_digest=parent_intent_digest,
            entry_receipt_id=entry_receipt_id,
            position_side=position_side,
            observed_exposure_quantity=observed_exposure_quantity,
            hnc_receipt_id=hnc_receipt_id,
            auris_receipt_id=auris_receipt_id,
            provider_receipt_ids=_receipt_ids(provider_receipt_ids, "provider_receipt_ids"),
            provider_moment_digest=provider_moment_digest,
            provider_source_timestamp=provider_source_timestamp,
            body_json=(
                _canonical_transport_json(body)
                if body_requires_json_numbers
                else _canonical_json(body)
            ),
            body_bindings=tuple(sorted((body_bindings or {}).items())),
            field_provider_receipt_ids=(
                None
                if field_provider_receipt_ids is None
                else _receipt_ids(
                    field_provider_receipt_ids,
                    "field_provider_receipt_ids",
                )
            ),
            field_provider_moment_digest=field_provider_moment_digest,
            field_provider_source_timestamp=field_provider_source_timestamp,
            provider_position_id=provider_position_id,
            body_requires_json_numbers=body_requires_json_numbers,
            decision_evidence_json=(
                None
                if decision_evidence is None
                else _canonical_transport_json(decision_evidence)
            ),
        )

    @property
    def body_digest(self) -> str:
        return _sha256_text(self.body_json)

    def payload(self) -> dict[str, Any]:
        payload = {
            "schema": ECONOMIC_INTENT_SCHEMA,
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
            "hnc_receipt_id": self.hnc_receipt_id,
            "auris_receipt_id": self.auris_receipt_id,
            "provider_receipt_ids": list(self.provider_receipt_ids),
            "provider_moment_digest": self.provider_moment_digest,
            "provider_source_timestamp": self.provider_source_timestamp,
            "request_body": (
                self.body_json
                if self.body_requires_json_numbers
                else json.loads(self.body_json)
            ),
            "request_body_digest": self.body_digest,
            "body_bindings": dict(self.body_bindings),
            "provider_position_id": self.provider_position_id,
            "body_requires_json_numbers": self.body_requires_json_numbers,
        }
        field_moment = _field_provider_moment(
            self.field_provider_receipt_ids,
            self.field_provider_moment_digest,
            self.field_provider_source_timestamp,
        )
        if field_moment is not None:
            field_ids, field_digest, field_time = field_moment
            payload.update(
                {
                    "field_provider_receipt_ids": list(field_ids),
                    "field_provider_moment_digest": field_digest,
                    "field_provider_source_timestamp": field_time,
                }
            )
        if self.decision_evidence_json is not None:
            payload["decision_evidence_json"] = self.decision_evidence_json
        return payload

    @property
    def intent_digest(self) -> str:
        return _sha256_payload(self.payload())


@dataclass(frozen=True, slots=True)
class ContingencyWarrantScope:
    """Pre-approved maximum scope for one deterministic exposure reduction."""

    venue: str
    environment: str
    account_id_hash: str
    symbol: str
    exposure_side: str
    reduction_side: str
    method: str
    path: str
    order_type: str
    max_reduce_quantity: str
    entry_intent_digest: str
    entry_client_order_id: str
    containment_client_order_id: str
    authorization_receipt_id: str
    cycle_id: str
    pre_entry_position_receipt_id: str
    provider_reduce_only_supported: bool
    hnc_receipt_id: str
    auris_receipt_id: str
    provider_receipt_ids: tuple[str, ...]
    provider_moment_digest: str
    provider_source_timestamp: str
    field_provider_receipt_ids: tuple[str, ...] | None = None
    field_provider_moment_digest: str | None = None
    field_provider_source_timestamp: str | None = None
    decision_evidence_json: str | None = None

    def __post_init__(self) -> None:
        _lower(self.venue, "venue")
        _lower(self.environment, "environment")
        _digest(self.account_id_hash, "account_id_hash")
        _nonblank(self.symbol, "symbol")
        exposure = _upper(self.exposure_side, "exposure_side")
        reduction = _upper(self.reduction_side, "reduction_side")
        if (exposure, reduction) not in {("LONG", "SELL"), ("SHORT", "BUY")}:
            raise ValueError("reduction_side_must_reduce_exposure_side")
        _canonical_method(self.method)
        _canonical_path(self.path)
        _upper(self.order_type, "order_type")
        _canonical_decimal_text(
            self.max_reduce_quantity,
            "max_reduce_quantity",
            positive=True,
        )
        _digest(self.entry_intent_digest, "entry_intent_digest")
        _nonblank(self.entry_client_order_id, "entry_client_order_id")
        _nonblank(self.containment_client_order_id, "containment_client_order_id")
        if self.entry_client_order_id == self.containment_client_order_id:
            raise ValueError("distinct_entry_and_containment_client_ids_required")
        _nonblank(self.authorization_receipt_id, "authorization_receipt_id")
        _nonblank(self.cycle_id, "cycle_id")
        _nonblank(self.pre_entry_position_receipt_id, "pre_entry_position_receipt_id")
        if type(self.provider_reduce_only_supported) is not bool:
            raise ValueError("provider_reduce_only_supported_must_be_boolean")
        if not self.hnc_receipt_id.startswith("hnc:live_field:"):
            raise ValueError("live_hnc_receipt_required")
        if not self.auris_receipt_id.startswith("auris:cosmic_state:"):
            raise ValueError("live_auris_receipt_required")
        provider_ids = _receipt_ids(self.provider_receipt_ids, "provider_receipt_ids")
        if provider_ids != self.provider_receipt_ids:
            raise ValueError("provider_receipt_ids_must_be_sorted_unique")
        if self.pre_entry_position_receipt_id not in provider_ids:
            raise ValueError("pre_entry_position_receipt_must_be_in_provider_lineage")
        _digest(self.provider_moment_digest, "provider_moment_digest")
        _canonical_decimal_text(self.provider_source_timestamp, "provider_source_timestamp")
        _field_provider_moment(
            self.field_provider_receipt_ids,
            self.field_provider_moment_digest,
            self.field_provider_source_timestamp,
        )
        _validate_decision_evidence_json(self.decision_evidence_json)

    @classmethod
    def build(
        cls,
        *,
        venue: str,
        environment: str,
        account_id_hash: str,
        symbol: str,
        exposure_side: str,
        reduction_side: str,
        method: str,
        path: str,
        order_type: str,
        max_reduce_quantity: str,
        entry_intent_digest: str,
        entry_client_order_id: str,
        containment_client_order_id: str,
        authorization_receipt_id: str,
        cycle_id: str,
        pre_entry_position_receipt_id: str,
        provider_reduce_only_supported: bool,
        hnc_receipt_id: str,
        auris_receipt_id: str,
        provider_receipt_ids: Collection[str],
        provider_moment_digest: str,
        provider_source_timestamp: str,
        field_provider_receipt_ids: Collection[str] | None = None,
        field_provider_moment_digest: str | None = None,
        field_provider_source_timestamp: str | None = None,
        decision_evidence: Mapping[str, Any] | None = None,
    ) -> ContingencyWarrantScope:
        return cls(
            venue=venue,
            environment=environment,
            account_id_hash=account_id_hash,
            symbol=symbol,
            exposure_side=exposure_side,
            reduction_side=reduction_side,
            method=method,
            path=path,
            order_type=order_type,
            max_reduce_quantity=max_reduce_quantity,
            entry_intent_digest=entry_intent_digest,
            entry_client_order_id=entry_client_order_id,
            containment_client_order_id=containment_client_order_id,
            authorization_receipt_id=authorization_receipt_id,
            cycle_id=cycle_id,
            pre_entry_position_receipt_id=pre_entry_position_receipt_id,
            provider_reduce_only_supported=provider_reduce_only_supported,
            hnc_receipt_id=hnc_receipt_id,
            auris_receipt_id=auris_receipt_id,
            provider_receipt_ids=_receipt_ids(provider_receipt_ids, "provider_receipt_ids"),
            provider_moment_digest=provider_moment_digest,
            provider_source_timestamp=provider_source_timestamp,
            field_provider_receipt_ids=(
                None
                if field_provider_receipt_ids is None
                else _receipt_ids(
                    field_provider_receipt_ids,
                    "field_provider_receipt_ids",
                )
            ),
            field_provider_moment_digest=field_provider_moment_digest,
            field_provider_source_timestamp=field_provider_source_timestamp,
            decision_evidence_json=(
                None
                if decision_evidence is None
                else _canonical_transport_json(decision_evidence)
            ),
        )

    def payload(self) -> dict[str, Any]:
        payload = {
            "schema": CONTINGENCY_SCOPE_SCHEMA,
            "venue": self.venue,
            "environment": self.environment,
            "account_id_hash": self.account_id_hash,
            "symbol": self.symbol,
            "exposure_side": self.exposure_side,
            "reduction_side": self.reduction_side,
            "method": self.method,
            "path": self.path,
            "order_type": self.order_type,
            "max_reduce_quantity": self.max_reduce_quantity,
            "entry_intent_digest": self.entry_intent_digest,
            "entry_client_order_id": self.entry_client_order_id,
            "containment_client_order_id": self.containment_client_order_id,
            "authorization_receipt_id": self.authorization_receipt_id,
            "cycle_id": self.cycle_id,
            "pre_entry_position_receipt_id": self.pre_entry_position_receipt_id,
            "provider_reduce_only_supported": self.provider_reduce_only_supported,
            "hnc_receipt_id": self.hnc_receipt_id,
            "auris_receipt_id": self.auris_receipt_id,
            "provider_receipt_ids": list(self.provider_receipt_ids),
            "provider_moment_digest": self.provider_moment_digest,
            "provider_source_timestamp": self.provider_source_timestamp,
        }
        field_moment = _field_provider_moment(
            self.field_provider_receipt_ids,
            self.field_provider_moment_digest,
            self.field_provider_source_timestamp,
        )
        if field_moment is not None:
            field_ids, field_digest, field_time = field_moment
            payload.update(
                {
                    "field_provider_receipt_ids": list(field_ids),
                    "field_provider_moment_digest": field_digest,
                    "field_provider_source_timestamp": field_time,
                }
            )
        if self.decision_evidence_json is not None:
            payload["decision_evidence_json"] = self.decision_evidence_json
        return payload

    @property
    def scope_digest(self) -> str:
        return _sha256_payload(self.payload())


@dataclass(frozen=True, slots=True)
class EconomicMutationPermit:
    """Opaque evidence that has no effect until its issuing boundary consumes it."""

    schema: str
    permit_id: str
    boundary_id: str
    permit_kind: str
    intent_digest: str
    method: str
    path: str
    body_digest: str
    provider_moment_digest: str
    hnc_receipt_id: str
    auris_receipt_id: str
    authorization_receipt_id: str
    cycle_id: str
    position_receipt_id: str
    dual_receipt_id: str
    proposal_digest: str
    context_digest: str
    issued_at: str
    expires_at: str
    contingency_warrant_id: str | None
    route_authorization_required: bool = True
    economic_mutation: bool = False
    action_eligible: bool = False


@dataclass(frozen=True, slots=True)
class ContingencyWarrant:
    """Registry-backed dual-voice evidence; never a transport capability itself."""

    schema: str
    warrant_id: str
    boundary_id: str
    scope_digest: str
    scope_json: str
    dual_receipt_id: str
    dual_receipt_json: str
    proposal_digest: str
    issued_at: str
    expires_at: str
    route_authorization_required: bool = True
    economic_mutation: bool = False
    action_eligible: bool = False


@dataclass(frozen=True, slots=True)
class TrustedContingencyRecoveryClaim:
    """One durable, adapter-issued claim over an exact persisted warrant."""

    adapter_id: str
    record_digest: str
    claim_id: str
    claimed_at: str
    expires_at: str
    warrant: ContingencyWarrant
    scope: ContingencyWarrantScope
    _boundary_capability: object = dataclass_field(
        repr=False,
        compare=False,
    )
    _seal: object = dataclass_field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._seal is not _RECOVERY_CLAIM_TOKEN:
            raise TypeError("trusted_recovery_adapter_claim_required")


def _issue_trusted_contingency_recovery_claim(
    *,
    adapter_id: str,
    record_digest: str,
    claim_id: str,
    claimed_at: str,
    expires_at: str,
    warrant: ContingencyWarrant,
    scope: ContingencyWarrantScope,
    boundary_capability: object,
) -> TrustedContingencyRecoveryClaim:
    """Internal constructor used only by the allowlisted durable adapter."""

    return TrustedContingencyRecoveryClaim(
        adapter_id=adapter_id,
        record_digest=record_digest,
        claim_id=claim_id,
        claimed_at=claimed_at,
        expires_at=expires_at,
        warrant=warrant,
        scope=scope,
        _boundary_capability=boundary_capability,
        _seal=_RECOVERY_CLAIM_TOKEN,
    )


@dataclass(slots=True)
class _PermitState:
    permit: EconomicMutationPermit
    body_json: str
    context_digest: str
    provider_source_timestamp: Decimal
    body_requires_json_numbers: bool


@dataclass(frozen=True, slots=True)
class _TransportContextState:
    context_id: str
    permit_id: str
    boundary_id: str
    method: str
    path: str
    body_json: str
    body_digest: str
    body_requires_json_numbers: bool


_TRANSPORT_CONTEXT_LOCK = threading.RLock()
_TRANSPORT_CONTEXTS: dict[str, _TransportContextState] = {}


def _economic_transport_body_digest(body: Mapping[str, Any]) -> str:
    """Return the exact digest used by permits and provider transport guards."""

    return _sha256_text(_canonical_json(body))


def _capital_economic_transport_body_digest(body: Mapping[str, Any]) -> str:
    """Capital-only digest for its provider-required numeric JSON fields."""

    return _sha256_text(_canonical_transport_json(body))


def _install_economic_transport_context(
    permit: EconomicMutationPermit,
    *,
    body_json: str,
    body_requires_json_numbers: bool = False,
) -> tuple[contextvars.Token[str | None], str]:
    """Install a private one-use context for the synchronous transport call."""

    context_id = f"economic-transport:{secrets.token_hex(24)}"
    state = _TransportContextState(
        context_id=context_id,
        permit_id=permit.permit_id,
        boundary_id=permit.boundary_id,
        method=permit.method,
        path=permit.path,
        body_json=body_json,
        body_digest=permit.body_digest,
        body_requires_json_numbers=body_requires_json_numbers,
    )
    with _TRANSPORT_CONTEXT_LOCK:
        _TRANSPORT_CONTEXTS[context_id] = state
    return _TRANSPORT_CONTEXT.set(context_id), context_id


def _clear_economic_transport_context(
    token: contextvars.Token[str | None],
    context_id: str,
) -> None:
    """Remove an unused context and restore any enclosing dispatch context."""

    with _TRANSPORT_CONTEXT_LOCK:
        _TRANSPORT_CONTEXTS.pop(context_id, None)
    _TRANSPORT_CONTEXT.reset(token)


def _claim_economic_transport_context(
    *,
    method: str,
    path: str,
    body: Mapping[str, Any],
) -> str:
    """Burn and verify the boundary-issued context at a provider client seam."""

    context_id = _TRANSPORT_CONTEXT.get()
    if context_id is None:
        raise EconomicGovernanceBlocked(
            "boundary_issued_economic_transport_context_required"
        )
    with _TRANSPORT_CONTEXT_LOCK:
        state = _TRANSPORT_CONTEXTS.pop(context_id, None)
    if state is None:
        raise EconomicGovernanceBlocked(
            "unknown_consumed_or_replayed_economic_transport_context"
        )
    if state.body_requires_json_numbers:
        raise EconomicGovernanceBlocked(
            "generic_transport_cannot_consume_capital_numeric_body_context"
        )
    try:
        canonical_method = _canonical_method(method)
        canonical_path = _canonical_path(path)
        body_json = _canonical_json(body)
    except (TypeError, ValueError) as exc:
        raise EconomicGovernanceBlocked(
            "exact_economic_transport_method_path_body_required"
        ) from exc
    body_digest = _sha256_text(body_json)
    if (
        canonical_method != state.method
        or canonical_path != state.path
        or body_json != state.body_json
        or body_digest != state.body_digest
    ):
        raise EconomicGovernanceBlocked(
            "exact_economic_transport_method_path_body_required"
        )
    return body_digest


def _claim_capital_economic_transport_context(
    *,
    method: str,
    path: str,
    body: Mapping[str, Any],
) -> str:
    """Burn a Capital-only context whose numeric JSON body is permit-bound."""

    context_id = _TRANSPORT_CONTEXT.get()
    if context_id is None:
        raise EconomicGovernanceBlocked(
            "boundary_issued_economic_transport_context_required"
        )
    with _TRANSPORT_CONTEXT_LOCK:
        state = _TRANSPORT_CONTEXTS.pop(context_id, None)
    if state is None:
        raise EconomicGovernanceBlocked(
            "unknown_consumed_or_replayed_economic_transport_context"
        )
    try:
        canonical_method = _canonical_method(method)
        canonical_path = _canonical_path(path)
        body_json = (
            _canonical_transport_json(body)
            if state.body_requires_json_numbers
            else _canonical_json(body)
        )
    except (TypeError, ValueError) as exc:
        raise EconomicGovernanceBlocked(
            "exact_capital_transport_method_path_body_required"
        ) from exc
    body_digest = _sha256_text(body_json)
    if (
        canonical_method != state.method
        or canonical_path != state.path
        or body_json != state.body_json
        or body_digest != state.body_digest
    ):
        raise EconomicGovernanceBlocked(
            "exact_capital_transport_method_path_body_required"
        )
    return body_digest


@dataclass(slots=True)
class _WarrantState:
    warrant: ContingencyWarrant
    scope: ContingencyWarrantScope
    consumed: bool = False


def _supplier_allowlist(values: Collection[str], name: str) -> frozenset[str]:
    if not isinstance(values, frozenset) or not values:
        raise ValueError(f"{name}_must_be_nonempty_frozenset")
    normalized = frozenset(_nonblank(value, name).casefold() for value in values)
    if len(normalized) != len(values):
        raise ValueError(f"{name}_must_be_case_distinct")
    return normalized


def _clock_decimal(clock: Callable[[], float]) -> Decimal:
    value = clock()
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("clock_must_return_finite_number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("clock_must_return_finite_number")
    return Decimal(str(number))


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if Decimal(text) == 0 else text


class EconomicGovernanceBoundary:
    """Composition-root capability that mints and atomically consumes permits."""

    def __init__(
        self,
        *,
        _factory_token: object,
        council_supplier: TrustedCouncilReceiptSupplier,
        crown_supplier: TrustedCrownReceiptSupplier,
        clock: Callable[[], float],
        permit_ttl: Decimal,
        warrant_ttl: Decimal,
        provider_max_age: Decimal,
        governance_max_age_s: float,
    ) -> None:
        if _factory_token is not _BOUNDARY_FACTORY_TOKEN:
            raise TypeError("use_bind_economic_governance_boundary")
        self._council_supplier = council_supplier
        self._crown_supplier = crown_supplier
        self._clock = clock
        self._permit_ttl = permit_ttl
        self._warrant_ttl = warrant_ttl
        self._provider_max_age = provider_max_age
        self._governance_max_age_s = governance_max_age_s
        self._boundary_id = f"economic-boundary:{secrets.token_hex(16)}"
        self._recovery_capability = object()
        self._permits: dict[str, _PermitState] = {}
        self._warrants: dict[str, _WarrantState] = {}
        self._consumed_recovery_claim_ids: set[str] = set()
        self._lock = threading.RLock()

    def _now(self) -> Decimal:
        return _clock_decimal(self._clock)

    def _context_digest(self) -> str:
        nonce = _EXECUTION_CONTEXT.get()
        if nonce is None:
            nonce = secrets.token_hex(16)
            _EXECUTION_CONTEXT.set(nonce)
        try:
            task = asyncio.current_task()
        except RuntimeError:
            task = None
        material = {
            "boundary_id": self._boundary_id,
            "context_nonce": nonce,
            "task_id": None if task is None else id(task),
            "thread_id": threading.get_ident(),
        }
        return _sha256_payload(material)

    def _require_fresh_provider_timestamp(self, source: str, now: Decimal) -> None:
        timestamp = Decimal(_canonical_decimal_text(source, "provider_source_timestamp"))
        if timestamp > now + _FUTURE_SKEW_S or now - timestamp > self._provider_max_age:
            raise EconomicGovernanceBlocked("fresh_target_provider_moment_required")

    def _proposal(
        self,
        *,
        proposal_kind: str,
        payload: Mapping[str, Any],
    ) -> tuple[str, str, tuple[Mapping[str, Any], ...], Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]]:
        if proposal_kind == "economic_mutation":
            prompt = "Should the exact route-bound economic mutation be permitted?"
            answer = "Require independent Council and Crown ACCEPT before one last-mile consume."
            tool_name = "economic_boundary.prepare_mutation"
        else:
            prompt = "Should this exact deterministic contingency reduction scope be retained?"
            answer = "Approve evidence only; the warrant cannot mutate until exact reduction consume."
            tool_name = "economic_boundary.approve_contingency_warrant"
        tool_calls: tuple[Mapping[str, Any], ...] = (
            {
                "tool": tool_name,
                "arguments": {proposal_kind: dict(payload)},
                "blocked": False,
            },
        )
        capability = {
            "family": "safe_trading_cognition",
            "route_authorization_required": True,
            "economic_boundary": "one_use_exact_transport_binding",
        }
        bake = {
            "complete": True,
            "voices_required": ["druid_council", "queen_chief"],
        }
        acquisition = {
            "intent_or_scope_digest": _sha256_payload(payload),
            "authorization_receipt_id": payload["authorization_receipt_id"],
            "cycle_id": payload["cycle_id"],
            "position_receipt_id": payload.get(
                "position_receipt_id",
                payload.get("pre_entry_position_receipt_id"),
            ),
            "hnc_receipt_id": payload["hnc_receipt_id"],
            "auris_receipt_id": payload["auris_receipt_id"],
            "provider_receipt_ids": payload["provider_receipt_ids"],
            "provider_moment_digest": payload["provider_moment_digest"],
            "provider_source_timestamp": payload["provider_source_timestamp"],
        }
        if "field_provider_receipt_ids" in payload:
            acquisition.update(
                {
                    "field_provider_receipt_ids": payload[
                        "field_provider_receipt_ids"
                    ],
                    "field_provider_moment_digest": payload[
                        "field_provider_moment_digest"
                    ],
                    "field_provider_source_timestamp": payload[
                        "field_provider_source_timestamp"
                    ],
                }
            )
        return prompt, answer, tool_calls, capability, bake, acquisition

    def _strict_dual_accept(
        self,
        *,
        proposal_kind: str,
        payload: Mapping[str, Any],
        hnc_receipt_id: str,
        auris_receipt_id: str,
        now: Decimal,
    ) -> tuple[dict[str, Any], CognitionGovernanceRequest]:
        expected_provider_ids = _receipt_ids(
            payload["provider_receipt_ids"],
            "provider_receipt_ids",
        )
        expected_provider_digest = _digest(
            payload["provider_moment_digest"],
            "provider_moment_digest",
        )
        expected_provider_source_timestamp = _canonical_decimal_text(
            payload["provider_source_timestamp"],
            "provider_source_timestamp",
        )
        explicit_field_moment = _field_provider_moment(
            payload.get("field_provider_receipt_ids"),
            payload.get("field_provider_moment_digest"),
            payload.get("field_provider_source_timestamp"),
        )
        if explicit_field_moment is None:
            expected_field_ids = expected_provider_ids
            expected_field_digest = expected_provider_digest
            expected_field_source_timestamp = expected_provider_source_timestamp
        else:
            (
                expected_field_ids,
                expected_field_digest,
                expected_field_source_timestamp,
            ) = explicit_field_moment
        prompt, answer, tool_calls, capability, bake, acquisition = self._proposal(
            proposal_kind=proposal_kind,
            payload=payload,
        )
        expected = build_cognition_governance_request(
            prompt=prompt,
            answer=answer,
            tool_calls=tool_calls,
            capability=capability,
            bake=bake,
            acquisition=acquisition,
            queen_verdict="APPROVED",
        )
        if (
            expected.target_provider_receipt_ids != expected_provider_ids
            or expected.target_provider_moment_digest != expected_provider_digest
            or expected.target_provider_source_timestamp
            != expected_provider_source_timestamp
            or expected.provider_receipt_ids != expected_field_ids
            or expected.provider_moment_digest != expected_field_digest
            or expected.provider_source_timestamp
            != expected_field_source_timestamp
        ):
            raise EconomicGovernanceBlocked(
                "immutable_request_provider_moment_required"
            )
        raw = evaluate_cognition_governance(
            prompt=prompt,
            answer=answer,
            queen_verdict="APPROVED",
            queen_evaluated=True,
            council_receipt_supplier=self._council_supplier,
            crown_receipt_supplier=self._crown_supplier,
            tool_calls=tool_calls,
            capability=capability,
            bake=bake,
            acquisition=acquisition,
            now=float(now),
            max_age_s=self._governance_max_age_s,
        )
        try:
            dual = validate_dual_key_receipt(
                raw,
                now=float(now),
                max_age_s=self._governance_max_age_s,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise EconomicGovernanceBlocked("complete_fresh_strict_dual_accept_required") from exc
        if (
            dual["decision"] != "ACCEPT"
            or dual["harmonic_outcome"] != "CONSTRUCTIVE"
            or dual["proposal_digest"] != expected.proposal_digest
            or dual["prompt_digest"] != expected.prompt_digest
            or dual["hnc_receipt_id"] != hnc_receipt_id
            or dual["auris_receipt_id"] != auris_receipt_id
            or tuple(dual["provider_receipt_ids"]) != expected_field_ids
            or dual["provider_moment_digest"] != expected_field_digest
            or dual["provider_source_timestamp"]
            != expected_field_source_timestamp
        ):
            raise EconomicGovernanceBlocked("exact_council_crown_accept_required")
        return dual, expected

    def _register_permit(
        self,
        *,
        intent: EconomicIntent,
        dual_receipt_id: str,
        proposal_digest: str,
        permit_kind: str,
        contingency_warrant_id: str | None,
        now: Decimal,
    ) -> EconomicMutationPermit:
        self._require_fresh_provider_timestamp(intent.provider_source_timestamp, now)
        context_digest = self._context_digest()
        permit = EconomicMutationPermit(
            schema=ECONOMIC_PERMIT_SCHEMA,
            permit_id=f"economic-permit:{secrets.token_hex(24)}",
            boundary_id=self._boundary_id,
            permit_kind=permit_kind,
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
            dual_receipt_id=dual_receipt_id,
            proposal_digest=proposal_digest,
            context_digest=context_digest,
            issued_at=_decimal_text(now),
            expires_at=_decimal_text(now + self._permit_ttl),
            contingency_warrant_id=contingency_warrant_id,
        )
        with self._lock:
            self._permits[permit.permit_id] = _PermitState(
                permit=permit,
                body_json=intent.body_json,
                context_digest=context_digest,
                provider_source_timestamp=Decimal(intent.provider_source_timestamp),
                body_requires_json_numbers=intent.body_requires_json_numbers,
            )
        return permit

    def prepare_mutation(self, intent: EconomicIntent) -> EconomicMutationPermit:
        """Obtain two fresh voices and mint evidence for this exact mutation."""

        if not isinstance(intent, EconomicIntent):
            raise TypeError("economic_intent_required")
        now = self._now()
        self._require_fresh_provider_timestamp(intent.provider_source_timestamp, now)
        dual, request = self._strict_dual_accept(
            proposal_kind="economic_mutation",
            payload=intent.payload(),
            hnc_receipt_id=intent.hnc_receipt_id,
            auris_receipt_id=intent.auris_receipt_id,
            now=now,
        )
        issue_time = self._now()
        return self._register_permit(
            intent=intent,
            dual_receipt_id=dual["receipt_id"],
            proposal_digest=request.proposal_digest,
            permit_kind="fresh_dual_accept",
            contingency_warrant_id=None,
            now=issue_time,
        )

    def approve_contingency_warrant(
        self,
        scope: ContingencyWarrantScope,
    ) -> ContingencyWarrant:
        """Ask both voices to retain one bounded reduction scope as evidence."""

        if not isinstance(scope, ContingencyWarrantScope):
            raise TypeError("contingency_warrant_scope_required")
        now = self._now()
        self._require_fresh_provider_timestamp(scope.provider_source_timestamp, now)
        dual, request = self._strict_dual_accept(
            proposal_kind="contingency_warrant",
            payload=scope.payload(),
            hnc_receipt_id=scope.hnc_receipt_id,
            auris_receipt_id=scope.auris_receipt_id,
            now=now,
        )
        issue_time = self._now()
        scope_json = _canonical_json(scope.payload())
        warrant = ContingencyWarrant(
            schema=CONTINGENCY_WARRANT_SCHEMA,
            warrant_id=f"economic-contingency:{secrets.token_hex(24)}",
            boundary_id=self._boundary_id,
            scope_digest=scope.scope_digest,
            scope_json=scope_json,
            dual_receipt_id=dual["receipt_id"],
            dual_receipt_json=_canonical_receipt_json(dual),
            proposal_digest=request.proposal_digest,
            issued_at=_decimal_text(issue_time),
            expires_at=_decimal_text(issue_time + self._warrant_ttl),
        )
        with self._lock:
            self._warrants[warrant.warrant_id] = _WarrantState(
                warrant=warrant,
                scope=scope,
            )
        return warrant

    def _validate_recovered_warrant(
        self,
        warrant: ContingencyWarrant,
        scope: ContingencyWarrantScope,
        *,
        now: Decimal,
    ) -> None:
        if (
            not isinstance(warrant, ContingencyWarrant)
            or not isinstance(scope, ContingencyWarrantScope)
            or warrant.schema != CONTINGENCY_WARRANT_SCHEMA
            or warrant.scope_digest != scope.scope_digest
            or warrant.scope_json != _canonical_json(scope.payload())
        ):
            raise EconomicGovernanceBlocked(
                "complete_untampered_durable_warrant_required"
            )
        _nonblank(warrant.warrant_id, "warrant_id")
        _nonblank(warrant.boundary_id, "origin_boundary_id")
        _nonblank(warrant.dual_receipt_id, "dual_receipt_id")
        _digest(warrant.proposal_digest, "proposal_digest")
        issued = Decimal(
            _canonical_decimal_text(warrant.issued_at, "issued_at")
        )
        expires = Decimal(
            _canonical_decimal_text(warrant.expires_at, "expires_at")
        )
        if issued > expires or now > expires:
            raise EconomicGovernanceBlocked("contingency_warrant_expired")
        try:
            raw_dual = json.loads(warrant.dual_receipt_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise EconomicGovernanceBlocked(
                "complete_untampered_durable_warrant_required"
            ) from exc
        if (
            not isinstance(raw_dual, Mapping)
            or _canonical_receipt_json(raw_dual)
            != warrant.dual_receipt_json
        ):
            raise EconomicGovernanceBlocked(
                "complete_untampered_durable_warrant_required"
            )
        try:
            dual = validate_dual_key_receipt(
                raw_dual,
                now=float(issued),
                max_age_s=self._governance_max_age_s,
            )
            prompt, answer, tool_calls, capability, bake, acquisition = (
                self._proposal(
                    proposal_kind="contingency_warrant",
                    payload=scope.payload(),
                )
            )
            expected = build_cognition_governance_request(
                prompt=prompt,
                answer=answer,
                tool_calls=tool_calls,
                capability=capability,
                bake=bake,
                acquisition=acquisition,
                queen_verdict="APPROVED",
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise EconomicGovernanceBlocked(
                "complete_untampered_durable_warrant_required"
            ) from exc
        if (
            dual["decision"] != "ACCEPT"
            or dual["harmonic_outcome"] != "CONSTRUCTIVE"
            or dual["receipt_id"] != warrant.dual_receipt_id
            or dual["proposal_digest"] != warrant.proposal_digest
            or dual["proposal_digest"] != expected.proposal_digest
            or dual["prompt_digest"] != expected.prompt_digest
            or dual["hnc_receipt_id"] != scope.hnc_receipt_id
            or dual["auris_receipt_id"] != scope.auris_receipt_id
            or tuple(dual["provider_receipt_ids"])
            != expected.provider_receipt_ids
            or dual["provider_moment_digest"]
            != expected.provider_moment_digest
            or dual["provider_source_timestamp"]
            != expected.provider_source_timestamp
            or expected.target_provider_receipt_ids
            != scope.provider_receipt_ids
            or expected.target_provider_moment_digest
            != scope.provider_moment_digest
            or expected.target_provider_source_timestamp
            != scope.provider_source_timestamp
        ):
            raise EconomicGovernanceBlocked(
                "exact_persisted_council_crown_accept_required"
            )

    @staticmethod
    def _validate_contingency_reduction(
        scope: ContingencyWarrantScope,
        intent: EconomicIntent,
    ) -> None:
        capital_deal_close = (
            scope.venue == "capital"
            and scope.method == "DELETE"
            and scope.path == "/positions/{provider_deal_id}"
            and scope.order_type == "MARKET_CLOSE_BY_DEAL"
        )
        exact_pairs = (
            (intent.venue, scope.venue),
            (intent.environment, scope.environment),
            (intent.account_id_hash, scope.account_id_hash),
            (intent.symbol, scope.symbol),
            (intent.side, scope.reduction_side),
            (intent.position_side, scope.exposure_side),
            (intent.method, scope.method),
            (intent.order_type, scope.order_type),
            (intent.client_order_id, scope.containment_client_order_id),
            (intent.authorization_receipt_id, scope.authorization_receipt_id),
            (intent.cycle_id, scope.cycle_id),
            (intent.parent_intent_digest, scope.entry_intent_digest),
            (intent.hnc_receipt_id, scope.hnc_receipt_id),
            (intent.auris_receipt_id, scope.auris_receipt_id),
        )
        if any(actual != expected for actual, expected in exact_pairs):
            raise EconomicGovernanceBlocked("contingency_scope_lineage_mismatch")
        if capital_deal_close:
            provider_position_id = intent.provider_position_id
            if (
                provider_position_id is None
                or intent.path != f"/positions/{provider_position_id}"
                or intent.body_json != "{}"
                or intent.body_bindings
            ):
                raise EconomicGovernanceBlocked(
                    "exact_capital_provider_deal_close_required"
                )
        elif intent.path != scope.path:
            raise EconomicGovernanceBlocked("contingency_scope_lineage_mismatch")
        if intent.purpose != _CONTAINMENT_PURPOSE or intent.operation != _CONTAINMENT_OPERATION:
            raise EconomicGovernanceBlocked("containment_reduction_intent_required")
        if (
            intent.reduce_only is not True
            or intent.quantity is None
            or intent.quote_quantity is not None
            or intent.limit_price is not None
            or intent.stop_price is not None
            or intent.take_profit is not None
            or intent.observed_exposure_quantity is None
            or intent.entry_receipt_id is None
        ):
            raise EconomicGovernanceBlocked("deterministic_quantity_only_reduction_required")
        quantity = Decimal(intent.quantity)
        observed = Decimal(intent.observed_exposure_quantity)
        if quantity > Decimal(scope.max_reduce_quantity) or quantity > observed:
            raise EconomicGovernanceBlocked("containment_quantity_exceeds_observed_or_warranted_exposure")
        if intent.position_receipt_id == scope.pre_entry_position_receipt_id:
            raise EconomicGovernanceBlocked("fresh_post_entry_position_receipt_required")
        if intent.entry_receipt_id not in intent.provider_receipt_ids:
            raise EconomicGovernanceBlocked("entry_receipt_must_be_in_current_provider_lineage")
        if not capital_deal_close:
            binding_names = {name for name, _ in intent.body_bindings}
            if not {"quantity", "side"}.issubset(binding_names):
                raise EconomicGovernanceBlocked("containment_body_side_and_quantity_bindings_required")
            if scope.provider_reduce_only_supported and "reduce_only" not in binding_names:
                raise EconomicGovernanceBlocked("provider_reduce_only_body_binding_required")

    def prepare_contingency_reduction(
        self,
        warrant: ContingencyWarrant,
        intent: EconomicIntent,
    ) -> EconomicMutationPermit:
        """Mint one permit only for an exact, fresh, deterministic reduction."""

        if not isinstance(warrant, ContingencyWarrant):
            raise TypeError("contingency_warrant_required")
        if not isinstance(intent, EconomicIntent):
            raise TypeError("economic_intent_required")
        now = self._now()
        self._require_fresh_provider_timestamp(intent.provider_source_timestamp, now)
        with self._lock:
            state = self._warrants.get(warrant.warrant_id)
            if state is None or state.warrant != warrant:
                raise EconomicGovernanceBlocked("unknown_or_tampered_contingency_warrant")
            if state.consumed:
                raise EconomicGovernanceBlocked("contingency_warrant_already_used")
            if now > Decimal(warrant.expires_at):
                raise EconomicGovernanceBlocked("contingency_warrant_expired")
            self._validate_contingency_reduction(state.scope, intent)
            state.consumed = True
            return self._register_permit(
                intent=intent,
                dual_receipt_id=warrant.dual_receipt_id,
                proposal_digest=warrant.proposal_digest,
                permit_kind="contingency_reduction",
                contingency_warrant_id=warrant.warrant_id,
                now=now,
            )

    def prepare_recovered_contingency_reduction(
        self,
        claim: TrustedContingencyRecoveryClaim,
        intent: EconomicIntent,
    ) -> EconomicMutationPermit:
        """Mint from one allowlisted durable claim without reopening voices."""

        if not isinstance(claim, TrustedContingencyRecoveryClaim):
            raise TypeError("trusted_recovery_adapter_claim_required")
        if not isinstance(intent, EconomicIntent):
            raise TypeError("economic_intent_required")
        if claim._boundary_capability is not self._recovery_capability:
            raise EconomicGovernanceBlocked("cross_boundary_recovery_claim")
        _nonblank(claim.adapter_id, "recovery_adapter_id")
        _digest(claim.record_digest, "recovery_record_digest")
        _nonblank(claim.claim_id, "recovery_claim_id")
        now = self._now()
        claimed = Decimal(
            _canonical_decimal_text(claim.claimed_at, "claim_claimed_at")
        )
        claim_expires = Decimal(
            _canonical_decimal_text(claim.expires_at, "claim_expires_at")
        )
        if claimed > claim_expires or now > claim_expires:
            raise EconomicGovernanceBlocked(
                "durable_recovery_claim_expired"
            )
        self._require_fresh_provider_timestamp(
            intent.provider_source_timestamp,
            now,
        )
        with self._lock:
            if claim.claim_id in self._consumed_recovery_claim_ids:
                raise EconomicGovernanceBlocked(
                    "durable_recovery_claim_already_consumed"
                )
            self._validate_recovered_warrant(
                claim.warrant,
                claim.scope,
                now=now,
            )
            self._validate_contingency_reduction(claim.scope, intent)
            self._consumed_recovery_claim_ids.add(claim.claim_id)
            return self._register_permit(
                intent=intent,
                dual_receipt_id=claim.warrant.dual_receipt_id,
                proposal_digest=claim.warrant.proposal_digest,
                permit_kind="durable_contingency_reduction",
                contingency_warrant_id=claim.warrant.warrant_id,
                now=now,
            )

    def consume_capital_and_call(
        self,
        permit: EconomicMutationPermit,
        *,
        method: str,
        path: str,
        body: Mapping[str, Any],
        transport: Callable[[], _T],
    ) -> _T:
        """Burn one Capital-only numeric-body permit and invoke transport once."""

        if not isinstance(permit, EconomicMutationPermit):
            raise TypeError("economic_mutation_permit_required")
        if not callable(transport):
            raise TypeError("transport_callable_required")
        canonical_method = _canonical_method(method)
        canonical_path = _canonical_path(path)
        body_json = _canonical_transport_json(body)
        with self._lock:
            state = self._permits.pop(permit.permit_id, None)
            if state is None:
                raise EconomicGovernanceBlocked("unknown_consumed_or_replayed_permit")
            now = self._now()
            if state.permit != permit or permit.boundary_id != self._boundary_id:
                raise EconomicGovernanceBlocked("tampered_or_cross_boundary_permit")
            if not state.body_requires_json_numbers:
                raise EconomicGovernanceBlocked("capital_numeric_body_permit_required")
            if state.context_digest != self._context_digest():
                raise EconomicGovernanceBlocked("permit_execution_context_mismatch")
            if now > Decimal(permit.expires_at):
                raise EconomicGovernanceBlocked("economic_mutation_permit_expired")
            self._require_fresh_provider_timestamp(
                _decimal_text(state.provider_source_timestamp),
                now,
            )
            if (
                canonical_method != permit.method
                or canonical_path != permit.path
                or body_json != state.body_json
                or _sha256_text(body_json) != permit.body_digest
            ):
                raise EconomicGovernanceBlocked("exact_method_path_body_binding_required")
        transport_token, transport_context_id = _install_economic_transport_context(
            permit,
            body_json=body_json,
            body_requires_json_numbers=True,
        )
        try:
            return transport()
        finally:
            _clear_economic_transport_context(
                transport_token,
                transport_context_id,
            )

    def consume_and_call(
        self,
        permit: EconomicMutationPermit,
        *,
        method: str,
        path: str,
        body: Mapping[str, Any],
        transport: Callable[[], _T],
    ) -> _T:
        """Atomically burn a matching permit, then invoke the raw transport once."""

        if not isinstance(permit, EconomicMutationPermit):
            raise TypeError("economic_mutation_permit_required")
        if not callable(transport):
            raise TypeError("transport_callable_required")
        canonical_method = _canonical_method(method)
        canonical_path = _canonical_path(path)
        body_json = _canonical_json(body)
        with self._lock:
            state = self._permits.pop(permit.permit_id, None)
            if state is None:
                raise EconomicGovernanceBlocked("unknown_consumed_or_replayed_permit")
            now = self._now()
            if state.permit != permit or permit.boundary_id != self._boundary_id:
                raise EconomicGovernanceBlocked("tampered_or_cross_boundary_permit")
            if state.body_requires_json_numbers:
                raise EconomicGovernanceBlocked(
                    "capital_numeric_body_requires_capital_consumer"
                )
            if state.context_digest != self._context_digest():
                raise EconomicGovernanceBlocked("permit_execution_context_mismatch")
            if now > Decimal(permit.expires_at):
                raise EconomicGovernanceBlocked("economic_mutation_permit_expired")
            self._require_fresh_provider_timestamp(
                _decimal_text(state.provider_source_timestamp),
                now,
            )
            if (
                canonical_method != permit.method
                or canonical_path != permit.path
                or body_json != state.body_json
                or _sha256_text(body_json) != permit.body_digest
            ):
                raise EconomicGovernanceBlocked("exact_method_path_body_binding_required")
        transport_token, transport_context_id = (
            _install_economic_transport_context(
                permit,
                body_json=body_json,
            )
        )
        try:
            return transport()
        finally:
            _clear_economic_transport_context(
                transport_token,
                transport_context_id,
            )


def bind_economic_governance_boundary(
    *,
    council_receipt_supplier: TrustedCouncilReceiptSupplier,
    crown_receipt_supplier: TrustedCrownReceiptSupplier,
    trusted_council_supplier_ids: frozenset[str],
    trusted_crown_supplier_ids: frozenset[str],
    clock: Callable[[], float] = time.time,
    permit_ttl_s: float = 2.0,
    warrant_ttl_s: float = 86_400.0,
    provider_max_age_s: float = DEFAULT_MAX_AGE_S,
    governance_max_age_s: float = DEFAULT_MAX_AGE_S,
) -> EconomicGovernanceBoundary:
    """Bind allowlisted independent suppliers once at the composition root."""

    if not isinstance(council_receipt_supplier, TrustedCouncilReceiptSupplier):
        raise TypeError("trusted_council_receipt_supplier_required")
    if not isinstance(crown_receipt_supplier, TrustedCrownReceiptSupplier):
        raise TypeError("trusted_crown_receipt_supplier_required")
    if council_receipt_supplier is crown_receipt_supplier:
        raise ValueError("independent_council_and_crown_suppliers_required")
    council_allowlist = _supplier_allowlist(
        trusted_council_supplier_ids,
        "trusted_council_supplier_ids",
    )
    crown_allowlist = _supplier_allowlist(
        trusted_crown_supplier_ids,
        "trusted_crown_supplier_ids",
    )
    if council_allowlist.intersection(crown_allowlist):
        raise ValueError("supplier_allowlists_must_be_disjoint")
    council_id = _nonblank(council_receipt_supplier.supplier_id, "council_supplier_id")
    crown_id = _nonblank(crown_receipt_supplier.supplier_id, "crown_supplier_id")
    if council_id.casefold() not in council_allowlist:
        raise ValueError("council_supplier_not_allowlisted")
    if crown_id.casefold() not in crown_allowlist:
        raise ValueError("crown_supplier_not_allowlisted")
    if council_id.casefold() == crown_id.casefold():
        raise ValueError("independent_council_and_crown_suppliers_required")
    if not callable(clock):
        raise TypeError("clock_callable_required")
    permit_ttl = Decimal(str(permit_ttl_s))
    warrant_ttl = Decimal(str(warrant_ttl_s))
    provider_max_age = Decimal(str(provider_max_age_s))
    if not all(value.is_finite() and value > 0 for value in (permit_ttl, warrant_ttl, provider_max_age)):
        raise ValueError("positive_finite_boundary_ttl_required")
    if (
        isinstance(governance_max_age_s, bool)
        or not isinstance(governance_max_age_s, (int, float))
        or not math.isfinite(float(governance_max_age_s))
        or governance_max_age_s <= 0
    ):
        raise ValueError("positive_finite_governance_max_age_required")
    return EconomicGovernanceBoundary(
        _factory_token=_BOUNDARY_FACTORY_TOKEN,
        council_supplier=council_receipt_supplier,
        crown_supplier=crown_receipt_supplier,
        clock=clock,
        permit_ttl=permit_ttl,
        warrant_ttl=warrant_ttl,
        provider_max_age=provider_max_age,
        governance_max_age_s=float(governance_max_age_s),
    )


__all__ = [
    "CONTINGENCY_SCOPE_SCHEMA",
    "CONTINGENCY_WARRANT_SCHEMA",
    "ECONOMIC_INTENT_SCHEMA",
    "ECONOMIC_PERMIT_SCHEMA",
    "ContingencyWarrant",
    "ContingencyWarrantScope",
    "EconomicGovernanceBlocked",
    "EconomicGovernanceBoundary",
    "EconomicIntent",
    "EconomicMutationPermit",
    "TrustedContingencyRecoveryClaim",
    "bind_economic_governance_boundary",
]
