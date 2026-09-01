#!/usr/bin/env python3
"""
run_aureon_live.py — watch the personas act on themselves in real time.

This is NOT a test. It boots the real pieces we've built:

    ThoughtBus  ←→  AureonVault  ←→  PersonaVacuum  →  PersonaActuator
                            ↑                             │
                            └────────── feedback ─────────┘

and lets the system drive itself at the φ² heartbeat. An ambient thread
emits realistic DJ drops and initial cognition snapshots; a feedback
reactor listens for the topics personas publish (queen.request_cognition,
auris.throne.alert, love.stream.528hz, persona.intent.*) and produces a
*new* cognition snapshot in response — so each persona's action really
does cause the next observation.

Everything prints to stdout as it happens. Run for DURATION seconds
(default 25), Ctrl-C to stop early. At the end we dump:
  - winner histogram
  - actuator history (kind / topic counts)
  - final vault card breakdown by category

Usage:
    python scripts/run_aureon_live.py                 # default 25 s
    python scripts/run_aureon_live.py --seconds 60
    python scripts/run_aureon_live.py --quiet         # summary only
"""

from __future__ import annotations

raise RuntimeError(
    "run_aureon_live_unreleased_import_hold:production_magic_star_release_unavailable"
)

import argparse
import logging
import math
import os
import random
import signal
import sys
import threading
import time
from collections import Counter
from typing import Any, Dict, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from aureon.core.aureon_thought_bus import Thought, ThoughtBus
from aureon.vault.aureon_vault import AureonVault
from aureon.vault.voice.aureon_personas import build_aureon_personas
from aureon.vault.voice.persona_action import PersonaActuator
from aureon.vault.voice.persona_vacuum import PersonaVacuum

PHI = (1 + math.sqrt(5)) / 2
PHI_SQUARED = PHI * PHI

# ─────────────────────────────────────────────────────────────────────────────
# Stub adapter — we care about memory behaviour, not LLM output
# ─────────────────────────────────────────────────────────────────────────────


class _QuietAdapter:
    def prompt(self, messages, system, max_tokens):
        class _R:
            text = "."  # silent utterance
            model = "live"
            usage = {"total_tokens": 1}

        return _R()


# ─────────────────────────────────────────────────────────────────────────────
# Console printer
# ─────────────────────────────────────────────────────────────────────────────


GREY = "\033[90m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
BLUE = "\033[94m"
RESET = "\033[0m"


class ConsolePrinter:
    def __init__(self, start_ts: float, quiet: bool = False):
        self.start_ts = start_ts
        self.quiet = quiet
        self._lock = threading.Lock()

    def _stamp(self) -> str:
        return f"[{time.time() - self.start_ts:6.2f}]"

    def emit(self, color: str, glyph: str, msg: str) -> None:
        if self.quiet:
            return
        with self._lock:
            print(f"{GREY}{self._stamp()}{RESET} {color}{glyph}{RESET} {msg}", flush=True)

    def cognition(self, payload: Dict[str, Any]) -> None:
        gamma = float(payload.get("coherence_gamma", 0.0) or 0.0)
        psi = float(payload.get("consciousness_psi", 0.0) or 0.0)
        lvl = payload.get("consciousness_level", "")
        self.emit(CYAN, "←cognition ",
                  f"Γ={gamma:.3f}  ψ={psi:.3f}  lvl={lvl}")

    def drop(self, payload: Dict[str, Any]) -> None:
        self.emit(BLUE, "←drop      ",
                  f"energy={float(payload.get('energy',0)):.2f}  bpm={float(payload.get('bpm',0)):.1f}")

    def collapse(self, winner: str, probs: Dict[str, float]) -> None:
        p = probs.get(winner, 0.0)
        self.emit(MAGENTA, "⎈collapse  ", f"{winner:<20s} p={p:.3f}")

    def action(self, persona: str, kind: str, topic: str, reason: str) -> None:
        self.emit(GREEN, "⊙action    ",
                  f"{persona:<20s} {kind:<14s} → {topic}   ({reason})")

    def absorbed(self, topic: str, category: str, card_count: int) -> None:
        self.emit(YELLOW, "⊕vault     ",
                  f"card[{category}] from {topic}  (vault size={card_count})")

    def react(self, topic: str) -> None:
        self.emit(GREY, "↺react     ", f"feedback from {topic}")


