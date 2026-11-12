"""Cross-process Capital.com session, login spacing, request pacing and backoff.

Every launcher organ runs in its own process, so a per-process dict cannot stop
nine processes each logging in to Capital.com. This module keeps one small JSON
state file guarded by a lock file (``fcntl.flock`` on POSIX, ``msvcrt.locking``
on Windows) so all processes on the box share:

* one session (CST / X-SECURITY-TOKEN) per account key and environment,
* the time of the last ``POST /session`` (Capital allows 1 per second per key),
* a sliding one-second window of request times (Capital allows 10 per second),
* the time of the last order/position creation (1 per 0.1 s),
* one backoff-until timestamp after a 429.

Capital's published limits: https://open-api.capital.com/ ("Rate limits").

If no lock works or the file cannot be written, backoff, login/order times and
the request window are still enforced from memory in this process; reads carry
on, and ORDER requests are refused (fail closed) with a distinctive log line.
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

try:  # POSIX
    import fcntl  # type: ignore
except Exception:  # pragma: no cover - platform dependent
    fcntl = None  # type: ignore
try:  # Windows
    import msvcrt  # type: ignore
except Exception:  # pragma: no cover - platform dependent
    msvcrt = None  # type: ignore

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
# Fields that must survive a failed file write: kept in memory and merged
# (max / union) into every read, so a write failure never drops a backoff.
_ENFORCED_MAX_FIELDS = ("rate_limit_until", "last_login_at", "last_order_at")
_TLS = threading.local()
ORDERS_REFUSED_LOG = "capital orders refused: shared lock unavailable"
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
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, separators=(",", ":"))
        os.replace(tmp, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _lock_fd(fd: int) -> bool:
    """Exclusive cross-process lock on ``fd``: flock (POSIX) or msvcrt (Windows)."""
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_EX)
        return True
    if msvcrt is not None:
        os.lseek(fd, 0, os.SEEK_SET)
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)  # one byte of the lock file
                return True
            except OSError:
                time.sleep(0.05)  # LK_LOCK gave up after its own retries; keep waiting
    return False


def _unlock_fd(fd: int) -> None:
    with contextlib.suppress(OSError):
        if fcntl is not None:
            fcntl.flock(fd, fcntl.LOCK_UN)
        elif msvcrt is not None:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)


def _open_lock(path: str) -> Optional[int]:
    """Open and lock ``path``; None if no lock mechanism works here."""
    if fcntl is None and msvcrt is None:
        _warn_fallback(RuntimeError("no fcntl or msvcrt"))
        return None
    fd = None
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
        if _lock_fd(fd):
            return fd
    except OSError as exc:
        _warn_fallback(exc)
    if fd is not None:
        with contextlib.suppress(OSError):
            os.close(fd)
    return None


def _merge_enforced(key: str, bucket: Dict[str, Any], now: float) -> None:
    local = _LOCAL_STATE.get(key) or {}
    for field in _ENFORCED_MAX_FIELDS:
        value = max(float(bucket.get(field) or 0.0), float(local.get(field) or 0.0))
        if value:
            bucket[field] = value
    times = {
        round(float(t), 6)
        for t in list(bucket.get("request_times") or []) + list(local.get("request_times") or [])
        if isinstance(t, (int, float)) and now - t < 1.0
    }
    bucket["request_times"] = sorted(times)


def _remember_enforced(key: str, bucket: Dict[str, Any]) -> None:
    local = _LOCAL_STATE.setdefault(key, {})
    for field in _ENFORCED_MAX_FIELDS:
        if bucket.get(field):
            local[field] = max(float(local.get(field) or 0.0), float(bucket[field]))
    local["request_times"] = list(bucket.get("request_times") or [])


def shared_state_ok() -> bool:
    """Whether this thread's last locked_state used a working lock and file write."""
    return bool(getattr(_TLS, "shared_ok", False))


@contextlib.contextmanager
def locked_state(key: str) -> Iterator[Dict[str, Any]]:
    """Yield the mutable state bucket for ``key`` under an exclusive lock.

    Changes made to the yielded dict are persisted when the block exits.
    Backoff, login and order times and the request window are also kept in
    memory, so a failed lock or write still enforces them in this process.
    ``shared_state_ok()`` reports afterwards whether the shared file was used.
    """

    path = cache_path()
    local_key = f"{path}|{key}"  # memory mirrors one state file
    lock_fd = _open_lock(path + ".lock")
    if lock_fd is None:
        _TLS.shared_ok = False
        with _LOCAL_LOCK:
            yield _LOCAL_STATE.setdefault(local_key, {})
        return
    _TLS.shared_ok = True
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
        with _LOCAL_LOCK:
            _merge_enforced(local_key, bucket, time.time())
        yield bucket
        with _LOCAL_LOCK:
            _remember_enforced(local_key, bucket)
        if json.dumps(bucket, sort_keys=True) != before:
            data[key] = bucket
            try:
                _write_file(path, data)
            except OSError as exc:
                _TLS.shared_ok = False
                _warn_fallback(exc)
    finally:
        _unlock_fd(lock_fd)
        with contextlib.suppress(OSError):
            os.close(lock_fd)


@contextlib.contextmanager
def login_lock() -> Iterator[None]:
    """Serialise logins across processes so only one POST /session is in flight."""

    fd = _open_lock(cache_path() + ".login.lock")
    if fd is None:
        with _LOCAL_LOGIN_LOCK:
            yield
        return
    try:
        yield
    finally:
        _unlock_fd(fd)
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


def acquire_request_slot(key: str, *, is_order: bool = False) -> Optional[str]:
    """Block until a request may be sent without exceeding Capital's limits.

    Returns None when the caller may send. Otherwise returns why not:
    ``"backoff"`` while a 429 backoff runs, or ``"shared_state_unavailable"``
    for an order when no working cross-process lock or file write exists
    (orders fail closed; reads continue with in-memory pacing).
    Also marks the shared session as used, which keeps the idle clock honest.
    """

    while True:
        wait = 0.0
        refused: Optional[str] = None
        granted = False
        with locked_state(key) as bucket:
            now = time.time()
            if now < float(bucket.get("rate_limit_until") or 0.0):
                refused = "backoff"
            elif is_order and not shared_state_ok():
                refused = "shared_state_unavailable"
            else:
                window = [t for t in (bucket.get("request_times") or []) if isinstance(t, (int, float)) and now - t < 1.0]
                limit = max(1, int(max_requests_per_sec()))
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
                    granted = True
        if granted and is_order and not shared_state_ok():
            refused = "shared_state_unavailable"  # the write that recorded it failed
        if refused == "shared_state_unavailable":
            logger.error("%s; not sending this order", ORDERS_REFUSED_LOG)
            return refused
        if refused or granted:
            return refused
        time.sleep(min(max(wait, 0.005), 1.0))
