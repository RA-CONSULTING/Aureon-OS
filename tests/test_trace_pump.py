"""
TracePump — re-fires subscribe-based cross-process signals onto the local bus.

Offline + hermetic: an isolated AUREON_BUS_TRACE_DIR per test; the pump runs
against a fresh ThoughtBus so a "consumer process" subscriber receives events a
"producer process" only wrote to the trace file. No background thread is started
(tick() is driven directly) so the tests are deterministic.
"""

from __future__ import annotations

import time

import pytest

from aureon.core.aureon_thought_bus import ThoughtBus
from aureon.core.bus_trace import append_trace
from aureon.core.trace_pump import DEFAULT_ROUTES, PumpRoute, TracePump


@pytest.fixture(autouse=True)
def _tmp_trace_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_BUS_TRACE_DIR", str(tmp_path))
    return tmp_path


def _pump_and_sink(routes=DEFAULT_ROUTES):
    bus = ThoughtBus(persist_path=None)
    seen: list[tuple[str, dict]] = []
    for r in routes:
        bus.subscribe(r.topic, lambda t, _r=r: seen.append((_r.topic, dict(t.payload))))
    return TracePump(bus=bus, routes=routes, interval_s=0.5), seen


# ── prime: skip backlog, seed current state ──────────────────────────────────

def test_prime_skips_event_backlog_but_seeds_state():
    append_trace("auris_cosmic_state", {"cosmic_score": 0.4, "_ts": time.time()})
    append_trace("lighthouse_event", {"type": "PHASE_RESET", "_ts": time.time()})
    pump, seen = _pump_and_sink()
    pump.prime()
    topics = [t for t, _ in seen]
    assert "auris.throne.cosmic_state" in topics   # state topic: latest seeded
    assert "lighthouse.event" not in topics        # event topic: backlog NOT replayed


# ── tick: publish only rows newer than the high-water mark ────────────────────

def test_tick_publishes_new_rows_to_subscriber():
    append_trace("lighthouse_event", {"type": "OLD", "_ts": time.time()})
    pump, seen = _pump_and_sink()
    pump.prime()                                   # OLD is backlog → skipped
    append_trace("lighthouse_event", {"type": "COHERENCE_COLLAPSE", "_ts": time.time()})
    n = pump.tick()
    assert n == 1
    assert ("lighthouse.event", {"type": "COHERENCE_COLLAPSE"}) in seen  # _ts stripped


def test_tick_is_idempotent_no_double_fire():
    pump, seen = _pump_and_sink()
    pump.prime()
    append_trace("auris_cosmic_state", {"cosmic_score": 0.9, "_ts": time.time()})
    assert pump.tick() == 1
    assert pump.tick() == 0                         # dedup by _ts — no replay
    assert pump.tick() == 0
    scores = [p.get("cosmic_score") for t, p in seen if t == "auris.throne.cosmic_state"]
    assert scores.count(0.9) == 1


def test_tick_before_prime_primes_and_returns_zero():
    append_trace("lighthouse_event", {"type": "X", "_ts": time.time()})
    pump, seen = _pump_and_sink()
    assert pump.tick() == 0                          # first call primes, publishes nothing new
    assert not any(t == "lighthouse.event" for t, _ in seen)


# ── the _ts is stripped from the republished payload ──────────────────────────

def test_ts_is_stripped_from_published_payload():
    pump, seen = _pump_and_sink()
    pump.prime()
    append_trace("lighthouse_event", {"type": "REGIME_CHANGE", "severity": 0.7, "_ts": time.time()})
    pump.tick()
    _, payload = next(e for e in seen if e[0] == "lighthouse.event")
    assert "_ts" not in payload
    assert payload["type"] == "REGIME_CHANGE" and payload["severity"] == 0.7


# ── cross-process: producer writes trace, a DIFFERENT bus's subscriber fires ──

def test_signal_crosses_process_boundary():
    # 'producer process' only ever wrote to the trace file (never to bus B).
    append_trace("auris_cosmic_state", {"cosmic_score": 0.55, "gate_open": True, "_ts": time.time()})
    pump, seen = _pump_and_sink()
    pump.prime()  # seeds the latest state onto bus B
    assert any(t == "auris.throne.cosmic_state" and p.get("cosmic_score") == 0.55 for t, p in seen)


# ── guarded: missing trace / no rows is a quiet no-op ─────────────────────────

def test_missing_trace_is_quiet():
    pump, seen = _pump_and_sink()
    pump.prime()          # no trace files exist
    assert seen == []
    assert pump.tick() == 0


def test_stats_shape():
    pump, _ = _pump_and_sink()
    pump.prime()
    st = pump.stats()
    assert set(st) == {"running", "published", "routes", "high_water"}
    # every default route must be reported, in declaration order
    assert st["routes"] == [r.topic for r in DEFAULT_ROUTES]
    assert "auris.throne.cosmic_state" in st["routes"]
    assert "lighthouse.event" in st["routes"]


# ── the default routes cover the subscribe-based signals ──────────────────────

def test_default_routes_cover_auris_and_lighthouse():
    names = {r.trace_name for r in DEFAULT_ROUTES}
    # The original two cross-process signals, plus the bio immune layer that was
    # deliberately un-siloed onto the bus (integrity guard, swarm defense,
    # immune memory, immune regulation — b35/b38/b39).
    assert names == {
        "auris_cosmic_state",
        "lighthouse_event",
        "integrity_guard",
        "swarm_defense",
        "immune_memory",
        "immune_regulation",
    }
    auris = next(r for r in DEFAULT_ROUTES if r.trace_name == "auris_cosmic_state")
    lh = next(r for r in DEFAULT_ROUTES if r.trace_name == "lighthouse_event")
    assert auris.seed_latest is True and lh.seed_latest is False  # state vs event
    # bio immune runs are events, not state — never seeded from backlog
    for r in DEFAULT_ROUTES:
        if r.trace_name.startswith(("integrity", "swarm", "immune")):
            assert r.seed_latest is False
    assert isinstance(auris, PumpRoute)
