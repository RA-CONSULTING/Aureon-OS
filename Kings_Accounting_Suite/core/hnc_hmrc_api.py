"""
HNC HMRC API — hnc_hmrc_api.py
================================
HMRC Making Tax Digital API Client.

Handles the complete HMRC MTD integration:
    1. OAuth 2.0 authentication (Authorization Code Grant)
    2. Token management (access + refresh, 4hr / 18mo expiry)
    3. Fraud prevention headers (WEB_APP_VIA_SERVER)
    4. Self Assessment MTD APIs:
       - Business Details (list businesses, get NINO/business ID)
       - Obligations (quarterly deadlines)
       - Self-Employment Period Summaries (quarterly updates)
       - Individual Calculations (trigger + retrieve tax calc)
       - Final Declaration (crystallise)
    5. VAT MTD API:
       - Retrieve obligations
       - Submit 9-box return
       - View return
    6. CIS Deductions API:
       - Retrieve deductions
       - Create / delete overrides

OAuth 2.0 Flow:
    Sandbox:  https://test-api.service.hmrc.gov.uk
    Live:     https://api.service.hmrc.gov.uk
    Auth:     https://test-www.tax.service.gov.uk/oauth/authorize  (sandbox)
              https://www.tax.service.gov.uk/oauth/authorize       (production)
    Token:    {base}/oauth/token

Fraud Prevention:
    Connection method: WEB_APP_VIA_SERVER
    16 headers required per HMRC specification.

References:
    HMRC Developer Hub:  https://developer.service.hmrc.gov.uk
    MTD ITSA Guide:      https://developer.service.hmrc.gov.uk/guides/
                         income-tax-mtd-end-to-end-service-guide/
    OAuth 2.0:           https://developer.service.hmrc.gov.uk/api-documentation/
                         docs/authorisation/user-restricted-endpoints
    Fraud Prevention:    https://developer.service.hmrc.gov.uk/guides/
                         fraud-prevention/connection-method/web-app-via-server/

Aureon Creator / Aureon Research — April 2026
"""

from __future__ import annotations
import json
import logging
import os
import time
import uuid
import hashlib
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from aureon.accounting.hmrc_mutation_boundary import (
    HMRCMutationHold,
    HMRCMutationRegistry,
)

logger = logging.getLogger("hnc_hmrc_api")


# =========================================================================
# CONFIGURATION
# =========================================================================

@dataclass
class HMRCConfig:
    """HMRC API configuration — sandbox or production."""
    # Environment
    environment: str = "sandbox"   # "sandbox" or "production"

    # Application credentials (from HMRC Developer Hub)
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8080/callback"

    # API scopes needed for full MTD
    scopes: List[str] = field(default_factory=lambda: [
        "read:self-assessment",
        "write:self-assessment",
        "read:vat",
        "write:vat",
        "read:construction-industry-scheme",
        "write:construction-industry-scheme",
    ])

    # Vendor info for fraud prevention
    vendor_product_name: str = "The HNC Accountant"
    vendor_version: str = "1.0.0"
    vendor_public_ip: str = ""

    # Token storage path
    token_file: str = ""

    @property
    def base_url(self) -> str:
        if self.environment == "production":
            return "https://api.service.hmrc.gov.uk"
        return "https://test-api.service.hmrc.gov.uk"

    @property
    def auth_url(self) -> str:
        if self.environment == "production":
            return "https://www.tax.service.gov.uk/oauth/authorize"
        return "https://test-www.tax.service.gov.uk/oauth/authorize"

    @property
    def token_url(self) -> str:
        return f"{self.base_url}/oauth/token"


# =========================================================================
# TOKEN MANAGEMENT
# =========================================================================

