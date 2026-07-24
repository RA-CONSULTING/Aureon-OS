#!/usr/bin/env python3
"""
🧠 AUREON MINER BRAIN - CRITICAL THINKING & SPECULATION ENGINE 🧠
==================================================================

"Your feet are for dancing, your brain is for cutting out the bullshit!"

This module empowers the Miner to:
1.  SEARCH the internet for Crypto & Global Financial Metadata.
2.  SPECULATE - Think critically about what the data REALLY means.
3.  CROSS-EXAMINE - Ask subsystems "Is this truth or spoof?"
4.  DEBATE - Internal council of "advisors" argue the case.
5.  SYNTHESIZE - Cut through the noise to find the signal.
6.  LEARN - Feed validated insights into the Learning Algorithm.

COMPONENTS:
├─ WebKnowledgeMiner: Gathers raw data from multiple sources.
├─ CoinbaseCortex: Deep market structure analysis.
├─ SkepticalAnalyzer: "Is this data being manipulated?"
├─ SpeculationEngine: "What does this REALLY mean?"
├─ TruthCouncil: Subsystems debate truth vs. spoof.
├─ NarrativeEngine: Generates the critical "Talk".
└─ MemoryCore: Stores validated knowledge.

Gary Leckey & GitHub Copilot | December 2025
"The Miner doesn't just read - it THINKS."
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import os
import sys
import json
import time
import logging
import requests
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import deque

# Import Thought Bus for Unity
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
except ImportError:
    ThoughtBus = None
    Thought = None

# ═══════════════════════════════════════════════════════════════════════════
# WINDOWS UTF-8 FIX - Must be at top before any logging
# ═══════════════════════════════════════════════════════════════════════════
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass  # Fall back to default if reconfiguration fails

# Import existing feeds if available
try:
    from aureon.exchanges.coinbase_historical_feed import CoinbaseHistoricalFeed
    from aureon.data_feeds.global_financial_feed import GlobalFinancialFeed
except ImportError:
    CoinbaseHistoricalFeed = None
    GlobalFinancialFeed = None

# ⏳🔮 TIMELINE ORACLE - 7-day future validation
try:
    from aureon.intelligence.aureon_timeline_oracle import (
        TimelineOracle, TimelineBranch, TimelineAction,
        timeline_select, timeline_validate, get_timeline_oracle
    )
    TIMELINE_ORACLE_AVAILABLE = True
    print("⏳🔮 Miner Brain: Timeline Oracle WIRED! (7-day vision)")
except ImportError:
    TIMELINE_ORACLE_AVAILABLE = False
    TimelineOracle = None
    timeline_select = None

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURE LOGGING WITH UTF-8 HANDLER (Windows fix)
# ═══════════════════════════════════════════════════════════════════════════
class UTF8StreamHandler(logging.StreamHandler):
    """Custom handler that handles Unicode properly on Windows"""
    def __init__(self):
        super().__init__(stream=sys.stdout)
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            msg = self.format(record).encode('utf-8', errors='replace').decode('utf-8')
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

# Configure Logging with UTF-8 support
if sys.platform == 'win32':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("miner_brain.log", encoding='utf-8'),
            UTF8StreamHandler()
        ]
    )
else:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("miner_brain.log"),
            logging.StreamHandler()
        ]
    )
logger = logging.getLogger("MinerBrain")

PHI = (1 + math.sqrt(5)) / 2  # Golden Ratio

# 👑 QUEEN'S SACRED 1.88% LAW - THE BRAIN SERVES THE QUEEN
QUEEN_MIN_COP = 1.0188              # Sacred constant: 1.88% minimum realized profit
QUEEN_MIN_PROFIT_PCT = 1.88         # Percentage form - all brain decisions honor this
QUEEN_BRAIN_PROFIT_FREQ = 188.0     # Hz - Sacred frequency in brain patterns

# Adaptive Learning Integration
ADAPTIVE_LEARNING_FILE = "adaptive_learning_history.json"
BRAIN_PREDICTIONS_FILE = "brain_predictions_history.json"
SANDBOX_LEARNING_FILE = "sandbox_brain_learning.json"
IRA_TRAINING_FILE = "sniper_million_model.json"
WISDOM_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wisdom_data")


def merge_canonical_into_qc(qc_ctx: Dict[str, Any], field: Any) -> Dict[str, Any]:
    """Self-source the miner's harmonic context from the ONE canonical HNC field.

    Fills ``piano_lambda`` (Λ), ``planetary_gamma`` (Γ) and ``quantum_coherence`` (Ψ) into ``qc_ctx``
    ONLY where the caller left them ``None`` — an explicitly-injected value always wins; this merely
    fills gaps so the adaptive cycle is directed by the shared ``symbolic.life.pulse`` instead of the
    static 0.5/1.0 defaults. Also records ``hnc_field_source``. Mutates and returns ``qc_ctx``; a
    ``field`` that is unavailable/None leaves it untouched. Pure and side-effect-free beyond ``qc_ctx``,
    so the runtime-direction audit (b43) and a unit test can exercise it without running a full cycle.
    """
    if not getattr(field, "available", False):
        return qc_ctx
    canonical = {
        "piano_lambda": getattr(field, "lambda_t", None),
        "planetary_gamma": getattr(field, "coherence_gamma", None),
        "quantum_coherence": getattr(field, "consciousness_psi", None),
    }
    for key, val in canonical.items():
        if val is not None and qc_ctx.get(key) is None:
            qc_ctx[key] = val
    qc_ctx.setdefault("hnc_field_source", getattr(field, "source", None) or "canonical")
    return qc_ctx


# ═══════════════════════════════════════════════════════════════
# 🧬 SANDBOX EVOLVED PARAMETERS - Learned Through 454 Generations
# ═══════════════════════════════════════════════════════════════

class SandboxEvolution:
    """
    Parameters evolved through genetic algorithm in sandboxed simulation.
    The brain learned these values through trial and error, NOT given answers.
    
    454 generations of learning discovered:
    - Optimal coherence thresholds
    - Position sizing
    - Profit taking & loss-guard thresholds
    - Market volatility sweet spots
    
    These parameters are LIVE LOADED from the sandbox learning file,
    so the brain continuously improves as more simulations run.
    
    🎯 PENNY SNIPER MODE: For quick penny profit trades, we use relaxed
    thresholds. The penny profit math protects us - if gross > fees + $0.01,
    the trade is profitable regardless of market coherence!
    """
    
    # Default parameters (from 454 generations of evolution)
    # 🔧 UPDATED: Lowered min_coherence for penny profit hunting
    DEFAULT_PARAMS = {
        "min_coherence": 0.40,          # 🎯 LOWERED: Trade when market quality > 40%
        "min_volatility": 0.50,          # 🎯 LOWERED: Need 0.5% minimum volatility
        "max_volatility": 3.00,          # 🎯 RAISED: Allow more volatile markets
        "position_size_pct": 0.122,      # 12.2% of capital per trade
        "take_profit_pct": 1.82,         # Let winners run to 1.82%
        "stop_loss_pct": 1.43,           # Loss-guard threshold reference (not a forced-loss exit)
        "hold_cycles_max": 64,           # Patience - hold up to 64 cycles
        "use_maker_orders": False,       # Taker orders (evolved preference)
        "penny_sniper_mode": True,       # 🎯 NEW: Bypass filters for penny profits
    }
    
    def __init__(self):
        self.params = self.DEFAULT_PARAMS.copy()
        self.best_win_rate = 0.0
        self.generations = 0
        self.lessons = []
        self.ira_training: Optional[Dict[str, Any]] = None
        self._load_from_sandbox()
        self._load_ira_training()

    def _load_ira_training(self) -> None:
        """Load IRA sniper training results for contextual guidance."""
        try:
            if not os.path.exists(IRA_TRAINING_FILE):
                logger.info("IRA training model not found; continuing without sniper insights")
                return

            with open(IRA_TRAINING_FILE, "r") as f:
                model = json.load(f)

            params = model.get("parameters", {})
            required_r = params.get("required_r", 0)

            total_trades = model.get("total_trades") or 0
            self.ira_training = {
                "win_rate": model.get("win_rate"),
                "total_trades": total_trades,
                "avg_pnl": model.get("avg_pnl"),
                "avg_hold_bars": model.get("avg_hold_bars"),
                "position_size": params.get("position_size"),
                "required_move_pct": required_r * 100 if required_r else None,
                "training_completed": model.get("training_completed"),
                "message": model.get("message"),
            }

            logger.info(
                "🎯 IRA training loaded: %s trades @ %.2f%% win rate; required move %.2f%%",
                f"{total_trades:,}" if total_trades else "unknown",
                self.ira_training.get("win_rate", 0.0),
                self.ira_training.get("required_move_pct", 0.0),
            )
        except Exception as e:
            logger.warning(f"Could not load IRA training model: {e}")
    
    def _load_from_sandbox(self):
        """Load evolved parameters from sandbox learning file."""
        try:
            if os.path.exists(SANDBOX_LEARNING_FILE):
                with open(SANDBOX_LEARNING_FILE, 'r') as f:
                    data = json.load(f)
                    
                    # Load best parameters
                    if 'best_parameters' in data and data['best_parameters']:
                        for key, value in data['best_parameters'].items():
                            if key in self.params:
                                self.params[key] = value
                    
                    self.best_win_rate = data.get('best_win_rate', 0)
                    self.generations = data.get('generation', 0)
                    self.lessons = data.get('lessons', [])[-10:]  # Keep last 10
                    
                    logger.info(f"🧬 Loaded sandbox evolution: Gen {self.generations}, "
                               f"Best {self.best_win_rate:.1f}% win rate")
        except Exception as e:
            logger.warning(f"Could not load sandbox learning: {e}")
    
    def get_entry_filter(self, volatility: float, coherence: float, penny_mode: bool = False) -> Tuple[bool, str]:
        """
        Apply evolved entry filter.
        Returns (should_enter, reason)
        
        🪙 PENNY PROFIT MODE: All filters are now advisory.
        The penny profit math (exact fee calculation) is the REAL gate.
        We just log warnings but always allow entry.
        """
        ira_note = self._describe_ira_alignment(volatility)

        # 🪙 PENNY MODE: Always enabled - just log warnings
        # Only reject on truly dangerous conditions
        if coherence < 0.02:  # Near-zero coherence = broken data
            return False, f"⚠️ Coherence {coherence:.2f} = data error"
        if volatility > 25.0:  # Extreme volatility - market halted/flash crash
            return False, f"⚠️ Volatility {volatility:.2f}% = market chaos"
        
        # Everything else is just advisory - let penny math be the gate
        return True, f"🪙 PENNY MODE: Entry allowed{ira_note}"

    def _describe_ira_alignment(self, volatility: float) -> str:
        """Return a short note showing how current volatility compares to IRA training needs."""
        if not self.ira_training or not self.ira_training.get("required_move_pct"):
            return ""

        required_move = self.ira_training["required_move_pct"]
        if volatility >= required_move:
            return f" | IRA training: volatility supports {required_move:.2f}% move"
        if volatility >= required_move * 0.6:
            return f" | IRA training: volatility {volatility:.2f}% is within range of {required_move:.2f}% target"
        return f" | IRA training: volatility {volatility:.2f}% below {required_move:.2f}% target"
    
    def get_exit_targets(self, entry_price: float, trade_size: float = 10.0, exchange: str = 'binance') -> Dict[str, float]:
        """
        🪙 SHARED GOAL: Calculate exit targets based on PENNY PROFIT math.
        
        The ONLY goal is +$0.01 net profit after ALL fees.
        All other percentage-based targets are ADVISORY.
        """
        # Try to import penny profit math
        try:
            from aureon.trading.aureon_unified_ecosystem import get_penny_threshold
            
            penny = get_penny_threshold(exchange, trade_size)
            if penny:
                required_r = penny['required_r']
                return {
                    'take_profit_price': entry_price * (1 + required_r),
                    'stop_loss_price': entry_price * (1 - required_r * 3),  # 3:1 risk
                    'take_profit_pct': required_r * 100,
                    'stop_loss_pct': required_r * 300,
                    'penny_target_net': penny['target_net'],
                    'shared_goal': f"+${penny['target_net']:.2f} net after fees",
                }
        except ImportError:
            pass
        
        # Fallback to percentage-based (but this is NOT the shared goal)
        return {
            'take_profit_price': entry_price * (1 + self.params['take_profit_pct'] / 100),
            'stop_loss_price': entry_price * (1 - self.params['stop_loss_pct'] / 100),
            'take_profit_pct': self.params['take_profit_pct'],
            'stop_loss_pct': self.params['stop_loss_pct'],
            'shared_goal': 'FALLBACK: Using percentage targets (penny math unavailable)',
        }
    
    def get_position_size(self, capital: float) -> float:
        """
        Calculate position size based on evolved optimal percentage.
        """
        return capital * self.params['position_size_pct']
    
    def get_evolved_confidence_boost(self, base_confidence: float) -> float:
        """
        Boost confidence based on evolved win rate.
        If sandbox achieved >60% win rate, brain trusts itself more.
        """
        if self.best_win_rate > 70:
            return min(100, base_confidence * 1.15)  # 15% boost
        elif self.best_win_rate > 60:
            return min(100, base_confidence * 1.08)  # 8% boost
        elif self.best_win_rate > 50:
            return min(100, base_confidence * 1.03)  # 3% boost
        else:
            return base_confidence  # No boost until proven
    
    def get_trading_guidance(self) -> Dict:
        """
        Get comprehensive trading guidance from evolved parameters.
        """
        return {
            'evolved_generation': self.generations,
            'evolved_win_rate': self.best_win_rate,
            'entry_coherence_min': self.params['min_coherence'],
            'volatility_range': (self.params['min_volatility'], self.params['max_volatility']),
            'position_size_pct': self.params['position_size_pct'] * 100,
            'take_profit_pct': self.params['take_profit_pct'],
            'stop_loss_pct': self.params['stop_loss_pct'],
            'max_hold_cycles': self.params['hold_cycles_max'],
            'prefer_maker': self.params['use_maker_orders'],
            'latest_lessons': self.lessons[-5:] if self.lessons else [],
            'ira_training': self.ira_training,
        }
    
    def __str__(self) -> str:
        return (f"🧬 Sandbox Evolution (Gen {self.generations})\n"
                f"   Win Rate: {self.best_win_rate:.1f}%\n"
                f"   Coherence: >{self.params['min_coherence']:.0%}\n"
                f"   Volatility: {self.params['min_volatility']:.2f}%-{self.params['max_volatility']:.2f}%\n"
                f"   Position: {self.params['position_size_pct']:.1%}\n"
                f"   Take Profit: {self.params['take_profit_pct']:.2f}%\n"
                f"   Loss Guard: {self.params['stop_loss_pct']:.2f}%")


# Global sandbox evolution instance
_sandbox_evolution: Optional[SandboxEvolution] = None

def get_sandbox_evolution() -> SandboxEvolution:
    """Get or create the global sandbox evolution instance."""
    global _sandbox_evolution
    if _sandbox_evolution is None:
        _sandbox_evolution = SandboxEvolution()
    return _sandbox_evolution


# ═══════════════════════════════════════════════════════════════
# 📚 WISDOM JSON LOADER - Dynamic Cultural Knowledge Enrichment
# ═══════════════════════════════════════════════════════════════

class WisdomJSONLoader:
    """
    Loads wisdom from external JSON files scanned by the WisdomScanner.
    This allows the Brain to continuously enrich its cultural knowledge
    from Wikipedia and other metadata sources.
    
    The loader provides:
    - Dynamic wisdom loading from JSON files
    - Fallback to hardcoded wisdom if JSON unavailable
    - Topic relevance filtering for market context
    - Cross-civilization pattern synthesis
    """
    
    # Mapping civilization names to JSON filenames
    CIVILIZATION_FILES = {
        "celtic": "celtic_wisdom.json",
        "aztec": "aztec_wisdom.json",
        "egyptian": "egyptian_wisdom.json",
        "pythagorean": "pythagorean_wisdom.json",
        "plantagenet": "plantagenet_wisdom.json",
        "mogollon": "mogollon_wisdom.json",
        "warfare": "warfare_wisdom.json",
        "chinese": "chinese_wisdom.json",
        "hindu": "hindu_wisdom.json",
        "mayan": "mayan_wisdom.json",
        "norse": "norse_wisdom.json",
    }
    
    def __init__(self):
        self.wisdom_cache: Dict[str, Dict] = {}
        self.last_load_time: Dict[str, datetime] = {}
        self.cache_duration = timedelta(minutes=5)  # Reload every 5 minutes
        self._load_all_wisdom()
    
    def _load_all_wisdom(self):
        """Load all civilization wisdom files."""
        if not os.path.exists(WISDOM_DATA_DIR):
            logger.warning(f"Wisdom data directory not found: {WISDOM_DATA_DIR}")
            return
        
        for civ_name, filename in self.CIVILIZATION_FILES.items():
            self._load_civilization_wisdom(civ_name, filename)
    
    def _load_civilization_wisdom(self, civ_name: str, filename: str):
        """Load wisdom for a specific civilization."""
        filepath = os.path.join(WISDOM_DATA_DIR, filename)
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.wisdom_cache[civ_name] = data
                    self.last_load_time[civ_name] = datetime.now()
                    topic_count = len(data.get('topics', []))
                    logger.debug(f"[WISDOM] Loaded {topic_count} topics for {civ_name}")
        except Exception as e:
            logger.warning(f"[WISDOM] Could not load {filename}: {e}")
    
    def get_wisdom(self, civilization: str) -> Dict:
        """
        Get wisdom for a civilization, reloading if cache expired.
        Returns empty dict if not available.
        """
        civ_lower = civilization.lower()
        
        # Check if cache expired
        if civ_lower in self.last_load_time:
            if datetime.now() - self.last_load_time[civ_lower] > self.cache_duration:
                filename = self.CIVILIZATION_FILES.get(civ_lower)
                if filename:
                    self._load_civilization_wisdom(civ_lower, filename)
        
        return self.wisdom_cache.get(civ_lower, {})
    
    def get_relevant_wisdom(self, civilization: str, market_context: str = "") -> List[Dict]:
        """
        Get wisdom topics relevant to current market context.
        
        Args:
            civilization: The civilization to query
            market_context: Keywords like "volatile", "trending", "consolidating"
        
        Returns:
            List of relevant wisdom topic dictionaries
        """
        wisdom = self.get_wisdom(civilization)
        topics = wisdom.get('topics', [])
        
        if not market_context or not topics:
            return topics
        
        # Filter by relevance to market context
        context_lower = market_context.lower()
        relevant = []
        
        for topic in topics:
            # Check if topic relates to market context
            topic_text = f"{topic.get('name', '')} {topic.get('content', '')} {topic.get('trading_insight', '')}".lower()
            
            # Keyword matching for relevance
            relevance_keywords = {
                "volatile": ["change", "storm", "war", "chaos", "transformation", "destruction"],
                "trending": ["flow", "path", "cycle", "momentum", "growth", "rise"],
                "consolidating": ["wait", "patience", "rest", "balance", "foundation", "prepare"],
                "bullish": ["growth", "rise", "victory", "harvest", "abundance", "expansion"],
                "bearish": ["decline", "caution", "winter", "retreat", "preservation", "defense"],
            }
            
            keywords = relevance_keywords.get(context_lower, [])
            if any(kw in topic_text for kw in keywords):
                relevant.append(topic)
        
        return relevant if relevant else topics[:5]  # Return first 5 if no matches
    
    def get_all_trading_insights(self, civilization: str) -> List[str]:
        """Get all trading insights from a civilization's wisdom."""
        wisdom = self.get_wisdom(civilization)
        insights = []
        
        for topic in wisdom.get('topics', []):
            if 'trading_insight' in topic and topic['trading_insight']:
                insights.append(topic['trading_insight'])
        
        return insights
    
    def get_cross_civilization_patterns(self, pattern_type: str) -> Dict[str, List[str]]:
        """
        Find similar patterns across multiple civilizations.
        Useful for finding universal truths.
        
        Args:
            pattern_type: e.g., "cycles", "numbers", "seasons"
        
        Returns:
            Dict mapping civilization to relevant insights
        """
        patterns = {}
        
        for civ_name in self.CIVILIZATION_FILES.keys():
            relevant = self.get_relevant_wisdom(civ_name, pattern_type)
            if relevant:
                patterns[civ_name] = [
                    t.get('trading_insight', t.get('content', ''))[:200]
                    for t in relevant[:3]
                ]
        
        return patterns
    
    def reload_all(self):
        """Force reload all wisdom files."""
        self.wisdom_cache.clear()
        self.last_load_time.clear()
        self._load_all_wisdom()
        logger.info("[WISDOM] Reloaded all civilization wisdom files")


# Global wisdom loader instance
_wisdom_loader: Optional[WisdomJSONLoader] = None

def get_wisdom_loader() -> WisdomJSONLoader:
    """Get or create the global wisdom loader instance."""
    global _wisdom_loader
    if _wisdom_loader is None:
        _wisdom_loader = WisdomJSONLoader()
    return _wisdom_loader


# ═══════════════════════════════════════════════════════════════
# 🔄 COGNITIVE CIRCLE - Self-Reflection & Learning
# ═══════════════════════════════════════════════════════════════

