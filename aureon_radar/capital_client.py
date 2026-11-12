import os
import sys
import logging
import requests
import time
import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure repo-root package imports and env resolution work when launched directly.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Load environment variables from repo-root .env first, then local .env.
try:
    from dotenv import load_dotenv
    # Try repo root first
    env_path = os.path.join(_REPO_ROOT, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)
    # Also try local directory (radar dir)
    local_env = os.path.join(_THIS_DIR, '.env')
    if os.path.exists(local_env):
        load_dotenv(local_env, override=True)
    # Fallback: try loading without path
    if not os.path.exists(env_path) and not os.path.exists(local_env):
        load_dotenv(override=False)
except ImportError:
    pass

try:
    from aureon.core.aureon_env import load_aureon_environment

    load_aureon_environment(Path(_REPO_ROOT), override=False)
except Exception:
    pass

from aureon.exchanges import capital_shared_state as _cap_shared

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

_KEEPALIVE_THREAD: Optional[threading.Thread] = None

CAPITAL_HTTP_TIMEOUT = float(os.getenv('CAPITAL_HTTP_TIMEOUT_SECS', '8'))
CAPITAL_SESSION_RETRY_BACKOFF_SECS = float(os.getenv('CAPITAL_SESSION_RETRY_BACKOFF_SECS', '15'))
CAPITAL_TICKER_WORKERS = int(os.getenv('CAPITAL_TICKER_WORKERS', '4'))
CAPITAL_TICKER_MEM_TTL = float(os.getenv('CAPITAL_TICKER_MEM_TTL', '25.0'))  # In-memory per-symbol ticker cache TTL
CAPITAL_MONITOR_CACHE_PATH = os.getenv("CAPITAL_MONITOR_CACHE_PATH", os.path.join("ws_cache", "capital_monitor.json"))
CAPITAL_MONITOR_CACHE_MAX_AGE_S = float(os.getenv("CAPITAL_MONITOR_CACHE_MAX_AGE_S", "20"))
# Safety cap for how old a cached snapshot/account list may be before we stop
# serving it as fresh.  Stale data is still returned during graceful degradation
# but is loudly logged as STALE so callers can reject it for live trading.
CAPITAL_MAX_STALE_SNAPSHOT_AGE_S = float(os.getenv("CAPITAL_MAX_STALE_SNAPSHOT_AGE_S", "300"))
# Disk cache for market catalogue — survives process restarts, avoids re-downloading 6799 markets
CAPITAL_MARKET_DISK_CACHE_PATH = os.getenv(
    "CAPITAL_MARKET_DISK_CACHE_PATH",
    os.path.join(_REPO_ROOT, "ws_cache", "capital_market_catalogue.json"),
)

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
            self.base_url = "https://demo-api-capital.backend-capital.com/api/v1"
        else:
            self.base_url = "https://api-capital.backend-capital.com/api/v1"

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
        # False when get_all_markets() last returned a partial walk (no cache to fall back on).
        self.market_catalogue_complete = bool(self.market_cache)
        self._rate_limit_until = 0  # Timestamp when rate limit expires
        self._rate_limit_logged = False  # Only log rate limits once
        self._session_error_logged = False  # Only log session errors once
        self._next_session_retry_at = 0.0
        self._ticker_mem_cache: Dict[str, Dict[str, Any]] = {}  # In-memory per-symbol ticker cache
        self._ticker_mem_cache_times: Dict[str, float] = {}    # Fetch timestamps for TTL
        self._accounts_cache: List[Dict[str, Any]] = []         # In-memory accounts cache
        self._accounts_cache_time: float = 0.0                  # Accounts cache fetch timestamp
        self._snapshot_cache: Dict[str, Any] = {}               # In-memory market snapshot cache {epic: data}
        self._snapshot_cache_times: Dict[str, float] = {}       # Snapshot cache fetch timestamps
        self._shared_key = _cap_shared.account_key(self.api_key, self.demo_mode)
        self._last_used_at = float(self.session_start_time or 0.0)
        self._last_slot_refusal = ""

        # Global host rate budget: reserves POSITIONS slots for account reads
        # and EXECUTION slots for session/order writes, so analytics can't starve
        # the portfolio writer / progress monitor.
        self._rate_budget = None
        self._RequestPriority = None
        self._budget_wait = None
        try:
            from aureon.core.global_rate_budget import (
                RequestPriority,
                get_host_rate_budget,
                wait_for_slot_deferred,
            )
            host = urlparse(self.base_url).netloc
            self._rate_budget = get_host_rate_budget(host)
            self._RequestPriority = RequestPriority
            self._budget_wait = wait_for_slot_deferred
        except Exception as exc:
            logger.debug("capital GlobalRateBudget unavailable (%s) - running unbudgeted", type(exc).__name__)

        if not self.api_key or not self.identifier or not self.password:
            logger.warning("Capital.com credentials not fully set. Client will be disabled.")
            self.enabled = False
            self.init_error = "credentials_missing"
        else:
            self.enabled = True
            self._create_session()

    @property
    def authenticated(self) -> bool:
        """Return True if the client has a valid, non-expired session."""
        if not self.enabled:
            return False
        if not self.cst or not self.x_security_token:
            return False
        # Session expires after ~55 minutes; refresh proactively at 50 min.
        return (time.time() - self.session_start_time) < (55 * 60)

    # ── rate budget helpers ───────────────────────────────────────────────
    def _budget_priority(self, method: str, path: str):
        """EXECUTION for session/auth/order mutations, POSITIONS for account/
        position/history reads, QUOTES for market data."""
        from aureon.core.global_rate_budget import RequestPriority
        method = str(method or "").upper()
        lowered = str(path or "").lower()
        if method == "POST" and lowered == "/session":
            return RequestPriority.EXECUTION
        if method in ("POST", "PUT", "DELETE"):
            return RequestPriority.EXECUTION
        if lowered.startswith(("/accounts", "/positions", "/confirms", "/history", "/workingorders")):
            return RequestPriority.POSITIONS
        if lowered.startswith(("/markets", "/marketnavigation")):
            return RequestPriority.QUOTES
        return RequestPriority.POSITIONS

    def _budget_acquire(self, method: str, path: str, *, write: bool = False,
                        max_wait_s: float = 10.0) -> bool:
        if self._rate_budget is None or self._RequestPriority is None:
            return True
        priority = self._budget_priority(method, path)
        granted = self._budget_wait(
            self._rate_budget, priority,
            is_trading=priority.name == "EXECUTION",
            max_wait_s=max_wait_s,
        )
        if not granted:
            if write:
                raise RuntimeError(
                    f"capital rate budget deferred {priority.name} {method} {path} "
                    f"beyond {max_wait_s}s - NOT sent (fail-closed)"
                )
            logger.warning(
                "capital rate budget deferred %s %s %s beyond %ss - proceeding anyway",
                priority.name, method, path, max_wait_s,
            )
        return granted

    def _budget_on_429(self, method: str, path: str) -> None:
        if self._rate_budget is None:
            return
        try:
            priority = self._budget_priority(method, path)
            self._rate_budget.on_429_error(priority)
        except Exception:
            pass

    def _record_shared_429(self, method: str, path: str, resp: Any) -> float:
        """Record a 429 as the shared backoff (Retry-After honoured, with jitter)."""
        global _SHARED_SESSION
        retry_after = _cap_shared.parse_retry_after(getattr(resp, "headers", None))
        wait_s = _cap_shared.with_jitter(
            retry_after if retry_after is not None else _cap_shared.DEFAULT_RATE_LIMIT_BACKOFF_S
        )
        self._rate_limit_until = _cap_shared.record_backoff(self._shared_key_name(), wait_s)
        _SHARED_SESSION["rate_limit_until"] = self._rate_limit_until
        self._budget_on_429(method, path)
        logger.warning(
            "Capital.com rate limited (HTTP 429) on %s %s - backing off for %d seconds%s; "
            "shared backoff until %s UTC (%d s remaining)",
            method,
            path,
            int(round(wait_s)),
            " (Retry-After)" if retry_after is not None else "",
            datetime.fromtimestamp(self._rate_limit_until, timezone.utc).strftime("%H:%M:%S"),
            int(round(max(0.0, self._rate_limit_until - time.time()))),
        )
        return wait_s

    def _drop_shared_session(self) -> None:
        """Forget a session Capital rejected, here and in the shared cache.

        The next call re-logs in through _create_session (login lock, 1/s spacing).
        """
        global _SHARED_SESSION
        try:
            _cap_shared.invalidate_session(self._shared_key_name(), self.cst)
        except Exception:
            pass
        self.cst = None
        self.x_security_token = None
        self.session_start_time = 0.0
        _SHARED_SESSION["cst"] = None
        _SHARED_SESSION["x_security_token"] = None
        _SHARED_SESSION["session_start_time"] = 0.0

    @staticmethod
    def _safe_error_code(response: Any) -> str:
        """Capital's errorCode only (never the body, which can echo identifiers)."""
        try:
            payload = response.json()
        except Exception:
            return "unknown"
        code = payload.get("errorCode") if isinstance(payload, dict) else None
        if not isinstance(code, str) or not code:
            return "unknown"
        cleaned = "".join(ch for ch in code if ch.isalnum() or ch in "._-")[:80]
        return cleaned or "unknown"

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

    def authenticate(self) -> bool:
        """Explicit authentication entry point.

        Returns True if a valid session exists or was successfully created.
        This method is called by DualCapitalConnector.authenticate().
        """
        if not self.enabled:
            return False
        if self.authenticated:
            return True
        self._create_session()
        return self.authenticated

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

        # Check if this instance already has a valid session
        if (self.cst and self.x_security_token and
                (now - self.session_start_time) < (50 * 60)):  # 50 min buffer
            logger.debug("Capital.com session still valid (within 50 min), skipping re-auth")
            return

        key = self._shared_key_name()
        # One login in flight across all processes and both clients; the
        # others wait and then reuse the session it stored.
        with _cap_shared.login_lock():
            with _cap_shared.locked_state(key) as bucket:
                now = time.time()
                shared_until = float(bucket.get("rate_limit_until") or 0.0)
                if now < shared_until:
                    self._rate_limit_until = shared_until
                    _SHARED_SESSION["rate_limit_until"] = max(
                        float(_SHARED_SESSION.get("rate_limit_until", 0.0) or 0.0), shared_until
                    )
                    self.init_error = "rate_limited"
                    return
                if _cap_shared.session_is_fresh(bucket, now):
                    self.cst = bucket.get("cst")
                    self.x_security_token = bucket.get("x_security_token")
                    self.session_start_time = float(bucket.get("session_start_time") or now)
                    self._last_used_at = float(bucket.get("last_used_at") or self.session_start_time)
                    self.init_error = ""
                    _SHARED_SESSION["cst"] = self.cst
                    _SHARED_SESSION["x_security_token"] = self.x_security_token
                    _SHARED_SESSION["session_start_time"] = self.session_start_time
                    _SHARED_SESSION["demo_mode"] = self.demo_mode
                    _SHARED_SESSION["init_error"] = ""
                    logger.debug("Capital.com session reused from shared cache.")
                    self._start_keepalive_thread()
                    return
                login_wait = (
                    float(bucket.get("last_login_at") or 0.0)
                    + _cap_shared.min_login_interval_s()
                    - now
                )
            if login_wait > 0:
                time.sleep(login_wait)
            with _cap_shared.locked_state(key) as bucket:
                bucket["last_login_at"] = time.time()
            self._post_session(key)

    def _shared_key_name(self) -> str:
        key = getattr(self, "_shared_key", None)
        if not key:
            key = _cap_shared.account_key(getattr(self, "api_key", None), bool(getattr(self, "demo_mode", False)))
            self._shared_key = key
        return key

    def _post_session(self, key: str) -> None:
        """Send one real POST /session (caller holds the cross-process login lock)."""
        global _SHARED_SESSION
        url = f"{self.base_url}/session"
        payload = {
            "identifier": self.identifier,
            "password": self.password
        }
        headers = {
            "X-CAP-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        # Counted on purpose: every real login attempt is logged (no secrets).
        logger.warning(
            "Capital.com login attempt: POST /session (%s, pid %s)",
            "demo" if self.demo_mode else "live",
            os.getpid(),
        )
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=CAPITAL_HTTP_TIMEOUT)
            if response.status_code == 200:
                self.cst = response.headers.get('CST')
                self.x_security_token = response.headers.get('X-SECURITY-TOKEN')
                self.session_start_time = time.time()
                self._last_used_at = self.session_start_time
                self._next_session_retry_at = 0.0
                self.init_error = ""
                self._session_error_logged = False  # Reset on success
                # Update shared caches so the main client and other processes reuse it
                if isinstance(self.cst, str) and isinstance(self.x_security_token, str):
                    with _cap_shared.locked_state(key) as bucket:
                        bucket["cst"] = self.cst
                        bucket["x_security_token"] = self.x_security_token
                        bucket["session_start_time"] = self.session_start_time
                        bucket["last_used_at"] = self.session_start_time
                _SHARED_SESSION["cst"] = self.cst
                _SHARED_SESSION["x_security_token"] = self.x_security_token
                _SHARED_SESSION["session_start_time"] = self.session_start_time
                _SHARED_SESSION["demo_mode"] = self.demo_mode
                _SHARED_SESSION["init_error"] = self.init_error
                logger.info("Capital.com session established.")
                self._start_keepalive_thread()
            elif response.status_code == 429 or 'too-many.requests' in response.text.lower():
                retry_after = _cap_shared.parse_retry_after(getattr(response, "headers", None))
                wait_s = _cap_shared.with_jitter(
                    retry_after if retry_after is not None else _cap_shared.DEFAULT_RATE_LIMIT_BACKOFF_S
                )
                self._rate_limit_until = _cap_shared.record_backoff(key, wait_s)
                _SHARED_SESSION["rate_limit_until"] = self._rate_limit_until
                self.init_error = "rate_limited"
                self._budget_on_429("POST", "/session")
                logger.warning(
                    "Capital.com rate limited (HTTP 429) on POST /session - backing off for %d seconds%s; "
                    "shared backoff until %s UTC (%d s remaining)",
                    int(round(wait_s)),
                    " (Retry-After)" if retry_after is not None else "",
                    datetime.fromtimestamp(self._rate_limit_until, timezone.utc).strftime("%H:%M:%S"),
                    int(round(max(0.0, self._rate_limit_until - time.time()))),
                )
                self._session_error_logged = True
            else:
                self.init_error = f"http_{response.status_code}"
                if not self._session_error_logged:
                    # Status and errorCode only: the body can echo identifiers.
                    logger.error(
                        "Failed to create Capital.com session: HTTP %s (errorCode %s)",
                        response.status_code,
                        self._safe_error_code(response),
                    )
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

    def keep_alive_if_idle(self) -> bool:
        """Send one shared GET /ping if the account has been quiet ~9 minutes.

        Capital.com drops a session after 10 idle minutes. The claim is made
        under the cross-process lock, so only one process pings; nobody logs
        in for this. Returns True if this call sent the ping.
        """
        if not getattr(self, "enabled", False):
            return False
        key = self._shared_key_name()
        tokens = _cap_shared.claim_keepalive(key)
        if not tokens:
            return False
        if not self._acquire_capital_request_slot(False):
            return False
        headers = {
            "X-CAP-API-KEY": self.api_key,
            "CST": tokens["cst"],
            "X-SECURITY-TOKEN": tokens["x_security_token"],
            "Content-Type": "application/json",
        }
        try:
            resp = requests.request(
                "GET",
                f"{self.base_url}/ping",
                headers=headers,
                timeout=CAPITAL_HTTP_TIMEOUT,
            )
        except Exception as e:
            logger.warning(f"Capital.com keep-alive ping failed: {type(e).__name__}")
            return True
        if resp.status_code == 429 or 'too-many.requests' in (getattr(resp, "text", "") or "").lower():
            # Same shared backoff as any other 429, so no process keeps calling.
            self._record_shared_429("GET", "/ping", resp)
        elif resp.status_code in (401, 403):
            _cap_shared.invalidate_session(key, tokens["cst"])
        logger.info("Capital.com keep-alive ping sent (HTTP %s)", resp.status_code)
        return True

    def _start_keepalive_thread(self) -> None:
        """One daemon per process that pings a quiet shared session (see keep_alive_if_idle)."""
        global _KEEPALIVE_THREAD
        if os.getenv("CAPITAL_SESSION_KEEPALIVE", "1") == "0":
            return
        if _KEEPALIVE_THREAD is not None and _KEEPALIVE_THREAD.is_alive():
            return

        def _loop(client=self):
            while True:
                time.sleep(30.0)
                try:
                    client.keep_alive_if_idle()
                except Exception:
                    pass

        _KEEPALIVE_THREAD = threading.Thread(target=_loop, name="capital-radar-keepalive", daemon=True)
        _KEEPALIVE_THREAD.start()

    def _acquire_capital_request_slot(self, is_mutation: bool) -> bool:
        """Pace requests across processes; False while a shared 429 backoff runs."""
        key = self._shared_key_name()
        refused = _cap_shared.acquire_request_slot(key, is_order=is_mutation)
        if refused is None:
            self._last_used_at = time.time()
            self._last_slot_refusal = ""
            return True
        self._last_slot_refusal = refused
        try:
            self._rate_limit_until = max(
                float(getattr(self, "_rate_limit_until", 0.0) or 0.0),
                time.time() + _cap_shared.backoff_remaining(key),
            )
        except Exception:
            pass
        return False

    @staticmethod
    def _is_order_path(method: str, path: str) -> bool:
        """Order and position mutations share Capital's 1-per-0.1s limit."""
        normalized = str(method or "").strip().upper()
        if normalized not in {"POST", "PUT", "DELETE"}:
            return False
        lowered = str(path or "").split("?", 1)[0].lower()
        return lowered == "/positions" or lowered.startswith("/positions/") \
            or lowered == "/workingorders" or lowered.startswith("/workingorders/")

    def _request(self, method: str, path: str, *, params: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Perform an API request with automatic session refresh and one retry on
        invalid session token or HTTP 401.
        """
        global _SHARED_SESSION
        normalized_method = str(method).strip().upper()
        is_order = self._is_order_path(normalized_method, path)

        # Return error response if client is disabled (don't raise exception)
        if not self.enabled:
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

        url = f"{self.base_url}{path}"
        headers = self._get_headers()
        if not headers:
            return self._error_response(503, "session_unavailable", self.init_error or "session_unavailable")
        if not self._acquire_capital_request_slot(is_order):
            # A shared 429 backoff is running, or (orders only) no working
            # cross-process lock exists: do not send anything.
            if getattr(self, "_last_slot_refusal", "") == "shared_state_unavailable":
                return self._error_response(503, "shared_state_unavailable", _cap_shared.ORDERS_REFUSED_LOG)
            return self._error_response(429, "rate_limited", "capital_shared_backoff_active")

        is_write = normalized_method != "GET"
        try:
            # Local organ budget is extra; the shared lock is the authority.
            self._budget_acquire(normalized_method, path, write=is_write, max_wait_s=15.0)
            resp = requests.request(method.upper(), url, headers=headers, params=params, json=json_body, timeout=CAPITAL_HTTP_TIMEOUT)
        except RuntimeError as exc:
            # Budget fail-closed for writes; for reads we never pass this way
            # because _budget_acquire logs and proceeds. Only writes raise.
            logger.warning("Capital.com %s %s blocked by rate budget: %s", method, path, exc)
            return self._error_response(503, "rate_budget_deferred", str(exc)[:200])
        except Exception as e:
            logger.error(f"Capital.com request error ({method} {path}): {e}")
            return self._error_response(503, "request_error", str(e))

        # Rate limit handling — shared so the main client backs off too.
        rate_limit_hit = resp.status_code == 429 or ('too-many.requests' in (resp.text or '').lower())
        if rate_limit_hit:
            self._record_shared_429(normalized_method, path, resp)
            self._rate_limit_logged = True
            return resp

        # Reset rate limit log flag on success
        if resp.status_code == 200 and self._rate_limit_logged:
            self._rate_limit_logged = False

        # Mutations are not retried (the slot has already been spent).
        if is_order:
            if resp.status_code == 401 or ('error.invalid.session.token' in (resp.text or '').lower()):
                # Do not leave the dead token shared: the next call re-logs in
                # through the paced POST /session path. The order is not resent.
                logger.warning("Capital.com session invalid on %s %s; shared session cleared, not retried",
                               normalized_method, path)
                self._drop_shared_session()
            return resp

        # Handle invalid session
        if resp.status_code in (401, 403) or ('error.invalid.session.token' in (resp.text or '').lower()):
            logger.warning("Capital.com session invalid; attempting re-login and retry")
            # Clear stale tokens and re-enable so _create_session does a real POST
            self._drop_shared_session()
            self.enabled = True
            self._session_error_logged = False
            self._create_session()
            headers = self._get_headers()
            if not headers:
                return self._error_response(503, "session_unavailable", self.init_error or "session_unavailable")
            if not self._acquire_capital_request_slot(False):
                if getattr(self, "_last_slot_refusal", "") == "shared_state_unavailable":
                    return self._error_response(503, "shared_state_unavailable", _cap_shared.ORDERS_REFUSED_LOG)
                return self._error_response(429, "rate_limited", "capital_shared_backoff_active")
            try:
                self._budget_acquire(normalized_method, path, write=is_write, max_wait_s=15.0)
                resp = requests.request(method.upper(), url, headers=headers, params=params, json=json_body, timeout=CAPITAL_HTTP_TIMEOUT)
            except RuntimeError as exc:
                logger.warning("Capital.com retry %s %s blocked by rate budget: %s", method, path, exc)
                return self._error_response(503, "rate_budget_deferred", str(exc)[:200])
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
            self.market_catalogue_complete = True
            return self.market_cache

        # Return instance in-memory cache if still fresh.
        if (
            not force_refresh
            and self.market_cache
            and (time.time() - self.market_cache_time) < self.market_cache_ttl
        ):
            self.market_catalogue_complete = True
            return self.market_cache

        # Don't download while rate-limited, or soon after an incomplete walk.
        if time.time() < self._rate_limit_until:
            return self.market_cache or []
        if not force_refresh and time.time() < float(getattr(self, "_market_walk_retry_at", 0.0) or 0.0):
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
                            self.market_catalogue_complete = True
                            return self.market_cache
            except Exception as _disk_err:
                logger.debug(f"Disk market cache load failed: {_disk_err}")

        markets: List[Dict[str, Any]] = []
        queue: List[Optional[str]] = [None]
        visited: set = set()
        bfs_started = time.time()
        max_bfs_sec = 30.0  # Hard cap on catalogue traversal time
        walk_complete = True  # any error, 429 or timeout makes the result partial

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
                    walk_complete = False
                    if response.status_code == 429:
                        break  # backing off: stop the walk rather than keep asking
                    continue

                data = response.json() or {}
                node_markets = data.get('markets', [])
                if node_markets:
                    markets.extend(node_markets)

                for node in data.get('nodes', []):
                    nid = node.get('id') or node.get('nodeId') or node.get('identifier') or node.get('name')
                    if not nid:
                        continue
                    # Only mark a node visited when we actually fetch it. Marking
                    # it when it is queued would skip every child (the root is
                    # the only node not pre-added).
                    if nid in visited or nid in queue:
                        continue
                    queue.append(nid)
            except Exception as e:
                logger.error(f"Capital.com navigation error at node {node_id}: {e}")
                walk_complete = False
                continue
        if queue:
            walk_complete = False  # stopped by the time cap

        if not walk_complete or not markets:
            # Only a fully completed, non-empty walk is cached or saved; a
            # partial or empty one never replaces a good cache or the disk file.
            logger.warning(
                "Capital.com market catalogue walk incomplete or empty (%d markets); not caching",
                len(markets),
            )
            self._market_walk_retry_at = time.time() + 60.0
            if self.market_cache:
                self.market_catalogue_complete = True  # last full walk, unchanged
                return self.market_cache
            # No full catalogue to fall back on: hand back what we got, but
            # flagged so callers do not treat it as the full market list.
            self.market_catalogue_complete = False
            logger.warning(
                "Capital.com market catalogue is PARTIAL (%d markets, no cache); "
                "market_catalogue_complete=False",
                len(markets),
            )
            return markets

        self.market_cache = markets
        self.market_cache_time = time.time()
        self._update_market_index(markets)
        _SHARED_MARKET_CACHE["markets"] = list(markets)
        _SHARED_MARKET_CACHE["market_index"] = dict(self.market_index)
        _SHARED_MARKET_CACHE["market_cache_time"] = self.market_cache_time
        self.market_catalogue_complete = True
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


    @staticmethod
    def _is_dated_future(epic: Optional[str]) -> bool:
        """Dated futures/contracts carry month-year codes (e.g. EURUSDU2026)."""
        if not epic:
            return False
        import re
        return bool(re.search(r"[A-Z]\d{4}$", str(epic).upper()))

    @staticmethod
    def _market_score(m: Dict[str, Any], canonical: str) -> int:
        """Higher score = better match. Prefer exact, tradeable, non-dated."""
        score = 0
        epic = str(m.get('epic') or '').upper()
        name = str(m.get('instrumentName') or '').upper()
        if epic == canonical or name == canonical:
            score += 1000
        if canonical in epic or canonical in name:
            score += 100
        if str(m.get('marketStatus', '')).upper() == 'TRADEABLE':
            score += 50
        if not CapitalClient._is_dated_future(m.get('epic')):
            score += 200
        if str(m.get('expiry', '')).upper() in ('', 'NONE', 'NA', 'N/A'):
            score += 25
        return score

    def _resolve_market(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Map a user-facing symbol (e.g., BTCUSD, TSLA) to the corresponding Capital.com market entry.
        Falls back to the search endpoint if the market isn't in cache yet.
        Prefers tradeable, non-dated (spot/rolling) instruments over futures.
        """
        if not symbol:
            return None

        canonical = self._canonicalize(symbol)
        markets = self.get_all_markets()

        # Exact canonical lookup first
        if canonical in self.market_index:
            candidate = self.market_index[canonical]
            if not self._is_dated_future(candidate.get('epic')):
                return candidate

        # Score and pick best cached match
        scored = [(self._market_score(m, canonical), m) for m in markets
                  if canonical in self._canonicalize(m.get('epic', ''))
                  or canonical in self._canonicalize(m.get('instrumentName', ''))]
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            return scored[0][1]

        # Fallback: use search endpoint to pull the market and refresh cache
        try:
            search_resp = self._request('GET', '/markets', params={'searchTerm': symbol, 'pageSize': 50})
            if search_resp.status_code == 200:
                data = search_resp.json() or {}
                found = data.get('markets', [])
                if found:
                    scored = [(self._market_score(m, canonical), m) for m in found
                              if canonical in self._canonicalize(m.get('epic', ''))
                              or canonical in self._canonicalize(m.get('instrumentName', ''))]
                    if scored:
                        scored.sort(key=lambda x: x[0], reverse=True)
                        best = scored[0][1]
                    else:
                        best = found[0]
                    markets.extend(found)
                    self._update_market_index(markets)
                    self.market_cache = markets
                    self.market_cache_time = time.time()
                    return best
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
                self._snapshot_cache[epic] = result
                self._snapshot_cache_times[epic] = time.time()
                return result
            if response.status_code == 429 or 'too-many.requests' in (response.text or '').lower():
                stale_age = now - self._snapshot_cache_times.get(epic, 0.0)
                if cached_snap is not None and stale_age <= CAPITAL_MAX_STALE_SNAPSHOT_AGE_S:
                    logger.warning(f"Capital.com rate-limited for {epic}; returning cached snapshot (age={stale_age:.0f}s)")
                    return cached_snap
                logger.error(f"Capital.com rate-limited for {epic}; cached snapshot too old (age={stale_age:.0f}s) — refusing stale data")
                return None
            logger.error(f"Capital.com market snapshot failed for {epic}: {response.text}")
        except Exception as e:
            logger.error(f"Capital.com market snapshot error for {epic}: {e}")
        if cached_snap is not None:
            stale_age = now - self._snapshot_cache_times.get(epic, 0.0)
            if stale_age <= CAPITAL_MAX_STALE_SNAPSHOT_AGE_S:
                logger.warning(f"Capital.com snapshot error for {epic}; returning cached snapshot (age={stale_age:.0f}s)")
                return cached_snap
            logger.error(f"Capital.com snapshot error for {epic}; cached snapshot too old (age={stale_age:.0f}s) — refusing stale data")
        return None

    def _read_monitor_cache(self) -> Dict[str, Any]:
        path = CAPITAL_MONITOR_CACHE_PATH
        if not path or not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return {}
        generated_at = float(payload.get("generated_at", 0.0) or 0.0)
        if generated_at <= 0 or (time.time() - generated_at) > CAPITAL_MONITOR_CACHE_MAX_AGE_S:
            return {}
        return payload

    def _get_cached_monitor_quote(self, symbol: str) -> Dict[str, float]:
        payload = self._read_monitor_cache()
        prices = payload.get("prices", {}) if isinstance(payload.get("prices"), dict) else {}
        quote = prices.get(str(symbol or "").upper(), {})
        if not isinstance(quote, dict):
            return {}
        return {
            "price": float(quote.get("price", 0.0) or 0.0),
            "bid": float(quote.get("bid", 0.0) or 0.0),
            "ask": float(quote.get("ask", 0.0) or 0.0),
            "epic": str(quote.get("epic") or ""),
            "change_pct": float(quote.get("change_pct", 0.0) or 0.0),
        }

    def get_account_balance(self) -> float:
        """Get primary account balance as a single float.

        Returns the 'available' balance of the preferred (primary) account.
        This is what the radar/honey ladder expects.
        """
        if not self.enabled:
            return 0.0

        try:
            response = self._request('GET', '/accounts')
            if response.status_code == 200:
                data = response.json()
                if 'accounts' in data:
                    # Find preferred account, or first non-zero account
                    for acc in data['accounts']:
                        if acc.get('preferred', False):
                            return float(acc.get('balance', {}).get('available', 0.0))
                    # Fallback: first account with non-zero balance
                    for acc in data['accounts']:
                        bal = float(acc.get('balance', {}).get('available', 0.0))
                        if bal > 0:
                            return bal
                    # Ultimate fallback: first account
                    return float(data['accounts'][0].get('balance', {}).get('available', 0.0))
                return 0.0
            else:
                logger.error(f"Failed to get Capital.com balances: {response.text}")
                return 0.0
        except Exception as e:
            logger.error(f"Error fetching Capital.com balances: {e}")
            return 0.0

    def get_account_balances(self) -> Dict[str, float]:
        """Get all account balances as currency-denominated dict."""

    def get_accounts(self, *, cache_ttl: float = 60.0) -> List[Dict[str, Any]]:
        """Get account information including available balance.
        Returns list of accounts with structure: [{'accountId': str, 'available': float, 'balance': float}]
        Results are cached for cache_ttl seconds (default 60s) to avoid serial HTTP calls during preflight.
        """
        if not self.enabled:
            return []

        now = time.time()
        if self._accounts_cache and (now - self._accounts_cache_time) < cache_ttl:
            return self._accounts_cache

        try:
            response = self._request('GET', '/accounts')
            if response.status_code == 200:
                data = response.json()
                accounts = []
                for acc in data.get('accounts', []):
                    balance_data = acc.get('balance', {})
                    accounts.append({
                        'accountId': acc.get('accountId', ''),
                        'balance': float(balance_data.get('balance', 0.0)),
                        'available': float(balance_data.get('available', balance_data.get('balance', 0.0))),
                        'currency': os.getenv('CAPITAL_ACCOUNT_CURRENCY', 'GBP').upper()
                    })
                self._accounts_cache = accounts
                self._accounts_cache_time = now
                return accounts
            else:
                logger.error(f"Failed to get Capital.com accounts: {response.text}")
        except Exception as e:
            logger.error(f"Error fetching Capital.com accounts: {e}")
        if self._accounts_cache:
            stale_age = now - self._accounts_cache_time
            if stale_age <= CAPITAL_MAX_STALE_SNAPSHOT_AGE_S:
                logger.warning(f"Capital.com accounts unavailable; returning cached accounts (age={stale_age:.0f}s)")
                return self._accounts_cache
            logger.error(f"Capital.com accounts unavailable; cached accounts too old (age={stale_age:.0f}s) — refusing stale data")
        return []

    def get_ticker(self, symbol: str) -> Dict[str, float]:
        """Get current price for a symbol."""
        if not self.enabled:
            cached = self._get_cached_monitor_quote(symbol)
            if cached:
                return cached
            return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

        # 🔥 Skip crypto symbols - Capital.com doesn't have them
        CRYPTO_PATTERNS = ('USDT', 'USDC', 'BTC', 'ETH', 'XBT', 'SOL', 'ADA', 'XRP',
                           'DOGE', 'SHIB', 'AVAX', 'DOT', 'LINK', 'MATIC', 'UNI')
        if any(p in symbol.upper() for p in CRYPTO_PATTERNS):
            return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

        cached = self._get_cached_monitor_quote(symbol)
        if cached and float(cached.get("price", 0.0) or 0.0) > 0:
            return cached

        try:
            market = self._resolve_market(symbol) or {}
            epic = market.get('epic') or symbol
            snapshot = self._get_market_snapshot(epic) or {}
            snap = snapshot.get('snapshot', {})

            bid = float(snap.get('bid') or market.get('bid') or market.get('snapshot', {}).get('bid') or 0)
            ask = float(snap.get('offer') or market.get('offer') or market.get('snapshot', {}).get('offer') or 0)
            price = (bid + ask) / 2 if bid and ask else (bid or ask or float(snap.get('midOpen', 0) or 0))

            change_pct = float(snap.get('percentageChange', 0) or 0)
            high = float(snap.get('high') or snap.get('dayHigh') or 0)
            low  = float(snap.get('low')  or snap.get('dayLow')  or 0)
            return {
                'price': price,
                'bid': bid,
                'ask': ask,
                'epic': epic,
                'change_pct': change_pct,
                'high': high,
                'low': low,
            }
        except Exception as e:
            logger.error(f"Error fetching Capital.com ticker for {symbol}: {e}")
            return {'price': 0.0, 'bid': 0.0, 'ask': 0.0}

    def get_tickers_for_symbols(self, symbols: List[str], *, max_workers: int = CAPITAL_TICKER_WORKERS) -> Dict[str, Dict[str, float]]:
        """Fetch tickers for many symbols concurrently (best-effort).

        Returns: {symbol: {price,bid,ask,epic,change_pct}}
        """
        if not self.enabled:
            return {}
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

        results: Dict[str, Dict[str, float]] = {}
        uncached_symbols: List[str] = []
        now = time.time()
        for sym in unique_symbols:
            # 1. Check disk-based monitor cache (written by background monitor process)
            cached = self._get_cached_monitor_quote(sym)
            if cached and float(cached.get("price", 0.0) or 0.0) > 0:
                results[sym] = cached
                continue
            # 2. Check in-memory per-symbol cache (populated by previous batch fetches)
            mem_age = now - self._ticker_mem_cache_times.get(sym, 0.0)
            if mem_age < CAPITAL_TICKER_MEM_TTL:
                mem_hit = self._ticker_mem_cache.get(sym, {})
                if mem_hit and float(mem_hit.get("price", 0.0) or 0.0) > 0:
                    results[sym] = mem_hit
                    continue
            uncached_symbols.append(sym)

        if not uncached_symbols:
            return results
        max_workers = max(1, int(max_workers))

        # Pre-warm market catalogue once serially — prevents N concurrent
        # get_all_markets() calls each downloading 6799 markets → 429 ban.
        self.get_all_markets()

        def _fetch(sym: str) -> Dict[str, float]:
            return self.get_ticker(sym)

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            future_map = {ex.submit(_fetch, sym): sym for sym in uncached_symbols}
            for fut in as_completed(future_map):
                sym = future_map[fut]
                try:
                    result = fut.result() or {'price': 0.0, 'bid': 0.0, 'ask': 0.0}
                except Exception:
                    result = {'price': 0.0, 'bid': 0.0, 'ask': 0.0}
                results[sym] = result
                # Populate in-memory cache for subsequent ticks
                if float(result.get("price", 0.0) or 0.0) > 0:
                    self._ticker_mem_cache[sym] = result
                    self._ticker_mem_cache_times[sym] = time.time()

        return results

    def get_24h_tickers(self) -> List[Dict[str, Any]]:
        """
        Get top markets or a watchlist.
        Capital.com doesn't have a simple 'all tickers' endpoint that is lightweight.
        We'll fetch a top list or specific categories if possible.
        For now, let's fetch top crypto and tech stocks if we can, or just return empty if too complex.
        Actually, let's try to fetch 'crypto' category.
        """
        if not self.enabled:
            return []

        max_snapshots = int(os.getenv('CAPITAL_MAX_TICKER_SNAPSHOTS', '400'))
        tickers: List[Dict[str, Any]] = []
        markets = self.get_all_markets()

        try:
            for idx, m in enumerate(markets):
                epic = m.get('epic')
                if not epic:
                    continue

                bid = ask = price = change_pct = 0.0
                if idx < max_snapshots:
                    snap = self._get_market_snapshot(epic) or {}
                    snapshot = snap.get('snapshot', {})
                    bid = float(snapshot.get('bid', 0) or 0)
                    ask = float(snapshot.get('offer', 0) or 0)
                    price = (bid + ask) / 2 if bid and ask else float(snapshot.get('midOpen', 0) or 0)
                    change_pct = float(snapshot.get('percentageChange', 0) or 0)

                tickers.append({
                    # Keep 'symbol' as epic for backward-compat with existing code.
                    'symbol': epic,
                    'epic': epic,
                    # Where available, 'ticker' is the underlying instrument symbol (e.g., AAPL).
                    'ticker': m.get('symbol') or '',
                    'instrumentName': m.get('instrumentName'),
                    'price': price,
                    'bid': bid,
                    'ask': ask,
                    'priceChangePercent': change_pct,
                    'volume': 0.0,
                    'source': 'capital'
                })
        except Exception as e:
            logger.error(f"Error fetching Capital.com tickers: {e}")

        return tickers

    def get_stock_snapshot_watchlist(self, symbols: List[str], *, max_workers: int = 8) -> List[Dict[str, Any]]:
        """Convenience: returns a ticker-like list for a list of stock symbols."""
        tmap = self.get_tickers_for_symbols(symbols, max_workers=max_workers)
        out: List[Dict[str, Any]] = []
        for sym, t in tmap.items():
            out.append({
                'symbol': t.get('epic', sym),
                'epic': t.get('epic', sym),
                'ticker': sym,
                'instrumentName': '',
                'price': float(t.get('price', 0) or 0),
                'bid': float(t.get('bid', 0) or 0),
                'ask': float(t.get('ask', 0) or 0),
                'priceChangePercent': float(t.get('change_pct', 0) or 0),
                'volume': 0.0,
                'source': 'capital'
            })
        return out

    @staticmethod
    def _add_optional_order_controls(payload: Dict[str, Any], **controls: Any) -> None:
        """Attach Capital order controls without emitting empty fields."""
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
            payload[target] = value

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
        """Place a market order."""
        if not self.enabled:
            return {'error': 'Client disabled'}

        # 🔥 CRYPTO GUARD: Capital.com does NOT support direct crypto trading!
        # Only CFDs (forex, indices, commodities, stocks) are supported
        CRYPTO_PATTERNS = ('USDT', 'USDC', 'BTC', 'ETH', 'XBT', 'SOL', 'ADA', 'XRP',
                           'DOGE', 'SHIB', 'AVAX', 'DOT', 'LINK', 'MATIC', 'UNI',
                           'ATOM', 'LTC', 'BCH', 'ETC', 'XLM', 'ALGO', 'FIL', 'VET')
        symbol_upper = symbol.upper()
        if any(pattern in symbol_upper for pattern in CRYPTO_PATTERNS):
            logger.warning(f"Capital.com BLOCKED crypto order for {symbol} - use Binance/Kraken instead")
            return {'error': 'Crypto not supported on Capital.com', 'rejected': True, 'reason': 'CRYPTO_NOT_SUPPORTED'}

        if self.dry_run:
            logger.info(f"[DRY RUN] Capital.com {side} {quantity} {symbol}")
            return {'id': 'dry_run_id', 'status': 'filled'}

        path = '/positions'
        direction = "BUY" if side.upper() == "BUY" else "SELL"

        market = self._resolve_market(symbol) or {}
        epic = market.get('epic') or symbol

        payload = {
            "epic": epic,
            "direction": direction,
            "size": quantity,
            "orderType": "MARKET",
            "guaranteedStop": False,
            "forceOpen": True,
            "currencyCode": os.getenv('CAPITAL_ACCOUNT_CURRENCY', 'GBP').upper()
        }
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

        try:
            response = self._request('POST', path, json_body=payload)
            if response.status_code == 200:
                data = response.json() if isinstance(response.json(), dict) else {}
                deal_reference = data.get('dealReference')
                # Confirm the order via positions polling so callers always get
                # a stable dealId. This fixes the "dealId not found in positions"
                # race where /confirms is queried before the position propagates.
                if deal_reference:
                    confirmation = self.confirm_order_by_positions(deal_reference)
                    return {
                        'submitted': True,
                        'dealReference': deal_reference,
                        'dealId': confirmation.get('dealId'),
                        'confirmed': confirmation.get('confirmed', False),
                        'status': confirmation.get('status', data.get('status', 'UNKNOWN')),
                        'epic': epic,
                        'direction': direction,
                        'size': quantity,
                        'confirmation': confirmation,
                        'raw': data,
                    }
                return {
                    'submitted': True,
                    'dealReference': deal_reference,
                    'dealId': data.get('dealId'),
                    'confirmed': bool(data.get('dealId')),
                    'status': data.get('status', 'UNKNOWN'),
                    'epic': epic,
                    'direction': direction,
                    'size': quantity,
                    'raw': data,
                }
            else:
                logger.error(f"Capital.com order failed: {response.text}")
                return {
                    'submitted': False,
                    'rejected': True,
                    'error': 'http_error',
                    'status_code': response.status_code,
                    'reason': response.text,
                    'symbol': symbol,
                    'side': side,
                    'quantity': quantity,
                }
        except Exception as e:
            logger.error(f"Capital.com order error: {e}")
            return {
                'submitted': False,
                'rejected': True,
                'error': 'exception',
                'reason': str(e),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
            }

    def get_working_orders(self) -> List[Dict[str, Any]]:
        """Return pending Capital.com working orders."""
        if not self.enabled:
            return []
        try:
            response = self._request('GET', '/workingorders')
            if response.status_code == 200:
                data = response.json() or {}
                return data.get('workingOrders', data.get('orders', [])) or []
            logger.warning(f"Capital.com working orders fetch failed ({response.status_code}): {response.text[:200]}")
            return []
        except Exception as e:
            logger.error(f"Capital.com working orders error: {e}")
            return []

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
            return {'error': 'Client disabled'}
        direction = "BUY" if str(side).upper() == "BUY" else "SELL"
        market = self._resolve_market(symbol) or {}
        epic = market.get('epic') or symbol
        payload: Dict[str, Any] = {
            "epic": epic,
            "direction": direction,
            "size": quantity,
            "level": level,
            "type": str(order_type or "LIMIT").upper(),
            "guaranteedStop": False,
        }
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
        try:
            response = self._request('POST', '/workingorders', json_body=payload)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    data.setdefault("submitted_payload", payload)
                return data
            logger.error(f"Capital.com working order failed: {response.text}")
            return {
                'rejected': True,
                'error': 'http_error',
                'status_code': response.status_code,
                'reason': response.text,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'level': level,
            }
        except Exception as e:
            logger.error(f"Capital.com working order error: {e}")
            return {
                'rejected': True,
                'error': 'exception',
                'reason': str(e),
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'level': level,
            }

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
        try:
            response = self._request('PUT', f'/positions/{deal_id}', json_body=payload)
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    data.setdefault("submitted_payload", payload)
                return {'success': True, 'deal_id': deal_id, 'data': data}
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
                try:
                    data = response.json()
                except Exception:
                    data = {}
                return {'success': True, 'deal_id': deal_id, 'data': data}
            logger.warning(f"Capital.com delete_working_order failed ({response.status_code}): {response.text[:200]}")
            return {'success': False, 'deal_id': deal_id, 'status_code': response.status_code, 'error': response.text[:200]}
        except Exception as e:
            logger.error(f"Capital.com delete_working_order exception: {e}")
            return {'success': False, 'deal_id': deal_id, 'error': str(e)}

    def confirm_order(self, deal_reference: str) -> Dict[str, Any]:
        """Fetch confirmation for a previously submitted deal reference."""
        if not self.enabled:
            return {'error': 'Client disabled'}

        if not deal_reference:
            return {'error': 'Missing deal reference'}

        try:
            response = self._request('GET', f'/confirms/{deal_reference}')
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Capital.com confirm failed: {response.text}")
                return {'error': response.text, 'status_code': response.status_code}
        except Exception as e:
            logger.error(f"Capital.com confirm error: {e}")
            return {'error': str(e)}

    def confirm_order_by_positions(
        self,
        deal_reference: str,
        max_attempts: int = 6,
        delay_sec: float = 2.0,
    ) -> Dict[str, Any]:
        """Confirm an order by polling the positions endpoint.

        Capital.com's `/confirms/{dealReference}` endpoint can return
        ORDER_FAILED / "dealId not found" immediately after submission because
        the position takes a moment to propagate. This method refreshes the
        session, tries `/confirms`, and falls back to polling `/positions`
        until the matching dealReference appears or the timeout is reached.
        """
        if not self.enabled:
            return {'confirmed': False, 'error': 'Client disabled'}
        if not deal_reference:
            return {'confirmed': False, 'error': 'Missing deal reference'}

        # Ensure session is fresh before we start polling
        self.authenticate()

        # First try the confirms endpoint
        confirm = self.confirm_order(deal_reference)
        if isinstance(confirm, dict) and confirm.get('dealId'):
            return {
                'confirmed': True,
                'dealReference': deal_reference,
                'dealId': confirm['dealId'],
                'status': confirm.get('status', 'UNKNOWN'),
                'source': 'confirms',
                'data': confirm,
            }

        # Fall back to polling /positions for the newly-opened position
        for attempt in range(1, max_attempts + 1):
            try:
                positions = self.get_positions()
                for pos in positions:
                    pos_meta = pos.get('position', {})
                    if pos_meta.get('dealReference') == deal_reference:
                        return {
                            'confirmed': True,
                            'dealReference': deal_reference,
                            'dealId': pos_meta.get('dealId'),
                            'status': pos_meta.get('status', 'OPEN'),
                            'source': 'positions_poll',
                            'attempt': attempt,
                            'data': pos,
                        }
                    # Some responses nest dealReference under the top-level position
                    if pos.get('dealReference') == deal_reference:
                        return {
                            'confirmed': True,
                            'dealReference': deal_reference,
                            'dealId': pos.get('dealId') or pos_meta.get('dealId'),
                            'status': pos_meta.get('status', 'OPEN'),
                            'source': 'positions_poll',
                            'attempt': attempt,
                            'data': pos,
                        }
            except Exception as e:
                logger.warning(f"Capital.com positions poll attempt {attempt} error: {e}")

            if attempt < max_attempts:
                time.sleep(delay_sec)

        return {
            'confirmed': False,
            'dealReference': deal_reference,
            'error': 'dealId not found in Capital.com positions after polling',
            'confirms_response': confirm if isinstance(confirm, dict) else {'error': str(confirm)},
            'attempts': max_attempts,
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions."""
        if not self.enabled:
            return []

        try:
            response = self._request('GET', '/positions')
            if response.status_code == 200:
                data = response.json()
                return data.get('positions', [])
            return []
        except Exception as e:
            logger.error(f"Capital.com positions error: {e}")
            return []

    def close_position(self, deal_id: str) -> Dict[str, Any]:
        """
        Close an open CFD position by deal ID.

        Capital.com REST: DELETE /positions/{dealId}
        Falls back gracefully if the deal_id is unknown or already closed.
        Returns a dict with 'success' boolean and raw response data.
        """
        if not self.enabled:
            return {'success': False, 'error': 'client_disabled'}
        if not deal_id:
            return {'success': False, 'error': 'missing_deal_id'}

        try:
            resp = self._request('DELETE', f'/positions/{deal_id}')
            if resp.status_code in (200, 204):
                try:
                    data = resp.json()
                except Exception:
                    data = {}
                return {'success': True, 'deal_id': deal_id, 'data': data}
            else:
                logger.warning(f"Capital.com close_position failed ({resp.status_code}): {resp.text[:200]}")
                return {'success': False, 'deal_id': deal_id, 'status_code': resp.status_code, 'error': resp.text[:200]}
        except Exception as e:
            logger.error(f"Capital.com close_position exception: {e}")
            return {'success': False, 'deal_id': deal_id, 'error': str(e)}

    def get_order_history(self, from_date: str = None) -> List[Dict[str, Any]]:
        """Get order/deal history.

        Note: Capital's `/history/activity` endpoint expects a *datetime* `from`
        (e.g. `YYYY-MM-DDTHH:MM:SS`) and supports `detailed=true` for size/side/level.
        """
        if not self.enabled:
            return []

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
                data = response.json()
                return data.get('activities', [])
            return []
        except Exception as e:
            logger.error(f"Capital.com history error: {e}")
            return []

    def compute_trade_fees(self, position: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate fees for a Capital.com position/trade.

        Capital.com Fee Structure (CFD/Spread Betting):
        - Spread cost: Built into bid/ask (varies by instrument, typically 0.1-0.5%)
        - Overnight financing: ~2.5% annually (charged daily on leveraged positions)
        - No commission on most instruments

        Returns dict with:
        - spread_cost: Estimated spread cost in account currency
        - overnight_cost: Accumulated overnight financing
        - total_fees: Total fees
        - fee_pct: Approximate fee as percentage of notional
        """
        size = float(position.get('position', {}).get('size', 0) or 0)
        level = float(position.get('position', {}).get('level', 0) or 0)  # Entry price
        notional = size * level

        # Get current market to estimate spread
        epic = position.get('market', {}).get('epic', '')
        market = position.get('market', {})
        bid = float(market.get('bid', 0) or 0)
        offer = float(market.get('offer', 0) or 0)

        # Calculate spread percentage
        if bid > 0 and offer > 0:
            spread_pct = (offer - bid) / ((offer + bid) / 2)
        else:
            spread_pct = 0.001  # Default 0.1%

        # Spread cost (paid on entry)
        spread_cost = notional * spread_pct

        # Overnight financing (calculate based on creation date if available)
        overnight_cost = 0.0
        # Note: Would need to track days held for accurate overnight cost
        # For now, estimate based on typical overnight rates

        total_fees = spread_cost + overnight_cost
        fee_pct = (total_fees / notional) if notional > 0 else 0

        return {
            'spread_cost': spread_cost,
            'spread_pct': spread_pct,
            'overnight_cost': overnight_cost,
            'total_fees': total_fees,
            'fee_pct': fee_pct,
            'notional': notional,
            'epic': epic
        }

    def get_positions_with_fees(self) -> List[Dict[str, Any]]:
        """Get all positions with computed fee metrics."""
        positions = self.get_positions()
        for pos in positions:
            fees = self.compute_trade_fees(pos)
            pos['computed_fees'] = fees
        return positions

    def compute_order_fees_in_quote(self, position: Dict[str, Any], primary_quote: str = "USD") -> float:
        """
        Calculate total fees for a position/trade in the quote currency.
        This provides a consistent interface with Binance/Kraken clients.

        Returns: Total fee in quote currency
        """
        fees = self.compute_trade_fees(position)
        return fees['total_fees']

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

        if not history:
            return {
                "symbol": symbol,
                "total_quantity": 0.0,
                "total_cost": 0.0,
                "avg_cost": 0.0,
                "trades": 0
            }

        total_qty = 0.0
        buy_qty = 0.0
        buy_cost = 0.0
        trade_count = 0

        for activity in history:
            # Capital.com activity structure varies by type
            epic = activity.get('epic', '') or activity.get('details', {}).get('epic', '')
            if epic.upper() != symbol.upper():
                continue

            activity_type = activity.get('type', '')

            # Look for deal confirmed activities
            if 'deal' in activity_type.lower() or 'position' in activity_type.lower():
                size = float(activity.get('details', {}).get('size', 0) or 0)
                level = float(activity.get('details', {}).get('level', 0) or 0)
                direction = activity.get('details', {}).get('direction', '')

                if size <= 0 or level <= 0:
                    continue

                trade_count += 1

                if direction.upper() == 'BUY':
                    total_qty += size
                    buy_qty += size
                    buy_cost += size * level
                elif direction.upper() == 'SELL':
                    total_qty -= size

        avg_cost = buy_cost / buy_qty if buy_qty > 0 else 0.0

        return {
            "symbol": symbol,
            "total_quantity": total_qty,
            "total_cost": buy_cost,
            "avg_cost": avg_cost,
            "trades": trade_count
        }
