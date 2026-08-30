from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import socket
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import pytest
import requests

from Kings_Accounting_Suite.tools.quickbooks_accounting_integration import (
    AureonCanonicalAccountingEvent,
    ConfigurationError,
    DPAPIClientCredentialVault,
    DPAPITokenVault,
    MutationBlockedError,
    OAuthStateError,
    QuickBooksAPIClient,
    QuickBooksAuditWriter,
    QuickBooksClientCredentials,
    QuickBooksConfig,
    QuickBooksLocalCredentialReceiver,
    QuickBooksLocalOAuthCallbackServer,
    QuickBooksMutationApproval,
    QuickBooksOAuthClient,
    QuickBooksStatusStore,
    QuickBooksTokenSet,
    QuickBooksWebhookVerifier,
    WebhookVerificationError,
    bind_config_to_tokens,
    build_aureon_quickbooks_reconciliation_plan,
    build_quickbooks_browser_observation,
    build_quickbooks_production_readiness,
    build_recommended_quickbooks_chart,
    payload_sha256,
)

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)


class FakeResponse:
    def __init__(self, payload: Any, status_code: int = 200, reason: str = "OK"):
        self.payload = payload
        self.status_code = status_code
        self.reason = reason

    def json(self) -> Any:
        return self.payload


class FakeTransport:
    def __init__(self, responses: list[FakeResponse] | None = None):
        self.responses = list(responses or [])
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse({"QueryResponse": {}})


def config(*, allow_mutation: bool = False) -> QuickBooksConfig:
    return QuickBooksConfig(
        client_id="client-id-123",
        client_secret="client-secret-456",
        redirect_uri="https://example.test/intuit/callback",
        realm_id="9341457629693092",
        environment="production",
        allow_mutation=allow_mutation,
    )


def tokens(*, environment: str = "production") -> QuickBooksTokenSet:
    return QuickBooksTokenSet(
        access_token="access-secret",
        refresh_token="refresh-secret",
        access_expires_at="2099-01-01T00:00:00Z",
        refresh_expires_at="2099-02-01T00:00:00Z",
        realm_id="9341457629693092",
        environment=environment,
    )


def canonical_event(payload: dict[str, Any], *, event_id: str = "aureon-accounting-event-1"):
    return AureonCanonicalAccountingEvent.create(
        event_id=event_id,
        operation="create",
        entity="Vendor",
        payload=payload,
        evidence_sha256=[hashlib.sha256(b"source-evidence").hexdigest()],
        now=NOW,
    )


def test_config_uses_official_production_base_and_redacts_secret() -> None:
    value = config()
    assert value.api_base_url == "https://quickbooks.api.intuit.com"
    assert "client-secret-456" not in repr(value)
    assert value.redacted()["client_secret"] == "<redacted>"


def test_config_rejects_insecure_non_local_redirect() -> None:
    with pytest.raises(ConfigurationError):
        QuickBooksConfig(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://example.test/callback",
        )


def test_production_config_rejects_localhost_redirect() -> None:
    with pytest.raises(ConfigurationError, match="Production"):
        QuickBooksConfig(
            client_id="client",
            client_secret="secret",
            redirect_uri="http://localhost:8765/callback",
            environment="production",
        )


def test_secured_token_vault_supplies_realm_and_rejects_mismatch() -> None:
    unbound = QuickBooksConfig(
        client_id="client",
        client_secret="secret",
        redirect_uri="http://localhost:8765/callback",
        environment="sandbox",
    )
    sandbox_tokens = tokens(environment="sandbox")
    bound = bind_config_to_tokens(unbound, sandbox_tokens)
    assert bound.realm_id == sandbox_tokens.realm_id
    with pytest.raises(ConfigurationError, match="does not match"):
        bind_config_to_tokens(config(), QuickBooksTokenSet(**{**tokens().__dict__, "realm_id": "other"}))
    with pytest.raises(ConfigurationError, match="environment"):
        bind_config_to_tokens(config(), tokens(environment="sandbox"))


def test_oauth_state_is_signed_expiring_and_callback_bound() -> None:
    oauth = QuickBooksOAuthClient(config())
    state = oauth.create_state(now=NOW)
    oauth.validate_state(state, now=NOW + timedelta(minutes=9))
    with pytest.raises(OAuthStateError):
        oauth.validate_state(f"{state[:-1]}x", now=NOW)
    with pytest.raises(OAuthStateError):
        oauth.validate_state(state, now=NOW + timedelta(minutes=11))


