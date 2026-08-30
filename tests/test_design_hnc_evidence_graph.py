"""Contract and rendering tests for the source-neutral HNC graph."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest

from aureon.operator.design_hnc_evidence_graph import (
    AUDIT_SCHEMA,
    DEFAULT_CONTRACT_PATH,
    NON_AUTHORITATIVE_AUTHORITY,
    HNCEvidenceGraphError,
    audit_hnc_evidence_graph_contract,
    audit_hnc_evidence_graph_contract_file,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / DEFAULT_CONTRACT_PATH
AS_OF = datetime(2026, 7, 30, 18, 0, tzinfo=UTC)


def _contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_canonical_graph_is_exact_source_bound_and_within_budget() -> None:
    result = audit_hnc_evidence_graph_contract_file(
        repo_root=REPO_ROOT,
        as_of=AS_OF,
    )

    assert result["schema"] == AUDIT_SCHEMA
    assert result["state"] == "pass"
    assert result["passed"] is True
    assert result["authority"] == NON_AUTHORITATIVE_AUTHORITY
    assert result["release_eligible"] is False
    assert result["package_authority"] == "none"
    assert result["deployment_authority"] == "none"
    assert result["claim_register"]["claim_ids"] == [
        "hnc-research-framework",
        "aureon-os-evidence-system",
    ]
    assert all(check["passed"] for check in result["checks"])
    assert result["outputs"]["component.html"]["bytes"] <= 2500
    assert result["outputs"]["component.css"]["bytes"] <= 5500
    assert result["outputs"]["component.js"]["bytes"] <= 1800


def test_extra_claim_or_changed_claim_wording_fails_closed() -> None:
    extra = _contract()
    extra["claim_ids"].append("mission-blades-application-model")
    with pytest.raises(HNCEvidenceGraphError, match="claim identifiers"):
        audit_hnc_evidence_graph_contract(
            extra,
            contract_path=CONTRACT_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    changed = _contract()
    changed["process_steps"][0]["body"] = "HNC is a proven universal field."
    with pytest.raises(HNCEvidenceGraphError, match="exact permitted claim wording"):
        audit_hnc_evidence_graph_contract(
            changed,
            contract_path=CONTRACT_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


def test_motion_budget_and_authority_cannot_expand() -> None:
    motion = _contract()
    motion["motion"]["repeats"] = True
    with pytest.raises(HNCEvidenceGraphError, match="motion contract changed"):
        audit_hnc_evidence_graph_contract(
            motion,
            contract_path=CONTRACT_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    budget = _contract()
    budget["budgets"]["additional_requests"] = 1
    with pytest.raises(HNCEvidenceGraphError, match="performance budgets changed"):
        audit_hnc_evidence_graph_contract(
            budget,
            contract_path=CONTRACT_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )

    authority = _contract()
    authority["authority"]["candidate_mutation"] = "allowed"
    with pytest.raises(HNCEvidenceGraphError, match="authority changed"):
        audit_hnc_evidence_graph_contract(
            authority,
            contract_path=CONTRACT_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )


def test_claim_register_hash_drift_is_rejected() -> None:
    contract = deepcopy(_contract())
    contract["claim_register"]["sha256"] = "0" * 64
    with pytest.raises(HNCEvidenceGraphError, match="changed after"):
        audit_hnc_evidence_graph_contract(
            contract,
            contract_path=CONTRACT_PATH,
            repo_root=REPO_ROOT,
            as_of=AS_OF,
        )
