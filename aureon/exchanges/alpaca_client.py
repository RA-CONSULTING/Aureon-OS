import logging
import math
import os
import re
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import requests

from aureon.governance.economic_boundary import (
    EconomicGovernanceBlocked,
    _claim_economic_transport_context,
    _economic_transport_body_digest,
)

# Windows UTF-8 fix (MANDATORY - must be early)
if sys.platform == 'win32' and sys.stdout is sys.__stdout__ and sys.stdout.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        force_stdio_wrap = os.getenv("ALPACA_FORCE_UTF8_STDIO", "false").lower() == "true"
        if force_stdio_wrap and _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if force_stdio_wrap and _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

# Load environment variables from .env file
#
# NOTE:
# This project is often run from different working directories (or via stdin).
# `python-dotenv`'s default `find_dotenv()` can fail or miss the repo root.
# We therefore try a few explicit candidate paths before falling back.
try:
    from dotenv import load_dotenv

    dotenv_candidates = []
    explicit = os.getenv("DOTENV_PATH")
    if explicit:
        dotenv_candidates.append(Path(explicit))

    dotenv_candidates.append(Path.cwd() / ".env")
    dotenv_candidates.append(Path(__file__).resolve().parent / ".env")

    loaded = False
    for candidate in dotenv_candidates:
        try:
            if candidate.exists():
                load_dotenv(dotenv_path=str(candidate), override=False)
                loaded = True
                break
        except Exception:
            continue

    if not loaded:
        load_dotenv(override=False)
except ImportError:
    pass

try:
    from aureon.core.aureon_env import load_aureon_environment

    load_aureon_environment(Path(__file__).resolve().parents[2], override=False)
except Exception:
    pass

logger = logging.getLogger(__name__)

ALPACA_LIVE_BASE = "https://api.alpaca.markets"
ALPACA_PAPER_BASE = "https://paper-api.alpaca.markets"
_ALPACA_MUTATION_SEGMENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


def _is_alpaca_economic_mutation_path(method: str, endpoint: str) -> bool:
    """Return whether an exact Alpaca trading route mutates economic state."""

    normalized_method = str(method).strip().upper()
    if not isinstance(endpoint, str) or not endpoint.startswith("/"):
        return False
    if "?" in endpoint or "#" in endpoint or "//" in endpoint:
        return False
    if endpoint == "/v2/orders":
        return normalized_method in {"POST", "DELETE"}
    if endpoint == "/v2/positions":
        return normalized_method == "DELETE"
    parts = endpoint.split("/")
    if (
        len(parts) == 4
        and parts[:3] == ["", "v2", "orders"]
        and normalized_method in {"DELETE", "PATCH"}
        and _ALPACA_MUTATION_SEGMENT_RE.fullmatch(parts[3]) is not None
        and parts[3] not in {".", ".."}
    ):
        return True
    return bool(
        len(parts) == 4
        and parts[:3] == ["", "v2", "positions"]
        and normalized_method == "DELETE"
        and _ALPACA_MUTATION_SEGMENT_RE.fullmatch(parts[3]) is not None
        and parts[3] not in {".", ".."}
    )


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default

# ═══════════════════════════════════════════════════════════════════════════════════════════════════
# CRYPTO SYMBOL DETECTION - Centralized set to prevent stock API fallback for crypto
# ═══════════════════════════════════════════════════════════════════════════════════════════════════
CRYPTO_BASE_SYMBOLS = {
    'BTC', 'ETH', 'LTC', 'XRP', 'SOL', 'DOGE', 'AVAX', 'DOT', 'LINK', 'UNI',
    'AAVE', 'BCH', 'XLM', 'ATOM', 'ALGO', 'MATIC', 'SHIB', 'PEPE', 'TRUMP',
    'ADA', 'BNB', 'XMR', 'ETC', 'FIL', 'NEAR', 'APT', 'OP', 'ARB', 'CRV',
    'MKR', 'SNX', 'COMP', 'YFI', 'SUSHI', 'GRT', 'BAT', 'ZRX', 'ENJ', 'MANA',
    'SAND', 'AXS', 'GALA', 'IMX', 'LRC', 'SKY', 'XTZ', 'USDG', 'BONK', 'WIF',
    'FLOKI', 'RENDER', 'INJ', 'TIA', 'SEI', 'SUI', 'BLUR', 'JTO', 'PYTH',
    'RNDR', 'FET', 'AGIX', 'OCEAN', 'TAO', 'ORDI', 'WLD', 'STRK', 'MEME',
    'USDC', 'USDT', 'DAI', 'BUSD',  # Stablecoins (quote currencies)
}

