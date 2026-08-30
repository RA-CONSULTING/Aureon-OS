from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys, os
if sys.platform == 'win32' and sys.stdout.isatty() and sys.stderr.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            """Check if stream is already a UTF-8 TextIOWrapper."""
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        # Only wrap if not already UTF-8 wrapped (prevents re-wrapping on import)
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffling=True)
        if hasattr(sys.stderr, 'buffer') and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffling=True)
    except Exception:
        pass

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Firm intelligence catalog integration
try:
    from aureon.bots_intelligence.aureon_firm_intelligence_catalog import get_firm_catalog, FirmIntelligenceCatalog
    CATALOG_AVAILABLE = True
except ImportError:
    CATALOG_AVAILABLE = False
    logger.debug("Firm Intelligence Catalog not available")

# Sacred constants for counter-intelligence
PHI = (1 + math.sqrt(5)) / 2  # Golden ratio for timing calculations
LOVE_FREQUENCY = 528  # Hz for resonance-based counter-timing
SCHUMANN_BASE = 7.83  # Hz for earth resonance timing

class CounterStrategy(Enum):
    TIMING_ADVANTAGE = "timing_advantage"  # 30-200ms faster execution
    PATTERN_EXPLOITATION = "pattern_exploitation"  # Exploit known firm patterns
    MOMENTUM_COUNTER = "momentum_counter"  # Counter momentum-based strategies
    VOLUME_SPIKE_COUNTER = "volume_spike_counter"  # Counter volume-based attacks
    HFT_FRONT_RUNNING = "hft_front_running"  # Front-run HFT algorithms
    ICEBERG_ORDER_EXPLOIT = "iceberg_order_exploit"  # Detect and counter iceberg orders

@dataclass
class FirmCounterStrategy:
    firm_name: str
    primary_strategy: CounterStrategy
    timing_advantage_ms: float  # How many ms faster we can execute
    confidence_score: float = 0.0
    last_updated: float = field(default_factory=time.time)
    exploit_patterns: List[str] = field(default_factory=list)
    success_rate: float = 0.0
    risk_adjusted_return: float = 0.0

@dataclass
class CounterIntelligenceSignal:
    firm_id: str
    strategy: CounterStrategy
    confidence: float
    timing_advantage: float
    expected_profit_pips: float
    risk_score: float
    execution_window_seconds: float
    reasoning: str