# ─────────────────────────────────────────────────────────────────────────────
# Feedback reactor — closes the loop
# ─────────────────────────────────────────────────────────────────────────────


class FeedbackReactor:
    """Subscribes to the topics personas publish. When any of them arrives,
    synthesises a new 'queen.source_law.cognition' so the next persona
    observation sees an updated state.  The resulting new cognition
    propagates back into the PersonaVacuum via its own subscription.
    """

    REACT_TOPICS = (
        "queen.request_cognition",
        "auris.throne.alert",
        "persona.intent.rally",
        "persona.intent.velocity_alert",
        "love.stream.528hz",
    )

    def __init__(self, bus: ThoughtBus, vault: AureonVault, printer: ConsolePrinter):
        self.bus = bus
        self.vault = vault
        self.printer = printer
        self._rng = random.Random()

    def wire(self) -> None:
        for t in self.REACT_TOPICS:
            self.bus.subscribe(t, self._on_topic)

    def _on_topic(self, thought: Thought) -> None:
        self.printer.react(thought.topic)
        # Nudge the vault's synthesised state based on which topic fired.
        love_bump = 0.0
        gamma_mod = 0.0
        psi_mod = 0.0
        if thought.topic == "love.stream.528hz":
            love_bump = 0.03
        elif thought.topic == "auris.throne.alert":
            psi_mod = -0.08   # drift alert cools ψ slightly
            gamma_mod = -0.05
        elif thought.topic == "queen.request_cognition":
            gamma_mod = 0.02  # cognition request tightens coherence
        elif thought.topic == "persona.intent.rally":
            gamma_mod = 0.04
            psi_mod = 0.04
        elif thought.topic == "persona.intent.velocity_alert":
            gamma_mod = 0.03

        new_love = max(0.0, min(1.0, getattr(self.vault, "love_amplitude", 0.5) + love_bump))
        self.vault.love_amplitude = new_love

        # Synthesise a fresh cognition with small jitter around the last one.
        last_gamma = getattr(self.vault, "_live_last_gamma", 0.6)
        last_psi = getattr(self.vault, "_live_last_psi", 0.6)
        gamma = max(0.0, min(1.0, last_gamma + gamma_mod + (self._rng.random() - 0.5) * 0.05))
        psi = max(0.0, min(1.0, last_psi + psi_mod + (self._rng.random() - 0.5) * 0.06))
        self.vault._live_last_gamma = gamma
        self.vault._live_last_psi = psi

        level = "DORMANT"
        if psi > 0.85:
            level = "UNIFIED"
        elif psi > 0.7:
            level = "DAWNING"
        elif psi > 0.5:
            level = "AWARE"

        # Node readings jitter
        nodes = {
            "tiger": self._rng.uniform(0.3, 0.95),
            "falcon": self._rng.uniform(0.2, 0.95),
            "dolphin": self._rng.uniform(0.3, 0.9),
            "panda": self._rng.uniform(0.3, 0.9),
            "clownfish": self._rng.uniform(0.3, 0.9),
        }
        payload = {
            "coherence_gamma": gamma,
            "consciousness_psi": psi,
            "consciousness_level": level,
            "confidence": self._rng.uniform(0.4, 0.9),
            "node_readings": nodes,
        }
        self.bus.publish(Thought(
            source="feedback_reactor",
            topic="queen.source_law.cognition",
            payload=payload,
        ))


# ─────────────────────────────────────────────────────────────────────────────
# Ambient signal generator
# ─────────────────────────────────────────────────────────────────────────────


