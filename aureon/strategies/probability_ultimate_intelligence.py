#!/usr/bin/env python3
"""
💎 PROBABILITY ULTIMATE INTELLIGENCE
=====================================
Learns patterns from backtesting

This module learns from every trade to build pattern recognition
that approaches perfect prediction.

Key innovations:
1. Multi-dimensional pattern keys (scenario × risk × proximity × momentum × clownfish)
2. Historical win rate tracking per pattern
3. Guaranteed win/loss pattern identification
4. Adaptive threshold based on pattern history
5. 🐠 Clownfish micro-change integration for 12-factor analysis

Pattern dimensions:
- Scenario: strong, dying, volatile, reversal, sideways (detected via acceleration)
- Risk Level: none, low (1 flag), high (2+ flags)
- Proximity: far (<20% to target), mid (20-50%), close (>50%)
- Momentum: down (<-0.1), flat (-0.1 to 0.3), up (>0.3)
- Clownfish: danger (<0.35), weak (0.35-0.55), neutral (0.55-0.75), strong (>0.75)
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import json
import logging
import time
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Optional
from collections import defaultdict

# Safe print function that won't fail on closed stdout
def safe_print(*args, **kwargs):
    """Print that won't crash if stdout is closed."""
    try:
        print(*args, **kwargs)
        if hasattr(sys.stdout, 'flush'):
            sys.stdout.flush()
    except (ValueError, OSError, IOError):
        pass  # Ignore I/O errors on closed file
logger = logging.getLogger(__name__)

from aureon.strategies.probability_intelligence_matrix import (
    get_probability_matrix,
    ProbabilityIntelligence
)

# � ThoughtBus - Primary neural communication
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought, get_thought_bus
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    THOUGHT_BUS_AVAILABLE = False

# 🐦 ChirpBus - kHz-speed signaling
try:
    from aureon.core.aureon_chirp_bus import get_chirp_bus, ChirpDirection, ChirpType
    CHIRP_BUS_AVAILABLE = True
except ImportError:
    CHIRP_BUS_AVAILABLE = False

# 👑 Queen Hive Mind - Decision approval
QUEEN_AVAILABLE = False
def _lazy_load_queen():
    global QUEEN_AVAILABLE
    try:
        from aureon.utils.aureon_queen_hive_mind import QueenHiveMind, get_queen
        QUEEN_AVAILABLE = True
        return get_queen()
    except ImportError:
        QUEEN_AVAILABLE = False
        return None

# �🐠 CLOWNFISH INTEGRATION - Lazy load to avoid circular imports
CLOWNFISH_AVAILABLE = False
ClownfishNode = None
MarketState = None

def _lazy_load_clownfish():
    """Lazy load to avoid circular imports with aureon_unified_ecosystem"""
    global CLOWNFISH_AVAILABLE, ClownfishNode, MarketState
    if ClownfishNode is not None:
        return CLOWNFISH_AVAILABLE
    try:
        from aureon.trading.aureon_unified_ecosystem import ClownfishNode as _ClownfishNode, MarketState as _MarketState
        ClownfishNode = _ClownfishNode
        MarketState = _MarketState
        CLOWNFISH_AVAILABLE = True
        return True
    except ImportError:
        CLOWNFISH_AVAILABLE = False
        return False

STATE_FILE = os.path.join(os.path.dirname(__file__), "probability_ultimate_state.json")


@dataclass
class PatternStats:
    """Statistics for a specific pattern combination."""
    wins: int = 0
    losses: int = 0
    total: int = 0
    avg_probability: float = 0.5
    avg_momentum: float = 0.0
    last_updated: float = 0.0
    
    @property
    def win_rate(self) -> float:
        return self.wins / self.total if self.total > 0 else 0.5
    
    @property
    def is_guaranteed_win(self) -> bool:
        """100% win rate with enough samples."""
        return self.win_rate >= 0.99 and self.total >= 10
    
    @property
    def is_guaranteed_loss(self) -> bool:
        """0% win rate with enough samples."""
        return self.win_rate <= 0.01 and self.total >= 10
    
    @property
    def confidence(self) -> float:
        """How confident are we in this pattern?"""
        if self.total < 5:
            return 0.3  # Low confidence with few samples
        elif self.total < 20:
            return 0.6  # Medium confidence
        elif self.total < 50:
            return 0.8  # High confidence
        else:
            return 0.95  # Very high confidence


