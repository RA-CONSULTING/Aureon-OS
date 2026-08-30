"""QuickBooks Online projection/read-back adapter for Aureon's accounting organism.

The integration is deliberately read-only by default. OAuth tokens are kept in
memory or in a Windows DPAPI vault; they are never written to receipts or logs.
QuickBooks mutations require all of the following:

* ``allow_mutation=True`` in the runtime configuration;
* an expiring HMAC-signed approval bound to the realm, operation, entity,
  payload digest, and idempotency key; and
* a matching ``AUREON_ACCOUNTING_APPROVAL_HMAC_KEY`` supplied at runtime.

HMRC submissions, Companies House filings, payments, bank changes, and payroll
remain outside this module. Aureon OS is the canonical accounting/evidence
authority. QuickBooks is a downstream projection and observation surface only.
No QBO import, suggestion, balance, or webhook can overwrite Aureon's truth.
"""

from __future__ import annotations

import argparse
import base64
import ctypes
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import webbrowser
from dataclasses import asdict, dataclass, field, replace
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import parse_qs, urlencode, urlparse

import requests

OAUTH_AUTHORIZE_URL = "https://appcenter.intuit.com/connect/oauth2"
OAUTH_TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
OAUTH_REVOKE_URL = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"
ACCOUNTING_SCOPE = "com.intuit.quickbooks.accounting"
DEFAULT_LOCAL_REDIRECT_URI = "http://localhost:8765/callback"
API_BASE_URLS = {
    "sandbox": "https://sandbox-quickbooks.api.intuit.com",
    "production": "https://quickbooks.api.intuit.com",
}
READ_ENTITY_ALLOWLIST = frozenset(
    {
        "Account",
        "Bill",
        "BillPayment",
        "CompanyInfo",
        "CreditMemo",
        "Customer",
        "Deposit",
        "Employee",
        "Estimate",
        "Invoice",
        "JournalEntry",
        "Payment",
        "Purchase",
        "PurchaseOrder",
        "RefundReceipt",
        "SalesReceipt",
        "TaxCode",
        "TaxRate",
        "Transfer",
        "Vendor",
    }
)
REPORT_ALLOWLIST = frozenset(
    {
        "BalanceSheet",
        "CashFlow",
        "ProfitAndLoss",
        "TransactionList",
        "TrialBalance",
        "VendorExpenses",
    }
)
MUTATION_ENTITY_ALLOWLIST = frozenset(
    {
        "Account",
        "Bill",
        "Customer",
        "Invoice",
        "JournalEntry",
        "Payment",
        "Purchase",
        "SalesReceipt",
        "Vendor",
    }
)
SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "authorization",
        "client_secret",
        "code",
        "refresh_token",
        "signature",
    }
)


class QuickBooksIntegrationError(RuntimeError):
    """Base exception for controlled QuickBooks failures."""


class ConfigurationError(QuickBooksIntegrationError):
    """Raised when required configuration is absent or unsafe."""


class OAuthStateError(QuickBooksIntegrationError):
    """Raised when an OAuth callback state cannot be trusted."""


class MutationBlockedError(QuickBooksIntegrationError):
    """Raised when a QuickBooks mutation has not passed every control gate."""


class WebhookVerificationError(QuickBooksIntegrationError):
    """Raised when an Intuit webhook signature or envelope is untrusted."""


class HTTPResponse(Protocol):
    status_code: int
    reason: str

    def json(self) -> Any: ...


