#!/usr/bin/env python3
"""
Full-pathway stress harness (Stage 6.4).

Boots the whole persona chain on a single in-memory ThoughtBus and
pushes synthetic ``persona.collapse`` events through it, measuring:

  count in / count out per stage  — no packets silently dropped
  harmonic_hash uniqueness        — no collisions across the vault
  bonding correctness             — same-semantic repeats collapse to
                                    one fingerprint (they should)
  per-stage p50 / p95 latency     — no unexpected regressions

Runs deterministically and finishes in a few seconds. Not a pytest —
standalone script. Exits non-zero on any invariant failure.

Dependencies: BusFlightCheck, VaultFeedAudit, HashResonanceIndex,
PersonaActuator, TemporalCausalityLaw, GoalDispatchBridge,
SymbolicLifeBridge — all the previous stages.
"""

from __future__ import annotations

import os
import random
import statistics
import sys
import time
import io
from typing import Any, Callable, Dict, List, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

if hasattr(sys.stdout, "buffer"):
    sys.stdout = sys.stdout if 'pytest' in sys.modules else io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from aureon.core.aureon_thought_bus import Thought, ThoughtBus  # noqa: E402
from aureon.vault.aureon_vault import AureonVault  # noqa: E402
from aureon.vault.voice.bus_flight_check import BusFlightCheck  # noqa: E402
from aureon.vault.voice.goal_dispatch_bridge import GoalDispatchBridge  # noqa: E402
from aureon.vault.voice.hash_resonance_index import HashResonanceIndex  # noqa: E402
from aureon.vault.voice.persona_action import PersonaActuator  # noqa: E402
from aureon.vault.voice.symbolic_life_bridge import SymbolicLifeBridge  # noqa: E402
from aureon.vault.voice.temporal_causality import (  # noqa: E402
    TemporalCausalityLaw, reset_temporal_causality_law,
)
from aureon.vault.voice.vault_feed_audit import VaultFeedAudit  # noqa: E402


STRESS_FULL_PATHWAY_RELEASE_HOLD = (
    "stress_full_pathway_hold:production_magic_star_release_unavailable"
)


# ─────────────────────────────────────────────────────────────────────────────
# Output
# ─────────────────────────────────────────────────────────────────────────────


GREEN = "\033[92m"; RED = "\033[91m"; CYAN = "\033[96m"; RESET = "\033[0m"


def ok(msg: str) -> None:
    print(f"  {GREEN}[PASS]{RESET} {msg}")


