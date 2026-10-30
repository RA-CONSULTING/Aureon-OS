"""Streamable HTTP bind rule, bearer check, and per-client limits.

No key is read from disk. AUREON_PUBLIC_API_KEY is an optional runtime
environment variable. When it is unset, the public surface is served only if
AUREON_PUBLIC_OPEN=1. With neither one set, the listener must be 127.0.0.1.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

LOCAL_BIND = "127.0.0.1"
_DEFAULT_RATE_LIMIT = 120
_DEFAULT_RATE_WINDOW_S = 60.0
_DEFAULT_MAX_BODY = 1_048_576
_DEFAULT_TIMEOUT_S = 30.0


@dataclass(frozen=True)
class HttpLimits:
    """Limits for one server process. Values come from the environment."""

    api_key: str
    max_body_bytes: int
    rate_limit: int
    rate_window_s: float
    timeout_s: float


class RateLimiter:
    """Fixed window of request starts, keyed by client id."""

    def __init__(self, limit: int, window_s: float) -> None:
        self.limit = limit
        self.window_s = window_s
        self._hits: dict[str, list[float]] = {}

    def allow(self, client_id: str) -> bool:
        now = time.monotonic()
        window = self.window_s
        hits = [stamp for stamp in self._hits.get(client_id, []) if now - stamp < window]
        if len(hits) >= self.limit:
            self._hits[client_id] = hits
            return False
        hits.append(now)
        self._hits[client_id] = hits
        return True


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise SystemExit(f"{name} must be a positive integer")
    return value


def _positive_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a positive number") from exc
    if value <= 0:
        raise SystemExit(f"{name} must be a positive number")
    return value


def load_http_limits() -> HttpLimits:
    """Read the optional key and the limit environment variables."""

    return HttpLimits(
        api_key=os.environ.get("AUREON_PUBLIC_API_KEY", "").strip(),
        max_body_bytes=_positive_int("AUREON_PUBLIC_MAX_BODY_BYTES", _DEFAULT_MAX_BODY),
        rate_limit=_positive_int("AUREON_PUBLIC_RATE_LIMIT", _DEFAULT_RATE_LIMIT),
        rate_window_s=_positive_float("AUREON_PUBLIC_RATE_WINDOW_S", _DEFAULT_RATE_WINDOW_S),
        timeout_s=_positive_float("AUREON_PUBLIC_REQUEST_TIMEOUT_S", _DEFAULT_TIMEOUT_S),
    )


def public_bind_allowed(host: str) -> bool:
    """True when this host may listen.

    A bearer key or AUREON_PUBLIC_OPEN=1 allows the requested host. Otherwise
    only 127.0.0.1 is allowed.
    """

    if os.environ.get("AUREON_PUBLIC_API_KEY", "").strip():
        return True
    if os.environ.get("AUREON_PUBLIC_OPEN") == "1":
        return True
    return host == LOCAL_BIND


def resolve_http_bind(host: str) -> str:
    """Return host, or refuse a non-local bind when the surface is locked."""

    if public_bind_allowed(host):
        return host
    raise SystemExit(
        "Streamable HTTP binds to 127.0.0.1 unless AUREON_PUBLIC_API_KEY is set "
        "or AUREON_PUBLIC_OPEN=1."
    )


def _header_map(scope: dict) -> dict[str, str]:
    found: dict[str, str] = {}
    for key, value in scope.get("headers") or []:
        found[key.decode("latin1").lower()] = value.decode("latin1")
    return found


def _bearer(authorization: str) -> str | None:
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    if not token:
        return None
    return token


def _key_matches(presented: str, expected: str) -> bool:
    presented_bytes = presented.encode("utf-8")
    expected_bytes = expected.encode("utf-8")
    if len(presented_bytes) != len(expected_bytes):
        return False
    return hmac.compare_digest(presented_bytes, expected_bytes)


def _client_id(scope: dict, headers: dict[str, str]) -> str:
    """Bearer hash when a token is sent, otherwise the forwarded or socket address."""

    presented = _bearer(headers.get("authorization", ""))
    if presented is not None:
        digest = hashlib.sha256(presented.encode("utf-8")).hexdigest()
        return f"bearer:{digest}"
    forwarded = headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return f"ip:{forwarded}"
    client = scope.get("client")
    host = client[0] if isinstance(client, (list, tuple)) and client else "unknown"
    return f"ip:{host}"


def _content_length(headers: dict[str, str]) -> int | None:
    raw = headers.get("content-length", "").strip()
    if not raw or not raw.isdigit():
        return None
    return int(raw)


async def _reject(send, status: int, error: str, *, retry_after: str | None = None) -> None:
    body = json.dumps({"error": error}).encode("utf-8")
    header_list = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    if status == 401:
        header_list.append((b"www-authenticate", b"Bearer"))
    if retry_after is not None:
        header_list.append((b"retry-after", retry_after.encode("ascii")))
    await send({"type": "http.response.start", "status": status, "headers": header_list})
    await send({"type": "http.response.body", "body": body})


class PublicHttpMiddleware:
    """ASGI wrapper for the Streamable HTTP app. Lifespan scopes pass through."""

    def __init__(self, app, limits: HttpLimits, limiter: RateLimiter | None = None) -> None:
        self.app = app
        self.limits = limits
        self.limiter = limiter if limiter is not None else RateLimiter(limits.rate_limit, limits.rate_window_s)

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or ""
        if path != "/mcp" and not path.startswith("/mcp/"):
            await self.app(scope, receive, send)
            return
        headers = _header_map(scope)
        length = _content_length(headers)
        if length is not None and length > self.limits.max_body_bytes:
            await _reject(send, 429, "body_too_large")
            return
        client_id = _client_id(scope, headers)
        if not self.limiter.allow(client_id):
            retry_after = str(max(1, int(self.limits.rate_window_s)))
            await _reject(send, 429, "rate_limit", retry_after=retry_after)
            return
        if self.limits.api_key:
            presented = _bearer(headers.get("authorization", ""))
            if presented is None or not _key_matches(presented, self.limits.api_key):
                await _reject(send, 401, "unauthorized")
                return
        method = scope.get("method", "GET")
        if method != "POST":
            await self.app(scope, receive, send)
            return
        started = False

        async def send_wrapper(message) -> None:
            nonlocal started
            if message.get("type") == "http.response.start":
                started = True
            await send(message)

        try:
            await asyncio.wait_for(
                self.app(scope, receive, send_wrapper),
                timeout=self.limits.timeout_s,
            )
        except TimeoutError:
            if started:
                raise
            await _reject(send, 429, "timeout")
