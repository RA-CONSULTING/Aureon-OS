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
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass

LOCAL_BIND = "127.0.0.1"
_DEFAULT_RATE_LIMIT = 120
_DEFAULT_RATE_WINDOW_S = 60.0
_DEFAULT_MAX_BODY = 1_048_576
_DEFAULT_TIMEOUT_S = 30.0
_DEFAULT_TRUSTED_HOPS = 1
_DEFAULT_MAX_CLIENTS = 4096
# The public worker pool is 4. One live session holds the SSE GET and a POST
# at the same time, so the cap stays at that same low number.
_DEFAULT_MAX_INFLIGHT = 4


@dataclass(frozen=True)
class HttpLimits:
    """Limits for one server process. Values come from the environment."""

    api_key: str
    max_body_bytes: int
    rate_limit: int
    rate_window_s: float
    timeout_s: float
    trusted_hops: int = _DEFAULT_TRUSTED_HOPS
    max_clients: int = _DEFAULT_MAX_CLIENTS
    max_inflight: int = _DEFAULT_MAX_INFLIGHT


class RateLimiter:
    """Fixed window of request starts, keyed by client id.

    Expired windows are dropped. The table keeps at most ``max_clients``
    ids and evicts the least recently used id when a new one arrives.
    """

    def __init__(
        self,
        limit: int,
        window_s: float,
        max_clients: int = _DEFAULT_MAX_CLIENTS,
        now: Callable[[], float] | None = None,
    ) -> None:
        self.limit = limit
        self.window_s = window_s
        self.max_clients = max_clients
        self._now = now or time.monotonic
        self._hits: OrderedDict[str, list[float]] = OrderedDict()

    def allow(self, client_id: str) -> bool:
        now = self._now()
        self._evict_expired(now)
        if client_id in self._hits:
            self._hits.move_to_end(client_id)
        elif len(self._hits) >= self.max_clients:
            self._hits.popitem(last=False)
        hits = [stamp for stamp in self._hits.get(client_id, []) if now - stamp < self.window_s]
        if len(hits) >= self.limit:
            self._hits[client_id] = hits
            self._hits.move_to_end(client_id)
            return False
        hits.append(now)
        self._hits[client_id] = hits
        self._hits.move_to_end(client_id)
        return True

    def _evict_expired(self, now: float) -> None:
        expired = [
            client_id
            for client_id, hits in self._hits.items()
            if not hits or now - hits[-1] >= self.window_s
        ]
        for client_id in expired:
            del self._hits[client_id]


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
        trusted_hops=_nonnegative_int("AUREON_PUBLIC_TRUSTED_HOPS", _DEFAULT_TRUSTED_HOPS),
        max_clients=_positive_int("AUREON_PUBLIC_RATE_MAX_CLIENTS", _DEFAULT_MAX_CLIENTS),
        max_inflight=_positive_int("AUREON_PUBLIC_MAX_INFLIGHT", _DEFAULT_MAX_INFLIGHT),
    )


def _nonnegative_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be a non-negative integer") from exc
    if value < 0:
        raise SystemExit(f"{name} must be a non-negative integer")
    return value


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


def _socket_peer(scope: dict) -> str:
    client = scope.get("client")
    if isinstance(client, (list, tuple)) and client and client[0]:
        return str(client[0])
    return "unknown"


def _forwarded_hops(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def client_address(scope: dict, headers: dict[str, str], trusted_hops: int) -> str:
    """Address appended by the trusted proxy, or the socket peer.

    The first ``X-Forwarded-For`` value is the one a client can set. A header
    that is only that first hop is not trusted, and the socket peer is used.
    ``trusted_hops`` counts appended hops from the right. The chosen hop is
    used only when it sits after that first value. Hugging Face's appended
    peer is the last hop when the header has that extra hop and
    ``trusted_hops`` is 1.
    """

    peer = _socket_peer(scope)
    if trusted_hops <= 0:
        return peer
    hops = _forwarded_hops(headers.get("x-forwarded-for", ""))
    if len(hops) <= trusted_hops:
        return peer
    return hops[-trusted_hops]


def _client_id(scope: dict, headers: dict[str, str], limits: HttpLimits) -> str:
    """Bucket by address. The bearer is the id only when it matches the configured key.

    Open mode has no configured key, so a presented bearer is never the client id.
    """

    address = client_address(scope, headers, limits.trusted_hops)
    if limits.api_key:
        presented = _bearer(headers.get("authorization", ""))
        if presented is not None and _key_matches(presented, limits.api_key):
            digest = hashlib.sha256(presented.encode("utf-8")).hexdigest()
            return f"bearer:{digest}"
    return f"ip:{address}"


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
        self.limiter = limiter if limiter is not None else RateLimiter(
            limits.rate_limit,
            limits.rate_window_s,
            max_clients=limits.max_clients,
        )
        self._inflight = 0
        self._inflight_lock = asyncio.Lock()

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path") or ""
        if path != "/mcp" and not path.startswith("/mcp/"):
            await self.app(scope, receive, send)
            return
        headers = _header_map(scope)
        client_id = _client_id(scope, headers, self.limits)
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
        if method == "POST":
            declared = _content_length(headers)
            if declared is not None and declared > self.limits.max_body_bytes:
                await _reject(send, 413, "body_too_large")
                return
            receive = await _bounded_receive(receive, self.limits.max_body_bytes, send)
            if receive is None:
                return
        if not await self._acquire_inflight():
            await _reject(send, 503, "busy")
            return
        try:
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
                await _reject(send, 504, "timeout")
        finally:
            await self._release_inflight()

    async def _acquire_inflight(self) -> bool:
        async with self._inflight_lock:
            if self._inflight >= self.limits.max_inflight:
                return False
            self._inflight += 1
            return True

    async def _release_inflight(self) -> None:
        async with self._inflight_lock:
            self._inflight -= 1


async def _bounded_receive(receive, max_body: int, send):
    """Buffer a POST body and reject it once the arrived bytes pass the cap.

    Chunked requests omit content-length. The count is the bytes ``receive``
    yields, not the header.
    """

    buffered: list[dict] = []
    total = 0
    empty_spins = 0
    while True:
        message = await receive()
        kind = message.get("type")
        if kind != "http.request":
            buffered.append(message)
            if kind == "http.disconnect":
                break
            continue
        chunk = message.get("body") or b""
        total += len(chunk)
        if total > max_body:
            await _reject(send, 413, "body_too_large")
            return None
        buffered.append(message)
        if not message.get("more_body", False):
            break
        if not chunk:
            empty_spins += 1
            if empty_spins > 8:
                break
    index = 0

    async def replay():
        nonlocal index
        if index < len(buffered):
            message = buffered[index]
            index += 1
            return message
        return await receive()

    return replay