class HTTPTransport(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> HTTPResponse: ...


class RequestsTransport:
    """Small requests adapter that is replaceable in tests."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        return self.session.request(method, url, **kwargs)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def payload_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): ("<redacted>" if str(key).lower() in SENSITIVE_KEYS else _redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact(item) for item in value)
    return value


def _require_non_placeholder(name: str, value: str) -> str:
    cleaned = value.strip()
    if not cleaned or cleaned.lower() in {"changeme", "example", "placeholder", "todo"}:
        raise ConfigurationError(f"{name} is required and must not be a placeholder")
    return cleaned


@dataclass(frozen=True)
class QuickBooksConfig:
    client_id: str
    client_secret: str = field(repr=False)
    redirect_uri: str
    realm_id: str = ""
    environment: str = "sandbox"
    minor_version: int = 75
    timeout_seconds: int = 30
    allow_mutation: bool = False

    def __post_init__(self) -> None:
        _require_non_placeholder("QUICKBOOKS_CLIENT_ID", self.client_id)
        _require_non_placeholder("QUICKBOOKS_CLIENT_SECRET", self.client_secret)
        redirect_uri = _require_non_placeholder("QUICKBOOKS_REDIRECT_URI", self.redirect_uri)
        if self.environment not in API_BASE_URLS:
            raise ConfigurationError("QUICKBOOKS_ENVIRONMENT must be sandbox or production")
        parsed_redirect = urlparse(redirect_uri)
        if self.environment == "production":
            if parsed_redirect.scheme != "https" or parsed_redirect.hostname in {
                "localhost",
                "127.0.0.1",
            }:
                raise ConfigurationError(
                    "Production QUICKBOOKS_REDIRECT_URI must use HTTPS on a public host"
                )
        elif not redirect_uri.startswith(("https://", "http://localhost", "http://127.0.0.1")):
            raise ConfigurationError("QUICKBOOKS_REDIRECT_URI must use HTTPS or a localhost callback")
        if not 1 <= int(self.minor_version) <= 999:
            raise ConfigurationError("QUICKBOOKS_MINOR_VERSION must be a positive API minor version")
        if self.timeout_seconds < 1:
            raise ConfigurationError("QuickBooks timeout must be positive")

    @property
    def api_base_url(self) -> str:
        return API_BASE_URLS[self.environment]

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        require_realm: bool = False,
    ) -> QuickBooksConfig:
        source = env or os.environ
        realm_id = source.get("QUICKBOOKS_REALM_ID", "").strip()
        environment = source.get("QUICKBOOKS_ENVIRONMENT", "sandbox").strip().lower()
        if require_realm:
            _require_non_placeholder("QUICKBOOKS_REALM_ID", realm_id)
        client_id = source.get("QUICKBOOKS_CLIENT_ID", "").strip()
        client_secret = source.get("QUICKBOOKS_CLIENT_SECRET", "").strip()
        credential_vault_path = Path(
            source.get("QUICKBOOKS_CLIENT_CREDENTIAL_VAULT", "").strip()
            or _default_client_credential_vault_path(environment)
        )
        if not client_id and not client_secret and credential_vault_path.exists():
            credentials = DPAPIClientCredentialVault(credential_vault_path).load()
            if credentials.environment != environment:
                raise ConfigurationError(
                    "QuickBooks client credential vault environment does not match QUICKBOOKS_ENVIRONMENT"
                )
            client_id = credentials.client_id
            client_secret = credentials.client_secret
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=source.get("QUICKBOOKS_REDIRECT_URI", "").strip() or DEFAULT_LOCAL_REDIRECT_URI,
            realm_id=realm_id,
            environment=environment,
            minor_version=int(source.get("QUICKBOOKS_MINOR_VERSION", "75")),
            timeout_seconds=int(source.get("QUICKBOOKS_TIMEOUT_SECONDS", "30")),
            allow_mutation=source.get("QUICKBOOKS_ALLOW_MUTATION", "").strip().lower()
            in {"1", "true", "yes"},
        )

    def redacted(self) -> dict[str, Any]:
        return {
            "client_id_suffix": self.client_id[-6:],
            "client_secret": "<redacted>",
            "redirect_uri": self.redirect_uri,
            "realm_id": self.realm_id,
            "environment": self.environment,
            "minor_version": self.minor_version,
            "timeout_seconds": self.timeout_seconds,
            "allow_mutation": self.allow_mutation,
        }


@dataclass
class QuickBooksTokenSet:
    access_token: str = field(repr=False)
    refresh_token: str = field(repr=False)
    access_expires_at: str
    refresh_expires_at: str
    realm_id: str
    environment: str = "sandbox"
    token_type: str = "bearer"

    def __post_init__(self) -> None:
        if self.environment not in API_BASE_URLS:
            raise ConfigurationError("QuickBooks token environment must be sandbox or production")

    @classmethod
    def from_oauth_response(
        cls,
        payload: Mapping[str, Any],
        *,
        realm_id: str,
        environment: str = "sandbox",
        now: datetime | None = None,
    ) -> QuickBooksTokenSet:
        issued_at = now or _utc_now()
        access_token = _require_non_placeholder("OAuth access_token", str(payload.get("access_token", "")))
        refresh_token = _require_non_placeholder("OAuth refresh_token", str(payload.get("refresh_token", "")))
        access_seconds = int(payload.get("expires_in", 3600))
        refresh_seconds = int(payload.get("x_refresh_token_expires_in", 8_726_400))
        return cls(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=_iso(issued_at + timedelta(seconds=access_seconds)),
            refresh_expires_at=_iso(issued_at + timedelta(seconds=refresh_seconds)),
            realm_id=_require_non_placeholder("OAuth realmId", realm_id),
            environment=environment,
            token_type=str(payload.get("token_type", "bearer")).lower(),
        )

    def access_expiring(self, *, now: datetime | None = None, leeway_seconds: int = 90) -> bool:
        return _parse_time(self.access_expires_at) <= (now or _utc_now()) + timedelta(seconds=leeway_seconds)

    def refresh_expired(self, *, now: datetime | None = None) -> bool:
        return _parse_time(self.refresh_expires_at) <= (now or _utc_now())

    def secret_payload(self) -> dict[str, Any]:
        """Return the secret-bearing representation for an approved vault only."""
        return asdict(self)

    def redacted(self) -> dict[str, Any]:
        return {
            "access_token": "<redacted>",
            "refresh_token": "<redacted>",
            "access_expires_at": self.access_expires_at,
            "refresh_expires_at": self.refresh_expires_at,
            "realm_id": self.realm_id,
            "environment": self.environment,
            "token_type": self.token_type,
        }


class QuickBooksOAuthClient:
    """OAuth 2.0 authorization, exchange, refresh, and revocation."""

    STATE_TTL_SECONDS = 600

    def __init__(self, config: QuickBooksConfig, transport: HTTPTransport | None = None):
        self.config = config
        self.transport = transport or RequestsTransport()

    def create_state(self, *, now: datetime | None = None) -> str:
        issued_at = int((now or _utc_now()).timestamp())
        body = f"{issued_at}.{secrets.token_urlsafe(24)}"
        signature = hmac.new(
            self.config.client_secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return f"{body}.{signature}"

    def validate_state(self, state: str, *, now: datetime | None = None) -> None:
        try:
            issued_raw, nonce, signature = state.split(".", 2)
            issued_at = int(issued_raw)
        except (TypeError, ValueError) as exc:
            raise OAuthStateError("OAuth state is malformed") from exc
        body = f"{issued_raw}.{nonce}"
        expected = hmac.new(
            self.config.client_secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise OAuthStateError("OAuth state signature does not match")
        age = int((now or _utc_now()).timestamp()) - issued_at
        if age < -30 or age > self.STATE_TTL_SECONDS:
            raise OAuthStateError("OAuth state has expired or has an invalid timestamp")

    def authorization_url(self, *, state: str | None = None) -> tuple[str, str]:
        trusted_state = state or self.create_state()
        params = {
            "client_id": self.config.client_id,
            "response_type": "code",
            "scope": ACCOUNTING_SCOPE,
            "redirect_uri": self.config.redirect_uri,
            "state": trusted_state,
        }
        return f"{OAUTH_AUTHORIZE_URL}?{urlencode(params)}", trusted_state

    def _token_request(self, data: Mapping[str, str], *, realm_id: str) -> QuickBooksTokenSet:
        response = self.transport.request(
            "POST",
            OAUTH_TOKEN_URL,
            auth=(self.config.client_id, self.config.client_secret),
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
            data=dict(data),
            timeout=self.config.timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise QuickBooksIntegrationError(
                f"QuickBooks OAuth request failed with HTTP {response.status_code} {response.reason}"
            )
        payload = response.json()
        if not isinstance(payload, Mapping):
            raise QuickBooksIntegrationError("QuickBooks OAuth response was not a JSON object")
        return QuickBooksTokenSet.from_oauth_response(
            payload,
            realm_id=realm_id,
            environment=self.config.environment,
        )

    def exchange_code(
        self,
        *,
        code: str,
        returned_state: str,
        expected_state: str,
        realm_id: str,
    ) -> QuickBooksTokenSet:
        if not hmac.compare_digest(returned_state, expected_state):
            raise OAuthStateError("Returned OAuth state does not match the initiating state")
        self.validate_state(returned_state)
        return self._token_request(
            {
                "grant_type": "authorization_code",
                "code": _require_non_placeholder("OAuth authorization code", code),
                "redirect_uri": self.config.redirect_uri,
            },
            realm_id=realm_id,
        )

    def refresh(self, tokens: QuickBooksTokenSet) -> QuickBooksTokenSet:
        if tokens.environment != self.config.environment:
            raise ConfigurationError(
                "QuickBooks OAuth token environment does not match the configured environment"
            )
        if tokens.refresh_expired():
            raise QuickBooksIntegrationError("QuickBooks refresh token has expired; reconnect the company")
        return self._token_request(
            {"grant_type": "refresh_token", "refresh_token": tokens.refresh_token},
            realm_id=tokens.realm_id,
        )

    def revoke(self, token: str) -> None:
        response = self.transport.request(
            "POST",
            OAUTH_REVOKE_URL,
            auth=(self.config.client_id, self.config.client_secret),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json={"token": _require_non_placeholder("QuickBooks token", token)},
            timeout=self.config.timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise QuickBooksIntegrationError(
                f"QuickBooks token revocation failed with HTTP {response.status_code} {response.reason}"
            )


@dataclass(frozen=True)
class QuickBooksOAuthCallbackResult:
    code: str = field(repr=False)
    state: str = field(repr=False)
    realm_id: str

    def redacted(self) -> dict[str, str]:
        return {
            "code": "<redacted>",
            "state": "<redacted>",
            "realm_id_suffix": self.realm_id[-6:],
        }


def bind_config_to_tokens(
    config: QuickBooksConfig,
    tokens: QuickBooksTokenSet,
) -> QuickBooksConfig:
    """Use the DPAPI token vault realm while rejecting an explicit mismatch."""

    if config.realm_id and config.realm_id != tokens.realm_id:
        raise ConfigurationError("Configured QuickBooks realm does not match the secured token vault")
    if config.environment != tokens.environment:
        raise ConfigurationError(
            "Configured QuickBooks environment does not match the secured token vault"
        )
    return replace(config, realm_id=tokens.realm_id)


class QuickBooksLocalOAuthCallbackServer:
    """Receive one Intuit sandbox callback on an exact localhost URI."""

    def __init__(self, redirect_uri: str):
        parsed = urlparse(redirect_uri)
        if parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}:
            raise ConfigurationError("Local OAuth callback requires an http://localhost or 127.0.0.1 URI")
        if not parsed.port:
            raise ConfigurationError("Local OAuth callback URI requires an explicit port")
        if parsed.query or parsed.fragment:
            raise ConfigurationError("Local OAuth callback URI cannot contain a query or fragment")
        self.host = parsed.hostname
        self.port = parsed.port
        self.path = parsed.path or "/"

    def wait_for_callback(self, *, timeout_seconds: int = 300) -> QuickBooksOAuthCallbackResult:
        if not 1 <= timeout_seconds <= 600:
            raise ConfigurationError("OAuth callback timeout must be between 1 and 600 seconds")
        captured: dict[str, str] = {}
        callback_path = self.path

        class CallbackHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def do_GET(self) -> None:  # noqa: N802 - stdlib handler method name
                parsed = urlparse(self.path)
                if parsed.path != callback_path:
                    self.send_error(404)
                    return
                query = parse_qs(parsed.query, keep_blank_values=True)
                captured["code"] = str((query.get("code") or [""])[0])
                captured["state"] = str((query.get("state") or [""])[0])
                captured["realm_id"] = str((query.get("realmId") or [""])[0])
                captured["error"] = str((query.get("error") or [""])[0])
                ok = bool(captured["code"] and captured["state"] and captured["realm_id"] and not captured["error"])
                body = (
                    "<!doctype html><title>Aureon QuickBooks connection</title>"
                    "<h1>Authorization received</h1><p>You may close this tab and return to Aureon.</p>"
                    if ok
                    else "<!doctype html><title>Aureon QuickBooks connection</title>"
                    "<h1>Authorization was not completed</h1><p>Return to Aureon and retry.</p>"
                ).encode()
                self.send_response(200 if ok else 400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = HTTPServer((self.host, self.port), CallbackHandler)
        server.timeout = timeout_seconds
        try:
            server.handle_request()
        finally:
            server.server_close()
        if not captured:
            raise QuickBooksIntegrationError("Timed out waiting for the local QuickBooks OAuth callback")
        if captured.get("error"):
            raise QuickBooksIntegrationError("QuickBooks authorization was declined or returned an error")
        return QuickBooksOAuthCallbackResult(
            code=_require_non_placeholder("OAuth authorization code", captured.get("code", "")),
            state=_require_non_placeholder("OAuth returned state", captured.get("state", "")),
            realm_id=_require_non_placeholder("OAuth realmId", captured.get("realm_id", "")),
        )


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", ctypes.c_ulong), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _dpapi_transform(data: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":
        raise ConfigurationError("The built-in QuickBooks token vault requires Windows DPAPI")
    source_buffer = (ctypes.c_byte * len(data)).from_buffer_copy(data)
    source = _DataBlob(len(data), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_byte)))
    destination = _DataBlob()
    function = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    if protect:
        ok = function(
            ctypes.byref(source),
            "Aureon QuickBooks OAuth tokens",
            None,
            None,
            None,
            0x1,
            ctypes.byref(destination),
        )
    else:
        ok = function(
            ctypes.byref(source),
            None,
            None,
            None,
            None,
            0x1,
            ctypes.byref(destination),
        )
    if not ok:
        raise ConfigurationError(f"Windows DPAPI {'encryption' if protect else 'decryption'} failed")
    try:
        return ctypes.string_at(destination.pbData, destination.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(destination.pbData)


@dataclass(frozen=True)
class QuickBooksClientCredentials:
    client_id: str
    client_secret: str = field(repr=False)
    environment: str = "sandbox"

    def __post_init__(self) -> None:
        _require_non_placeholder("QuickBooks client ID", self.client_id)
        _require_non_placeholder("QuickBooks client secret", self.client_secret)
        if self.environment not in API_BASE_URLS:
            raise ConfigurationError(
                "QuickBooks client credential environment must be sandbox or production"
            )

    def redacted(self) -> dict[str, str]:
        return {
            "client_id_suffix": self.client_id[-6:],
            "client_secret": "<redacted>",
            "environment": self.environment,
        }


class DPAPIClientCredentialVault:
    """Windows-user-bound encrypted storage for Intuit client credentials."""

    SCHEMA_VERSION = "aureon-qbo-client-credentials-dpapi-v1"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def save(self, credentials: QuickBooksClientCredentials) -> Path:
        plaintext = _canonical_json(
            {
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "environment": credentials.environment,
            }
        )
        ciphertext = _dpapi_transform(plaintext, protect=True)
        envelope = {
            "schema_version": self.SCHEMA_VERSION,
            "protection": "windows-dpapi-current-user",
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(envelope, handle, indent=2, sort_keys=True)
            handle.write("\n")
            temp_path = Path(handle.name)
        os.replace(temp_path, self.path)
        return self.path

    def load(self) -> QuickBooksClientCredentials:
        if not self.path.exists():
            raise ConfigurationError(f"QuickBooks client credential vault does not exist: {self.path}")
        envelope = json.loads(self.path.read_text(encoding="utf-8"))
        if envelope.get("schema_version") != self.SCHEMA_VERSION:
            raise ConfigurationError("QuickBooks client credential vault schema is not supported")
        ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
        payload = json.loads(_dpapi_transform(ciphertext, protect=False).decode("utf-8"))
        return QuickBooksClientCredentials(**payload)


class QuickBooksLocalCredentialReceiver:
    """Accept one loopback-only credential handoff and persist it directly to DPAPI."""

    PATH = "/quickbooks/client-credentials"

    def __init__(
        self,
        *,
        nonce: str,
        host: str = "127.0.0.1",
        port: int = 8766,
        environment: str = "sandbox",
    ):
        self.nonce = _require_non_placeholder("local credential handoff nonce", nonce)
        if host not in {"127.0.0.1", "localhost"}:
            raise ConfigurationError("Credential receiver must bind to loopback")
        if not 1 <= int(port) <= 65535:
            raise ConfigurationError("Credential receiver port is invalid")
        self.host = host
        self.port = int(port)
        if environment not in API_BASE_URLS:
            raise ConfigurationError(
                "QuickBooks client credential environment must be sandbox or production"
            )
        self.environment = environment

    def receive_and_save(
        self,
        vault: DPAPIClientCredentialVault,
        *,
        timeout_seconds: int = 60,
    ) -> QuickBooksClientCredentials:
        if not 1 <= timeout_seconds <= 120:
            raise ConfigurationError("Credential receiver timeout must be between 1 and 120 seconds")
        captured: dict[str, QuickBooksClientCredentials] = {}
        expected_nonce = self.nonce
        credential_environment = self.environment

        class CredentialHandler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                return

            def do_POST(self) -> None:  # noqa: N802 - stdlib handler method name
                if urlparse(self.path).path != QuickBooksLocalCredentialReceiver.PATH:
                    self.send_error(404)
                    return
                supplied_nonce = self.headers.get("X-Aureon-Nonce", "")
                if not hmac.compare_digest(supplied_nonce, expected_nonce):
                    self.send_error(403)
                    return
                try:
                    content_length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    self.send_error(400)
                    return
                if not 1 <= content_length <= 4096:
                    self.send_error(413)
                    return
                try:
                    payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
                    credentials = QuickBooksClientCredentials(
                        client_id=str(payload.get("client_id", "")),
                        client_secret=str(payload.get("client_secret", "")),
                        environment=credential_environment,
                    )
                    vault.save(credentials)
                except (UnicodeDecodeError, json.JSONDecodeError, AttributeError, ConfigurationError):
                    self.send_error(400)
                    return
                captured["credentials"] = credentials
                body = json.dumps(
                    {"saved": True, "client_id_suffix": credentials.client_id[-6:]}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = HTTPServer((self.host, self.port), CredentialHandler)
        server.timeout = timeout_seconds
        try:
            server.handle_request()
        finally:
            server.server_close()
        if "credentials" not in captured:
            raise QuickBooksIntegrationError("No valid local Intuit credential handoff was received")
        return captured["credentials"]


class DPAPITokenVault:
    """User-bound encrypted token storage, suitable for local Windows runtime."""

    SCHEMA_VERSION = "aureon-quickbooks-dpapi-v1"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def save(self, tokens: QuickBooksTokenSet) -> Path:
        ciphertext = _dpapi_transform(_canonical_json(tokens.secret_payload()), protect=True)
        envelope = {
            "schema_version": self.SCHEMA_VERSION,
            "protection": "windows-dpapi-current-user",
            "saved_at": _iso(_utc_now()),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(envelope, handle, indent=2, sort_keys=True)
            handle.write("\n")
            temp_path = Path(handle.name)
        os.replace(temp_path, self.path)
        return self.path

    def load(self) -> QuickBooksTokenSet:
        if not self.path.exists():
            raise ConfigurationError(f"QuickBooks token vault does not exist: {self.path}")
        envelope = json.loads(self.path.read_text(encoding="utf-8"))
        if envelope.get("schema_version") != self.SCHEMA_VERSION:
            raise ConfigurationError("QuickBooks token vault schema is not supported")
        ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
        payload = json.loads(_dpapi_transform(ciphertext, protect=False).decode("utf-8"))
        return QuickBooksTokenSet(**payload)


@dataclass(frozen=True)
class AureonCanonicalAccountingEvent:
    """Immutable event digest proving a QBO write originated in Aureon OS."""

    event_id: str
    operation: str
    entity: str
    payload_sha256: str
    evidence_sha256: tuple[str, ...]
    created_at: str
    canonical_source: str = "aureon_os"

    @classmethod
    def create(
        cls,
        *,
        event_id: str,
        operation: str,
        entity: str,
        payload: Mapping[str, Any],
        evidence_sha256: list[str] | tuple[str, ...],
        now: datetime | None = None,
    ) -> AureonCanonicalAccountingEvent:
        evidence = tuple(sorted({str(item).lower() for item in evidence_sha256}))
        if not evidence or any(not re.fullmatch(r"[0-9a-f]{64}", item) for item in evidence):
            raise ConfigurationError("A canonical Aureon accounting event requires valid evidence SHA-256 digests")
        if operation not in {"create", "update"}:
            raise ConfigurationError("Aureon accounting event operation must be create or update")
        if entity not in MUTATION_ENTITY_ALLOWLIST:
            raise ConfigurationError(f"Aureon accounting event entity is not allowlisted: {entity}")
        return cls(
            event_id=_require_non_placeholder("Aureon accounting event ID", event_id),
            operation=operation,
            entity=entity,
            payload_sha256=payload_sha256(payload),
            evidence_sha256=evidence,
            created_at=_iso(now or _utc_now()),
        )

    def verify_projection(self, *, operation: str, entity: str, payload: Mapping[str, Any]) -> None:
        if self.canonical_source != "aureon_os":
            raise MutationBlockedError("QuickBooks projection has no Aureon OS canonical authority")
        if self.operation != operation or self.entity != entity:
            raise MutationBlockedError("QuickBooks projection differs from the canonical Aureon event scope")
        if not hmac.compare_digest(self.payload_sha256, payload_sha256(payload)):
            raise MutationBlockedError("QuickBooks projection payload differs from the canonical Aureon event")
        if not self.evidence_sha256:
            raise MutationBlockedError("QuickBooks projection has no canonical Aureon evidence digests")

    def digest(self) -> str:
        return payload_sha256(asdict(self))


@dataclass(frozen=True)
class QuickBooksMutationApproval:
    approval_id: str
    approved_by: str
    realm_id: str
    operation: str
    entity: str
    payload_sha256: str
    canonical_event_sha256: str
    idempotency_key: str
    issued_at: str
    expires_at: str
    signature: str = field(repr=False)

    @classmethod
    def create(
        cls,
        *,
        approved_by: str,
        realm_id: str,
        operation: str,
        entity: str,
        payload: Mapping[str, Any],
        canonical_event: AureonCanonicalAccountingEvent,
        idempotency_key: str,
        signing_key: str,
        ttl_minutes: int = 15,
        now: datetime | None = None,
    ) -> QuickBooksMutationApproval:
        issued = now or _utc_now()
        canonical_event.verify_projection(operation=operation, entity=entity, payload=payload)
        unsigned = {
            "approval_id": secrets.token_urlsafe(18),
            "approved_by": _require_non_placeholder("approved_by", approved_by),
            "realm_id": _require_non_placeholder("realm_id", realm_id),
            "operation": operation,
            "entity": entity,
            "payload_sha256": payload_sha256(payload),
            "canonical_event_sha256": canonical_event.digest(),
            "idempotency_key": _require_non_placeholder("idempotency_key", idempotency_key),
            "issued_at": _iso(issued),
            "expires_at": _iso(issued + timedelta(minutes=ttl_minutes)),
        }
        signature = hmac.new(
            _require_non_placeholder("approval signing key", signing_key).encode("utf-8"),
            _canonical_json(unsigned),
            hashlib.sha256,
        ).hexdigest()
        return cls(**unsigned, signature=signature)

    def unsigned_payload(self) -> dict[str, str]:
        return {
            "approval_id": self.approval_id,
            "approved_by": self.approved_by,
            "realm_id": self.realm_id,
            "operation": self.operation,
            "entity": self.entity,
            "payload_sha256": self.payload_sha256,
            "canonical_event_sha256": self.canonical_event_sha256,
            "idempotency_key": self.idempotency_key,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }

    def verify(
        self,
        *,
        signing_key: str,
        realm_id: str,
        operation: str,
        entity: str,
        payload: Mapping[str, Any],
        canonical_event: AureonCanonicalAccountingEvent,
        now: datetime | None = None,
    ) -> None:
        expected = hmac.new(
            _require_non_placeholder("approval signing key", signing_key).encode("utf-8"),
            _canonical_json(self.unsigned_payload()),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(self.signature, expected):
            raise MutationBlockedError("QuickBooks mutation approval signature is invalid")
        if self.realm_id != realm_id or self.operation != operation or self.entity != entity:
            raise MutationBlockedError("QuickBooks mutation approval scope does not match this request")
        if not hmac.compare_digest(self.payload_sha256, payload_sha256(payload)):
            raise MutationBlockedError("QuickBooks mutation payload differs from the approved payload")
        canonical_event.verify_projection(operation=operation, entity=entity, payload=payload)
        if not hmac.compare_digest(self.canonical_event_sha256, canonical_event.digest()):
            raise MutationBlockedError("QuickBooks mutation differs from the approved Aureon canonical event")
        instant = now or _utc_now()
        if _parse_time(self.issued_at) > instant + timedelta(seconds=30):
            raise MutationBlockedError("QuickBooks mutation approval is not yet valid")
        if _parse_time(self.expires_at) <= instant:
            raise MutationBlockedError("QuickBooks mutation approval has expired")

    def redacted(self) -> dict[str, str]:
        return {**self.unsigned_payload(), "signature": "<redacted>"}


class QuickBooksAuditWriter:
    """Write payload-free, hash-verifiable receipts to an ignored/private root."""

    SCHEMA_VERSION = "aureon-quickbooks-audit-v1"

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def write(
        self,
        *,
        action: str,
        request_summary: Mapping[str, Any],
        response_payload: Any,
        mutation: bool,
        approval: QuickBooksMutationApproval | None = None,
    ) -> Path:
        created_at = _utc_now()
        receipt = {
            "schema_version": self.SCHEMA_VERSION,
            "created_at": _iso(created_at),
            "action": action,
            "mutation": mutation,
            "request": _redact(dict(request_summary)),
            "response_sha256": payload_sha256(response_payload),
            "response_shape": _response_shape(response_payload),
            "payload_persisted": False,
            "approval": approval.redacted() if approval else None,
        }
        self.root.mkdir(parents=True, exist_ok=True)
        safe_action = re.sub(r"[^a-z0-9_-]+", "-", action.lower()).strip("-") or "event"
        filename = f"{created_at.strftime('%Y%m%dT%H%M%S%fZ')}_{safe_action}_{secrets.token_hex(4)}.json"
        path = self.root / filename
        path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path


def _response_shape(payload: Any) -> dict[str, Any]:
    if isinstance(payload, Mapping):
        return {"type": "object", "keys": sorted(str(key) for key in payload)[:40]}
    if isinstance(payload, list):
        return {"type": "array", "count": len(payload)}
    return {"type": type(payload).__name__}


class QuickBooksAPIClient:
    """Read-first QuickBooks Accounting API client with a hard write gate."""

    def __init__(
        self,
        config: QuickBooksConfig,
        tokens: QuickBooksTokenSet,
        *,
        transport: HTTPTransport | None = None,
        audit_writer: QuickBooksAuditWriter | None = None,
        token_updater: Callable[[QuickBooksTokenSet], None] | None = None,
        approval_signing_key: str = "",
    ):
        if not config.realm_id:
            raise ConfigurationError("QUICKBOOKS_REALM_ID is required for Accounting API calls")
        if config.realm_id != tokens.realm_id:
            raise ConfigurationError("Configured QuickBooks realm does not match the OAuth token realm")
        if config.environment != tokens.environment:
            raise ConfigurationError(
                "Configured QuickBooks environment does not match the OAuth token environment"
            )
        self.config = config
        self.tokens = tokens
        self.transport = transport or RequestsTransport()
        self.oauth = QuickBooksOAuthClient(config, self.transport)
        self.audit_writer = audit_writer
        self.token_updater = token_updater
        self.approval_signing_key = approval_signing_key

    def _ensure_access_token(self) -> None:
        if not self.tokens.access_expiring():
            return
        self.tokens = self.oauth.refresh(self.tokens)
        if self.token_updater:
            self.token_updater(self.tokens)

    def _url(self, suffix: str) -> str:
        return f"{self.config.api_base_url}/v3/company/{self.config.realm_id}/{suffix.lstrip('/')}"

    def _request(
        self,
        method: str,
        suffix: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_payload: Mapping[str, Any] | None = None,
        action: str,
        mutation: bool = False,
        approval: QuickBooksMutationApproval | None = None,
    ) -> Any:
        self._ensure_access_token()
        request_params = dict(params or {})
        request_params.setdefault("minorversion", self.config.minor_version)
        response = self.transport.request(
            method,
            self._url(suffix),
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.tokens.access_token}",
                "Content-Type": "application/json",
            },
            params=request_params,
            json=dict(json_payload) if json_payload is not None else None,
            timeout=self.config.timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise QuickBooksIntegrationError(
                f"QuickBooks API {action} failed with HTTP {response.status_code} {response.reason}"
            )
        payload = response.json()
        if self.audit_writer:
            self.audit_writer.write(
                action=action,
                request_summary={
                    "method": method,
                    "path": suffix,
                    "params": request_params,
                    "payload_sha256": payload_sha256(json_payload) if json_payload is not None else "",
                },
                response_payload=payload,
                mutation=mutation,
                approval=approval,
            )
        return payload

    def query(self, query: str) -> dict[str, Any]:
        normalized = " ".join(query.strip().split())
        match = re.fullmatch(
            r"SELECT\s+.+?\s+FROM\s+([A-Za-z]+)(?:\s+WHERE\s+.+)?(?:\s+STARTPOSITION\s+\d+)?"
            r"(?:\s+MAXRESULTS\s+\d+)?",
            normalized,
            flags=re.IGNORECASE,
        )
        if not match:
            raise ConfigurationError("Only a single QuickBooks SELECT query is permitted")
        entity = next((item for item in READ_ENTITY_ALLOWLIST if item.lower() == match.group(1).lower()), "")
        if not entity:
            raise ConfigurationError(f"QuickBooks read entity is not allowlisted: {match.group(1)}")
        payload = self._request(
            "GET",
            "query",
            params={"query": normalized},
            action=f"query-{entity}",
        )
        if not isinstance(payload, dict):
            raise QuickBooksIntegrationError("QuickBooks query response was not an object")
        return payload

    def report(self, name: str, **filters: Any) -> dict[str, Any]:
        report_name = next((item for item in REPORT_ALLOWLIST if item.lower() == name.lower()), "")
        if not report_name:
            raise ConfigurationError(f"QuickBooks report is not allowlisted: {name}")
        payload = self._request(
            "GET",
            f"reports/{report_name}",
            params={key: value for key, value in filters.items() if value not in (None, "")},
            action=f"report-{report_name}",
        )
        if not isinstance(payload, dict):
            raise QuickBooksIntegrationError("QuickBooks report response was not an object")
        return payload

    def read_control_snapshot(
        self,
        *,
        report_start_date: str | None = None,
        report_end_date: str | None = None,
    ) -> dict[str, Any]:
        report_filters: dict[str, Any] = {}
        if report_start_date:
            report_filters["start_date"] = report_start_date
        if report_end_date:
            report_filters["end_date"] = report_end_date
        return {
            "schema_version": "aureon-quickbooks-external-observation-v1",
            "captured_at": _iso(_utc_now()),
            "realm_id": self.config.realm_id,
            "environment": self.config.environment,
            "authority": {
                "canonical_system": "aureon_os",
                "quickbooks_role": "downstream_projection_and_readback",
                "may_overwrite_aureon_truth": False,
            },
            "company_info": self.query("SELECT * FROM CompanyInfo"),
            "accounts": self.query("SELECT * FROM Account MAXRESULTS 1000"),
            "vendors": self.query("SELECT * FROM Vendor MAXRESULTS 1000"),
            "customers": self.query("SELECT * FROM Customer MAXRESULTS 1000"),
            "balance_sheet": self.report("BalanceSheet", **report_filters),
            "profit_and_loss": self.report("ProfitAndLoss", **report_filters),
            "trial_balance": self.report("TrialBalance", **report_filters),
            "cash_flow": self.report("CashFlow", **report_filters),
        }

    def mutate(
        self,
        *,
        operation: str,
        entity: str,
        payload: Mapping[str, Any],
        approval: QuickBooksMutationApproval,
        canonical_event: AureonCanonicalAccountingEvent | None = None,
    ) -> dict[str, Any]:
        if not self.config.allow_mutation:
            raise MutationBlockedError("QuickBooks mutations are disabled by configuration")
        allowed_entity = next(
            (item for item in MUTATION_ENTITY_ALLOWLIST if item.lower() == entity.lower()),
            "",
        )
        if not allowed_entity:
            raise MutationBlockedError(f"QuickBooks mutation entity is not allowlisted: {entity}")
        if operation not in {"create", "update"}:
            raise MutationBlockedError("QuickBooks mutation operation must be create or update")
        if not self.approval_signing_key:
            raise MutationBlockedError("QuickBooks approval signing key is unavailable")
        if canonical_event is None:
            raise MutationBlockedError("QuickBooks projection requires a canonical Aureon accounting event")
        approval.verify(
            signing_key=self.approval_signing_key,
            realm_id=self.config.realm_id,
            operation=operation,
            entity=allowed_entity,
            payload=payload,
            canonical_event=canonical_event,
        )
        if operation == "update" and not {"Id", "SyncToken"}.issubset(payload):
            raise MutationBlockedError("QuickBooks updates require both Id and SyncToken")
        result = self._request(
            "POST",
            allowed_entity.lower(),
            params={"requestid": approval.idempotency_key},
            json_payload=payload,
            action=f"{operation}-{allowed_entity}",
            mutation=True,
            approval=approval,
        )
        if not isinstance(result, dict):
            raise QuickBooksIntegrationError("QuickBooks mutation response was not an object")
        return result


class QuickBooksStatusStore:
    """Atomic, secret-free status used by Aureon's accounting context bridge."""

    SCHEMA_VERSION = "aureon-quickbooks-status-v1"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        if payload.get("schema_version") != self.SCHEMA_VERSION:
            return {}
        return payload

    def write(self, payload: Mapping[str, Any]) -> Path:
        safe_payload = _redact(dict(payload))
        safe_payload["schema_version"] = self.SCHEMA_VERSION
        safe_payload["updated_at"] = _iso(_utc_now())
        safe_payload["status_sha256"] = payload_sha256(
            {key: value for key, value in safe_payload.items() if key != "status_sha256"}
        )
        raw = json.dumps(safe_payload, indent=2, sort_keys=True) + "\n"
        for forbidden in ("access_token", "refresh_token", "client_secret", "Bearer "):
            if forbidden in raw:
                raise ConfigurationError(f"QuickBooks status attempted to persist forbidden secret material: {forbidden}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.path.parent,
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(raw)
            temp_path = Path(handle.name)
        os.replace(temp_path, self.path)
        return self.path

    def merge(self, update: Mapping[str, Any]) -> Path:
        current = self.read()
        current.update(dict(update))
        return self.write(current)


def build_quickbooks_browser_observation(
    *,
    legal_name: str,
    bank_feed_connected: bool,
    bank_provider: str,
    pending_transaction_count: int,
    displayed_transaction_count: int,
    chart_account_count: int,
    mixed_use_review_required: bool,
    profit_and_loss_has_data: bool = False,
    balance_sheet_nonzero_account_count: int = 0,
    cis_enabled: bool = False,
    vat_enabled: bool = False,
    payroll_enabled: bool = False,
    developer_terms_state: str = "not_observed",
) -> dict[str, Any]:
    """Create a privacy-minimised QBO UI receipt from operator read-back."""
    allowed_terms_states = {
        "not_observed",
        "awaiting_owner_acceptance",
        "accepted_by_owner",
    }
    if developer_terms_state not in allowed_terms_states:
        raise ValueError(
            "developer_terms_state must be one of "
            f"{', '.join(sorted(allowed_terms_states))}"
        )
    return {
        "connection_state": "qbo_ui_connected_api_pending",
        "authority": {
            "canonical_system": "aureon_os",
            "quickbooks_role": "downstream_projection_and_readback",
            "quickbooks_may_overwrite_aureon_truth": False,
            "projection_requires_canonical_event": True,
        },
        "company": {
            "legal_name": legal_name.strip().upper(),
            "identity_verified_in_qbo_ui": bool(legal_name.strip()),
            "company_number": "NI696693",
        },
        "api": {
            "developer_app": "not_verified",
            "developer_terms_state": developer_terms_state,
            "oauth": "not_verified",
            "company_info_readback": "not_verified",
            "default_mode": "read_only",
        },
        "bank_feed": {
            "connected": bank_feed_connected,
            "provider": bank_provider.strip(),
            "pending_transaction_count": max(0, int(pending_transaction_count)),
            "displayed_transaction_count": max(0, int(displayed_transaction_count)),
            "ownership_status": (
                "mixed_use_owner_accountant_review_required"
                if mixed_use_review_required
                else "owner_confirmation_required"
            ),
            "aureon_posted_transaction_count": 0,
            "bulk_posting_allowed": False,
        },
        "chart_of_accounts": {
            "account_count": max(0, int(chart_account_count)),
            "source": "live_qbo_ui_readback",
            "staged_changes_applied": False,
        },
        "reports": {
            "profit_and_loss_current_period_has_data": profit_and_loss_has_data,
            "balance_sheet_nonzero_account_count": max(0, int(balance_sheet_nonzero_account_count)),
            "reconciled_to_aureon_canonical_ledger": False,
        },
        "tax_features": {
            "cis_enabled": cis_enabled,
            "vat_enabled": vat_enabled,
            "payroll_enabled": payroll_enabled,
            "status_source": "live_qbo_ui_readback",
            "may_be_enabled_from_qbo_alone": False,
        },
        "controls": {
            "source_of_truth": "aureon_os",
            "quickbooks_mutations": "disabled",
            "bank_posting": "blocked_pending_ownership_and_evidence_reconciliation",
            "external_legal_agreements": "owner_confirmation_required",
            "hmrc_submission": "manual_only",
            "companies_house_filing": "manual_only",
            "tax_or_penalty_payment": "manual_only",
        },
    }


def build_quickbooks_production_readiness(
    *,
    live_company_observed: bool,
    legal_name_match_observed: bool,
    subscription_state: str,
    bank_feed_consent_state: str,
    developer_session_state: str,
    sandbox_test_state: str,
    production_app_assessment_state: str,
    production_credentials_state: str,
    production_redirect_uri: str = "",
    verified_public_urls: Mapping[str, str] | None = None,
    oauth_state: str = "not_connected",
    company_info_readback: str = "not_verified",
) -> dict[str, Any]:
    """Build a fail-closed gate for connecting Aureon's live QBO company."""

    allowed_states = {
        "subscription_state": {
            "not_observed",
            "payment_scheduled_not_settled",
            "active_provider_verified",
            "cancelled",
        },
        "bank_feed_consent_state": {
            "not_observed",
            "consent_observed_import_readback_pending",
            "connected_readback_verified",
            "revoked",
        },
        "developer_session_state": {"active", "expired", "not_observed"},
        "sandbox_test_state": {"not_started", "provider_blocked", "oauth_verified"},
        "production_app_assessment_state": {"not_observed", "in_progress", "approved"},
        "production_credentials_state": {"not_observed", "secured_in_dpapi"},
        "oauth_state": {"not_connected", "tokens_secured", "connected"},
        "company_info_readback": {"not_verified", "verified"},
    }
    values = {
        "subscription_state": subscription_state,
        "bank_feed_consent_state": bank_feed_consent_state,
        "developer_session_state": developer_session_state,
        "sandbox_test_state": sandbox_test_state,
        "production_app_assessment_state": production_app_assessment_state,
        "production_credentials_state": production_credentials_state,
        "oauth_state": oauth_state,
        "company_info_readback": company_info_readback,
    }
    for name, value in values.items():
        if value not in allowed_states[name]:
            raise ConfigurationError(
                f"Unsupported QuickBooks production readiness state for {name}: {value}"
            )

    required_public_urls = (
        "privacy_policy",
        "end_user_licence_agreement",
        "host_domain",
        "launch",
        "disconnect",
        "connect_reconnect",
    )
    supplied_urls = dict(verified_public_urls or {})
    public_url_status: dict[str, dict[str, str]] = {}
    for name in required_public_urls:
        value = str(supplied_urls.get(name, "")).strip()
        parsed = urlparse(value)
        valid = parsed.scheme == "https" and bool(parsed.hostname)
        public_url_status[name] = {
            "state": "verified_https" if valid else "missing_or_unverified",
            "url": value if valid else "",
        }

    redirect = production_redirect_uri.strip()
    parsed_redirect = urlparse(redirect)
    redirect_ready = (
        parsed_redirect.scheme == "https"
        and bool(parsed_redirect.hostname)
        and parsed_redirect.hostname not in {"localhost", "127.0.0.1"}
    )
    public_urls_ready = all(
        item["state"] == "verified_https" for item in public_url_status.values()
    )
    production_oauth_ready = all(
        (
            production_app_assessment_state == "approved",
            production_credentials_state == "secured_in_dpapi",
            redirect_ready,
            public_urls_ready,
        )
    )
    read_only_sync_ready = all(
        (
            production_oauth_ready,
            oauth_state == "connected",
            company_info_readback == "verified",
            legal_name_match_observed,
        )
    )
    if read_only_sync_ready:
        connection_state = "live_api_readback_verified"
    elif production_oauth_ready:
        connection_state = "production_oauth_authorization_ready"
    elif live_company_observed:
        connection_state = "live_qbo_company_observed_production_api_gated"
    else:
        connection_state = "live_qbo_company_not_verified"

    return {
        "schema_version": "aureon-quickbooks-production-readiness-v1",
        "generated_at": _iso(_utc_now()),
        "connection_state": connection_state,
        "authority": {
            "canonical_system": "aureon_os",
            "quickbooks_role": "downstream_projection_and_readback",
            "quickbooks_mutations_authorised": False,
        },
        "live_company_evidence": {
            "observed": live_company_observed,
            "legal_name_match_observed": legal_name_match_observed,
            "subscription_state": subscription_state,
            "bank_feed_consent_state": bank_feed_consent_state,
        },
        "developer_gate": {
            "session_state": developer_session_state,
            "sandbox_test_state": sandbox_test_state,
            "production_app_assessment_state": production_app_assessment_state,
            "production_credentials_state": production_credentials_state,
            "production_redirect_uri_state": (
                "verified_https" if redirect_ready else "missing_or_unverified"
            ),
            "production_redirect_uri": redirect if redirect_ready else "",
            "public_urls": public_url_status,
        },
        "api_gate": {
            "production_oauth_ready": production_oauth_ready,
            "oauth_state": oauth_state,
            "company_info_readback": company_info_readback,
            "read_only_sync_ready": read_only_sync_ready,
            "mutation_projection_ready": False,
        },
        "next_actions": [
            "Sign in to Intuit Developer as the owner and complete the production app details and assessment.",
            "Publish or verify every required HTTPS policy, launch, connect, reconnect, and disconnect URL.",
            "Register the HTTPS production redirect URI and secure production credentials in the production DPAPI vault.",
            "Complete production OAuth, then run read-only CompanyInfo and accounting snapshot verification.",
            "Keep all QuickBooks writes disabled until Aureon opening entries are evidenced and explicitly approved.",
        ],
    }


class QuickBooksWebhookVerifier:
    """Verify Intuit signatures and emit refresh-only change receipts."""

    ALLOWED_OPERATIONS = frozenset({"Create", "Update", "Delete", "Merge", "Void", "Emailed"})

    def __init__(self, verifier_token: str, *, expected_realm_id: str = ""):
        self.verifier_token = _require_non_placeholder("QuickBooks webhook verifier token", verifier_token)
        self.expected_realm_id = expected_realm_id.strip()

    def verify(self, raw_body: bytes, intuit_signature: str) -> dict[str, Any]:
        expected = base64.b64encode(
            hmac.new(self.verifier_token.encode("utf-8"), raw_body, hashlib.sha256).digest()
        ).decode("ascii")
        if not hmac.compare_digest(expected, intuit_signature.strip()):
            raise WebhookVerificationError("Intuit webhook signature does not match")
        try:
            envelope = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WebhookVerificationError("Intuit webhook body is not valid JSON") from exc
        notifications = envelope.get("eventNotifications")
        if not isinstance(notifications, list):
            raise WebhookVerificationError("Intuit webhook eventNotifications must be an array")

        changes: list[dict[str, str]] = []
        realms: set[str] = set()
        for notification in notifications:
            realm_id = str((notification or {}).get("realmId", "")).strip()
            if not realm_id:
                raise WebhookVerificationError("Intuit webhook notification has no realmId")
            if self.expected_realm_id and realm_id != self.expected_realm_id:
                raise WebhookVerificationError("Intuit webhook realmId does not match the connected company")
            realms.add(realm_id)
            entities = (((notification or {}).get("dataChangeEvent") or {}).get("entities") or [])
            if not isinstance(entities, list):
                raise WebhookVerificationError("Intuit webhook entities must be an array")
            for entity in entities:
                name = str((entity or {}).get("name", "")).strip()
                operation = str((entity or {}).get("operation", "")).strip()
                entity_id = str((entity or {}).get("id", "")).strip()
                if name not in READ_ENTITY_ALLOWLIST or operation not in self.ALLOWED_OPERATIONS:
                    continue
                changes.append(
                    {
                        "name": name,
                        "operation": operation,
                        "entity_id_sha256": hashlib.sha256(entity_id.encode("utf-8")).hexdigest(),
                        "last_updated": str((entity or {}).get("lastUpdated", "")),
                    }
                )
        return {
            "schema_version": "aureon-quickbooks-webhook-receipt-v1",
            "verified_at": _iso(_utc_now()),
            "signature_verified": True,
            "realm_count": len(realms),
            "realm_id_suffixes": sorted(realm[-6:] for realm in realms),
            "change_count": len(changes),
            "changes": changes,
            "action": "queue_read_only_refresh",
            "mutations_triggered": False,
            "authority": "aureon_os",
            "raw_body_sha256": hashlib.sha256(raw_body).hexdigest(),
        }


def build_recommended_quickbooks_chart() -> dict[str, Any]:
    """Stage the missing UK, grant, CIS, and R&D controls without creating them."""
    accounts = [
        ("Grant income - confirmed awards", "Other Income", "award/provider evidence required"),
        ("Deferred grant income", "Current liabilities", "recognition basis required"),
        ("Grant receivable - confirmed awards", "Current assets", "award and payment terms required"),
        ("R&D staff costs", "Expenses", "payroll and project allocation required"),
        ("R&D subcontractor costs", "Expenses", "contract, invoice, payment, and eligibility review required"),
        ("R&D software and cloud", "Expenses", "invoice and project allocation required"),
        ("R&D consumables", "Expenses", "invoice and project allocation required"),
        ("CIS deductions suffered", "Current assets", "CIS statements and live HMRC status required"),
        ("CIS deductions payable", "Current liabilities", "CIS registration and return basis required"),
        ("PAYE and NIC payable", "Current liabilities", "PAYE reference and payroll records required"),
        ("VAT control", "Current liabilities", "VAT registration and live HMRC status required"),
        ("Director loan account", "Current liabilities", "mixed-use and related-party reconciliation required"),
        ("Research project costs - non-claim", "Expenses", "project code and evidence required"),
    ]
    return {
        "schema_version": "aureon-quickbooks-chart-plan-v1",
        "generated_at": _iso(_utc_now()),
        "status": "staged_not_applied",
        "account_count": len(accounts),
        "accounts": [
            {"name": name, "account_type": account_type, "posting_gate": gate}
            for name, account_type, gate in accounts
        ],
        "controls": {
            "canonical_system": "aureon_os",
            "quickbooks_role": "staged_projection_target",
            "creates_quickbooks_accounts": False,
            "posts_opening_balances": False,
            "enables_cis": False,
            "enables_vat": False,
            "requires_accountant_mapping_review": True,
        },
    }


def build_aureon_quickbooks_reconciliation_plan(
    *,
    active_grant_ledger: str | Path | None = None,
) -> dict[str, Any]:
    """Return the evidence-led control plan without asserting unverified balances."""
    grant_root = str(Path(active_grant_ledger).resolve()) if active_grant_ledger else ""
    return {
        "schema_version": "aureon-quickbooks-reconciliation-plan-v1",
        "generated_at": _iso(_utc_now()),
        "entity": {
            "legal_name": "R&A CONSULTING AND BROKERAGE SERVICES LTD",
            "company_number": "NI696693",
            "trading_programme": "Aureon Zorza Technologies",
            "identity_source": "Companies House profile plus company-controlled website; verify in live QBO",
        },
        "control_mode": {
            "canonical_system": "aureon_os",
            "quickbooks_role": "downstream_projection_and_readback",
            "quickbooks_may_overwrite_aureon_truth": False,
            "default": "read_only",
            "quickbooks_mutations": "signed_expiring_payload_bound_approval_required",
            "hmrc_submission": "manual_only",
            "companies_house_filing": "manual_only",
            "tax_or_penalty_payment": "manual_only",
            "bank_or_billing_change": "manual_only",
        },
        "connection": [
            "Use development credentials only for sandbox companies and production credentials only for the live company.",
            "Bind credentials and OAuth tokens to separate environment-specific Windows DPAPI vaults.",
            "Complete the Intuit production app assessment and publish the required HTTPS policy, launch, connect, reconnect, disconnect, and redirect URLs.",
            "Complete OAuth 2.0 authorization and store tokens only in the matching DPAPI vault.",
            "Read back CompanyInfo and confirm the realm belongs to NI696693 before any reconciliation.",
        ],
        "xero_migration": [
            "Export and preserve Xero chart of accounts, trial balance, journals, open invoices, bills, contacts, and tax settings.",
            "Agree one migration cut-off date and opening-balance control total with the accountant.",
            "Post nothing from historic emails or PDFs unless it reconciles to source records and a signed approval.",
        ],
        "read_only_quickbooks_snapshot": [
            "CompanyInfo",
            "Chart of accounts",
            "Customers and vendors",
            "Balance sheet",
            "Profit and loss",
            "Trial balance",
            "Cash flow",
        ],
        "bank_and_processor_sources": [
            "Zempler business bank statements",
            "Revolut exports where they belong to the legal entity",
            "SumUp transaction and payout reports",
            "Any other company bank, card, loan, PayPal, Stripe, cash, or director account confirmed by the owner",
        ],
        "tax_controls": {
            "corporation_tax": [
                "Reconcile each accounting period and HMRC notice to the live HMRC account.",
                "Keep CT600 preparation separate from QBO bookkeeping and commercial-software submission.",
            ],
            "vat": [
                "Confirm VAT registration status, effective date, schemes, periods, and live HMRC balance.",
                "Do not infer current VAT liability from historic correspondence alone.",
            ],
            "paye": [
                "Confirm whether a PAYE employer reference was issued and obtain live HMRC status.",
            ],
            "cis": [
                "Determine employment/subcontractor status from contracts and working facts.",
                "Only enable CIS after the accountant confirms registration and treatment.",
            ],
        },
        "grants_and_rd": {
            "active_grant_ledger": grant_root,
            "grant_income": "Recognise only from award/provider evidence and the applicable accounting treatment.",
            "applications": "Drafts, route-fit contacts, and submissions without provider receipts are not awards or receivables.",
            "rd_projects": "Use project codes for eligible staff/subcontractor/software/consumable evidence; tax claim remains accountant-reviewed.",
        },
        "human_decisions_required": [
            "Whether the company is the owner's main source of income (QBO onboarding personalisation).",
            "Migration cut-off date and signed opening balances.",
            "PAYE reference/status and labour engagement basis.",
            "CIS applicability and registration status.",
            "VAT status and current balance.",
            "Current HMRC Corporation Tax balances, returns, penalties, and payment plan.",
            "Confirmation statement filing and identity-verification route.",
        ],
    }


def _default_vault_path(environment: str | None = None) -> Path:
    configured = os.environ.get("QUICKBOOKS_TOKEN_VAULT", "").strip()
    if configured:
        return Path(configured)
    selected_environment = (
        environment or os.environ.get("QUICKBOOKS_ENVIRONMENT", "sandbox")
    ).strip().lower()
    if selected_environment not in API_BASE_URLS:
        raise ConfigurationError("QUICKBOOKS_ENVIRONMENT must be sandbox or production")
    filename = (
        "quickbooks_tokens.dpapi.json"
        if selected_environment == "sandbox"
        else "quickbooks_production_tokens.dpapi.json"
    )
    return Path(__file__).resolve().parents[2] / ".aureon" / filename


def _default_client_credential_vault_path(environment: str | None = None) -> Path:
    configured = os.environ.get("QUICKBOOKS_CLIENT_CREDENTIAL_VAULT", "").strip()
    if configured:
        return Path(configured)
    selected_environment = (
        environment or os.environ.get("QUICKBOOKS_ENVIRONMENT", "sandbox")
    ).strip().lower()
    if selected_environment not in API_BASE_URLS:
        raise ConfigurationError("QUICKBOOKS_ENVIRONMENT must be sandbox or production")
    filename = (
        "quickbooks_client_credentials.dpapi.json"
        if selected_environment == "sandbox"
        else "quickbooks_production_client_credentials.dpapi.json"
    )
    return Path(__file__).resolve().parents[2] / ".aureon" / filename


def _default_audit_path() -> Path:
    configured = os.environ.get("QUICKBOOKS_AUDIT_DIR", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "output" / "quickbooks" / "audit"


def _default_status_path() -> Path:
    configured = os.environ.get("QUICKBOOKS_STATUS_PATH", "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "output" / "quickbooks" / "status.json"


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("preflight", help="Print the evidence-led integration plan")
    plan_parser.add_argument("--active-grant-ledger", default=os.environ.get("AUREON_ACTIVE_GRANT_LEDGER", ""))

    subparsers.add_parser("chart-plan", help="Print the staged QuickBooks chart additions")
    status_parser = subparsers.add_parser("status", help="Print the secret-free integration status")
    status_parser.add_argument("--status-path", type=Path, default=_default_status_path())

    production_parser = subparsers.add_parser(
        "production-readiness",
        help="Record the fail-closed readiness gate for Aureon's live QuickBooks company",
    )
    production_parser.add_argument("--evidence", type=Path, required=True)
    production_parser.add_argument("--status-path", type=Path, default=_default_status_path())

    observe_parser = subparsers.add_parser(
        "record-browser-observation",
        help="Record a privacy-minimised live QBO UI read-back",
    )
    observe_parser.add_argument("--legal-name", required=True)
    observe_parser.add_argument("--bank-provider", default="")
    observe_parser.add_argument("--bank-feed-connected", action="store_true")
    observe_parser.add_argument("--pending-count", type=int, default=0)
    observe_parser.add_argument("--displayed-count", type=int, default=0)
    observe_parser.add_argument("--chart-account-count", type=int, default=0)
    observe_parser.add_argument("--mixed-use-review-required", action="store_true")
    observe_parser.add_argument("--profit-and-loss-has-data", action="store_true")
    observe_parser.add_argument("--balance-sheet-nonzero-accounts", type=int, default=0)
    observe_parser.add_argument("--cis-enabled", action="store_true")
    observe_parser.add_argument("--vat-enabled", action="store_true")
    observe_parser.add_argument("--payroll-enabled", action="store_true")
    observe_parser.add_argument(
        "--developer-terms-state",
        choices=("not_observed", "awaiting_owner_acceptance", "accepted_by_owner"),
        default="not_observed",
    )
    observe_parser.add_argument("--status-path", type=Path, default=_default_status_path())

    subparsers.add_parser("oauth-url", help="Print the OAuth URL and short-lived signed state")

    credentials_parser = subparsers.add_parser(
        "credentials-save",
        help="Encrypt Intuit client credentials from the current environment with Windows DPAPI",
    )
    credentials_parser.add_argument(
        "--credential-vault",
        type=Path,
        default=_default_client_credential_vault_path(),
    )

    credentials_status_parser = subparsers.add_parser(
        "credentials-status",
        help="Verify the DPAPI client-credential vault without printing secrets",
    )
    credentials_status_parser.add_argument(
        "--credential-vault",
        type=Path,
        default=_default_client_credential_vault_path(),
    )

    credentials_receive_parser = subparsers.add_parser(
        "credentials-receive-local",
        help="Receive one loopback-only credential handoff and write it directly to DPAPI",
    )
    credentials_receive_parser.add_argument("--nonce", required=True)
    credentials_receive_parser.add_argument("--port", type=int, default=8766)
    credentials_receive_parser.add_argument("--timeout", type=int, default=60)
    credentials_receive_parser.add_argument(
        "--credential-vault",
        type=Path,
        default=_default_client_credential_vault_path(),
    )

    connect_parser = subparsers.add_parser(
        "oauth-connect-local",
        help="Open authorization, receive the localhost callback, and secure tokens with DPAPI",
    )
    connect_parser.add_argument("--vault", type=Path, default=_default_vault_path())
    connect_parser.add_argument(
        "--credential-vault",
        type=Path,
        default=_default_client_credential_vault_path(),
    )
    connect_parser.add_argument("--status-path", type=Path, default=_default_status_path())
    connect_parser.add_argument("--timeout", type=int, default=300)
    connect_parser.add_argument(
        "--authorization-url-path",
        type=Path,
        help="Write the short-lived authorization URL for a controlled local browser",
    )
    connect_parser.add_argument(
        "--no-open-browser",
        action="store_true",
        help="Do not use the Windows default browser (requires --authorization-url-path)",
    )

    exchange_parser = subparsers.add_parser(
        "oauth-exchange",
        help="Exchange callback values from environment variables and save them with DPAPI",
    )
    exchange_parser.add_argument("--realm-id", default=os.environ.get("QUICKBOOKS_REALM_ID", ""))
    exchange_parser.add_argument("--vault", type=Path, default=_default_vault_path())

    sync_parser = subparsers.add_parser("sync-read-only", help="Read the controlled QBO accounting snapshot")
    sync_parser.add_argument("--vault", type=Path, default=_default_vault_path())
    sync_parser.add_argument("--audit-dir", type=Path, default=_default_audit_path())
    sync_parser.add_argument("--start-date", default="")
    sync_parser.add_argument("--end-date", default="")
    sync_parser.add_argument("--status-path", type=Path, default=_default_status_path())

    args = parser.parse_args()
    if args.command == "preflight":
        print(
            json.dumps(
                build_aureon_quickbooks_reconciliation_plan(
                    active_grant_ledger=args.active_grant_ledger or None
                ),
                indent=2,
            )
        )
        return 0
    if args.command == "chart-plan":
        print(json.dumps(build_recommended_quickbooks_chart(), indent=2))
        return 0
    if args.command == "status":
        print(json.dumps(QuickBooksStatusStore(args.status_path).read(), indent=2))
        return 0
    if args.command == "production-readiness":
        try:
            evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(
                f"QuickBooks production readiness evidence is unavailable or invalid: {args.evidence}"
            ) from exc
        if not isinstance(evidence, Mapping):
            raise ConfigurationError("QuickBooks production readiness evidence must be an object")
        readiness = build_quickbooks_production_readiness(**dict(evidence))
        store = QuickBooksStatusStore(args.status_path)
        current = store.read()
        api = dict(current.get("api") or {})
        api.update(
            {
                "live_company_connected": bool(
                    readiness["live_company_evidence"]["observed"]
                ),
                "target_environment": "production",
                "developer_session_state": readiness["developer_gate"]["session_state"],
                "production_app_assessment": readiness["developer_gate"][
                    "production_app_assessment_state"
                ],
                "production_credentials": readiness["developer_gate"][
                    "production_credentials_state"
                ],
                "production_oauth": readiness["api_gate"]["oauth_state"],
                "company_info_readback": readiness["api_gate"]["company_info_readback"],
                "mutations_enabled": False,
            }
        )
        path = store.merge(
            {
                "connection_state": readiness["connection_state"],
                "api": api,
                "production_readiness": readiness,
            }
        )
        print(
            json.dumps(
                {
                    "recorded": True,
                    "status_path": str(path),
                    "connection_state": readiness["connection_state"],
                    "production_oauth_ready": readiness["api_gate"][
                        "production_oauth_ready"
                    ],
                    "read_only_sync_ready": readiness["api_gate"]["read_only_sync_ready"],
                },
                indent=2,
            )
        )
        return 0
    if args.command == "record-browser-observation":
        observation = build_quickbooks_browser_observation(
            legal_name=args.legal_name,
            bank_feed_connected=args.bank_feed_connected,
            bank_provider=args.bank_provider,
            pending_transaction_count=args.pending_count,
            displayed_transaction_count=args.displayed_count,
            chart_account_count=args.chart_account_count,
            mixed_use_review_required=args.mixed_use_review_required,
            profit_and_loss_has_data=args.profit_and_loss_has_data,
            balance_sheet_nonzero_account_count=args.balance_sheet_nonzero_accounts,
            cis_enabled=args.cis_enabled,
            vat_enabled=args.vat_enabled,
            payroll_enabled=args.payroll_enabled,
            developer_terms_state=args.developer_terms_state,
        )
        path = QuickBooksStatusStore(args.status_path).write(observation)
        print(json.dumps({"recorded": True, "status_path": str(path), "status": observation}, indent=2))
        return 0

    if args.command == "credentials-save":
        environment = os.environ.get("QUICKBOOKS_ENVIRONMENT", "sandbox").strip().lower()
        credentials = QuickBooksClientCredentials(
            client_id=os.environ.get("QUICKBOOKS_CLIENT_ID", ""),
            client_secret=os.environ.get("QUICKBOOKS_CLIENT_SECRET", ""),
            environment=environment,
        )
        path = DPAPIClientCredentialVault(args.credential_vault).save(credentials)
        print(json.dumps({"saved": True, "vault": str(path), "credentials": credentials.redacted()}, indent=2))
        return 0
    if args.command == "credentials-status":
        credentials = DPAPIClientCredentialVault(args.credential_vault).load()
        print(
            json.dumps(
                {"available": True, "vault": str(args.credential_vault), "credentials": credentials.redacted()},
                indent=2,
            )
        )
        return 0
    if args.command == "credentials-receive-local":
        credential_vault = DPAPIClientCredentialVault(args.credential_vault)
        receiver = QuickBooksLocalCredentialReceiver(
            nonce=args.nonce,
            port=args.port,
            environment=os.environ.get("QUICKBOOKS_ENVIRONMENT", "sandbox").strip().lower(),
        )
        credentials = receiver.receive_and_save(credential_vault, timeout_seconds=args.timeout)
        print(
            json.dumps(
                {
                    "saved": True,
                    "vault": str(args.credential_vault),
                    "credentials": credentials.redacted(),
                },
                indent=2,
            )
        )
        return 0

    config_source = dict(os.environ)
    if hasattr(args, "credential_vault"):
        config_source["QUICKBOOKS_CLIENT_CREDENTIAL_VAULT"] = str(args.credential_vault)
    config = QuickBooksConfig.from_env(config_source, require_realm=False)
    oauth = QuickBooksOAuthClient(config)
    if args.command == "oauth-url":
        url, state = oauth.authorization_url()
        print(json.dumps({"authorization_url": url, "state": state}, indent=2))
        return 0
    if args.command == "oauth-exchange":
        code = os.environ.get("QUICKBOOKS_AUTH_CODE", "")
        returned_state = os.environ.get("QUICKBOOKS_RETURNED_STATE", "")
        expected_state = os.environ.get("QUICKBOOKS_EXPECTED_STATE", "")
        tokens = oauth.exchange_code(
            code=code,
            returned_state=returned_state,
            expected_state=expected_state,
            realm_id=args.realm_id,
        )
        DPAPITokenVault(args.vault).save(tokens)
        QuickBooksStatusStore(_default_status_path()).merge(
            {
                "connection_state": "oauth_tokens_secured_api_readback_pending",
                "api": {
                    "developer_app": "configured",
                    "oauth": "tokens_secured_in_windows_dpapi",
                    "company_info_readback": "not_verified",
                    "realm_id_suffix": tokens.realm_id[-6:],
                    "default_mode": "read_only",
                },
            }
        )
        print(json.dumps({"saved": True, "vault": str(args.vault), "tokens": tokens.redacted()}, indent=2))
        return 0
    if args.command == "oauth-connect-local":
        authorization_url, expected_state = oauth.authorization_url()
        callback_server = QuickBooksLocalOAuthCallbackServer(config.redirect_uri)
        authorization_url_path = args.authorization_url_path
        if args.no_open_browser and authorization_url_path is None:
            raise ConfigurationError("--no-open-browser requires --authorization-url-path")
        if authorization_url_path is not None:
            authorization_url_path.parent.mkdir(parents=True, exist_ok=True)
            authorization_url_path.write_text(authorization_url + "\n", encoding="utf-8")
        if not args.no_open_browser and not webbrowser.open(authorization_url, new=2):
            raise QuickBooksIntegrationError("Could not open the Intuit authorization page in the default browser")
        try:
            callback = callback_server.wait_for_callback(timeout_seconds=args.timeout)
        finally:
            if authorization_url_path is not None:
                authorization_url_path.unlink(missing_ok=True)
        tokens = oauth.exchange_code(
            code=callback.code,
            returned_state=callback.state,
            expected_state=expected_state,
            realm_id=callback.realm_id,
        )
        DPAPITokenVault(args.vault).save(tokens)
        QuickBooksStatusStore(args.status_path).merge(
            {
                "connection_state": "oauth_tokens_secured_api_readback_pending",
                "api": {
                    "developer_app": "development_app_created",
                    "developer_terms_state": "accepted_by_owner",
                    "oauth": "tokens_secured_in_windows_dpapi",
                    "company_info_readback": "not_verified",
                    "realm_id_suffix": tokens.realm_id[-6:],
                    "environment": config.environment,
                    "default_mode": "read_only",
                },
            }
        )
        print(
            json.dumps(
                {
                    "connected": True,
                    "vault": str(args.vault),
                    "callback": callback.redacted(),
                    "tokens": tokens.redacted(),
                },
                indent=2,
            )
        )
        return 0
    if args.command == "sync-read-only":
        vault = DPAPITokenVault(args.vault)
        tokens = vault.load()
        config = bind_config_to_tokens(config, tokens)
        client = QuickBooksAPIClient(
            config,
            tokens,
            audit_writer=QuickBooksAuditWriter(args.audit_dir),
            token_updater=vault.save,
        )
        snapshot = client.read_control_snapshot(
            report_start_date=args.start_date or None,
            report_end_date=args.end_date or None,
        )
        snapshot_digest = payload_sha256(snapshot)
        QuickBooksStatusStore(args.status_path).merge(
            {
                "connection_state": (
                    "sandbox_api_readback_verified"
                    if config.environment == "sandbox"
                    else "live_api_readback_verified"
                ),
                "api": {
                    "developer_app": (
                        "development_app_created"
                        if config.environment == "sandbox"
                        else "production_app_configured"
                    ),
                    "oauth": "connected",
                    "company_info_readback": "verified",
                    "realm_id_suffix": config.realm_id[-6:],
                    "environment": config.environment,
                    "snapshot_sha256": snapshot_digest,
                    "captured_at": snapshot["captured_at"],
                    "sections": sorted(snapshot),
                    "default_mode": "read_only",
                },
            }
        )
        print(
            json.dumps(
                {
                    "captured_at": snapshot["captured_at"],
                    "realm_id_suffix": str(snapshot["realm_id"])[-6:],
                    "environment": snapshot["environment"],
                    "snapshot_sha256": snapshot_digest,
                    "sections": sorted(snapshot),
                    "audit_dir": str(args.audit_dir),
                },
                indent=2,
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(_cli())
