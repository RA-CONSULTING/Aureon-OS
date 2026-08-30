"""Aureon Operator HTTP security envelope.

Production mode is fail-closed: it requires a nonempty operator secret, a
positive request rate, and one HTTP process/replica while limiter state remains
in memory. Development and test modes retain explicit offline/local operation.
Forwarded client addresses are accepted only from configured trusted proxies.
"""

from __future__ import annotations

import hmac
import ipaddress
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict

_DEPLOYMENT_MODES = frozenset({"development", "test", "production"})
_PRODUCTION_RATE_RPS = 10.0
_DEFAULT_BURST = 20
_DEFAULT_MAX_BODY_BYTES = 256 * 1024


def _float_env(name: str, default: float) -> float:
    raw = str(os.environ.get(name, "") or "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc


def _int_env(name: str, default: int) -> int:
    raw = str(os.environ.get(name, "") or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc


def _trusted_proxy_networks(raw: str) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for value in raw.split(","):
        value = value.strip()
        if not value:
            continue
        try:
            networks.append(ipaddress.ip_network(value, strict=False))
        except ValueError as exc:
            raise ValueError(
                "AUREON_OPERATOR_TRUSTED_PROXY_CIDRS must be a comma-separated IP/CIDR list"
            ) from exc
    return tuple(networks)


def _parse_ip(value: str | None) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(str(value or "").strip())
    except ValueError:
        return None


def resolve_client_ip(
    remote_addr: str | None,
    forwarded_for: str | None,
    trusted_proxies: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (),
) -> str:
    """Resolve a client bucket without trusting an unverified proxy header."""
    peer = _parse_ip(remote_addr)
    if peer is None:
        return str(remote_addr or "anon").strip() or "anon"
    peer_key = peer.compressed
    if not trusted_proxies or not any(peer in network for network in trusted_proxies):
        return peer_key
    if not forwarded_for:
        return peer_key

    forwarded: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for value in forwarded_for.split(","):
        parsed = _parse_ip(value)
        if parsed is None:
            return peer_key
        forwarded.append(parsed)
    for candidate in reversed(forwarded):
        if not any(candidate in network for network in trusted_proxies):
            return candidate.compressed
    return peer_key


@dataclass(frozen=True)
class SecurityConfig:
    environment: str = "development"
    api_key: str = ""            # empty ⇒ auth disabled
    rate_rps: float = 0.0        # 0 ⇒ rate limiting disabled
    burst: int = 20              # bucket capacity
    max_body_bytes: int = 256 * 1024
    trusted_proxies: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = ()
    http_processes: int = 1
    replicas: int = 1

    @property
    def production(self) -> bool:
        return self.environment == "production"

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key.strip())

    @property
    def rate_enabled(self) -> bool:
        return self.rate_rps > 0

    def client_ip(self, remote_addr: str | None, forwarded_for: str | None) -> str:
        return resolve_client_ip(remote_addr, forwarded_for, self.trusted_proxies)

    def validate(self) -> SecurityConfig:
        if self.environment not in _DEPLOYMENT_MODES:
            raise ValueError(
                "AUREON_OPERATOR_ENV must be one of: development, test, production"
            )
        if self.rate_rps < 0:
            raise ValueError("AUREON_OPERATOR_RATE_RPS must be >= 0")
        if self.burst < 1:
            raise ValueError("AUREON_OPERATOR_RATE_BURST must be >= 1")
        if self.max_body_bytes < 1:
            raise ValueError("AUREON_OPERATOR_MAX_BODY must be >= 1")
        if self.http_processes < 1:
            raise ValueError("AUREON_OPERATOR_HTTP_PROCESSES must be >= 1")
        if self.replicas < 1:
            raise ValueError("AUREON_OPERATOR_REPLICAS must be >= 1")
        if self.production and not self.auth_enabled:
            raise ValueError(
                "AUREON_OPERATOR_API_KEY must contain a nonempty secret in production"
            )
        if self.production and not self.rate_enabled:
            raise ValueError("AUREON_OPERATOR_RATE_RPS must be > 0 in production")
        if self.production and self.http_processes != 1:
            raise ValueError(
                "AUREON_OPERATOR_HTTP_PROCESSES must be 1 while rate limiting is process-local"
            )
        if self.production and self.replicas != 1:
            raise ValueError(
                "AUREON_OPERATOR_REPLICAS must be 1 while rate limiting is process-local"
            )
        return self

    @classmethod
    def from_env(cls) -> SecurityConfig:
        environment = str(
            os.environ.get("AUREON_OPERATOR_ENV", "development") or "development"
        ).strip().lower()
        production = environment == "production"
        config = cls(
            environment=environment,
            api_key=str(os.environ.get("AUREON_OPERATOR_API_KEY", "") or ""),
            rate_rps=_float_env(
                "AUREON_OPERATOR_RATE_RPS",
                _PRODUCTION_RATE_RPS if production else 0.0,
            ),
            burst=_int_env("AUREON_OPERATOR_RATE_BURST", _DEFAULT_BURST),
            max_body_bytes=_int_env("AUREON_OPERATOR_MAX_BODY", _DEFAULT_MAX_BODY_BYTES),
            trusted_proxies=_trusted_proxy_networks(
                str(os.environ.get("AUREON_OPERATOR_TRUSTED_PROXY_CIDRS", "") or "")
            ),
            http_processes=_int_env("AUREON_OPERATOR_HTTP_PROCESSES", 1),
            replicas=_int_env("AUREON_OPERATOR_REPLICAS", 1),
        )
        return config.validate()


class TokenBucket:
    """Thread-safe, process-local token bucket keyed by resolved client IP."""

    def __init__(
        self,
        rate_rps: float,
        burst: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.rate = float(rate_rps)
        self.burst = float(max(1, burst))
        self._clock = clock
        self._state: Dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, float]:
        if self.rate <= 0:
            return True, 0.0
        now = self._clock()
        with self._lock:
            tokens, last = self._state.get(key, (self.burst, now))
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            if tokens >= 1.0:
                self._state[key] = (tokens - 1.0, now)
                return True, 0.0
            self._state[key] = (tokens, now)
            retry = (1.0 - tokens) / self.rate
            return False, round(retry, 3)


def check_bearer(auth_header: str | None, api_key: str) -> bool:
    """Constant-time bearer-token check."""
    if not api_key:
        return True
    if not auth_header or not auth_header.startswith("Bearer "):
        return False
    presented = auth_header[len("Bearer "):].strip()
    return hmac.compare_digest(presented, api_key)


__all__ = ["SecurityConfig", "TokenBucket", "check_bearer", "resolve_client_ip"]
