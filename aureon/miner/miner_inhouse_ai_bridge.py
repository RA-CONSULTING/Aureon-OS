"""
Miner In-House AI Bridge — Mining Consciousness Integration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Wires the sovereign in-house AI framework directly into the Aureon Miner
(MinerBrain + QuantumProcessingBrain) at 5 integration points:

  1. SKEPTICAL ANALYSIS — enhance BS detection with AI pattern recognition
  2. TRUTH COUNCIL      — synthesise the 5-advisor debate with AI reasoning
  3. WISDOM SYNTHESIS   — blend 7 civilisations into a coherent directive
  4. QUANTUM WEIGHTING  — adapt the 8-component weights dynamically
  5. MINER REASONING    — general purpose reasoning over full mining state

The bridge mirrors the QueenAIBridge architecture:
  - Singleton pattern via get_miner_ai_bridge()
  - Auto-wires to ThoughtBus for cross-system awareness
  - Graceful degradation when adapter unavailable
  - Publishes 'miner.ai.insight' events for the trading loop to consume

Gary Leckey / Aureon Institute — 2026
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("aureon.miner.ai_bridge")

# ─────────────────────────────────────────────────────────────────────────────
# Lazy adapter loader (graceful degradation)
# ─────────────────────────────────────────────────────────────────────────────

_adapter = None
_adapter_loaded = False


def _ensure_adapter():
    """Load the in-house AI adapter once."""
    global _adapter, _adapter_loaded
    if _adapter_loaded:
        return _adapter
    _adapter_loaded = True
    try:
        from aureon.inhouse_ai.llm_adapter import AureonHybridAdapter, AureonBrainAdapter
        try:
            from aureon.integrations.ollama import OllamaModelSwitchboard

            _adapter, _selection = OllamaModelSwitchboard().hybrid_adapter_for("fast")
            if not _adapter.health_check():
                _adapter = AureonBrainAdapter()
        except Exception:
            _adapter = AureonBrainAdapter()
        logger.info("Miner AI Bridge: %s loaded", type(_adapter).__name__)
    except Exception as e:
        logger.warning("Miner AI Bridge: adapter unavailable — %s", e)
        _adapter = None
    return _adapter


# ─────────────────────────────────────────────────────────────────────────────
# Insight dataclass
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MinerAIInsight:
    """An AI-generated insight for the Miner."""
    category: str = ""                    # skeptical | council | wisdom | quantum | general
    verdict: str = "NEUTRAL"              # BUY | SELL | NEUTRAL | SUSPICIOUS | OPPORTUNITY
    confidence: float = 0.5
    coherence: float = 0.5
    reasoning: str = ""
    red_flags: List[str] = field(default_factory=list)
    green_flags: List[str] = field(default_factory=list)
    suggested_weights: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "coherence": self.coherence,
            "reasoning": self.reasoning,
            "red_flags": self.red_flags,
            "green_flags": self.green_flags,
            "suggested_weights": self.suggested_weights,
            "timestamp": self.timestamp,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Miner AI Bridge
# ─────────────────────────────────────────────────────────────────────────────


class MinerAIBridge:
    """
    Bridges the in-house AI framework into the Aureon Miner subsystem.

    Usage:
        bridge = get_miner_ai_bridge()
        bridge.start()

        # Enhance the SkepticalAnalyzer
        insights = bridge.enhance_skeptical_analysis(market_data)

        # Synthesise the Truth Council verdict
        verdict = bridge.synthesise_council_verdict(market_data, advisor_votes)

        # Enhance wisdom synthesis
        directive = bridge.enhance_wisdom_synthesis(civilization_signals, quantum_context)

        # Suggest quantum weights
        weights = bridge.suggest_quantum_weights(subsystem_states)

        # General reasoning
        answer = bridge.reason_about_mining_state(full_context)
    """

    def __init__(self):
        self._adapter = _ensure_adapter()
        self._thought_bus = None
        self._running = False
        self._lock = threading.Lock()

        # Metrics
        self._skeptical_calls = 0
        self._council_calls = 0
        self._wisdom_calls = 0
        self._quantum_calls = 0
        self._general_calls = 0
        self._errors = 0
        self._start_time: Optional[float] = None

        # Cache
        self._last_insight: Optional[MinerAIInsight] = None
        self._insight_history: List[MinerAIInsight] = []
        self._max_history = 100

        # Wire ThoughtBus
        self._wire_thought_bus()

    def _wire_thought_bus(self):
        """Connect to the ThoughtBus for real-time insight publishing."""
        try:
            from aureon.core.aureon_thought_bus import ThoughtBus
            self._thought_bus = ThoughtBus()
            logger.info("Miner AI Bridge wired to ThoughtBus")
        except Exception as e:
            logger.debug("ThoughtBus not available for Miner AI Bridge: %s", e)

    @property
    def is_alive(self) -> bool:
        return self._adapter is not None

    def start(self):
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        logger.info(
            "Miner AI Bridge started — adapter: %s",
            type(self._adapter).__name__ if self._adapter else "None",
        )

    def stop(self):
        self._running = False

    # ─────────────────────────────────────────────────────────────────────
    # 1. SKEPTICAL ANALYSIS — enhance BS detection
    # ─────────────────────────────────────────────────────────────────────

    def enhance_skeptical_analysis(
        self,
        market_data: Dict[str, Any],
        existing_red_flags: Optional[List[str]] = None,
        existing_green_flags: Optional[List[str]] = None,
    ) -> MinerAIInsight:
        """
        Enhance the SkepticalAnalyzer with AI-powered pattern recognition.

        Called from MinerBrain.run_cycle() Phase 3 to add AI reasoning
        about market anomalies and manipulation patterns.
        """
        self._skeptical_calls += 1

        if not self._adapter:
            return MinerAIInsight(
                category="skeptical",
                verdict="NEUTRAL",
                confidence=0.5,
                reasoning="Adapter unavailable",
            )

        system_prompt = (
            "You are the Miner's skeptical analyzer — trained to detect market "
            "manipulation, suspicious patterns, and emotional noise. "
            "Analyse the market data and return a JSON block with keys: "
            "verdict (SUSPICIOUS|CLEAN|INCONCLUSIVE), confidence (0-1), "
            "red_flags (list of strings), green_flags (list of strings), "
            "reasoning (brief explanation)."
        )

        context_parts = []
        if market_data.get("fear_greed") is not None:
            fg = market_data["fear_greed"]
            context_parts.append(f"Fear/Greed: {fg}")
            if fg < 20 or fg > 80:
                context_parts.append("(extreme sentiment)")
        if market_data.get("btc_dominance") is not None:
            context_parts.append(f"BTC dominance: {market_data['btc_dominance']:.1f}%")
        if market_data.get("mcap_change") is not None:
            context_parts.append(f"Market cap change: {market_data['mcap_change']:+.2f}%")
        if existing_red_flags:
            context_parts.append(f"Existing red flags: {existing_red_flags[:3]}")
        if existing_green_flags:
            context_parts.append(f"Existing green flags: {existing_green_flags[:3]}")

        message = (
            f"Market state: {', '.join(context_parts) or 'insufficient data'}\n"
            "Detect any manipulation or emotional traps."
        )

        try:
            response = self._adapter.prompt(
                messages=[{"role": "user", "content": message}],
                system=system_prompt,
                max_tokens=512,
            )
            insight = self._parse_skeptical_response(response.text)
            self._record_insight(insight)
            return insight
        except Exception as e:
            self._errors += 1
            logger.debug("Skeptical enhancement failed: %s", e)
            return MinerAIInsight(
                category="skeptical",
                verdict="NEUTRAL",
                confidence=0.5,
                reasoning=f"Error: {e}",
            )

    def _parse_skeptical_response(self, text: str) -> MinerAIInsight:
        insight = MinerAIInsight(category="skeptical", reasoning=text)
        try:
            match = re.search(r"\{[^{}]*\"verdict\"\s*:[^{}]*\}", text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                insight.verdict = str(data.get("verdict", "NEUTRAL")).upper()
                insight.confidence = float(data.get("confidence", 0.5))
                insight.red_flags = list(data.get("red_flags", []))[:10]
                insight.green_flags = list(data.get("green_flags", []))[:10]
                insight.reasoning = str(data.get("reasoning", text))[:500]
        except Exception:
            # Heuristic fallback
            upper = text.upper()
            if "SUSPICIOUS" in upper or "MANIPULATION" in upper:
                insight.verdict = "SUSPICIOUS"
                insight.confidence = 0.65
            elif "CLEAN" in upper or "ORGANIC" in upper:
                insight.verdict = "CLEAN"
                insight.confidence = 0.65
        return insight

    # ─────────────────────────────────────────────────────────────────────
    # 2. TRUTH COUNCIL — synthesise advisor debate
    # ─────────────────────────────────────────────────────────────────────

    def synthesise_council_verdict(
        self,
        market_data: Dict[str, Any],
        advisor_votes: List[Dict[str, Any]],
    ) -> MinerAIInsight:
        """
        Synthesise the Truth Council's 5 advisor votes into an AI-weighted verdict.

        Called from TruthCouncil.convene() to enhance the rule-based consensus
        with AI reasoning about the combined signal.
        """
        self._council_calls += 1

        if not self._adapter:
            return MinerAIInsight(
                category="council",
                verdict="INCONCLUSIVE",
                confidence=0.5,
                reasoning="Adapter unavailable",
            )

        system_prompt = (
            "You are the Miner's Truth Council synthesiser. Read the advisor votes "
            "and market state, then produce a unified verdict. "
            "Return JSON: {\"verdict\": \"BUY|SELL|NEUTRAL|SUSPICIOUS|OPPORTUNITY\", "
            "\"confidence\": 0-1, \"coherence\": 0-1, \"reasoning\": \"explanation\"}"
        )

        votes_summary = []
        for v in advisor_votes[:8]:  # cap at 8
            votes_summary.append(
                f"{v.get('advisor', 'Unknown')} ({v.get('verdict', '?')}, "
                f"conf={v.get('confidence', 0):.2f}): {str(v.get('reasoning', ''))[:100]}"
            )

        message = (
            f"Market data: {json.dumps({k: v for k, v in market_data.items() if not isinstance(v, (list, dict))}, default=str)[:500]}\n"
            f"Advisor votes:\n" + "\n".join(votes_summary) + "\n"
            "Synthesise the unified verdict."
        )

        try:
            response = self._adapter.prompt(
                messages=[{"role": "user", "content": message}],
                system=system_prompt,
                max_tokens=512,
            )
            insight = self._parse_council_response(response.text)
            self._record_insight(insight)
            self._publish_insight(insight)
            return insight
        except Exception as e:
            self._errors += 1
            return MinerAIInsight(
                category="council",
                verdict="INCONCLUSIVE",
                confidence=0.5,
                reasoning=f"Error: {e}",
            )

    def _parse_council_response(self, text: str) -> MinerAIInsight:
        insight = MinerAIInsight(category="council", reasoning=text)
        try:
            match = re.search(r"\{[^{}]*\"verdict\"\s*:[^{}]*\}", text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                insight.verdict = str(data.get("verdict", "NEUTRAL")).upper()
                insight.confidence = float(data.get("confidence", 0.5))
                insight.coherence = float(data.get("coherence", 0.5))
                insight.reasoning = str(data.get("reasoning", text))[:500]
        except Exception:
            upper = text.upper()
            if "BUY" in upper and "SELL" not in upper:
                insight.verdict = "BUY"
            elif "SELL" in upper and "BUY" not in upper:
                insight.verdict = "SELL"
            elif "OPPORTUNITY" in upper:
                insight.verdict = "OPPORTUNITY"
            elif "SUSPICIOUS" in upper:
                insight.verdict = "SUSPICIOUS"
        return insight

    # ─────────────────────────────────────────────────────────────────────
    # 3. WISDOM SYNTHESIS — blend 7 civilisations
    # ─────────────────────────────────────────────────────────────────────

    def enhance_wisdom_synthesis(
        self,
        civilization_signals: Dict[str, Any],
        quantum_context: Optional[Dict[str, Any]] = None,
    ) -> MinerAIInsight:
        """
        Blend the 7 civilisations' wisdom signals into a coherent directive.

        Called after MinerBrain Phase 7 wisdom gathering to produce a unified
        directive for the next mining cycle.
        """
        self._wisdom_calls += 1

        if not self._adapter:
            return MinerAIInsight(
                category="wisdom",
                verdict="NEUTRAL",
                confidence=0.5,
                reasoning="Adapter unavailable",
            )

        system_prompt = (
            "You are the Miner's Wisdom Cognition Engine. Blend signals from "
            "ancient civilisations (Egyptian Ma'at, Pythagorean harmony, Celtic "
            "frequencies, Aztec cycles, Mogollon patterns, Plantagenet strategy, "
            "Strategic Warfare) into a single directive. Return JSON: "
            "{\"verdict\": \"BUY|SELL|NEUTRAL|OPPORTUNITY|PROTECT_CAPITAL\", "
            "\"confidence\": 0-1, \"coherence\": 0-1, \"reasoning\": \"synthesis\"}"
        )

        civ_parts = []
        for name, signal in civilization_signals.items():
            if isinstance(signal, dict):
                civ_parts.append(f"{name}: {signal.get('verdict', '?')} (conf={signal.get('confidence', 0):.2f})")
            else:
                civ_parts.append(f"{name}: {signal}")

        ctx_parts = []
        if quantum_context:
            ctx_parts.append(f"quantum coherence Ψ: {quantum_context.get('quantum_coherence', 0.5):.3f}")
            ctx_parts.append(f"planetary gamma Γ: {quantum_context.get('planetary_gamma', 0.5):.3f}")
            ctx_parts.append(f"lighthouse: {quantum_context.get('is_lighthouse', False)}")

        message = (
            f"Civilisation signals: {'; '.join(civ_parts) or 'none'}\n"
            f"Quantum context: {', '.join(ctx_parts) or 'none'}\n"
            "Synthesise the unified wisdom directive."
        )

        try:
            response = self._adapter.prompt(
                messages=[{"role": "user", "content": message}],
                system=system_prompt,
                max_tokens=512,
            )
            insight = self._parse_council_response(response.text)
            insight.category = "wisdom"
            self._record_insight(insight)
            self._publish_insight(insight)
            return insight
        except Exception as e:
            self._errors += 1
            return MinerAIInsight(
                category="wisdom",
                verdict="NEUTRAL",
                confidence=0.5,
                reasoning=f"Error: {e}",
            )

    # ─────────────────────────────────────────────────────────────────────
    # 4. QUANTUM WEIGHTING — adapt the 8-component weights
    # ─────────────────────────────────────────────────────────────────────

    def suggest_quantum_weights(
        self,
        subsystem_states: Dict[str, float],
        current_weights: Optional[Dict[str, float]] = None,
    ) -> MinerAIInsight:
        """
        Suggest adaptive weights for the QuantumProcessingBrain's 8 components.

        Given the current state of each subsystem (probability, planetary,
        harmonic, temporal, casimir, coherence, memory, diamond), use AI
        reasoning to suggest weight adjustments.
        """
        self._quantum_calls += 1

        insight = MinerAIInsight(category="quantum")

        if not self._adapter:
            insight.reasoning = "Adapter unavailable"
            insight.suggested_weights = current_weights or {}
            return insight

        # Default weights (from QuantumProcessingBrain)
        default_weights = {
            "probability": 0.22,
            "planetary": 0.18,
            "harmonic": 0.13,
            "temporal": 0.12,
            "casimir": 0.08,
            "coherence": 0.10,
            "memory": 0.05,
            "diamond": 0.12,
        }
        base_weights = current_weights or default_weights

        # Rule-based weight adjustment (deterministic, fast, doesn't require LLM)
        suggested = dict(base_weights)

        # If planetary gamma is strong, boost planetary weight
        gamma = subsystem_states.get("planetary_gamma", 0.5)
        if gamma > 0.7:
            suggested["planetary"] = min(0.30, base_weights["planetary"] * 1.3)
        elif gamma < 0.3:
            suggested["planetary"] = max(0.08, base_weights["planetary"] * 0.7)

        # If coherence psi is strong, boost coherence weight
        psi = subsystem_states.get("coherence_psi", 0.5)
        if psi > 0.7:
            suggested["coherence"] = min(0.20, base_weights["coherence"] * 1.4)
        elif psi < 0.3:
            suggested["coherence"] = max(0.05, base_weights["coherence"] * 0.7)

        # If probability edge is strong, boost probability
        prob_edge = subsystem_states.get("probability_edge", 0.0)
        if prob_edge > 0.3:
            suggested["probability"] = min(0.35, base_weights["probability"] * 1.3)

        # If lighthouse active, boost diamond (sacred geometry timing)
        if subsystem_states.get("is_lighthouse", False):
            suggested["diamond"] = min(0.25, base_weights["diamond"] * 1.5)
            suggested["temporal"] = min(0.20, base_weights["temporal"] * 1.4)

        # Normalise so weights sum to 1.0
        total = sum(suggested.values())
        if total > 0:
            suggested = {k: round(v / total, 4) for k, v in suggested.items()}

        insight.suggested_weights = suggested
        insight.confidence = 0.75
        insight.coherence = (gamma + psi) / 2
        insight.verdict = "ADAPTED"
        insight.reasoning = (
            f"Adjusted weights based on gamma={gamma:.2f}, psi={psi:.2f}, "
            f"edge={prob_edge:.2f}, lighthouse={subsystem_states.get('is_lighthouse', False)}"
        )

        self._record_insight(insight)
        return insight

    # ─────────────────────────────────────────────────────────────────────
    # 5. GENERAL REASONING — full mining state reasoning
    # ─────────────────────────────────────────────────────────────────────

    def reason_about_mining_state(
        self,
        full_context: Dict[str, Any],
        question: str = "What should the miner prioritise right now?",
    ) -> str:
        """General-purpose reasoning over the full mining state."""
        self._general_calls += 1

        if not self._adapter:
            return "AI adapter not available"

        system_prompt = (
            "You are the Miner's reasoning engine. Given the full mining state, "
            "provide actionable guidance. Be concise and direct."
        )

        # Compact context
        ctx_str = json.dumps(
            {k: v for k, v in full_context.items() if not isinstance(v, (list, dict))},
            default=str,
        )[:1500]

        message = f"Mining state: {ctx_str}\n\nQuestion: {question}"

        try:
            response = self._adapter.prompt(
                messages=[{"role": "user", "content": message}],
                system=system_prompt,
                max_tokens=512,
            )
            return response.text
        except Exception as e:
            self._errors += 1
            return f"Reasoning failed: {e}"

    # ─────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────

    def _record_insight(self, insight: MinerAIInsight):
        with self._lock:
            self._last_insight = insight
            self._insight_history.append(insight)
            if len(self._insight_history) > self._max_history:
                self._insight_history = self._insight_history[-self._max_history:]

    def _publish_insight(self, insight: MinerAIInsight):
        """Publish an insight to the ThoughtBus for cross-system consumption."""
        if not self._thought_bus:
            return
        try:
            from aureon.core.aureon_thought_bus import Thought
            self._thought_bus.publish(Thought(
                source="miner.ai_bridge",
                topic="miner.ai.insight",
                payload=insight.to_dict(),
            ))
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # Status
    # ─────────────────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        return {
            "alive": self.is_alive,
            "adapter": type(self._adapter).__name__ if self._adapter else None,
            "running": self._running,
            "skeptical_calls": self._skeptical_calls,
            "council_calls": self._council_calls,
            "wisdom_calls": self._wisdom_calls,
            "quantum_calls": self._quantum_calls,
            "general_calls": self._general_calls,
            "total_calls": (
                self._skeptical_calls + self._council_calls + self._wisdom_calls
                + self._quantum_calls + self._general_calls
            ),
            "errors": self._errors,
            "uptime_s": time.time() - self._start_time if self._start_time else 0,
            "insight_history_size": len(self._insight_history),
            "last_insight": self._last_insight.to_dict() if self._last_insight else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Singleton accessor
# ─────────────────────────────────────────────────────────────────────────────

_bridge_instance: Optional[MinerAIBridge] = None


def get_miner_ai_bridge() -> MinerAIBridge:
    """Get or create the singleton MinerAIBridge."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MinerAIBridge()
    return _bridge_instance
