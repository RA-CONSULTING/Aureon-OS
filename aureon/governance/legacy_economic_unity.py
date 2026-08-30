"""Unify legacy economic entry points behind the exact Aureon boundary.

Legacy code remains callable through its original transport closure, but it may
not create a second authority path.  A registered capability is matched to an
exact :class:`EconomicIntent`; HNC, Auris, Council, and Crown authority is then
obtained and consumed by the existing one-use economic boundary.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from decimal import Decimal
from pathlib import PurePosixPath
from typing import Any, Callable, Collection, Mapping, TypeVar

from .economic_boundary import (
    EconomicGovernanceBlocked,
    EconomicGovernanceBoundary,
    EconomicIntent,
)

LEGACY_CAPABILITY_SCHEMA = "aureon.legacy_economic_capability.v1"
LEGACY_UNITY_RECEIPT_SCHEMA = "aureon.legacy_economic_unity_receipt.v1"
LEGACY_UNITY_TARGET = "aureon.governance.economic_boundary"

_T = TypeVar("_T")
_FACTORY_TOKEN = object()
_STATUSES = frozenset({"EXECUTED", "HOLD", "AMBIGUOUS"})
_RECEIPT_KEYS = frozenset(
    {
        "schema",
        "receipt_type",
        "receipt_id",
        "status",
        "data_status",
        "reason",
        "capability_id",
        "capability_digest",
        "source_file",
        "source_symbol",
        "intent_digest",
        "hnc_receipt_id",
        "auris_receipt_id",
        "permit_id",
        "dual_receipt_id",
        "proposal_digest",
        "provider_result_digest",
        "migration_target",
        "legacy_capability_preserved",
        "route_authorization_required",
        "economic_mutation",
        "action_eligible",
        "accounting_eligible",
        "learning_eligible",
    }
)


def _nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name}_must_be_nonblank_canonical_text")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _source_path(value: Any) -> str:
    path = _nonblank(value, "source_file")
    if "\\" in path:
        raise ValueError("source_file_must_be_repo_relative_posix_path")
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts or path != parsed.as_posix():
        raise ValueError("source_file_must_be_repo_relative_posix_path")
    return path


def _reason_code(value: Any, fallback: str) -> str:
    reason = str(value or "")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_.:-")
    if (
        not reason
        or len(reason) > 128
        or reason != reason.strip()
        or any(char not in allowed for char in reason)
    ):
        return fallback
    return reason


def _canonical_result(value: Any) -> Any:
    """Return secret-safe deterministic result material for receipt hashing."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            return {"type": "float", "status": "non_finite"}
        return {"type": "float", "hex": value.hex()}
    if isinstance(value, Decimal):
        return {"type": "decimal", "text": format(value, "f")}
    if isinstance(value, bytes):
        return {
            "type": "bytes",
            "sha256": hashlib.sha256(value).hexdigest(),
            "length": len(value),
        }
    if isinstance(value, Mapping):
        normalized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                return {
                    "type": f"{type(value).__module__}.{type(value).__qualname__}",
                    "status": "non_string_mapping_key",
                }
            normalized[key] = _canonical_result(item)
        return normalized
    if isinstance(value, (list, tuple)):
        return [_canonical_result(item) for item in value]
    return {
        "type": f"{type(value).__module__}.{type(value).__qualname__}",
        "status": "opaque_result",
    }


@dataclass(frozen=True, slots=True)
class LegacyEconomicCapability:
    """One preserved legacy entry point and its exact unified route."""

    capability_id: str
    source_file: str
    source_symbol: str
    venue: str
    method: str
    path: str
    operation: str
    purpose: str
    body_bindings: tuple[tuple[str, str], ...]
    preserved_operations: tuple[str, ...]
    migration_target: str = LEGACY_UNITY_TARGET

    def __post_init__(self) -> None:
        capability_id = _nonblank(self.capability_id, "capability_id")
        if not capability_id.startswith("legacy-capability:"):
            raise ValueError("legacy_capability_id_required")
        _source_path(self.source_file)
        _nonblank(self.source_symbol, "source_symbol")
        if self.venue != _nonblank(self.venue, "venue").lower():
            raise ValueError("venue_must_be_lowercase")
        if self.method != _nonblank(self.method, "method").upper():
            raise ValueError("method_must_be_uppercase")
        if not self.path.startswith("/") or "?" in self.path or "#" in self.path:
            raise ValueError("canonical_provider_path_required")
        if self.operation != _nonblank(self.operation, "operation").upper():
            raise ValueError("operation_must_be_uppercase")
        if self.purpose != _nonblank(self.purpose, "purpose").upper():
            raise ValueError("purpose_must_be_uppercase")
        if tuple(sorted(self.body_bindings)) != self.body_bindings:
            raise ValueError("body_bindings_must_be_sorted")
        if len({name for name, _ in self.body_bindings}) != len(self.body_bindings):
            raise ValueError("body_bindings_must_be_unique")
        if not self.preserved_operations or tuple(sorted(set(self.preserved_operations))) != self.preserved_operations:
            raise ValueError("preserved_operations_must_be_sorted_unique_nonempty")
        if self.operation not in self.preserved_operations:
            raise ValueError("route_operation_must_be_preserved")
        if self.migration_target != LEGACY_UNITY_TARGET:
            raise ValueError("economic_boundary_migration_target_required")

    def payload(self) -> dict[str, Any]:
        return {
            "schema": LEGACY_CAPABILITY_SCHEMA,
            "capability_id": self.capability_id,
            "source_file": self.source_file,
            "source_symbol": self.source_symbol,
            "venue": self.venue,
            "method": self.method,
            "path": self.path,
            "operation": self.operation,
            "purpose": self.purpose,
            "body_bindings": [list(item) for item in self.body_bindings],
            "preserved_operations": list(self.preserved_operations),
            "migration_target": self.migration_target,
        }

    @property
    def capability_digest(self) -> str:
        return _sha256_payload(self.payload())