def test_oauth_token_response_never_exposes_secrets_in_repr_or_redacted_form() -> None:
    value = QuickBooksTokenSet.from_oauth_response(
        {
            "access_token": "live-access",
            "refresh_token": "live-refresh",
            "expires_in": 3600,
            "x_refresh_token_expires_in": 7200,
        },
        realm_id="realm",
        now=NOW,
    )
    assert "live-access" not in repr(value)
    assert "live-refresh" not in repr(value)
    assert "live-access" not in json.dumps(value.redacted())
    assert value.redacted()["access_token"] == "<redacted>"


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI is the local production vault")
def test_dpapi_token_vault_round_trip_is_ciphertext_only(tmp_path: Path) -> None:
    vault_path = tmp_path / "quickbooks_tokens.dpapi.json"
    vault = DPAPITokenVault(vault_path)
    vault.save(tokens())
    raw = vault_path.read_text(encoding="utf-8")
    assert "access-secret" not in raw
    assert "refresh-secret" not in raw
    restored = vault.load()
    assert restored.access_token == "access-secret"
    assert restored.refresh_token == "refresh-secret"
    assert restored.environment == "production"


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI is the local production vault")
def test_dpapi_client_credential_vault_loads_config_without_plaintext(tmp_path: Path) -> None:
    vault_path = tmp_path / "quickbooks_client_credentials.dpapi.json"
    vault = DPAPIClientCredentialVault(vault_path)
    vault.save(QuickBooksClientCredentials(client_id="client-id-value", client_secret="client-secret-value"))
    raw = vault_path.read_text(encoding="utf-8")
    assert "client-id-value" not in raw
    assert "client-secret-value" not in raw

    loaded = vault.load()
    assert loaded.client_id == "client-id-value"
    assert loaded.client_secret == "client-secret-value"
    configured = QuickBooksConfig.from_env(
        {
            "QUICKBOOKS_CLIENT_CREDENTIAL_VAULT": str(vault_path),
            "QUICKBOOKS_REDIRECT_URI": "http://localhost:8765/quickbooks/oauth/callback",
            "QUICKBOOKS_ENVIRONMENT": "sandbox",
        }
    )
    assert configured.client_id == "client-id-value"
    assert configured.client_secret == "client-secret-value"


def test_local_oauth_callback_captures_exact_callback_without_logging_secrets() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    callback = QuickBooksLocalOAuthCallbackServer(
        f"http://127.0.0.1:{port}/quickbooks/oauth/callback"
    )
    outcome: dict[str, Any] = {}

    def wait_for_callback() -> None:
        outcome["result"] = callback.wait_for_callback(timeout_seconds=5)

    thread = threading.Thread(target=wait_for_callback)
    thread.start()
    query = urlencode({"code": "short-lived-code", "state": "signed-state", "realmId": "9341457629693092"})
    for _ in range(30):
        try:
            response = requests.get(
                f"http://127.0.0.1:{port}/quickbooks/oauth/callback?{query}",
                timeout=1,
            )
            break
        except requests.ConnectionError:
            time.sleep(0.02)
    else:
        pytest.fail("Local OAuth callback server did not start")
    thread.join(timeout=2)

    assert response.status_code == 200
    result = outcome["result"]
    assert result.code == "short-lived-code"
    assert result.state == "signed-state"
    assert result.realm_id == "9341457629693092"
    assert result.redacted()["code"] == "<redacted>"


def test_local_oauth_callback_rejects_non_local_or_ambiguous_uri() -> None:
    with pytest.raises(ConfigurationError, match="localhost"):
        QuickBooksLocalOAuthCallbackServer("https://example.com/callback")
    with pytest.raises(ConfigurationError, match="query or fragment"):
        QuickBooksLocalOAuthCallbackServer("http://localhost:8765/callback?unsafe=true")