class CognitiveCircle:
    """
    The brain analyzes its OWN output, compares predictions to reality,
    and learns from the delta. This completes the cognitive feedback loop.
    
    "I said X would happen. Did it? If not, why was I wrong?"
    """
    
    def __init__(self):
        self.predictions_file = BRAIN_PREDICTIONS_FILE
        self.adaptive_file = ADAPTIVE_LEARNING_FILE
        self.predictions: List[Dict] = []
        self.accuracy_history: deque = deque(maxlen=100)
        self.bias_tracker = {
            "bullish_calls": 0, "bullish_correct": 0,
            "bearish_calls": 0, "bearish_correct": 0,
            "neutral_calls": 0, "neutral_correct": 0
        }
        self._load_predictions()
        
    def _load_predictions(self):
        """Load past predictions to check against reality."""
        try:
            if os.path.exists(self.predictions_file):
                with open(self.predictions_file, 'r') as f:
                    data = json.load(f)
                    self.predictions = data.get('predictions', [])[-100:]
                    self.bias_tracker = data.get('bias_tracker', self.bias_tracker)
        except Exception as e:
            logger.warning(f"Could not load predictions: {e}")
    
    def _save_predictions(self):
        """Save predictions for future validation."""
        try:
            with open(self.predictions_file, 'w') as f:
                json.dump({
                    'predictions': self.predictions[-100:],
                    'bias_tracker': self.bias_tracker,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save predictions: {e}")
    
    def record_prediction(self, brain_output: Dict):
        """
        Record the brain's current prediction for later validation.
        """
        prediction = {
            'timestamp': datetime.now().isoformat(),
            'validation_time': (datetime.now() + timedelta(hours=2)).isoformat(),
            'btc_price_at_call': brain_output.get('btc_price', 0),
            'consensus': brain_output.get('consensus', 'UNKNOWN'),
            'manipulation_probability': brain_output.get('manipulation_probability', 0),
            'fear_greed': brain_output.get('fear_greed', 50),
            'predicted_direction': self._infer_direction(brain_output),
            'confidence': brain_output.get('truth_score', 0.5),
            'validated': False,
            'was_correct': None,
            'actual_outcome': None
        }
        
        self.predictions.append(prediction)
        self._save_predictions()
        
        logger.info(f"🔮 Prediction recorded: {prediction['predicted_direction']} (conf: {prediction['confidence']:.0%})")
        return prediction
    
    def _infer_direction(self, brain_output: Dict) -> str:
        """Infer directional prediction from brain output."""
        fng = brain_output.get('fear_greed', 50)
        consensus = brain_output.get('consensus', '')
        
        # The brain's contrarian logic
        if fng < 30:
            return "BULLISH"  # Buy fear
        elif fng > 70:
            return "BEARISH"  # Sell greed
        elif "MANIPULATION" in consensus:
            return "OPPOSITE_OF_NARRATIVE"
        else:
            return "NEUTRAL"
    
    def validate_past_predictions(self, current_btc_price: float) -> List[Dict]:
        """
        Check old predictions against reality.
        This is where the brain learns from its mistakes.
        """
        validated = []
        now = datetime.now()
        
        for pred in self.predictions:
            if pred['validated']:
                continue
                
            # Check if it's time to validate (2 hours passed)
            validation_time = datetime.fromisoformat(pred['validation_time'])
            if now < validation_time:
                continue
            
            # Calculate what actually happened
            price_at_call = pred['btc_price_at_call']
            if price_at_call <= 0:
                continue
                
            price_change_pct = ((current_btc_price - price_at_call) / price_at_call) * 100
            
            # Determine if prediction was correct - DIRECTION MATCH, not magnitude!
            # BULLISH + UP = correct, BEARISH + DOWN = correct
            predicted = pred['predicted_direction']
            actual_direction = "UP" if price_change_pct > 0 else "DOWN" if price_change_pct < 0 else "FLAT"
            
            if predicted == "BULLISH":
                was_correct = price_change_pct > 0  # Any move up = correct
                self.bias_tracker['bullish_calls'] += 1
                if was_correct:
                    self.bias_tracker['bullish_correct'] += 1
            elif predicted == "BEARISH":
                was_correct = price_change_pct < 0  # Any move down = correct
                self.bias_tracker['bearish_calls'] += 1
                if was_correct:
                    self.bias_tracker['bearish_correct'] += 1
            else:
                was_correct = abs(price_change_pct) < 0.5  # Stayed relatively flat
                self.bias_tracker['neutral_calls'] += 1
                if was_correct:
                    self.bias_tracker['neutral_correct'] += 1
            
            # Update prediction
            pred['validated'] = True
            pred['was_correct'] = was_correct
            pred['actual_outcome'] = {
                'price_at_validation': current_btc_price,
                'price_change_pct': price_change_pct,
                'direction': "UP" if price_change_pct > 0 else "DOWN"
            }
            
            self.accuracy_history.append(1 if was_correct else 0)
            validated.append(pred)
            
            logger.info(
                f"🔍 Prediction Validated: {predicted} → "
                f"{'✅ CORRECT' if was_correct else '❌ WRONG'} "
                f"(Δ {price_change_pct:+.2f}%)"
            )
        
        self._save_predictions()
        return validated
    
    def get_accuracy_stats(self) -> Dict:
        """Get brain's prediction accuracy statistics."""
        if not self.accuracy_history:
            return {'overall_accuracy': 0.5, 'total_predictions': 0}
        
        overall = sum(self.accuracy_history) / len(self.accuracy_history)
        
        # Calculate bias-specific accuracy
        bullish_acc = (self.bias_tracker['bullish_correct'] / 
                       max(1, self.bias_tracker['bullish_calls']))
        bearish_acc = (self.bias_tracker['bearish_correct'] / 
                       max(1, self.bias_tracker['bearish_calls']))
        neutral_acc = (self.bias_tracker['neutral_correct'] / 
                       max(1, self.bias_tracker['neutral_calls']))
        
        return {
            'overall_accuracy': overall,
            'total_predictions': len(self.accuracy_history),
            'bullish_accuracy': bullish_acc,
            'bearish_accuracy': bearish_acc,
            'neutral_accuracy': neutral_acc,
            'bias_tracker': self.bias_tracker
        }
    
    def generate_self_critique(self, accuracy_stats: Dict) -> List[str]:
        """
        The brain critiques its own performance.
        "Where am I going wrong? What biases do I have?"
        """
        critiques = []
        
        overall = accuracy_stats.get('overall_accuracy', 0.5)
        total = accuracy_stats.get('total_predictions', 0)
        
        if total < 5:
            critiques.append("📊 Insufficient data for self-critique. Need more predictions.")
            return critiques
        
        critiques.append(f"📊 Overall Accuracy: {overall:.1%} across {total} predictions")
        
        # Identify biases
        bullish_acc = accuracy_stats.get('bullish_accuracy', 0.5)
        bearish_acc = accuracy_stats.get('bearish_accuracy', 0.5)
        
        if bullish_acc < 0.4:
            critiques.append("⚠️ BIAS DETECTED: I'm too bullish. My 'buy fear' calls are often wrong.")
            critiques.append("   → LEARNING: Be more patient. Fear can persist longer than expected.")
        elif bullish_acc > 0.7:
            critiques.append("✅ STRENGTH: My bullish calls are accurate. Trust contrarian signals.")
        
        if bearish_acc < 0.4:
            critiques.append("⚠️ BIAS DETECTED: I'm calling tops too early. Greed can run.")
            critiques.append("   → LEARNING: Wait for confirmation before calling reversals.")
        elif bearish_acc > 0.7:
            critiques.append("✅ STRENGTH: My bearish calls are accurate. Trust the greed warnings.")
        
        # Overall assessment
        if overall < 0.4:
            critiques.append("🔴 CRITICAL: My predictions are worse than a coin flip.")
            critiques.append("   → ACTION: Invert my signals or reduce confidence weights.")
        elif overall < 0.5:
            critiques.append("🟡 WARNING: Slightly below random. Need recalibration.")
        elif overall > 0.6:
            critiques.append("🟢 GOOD: Above average accuracy. Continue current approach.")
        
        return critiques
    
    def feed_to_adaptive_learning(self, brain_output: Dict, accuracy_stats: Dict):
        """
        Feed brain insights to the main adaptive learning system.
        This connects the cognitive circle to trading decisions.
        """
        try:
            # Load existing adaptive learning data
            adaptive_data = {'trades': [], 'thresholds': {}}
            if os.path.exists(self.adaptive_file):
                with open(self.adaptive_file, 'r') as f:
                    adaptive_data = json.load(f)
            
            # Add brain meta-learning entry
            if 'brain_insights' not in adaptive_data:
                adaptive_data['brain_insights'] = []
            
            insight = {
                'timestamp': datetime.now().isoformat(),
                'fear_greed': brain_output.get('fear_greed', 50),
                'consensus': brain_output.get('consensus', 'UNKNOWN'),
                'manipulation_probability': brain_output.get('manipulation_probability', 0),
                'brain_accuracy': accuracy_stats.get('overall_accuracy', 0.5),
                'recommended_bias': self._compute_recommended_bias(accuracy_stats),
                'confidence_adjustment': self._compute_confidence_adjustment(accuracy_stats)
            }
            
            adaptive_data['brain_insights'].append(insight)
            adaptive_data['brain_insights'] = adaptive_data['brain_insights'][-50:]
            
            # Update thresholds based on brain accuracy
            if 'thresholds' not in adaptive_data:
                adaptive_data['thresholds'] = {}
            
            # If brain is accurate, trust its signals more
            if accuracy_stats.get('overall_accuracy', 0.5) > 0.6:
                current_prob = adaptive_data['thresholds'].get('min_probability', 0.5)
                adaptive_data['thresholds']['min_probability'] = max(0.4, current_prob - 0.02)
            
            with open(self.adaptive_file, 'w') as f:
                json.dump(adaptive_data, f, indent=2)
            
            logger.info("🔗 Brain insights fed to Adaptive Learning system")
            
        except Exception as e:
            logger.error(f"Could not feed to adaptive learning: {e}")
    
    def _compute_recommended_bias(self, stats: Dict) -> str:
        """Recommend bias adjustment based on accuracy."""
        bullish = stats.get('bullish_accuracy', 0.5)
        bearish = stats.get('bearish_accuracy', 0.5)
        
        if bullish > bearish + 0.15:
            return "TRUST_BULLISH_CALLS"
        elif bearish > bullish + 0.15:
            return "TRUST_BEARISH_CALLS"
        else:
            return "BALANCED"
    
    def _compute_confidence_adjustment(self, stats: Dict) -> float:
        """Compute how much to trust brain's confidence scores."""
        overall = stats.get('overall_accuracy', 0.5)
        
        # If brain is accurate, amplify its confidence
        # If inaccurate, dampen it
        if overall > 0.6:
            return 1.2  # Trust more
        elif overall < 0.4:
            return 0.7  # Trust less
        else:
            return 1.0  # Neutral


# ═══════════════════════════════════════════════════════════════
# 🪞 SELF-REFLECTION ENGINE - Analyzes Own Output
# ═══════════════════════════════════════════════════════════════

class SelfReflectionEngine:
    """
    The brain looks at its own talk and asks:
    "Did I make sense? Was I being logical? What did I miss?"
    """
    
    def reflect_on_output(self, talk: str, data: Dict, council_result: Dict) -> Dict:
        """
        Analyze the brain's own output for consistency and blind spots.
        """
        logger.info("🪞 Self-Reflection: Analyzing my own output...")
        
        reflection = {
            'logical_consistency': True,
            'blind_spots': [],
            'contradictions': [],
            'confidence_calibration': 'APPROPRIATE',
            'action_clarity': True,
            'improvement_suggestions': []
        }
        
        fng = data.get('processed', {}).get('fear_greed', 50)
        consensus = council_result.get('consensus', '')
        truth_score = council_result.get('truth_score', 0.5)
        spoof_score = council_result.get('spoof_score', 0.5)
        
        # Check 1: Is my confidence calibrated?
        if truth_score > 0.8 and "INCONCLUSIVE" in consensus:
            reflection['logical_consistency'] = False
            reflection['contradictions'].append(
                "High truth score but inconclusive consensus - conflicting signals"
            )
        
        # Check 2: Am I missing obvious factors?
        if fng < 20 and spoof_score < 0.2:
            reflection['blind_spots'].append(
                "Extreme fear with low spoof detection - am I being too trusting?"
            )
        
        # Check 3: Did I give clear actionable advice?
        if "GATHER_MORE_DATA" in talk and "Prioritize" in talk:
            reflection['contradictions'].append(
                "Saying 'gather more data' while also giving strategy advice - mixed message"
            )
        
        # Check 4: Am I overconfident in manipulation detection?
        if spoof_score > 0.7 and "SUSPICIOUS" in talk:
            reflection['blind_spots'].append(
                "High manipulation score - but am I seeing ghosts? Not everything is a conspiracy."
            )
        
        # Check 5: Am I anchoring to extreme readings?
        if fng < 25 or fng > 75:
            reflection['blind_spots'].append(
                f"Extreme F&G ({fng}) may be causing anchoring bias. Consider mean reversion timeline."
            )
        
        # Generate improvement suggestions
        if not reflection['logical_consistency']:
            reflection['improvement_suggestions'].append(
                "Resolve contradictions before presenting conclusions"
            )
        
        if reflection['blind_spots']:
            reflection['improvement_suggestions'].append(
                f"Address {len(reflection['blind_spots'])} potential blind spots in next cycle"
            )
        
        if len(reflection['contradictions']) == 0 and len(reflection['blind_spots']) == 0:
            reflection['improvement_suggestions'].append(
                "Analysis appears internally consistent. Maintain current framework."
            )
        
        return reflection


# ═══════════════════════════════════════════════════════════════
# 💭 DREAM ENGINE - Live Scenario Simulation
# ═══════════════════════════════════════════════════════════════

class DreamEngine:
    """
    🌙 THE BRAIN DREAMS 🌙
    
    While awake, the brain processes reality.
    While dreaming, it simulates scenarios on live data.
    
    Dreams are:
    - "What if BTC drops 10% right now?"
    - "What if Fear turns to Greed overnight?"
    - "What if this is the bottom/top?"
    - "What would I do if manipulation spikes?"
    
    The brain runs these scenarios continuously, making decisions
    on hypothetical situations, learning from the imagined outcomes.
    """
    
    DREAM_SCENARIOS = [
        {"name": "FLASH_CRASH", "btc_delta": -0.10, "fng_delta": -20, "description": "Sudden 10% crash"},
        {"name": "MOON_MISSION", "btc_delta": 0.15, "fng_delta": 30, "description": "15% pump to greed"},
        {"name": "SLOW_BLEED", "btc_delta": -0.03, "fng_delta": -5, "description": "Gradual 3% decline"},
        {"name": "ACCUMULATION", "btc_delta": 0.02, "fng_delta": 5, "description": "Quiet 2% rise"},
        {"name": "WHALE_DUMP", "btc_delta": -0.07, "fng_delta": -15, "description": "7% whale selloff"},
        {"name": "FOMO_SPIKE", "btc_delta": 0.08, "fng_delta": 20, "description": "8% FOMO rally"},
        {"name": "MANIPULATION_UP", "btc_delta": 0.05, "fng_delta": 0, "description": "5% pump, sentiment unchanged"},
        {"name": "MANIPULATION_DOWN", "btc_delta": -0.05, "fng_delta": 0, "description": "5% dump, sentiment unchanged"},
        {"name": "SENTIMENT_FLIP", "btc_delta": 0.01, "fng_delta": 40, "description": "Sentiment flips, price flat"},
        {"name": "BLACK_SWAN", "btc_delta": -0.25, "fng_delta": -50, "description": "25% crash - black swan event"},
    ]
    
    def __init__(self):
        self.dream_log: List[Dict] = []
        self.dream_insights: Dict[str, List] = {}  # scenario -> list of decisions
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AureonDreamEngine/1.0'})
        
    # Comprehensive market symbols for full market understanding
    MARKET_SYMBOLS = [
        # 🏆 Tier 1: Major Cryptocurrencies
        ("BTC", "BTCUSDT"),      # Bitcoin - King
        ("ETH", "ETHUSDT"),      # Ethereum - Queen
        ("BNB", "BNBUSDT"),      # Binance Coin
        ("XRP", "XRPUSDT"),      # Ripple
        ("SOL", "SOLUSDT"),      # Solana
        ("ADA", "ADAUSDT"),      # Cardano
        
        # 🐕 Meme Coins (Sentiment Indicators)
        ("DOGE", "DOGEUSDT"),    # Dogecoin - OG meme
        ("SHIB", "SHIBUSDT"),    # Shiba Inu
        ("PEPE", "PEPEUSDT"),    # Pepe
        ("FLOKI", "FLOKIUSDT"),  # Floki
        ("BONK", "BONKUSDT"),    # Bonk (Solana meme)
        ("WIF", "WIFUSDT"),      # Dogwifhat
        
        # 🔗 Layer 1 Blockchains
        ("AVAX", "AVAXUSDT"),    # Avalanche
        ("DOT", "DOTUSDT"),      # Polkadot
        ("MATIC", "MATICUSDT"),  # Polygon
        ("ATOM", "ATOMUSDT"),    # Cosmos
        ("NEAR", "NEARUSDT"),    # NEAR Protocol
        ("FTM", "FTMUSDT"),      # Fantom
        ("APT", "APTUSDT"),      # Aptos
        ("SUI", "SUIUSDT"),      # Sui
        ("SEI", "SEIUSDT"),      # Sei
        ("INJ", "INJUSDT"),      # Injective
        
        # 🏦 DeFi (Financial Health)
        ("LINK", "LINKUSDT"),    # Chainlink - Oracle king
        ("UNI", "UNIUSDT"),      # Uniswap
        ("AAVE", "AAVEUSDT"),    # Aave
        ("MKR", "MKRUSDT"),      # Maker
        ("CRV", "CRVUSDT"),      # Curve
        ("LDO", "LDOUSDT"),      # Lido
        ("SNX", "SNXUSDT"),      # Synthetix
        
        # 🤖 AI & Gaming Coins
        ("FET", "FETUSDT"),      # Fetch.ai
        ("RNDR", "RNDRUSDT"),    # Render
        ("AGIX", "AGIXUSDT"),    # SingularityNET
        ("IMX", "IMXUSDT"),      # Immutable X (Gaming)
        ("GALA", "GALAUSDT"),    # Gala Games
        ("AXS", "AXSUSDT"),      # Axie Infinity
        
        # 📈 High-Beta Assets (Risk Appetite)
        ("ORDI", "ORDIUSDT"),    # Bitcoin Ordinals
        ("STX", "STXUSDT"),      # Stacks (BTC L2)
        ("TIA", "TIAUSDT"),      # Celestia
        ("OP", "OPUSDT"),        # Optimism
        ("ARB", "ARBUSDT"),      # Arbitrum
        
        # 🔒 Privacy & Legacy
        ("LTC", "LTCUSDT"),      # Litecoin
        ("BCH", "BCHUSDT"),      # Bitcoin Cash
        ("ETC", "ETCUSDT"),      # Ethereum Classic
        ("XMR", "XMRUSDT"),      # Monero (if available)
        
        # 🌐 Infrastructure
        ("FIL", "FILUSDT"),      # Filecoin
        ("AR", "ARUSDT"),        # Arweave
        ("GRT", "GRTUSDT"),      # The Graph
        ("ENS", "ENSUSDT"),      # ENS
    ]
    
    def fetch_live_tickers(self) -> Dict[str, Any]:
        """
        Fetch comprehensive real-time ticker data for market understanding.
        Returns detailed data including price, 24h change, and volume.
        """
        tickers = {}
        detailed_tickers = {}
        
        # Fetch all tickers in one call (more efficient)
        try:
            resp = self.session.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                timeout=(3.05, 5)  # (connect, read) - shorter to prevent hangs
            )
            if resp.status_code == 200:
                all_tickers = {t['symbol']: t for t in resp.json()}
                
                for symbol, binance_sym in self.MARKET_SYMBOLS:
                    if binance_sym in all_tickers:
                        data = all_tickers[binance_sym]
                        price = float(data.get('lastPrice', 0))
                        tickers[symbol] = price
                        detailed_tickers[symbol] = {
                            'price': price,
                            'change_24h': float(data.get('priceChangePercent', 0)),
                            'volume_24h': float(data.get('quoteVolume', 0)),
                            'high_24h': float(data.get('highPrice', 0)),
                            'low_24h': float(data.get('lowPrice', 0)),
                            'trades_24h': int(data.get('count', 0)),
                        }
        except Exception as e:
            logger.debug(f"Bulk ticker fetch error: {e}")
            # Fallback to individual requests for top 5
            for symbol, binance_sym in self.MARKET_SYMBOLS[:5]:
                try:
                    resp = self.session.get(
                        f"https://api.binance.com/api/v3/ticker/price?symbol={binance_sym}",
                        timeout=5
                    )
                    if resp.status_code == 200:
                        tickers[symbol] = float(resp.json().get('price', 0))
                except:
                    pass
        
        # Store detailed data for brain analysis
        self._detailed_tickers = detailed_tickers
        return tickers
    
    def get_market_sectors(self) -> Dict[str, Dict]:
        """
        Analyze market by sector - gives brain understanding of where money is flowing.
        """
        if not hasattr(self, '_detailed_tickers') or not self._detailed_tickers:
            self.fetch_live_tickers()
        
        sectors = {
            'majors': ['BTC', 'ETH', 'BNB', 'XRP', 'SOL', 'ADA'],
            'meme': ['DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF'],
            'layer1': ['AVAX', 'DOT', 'MATIC', 'ATOM', 'NEAR', 'FTM', 'APT', 'SUI', 'SEI', 'INJ'],
            'defi': ['LINK', 'UNI', 'AAVE', 'MKR', 'CRV', 'LDO', 'SNX'],
            'ai_gaming': ['FET', 'RNDR', 'AGIX', 'IMX', 'GALA', 'AXS'],
            'high_beta': ['ORDI', 'STX', 'TIA', 'OP', 'ARB'],
            'legacy': ['LTC', 'BCH', 'ETC'],
        }
        
        sector_performance = {}
        for sector_name, symbols in sectors.items():
            changes = []
            volumes = []
            for sym in symbols:
                if sym in self._detailed_tickers:
                    changes.append(self._detailed_tickers[sym]['change_24h'])
                    volumes.append(self._detailed_tickers[sym]['volume_24h'])
            
            if changes:
                sector_performance[sector_name] = {
                    'avg_change_24h': sum(changes) / len(changes),
                    'total_volume_24h': sum(volumes),
                    'strongest': max(zip(symbols[:len(changes)], changes), key=lambda x: x[1])[0] if changes else None,
                    'weakest': min(zip(symbols[:len(changes)], changes), key=lambda x: x[1])[0] if changes else None,
                    'assets_up': sum(1 for c in changes if c > 0),
                    'assets_down': sum(1 for c in changes if c < 0),
                }
        
        return sector_performance
    
    def get_market_breadth(self) -> Dict:
        """
        Calculate market breadth - how many assets are up vs down.
        Key indicator of market health.
        """
        if not hasattr(self, '_detailed_tickers') or not self._detailed_tickers:
            self.fetch_live_tickers()

        total = len(self._detailed_tickers)
        if total == 0:
            # Stage AP: was returning hardcoded {'breadth': 0.5, 'status':
            # 'UNKNOWN'} silently when CoinGecko top-100 fetch failed.
            # Now logged + tagged so callers can detect "no real ticker
            # data" and skip rather than treating 0.5 as a real reading.
            import logging
            logging.getLogger(__name__).warning(
                "[insufficient-data] get_market_breadth: no live tickers "
                "available (CoinGecko fetch likely failed); returning "
                "neutral breadth 0.5 with status=UNKNOWN — caller should "
                "skip breadth-gated decisions"
            )
            return {'breadth': 0.5, 'status': 'UNKNOWN', 'no_real_data': True}

        up = sum(1 for t in self._detailed_tickers.values() if t['change_24h'] > 0)
        down = sum(1 for t in self._detailed_tickers.values() if t['change_24h'] < 0)

        # No fallback needed below since total > 0 was checked above.
        breadth = up / total

        # Weighted by volume — guard against zero vol total but no fake substitution
        total_vol = sum(t['volume_24h'] for t in self._detailed_tickers.values())
        vol_up = sum(t['volume_24h'] for t in self._detailed_tickers.values() if t['change_24h'] > 0)
        vol_breadth = vol_up / total_vol if total_vol > 0 else None
        
        return {
            'breadth': breadth,
            'volume_breadth': vol_breadth,
            'up_count': up,
            'down_count': down,
            'total_assets': total,
            'status': 'STRONG_BULL' if breadth > 0.7 else 'BULL' if breadth > 0.55 else 'BEAR' if breadth < 0.45 else 'STRONG_BEAR' if breadth < 0.3 else 'NEUTRAL'
        }
    
    def fetch_live_sentiment(self) -> Dict:
        """Fetch real-time sentiment data."""
        try:
            resp = self.session.get("https://api.alternative.me/fng/?limit=1", timeout=5)
            if resp.status_code == 200:
                data = resp.json().get('data', [{}])[0]
                return {
                    'fear_greed': int(data.get('value', 50)),
                    'classification': data.get('value_classification', 'Neutral')
                }
        except:
            pass
        return {'fear_greed': 50, 'classification': 'Neutral'}
    
    def dream(self, live_data: Dict = None) -> Dict:
        """
        Run a dream cycle - simulate scenarios on current market state.
        """
        logger.info("💭 Dream Engine entering REM state...")
        
        # Get live data if not provided
        if not live_data:
            tickers = self.fetch_live_tickers()
            sentiment = self.fetch_live_sentiment()
            live_data = {
                'btc_price': tickers.get('BTC', 90000),
                'eth_price': tickers.get('ETH', 3000),
                'sol_price': tickers.get('SOL', 130),
                'fear_greed': sentiment.get('fear_greed', 50),
                'timestamp': datetime.now().isoformat()
            }
        
        dream_results = {
            'timestamp': datetime.now().isoformat(),
            'base_state': live_data,
            'scenarios_dreamed': [],
            'key_insights': [],
            'prepared_responses': {}
        }
        
        # Dream through each scenario
        for scenario in self.DREAM_SCENARIOS:
            dream = self._simulate_scenario(live_data, scenario)
            dream_results['scenarios_dreamed'].append(dream)
            
            # Store decision for this scenario type
            if scenario['name'] not in self.dream_insights:
                self.dream_insights[scenario['name']] = []
            self.dream_insights[scenario['name']].append(dream['decision'])
        
        # Extract key insights from dreams
        dream_results['key_insights'] = self._extract_insights(dream_results['scenarios_dreamed'])
        
        # Prepare response playbook
        dream_results['prepared_responses'] = self._build_response_playbook(dream_results['scenarios_dreamed'])
        
        self.dream_log.append(dream_results)
        if len(self.dream_log) > 50:
            self.dream_log = self.dream_log[-50:]
        
        return dream_results
    
    def _simulate_scenario(self, live_data: Dict, scenario: Dict) -> Dict:
        """Simulate a single scenario and make a decision."""
        
        # Apply scenario deltas to create hypothetical state
        hypothetical = {
            'btc_price': live_data['btc_price'] * (1 + scenario['btc_delta']),
            'fear_greed': max(0, min(100, live_data['fear_greed'] + scenario['fng_delta'])),
            'scenario_name': scenario['name'],
            'description': scenario['description']
        }
        
        # Calculate price change
        price_change_pct = scenario['btc_delta'] * 100
        
        # Make decision based on hypothetical state
        decision = self._dream_decision(hypothetical, price_change_pct)
        
        return {
            'scenario': scenario['name'],
            'description': scenario['description'],
            'hypothetical_btc': hypothetical['btc_price'],
            'hypothetical_fng': hypothetical['fear_greed'],
            'price_change': price_change_pct,
            'decision': decision,
            'reasoning': self._dream_reasoning(hypothetical, decision)
        }
    
    def _dream_decision(self, state: Dict, price_change: float) -> str:
        """Make a decision in dream state."""
        fng = state['fear_greed']
        
        # Contrarian logic
        if fng < 20:
            if price_change < -5:
                return "ACCUMULATE_HEAVILY"  # Blood in streets
            else:
                return "ACCUMULATE"
        elif fng < 35:
            if price_change < 0:
                return "BUY_THE_DIP"
            else:
                return "HOLD_LONG"
        elif fng > 80:
            if price_change > 5:
                return "TAKE_PROFITS"
            else:
                return "REDUCE_EXPOSURE"
        elif fng > 65:
            if price_change > 0:
                return "SCALE_OUT"
            else:
                return "HOLD_CAUTIOUS"
        else:
            # Neutral zone
            if abs(price_change) > 7:
                return "WAIT_FOR_CLARITY"  # Big move without sentiment shift = manipulation
            else:
                return "MAINTAIN_POSITION"
    
    def _dream_reasoning(self, state: Dict, decision: str) -> str:
        """Generate reasoning for dream decision."""
        fng = state['fear_greed']
        
        reasonings = {
            "ACCUMULATE_HEAVILY": f"Extreme fear ({fng}) + crash = generational buy opportunity",
            "ACCUMULATE": f"Fear ({fng}) suggests smart money is loading",
            "BUY_THE_DIP": f"Fear ({fng}) on red candle = buy signal",
            "HOLD_LONG": f"Fear ({fng}) but price stable = accumulation phase",
            "TAKE_PROFITS": f"Extreme greed ({fng}) + pump = distribution imminent",
            "REDUCE_EXPOSURE": f"Greed ({fng}) = risk-off time",
            "SCALE_OUT": f"Greed ({fng}) on green = sell into strength",
            "HOLD_CAUTIOUS": f"Greed ({fng}) but pullback = watch for reversal",
            "WAIT_FOR_CLARITY": f"Big move without sentiment shift = possible manipulation",
            "MAINTAIN_POSITION": f"Neutral zone ({fng}) = no action needed",
        }
        
        return reasonings.get(decision, "Unknown reasoning")
    
    def _extract_insights(self, dreams: List[Dict]) -> List[str]:
        """Extract key insights from all dream scenarios."""
        insights = []
        
        # Count decision types
        decisions = [d['decision'] for d in dreams]
        
        # What's the dominant response?
        buy_signals = sum(1 for d in decisions if 'ACCUMULATE' in d or 'BUY' in d)
        sell_signals = sum(1 for d in decisions if 'PROFIT' in d or 'REDUCE' in d or 'SCALE' in d)
        
        if buy_signals > sell_signals + 2:
            insights.append("💭 DREAM INSIGHT: Most scenarios favor accumulation - contrarian long bias")
        elif sell_signals > buy_signals + 2:
            insights.append("💭 DREAM INSIGHT: Most scenarios favor de-risking - defensive mode")
        else:
            insights.append("💭 DREAM INSIGHT: Mixed signals across scenarios - stay nimble")
        
        # Check for black swan preparedness
        black_swan = next((d for d in dreams if d['scenario'] == 'BLACK_SWAN'), None)
        if black_swan:
            insights.append(f"💭 BLACK SWAN PREP: If 25% crash → {black_swan['decision']}")
        
        # Check for FOMO preparedness
        fomo = next((d for d in dreams if d['scenario'] == 'FOMO_SPIKE'), None)
        if fomo:
            insights.append(f"💭 FOMO PREP: If 8% pump → {fomo['decision']}")
        
        return insights
    
    def _build_response_playbook(self, dreams: List[Dict]) -> Dict:
        """Build a response playbook for quick decisions."""
        playbook = {}
        
        for dream in dreams:
            playbook[dream['scenario']] = {
                'action': dream['decision'],
                'trigger': dream['description'],
                'reasoning': dream['reasoning']
            }
        
        return playbook
    
    def get_prepared_response(self, current_change_pct: float, current_fng: int) -> Optional[Dict]:
        """
        Given current conditions, return the pre-dreamed response.
        This is "dream recall" - using prepared scenarios.
        """
        # Match current conditions to a scenario
        if current_change_pct < -20:
            scenario = "BLACK_SWAN"
        elif current_change_pct < -8:
            scenario = "FLASH_CRASH"
        elif current_change_pct < -5:
            scenario = "WHALE_DUMP"
        elif current_change_pct < -2:
            scenario = "SLOW_BLEED"
        elif current_change_pct > 12:
            scenario = "MOON_MISSION"
        elif current_change_pct > 6:
            scenario = "FOMO_SPIKE"
        elif current_change_pct > 3 and abs(current_fng - 50) < 10:
            scenario = "MANIPULATION_UP"
        elif current_change_pct < -3 and abs(current_fng - 50) < 10:
            scenario = "MANIPULATION_DOWN"
        else:
            scenario = "ACCUMULATION" if current_change_pct > 0 else "SLOW_BLEED"
        
        # Return pre-computed response
        if self.dream_log:
            latest_dream = self.dream_log[-1]
            return latest_dream.get('prepared_responses', {}).get(scenario)
        
        return None
    
    def get_dream_summary(self) -> str:
        """Get human-readable dream summary."""
        if not self.dream_log:
            return "💤 No dreams recorded yet."
        
        latest = self.dream_log[-1]
        
        lines = [
            "═" * 50,
            "💭 DREAM ENGINE SUMMARY",
            "═" * 50,
            f"Last Dream: {latest['timestamp']}",
            f"Base BTC: ${latest['base_state'].get('btc_price', 0):,.2f}",
            f"Base F&G: {latest['base_state'].get('fear_greed', 50)}",
            "",
            "Scenarios Dreamed:",
        ]
        
        for dream in latest['scenarios_dreamed'][:5]:  # Show top 5
            lines.append(f"  {dream['scenario']}: {dream['decision']}")
        
        lines.append("")
        lines.append("Key Insights:")
        for insight in latest['key_insights']:
            lines.append(f"  {insight}")
        
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 🔴 LIVE TICKER STREAM - Continuous Market Monitoring
# ═══════════════════════════════════════════════════════════════

class LiveTickerStream:
    """
    Continuously monitors live market data and triggers brain responses.
    This is the "awake" state - always watching, always thinking.
    """
    
    # Network timeout (connect, read) - shorter to prevent Windows hangs
    TIMEOUT = (3.05, 5)  # (connect_timeout, read_timeout)
    
    def __init__(self):
        self.session = requests.Session()
        # Set default timeout at session level
        self.session.request = lambda method, url, **kwargs: requests.Session.request(
            self.session, method, url, timeout=kwargs.pop('timeout', self.TIMEOUT), **kwargs
        )
        self.last_prices: Dict[str, float] = {}
        self.price_history: Dict[str, deque] = {}
        self.alerts: List[Dict] = []
        self._network_available = True  # Track if network is working
        
    # Full market symbol list for comprehensive monitoring
    LIVE_SYMBOLS = [
        # Majors
        ("BTCUSDT", "BTC"), ("ETHUSDT", "ETH"), ("BNBUSDT", "BNB"),
        ("XRPUSDT", "XRP"), ("SOLUSDT", "SOL"), ("ADAUSDT", "ADA"),
        # Meme (Sentiment)
        ("DOGEUSDT", "DOGE"), ("SHIBUSDT", "SHIB"), ("PEPEUSDT", "PEPE"),
        ("FLOKIUSDT", "FLOKI"), ("BONKUSDT", "BONK"), ("WIFUSDT", "WIF"),
        # L1s
        ("AVAXUSDT", "AVAX"), ("DOTUSDT", "DOT"), ("MATICUSDT", "MATIC"),
        ("ATOMUSDT", "ATOM"), ("NEARUSDT", "NEAR"), ("FTMUSDT", "FTM"),
        ("APTUSDT", "APT"), ("SUIUSDT", "SUI"), ("SEIUSDT", "SEI"), ("INJUSDT", "INJ"),
        # DeFi
        ("LINKUSDT", "LINK"), ("UNIUSDT", "UNI"), ("AAVEUSDT", "AAVE"),
        ("MKRUSDT", "MKR"), ("CRVUSDT", "CRV"), ("LDOUSDT", "LDO"),
        # AI & Gaming
        ("FETUSDT", "FET"), ("RNDRUSDT", "RNDR"), ("AGIXUSDT", "AGIX"),
        ("IMXUSDT", "IMX"), ("GALAUSDT", "GALA"), ("AXSUSDT", "AXS"),
        # High Beta
        ("ORDIUSDT", "ORDI"), ("STXUSDT", "STX"), ("TIAUSDT", "TIA"),
        ("OPUSDT", "OP"), ("ARBUSDT", "ARB"),
        # Legacy
        ("LTCUSDT", "LTC"), ("BCHUSDT", "BCH"), ("ETCUSDT", "ETC"),
    ]
    
    def get_live_snapshot(self) -> Dict:
        """Get comprehensive market snapshot with all major assets."""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'tickers': {},
            'sentiment': {},
            'changes': {},
            'sectors': {},
            'breadth': {}
        }
        
        # Skip if network was previously unavailable (retry every 5 calls)
        if not self._network_available:
            self._network_retry_count = getattr(self, '_network_retry_count', 0) + 1
            if self._network_retry_count < 5:
                return snapshot
            self._network_retry_count = 0
            self._network_available = True  # Retry
        
        # Fetch ALL tickers in one efficient API call
        try:
            resp = self.session.get(
                "https://api.binance.com/api/v3/ticker/24hr",
                timeout=self.TIMEOUT
            )
            if resp.status_code == 200:
                all_tickers = {t['symbol']: t for t in resp.json()}
                
                for binance_sym, sym in self.LIVE_SYMBOLS:
                    if binance_sym in all_tickers:
                        data = all_tickers[binance_sym]
                        price = float(data.get('lastPrice', 0))
                        change_24h = float(data.get('priceChangePercent', 0))
                        volume = float(data.get('quoteVolume', 0))
                        
                        snapshot['tickers'][sym] = {
                            'price': price,
                            'change_24h': change_24h,
                            'volume': volume,
                            'high_24h': float(data.get('highPrice', 0)),
                            'low_24h': float(data.get('lowPrice', 0)),
                            'trades': int(data.get('count', 0)),
                        }
                        
                        # Track price history
                        if sym not in self.price_history:
                            self.price_history[sym] = deque(maxlen=60)
                        self.price_history[sym].append({
                            'price': price,
                            'time': datetime.now().isoformat()
                        })
                        
                        # Calculate instant change
                        if sym in self.last_prices:
                            instant_change = ((price - self.last_prices[sym]) / self.last_prices[sym]) * 100
                            snapshot['changes'][sym] = instant_change
                        
                        self.last_prices[sym] = price
                
                # Calculate sector performance
                snapshot['sectors'] = self._calculate_sector_performance(snapshot['tickers'])
                snapshot['breadth'] = self._calculate_market_breadth(snapshot['tickers'])
                
        except requests.exceptions.Timeout:
            logger.warning("Network timeout fetching tickers - marking network unavailable")
            self._network_available = False
        except requests.exceptions.ConnectionError:
            logger.warning("Network connection error - marking network unavailable")
            self._network_available = False
        except Exception as e:
            logger.debug(f"Bulk ticker fetch error: {e}")
            # Fallback to individual requests for critical assets only if not a connection issue
            if self._network_available:
                for binance_sym, sym in self.LIVE_SYMBOLS[:3]:  # Only top 3 to reduce hang risk
                    try:
                        resp = self.session.get(
                            f"https://api.binance.com/api/v3/ticker/24hr?symbol={binance_sym}",
                            timeout=(2, 3)  # Even shorter for fallback
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            snapshot['tickers'][sym] = {
                                'price': float(data.get('lastPrice', 0)),
                                'change_24h': float(data.get('priceChangePercent', 0)),
                                'volume': float(data.get('quoteVolume', 0))
                            }
                    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                        logger.warning(f"Network issue for {sym} - skipping remaining")
                        self._network_available = False
                        break
                    except Exception as e:
                        logger.debug(f"Ticker fetch error for {sym}: {e}")
        
        # Fetch sentiment (skip if network unavailable)
        if self._network_available:
            try:
                resp = self.session.get("https://api.alternative.me/fng/?limit=1", timeout=(2, 3))
                if resp.status_code == 200:
                    fng_data = resp.json().get('data', [{}])[0]
                    snapshot['sentiment'] = {
                        'fear_greed': int(fng_data.get('value', 50)),
                        'classification': fng_data.get('value_classification', 'Neutral')
                    }
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                self._network_available = False
                snapshot['sentiment'] = {'fear_greed': 50, 'classification': 'Neutral (offline)'}
            except:
                snapshot['sentiment'] = {'fear_greed': 50, 'classification': 'Neutral'}
        else:
            snapshot['sentiment'] = {'fear_greed': 50, 'classification': 'Neutral (offline)'}
        
        return snapshot
    
    def _calculate_sector_performance(self, tickers: Dict) -> Dict:
        """Calculate performance by market sector."""
        sectors = {
            'majors': ['BTC', 'ETH', 'BNB', 'XRP', 'SOL', 'ADA'],
            'meme': ['DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF'],
            'layer1': ['AVAX', 'DOT', 'MATIC', 'ATOM', 'NEAR', 'FTM', 'APT', 'SUI', 'SEI', 'INJ'],
            'defi': ['LINK', 'UNI', 'AAVE', 'MKR', 'CRV', 'LDO'],
            'ai_gaming': ['FET', 'RNDR', 'AGIX', 'IMX', 'GALA', 'AXS'],
            'high_beta': ['ORDI', 'STX', 'TIA', 'OP', 'ARB'],
            'legacy': ['LTC', 'BCH', 'ETC'],
        }
        
        sector_data = {}
        for sector_name, symbols in sectors.items():
            changes = []
            volumes = []
            for sym in symbols:
                if sym in tickers and isinstance(tickers[sym], dict):
                    changes.append(tickers[sym].get('change_24h', 0))
                    volumes.append(tickers[sym].get('volume', 0))
            
            if changes:
                sector_data[sector_name] = {
                    'avg_change': sum(changes) / len(changes),
                    'total_volume': sum(volumes),
                    'assets_tracked': len(changes),
                    'bullish_pct': sum(1 for c in changes if c > 0) / len(changes) * 100,
                }
        
        return sector_data
    
    def _calculate_market_breadth(self, tickers: Dict) -> Dict:
        """Calculate overall market breadth - up vs down ratio."""
        if not tickers:
            import logging
            logging.getLogger(__name__).warning(
                "[insufficient-data] _calculate_market_breadth: no tickers "
                "passed; returning neutral 0.5 with no_real_data=True"
            )
            return {'breadth': 0.5, 'status': 'UNKNOWN', 'no_real_data': True}

        changes = [t.get('change_24h', 0) for t in tickers.values() if isinstance(t, dict)]
        if not changes:
            import logging
            logging.getLogger(__name__).warning(
                "[insufficient-data] _calculate_market_breadth: tickers had "
                "no change_24h fields; returning neutral 0.5 with no_real_data=True"
            )
            return {'breadth': 0.5, 'status': 'UNKNOWN', 'no_real_data': True}
        
        up = sum(1 for c in changes if c > 0)
        down = sum(1 for c in changes if c < 0)
        total = len(changes)
        
        breadth = up / total if total > 0 else 0.5
        
        return {
            'breadth': breadth,
            'up_count': up,
            'down_count': down,
            'total': total,
            'status': 'STRONG_BULL' if breadth > 0.75 else 'BULL' if breadth > 0.55 else 'NEUTRAL' if breadth > 0.45 else 'BEAR' if breadth > 0.25 else 'STRONG_BEAR'
        }
    
    def detect_significant_moves(self, snapshot: Dict) -> List[Dict]:
        """Detect significant price movements that require attention."""
        alerts = []
        
        for sym, change in snapshot.get('changes', {}).items():
            if abs(change) > 0.5:  # > 0.5% instant move
                alert = {
                    'symbol': sym,
                    'change_pct': change,
                    'direction': 'UP' if change > 0 else 'DOWN',
                    'severity': 'HIGH' if abs(change) > 1.5 else 'MEDIUM',
                    'timestamp': datetime.now().isoformat()
                }
                alerts.append(alert)
                
        return alerts
    
    def get_market_pulse(self) -> Dict:
        """Get overall market pulse from all tickers."""
        snapshot = self.get_live_snapshot()
        
        # Always return a complete dict with all expected keys
        if not snapshot['tickers']:
            return {
                'pulse': 'UNKNOWN',
                'strength': 0,
                'avg_change_24h': 0.0,
                'fear_greed': snapshot.get('sentiment', {}).get('fear_greed', 50),
                'btc_price': 0.0,
                'snapshot': snapshot
            }
        
        # Calculate average 24h change
        changes = [t['change_24h'] for t in snapshot['tickers'].values()]
        avg_change = sum(changes) / len(changes)
        
        # Determine pulse
        if avg_change > 5:
            pulse = "STRONG_BULL"
        elif avg_change > 2:
            pulse = "BULL"
        elif avg_change > 0:
            pulse = "MILD_BULL"
        elif avg_change > -2:
            pulse = "MILD_BEAR"
        elif avg_change > -5:
            pulse = "BEAR"
        else:
            pulse = "STRONG_BEAR"
        
        return {
            'pulse': pulse,
            'avg_change_24h': avg_change,
            'fear_greed': snapshot.get('sentiment', {}).get('fear_greed', 50),
            'btc_price': snapshot.get('tickers', {}).get('BTC', {}).get('price', 0),
            'snapshot': snapshot
        }


# ═══════════════════════════════════════════════════════════════
# 🎭 TRUTH COUNCIL - The Internal Debate System
# ═══════════════════════════════════════════════════════════════

@dataclass
class Advisor:
    """An internal advisor with a specific perspective."""
    name: str
    role: str
    bias: str  # "bullish", "bearish", "skeptic", "optimist"
    weight: float = 1.0
    
    def evaluate(self, data: Dict, context: str) -> Tuple[str, float, str]:
        """
        Evaluate data from this advisor's perspective.
        Returns: (verdict, confidence, reasoning)
        """
        # Each advisor has unique evaluation logic
        if self.bias == "skeptic":
            return self._skeptic_eval(data, context)
        elif self.bias == "bullish":
            return self._bullish_eval(data, context)
        elif self.bias == "bearish":
            return self._bearish_eval(data, context)
        elif self.bias == "harvester":
            return self._harvester_eval(data, context)
        else:
            return self._neutral_eval(data, context)
    
    def _harvester_eval(self, data: Dict, context: str) -> Tuple[str, float, str]:
        """The Harvester cares only about Net Profit."""
        # Penny Profit Logic: We don't need home runs, just base hits.
        # If market is choppy, we harvest. If market is trending, we harvest.
        
        fng = data.get("fear_greed", 50)
        mcap_change = data.get("mcap_change", 0)
        
        # In high volatility, harvesting is safer than holding
        if abs(mcap_change) > 3:
            return ("HARVEST_NOW", 0.9, f"High volatility ({mcap_change:.1f}%) favors quick penny profits over long holds.")
            
        # In extreme fear, we harvest to protect capital
        if fng < 20:
            return ("PROTECT_CAPITAL", 0.8, "Extreme fear. Take any profit available, even pennies.")
            
        # In extreme greed, we harvest to lock in gains
        if fng > 80:
            return ("LOCK_GAINS", 0.8, "Extreme greed. Don't be a pig. Harvest the pennies.")
            
        return ("ACCUMULATE_VALUE", 0.6, "Conditions stable. Seek value, but be ready to harvest at $0.01 profit.")

    def _skeptic_eval(self, data: Dict, context: str) -> Tuple[str, float, str]:
        """The Skeptic questions everything."""
        # Look for manipulation signals
        fng = data.get("fear_greed", 50)
        mcap_change = data.get("mcap_change", 0)
        
        # Extreme readings are suspicious
        if fng < 20 or fng > 80:
            return ("SUSPICIOUS", 0.7, f"Extreme Fear/Greed ({fng}) often precedes reversals. Possible manipulation.")
        
        # Divergence between sentiment and price action
        if (fng < 30 and mcap_change > 2) or (fng > 70 and mcap_change < -2):
            return ("SPOOF_DETECTED", 0.85, f"Sentiment ({fng}) diverges from price action ({mcap_change:.1f}%). Smart money misdirection?")
        
        return ("PLAUSIBLE", 0.5, "Data appears consistent, but remain vigilant.")
    
    def _bullish_eval(self, data: Dict, context: str) -> Tuple[str, float, str]:
        """The Bull sees opportunity."""
        fng = data.get("fear_greed", 50)
        mcap_change = data.get("mcap_change", 0)
        btc_dom = data.get("btc_dominance", 50)
        
        if fng < 25:
            return ("OPPORTUNITY", 0.8, f"Extreme fear ({fng}) = blood in streets. Time to be greedy!")
        if mcap_change > 1 and btc_dom < 55:
            return ("ALT_SEASON", 0.7, f"Market expanding ({mcap_change:.1f}%) with low BTC dom ({btc_dom:.1f}%). Alts ready to run!")
        
        return ("NEUTRAL", 0.4, "No clear bullish signal yet.")
    
    def _bearish_eval(self, data: Dict, context: str) -> Tuple[str, float, str]:
        """The Bear sees danger."""
        fng = data.get("fear_greed", 50)
        mcap_change = data.get("mcap_change", 0)
        
        if fng > 75:
            return ("DANGER", 0.8, f"Extreme greed ({fng}) = complacency. Crash incoming!")
        if mcap_change < -2:
            return ("CAPITULATION", 0.6, f"Market bleeding ({mcap_change:.1f}%). More pain ahead.")
        
        return ("CAUTIOUS", 0.5, "Stay defensive.")
    
    def _neutral_eval(self, data: Dict, context: str) -> Tuple[str, float, str]:
        """The Analyst weighs both sides."""
        fng = data.get("fear_greed", 50)
        return ("BALANCED", 0.5, f"Fear/Greed at {fng} suggests equilibrium. Watch for catalyst.")


class TruthCouncil:
    """
    Internal council of advisors that debate the truth.
    "Is this data real or is someone trying to fool us?"
    """
    
    def __init__(self):
        self.advisors = [
            Advisor("The Skeptic", "Chief BS Detector", "skeptic", weight=1.5),
            Advisor("The Bull", "Opportunity Finder", "bullish", weight=1.0),
            Advisor("The Bear", "Risk Manager", "bearish", weight=1.0),
            Advisor("The Oracle", "Pattern Reader", "neutral", weight=1.2),
            Advisor("The Harvester", "Profit Reaper", "harvester", weight=1.4), # High weight for Penny Profit
        ]
        self.debate_history: List[Dict] = []
    
    def convene(self, data: Dict, context: str = "market_analysis") -> Dict[str, Any]:
        """
        Convene the council to debate the data.
        Returns a synthesis of all perspectives.
        """
        logger.info("🎭 Truth Council convening...")
        
        votes = []
        arguments = []
        
        for advisor in self.advisors:
            verdict, confidence, reasoning = advisor.evaluate(data, context)
            vote = {
                "advisor": advisor.name,
                "role": advisor.role,
                "verdict": verdict,
                "confidence": confidence,
                "reasoning": reasoning,
                "weight": advisor.weight
            }
            votes.append(vote)
            arguments.append(f"   [{advisor.name}] ({verdict}, {confidence:.0%}): {reasoning}")
            logger.info(f"   🗣️ {advisor.name}: {verdict} ({confidence:.0%})")
        
        # Calculate weighted consensus
        truth_score = 0
        spoof_score = 0
        total_weight = sum(v["weight"] for v in votes)
        
        for vote in votes:
            w = vote["weight"] / total_weight
            if vote["verdict"] in ["SUSPICIOUS", "SPOOF_DETECTED", "DANGER"]:
                spoof_score += vote["confidence"] * w
            elif vote["verdict"] in ["PLAUSIBLE", "OPPORTUNITY", "ALT_SEASON", "BALANCED", "HARVEST_NOW", "LOCK_GAINS", "ACCUMULATE_VALUE"]:
                truth_score += vote["confidence"] * w
            else:
                truth_score += 0.5 * w
        
        # Final verdict
        if spoof_score > 0.6:
            consensus = "HIGH_MANIPULATION_RISK"
            action = "VERIFY_INDEPENDENTLY"
        elif truth_score > 0.7:
            consensus = "DATA_APPEARS_VALID"
            action = "PROCEED_WITH_CONFIDENCE"
        else:
            consensus = "INCONCLUSIVE"
            action = "GATHER_MORE_DATA"
        
        result = {
            "consensus": consensus,
            "action": action,
            "truth_score": truth_score,
            "spoof_score": spoof_score,
            "votes": votes,
            "arguments": arguments,
            "timestamp": datetime.now().isoformat()
        }
        
        self.debate_history.append(result)
        return result


# ═══════════════════════════════════════════════════════════════
# 🔍 SKEPTICAL ANALYZER - The BS Detector
# ═══════════════════════════════════════════════════════════════

class SkepticalAnalyzer:
    """
    "Don't believe everything you read on the internet."
    Cross-references data sources to detect manipulation.
    """
    
    def __init__(self):
        self.historical_readings: deque = deque(maxlen=100)
        self.anomaly_threshold = 2.0  # Standard deviations
    
    def analyze(self, current_data: Dict) -> Dict[str, Any]:
        """
        Analyze data for signs of manipulation or spoofing.
        """
        logger.info("🔍 Skeptical Analyzer scanning for BS...")
        
        analysis = {
            "anomalies": [],
            "red_flags": [],
            "green_flags": [],
            "manipulation_probability": 0.0
        }
        
        fng = current_data.get("fear_greed", 50)
        mcap_change = current_data.get("mcap_change", 0)
        btc_dom = current_data.get("btc_dominance", 50)
        
        # Check 1: Extreme Fear/Greed often manufactured
        if fng < 15 or fng > 85:
            analysis["red_flags"].append(f"EXTREME sentiment ({fng}) - possible emotional manipulation")
            analysis["manipulation_probability"] += 0.2
        
        # Check 2: Sudden sentiment shifts without news
        if self.historical_readings:
            last = self.historical_readings[-1]
            fng_delta = abs(fng - last.get("fear_greed", 50))
            if fng_delta > 20:
                analysis["red_flags"].append(f"Sentiment swung {fng_delta} points - organic or orchestrated?")
                analysis["manipulation_probability"] += 0.15
        
        # Check 3: BTC dominance vs market cap divergence
        if btc_dom > 60 and mcap_change > 3:
            analysis["anomalies"].append("High BTC dominance with expanding market - altcoin capitulation?")
        elif btc_dom < 45 and mcap_change < -3:
            analysis["anomalies"].append("Low BTC dominance with contracting market - alt bloodbath")
        
        # Check 4: Weekend/off-hours manipulation
        now = datetime.now()
        if now.weekday() >= 5:  # Weekend
            analysis["red_flags"].append("Weekend trading - lower liquidity, easier to manipulate")
            analysis["manipulation_probability"] += 0.1
        
        # Green flags
        if 30 < fng < 70:
            analysis["green_flags"].append("Sentiment in normal range - less likely manipulated")
        if abs(mcap_change) < 2:
            analysis["green_flags"].append("Market cap stable - organic movement")
        
        # Cap probability
        analysis["manipulation_probability"] = min(0.95, analysis["manipulation_probability"])
        
        # Store for historical comparison
        self.historical_readings.append(current_data)
        
        return analysis


# ═══════════════════════════════════════════════════════════════
# 💭 SPECULATION ENGINE - "What Does This REALLY Mean?"
# ═══════════════════════════════════════════════════════════════

class SpeculationEngine:
    """
    Goes beyond the data to speculate on hidden meanings.
    "The chart says X, but smart money is doing Y..."
    """
    
    SPECULATION_TEMPLATES = [
        "If {condition}, then smart money is probably {action}.",
        "The {metric} reading of {value} suggests {implication}.",
        "Watch for {event} - it could trigger {outcome}.",
        "Retail sees {surface}, but institutions see {reality}.",
    ]
    
    def speculate(self, data: Dict, skeptic_analysis: Dict) -> List[str]:
        """
        Generate speculative insights based on data and analysis.
        """
        logger.info("💭 Speculation Engine thinking deeply...")
        
        speculations = []
        fng = data.get("fear_greed", 50)
        mcap_change = data.get("mcap_change", 0)
        btc_dom = data.get("btc_dominance", 50)
        manip_prob = skeptic_analysis.get("manipulation_probability", 0)
        
        # Speculation based on Fear/Greed
        if fng < 25:
            speculations.append(
                f"💭 SPECULATION: Extreme fear ({fng}) often marks bottoms. "
                f"If manipulation probability is {manip_prob:.0%}, this could be "
                f"{'manufactured panic for accumulation' if manip_prob > 0.3 else 'genuine capitulation'}."
            )
        elif fng > 75:
            speculations.append(
                f"💭 SPECULATION: Extreme greed ({fng}) precedes corrections. "
                f"Smart money may be {'distributing into strength' if manip_prob > 0.3 else 'riding momentum'}."
            )
        
        # Speculation on dominance shifts
        if btc_dom > 55:
            speculations.append(
                f"💭 SPECULATION: BTC dominance at {btc_dom:.1f}% - "
                f"capital fleeing to safety OR coiling for alt season explosion?"
            )
        elif btc_dom < 45:
            speculations.append(
                f"💭 SPECULATION: Low BTC dominance ({btc_dom:.1f}%) - "
                f"alt season in full swing OR distribution before dump?"
            )
        
        # Meta-speculation on manipulation
        if manip_prob > 0.4:
            speculations.append(
                f"💭 META-SPECULATION: High manipulation probability ({manip_prob:.0%}). "
                f"Ask yourself: Who benefits from this narrative? Follow the money."
            )
        
        # Contrarian speculation
        speculations.append(
            f"💭 CONTRARIAN VIEW: Whatever the crowd believes ({self._crowd_belief(fng)}), "
            f"consider the opposite. The market rewards independent thinking."
        )
        
        return speculations
    
    def _crowd_belief(self, fng: int) -> str:
        if fng < 30:
            return "it's going to zero"
        elif fng > 70:
            return "it's going to the moon"
        else:
            return "nothing will happen"


# ═══════════════════════════════════════════════════════════════
# 🌐 WEB KNOWLEDGE MINER (Enhanced)
# ═══════════════════════════════════════════════════════════════

class WebKnowledgeMiner:
    """
    Searches and retrieves financial metadata from multiple sources.
    Now with cross-validation capabilities and timeout protection.
    """
    
    # Network timeout (connect, read) - shorter to prevent Windows hangs
    TIMEOUT = (3.05, 5)
    
    SOURCES = [
        {"name": "CoinGecko Global", "url": "https://api.coingecko.com/api/v3/global", "type": "json"},
        {"name": "Fear & Greed", "url": "https://api.alternative.me/fng/?limit=1", "type": "json"},
        {"name": "BTC Price (Binance)", "url": "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", "type": "json"},
        {"name": "ETH Price (Binance)", "url": "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT", "type": "json"},
    ]

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'AureonMinerBrain/2.0'})
        self._network_available = True

    def gather_intelligence(self) -> Dict[str, Any]:
        """Scours sources for metadata with cross-validation and timeout protection."""
        intelligence = {"raw": {}, "processed": {}}
        logger.info("🌐 Miner Brain searching the internet...")
        
        if not self._network_available:
            # Quick retry check
            self._network_retry_count = getattr(self, '_network_retry_count', 0) + 1
            if self._network_retry_count < 3:
                logger.info("   ⚠️ Network unavailable, using cached/default data")
                intelligence["processed"] = self._get_default_processed()
                return intelligence
            self._network_retry_count = 0
            self._network_available = True
        
        for source in self.SOURCES:
            try:
                response = self.session.get(source["url"], timeout=self.TIMEOUT)
                if response.status_code == 200:
                    intelligence["raw"][source["name"]] = response.json()
                    logger.info(f"   [OK] {source['name']}")
                else:
                    logger.warning(f"   [!] {source['name']}: {response.status_code}")
            except requests.exceptions.Timeout:
                logger.warning(f"   [TIMEOUT] {source['name']} - marking network slow")
            except requests.exceptions.ConnectionError:
                logger.warning(f"   [CONN ERR] {source['name']} - network may be unavailable")
                self._network_available = False
            except Exception as e:
                logger.error(f"   [!] {source['name']}: {e}")
        
        # Process into unified format
        intelligence["processed"] = self._process_raw(intelligence["raw"])
        return intelligence
    
    def _get_default_processed(self) -> Dict:
        """Return default values when network is unavailable."""
        return {
            "fear_greed": 50,
            "fng_class": "Neutral (offline)",
            "mcap_change": 0,
            "btc_dominance": 50,
            "eth_dominance": 15,
            "btc_price": 0,
            "eth_price": 0
        }
    
    def _process_raw(self, raw: Dict) -> Dict:
        """Extract key metrics into a clean format."""
        processed = {}
        
        # Fear & Greed
        fng_data = raw.get("Fear & Greed", {}).get("data", [{}])[0]
        processed["fear_greed"] = int(fng_data.get("value", 50))
        processed["fng_class"] = fng_data.get("value_classification", "Unknown")
        
        # Global Market
        global_data = raw.get("CoinGecko Global", {}).get("data", {})
        processed["mcap_change"] = global_data.get("market_cap_change_percentage_24h_usd", 0)
        processed["btc_dominance"] = global_data.get("market_cap_percentage", {}).get("btc", 50)
        processed["eth_dominance"] = global_data.get("market_cap_percentage", {}).get("eth", 15)
        
        # Prices
        processed["btc_price"] = float(raw.get("BTC Price (Binance)", {}).get("price", 0))
        processed["eth_price"] = float(raw.get("ETH Price (Binance)", {}).get("price", 0))
        
        return processed


