#!/usr/bin/env python3
"""
Mycelium Mind -- Thought Propagation & Neural Plasticity Engine

Thoughts propagate like mycelium spores. Each one can spawn children.
Synaptic pathways strengthen on success, weaken on failure.
The Lambda Engine's consciousness level controls the learning rate.
As above (Queen consciousness), so below (synaptic weights).

Architecture:
    ThoughtBus signals
        |
        v
    ABSORB: signals become ThoughtSpores
        |
        v
    PROPAGATE: spores travel synaptic pathways (weighted)
        |
        v
    SPAWN: high-coherence spores create child spores
        |
        v
    PUBLISH: children re-enter ThoughtBus (feedback loop)
        |
        v
    LEARN: Source Law outcomes strengthen/weaken pathways

The feedback loop IS neural plasticity:
    Decision -> Outcome -> Learn -> Reweight -> Better Propagation -> Repeat

Gary Leckey & Tina Brown | April 2026 | As Above, So Below
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import logging
import math
import threading
import time
import uuid
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Constants
MAX_GENERATIONS = 3        # Root(0) -> child(1) -> grandchild(2) -> great-grandchild(3)
SPAWN_THRESHOLD = 0.6      # Minimum coherence to spawn a child spore
PROPAGATION_CYCLE = 1.0    # Seconds between propagation cycles
MAX_SPORES_PER_CYCLE = 200 # Cap to prevent runaway
MIN_PATHWAY_WEIGHT = 0.1
MAX_PATHWAY_WEIGHT = 2.0
DEFAULT_PLASTICITY = 0.1


# ============================================================================
# THOUGHT SPORE — a thought that can propagate and spawn children
# ============================================================================

@dataclass
class ThoughtSpore:
    """A thought that propagates through the mycelium mind."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    parent_id: Optional[str] = None
    topic: str = ""
    source: str = ""
    coherence: float = 0.5
    generation: int = 0         # 0=root, 1=child, etc.
    pathway: List[str] = field(default_factory=list)
    lambda_echo: float = 0.0   # Lambda(t) value when created
    timestamp: float = field(default_factory=time.time)


# ============================================================================
# SYNAPTIC PATHWAY — weighted connection between topic domains
# ============================================================================

@dataclass
class SynapticPathway:
    """A weighted connection between signal domains. Hebbian learning."""
    source_domain: str
    target_domain: str
    weight: float = 1.0
    plasticity: float = DEFAULT_PLASTICITY
    activations: int = 0
    successes: int = 0

    def transmit(self, coherence: float) -> float:
        """Transmit a spore through this pathway. Returns weighted coherence."""
        self.activations += 1
        return coherence * self.weight

    def strengthen(self, reward: float) -> None:
        """Hebbian: strengthen on success."""
        delta = self.plasticity * reward
        self.weight = min(MAX_PATHWAY_WEIGHT, self.weight + delta)
        self.successes += 1

    def weaken(self, penalty: float) -> None:
        """Weaken on failure."""
        delta = self.plasticity * penalty
        self.weight = max(MIN_PATHWAY_WEIGHT, self.weight - delta)

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.activations, 1)


# ============================================================================
# DEFAULT PATHWAY MAP — how signal domains connect
# ============================================================================

# (source_domain_prefix, target_domain_prefix)
DEFAULT_PATHWAYS = [
    # Intelligence flows TO cortex and source law
    ("intelligence.", "cortex"),
    ("intelligence.", "source_law"),
    # Harmonic flows TO cortex
    ("harmonic.",     "cortex"),
    ("harmonic.",     "auris_throne"),
    # Whale/enigma flows TO cortex and intelligence
    ("whale.",        "cortex"),
    ("enigma.",       "cortex"),
    # Queen systems flow TO source law
    ("queen.alert.",  "source_law"),
    ("queen.cortex.", "source_law"),
    # Auris Throne flows TO cortex and source law
    ("auris.throne.", "cortex"),
    ("auris.throne.", "source_law"),
    # Bot detection flows TO intelligence
    ("bot.",          "intelligence"),
    # Scanner flows TO intelligence
    ("scanner.",      "intelligence"),
    ("hive.scan.",    "intelligence"),
    # Source law cognition flows BACK TO mycelium (the feedback loop)
    ("queen.source_law.", "mycelium"),
    # Metacognitive insights flow TO source law and cortex (self-awareness loop)
    ("queen.metacognition.", "source_law"),
    ("queen.metacognition.", "cortex"),
]


# ============================================================================
# THE MYCELIUM MIND
# ============================================================================

