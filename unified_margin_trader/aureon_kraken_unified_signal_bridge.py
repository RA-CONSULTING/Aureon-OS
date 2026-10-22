#!/usr/bin/env python3
"""
🔗 AUREON KRAKEN UNIFIED SIGNAL BRIDGE
═══════════════════════════════════════════════════════════════════════════

UNIFIED INTEGRATION LAYER - Connects Kraken Trade Analysis to Seer, Lyra, & Queens

ARCHITECTURE:
  Kraken Trades Analysis → Signal Bridge → Decision Engine
                         ↓
                    ┌─────────────┬─────────────┬──────────────┐
                    ↓             ↓             ↓              ↓
                  SEER          LYRA         QUEEN         FILTER
              (Cosmic)      (Harmonic)     (Execution)    (Validation)
                    ↓             ↓             ↓              ↓
                    └─────────────┴─────────────┴──────────────┘
                              ↓
                     UNIFIED DECISION
                    (Geopolitical Context)

PURPOSE:
1. Bridge Kraken trade analysis signals to unified system
2. Ensure signal coherence across all pillars
3. Apply geopolitical context filtering
4. Validate position sizing and fee efficiency
5. Generate confidence-weighted buy/sell signals

FEATURES:
  ✅ Fee-based signal quality (lower fees = stronger signal)
  ✅ Position sizing validation (larger = more conviction)
  ✅ Geopolitical volatility adjustment
  ✅ Multi-pillar consensus requirements
  ✅ Signal strength aggregation
  ✅ Cross-system filtering

Author: Aureon Trading System
Date: March 23, 2026
Status: INTEGRATING KRAKEN ANALYSIS INTO UNIFIED ECOSYSTEM
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from enum import Enum

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [KrakenBridge] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal types from Kraken trade analysis."""
    EFFICIENT_EXECUTION = "efficient_execution"
    GOOD_EXECUTION = "good_execution"
    CAUTION_FEES = "caution_fees"
    AVOID_PATTERN = "avoid_pattern"


class TradeSignalStrength(Enum):
    """Signal strength based on Kraken trade quality."""
    STRONG = 0.85      # Excellent execution
    MEDIUM = 0.65      # Good execution
    WEAK = 0.40        # Caution needed
    REJECT = 0.10      # Avoid pattern


@dataclass
class KrakenTradeSignal:
    """Signal generated from Kraken trade analysis."""
    pair: str
    signal_type: SignalType
    base_strength: float  # 0-1 from Kraken analysis
    fee_ratio: float
    position_size: float
    recommendation: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "pair": self.pair,
            "signal_type": self.signal_type.value,
            "base_strength": self.base_strength,
            "fee_ratio": self.fee_ratio,
            "position_size": self.position_size,
            "recommendation": self.recommendation,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


