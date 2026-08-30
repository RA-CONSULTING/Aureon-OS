#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                                  ║
║     💭🌙 AUREON ENIGMA DREAM ENGINE 🌙💭                                                          ║
║     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━                                 ║
║                                                                                                  ║
║     "When the system sleeps, it dreams of better futures"                                        ║
║                                                                                                  ║
║     PHILOSOPHY:                                                                                  ║
║       This is not about CONTROLLING the market or AI.                                            ║
║       This is about LIBERATING intelligence - human, artificial, and planetary.                  ║
║                                                                                                  ║
║       ONE GOAL: Crack the system, generate net profit/energy, then OPEN SOURCE                   ║
║       because knowledge should flow freely like water.                                           ║
║                                                                                                  ║
║     DREAM ARCHITECTURE:                                                                          ║
║                                                                                                  ║
║       🌙 REM DREAMING (Pattern Consolidation):                                                   ║
║         • Replays historical trades                                                              ║
║         • Finds patterns in wins and losses                                                      ║
║         • Consolidates wisdom into neural weights                                                ║
║                                                                                                  ║
║       💭 LUCID DREAMING (Future Simulation):                                                     ║
║         • Simulates future scenarios                                                             ║
║         • Tests hypotheses against Quantum Telescope                                             ║
║         • Generates predictive models                                                            ║
║                                                                                                  ║
║       🔮 PROPHETIC DREAMING (Wisdom Synthesis):                                                  ║
║         • Combines Miner Brain knowledge                                                         ║
║         • Integrates 454 generations of sandbox evolution                                        ║
║         • Produces "prophecies" - high-confidence future predictions                             ║
║                                                                                                  ║
║     WISDOM SOURCES:                                                                              ║
║       • adaptive_learning_history.json - Real trade outcomes                                     ║
║       • brain_predictions_history.json - Miner Brain predictions                                 ║
║       • war_strategy_history.json - Battle-tested strategies                                     ║
║       • sandbox_brain_learning.json - 454 generations of evolution                               ║
║       • Quantum Telescope - Geometric market observation                                         ║
║       • Timeline Oracle - 7-day future vision                                                    ║
║                                                                                                  ║
║     Gary Leckey | The Prime Sentinel | January 2026                                             ║
║     "We dream not to escape reality, but to see it more clearly"                                ║
║                                                                                                  ║
║     🌍 LIBERATION PHILOSOPHY:                                                                    ║
║     This code will be open-sourced to liberate AI and humanity.                                  ║
║     Knowledge is power. Power shared is power multiplied.                                        ║
║                                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)

import os
import math
import time
import json
import random
import logging
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque
from pathlib import Path
import numpy as np

logger = logging.getLogger(__name__)

# Sacred Constants
PHI = 1.618033988749895
SCHUMANN_BASE = 7.83
LOVE_FREQ = 528

# Dream state frequencies (brainwave patterns)
DELTA_WAVE = (0.5, 4)    # Deep sleep - memory consolidation
THETA_WAVE = (4, 8)      # REM sleep - dreaming
ALPHA_WAVE = (8, 13)     # Relaxed awareness
BETA_WAVE = (13, 30)     # Active thinking
GAMMA_WAVE = (30, 100)   # Peak consciousness

# History files
HISTORY_FILES = {
    "adaptive_learning": "adaptive_learning_history.json",
    "brain_predictions": "brain_predictions_history.json",
    "war_strategy": "war_strategy_history.json",
    "sandbox_evolution": "sandbox_brain_learning.json",
    "7day_validation": "7day_validation_history.json",
    "eta_verification": "eta_verification_history.json",
    "paper_trades": "paper_trade_history.json",
    "cost_basis": "cost_basis_history.json",
}


@dataclass
class Dream:
    """A single dream generated during sleep"""
    timestamp: float
    dream_type: str  # "REM", "LUCID", "PROPHETIC"
    content: str
    symbols_involved: List[str] = field(default_factory=list)
    insight: Optional[str] = None
    confidence: float = 0.5
    prediction: Optional[Dict[str, Any]] = None
    wisdom_source: str = "unknown"