class AmbientSignals:
    """Cycles the system through distinct harmonic 'moods' so every persona's
    trigger region gets visited during a short session. Each mood runs for
    a few seconds, emits matching cognition + vault state, and then we move
    on to the next mood.
    """

    MOODS = (
        ("gate_clean",   "Γ high, Tiger clear — Engineer's gate"),
        ("lambda_drift", "|Λ| spikes — Quantum Physicist alert"),
        ("dawning",      "consciousness DAWNING — Philosopher"),
        ("rally_drop",   "big DJ drop + rally — Artist"),
        ("mystic_love",  "love > 0.9 at 528 Hz — Mystic"),
        ("heart_paint",  "heart chakra + gamma — Painter"),
        ("velocity",     "falcon surging — Left"),
        ("heart_field",  "dolphin + panda high — Right"),
        ("curiosity",    "small vault + delta — Child"),
        ("recurrence",   "theta + high ψ — Elder"),
    )

    def __init__(self, bus: ThoughtBus, vault: AureonVault,
                 printer: ConsolePrinter, mood_interval_s: float = PHI_SQUARED * 2):
        self.bus = bus
        self.vault = vault
        self.printer = printer
        self.mood_interval_s = float(mood_interval_s)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._rng = random.Random()

    def start(self) -> None:
        self._running = True
        self._apply("gate_clean")  # ensure the first collapse has data
        self._thread = threading.Thread(target=self._loop, daemon=True, name="AmbientSignals")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _loop(self) -> None:
        while self._running:
            mood, _ = self._rng.choice(self.MOODS)
            self._apply(mood)
            time.sleep(self.mood_interval_s)

    def _apply(self, mood: str) -> None:
        rng = self._rng
        # Describe the switch so the trace is readable.
        desc = dict(self.MOODS).get(mood, "?")
        self.printer.emit(GREY, "~mood      ", f"{mood:<14s} — {desc}")

        vault = self.vault
        # Default neutral anchors; per-mood overrides follow.
        cortex = {"delta": rng.uniform(0.1, 0.3), "theta": rng.uniform(0.1, 0.3),
                  "alpha": rng.uniform(0.1, 0.3), "beta": rng.uniform(0.1, 0.3),
                  "gamma": rng.uniform(0.1, 0.3)}
        gamma_coh = rng.uniform(0.4, 0.75)
        psi = rng.uniform(0.3, 0.7)
        lvl = "AWARE"
        nodes = {"tiger": 0.4, "falcon": 0.4, "dolphin": 0.4, "panda": 0.4, "clownfish": 0.4}
        chakra = vault.dominant_chakra
        freq = 432.0
        love = getattr(vault, "love_amplitude", 0.5)
        rally = False
        drop_energy = 0.0

        if mood == "gate_clean":
            gamma_coh = rng.uniform(0.94, 0.99)
            nodes["tiger"] = rng.uniform(0.8, 0.98)
            cortex["beta"] = 0.6
        elif mood == "lambda_drift":
            vault.last_lambda_t = rng.choice([-1, 1]) * rng.uniform(1.2, 2.2)
            psi = rng.uniform(0.88, 0.97)
            lvl = "UNIFIED"
        elif mood == "dawning":
            psi = rng.uniform(0.72, 0.85)
            lvl = "DAWNING"
            cortex["theta"] = rng.uniform(0.6, 0.9)
        elif mood == "rally_drop":
            rally = True
            drop_energy = rng.uniform(0.8, 1.0)
            cortex["beta"] = rng.uniform(0.6, 0.9)
        elif mood == "mystic_love":
            love = rng.uniform(0.9, 0.98)
            freq = 528.0
            chakra = "heart"
        elif mood == "heart_paint":
            love = rng.uniform(0.75, 0.92)
            chakra = rng.choice(["heart", "third_eye", "crown"])
            cortex["gamma"] = rng.uniform(0.7, 0.95)
        elif mood == "velocity":
            nodes["falcon"] = rng.uniform(0.85, 0.98)
            cortex["beta"] = rng.uniform(0.6, 0.9)
            confidence = rng.uniform(0.75, 0.95)
        elif mood == "heart_field":
            nodes["dolphin"] = rng.uniform(0.85, 0.95)
            nodes["panda"] = rng.uniform(0.85, 0.95)
            love = max(love, rng.uniform(0.65, 0.85))
        elif mood == "curiosity":
            cortex["delta"] = rng.uniform(0.8, 0.95)
            # Vault is already small if we're early, so this naturally lights Child.
        elif mood == "recurrence":
            psi = rng.uniform(0.85, 0.95)
            cortex["theta"] = rng.uniform(0.6, 0.9)

        # Update vault attribute state
        vault.dominant_chakra = chakra
        vault.dominant_frequency_hz = freq
        vault.love_amplitude = float(love)
        vault.rally_active = rally
        vault.cortex_snapshot = cortex

        # Publish cognition so the PersonaVacuum's build_state picks it up.
        self.bus.publish(Thought(
            source="ambient",
            topic="queen.source_law.cognition",
            payload={
                "coherence_gamma": gamma_coh,
                "consciousness_psi": psi,
                "consciousness_level": lvl,
                "confidence": rng.uniform(0.5, 0.9) if mood != "velocity" else rng.uniform(0.75, 0.95),
                "node_readings": nodes,
            },
        ))
        if drop_energy > 0.0:
            self.bus.publish(Thought(
                source="ambient",
                topic="dj.track.drop",
                payload={"energy": drop_energy, "bpm": rng.uniform(124, 138)},
            ))


