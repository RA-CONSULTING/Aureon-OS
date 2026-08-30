"""Compact, hash-bound readiness receipt for the repository mutation census.

The static auditor remains the source of discovery truth.  This module turns
one completed audit result into a small process-owned receipt that the organism
composition can validate without importing validation scripts or retaining the
full call-site inventory in memory.

A HOLD receipt is useful evidence, but only an aligned census with zero
live-capable unguarded blockers is READY.  The receipt is never action,
accounting, learning, provider, or economic authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Mapping
from typing import Any

READINESS_SCHEMA = "aureon.economic-mutation-readiness.v1"
CENSUS_SCHEMA = "aureon.economic-mutation-census.v1"
BLOCKER_CLASSIFICATION = "live-capable-unguarded-blocker"
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
_KEYS = frozenset(
    {
        "schema",
        "receipt_type",
        "receipt_id",
        "status",
        "reason",
        "truth_status",
        "census_schema",
        "source_files_scanned",
        "detected_count",
        "classified_count",
        "counts_by_classification",
        "counts_by_provider",
        "inventory_aligned",
        "certified_no_bypass",
        "blocker_count",
        "unallowlisted_count",
        "stale_allowlist_count",
        "parse_error_count",
        "allowlist_sha256",
        "findings_digest",
        "derived_at",
        *_FALSE_FLAGS,
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


def _count_mapping(value: Any, label: str) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label}_mapping_required")
    normalized: dict[str, int] = {}
    for raw_key, raw_count in value.items():
        if (
            not isinstance(raw_key, str)
            or not raw_key
            or raw_key != raw_key.strip()
            or type(raw_count) is not int
            or raw_count < 0
        ):
            raise ValueError(f"canonical_nonnegative_{label}_required")
        normalized[raw_key] = raw_count
    if list(normalized) != sorted(normalized):
        raise ValueError(f"sorted_{label}_required")
    return normalized


def _nonnegative_int(value: Any, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"nonnegative_{label}_required")
    return value


def _readiness_reason(
    *,
    inventory_aligned: bool,
    blocker_count: int,
    certified_no_bypass: bool,
) -> str | None:
    if not inventory_aligned:
        return "economic_mutation_inventory_alignment_required"
    if blocker_count:
        return "unguarded_economic_mutation_routes_remain"
    if not certified_no_bypass:
        return "economic_mutation_no_bypass_certification_required"
    return None


def build_economic_mutation_readiness_receipt(
    census: Mapping[str, Any],
    *,
    allowlist_sha256: str,
    now: float | None = None,
) -> dict[str, Any]:
    """Build a compact receipt from one in-process static-auditor result."""

    if not isinstance(census, Mapping) or census.get("schema") != CENSUS_SCHEMA:
        raise ValueError("economic_mutation_census_v1_required")
    if not isinstance(allowlist_sha256, str) or _DIGEST_RE.fullmatch(allowlist_sha256) is None:
        raise ValueError("allowlist_sha256_required")
    counts_by_classification = _count_mapping(
        census.get("counts_by_classification"),
        "classification_counts",
    )
    counts_by_provider = _count_mapping(
        census.get("counts_by_provider"),
        "provider_counts",
    )
    source_files_scanned = _nonnegative_int(
        census.get("source_files_scanned"),
        "source_files_scanned",
    )
    detected_count = _nonnegative_int(census.get("detected_count"), "detected_count")
    classified_count = _nonnegative_int(
        census.get("classified_count"),
        "classified_count",
    )
    blocker_count = _nonnegative_int(census.get("blocker_count"), "blocker_count")
    inventory_aligned = census.get("inventory_aligned")
    certified_no_bypass = census.get("certified_no_bypass")
    if type(inventory_aligned) is not bool or type(certified_no_bypass) is not bool:
        raise ValueError("strict_census_readiness_booleans_required")
    collections = {
        "unallowlisted": census.get("unallowlisted"),
        "stale_allowlist_entries": census.get("stale_allowlist_entries"),
        "parse_errors": census.get("parse_errors"),
        "findings": census.get("findings"),
    }
    if any(not isinstance(value, list) for value in collections.values()):
        raise ValueError("complete_census_collections_required")
    if (
        sum(counts_by_classification.values()) != classified_count
        or sum(counts_by_provider.values()) != classified_count
        or blocker_count != counts_by_classification.get(BLOCKER_CLASSIFICATION, 0)
        or len(collections["findings"]) != classified_count
    ):
        raise ValueError("census_count_mismatch")
    expected_aligned = not (
        collections["unallowlisted"]
        or collections["stale_allowlist_entries"]
        or collections["parse_errors"]
    )
    expected_certified = expected_aligned and blocker_count == 0
    if inventory_aligned is not expected_aligned or certified_no_bypass is not expected_certified:
        raise ValueError("census_readiness_claim_mismatch")
    if inventory_aligned and detected_count != classified_count:
        raise ValueError("aligned_census_must_classify_every_detection")
    timestamp = time.time() if now is None else float(now)
    if not math.isfinite(timestamp):
        raise ValueError("finite_readiness_timestamp_required")
    reason = _readiness_reason(
        inventory_aligned=inventory_aligned,
        blocker_count=blocker_count,
        certified_no_bypass=certified_no_bypass,
    )
    payload: dict[str, Any] = {
        "schema": READINESS_SCHEMA,
        "receipt_type": "economic_mutation_readiness",
        "status": "ready" if reason is None else "hold",
        "reason": reason,
        "truth_status": "real_derived",
        "census_schema": CENSUS_SCHEMA,
        "source_files_scanned": source_files_scanned,
        "detected_count": detected_count,
        "classified_count": classified_count,
        "counts_by_classification": counts_by_classification,
        "counts_by_provider": counts_by_provider,
        "inventory_aligned": inventory_aligned,
        "certified_no_bypass": certified_no_bypass,
        "blocker_count": blocker_count,
        "unallowlisted_count": len(collections["unallowlisted"]),
        "stale_allowlist_count": len(collections["stale_allowlist_entries"]),
        "parse_error_count": len(collections["parse_errors"]),
        "allowlist_sha256": allowlist_sha256,
        "findings_digest": _sha256_payload(collections["findings"]),
        "derived_at": timestamp,
        **_FALSE_FLAGS,
    }
    payload["receipt_id"] = f"economic-readiness:{_sha256_payload(payload)}"
    return validate_economic_mutation_readiness_receipt(payload)


def validate_economic_mutation_readiness_receipt(
    receipt: Mapping[str, Any],
    *,
    now: float | None = None,
    max_age_s: float | None = None,
) -> dict[str, Any]:
    """Validate shape, causal hash, internal counts, and optional freshness."""

    if not isinstance(receipt, Mapping) or set(receipt) != _KEYS:
        raise ValueError("economic_mutation_readiness_receipt_schema_mismatch")
    normalized = json.loads(_canonical_json(dict(receipt)))
    if (
        normalized["schema"] != READINESS_SCHEMA
        or normalized["receipt_type"] != "economic_mutation_readiness"
        or normalized["truth_status"] != "real_derived"
        or normalized["census_schema"] != CENSUS_SCHEMA
        or any(normalized[name] is not expected for name, expected in _FALSE_FLAGS.items())
    ):
        raise ValueError("economic_mutation_readiness_policy_mismatch")
    counts_by_classification = _count_mapping(
        normalized["counts_by_classification"],
        "classification_counts",
    )
    counts_by_provider = _count_mapping(
        normalized["counts_by_provider"],
        "provider_counts",
    )
    for name in (
        "source_files_scanned",
        "detected_count",
        "classified_count",
        "blocker_count",
        "unallowlisted_count",
        "stale_allowlist_count",
        "parse_error_count",
    ):
        _nonnegative_int(normalized[name], name)
    if (
        type(normalized["inventory_aligned"]) is not bool
        or type(normalized["certified_no_bypass"]) is not bool
        or sum(counts_by_classification.values()) != normalized["classified_count"]
        or sum(counts_by_provider.values()) != normalized["classified_count"]
        or normalized["blocker_count"]
        != counts_by_classification.get(BLOCKER_CLASSIFICATION, 0)
    ):
        raise ValueError("economic_mutation_readiness_count_mismatch")
    expected_aligned = not (
        normalized["unallowlisted_count"]
        or normalized["stale_allowlist_count"]
        or normalized["parse_error_count"]
    )
    expected_certified = expected_aligned and normalized["blocker_count"] == 0
    reason = _readiness_reason(
        inventory_aligned=normalized["inventory_aligned"],
        blocker_count=normalized["blocker_count"],
        certified_no_bypass=normalized["certified_no_bypass"],
    )
    if (
        normalized["inventory_aligned"] is not expected_aligned
        or normalized["certified_no_bypass"] is not expected_certified
        or normalized["status"] != ("ready" if reason is None else "hold")
        or normalized["reason"] != reason
        or not isinstance(normalized["allowlist_sha256"], str)
        or _DIGEST_RE.fullmatch(normalized["allowlist_sha256"]) is None
        or not isinstance(normalized["findings_digest"], str)
        or _DIGEST_RE.fullmatch(normalized["findings_digest"]) is None
    ):
        raise ValueError("economic_mutation_readiness_claim_mismatch")
    derived_at = normalized["derived_at"]
    if type(derived_at) not in {int, float} or not math.isfinite(float(derived_at)):
        raise ValueError("finite_readiness_timestamp_required")
    if max_age_s is not None:
        if type(max_age_s) not in {int, float} or not math.isfinite(float(max_age_s)) or max_age_s <= 0:
            raise ValueError("positive_finite_readiness_max_age_required")
        current = time.time() if now is None else float(now)
        if not math.isfinite(current) or derived_at > current + 5.0 or current - derived_at > max_age_s:
            raise ValueError("fresh_economic_mutation_readiness_required")
    causal = dict(normalized)
    receipt_id = causal.pop("receipt_id")
    if receipt_id != f"economic-readiness:{_sha256_payload(causal)}":
        raise ValueError("economic_mutation_readiness_receipt_id_mismatch")
    return normalized


__all__ = [
    "BLOCKER_CLASSIFICATION",
    "CENSUS_SCHEMA",
    "READINESS_SCHEMA",
    "build_economic_mutation_readiness_receipt",
    "validate_economic_mutation_readiness_receipt",
]
