"""
Aureon Operator — API security envelope.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Optional, off-by-default hardening for the operator's HTTP surface:

  • Bearer auth — when AUREON_OPERATOR_API_KEY is set, /api/* requires
    `Authorization: Bearer <key>`; unset ⇒ open (dev/offline unchanged).
  • Rate limiting — a per-client token bucket (AUREON_OPERATOR_RATE_RPS, 0 =
    unlimited) → HTTP 429 + Retry-After.
  • Request-size cap — AUREON_OPERATOR_MAX_BODY bytes (default 256 KiB).

Pure stdlib + threading; no new dependency. Probe/scrape routes (/, /healthz,
/readyz, /metrics) are always open so orchestrators and Prometheus keep working.
"""

from __future__ import annotations

import hmac
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict


@dataclass
class SecurityConfig:
    api_key: str = ""            # empty ⇒ auth disabled
    rate_rps: float = 0.0        # 0 ⇒ rate limiting disabled
    burst: int = 20              # bucket capacity
    max_body_bytes: int = 256 * 1024

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_key.strip())

    @property
    def rate_enabled(self) -> bool:
        return self.rate_rps > 0

    @classmethod
    def from_env(cls) -> SecurityConfig:
        def _f(name: str, default: float) -> float:
            try:
                return float(os.environ.get(name, "") or default)
            except (TypeError, ValueError):
                return default

        def _i(name: str, default: int) -> int:
            try:
                return int(os.environ.get(name, "") or default)
            except (TypeError, ValueError):
                return default

        return cls(
            api_key=str(os.environ.get("AUREON_OPERATOR_API_KEY", "") or ""),
            rate_rps=_f("AUREON_OPERATOR_RATE_RPS", 0.0),
            burst=_i("AUREON_OPERATOR_RATE_BURST", 20),
            max_body_bytes=_i("AUREON_OPERATOR_MAX_BODY", 256 * 1024),
        )


class TokenBucket:
    """Thread-safe per-key token bucket. Returns (allowed, retry_after_seconds)."""

    def __init__(self, rate_rps: float, burst: int, clock=time.monotonic):
        self.rate = float(rate_rps)
        self.burst = float(max(1, burst))
        self._clock = clock
        self._state: Dict[str, tuple] = {}   # key -> (tokens, last_ts)
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple:
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


__all__ = ["SecurityConfig", "TokenBucket", "check_bearer"]
