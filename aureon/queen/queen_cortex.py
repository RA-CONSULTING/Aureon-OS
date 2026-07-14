#!/usr/bin/env python3
"""
Queen Cortex -- Brainwave Signal Layers

Like a human brain organizes raw electrical signals into frequency bands
(delta, theta, alpha, beta, gamma), the Queen Cortex organizes the flood
of ThoughtBus signals into 5 structured layers of consciousness.

Architecture:
    ThoughtBus (raw signal flood, 500+ messages/5s)
        |
        v
    Queen Cortex (this file)
        |
        +-- Delta (0.5-4 Hz)  : Deep foundation -- system health, portfolio state
        +-- Theta (4-8 Hz)    : Learning/memory -- historical patterns, wisdom
        +-- Alpha (8-13 Hz)   : Awareness/flow  -- market regime, trend, sentiment
        +-- Beta  (13-30 Hz)  : Active analysis  -- scanners, bots, whales, intelligence
        +-- Gamma (30+ Hz)    : Peak decisions   -- execution, validated opportunities
        |
        v
    queen.cortex.state (published every 1s to ThoughtBus)
        |
        v
    Sentient Loop / NeuronV2 / Decisions

Each band computes amplitude (how active) and coherence (how aligned).
The 9 Auris nodes, Lambda Engine, and Coherence Mandala map naturally
onto these bands -- the cortex unifies what was already there.

Gary Leckey & Tina Brown | April 2026 | The Queen's Brain
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import logging
import math
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass, field, asdict
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

# ============================================================================
# BAND ROUTING — which ThoughtBus topics map to which brainwave band
# ============================================================================

BAND_ROUTING: Dict[str, List[str]] = {
    # Delta — deep/slow/foundational (system heartbeat)
    "delta": [
        "queen.layer.",         # boot lifecycle
        "queen.cortex.",        # cortex own signals (avoid feedback)
        "system.",              # system health
        "portfolio.",           # portfolio state
        "baton.",               # baton relay
    ],
    # Theta — memory/learning (wisdom and historical patterns)
    "theta": [
        "wisdom.",              # wisdom systems
        "decoder.",             # ancient pattern decoders
        "elephant.",            # elephant memory
        "queen.conscience.",    # ethical learning
        "queen.metacognition.", # metacognitive reflections and insights
        "miner.",               # miner brain insights
        "strategy.",            # strategy signals
        "auris.throne.cosmic_state",  # Dr. Auris Throne cosmic analysis
    ],
    # Alpha — awareness/flow (market regime and coherence)
    "alpha": [
        "harmonic.",            # harmonic field snapshots
        "market.",              # market data/regime
        "auris.throne.advisory",  # Dr. Auris Throne advisory
        "auris.throne.alert",     # Dr. Auris Throne alerts
        "queen.broadcast",      # queen awareness broadcasts
        "analytics.",           # analytics insights
        "queen.alert.",         # queen alerts
        "chain.",               # harmonic chain signals
        "monitor.",             # monitoring data
        "mycelium.spore.",      # Mycelium propagated thoughts
        "mycelium.mind.",       # Mind state updates
    ],
    # Beta — active analysis (scanners, intelligence, detection)
    "beta": [
        "intelligence.",        # all intelligence signals
        "scanner.",             # scanner findings
        "hive.scan.",           # hive command scans
        "bot.",                 # bot detection
        "whale.",               # whale sonar
        "enigma.",              # enigma codebreaking
    ],
    # Gamma — peak execution (decisions and actions)
    "gamma": [
        "queen.command.",       # execution commands
        "execution.",           # trade execution
        "orca.",                # kill cycle
        "dtp.",                 # dead man's switch
        "mirror.execution.",    # 4th pass veto
    ],
}

# Expected signals per second per band (for amplitude normalization)
BAND_EXPECTED_RATE = {
    "delta": 5,
    "theta": 10,
    "alpha": 50,
    "beta": 30,
    "gamma": 5,
}

# Solfeggio frequency mapping (cosmetic, for identity/logging)
BAND_FREQUENCY = {
    "delta": 7.83,    # Schumann resonance — Earth's heartbeat
    "theta": 174.0,   # UT — Foundation
    "alpha": 528.0,   # SOL — Love, DNA repair
    "beta":  741.0,   # SI — Intuition, clarity
    "gamma": 963.0,   # TI — Crown, divine unity
}

BAND_NAMES = ["delta", "theta", "alpha", "beta", "gamma"]


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class BandState:
    """State of a single brainwave band."""
    name: str = ""
    amplitude: float = 0.0       # 0-1, how active this band is
    coherence: float = 0.5       # 0-1, how coherent/aligned signals are
    frequency: float = 0.0       # Solfeggio Hz identity
    dominant_signal: str = ""    # Most frequent topic this cycle
    signal_count: int = 0        # Raw signals received this cycle
    summary: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CortexState:
    """Complete brainwave state of the Queen's cortex."""
    delta: BandState = field(default_factory=lambda: BandState(name="delta"))
    theta: BandState = field(default_factory=lambda: BandState(name="theta"))
    alpha: BandState = field(default_factory=lambda: BandState(name="alpha"))
    beta: BandState = field(default_factory=lambda: BandState(name="beta"))
    gamma: BandState = field(default_factory=lambda: BandState(name="gamma"))
    consciousness_psi: float = 0.0      # From Lambda Engine (0-1)
    coherence_gamma_field: float = 0.0   # From Lambda Engine Γ
    dominant_band: str = "alpha"         # Which band has highest amplitude
    cycle: int = 0
    timestamp: float = 0.0

    def band(self, name: str) -> BandState:
        return getattr(self, name, BandState())