@dataclass
class UltimatePrediction:
    """The ultimate prediction with full intelligence."""
    # Base probability from matrix
    base_probability: float
    
    # Pattern-based adjustment (now 5D with clownfish)
    pattern_key: Tuple[str, str, str, str, str]
    pattern_win_rate: float
    pattern_confidence: float
    pattern_samples: int
    
    # Final prediction
    final_probability: float
    should_trade: bool
    
    # Intelligence from matrix
    matrix_intel: ProbabilityIntelligence
    
    # Special flags
    is_guaranteed_win: bool = False
    is_guaranteed_loss: bool = False
    
    # 🐠 Clownfish micro-change signal
    clownfish_signal: float = 0.5
    
    # Reasoning
    reasoning: str = ""


class ProbabilityUltimateIntelligence:
    """
    The ultimate probability system that learns from every trade.
    Learns patterns from backtesting.
    
    🐠 Enhanced with Clownfish v2.0 micro-change detection for 5D pattern keys.
    """
    
    def __init__(self):
        self.matrix = get_probability_matrix()
        # Pattern keys are now 5-dimensional (includes clownfish)
        self.patterns: Dict[Tuple[str, str, str, str, str], PatternStats] = {}
        self.total_predictions = 0
        self.correct_predictions = 0
        
        # 🐠 Initialize ClownfishNode for micro-change detection
        self.clownfish = None
        if CLOWNFISH_AVAILABLE and ClownfishNode is not None:
            try:
                self.clownfish = ClownfishNode()
                logger.debug("🐠 ClownfishNode v2.0 initialized for pattern learning")
            except Exception as e:
                logger.debug("ClownfishNode init failed: %s", e)
        
        # 🔗 Initialize Communication Buses
        self.thought_bus = get_thought_bus() if THOUGHT_BUS_AVAILABLE else None
        self.chirp_bus = get_chirp_bus() if CHIRP_BUS_AVAILABLE else None
        self.queen = _lazy_load_queen()
        
        if self.thought_bus:
            logger.debug("📡 Ultimate Intelligence: Wired to ThoughtBus")
        if self.chirp_bus:
            logger.debug("🐦 Ultimate Intelligence: Wired to ChirpBus")
        if self.queen:
            logger.debug("👑 Ultimate Intelligence: Connected to Queen Hive")
        
        self._load_state()
    
    def _load_state(self):
        """Load learned patterns from disk."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    data = json.load(f)
                
                for key_str, stats in data.get("patterns", {}).items():
                    # Parse key from string
                    key = tuple(key_str.split("|"))
                    self.patterns[key] = PatternStats(
                        wins=stats.get("wins", 0),
                        losses=stats.get("losses", 0),
                        total=stats.get("total", 0),
                        avg_probability=stats.get("avg_probability", 0.5),
                        avg_momentum=stats.get("avg_momentum", 0.0),
                        last_updated=stats.get("last_updated", 0.0)
                    )
                
                self.total_predictions = data.get("total_predictions", 0)
                self.correct_predictions = data.get("correct_predictions", 0)
                
                logger.debug("💎 Loaded %s learned patterns", len(self.patterns))
            except Exception as e:
                safe_print(f"⚠️ Could not load state: {e}")
    
    def _save_state(self):
        """Save learned patterns to disk."""
        try:
            patterns_dict = {}
            for key, stats in self.patterns.items():
                key_str = "|".join(key)
                patterns_dict[key_str] = {
                    "wins": stats.wins,
                    "losses": stats.losses,
                    "total": stats.total,
                    "avg_probability": stats.avg_probability,
                    "avg_momentum": stats.avg_momentum,
                    "last_updated": stats.last_updated
                }
            
            data = {
                "patterns": patterns_dict,
                "total_predictions": self.total_predictions,
                "correct_predictions": self.correct_predictions,
                "last_updated": time.time()
            }
            
            with open(STATE_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            safe_print(f"⚠️ Could not save state: {e}")
    
    def _detect_scenario(
        self,
        pnl_history: List[Tuple[float, float]],
        momentum: float
    ) -> str:
        """
        Detect market scenario from PnL history.
        
        Returns: strong, dying, volatile, reversal, or sideways
        """
        if len(pnl_history) < 5:
            return "unknown"
        
        # Calculate acceleration (change in velocity)
        velocities = []
        for i in range(1, len(pnl_history)):
            dt = pnl_history[i][0] - pnl_history[i-1][0]
            if dt > 0:
                dpnl = pnl_history[i][1] - pnl_history[i-1][1]
                velocities.append(dpnl / dt)
        
        if len(velocities) < 2:
            return "unknown"
        
        # Average acceleration
        accelerations = []
        for i in range(1, len(velocities)):
            accelerations.append(velocities[i] - velocities[i-1])
        
        avg_acceleration = sum(accelerations) / len(accelerations) if accelerations else 0
        
        # Volatility (std dev of velocities)
        if len(velocities) >= 2:
            mean_vel = sum(velocities) / len(velocities)
            variance = sum((v - mean_vel) ** 2 for v in velocities) / len(velocities)
            volatility = variance ** 0.5
        else:
            volatility = 0
        
        # Classify scenario
        high_volatility = volatility > 0.0001
        strong_momentum = momentum > 0.5
        weak_momentum = momentum < 0.2
        decelerating = avg_acceleration < -0.00001
        
        # Check for reversal (momentum was up, now accelerating down)
        if momentum > 0 and avg_acceleration < -0.00002:
            return "reversal"
        
        if high_volatility:
            return "volatile"
        
        if strong_momentum and avg_acceleration >= 0:
            return "strong"
        
        if weak_momentum and decelerating:
            return "dying"
        
        if abs(momentum) < 0.1:
            return "sideways"
        
        # Default based on momentum
        if momentum > 0.3:
            return "strong"
        elif momentum < -0.1:
            return "dying"
        else:
            return "sideways"
    
    def _build_pattern_key(
        self,
        scenario: str,
        risk_flags: List[str],
        current_pnl: float,
        target_pnl: float,
        momentum: float,
        clownfish_signal: float = 0.5
    ) -> Tuple[str, str, str, str, str]:
        """Build the multi-dimensional pattern key (now 5D with clownfish)."""
        
        # Risk level
        if len(risk_flags) == 0:
            risk_level = "none"
        elif len(risk_flags) == 1:
            risk_level = "low"
        else:
            risk_level = "high"
        
        # Proximity to target
        if target_pnl > 0:
            proximity = current_pnl / target_pnl
        else:
            proximity = 0
        
        if proximity >= 0.5:
            prox_cat = "close"
        elif proximity >= 0.2:
            prox_cat = "mid"
        else:
            prox_cat = "far"
        
        # Momentum category
        if momentum > 0.3:
            mom_cat = "up"
        elif momentum > -0.1:
            mom_cat = "flat"
        else:
            mom_cat = "down"
        
        # 🐠 Clownfish micro-change category (5th dimension)
        if clownfish_signal > 0.75:
            cf_cat = "strong"
        elif clownfish_signal > 0.55:
            cf_cat = "neutral"
        elif clownfish_signal > 0.35:
            cf_cat = "weak"
        else:
            cf_cat = "danger"
        
        return (scenario, risk_level, prox_cat, mom_cat, cf_cat)
    
    def predict(
        self,
        current_pnl: float,
        target_pnl: float,
        pnl_history: List[Tuple[float, float]],
        momentum_score: float = 0.0,
        market_state: Optional[any] = None,
        symbol: str = "UNKNOWN"
    ) -> UltimatePrediction:
        """
        Generate the ultimate prediction combining matrix intelligence
        with learned pattern recognition.
        
        🐠 Now includes 5th dimension: Clownfish micro-change analysis.
        
        Args:
            current_pnl: Current profit/loss
            target_pnl: Target profit/loss
            pnl_history: List of (timestamp, pnl) tuples
            momentum_score: Current momentum (0-1)
            market_state: Optional MarketState for Clownfish analysis
            symbol: Optional symbol identifier for bus emission
        """
        
        # 🐠 Compute Clownfish signal if available
        clownfish_signal = 0.5  # Default neutral
        clownfish_boost = 1.0
        
        if self.clownfish is not None and market_state is not None:
            try:
                cf_result = self.clownfish.compute(market_state)
                clownfish_signal = cf_result.get('signal', 0.5)
                micro_signals = cf_result.get('micro_signals', {})
                
                # Count strong/danger signals
                strong_count = sum(1 for v in micro_signals.values() if v > 0.7)
                danger_count = sum(1 for v in micro_signals.values() if v < 0.3)
                
                # Calculate boost/penalty
                if strong_count >= 4:
                    clownfish_boost = 1.12  # Strong micro-change support
                elif strong_count >= 3:
                    clownfish_boost = 1.06
                elif danger_count >= 3:
                    clownfish_boost = 0.88  # Micro-change danger
                elif danger_count >= 2:
                    clownfish_boost = 0.94
            except Exception as e:
                safe_print(f"⚠️ Clownfish compute error: {e}")
        
        # Get base intelligence from matrix
        matrix_intel = self.matrix.calculate_intelligent_probability(
            current_pnl=current_pnl,
            target_pnl=target_pnl,
            pnl_history=pnl_history,
            momentum_score=momentum_score
        )
        
        # Detect scenario from history
        scenario = self._detect_scenario(pnl_history, momentum_score)
        
        # Build pattern key (now 5D with clownfish)
        pattern_key = self._build_pattern_key(
            scenario=scenario,
            risk_flags=matrix_intel.risk_flags,
            current_pnl=current_pnl,
            target_pnl=target_pnl,
            momentum=momentum_score,
            clownfish_signal=clownfish_signal
        )
        
        # Get pattern stats if we have them
        pattern_stats = self.patterns.get(pattern_key)
        
        if pattern_stats and pattern_stats.total >= 5:
            # We have learned data for this pattern
            pattern_win_rate = pattern_stats.win_rate
            pattern_confidence = pattern_stats.confidence
            pattern_samples = pattern_stats.total
            
            # Check for guaranteed patterns
            is_guaranteed_win = pattern_stats.is_guaranteed_win
            is_guaranteed_loss = pattern_stats.is_guaranteed_loss
        else:
            # No learned data, use matrix probability
            pattern_win_rate = matrix_intel.adjusted_probability
            pattern_confidence = 0.3
            pattern_samples = 0
            is_guaranteed_win = False
            is_guaranteed_loss = False
        
        # Calculate final probability
        if is_guaranteed_win:
            final_probability = 0.99
            reasoning = f"🏆 GUARANTEED WIN pattern detected! {pattern_samples} historical samples, all wins"
        elif is_guaranteed_loss:
            final_probability = 0.01
            reasoning = f"💀 GUARANTEED LOSS pattern detected! {pattern_samples} historical samples, all losses"
        elif pattern_confidence > 0.5:
            # Blend matrix and pattern with weight based on confidence
            weight = pattern_confidence
            final_probability = (
                weight * pattern_win_rate +
                (1 - weight) * matrix_intel.adjusted_probability
            )
            reasoning = f"Pattern {pattern_key} has {pattern_samples} samples, {pattern_win_rate*100:.1f}% win rate"
        else:
            # Fall back to matrix
            final_probability = matrix_intel.adjusted_probability
            reasoning = f"Limited pattern data ({pattern_samples} samples), using matrix intelligence"
        
        # 🐠 Apply Clownfish boost/penalty to final probability
        if clownfish_boost != 1.0:
            final_probability = 0.5 + (final_probability - 0.5) * clownfish_boost
            final_probability = max(0.01, min(0.99, final_probability))
            if clownfish_boost > 1.0:
                reasoning += f" 🐠+{(clownfish_boost-1)*100:.0f}%"
            else:
                reasoning += f" 🐠{(clownfish_boost-1)*100:.0f}%"
        
        # Final decision
        # Use 0.50 threshold for patterns we know, 0.45 for unknown
        threshold = 0.50 if pattern_confidence > 0.5 else 0.45
        should_trade = final_probability >= threshold
        
        # Override: Never trade guaranteed losses
        if is_guaranteed_loss:
            should_trade = False
        
        # 🐠 Override: Block trade if clownfish shows strong danger
        if clownfish_signal < 0.25 and not is_guaranteed_win:
            should_trade = False
            reasoning += " [🐠BLOCKED:danger]"
        
        # Override: Always consider guaranteed wins (but still check matrix action)
        if is_guaranteed_win and matrix_intel.action != "DANGER":
            should_trade = True
        
        prediction = UltimatePrediction(
            base_probability=matrix_intel.adjusted_probability,
            pattern_key=pattern_key,
            pattern_win_rate=pattern_win_rate,
            pattern_confidence=pattern_confidence,
            pattern_samples=pattern_samples,
            final_probability=final_probability,
            should_trade=should_trade,
            matrix_intel=matrix_intel,
            is_guaranteed_win=is_guaranteed_win,
            is_guaranteed_loss=is_guaranteed_loss,
            clownfish_signal=clownfish_signal,
            reasoning=reasoning
        )
        
        # 🔊 Publish to Hive Mind if integrated
        if hasattr(self, 'publish_prediction'):
            self.publish_prediction(prediction, symbol)
            
        return prediction
    
    def publish_prediction(self, prediction: UltimatePrediction, symbol: str = "UNKNOWN"):
        """Publish the prediction to the Hive Mind (ThoughtBus + ChirpBus)."""
        
        # 1. ThoughtBus (Brain Persistence)
        if hasattr(self, 'thought_bus') and self.thought_bus and prediction.should_trade:
            try:
                thought = Thought(
                    source="ultimate_intelligence",
                    topic="prediction.opportunity.strong" if prediction.final_probability > 0.8 else "prediction.opportunity",
                    payload={
                        "symbol": symbol,
                        "probability": prediction.final_probability,
                        "confidence": prediction.pattern_confidence,
                        "is_guaranteed": prediction.is_guaranteed_win,
                        "pattern_key": "|".join(prediction.pattern_key),
                        "reasoning": prediction.reasoning,
                        "timestamp": time.time()
                    }
                )
                self.thought_bus.publish(thought)
            except Exception as e:
                safe_print(f"⚠️ Failed to publish thought: {e}")

        # 2. ChirpBus (Speed Signal)
        if hasattr(self, 'chirp_bus') and self.chirp_bus and prediction.should_trade:
            try:
                # Use frequency based on probability (higher prob = higher freq)
                freq = 432 + (prediction.final_probability * 400) # 432Hz - 832Hz
                
                self.chirp_bus.emit_message(
                    message=f"ULTIMATE_PREDICTION {symbol} {prediction.final_probability:.2f}",
                    direction=ChirpDirection.UP,
                    confidence=prediction.final_probability,
                    symbol=symbol,
                    frequency=freq,
                    message_type=ChirpType.OPPORTUNITY
                )
            except Exception as e:
                safe_print(f"⚠️ Failed to emit chirp: {e}")

    def record_outcome(
        self,
        pattern_key: Tuple[str, str, str, str, str],
        won: bool,
        probability: float,
        momentum: float,
        predicted: bool,
        clownfish_signal: float = 0.5
    ):
        """Record the outcome of a trade for learning.
        
        🐠 Pattern key is now 5D: (scenario, risk, proximity, momentum, clownfish)
        """
        
        # Update pattern stats
        if pattern_key not in self.patterns:
            self.patterns[pattern_key] = PatternStats()
        
        stats = self.patterns[pattern_key]
        stats.total += 1
        if won:
            stats.wins += 1
        else:
            stats.losses += 1
        
        # Update rolling averages
        n = stats.total
        stats.avg_probability = (stats.avg_probability * (n - 1) + probability) / n
        stats.avg_momentum = (stats.avg_momentum * (n - 1) + momentum) / n
        stats.last_updated = time.time()
        
        # Update prediction accuracy
        self.total_predictions += 1
        if predicted == won:
            self.correct_predictions += 1
        
        # 🐠 Feed outcome to Clownfish for neural learning
        if self.clownfish is not None and hasattr(self.clownfish, 'record_signal_outcome'):
            try:
                self.clownfish.record_signal_outcome(won, clownfish_signal)
            except Exception:
                pass
        
        # Log learning
        accuracy = self.correct_predictions / self.total_predictions * 100 if self.total_predictions > 0 else 0
        cf_dim = pattern_key[4] if len(pattern_key) > 4 else "n/a"
        safe_print(f"💎 Pattern {pattern_key[:4]}|🐠{cf_dim}: {stats.wins}/{stats.total} wins ({stats.win_rate*100:.1f}%)")
        safe_print(f"   Overall accuracy: {accuracy:.1f}% ({self.correct_predictions}/{self.total_predictions})")
        
        # Save every 10 outcomes
        if stats.total % 10 == 0:
            self._save_state()
    
    def get_predictions(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Backward-compatible summary predictions for legacy orchestrators."""
        predictions: List[Dict[str, Any]] = []
        for key, stats in self.patterns.items():
            if stats.total < 5:
                continue
            predictions.append({
                'pattern_key': key,
                'win_rate': stats.win_rate,
                'confidence': stats.confidence,
                'samples': stats.total,
                'should_trade': stats.win_rate >= 0.5,
            })

        predictions.sort(key=lambda x: (x['confidence'], x['win_rate'], x['samples']), reverse=True)
        return predictions[:max(1, limit)]

    def get_guaranteed_patterns(self) -> Dict[str, List[Tuple[str, str, str, str]]]:
        """Get all guaranteed win/loss patterns."""
        
        wins = []
        losses = []
        
        for key, stats in self.patterns.items():
            if stats.is_guaranteed_win:
                wins.append(key)
            elif stats.is_guaranteed_loss:
                losses.append(key)
        
        return {"wins": wins, "losses": losses}
    
    @property
    def accuracy(self) -> float:
        """Overall prediction accuracy."""
        if self.total_predictions == 0:
            return 0.0
        return self.correct_predictions / self.total_predictions
    
    def get_stats(self) -> Dict:
        """Get comprehensive statistics."""
        guaranteed = self.get_guaranteed_patterns()
        
        return {
            "total_patterns_learned": len(self.patterns),
            "total_predictions": self.total_predictions,
            "correct_predictions": self.correct_predictions,
            "accuracy": self.accuracy * 100,
            "guaranteed_win_patterns": len(guaranteed["wins"]),
            "guaranteed_loss_patterns": len(guaranteed["losses"]),
            "high_confidence_patterns": sum(1 for s in self.patterns.values() if s.confidence >= 0.8)
        }