def fail(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {msg}")


def banner(title: str) -> None:
    bar = "━" * 76
    print(f"\n{CYAN}{bar}\n{title}\n{bar}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
# Stubs
# ─────────────────────────────────────────────────────────────────────────────


class _StubConscience:
    """Always-APPROVED conscience so the dispatch bridge reliably hands
    off to the stub engine."""

    class _V:
        name = "APPROVED"

    class _W:
        verdict = None
        message = "ok"
        why_it_matters = ""

    def __init__(self):
        self.W = _StubConscience._W
        self.W.verdict = _StubConscience._V

    def ask_why(self, action: str, context: Dict[str, Any] = None):
        return self.W


class _StubGoalEngine:
    """Records every submitted goal and publishes `goal.completed` so
    the TemporalCausalityLaw closes the causal line."""

    def __init__(self, bus: ThoughtBus):
        self.bus = bus
        self.submissions: List[str] = []

    def submit_goal(self, text: str):
        self.submissions.append(text)
        # Close the line immediately — full-chain liveness check
        self.bus.publish(Thought(
            source="stub_engine",
            topic="goal.completed",
            payload={"text": text, "result_summary": "stub completed"},
        ))
        return {"goal_id": f"E-{len(self.submissions)}", "text": text}


# ─────────────────────────────────────────────────────────────────────────────
# Stage counter
# ─────────────────────────────────────────────────────────────────────────────


class _StageCounter:
    """Subscribes to each pipeline stage's topic and records counts +
    per-event latencies (from trace-start marker in payload)."""

    def __init__(self, bus: ThoughtBus, topics: List[str]):
        self.counts: Dict[str, int] = {t: 0 for t in topics}
        self.latencies: Dict[str, List[float]] = {t: [] for t in topics}
        for topic in topics:
            bus.subscribe(topic, self._on(topic))

    def _on(self, topic: str) -> Callable[[Any], None]:
        def _handler(thought: Any) -> None:
            self.counts[topic] = self.counts.get(topic, 0) + 1
            # Trace markers live in Thought.meta so they don't pollute the
            # payload bonding fingerprint.
            meta = getattr(thought, "meta", {}) or {}
            if isinstance(meta, dict) and "_stress_t0" in meta:
                dt = time.time() - float(meta["_stress_t0"])
                self.latencies.setdefault(topic, []).append(dt)
        return _handler


# ─────────────────────────────────────────────────────────────────────────────
# Harness
# ─────────────────────────────────────────────────────────────────────────────


def run(n_events: int = 1000) -> int:
    raise RuntimeError(STRESS_FULL_PATHWAY_RELEASE_HOLD)
    banner(f"Stage 6.4 — full-pathway stress ({n_events} events)")

    bus = ThoughtBus()
    vault = AureonVault()
    vault._thought_bus = bus

    # BusFlightCheck first so it sees everything.
    fc = BusFlightCheck(bus, recent_horizon_s=120.0)
    fc.start()

    # HashResonanceIndex — subscribes to vault.card.added.
    idx = HashResonanceIndex(vault=vault, thought_bus=bus, thresholds=[3, 8, 21])
    idx.start()

    # Actuator — personas' actions flow through here.
    actuator = PersonaActuator(vault=vault, thought_bus=bus)

    # TemporalCausalityLaw — goals' β Λ(t-τ) lighthouse.
    reset_temporal_causality_law()
    law = TemporalCausalityLaw(thought_bus=bus, vault=vault,
                               ack_budget_tau=1000, complete_budget_tau=10000)
    law.start()

    # Stub engine + conscience → GoalDispatchBridge.
    engine = _StubGoalEngine(bus)
    conscience = _StubConscience()
    dispatcher = GoalDispatchBridge(
        thought_bus=bus, conscience=conscience,
        goal_engine=engine, vault=vault,
    )
    dispatcher._run_in_thread = False       # deterministic in-thread execution
    dispatcher.start()

    # SymbolicLifeBridge — the five Auris Conjecture pillars.
    slb = SymbolicLifeBridge(thought_bus=bus, vault=vault, horizon=128)
    slb.start()

    # Wire vault ingestion for everything it now subscribes to.
    for topic in vault.DEFAULT_SUBSCRIPTIONS:
        bus.subscribe(topic, vault._on_thought)

    # Stage counter — the topics we're measuring end-to-end.
    stage_topics = [
        "persona.collapse",
        "persona.action",          # not published — we use it as a marker
        "goal.submit.request",
        "goal.submitted",
        "goal.completed",
        "goal.abandoned",
        "goal.echo",
        "goal.echo.summary",
        "symbolic.life.pulse",
        "vault.card.added",
        "standing.wave.bond",
    ]
    counter = _StageCounter(bus, stage_topics)

    vault_audit = VaultFeedAudit(vault=vault, flight_check=fc)

    # ─── Drive synthetic collapses ──────────────────────────────────────
    # Each collapse fires a persona.collapse AND an actuator goal.submit
    # so we exercise the full chain. We deliberately include BOTH
    # unique (varied) events and repeat-semantic events (same phrase
    # across many collapses) so the bonding index has a chance to form
    # a standing wave.

    rng = random.Random(42)
    start = time.time()
    repeat_phrase = "author a coherence-audit skill"
    for i in range(n_events):
        t0 = time.time()
        # Persona-collapse event (trace marker in META, not payload, so
        # it doesn't pollute bonding fingerprints).
        bus.publish(Thought(
            source="stress", topic="persona.collapse",
            payload={
                "winner": "engineer",
                "probabilities": {"engineer": 0.95},
            },
            meta={"_stress_t0": t0},
        ))
        # Goal proposal — alternate between repeat semantic + unique
        use_repeat = (i % 3 == 0)
        goal_text = repeat_phrase if use_repeat else f"unique goal {i}"
        actuator.dispatch(
            "engineer",
            action=_build_goal_action(goal_text, urgency=0.9),
            state={"persona": "engineer"},
        )
        # Every 32nd event, also pulse the law to drive goal.echo.summary
        if i % 32 == 0:
            law.pulse()
            slb.pulse()

    # Close out with a few final pulses so all summaries flush
    for _ in range(4):
        law.pulse()
        slb.pulse()

    elapsed = time.time() - start

    # ─── Invariant checks ──────────────────────────────────────────────
    all_good = True

    # 1. No drops: persona.collapse count == n_events
    if counter.counts["persona.collapse"] != n_events:
        fail(f"persona.collapse drops: got {counter.counts['persona.collapse']} / {n_events}")
        all_good = False
    else:
        ok(f"persona.collapse delivered: {counter.counts['persona.collapse']} / {n_events}")

    # 2. goal.submit.request count should match — actuator dispatches 1 per event
    if counter.counts["goal.submit.request"] != n_events:
        fail(f"goal.submit.request drops: got {counter.counts['goal.submit.request']} / {n_events}")
        all_good = False
    else:
        ok(f"goal.submit.request delivered: {counter.counts['goal.submit.request']} / {n_events}")

    # 3. Every goal reached the engine (conscience = APPROVED)
    if len(engine.submissions) != n_events:
        fail(f"engine submissions: got {len(engine.submissions)} / {n_events}")
        all_good = False
    else:
        ok(f"engine.submit_goal called: {len(engine.submissions)} / {n_events}")

    # 4. Every goal closed (goal.completed)
    if counter.counts["goal.completed"] != n_events:
        fail(f"goal.completed drops: got {counter.counts['goal.completed']} / {n_events}")
        all_good = False
    else:
        ok(f"goal.completed delivered: {counter.counts['goal.completed']} / {n_events}")

    # 5. Hash distinctness is semantic, not per-card — repeat events
    #    SHOULD collide (that's what stage 6.3 bonding is about). We
    #    instead assert: different-semantic cards produce different
    #    hashes. Sample n unique-goal-text cards and confirm their
    #    harmonic_hashes are all distinct.
    unique_goal_cards = [
        c for c in vault._contents.values()
        if c.source_topic == "goal.submit.request"
        and c.payload.get("text", "").startswith("unique goal ")
    ]
    distinct_unique_hashes = {c.harmonic_hash for c in unique_goal_cards}
    if len(distinct_unique_hashes) == len(unique_goal_cards):
        ok(f"hash distinctness on unique goals: {len(unique_goal_cards)} "
           f"cards, {len(distinct_unique_hashes)} unique hashes")
    else:
        fail(f"hash collisions on different-semantic goals: "
             f"{len(unique_goal_cards) - len(distinct_unique_hashes)} collisions")
        all_good = False

    # 6. Bonding: repeat_phrase goals must all bond to one fingerprint
    repeats = [c for c in vault._contents.values()
               if c.source_topic == "goal.submit.request"
               and c.payload.get("text") == repeat_phrase]
    if repeats:
        # They should all map to the same bonding fingerprint.
        fp_set = {idx.fingerprint_for_content(c.content_id) for c in repeats}
        fp_set.discard(None)
        if len(fp_set) == 1:
            bond = next(iter(fp_set))
            count = idx.bond_count(bond)
            ok(f"repeat-goal bonding: {len(repeats)} events → 1 fingerprint "
               f"(bond count {count}, strength {idx.bond_strength(bond):.3f})")
        else:
            fail(f"repeat-goal bonding broken: {len(repeats)} events → "
                 f"{len(fp_set)} fingerprints (should be 1)")
            all_good = False

    # 7. Standing-wave bond events published
    if counter.counts["standing.wave.bond"] >= 3:
        ok(f"standing.wave.bond events published: {counter.counts['standing.wave.bond']}")
    else:
        fail(f"standing.wave.bond: got {counter.counts['standing.wave.bond']}, "
             f"expected ≥3 (Fibonacci threshold crossings)")
        all_good = False

    # 8. Latency profile (only measure where we captured _stress_t0)
    lat = counter.latencies.get("goal.submit.request", [])
    if lat:
        p50 = statistics.median(lat) * 1000
        p95 = _percentile(lat, 0.95) * 1000
        print(f"  {CYAN}[INFO]{RESET} goal.submit.request latency p50={p50:.2f}ms p95={p95:.2f}ms")
        if p95 > 50.0:
            fail(f"goal.submit.request p95 latency {p95:.2f}ms > 50ms budget")
            all_good = False
        else:
            ok(f"latency budget met (p95 {p95:.2f}ms ≤ 50ms)")

    # 9. SLS bridge actually produced a pulse
    if counter.counts["symbolic.life.pulse"] >= 1:
        ok(f"symbolic.life.pulse pulses: {counter.counts['symbolic.life.pulse']}")
    else:
        fail("symbolic.life.pulse never fired")
        all_good = False

    # 10. Vault growth
    card_count = len(vault)
    if card_count < n_events:
        fail(f"vault card count {card_count} < expected minimum {n_events}")
        all_good = False
    else:
        ok(f"vault cards: {card_count}")

    # 11. Vault-feed audit — no high-severity dead branches on our topics.
    # `vault.card.added` is by-design NOT ingested (infinite-recursion
    # prevention), so exclude it. Same for `persona.action` which is a
    # synthetic marker in this harness.
    audit = vault_audit.coverage_report()
    bus_internal = {"vault.card.added", "persona.action"}
    high = [t for t in audit["high_severity_dead_branches"]
            if not t.startswith("fc_test.") and t not in bus_internal]
    our_topics = set(stage_topics) - bus_internal
    dead_ours = [t for t in high if t in our_topics]
    if dead_ours:
        fail(f"our own topics are dead branches: {dead_ours}")
        all_good = False
    else:
        ok("no high-severity dead branches among our pathway topics")

    banner(f"SUMMARY — {elapsed:.2f}s wall time, "
           f"{len(vault)} vault cards, "
           f"{idx.summary()['unique_fingerprints']} unique fingerprints")
    if all_good:
        print(f"  {GREEN}ALL INVARIANTS HELD{RESET}")
        return 0
    print(f"  {RED}INVARIANTS VIOLATED — see above{RESET}")
    return 1


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(len(s) - 1, int(pct * len(s)))
    return s[idx]


def _build_goal_action(text: str, *, urgency: float):
    """Build a PersonaAction of kind goal.submit. Import lazily so the
    stress script stays small. No trace markers in payload — they'd
    break bonding."""
    from aureon.vault.voice.persona_action import PersonaAction
    return PersonaAction(
        kind="goal.submit",
        topic=text,
        payload={},
        reason="stress-test goal",
        urgency=urgency,
    )


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--events", type=int, default=1000)
    args = ap.parse_args()
    raise SystemExit(run(n_events=args.events))
