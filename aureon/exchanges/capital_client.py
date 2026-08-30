import json
import logging
import math
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from aureon.governance.economic_boundary import (
    EconomicGovernanceBlocked,
    _capital_economic_transport_body_digest,
    _claim_capital_economic_transport_context,
)

# Ensure repo-root package imports and env resolution work when launched directly.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Load environment variables from repo-root .env first.
try:
    from dotenv import load_dotenv
    env_path = os.path.join(_REPO_ROOT, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)
    else:
        load_dotenv(override=False)
except ImportError:
    pass

try:
    from aureon.core.aureon_env import load_aureon_environment

    load_aureon_environment(Path(_REPO_ROOT), override=False)
except Exception:
    pass

logger = logging.getLogger(__name__)

# Module-level shared session cache to prevent multiple instances from
# flooding Capital.com with independent session requests.
_SHARED_SESSION: Dict[str, Any] = {
    "cst": None,
    "x_security_token": None,
    "session_start_time": 0.0,
    "demo_mode": None,
    "rate_limit_until": 0.0,
    "init_error": "",
}

# Module-level shared market cache so multiple CapitalClient instances
# don't each re-download the full market catalogue.
_SHARED_MARKET_CACHE: Dict[str, Any] = {
    "markets": [],
    "market_index": {},
    "market_cache_time": 0.0,
}

CAPITAL_HTTP_TIMEOUT = float(os.getenv('CAPITAL_HTTP_TIMEOUT_SECS', '8'))
CAPITAL_SESSION_RETRY_BACKOFF_SECS = float(os.getenv('CAPITAL_SESSION_RETRY_BACKOFF_SECS', '15'))
CAPITAL_TICKER_WORKERS = int(os.getenv('CAPITAL_TICKER_WORKERS', '4'))
CAPITAL_TICKER_MEM_TTL = float(os.getenv('CAPITAL_TICKER_MEM_TTL', '25.0'))  # In-memory per-symbol ticker cache TTL
CAPITAL_MONITOR_CACHE_PATH = os.getenv("CAPITAL_MONITOR_CACHE_PATH", os.path.join("ws_cache", "capital_monitor.json"))
CAPITAL_MONITOR_CACHE_MAX_AGE_S = float(os.getenv("CAPITAL_MONITOR_CACHE_MAX_AGE_S", "20"))
CAPITAL_QUOTE_MAX_AGE_S = float(os.getenv("CAPITAL_QUOTE_MAX_AGE_S", "120"))
CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S = float(os.getenv("CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S", "300"))
CAPITAL_FUTURE_SKEW_S = float(os.getenv("CAPITAL_FUTURE_SKEW_S", "5"))
CAPITAL_LIVE_BASE = "https://api-capital.backend-capital.com/api/v1"
CAPITAL_DEMO_BASE = "https://demo-api-capital.backend-capital.com/api/v1"
_CAPITAL_DEAL_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]*")
# Disk cache for market catalogue — survives process restarts, avoids re-downloading 6799 markets
CAPITAL_MARKET_DISK_CACHE_PATH = os.getenv(
    "CAPITAL_MARKET_DISK_CACHE_PATH",
    os.path.join(_REPO_ROOT, "ws_cache", "capital_market_catalogue.json"),
)


def _is_capital_economic_mutation_path(method: str, path: str) -> bool:
    """Return whether an exact Capital route changes economic state."""

    normalized_method = str(method).strip().upper()
    if not isinstance(path, str) or not path.startswith("/"):
        return False
    if "?" in path or "#" in path or "//" in path:
        return False
    if normalized_method == "POST":
        return path in {"/positions", "/workingorders"}
    parts = path.split("/")
    if (
        normalized_method in {"PUT", "DELETE"}
        and len(parts) == 3
        and parts[1] in {"positions", "workingorders"}
        and _CAPITAL_DEAL_ID_RE.fullmatch(parts[2]) is not None
        and parts[2] not in {".", ".."}
    ):
        return normalized_method == "DELETE" or parts[1] == "positions"
    return False