# ============================================================================
# BAND ACCUMULATOR — collects and processes signals for one band
# ============================================================================

class BandAccumulator:
    """Collects signals for a single brainwave band and computes its state."""

    def __init__(self, name: str):
        self.name = name
        self._buffer: Deque = deque(maxlen=500)
        self._topic_counts: Counter = Counter()
        self._total: int = 0
        self._coherence_values: List[float] = []

    def ingest(self, thought: Any) -> None:
        """Add a signal to this band."""
        self._buffer.append(thought)
        self._total += 1

        topic = thought.topic if hasattr(thought, "topic") else ""
        self._topic_counts[topic] += 1

        # Extract coherence if present in payload
        payload = thought.payload if hasattr(thought, "payload") else {}
        if isinstance(payload, dict):
            coh = payload.get("coherence") or payload.get("confidence") or payload.get("score")
            if isinstance(coh, (int, float)) and 0 <= coh <= 1:
                self._coherence_values.append(float(coh))

    def process(self) -> BandState:
        """Compute the band's state from accumulated signals."""
        expected = BAND_EXPECTED_RATE.get(self.name, 10)
        amplitude = min(1.0, self._total / max(expected, 1))

        # Coherence: average of extracted coherence values, or estimate from agreement
        if self._coherence_values:
            coherence = sum(self._coherence_values) / len(self._coherence_values)
        elif self._total > 0:
            # Estimate coherence from topic concentration (many topics = less focused)
            unique_topics = len(self._topic_counts)
            coherence = 1.0 / (1.0 + math.log1p(unique_topics))
        else:
            coherence = 0.5

        dominant = self._topic_counts.most_common(1)[0][0] if self._topic_counts else ""

        summary = {
            "unique_topics": len(self._topic_counts),
            "top_topics": dict(self._topic_counts.most_common(3)),
        }

        return BandState(
            name=self.name,
            amplitude=round(amplitude, 4),
            coherence=round(min(1.0, max(0.0, coherence)), 4),
            frequency=BAND_FREQUENCY.get(self.name, 0.0),
            dominant_signal=dominant,
            signal_count=self._total,
            summary=summary,
        )

    def reset(self) -> None:
        """Clear for the next cycle."""
        self._buffer.clear()
        self._topic_counts.clear()
        self._total = 0
        self._coherence_values.clear()


# ============================================================================
# TOPIC ROUTER — classifies a topic into a band
# ============================================================================

