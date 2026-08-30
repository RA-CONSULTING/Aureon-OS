"""P1 repairs: the phase-transition detector's consumers actually work.

Three defects lived here since the detector shipped, all silent:

1. ``_publish_transition`` built ``Thought(data=…, confidence=…)`` — kwargs the
   dataclass does not have — so ``phase.transition.detected`` had never once
   been emitted (the TypeError died in a bare except).
2. The SignalGate called ``update()/get_state()/get_curvature()``, none of which
   exist on the detector, so the PHASE_CRITICAL and high-curvature blocks had
   never once fired (every call raised and was logged at debug as "allowing
   trade").
3. The kraken scorer read ``phase_state``/``transition_score`` keys that
   ``get_status()`` does not return (state pinned at UNKNOWN forever) and
   compared the enter/exit navigation signal to a buy/sell side (never equal).

These tests drive the REAL detector — no stub detector objects — using the same
synthetic-crash shape as the detector's own __main__ validation.
"""

import math
import random
from pathlib import Path

import pytest

from aureon.core.aureon_operational_core import SignalGate
from aureon.intelligence.aureon_phase_transition_detector import (
    PhaseTransitionDetector,
)


@pytest.fixture(autouse=True)
def _isolate_phase_receipts(tmp_path, monkeypatch):
    """Keep transition thoughts and observer audits out of operational journals."""
    from aureon.core import aureon_thought_bus as thought_bus_module
    from aureon.observer import production_mode

    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path / "bus-traces"))
    monkeypatch.delenv("AUREON_REDIS_URL", raising=False)
    bus = thought_bus_module.ThoughtBus(persist_path=str(tmp_path / "phase-thoughts.jsonl"))
    monkeypatch.setattr(thought_bus_module, "_thought_bus_instance", bus)
    monkeypatch.setattr(
        production_mode,
        "AUDIT_LOG_PATH",
        Path(tmp_path / "observer_audit.jsonl"),
    )


def _feed_stable_then_crash(sink, n_stable: int = 200, n_crash: int = 60, seed: int = 7):
    """Generate a stable random-walk then a crash, feeding ``sink(price, i)``.

    Mirrors the detector's own test scenario: low-vol drift, then an abrupt
    high-volatility collapse — the regime change the detector exists to catch.
    """
    rng = random.Random(seed)
    price = 100.0
    i = 0
    for _ in range(n_stable):
        price *= 1.0 + rng.gauss(0.0, 0.001)
        sink(price, i)
        i += 1
    for _ in range(n_crash):
        price *= 1.0 + rng.gauss(-0.02, 0.015)
        sink(price, i)
        i += 1
    return i


def test_publish_transition_emits_real_thought():
    """The bus actually receives phase.transition.detected after the kwargs fix.

    State transitions fire inside predict(), so the drive loop calls it each
    step the way every real consumer does. A process-local subscriber (not
    recall) proves THIS process emitted the event — recall can be satisfied by
    stale cross-process trace rows.
    """
    from aureon.core.aureon_thought_bus import get_thought_bus

    received = []
    bus = get_thought_bus()
    bus.subscribe("phase.transition.detected", lambda t: received.append(t))

    det = PhaseTransitionDetector()

    def sink(price, i):
        det.ingest(price, float(i))
        det.predict()

    _feed_stable_then_crash(sink)

    assert received, (
        "no phase.transition.detected reached the bus — either the synthetic "
        "data no longer triggers a transition or the Thought kwargs regressed"
    )
    thought = received[-1]
    payload = thought.payload if hasattr(thought, "payload") else thought.get("payload")
    assert "from_state" in payload and "to_state" in payload
    assert "curvature" in payload and "coherence" in payload


