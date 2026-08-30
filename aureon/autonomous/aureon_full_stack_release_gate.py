"""Fail-closed release evidence for Aureon's complete application stack.

This gate does not run tests, deploy services, or invent readiness.  A trusted
composition root supplies a hash-bound bundle containing one fresh receipt for
every canonical stack layer.  Local code release requires offline/runtime
contract evidence for every layer; production release additionally requires
provider read-back evidence for every layer.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, runtime_checkable

LAYER_SCHEMA = "aureon.full-stack-layer-evidence.v1"
BUNDLE_SCHEMA = "aureon.full-stack-evidence-bundle.v1"
RELEASE_SCHEMA = "aureon.full-stack-release-receipt.v1"
DEFAULT_FULL_STACK_EVIDENCE_PATH = Path("docs/evidence/aureon_full_stack_release.v1.json")
DEFAULT_MAX_AGE_S = 86_400.0

LOCAL_ACCEPTANCE = "local_acceptance"
PRODUCTION_READBACK = "production_readback"
ASSURANCE_LEVELS = frozenset({LOCAL_ACCEPTANCE, PRODUCTION_READBACK})

CANONICAL_STACK_LAYERS = (
    "frontend",
    "apis_backend_logic",
    "database_storage",
    "auth_permissions",
    "hosting_deployment",
    "cloud_compute",
    "ci_cd_version_control",
    "security_rls",
    "rate_limiting",
    "caching_cdn",
    "load_balancing_scaling",
    "error_tracking_logs",
)

REQUIRED_LAYER_CONTROLS = {
    "frontend": (
        "frontend_build",
        "frontend_lint",
        "frontend_playwright",
        "frontend_typecheck",
    ),
    "apis_backend_logic": (
        "operator_api_contract",
        "ten_nine_one_thought_path",
        "tool_dispatch_governance",
    ),
    "database_storage": (
        "database_migration_contract",
        "storage_access_contract",
    ),
    "auth_permissions": (
        "edge_function_auth_contract",
        "operator_auth_fail_closed",
    ),
    "hosting_deployment": (
        "cloudflare_packaging",
        "container_packaging",
        "digitalocean_fail_closed",
    ),
    "cloud_compute": (
        "cloud_deploy_preflight",
        "cloudflare_worker_contract",
    ),
    "ci_cd_version_control": (
        "acceptance_workflow_contract",
        "economic_census_inventory_aligned",
        "no_skip_shard_contract",
    ),
    "security_rls": (
        "dual_key_governance",
        "economic_boundary_zero_bypass",
        "supabase_rls_contract",
    ),
    "rate_limiting": (
        "cloudflare_dual_rate_limit",
        "exchange_rate_budget_contract",
        "operator_rate_limit_contract",
    ),
    "caching_cdn": (
        "api_no_store",
        "static_cache_policy",
    ),
    "load_balancing_scaling": (
        "provider_topology_readback",
        "single_writer_scaling",
    ),
    "error_tracking_logs": (
        "alert_delivery_readback",
        "durable_observability_outbox",
        "structured_redaction_correlation",
    ),
}

EVIDENCE_KINDS = frozenset({"offline_contract", "runtime_readback", "provider_readback"})
_FALSE_FLAGS = {
    "operational_eligible": False,
    "provider_eligible": False,
    "action_eligible": False,
    "actionable": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "eligible_for_action": False,
    "eligible_for_accounting": False,
    "eligible_for_learning": False,
    "economic_eligible": False,
    "action_gate_passed": False,
}


class FullStackHold(RuntimeError):
    """Raised when a complete stack release receipt cannot be proven."""


@dataclass(frozen=True)
class FullStackReleaseRequest:
    release_id: str
    environment: str
    assurance_level: str
    scope_digest: str


@dataclass(frozen=True)
class FullStackGateResult:
    decision: str
    receipt: Mapping[str, Any]


@runtime_checkable
class FullStackEvidenceResolver(Protocol):
    """Trusted composition-root boundary for full-stack evidence bundles."""

    resolver_id: str

    def resolve_full_stack_evidence(
        self,
        request: FullStackReleaseRequest,
    ) -> Mapping[str, Any] | None: ...


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Mapping[str, Any] | str) -> str:
    raw = value.encode("utf-8") if isinstance(value, str) else _canonical_bytes(value)
    return hashlib.sha256(raw).hexdigest()


def _receipt(prefix: str, causal: Mapping[str, Any]) -> dict[str, Any]:
    return {**dict(causal), "receipt_id": f"{prefix}{_sha256(causal)}"}


def _nonblank(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"nonblank_{label}_required")
    return value.strip()


def _digest(value: Any, label: str) -> str:
    text = _nonblank(value, label)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise ValueError(f"sha256_{label}_required")
    return text


def _finite(value: Any, label: str) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"finite_{label}_required")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"finite_{label}_required")
    return result


def _sorted_unique_strings(value: Any, label: str, *, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{label}_must_be_string_list")
    if value != sorted(set(value)):
        raise ValueError(f"{label}_must_be_sorted_unique")
    if not allow_empty and not value:
        raise ValueError(f"{label}_required")
    return list(value)


def _require_false_flags(payload: Mapping[str, Any]) -> None:
    if any(payload.get(key) is not expected for key, expected in _FALSE_FLAGS.items()):
        raise ValueError("full_stack_receipt_is_evidence_only")


def _expected_layer_keys() -> set[str]:
    return {
        "schema_version",
        "layer_id",
        "status",
        "environment",
        "scope_digest",
        "checked_at",
        "expires_at",
        "evidence_kinds",
        "control_ids",
        "source_receipt_ids",
        "provider_readback_receipt_ids",
        "summary_digest",
        *_FALSE_FLAGS,
        "receipt_id",
    }


def validate_layer_evidence(
    payload: Mapping[str, Any],
    *,
    request: FullStackReleaseRequest,
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != _expected_layer_keys():
        raise ValueError("exact_full_stack_layer_evidence_required")
    _require_false_flags(payload)
    if payload.get("schema_version") != LAYER_SCHEMA:
        raise ValueError("full_stack_layer_schema_required")
    layer_id = _nonblank(payload.get("layer_id"), "layer_id")
    if layer_id not in CANONICAL_STACK_LAYERS:
        raise ValueError("canonical_stack_layer_required")
    if payload.get("status") != "PASS":
        raise ValueError("full_stack_layer_pass_required")
    if payload.get("environment") != request.environment:
        raise ValueError("full_stack_layer_environment_mismatch")
    if payload.get("scope_digest") != request.scope_digest:
        raise ValueError("full_stack_layer_scope_mismatch")
    checked_at = _finite(payload.get("checked_at"), "checked_at")
    expires_at = _finite(payload.get("expires_at"), "expires_at")
    if checked_at > now + 1.0 or now - checked_at > max_age_s or expires_at < now:
        raise ValueError("fresh_full_stack_layer_evidence_required")
    if expires_at <= checked_at or expires_at - checked_at > max_age_s:
        raise ValueError("bounded_full_stack_layer_expiry_required")
    kinds = _sorted_unique_strings(payload.get("evidence_kinds"), "evidence_kinds")
    if any(kind not in EVIDENCE_KINDS for kind in kinds):
        raise ValueError("recognized_full_stack_evidence_kind_required")
    if not {"offline_contract", "runtime_readback"}.intersection(kinds):
        raise ValueError("local_full_stack_contract_evidence_required")
    control_ids = _sorted_unique_strings(payload.get("control_ids"), "control_ids")
    if control_ids != sorted(REQUIRED_LAYER_CONTROLS[layer_id]):
        raise ValueError("exact_full_stack_layer_controls_required")
    source_ids = _sorted_unique_strings(payload.get("source_receipt_ids"), "source_receipt_ids")
    provider_ids = _sorted_unique_strings(
        payload.get("provider_readback_receipt_ids"),
        "provider_readback_receipt_ids",
        allow_empty=True,
    )
    if any(receipt_id not in source_ids for receipt_id in provider_ids):
        raise ValueError("provider_readback_must_be_source_evidence")
    if request.assurance_level == PRODUCTION_READBACK and (
        "provider_readback" not in kinds or not provider_ids
    ):
        raise ValueError("production_provider_readback_required")
    _digest(payload.get("summary_digest"), "summary_digest")
    causal = {key: payload[key] for key in payload if key != "receipt_id"}
    if payload.get("receipt_id") != f"stack:layer:{_sha256(causal)}":
        raise ValueError("full_stack_layer_receipt_hash_mismatch")
    return dict(payload)


def _bundle_keys() -> set[str]:
    return {
        "schema_version",
        "resolver_id",
        "release_id",
        "environment",
        "assurance_level",
        "scope_digest",
        "issued_at",
        "layers",
        *_FALSE_FLAGS,
        "receipt_id",
    }


def validate_full_stack_bundle(
    payload: Mapping[str, Any],
    *,
    resolver_id: str,
    request: FullStackReleaseRequest,
    now: float,
    max_age_s: float,
) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or set(payload) != _bundle_keys():
        raise ValueError("exact_full_stack_evidence_bundle_required")
    _require_false_flags(payload)
    if payload.get("schema_version") != BUNDLE_SCHEMA:
        raise ValueError("full_stack_bundle_schema_required")
    if payload.get("resolver_id") != resolver_id:
        raise ValueError("full_stack_resolver_identity_mismatch")
    if payload.get("release_id") != request.release_id:
        raise ValueError("full_stack_release_id_mismatch")
    if payload.get("environment") != request.environment:
        raise ValueError("full_stack_environment_mismatch")
    if payload.get("assurance_level") != request.assurance_level:
        raise ValueError("full_stack_assurance_mismatch")
    if payload.get("scope_digest") != request.scope_digest:
        raise ValueError("full_stack_scope_mismatch")
    issued_at = _finite(payload.get("issued_at"), "issued_at")
    if issued_at > now + 1.0 or now - issued_at > max_age_s:
        raise ValueError("fresh_full_stack_bundle_required")
    layers = payload.get("layers")
    if not isinstance(layers, list) or len(layers) != len(CANONICAL_STACK_LAYERS):
        raise ValueError("complete_full_stack_layer_set_required")
    validated = [
        validate_layer_evidence(item, request=request, now=now, max_age_s=max_age_s) for item in layers
    ]
    layer_ids = [item["layer_id"] for item in validated]
    if layer_ids != list(CANONICAL_STACK_LAYERS):
        raise ValueError("canonical_full_stack_layer_order_required")
    causal = {key: payload[key] for key in payload if key != "receipt_id"}
    if payload.get("receipt_id") != f"stack:bundle:{_sha256(causal)}":
        raise ValueError("full_stack_bundle_receipt_hash_mismatch")
    return {**dict(payload), "layers": validated}


def _release_receipt(
    *,
    request: FullStackReleaseRequest,
    decision: str,
    reason: str,
    bundle_receipt_id: str,
    layer_receipt_ids: list[str],
    derived_at: float,
) -> dict[str, Any]:
    return _receipt(
        "stack:release:",
        {
            "schema_version": RELEASE_SCHEMA,
            "decision": decision,
            "reason": reason,
            "release_id": request.release_id,
            "environment": request.environment,
            "assurance_level": request.assurance_level,
            "scope_digest": request.scope_digest,
            "required_layer_ids": list(CANONICAL_STACK_LAYERS),
            "bundle_receipt_id": bundle_receipt_id,
            "layer_receipt_ids": sorted(set(layer_receipt_ids)),
            "derived_at": derived_at,
            **_FALSE_FLAGS,
        },
    )


def validate_full_stack_release_receipt(
    payload: Mapping[str, Any],
    *,
    request: FullStackReleaseRequest,
) -> dict[str, Any]:
    expected_keys = {
        "schema_version",
        "decision",
        "reason",
        "release_id",
        "environment",
        "assurance_level",
        "scope_digest",
        "required_layer_ids",
        "bundle_receipt_id",
        "layer_receipt_ids",
        "derived_at",
        *_FALSE_FLAGS,
        "receipt_id",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected_keys:
        raise ValueError("exact_full_stack_release_receipt_required")
    _require_false_flags(payload)
    if payload.get("schema_version") != RELEASE_SCHEMA:
        raise ValueError("full_stack_release_schema_required")
    if payload.get("decision") not in {"ACCEPT", "HOLD"}:
        raise ValueError("full_stack_release_decision_required")
    _nonblank(payload.get("reason"), "reason")
    if (
        payload.get("release_id") != request.release_id
        or payload.get("environment") != request.environment
        or payload.get("assurance_level") != request.assurance_level
        or payload.get("scope_digest") != request.scope_digest
    ):
        raise ValueError("full_stack_release_request_mismatch")
    if payload.get("required_layer_ids") != list(CANONICAL_STACK_LAYERS):
        raise ValueError("canonical_full_stack_release_layers_required")
    layer_ids = _sorted_unique_strings(
        payload.get("layer_receipt_ids"),
        "layer_receipt_ids",
        allow_empty=payload.get("decision") == "HOLD",
    )
    bundle_id = payload.get("bundle_receipt_id")
    if payload.get("decision") == "ACCEPT":
        if (
            not isinstance(bundle_id, str)
            or not bundle_id.startswith("stack:bundle:")
            or len(layer_ids) != len(CANONICAL_STACK_LAYERS)
            or any(not receipt_id.startswith("stack:layer:") for receipt_id in layer_ids)
        ):
            raise ValueError("complete_full_stack_accept_lineage_required")
    elif bundle_id != "" or layer_ids:
        raise ValueError("numeric_free_full_stack_hold_required")
    _finite(payload.get("derived_at"), "derived_at")
    causal = {key: payload[key] for key in payload if key != "receipt_id"}
    if payload.get("receipt_id") != f"stack:release:{_sha256(causal)}":
        raise ValueError("full_stack_release_receipt_hash_mismatch")
    return dict(payload)


class FullStackReleaseGate:
    """Evaluate a trusted evidence bundle and issue evidence-only ACCEPT/HOLD."""

    def __init__(
        self,
        *,
        resolver: FullStackEvidenceResolver,
        now: Callable[[], float] = time.time,
        max_age_s: float = DEFAULT_MAX_AGE_S,
    ) -> None:
        if not isinstance(resolver, FullStackEvidenceResolver):
            raise ValueError("trusted_full_stack_evidence_resolver_required")
        self._resolver = resolver
        self._now = now
        self._max_age_s = _finite(max_age_s, "max_age_s")
        if self._max_age_s <= 0:
            raise ValueError("positive_max_age_s_required")

    def evaluate(self, request: FullStackReleaseRequest) -> FullStackGateResult:
        if not isinstance(request, FullStackReleaseRequest):
            raise FullStackHold("full_stack_release_request_required")
        try:
            _nonblank(request.release_id, "release_id")
            _nonblank(request.environment, "environment")
            if request.assurance_level not in ASSURANCE_LEVELS:
                raise ValueError("recognized_assurance_level_required")
            _digest(request.scope_digest, "scope_digest")
            now = _finite(self._now(), "now")
        except ValueError as exc:
            raise FullStackHold(str(exc)) from exc
        try:
            raw = self._resolver.resolve_full_stack_evidence(request)
            bundle = validate_full_stack_bundle(
                raw or {},
                resolver_id=self._resolver.resolver_id,
                request=request,
                now=now,
                max_age_s=self._max_age_s,
            )
        except Exception:  # noqa: BLE001 - resolver is a trust boundary
            receipt = _release_receipt(
                request=request,
                decision="HOLD",
                reason="complete_fresh_full_stack_evidence_required",
                bundle_receipt_id="",
                layer_receipt_ids=[],
                derived_at=now,
            )
            return FullStackGateResult(decision="HOLD", receipt=receipt)
        receipt = _release_receipt(
            request=request,
            decision="ACCEPT",
            reason=(
                "all_layers_provider_read_back"
                if request.assurance_level == PRODUCTION_READBACK
                else "all_layers_local_contracts_passed"
            ),
            bundle_receipt_id=bundle["receipt_id"],
            layer_receipt_ids=[item["receipt_id"] for item in bundle["layers"]],
            derived_at=now,
        )
        return FullStackGateResult(decision="ACCEPT", receipt=receipt)

    def require_accept(self, request: FullStackReleaseRequest) -> Mapping[str, Any]:
        result = self.evaluate(request)
        if result.decision != "ACCEPT":
            raise FullStackHold(str(result.receipt.get("reason") or "full_stack_release_hold"))
        return dict(result.receipt)


class LocalFullStackEvidenceResolver:
    """Read the canonical local evidence bundle; never execute checks or deploy."""

    resolver_id = "aureon:local-full-stack-evidence"

    def __init__(self, *, root: Path | None = None, path: Path | None = None) -> None:
        repo_root = Path(root or Path(__file__).resolve().parents[2]).resolve()
        self._path = Path(path) if path is not None else repo_root / DEFAULT_FULL_STACK_EVIDENCE_PATH

    def resolve_full_stack_evidence(
        self,
        request: FullStackReleaseRequest,
    ) -> Mapping[str, Any] | None:
        del request
        try:
            value = json.loads(self._path.read_text(encoding="utf-8"))
            return dict(value) if isinstance(value, Mapping) else None
        except (OSError, UnicodeError, ValueError):
            return None


def build_local_full_stack_release_gate(*, root: Path | None = None) -> FullStackReleaseGate:
    return FullStackReleaseGate(resolver=LocalFullStackEvidenceResolver(root=root))


def build_layer_evidence(
    *,
    layer_id: str,
    environment: str,
    scope_digest: str,
    checked_at: float,
    expires_at: float,
    evidence_kinds: list[str],
    control_ids: list[str],
    source_receipt_ids: list[str],
    provider_readback_receipt_ids: list[str],
    summary_digest: str,
) -> dict[str, Any]:
    """Serialize already-observed evidence; this helper grants no authority."""

    return _receipt(
        "stack:layer:",
        {
            "schema_version": LAYER_SCHEMA,
            "layer_id": layer_id,
            "status": "PASS",
            "environment": environment,
            "scope_digest": scope_digest,
            "checked_at": checked_at,
            "expires_at": expires_at,
            "evidence_kinds": sorted(set(evidence_kinds)),
            "control_ids": sorted(set(control_ids)),
            "source_receipt_ids": sorted(set(source_receipt_ids)),
            "provider_readback_receipt_ids": sorted(set(provider_readback_receipt_ids)),
            "summary_digest": summary_digest,
            **_FALSE_FLAGS,
        },
    )


def build_full_stack_bundle(
    *,
    resolver_id: str,
    request: FullStackReleaseRequest,
    issued_at: float,
    layers: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Serialize a trusted resolver bundle; the resolver remains the authority."""

    return _receipt(
        "stack:bundle:",
        {
            "schema_version": BUNDLE_SCHEMA,
            "resolver_id": resolver_id,
            "release_id": request.release_id,
            "environment": request.environment,
            "assurance_level": request.assurance_level,
            "scope_digest": request.scope_digest,
            "issued_at": issued_at,
            "layers": [dict(item) for item in layers],
            **_FALSE_FLAGS,
        },
    )


__all__ = [
    "ASSURANCE_LEVELS",
    "BUNDLE_SCHEMA",
    "CANONICAL_STACK_LAYERS",
    "DEFAULT_FULL_STACK_EVIDENCE_PATH",
    "FullStackEvidenceResolver",
    "FullStackGateResult",
    "FullStackHold",
    "FullStackReleaseGate",
    "FullStackReleaseRequest",
    "LAYER_SCHEMA",
    "LOCAL_ACCEPTANCE",
    "LocalFullStackEvidenceResolver",
    "PRODUCTION_READBACK",
    "REQUIRED_LAYER_CONTROLS",
    "RELEASE_SCHEMA",
    "build_full_stack_bundle",
    "build_layer_evidence",
    "build_local_full_stack_release_gate",
    "validate_full_stack_bundle",
    "validate_full_stack_release_receipt",
    "validate_layer_evidence",
]