def _finite_number(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Optional[float]:
    """Return a finite provider number without manufacturing a fallback."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if not math.isfinite(number):
        return None
    if positive and number <= 0:
        return None
    if nonnegative and number < 0:
        return None
    return number


def _provider_timestamp(value: Any) -> Optional[float]:
    """Parse an immutable provider timestamp as UTC epoch seconds."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        numeric = _finite_number(value, positive=True)
        if numeric is None:
            return None
        while numeric > 100_000_000_000:
            numeric /= 1000.0
        return numeric
    else:
        raw = str(value).strip()
        if not raw:
            return None
        numeric = _finite_number(raw, positive=True)
        if numeric is not None:
            while numeric > 100_000_000_000:
                numeric /= 1000.0
            return numeric
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = parsedate_to_datetime(raw)
            except (TypeError, ValueError, OverflowError):
                return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        timestamp = dt.astimezone(timezone.utc).timestamp()
    except (OverflowError, OSError, ValueError):
        return None
    return timestamp if math.isfinite(timestamp) and timestamp > 0 else None


def _fresh_provider_timestamp(
    value: Any,
    max_age_s: float,
    *,
    received_at: Optional[float] = None,
) -> Optional[float]:
    timestamp = _provider_timestamp(value)
    reference = time.time() if received_at is None else received_at
    if timestamp is None or not math.isfinite(reference):
        return None
    age = reference - timestamp
    if age < -CAPITAL_FUTURE_SKEW_S or age > max_age_s:
        return None
    return timestamp


def _response_source_timestamp(response: Any) -> Optional[float]:
    """Use the provider HTTP Date header when an endpoint has no body time."""
    headers = getattr(response, "headers", None)
    if not hasattr(headers, "get"):
        return None
    return _provider_timestamp(headers.get("Date"))


class ObservationList(list):
    """List-compatible observation surface with non-numeric provenance metadata."""

    def __init__(self, values=(), **provenance: Any):
        super().__init__(values)
        self.truth_status = str(provenance.get("truth_status") or "no_data")
        self.reason = str(provenance.get("reason") or "")
        self.source_timestamp = provenance.get("source_timestamp")
        self.received_at = provenance.get("received_at")
        self.generated_values = False


class BalanceObservation(dict):
    """Dict-compatible currency map that keeps provenance out of numeric items."""

    def __init__(self, values=None, **provenance: Any):
        super().__init__(values or {})
        self.truth_status = str(provenance.get("truth_status") or "no_data")
        self.reason = str(provenance.get("reason") or "")
        self.source_timestamp = provenance.get("source_timestamp")
        self.received_at = provenance.get("received_at")
        self.source_ids = list(provenance.get("source_ids") or [])
        self.generated_values = False

class CapitalClient:
    """
    Client for Capital.com API.
    Handles session management and trading operations.
    """
    def __init__(self):
        self.api_key = os.getenv('CAPITAL_API_KEY')
        self.identifier = os.getenv('CAPITAL_IDENTIFIER')
        # Support both legacy and documented env names.
        self.password = os.getenv('CAPITAL_PASSWORD') or os.getenv('CAPITAL_API_PASSWORD')
        self.demo_mode = os.getenv('CAPITAL_DEMO', '0') == '1'
        self.init_error = ""

        if self.demo_mode:
            self.base_url = CAPITAL_DEMO_BASE
        else:
            self.base_url = CAPITAL_LIVE_BASE

        self.dry_run = False  # ALWAYS LIVE
        # Share session tokens across all CapitalClient instances
        global _SHARED_SESSION
        if _SHARED_SESSION.get("demo_mode") is None:
            _SHARED_SESSION["demo_mode"] = self.demo_mode
        if _SHARED_SESSION.get("demo_mode") == self.demo_mode and _SHARED_SESSION.get("cst"):
            self.cst = _SHARED_SESSION.get("cst")
            self.x_security_token = _SHARED_SESSION.get("x_security_token")
            self.session_start_time = float(_SHARED_SESSION.get("session_start_time", 0.0) or 0.0)
            self.init_error = str(_SHARED_SESSION.get("init_error", "") or "")
        else:
            self.cst = None
            self.x_security_token = None
            self.session_start_time = 0
        # Share market cache across instances to avoid duplicate catalogue downloads
        global _SHARED_MARKET_CACHE
        self.market_cache: List[Dict[str, Any]] = list(_SHARED_MARKET_CACHE.get("markets", []))
        self.market_index: Dict[str, Dict[str, Any]] = dict(_SHARED_MARKET_CACHE.get("market_index", {}))
        self.market_cache_time = float(_SHARED_MARKET_CACHE.get("market_cache_time", 0.0) or 0.0)
        self.market_cache_ttl = int(os.getenv('CAPITAL_MARKET_CACHE_TTL', '3600'))  # 60 minutes (was 15)
        self._rate_limit_until = 0  # Timestamp when rate limit expires
        self._rate_limit_logged = False  # Only log rate limits once
        self._session_error_logged = False  # Only log session errors once
        self._next_session_retry_at = 0.0
        self._ticker_mem_cache: Dict[str, Dict[str, Any]] = {}  # In-memory per-symbol ticker cache
        self._ticker_mem_cache_times: Dict[str, float] = {}    # Fetch timestamps for TTL
        self._accounts_cache: ObservationList = ObservationList()  # In-memory accounts cache
        self._accounts_cache_time: float = 0.0                  # Accounts cache fetch timestamp
        self._snapshot_cache: Dict[str, Any] = {}               # In-memory market snapshot cache {epic: data}
        self._snapshot_cache_times: Dict[str, float] = {}       # Snapshot cache fetch timestamps
        self.last_account_observation = BalanceObservation(
            truth_status="no_data",
            reason="not_fetched",
            received_at=time.time(),
        )
        self.last_ticker_observation: Dict[str, Any] = {
            "truth_status": "no_data",
            "reason": "not_fetched",
            "source_timestamp": None,
            "received_at": time.time(),
            "generated_values": False,
            "action_eligible": False,
        }
        self._pending_close_confirmations: Dict[str, Dict[str, Any]] = {}
        self._economic_dispatch_lock = threading.RLock()
        self._economic_dispatches: Dict[object, tuple[str, str, str]] = {}

        if not self.api_key or not self.identifier or not self.password:
            logger.warning("Capital.com credentials not fully set. Client will be disabled.")
            self.enabled = False
            self.init_error = "credentials_missing"
        else:
            self.enabled = True
            self._create_session()

    @staticmethod
    def _error_response(status_code: int, error_code: str, detail: str = ""):
        class ErrorResponse:
            def __init__(self, code: int, err: str, msg: str):
                self.status_code = code
                self._payload = {"errorCode": err, "detail": msg}
                self.text = json.dumps(self._payload)

            def json(self):
                return dict(self._payload)

        return ErrorResponse(status_code, error_code, detail)

    def _create_session(self):
        """Create a new session to get CST and X-SECURITY-TOKEN."""
        if not self.enabled:
            return

        global _SHARED_SESSION
        now = time.time()

        # Check global rate limit first
        if now < _SHARED_SESSION.get("rate_limit_until", 0.0):
            self._rate_limit_until = _SHARED_SESSION.get("rate_limit_until", 0.0)
            self.init_error = "rate_limited"
            return  # Still rate limited globally, skip silently

        # Check if we're rate limited
        if now < self._rate_limit_until:
            return  # Still rate limited, skip silently

        if now < self._next_session_retry_at:
            return

        # Check shared session cache first (avoid duplicate auth across instances)
        if (_SHARED_SESSION.get("demo_mode") == self.demo_mode
                and _SHARED_SESSION.get("cst")
                and _SHARED_SESSION.get("x_security_token")
                and (now - float(_SHARED_SESSION.get("session_start_time", 0.0) or 0.0)) < (50 * 60)):
            self.cst = _SHARED_SESSION.get("cst")
            self.x_security_token = _SHARED_SESSION.get("x_security_token")
            self.session_start_time = float(_SHARED_SESSION.get("session_start_time", 0.0) or 0.0)
            self.init_error = str(_SHARED_SESSION.get("init_error", "") or "")
            logger.debug("Capital.com session reused from shared cache.")
            return

        # Check if this instance already has a valid session
        if (self.cst and self.x_security_token and
            (now - self.session_start_time) < (50 * 60)):  # 50 min buffer
            logger.debug("Capital.com session still valid (within 50 min), skipping re-auth")
            return

        url = f"{self.base_url}/session"
        payload = {
            "identifier": self.identifier,
            "password": self.password
        }
        headers = {
            "X-CAP-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=CAPITAL_HTTP_TIMEOUT)
            if response.status_code == 200:
                self.cst = response.headers.get('CST')
                self.x_security_token = response.headers.get('X-SECURITY-TOKEN')
                self.session_start_time = time.time()
                self._next_session_retry_at = 0.0
                self.init_error = ""
                self._session_error_logged = False  # Reset on success
                # Update shared cache so other instances can reuse
                _SHARED_SESSION["cst"] = self.cst
                _SHARED_SESSION["x_security_token"] = self.x_security_token
                _SHARED_SESSION["session_start_time"] = self.session_start_time
                _SHARED_SESSION["demo_mode"] = self.demo_mode
                _SHARED_SESSION["init_error"] = self.init_error
                logger.info("Capital.com session established.")
            elif response.status_code == 429 or 'too-many.requests' in response.text.lower():
                # Rate limited - back off for 10 minutes (Capital.com has aggressive limits)
                self._rate_limit_until = time.time() + 600
                _SHARED_SESSION["rate_limit_until"] = self._rate_limit_until
                self.init_error = "rate_limited"
                if not self._session_error_logged:
                    logger.warning("Capital.com rate limited - backing off for 5 minutes")
                    self._session_error_logged = True
            else:
                self.init_error = f"http_{response.status_code}"
                if not self._session_error_logged:
                    logger.error(f"Failed to create Capital.com session: {response.text}")
                    self._session_error_logged = True
                if response.status_code in (400, 401, 403):
                    self.enabled = False
                else:
                    self._next_session_retry_at = time.time() + CAPITAL_SESSION_RETRY_BACKOFF_SECS
        except Exception as e:
            self.init_error = str(e)
            self._next_session_retry_at = time.time() + CAPITAL_SESSION_RETRY_BACKOFF_SECS
            if not self._session_error_logged:
                logger.error(f"Capital.com connection error: {e}")
                self._session_error_logged = True

    def _session_is_expired(self) -> bool:
        """Capital.com sessions can expire; refresh after 55 minutes or when tokens missing."""
        if not self.cst or not self.x_security_token:
            return True
        # Refresh after ~55 minutes proactively
        return (time.time() - self.session_start_time) > (55 * 60)

    def _ensure_economic_dispatch_store(self) -> None:
        """Lazily provide the private store for hermetic legacy constructions."""

        if not hasattr(self, "_economic_dispatch_lock"):
            self._economic_dispatch_lock = threading.RLock()
        if not hasattr(self, "_economic_dispatches"):
            self._economic_dispatches = {}

    def _register_economic_dispatch(
        self,
        *,
        method: str,
        path: str,
        body_digest: str,
    ) -> object:
        self._ensure_economic_dispatch_store()
        dispatch = object()
        with self._economic_dispatch_lock:
            self._economic_dispatches[dispatch] = (method, path, body_digest)
        return dispatch

    def _discard_economic_dispatch(self, dispatch: object | None) -> None:
        if dispatch is None:
            return
        self._ensure_economic_dispatch_store()
        with self._economic_dispatch_lock:
            self._economic_dispatches.pop(dispatch, None)

    def _consume_economic_dispatch(
        self,
        dispatch: object | None,
        *,
        method: str,
        path: str,
        body: Dict[str, Any],
    ) -> None:
        self._ensure_economic_dispatch_store()
        with self._economic_dispatch_lock:
            state = self._economic_dispatches.pop(dispatch, None)
        if state is None:
            raise EconomicGovernanceBlocked(
                "capital_mutation_dispatch_capability_required"
            )
        if not isinstance(body, dict):
            raise EconomicGovernanceBlocked("exact_capital_mutation_body_required")
        try:
            observed = (
                str(method).strip().upper(),
                path,
                _capital_economic_transport_body_digest(body),
            )
        except (TypeError, ValueError) as exc:
            raise EconomicGovernanceBlocked(
                "exact_capital_mutation_body_required"
            ) from exc
        if observed != state:
            raise EconomicGovernanceBlocked(
                "exact_capital_mutation_method_path_body_required"
            )

    def _capital_http_request(
        self,
        method: str,
        path: str,
        *,
        headers: Dict[str, str],
        params: Optional[Dict[str, Any]],
        json_body: Dict[str, Any],
        _economic_dispatch: object | None = None,
    ) -> requests.Response:
        """Final HTTP seam; economic dispatch is burned before requests sees it."""

        normalized_method = str(method).strip().upper()
        is_mutation = _is_capital_economic_mutation_path(normalized_method, path)
        if is_mutation:
            expected_base = CAPITAL_DEMO_BASE if self.demo_mode else CAPITAL_LIVE_BASE
            if self.base_url != expected_base:
                raise EconomicGovernanceBlocked(
                    "canonical_capital_environment_endpoint_required"
                )
            if self.dry_run:
                raise EconomicGovernanceBlocked(
                    "capital_dry_run_mutation_transport_forbidden"
                )
            self._consume_economic_dispatch(
                _economic_dispatch,
                method=normalized_method,
                path=path,
                body=json_body,
            )
        elif normalized_method != "GET" or _economic_dispatch is not None:
            raise EconomicGovernanceBlocked(
                "unsupported_or_misbound_capital_transport_operation"
            )
        return requests.request(
            normalized_method,
            f"{self.base_url}{path}",
            headers=headers,
            params=params,
            json=json_body or None,
            timeout=CAPITAL_HTTP_TIMEOUT,
        )

    def _request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Perform an API request with automatic session refresh and one retry on
        invalid session token or HTTP 401.
        """
        normalized_method = str(method).strip().upper()
        is_mutation = _is_capital_economic_mutation_path(normalized_method, path)
        if normalized_method != "GET" and not is_mutation:
            raise EconomicGovernanceBlocked(
                "canonical_capital_mutation_method_and_path_required"
            )
        if is_mutation and params:
            raise EconomicGovernanceBlocked(
                "capital_mutation_query_parameters_forbidden"
            )
        if json_body is not None and not isinstance(json_body, dict):
            raise EconomicGovernanceBlocked("exact_capital_mutation_body_required")
        economic_body = dict(json_body or {})
        dispatch = None
        if is_mutation:
            if self.dry_run:
                raise EconomicGovernanceBlocked(
                    "capital_dry_run_mutation_transport_forbidden"
                )
            expected_base = CAPITAL_DEMO_BASE if self.demo_mode else CAPITAL_LIVE_BASE
            if self.base_url != expected_base:
                raise EconomicGovernanceBlocked(
                    "canonical_capital_environment_endpoint_required"
                )
            if self.demo_mode:
                body_digest = _capital_economic_transport_body_digest(economic_body)
            else:
                body_digest = _claim_capital_economic_transport_context(
                    method=normalized_method,
                    path=path,
                    body=economic_body,
                )
            dispatch = self._register_economic_dispatch(
                method=normalized_method,
                path=path,
                body_digest=body_digest,
            )

        # Return error response if client is disabled (don't raise exception)
        if not self.enabled:
            self._discard_economic_dispatch(dispatch)
            class DisabledResponse:
                status_code = 503
                text = '{\"errorCode\":\"client.disabled\"}'
                def json(self):
                    return {"errorCode": "client.disabled"}
            return DisabledResponse()

        # Proactive refresh
        if self._session_is_expired():
            logger.debug("Capital.com session expired; refreshing")
            self._create_session()

        headers = self._get_headers()
        if not headers:
            self._discard_economic_dispatch(dispatch)
            return self._error_response(503, "session_unavailable", self.init_error or "session_unavailable")
        try:
            resp = self._capital_http_request(
                normalized_method,
                path,
                headers=headers,
                params=params,
                json_body=economic_body,
                _economic_dispatch=dispatch,
            )
        except Exception as e:
            self._discard_economic_dispatch(dispatch)
            if isinstance(e, EconomicGovernanceBlocked):
                raise
            logger.error(f"Capital.com request error ({method} {path}): {e}")
            return self._error_response(503, "request_error", str(e))

        # Rate limit handling
        rate_limit_hit = resp.status_code == 429 or ('too-many.requests' in (resp.text or '').lower())
        if rate_limit_hit:
            self._rate_limit_until = time.time() + 600
            if not self._rate_limit_logged:
                logger.warning("Capital.com rate limited - backing off for 5 minutes")
                self._rate_limit_logged = True
            return resp

        # Reset rate limit log flag on success
        if resp.status_code == 200 and self._rate_limit_logged:
            self._rate_limit_logged = False

        # A mutation has spent its only authority and is never retried. Rate
        # pressure is recorded above, while any negative or ambiguous outcome
        # must be reconciled before a separately governed permit is considered.
        if is_mutation:
            return resp

        # Handle invalid session
        if resp.status_code in (401, 403) or ('error.invalid.session.token' in (resp.text or '').lower()):
            logger.warning("Capital.com session invalid; attempting re-login and retry")
            # Clear stale tokens and re-enable so _create_session does a real POST
            self.cst = None
            self.x_security_token = None
            self.session_start_time = 0.0
            self.enabled = True
            self._session_error_logged = False
            self._create_session()
            headers = self._get_headers()
            if not headers:
                return self._error_response(503, "session_unavailable", self.init_error or "session_unavailable")
            try:
                resp = self._capital_http_request(
                    normalized_method,
                    path,
                    headers=headers,
                    params=params,
                    json_body=economic_body,
                )
            except Exception as e:
                logger.error(f"Capital.com retry request error ({method} {path}): {e}")
                return self._error_response(503, "request_error", str(e))
        return resp

    def _get_headers(self):
        """Get headers for authenticated requests."""
        if not self.enabled:
            return {}  # Don't try to create session when disabled

        if not self.cst or not self.x_security_token:
            self._create_session()

        # If session creation failed, return empty headers
        if not self.cst or not self.x_security_token:
            return {}

        return {
            "X-CAP-API-KEY": self.api_key,
            "CST": self.cst,
            "X-SECURITY-TOKEN": self.x_security_token,
            "Content-Type": "application/json"
        }

    @staticmethod
    def _canonicalize(value: Optional[str]) -> str:
        """Normalize symbols/epics for robust matching."""
        if not value:
            return ""
        return "".join(ch for ch in str(value).upper() if ch.isalnum())

    def _update_market_index(self, markets: List[Dict[str, Any]]):
        """Build fast lookup index for epic/instrument names."""
        index: Dict[str, Dict[str, Any]] = {}
        for m in markets:
            for key in (
                self._canonicalize(m.get('epic')),
                self._canonicalize(m.get('instrumentName')),
                self._canonicalize(m.get('symbol')),
                self._canonicalize(m.get('marketId')),
            ):
                if key and key not in index:
                    index[key] = m
        self.market_index = index

    def get_all_markets(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Discover all available Capital.com markets by traversing the market navigation tree.
        This ensures we can trade any listed epic instead of a small search subset.
        """
        if not self.enabled:
            return []

        global _SHARED_MARKET_CACHE

        # Return shared in-memory cache if still fresh.
        if (
            not force_refresh
            and _SHARED_MARKET_CACHE.get("markets")
            and (time.time() - float(_SHARED_MARKET_CACHE.get("market_cache_time", 0.0) or 0.0)) < self.market_cache_ttl
        ):
            self.market_cache = list(_SHARED_MARKET_CACHE["markets"])
            self.market_index = dict(_SHARED_MARKET_CACHE.get("market_index", {}))
            self.market_cache_time = float(_SHARED_MARKET_CACHE.get("market_cache_time", 0.0) or 0.0)
            return self.market_cache

        # Return instance in-memory cache if still fresh.
        if (
            not force_refresh
            and self.market_cache
            and (time.time() - self.market_cache_time) < self.market_cache_ttl
        ):
            return self.market_cache

        # Don't download while rate-limited.
        if time.time() < self._rate_limit_until:
            return self.market_cache or []

        # Try disk cache — avoids re-downloading 6799 markets on every process restart.
        if not force_refresh:
            try:
                disk_path = CAPITAL_MARKET_DISK_CACHE_PATH
                if os.path.exists(disk_path):
                    stat = os.stat(disk_path)
                    age = time.time() - stat.st_mtime
                    if age < self.market_cache_ttl:
                        with open(disk_path, "r", encoding="utf-8") as _f:
                            disk_data = json.load(_f)
                        markets = disk_data.get("markets", [])
                        if markets:
                            self.market_cache = markets
                            self.market_cache_time = time.time() - age
                            self._update_market_index(markets)
                            _SHARED_MARKET_CACHE["markets"] = list(markets)
                            _SHARED_MARKET_CACHE["market_index"] = dict(self.market_index)
                            _SHARED_MARKET_CACHE["market_cache_time"] = self.market_cache_time
                            logger.info(f"Capital.com market catalogue loaded from disk cache ({len(markets)} markets, age={age:.0f}s)")
                            return self.market_cache
            except Exception as _disk_err:
                logger.debug(f"Disk market cache load failed: {_disk_err}")

        markets: List[Dict[str, Any]] = []
        queue: List[Optional[str]] = [None]
        visited: set = set()
        bfs_started = time.time()
        max_bfs_sec = 30.0  # Hard cap on catalogue traversal time

        while queue and (time.time() - bfs_started) < max_bfs_sec:
            node_id = queue.pop(0)
            if node_id in visited:
                continue
            visited.add(node_id)
            path = '/marketnavigation' if not node_id else f'/marketnavigation/{node_id}'
            try:
                response = self._request('GET', path)
                if response.status_code != 200:
                    logger.warning(f"Capital.com marketnavigation failed for {node_id}: {response.text}")
                    continue

                data = response.json() or {}
                node_markets = data.get('markets', [])
                if node_markets:
                    markets.extend(node_markets)

                for node in data.get('nodes', []):
                    nid = node.get('id') or node.get('nodeId') or node.get('identifier') or node.get('name')
                    if not nid:
                        continue
                    if nid in visited:
                        continue
                    visited.add(nid)
                    queue.append(nid)
            except Exception as e:
                logger.error(f"Capital.com navigation error at node {node_id}: {e}")
                continue

        self.market_cache = markets
        self.market_cache_time = time.time()
        self._update_market_index(markets)
        logger.info(f"Capital.com market catalogue loaded ({len(markets)} markets)")

        # Persist to disk so the next process start can skip this BFS download.
        try:
            disk_path = CAPITAL_MARKET_DISK_CACHE_PATH
            os.makedirs(os.path.dirname(disk_path), exist_ok=True)
            with open(disk_path, "w", encoding="utf-8") as _f:
                json.dump({"markets": markets, "ts": self.market_cache_time}, _f)
        except Exception as _save_err:
            logger.debug(f"Disk market cache save failed: {_save_err}")

        return markets

    def _resolve_market(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Map a user-facing symbol (e.g., BTCUSD, TSLA) to the corresponding Capital.com market entry.
        Falls back to the search endpoint if the market isn't in cache yet.
        """
        if not symbol:
            return None

        canonical = self._canonicalize(symbol)
        markets = self.get_all_markets()
        if canonical in self.market_index:
            return self.market_index[canonical]

        # Partial match on epic or instrument name
        for m in markets:
            if canonical in self._canonicalize(m.get('epic')) or canonical in self._canonicalize(m.get('instrumentName')):
                return m

        # Fallback: use search endpoint to pull the market and refresh cache
        try:
            search_resp = self._request('GET', '/markets', params={'searchTerm': symbol, 'pageSize': 50})
            if search_resp.status_code == 200:
                data = search_resp.json() or {}
                found = data.get('markets', [])
                if found:
                    markets.extend(found)
                    self._update_market_index(markets)
                    self.market_cache = markets
                    self.market_cache_time = time.time()
                    return found[0]
        except Exception as e:
            logger.error(f"Capital.com search failed for {symbol}: {e}")

        return None

    def _get_market_snapshot(self, epic: str, *, cache_ttl: float = 30.0) -> Optional[Dict[str, Any]]:
        """Fetch detailed market info (including bid/ask) for a specific epic.
        Results cached for cache_ttl seconds (default 30s) to avoid duplicate HTTP calls.
        """
        if time.time() < self._rate_limit_until:
            return None  # Silently skip if globally rate limited

        now = time.time()
        cached_snap = self._snapshot_cache.get(epic)
        if cached_snap is not None and (now - self._snapshot_cache_times.get(epic, 0.0)) < cache_ttl:
            return cached_snap

        try:
            response = self._request('GET', f'/markets/{epic}')
            if response.status_code == 200:
                result = response.json()
                response_source_timestamp = _response_source_timestamp(response)
                if isinstance(result, dict) and response_source_timestamp is not None:
                    result = dict(result)
                    result["_provider_response_source_timestamp"] = response_source_timestamp
                self._snapshot_cache[epic] = result
                self._snapshot_cache_times[epic] = time.time()
                return result
            if response.status_code == 429 or 'too-many.requests' in (response.text or '').lower():
                return cached_snap  # Return stale on rate limit
            logger.error(f"Capital.com market snapshot failed for {epic}: {response.text}")
        except Exception as e:
            logger.error(f"Capital.com market snapshot error for {epic}: {e}")
        return cached_snap  # Return stale on error

    def _read_monitor_cache(self) -> Dict[str, Any]:
        path = CAPITAL_MONITOR_CACHE_PATH
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return {}
        generated_at = _fresh_provider_timestamp(
            payload.get("generated_at"),
            CAPITAL_MONITOR_CACHE_MAX_AGE_S,
        )
        if generated_at is None:
            return {}
        return payload

    @staticmethod
    def _no_data_ticker(
        symbol: str,
        reason: str,
        *,
        epic: Optional[str] = None,
        truth_status: str = "no_data",
        source_timestamp: Optional[float] = None,
        received_at: Optional[float] = None,
    ) -> Dict[str, Any]:
        return {
            "symbol": str(symbol or "").upper(),
            "epic": str(epic or ""),
            "price": None,
            "bid": None,
            "ask": None,
            "change_pct": None,
            "high": None,
            "low": None,
            "truth_status": truth_status,
            "reason": reason,
            "source_id": None,
            "source_timestamp": source_timestamp,
            "received_at": time.time() if received_at is None else received_at,
            "generated_values": False,
            "action_eligible": False,
            "eligible_for_learning": False,
        }

    @staticmethod
    def _ticker_is_actionable(ticker: Any) -> bool:
        if not isinstance(ticker, dict):
            return False
        source_timestamp = _fresh_provider_timestamp(
            ticker.get("source_timestamp"),
            CAPITAL_QUOTE_MAX_AGE_S,
        )
        return bool(
            ticker.get("truth_status") in {"real_observed", "real_derived"}
            and ticker.get("generated_values") is False
            and ticker.get("action_eligible") is True
            and source_timestamp is not None
            and _finite_number(ticker.get("price"), positive=True) is not None
            and _finite_number(ticker.get("bid"), positive=True) is not None
            and _finite_number(ticker.get("ask"), positive=True) is not None
            and _finite_number(ticker.get("change_pct")) is not None
        )

    def _get_cached_monitor_quote(self, symbol: str) -> Dict[str, Any]:
        received_at = time.time()
        payload = self._read_monitor_cache()
        if not payload:
            return self._no_data_ticker(symbol, "monitor_cache_missing_or_stale", received_at=received_at)
        prices = payload.get("prices", {}) if isinstance(payload.get("prices"), dict) else {}
        quote = prices.get(str(symbol or "").upper(), {})
        if not isinstance(quote, dict):
            return self._no_data_ticker(symbol, "monitor_quote_missing", received_at=received_at)
        cache_received_at = _provider_timestamp(payload.get("generated_at"))
        source_timestamp = _fresh_provider_timestamp(
            quote.get("source_timestamp"),
            CAPITAL_MONITOR_CACHE_MAX_AGE_S,
            received_at=received_at,
        )
        price = _finite_number(quote.get("price"), positive=True)
        bid = _finite_number(quote.get("bid"), positive=True)
        ask = _finite_number(quote.get("ask"), positive=True)
        change_pct = _finite_number(quote.get("change_pct"))
        source = str(quote.get("source") or "").strip().lower()
        if (
            cache_received_at is None
            or source_timestamp is None
            or price is None
            or bid is None
            or ask is None
            or ask < bid
            or change_pct is None
            or not source
        ):
            return self._no_data_ticker(
                symbol,
                "monitor_quote_incomplete_or_unproven",
                epic=str(quote.get("epic") or ""),
                source_timestamp=_provider_timestamp(quote.get("source_timestamp")),
                received_at=received_at,
            )
        return {
            "symbol": str(symbol or "").upper(),
            "price": price,
            "bid": bid,
            "ask": ask,
            "epic": str(quote.get("epic") or ""),
            "change_pct": change_pct,
            "high": _finite_number(quote.get("high"), positive=True),
            "low": _finite_number(quote.get("low"), positive=True),
            "truth_status": "real_observed",
            "reason": "fresh_provider_monitor_quote",
            "source_id": f"{source}_quote:{str(symbol or '').upper()}",
            "source_timestamp": source_timestamp,
            "received_at": cache_received_at,
            "generated_values": False,
            "action_eligible": True,
            "eligible_for_learning": True,
            "field_provenance": {
                "price": {"source": f"{source}.price", "source_timestamp": source_timestamp},
                "bid": {"source": f"{source}.bid", "source_timestamp": source_timestamp},
                "ask": {"source": f"{source}.ask", "source_timestamp": source_timestamp},
                "change_pct": {"source": f"{source}.change_pct", "source_timestamp": source_timestamp},
            },
        }

    @staticmethod
    def _no_data_accounts(reason: str, *, received_at: Optional[float] = None) -> ObservationList:
        return ObservationList(
            truth_status="no_data",
            reason=reason,
            source_timestamp=None,
            received_at=time.time() if received_at is None else received_at,
        )

    def _normalize_accounts_response(
        self,
        data: Any,
        *,
        source_timestamp: Optional[float],
        received_at: float,
    ) -> ObservationList:
        fresh_source_timestamp = _fresh_provider_timestamp(
            source_timestamp,
            CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S,
            received_at=received_at,
        )
        if fresh_source_timestamp is None or not isinstance(data, dict):
            return self._no_data_accounts("account_receipt_missing_provider_time", received_at=received_at)
        raw_accounts = data.get("accounts")
        if not isinstance(raw_accounts, list):
            return self._no_data_accounts("accounts_payload_missing", received_at=received_at)

        accounts: List[Dict[str, Any]] = []
        incomplete_rows = 0
        for raw in raw_accounts:
            if not isinstance(raw, dict):
                incomplete_rows += 1
                continue
            balance_data = raw.get("balance")
            account_id = str(raw.get("accountId") or "").strip()
            currency = str(raw.get("currency") or "").strip().upper()
            status = str(raw.get("status") or "").strip().upper()
            balance = _finite_number(
                balance_data.get("balance") if isinstance(balance_data, dict) else None,
                nonnegative=True,
            )
            available = _finite_number(
                balance_data.get("available") if isinstance(balance_data, dict) else None,
                nonnegative=True,
            )
            if not account_id or not currency or not status or balance is None or available is None:
                incomplete_rows += 1
                continue
            accounts.append({
                "accountId": account_id,
                "accountName": str(raw.get("accountName") or ""),
                "status": status,
                "accountType": str(raw.get("accountType") or ""),
                "preferred": raw.get("preferred") is True,
                "balance": balance,
                "available": available,
                "currency": currency,
                "truth_status": "real_observed",
                "reason": "fresh_provider_account_receipt",
                "source_id": f"capital_account:{account_id}",
                "source_timestamp": fresh_source_timestamp,
                "received_at": received_at,
                "generated_values": False,
                "action_eligible": status == "ENABLED",
                "eligible_for_learning": False,
                "field_provenance": {
                    "balance": {"source": "capital.accounts.balance.balance", "source_timestamp": fresh_source_timestamp},
                    "available": {"source": "capital.accounts.balance.available", "source_timestamp": fresh_source_timestamp},
                    "currency": {"source": "capital.accounts.currency", "source_timestamp": fresh_source_timestamp},
                },
            })
        if not accounts:
            reason = "accounts_empty" if not raw_accounts else "accounts_incomplete"
            return self._no_data_accounts(reason, received_at=received_at)
        return ObservationList(
            accounts,
            truth_status="incomplete" if incomplete_rows else "real_observed",
            reason="some_account_rows_incomplete" if incomplete_rows else "fresh_provider_account_receipt",
            source_timestamp=fresh_source_timestamp,
            received_at=received_at,
        )

    def get_account_balance(self) -> BalanceObservation:
        """Return provider-reported currency balances without currency substitution."""
        accounts = self.get_accounts(cache_ttl=0.0)
        received_at = time.time()
        if not accounts:
            observation = BalanceObservation(
                truth_status=getattr(accounts, "truth_status", "no_data"),
                reason=getattr(accounts, "reason", "accounts_unavailable"),
                source_timestamp=getattr(accounts, "source_timestamp", None),
                received_at=getattr(accounts, "received_at", received_at),
            )
            self.last_account_observation = observation
            return observation
        balances: Dict[str, float] = {}
        source_ids: List[str] = []
        timestamps: List[float] = []
        for account in accounts:
            if account.get("truth_status") != "real_observed" or account.get("generated_values") is not False:
                continue
            if account.get("action_eligible") is not True:
                continue
            currency = str(account.get("currency") or "").strip().upper()
            amount = _finite_number(account.get("balance"), nonnegative=True)
            source_timestamp = _fresh_provider_timestamp(
                account.get("source_timestamp"),
                CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S,
                received_at=received_at,
            )
            if not currency or amount is None or source_timestamp is None:
                continue
            balances[currency] = balances.get(currency, 0.0) + amount
            timestamps.append(source_timestamp)
            source_ids.append(str(account.get("source_id")))
        if not balances:
            observation = BalanceObservation(
                truth_status="no_data",
                reason="no_complete_enabled_account_balances",
                received_at=received_at,
            )
        else:
            observation = BalanceObservation(
                balances,
                truth_status="real_derived",
                reason="sum_of_fresh_provider_account_balances",
                source_timestamp=min(timestamps),
                received_at=received_at,
                source_ids=source_ids,
            )
        self.last_account_observation = observation
        return observation

    def get_accounts(self, *, cache_ttl: float = 60.0) -> ObservationList:
        """Get account information including available balance.
        Returns list of accounts with structure: [{'accountId': str, 'available': float, 'balance': float}]
        Results are cached for cache_ttl seconds (default 60s) to avoid serial HTTP calls during preflight.
        """
        if not self.enabled:
            return self._no_data_accounts("client_disabled")

        now = time.time()
        cached_source_timestamp = _fresh_provider_timestamp(
            getattr(self._accounts_cache, "source_timestamp", None),
            CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S,
            received_at=now,
        )
        if (
            self._accounts_cache
            and (now - self._accounts_cache_time) < cache_ttl
            and cached_source_timestamp is not None
        ):
            return self._accounts_cache

        try:
            response = self._request('GET', '/accounts')
            if response.status_code == 200:
                received_at = time.time()
                accounts = self._normalize_accounts_response(
                    response.json(),
                    source_timestamp=_response_source_timestamp(response),
                    received_at=received_at,
                )
                if accounts:
                    self._accounts_cache = accounts
                    self._accounts_cache_time = received_at
                return accounts
            logger.error(f"Failed to get Capital.com accounts: {response.text}")
            return self._no_data_accounts(f"accounts_http_{response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching Capital.com accounts: {e}")
            return self._no_data_accounts("accounts_request_failed")

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get a complete, fresh quote with provider and receipt timestamps."""
        received_at = time.time()
        if not self.enabled:
            cached = self._get_cached_monitor_quote(symbol)
            if self._ticker_is_actionable(cached):
                self.last_ticker_observation = cached
                return cached
            result = self._no_data_ticker(symbol, "client_disabled_and_no_proven_monitor_quote", received_at=received_at)
            self.last_ticker_observation = result
            return result

        crypto_patterns = (
            "USDT", "USDC", "BTC", "ETH", "XBT", "SOL", "ADA", "XRP",
            "DOGE", "SHIB", "AVAX", "DOT", "LINK", "MATIC", "UNI",
        )
        if any(pattern in symbol.upper() for pattern in crypto_patterns):
            result = self._no_data_ticker(
                symbol,
                "unsupported_crypto_market",
                received_at=received_at,
            )
            self.last_ticker_observation = result
            return result
        cached = self._get_cached_monitor_quote(symbol)
        if self._ticker_is_actionable(cached):
            self.last_ticker_observation = cached
            return cached
        try:
            market = self._resolve_market(symbol) or {}
            epic = market.get("epic") or symbol
            snapshot = self._get_market_snapshot(epic) or {}
            snap = snapshot.get("snapshot")
            if not isinstance(snap, dict):
                result = self._no_data_ticker(
                    symbol,
                    "market_snapshot_missing",
                    epic=str(epic),
                    received_at=received_at,
                )
                self.last_ticker_observation = result
                return result
            received_at = time.time()
            bid = _finite_number(snap.get("bid"), positive=True)
            ask = _finite_number(snap.get("offer"), positive=True)
            change_pct = _finite_number(snap.get("percentageChange"))
            raw_source_timestamp = snap.get("updateTimeUTC") or snapshot.get(
                "_provider_response_source_timestamp"
            )
            source_timestamp = _fresh_provider_timestamp(
                raw_source_timestamp,
                CAPITAL_QUOTE_MAX_AGE_S,
                received_at=received_at,
            )
            if bid is None or ask is None or ask < bid or change_pct is None or source_timestamp is None:
                result = self._no_data_ticker(
                    symbol,
                    "market_snapshot_incomplete_or_stale",
                    epic=str(epic),
                    source_timestamp=_provider_timestamp(raw_source_timestamp),
                    received_at=received_at,
                )
                self.last_ticker_observation = result
                return result
            price = (bid + ask) / 2.0
            market_status = str(snap.get("marketStatus") or "").strip().upper()
            action_eligible = market_status == "TRADEABLE"
            result = {
                "symbol": str(symbol or "").upper(),
                "price": price,
                "bid": bid,
                "ask": ask,
                "epic": epic,
                "change_pct": change_pct,
                "high": _finite_number(snap.get("high") or snap.get("dayHigh"), positive=True),
                "low": _finite_number(snap.get("low") or snap.get("dayLow"), positive=True),
                "market_status": market_status,
                "truth_status": "real_derived" if action_eligible else "incomplete",
                "reason": "fresh_provider_quote" if action_eligible else "market_not_tradeable",
                "source_id": f"capital_market:{epic}",
                "source_timestamp": source_timestamp,
                "received_at": received_at,
                "generated_values": False,
                "action_eligible": action_eligible,
                "eligible_for_learning": action_eligible,
                "field_provenance": {
                    "bid": {"source": "capital.snapshot.bid", "source_timestamp": source_timestamp},
                    "ask": {"source": "capital.snapshot.offer", "source_timestamp": source_timestamp},
                    "price": {
                        "source": "midpoint(capital.snapshot.bid,capital.snapshot.offer)",
                        "source_timestamp": source_timestamp,
                    },
                    "change_pct": {
                        "source": "capital.snapshot.percentageChange",
                        "source_timestamp": source_timestamp,
                    },
                },
            }
            self.last_ticker_observation = result
            return result
        except Exception as exc:
            logger.error(
                "Error fetching Capital.com ticker for %s: %s",
                symbol,
                type(exc).__name__,
            )
            result = self._no_data_ticker(
                symbol,
                "market_snapshot_request_failed",
                received_at=received_at,
            )
            self.last_ticker_observation = result
            return result

    def get_price_history(
        self,
        epic: str,
        *,
        resolution: str = "MINUTE",
        max_points: int = 100,
    ) -> ObservationList:
        """Return strict provider-observed bid/ask bars for evidence calibration."""
        received_at = time.time()
        canonical_epic = str(epic or "").strip()
        canonical_resolution = str(resolution or "").strip().upper()
        if (
            not self.enabled
            or not canonical_epic
            or canonical_resolution != "MINUTE"
            or isinstance(max_points, bool)
            or not isinstance(max_points, int)
            or not 16 <= max_points <= 1_000
        ):
            return ObservationList(
                truth_status="no_data",
                reason="invalid_or_disabled_price_history_request",
                received_at=received_at,
            )
        try:
            response = self._request(
                "GET",
                f"/prices/{canonical_epic}",
                params={"resolution": canonical_resolution, "max": max_points},
            )
            if response.status_code != 200:
                return ObservationList(
                    truth_status="no_data",
                    reason=f"price_history_http_{response.status_code}",
                    received_at=time.time(),
                )
            received_at = time.time()
            data = response.json()
            raw_prices = data.get("prices") if isinstance(data, dict) else None
            response_timestamp = _fresh_provider_timestamp(
                _response_source_timestamp(response),
                CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S,
                received_at=received_at,
            )
            if response_timestamp is None or not isinstance(raw_prices, list):
                return ObservationList(
                    truth_status="no_data",
                    reason="price_history_receipt_incomplete",
                    received_at=received_at,
                )
            bars: List[Dict[str, Any]] = []
            for raw in raw_prices:
                if not isinstance(raw, dict):
                    continue
                timestamp = _provider_timestamp(
                    raw.get("snapshotTimeUTC") or raw.get("snapshotTime")
                )
                prices = {
                    name: raw.get(provider_name)
                    for name, provider_name in (
                        ("open", "openPrice"),
                        ("high", "highPrice"),
                        ("low", "lowPrice"),
                        ("close", "closePrice"),
                    )
                }
                if timestamp is None or any(not isinstance(value, dict) for value in prices.values()):
                    continue
                bar: Dict[str, Any] = {"timestamp": timestamp}
                valid = True
                for name, value in prices.items():
                    bid = _finite_number(value.get("bid"), positive=True)
                    ask = _finite_number(value.get("ask"), positive=True)
                    if bid is None or ask is None or ask < bid:
                        valid = False
                        break
                    bar[f"{name}_bid"] = bid
                    bar[f"{name}_ask"] = ask
                volume = _finite_number(raw.get("lastTradedVolume"), nonnegative=True)
                if valid and volume is not None:
                    bar["volume"] = volume
                    bars.append(bar)
            bars.sort(key=lambda item: item["timestamp"])
            if len(bars) < 16 or any(
                bars[index]["timestamp"] <= bars[index - 1]["timestamp"]
                for index in range(1, len(bars))
            ):
                return ObservationList(
                    truth_status="no_data",
                    reason="insufficient_complete_price_history",
                    received_at=received_at,
                )
            return ObservationList(
                bars,
                truth_status="real_observed",
                reason="fresh_provider_price_history",
                source_timestamp=response_timestamp,
                received_at=received_at,
            )
        except Exception as exc:
            logger.error("Capital.com price history error: %s", type(exc).__name__)
            return ObservationList(
                truth_status="no_data",
                reason="price_history_request_failed",
                received_at=time.time(),
            )

        # 🔥 Skip crypto symbols - Capital.com doesn't have them
    def get_tickers_for_symbols(self, symbols: List[str], *, max_workers: int = CAPITAL_TICKER_WORKERS) -> Dict[str, Dict[str, Any]]:
        """Fetch tickers for many symbols concurrently (best-effort).

        Returns: {symbol: {price,bid,ask,epic,change_pct}}
        """
        if not self.enabled:
            return {str(symbol).upper(): self.get_ticker(str(symbol)) for symbol in symbols if symbol}
        if not symbols:
            return {}

        # Deduplicate while preserving a stable order
        seen = set()
        unique_symbols: List[str] = []
        for s in symbols:
            if not s:
                continue
            su = str(s).strip().upper()
            if not su or su in seen:
                continue
            seen.add(su)
            unique_symbols.append(su)

        results: Dict[str, Dict[str, Any]] = {}
        uncached_symbols: List[str] = []
        now = time.time()
        for sym in unique_symbols:
            # 1. Check disk-based monitor cache (written by background monitor process)
            cached = self._get_cached_monitor_quote(sym)
            if self._ticker_is_actionable(cached):
                results[sym] = cached
                continue
            # 2. Check in-memory per-symbol cache (populated by previous batch fetches)
            mem_age = now - self._ticker_mem_cache_times.get(sym, 0.0)
            if mem_age < CAPITAL_TICKER_MEM_TTL:
                mem_hit = self._ticker_mem_cache.get(sym, {})
                if self._ticker_is_actionable(mem_hit):
                    results[sym] = mem_hit
                    continue
            uncached_symbols.append(sym)

        if not uncached_symbols:
            return results
        max_workers = max(1, int(max_workers))

        # Pre-warm market catalogue once serially — prevents N concurrent
        # get_all_markets() calls each downloading 6799 markets → 429 ban.
        self.get_all_markets()

        def _fetch(sym: str) -> Dict[str, Any]:
            return self.get_ticker(sym)

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            future_map = {ex.submit(_fetch, sym): sym for sym in uncached_symbols}
            for fut in as_completed(future_map):
                sym = future_map[fut]
                try:
                    result = fut.result()
                except Exception:
                    result = self._no_data_ticker(sym, "ticker_worker_failed")
                if not isinstance(result, dict):
                    result = self._no_data_ticker(sym, "ticker_worker_returned_no_observation")
                results[sym] = result
                # Populate in-memory cache for subsequent ticks
                if self._ticker_is_actionable(result):
                    self._ticker_mem_cache[sym] = result
                    self._ticker_mem_cache_times[sym] = time.time()

        return results

    def get_24h_tickers(self) -> ObservationList:
        """
        Get top markets or a watchlist.
        Capital.com doesn't have a simple 'all tickers' endpoint that is lightweight.
        We'll fetch a top list or specific categories if possible.
        For now, let's fetch top crypto and tech stocks if we can, or just return empty if too complex.
        Actually, let's try to fetch 'crypto' category.
        """
        if not self.enabled:
            return ObservationList(truth_status="no_data", reason="client_disabled", received_at=time.time())

        max_snapshots = int(os.getenv('CAPITAL_MAX_TICKER_SNAPSHOTS', '400'))
        tickers: List[Dict[str, Any]] = []
        markets = self.get_all_markets()

        try:
            for m in markets[:max_snapshots]:
                epic = m.get('epic')
                if not epic:
                    continue
                quote = self.get_ticker(str(epic))
                if not self._ticker_is_actionable(quote):
                    continue
                tickers.append({
                    'symbol': epic,
                    'epic': epic,
                    'ticker': m.get('symbol') or '',
                    'instrumentName': m.get('instrumentName'),
                    'price': quote.get('price'),
                    'bid': quote.get('bid'),
                    'ask': quote.get('ask'),
                    'priceChangePercent': quote.get('change_pct'),
                    'volume': None,
                    'source': 'capital',
                    'truth_status': quote.get('truth_status'),
                    'source_id': quote.get('source_id'),
                    'source_timestamp': quote.get('source_timestamp'),
                    'received_at': quote.get('received_at'),
                    'generated_values': False,
                    'action_eligible': True,
                })
        except Exception as e:
            logger.error(f"Error fetching Capital.com tickers: {e}")

        timestamps = [
            float(t["source_timestamp"])
            for t in tickers
            if _provider_timestamp(t.get("source_timestamp")) is not None
        ]
        return ObservationList(
            tickers,
            truth_status="real_observed" if tickers else "no_data",
            reason="fresh_provider_quotes" if tickers else "no_complete_fresh_quotes",
            source_timestamp=min(timestamps) if timestamps else None,
            received_at=time.time(),
        )

    def get_stock_snapshot_watchlist(self, symbols: List[str], *, max_workers: int = 8) -> ObservationList:
        """Convenience: returns a ticker-like list for a list of stock symbols."""
        tmap = self.get_tickers_for_symbols(symbols, max_workers=max_workers)
        out: List[Dict[str, Any]] = []
        for sym, t in tmap.items():
            out.append({
                'symbol': t.get('epic', sym),
                'epic': t.get('epic', sym),
                'ticker': sym,
                'instrumentName': '',
                'price': _finite_number(t.get('price'), positive=True),
                'bid': _finite_number(t.get('bid'), positive=True),
                'ask': _finite_number(t.get('ask'), positive=True),
                'priceChangePercent': _finite_number(t.get('change_pct')),
                'volume': None,
                'source': 'capital',
                'truth_status': t.get('truth_status', 'no_data'),
                'reason': t.get('reason'),
                'source_id': t.get('source_id'),
                'source_timestamp': t.get('source_timestamp'),
                'received_at': t.get('received_at'),
                'generated_values': False,
                'action_eligible': t.get('action_eligible') is True,
            })
        timestamps = [
            float(t["source_timestamp"])
            for t in out
            if _provider_timestamp(t.get("source_timestamp")) is not None
        ]
        return ObservationList(
            out,
            truth_status="real_observed" if any(t.get("action_eligible") for t in out) else "no_data",
            reason="watchlist_observations" if out else "watchlist_empty",
            source_timestamp=min(timestamps) if timestamps else None,
            received_at=time.time(),
        )

    @staticmethod
    def _add_optional_order_controls(payload: Dict[str, Any], **controls: Any) -> None:
        """Attach validated order controls; supplied malformed risk controls abort."""
        mapping = {
            "profit_level": "profitLevel",
            "profit_distance": "profitDistance",
            "profit_amount": "profitAmount",
            "stop_level": "stopLevel",
            "stop_distance": "stopDistance",
            "stop_amount": "stopAmount",
            "trailing_stop": "trailingStop",
            "good_till_date": "goodTillDate",
        }
        for source, target in mapping.items():
            value = controls.get(source)
            if value is None or value == "":
                continue
            if source == "trailing_stop":
                if not isinstance(value, bool):
                    raise ValueError("trailing_stop_must_be_boolean")
                payload[target] = value
                continue
            if source == "good_till_date":
                if _provider_timestamp(value) is None:
                    raise ValueError("good_till_date_invalid")
                payload[target] = str(value)
                continue
            number = _finite_number(value, positive=True)
            if number is None:
                raise ValueError(f"{source}_must_be_finite_positive")
            payload[target] = number

    @staticmethod
    def _no_action_receipt(
        purpose: str,
        reason: str,
        *,
        status: str = "not_submitted",
        received_at: Optional[float] = None,
        **context: Any,
    ) -> Dict[str, Any]:
        receipt = {
            "purpose": purpose,
            "status": status,
            "reason": reason,
            "error": reason,
            "rejected": True,
            "decision_status": "denied",
            "truth_status": "no_data",
            "source_id": None,
            "source_timestamp": None,
            "received_at": time.time() if received_at is None else received_at,
            "generated_values": False,
            "submission_acknowledged": False,
            "terminal_fill": False,
            "terminal_fill_receipt_complete": False,
            "eligible_for_state": False,
            "eligible_for_pnl": False,
            "eligible_for_learning": False,
        }
        receipt.update(context)
        return receipt

    def _submission_receipt(
        self,
        response: Any,
        *,
        purpose: str,
        submitted_payload: Dict[str, Any],
        expected_deal_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        received_at = time.time()
        try:
            data = response.json()
        except Exception:
            data = None
        if not isinstance(data, dict):
            return self._no_action_receipt(
                purpose,
                "provider_submission_payload_missing",
                status="incomplete",
                received_at=received_at,
            )
        deal_reference = str(data.get("dealReference") or "").strip()
        source_timestamp = _fresh_provider_timestamp(
            _response_source_timestamp(response),
            CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S,
            received_at=received_at,
        )
        if not deal_reference:
            return self._no_action_receipt(
                purpose,
                "provider_deal_reference_missing",
                status="incomplete",
                received_at=received_at,
                provider_response=data,
            )
        truth_status = "real_observed" if source_timestamp is not None else "incomplete"
        receipt = {
            "purpose": purpose,
            "status": "submitted",
            "reason": "terminal_provider_confirmation_required",
            "truth_status": truth_status,
            "dealReference": deal_reference,
            "provider_order_id": deal_reference,
            "requested_deal_id": expected_deal_id,
            "source_id": f"capital_submission:{deal_reference}",
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "generated_values": False,
            "submission_acknowledged": True,
            "terminal_fill": False,
            "terminal_fill_receipt_complete": False,
            "eligible_for_state": False,
            "eligible_for_pnl": False,
            "eligible_for_learning": False,
            "submitted_payload": dict(submitted_payload),
            "provider_response": data,
        }
        if purpose == "close_position" and expected_deal_id:
            pending = getattr(self, "_pending_close_confirmations", None)
            if not isinstance(pending, dict):
                pending = {}
                self._pending_close_confirmations = pending
            pending[deal_reference] = {
                "requested_deal_id": expected_deal_id,
                "received_at": received_at,
                "source_timestamp": source_timestamp,
            }
        return receipt

    @staticmethod
    def _normalize_fee_receipt(fee_receipt: Any, *, received_at: float) -> Optional[Dict[str, Any]]:
        if not isinstance(fee_receipt, dict):
            return None
        if fee_receipt.get("truth_status") != "real_observed" or fee_receipt.get("generated_values") is not False:
            return None
        amount = _finite_number(fee_receipt.get("amount"), nonnegative=True)
        currency = str(fee_receipt.get("currency") or "").strip().upper()
        source_id = str(fee_receipt.get("source_id") or "").strip()
        source_timestamp = _provider_timestamp(fee_receipt.get("source_timestamp"))
        if (
            amount is None
            or not currency
            or not source_id
            or source_timestamp is None
            or source_timestamp > received_at + CAPITAL_FUTURE_SKEW_S
        ):
            return None
        return {
            "amount": amount,
            "currency": currency,
            "source_id": source_id,
            "source_timestamp": source_timestamp,
            "received_at": received_at,
            "truth_status": "real_observed",
            "generated_values": False,
        }

    def normalize_order_confirmation(
        self,
        data: Any,
        *,
        received_at: Optional[float] = None,
        fee_receipt: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Normalize a confirmation without treating ACCEPTED alone as a fill."""
        receipt_time = time.time() if received_at is None else received_at
        if not isinstance(data, dict):
            return self._no_action_receipt(
                "order_confirmation",
                "provider_confirmation_missing",
                status="incomplete",
                received_at=receipt_time,
            )

        deal_reference = str(data.get("dealReference") or "").strip()
        top_deal_id = str(data.get("dealId") or "").strip()
        deal_status = str(data.get("dealStatus") or "").strip().upper()
        position_status = str(data.get("status") or "").strip().upper()
        epic = str(data.get("epic") or "").strip().upper()
        direction = str(data.get("direction") or "").strip().upper()
        filled_qty = _finite_number(data.get("size"), positive=True)
        filled_price = _finite_number(data.get("level"), positive=True)
        source_timestamp = _provider_timestamp(data.get("dateUTC") or data.get("date"))
        affected = data.get("affectedDeals")
        affected_rows = affected if isinstance(affected, list) else []
        terminal_rows: List[Dict[str, str]] = []
        for row in affected_rows:
            if not isinstance(row, dict):
                continue
            row_id = str(row.get("dealId") or "").strip()
            row_status = str(row.get("status") or "").strip().upper()
            if row_id and row_status in {"OPENED", "CLOSED"}:
                terminal_rows.append({"dealId": row_id, "status": row_status})

        source_id = f"capital_confirmation:{deal_reference}" if deal_reference else None
        base = {
            "purpose": "order_confirmation",
            "dealReference": deal_reference or None,
            "provider_order_id": deal_reference or None,
            "provider_deal_id": terminal_rows[0]["dealId"] if len(terminal_rows) == 1 else (top_deal_id or None),
            "provider_deal_status": deal_status or None,
            "provider_position_status": position_status or None,
            "epic": epic or None,
            "side": direction or None,
            "filled_qty": filled_qty,
            "filled_avg_price": filled_price,
            "affected_deals": terminal_rows,
            "source_id": source_id,
            "source_timestamp": source_timestamp,
            "received_at": receipt_time,
            "generated_values": False,
            "submission_acknowledged": bool(deal_reference),
            "eligible_for_state": False,
            "eligible_for_pnl": False,
            "eligible_for_learning": False,
            "provider_response": data,
        }

        if deal_status == "REJECTED":
            return {
                **base,
                "status": "rejected",
                "reason": str(
                    data.get("rejectReason")
                    or data.get("reason")
                    or "provider_rejected"
                ),
                "truth_status": "real_observed" if deal_reference and source_timestamp is not None else "incomplete",
                "terminal_fill": False,
                "terminal_fill_receipt_complete": False,
            }

        core_fill_complete = bool(
            deal_status == "ACCEPTED"
            and len(terminal_rows) == 1
            and deal_reference
            and source_timestamp is not None
            and source_timestamp <= receipt_time + CAPITAL_FUTURE_SKEW_S
            and epic
            and direction in {"BUY", "SELL"}
            and filled_qty is not None
            and filled_price is not None
        )
        if not core_fill_complete:
            return {
                **base,
                "status": "pending" if deal_reference else "incomplete",
                "reason": "terminal_provider_fill_receipt_pending_or_incomplete",
                "truth_status": "real_observed" if deal_reference and source_timestamp is not None else "incomplete",
                "terminal_fill": False,
                "terminal_fill_receipt_complete": False,
            }

        normalized_fee = self._normalize_fee_receipt(
            fee_receipt if fee_receipt is not None else data.get("provider_fee_receipt"),
            received_at=receipt_time,
        )
        if normalized_fee is None:
            return {
                **base,
                "status": "filled_unsettled",
                "reason": "provider_fee_receipt_required_for_state_pnl_and_learning",
                "truth_status": "incomplete",
                "terminal_fill": True,
                "terminal_fill_receipt_complete": False,
                "fee_receipt": None,
            }
        return {
            **base,
            "status": "filled",
            "reason": "complete_terminal_provider_fill_receipt",
            "truth_status": "real_observed",
            "terminal_fill": True,
            "terminal_fill_receipt_complete": True,
            "fee_amount": normalized_fee["amount"],
            "fee_currency": normalized_fee["currency"],
            "fee_receipt": normalized_fee,
            "eligible_for_state": True,
            "eligible_for_pnl": True,
            "eligible_for_learning": True,
        }

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        *,
        profit_level: Optional[float] = None,
        profit_distance: Optional[float] = None,
        profit_amount: Optional[float] = None,
        stop_level: Optional[float] = None,
        stop_distance: Optional[float] = None,
        stop_amount: Optional[float] = None,
        trailing_stop: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Submit a market order; a submission acknowledgement is never a fill."""
        if not self.enabled:
            return self._no_action_receipt("open_position", "client_disabled")

        pending_closes = getattr(self, "_pending_close_confirmations", {})
        if isinstance(pending_closes, dict) and pending_closes:
            active_pending = {
                reference: item
                for reference, item in pending_closes.items()
                if isinstance(item, dict)
                and _finite_number(item.get("received_at"), positive=True) is not None
                and str(item.get("requested_deal_id") or "").strip()
            }
            self._pending_close_confirmations = active_pending
            if active_pending:
                return self._no_action_receipt(
                    "open_position",
                    "close_confirmation_pending",
                    status="rejected",
                    pending_close_references=sorted(active_pending),
                )

        # 🔥 CRYPTO GUARD: Capital.com does NOT support direct crypto trading!
        # Only CFDs (forex, indices, commodities, stocks) are supported
        CRYPTO_PATTERNS = ('USDT', 'USDC', 'BTC', 'ETH', 'XBT', 'SOL', 'ADA', 'XRP',
                           'DOGE', 'SHIB', 'AVAX', 'DOT', 'LINK', 'MATIC', 'UNI',
                           'ATOM', 'LTC', 'BCH', 'ETC', 'XLM', 'ALGO', 'FIL', 'VET')
        symbol_upper = symbol.upper()
        if any(pattern in symbol_upper for pattern in CRYPTO_PATTERNS):
            logger.warning(f"Capital.com BLOCKED crypto order for {symbol} - use Binance/Kraken instead")
            return self._no_action_receipt(
                "open_position",
                "crypto_not_supported",
                status="rejected",
                symbol=symbol_upper,
            )

        direction = str(side or "").strip().upper()
        requested_quantity = _finite_number(quantity, positive=True)
        if direction not in {"BUY", "SELL"} or requested_quantity is None:
            return self._no_action_receipt(
                "open_position",
                "invalid_side_or_quantity",
                status="rejected",
                symbol=symbol_upper,
            )

        if self.dry_run:
            logger.info(f"[DRY RUN] Capital.com {side} {quantity} {symbol}")
            return self._no_action_receipt(
                "open_position",
                "dry_run_not_submitted",
                symbol=symbol_upper,
                side=direction,
                quantity=requested_quantity,
            )

        path = '/positions'
        market = self._resolve_market(symbol) or {}
        epic = str(market.get('epic') or "").strip()
        if not epic:
            return self._no_action_receipt(
                "open_position",
                "provider_market_resolution_required",
                status="rejected",
                symbol=symbol_upper,
            )

        payload = {
            "epic": epic,
            "direction": direction,
            "size": requested_quantity,
            "orderType": "MARKET",
            "guaranteedStop": False,
            "forceOpen": True,
        }
        try:
            self._add_optional_order_controls(
                payload,
                profit_level=profit_level,
                profit_distance=profit_distance,
                profit_amount=profit_amount,
                stop_level=stop_level,
                stop_distance=stop_distance,
                stop_amount=stop_amount,
                trailing_stop=trailing_stop,
            )
        except ValueError as exc:
            return self._no_action_receipt(
                "open_position",
                str(exc),
                status="rejected",
                symbol=symbol_upper,
                side=direction,
                quantity=requested_quantity,
            )

        try:
            response = self._request('POST', path, json_body=payload)
            if response.status_code in (200, 201):
                return self._submission_receipt(
                    response,
                    purpose="open_position",
                    submitted_payload=payload,
                )
            else:
                logger.error(f"Capital.com order failed: {response.text}")
                return self._no_action_receipt(
                    "open_position",
                    f"provider_http_{response.status_code}",
                    status="rejected",
                    symbol=symbol_upper,
                    side=direction,
                    quantity=requested_quantity,
                    provider_error=response.text,
                )
        except Exception as e:
            logger.error(f"Capital.com order error: {e}")
            return self._no_action_receipt(
                "open_position",
                "submission_request_failed",
                status="rejected",
                symbol=symbol_upper,
                side=direction,
                quantity=requested_quantity,
            )

    def get_working_orders(self) -> ObservationList:
        """Return pending Capital.com working orders."""
        if not self.enabled:
            return ObservationList(
                truth_status="no_data",
                reason="client_disabled",
                received_at=time.time(),
            )
        try:
            response = self._request('GET', '/workingorders')
            if response.status_code == 200:
                received_at = time.time()
                data = response.json() or {}
                source_timestamp = _fresh_provider_timestamp(
                    _response_source_timestamp(response),
                    CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S,
                    received_at=received_at,
                )
                orders = data.get('workingOrders', data.get('orders'))
                if source_timestamp is None or not isinstance(orders, list):
                    return ObservationList(
                        truth_status="no_data",
                        reason="working_orders_receipt_incomplete",
                        received_at=received_at,
                    )
                return ObservationList(
                    orders,
                    truth_status="real_observed",
                    reason="fresh_provider_working_orders",
                    source_timestamp=source_timestamp,
                    received_at=received_at,
                )
            logger.warning(f"Capital.com working orders fetch failed ({response.status_code}): {response.text[:200]}")
            return ObservationList(
                truth_status="no_data",
                reason=f"working_orders_http_{response.status_code}",
                received_at=time.time(),
            )
        except Exception as e:
            logger.error(f"Capital.com working orders error: {e}")
            return ObservationList(
                truth_status="no_data",
                reason="working_orders_request_failed",
                received_at=time.time(),
            )

    def place_working_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        level: float,
        *,
        order_type: str = "LIMIT",
        profit_level: Optional[float] = None,
        profit_distance: Optional[float] = None,
        profit_amount: Optional[float] = None,
        stop_level: Optional[float] = None,
        stop_distance: Optional[float] = None,
        stop_amount: Optional[float] = None,
        trailing_stop: Optional[bool] = None,
        good_till_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a pending limit/stop working order with optional take-profit controls."""
        if not self.enabled:
            return self._no_action_receipt("working_order", "client_disabled")
        direction = str(side or "").strip().upper()
        requested_quantity = _finite_number(quantity, positive=True)
        requested_level = _finite_number(level, positive=True)
        normalized_order_type = str(order_type or "").strip().upper()
        if (
            direction not in {"BUY", "SELL"}
            or requested_quantity is None
            or requested_level is None
            or normalized_order_type not in {"LIMIT", "STOP"}
        ):
            return self._no_action_receipt("working_order", "invalid_working_order_fields", status="rejected")
        market = self._resolve_market(symbol) or {}
        epic = str(market.get('epic') or "").strip()
        if not epic:
            return self._no_action_receipt(
                "working_order",
                "provider_market_resolution_required",
                status="rejected",
                symbol=str(symbol or "").upper(),
            )
        payload: Dict[str, Any] = {
            "epic": epic,
            "direction": direction,
            "size": requested_quantity,
            "level": requested_level,
            "type": normalized_order_type,
            "guaranteedStop": False,
        }
        try:
            self._add_optional_order_controls(
                payload,
                profit_level=profit_level,
                profit_distance=profit_distance,
                profit_amount=profit_amount,
                stop_level=stop_level,
                stop_distance=stop_distance,
                stop_amount=stop_amount,
                trailing_stop=trailing_stop,
                good_till_date=good_till_date,
            )
        except ValueError as exc:
            return self._no_action_receipt("working_order", str(exc), status="rejected")
        try:
            response = self._request('POST', '/workingorders', json_body=payload)
            if response.status_code in (200, 201):
                return self._submission_receipt(
                    response,
                    purpose="working_order",
                    submitted_payload=payload,
                )
            logger.error(f"Capital.com working order failed: {response.text}")
            return self._no_action_receipt(
                "working_order",
                f"provider_http_{response.status_code}",
                status="rejected",
                symbol=str(symbol or "").upper(),
                side=direction,
                quantity=requested_quantity,
                level=requested_level,
            )
        except Exception as e:
            logger.error(f"Capital.com working order error: {e}")
            return self._no_action_receipt("working_order", "submission_request_failed", status="rejected")

    def update_position_limits(
        self,
        deal_id: str,
        *,
        profit_level: Optional[float] = None,
        profit_distance: Optional[float] = None,
        profit_amount: Optional[float] = None,
        stop_level: Optional[float] = None,
        stop_distance: Optional[float] = None,
        stop_amount: Optional[float] = None,
        trailing_stop: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update take-profit/stop controls on an existing Capital.com position."""
        if not self.enabled:
            return {'success': False, 'error': 'client_disabled'}
        if not deal_id:
            return {'success': False, 'error': 'missing_deal_id'}
        payload: Dict[str, Any] = {"guaranteedStop": False}
        try:
            self._add_optional_order_controls(
                payload,
                profit_level=profit_level,
                profit_distance=profit_distance,
                profit_amount=profit_amount,
                stop_level=stop_level,
                stop_distance=stop_distance,
                stop_amount=stop_amount,
                trailing_stop=trailing_stop,
            )
        except ValueError as exc:
            return self._no_action_receipt("update_position_limits", str(exc), status="rejected")
        try:
            response = self._request('PUT', f'/positions/{deal_id}', json_body=payload)
            if response.status_code == 200:
                return self._submission_receipt(
                    response,
                    purpose="update_position_limits",
                    submitted_payload=payload,
                    expected_deal_id=deal_id,
                )
            logger.warning(f"Capital.com update_position_limits failed ({response.status_code}): {response.text[:200]}")
            return {'success': False, 'deal_id': deal_id, 'status_code': response.status_code, 'error': response.text[:200]}
        except Exception as e:
            logger.error(f"Capital.com update_position_limits exception: {e}")
            return {'success': False, 'deal_id': deal_id, 'error': str(e)}

    def delete_working_order(self, deal_id: str) -> Dict[str, Any]:
        """Cancel a pending Capital.com working order by deal ID."""
        if not self.enabled:
            return {'success': False, 'error': 'client_disabled'}
        if not deal_id:
            return {'success': False, 'error': 'missing_deal_id'}
        try:
            response = self._request('DELETE', f'/workingorders/{deal_id}')
            if response.status_code in (200, 204):
                return self._submission_receipt(
                    response,
                    purpose="cancel_working_order",
                    submitted_payload={"dealId": deal_id},
                    expected_deal_id=deal_id,
                )
            logger.warning(f"Capital.com delete_working_order failed ({response.status_code}): {response.text[:200]}")
            return {'success': False, 'deal_id': deal_id, 'status_code': response.status_code, 'error': response.text[:200]}
        except Exception as e:
            logger.error(f"Capital.com delete_working_order exception: {e}")
            return {'success': False, 'deal_id': deal_id, 'error': str(e)}

    def confirm_order(
        self,
        deal_reference: str,
        *,
        fee_receipt: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Read back and normalize a submitted order; fee evidence is mandatory."""
        if not self.enabled:
            return self._no_action_receipt("order_confirmation", "client_disabled")

        if not deal_reference:
            return self._no_action_receipt("order_confirmation", "missing_deal_reference")

        try:
            response = self._request('GET', f'/confirms/{deal_reference}')
            if response.status_code == 200:
                normalized = self.normalize_order_confirmation(
                    response.json(),
                    received_at=time.time(),
                    fee_receipt=fee_receipt,
                )
                if (
                    normalized.get("terminal_fill_receipt_complete") is True
                    or (
                        normalized.get("status") == "rejected"
                        and normalized.get("truth_status") == "real_observed"
                    )
                ):
                    pending = getattr(self, "_pending_close_confirmations", None)
                    if isinstance(pending, dict):
                        pending.pop(deal_reference, None)
                return normalized
            else:
                logger.error(f"Capital.com confirm failed: {response.text}")
                return self._no_action_receipt(
                    "order_confirmation",
                    f"provider_http_{response.status_code}",
                    status="incomplete",
                )
        except Exception as e:
            logger.error(f"Capital.com confirm error: {e}")
            return self._no_action_receipt(
                "order_confirmation",
                "confirmation_request_failed",
                status="incomplete",
            )

    def get_positions(self) -> ObservationList:
        """Return provider-visible positions without implying fee-complete fills."""
        if not self.enabled:
            return ObservationList(truth_status="no_data", reason="client_disabled", received_at=time.time())

        try:
            response = self._request('GET', '/positions')
            if response.status_code == 200:
                received_at = time.time()
                response_source_timestamp = _fresh_provider_timestamp(
                    _response_source_timestamp(response),
                    CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S,
                    received_at=received_at,
                )
                data = response.json()
                raw_positions = data.get('positions') if isinstance(data, dict) else None
                if response_source_timestamp is None or not isinstance(raw_positions, list):
                    return ObservationList(
                        truth_status="no_data",
                        reason="positions_receipt_incomplete",
                        received_at=received_at,
                    )
                normalized: List[Dict[str, Any]] = []
                incomplete_rows = 0
                for raw in raw_positions:
                    if not isinstance(raw, dict):
                        incomplete_rows += 1
                        continue
                    position = raw.get("position")
                    market = raw.get("market")
                    if not isinstance(position, dict) or not isinstance(market, dict):
                        incomplete_rows += 1
                        continue
                    deal_id = str(position.get("dealId") or "").strip()
                    created_at = _provider_timestamp(position.get("createdDateUTC") or position.get("createdDate"))
                    size = _finite_number(position.get("size"), positive=True)
                    level = _finite_number(position.get("level"), positive=True)
                    currency = str(position.get("currency") or "").strip().upper()
                    if not deal_id or created_at is None or size is None or level is None or not currency:
                        incomplete_rows += 1
                        continue
                    row = dict(raw)
                    row.update({
                        "truth_status": "real_observed",
                        "reason": "fresh_provider_position_readback_fee_receipt_pending",
                        "source_id": f"capital_position:{deal_id}",
                        "source_timestamp": created_at,
                        "received_at": received_at,
                        "receipt_source_timestamp": response_source_timestamp,
                        "generated_values": False,
                        "terminal_fill_receipt_complete": False,
                        "eligible_for_state": False,
                        "eligible_for_pnl": False,
                        "eligible_for_learning": False,
                    })
                    normalized.append(row)
                return ObservationList(
                    normalized,
                    truth_status="incomplete" if incomplete_rows or normalized else "real_observed",
                    reason=(
                        "provider_positions_visible_but_fee_receipts_required"
                        if normalized
                        else "no_open_positions"
                    ),
                    source_timestamp=response_source_timestamp,
                    received_at=received_at,
                )
            return ObservationList(
                truth_status="no_data",
                reason=f"positions_http_{response.status_code}",
                received_at=time.time(),
            )
        except Exception as e:
            logger.error(f"Capital.com positions error: {e}")
            return ObservationList(truth_status="no_data", reason="positions_request_failed", received_at=time.time())

    def close_position(self, deal_id: str) -> Dict[str, Any]:
        """
        Close an open CFD position by deal ID.

        Capital.com REST: DELETE /positions/{dealId}
        The DELETE response only acknowledges submission. The caller must pass
        its dealReference to confirm_order before mutating position/PnL state.
        """
        if not self.enabled:
            return self._no_action_receipt("close_position", "client_disabled")
        if not deal_id:
            return self._no_action_receipt("close_position", "missing_deal_id")

        try:
            resp = self._request('DELETE', f'/positions/{deal_id}')
            if resp.status_code in (200, 204):
                return self._submission_receipt(
                    resp,
                    purpose="close_position",
                    submitted_payload={"dealId": deal_id},
                    expected_deal_id=deal_id,
                )
            else:
                logger.warning(f"Capital.com close_position failed ({resp.status_code}): {resp.text[:200]}")
                return self._no_action_receipt(
                    "close_position",
                    f"provider_http_{resp.status_code}",
                    status="rejected",
                    requested_deal_id=deal_id,
                )
        except Exception as e:
            logger.error(f"Capital.com close_position exception: {e}")
            return self._no_action_receipt(
                "close_position",
                "submission_request_failed",
                status="rejected",
                requested_deal_id=deal_id,
            )

    def get_order_history(self, from_date: str = None) -> ObservationList:
        """Get order/deal history.

        Note: Capital's `/history/activity` endpoint expects a *datetime* `from`
        (e.g. `YYYY-MM-DDTHH:MM:SS`) and supports `detailed=true` for size/side/level.
        """
        if not self.enabled:
            return ObservationList(truth_status="no_data", reason="client_disabled", received_at=time.time())

        path = '/history/activity'
        params: Dict[str, Any] = {"detailed": "true"}
        if from_date:
            # API rejects date-only strings; coerce to start-of-day datetime.
            raw = str(from_date).strip()
            if raw and "T" not in raw:
                raw = raw + "T00:00:00"
            params['from'] = raw

        try:
            response = self._request('GET', path, params=params)
            if response.status_code == 200:
                received_at = time.time()
                response_source_timestamp = _fresh_provider_timestamp(
                    _response_source_timestamp(response),
                    CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S,
                    received_at=received_at,
                )
                data = response.json()
                raw_activities = data.get('activities') if isinstance(data, dict) else None
                if response_source_timestamp is None or not isinstance(raw_activities, list):
                    return ObservationList(
                        truth_status="no_data",
                        reason="activity_receipt_incomplete",
                        received_at=received_at,
                    )
                activities: List[Dict[str, Any]] = []
                incomplete_rows = 0
                for raw_activity in raw_activities:
                    if not isinstance(raw_activity, dict):
                        incomplete_rows += 1
                        continue
                    deal_id = str(raw_activity.get("dealId") or "").strip()
                    activity_timestamp = _provider_timestamp(
                        raw_activity.get("dateUTC") or raw_activity.get("date")
                    )
                    activity_type = str(raw_activity.get("type") or "").strip().upper()
                    activity_status = str(raw_activity.get("status") or "").strip().upper()
                    epic = str(raw_activity.get("epic") or "").strip().upper()
                    if not deal_id or activity_timestamp is None or not activity_type or not activity_status or not epic:
                        incomplete_rows += 1
                        continue
                    activity = dict(raw_activity)
                    activity.update({
                        "truth_status": "real_observed",
                        "reason": "activity_is_not_a_fee_complete_fill_receipt",
                        "source_id": f"capital_activity:{deal_id}:{activity_timestamp}",
                        "source_timestamp": activity_timestamp,
                        "received_at": received_at,
                        "receipt_source_timestamp": response_source_timestamp,
                        "generated_values": False,
                        "terminal_fill": False,
                        "terminal_fill_receipt_complete": False,
                        "eligible_for_state": False,
                        "eligible_for_pnl": False,
                        "eligible_for_learning": False,
                    })
                    activities.append(activity)
                return ObservationList(
                    activities,
                    truth_status="incomplete" if incomplete_rows or activities else "real_observed",
                    reason=(
                        "provider_activities_require_confirmation_and_fee_reconciliation"
                        if activities
                        else "no_activities"
                    ),
                    source_timestamp=response_source_timestamp,
                    received_at=received_at,
                )
            return ObservationList(
                truth_status="no_data",
                reason=f"history_http_{response.status_code}",
                received_at=time.time(),
            )
        except Exception as e:
            logger.error(f"Capital.com history error: {e}")
            return ObservationList(truth_status="no_data", reason="history_request_failed", received_at=time.time())

    def get_transaction_history(self, last_period: int = 600) -> ObservationList:
        """Return exact provider-booked transactions without inferring fees.

        Capital's public API documents ``GET /history/transactions`` as the
        transaction ledger. Rows remain observations only; callers must bind
        an exact processed trade/reference before deriving a fee receipt.
        """

        if not self.enabled:
            return ObservationList(
                truth_status="no_data",
                reason="client_disabled",
                received_at=time.time(),
            )
        if (
            isinstance(last_period, bool)
            or not isinstance(last_period, int)
            or not 1 <= last_period <= 86_400
        ):
            return ObservationList(
                truth_status="no_data",
                reason="transaction_history_window_invalid",
                received_at=time.time(),
            )

        try:
            response = self._request(
                "GET",
                "/history/transactions",
                params={"lastPeriod": last_period},
            )
            if response.status_code != 200:
                return ObservationList(
                    truth_status="no_data",
                    reason=f"transactions_http_{response.status_code}",
                    received_at=time.time(),
                )
            received_at = time.time()
            response_source_timestamp = _fresh_provider_timestamp(
                _response_source_timestamp(response),
                CAPITAL_ACCOUNT_RECEIPT_MAX_AGE_S,
                received_at=received_at,
            )
            data = response.json()
            raw_transactions = data.get("transactions") if isinstance(data, dict) else None
            if response_source_timestamp is None or not isinstance(raw_transactions, list):
                return ObservationList(
                    truth_status="no_data",
                    reason="transaction_history_receipt_incomplete",
                    received_at=received_at,
                )
            transactions: List[Dict[str, Any]] = []
            incomplete_rows = 0
            for raw in raw_transactions:
                if not isinstance(raw, dict):
                    incomplete_rows += 1
                    continue
                timestamp = _provider_timestamp(
                    raw.get("dateUtc") or raw.get("dateUTC") or raw.get("date")
                )
                instrument = str(raw.get("instrumentName") or "").strip().upper()
                transaction_type = str(raw.get("transactionType") or "").strip().upper()
                reference = str(raw.get("reference") or "").strip()
                amount = _finite_number(raw.get("size"))
                currency = str(raw.get("currency") or "").strip().upper()
                status = str(raw.get("status") or "").strip().upper()
                if (
                    timestamp is None
                    or not instrument
                    or not transaction_type
                    or not reference
                    or amount is None
                    or not currency
                    or not status
                ):
                    incomplete_rows += 1
                    continue
                transactions.append(
                    {
                        "amount": amount,
                        "currency": currency,
                        "generated_values": False,
                        "instrument_name": instrument,
                        "note": str(raw.get("note") or "").strip() or None,
                        "provider_response": dict(raw),
                        "received_at": received_at,
                        "reference": reference,
                        "source_id": (
                            f"capital_transaction:{reference}:{transaction_type}:{timestamp}"
                        ),
                        "source_timestamp": timestamp,
                        "status": status,
                        "transaction_type": transaction_type,
                        "truth_status": "real_observed",
                    }
                )
            return ObservationList(
                transactions,
                truth_status="incomplete" if incomplete_rows else "real_observed",
                reason=(
                    "transaction_history_contains_incomplete_rows"
                    if incomplete_rows
                    else "complete_provider_transaction_history"
                ),
                source_timestamp=response_source_timestamp,
                received_at=received_at,
            )
        except Exception as exc:
            logger.error("Capital.com transactions error: %s", type(exc).__name__)
            return ObservationList(
                truth_status="no_data",
                reason="transaction_history_request_failed",
                received_at=time.time(),
            )

    def compute_trade_fees(self, position: Dict[str, Any]) -> Dict[str, Any]:
        """Expose fees only from a complete provider fee receipt."""
        received_at = time.time()
        position_data = position.get("position") if isinstance(position.get("position"), dict) else position
        market_data = position.get("market") if isinstance(position.get("market"), dict) else {}
        size = _finite_number(
            position.get("filled_qty") if position.get("filled_qty") is not None else position_data.get("size"),
            positive=True,
        )
        level = _finite_number(
            position.get("filled_avg_price")
            if position.get("filled_avg_price") is not None
            else position_data.get("level"),
            positive=True,
        )
        epic = str(position.get("epic") or market_data.get("epic") or "").strip().upper()
        notional = size * level if size is not None and level is not None else None
        fee_receipt = self._normalize_fee_receipt(
            position.get("fee_receipt") or position.get("provider_fee_receipt"),
            received_at=received_at,
        )
        base = {
            "spread_cost": None,
            "spread_pct": None,
            "overnight_cost": None,
            "total_fees": None,
            "fee_pct": None,
            "fee_currency": None,
            "notional": notional,
            "epic": epic or None,
            "received_at": received_at,
            "generated_values": False,
            "eligible_for_pnl": False,
            "eligible_for_learning": False,
        }
        if notional is None:
            return {
                **base,
                "truth_status": "no_data",
                "reason": "position_quantity_or_price_missing",
                "source_id": None,
                "source_timestamp": None,
            }
        if fee_receipt is None:
            return {
                **base,
                "truth_status": "incomplete",
                "reason": "provider_fee_receipt_required",
                "source_id": None,
                "source_timestamp": _provider_timestamp(position.get("source_timestamp")),
            }
        return {
            **base,
            "total_fees": fee_receipt["amount"],
            "fee_pct": fee_receipt["amount"] / notional,
            "fee_currency": fee_receipt["currency"],
            "truth_status": "real_derived",
            "reason": "provider_fee_receipt_over_observed_notional",
            "source_id": fee_receipt["source_id"],
            "source_timestamp": fee_receipt["source_timestamp"],
            "eligible_for_pnl": True,
            "eligible_for_learning": True,
        }

    def get_positions_with_fees(self) -> ObservationList:
        """Get all positions with computed fee metrics."""
        positions = self.get_positions()
        for pos in positions:
            fees = self.compute_trade_fees(pos)
            pos['computed_fees'] = fees
        return ObservationList(
            positions,
            truth_status=getattr(positions, "truth_status", "incomplete"),
            reason="positions_with_provider_fee_receipt_status",
            source_timestamp=getattr(positions, "source_timestamp", None),
            received_at=time.time(),
        )

    def compute_order_fees_in_quote(self, position: Dict[str, Any], primary_quote: str = "USD") -> Optional[float]:
        """
        Calculate total fees for a position/trade in the quote currency.
        This provides a consistent interface with Binance/Kraken clients.

        Returns None when no provider receipt exists or a currency conversion
        would be required.
        """
        fees = self.compute_trade_fees(position)
        fee_currency = str(fees.get("fee_currency") or "").upper()
        requested_currency = str(primary_quote or "").upper()
        if fees.get("truth_status") != "real_derived" or fee_currency != requested_currency:
            return None
        return _finite_number(fees.get("total_fees"), nonnegative=True)

    def calculate_cost_basis(self, symbol: str) -> Dict[str, Any]:
        """
        Calculate cost basis for a symbol from order history.

        Capital.com uses 'epic' for symbol names (e.g., 'BTCUSD', 'AAPL').

        Returns dict with:
        - symbol: The symbol/epic
        - total_quantity: Net quantity held
        - total_cost: Total cost of buys
        - avg_cost: Average cost per unit
        - trades: Number of trades
        """
        history = self.get_order_history()
        received_at = time.time()
        normalized_symbol = str(symbol or "").strip().upper()
        no_data = {
            "symbol": normalized_symbol,
            "total_quantity": None,
            "total_cost": None,
            "avg_cost": None,
            "trades": None,
            "total_fees_by_currency": {},
            "truth_status": "no_data",
            "reason": "order_history_unavailable",
            "source_id": None,
            "source_timestamp": None,
            "received_at": received_at,
            "generated_values": False,
            "eligible_for_pnl": False,
            "eligible_for_learning": False,
        }
        if not history:
            if (
                getattr(history, "truth_status", None) == "real_observed"
                and getattr(history, "reason", None) == "no_activities"
            ):
                return {
                    **no_data,
                    "total_quantity": 0.0,
                    "total_cost": 0.0,
                    "avg_cost": None,
                    "trades": 0,
                    "truth_status": "real_observed",
                    "reason": "provider_history_confirms_no_trades",
                    "source_timestamp": getattr(history, "source_timestamp", None),
                }
            return no_data

        total_qty = 0.0
        buy_qty = 0.0
        buy_cost = 0.0
        trade_count = 0
        fees_by_currency: Dict[str, float] = {}
        source_timestamps: List[float] = []
        source_ids: List[str] = []

        for receipt in history:
            if not isinstance(receipt, dict):
                continue
            epic = str(receipt.get("epic") or "").strip().upper()
            if epic != normalized_symbol:
                continue
            if (
                receipt.get("truth_status") != "real_observed"
                or receipt.get("generated_values") is not False
                or receipt.get("terminal_fill") is not True
                or receipt.get("terminal_fill_receipt_complete") is not True
                or receipt.get("eligible_for_state") is not True
                or receipt.get("eligible_for_pnl") is not True
                or receipt.get("eligible_for_learning") is not True
            ):
                continue
            provider_order_id = str(receipt.get("provider_order_id") or "").strip()
            provider_deal_id = str(receipt.get("provider_deal_id") or "").strip()
            source_id = str(receipt.get("source_id") or "").strip()
            source_timestamp = _provider_timestamp(receipt.get("source_timestamp"))
            quantity = _finite_number(receipt.get("filled_qty"), positive=True)
            price = _finite_number(receipt.get("filled_avg_price"), positive=True)
            direction = str(receipt.get("side") or "").strip().upper()
            fee_receipt = self._normalize_fee_receipt(receipt.get("fee_receipt"), received_at=received_at)
            if (
                not provider_order_id
                or not provider_deal_id
                or not source_id
                or source_timestamp is None
                or source_timestamp > received_at + CAPITAL_FUTURE_SKEW_S
                or quantity is None
                or price is None
                or direction not in {"BUY", "SELL"}
                or fee_receipt is None
            ):
                continue

            trade_count += 1
            if direction == "BUY":
                total_qty += quantity
                buy_qty += quantity
                buy_cost += quantity * price
            else:
                total_qty -= quantity
            fee_currency = fee_receipt["currency"]
            fees_by_currency[fee_currency] = fees_by_currency.get(fee_currency, 0.0) + fee_receipt["amount"]
            source_timestamps.extend([source_timestamp, fee_receipt["source_timestamp"]])
            source_ids.extend([source_id, fee_receipt["source_id"]])

        if trade_count == 0:
            return {
                **no_data,
                "truth_status": "incomplete",
                "reason": "terminal_fee_complete_fill_receipts_required",
            }
        return {
            "symbol": normalized_symbol,
            "total_quantity": total_qty,
            "total_cost": buy_cost,
            "avg_cost": buy_cost / buy_qty if buy_qty > 0 else None,
            "trades": trade_count,
            "total_fees_by_currency": fees_by_currency,
            "truth_status": "real_derived",
            "reason": "cost_basis_from_terminal_fee_complete_provider_fills",
            "source_id": source_ids,
            "source_timestamp": min(source_timestamps),
            "received_at": received_at,
            "generated_values": False,
            "eligible_for_pnl": True,
            "eligible_for_learning": True,
        }