# ─────────────────────────────────────────────────────────────────────────────
# Heartbeat — triggers persona.observe at φ² cadence
# ─────────────────────────────────────────────────────────────────────────────


class Heartbeat:
    def __init__(self, bus: ThoughtBus, interval_s: float = PHI_SQUARED):
        self.bus = bus
        self.interval_s = float(interval_s)
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="Heartbeat")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _loop(self) -> None:
        while self._running:
            self.bus.publish(Thought(
                source="heartbeat",
                topic="persona.observe",
                payload={},
            ))
            time.sleep(self.interval_s)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description="Live Aureon persona loop.")
    ap.add_argument("--seconds", type=float, default=25.0, help="run duration")
    ap.add_argument("--quiet", action="store_true", help="suppress event trace")
    ap.add_argument("--heartbeat", type=float, default=PHI_SQUARED,
                    help=f"heartbeat interval (default {PHI_SQUARED:.3f}s = φ²)")
    args = ap.parse_args()

    # Silence library logging so the event stream is readable.
    logging.basicConfig(level=logging.WARNING, format="%(name)s: %(message)s")

    start = time.time()
    printer = ConsolePrinter(start_ts=start, quiet=args.quiet)

    bus = ThoughtBus(max_memory=5000)
    vault = AureonVault()
    vault.love_amplitude = 0.5
    vault.gratitude_score = 0.6
    vault.dominant_chakra = "heart"
    vault.dominant_frequency_hz = 528.0
    vault.cortex_snapshot = {"delta": 0.2, "theta": 0.2, "alpha": 0.2, "beta": 0.2, "gamma": 0.2}

    # Vault ingests cognition + love + persona stuff straight off the bus.
    for topic in (
        "queen.source_law.cognition",
        "love.stream.528hz",
        "aureon.master.directive",
        "persona.thought",
        "persona.painter.composition",
        "persona.child.curiosity",
        "persona.elder.recurrence",
        "persona.right.field",
    ):
        def _make_ingest(_t):
            def _h(thought: Thought) -> None:
                vault.ingest(topic=thought.topic, payload=dict(thought.payload))
                try:
                    category = vault._contents[next(reversed(vault._contents))].category
                except StopIteration:
                    category = "?"
                printer.absorbed(thought.topic, category, len(vault))
            return _h

        bus.subscribe(topic, _make_ingest(topic))

    # Actuator — the thing that makes personas *act*.
    actuator = PersonaActuator(vault=vault, thought_bus=bus, dry_run=False, history_size=2000)

    # Persona vacuum, wired to the real bus.
    personas = build_aureon_personas(adapter=_QuietAdapter())
    vacuum = PersonaVacuum(
        personas=personas,
        thought_bus=bus,
        vault=vault,
        actuator=actuator,
        rng=random.Random(),
    )
    vacuum.start()

    # Print every collapse + every action.
    def on_collapse(thought: Thought) -> None:
        p = thought.payload
        printer.collapse(p.get("winner", "?"), p.get("probabilities", {}))

    def on_thought(thought: Thought) -> None:
        # Nothing to print here — the vacuum-sourced persona.thought is
        # already captured by the 'persona.thought' vault subscriber above.
        pass

    bus.subscribe("persona.collapse", on_collapse)
    bus.subscribe("persona.thought", on_thought)

    # After each collapse, print the actuator's outcome if one fired.
    last_count = {"n": 0}

    def actuator_tail(thought: Thought) -> None:
        hist = actuator.history(n=5)
        if len(hist) <= last_count["n"]:
            return
        for rec in hist[last_count["n"] - len(hist):]:
            printer.action(
                rec["persona"],
                rec["action"]["kind"],
                rec["action"]["topic"],
                rec["action"]["reason"] or "—",
            )
        last_count["n"] = len(hist)

    bus.subscribe("persona.collapse", actuator_tail)

    # Feedback reactor, ambient signals, heartbeat.
    reactor = FeedbackReactor(bus, vault, printer)
    reactor.wire()
    ambient = AmbientSignals(bus, vault=vault, printer=printer, mood_interval_s=PHI_SQUARED)
    heartbeat = Heartbeat(bus, interval_s=float(args.heartbeat))

    # Print incoming cognition + drops too.
    bus.subscribe("queen.source_law.cognition", lambda t: printer.cognition(t.payload))
    bus.subscribe("dj.track.drop", lambda t: printer.drop(t.payload))

    ambient.start()
    heartbeat.start()

    # Graceful Ctrl-C
    stop_flag = {"stop": False}

    def _sig(_sig, _frame):
        stop_flag["stop"] = True

    signal.signal(signal.SIGINT, _sig)

    try:
        deadline = start + float(args.seconds)
        while time.time() < deadline and not stop_flag["stop"]:
            time.sleep(0.1)
    finally:
        heartbeat.stop()
        ambient.stop()

    # ─────────────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────────────
    elapsed = time.time() - start
    print()
    print("━" * 78)
    print(f"SESSION COMPLETE  (duration {elapsed:.1f}s)")
    print("━" * 78)

    winners: Counter = Counter()
    for rec in actuator.history(n=10_000):
        winners[rec["persona"]] += 1

    print("\nWINNER HISTOGRAM (persona.collapse outcomes that produced an action)")
    total_w = sum(winners.values())
    for name, count in sorted(winners.items(), key=lambda kv: -kv[1]):
        bar = "█" * int(count * 30 / max(1, winners.most_common(1)[0][1]))
        pct = 100 * count / max(1, total_w)
        print(f"  {name:<20s} {count:4d}  ({pct:4.1f}%)  {bar}")
    if not winners:
        print("  (no actions fired — state never crossed any trigger)")

    action_kinds: Counter = Counter()
    action_topics: Counter = Counter()
    for rec in actuator.history(n=10_000):
        action_kinds[rec["action"]["kind"]] += 1
        action_topics[rec["action"]["topic"]] += 1

    print("\nACTION KINDS")
    for kind, count in action_kinds.most_common():
        print(f"  {kind:<20s} {count:4d}")

    print("\nACTION TOPICS")
    for topic, count in action_topics.most_common():
        print(f"  {topic:<40s} {count:4d}")

    print("\nVAULT CARDS BY CATEGORY")
    cats: Counter = Counter()
    for c in vault._contents.values():
        cats[c.category] += 1
    for cat, count in cats.most_common():
        print(f"  {cat:<30s} {count:4d}")
    print(f"  {'TOTAL':<30s} {len(vault):4d}")

    print("\nVAULT FINGERPRINT")
    try:
        print("  " + vault.fingerprint())
    except Exception:
        print("  (unavailable)")

    print()
    print("━" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
