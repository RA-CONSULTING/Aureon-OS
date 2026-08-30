"""Hermetic preflight tests for the canonical cloud-organism launcher."""

from __future__ import annotations

import hashlib
import json

from aureon.governance.economic_mutation_readiness import (
    build_economic_mutation_readiness_receipt,
)
from aureon.governance.legacy_capability_manifest import (
    build_legacy_capability_manifest,
)
from scripts.operations import run_canonical_cloud_organism as operation
from tests.test_live_workforce_calibration import NOW, _canonical
from tests.test_unified_exchange_unity_composition import _capability
from tests.test_unified_organism_builder import _complete_operation


def _census(*, blockers: int = 0):
    counts = {
        "economic-boundary-last-mile": 4,
        "live-capable-unguarded-blocker": blockers,
        "provider-client-raw-transport-guard": 68,
    }
    count = sum(counts.values())
    return {
        "schema": "aureon.economic-mutation-census.v1",
        "source_files_scanned": 393,
        "detected_count": count,
        "classified_count": count,
        "counts_by_classification": counts,
        "counts_by_provider": {"multi-provider": count},
        "inventory_aligned": True,
        "certified_no_bypass": blockers == 0,
        "blocker_count": blockers,
        "unallowlisted": [],
        "stale_allowlist_entries": [],
        "parse_errors": [],
        "findings": [
            {"fingerprint": f"econop:{index}"} for index in range(count)
        ],
    }


def _allowlist(monkeypatch, tmp_path):
    path = tmp_path / "economic_mutation_allowlist.json"
    path.write_text('{"schema":"test","entries":[]}\n', encoding="utf-8")
    monkeypatch.setattr(operation, "ALLOWLIST_PATH", path)
    return path


def test_current_blockers_hold_before_manifest_cloud_or_exchange(monkeypatch, tmp_path):
    _allowlist(monkeypatch, tmp_path)
    manifest = tmp_path / "must-not-be-read.json"
    manifest.write_text("not-json", encoding="utf-8")

    report, economic, capabilities = operation.inspect_bootstrap_readiness(
        capability_manifest_path=manifest,
        calibration_path=tmp_path / "missing-calibration.json",
        clock=lambda: NOW,
        census_loader=lambda: _census(blockers=1_398),
    )

    assert report["status"] == "hold"
    assert report["reason"] == "unguarded_economic_mutation_routes_remain"
    assert report["economic_blocker_count"] == 1_398
    assert report["capability_manifest_status"] == "blocked_by_economic_census"
    assert report["cloud_configuration_checked"] is False
    assert report["cloud_model_call_count"] == 0
    assert report["exchange_client_construction_count"] == 0
    assert report["exchange_call_count"] == report["order_call_count"] == 0
    assert report["economic_mutation"] is False
    assert economic["status"] == "hold"
    assert capabilities == ()


def test_zero_blocker_preflight_requires_exact_current_manifest(monkeypatch, tmp_path):
    allowlist = _allowlist(monkeypatch, tmp_path)
    calibration_path, _pair = _complete_operation(tmp_path)
    census = _census()
    readiness = build_economic_mutation_readiness_receipt(
        census,
        allowlist_sha256=hashlib.sha256(allowlist.read_bytes()).hexdigest(),
        now=NOW,
    )
    manifest = build_legacy_capability_manifest(
        (_capability(),),
        economic_readiness_receipt=readiness,
    )
    manifest_path = tmp_path / "legacy_economic_capability_manifest.json"
    manifest_path.write_text(_canonical(manifest), encoding="utf-8")

    report, economic, capabilities = operation.inspect_bootstrap_readiness(
        capability_manifest_path=manifest_path,
        calibration_path=calibration_path,
        max_age_s=30.0,
        clock=lambda: NOW,
        census_loader=lambda: census,
    )

    assert report["status"] == "ready_to_activate"
    assert report["reason"] is None
    assert report["calibration_status"] == "complete"
    assert report["capability_manifest_status"] == "ready"
    assert report["capability_count"] == 1
    assert report["cloud_configuration_checked"] is False
    assert economic["status"] == "ready"
    assert capabilities == (_capability(),)


def test_activation_with_current_blockers_never_reaches_builder(monkeypatch, tmp_path):
    _allowlist(monkeypatch, tmp_path)
    builder_calls = [0]
    monkeypatch.setattr(operation, "_run_census", lambda: _census(blockers=1_398))
    monkeypatch.setattr(
        operation,
        "build_canonical_cloud_organism",
        lambda **_kwargs: builder_calls.__setitem__(0, builder_calls[0] + 1),
    )

    report = operation.activate(
        capability_manifest_path=tmp_path / "missing-manifest.json",
        calibration_path=tmp_path / "missing-calibration.json",
    )

    assert report["status"] == "hold"
    assert report["economic_blocker_count"] == 1_398
    assert report["cloud_configuration_checked"] is False
    assert builder_calls == [0]


def test_changed_allowlist_invalidates_existing_manifest(monkeypatch, tmp_path):
    allowlist = _allowlist(monkeypatch, tmp_path)
    calibration_path, _pair = _complete_operation(tmp_path)
    census = _census()
    readiness = build_economic_mutation_readiness_receipt(
        census,
        allowlist_sha256=hashlib.sha256(allowlist.read_bytes()).hexdigest(),
        now=NOW,
    )
    manifest = build_legacy_capability_manifest(
        (_capability(),),
        economic_readiness_receipt=readiness,
    )
    manifest_path = tmp_path / "legacy_economic_capability_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    allowlist.write_text('{"schema":"changed","entries":[]}\n', encoding="utf-8")

    report, _economic, capabilities = operation.inspect_bootstrap_readiness(
        capability_manifest_path=manifest_path,
        calibration_path=calibration_path,
        clock=lambda: NOW,
        census_loader=lambda: census,
    )

    assert report["status"] == "hold"
    assert report["capability_manifest_status"] == "hold"
    assert report["capability_manifest_error"] == (
        "legacy_capability_manifest_policy_mismatch"
    )
    assert capabilities == ()