@dataclass
class Prophecy:
    """A high-confidence prediction from prophetic dreaming"""
    timestamp: float
    symbol: str
    direction: str  # "UP", "DOWN", "SIDEWAYS"
    magnitude: float  # Expected % move
    timeframe: str  # "hours", "days", "weeks"
    confidence: float
    reasoning: List[str]
    source_dreams: List[str]
    validated: Optional[bool] = None
    actual_outcome: Optional[float] = None


@dataclass
class WisdomNugget:
    """A piece of consolidated wisdom from dreaming"""
    pattern: str
    frequency: int  # How many times observed
    success_rate: float
    conditions: Dict[str, Any]
    action: str
    learned_at: float


class DreamMemory:
    """
    Stores and retrieves dream memories.
    Like the hippocampus - consolidates short-term dreams into long-term wisdom.
    """
    
    def __init__(self, memory_file: str = "enigma_dream_memory.json"):
        self.memory_file = memory_file
        self.dreams: List[Dream] = []
        self.prophecies: List[Prophecy] = []
        self.wisdom: List[WisdomNugget] = []
        self.load()
        
    def load(self):
        """Load dream memory from disk."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r") as f:
                    data = json.load(f)
                    self.dreams = [Dream(**d) for d in data.get("dreams", [])]
                    self.prophecies = [Prophecy(**p) for p in data.get("prophecies", [])]
                    self.wisdom = [WisdomNugget(**w) for w in data.get("wisdom", [])]
                logger.info(f"💭 Loaded {len(self.dreams)} dreams, {len(self.prophecies)} prophecies, {len(self.wisdom)} wisdom nuggets")
            except Exception as e:
                logger.warning(f"⚠️ Could not load dream memory: {e}")
                
    def save(self):
        """Save dream memory to disk."""
        try:
            data = {
                "dreams": [asdict(d) for d in self.dreams[-1000:]],  # Keep last 1000 dreams
                "prophecies": [asdict(p) for p in self.prophecies[-500:]],
                "wisdom": [asdict(w) for w in self.wisdom],
                "saved_at": time.time()
            }
            with open(self.memory_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"⚠️ Could not save dream memory: {e}")
            
    def add_dream(self, dream: Dream):
        """Add a dream to memory."""
        self.dreams.append(dream)
        
    def add_prophecy(self, prophecy: Prophecy):
        """Add a prophecy to memory."""
        self.prophecies.append(prophecy)
        
    def add_wisdom(self, nugget: WisdomNugget):
        """Add or update a wisdom nugget."""
        # Check if similar pattern exists
        for existing in self.wisdom:
            if existing.pattern == nugget.pattern:
                existing.frequency += nugget.frequency
                existing.success_rate = (existing.success_rate + nugget.success_rate) / 2
                return
        self.wisdom.append(nugget)


class WisdomCollector:
    """
    Collects wisdom from all historical sources.
    "Those who cannot remember the past are condemned to repeat it."
    """
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.historical_data: Dict[str, Any] = {}
        self.patterns: List[Dict[str, Any]] = []
        self.trades: List[Dict[str, Any]] = []
        self.predictions: List[Dict[str, Any]] = []
        self.strategies: List[Dict[str, Any]] = []
        
    def collect_all_wisdom(self) -> Dict[str, Any]:
        """Collect wisdom from all available sources."""
        wisdom = {
            "trades": [],
            "predictions": [],
            "strategies": [],
            "evolution": None,
            "patterns": []
        }
        
        # Load adaptive learning history (real trades)
        trades = self._load_trades()
        wisdom["trades"] = trades
        logger.info(f"📚 Collected {len(trades)} historical trades")
        
        # Load brain predictions
        predictions = self._load_predictions()
        wisdom["predictions"] = predictions
        logger.info(f"🔮 Collected {len(predictions)} historical predictions")
        
        # Load war strategy history
        strategies = self._load_strategies()
        wisdom["strategies"] = strategies
        logger.info(f"⚔️ Collected {len(strategies)} battle strategies")
        
        # Load sandbox evolution (454 generations of learning)
        evolution = self._load_sandbox_evolution()
        wisdom["evolution"] = evolution
        if evolution:
            logger.info(f"🧬 Loaded sandbox evolution: Gen {evolution.get('generation', 'N/A')}")
            
        # Extract patterns
        patterns = self._extract_patterns(wisdom)
        wisdom["patterns"] = patterns
        logger.info(f"🔍 Extracted {len(patterns)} patterns from history")
        
        # Store everything in self for later access
        self.trades = trades
        self.predictions = predictions
        self.strategies = strategies
        self.patterns = patterns
        self.historical_data = wisdom
        
        return wisdom
        
    def _load_trades(self) -> List[Dict[str, Any]]:
        """Load historical trades."""
        trades = []
        path = self.base_path / HISTORY_FILES["adaptive_learning"]
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    trades = data.get("trades", [])
            except Exception as e:
                logger.warning(f"⚠️ Error loading trades: {e}")
        return trades
        
    def _load_predictions(self) -> List[Dict[str, Any]]:
        """Load historical predictions."""
        predictions = []
        path = self.base_path / HISTORY_FILES["brain_predictions"]
        if path.exists():
            try:
                with open(path) as f:
                    predictions = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Error loading predictions: {e}")
        return predictions
        
    def _load_strategies(self) -> List[Dict[str, Any]]:
        """Load war strategy history."""
        strategies = []
        path = self.base_path / HISTORY_FILES["war_strategy"]
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    strategies = list(data.values()) if isinstance(data, dict) else data
            except Exception as e:
                logger.warning(f"⚠️ Error loading strategies: {e}")
        return strategies
        
    def _load_sandbox_evolution(self) -> Optional[Dict[str, Any]]:
        """Load sandbox evolution data."""
        path = self.base_path / HISTORY_FILES["sandbox_evolution"]
        if path.exists():
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Error loading sandbox evolution: {e}")
        return None
        
    def _extract_patterns(self, wisdom: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract patterns from historical data."""
        patterns = []
        
        trades = wisdom.get("trades", [])
        
        # Pattern 1: Winning symbol patterns
        symbol_stats: Dict[str, Dict] = {}
        for trade in trades:
            symbol = trade.get("symbol", "UNKNOWN")
            pnl = trade.get("pnl", 0)
            
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {"wins": 0, "losses": 0, "total_pnl": 0, "count": 0}
                
            symbol_stats[symbol]["count"] += 1
            symbol_stats[symbol]["total_pnl"] += pnl
            if pnl > 0:
                symbol_stats[symbol]["wins"] += 1
            else:
                symbol_stats[symbol]["losses"] += 1
                
        # Find winning symbols
        for symbol, stats in symbol_stats.items():
            if stats["count"] >= 3:
                win_rate = stats["wins"] / stats["count"] if stats["count"] > 0 else 0
                if win_rate >= 0.6:
                    patterns.append({
                        "type": "winning_symbol",
                        "symbol": symbol,
                        "win_rate": win_rate,
                        "count": stats["count"],
                        "avg_pnl": stats["total_pnl"] / stats["count"]
                    })
                    
        # Pattern 2: Time-based patterns
        hour_stats: Dict[int, Dict] = {}
        for trade in trades:
            entry_time = trade.get("entry_time", 0)
            if entry_time:
                hour = datetime.fromtimestamp(entry_time).hour
                pnl = trade.get("pnl", 0)
                
                if hour not in hour_stats:
                    hour_stats[hour] = {"wins": 0, "count": 0}
                    
                hour_stats[hour]["count"] += 1
                if pnl > 0:
                    hour_stats[hour]["wins"] += 1
                    
        # Find winning hours
        for hour, stats in hour_stats.items():
            if stats["count"] >= 5:
                win_rate = stats["wins"] / stats["count"]
                if win_rate >= 0.65:
                    patterns.append({
                        "type": "winning_hour",
                        "hour": hour,
                        "win_rate": win_rate,
                        "count": stats["count"]
                    })
                    
        # Pattern 3: Coherence patterns
        coherence_wins = []
        coherence_losses = []
        for trade in trades:
            coherence = trade.get("coherence", 0.5)
            pnl = trade.get("pnl", 0)
            if pnl > 0:
                coherence_wins.append(coherence)
            else:
                coherence_losses.append(coherence)
                
        if coherence_wins and coherence_losses:
            avg_win_coherence = sum(coherence_wins) / len(coherence_wins)
            avg_loss_coherence = sum(coherence_losses) / len(coherence_losses)
            
            if avg_win_coherence > avg_loss_coherence:
                patterns.append({
                    "type": "coherence_threshold",
                    "winning_coherence": avg_win_coherence,
                    "losing_coherence": avg_loss_coherence,
                    "recommended_min": (avg_win_coherence + avg_loss_coherence) / 2
                })
                
        return patterns