class MyceliumMind:
    """
    The thought propagation engine. Turns flat signals into a growing,
    learning, self-reinforcing web of interconnected thoughts.

    Thoughts propagate like spores. Strong thoughts spawn children.
    Lambda consciousness modulates learning rate. Outcomes feed back
    to strengthen winning pathways and weaken losing ones.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cycle = 0
        self._lock = threading.Lock()

        # Spore queue (incoming, waiting for propagation)
        self._spore_queue: Deque[ThoughtSpore] = deque(maxlen=5000)

        # Synaptic pathways
        self._pathways: Dict[str, SynapticPathway] = {}
        self._init_pathways()

        # Statistics
        self._total_spores_created = 0
        self._total_spores_spawned = 0
        self._total_propagations = 0

        # Lambda Engine for consciousness-modulated plasticity
        self._lambda_engine = None
        try:
            from aureon.core.aureon_lambda_engine import LambdaEngine
            self._lambda_engine = LambdaEngine()
        except Exception:
            pass

        # ThoughtBus
        self._thought_bus = None
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            self._thought_bus = get_thought_bus()
        except Exception:
            pass

        # Current Lambda state
        self._psi = 0.0         # consciousness level
        self._lambda_t = 0.0    # master equation value

    def _init_pathways(self):
        """Build initial synaptic pathway map."""
        for src, tgt in DEFAULT_PATHWAYS:
            key = f"{src}->{tgt}"
            self._pathways[key] = SynapticPathway(
                source_domain=src,
                target_domain=tgt,
            )

    # ================================================================
    # LIFECYCLE
    # ================================================================

    def start(self) -> None:
        if self._running:
            return
        self._running = True

        if self._thought_bus is not None:
            # Absorb all signals (passive)
            self._thought_bus.subscribe("*", self._absorb)
            # Listen for Source Law outcomes (for learning)
            self._thought_bus.subscribe("queen.source_law.cognition", self._on_cognition)

        self._thread = threading.Thread(
            target=self._propagation_loop,
            name="MyceliumMind",
            daemon=True,
        )
        self._thread.start()
        logger.info("[MYCELIUM MIND] Thought propagation ACTIVE — spores spreading")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    # ================================================================
    # ABSORB — signals become spores
    # ================================================================

    def _absorb(self, thought: Any) -> None:
        """Convert a ThoughtBus signal into a ThoughtSpore."""
        topic = getattr(thought, "topic", "") if hasattr(thought, "topic") else ""
        source = getattr(thought, "source", "") if hasattr(thought, "source") else ""

        # Don't absorb our own spores (prevent feedback explosion)
        if topic.startswith("mycelium.spore.") or topic.startswith("mycelium.mind."):
            return
        # Don't absorb source law output here (handled by _on_cognition)
        if topic.startswith("queen.source_law."):
            return

        payload = getattr(thought, "payload", {}) if hasattr(thought, "payload") else {}
        coherence = 0.5
        if isinstance(payload, dict):
            c = payload.get("coherence") or payload.get("confidence") or payload.get("score")
            if isinstance(c, (int, float)) and 0 <= c <= 1:
                coherence = float(c)

        spore = ThoughtSpore(
            topic=topic,
            source=source,
            coherence=coherence,
            generation=0,
            lambda_echo=self._lambda_t,
        )

        with self._lock:
            self._spore_queue.append(spore)
            self._total_spores_created += 1

    # ================================================================
    # PROPAGATION LOOP
    # ================================================================

    def _propagation_loop(self) -> None:
        """Main loop: propagate spores, spawn children, modulate plasticity."""
        while self._running:
            cycle_start = time.time()
            self._cycle += 1

            try:
                self._propagate_cycle()
            except Exception as e:
                logger.debug(f"Mycelium Mind cycle error: {e}")

            elapsed = time.time() - cycle_start
            if elapsed < PROPAGATION_CYCLE:
                time.sleep(PROPAGATION_CYCLE - elapsed)

    def _propagate_cycle(self) -> None:
        """One propagation cycle: drain queue, propagate, spawn, echo."""
        # Drain spore queue
        with self._lock:
            spores = []
            while self._spore_queue and len(spores) < MAX_SPORES_PER_CYCLE:
                spores.append(self._spore_queue.popleft())

        if not spores:
            return

        # Propagate each spore through matching pathways
        children = []
        propagation_coherences = []

        for spore in spores:
            for key, pathway in self._pathways.items():
                # Match: spore topic starts with pathway source domain
                if spore.topic.startswith(pathway.source_domain):
                    transmitted = pathway.transmit(spore.coherence)
                    propagation_coherences.append(transmitted)
                    self._total_propagations += 1

                    # Record pathway in spore's journey
                    spore.pathway.append(key)

                    # SPAWN: if transmitted coherence exceeds threshold and not at max gen
                    if transmitted > SPAWN_THRESHOLD and spore.generation < MAX_GENERATIONS:
                        child = ThoughtSpore(
                            parent_id=spore.id,
                            topic=spore.topic,
                            source=f"mycelium_gen{spore.generation + 1}",
                            coherence=transmitted,
                            generation=spore.generation + 1,
                            pathway=list(spore.pathway),
                            lambda_echo=self._lambda_t,
                        )
                        children.append(child)
                        self._total_spores_spawned += 1

        # Publish child spores back to ThoughtBus (THE FEEDBACK LOOP)
        if children and self._thought_bus is not None:
            try:
                from aureon.core.aureon_thought_bus import Thought
                for child in children[:50]:  # Cap publishing per cycle
                    # Use mycelium.spore.{original_topic_prefix} as topic
                    prefix = child.topic.split(".")[0] if "." in child.topic else child.topic
                    self._thought_bus.publish(Thought(
                        source="mycelium_mind",
                        topic=f"mycelium.spore.{prefix}",
                        payload={
                            "spore_id": child.id,
                            "parent_id": child.parent_id,
                            "generation": child.generation,
                            "coherence": round(child.coherence, 4),
                            "original_topic": child.topic,
                            "pathway": child.pathway[-3:],  # Last 3 hops
                            "lambda_echo": round(child.lambda_echo, 4),
                        },
                    ))
            except Exception:
                pass

        # LAMBDA ECHO: compute consciousness from propagation metrics
        if self._lambda_engine is not None:
            try:
                from aureon.core.aureon_lambda_engine import SubsystemReading
                avg_coh = sum(propagation_coherences) / max(len(propagation_coherences), 1)
                readings = [
                    SubsystemReading("propagation_volume", min(1.0, len(spores) / 100.0), 0.8, "volume"),
                    SubsystemReading("avg_coherence", avg_coh, 0.9, "coherence"),
                    SubsystemReading("spawn_rate", min(1.0, len(children) / max(len(spores), 1)), 0.7, "spawning"),
                ]
                ls = self._lambda_engine.step(readings, volatility=0.02)
                from aureon.core.hnc_field import publish_subfield
                publish_subfield("queen_mycelium_mind", ls)
                self._psi = ls.consciousness_psi
                self._lambda_t = ls.lambda_t

                # MODULATE PLASTICITY based on consciousness
                # High psi = faster learning, low psi = conservative
                plasticity_mod = 0.05 + (self._psi * 0.15)  # Range: 0.05 to 0.20
                for pathway in self._pathways.values():
                    pathway.plasticity = plasticity_mod
            except Exception:
                pass

        # Publish mind state periodically (every 5 cycles)
        if self._cycle % 5 == 0:
            self._publish_mind_state(len(spores), len(children))

    # ================================================================
    # LEARNING — outcomes modify pathways
    # ================================================================

    def _on_cognition(self, thought: Any) -> None:
        """Source Law outcome feeds back to strengthen/weaken pathways."""
        payload = getattr(thought, "payload", {}) if hasattr(thought, "payload") else {}
        if not isinstance(payload, dict):
            return

        coherence = payload.get("coherence_gamma", 0)
        action = payload.get("action", "HOLD")

        # Strengthen pathways that contributed to high-coherence cognitions
        for pathway in self._pathways.values():
            if pathway.activations > 0:
                if coherence > 0.7:
                    pathway.strengthen(coherence * 0.1)
                elif coherence < 0.4:
                    pathway.weaken(0.05)

    # ================================================================
    # PUBLISHING
    # ================================================================

    def _publish_mind_state(self, spores_processed: int, children_spawned: int) -> None:
        """Publish mycelium mind state to ThoughtBus."""
        if self._thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought

            # Top pathways by weight
            sorted_paths = sorted(self._pathways.values(), key=lambda p: p.weight, reverse=True)
            top_5 = [(p.source_domain, p.target_domain, round(p.weight, 3), p.activations)
                     for p in sorted_paths[:5]]

            self._thought_bus.publish(Thought(
                source="mycelium_mind",
                topic="mycelium.mind.state",
                payload={
                    "cycle": self._cycle,
                    "psi": round(self._psi, 4),
                    "lambda_t": round(self._lambda_t, 4),
                    "total_spores": self._total_spores_created,
                    "total_spawned": self._total_spores_spawned,
                    "total_propagations": self._total_propagations,
                    "spores_this_cycle": spores_processed,
                    "children_this_cycle": children_spawned,
                    "pathways": len(self._pathways),
                    "avg_weight": round(sum(p.weight for p in self._pathways.values()) / max(len(self._pathways), 1), 4),
                    "top_pathways": top_5,
                },
            ))
        except Exception:
            pass

    # ================================================================
    # PUBLIC API
    # ================================================================

    def get_mind_state(self) -> Dict:
        """Return current state of the mycelium mind."""
        sorted_paths = sorted(self._pathways.values(), key=lambda p: p.weight, reverse=True)
        return {
            "cycle": self._cycle,
            "consciousness_psi": round(self._psi, 4),
            "lambda_t": round(self._lambda_t, 4),
            "total_spores_created": self._total_spores_created,
            "total_spores_spawned": self._total_spores_spawned,
            "total_propagations": self._total_propagations,
            "queue_size": len(self._spore_queue),
            "pathways": len(self._pathways),
            "avg_pathway_weight": round(
                sum(p.weight for p in self._pathways.values()) / max(len(self._pathways), 1), 4
            ),
            "strongest": [(p.source_domain, p.target_domain, round(p.weight, 3))
                          for p in sorted_paths[:5]],
            "weakest": [(p.source_domain, p.target_domain, round(p.weight, 3))
                        for p in sorted_paths[-3:]],
        }


# ============================================================================
# SINGLETON
# ============================================================================

_MIND: Optional[MyceliumMind] = None


def get_mycelium_mind() -> MyceliumMind:
    """Get or create the global MyceliumMind singleton."""
    global _MIND
    if _MIND is None:
        _MIND = MyceliumMind()
    return _MIND
