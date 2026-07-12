"""
Aureon Operator — observability (Prometheus + structured logs).
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Two surfaces, both optional and both fail-safe:

  • Prometheus counters/histograms via ``prometheus_client`` (a declared repo
    dep). If the library is missing the whole module degrades to no-op shims, so
    nothing here can break an import or a test.
  • Structured JSON log lines (one per phase) on the ``aureon.operator.metrics``
    logger, for when a metrics endpoint isn't scraped.

Metric names follow the repo's ``aureon_*`` convention.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from typing import Any

logger = logging.getLogger("aureon.operator.metrics")

try:
    from prometheus_client import Counter, Histogram

    _HAS_PROM = True
except Exception:  # noqa: BLE001
    _HAS_PROM = False


class _NullMetric:
    """No-op stand-in when prometheus_client is unavailable."""

    def labels(self, *a, **k) -> _NullMetric:
        return self

    def inc(self, *a, **k) -> None:
        pass

    def observe(self, *a, **k) -> None:
        pass


def _counter(name: str, doc: str, labels=()):
    if _HAS_PROM:
        try:
            return Counter(name, doc, labels)
        except Exception:  # noqa: BLE001 — duplicate registration across reloads
            return _NullMetric()
    return _NullMetric()


def _histogram(name: str, doc: str, labels=()):
    if _HAS_PROM:
        try:
            return Histogram(name, doc, labels)
        except Exception:  # noqa: BLE001
            return _NullMetric()
    return _NullMetric()


# ── Metric handles ────────────────────────────────────────────────────────────
REQUESTS = _counter("aureon_operator_requests_total", "Operator prompts handled", ("outcome",))
PHASE_LATENCY = _histogram(
    "aureon_operator_phase_latency_seconds", "Per-phase latency", ("phase",)
)
PROVIDER_CALLS = _counter(
    "aureon_operator_provider_calls_total", "Per-line calls", ("provider", "result")
)
VETO_TOTAL = _counter("aureon_operator_veto_total", "Conscience verdicts", ("verdict",))
CONSENSUS_AGREEMENT = _histogram(
    "aureon_operator_consensus_agreement", "Cross-line agreement at collapse"
)
CACHE_EVENTS = _counter("aureon_operator_cache_total", "Cache hits/misses", ("event",))


class OperatorMetrics:
    """Thin facade the operator calls; respects config.metrics_enabled / structured_logs."""

    def __init__(self, enabled: bool = True, structured_logs: bool = True, trace_id: str = ""):
        self.enabled = enabled
        self.structured_logs = structured_logs
        self.trace_id = trace_id

    def _log(self, event: str, **fields: Any) -> None:
        if not self.structured_logs:
            return
        record = {"event": event, "trace_id": self.trace_id, **fields}
        logger.info(json.dumps(record, default=str))

    @contextmanager
    def phase(self, name: str):
        t0 = time.time()
        try:
            yield
        finally:
            dt = time.time() - t0
            if self.enabled:
                PHASE_LATENCY.labels(phase=name).observe(dt)
            self._log("phase", phase=name, latency_ms=round(dt * 1000, 2))

    def provider_call(self, provider: str, ok: bool, latency_ms: float) -> None:
        if self.enabled:
            PROVIDER_CALLS.labels(provider=provider, result="ok" if ok else "error").inc()
        self._log("provider_call", provider=provider, ok=ok, latency_ms=round(latency_ms, 2))

    def consensus(self, agreement: float, winner: str, n: int) -> None:
        if self.enabled:
            CONSENSUS_AGREEMENT.observe(float(agreement))
        self._log("consensus", agreement=round(agreement, 4), winner=winner, n_answers=n)

    def veto(self, verdict: str, blocked: bool) -> None:
        if self.enabled:
            VETO_TOTAL.labels(verdict=verdict).inc()
        self._log("veto", verdict=verdict, blocked=blocked)

    def cache(self, event: str) -> None:
        if self.enabled:
            CACHE_EVENTS.labels(event=event).inc()
        self._log("cache", cache_event=event)

    def request(self, outcome: str, elapsed_ms: float) -> None:
        if self.enabled:
            REQUESTS.labels(outcome=outcome).inc()
        self._log("request", outcome=outcome, elapsed_ms=round(elapsed_ms, 2))


def metrics_available() -> bool:
    return _HAS_PROM


__all__ = ["OperatorMetrics", "metrics_available"]
