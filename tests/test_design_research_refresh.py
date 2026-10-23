"""Focused safety guarantees for local design research source refresh evidence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from aureon.operator.design_research_refresh import (
    DEFAULT_SOURCE_DECLARATION_PATH,
    NON_AUTHORITATIVE_AUTHORITY,
    REFRESH_RECEIPT_SCHEMA,
    SOURCE_DECLARATION_SCHEMA,
    DesignResearchRefreshError,
    audit_design_research_sources,
    audit_design_research_sources_file,
    write_design_research_refresh_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DECLARATION_PATH = REPO_ROOT / DEFAULT_SOURCE_DECLARATION_PATH
AS_OF = datetime(2026, 7, 30, 0, 0, tzinfo=UTC)


def _declaration() -> dict:
    return json.loads(DECLARATION_PATH.read_text(encoding="utf-8"))


def _check(receipt: dict, identifier: str) -> dict:
    return next(item for item in receipt["checks"] if item["id"] == identifier)


def test_canonical_declaration_is_source_bound_and_non_authoritative() -> None:
    receipt = audit_design_research_sources_file(
        DECLARATION_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert receipt["schema"] == REFRESH_RECEIPT_SCHEMA
    assert receipt["state"] == "current"
    assert receipt["passed"] is True
    assert receipt["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert receipt["release_eligible"] is False
    assert receipt["package_authority"] == "none"
    assert receipt["deployment_authority"] == "none"
    assert receipt["declaration"]["path"] == DEFAULT_SOURCE_DECLARATION_PATH.as_posix()
    assert receipt["summary"] == {
        "source_count": 3,
        "fresh_count": 3,
        "due_count": 0,
        "stale_count": 0,
        "missing_count": 0,
        "invalid_count": 0,
    }
    assert _check(receipt, "declaration-file-binding")["passed"] is True
    assert _check(receipt, "source-integrity")["passed"] is True
    assert _check(receipt, "source-freshness")["evidence"]["due_source_ids"] == []
    assert receipt["artwork"]["state"] == "not-cleared"
    assert receipt["artwork"]["cleared_for_use"] is False
    assert receipt["artwork"]["source_artwork_included"] is False


def test_due_source_is_identified_without_granting_any_release_authority() -> None:
    receipt = audit_design_research_sources_file(
        DECLARATION_PATH,
        repo_root=REPO_ROOT,
        as_of=datetime(2026, 8, 13, 20, 30, tzinfo=UTC),
    )

    assert receipt["passed"] is True
    assert receipt["state"] == "refresh-due"
    assert receipt["summary"]["due_count"] == 2
    assert set(_check(receipt, "source-freshness")["evidence"]["due_source_ids"]) == {
        "research-catalogue-public-data",
        "peer-design-pattern-review",
    }
    assert receipt["release_eligible"] is False
    assert receipt["deployment_authority"] == "none"


def test_stale_source_is_blocked_and_identified() -> None:
    declaration = _declaration()
    declaration["sources"][0]["expires_at"] = "2026-07-29T23:45:00Z"

    receipt = audit_design_research_sources(
        declaration,
        declaration_path=DECLARATION_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert receipt["passed"] is False
    assert receipt["state"] == "blocked"
    assert receipt["summary"]["stale_count"] == 1
    assert "orcid-public-research-index" in _check(receipt, "source-freshness")["evidence"][
        "stale_source_ids"
    ]
    assert receipt["release_eligible"] is False
    assert receipt["deployment_authority"] == "none"


def test_missing_snapshot_is_blocked_and_identified() -> None:
    declaration = _declaration()
    declaration["sources"][1]["snapshot"]["path"] = "docs/research/NO_SUCH_PUBLIC_SNAPSHOT.md"

    receipt = audit_design_research_sources(
        declaration,
        declaration_path=DECLARATION_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert receipt["passed"] is False
    assert receipt["summary"]["missing_count"] == 1
    assert "research-catalogue-public-data" in _check(receipt, "source-freshness")["evidence"][
        "missing_source_ids"
    ]
    assert _check(receipt, "source-integrity")["passed"] is False


def test_snapshot_hash_drift_and_path_escape_fail_closed() -> None:
    hash_drift = _declaration()
    hash_drift["sources"][0]["snapshot"]["sha256"] = "0" * 64
    drift_receipt = audit_design_research_sources(
        hash_drift,
        declaration_path=DECLARATION_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert drift_receipt["passed"] is False
    assert drift_receipt["summary"]["invalid_count"] == 1
    assert _check(drift_receipt, "source-integrity")["passed"] is False

    escaped = _declaration()
    escaped["sources"][0]["snapshot"]["path"] = "../.env"
    escaped_receipt = audit_design_research_sources(
        escaped,
        declaration_path=DECLARATION_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert escaped_receipt["passed"] is False
    assert escaped_receipt["summary"]["invalid_count"] == 1
    assert _check(escaped_receipt, "source-integrity")["passed"] is False


def test_unsupported_artwork_and_authority_escalation_fail_closed() -> None:
    artwork = _declaration()
    artwork["artwork_policy"]["state"] = "cleared"
    artwork_receipt = audit_design_research_sources(
        artwork,
        declaration_path=DECLARATION_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert artwork_receipt["passed"] is False
    assert _check(artwork_receipt, "artwork-not-cleared")["passed"] is False
    assert artwork_receipt["artwork"]["cleared_for_use"] is False

    elevated = _declaration()
    elevated["authority"]["deployment_authority"] = "design-agent"
    elevated_receipt = audit_design_research_sources(
        elevated,
        declaration_path=DECLARATION_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert elevated_receipt["passed"] is False
    assert _check(elevated_receipt, "non-authoritative-boundary")["passed"] is False
    assert elevated_receipt["release_eligible"] is False
    assert elevated_receipt["deployment_authority"] == "none"


def test_declaration_cannot_be_issued_from_an_unbound_mapping() -> None:
    declaration = _declaration()
    declaration["sources"][0]["purpose"] = "A changed source record that was never persisted to the canonical declaration."

    receipt = audit_design_research_sources(
        declaration,
        declaration_path=DECLARATION_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert receipt["passed"] is False
    assert _check(receipt, "declaration-file-binding")["passed"] is False


def test_receipt_write_is_immutable_and_restricted_to_evidence_area() -> None:
    receipt = audit_design_research_sources_file(
        DECLARATION_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )
    output = (
        REPO_ROOT
        / "artifacts/website-operator/design-research-refreshes"
        / f"design-research-refresh-test-{uuid4().hex}.json"
    )
    try:
        written = write_design_research_refresh_receipt(receipt, output, repo_root=REPO_ROOT)
        assert written == output
        assert json.loads(written.read_text(encoding="utf-8"))["schema"] == REFRESH_RECEIPT_SCHEMA
        with pytest.raises(DesignResearchRefreshError, match="Refusing to overwrite"):
            write_design_research_refresh_receipt(receipt, output, repo_root=REPO_ROOT)
    finally:
        if output.exists():
            output.unlink()

    with pytest.raises(DesignResearchRefreshError, match="design-research-refreshes"):
        write_design_research_refresh_receipt(
            receipt,
            REPO_ROOT / "artifacts/website-operator/design-research-refresh-outside.json",
            repo_root=REPO_ROOT,
        )


def test_schema_declares_artwork_not_cleared_and_no_release_authority() -> None:
    schema_path = REPO_ROOT / "docs/research/schemas/AUREON_DESIGN_RESEARCH_REFRESH_V1.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))

    declaration = schema["$defs"]["declaration"]
    authority = schema["$defs"]["authority"]["properties"]
    artwork = schema["$defs"]["artworkPolicy"]["properties"]
    assert declaration["properties"]["schema"]["const"] == SOURCE_DECLARATION_SCHEMA
    assert artwork["state"]["const"] == "not-cleared"
    assert artwork["confirmed_local_provenance"]["const"] is False
    assert artwork["source_artwork_included"]["const"] is False
    assert authority["deployment_authority"]["const"] == "none"
    assert authority["network_access"]["const"] == "none"
    assert authority["connector_access"]["const"] == "none"
