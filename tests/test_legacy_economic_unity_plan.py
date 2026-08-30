from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from scripts.validation.plan_legacy_economic_unity import (
    BLOCKER,
    DEFAULT_ALLOWLIST,
    UNITY_TARGET,
    build_legacy_unity_plan,
    validate_legacy_unity_plan,
)


def _entry(
    *,
    file: str,
    fingerprint: str,
    provider: str = "kraken",
    classification: str = BLOCKER,
) -> dict[str, str]:
    return {
        "file": file,
        "fingerprint": fingerprint,
        "provider": provider,
        "operation": "sdk-submit-order",
        "transport": "sdk-or-provider-wrapper",
        "classification": classification,
        "rationale": "source census evidence",
        "owner": "economic-governance-migration",
    }


def _allowlist(entries: list[dict[str, str]]) -> dict[str, object]:
    return {
        "schema": "aureon.economic-mutation-allowlist.v1",
        "entries": entries,
    }


def test_every_legacy_blocker_becomes_a_preserved_migration_target() -> None:
    plan = build_legacy_unity_plan(
        _allowlist(
            [
                _entry(
                    file="aureon/trading/unified_exchange_client.py",
                    fingerprint="econop:unified",
                ),
                _entry(
                    file="aureon/queen/queen_quantum_frog.py",
                    fingerprint="econop:queen",
                    provider="multi-provider",
                ),
                _entry(
                    file="scripts/traders/oandaApi.ts",
                    fingerprint="econop:oanda",
                    provider="oanda",
                ),
            ]
        )
    )

    assert plan["summary"]["remaining_legacy_routes"] == 3
    assert plan["summary"]["migration_target_count"] == 3
    assert plan["summary"]["legacy_capability_preserved_count"] == 3
    assert plan["summary"]["discarded_route_count"] == 0
    assert plan["summary"]["discounted_route_count"] == 0
    assert plan["summary"]["capability_loss_count"] == 0
    assert {route["disposition"] for route in plan["routes"]} == {
        "MIGRATE_AND_PRESERVE"
    }
    assert {route["migration_wave"] for route in plan["routes"]} == {
        "cross_runtime_signed_envelope",
        "multi_provider_orchestrator",
        "unified_exchange_dispatch",
    }
    assert all(route["requires_hnc_receipt"] is True for route in plan["routes"])
    assert all(route["requires_auris_receipt"] is True for route in plan["routes"])
    assert all(route["requires_dual_key"] is True for route in plan["routes"])


def test_imported_parallel_tree_is_merged_not_dismissed_by_path() -> None:
    plan = build_legacy_unity_plan(
        _allowlist(
            [
                _entry(
                    file="imports/snapshot/aureon/trading/legacy.py",
                    fingerprint="econop:snapshot",
                    provider="binance",
                )
            ]
        )
    )
    route = plan["routes"][0]

    assert route["migration_wave"] == "parallel_snapshot_merge"
    assert route["disposition"] == "MIGRATE_AND_PRESERVE"
    assert route["target_adapter"].endswith(".snapshot_parity")
    assert route["legacy_capability_preserved"] is True


@pytest.mark.parametrize(
    ("classification", "disposition"),
    [
        ("economic-boundary-last-mile", "PRESERVE_UNIFIED"),
        ("provider-client-raw-transport-guard", "PRESERVE_UNIFIED"),
        ("dry-run-test-demo-only", "PRESERVE_TEST_CAPABILITY"),
    ],
)
def test_existing_guarded_and_test_capabilities_are_preserved(
    classification: str,
    disposition: str,
) -> None:
    plan = build_legacy_unity_plan(
        _allowlist(
            [
                _entry(
                    file="tests/test_route.py",
                    fingerprint=f"econop:{classification}",
                    classification=classification,
                )
            ]
        )
    )

    assert plan["routes"][0]["disposition"] == disposition
    assert plan["routes"][0]["legacy_capability_preserved"] is True
    assert plan["routes"][0]["target_adapter"].startswith(UNITY_TARGET)


def test_unknown_discounting_classification_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported_or_discounting"):
        build_legacy_unity_plan(
            _allowlist(
                [
                    _entry(
                        file="aureon/legacy.py",
                        fingerprint="econop:discount",
                        classification="ignore-old-code",
                    )
                ]
            )
        )


@pytest.mark.parametrize(
    "mutation",
    [
        lambda plan: plan["summary"].__setitem__("discarded_route_count", 1),
        lambda plan: plan["routes"][0].__setitem__("legacy_capability_preserved", False),
        lambda plan: plan["routes"][0].__setitem__("disposition", "DISCARD"),
    ],
)
def test_tampered_or_discounting_plan_never_validates(mutation) -> None:
    plan = build_legacy_unity_plan(
        _allowlist(
            [
                _entry(
                    file="aureon/trading/legacy.py",
                    fingerprint="econop:tamper",
                )
            ]
        )
    )
    forged = deepcopy(plan)
    mutation(forged)

    with pytest.raises(ValueError):
        validate_legacy_unity_plan(forged)


def test_current_repository_allowlist_has_exact_no_loss_migration_coverage() -> None:
    allowlist = json.loads(DEFAULT_ALLOWLIST.read_text(encoding="utf-8"))
    plan = build_legacy_unity_plan(allowlist)
    blocker_count = sum(
        entry["classification"] == BLOCKER for entry in allowlist["entries"]
    )

    assert plan["summary"]["total_census_entries"] == len(allowlist["entries"])
    assert plan["summary"]["remaining_legacy_routes"] == blocker_count
    assert plan["summary"]["migration_target_count"] == blocker_count
    assert plan["summary"]["legacy_capability_preserved_count"] == len(
        allowlist["entries"]
    )
    assert plan["summary"]["discarded_route_count"] == 0
    assert plan["summary"]["discounted_route_count"] == 0
    assert plan["summary"]["capability_loss_count"] == 0
    assert plan["summary"]["migration_complete"] is (blocker_count == 0)
    assert Path(DEFAULT_ALLOWLIST).is_file()
    validate_legacy_unity_plan(plan)
