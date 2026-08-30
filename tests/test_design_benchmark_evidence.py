"""Deterministic safety checks for local competitor-benchmark evidence."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType

import pytest

from aureon.operator.design_benchmark_evidence import (
    BENCHMARK_SCHEMA,
    LOCAL_METADATA_VERIFICATION,
    NON_AUTHORITATIVE_AUTHORITY,
    OBSERVATION_TYPE,
    PATTERN_USE_BOUNDARY,
    discover_design_benchmark_evidence,
    main,
    verify_design_benchmark_evidence,
    verify_design_benchmark_evidence_against_config,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
FRESH_NOW = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)


def _check(result: dict, identifier: str) -> dict:
    return next(item for item in result["checks"] if item["id"] == identifier)


def test_benchmark_evidence_binds_all_configured_source_metadata() -> None:
    evidence = discover_design_benchmark_evidence(REPO_ROOT, now=FRESH_NOW)

    assert evidence["schema"] == BENCHMARK_SCHEMA
    assert evidence["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert evidence["verification"]["passed"] is True
    assert evidence["verification"]["release_eligible"] is False
    assert evidence["verification"]["deployment_authority"] == "none"
    assert len(evidence["sources"]) == 8
    for source in evidence["sources"]:
        assert source["official_url"].startswith("https://")
        assert source["metadata_sha256"]
        assert source["observation_type"] == OBSERVATION_TYPE
        assert source["use_boundary"] == PATTERN_USE_BOUNDARY
        assert source["metadata_verification"] == LOCAL_METADATA_VERIFICATION
        assert source["remote_content_fetched"] is False


def test_benchmark_evidence_fails_when_metadata_or_no_copy_boundary_drifts() -> None:
    evidence = deepcopy(discover_design_benchmark_evidence(REPO_ROOT, now=FRESH_NOW))
    evidence["sources"][0]["official_url"] = "https://example.test/copied-page"
    evidence["sources"][0]["use_boundary"] = "Can copy a competitor visual style."

    result = verify_design_benchmark_evidence(evidence, repo_root=REPO_ROOT, now=FRESH_NOW)

    assert result["passed"] is False
    assert _check(result, "source-metadata-binding")["passed"] is False
    assert result["release_eligible"] is False
    assert result["deployment_authority"] == "none"


def test_benchmark_evidence_rejects_retained_remote_expression_fields() -> None:
    evidence = deepcopy(discover_design_benchmark_evidence(REPO_ROOT, now=FRESH_NOW))
    evidence["sources"][0]["screenshot"] = "competitor-home.png"

    result = verify_design_benchmark_evidence(evidence, repo_root=REPO_ROOT, now=FRESH_NOW)

    assert result["passed"] is False
    assert _check(result, "source-metadata-binding")["passed"] is False


def test_benchmark_evidence_rejects_extra_top_level_material_or_embedded_release_claim() -> None:
    evidence = deepcopy(discover_design_benchmark_evidence(REPO_ROOT, now=FRESH_NOW))
    evidence["captured_html"] = "<main>copied content</main>"
    evidence["verification"]["release_eligible"] = True

    result = verify_design_benchmark_evidence(evidence, repo_root=REPO_ROOT, now=FRESH_NOW)

    assert result["passed"] is False
    assert _check(result, "strict-record-shape")["passed"] is False
    assert _check(result, "embedded-verification-boundary")["passed"] is False


def test_benchmark_evidence_fails_closed_when_freshness_window_expires() -> None:
    evidence = discover_design_benchmark_evidence(REPO_ROOT, now=FRESH_NOW)
    stale_now = datetime(2026, 9, 11, 12, 0, tzinfo=UTC)

    result = verify_design_benchmark_evidence(evidence, repo_root=REPO_ROOT, now=stale_now)

    assert result["passed"] is False
    assert _check(result, "fresh-source-coverage")["passed"] is False
    assert result["release_eligible"] is False
    assert result["deployment_authority"] == "none"


def test_benchmark_evidence_rejects_claimed_deployment_authority() -> None:
    evidence = deepcopy(discover_design_benchmark_evidence(REPO_ROOT, now=FRESH_NOW))
    evidence["authority"]["deployment_authority"] = "benchmark"

    result = verify_design_benchmark_evidence(evidence, repo_root=REPO_ROOT, now=FRESH_NOW)

    assert result["passed"] is False
    assert _check(result, "non-authoritative-boundary")["passed"] is False
    assert result["release_eligible"] is False


def test_in_memory_adapter_binds_the_exact_operator_config_without_mutation() -> None:
    evidence = discover_design_benchmark_evidence(REPO_ROOT, now=FRESH_NOW)
    config_path = REPO_ROOT / "aureon/operator/website_operator.defaults.json"
    supplied_config = json.loads(config_path.read_text(encoding="utf-8"))
    original_config = deepcopy(supplied_config)

    result = verify_design_benchmark_evidence_against_config(
        evidence,
        MappingProxyType(supplied_config),
        repo_root=REPO_ROOT,
        config_path="aureon/operator/website_operator.defaults.json",
        now=FRESH_NOW,
    )

    assert result["passed"] is True
    assert _check(result, "supplied-config-path")["passed"] is True
    assert _check(result, "supplied-config-design-contract")["passed"] is True
    assert _check(result, "supplied-config-provenance")["passed"] is True
    assert _check(result, "adapter-non-authoritative-boundary")["passed"] is True
    assert result["release_eligible"] is False
    assert result["deployment_authority"] == "none"
    assert supplied_config == original_config


def test_in_memory_adapter_fails_closed_when_mapping_does_not_match_bound_config() -> None:
    evidence = discover_design_benchmark_evidence(REPO_ROOT, now=FRESH_NOW)
    config_path = REPO_ROOT / "aureon/operator/website_operator.defaults.json"
    supplied_config = json.loads(config_path.read_text(encoding="utf-8"))
    supplied_config["ethos"]["principles"].append("Unbound local policy change.")

    result = verify_design_benchmark_evidence_against_config(
        evidence,
        supplied_config,
        repo_root=REPO_ROOT,
        now=FRESH_NOW,
    )

    assert result["passed"] is False
    assert _check(result, "supplied-config-design-contract")["passed"] is True
    assert _check(result, "supplied-config-provenance")["passed"] is False
    assert result["release_eligible"] is False
    assert result["deployment_authority"] == "none"


def test_in_memory_adapter_rejects_a_different_config_path_even_with_same_mapping() -> None:
    evidence = discover_design_benchmark_evidence(REPO_ROOT, now=FRESH_NOW)
    config_path = REPO_ROOT / "aureon/operator/website_operator.defaults.json"
    supplied_config = json.loads(config_path.read_text(encoding="utf-8"))

    result = verify_design_benchmark_evidence_against_config(
        evidence,
        supplied_config,
        repo_root=REPO_ROOT,
        config_path="docs/research/schemas/AUREON_DESIGN_BENCHMARK_EVIDENCE_V1.schema.json",
        now=FRESH_NOW,
    )

    assert result["passed"] is False
    assert _check(result, "supplied-config-path")["passed"] is False
    assert _check(result, "supplied-config-provenance")["passed"] is False
    assert result["release_eligible"] is False
    assert result["deployment_authority"] == "none"


def test_benchmark_evidence_schema_declares_no_remote_content_and_no_deployment_authority() -> None:
    schema_path = REPO_ROOT / "docs/research/schemas/AUREON_DESIGN_BENCHMARK_EVIDENCE_V1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    source_properties = schema["$defs"]["source"]["properties"]
    authority_properties = schema["properties"]["authority"]["properties"]
    assert schema["properties"]["schema"]["const"] == BENCHMARK_SCHEMA
    assert source_properties["remote_content_fetched"]["const"] is False
    assert source_properties["observation_type"]["const"] == OBSERVATION_TYPE
    assert source_properties["use_boundary"]["const"] == PATTERN_USE_BOUNDARY
    assert authority_properties["deployment_authority"]["const"] == "none"
    assert authority_properties["release_eligibility"]["const"] == "always-false"


def test_cli_refuses_to_overwrite_config_or_write_evidence_outside_receipt_area(
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = REPO_ROOT / "aureon/operator/website_operator.defaults.json"
    original_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()

    status = main(
        [
            "--repo-root",
            str(REPO_ROOT),
            "--output",
            "aureon/operator/website_operator.defaults.json",
        ]
    )

    assert status == 2
    assert hashlib.sha256(config_path.read_bytes()).hexdigest() == original_sha
    assert "Benchmark evidence output must be inside artifacts/website-operator/" in capsys.readouterr().out