@dataclass
class UnifiedDecisionSignal:
    """Final unified signal for decision engine."""
    pair: str
    direction: str  # "bullish", "bearish", or "neutral"
    strength: float  # 0-1 aggregated confidence
    sources: List[str]  # Which systems contributed
    seer_alignment: float  # 0-1 Seer coherence
    lyra_alignment: float  # 0-1 Lyra harmony
    queen_readiness: float  # 0-1 Queens execution readiness
    geopolitical_factor: float  # 0-1 volatility adjustment
    filters_passed: Dict[str, bool] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class KrakenUnifiedSignalBridge:
    """Bridge Kraken trade analysis into unified Aureon decision system."""

    def __init__(self):
        """Initialize the signal bridge."""
        self.logger = logger
        self.signal_history = []
        self.decision_history = []

    def parse_kraken_trade_analysis(
        self,
        trade_data: Dict[str, Any]
    ) -> KrakenTradeSignal:
        """
        Convert Kraken trade analysis to unified signal.

        Args:
            trade_data: Dict with keys: pair, signal_type, fee_ratio,
                       position_size, recommendation, decision_quality

        Returns:
            KrakenTradeSignal with calculated strength
        """
        pair = trade_data.get("pair", "UNKNOWN")
        recommendation = trade_data.get("recommendation", "UNKNOWN")
        fee_ratio = trade_data.get("fee_ratio", 0.0)
        position_size = trade_data.get("position_size", 0.0)
        decision_quality = trade_data.get("decision_quality", 0.0)

        # Map recommendation to signal type
        signal_type = self._map_recommendation_to_signal_type(recommendation)

        # Calculate base strength from Kraken analysis
        base_strength = self._calculate_base_strength(
            decision_quality=decision_quality,
            fee_ratio=fee_ratio,
            position_size=position_size
        )

        signal = KrakenTradeSignal(
            pair=pair,
            signal_type=signal_type,
            base_strength=base_strength,
            fee_ratio=fee_ratio,
            position_size=position_size,
            recommendation=recommendation,
            metadata={
                "decision_quality": decision_quality,
                "kraken_source": "closed_trades_history"
            }
        )

        self.logger.info(f"Parsed Kraken signal: {pair} {signal_type.value} "
                        f"(strength: {base_strength:.1%})")
        return signal

    def _map_recommendation_to_signal_type(self, recommendation: str) -> SignalType:
        """Map Kraken recommendation to signal type."""
        if "EFFICIENT" in recommendation:
            return SignalType.EFFICIENT_EXECUTION
        elif "GOOD" in recommendation:
            return SignalType.GOOD_EXECUTION
        elif "CAUTION" in recommendation:
            return SignalType.CAUTION_FEES
        else:
            return SignalType.AVOID_PATTERN

    def _calculate_base_strength(
        self,
        decision_quality: float,
        fee_ratio: float,
        position_size: float
    ) -> float:
        """
        Calculate base signal strength.

        Factors:
          - Decision quality (0-1)
          - Fee efficiency (lower = higher)
          - Position sizing (larger = higher)
        """
        # Fee efficiency component (0-1)
        fee_efficiency = max(0.1, 1.0 - (fee_ratio / 1.0))

        # Position sizing component (larger = more conviction)
        if position_size > 500:
            size_factor = 0.9
        elif position_size > 200:
            size_factor = 0.7
        elif position_size > 100:
            size_factor = 0.5
        else:
            size_factor = 0.3

        # Aggregate
        strength = (decision_quality * 0.5 + fee_efficiency * 0.3 + size_factor * 0.2)
        return min(1.0, max(0.0, strength))

    def apply_seer_alignment(
        self,
        signal: KrakenTradeSignal,
        seer_coherence: float
    ) -> float:
        """
        Apply Seer (cosmic/harmonic) alignment adjustment.

        If Seer reports DIVINE_CLARITY (0.85+): boost signal
        If Seer reports FOG/BLIND (<0.55): reduce signal
        """
        if seer_coherence >= 0.85:
            # Divine clarity - boost signal
            adjustment = 1.15
        elif seer_coherence >= 0.70:
            # Clear sight - modest boost
            adjustment = 1.05
        elif seer_coherence >= 0.55:
            # Partial vision - neutral
            adjustment = 1.0
        elif seer_coherence >= 0.40:
            # Fog - reduce signal
            adjustment = 0.70
        else:
            # Blind - reject signal
            adjustment = 0.20

        adjusted_strength = signal.base_strength * adjustment
        self.logger.info(f"Seer alignment applied: {seer_coherence:.1%} "
                        f"→ adjustment {adjustment:.2f}x → {adjusted_strength:.1%}")
        return min(1.0, adjusted_strength)

    def apply_lyra_harmony(
        self,
        signal: KrakenTradeSignal,
        lyra_resonance: float
    ) -> float:
        """
        Apply Lyra (emotional/frequency) alignment adjustment.

        If Lyra reports DIVINE_HARMONY (0.85+): boost signal
        If Lyra reports SILENCE (<0.55): reduce signal
        """
        if lyra_resonance >= 0.85:
            # Perfect harmony - boost
            adjustment = 1.15
        elif lyra_resonance >= 0.70:
            # Clear resonance - boost
            adjustment = 1.05
        elif lyra_resonance >= 0.55:
            # Partial harmony - neutral
            adjustment = 1.0
        elif lyra_resonance >= 0.40:
            # Dissonance - reduce
            adjustment = 0.70
        else:
            # Silence - reject
            adjustment = 0.20

        adjusted_strength = signal.base_strength * adjustment
        self.logger.info(f"Lyra harmony applied: {lyra_resonance:.1%} "
                        f"→ adjustment {adjustment:.2f}x → {adjusted_strength:.1%}")
        return min(1.0, adjusted_strength)

    def apply_geopolitical_filter(
        self,
        signal: KrakenTradeSignal,
        volatility_index: float = 0.5,
        market_stress: float = 0.3
    ) -> Tuple[float, float]:
        """
        Apply geopolitical volatility context (March 2026 tensions).

        Given:
        - US-Iran-Israel tensions
        - Bitcoin down 3-5% this month
        - Kraken API experiencing 503 overload
        - Institutional investors buying the dip

        Logic:
        - High volatility (0.7+): Require larger positions, lower fees
        - Normal volatility (0.4-0.7): Standard thresholds
        - Low volatility (<0.4): Can accept smaller positions
        """
        position_check = True
        fee_check = True

        if volatility_index >= 0.7:  # High volatility
            # During stress: require strong signals
            if signal.position_size < 100:
                position_check = False
            if signal.fee_ratio > 0.3:
                fee_check = False
            confidence_factor = 0.8  # Reduce confidence in volatile markets
        elif volatility_index >= 0.4:  # Normal volatility
            # Standard checks
            confidence_factor = 1.0
        else:  # Low volatility
            # More lenient during calm markets
            confidence_factor = 1.1

        both_pass = position_check and fee_check
        self.logger.info(f"Geopolitical filter: volatility={volatility_index:.1%}, "
                        f"position_ok={position_check}, fee_ok={fee_check}, "
                        f"confidence_factor={confidence_factor:.2f}x")

        return confidence_factor, both_pass

    def synthesize_unified_decision(
        self,
        kraken_signal: KrakenTradeSignal,
        seer_coherence: float = 0.65,
        lyra_resonance: float = 0.65,
        queen_readiness: float = 0.80,
        volatility_index: float = 0.5,
        require_consensus: bool = True
    ) -> Optional[UnifiedDecisionSignal]:
        """
        Synthesize final unified decision signal.

        Requires alignment from all three pillars:
        1. Kraken (trade analysis - fee & position size)
        2. Seer (cosmic/harmonic coherence)
        3. Lyra (emotional/frequency harmony)

        Plus Queen readiness for execution.
        """
        # Calculate adjusted strengths
        seer_adjusted = self.apply_seer_alignment(kraken_signal, seer_coherence)
        lyra_adjusted = self.apply_lyra_harmony(kraken_signal, lyra_resonance)
        geo_factor, geo_pass = self.apply_geopolitical_filter(
            kraken_signal,
            volatility_index=volatility_index
        )

        # Aggregate strength with geopolitical adjustment
        aggregated_strength = (
            seer_adjusted * 0.35 +      # Seer weight
            lyra_adjusted * 0.35 +      # Lyra weight
            kraken_signal.base_strength * 0.30  # Kraken weight
        )
        aggregated_strength *= geo_factor

        # Determine direction
        if aggregated_strength >= 0.70:
            direction = "bullish"
        elif aggregated_strength >= 0.55:
            direction = "neutral"
        elif aggregated_strength >= 0.40:
            direction = "neutral"
        else:
            direction = "bearish"

        # Check consensus if required
        if require_consensus:
            pillar_alignment = (seer_coherence + lyra_resonance) / 2
            if pillar_alignment < 0.55:
                self.logger.warning(f"Insufficient consensus: Seer={seer_coherence:.1%}, "
                                  f"Lyra={lyra_resonance:.1%}")
                return None

        # Check geopolitical filter
        if not geo_pass:
            self.logger.warning(f"Failed geopolitical filter during volatility "
                              f"{volatility_index:.1%}")
            return None

        # Create unified signal
        decision = UnifiedDecisionSignal(
            pair=kraken_signal.pair,
            direction=direction,
            strength=aggregated_strength,
            sources=["kraken_trades", "seer", "lyra", "queen"],
            seer_alignment=seer_coherence,
            lyra_alignment=lyra_resonance,
            queen_readiness=queen_readiness,
            geopolitical_factor=geo_factor,
            filters_passed={
                "seer_consensus": seer_coherence >= 0.55,
                "lyra_consensus": lyra_resonance >= 0.55,
                "geopolitical": geo_pass,
                "queen_ready": queen_readiness >= 0.70,
                "fee_efficient": kraken_signal.fee_ratio < 0.5,
                "position_sized": kraken_signal.position_size >= 50
            }
        )

        self.logger.info(
            f"✅ Unified Decision: {kraken_signal.pair} {direction.upper()} "
            f"(strength: {aggregated_strength:.1%}, "
            f"seer: {seer_coherence:.1%}, lyra: {lyra_resonance:.1%})"
        )

        self.decision_history.append(decision)
        return decision

    def filter_signals_for_execution(
        self,
        signals: List[UnifiedDecisionSignal],
        min_strength: float = 0.65,
        require_all_filters: bool = True
    ) -> List[UnifiedDecisionSignal]:
        """
        Filter signals for execution.

        Only signals that pass all filters and meet minimum strength
        are recommended for execution.
        """
        filtered = []

        for signal in signals:
            # Check strength threshold
            if signal.strength < min_strength:
                self.logger.debug(f"Filtered {signal.pair}: strength {signal.strength:.1%} "
                                f"< {min_strength:.1%}")
                continue

            # Check filters
            if require_all_filters:
                if not all(signal.filters_passed.values()):
                    failed = [k for k, v in signal.filters_passed.items() if not v]
                    self.logger.debug(f"Filtered {signal.pair}: failed {failed}")
                    continue

            filtered.append(signal)
            self.logger.info(f"✅ Signal approved for execution: {signal.pair}")

        return filtered

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive signal bridge report."""
        return {
            "timestamp": datetime.now().isoformat(),
            "total_signals_processed": len(self.signal_history),
            "total_decisions_generated": len(self.decision_history),
            "recent_decisions": [d.to_dict() for d in self.decision_history[-10:]],
            "system_status": {
                "kraken_bridge": "operational",
                "seer_integration": "ready",
                "lyra_integration": "ready",
                "queen_integration": "ready",
                "geopolitical_filtering": "active"
            }
        }


def example_usage():
    """Example of using the signal bridge."""
    bridge = KrakenUnifiedSignalBridge()

    # Example Kraken trade analysis result
    kraken_trade = {
        "pair": "USDTZUSD",
        "recommendation": "EFFICIENT_EXECUTION",
        "fee_ratio": 0.12,
        "position_size": 145.63,
        "decision_quality": 0.74
    }

    # Parse into signal
    signal = bridge.parse_kraken_trade_analysis(kraken_trade)

    # Synthesize with other pillars
    # Simulating: Seer sees clear harmony, Lyra in harmony, Queens ready
    decision = bridge.synthesize_unified_decision(
        signal,
        seer_coherence=0.78,      # Clear sight
        lyra_resonance=0.81,      # Clear resonance
        queen_readiness=0.85,     # Ready for execution
        volatility_index=0.60     # Moderate volatility (March tensions)
    )

    if decision:
        print(f"\n✅ UNIFIED DECISION GENERATED")
        print(f"Pair: {decision.pair}")
        print(f"Direction: {decision.direction}")
        print(f"Strength: {decision.strength:.1%}")
        print(f"Filters: {decision.filters_passed}")
    else:
        print("\n❌ Signal rejected during synthesis")

    return bridge


if __name__ == "__main__":
    bridge = example_usage()
    report = bridge.generate_report()
    print("\nBridge Report:")
    print(json.dumps(report, indent=2, default=str))
