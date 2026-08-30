import os, time, json, hmac, hashlib, base64, threading, logging, math
from pathlib import Path
from typing import Dict, Any, List, Tuple
from decimal import Decimal

from aureon.governance.economic_boundary import (
    EconomicGovernanceBlocked,
    _claim_economic_transport_context,
    _economic_transport_body_digest,
)

# Cross-process file locking for the Kraken nonce counter.
# - POSIX: fcntl.flock
# - Windows: msvcrt.locking (byte-range lock)
try:
    import fcntl  # type: ignore
except Exception:  # pragma: no cover - Windows
    fcntl = None  # type: ignore
    try:
        import msvcrt  # type: ignore
    except Exception:  # pragma: no cover
        msvcrt = None  # type: ignore

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    requests = None  # type: ignore
    HTTPAdapter = None  # type: ignore
    Retry = None  # type: ignore

# Load environment variables from the shared Aureon env policy.
try:
    from aureon.core.aureon_env import load_aureon_environment
    load_aureon_environment(Path(__file__).resolve().parents[2], override=False)
except Exception:
    pass

KRAKEN_BASE = "https://api.kraken.com"

ASSETPAIR_CACHE_TTL = 300  # seconds
KRAKEN_TRADES_PAGE_SIZE = 50
KRAKEN_FILL_RECEIPT_MAX_AGE_SECONDS = 300.0

_KRAKEN_TRANSPORT_OWNED_FIELDS = frozenset({"nonce"})
_KRAKEN_ORDER_MUTATION_ACTIONS = frozenset(
    {
        "addorder",
        "addorderbatch",
        "amendorder",
        "editorder",
        "cancelorder",
        "cancelorderbatch",
        "cancelall",
        "cancelallordersafter",
    }
)
_KRAKEN_FUND_MUTATION_ACTIONS = frozenset(
    {
        "withdraw",
        "withdrawcancel",
        "wallettransfer",
        "accounttransfer",
        "transfer",
        "stake",
        "unstake",
    }
)
_KRAKEN_EARN_MUTATION_ROUTES = frozenset(
    {
        "earn/allocate",
        "earn/deallocate",
    }
)
_KRAKEN_CANONICAL_MUTATION_PATHS = frozenset(
    {
        "/0/private/AddOrder",
        "/0/private/AddOrderBatch",
        "/0/private/AmendOrder",
        "/0/private/EditOrder",
        "/0/private/CancelOrder",
        "/0/private/CancelOrderBatch",
        "/0/private/CancelAll",
        "/0/private/CancelAllOrdersAfter",
        "/0/private/Withdraw",
        "/0/private/WithdrawCancel",
        "/0/private/WalletTransfer",
        "/0/private/AccountTransfer",
        "/0/private/Transfer",
        "/0/private/Stake",
        "/0/private/Unstake",
        "/0/private/Earn/Allocate",
        "/0/private/Earn/Deallocate",
    }
)

_KRAKEN_SENTINEL_IDS = frozenset({
    "unknown",
    "none",
    "null",
    "dry_run",
    "dry_run_id",
    "dryrun",
    "mock",  # sentinel rejected as no_data
    "mock_order",
    "test",
    "test_order",
})

logger = logging.getLogger(__name__)


def _is_kraken_economic_mutation_path(path: object) -> bool:
    """Identify Kraken private routes that can change orders or funds."""

    if not isinstance(path, str):
        return False
    route = path.split("?", 1)[0].rstrip("/")
    prefix = "/0/private/"
    if not route.casefold().startswith(prefix):
        return False
    action = route[len(prefix):].casefold()
    return (
        action in _KRAKEN_ORDER_MUTATION_ACTIONS
        or action in _KRAKEN_FUND_MUTATION_ACTIONS
        or action in _KRAKEN_EARN_MUTATION_ROUTES
    )


def _finite_decimal(
    value: Any,
    *,
    positive: bool = False,
    nonnegative: bool = False,
) -> Decimal | None:
    """Parse an observed numeric value without substituting a fallback."""
    if value is None or isinstance(value, bool):
        return None
    try:
        observed = Decimal(str(value).strip())
    except Exception:
        return None
    if not observed.is_finite():
        return None
    if positive and observed <= 0:
        return None
    if nonnegative and observed < 0:
        return None
    return observed


def _decimal_text(value: Any) -> str | None:
    """Return the provider numeric value as a validated decimal string."""
    observed = _finite_decimal(value)
    if observed is None:
        return None
    return format(observed, "f")


def _valid_kraken_id(value: Any) -> str | None:
    """Return a non-sentinel provider identifier, otherwise no data."""
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    normalized = candidate.lower().replace("-", "_").replace(" ", "_")
    if not candidate or normalized in _KRAKEN_SENTINEL_IDS:
        return None
    if normalized.startswith(("dry_run", "mock_", "test_")):
        return None
    return candidate


def _valid_kraken_client_order_id(value: Any) -> str | None:
    """Accept only the deterministic short-UUID form used by S5."""
    if not isinstance(value, str):
        return None
    candidate = value.strip().lower()
    if len(candidate) != 32:
        return None
    if any(character not in "0123456789abcdef" for character in candidate):
        return None
    return candidate


def _add_order_txid(result: Any) -> str | None:
    """Extract the single txid Kraken documents for an AddOrder receipt."""
    if not isinstance(result, dict):
        return None
    txids = result.get("txid")
    if not isinstance(txids, (list, tuple)) or len(txids) != 1:
        return None
    return _valid_kraken_id(txids[0])


def _fresh_provider_timestamp(
    value: Any,
    *,
    now: float | None = None,
    max_age_seconds: float = KRAKEN_FILL_RECEIPT_MAX_AGE_SECONDS,
) -> float | None:
    """Validate Kraken time; local receipt time is never a substitute."""
    observed = _finite_decimal(value, positive=True)
    if observed is None:
        return None
    try:
        timestamp = float(observed)
    except (OverflowError, ValueError):
        return None
    if timestamp > 10_000_000_000:
        timestamp /= 1000.0
    checked_at = time.time() if now is None else now
    age_seconds = checked_at - timestamp
    if age_seconds < -30.0 or age_seconds > max_age_seconds:
        return None
    return timestamp


def _deterministic_receipt_id(prefix: str, payload: Dict[str, Any]) -> str:
    """Hash provider evidence without including a local receipt clock."""
    material = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return f"{prefix}:" + hashlib.sha256(material.encode("utf-8")).hexdigest()

# Import TokenBucket for proper rate limiting
try:
    from aureon.core.rate_limiter import TokenBucket
    _RATE_LIMITER_AVAILABLE = True
except ImportError:
    _RATE_LIMITER_AVAILABLE = False

# ─── Kraken Rate Limit Tiers ──────────────────────────────────────────
# Kraken uses a decaying counter model. Each private API call adds to the
# counter; it decays at a fixed rate depending on verification tier.
#   Starter:      max 15, decay 0.33/sec → sustain ~1 call / 3s
#   Intermediate: max 20, decay 0.5 /sec → sustain ~1 call / 2s
#   Pro:          max 20, decay 1.0 /sec → sustain ~1 call / 1s
# Matching orders add 0 (limit) or 1 (market). Ledger/TradesHistory add 2.
# Public endpoints have a separate, looser limit (~1 call/sec sustained).
KRAKEN_TIER = os.getenv("KRAKEN_TIER", "starter").lower()  # starter|intermediate|pro

_TIER_SETTINGS: Dict[str, Dict[str, float]] = {
    "starter":      {"capacity": 15, "decay": 0.33, "private_interval": 2.0, "page_interval": 4.0},
    "intermediate": {"capacity": 20, "decay": 0.50, "private_interval": 1.5, "page_interval": 3.0},
    "pro":          {"capacity": 20, "decay": 1.00, "private_interval": 1.0, "page_interval": 2.0},
}
_TIER = _TIER_SETTINGS.get(KRAKEN_TIER, _TIER_SETTINGS["starter"])

# 🔐 CROSS-PROCESS NONCE MANAGER
# Prevents "Invalid nonce" errors when multiple processes share the same API key
# Uses file-based atomic counter with locking
_DEFAULT_NONCE_FILE = os.path.join(os.path.dirname(__file__) or '.', '.kraken_nonce')
# Prefer a stable per-instance state path when provided (Docker/Windows-friendly).
NONCE_FILE = os.getenv("KRAKEN_NONCE_PATH") or _DEFAULT_NONCE_FILE
_nonce_lock = threading.Lock()
_nonce_offset_counter = 0


def _next_nonce_offset() -> int:
    """Small deterministic offset used only to separate same-microsecond nonces."""
    global _nonce_offset_counter
    _nonce_offset_counter = (_nonce_offset_counter % 999) + 1
    return _nonce_offset_counter

def _lock_file(handle) -> None:
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        return
    if 'msvcrt' in globals() and msvcrt is not None:
        # Ensure file has at least one byte so we can lock a range.
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write("0")
                handle.flush()
        except Exception:
            pass
        handle.seek(0)
        # Lock the first byte. This blocks until acquired.
        msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        return

def _unlock_file(handle) -> None:
    if fcntl is not None:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return
    if 'msvcrt' in globals() and msvcrt is not None:
        try:
            handle.seek(0)
        except Exception:
            pass
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass

def _read_nonce_text(text: str) -> int:
    text = (text or "").strip()
    if not text:
        return 0
    if text.startswith("{"):
        try:
            payload = json.loads(text)
            return int(payload.get("nonce") or 0)
        except Exception:
            return 0
    try:
        return int(text)
    except Exception:
        return 0

def _get_next_nonce() -> int:
    """Get next nonce that's guaranteed higher than any previous nonce.
    
    Uses file-based atomic counter with locking to ensure:
    1. Nonces always increase (even across process restarts)
    2. Multiple parallel processes don't collide
    3. Recovers gracefully if nonce file is corrupted
    """
    with _nonce_lock:
        # Kraken remembers the highest nonce ever observed for an API key.
        # This key has historically been used by Aureon clients with
        # nanosecond nonces, so falling back to microseconds permanently
        # strands every authenticated request below that provider high-water.
        current_ns = time.time_ns()
        
        try:
            # Try to read existing nonce from file (with locking)
            if os.path.exists(NONCE_FILE):
                with open(NONCE_FILE, 'r+') as f:
                    _lock_file(f)
                    try:
                        last_nonce = _read_nonce_text(f.read())
                    except Exception:
                        last_nonce = 0
                    
                    # New nonce = max(current_time, last_nonce + 1) plus a
                    # deterministic offset for same-nanosecond calls.
                    new_nonce = max(current_ns, last_nonce + 1) + _next_nonce_offset()
                    
                    # Write back atomically
                    f.seek(0)
                    f.truncate()
                    f.write(str(new_nonce))
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        pass
                    _unlock_file(f)
                    return new_nonce
            else:
                # Create new nonce file
                new_nonce = current_ns + _next_nonce_offset()
                with open(NONCE_FILE, 'w+') as f:
                    _lock_file(f)
                    f.write(str(new_nonce))
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except Exception:
                        pass
                    _unlock_file(f)
                return new_nonce
                
        except Exception:
            # Fallback: use time + PID + deterministic offset.
            return current_ns + (os.getpid() % 10000) * 1000 + _next_nonce_offset()

