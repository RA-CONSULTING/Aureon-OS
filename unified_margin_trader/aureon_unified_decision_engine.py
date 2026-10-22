#!/usr/bin/env python3
"""
⚡ AUREON UNIFIED DECISION ENGINE - Real-Time Trading Decision Synthesis
==========================================================================

Synthesizes market data, system coordination, and intelligence feeds into
unified trading decisions. Generates buy/sell/hold signals with confidence
metrics and system readiness validation.

Features:
  - Multi-source signal aggregation
  - Confidence scoring based on system coordination
  - Decision logging and audit trail
  - ThoughtBus event publishing
  - Risk validation before decisions

Author: Aureon Trading System
Date: March 2026
"""

import asyncio
import json
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

# Import ThoughtBus for pub/sub messaging
try:
    from aureon.core.aureon_thought_bus import ThoughtBus
except ImportError:
    ThoughtBus = None

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of trading decisions."""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"  # Close existing position
    WAIT = "wait"    # Wait for better conditions


class DecisionReason(Enum):
    """Reasons for trading decisions."""
    SIGNAL_STRENGTH = "signal_strength"
    RISK_MANAGEMENT = "risk_management"
    PROFIT_TARGET = "profit_target"
    SYSTEM_READINESS = "system_readiness"
    MARKET_CONDITION = "market_condition"
    COORDINATION_FAILURE = "coordination_failure"
    WHALE_ACTIVITY = "whale_activity"
    MOMENTUM_DETECTED = "momentum_detected"
    PATTERN_MATCH = "pattern_match"


@dataclass
class SignalInput:
    """Market signal from any source."""
    source: str  # Which system generated this signal
    symbol: str  # Trading pair (BTC, ETH, etc.)
    direction: str  # "bullish" or "bearish"
    strength: float  # 0.0 to 1.0 confidence
    timestamp: float = field(default_factory=datetime.now().timestamp)
    metadata: Dict = field(default_factory=dict)


@dataclass
class CoordinationInput:
    """System coordination status."""
    orca_ready: bool
    blockers: List[str] = field(default_factory=list)
    all_systems_ready: int = 0
    total_systems: int = 0


@dataclass
class TradingDecision:
    """A trading decision with reasoning."""
    decision_id: str
    decision_type: DecisionType
    symbol: str
    timestamp: datetime
    confidence: float  # 0.0 to 1.0
    reason: DecisionReason
    signals_used: List[str] = field(default_factory=list)
    system_coordination_ok: bool = False
    risk_check_passed: bool = True
    metadata: Dict = field(default_factory=dict)
    cancel_reason: Optional[str] = None  # If decision is cancelled


class UnifiedDecisionEngine:
    """
    Synthesizes all feeds and system states into trading decisions.
    """

    def __init__(self):
        """Initialize the decision engine."""
        self.thought_bus = ThoughtBus() if ThoughtBus else None
        self.signal_buffer: Dict[str, List[SignalInput]] = {}
        self.last_decisions: Dict[str, TradingDecision] = {}
        self.decision_counter = 0
        self.coordination_state = None

        logger.info("UnifiedDecisionEngine initialized")

    def add_signal(self, signal: SignalInput):
        """
        Add a market signal to the buffer.

        Args:
            signal: SignalInput from any system
        """
        if signal.symbol not in self.signal_buffer:
            self.signal_buffer[signal.symbol] = []

        self.signal_buffer[signal.symbol].append(signal)

        # Keep only recent signals (last 100 per symbol)
        if len(self.signal_buffer[signal.symbol]) > 100:
            self.signal_buffer[signal.symbol].pop(0)

        logger.debug(f"Added signal for {signal.symbol} from {signal.source}")

    def set_coordination_state(self, coordination: CoordinationInput):
        """
        Update system coordination state.

        Args:
            coordination: Current coordination status
        """
        self.coordination_state = coordination
        logger.info(
            f"Coordination state: Orca ready={coordination.orca_ready}, "
            f"Systems {coordination.all_systems_ready}/{coordination.total_systems} ready"
        )

    def analyze_signals(self, symbol: str) -> Tuple[float, str]:
        """
        Analyze accumulated signals for a symbol.

        Returns:
            (confidence_score: float, direction: str)
        """
        if symbol not in self.signal_buffer or not self.signal_buffer[symbol]:
            return 0.5, "neutral"

        signals = self.signal_buffer[symbol]

        # Weight recent signals more heavily
        now = datetime.now().timestamp()
        weighted_bullish = 0.0
        total_weight = 0.0

        for signal in signals[-50:]:  # Use last 50 signals
            # Time decay: newer signals weighted more
            time_diff = now - signal.timestamp
            weight = max(0.1, 1.0 - (time_diff / 3600))  # Decay over 1 hour

            if signal.direction == "bullish":
                weighted_bullish += signal.strength * weight
            total_weight += weight

        if total_weight == 0:
            return 0.5, "neutral"

        confidence = weighted_bullish / total_weight
        direction = "bullish" if confidence > 0.55 else "bearish" if confidence < 0.45 else "neutral"

        return confidence, direction

    def check_risk_conditions(self, symbol: str, decision_type: DecisionType) -> Tuple[bool, str]:
        """
        Validate risk conditions before a decision.

        Returns:
            (passed: bool, reason: str)
        """
        # Risk checks
        if decision_type == DecisionType.BUY:
            # Don't buy if too bearish signals
            confidence, direction = self.analyze_signals(symbol)
            if confidence < 0.4:
                return False, "Insufficient bullish confidence for BUY"

        if decision_type == DecisionType.SELL:
            # Don't sell at worst prices
            if symbol in self.signal_buffer:
                signals = self.signal_buffer[symbol]
                recent_signals = [s for s in signals[-10:] if s.direction == "bearish"]
                if len(recent_signals) > 8:
                    return False, "Too many bearish signals - avoid selling at worst"

        return True, "Risk check passed"

    def generate_decision(
        self,
        symbol: str,
        decision_type: DecisionType,
        reason: DecisionReason
    ) -> Optional[TradingDecision]:
        """
        Generate a trading decision.

        Args:
            symbol: Trading pair
            decision_type: Type of decision
            reason: Why this decision

        Returns:
            TradingDecision or None if cancelled
        """
        self.decision_counter += 1
        decision_id = f"dec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.decision_counter}"

        # Analyze signals
        confidence, direction = self.analyze_signals(symbol)

        # Check risk conditions
        risk_ok, risk_msg = self.check_risk_conditions(symbol, decision_type)

        # Check system coordination
        coord_ok = False
        if self.coordination_state:
            coord_ok = self.coordination_state.orca_ready
        else:
            coord_ok = True  # Proceed if no coordination state available

        # Build decision
        decision = TradingDecision(
            decision_id=decision_id,
            decision_type=decision_type,
            symbol=symbol,
            timestamp=datetime.now(),
            confidence=confidence,
            reason=reason,
            signals_used=self._get_signal_sources(symbol),
            system_coordination_ok=coord_ok,
            risk_check_passed=risk_ok,
            metadata={
                "signal_direction": direction,
                "risk_message": risk_msg,
                "num_signals": len(self.signal_buffer.get(symbol, []))
            }
        )

        # Check if decision should be cancelled
        if not risk_ok:
            decision.cancel_reason = risk_msg
            logger.warning(f"Decision {decision_id} cancelled: {risk_msg}")
            return None

        if not coord_ok and decision_type == DecisionType.BUY:
            decision.cancel_reason = "System coordination not ready for execution"
            logger.warning(f"Decision {decision_id} cancelled: coordination not ready")
            return None

        # Store and publish
        self.last_decisions[symbol] = decision
        self._publish_decision(decision)

        logger.info(
            f"Decision {decision_id}: {decision_type.value} {symbol} "
            f"(confidence={confidence:.2f}, risk_ok={risk_ok})"
        )

        return decision

    def _get_signal_sources(self, symbol: str) -> List[str]:
        """Get list of sources contributing to a symbol's signals."""
        if symbol not in self.signal_buffer:
            return []

        sources = set()
        for signal in self.signal_buffer[symbol][-10:]:  # Last 10 signals
            sources.add(signal.source)

        return list(sources)

    def _publish_decision(self, decision: TradingDecision):
        """Publish decision to ThoughtBus."""
        if not self.thought_bus:
            return

        try:
            event = {
                "decision_id": decision.decision_id,
                "type": decision.decision_type.value,
                "symbol": decision.symbol,
                "timestamp": decision.timestamp.isoformat(),
                "confidence": decision.confidence,
                "reason": decision.reason.value,
                "signals_used": decision.signals_used,
                "coordination_ok": decision.system_coordination_ok,
                "risk_ok": decision.risk_check_passed,
                "metadata": decision.metadata
            }
            self.thought_bus.publish("decisions.trading", event)
        except Exception as e:
            logger.error(f"Failed to publish decision: {e}")

    def get_latest_decision(self, symbol: str) -> Optional[TradingDecision]:
        """Get the latest decision for a symbol."""
        return self.last_decisions.get(symbol)

    def get_all_decisions(self) -> Dict[str, TradingDecision]:
        """Get all latest decisions by symbol."""
        return self.last_decisions.copy()

    async def monitor_decisions(self, interval: float = 1.0):
        """
        Continuously monitor and publish decision state.

        Args:
            interval: Update interval in seconds
        """
        logger.info("Starting decision monitoring")

        try:
            while True:
                # Publish current decisions
                if self.thought_bus:
                    state = {
                        "timestamp": datetime.now().isoformat(),
                        "active_decisions": len(self.last_decisions),
                        "by_symbol": {
                            symbol: {
                                "type": dec.decision_type.value,
                                "confidence": dec.confidence,
                                "reason": dec.reason.value
                            }
                            for symbol, dec in self.last_decisions.items()
                        }
                    }
                    self.thought_bus.publish("decisions.monitor", state)

                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Decision monitoring stopped")
        except Exception as e:
            logger.error(f"Error in decision monitoring: {e}")


async def main():
    """Test the decision engine."""
    engine = UnifiedDecisionEngine()

    # Simulate some signals
    signals = [
        SignalInput("seer_oracle", "BTC", "bullish", 0.8),
        SignalInput("momentum_scanner", "BTC", "bullish", 0.75),
        SignalInput("pattern_matcher", "BTC", "bullish", 0.7),
    ]

    for signal in signals:
        engine.add_signal(signal)

    # Simulate coordination state
    coordination = CoordinationInput(orca_ready=True, all_systems_ready=10, total_systems=12)
    engine.set_coordination_state(coordination)

    # Generate a decision
    decision = engine.generate_decision(
        "BTC",
        DecisionType.BUY,
        DecisionReason.SIGNAL_STRENGTH
    )

    if decision:
        print(f"\n✅ Decision Generated:")
        print(f"   ID: {decision.decision_id}")
        print(f"   Type: {decision.decision_type.value}")
        print(f"   Symbol: {decision.symbol}")
        print(f"   Confidence: {decision.confidence:.2f}")
        print(f"   Risk OK: {decision.risk_check_passed}")


if __name__ == "__main__":
    asyncio.run(main())
