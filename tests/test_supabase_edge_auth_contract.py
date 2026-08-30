from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AUDITOR_PATH = REPO_ROOT / "scripts" / "validation" / "audit_supabase_edge_auth.py"


def _load_auditor():
    spec = importlib.util.spec_from_file_location("supabase_edge_auth_audit", AUDITOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_privileged_mutations_require_gateway_jwt_or_reviewed_custom_auth() -> None:
    auditor = _load_auditor()
    matrix = auditor.build_auth_matrix(REPO_ROOT)

    assert matrix
    assert auditor.policy_violations(matrix) == []


def test_reviewed_custom_auth_allowlist_is_source_bound_and_minimal() -> None:
    auditor = _load_auditor()
    matrix = auditor.build_auth_matrix(REPO_ROOT)
    by_name = {row["function"]: row for row in matrix}

    assert set(auditor.REVIEWED_CUSTOM_AUTH) == {"ingest-kelly-computation"}
    kelly = by_name["ingest-kelly-computation"]
    assert kelly["verify_jwt"] is False
    assert kelly["privileged_mutation"] is True
    assert kelly["custom_auth"] == "supabase_auth_get_user"
    assert kelly["custom_auth_allowlisted"] is True
    assert kelly["protection"] == "reviewed_custom:supabase_auth_get_user"


def test_cors_authorization_header_is_not_authentication() -> None:
    auditor = _load_auditor()
    matrix = auditor.build_auth_matrix(REPO_ROOT)
    by_name = {row["function"]: row for row in matrix}

    telescope = by_name["ingest-telescope-state"]
    assert telescope["cors_mentions_authorization"] is True
    assert telescope["custom_auth"] == "none"
    assert telescope["protection"] == "gateway_jwt"


def test_inbound_shared_secret_checks_are_distinguished_from_provider_keys() -> None:
    auditor = _load_auditor()
    matrix = auditor.build_auth_matrix(REPO_ROOT)
    by_name = {row["function"]: row for row in matrix}

    assert by_name["ingest-trades"]["custom_auth"] == "shared_secret_exact_compare"
    assert by_name["ingest-terminal-state"]["custom_auth"] == "shared_secret_exact_compare"
    assert by_name["fetch-binance-market-data"]["custom_auth"] == "none"


def test_optional_auth_probe_does_not_replace_the_gateway_gate() -> None:
    auditor = _load_auditor()
    matrix = auditor.build_auth_matrix(REPO_ROOT)
    by_name = {row["function"]: row for row in matrix}

    health = by_name["backend-health-check"]
    assert health["verify_jwt"] is True
    assert health["custom_auth"] == "none"
    assert health["custom_auth_allowlisted"] is False
    assert health["privileged_mutation"] is True
    assert "sync-harmonic-nexus" in health["invoked_edge_functions"]
    assert health["protection"] == "gateway_jwt"