class KrakenClient:
    """
    Minimal Kraken REST client exposing a Binance-like interface expected by the
    Aureon orchestrators. Designed for dry-run use by default; private/signed
    endpoints are stubbed unless keys are configured and dry_run is disabled.
    """

    def __init__(self):
        # API keys (optional in dry-run)
        self.api_key = os.getenv("KRAKEN_API_KEY", "")
        self.api_secret = os.getenv("KRAKEN_API_SECRET", "")
        # Kraken has no public testnet for spot; keep flag for parity
        self.use_testnet = False
        # Dry-run - default FALSE for live trading
        self.dry_run = os.getenv("KRAKEN_DRY_RUN", "false").lower() == "true"

        self.base = KRAKEN_BASE
        self.session = requests.Session()
        
        # Configure HTTPAdapter with connection pooling and SSL/TLS stability improvements
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            # A transport retry of AddOrder can duplicate a mutation after an
            # ambiguous timeout/5xx. Private POSTs surface to their durable
            # caller; only explicit Kraken rejection payloads retry below.
            allowed_methods=["GET"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10,
            pool_block=False
        )
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        
        if self.api_key:
            self.session.headers.update({"API-Key": self.api_key})

        self._pairs_cache: Dict[str, Any] = {}
        self._pairs_cache_time: float = 0.0
        # Map altname -> internal pair key used by ticker results
        self._alt_to_int: Dict[str, str] = {}
        self._int_to_alt: Dict[str, str] = {}
        
        # ── Rate Limiting (production-grade) ──────────────────────────────
        # Private API: token bucket mirroring Kraken's decaying counter model
        self._private_lock = threading.Lock()
        self._last_private_call: float = 0.0
        self._min_call_interval: float = _TIER["private_interval"]
        # Heavier interval for paginated endpoints (ledgers, trades history)
        self._page_call_interval: float = _TIER["page_interval"]

        if _RATE_LIMITER_AVAILABLE:
            # Private bucket: match Kraken tier capacity & decay rate
            self._private_bucket = TokenBucket(
                rate=_TIER["decay"],
                capacity=_TIER["capacity"],
                name="kraken_private",
            )
            # Public bucket: ~1 call/sec sustained, burst up to 15
            self._public_bucket = TokenBucket(
                rate=1.0,
                capacity=15.0,
                name="kraken_public",
            )
        else:
            self._private_bucket = None
            self._public_bucket = None
        
        # ── Response Caching (reduce redundant API calls) ─────────────────
        # Balance cache: 30s TTL — get_balance() is called 5+ times per Orca cycle
        self._balance_cache: Dict[str, Any] = {}
        self._balance_cache_time: float = 0.0
        self._balance_cache_ttl: float = 30.0
        # Backoff state for EAPI:Rate limit recovery
        self._rate_limit_backoff: float = 0.0
        self._rate_limit_until: float = 0.0
        self._consecutive_rate_limits: int = 0
        # A one-call capability independently protects the final HTTP seam.
        # It is consumed before the fake/real session can observe a mutation.
        self._economic_dispatch_lock = threading.RLock()
        self._economic_dispatches: dict[object, tuple[str, str, str]] = {}

    def _normalize_asset_name(self, asset: str) -> str:
        asset_up = (asset or "").upper()
        alias_map = {
            "XBT": "BTC",
            "XXBT": "BTC",
            "XDG": "DOGE",
            "XXDG": "DOGE",
            "XETH": "ETH",
            "XXETH": "ETH",
            "ZUSD": "USD",
            "ZEUR": "EUR",
            "ZGBP": "GBP",
            "ZCAD": "CAD",
        }
        if asset_up in alias_map:
            return alias_map[asset_up]
        if asset_up.startswith(("X", "Z")) and len(asset_up) > 3:
            return asset_up[1:]
        return asset_up

    def _pair_base_quote(self, pair: str) -> Tuple[str, str]:
        pairs = self._load_asset_pairs()
        internal = pair if pair in pairs else self._alt_to_int.get(pair) or self._alt_to_int.get(pair.upper())
        if not internal or internal not in pairs:
            return "", ""
        info = pairs[internal]
        base = self._normalize_asset_name(info.get("base", ""))
        quote = self._normalize_asset_name(info.get("quote", ""))
        return base, quote

    # ──────────────────────────────────────────────────────────────────────
    # Private signing helpers (only if we later enable non-dry-run)
    # ──────────────────────────────────────────────────────────────────────
    def _kraken_sign(self, url_path: str, data: Dict[str, Any]) -> str:
        # Kraken signature: HMAC-SHA512 of (url_path + SHA256(nonce+postdata)) with base64-decoded secret
        postdata = "".join([f"{k}={data[k]}&" for k in data]).rstrip("&")
        nonce = str(data.get("nonce", ""))
        message = (nonce + postdata).encode()
        sha256_hash = hashlib.sha256(message).digest()
        mac = hmac.new(base64.b64decode(self.api_secret), url_path.encode() + sha256_hash, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest()).decode()
        return sigdigest

    def _register_economic_dispatch(
        self,
        *,
        method: str,
        path: str,
        body_digest: str,
    ) -> object:
        dispatch = object()
        with self._economic_dispatch_lock:
            self._economic_dispatches[dispatch] = (method, path, body_digest)
        return dispatch

    def _discard_economic_dispatch(self, dispatch: object | None) -> None:
        if dispatch is None:
            return
        with self._economic_dispatch_lock:
            self._economic_dispatches.pop(dispatch, None)

    def _consume_economic_dispatch(
        self,
        dispatch: object | None,
        *,
        method: str,
        path: str,
        data: Dict[str, Any],
    ) -> None:
        with self._economic_dispatch_lock:
            state = self._economic_dispatches.pop(dispatch, None)
        if state is None:
            raise EconomicGovernanceBlocked(
                "signed_kraken_mutation_dispatch_capability_required"
            )
        if not isinstance(data, dict):
            raise EconomicGovernanceBlocked(
                "exact_kraken_mutation_body_required"
            )
        economic_body = dict(data)
        nonce = economic_body.pop("nonce", None)
        if not isinstance(nonce, str) or not nonce:
            raise EconomicGovernanceBlocked(
                "kraken_transport_owned_nonce_required"
            )
        try:
            observed = (
                method,
                path,
                _economic_transport_body_digest(economic_body),
            )
        except (TypeError, ValueError) as exc:
            raise EconomicGovernanceBlocked(
                "exact_kraken_mutation_body_required"
            ) from exc
        if observed != state:
            raise EconomicGovernanceBlocked(
                "exact_kraken_mutation_method_path_body_required"
            )

    def _private_http_post(
        self,
        path: str,
        *,
        data: Dict[str, Any],
        headers: Dict[str, str],
        timeout: int,
        _economic_dispatch: object | None = None,
    ):
        """Final authenticated POST seam; mutations require one exact capability."""

        is_mutation = _is_kraken_economic_mutation_path(path)
        if is_mutation:
            if path not in _KRAKEN_CANONICAL_MUTATION_PATHS:
                raise EconomicGovernanceBlocked(
                    "canonical_kraken_mutation_path_required"
                )
            if self.use_testnet:
                raise EconomicGovernanceBlocked(
                    "kraken_spot_testnet_mutation_unavailable"
                )
            if self.base != KRAKEN_BASE:
                raise EconomicGovernanceBlocked(
                    "canonical_kraken_live_endpoint_required"
                )
            self._consume_economic_dispatch(
                _economic_dispatch,
                method="POST",
                path=path,
                data=data,
            )
        elif _economic_dispatch is not None:
            raise EconomicGovernanceBlocked(
                "kraken_mutation_dispatch_on_read_only_request_forbidden"
            )
        url = f"{self.base}{path}"
        return self.session.post(
            url,
            data=data,
            headers=headers,
            timeout=timeout,
        )

    def _private(self, path: str, data: Dict[str, Any] = None, _cost: float = 1.0) -> Dict[str, Any]:
        """Execute a private (authenticated) Kraken API call with production-grade rate limiting.
        
        Args:
            path: API endpoint path (e.g. /0/private/Balance)
            data: POST data dict
            _cost: Rate limit cost — 1 for normal calls, 2 for ledger/trades queries
        """
        is_mutation = _is_kraken_economic_mutation_path(path)
        if self.dry_run:
            if is_mutation:
                raise EconomicGovernanceBlocked(
                    "dry_run_kraken_provider_mutation_forbidden"
                )
            raise RuntimeError("Private Kraken endpoint used in dry-run. Provide balances via env or disable dry-run.")
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Missing KRAKEN_API_KEY / KRAKEN_API_SECRET")

        request_data = dict(data or {})
        authorized_body_digest: str | None = None
        if is_mutation:
            if path not in _KRAKEN_CANONICAL_MUTATION_PATHS:
                raise EconomicGovernanceBlocked(
                    "canonical_kraken_mutation_path_required"
                )
            if self.use_testnet:
                raise EconomicGovernanceBlocked(
                    "kraken_spot_testnet_mutation_unavailable"
                )
            if self.base != KRAKEN_BASE:
                raise EconomicGovernanceBlocked(
                    "canonical_kraken_live_endpoint_required"
                )
            if _KRAKEN_TRANSPORT_OWNED_FIELDS.intersection(request_data):
                raise EconomicGovernanceBlocked(
                    "kraken_nonce_is_transport_owned"
                )
            authorized_body_digest = _claim_economic_transport_context(
                method="POST",
                path=path,
                body=request_data,
            )

        # A mutation permit authorizes exactly one provider request. Read-only
        # calls retain their existing bounded retry behaviour.
        max_retries = 1 if is_mutation else 3
        for attempt in range(max_retries):
            # Thread-safe rate limiting
            with self._private_lock:
                # 1. Check if we're in a backoff period from a previous rate limit error
                now = time.time()
                if now < self._rate_limit_until:
                    wait_time = self._rate_limit_until - now
                    logger.warning(f"Kraken rate limit backoff: waiting {wait_time:.1f}s")
                    time.sleep(wait_time)
                    now = time.time()
                
                # 2. TokenBucket gate — mirrors Kraken's decaying counter model
                if self._private_bucket:
                    self._private_bucket.wait(tokens=_cost)
                
                # 3. Minimum interval between calls (prevents nonce errors too)
                elapsed = now - self._last_private_call
                if elapsed < self._min_call_interval:
                    time.sleep(self._min_call_interval - elapsed)
                
                wire_data = dict(request_data)
                wire_data["nonce"] = str(_get_next_nonce())
                headers = {
                    "API-Key": self.api_key,
                    "API-Sign": self._kraken_sign(path, wire_data)
                }
                
                # Update last call time before making request
                self._last_private_call = time.time()
                
                dispatch: object | None = None
                if is_mutation:
                    if authorized_body_digest is None:
                        raise EconomicGovernanceBlocked(
                            "exact_kraken_mutation_body_required"
                        )
                    dispatch = self._register_economic_dispatch(
                        method="POST",
                        path=path,
                        body_digest=authorized_body_digest,
                    )
                try:
                    r = self._private_http_post(
                        path,
                        data=wire_data,
                        headers=headers,
                        timeout=15,
                        _economic_dispatch=dispatch,
                    )
                finally:
                    self._discard_economic_dispatch(dispatch)
                r.raise_for_status()
                res = r.json()
                
                errors = res.get("error", [])
                if errors:
                    error_str = str(errors)
                    # Handle rate limit errors with exponential backoff
                    if "EAPI:Rate limit exceeded" in error_str or "EGeneral:Too many requests" in error_str:
                        self._consecutive_rate_limits += 1
                        # Exponential backoff: 15s, 30s, 60s, 120s cap
                        backoff = min(15 * (2 ** (self._consecutive_rate_limits - 1)), 120)
                        self._rate_limit_until = time.time() + backoff
                        self._rate_limit_backoff = backoff
                        logger.warning(
                            f"Kraken RATE LIMIT on {path} (attempt {attempt+1}/{max_retries}). "
                            f"Backing off {backoff}s (consecutive: {self._consecutive_rate_limits})"
                        )
                        if attempt < max_retries - 1:
                            time.sleep(backoff)
                            continue  # Retry
                        else:
                            raise RuntimeError(f"Kraken error: {errors}")
                    
                    # Handle invalid nonce (retry with fresh nonce)
                    if "EAPI:Invalid nonce" in error_str and attempt < max_retries - 1:
                        logger.warning(f"Kraken invalid nonce on {path}, retrying...")
                        time.sleep(0.5)
                        continue
                    
                    raise RuntimeError(f"Kraken error: {errors}")
                
                # Success — reset backoff state
                if self._consecutive_rate_limits > 0:
                    logger.info(f"Kraken rate limit recovered after {self._consecutive_rate_limits} consecutive limits")
                    self._consecutive_rate_limits = 0
                    self._rate_limit_backoff = 0.0
                
                # Invalidate balance cache after order/cancel operations
                if "AddOrder" in path or "CancelOrder" in path:
                    self._balance_cache = {}
                    self._balance_cache_time = 0.0
                
                return res.get("result", {})

    # ──────────────────────────────────────────────────────────────────────
    # Public helpers and Binance-like interface
    # ──────────────────────────────────────────────────────────────────────
    def _public_get(self, endpoint: str, params: Dict[str, Any] | None = None, timeout: int = 20) -> Dict[str, Any]:
        """Execute a public Kraken API call with rate limiting.
        
        All public GET requests should go through this method.
        """
        if self._public_bucket:
            self._public_bucket.wait(tokens=1.0)
        
        url = f"{self.base}{endpoint}"
        r = self.session.get(url, params=params, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if data.get("error"):
            error_str = str(data["error"])
            if "EAPI:Rate limit" in error_str or "EGeneral:Too many" in error_str:
                logger.warning(f"Kraken public rate limit on {endpoint}, waiting 5s...")
                time.sleep(5)
                # Retry once
                r = self.session.get(url, params=params, timeout=timeout)
                r.raise_for_status()
                data = r.json()
                if data.get("error"):
                    raise RuntimeError(f"Kraken error: {data['error']}")
            else:
                raise RuntimeError(f"Kraken error: {data['error']}")
        return data.get("result", {})

    def _load_asset_pairs(self, force: bool = False) -> Dict[str, Any]:
        if not force and time.time() - self._pairs_cache_time < ASSETPAIR_CACHE_TTL and self._pairs_cache:
            return self._pairs_cache
        pairs = self._public_get("/0/public/AssetPairs")
        self._pairs_cache = pairs
        self._pairs_cache_time = time.time()
        # Build alt<->internal maps
        self._alt_to_int = {}
        self._int_to_alt = {}
        for internal, info in pairs.items():
            alt = info.get("altname") or internal
            self._alt_to_int[alt] = internal
            self._int_to_alt[internal] = alt
        return pairs

    def get_ledgers(self, since: int | None = None, max_records: int = 1000) -> List[Dict[str, Any]]:
        if self.dry_run:
            return []
        data: Dict[str, Any] = {"ofs": 0}
        if since:
            data["start"] = int(since)
        ledgers: List[Dict[str, Any]] = []
        total = None
        page = 0
        while True:
            # Ledger queries cost 2 rate limit tokens per Kraken docs
            res = self._private("/0/private/Ledgers", data, _cost=2)
            page += 1
            batch = res.get("ledger", {}) or {}
            count = int(res.get("count", 0) or 0)
            if total is None:
                total = count
            for ledger_id, entry in batch.items():
                entry = dict(entry)
                entry["id"] = ledger_id
                entry["asset"] = self._normalize_asset_name(entry.get("asset", ""))
                ledgers.append(entry)
                if len(ledgers) >= max_records:
                    break
            if len(ledgers) >= max_records or not batch:
                break
            data["ofs"] += len(batch)
            if total is not None and data["ofs"] >= total:
                break
            # Extra delay between pages to avoid rate limit saturation
            time.sleep(self._page_call_interval)
        ledgers.sort(key=lambda x: x.get("time", 0))
        return ledgers

    def get_trades_history(self, since: int | None = None, max_records: int = 1000) -> List[Dict[str, Any]]:
        if self.dry_run:
            return []
        data: Dict[str, Any] = {"ofs": 0}
        if since:
            data["start"] = int(since)
        trades: List[Dict[str, Any]] = []
        total = None
        page = 0
        while True:
            # TradesHistory queries cost 2 rate limit tokens per Kraken docs
            res = self._private("/0/private/TradesHistory", data, _cost=2)
            page += 1
            batch = res.get("trades", {}) or {}
            count = int(res.get("count", 0) or 0)
            if total is None:
                total = count
            for trade_id, trade in batch.items():
                provider_trade_id = _valid_kraken_id(trade_id)
                pair = trade.get("pair") if isinstance(trade, dict) else None
                trade_type = trade.get("type") if isinstance(trade, dict) else None
                price = _finite_decimal(
                    trade.get("price") if isinstance(trade, dict) else None,
                    positive=True,
                )
                volume = _finite_decimal(
                    trade.get("vol") if isinstance(trade, dict) else None,
                    positive=True,
                )
                cost = _finite_decimal(
                    trade.get("cost") if isinstance(trade, dict) else None,
                    positive=True,
                )
                fee = _finite_decimal(
                    trade.get("fee") if isinstance(trade, dict) else None,
                    nonnegative=True,
                )
                provider_time = _finite_decimal(
                    trade.get("time") if isinstance(trade, dict) else None,
                    positive=True,
                )
                if (
                    provider_trade_id is None
                    or not isinstance(pair, str)
                    or not pair
                    or trade_type not in {"buy", "sell"}
                    or price is None
                    or volume is None
                    or cost is None
                    or fee is None
                    or provider_time is None
                ):
                    raise RuntimeError("Incomplete Kraken TradesHistory provider receipt")
                base, quote = self._pair_base_quote(pair)
                trades.append({
                    "id": provider_trade_id,
                    "pair": pair,
                    "base": base,
                    "quote": quote,
                    "type": trade_type,
                    "price": float(price),
                    "vol": float(volume),
                    "cost": float(cost),
                    "fee": float(fee),
                    "time": float(provider_time),
                    "truth_status": "real_observed",
                    "generated_values": False,
                })
                if len(trades) >= max_records:
                    break
            if len(trades) >= max_records or not batch:
                break
            data["ofs"] += len(batch)
            if total is not None and data["ofs"] >= total:
                break
            # Extra delay between pages to avoid rate limit saturation
            time.sleep(self._page_call_interval)
        trades.sort(key=lambda x: x["time"])
        return trades

    def _normalize_symbol(self, symbol: str) -> List[str]:
        """
        Generate Kraken-compatible alternative altnames for a given symbol.
        Handles BTC/XBT aliasing and quote currency fallbacks.
        """
        s = symbol.upper()
        alts: List[str] = [s]
        # BTC vs XBT
        if s.startswith("BTC"):
            alts.append("XBT" + s[3:])
        if s.startswith("XBT"):
            alts.append("BTC" + s[3:])
        # USDT/USDC/USD fallbacks
        for q in ["USDT", "USDC", "USD"]:
            if s.endswith(q):
                base = s[:-len(q)]
                for alt_q in ["USD", "USDC", "USDT"]:
                    alts.append(base + alt_q)
                break
        # EUR/GBP alt quotes
        for q in ["EUR", "GBP"]:
            if s.endswith(q):
                base = s[:-len(q)]
                alts.extend([base + "USD", base + "USDC", base + "USDT"])  # try USD family too
                break
        # Deduplicate order-preserving
        seen = set()
        out: List[str] = []
        for a in alts:
            if a not in seen:
                out.append(a)
                seen.add(a)
        return out

    def _resolve_pair(self, symbol: str) -> Tuple[str | None, Dict[str, Any] | None]:
        """
        Try to resolve a human-friendly symbol (e.g., 'PEPEUSD', 'ada/usdt')
        to Kraken's internal pair code and return the associated pair info.
        """
        pairs = self._load_asset_pairs()
        normalized = symbol.replace("/", "").upper()
        candidates = [normalized, *self._normalize_symbol(normalized)]

        # Include Kraken-style prefixed forms that sometimes appear in configs
        if normalized in self._int_to_alt:
            candidates.append(normalized)

        for cand in candidates:
            internal = self._alt_to_int.get(cand) or (cand if cand in pairs else None)
            if internal and internal in pairs:
                return internal, pairs[internal]
        return None, None

    def exchange_info(self, symbol: str | None = None) -> Dict[str, Any]:
        """
        Return a Binance-like exchangeInfo structure using Kraken AssetPairs.
        Only fields used by Aureon are populated.
        """
        pairs = self._load_asset_pairs()
        symbols = []
        wanted = None
        if symbol:
            # Kraken altname must be used; try to map from typical BINANCE-style like "ETHUSDC"
            wanted = symbol
        for internal, info in pairs.items():
            alt = info.get("altname") or internal
            if wanted and alt != wanted:
                continue
            wsname = info.get("wsname", "")  # e.g., "ETH/USDC"
            # Derive base/quote from altname if possible
            base_asset, quote_asset = None, None
            if isinstance(alt, str):
                # Try to split alt into [base][quote] by checking common quotes
                for q in ["USDC", "USDT", "USD", "EUR", "BTC", "ETH"]:
                    if alt.endswith(q):
                        base_asset = alt[:-len(q)]
                        quote_asset = q
                        break
            if not base_asset or not quote_asset:
                # Fallback from wsname like "ETH/USDC"
                if "/" in wsname:
                    base_asset, quote_asset = wsname.split("/")
                else:
                    continue

            lot_dec = int(info.get("lot_decimals", info.get("lot_decimals", 8)))
            step_size = 10 ** (-lot_dec)
            ordermin = info.get("ordermin")
            try:
                min_qty = float(ordermin) if ordermin is not None else step_size
            except Exception:
                min_qty = step_size

            # Cost min (quote notional); if missing, set sensible default like $5
            costmin = info.get("costmin")
            try:
                min_notional = float(costmin) if costmin is not None else 5.0
            except Exception:
                min_notional = 5.0

            symbols.append({
                "symbol": alt,
                "status": "TRADING",  # Kraken AssetPairs doesn't expose per-pair trading status consistently
                "baseAsset": base_asset,
                "quoteAsset": quote_asset,
                "filters": {
                    "LOT_SIZE": {"stepSize": str(step_size), "minQty": str(min_qty)},
                    "NOTIONAL": {"minNotional": str(min_notional)}
                }
            })
        return {"symbols": symbols}

    def get_symbol_filters(self, symbol: str) -> Dict[str, float]:
        """
        Get trading filters for a symbol (ordermin, lot_decimals, costmin).
        Returns dict with: min_qty, step_size, min_notional
        """
        _pairs = self._load_asset_pairs()
        _pair, pair_info = self._resolve_pair(symbol)
        if not pair_info:
            return {}
        
        lot_decimals = int(pair_info.get("lot_decimals", 8))
        step_size = 10 ** (-lot_decimals)
        
        ordermin = pair_info.get("ordermin")
        try:
            min_qty = float(ordermin) if ordermin is not None else step_size
        except Exception:
            min_qty = step_size
        
        costmin = pair_info.get("costmin")
        try:
            min_notional = float(costmin) if costmin is not None else 0.5
        except Exception:
            min_notional = 0.5
        
        return {
            "min_qty": min_qty,
            "step_size": step_size,
            "min_notional": min_notional,
            "lot_decimals": lot_decimals
        }

    def _ticker(self, altnames: List[str]) -> Dict[str, Any]:
        if not altnames:
            return {}
        # Kraken expects internal pair names, not altnames; map
        self._load_asset_pairs()
        
        internal_names = []
        for a in altnames:
            pair, _ = self._resolve_pair(a)
            if pair:
                internal_names.append(pair)
            # Else skip unknown pair to prevent API error
            
        if not internal_names:
            return {}

        # Batch request (Kraken accepts comma-separated list)
        pairs_param = ",".join(internal_names)
        result = self._public_get("/0/public/Ticker", params={"pair": pairs_param})
        # If empty result, try normalized alternatives once
        if not result and len(altnames) == 1:
            alts = self._normalize_symbol(altnames[0])
            internal_names = []
            for a in alts:
                if a in self._alt_to_int:
                    internal_names.append(self._alt_to_int[a])
            if internal_names:
                pairs_param = ",".join(internal_names)
                result = self._public_get("/0/public/Ticker", params={"pair": pairs_param})
        return result

    def get_24h_tickers(self) -> list:
        """
        Return a list of Binance-like 24h ticker dicts with fields:
        - symbol: altname like "ETHUSDC"
        - lastPrice, priceChangePercent, quoteVolume
        """
        pairs = self._load_asset_pairs()
        # Include *all* listed asset pairs to cover every Kraken market, including alt coins
        alts = sorted({info.get("altname") or internal for internal, info in pairs.items()})
        out = []
        # Batch in chunks of 40 with rate-limit-safe delay between chunks
        total_chunks = (len(alts) + 39) // 40
        for chunk_idx in range(total_chunks):
            i = chunk_idx * 40
            chunk = alts[i:i+40]
            try:
                result = self._ticker(chunk)
                provider_clock = self._public_get("/0/public/Time")
                source_timestamp = _fresh_provider_timestamp(
                    provider_clock.get("unixtime") if isinstance(provider_clock, dict) else None,
                    max_age_seconds=60.0,
                )
                if source_timestamp is None:
                    logger.warning(
                        "Kraken ticker chunk %s has no fresh provider clock receipt",
                        chunk_idx + 1,
                    )
                    continue
            except RuntimeError as e:
                if "Rate limit" in str(e):
                    logger.warning(f"Kraken 24h ticker rate limited at chunk {chunk_idx+1}/{total_chunks}, stopping")
                    break
                raise
            for internal, t in result.items():
                alt = self._int_to_alt.get(internal, internal)
                try:
                    closes = t["c"]
                    volumes = t["v"]
                    if not isinstance(closes, list) or not closes:
                        continue
                    if not isinstance(volumes, list) or len(volumes) < 2:
                        continue
                    last_decimal = _finite_decimal(closes[0], positive=True)
                    open_decimal = _finite_decimal(t["o"], positive=True)
                    volume_decimal = _finite_decimal(volumes[1], nonnegative=True)
                    if (
                        last_decimal is None
                        or open_decimal is None
                        or volume_decimal is None
                    ):
                        continue
                    last = float(last_decimal)
                    openp = float(open_decimal)
                    vol_base = float(volume_decimal)
                    change_pct = (last - openp) / openp * 100.0
                    quote_vol = last * vol_base
                    out.append({
                        "symbol": alt,
                        "lastPrice": str(last),
                        "priceChangePercent": str(change_pct),
                        "quoteVolume": str(quote_vol),
                        "source_id": "kraken:/0/public/Ticker+/0/public/Time",
                        "source_timestamp": source_timestamp,
                        "received_at": time.time(),
                        "timestamp_policy": "kraken_server_time_near_ticker_read",
                        "truth_status": "real_derived",
                        "generated_values": False,
                    })
                except Exception:
                    continue
        return out

    def get_24h_ticker(self, symbol: str) -> Dict[str, Any]:
        # Try symbol and normalized aliases
        candidates = self._normalize_symbol(symbol)
        res = self._ticker([candidates[0]])
        # Only one expected
        if not res:
            # Try other candidates
            for alt in candidates[1:]:
                res = self._ticker([alt])
                if res:
                    break
        if not res:
            return {}
        internal, t = next(iter(res.items()))
        closes = t.get("c")
        volumes = t.get("v")
        if not isinstance(closes, list) or not closes:
            return {}
        if not isinstance(volumes, list) or len(volumes) < 2:
            return {}
        last_decimal = _finite_decimal(closes[0], positive=True)
        open_decimal = _finite_decimal(t.get("o"), positive=True)
        volume_decimal = _finite_decimal(volumes[1], nonnegative=True)
        if (
            last_decimal is None
            or open_decimal is None
            or volume_decimal is None
        ):
            return {}
        provider_clock = self._public_get("/0/public/Time")
        source_timestamp = _fresh_provider_timestamp(
            provider_clock.get("unixtime") if isinstance(provider_clock, dict) else None,
            max_age_seconds=60.0,
        )
        if source_timestamp is None:
            return {}
        last = float(last_decimal)
        openp = float(open_decimal)
        vol_base = float(volume_decimal)
        change_pct = (last - openp) / openp * 100.0
        quote_vol = last * vol_base
        return {
            "symbol": self._int_to_alt.get(internal, symbol),
            "lastPrice": str(last),
            "priceChangePercent": str(change_pct),
            "quoteVolume": str(quote_vol),
            "price": last,
            "source_id": "kraken:/0/public/Ticker+/0/public/Time",
            "source_timestamp": source_timestamp,
            "received_at": time.time(),
            "timestamp_policy": "kraken_server_time_near_ticker_read",
            "truth_status": "real_derived",
            "generated_values": False,
        }

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Return bid/ask/last for a symbol in a Binance-like shape."""
        try:
            res = self._ticker([symbol]) or self._ticker(self._normalize_symbol(symbol))
            if not res:
                return {"symbol": symbol, "price": 0.0, "bid": 0.0, "ask": 0.0}

            _, t = next(iter(res.items()))
            last = float(t.get("c", [0])[0] or 0.0)
            bid = float(t.get("b", [last])[0] or last)
            ask = float(t.get("a", [last])[0] or last)
            return {
                "symbol": symbol,
                "price": last,
                "bid": bid,
                "ask": ask,
            }
        except Exception:
            return {"symbol": symbol, "price": 0.0, "bid": 0.0, "ask": 0.0}

    def get_ticker_receipt(self, symbol: str) -> Dict[str, Any]:
        """Return a complete, fresh, provider-observed ticker receipt or no_data.

        This is deliberately separate from the legacy ``get_ticker`` shape so
        receipt consumers never have to infer provenance from compatibility
        defaults.  Kraken's public ticker response has no per-ticker clock, so
        the provider's own Time endpoint is retained as a distinct near-read
        source timestamp; the local receipt time is never substituted for it.
        """
        def no_data(reason: str) -> Dict[str, Any]:
            return {
                "symbol": symbol,
                "data_status": "no_data",
                "truth_status": "no_data",
                "generated_values": False,
                "action": False,
                "accounting": False,
                "learning": False,
                "reason": reason,
            }

        try:
            result = self._ticker([symbol]) or self._ticker(self._normalize_symbol(symbol))
            if not isinstance(result, dict) or not result:
                return no_data("missing_provider_ticker")
            internal, raw = next(iter(result.items()))
            if not isinstance(raw, dict):
                return no_data("malformed_provider_ticker")
            closes = raw.get("c")
            bids = raw.get("b")
            asks = raw.get("a")
            volumes = raw.get("v")
            if (
                not isinstance(closes, list) or not closes
                or not isinstance(bids, list) or not bids
                or not isinstance(asks, list) or not asks
                or not isinstance(volumes, list) or len(volumes) < 2
            ):
                return no_data("incomplete_provider_book_or_ticker")
            last = _finite_decimal(closes[0], positive=True)
            bid = _finite_decimal(bids[0], positive=True)
            ask = _finite_decimal(asks[0], positive=True)
            open_price = _finite_decimal(raw.get("o"), positive=True)
            volume = _finite_decimal(volumes[1], nonnegative=True)
            if (
                last is None or bid is None or ask is None
                or open_price is None or volume is None or ask < bid
            ):
                return no_data("invalid_provider_book_or_ticker")
            provider_clock = self._public_get("/0/public/Time")
            received_at = time.time()
            source_timestamp = _fresh_provider_timestamp(
                provider_clock.get("unixtime") if isinstance(provider_clock, dict) else None,
                now=received_at,
                max_age_seconds=60.0,
            )
            if source_timestamp is None or source_timestamp > received_at + 5.0:
                return no_data("missing_or_stale_provider_clock")
            source_id = "kraken:/0/public/Ticker+/0/public/Time"
            ticker_payload_material = "|".join((
                str(internal),
                format(last, "f"),
                format(bid, "f"),
                format(ask, "f"),
                format(open_price, "f"),
                format(volume, "f"),
            ))
            ticker_input_id = "kraken_ticker_payload:" + hashlib.sha256(
                ticker_payload_material.encode("utf-8")
            ).hexdigest()
            clock_input_id = "kraken_time:" + hashlib.sha256(
                format(source_timestamp, ".6f").encode("utf-8")
            ).hexdigest()
            input_receipt_ids = [ticker_input_id, clock_input_id]
            receipt_material = "|".join((
                source_id,
                str(internal),
                format(source_timestamp, ".6f"),
                format(last, "f"),
                format(bid, "f"),
                format(ask, "f"),
                format(open_price, "f"),
                format(volume, "f"),
                *input_receipt_ids,
            ))
            return {
                "symbol": self._int_to_alt.get(internal, symbol),
                "price": float(last),
                "bid": float(bid),
                "ask": float(ask),
                "open_price": float(open_price),
                "volume_24h": float(volume),
                "change_pct": (float(last) - float(open_price)) / float(open_price) * 100.0,
                "provider": "kraken",
                "venue": "kraken",
                "provider_receipt_type": "Ticker+Time",
                "data_status": "live",
                "truth_status": "real_observed",
                "generated_values": False,
                "source_id": source_id,
                "source_timestamp": source_timestamp,
                "received_at": received_at,
                "receipt_id": "kraken_ticker:" + hashlib.sha256(receipt_material.encode("utf-8")).hexdigest(),
                "input_receipt_ids": input_receipt_ids,
                "action": False,
                "accounting": False,
                "learning": False,
            }
        except Exception as exc:
            logger.warning("Kraken ticker receipt unavailable for %s: %s", symbol, exc)
            return no_data("provider_ticker_receipt_error")

    def best_price(self, symbol: str) -> Dict[str, Any]:
        t = self.get_24h_ticker(symbol)
        return {"symbol": t.get("symbol", symbol), "price": t.get("lastPrice", "0")}

    def account(self) -> Dict[str, Any]:
        """
        In dry-run, synthesize balances from env vars like DRY_RUN_BALANCE_USDC, DRY_RUN_BALANCE_USD, etc.
        Otherwise, call private Balance (not enabled by default).
        """
        if self.dry_run:
            balances = []
            for asset in ["USDC", "USDT", "USD", "EUR", "BTC", "ETH"]:
                val = os.getenv(f"DRY_RUN_BALANCE_{asset}")
                if val is None:
                    # default to 0 for safety
                    free = 0.0
                else:
                    try:
                        free = float(val)
                    except Exception:
                        free = 0.0
                if free > 0:
                    balances.append({"asset": asset, "free": str(free), "locked": "0"})
            return {"balances": balances}
        # Check balance cache first (30s TTL — prevents hammering for repeated calls)
        now = time.time()
        if self._balance_cache and (now - self._balance_cache_time) < self._balance_cache_ttl:
            return self._balance_cache
        
        # Live API call
        result = self._private("/0/private/Balance", {})
        balances = []
        for asset, amt in result.items():
            try:
                free = float(amt)
            except Exception:
                free = 0.0
            # Kraken uses asset codes like XXBT, XETH, ZUSD -> map to standard symbols
            kraken_norm = {
                "XBT": "BTC", "XXBT": "BTC",
                "XETH": "ETH", "XLTC": "LTC",
                "XXRP": "XRP", "XXLM": "XLM",
                "XXDG": "DOGE", "XZEC": "ZEC",
                "XMLN": "MLN", "XREP": "REP",
                "XETC": "ETC", "XXMR": "XMR",
                "ZUSD": "USD", "ZEUR": "EUR",
                "ZGBP": "GBP", "ZCAD": "CAD",
                "ZJPY": "JPY", "ZAUD": "AUD",
                "ZKRW": "KRW",
            }
            norm = kraken_norm.get(asset, asset)
            balances.append({"asset": norm, "free": str(free), "locked": "0"})
        account_data = {"balances": balances}
        
        # Update cache
        self._balance_cache = account_data
        self._balance_cache_time = time.time()
        return account_data

    def get_account_balance(self) -> Dict[str, float]:
        """Return balances as a simple asset -> amount map (free+locked)."""
        try:
            acct = self.account()
        except Exception:
            return {}

        out: Dict[str, float] = {}
        for bal in acct.get("balances", []):
            try:
                free = float(bal.get("free", 0))
            except Exception:
                free = 0.0
            try:
                locked = float(bal.get("locked", 0))
            except Exception:
                locked = 0.0
            total = free + locked
            if total > 0:
                asset = bal.get("asset")
                if asset:
                    out[asset] = total
        return out

    def get_balance(self) -> Dict[str, float]:
        """Alias for get_account_balance for Alpaca-compatible interface."""
        return self.get_account_balance()

    def invalidate_balance_cache(self) -> None:
        """Force next get_balance() to make a live API call.
        Call this after placing/canceling orders."""
        self._balance_cache = {}
        self._balance_cache_time = 0.0

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Return current rate limit state for diagnostics."""
        status = {
            "tier": KRAKEN_TIER,
            "min_call_interval": self._min_call_interval,
            "page_call_interval": self._page_call_interval,
            "consecutive_rate_limits": self._consecutive_rate_limits,
            "backoff_seconds": self._rate_limit_backoff,
            "backoff_until": self._rate_limit_until,
            "in_backoff": time.time() < self._rate_limit_until,
        }
        if self._private_bucket:
            status["private_bucket_tokens"] = self._private_bucket._tokens
            status["private_bucket_capacity"] = self._private_bucket.capacity
        if self._public_bucket:
            status["public_bucket_tokens"] = self._public_bucket._tokens
            status["public_bucket_capacity"] = self._public_bucket.capacity
        return status

    def get_free_balance(self, asset: str) -> float:
        acct = self.account()
        for bal in acct.get("balances", []):
            if bal.get("asset") == asset:
                try:
                    return float(bal.get("free", 0))
                except Exception:
                    return 0.0
        return 0.0

    def _format_order_value(self, value: float | str | Decimal | None) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return format(Decimal(str(value)), 'f').rstrip('0').rstrip('.') or '0'

    def _order_receipt_shell(
        self,
        *,
        symbol: str | None,
        side: str | None,
        order_type: str | None,
        order_id: Any = None,
        requested_quantity: Any = None,
        requested_price: Any = None,
        client_order_id: Any = None,
    ) -> Dict[str, Any]:
        txid = _valid_kraken_id(order_id)
        cl_ord_id = _valid_kraken_client_order_id(client_order_id)
        return {
            "provider": "kraken",
            "venue": "kraken",
            "orderId": txid,
            "symbol": symbol,
            "side": side.upper() if isinstance(side, str) else None,
            "type": order_type.upper() if isinstance(order_type, str) else None,
            "requestedQty": _decimal_text(requested_quantity),
            "origQty": _decimal_text(requested_quantity),
            "requestedPrice": _decimal_text(requested_price),
            "cl_ord_id": cl_ord_id,
            "price": None,
            "executedQty": None,
            "filled_qty": None,
            "avgPrice": None,
            "filled_avg_price": None,
            "cummulativeQuoteQty": None,
            "filled_notional": None,
            "fee": None,
            "fee_asset": None,
            "fee_currency": None,
            "fills": None,
            "provider_timestamp": None,
            "source_timestamp": None,
            "source_id": None,
            "receipt_id": None,
            "input_receipt_ids": [],
            "fill_receipt_complete": False,
            "eligible_for_accounting": False,
            "eligible_for_learning": False,
            "eligible_for_action": False,
            "action": False,
            "accounting": False,
            "learning": False,
            "generated_values": False,
        }

    def _not_submitted_order_receipt(
        self,
        *,
        symbol: str | None,
        side: str | None,
        order_type: str | None,
        requested_quantity: Any = None,
        requested_price: Any = None,
        client_order_id: Any = None,
    ) -> Dict[str, Any]:
        receipt = self._order_receipt_shell(
            symbol=symbol,
            side=side,
            order_type=order_type,
            requested_quantity=requested_quantity,
            requested_price=requested_price,
            client_order_id=client_order_id,
        )
        receipt.update({
            "status": "not_submitted",
            "data_status": "not_submitted",
            "truth_status": "not_submitted",
            "submitted": False,
            "dryRun": True,
            "reconciliation_required": False,
            "reason": "dry_run_order_not_submitted",
        })
        return receipt

    def _submission_order_receipt(
        self,
        result: Any,
        *,
        symbol: str | None,
        side: str | None,
        order_type: str | None,
        requested_quantity: Any = None,
        requested_price: Any = None,
        client_order_id: Any = None,
    ) -> Dict[str, Any]:
        """Normalize AddOrder only as a submission acknowledgement."""
        txid = _add_order_txid(result)
        receipt = self._order_receipt_shell(
            symbol=symbol,
            side=side,
            order_type=order_type,
            order_id=txid,
            requested_quantity=requested_quantity,
            requested_price=requested_price,
            client_order_id=client_order_id,
        )
        receipt["received_at"] = time.time()
        receipt["provider_receipt_type"] = "AddOrder"
        receipt["receipt_id"] = _deterministic_receipt_id(
            "kraken_order_ack",
            {
                "provider_receipt_type": "AddOrder",
                "provider_result": result,
                "order_id": txid,
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "requested_quantity": _decimal_text(requested_quantity),
                "requested_price": _decimal_text(requested_price),
                "cl_ord_id": receipt["cl_ord_id"],
            },
        )
        if txid is None:
            receipt.update({
                "status": "pending_reconciliation",
                "data_status": "pending_reconciliation",
                "truth_status": "no_data",
                "submitted": None,
                "reconciliation_required": True,
                "reason": "missing_or_ambiguous_provider_txid",
                "source_id": None,
            })
            return receipt
        receipt.update({
            "status": "pending_reconciliation",
            "data_status": "pending_reconciliation",
            "truth_status": "real_observed",
            "submitted": True,
            "reconciliation_required": True,
            "reason": "terminal_provider_fill_receipt_required",
            "source_id": f"kraken:/0/private/AddOrder:{txid}",
        })
        return receipt

    def _normalize_order_receipt(
        self,
        order_id: Any,
        order: Any,
        *,
        provider_receipt_type: str,
        now: float | None = None,
    ) -> Dict[str, Any]:
        """Normalize QueryOrders/ClosedOrders without manufacturing fill data."""
        txid = _valid_kraken_id(order_id)
        if not isinstance(order, dict):
            order = None
        descr = order.get("descr") if order is not None else None
        if not isinstance(descr, dict):
            descr = {}
        pair = descr.get("pair") if isinstance(descr.get("pair"), str) else None
        side = descr.get("type") if isinstance(descr.get("type"), str) else None
        order_type = descr.get("ordertype") if isinstance(descr.get("ordertype"), str) else None
        requested_quantity = order.get("vol") if order is not None else None
        requested_price = descr.get("price")
        receipt = self._order_receipt_shell(
            symbol=pair,
            side=side,
            order_type=order_type,
            order_id=txid,
            requested_quantity=requested_quantity,
            requested_price=requested_price,
        )
        receipt.update({
            "provider_receipt_type": provider_receipt_type,
            "received_at": time.time(),
            "source_id": (
                f"kraken_order:/0/private/{provider_receipt_type}:{txid}"
                if txid else None
            ),
            "submitted": txid is not None,
            "reconciliation_required": True,
            "receipt_id": _deterministic_receipt_id(
                "kraken_order",
                {
                    "provider_receipt_type": provider_receipt_type,
                    "order_id": txid,
                    "provider_order": order,
                },
            ),
        })

        if txid is None:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "missing_or_sentinel_provider_txid",
            })
            return receipt
        if order is None:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "missing_provider_order_receipt",
            })
            return receipt

        provider_status = str(order.get("status") or "").strip().lower()
        receipt["provider_status"] = provider_status or None
        if provider_status in {"pending", "open"}:
            receipt.update({
                "status": "pending_reconciliation",
                "data_status": "pending_reconciliation",
                "truth_status": "real_observed",
                "reason": "terminal_provider_fill_receipt_required",
            })
            return receipt
        if provider_status not in {"closed", "canceled", "expired"}:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "unknown_or_nonterminal_provider_status",
            })
            return receipt

        provider_timestamp = _fresh_provider_timestamp(order.get("closetm"), now=now)
        filled_quantity = _finite_decimal(order.get("vol_exec"), nonnegative=True)
        if provider_timestamp is None:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "missing_or_stale_provider_close_timestamp",
            })
            return receipt
        if filled_quantity is None:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "missing_or_malformed_provider_filled_quantity",
            })
            return receipt

        if provider_status in {"canceled", "expired"} and filled_quantity == 0:
            receipt.update({
                "status": provider_status.upper(),
                "data_status": "live",
                "truth_status": "real_observed",
                "provider_timestamp": provider_timestamp,
                "source_timestamp": provider_timestamp,
                "reconciliation_required": False,
                "reason": "terminal_provider_receipt_without_fill",
            })
            return receipt

        if filled_quantity <= 0:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "terminal_receipt_has_no_observed_fill",
            })
            return receipt

        average_price = _finite_decimal(order.get("price"), positive=True)
        filled_cost = _finite_decimal(order.get("cost"), positive=True)
        observed_fee = _finite_decimal(order.get("fee"), nonnegative=True)
        raw_trade_ids = order.get("trades")
        trade_ids = []
        if isinstance(raw_trade_ids, (list, tuple)):
            for raw_trade_id in raw_trade_ids:
                trade_id = _valid_kraken_id(raw_trade_id)
                if trade_id is None or trade_id in trade_ids:
                    trade_ids = []
                    break
                trade_ids.append(trade_id)

        if average_price is None:
            reason = "missing_or_malformed_provider_average_price"
        elif filled_cost is None:
            reason = "missing_or_malformed_provider_filled_cost"
        elif observed_fee is None:
            reason = "missing_or_malformed_provider_fee"
        elif not trade_ids:
            reason = "missing_or_ambiguous_provider_trade_ids"
        else:
            reason = None
        if reason is not None:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": reason,
            })
            return receipt

        expected_cost = filled_quantity * average_price
        cost_tolerance = max(Decimal("0.00000001"), filled_cost * Decimal("0.001"))
        if abs(expected_cost - filled_cost) > cost_tolerance:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "inconsistent_provider_fill_cost_and_average_price",
            })
            return receipt

        requested = _finite_decimal(requested_quantity, positive=True)
        if requested is None:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "missing_or_malformed_provider_requested_quantity",
            })
            return receipt
        if filled_quantity > requested:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "provider_filled_quantity_exceeds_order_quantity",
            })
            return receipt

        fee_asset = None
        if pair:
            try:
                _base_asset, fee_asset = self._pair_base_quote(pair)
            except Exception:
                fee_asset = None
        if not fee_asset:
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "missing_provider_pair_metadata_for_fee_currency",
            })
            return receipt

        fully_filled = provider_status == "closed"
        if requested is not None and filled_quantity < requested:
            fully_filled = False
        fill_status = "FILLED" if fully_filled else "PARTIALLY_FILLED"
        input_receipt_ids = [f"kraken_trade:{trade_id}" for trade_id in trade_ids]
        receipt.update({
            "status": fill_status,
            "data_status": "live",
            "truth_status": "real_observed",
            "price": format(average_price, "f"),
            "executedQty": format(filled_quantity, "f"),
            "filled_qty": format(filled_quantity, "f"),
            "avgPrice": format(average_price, "f"),
            "filled_avg_price": format(average_price, "f"),
            "cummulativeQuoteQty": format(filled_cost, "f"),
            "filled_notional": format(filled_cost, "f"),
            "fee": format(observed_fee, "f"),
            "fee_asset": fee_asset,
            "fee_currency": fee_asset,
            "fills": [
                {
                    "tradeId": trade_id,
                    "source": f"kraken_{provider_receipt_type.lower()}",
                }
                for trade_id in trade_ids
            ],
            "provider_timestamp": provider_timestamp,
            "source_timestamp": provider_timestamp,
            "closedTime": provider_timestamp,
            "input_receipt_ids": input_receipt_ids,
            "fill_receipt_complete": fully_filled,
            "eligible_for_accounting": fully_filled,
            "eligible_for_learning": fully_filled,
            "eligible_for_action": False,
            "action": False,
            "accounting": fully_filled,
            "learning": fully_filled,
            "generated_values": False,
            "reconciliation_required": not fully_filled,
            "reason": (
                None if fully_filled
                else "terminal_partial_fill_requires_external_reconciliation"
            ),
        })
        return receipt

    def place_market_order(
        self,
        symbol: str,
        side: str,
        quantity: float | str | Decimal | None = None,
        quote_qty: float | str | Decimal | None = None,
        *,
        client_order_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        Submit a market order.

        AddOrder acknowledges submission only. Fill fields remain unavailable
        until get_order_status() observes a complete terminal provider receipt.
        """
        cl_ord_id = None
        if client_order_id is not None:
            cl_ord_id = _valid_kraken_client_order_id(client_order_id)
            if cl_ord_id is None:
                raise ValueError(
                    "client_order_id must be a 32-character hexadecimal value"
                )
        if self.dry_run:
            receipt = self._not_submitted_order_receipt(
                symbol=symbol,
                side=side,
                order_type="market",
                requested_quantity=quantity,
                client_order_id=cl_ord_id,
            )
            receipt["requestedQuoteQty"] = _decimal_text(quote_qty)
            return receipt
        
        # ═══ SAFETY NET: £50 GBP minimum trade value (≈ $63 USD at 1.27 GBP/USD) ═══
        # Aligned with the system-wide spot minimum — any buy below this is rejected.
        MIN_TRADE_USD = 63.0
        if side.lower() == 'buy':
            usd_value = 0.0
            if quote_qty:
                usd_value = float(quote_qty)
            elif quantity:
                try:
                    price_info = self.best_price(symbol)
                    usd_value = float(quantity) * float(price_info.get('price', 0))
                except Exception:
                    pass
            if 0 < usd_value < MIN_TRADE_USD:
                print(f"   🚫 KRAKEN SAFETY NET: Buy ${usd_value:.2f} < ${MIN_TRADE_USD} minimum for {symbol} — BLOCKED")
                return {"error": "below_minimum_trade_value", "symbol": symbol, "value": usd_value, "min": MIN_TRADE_USD}
        
        # Resolve pair and get pair info for validation across *all* Kraken markets
        pair, pair_info = self._resolve_pair(symbol)
        if not pair or not pair_info:
            raise RuntimeError(f"Unknown Kraken trading pair: {symbol}")
        
        ordermin = float(pair_info.get("ordermin", 0.0001))
        lot_decimals = int(pair_info.get("lot_decimals", 8))
        
        params = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": "market",
        }
        
        if quantity:
            vol = float(quantity) if not isinstance(quantity, float) else quantity
        elif quote_qty:
            # Estimate volume from quote quantity
            price_info = self.best_price(symbol)
            price = float(price_info.get("price", 0))
            if price <= 0:
                raise RuntimeError(f"Cannot estimate volume for quote_qty: price is {price}")
            vol = float(quote_qty) / price
        else:
            raise ValueError("Must provide quantity or quote_qty")
        
        # Round to lot_decimals
        vol = round(vol, lot_decimals)
        
        # Validate volume meets minimum
        if vol < ordermin:
            print(f"   ⚠️ Kraken volume {vol:.8f} < min {ordermin} for {symbol}, need larger trade")
            return {"error": "volume_minimum", "symbol": symbol, "volume": vol, "ordermin": ordermin}
        
        params["volume"] = self._format_order_value(vol)
        if cl_ord_id is not None:
            params["cl_ord_id"] = cl_ord_id

        res = self._private("/0/private/AddOrder", params)
        receipt = self._submission_order_receipt(
            res,
            symbol=symbol,
            side=side,
            order_type="market",
            requested_quantity=params.get("volume"),
            client_order_id=cl_ord_id,
        )
        receipt["requestedQuoteQty"] = _decimal_text(quote_qty)
        return receipt

    def convert_to_quote(self, asset: str, amount: float, quote: str) -> float:
        asset_up = asset.upper()
        quote_up = quote.upper()

        if asset_up == quote_up:
            return amount

        # Treat USD stables as 1:1 to avoid false "insufficient funds" from missing pairs
        stable_usd = {"USD", "USDC", "USDT"}
        if asset_up in stable_usd and quote_up in stable_usd:
            return amount

        pair = f"{asset_up}{quote_up}"
        inv_pair = f"{quote_up}{asset_up}"
        try:
            price_info = self.best_price(pair)
            price = float(price_info.get("price", 0))
            if price > 0:
                return amount * price
        except Exception:
            pass
        try:
            price_info = self.best_price(inv_pair)
            price = float(price_info.get("price", 0))
            if price > 0:
                return amount / price
        except Exception:
            pass
        return 0.0

    def get_trades_history_dict(self, start: int = None, end: int = None, ofs: int = 0) -> Dict[str, Any]:
        """Get trade history from Kraken.
        
        Returns dict of trades with entry prices, quantities, fees etc.
        Used to calculate real cost basis for positions.
        
        Kraken API: https://docs.kraken.com/rest/#tag/User-Data/operation/getTradeHistory
        """
        params = {"ofs": ofs}
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        try:
            # Kraken returns paginated results (default ~50 per call).
            # Aggregate pages by default so downstream cost-basis calculations
            # are based on full ledger-backed trade history.
            all_trades: Dict[str, Any] = {}
            page_size = 50
            max_pages = 200
            page = 0
            next_ofs = ofs

            while page < max_pages:
                page_params = dict(params)
                page_params["ofs"] = next_ofs
                # TradesHistory costs 2 rate limit tokens per Kraken docs
                result = self._private("/0/private/TradesHistory", page_params, _cost=2)
                trades = result.get("trades", {}) or {}

                if not trades:
                    break

                all_trades.update(trades)
                page += 1

                if len(trades) < page_size:
                    break

                next_ofs += len(trades)
                # Extra delay between pages to avoid rate limit saturation
                time.sleep(self._page_call_interval)

            return all_trades
        except Exception as e:
            print(f"⚠️ Failed to get Kraken trade history: {e}")
            return {}
    
    def calculate_cost_basis(self, symbol: str) -> Dict[str, Any]:
        """Calculate average cost basis for a symbol from trade history.
        
        Returns:
            {
                'symbol': str,
                'avg_entry_price': float,
                'total_quantity': float,
                'total_cost': float,
                'total_fees': float,
                'trade_count': int
            }
        """
        trades = self.get_trades_history_dict()
        if not trades:
            return None
        
        # Kraken uses different pair naming, normalize
        target_pairs = set()
        # Try various Kraken naming conventions
        base = symbol[:-3] if len(symbol) > 3 else symbol
        for quote in ['USD', 'USDC', 'USDT', 'EUR', 'GBP']:
            target_pairs.add(f"{base}{quote}")
            target_pairs.add(f"X{base}Z{quote}")
            target_pairs.add(f"XX{base}Z{quote}")
        
        total_qty = Decimal("0")
        total_cost = Decimal("0")
        total_fees = Decimal("0")
        buy_trades = 0
        
        for trade_id, trade in trades.items():
            if not isinstance(trade, dict) or _valid_kraken_id(trade_id) is None:
                return None
            pair = trade.get('pair')
            # Check if this trade matches our target symbol
            if not isinstance(pair, str) or (
                pair not in target_pairs and symbol not in pair
            ):
                continue
            
            trade_type = trade.get('type')
            qty = _finite_decimal(trade.get('vol'), positive=True)
            price = _finite_decimal(trade.get('price'), positive=True)
            fee = _finite_decimal(trade.get('fee'), nonnegative=True)
            if trade_type not in {'buy', 'sell'} or qty is None or price is None or fee is None:
                return None
            
            if trade_type == 'buy':
                total_qty += qty
                total_cost += qty * price
                total_fees += fee
                buy_trades += 1
            elif trade_type == 'sell':
                total_qty -= qty
                if total_qty > 0:
                    prior_quantity = total_qty + qty
                    if prior_quantity <= 0:
                        return None
                    avg_price = total_cost / prior_quantity
                    total_cost = total_qty * avg_price
        
        if total_qty <= 0 or buy_trades == 0:
            return None
        
        avg_entry = total_cost / total_qty
        
        return {
            'symbol': symbol,
            'avg_entry_price': float(avg_entry),
            'total_quantity': float(total_qty),
            'total_cost': float(total_cost),
            'total_fees': float(total_fees),
            'trade_count': buy_trades,
            'truth_status': 'real_derived',
            'generated_values': False,
        }

    def compute_order_fees_in_quote(
        self,
        order: Dict[str, Any],
        primary_quote: str,
    ) -> float | None:
        """Return only a verified provider fee already denominated in quote."""
        if (
            not isinstance(order, dict)
            or order.get("data_status") != "live"
            or order.get("fill_receipt_complete") is not True
            or order.get("eligible_for_accounting") is not True
        ):
            return None
        observed_fee = _finite_decimal(order.get("fee"), nonnegative=True)
        fee_asset = self._normalize_asset_name(
            str(order.get("fee_asset") or order.get("fee_currency") or "")
        )
        quote_asset = self._normalize_asset_name(primary_quote)
        if observed_fee is None or not fee_asset or fee_asset != quote_asset:
            return None
        return float(observed_fee)

    # ══════════════════════════════════════════════════════════════════════
    # ADVANCED ORDER TYPES - Limit, Stop-Loss, Take-Profit, Trailing Stop
    # ══════════════════════════════════════════════════════════════════════

    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float | str | Decimal,
        price: float | str | Decimal,
        post_only: bool = False,
        time_in_force: str = "GTC",
        reduce_only: bool = False
    ) -> Dict[str, Any]:
        """
        Place a limit order on Kraken.
        
        Args:
            symbol: Trading pair (e.g., 'ETHUSD', 'BTCUSDC')
            side: 'buy' or 'sell'
            quantity: Amount of base asset
            price: Limit price
            post_only: If True, order will only be maker (cancelled if would be taker)
            time_in_force: 'GTC' (good-til-cancelled), 'IOC' (immediate-or-cancel), 'GTD' (good-til-date)
            reduce_only: If True, only reduces existing position
            
        Returns:
            Binance-compatible order response
            
        Benefit: Maker fee 0.16% vs Taker fee 0.26% (40% savings with post_only)
        """
        if self.dry_run:
            receipt = self._not_submitted_order_receipt(
                symbol=symbol,
                side=side,
                order_type="limit",
                requested_quantity=quantity,
                requested_price=price,
            )
            receipt.update({"postOnly": post_only, "timeInForce": time_in_force})
            return receipt
        
        self._load_asset_pairs()
        pair = self._alt_to_int.get(symbol, symbol)
        
        params = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": "limit",
            "volume": self._format_order_value(quantity),
            "price": self._format_order_value(price),
        }
        
        # reduce_only is a top-level parameter, NOT an oflag
        if reduce_only:
            params["reduce_only"] = "true"

        # Order flags
        oflags = []
        if post_only:
            oflags.append("post")  # Post-only (maker) order
        if oflags:
            params["oflags"] = ",".join(oflags)

        # Time in force
        if time_in_force == "IOC":
            params["timeinforce"] = "IOC"
        elif time_in_force == "GTD":
            params["timeinforce"] = "GTD"
        # GTC is default, no param needed
        
        res = self._private("/0/private/AddOrder", params)
        receipt = self._submission_order_receipt(
            res,
            symbol=symbol,
            side=side,
            order_type="limit",
            requested_quantity=quantity,
            requested_price=price,
        )
        receipt.update({"postOnly": post_only, "timeInForce": time_in_force})
        return receipt

    def place_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float | str | Decimal,
        stop_price: float | str | Decimal,
        limit_price: float | str | Decimal | None = None
    ) -> Dict[str, Any]:
        """
        Place a stop-loss order on Kraken (server-side, executes even if bot offline).
        
        Args:
            symbol: Trading pair
            side: 'sell' for long positions, 'buy' for short positions
            quantity: Amount to sell/buy when triggered
            stop_price: Price at which the stop triggers
            limit_price: If provided, uses stop-loss-limit instead of stop-loss-market
            
        Returns:
            Order response
            
        CRITICAL: Unlike client-side stops, these execute on Kraken's servers!
        """
        if self.dry_run:
            receipt = self._not_submitted_order_receipt(
                symbol=symbol,
                side=side,
                order_type="stop_loss_limit" if limit_price else "stop_loss",
                requested_quantity=quantity,
                requested_price=limit_price,
            )
            receipt.update({
                "stopPrice": _decimal_text(stop_price),
                "limitPrice": _decimal_text(limit_price),
            })
            return receipt
        
        self._load_asset_pairs()
        pair = self._alt_to_int.get(symbol, symbol)
        
        # stop-loss = market order when triggered
        # stop-loss-limit = limit order when triggered
        order_type = "stop-loss-limit" if limit_price else "stop-loss"
        
        params = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": order_type,
            "volume": self._format_order_value(quantity),
            "price": self._format_order_value(stop_price),  # Trigger price
        }
        
        if limit_price:
            params["price2"] = self._format_order_value(limit_price)  # Limit price after trigger
        
        res = self._private("/0/private/AddOrder", params)
        receipt = self._submission_order_receipt(
            res,
            symbol=symbol,
            side=side,
            order_type="stop_loss_limit" if limit_price else "stop_loss",
            requested_quantity=quantity,
            requested_price=limit_price,
        )
        receipt.update({
            "stopPrice": _decimal_text(stop_price),
            "limitPrice": _decimal_text(limit_price),
        })
        return receipt

    def place_take_profit_order(
        self,
        symbol: str,
        side: str,
        quantity: float | str | Decimal,
        take_profit_price: float | str | Decimal,
        limit_price: float | str | Decimal | None = None
    ) -> Dict[str, Any]:
        """
        Place a take-profit order on Kraken (server-side, executes even if bot offline).
        
        Args:
            symbol: Trading pair
            side: 'sell' for long positions (take profit when price rises)
            quantity: Amount to sell when triggered
            take_profit_price: Price at which to take profit
            limit_price: If provided, uses take-profit-limit instead of market
            
        Returns:
            Order response
        """
        if self.dry_run:
            receipt = self._not_submitted_order_receipt(
                symbol=symbol,
                side=side,
                order_type="take_profit_limit" if limit_price else "take_profit",
                requested_quantity=quantity,
                requested_price=limit_price,
            )
            receipt.update({
                "takeProfitPrice": _decimal_text(take_profit_price),
                "limitPrice": _decimal_text(limit_price),
            })
            return receipt
        
        self._load_asset_pairs()
        pair = self._alt_to_int.get(symbol, symbol)
        
        order_type = "take-profit-limit" if limit_price else "take-profit"
        
        params = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": order_type,
            "volume": self._format_order_value(quantity),
            "price": self._format_order_value(take_profit_price),  # Trigger price
        }
        
        if limit_price:
            params["price2"] = self._format_order_value(limit_price)
        
        res = self._private("/0/private/AddOrder", params)
        receipt = self._submission_order_receipt(
            res,
            symbol=symbol,
            side=side,
            order_type="take_profit_limit" if limit_price else "take_profit",
            requested_quantity=quantity,
            requested_price=limit_price,
        )
        receipt.update({
            "takeProfitPrice": _decimal_text(take_profit_price),
            "limitPrice": _decimal_text(limit_price),
        })
        return receipt

    def place_trailing_stop_order(
        self,
        symbol: str,
        side: str,
        quantity: float | str | Decimal,
        trailing_offset: float | str | Decimal,
        offset_type: str = "percent"
    ) -> Dict[str, Any]:
        """
        Place a trailing stop order on Kraken.
        
        Args:
            symbol: Trading pair
            side: 'sell' for long positions (trails below price as it rises)
            quantity: Amount to sell when triggered
            trailing_offset: Distance from peak price
            offset_type: 'percent' (e.g., 2.0 = 2%) or 'absolute' (price units)
            
        Returns:
            Order response
            
        Example: 2% trailing stop on ETH at $3000 -> stop at $2940
                 If ETH rises to $3500 -> stop auto-adjusts to $3430
        """
        if self.dry_run:
            receipt = self._not_submitted_order_receipt(
                symbol=symbol,
                side=side,
                order_type="trailing_stop",
                requested_quantity=quantity,
            )
            receipt.update({
                "trailingOffset": _decimal_text(trailing_offset),
                "offsetType": offset_type,
            })
            return receipt
        
        self._load_asset_pairs()
        pair = self._alt_to_int.get(symbol, symbol)
        
        params = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": "trailing-stop",
            "volume": self._format_order_value(quantity),
        }
        
        # Kraken trailing stop uses price as the offset
        # For percentage, we need to prefix with + or - and %
        if offset_type == "percent":
            # Kraken format: "+2%" means trail 2% below (for sells)
            params["price"] = f"+{trailing_offset}%"
        else:
            # Absolute offset in price units
            params["price"] = f"+{self._format_order_value(trailing_offset)}"
        
        res = self._private("/0/private/AddOrder", params)
        receipt = self._submission_order_receipt(
            res,
            symbol=symbol,
            side=side,
            order_type="trailing_stop",
            requested_quantity=quantity,
        )
        receipt.update({
            "trailingOffset": _decimal_text(trailing_offset),
            "offsetType": offset_type,
        })
        return receipt

    def place_order_with_tp_sl(
        self,
        symbol: str,
        side: str,
        quantity: float | str | Decimal,
        order_type: str = "market",
        price: float | str | Decimal | None = None,
        take_profit: float | str | Decimal | None = None,
        stop_loss: float | str | Decimal | None = None
    ) -> Dict[str, Any]:
        """
        Place an order with attached Take-Profit and/or Stop-Loss (conditional close).
        
        This is atomic - the TP/SL orders are attached to the entry and only activate
        when the entry fills. If entry is cancelled, TP/SL are also cancelled.
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell' for entry
            quantity: Amount for entry order
            order_type: 'market' or 'limit' for entry
            price: Required if order_type is 'limit'
            take_profit: Price to take profit (optional)
            stop_loss: Price to stop loss (optional)
            
        Returns:
            Order response with attached conditional close orders
            
        Example:
            place_order_with_tp_sl('ETHUSD', 'buy', 1.0, 
                                   take_profit=3500, stop_loss=2800)
            # Buys 1 ETH, auto-sells at $3500 profit or $2800 loss
        """
        if self.dry_run:
            receipt = self._not_submitted_order_receipt(
                symbol=symbol,
                side=side,
                order_type=order_type,
                requested_quantity=quantity,
                requested_price=price,
            )
            receipt.update({
                "takeProfit": _decimal_text(take_profit),
                "stopLoss": _decimal_text(stop_loss),
                "conditionalClose": True,
            })
            return receipt
        
        self._load_asset_pairs()
        pair = self._alt_to_int.get(symbol, symbol)
        
        params = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": order_type.lower(),
            "volume": self._format_order_value(quantity),
        }
        
        if order_type.lower() == "limit" and price:
            params["price"] = self._format_order_value(price)
        
        # Conditional close order - opposite side when entry fills
        close_side = "sell" if side.lower() == "buy" else "buy"
        
        if take_profit and stop_loss:
            # Use stop-loss with take-profit as conditional close
            # Kraken doesn't support both in one order directly,
            # so we create entry with stop-loss close, then add separate TP
            params["close[ordertype]"] = "stop-loss"
            params["close[price]"] = self._format_order_value(stop_loss)
            
            # Submit entry with stop-loss
            res = self._private("/0/private/AddOrder", params)
            entry_receipt = self._submission_order_receipt(
                res,
                symbol=symbol,
                side=side,
                order_type=order_type,
                requested_quantity=quantity,
                requested_price=price,
            )
            entry_receipt.update({
                "entryOrderId": entry_receipt.get("orderId"),
                "takeProfitOrderId": None,
                "stopLossAttached": True,
                "takeProfit": _decimal_text(take_profit),
                "stopLoss": _decimal_text(stop_loss),
                "conditionalClose": True,
            })
            if (
                entry_receipt.get("data_status") != "pending_reconciliation"
                or not entry_receipt.get("orderId")
            ):
                entry_receipt["reason"] = "entry_submission_receipt_unproven"
                return entry_receipt
            
            # Now add take-profit as separate order
            tp_params = {
                "pair": pair,
                "type": close_side,
                "ordertype": "take-profit",
                "volume": self._format_order_value(quantity),
                "price": self._format_order_value(take_profit),
            }
            try:
                tp_res = self._private("/0/private/AddOrder", tp_params)
            except Exception as exc:
                entry_receipt.update({
                    "reason": "secondary_submission_requires_reconciliation",
                    "secondary_submission_error": type(exc).__name__,
                })
                return entry_receipt
            tp_receipt = self._submission_order_receipt(
                tp_res,
                symbol=symbol,
                side=close_side,
                order_type="take_profit",
                requested_quantity=quantity,
                requested_price=take_profit,
            )
            entry_receipt.update({
                "takeProfitOrderId": tp_receipt.get("orderId"),
                "orderReceipts": [entry_receipt.copy(), tp_receipt],
            })
            if (
                tp_receipt.get("data_status") != "pending_reconciliation"
                or not tp_receipt.get("orderId")
            ):
                entry_receipt["reason"] = "secondary_submission_receipt_unproven"
            return entry_receipt
        
        elif take_profit:
            # Entry with take-profit close
            params["close[ordertype]"] = "take-profit"
            params["close[price]"] = self._format_order_value(take_profit)
        
        elif stop_loss:
            # Entry with stop-loss close
            params["close[ordertype]"] = "stop-loss"
            params["close[price]"] = self._format_order_value(stop_loss)
        
        res = self._private("/0/private/AddOrder", params)
        receipt = self._submission_order_receipt(
            res,
            symbol=symbol,
            side=side,
            order_type=order_type,
            requested_quantity=quantity,
            requested_price=price,
        )
        receipt.update({
            "takeProfit": _decimal_text(take_profit),
            "stopLoss": _decimal_text(stop_loss),
            "conditionalClose": True,
        })
        return receipt

    # ══════════════════════════════════════════════════════════════════════
    # ORDER MANAGEMENT - Query, Cancel, Modify
    # ══════════════════════════════════════════════════════════════════════

    def get_open_orders(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        """
        Get all open orders, optionally filtered by symbol.
        
        Returns:
            List of open orders with order details
        """
        if self.dry_run:
            return []
        
        result = self._private("/0/private/OpenOrders", {})
        orders = result.get("open", {})
        
        out = []
        for txid, order in orders.items():
            receipt = self._normalize_order_receipt(
                txid,
                order,
                provider_receipt_type="OpenOrders",
            )
            pair = receipt.get("symbol")
            
            # Filter by symbol if provided
            if symbol:
                self._load_asset_pairs()
                target_pair = self._alt_to_int.get(symbol, symbol)
                if pair != target_pair and pair != symbol:
                    continue
            out.append(receipt)
        
        return out

    def get_account_balance_receipt(
        self,
        pair: str | None = None,
    ) -> Dict[str, Any]:
        """Return authenticated balances and, when requested, a spot fee.

        Kraken's Balance response has no provider timestamp.  The public Time
        response is therefore read immediately after the private reads and
        retained as the source timestamp. TradeVolume fees are pair-specific,
        so S5 must request its exact spot pair; no fee is guessed or defaulted.
        ``received_at`` is a separate local receipt clock and is never used as
        a substitute for provider time.
        """
        pair_requested = pair is not None
        provider_receipt_type = (
            "Balance+TradeVolume+Time+KeyInfo"
            if pair_requested
            else "Balance+Time+KeyInfo"
        )

        def no_data(reason: str) -> Dict[str, Any]:
            return {
                "provider": "kraken",
                "venue": "kraken",
                "provider_receipt_type": provider_receipt_type,
                "account_scope": "incomplete",
                "account_id_hash": None,
                "balances": None,
                "balance_text": None,
                "taker_fee_pair": None,
                "provider_fee_pair": None,
                "taker_fee_percent_text": None,
                "taker_fee_rate": None,
                "taker_fee_rate_text": None,
                "source_id": None,
                "source_timestamp": None,
                "received_at": time.time(),
                "receipt_id": None,
                "input_receipt_ids": [],
                "api_key_permission_receipt_id": None,
                "api_key_query_funds": False,
                "api_key_modify_trades": False,
                "api_key_funding_mutations_absent": False,
                "data_status": "no_data",
                "truth_status": "no_data",
                "generated_values": False,
                "eligible_for_action": False,
                "action": False,
                "accounting": False,
                "learning": False,
                "reason": reason,
            }

        if getattr(self, "dry_run", True):
            return no_data("live_private_balance_receipt_required")
        try:
            raw_key_info = self._private("/0/private/GetApiKeyInfo", {})
            raw_permissions = (
                raw_key_info.get("permissions")
                if isinstance(raw_key_info, dict)
                else None
            )
            if (
                not isinstance(raw_permissions, list)
                or not raw_permissions
                or any(
                    not isinstance(value, str) or not value.strip()
                    for value in raw_permissions
                )
            ):
                return no_data("complete_provider_api_key_permissions_required")
            permissions = sorted({value.strip() for value in raw_permissions})
            dangerous_permission_tokens = (
                "withdraw",
                "transfer",
                "subaccount",
                "stake",
                "earn",
                "deposit",
            )
            query_funds = "query-funds" in permissions
            modify_trades = "modify-trades" in permissions
            funding_mutations_absent = not any(
                any(token in permission.lower() for token in dangerous_permission_tokens)
                for permission in permissions
            )
            if not query_funds or not modify_trades or not funding_mutations_absent:
                return no_data("least_privilege_kraken_trading_key_required")
            if raw_key_info.get("apiKey") != self.api_key:
                return no_data("provider_api_key_identity_mismatch")
            ip_allowlist = raw_key_info.get("ipAllowlist")
            if not isinstance(ip_allowlist, list) or any(
                not isinstance(value, str) for value in ip_allowlist
            ):
                return no_data("complete_provider_api_key_permissions_required")
            permission_material = json.dumps(
                {
                    "permissions": permissions,
                    "valid_until": str(raw_key_info.get("validUntil") or ""),
                    "ip_allowlist": sorted(ip_allowlist),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            permission_input_id = "kraken_api_key_permissions:" + hashlib.sha256(
                permission_material.encode("utf-8")
            ).hexdigest()
            account_id_hash = hashlib.sha256(
                f"kraken:live_spot:{self.api_key}".encode("utf-8")
            ).hexdigest()
            resolved_pair = None
            taker_fee_pair = None
            if pair_requested:
                if not isinstance(pair, str) or not pair.strip():
                    return no_data("valid_spot_fee_pair_required")
                resolved_pair, pair_info = self._resolve_pair(pair.strip())
                if not resolved_pair or not isinstance(pair_info, dict):
                    return no_data("valid_spot_fee_pair_required")
                raw_altname = pair_info.get("altname") or resolved_pair
                if not isinstance(raw_altname, str) or not raw_altname.strip():
                    return no_data("valid_spot_fee_pair_required")
                taker_fee_pair = raw_altname.strip().upper()

            raw_balances = self._private("/0/private/Balance", {})
            if not isinstance(raw_balances, dict) or not raw_balances:
                return no_data("missing_provider_balance_payload")

            balances: Dict[str, float] = {}
            balance_text: Dict[str, str] = {}
            provider_assets: Dict[str, str] = {}
            provider_rows: List[Tuple[str, str, str]] = []
            for raw_asset, raw_amount in raw_balances.items():
                if not isinstance(raw_asset, str) or not raw_asset.strip():
                    return no_data("malformed_provider_balance_asset")
                provider_asset = raw_asset.strip().upper()
                asset = self._normalize_asset_name(provider_asset)
                amount = _finite_decimal(raw_amount, nonnegative=True)
                if not asset or amount is None or asset in balances:
                    return no_data("ambiguous_or_malformed_provider_balances")
                try:
                    numeric_amount = float(amount)
                except (OverflowError, ValueError):
                    return no_data("nonfinite_provider_balance")
                if not math.isfinite(numeric_amount):
                    return no_data("nonfinite_provider_balance")
                exact_amount = format(amount, "f")
                balances[asset] = numeric_amount
                balance_text[asset] = exact_amount
                provider_assets[asset] = provider_asset
                provider_rows.append((asset, provider_asset, exact_amount))

            provider_fee_pair = None
            taker_fee_percent = None
            taker_fee_rate = None
            if resolved_pair is not None:
                raw_trade_volume = self._private(
                    "/0/private/TradeVolume",
                    {"pair": resolved_pair, "fee-info": True},
                )
                raw_fees = (
                    raw_trade_volume.get("fees")
                    if isinstance(raw_trade_volume, dict)
                    else None
                )
                if not isinstance(raw_fees, dict) or len(raw_fees) != 1:
                    return no_data("single_provider_spot_taker_fee_required")
                raw_provider_fee_pair, raw_fee_row = next(iter(raw_fees.items()))
                if (
                    not isinstance(raw_provider_fee_pair, str)
                    or not raw_provider_fee_pair.strip()
                    or not isinstance(raw_fee_row, dict)
                ):
                    return no_data("single_provider_spot_taker_fee_required")
                taker_fee_percent = _finite_decimal(
                    raw_fee_row.get("fee"),
                    nonnegative=True,
                )
                if taker_fee_percent is None or taker_fee_percent > Decimal("100"):
                    return no_data("valid_provider_spot_taker_fee_required")
                provider_fee_pair = raw_provider_fee_pair.strip().upper()
                taker_fee_rate = taker_fee_percent / Decimal("100")

            provider_clock = self._public_get("/0/public/Time")
            received_at = time.time()
            source_timestamp = _fresh_provider_timestamp(
                provider_clock.get("unixtime") if isinstance(provider_clock, dict) else None,
                now=received_at,
                max_age_seconds=60.0,
            )
            if source_timestamp is None or source_timestamp > received_at + 5.0:
                return no_data("missing_or_stale_provider_clock")

            provider_rows.sort()
            balance_payload = json.dumps(provider_rows, separators=(",", ":"))
            balance_input_id = "kraken_balance_payload:" + hashlib.sha256(
                balance_payload.encode("utf-8")
            ).hexdigest()
            clock_input_id = "kraken_time:" + hashlib.sha256(
                format(source_timestamp, ".6f").encode("utf-8")
            ).hexdigest()
            input_receipt_ids = [
                permission_input_id,
                balance_input_id,
                clock_input_id,
            ]
            source_id = (
                "kraken:/0/private/GetApiKeyInfo+"
                "/0/private/Balance+/0/public/Time"
            )
            receipt_evidence = {
                "source_id": source_id,
                "source_timestamp": format(source_timestamp, ".6f"),
                "account_id_hash": account_id_hash,
                "api_key_permissions": permissions,
                "api_key_permission_receipt_id": permission_input_id,
                "provider_rows": provider_rows,
                "input_receipt_ids": input_receipt_ids,
            }
            if taker_fee_rate is not None:
                fee_material = json.dumps(
                    {
                        "requested_pair": taker_fee_pair,
                        "provider_pair": provider_fee_pair,
                        "fee_percent": format(taker_fee_percent, "f"),
                        "fee_rate": format(taker_fee_rate, "f"),
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                fee_input_id = "kraken_trade_volume_fee:" + hashlib.sha256(
                    fee_material.encode("utf-8")
                ).hexdigest()
                input_receipt_ids.insert(1, fee_input_id)
                source_id = (
                    "kraken:/0/private/GetApiKeyInfo+"
                    "/0/private/Balance+"
                    "/0/private/TradeVolume+/0/public/Time"
                )
                receipt_evidence.update({
                    "source_id": source_id,
                    "taker_fee_pair": taker_fee_pair,
                    "provider_fee_pair": provider_fee_pair,
                    "taker_fee_percent": format(taker_fee_percent, "f"),
                    "taker_fee_rate": format(taker_fee_rate, "f"),
                    "input_receipt_ids": input_receipt_ids,
                })
            receipt_material = json.dumps(
                receipt_evidence,
                sort_keys=True,
                separators=(",", ":"),
            )
            return {
                "provider": "kraken",
                "venue": "kraken",
                "provider_receipt_type": provider_receipt_type,
                "account_scope": "complete",
                "account_id_hash": account_id_hash,
                "balances": balances,
                "balance_text": balance_text,
                "provider_assets": provider_assets,
                "taker_fee_pair": taker_fee_pair,
                "provider_fee_pair": provider_fee_pair,
                "taker_fee_percent_text": (
                    format(taker_fee_percent, "f")
                    if taker_fee_percent is not None
                    else None
                ),
                "taker_fee_rate": (
                    float(taker_fee_rate)
                    if taker_fee_rate is not None
                    else None
                ),
                "taker_fee_rate_text": (
                    format(taker_fee_rate, "f")
                    if taker_fee_rate is not None
                    else None
                ),
                "source_id": source_id,
                "source_timestamp": source_timestamp,
                "received_at": received_at,
                "timestamp_policy": "kraken_server_time_near_private_balance_read",
                "receipt_id": "kraken_balance:" + hashlib.sha256(
                    receipt_material.encode("utf-8")
                ).hexdigest(),
                "input_receipt_ids": input_receipt_ids,
                "api_key_permission_receipt_id": permission_input_id,
                "api_key_query_funds": query_funds,
                "api_key_modify_trades": modify_trades,
                "api_key_funding_mutations_absent": funding_mutations_absent,
                "data_status": "live",
                "truth_status": "real_observed",
                "generated_values": False,
                "eligible_for_action": True,
                "action": False,
                "accounting": False,
                "learning": False,
                "reason": None,
            }
        except Exception as exc:
            logger.warning("Kraken balance receipt unavailable: %s", exc)
            return no_data("provider_balance_receipt_error")

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get status of a specific order.
        
        Args:
            order_id: The Kraken transaction ID (txid)
            
        Returns:
            Order details including status
        """
        if self.dry_run:
            receipt = self._order_receipt_shell(
                symbol=None,
                side=None,
                order_type=None,
                order_id=order_id,
            )
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "submitted": None,
                "dryRun": True,
                "reconciliation_required": receipt.get("orderId") is not None,
                "reason": "provider_order_query_not_executed_in_dry_run",
            })
            return receipt

        txid = _valid_kraken_id(order_id)
        if txid is None:
            return self._normalize_order_receipt(
                order_id,
                None,
                provider_receipt_type="QueryOrders",
            )
        
        result = self._private(
            "/0/private/QueryOrders",
            {"txid": txid, "trades": True},
        )
        order = result.get(txid) if isinstance(result, dict) else None
        return self._normalize_order_receipt(
            txid,
            order,
            provider_receipt_type="QueryOrders",
        )

    def get_closed_orders(self, symbol: str | None = None) -> List[Dict[str, Any]]:
        """Return only fail-closed normalizations of provider ClosedOrders rows."""
        if self.dry_run:
            return []
        result = self._private("/0/private/ClosedOrders", {"trades": True})
        orders = result.get("closed") if isinstance(result, dict) else None
        if not isinstance(orders, dict):
            return []
        normalized = []
        for txid, order in orders.items():
            receipt = self._normalize_order_receipt(
                txid,
                order,
                provider_receipt_type="ClosedOrders",
            )
            pair = receipt.get("symbol")
            if symbol:
                self._load_asset_pairs()
                target_pair = self._alt_to_int.get(symbol, symbol)
                if pair != target_pair and pair != symbol:
                    continue
            normalized.append(receipt)
        return normalized

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """
        Cancel a specific order.
        
        Args:
            order_id: The Kraken transaction ID to cancel
            
        Returns:
            Cancellation result
        """
        if self.dry_run:
            receipt = self._not_submitted_order_receipt(
                symbol=None,
                side=None,
                order_type=None,
            )
            receipt["attemptedOrderId"] = _valid_kraken_id(order_id)
            receipt["reason"] = "dry_run_cancel_not_submitted"
            return receipt

        txid = _valid_kraken_id(order_id)
        if txid is None:
            receipt = self._order_receipt_shell(
                symbol=None,
                side=None,
                order_type=None,
            )
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "submitted": False,
                "reconciliation_required": False,
                "reason": "missing_or_sentinel_provider_txid",
            })
            return receipt

        result = self._private("/0/private/CancelOrder", {"txid": txid})
        count = _finite_decimal(result.get("count"), positive=True) if isinstance(result, dict) else None
        receipt = self._order_receipt_shell(
            symbol=None,
            side=None,
            order_type=None,
            order_id=txid,
        )
        receipt.update({
            "provider_receipt_type": "CancelOrder",
            "received_at": time.time(),
            "providerCancelCount": format(count, "f") if count is not None else None,
            "status": "pending_reconciliation" if count is not None else "no_data",
            "data_status": "pending_reconciliation" if count is not None else "no_data",
            "truth_status": "real_observed" if count is not None else "no_data",
            "submitted": count is not None,
            "reconciliation_required": count is not None,
            "reason": (
                "terminal_provider_order_receipt_required"
                if count is not None
                else "missing_or_malformed_cancel_acknowledgement"
            ),
        })
        return receipt

    def cancel_all_orders(self, symbol: str | None = None) -> Dict[str, Any]:
        """
        Cancel all open orders, optionally filtered by symbol.
        
        Args:
            symbol: If provided, only cancel orders for this pair
            
        Returns:
            Count of cancelled orders
        """
        if self.dry_run:
            return {
                "count": None,
                "status": "not_submitted",
                "data_status": "not_submitted",
                "truth_status": "not_submitted",
                "dryRun": True,
                "submitted": False,
                "generated_values": False,
            }
        
        if symbol:
            # Cancel orders for specific symbol by iterating
            open_orders = self.get_open_orders(symbol)
            cancelled = 0
            for order in open_orders:
                try:
                    receipt = self.cancel_order(order["orderId"])
                    if receipt.get("data_status") == "pending_reconciliation":
                        cancelled += 1
                except Exception:
                    pass
            return {
                "acknowledged_count": cancelled,
                "symbol": symbol,
                "status": "pending_reconciliation" if cancelled else "no_data",
                "data_status": "pending_reconciliation" if cancelled else "no_data",
                "reconciliation_required": bool(cancelled),
                "generated_values": False,
            }
        
        # Cancel all orders
        result = self._private("/0/private/CancelAll", {})
        count = _finite_decimal(result.get("count"), nonnegative=True) if isinstance(result, dict) else None
        return {
            "providerCancelCount": format(count, "f") if count is not None else None,
            "status": "pending_reconciliation" if count is not None else "no_data",
            "data_status": "pending_reconciliation" if count is not None else "no_data",
            "truth_status": "real_observed" if count is not None else "no_data",
            "reconciliation_required": count is not None,
            "generated_values": False,
        }

    def edit_order(
        self,
        order_id: str,
        quantity: float | str | Decimal | None = None,
        price: float | str | Decimal | None = None
    ) -> Dict[str, Any]:
        """
        Edit an existing order (change price or quantity without cancel/replace).
        
        Args:
            order_id: The Kraken transaction ID to edit
            quantity: New quantity (optional)
            price: New price (optional)
            
        Returns:
            New order ID (Kraken returns new txid for edited orders)
        """
        if self.dry_run:
            receipt = self._not_submitted_order_receipt(
                symbol=None,
                side=None,
                order_type=None,
                requested_quantity=quantity,
                requested_price=price,
            )
            receipt["attemptedOrderId"] = _valid_kraken_id(order_id)
            receipt["reason"] = "dry_run_edit_not_submitted"
            return receipt

        txid = _valid_kraken_id(order_id)
        if txid is None:
            receipt = self._order_receipt_shell(
                symbol=None,
                side=None,
                order_type=None,
            )
            receipt.update({
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "missing_or_sentinel_provider_txid",
            })
            return receipt

        params = {"txid": txid}
        
        if quantity:
            params["volume"] = self._format_order_value(quantity)
        if price:
            params["price"] = self._format_order_value(price)
        
        result = self._private("/0/private/EditOrder", params)
        new_txid = _valid_kraken_id(result.get("txid")) if isinstance(result, dict) else None
        receipt = self._order_receipt_shell(
            symbol=None,
            side=None,
            order_type=None,
            order_id=new_txid,
            requested_quantity=quantity,
            requested_price=price,
        )
        receipt.update({
            "originalOrderId": txid,
            "newOrderId": new_txid,
            "provider_receipt_type": "EditOrder",
            "received_at": time.time(),
            "status": "pending_reconciliation" if new_txid else "no_data",
            "data_status": "pending_reconciliation" if new_txid else "no_data",
            "truth_status": "real_observed" if new_txid else "no_data",
            "submitted": new_txid is not None,
            "reconciliation_required": new_txid is not None,
            "reason": (
                "terminal_provider_order_receipt_required"
                if new_txid
                else "missing_or_malformed_edit_acknowledgement"
            ),
        })
        return receipt

    # ══════════════════════════════════════════════════════════════════════
    # CRYPTO CONVERSION - Convert between crypto assets internally
    # ══════════════════════════════════════════════════════════════════════

    def get_available_pairs(self, base: str = None, quote: str = None) -> List[Dict[str, Any]]:
        """
        Get available trading pairs, optionally filtered by base or quote asset.
        
        Args:
            base: Filter by base asset (e.g., 'BTC', 'ETH')
            quote: Filter by quote asset (e.g., 'USD', 'ETH')
            
        Returns:
            List of pairs with base, quote, and pair name
        """
        pairs = self._load_asset_pairs()
        results = []
        
        for internal, info in pairs.items():
            alt = info.get("altname") or internal
            wsname = info.get("wsname", "")
            pair_base = info.get("base", "")
            pair_quote = info.get("quote", "")
            
            # Normalize asset names (Kraken uses X prefix for crypto, Z for fiat)
            pair_base_clean = pair_base.lstrip("XZ")
            pair_quote_clean = pair_quote.lstrip("XZ")
            
            # Also handle altname parsing (e.g., ETHBTC -> ETH, BTC)
            if not pair_base_clean and len(alt) >= 6:
                # Try to parse from altname
                for q in ['USD', 'USDC', 'USDT', 'EUR', 'GBP', 'BTC', 'XBT', 'ETH']:
                    if alt.endswith(q):
                        pair_base_clean = alt[:-len(q)]
                        pair_quote_clean = q
                        break
            
            # Normalize XBT to BTC
            if pair_base_clean == 'XBT':
                pair_base_clean = 'BTC'
            if pair_quote_clean == 'XBT':
                pair_quote_clean = 'BTC'
            
            # Apply filters
            if base and pair_base_clean.upper() != base.upper():
                continue
            if quote and pair_quote_clean.upper() != quote.upper():
                continue
            
            results.append({
                "pair": alt,
                "internal": internal,
                "base": pair_base_clean,
                "quote": pair_quote_clean,
                "wsname": wsname
            })
        
        return results

    def find_conversion_path(self, from_asset: str, to_asset: str, _depth: int = 0) -> List[Dict[str, Any]]:
        """
        Find the best path to convert from one asset to another.
        
        Returns list of trades to execute:
        - Single trade if direct pair exists
        - Two trades via USD/USDC if no direct pair
        
        Args:
            from_asset: Source asset (e.g., 'BTC')
            to_asset: Target asset (e.g., 'ETH')
            _depth: Internal recursion depth limiter
            
        Returns:
            List of {pair, side, description} for each trade needed
        """
        # 🐍 MEDUSA: Prevent infinite recursion
        if _depth > 2:
            return []
            
        from_asset = from_asset.upper()
        to_asset = to_asset.upper()
        
        if from_asset == to_asset:
            return []
        
        # Normalize BTC/XBT (for matching purposes below)
        _from_norm = 'XBT' if from_asset == 'BTC' else from_asset
        _to_norm = 'XBT' if to_asset == 'BTC' else to_asset
        
        # 🐍 MEDUSA: Normalize Kraken quote currencies
        # ZUSD = USD (Kraken internal naming)
        quote_currencies = ['USD', 'ZUSD', 'USDT', 'USDC', 'EUR', 'ZEUR']
        _from_is_quote = from_asset in quote_currencies
        _to_is_quote = to_asset in quote_currencies
        
        # Normalize ZUSD -> USD for matching purposes
        from_match = 'USD' if from_asset == 'ZUSD' else from_asset
        to_match = 'USD' if to_asset == 'ZUSD' else to_asset
        
        pairs = self._load_asset_pairs()
        
        # Try direct pair: from_asset/to_asset (sell from, get to)
        for internal, info in pairs.items():
            alt = info.get("altname", internal)
            raw_base = info.get("base", "")
            raw_quote = info.get("quote", "")
            
            # 🐍 MEDUSA: Smarter Kraken name normalization
            # XXBT -> BTC (not XBT or BT)
            # XETH -> ETH
            # ZUSD -> USD
            def normalize_kraken_asset(name: str) -> str:
                # Strip leading X or Z (Kraken prefixes)
                if name.startswith('XX'):
                    name = name[2:]  # XXBT -> BT
                elif name.startswith('X') and len(name) > 3:
                    name = name[1:]  # XETH -> ETH
                elif name.startswith('Z') and name not in ('ZUSD', 'ZEUR', 'ZGBP'):
                    name = name[1:]
                # XBT/BT -> BTC
                if name in ('XBT', 'BT'):
                    name = 'BTC'
                # Normalize quote currencies
                if name == 'ZUSD':
                    name = 'USD'
                if name == 'ZEUR':
                    name = 'EUR'
                return name.upper()
            
            base = normalize_kraken_asset(raw_base)
            quote = normalize_kraken_asset(raw_quote)
            
            # Normalize quote currencies for matching
            quote_normalized = 'USD' if quote in ('ZUSD', 'USD') else quote
            
            # Direct: from_asset is base, to_asset is quote -> SELL from_asset for to_asset
            if base == from_match and quote_normalized == to_match:
                return [{
                    "pair": alt,
                    "side": "sell",
                    "description": f"Sell {from_asset} for {to_asset}",
                    "from": from_asset,
                    "to": to_asset
                }]
            
            # Inverse: to_asset is base, from_asset is quote -> BUY to_asset with from_asset
            # 🐍 MEDUSA: When from_asset is USD/ZUSD, we BUY to_asset
            if base.upper() == to_match and quote_normalized == from_match:
                return [{
                    "pair": alt,
                    "side": "buy",
                    "description": f"Buy {to_asset} with {from_asset}",
                    "from": from_asset,
                    "to": to_asset
                }]
        
        # No direct pair - route through intermediary (USD, USDC, USDT, EUR)
        # 🐍 MEDUSA: Skip intermediate routing if from_asset IS the intermediate
        for intermediate in ['USD', 'USDC', 'USDT', 'EUR']:
            # Prevent infinite recursion: don't route through self
            if from_match == intermediate or to_match == intermediate:
                continue
            path1 = self.find_conversion_path(from_asset, intermediate, _depth + 1)
            path2 = self.find_conversion_path(intermediate, to_asset, _depth + 1)
            
            if path1 and path2 and len(path1) == 1 and len(path2) == 1:
                return path1 + path2
        
        return []  # No path found

    def convert_crypto(
        self,
        from_asset: str,
        to_asset: str,
        amount: float,
        use_quote_amount: bool = False
    ) -> Dict[str, Any]:
        """
        Convert one crypto asset to another within Kraken.
        
        Automatically finds the best path:
        - Direct pair if available (e.g., ETH/BTC)
        - Via USD/USDC if no direct pair
        
        Args:
            from_asset: Source asset (e.g., 'BTC', 'ETH')
            to_asset: Target asset (e.g., 'ETH', 'SOL')
            amount: Amount of from_asset to convert
            use_quote_amount: If True, amount is in to_asset terms
            
        Returns:
            Conversion result with executed trades
        """
        from_asset = from_asset.upper()
        to_asset = to_asset.upper()
        
        if from_asset == to_asset:
            return {"error": "Cannot convert to same asset", "from": from_asset, "to": to_asset}
        
        # 🚨 CRITICAL: Block stablecoin→stablecoin swaps - they ALWAYS lose to fees!
        STABLECOINS = {'USD', 'ZUSD', 'USDT', 'USDC', 'TUSD', 'DAI', 'BUSD', 'EUR', 'ZEUR'}
        if from_asset in STABLECOINS and to_asset in STABLECOINS:
            return {"error": f"Stablecoin→stablecoin swap blocked ({from_asset}→{to_asset}) - always loses to fees!"}
        
        # Find conversion path
        path = self.find_conversion_path(from_asset, to_asset)
        
        if not path:
            return {"error": f"No conversion path found from {from_asset} to {to_asset}"}
        
        # 👑 QUEEN MIND: Pre-flight validation for multi-step conversions
        # Estimate if each step will meet minimum requirements
        estimated_amount = amount
        for i, trade in enumerate(path):
            pair = trade["pair"]
            filters = self.get_symbol_filters(pair)
            ordermin = filters.get('min_qty', 0.0001)
            costmin = filters.get('min_notional', 1.20)  # Kraken costmin ~$1.20
            
            # Estimate value at this step
            try:
                price_info = self.best_price(pair)
                price = float(price_info.get("price", 0))
            except Exception:
                price = 0
            
            if trade["side"] == "sell":
                # We're selling estimated_amount
                if estimated_amount < ordermin:
                    return {
                        "error": f"Multi-hop step {i+1} would have {estimated_amount:.6f} < min {ordermin} for {pair}",
                        "failed_step": i,
                        "pair": pair
                    }
                # Estimate received amount
                if price > 0:
                    estimated_amount = estimated_amount * price
            else:
                # We're buying with estimated_amount as quote
                estimated_value = estimated_amount
                if estimated_value < costmin:
                    return {
                        "error": f"Multi-hop step {i+1} value ${estimated_value:.2f} < min ${costmin:.2f} for {pair}",
                        "failed_step": i,
                        "pair": pair
                    }
                # Estimate received amount
                if price > 0:
                    estimated_amount = estimated_amount / price
        
        if self.dry_run:
            return {
                "dryRun": True,
                "status": "not_submitted",
                "data_status": "not_submitted",
                "truth_status": "not_submitted",
                "submitted": False,
                "generated_values": False,
                "from_asset": from_asset,
                "to_asset": to_asset,
                "amount": amount,
                "path": path,
                "planned_steps": len(path),
                "trades": [],
            }
        
        # Execute trades
        results = []
        remaining_amount = amount
        
        for trade in path:
            pair = trade["pair"]
            side = trade["side"]
            
            try:
                if side == "sell":
                    # Selling from_asset
                    result = self.place_market_order(pair, "sell", quantity=remaining_amount)
                else:
                    # Buying to_asset - need to estimate quantity from current price
                    if use_quote_amount and len(path) == 1:
                        # User specified amount in target terms
                        result = self.place_market_order(pair, "buy", quantity=amount)
                    else:
                        # Use quote_qty to spend remaining_amount of from_asset
                        result = self.place_market_order(pair, "buy", quote_qty=remaining_amount)
                
                # Check for errors in result
                if result.get("error"):
                    results.append({
                        "trade": trade,
                        "result": result,
                        "status": "failed",
                        "error": result.get("error")
                    })
                    return {
                        "error": f"Trade failed: {result.get('error')}",
                        "from_asset": from_asset,
                        "to_asset": to_asset,
                        "partial_results": results
                    }

                if (
                    result.get("data_status") != "live"
                    or result.get("fill_receipt_complete") is not True
                    or result.get("eligible_for_accounting") is not True
                    or str(result.get("status") or "").upper() not in {"FILLED", "PARTIALLY_FILLED"}
                ):
                    reconciliation_status = str(
                        result.get("data_status") or "no_data"
                    )
                    results.append({
                        "trade": trade,
                        "result": result,
                        "status": reconciliation_status,
                    })
                    return {
                        "error": "terminal_fill_receipt_required",
                        "status": reconciliation_status,
                        "data_status": reconciliation_status,
                        "truth_status": result.get("truth_status") or "no_data",
                        "reconciliation_required": (
                            reconciliation_status == "pending_reconciliation"
                        ),
                        "from_asset": from_asset,
                        "to_asset": to_asset,
                        "partial_results": results,
                        "generated_values": False,
                    }

                executed_quantity = _finite_decimal(
                    result.get("executedQty"),
                    positive=True,
                )
                filled_cost = _finite_decimal(
                    result.get("cummulativeQuoteQty"),
                    positive=True,
                )
                observed_fee = _finite_decimal(result.get("fee"), nonnegative=True)
                fee_asset = str(result.get("fee_asset") or "").upper()
                if (
                    executed_quantity is None
                    or filled_cost is None
                    or observed_fee is None
                    or not fee_asset
                ):
                    results.append({
                        "trade": trade,
                        "result": result,
                        "status": "no_data",
                    })
                    return {
                        "error": "malformed_terminal_fill_receipt",
                        "status": "no_data",
                        "data_status": "no_data",
                        "truth_status": "no_data",
                        "reconciliation_required": True,
                        "from_asset": from_asset,
                        "to_asset": to_asset,
                        "partial_results": results,
                        "generated_values": False,
                    }

                base_asset, quote_asset = self._pair_base_quote(pair)
                if side == "sell":
                    received_amount = filled_cost
                    if fee_asset == quote_asset.upper():
                        received_amount -= observed_fee
                else:
                    received_amount = executed_quantity
                    if fee_asset == base_asset.upper():
                        received_amount -= observed_fee
                if received_amount <= 0:
                    results.append({
                        "trade": trade,
                        "result": result,
                        "status": "no_data",
                    })
                    return {
                        "error": "nonpositive_provider_net_received_quantity",
                        "status": "no_data",
                        "data_status": "no_data",
                        "truth_status": "no_data",
                        "reconciliation_required": True,
                        "from_asset": from_asset,
                        "to_asset": to_asset,
                        "partial_results": results,
                        "generated_values": False,
                    }
                
                verified_result = dict(result)
                verified_result["receivedQty"] = format(received_amount, "f")
                
                results.append({
                    "trade": trade,
                    "result": verified_result,
                    "status": "success",
                    "receivedQty": format(received_amount, "f"),
                })
                
                # Advance a conversion chain only with verified provider proceeds.
                remaining_amount = received_amount
                    
            except Exception as e:
                results.append({
                    "trade": trade,
                    "error": str(e),
                    "status": "failed"
                })
                return {
                    "error": f"Trade failed: {e}",
                    "from_asset": from_asset,
                    "to_asset": to_asset,
                    "partial_results": results
                }
        
        return {
            "success": True,
            "from_asset": from_asset,
            "to_asset": to_asset,
            "original_amount": amount,
            "path": path,
            "trades": results,
            "trade_count": len(results)
        }

    def get_convertible_assets(self) -> Dict[str, List[str]]:
        """
        Get all assets that can be converted to/from.

        Returns:
            Dict mapping each asset to list of assets it can convert to
        """
        pairs = self._load_asset_pairs()

        # Build conversion map
        conversions = {}

        for _internal, info in pairs.items():
            base = info.get("base", "").lstrip("XZ")
            quote = info.get("quote", "").lstrip("XZ")

            # Normalize XBT -> BTC
            if base == 'XBT': base = 'BTC'
            if quote == 'XBT': quote = 'BTC'

            if not base or not quote:
                continue

            base = base.upper()
            quote = quote.upper()

            # Base can convert to quote (by selling)
            if base not in conversions:
                conversions[base] = set()
            conversions[base].add(quote)

            # Quote can convert to base (by buying)
            if quote not in conversions:
                conversions[quote] = set()
            conversions[quote].add(base)

        # Convert sets to sorted lists
        return {k: sorted(v) for k, v in conversions.items()}

    # ══════════════════════════════════════════════════════════════════════
    # ══════════════════════════════════════════════════════════════════════
    # FUNDING - Deposits, withdrawals, and address management
    # ══════════════════════════════════════════════════════════════════════

    def get_deposit_addresses(self, asset: str = 'USDT', method: str | None = None,
                               new: bool = False) -> list:
        """Return deposit addresses for an asset on Kraken.

        Args:
            asset:  Kraken asset code, e.g. 'USDT' or 'ZUSD' or 'XBT'.
            method: Deposit method name, e.g. 'Tether USD (TRC20)'.
                    If omitted, Kraken returns all available methods.
            new:    If True, generate a new address even if one already exists.

        Returns:
            List of dicts each containing 'address', 'expiretm', 'new' keys.
            Empty list on error.
        """
        if self.dry_run:
            return [{'address': 'DRY_RUN_ADDRESS', 'expiretm': '0', 'new': False}]
        params: Dict[str, Any] = {'asset': asset}
        if method:
            params['method'] = method
        if new:
            params['new'] = 'true'
        try:
            result = self._private('/0/private/DepositAddresses', params)
            return result.get('result', [])
        except Exception as e:
            print(f"  [Kraken] get_deposit_addresses error: {e}")
            return []

    # MARGIN TRADING - Leveraged positions on Kraken
    # ══════════════════════════════════════════════════════════════════════

    def get_trade_balance(self, asset: str = "ZUSD") -> Dict[str, Any]:
        """
        Get margin/trade balance information from Kraken.

        Args:
            asset: Base asset for balance calculation (default ZUSD for USD)

        Returns:
            Dict with margin account details:
            - equity_value: Total equity (balance + unrealized P&L)
            - trade_balance: Balance available for trading (equity - margin used)
            - margin_amount: Total margin used by open positions
            - unrealized_pnl: Net unrealized profit/loss of open margin positions
            - cost_basis: Total cost basis of open margin positions
            - floating_valuation: Current floating valuation of open positions
            - free_margin: Available margin for new trades
            - margin_level: Margin level percentage (equity / margin * 100)
        """
        empty_values = {
            "equity_value": None,
            "trade_balance": None,
            "margin_amount": None,
            "unrealized_pnl": None,
            "cost_basis": None,
            "floating_valuation": None,
            "free_margin": None,
            "margin_level": None,
        }
        if self.dry_run:
            return {
                **empty_values,
                "status": "not_submitted",
                "data_status": "not_submitted",
                "truth_status": "not_submitted",
                "dryRun": True
            }

        result = self._private("/0/private/TradeBalance", {"asset": asset})
        if not isinstance(result, dict):
            return {
                **empty_values,
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "missing_provider_trade_balance_receipt",
            }
        provider_fields = {
            "equity_value": "e",
            "trade_balance": "tb",
            "margin_amount": "m",
            "unrealized_pnl": "n",
            "cost_basis": "c",
            "floating_valuation": "v",
            "free_margin": "mf",
            "margin_level": "ml",
        }
        observed = {
            output_name: _finite_decimal(result.get(provider_name))
            for output_name, provider_name in provider_fields.items()
        }
        if any(value is None for value in observed.values()):
            return {
                **empty_values,
                "status": "no_data",
                "data_status": "no_data",
                "truth_status": "no_data",
                "reason": "incomplete_provider_trade_balance_receipt",
                "generated_values": False,
            }
        return {
            **{name: float(value) for name, value in observed.items()},
            "status": "live",
            "data_status": "live",
            "truth_status": "real_observed",
            "source_id": f"kraken_trade_balance:{asset}",
            "received_at": time.time(),
            "generated_values": False,
        }

    def get_open_margin_positions(self, do_calcs: bool = True) -> List[Dict[str, Any]]:
        """
        Get all open margin positions on Kraken.

        Args:
            do_calcs: If True, include profit/loss calculations (default True)

        Returns:
            List of open margin positions with details:
            - position_id: Unique position identifier
            - pair: Trading pair
            - side: 'buy' (long) or 'sell' (short)
            - volume: Position volume
            - cost: Entry cost
            - fee: Fees paid
            - current_value: Current position value (if do_calcs=True)
            - unrealized_pnl: Unrealized P&L (if do_calcs=True)
            - leverage: Leverage used
            - margin: Margin allocated
        """
        if self.dry_run:
            return []

        params = {"docalcs": "true" if do_calcs else "false"}
        result = self._private("/0/private/OpenPositions", params)

        positions = []
        for pos_id, pos_data in result.items():
            base, quote = self._pair_base_quote(pos_data.get("pair", ""))
            positions.append({
                "position_id": pos_id,
                "pair": pos_data.get("pair", ""),
                "base": base,
                "quote": quote,
                "side": pos_data.get("type", ""),          # 'buy' or 'sell'
                "order_type": pos_data.get("ordertype", ""),
                "volume": float(pos_data.get("vol", 0)),
                "volume_closed": float(pos_data.get("vol_closed", 0)),
                "cost": float(pos_data.get("cost", 0)),
                "fee": float(pos_data.get("fee", 0)),
                "current_value": float(pos_data.get("value", 0)),
                "unrealized_pnl": float(pos_data.get("net", 0)),
                "leverage": pos_data.get("leverage", "1"),
                "margin": float(pos_data.get("margin", 0)),
                "terms": pos_data.get("terms", ""),
                "open_time": float(pos_data.get("time", 0)),
                "misc": pos_data.get("misc", ""),
            })

        return positions

    def get_margin_pairs(self) -> List[Dict[str, Any]]:
        """
        Get all trading pairs that support margin trading with their leverage limits.

        Returns:
            List of pairs with margin info:
            - pair: Altname of the pair
            - internal: Internal Kraken pair name
            - leverage_buy: List of available buy leverages (e.g., [2, 3, 4, 5])
            - leverage_sell: List of available sell leverages
            - max_leverage: Maximum leverage available
        """
        pairs = self._load_asset_pairs()
        margin_pairs = []

        for internal, info in pairs.items():
            leverage_buy = info.get("leverage_buy", [])
            leverage_sell = info.get("leverage_sell", [])

            # Only include pairs that support margin (have leverage options)
            if not leverage_buy and not leverage_sell:
                continue

            alt = info.get("altname") or internal
            base = self._normalize_asset_name(info.get("base", ""))
            quote = self._normalize_asset_name(info.get("quote", ""))

            max_lev = max(leverage_buy + leverage_sell) if (leverage_buy or leverage_sell) else 1

            margin_pairs.append({
                "pair": alt,
                "internal": internal,
                "base": base,
                "quote": quote,
                "leverage_buy": leverage_buy,
                "leverage_sell": leverage_sell,
                "max_leverage": max_lev,
            })

        return margin_pairs

    def get_pair_leverage(self, symbol: str) -> Dict[str, Any]:
        """
        Get available leverage options for a specific trading pair.

        Args:
            symbol: Trading pair (e.g., 'ETHUSD', 'BTCUSD')

        Returns:
            Dict with leverage info or empty dict if pair doesn't support margin
        """
        _pair, pair_info = self._resolve_pair(symbol)
        if not pair_info:
            return {}

        leverage_buy = pair_info.get("leverage_buy", [])
        leverage_sell = pair_info.get("leverage_sell", [])

        if not leverage_buy and not leverage_sell:
            return {}

        return {
            "pair": pair_info.get("altname", symbol),
            "leverage_buy": leverage_buy,
            "leverage_sell": leverage_sell,
            "max_leverage": max(leverage_buy + leverage_sell) if (leverage_buy or leverage_sell) else 1,
            "margin_supported": True,
        }

    def place_margin_order(
        self,
        symbol: str,
        side: str,
        quantity: float | str | Decimal,
        leverage: int | str,
        order_type: str = "market",
        price: float | str | Decimal | None = None,
        take_profit: float | str | Decimal | None = None,
        stop_loss: float | str | Decimal | None = None,
        post_only: bool = False,
        reduce_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Place a margin (leveraged) order on Kraken.

        This opens a leveraged position using borrowed funds. For example, with 3x
        leverage on a $100 trade, you put up ~$33 margin and borrow ~$67.

        Args:
            symbol: Trading pair (e.g., 'ETHUSD', 'BTCUSD')
            side: 'buy' for long, 'sell' for short
            quantity: Amount of base asset to trade
            leverage: Leverage multiplier (e.g., 2, 3, 5). Must be supported by pair.
            order_type: 'market' or 'limit'
            price: Limit price (required if order_type='limit')
            take_profit: Attach take-profit at this price (optional)
            stop_loss: Attach stop-loss at this price (optional)
            post_only: For limit orders, ensure maker-only (0.16% fee vs 0.26%)
            reduce_only: Only reduce an existing position, don't open new one

        Returns:
            Binance-compatible order response with margin details

        Example:
            # Long 0.5 ETH at 3x leverage
            place_margin_order('ETHUSD', 'buy', 0.5, leverage=3)

            # Short 0.01 BTC at 2x with stop-loss
            place_margin_order('BTCUSD', 'sell', 0.01, leverage=2, stop_loss=105000)
        """
        if self.dry_run:
            receipt = self._not_submitted_order_receipt(
                symbol=symbol,
                side=side,
                order_type=order_type,
                requested_quantity=quantity,
                requested_price=price,
            )
            receipt.update({
                "leverage": str(leverage),
                "takeProfit": _decimal_text(take_profit),
                "stopLoss": _decimal_text(stop_loss),
                "margin": True,
            })
            return receipt

        # ═══ SAFETY NET: $5 minimum margin trade value (last-resort gate) ═══
        # Note: For market orders (price=None), skip this gate — the ecosystem
        # already validates margin_budget in USD before calling place_margin_order.
        MIN_TRADE_USD = 5.0
        if side.lower() == "buy" and price is not None:
            usd_value = float(quantity) * float(price)
            if usd_value < MIN_TRADE_USD:
                import logging as _logging
                _logging.getLogger(__name__).error(
                    f"MARGIN SAFETY NET: Buy ${usd_value:.2f} < ${MIN_TRADE_USD} for {symbol} — BLOCKED"
                )
                return {
                    "error": "below_minimum_trade_value",
                    "symbol": symbol,
                    "usd_value": usd_value,
                    "minimum": MIN_TRADE_USD,
                    "margin": True,
                }

        # Resolve pair and validate
        pair, pair_info = self._resolve_pair(symbol)
        if not pair or not pair_info:
            raise RuntimeError(f"Unknown Kraken trading pair: {symbol}")

        # Validate leverage is supported for this pair
        lev = int(leverage)
        if side.lower() == "buy":
            valid_levs = pair_info.get("leverage_buy", [])
        else:
            valid_levs = pair_info.get("leverage_sell", [])

        if not valid_levs:
            raise RuntimeError(f"Margin trading not supported for {symbol}")
        if lev not in valid_levs:
            raise RuntimeError(
                f"Leverage {lev}x not supported for {symbol} ({side}). "
                f"Available: {valid_levs}"
            )

        # Validate minimum volume
        ordermin = float(pair_info.get("ordermin", 0.0001))
        lot_decimals = int(pair_info.get("lot_decimals", 8))
        vol = round(float(quantity), lot_decimals)

        if vol < ordermin:
            return {
                "error": "volume_minimum",
                "symbol": symbol,
                "volume": vol,
                "ordermin": ordermin,
                "margin": True
            }

        # Build order params
        params = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": order_type.lower(),
            "volume": self._format_order_value(vol),
            "leverage": str(lev),
            "trading_agreement": "agree",
        }

        # Price for limit orders
        if order_type.lower() == "limit" and price:
            params["price"] = self._format_order_value(price)

        # reduce_only is a top-level parameter, NOT an oflag
        # (nompp = "no market price protection" which is unrelated)
        if reduce_only:
            params["reduce_only"] = "true"

        # Order flags
        oflags = []
        if post_only and order_type.lower() == "limit":
            oflags.append("post")
        if oflags:
            params["oflags"] = ",".join(oflags)

        # Conditional close orders (TP/SL attached to margin position)
        if stop_loss and take_profit:
            # Attach stop-loss as conditional close, add TP as separate order
            params["close[ordertype]"] = "stop-loss"
            params["close[price]"] = self._format_order_value(stop_loss)

            res = self._private("/0/private/AddOrder", params)
            entry_receipt = self._submission_order_receipt(
                res,
                symbol=symbol,
                side=side,
                order_type=order_type,
                requested_quantity=vol,
                requested_price=price,
            )
            entry_receipt.update({
                "entryOrderId": entry_receipt.get("orderId"),
                "takeProfitOrderId": None,
                "stopLossAttached": True,
                "leverage": str(lev),
                "takeProfit": _decimal_text(take_profit),
                "stopLoss": _decimal_text(stop_loss),
                "margin": True,
            })
            if (
                entry_receipt.get("data_status") != "pending_reconciliation"
                or not entry_receipt.get("orderId")
            ):
                entry_receipt["reason"] = "entry_submission_receipt_unproven"
                return entry_receipt

            # Add take-profit as separate margin order
            close_side = "sell" if side.lower() == "buy" else "buy"
            tp_params = {
                "pair": pair,
                "type": close_side,
                "ordertype": "take-profit",
                "volume": self._format_order_value(vol),
                "price": self._format_order_value(take_profit),
                "leverage": str(lev),
                "reduce_only": "true",
                "trading_agreement": "agree",
            }
            try:
                tp_res = self._private("/0/private/AddOrder", tp_params)
            except Exception as exc:
                entry_receipt.update({
                    "reason": "secondary_submission_requires_reconciliation",
                    "secondary_submission_error": type(exc).__name__,
                })
                return entry_receipt
            tp_receipt = self._submission_order_receipt(
                tp_res,
                symbol=symbol,
                side=close_side,
                order_type="take_profit",
                requested_quantity=vol,
                requested_price=take_profit,
            )
            entry_receipt.update({
                "takeProfitOrderId": tp_receipt.get("orderId"),
                "orderReceipts": [entry_receipt.copy(), tp_receipt],
            })
            if (
                tp_receipt.get("data_status") != "pending_reconciliation"
                or not tp_receipt.get("orderId")
            ):
                entry_receipt["reason"] = "secondary_submission_receipt_unproven"
            return entry_receipt

        elif take_profit:
            params["close[ordertype]"] = "take-profit"
            params["close[price]"] = self._format_order_value(take_profit)
        elif stop_loss:
            params["close[ordertype]"] = "stop-loss"
            params["close[price]"] = self._format_order_value(stop_loss)

        res = self._private("/0/private/AddOrder", params)
        receipt = self._submission_order_receipt(
            res,
            symbol=symbol,
            side=side,
            order_type=order_type,
            requested_quantity=vol,
            requested_price=price,
        )
        receipt.update({
            "timeInForce": "GTC",
            "leverage": str(lev),
            "takeProfit": _decimal_text(take_profit),
            "stopLoss": _decimal_text(stop_loss),
            "margin": True,
        })
        return receipt

    def close_margin_position(
        self,
        symbol: str,
        side: str,
        volume: float | str | Decimal | None = None,
        order_type: str = "market",
        price: float | str | Decimal | None = None,
        leverage: int | str | None = None,
    ) -> Dict[str, Any]:
        """
        Close an open margin position by placing an opposing order.

        To close a long margin position, place a leveraged sell.
        To close a short margin position, place a leveraged buy.

        Args:
            symbol: Trading pair
            side: 'sell' to close a long, 'buy' to close a short
            volume: Amount to close (None = close entire position for this pair)
            order_type: 'market' or 'limit'
            price: Limit price (required if order_type='limit')
            leverage: Leverage (should match the open position's leverage)

        Returns:
            Order response
        """
        if self.dry_run:
            receipt = self._not_submitted_order_receipt(
                symbol=symbol,
                side=side,
                order_type=order_type,
                requested_quantity=volume,
                requested_price=price,
            )
            receipt.update({
                "leverage": str(leverage) if leverage else None,
                "margin_close": True,
            })
            return receipt

        # If no volume specified, find the open position volume
        if volume is None:
            positions = self.get_open_margin_positions(do_calcs=False)
            pair, _ = self._resolve_pair(symbol)
            for pos in positions:
                if pos["pair"] == pair and pos["side"] != side.lower():
                    remaining = pos["volume"] - pos["volume_closed"]
                    if remaining > 0:
                        volume = remaining
                        if leverage is None:
                            leverage = pos["leverage"]
                        break
            if volume is None:
                return {"error": "no_position", "symbol": symbol}

        pair, pair_info = self._resolve_pair(symbol)
        if not pair:
            raise RuntimeError(f"Unknown Kraken trading pair: {symbol}")

        lot_decimals = int(pair_info.get("lot_decimals", 8)) if pair_info else 8
        vol = round(float(volume), lot_decimals)

        params = {
            "pair": pair,
            "type": side.lower(),
            "ordertype": order_type.lower(),
            "volume": self._format_order_value(vol),
            "trading_agreement": "agree",
        }

        if leverage:
            params["leverage"] = str(int(leverage) if str(leverage).isdigit() else leverage)

        if order_type.lower() == "limit" and price:
            params["price"] = self._format_order_value(price)

        # reduce_only ensures we only close, never open new position
        params["reduce_only"] = "true"

        res = self._private("/0/private/AddOrder", params)
        receipt = self._submission_order_receipt(
            res,
            symbol=symbol,
            side=side,
            order_type=order_type,
            requested_quantity=vol,
            requested_price=price,
        )
        receipt.update({
            "leverage": str(leverage) if leverage else None,
            "margin_close": True,
        })
        return receipt


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE - for easy import
# ══════════════════════════════════════════════════════════════════════════════
_kraken_instance: KrakenClient = None

def get_kraken_client() -> KrakenClient:
    """Get singleton Kraken client instance."""
    global _kraken_instance
    if _kraken_instance is None:
        _kraken_instance = KrakenClient()
    return _kraken_instance
