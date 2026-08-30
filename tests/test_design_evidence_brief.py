"""Focused guarantees for the source-bound investor/design brief contract."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aureon.operator import design_evidence_brief as brief_module
from aureon.operator.design_evidence_brief import (
    AUDIT_SCHEMA,
    BRIEF_SCHEMA,
    NON_AUTHORITATIVE_AUTHORITY,
    DesignEvidenceBriefError,
    audit_design_evidence_brief,
    audit_design_evidence_brief_file,
    write_design_evidence_brief_audit,
)
from aureon.operator.design_research_refresh import audit_design_research_sources_file

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIEF_PATH = REPO_ROOT / "data/website_operator/investor_site_design_brief.v1.json"
AS_OF = datetime(2026, 7, 30, 0, 0, tzinfo=UTC)


def _brief() -> dict:
    return json.loads(BRIEF_PATH.read_text(encoding="utf-8"))


def _check(receipt: dict, identifier: str) -> dict:
    return next(item for item in receipt["checks"] if item["id"] == identifier)


def test_default_brief_is_current_source_bound_and_non_authoritative() -> None:
    receipt = audit_design_evidence_brief_file(BRIEF_PATH, repo_root=REPO_ROOT, as_of=AS_OF)

    assert receipt["schema"] == AUDIT_SCHEMA
    assert receipt["state"] == "pass"
    assert receipt["passed"] is True
    assert receipt["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert receipt["release_eligible"] is False
    assert receipt["package_authority"] == "none"
    assert receipt["deployment_authority"] == "none"
    assert receipt["brief"]["brief_id"] == "investor-site-20260730"
    assert receipt["brief"]["path"] == "data/website_operator/investor_site_design_brief.v1.json"
    assert len(receipt["brief"]["sha256"]) == 64
    assert receipt["summary"] == {
        "check_count": 17,
        "passed_check_count": 17,
        "source_input_count": 8,
        "route_count": 4,
        "claim_capsule_count": 15,
        "feedback_signal_count": 7,
        "visual_rule_count": 4,
    }
    assert all(rule["reduced_motion_required"] is True for rule in receipt["visual_rules"])
    assert all(
        route["local_path"] in route["allowed_paths"] for route in receipt["route_plan"]
    )
    assert _check(receipt, "brief-file-binding")["passed"] is True
    refresh = receipt["research_refresh"]
    assert refresh == {
        "declaration_path": "data/website_operator/design_research_sources.v1.json",
        "declaration_sha256": _brief()["research_refresh"]["declaration_sha256"],
        "state": "current",
        "passed": True,
        "artwork": {"state": "not-cleared", "cleared_for_use": False},
    }
    assert _check(receipt, "research-refresh-binding")["passed"] is True
    assert _check(receipt, "route-claim-permissions")["passed"] is True
    assert _check(receipt, "route-claim-capsules")["passed"] is True
    assert _check(receipt, "stakeholder-feedback-binding")["passed"] is True
    assert _check(receipt, "route-feedback-capsules")["passed"] is True
    assert _check(receipt, "visual-route-coverage")["passed"] is True
    assert len(receipt["route_claim_capsules_sha256"]) == 64
    assert len(receipt["route_feedback_capsules_sha256"]) == 64
    assert receipt["stakeholder_feedback"] == {
        "feedback_id": "investor-site-signals-20260730",
        "path": "data/website_operator/design_stakeholder_feedback.v1.json",
        "sha256": _brief()["feedback_control"]["feedback_sha256"],
        "state": "current",
        "passed": True,
        "signal_ids": [
            "signal-market-problem-clarity",
            "signal-product-solution-clarity",
            "signal-first-buyer-clarity",
            "signal-business-model-clarity",
            "signal-differentiation-boundary",
            "signal-proof-state-clarity",
            "signal-information-hierarchy",
        ],
        "signal_capsules_sha256": (
            "24ED351D0CFE5978185428FE749335F5CB4DF83FA39E6F3A7A5FE2C589A4717A"
        ),
    }
    assert sum(
        len(route_capsule["signals"])
        for route_capsule in receipt["route_feedback_capsules"]
    ) == 7

    route_claim_ids = {
        claim["id"]
        for route_capsule in receipt["route_claim_capsules"]
        for claim in route_capsule["claims"]
    }
    assert route_claim_ids == set(receipt["claim_control"]["claim_ids"])
    assert all(
        claim["boundary"] and claim["permitted_wording"] and claim["prohibited_inferences"]
        for route_capsule in receipt["route_claim_capsules"]
        for claim in route_capsule["claims"]
    )


def test_source_document_hash_drift_and_unknown_claim_are_blocked() -> None:
    changed_document = deepcopy(_brief())
    changed_document["source_document"]["sha256"] = "0" * 64
    document_receipt = audit_design_evidence_brief(
        changed_document,
        brief_path=BRIEF_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert document_receipt["passed"] is False
    assert _check(document_receipt, "source-document-binding")["passed"] is False
    assert _check(document_receipt, "brief-file-binding")["passed"] is False
    assert document_receipt["release_eligible"] is False
    assert document_receipt["deployment_authority"] == "none"

    changed_claim = deepcopy(_brief())
    changed_claim["claim_control"]["claim_ids"].append("unsupported-public-claim")
    claim_receipt = audit_design_evidence_brief(
        changed_claim,
        brief_path=BRIEF_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert claim_receipt["passed"] is False
    assert _check(claim_receipt, "claim-register-binding")["passed"] is False
    assert "unsupported-public-claim" in _check(
        claim_receipt, "claim-register-binding"
    )["evidence"]["missing_claim_ids"]


def test_noncurrent_refresh_blocks_the_brief_without_clearing_artwork(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refresh = audit_design_research_sources_file(repo_root=REPO_ROOT, as_of=AS_OF)
    refresh["state"] = "refresh-due"
    refresh["passed"] = True
    monkeypatch.setattr(
        brief_module,
        "audit_design_research_sources_file",
        lambda **_kwargs: deepcopy(refresh),
    )

    receipt = audit_design_evidence_brief(
        _brief(),
        brief_path=BRIEF_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert receipt["passed"] is False
    assert _check(receipt, "research-refresh-binding")["passed"] is False
    assert receipt["research_refresh"]["state"] == "refresh-due"
    assert receipt["research_refresh"]["artwork"] == {
        "state": "not-cleared",
        "cleared_for_use": False,
    }
    assert receipt["release_eligible"] is False
    assert receipt["deployment_authority"] == "none"


def test_route_claims_must_be_permitted_on_their_exact_public_route() -> None:
    brief = deepcopy(_brief())
    brief["route_plan"][0]["claim_ids"].append("shared-core-application-thesis")

    receipt = audit_design_evidence_brief(
        brief,
        brief_path=BRIEF_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert receipt["passed"] is False
    route_claim_check = _check(receipt, "route-claim-permissions")
    assert route_claim_check["passed"] is False
    assert {"route": "/", "claim_id": "shared-core-application-thesis"} in route_claim_check[
        "evidence"
    ]["mismatches"]


def test_future_brief_and_alias_routes_fail_closed() -> None:
    future = _brief()
    future["issued_at"] = "2026-07-30T01:00:00Z"
    future_receipt = audit_design_evidence_brief(
        future,
        brief_path=BRIEF_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert future_receipt["passed"] is False
    assert _check(future_receipt, "brief-identity-and-freshness")["passed"] is False

    aliased = _brief()
    duplicate = deepcopy(aliased["route_plan"][2])
    duplicate["id"] = "research-alias"
    duplicate["route"] = "/research"
    aliased["route_plan"].append(duplicate)
    alias_receipt = audit_design_evidence_brief(
        aliased,
        brief_path=BRIEF_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert alias_receipt["passed"] is False
    assert _check(alias_receipt, "route-plan")["passed"] is False


def test_in_memory_mapping_cannot_issue_a_passing_receipt_for_another_file() -> None:
    detached = _brief()
    detached["objective"] = "A changed in-memory brief that was never persisted to the canonical control file."

    receipt = audit_design_evidence_brief(
        detached,
        brief_path=BRIEF_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert receipt["passed"] is False
    assert _check(receipt, "brief-file-binding")["passed"] is False
    assert receipt["brief"]["sha256"] != ""


def test_brief_rejects_unsafe_sources_and_any_release_authority() -> None:
    escaped = deepcopy(_brief())
    escaped["source_inputs"][0]["path"] = "../.env"
    escaped_receipt = audit_design_evidence_brief(
        escaped,
        brief_path=BRIEF_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert escaped_receipt["passed"] is False
    assert _check(escaped_receipt, "source-input-bindings")["passed"] is False

    elevated = deepcopy(_brief())
    elevated["authority"]["deployment_authority"] = "design-agent"
    elevated_receipt = audit_design_evidence_brief(
        elevated,
        brief_path=BRIEF_PATH,
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert elevated_receipt["passed"] is False
    assert _check(elevated_receipt, "authority")["passed"] is False
    assert elevated_receipt["release_eligible"] is False
    assert elevated_receipt["deployment_authority"] == "none"


def test_brief_expiry_and_invalid_audit_output_location_fail_closed(tmp_path: Path) -> None:
    stale_receipt = audit_design_evidence_brief(
        _brief(),
        brief_path=BRIEF_PATH,
        repo_root=REPO_ROOT,
        as_of=datetime(2026, 8, 13, 0, 0, tzinfo=UTC),
    )

    assert stale_receipt["passed"] is False
    assert _check(stale_receipt, "brief-identity-and-freshness")["passed"] is False

    with pytest.raises(DesignEvidenceBriefError, match="docs/audits"):
        write_design_evidence_brief_audit(
            stale_receipt,
            tmp_path / "outside-audit.json",
            repo_root=REPO_ROOT,
        )


def test_brief_schema_and_route_contracts_are_explicit() -> None:
    brief = _brief()

    assert brief["schema"] == BRIEF_SCHEMA
    assert set(brief) == {
        "schema",
        "brief_id",
        "issued_at",
        "refresh_by",
        "objective",
        "authority",
        "source_document",
        "research_refresh",
        "feedback_control",
        "claim_control",
        "source_inputs",
        "route_plan",
        "visual_rules",
        "prohibited_public_inferences",
        "acceptance_criteria",
    }
    assert all(
        path.startswith(("website/data/", "docs/research/"))
        for path in (entry["path"] for entry in brief["source_inputs"])
    )
    assert brief["research_refresh"]["required_state"] == "current"
    assert brief["research_refresh"]["required_passed"] is True
    assert brief["research_refresh"]["artwork_state"] == "not-cleared"
    assert brief["research_refresh"]["artwork_cleared_for_use"] is False
