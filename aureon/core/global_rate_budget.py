#!/usr/bin/env python3
"""
Global Rate Budget - Priority-based API rate limiting

Implements priority buckets for API requests:
- EXECUTION (highest): Trading orders, fills
- POSITIONS (medium): Account positions, balances
- QUOTES (lowest): Market data, quotes

Ensures critical operations get priority during rate limit pressure.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import time
import threading
import logging
import os
from enum import Enum
from typing import Dict, Optional
try:
    from aureon.core.rate_limiter_v2 import AdaptiveRateLimiter
except ImportError:
    from aureon.core.rate_limiter_v2 import AdaptiveRateLimiter

# Metrics (optional)
try:
    from aureon.core.metrics import global_budget_requests_total
    METRICS_AVAILABLE = True
except Exception:
    METRICS_AVAILABLE = False

logger = logging.getLogger(__name__)

class RequestPriority(Enum):
    """Priority levels for API requests."""
    EXECUTION = 1  # Trading orders (highest priority)
    POSITIONS = 2  # Account/balance queries
    QUOTES = 3     # Market data (lowest priority)

class GlobalRateBudget:
    """
    Global rate budget with priority-based allocation.

    During rate limit pressure, higher priority requests get preference.
    Lower priority requests may be delayed or rejected.
    """

    def __init__(self, total_rate_per_second: float = 5.0, total_burst: float = 10.0):
        """
        Initialize global rate budget.

        Args:
            total_rate_per_second: Total API calls allowed per second across all priorities
            total_burst: Maximum burst capacity
        """
        self.total_rate = total_rate_per_second
        self.total_burst = total_burst

        # Priority-specific rate limiters
        # Execution gets 40% of total rate, Positions 30%, Quotes 30%
        exec_rate = total_rate_per_second * 0.4
        pos_rate = total_rate_per_second * 0.3
        quote_rate = total_rate_per_second * 0.3

        exec_burst = max(1, int(total_burst * 0.5))  # Execution can burst more
        pos_burst = max(1, int(total_burst * 0.3))
        quote_burst = max(1, int(total_burst * 0.2))

        self._rate_limiters = {
            RequestPriority.EXECUTION: AdaptiveRateLimiter(
                trading_rate=exec_rate, data_rate=exec_rate,
                trading_capacity=exec_burst, data_capacity=exec_burst,
                name='global_execution'
            ),
            RequestPriority.POSITIONS: AdaptiveRateLimiter(
                trading_rate=pos_rate, data_rate=pos_rate,
                trading_capacity=pos_burst, data_capacity=pos_burst,
                name='global_positions'
            ),
            RequestPriority.QUOTES: AdaptiveRateLimiter(
                trading_rate=quote_rate, data_rate=quote_rate,
                trading_capacity=quote_burst, data_capacity=quote_burst,
                name='global_quotes'
            )
        }

        # Backoff tracking for lower priorities when higher priorities are active
        self._backoff_until: Dict[RequestPriority, float] = {
            priority: 0.0 for priority in RequestPriority
        }

        self._lock = threading.Lock()

        # Stats
        self.requests_processed = {priority: 0 for priority in RequestPriority}
        self.requests_delayed = {priority: 0 for priority in RequestPriority}
        self.requests_rejected = {priority: 0 for priority in RequestPriority}

    def wait_for_slot(self, priority: RequestPriority, is_trading: bool = False) -> bool:
        """
        Wait for a rate limit slot for the given priority.

        Args:
            priority: Request priority level
            is_trading: Whether this is a trading operation

        Returns:
            True if slot granted, False if rejected due to high-priority backoff
        """
        with self._lock:
            current_time = time.time()

            # Check if we're in backoff from higher priority requests
            if current_time < self._backoff_until[priority]:
                self.requests_rejected[priority] += 1
                if METRICS_AVAILABLE:
                    try:
                        global_budget_requests_total.inc(1, priority=priority.name, status='rejected')
                    except Exception:
                        pass
                return False

            # Try to get a slot from this priority's limiter
            limiter = self._rate_limiters[priority]
            try:
                if is_trading:
                    limiter.wait_trading()
                else:
                    limiter.wait_data()
            except Exception as e:
                logger.warning(f"Rate limiter error for {priority}: {e}")
                # Still allow the request but mark as delayed
                self.requests_delayed[priority] += 1
                if METRICS_AVAILABLE:
                    try:
                        global_budget_requests_total.inc(1, priority=priority.name, status='delayed')
                    except Exception:
                        pass

            self.requests_processed[priority] += 1
            if METRICS_AVAILABLE:
                try:
                    global_budget_requests_total.inc(1, priority=priority.name, status='processed')
                except Exception:
                    pass

            # If this is a high-priority request, impose backoff on lower priorities
            if priority == RequestPriority.EXECUTION:
                # Block positions and quotes for 0.5 seconds
                self._backoff_until[RequestPriority.POSITIONS] = current_time + 0.5
                self._backoff_until[RequestPriority.QUOTES] = current_time + 0.5
            elif priority == RequestPriority.POSITIONS:
                # Block quotes for 0.2 seconds
                self._backoff_until[RequestPriority.QUOTES] = current_time + 0.2

            return True

    def on_429_error(self, priority: RequestPriority):
        """Handle 429 error by triggering backoff for this priority level."""
        with self._lock:
            current_time = time.time()

            # Trigger backoff for this priority and all lower priorities
            backoff_time = 2.0  # Base backoff

            for p in RequestPriority:
                if p.value >= priority.value:  # This priority and lower
                    self._backoff_until[p] = max(
                        self._backoff_until[p],
                        current_time + backoff_time
                    )
                    backoff_time *= 0.5  # Shorter backoff for lower priorities

            # Also trigger adaptive backoff in the specific limiter
            if priority in self._rate_limiters:
                self._rate_limiters[priority].on_429_error()

    def get_stats(self) -> Dict:
        """Get budget statistics."""
        with self._lock:
            return {
                "total_rate_per_second": self.total_rate,
                "total_burst": self.total_burst,
                "requests_processed": dict(self.requests_processed),
                "requests_delayed": dict(self.requests_delayed),
                "requests_rejected": dict(self.requests_rejected),
                "active_backoffs": {
                    priority.name: max(0, until - time.time())
                    for priority, until in self._backoff_until.items()
                }
            }

# Global instance
_global_rate_budget: Optional[GlobalRateBudget] = None

def get_global_rate_budget() -> GlobalRateBudget:
    """Get or create the global rate budget instance."""
    global _global_rate_budget
    if _global_rate_budget is None:
        # Configure from environment
        try:
            total_rate = float(os.getenv('GLOBAL_RATE_BUDGET_PER_SECOND', '5.0'))
            total_burst = float(os.getenv('GLOBAL_RATE_BUDGET_BURST', '10.0'))
        except Exception:
            total_rate = 5.0
            total_burst = 10.0

        _global_rate_budget = GlobalRateBudget(total_rate, total_burst)
        logger.info(f"GlobalRateBudget initialized: {total_rate}/sec, burst={total_burst}")

    return _global_rate_budget

def classify_request_type(endpoint: str, method: str = 'GET') -> RequestPriority:
    """
    Classify API request type based on endpoint.

    Args:
        endpoint: API endpoint path
        method: HTTP method

    Returns:
        RequestPriority for this endpoint
    """
    endpoint = endpoint.lower()

    # Trading execution (highest priority)
    if any(keyword in endpoint for keyword in ['order', 'trade', 'fill', 'execution']):
        return RequestPriority.EXECUTION

    # Account/positions (medium priority)
    if any(keyword in endpoint for keyword in ['account', 'position', 'balance', 'portfolio']):
        return RequestPriority.POSITIONS

    # Market data (lowest priority)
    if any(keyword in endpoint for keyword in ['quote', 'bar', 'trade', 'price', 'market']):
        return RequestPriority.QUOTES

    # Default to quotes for unknown endpoints
    return RequestPriority.QUOTES


# ───────────────────────── per-host budget registry ─────────────────────────
# The radar-side exchange clients each get their own GlobalRateBudget sized to
# the host's real tolerance. Priority buckets guarantee that account/position
# reads (POSITIONS) and order/session writes (EXECUTION) keep reserved slots
# that analytics market-data reads (QUOTES) can never consume.
#
# Env overrides per host:
#   AUREON_RATE_BUDGET_<HOST_SLUG>_PER_SEC   (dots/dashes → underscores, upper)
#   AUREON_RATE_BUDGET_<HOST_SLUG>_BURST
# Global kill-switch: AUREON_RATE_BUDGET_ENABLED=0 disables host budgets
# (get_host_rate_budget returns None → callers run unbudgeted).

HOST_BUDGET_DEFAULTS: Dict[str, Dict[str, float]] = {
    # Kraken spot: conservative, ~1 req/3s matched to a public+private mix.
    'api.kraken.com': {'rate': 1.0 / 3.0, 'burst': 2.0},
    # Capital.com is aggressively limited upstream; the portfolio writer
    # probes every 60s and must never be starved by analytics.
    'api-capital.backend-capital.com': {'rate': 0.34, 'burst': 4.0},
    'demo-api-capital.backend-capital.com': {'rate': 0.34, 'burst': 4.0},
    # Binance public data: generous (quote bucket ≈ 9/min on top of the
    # client's own TokenBucket) while signed/account reads stay reserved.
    'api.binance.com': {'rate': 0.5, 'burst': 6.0},
    'testnet.binance.vision': {'rate': 0.5, 'burst': 6.0},
}

_HOST_BUDGET_FALLBACK = {'rate': 0.2, 'burst': 2.0}
_host_budgets: Dict[str, GlobalRateBudget] = {}
_host_budgets_lock = threading.Lock()


def _host_env_slug(host: str) -> str:
    slug = []
    for ch in str(host or '').lower():
        slug.append(ch if ch.isalnum() else '_')
    return ''.join(slug).strip('_').upper()


def get_host_rate_budget(host: str) -> Optional[GlobalRateBudget]:
    """Get (or lazily create) the GlobalRateBudget for one API host.

    Returns None when host budgets are disabled via
    AUREON_RATE_BUDGET_ENABLED=0 or the host is empty.
    """
    host = str(host or '').strip().lower()
    if not host:
        return None
    if os.getenv('AUREON_RATE_BUDGET_ENABLED', '1').strip().lower() in {'0', 'false', 'off', 'no'}:
        return None

    with _host_budgets_lock:
        existing = _host_budgets.get(host)
        if existing is not None:
            return existing

        profile = dict(HOST_BUDGET_DEFAULTS.get(host, _HOST_BUDGET_FALLBACK))
        slug = _host_env_slug(host)
        try:
            override_rate = os.getenv(f'AUREON_RATE_BUDGET_{slug}_PER_SEC')
            if override_rate:
                profile['rate'] = max(0.01, float(override_rate))
            override_burst = os.getenv(f'AUREON_RATE_BUDGET_{slug}_BURST')
            if override_burst:
                profile['burst'] = max(1.0, float(override_burst))
        except Exception:
            pass

        budget = GlobalRateBudget(
            total_rate_per_second=profile['rate'],
            total_burst=profile['burst'],
        )
        _host_budgets[host] = budget
        logger.info(
            "Host rate budget initialized: %s -> %.3f/sec burst=%.1f",
            host, profile['rate'], profile['burst'],
        )
        return budget


def wait_for_slot_deferred(
    budget: GlobalRateBudget,
    priority: RequestPriority,
    *,
    is_trading: bool = False,
    max_wait_s: float = 10.0,
    poll_s: float = 0.25,
) -> bool:
    """Queue for a rate-limit slot without ever raising.

    Loops on wait_for_slot (which grants immediately, blocks for tokens, or
    returns False while a higher-priority backoff defers this priority) until
    the slot is granted or max_wait_s elapses. Read paths use this so a
    throttled caller is deferred, never crashed; write paths treat a False
    return as fail-closed and refuse to send.

    If the limiter itself raises, trading requests (is_trading=True) get
    False so order writes fail closed; read requests still get True so a
    broken limiter never crashes a read path.
    """
    deadline = time.time() + max(0.0, float(max_wait_s))
    while True:
        try:
            if budget.wait_for_slot(priority, is_trading):
                return True
        except Exception as exc:  # limiter internals must never crash a caller
            logger.warning("wait_for_slot_deferred error (%s): %s", priority.name, exc)
            if is_trading:
                return False  # fail closed: never send an order on a broken limiter
            return True  # one uncounted read beats a crashed read path
        if time.time() >= deadline:
            return False
        time.sleep(max(0.05, float(poll_s)))