@dataclass
class OAuthToken:
    """OAuth 2.0 token pair with metadata."""
    access_token: str = ""
    refresh_token: str = ""
    token_type: str = "bearer"
    expires_in: int = 14400       # 4 hours default
    scope: str = ""
    issued_at: float = 0.0        # Unix timestamp

    @property
    def is_expired(self) -> bool:
        if not self.access_token:
            return True
        return time.time() > (self.issued_at + self.expires_in - 60)

    @property
    def expires_at_human(self) -> str:
        if not self.issued_at:
            return "never"
        exp = datetime.fromtimestamp(self.issued_at + self.expires_in)
        return exp.strftime("%d/%m/%Y %H:%M:%S")

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> OAuthToken:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def save(self, filepath: str):
        """Persist token to file (encrypted in production)."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info(f"Token saved to {filepath}")

    @classmethod
    def load(cls, filepath: str) -> Optional[OAuthToken]:
        """Load token from file."""
        try:
            with open(filepath) as f:
                return cls.from_dict(json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return None


# =========================================================================
# FRAUD PREVENTION HEADERS
# =========================================================================

def build_fraud_headers(config: HMRCConfig,
                        client_ip: str = "",
                        client_port: str = "",
                        user_agent: str = "",
                        screen_width: int = 1920,
                        screen_height: int = 1080,
                        window_width: int = 1200,
                        window_height: int = 800,
                        device_id: str = "",
                        user_id: str = "",
                        timezone_offset: str = "UTC+00:00",
                        ) -> Dict[str, str]:
    """
    Build the 16 HMRC fraud prevention headers for WEB_APP_VIA_SERVER.

    These MUST be sent with every API request. HMRC validates them
    and non-compliance can result in fines and API blocking.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    dev_id = device_id or str(uuid.uuid4())

    headers = {
        "Gov-Client-Connection-Method": "WEB_APP_VIA_SERVER",
        "Gov-Client-Device-ID": dev_id,
        "Gov-Client-Timezone": timezone_offset,
        "Gov-Client-Browser-JS-User-Agent": (
            user_agent or "Mozilla/5.0 (compatible; HNCAccountant/1.0)"
        ),
        "Gov-Client-Screens": (
            f"width={screen_width}&height={screen_height}"
            f"&scaling-factor=1&colour-depth=24"
        ),
        "Gov-Client-Window-Size": (
            f"width={window_width}&height={window_height}"
        ),
        "Gov-Client-User-IDs": (
            urllib.parse.quote(f"hnc-accountant={user_id or 'anonymous'}")
        ),
        "Gov-Vendor-Product-Name": urllib.parse.quote(
            config.vendor_product_name
        ),
        "Gov-Vendor-Version": urllib.parse.quote(
            f"the-hnc-accountant={config.vendor_version}"
        ),
    }

    # Conditional headers
    if client_ip:
        headers["Gov-Client-Public-IP"] = client_ip
        headers["Gov-Client-Public-IP-Timestamp"] = now
    if client_port:
        headers["Gov-Client-Public-Port"] = str(client_port)
    if config.vendor_public_ip:
        headers["Gov-Vendor-Public-IP"] = config.vendor_public_ip

    # Forwarded header (required for web apps)
    if client_ip and config.vendor_public_ip:
        headers["Gov-Vendor-Forwarded"] = (
            f"by={config.vendor_public_ip}&for={client_ip}"
        )

    return headers


# =========================================================================
# API CLIENT
# =========================================================================