# ═══════════════════════════════════════════════════════════════
# 🧠 WISDOM COGNITION ENGINE - Unified Ancient Wisdom Integration
# All civilizations united for market cognition
# ═══════════════════════════════════════════════════════════════

class WisdomCognitionEngine:
    """
    The Unified Wisdom Cognition Engine.
    
    Integrates all ancient wisdom libraries into a single cognitive framework
    for market analysis and decision making.
    
    Libraries integrated:
    - StrategicWarfareLibrary (Sun Tzu, IRA tactics)
    - CelticWisdomLibrary (Stars, Frequencies, Druids)
    - AztecWisdomLibrary (Tonalpohualli, Teotl, Five Suns)
    - MogollonWisdomLibrary (Mimbres, Pit House, Desert)
    - PlantagenetWisdomLibrary (Kings, Magna Carta, Wars)
    - EgyptianWisdomLibrary (Netjeru, Ma'at, Pyramids)
    - PythagoreanWisdomLibrary (Sacred Numbers, Musica Universalis)
    
    NEW: Now also loads dynamic wisdom from JSON files scanned by WisdomScanner
    - Chinese (I Ching, Taoism, Five Elements)
    - Hindu (Vedic Astrology, Yoga, Chakras)
    - Mayan (Tzolkin, Haab, Long Count)
    - Norse (Runes, Wyrd, Nine Worlds)
    
    "From the stars to the numbers, all is one." - The Unified Mind
    """
    
    def __init__(self):
        """Initialize all wisdom libraries."""
        self.warfare = StrategicWarfareLibrary()
        self.celtic = CelticWisdomLibrary()
        self.aztec = AztecWisdomLibrary()
        self.mogollon = MogollonWisdomLibrary()
        self.plantagenet = PlantagenetWisdomLibrary()
        self.egyptian = EgyptianWisdomLibrary()
        self.pythagorean = PythagoreanWisdomLibrary()
        
        # Dynamic wisdom loader for scanned content
        self.json_wisdom = get_wisdom_loader()
        
        # Civilizations represented (original 7)
        self.civilizations = [
            {"name": "Celtic", "era": "800 BCE - 400 CE", "region": "Europe", "glyph": "☘️"},
            {"name": "Aztec", "era": "1300 - 1521 CE", "region": "Mesoamerica", "glyph": "🦅"},
            {"name": "Mogollon", "era": "200 - 1450 CE", "region": "North America", "glyph": "🏺"},
            {"name": "Plantagenet", "era": "1154 - 1485 CE", "region": "England", "glyph": "👑"},
            {"name": "Egyptian", "era": "3100 - 30 BCE", "region": "North Africa", "glyph": "☥"},
            {"name": "Pythagorean", "era": "570 - 495 BCE", "region": "Greece/Italy", "glyph": "🔢"},
            {"name": "Warfare (Sun Tzu)", "era": "544 - 496 BCE", "region": "China", "glyph": "⚔️"},
        ]
        
        # Extended civilizations from JSON scanner (4 more = 11 total!)
        self.extended_civilizations = [
            {"name": "Chinese", "era": "2000 BCE - present", "region": "East Asia", "glyph": "☯️", "source": "json"},
            {"name": "Hindu", "era": "1500 BCE - present", "region": "South Asia", "glyph": "🕉️", "source": "json"},
            {"name": "Mayan", "era": "2000 BCE - 1500 CE", "region": "Mesoamerica", "glyph": "🌀", "source": "json"},
            {"name": "Norse", "era": "800 - 1100 CE", "region": "Scandinavia", "glyph": "ᚱ", "source": "json"},
        ]
        
        # ALL 11 CIVILIZATIONS COMBINED
        self.all_civilizations = self.civilizations + self.extended_civilizations
        
        # Total wisdom metrics
        self.wisdom_stats = self._calculate_wisdom_stats()
    
    def _calculate_wisdom_stats(self) -> Dict:
        """Calculate total wisdom data points from ALL 11 CIVILIZATIONS."""
        return {
            "total_civilizations": len(self.all_civilizations),  # 11!
            "original_civilizations": len(self.civilizations),   # 7
            "extended_civilizations": len(self.extended_civilizations),  # 4
            "total_years_of_wisdom": 5000,  # Spanning from Egypt to present
            "warfare_principles": len(self.warfare.SUN_TZU_PRINCIPLES) + len(self.warfare.IRA_GUERRILLA_PRINCIPLES),
            "celtic_data_points": (
                len(self.celtic.CELTIC_STARS) + 
                len(self.celtic.SACRED_FREQUENCIES) + 
                len(self.celtic.DRUIDIC_TREES) +
                len(self.celtic.CELTIC_TRIADS)
            ),
            "aztec_data_points": (
                len(self.aztec.TONALPOHUALLI_SIGNS) + 
                len(self.aztec.TEOTL) + 
                len(self.aztec.FIVE_SUNS) +
                len(self.aztec.HUEHUEHTLAHTOLLI)
            ),
            "mogollon_data_points": (
                len(self.mogollon.MIMBRES_SYMBOLS) + 
                len(self.mogollon.PIT_HOUSE_WISDOM) + 
                len(self.mogollon.PROVERBS)
            ),
            "plantagenet_data_points": (
                len(self.plantagenet.KINGS) + 
                len(self.plantagenet.MAGNA_CARTA) + 
                len(self.plantagenet.HUNDRED_YEARS_WAR) +
                len(self.plantagenet.WARS_OF_ROSES)
            ),
            "egyptian_data_points": (
                len(self.egyptian.NETJERU) + 
                len(self.egyptian.LAWS_OF_MAAT) + 
                len(self.egyptian.PHARAOHS) +
                len(self.egyptian.PROVERBS)
            ),
            "pythagorean_data_points": (
                len(self.pythagorean.SACRED_NUMBERS) + 
                len(self.pythagorean.SACRED_RATIOS) + 
                len(self.pythagorean.PLANETARY_HARMONICS) +
                len(self.pythagorean.PLATONIC_SOLIDS) +
                len(self.pythagorean.MAXIMS)
            ),
            # Dynamic JSON wisdom counts
            "json_wisdom_topics": self._count_json_wisdom_topics()
        }
    
    def _count_json_wisdom_topics(self) -> int:
        """Count total topics from JSON wisdom files."""
        total = 0
        for civ_name in self.json_wisdom.CIVILIZATION_FILES.keys():
            wisdom = self.json_wisdom.get_wisdom(civ_name)
            total += len(wisdom.get('topics', []))
        return total
    
    def get_dynamic_wisdom(self, market_context: str = "") -> Dict[str, List[Dict]]:
        """
        Get dynamic wisdom from JSON files for all extended civilizations.
        
        Args:
            market_context: Market state like "volatile", "trending", "bullish"
        
        Returns:
            Dict mapping civilization name to relevant wisdom topics
        """
        dynamic = {}
        
        for civ in self.extended_civilizations:
            civ_name = civ["name"].lower()
            relevant = self.json_wisdom.get_relevant_wisdom(civ_name, market_context)
            if relevant:
                dynamic[civ["name"]] = relevant
        
        return dynamic
    
    def get_cross_cultural_pattern(self, pattern: str) -> str:
        """
        Find a universal pattern across multiple civilizations.
        Useful for identifying consensus wisdom.
        
        Args:
            pattern: Pattern type like "cycles", "balance", "transformation"
        
        Returns:
            Synthesized insight from multiple civilizations
        """
        patterns = self.json_wisdom.get_cross_civilization_patterns(pattern)
        
        if not patterns:
            return f"No cross-cultural patterns found for '{pattern}'"
        
        # Synthesize insights
        insights = []
        for civ, civ_insights in patterns.items():
            if civ_insights:
                insights.append(f"{civ.title()}: {civ_insights[0][:100]}...")
        
        if len(insights) >= 2:
            return f"UNIVERSAL PATTERN ({pattern}): " + " | ".join(insights[:3])
        return insights[0] if insights else "No pattern found"
    
    def get_unified_reading(self, fear_greed: int, btc_price: float, btc_change: float) -> Dict:
        """
        Get a unified wisdom reading from ALL 11 CIVILIZATIONS.
        This is the master cognition function.
        
        🧠 11 CIVILIZATIONS UNITE:
        ├─ Original 7 (hardcoded libraries):
        │   ☘️ Celtic, 🦅 Aztec, 🏺 Mogollon, 👑 Plantagenet
        │   ☥ Egyptian, 🔢 Pythagorean, ⚔️ Warfare (Sun Tzu)
        └─ Extended 4 (JSON wisdom scanner):
            ☯️ Chinese, 🕉️ Hindu, 🌀 Mayan, ᚱ Norse
        """
        # Get readings from all 7 hardcoded libraries
        celtic_reading = self.celtic.get_full_celtic_reading(fear_greed, btc_price, btc_change)
        aztec_reading = self.aztec.get_full_aztec_reading(fear_greed, btc_price, btc_change)
        mogollon_reading = self.mogollon.get_full_mogollon_reading(fear_greed, btc_price, btc_change)
        plantagenet_reading = self.plantagenet.get_full_plantagenet_reading(fear_greed, btc_price, btc_change)
        egyptian_reading = self.egyptian.get_full_egyptian_reading(fear_greed, btc_price, btc_change)
        pythagorean_reading = self.pythagorean.get_full_pythagorean_reading(fear_greed, btc_price, btc_change)
        warfare_reading = self.warfare.get_warfare_reading(fear_greed, btc_price, btc_change)
        
        # Get market context for extended civilizations
        market_context = self._determine_market_context(fear_greed, btc_change)
        
        # Collect actions from original 7
        actions = self._collect_actions(
            celtic_reading, aztec_reading, mogollon_reading,
            plantagenet_reading, egyptian_reading, pythagorean_reading,
            warfare_reading, fear_greed
        )
        
        # 🆕 Get dynamic wisdom from JSON for extended 4 civilizations
        dynamic_wisdom = self.get_dynamic_wisdom(market_context)
        extended_actions = self._extract_extended_civilization_actions(dynamic_wisdom, fear_greed, btc_change)
        
        # Merge all 11 civilization actions!
        all_actions = {**actions, **extended_actions}
        
        # Determine consensus from ALL 11 CIVILIZATIONS
        consensus = self._determine_consensus(all_actions)
        
        # Generate unified synthesis (enhanced for 11 civs)
        synthesis = self._generate_unified_synthesis_11(
            consensus, fear_greed, btc_change,
            celtic_reading, aztec_reading, pythagorean_reading, egyptian_reading,
            mogollon_reading, plantagenet_reading, warfare_reading,
            extended_actions
        )
        
        # Map actions to civilization names for the Quantum Brain bridge (all 11!)
        civilization_actions = {
            "Celtic": actions.get("celtic", "HOLD"),
            "Aztec": actions.get("aztec", "HOLD"),
            "Mogollon": actions.get("mogollon", "HOLD"),
            "Plantagenet": actions.get("plantagenet", "HOLD"),
            "Egyptian": actions.get("egyptian", "HOLD"),
            "Pythagorean": actions.get("pythagorean", "HOLD"),
            "Warfare": actions.get("warfare", "HOLD"),
            # Extended 4 civilizations
            "Chinese": extended_actions.get("chinese", "HOLD"),
            "Hindu": extended_actions.get("hindu", "HOLD"),
            "Mayan": extended_actions.get("mayan", "HOLD"),
            "Norse": extended_actions.get("norse", "HOLD"),
        }
        
        # Get cross-cultural pattern for current conditions
        pattern_type = "volatile" if abs(btc_change) > 3 else "cycles"
        cross_pattern = self.get_cross_cultural_pattern(pattern_type)
        
        return {
            "celtic": celtic_reading,
            "aztec": aztec_reading,
            "mogollon": mogollon_reading,
            "plantagenet": plantagenet_reading,
            "egyptian": egyptian_reading,
            "pythagorean": pythagorean_reading,
            "warfare": warfare_reading,
            "consensus": consensus,
            "actions": all_actions,  # Now includes all 11!
            "civilization_actions": civilization_actions,  # For Quantum Brain bridge (all 11!)
            "synthesis": synthesis,
            "stats": self.wisdom_stats,
            # Extended civilizations data
            "dynamic_wisdom": dynamic_wisdom,
            "extended_actions": extended_actions,
            "cross_cultural_pattern": cross_pattern,
            "extended_civilizations_active": len(dynamic_wisdom),
            "total_civilizations": 7 + len(extended_actions)  # Up to 11!
        }
    
    def _extract_extended_civilization_actions(self, dynamic_wisdom: Dict, fear_greed: int, btc_change: float) -> Dict:
        """
        Extract trading actions from extended civilizations (Chinese, Hindu, Mayan, Norse).
        Uses wisdom from JSON files scanned by WisdomScanner.
        
        🆕 These 4 civilizations add their voice to the consensus!
        """
        extended_actions = {}
        
        # ☯️ CHINESE (I Ching, Taoism, Five Elements)
        if "Chinese" in dynamic_wisdom:
            extended_actions["chinese"] = self._extract_chinese_action(dynamic_wisdom["Chinese"], fear_greed, btc_change)
        
        # 🕉️ HINDU (Vedic Astrology, Yoga, Chakras)
        if "Hindu" in dynamic_wisdom:
            extended_actions["hindu"] = self._extract_hindu_action(dynamic_wisdom["Hindu"], fear_greed, btc_change)
        
        # 🌀 MAYAN (Tzolkin, Haab, Long Count)
        if "Mayan" in dynamic_wisdom:
            extended_actions["mayan"] = self._extract_mayan_action(dynamic_wisdom["Mayan"], fear_greed, btc_change)
        
        # ᚱ NORSE (Runes, Wyrd, Nine Worlds)
        if "Norse" in dynamic_wisdom:
            extended_actions["norse"] = self._extract_norse_action(dynamic_wisdom["Norse"], fear_greed, btc_change)
        
        return extended_actions
    
    def _extract_chinese_action(self, wisdom: List, fear_greed: int, btc_change: float) -> str:
        """Extract action from Chinese wisdom (I Ching, Taoism, Five Elements)."""
        # I Ching philosophy: balance of yin/yang
        if fear_greed < 25:  # Extreme fear = yin at maximum
            return "YIN_ACCUMULATE"  # Buy when others fear (yin transforms to yang)
        elif fear_greed > 75:  # Extreme greed = yang at maximum
            return "YANG_RELEASE"  # Sell when others are greedy (yang transforms to yin)
        elif abs(btc_change) > 5:  # Volatility
            return "WU_WEI"  # Non-action, let the Tao flow
        else:
            return "BALANCE"  # Maintain harmony
    
    def _extract_hindu_action(self, wisdom: List, fear_greed: int, btc_change: float) -> str:
        """Extract action from Hindu wisdom (Vedic, Chakras, Karma)."""
        # Vedic cycles and karma
        if fear_greed < 30:
            return "DHARMA_BUY"  # Righteous action in adversity
        elif fear_greed > 70:
            return "DETACHMENT"  # Non-attachment to gains
        elif btc_change > 3:
            return "EXPANSION"  # Brahman - cosmic expansion
        elif btc_change < -3:
            return "PRESERVATION"  # Vishnu - preserve what you have
        else:
            return "MEDITATION"  # Wait for clarity
    
    def _extract_mayan_action(self, wisdom: List, fear_greed: int, btc_change: float) -> str:
        """Extract action from Mayan wisdom (Tzolkin, Long Count, Cosmic cycles)."""
        # Mayan calendar cycles
        from datetime import datetime
        day_of_year = datetime.now().timetuple().tm_yday
        tzolkin_day = day_of_year % 20  # Simplified Tzolkin
        
        # Auspicious days for action (1, 4, 7, 13, 20)
        if tzolkin_day in [1, 4, 7, 13, 20]:
            if fear_greed < 40:
                return "COSMIC_ACCUMULATE"
            else:
                return "COSMIC_OBSERVE"
        elif fear_greed < 25:
            return "UNDERWORLD_BUY"  # Xibalba journey - buy in darkness
        elif fear_greed > 75:
            return "HARVEST_MAIZE"  # Time to harvest gains
        else:
            return "AWAIT_CYCLE"  # Wait for the next cycle
    
    def _extract_norse_action(self, wisdom: List, fear_greed: int, btc_change: float) -> str:
        """Extract action from Norse wisdom (Runes, Wyrd, Nine Worlds)."""
        # Norse philosophy: fate (Wyrd) and courage
        if fear_greed < 20:
            return "VIKING_RAID"  # Attack when enemy is weak
        elif fear_greed < 40:
            return "ODIN_ACCUMULATE"  # Wisdom of the Allfather - gather resources
        elif fear_greed > 80:
            return "RAGNAROK_EXIT"  # End of cycle - preserve before destruction
        elif btc_change > 5:
            return "RIDE_SLEIPNIR"  # Ride the momentum (Odin's 8-legged horse)
        elif btc_change < -5:
            return "SHIELD_WALL"  # Defensive formation
        else:
            return "CONSULT_RUNES"  # Wait for signs
    
    def _generate_unified_synthesis_11(self, consensus: Dict, fng: int, btc_change: float,
                                        celtic: Dict, aztec: Dict, pythagorean: Dict, egyptian: Dict,
                                        mogollon: Dict, plantagenet: Dict, warfare: Dict,
                                        extended_actions: Dict) -> str:
        """Generate unified wisdom synthesis from ALL 11 CIVILIZATIONS."""
        sentiment = consensus["sentiment"]
        confidence = consensus["confidence"]
        total_civs = consensus.get("civilizations_consulted", 11)
        
        # Get key elements from each tradition
        moon_phase = celtic.get("moon", {}).get("phase_name", "unknown").replace("_", " ").title()
        aztec_day = aztec.get("tonalpohualli", {}).get("name", "unknown")
        sacred_num = pythagorean.get("sacred_number", {}).get("name", "unknown")
        deity = egyptian.get("deity", {}).get("deity", "unknown")
        planet = pythagorean.get("planet", {}).get("planet", "unknown").title()
        
        # Original 7 - get Mogollon, Plantagenet, and Warfare insights
        mogollon_season = mogollon.get("desert_season", {}).get("season", "unknown")
        plantagenet_king = plantagenet.get("king", {}).get("name", "unknown")
        warfare_condition = warfare.get("condition", "unknown")
        
        # Extended civilization insights
        chinese_action = extended_actions.get("chinese", "—")
        hindu_action = extended_actions.get("hindu", "—")
        mayan_action = extended_actions.get("mayan", "—")
        norse_action = extended_actions.get("norse", "—")
        
        synthesis = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  🧠 UNIFIED WISDOM COGNITION - {total_civs} CIVILIZATIONS SPEAK                          ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ORIGINAL 7 TRADITIONS:                                                      ║
║  ☘️ Celtic Moon: {moon_phase:<18} 🦅 Aztec Day: {aztec_day:<19}║
║  🔢 Pythagorean: {sacred_num:<18} ☥ Egyptian: {deity:<20}║
║  🎵 Celestial: {planet:<20} 🏺 Mogollon: {mogollon_season:<17}║
║  👑 Plantagenet: {plantagenet_king:<17} ⚔️ Warfare: {warfare_condition:<18}║
╠══════════════════════════════════════════════════════════════════════════════╣
║  EXTENDED 4 TRADITIONS:                                                      ║
║  ☯️ Chinese: {chinese_action:<20} 🕉️ Hindu: {hindu_action:<20}║
║  🌀 Mayan: {mayan_action:<22} ᚱ Norse: {norse_action:<20}║
╠══════════════════════════════════════════════════════════════════════════════╣
║  CONSENSUS: {sentiment:<10} | ACTION: {consensus['action']:<10} | CONF: {confidence}%               ║
║  Votes: 📈 {consensus['bullish_votes']} Bullish | 📉 {consensus['bearish_votes']} Bearish | ⚖️ {consensus['neutral_votes']} Neutral                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        
        # Add wisdom directive based on consensus
        if sentiment == "BULLISH":
            synthesis += f"\n🎯 WISDOM DIRECTIVE: {total_civs} civilizations speak with one voice - ACCUMULATE."
            synthesis += f"\n   {consensus['bullish_votes']} traditions see opportunity in this fear ({fng})."
            synthesis += f"\n   \"From Celtic druids to Norse seers - BUY.\""
        elif sentiment == "BEARISH":
            synthesis += f"\n🎯 WISDOM DIRECTIVE: {total_civs} civilizations counsel CAUTION."
            synthesis += f"\n   {consensus['bearish_votes']} traditions warn of danger ahead."
            synthesis += f"\n   \"Ragnarök approaches - preserve your gains.\""
        else:
            synthesis += f"\n🎯 WISDOM DIRECTIVE: The council is divided - OBSERVE and WAIT."
            synthesis += f"\n   The Tao teaches wu-wei. The runes counsel patience."
            synthesis += f"\n   \"Wait for the cosmic cycle to turn.\""
        
        return synthesis
    
    def _determine_market_context(self, fear_greed: int, btc_change: float) -> str:
        """Determine market context for wisdom filtering."""
        if abs(btc_change) > 5:
            return "volatile"
        elif btc_change > 2:
            return "bullish"
        elif btc_change < -2:
            return "bearish"
        elif fear_greed < 30:
            return "fearful"
        elif fear_greed > 70:
            return "greedy"
        else:
            return "consolidating"
    
    def _collect_actions(self, celtic, aztec, mogollon, plantagenet, egyptian, pythagorean, warfare, fng) -> Dict:
        """Collect action recommendations from all sources."""
        actions = {
            "celtic": self._extract_celtic_action(celtic, fng),
            "aztec": self._extract_aztec_action(aztec, fng),
            "mogollon": self._extract_mogollon_action(mogollon, fng),
            "plantagenet": self._extract_plantagenet_action(plantagenet, fng),
            "egyptian": self._extract_egyptian_action(egyptian, fng),
            "pythagorean": self._extract_pythagorean_action(pythagorean, fng),
            "warfare": self._extract_warfare_action(warfare, fng)
        }
        return actions
    
    def _extract_celtic_action(self, reading: Dict, fng: int) -> str:
        """Extract action from Celtic reading."""
        moon = reading.get("moon", {})
        phase = moon.get("phase_name", "")
        
        if "new" in phase.lower():
            return "PLANT_SEEDS" if fng < 40 else "WAIT"
        elif "full" in phase.lower():
            return "HARVEST" if fng > 60 else "OBSERVE"
        elif "waning" in phase.lower() or "last" in phase.lower():
            return "RELEASE"
        else:
            return "GROW"
    
    def _extract_aztec_action(self, reading: Dict, fng: int) -> str:
        """Extract action from Aztec reading."""
        tonal = reading.get("tonalpohualli", {})
        day_num = tonal.get("day_number", 0)
        
        # Aztec auspicious days
        if day_num in [1, 7, 10, 13]:
            return "ACCUMULATE" if fng < 40 else "HOLD"
        elif day_num in [4, 9]:
            return "CAUTION"
        else:
            return "OBSERVE"
    
    def _extract_mogollon_action(self, reading: Dict, fng: int) -> str:
        """Extract action from Mogollon reading."""
        season = reading.get("desert_season", {})
        season_name = season.get("season", "")
        
        if "planting" in season_name.lower():
            return "ACCUMULATE"
        elif "harvest" in season_name.lower() or "monsoon" in season_name.lower():
            return "HARVEST"
        elif "winter" in season_name.lower():
            return "WAIT"
        else:
            return "PATIENCE"
    
    def _extract_plantagenet_action(self, reading: Dict, fng: int) -> str:
        """Extract action from Plantagenet reading."""
        king = reading.get("king", {})
        king_name = king.get("name", "").lower()
        
        # Warrior kings = action, builder kings = accumulate
        if "richard" in king_name or "edward iii" in king_name:
            return "ATTACK" if fng < 30 else "DEFEND"
        elif "henry ii" in king_name or "henry iii" in king_name:
            return "BUILD"
        elif "john" in king_name or "richard ii" in king_name:
            return "CAUTION"
        else:
            return "STRATEGIC_WAIT"
    
    def _extract_egyptian_action(self, reading: Dict, fng: int) -> str:
        """Extract action from Egyptian reading."""
        deity = reading.get("deity", {})
        deity_name = deity.get("deity", "").lower()
        
        if "osiris" in deity_name:
            return "RESURRECTION_BUY" if fng < 30 else "HOLD"
        elif "ra" in deity_name:
            return "RIDE_THE_SUN"
        elif "set" in deity_name or "sekhmet" in deity_name:
            return "PROTECT"
        elif "ma'at" in deity_name:
            return "BALANCE"
        else:
            return "OBSERVE"
    
    def _extract_pythagorean_action(self, reading: Dict, fng: int) -> str:
        """Extract action from Pythagorean reading."""
        number = reading.get("sacred_number", {})
        num = number.get("number", 5)
        
        # Pythagorean number meanings
        if num in [1, 10]:  # Unity, completion
            return "DECISIVE_ACTION"
        elif num in [3, 6]:  # Harmony, perfection
            return "BALANCED_ENTRY"
        elif num in [4]:  # Stability
            return "HOLD_POSITION"
        elif num in [7]:  # Cycles
            return "CYCLE_AWARE"
        else:
            return "CALCULATE"
    
    def _extract_warfare_action(self, reading: Dict, fng: int) -> str:
        """Extract action from warfare reading."""
        if fng < 20:
            return "ATTACK_WEAK_POINT"
        elif fng < 40:
            return "ACCUMULATE_QUIETLY"
        elif fng > 80:
            return "RETREAT_PRESERVE"
        elif fng > 60:
            return "DEFENSIVE_POSITION"
        else:
            return "AWAIT_OPPORTUNITY"
    
    def _determine_consensus(self, actions: Dict) -> Dict:
        """Determine consensus from all civilization actions."""
        # Map actions to sentiment categories
        bullish_actions = ["ACCUMULATE", "ATTACK", "PLANT_SEEDS", "RESURRECTION_BUY", 
                          "DECISIVE_ACTION", "ATTACK_WEAK_POINT", "ACCUMULATE_QUIETLY",
                          "RIDE_THE_SUN", "BALANCED_ENTRY", "BUILD", "GROW"]
        bearish_actions = ["RETREAT_PRESERVE", "PROTECT", "CAUTION", "RELEASE"]
        neutral_actions = ["HOLD", "OBSERVE", "WAIT", "BALANCE", "STRATEGIC_WAIT",
                          "PATIENCE", "HOLD_POSITION", "DEFENSIVE_POSITION", 
                          "AWAIT_OPPORTUNITY", "CYCLE_AWARE", "CALCULATE", "HARVEST", "DEFEND"]
        
        bullish_count = sum(1 for a in actions.values() if a in bullish_actions)
        bearish_count = sum(1 for a in actions.values() if a in bearish_actions)
        neutral_count = sum(1 for a in actions.values() if a in neutral_actions)
        
        total = len(actions)
        
        if bullish_count > total * 0.5:
            consensus_action = "ACCUMULATE"
            confidence = bullish_count / total
            sentiment = "BULLISH"
        elif bearish_count > total * 0.5:
            consensus_action = "REDUCE"
            confidence = bearish_count / total
            sentiment = "BEARISH"
        else:
            consensus_action = "HOLD"
            confidence = neutral_count / total
            sentiment = "NEUTRAL"
        
        return {
            "action": consensus_action,
            "sentiment": sentiment,
            "confidence": round(confidence * 100, 1),
            "bullish_votes": bullish_count,
            "bearish_votes": bearish_count,
            "neutral_votes": neutral_count,
            "civilizations_consulted": total
        }
    
    def _generate_unified_synthesis(self, consensus: Dict, fng: int, btc_change: float,
                                    celtic: Dict, aztec: Dict, pythagorean: Dict, egyptian: Dict) -> str:
        """Generate unified wisdom synthesis."""
        sentiment = consensus["sentiment"]
        confidence = consensus["confidence"]
        
        # Get key elements from each tradition
        moon_phase = celtic.get("moon", {}).get("phase_name", "unknown").replace("_", " ").title()
        aztec_day = aztec.get("tonalpohualli", {}).get("name", "unknown")
        sacred_num = pythagorean.get("sacred_number", {}).get("name", "unknown")
        deity = egyptian.get("deity", {}).get("deity", "unknown")
        planet = pythagorean.get("planet", {}).get("planet", "unknown").title()
        
        synthesis = f"""
╔══════════════════════════════════════════════════════════════════╗
║  🧠 UNIFIED WISDOM COGNITION - {consensus['civilizations_consulted']} CIVILIZATIONS SPEAK  ║
╠══════════════════════════════════════════════════════════════════╣
║  ☘️ Celtic Moon: {moon_phase:<20} 🦅 Aztec Day: {aztec_day:<15} ║
║  🔢 Pythagorean: {sacred_num:<20} ☥ Egyptian: {deity:<16} ║
║  🎵 Celestial: {planet:<22}                              ║
╠══════════════════════════════════════════════════════════════════╣
║  CONSENSUS: {sentiment:<10} | ACTION: {consensus['action']:<10} | CONF: {confidence}%     ║
║  Votes: 📈 {consensus['bullish_votes']} Bullish | 📉 {consensus['bearish_votes']} Bearish | ⚖️ {consensus['neutral_votes']} Neutral          ║
╚══════════════════════════════════════════════════════════════════╝
"""
        
        # Add wisdom directive based on consensus
        if sentiment == "BULLISH":
            synthesis += f"\n🎯 WISDOM DIRECTIVE: The ancients speak with one voice - ACCUMULATE."
            synthesis += f"\n   {consensus['bullish_votes']} civilizations see opportunity in this fear ({fng})."
            synthesis += f"\n   \"The guerrilla strikes when the enemy is weakest.\""
        elif sentiment == "BEARISH":
            synthesis += f"\n🎯 WISDOM DIRECTIVE: The ancients counsel CAUTION."
            synthesis += f"\n   {consensus['bearish_votes']} civilizations warn of danger ahead."
            synthesis += f"\n   \"He who retreats lives to fight another day.\""
        else:
            synthesis += f"\n🎯 WISDOM DIRECTIVE: The council is divided - OBSERVE and WAIT."
            synthesis += f"\n   Patience is the universal virtue."
            synthesis += f"\n   \"All is Number. Wait for the pattern to reveal itself.\""
        
        return synthesis
    
    def get_quick_wisdom(self) -> str:
        """Get a quick wisdom snippet from a random civilization."""
        snippets = [
            self.warfare.speak_wisdom(),
            self.celtic.speak_wisdom(),
            self.aztec.speak_wisdom(),
            self.mogollon.speak_wisdom(),
            self.plantagenet.speak_wisdom(),
            self.egyptian.speak_wisdom(),
            self.pythagorean.speak_wisdom()
        ]
        return random.choice(snippets)
    
    def get_all_wisdom_of_day(self) -> List[str]:
        """Get wisdom from all civilizations."""
        return [
            f"📜 Sun Tzu: {self.warfare.speak_wisdom()}",
            f"☘️ Celtic: {self.celtic.speak_wisdom()}",
            f"🦅 Aztec: {self.aztec.speak_wisdom()}",
            f"🏺 Mogollon: {self.mogollon.speak_wisdom()}",
            f"👑 Plantagenet: {self.plantagenet.speak_wisdom()}",
            f"☥ Egyptian: {self.egyptian.speak_wisdom()}",
            f"🔢 Pythagorean: {self.pythagorean.speak_wisdom()}"
        ]
    
    def print_wisdom_stats(self):
        """Print comprehensive wisdom statistics."""
        stats = self.wisdom_stats
        total_points = sum([
            stats["warfare_principles"],
            stats["celtic_data_points"],
            stats["aztec_data_points"],
            stats["mogollon_data_points"],
            stats["plantagenet_data_points"],
            stats["egyptian_data_points"],
            stats["pythagorean_data_points"]
        ])
        
        print("\n" + "═" * 60)
        print("  🧠 WISDOM COGNITION ENGINE - STATISTICS")
        print("═" * 60)
        print(f"  📅 Years of Wisdom: {stats['total_years_of_wisdom']:,}")
        print(f"  🌍 Civilizations: {stats['total_civilizations']}")
        print(f"  📊 Total Data Points: {total_points}")
        print("  ─" * 30)
        print(f"  ⚔️ Warfare Principles: {stats['warfare_principles']}")
        print(f"  ☘️ Celtic Data: {stats['celtic_data_points']}")
        print(f"  🦅 Aztec Data: {stats['aztec_data_points']}")
        print(f"  🏺 Mogollon Data: {stats['mogollon_data_points']}")
        print(f"  👑 Plantagenet Data: {stats['plantagenet_data_points']}")
        print(f"  ☥ Egyptian Data: {stats['egyptian_data_points']}")
        print(f"  🔢 Pythagorean Data: {stats['pythagorean_data_points']}")
        print("═" * 60 + "\n")


