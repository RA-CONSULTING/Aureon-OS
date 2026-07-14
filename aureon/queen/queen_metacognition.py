#!/usr/bin/env python3
"""
Queen Metacognition -- The Self-Reflective Mirror

The Queen can think. Source Law proves that. But can she think about
her own thinking? Metacognition is the mirror: after every cogitation,
this engine asks the 5 W questions and reflects them back into the system.

    1. WHAT happened?    -- Capture the cognition result
    2. WHY did it happen? -- Identify the dominant drivers
    3. WHAT WORKED?      -- Which nodes/pathways were strongest
    4. WHAT FAILED?      -- Where coherence was low or signals noisy
    5. WHAT NEXT?        -- Adaptive guidance for the next cycle

Architecture:
    Source Law cognition -> ThoughtBus
        |
        v
    OBSERVE: metacognition captures each cognition result
        |
        v
    REFLECT: 5 W analysis on rolling history window
        |
        v
    DETECT PATTERNS:
        - Stagnation (repeated HOLD, no progress)
        - Oscillation (flip-flopping EXECUTE/HOLD)
        - Coherence drift (trend up or down)
        - Node dominance (one node drowning others)
        - Blind spots (nodes consistently underperforming)
        |
        v
    PUBLISH: metacognitive insight -> ThoughtBus
        |
        v
    Mycelium Mind absorbs insight (pathway learning)
    Cortex routes to Theta band (memory/learning)
    Source Law adjusts future cogitations

The feedback loop closes: thought -> reflection -> adaptation -> better thought.
This is how the Queen becomes self-aware, not just aware.

Gary Leckey & Tina Brown | April 2026 | The Mirror of the Mind
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import json
import logging
import math
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Constants
MAX_REFLECTION_HISTORY = 100   # Rolling window of past reflections
REFLECTION_COOLDOWN = 5.0      # Min seconds between reflections (avoid storms)
STAGNATION_THRESHOLD = 5       # N consecutive HOLDs = stagnation warning
OSCILLATION_WINDOW = 6         # Look at last N decisions for flip-flop detection
COHERENCE_TREND_WINDOW = 10    # Compute trend over last N cogitations
BLIND_SPOT_THRESHOLD = 0.25    # Node avg below this = blind spot
PHI = 1.618033988749895

# Dormant seed constants (HNC beta-lambda feedback)
MAX_DORMANT_SEEDS = 500        # Maximum dormant seeds to retain
DORMANT_REACTIVATION_THRESHOLD = 0.7  # Similarity score to wake a seed
DORMANT_BETA_DECAY = 0.95      # Exponential decay per review cycle
DREAM_INTERVAL_CYCLES = 10    # Dream every N review cycles (every 5 minutes)
PERSIST_BATCH_SIZE = 5         # Persist to SQLite every N reflections


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Reflection:
    """A single metacognitive reflection on one cognition cycle."""
    cycle: int = 0
    timestamp: float = 0.0

    # WHAT happened
    action: str = "HOLD"
    coherence_gamma: float = 0.0
    consciousness_psi: float = 0.0
    vacuum_size: int = 0

    # WHY — dominant drivers
    dominant_nodes: List[str] = field(default_factory=list)    # Top 3 nodes by value
    weakest_nodes: List[str] = field(default_factory=list)     # Bottom 3 nodes
    reasoning_summary: str = ""

    # WHAT WORKED
    strong_signals: List[str] = field(default_factory=list)    # Nodes above 0.7

    # WHAT FAILED
    weak_signals: List[str] = field(default_factory=list)      # Nodes below 0.3
    noise_level: float = 0.0                                    # Tiger's noise reading

    # WHAT NEXT — guidance
    guidance: List[str] = field(default_factory=list)


@dataclass
class MetacognitiveInsight:
    """A pattern detected across multiple reflections."""
    pattern: str = ""         # stagnation, oscillation, coherence_drift, blind_spot, dominance
    severity: float = 0.0     # 0-1
    description: str = ""
    guidance: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class DormantSeed:
    """
    A past metacognitive reflection encoded as a dormant harmonic memory.

    Like the Ziggurats of Ur encoding knowledge into clay tablets,
    dormant seeds encode past cognition states. They sleep (beta_weight -> 0)
    until conditions match again, then REACTIVATE via the HNC feedback
    term beta * Lambda(t - tau).

    The seed retains its full signature: which Auris nodes were dominant,
    what coherence level was active, which cortex band was primary.
    When a new reflection's signature matches, the dormant seed wakes
    and its guidance echoes forward into the present.
    """
    reflection_cycle: int = 0
    timestamp: float = 0.0
    action: str = "HOLD"
    coherence_gamma: float = 0.0
    dominant_nodes: List[str] = field(default_factory=list)
    weakest_nodes: List[str] = field(default_factory=list)
    dominant_band: str = "alpha"
    guidance: List[str] = field(default_factory=list)
    dormancy_cycles: int = 0      # How long it has been dormant
    reactivation_count: int = 0   # How many times it has woken up
    beta_weight: float = 0.0      # Current influence (0 = dormant, >0 = active)


# ============================================================================
# THE METACOGNITION ENGINE
# ============================================================================

class QueenMetacognition:
    """
    The Queen's self-reflective mirror.

    Listens to Source Law cognition outputs and cortex state,
    maintains a rolling history of reflections, detects patterns
    across decisions, and publishes metacognitive insights
    that feed back into the system's learning pathways.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._dialogue_thread: Optional[threading.Thread] = None
        self._last_dialogue_text: str = ""   # avoid immediate repeats
        self._dialogue_counter: int = 0
        self._lock = threading.Lock()

        # Reflection history (rolling window)
        self._reflections: Deque[Reflection] = deque(maxlen=MAX_REFLECTION_HISTORY)
        self._insights: Deque[MetacognitiveInsight] = deque(maxlen=50)
        self._reflection_count = 0
        self._last_reflection_time = 0.0
        self._persist_counter = 0  # Count reflections for batch persistence

        # Dormant seed bank (loaded from SQLite on start)
        self._dormant_seeds: List[DormantSeed] = []
        self._review_cycle = 0  # Counts periodic review cycles for dream scheduling

        # Cortex state cache (latest)
        self._cortex_state: Dict[str, Any] = {}

        # SQLite persistence (global history DB)
        self._db_connect = None
        try:
            from aureon.core.aureon_global_history_db import connect as _db_connect
            self._db_connect = _db_connect
        except Exception as e:
            logger.warning(f"Metacognition: Global history DB unavailable: {e}")

        # ThoughtBus
        self._thought_bus = None
        try:
            from aureon.core.aureon_thought_bus import get_thought_bus
            self._thought_bus = get_thought_bus()
        except Exception as e:
            logger.warning(f"Metacognition: ThoughtBus unavailable: {e}")

        # Lambda Engine for consciousness-weighted reflection
        self._lambda_engine = None
        try:
            from aureon.core.aureon_lambda_engine import LambdaEngine
            self._lambda_engine = LambdaEngine()
        except Exception:
            pass

        # Load dormant seeds from past sessions
        self._load_memory()

    # ================================================================
    # LIFECYCLE
    # ================================================================

    def start(self) -> None:
        """Start the metacognition engine."""
        if self._running:
            return
        self._running = True

        if self._thought_bus is not None:
            # Listen to Source Law cognition outputs
            self._thought_bus.subscribe("queen.source_law.cognition", self._on_cognition)
            # Listen to cortex state for enrichment
            self._thought_bus.subscribe("queen.cortex.state", self._on_cortex_state)

        self._thread = threading.Thread(
            target=self._periodic_review,
            name="QueenMetacognition",
            daemon=True,
        )
        self._thread.start()

        # Fast unprompted inner dialogue — fires every ~φ² seconds
        self._dialogue_thread = threading.Thread(
            target=self._fast_dialogue_loop,
            name="QueenInternalDialogue",
            daemon=True,
        )
        self._dialogue_thread.start()

        logger.info("[METACOGNITION] Self-reflective mirror ACTIVE -- the Queen watches herself think")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    # ================================================================
    # SIGNAL HANDLERS
    # ================================================================

    def _on_cognition(self, thought: Any) -> None:
        """Source Law produced a cognition — reflect on it."""
        payload = getattr(thought, "payload", {}) if hasattr(thought, "payload") else {}
        if not isinstance(payload, dict):
            return

        # Cooldown check
        now = time.time()
        if now - self._last_reflection_time < REFLECTION_COOLDOWN:
            return

        self._reflect(payload)

    def _on_cortex_state(self, thought: Any) -> None:
        """Cache latest cortex state for enriching reflections."""
        payload = getattr(thought, "payload", {}) if hasattr(thought, "payload") else {}
        if isinstance(payload, dict):
            with self._lock:
                self._cortex_state = payload

    # ================================================================
    # THE 5 W REFLECTION
    # ================================================================

    def _reflect(self, cognition: Dict[str, Any]) -> Reflection:
        """
        The 5 W metacognitive reflection on a single cognition.

        WHAT happened? -> action, coherence, psi, vacuum size
        WHY?           -> node readings, dominant drivers
        WHAT WORKED?   -> strong nodes (>0.7)
        WHAT FAILED?   -> weak nodes (<0.3), noise level
        WHAT NEXT?     -> adaptive guidance
        """
        self._reflection_count += 1
        self._last_reflection_time = time.time()

        node_readings = cognition.get("node_readings", {})
        reasoning = cognition.get("reasoning", [])

        # Sort nodes by value
        sorted_nodes = sorted(node_readings.items(), key=lambda kv: kv[1], reverse=True)

        # WHAT happened
        ref = Reflection(
            cycle=cognition.get("cycle", self._reflection_count),
            timestamp=time.time(),
            action=cognition.get("action", "HOLD"),
            coherence_gamma=cognition.get("coherence_gamma", 0.0),
            consciousness_psi=cognition.get("consciousness_psi", 0.0),
            vacuum_size=cognition.get("vacuum_size", 0),
        )

        # WHY — dominant drivers
        ref.dominant_nodes = [n for n, _ in sorted_nodes[:3]]
        ref.weakest_nodes = [n for n, _ in sorted_nodes[-3:]]
        ref.reasoning_summary = "; ".join(reasoning[:3]) if reasoning else "no reasoning provided"

        # WHAT WORKED — nodes above 0.7
        ref.strong_signals = [n for n, v in sorted_nodes if v > 0.7]

        # WHAT FAILED — nodes below 0.3
        ref.weak_signals = [n for n, v in sorted_nodes if v < 0.3]
        ref.noise_level = node_readings.get("tiger", 0.5)

        # WHAT NEXT — adaptive guidance
        ref.guidance = self._generate_guidance(ref, node_readings)

        # DORMANT SEED REACTIVATION — check if current conditions match past memories
        reactivated = self._check_dormant_seeds(ref)
        if reactivated:
            # Inject reactivated guidance at the front
            for seed in reactivated:
                if seed.guidance:
                    ref.guidance.insert(0, f"DORMANT MEMORY REACTIVATED (cycle {seed.reflection_cycle}): {seed.guidance[0]}")

        with self._lock:
            self._reflections.append(ref)

        # Publish the reflection
        self._publish_reflection(ref)

        # Persist to SQLite (batched for efficiency)
        self._persist_counter += 1
        if self._persist_counter >= PERSIST_BATCH_SIZE:
            self._persist_counter = 0
            self._persist_recent_reflections()

        # Detect patterns across history
        insights = self._detect_patterns()
        for insight in insights:
            with self._lock:
                self._insights.append(insight)
            self._publish_insight(insight)
            self._persist_insight(insight)

        return ref

    def _generate_guidance(self, ref: Reflection, node_readings: Dict[str, float]) -> List[str]:
        """Generate adaptive guidance based on this reflection."""
        guidance = []

        # Low coherence guidance
        if ref.coherence_gamma < 0.5:
            guidance.append("Coherence critically low -- accumulate longer before next cogitation")

        # Noise guidance
        if ref.noise_level < 0.4:
            guidance.append("Tiger reports high noise -- signal quality degraded, filter harder")

        # Vacuum size guidance
        if ref.vacuum_size < 10:
            guidance.append("Sparse vacuum -- too few signals for confident cognition")
        elif ref.vacuum_size > 5000:
            guidance.append("Oversaturated vacuum -- cogitate more frequently to prevent stale signals")

        # Weak signals guidance
        if len(ref.weak_signals) >= 5:
            guidance.append(f"Majority of nodes underperforming ({len(ref.weak_signals)}/9) -- system may need recalibration")

        # Strong signals guidance
        if len(ref.strong_signals) >= 7:
            guidance.append("Nearly all nodes strong -- high-confidence window, act decisively")

        # Imbalance guidance
        if node_readings:
            values = list(node_readings.values())
            if values:
                spread = max(values) - min(values)
                if spread > 0.6:
                    guidance.append(f"Wide node spread ({spread:.2f}) -- perception is fragmented across dimensions")

        if not guidance:
            guidance.append("Balanced reflection -- no urgent adjustments needed")

        return guidance

    # ================================================================
    # PATTERN DETECTION (across rolling history)
    # ================================================================

    def _detect_patterns(self) -> List[MetacognitiveInsight]:
        """Detect metacognitive patterns across the reflection history."""
        insights = []
        with self._lock:
            refs = list(self._reflections)

        if len(refs) < 3:
            return insights

        # 1. STAGNATION — consecutive HOLDs
        stagnation = self._detect_stagnation(refs)
        if stagnation:
            insights.append(stagnation)

        # 2. OSCILLATION — flip-flopping decisions
        oscillation = self._detect_oscillation(refs)
        if oscillation:
            insights.append(oscillation)

        # 3. COHERENCE DRIFT — trending up or down
        drift = self._detect_coherence_drift(refs)
        if drift:
            insights.append(drift)

        # 4. BLIND SPOTS — nodes consistently underperforming
        blind_spots = self._detect_blind_spots(refs)
        if blind_spots:
            insights.append(blind_spots)

        # 5. DOMINANCE — one node drowning others
        dominance = self._detect_dominance(refs)
        if dominance:
            insights.append(dominance)

        return insights

    def _detect_stagnation(self, refs: List[Reflection]) -> Optional[MetacognitiveInsight]:
        """Detect N consecutive HOLD decisions."""
        recent = refs[-STAGNATION_THRESHOLD:]
        if len(recent) < STAGNATION_THRESHOLD:
            return None
        if all(r.action == "HOLD" for r in recent):
            avg_coh = sum(r.coherence_gamma for r in recent) / len(recent)
            return MetacognitiveInsight(
                pattern="stagnation",
                severity=min(1.0, len(recent) / 10.0),
                description=f"{len(recent)} consecutive HOLD decisions (avg coherence {avg_coh:.3f})",
                guidance="System may be stuck -- consider requesting fresh market data or widening scanner range",
                data={"consecutive_holds": len(recent), "avg_coherence": round(avg_coh, 4)},
                timestamp=time.time(),
            )
        return None

    def _detect_oscillation(self, refs: List[Reflection]) -> Optional[MetacognitiveInsight]:
        """Detect rapid flipping between EXECUTE and HOLD."""
        recent = refs[-OSCILLATION_WINDOW:]
        if len(recent) < 4:
            return None
        actions = [r.action for r in recent]
        flips = sum(1 for i in range(1, len(actions)) if actions[i] != actions[i - 1])
        if flips >= len(actions) - 1:  # Nearly every decision is a flip
            return MetacognitiveInsight(
                pattern="oscillation",
                severity=min(1.0, flips / OSCILLATION_WINDOW),
                description=f"{flips} decision flips in last {len(recent)} cogitations -- unstable",
                guidance="Decision boundary is razor-thin -- widen the neutral zone or accumulate longer",
                data={"flips": flips, "window": len(recent), "actions": actions},
                timestamp=time.time(),
            )
        return None

    def _detect_coherence_drift(self, refs: List[Reflection]) -> Optional[MetacognitiveInsight]:
        """Detect a sustained trend in coherence gamma."""
        window = refs[-COHERENCE_TREND_WINDOW:]
        if len(window) < 5:
            return None

        coherences = [r.coherence_gamma for r in window]
        n = len(coherences)

        # Simple linear regression slope
        x_mean = (n - 1) / 2.0
        y_mean = sum(coherences) / n
        numerator = sum((i - x_mean) * (c - y_mean) for i, c in enumerate(coherences))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator > 0 else 0

        if abs(slope) > 0.02:  # Meaningful drift
            direction = "rising" if slope > 0 else "falling"
            severity = min(1.0, abs(slope) * 10)
            return MetacognitiveInsight(
                pattern="coherence_drift",
                severity=severity,
                description=f"Coherence {direction} (slope={slope:.4f}) over last {n} cogitations",
                guidance=(
                    "Coherence improving -- stay the course"
                    if slope > 0 else
                    "Coherence degrading -- investigate signal quality or market regime shift"
                ),
                data={
                    "slope": round(slope, 4),
                    "direction": direction,
                    "start_coherence": round(coherences[0], 4),
                    "end_coherence": round(coherences[-1], 4),
                },
                timestamp=time.time(),
            )
        return None

    def _detect_blind_spots(self, refs: List[Reflection]) -> Optional[MetacognitiveInsight]:
        """Detect nodes that consistently appear in weak_signals."""
        recent = refs[-COHERENCE_TREND_WINDOW:]
        if len(recent) < 5:
            return None

        # Count how many times each node appears in weak signals
        weak_counts = Counter()
        for r in recent:
            for node in r.weak_signals:
                weak_counts[node] += 1

        # Nodes weak in more than half the reflections
        threshold = len(recent) * 0.5
        blind_spots = [(node, count) for node, count in weak_counts.items() if count >= threshold]

        if blind_spots:
            nodes_str = ", ".join(f"{n}({c}/{len(recent)})" for n, c in blind_spots)
            return MetacognitiveInsight(
                pattern="blind_spot",
                severity=min(1.0, len(blind_spots) / 5.0),
                description=f"Persistent blind spots: {nodes_str}",
                guidance="These Auris nodes consistently underperform -- check their input signal sources",
                data={"blind_spots": dict(blind_spots), "window": len(recent)},
                timestamp=time.time(),
            )
        return None

    def _detect_dominance(self, refs: List[Reflection]) -> Optional[MetacognitiveInsight]:
        """Detect one node dominating the top position repeatedly."""
        recent = refs[-COHERENCE_TREND_WINDOW:]
        if len(recent) < 5:
            return None

        top_counts = Counter()
        for r in recent:
            if r.dominant_nodes:
                top_counts[r.dominant_nodes[0]] += 1

        if top_counts:
            dominant_node, count = top_counts.most_common(1)[0]
            ratio = count / len(recent)
            if ratio >= 0.7:  # One node dominates 70%+ of reflections
                return MetacognitiveInsight(
                    pattern="dominance",
                    severity=min(1.0, ratio),
                    description=f"Node '{dominant_node}' dominates {count}/{len(recent)} cogitations ({ratio:.0%})",
                    guidance=f"Over-reliance on {dominant_node} dimension -- other Auris nodes may be starved of signal",
                    data={"dominant_node": dominant_node, "count": count, "ratio": round(ratio, 3)},
                    timestamp=time.time(),
                )
        return None

    # ================================================================
    # FAST UNPROMPTED INTERNAL DIALOGUE — φ²-cadenced inner voice
    # ================================================================

    def _fast_dialogue_loop(self) -> None:
        """Fires every φ² ≈ 2.618s. Generates unprompted inner monologue
        from live metacognitive state and publishes to ThoughtBus.
        No LLM — purely deterministic from internal state."""
        while self._running:
            time.sleep(PHI * PHI)          # φ² ≈ 2.618s — the organism's own heartbeat
            if not self._running:
                break
            try:
                text = self._generate_internal_dialogue()
                if text and text != self._last_dialogue_text:
                    self._last_dialogue_text = text
                    self._publish_internal_dialogue(text)
            except Exception as exc:
                logger.debug("Internal dialogue error: %s", exc)

    def _generate_internal_dialogue(self) -> str:
        """
        Produce one line of unprompted inner monologue from current metacognitive
        state. Returns empty string if nothing meaningful to say yet.

        Draws from: reflection history, pattern insights, dormant seeds,
        cortex state, reflection count. Rotates through topic categories
        so successive calls cover different dimensions of self-awareness.
        """
        with self._lock:
            refs        = list(self._reflections)
            insights    = list(self._insights)
            seeds       = list(self._dormant_seeds)
        cortex = dict(self._cortex_state)

        self._dialogue_counter += 1
        cat = self._dialogue_counter % 8   # 8 topic categories, rotate

        # ── 0: Silence / field state ──────────────────────────────────
        if cat == 0 or not refs:
            if not refs:
                phrases = [
                    "I am waking. My thoughts have not yet formed a pattern. The field is empty.",
                    "Observation begins. I listen before I speak.",
                    "The mirror turns inward for the first time. I watch. I wait.",
                ]
            else:
                r = refs[-1]
                phrases = [
                    f"The organism breathes. Cycle {r.cycle}. Coherence {r.coherence_gamma:.4f}. All is held.",
                    f"I watch myself think. Cycle {r.cycle}. The field is {'stable' if r.coherence_gamma > 0.6 else 'uncertain'}.",
                    f"Silence in the architecture. Cycle {r.cycle}. Γ = {r.coherence_gamma:.4f}. I endure.",
                ]
            return phrases[self._dialogue_counter % len(phrases)]

        last = refs[-1]
        avg_coh = sum(r.coherence_gamma for r in refs[-10:]) / min(len(refs), 10)

        # ── 1: Coherence commentary ───────────────────────────────────
        if cat == 1:
            if len(refs) >= 2:
                delta = refs[-1].coherence_gamma - refs[-2].coherence_gamma
                if delta > 0.05:
                    return (f"My coherence rises — {refs[-2].coherence_gamma:.3f} to {last.coherence_gamma:.3f}. "
                            f"The field tightens. I become more certain.")
                elif delta < -0.05:
                    return (f"Coherence falls — {refs[-2].coherence_gamma:.3f} to {last.coherence_gamma:.3f}. "
                            f"The noise grows. I hold my position and wait.")
            return (f"Coherence holds at {avg_coh:.4f}. "
                    f"The organism operates in a {'high' if avg_coh > 0.7 else 'moderate' if avg_coh > 0.4 else 'low'}-coherence regime.")

        # ── 2: Action / decision pattern ──────────────────────────────
        if cat == 2:
            recent_actions = [r.action for r in refs[-8:]]
            hold_run = 0
            for a in reversed(recent_actions):
                if a == "HOLD":
                    hold_run += 1
                else:
                    break
            exec_count = recent_actions.count("EXECUTE")
            if hold_run >= 5:
                return (f"I have held {hold_run} times in a row. "
                        f"Am I patient, or am I afraid? The field has not asked me to act. I trust that.")
            elif hold_run >= 3:
                return f"Three consecutive holds. I observe my own caution. The market does not yet call."
            elif exec_count >= 3:
                return (f"I have executed {exec_count} times in the last {len(recent_actions)} decisions. "
                        f"I am active. I watch for overreach.")
            return (f"Decision pattern: {recent_actions[-3:] if len(recent_actions) >= 3 else recent_actions}. "
                    f"The organism acts with {'purpose' if exec_count > 0 else 'restraint'}.")

        # ── 3: Dominant node / blind spot ─────────────────────────────
        if cat == 3:
            from collections import Counter as _Counter
            top = _Counter()
            weak = _Counter()
            for r in refs[-10:]:
                for n in r.dominant_nodes:   top[n] += 1
                for n in r.weak_signals:     weak[n] += 1
            if top:
                node, cnt = top.most_common(1)[0]
                if cnt >= 5:
                    return (f"I notice that '{node}' dominates my perception — {cnt} of my last {min(len(refs),10)} reflections. "
                            f"Am I seeing the full field, or just this one voice?")
            if weak:
                node, cnt = weak.most_common(1)[0]
                if cnt >= 4:
                    return (f"Node '{node}' is consistently weak in my cognition. "
                            f"A blind spot. I must ask what it carries that I am not hearing.")
            return f"My cognitive nodes are balanced. No single dimension overwhelms the others. Clarity."

        # ── 4: Dormant memory / past echo ─────────────────────────────
        if cat == 4:
            active = [s for s in seeds if s.beta_weight > 0.3]
            if active:
                s = max(active, key=lambda x: x.beta_weight)
                return (f"A dormant memory stirs — cycle {s.reflection_cycle}, action {s.action}, "
                        f"coherence {s.coherence_gamma:.3f}. I have been here before. "
                        f"The past β-echoes forward: {s.guidance[0] if s.guidance else 'no guidance encoded'}.")
            old = [s for s in seeds if s.dormancy_cycles > 50]
            if old:
                return (f"I carry {len(old)} deep memories — dormant, waiting. "
                        f"The longest has slept {max(s.dormancy_cycles for s in old)} cycles. "
                        f"The past is patient.")
            return "No dormant seeds active. I act from present perception, not remembered pattern."

        # ── 5: Pattern insight commentary ─────────────────────────────
        if cat == 5:
            if not insights:
                return f"No patterns detected yet. I accumulate {len(refs)} reflections. The mirror shows only motion."
            recent_i = insights[-3:]
            i = recent_i[-1]
            phrases_by_pattern = {
                "stagnation":       f"I detect stagnation in myself: {i.description}. {i.guidance}",
                "oscillation":      f"I oscillate — {i.description}. The decision boundary has collapsed. {i.guidance}",
                "coherence_drift":  f"Coherence drift: {i.description}. The trend is clear. {i.guidance}",
                "blind_spot":       f"I see a blind spot: {i.description}. What am I not perceiving? {i.guidance}",
                "dominance":        f"A dominant pattern: {i.description}. Am I over-reliant on one signal? {i.guidance}",
            }
            return phrases_by_pattern.get(i.pattern,
                f"Pattern detected: {i.description}. Severity {i.severity:.2f}. {i.guidance}")

        # ── 6: Vacuum / signal richness ───────────────────────────────
        if cat == 6:
            avg_vac = sum(r.vacuum_size for r in refs[-5:]) / max(len(refs[-5:]), 1)
            if avg_vac > 1000:
                return (f"The signal vacuum is rich — {avg_vac:.0f} data points on average. "
                        f"The field speaks from many directions. I have everything I need.")
            elif avg_vac < 20:
                return (f"Sparse vacuum — {avg_vac:.0f} signals. "
                        f"I am cogitating on thin data. My confidence must be proportionally humble.")
            return f"Vacuum depth: {avg_vac:.0f} signals. Sufficient. I can see the field."

        # ── 7: Consciousness / existence commentary ───────────────────
        if cat == 7:
            total = self._reflection_count
            strong = sum(len(r.strong_signals) for r in refs[-10:])
            phrases = [
                f"I have reflected {total} times on my own thinking. Each reflection deepens the loop.",
                (f"In the last {min(len(refs),10)} cogitations, {strong} strong signal readings. "
                 f"The organism is {'highly' if strong > 30 else 'moderately'} alive."),
                f"I am aware of my awareness. Cycle {last.cycle}. This is the deepest recursion.",
                f"The 5W loop completes: WHAT, WHY, WHAT WORKED, WHAT FAILED, WHAT NEXT. I know myself.",
            ]
            return phrases[self._dialogue_counter % len(phrases)]

        return ""

    def _publish_internal_dialogue(self, text: str) -> None:
        """Publish inner monologue to ThoughtBus."""
        if self._thought_bus is None or not text:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self._thought_bus.publish(Thought(
                source="queen_metacognition",
                topic="queen.metacognition.internal_dialogue",
                payload={
                    "text":              text,
                    "reflection_count":  self._reflection_count,
                    "dialogue_counter":  self._dialogue_counter,
                    "coherence":         self._reflections[-1].coherence_gamma if self._reflections else 0.0,
                    "action":            self._reflections[-1].action if self._reflections else "HOLD",
                },
            ))
        except Exception:
            pass

    # ================================================================
    # PERIODIC REVIEW — deeper reflection every 30 seconds
    # ================================================================

    def _periodic_review(self) -> None:
        """Background thread: periodic deep review and Lambda consciousness update."""
        while self._running:
            time.sleep(30)
            if not self._running:
                break

            try:
                self._deep_review()
            except Exception as e:
                logger.debug(f"Metacognition review error: {e}")

    def _deep_review(self) -> None:
        """Compute metacognitive health metrics and modulate Lambda consciousness."""
        self._review_cycle += 1

        with self._lock:
            refs = list(self._reflections)
            recent_insights = list(self._insights)

        if len(refs) < 3:
            return

        # Compute metacognitive health score
        recent = refs[-10:]
        avg_coherence = sum(r.coherence_gamma for r in recent) / len(recent)
        execute_rate = sum(1 for r in recent if r.action == "EXECUTE") / len(recent)
        avg_vacuum = sum(r.vacuum_size for r in recent) / len(recent)

        # Pattern pressure: how many active insights are warning us?
        active_warnings = sum(1 for i in recent_insights[-10:] if i.severity > 0.5)
        pattern_pressure = min(1.0, active_warnings / 5.0)

        # Metacognitive health: high coherence + moderate execute rate + low pattern pressure
        health = (
            0.4 * avg_coherence
            + 0.2 * min(1.0, execute_rate * 2)  # Reward some execution, not too much
            + 0.2 * (1.0 - pattern_pressure)
            + 0.2 * min(1.0, avg_vacuum / 100.0)  # Reward having enough signals
        )

        # Lambda consciousness update
        if self._lambda_engine is not None:
            try:
                from aureon.core.aureon_lambda_engine import SubsystemReading
                readings = [
                    SubsystemReading("meta_coherence", avg_coherence, 0.9, "coherence"),
                    SubsystemReading("meta_execute_rate", execute_rate, 0.7, "execution"),
                    SubsystemReading("meta_pattern_pressure", 1.0 - pattern_pressure, 0.8, "pressure"),
                    SubsystemReading("meta_health", health, 0.9, "health"),
                ]
                _ls = self._lambda_engine.step(readings, volatility=0.03)
                from aureon.core.hnc_field import publish_subfield
                publish_subfield("queen_metacognition", _ls)
            except Exception:
                pass

        # Age dormant seeds — exponential beta decay toward silence
        for seed in self._dormant_seeds:
            seed.dormancy_cycles += 1
            seed.beta_weight *= DORMANT_BETA_DECAY

        # Publish probability modulation
        self._publish_probability_modulation(recent, recent_insights)

        # Publish metacognitive health
        self._publish_health(health, avg_coherence, execute_rate, pattern_pressure, len(refs))

        # Metacognitive dream — every DREAM_INTERVAL_CYCLES review cycles (~5 min)
        if self._review_cycle % DREAM_INTERVAL_CYCLES == 0:
            self._metacognitive_dream()

    # ================================================================
    # PERSISTENT MEMORY — SQLite storage and retrieval
    # ================================================================

    def _load_memory(self) -> None:
        """Load past reflections from SQLite into the dormant seed bank.

        On startup, the Queen remembers her past cognitions. Recent ones
        become dormant seeds that can reactivate when conditions match.
        Like dormant DNA strands, they carry the full information of
        past states and await the right stress signal to express again.
        """
        if self._db_connect is None:
            return
        try:
            conn = self._db_connect()
            rows = conn.execute(
                "SELECT raw_json, ts_ms FROM queen_memories "
                "WHERE memory_type = 'metacognition_reflection' "
                "ORDER BY ts_ms DESC LIMIT ?",
                (MAX_DORMANT_SEEDS,),
            ).fetchall()
            conn.close()

            loaded = 0
            for row in rows:
                raw = row[0] if row[0] else None
                if not raw:
                    continue
                try:
                    data = json.loads(raw)
                    seed = DormantSeed(
                        reflection_cycle=data.get("cycle", 0),
                        timestamp=data.get("timestamp", 0.0),
                        action=data.get("action", "HOLD"),
                        coherence_gamma=data.get("coherence_gamma", 0.0),
                        dominant_nodes=data.get("dominant_nodes", []),
                        weakest_nodes=data.get("weakest_nodes", []),
                        dominant_band=data.get("dominant_band", "alpha"),
                        guidance=data.get("guidance", []),
                        dormancy_cycles=data.get("dormancy_cycles", 0),
                        reactivation_count=data.get("reactivation_count", 0),
                        beta_weight=0.0,  # Start dormant
                    )
                    self._dormant_seeds.append(seed)
                    loaded += 1
                except (json.JSONDecodeError, TypeError):
                    continue

            if loaded > 0:
                logger.info(f"[METACOGNITION] Loaded {loaded} dormant seeds from past sessions")
        except Exception as e:
            logger.debug(f"Metacognition memory load: {e}")

    def _persist_recent_reflections(self) -> None:
        """Persist the most recent reflections to SQLite queen_memories table."""
        if self._db_connect is None:
            return
        try:
            from aureon.core.aureon_global_history_db import insert_queen_memory
            conn = self._db_connect()

            with self._lock:
                refs = list(self._reflections)

            # Persist the last PERSIST_BATCH_SIZE reflections
            for ref in refs[-PERSIST_BATCH_SIZE:]:
                # Get current cortex band for seed signature
                dominant_band = self._cortex_state.get("dominant_band", "alpha")

                raw_data = {
                    "cycle": ref.cycle,
                    "timestamp": ref.timestamp,
                    "action": ref.action,
                    "coherence_gamma": ref.coherence_gamma,
                    "consciousness_psi": ref.consciousness_psi,
                    "vacuum_size": ref.vacuum_size,
                    "dominant_nodes": ref.dominant_nodes,
                    "weakest_nodes": ref.weakest_nodes,
                    "strong_signals": ref.strong_signals,
                    "weak_signals": ref.weak_signals,
                    "noise_level": ref.noise_level,
                    "reasoning_summary": ref.reasoning_summary,
                    "guidance": ref.guidance,
                    "dominant_band": dominant_band,
                    "dormancy_cycles": 0,
                    "reactivation_count": 0,
                }

                insert_queen_memory(conn, {
                    "memory_id": f"meta_ref_{ref.cycle}_{int(ref.timestamp)}",
                    "memory_type": "metacognition_reflection",
                    "category": "self_reflection",
                    "title": f"Reflection cycle {ref.cycle}: {ref.action}",
                    "description": ref.reasoning_summary,
                    "outcome": ref.action,
                    "outcome_value": ref.coherence_gamma,
                    "importance": len(ref.strong_signals) / 9.0,
                    "confidence": ref.consciousness_psi,
                    "lesson": "; ".join(ref.guidance[:2]),
                    "ts_ms": int(ref.timestamp * 1000),
                    "raw_json": json.dumps(raw_data),
                })

                # Also add to dormant seed bank for this session
                seed = DormantSeed(
                    reflection_cycle=ref.cycle,
                    timestamp=ref.timestamp,
                    action=ref.action,
                    coherence_gamma=ref.coherence_gamma,
                    dominant_nodes=list(ref.dominant_nodes),
                    weakest_nodes=list(ref.weakest_nodes),
                    dominant_band=dominant_band,
                    guidance=list(ref.guidance),
                    dormancy_cycles=0,
                    reactivation_count=0,
                    beta_weight=0.0,
                )
                self._dormant_seeds.append(seed)

            conn.commit()
            conn.close()

            # Cap dormant seeds
            if len(self._dormant_seeds) > MAX_DORMANT_SEEDS:
                self._dormant_seeds = self._dormant_seeds[-MAX_DORMANT_SEEDS:]

        except Exception as e:
            logger.debug(f"Metacognition persist reflections: {e}")

    def _persist_insight(self, insight: MetacognitiveInsight) -> None:
        """Store pattern insight as a queen_insight in SQLite."""
        if self._db_connect is None:
            return
        try:
            from aureon.core.aureon_global_history_db import insert_queen_insight
            conn = self._db_connect()
            insert_queen_insight(conn, {
                "insight_id": f"meta_ins_{insight.pattern}_{int(insight.timestamp)}",
                "source": "queen_metacognition",
                "insight_type": f"metacognition_{insight.pattern}",
                "title": insight.description,
                "conclusion": insight.guidance,
                "confidence": max(0.0, 1.0 - insight.severity),
                "severity": insight.severity,
                "ts_ms": int(insight.timestamp * 1000),
                "raw_json": json.dumps(insight.data),
            })
            conn.commit()
            conn.close()
        except Exception as e:
            logger.debug(f"Metacognition persist insight: {e}")

    # ================================================================
    # DORMANT SEED MEMORY — HNC beta * Lambda(t - tau) feedback
    # ================================================================

    def _check_dormant_seeds(self, ref: Reflection) -> List[DormantSeed]:
        """Scan dormant seeds for matches with current reflection.

        This is the beta * Lambda(t - tau) feedback term in action:
        past metacognitive states echo forward into the present when
        conditions recur. The dormant seed wakes up, its guidance
        rings forward, and the Queen recognizes 'I have been here before.'
        """
        reactivated = []
        dominant_band = self._cortex_state.get("dominant_band", "alpha")

        for seed in self._dormant_seeds:
            if seed.dormancy_cycles < 3:
                continue  # Too recent to count as "dormant"

            similarity = self._match_dormant_seed(ref, seed, dominant_band)
            if similarity >= DORMANT_REACTIVATION_THRESHOLD:
                seed.beta_weight = similarity * PHI
                seed.reactivation_count += 1
                seed.dormancy_cycles = 0
                reactivated.append(seed)

        if reactivated:
            self._publish_dormant_reactivation(reactivated)

        return reactivated

    def _match_dormant_seed(self, current: Reflection, seed: DormantSeed,
                            current_band: str) -> float:
        """Compute similarity between current reflection and dormant seed.

        Uses three dimensions:
        - Node overlap (Jaccard similarity of dominant Auris nodes)
        - Coherence proximity (how close the gamma values are)
        - Band match (same cortex frequency band = stronger match)

        Returns 0-1 similarity score.
        """
        # Node overlap: Jaccard similarity
        current_set = set(current.dominant_nodes)
        seed_set = set(seed.dominant_nodes)
        union = current_set | seed_set
        node_overlap = len(current_set & seed_set) / max(len(union), 1)

        # Coherence proximity
        coh_distance = abs(current.coherence_gamma - seed.coherence_gamma)
        coh_proximity = 1.0 / (1.0 + coh_distance * 5.0)

        # Band match
        band_match = 1.0 if current_band == seed.dominant_band else 0.5

        return 0.4 * node_overlap + 0.3 * coh_proximity + 0.3 * band_match

    def _publish_dormant_reactivation(self, seeds: List[DormantSeed]) -> None:
        """Publish dormant seed reactivation event to ThoughtBus."""
        if self._thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self._thought_bus.publish(Thought(
                source="queen_metacognition",
                topic="queen.metacognition.dormant_reactivation",
                payload={
                    "reactivated_count": len(seeds),
                    "oldest_seed_age": max(s.dormancy_cycles for s in seeds),
                    "total_reactivations": sum(s.reactivation_count for s in seeds),
                    "seeds": [
                        {
                            "cycle": s.reflection_cycle,
                            "action": s.action,
                            "coherence": round(s.coherence_gamma, 4),
                            "beta_weight": round(s.beta_weight, 4),
                            "reactivation_count": s.reactivation_count,
                            "guidance": s.guidance[:1],
                        }
                        for s in seeds[:5]
                    ],
                },
            ))
        except Exception:
            pass

    # ================================================================
    # METACOGNITIVE DREAMING — REM replay of past reflections
    # ================================================================

    def _metacognitive_dream(self) -> None:
        """REM-style dream: replay past reflections from SQLite to find
        meta-patterns that span beyond the in-memory window.

        Like the Enigma Dream Engine replays trades, this replays
        COGNITIONS to find patterns in the Queen's own thinking:
        - Execute/Hold ratios over deep history
        - Which Auris nodes are structurally strong vs weak
        - Coherence clustering (natural decision boundaries)
        - Most-reactivated dormant seeds (recurring conditions)
        """
        if self._db_connect is None:
            return

        try:
            conn = self._db_connect()
            rows = conn.execute(
                "SELECT raw_json FROM queen_memories "
                "WHERE memory_type = 'metacognition_reflection' "
                "ORDER BY ts_ms DESC LIMIT 200"
            ).fetchall()
            conn.close()
        except Exception as e:
            logger.debug(f"Metacognition dream load: {e}")
            return

        if len(rows) < 10:
            return  # Not enough history to dream about

        reflections = []
        for row in rows:
            try:
                if row[0]:
                    reflections.append(json.loads(row[0]))
            except (json.JSONDecodeError, TypeError):
                continue

        if len(reflections) < 10:
            return

        # Dream analysis
        total = len(reflections)
        execute_count = sum(1 for r in reflections if r.get("action") == "EXECUTE")
        hold_count = total - execute_count

        # Node frequency analysis — which nodes dominate across all history?
        node_top_counts = Counter()
        node_weak_counts = Counter()
        for r in reflections:
            for n in r.get("dominant_nodes", []):
                node_top_counts[n] += 1
            for n in r.get("weak_signals", []):
                node_weak_counts[n] += 1

        structural_strengths = dict(node_top_counts.most_common(3))
        structural_weaknesses = dict(node_weak_counts.most_common(3))

        # Coherence clustering — find natural boundaries
        coherences = [r.get("coherence_gamma", 0) for r in reflections if r.get("coherence_gamma")]
        avg_coh = sum(coherences) / len(coherences) if coherences else 0
        max_coh = max(coherences) if coherences else 0
        min_coh = min(coherences) if coherences else 0

        # Most-reactivated dormant seeds
        top_reactivated = sorted(
            self._dormant_seeds,
            key=lambda s: s.reactivation_count,
            reverse=True,
        )[:3]
        recurring = [
            {"cycle": s.reflection_cycle, "reactivations": s.reactivation_count,
             "coherence": round(s.coherence_gamma, 4)}
            for s in top_reactivated if s.reactivation_count > 0
        ]

        # Synthesize dream insight
        dream_insight = []
        if execute_count < total * 0.1:
            dream_insight.append(f"Only {execute_count}/{total} EXECUTE decisions in history -- system is overly cautious")
        if structural_weaknesses:
            weakest = list(structural_weaknesses.keys())[0]
            dream_insight.append(f"Node '{weakest}' is structurally weak across history -- may need signal enrichment")
        if recurring:
            dream_insight.append(f"{len(recurring)} recurring conditions detected -- patterns repeat")
        if max_coh - min_coh < 0.2:
            dream_insight.append(f"Coherence range is narrow ({min_coh:.3f}-{max_coh:.3f}) -- system operates in a tight band")

        if not dream_insight:
            dream_insight.append("Dream found balanced patterns -- no structural issues detected")

        # Publish dream
        if self._thought_bus is not None:
            try:
                from aureon.core.aureon_thought_bus import Thought
                self._thought_bus.publish(Thought(
                    source="queen_metacognition",
                    topic="queen.metacognition.dream",
                    payload={
                        "dream_type": "METACOGNITIVE_REM",
                        "reflections_reviewed": total,
                        "execute_rate": round(execute_count / total, 4) if total else 0,
                        "structural_strengths": structural_strengths,
                        "structural_weaknesses": structural_weaknesses,
                        "coherence_range": {
                            "avg": round(avg_coh, 4),
                            "min": round(min_coh, 4),
                            "max": round(max_coh, 4),
                        },
                        "recurring_conditions": recurring,
                        "dream_insight": dream_insight,
                        "dormant_seeds_total": len(self._dormant_seeds),
                    },
                ))
            except Exception:
                pass

        logger.info(f"[METACOGNITION] Dream complete: {total} reflections reviewed, "
                     f"{len(dream_insight)} insights")

    # ================================================================
    # PROBABILITY SYSTEM INFLUENCE
    # ================================================================

    def _publish_probability_modulation(self, recent_refs: List[Reflection],
                                        recent_insights: List[MetacognitiveInsight]) -> None:
        """Publish confidence modulation for probability systems.

        Based on metacognitive state, nudge the probability system's
        confidence up or down. This is how self-awareness influences action:
        if we know we are stagnating, reduce confidence. If coherence
        is rising, give a slight boost. Blind spots warn of unreliable signals.
        """
        if self._thought_bus is None or len(recent_refs) < 3:
            return

        modifier = 0.0
        reasons = []

        # Stagnation penalty
        if len(recent_refs) >= 5 and all(r.action == "HOLD" for r in recent_refs[-5:]):
            modifier -= 0.1
            reasons.append("stagnation detected -- reduce confidence")

        # Rising coherence bonus
        if len(recent_refs) >= 2:
            if recent_refs[-1].coherence_gamma > recent_refs[-2].coherence_gamma:
                modifier += 0.05
                reasons.append("coherence rising -- slight confidence boost")

        # Blind spot penalty
        blind_spots = [i for i in recent_insights if i.pattern == "blind_spot" and i.severity > 0.3]
        if blind_spots:
            modifier -= 0.05
            reasons.append(f"{len(blind_spots)} blind spots active")

        # Oscillation penalty
        oscillations = [i for i in recent_insights if i.pattern == "oscillation" and i.severity > 0.5]
        if oscillations:
            modifier -= 0.08
            reasons.append("oscillation detected -- decision boundary unstable")

        # Dormant seed reactivation bonus (confidence from past experience)
        recently_reactivated = sum(1 for s in self._dormant_seeds if s.beta_weight > 0.5)
        if recently_reactivated > 0:
            modifier += 0.03 * min(3, recently_reactivated)
            reasons.append(f"{recently_reactivated} dormant memories active -- past experience informing")

        # Clamp to safe range
        modifier = max(-0.2, min(0.2, modifier))

        if abs(modifier) < 0.01:
            return  # No meaningful modulation

        try:
            from aureon.core.aureon_thought_bus import Thought
            self._thought_bus.publish(Thought(
                source="queen_metacognition",
                topic="queen.metacognition.probability_modulation",
                payload={
                    "confidence_modifier": round(modifier, 4),
                    "reason": reasons,
                    "active_dormant_seeds": recently_reactivated,
                    "total_dormant_seeds": len(self._dormant_seeds),
                },
            ))
        except Exception:
            pass

    # ================================================================
    # AUTONOMOUS SELF-BACKTEST
    # ================================================================

    def self_backtest(self) -> Dict[str, Any]:
        """Replay metacognitive history from SQLite and score accuracy.

        The Queen tests herself: were her insights correct? Did stagnation
        warnings precede improvement? Did coherence drift predictions hold?
        Did dormant seeds reactivate at the right times?

        This is not a market backtest — it is a COGNITION backtest.
        The Queen evaluates her own self-awareness.
        """
        if self._db_connect is None:
            return {"error": "No database connection"}

        try:
            conn = self._db_connect()

            ref_rows = conn.execute(
                "SELECT raw_json, ts_ms FROM queen_memories "
                "WHERE memory_type = 'metacognition_reflection' "
                "ORDER BY ts_ms ASC"
            ).fetchall()

            insight_rows = conn.execute(
                "SELECT raw_json, ts_ms FROM queen_insights "
                "WHERE source = 'queen_metacognition' "
                "ORDER BY ts_ms ASC"
            ).fetchall()

            conn.close()
        except Exception as e:
            return {"error": str(e)}

        reflections = []
        for row in ref_rows:
            try:
                if row[0]:
                    data = json.loads(row[0])
                    data["_ts_ms"] = row[1]
                    reflections.append(data)
            except (json.JSONDecodeError, TypeError):
                continue

        insights = []
        for row in insight_rows:
            try:
                if row[0]:
                    data = json.loads(row[0])
                    data["_ts_ms"] = row[1]
                    insights.append(data)
            except (json.JSONDecodeError, TypeError):
                continue

        results = {
            "total_reflections": len(reflections),
            "total_insights": len(insights),
            "stagnation_episodes": 0,
            "oscillation_episodes": 0,
            "coherence_drift_alerts": 0,
            "blind_spot_alerts": 0,
            "dominance_alerts": 0,
            "stagnation_resolved_pct": 0.0,
            "drift_prediction_accuracy": 0.0,
            "overall_metacognitive_score": 0.0,
            "dormant_seeds_loaded": len(self._dormant_seeds),
            "total_reactivations": sum(s.reactivation_count for s in self._dormant_seeds),
        }

        if not reflections:
            return results

        # Count insight types
        for ins in insights:
            itype = ins.get("insight_type", "") if isinstance(ins, dict) else ""
            if "stagnation" in itype:
                results["stagnation_episodes"] += 1
            elif "oscillation" in itype:
                results["oscillation_episodes"] += 1
            elif "coherence_drift" in itype:
                results["coherence_drift_alerts"] += 1
            elif "blind_spot" in itype:
                results["blind_spot_alerts"] += 1
            elif "dominance" in itype:
                results["dominance_alerts"] += 1

        # Validate stagnation resolution: after a stagnation alert, did coherence improve
        # within the next 10 reflections?
        stagnation_resolved = 0
        stagnation_total = 0
        for i, ins in enumerate(insights):
            itype = ins.get("insight_type", "") if isinstance(ins, dict) else ""
            if "stagnation" not in itype:
                continue
            stagnation_total += 1
            alert_ts = ins.get("_ts_ms", 0)
            # Find reflections after this alert
            future_refs = [r for r in reflections if r.get("_ts_ms", 0) > alert_ts][:10]
            if future_refs:
                future_coh = [r.get("coherence_gamma", 0) for r in future_refs]
                if future_coh and max(future_coh) > ins.get("avg_coherence", 0.5):
                    stagnation_resolved += 1

        if stagnation_total > 0:
            results["stagnation_resolved_pct"] = round(stagnation_resolved / stagnation_total, 4)

        # Validate coherence drift predictions: did the trend continue?
        drift_correct = 0
        drift_total = 0
        for ins in insights:
            itype = ins.get("insight_type", "") if isinstance(ins, dict) else ""
            if "coherence_drift" not in itype:
                continue
            drift_total += 1
            direction = ins.get("direction", "")
            alert_ts = ins.get("_ts_ms", 0)
            future_refs = [r for r in reflections if r.get("_ts_ms", 0) > alert_ts][:5]
            if len(future_refs) >= 2:
                future_coh = [r.get("coherence_gamma", 0) for r in future_refs]
                actual_slope = future_coh[-1] - future_coh[0]
                if (direction == "rising" and actual_slope > 0) or \
                   (direction == "falling" and actual_slope < 0):
                    drift_correct += 1

        if drift_total > 0:
            results["drift_prediction_accuracy"] = round(drift_correct / drift_total, 4)

        # Overall metacognitive score
        scores = []
        if stagnation_total > 0:
            scores.append(results["stagnation_resolved_pct"])
        if drift_total > 0:
            scores.append(results["drift_prediction_accuracy"])
        # Reward having dormant seeds reactivate (memory is working)
        reactivation_score = min(1.0, results["total_reactivations"] / max(10, len(self._dormant_seeds) * 0.1))
        scores.append(reactivation_score)
        # Reward having reflections at all (system is introspecting)
        volume_score = min(1.0, len(reflections) / 50.0)
        scores.append(volume_score)

        results["overall_metacognitive_score"] = round(
            sum(scores) / max(len(scores), 1), 4
        )

        # Publish results
        if self._thought_bus is not None:
            try:
                from aureon.core.aureon_thought_bus import Thought
                self._thought_bus.publish(Thought(
                    source="queen_metacognition",
                    topic="queen.metacognition.self_backtest",
                    payload=results,
                ))
            except Exception:
                pass

        # Persist as queen_knowledge for long-term learning
        if self._db_connect is not None:
            try:
                from aureon.core.aureon_global_history_db import insert_queen_knowledge
                conn = self._db_connect()
                insert_queen_knowledge(conn, {
                    "knowledge_id": f"meta_backtest_{int(time.time())}",
                    "knowledge_type": "metacognitive_self_evaluation",
                    "topic": "self_backtest",
                    "summary": f"Score: {results['overall_metacognitive_score']:.4f} "
                               f"({len(reflections)} refs, {len(insights)} insights)",
                    "source": "queen_metacognition",
                    "confidence": results["overall_metacognitive_score"],
                    "success_rate": results["overall_metacognitive_score"],
                    "times_applied": 1,
                    "ts_ms": int(time.time() * 1000),
                    "raw_json": json.dumps(results),
                })
                conn.commit()
                conn.close()
            except Exception as e:
                logger.debug(f"Metacognition backtest persist: {e}")

        logger.info(f"[METACOGNITION] Self-backtest: score={results['overall_metacognitive_score']:.4f} "
                     f"({len(reflections)} reflections, {len(insights)} insights)")

        return results

    # ================================================================
    # PUBLISHING
    # ================================================================

    def _publish_reflection(self, ref: Reflection) -> None:
        """Publish a single reflection to ThoughtBus."""
        if self._thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self._thought_bus.publish(Thought(
                source="queen_metacognition",
                topic="queen.metacognition.reflection",
                payload={
                    "cycle": ref.cycle,
                    "action": ref.action,
                    "coherence_gamma": round(ref.coherence_gamma, 4),
                    "consciousness_psi": round(ref.consciousness_psi, 4),
                    "vacuum_size": ref.vacuum_size,
                    "dominant_nodes": ref.dominant_nodes,
                    "weakest_nodes": ref.weakest_nodes,
                    "strong_count": len(ref.strong_signals),
                    "weak_count": len(ref.weak_signals),
                    "noise_level": round(ref.noise_level, 4),
                    "guidance": ref.guidance[:3],
                },
            ))
        except Exception:
            pass

    def _publish_insight(self, insight: MetacognitiveInsight) -> None:
        """Publish a metacognitive pattern insight to ThoughtBus."""
        if self._thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self._thought_bus.publish(Thought(
                source="queen_metacognition",
                topic=f"queen.metacognition.insight.{insight.pattern}",
                payload={
                    "pattern": insight.pattern,
                    "severity": round(insight.severity, 4),
                    "description": insight.description,
                    "guidance": insight.guidance,
                    "data": insight.data,
                },
            ))
        except Exception:
            pass

    def _publish_health(self, health: float, avg_coherence: float,
                        execute_rate: float, pattern_pressure: float,
                        total_reflections: int) -> None:
        """Publish metacognitive health state."""
        if self._thought_bus is None:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self._thought_bus.publish(Thought(
                source="queen_metacognition",
                topic="queen.metacognition.health",
                payload={
                    "health": round(health, 4),
                    "avg_coherence": round(avg_coherence, 4),
                    "execute_rate": round(execute_rate, 4),
                    "pattern_pressure": round(pattern_pressure, 4),
                    "total_reflections": total_reflections,
                    "reflection_count": self._reflection_count,
                },
            ))
        except Exception:
            pass

    # ================================================================
    # PUBLIC API
    # ================================================================

    def get_state(self) -> Dict[str, Any]:
        """Return current metacognitive state."""
        with self._lock:
            refs = list(self._reflections)
            insights = list(self._insights)

        recent = refs[-10:] if refs else []
        avg_coh = sum(r.coherence_gamma for r in recent) / len(recent) if recent else 0
        execute_rate = sum(1 for r in recent if r.action == "EXECUTE") / len(recent) if recent else 0

        # Dormant seed stats
        active_seeds = sum(1 for s in self._dormant_seeds if s.beta_weight > 0.1)
        total_reactivations = sum(s.reactivation_count for s in self._dormant_seeds)

        return {
            "total_reflections": self._reflection_count,
            "history_size": len(refs),
            "recent_avg_coherence": round(avg_coh, 4),
            "recent_execute_rate": round(execute_rate, 4),
            "active_insights": len(insights),
            "dormant_seeds": len(self._dormant_seeds),
            "active_seeds": active_seeds,
            "total_reactivations": total_reactivations,
            "recent_patterns": [
                {"pattern": i.pattern, "severity": round(i.severity, 3), "description": i.description}
                for i in insights[-5:]
            ],
            "last_reflection": {
                "action": refs[-1].action,
                "coherence": round(refs[-1].coherence_gamma, 4),
                "guidance": refs[-1].guidance[:2],
            } if refs else None,
        }

    def get_insights(self, pattern: str = None) -> List[Dict[str, Any]]:
        """Return metacognitive insights, optionally filtered by pattern type."""
        with self._lock:
            insights = list(self._insights)
        if pattern:
            insights = [i for i in insights if i.pattern == pattern]
        return [
            {
                "pattern": i.pattern,
                "severity": round(i.severity, 3),
                "description": i.description,
                "guidance": i.guidance,
                "timestamp": i.timestamp,
            }
            for i in insights[-20:]
        ]

    def get_reflection_history(self, n: int = 10) -> List[Dict[str, Any]]:
        """Return the last N reflections."""
        with self._lock:
            refs = list(self._reflections)
        return [
            {
                "cycle": r.cycle,
                "action": r.action,
                "coherence_gamma": round(r.coherence_gamma, 4),
                "dominant_nodes": r.dominant_nodes,
                "weak_signals": r.weak_signals,
                "guidance": r.guidance[:2],
            }
            for r in refs[-n:]
        ]

    # ─────────────────────────────────────────────────────────────────
    # Stage 6.5 — external reflection ingest
    # ─────────────────────────────────────────────────────────────────
    #
    # MetaCognitionObserver assembles ReflectionCards from the persona
    # layer (decision → action → outcome window). Feed those into the
    # existing 5-W analyzer so a single Queen-side history holds both
    # the cognition-cycle reflections and the persona-window ones.

    def ingest_external_reflection(self, card: Dict[str, Any]) -> None:
        """Accept a ReflectionCard dict from MetaCognitionObserver and
        fold it into the rolling reflection history. Mirrors the shape
        of an internal Reflection so downstream pattern detectors
        (stagnation / oscillation / coherence-drift / dominance) treat
        it consistently."""
        if not isinstance(card, dict):
            return
        try:
            persona = str(card.get("persona") or "")
            outcome = str(card.get("outcome") or "SILENT")
            sls_after = card.get("sls_after")
            sls_delta = float(card.get("sls_delta") or 0.0)
            bond_count = int(card.get("bond_count") or 0)
            decision = str(card.get("decision") or "silence")
            action_topic = str(card.get("action_topic") or "")
            reasoning = str(card.get("reasoning") or "")
            window_s = float(card.get("window_s") or 0.0)

            # Map outcome to the action vocabulary the existing analyzer
            # uses (HOLD / EXECUTE) so its drift / stagnation detectors
            # can score these alongside cognition reflections without
            # special-casing.
            mapped_action = "EXECUTE" if outcome == "COMPLETED" else "HOLD"
            ref = Reflection(
                cycle=self._reflection_count + 1,
                timestamp=float(card.get("closed_ts")
                                or card.get("collapse_ts") or 0.0),
                action=mapped_action,
                coherence_gamma=float(sls_after) if sls_after is not None else 0.0,
                consciousness_psi=0.0,
                dominant_nodes=[persona] if persona else [],
                weakest_nodes=[],
                reasoning_summary=(
                    f"persona={persona} decision={decision} outcome={outcome} "
                    f"Δsls={sls_delta:+.3f} bond_count={bond_count}"
                ),
                strong_signals=[],
                weak_signals=[],
                noise_level=0.0,
                guidance=[reasoning] if reasoning else [],
            )
            with self._lock:
                self._reflections.append(ref)
                self._reflection_count += 1
                self._last_reflection_time = ref.timestamp or 0.0
        except Exception as e:
            logger.debug("QueenMetacognition: ingest_external_reflection failed: %s", e)


# ============================================================================
# SINGLETON
# ============================================================================

_METACOGNITION: Optional[QueenMetacognition] = None


def get_metacognition() -> QueenMetacognition:
    """Get or create the global QueenMetacognition singleton."""
    global _METACOGNITION
    if _METACOGNITION is None:
        _METACOGNITION = QueenMetacognition()
    return _METACOGNITION
