"""Focused guarantees for the source-bound public-claim evidence control."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import date
from pathlib import Path

from aureon.operator.public_claim_evidence import (
    CLAIM_AUDIT_SCHEMA,
    CLAIM_REGISTER_SCHEMA,
    NON_AUTHORITATIVE_AUTHORITY,
    audit_public_claim_evidence,
    audit_public_claim_evidence_file,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTER_PATH = REPO_ROOT / "data/website_operator/public_claim_evidence_register.v1.json"
AS_OF = date(2026, 7, 26)


def _register() -> dict:
    return json.loads(REGISTER_PATH.read_text(encoding="utf-8"))


def _codes(result: dict, claim_id: str | None = None) -> set[str]:
    return {
        item["code"]
        for item in result["findings"]
        if claim_id is None or item.get("claim_id") == claim_id
    }


def test_default_claim_register_is_source_bound_and_non_authoritative() -> None:
    result = audit_public_claim_evidence_file(REGISTER_PATH, repo_root=REPO_ROOT, as_of=AS_OF)

    assert result["schema"] == CLAIM_AUDIT_SCHEMA
    assert result["state"] == "pass"
    assert result["passed"] is True
    assert result["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert result["release_eligible"] is False
    assert result["deployment_authority"] == "none"
    assert result["summary"] == {
        "claim_count": 14,
        "passed_claim_count": 14,
        "error_count": 0,
        "warning_count": 2,
    }
    assert _codes(result) == {"claim-expiry-near"}
    assert result["register"]["path"] == "data/website_operator/public_claim_evidence_register.v1.json"
    assert len(result["register"]["sha256"]) == 64


def test_register_schema_requires_the_control_fields() -> None:
    schema = json.loads(
        (REPO_ROOT / "aureon/operator/public_claim_evidence.schema.json").read_text(encoding="utf-8")
    )
    register = _register()

    assert register["schema"] == CLAIM_REGISTER_SCHEMA
    assert set(schema["required"]) == {"schema", "generated_at", "authority", "scope", "claims"}
    assert set(schema["$defs"]["claim"]["required"]) == {
        "id",
        "title",
        "claim",
        "state",
        "boundary",
        "permitted_wording",
        "prohibited_inferences",
        "expires_on",
        "source",
        "public_routes",
    }
    assert set(schema["$defs"]["source"]["required"]) == {
        "path",
        "sha256",
        "locator",
        "evidence_texts",
        "boundary_text",
    }
    assert all(claim["source"]["path"].startswith("website/") for claim in register["claims"])


def test_source_hash_drift_is_detected_without_granting_release_authority() -> None:
    register = deepcopy(_register())
    register["claims"][0]["source"]["sha256"] = "0" * 64

    result = audit_public_claim_evidence(register, repo_root=REPO_ROOT, as_of=AS_OF)

    assert result["passed"] is False
    assert "claim-source-drift" in _codes(result, "company-research-led-systems")
    assert result["release_eligible"] is False
    assert result["deployment_authority"] == "none"


def test_expired_and_missing_claim_controls_are_detected() -> None:
    register = deepcopy(_register())
    claim = register["claims"][0]
    claim["boundary"] = ""
    claim["expires_on"] = "2026-07-25"

    result = audit_public_claim_evidence(register, repo_root=REPO_ROOT, as_of=AS_OF)

    assert result["passed"] is False
    codes = _codes(result, "company-research-led-systems")
    assert "claim-boundary" in codes
    assert "claim-expired" in codes


def test_required_state_wording_and_source_locator_are_detected() -> None:
    register = deepcopy(_register())
    claim = register["claims"][0]
    claim["state"] = ""
    claim["permitted_wording"] = []
    claim["source"]["locator"] = ""

    result = audit_public_claim_evidence(register, repo_root=REPO_ROOT, as_of=AS_OF)

    assert result["passed"] is False
    codes = _codes(result, "company-research-led-systems")
    assert "claim-state" in codes
    assert "claim-permitted-wording" in codes
    assert "claim-source-locator" in codes


def test_unsafe_permitted_wording_is_rejected() -> None:
    register = deepcopy(_register())
    register["claims"][1]["permitted_wording"] = [
        "HNC is a market-leading proven customer platform."
    ]

    result = audit_public_claim_evidence(register, repo_root=REPO_ROOT, as_of=AS_OF)

    assert result["passed"] is False
    assert "claim-permitted-wording-unsafe" in _codes(result, "hnc-research-framework")


def test_source_escape_and_missing_anchor_are_rejected() -> None:
    escaped = deepcopy(_register())
    escaped["claims"][0]["source"]["path"] = "../outside.txt"

    escaped_result = audit_public_claim_evidence(escaped, repo_root=REPO_ROOT, as_of=AS_OF)

    assert escaped_result["passed"] is False
    assert "claim-source-path" in _codes(escaped_result, "company-research-led-systems")

    missing_anchor = deepcopy(_register())
    missing_anchor["claims"][0]["source"]["evidence_texts"] = ["evidence not in the website source"]

    missing_anchor_result = audit_public_claim_evidence(missing_anchor, repo_root=REPO_ROOT, as_of=AS_OF)

    assert missing_anchor_result["passed"] is False
    assert "claim-source-anchor-missing" in _codes(
        missing_anchor_result, "company-research-led-systems"
    )


def test_register_cannot_claim_deployment_authority() -> None:
    register = deepcopy(_register())
    register["authority"]["deployment_authority"] = "claim-register"

    result = audit_public_claim_evidence(register, repo_root=REPO_ROOT, as_of=AS_OF)

    assert result["passed"] is False
    assert "non-authoritative-boundary" in _codes(result)
    assert result["release_eligible"] is False
    assert result["deployment_authority"] == "none"


def test_register_requires_generated_time_and_exact_scope() -> None:
    register = deepcopy(_register())
    register["generated_at"] = "not-a-timestamp"
    register["scope"] = "unbounded deployment claims"

    result = audit_public_claim_evidence(register, repo_root=REPO_ROOT, as_of=AS_OF)

    assert result["passed"] is False
    assert {"register-generated-at", "register-scope"}.issubset(_codes(result))