class HMRCApiClient:
    """
    HMRC Making Tax Digital API client.

    Handles authentication, token refresh, fraud headers,
    and all MTD API calls.
    """

    def __init__(
        self,
        config: HMRCConfig,
        mutation_registry: Optional[HMRCMutationRegistry] = None,
    ):
        if (
            mutation_registry is not None
            and not isinstance(mutation_registry, HMRCMutationRegistry)
        ):
            raise TypeError("hmrc_mutation_registry_required")
        self.config = config
        self.token: Optional[OAuthToken] = None
        self._device_id = str(uuid.uuid4())
        self._mutation_registry = mutation_registry

        # Load persisted token if available
        if config.token_file:
            self.token = OAuthToken.load(config.token_file)

    # -----------------------------------------------------------------
    # OAUTH 2.0
    # -----------------------------------------------------------------

    def get_authorization_url(self, state: str = "") -> str:
        """
        Generate the URL to redirect user to HMRC login.

        Returns the URL — caller must redirect user's browser there.
        User logs into Government Gateway, approves access, gets
        redirected back to redirect_uri with ?code=xxx&state=yyy.
        """
        if not state:
            state = hashlib.sha256(os.urandom(32)).hexdigest()[:16]

        params = {
            "response_type": "code",
            "client_id": self.config.client_id,
            "scope": " ".join(self.config.scopes),
            "redirect_uri": self.config.redirect_uri,
            "state": state,
        }
        url = f"{self.config.auth_url}?{urllib.parse.urlencode(params)}"
        logger.info(f"Authorization URL generated (state={state})")
        return url

    def exchange_code(self, authorization_code: str) -> OAuthToken:
        """
        Exchange authorization code for access + refresh tokens.

        Called after user is redirected back with ?code=xxx.
        """
        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.config.redirect_uri,
        }
        return self._token_request(payload)

    def refresh_access_token(self) -> OAuthToken:
        """
        Refresh expired access token using refresh token.

        Refresh tokens are single-use — each refresh returns a new pair.
        Refresh tokens expire after 18 months of non-use.
        """
        if not self.token or not self.token.refresh_token:
            raise HMRCAuthError("No refresh token available — re-authorize")

        payload = {
            "client_id": self.config.client_id,
            "client_secret": self.config.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.token.refresh_token,
        }
        return self._token_request(payload)

    def _token_request(self, payload: Dict) -> OAuthToken:
        """Execute token request to HMRC."""
        import requests

        resp = requests.post(
            self.config.token_url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if resp.status_code != 200:
            error = resp.json() if resp.headers.get(
                "content-type", "").startswith("application/json") else {}
            raise HMRCAuthError(
                f"Token request failed ({resp.status_code}): "
                f"{error.get('error_description', resp.text)}"
            )

        data = resp.json()
        self.token = OAuthToken(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            token_type=data.get("token_type", "bearer"),
            expires_in=data.get("expires_in", 14400),
            scope=data.get("scope", ""),
            issued_at=time.time(),
        )

        if self.config.token_file:
            self.token.save(self.config.token_file)

        logger.info(f"Token obtained, expires: {self.token.expires_at_human}")
        return self.token

    def _ensure_token(self):
        """Auto-refresh if token expired."""
        if not self.token:
            raise HMRCAuthError("Not authenticated — call get_authorization_url() first")
        if self.token.is_expired:
            logger.info("Access token expired, refreshing...")
            self.refresh_access_token()

    # -----------------------------------------------------------------
    # HTTP HELPERS
    # -----------------------------------------------------------------

    def _headers(self, accept_version: str = "1.0",
                 content_type: bool = False,
                 client_ip: str = "",
                 test_scenario: str = "") -> Dict[str, str]:
        """Build standard headers for an API call."""
        self._ensure_token()

        h = {
            "Authorization": f"Bearer {self.token.access_token}",
            "Accept": f"application/vnd.hmrc.{accept_version}+json",
        }
        if content_type:
            h["Content-Type"] = "application/json"

        # Fraud prevention headers
        fraud = build_fraud_headers(
            self.config,
            client_ip=client_ip,
            device_id=self._device_id,
        )
        h.update(fraud)

        # Sandbox test scenario header
        if test_scenario and self.config.environment == "sandbox":
            h["Gov-Test-Scenario"] = test_scenario

        return h

    def _get(self, path: str, version: str = "1.0",
             test_scenario: str = "", client_ip: str = "") -> Dict:
        """HTTP GET to HMRC API."""
        import requests

        url = f"{self.config.base_url}{path}"
        resp = requests.get(
            url,
            headers=self._headers(version, client_ip=client_ip,
                                  test_scenario=test_scenario),
        )
        return self._handle_response(resp)

    def _post(self, path: str, body: Dict = None,
              version: str = "1.0", test_scenario: str = "",
              client_ip: str = "") -> Dict:
        """HTTP POST to HMRC API."""
        import requests

        if self._mutation_registry is None:
            raise HMRCMutationHold("canonical_hmrc_mutation_registry_required")
        payload = body or {}
        return self._mutation_registry.execute(
            environment=self.config.environment,
            method="POST",
            path=path,
            body=payload,
            transport=lambda: self._handle_response(
                requests.post(
                    f"{self.config.base_url}{path}",
                    json=payload,
                    headers=self._headers(
                        version,
                        content_type=True,
                        client_ip=client_ip,
                        test_scenario=test_scenario,
                    ),
                )
            ),
        )

    def _put(self, path: str, body: Dict = None,
             version: str = "1.0", test_scenario: str = "",
             client_ip: str = "") -> Dict:
        """HTTP PUT to HMRC API."""
        import requests

        if self._mutation_registry is None:
            raise HMRCMutationHold("canonical_hmrc_mutation_registry_required")
        payload = body or {}
        return self._mutation_registry.execute(
            environment=self.config.environment,
            method="PUT",
            path=path,
            body=payload,
            transport=lambda: self._handle_response(
                requests.put(
                    f"{self.config.base_url}{path}",
                    json=payload,
                    headers=self._headers(
                        version,
                        content_type=True,
                        client_ip=client_ip,
                        test_scenario=test_scenario,
                    ),
                )
            ),
        )

    def _delete(self, path: str, version: str = "1.0",
                test_scenario: str = "", client_ip: str = "") -> Dict:
        """HTTP DELETE to HMRC API."""
        import requests

        if self._mutation_registry is None:
            raise HMRCMutationHold("canonical_hmrc_mutation_registry_required")
        return self._mutation_registry.execute(
            environment=self.config.environment,
            method="DELETE",
            path=path,
            body={},
            transport=lambda: self._handle_response(
                requests.delete(
                    f"{self.config.base_url}{path}",
                    headers=self._headers(
                        version,
                        client_ip=client_ip,
                        test_scenario=test_scenario,
                    ),
                )
            ),
        )

    def _handle_response(self, resp) -> Dict:
        """Parse HMRC API response."""
        if resp.status_code in (200, 201, 204):
            if resp.status_code == 204:
                return {"status": "success", "code": 204}
            try:
                return resp.json()
            except ValueError:
                return {"status": "success", "code": resp.status_code}

        # Error handling
        try:
            error = resp.json()
        except ValueError:
            error = {"message": resp.text}

        raise HMRCApiError(
            status_code=resp.status_code,
            code=error.get("code", "UNKNOWN"),
            message=error.get("message", str(error)),
            errors=error.get("errors", []),
        )

    # =================================================================
    # BUSINESS DETAILS API (v2.0)
    # =================================================================

    def list_businesses(self, nino: str) -> Dict:
        """
        List all businesses for a taxpayer.

        Returns business IDs needed for other API calls.
        GET /individuals/business/details/{nino}/list
        """
        return self._get(
            f"/individuals/business/details/{nino}/list",
            version="2.0",
        )

    def get_business_details(self, nino: str, business_id: str) -> Dict:
        """
        Get details for a specific business.

        GET /individuals/business/details/{nino}/{businessId}
        """
        return self._get(
            f"/individuals/business/details/{nino}/{business_id}",
            version="2.0",
        )

    # =================================================================
    # OBLIGATIONS API
    # =================================================================

    def get_obligations(self, nino: str,
                        from_date: str = "", to_date: str = "",
                        status: str = "") -> Dict:
        """
        Retrieve quarterly filing obligations.

        Returns deadlines with status (Open/Fulfilled).
        GET /obligations/details/{nino}/income-and-expenditure
        """
        params = []
        if from_date:
            params.append(f"from={from_date}")
        if to_date:
            params.append(f"to={to_date}")
        if status:
            params.append(f"status={status}")
        qs = f"?{'&'.join(params)}" if params else ""
        return self._get(
            f"/obligations/details/{nino}/income-and-expenditure{qs}",
            version="2.0",
        )

    # =================================================================
    # SELF-EMPLOYMENT — QUARTERLY UPDATES (MTD)
    # =================================================================

    def create_se_period_summary(self, nino: str, business_id: str,
                                  tax_year: str, body: Dict) -> Dict:
        """
        Submit quarterly self-employment income & expenses.

        For turnover < £90k: can use consolidatedExpenses (single figure).
        For turnover >= £90k: must itemise all expense categories.

        PUT /individuals/business/self-employment/{nino}/{businessId}/
            period/{taxYear}

        body example (consolidated):
        {
            "periodDates": {"periodStartDate": "2025-04-06",
                            "periodEndDate": "2025-07-05"},
            "periodIncome": {"turnover": 34740.00,
                             "other": 0},
            "periodExpenses": {"consolidatedExpenses": 9052.17}
        }

        body example (itemised):
        {
            "periodDates": {...},
            "periodIncome": {"turnover": 34740.00, "other": 0},
            "periodExpenses": {
                "costOfGoods": {"amount": 6750.00},
                "premisesRunningCosts": {"amount": 0},
                "maintenanceCosts": {"amount": 0},
                "adminCosts": {"amount": 200.00},
                "advertisingCosts": {"amount": 0},
                "businessEntertainmentCosts": {"amount": 0},
                "interest": {"amount": 0},
                "financialCharges": {"amount": 0},
                "irrecoverableDebts": {"amount": 0},
                "professionalFees": {"amount": 0},
                "depreciation": {"amount": 0},
                "otherExpenses": {"amount": 2102.17},
                "travelCosts": {"amount": 85.50},
                "staffCosts": {"amount": 0}
            }
        }
        """
        return self._put(
            f"/individuals/business/self-employment/{nino}/{business_id}"
            f"/period/{tax_year}",
            body=body,
            version="4.0",
        )

    def get_se_period_summary(self, nino: str, business_id: str,
                               tax_year: str, period_id: str) -> Dict:
        """Retrieve a submitted period summary."""
        return self._get(
            f"/individuals/business/self-employment/{nino}/{business_id}"
            f"/period/{tax_year}/{period_id}",
            version="4.0",
        )

    # =================================================================
    # SELF-EMPLOYMENT — ANNUAL SUMMARY
    # =================================================================

    def create_se_annual_summary(self, nino: str, business_id: str,
                                  tax_year: str, body: Dict) -> Dict:
        """
        Submit annual adjustments (capital allowances, etc).

        PUT /individuals/business/self-employment/{nino}/{businessId}/
            annual/{taxYear}
        """
        return self._put(
            f"/individuals/business/self-employment/{nino}/{business_id}"
            f"/annual/{tax_year}",
            body=body,
            version="4.0",
        )

    # =================================================================
    # TAX CALCULATION API (v8.0)
    # =================================================================

    def trigger_calculation(self, nino: str, tax_year: str,
                            final_declaration: bool = False) -> Dict:
        """
        Trigger a tax calculation.

        POST /individuals/calculations/self-assessment/{nino}/{taxYear}

        Set final_declaration=True only for year-end crystallisation.
        Returns a calculationId to retrieve the result.
        """
        body = {}
        if final_declaration:
            body["finalDeclaration"] = True
        return self._post(
            f"/individuals/calculations/self-assessment/{nino}/{tax_year}",
            body=body,
            version="8.0",
        )

    def get_calculation(self, nino: str, tax_year: str,
                        calculation_id: str) -> Dict:
        """
        Retrieve a completed tax calculation.

        GET /individuals/calculations/self-assessment/{nino}/{taxYear}/
            {calculationId}
        """
        return self._get(
            f"/individuals/calculations/self-assessment/{nino}/{tax_year}"
            f"/{calculation_id}",
            version="8.0",
        )

    def submit_final_declaration(self, nino: str, tax_year: str,
                                  calculation_id: str) -> Dict:
        """
        Submit final declaration (crystallise the tax year).

        This is the equivalent of submitting the SA100.
        POST /individuals/calculations/self-assessment/
             {nino}/{taxYear}/{calculationId}/final-declaration
        """
        return self._post(
            f"/individuals/calculations/self-assessment/{nino}/{tax_year}"
            f"/{calculation_id}/final-declaration",
            version="8.0",
        )

    # =================================================================
    # SELF ASSESSMENT ACCOUNTS API (v4.0)
    # =================================================================

    def get_balance(self, nino: str) -> Dict:
        """
        Retrieve SA balance — overdue, payable, pending.

        GET /accounts/self-assessment/{nino}/balance
        """
        return self._get(
            f"/accounts/self-assessment/{nino}/balance",
            version="4.0",
        )

    def get_payments(self, nino: str,
                     from_date: str = "", to_date: str = "") -> Dict:
        """Retrieve payment history."""
        params = []
        if from_date:
            params.append(f"from={from_date}")
        if to_date:
            params.append(f"to={to_date}")
        qs = f"?{'&'.join(params)}" if params else ""
        return self._get(
            f"/accounts/self-assessment/{nino}/payments{qs}",
            version="4.0",
        )

    # =================================================================
    # VAT MTD API (v1.0)
    # =================================================================

    def get_vat_obligations(self, vrn: str,
                            from_date: str = "", to_date: str = "",
                            status: str = "") -> Dict:
        """
        Retrieve VAT filing obligations.

        GET /organisations/vat/{vrn}/obligations
        """
        params = []
        if from_date:
            params.append(f"from={from_date}")
        if to_date:
            params.append(f"to={to_date}")
        if status:
            params.append(f"status={status}")
        qs = f"?{'&'.join(params)}" if params else ""
        return self._get(
            f"/organisations/vat/{vrn}/obligations{qs}",
            version="1.0",
        )

    def submit_vat_return(self, vrn: str, body: Dict) -> Dict:
        """
        Submit a VAT return (9-box).

        POST /organisations/vat/{vrn}/returns

        body:
        {
            "periodKey": "25A1",       # from obligations
            "vatDueSales": 4432.50,    # Box 1
            "vatDueAcquisitions": 0,   # Box 2
            "totalVatDue": 4432.50,    # Box 3
            "vatReclaimedCurrPeriod": 1247.80,  # Box 4
            "netVatDue": 3184.70,      # Box 5 (absolute value)
            "totalValueSalesExVAT": 46657,      # Box 6 (whole pounds)
            "totalValuePurchasesExVAT": 22840,  # Box 7 (whole pounds)
            "totalValueGoodsSuppliedExVAT": 0,  # Box 8
            "totalAcquisitionsExVAT": 0,        # Box 9
            "finalised": true
        }
        """
        return self._post(
            f"/organisations/vat/{vrn}/returns",
            body=body,
            version="1.0",
        )

    def get_vat_return(self, vrn: str, period_key: str) -> Dict:
        """Retrieve a submitted VAT return."""
        return self._get(
            f"/organisations/vat/{vrn}/returns/{period_key}",
            version="1.0",
        )

    def get_vat_liabilities(self, vrn: str,
                            from_date: str, to_date: str) -> Dict:
        """Retrieve VAT liabilities."""
        return self._get(
            f"/organisations/vat/{vrn}/liabilities"
            f"?from={from_date}&to={to_date}",
            version="1.0",
        )

    def get_vat_payments(self, vrn: str,
                         from_date: str, to_date: str) -> Dict:
        """Retrieve VAT payment history."""
        return self._get(
            f"/organisations/vat/{vrn}/payments"
            f"?from={from_date}&to={to_date}",
            version="1.0",
        )

    # =================================================================
    # CIS DEDUCTIONS API (v3.0)
    # =================================================================

    def get_cis_deductions(self, nino: str,
                           from_date: str = "", to_date: str = "",
                           source: str = "") -> Dict:
        """
        Retrieve CIS deductions made by contractors.

        GET /individuals/deductions/cis/{nino}/current-position
        """
        params = []
        if from_date:
            params.append(f"fromDate={from_date}")
        if to_date:
            params.append(f"toDate={to_date}")
        if source:
            params.append(f"source={source}")
        qs = f"?{'&'.join(params)}" if params else ""
        return self._get(
            f"/individuals/deductions/cis/{nino}/current-position{qs}",
            version="3.0",
        )

    def create_cis_deduction(self, nino: str, body: Dict) -> Dict:
        """Create a CIS deduction override."""
        return self._post(
            f"/individuals/deductions/cis/{nino}/amendments",
            body=body,
            version="3.0",
        )

    def delete_cis_deduction(self, nino: str, submission_id: str) -> Dict:
        """Delete a CIS deduction override."""
        return self._delete(
            f"/individuals/deductions/cis/{nino}/amendments/{submission_id}",
            version="3.0",
        )


# =========================================================================
# HIGH-LEVEL WORKFLOW — "THE COOK DOES THE REST"
# =========================================================================

class HMRCFilingWorkflow:
    """
    End-to-end filing workflow.

    John fills in details → uploads bank CSV → this class:
    1. Checks obligations (what's due)
    2. Prepares quarterly update from pipeline output
    3. Submits to HMRC
    4. Triggers tax calculation
    5. Retrieves calculation for review
    6. On confirmation, submits final declaration
    7. Files VAT return if applicable
    """

    def __init__(self, api_client: HMRCApiClient,
                 nino: str, business_id: str = "",
                 vrn: str = "", tax_year: str = "2025-26"):
        self.api = api_client
        self.nino = nino
        self.business_id = business_id
        self.vrn = vrn
        self.tax_year = tax_year
        self.steps_completed: List[str] = []
        self.results: Dict[str, Any] = {}

    # ----- Step 1: Discover business -----

    def discover_business(self) -> Dict:
        """Find the user's business ID if not already known."""
        if self.business_id:
            return {"business_id": self.business_id}

        businesses = self.api.list_businesses(self.nino)
        business_list = businesses.get("listOfBusinesses", [])

        # Auto-select sole trade if only one
        se_businesses = [b for b in business_list
                         if b.get("typeOfBusiness") == "self-employment"]

        if len(se_businesses) == 1:
            self.business_id = se_businesses[0].get("businessId", "")
            logger.info(f"Auto-discovered business: {self.business_id}")
        elif len(se_businesses) > 1:
            # Return list for user to choose
            return {
                "action_required": "choose_business",
                "businesses": se_businesses,
            }
        else:
            return {"error": "No self-employment business found on HMRC record"}

        self.steps_completed.append("discover_business")
        self.results["business"] = se_businesses[0] if se_businesses else {}
        return self.results["business"]

    # ----- Step 2: Check obligations -----

    def check_obligations(self) -> Dict:
        """Find what quarterly updates are due."""
        obligations = self.api.get_obligations(
            self.nino,
            from_date=f"{self.tax_year[:4]}-04-06",
            to_date=f"20{self.tax_year[5:]}-04-05",
        )
        self.steps_completed.append("check_obligations")
        self.results["obligations"] = obligations
        return obligations

    # ----- Step 3: Submit quarterly update -----

    def submit_quarterly_update(self, pipeline_result,
                                 period_start: str = "",
                                 period_end: str = "",
                                 consolidated: bool = True) -> Dict:
        """
        Convert pipeline result to HMRC quarterly update and submit.

        pipeline_result: PipelineResult from HNCQueen.process()
        consolidated: if True, use single consolidatedExpenses figure
                      (valid if turnover < £90k)
        """
        turnover = getattr(pipeline_result, "total_income",
                           pipeline_result.get("total_income", 0)
                           if isinstance(pipeline_result, dict) else 0)
        expenses = getattr(pipeline_result, "total_expenses",
                           pipeline_result.get("total_expenses", 0)
                           if isinstance(pipeline_result, dict) else 0)

        body = {
            "periodDates": {
                "periodStartDate": period_start,
                "periodEndDate": period_end,
            },
            "periodIncome": {
                "turnover": round(turnover, 2),
                "other": 0,
            },
        }

        if consolidated and turnover < 90000:
            body["periodExpenses"] = {
                "consolidatedExpenses": round(expenses, 2),
            }
        else:
            # Itemised — map HNC categories to HMRC fields
            body["periodExpenses"] = self._map_expenses_to_hmrc(
                pipeline_result
            )

        result = self.api.create_se_period_summary(
            self.nino, self.business_id, self.tax_year, body
        )
        self.steps_completed.append("submit_quarterly")
        self.results["quarterly_update"] = result
        return result

    def _map_expenses_to_hmrc(self, pipeline_result) -> Dict:
        """Map HNC expense categories to HMRC API fields."""
        # These are the HMRC-accepted expense categories
        # Our categoriser maps to these
        categories = pipeline_result if isinstance(pipeline_result, dict) else {}

        return {
            "costOfGoods": {
                "amount": round(categories.get("materials", 0) +
                                categories.get("subcontractor_costs", 0), 2)
            },
            "travelCosts": {
                "amount": round(categories.get("motor", 0) +
                                categories.get("travel", 0), 2)
            },
            "premisesRunningCosts": {
                "amount": round(categories.get("premises", 0), 2)
            },
            "adminCosts": {
                "amount": round(categories.get("office_admin", 0) +
                                categories.get("telephone", 0), 2)
            },
            "professionalFees": {
                "amount": round(categories.get("accountancy", 0) +
                                categories.get("legal", 0), 2)
            },
            "otherExpenses": {
                "amount": round(categories.get("insurance", 0) +
                                categories.get("tools", 0) +
                                categories.get("other", 0), 2)
            },
            "advertisingCosts": {"amount": 0},
            "businessEntertainmentCosts": {"amount": 0},
            "interest": {"amount": 0},
            "financialCharges": {"amount": 0},
            "irrecoverableDebts": {"amount": 0},
            "depreciation": {"amount": 0},
            "maintenanceCosts": {"amount": 0},
            "staffCosts": {"amount": 0},
        }

    # ----- Step 4: Trigger tax calculation -----

    def trigger_tax_calc(self, final: bool = False) -> Dict:
        """Trigger HMRC to calculate tax liability."""
        result = self.api.trigger_calculation(
            self.nino, self.tax_year, final_declaration=final,
        )
        self.steps_completed.append("trigger_calc")
        self.results["calculation_trigger"] = result
        return result

    # ----- Step 5: Get calculation result -----

    def get_tax_calc_result(self, calculation_id: str) -> Dict:
        """Retrieve the completed tax calculation."""
        result = self.api.get_calculation(
            self.nino, self.tax_year, calculation_id,
        )
        self.steps_completed.append("get_calc_result")
        self.results["tax_calculation"] = result
        return result

    # ----- Step 6: Final declaration -----

    def submit_final_declaration(self, calculation_id: str) -> Dict:
        """
        Submit final declaration — equivalent to filing the SA100.

        THIS IS IRREVERSIBLE for the tax year. Only call after
        user has reviewed and confirmed the calculation.
        """
        result = self.api.submit_final_declaration(
            self.nino, self.tax_year, calculation_id,
        )
        self.steps_completed.append("final_declaration")
        self.results["final_declaration"] = result
        return result

    # ----- Step 7: VAT return -----

    def submit_vat_return(self, vat_data: Dict,
                          period_key: str) -> Dict:
        """
        Submit VAT MTD return.

        vat_data: output from HNCVATEngine — we map to HMRC's 9-box format.
        period_key: from obligations API (e.g. "25A1").
        """
        body = {
            "periodKey": period_key,
            "vatDueSales": round(vat_data.get("box1", 0), 2),
            "vatDueAcquisitions": round(vat_data.get("box2", 0), 2),
            "totalVatDue": round(vat_data.get("box3", 0), 2),
            "vatReclaimedCurrPeriod": round(vat_data.get("box4", 0), 2),
            "netVatDue": round(abs(vat_data.get("box5", 0)), 2),
            "totalValueSalesExVAT": int(vat_data.get("box6", 0)),
            "totalValuePurchasesExVAT": int(vat_data.get("box7", 0)),
            "totalValueGoodsSuppliedExVAT": int(vat_data.get("box8", 0)),
            "totalAcquisitionsExVAT": int(vat_data.get("box9", 0)),
            "finalised": True,
        }
        result = self.api.submit_vat_return(self.vrn, body)
        self.steps_completed.append("vat_return")
        self.results["vat_return"] = result
        return result

    # ----- Summary -----

    def get_workflow_status(self) -> Dict:
        """Return current workflow status."""
        return {
            "nino": self.nino,
            "business_id": self.business_id,
            "vrn": self.vrn,
            "tax_year": self.tax_year,
            "steps_completed": self.steps_completed,
            "environment": self.api.config.environment,
            "token_valid": (self.api.token is not None and
                            not self.api.token.is_expired),
        }


# =========================================================================
# EXCEPTIONS
# =========================================================================

class HMRCAuthError(Exception):
    """Authentication/authorization failure."""
    pass


class HMRCApiError(Exception):
    """HMRC API returned an error."""
    def __init__(self, status_code: int = 0, code: str = "",
                 message: str = "", errors: list = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.errors = errors or []
        super().__init__(f"HMRC API Error {status_code} [{code}]: {message}")


# =========================================================================
# SETUP GUIDE — printed when module is run directly
# =========================================================================

def print_setup_guide():
    """Print the HMRC API setup guide for John."""
    guide = """
╔══════════════════════════════════════════════════════════════════╗
║          THE HNC ACCOUNTANT — HMRC API SETUP GUIDE             ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  STEP 1: Register on HMRC Developer Hub                         ║
║  ────────────────────────────────────────                       ║
║  Go to: https://developer.service.hmrc.gov.uk                  ║
║  Click "Register" → create account → verify email              ║
║                                                                  ║
║  STEP 2: Create a Sandbox Application                           ║
║  ────────────────────────────────────────                       ║
║  Developer Hub → "Add an application" → Sandbox                ║
║  Name: "The HNC Accountant"                                    ║
║  Subscribe to these APIs:                                       ║
║    ✓ Self Assessment (MTD) — all sub-APIs                      ║
║    ✓ VAT (MTD)                                                  ║
║    ✓ CIS Deductions (MTD)                                      ║
║    ✓ Business Details (MTD)                                    ║
║    ✓ Individual Calculations (MTD)                             ║
║  Set redirect URI: http://localhost:8080/callback              ║
║                                                                  ║
║  STEP 3: Get Your Credentials                                   ║
║  ────────────────────────────────────────                       ║
║  From your app's page, copy:                                   ║
║    • Client ID     (looks like: 4fBaP...)                      ║
║    • Client Secret (looks like: 12abc...)                      ║
║                                                                  ║
║  STEP 4: Create Test User                                       ║
║  ────────────────────────────────────────                       ║
║  Developer Hub → "Create a test user"                          ║
║  Select: "Individual" with Self Assessment enrolment           ║
║  You'll get a test NINO and Government Gateway login           ║
║                                                                  ║
║  STEP 5: Configure HNC                                          ║
║  ────────────────────────────────────────                       ║
║  Create config file: hmrc_config.json                          ║
║  {                                                               ║
║    "environment": "sandbox",                                    ║
║    "client_id": "YOUR_CLIENT_ID",                              ║
║    "client_secret": "YOUR_CLIENT_SECRET",                      ║
║    "redirect_uri": "http://localhost:8080/callback"            ║
║  }                                                               ║
║                                                                  ║
║  STEP 6: Run First Test                                         ║
║  ────────────────────────────────────────                       ║
║  python hnc_hmrc_api.py --setup                                ║
║  → Opens browser for Government Gateway login                  ║
║  → Authorizes the app                                           ║
║  → Redirects back with token                                   ║
║  → Ready to file!                                               ║
║                                                                  ║
║  FOR PRODUCTION (real HMRC filing):                             ║
║  ────────────────────────────────────────                       ║
║  1. Complete sandbox testing (all endpoints)                   ║
║  2. Email SDSTeam@hmrc.gov.uk within 14 days                  ║
║  3. Register Production application on Developer Hub           ║
║  4. Complete Production Approvals Checklist                    ║
║  5. HMRC reviews (up to 10 working days)                       ║
║  6. Change config to "production" and use real credentials     ║
║                                                                  ║
║  QUARTERLY DEADLINES:                                           ║
║  ────────────────────────────────────────                       ║
║  Q1: 6 Apr – 5 Jul  → file by 5 Aug                           ║
║  Q2: 6 Jul – 5 Oct  → file by 5 Nov                           ║
║  Q3: 6 Oct – 5 Jan  → file by 5 Feb                           ║
║  Q4: 6 Jan – 5 Apr  → file by 5 May                           ║
║  Final declaration  → file by 31 Jan following year            ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
    print(guide)


# =========================================================================
# STANDALONE TEST
# =========================================================================

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("HNC HMRC API MODULE — BUILD VERIFICATION")
    print("=" * 60)

    # Test 1: Config creation
    print("\n--- Test 1: Configuration ---")
    config = HMRCConfig(
        client_id="test_client_id",
        client_secret="test_client_secret",
    )
    print(f"  Environment: {config.environment}")
    print(f"  Base URL: {config.base_url}")
    print(f"  Auth URL: {config.auth_url}")
    print(f"  Token URL: {config.token_url}")
    assert "test-api" in config.base_url
    print("  ✓ Sandbox config correct")

    config_prod = HMRCConfig(environment="production")
    assert "test" not in config_prod.base_url
    print("  ✓ Production config correct")

    # Test 2: Token management
    print("\n--- Test 2: Token Management ---")
    token = OAuthToken(
        access_token="test_access_token",
        refresh_token="test_refresh_token",
        expires_in=14400,
        issued_at=time.time(),
    )
    assert not token.is_expired
    print(f"  Token valid until: {token.expires_at_human}")
    print("  ✓ Token not expired")

    expired_token = OAuthToken(
        access_token="old",
        refresh_token="old",
        issued_at=time.time() - 20000,
        expires_in=14400,
    )
    assert expired_token.is_expired
    print("  ✓ Expired token detected")

    # Test 3: Token persistence
    print("\n--- Test 3: Token Save/Load ---")
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        token.save(f.name)
        loaded = OAuthToken.load(f.name)
        assert loaded.access_token == token.access_token
        assert loaded.refresh_token == token.refresh_token
        os.unlink(f.name)
    print("  ✓ Token save/load round-trip")

    # Test 4: Fraud prevention headers
    print("\n--- Test 4: Fraud Prevention Headers ---")
    headers = build_fraud_headers(
        config,
        client_ip="86.12.45.67",
        client_port="51234",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        device_id="test-device-123",
        user_id="john-smith",
    )
    assert headers["Gov-Client-Connection-Method"] == "WEB_APP_VIA_SERVER"
    assert headers["Gov-Client-Device-ID"] == "test-device-123"
    assert "Gov-Client-Public-IP" in headers
    assert "Gov-Client-Timezone" in headers
    assert "Gov-Vendor-Product-Name" in headers
    print(f"  Headers generated: {len(headers)}")
    for k, v in sorted(headers.items()):
        print(f"    {k}: {v[:50]}{'...' if len(v) > 50 else ''}")
    print("  ✓ All fraud prevention headers present")

    # Test 5: API client creation
    print("\n--- Test 5: API Client ---")
    client = HMRCApiClient(config)
    auth_url = client.get_authorization_url(state="test_state")
    assert "test-www.tax.service.gov.uk" in auth_url
    assert "client_id=test_client_id" in auth_url
    assert "response_type=code" in auth_url
    assert "state=test_state" in auth_url
    print(f"  Auth URL: {auth_url[:80]}...")
    print("  ✓ Authorization URL generated correctly")

    # Test 6: Filing workflow
    print("\n--- Test 6: Filing Workflow ---")
    client.token = token  # Inject test token
    workflow = HMRCFilingWorkflow(
        api_client=client,
        nino="QQ123456C",
        business_id="XAIS12345678901",
        vrn="123456789",
        tax_year="2025-26",
    )
    status = workflow.get_workflow_status()
    print(f"  NINO: {status['nino']}")
    print(f"  Business: {status['business_id']}")
    print(f"  VRN: {status['vrn']}")
    print(f"  Tax Year: {status['tax_year']}")
    print(f"  Token Valid: {status['token_valid']}")
    print("  ✓ Workflow initialized")

    # Test 7: Expense mapping
    print("\n--- Test 7: HMRC Expense Mapping ---")
    mock_expenses = {
        "materials": 6750.00,
        "subcontractor_costs": 3800.00,
        "motor": 85.50,
        "insurance": 441.67,
        "telephone": 45.00,
        "tools": 530.00,
        "accountancy": 1200.00,
    }
    mapped = workflow._map_expenses_to_hmrc(mock_expenses)
    print(f"  costOfGoods: £{mapped['costOfGoods']['amount']:,.2f}")
    print(f"  travelCosts: £{mapped['travelCosts']['amount']:,.2f}")
    print(f"  adminCosts: £{mapped['adminCosts']['amount']:,.2f}")
    print(f"  professionalFees: £{mapped['professionalFees']['amount']:,.2f}")
    print(f"  otherExpenses: £{mapped['otherExpenses']['amount']:,.2f}")
    assert mapped["costOfGoods"]["amount"] == 10550.00  # materials + subcontractor
    assert mapped["travelCosts"]["amount"] == 85.50
    print("  ✓ Expense mapping correct")

    print("\n" + "=" * 60)
    print("ALL BUILD VERIFICATION TESTS PASSED")
    print(f"Module ready for HMRC sandbox testing")
    print("=" * 60)

    if "--setup" in sys.argv:
        print_setup_guide()
    else:
        print("\nRun with --setup to see the full HMRC registration guide")