class AlpacaClient:
    """
    Client for Alpaca Markets API (Stocks & Crypto).
    """
    def __init__(self):
        self.api_key = os.getenv('ALPACA_API_KEY')
        self.secret_key = (
            os.getenv('ALPACA_SECRET_KEY')
            or os.getenv('ALPACA_API_SECRET')
            or os.getenv('ALPACA_SECRET')
        )
        # Default to LIVE trading
        self.use_paper = os.getenv('ALPACA_PAPER', 'false').lower() == 'true'
        self.dry_run = os.getenv('ALPACA_DRY_RUN', 'false').lower() == 'true'
        
        self.timeout_seconds = 10.0
        try:
            self.timeout_seconds = float(os.getenv("ALPACA_TIMEOUT", "10") or 10)
        except (TypeError, ValueError):
            self.timeout_seconds = 10.0
        self.auth_probe_timeout_seconds = max(3.0, _env_float("ALPACA_AUTH_TIMEOUT", min(self.timeout_seconds, 8.0)))
        self.quote_max_age_seconds = max(1.0, _env_float("ALPACA_QUOTE_MAX_AGE_SECONDS", 120.0))
        self.order_receipt_max_age_seconds = max(
            1.0,
            _env_float("ALPACA_ORDER_RECEIPT_MAX_AGE_SECONDS", 300.0),
        )
        self.provider_future_skew_seconds = max(
            0.0,
            _env_float("ALPACA_PROVIDER_FUTURE_SKEW_SECONDS", 30.0),
        )
        self.max_retries = 3  # 🛡️ Increased for rate limit retries
        try:
            self.max_retries = max(0, int(os.getenv("ALPACA_RETRY_COUNT", "3") or 3))
        except (TypeError, ValueError):
            self.max_retries = 3

        if self.use_paper:
            self.base_url = ALPACA_PAPER_BASE
        else:
            self.base_url = ALPACA_LIVE_BASE
            
        # Data API URL (Crypto)
        self.data_url = "https://data.alpaca.markets"
        
        self.session = requests.Session()
        self.last_error: Optional[Dict[str, Any]] = None
        self.init_error: str = ""
        self.auth_probe_warning = ""
        self.auth_verified = False
        self._auth_probe_thread: Optional[threading.Thread] = None
        self._auth_probe_lock = threading.Lock()
        self._closed = False
        self._telemetry_owner = f"alpaca-client:{id(self)}"
        self._telemetry_started = False
        self._economic_dispatch_lock = threading.RLock()
        self._economic_dispatches: Dict[object, tuple[str, str, str]] = {}

        # Rate limiting and in-memory TTL caching for market data
        try:
            try:
                from aureon.core.rate_limiter_v2 import AdaptiveRateLimiter  # type: ignore
            except ImportError:
                from aureon.core.rate_limiter_v2 import AdaptiveRateLimiter  # type: ignore
        except ImportError:
            try:
                try:
                    from aureon.core.rate_limiter import TokenBucket  # type: ignore
                except ImportError:
                    from aureon.core.rate_limiter import TokenBucket  # type: ignore
            except ImportError:
                TokenBucket = None  # type: ignore

            class AdaptiveRateLimiter:  # type: ignore[no-redef]
                def __init__(self, trading_rate: float, data_rate: float, trading_capacity: float, data_capacity: float, name: str = "alpaca"):
                    self._trading = TokenBucket(rate=trading_rate, capacity=trading_capacity) if TokenBucket else None
                    self._data = TokenBucket(rate=data_rate, capacity=data_capacity) if TokenBucket else None
                    self.name = name

                def wait_trading(self) -> None:
                    if self._trading:
                        self._trading.wait()

                def wait_data(self) -> None:
                    if self._data:
                        self._data.wait()

                def on_429_error(self) -> None:
                    time.sleep(1.0)

        try:
            try:
                from aureon.core.rate_limiter import TTLCache  # type: ignore
            except ImportError:
                from aureon.core.rate_limiter import TTLCache  # type: ignore
        except ImportError:
            class TTLCache:  # type: ignore[no-redef]
                def __init__(self, default_ttl: float = 1.0, name: str = "cache"):
                    self.default_ttl = float(default_ttl)
                    self.name = name
                    self._store: Dict[str, Any] = {}
                    self._expires: Dict[str, float] = {}

                def get(self, key: str) -> Any:
                    expires = self._expires.get(key, 0.0)
                    if expires and expires >= time.time():
                        return self._store.get(key)
                    self._store.pop(key, None)
                    self._expires.pop(key, None)
                    return None

                def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
                    life = self.default_ttl if ttl is None else float(ttl)
                    self._store[key] = value
                    self._expires[key] = time.time() + max(0.0, life)
        
        # Production-safe rates: trading below Alpaca's 200/min limit (3.33/sec)
        try:
            trading_rate = float(os.getenv('ALPACA_TRADING_RATE_PER_SECOND', '2.5'))  # Conservative trading rate
            data_rate = float(os.getenv('ALPACA_DATA_RATE_PER_SECOND', '5.0'))       # Data rate for quotes/bars
        except Exception:
            trading_rate = 2.5
            data_rate = 5.0
            
        try:
            trading_burst = float(os.getenv('ALPACA_TRADING_BURST_CAPACITY', str(max(1, int(trading_rate)))))
            data_burst = float(os.getenv('ALPACA_DATA_BURST_CAPACITY', str(max(1, int(data_rate)))))
        except Exception:
            trading_burst = max(1, trading_rate)
            data_burst = max(1, data_rate)

        self._rate_limiter = AdaptiveRateLimiter(
            trading_rate=trading_rate,
            data_rate=data_rate,
            trading_capacity=trading_burst,
            data_capacity=data_burst,
            name='alpaca'
        )
        try:
            ttl = float(os.getenv('ALPACA_QUOTE_CACHE_TTL', '2.0'))
        except Exception:
            ttl = 2.0
        self._quote_cache = TTLCache(default_ttl=ttl, name='alpaca_quotes')

        # Position and account caches
        try:
            pos_ttl = float(os.getenv('ALPACA_POSITION_CACHE_TTL', '5.0'))
        except Exception:
            pos_ttl = 5.0
        self._position_cache = TTLCache(default_ttl=pos_ttl, name='alpaca_positions')

        try:
            acc_ttl = float(os.getenv('ALPACA_ACCOUNT_CACHE_TTL', '10.0'))
        except Exception:
            acc_ttl = 10.0
        self._account_cache = TTLCache(default_ttl=acc_ttl, name='alpaca_account')

        # Short-lived response deduplication cache (used to avoid duplicate GETs)
        try:
            dedup_ttl = float(os.getenv('ALPACA_DEDUP_TTL', '0.2'))
        except Exception:
            dedup_ttl = 0.2
        self._response_cache = TTLCache(default_ttl=dedup_ttl, name='alpaca_response_cache')

        # Market Data Hub integration (Phase 2 optimization)
        self._market_data_hub = None
        try:
            try:
                from aureon.data_feeds.market_data_hub import get_market_data_hub
            except ImportError:
                from aureon.data_feeds.market_data_hub import get_market_data_hub
            self._market_data_hub = get_market_data_hub(self)
        except ImportError:
            logger.debug("MarketDataHub not available - running without prefetching")

        # Global Rate Budget integration (Phase 2 optimization)
        self._global_rate_budget = None
        self._classify_request_type = None
        try:
            try:
                from aureon.core.global_rate_budget import get_global_rate_budget, classify_request_type
            except ImportError:
                from aureon.core.global_rate_budget import get_global_rate_budget, classify_request_type
            self._global_rate_budget = get_global_rate_budget()
            self._classify_request_type = classify_request_type
        except ImportError:
            logger.debug("GlobalRateBudget not available - running without priority budgeting")

        if self.api_key and self.secret_key:
            self.session.headers.update({
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.secret_key
            })
            self.is_authenticated = True
        else:
            logger.warning("Alpaca API keys not found in environment variables.")
            self.init_error = "credentials_missing"
            self.is_authenticated = False

    def _probe_initial_auth(self) -> None:
        """Probe auth once without disabling the client on transient network issues."""
        if self._closed:
            return
        try:
            test_url = f"{self.base_url}/v2/account"
            auth_resp = self.session.get(test_url, timeout=self.auth_probe_timeout_seconds)
            if self._closed:
                return
            if auth_resp.status_code in (401, 403):
                logger.warning(f"⚠️ Alpaca authentication failed ({auth_resp.status_code}). Disabling client.")
                self.init_error = f"auth_failed_{auth_resp.status_code}"
                self.is_authenticated = False
                self.auth_verified = False
                return
            if 200 <= auth_resp.status_code < 300:
                self.init_error = ""
                self.auth_probe_warning = ""
                self.auth_verified = True
            else:
                self.auth_probe_warning = f"http_status_{auth_resp.status_code}"
                self.auth_verified = False
        except Exception as e:
            error_text = str(e)
            if "WinError 10013" in error_text:
                logger.warning(f"⚠️ Alpaca initial auth check blocked by local socket policy: {e}")
                self.init_error = "socket_blocked"
                self.is_authenticated = False
                self.auth_verified = False
                return
            self.auth_probe_warning = error_text
            self.auth_verified = False
            logger.warning(
                "⚠️ Alpaca initial auth probe failed (%s). Keeping client enabled and retrying on demand.",
                e,
            )
            self.init_error = ""

    def start_auth_probe(self, *, background: bool = True) -> bool:
        """Explicitly validate configured credentials.

        Construction never performs network I/O. Dry-run and credential-free
        clients remain inert even when this method is called.
        """
        if self._closed:
            self.auth_probe_warning = "client_closed"
            return False
        if self.dry_run:
            self.auth_probe_warning = "dry_run"
            return False
        if not self.api_key or not self.secret_key:
            self.init_error = "credentials_missing"
            self.is_authenticated = False
            return False

        if not background:
            self._probe_initial_auth()
            return self.auth_verified

        with self._auth_probe_lock:
            if self._auth_probe_thread is not None and self._auth_probe_thread.is_alive():
                return True
            self._auth_probe_thread = threading.Thread(
                target=self._probe_initial_auth,
                daemon=True,
                name="alpaca-auth-probe",
            )
            self._auth_probe_thread.start()
        return True

    def start_telemetry(self) -> bool:
        """Explicitly start this runtime's configured Prometheus exporter."""
        if self._closed:
            return False
        raw_port = os.getenv("PROMETHEUS_METRICS_PORT")
        if not raw_port:
            return False
        try:
            port = int(raw_port)
            from aureon.monitors.telemetry_server import start_telemetry_server

            started = start_telemetry_server(
                port,
                owner=self._telemetry_owner,
            )
            self._telemetry_started = bool(started)
            return self._telemetry_started
        except (TypeError, ValueError) as exc:
            logger.warning("Invalid PROMETHEUS_METRICS_PORT %r: %s", raw_port, exc)
        except Exception as exc:
            logger.warning("Failed to start telemetry server: %s", exc)
        self._telemetry_started = False
        return False

    def stop_telemetry(self, timeout: float = 2.0) -> bool:
        """Release this client's telemetry ownership and join if it is last."""
        if not self._telemetry_started:
            return True
        try:
            from aureon.monitors.telemetry_server import stop_telemetry_server

            stopped = stop_telemetry_server(
                timeout=timeout,
                owner=self._telemetry_owner,
            )
        except Exception as exc:
            logger.warning("Failed to stop telemetry server: %s", exc)
            return False
        finally:
            self._telemetry_started = False
        return bool(stopped)

    def start(self) -> bool:
        """Start optional runtime services; construction remains inert."""
        telemetry_started = self.start_telemetry()
        auth_started = self.start_auth_probe(background=True)
        return bool(telemetry_started or auth_started)

    def close(self, timeout: float = 2.0) -> bool:
        """Close the HTTP session and join the owned auth-probe thread."""
        self._closed = True
        self.is_authenticated = False
        self.auth_verified = False
        self.init_error = "client_closed"
        telemetry_stopped = self.stop_telemetry(timeout=timeout)
        try:
            self.session.close()
        finally:
            thread = self._auth_probe_thread
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout=max(0.0, float(timeout)))
        auth_stopped = thread is None or not thread.is_alive()
        return bool(auth_stopped and telemetry_stopped)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        return False

    def _ensure_economic_dispatch_store(self) -> None:
        if not hasattr(self, "_economic_dispatch_lock"):
            self._economic_dispatch_lock = threading.RLock()
        if not hasattr(self, "_economic_dispatches"):
            self._economic_dispatches = {}

    def _register_economic_dispatch(
        self,
        *,
        method: str,
        endpoint: str,
        body_digest: str,
    ) -> object:
        self._ensure_economic_dispatch_store()
        dispatch = object()
        with self._economic_dispatch_lock:
            self._economic_dispatches[dispatch] = (method, endpoint, body_digest)
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
        endpoint: str,
        body: Dict[str, Any],
    ) -> None:
        self._ensure_economic_dispatch_store()
        with self._economic_dispatch_lock:
            state = self._economic_dispatches.pop(dispatch, None)
        if state is None:
            raise EconomicGovernanceBlocked(
                "alpaca_mutation_dispatch_capability_required"
            )
        if not isinstance(body, dict):
            raise EconomicGovernanceBlocked("exact_alpaca_mutation_body_required")
        try:
            observed = (
                str(method).strip().upper(),
                endpoint,
                _economic_transport_body_digest(body),
            )
        except (TypeError, ValueError) as exc:
            raise EconomicGovernanceBlocked(
                "exact_alpaca_mutation_body_required"
            ) from exc
        if observed != state:
            raise EconomicGovernanceBlocked(
                "exact_alpaca_mutation_method_path_body_required"
            )

    def _alpaca_http_request(
        self,
        method: str,
        endpoint: str,
        *,
        request_base: str,
        params: Optional[Dict[str, Any]],
        body: Dict[str, Any],
        _economic_dispatch: object | None = None,
    ) -> requests.Response:
        """Final HTTP seam; mutation capability is burned before the session."""

        normalized_method = str(method).strip().upper()
        is_mutation = _is_alpaca_economic_mutation_path(
            normalized_method, endpoint
        )
        if is_mutation:
            expected_base = ALPACA_PAPER_BASE if self.use_paper else ALPACA_LIVE_BASE
            if request_base != expected_base:
                raise EconomicGovernanceBlocked(
                    "canonical_alpaca_environment_endpoint_required"
                )
            if self.dry_run:
                raise EconomicGovernanceBlocked(
                    "alpaca_dry_run_mutation_transport_forbidden"
                )
            self._consume_economic_dispatch(
                _economic_dispatch,
                method=normalized_method,
                endpoint=endpoint,
                body=body,
            )
        elif normalized_method != "GET" or _economic_dispatch is not None:
            raise EconomicGovernanceBlocked(
                "unsupported_or_misbound_alpaca_transport_operation"
            )
        return self.session.request(
            normalized_method,
            f"{request_base}{endpoint}",
            params=params,
            json=body or None,
            timeout=self.timeout_seconds,
        )

    def _request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None, base_url: str = None, request_type: str = 'data') -> Any:
        """Make a request with adaptive rate limiting.
        
        Args:
            request_type: 'trading' or 'data' - determines which rate limit bucket to use
        """
        normalized_method = str(method).strip().upper()
        is_mutation = _is_alpaca_economic_mutation_path(
            normalized_method, endpoint
        )
        if normalized_method != "GET" and not is_mutation:
            raise EconomicGovernanceBlocked(
                "canonical_alpaca_mutation_method_and_path_required"
            )
        request_base = base_url or self.base_url
        economic_body = dict(data or {}) if isinstance(data, dict) or data is None else data
        if is_mutation:
            if request_type != "trading":
                raise EconomicGovernanceBlocked(
                    "alpaca_mutation_trading_request_type_required"
                )
            if params:
                raise EconomicGovernanceBlocked(
                    "alpaca_mutation_query_parameters_forbidden"
                )
            if not isinstance(economic_body, dict):
                raise EconomicGovernanceBlocked(
                    "exact_alpaca_mutation_body_required"
                )
            if self.dry_run:
                raise EconomicGovernanceBlocked(
                    "alpaca_dry_run_mutation_transport_forbidden"
                )
            expected_base = ALPACA_PAPER_BASE if self.use_paper else ALPACA_LIVE_BASE
            if request_base != expected_base:
                raise EconomicGovernanceBlocked(
                    "canonical_alpaca_environment_endpoint_required"
                )

        if self._closed or not getattr(self, 'is_authenticated', True):
            return {}
        url = f"{request_base}{endpoint}"
        attempt_count = 1 if is_mutation else self.max_retries + 1
        for attempt in range(attempt_count):
            try:
                # Short GET dedup: avoid duplicate identical GET requests within short TTL
                cache_key = None
                if method.upper() == 'GET' and not data:
                    try:
                        params_key = ''
                        if params:
                            params_items = sorted((k, str(v)) for k, v in params.items())
                            params_key = '&'.join([f"{k}={v}" for k, v in params_items])
                        cache_key = f"GET::{url}::{params_key}"
                        cached = self._response_cache.get(cache_key)
                        if cached is not None:
                            return cached
                    except Exception:
                        cache_key = None

                # Phase 2: Global Rate Budget with priority allocation
                if self._global_rate_budget and self._classify_request_type:
                    try:
                        priority = self._classify_request_type(endpoint, method)
                        is_trading = request_type == 'trading'
                        if not self._global_rate_budget.wait_for_slot(priority, is_trading):
                            # Request rejected due to high-priority backoff
                            logger.warning(f"Request rejected by GlobalRateBudget: {priority.name} for {endpoint}")
                            if is_mutation:
                                self.last_error = {
                                    "error": "global_rate_budget_denied",
                                    "endpoint": endpoint,
                                    "url": url,
                                }
                                return {}
                            time.sleep(0.1)  # Brief delay before retry
                            continue
                    except Exception as e:
                        logger.debug(f"GlobalRateBudget check failed: {e}")

                # Respect adaptive rate limiter
                try:
                    if request_type == 'trading':
                        self._rate_limiter.wait_trading()
                    else:
                        self._rate_limiter.wait_data()
                except Exception:
                    # In case rate limiter fails, don't block the call
                    pass

                dispatch = None
                if is_mutation:
                    if self.use_paper:
                        body_digest = _economic_transport_body_digest(economic_body)
                    else:
                        body_digest = _claim_economic_transport_context(
                            method=normalized_method,
                            path=endpoint,
                            body=economic_body,
                        )
                    dispatch = self._register_economic_dispatch(
                        method=normalized_method,
                        endpoint=endpoint,
                        body_digest=body_digest,
                    )
                try:
                    resp = self._alpaca_http_request(
                        normalized_method,
                        endpoint,
                        request_base=request_base,
                        params=params,
                        body=economic_body if isinstance(economic_body, dict) else {},
                        _economic_dispatch=dispatch,
                    )
                finally:
                    self._discard_economic_dispatch(dispatch)

                # 🛡️ RATE LIMIT HANDLING - Respect Retry-After header if present
                if resp.status_code == 429:
                    # Trigger adaptive backoff
                    self._rate_limiter.on_429_error()

                    # Phase 2: Notify GlobalRateBudget of 429
                    if self._global_rate_budget and self._classify_request_type:
                        try:
                            priority = self._classify_request_type(endpoint, method)
                            self._global_rate_budget.on_429_error(priority)
                        except Exception as e:
                            logger.debug(f"GlobalRateBudget 429 notification failed: {e}")
                    
                    # Metric: API 429
                    try:
                        from aureon.core.metrics import api_429_counter
                        api_429_counter.inc(1, exchange='alpaca', endpoint=endpoint)
                    except Exception:
                        pass

                    if is_mutation:
                        body_text = (resp.text or "").strip()
                        self.last_error = {
                            "status_code": 429,
                            "body": body_text[:2000],
                            "endpoint": endpoint,
                            "url": url,
                        }
                        return {}

                    retry_after = resp.headers.get('Retry-After')
                    if retry_after:
                        try:
                            wait_time = float(retry_after)
                        except Exception:
                            wait_time = min(60, 2 ** (attempt + 2))  # More aggressive backoff
                    else:
                        wait_time = min(60, 2 ** (attempt + 2))  # More aggressive backoff

                    # add jitter
                    import random
                    jitter = min(2.0, wait_time * 0.2)  # More jitter
                    wait_time = wait_time + (jitter * (0.5 - random.random()))

                    logger.warning(f"Rate limited (429) - waiting {wait_time:.2f}s before retry {attempt + 1}")
                    time.sleep(max(1.0, wait_time))  # Min 1s wait
                    if attempt < self.max_retries:
                        continue
                    # Fall through to error handling if out of retries

                if not resp.ok:
                    body_text = (resp.text or "").strip()
                    logger.error(f"Alpaca API Error {resp.status_code}: {body_text} [URL: {url}]")
                    self.last_error = {
                        "status_code": resp.status_code,
                        "body": body_text[:2000],
                        "endpoint": endpoint,
                        "url": url,
                    }
                    return {}

                # Cache GET responses for dedup window
                try:
                    result_json = resp.json()
                    if cache_key and result_json is not None:
                        self._response_cache.set(cache_key, result_json)
                except Exception:
                    result_json = {}

                self.last_error = None
                self.init_error = ""
                return result_json
            except requests.exceptions.Timeout as e:
                if not is_mutation and attempt < self.max_retries:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                logger.error(f"Alpaca Request Failed: {e}")
                self.last_error = {"exception": str(e), "endpoint": endpoint, "url": url}
                if "WinError 10013" in str(e):
                    self.init_error = "socket_blocked"
                return {}
            except Exception as e:
                if isinstance(e, EconomicGovernanceBlocked):
                    raise
                logger.error(f"Alpaca Request Failed: {e}")
                self.last_error = {"exception": str(e), "endpoint": endpoint, "url": url}
                if "WinError 10013" in str(e):
                    self.init_error = "socket_blocked"
                return {}

    # ═════════════════════════════════════════════════════════════════════=
    # INTERNAL HELPERS
    # ═════════════════════════════════════════════════════════════════════=

    @staticmethod
    def _normalize_pair_symbol(symbol: str) -> Optional[str]:
        """
        Normalize crypto pair symbols to Alpaca's slash format (e.g., BTCUSD -> BTC/USD).

        Alpaca asset payloads sometimes return BTC/USD while upstream callers may
        provide BTCUSD. This helper makes sure we always talk to the API using the
        slash variant and keeps base/quote parsing consistent across the client.
        """
        if not symbol:
            return None

        cleaned = symbol.replace(' ', '').replace('-', '/').upper()
        if '/' in cleaned:
            parts = cleaned.split('/')
            if len(parts) == 2 and parts[0] and parts[1]:
                return f"{parts[0]}/{parts[1]}"

        # Check quote currencies - LONGEST FIRST to avoid "USDC".endswith("USD") matching!
        for quote in ("USDT", "USDC", "USD"):  # Longest first!
            if cleaned.endswith(quote) and len(cleaned) > len(quote):
                base = cleaned[:-len(quote)]
                return f"{base}/{quote}"

        # If it's a plain crypto symbol (no slash, doesn't end with quote), assume USD quote
        # This handles cases like "BTC", "ETH", "LTC" -> "BTC/USD", "ETH/USD", "LTC/USD"
        # Check in order: longest first to avoid substring matches
        if cleaned and not cleaned.endswith("USDT") and not cleaned.endswith("USDC") and not cleaned.endswith("USD"):
            return f"{cleaned}/USD"

        return None

    @staticmethod
    def _chunk_symbols(symbols: Iterable[str], chunk_size: int = 50) -> Iterable[List[str]]:
        chunk = []
        for sym in symbols:
            normalized = AlpacaClient._normalize_pair_symbol(sym)
            if not normalized:
                continue
            chunk.append(normalized)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk

    @staticmethod
    def _resolve_symbol(symbol: str) -> str:
        cleaned = str(symbol or "").strip().upper()
        base = cleaned.replace("-", "/").split("/")[0]
        looks_crypto = (
            "/" in cleaned
            or "-" in cleaned
            or base in CRYPTO_BASE_SYMBOLS
            or any(
                cleaned.endswith(quote) and len(cleaned) > len(quote)
                for quote in ("USDT", "USDC", "USD")
            )
        )
        if looks_crypto:
            normalized = AlpacaClient._normalize_pair_symbol(cleaned)
            if normalized:
                return normalized
        return cleaned

    @staticmethod
    def _finite_number(
        value: Any,
        *,
        positive: bool = False,
        nonnegative: bool = False,
    ) -> Optional[float]:
        if isinstance(value, bool) or value is None:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if not math.isfinite(number):
            return None
        if positive and number <= 0.0:
            return None
        if nonnegative and number < 0.0:
            return None
        return number

    @staticmethod
    def _provider_timestamp_epoch(value: Any) -> Optional[float]:
        if isinstance(value, bool) or value is None:
            return None
        if isinstance(value, (int, float)):
            epoch = AlpacaClient._finite_number(value, positive=True)
            if epoch is not None and epoch >= 100_000_000_000.0:
                epoch /= 1000.0
            return epoch
        text = str(value).strip()
        if not text:
            return None
        numeric = AlpacaClient._finite_number(text, positive=True)
        if numeric is not None:
            if numeric >= 100_000_000_000.0:
                numeric /= 1000.0
            return numeric
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed.tzinfo is None:
            return None
        try:
            epoch = parsed.timestamp()
        except (OSError, OverflowError, ValueError):
            return None
        return epoch if math.isfinite(epoch) and epoch > 0.0 else None

    def _fresh_provider_timestamp(
        self,
        value: Any,
        *,
        max_age_seconds: float,
        now: Optional[float] = None,
    ) -> Optional[float]:
        epoch = self._provider_timestamp_epoch(value)
        current = self._finite_number(time.time() if now is None else now, positive=True)
        if epoch is None or current is None:
            return None
        age = current - epoch
        if age < -self.provider_future_skew_seconds or age > max_age_seconds:
            return None
        return epoch

    @staticmethod
    def _valid_provider_identifier(value: Any) -> Optional[str]:
        if isinstance(value, bool) or value is None:
            return None
        identifier = str(value).strip()
        if not identifier:
            return None
        candidate = identifier
        if "::" in identifier:
            activity_prefix, candidate = identifier.rsplit("::", 1)
            if not activity_prefix.isdigit():
                return None
        try:
            uuid.UUID(candidate)
        except (AttributeError, TypeError, ValueError):
            return None
        return identifier

    def _normalize_quote_observation(
        self,
        symbol: str,
        payload: Any,
        *,
        now: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        bid = self._finite_number(payload.get("bp"), positive=True)
        ask = self._finite_number(payload.get("ap"), positive=True)
        timestamp_raw = payload.get("t")
        provider_timestamp = self._fresh_provider_timestamp(
            timestamp_raw,
            max_age_seconds=self.quote_max_age_seconds,
            now=now,
        )
        if bid is None or ask is None or bid > ask or provider_timestamp is None:
            return None
        received_at = datetime.now(timezone.utc).isoformat()
        result = dict(payload)
        result.update(
            {
                "symbol": symbol,
                "bp": bid,
                "ap": ask,
                "mid": (bid + ask) / 2.0,
                "provider_timestamp": provider_timestamp,
                "source_timestamp": provider_timestamp,
                "provider_timestamp_raw": timestamp_raw,
                "received_at": received_at,
                "data_status": "live",
                "truth_status": "real_observed",
                "generated_values": False,
                "action_eligible": True,
            }
        )
        return result

    def _normalize_bar_observation(
        self,
        symbol: str,
        payload: Any,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(payload, dict):
            return None
        open_price = self._finite_number(payload.get("o"), positive=True)
        high_price = self._finite_number(payload.get("h"), positive=True)
        low_price = self._finite_number(payload.get("l"), positive=True)
        close_price = self._finite_number(payload.get("c"), positive=True)
        volume = self._finite_number(payload.get("v"), nonnegative=True)
        timestamp_raw = payload.get("t")
        provider_timestamp = self._provider_timestamp_epoch(timestamp_raw)
        received_epoch = time.time()
        if (
            open_price is None
            or high_price is None
            or low_price is None
            or close_price is None
            or volume is None
            or provider_timestamp is None
            or provider_timestamp > received_epoch + self.provider_future_skew_seconds
            or high_price < low_price
            or not (low_price <= open_price <= high_price)
            or not (low_price <= close_price <= high_price)
        ):
            return None
        result = dict(payload)
        result.update(
            {
                "symbol": symbol,
                "o": open_price,
                "h": high_price,
                "l": low_price,
                "c": close_price,
                "v": volume,
                "provider_timestamp": provider_timestamp,
                "source_timestamp": provider_timestamp,
                "provider_timestamp_raw": timestamp_raw,
                "received_at": datetime.now(timezone.utc).isoformat(),
                "data_status": "live",
                "truth_status": "real_observed",
                "generated_values": False,
            }
        )
        return result

    def _pending_order_receipt(
        self,
        order: Any,
        reason: str,
        *,
        submission_attempted: bool,
    ) -> Dict[str, Any]:
        raw = dict(order) if isinstance(order, dict) else {}
        provider_order_id = self._valid_provider_identifier(raw.get("id"))
        provider_status = str(raw.get("status") or "").strip().lower() or None
        timestamp_raw = (
            raw.get("filled_at")
            or raw.get("updated_at")
            or raw.get("submitted_at")
            or raw.get("created_at")
        )
        provider_timestamp = self._provider_timestamp_epoch(timestamp_raw)
        submitted = provider_order_id is not None
        return {
            **raw,
            "id": provider_order_id,
            "provider_order_id": provider_order_id,
            "status": "pending_reconciliation" if submission_attempted else "no_data",
            "provider_status": provider_status,
            "data_status": "pending_reconciliation" if submission_attempted else "no_data",
            "truth_status": "real_observed" if raw else "no_data",
            "reason": reason,
            "submitted": submitted,
            "submission_attempted": bool(submission_attempted),
            "submission_acknowledged": submitted,
            "reconciliation_required": bool(submission_attempted),
            "provider_timestamp": provider_timestamp,
            "source_timestamp": provider_timestamp,
            "provider_timestamp_raw": timestamp_raw,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "fills": [],
            "filled_qty": None,
            "filled_avg_price": None,
            "filled_notional": None,
            "fee": None,
            "fee_currency": None,
            "fill_receipt_complete": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "generated_values": False,
            "raw_receipt": raw,
        }

    @staticmethod
    def _not_submitted_order_receipt(
        reason: str,
        **request: Any,
    ) -> Dict[str, Any]:
        return {
            **request,
            "id": None,
            "provider_order_id": None,
            "status": "not_submitted",
            "provider_status": None,
            "data_status": "not_submitted",
            "truth_status": "dry_run" if reason == "dry_run" else "no_data",
            "reason": reason,
            "submitted": False,
            "submission_attempted": False,
            "submission_acknowledged": False,
            "reconciliation_required": False,
            "provider_timestamp": None,
            "source_timestamp": None,
            "fills": [],
            "filled_qty": None,
            "filled_avg_price": None,
            "filled_notional": None,
            "fee": None,
            "fee_currency": None,
            "fill_receipt_complete": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "generated_values": False,
        }

    def _normalize_fill_activity(
        self,
        activity: Any,
        *,
        order_id: str,
        symbol: str,
        side: str,
        now: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(activity, dict):
            return None
        details = activity.get("details") if isinstance(activity.get("details"), dict) else {}
        activity_order_id = self._valid_provider_identifier(
            activity.get("order_id") or details.get("order_id")
        )
        trade_id = self._valid_provider_identifier(
            activity.get("id") or activity.get("ref_id") or activity.get("event_id")
        )
        activity_type = str(
            activity.get("activity_type")
            or details.get("execution_type")
            or activity.get("type")
            or ""
        ).strip().lower()
        activity_symbol = str(activity.get("symbol") or details.get("symbol") or "").strip().upper()
        activity_side = str(activity.get("side") or details.get("side") or "").strip().lower()
        qty = self._finite_number(activity.get("qty"), positive=True)
        price = self._finite_number(activity.get("price"), positive=True)
        timestamp_raw = (
            activity.get("transaction_time")
            or activity.get("executed_at")
            or activity.get("at")
        )
        provider_timestamp = self._fresh_provider_timestamp(
            timestamp_raw,
            max_age_seconds=self.order_receipt_max_age_seconds,
            now=now,
        )
        if (
            activity_order_id != order_id
            or trade_id is None
            or activity_type not in {"fill", "partial_fill", "trd"}
            or activity_symbol.replace("/", "") != symbol.upper().replace("/", "")
            or activity_side != side
            or qty is None
            or price is None
            or provider_timestamp is None
        ):
            return None
        commission = self._finite_number(
            activity.get("commission")
            if "commission" in activity
            else details.get("commission"),
            nonnegative=True,
        )
        fee_currency = str(
            activity.get("fee_currency")
            or activity.get("currency")
            or details.get("fee_currency")
            or details.get("currency")
            or ""
        ).strip()
        return {
            "tradeId": trade_id,
            "trade_id": trade_id,
            "qty": qty,
            "price": price,
            "commission": commission,
            "commissionAsset": fee_currency or None,
            "fee_currency": fee_currency or None,
            "provider_timestamp": provider_timestamp,
            "source_timestamp": provider_timestamp,
            "provider_timestamp_raw": timestamp_raw,
            "truth_status": "real_observed",
            "generated_values": False,
            "raw_activity": dict(activity),
        }

    def _normalize_order_receipt(
        self,
        order: Any,
        *,
        fill_activities: Optional[List[Dict[str, Any]]] = None,
        submission_attempted: bool,
        now: Optional[float] = None,
    ) -> Dict[str, Any]:
        if not isinstance(order, dict):
            return self._pending_order_receipt(
                order,
                "provider_submission_outcome_unproven",
                submission_attempted=submission_attempted,
            )
        provider_order_id = self._valid_provider_identifier(order.get("id"))
        provider_status = str(order.get("status") or "").strip().lower()
        if provider_order_id is None:
            return self._pending_order_receipt(
                order,
                "non_sentinel_provider_order_id_required",
                submission_attempted=submission_attempted,
            )
        if provider_status != "filled":
            terminal_reason = (
                f"provider_order_{provider_status}"
                if provider_status in {"canceled", "expired", "rejected", "replaced"}
                else "terminal_provider_fill_receipt_required"
            )
            return self._pending_order_receipt(
                order,
                terminal_reason,
                submission_attempted=submission_attempted,
            )

        filled_qty = self._finite_number(order.get("filled_qty"), positive=True)
        filled_avg_price = self._finite_number(order.get("filled_avg_price"), positive=True)
        filled_at_raw = order.get("filled_at")
        provider_timestamp = self._fresh_provider_timestamp(
            filled_at_raw,
            max_age_seconds=self.order_receipt_max_age_seconds,
            now=now,
        )
        symbol = str(order.get("symbol") or "").strip().upper()
        side = str(order.get("side") or "").strip().lower()
        if (
            filled_qty is None
            or filled_avg_price is None
            or provider_timestamp is None
            or not symbol
            or side not in {"buy", "sell"}
        ):
            return self._pending_order_receipt(
                order,
                "fresh_provider_fill_quantity_price_and_timestamp_required",
                submission_attempted=submission_attempted,
            )

        normalized_fills: List[Dict[str, Any]] = []
        for activity in fill_activities or []:
            normalized = self._normalize_fill_activity(
                activity,
                order_id=provider_order_id,
                symbol=symbol,
                side=side,
                now=now,
            )
            if normalized is not None:
                normalized_fills.append(normalized)
        trade_ids = [str(fill["trade_id"]) for fill in normalized_fills]
        if not normalized_fills or len(trade_ids) != len(set(trade_ids)):
            return self._pending_order_receipt(
                order,
                "fresh_provider_fill_activity_ids_required",
                submission_attempted=submission_attempted,
            )
        activity_qty = sum(float(fill["qty"]) for fill in normalized_fills)
        activity_notional = sum(float(fill["qty"]) * float(fill["price"]) for fill in normalized_fills)
        activity_avg_price = activity_notional / activity_qty
        qty_tolerance = max(1e-12, filled_qty * 1e-8)
        price_tolerance = max(1e-8, filled_avg_price * 1e-6)
        if (
            abs(activity_qty - filled_qty) > qty_tolerance
            or abs(activity_avg_price - filled_avg_price) > price_tolerance
        ):
            return self._pending_order_receipt(
                order,
                "order_and_fill_activity_totals_inconsistent",
                submission_attempted=submission_attempted,
            )

        fee = self._finite_number(
            order.get("commission") if "commission" in order else order.get("fee"),
            nonnegative=True,
        )
        fee_currency = str(
            order.get("commission_currency")
            or order.get("fee_currency")
            or order.get("currency")
            or ""
        ).strip()
        if fee is None or not fee_currency:
            commissions = [fill.get("commission") for fill in normalized_fills]
            currencies = {
                str(fill.get("fee_currency") or "").strip()
                for fill in normalized_fills
                if str(fill.get("fee_currency") or "").strip()
            }
            if all(value is not None for value in commissions) and len(currencies) == 1:
                fee = sum(float(value) for value in commissions)
                fee_currency = next(iter(currencies))
        if fee is None or not fee_currency:
            pending = self._pending_order_receipt(
                order,
                "provider_fee_receipt_and_currency_required",
                submission_attempted=submission_attempted,
            )
            pending.update(
                {
                    "provider_status": "filled",
                    "fills": normalized_fills,
                    "filled_qty": filled_qty,
                    "filled_avg_price": filled_avg_price,
                    "filled_notional": activity_notional,
                }
            )
            return pending

        latest_fill_timestamp = max(
            provider_timestamp,
            *(float(fill["provider_timestamp"]) for fill in normalized_fills),
        )
        return {
            **dict(order),
            "id": provider_order_id,
            "provider_order_id": provider_order_id,
            "status": "filled",
            "provider_status": "filled",
            "data_status": "live",
            "truth_status": "real_derived",
            "reason": "complete_fresh_terminal_provider_fill_receipt",
            "submitted": True,
            "submission_attempted": bool(submission_attempted),
            "submission_acknowledged": True,
            "reconciliation_required": False,
            "provider_timestamp": latest_fill_timestamp,
            "source_timestamp": latest_fill_timestamp,
            "provider_timestamp_raw": filled_at_raw,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "fills": normalized_fills,
            "filled_qty": filled_qty,
            "filled_avg_price": filled_avg_price,
            "filled_notional": activity_notional,
            "fee": fee,
            "fee_currency": fee_currency,
            "fill_receipt_complete": True,
            "eligible_for_accounting": True,
            "eligible_for_learning": True,
            "generated_values": False,
            "provider_receipt_type": "AlpacaOrderAndFillActivities",
            "raw_receipt": dict(order),
        }

    # ═════════════════════════════════════════════════════════════════════=
    # CORE ACCOUNT / MARKET DATA
    # ═════════════════════════════════════════════════════════════════════=

    def get_account(self) -> Dict[str, Any]:
        """Get account details with short-lived caching."""
        if not self.is_authenticated:
            return {}
        cached = None
        try:
            cached = self._account_cache.get('account')
        except Exception:
            pass
        if cached is not None:
            return cached

        resp = self._request("GET", "/v2/account", request_type='trading')
        try:
            if isinstance(resp, dict):
                self._account_cache.set('account', resp)
        except Exception:
            pass
        return resp

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions with short-lived caching."""
        cached = None
        try:
            cached = self._position_cache.get('positions')
        except Exception:
            pass
        if cached is not None:
            return cached

        resp = self._request("GET", "/v2/positions", request_type='trading')

        # Handle API errors - if we get an empty dict due to error, return empty list
        if resp == {}:
            logger.warning("Alpaca positions API returned empty response (likely rate limited), returning empty positions list")
            resp = []

        try:
            if isinstance(resp, list) or isinstance(resp, dict):
                self._position_cache.set('positions', resp)
        except Exception:
            pass
        return resp

    def get_position(self, symbol: str) -> Dict[str, Any]:
        """Get position for a specific symbol."""
        symbol = self._resolve_symbol(symbol)
        return self._request("GET", f"/v2/positions/{symbol}", request_type='trading')

    def list_assets(self, status: str = "active", asset_class: str = "crypto") -> List[Dict[str, Any]]:
        """List assets (compatibility helper for wave scanner)."""
        params = {"status": status, "asset_class": asset_class}
        resp = self._request("GET", "/v2/assets", params=params, request_type='data')
        return resp if isinstance(resp, list) else resp.get("assets", []) if isinstance(resp, dict) else []

    def get_clock(self) -> Dict[str, Any]:
        """Get market clock."""
        return self._request("GET", "/v2/clock", request_type='data')

    def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        type: str = "market",
        time_in_force: str = "gtc",
        position_intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit an order and return only provider-observed lifecycle evidence."""
        symbol = self._resolve_symbol(symbol)
        quantity = self._finite_number(qty, positive=True)
        side_normalized = str(side or "").strip().lower()
        order_type = str(type or "").strip().lower()
        if quantity is None or side_normalized not in {"buy", "sell"} or not order_type:
            return self._not_submitted_order_receipt(
                "invalid_order_request",
                symbol=symbol,
                side=side_normalized,
                requested_qty=qty,
                type=order_type or None,
            )
        if self.dry_run:
            logger.info(f"[DRY RUN] Alpaca Order: {side_normalized} {quantity} {symbol}")
            return self._not_submitted_order_receipt(
                "dry_run",
                symbol=symbol,
                side=side_normalized,
                requested_qty=quantity,
                type=order_type,
                time_in_force=time_in_force,
            )
        if not self.is_authenticated:
            return self._not_submitted_order_receipt(
                self.init_error or "credentials_missing",
                symbol=symbol,
                side=side_normalized,
                requested_qty=quantity,
                type=order_type,
                time_in_force=time_in_force,
            )

        data = {
            "symbol": symbol,
            "qty": str(quantity),
            "side": side_normalized,
            "type": order_type,
            "time_in_force": time_in_force,
        }
        if position_intent:
            data["position_intent"] = position_intent
        result = self._request("POST", "/v2/orders", data=data, request_type="trading")
        if not isinstance(result, dict):
            return self._normalize_order_receipt(
                result,
                submission_attempted=True,
            )

        provider_order_id = self._valid_provider_identifier(result.get("id"))
        last_observed = result
        if order_type == "market" and provider_order_id is not None:
            if str(result.get("status") or "").strip().lower() == "filled":
                return self.get_order_fills(provider_order_id, order=result)
            for attempt in range(3):
                time.sleep(0.5 * (attempt + 1))
                order_status = self._request(
                    "GET",
                    f"/v2/orders/{provider_order_id}",
                    request_type="trading",
                )
                if not isinstance(order_status, dict) or not order_status:
                    continue
                last_observed = order_status
                status = str(order_status.get("status") or "").strip().lower()
                if status == "filled":
                    return self.get_order_fills(provider_order_id, order=order_status)
                if status in {"canceled", "expired", "rejected", "replaced"}:
                    break

        return self._normalize_order_receipt(
            last_observed,
            fill_activities=[],
            submission_attempted=True,
        )
    # Compatibility alias for older code (create_order -> place_order)
    create_order = place_order

    async def execute_trade(self, symbol: str, side: str, quantity: float) -> Dict:
        """Standardized trade execution method."""
        return self.place_order(
            symbol=symbol,
            qty=quantity,
            side=side,
            type="market",
            time_in_force="gtc"
        )

    def get_orders(self, status: str = "open", limit: int = 50) -> List[Dict]:
        """Get a list of orders."""
        params = {"status": status, "limit": limit}
        result = self._request("GET", "/v2/orders", params=params, request_type='trading')
        return result if isinstance(result, list) else []

    def get_crypto_bars(self, symbols: List[str], timeframe: str = "1Min", limit: int = 100) -> Dict[str, Any]:
        """Return only structurally valid provider bars with their source times."""
        all_bars: Dict[str, List[Dict[str, Any]]] = {}
        for chunk in self._chunk_symbols(symbols):
            response = self._request(
                "GET", "/v1beta3/crypto/us/bars",
                params={"symbols": ",".join(chunk), "timeframe": timeframe, "limit": limit},
                base_url=self.data_url, request_type="data",
            )
            payload = response.get("bars", response) if isinstance(response, dict) else {}
            if not isinstance(payload, dict):
                continue
            for raw_symbol, raw_bars in payload.items():
                normalized_symbol = self._normalize_pair_symbol(raw_symbol) or str(raw_symbol)
                if not isinstance(raw_bars, list):
                    continue
                verified = [
                    bar for item in raw_bars
                    if (bar := self._normalize_bar_observation(normalized_symbol, item)) is not None
                ]
                if verified:
                    all_bars.setdefault(normalized_symbol, []).extend(verified)
        if not all_bars:
            return {
                "bars": {}, "data_status": "no_data", "truth_status": "no_data",
                "reason": "provider_bars_missing_or_malformed", "generated_values": False,
            }
        return {
            "bars": all_bars, "data_status": "live", "truth_status": "real_observed",
            "received_at": datetime.now(timezone.utc).isoformat(), "generated_values": False,
        }

    def get_latest_crypto_quotes(self, symbols: List[str]) -> Dict[str, Any]:
        """Return fresh, two-sided crypto quotes with provider source timestamps."""
        all_quotes: Dict[str, Any] = {}
        remaining: List[str] = []
        now = time.time()
        for symbol in symbols:
            normalized = self._normalize_pair_symbol(symbol) or str(symbol)
            cache_key = f"last_quote::{normalized}"
            try:
                cached = self._quote_cache.get(cache_key)
            except Exception:
                cached = None
            raw_cached = cached.get("raw") if isinstance(cached, dict) else None
            verified_cached = self._normalize_quote_observation(normalized, raw_cached, now=now)
            if verified_cached is not None:
                all_quotes[normalized] = verified_cached
            else:
                remaining.append(normalized)
        for chunk in self._chunk_symbols(remaining):
            response = self._request(
                "GET", "/v1beta3/crypto/us/latest/quotes",
                params={"symbols": ",".join(chunk)}, base_url=self.data_url, request_type="data",
            )
            payload = response.get("quotes", response) if isinstance(response, dict) else {}
            if not isinstance(payload, dict):
                continue
            for raw_symbol, raw_quote in payload.items():
                normalized_symbol = self._normalize_pair_symbol(raw_symbol) or str(raw_symbol)
                quote = self._normalize_quote_observation(normalized_symbol, raw_quote, now=now)
                if quote is None:
                    continue
                all_quotes[normalized_symbol] = quote
                cache_value = {
                    "last": {"price": quote["mid"], "source": "provider_quote_midpoint"},
                    "raw": quote, "provider_timestamp": quote["provider_timestamp"],
                    "source_timestamp": quote["source_timestamp"], "data_status": "live",
                    "truth_status": "real_derived", "generated_values": False,
                }
                try:
                    self._quote_cache.set(f"last_quote::{normalized_symbol}", cache_value)
                except Exception:
                    pass
        return all_quotes

    def get_crypto_snapshot(self, symbols: List[str]) -> Dict[str, Any]:
        """Return fresh provider quotes without relabelling a midpoint as a trade."""
        normalized: List[str] = []
        symbol_map: Dict[str, str] = {}
        for symbol in symbols:
            resolved = self._normalize_pair_symbol(symbol) or str(symbol)
            normalized.append(resolved)
            symbol_map[resolved] = symbol
        result: Dict[str, Any] = {}
        for resolved, quote in self.get_latest_crypto_quotes(normalized).items():
            original = symbol_map.get(resolved, resolved)
            result[original] = {
                "symbol": resolved,
                "latestQuote": {
                    "bp": quote["bp"], "ap": quote["ap"], "t": quote.get("provider_timestamp_raw"),
                    "provider_timestamp": quote["provider_timestamp"],
                    "source_timestamp": quote["source_timestamp"],
                    "truth_status": "real_observed", "generated_values": False,
                },
                "derivedMidpoint": {
                    "p": quote["mid"], "source": "provider_bid_ask_midpoint",
                    "source_timestamp": quote["source_timestamp"],
                    "truth_status": "real_derived", "generated_values": False,
                },
                "data_status": "live", "truth_status": "real_derived", "generated_values": False,
            }
        return result

    def get_last_quote(self, symbol: str) -> Dict[str, Any]:
        """Return a fresh two-sided provider quote and its derived midpoint."""
        requested = str(symbol or "").strip().upper()
        if not requested:
            return {"data_status": "no_data", "truth_status": "no_data", "reason": "symbol_required", "generated_values": False}
        resolved = self._resolve_symbol(requested)
        cache_key = f"last_quote::{resolved}"
        try:
            cached = self._quote_cache.get(cache_key)
        except Exception:
            cached = None
        if isinstance(cached, dict):
            verified = self._normalize_quote_observation(resolved, cached.get("raw"))
            if verified is not None:
                return {
                    "last": {"price": verified["mid"], "source": "provider_quote_midpoint"},
                    "raw": verified, "provider_timestamp": verified["provider_timestamp"],
                    "source_timestamp": verified["source_timestamp"], "data_status": "live",
                    "truth_status": "real_derived", "generated_values": False,
                }
        if "/" in resolved:
            quote = self.get_latest_crypto_quotes([resolved]).get(resolved)
        else:
            response = self._request(
                "GET", f"/v2/stocks/{resolved}/quotes/latest",
                base_url=self.data_url, request_type="data",
            )
            raw_quote = response.get("quote") if isinstance(response, dict) else None
            quote = self._normalize_quote_observation(resolved, raw_quote)
        if quote is None:
            return {
                "symbol": resolved, "data_status": "no_data", "truth_status": "no_data",
                "reason": "fresh_two_sided_provider_quote_required", "generated_values": False,
            }
        receipt = {
            "last": {"price": quote["mid"], "source": "provider_quote_midpoint"},
            "raw": quote, "provider_timestamp": quote["provider_timestamp"],
            "source_timestamp": quote["source_timestamp"], "data_status": "live",
            "truth_status": "real_derived", "generated_values": False,
        }
        try:
            self._quote_cache.set(cache_key, receipt)
        except Exception:
            pass
        return receipt

    def get_assets(self, status: str = "active", asset_class: str = "crypto") -> List[Dict[str, Any]]:
        """Get list of assets."""
        params = {
            "status": status,
            "asset_class": asset_class
        }
        return self._request("GET", "/v2/assets", params=params, request_type='data')

    def get_tradable_crypto_symbols(self, quote_filter: Optional[str] = None) -> List[str]:
        """
        Return all tradable crypto symbols in normalized Alpaca format.

        Args:
            quote_filter: Optional quote currency to restrict to (e.g., 'USD')
        """
        symbols: List[str] = []
        assets = self.get_assets(status='active', asset_class='crypto') or []

        for asset in assets:
            if not asset.get('tradable'):
                continue

            normalized = self._normalize_pair_symbol(asset.get('symbol', ''))
            if not normalized:
                continue

            base, quote = normalized.split('/')
            if quote_filter and quote.upper() != quote_filter.upper():
                continue

            symbols.append(normalized)

        return symbols

    def get_tradable_stock_symbols(self) -> List[str]:
        """
        Return all tradable stock symbols.
        """
        symbols: List[str] = []
        assets = self.get_assets(status='active', asset_class='us_equity') or []

        for asset in assets:
            if not asset.get('tradable'):
                continue

            symbol = asset.get('symbol', '')
            if symbol:
                symbols.append(symbol)

        return symbols

    def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get the provider order object by its non-sentinel ID."""
        provider_order_id = self._valid_provider_identifier(order_id)
        if provider_order_id is None:
            return {}
        result = self._request(
            "GET",
            f"/v2/orders/{provider_order_id}",
            request_type="trading",
        )
        return result if isinstance(result, dict) else {}

    def get_order_fills(
        self,
        order_id: str,
        *,
        order: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Reconcile an order with provider fill activities and provider fees."""
        provider_order_id = self._valid_provider_identifier(order_id)
        if provider_order_id is None:
            return self._pending_order_receipt(
                {},
                "non_sentinel_provider_order_id_required",
                submission_attempted=False,
            )
        observed_order = dict(order) if isinstance(order, dict) else self.get_order(provider_order_id)
        if self._valid_provider_identifier(observed_order.get("id")) != provider_order_id:
            return self._pending_order_receipt(
                observed_order,
                "provider_order_identity_mismatch",
                submission_attempted=True,
            )

        activities: List[Dict[str, Any]] = []
        if str(observed_order.get("status") or "").strip().lower() == "filled":
            fetched = self.get_account_activities(
                activity_types="FILL",
                direction="desc",
                page_size=100,
            )
            if isinstance(fetched, list):
                activities = fetched
        return self._normalize_order_receipt(
            observed_order,
            fill_activities=activities,
            submission_attempted=True,
        )

    def compute_order_fees(
        self,
        order: Dict[str, Any],
        asset_class: str = "crypto",
    ) -> Dict[str, Any]:
        """Return provider fee evidence only; never infer a fee from a rate."""
        del asset_class
        if not isinstance(order, dict):
            return {
                "fee": None,
                "fee_currency": None,
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "provider_order_receipt_required",
                "generated_values": False,
            }
        fee = self._finite_number(
            order.get("fee") if "fee" in order else order.get("commission"),
            nonnegative=True,
        )
        fee_currency = str(
            order.get("fee_currency")
            or order.get("commission_currency")
            or order.get("currency")
            or ""
        ).strip()
        if (
            order.get("fill_receipt_complete") is not True
            or order.get("generated_values") is not False
            or fee is None
            or not fee_currency
        ):
            return {
                "fee": None,
                "fee_currency": None,
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "provider_fee_receipt_and_currency_required",
                "generated_values": False,
            }
        return {
            "fee": fee,
            "fee_currency": fee_currency,
            "data_status": "live",
            "truth_status": "real_observed",
            "source_timestamp": order.get("source_timestamp"),
            "generated_values": False,
        }

    def get_order_with_fees(self, order_id: str) -> Dict[str, Any]:
        """Return a reconciled order, pending when provider fees are unavailable."""
        return self.get_order_fills(order_id)

    def compute_order_fees_in_quote(
        self,
        order: Dict[str, Any],
        primary_quote: str = "USD",
    ) -> Optional[float]:
        """Return a provider-observed fee only when it is in the requested quote."""
        fee_receipt = self.compute_order_fees(order)
        if (
            fee_receipt.get("data_status") != "live"
            or str(fee_receipt.get("fee_currency") or "").upper() != str(primary_quote).upper()
        ):
            return None
        return self._finite_number(fee_receipt.get("fee"), nonnegative=True)

    def get_all_orders(self, status: str = "closed", limit: int = 500, symbols: str = None) -> List[Dict[str, Any]]:
        """
        Get all orders with optional filtering.
        
        Args:
            status: 'open', 'closed', or 'all'
            limit: Max orders to return (max 500)
            symbols: Comma-separated symbols (e.g., "BTCUSD,ETHUSD")
        """
        params = {
            "status": status,
            "limit": limit
        }
        if symbols:
            params["symbols"] = symbols
        result = self._request("GET", "/v2/orders", params=params, request_type='trading')
        return result if isinstance(result, list) else []

    def calculate_cost_basis(self, symbol: str) -> Dict[str, Any]:
        """Calculate cost basis only from complete accounting-eligible receipts."""
        orders = self.get_all_orders(status="closed", symbols=symbol)
        verified: List[Dict[str, Any]] = []
        for order in orders if isinstance(orders, list) else []:
            qty = self._finite_number(order.get("filled_qty"), positive=True)
            price = self._finite_number(order.get("filled_avg_price"), positive=True)
            fee = self._finite_number(order.get("fee"), nonnegative=True)
            fee_currency = str(order.get("fee_currency") or "").strip().upper()
            if (
                str(order.get("status") or "").lower() != "filled"
                or order.get("fill_receipt_complete") is not True
                or order.get("eligible_for_accounting") is not True
                or order.get("generated_values") is not False
                or self._valid_provider_identifier(order.get("id")) is None
                or qty is None
                or price is None
                or fee is None
                or not fee_currency
            ):
                continue
            verified.append({**order, "_qty": qty, "_price": price, "_fee": fee, "_fee_currency": fee_currency})
        if not verified:
            return {
                "symbol": symbol,
                "total_quantity": None,
                "total_cost": None,
                "avg_cost": None,
                "trades": None,
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "complete_provider_fill_and_fee_receipts_required",
                "generated_values": False,
                "eligible_for_accounting": False,
            }

        normalized_symbol = self._normalize_pair_symbol(symbol)
        base_asset, quote_asset = (
            normalized_symbol.split("/", 1)
            if normalized_symbol and "/" in normalized_symbol
            else (str(symbol).upper(), "USD")
        )
        net_quantity = 0.0
        buy_quantity = 0.0
        buy_cost = 0.0
        for order in verified:
            qty = float(order["_qty"])
            price = float(order["_price"])
            fee = float(order["_fee"])
            fee_currency = str(order["_fee_currency"])
            side = str(order.get("side") or "").lower()
            if fee_currency not in {base_asset, quote_asset}:
                return {
                    "symbol": symbol,
                    "total_quantity": None,
                    "total_cost": None,
                    "avg_cost": None,
                    "trades": None,
                    "data_status": "no_data",
                    "truth_status": "no_data",
                    "reason": "fee_currency_conversion_receipt_required",
                    "generated_values": False,
                    "eligible_for_accounting": False,
                }
            if side == "buy":
                received_base = qty - fee if fee_currency == base_asset else qty
                quote_cost = qty * price + (fee if fee_currency == quote_asset else 0.0)
                if received_base <= 0.0:
                    continue
                net_quantity += received_base
                buy_quantity += received_base
                buy_cost += quote_cost
            elif side == "sell":
                net_quantity -= qty + (fee if fee_currency == base_asset else 0.0)
        if buy_quantity <= 0.0:
            return {
                "symbol": symbol,
                "total_quantity": net_quantity,
                "total_cost": None,
                "avg_cost": None,
                "trades": len(verified),
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "verified_buy_receipt_required",
                "generated_values": False,
                "eligible_for_accounting": False,
            }
        return {
            "symbol": symbol,
            "total_quantity": net_quantity,
            "total_cost": buy_cost,
            "avg_cost": buy_cost / buy_quantity,
            "trades": len(verified),
            "data_status": "live",
            "truth_status": "real_derived",
            "generated_values": False,
            "eligible_for_accounting": True,
        }

    def place_limit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        limit_price: float,
        time_in_force: str = "gtc",
        extended_hours: bool = False
    ) -> Dict[str, Any]:
        """
        Place a limit order on Alpaca.
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USD', 'AAPL')
            qty: Quantity to buy/sell
            side: 'buy' or 'sell'
            limit_price: Maximum buy price or minimum sell price
            time_in_force: 'day', 'gtc', 'ioc' (crypto only supports gtc, ioc)
            extended_hours: If True, order can execute in extended hours (stocks only)
            
        Returns:
            Order response
            
        Benefit: Better price control, may get better fills
        """
        symbol = self._resolve_symbol(symbol)
        if self.dry_run:
            logger.info(f"[DRY RUN] Alpaca Limit Order: {side} {qty} {symbol} @ {limit_price}")
            return self._not_submitted_order_receipt(
                "dry_run", symbol=symbol, side=side, requested_qty=qty, type="limit"
            )

        data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "limit",
            "limit_price": str(limit_price),
            "time_in_force": time_in_force
        }
        
        if extended_hours:
            data["extended_hours"] = True
            
        result = self._request("POST", "/v2/orders", data=data, request_type='trading')
        return self._normalize_order_receipt(
            result, fill_activities=[], submission_attempted=True
        )

    def place_stop_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        stop_price: float,
        time_in_force: str = "gtc"
    ) -> Dict[str, Any]:
        """
        Place a stop order on Alpaca.
        
        Args:
            symbol: Trading pair
            qty: Quantity
            side: 'buy' or 'sell'
            stop_price: Price at which to trigger the order
            time_in_force: 'day', 'gtc'
            
        Returns:
            Order response
            
        Note: For crypto, use stop_limit instead (stop not supported directly)
        """
        symbol = self._resolve_symbol(symbol)
        if self.dry_run:
            logger.info(f"[DRY RUN] Alpaca Stop Order: {side} {qty} {symbol} @ stop={stop_price}")
            return self._not_submitted_order_receipt(
                "dry_run", symbol=symbol, side=side, requested_qty=qty, type="stop"
            )

        data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "stop",
            "stop_price": str(stop_price),
            "time_in_force": time_in_force
        }
        result = self._request("POST", "/v2/orders", data=data, request_type='trading')
        return self._normalize_order_receipt(
            result, fill_activities=[], submission_attempted=True
        )

    def place_stop_limit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        stop_price: float,
        limit_price: float,
        time_in_force: str = "gtc"
    ) -> Dict[str, Any]:
        """
        Place a stop-limit order on Alpaca.
        
        Args:
            symbol: Trading pair
            qty: Quantity
            side: 'buy' or 'sell'
            stop_price: Price at which to trigger
            limit_price: Price limit for execution after trigger
            time_in_force: 'day', 'gtc'
            
        Returns:
            Order response
            
        For crypto: This is the primary way to do stop-loss (stop orders not supported)
        """
        symbol = self._resolve_symbol(symbol)
        if self.dry_run:
            logger.info(f"[DRY RUN] Alpaca Stop-Limit: {side} {qty} {symbol} @ stop={stop_price} limit={limit_price}")
            return self._not_submitted_order_receipt(
                "dry_run", symbol=symbol, side=side, requested_qty=qty, type="stop_limit"
            )

        data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "stop_limit",
            "stop_price": str(stop_price),
            "limit_price": str(limit_price),
            "time_in_force": time_in_force
        }
        result = self._request("POST", "/v2/orders", data=data, request_type='trading')
        return self._normalize_order_receipt(
            result, fill_activities=[], submission_attempted=True
        )

    def place_trailing_stop_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        trail_percent: float = None,
        trail_price: float = None,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """
        Place a trailing stop order on Alpaca.
        
        Args:
            symbol: Trading pair
            qty: Quantity
            side: 'buy' or 'sell'
            trail_percent: Percentage to trail (e.g., 2.0 = 2%)
            trail_price: Dollar amount to trail (alternative to percent)
            time_in_force: 'day' or 'gtc'
            
        Returns:
            Order response
            
        Example: 2% trailing stop on AAPL at $200 -> stop at $196
                 If AAPL rises to $210 -> stop auto-adjusts to $205.80
                 
        Note: Trailing stop only triggers during regular market hours
        """
        symbol = self._resolve_symbol(symbol)
        if self.dry_run:
            trail = f"{trail_percent}%" if trail_percent else f"${trail_price}"
            logger.info(f"[DRY RUN] Alpaca Trailing Stop: {side} {qty} {symbol} trail={trail}")
            return self._not_submitted_order_receipt(
                "dry_run", symbol=symbol, side=side, requested_qty=qty, type="trailing_stop"
            )

        data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "trailing_stop",
            "time_in_force": time_in_force
        }
        
        if trail_percent is not None:
            data["trail_percent"] = str(trail_percent)
        elif trail_price is not None:
            data["trail_price"] = str(trail_price)
        else:
            raise ValueError("Must provide either trail_percent or trail_price")
            
        result = self._request("POST", "/v2/orders", data=data, request_type='trading')
        return self._normalize_order_receipt(
            result, fill_activities=[], submission_attempted=True
        )

    def place_bracket_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        entry_type: str = "market",
        entry_limit_price: float = None,
        take_profit_limit: float = None,
        stop_loss_stop: float = None,
        stop_loss_limit: float = None,
        time_in_force: str = "gtc",
        position_intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place a bracket order (entry + take-profit + stop-loss) on Alpaca.
        
        This is atomic - if entry fills, both TP and SL orders activate.
        One cancels the other when either fills.
        
        Args:
            symbol: Trading pair
            qty: Quantity for all legs
            side: 'buy' or 'sell' for entry
            entry_type: 'market' or 'limit' for entry order
            entry_limit_price: Required if entry_type is 'limit'
            take_profit_limit: Limit price for take-profit (required)
            stop_loss_stop: Stop trigger price for stop-loss (required)
            stop_loss_limit: Optional limit price for stop-loss (creates stop-limit)
            time_in_force: 'day' or 'gtc'
            
        Returns:
            Order response with legs array
            
        Example:
            place_bracket_order('AAPL', 100, 'buy',
                               take_profit_limit=210,
                               stop_loss_stop=195,
                               stop_loss_limit=194)
        """
        symbol = self._resolve_symbol(symbol)
        if self.dry_run:
            logger.info(f"[DRY RUN] Alpaca Bracket: {side} {qty} {symbol} TP={take_profit_limit} SL={stop_loss_stop}")
            return self._not_submitted_order_receipt(
                "dry_run", symbol=symbol, side=side, requested_qty=qty,
                type=entry_type, order_class="bracket"
            )

        if take_profit_limit is None or stop_loss_stop is None:
            raise ValueError("Bracket orders require both take_profit_limit and stop_loss_stop")

        data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": entry_type,
            "time_in_force": time_in_force,
            "order_class": "bracket",
            "take_profit": {
                "limit_price": str(take_profit_limit)
            },
            "stop_loss": {
                "stop_price": str(stop_loss_stop)
            }
        }
        if position_intent:
            data["position_intent"] = position_intent
        
        if entry_type == "limit" and entry_limit_price:
            data["limit_price"] = str(entry_limit_price)
            
        if stop_loss_limit:
            data["stop_loss"]["limit_price"] = str(stop_loss_limit)
            
        result = self._request("POST", "/v2/orders", data=data, request_type='trading')
        return self._normalize_order_receipt(
            result, fill_activities=[], submission_attempted=True
        )

    def place_oco_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        take_profit_limit: float,
        stop_loss_stop: float,
        stop_loss_limit: float = None,
        time_in_force: str = "gtc"
    ) -> Dict[str, Any]:
        """
        Place an OCO (One-Cancels-Other) order on Alpaca.
        
        Use this for existing positions to add TP and SL.
        When one fills, the other is automatically cancelled.
        
        Args:
            symbol: Trading pair
            qty: Quantity to close
            side: 'sell' for long positions, 'buy' for short positions
            take_profit_limit: Limit price for take-profit
            stop_loss_stop: Stop trigger price for stop-loss
            stop_loss_limit: Optional limit price after stop triggers
            time_in_force: 'day' or 'gtc'
            
        Returns:
            Order response
        """
        symbol = self._resolve_symbol(symbol)
        if self.dry_run:
            logger.info(f"[DRY RUN] Alpaca OCO: {side} {qty} {symbol} TP={take_profit_limit} SL={stop_loss_stop}")
            return self._not_submitted_order_receipt(
                "dry_run", symbol=symbol, side=side, requested_qty=qty,
                type="limit", order_class="oco"
            )

        data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "limit",  # OCO requires limit type
            "time_in_force": time_in_force,
            "order_class": "oco",
            "take_profit": {
                "limit_price": str(take_profit_limit)
            },
            "stop_loss": {
                "stop_price": str(stop_loss_stop)
            }
        }
        
        if stop_loss_limit:
            data["stop_loss"]["limit_price"] = str(stop_loss_limit)
            
        result = self._request("POST", "/v2/orders", data=data, request_type='trading')
        return self._normalize_order_receipt(
            result, fill_activities=[], submission_attempted=True
        )

    def place_oto_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        entry_type: str = "market",
        entry_limit_price: float = None,
        take_profit_limit: float = None,
        stop_loss_stop: float = None,
        stop_loss_limit: float = None,
        time_in_force: str = "gtc",
        position_intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place an OTO (One-Triggers-Other) order on Alpaca.
        
        Entry order triggers a single exit order (either TP or SL, not both).
        Use this when you only want one exit condition.
        
        Args:
            symbol: Trading pair
            qty: Quantity
            side: 'buy' or 'sell' for entry
            entry_type: 'market' or 'limit'
            entry_limit_price: Required if entry_type is 'limit'
            take_profit_limit: Limit price for TP (provide this OR stop_loss)
            stop_loss_stop: Stop price for SL (provide this OR take_profit)
            stop_loss_limit: Optional limit price for SL
            time_in_force: 'day' or 'gtc'
            
        Returns:
            Order response
        """
        symbol = self._resolve_symbol(symbol)
        if self.dry_run:
            exit_type = f"TP={take_profit_limit}" if take_profit_limit else f"SL={stop_loss_stop}"
            logger.info(f"[DRY RUN] Alpaca OTO: {side} {qty} {symbol} {exit_type}")
            return self._not_submitted_order_receipt(
                "dry_run", symbol=symbol, side=side, requested_qty=qty,
                type=entry_type, order_class="oto"
            )

        if not take_profit_limit and not stop_loss_stop:
            raise ValueError("OTO orders require either take_profit_limit or stop_loss_stop")

        data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": entry_type,
            "time_in_force": time_in_force,
            "order_class": "oto"
        }
        if position_intent:
            data["position_intent"] = position_intent
        
        if entry_type == "limit" and entry_limit_price:
            data["limit_price"] = str(entry_limit_price)
            
        if take_profit_limit:
            data["take_profit"] = {"limit_price": str(take_profit_limit)}
        elif stop_loss_stop:
            data["stop_loss"] = {"stop_price": str(stop_loss_stop)}
            if stop_loss_limit:
                data["stop_loss"]["limit_price"] = str(stop_loss_limit)
                
        result = self._request("POST", "/v2/orders", data=data, request_type='trading')
        return self._normalize_order_receipt(
            result, fill_activities=[], submission_attempted=True
        )

    # ══════════════════════════════════════════════════════════════════════
    # ORDER MANAGEMENT - Query, Cancel, Replace
    # ══════════════════════════════════════════════════════════════════════

    def get_open_orders(self, symbol: str = None) -> List[Dict[str, Any]]:
        """
        Get all open orders, optionally filtered by symbol.
        
        Args:
            symbol: If provided, filter to this symbol only
            
        Returns:
            List of open orders
        """
        params = {"status": "open"}
        if symbol:
            params["symbols"] = symbol
        result = self._request("GET", "/v2/orders", params=params, request_type='trading')
        return result if isinstance(result, list) else []

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel a specific order by ID.
        
        Args:
            order_id: The Alpaca order ID
            
        Returns:
            Empty dict on success, error on failure
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Cancel order: {order_id}")
            return self._not_submitted_order_receipt(
                "dry_run", provider_order_id=None, requested_order_id=order_id, type="cancel"
            )

        result = self._request(
            "DELETE", f"/v2/orders/{order_id}", request_type='trading'
        )
        acknowledged = self.last_error is None
        return {
            "requested_order_id": order_id,
            "status": "pending_reconciliation" if acknowledged else "no_data",
            "data_status": "pending_reconciliation" if acknowledged else "no_data",
            "reason": (
                "cancel_request_acknowledged_position_readback_required"
                if acknowledged
                else "cancel_request_outcome_unproven"
            ),
            "cancellation_requested": acknowledged,
            "canceled_confirmed": False,
            "provider_response": result if isinstance(result, dict) else None,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "generated_values": False,
        }

    def cancel_all_orders(self) -> Dict[str, Any]:
        """
        Cancel all open orders.
        
        Returns:
            Response with count of cancelled orders
        """
        if self.dry_run:
            logger.info("[DRY RUN] Cancel all orders")
            return self._not_submitted_order_receipt(
                "dry_run", type="cancel_all"
            )

        result = self._request("DELETE", "/v2/orders", request_type='trading')
        acknowledged = self.last_error is None
        return {
            "status": "pending_reconciliation" if acknowledged else "no_data",
            "data_status": "pending_reconciliation" if acknowledged else "no_data",
            "reason": (
                "cancel_all_request_acknowledged_order_readback_required"
                if acknowledged
                else "cancel_all_request_outcome_unproven"
            ),
            "cancellation_requested": acknowledged,
            "canceled_confirmed": False,
            "provider_response": result,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "generated_values": False,
        }

    def replace_order(
        self,
        order_id: str,
        qty: float = None,
        limit_price: float = None,
        stop_price: float = None,
        trail: float = None,
        time_in_force: str = None
    ) -> Dict[str, Any]:
        """
        Replace/modify an existing order.
        
        Args:
            order_id: The order to replace
            qty: New quantity (optional)
            limit_price: New limit price (optional)
            stop_price: New stop price (optional)
            trail: New trail value for trailing stop (optional)
            time_in_force: New TIF (optional)
            
        Returns:
            New order response (replacement creates new order ID)
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Replace order: {order_id}")
            return self._not_submitted_order_receipt(
                "dry_run", replaces=order_id, type="replace"
            )

        data = {}
        if qty is not None:
            data["qty"] = str(qty)
        if limit_price is not None:
            data["limit_price"] = str(limit_price)
        if stop_price is not None:
            data["stop_price"] = str(stop_price)
        if trail is not None:
            data["trail"] = str(trail)
        if time_in_force is not None:
            data["time_in_force"] = time_in_force
            
        result = self._request(
            "PATCH", f"/v2/orders/{order_id}", data=data, request_type='trading'
        )
        return self._normalize_order_receipt(
            result, fill_activities=[], submission_attempted=True
        )

    # ══════════════════════════════════════════════════════════════════════
    # CONVENIENCE METHODS - Kraken-compatible interface
    # ══════════════════════════════════════════════════════════════════════

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float = None,
        quote_qty: float = None,
        position_intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit a market order without inventing quantity from incomplete data."""
        resolved = self._resolve_symbol(symbol)
        side_normalized = str(side or "").strip().lower()
        base_quantity = self._finite_number(quantity, positive=True)
        quote_quantity = self._finite_number(quote_qty, positive=True)

        if base_quantity is None and quote_quantity is not None:
            quote = self.get_latest_crypto_quotes([resolved]).get(resolved)
            if not isinstance(quote, dict):
                return self._not_submitted_order_receipt(
                    "fresh_two_sided_provider_quote_required",
                    symbol=resolved,
                    side=side_normalized,
                    requested_quote_qty=quote_quantity,
                    type="market",
                )
            bid = self._finite_number(quote.get("bp"), positive=True)
            ask = self._finite_number(quote.get("ap"), positive=True)
            provider_timestamp = self._fresh_provider_timestamp(
                quote.get("provider_timestamp") or quote.get("t"),
                max_age_seconds=self.quote_max_age_seconds,
            )
            if bid is None or ask is None or bid > ask or provider_timestamp is None:
                return self._not_submitted_order_receipt(
                    "fresh_two_sided_provider_quote_required",
                    symbol=resolved,
                    side=side_normalized,
                    requested_quote_qty=quote_quantity,
                    type="market",
                )
            base_quantity = quote_quantity / ((bid + ask) / 2.0)

        if base_quantity is None:
            return self._not_submitted_order_receipt(
                "positive_base_or_quote_quantity_required",
                symbol=resolved,
                side=side_normalized,
                requested_qty=quantity,
                requested_quote_qty=quote_qty,
                type="market",
            )

        is_crypto = "/" in resolved
        is_usdt = resolved.endswith("/USDT")
        time_in_force = "day" if is_crypto and is_usdt else "ioc" if is_crypto else "gtc"
        return self.place_order(
            resolved,
            base_quantity,
            side_normalized,
            type="market",
            time_in_force=time_in_force,
            position_intent=position_intent,
        )

    def place_stop_loss_order(self, symbol: str, side: str, quantity: float, stop_price: float, limit_price: float = None) -> Dict[str, Any]:
        """
        Place a stop-loss order (Kraken-compatible interface).
        For crypto, uses stop_limit since stop orders aren't supported.
        
        Args:
            symbol: Trading pair
            side: 'sell' for long positions
            quantity: Amount to sell when triggered
            stop_price: Price at which to trigger
            limit_price: Optional limit price after trigger
            
        Returns:
            Order response
        """
        symbol = self._resolve_symbol(symbol)
        # For crypto, stop orders aren't supported - use stop_limit
        is_crypto = "/" in symbol or symbol.endswith("USD") and len(symbol) > 5
        
        if is_crypto or limit_price:
            # Use stop_limit for crypto (required) or if limit specified
            lp = limit_price if limit_price else stop_price * 0.995  # 0.5% below stop
            return self.place_stop_limit_order(symbol, quantity, side, stop_price, lp)
        else:
            return self.place_stop_order(symbol, quantity, side, stop_price)

    def place_take_profit_order(self, symbol: str, side: str, quantity: float, take_profit_price: float, limit_price: float = None) -> Dict[str, Any]:
        """
        Place a take-profit order (Kraken-compatible interface).
        Uses limit order at the take-profit price.
        
        Args:
            symbol: Trading pair
            side: 'sell' for long positions
            quantity: Amount to sell
            take_profit_price: Price at which to take profit
            limit_price: Optional different limit price
            
        Returns:
            Order response
        """
        symbol = self._resolve_symbol(symbol)
        price = limit_price if limit_price else take_profit_price
        return self.place_limit_order(symbol, quantity, side, price)

    def place_order_with_tp_sl(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "market",
        price: float = None,
        take_profit: float = None,
        stop_loss: float = None,
        position_intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Place an order with attached Take-Profit and/or Stop-Loss (Kraken-compatible).
        Uses Alpaca's bracket order for atomic TP+SL, or OTO for single exit.
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell' for entry
            quantity: Amount
            order_type: 'market' or 'limit'
            price: Required if order_type is 'limit'
            take_profit: Take-profit price
            stop_loss: Stop-loss price
            
        Returns:
            Order response
        """
        symbol = self._resolve_symbol(symbol)
        if take_profit and stop_loss:
            # Both TP and SL -> use bracket order
            return self.place_bracket_order(
                symbol, quantity, side,
                entry_type=order_type,
                entry_limit_price=price,
                take_profit_limit=take_profit,
                stop_loss_stop=stop_loss,
                position_intent=position_intent,
            )
        elif take_profit or stop_loss:
            # Single exit -> use OTO order
            return self.place_oto_order(
                symbol, quantity, side,
                entry_type=order_type,
                entry_limit_price=price,
                take_profit_limit=take_profit,
                stop_loss_stop=stop_loss,
                position_intent=position_intent,
            )
        else:
            # No exits -> regular order
            if order_type == "limit" and price:
                return self.place_limit_order(symbol, quantity, side, price)
            return self.place_order(symbol, quantity, side, position_intent=position_intent)

    def get_asset(self, symbol: str) -> Dict[str, Any]:
        """Fetch asset metadata (shortable, marginable, etc.)."""
        raw = (symbol or '').strip().upper()
        if raw and '/' not in raw and raw.replace('.', '').replace('-', '').isalnum():
            symbol = raw
        else:
            symbol = self._resolve_symbol(symbol)
        return self._request("GET", f"/v2/assets/{symbol}")

    def is_shortable(self, symbol: str) -> bool:
        """Return True if asset is shortable for the account."""
        try:
            asset = self.get_asset(symbol) or {}
            return bool(asset.get("shortable"))
        except Exception:
            return False

    def open_position_with_tp_sl(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_pct: float = None,
        stop_loss_pct: float = None,
        entry_price: float = None,
        position_intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Open a long/short with optional TP/SL based on current price."""
        symbol = self._resolve_symbol(symbol)

        if entry_price is None:
            try:
                quotes = self.get_latest_crypto_quotes([symbol]) or {}
                quote = quotes.get(symbol, {})
                bp = float(quote.get("bp") or 0)
                ap = float(quote.get("ap") or 0)
                if bp > 0 and ap > 0:
                    entry_price = (bp + ap) / 2
            except Exception:
                entry_price = None

        take_profit_price = None
        stop_loss_price = None
        if entry_price:
            if take_profit_pct is not None:
                if side == "buy":
                    take_profit_price = entry_price * (1 + take_profit_pct / 100.0)
                else:
                    take_profit_price = entry_price * (1 - take_profit_pct / 100.0)
            if stop_loss_pct is not None:
                if side == "buy":
                    stop_loss_price = entry_price * (1 - stop_loss_pct / 100.0)
                else:
                    stop_loss_price = entry_price * (1 + stop_loss_pct / 100.0)

        return self.place_order_with_tp_sl(
            symbol=symbol,
            side=side,
            quantity=quantity,
            take_profit=take_profit_price,
            stop_loss=stop_loss_price,
            position_intent=position_intent,
        )

    def get_free_balance(self, asset: str) -> float:
        """
        Get free balance for an asset (Kraken-compatible interface).
        
        Args:
            asset: Asset symbol (e.g., 'BTC', 'USD')
            
        Returns:
            Free balance amount
        """
        try:
            if asset.upper() in ['USD', 'USDT', 'USDC']:
                acct = self.get_account()
                return float(acct.get('cash', 0) or 0)
            
            positions = self.get_positions()
            for pos in positions:
                norm = self._normalize_pair_symbol(pos.get('symbol', '')) or ''
                base = norm.split('/')[0] if '/' in norm else ''
                if base.upper() == asset.upper():
                    # Prefer qty_available when present (crypto fee/hold safe)
                    return float(pos.get('qty_available', pos.get('qty', 0)) or 0)
            return 0.0
        except:
            return 0.0

    def get_account_balance(self) -> Dict[str, float]:
        """
        Get all balances (Kraken-compatible interface).
        
        Returns:
            Dict of asset -> amount
        """
        if not self.is_authenticated:
            return {}
        balances = {}
        try:
            acct = self.get_account()
            cash = float(acct.get('cash', 0) or 0)
            if cash > 0:
                balances['USD'] = cash
            
            positions = self.get_positions()
            for pos in positions:
                qty = float(pos.get('qty_available', pos.get('qty', 0)) or 0)
                if qty > 0:
                    norm = self._normalize_pair_symbol(pos.get('symbol', '')) or ''
                    base = norm.split('/')[0] if '/' in norm else ''
                    balances[base] = qty
        except:
            pass
        return balances


    def get_balance(self) -> Dict[str, float]:
        """Alias for get_account_balance for cross-exchange compatible interface."""
        return self.get_account_balance()

    def get_stock_snapshot(self, symbol: str) -> Dict[str, Any]:
        """Return snapshot for a stock symbol (latest/daily bars)."""
        try:
            sym = symbol.upper()
            # Use data API endpoint for market data
            return self._request("GET", f"/v2/stocks/{sym}/snapshot", base_url=self.data_url, request_type='data') or {}
        except Exception as e:
            logger.error(f"Error getting Alpaca stock snapshot for {symbol}: {e}")
            return {}

    def get_stock_snapshots(self, symbols: List[str]) -> Dict[str, Any]:
        """
        Return snapshots for multiple stock symbols (BATCH REQUEST).
        Optimized for bulk data retrieval to avoid rate limits.
        """
        try:
            # Chunking handled by caller or simple join (URL length limits apply)
            results = {}
            # Split into chunks of 50 to be safe with URL length
            chunk_size = 50
            for i in range(0, len(symbols), chunk_size):
                chunk = symbols[i:i + chunk_size]
                syms_str = ",".join([s.upper() for s in chunk])
                # Use data API endpoint for market data
                resp = self._request("GET", "/v2/stocks/snapshots", params={"symbols": syms_str}, base_url=self.data_url, request_type='data')
                if resp and isinstance(resp, dict):
                    results.update(resp)
            return results
        except Exception as e:
            logger.error(f"Error getting Alpaca stock snapshots batch: {e}")
            return {}

    def get_latest_stock_quote(self, symbol: str) -> Dict[str, Any]:
        """Return a fresh two-sided stock quote with its provider timestamp."""
        resolved = str(symbol or "").strip().upper()
        if not resolved:
            return {
                "quote": {}, "data_status": "no_data", "truth_status": "no_data",
                "reason": "symbol_required", "generated_values": False,
            }
        response = self._request(
            "GET", f"/v2/stocks/{resolved}/quotes/latest",
            base_url=self.data_url, request_type="data",
        )
        raw_quote = response.get("quote") if isinstance(response, dict) else None
        quote = self._normalize_quote_observation(resolved, raw_quote)
        if quote is None:
            return {
                "quote": {}, "data_status": "no_data", "truth_status": "no_data",
                "reason": "fresh_two_sided_provider_quote_required", "generated_values": False,
            }
        return {
            "quote": quote, "data_status": "live", "truth_status": "real_observed",
            "provider_timestamp": quote["provider_timestamp"],
            "source_timestamp": quote["source_timestamp"], "generated_values": False,
        }

    def get_stock_bars(self, symbols: List[str], limit: int = 1) -> Dict[str, Any]:
        """Return valid provider stock bars without numeric substitution."""
        requested = [str(symbol or "").strip().upper() for symbol in symbols if str(symbol or "").strip()]
        if not requested:
            return {
                "bars": {}, "data_status": "no_data", "truth_status": "no_data",
                "reason": "symbols_required", "generated_values": False,
            }
        response = self._request(
            "GET", "/v2/stocks/bars/latest",
            params={"symbols": ",".join(requested), "limit": limit},
            base_url=self.data_url, request_type="data",
        )
        payload = response.get("bars") if isinstance(response, dict) else None
        verified_bars: Dict[str, List[Dict[str, Any]]] = {}
        if isinstance(payload, dict):
            for symbol, raw in payload.items():
                rows = raw if isinstance(raw, list) else [raw]
                verified = [
                    bar for item in rows
                    if (bar := self._normalize_bar_observation(str(symbol), item)) is not None
                ]
                if verified:
                    verified_bars[str(symbol)] = verified
        if not verified_bars:
            return {
                "bars": {}, "data_status": "no_data", "truth_status": "no_data",
                "reason": "provider_bars_missing_or_malformed", "generated_values": False,
            }
        return {
            "bars": verified_bars, "data_status": "live", "truth_status": "real_observed",
            "received_at": datetime.now(timezone.utc).isoformat(), "generated_values": False,
        }

    def get_24h_tickers(self) -> List[Dict[str, Any]]:
        """Derive 24-hour crypto metrics only from two provider-timestamped bars."""
        symbols = self.get_tradable_crypto_symbols()
        if not symbols:
            return []
        bars_response = self.get_crypto_bars(symbols, timeframe="1Day", limit=2)
        bars = bars_response.get("bars") if isinstance(bars_response, dict) else None
        if not isinstance(bars, dict):
            return []
        tickers: List[Dict[str, Any]] = []
        now = time.time()
        for symbol in symbols:
            data = bars.get(symbol)
            if not isinstance(data, list) or len(data) < 2:
                continue
            previous, latest = data[-2], data[-1]
            previous_close = self._finite_number(previous.get("c"), positive=True)
            close = self._finite_number(latest.get("c"), positive=True)
            volume = self._finite_number(latest.get("v"), nonnegative=True)
            source_timestamp = self._fresh_provider_timestamp(
                latest.get("source_timestamp"), max_age_seconds=172800.0, now=now,
            )
            if previous_close is None or close is None or volume is None or source_timestamp is None:
                continue
            tickers.append({
                "symbol": symbol.replace("/", ""),
                "lastPrice": str(close),
                "priceChangePercent": str(((close - previous_close) / previous_close) * 100.0),
                "quoteVolume": str(volume * close),
                "provider_timestamp": source_timestamp,
                "source_timestamp": source_timestamp,
                "data_status": "live",
                "truth_status": "real_derived",
                "generated_values": False,
            })
        return tickers

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Return a fresh two-sided quote; missing evidence remains no-data."""
        resolved = self._resolve_symbol(symbol)
        if "/" in resolved:
            quote = self.get_latest_crypto_quotes([resolved]).get(resolved)
        else:
            response = self.get_latest_stock_quote(resolved)
            quote = response.get("quote") if isinstance(response, dict) else None
        if not isinstance(quote, dict):
            return {
                "symbol": resolved,
                "price": None,
                "bid": None,
                "ask": None,
                "last": None,
                "provider_timestamp": None,
                "source_timestamp": None,
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "fresh_two_sided_provider_quote_required",
                "generated_values": False,
                "action_eligible": False,
            }
        bid = self._finite_number(quote.get("bp"), positive=True)
        ask = self._finite_number(quote.get("ap"), positive=True)
        provider_timestamp = self._fresh_provider_timestamp(
            quote.get("provider_timestamp") or quote.get("t"),
            max_age_seconds=self.quote_max_age_seconds,
        )
        if bid is None or ask is None or bid > ask or provider_timestamp is None:
            return {
                "symbol": resolved,
                "price": None,
                "bid": None,
                "ask": None,
                "last": None,
                "provider_timestamp": None,
                "source_timestamp": None,
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "fresh_two_sided_provider_quote_required",
                "generated_values": False,
                "action_eligible": False,
            }
        midpoint = (bid + ask) / 2.0
        return {
            "symbol": resolved,
            "price": midpoint,
            "bid": bid,
            "ask": ask,
            "last": {"price": midpoint, "source": "provider_quote_midpoint"},
            "provider_timestamp": provider_timestamp,
            "source_timestamp": provider_timestamp,
            "data_status": "live",
            "truth_status": "real_derived",
            "generated_values": False,
            "action_eligible": True,
            "raw": quote,
        }

    def convert_to_quote(self, asset: str, amount: float, quote: str) -> Optional[float]:
        """Convert using a fresh two-sided provider quote, or return no value."""
        source_asset = str(asset or "").strip().upper()
        quote_asset = str(quote or "").strip().upper()
        source_amount = self._finite_number(amount, nonnegative=True)
        if source_amount is None or not source_asset or not quote_asset:
            return None
        if source_asset == quote_asset:
            return source_amount
        symbol = self._resolve_symbol(f"{source_asset}/{quote_asset}")
        observation = self.get_latest_crypto_quotes([symbol]).get(symbol)
        if not isinstance(observation, dict):
            return None
        bid = self._finite_number(observation.get("bp"), positive=True)
        ask = self._finite_number(observation.get("ap"), positive=True)
        source_timestamp = self._fresh_provider_timestamp(
            observation.get("provider_timestamp") or observation.get("t"),
            max_age_seconds=self.quote_max_age_seconds,
        )
        if bid is None or ask is None or bid > ask or source_timestamp is None:
            return None
        return source_amount * ((bid + ask) / 2.0)

    def get_available_pairs(self, base: str = None, quote: str = None) -> List[Dict[str, Any]]:
        """
        Get available trading pairs, optionally filtered by base or quote asset.

        Note: Alpaca crypto pairs are typically USD-quoted but this helper
        normalizes any quote currency returned by the API (USD, USDT, USDC, etc.).
        
        Args:
            base: Filter by base asset (e.g., 'BTC', 'ETH')
            quote: Filter by quote asset (e.g., 'USD')
            
        Returns:
            List of pairs with base, quote, and pair name
        """
        try:
            assets = self.get_assets(status='active', asset_class='crypto') or []
            results = []

            for asset in assets:
                if not asset.get('tradable'):
                    continue

                normalized = self._normalize_pair_symbol(asset.get('symbol', ''))
                if not normalized:
                    continue

                pair_base, pair_quote = normalized.split('/')
                if base and pair_base.upper() != base.upper():
                    continue
                if quote and pair_quote.upper() != quote.upper():
                    continue

                min_qty = asset.get('min_order_size') or asset.get('min_trade_increment') or 0
                min_notional = asset.get('min_trade_increment') or 0

                results.append({
                    "pair": normalized,
                    "base": pair_base,
                    "quote": pair_quote,
                    "min_qty": float(min_qty),
                    "min_notional": float(min_notional)
                })

            return results
        except Exception as e:
            logger.error(f"Error getting Alpaca pairs: {e}")
            return []

    def find_conversion_path(self, from_asset: str, to_asset: str) -> List[Dict[str, Any]]:
        """
        Find the best path to convert from one asset to another.
        
        Note: Alpaca supports USD pairs and select BTC-quoted pairs.
        
        Args:
            from_asset: Source asset (e.g., 'BTC')
            to_asset: Target asset (e.g., 'ETH')
            
        Returns:
            List of {pair, side, description} for each trade needed
        """
        from_asset = from_asset.upper()
        to_asset = to_asset.upper()
        
        if from_asset == to_asset:
            return []
        
        pairs = self.get_available_pairs()
        pair_bases = {p["base"].upper() for p in pairs}
        pair_quotes = {(p["base"].upper(), p["quote"].upper()) for p in pairs}
        
        # If converting to/from USD, single trade
        if from_asset == 'USD':
            if (to_asset, 'USD') in pair_quotes:
                return [{
                    "pair": f"{to_asset}/USD",
                    "side": "buy",
                    "description": f"Buy {to_asset} with USD",
                    "from": "USD",
                    "to": to_asset
                }]
            return []
        
        if to_asset == 'USD':
            if (from_asset, 'USD') in pair_quotes:
                return [{
                    "pair": f"{from_asset}/USD",
                    "side": "sell",
                    "description": f"Sell {from_asset} for USD",
                    "from": from_asset,
                    "to": "USD"
                }]
            return []

        # BTC-quoted direct pairs
        if from_asset == 'BTC' and (to_asset, 'BTC') in pair_quotes:
            return [{
                "pair": f"{to_asset}/BTC",
                "side": "buy",
                "description": f"Buy {to_asset} with BTC",
                "from": "BTC",
                "to": to_asset
            }]

        if to_asset == 'BTC' and (from_asset, 'BTC') in pair_quotes:
            return [{
                "pair": f"{from_asset}/BTC",
                "side": "sell",
                "description": f"Sell {from_asset} for BTC",
                "from": from_asset,
                "to": "BTC"
            }]
        
        # Both are crypto - prefer USD bridge
        if (from_asset, 'USD') in pair_quotes and (to_asset, 'USD') in pair_quotes:
            return [
                {
                    "pair": f"{from_asset}/USD",
                    "side": "sell",
                    "description": f"Sell {from_asset} for USD",
                    "from": from_asset,
                    "to": "USD"
                },
                {
                    "pair": f"{to_asset}/USD",
                    "side": "buy",
                    "description": f"Buy {to_asset} with USD",
                    "from": "USD",
                    "to": to_asset
                }
            ]

        # Fallback: USD -> BTC -> asset when BTC-quote exists
        if (from_asset, 'USD') in pair_quotes and (to_asset, 'BTC') in pair_quotes and ('BTC', 'USD') in pair_quotes:
            return [
                {
                    "pair": f"{from_asset}/USD",
                    "side": "sell",
                    "description": f"Sell {from_asset} for USD",
                    "from": from_asset,
                    "to": "USD"
                },
                {
                    "pair": "BTC/USD",
                    "side": "buy",
                    "description": "Buy BTC with USD",
                    "from": "USD",
                    "to": "BTC"
                },
                {
                    "pair": f"{to_asset}/BTC",
                    "side": "buy",
                    "description": f"Buy {to_asset} with BTC",
                    "from": "BTC",
                    "to": to_asset
                }
            ]

    def convert_crypto(
        self,
        from_asset: str,
        to_asset: str,
        amount: float,
        use_quote_amount: bool = False,
    ) -> Dict[str, Any]:
        """Build a provider-grounded route without implicitly submitting its hops."""
        source_asset = str(from_asset or "").strip().upper()
        target_asset = str(to_asset or "").strip().upper()
        source_amount = self._finite_number(amount, positive=True)
        if source_amount is None or not source_asset or not target_asset:
            return {
                "status": "not_submitted",
                "data_status": "no_data",
                "reason": "positive_amount_and_assets_required",
                "submitted": False,
                "generated_values": False,
            }
        if source_asset == target_asset:
            return {
                "status": "not_submitted",
                "data_status": "no_data",
                "reason": "source_and_target_assets_must_differ",
                "submitted": False,
                "generated_values": False,
            }
        path = self.find_conversion_path(source_asset, target_asset)
        if not path:
            return {
                "status": "not_submitted",
                "data_status": "no_data",
                "reason": "provider_conversion_path_unavailable",
                "from_asset": source_asset,
                "to_asset": target_asset,
                "submitted": False,
                "generated_values": False,
            }

        projected_amount = source_amount
        price_evidence: List[Dict[str, Any]] = []
        for index, trade in enumerate(path):
            pair = str(trade.get("pair") or "")
            side = str(trade.get("side") or "").strip().lower()
            quote = self.get_latest_crypto_quotes([pair]).get(pair)
            if not isinstance(quote, dict):
                return {
                    "status": "not_submitted",
                    "data_status": "no_data",
                    "reason": "fresh_two_sided_provider_quote_required",
                    "failed_step": index,
                    "pair": pair,
                    "submitted": False,
                    "generated_values": False,
                }
            bid = self._finite_number(quote.get("bp"), positive=True)
            ask = self._finite_number(quote.get("ap"), positive=True)
            timestamp = self._fresh_provider_timestamp(
                quote.get("provider_timestamp") or quote.get("t"),
                max_age_seconds=self.quote_max_age_seconds,
            )
            if bid is None or ask is None or bid > ask or timestamp is None:
                return {
                    "status": "not_submitted",
                    "data_status": "no_data",
                    "reason": "fresh_two_sided_provider_quote_required",
                    "failed_step": index,
                    "pair": pair,
                    "submitted": False,
                    "generated_values": False,
                }
            if side == "sell":
                projected_amount *= bid
                projected_price = bid
            elif side == "buy":
                projected_amount /= ask
                projected_price = ask
            else:
                return {
                    "status": "not_submitted",
                    "data_status": "no_data",
                    "reason": "conversion_side_invalid",
                    "failed_step": index,
                    "pair": pair,
                    "submitted": False,
                    "generated_values": False,
                }
            price_evidence.append({
                "pair": pair,
                "side": side,
                "price": projected_price,
                "provider_timestamp": timestamp,
                "source_timestamp": timestamp,
                "truth_status": "real_observed",
                "generated_values": False,
            })

        return {
            "dryRun": bool(self.dry_run),
            "status": "not_submitted",
            "data_status": "not_submitted",
            "truth_status": "real_derived",
            "reason": (
                "dry_run"
                if self.dry_run
                else "explicit_per_hop_order_authority_and_terminal_receipts_required"
            ),
            "from_asset": source_asset,
            "to_asset": target_asset,
            "requested_amount": source_amount,
            "projected_amount": projected_amount,
            "path": path,
            "price_evidence": price_evidence,
            "use_quote_amount": bool(use_quote_amount),
            "submitted": False,
            "fill_receipt_complete": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "generated_values": False,
        }

    def get_convertible_assets(self) -> Dict[str, List[str]]:
        """
        Get all crypto assets that can be converted.
        
        Note: Alpaca only supports USD pairs, so all conversions go through USD.
        
        Returns:
            Dict mapping each asset to list of assets it can convert to
        """
        pairs = self.get_available_pairs()
        
        # All crypto can convert to USD and to each other (via USD)
        crypto_assets = set()
        for p in pairs:
            crypto_assets.add(p["base"].upper())
        
        conversions = {"USD": sorted(crypto_assets)}
        
        for asset in crypto_assets:
            # Can convert to USD directly, or to any other crypto via USD
            targets = {"USD"} | (crypto_assets - {asset})
            conversions[asset] = sorted(targets)
        
        return conversions
    # ══════════════════════════════════════════════════════════════════════
    # 🦙💰 EXTENDED FEE & COST TRACKING METHODS
    # ══════════════════════════════════════════════════════════════════════

    def get_all_crypto_pairs_extended(self) -> List[Dict[str, Any]]:
        """
        Get ALL crypto pairs with extended metadata.
        
        Returns list with:
        - symbol: Trading pair (e.g., 'BTC/USD')
        - base: Base asset (e.g., 'BTC')
        - quote: Quote asset (e.g., 'USD')
        - min_order_size: Minimum order quantity
        - min_trade_increment: Minimum trade increment
        - price_increment: Price tick size
        - fractionable: Whether fractional trading is supported
        - status: Active/inactive
        """
        assets = self.get_assets(status='active', asset_class='crypto')
        if not assets:
            return []
        
        pairs = []
        for asset in assets:
            if not asset.get('tradable'):
                continue
            
            symbol = asset.get('symbol', '')
            normalized = self._normalize_pair_symbol(symbol)
            if not normalized or '/' not in normalized:
                continue
            
            base, quote = normalized.split('/')
            
            pairs.append({
                'symbol': normalized,
                'base': base,
                'quote': quote,
                'min_order_size': float(asset.get('min_order_size', 0) or 0),
                'min_trade_increment': float(asset.get('min_trade_increment', 0) or 0),
                'price_increment': float(asset.get('price_increment', 0) or 0),
                'fractionable': asset.get('fractionable', False),
                'marginable': asset.get('marginable', False),
                'shortable': asset.get('shortable', False),
                'status': asset.get('status', 'unknown'),
                'exchange': asset.get('exchange', 'ALPACA'),
                'id': asset.get('id', ''),
                'name': asset.get('name', symbol)
            })
        
        logger.info(f"🦙 Found {len(pairs)} tradeable crypto pairs")
        return pairs

    def get_account_activities(
        self, 
        activity_types: str = None,
        date: str = None,
        after: str = None,
        until: str = None,
        direction: str = 'desc',
        page_size: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get account activities with filtering.
        
        Activity types:
        - FILL: Order fills
        - CFEE: Crypto fees
        - FEE: Other fees
        - DIV: Dividends
        - TRANS: Transfers
        - etc.
        
        Args:
            activity_types: Comma-separated activity types (e.g., 'FILL,CFEE')
            date: Filter to specific date (YYYY-MM-DD)
            after: Filter after this datetime
            until: Filter until this datetime
            direction: 'asc' or 'desc'
            page_size: Max results (max 100)
        """
        params = {
            'direction': direction,
            'page_size': page_size
        }
        
        if activity_types:
            params['activity_types'] = activity_types
        if date:
            params['date'] = date
        if after:
            params['after'] = after
        if until:
            params['until'] = until
        
        result = self._request("GET", "/v2/account/activities", params=params)
        return result if isinstance(result, list) else []

    def get_crypto_fees(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get crypto fee activities (CFEE) for the specified period.
        
        Returns list of fee records with qty, price, symbol.
        """
        from datetime import datetime, timedelta
        
        after = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        
        return self.get_account_activities(
            activity_types='CFEE,FEE',
            after=after,
            page_size=100
        )

    def get_trading_volume(self, days: int = 30) -> Dict[str, Any]:
        """Aggregate provider fill activity without inferring a fee tier or currency."""
        from datetime import timedelta

        period_days = int(days) if isinstance(days, int) and days > 0 else 30
        start = datetime.now(timezone.utc) - timedelta(days=period_days)
        fills = self.get_account_activities(
            activity_types="FILL",
            after=start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            page_size=100,
        )
        totals_by_currency: Dict[str, float] = {}
        by_symbol: Dict[str, Dict[str, Any]] = {}
        verified_count = 0
        now = time.time()
        for fill in fills if isinstance(fills, list) else []:
            activity_id = self._valid_provider_identifier(fill.get("id") or fill.get("ref_id"))
            order_id = self._valid_provider_identifier(fill.get("order_id"))
            qty = self._finite_number(fill.get("qty"), positive=True)
            price = self._finite_number(fill.get("price"), positive=True)
            symbol = str(fill.get("symbol") or "").strip().upper()
            timestamp_raw = fill.get("transaction_time") or fill.get("executed_at") or fill.get("at")
            timestamp = self._provider_timestamp_epoch(timestamp_raw)
            if (
                activity_id is None
                or order_id is None
                or qty is None
                or price is None
                or not symbol
                or timestamp is None
                or timestamp < start.timestamp()
                or timestamp > now + self.provider_future_skew_seconds
            ):
                continue
            resolved = self._resolve_symbol(symbol)
            currency = str(fill.get("currency") or "").strip().upper()
            if not currency and "/" in resolved:
                currency = resolved.split("/", 1)[1]
            if not currency:
                continue
            notional = qty * price
            totals_by_currency[currency] = totals_by_currency.get(currency, 0.0) + notional
            row = by_symbol.setdefault(
                symbol,
                {"notional": 0.0, "currency": currency, "trade_count": 0},
            )
            if row["currency"] != currency:
                continue
            row["notional"] += notional
            row["trade_count"] += 1
            verified_count += 1
        if verified_count == 0:
            return {
                "total_notional_by_currency": {},
                "trade_count": None,
                "by_symbol": {},
                "fee_tier": None,
                "period_days": period_days,
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "provider_fill_activities_with_currency_required",
                "generated_values": False,
            }
        return {
            "total_notional_by_currency": totals_by_currency,
            "trade_count": verified_count,
            "by_symbol": by_symbol,
            "fee_tier": None,
            "period_days": period_days,
            "data_status": "live",
            "truth_status": "real_derived",
            "reason": "provider_fee_tier_not_supplied",
            "generated_values": False,
        }

    def get_orderbook(self, symbol: str) -> Dict[str, Any]:
        """
        Get real-time orderbook for a crypto symbol.
        
        Returns:
        - a: Ask array [{p: price, s: size}, ...]
        - b: Bid array [{p: price, s: size}, ...]
        - t: Timestamp
        """
        symbol = self._normalize_pair_symbol(symbol) or symbol
        
        params = {'symbols': symbol}
        result = self._request(
            "GET",
            "/v1beta3/crypto/us/latest/orderbooks",
            params=params,
            base_url=self.data_url
        )
        
        orderbooks = result.get('orderbooks', result) if isinstance(result, dict) else {}
        return orderbooks.get(symbol, {})

    def get_crypto_orderbook(self, symbol: str, depth: Optional[int] = None) -> Dict[str, Any]:
        """Compatibility wrapper: return Alpaca crypto orderbook with standardized keys.

        - Fetches the full orderbook payload Alpaca provides (no server-side truncation).
        - If `depth` is provided, trims bids/asks client-side.

        Returns keys:
        - symbol, t (timestamp)
        - bids / asks (also includes original a/b)
        """
        resolved = self._normalize_pair_symbol(symbol) or symbol
        ob = self.get_orderbook(resolved) or {}

        asks = ob.get('a', []) or []
        bids = ob.get('b', []) or []

        # Trim client-side if requested
        if depth is not None:
            try:
                d = max(0, int(depth))
            except (TypeError, ValueError):
                d = 0
            if d > 0:
                asks = asks[:d]
                bids = bids[:d]

        # Standardize keys expected by other modules
        out: Dict[str, Any] = dict(ob)
        out['symbol'] = resolved
        out['asks'] = asks
        out['bids'] = bids
        return out

    def get_spread(self, symbol: str) -> Dict[str, Any]:
        """Return a spread only from fresh, two-sided provider evidence."""
        resolved = self._normalize_pair_symbol(symbol) or str(symbol)
        orderbook = self.get_orderbook(resolved)
        if isinstance(orderbook, dict):
            bids = orderbook.get("b")
            asks = orderbook.get("a")
            source_timestamp = self._fresh_provider_timestamp(
                orderbook.get("t"),
                max_age_seconds=self.quote_max_age_seconds,
            )
            if isinstance(bids, list) and bids and isinstance(asks, list) and asks and source_timestamp is not None:
                raw_bid = bids[0].get("p") if isinstance(bids[0], dict) else bids[0][0] if isinstance(bids[0], (list, tuple)) and bids[0] else None
                raw_ask = asks[0].get("p") if isinstance(asks[0], dict) else asks[0][0] if isinstance(asks[0], (list, tuple)) and asks[0] else None
                bid = self._finite_number(raw_bid, positive=True)
                ask = self._finite_number(raw_ask, positive=True)
                if bid is not None and ask is not None and bid <= ask:
                    midpoint = (bid + ask) / 2.0
                    spread = ask - bid
                    return {
                        "bid": bid,
                        "ask": ask,
                        "mid": midpoint,
                        "spread_abs": spread,
                        "spread_pct": (spread / midpoint) * 100.0,
                        "provider_timestamp": source_timestamp,
                        "source_timestamp": source_timestamp,
                        "source_type": "provider_orderbook",
                        "data_status": "live",
                        "truth_status": "real_derived",
                        "generated_values": False,
                    }

        quote = self.get_latest_crypto_quotes([resolved]).get(resolved)
        if isinstance(quote, dict):
            bid = self._finite_number(quote.get("bp"), positive=True)
            ask = self._finite_number(quote.get("ap"), positive=True)
            source_timestamp = self._fresh_provider_timestamp(
                quote.get("provider_timestamp") or quote.get("t"),
                max_age_seconds=self.quote_max_age_seconds,
            )
            if bid is not None and ask is not None and bid <= ask and source_timestamp is not None:
                midpoint = (bid + ask) / 2.0
                spread = ask - bid
                return {
                    "bid": bid,
                    "ask": ask,
                    "mid": midpoint,
                    "spread_abs": spread,
                    "spread_pct": (spread / midpoint) * 100.0,
                    "provider_timestamp": source_timestamp,
                    "source_timestamp": source_timestamp,
                    "source_type": "provider_quote",
                    "data_status": "live",
                    "truth_status": "real_derived",
                    "generated_values": False,
                }
        return {
            "bid": None,
            "ask": None,
            "mid": None,
            "spread_abs": None,
            "spread_pct": None,
            "provider_timestamp": None,
            "source_timestamp": None,
            "data_status": "no_data",
            "truth_status": "no_data",
            "reason": "fresh_two_sided_provider_spread_required",
            "generated_values": False,
        }

    def estimate_trade_cost(
        self,
        symbol: str,
        side: str,
        quantity: float,
        fee_tier: int = 1,
    ) -> Dict[str, Any]:
        """Expose quote-derived spread evidence but never invent a provider fee."""
        del fee_tier
        side_normalized = str(side or "").strip().lower()
        order_quantity = self._finite_number(quantity, positive=True)
        spread = self.get_spread(symbol)
        if (
            side_normalized not in {"buy", "sell"}
            or order_quantity is None
            or spread.get("data_status") != "live"
        ):
            return {
                "symbol": symbol,
                "side": side_normalized,
                "quantity": order_quantity,
                "exec_price": None,
                "mid_price": None,
                "notional": None,
                "fee": None,
                "fee_currency": None,
                "spread_cost": None,
                "total_cost": None,
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "fresh_provider_spread_and_valid_order_request_required",
                "eligible_for_accounting": False,
                "generated_values": False,
            }
        execution_price = spread["ask"] if side_normalized == "buy" else spread["bid"]
        midpoint = float(spread["mid"])
        notional = order_quantity * float(execution_price)
        spread_cost = order_quantity * abs(float(execution_price) - midpoint)
        return {
            "symbol": symbol,
            "side": side_normalized,
            "quantity": order_quantity,
            "exec_price": execution_price,
            "mid_price": midpoint,
            "notional": notional,
            "fee": None,
            "fee_currency": None,
            "spread_cost": spread_cost,
            "total_cost": None,
            "provider_timestamp": spread["provider_timestamp"],
            "source_timestamp": spread["source_timestamp"],
            "data_status": "no_data",
            "truth_status": "real_derived",
            "reason": "provider_fee_receipt_required_for_total_cost",
            "indicative_only": True,
            "eligible_for_accounting": False,
            "generated_values": False,
        }

    def get_full_account_summary(self) -> Dict[str, Any]:
        """Return provider account data without zero or fee-tier substitution."""
        account = self.get_account()
        positions = self.get_positions()
        volume = self.get_trading_volume(days=30)
        recent_fees = self.get_crypto_fees(days=7)
        received_at = datetime.now(timezone.utc).isoformat()

        account_values = {}
        for field in (
            "cash",
            "portfolio_value",
            "equity",
            "buying_power",
            "non_marginable_buying_power",
        ):
            account_values[field] = self._finite_number(account.get(field))
        account_live = (
            isinstance(account, dict)
            and self._valid_provider_identifier(account.get("id")) is not None
            and all(value is not None for value in account_values.values())
        )
        normalized_positions: List[Dict[str, Any]] = []
        for position in positions if isinstance(positions, list) else []:
            values = {
                "qty": self._finite_number(position.get("qty")),
                "avg_entry_price": self._finite_number(position.get("avg_entry_price"), positive=True),
                "market_value": self._finite_number(position.get("market_value")),
                "unrealized_pl": self._finite_number(position.get("unrealized_pl")),
                "unrealized_plpc": self._finite_number(position.get("unrealized_plpc")),
            }
            if not str(position.get("symbol") or "").strip() or any(value is None for value in values.values()):
                continue
            normalized_positions.append({
                "symbol": position.get("symbol"),
                **values,
                "truth_status": "real_observed",
                "generated_values": False,
            })

        verified_fee_activities = []
        for activity in recent_fees if isinstance(recent_fees, list) else []:
            activity_id = self._valid_provider_identifier(activity.get("id") or activity.get("ref_id"))
            qty = self._finite_number(activity.get("qty"))
            price = self._finite_number(activity.get("price"), positive=True)
            if activity_id is None or qty is None or price is None:
                continue
            verified_fee_activities.append({
                "id": activity_id,
                "activity_type": activity.get("activity_type"),
                "symbol": activity.get("symbol"),
                "qty": qty,
                "price": price,
                "currency": activity.get("currency"),
                "date": activity.get("date"),
                "truth_status": "real_observed",
                "generated_values": False,
            })
        return {
            "account": {
                "id": account.get("id") if account_live else None,
                "status": account.get("status") if account_live else None,
                "cash": account_values.get("cash") if account_live else None,
                "portfolio_value": account_values.get("portfolio_value") if account_live else None,
                "equity": account_values.get("equity") if account_live else None,
                "buying_power": account_values.get("buying_power") if account_live else None,
                "crypto_buying_power": (
                    account_values.get("non_marginable_buying_power") if account_live else None
                ),
                "data_status": "live" if account_live else "no_data",
                "truth_status": "real_observed" if account_live else "no_data",
                "received_at": received_at,
                "generated_values": False,
            },
            "positions": normalized_positions,
            "trading_volume": volume,
            "fees_7d": {
                "activities": verified_fee_activities,
                "total": None,
                "currency": None,
                "count": len(verified_fee_activities),
                "data_status": "live" if verified_fee_activities else "no_data",
                "reason": "provider_fee_currency_required_for_total",
                "generated_values": False,
            },
            "fee_tier": None,
            "data_status": (
                "live"
                if account_live and volume.get("data_status") == "live"
                else "no_data"
            ),
            "truth_status": "real_observed" if account_live else "no_data",
            "received_at": received_at,
            "generated_values": False,
        }

    def start_market_data_hub(self):
        """Start the MarketDataHub prefetching service."""
        if self._market_data_hub:
            try:
                try:
                    from aureon.data_feeds.market_data_hub import start_market_data_hub
                except ImportError:
                    from aureon.data_feeds.market_data_hub import start_market_data_hub
                start_market_data_hub(self)
                logger.info("MarketDataHub started for Alpaca client")
            except Exception as e:
                logger.error(f"Failed to start MarketDataHub: {e}")

    def stop_market_data_hub(self):
        """Stop the MarketDataHub prefetching service."""
        try:
            try:
                from aureon.data_feeds.market_data_hub import stop_market_data_hub
            except ImportError:
                from aureon.data_feeds.market_data_hub import stop_market_data_hub
            stop_market_data_hub()
            logger.info("MarketDataHub stopped")
        except Exception as e:
            logger.error(f"Failed to stop MarketDataHub: {e}")

    def get_market_data_hub_stats(self) -> Dict[str, Any]:
        """Get MarketDataHub statistics."""
        if self._market_data_hub:
            return self._market_data_hub.get_stats()
        return {"error": "MarketDataHub not available"}

    def get_global_rate_budget_stats(self) -> Dict[str, Any]:
        """Get GlobalRateBudget statistics."""
        if self._global_rate_budget:
            return self._global_rate_budget.get_stats()
        return {"error": "GlobalRateBudget not available"}


# ─── Singleton factory (mirrors get_binance_client / get_kraken_client) ───────
_alpaca_client_instance = None
_alpaca_client_lock = None


def get_alpaca_client() -> 'AlpacaClient':
    """
    Return the singleton AlpacaClient instance.

    Thread-safe lazy initialisation — only one connection is created regardless
    of how many modules import this helper.

    Returns:
        AlpacaClient instance, or None if credentials are missing.
    """
    global _alpaca_client_instance, _alpaca_client_lock
    if _alpaca_client_lock is None:
        import threading
        _alpaca_client_lock = threading.Lock()
    if _alpaca_client_instance is None:
        with _alpaca_client_lock:
            if _alpaca_client_instance is None:
                try:
                    _alpaca_client_instance = AlpacaClient()
                    import logging as _lg
                    _lg.getLogger(__name__).info('🦙 Alpaca singleton client initialized')
                except Exception as e:
                    import logging as _lg
                    _lg.getLogger(__name__).warning(f'⚠️ Alpaca client unavailable: {e}')
                    return None
    return _alpaca_client_instance