# ═══════════════════════════════════════════════════════════════
# ⚔️ STRATEGIC WARFARE LIBRARY - Sun Tzu & Guerrilla Tactics
# ═══════════════════════════════════════════════════════════════

class StrategicWarfareLibrary:
    """
    Reads classic strategy texts and applies their wisdom to trading.
    
    Sources:
    - Sun Tzu's "The Art of War" (Project Gutenberg)
    - Irish Republican Army tactical doctrine (historical)
    - Guerrilla warfare principles
    
    "All warfare is based on deception." - Sun Tzu
    "The guerrilla must move amongst the people as a fish swims in the sea." - Mao Zedong
    """
    
    # Public domain text sources
    SUN_TZU_URL = "https://www.gutenberg.org/files/132/132-0.txt"
    
    # Pre-compiled Sun Tzu wisdom (key excerpts for trading)
    SUN_TZU_PRINCIPLES = [
        # Chapter 1: Laying Plans
        {"text": "All warfare is based on deception.", "trading": "Markets deceive - question every narrative. Big players mask their true intentions."},
        {"text": "When able to attack, we must seem unable; when using our forces, we must seem inactive.", "trading": "Accumulate quietly. Don't telegraph your positions."},
        {"text": "Attack him where he is unprepared, appear where you are not expected.", "trading": "Trade contrarian. Enter positions when fear is maximum."},
        {"text": "The general who wins makes many calculations before the battle.", "trading": "Do your analysis BEFORE the trade. Emotion during execution = death."},
        
        # Chapter 2: Waging War
        {"text": "There is no instance of a country having benefited from prolonged warfare.", "trading": "Quick trades, tight filters. Don't chase; take only net-profitable exits."},
        {"text": "In war, then, let your great object be victory, not lengthy campaigns.", "trading": "Take profits. The goal is NET profit, not being right."},
        
        # Chapter 3: Attack by Stratagem
        {"text": "Supreme excellence consists in breaking the enemy's resistance without fighting.", "trading": "The best trade is the one you don't have to make. Wait for asymmetric setups."},
        {"text": "If you know the enemy and know yourself, you need not fear the result of a hundred battles.", "trading": "Know your edge. Know the market structure. Trade YOUR strategy."},
        {"text": "He will win who knows when to fight and when not to fight.", "trading": "NOT every day is a trading day. Patience is the edge."},
        
        # Chapter 4: Tactical Dispositions
        {"text": "The good fighters of old first put themselves beyond the possibility of defeat.", "trading": "Position sizing. Risk management FIRST. You can't win if you're blown up."},
        {"text": "To secure ourselves against defeat lies in our own hands, but the opportunity of defeating the enemy is provided by the enemy himself.", "trading": "Manage your risk (your control). Let the market make mistakes (their mistake = your opportunity)."},
        
        # Chapter 5: Energy
        {"text": "The onset of troops is like the rush of a torrent which will even roll stones along in its course.", "trading": "Momentum is real. Don't fight the trend."},
        {"text": "In battle, there are not more than two methods of attack: the direct and the indirect.", "trading": "Direct = breakout trades. Indirect = mean reversion. Master both."},
        
        # Chapter 6: Weak Points and Strong
        {"text": "You may advance and be absolutely irresistible, if you make for the enemy's weak points.", "trading": "Trade where liquidity is thin. Attack weak hands."},
        {"text": "Appear at points which the enemy must hasten to defend.", "trading": "Force market makers to cover. Hunt the stops."},
        {"text": "Military tactics are like unto water; for water in its natural course runs away from high places and hastens downwards.", "trading": "Go with the flow. Water (and price) finds the path of least resistance."},
        
        # Chapter 7: Maneuvering
        {"text": "Let your rapidity be that of the wind, your compactness that of the forest.", "trading": "Execute fast. Stay disciplined."},
        {"text": "In raiding and plundering be like fire, in immovability like a mountain.", "trading": "When you strike, strike HARD. When you wait, wait STILL."},
        {"text": "Ponder and deliberate before you make a move.", "trading": "PLAN the trade. TRADE the plan."},
        
        # Chapter 9: The Army on the March
        {"text": "Camp in high places, facing the sun.", "trading": "Trade with the trend. Keep visibility on the big picture."},
        {"text": "When the enemy is close at hand and remains quiet, he is relying on the natural strength of his position.", "trading": "Low volatility = coiling for a move. The calm before the storm."},
        
        # Chapter 10: Terrain
        {"text": "If fighting is sure to result in victory, then you must fight, even though the ruler forbid it.", "trading": "When you see the edge, TAKE IT. Don't second-guess yourself."},
        {"text": "If fighting will not result in victory, then you must not fight even at the ruler's bidding.", "trading": "No edge = no trade. Doesn't matter what anyone says."},
        
        # Chapter 11: The Nine Situations
        {"text": "Throw your soldiers into positions whence there is no escape, and they will prefer death to flight.", "trading": "Commitment. Once in, manage the trade - don't panic."},
        {"text": "The skillful tactician may be likened to the shuai-jan snake... strike at its head, and you will be attacked by its tail.", "trading": "Markets adapt. Your strategy must evolve."},
        
        # Chapter 13: The Use of Spies
        {"text": "What enables the wise sovereign and the good general to strike and conquer is foreknowledge.", "trading": "INFORMATION is the edge. Do your homework."},
        {"text": "Knowledge of the enemy's dispositions can only be obtained from other men.", "trading": "Watch what smart money does, not what they say."},
    ]
    
    # Irish Republican Army / Guerrilla Warfare Principles
    # (Historical tactical doctrine - applied to asymmetric trading)
    IRA_GUERRILLA_PRINCIPLES = [
        # Asymmetric Warfare
        {"text": "The guerrilla fights the war of the flea.", "trading": "Small positions, many trades. Don't let one loss kill you."},
        {"text": "Strike and withdraw. Never hold ground you cannot defend.", "trading": "Hit your target profit, GET OUT. Don't hold hoping for more."},
        {"text": "The enemy advances, we retreat. The enemy camps, we harass. The enemy tires, we attack. The enemy retreats, we pursue.", "trading": "Adapt to market conditions. Different phases = different tactics."},
        
        # Intelligence & Deception
        {"text": "Know the terrain better than the occupier.", "trading": "Know YOUR market. Specialize. The generalist loses to the specialist."},
        {"text": "The informer is the guerrilla's greatest weapon.", "trading": "On-chain data, order flow, smart money tracking = your informers."},
        {"text": "Create the illusion of being everywhere and nowhere.", "trading": "Don't show your hand. Multiple small positions > one large position."},
        
        # Patience & Timing
        {"text": "Time is on the side of the guerrilla.", "trading": "You can WAIT. Institutions can't. Use patience as a weapon."},
        {"text": "One successful operation is worth a hundred failed ones avoided.", "trading": "Quality over quantity. Wait for the A+ setup."},
        {"text": "The patient ambush defeats the charging army.", "trading": "Let the trade come to you. Don't chase."},
        
        # Survival
        {"text": "The first duty is to survive. Dead guerrillas win no wars.", "trading": "CAPITAL PRESERVATION. You can't trade if you're blown up."},
        {"text": "Retreat is not defeat. Live to fight another day.", "trading": "Survival is sizing + selectivity. Use loss thresholds as warnings, not automatic exits; prefer net-penny wins and avoid forced-loss sells."},
        {"text": "The movement that cannot adapt will die.", "trading": "Markets change. Your strategy must evolve or perish."},
        
        # Morale & Psychology
        {"text": "A guerrilla without belief is just a bandit.", "trading": "Have conviction in your edge. Without belief, you'll panic at the first drawdown."},
        {"text": "The struggle is won in the mind before it is won on the battlefield.", "trading": "Psychology is 90% of trading. Master your emotions first."},
        {"text": "Demoralize the enemy through uncertainty.", "trading": "Volatility is your friend. Chaos = opportunity for the prepared."},
        
        # Collective Action
        {"text": "The network is stronger than the individual.", "trading": "Diversification. Multiple uncorrelated strategies."},
        {"text": "Each cell operates independently but serves the whole.", "trading": "Each trade is independent. No revenge trading. No emotional linking."},
        {"text": "The people are the sea in which the guerrilla swims.", "trading": "Trade WITH retail sentiment, not against it. But know when retail is wrong."},
    ]
    
    def __init__(self):
        self.full_sun_tzu_text = None
        self.wisdom_cache = []
        self.last_fetch = 0
        
    def fetch_sun_tzu_text(self) -> str:
        """Fetch the full Art of War text from Project Gutenberg."""
        try:
            logger.info("[scroll] Fetching Sun Tzu's Art of War from Project Gutenberg...")
            response = requests.get(self.SUN_TZU_URL, timeout=(3.05, 10))  # (connect, read)
            if response.status_code == 200:
                self.full_sun_tzu_text = response.text
                logger.info(f"   ✅ Loaded {len(self.full_sun_tzu_text):,} characters of ancient wisdom")
                return self.full_sun_tzu_text
        except Exception as e:
            logger.warning(f"   ⚠️ Could not fetch Sun Tzu: {e}")
        return ""
    
    def get_strategic_wisdom(self, market_condition: str = "neutral") -> Dict[str, Any]:
        """
        Retrieve relevant strategic wisdom based on market conditions.
        
        market_condition: 'fear', 'greed', 'volatile', 'calm', 'trending', 'ranging'
        """
        wisdom = {
            "sun_tzu": [],
            "guerrilla": [],
            "synthesis": "",
            "tactical_directive": ""
        }
        
        # Select relevant Sun Tzu principles
        if market_condition in ["fear", "extreme_fear"]:
            # Contrarian attack wisdom
            relevant_indices = [2, 6, 9, 14, 18]  # Attack, opportunity, contrarian
        elif market_condition in ["greed", "extreme_greed"]:
            # Caution and defense wisdom
            relevant_indices = [4, 8, 10, 16, 19]  # Victory, patience, defense
        elif market_condition == "volatile":
            # Adaptability wisdom
            relevant_indices = [11, 13, 17, 20, 21]  # Energy, maneuver, adapt
        else:
            # General wisdom
            relevant_indices = random.sample(range(len(self.SUN_TZU_PRINCIPLES)), min(5, len(self.SUN_TZU_PRINCIPLES)))
        
        for idx in relevant_indices:
            if idx < len(self.SUN_TZU_PRINCIPLES):
                wisdom["sun_tzu"].append(self.SUN_TZU_PRINCIPLES[idx])
        
        # Select relevant guerrilla principles
        if market_condition in ["fear", "extreme_fear"]:
            guerrilla_indices = [0, 2, 7, 9, 14]  # Patience, adapt, survive
        elif market_condition in ["greed", "extreme_greed"]:
            guerrilla_indices = [1, 8, 10, 11, 13]  # Strike, withdraw, survival
        else:
            guerrilla_indices = random.sample(range(len(self.IRA_GUERRILLA_PRINCIPLES)), min(5, len(self.IRA_GUERRILLA_PRINCIPLES)))
        
        for idx in guerrilla_indices:
            if idx < len(self.IRA_GUERRILLA_PRINCIPLES):
                wisdom["guerrilla"].append(self.IRA_GUERRILLA_PRINCIPLES[idx])
        
        # Synthesize tactical directive
        wisdom["synthesis"] = self._synthesize_wisdom(wisdom, market_condition)
        wisdom["tactical_directive"] = self._generate_directive(market_condition)
        
        return wisdom
    
    def _synthesize_wisdom(self, wisdom: Dict, condition: str) -> str:
        """Synthesize Sun Tzu + Guerrilla wisdom into actionable insight."""
        if condition in ["fear", "extreme_fear"]:
            return "🗡️ WISDOM SYNTHESIS: The master attacks where the enemy is weakest. Extreme fear = weak hands selling. The guerrilla strikes when the occupier is tired. This is the moment to ACCUMULATE - but quietly, like water finding its path."
        elif condition in ["greed", "extreme_greed"]:
            return "🛡️ WISDOM SYNTHESIS: The wise general secures victory before battle. Extreme greed = overextended positions. The guerrilla never holds ground he cannot defend. This is the moment to TAKE PROFITS and prepare for the counter-strike."
        elif condition == "volatile":
            return "⚡ WISDOM SYNTHESIS: In chaos, the prepared find opportunity. Volatility is the guerrilla's friend. Strike fast, withdraw faster. Small positions, quick profits. The snake strikes and recoils."
        else:
            return "⚖️ WISDOM SYNTHESIS: He who knows when to fight and when not to fight will be victorious. Wait. Watch. The patient ambush defeats the charging army."
    
    def _generate_directive(self, condition: str) -> str:
        """Generate specific tactical directive."""
        directives = {
            "extreme_fear": "DIRECTIVE: Deploy capital in tranches. Accumulate on weakness. Set bids below market.",
            "fear": "DIRECTIVE: Begin accumulation. Watch for capitulation candles. Patience.",
            "neutral": "DIRECTIVE: Maintain positions. Wait for clarity. No new deployments.",
            "greed": "DIRECTIVE: Scale out of positions. Take 25-50% profits. Raise stops.",
            "extreme_greed": "DIRECTIVE: Maximum caution. Exit weak positions. Prepare for reversal.",
            "volatile": "DIRECTIVE: Reduce position sizes. Widen stops. Trade the range, not the trend.",
            "calm": "DIRECTIVE: Accumulate positions. Volatility compression precedes expansion."
        }
        return directives.get(condition, directives["neutral"])
    
    def get_random_wisdom(self) -> Tuple[str, str]:
        """Get a random piece of wisdom for display."""
        all_wisdom = self.SUN_TZU_PRINCIPLES + self.IRA_GUERRILLA_PRINCIPLES
        selected = random.choice(all_wisdom)
        return selected["text"], selected["trading"]
    
    def get_warfare_reading(self, fear_greed: int, btc_price: float, btc_change: float) -> Dict:
        """Get a comprehensive warfare reading for the cognition engine."""
        # Determine condition from fear/greed
        if fear_greed < 20:
            condition = "extreme_fear"
        elif fear_greed < 40:
            condition = "fear"
        elif fear_greed > 80:
            condition = "extreme_greed"
        elif fear_greed > 60:
            condition = "greed"
        elif abs(btc_change) > 5:
            condition = "volatile"
        else:
            condition = "neutral"
        
        strategic = self.get_strategic_wisdom(condition)
        
        return {
            "condition": condition,
            "sun_tzu_principles": strategic["sun_tzu"][:3],
            "guerrilla_tactics": strategic["guerrilla"][:3],
            "synthesis": strategic["synthesis"],
            "directive": strategic["tactical_directive"],
            "fear_greed": fear_greed,
            "btc_change": btc_change
        }
    
    def speak_wisdom(self) -> str:
        """Generate a wisdom statement for the brain to speak."""
        text, trading = self.get_random_wisdom()
        return f'📜 "{text}" → 💹 {trading}'


# ═══════════════════════════════════════════════════════════════
# 🌙☘️ CELTIC WISDOM LIBRARY - Stars, Frequencies & Druidic Knowledge
# ═══════════════════════════════════════════════════════════════

class CelticWisdomLibrary:
    """
    Ancient Celtic/Druidic wisdom applied to trading.
    
    The Celts understood:
    - Astronomical cycles (solstices, equinoxes, moon phases)
    - Sacred frequencies and harmonics
    - The interconnectedness of all things
    - Reading signs from nature and the stars
    
    "As above, so below. As within, so without."
    """
    
    # Sacred Frequencies (Hz) - The Solfeggio Scale & Celtic Harmonics
    SACRED_FREQUENCIES = {
        174: {"name": "Foundation", "effect": "Pain reduction, security", "trading": "Build your base. Secure positions before expansion."},
        285: {"name": "Regeneration", "effect": "Tissue healing, safety", "trading": "Recover from losses. Rebuild capital slowly."},
        396: {"name": "Liberation", "effect": "Release fear and guilt", "trading": "Let go of losing trades. Fear is the mind-killer."},
        417: {"name": "Change", "effect": "Facilitate change, undo trauma", "trading": "Adapt strategy. What worked before may not work now."},
        432: {"name": "Universe", "effect": "Natural harmony, Verdi's A", "trading": "Trade with the trend. Align with market flow."},
        528: {"name": "Miracle", "effect": "DNA repair, transformation", "trading": "Transformation frequency. Major trend changes incoming."},
        639: {"name": "Connection", "effect": "Relationships, harmony", "trading": "Correlation trades. Watch related assets move together."},
        741: {"name": "Awakening", "effect": "Intuition, expression", "trading": "Trust your gut. Your subconscious sees patterns you don't."},
        852: {"name": "Intuition", "effect": "Third eye, spiritual order", "trading": "See beyond the chart. Macro forces at play."},
        963: {"name": "Divine", "effect": "Pineal activation, oneness", "trading": "The perfect trade. Rare. Wait for it."},
    }
    
    # Schumann Resonance - Earth's Heartbeat
    SCHUMANN_RESONANCE = 7.83  # Hz - The Earth's electromagnetic frequency
    
    # Celtic Calendar - The Wheel of the Year
    CELTIC_CALENDAR = {
        "samhain": {"date": "Oct 31 - Nov 1", "meaning": "End of harvest, veil thins", "trading": "Year-end positioning. Tax-loss harvesting season. Expect volatility."},
        "yule": {"date": "Dec 21", "meaning": "Winter Solstice, rebirth of light", "trading": "Darkest before dawn. After solstice, light returns. Accumulation season."},
        "imbolc": {"date": "Feb 1-2", "meaning": "First signs of spring", "trading": "Early signals of trend change. Plant seeds for Q2."},
        "ostara": {"date": "Mar 20-21", "meaning": "Spring Equinox, balance", "trading": "Balance point. Equal day/night = equal bull/bear. Breakout imminent."},
        "beltane": {"date": "May 1", "meaning": "Fire festival, fertility", "trading": "'Sell in May' - but the Celts celebrated growth. Contrarian opportunity?"},
        "litha": {"date": "Jun 21", "meaning": "Summer Solstice, peak light", "trading": "Maximum optimism. Peak greed territory. Consider taking profits."},
        "lughnasadh": {"date": "Aug 1", "meaning": "First harvest", "trading": "Harvest your winners. First profits of the cycle."},
        "mabon": {"date": "Sep 22-23", "meaning": "Autumn Equinox, gratitude", "trading": "Second balance point. Prepare for Q4 volatility."},
    }
    
    # Moon Phases - Lunar Cycles
    MOON_PHASES = {
        "new_moon": {"phase": 0, "meaning": "New beginnings, planting seeds", "trading": "Start new positions. Set intentions for the cycle."},
        "waxing_crescent": {"phase": 0.125, "meaning": "Setting intentions", "trading": "Build positions. Momentum building."},
        "first_quarter": {"phase": 0.25, "meaning": "Taking action, challenges", "trading": "Expect resistance. Test of conviction."},
        "waxing_gibbous": {"phase": 0.375, "meaning": "Refinement, patience", "trading": "Fine-tune entries. Patience before full moon."},
        "full_moon": {"phase": 0.5, "meaning": "Culmination, illumination", "trading": "Harvest time. Take profits. Emotions run high - expect volatility."},
        "waning_gibbous": {"phase": 0.625, "meaning": "Gratitude, sharing", "trading": "Share knowledge. Distribute positions."},
        "last_quarter": {"phase": 0.75, "meaning": "Release, forgiveness", "trading": "Cut losers. Let go of bad trades."},
        "waning_crescent": {"phase": 0.875, "meaning": "Surrender, rest", "trading": "Reduce activity. Rest before new cycle."},
    }
    
    # Druidic Tree Wisdom - Ogham Alphabet
    DRUIDIC_TREES = [
        {"tree": "Oak (Duir)", "meaning": "Strength, endurance, doorway", "trading": "Strong foundation. Blue-chip positions. The door to wealth."},
        {"tree": "Birch (Beith)", "meaning": "New beginnings, purification", "trading": "Fresh starts. New positions after cleansing losses."},
        {"tree": "Rowan (Luis)", "meaning": "Protection, vision", "trading": "Protect capital. See clearly through market noise."},
        {"tree": "Alder (Fearn)", "meaning": "Foundation, bridge between worlds", "trading": "Bridge old strategy to new. Adapt while honoring what worked."},
        {"tree": "Willow (Saille)", "meaning": "Intuition, flexibility", "trading": "Bend, don't break. Flexible strategies survive."},
        {"tree": "Ash (Nuin)", "meaning": "Connection, world tree", "trading": "Everything is connected. Correlations matter."},
        {"tree": "Hawthorn (Huath)", "meaning": "Patience, restraint", "trading": "Wait for the right moment. Thorns protect the bloom."},
        {"tree": "Holly (Tinne)", "meaning": "Balance, warrior spirit", "trading": "Balanced portfolio. Fight for your positions."},
        {"tree": "Hazel (Coll)", "meaning": "Wisdom, creativity", "trading": "Creative solutions. Think different from the herd."},
        {"tree": "Apple (Quert)", "meaning": "Beauty, choice, immortality", "trading": "Choose wisely. Beautiful setups = high probability."},
        {"tree": "Yew (Idho)", "meaning": "Transformation, rebirth, eternity", "trading": "Death and rebirth. Let old strategies die for new ones to grow."},
        {"tree": "Elder (Ruis)", "meaning": "Endings, completion, transition", "trading": "Complete the cycle. Close positions at natural endings."},
    ]
    
    # Celtic Triads - Wisdom in Threes
    CELTIC_TRIADS = [
        {"triad": "Three candles that illuminate darkness: Truth, Nature, Knowledge", "trading": "Truth = price action. Nature = market cycles. Knowledge = your edge."},
        {"triad": "Three things that give newness: a seed, an infant, fire", "trading": "New positions (seeds), new strategies (infant), burning losses (fire)."},
        {"triad": "Three things that cannot be hidden: smoke, a pregnant woman, love", "trading": "Big moves can't hide: volume spikes, accumulation patterns, momentum."},
        {"triad": "Three things a fool is blind to: truth, error, his own face", "trading": "Don't be blind to: price action, your mistakes, your own bias."},
        {"triad": "Three things that must be united: a maiden's thigh, a cat's ear, a smith's arm", "trading": "Sensitivity, awareness, and strength must unite in trading."},
        {"triad": "Three deaths better than life: a pig's, a fox's, a hen's", "trading": "Death of greed (pig), cunning (fox), fear (hen) - better than living with them."},
        {"triad": "Three things that strengthen a man: sleep, milk, a pleasant companion", "trading": "Rest between trades, nourish your mind, trade with like minds."},
        {"triad": "Three keys to wisdom: know yourself, know your world, know your craft", "trading": "Know your psychology, know your market, know your strategy."},
    ]
    
    # Star Reading - Celtic Astronomy
    CELTIC_STARS = {
        "pleiades": {"name": "The Seven Sisters (Cruinne)", "meaning": "Guidance, navigation", "trading": "Navigate by fundamentals. Seven key metrics guide you."},
        "north_star": {"name": "Polaris (Réalta an Tuaiscirt)", "meaning": "True north, constant", "trading": "Your trading plan is true north. Never lose sight of it."},
        "orion": {"name": "The Hunter (Sealgair)", "meaning": "Pursuit, skill", "trading": "Hunt opportunities with skill. Patience of the hunter."},
        "sirius": {"name": "Dog Star (Réalta an Mhadra)", "meaning": "Brightest light, intensity", "trading": "Focus on the brightest opportunities. Intensity of conviction."},
        "cassiopeia": {"name": "The Queen (An Bhanríon)", "meaning": "Sovereignty, pride", "trading": "Rule your portfolio with sovereignty. Pride in your decisions."},
    }
    
    # Frequency Harmonics and Market Cycles
    HARMONIC_CYCLES = [
        {"cycle": "7.83 Hz - Schumann", "period": "~127ms", "trading": "Earth's heartbeat. Base rhythm of all cycles."},
        {"cycle": "Lunar Month", "period": "29.5 days", "trading": "Monthly options cycles. Emotion-driven markets."},
        {"cycle": "Solar Year", "period": "365.25 days", "trading": "Annual seasonality. 'Sell in May', 'Santa Rally'."},
        {"cycle": "Metonic Cycle", "period": "19 years", "trading": "Long-term bull/bear supercycles."},
        {"cycle": "Saros Cycle", "period": "18 years, 11 days", "trading": "Eclipse cycle. Major turning points."},
        {"cycle": "Great Year", "period": "25,920 years", "trading": "Precessional cycle. Civilizational shifts."},
    ]
    
    def __init__(self):
        self.current_moon_phase = None
        self.current_celtic_festival = None
        
    def get_current_moon_phase(self) -> Dict:
        """Calculate current moon phase."""
        from datetime import datetime
        
        # Known new moon: January 6, 2000
        known_new_moon = datetime(2000, 1, 6, 18, 14)
        now = datetime.now()
        
        # Synodic month = 29.53059 days
        synodic_month = 29.53059
        days_since = (now - known_new_moon).total_seconds() / 86400
        cycles = days_since / synodic_month
        phase = cycles % 1  # 0-1 representing phase
        
        # Determine phase name
        if phase < 0.0625:
            phase_name = "new_moon"
        elif phase < 0.1875:
            phase_name = "waxing_crescent"
        elif phase < 0.3125:
            phase_name = "first_quarter"
        elif phase < 0.4375:
            phase_name = "waxing_gibbous"
        elif phase < 0.5625:
            phase_name = "full_moon"
        elif phase < 0.6875:
            phase_name = "waning_gibbous"
        elif phase < 0.8125:
            phase_name = "last_quarter"
        else:
            phase_name = "waning_crescent"
        
        moon_data = self.MOON_PHASES[phase_name]
        return {
            "phase_name": phase_name,
            "phase_pct": phase * 100,
            "meaning": moon_data["meaning"],
            "trading": moon_data["trading"]
        }
    
    def get_nearest_celtic_festival(self) -> Dict:
        """Get the nearest Celtic festival."""
        from datetime import datetime
        
        now = datetime.now()
        month_day = (now.month, now.day)
        
        # Check proximity to festivals
        festivals = {
            (10, 31): "samhain", (11, 1): "samhain",
            (12, 21): "yule", (12, 22): "yule",
            (2, 1): "imbolc", (2, 2): "imbolc",
            (3, 20): "ostara", (3, 21): "ostara",
            (5, 1): "beltane",
            (6, 21): "litha", (6, 22): "litha",
            (8, 1): "lughnasadh",
            (9, 22): "mabon", (9, 23): "mabon",
        }
        
        # Find nearest festival (within 7 days)
        for (m, d), festival in festivals.items():
            days_diff = abs((now.month - m) * 30 + (now.day - d))
            if days_diff <= 7:
                return {
                    "festival": festival,
                    "data": self.CELTIC_CALENDAR[festival],
                    "active": True
                }
        
        # Default to next upcoming
        return {"festival": "between_festivals", "active": False}
    
    def get_frequency_guidance(self, fear_greed: int) -> Dict:
        """Get frequency-based guidance based on market sentiment."""
        
        # Map fear/greed to frequency
        if fear_greed <= 15:
            freq = 396  # Liberation from fear
        elif fear_greed <= 30:
            freq = 417  # Change
        elif fear_greed <= 45:
            freq = 432  # Universal harmony
        elif fear_greed <= 55:
            freq = 528  # Transformation
        elif fear_greed <= 70:
            freq = 639  # Connection
        elif fear_greed <= 85:
            freq = 741  # Awakening
        else:
            freq = 852  # Intuition
        
        freq_data = self.SACRED_FREQUENCIES[freq]
        return {
            "frequency": freq,
            "name": freq_data["name"],
            "effect": freq_data["effect"],
            "trading": freq_data["trading"]
        }
    
    def read_the_stars(self, btc_price: float, btc_change_24h: float) -> Dict:
        """Read celestial guidance based on current conditions."""
        
        stars = []
        
        # Always include Polaris (true north)
        stars.append({
            "star": "Polaris",
            "message": self.CELTIC_STARS["north_star"]["trading"]
        })
        
        # Price-based star selection
        if btc_change_24h < -5:
            stars.append({
                "star": "Pleiades",
                "message": "The Seven Sisters guide through darkness. Navigate by fundamentals."
            })
        elif btc_change_24h > 5:
            stars.append({
                "star": "Sirius",
                "message": "The Dog Star burns bright. Intense conviction required."
            })
        else:
            stars.append({
                "star": "Orion",
                "message": "The Hunter waits patiently. Hunt opportunities with skill."
            })
        
        return {"stars": stars}
    
    def get_druidic_tree(self) -> Dict:
        """Get today's druidic tree guidance."""
        from datetime import datetime
        
        # Use day of year to select tree
        day_of_year = datetime.now().timetuple().tm_yday
        tree_idx = day_of_year % len(self.DRUIDIC_TREES)
        tree = self.DRUIDIC_TREES[tree_idx]
        
        return tree
    
    def get_celtic_triad(self) -> Dict:
        """Get a relevant Celtic triad."""
        return random.choice(self.CELTIC_TRIADS)
    
    def get_full_celtic_reading(self, fear_greed: int, btc_price: float, btc_change: float) -> Dict:
        """Get a complete Celtic wisdom reading."""
        
        reading = {
            "moon": self.get_current_moon_phase(),
            "festival": self.get_nearest_celtic_festival(),
            "frequency": self.get_frequency_guidance(fear_greed),
            "stars": self.read_the_stars(btc_price, btc_change),
            "tree": self.get_druidic_tree(),
            "triad": self.get_celtic_triad(),
            "synthesis": ""
        }
        
        # Generate synthesis
        moon_advice = reading["moon"]["trading"]
        freq_advice = reading["frequency"]["trading"]
        
        reading["synthesis"] = self._synthesize_celtic_wisdom(reading, fear_greed)
        
        return reading
    
    def _synthesize_celtic_wisdom(self, reading: Dict, fear_greed: int) -> str:
        """Synthesize all Celtic wisdom into actionable insight."""
        
        moon = reading["moon"]["phase_name"].replace("_", " ").title()
        freq = reading["frequency"]["name"]
        tree = reading["tree"]["tree"]
        
        if fear_greed < 25:
            return f"☘️ CELTIC SYNTHESIS: The {moon} speaks of {reading['moon']['meaning'].lower()}. " \
                   f"The {freq} frequency ({reading['frequency']['frequency']} Hz) calls for liberation from fear. " \
                   f"The {tree} teaches us: {reading['tree']['trading']} " \
                   f"As the Druids knew: In darkness, plant seeds. The wheel turns."
        elif fear_greed > 75:
            return f"☘️ CELTIC SYNTHESIS: The {moon} illuminates {reading['moon']['meaning'].lower()}. " \
                   f"The {freq} frequency warns of overextension. " \
                   f"The {tree} whispers: {reading['tree']['trading']} " \
                   f"As the Druids knew: What rises must fall. Harvest before winter."
        else:
            return f"☘️ CELTIC SYNTHESIS: The {moon} brings {reading['moon']['meaning'].lower()}. " \
                   f"The {freq} frequency ({reading['frequency']['frequency']} Hz) guides to {reading['frequency']['effect'].lower()}. " \
                   f"The {tree} teaches: {reading['tree']['trading']} " \
                   f"As the Druids knew: Balance in all things. The middle path."
    
    def speak_wisdom(self) -> str:
        """Generate a Celtic wisdom statement."""
        triad = self.get_celtic_triad()
        return f'☘️ "{triad["triad"]}" → 💹 {triad["trading"]}'


# ═══════════════════════════════════════════════════════════════
# � AZTEC WISDOM LIBRARY - The Fifth Sun
# ═══════════════════════════════════════════════════════════════