def test_loopback_credential_receiver_saves_without_echoing_secret() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    class MemoryVault:
        saved: QuickBooksClientCredentials | None = None

        def save(self, credentials: QuickBooksClientCredentials) -> Path:
            self.saved = credentials
            return Path("memory")

    vault = MemoryVault()
    receiver = QuickBooksLocalCredentialReceiver(nonce="one-use-test-nonce", port=port)
    outcome: dict[str, Any] = {}

    def receive() -> None:
        outcome["credentials"] = receiver.receive_and_save(vault, timeout_seconds=5)  # type: ignore[arg-type]

    thread = threading.Thread(target=receive)
    thread.start()
    for _ in range(30):
        try:
            response = requests.post(
                f"http://127.0.0.1:{port}/quickbooks/client-credentials",
                headers={"X-Aureon-Nonce": "one-use-test-nonce"},
                json={"client_id": "client-id-value", "client_secret": "client-secret-value"},
                timeout=1,
            )
            break
        except requests.ConnectionError:
            time.sleep(0.02)
    else:
        pytest.fail("Local credential receiver did not start")
    thread.join(timeout=2)

    assert response.status_code == 200
    assert "client-secret-value" not in response.text
    assert vault.saved is not None
    assert vault.saved.client_id == "client-id-value"
    assert vault.saved.client_secret == "client-secret-value"
    assert outcome["credentials"].redacted()["client_secret"] == "<redacted>"


def test_read_query_allowlist_and_bearer_header() -> None:
    transport = FakeTransport([FakeResponse({"QueryResponse": {"Account": [{"Id": "1"}]}})])
    client = QuickBooksAPIClient(config(), tokens(), transport=transport)
    result = client.query("SELECT * FROM Account MAXRESULTS 1000")
    assert result["QueryResponse"]["Account"][0]["Id"] == "1"
    call = transport.calls[0]
    assert call["method"] == "GET"
    assert call["url"].startswith("https://quickbooks.api.intuit.com/v3/company/9341457629693092/query")
    assert call["headers"]["Authorization"] == "Bearer access-secret"
    with pytest.raises(ConfigurationError):
        client.query("DELETE FROM Account")
    with pytest.raises(ConfigurationError):
        client.query("SELECT * FROM SecretEntity")


def test_mutation_is_blocked_by_default_even_with_approval() -> None:
    payload = {"DisplayName": "Controlled vendor"}
    approval = QuickBooksMutationApproval.create(
        approved_by="Company owner",
        realm_id=config().realm_id,
        operation="create",
        entity="Vendor",
        payload=payload,
        canonical_event=canonical_event(payload),
        idempotency_key="approval-request-1",
        signing_key="approval-secret",
    )
    client = QuickBooksAPIClient(config(), tokens(), approval_signing_key="approval-secret")
    with pytest.raises(MutationBlockedError, match="disabled"):
        client.mutate(operation="create", entity="Vendor", payload=payload, approval=approval)


def test_mutation_requires_valid_payload_bound_approval_and_idempotency_key() -> None:
    transport = FakeTransport([FakeResponse({"Vendor": {"Id": "22"}})])
    payload = {"DisplayName": "Controlled vendor"}
    approval = QuickBooksMutationApproval.create(
        approved_by="Company owner",
        realm_id=config().realm_id,
        operation="create",
        entity="Vendor",
        payload=payload,
        canonical_event=canonical_event(payload),
        idempotency_key="approval-request-2",
        signing_key="approval-secret",
    )
    client = QuickBooksAPIClient(
        config(allow_mutation=True),
        tokens(),
        transport=transport,
        approval_signing_key="approval-secret",
    )
    with pytest.raises(MutationBlockedError, match="differs"):
        client.mutate(
            operation="create",
            entity="Vendor",
            payload={"DisplayName": "Unapproved vendor"},
            approval=approval,
            canonical_event=canonical_event(payload),
        )
    result = client.mutate(
        operation="create",
        entity="Vendor",
        payload=payload,
        approval=approval,
        canonical_event=canonical_event(payload),
    )
    assert result["Vendor"]["Id"] == "22"
    assert transport.calls[-1]["params"]["requestid"] == "approval-request-2"


def test_audit_receipt_contains_hash_and_no_response_payload_or_tokens(tmp_path: Path) -> None:
    writer = QuickBooksAuditWriter(tmp_path)
    response = {"Account": [{"Id": "1", "Name": "Bank"}], "access_token": "must-not-leak"}
    path = writer.write(
        action="query-Account",
        request_summary={"authorization": "Bearer must-not-leak"},
        response_payload=response,
        mutation=False,
    )
    raw = path.read_text(encoding="utf-8")
    receipt = json.loads(raw)
    assert receipt["payload_persisted"] is False
    assert receipt["request"]["authorization"] == "<redacted>"
    assert "must-not-leak" not in raw
    assert '"Name": "Bank"' not in raw
    assert len(receipt["response_sha256"]) == 64


