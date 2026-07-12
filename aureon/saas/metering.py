"""
Aureon SaaS — usage metering (record-only, never blocks a request).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A bounded in-memory buffer of `UsageEvent`s flushed by one daemon thread to the
Supabase `saas_usage_events` table (PostgREST, service-role). This is METERING,
not billing: nothing here debits a balance.

Honesty rules:
  • Bounded buffer — when full, the oldest events are dropped and COUNTED.
  • Flush failures are logged, counted, and the batch is dropped — no silent
    success, no unbounded retry queues.
  • `stats()` reports the true sink: "disabled" (flag off), "prometheus-only"
    (flag on but Supabase env missing), or "supabase".

The flusher also owns the token-delta sweep: it diffs snapshots of the
process-wide per-provider token tally (aureon.operator.metrics) and emits one
untenanted `llm_tokens` event per provider per interval with usage. Per-tenant
token attribution is staged — provider fan-out runs in worker threads, so
claiming per-request attribution today would be dishonest.
"""

from __future__ import annotations

import logging
import os
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List

from aureon.saas.supabase_rest import SupabaseConfig, SupabaseRest

logger = logging.getLogger("aureon.saas.metering")

_USAGE_TABLE = "saas_usage_events"


@dataclass
class UsageEvent:
    """One metered unit of platform usage."""

    kind: str                       # "api_request" | "llm_tokens" | "fee_charge"
    tenant_id: str | None = None  # Supabase user id; None = unattributed
    quantity: float = 1.0
    unit: str = "request"           # "request" | "tokens" | "gbp"
    route: str = ""
    method: str = ""
    status: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_row(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "kind": self.kind,
            "route": self.route,
            "method": self.method,
            "status": int(self.status),
            "quantity": float(self.quantity),
            "unit": self.unit,
            "metadata": self.metadata,
        }


class MeteringBuffer:
    """Bounded event buffer with a background flusher. All methods are non-blocking."""

    def __init__(
        self,
        rest: SupabaseRest | None,
        maxlen: int = 5000,
        flush_interval_s: float = 10.0,
        enabled: bool = False,
    ) -> None:
        self._rest = rest
        self._enabled = enabled
        self._events: Deque[UsageEvent] = deque()
        self._maxlen = max(10, int(maxlen))
        self._flush_interval_s = max(1.0, float(flush_interval_s))
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._flushed = 0
        self._dropped = 0
        self._flush_failures = 0
        self._token_snapshot: Dict[str, Dict[str, int]] = {}

    # ── recording ──────────────────────────────────────────────────────────

    def record(self, event: UsageEvent) -> None:
        """O(1) append; drop-oldest (counted) when full; no-op when disabled."""
        if not self._enabled:
            return
        with self._lock:
            if len(self._events) >= self._maxlen:
                self._events.popleft()
                self._dropped += 1
            self._events.append(event)

    # ── flushing ───────────────────────────────────────────────────────────

    def _drain(self, limit: int = 500) -> List[UsageEvent]:
        with self._lock:
            batch: List[UsageEvent] = []
            while self._events and len(batch) < limit:
                batch.append(self._events.popleft())
            return batch

    def _sweep_tokens(self) -> None:
        """Diff the process token tally and emit one llm_tokens event per provider delta."""
        try:
            from aureon.operator.metrics import token_usage_totals

            current = token_usage_totals()
        except Exception:  # noqa: BLE001 — operator metrics unavailable
            return
        for provider, totals in current.items():
            prev = self._token_snapshot.get(provider, {"input_tokens": 0, "output_tokens": 0})
            d_in = totals["input_tokens"] - prev.get("input_tokens", 0)
            d_out = totals["output_tokens"] - prev.get("output_tokens", 0)
            if d_in > 0 or d_out > 0:
                self.record(UsageEvent(
                    kind="llm_tokens",
                    tenant_id=None,  # per-tenant token attribution is staged; see module docstring
                    quantity=float(d_in + d_out),
                    unit="tokens",
                    metadata={"provider": provider, "input_tokens": d_in, "output_tokens": d_out},
                ))
        self._token_snapshot = current

    def flush_now(self) -> int:
        """Synchronous flush of up to one batch. Returns rows written."""
        self._sweep_tokens()
        batch = self._drain()
        if not batch:
            return 0
        if self._rest is None or not self._rest.config.ok:
            # prometheus-only sink: events are counted in metrics but have no store.
            with self._lock:
                self._dropped += len(batch)
            return 0
        if self._rest.insert(_USAGE_TABLE, [e.to_row() for e in batch]):
            with self._lock:
                self._flushed += len(batch)
            return len(batch)
        with self._lock:
            self._flush_failures += 1
            self._dropped += len(batch)
        logger.warning("usage flush failed; dropped %d events", len(batch))
        return 0

    def _run(self) -> None:
        while not self._stop.wait(self._flush_interval_s):
            try:
                self.flush_now()
            except Exception as exc:  # noqa: BLE001 — the flusher must never die
                logger.warning("metering flusher error: %s", exc)

    def start(self) -> None:
        """Idempotent daemon-thread start (only meaningful when enabled)."""
        if not self._enabled or (self._thread is not None and self._thread.is_alive()):
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="aureon-metering", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    # ── reporting ──────────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    def stats(self) -> Dict[str, Any]:
        if not self._enabled:
            sink = "disabled"
        elif self._rest is None or not self._rest.config.ok:
            sink = "prometheus-only"
        else:
            sink = "supabase"
        with self._lock:
            return {
                "sink": sink,
                "pending": len(self._events),
                "flushed": self._flushed,
                "dropped": self._dropped,
                "flush_failures": self._flush_failures,
                "note": "llm_tokens events are per-provider and untenanted; "
                        "per-tenant token attribution is staged.",
            }


# ── module singleton ──────────────────────────────────────────────────────────

_BUFFER: MeteringBuffer | None = None
_BUFFER_LOCK = threading.Lock()


def _build_from_env() -> MeteringBuffer:
    enabled = str(os.environ.get("AUREON_BILLING_METERING", "") or "") == "1"
    config = SupabaseConfig.from_env()
    rest = SupabaseRest(config) if config.ok else None
    buf = MeteringBuffer(
        rest,
        maxlen=int(os.environ.get("AUREON_BILLING_BUFFER_MAX", "5000") or 5000),
        flush_interval_s=float(os.environ.get("AUREON_BILLING_FLUSH_S", "10") or 10),
        enabled=enabled,
    )
    if enabled:
        buf.start()
    return buf


def get_buffer() -> MeteringBuffer:
    global _BUFFER
    with _BUFFER_LOCK:
        if _BUFFER is None:
            _BUFFER = _build_from_env()
        return _BUFFER


def reset_buffer_for_tests() -> None:
    global _BUFFER
    with _BUFFER_LOCK:
        if _BUFFER is not None:
            _BUFFER.stop()
        _BUFFER = None


__all__ = ["UsageEvent", "MeteringBuffer", "get_buffer", "reset_buffer_for_tests"]
