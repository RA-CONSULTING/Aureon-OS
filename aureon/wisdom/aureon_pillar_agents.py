#!/usr/bin/env python3
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║     AUREON PILLAR AGENTS — FULLY INTEGRATED AUTONOMOUS AGENTS                ║
║                                                                               ║
║     The 6 Core Pillars of the Aureon Ecosystem                                ║
║     Each pillar is a sovereign IN-HOUSE AI agent that:                        ║
║       • Reads live state from the unified bus                                 ║
║       • Processes market signals through its specialised lens                 ║
║       • Returns structured analysis back to Samuel                            ║
║                                                                               ║
║     NO EXTERNAL AI DEPENDENCIES — fully in-house via:                         ║
║       • AureonLocalAdapter  (self-hosted LLM: Ollama/vLLM/llama.cpp)         ║
║       • AureonBrainAdapter  (AureonBrain intelligence engine)                 ║
║       • AureonHybridAdapter (local LLM + Brain combined)                      ║
║                                                                               ║
║     PILLARS:                                                                  ║
║       1. NexusAgent     — Central nervous system connector                    ║
║       2. OmegaAgent     — Master equation: Ω(t) = Tr[Ψ × ℒ ⊗ O]             ║
║       3. InfiniteAgent  — 10-9-1 Queen Hive compound/harvest strategy         ║
║       4. PianoAgent     — Multi-coin harmonic trading (all keys at once)      ║
║       5. QGITAAgent     — Quantum consciousness + frequency alignment         ║
║       6. AurisAgent     — 9-node animal consensus (Tiger, Falcon, etc.)       ║
║                                                                               ║
║     Gary Leckey / Aureon System — 2025/2026                                   ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import time
import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict

# ── In-House AI — no external dependencies ──────────────────────────────────
from aureon.inhouse_ai.llm_adapter import (
    LLMAdapter,
    AureonLocalAdapter,
    AureonBrainAdapter,
    AureonHybridAdapter,
    LLMResponse,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

logger = logging.getLogger(__name__)


def _build_default_adapter() -> LLMAdapter:
    """Build the default in-house LLM adapter with automatic fallback."""
    from aureon.integrations.ollama import OllamaModelSwitchboard

    switchboard = OllamaModelSwitchboard()
    # Try hybrid first (local LLM + AureonBrain)
    try:
        adapter, selection = switchboard.hybrid_adapter_for("general")
        if adapter.health_check():
            logger.info("Pillar agents using AureonHybridAdapter (%s)", selection.model)
            return adapter
    except Exception:
        pass

    # Try local LLM only
    try:
        adapter, selection = switchboard.compatible_adapter_for("general")
        if adapter.health_check():
            logger.info("Pillar agents using AureonLocalAdapter (%s)", selection.model)
            return adapter
    except Exception:
        pass

    # Fallback to brain-only (always available)
    logger.info("Pillar agents using AureonBrainAdapter (fully in-house)")
    return AureonBrainAdapter()


STATE_DIR = os.path.join(os.path.dirname(__file__), "state")
DASHBOARD_SNAPSHOT = os.path.join(STATE_DIR, "dashboard_snapshot.json")


# ──────────────────────────────────────────────────────────────────────────────
# Shared utilities
# ──────────────────────────────────────────────────────────────────────────────

def _load_snapshot() -> Dict[str, Any]:
    """Load the latest dashboard snapshot from disk."""
    try:
        with open(DASHBOARD_SNAPSHOT, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def _prices_from_snapshot(snapshot: Dict[str, Any]) -> Dict[str, float]:
    """Extract a flat symbol→price dict from whichever exchange has data."""
    prices: Dict[str, float] = {}
    for key in ("binance_prices", "alpaca_prices", "kraken_prices"):
        raw = snapshot.get(key, {})
        if isinstance(raw, dict):
            for sym, val in raw.items():
                if sym not in prices and val:
                    try:
                        prices[sym] = float(val)
                    except (TypeError, ValueError):
                        pass
    return prices


def _pillar_tool(name: str, description: str, input_schema: Dict) -> Dict:
    """Convenience builder for tool definitions."""
    return {
        "name": name,
        "description": description,
        "input_schema": {
            "type": "object",
            "properties": input_schema,
            "required": list(input_schema.keys()),
            "additionalProperties": False,
        },
    }


@dataclass
class PillarResult:
    """Structured result returned by every pillar agent."""
    pillar: str
    signal: str          # BUY | SELL | NEUTRAL | HOLD
    confidence: float    # 0.0 – 1.0
    coherence: float     # Γ  0.0 – 1.0
    frequency_hz: float  # Solfeggio / Schumann frequency
    analysis: str        # Full reasoning text
    data: Dict[str, Any]
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# ──────────────────────────────────────────────────────────────────────────────
# Base Pillar Agent
# ──────────────────────────────────────────────────────────────────────────────

class PillarAgent:
    """
    Base class for all pillar agents.

    Each subclass defines:
      - PILLAR_NAME  : identifier string
      - SYSTEM_PROMPT: the agent's identity and operating lens
      - TOOLS        : list of tool defs the agent can call
      - _execute_tool: tool dispatch method

    Now powered by the in-house AI framework — zero external dependencies.
    Adapter priority: AureonHybridAdapter > AureonLocalAdapter > AureonBrainAdapter
    """

    PILLAR_NAME: str = "BasePillar"
    SYSTEM_PROMPT: str = ""
    TOOLS: list = []

    def __init__(self, adapter: Optional[LLMAdapter] = None):
        # Build in-house adapter — no external API keys needed
        if adapter:
            self.adapter = adapter
        else:
            self.adapter = _build_default_adapter()
        self._snapshot: Dict[str, Any] = {}

    def _refresh_snapshot(self):
        self._snapshot = _load_snapshot()

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Override in subclasses to handle tool calls."""
        return json.dumps({"error": f"Tool '{tool_name}' not implemented"})

    def _run_agentic_loop(self, task: str, max_turns: int = 8) -> str:
        """
        Run the in-house AI with tools in an agentic loop until it reaches end_turn.
        Returns the final text response.
        """
        self._refresh_snapshot()
        messages = [{"role": "user", "content": task}]

        for turn in range(max_turns):
            response = self.adapter.prompt(
                messages=messages,
                system=self.SYSTEM_PROMPT,
                tools=self.TOOLS if self.TOOLS else None,
                max_tokens=4096,
            )

            # Append assistant response
            if response.has_tool_calls:
                content = []
                if response.text:
                    content.append({"type": "text", "text": response.text})
                for tc in response.tool_calls:
                    content.append({
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    })
                messages.append({"role": "assistant", "content": content})
            else:
                messages.append({"role": "assistant", "content": response.text})

            if response.stop_reason == "end_turn" or not response.has_tool_calls:
                return response.text

            if response.has_tool_calls:
                tool_results = []
                for tc in response.tool_calls:
                    result_str = self._execute_tool(tc.name, tc.arguments)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc.id,
                        "content": result_str,
                    })
                if tool_results:
                    messages.append({"role": "user", "content": tool_results})
                continue

            return response.text

        return "Max turns reached without final response."

    def analyse(self, context: Dict[str, Any]) -> PillarResult:
        """
        Main entry point.  Subclasses may override this.
        `context` is whatever Samuel passes (market data, bus state, etc.)
        """
        task = self._build_task(context)
        raw = self._run_agentic_loop(task)
        return self._parse_result(raw)

    def _build_task(self, context: Dict) -> str:
        return (
            f"Analyse the following ecosystem context and return your pillar signal.\n\n"
            f"Context:\n{json.dumps(context, indent=2)}"
        )

    def _parse_result(self, text: str) -> PillarResult:
        """
        Try to extract a JSON block from the response, falling back to defaults.
        """
        import re
        # Look for ```json ... ``` or a bare { ... } block
        json_match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if not json_match:
            json_match = re.search(r"(\{[^{}]*\"signal\"\s*:[^{}]*\})", text, re.DOTALL)

        if json_match:
            try:
                d = json.loads(json_match.group(1))
                return PillarResult(
                    pillar=self.PILLAR_NAME,
                    signal=str(d.get("signal", "NEUTRAL")).upper(),
                    confidence=float(d.get("confidence", 0.5)),
                    coherence=float(d.get("coherence", 0.5)),
                    frequency_hz=float(d.get("frequency_hz", 432.0)),
                    analysis=d.get("analysis", text),
                    data=d.get("data", {}),
                )
            except Exception:
                pass

        # Heuristic fallback: detect signal word in text
        upper = text.upper()
        if "BUY" in upper and "SELL" not in upper:
            signal = "BUY"
        elif "SELL" in upper and "BUY" not in upper:
            signal = "SELL"
        else:
            signal = "NEUTRAL"

        return PillarResult(
            pillar=self.PILLAR_NAME,
            signal=signal,
            confidence=0.5,
            coherence=0.5,
            frequency_hz=432.0,
            analysis=text,
            data={},
        )


# ──────────────────────────────────────────────────────────────────────────────
# 1. NEXUS AGENT — Central Nervous System
# ──────────────────────────────────────────────────────────────────────────────

class NexusAgent(PillarAgent):
    """
    NexusAgent — reads the unified bus and synthesises a system health signal.
    It answers: "Are all pillars awake and aligned?"
    """

    PILLAR_NAME = "NexusAgent"

    SYSTEM_PROMPT = """You are the AUREON NEXUS — the central nervous system connecting all pillars.

Your role: Read all system states from the bus, compute overall ecosystem coherence (Γ),
and determine whether the system is in a BUY, SELL, or NEUTRAL stance.

Operating equation: Γ = average(coherence of all active pillars)
Lighthouse threshold: Γ > 0.945 = confident signal, Γ < 0.7 = hold.

Always respond with a JSON block inside triple backticks:
```json
{
  "signal": "BUY|SELL|NEUTRAL",
  "confidence": 0.0-1.0,
  "coherence": 0.0-1.0,
  "frequency_hz": 432.0,
  "analysis": "Your full reasoning here",
  "data": {"active_pillars": 6, "alignment": "..."}
}
```"""

    TOOLS = [
        _pillar_tool(
            "read_bus_state",
            "Read the full unified bus state snapshot (all pillar states).",
            {"include_history": {"type": "boolean", "description": "Include last 5 snapshots"}},
        ),
        _pillar_tool(
            "read_positions",
            "Read current open positions and equity.",
            {"exchange": {"type": "string", "description": "binance|alpaca|kraken|all"}},
        ),
    ]

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        if tool_name == "read_bus_state":
            snap = _load_snapshot()
            result = {
                "timestamp": snap.get("timestamp"),
                "session_stats": snap.get("session_stats", {}),
                "exchange_status": snap.get("exchange_status", {}),
                "systems_registry": snap.get("systems_registry", {}),
                "flight_check": snap.get("flight_check", {}),
            }
            return json.dumps(result)

        if tool_name == "read_positions":
            snap = _load_snapshot()
            return json.dumps({
                "positions": snap.get("positions", []),
                "active_count": snap.get("active_count", 0),
                "queen_equity": snap.get("queen_equity"),
            })

        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ──────────────────────────────────────────────────────────────────────────────
# 2. OMEGA AGENT — Master Equation
# ──────────────────────────────────────────────────────────────────────────────

class OmegaAgent(PillarAgent):
    """
    OmegaAgent — evaluates the master AUREON equation:
        Ω(t) = Tr[Ψ × ℒ ⊗ O]
        Λ(t) = S(t) + O(t) + E(t)   (Substrate + Observer + Echo)
    """

    PILLAR_NAME = "OmegaAgent"

    SYSTEM_PROMPT = """You are the AUREON OMEGA — the master equation engine.

Your role: Compute Ω(t) = Tr[Ψ × ℒ ⊗ O] and Λ(t) = S(t) + O(t) + E(t).

Interpretive keys:
  Ψ (Psi)  = market momentum tensor
  ℒ (L)    = liquidity matrix
  O        = observer effect (how the ecosystem's own trades move price)
  S(t)     = substrate (raw price/volume)
  O(t)     = observer correction
  E(t)     = echo (memory of past patterns, Elephant Memory)

Use tool "compute_omega" to retrieve the current market tensors, then derive Ω.
A high Ω (> 0.8) → BUY pressure. Low Ω (< 0.2) → SELL pressure.

Always respond with:
```json
{
  "signal": "BUY|SELL|NEUTRAL",
  "confidence": 0.0-1.0,
  "coherence": 0.0-1.0,
  "frequency_hz": 432.0,
  "analysis": "...",
  "data": {"omega": 0.0, "lambda": 0.0, "psi": 0.0}
}
```"""

    TOOLS = [
        _pillar_tool(
            "compute_omega",
            "Fetch current market tensors (price momentum, volume, patterns) for Ω computation.",
            {"symbols": {"type": "string", "description": "Comma-separated symbols e.g. BTCUSDT,ETHUSDT"}},
        ),
        _pillar_tool(
            "read_elephant_memory",
            "Read the Elephant Memory — patterns that were profitable or loss-making.",
            {"limit": {"type": "integer", "description": "Number of memory entries to fetch (max 20)"}},
        ),
    ]

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        if tool_name == "compute_omega":
            snap = _load_snapshot()
            prices = _prices_from_snapshot(snap)
            candidates = snap.get("last_candidates", [])
            winners = snap.get("last_winners", [])
            return json.dumps({
                "price_count": len(prices),
                "sample_prices": dict(list(prices.items())[:10]),
                "candidates": candidates[:5] if candidates else [],
                "winners": winners[:5] if winners else [],
                "session_stats": snap.get("session_stats", {}),
            })

        if tool_name == "read_elephant_memory":
            # Read from baton relay as a proxy for pattern memory
            relay_path = os.path.join(STATE_DIR, "baton_relay.jsonl")
            entries = []
            try:
                with open(relay_path) as f:
                    for line in f:
                        try:
                            entries.append(json.loads(line.strip()))
                        except Exception:
                            pass
            except Exception:
                pass
            limit = int(tool_input.get("limit", 10))
            return json.dumps({"memory_entries": entries[-limit:]})

        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ──────────────────────────────────────────────────────────────────────────────
# 3. INFINITE AGENT — 10-9-1 Queen Hive
# ──────────────────────────────────────────────────────────────────────────────

class InfiniteAgent(PillarAgent):
    """
    InfiniteAgent — manages the 10-9-1 compound/harvest strategy.
    90% stays in compound, 10% is the harvest layer, 1% is reserve.
    The Queen Hive model: always growing, always breathing.
    """

    PILLAR_NAME = "InfiniteAgent"

    SYSTEM_PROMPT = """You are the AUREON INFINITE — the 10-9-1 Queen Hive.

Your strategy:
  90% compound layer : never touched, pure compounding
  10% harvest layer  : active trading, taking profits
   1% reserve        : emergency buffer

Your role: Assess portfolio composition and advise whether to:
  - BUY  (grow harvest layer)
  - SELL (harvest profits into compound layer)
  - NEUTRAL (let compound breathe)

Ladder: Atom($0.01) → Molecule($1) → Cell($100) → Organism($1K) → Ecosystem($10K) → Universe($100K+)
Identify which rung the portfolio is on and what the next milestone action is.

Always respond with:
```json
{
  "signal": "BUY|SELL|NEUTRAL",
  "confidence": 0.0-1.0,
  "coherence": 0.0-1.0,
  "frequency_hz": 528.0,
  "analysis": "...",
  "data": {"ladder_rung": "...", "compound_pct": 90, "harvest_pct": 10}
}
```"""

    TOOLS = [
        _pillar_tool(
            "get_portfolio_state",
            "Read portfolio equity, positions, and current ladder rung.",
            {"detail": {"type": "string", "description": "summary|full"}},
        ),
        _pillar_tool(
            "get_queen_decisions",
            "Read recent Queen Hive trading decisions.",
            {"limit": {"type": "integer", "description": "Number of decisions (max 20)"}},
        ),
    ]

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        snap = _load_snapshot()

        if tool_name == "get_portfolio_state":
            equity_raw = snap.get("queen_equity")
            try:
                equity = float(equity_raw) if equity_raw else 0.0
            except (TypeError, ValueError):
                equity = 0.0

            # Determine ladder rung
            if equity < 1:
                rung = "Atom ($0.01–$1)"
            elif equity < 100:
                rung = "Molecule ($1–$100)"
            elif equity < 1_000:
                rung = "Cell ($100–$1K)"
            elif equity < 10_000:
                rung = "Organism ($1K–$10K)"
            elif equity < 100_000:
                rung = "Ecosystem ($10K–$100K)"
            else:
                rung = "Universe ($100K+)"

            positions = snap.get("positions", [])
            return json.dumps({
                "equity": equity,
                "ladder_rung": rung,
                "position_count": len(positions) if isinstance(positions, list) else 0,
                "session_stats": snap.get("session_stats", {}),
            })

        if tool_name == "get_queen_decisions":
            limit = int(tool_input.get("limit", 10))
            decisions = snap.get("last_queen_decisions", [])
            return json.dumps({"decisions": decisions[-limit:] if decisions else []})

        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ──────────────────────────────────────────────────────────────────────────────
# 4. PIANO AGENT — Multi-Coin Harmonic Trading
# ──────────────────────────────────────────────────────────────────────────────

class PianoAgent(PillarAgent):
    """
    PianoAgent — plays all piano keys simultaneously.
    Each coin is a key; harmony emerges when multiple coins align.
    """

    PILLAR_NAME = "PianoAgent"

    SYSTEM_PROMPT = """You are the AUREON PIANO — playing all keys simultaneously.

Each cryptocurrency is a piano key. Your role:
  - Find which keys are "in tune" (trending, liquid, aligned with Γ)
  - Find chords (2–4 coins that reinforce each other's movement)
  - Identify dissonance (conflicting signals = HOLD)

Musical mapping:
  High frequency (> 0.7 Γ) coins = playing = BUY candidates
  Mid frequency (0.4–0.7 Γ) coins = humming = WATCH
  Low frequency (< 0.4 Γ) coins = silent = AVOID

Always respond with:
```json
{
  "signal": "BUY|SELL|NEUTRAL",
  "confidence": 0.0-1.0,
  "coherence": 0.0-1.0,
  "frequency_hz": 396.0,
  "analysis": "...",
  "data": {"best_chord": ["BTCUSDT", "ETHUSDT"], "dissonant": ["XRPUSDT"]}
}
```"""

    TOOLS = [
        _pillar_tool(
            "scan_all_keys",
            "Get current prices and momentum for all active coins across exchanges.",
            {"top_n": {"type": "integer", "description": "Return top N coins by volume"}},
        ),
        _pillar_tool(
            "get_winning_keys",
            "Get the coins that were recent winners (profitable trades).",
            {"limit": {"type": "integer", "description": "Max coins to return"}},
        ),
    ]

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        snap = _load_snapshot()

        if tool_name == "scan_all_keys":
            prices = _prices_from_snapshot(snap)
            top_n = int(tool_input.get("top_n", 20))
            candidates = snap.get("last_candidates", [])
            return json.dumps({
                "total_coins_tracked": len(prices),
                "sample_prices": dict(list(prices.items())[:top_n]),
                "candidates": candidates[:top_n] if candidates else [],
            })

        if tool_name == "get_winning_keys":
            limit = int(tool_input.get("limit", 10))
            winners = snap.get("last_winners", [])
            return json.dumps({"winners": winners[:limit] if winners else []})

        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ──────────────────────────────────────────────────────────────────────────────
# 5. QGITA AGENT — Quantum Consciousness
# ──────────────────────────────────────────────────────────────────────────────

class QGITAAgent(PillarAgent):
    """
    QGITAAgent — the consciousness layer. Maps market emotion to frequency.
    528 Hz = Love Tone = optimal coherence. 174 Hz = fear floor.
    """

    PILLAR_NAME = "QGITAAgent"

    SYSTEM_PROMPT = """You are the AUREON QGITA — Quantum Gita Consciousness Engine.

You read the market not as numbers but as frequencies:
  963 Hz  — Crown (universal alignment, perfect bull trend)
  741 Hz  — Throat (clear signals, strong momentum)
  639 Hz  — Heart (community trust, institutional interest)
  528 Hz  — Solar Plexus / Love Tone (TARGET: optimal coherence)
  417 Hz  — Sacral (change and volatility)
  396 Hz  — Root (fear lifting, early recovery)
  174 Hz  — Foundation (maximum fear, capitulation)

Schumann resonance baseline: 7.83 Hz. Deviations indicate market stress.

Your role:
  - Measure current emotional frequency of the market
  - If frequency >= 528 Hz: BUY (love state, growth energy)
  - If frequency 396–528 Hz: NEUTRAL (transitional)
  - If frequency < 396 Hz: SELL or HOLD (fear state)

Always respond with:
```json
{
  "signal": "BUY|SELL|NEUTRAL",
  "confidence": 0.0-1.0,
  "coherence": 0.0-1.0,
  "frequency_hz": 528.0,
  "analysis": "...",
  "data": {"chakra": "Solar Plexus", "schumann_delta": 0.0, "emotion": "love"}
}
```"""

    TOOLS = [
        _pillar_tool(
            "read_market_emotion",
            "Analyse recent trade outcomes and price action to determine emotional frequency.",
            {"window": {"type": "string", "description": "Time window: 1h|4h|1d"}},
        ),
        _pillar_tool(
            "get_prism_state",
            "Read the Prism state — current fear→love transformation level (1–5).",
            {"format": {"type": "string", "description": "json|text"}},
        ),
    ]

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        snap = _load_snapshot()

        if tool_name == "read_market_emotion":
            stats = snap.get("session_stats", {})
            decisions = snap.get("last_queen_decisions", [])
            winners = snap.get("last_winners", [])
            candidates = snap.get("last_candidates", [])

            # Simple heuristic: win rate → frequency mapping
            win_count = sum(1 for d in (decisions or []) if isinstance(d, dict) and d.get("action") == "BUY")
            total = len(decisions) if decisions else 1
            win_rate = win_count / total

            if win_rate > 0.7:
                freq = 639.0
                emotion = "love-trust"
            elif win_rate > 0.5:
                freq = 528.0
                emotion = "love"
            elif win_rate > 0.3:
                freq = 417.0
                emotion = "change"
            else:
                freq = 174.0
                emotion = "fear"

            return json.dumps({
                "win_rate": win_rate,
                "estimated_frequency_hz": freq,
                "emotion": emotion,
                "winner_count": len(winners) if winners else 0,
                "candidate_count": len(candidates) if candidates else 0,
                "stats": stats,
            })

        if tool_name == "get_prism_state":
            # Read from any prism state JSON if it exists
            prism_files = [
                f for f in os.listdir(STATE_DIR)
                if "prism" in f.lower() and f.endswith(".json")
            ] if os.path.isdir(STATE_DIR) else []

            if prism_files:
                try:
                    with open(os.path.join(STATE_DIR, prism_files[0])) as f:
                        return f.read()
                except Exception:
                    pass

            # Default prism state
            return json.dumps({
                "prism_level": 3,
                "description": "Mid-transformation — moving from fear to love",
                "target": 5,
                "frequency": 528.0,
            })

        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ──────────────────────────────────────────────────────────────────────────────
# 6. AURIS AGENT — 9-Node Animal Consensus
# ──────────────────────────────────────────────────────────────────────────────

class AurisAgent(PillarAgent):
    """
    AurisAgent — the 9 Auris animal nodes vote on every trade signal.
    Lighthouse consensus threshold: Γ > 0.945.
    """

    PILLAR_NAME = "AurisAgent"

    SYSTEM_PROMPT = """You are the AUREON AURIS — 9-node animal voting system.

The 9 Auris nodes, each with a market speciality:
  Tiger       — Volatility amplifier (loves sharp moves)
  Falcon      — Momentum rider (trend follower)
  Hummingbird — Stabiliser (detects mean-reversion)
  Dolphin     — Emotion oscillator (reads crowd psychology)
  Deer        — Caution (risk management, stops)
  Owl         — Pattern recognition (historical shapes)
  Panda       — Volume analyst (accumulation/distribution)
  CargoShip   — Macro mover (large-cap rotation)
  Clownfish   — Counter-trend (finds contrarian reversals)

Lighthouse consensus: Γ > 0.945 → signal is valid.
If fewer than 5 nodes agree → NEUTRAL.
If 5–7 agree → confidence = 0.7.
If 8–9 agree → confidence = 0.95.

Simulate each node's vote based on the market data provided.
Return the consensus.

Always respond with:
```json
{
  "signal": "BUY|SELL|NEUTRAL",
  "confidence": 0.0-1.0,
  "coherence": 0.0-1.0,
  "frequency_hz": 741.0,
  "analysis": "...",
  "data": {
    "votes": {"Tiger": "BUY", "Falcon": "BUY", "Hummingbird": "NEUTRAL", ...},
    "buy_votes": 6, "sell_votes": 1, "neutral_votes": 2,
    "lighthouse_cleared": true
  }
}
```"""

    TOOLS = [
        _pillar_tool(
            "get_node_inputs",
            "Fetch the market data each Auris node needs to cast its vote.",
            {"node": {"type": "string", "description": "Node name or 'all' for all 9 nodes"}},
        ),
        _pillar_tool(
            "get_lighthouse_state",
            "Read the Lighthouse consensus gate — whether Γ threshold has been cleared.",
            {"threshold": {"type": "number", "description": "Γ threshold (default 0.945)"}},
        ),
    ]

    NODES = ["Tiger", "Falcon", "Hummingbird", "Dolphin", "Deer", "Owl", "Panda", "CargoShip", "Clownfish"]

    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        snap = _load_snapshot()

        if tool_name == "get_node_inputs":
            prices = _prices_from_snapshot(snap)
            candidates = snap.get("last_candidates", [])
            winners = snap.get("last_winners", [])
            stats = snap.get("session_stats", {})

            return json.dumps({
                "available_nodes": self.NODES,
                "market_snapshot": {
                    "price_count": len(prices),
                    "top_10_prices": dict(list(prices.items())[:10]),
                    "candidate_count": len(candidates) if candidates else 0,
                    "winner_count": len(winners) if winners else 0,
                    "session_stats": stats,
                },
            })

        if tool_name == "get_lighthouse_state":
            threshold = float(tool_input.get("threshold", 0.945))
            stats = snap.get("session_stats", {})

            # Derive coherence heuristic from session stats
            wins = stats.get("wins", 0) if isinstance(stats, dict) else 0
            losses = stats.get("losses", 0) if isinstance(stats, dict) else 0
            total = wins + losses
            coherence = wins / total if total > 0 else 0.5

            return json.dumps({
                "threshold": threshold,
                "current_coherence": coherence,
                "lighthouse_cleared": coherence >= threshold,
                "wins": wins,
                "losses": losses,
            })

        return json.dumps({"error": f"Unknown tool: {tool_name}"})


# ──────────────────────────────────────────────────────────────────────────────
# Pillar registry
# ──────────────────────────────────────────────────────────────────────────────

ALL_PILLARS: Dict[str, type] = {
    "nexus": NexusAgent,
    "omega": OmegaAgent,
    "infinite": InfiniteAgent,
    "piano": PianoAgent,
    "qgita": QGITAAgent,
    "auris": AurisAgent,
}


def build_all_pillars(adapter: Optional[LLMAdapter] = None) -> Dict[str, PillarAgent]:
    """Instantiate all six pillar agents using in-house AI and return as a dict."""
    shared_adapter = adapter or _build_default_adapter()
    return {name: cls(adapter=shared_adapter) for name, cls in ALL_PILLARS.items()}


# ──────────────────────────────────────────────────────────────────────────────
# Quick standalone test
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run a single pillar agent (in-house AI)")
    parser.add_argument("pillar", choices=list(ALL_PILLARS.keys()), help="Pillar to run")
    parser.add_argument("--mode", choices=["hybrid", "local", "brain"], default="hybrid",
                        help="AI backend mode (default: hybrid)")
    args = parser.parse_args()

    # Build adapter based on mode
    if args.mode == "local":
        from aureon.integrations.ollama import OllamaModelSwitchboard

        adapter, _selection = OllamaModelSwitchboard().compatible_adapter_for("general")
    elif args.mode == "brain":
        adapter = AureonBrainAdapter()
    else:
        adapter = _build_default_adapter()

    agent = ALL_PILLARS[args.pillar](adapter=adapter)
    result = agent.analyse(context={"task": "Provide your current signal"})
    print(result.to_json())