@dataclass(frozen=True, slots=True)
class LegacyEconomicInvocation:
    """A legacy capability paired with its immutable HNC/Auris intent."""

    capability_id: str
    intent: EconomicIntent

    def __post_init__(self) -> None:
        if not self.capability_id.startswith("legacy-capability:"):
            raise ValueError("legacy_capability_id_required")
        if not isinstance(self.intent, EconomicIntent):
            raise TypeError("economic_intent_required")


@dataclass(frozen=True, slots=True)
class LegacyUnityOutcome:
    """Provider result plus a non-authoritative migration receipt."""

    status: str
    provider_result: Any
    receipt: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.status not in _STATUSES:
            raise ValueError("valid_legacy_unity_status_required")
        validate_legacy_unity_receipt(self.receipt)


def _receipt(
    *,
    status: str,
    reason: str,
    capability: LegacyEconomicCapability | None,
    invocation: LegacyEconomicInvocation,
    permit: Any = None,
    provider_result: Any = None,
) -> dict[str, Any]:
    if status not in _STATUSES:
        raise ValueError("valid_legacy_unity_status_required")
    cap = capability
    payload: dict[str, Any] = {
        "schema": LEGACY_UNITY_RECEIPT_SCHEMA,
        "receipt_type": "legacy_economic_unity",
        "status": status,
        "data_status": "live" if status == "EXECUTED" else ("ambiguous" if status == "AMBIGUOUS" else "no_data"),
        "reason": _nonblank(reason, "reason"),
        "capability_id": invocation.capability_id,
        "capability_digest": None if cap is None else cap.capability_digest,
        "source_file": None if cap is None else cap.source_file,
        "source_symbol": None if cap is None else cap.source_symbol,
        "intent_digest": invocation.intent.intent_digest,
        "hnc_receipt_id": invocation.intent.hnc_receipt_id,
        "auris_receipt_id": invocation.intent.auris_receipt_id,
        "permit_id": None if permit is None else permit.permit_id,
        "dual_receipt_id": None if permit is None else permit.dual_receipt_id,
        "proposal_digest": None if permit is None else permit.proposal_digest,
        "provider_result_digest": None if provider_result is None else _sha256_payload(_canonical_result(provider_result)),
        "migration_target": LEGACY_UNITY_TARGET,
        "legacy_capability_preserved": cap is not None,
        "route_authorization_required": True,
        "economic_mutation": False,
        "action_eligible": False,
        "accounting_eligible": False,
        "learning_eligible": False,
    }
    payload["receipt_id"] = f"legacy-unity:{_sha256_payload(payload)}"
    return payload


