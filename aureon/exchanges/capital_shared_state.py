"""Cross-process Capital.com session, login spacing, request pacing and backoff.

Every launcher organ runs in its own process, so a per-process dict cannot stop
nine processes each logging in to Capital.com. This module keeps one small JSON
state file guarded by ``fcntl.flock`` so all processes on the box share:

* one session (CST / X-SECURITY-TOKEN) per account key and environment,
* the time of the last ``POST /session`` (Capital allows 1 per second per key),
* a sliding one-second window of request times (Capital allows 10 per second),
* the time of the last order/position creation (1 per 0.1 s),
* one backoff-until timestamp after a 429.

Capital's published limits: https://open-api.capital.com/ ("Rate limits").

If the lock or file is unavailable (no ``fcntl``, read-only disk), the module
falls back to an in-process dict, which is the behaviour before this module.
Token values are never logged. The file is created with mode 0600.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import os
import random
import tempfile
import threading
import time
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Iterator, Optional

try:  # POSIX only; Windows falls back to the in-process state.
    import fcntl  # type: ignore
except Exception:  # pragma: no cover - platform dependent
    fcntl = None  # type: ignore

logger = logging.getLogger(__name__)

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

# Published: 10 req/s per user; we default below it.
DEFAULT_MAX_REQUESTS_PER_SEC = 8.0
# Published: POST /session 1 per second per API key; we keep a margin.
DEFAULT_MIN_LOGIN_INTERVAL_S = 1.1
# Published: order/position creation 1 per 0.1 s; we keep a margin.
DEFAULT_MIN_ORDER_INTERVAL_S = 0.15
# Published: sessions expire after 10 minutes idle; one shared GET /ping is
# sent once the account has been quiet this long (no extra logins).
DEFAULT_SESSION_IDLE_REFRESH_S = 540.0
# Hard age limit kept from the previous code (refresh well before 60 min).
SESSION_MAX_AGE_S = 50 * 60
# Backoff used after a 429 that carries no Retry-After (unchanged from before).
DEFAULT_RATE_LIMIT_BACKOFF_S = 600.0

_LOCAL_STATE: Dict[str, Any] = {}
_LOCAL_LOCK = threading.RLock()
_LOCAL_LOGIN_LOCK = threading.RLock()
_FALLBACK_WARNED = False


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        value = float(os.getenv(name, "") or default)
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def max_requests_per_sec() -> float:
    # Never allow a configuration above Capital's published 10/s.
    return min(10.0, _env_float("CAPITAL_MAX_REQUESTS_PER_SEC", DEFAULT_MAX_REQUESTS_PER_SEC, 0.1))


def min_login_interval_s() -> float:
    return _env_float("CAPITAL_MIN_LOGIN_INTERVAL_S", DEFAULT_MIN_LOGIN_INTERVAL_S, 1.0)


def min_order_interval_s() -> float:
    return _env_float("CAPITAL_MIN_ORDER_INTERVAL_S", DEFAULT_MIN_ORDER_INTERVAL_S, 0.1)


def session_idle_refresh_s() -> float:
    return _env_float("CAPITAL_SESSION_IDLE_REFRESH_S", DEFAULT_SESSION_IDLE_REFRESH_S, 1.0)


def cache_path() -> str:
    configured = os.getenv("CAPITAL_SESSION_CACHE_PATH", "").strip()
    if configured:
        return configured
    return os.path.join(_REPO_ROOT, "state", "capital_session_cache.json")


def account_key(api_key: Optional[str], demo_mode: bool) -> str:
    """Opaque per-account bucket name; a short hash, never the key itself."""

    digest = hashlib.sha256(str(api_key or "").encode("utf-8")).hexdigest()[:16]
    return f"{'demo' if demo_mode else 'live'}:{digest}"


def _warn_fallback(exc: BaseException) -> None:
    global _FALLBACK_WARNED
    if not _FALLBACK_WARNED:
        _FALLBACK_WARNED = True
        logger.warning(
            "Capital.com shared session file unavailable (%s); using per-process state",
            type(exc).__name__,
        )


def _read_file(fd: int) -> Dict[str, Any]:
    os.lseek(fd, 0, os.SEEK_SET)
    chunks = []
    while True:
        chunk = os.read(fd, 65536)
        if not chunk:
            break
        chunks.append(chunk)
    raw = b"".join(chunks)
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_file(path: str, data: Dict[str, Any]) -> None:
    directory = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(prefix=".capital_session.", dir=directory)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, separators=(",", ":"))
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


@contextlib.contextmanager
def locked_state(key: str) -> Iterator[Dict[str, Any]]:
    """Yield the mutable state bucket for ``key`` under an exclusive lock.

    Changes made to the yielded dict are persisted when the block exits.
    """

    path = cache_path()
    lock_fd = None
    if fcntl is not None:
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            lock_fd = os.open(path + ".lock", os.O_RDWR | os.O_CREAT, 0o600)
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
        except OSError as exc:
            if lock_fd is not None:
                with contextlib.suppress(OSError):
                    os.close(lock_fd)
            lock_fd = None
            _warn_fallback(exc)
    if lock_fd is None:
        with _LOCAL_LOCK:
            yield _LOCAL_STATE.setdefault(key, {})
        return
    try:
        try:
            data_fd = os.open(path, os.O_RDONLY | os.O_CREAT, 0o600)
            try:
                data = _read_file(data_fd)
            finally:
                os.close(data_fd)
        except OSError:
            data = {}
        bucket = data.get(key)
        if not isinstance(bucket, dict):
            bucket = {}
        before = json.dumps(bucket, sort_keys=True)
        yield bucket
        if json.dumps(bucket, sort_keys=True) != before:
            data[key] = bucket
            try:
                _write_file(path, data)
            except OSError as exc:
                _warn_fallback(exc)
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        with contextlib.suppress(OSError):
            os.close(lock_fd)


@contextlib.contextmanager
def login_lock() -> Iterator[None]:
    """Serialise logins across processes so only one POST /session is in flight."""

    path = cache_path()
    fd = None
    if fcntl is not None:
        try:
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            fd = os.open(path + ".login.lock", os.O_RDWR | os.O_CREAT, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
        except OSError as exc:
            if fd is not None:
                with contextlib.suppress(OSError):
                    os.close(fd)
            fd = None
            _warn_fallback(exc)
    if fd is None:
        with _LOCAL_LOGIN_LOCK:
            yield
        return
    try:
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fd, fcntl.LOCK_UN)
        with contextlib.suppress(OSError):
            os.close(fd)


def session_is_fresh(bucket: Dict[str, Any], now: Optional[float] = None) -> bool:
    """Shared tokens exist and are inside the existing 50-minute refresh window.

    Idle expiry is handled by :func:`claim_keepalive` (a ping), not a re-login;
    a real 401 clears the shared tokens instead.
    """
    now = time.time() if now is None else now
    if not bucket.get("cst") or not bucket.get("x_security_token"):
        return False
    started = float(bucket.get("session_start_time") or 0.0)
    return (now - started) < SESSION_MAX_AGE_S


def claim_keepalive(key: str) -> Optional[Dict[str, str]]:
    """Claim the single keep-alive ping for a quiet shared session.

    Returns the tokens to ping with if this caller won the claim, else None.
    Claiming marks the session used, so other processes do not ping too.
    """

    with locked_state(key) as bucket:
        now = time.time()
        if not session_is_fresh(bucket, now):
            return None
        if now < float(bucket.get("rate_limit_until") or 0.0):
            return None
        started = float(bucket.get("session_start_time") or 0.0)
        last_used = max(started, float(bucket.get("last_used_at") or 0.0))
        if (now - last_used) < session_idle_refresh_s():
            return None
        bucket["last_used_at"] = now
        return {"cst": str(bucket["cst"]), "x_security_token": str(bucket["x_security_token"])}


def invalidate_session(key: str, cst: Optional[str]) -> None:
    """Drop shared tokens after a real 401, only if they are the ones that failed."""

    with locked_state(key) as bucket:
        if cst and bucket.get("cst") == cst:
            bucket.pop("cst", None)
            bucket.pop("x_security_token", None)


def with_jitter(seconds: float) -> float:
    """Add up to 10% (at least 0.25 s) random jitter so processes do not resume in lockstep."""

    seconds = max(0.0, float(seconds))
    return seconds + random.uniform(0.0, max(0.25, 0.1 * seconds))


def backoff_remaining(key: str) -> float:
    with locked_state(key) as bucket:
        return max(0.0, float(bucket.get("rate_limit_until") or 0.0) - time.time())


def record_backoff(key: str, seconds: float) -> float:
    """Extend the shared backoff; returns the shared backoff-until timestamp."""

    until = time.time() + max(0.0, float(seconds))
    with locked_state(key) as bucket:
        until = max(until, float(bucket.get("rate_limit_until") or 0.0))
        bucket["rate_limit_until"] = until
    return until


def parse_retry_after(headers: Any) -> Optional[float]:
    """Return Retry-After in seconds (delta-seconds or HTTP date), or None."""

    try:
        value = headers.get("Retry-After") if headers is not None else None
    except Exception:
        return None
    if value is None or not isinstance(value, (str, int, float)):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return max(0.0, float(text))
    except ValueError:
        pass
    try:
        return max(0.0, parsedate_to_datetime(text).timestamp() - time.time())
    except Exception:
        return None


def acquire_request_slot(key: str, *, is_order: bool = False) -> bool:
    """Block until a request may be sent without exceeding Capital's limits.

    Returns False if a shared 429 backoff is active (caller must not send).
    Also marks the shared session as used, which keeps the idle clock honest.
    """

    while True:
        with locked_state(key) as bucket:
            now = time.time()
            if now < float(bucket.get("rate_limit_until") or 0.0):
                return False
            window = [t for t in (bucket.get("request_times") or []) if isinstance(t, (int, float)) and now - t < 1.0]
            limit = max(1, int(max_requests_per_sec()))
            wait = 0.0
            if len(window) >= limit:
                wait = max(wait, 1.0 - (now - min(window)))
            if is_order:
                last_order = float(bucket.get("last_order_at") or 0.0)
                wait = max(wait, min_order_interval_s() - (now - last_order))
            if wait <= 0.0:
                window.append(now)
                bucket["request_times"] = window
                if is_order:
                    bucket["last_order_at"] = now
                if bucket.get("cst"):
                    bucket["last_used_at"] = now
                return True
        time.sleep(min(max(wait, 0.005), 1.0))