def _build_route_index() -> List[tuple]:
    """Pre-compute (prefix, band_name) pairs sorted longest-first for correct matching."""
    pairs = []
    for band_name, prefixes in BAND_ROUTING.items():
        for prefix in prefixes:
            pairs.append((prefix, band_name))
    pairs.sort(key=lambda p: len(p[0]), reverse=True)
    return pairs

_ROUTE_INDEX = _build_route_index()


def classify_topic(topic: str) -> str:
    """Return which brainwave band a ThoughtBus topic belongs to."""
    for prefix, band_name in _ROUTE_INDEX:
        if topic.startswith(prefix):
            return band_name
    # Default: route unclassified signals to Alpha (awareness)
    return "alpha"


# ============================================================================
# THE QUEEN CORTEX
# ============================================================================

class QueenCortex:
    """
    The Queen's brainwave processing cortex.

    Subscribes to ALL ThoughtBus signals, routes them into 5 frequency
    bands (delta through gamma), and publishes a unified CortexState
    every cycle. This organized state replaces the raw signal flood
    with structured consciousness layers.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cycle: int = 0
        self._state: CortexState = CortexState()
        self._lock = threading.Lock()

        # Band accumulators
        self._bands: Dict[str, BandAccumulator] = {
            name: BandAccumulator(name) for name in BAND_NAMES
        }

        # ThoughtBus
        self._thought_bus = None
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            self._thought_bus = get_thought_bus()
        except Exception as e:
            logger.warning(f"Cortex: ThoughtBus unavailable: {e}")

        # Lambda Engine (optional — enriches consciousness metrics)
        self._lambda_engine = None
        try:
            from aureon.core.aureon_lambda_engine import LambdaEngine
            self._lambda_engine = LambdaEngine()
        except Exception:
            pass

        # Mandala operators (optional — enriches Alpha band)
        self._aleph = None
        self._phi_op = None
        try:
            import numpy as np
            from aureon.queen.queen_coherence_mandala import Aleph, Phi
            self._aleph = Aleph()
            self._phi_op = Phi()
        except Exception:
            pass

    # ================================================================
    # LIFECYCLE
    # ================================================================

    def start(self) -> None:
        """Start the cortex background processing thread."""
        if self._running:
            return
        self._running = True

        # Subscribe to all ThoughtBus topics
        if self._thought_bus is not None:
            try:
                self._thought_bus.subscribe("*", self._on_thought)
            except Exception as e:
                logger.warning(f"Cortex: subscribe failed: {e}")

        self._thread = threading.Thread(
            target=self._cortex_loop,
            name="QueenCortex",
            daemon=True,
        )
        self._thread.start()
        logger.info("[CORTEX] Brainwave processing STARTED")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    # ================================================================
    # SIGNAL INGESTION
    # ================================================================

    def _on_thought(self, thought: Any) -> None:
        """Callback: route each incoming thought to the correct band."""
        topic = thought.topic if hasattr(thought, "topic") else ""
        # Skip our own output to avoid feedback loops
        if topic == "queen.cortex.state":
            return
        band_name = classify_topic(topic)
        with self._lock:
            self._bands[band_name].ingest(thought)

    # ================================================================
    # MAIN LOOP
    # ================================================================

    def _cortex_loop(self) -> None:
        """Process signals every 1 second and publish brainwave state."""
        while self._running:
            cycle_start = time.time()
            self._cycle += 1

            try:
                self._process_cycle()
            except Exception as e:
                logger.debug(f"Cortex cycle error: {e}")

            # Sleep remainder of 1-second cycle
            elapsed = time.time() - cycle_start
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

    def _process_cycle(self) -> None:
        """One cycle: process all bands, build state, publish."""
        with self._lock:
            band_states = {}
            for name in BAND_NAMES:
                band_states[name] = self._bands[name].process()
                self._bands[name].reset()

        # Enrich with Lambda Engine if available
        psi = 0.0
        gamma_field = 0.0
        if self._lambda_engine is not None:
            try:
                from aureon.core.aureon_lambda_engine import SubsystemReading
                # Feed band amplitudes as subsystem readings into Lambda
                readings = [
                    SubsystemReading(
                        name=f"cortex_{name}",
                        value=band_states[name].amplitude,
                        confidence=band_states[name].coherence,
                        state=name,
                    )
                    for name in BAND_NAMES
                ]
                ls = self._lambda_engine.step(readings, volatility=0.05)
                from aureon.core.hnc_field import publish_subfield
                publish_subfield("queen_cortex", ls)
                psi = ls.consciousness_psi
                gamma_field = ls.coherence_gamma
            except Exception:
                pass

        # Enrich Alpha band with Mandala operators if available
        if self._aleph is not None and self._phi_op is not None:
            try:
                import numpy as np
                alpha_bs = band_states["alpha"]
                # Feed [amplitude, coherence, signal_count_norm] through ℵ→Φ
                raw = np.array([
                    alpha_bs.amplitude,
                    alpha_bs.coherence,
                    min(1.0, alpha_bs.signal_count / 50.0),
                ])
                filtered = self._aleph(raw)
                pattern = self._phi_op(filtered)
                # Use pattern magnitude as enriched coherence
                enriched = float(np.linalg.norm(pattern) / math.sqrt(3))
                alpha_bs.coherence = round(
                    0.6 * alpha_bs.coherence + 0.4 * min(1.0, enriched), 4
                )
                band_states["alpha"] = alpha_bs
            except Exception:
                pass

        # Determine dominant band (highest amplitude)
        dominant = max(BAND_NAMES, key=lambda n: band_states[n].amplitude)

        # Build unified state
        state = CortexState(
            delta=band_states["delta"],
            theta=band_states["theta"],
            alpha=band_states["alpha"],
            beta=band_states["beta"],
            gamma=band_states["gamma"],
            consciousness_psi=round(psi, 4),
            coherence_gamma_field=round(gamma_field, 4),
            dominant_band=dominant,
            cycle=self._cycle,
            timestamp=time.time(),
        )

        self._state = state

        # Publish to ThoughtBus
        if self._thought_bus is not None:
            try:
                from aureon.core.aureon_thought_bus import Thought
                payload = {
                    "dominant_band": state.dominant_band,
                    "consciousness_psi": state.consciousness_psi,
                    "coherence_gamma": state.coherence_gamma_field,
                    "cycle": state.cycle,
                    "bands": {
                        name: {
                            "amplitude": band_states[name].amplitude,
                            "coherence": band_states[name].coherence,
                            "frequency": band_states[name].frequency,
                            "signal_count": band_states[name].signal_count,
                            "dominant_signal": band_states[name].dominant_signal,
                        }
                        for name in BAND_NAMES
                    },
                }
                self._thought_bus.publish(Thought(
                    source="queen_cortex",
                    topic="queen.cortex.state",
                    payload=payload,
                ))

                # Gamma spike detection — triggers Source Law cogitation
                gamma_amp = band_states["gamma"].amplitude
                if gamma_amp > 0.3:
                    self._thought_bus.publish(Thought(
                        source="queen_cortex",
                        topic="queen.cortex.gamma_spike",
                        payload={
                            "gamma_amplitude": gamma_amp,
                            "gamma_coherence": band_states["gamma"].coherence,
                            "gamma_signals": band_states["gamma"].signal_count,
                            "dominant_signal": band_states["gamma"].dominant_signal,
                        },
                    ))
            except Exception:
                pass

    # ================================================================
    # PUBLIC API
    # ================================================================

    def get_state(self) -> CortexState:
        """Return the latest cortex state."""
        return self._state

    def get_band(self, name: str) -> BandState:
        """Return the latest state for a specific band."""
        return self._state.band(name)

    def get_dominant_band(self) -> str:
        """Return which band is currently most active."""
        return self._state.dominant_band


# ============================================================================
# SINGLETON
# ============================================================================

_CORTEX: Optional[QueenCortex] = None


def get_cortex() -> QueenCortex:
    """Get or create the global QueenCortex singleton."""
    global _CORTEX
    if _CORTEX is None:
        _CORTEX = QueenCortex()
    return _CORTEX
