"""Shared freshness rules for schumann_state.json readers.

Two clocks are checked separately:

  * ``timestamp`` — when the local daemon last wrote the file (daemon alive).
    Each reader keeps its own write window (120–600 s).
  * ``observed_at`` — when Tomsk measured the field (reading recent).
    Tomsk publishes about hourly, so a live reading is often 1–2 hours old.
    The shared cap is SCHUMANN_OBSERVED_MAX_AGE_SEC (default 7200 s),
    overridable by AUREON_SCHUMANN_OBSERVED_MAX_AGE_SEC.

If ``observed_at`` is present it must parse, and a write ``timestamp`` must
also be present and fresh — otherwise nothing proves the daemon is alive.
If ``observed_at`` is absent, freshness falls back to the write timestamp
and that reader's write window, as before.

Ages more than SCHUMANN_CLOCK_SKEW_SEC (60 s) in the future are refused
for both clocks. Naive ISO values are treated as UTC. This module is
stdlib-only so radar and fusion readers can import it without cycles.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

SCHUMANN_OBSERVED_MAX_AGE_SEC = 7200.0
SCHUMANN_CLOCK_SKEW_SEC = 60.0
ENV_SCHUMANN_OBSERVED_MAX_AGE_SEC = "AUREON_SCHUMANN_OBSERVED_MAX_AGE_SEC"


def schumann_observed_max_age_sec() -> float:
    raw = os.getenv(ENV_SCHUMANN_OBSERVED_MAX_AGE_SEC, "").strip()
    if not raw:
        return SCHUMANN_OBSERVED_MAX_AGE_SEC
    try:
        value = float(raw)
    except ValueError:
        return SCHUMANN_OBSERVED_MAX_AGE_SEC
    if value <= 0:
        return SCHUMANN_OBSERVED_MAX_AGE_SEC
    return value


def parse_schumann_clock(value: Any) -> Optional[datetime]:
    """Parse an ISO clock to aware UTC, or None. Naive values are UTC."""
    if value in (None, ""):
        return None
    try:
        ts = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def _age_seconds(now: datetime, ts: datetime) -> float:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return (now - ts).total_seconds()


@dataclass(frozen=True)
class SchumannFreshness:
    accepted: bool
    reason: Optional[str]
    has_observed_at: bool
    write_ts: Optional[datetime]
    observed_ts: Optional[datetime]
    write_age: Optional[float]
    observed_age: Optional[float]


def evaluate_schumann_freshness(
    data: dict,
    write_window_sec: float,
    now: Optional[datetime] = None,
) -> SchumannFreshness:
    """Judge a schumann_state.json payload.

    ``write_window_sec`` is the reader's existing daemon-alive window.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    write_ts = parse_schumann_clock(data.get("timestamp"))
    write_age = _age_seconds(now, write_ts) if write_ts is not None else None

    observed_raw = data.get("observed_at")
    has_observed = observed_raw not in (None, "")
    observed_ts = parse_schumann_clock(observed_raw) if has_observed else None
    observed_age = _age_seconds(now, observed_ts) if observed_ts is not None else None

    def reject(reason: str) -> SchumannFreshness:
        return SchumannFreshness(
            accepted=False,
            reason=reason,
            has_observed_at=has_observed,
            write_ts=write_ts,
            observed_ts=observed_ts,
            write_age=write_age,
            observed_age=observed_age,
        )

    def accept() -> SchumannFreshness:
        return SchumannFreshness(
            accepted=True,
            reason=None,
            has_observed_at=has_observed,
            write_ts=write_ts,
            observed_ts=observed_ts,
            write_age=write_age,
            observed_age=observed_age,
        )

    if has_observed:
        if observed_ts is None:
            return reject("state has unparseable observed_at")
        if write_ts is None:
            return reject(
                "state has observed_at but no write timestamp — daemon liveness unknown"
            )
        if write_age < -SCHUMANN_CLOCK_SKEW_SEC:
            return reject(f"write timestamp is in the future ({-write_age:.0f}s)")
        if write_age > write_window_sec:
            return reject(
                f"daemon write timestamp stale ({write_age:.0f}s > {write_window_sec:.0f}s)"
            )
        observed_max = schumann_observed_max_age_sec()
        if observed_age < -SCHUMANN_CLOCK_SKEW_SEC:
            return reject(f"observed_at is in the future ({-observed_age:.0f}s)")
        if observed_age > observed_max:
            return reject(
                f"observed_at stale ({observed_age:.0f}s > {observed_max:.0f}s)"
            )
        return accept()

    if write_ts is None:
        return reject("state has no valid timestamp")
    if write_age < -SCHUMANN_CLOCK_SKEW_SEC:
        return reject(f"write timestamp is in the future ({-write_age:.0f}s)")
    if write_age > write_window_sec:
        return reject(f"state stale ({write_age:.0f}s > {write_window_sec:.0f}s)")
    return accept()
