"""Exact, short-lived authority for entering one consequential tool handler.

HNC coherence and the Council/Crown dual-key are evidence.  Neither authorizes
an effect.  This module defines the separate composition-root authority lease
that may admit one frozen :class:`ToolDispatchProposal` to its handler.  The
lease does not authorize a provider mutation; economic, filing, payment, and
other irreversible routes retain their downstream execution boundaries and
provider read-back requirements.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from aureon.governance.dual_key import validate_dual_key_receipt
from aureon.inhouse_ai.tool_registry import ToolDispatchProposal, ToolEffect
from aureon.swarm.auris_node_receipts import DEFAULT_MAX_AGE_S

REQUEST_SCHEMA = "aureon.tool_route_authority.request.v1"
LEASE_SCHEMA = "aureon.tool_route_authority.lease.v1"
LEASE_PREFIX = "tool:route-authority:"
DEFAULT_MAX_TTL_S = 5.0
FUTURE_SKEW_S = 1.0

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_PROVIDER_EFFECTS = frozenset({
    ToolEffect.EXTERNAL_MUTATION.value,
    ToolEffect.ECONOMIC_MUTATION.value,
    ToolEffect.PRIVILEGED.value,
})


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


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}_required")
    return value.strip()


def _digest(value: Any, name: str) -> str:
    candidate = _text(value, name)
    suffix = candidate.rsplit(":", 1)[-1]
    if _SHA256_RE.fullmatch(suffix) is None:
        raise ValueError(f"{name}_must_end_with_sha256")
    return candidate


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}_must_be_finite")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name}_must_be_finite")
    return number


@dataclass(frozen=True)
class ToolRouteAuthorityRequest:
    schema: str
    proposal_digest: str
    tool_call_id: str
    runner_turn_index: int
    response_call_index: int
    tool_name: str
    effect: str
    operation_id: str
    arguments_digest: str
    tool_definition_digest: str
    context_digest: str
    governance_proposal_digest: str
    dual_key_receipt_id: str
    dual_key_receipt_digest: str
    dual_key_valid_until: float
    requested_at: float
    request_digest: str

    def material(self) -> dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "request_digest"
        }


@runtime_checkable
class TrustedToolRouteAuthoritySupplier(Protocol):
    """Composition-root trust adapter; never selected by a prompt or plugin."""

    supplier_id: str

    def supply_tool_route_authority(
        self,
        request: ToolRouteAuthorityRequest,
    ) -> Mapping[str, Any]:
        """Return one strict, mandate-backed lease for ``request``."""


def build_tool_route_authority_request(
    proposal: ToolDispatchProposal,
    dual_key_receipt: Mapping[str, Any],
    *,
    expected_governance_proposal_digest: str,
    now: float | None = None,
    dual_key_max_age_s: float = DEFAULT_MAX_AGE_S,
) -> ToolRouteAuthorityRequest:
    if not isinstance(proposal, ToolDispatchProposal):
        raise TypeError("tool_dispatch_proposal_required")
    integrity_error = proposal.integrity_error()
    if integrity_error:
        raise ValueError(f"invalid_tool_dispatch_proposal:{integrity_error}")
    current = _finite(time.time() if now is None else now, "now")
    max_age = _finite(dual_key_max_age_s, "dual_key_max_age_s")
    if max_age <= 0.0 or max_age > DEFAULT_MAX_AGE_S:
        raise ValueError("bounded_dual_key_max_age_required")
    dual_key = validate_dual_key_receipt(
        dual_key_receipt,
        now=current,
        max_age_s=max_age,
    )
    if dual_key.get("decision") != "ACCEPT":
        raise ValueError("accepted_dual_key_evidence_required")
    governance_proposal_digest = _digest(
        expected_governance_proposal_digest,
        "expected_governance_proposal_digest",
    )
    if dual_key.get("proposal_digest") != governance_proposal_digest:
        raise ValueError("dual_key_governance_proposal_mismatch")
    dual_key_id = _text(dual_key.get("receipt_id"), "dual_key_receipt_id")
    dual_key_digest = _sha(dual_key)
    source_timestamp = _finite(dual_key.get("source_timestamp"), "source_timestamp")
    material = {
        "schema": REQUEST_SCHEMA,
        "proposal_digest": proposal.proposal_digest,
        "tool_call_id": proposal.tool_call_id,
        "runner_turn_index": proposal.runner_turn_index,
        "response_call_index": proposal.response_call_index,
        "tool_name": proposal.tool_name,
        "effect": proposal.effect,
        "operation_id": proposal.operation_id,
        "arguments_digest": proposal.arguments_digest,
        "tool_definition_digest": proposal.tool_definition_digest,
        "context_digest": proposal.context_digest,
        "governance_proposal_digest": governance_proposal_digest,
        "dual_key_receipt_id": dual_key_id,
        "dual_key_receipt_digest": dual_key_digest,
        "dual_key_valid_until": source_timestamp + max_age,
        "requested_at": current,
    }
    return ToolRouteAuthorityRequest(
        **material,
        request_digest=f"tool:route-request:{_sha(material)}",
    )


def issue_tool_route_authority_lease(
    request: ToolRouteAuthorityRequest,
    *,
    supplier_id: str,
    mandate_receipt_id: str,
    mandate_receipt_digest: str,
    nonce: str,
    issued_at: float | None = None,
    not_before: float | None = None,
    expires_at: float | None = None,
    max_ttl_s: float = DEFAULT_MAX_TTL_S,
) -> dict[str, Any]:
    """Helper for a trusted supplier; validates its own result before return."""

    if not isinstance(request, ToolRouteAuthorityRequest):
        raise TypeError("tool_route_authority_request_required")
    issued = _finite(time.time() if issued_at is None else issued_at, "issued_at")
    ttl_limit = _finite(max_ttl_s, "max_ttl_s")
    if ttl_limit <= 0.0 or ttl_limit > DEFAULT_MAX_TTL_S:
        raise ValueError("bounded_max_ttl_required")
    start = issued if not_before is None else _finite(not_before, "not_before")
    expiry = issued + min(1.0, ttl_limit) if expires_at is None else _finite(
        expires_at,
        "expires_at",
    )
    causal = {
        "schema": LEASE_SCHEMA,
        "receipt_type": "tool_route_authority_lease",
        "decision": "AUTHORIZE",
        "supplier_id": _text(supplier_id, "supplier_id"),
        "request_digest": request.request_digest,
        "proposal_digest": request.proposal_digest,
        "tool_name": request.tool_name,
        "effect": request.effect,
        "operation_id": request.operation_id,
        "arguments_digest": request.arguments_digest,
        "tool_definition_digest": request.tool_definition_digest,
        "context_digest": request.context_digest,
        "dual_key_receipt_id": request.dual_key_receipt_id,
        "dual_key_receipt_digest": request.dual_key_receipt_digest,
        "mandate_receipt_id": _text(mandate_receipt_id, "mandate_receipt_id"),
        "mandate_receipt_digest": _digest(
            mandate_receipt_digest,
            "mandate_receipt_digest",
        ),
        "nonce": _text(nonce, "nonce"),
        "issued_at": issued,
        "not_before": start,
        "expires_at": expiry,
        "one_use": True,
        "max_uses": 1,
        "handler_entry_authorized": True,
        "effect_executed": False,
        "provider_receipt_required": request.effect in _PROVIDER_EFFECTS,
        "data_status": "live",
        # This is an assertion made by an explicitly allowlisted composition-
        # root supplier. It is not itself a provider signature or legal proof.
        "truth_status": "trusted_supplier_assertion",
        "generated_values": False,
    }
    lease = {**causal, "receipt_id": f"{LEASE_PREFIX}{_sha(causal)}"}
    return validate_tool_route_authority_lease(
        lease,
        request=request,
        expected_supplier_id=causal["supplier_id"],
        now=issued,
        max_ttl_s=ttl_limit,
    )


def validate_tool_route_authority_lease(
    lease: Mapping[str, Any],
    *,
    request: ToolRouteAuthorityRequest,
    expected_supplier_id: str,
    now: float | None = None,
    max_ttl_s: float = DEFAULT_MAX_TTL_S,
) -> dict[str, Any]:
    if not isinstance(request, ToolRouteAuthorityRequest):
        raise TypeError("tool_route_authority_request_required")
    if request.request_digest != f"tool:route-request:{_sha(request.material())}":
        raise ValueError("tool_route_authority_request_digest_mismatch")
    if not isinstance(lease, Mapping):
        raise TypeError("tool_route_authority_lease_required")
    payload = dict(lease)
    causal_keys = {
        "schema", "receipt_type", "decision", "supplier_id",
        "request_digest", "proposal_digest", "tool_name", "effect",
        "operation_id", "arguments_digest", "tool_definition_digest",
        "context_digest", "dual_key_receipt_id", "dual_key_receipt_digest",
        "mandate_receipt_id", "mandate_receipt_digest", "nonce",
        "issued_at", "not_before", "expires_at", "one_use", "max_uses",
        "handler_entry_authorized", "effect_executed",
        "provider_receipt_required", "data_status", "truth_status",
        "generated_values",
    }
    if set(payload) != causal_keys | {"receipt_id"}:
        raise ValueError("exact_tool_route_authority_lease_schema_required")
    supplier_id = _text(expected_supplier_id, "expected_supplier_id")
    if (
        payload["schema"] != LEASE_SCHEMA
        or payload["receipt_type"] != "tool_route_authority_lease"
        or payload["decision"] != "AUTHORIZE"
        or payload["supplier_id"] != supplier_id
        or payload["request_digest"] != request.request_digest
        or payload["proposal_digest"] != request.proposal_digest
        or payload["tool_name"] != request.tool_name
        or payload["effect"] != request.effect
        or payload["operation_id"] != request.operation_id
        or payload["arguments_digest"] != request.arguments_digest
        or payload["tool_definition_digest"] != request.tool_definition_digest
        or payload["context_digest"] != request.context_digest
        or payload["dual_key_receipt_id"] != request.dual_key_receipt_id
        or payload["dual_key_receipt_digest"] != request.dual_key_receipt_digest
        or payload["one_use"] is not True
        or isinstance(payload["max_uses"], bool)
        or not isinstance(payload["max_uses"], int)
        or payload["max_uses"] != 1
        or payload["handler_entry_authorized"] is not True
        or payload["effect_executed"] is not False
        or payload["provider_receipt_required"]
        is not (request.effect in _PROVIDER_EFFECTS)
        or payload["data_status"] != "live"
        or payload["truth_status"] != "trusted_supplier_assertion"
        or payload["generated_values"] is not False
    ):
        raise ValueError("tool_route_authority_lease_binding_mismatch")
    mandate_id = _text(payload["mandate_receipt_id"], "mandate_receipt_id")
    _digest(payload["mandate_receipt_digest"], "mandate_receipt_digest")
    if (
        mandate_id == request.dual_key_receipt_id
        or mandate_id.startswith(LEASE_PREFIX)
    ):
        raise ValueError("independent_mandate_receipt_required")
    if len(_text(payload["nonce"], "nonce")) < 16:
        raise ValueError("route_authority_nonce_too_short")
    current = _finite(time.time() if now is None else now, "now")
    ttl_limit = _finite(max_ttl_s, "max_ttl_s")
    issued = _finite(payload["issued_at"], "issued_at")
    start = _finite(payload["not_before"], "not_before")
    expiry = _finite(payload["expires_at"], "expires_at")
    if (
        ttl_limit <= 0.0
        or ttl_limit > DEFAULT_MAX_TTL_S
        or issued > current + FUTURE_SKEW_S
        or start < issued
        or current < start
        or current >= expiry
        or expiry <= start
        or expiry - issued > ttl_limit
        or expiry > request.dual_key_valid_until
    ):
        raise ValueError("fresh_short_lived_tool_route_authority_required")
    causal = {key: payload[key] for key in sorted(causal_keys)}
    if payload["receipt_id"] != f"{LEASE_PREFIX}{_sha(causal)}":
        raise ValueError("tool_route_authority_lease_hash_mismatch")
    return payload


__all__ = [
    "DEFAULT_MAX_TTL_S",
    "LEASE_PREFIX",
    "LEASE_SCHEMA",
    "REQUEST_SCHEMA",
    "ToolRouteAuthorityRequest",
    "TrustedToolRouteAuthoritySupplier",
    "build_tool_route_authority_request",
    "issue_tool_route_authority_lease",
    "validate_tool_route_authority_lease",
]