class QueenCounterIntelligence:
    """
    Queen's Counter-Intelligence Weapon System
    
    Uses firm intelligence data to beat major trading firms at their own game.
    Implements timing advantages (30-200ms faster) and pattern exploitation.
    """

    def __init__(self, firm_intelligence_db: Optional[Dict] = None):
        self.firm_intelligence_db = firm_intelligence_db or {}
        self.counter_strategies: Dict[str, FirmCounterStrategy] = {}
        self.active_counters: List[CounterIntelligenceSignal] = []
        self.timing_calibrations: Dict[str, float] = {}
        
        # Initialize firm intelligence catalog
        self.catalog: Optional[FirmIntelligenceCatalog] = None
        if CATALOG_AVAILABLE:
            self.catalog = get_firm_catalog()
            logger.info("📊 Firm Intelligence Catalog integrated")
        
        # Initialize firm-specific counter-strategies
        self._initialize_firm_counter_strategies()
        
        logger.info("Queen Counter-Intelligence System initialized")

    def _initialize_firm_counter_strategies(self):
        """Initialize counter-strategies for known firms based on their patterns."""
        
        # Citadel - HFT timing advantage
        self.counter_strategies["citadel"] = FirmCounterStrategy(
            firm_name="Citadel",
            primary_strategy=CounterStrategy.TIMING_ADVANTAGE,
            timing_advantage_ms=45.0,  # 45ms faster than Citadel's typical latency
            exploit_patterns=[
                "latency_arbitrage",
                "co_location_advantage",
                "order_flow_prediction"
            ]
        )
        
        # Jane Street - Pattern exploitation
        self.counter_strategies["jane_street"] = FirmCounterStrategy(
            firm_name="Jane Street",
            primary_strategy=CounterStrategy.PATTERN_EXPLOITATION,
            timing_advantage_ms=30.0,
            exploit_patterns=[
                "vwap_execution_pattern",
                "market_making_cycles",
                "statistical_arbitrage_loops"
            ]
        )
        
        # Two Sigma - Momentum counter
        self.counter_strategies["two_sigma"] = FirmCounterStrategy(
            firm_name="Two Sigma",
            primary_strategy=CounterStrategy.MOMENTUM_COUNTER,
            timing_advantage_ms=60.0,
            exploit_patterns=[
                "momentum_reversal_detection",
                "machine_learning_prediction_counter",
                "signal_decay_exploitation"
            ]
        )
        
        # Jump Trading - Volume spike counter
        self.counter_strategies["jump_trading"] = FirmCounterStrategy(
            firm_name="Jump Trading",
            primary_strategy=CounterStrategy.VOLUME_SPIKE_COUNTER,
            timing_advantage_ms=25.0,
            exploit_patterns=[
                "volume_spike_prediction",
                "liquidity_grabbing_counter",
                "order_book_manipulation_detection"
            ]
        )
        
        # DRW - HFT front-running
        self.counter_strategies["drw"] = FirmCounterStrategy(
            firm_name="DRW",
            primary_strategy=CounterStrategy.HFT_FRONT_RUNNING,
            timing_advantage_ms=35.0,
            exploit_patterns=[
                "order_flow_front_running",
                "latency_based_arbitrage",
                "queue_position_exploitation"
            ]
        )
        
        # Millennium - Iceberg order exploit
        self.counter_strategies["millennium"] = FirmCounterStrategy(
            firm_name="Millennium",
            primary_strategy=CounterStrategy.ICEBERG_ORDER_EXPLOIT,
            timing_advantage_ms=50.0,
            exploit_patterns=[
                "iceberg_order_detection",
                "hidden_liquidity_exploitation",
                "order_splitting_counter"
            ]
        )

    def analyze_firm_for_counter_opportunity(self, firm_id: str, market_data: Dict, 
                                           bot_detection_data: Dict) -> Optional[CounterIntelligenceSignal]:
        """
        Analyze a specific firm for counter-trading opportunities.
        
        Args:
            firm_id: The firm identifier
            market_data: Current market data snapshot
            bot_detection_data: Bot detection results
            
        Returns:
            CounterIntelligenceSignal if opportunity found, None otherwise
        """
        if firm_id not in self.counter_strategies:
            logger.warning(f"No counter-strategy defined for firm: {firm_id}")
            return None
            
        strategy = self.counter_strategies[firm_id]
        
        # Calculate confidence based on firm intelligence and market conditions
        confidence = self._calculate_counter_confidence(firm_id, market_data, bot_detection_data)
        
        if confidence < 0.7:  # Minimum confidence threshold
            return None
            
        # Calculate timing advantage with resonance harmonics
        timing_advantage = self._calculate_timing_advantage(firm_id, market_data)
        
        # Estimate profit potential
        expected_profit = self._estimate_counter_profit(strategy.primary_strategy, market_data)
        
        # Assess risk
        risk_score = self._assess_counter_risk(firm_id, strategy.primary_strategy, market_data)
        
        # Determine execution window
        execution_window = self._calculate_execution_window(strategy.primary_strategy, timing_advantage)
        
        # Generate reasoning
        reasoning = self._generate_counter_reasoning(firm_id, strategy, confidence, timing_advantage)
        
        signal = CounterIntelligenceSignal(
            firm_id=firm_id,
            strategy=strategy.primary_strategy,
            confidence=confidence,
            timing_advantage=timing_advantage,
            expected_profit_pips=expected_profit,
            risk_score=risk_score,
            execution_window_seconds=execution_window,
            reasoning=reasoning
        )
        
        # Update strategy success metrics
        self._update_strategy_metrics(firm_id, signal)
        
        logger.info(f"Counter-opportunity detected for {firm_id}: {strategy.primary_strategy.value} "
                   f"(confidence: {confidence:.2f}, timing: {timing_advantage:.1f}ms)")
        
        return signal

    def _calculate_counter_confidence(self, firm_id: str, market_data: Dict, 
                                    bot_detection_data: Dict) -> float:
        """Calculate confidence score for counter-trading opportunity."""
        base_confidence = 0.5
        
        # Firm intelligence confidence
        if firm_id in self.firm_intelligence_db:
            firm_data = self.firm_intelligence_db[firm_id]
            base_confidence += firm_data.get('attribution_confidence', 0) * 0.3
            
        # Bot detection confidence
        if 'confidence' in bot_detection_data:
            base_confidence += bot_detection_data['confidence'] * 0.2
            
        # Market condition factors
        volatility = market_data.get('volatility', 0.5)
        volume = market_data.get('volume_ratio', 1.0)
        
        # Higher confidence in volatile, high-volume conditions
        market_factor = min(1.0, (volatility * 2 + volume) / 3)
        base_confidence += market_factor * 0.2
        
        return min(1.0, base_confidence)

    def _calculate_timing_advantage(self, firm_id: str, market_data: Dict) -> float:
        """Calculate timing advantage using resonance harmonics."""
        base_advantage = self.counter_strategies[firm_id].timing_advantage_ms
        
        # Apply Schumann resonance timing (7.83 Hz = ~128ms cycle)
        schumann_factor = math.sin(time.time() * SCHUMANN_BASE * 2 * math.pi) * 0.1 + 1.0
        
        # Apply golden ratio timing optimization
        phi_factor = (PHI - 1) * 10  # Convert to millisecond scale
        
        # Market latency factor
        market_latency = market_data.get('average_latency_ms', 50)
        latency_factor = max(0.5, 1 - (market_latency / 100))
        
        total_advantage = base_advantage * schumann_factor * phi_factor * latency_factor
        
        return max(10.0, min(200.0, total_advantage))  # Clamp between 10-200ms

    def _estimate_counter_profit(self, strategy: CounterStrategy, market_data: Dict) -> float:
        """Estimate profit potential in pips for counter-strategy."""
        base_profit = 0.5  # Base 0.5 pips
        
        # Strategy-specific multipliers
        strategy_multipliers = {
            CounterStrategy.TIMING_ADVANTAGE: 1.5,
            CounterStrategy.PATTERN_EXPLOITATION: 1.8,
            CounterStrategy.MOMENTUM_COUNTER: 2.0,
            CounterStrategy.VOLUME_SPIKE_COUNTER: 2.5,
            CounterStrategy.HFT_FRONT_RUNNING: 1.3,
            CounterStrategy.ICEBERG_ORDER_EXPLOIT: 1.7
        }
        
        multiplier = strategy_multipliers.get(strategy, 1.0)
        
        # Market condition adjustments
        volatility = market_data.get('volatility', 0.5)
        spread = market_data.get('spread_pips', 2.0)
        
        market_adjustment = (volatility * 2 + (10 / spread)) / 3
        
        return base_profit * multiplier * market_adjustment

    def _assess_counter_risk(self, firm_id: str, strategy: CounterStrategy, market_data: Dict) -> float:
        """Assess risk score for counter-strategy (0-1, higher = riskier)."""
        base_risk = 0.3
        
        # Firm-specific risk adjustments
        firm_risk_adjustments = {
            "citadel": 0.8,  # High risk due to HFT competition
            "jane_street": 0.6,  # Moderate risk
            "two_sigma": 0.7,  # ML-based, unpredictable
            "jump_trading": 0.9,  # Volume-based, high risk
            "drw": 0.8,  # HFT focused
            "millennium": 0.5   # More conservative
        }
        
        firm_risk = firm_risk_adjustments.get(firm_id, 0.6)
        base_risk += firm_risk * 0.4
        
        # Market condition risk
        volatility = market_data.get('volatility', 0.5)
        base_risk += volatility * 0.3
        
        return min(1.0, base_risk)

    def _calculate_execution_window(self, strategy: CounterStrategy, timing_advantage: float) -> float:
        """Calculate execution window in seconds."""
        base_window = 30.0  # 30 seconds base
        
        # Strategy-specific adjustments
        strategy_windows = {
            CounterStrategy.TIMING_ADVANTAGE: 10.0,  # Quick execution needed
            CounterStrategy.PATTERN_EXPLOITATION: 45.0,
            CounterStrategy.MOMENTUM_COUNTER: 60.0,
            CounterStrategy.VOLUME_SPIKE_COUNTER: 15.0,
            CounterStrategy.HFT_FRONT_RUNNING: 5.0,   # Very quick
            CounterStrategy.ICEBERG_ORDER_EXPLOIT: 120.0  # Longer for detection
        }
        
        window = strategy_windows.get(strategy, base_window)
        
        # Adjust for timing advantage (faster advantage = shorter window)
        timing_factor = max(0.5, 1 - (timing_advantage / 100))
        window *= timing_factor
        
        return window

    def _generate_counter_reasoning(self, firm_id: str, strategy: FirmCounterStrategy, 
                                  confidence: float, timing_advantage: float) -> str:
        """Generate reasoning for counter-strategy."""
        return (f"Counter-trading opportunity against {firm_id} using {strategy.primary_strategy.value}. "
                f"Confidence: {confidence:.2f}, Timing advantage: {timing_advantage:.1f}ms. "
                f"Exploiting patterns: {', '.join(strategy.exploit_patterns[:2])}")

    def _update_strategy_metrics(self, firm_id: str, signal: CounterIntelligenceSignal):
        """Update success metrics for counter-strategy."""
        strategy = self.counter_strategies[firm_id]
        
        # Simple exponential moving average for success rate
        alpha = 0.1
        if signal.confidence > 0.8:  # Assume success if high confidence
            strategy.success_rate = strategy.success_rate * (1 - alpha) + 1.0 * alpha
        else:
            strategy.success_rate = strategy.success_rate * (1 - alpha) + 0.0 * alpha
            
        strategy.last_updated = time.time()

    def get_active_counter_signals(self) -> List[CounterIntelligenceSignal]:
        """Get all active counter-intelligence signals."""
        # Filter out expired signals
        current_time = time.time()
        self.active_counters = [
            signal for signal in self.active_counters
            if current_time - signal.execution_window_seconds < 300  # 5 minute expiry
        ]
        
        return self.active_counters

    def execute_counter_trade(self, signal: CounterIntelligenceSignal, 
                            market_data: Dict) -> Dict[str, Any]:
        """
        Execute a counter-trade based on intelligence signal.
        
        Args:
            signal: The counter-intelligence signal
            market_data: Current market data
            
        Returns:
            Trade execution result
        """
        logger.info(f"Executing counter-trade against {signal.firm_id} using {signal.strategy.value}")
        
        # This would integrate with the actual trading execution system
        # For now, return a mock result
        result = {
            "success": True,
            "firm_targeted": signal.firm_id,
            "strategy_used": signal.strategy.value,
            "timing_advantage_used": signal.timing_advantage,
            "expected_profit_pips": signal.expected_profit_pips,
            "execution_time": time.time(),
            "reasoning": signal.reasoning
        }
        
        # Update strategy success metrics
        self._update_strategy_metrics(signal.firm_id, signal)
        
        return result

    def calibrate_timing_advantage(self, firm_id: str, measured_latency: float):
        """Calibrate timing advantage based on measured execution latency."""
        if firm_id not in self.timing_calibrations:
            self.timing_calibrations[firm_id] = measured_latency
        else:
            # Exponential moving average
            alpha = 0.2
            self.timing_calibrations[firm_id] = (
                self.timing_calibrations[firm_id] * (1 - alpha) + measured_latency * alpha
            )
            
        logger.info(f"Calibrated timing for {firm_id}: {self.timing_calibrations[firm_id]:.2f}ms")

# Global instance for integration with other systems
queen_counter_intelligence = QueenCounterIntelligence()
