"""Tests for the company-profile surface (the organization behind Aureon OS).

The profile is registry-as-data transcribed from COMPANY.md — verifiable public facts,
never fabricated. It is served at GET /api/org (distinct from /api/company, the agent
workforce roster) and stamped real_derived with a provenance block.
"""

from __future__ import annotations

from aureon.saas.company_profile import build_company_profile


def test_profile_carries_the_registered_company_facts():
    p = build_company_profile()
    ident = p["identity"]
    assert ident["registered_name"] == "R&A Consulting and Brokerage Services Ltd"
    assert ident["company_number"] == "NI696693"
    assert ident["trading_name"] == "Aureon Zorza Technologies"
    assert ident["registered_office"].startswith("Belfast")
    assert ident["website"].startswith("https://")
    assert p["truth_status"] == "real_derived"
    assert p["source"] == "COMPANY.md"


def test_profile_has_recognition_community_and_contact():
    p = build_company_profile()
    assert "Silver" in p["recognition"]["award"]
    assert p["recognition"]["date"] == "2025-07-21"
    assert any("Street Soccer" in x for x in p["community"]["partners"])
    assert p["contact"]["license"] == "MIT"
    assert p["disclaimer"]


def test_profile_is_deterministic_and_pure_data():
    # Pure registry-as-data: two calls are equal, and mutating the result does not
    # bleed into the next call (defensive copies).
    a = build_company_profile()
    b = build_company_profile()
    assert a == b
    a["identity"]["company_number"] = "TAMPERED"
    a["community"]["partners"].append("nope")
    assert build_company_profile()["identity"]["company_number"] == "NI696693"
    assert "nope" not in build_company_profile()["community"]["partners"]


def test_org_route_serves_profile_stamped(monkeypatch):
    # The gateway route mounts the profile, guarded + stamped, distinct from /api/company.
    try:
        from flask import Flask
    except Exception:  # pragma: no cover - flask always present in the operator extra
        import pytest

        pytest.skip("flask not available")

    from aureon.saas.gateway import register_saas_routes

    monkeypatch.delenv("AUREON_SUPABASE_JWT_SECRET", raising=False)  # tenancy bridge off → guard passes
    app = Flask(__name__)
    register_saas_routes(app)
    client = app.test_client()

    resp = client.get("/api/org")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["identity"]["company_number"] == "NI696693"
    assert body["truth_status"] == "real_derived"
    assert "provenance" in body  # _stamp attaches the provenance block
