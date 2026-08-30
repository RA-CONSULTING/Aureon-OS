"""HarmonicObserver production-mode gate.

Three modes controlled by ``AUREON_OBSERVER_MODE``:

  ``dry_run`` (default — chosen for safety on first deploy):
      Observer + bus consensus + wave predictor all RUN. Their outputs
      are computed and logged to ``state/observer_audit.jsonl`` so a
      reviewer can see what the system WOULD have done. Decisions
      flow through original (pre-observer) logic — no Vote 7 veto, no
      narrow-band threshold tightening, no Kelly buffer scaling.

  ``shadow``:
      Same as ``dry_run`` for decision *outcomes* (no veto, no scaling),
      but the audit log explicitly tags the run as "shadow" so post-hoc
      analysis can compare shadow recommendations against actual trade
      outcomes. Operator runs this for N days/weeks before flipping
      to ``live``.

  ``live``:
      Full Stages L/T/V/Y behaviour — observer vetoes, narrow-band
      threshold raises, Kelly buffer widens. This is the originally-
      designed integration.

Switching modes is a single env-var change followed by a daemon
restart; no code change needed. The audit log writes in every mode so
the operator can compare modes apples-to-apples.

Why default to dry_run instead of live: Stages A–AA were all smoke-
tested but none of them have ever influenced a real exchange order.
Until they have, "live" should require operator opt-in.
"""

from __future__ import annotations

import enum
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ObserverMode(enum.Enum):
    DRY_RUN = "dry_run"
    SHADOW = "shadow"
    LIVE = "live"


ENV_MODE = "AUREON_OBSERVER_MODE"
# Default flipped to LIVE on operator request: "everything must be live
# and production ready for all live data trading". Operators who want
# the safer dry_run / shadow flow set AUREON_OBSERVER_MODE explicitly.
# Promotion criteria + monitoring guidance still in
# docs/runbooks/HARMONIC_OBSERVER_PRODUCTION.md.
DEFAULT_MODE = ObserverMode.LIVE


# Module-level cache of the resolved mode. The env var is read once on
# first call to keep the hot path (every gate evaluation) cheap. To
# change mode at runtime: change env var, then call ``reload_mode()``.
_cached_mode: Optional[ObserverMode] = None
_mode_lock = threading.Lock()


def get_mode() -> ObserverMode:
    """Resolve the active mode from env, with fallback to DEFAULT_MODE.

    Anything we don't recognise (typo, missing var, malformed value)
    falls through to ``DEFAULT_MODE`` — currently ``LIVE`` per Stage
    AC's operator-set production posture. The env var is read case-
    insensitively so 'LIVE', 'live', 'Live' all work. Operators who
    want a safer first-deploy can either set
    ``AUREON_OBSERVER_MODE=dry_run`` explicitly or change
    ``DEFAULT_MODE`` at the top of this module.
    """
    global _cached_mode
    if _cached_mode is not None:
        return _cached_mode
    with _mode_lock:
        if _cached_mode is not None:
            return _cached_mode
        raw = os.environ.get(ENV_MODE, DEFAULT_MODE.value).strip().lower()
        for m in ObserverMode:
            if m.value == raw:
                _cached_mode = m
                logger.info("HarmonicObserver mode resolved: %s", m.value)
                return m
        logger.warning(
            "AUREON_OBSERVER_MODE=%r not recognised; falling back to DRY_RUN. "
            "Valid values: dry_run | shadow | live", raw,
        )
        _cached_mode = DEFAULT_MODE
        return DEFAULT_MODE


def reload_mode() -> ObserverMode:
    """Drop the cached mode so the next ``get_mode`` call re-reads env."""
    global _cached_mode
    with _mode_lock:
        _cached_mode = None
    return get_mode()


def is_live() -> bool:
    """True only when AUREON_OBSERVER_MODE=live. Used as the master
    switch for every observer-driven decision side-effect."""
    return get_mode() == ObserverMode.LIVE


def is_shadow() -> bool:
    return get_mode() == ObserverMode.SHADOW


def is_dry_run() -> bool:
    return get_mode() == ObserverMode.DRY_RUN


# ─── audit log ─────────────────────────────────────────────────────

AUDIT_LOG_PATH = (
    Path(__file__).resolve().parents[2] / "state" / "observer_audit.jsonl"
)


def audit(
    event: str,
    payload: Dict[str, Any],
    *,
    decision: Optional[str] = None,
    would_have_blocked: Optional[bool] = None,
    actually_blocked: Optional[bool] = None,
) -> None:
    """Append one observer-decision event to ``state/observer_audit.jsonl``.

    Always writes regardless of mode — the audit log is the operator's
    primary visibility into "what is the observer recommending?". In
    DRY_RUN / SHADOW modes ``actually_blocked`` will diverge from
    ``would_have_blocked`` and reading the log shows exactly which
    trades the LIVE mode would have changed.

    Failures are debug-logged; never raise into the trading hot path.
    """
    try:
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "ts": time.time(),
            "mode": get_mode().value,
            "event": event,
            "decision": decision,
            "would_have_blocked": would_have_blocked,
            "actually_blocked": actually_blocked,
            "payload": payload,
        }
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
    except Exception as exc:
        logger.debug("observer audit write failed: %s", exc)


# ─── decision-side helpers ─────────────────────────────────────────

def gate_buy_veto_active() -> bool:
    """Should ``queen_gated_buy`` actually veto on BEARISH high-conf
    consensus, or just record what it would have done?

    True only in LIVE mode. DRY_RUN and SHADOW always return False.
    """
    return is_live()


def gate_sell_veto_active() -> bool:
    """Should ``execute_sell_with_logging`` veto premature TP exits on
    BULLISH high-conf consensus, or just record?"""
    return is_live()


def narrow_band_threshold_active() -> bool:
    """Should the observer's coherence_score raise the multi-brain
    threshold (Stage L), or just record?"""
    return is_live()


def kelly_buffer_scaling_active() -> bool:
    """Should the Kelly gate widen ``r_prime_buffer`` based on the
    observer's coherence (Stage C/Y), or just record?"""
    return is_live()


def vote_addition_active() -> bool:
    """Should Brain 6 (per-symbol observer) and Brain 7 (bus consensus)
    contribute +1 votes to the multi-brain validation count (Stages
    L/T), or stay informational?

    The +1 votes are NOT vetoes — they only help approve trades. In
    DRY_RUN we still keep them off so the trade-decision count is
    bit-identical to pre-observer behaviour and any divergence in the
    audit log is diagnostic only.
    """
    return is_live()


def phase_veto_active() -> bool:
    """Should the SignalGate's phase-transition check actually block
    entries (PHASE_CRITICAL / high curvature), or just record what it
    would have done?

    The check itself had never executed before the P1 repair (it called
    methods the detector doesn't have), so arming it everywhere at once
    would be an untested behaviour change on live paths. Same contract
    as the other decision helpers: True only in LIVE; DRY_RUN and
    SHADOW audit ``would_have_blocked`` and allow.
    """
    return is_live()


def volatility_veto_active() -> bool:
    """Should the SignalGate's volatility-sentinel check actually block
    entries when predicted volatility risk crosses VOL_RISK_BLOCK, or
    just record? True only in LIVE (b46: the prediction can only ever
    tighten, and only once the operator runs live)."""
    return is_live()