def validate_legacy_unity_receipt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Strictly validate a migration receipt and reject hidden authority."""

    if not isinstance(receipt, Mapping) or frozenset(receipt) != _RECEIPT_KEYS:
        raise ValueError("complete_legacy_unity_receipt_required")
    normalized = dict(receipt)
    receipt_id = normalized.pop("receipt_id", None)
    expected_id = f"legacy-unity:{_sha256_payload(normalized)}"
    if receipt_id != expected_id:
        raise ValueError("legacy_unity_receipt_hash_mismatch")
    if normalized["schema"] != LEGACY_UNITY_RECEIPT_SCHEMA or normalized["receipt_type"] != "legacy_economic_unity":
        raise ValueError("legacy_unity_receipt_schema_required")
    status = normalized["status"]
    if status not in _STATUSES:
        raise ValueError("valid_legacy_unity_status_required")
    expected_data = "live" if status == "EXECUTED" else ("ambiguous" if status == "AMBIGUOUS" else "no_data")
    if normalized["data_status"] != expected_data:
        raise ValueError("legacy_unity_data_status_mismatch")
    if normalized["migration_target"] != LEGACY_UNITY_TARGET:
        raise ValueError("economic_boundary_migration_target_required")
    if any(
        normalized[name] is not False
        for name in (
            "economic_mutation",
            "action_eligible",
            "accounting_eligible",
            "learning_eligible",
        )
    ) or normalized["route_authorization_required"] is not True:
        raise ValueError("legacy_unity_receipt_must_not_grant_authority")
    if type(normalized["legacy_capability_preserved"]) is not bool:
        raise ValueError("legacy_capability_preserved_must_be_boolean")
    return dict(receipt)


class LegacyEconomicUnityGateway:
    """Only composition-root bridge from preserved legacy code to authority."""

    def __init__(
        self,
        *,
        _factory_token: object,
        boundary: EconomicGovernanceBoundary,
        capabilities: Collection[LegacyEconomicCapability],
    ) -> None:
        if _factory_token is not _FACTORY_TOKEN:
            raise TypeError("use_bind_legacy_economic_unity_gateway")
        if not isinstance(boundary, EconomicGovernanceBoundary):
            raise TypeError("economic_governance_boundary_required")
        items = tuple(capabilities)
        if not items or any(not isinstance(item, LegacyEconomicCapability) for item in items):
            raise ValueError("legacy_capabilities_must_be_nonempty")
        by_id = {item.capability_id: item for item in items}
        if len(by_id) != len(items):
            raise ValueError("legacy_capability_ids_must_be_unique")
        source_routes = {(item.source_file, item.source_symbol, item.operation) for item in items}
        if len(source_routes) != len(items):
            raise ValueError("legacy_source_routes_must_be_unique")
        self._boundary = boundary
        self._capabilities = by_id
        self._receipts: list[dict[str, Any]] = []

    @property
    def capabilities(self) -> tuple[LegacyEconomicCapability, ...]:
        return tuple(self._capabilities[key] for key in sorted(self._capabilities))

    @property
    def receipts(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(receipt) for receipt in self._receipts)

    @staticmethod
    def _matches(capability: LegacyEconomicCapability, intent: EconomicIntent) -> bool:
        return (
            intent.venue == capability.venue
            and intent.method == capability.method
            and intent.path == capability.path
            and intent.operation == capability.operation
            and intent.purpose == capability.purpose
            and intent.body_bindings == capability.body_bindings
        )

    def execute(
        self,
        invocation: LegacyEconomicInvocation,
        *,
        transport: Callable[[], _T],
    ) -> LegacyUnityOutcome:
        """Run one preserved transport only after exact dual-key authority."""

        if not isinstance(invocation, LegacyEconomicInvocation):
            raise TypeError("legacy_economic_invocation_required")
        if not callable(transport):
            raise TypeError("transport_callable_required")
        capability = self._capabilities.get(invocation.capability_id)
        if capability is None or not self._matches(capability, invocation.intent):
            receipt = _receipt(
                status="HOLD",
                reason="registered_exact_legacy_capability_required",
                capability=capability,
                invocation=invocation,
            )
            self._receipts.append(receipt)
            return LegacyUnityOutcome("HOLD", None, receipt)
        try:
            permit = self._boundary.prepare_mutation(invocation.intent)
            body = json.loads(invocation.intent.body_json)
            result = self._boundary.consume_and_call(
                permit,
                method=invocation.intent.method,
                path=invocation.intent.path,
                body=body,
                transport=transport,
            )
        except EconomicGovernanceBlocked as exc:
            receipt = _receipt(
                status="HOLD",
                reason=_reason_code(exc, "economic_governance_hold"),
                capability=capability,
                invocation=invocation,
            )
            self._receipts.append(receipt)
            return LegacyUnityOutcome("HOLD", None, receipt)
        except Exception:
            permit_value = locals().get("permit")
            receipt = _receipt(
                status="AMBIGUOUS",
                reason="transport_outcome_ambiguous_reconciliation_required",
                capability=capability,
                invocation=invocation,
                permit=permit_value,
            )
            self._receipts.append(receipt)
            return LegacyUnityOutcome("AMBIGUOUS", None, receipt)
        receipt = _receipt(
            status="EXECUTED",
            reason="legacy_capability_executed_through_exact_economic_boundary",
            capability=capability,
            invocation=invocation,
            permit=permit,
            provider_result=result,
        )
        self._receipts.append(receipt)
        return LegacyUnityOutcome("EXECUTED", result, receipt)


def bind_legacy_economic_unity_gateway(
    *,
    boundary: EconomicGovernanceBoundary,
    capabilities: Collection[LegacyEconomicCapability],
) -> LegacyEconomicUnityGateway:
    """Bind the only supported legacy migration gateway."""

    return LegacyEconomicUnityGateway(
        _factory_token=_FACTORY_TOKEN,
        boundary=boundary,
        capabilities=capabilities,
    )


__all__ = [
    "LEGACY_CAPABILITY_SCHEMA",
    "LEGACY_UNITY_RECEIPT_SCHEMA",
    "LEGACY_UNITY_TARGET",
    "LegacyEconomicCapability",
    "LegacyEconomicInvocation",
    "LegacyEconomicUnityGateway",
    "LegacyUnityOutcome",
    "bind_legacy_economic_unity_gateway",
    "validate_legacy_unity_receipt",
]
