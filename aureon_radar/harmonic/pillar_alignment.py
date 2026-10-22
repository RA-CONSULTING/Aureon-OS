"""
PillarAlignment — The Six Singing as One
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Runs all six Aureon pillar agents in parallel on a shared context, measures
their harmonic alignment (signal consensus + frequency lock + phase coherence
+ mean Γ), and emits a unified alignment signal.

Usage:
    from aureon.alignment import PillarAlignment

    alignment = PillarAlignment()
    alignment.load_pillars()                      # loads all 6 pillar agents

    # Run one alignment cycle with shared context
    result = alignment.run_cycle(context={
        "query": "Should we enter BTCUSDT now?",
        "love_stream_lambda": 0.87,
        "queen_gamma": 0.88,
    })

    if result.lighthouse_cleared:
        print(f"★ LIGHTHOUSE BURNS  signal={result.consensus_signal}  Γ={result.alignment_score:.4f}")

The alignment result is published to the ThoughtBus as 'pillar.alignment'.
When the Lighthouse clears (alignment > 0.945), 'pillar.lighthouse.cleared'
fires and the Queen / Miner / trading layer know the six have become one.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aureon.alignment.harmonic_resonance import (
    full_harmonic_analysis,
    LIGHTHOUSE_THRESHOLD,
    FUNDAMENTAL_HZ,
)

logger = logging.getLogger("aureon.alignment.pillars")


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class AlignmentConfig:
    """Configuration for the PillarAlignment engine."""

    max_concurrent_pillars: int = 6
    cycle_timeout_s: float = 30.0
    fundamental_hz: float = FUNDAMENTAL_HZ
    lighthouse_threshold: float = LIGHTHOUSE_THRESHOLD
    auto_load_pillars: bool = True


@dataclass
class AlignmentCycleResult:
    """Result of one full alignment cycle."""

    cycle_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)
    duration_s: float = 0.0

    # Per-pillar results (raw PillarResult.to_dict())
    pillar_results: List[Dict[str, Any]] = field(default_factory=list)

    # Consensus
    consensus_signal: str = "NEUTRAL"
    consensus_confidence: float = 0.0

    # Alignment breakdown
    signal_consensus: float = 0.0
    harmonic_lock: float = 0.0
    phase_coherence: float = 0.0
    mean_coherence: float = 0.0
    alignment_score: float = 0.0
    lighthouse_cleared: bool = False

    # Counts
    total_pillars: int = 0
    responding_pillars: int = 0
    agreeing_pillars: int = 0
    errors: List[str] = field(default_factory=list)

    # Harmonic profile
    mean_frequency_hz: float = 0.0
    per_pillar_consonance: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp,
            "duration_s": round(self.duration_s, 4),
            "pillar_results": self.pillar_results,
            "consensus_signal": self.consensus_signal,
            "consensus_confidence": round(self.consensus_confidence, 4),
            "signal_consensus": round(self.signal_consensus, 4),
            "harmonic_lock": round(self.harmonic_lock, 4),
            "phase_coherence": round(self.phase_coherence, 4),
            "mean_coherence": round(self.mean_coherence, 4),
            "alignment_score": round(self.alignment_score, 4),
            "lighthouse_cleared": self.lighthouse_cleared,
            "total_pillars": self.total_pillars,
            "responding_pillars": self.responding_pillars,
            "agreeing_pillars": self.agreeing_pillars,
            "errors": self.errors,
            "mean_frequency_hz": round(self.mean_frequency_hz, 2),
            "per_pillar_consonance": {k: round(v, 4) for k, v in self.per_pillar_consonance.items()},
        }


# ─────────────────────────────────────────────────────────────────────────────
# PillarAlignment engine
# ─────────────────────────────────────────────────────────────────────────────


class PillarAlignment:
    """
    The alignment engine. Owns the 6 pillar agents, runs them in parallel,
    computes alignment, publishes to the bus.
    """

    def __init__(self, config: Optional[AlignmentConfig] = None):
        self.config = config or AlignmentConfig()
        self._pillars: Dict[str, Any] = {}           # name → PillarAgent
        self._pillar_classes: Dict[str, type] = {}
        self._lock = threading.RLock()
        self._thought_bus = None
        self._wire_thought_bus()

        # Metrics
        self._cycles_run = 0
        self._lighthouse_cleared_count = 0
        self._errors = 0
        self._start_time = time.time()
        self._last_result: Optional[AlignmentCycleResult] = None
        self._history: List[AlignmentCycleResult] = []
        self._max_history = 200

        if self.config.auto_load_pillars:
            try:
                self.load_pillars()
            except Exception as e:
                logger.warning("auto-load of pillars failed: %s", e)

    def _wire_thought_bus(self):
        try:
            from aureon.core.aureon_thought_bus import ThoughtBus
            self._thought_bus = ThoughtBus()
            logger.info("PillarAlignment wired to ThoughtBus")
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Pillar loading
    # ─────────────────────────────────────────────────────────────────────

    def load_pillars(self) -> Dict[str, Any]:
        """Load all 6 pillar agents with a shared in-house AI adapter."""
        try:
            from aureon.wisdom.aureon_pillar_agents import ALL_PILLARS, _build_default_adapter
        except Exception as e:
            logger.error("Could not import pillar agents: %s", e)
            raise

        with self._lock:
            adapter = _build_default_adapter()
            self._pillars = {}
            self._pillar_classes = dict(ALL_PILLARS)
            for name, cls in ALL_PILLARS.items():
                try:
                    self._pillars[name] = cls(adapter=adapter)
                    logger.info("Pillar loaded: %s", name)
                except Exception as e:
                    logger.warning("Failed to load pillar %s: %s", name, e)
                    self._errors += 1
        return self._pillars

    def add_pillar(self, name: str, instance: Any) -> None:
        """Manually register a pillar instance (for tests or custom pillars)."""
        with self._lock:
            self._pillars[name] = instance

    def list_pillars(self) -> List[str]:
        with self._lock:
            return list(self._pillars.keys())

    @property
    def pillar_count(self) -> int:
        return len(self._pillars)

    # ─────────────────────────────────────────────────────────────────────
    # Running one pillar
    # ─────────────────────────────────────────────────────────────────────

    def _run_single_pillar(
        self,
        name: str,
        pillar: Any,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Run a single pillar's analyse() and normalise the result."""
        try:
            result = pillar.analyse(context)
            # Pillar returns PillarResult dataclass — convert to dict
            if hasattr(result, "to_dict"):
                d = result.to_dict()
            elif isinstance(result, dict):
                d = result
            else:
                d = {
                    "signal": "NEUTRAL",
                    "confidence": 0.5,
                    "coherence": 0.5,
                    "frequency_hz": self.config.fundamental_hz,
                    "analysis": str(result),
                    "data": {},
                }
            d.setdefault("pillar", name)
            return d
        except Exception as e:
            logger.warning("Pillar %s failed: %s", name, e)
            return {
                "pillar": name,
                "signal": "NEUTRAL",
                "confidence": 0.0,
                "coherence": 0.0,
                "frequency_hz": self.config.fundamental_hz,
                "analysis": "",
                "data": {},
                "error": str(e),
            }

    # ─────────────────────────────────────────────────────────────────────
    # The alignment cycle
    # ─────────────────────────────────────────────────────────────────────

    def run_cycle(
        self,
        context: Optional[Dict[str, Any]] = None,
        parallel: bool = True,
    ) -> AlignmentCycleResult:
        """
        Execute one alignment cycle:
          1. Run all pillars on the shared context (parallel by default)
          2. Compute harmonic alignment across their results
          3. Publish the result to the ThoughtBus
          4. Return the AlignmentCycleResult
        """
        ctx = dict(context or {})
        ctx.setdefault("timestamp", time.time())
        ctx.setdefault("fundamental_hz", self.config.fundamental_hz)

        start = time.time()
        result = AlignmentCycleResult()

        with self._lock:
            pillars = dict(self._pillars)

        if not pillars:
            result.errors.append("no_pillars_loaded")
            self._record(result)
            return result

        result.total_pillars = len(pillars)

        # Run the pillars
        pillar_dicts: List[Dict[str, Any]] = []
        if parallel and len(pillars) > 1:
            with ThreadPoolExecutor(max_workers=min(len(pillars), self.config.max_concurrent_pillars)) as executor:
                futures = {
                    executor.submit(self._run_single_pillar, name, inst, ctx): name
                    for name, inst in pillars.items()
                }
                for fut in as_completed(futures, timeout=self.config.cycle_timeout_s):
                    try:
                        d = fut.result(timeout=5)
                        if d is not None:
                            pillar_dicts.append(d)
                    except Exception as e:
                        name = futures[fut]
                        result.errors.append(f"{name}: {e}")
        else:
            for name, inst in pillars.items():
                d = self._run_single_pillar(name, inst, ctx)
                if d is not None:
                    pillar_dicts.append(d)

        result.pillar_results = pillar_dicts
        result.responding_pillars = len([d for d in pillar_dicts if not d.get("error")])

        # Harmonic analysis
        analysis = full_harmonic_analysis(
            pillar_results=pillar_dicts,
            t=ctx["timestamp"],
            fundamental_hz=self.config.fundamental_hz,
        )

        # Fold into result
        result.signal_consensus = analysis.signal_consensus
        result.harmonic_lock = analysis.harmonic_lock
        result.phase_coherence = analysis.phase_coherence
        result.mean_coherence = analysis.mean_coherence
        result.alignment_score = analysis.alignment_score
        result.lighthouse_cleared = analysis.alignment_score > self.config.lighthouse_threshold
        result.consensus_signal = analysis.dominant_signal
        result.agreeing_pillars = analysis.agreeing_pillars
        result.mean_frequency_hz = analysis.mean_frequency_hz
        result.per_pillar_consonance = analysis.per_pillar_consonance

        # Compute mean confidence across agreeing pillars
        agreeing = [
            d for d in pillar_dicts
            if str(d.get("signal", "")).upper() == result.consensus_signal
        ]
        if agreeing:
            result.consensus_confidence = sum(
                float(d.get("confidence", 0)) for d in agreeing
            ) / len(agreeing)

        result.duration_s = time.time() - start
        self._record(result)
        self._publish(result)
        return result

    # ─────────────────────────────────────────────────────────────────────
    # Fast synthetic alignment (for stress tests + when pillars unavailable)
    # ─────────────────────────────────────────────────────────────────────

    def run_synthetic_cycle(
        self,
        signals: Optional[List[Dict[str, Any]]] = None,
    ) -> AlignmentCycleResult:
        """
        Run an alignment cycle on synthetic signals (skip the pillar agents).

        Useful for stress testing the alignment math without incurring the
        agent conversation overhead, and for feeding externally-computed
        signals (e.g. from the love stream) into the alignment engine.
        """
        start = time.time()
        result = AlignmentCycleResult()

        if not signals:
            # Default: use the canonical pillar stack
            signals = self._default_pillar_signals()

        result.pillar_results = signals
        result.total_pillars = len(signals)
        result.responding_pillars = len([d for d in signals if not d.get("error")])

        analysis = full_harmonic_analysis(
            pillar_results=signals,
            fundamental_hz=self.config.fundamental_hz,
        )

        result.signal_consensus = analysis.signal_consensus
        result.harmonic_lock = analysis.harmonic_lock
        result.phase_coherence = analysis.phase_coherence
        result.mean_coherence = analysis.mean_coherence
        result.alignment_score = analysis.alignment_score
        result.lighthouse_cleared = analysis.alignment_score > self.config.lighthouse_threshold
        result.consensus_signal = analysis.dominant_signal
        result.agreeing_pillars = analysis.agreeing_pillars
        result.mean_frequency_hz = analysis.mean_frequency_hz
        result.per_pillar_consonance = analysis.per_pillar_consonance

        agreeing = [d for d in signals if str(d.get("signal", "")).upper() == result.consensus_signal]
        if agreeing:
            result.consensus_confidence = sum(float(d.get("confidence", 0)) for d in agreeing) / len(agreeing)

        result.duration_s = time.time() - start
        self._record(result)
        self._publish(result)
        return result

    def _default_pillar_signals(self) -> List[Dict[str, Any]]:
        """Canonical pillar frequency stack — useful default for tests."""
        return [
            {"pillar": "NexusAgent",    "signal": "NEUTRAL", "confidence": 0.7, "coherence": 0.8, "frequency_hz": 432.0},
            {"pillar": "OmegaAgent",    "signal": "NEUTRAL", "confidence": 0.7, "coherence": 0.8, "frequency_hz": 432.0},
            {"pillar": "InfiniteAgent", "signal": "BUY",     "confidence": 0.8, "coherence": 0.85, "frequency_hz": 528.0},
            {"pillar": "PianoAgent",    "signal": "BUY",     "confidence": 0.75, "coherence": 0.8, "frequency_hz": 396.0},
            {"pillar": "QGITAAgent",    "signal": "BUY",     "confidence": 0.8, "coherence": 0.9, "frequency_hz": 528.0},
            {"pillar": "AurisAgent",    "signal": "BUY",     "confidence": 0.75, "coherence": 0.85, "frequency_hz": 741.0},
        ]

    # ─────────────────────────────────────────────────────────────────────
    # Recording & publishing
    # ─────────────────────────────────────────────────────────────────────

    def _record(self, result: AlignmentCycleResult) -> None:
        with self._lock:
            self._cycles_run += 1
            if result.lighthouse_cleared:
                self._lighthouse_cleared_count += 1
            if result.errors:
                self._errors += 1
            self._last_result = result
            self._history.append(result)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def _publish(self, result: AlignmentCycleResult) -> None:
        if not self._thought_bus:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            payload = result.to_dict()
            self._thought_bus.publish(Thought(
                source="pillar.alignment",
                topic="pillar.alignment",
                payload=payload,
            ))
            if result.lighthouse_cleared:
                self._thought_bus.publish(Thought(
                    source="pillar.alignment",
                    topic="pillar.lighthouse.cleared",
                    payload=payload,
                ))
        except Exception as e:
            logger.debug("Publish failed: %s", e)

    # ─────────────────────────────────────────────────────────────────────
    # Introspection
    # ─────────────────────────────────────────────────────────────────────

    def get_last_result(self) -> Optional[AlignmentCycleResult]:
        with self._lock:
            return self._last_result

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [r.to_dict() for r in self._history[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            last = self._last_result
            return {
                "pillar_count": len(self._pillars),
                "pillars": list(self._pillars.keys()),
                "cycles_run": self._cycles_run,
                "lighthouse_cleared_count": self._lighthouse_cleared_count,
                "lighthouse_clear_rate": (
                    self._lighthouse_cleared_count / self._cycles_run if self._cycles_run > 0 else 0.0
                ),
                "errors": self._errors,
                "uptime_s": time.time() - self._start_time,
                "last_alignment_score": last.alignment_score if last else None,
                "last_signal": last.consensus_signal if last else None,
                "last_lighthouse": last.lighthouse_cleared if last else None,
                "fundamental_hz": self.config.fundamental_hz,
                "lighthouse_threshold": self.config.lighthouse_threshold,
            }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


_instance: Optional[PillarAlignment] = None
_instance_lock = threading.Lock()


def get_pillar_alignment(config: Optional[AlignmentConfig] = None) -> PillarAlignment:
    """Get or create the singleton PillarAlignment."""
    global _instance
    with _instance_lock:
        if _instance is None:
            # Don't auto-load if no config provided — caller decides
            cfg = config or AlignmentConfig(auto_load_pillars=False)
            _instance = PillarAlignment(cfg)
        return _instance