def test_aureon_plan_keeps_filing_and_finance_actions_manual(tmp_path: Path) -> None:
    plan = build_aureon_quickbooks_reconciliation_plan(active_grant_ledger=tmp_path)
    assert plan["entity"]["company_number"] == "NI696693"
    assert plan["control_mode"]["default"] == "read_only"
    assert plan["control_mode"]["hmrc_submission"] == "manual_only"
    assert plan["control_mode"]["companies_house_filing"] == "manual_only"
    assert plan["control_mode"]["bank_or_billing_change"] == "manual_only"
    assert plan["control_mode"]["canonical_system"] == "aureon_os"
    assert plan["control_mode"]["quickbooks_may_overwrite_aureon_truth"] is False
    assert plan["grants_and_rd"]["active_grant_ledger"] == str(tmp_path.resolve())
    assert any("main source of income" in item for item in plan["human_decisions_required"])


def test_status_store_is_atomic_hashable_and_secret_free(tmp_path: Path) -> None:
    store = QuickBooksStatusStore(tmp_path / "quickbooks" / "status.json")
    observation = build_quickbooks_browser_observation(
        legal_name="R&A Consulting and Brokerage Services Ltd",
        bank_feed_connected=True,
        bank_provider="Zempler Bank (UK)",
        pending_transaction_count=911,
        displayed_transaction_count=401,
        chart_account_count=58,
        mixed_use_review_required=True,
        balance_sheet_nonzero_account_count=1,
        developer_terms_state="awaiting_owner_acceptance",
    )
    store.write(observation)
    status = store.read()
    assert status["company"]["legal_name"] == "R&A CONSULTING AND BROKERAGE SERVICES LTD"
    assert status["bank_feed"]["ownership_status"] == "mixed_use_owner_accountant_review_required"
    assert status["bank_feed"]["aureon_posted_transaction_count"] == 0
    assert status["authority"]["canonical_system"] == "aureon_os"
    assert status["authority"]["quickbooks_may_overwrite_aureon_truth"] is False
    assert status["api"]["developer_terms_state"] == "awaiting_owner_acceptance"
    assert status["controls"]["external_legal_agreements"] == "owner_confirmation_required"
    assert status["chart_of_accounts"]["account_count"] == 58
    assert status["reports"]["profit_and_loss_current_period_has_data"] is False
    assert status["reports"]["balance_sheet_nonzero_account_count"] == 1
    assert status["tax_features"]["cis_enabled"] is False
    assert status["tax_features"]["vat_enabled"] is False
    assert status["tax_features"]["payroll_enabled"] is False
    assert len(status["status_sha256"]) == 64
    assert "5600" not in json.dumps(status)


def test_browser_observation_rejects_unknown_developer_terms_state() -> None:
    with pytest.raises(ValueError, match="developer_terms_state"):
        build_quickbooks_browser_observation(
            legal_name="R&A CONSULTING AND BROKERAGE SERVICES LTD",
            bank_feed_connected=False,
            bank_provider="",
            pending_transaction_count=0,
            displayed_transaction_count=0,
            chart_account_count=0,
            mixed_use_review_required=False,
            developer_terms_state="operator_accepted_without_owner",
        )


def test_production_readiness_requires_every_live_connection_gate() -> None:
    gated = build_quickbooks_production_readiness(
        live_company_observed=True,
        legal_name_match_observed=True,
        subscription_state="payment_scheduled_not_settled",
        bank_feed_consent_state="consent_observed_import_readback_pending",
        developer_session_state="expired",
        sandbox_test_state="provider_blocked",
        production_app_assessment_state="not_observed",
        production_credentials_state="not_observed",
        verified_public_urls={
            "privacy_policy": "https://example.test/privacy",
            "host_domain": "https://example.test",
        },
    )
    assert gated["connection_state"] == "live_qbo_company_observed_production_api_gated"
    assert gated["api_gate"]["production_oauth_ready"] is False
    assert gated["api_gate"]["read_only_sync_ready"] is False
    assert gated["authority"]["quickbooks_mutations_authorised"] is False
    assert (
        gated["developer_gate"]["public_urls"]["end_user_licence_agreement"]["state"]
        == "missing_or_unverified"
    )