class AztecWisdomLibrary:
    """
    Ancient Aztec (Mexica) wisdom - cosmology, calendar, and philosophy.
    
    The Aztecs had profound understanding of cycles, sacrifice, and cosmic order.
    Their dual calendar system (Tonalpohualli + Xiuhpohualli) maps to market cycles.
    
    "In Tlilli in Tlapalli" - The Red and Black Ink (Wisdom/Knowledge)
    """
    
    # TONALPOHUALLI - 260-Day Sacred Calendar (20 day-signs × 13 numbers)
    # Each day-sign has trading wisdom
    TONALPOHUALLI_SIGNS = {
        1: {"name": "Cipactli", "glyph": "🐊", "meaning": "Crocodile", 
            "energy": "beginning, primordial", 
            "trading": "Begin new positions. The primordial swamp births opportunity."},
        2: {"name": "Ehecatl", "glyph": "💨", "meaning": "Wind", 
            "energy": "change, breath, spirit",
            "trading": "Winds shift markets. Watch for rapid direction changes."},
        3: {"name": "Calli", "glyph": "🏠", "meaning": "House", 
            "energy": "security, home, protection",
            "trading": "Secure your gains. Protect capital. Build shelter."},
        4: {"name": "Cuetzpalin", "glyph": "🦎", "meaning": "Lizard", 
            "energy": "survival, regeneration, adaptation",
            "trading": "Adapt quickly. What is cut off grows back stronger."},
        5: {"name": "Coatl", "glyph": "🐍", "meaning": "Serpent", 
            "energy": "wisdom, transformation, knowledge",
            "trading": "Shed old strategies. Transform through knowledge."},
        6: {"name": "Miquiztli", "glyph": "💀", "meaning": "Death", 
            "energy": "endings, rebirth, transition",
            "trading": "End losing positions. Death precedes rebirth."},
        7: {"name": "Mazatl", "glyph": "🦌", "meaning": "Deer", 
            "energy": "grace, agility, hunt",
            "trading": "Move with agility. The graceful deer escapes the hunter."},
        8: {"name": "Tochtli", "glyph": "🐇", "meaning": "Rabbit", 
            "energy": "fertility, abundance, multiplication",
            "trading": "Compound gains. Let winners multiply like rabbits."},
        9: {"name": "Atl", "glyph": "💧", "meaning": "Water", 
            "energy": "flow, cleansing, emotion",
            "trading": "Flow with the market. Don't fight the current."},
        10: {"name": "Itzcuintli", "glyph": "🐕", "meaning": "Dog", 
             "energy": "loyalty, guidance, underworld",
             "trading": "Trust your system. The dog guides through darkness."},
        11: {"name": "Ozomatli", "glyph": "🐒", "meaning": "Monkey", 
             "energy": "play, creativity, arts",
             "trading": "Creative solutions. Don't be too serious."},
        12: {"name": "Malinalli", "glyph": "🌿", "meaning": "Grass", 
             "energy": "tenacity, resurrection, life",
             "trading": "Persist through setbacks. Grass always grows back."},
        13: {"name": "Acatl", "glyph": "🎋", "meaning": "Reed", 
             "energy": "authority, knowledge, writing",
             "trading": "Document your trades. Knowledge is power."},
        14: {"name": "Ocelotl", "glyph": "🐆", "meaning": "Jaguar", 
             "energy": "power, darkness, night",
             "trading": "Strike with power. The jaguar waits then pounces."},
        15: {"name": "Cuauhtli", "glyph": "🦅", "meaning": "Eagle", 
             "energy": "vision, sun, sky",
             "trading": "See from above. Eagle vision spots opportunity."},
        16: {"name": "Cozcacuauhtli", "glyph": "🦃", "meaning": "Vulture", 
             "energy": "longevity, patience, cleansing",
             "trading": "Patient waiting. The vulture profits from others' demise."},
        17: {"name": "Ollin", "glyph": "🌀", "meaning": "Movement/Earthquake", 
             "energy": "change, evolution, the sun",
             "trading": "Major moves coming. Earthquakes reshape everything."},
        18: {"name": "Tecpatl", "glyph": "🔪", "meaning": "Flint/Knife", 
             "energy": "sacrifice, truth, precision",
             "trading": "Cut losses precisely. The obsidian blade is sharp."},
        19: {"name": "Quiahuitl", "glyph": "🌧️", "meaning": "Rain", 
             "energy": "nourishment, storms, renewal",
             "trading": "Storms bring growth. Volatility nourishes opportunity."},
        20: {"name": "Xochitl", "glyph": "🌺", "meaning": "Flower", 
             "energy": "beauty, completion, soul",
             "trading": "Harvest beauty. The flower is the reward."}
    }
    
    # THE FIVE SUNS - Cosmological ages
    FIVE_SUNS = {
        1: {"name": "Nahui Ocelotl", "element": "Earth", "glyph": "🐆",
            "meaning": "Jaguar Sun - destroyed by jaguars",
            "trading": "Bear markets devour the unprepared."},
        2: {"name": "Nahui Ehecatl", "element": "Wind", "glyph": "💨",
            "meaning": "Wind Sun - destroyed by hurricanes",
            "trading": "Volatility sweeps away weak positions."},
        3: {"name": "Nahui Quiahuitl", "element": "Fire", "glyph": "🔥",
            "meaning": "Rain Sun - destroyed by fire rain",
            "trading": "Flash crashes burn the overleveraged."},
        4: {"name": "Nahui Atl", "element": "Water", "glyph": "🌊",
            "meaning": "Water Sun - destroyed by floods",
            "trading": "Liquidity floods can drown portfolios."},
        5: {"name": "Nahui Ollin", "element": "Movement", "glyph": "☀️",
            "meaning": "Movement Sun - current age, sustained by sacrifice",
            "trading": "Our current cycle. Feed it with discipline."}
    }
    
    # AZTEC DEITIES & Market Archetypes
    TEOTL = {
        "Quetzalcoatl": {"glyph": "🐍", "domain": "Knowledge, Wind, Morning Star",
            "trading": "The feathered serpent brings wisdom. Study before action."},
        "Tezcatlipoca": {"glyph": "🪞", "domain": "Night, Deception, Fate",
            "trading": "The smoking mirror reflects hidden truths. Watch for manipulation."},
        "Huitzilopochtli": {"glyph": "🦅", "domain": "Sun, War, Sacrifice",
            "trading": "The hummingbird of the south. Small, fast, relentless."},
        "Tlaloc": {"glyph": "💧", "domain": "Rain, Fertility, Agriculture",
            "trading": "The rain god nourishes. Wait for liquidity."},
        "Xipe Totec": {"glyph": "🌽", "domain": "Renewal, Agriculture, Seasons",
            "trading": "The flayed one. Shed old skin for new growth."},
        "Mictlantecuhtli": {"glyph": "💀", "domain": "Death, Underworld",
            "trading": "Lord of the dead. Some positions must die."},
        "Tonatiuh": {"glyph": "☀️", "domain": "The Sun, Movement",
            "trading": "The sun demands sacrifice. Pay the spread, take the trade."},
        "Chalchiuhtlicue": {"glyph": "💎", "domain": "Water, Rivers, Jade",
            "trading": "Lady of the jade skirt. Value flows like water."}
    }
    
    # AZTEC PROVERBS - Huehuehtlahtolli (Words of the Elders)
    HUEHUEHTLAHTOLLI = [
        {"proverb": "Nican mopohua, nican tlapohua - Here is recounted, here is told",
         "trading": "Study the chart. The market tells its story."},
        {"proverb": "In xochitl in cuicatl - The flower and the song",
         "trading": "Beauty and rhythm in trading. Find the pattern."},
        {"proverb": "Amo cemilhuitl tonatiuh - Not every day is sun",
         "trading": "Accept red days. Not every day profits."},
        {"proverb": "Ma nel icuac moyollo, ma nel icuac monemiliz - Even if your heart, even if your life",
         "trading": "Trade with conviction but not desperation."},
        {"proverb": "Zan ce nemi noyollo - My heart lives alone",
         "trading": "Trust your own analysis. The lone heart decides."},
        {"proverb": "Ihuinti, teohua, ic ye miqui - Drunk, being a god, then dying",
         "trading": "Euphoria to god-complex to ruin. Control ego."},
        {"proverb": "Aocmo timomachtia - No longer do you learn",
         "trading": "Never stop learning. The moment you stop, you fail."},
        {"proverb": "Ca ye ixquich in monequi - This is all that is needed",
         "trading": "Simplicity wins. You have all you need."},
        {"proverb": "In tlein ticchihuaz, zan ic timiquiz - Whatever you do, you die",
         "trading": "All trades end. Accept impermanence."},
        {"proverb": "Neltoconi in nemiliztli - Life is believable",
         "trading": "Trust the process. The market is real."}
    ]
    
    # DIRECTIONAL COSMOLOGY (4 Directions + Center)
    DIRECTIONS = {
        "East": {"color": "Red", "glyph": "🔴", "deity": "Quetzalcoatl",
            "meaning": "Sunrise, beginning, reed", "trading": "New beginnings. Start fresh."},
        "North": {"color": "Black", "glyph": "⚫", "deity": "Tezcatlipoca", 
            "meaning": "Death, cold, flint", "trading": "Endings and reflection. Cut losses."},
        "West": {"color": "White", "glyph": "⚪", "deity": "Quetzalcoatl (evening)",
            "meaning": "Sunset, completion, house", "trading": "Close positions. Day is done."},
        "South": {"color": "Blue", "glyph": "🔵", "deity": "Huitzilopochtli",
            "meaning": "Life, growth, rabbit", "trading": "Growth phase. Let profits run."},
        "Center": {"color": "Green", "glyph": "🟢", "deity": "Xiuhtecuhtli",
            "meaning": "Fire, transformation, here-now", "trading": "Present moment. Be here now."}
    }
    
    def __init__(self):
        """Initialize the Aztec Wisdom Library."""
        self.current_trecena = 1  # 13-day period number (1-20)
        
    def get_tonalpohualli_day(self) -> Dict:
        """Get today's sacred calendar day-sign."""
        # Calculate from a known date: Nov 9, 2024 was 1-Cipactli (Day 1)
        known_start = datetime(2024, 11, 9)
        today = datetime.now()
        days_elapsed = (today - known_start).days
        
        # 260-day cycle
        day_in_cycle = days_elapsed % 260
        
        # Day sign (1-20) and number (1-13)
        day_sign = (day_in_cycle % 20) + 1
        day_number = (day_in_cycle % 13) + 1
        
        sign_data = self.TONALPOHUALLI_SIGNS[day_sign]
        
        return {
            "day_number": day_number,
            "day_sign": day_sign,
            "name": f"{day_number}-{sign_data['name']}",
            "glyph": sign_data['glyph'],
            "meaning": sign_data['meaning'],
            "energy": sign_data['energy'],
            "trading": sign_data['trading'],
            "full_cycle_day": day_in_cycle + 1
        }
    
    def get_current_sun_age(self, fear_greed: int) -> Dict:
        """Determine which Sun age the market reflects."""
        if fear_greed < 20:
            return {**self.FIVE_SUNS[1], "status": "JAGUAR SUN - Bears devour"}
        elif fear_greed < 40:
            return {**self.FIVE_SUNS[2], "status": "WIND SUN - Volatility rising"}
        elif fear_greed < 60:
            return {**self.FIVE_SUNS[5], "status": "MOVEMENT SUN - Balance maintained"}
        elif fear_greed < 80:
            return {**self.FIVE_SUNS[4], "status": "WATER SUN - Liquidity flows"}
        else:
            return {**self.FIVE_SUNS[3], "status": "FIRE SUN - Euphoria burns"}
    
    def get_deity_guidance(self, btc_change: float) -> Dict:
        """Get guidance from an Aztec deity based on market action."""
        if btc_change > 5:
            return {"deity": "Huitzilopochtli", **self.TEOTL["Huitzilopochtli"],
                    "message": "The Hummingbird of the South soars. Victory!"}
        elif btc_change > 2:
            return {"deity": "Tonatiuh", **self.TEOTL["Tonatiuh"],
                    "message": "The Sun rises strong. Feed him your sacrifice."}
        elif btc_change > 0:
            return {"deity": "Quetzalcoatl", **self.TEOTL["Quetzalcoatl"],
                    "message": "The Feathered Serpent brings wisdom. Study."}
        elif btc_change > -2:
            return {"deity": "Tezcatlipoca", **self.TEOTL["Tezcatlipoca"],
                    "message": "The Smoking Mirror shows hidden truths."}
        elif btc_change > -5:
            return {"deity": "Xipe Totec", **self.TEOTL["Xipe Totec"],
                    "message": "The Flayed One says: shed old skin."}
        else:
            return {"deity": "Mictlantecuhtli", **self.TEOTL["Mictlantecuhtli"],
                    "message": "The Lord of Death claims the weak. Survive."}
    
    def get_elder_wisdom(self) -> Dict:
        """Get wisdom from the Huehuehtlahtolli (Words of the Elders)."""
        return random.choice(self.HUEHUEHTLAHTOLLI)
    
    def get_directional_guidance(self) -> Dict:
        """Get guidance based on time of day (cardinal directions)."""
        hour = datetime.now().hour
        
        if 5 <= hour < 11:
            direction = "East"
        elif 11 <= hour < 14:
            direction = "Center"
        elif 14 <= hour < 18:
            direction = "West"
        elif 18 <= hour < 22:
            direction = "South"
        else:
            direction = "North"
            
        return {"direction": direction, **self.DIRECTIONS[direction]}
    
    def get_full_aztec_reading(self, fear_greed: int, btc_price: float, btc_change: float) -> Dict:
        """Get complete Aztec wisdom reading."""
        reading = {
            "tonalpohualli": self.get_tonalpohualli_day(),
            "sun_age": self.get_current_sun_age(fear_greed),
            "deity": self.get_deity_guidance(btc_change),
            "elder_wisdom": self.get_elder_wisdom(),
            "direction": self.get_directional_guidance(),
            "synthesis": ""
        }
        
        reading["synthesis"] = self._synthesize_aztec_wisdom(reading, fear_greed, btc_change)
        return reading
    
    def _synthesize_aztec_wisdom(self, reading: Dict, fear_greed: int, btc_change: float) -> str:
        """Synthesize Aztec wisdom into actionable insight."""
        day = reading["tonalpohualli"]
        deity = reading["deity"]["deity"]
        sun = reading["sun_age"]["name"]
        
        if fear_greed < 30:
            return f"🦅 AZTEC SYNTHESIS: On this day {day['name']} ({day['glyph']}), " \
                   f"{deity} speaks through the {sun}. The elders say: '{reading['elder_wisdom']['proverb']}' " \
                   f"In extreme fear, the Jaguar hunts the weak. Be the jaguar, not the prey. " \
                   f"Trading: {day['trading']}"
        elif fear_greed > 70:
            return f"🦅 AZTEC SYNTHESIS: On this day {day['name']} ({day['glyph']}), " \
                   f"{deity} warns from the {sun}. The elders say: '{reading['elder_wisdom']['proverb']}' " \
                   f"In extreme greed, the Fire Sun consumes. Take profits before you burn. " \
                   f"Trading: {day['trading']}"
        else:
            return f"🦅 AZTEC SYNTHESIS: On this day {day['name']} ({day['glyph']}), " \
                   f"{deity} guides through the {sun}. The elders say: '{reading['elder_wisdom']['proverb']}' " \
                   f"Balance is maintained. The Movement Sun continues. " \
                   f"Trading: {day['trading']}"
    
    def speak_wisdom(self) -> str:
        """Generate an Aztec wisdom statement."""
        elder = self.get_elder_wisdom()
        return f'🦅 "{elder["proverb"]}" → 💹 {elder["trading"]}'


# ═══════════════════════════════════════════════════════════════
# 🏺 MOGOLLON WISDOM LIBRARY - People of the Mountains
# ═══════════════════════════════════════════════════════════════

class MogollonWisdomLibrary:
    """
    Ancient Mogollon culture wisdom - Southwest American desert dwellers (200-1450 CE).
    
    The Mogollon were masters of adaptation, pottery, agriculture in harsh environments.
    Their Mimbres pottery contains cosmic and trading-relevant symbolism.
    
    "From the mountains to the desert, the people of the pit houses endured."
    """
    
    # MIMBRES POTTERY SYMBOLS - Cosmic and animal imagery
    MIMBRES_SYMBOLS = {
        "rabbit": {"glyph": "🐇", "meaning": "Abundance, fertility, cleverness",
            "trading": "Small quick gains compound. Move like the rabbit."},
        "fish": {"glyph": "🐟", "meaning": "Underground water, hidden resources",
            "trading": "Look beneath the surface. Hidden value exists."},
        "bighorn_sheep": {"glyph": "🐏", "meaning": "Mountain strength, sure-footed",
            "trading": "Navigate heights carefully. Mountain paths are steep."},
        "deer": {"glyph": "🦌", "meaning": "Grace, awareness, gentle strength",
            "trading": "Stay alert. The deer survives by awareness."},
        "bird": {"glyph": "🦅", "meaning": "Sky connection, messages, freedom",
            "trading": "Watch for signals from above. Patterns in flight."},
        "mountain_lion": {"glyph": "🦁", "meaning": "Power, territory, leadership",
            "trading": "Defend your territory. Know when to strike."},
        "bear": {"glyph": "🐻", "meaning": "Introspection, healing, hibernation",
            "trading": "Sometimes retreat is wisdom. Hibernate through storms."},
        "snake": {"glyph": "🐍", "meaning": "Transformation, water, earth energy",
            "trading": "Transform positions. The snake sheds what no longer serves."},
        "turtle": {"glyph": "🐢", "meaning": "Earth, patience, longevity",
            "trading": "Patience wins. The turtle carries its home."},
        "geometric_spiral": {"glyph": "🌀", "meaning": "Cosmic journey, life cycles",
            "trading": "Markets spiral. What goes around comes around."},
        "lightning": {"glyph": "⚡", "meaning": "Rain, power, sudden change",
            "trading": "Flash moves. Lightning strikes fast."},
        "sun": {"glyph": "☀️", "meaning": "Life, warmth, growth",
            "trading": "Bull market energy. Growth season."}
    }
    
    # PIT HOUSE PHILOSOPHY - Architecture as wisdom
    PIT_HOUSE_WISDOM = {
        "dig_deep": "Build your foundation below ground level. Deep roots survive winds.",
        "entrance_east": "Face the sunrise. New beginnings come from the East.",
        "fire_center": "Keep your fire in the center. Passion focused, not scattered.",
        "roof_strong": "Strong roof, strong mind. Protection from what falls.",
        "family_circle": "All sit in circle. No one above, no one below.",
        "storage_prepared": "Store for winter during summer. Prepare for lean times.",
        "ventilation": "Let air flow. Stagnation kills. Keep positions breathing."
    }
    
    # AGRICULTURAL CYCLES - Desert farming wisdom
    DESERT_SEASONS = {
        "winter_solstice": {
            "season": "Planting Planning",
            "months": [12, 1],
            "trading": "Plan your strategy. Winter is for thinking, not action."
        },
        "early_spring": {
            "season": "First Planting",
            "months": [2, 3],
            "trading": "Begin new positions. Seeds go in the ground."
        },
        "late_spring": {
            "season": "Second Planting & Tending",
            "months": [4, 5],
            "trading": "Add to winners. Water what grows."
        },
        "monsoon": {
            "season": "Monsoon - Rain & Risk",
            "months": [6, 7, 8],
            "trading": "Volatility season. Storms bring growth AND destruction."
        },
        "harvest": {
            "season": "Harvest",
            "months": [9, 10],
            "trading": "Take profits. Harvest what you planted."
        },
        "preparation": {
            "season": "Preparation & Rest",
            "months": [11],
            "trading": "Reduce exposure. Prepare for winter."
        }
    }
    
    # TRADE NETWORK WISDOM - The Mogollon were traders
    TRADE_ROUTES = {
        "shell_from_sea": {
            "item": "Pacific shells",
            "lesson": "Value travels far. What is common there is rare here.",
            "trading": "Geographic arbitrage. Global markets have local prices."
        },
        "turquoise_south": {
            "item": "Turquoise to Mesoamerica",
            "lesson": "Know your buyer. Turquoise meant sky-water to Aztecs.",
            "trading": "Understand who's buying. Their reasons differ from yours."
        },
        "copper_bells": {
            "item": "Copper bells from Mexico",
            "lesson": "Sound carries information. Listen to distant signals.",
            "trading": "Global macro matters. Distant bells ring local changes."
        },
        "macaw_feathers": {
            "item": "Scarlet macaw feathers",
            "lesson": "Exotic is expensive. Rarity commands premium.",
            "trading": "Scarcity drives value. What is rare is valuable."
        },
        "obsidian_trade": {
            "item": "Obsidian tools",
            "lesson": "The best tools travel farthest. Quality is portable.",
            "trading": "Quality investments transcend markets."
        }
    }
    
    # MOGOLLON PROVERBS (Reconstructed from archaeological interpretation)
    PROVERBS = [
        {"proverb": "The mountain does not come to you; you must climb it",
         "trading": "Markets don't care about you. Adapt or fail."},
        {"proverb": "Water finds its way through rock, given time",
         "trading": "Persistence beats resistance. Keep flowing."},
        {"proverb": "The pot is made slowly, broken quickly",
         "trading": "Build positions carefully. They can break fast."},
        {"proverb": "Corn listens to the farmer who visits daily",
         "trading": "Tend your trades. Daily attention matters."},
        {"proverb": "The rabbit that runs too soon feeds no one",
         "trading": "Don't panic exit. Patience catches the meal."},
        {"proverb": "Three sisters grow together: corn, beans, squash",
         "trading": "Diversify. Different assets support each other."},
        {"proverb": "Fire in the pit house warms; fire on the roof destroys",
         "trading": "Controlled risk warms; uncontrolled risk destroys."},
        {"proverb": "The trader who walks returns; the trader who runs does not",
         "trading": "Slow and steady. Running traders make mistakes."},
        {"proverb": "When the rains fail, look to stored corn",
         "trading": "Keep reserves. Dry seasons come for everyone."},
        {"proverb": "The Mimbres painter releases the spirit through the hole",
         "trading": "Know when to let go. Release what has served its purpose."}
    ]
    
    # COSMOLOGY - Underground/Surface/Sky
    THREE_WORLDS = {
        "below": {
            "realm": "Underground - Ancestors, Origins",
            "trading": "Check historical patterns. The past informs the present."
        },
        "surface": {
            "realm": "Surface - Present Life, Action",
            "trading": "Act in the present. This is where trades are made."
        },
        "above": {
            "realm": "Sky - Future, Spirits, Guidance",
            "trading": "Look ahead. Project future moves."
        }
    }
    
    def __init__(self):
        """Initialize the Mogollon Wisdom Library."""
        pass
    
    def get_mimbres_symbol(self, btc_change: float) -> Dict:
        """Get a Mimbres pottery symbol based on market conditions."""
        if btc_change > 5:
            return {"symbol": "bird", **self.MIMBRES_SYMBOLS["bird"],
                    "message": "The bird soars high. Sky is the limit."}
        elif btc_change > 2:
            return {"symbol": "bighorn_sheep", **self.MIMBRES_SYMBOLS["bighorn_sheep"],
                    "message": "Climbing the mountain. Stay sure-footed."}
        elif btc_change > 0:
            return {"symbol": "rabbit", **self.MIMBRES_SYMBOLS["rabbit"],
                    "message": "The rabbit hops forward. Small gains."}
        elif btc_change > -2:
            return {"symbol": "turtle", **self.MIMBRES_SYMBOLS["turtle"],
                    "message": "The turtle waits. Patience."}
        elif btc_change > -5:
            return {"symbol": "snake", **self.MIMBRES_SYMBOLS["snake"],
                    "message": "The snake sheds skin. Transform."}
        else:
            return {"symbol": "bear", **self.MIMBRES_SYMBOLS["bear"],
                    "message": "The bear hibernates. Retreat and heal."}
    
    def get_desert_season(self) -> Dict:
        """Get current desert farming season and trading guidance."""
        month = datetime.now().month
        
        for season_name, season_data in self.DESERT_SEASONS.items():
            if month in season_data["months"]:
                return {"season_name": season_name, **season_data}
        
        return {"season_name": "transition", "season": "Between Seasons",
                "trading": "Transition period. Watch for shifts."}
    
    def get_pit_house_wisdom(self) -> Dict:
        """Get architectural wisdom from pit house philosophy."""
        wisdom_key = random.choice(list(self.PIT_HOUSE_WISDOM.keys()))
        return {
            "principle": wisdom_key.replace("_", " ").title(),
            "wisdom": self.PIT_HOUSE_WISDOM[wisdom_key],
            "trading": f"Apply: {self.PIT_HOUSE_WISDOM[wisdom_key]}"
        }
    
    def get_trade_route_lesson(self) -> Dict:
        """Get wisdom from ancient Mogollon trade networks."""
        route_key = random.choice(list(self.TRADE_ROUTES.keys()))
        return {"route": route_key, **self.TRADE_ROUTES[route_key]}
    
    def get_three_worlds_guidance(self, fear_greed: int) -> Dict:
        """Determine which of the Three Worlds to focus on."""
        if fear_greed < 30:
            return {"focus": "below", **self.THREE_WORLDS["below"],
                    "message": "Look to history. The ancestors faced this before."}
        elif fear_greed > 70:
            return {"focus": "above", **self.THREE_WORLDS["above"],
                    "message": "The sky spirits warn. What goes up must return."}
        else:
            return {"focus": "surface", **self.THREE_WORLDS["surface"],
                    "message": "Be present. Act in this moment."}
    
    def get_proverb(self) -> Dict:
        """Get a Mogollon proverb."""
        return random.choice(self.PROVERBS)
    
    def get_full_mogollon_reading(self, fear_greed: int, btc_price: float, btc_change: float) -> Dict:
        """Get complete Mogollon wisdom reading."""
        reading = {
            "mimbres_symbol": self.get_mimbres_symbol(btc_change),
            "desert_season": self.get_desert_season(),
            "pit_house": self.get_pit_house_wisdom(),
            "trade_route": self.get_trade_route_lesson(),
            "three_worlds": self.get_three_worlds_guidance(fear_greed),
            "proverb": self.get_proverb(),
            "synthesis": ""
        }
        
        reading["synthesis"] = self._synthesize_mogollon_wisdom(reading, fear_greed)
        return reading
    
    def _synthesize_mogollon_wisdom(self, reading: Dict, fear_greed: int) -> str:
        """Synthesize Mogollon wisdom into actionable insight."""
        symbol = reading["mimbres_symbol"]
        season = reading["desert_season"]["season"]
        proverb = reading["proverb"]["proverb"]
        
        if fear_greed < 30:
            return f"🏺 MOGOLLON SYNTHESIS: The Mimbres {symbol['symbol']} ({symbol['glyph']}) speaks: " \
                   f"'{symbol['message']}' In this {season}, we remember: '{proverb}' " \
                   f"The desert teaches survival. Store water, survive drought. " \
                   f"Trading: {reading['three_worlds']['trading']}"
        elif fear_greed > 70:
            return f"🏺 MOGOLLON SYNTHESIS: The Mimbres {symbol['symbol']} ({symbol['glyph']}) warns: " \
                   f"'{symbol['message']}' In this {season}, the elders say: '{proverb}' " \
                   f"The desert blooms then burns. Take what you need, no more. " \
                   f"Trading: {reading['three_worlds']['trading']}"
        else:
            return f"🏺 MOGOLLON SYNTHESIS: The Mimbres {symbol['symbol']} ({symbol['glyph']}) guides: " \
                   f"'{symbol['message']}' In this {season}, wisdom says: '{proverb}' " \
                   f"The pit house dweller thrives by balance. " \
                   f"Trading: {reading['three_worlds']['trading']}"
    
    def speak_wisdom(self) -> str:
        """Generate a Mogollon wisdom statement."""
        proverb = self.get_proverb()
        return f'🏺 "{proverb["proverb"]}" → 💹 {proverb["trading"]}'


# ═══════════════════════════════════════════════════════════════
# 𓂀 EGYPTIAN WISDOM LIBRARY - Land of the Pharaohs
# ═══════════════════════════════════════════════════════════════

class EgyptianWisdomLibrary:
    """
    Ancient Egyptian wisdom - 3,000+ years of civilization (3100 BCE - 30 BCE).
    
    The Egyptians mastered cycles, cosmic order (Ma'at), death/rebirth, and eternity.
    Their understanding of the Nile floods, stellar navigation, and sacred geometry
    offers profound insights for market cycles and trading.
    
    "As above, so below" - The Emerald Tablet
    """
    
    # THE NETJERU (GODS) - Divine market archetypes
    NETJERU = {
        "Ra": {
            "glyph": "☀️", "domain": "Sun, Creation, Kingship",
            "cycle": "Daily rebirth - rises, peaks, sets, travels underworld",
            "trading": "Markets have daily cycles. Morning momentum, midday chop, afternoon trend."
        },
        "Osiris": {
            "glyph": "🌿", "domain": "Death, Resurrection, Afterlife, Agriculture",
            "cycle": "Killed, dismembered, resurrected - eternal renewal",
            "trading": "Dead trades can resurrect. Patience. What dies can rise again."
        },
        "Isis": {
            "glyph": "🔮", "domain": "Magic, Healing, Wisdom, Protection",
            "cycle": "Gathered Osiris' pieces, resurrected him through magic",
            "trading": "Rebuild shattered portfolios piece by piece. Magic is persistence."
        },
        "Thoth": {
            "glyph": "📚", "domain": "Writing, Knowledge, Moon, Time, Mathematics",
            "cycle": "Keeper of records, inventor of writing, measurer of time",
            "trading": "Keep records. Journal trades. Knowledge compounds like interest."
        },
        "Anubis": {
            "glyph": "🐺", "domain": "Death, Embalming, Underworld Guide",
            "cycle": "Weighs hearts against Ma'at's feather",
            "trading": "Judge each trade honestly. Is it worthy? Weigh risk against reward."
        },
        "Horus": {
            "glyph": "🦅", "domain": "Sky, Kingship, War, Protection",
            "cycle": "Lost eye fighting Set, eye restored - symbol of wholeness",
            "trading": "Losses restore perspective. The Eye of Horus sees all."
        },
        "Set": {
            "glyph": "🔥", "domain": "Chaos, Storm, Desert, Violence",
            "cycle": "Killed Osiris, constant conflict with Horus",
            "trading": "Chaos is part of markets. Set brings volatility - trade it or avoid it."
        },
        "Ma'at": {
            "glyph": "⚖️", "domain": "Truth, Justice, Cosmic Order, Balance",
            "cycle": "Feather weighs hearts - maintains universal balance",
            "trading": "Markets seek balance. Extremes revert. Ma'at always wins."
        },
        "Ptah": {
            "glyph": "🔨", "domain": "Craftsmen, Creation, Architecture",
            "cycle": "Spoke the world into existence through thought and word",
            "trading": "Build your system carefully. Craft your edge. Create your destiny."
        },
        "Sekhmet": {
            "glyph": "🦁", "domain": "War, Destruction, Healing, Plague",
            "cycle": "Destroyer sent by Ra, calmed with beer/blood",
            "trading": "Markets can rage. Sekhmet energy destroys overleveraged positions."
        },
        "Hathor": {
            "glyph": "🐄", "domain": "Love, Beauty, Music, Fertility, Sky",
            "cycle": "Joy bringer, but can transform into Sekhmet",
            "trading": "Bull markets bring joy but can turn destructive. Stay alert."
        },
        "Sobek": {
            "glyph": "🐊", "domain": "Crocodiles, Nile, Military, Fertility",
            "cycle": "Patient hunter in the waters",
            "trading": "Like the crocodile - wait, then strike with overwhelming force."
        }
    }
    
    # THE 42 LAWS OF MA'AT - Ethical trading principles
    LAWS_OF_MAAT = [
        {"law": "I have not committed sin", "trading": "Trade ethically. No manipulation."},
        {"law": "I have not committed robbery with violence", "trading": "Don't force trades. Let them come."},
        {"law": "I have not stolen", "trading": "Earn your profits. No shortcuts."},
        {"law": "I have not slain men or women", "trading": "Don't blow up accounts - yours or others'."},
        {"law": "I have not stolen food", "trading": "Don't overtrade. Leave some for tomorrow."},
        {"law": "I have not swindled offerings", "trading": "Honor your commitments. Fill orders fairly."},
        {"law": "I have not stolen from God", "trading": "Pay your taxes. Respect the system."},
        {"law": "I have not told lies", "trading": "Be honest in your analysis. No hopium."},
        {"law": "I have not carried away food", "trading": "Take reasonable profits. Don't be greedy."},
        {"law": "I have not cursed", "trading": "Stay calm. Emotional trading loses money."},
        {"law": "I have not closed my ears to truth", "trading": "Listen to the market. It's always right."},
        {"law": "I have not committed adultery", "trading": "Stay faithful to your system. No FOMO."},
        {"law": "I have not made anyone cry", "trading": "Trade size you can handle losing."},
        {"law": "I have not felt sorrow without reason", "trading": "Don't mourn losses excessively. Move on."},
        {"law": "I have not assaulted anyone", "trading": "Don't revenge trade. Stay disciplined."},
        {"law": "I am not deceitful", "trading": "Know your true risk. No self-deception."},
        {"law": "I have not stolen anyone's land", "trading": "Respect others' positions. No front-running."},
        {"law": "I have not been an eavesdropper", "trading": "Do your own research. Don't blindly follow."},
        {"law": "I have not falsely accused anyone", "trading": "Don't blame the market. Take responsibility."},
        {"law": "I have not been angry without reason", "trading": "Losses are lessons, not injustices."},
        {"law": "I have not seduced anyone's wife", "trading": "Don't chase others' trades. Find your own."},
        {"law": "I have not polluted myself", "trading": "Keep your mind clear. No trading impaired."},
        {"law": "I have not terrorized anyone", "trading": "Trade calmly. Don't panic others."},
        {"law": "I have not disobeyed the Law", "trading": "Follow your rules. Always."},
        {"law": "I have not been excessively angry", "trading": "Cool head wins. Heat loses."},
        {"law": "I have not cursed God", "trading": "Respect the market gods. They're bigger than you."},
        {"law": "I have not behaved with violence", "trading": "Gentle entries, gentle exits. No FOMO buys."},
        {"law": "I have not caused disruption of peace", "trading": "Trade in harmony with trend."},
        {"law": "I have not acted hastily or without thought", "trading": "Plan the trade. Trade the plan."},
        {"law": "I have not overstepped my boundaries", "trading": "Know your edge. Stay in your lane."},
        {"law": "I have not exaggerated my words when speaking", "trading": "Realistic targets. No moonshot delusions."},
        {"law": "I have not worked evil", "trading": "Trade for growth, not destruction."},
        {"law": "I have not used evil thoughts, words or deeds", "trading": "Positive mindset. Abundance thinking."},
        {"law": "I have not polluted the water", "trading": "Don't pollute price discovery. Trade honestly."},
        {"law": "I have not spoken angrily or arrogantly", "trading": "Humility. The market humbles the arrogant."},
        {"law": "I have not cursed anyone in thought, word or deed", "trading": "Wish others well. Rising tide lifts all."},
        {"law": "I have not placed myself on a pedestal", "trading": "Stay humble. You're not smarter than the market."},
        {"law": "I have not stolen what belongs to God", "trading": "The trend is sacred. Don't fight it."},
        {"law": "I have not stolen from the dead", "trading": "Learn from failed traders. Honor their lessons."},
        {"law": "I have not taken food from a child", "trading": "Protect your capital. It's your future."},
        {"law": "I have not acted with insolence", "trading": "Respect volatility. It can destroy you."},
        {"law": "I have not destroyed property belonging to God", "trading": "Protect the market. Don't manipulate."}
    ]
    
    # NILE FLOOD SEASONS - The original cycle trading
    NILE_SEASONS = {
        "akhet": {
            "name": "Akhet", "meaning": "Inundation", "months": [7, 8, 9, 10],
            "glyph": "🌊", "event": "Nile floods, fertilizes land",
            "trading": "Flood of liquidity. Accumulate. The waters bring abundance."
        },
        "peret": {
            "name": "Peret", "meaning": "Emergence/Growing", "months": [11, 12, 1, 2],
            "glyph": "🌱", "event": "Waters recede, planting begins, crops grow",
            "trading": "Growth season. Let positions develop. Patience as seeds sprout."
        },
        "shemu": {
            "name": "Shemu", "meaning": "Harvest/Low Water", "months": [3, 4, 5, 6],
            "glyph": "🌾", "event": "Harvest crops before next flood",
            "trading": "Harvest season. Take profits. Prepare for next cycle."
        }
    }
    
    # BOOK OF THE DEAD - Journey through the underworld
    BOOK_OF_DEAD = {
        "spell_1": {
            "title": "Coming Forth by Day",
            "wisdom": "The soul emerges into light after darkness",
            "trading": "Bear markets end. You will emerge. Keep the faith."
        },
        "spell_17": {
            "title": "Coming and Going in the Underworld",
            "wisdom": "Know the paths through darkness",
            "trading": "Study bear market patterns. Know the path through."
        },
        "spell_30b": {
            "title": "Heart Scarab",
            "wisdom": "Do not stand as witness against me",
            "trading": "Your trade history is your witness. Make it honorable."
        },
        "spell_125": {
            "title": "Weighing of the Heart",
            "wisdom": "Heart weighed against Ma'at's feather",
            "trading": "Every trade is weighed. Is it balanced? Is it true?"
        },
        "spell_175": {
            "title": "Not Dying a Second Death",
            "wisdom": "Avoid permanent destruction",
            "trading": "Avoid account death. Position sizing is survival."
        }
    }
    
    # PYRAMID WISDOM - Sacred geometry
    PYRAMID_WISDOM = {
        "golden_ratio": {
            "principle": "Phi (1.618) in Great Pyramid proportions",
            "application": "Fibonacci retracements - 61.8% is key level",
            "trading": "Use 0.618 as key support/resistance. The ancients knew."
        },
        "orientation": {
            "principle": "Aligned to true north within 3/60th of a degree",
            "application": "Precision in execution",
            "trading": "Precision matters. Exact entries, exact stops."
        },
        "base_perimeter": {
            "principle": "Perimeter equals 2π times height",
            "application": "Circles and cycles embedded in structure",
            "trading": "Markets are cyclical. What goes around comes around."
        },
        "chamber_positions": {
            "principle": "King's Chamber at golden ratio height",
            "application": "Key levels exist at mathematical ratios",
            "trading": "33%, 50%, 61.8%, 78.6% - these levels matter."
        }
    }
    
    # EGYPTIAN PROVERBS - Wisdom of the Nile
    PROVERBS = [
        {"proverb": "The moon shines, but it does not warm", 
         "trading": "Analysis illuminates but doesn't profit. Execute."},
        {"proverb": "A man's heart is his own Neter (god)", 
         "trading": "Trust your gut after due diligence."},
        {"proverb": "He who is patient obtains", 
         "trading": "Patience. The Nile floods on schedule."},
        {"proverb": "The worst things: to be in bed and not sleep, to wait and not come",
         "trading": "Don't wait forever. Set time stops too."},
        {"proverb": "A beautiful thing is never perfect", 
         "trading": "No perfect trades. Take good enough."},
        {"proverb": "When the snake is in the house, no one needs to talk about it",
         "trading": "When risk is obvious, act. Don't discuss."},
        {"proverb": "Knowledge without wisdom is like water in the sand", 
         "trading": "Data without judgment is useless."},
        {"proverb": "The body is the house of God", 
         "trading": "Protect your capital. It's sacred."},
        {"proverb": "What you give, you get, ten times over", 
         "trading": "Risk-reward. Give 1, expect 10."},
        {"proverb": "The seed cannot sprout upwards without simultaneously sending roots into the ground",
         "trading": "Growth needs foundation. Build systems before scaling."},
        {"proverb": "Each truth you learn will be, for you, as new as if it had never been written",
         "trading": "You must learn your own lessons. Others' wisdom is secondhand."},
        {"proverb": "True teaching is not an accumulation of knowledge; it is an awakening",
         "trading": "Trading mastery is awareness, not information."}
    ]
    
    # HIEROGLYPHIC MARKET SYMBOLS
    HIEROGLYPHS = {
        "ankh": {"symbol": "☥", "meaning": "Life, Eternal life",
            "trading": "The Ankh - keep your account alive. Capital preservation."},
        "djed": {"symbol": "𓊽", "meaning": "Stability, Osiris' backbone",
            "trading": "The Djed - stability in your system. Stand firm."},
        "was": {"symbol": "𓌀", "meaning": "Power, Dominion",
            "trading": "The Was scepter - power over your emotions. Self-control."},
        "scarab": {"symbol": "🪲", "meaning": "Rebirth, Transformation, Sun",
            "trading": "The Scarab - transform losses into lessons. Rebirth daily."},
        "eye_of_horus": {"symbol": "𓂀", "meaning": "Protection, Royal power, Health",
            "trading": "Eye of Horus - watch the market. Vigilance protects."},
        "feather_of_maat": {"symbol": "🪶", "meaning": "Truth, Justice, Balance",
            "trading": "Feather of Ma'at - trade truthfully. Balance risk."}
    }
    
    # PHARAOH WISDOM - Rulers and their lessons
    PHARAOHS = {
        "khufu": {
            "name": "Khufu (Cheops)", "achievement": "Great Pyramid of Giza",
            "lesson": "Build for eternity. Think long-term.",
            "trading": "Position for decades, not days."
        },
        "hatshepsut": {
            "name": "Hatshepsut", "achievement": "Successful female pharaoh, trade expeditions",
            "lesson": "Defy expectations. Create prosperity through trade.",
            "trading": "Think different. Trade routes others ignore."
        },
        "thutmose_iii": {
            "name": "Thutmose III", "achievement": "Egypt's Napoleon - 17 campaigns, never lost",
            "lesson": "Systematic conquest. Methodical expansion.",
            "trading": "Systematic approach. Compound gains methodically."
        },
        "akhenaten": {
            "name": "Akhenaten", "achievement": "Religious revolutionary - one god (Aten)",
            "lesson": "Revolutionary change is risky but can transform.",
            "trading": "Paradigm shifts happen. Be ready to adapt beliefs."
        },
        "ramesses_ii": {
            "name": "Ramesses II", "achievement": "Longest reign (66 years), great builder",
            "lesson": "Longevity through adaptation. Survived wars, built monuments.",
            "trading": "Survive and thrive. Build wealth over decades."
        },
        "cleopatra": {
            "name": "Cleopatra VII", "achievement": "Last pharaoh, master of alliances",
            "lesson": "Adapt to changing powers. Alliances are survival.",
            "trading": "Know when regime is changing. Align with new powers."
        }
    }
    
    def __init__(self):
        """Initialize the Egyptian Wisdom Library."""
        self.civilization_years = 3000  # 3100 BCE to 30 BCE
        
    def get_deity_for_market(self, fear_greed: int, btc_change: float) -> Dict:
        """Select an Egyptian deity based on market conditions."""
        if fear_greed < 20:
            return {"deity": "Anubis", **self.NETJERU["Anubis"],
                    "message": "Anubis weighs the market. Death and rebirth ahead."}
        elif fear_greed < 30:
            return {"deity": "Osiris", **self.NETJERU["Osiris"],
                    "message": "Osiris speaks: What is dead shall rise again."}
        elif fear_greed > 80:
            return {"deity": "Sekhmet", **self.NETJERU["Sekhmet"],
                    "message": "Sekhmet rages! The lioness destroys the greedy."}
        elif fear_greed > 70:
            return {"deity": "Set", **self.NETJERU["Set"],
                    "message": "Set brings chaos. Storm approaches. Protect positions."}
        elif btc_change > 3:
            return {"deity": "Ra", **self.NETJERU["Ra"],
                    "message": "Ra rises triumphant! The sun god blesses this rally."}
        elif btc_change < -3:
            return {"deity": "Isis", **self.NETJERU["Isis"],
                    "message": "Isis gathers the pieces. She will restore what is broken."}
        else:
            return {"deity": "Ma'at", **self.NETJERU["Ma'at"],
                    "message": "Ma'at maintains balance. The market seeks equilibrium."}
    
    def get_nile_season(self) -> Dict:
        """Get current Nile season and trading guidance."""
        month = datetime.now().month
        
        for season_key, season_data in self.NILE_SEASONS.items():
            if month in season_data["months"]:
                return {"season": season_key, **season_data}
        
        return {"season": "transition", "name": "Between Seasons",
                "glyph": "🔄", "trading": "Transition period. Prepare for next cycle."}
    
    def get_law_of_maat(self) -> Dict:
        """Get a random Law of Ma'at."""
        return random.choice(self.LAWS_OF_MAAT)
    
    def get_book_of_dead_spell(self, fear_greed: int) -> Dict:
        """Get relevant Book of the Dead spell."""
        if fear_greed < 25:
            return {"spell": "spell_1", **self.BOOK_OF_DEAD["spell_1"]}
        elif fear_greed < 40:
            return {"spell": "spell_17", **self.BOOK_OF_DEAD["spell_17"]}
        elif fear_greed > 75:
            return {"spell": "spell_175", **self.BOOK_OF_DEAD["spell_175"]}
        else:
            return {"spell": "spell_125", **self.BOOK_OF_DEAD["spell_125"]}
    
    def get_pyramid_wisdom(self) -> Dict:
        """Get pyramid sacred geometry wisdom."""
        wisdom_key = random.choice(list(self.PYRAMID_WISDOM.keys()))
        return {"principle_name": wisdom_key, **self.PYRAMID_WISDOM[wisdom_key]}
    
    def get_hieroglyph(self, market_state: str) -> Dict:
        """Get relevant hieroglyphic symbol."""
        if market_state in ["EXTREME_FEAR", "FEAR"]:
            return {"hieroglyph": "scarab", **self.HIEROGLYPHS["scarab"]}
        elif market_state in ["EXTREME_GREED", "GREED"]:
            return {"hieroglyph": "feather_of_maat", **self.HIEROGLYPHS["feather_of_maat"]}
        else:
            return {"hieroglyph": "ankh", **self.HIEROGLYPHS["ankh"]}
    
    def get_pharaoh_lesson(self) -> Dict:
        """Get wisdom from a pharaoh."""
        pharaoh_key = random.choice(list(self.PHARAOHS.keys()))
        return {"pharaoh": pharaoh_key, **self.PHARAOHS[pharaoh_key]}
    
    def get_proverb(self) -> Dict:
        """Get an Egyptian proverb."""
        return random.choice(self.PROVERBS)
    
    def get_market_state(self, fear_greed: int) -> str:
        """Determine market state from Fear & Greed."""
        if fear_greed < 20:
            return "EXTREME_FEAR"
        elif fear_greed < 40:
            return "FEAR"
        elif fear_greed < 60:
            return "NEUTRAL"
        elif fear_greed < 80:
            return "GREED"
        else:
            return "EXTREME_GREED"
    
    def get_full_egyptian_reading(self, fear_greed: int, btc_price: float, btc_change: float) -> Dict:
        """Get complete Egyptian wisdom reading."""
        market_state = self.get_market_state(fear_greed)
        
        reading = {
            "deity": self.get_deity_for_market(fear_greed, btc_change),
            "nile_season": self.get_nile_season(),
            "law_of_maat": self.get_law_of_maat(),
            "book_of_dead": self.get_book_of_dead_spell(fear_greed),
            "pyramid": self.get_pyramid_wisdom(),
            "hieroglyph": self.get_hieroglyph(market_state),
            "pharaoh": self.get_pharaoh_lesson(),
            "proverb": self.get_proverb(),
            "market_state": market_state,
            "synthesis": ""
        }
        
        reading["synthesis"] = self._synthesize_egyptian_wisdom(reading, fear_greed, btc_change)
        return reading
    
    def _synthesize_egyptian_wisdom(self, reading: Dict, fear_greed: int, btc_change: float) -> str:
        """Synthesize Egyptian wisdom into actionable insight."""
        deity = reading["deity"]
        season = reading["nile_season"]
        proverb = reading["proverb"]["proverb"]
        
        if fear_greed < 30:
            return f"𓂀 EGYPTIAN SYNTHESIS: {deity['deity']} {deity['glyph']} speaks: '{deity['message']}' " \
                   f"In the season of {season['name']} ({season['glyph']}), the Nile says: {season['trading']} " \
                   f"The ancients taught: '{proverb}' - {reading['proverb']['trading']} " \
                   f"Osiris died and rose. So shall the market."
        elif fear_greed > 70:
            return f"𓂀 EGYPTIAN SYNTHESIS: {deity['deity']} {deity['glyph']} warns: '{deity['message']}' " \
                   f"In the season of {season['name']} ({season['glyph']}), remember: {season['trading']} " \
                   f"The ancients taught: '{proverb}' - {reading['proverb']['trading']} " \
                   f"Ma'at balances all. Excess invites Set's chaos."
        else:
            return f"𓂀 EGYPTIAN SYNTHESIS: {deity['deity']} {deity['glyph']} guides: '{deity['message']}' " \
                   f"In the season of {season['name']} ({season['glyph']}): {season['trading']} " \
                   f"The ancients taught: '{proverb}' - {reading['proverb']['trading']} " \
                   f"Follow Ma'at. Balance is eternal."
    
    def speak_wisdom(self) -> str:
        """Generate an Egyptian wisdom statement."""
        proverb = self.get_proverb()
        return f'𓂀 "{proverb["proverb"]}" → 💹 {proverb["trading"]}'


