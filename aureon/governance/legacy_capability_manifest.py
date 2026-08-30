"""Strict manifest for the preserved legacy capabilities admitted to unity.

The manifest is bound to one exact economic-readiness receipt.  A new census
therefore requires a new reviewed manifest instead of silently inheriting old
routes.  Entries are the existing :class:`LegacyEconomicCapability` contract;
unknown or omitted capabilities remain unavailable rather than falling back to
an ungoverned transport.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

from .economic_mutation_readiness import (
    validate_economic_mutation_readiness_receipt,
)
from .legacy_economic_unity import (
    LEGACY_CAPABILITY_SCHEMA,
    LegacyEconomicCapability,
)

MANIFEST_SCHEMA = "aureon.legacy-economic-capability-manifest.v1"
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
_FALSE_FLAGS = {
    "action_eligible": False,
    "accounting_eligible": False,
    "learning_eligible": False,
    "actionable": False,
    "operational_eligible": False,
    "provider_eligible": False,
    "economic_mutation": False,
}
_MANIFEST_KEYS = frozenset(
    {
        "schema",
        "manifest_id",
        "source_census_receipt_id",
        "source_allowlist_sha256",
        "capability_count",
        "capabilities",
        "manifest_digest",
        *_FALSE_FLAGS,
    }
)
_ENTRY_KEYS = frozenset({"capability", "capability_digest"})
_CAPABILITY_KEYS = frozenset(
    {
        "schema",
        "capability_id",
        "source_file",
        "source_symbol",
        "venue",
        "method",
        "path",
        "operation",
        "purpose",
        "body_bindings",
        "preserved_operations",
        "migration_target",
    }
)


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


def _capability_from_payload(payload: Mapping[str, Any]) -> LegacyEconomicCapability:
    if not isinstance(payload, Mapping) or set(payload) != _CAPABILITY_KEYS:
        raise ValueError("legacy_capability_manifest_entry_schema_mismatch")
    if payload.get("schema") != LEGACY_CAPABILITY_SCHEMA:
        raise ValueError("legacy_economic_capability_v1_required")
    values = dict(payload)
    values.pop("schema")
    body_bindings = values.get("body_bindings")
    preserved_operations = values.get("preserved_operations")
    if not isinstance(body_bindings, list) or any(
        not isinstance(item, list) or len(item) != 2 for item in body_bindings
    ):
        raise ValueError("legacy_capability_body_bindings_required")
    if not isinstance(preserved_operations, list):
        raise ValueError("legacy_capability_preserved_operations_required")
    values["body_bindings"] = tuple(tuple(item) for item in body_bindings)
    values["preserved_operations"] = tuple(preserved_operations)
    return LegacyEconomicCapability(**values)


def build_legacy_capability_manifest(
    capabilities: Sequence[LegacyEconomicCapability],
    *,
    economic_readiness_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a manifest only for a current, zero-bypass census receipt."""

    readiness = validate_economic_mutation_readiness_receipt(
        economic_readiness_receipt
    )
    if readiness["status"] != "ready":
        raise ValueError("ready_economic_mutation_census_required")
    normalized_capabilities = tuple(capabilities)
    if not normalized_capabilities or any(
        not isinstance(item, LegacyEconomicCapability)
        for item in normalized_capabilities
    ):
        raise ValueError("nonempty_legacy_economic_capabilities_required")
    capability_ids = [item.capability_id for item in normalized_capabilities]
    if len(set(capability_ids)) != len(capability_ids):
        raise ValueError("unique_legacy_capability_ids_required")
    entries = [
        {
            "capability": item.payload(),
            "capability_digest": item.capability_digest,
        }
        for item in sorted(normalized_capabilities, key=lambda item: item.capability_id)
    ]
    causal: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "source_census_receipt_id": readiness["receipt_id"],
        "source_allowlist_sha256": readiness["allowlist_sha256"],
        "capability_count": len(entries),
        "capabilities": entries,
        **_FALSE_FLAGS,
    }
    causal["manifest_digest"] = _sha256_payload(causal)
    causal["manifest_id"] = f"legacy-capability-manifest:{causal['manifest_digest']}"
    return validate_legacy_capability_manifest(
        causal,
        economic_readiness_receipt=readiness,
    )[0]


def validate_legacy_capability_manifest(
    manifest: Mapping[str, Any],
    *,
    economic_readiness_receipt: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[LegacyEconomicCapability, ...]]:
    """Validate exact census binding and return reconstructed capabilities."""

    readiness = validate_economic_mutation_readiness_receipt(
        economic_readiness_receipt
    )
    if readiness["status"] != "ready":
        raise ValueError("ready_economic_mutation_census_required")
    if not isinstance(manifest, Mapping) or set(manifest) != _MANIFEST_KEYS:
        raise ValueError("legacy_capability_manifest_schema_mismatch")
    normalized = json.loads(_canonical_json(dict(manifest)))
    if (
        normalized["schema"] != MANIFEST_SCHEMA
        or normalized["source_census_receipt_id"] != readiness["receipt_id"]
        or normalized["source_allowlist_sha256"] != readiness["allowlist_sha256"]
        or any(normalized[name] is not expected for name, expected in _FALSE_FLAGS.items())
    ):
        raise ValueError("legacy_capability_manifest_policy_mismatch")
    entries = normalized["capabilities"]
    if (
        not isinstance(entries, list)
        or not entries
        or type(normalized["capability_count"]) is not int
        or normalized["capability_count"] != len(entries)
    ):
        raise ValueError("nonempty_exact_legacy_capability_count_required")
    capabilities: list[LegacyEconomicCapability] = []
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != _ENTRY_KEYS:
            raise ValueError("legacy_capability_manifest_entry_mismatch")
        capability = _capability_from_payload(entry["capability"])
        if entry["capability_digest"] != capability.capability_digest:
            raise ValueError("legacy_capability_digest_mismatch")
        capabilities.append(capability)
    ids = [item.capability_id for item in capabilities]
    if ids != sorted(ids) or len(set(ids)) != len(ids):
        raise ValueError("sorted_unique_legacy_capability_ids_required")
    causal = dict(normalized)
    manifest_id = causal.pop("manifest_id")
    manifest_digest = causal.pop("manifest_digest")
    if (
        not isinstance(manifest_digest, str)
        or _DIGEST_RE.fullmatch(manifest_digest) is None
        or manifest_digest != _sha256_payload(causal)
        or manifest_id != f"legacy-capability-manifest:{manifest_digest}"
    ):
        raise ValueError("legacy_capability_manifest_digest_mismatch")
    return normalized, tuple(capabilities)


__all__ = [
    "MANIFEST_SCHEMA",
    "build_legacy_capability_manifest",
    "validate_legacy_capability_manifest",
]