# Global singleton
_ultimate_intelligence = None

def get_ultimate_intelligence() -> ProbabilityUltimateIntelligence:
    """Get the global Ultimate Intelligence instance."""
    global _ultimate_intelligence
    if _ultimate_intelligence is None:
        _ultimate_intelligence = ProbabilityUltimateIntelligence()
    return _ultimate_intelligence


def ultimate_predict(
    current_pnl: float,
    target_pnl: float,
    pnl_history: List[Tuple[float, float]],
    momentum_score: float = 0.0
) -> UltimatePrediction:
    """Quick access to ultimate prediction."""
    return get_ultimate_intelligence().predict(
        current_pnl=current_pnl,
        target_pnl=target_pnl,
        pnl_history=pnl_history,
        momentum_score=momentum_score
    )


def record_ultimate_outcome(
    pattern_key: Tuple[str, str, str, str],
    won: bool,
    probability: float,
    momentum: float,
    predicted: bool
):
    """Quick access to record outcome."""
    get_ultimate_intelligence().record_outcome(
        pattern_key=pattern_key,
        won=won,
        probability=probability,
        momentum=momentum,
        predicted=predicted
    )


if __name__ == "__main__":
    safe_print("\n💎 PROBABILITY ULTIMATE INTELLIGENCE")
    safe_print("=" * 60)
    
    intel = get_ultimate_intelligence()
    stats = intel.get_stats()
    
    safe_print(f"\n📊 Current Status:")
    safe_print(f"   Patterns Learned: {stats['total_patterns_learned']}")
    safe_print(f"   Total Predictions: {stats['total_predictions']}")
    safe_print(f"   Accuracy: {stats['accuracy']:.1f}%")
    safe_print(f"   Guaranteed Win Patterns: {stats['guaranteed_win_patterns']}")
    safe_print(f"   Guaranteed Loss Patterns: {stats['guaranteed_loss_patterns']}")
    safe_print(f"   High Confidence Patterns: {stats['high_confidence_patterns']}")
    
    # Test prediction
    safe_print(f"\n🧪 Test Prediction:")
    now = time.time()
    test_history = [
        (now - 10, 0.001),
        (now - 8, 0.003),
        (now - 6, 0.005),
        (now - 4, 0.006),
        (now - 2, 0.007),
        (now, 0.008),
    ]
    
    prediction = intel.predict(
        current_pnl=0.008,
        target_pnl=0.01,
        pnl_history=test_history,
        momentum_score=0.6
    )
    
    safe_print(f"   Pattern: {prediction.pattern_key}")
    safe_print(f"   Base Probability: {prediction.base_probability*100:.1f}%")
    safe_print(f"   Pattern Win Rate: {prediction.pattern_win_rate*100:.1f}%")
    safe_print(f"   Final Probability: {prediction.final_probability*100:.1f}%")
    safe_print(f"   Should Trade: {'✅ YES' if prediction.should_trade else '❌ NO'}")
    safe_print(f"   Reasoning: {prediction.reasoning}")
    
    if prediction.is_guaranteed_win:
        safe_print(f"   🏆 GUARANTEED WIN DETECTED!")
    elif prediction.is_guaranteed_loss:
        safe_print(f"   💀 GUARANTEED LOSS DETECTED!")