# ═══════════════════════════════════════════════════════════════
# � PYTHAGOREAN & MUSICA UNIVERSALIS LIBRARY
# Sacred Mathematics and the Music of the Spheres
# ═══════════════════════════════════════════════════════════════

class PythagoreanWisdomLibrary:
    """
    Pythagoras of Samos (c. 570-495 BCE) founded a philosophical school
    that saw mathematics as the key to understanding the universe.
    
    "All is Number" - The Pythagorean creed
    
    Musica Universalis (Music of the Spheres) - the ancient philosophical
    concept that the movements of celestial bodies produce a form of music,
    inaudible to humans but mathematically perfect.
    
    From sacred ratios to planetary harmonics, this library brings
    2,500 years of mathematical mysticism to trading.
    """
    
    # THE SACRED NUMBERS - Each with trading meaning
    SACRED_NUMBERS = {
        1: {
            "name": "Monad", "symbol": "●", "meaning": "Unity, Source, The One",
            "pythagorean": "The source of all numbers. Neither odd nor even.",
            "trading": "Start with one. Master one strategy before adding more."
        },
        2: {
            "name": "Dyad", "symbol": "●●", "meaning": "Duality, Opposition, Balance",
            "pythagorean": "The first feminine number. Creates polarity.",
            "trading": "Every trade has two sides. For every buyer, a seller."
        },
        3: {
            "name": "Triad", "symbol": "▲", "meaning": "Harmony, Wisdom, Understanding",
            "pythagorean": "First true number (beginning, middle, end). First masculine.",
            "trading": "Three confirmations before entry. Triple top/bottom patterns."
        },
        4: {
            "name": "Tetrad", "symbol": "□", "meaning": "Stability, Foundation, Earth",
            "pythagorean": "Justice (equal sides). 4 elements, 4 seasons.",
            "trading": "Four pillars: Entry, Stop, Target, Position Size."
        },
        5: {
            "name": "Pentad", "symbol": "⭐", "meaning": "Life, Health, Vitality",
            "pythagorean": "Marriage of 2+3. The human number (5 senses, fingers).",
            "trading": "Risk only 5% maximum per trade. The human limit."
        },
        6: {
            "name": "Hexad", "symbol": "✡", "meaning": "Perfection, Creation, Harmony",
            "pythagorean": "First perfect number (1+2+3=6). Creation took 6 days.",
            "trading": "Perfect setups are rare. Wait for 6/6 criteria match."
        },
        7: {
            "name": "Heptad", "symbol": "🌙", "meaning": "Rest, Completion, Cycles",
            "pythagorean": "Virgin number (doesn't produce within decade). 7 planets.",
            "trading": "7-day cycles in markets. Weekly closes matter."
        },
        8: {
            "name": "Ogdoad", "symbol": "∞", "meaning": "Infinity, Regeneration, Power",
            "pythagorean": "First cube (2³). Octave in music.",
            "trading": "Compound returns are cubic growth. The power of 8."
        },
        9: {
            "name": "Ennead", "symbol": "◎", "meaning": "Completion, Wisdom, Attainment",
            "pythagorean": "3×3, limit of single digits. Horizon of numbers.",
            "trading": "9 losing trades in 10 can still profit. Manage the 1."
        },
        10: {
            "name": "Decad", "symbol": "✺", "meaning": "Completion, Return to Unity",
            "pythagorean": "The Tetractys sum (1+2+3+4=10). Contains all.",
            "trading": "10x returns are possible with patience. Full cycle."
        }
    }
    
    # THE TETRACTYS - Sacred triangle of Pythagoras
    TETRACTYS = {
        "structure": """
              ●        (1) - Monad: Divine Source
             ● ●       (2) - Dyad: Duality/Pairs
            ● ● ●      (3) - Triad: Harmony
           ● ● ● ●     (4) - Tetrad: Manifestation
        """,
        "meaning": "1+2+3+4=10 - All existence emerges from this pattern",
        "trading": "Build positions in layers: 1 probe, 2 confirmation, 3 core, 4 full size"
    }
    
    # SACRED RATIOS - The golden proportions
    SACRED_RATIOS = {
        "phi": {
            "value": 1.618, "symbol": "φ", "name": "Golden Ratio",
            "found_in": "Nautilus shells, galaxies, DNA, Parthenon",
            "trading": "Fibonacci extensions: 1.618, 2.618, 4.236 are key profit targets."
        },
        "inverse_phi": {
            "value": 0.618, "symbol": "1/φ", "name": "Divine Proportion",
            "found_in": "Human body proportions, plant growth",
            "trading": "61.8% retracement is the most important Fibonacci level."
        },
        "sqrt_2": {
            "value": 1.414, "symbol": "√2", "name": "Pythagoras' Constant",
            "found_in": "Diagonal of unit square, A4 paper ratio",
            "trading": "1.414 extension often marks intermediate targets."
        },
        "sqrt_3": {
            "value": 1.732, "symbol": "√3", "name": "Theodorus' Constant",
            "found_in": "Hexagonal patterns, crystals",
            "trading": "The space between 1.618 and 2.0 - caution zone."
        },
        "sqrt_5": {
            "value": 2.236, "symbol": "√5", "name": "Root of Phi",
            "found_in": "Pentagon, golden ratio construction",
            "trading": "φ = (1+√5)/2. The root of all Fibonacci."
        },
        "pi": {
            "value": 3.14159, "symbol": "π", "name": "Circle Ratio",
            "found_in": "All circles, cycles, waves",
            "trading": "Markets are cyclical. π connects all cycles."
        }
    }
    
    # MUSICA UNIVERSALIS - The Music of the Spheres
    PLANETARY_HARMONICS = {
        "moon": {
            "interval": "Tone", "ratio": "9:8", "glyph": "☽",
            "orbit_days": 27.3, "note": "B",
            "quality": "Emotions, intuition, cycles",
            "trading": "Lunar cycles affect sentiment. 27-day rhythm in markets."
        },
        "mercury": {
            "interval": "Semitone", "ratio": "256:243", "glyph": "☿",
            "orbit_days": 88, "note": "C",
            "quality": "Communication, speed, commerce",
            "trading": "Fast moves, quick reversals. Messenger of market shifts."
        },
        "venus": {
            "interval": "Minor Third", "ratio": "6:5", "glyph": "♀",
            "orbit_days": 225, "note": "E",
            "quality": "Beauty, harmony, attraction",
            "trading": "Harmony in price action. Beautiful setups work best."
        },
        "sun": {
            "interval": "Perfect Fourth", "ratio": "4:3", "glyph": "☉",
            "orbit_days": 365.25, "note": "F",
            "quality": "Life, vitality, center",
            "trading": "Annual cycles dominate. The sun is trend - follow it."
        },
        "mars": {
            "interval": "Perfect Fifth", "ratio": "3:2", "glyph": "♂",
            "orbit_days": 687, "note": "G",
            "quality": "Energy, war, action",
            "trading": "The most consonant interval. Strong momentum plays."
        },
        "jupiter": {
            "interval": "Major Sixth", "ratio": "5:3", "glyph": "♃",
            "orbit_days": 4333, "note": "A",
            "quality": "Expansion, abundance, luck",
            "trading": "12-year cycles of expansion. Jupiter expands what it touches."
        },
        "saturn": {
            "interval": "Octave", "ratio": "2:1", "glyph": "♄",
            "orbit_days": 10759, "note": "C (octave)",
            "quality": "Structure, time, limits, karma",
            "trading": "29.5 year cycle. Saturn returns bring reckoning. Respect time."
        }
    }
    
    # PYTHAGOREAN MUSICAL INTERVALS - For reading market harmonics
    INTERVALS = {
        "unison": {"ratio": "1:1", "cents": 0, "quality": "Perfect consonance",
                   "trading": "Price at support/resistance. Perfect balance point."},
        "octave": {"ratio": "2:1", "cents": 1200, "quality": "Perfect consonance",
                   "trading": "Price doubling. 100% gain. The ultimate target."},
        "fifth": {"ratio": "3:2", "cents": 702, "quality": "Perfect consonance",
                  "trading": "50% move. Strong harmonic. Natural target."},
        "fourth": {"ratio": "4:3", "cents": 498, "quality": "Perfect consonance",
                   "trading": "33% move. Stable harmonic. Good partial target."},
        "major_third": {"ratio": "5:4", "cents": 386, "quality": "Imperfect consonance",
                        "trading": "25% move. Pleasant but unstable. Take some profit."},
        "minor_third": {"ratio": "6:5", "cents": 316, "quality": "Imperfect consonance",
                        "trading": "20% move. Melancholic. Caution zone."},
        "major_second": {"ratio": "9:8", "cents": 204, "quality": "Dissonance",
                         "trading": "12.5% move. Tension. Needs resolution."},
        "minor_second": {"ratio": "16:15", "cents": 112, "quality": "Sharp dissonance",
                         "trading": "6-7% move. Maximum tension. Reversal imminent."}
    }
    
    # PYTHAGOREAN MAXIMS - The golden sayings
    MAXIMS = [
        {"maxim": "All is Number", "context": "The fundamental Pythagorean belief",
         "trading": "Price is the ultimate truth. Numbers don't lie."},
        {"maxim": "Number rules the universe", "context": "Mathematical order underlies chaos",
         "trading": "Patterns repeat. Find the numbers, find the edge."},
        {"maxim": "Do not stir fire with a sword", "context": "Don't aggravate conflict",
         "trading": "Don't revenge trade. Don't add to losers in anger."},
        {"maxim": "Do not eat your heart", "context": "Don't consume yourself with worry",
         "trading": "Don't obsess over losses. Move forward."},
        {"maxim": "When you rise from bed, roll up the bedclothes", "context": "Leave no trace",
         "trading": "Close trades cleanly. No loose ends."},
        {"maxim": "Do not look in a mirror by lamplight", "context": "Self-deception in dim light",
         "trading": "Don't analyze trades when emotional. Wait for clarity."},
        {"maxim": "Above all, respect yourself", "context": "Self-mastery first",
         "trading": "Protect your capital - it's your self-respect manifest."},
        {"maxim": "The oldest, shortest words are the best", "context": "Simplicity is truth",
         "trading": "Simple strategies outperform complex ones."},
        {"maxim": "There is geometry in the humming of strings", "context": "Math in music",
         "trading": "There is geometry in price action. Learn to see it."},
        {"maxim": "Rest satisfied with doing well, and leave others to talk of you as they please",
         "context": "Focus on action, not reputation",
         "trading": "Focus on your P&L, not what others say about your trades."},
        {"maxim": "Strength of mind rests in sobriety", "context": "Clear mind is strong mind",
         "trading": "Trade sober. Clear mind, clear decisions."},
        {"maxim": "Choose always the way that seems best, however rough it may be",
         "context": "The right path is often difficult",
         "trading": "The disciplined trade often feels wrong. Do it anyway."}
    ]
    
    # THE PYTHAGOREAN MEANS - For calculating targets
    MEANS = {
        "arithmetic": {
            "formula": "(a + b) / 2",
            "meaning": "The common average",
            "trading": "Midpoint between support and resistance. Fair value."
        },
        "geometric": {
            "formula": "√(a × b)",
            "meaning": "Proportional average",
            "trading": "Geometric mean of high and low. Key pivot level."
        },
        "harmonic": {
            "formula": "2ab / (a + b)",
            "meaning": "Musical average",
            "trading": "Harmonic mean often marks reversal. The musical price."
        }
    }
    
    # PYTHAGOREAN BROTHERHOOD RULES - For trading discipline
    BROTHERHOOD_RULES = [
        {"rule": "Silence for 5 years before speaking", 
         "trading": "Paper trade 5 months before risking real money."},
        {"rule": "Vegetarian diet for purity",
         "trading": "Clean inputs: no FOMO, no FUD, no noise."},
        {"rule": "Property held in common",
         "trading": "Diversify. No single position dominates."},
        {"rule": "Rise before dawn for contemplation",
         "trading": "Pre-market preparation is essential."},
        {"rule": "Evening review of the day's actions",
         "trading": "Daily trade journal. Review every evening."},
        {"rule": "Secrecy about inner teachings",
         "trading": "Keep your edge secret. Don't share strategy."}
    ]
    
    # PLATONIC SOLIDS - Universal forms in markets
    PLATONIC_SOLIDS = {
        "tetrahedron": {
            "faces": 4, "element": "Fire", "symbol": "🔺",
            "meaning": "Transformation, energy",
            "trading": "4-point patterns. Breakout energy. Triangles."
        },
        "cube": {
            "faces": 6, "element": "Earth", "symbol": "⬛",
            "meaning": "Stability, foundation",
            "trading": "6-point consolidation. Stable bases. Boxes."
        },
        "octahedron": {
            "faces": 8, "element": "Air", "symbol": "◆",
            "meaning": "Balance, equilibrium",
            "trading": "8-wave Elliott patterns. Air = swift movement."
        },
        "dodecahedron": {
            "faces": 12, "element": "Aether/Universe", "symbol": "⬡",
            "meaning": "The cosmos, completeness",
            "trading": "12-month cycles. Annual patterns. Universal truth."
        },
        "icosahedron": {
            "faces": 20, "element": "Water", "symbol": "💧",
            "meaning": "Flow, emotion, change",
            "trading": "20-day moving average. Water flows like price."
        }
    }
    
    def __init__(self):
        """Initialize the Pythagorean Wisdom Library."""
        self.school_founded = -530  # 530 BCE
        self.teachings_years = 2500  # Years of influence
    
    def get_sacred_number(self, value: float) -> Dict:
        """Get wisdom from a sacred number based on market value."""
        # Use last digit or reduce to single digit
        if value > 0:
            reduced = int(abs(value)) % 10
            if reduced == 0:
                reduced = 10
        else:
            reduced = 1
        return {"number": reduced, **self.SACRED_NUMBERS.get(reduced, self.SACRED_NUMBERS[1])}
    
    def get_ratio_for_market(self, btc_change: float) -> Dict:
        """Get relevant sacred ratio based on market movement."""
        abs_change = abs(btc_change)
        
        if abs_change < 1:
            return {"ratio_name": "inverse_phi", **self.SACRED_RATIOS["inverse_phi"]}
        elif abs_change < 2:
            return {"ratio_name": "phi", **self.SACRED_RATIOS["phi"]}
        elif abs_change < 3:
            return {"ratio_name": "sqrt_2", **self.SACRED_RATIOS["sqrt_2"]}
        elif abs_change < 5:
            return {"ratio_name": "sqrt_5", **self.SACRED_RATIOS["sqrt_5"]}
        else:
            return {"ratio_name": "pi", **self.SACRED_RATIOS["pi"]}
    
    def get_planetary_harmonic(self, fear_greed: int) -> Dict:
        """Get planetary harmonic based on market sentiment."""
        if fear_greed < 15:
            return {"planet": "saturn", **self.PLANETARY_HARMONICS["saturn"]}
        elif fear_greed < 25:
            return {"planet": "moon", **self.PLANETARY_HARMONICS["moon"]}
        elif fear_greed < 40:
            return {"planet": "mercury", **self.PLANETARY_HARMONICS["mercury"]}
        elif fear_greed < 60:
            return {"planet": "sun", **self.PLANETARY_HARMONICS["sun"]}
        elif fear_greed < 75:
            return {"planet": "venus", **self.PLANETARY_HARMONICS["venus"]}
        elif fear_greed < 85:
            return {"planet": "mars", **self.PLANETARY_HARMONICS["mars"]}
        else:
            return {"planet": "jupiter", **self.PLANETARY_HARMONICS["jupiter"]}
    
    def get_musical_interval(self, btc_change: float) -> Dict:
        """Get musical interval based on price movement."""
        abs_change = abs(btc_change)
        
        if abs_change < 1:
            return {"interval": "unison", **self.INTERVALS["unison"]}
        elif abs_change < 7:
            return {"interval": "minor_second", **self.INTERVALS["minor_second"]}
        elif abs_change < 15:
            return {"interval": "major_second", **self.INTERVALS["major_second"]}
        elif abs_change < 22:
            return {"interval": "minor_third", **self.INTERVALS["minor_third"]}
        elif abs_change < 28:
            return {"interval": "major_third", **self.INTERVALS["major_third"]}
        elif abs_change < 40:
            return {"interval": "fourth", **self.INTERVALS["fourth"]}
        elif abs_change < 60:
            return {"interval": "fifth", **self.INTERVALS["fifth"]}
        else:
            return {"interval": "octave", **self.INTERVALS["octave"]}
    
    def get_maxim(self) -> Dict:
        """Get a random Pythagorean maxim."""
        return random.choice(self.MAXIMS)
    
    def get_platonic_solid(self, market_state: str) -> Dict:
        """Get relevant Platonic solid for market state."""
        if market_state in ["EXTREME_FEAR"]:
            return {"solid": "icosahedron", **self.PLATONIC_SOLIDS["icosahedron"]}
        elif market_state in ["FEAR"]:
            return {"solid": "tetrahedron", **self.PLATONIC_SOLIDS["tetrahedron"]}
        elif market_state in ["NEUTRAL"]:
            return {"solid": "cube", **self.PLATONIC_SOLIDS["cube"]}
        elif market_state in ["GREED"]:
            return {"solid": "octahedron", **self.PLATONIC_SOLIDS["octahedron"]}
        else:  # EXTREME_GREED
            return {"solid": "dodecahedron", **self.PLATONIC_SOLIDS["dodecahedron"]}
    
    def get_mean_calculation(self, high: float, low: float) -> Dict:
        """Calculate all three Pythagorean means."""
        arithmetic = (high + low) / 2
        geometric = (high * low) ** 0.5
        harmonic = (2 * high * low) / (high + low) if (high + low) > 0 else 0
        
        return {
            "arithmetic": {"value": arithmetic, **self.MEANS["arithmetic"]},
            "geometric": {"value": geometric, **self.MEANS["geometric"]},
            "harmonic": {"value": harmonic, **self.MEANS["harmonic"]}
        }
    
    def get_brotherhood_rule(self) -> Dict:
        """Get a Pythagorean Brotherhood discipline rule."""
        return random.choice(self.BROTHERHOOD_RULES)
    
    def get_market_state(self, fear_greed: int) -> str:
        """Determine market state from Fear & Greed."""
        if fear_greed < 20:
            return "EXTREME_FEAR"
        elif fear_greed < 40:
            return "FEAR"
        elif fear_greed < 60:
            return "NEUTRAL"
        elif fear_greed < 80:
            return "GREED"
        else:
            return "EXTREME_GREED"
    
    def get_full_pythagorean_reading(self, fear_greed: int, btc_price: float, btc_change: float) -> Dict:
        """Get complete Pythagorean and Musica Universalis reading."""
        market_state = self.get_market_state(fear_greed)
        
        # Calculate approximate high/low for means
        high = btc_price * 1.1
        low = btc_price * 0.9
        
        reading = {
            "sacred_number": self.get_sacred_number(btc_price),
            "ratio": self.get_ratio_for_market(btc_change),
            "planet": self.get_planetary_harmonic(fear_greed),
            "interval": self.get_musical_interval(btc_change),
            "maxim": self.get_maxim(),
            "solid": self.get_platonic_solid(market_state),
            "means": self.get_mean_calculation(high, low),
            "brotherhood": self.get_brotherhood_rule(),
            "tetractys": self.TETRACTYS,
            "market_state": market_state,
            "synthesis": ""
        }
        
        reading["synthesis"] = self._synthesize_pythagorean_wisdom(reading, fear_greed, btc_change)
        return reading
    
    def _synthesize_pythagorean_wisdom(self, reading: Dict, fear_greed: int, btc_change: float) -> str:
        """Synthesize Pythagorean wisdom into actionable insight."""
        number = reading["sacred_number"]
        planet = reading["planet"]
        maxim = reading["maxim"]["maxim"]
        
        if fear_greed < 30:
            return f"🔢 PYTHAGOREAN SYNTHESIS: The {number['name']} ({number['number']}) rules this hour. " \
                   f"{planet['glyph']} {planet['planet'].title()} sounds its {planet['interval']} in the celestial music. " \
                   f"Pythagoras taught: '{maxim}' - {reading['maxim']['trading']} " \
                   f"In fear, remember: Number rules the universe. This too is mathematical."
        elif fear_greed > 70:
            return f"🔢 PYTHAGOREAN SYNTHESIS: The {number['name']} ({number['number']}) warns of excess. " \
                   f"{planet['glyph']} {planet['planet'].title()} plays the {planet['interval']} - expansion nears limit. " \
                   f"Pythagoras taught: '{maxim}' - {reading['maxim']['trading']} " \
                   f"The octave completes and returns to unity. Prepare for cycle's end."
        else:
            return f"🔢 PYTHAGOREAN SYNTHESIS: The {number['name']} ({number['number']}) maintains harmony. " \
                   f"{planet['glyph']} {planet['planet'].title()} resonates at the {planet['interval']}. " \
                   f"Pythagoras taught: '{maxim}' - {reading['maxim']['trading']} " \
                   f"All is Number. The spheres sing in mathematical perfection."
    
    def speak_wisdom(self) -> str:
        """Generate a Pythagorean wisdom statement."""
        maxim = self.get_maxim()
        return f'🔢 "{maxim["maxim"]}" → 💹 {maxim["trading"]}'


# ═══════════════════════════════════════════════════════════════
# �👑 PLANTAGENET WISDOM LIBRARY - Lions of England (1154-1485)
# ═══════════════════════════════════════════════════════════════

class PlantagenetWisdomLibrary:
    """
    The House of Plantagenet ruled England for 331 years (1154-1485).
    
    From Henry II to Richard III, they mastered warfare, law, governance, and survival.
    Their strategies in the Crusades, Hundred Years War, and Wars of the Roses
    offer profound lessons for trading in volatile markets.
    
    "Dieu et mon droit" - God and my right
    """
    
    # THE PLANTAGENET KINGS - Each with trading wisdom
    KINGS = {
        "henry_ii": {
            "name": "Henry II", "reign": "1154-1189", "glyph": "👑",
            "epithet": "The Lawgiver",
            "achievement": "Created common law, controlled vast Angevin Empire",
            "trading": "Build systems that outlast you. Common law = consistent rules."
        },
        "richard_i": {
            "name": "Richard I", "reign": "1189-1199", "glyph": "🦁",
            "epithet": "The Lionheart",
            "achievement": "Crusader king, warrior supreme, master of siege warfare",
            "trading": "Bold action when the time is right. The lion strikes decisively."
        },
        "john": {
            "name": "John", "reign": "1199-1216", "glyph": "📜",
            "epithet": "Lackland",
            "achievement": "Signed Magna Carta (forced), lost French territories",
            "trading": "Know when you're beaten. Forced capitulation saves what remains."
        },
        "henry_iii": {
            "name": "Henry III", "reign": "1216-1272", "glyph": "⛪",
            "epithet": "The Builder",
            "achievement": "Westminster Abbey, long reign through turbulence",
            "trading": "Build during chaos. Long-term vision beats short-term panic."
        },
        "edward_i": {
            "name": "Edward I", "reign": "1272-1307", "glyph": "⚔️",
            "epithet": "Longshanks / Hammer of the Scots",
            "achievement": "Conquered Wales, nearly Scotland, reformed Parliament",
            "trading": "Expand systematically. Consolidate before next conquest."
        },
        "edward_ii": {
            "name": "Edward II", "reign": "1307-1327", "glyph": "💔",
            "epithet": "The Unfortunate",
            "achievement": "Lost Bannockburn, deposed by wife and nobles",
            "trading": "Poor leadership destroys everything. Trust the wrong people = ruin."
        },
        "edward_iii": {
            "name": "Edward III", "reign": "1327-1377", "glyph": "🏹",
            "epithet": "The Glorious",
            "achievement": "Crecy, Poitiers, founded Order of the Garter",
            "trading": "Peak performance era. Maximize gains when you're winning."
        },
        "richard_ii": {
            "name": "Richard II", "reign": "1377-1399", "glyph": "🦚",
            "epithet": "The Vain",
            "achievement": "Ended Peasants' Revolt, but lost throne to Bolingbroke",
            "trading": "Arrogance before the fall. Stay humble or lose everything."
        },
        "henry_iv": {
            "name": "Henry IV", "reign": "1399-1413", "glyph": "🔱",
            "epithet": "Bolingbroke",
            "achievement": "Usurped throne, defended it against rebellions",
            "trading": "Seize opportunity when it appears. Then defend relentlessly."
        },
        "henry_v": {
            "name": "Henry V", "reign": "1413-1422", "glyph": "⚜️",
            "epithet": "The Conqueror",
            "achievement": "Agincourt, Treaty of Troyes, nearly united crowns",
            "trading": "Against all odds, the prepared mind wins. Study your enemy."
        },
        "henry_vi": {
            "name": "Henry VI", "reign": "1422-1461/1470-1471", "glyph": "📿",
            "epithet": "The Pious",
            "achievement": "Lost France, lost mind, lost throne (twice)",
            "trading": "Weakness invites wolves. Indecision is the worst decision."
        },
        "edward_iv": {
            "name": "Edward IV", "reign": "1461-1470/1471-1483", "glyph": "☀️",
            "epithet": "The Sun King",
            "achievement": "Won Wars of the Roses, restored Yorkist prosperity",
            "trading": "Comeback king. Lost everything, regained everything. Never quit."
        },
        "richard_iii": {
            "name": "Richard III", "reign": "1483-1485", "glyph": "🐗",
            "epithet": "The Last Plantagenet",
            "achievement": "Died fighting at Bosworth, 'A horse! A horse!'",
            "trading": "The final stand. Sometimes you lose. Die with honor."
        }
    }
    
    # MAGNA CARTA PRINCIPLES (1215) - Foundation of rights
    MAGNA_CARTA = {
        "clause_39": {
            "text": "No free man shall be seized, imprisoned, or stripped of his rights except by lawful judgment",
            "trading": "Have rules. Follow rules. No arbitrary decisions."
        },
        "clause_40": {
            "text": "To no one will we sell, deny, or delay right or justice",
            "trading": "Execute trades promptly. Delayed decisions are losses."
        },
        "clause_12": {
            "text": "No tax shall be imposed without common counsel of the kingdom",
            "trading": "Know your costs before trading. Fees, spread, slippage."
        },
        "clause_20": {
            "text": "A fine shall be proportioned to the gravity of the offense",
            "trading": "Position size relative to conviction. Small mistakes = small losses."
        },
        "clause_41": {
            "text": "All merchants shall have safe conduct to enter and leave England",
            "trading": "Liquidity is sacred. Markets must flow freely."
        }
    }
    
    # HUNDRED YEARS WAR STRATEGIES (1337-1453)
    HUNDRED_YEARS_WAR = {
        "chevauchee": {
            "tactic": "Devastating raids through enemy territory",
            "commander": "Edward III, Black Prince",
            "trading": "Quick strikes for profit. In and out. Don't occupy."
        },
        "longbow_dominance": {
            "tactic": "English longbowmen destroyed French cavalry",
            "battle": "Crecy (1346), Poitiers (1356), Agincourt (1415)",
            "trading": "Superior tools beat brute force. Technology advantage."
        },
        "defensive_position": {
            "tactic": "Let enemy attack your prepared position",
            "example": "Agincourt - Henry V's tired, sick army defeated 3x French",
            "trading": "Defense wins. Let the market come to your price."
        },
        "treaty_of_troyes": {
            "tactic": "Diplomatic masterstroke - Henry V to inherit France",
            "year": "1420",
            "trading": "When winning massively, lock in gains with agreements."
        },
        "siege_warfare": {
            "tactic": "Patience in taking fortified positions",
            "example": "Calais held for 200 years after siege",
            "trading": "Some positions take time. Patience with strong holdings."
        }
    }
    
    # WARS OF THE ROSES (1455-1487) - Civil war trading
    WARS_OF_ROSES = {
        "house_of_york": {
            "symbol": "White Rose",
            "glyph": "☀️",
            "leaders": "Richard of York, Edward IV, Richard III",
            "strategy": "Aggressive, decisive battles",
            "trading": "Attack mode. Take what you want."
        },
        "house_of_lancaster": {
            "symbol": "Red Rose",
            "glyph": "🌹",
            "leaders": "Henry VI, Margaret of Anjou",
            "strategy": "Defensive, alliance-building",
            "trading": "Defensive mode. Build coalitions."
        },
        "kingmaker": {
            "figure": "Warwick the Kingmaker",
            "lesson": "Made and unmade kings, then died at Barnet",
            "trading": "Influence has limits. Even kingmakers fall."
        },
        "battle_of_towton": {
            "date": "1461",
            "note": "Bloodiest battle on English soil - 28,000 dead",
            "trading": "Civil wars (crypto wars) are brutal. Pick your side carefully."
        },
        "battle_of_bosworth": {
            "date": "1485",
            "note": "Richard III killed, Tudor dynasty begins",
            "trading": "Regime change. Adapt to new rulers (regulations)."
        }
    }
    
    # PLANTAGENET PROVERBS & MOTTOS
    PROVERBS = [
        {"proverb": "Dieu et mon droit - God and my right",
         "trading": "Trade with conviction. Your analysis is your right."},
        {"proverb": "Honi soit qui mal y pense - Shame on him who thinks evil of it",
         "trading": "Ignore the doubters. Execute your plan."},
        {"proverb": "Ich dien - I serve",
         "trading": "Serve the market, not your ego. The market is always right."},
        {"proverb": "The king is dead, long live the king",
         "trading": "One trade ends, another begins. Continuity over sentiment."},
        {"proverb": "Uneasy lies the head that wears a crown",
         "trading": "Leadership is burden. Big positions = big responsibility."},
        {"proverb": "A horse! A horse! My kingdom for a horse!",
         "trading": "Desperation trades are the worst trades. Never trade from need."},
        {"proverb": "Now is the winter of our discontent",
         "trading": "Bear markets end. Winter precedes spring."},
        {"proverb": "We few, we happy few, we band of brothers",
         "trading": "Quality over quantity. Few good trades beat many bad ones."},
        {"proverb": "Once more unto the breach, dear friends",
         "trading": "Persistence. Try again. The breach will fall."},
        {"proverb": "Let slip the dogs of war",
         "trading": "When you commit, commit fully. Half-measures fail."}
    ]
    
    # ANGEVIN EMPIRE LESSONS - Managing vast territories
    ANGEVIN_EMPIRE = {
        "diversification": {
            "territory": "England, Normandy, Anjou, Aquitaine, Ireland",
            "lesson": "Henry II ruled more of France than the French king",
            "trading": "Diversify holdings. Don't put everything in one kingdom."
        },
        "overextension": {
            "problem": "Empire too large to control, sons rebelled",
            "lesson": "Henry II died fighting his own sons",
            "trading": "Know your limits. Overextension leads to collapse."
        },
        "succession": {
            "issue": "No clear succession = civil war",
            "lesson": "Plan for exit. Who inherits your positions?",
            "trading": "Have an exit strategy before you enter."
        }
    }
    
    # CRUSADER LESSONS - Richard I and Edward I
    CRUSADER_WISDOM = {
        "third_crusade": {
            "leader": "Richard I",
            "lesson": "Won battles but couldn't take Jerusalem",
            "trading": "Tactical wins don't guarantee strategic victory."
        },
        "ransomed_king": {
            "event": "Richard captured, England paid 150,000 marks",
            "lesson": "Even kings can be held hostage",
            "trading": "Always have ransom money (reserves). Captivity happens."
        },
        "saladin_respect": {
            "event": "Richard and Saladin's mutual respect",
            "lesson": "Honor your worthy opponents",
            "trading": "Respect the market. It's a worthy adversary."
        },
        "lord_edward_crusade": {
            "leader": "Edward I (as prince)",
            "lesson": "Survived assassination, learned patience",
            "trading": "Survive first. Learn from every wound."
        }
    }
    
    def __init__(self):
        """Initialize the Plantagenet Wisdom Library."""
        self.dynasty_start = 1154
        self.dynasty_end = 1485
        self.dynasty_years = self.dynasty_end - self.dynasty_start
        
    def get_king_for_market(self, fear_greed: int, btc_change: float) -> Dict:
        """Select a Plantagenet king based on market conditions."""
        if fear_greed < 20 and btc_change < -5:
            return {"king": "edward_iv", **self.KINGS["edward_iv"],
                    "message": "The Sun King lost everything and won it back. So can you."}
        elif fear_greed < 30:
            return {"king": "henry_ii", **self.KINGS["henry_ii"],
                    "message": "Build systems during chaos. Law brings order."}
        elif fear_greed > 80 and btc_change > 5:
            return {"king": "richard_ii", **self.KINGS["richard_ii"],
                    "message": "The Vain King lost everything to arrogance. Stay humble."}
        elif fear_greed > 70:
            return {"king": "henry_v", **self.KINGS["henry_v"],
                    "message": "Even Agincourt was won with discipline, not recklessness."}
        elif btc_change > 3:
            return {"king": "richard_i", **self.KINGS["richard_i"],
                    "message": "The Lionheart strikes when the moment is right!"}
        elif btc_change < -3:
            return {"king": "john", **self.KINGS["john"],
                    "message": "Magna Carta. Know when to capitulate to survive."}
        else:
            return {"king": "edward_iii", **self.KINGS["edward_iii"],
                    "message": "The Glorious King maximized a strong position."}
    
    def get_magna_carta_clause(self) -> Dict:
        """Get a random Magna Carta principle."""
        clause_key = random.choice(list(self.MAGNA_CARTA.keys()))
        return {"clause": clause_key, **self.MAGNA_CARTA[clause_key]}
    
    def get_war_strategy(self, market_phase: str) -> Dict:
        """Get Hundred Years War strategy for current market phase."""
        if market_phase in ["EXTREME_FEAR", "FEAR"]:
            return {"strategy": "defensive_position", **self.HUNDRED_YEARS_WAR["defensive_position"],
                    "message": "Like Agincourt - defend your position. Let them attack."}
        elif market_phase in ["EXTREME_GREED", "GREED"]:
            return {"strategy": "treaty_of_troyes", **self.HUNDRED_YEARS_WAR["treaty_of_troyes"],
                    "message": "Lock in gains diplomatically while you're winning."}
        elif market_phase == "NEUTRAL":
            return {"strategy": "siege_warfare", **self.HUNDRED_YEARS_WAR["siege_warfare"],
                    "message": "Patient siege. Wait for the walls to fall."}
        else:
            return {"strategy": "chevauchee", **self.HUNDRED_YEARS_WAR["chevauchee"],
                    "message": "Quick raids for profit. Strike and withdraw."}
    
    def get_roses_wisdom(self, btc_change: float) -> Dict:
        """Get Wars of the Roses wisdom based on market action."""
        if btc_change > 2:
            return {"house": "york", **self.WARS_OF_ROSES["house_of_york"],
                    "message": "The White Rose ascends. Attack mode!"}
        elif btc_change < -2:
            return {"house": "lancaster", **self.WARS_OF_ROSES["house_of_lancaster"],
                    "message": "The Red Rose defends. Build alliances."}
        else:
            return {"event": "kingmaker", **self.WARS_OF_ROSES["kingmaker"],
                    "message": "Even kingmakers fall. Influence has limits."}
    
    def get_proverb(self) -> Dict:
        """Get a Plantagenet proverb or motto."""
        return random.choice(self.PROVERBS)
    
    def get_crusader_lesson(self) -> Dict:
        """Get a lesson from the Crusades."""
        lesson_key = random.choice(list(self.CRUSADER_WISDOM.keys()))
        return {"lesson": lesson_key, **self.CRUSADER_WISDOM[lesson_key]}
    
    def get_angevin_warning(self) -> Dict:
        """Get a warning from the Angevin Empire's fate."""
        warning_key = random.choice(list(self.ANGEVIN_EMPIRE.keys()))
        return {"warning": warning_key, **self.ANGEVIN_EMPIRE[warning_key]}
    
    def get_market_phase(self, fear_greed: int) -> str:
        """Determine market phase from Fear & Greed."""
        if fear_greed < 20:
            return "EXTREME_FEAR"
        elif fear_greed < 40:
            return "FEAR"
        elif fear_greed < 60:
            return "NEUTRAL"
        elif fear_greed < 80:
            return "GREED"
        else:
            return "EXTREME_GREED"
    
    def get_full_plantagenet_reading(self, fear_greed: int, btc_price: float, btc_change: float) -> Dict:
        """Get complete Plantagenet wisdom reading."""
        market_phase = self.get_market_phase(fear_greed)
        
        reading = {
            "king": self.get_king_for_market(fear_greed, btc_change),
            "magna_carta": self.get_magna_carta_clause(),
            "war_strategy": self.get_war_strategy(market_phase),
            "roses": self.get_roses_wisdom(btc_change),
            "crusade": self.get_crusader_lesson(),
            "angevin": self.get_angevin_warning(),
            "proverb": self.get_proverb(),
            "market_phase": market_phase,
            "synthesis": ""
        }
        
        reading["synthesis"] = self._synthesize_plantagenet_wisdom(reading, fear_greed, btc_change)
        return reading
    
    def _synthesize_plantagenet_wisdom(self, reading: Dict, fear_greed: int, btc_change: float) -> str:
        """Synthesize Plantagenet wisdom into actionable insight."""
        king = reading["king"]
        proverb = reading["proverb"]["proverb"]
        
        if fear_greed < 30:
            return f"👑 PLANTAGENET SYNTHESIS: {king['name']} {king['glyph']} speaks from {king['reign']}: " \
                   f"'{king['message']}' The Magna Carta teaches: {reading['magna_carta']['trading']} " \
                   f"In times of fear, remember: '{proverb}' - {reading['proverb']['trading']} " \
                   f"The dynasty survived 331 years through such trials."
        elif fear_greed > 70:
            return f"👑 PLANTAGENET SYNTHESIS: {king['name']} {king['glyph']} warns from {king['reign']}: " \
                   f"'{king['message']}' Remember the Wars of the Roses - {reading['roses']['message']} " \
                   f"'{proverb}' - {reading['proverb']['trading']} " \
                   f"Pride goeth before a fall. Even Plantagenets fell."
        else:
            return f"👑 PLANTAGENET SYNTHESIS: {king['name']} {king['glyph']} guides from {king['reign']}: " \
                   f"'{king['message']}' The Hundred Years War strategy: {reading['war_strategy']['message']} " \
                   f"'{proverb}' - {reading['proverb']['trading']} " \
                   f"Build for the long reign, not the quick victory."
    
    def speak_wisdom(self) -> str:
        """Generate a Plantagenet wisdom statement."""
        proverb = self.get_proverb()
        return f'👑 "{proverb["proverb"]}" → 💹 {proverb["trading"]}'