def test_signal_gate_blocks_in_crash_window_when_armed(monkeypatch):
    """With the veto armed, the repaired SignalGate blocks during the crash."""
    monkeypatch.setattr("aureon.observer.production_mode.phase_veto_active", lambda: True)

    det = PhaseTransitionDetector()
    gate = SignalGate(phase_detector=det)
    gate._cache_ttl = 0.0  # ingest every call — the test drives time itself

    outcomes = []

    def sink(price, i):
        # Windows can return the same time.time() value across many rapid calls.
        # Reset only the test cache marker so every synthetic observation reaches
        # the real detector; production's five-second cache remains unchanged.
        gate._last_check_time = 0.0
        allowed, reason = gate.check_entry_allowed("BTC/USD", price)
        outcomes.append((i, allowed, reason))

    _feed_stable_then_crash(sink)

    blocked = [(i, r) for i, ok, r in outcomes if not ok]
    assert blocked, "gate never blocked across a synthetic crash — repair regressed"
    assert any(r.startswith("PHASE_CRITICAL") or r.startswith("HIGH_CURVATURE") for _, r in blocked)
    # Warm-up honored: no block is possible before the Takens memory fills
    # (memory_length=144), so the first 100 entries must all have been allowed.
    # (The detector saturates CRITICAL from its first prediction on realistic
    # volatility — a calibration question tracked separately, not this repair.)
    assert all(ok for _, ok, _ in [o for o in outcomes if o[0] < 100])


def test_signal_gate_audits_but_allows_when_not_armed(monkeypatch):
    """DRY_RUN semantics: same detector state, would_have_blocked recorded, trade allowed."""
    monkeypatch.setattr("aureon.observer.production_mode.phase_veto_active", lambda: False)
    audits = []
    monkeypatch.setattr(
        "aureon.observer.production_mode.audit",
        lambda event, payload, **kw: audits.append((event, payload, kw)),
    )

    det = PhaseTransitionDetector()
    gate = SignalGate(phase_detector=det)
    gate._cache_ttl = 0.0

    outcomes = []

    def sink(price, _i):
        gate._last_check_time = 0.0
        outcomes.append(gate.check_entry_allowed("BTC/USD", price))

    _feed_stable_then_crash(sink)

    assert all(ok for ok, _ in outcomes), "unarmed gate must allow every entry"
    phase_audits = [a for a in audits if a[0] == "signal_gate_phase_check"]
    assert phase_audits, "crash produced no would_have_blocked audit rows"
    assert all(a[2].get("would_have_blocked") is True for a in phase_audits)
    assert all(a[2].get("actually_blocked") is False for a in phase_audits)


def test_signal_gate_without_detector_is_clear():
    gate = SignalGate(phase_detector=None)
    assert gate.check_entry_allowed("BTC/USD", 100.0) == (True, "CLEAR")


class _KrakenScorerHost:
    """Minimal host exposing exactly what _score_phase_transition touches."""

    def __init__(self, detector):
        self.phase_transition_detector = detector
        self._phase_transition_snapshot = None

    from aureon.exchanges.kraken_margin_penny_trader import (  # type: ignore
        KrakenMarginArmyTrader as _K,
    )

    _score_phase_transition = _K._score_phase_transition


@pytest.fixture()
def warmed_detector():
    det = PhaseTransitionDetector()
    _feed_stable_then_crash(lambda p, i: det.ingest(p, float(i)))
    return det


def test_kraken_scorer_reads_real_state(warmed_detector):
    host = _KrakenScorerHost(warmed_detector)
    result = host._score_phase_transition("BTC/USD", "buy", 100.0)
    assert result["state"] != "UNKNOWN", "state pinned at UNKNOWN — the get_status() key repair regressed"
    assert result["state"] in {"STABLE", "ELEVATED", "CRITICAL", "RECOVERY"}
    assert not math.isnan(result["score"])
    snap = host._phase_transition_snapshot
    assert snap is not None and "error" not in snap


def test_kraken_scorer_nav_mapping_can_match_side(warmed_detector):
    """enter/exit maps onto buy/sell so the ±0.5 nav bonus is reachable again."""
    host = _KrakenScorerHost(warmed_detector)
    nav = str(warmed_detector.get_status().get("navigation_signal", "HOLD")).lower()
    nav_side = {"enter": "buy", "exit": "sell"}.get(nav, nav)
    if nav_side in {"buy", "sell"}:
        with_match = host._score_phase_transition("BTC/USD", nav_side, 100.0)
        other = "sell" if nav_side == "buy" else "buy"
        against = host._score_phase_transition("BTC/USD", other, 100.0)
        assert with_match["bonus"] > against["bonus"]
    else:
        # HOLD is a legitimate signal: the mapping must simply not crash and
        # must not hand out the directional bonus.
        result = host._score_phase_transition("BTC/USD", "buy", 100.0)
        assert result["state"] != "UNKNOWN"
