"""Focused contracts for the compact economic-census readiness receipt."""

from __future__ import annotations

from copy import deepcopy

import pytest

from aureon.governance.economic_mutation_readiness import (
    build_economic_mutation_readiness_receipt,
    validate_economic_mutation_readiness_receipt,
)

NOW = 1_776_000_000.0


def _census(*, blockers: int = 0, aligned: bool = True):
    classification_counts = {
        "economic-boundary-last-mile": 4,
        "live-capable-unguarded-blocker": blockers,
        "provider-client-raw-transport-guard": 68,
    }
    count = sum(classification_counts.values())
    unallowlisted = [] if aligned else [{"file": "drift.py"}]
    findings = [
        {
            "file": f"route-{index}.py",
            "fingerprint": f"econop:{index:024x}",
        }
        for index in range(count)
    ]
    return {
        "schema": "aureon.economic-mutation-census.v1",
        "source_files_scanned": 393,
        "detected_count": count,
        "classified_count": count,
        "counts_by_classification": classification_counts,
        "counts_by_provider": {"multi-provider": count},
        "inventory_aligned": aligned,
        "certified_no_bypass": aligned and blockers == 0,
        "blocker_count": blockers,
        "unallowlisted": unallowlisted,
        "stale_allowlist_entries": [],
        "parse_errors": [],
        "findings": findings,
    }


def test_zero_blocker_aligned_census_is_ready_but_never_authority():
    receipt = build_economic_mutation_readiness_receipt(
        _census(),
        allowlist_sha256="a" * 64,
        now=NOW,
    )

    validated = validate_economic_mutation_readiness_receipt(
        receipt,
        now=NOW + 1.0,
        max_age_s=30.0,
    )

    assert validated["status"] == "ready"
    assert validated["certified_no_bypass"] is True
    assert validated["blocker_count"] == 0
    assert validated["economic_mutation"] is False
    assert validated["action_eligible"] is False


def test_aligned_census_with_blockers_is_hash_bound_hold():
    receipt = build_economic_mutation_readiness_receipt(
        _census(blockers=1_445),
        allowlist_sha256="b" * 64,
        now=NOW,
    )

    assert receipt["status"] == "hold"
    assert receipt["reason"] == "unguarded_economic_mutation_routes_remain"
    assert receipt["blocker_count"] == 1_445
    assert validate_economic_mutation_readiness_receipt(receipt) == receipt


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("blocker_count", True),
        ("inventory_aligned", False),
        ("certified_no_bypass", False),
        ("economic_mutation", True),
        ("findings_digest", "0" * 64),
    ),
)
def test_rehashed_or_plain_tamper_is_rejected(field, value):
    receipt = build_economic_mutation_readiness_receipt(
        _census(),
        allowlist_sha256="c" * 64,
        now=NOW,
    )
    tampered = deepcopy(receipt)
    tampered[field] = value

    with pytest.raises(ValueError):
        validate_economic_mutation_readiness_receipt(tampered)


def test_stale_readiness_receipt_is_rejected():
    receipt = build_economic_mutation_readiness_receipt(
        _census(),
        allowlist_sha256="d" * 64,
        now=NOW,
    )

    with pytest.raises(ValueError, match="fresh_economic_mutation_readiness_required"):
        validate_economic_mutation_readiness_receipt(
            receipt,
            now=NOW + 31.0,
            max_age_s=30.0,
        )