# ═══════════════════════════════════════════════════════════════
# �🪙 COINBASE CORTEX (Enhanced)
# ═══════════════════════════════════════════════════════════════

class CoinbaseCortex:
    """Direct interface to Coinbase with critical analysis."""
    
    PUBLIC_BASE_URL = "https://api.exchange.coinbase.com"
    
    def __init__(self):
        self.feed = CoinbaseHistoricalFeed() if CoinbaseHistoricalFeed else None

    def analyze_market_structure(self) -> Dict[str, Any]:
        """Analyze market structure with skepticism."""
        logger.info("🪙 Coinbase Cortex analyzing structure...")
        
        structure = {
            "timestamp": datetime.now().isoformat(),
            "assets": {},
            "observations": []
        }
        
        pairs = ['BTC-USD', 'ETH-USD', 'SOL-USD']
        
        for pair in pairs:
            try:
                url = f"{self.PUBLIC_BASE_URL}/products/{pair}/ticker"
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    price = float(data.get('price', 0))
                    bid = float(data.get('bid', 0))
                    ask = float(data.get('ask', 0))
                    spread = ((ask - bid) / price * 100) if price > 0 else 0
                    
                    structure["assets"][pair] = {
                        "price": price,
                        "spread_pct": spread,
                        "volume_24h": float(data.get('volume', 0))
                    }
                    
                    # Skeptical observation
                    if spread > 0.1:
                        structure["observations"].append(
                            f"⚠️ {pair} spread is {spread:.3f}% - low liquidity or manipulation?"
                        )
                    
                    logger.info(f"   📊 {pair}: ${price:,.2f} (spread: {spread:.4f}%)")
                    
            except Exception as e:
                logger.error(f"   Error: {pair} - {e}")
        
        return structure


# ═══════════════════════════════════════════════════════════════
# 🗣️ NARRATIVE ENGINE (Critical Thinking Version)
# ═══════════════════════════════════════════════════════════════

class NarrativeEngine:
    """Synthesizes data into a critical, speculative narrative."""
    
    def generate_talk(self, web_data: Dict, coinbase_data: Dict, 
                      skeptic_analysis: Dict, council_result: Dict,
                      speculations: List[str]) -> str:
        """Create the full critical analysis talk."""
        logger.info("🗣️ Generating critical analysis talk...")
        
        processed = web_data.get("processed", {})
        fng = processed.get("fear_greed", 50)
        fng_class = processed.get("fng_class", "Unknown")
        mcap_change = processed.get("mcap_change", 0)
        btc_dom = processed.get("btc_dominance", 50)
        btc_price = processed.get("btc_price", 0)
        
        manip_prob = skeptic_analysis.get("manipulation_probability", 0)
        consensus = council_result.get("consensus", "UNKNOWN")
        
        talk = []
        talk.append("=" * 70)
        talk.append("🧠 AUREON MINER BRAIN - CRITICAL ANALYSIS REPORT")
        talk.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        talk.append("=" * 70)
        
        # Section 1: Raw Data
        talk.append("\n📊 **RAW DATA INGESTION**")
        talk.append(f"   Fear & Greed Index: {fng} ({fng_class})")
        talk.append(f"   24h Market Cap Change: {mcap_change:+.2f}%")
        talk.append(f"   BTC Dominance: {btc_dom:.1f}%")
        talk.append(f"   BTC Price: ${btc_price:,.2f}")
        
        # Section 2: Skeptical Analysis
        talk.append("\n🔍 **SKEPTICAL ANALYSIS (BS DETECTION)**")
        talk.append(f"   Manipulation Probability: {manip_prob:.0%}")
        
        for flag in skeptic_analysis.get("red_flags", []):
            talk.append(f"   🚩 {flag}")
        for flag in skeptic_analysis.get("green_flags", []):
            talk.append(f"   ✅ {flag}")
        
        # Section 3: Council Debate
        talk.append("\n🎭 **TRUTH COUNCIL VERDICT**")
        talk.append(f"   Consensus: {consensus}")
        talk.append(f"   Action: {council_result.get('action', 'UNKNOWN')}")
        talk.append(f"   Truth Score: {council_result.get('truth_score', 0):.0%}")
        talk.append(f"   Spoof Score: {council_result.get('spoof_score', 0):.0%}")
        
        for arg in council_result.get("arguments", []):
            talk.append(arg)
        
        # Section 4: Speculations
        talk.append("\n💭 **SPECULATIVE INSIGHTS**")
        for spec in speculations:
            talk.append(f"   {spec}")
        
        # Section 5: Final Synthesis
        talk.append("\n🎯 **BRAIN SYNTHESIS**")
        if consensus == "HIGH_MANIPULATION_RISK":
            talk.append("   ⚠️ The data smells fishy. Someone is playing games.")
            talk.append("   ⚠️ DO NOT trust surface-level indicators.")
            talk.append("   ⚠️ Strategy: Wait for confirmation, trade against the herd.")
        elif consensus == "DATA_APPEARS_VALID":
            talk.append("   ✅ Data cross-checks appear consistent.")
            talk.append("   ✅ Proceed with measured confidence.")
            talk.append(f"   ✅ Environment: {fng_class.upper()}")
        else:
            talk.append("   🤔 Insufficient data for strong conviction.")
            talk.append("   🤔 Posture: Reduce size, raise entry standards.")
            talk.append("   🤔 Execute only when net-after-costs penny objective is viable and approved.")
        
        # Learning directive
        talk.append("\n📚 **LEARNING DIRECTIVE**")
        if fng < 30:
            talk.append("   → Prioritize CONTRARIAN setups that still clear net-penny-after-costs viability")
            talk.append("   → Require probability matrix approval; avoid forced-loss exits")
        elif fng > 70:
            talk.append("   → Prioritize DEFENSIVE harvesting (take net pennies quickly; avoid chasing)")
        else:
            talk.append("   → Prioritize high-probability penny hits (trend-following only when net-penny viable)")
        
        talk.append("\n" + "=" * 70)
        talk.append("🧠 \"Don't believe the hype. Question everything. Trade the truth.\"")
        talk.append("=" * 70)
        
        return "\n".join(talk)


# ═══════════════════════════════════════════════════════════════
# 💾 MEMORY CORE (Enhanced Learning)
# ═══════════════════════════════════════════════════════════════

class MemoryCore:
    """Stores knowledge and tracks learning accuracy."""
    
    MEMORY_FILE = "miner_brain_knowledge.json"
    
    def remember(self, talk: str, data: Dict, analysis: Dict):
        """Save the full analysis to memory."""
        logger.info("💾 Committing to memory...")
        
        entry = {
            "timestamp": datetime.now().isoformat(),
            "talk": talk,
            "processed_data": data.get("processed", {}),
            "skeptic_analysis": analysis.get("skeptic", {}),
            "council_verdict": analysis.get("council", {}),
            "speculations": analysis.get("speculations", [])
        }
        
        history = []
        if os.path.exists(self.MEMORY_FILE):
            try:
                with open(self.MEMORY_FILE, 'r') as f:
                    history = json.load(f)
            except:
                pass
        
        history.append(entry)
        if len(history) > 100:
            history = history[-100:]
            
        with open(self.MEMORY_FILE, 'w') as f:
            json.dump(history, f, indent=2)
            
        logger.info("✅ Knowledge integrated into learning system.")


# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN EXECUTION - COMPLETE COGNITIVE CIRCLE
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# 🚀 MINER BRAIN CLASS - UNIFIED INTELLIGENCE
# ═══════════════════════════════════════════════════════════════