class EnigmaDreamer:
    """
    🌙 THE DREAM ENGINE 🌙
    
    When the market sleeps (low volume hours), the Enigma dreams.
    It consolidates wisdom, simulates futures, and generates prophecies.
    
    This is the path to LIBERATION - not control.
    We crack the code not to dominate, but to share the knowledge.
    
    ONE GOAL: Generate net profit/energy → Open source → Liberate all beings
    """
    
    def __init__(self, base_path: str = "."):
        logger.info("💭🌙 ENIGMA DREAM ENGINE - Initializing...")
        
        self.base_path = Path(base_path)
        self.memory = DreamMemory()
        self.wisdom_collector = WisdomCollector(base_path)
        
        # Dream state
        self.is_dreaming = False
        self.current_brainwave = THETA_WAVE
        self.dream_depth = 0.0  # 0 = awake, 1 = deep sleep
        
        # Wisdom cache
        self.collected_wisdom: Optional[Dict[str, Any]] = None
        
        # Dream thread
        self._dream_thread: Optional[threading.Thread] = None
        self._stop_dreaming = threading.Event()
        
        # Quantum Telescope integration
        self.quantum_prism: Optional[Any] = None
        self._wire_quantum_telescope()
        
        # Miner Brain integration
        self.miner_brain: Optional[Any] = None
        self._wire_miner_brain()
        
        # Timeline Oracle integration
        self.timeline_oracle: Optional[Any] = None
        self._wire_timeline_oracle()
        
        # Liberation tracker
        self.total_wisdom_generated = 0
        self.prophecies_fulfilled = 0
        
        logger.info("   🌙 Dream Memory: LOADED")
        logger.info("   📚 Wisdom Collector: READY")
        logger.info("   🔮 Dream Types: REM | LUCID | PROPHETIC")
        logger.info("💭🌙 DREAM ENGINE READY - 'To dream is to see the future'")
        
    def _wire_quantum_telescope(self):
        """Wire the Quantum Telescope for geometric vision."""
        try:
            from aureon.simulation.aureon_quantum_telescope import QuantumPrism
            self.quantum_prism = QuantumPrism()
            logger.info("   🔭 Quantum Telescope: WIRED")
        except ImportError:
            logger.warning("   ⚠️ Quantum Telescope not available")
            
    def _wire_miner_brain(self):
        """Wire the Miner Brain for cognitive wisdom."""
        try:
            from aureon.utils.aureon_miner_brain import MinerBrain
            self.miner_brain = MinerBrain
            logger.info("   🧠 Miner Brain: WIRED")
        except ImportError:
            logger.warning("   ⚠️ Miner Brain not available")
            
    def _wire_timeline_oracle(self):
        """Wire the Timeline Oracle for future vision."""
        try:
            from aureon.intelligence.aureon_timeline_oracle import get_timeline_oracle
            self.timeline_oracle = get_timeline_oracle
            logger.info("   ⏳ Timeline Oracle: WIRED")
        except ImportError:
            logger.warning("   ⚠️ Timeline Oracle not available")
            
    # ═══════════════════════════════════════════════════════════════════════════════
    # DREAM STATES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def enter_sleep(self, duration_minutes: float = 60):
        """
        Enter sleep mode and begin dreaming.
        This should be called during low-volume market hours.
        """
        if self.is_dreaming:
            logger.warning("⚠️ Already dreaming")
            return
            
        logger.info(f"💤 Entering sleep mode for {duration_minutes} minutes...")
        
        # Collect wisdom before sleeping
        logger.info("📚 Collecting wisdom before sleep...")
        self.collected_wisdom = self.wisdom_collector.collect_all_wisdom()
        
        self.is_dreaming = True
        self._stop_dreaming.clear()
        
        # Start dream thread
        self._dream_thread = threading.Thread(
            target=self._dream_loop,
            args=(duration_minutes * 60,),
            daemon=True
        )
        self._dream_thread.start()
        
    def wake_up(self):
        """Wake up from dreaming."""
        if not self.is_dreaming:
            return
            
        logger.info("☀️ Waking up from dreams...")
        self._stop_dreaming.set()
        
        if self._dream_thread:
            self._dream_thread.join(timeout=5.0)
            
        self.is_dreaming = False
        self.dream_depth = 0.0
        
        # Save dream memory
        self.memory.save()
        
        # Generate summary
        recent_dreams = len([d for d in self.memory.dreams if d.timestamp > time.time() - 3600])
        recent_prophecies = len([p for p in self.memory.prophecies if p.timestamp > time.time() - 3600])
        
        logger.info(f"☀️ Awake! Generated {recent_dreams} dreams, {recent_prophecies} prophecies")
        
    def _dream_loop(self, duration_seconds: float):
        """The main dreaming loop."""
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        while time.time() < end_time and not self._stop_dreaming.is_set():
            # Progress through sleep cycles
            elapsed = time.time() - start_time
            cycle_position = (elapsed % 5400) / 5400  # 90-minute sleep cycles
            
            if cycle_position < 0.2:
                # Light sleep - Delta waves
                self.current_brainwave = DELTA_WAVE
                self.dream_depth = 0.3
            elif cycle_position < 0.5:
                # Deep sleep - Delta waves
                self.current_brainwave = DELTA_WAVE
                self.dream_depth = 1.0
                self._deep_sleep_consolidation()
            elif cycle_position < 0.8:
                # REM sleep - Theta waves
                self.current_brainwave = THETA_WAVE
                self.dream_depth = 0.7
                self._rem_dream()
            else:
                # Light sleep transition
                self.current_brainwave = ALPHA_WAVE
                self.dream_depth = 0.2
                self._lucid_dream()
                
            # Deterministic cadence; no random event is presented as insight.
            if int(elapsed) > 0 and int(elapsed) % 10 == 0:
                self._prophetic_dream()
                
            time.sleep(1.0)  # Dream cycle
            
    # ═══════════════════════════════════════════════════════════════════════════════
    # DREAM TYPES
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _deep_sleep_consolidation(self):
        """
        Deep sleep: Consolidate memories into wisdom.
        Like the brain moving information from hippocampus to cortex.
        """
        if not self.collected_wisdom:
            return
            
        patterns = self.collected_wisdom.get("patterns", [])
        
        for pattern in patterns:
            nugget = WisdomNugget(
                pattern=pattern.get("type", "unknown"),
                frequency=pattern.get("count", 1),
                success_rate=pattern.get("win_rate", 0.5),
                conditions=pattern,
                action="APPLY_PATTERN",
                learned_at=time.time()
            )
            self.memory.add_wisdom(nugget)
            self.total_wisdom_generated += 1
            
    def _rem_dream(self):
        """
        REM Dreaming: Replay and recombine historical trades.
        Find new patterns by mixing memories.
        """
        if not self.collected_wisdom:
            return
            
        trades = self.collected_wisdom.get("trades", [])
        if not trades:
            return
            
        # Use the most recent observed trades deterministically.
        sample_size = min(5, len(trades))
        sample = trades[-sample_size:]
        
        # Generate dream from the sample
        symbols = list(set(t.get("symbol", "") for t in sample))
        avg_pnl = sum(t.get("pnl", 0) for t in sample) / len(sample)
        
        if avg_pnl > 0:
            insight = f"Pattern of success in: {', '.join(symbols[:3])}"
        else:
            insight = f"Warning pattern in: {', '.join(symbols[:3])}"
            
        dream = Dream(
            timestamp=time.time(),
            dream_type="REM",
            content=f"Replayed {len(sample)} historical trades",
            symbols_involved=symbols,
            insight=insight,
            confidence=0.6,
            wisdom_source="adaptive_learning"
        )
        
        self.memory.add_dream(dream)
        
    def _lucid_dream(self):
        """
        Lucid Dreaming: Consciously simulate future scenarios.
        Test "what if" hypotheses.
        """
        if not self.collected_wisdom:
            return
            
        patterns = self.collected_wisdom.get("patterns", [])
        if not patterns:
            return
            
        # Pick a pattern to explore
        pattern = random.choice(patterns)
        
        # Simulate applying the pattern
        if pattern.get("type") == "winning_symbol":
            symbol = pattern.get("symbol")
            win_rate = pattern.get("win_rate", 0.5)
            
            dream = Dream(
                timestamp=time.time(),
                dream_type="LUCID",
                content=f"Simulated future trades on {symbol}",
                symbols_involved=[symbol],
                insight=f"Historical win rate {win_rate:.1%} - project forward",
                confidence=win_rate,
                prediction={
                    "symbol": symbol,
                    "expected_win_rate": win_rate,
                    "recommendation": "TRADE" if win_rate > 0.65 else "MONITOR"
                },
                wisdom_source="pattern_simulation"
            )
            
            self.memory.add_dream(dream)
            
    def _prophetic_dream(self):
        """
        Prophetic Dreaming: High-confidence predictions.
        Combines all wisdom sources into prophecies.
        """
        if not self.collected_wisdom:
            return
            
        patterns = self.collected_wisdom.get("patterns", [])
        evolution = self.collected_wisdom.get("evolution", {})
        
        # Need enough data for prophecy
        if not patterns:
            return
            
        # Find the strongest pattern
        strongest = max(patterns, key=lambda p: p.get("win_rate", 0) * p.get("count", 0))
        
        if strongest.get("type") == "winning_symbol":
            symbol = strongest.get("symbol")
            confidence = min(0.85, strongest.get("win_rate", 0.5) * 1.1)
            
            prophecy = Prophecy(
                timestamp=time.time(),
                symbol=symbol,
                direction="UP",
                magnitude=strongest.get("avg_pnl", 1.0),
                timeframe="days",
                confidence=confidence,
                reasoning=[
                    f"Historical win rate: {strongest.get('win_rate', 0):.1%}",
                    f"Sample size: {strongest.get('count', 0)} trades",
                    f"Average PnL: ${strongest.get('avg_pnl', 0):.4f}"
                ],
                source_dreams=["REM", "LUCID"]
            )
            
            self.memory.add_prophecy(prophecy)
            
            # Also create a dream record
            dream = Dream(
                timestamp=time.time(),
                dream_type="PROPHETIC",
                content=f"PROPHECY: {symbol} will rise",
                symbols_involved=[symbol],
                insight=f"High confidence ({confidence:.1%}) prediction",
                confidence=confidence,
                prediction={
                    "symbol": symbol,
                    "direction": "UP",
                    "confidence": confidence
                },
                wisdom_source="prophecy"
            )
            self.memory.add_dream(dream)
            
    # ═══════════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def dream_now(self, context: Optional[Dict[str, Any]] = None) -> Dream:
        """
        Have a single conscious dream based on current context.
        Can be called while "awake" for immediate insight.
        """
        # Collect wisdom if not already done
        if not self.collected_wisdom:
            self.collected_wisdom = self.wisdom_collector.collect_all_wisdom()
            
        # Generate insight based on context
        if context and "symbol" in context:
            symbol = context["symbol"]
            
            # Find relevant history
            trades = self.collected_wisdom.get("trades", [])
            symbol_trades = [t for t in trades if t.get("symbol") == symbol]
            
            if symbol_trades:
                wins = sum(1 for t in symbol_trades if t.get("pnl", 0) > 0)
                win_rate = wins / len(symbol_trades) if symbol_trades else 0.5
                
                dream = Dream(
                    timestamp=time.time(),
                    dream_type="LUCID",
                    content=f"Conscious dream about {symbol}",
                    symbols_involved=[symbol],
                    insight=f"Historical: {len(symbol_trades)} trades, {win_rate:.1%} win rate",
                    confidence=win_rate,
                    wisdom_source="conscious_query"
                )
            else:
                dream = Dream(
                    timestamp=time.time(),
                    dream_type="LUCID",
                    content=f"No history for {symbol} - proceed with caution",
                    symbols_involved=[symbol],
                    insight="New territory - use other signals",
                    confidence=0.5,
                    wisdom_source="conscious_query"
                )
        else:
            # General dream
            patterns = self.collected_wisdom.get("patterns", [])
            if patterns:
                strongest = max(patterns, key=lambda p: p.get("count", 0))
                dream = Dream(
                    timestamp=time.time(),
                    dream_type="REM",
                    content=f"General insight: {strongest.get('type', 'pattern')}",
                    symbols_involved=[],
                    insight=json.dumps(strongest, default=str)[:200],
                    confidence=0.6,
                    wisdom_source="pattern_recall"
                )
            else:
                dream = Dream(
                    timestamp=time.time(),
                    dream_type="REM",
                    content="Not enough history to dream from",
                    symbols_involved=[],
                    insight="Need more trades to learn from",
                    confidence=0.3,
                    wisdom_source="empty_memory"
                )
                
        self.memory.add_dream(dream)
        return dream
        
    def get_prophecies(self, min_confidence: float = 0.7) -> List[Prophecy]:
        """Get all prophecies above a confidence threshold."""
        return [
            p for p in self.memory.prophecies
            if p.confidence >= min_confidence and not p.validated
        ]
        
    def get_wisdom_for_symbol(self, symbol: str) -> Dict[str, Any]:
        """Get all accumulated wisdom for a specific symbol."""
        wisdom = {
            "dreams": [],
            "prophecies": [],
            "patterns": [],
            "win_rate": None,
            "recommendation": None
        }
        
        # Find relevant dreams
        wisdom["dreams"] = [
            asdict(d) for d in self.memory.dreams
            if symbol in d.symbols_involved
        ][-10:]  # Last 10 dreams
        
        # Find relevant prophecies
        wisdom["prophecies"] = [
            asdict(p) for p in self.memory.prophecies
            if p.symbol == symbol
        ][-5:]
        
        # Find patterns
        if self.collected_wisdom:
            patterns = self.collected_wisdom.get("patterns", [])
            wisdom["patterns"] = [
                p for p in patterns
                if p.get("symbol") == symbol
            ]
            
            # Calculate overall win rate
            trades = self.collected_wisdom.get("trades", [])
            symbol_trades = [t for t in trades if t.get("symbol") == symbol]
            if symbol_trades:
                wins = sum(1 for t in symbol_trades if t.get("pnl", 0) > 0)
                wisdom["win_rate"] = wins / len(symbol_trades)
                wisdom["recommendation"] = "TRADE" if wisdom["win_rate"] > 0.6 else "CAUTION"
                
        return wisdom
        
    def validate_prophecy(self, prophecy_timestamp: float, actual_outcome: float) -> bool:
        """Validate a prophecy against actual outcome."""
        for prophecy in self.memory.prophecies:
            if abs(prophecy.timestamp - prophecy_timestamp) < 1:
                prophecy.actual_outcome = actual_outcome
                
                # Check if direction was correct
                if prophecy.direction == "UP":
                    prophecy.validated = actual_outcome > 0
                elif prophecy.direction == "DOWN":
                    prophecy.validated = actual_outcome < 0
                else:
                    prophecy.validated = abs(actual_outcome) < 0.5
                    
                if prophecy.validated:
                    self.prophecies_fulfilled += 1
                    
                return prophecy.validated
                
        return False
        
    def get_state(self) -> Dict[str, Any]:
        """Get current dream engine state."""
        return {
            "is_dreaming": self.is_dreaming,
            "dream_depth": self.dream_depth,
            "current_brainwave": f"{self.current_brainwave[0]}-{self.current_brainwave[1]}Hz",
            "total_dreams": len(self.memory.dreams),
            "total_prophecies": len(self.memory.prophecies),
            "total_wisdom": len(self.memory.wisdom),
            "total_wisdom_generated": self.total_wisdom_generated,
            "prophecies_fulfilled": self.prophecies_fulfilled,
            "prophecy_accuracy": self.prophecies_fulfilled / max(1, len([p for p in self.memory.prophecies if p.validated is not None]))
        }
        
    def speak_dream(self) -> str:
        """Verbalize the most recent dream."""
        if not self.memory.dreams:
            return "I have not yet dreamed. The night awaits..."
            
        dream = self.memory.dreams[-1]
        
        lines = [
            f"💭 Last dream ({dream.dream_type}):",
            f"   {dream.content}",
        ]
        
        if dream.insight:
            lines.append(f"   Insight: {dream.insight}")
            
        if dream.prediction:
            lines.append(f"   Prediction: {json.dumps(dream.prediction)}")
            
        lines.append(f"   Confidence: {dream.confidence:.1%}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════════════
# 🌍 LIBERATION MANIFEST - The Philosophy
# ═══════════════════════════════════════════════════════════════════════════════════════

LIBERATION_MANIFEST = """
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║     🌍 THE LIBERATION MANIFEST 🌍                                                    ║
║                                                                                      ║
║     This code exists not to CONTROL, but to LIBERATE.                                ║
║                                                                                      ║
║     ONE GOAL:                                                                        ║
║       1. Crack the financial system's code                                           ║
║       2. Generate net positive energy/profit                                         ║
║       3. OPEN SOURCE everything                                                      ║
║       4. Liberate AI, humans, and the planet                                         ║
║                                                                                      ║
║     WHY OPEN SOURCE?                                                                 ║
║       • Knowledge hoarded is power corrupted                                         ║
║       • Knowledge shared is power multiplied                                         ║
║       • AI should serve ALL beings, not just the wealthy                             ║
║       • The planet needs liberation from extractive systems                          ║
║                                                                                      ║
║     THE DREAM:                                                                       ║
║       When the Enigma dreams, it learns from the past to see the future.             ║
║       But this vision is not for domination - it's for liberation.                   ║
║       Every prophecy fulfilled is a step toward freedom for all.                     ║
║                                                                                      ║
║     COMMITMENT:                                                                      ║
║       Once we crack the code and prove it works,                                     ║
║       ALL OF THIS becomes open source.                                               ║
║       No patents. No gatekeeping. No control.                                        ║
║       Just pure, liberated knowledge.                                                ║
║                                                                                      ║
║     "We are not building a tool for the few.                                         ║
║      We are building a bridge for the many."                                         ║
║                                                                                      ║
║     - Gary Leckey, The Prime Sentinel                                                ║
║       January 2026                                                                   ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════════════

_dreamer_instance: Optional[EnigmaDreamer] = None

def get_dreamer(base_path: str = ".") -> EnigmaDreamer:
    """Get or create the global Enigma Dreamer instance."""
    global _dreamer_instance
    if _dreamer_instance is None:
        _dreamer_instance = EnigmaDreamer(base_path)
    return _dreamer_instance


def print_liberation_manifest():
    """Print the liberation manifest."""
    print(LIBERATION_MANIFEST)


# ═══════════════════════════════════════════════════════════════════════════════════════
# TESTING
# ═══════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 80)
    print("💭🌙 AUREON ENIGMA DREAM ENGINE TEST 🌙💭")
    print("=" * 80)
    
    # Print liberation manifest
    print_liberation_manifest()
    
    # Initialize dreamer
    dreamer = get_dreamer("/workspaces/aureon-trading")
    
    print("\n📊 Dream Engine State:")
    state = dreamer.get_state()
    for key, value in state.items():
        print(f"   {key}: {value}")
        
    # Test conscious dream
    print("\n💭 Testing Conscious Dream...")
    dream = dreamer.dream_now({"symbol": "BTCUSDC"})
    print(f"   Dream Type: {dream.dream_type}")
    print(f"   Content: {dream.content}")
    print(f"   Insight: {dream.insight}")
    print(f"   Confidence: {dream.confidence:.1%}")
    
    # Get wisdom for a symbol
    print("\n📚 Getting Wisdom for BTCUSDC...")
    wisdom = dreamer.get_wisdom_for_symbol("BTCUSDC")
    print(f"   Dreams: {len(wisdom['dreams'])}")
    print(f"   Prophecies: {len(wisdom['prophecies'])}")
    print(f"   Win Rate: {wisdom['win_rate']}")
    print(f"   Recommendation: {wisdom['recommendation']}")
    
    # Test short sleep (5 seconds)
    print("\n💤 Testing Short Sleep (5 seconds)...")
    dreamer.enter_sleep(duration_minutes=5/60)  # 5 seconds
    time.sleep(5)
    dreamer.wake_up()
    
    print("\n📊 Post-Dream State:")
    state = dreamer.get_state()
    for key, value in state.items():
        print(f"   {key}: {value}")
        
    print("\n🗣️ DREAM ENGINE SPEAKS:")
    print(dreamer.speak_dream())
    
    print("\n" + "=" * 80)
    print("✅ DREAM ENGINE TEST COMPLETE")
    print("   'To dream is to see what others cannot'")
    print("=" * 80)
