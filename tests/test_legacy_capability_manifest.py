"""Focused exact-binding tests for the legacy capability manifest."""

from __future__ import annotations

from copy import deepcopy

import pytest

from aureon.governance.economic_mutation_readiness import (
    build_economic_mutation_readiness_receipt,
)
from aureon.governance.legacy_capability_manifest import (
    build_legacy_capability_manifest,
    validate_legacy_capability_manifest,
)
from tests.test_unified_exchange_unity_composition import _capability


def _readiness(*, blockers: int = 0):
    counts = {
        "economic-boundary-last-mile": 1,
        "live-capable-unguarded-blocker": blockers,
    }
    count = sum(counts.values())
    return build_economic_mutation_readiness_receipt(
        {
            "schema": "aureon.economic-mutation-census.v1",
            "source_files_scanned": 1,
            "detected_count": count,
            "classified_count": count,
            "counts_by_classification": counts,
            "counts_by_provider": {"kraken": count},
            "inventory_aligned": True,
            "certified_no_bypass": blockers == 0,
            "blocker_count": blockers,
            "unallowlisted": [],
            "stale_allowlist_entries": [],
            "parse_errors": [],
            "findings": [
                {"fingerprint": f"econop:{index}"} for index in range(count)
            ],
        },
        allowlist_sha256="a" * 64,
        now=1.0,
    )


def test_manifest_round_trip_binds_exact_census_and_capability():
    readiness = _readiness()
    manifest = build_legacy_capability_manifest(
        (_capability(),),
        economic_readiness_receipt=readiness,
    )

    validated, capabilities = validate_legacy_capability_manifest(
        manifest,
        economic_readiness_receipt=readiness,
    )

    assert validated == manifest
    assert capabilities == (_capability(),)
    assert validated["source_census_receipt_id"] == readiness["receipt_id"]
    assert validated["economic_mutation"] is False


def test_manifest_cannot_be_built_from_blocked_census():
    with pytest.raises(ValueError, match="ready_economic_mutation_census_required"):
        build_legacy_capability_manifest(
            (_capability(),),
            economic_readiness_receipt=_readiness(blockers=1),
        )


def test_manifest_rejects_different_current_census():
    readiness = _readiness()
    manifest = build_legacy_capability_manifest(
        (_capability(),),
        economic_readiness_receipt=readiness,
    )
    changed = deepcopy(readiness)
    changed["allowlist_sha256"] = "b" * 64

    with pytest.raises(ValueError):
        validate_legacy_capability_manifest(
            manifest,
            economic_readiness_receipt=changed,
        )


@pytest.mark.parametrize(
    "mutation",
    (
        lambda value: value["capabilities"][0]["capability"].__setitem__(
            "path",
            "/0/private/Withdraw",
        ),
        lambda value: value["capabilities"][0].__setitem__(
            "capability_digest",
            "0" * 64,
        ),
        lambda value: value.__setitem__("economic_mutation", True),
        lambda value: value.__setitem__("manifest_digest", "0" * 64),
    ),
)
def test_manifest_tamper_is_rejected(mutation):
    readiness = _readiness()
    manifest = build_legacy_capability_manifest(
        (_capability(),),
        economic_readiness_receipt=readiness,
    )
    tampered = deepcopy(manifest)
    mutation(tampered)

    with pytest.raises(ValueError):
        validate_legacy_capability_manifest(
            tampered,
            economic_readiness_receipt=readiness,
        )