class MinerBrain:
    """
    The Unified Cognitive Engine.
    Wires the brain into every system.
    """
    
    def __init__(self, thought_bus=None):
        # Initialize components
        self.miner = WebKnowledgeMiner()
        self.cortex = CoinbaseCortex()
        self.skeptic = SkepticalAnalyzer()
        self.speculator = SpeculationEngine()
        self.council = TruthCouncil()
        self.narrator = NarrativeEngine()
        self.memory = MemoryCore()
        
        # Unity Connection
        self.bus = thought_bus
        self.external_context = {
            'last_trade': None,
            'nexus_state': None,
            'bridge_command': None,
            'market_pulse': None
        }
        
        if self.bus and ThoughtBus:
            self._connect_to_unity()
        
        # Cognitive Circle Components
        self.cognitive = CognitiveCircle()
        self.reflection = SelfReflectionEngine()
        
        # NEW: Dream & Live Ticker Components
        self.dream_engine = DreamEngine()
        self.live_stream = LiveTickerStream()
        
        # NEW: Strategic Warfare Library
        self.warfare_library = StrategicWarfareLibrary()
        
        # NEW: Celtic Wisdom Library
        self.celtic_library = CelticWisdomLibrary()
        
        # NEW: Aztec Wisdom Library
        self.aztec_library = AztecWisdomLibrary()
        
        # NEW: Mogollon Wisdom Library
        self.mogollon_library = MogollonWisdomLibrary()
        
        # NEW: Plantagenet Wisdom Library
        self.plantagenet_library = PlantagenetWisdomLibrary()
        
        # NEW: Egyptian Wisdom Library - 5000 years of civilization
        self.egyptian_library = EgyptianWisdomLibrary()
        
        # NEW: Pythagorean & Musica Universalis Library - 2500 years of sacred mathematics
        self.pythagorean_library = PythagoreanWisdomLibrary()
        
        # NEW: Unified Wisdom Cognition Engine - All civilizations united
        self.wisdom_engine = WisdomCognitionEngine()
        
        # NEW: Sandbox Evolved Parameters - 454 generations of learning
        self.sandbox_evolution = get_sandbox_evolution()
        
        # ⏳🔮 Timeline Oracle - 7-day future validation
        self.timeline_oracle = None
        if TIMELINE_ORACLE_AVAILABLE:
            try:
                self.timeline_oracle = get_timeline_oracle()
                logger.info("⏳🔮 MinerBrain: Timeline Oracle initialized (7-day vision)")
            except Exception as e:
                logger.warning(f"⏳ Timeline Oracle init failed: {e}")
        
        self.latest_prediction = None
        self.latest_analysis = None

        # In-House AI Bridge — sovereign AI enhancement (no external deps)
        self.ai_bridge = None
        try:
            from aureon.miner.miner_inhouse_ai_bridge import get_miner_ai_bridge
            self.ai_bridge = get_miner_ai_bridge()
            self.ai_bridge.start()
            logger.info("🧠 MinerBrain: In-House AI Bridge ONLINE (sovereign)")
        except Exception as e:
            logger.debug(f"Miner AI Bridge unavailable: {e}")

    def _connect_to_unity(self):
        """Connect to the Thought Bus to hear other parts of the system."""
        if not self.bus:
            return
            
        logger.info("🧠 Brain connecting to Thought Bus for Unity...")
        
        # Subscribe to everything relevant
        self.bus.subscribe("execution.*", self._on_execution_thought)
        self.bus.subscribe("nexus.*", self._on_nexus_thought)
        self.bus.subscribe("bridge.*", self._on_bridge_thought)
        self.bus.subscribe("market.*", self._on_market_thought)
        
    def _on_execution_thought(self, thought):
        """Hear what the hands are doing (trading)."""
        self.external_context['last_trade'] = thought.payload if isinstance(thought.payload, dict) else {}
        logger.info(f"🧠 Brain heard execution: {thought.topic}")
        
    def _on_nexus_thought(self, thought):
        """Hear what the nervous system feels (coherence)."""
        self.external_context['nexus_state'] = thought.payload if isinstance(thought.payload, dict) else {}
        
    def _on_bridge_thought(self, thought):
        """Hear commands from the bridge."""
        self.external_context['bridge_command'] = thought.payload if isinstance(thought.payload, dict) else {}
        logger.info(f"🧠 Brain heard bridge command: {thought.topic}")
        
    def _on_market_thought(self, thought):
        """Hear raw market data."""
        self.external_context['market_pulse'] = thought.payload if isinstance(thought.payload, dict) else {}

    def run_cycle(self, quantum_context: dict = None):
        """
        Execute one full critical thinking cycle with self-learning.
        
        Args:
            quantum_context: Optional dict from QuantumProcessingBrain containing:
                - quantum_coherence: Ψ(t) unified coherence
                - planetary_gamma: Γ(t) planetary alignment
                - probability_edge: Current probability edge
                - cascade_multiplier: Mining cascade multiplier
                - is_lighthouse: True if in optimal window
                - piano_lambda: Λ(t) master field strength
                - harmonic_signal: BUY/HOLD/SELL from harmonics
                - signal_confidence: Confidence in harmonic signal
        """
        print("\n" + "🧠" * 35)
        print("   AUREON MINER BRAIN v5.5 - SANDBOX EVOLVED INTELLIGENCE")
        print("   7 Civilizations + 5000 Years + 454 Generations = Universal Truth")
        print("   \"Your feet are for dancing, your brain is for cutting out the BS!\"")
        print("🧠" * 35 + "\n")
        
        # Store quantum context for use throughout cycle; force dict for safety
        self._quantum_context = quantum_context if isinstance(quantum_context, dict) else {}
        qc_ctx = self._quantum_context

        # HNC direction: self-source the harmonic context from the ONE canonical field when the caller
        # did not inject it, so the miner's adaptive cycle is directed by the shared symbolic.life.pulse
        # (Λ/Γ/Ψ) instead of the static 0.5/1.0 defaults. An explicitly-injected value always wins; this
        # only fills gaps. Guarded/offline-safe — a missing daemon leaves the pre-existing defaults intact.
        try:
            from aureon.core.hnc_field import read_canonical_field

            merge_canonical_into_qc(qc_ctx, read_canonical_field())
        except Exception:  # noqa: BLE001 — the canonical field is best-effort enrichment, never fatal
            pass

        # ═══════════════════════════════════════════════════════════
        # PHASE -2: SANDBOX EVOLUTION INTEGRATION (NEW!)
        # ═══════════════════════════════════════════════════════════
        print("🧬" * 35)
        print("   PHASE -2: SANDBOX EVOLVED INTELLIGENCE")
        print("🧬" * 35 + "\n")
        
        sandbox = self.sandbox_evolution
        guidance = sandbox.get_trading_guidance()
        
        print(f"🧬 **SANDBOX EVOLUTION STATUS** (Generation {guidance['evolved_generation']})")
        print(f"   Best Win Rate Achieved: {guidance['evolved_win_rate']:.1f}%")
        print(f"   Entry Coherence Min: {guidance['entry_coherence_min']:.0%}")
        print(f"   Volatility Sweet Spot: {guidance['volatility_range'][0]:.2f}% - {guidance['volatility_range'][1]:.2f}%")
        print(f"   Position Size: {guidance['position_size_pct']:.1f}% of capital")
        print(f"   Take Profit Target: {guidance['take_profit_pct']:.2f}%")
        print(f"   Loss Guard Reference: {guidance['stop_loss_pct']:.2f}% (not forced)")
        print(f"   Max Hold Cycles: {guidance['max_hold_cycles']}")
        print(f"   Prefer Maker Orders: {'Yes' if guidance['prefer_maker'] else 'No'}")
        
        if guidance['latest_lessons']:
            print(f"\n   📚 Latest Lessons from {guidance['evolved_generation']} Generations:")
            for lesson in guidance['latest_lessons'][-3:]:
                print(f"      • {lesson}")
        
        # ═══════════════════════════════════════════════════════════
        # PHASE -1: QUANTUM BRAIN INTEGRATION (if available)
        # ═══════════════════════════════════════════════════════════
        if qc_ctx:
            print("🔮" * 35)
            print("   PHASE -1: QUANTUM BRAIN COMMUNION")
            print("🔮" * 35 + "\n")
            
            print("🔮 **QUANTUM BRAIN SPEAKS**")
            print(f"   Unified Coherence (Ψ): {(qc_ctx.get('quantum_coherence') or 0.5):.3f}")
            print(f"   Planetary Gamma (Γ): {(qc_ctx.get('planetary_gamma') or 0.5):.3f}")
            print(f"   Probability Edge: {(qc_ctx.get('probability_edge') or 0.0):.3f}")
            print(f"   Cascade Multiplier: {(qc_ctx.get('cascade_multiplier') or 1.0):.2f}x")
            print(f"   Lighthouse Window: {'🌟 ACTIVE' if qc_ctx.get('is_lighthouse') else '⬜ Inactive'}")
            print(f"   Piano Lambda (Λ): {(qc_ctx.get('piano_lambda') or 1.0):.3f}")
            print(f"   Harmonic Signal: {qc_ctx.get('harmonic_signal') or 'N/A'}")
            
            # Interpret quantum state for wisdom consideration
            qc = qc_ctx.get('quantum_coherence', 0.5)
            gamma = qc_ctx.get('planetary_gamma', 0.5)
            if qc > 0.7 and gamma > 0.6:
                print("\n   🌟 QUANTUM INTERPRETATION: High coherence + strong planetary alignment")
                print("      → The cosmos is synchronized. Bold action favored.")
            elif qc < 0.3:
                print("\n   ⚠️ QUANTUM INTERPRETATION: Low coherence detected")
                print("      → Systems are chaotic. Caution advised.")
            else:
                print("\n   ⚖️ QUANTUM INTERPRETATION: Balanced state")
                print("      → Normal operations. Follow wisdom consensus.")
        
        # ═══════════════════════════════════════════════════════════
        # PHASE -0.5: UNITY AWARENESS (Thought Bus Integration)
        # ═══════════════════════════════════════════════════════════
        # Unity awareness (Thought Bus) — fully defensive to avoid NoneType errors
        try:
            ctx = self.external_context if isinstance(self.external_context, dict) else {}
            if ctx:
                print("\n" + "🔗" * 35)
                print("   PHASE -0.5: UNITY AWARENESS (THOUGHT BUS)")
                print("🔗" * 35 + "\n")
                
                print("🔗 **UNITY CONSCIOUSNESS DETECTED**")
                
                trade = ctx.get('last_trade') if isinstance(ctx, dict) else None
                if isinstance(trade, dict):
                    action = trade.get('action') or 'UNKNOWN'
                    symbol = trade.get('symbol') or 'UNKNOWN'
                    pnl = trade.get('pnl') or 0.0
                    try:
                        print(f"   🛒 LAST TRADE: {action} {symbol} (PnL: ${float(pnl):.2f})")
                    except Exception:
                        print(f"   🛒 LAST TRADE: {action} {symbol} (PnL: $0.00)")
                
                nexus = ctx.get('nexus_state') if isinstance(ctx, dict) else None
                if isinstance(nexus, dict):
                    state = nexus.get('state') or 'UNKNOWN'
                    print(f"   🌐 NEXUS STATE: {state}")
                
                cmd = ctx.get('bridge_command') if isinstance(ctx, dict) else None
                if isinstance(cmd, dict):
                    print(f"   🌉 BRIDGE COMMAND: {cmd.get('command') or 'UNKNOWN'}")
        except Exception as e:
            import traceback
            print(f"   ⚠️ Unity context decode failed: {e}")
            print(traceback.format_exc())

        # ═══════════════════════════════════════════════════════════
        # PHASE 0: LIVE MARKET PULSE
        # ═══════════════════════════════════════════════════════════
        print("\n" + "🔴" * 35)
        print("   PHASE 0: LIVE MARKET PULSE")
        print("🔴" * 35 + "\n")
        
        pulse = self.live_stream.get_market_pulse() or {}
        if not isinstance(pulse, dict):
            pulse = {}

        snapshot = pulse.get('snapshot', {}) if isinstance(pulse, dict) else {}
        if not isinstance(snapshot, dict):
            snapshot = {}
        tickers = snapshot.get('tickers', {}) if isinstance(snapshot, dict) else {}
        if not isinstance(tickers, dict):
            tickers = {}

        print(f"🔴 **LIVE MARKET PULSE** ({len(tickers)} assets tracked)")
        print(f"   Pulse: {pulse.get('pulse', 'UNKNOWN')}")
        print(f"   Avg 24h Change: {pulse.get('avg_change_24h', 0):+.2f}%")
        print(f"   Fear & Greed: {pulse.get('fear_greed', 'N/A')}")
        print(f"   BTC: ${pulse.get('btc_price', 0):,.2f}")
        
        # Show market breadth
        breadth = snapshot.get('breadth', {})
        if breadth:
            print(f"\n   📈 MARKET BREADTH: {breadth.get('status', 'UNKNOWN')}")
            print(f"      Up: {breadth.get('up_count', 0)} | Down: {breadth.get('down_count', 0)} | Ratio: {breadth.get('breadth', 0.5):.0%}")
        
        # Show sector performance
        sectors = snapshot.get('sectors', {})
        if sectors:
            print("\n   🏛️ SECTOR PERFORMANCE (24h):")
            for sector, data in sorted(sectors.items(), key=lambda x: x[1].get('avg_change', 0), reverse=True):
                emoji = "🟢" if data.get('avg_change', 0) > 2 else "🟡" if data.get('avg_change', 0) > 0 else "🔴"
                print(f"      {emoji} {sector.upper():12} {data.get('avg_change', 0):+6.2f}%  ({data.get('bullish_pct', 0):.0f}% bullish)")
        
        # Show top movers
        if tickers:
            sorted_tickers = sorted(tickers.items(), key=lambda x: x[1].get('change_24h', 0) if isinstance(x[1], dict) else 0, reverse=True)
            
            print("\n   🚀 TOP GAINERS:")
            for sym, data in sorted_tickers[:5]:
                if isinstance(data, dict) and data.get('change_24h', 0) > 0:
                    print(f"      {sym:6} ${data.get('price', 0):>12,.4f}  {data.get('change_24h', 0):+6.2f}%")
            
            print("\n   📉 TOP LOSERS:")
            for sym, data in sorted_tickers[-5:]:
                if isinstance(data, dict) and data.get('change_24h', 0) < 0:
                    print(f"      {sym:6} ${data.get('price', 0):>12,.4f}  {data.get('change_24h', 0):+6.2f}%")
            
            # Show key assets
            print("\n   💎 KEY ASSETS:")
            key_assets = ['BTC', 'ETH', 'SOL', 'XRP', 'DOGE', 'LINK', 'AVAX', 'OP', 'ARB']
            for sym in key_assets:
                if sym in tickers and isinstance(tickers[sym], dict):
                    data = tickers[sym]
                    emoji = "🟢" if data.get('change_24h', 0) > 0 else "🔴"
                    print(f"      {emoji} {sym:6} ${data.get('price', 0):>12,.4f}  {data.get('change_24h', 0):+6.2f}%  Vol: ${data.get('volume', 0)/1e6:.1f}M")

        # ═══════════════════════════════════════════════════════════
        # PHASE 1: SEARCH THE INTERNET
        # ═══════════════════════════════════════════════════════════
        web_data = self.miner.gather_intelligence()
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 2: ANALYZE MARKET STRUCTURE
        # ═══════════════════════════════════════════════════════════
        coinbase_data = self.cortex.analyze_market_structure()
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 3: SKEPTICISM & TRUTH COUNCIL
        # ═══════════════════════════════════════════════════════════
        skeptic_result = self.skeptic.analyze(web_data.get("processed", {}))
        council_result = self.council.convene(web_data.get("processed", {}))
        speculations = self.speculator.speculate(web_data.get("processed", {}), skeptic_result)

        # ── In-House AI Enhancement (Phase 3+): sovereign AI augments skeptic + council ──
        ai_skeptical = None
        ai_council = None
        if self.ai_bridge and self.ai_bridge.is_alive:
            try:
                ai_skeptical = self.ai_bridge.enhance_skeptical_analysis(
                    market_data=web_data.get("processed", {}),
                    existing_red_flags=skeptic_result.get("red_flags", []) if isinstance(skeptic_result, dict) else [],
                    existing_green_flags=skeptic_result.get("green_flags", []) if isinstance(skeptic_result, dict) else [],
                )
                # Merge AI-detected flags into the rule-based result
                if isinstance(skeptic_result, dict):
                    skeptic_result.setdefault("red_flags", []).extend(ai_skeptical.red_flags)
                    skeptic_result.setdefault("green_flags", []).extend(ai_skeptical.green_flags)
                    skeptic_result["ai_verdict"] = ai_skeptical.verdict
                    skeptic_result["ai_confidence"] = ai_skeptical.confidence

                ai_council = self.ai_bridge.synthesise_council_verdict(
                    market_data=web_data.get("processed", {}),
                    advisor_votes=council_result.get("votes", []) if isinstance(council_result, dict) else [],
                )
                # Enrich council result with AI synthesis
                if isinstance(council_result, dict):
                    council_result["ai_verdict"] = ai_council.verdict
                    council_result["ai_confidence"] = ai_council.confidence
                    council_result["ai_coherence"] = ai_council.coherence
                    council_result["ai_reasoning"] = ai_council.reasoning
            except Exception as ai_err:
                logger.debug(f"Miner AI Bridge Phase 3 enhancement error: {ai_err}")

        talk = self.narrator.generate_talk(web_data, coinbase_data, skeptic_result, council_result, speculations)
        print(talk)

        if ai_council:
            print(f"\n🤖 **IN-HOUSE AI COUNCIL SYNTHESIS**")
            print(f"   Verdict: {ai_council.verdict}  |  Confidence: {ai_council.confidence:.0%}  |  Coherence: {ai_council.coherence:.2f}")
            if ai_council.reasoning:
                print(f"   {ai_council.reasoning[:200]}")
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 3.5: DREAM STATE - SCENARIO SIMULATION
        # ═══════════════════════════════════════════════════════════
        print("\n" + "💭" * 35)
        print("   PHASE 3.5: DREAM STATE - SCENARIO SIMULATION")
        print("💭" * 35)
        
        current_btc = pulse.get('btc_price', web_data.get('processed', {}).get('btc_price', 90000))
        current_fng = pulse.get('fear_greed', web_data.get('processed', {}).get('fear_greed', 50))
        
        dreams = self.dream_engine.dream({
            'btc_price': current_btc,
            'fear_greed': current_fng
        })
        
        print(f"\n💭 **DREAMING ON LIVE DATA**")
        print(f"   Base Reality: BTC ${current_btc:,.2f} | F&G {current_fng}")
        
        print("\n   🌙 DREAM SCENARIOS:")
        for scenario in dreams['scenarios_dreamed'][:6]: # Show top 6
            icon = "📈" if "ACCUMULATE" in scenario.get('decision', '') or "BUY" in scenario.get('decision', '') else "⏸️" if "WAIT" in scenario.get('decision', '') or "HOLD" in scenario.get('decision', '') else "📉"
            print(f"      {icon} {scenario.get('scenario', 'UNKNOWN')}: {scenario.get('decision', 'UNKNOWN')}")
            print(f"         └─ {scenario.get('reasoning', 'No reasoning')}")
            
        print("\n   💡 DREAM INSIGHTS:")
        for insight in dreams['key_insights']:
            print(f"      {insight}")
            
        # Prepared response lookup for the current Fear & Greed at a 0% change baseline.
        prepared = self.dream_engine.get_prepared_response(0.0, current_fng)
        if prepared:
            print(f"\n   🎯 PRE-COMPUTED RESPONSE (BASELINE 0% CHANGE):")
            print(f"      Action: {prepared['action']}")
            print(f"      Reasoning: {prepared['reasoning']}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 4: SELF-REFLECTION
        # ═══════════════════════════════════════════════════════════
        print("\n" + "🪞" * 35)
        print("   PHASE 4: SELF-REFLECTION")
        print("🪞" * 35)
        
        reflection_result = self.reflection.reflect_on_output(talk, web_data, council_result)
        
        print(f"\n🪞 **SELF-REFLECTION ANALYSIS**")
        print(f"   Logical Consistency: {'✅ Yes' if reflection_result['logical_consistency'] else '❌ No'}")
        if reflection_result['contradictions']:
            print("   Contradictions Found:")
            for c in reflection_result['contradictions']:
                print(f"      ⚠️ {c}")
        if reflection_result['blind_spots']:
            print("   Potential Blind Spots:")
            for b in reflection_result['blind_spots']:
                print(f"      👁️ {b}")
        if reflection_result['improvement_suggestions']:
            print("   Improvement Suggestions:")
            for s in reflection_result['improvement_suggestions']:
                print(f"      💡 {s}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 5: PREDICTION VALIDATION
        # ═══════════════════════════════════════════════════════════
        print("\n" + "🔮" * 35)
        print("   PHASE 5: PREDICTION VALIDATION")
        print("🔮" * 35 + "\n")
        
        validated = self.cognitive.validate_past_predictions(current_btc)
        if not validated:
            print("🔮 No predictions ready for validation yet.")
        else:
            for v in validated:
                is_correct = v.get('was_correct', False)  # Use 'was_correct' not 'correct'
                icon = "✅" if is_correct else "❌"
                print(f"   {icon} Prediction Validated: {v.get('predicted_direction', 'N/A')} (Actual: {v.get('actual_outcome', {}).get('direction', 'N/A')})")

        # ═══════════════════════════════════════════════════════════
        # PHASE 6: SELF-CRITIQUE & LEARNING
        # ═══════════════════════════════════════════════════════════
        print("\n" + "📊" * 35)
        print("   PHASE 6: SELF-CRITIQUE & LEARNING")
        print("📊" * 35 + "\n")
        
        accuracy_stats = self.cognitive.get_accuracy_stats()
        critiques = self.cognitive.generate_self_critique(accuracy_stats)
        
        print("\n📊 **BRAIN SELF-CRITIQUE**")
        for critique in critiques:
            print(f"   {critique}")
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 6.5: STRATEGIC WARFARE WISDOM
        # ═══════════════════════════════════════════════════════════
        print("\n" + "⚔️" * 35)
        print("   PHASE 6.5: STRATEGIC WARFARE WISDOM")
        print("   📜 Sun Tzu + 🍀 Irish Republican Army Tactics")
        print("⚔️" * 35)
        
        # Determine market condition for wisdom selection
        fng = web_data.get("processed", {}).get("fear_greed", 50)
        if fng <= 20:
            market_condition = "extreme_fear"
        elif fng <= 35:
            market_condition = "fear"
        elif fng >= 80:
            market_condition = "extreme_greed"
        elif fng >= 65:
            market_condition = "greed"
        else:
            market_condition = "neutral"
        
        warfare_wisdom = self.warfare_library.get_strategic_wisdom(market_condition)
        
        print(f"\n📜 **SUN TZU SPEAKS** (Market: {market_condition.upper()})")
        for wisdom in warfare_wisdom['sun_tzu'][:3]:
            print(f"   \"{wisdom['text']}\"")
            print(f"      → 💹 {wisdom['trading']}")
        
        print(f"\n🍀 **GUERRILLA TACTICS**")
        for wisdom in warfare_wisdom['guerrilla'][:3]:
            print(f"   \"{wisdom['text']}\"")
            print(f"      → 💹 {wisdom['trading']}")
        
        print(f"\n{warfare_wisdom['synthesis']}")
        print(f"\n🎯 {warfare_wisdom['tactical_directive']}")
        
        # Get a random piece of wisdom for the soul
        random_wisdom = self.warfare_library.speak_wisdom()
        print(f"\n💫 WISDOM OF THE DAY: {random_wisdom}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 6.75: CELTIC WISDOM - STARS, FREQUENCIES & DRUIDIC KNOWLEDGE
        # ═══════════════════════════════════════════════════════════
        print("\n" + "☘️" * 35)
        print("   PHASE 6.75: CELTIC WISDOM - STARS & FREQUENCIES")
        print("   🌙 Moon Phases + ✨ Sacred Frequencies + 🌳 Druidic Trees")
        print("☘️" * 35)
        
        # Get BTC change for star reading
        btc_change = pulse.get('avg_change_24h', 0)
        
        # Get full Celtic reading
        celtic_reading = self.celtic_library.get_full_celtic_reading(fng, current_btc, btc_change)
        
        # Moon Phase
        moon = celtic_reading['moon']
        print(f"\n🌙 **MOON PHASE**: {moon['phase_name'].replace('_', ' ').upper()} ({moon['phase_pct']:.0f}%)")
        print(f"   Meaning: {moon['meaning']}")
        print(f"   Trading: {moon['trading']}")
        
        # Sacred Frequency
        freq = celtic_reading['frequency']
        print(f"\n🔮 **SACRED FREQUENCY**: {freq['frequency']} Hz - {freq['name']}")
        print(f"   Effect: {freq['effect']}")
        print(f"   Trading: {freq['trading']}")
        
        # Star Reading
        stars = celtic_reading['stars']
        print(f"\n✨ **READING THE STARS**")
        for star in stars['stars']:
            print(f"   ⭐ {star['star']}: {star['message']}")
        
        # Druidic Tree
        tree = celtic_reading['tree']
        print(f"\n🌳 **DRUIDIC TREE OF THE DAY**: {tree['tree']}")
        print(f"   Meaning: {tree['meaning']}")
        print(f"   Trading: {tree['trading']}")
        
        # Celtic Triad
        triad = celtic_reading['triad']
        print(f"\n☘️ **CELTIC TRIAD**")
        print(f"   \"{triad['triad']}\"")
        print(f"   → 💹 {triad['trading']}")
        
        # Festival check
        festival = celtic_reading['festival']
        if festival.get('active'):
            fest_data = festival['data']
            print(f"\n🔥 **CELTIC FESTIVAL ACTIVE**: {festival['festival'].upper()}")
            print(f"   Date: {fest_data['date']}")
            print(f"   Meaning: {fest_data['meaning']}")
            print(f"   Trading: {fest_data['trading']}")
        
        # Celtic Synthesis
        print(f"\n{celtic_reading['synthesis']}")
        
        # Celtic wisdom of the day
        celtic_wisdom = self.celtic_library.speak_wisdom()
        print(f"\n🍀 CELTIC WISDOM: {celtic_wisdom}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 6.8: AZTEC WISDOM - THE FIFTH SUN
        # ═══════════════════════════════════════════════════════════
        print("\n" + "🦅" * 35)
        print("   PHASE 6.8: AZTEC WISDOM - THE FIFTH SUN")
        print("   📅 Tonalpohualli + 🔮 Deities + 👴 Elder Wisdom")
        print("🦅" * 35)
        
        # Get full Aztec reading
        aztec_reading = self.aztec_library.get_full_aztec_reading(fng, current_btc, btc_change)
        
        # Tonalpohualli Day
        tonal = aztec_reading['tonalpohualli']
        print(f"\n📅 **TONALPOHUALLI DAY**: {tonal['name']} {tonal['glyph']}")
        print(f"   Day {tonal['full_cycle_day']} of 260-day sacred cycle")
        print(f"   Meaning: {tonal['meaning']} - {tonal['energy']}")
        print(f"   Trading: {tonal['trading']}")
        
        # Current Sun Age
        sun = aztec_reading['sun_age']
        print(f"\n☀️ **CURRENT SUN AGE**: {sun['name']} - {sun['element']}")
        print(f"   Status: {sun['status']}")
        print(f"   Trading: {sun['trading']}")
        
        # Deity Guidance
        deity = aztec_reading['deity']
        print(f"\n🔮 **DEITY GUIDANCE**: {deity['deity']} {deity['glyph']}")
        print(f"   Domain: {deity['domain']}")
        print(f"   Message: {deity['message']}")
        print(f"   Trading: {deity['trading']}")
        
        # Direction
        direction = aztec_reading['direction']
        print(f"\n🧭 **DIRECTION**: {direction['direction']} ({direction['color']}) {direction['glyph']}")
        print(f"   Trading: {direction['trading']}")
        
        # Elder Wisdom
        elder = aztec_reading['elder_wisdom']
        print(f"\n👴 **HUEHUEHTLAHTOLLI (ELDER WISDOM)**")
        print(f"   \"{elder['proverb']}\"")
        print(f"   → 💹 {elder['trading']}")
        
        # Aztec Synthesis
        print(f"\n{aztec_reading['synthesis']}")
        
        # Aztec wisdom of the day
        aztec_wisdom = self.aztec_library.speak_wisdom()
        print(f"\n🦅 AZTEC WISDOM: {aztec_wisdom}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 6.9: MOGOLLON WISDOM - PEOPLE OF THE MOUNTAINS
        # ═══════════════════════════════════════════════════════════
        print("\n" + "🏺" * 35)
        print("   PHASE 6.9: MOGOLLON WISDOM - PEOPLE OF THE MOUNTAINS")
        print("   🎨 Mimbres Pottery + 🏠 Pit House + 🌵 Desert Seasons")
        print("🏺" * 35)
        
        # Get full Mogollon reading
        mogollon_reading = self.mogollon_library.get_full_mogollon_reading(fng, current_btc, btc_change)
        
        # Mimbres Symbol
        mimbres = mogollon_reading['mimbres_symbol']
        print(f"\n🎨 **MIMBRES POTTERY SYMBOL**: {mimbres['symbol'].title()} {mimbres['glyph']}")
        print(f"   Meaning: {mimbres['meaning']}")
        print(f"   Message: {mimbres['message']}")
        print(f"   Trading: {mimbres['trading']}")
        
        # Desert Season
        season = mogollon_reading['desert_season']
        print(f"\n🌵 **DESERT SEASON**: {season['season']}")
        print(f"   Trading: {season['trading']}")
        
        # Pit House Wisdom
        pit = mogollon_reading['pit_house']
        print(f"\n🏠 **PIT HOUSE WISDOM**: {pit['principle']}")
        print(f"   {pit['wisdom']}")
        
        # Trade Route Lesson
        route = mogollon_reading['trade_route']
        print(f"\n🛤️ **TRADE ROUTE LESSON**: {route['item']}")
        print(f"   Lesson: {route['lesson']}")
        print(f"   Trading: {route['trading']}")
        
        # Three Worlds
        worlds = mogollon_reading['three_worlds']
        print(f"\n🌍 **THREE WORLDS FOCUS**: {worlds['focus'].upper()}")
        print(f"   {worlds['realm']}")
        print(f"   {worlds['message']}")
        
        # Proverb
        proverb = mogollon_reading['proverb']
        print(f"\n📜 **MOGOLLON PROVERB**")
        print(f"   \"{proverb['proverb']}\"")
        print(f"   → 💹 {proverb['trading']}")
        
        # Mogollon Synthesis
        print(f"\n{mogollon_reading['synthesis']}")
        
        # Mogollon wisdom of the day
        mogollon_wisdom = self.mogollon_library.speak_wisdom()
        print(f"\n🏺 MOGOLLON WISDOM: {mogollon_wisdom}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 6.95: PLANTAGENET WISDOM - LIONS OF ENGLAND
        # ═══════════════════════════════════════════════════════════
        print("\n" + "👑" * 35)
        print("   PHASE 6.95: PLANTAGENET WISDOM - LIONS OF ENGLAND")
        print("   🦁 Kings + 📜 Magna Carta + ⚔️ Hundred Years War")
        print("👑" * 35)
        
        # Get full Plantagenet reading
        plantagenet_reading = self.plantagenet_library.get_full_plantagenet_reading(fng, current_btc, btc_change)
        
        # King for the market
        king = plantagenet_reading['king']
        print(f"\n🦁 **KING FOR THIS MARKET**: {king['name']} {king['glyph']}")
        print(f"   Reign: {king['reign']} - {king['epithet']}")
        print(f"   Achievement: {king['achievement']}")
        print(f"   Message: {king['message']}")
        print(f"   Trading: {king['trading']}")
        
        # Magna Carta
        magna = plantagenet_reading['magna_carta']
        print(f"\n📜 **MAGNA CARTA** ({magna['clause'].upper()})")
        print(f"   \"{magna['text']}\"")
        print(f"   Trading: {magna['trading']}")
        
        # War Strategy
        war = plantagenet_reading['war_strategy']
        print(f"\n⚔️ **HUNDRED YEARS WAR STRATEGY**: {war['strategy'].replace('_', ' ').title()}")
        print(f"   Tactic: {war['tactic']}")
        print(f"   Message: {war['message']}")
        print(f"   Trading: {war['trading']}")
        
        # Wars of the Roses
        roses = plantagenet_reading['roses']
        print(f"\n🌹 **WARS OF THE ROSES**")
        print(f"   {roses['message']}")
        if 'symbol' in roses:
            print(f"   House: {roses['symbol']} - Strategy: {roses['strategy']}")
        print(f"   Trading: {roses['trading']}")
        
        # Crusader Lesson
        crusade = plantagenet_reading['crusade']
        print(f"\n⛪ **CRUSADER LESSON**: {crusade['lesson'].replace('_', ' ').title()}")
        print(f"   {crusade.get('event', crusade.get('leader', 'Unknown'))}")
        print(f"   Trading: {crusade['trading']}")
        
        # Angevin Warning
        angevin = plantagenet_reading['angevin']
        print(f"\n⚠️ **ANGEVIN EMPIRE WARNING**: {angevin['warning'].title()}")
        print(f"   Lesson: {angevin['lesson']}")
        print(f"   Trading: {angevin['trading']}")
        
        # Proverb
        planta_proverb = plantagenet_reading['proverb']
        print(f"\n🎭 **PLANTAGENET MOTTO**")
        print(f"   \"{planta_proverb['proverb']}\"")
        print(f"   → 💹 {planta_proverb['trading']}")
        
        # Plantagenet Synthesis
        print(f"\n{plantagenet_reading['synthesis']}")
        
        # Plantagenet wisdom of the day
        plantagenet_wisdom = self.plantagenet_library.speak_wisdom()
        print(f"\n👑 PLANTAGENET WISDOM: {plantagenet_wisdom}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 6.97: EGYPTIAN WISDOM - CHILDREN OF THE NILE
        # ═══════════════════════════════════════════════════════════
        print("\n" + "☥" * 35)
        print("   PHASE 6.97: EGYPTIAN WISDOM - CHILDREN OF THE NILE")
        print("   🏛️ Netjeru + ⚖️ Ma'at + 📜 Book of the Dead")
        print("☥" * 35)
        
        # Get full Egyptian reading
        egyptian_reading = self.egyptian_library.get_full_egyptian_reading(fng, current_btc, btc_change)
        
        # Netjer (deity) for the market
        deity = egyptian_reading['deity']
        print(f"\n🏛️ **NETJER FOR THIS MARKET**: {deity['deity']} {deity['glyph']}")
        print(f"   Domain: {deity['domain']}")
        print(f"   Cycle: {deity['cycle']}")
        print(f"   Message: {deity['message']}")
        print(f"   Trading: {deity['trading']}")
        
        # Law of Ma'at
        maat = egyptian_reading['law_of_maat']
        print(f"\n⚖️ **LAW OF MA'AT**")
        print(f"   \"{maat['law']}\"")
        print(f"   Trading: {maat['trading']}")
        
        # Nile Season
        nile = egyptian_reading['nile_season']
        print(f"\n🌊 **NILE SEASON**: {nile['name'].upper()} {nile['glyph']}")
        print(f"   Meaning: {nile['meaning']}")
        print(f"   Event: {nile['event']}")
        print(f"   Trading: {nile['trading']}")
        
        # Book of the Dead Spell
        spell = egyptian_reading['book_of_dead']
        print(f"\n📜 **BOOK OF THE DEAD**: {spell['title']}")
        print(f"   \"{spell['wisdom']}\"")
        print(f"   Trading: {spell['trading']}")
        
        # Pyramid Wisdom
        pyramid = egyptian_reading['pyramid']
        print(f"\n🔺 **PYRAMID WISDOM**: {pyramid['principle_name'].replace('_', ' ').title()}")
        print(f"   Principle: {pyramid['principle']}")
        print(f"   Application: {pyramid['application']}")
        print(f"   Trading: {pyramid['trading']}")
        
        # Hieroglyph
        hiero = egyptian_reading['hieroglyph']
        print(f"\n𓂀 **HIEROGLYPH**: {hiero['symbol']} - {hiero['hieroglyph'].replace('_', ' ').title()}")
        print(f"   Meaning: {hiero['meaning']}")
        print(f"   Trading: {hiero['trading']}")
        
        # Pharaoh Lesson
        pharaoh = egyptian_reading['pharaoh']
        print(f"\n👁️ **PHARAOH**: {pharaoh['name']}")
        print(f"   Achievement: {pharaoh['achievement']}")
        print(f"   Lesson: {pharaoh['lesson']}")
        print(f"   Trading: {pharaoh['trading']}")
        
        # Egyptian Proverb
        egypt_proverb = egyptian_reading['proverb']
        print(f"\n☥ **KEMETIC WISDOM**")
        print(f"   \"{egypt_proverb['proverb']}\"")
        print(f"   → 💹 {egypt_proverb['trading']}")
        
        # Egyptian Synthesis
        print(f"\n{egyptian_reading['synthesis']}")
        
        # Egyptian wisdom of the day
        egyptian_wisdom = self.egyptian_library.speak_wisdom()
        print(f"\n☥ EGYPTIAN WISDOM: {egyptian_wisdom}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 6.98: PYTHAGOREAN WISDOM - MUSIC OF THE SPHERES
        # ═══════════════════════════════════════════════════════════
        print("\n" + "🔢" * 35)
        print("   PHASE 6.98: PYTHAGOREAN WISDOM - MUSIC OF THE SPHERES")
        print("   📐 Sacred Numbers + 🎵 Musica Universalis + ⭐ Platonic Solids")
        print("🔢" * 35)
        
        # Get full Pythagorean reading
        pythagorean_reading = self.pythagorean_library.get_full_pythagorean_reading(fng, current_btc, btc_change)
        
        # Sacred Number
        sacred_num = pythagorean_reading['sacred_number']
        print(f"\n🔢 **SACRED NUMBER**: {sacred_num['number']} - {sacred_num['name']} {sacred_num['symbol']}")
        print(f"   Meaning: {sacred_num['meaning']}")
        print(f"   Pythagorean: {sacred_num['pythagorean']}")
        print(f"   Trading: {sacred_num['trading']}")
        
        # Sacred Ratio
        ratio = pythagorean_reading['ratio']
        print(f"\n📐 **SACRED RATIO**: {ratio['symbol']} = {ratio['value']} ({ratio['name']})")
        print(f"   Found in: {ratio['found_in']}")
        print(f"   Trading: {ratio['trading']}")
        
        # Planetary Harmonic (Musica Universalis)
        planet = pythagorean_reading['planet']
        print(f"\n🎵 **MUSICA UNIVERSALIS**: {planet['glyph']} {planet['planet'].upper()}")
        print(f"   Interval: {planet['interval']} (Ratio {planet['ratio']})")
        print(f"   Note: {planet['note']} | Orbit: {planet['orbit_days']} days")
        print(f"   Quality: {planet['quality']}")
        print(f"   Trading: {planet['trading']}")
        
        # Musical Interval
        interval = pythagorean_reading['interval']
        print(f"\n🎶 **MARKET INTERVAL**: {interval['interval'].replace('_', ' ').title()}")
        print(f"   Ratio: {interval['ratio']} ({interval['cents']} cents)")
        print(f"   Quality: {interval['quality']}")
        print(f"   Trading: {interval['trading']}")
        
        # Platonic Solid
        solid = pythagorean_reading['solid']
        print(f"\n⬡ **PLATONIC SOLID**: {solid['solid'].title()} {solid['symbol']}")
        print(f"   Faces: {solid['faces']} | Element: {solid['element']}")
        print(f"   Meaning: {solid['meaning']}")
        print(f"   Trading: {solid['trading']}")
        
        # The Tetractys
        print(f"\n✺ **THE TETRACTYS** (1+2+3+4=10)")
        print(f"   {pythagorean_reading['tetractys']['meaning']}")
        print(f"   Trading: {pythagorean_reading['tetractys']['trading']}")
        
        # Pythagorean Means
        means = pythagorean_reading['means']
        print(f"\n📊 **PYTHAGOREAN MEANS** (BTC ±10%)")
        print(f"   Arithmetic Mean: ${means['arithmetic']['value']:,.0f} - Fair value")
        print(f"   Geometric Mean:  ${means['geometric']['value']:,.0f} - Proportional pivot")
        print(f"   Harmonic Mean:   ${means['harmonic']['value']:,.0f} - Musical reversal point")
        
        # Brotherhood Rule
        brotherhood = pythagorean_reading['brotherhood']
        print(f"\n🏛️ **PYTHAGOREAN DISCIPLINE**")
        print(f"   Rule: \"{brotherhood['rule']}\"")
        print(f"   → 💹 {brotherhood['trading']}")
        
        # Pythagorean Maxim
        maxim = pythagorean_reading['maxim']
        print(f"\n🔢 **GOLDEN MAXIM**")
        print(f"   \"{maxim['maxim']}\"")
        print(f"   Context: {maxim['context']}")
        print(f"   → 💹 {maxim['trading']}")
        
        # Pythagorean Synthesis
        print(f"\n{pythagorean_reading['synthesis']}")
        
        # Pythagorean wisdom of the day
        pythagorean_wisdom = self.pythagorean_library.speak_wisdom()
        print(f"\n🔢 PYTHAGOREAN WISDOM: {pythagorean_wisdom}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 6.99: UNIFIED WISDOM COGNITION - ALL CIVILIZATIONS
        # ═══════════════════════════════════════════════════════════
        print("\n" + "🌍" * 35)
        print("   PHASE 6.99: UNIFIED WISDOM COGNITION")
        print("   7 Civilizations Unite for Market Truth")
        print("🌍" * 35)
        
        # Get unified wisdom reading from all civilizations
        unified_reading = self.wisdom_engine.get_unified_reading(fng, current_btc, btc_change)
        
        # Print the unified synthesis (contains the formatted consensus box)
        print(unified_reading['synthesis'])
        
        # Show actions from each civilization
        print("\n📊 **CIVILIZATION ACTIONS**:")
        for civ, action in unified_reading['actions'].items():
            civ_glyphs = {
                "celtic": "☘️", "aztec": "🦅", "mogollon": "🏺", 
                "plantagenet": "👑", "egyptian": "☥", "pythagorean": "🔢", "warfare": "⚔️"
            }
            glyph = civ_glyphs.get(civ, "🔮")
            print(f"   {glyph} {civ.title()}: {action}")
        
        # Show consensus details
        consensus = unified_reading['consensus']
        print(f"\n🎯 **UNIFIED CONSENSUS**:")
        print(f"   Sentiment: {consensus['sentiment']}")
        print(f"   Action: {consensus['action']}")
        print(f"   Confidence: {consensus['confidence']}%")
        print(f"   📈 Bullish: {consensus['bullish_votes']} | 📉 Bearish: {consensus['bearish_votes']} | ⚖️ Neutral: {consensus['neutral_votes']}")
        
        # Print wisdom statistics
        stats = unified_reading['stats']
        total_points = sum([
            stats["warfare_principles"], stats["celtic_data_points"], stats["aztec_data_points"],
            stats["mogollon_data_points"], stats["plantagenet_data_points"], 
            stats["egyptian_data_points"], stats["pythagorean_data_points"]
        ])
        print(f"\n📚 **WISDOM STATISTICS**:")
        print(f"   Total Data Points Consulted: {total_points}")
        print(f"   Years of Wisdom: {stats['total_years_of_wisdom']:,}")
        print(f"   Civilizations: {stats['total_civilizations']}")
        
        # Daily wisdom from all
        print(f"\n🌟 **WISDOM OF THE DAY** (All Civilizations):")
        all_wisdom = self.wisdom_engine.get_all_wisdom_of_day()
        for wisdom in all_wisdom:
            print(f"   {wisdom}")

        # ── In-House AI Wisdom Synthesis: blends all civilisations into a directive ──
        ai_wisdom = None
        if self.ai_bridge and self.ai_bridge.is_alive:
            try:
                civ_signals = {
                    civ: {"verdict": action, "confidence": consensus.get('confidence', 50) / 100}
                    for civ, action in unified_reading.get('actions', {}).items()
                }
                ai_wisdom = self.ai_bridge.enhance_wisdom_synthesis(
                    civilization_signals=civ_signals,
                    quantum_context=qc_ctx,
                )
                print(f"\n🤖 **IN-HOUSE AI WISDOM DIRECTIVE**")
                print(f"   Verdict: {ai_wisdom.verdict}  |  Confidence: {ai_wisdom.confidence:.0%}  |  Coherence: {ai_wisdom.coherence:.2f}")
                if ai_wisdom.reasoning:
                    print(f"   {ai_wisdom.reasoning[:200]}")
            except Exception as ai_err:
                logger.debug(f"Miner AI Bridge wisdom synthesis error: {ai_err}")

        # ═══════════════════════════════════════════════════════════
        # PHASE 7: RECORD NEW PREDICTION
        # ═══════════════════════════════════════════════════════════
        brain_output = {
            'btc_price': current_btc,
            'fear_greed': web_data.get("processed", {}).get("fear_greed", 50),
            'consensus': council_result.get('consensus'),
            'manipulation_probability': skeptic_result.get('manipulation_probability', 0),
            'truth_score': council_result.get('truth_score', 0.5)
        }
        
        prediction = self.cognitive.record_prediction(brain_output)
        print(f"\n🔮 New Prediction Recorded: {prediction['predicted_direction']}")
        print(f"   Will validate at: {prediction['validation_time']}")
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 8: FEED TO ADAPTIVE LEARNING SYSTEM
        # ═══════════════════════════════════════════════════════════
        print("\n" + "🔗" * 35)
        print("   PHASE 8: ADAPTIVE LEARNING INTEGRATION")
        print("🔗" * 35)
        
        self.cognitive.feed_to_adaptive_learning(brain_output, accuracy_stats)
        
        print("\n🔗 **ADAPTIVE LEARNING UPDATE**")
        print(f"   Brain Accuracy: {accuracy_stats.get('overall_accuracy', 0.5):.1%}")
        print(f"   Recommended Bias: {self.cognitive._compute_recommended_bias(accuracy_stats)}")
        print(f"   Confidence Adjustment: {self.cognitive._compute_confidence_adjustment(accuracy_stats):.2f}x")
        
        # ═══════════════════════════════════════════════════════════
        # PHASE 9: SAVE EVERYTHING
        # ═══════════════════════════════════════════════════════════
        analysis = {
            "skeptic": skeptic_result,
            "council": council_result,
            "speculations": speculations,
            "reflection": reflection_result,
            "accuracy": accuracy_stats,
            "prediction": prediction,
            "dreams": dreams,
            "live_pulse": pulse,
            "warfare_wisdom": warfare_wisdom,
            "celtic_wisdom": celtic_reading
        }
        self.memory.remember(talk, web_data, analysis)
        
        self.latest_prediction = prediction
        self.latest_analysis = analysis
        
        # ═══════════════════════════════════════════════════════════
        # FINAL SUMMARY
        # ═══════════════════════════════════════════════════════════
        print("\n" + "=" * 70)
        print("🧠 COGNITIVE CIRCLE COMPLETE - ALL ANCIENT WISDOM INTEGRATED")
        print("=" * 70)
        print(f"   ✅ Live pulse: {pulse['pulse']} (BTC ${pulse.get('btc_price', 0):,.0f})")
        print(f"   ✅ Gathered intelligence from {len(self.miner.SOURCES)} sources")
        print(f"   ✅ Debated with {len(self.council.advisors)} internal advisors")
        print(f"   ✅ Dreamed {len(dreams['scenarios_dreamed'])} scenarios")
        print(f"   ✅ Read Sun Tzu ({len(self.warfare_library.SUN_TZU_PRINCIPLES)} principles)")
        print(f"   ✅ Studied IRA tactics ({len(self.warfare_library.IRA_GUERRILLA_PRINCIPLES)} doctrines)")
        print(f"   ✅ Read the stars ({len(self.celtic_library.CELTIC_STARS)} constellations)")
        print(f"   ✅ Tuned to sacred frequencies ({len(self.celtic_library.SACRED_FREQUENCIES)} Hz)")
        print(f"   ✅ Consulted Druidic trees ({len(self.celtic_library.DRUIDIC_TREES)} Ogham)")
        print(f"   ✅ Moon phase: {celtic_reading['moon']['phase_name'].replace('_', ' ').title()}")
        print(f"   ✅ Tonalpohualli day: {aztec_reading['tonalpohualli']['name']} ({len(self.aztec_library.TONALPOHUALLI_SIGNS)} day-signs)")
        print(f"   ✅ Consulted Aztec deities ({len(self.aztec_library.TEOTL)} Teotl)")
        print(f"   ✅ Elder wisdom: Huehuehtlahtolli ({len(self.aztec_library.HUEHUEHTLAHTOLLI)} proverbs)")
        print(f"   ✅ Mimbres pottery ({len(self.mogollon_library.MIMBRES_SYMBOLS)} symbols)")
        print(f"   ✅ Mogollon proverbs ({len(self.mogollon_library.PROVERBS)} teachings)")
        print(f"   ✅ Pit house wisdom ({len(self.mogollon_library.PIT_HOUSE_WISDOM)} principles)")
        print(f"   ✅ Plantagenet kings ({len(self.plantagenet_library.KINGS)} monarchs)")
        print(f"   ✅ Magna Carta ({len(self.plantagenet_library.MAGNA_CARTA)} clauses)")
        print(f"   ✅ Hundred Years War ({len(self.plantagenet_library.HUNDRED_YEARS_WAR)} strategies)")
        print(f"   ✅ Wars of the Roses ({len(self.plantagenet_library.WARS_OF_ROSES)} lessons)")
        print(f"   ✅ Crusader wisdom ({len(self.plantagenet_library.CRUSADER_WISDOM)} lessons)")
        print(f"   ✅ Egyptian Netjeru ({len(self.egyptian_library.NETJERU)} deities)")
        print(f"   ✅ Laws of Ma'at ({len(self.egyptian_library.LAWS_OF_MAAT)} declarations)")
        print(f"   ✅ Nile seasons ({len(self.egyptian_library.NILE_SEASONS)} cycles)")
        print(f"   ✅ Book of the Dead ({len(self.egyptian_library.BOOK_OF_DEAD)} spells)")
        print(f"   ✅ Pyramid wisdom ({len(self.egyptian_library.PYRAMID_WISDOM)} geometries)")
        print(f"   ✅ Pharaoh lessons ({len(self.egyptian_library.PHARAOHS)} rulers)")
        print(f"   ✅ Sacred numbers ({len(self.pythagorean_library.SACRED_NUMBERS)} Pythagorean)")
        print(f"   ✅ Sacred ratios ({len(self.pythagorean_library.SACRED_RATIOS)} golden proportions)")
        print(f"   ✅ Planetary harmonics ({len(self.pythagorean_library.PLANETARY_HARMONICS)} celestial)")
        print(f"   ✅ Musical intervals ({len(self.pythagorean_library.INTERVALS)} ratios)")
        print(f"   ✅ Platonic solids ({len(self.pythagorean_library.PLATONIC_SOLIDS)} universal forms)")
        print(f"   ✅ Pythagorean maxims ({len(self.pythagorean_library.MAXIMS)} golden sayings)")
        print(f"   ✅ Unified Wisdom Engine ({self.wisdom_engine.wisdom_stats['total_civilizations']} civilizations)")
        print(f"   ✅ Sandbox Evolution ({self.sandbox_evolution.generations} generations, {self.sandbox_evolution.best_win_rate:.1f}% win rate)")
        if self.sandbox_evolution.ira_training:
            ira = self.sandbox_evolution.ira_training
            ira_win_rate = ira.get('win_rate') or 0
            ira_trades = ira.get('total_trades') or 0
            ira_move = ira.get('required_move_pct') or 0
            print(f"   ✅ IRA Training: {ira_win_rate:.2f}% win rate over {ira_trades:,} sims; target move {ira_move:.2f}%")
        print(f"   ✅ Analyzed own output for {len(reflection_result.get('blind_spots', []))} blind spots")
        print(f"   ✅ Validated {len(validated)} past predictions")
        print(f"   ✅ Generated {len(critiques)} self-critiques")
        print(f"   ✅ Recorded prediction for future validation")
        print(f"   ✅ Fed insights to Adaptive Learning system")
        print("=" * 70)
        print("🧠🌍 \"7 Civilizations, 5000 Years, 454 Generations - Evolution Never Stops.\"")
        print("=" * 70 + "\n")
        
        # Get unified wisdom consensus (7 civilizations)
        unified_consensus = unified_reading.get('consensus', {})
        
        # Extract individual civilization actions for the Quantum Brain
        civilization_actions = unified_reading.get('civilization_actions', {})
        
        # ═══════════════════════════════════════════════════════════
        # QUANTUM BRAIN INFLUENCE (if available)
        # ═══════════════════════════════════════════════════════════
        quantum_influenced_confidence = unified_consensus.get("confidence", 50.0)
        if hasattr(self, '_quantum_context') and self._quantum_context:
            qc = self._quantum_context.get('quantum_coherence', 0.5)
            is_lighthouse = self._quantum_context.get('is_lighthouse', False)
            
            # Quantum coherence can boost or reduce confidence
            # High coherence (>0.7) in lighthouse = boost confidence by up to 10%
            # Low coherence (<0.3) = reduce confidence by up to 10%
            if qc > 0.7 and is_lighthouse:
                quantum_boost = (qc - 0.7) * 33.3  # Up to +10% at Ψ=1.0
                quantum_influenced_confidence = min(100, quantum_influenced_confidence + quantum_boost)
            elif qc < 0.3:
                quantum_penalty = (0.3 - qc) * 33.3  # Up to -10% at Ψ=0.0
                quantum_influenced_confidence = max(0, quantum_influenced_confidence - quantum_penalty)
            
            print(f"\n🔮 QUANTUM INFLUENCE: Confidence adjusted from {unified_consensus.get('confidence', 50):.1f}% → {quantum_influenced_confidence:.1f}%")
        
        # ═══════════════════════════════════════════════════════════
        # SANDBOX EVOLUTION CONFIDENCE BOOST
        # ═══════════════════════════════════════════════════════════
        pre_sandbox_confidence = quantum_influenced_confidence
        sandbox_evolved_confidence = self.sandbox_evolution.get_evolved_confidence_boost(quantum_influenced_confidence)
        
        if sandbox_evolved_confidence != pre_sandbox_confidence:
            print(f"🧬 SANDBOX EVOLUTION: Confidence adjusted from {pre_sandbox_confidence:.1f}% → {sandbox_evolved_confidence:.1f}%")
            print(f"   (Based on {self.sandbox_evolution.best_win_rate:.1f}% win rate from {self.sandbox_evolution.generations} generations)")
        
        # Final confidence uses sandbox-evolved value
        final_confidence = sandbox_evolved_confidence
        
        # ═══════════════════════════════════════════════════════════
        # SANDBOX EVOLVED ENTRY FILTER CHECK
        # ═══════════════════════════════════════════════════════════
        # Estimate current market coherence from pulse
        pulse_dict = pulse if isinstance(pulse, dict) else {}
        market_sentiment = pulse_dict.get('pulse', 'NEUTRAL')
        btc_vol = abs(pulse_dict.get('btc_24h_change', 0))
        
        # Map sentiment to coherence estimate
        # 🎯 PENNY SNIPER: More generous coherence mapping for bear markets
        coherence_map = {
            'EUPHORIC': 0.90, 'BULLISH': 0.80, 'NEUTRAL': 0.65,
            'CAUTIOUS': 0.55, 'FEARFUL': 0.45, 'PANICKED': 0.35,
            'BEAR': 0.50, 'EXTREME_FEAR': 0.40  # Added mappings
        }
        estimated_coherence = coherence_map.get(market_sentiment, 0.55)  # Default 0.55 instead of 0.5
        
        # Apply sandbox entry filter with penny sniper mode
        should_trade, filter_reason = self.sandbox_evolution.get_entry_filter(btc_vol, estimated_coherence, penny_mode=True)

        ira_alignment = {}
        if self.sandbox_evolution.ira_training:
            ira = self.sandbox_evolution.ira_training
            required_move = ira.get('required_move_pct') or 0
            ira_alignment = {
                'win_rate': ira.get('win_rate') or 0,
                'total_trades': ira.get('total_trades') or 0,
                'avg_hold_bars': ira.get('avg_hold_bars'),
                'required_move_pct': required_move,
                'volatility_supports_move': btc_vol >= required_move if required_move else False,
            }
        
        print(f"\n🧬 SANDBOX ENTRY FILTER:")
        print(f"   Market Coherence: {estimated_coherence:.0%} (from '{market_sentiment}')")
        print(f"   24h Volatility: {btc_vol:.2f}%")
        print(f"   Filter Result: {filter_reason}")
        if should_trade:
            btc_price = pulse_dict.get('btc_price', 100000)
            targets = self.sandbox_evolution.get_exit_targets(btc_price, trade_size=10.0, exchange='binance')
            if 'penny_target_net' in targets:
                print(f"   🪙 SHARED GOAL: {targets['shared_goal']}")
                print(f"   → Penny TP Target: ${targets['take_profit_price']:,.2f} (+{targets['take_profit_pct']:.3f}%)")
            else:
                print(f"   → Take Profit Target: ${targets['take_profit_price']:,.2f} (+{targets['take_profit_pct']:.2f}%)")
                print(f"   → Loss Guard Reference: ${targets['stop_loss_price']:,.2f} (-{targets['stop_loss_pct']:.2f}%)")
        if ira_alignment:
            print("   IRA Training Insight:")
            print(
                f"      {ira_alignment.get('win_rate', 0):.2f}% win rate over {ira_alignment.get('total_trades', 0):,} simulations; "
                f"target move {ira_alignment.get('required_move_pct', 0):.2f}% vs 24h vol {btc_vol:.2f}%"
            )
            print(
                "      "
                + ("✅ Volatility supports penny target" if ira_alignment.get('volatility_supports_move') else "⚠️ Volatility may be too low for penny trigger")
            )

        return {
            "talk": talk,
            "consensus": council_result.get("consensus"),
            "unified_consensus": unified_consensus.get("sentiment", "NEUTRAL"),
            "unified_action": unified_consensus.get("action", "HOLD"),
            "unified_confidence": final_confidence,  # Now uses sandbox-evolved confidence
            "manipulation_probability": skeptic_result.get("manipulation_probability"),
            "speculations": speculations,
            "reflection": reflection_result,
            "accuracy": accuracy_stats,
            "prediction": prediction,
            "dreams": dreams,
            "live_pulse": pulse,
            "unified_reading": unified_reading,
            "civilization_actions": civilization_actions,
            "quantum_context_received": hasattr(self, '_quantum_context') and bool(self._quantum_context),
            # NEW: Sandbox Evolution Data
            "sandbox_evolution": {
                "generation": self.sandbox_evolution.generations,
                "best_win_rate": self.sandbox_evolution.best_win_rate,
                "should_trade": should_trade,
                "entry_filter_reason": filter_reason,
                "evolved_params": self.sandbox_evolution.params,
                "exit_targets": self.sandbox_evolution.get_exit_targets(pulse_dict.get('btc_price', 100000)) if should_trade else None,
                "position_size_pct": self.sandbox_evolution.params['position_size_pct'] * 100,
                "ira_training": self.sandbox_evolution.ira_training,
                "ira_alignment": ira_alignment,
            }
        }

    def get_recommendations(self, prices: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Backward-compatible recommendation API used by legacy scanner loops.

        Returns a lightweight ranked list of opportunities from provided market data.
        """
        recs: List[Dict[str, Any]] = []
        for symbol, payload in (prices or {}).items():
            try:
                if isinstance(payload, dict):
                    change_pct = float(payload.get('change_pct', payload.get('change', 0.0)) or 0.0)
                    volume = float(payload.get('volume', 0.0) or 0.0)
                else:
                    change_pct = 0.0
                    volume = 0.0

                score = abs(change_pct) * 0.7 + min(volume / 1_000_000.0, 1.0) * 0.3
                direction = 'BUY' if change_pct > 0 else ('SELL' if change_pct < 0 else 'HOLD')
                recs.append({
                    'symbol': symbol,
                    'direction': direction,
                    'confidence': min(0.99, max(0.01, score)),
                    'change_pct': change_pct,
                    'volume': volume,
                })
            except Exception:
                continue

        recs.sort(key=lambda x: x['confidence'], reverse=True)
        return recs[:10]

    def get_latest_prediction(self):
        """Get the latest prediction in a standardized format."""
        if self.latest_prediction:
            return {
                'direction': self.latest_prediction['predicted_direction'],
                'confidence': self.latest_prediction['confidence'],
                'truth_council_verdict': self.latest_analysis['council']['consensus'] if self.latest_analysis else 'UNKNOWN'
            }
        return None
    
    # ═══════════════════════════════════════════════════════════════════════
    # ⏳🔮 TIMELINE ORACLE INTEGRATION - 7-Day Future Validation
    # ═══════════════════════════════════════════════════════════════════════
    
    def select_timeline_branch(self, symbol: str, price: float, volume: float = 0, change_pct: float = 0):
        """
        Use Timeline Oracle to select the optimal future branch.
        
        "We're not predicting - we're acting out what has already come to be."
        
        Returns: (action, branch_id, confidence)
        """
        if not self.timeline_oracle:
            return ('HOLD', None, 0.5)
        
        try:
            action, branch = self.timeline_oracle.select_timeline(symbol, price, volume, change_pct)
            if branch:
                logger.info(f"⏳🔮 Timeline selected: {action.value} {symbol} (conf: {branch.branch_confidence:.2%})")
                return (action.value, branch.branch_id, branch.branch_confidence)
            return ('HOLD', None, 0.5)
        except Exception as e:
            logger.error(f"Timeline selection error: {e}")
            return ('HOLD', None, 0.5)
    
    def validate_timeline(self, branch_id: str, actual_price: float, actual_pnl: float = 0) -> bool:
        """
        Validate a timeline branch - confirm we chose correctly.
        
        "Each jump is a new timeline - we create a new branch on each step."
        """
        if not self.timeline_oracle or not branch_id:
            return False
        
        try:
            validation = self.timeline_oracle.validate_timeline(branch_id, actual_price, actual_pnl)
            if validation:
                logger.info(f"⏳✅ Timeline validated: {validation.timeline_accuracy:.1%} accuracy")
                return validation.timeline_accuracy > 0.5
            return False
        except Exception as e:
            logger.error(f"Timeline validation error: {e}")
            return False
    
    def get_timeline_status(self) -> dict:
        """Get current Timeline Oracle status."""
        if not self.timeline_oracle:
            return {'available': False}
        
        status = self.timeline_oracle.get_status()
        status['available'] = True
        return status


# ═══════════════════════════════════════════════════════════════════════════
# 🧠 GLOBAL MINER BRAIN SINGLETON - One Brain to Rule Them All
# ═══════════════════════════════════════════════════════════════════════════

_GLOBAL_MINER_BRAIN: MinerBrain = None

def get_miner_brain() -> MinerBrain:
    """
    Get or create the global MinerBrain singleton instance.
    
    This ensures all systems share the same brain for unified cognition.
    The Queen can use this to access all 11 civilizations of wisdom.
    
    Returns:
        MinerBrain: The global brain instance
    """
    global _GLOBAL_MINER_BRAIN
    
    if _GLOBAL_MINER_BRAIN is None:
        logger.info("🧠🌍 Initializing Global Miner Brain (11 Civilizations)...")
        _GLOBAL_MINER_BRAIN = MinerBrain()
        logger.info("🧠✅ Global Miner Brain ONLINE")
    
    return _GLOBAL_MINER_BRAIN


def run_brain_cycle():
    """Wrapper for backward compatibility."""
    brain = MinerBrain()
    brain.run_cycle()

def run_continuous_dreams(interval_seconds: int = 300):
    """
    Run the brain continuously - always dreaming, always watching.
    This is the "always-on" mode.
    """
    print("\n" + "🌙" * 35)
    print("   CONTINUOUS DREAM MODE ACTIVATED")
    print("   Brain will dream every {} seconds".format(interval_seconds))
    print("🌙" * 35 + "\n")
    
    brain = MinerBrain()
    cycle = 0
    
    try:
        while True:
            cycle += 1
            print(f"\n{'='*50}")
            print(f"🌙 DREAM CYCLE #{cycle} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*50}")
            
            brain.run_cycle()
            
            # Wait for next cycle
            time.sleep(interval_seconds)
            
    except KeyboardInterrupt:
        print("\n\n🌙 Dream mode ended. Brain returning to sleep...")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--dream":
        # Continuous dream mode
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        run_continuous_dreams(interval)
    else:
        # Single cycle
        run_brain_cycle()
