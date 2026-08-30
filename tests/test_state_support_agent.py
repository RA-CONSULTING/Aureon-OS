from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from aureon.operator.state_support_agent import StateSupportEligibilityAgent

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data" / "research" / "benchmarks" / "naic2026_state_support"


def load(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def by_id(portfolio: dict, route_id: str) -> dict:
    return next(row for row in portfolio["route_results"] if row["route_id"] == route_id)


def evaluate(profile_id: str) -> dict:
    rules = load("rules_snapshot_20260821.json")
    profiles = load("synthetic_companies.json")
    profile = next(row for row in profiles["profiles"] if row["profile_id"] == profile_id)
    agent = StateSupportEligibilityAgent(rules["routes"])
    return agent.evaluate_portfolio(
        profile,
        as_of=datetime.fromisoformat("2026-08-21T05:00:00+01:00"),
        source_snapshot=rules,
    )


def test_northern_ireland_sme_is_sequenced_to_challenge_and_evidence_gates():
    result = evaluate("SYNTHETIC-NI-AI-SME")
    assert by_id(result, "TECHIRELAND-NAIC2026")["decision"] == "AVAILABLE_NOW"
    assert by_id(result, "INVESTNI-BIG-2026-09")["decision"] == "NEEDS_EVIDENCE"
    assert by_id(result, "GO-SUCCEED-ULTIMATE-PITCH-2026")["decision"] == "PROVIDER_DECISION_REQUIRED"
    assert by_id(result, "UKRI-EPSRC-FUTURE-COMPUTING-2026")["decision"] == "NOT_ELIGIBLE"


def test_scottish_research_organisation_reaches_epsrc_provider_decision():
    result = evaluate("SYNTHETIC-SCOTTISH-RESEARCH-LEAD")
    epsrc = by_id(result, "UKRI-EPSRC-FUTURE-COMPUTING-2026")
    assert epsrc["decision"] == "PROVIDER_DECISION_REQUIRED"
    assert epsrc["readiness_score"] == 1.0
    assert epsrc["provider_is_final_authority"] is True


def test_republic_of_ireland_sme_is_eligible_for_the_ai_challenge_only():
    result = evaluate("SYNTHETIC-ROI-DATA-SME")
    assert by_id(result, "TECHIRELAND-NAIC2026")["decision"] == "AVAILABLE_NOW"
    assert by_id(result, "INVESTNI-BIG-2026-09")["decision"] == "NOT_ELIGIBLE"
    assert by_id(result, "GO-SUCCEED-ULTIMATE-PITCH-2026")["decision"] == "NOT_ELIGIBLE"


def test_missing_fact_is_an_evidence_gap_not_an_invented_answer():
    rules = load("rules_snapshot_20260821.json")
    profile = {
        "profile_id": "SYNTHETIC-INCOMPLETE",
        "jurisdiction": "Northern Ireland",
        "organisation_size": "micro",
        "sector": "technology",
    }
    result = StateSupportEligibilityAgent(rules["routes"]).evaluate_portfolio(
        profile,
        as_of=datetime.fromisoformat("2026-08-21T05:00:00+01:00"),
        source_snapshot=rules,
    )
    big = by_id(result, "INVESTNI-BIG-2026-09")
    assert big["decision"] == "NEEDS_EVIDENCE"
    assert "Current finance and cash-flow evidence" in big["missing_evidence"]


def test_evaluation_never_grants_submission_authority_or_records_actions():
    result = evaluate("SYNTHETIC-NI-AI-SME")
    assert result["controls"]["submission_authority"] is False
    assert result["controls"]["human_approval_required_before_external_action"] is True
    assert set(result["external_actions"].values()) == {0}
    assert all(row["submission_allowed"] is False for row in result["route_results"])


def test_closed_route_is_not_recommended_for_submission():
    rules = load("rules_snapshot_20260821.json")
    profile = load("synthetic_companies.json")["profiles"][0]
    result = StateSupportEligibilityAgent(rules["routes"]).evaluate_portfolio(
        profile,
        as_of=datetime.fromisoformat("2026-08-22T05:00:00+01:00"),
        source_snapshot=rules,
    )
    assert by_id(result, "GO-SUCCEED-ULTIMATE-PITCH-2026")["decision"] == "CLOSED"
