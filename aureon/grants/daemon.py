"""The grant organ — a daemon that keeps the funding pipeline in the organism's awareness.

Until now the grant work lived entirely outside the code: an operator run would
author artifacts by hand, and nothing in Aureon could see the pipeline, notice a
deadline, or act on one. This daemon closes that loop. It reads the ledger,
publishes what it finds onto the thought bus, and contributes its urgency to the
shared HNC field as a subfield — so the rest of the organism can feel funding
pressure the same way it feels market or affect pressure.

**It paces itself.** Breath interval is φ-scaled and driven by real urgency: a
calm pipeline breathes slowly (~φ² × base), a critical deadline breathes fast.
The organism speeds up as the deadline approaches, without being told to.

**It never submits.** ``autopilot_status.json`` reserves final submission for
explicit human confirmation, and this daemon holds that line: it is read-only
over the ledger and raises awareness, nothing more. Drafting, packaging and
submitting stay with the operator and with Gary.
"""

from __future__ import annotations

import logging
import os
import signal
import time
from datetime import datetime, timezone
from typing import Any

from aureon.grants.ledger import configured_routes, read_pipeline
from aureon.grants.schemas import PipelineState
from aureon.harmonic.phi_bridge import PHI

LOG = logging.getLogger("aureon.grants.daemon")

# Breath bounds in seconds. These are *guard rails*, not the operating band:
# over urgency 0→1 the φ curve below spans only 1456s→556s, so MAX is reached
# solely by an unknown urgency and MIN is never reached at all. They exist so a
# future change to BASE_INTERVAL_S cannot send the daemon into a spin or a coma.
BASE_INTERVAL_S = 900.0
MIN_INTERVAL_S = 60.0
MAX_INTERVAL_S = 3600.0

TOPIC_PULSE = "grants.pipeline.pulse"
TOPIC_ALERT = "grants.deadline.alert"

_running = True


def breath_interval(urgency: float | None) -> float:
    """Seconds until the next read, from real deadline pressure.

    Strictly decreasing in urgency, and the clamp cannot invert that (it is a
    monotone map applied to a monotone curve). The measured band is:

    ==============  ============================================
    urgency         interval
    ==============  ============================================
    ``None``        3600.0s — nothing dated is known, breathe slowest
    0.0             1456.2s — ``BASE × φ``
    0.5              900.0s — ``BASE`` exactly, the geometric midpoint
    1.0              556.2s — ``BASE ÷ φ``
    ==============  ============================================

    Note what this does **not** do: urgency 1.0 reaches ``BASE ÷ φ``, not
    ``MIN_INTERVAL_S``. The φ curve spans a single factor of φ² end to end, so
    neither clamp binds anywhere in [0, 1] — they only guard against a future
    change to ``BASE_INTERVAL_S``. An overdue pipeline therefore breathes every
    ~9 minutes, not every minute.
    """
    if urgency is None:
        return MAX_INTERVAL_S
    u = max(0.0, min(1.0, urgency))
    # φ-scaled decay: slow when calm, fast when pressed.
    interval = BASE_INTERVAL_S * (PHI ** (1.0 - 2.0 * u))
    return max(MIN_INTERVAL_S, min(MAX_INTERVAL_S, interval))


def _publish(bus: Any, state: PipelineState) -> None:
    """Publish the pipeline read onto the thought bus. Guarded: never fatal."""
    if bus is None:
        return
    try:
        from aureon.core.aureon_thought_bus import Thought

        bus.publish(Thought(source="grants_daemon", topic=TOPIC_PULSE, payload=state.to_dict()))
        for alert in state.alerts:
            if alert.severity in ("overdue", "critical"):
                bus.publish(Thought(source="grants_daemon", topic=TOPIC_ALERT, payload=alert.to_dict()))
    except Exception:  # noqa: BLE001 — awareness must never crash the organ
        LOG.debug("thought bus publish skipped", exc_info=True)


def _publish_field(state: PipelineState) -> None:
    """Contribute grant urgency to the shared HNC field as a subfield.

    Only published when there is a real reading. With no dated open application
    there is no urgency, and an absent contribution is correct — publishing a 0
    would tell the organism the pipeline is calm when in truth it is unknown.
    """
    if state.urgency is None:
        return
    try:
        from aureon.core.hnc_field import publish_subfield

        # A pressed pipeline lowers the symbolic life score: unmet obligations
        # are a real cost to the organism, not a neutral fact.
        publish_subfield("grants", type("GrantField", (), {
            "symbolic_life_score": 1.0 - state.urgency,
            "coherence_gamma": None,
            "consciousness_level": None,
        })())
    except Exception:  # noqa: BLE001
        LOG.debug("subfield publish skipped", exc_info=True)


def run_once(bus: Any = None, *, now: datetime | None = None) -> PipelineState:
    """One breath: read, publish, report. The unit the daemon repeats."""
    state = read_pipeline(now=now)
    if not state.available:
        LOG.warning("grant pipeline unavailable: %s", state.blocker)
        return state

    overdue = [a for a in state.alerts if a.severity == "overdue"]
    LOG.info(
        "grants: %d applications (%d open), %d artifacts, urgency=%s, %d alert(s), %d OVERDUE",
        len(state.applications), state.open_count, state.artifact_count,
        "unknown" if state.urgency is None else f"{state.urgency:.2f}",
        len(state.alerts), len(overdue),
    )
    for alert in overdue:
        LOG.warning("OVERDUE by %.1fd: %s (%s)", -alert.days_remaining, alert.name, alert.funder)

    _publish(bus, state)
    _publish_field(state)
    return state


def _stop(signum, frame) -> None:  # noqa: ANN001, ARG001
    global _running
    _running = False
    LOG.info("grant daemon: stop signal received")


def main(argv: list[str] | None = None) -> int:
    """Run the grant organ until stopped. Wired into the launcher."""
    import argparse

    parser = argparse.ArgumentParser(description="Aureon grant pipeline daemon (read-only).")
    parser.add_argument("--once", action="store_true", help="single read, then exit")
    parser.add_argument("--interval", type=float, default=None,
                        help="fixed seconds between reads (default: field-paced by urgency)")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=os.getenv("AUREON_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Give the AUREON_GRANT_* variables their consumer.
    try:
        from aureon.core.aureon_env import load_aureon_environment

        load_aureon_environment()
    except Exception:  # noqa: BLE001
        LOG.debug("env bootstrap skipped", exc_info=True)

    bus = None
    try:
        from aureon.core.aureon_thought_bus import get_thought_bus

        bus = get_thought_bus()
    except Exception:  # noqa: BLE001
        LOG.warning("thought bus unavailable — running without publication")

    routes = configured_routes()
    LOG.info("grant organ waking: %d configured route variable(s)", len(routes))

    if args.once:
        state = run_once(bus)
        return 0 if state.available else 1

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _stop)
        except (ValueError, OSError):
            pass  # not on the main thread, or unsupported on this platform

    while _running:
        state = run_once(bus)
        wait = args.interval if args.interval else breath_interval(state.urgency)
        LOG.debug("next breath in %.0fs", wait)
        # Sleep in slices so a stop signal is honoured promptly.
        slept = 0.0
        while _running and slept < wait:
            time.sleep(min(1.0, wait - slept))
            slept += 1.0
    LOG.info("grant organ resting")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
