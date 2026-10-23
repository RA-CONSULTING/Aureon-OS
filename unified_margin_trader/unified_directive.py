"""
UnifiedHarmonicDirective — The Master Directive
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The final mile of alignment: assembles a single MasterDirective from every
sovereign layer of the Aureon system:

  ┌──────────────────────────────────────────────────────────┐
  │                  UnifiedHarmonicDirective                 │
  │                                                           │
  │   Pillars (6)  +  Love Stream Λ(t)  +  Queen Γ  +  Miner  │
  │        │                │                 │         │     │
  │        ▼                ▼                 ▼         ▼     │
  │      signal         standing wave     macro Γ    council  │
  │   consensus          intensity        coherence    verdict │
  │        └────────────────┴────────────────┴────────┘       │
  │                         │                                  │
  │                         ▼                                  │
  │                 MasterDirective                            │
  │           signal · confidence · γ · reasoning              │
  └──────────────────────────────────────────────────────────┘

The MasterDirective is the single source of truth when the Lighthouse burns.
It is published on the ThoughtBus as 'aureon.master.directive' and consumed
by the execution layer when confidence × Γ exceeds the Lighthouse threshold.

If any layer is unavailable, the directive degrades gracefully — each layer
contributes what it can, the final Γ reflects the weakest link.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aureon.alignment.harmonic_resonance import (
    LIGHTHOUSE_THRESHOLD,
    FUNDAMENTAL_HZ,
    geometric_mean,
)
from aureon.alignment.pillar_alignment import (
    PillarAlignment,
    AlignmentCycleResult,
)

logger = logging.getLogger("aureon.alignment.unified")


# ─────────────────────────────────────────────────────────────────────────────
# MasterDirective
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MasterDirective:
    """The unified signal from the entire Aureon stack."""

    directive_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)

    # The verdict
    signal: str = "NEUTRAL"                    # BUY | SELL | NEUTRAL | HOLD
    confidence: float = 0.0                    # [0, 1]
    gamma: float = 0.0                         # the ruling coherence
    lighthouse_cleared: bool = False           # Γ > 0.945

    # The layers (each [0, 1] contribution)
    pillar_alignment_score: float = 0.0
    love_stream_coherence: float = 0.0
    queen_coherence: float = 0.0
    miner_confidence: float = 0.0

    # Dominant harmonics
    dominant_frequency_hz: float = FUNDAMENTAL_HZ
    dominant_chakra: str = "love"

    # Context
    contributing_layers: List[str] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "directive_id": self.directive_id,
            "timestamp": self.timestamp,
            "signal": self.signal,
            "confidence": round(self.confidence, 4),
            "gamma": round(self.gamma, 4),
            "lighthouse_cleared": self.lighthouse_cleared,
            "pillar_alignment_score": round(self.pillar_alignment_score, 4),
            "love_stream_coherence": round(self.love_stream_coherence, 4),
            "queen_coherence": round(self.queen_coherence, 4),
            "miner_confidence": round(self.miner_confidence, 4),
            "dominant_frequency_hz": round(self.dominant_frequency_hz, 2),
            "dominant_chakra": self.dominant_chakra,
            "contributing_layers": self.contributing_layers,
            "reasoning": self.reasoning,
        }


# ─────────────────────────────────────────────────────────────────────────────
# UnifiedHarmonicDirective
# ─────────────────────────────────────────────────────────────────────────────


class UnifiedHarmonicDirective:
    """
    Assembles the MasterDirective from pillars + love stream + Queen + Miner.
    """

    def __init__(
        self,
        pillar_alignment: Optional[PillarAlignment] = None,
        auto_wire: bool = True,
    ):
        self.pillars = pillar_alignment
        self._love_stream = None
        self._queen_bridge = None
        self._miner_bridge = None
        self._thought_bus = None
        self._lock = threading.RLock()

        # Metrics
        self._directives_issued = 0
        self._lighthouse_directives = 0
        self._history: List[MasterDirective] = []
        self._max_history = 200

        if auto_wire:
            self._auto_wire()

    def _auto_wire(self) -> None:
        # PillarAlignment
        if self.pillars is None:
            try:
                from aureon.alignment.pillar_alignment import get_pillar_alignment
                self.pillars = get_pillar_alignment()
            except Exception:
                pass

        # Love stream (from swarm motion hive singleton if alive)
        try:
            from aureon.swarm_motion.swarm_hive import _hive_instance
            if _hive_instance is not None and _hive_instance._love_stream is not None:
                self._love_stream = _hive_instance._love_stream
        except Exception:
            pass

        # Queen bridge
        try:
            from aureon.queen.queen_inhouse_ai_bridge import get_queen_ai_bridge
            self._queen_bridge = get_queen_ai_bridge()
        except Exception:
            pass

        # Miner bridge
        try:
            from aureon.miner.miner_inhouse_ai_bridge import get_miner_ai_bridge
            self._miner_bridge = get_miner_ai_bridge()
        except Exception:
            pass

        # ThoughtBus
        try:
            from aureon.core.aureon_thought_bus import ThoughtBus
            self._thought_bus = ThoughtBus()
        except Exception:
            pass

    def set_love_stream(self, stream: Any) -> None:
        self._love_stream = stream

    # ─────────────────────────────────────────────────────────────────────
    # Layer extraction
    # ─────────────────────────────────────────────────────────────────────

    def _pillar_contribution(
        self,
        context: Dict[str, Any],
        use_synthetic: bool = False,
        synthetic_signals: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[AlignmentCycleResult]:
        if self.pillars is None:
            return None
        try:
            if use_synthetic:
                return self.pillars.run_synthetic_cycle(signals=synthetic_signals)
            return self.pillars.run_cycle(context=context)
        except Exception as e:
            logger.debug("Pillar contribution failed: %s", e)
            return None

    def _try_pickup_love_stream(self) -> None:
        """
        S04: Retry love-stream auto-discovery. The swarm hive may have
        been built AFTER the directive was constructed, so we re-probe
        on every assemble() call when _love_stream is still None.
        """
        if self._love_stream is not None:
            return
        try:
            from aureon.swarm_motion.swarm_hive import _hive_instance
            if _hive_instance is not None and _hive_instance._love_stream is not None:
                self._love_stream = _hive_instance._love_stream
        except Exception:
            pass

    def _love_stream_contribution(self) -> Dict[str, Any]:
        self._try_pickup_love_stream()
        if self._love_stream is None:
            return {"available": False, "coherence": 0.0, "lambda_t": 0.0,
                    "dominant_chakra": "love", "dominant_frequency_hz": FUNDAMENTAL_HZ}
        try:
            sample = self._love_stream.get_last_sample()
            if sample is None:
                sample = self._love_stream.evaluate()
            return {
                "available": True,
                "coherence": float(sample.gamma_coherence),
                "lambda_t": float(sample.lambda_t),
                "standing_wave": float(sample.standing_wave_intensity),
                "dominant_chakra": sample.dominant_chakra,
                "dominant_frequency_hz": sample.dominant_frequency_hz,
            }
        except Exception as e:
            logger.debug("Love stream contribution failed: %s", e)
            return {"available": False, "coherence": 0.0, "lambda_t": 0.0,
                    "dominant_chakra": "love", "dominant_frequency_hz": FUNDAMENTAL_HZ}

    def _queen_contribution(self) -> Dict[str, Any]:
        if self._queen_bridge is None or not getattr(self._queen_bridge, "is_alive", False):
            return {"available": False, "coherence": 0.0}
        try:
            status = self._queen_bridge.get_status()
            last_insight = status.get("last_insight") or {}
            coherence = float(last_insight.get("confidence", 0.5))
            return {"available": True, "coherence": coherence, "status": status}
        except Exception:
            return {"available": False, "coherence": 0.0}

    def _miner_contribution(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self._miner_bridge is None or not getattr(self._miner_bridge, "is_alive", False):
            return {"available": False, "confidence": 0.0, "verdict": "NEUTRAL"}
        try:
            market_data = {
                "fear_greed": context.get("fear_greed", 50),
                "btc_price": context.get("btc_price", 0),
                "btc_dominance": context.get("btc_dominance", 50),
            }
            # Use synthesise_council_verdict if we have votes, else enhance_skeptical
            votes = context.get("advisor_votes")
            if votes:
                insight = self._miner_bridge.synthesise_council_verdict(
                    market_data=market_data, advisor_votes=votes,
                )
            else:
                insight = self._miner_bridge.enhance_skeptical_analysis(
                    market_data=market_data,
                )
            return {
                "available": True,
                "confidence": float(insight.confidence),
                "verdict": insight.verdict,
                "coherence": float(insight.coherence),
            }
        except Exception as e:
            logger.debug("Miner contribution failed: %s", e)
            return {"available": False, "confidence": 0.0, "verdict": "NEUTRAL"}

    # ─────────────────────────────────────────────────────────────────────
    # Assemble the directive
    # ─────────────────────────────────────────────────────────────────────

    def assemble(
        self,
        context: Optional[Dict[str, Any]] = None,
        use_synthetic_pillars: bool = False,
        synthetic_pillar_signals: Optional[List[Dict[str, Any]]] = None,
    ) -> MasterDirective:
        """
        Assemble one MasterDirective from every available layer.
        """
        ctx = dict(context or {})
        directive = MasterDirective()

        contributing: List[str] = []

        # 1. Pillars
        pillar_result = self._pillar_contribution(
            ctx,
            use_synthetic=use_synthetic_pillars,
            synthetic_signals=synthetic_pillar_signals,
        )
        if pillar_result is not None:
            directive.pillar_alignment_score = pillar_result.alignment_score
            contributing.append("pillars")
            # Pillar signal is the default signal
            directive.signal = pillar_result.consensus_signal
            # Capture dominant chakra from pillar frequency if nothing else
            directive.dominant_frequency_hz = pillar_result.mean_frequency_hz or FUNDAMENTAL_HZ

        # 2. Love stream
        love = self._love_stream_contribution()
        if love.get("available"):
            directive.love_stream_coherence = love["coherence"]
            contributing.append("love_stream")
            directive.dominant_chakra = love.get("dominant_chakra", directive.dominant_chakra)
            if love.get("dominant_frequency_hz"):
                directive.dominant_frequency_hz = float(love["dominant_frequency_hz"])

        # 3. Queen
        queen = self._queen_contribution()
        if queen.get("available"):
            directive.queen_coherence = queen["coherence"]
            contributing.append("queen")

        # 4. Miner
        miner = self._miner_contribution(ctx)
        if miner.get("available"):
            directive.miner_confidence = miner["confidence"]
            contributing.append("miner")
            # If miner strongly disagrees with pillars, caveat the signal
            miner_verdict = str(miner.get("verdict", "NEUTRAL")).upper()
            if miner_verdict == "SUSPICIOUS":
                # Downgrade: the miner smells manipulation
                if directive.signal in ("BUY", "SELL"):
                    directive.signal = "NEUTRAL"

        # ── Compute unified γ as the geometric mean of contributing layers ──
        layer_scores: List[float] = []
        if pillar_result is not None:
            layer_scores.append(directive.pillar_alignment_score)
        if love.get("available"):
            layer_scores.append(directive.love_stream_coherence)
        if queen.get("available"):
            layer_scores.append(directive.queen_coherence)
        if miner.get("available"):
            layer_scores.append(directive.miner_confidence)

        if layer_scores:
            directive.gamma = geometric_mean(layer_scores)
        else:
            directive.gamma = 0.0

        directive.lighthouse_cleared = directive.gamma > LIGHTHOUSE_THRESHOLD

        # Overall confidence = pillar consensus × layer agreement
        if pillar_result is not None:
            directive.confidence = pillar_result.consensus_confidence * directive.gamma
        else:
            directive.confidence = directive.gamma

        directive.contributing_layers = contributing

        # Reasoning summary
        parts = [
            f"pillars={directive.pillar_alignment_score:.3f}",
            f"love={directive.love_stream_coherence:.3f}",
            f"queen={directive.queen_coherence:.3f}",
            f"miner={directive.miner_confidence:.3f}",
            f"→ γ={directive.gamma:.4f}",
            f"({'LIGHTHOUSE' if directive.lighthouse_cleared else 'below threshold'})",
            f"signal={directive.signal}",
            f"@ {directive.dominant_frequency_hz:.0f}Hz ({directive.dominant_chakra})",
        ]
        directive.reasoning = " | ".join(parts)

        # Record
        self._record(directive)
        self._publish(directive)
        return directive

    def _record(self, directive: MasterDirective) -> None:
        with self._lock:
            self._directives_issued += 1
            if directive.lighthouse_cleared:
                self._lighthouse_directives += 1
            self._history.append(directive)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]

    def _publish(self, directive: MasterDirective) -> None:
        if not self._thought_bus:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            payload = directive.to_dict()
            self._thought_bus.publish(Thought(
                source="aureon.unified",
                topic="aureon.master.directive",
                payload=payload,
            ))
            if directive.lighthouse_cleared:
                self._thought_bus.publish(Thought(
                    source="aureon.unified",
                    topic="aureon.lighthouse.burns",
                    payload=payload,
                ))
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Introspection
    # ─────────────────────────────────────────────────────────────────────

    def get_last_directive(self) -> Optional[MasterDirective]:
        with self._lock:
            return self._history[-1] if self._history else None

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            return [d.to_dict() for d in self._history[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            last = self._history[-1] if self._history else None
            return {
                "directives_issued": self._directives_issued,
                "lighthouse_directives": self._lighthouse_directives,
                "lighthouse_rate": (
                    self._lighthouse_directives / self._directives_issued if self._directives_issued > 0 else 0.0
                ),
                "layers_wired": {
                    "pillars": self.pillars is not None,
                    "love_stream": self._love_stream is not None,
                    "queen": self._queen_bridge is not None and getattr(self._queen_bridge, "is_alive", False),
                    "miner": self._miner_bridge is not None and getattr(self._miner_bridge, "is_alive", False),
                },
                "last_directive": last.to_dict() if last else None,
            }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton
# ─────────────────────────────────────────────────────────────────────────────


_directive_instance: Optional[UnifiedHarmonicDirective] = None
_directive_lock = threading.Lock()


def get_unified_directive() -> UnifiedHarmonicDirective:
    """Get or create the singleton UnifiedHarmonicDirective."""
    global _directive_instance
    with _directive_lock:
        if _directive_instance is None:
            _directive_instance = UnifiedHarmonicDirective()
        return _directive_instance
