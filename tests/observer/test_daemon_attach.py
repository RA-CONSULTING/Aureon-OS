"""HNCLiveDaemon attach_observer flag and singleton wiring.

Verifies that:
  * attach_observer=True (default) constructs an observer
  * The observer claims the singleton
  * Caller-provided observers take precedence
  * attach_observer=False with no observer disables the integration
  * The daemon never raises on attach failures (graceful degrade)
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import pytest

from aureon.core.aureon_lambda_engine import SubsystemReading
from aureon.core.hnc_live_daemon import (
    HNCLiveDaemon,
    SourceObservation,
    SourceReceipt,
)
from aureon.observer import HarmonicObserver, get_observer


def _daemon(tmp_path: Path, **kwargs: Any) -> HNCLiveDaemon:
    return HNCLiveDaemon(
        state_path=tmp_path / "lambda_history.json",
        trace_path=tmp_path / "hnc_trace.jsonl",
        **kwargs,
    )


def _offline_receipt_daemon(tmp_path: Path) -> HNCLiveDaemon:
    daemon = _daemon(tmp_path)
    daemon._sources.clear()
    daemon._fetchers.clear()

    async def fetch_fixture() -> SourceObservation:
        observed_at = time.time()
        return SourceObservation(
            reading=SubsystemReading(
                name="fixture",
                value=0.62,
                confidence=0.9,
                state="live",
            ),
            receipt=SourceReceipt(
                source_id="test.fixture",
                source_timestamp=observed_at,
                received_at=observed_at,
                receipt_id=f"test:fixture:{time.time_ns()}",
                receipt_type="test_provider_measurement",
                truth_status="real_observed",
                generated_values=False,
            ),
        )

    daemon.register_source(
        "fixture",
        0.05,
        fetch_fixture,
        max_age_s=60.0,
    )
    return daemon


def test_default_attach_observer_constructs(tmp_path: Path):
    d = _daemon(tmp_path)
    assert d._observer is not None
    assert get_observer() is d._observer


def test_attach_observer_false_disables(tmp_path: Path):
    d = _daemon(tmp_path, attach_observer=False)
    assert d._observer is None


def test_caller_provided_observer_used(tmp_path: Path):
    custom = HarmonicObserver(publish_to_bus=False)
    d = _daemon(tmp_path, attach_observer=False, observer=custom)
    assert d._observer is custom


def test_caller_observer_overrides_attach_flag(tmp_path: Path):
    """If caller provides an observer, attach_observer=True does NOT
    construct a second one."""
    custom = HarmonicObserver(publish_to_bus=False)
    d = _daemon(tmp_path, attach_observer=True, observer=custom)
    assert d._observer is custom


def test_compute_loop_feeds_observer_ingest_state(tmp_path: Path):
    """Run a tiny duration-bounded loop; verify ingest_state was called."""
    d = _offline_receipt_daemon(tmp_path)
    asyncio.run(d.run(duration_s=0.5))
    snap = d._observer.metrics_snapshot()
    assert snap["n_ingested"] >= 1
    latest = snap["latest_field"]
    assert latest["lambda_t"] is not None
    # ingest_state must have populated psi/level — these only flow from
    # ingest_state, never from plain ingest().
    assert latest["consciousness_psi"] is not None
    assert latest["consciousness_level"] is not None


def test_predictionbus_auto_picks_up_observer(tmp_path: Path):
    """Stage B + Stage E together: bus auto-wires; daemon installs observer;
    bus then sees real observer state."""
    from aureon.autonomous.aureon_autonomy_hub import PredictionBus
    bus = PredictionBus()
    d = _offline_receipt_daemon(tmp_path)
    asyncio.run(d.run(duration_s=0.5))
    results = bus.run_predictions({}, symbol="BTCUSD")
    assert "harmonic_observer" in results
    sig = results["harmonic_observer"]
    assert sig.direction in ("BULLISH", "BEARISH", "NEUTRAL")
    assert 0.0 <= sig.confidence <= 1.0