def test_production_readiness_can_reach_read_only_without_authorising_writes() -> None:
    public_urls = {
        "privacy_policy": "https://example.test/privacy",
        "end_user_licence_agreement": "https://example.test/terms",
        "host_domain": "https://example.test",
        "launch": "https://example.test/accounts",
        "disconnect": "https://example.test/quickbooks/disconnect",
        "connect_reconnect": "https://example.test/quickbooks/connect",
    }
    ready = build_quickbooks_production_readiness(
        live_company_observed=True,
        legal_name_match_observed=True,
        subscription_state="active_provider_verified",
        bank_feed_consent_state="connected_readback_verified",
        developer_session_state="active",
        sandbox_test_state="oauth_verified",
        production_app_assessment_state="approved",
        production_credentials_state="secured_in_dpapi",
        production_redirect_uri="https://example.test/quickbooks/callback",
        verified_public_urls=public_urls,
        oauth_state="connected",
        company_info_readback="verified",
    )
    assert ready["connection_state"] == "live_api_readback_verified"
    assert ready["api_gate"]["read_only_sync_ready"] is True
    assert ready["api_gate"]["mutation_projection_ready"] is False


def test_intuit_webhook_signature_is_verified_and_only_queues_read_refresh() -> None:
    body = json.dumps(
        {
            "eventNotifications": [
                {
                    "realmId": "9341457629693092",
                    "dataChangeEvent": {
                        "entities": [
                            {
                                "name": "Invoice",
                                "id": "44",
                                "operation": "Update",
                                "lastUpdated": "2026-07-31T10:00:00Z",
                            },
                            {"name": "Unsupported", "id": "99", "operation": "Create"},
                        ]
                    },
                }
            ]
        },
        separators=(",", ":"),
    ).encode()
    signature = base64.b64encode(
        hmac.new(b"verifier-secret", body, hashlib.sha256).digest()
    ).decode()
    receipt = QuickBooksWebhookVerifier(
        "verifier-secret",
        expected_realm_id="9341457629693092",
    ).verify(body, signature)
    assert receipt["signature_verified"] is True
    assert receipt["change_count"] == 1
    assert receipt["action"] == "queue_read_only_refresh"
    assert receipt["mutations_triggered"] is False
    assert receipt["authority"] == "aureon_os"
    assert receipt["changes"][0]["entity_id_sha256"] == hashlib.sha256(b"44").hexdigest()
    with pytest.raises(WebhookVerificationError):
        QuickBooksWebhookVerifier("verifier-secret").verify(body, "wrong")


def test_quickbooks_chart_plan_is_staged_and_requires_evidence() -> None:
    plan = build_recommended_quickbooks_chart()
    names = {item["name"] for item in plan["accounts"]}
    assert plan["status"] == "staged_not_applied"
    assert plan["controls"]["creates_quickbooks_accounts"] is False
    assert plan["controls"]["canonical_system"] == "aureon_os"
    assert plan["controls"]["enables_cis"] is False
    assert "Deferred grant income" in names
    assert "R&D subcontractor costs" in names
    assert "CIS deductions suffered" in names


def test_qbo_write_requires_matching_canonical_aureon_event() -> None:
    payload = {"DisplayName": "Controlled vendor"}
    event = canonical_event(payload)
    approval = QuickBooksMutationApproval.create(
        approved_by="Company owner",
        realm_id=config().realm_id,
        operation="create",
        entity="Vendor",
        payload=payload,
        canonical_event=event,
        idempotency_key="canonical-event-request",
        signing_key="approval-secret",
        now=NOW,
    )
    client = QuickBooksAPIClient(
        config(allow_mutation=True),
        tokens(),
        approval_signing_key="approval-secret",
    )
    with pytest.raises(MutationBlockedError, match="canonical Aureon"):
        client.mutate(operation="create", entity="Vendor", payload=payload, approval=approval)
    different_event = canonical_event(payload, event_id="different-event")
    with pytest.raises(MutationBlockedError, match="approved Aureon canonical event"):
        client.mutate(
            operation="create",
            entity="Vendor",
            payload=payload,
            approval=approval,
            canonical_event=different_event,
        )
