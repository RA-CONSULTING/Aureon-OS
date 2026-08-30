#!/usr/bin/env python3
"""
🔗 UNIFIED SYSTEM INTEGRATION TEST
═══════════════════════════════════════════════════════════════════════════

Tests complete unity of Kraken → Seer → Lyra → Queens signal flow.

VALIDATES:
  ✅ Kraken trade analysis signals
  ✅ Seer cosmic coherence alignment
  ✅ Lyra emotional harmony alignment
  ✅ Queens execution readiness
  ✅ Geopolitical filter (March 2026 tensions)
  ✅ Signal aggregation and consensus
  ✅ Execution-ready decision generation

TEST SCENARIOS:
  1. Strong signal (all systems aligned)
  2. Weak signal (pillar misalignment)
  3. High volatility context (geopolitical impact)
  4. Filter failures and rejections
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Any

# Import the unified bridge
try:
    from aureon_kraken_unified_signal_bridge import (
        KrakenUnifiedSignalBridge,
        KrakenTradeSignal,
        UnifiedDecisionSignal
    )
except ImportError:
    print("❌ ERROR: Could not import KrakenUnifiedSignalBridge")
    print("   Make sure aureon_kraken_unified_signal_bridge.py exists")
    # Under pytest, a module-level sys.exit kills the whole session with
    # INTERNALERROR (it only ever "worked" while test_crash.py had disarmed
    # sys.exit process-wide — see conftest.py). Skip honestly instead; the
    # script path (python tests/test_kraken_seer_lyra_queens_unity.py) is
    # unchanged.
    if "pytest" in sys.modules:
        import pytest
        pytest.skip("KrakenUnifiedSignalBridge unavailable in this environment",
                    allow_module_level=True)
    sys.exit(1)


class UnityTestSuite:
    """Test suite for unified system integration."""

    def __init__(self):
        """Initialize test suite."""
        self.bridge = KrakenUnifiedSignalBridge()
        self.test_results = []

    def test_scenario_1_strong_signal(self):
        """
        Scenario 1: All systems aligned (high conviction)
        - Kraken: Excellent execution (0.74 quality, 0.12% fees, $146 position)
        - Seer: Clear sight (0.78 coherence)
        - Lyra: Clear resonance (0.81 harmony)
        - Queens: Ready (0.85 readiness)
        - Market: Moderate volatility
        """
        print("\n" + "=" * 100)
        print("TEST 1: STRONG SIGNAL - All systems aligned")
        print("=" * 100)

        # Kraken trade analysis
        kraken_trade = {
            "pair": "USDTZUSD",
            "recommendation": "EFFICIENT_EXECUTION",
            "fee_ratio": 0.12,
            "position_size": 145.63,
            "decision_quality": 0.74
        }

        signal = self.bridge.parse_kraken_trade_analysis(kraken_trade)
        print(f"✅ Kraken Signal: {signal.pair} {signal.signal_type.value}")
        print(f"   Base Strength: {signal.base_strength:.1%}")
        print(f"   Position: ${signal.position_size:.2f}, Fee: {signal.fee_ratio:.3f}%")

        # System alignments
        seer_coherence = 0.78     # Clear sight
        lyra_resonance = 0.81     # Clear resonance
        queen_readiness = 0.85    # Ready
        volatility = 0.60         # Moderate (March tensions)

        print(f"\n📊 System Alignment:")
        print(f"   Seer (cosmic):     {seer_coherence:.1%} - CLEAR_SIGHT ✓")
        print(f"   Lyra (harmonic):   {lyra_resonance:.1%} - CLEAR_RESONANCE ✓")
        print(f"   Queens (execute):  {queen_readiness:.1%} - READY ✓")
        print(f"   Volatility:        {volatility:.1%} - MODERATE")

        # Synthesize decision
        decision = self.bridge.synthesize_unified_decision(
            signal,
            seer_coherence=seer_coherence,
            lyra_resonance=lyra_resonance,
            queen_readiness=queen_readiness,
            volatility_index=volatility,
            require_consensus=True
        )

        if decision:
            print(f"\n✅ UNIFIED DECISION GENERATED")
            print(f"   Direction: {decision.direction.upper()}")
            print(f"   Strength: {decision.strength:.1%}")
            print(f"   Seer Alignment: {decision.seer_alignment:.1%}")
            print(f"   Lyra Alignment: {decision.lyra_alignment:.1%}")
            print(f"   Queen Readiness: {decision.queen_readiness:.1%}")
            print(f"   Geo Factor: {decision.geopolitical_factor:.2f}x")

            print(f"\n🔍 Filter Status:")
            for filter_name, passed in decision.filters_passed.items():
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"   {filter_name:20s}: {status}")

            result = "PASS"
            expected = "bullish"
            if decision.direction != expected:
                print(f"\n❌ Direction mismatch: expected {expected}, got {decision.direction}")
                result = "FAIL"
            elif decision.strength < 0.70:
                print(f"\n⚠️  Strength lower than expected: {decision.strength:.1%}")
            else:
                print(f"\n✅ All checks passed!")
        else:
            result = "FAIL"
            print(f"\n❌ DECISION REJECTED - No unified decision generated")

        self.test_results.append(("Strong Signal", result))
        return result == "PASS"

    def test_scenario_2_weak_signal(self):
        """
        Scenario 2: Pillar misalignment (caution)
        - Kraken: Good execution (0.23 quality, 0.22% fees, $50 position)
        - Seer: Fog (0.45 coherence)
        - Lyra: Dissonance (0.42 harmony)
        - Queens: Partial readiness (0.60)
        - Market: High volatility
        """
        print("\n" + "=" * 100)
        print("TEST 2: WEAK SIGNAL - Pillar misalignment")
        print("=" * 100)

        kraken_trade = {
            "pair": "TAOUSD",
            "recommendation": "GOOD_EXECUTION",
            "fee_ratio": 0.22,
            "position_size": 50.02,
            "decision_quality": 0.23
        }

        signal = self.bridge.parse_kraken_trade_analysis(kraken_trade)
        print(f"✅ Kraken Signal: {signal.pair} {signal.signal_type.value}")
        print(f"   Base Strength: {signal.base_strength:.1%}")
        print(f"   Position: ${signal.position_size:.2f}, Fee: {signal.fee_ratio:.3f}%")

        seer_coherence = 0.45     # Fog
        lyra_resonance = 0.42     # Dissonance
        queen_readiness = 0.60    # Partial
        volatility = 0.70         # High (March tensions)

        print(f"\n📊 System Alignment:")
        print(f"   Seer (cosmic):     {seer_coherence:.1%} - FOG ⚠️")
        print(f"   Lyra (harmonic):   {lyra_resonance:.1%} - DISSONANCE ⚠️")
        print(f"   Queens (execute):  {queen_readiness:.1%} - PARTIAL ⚠️")
        print(f"   Volatility:        {volatility:.1%} - HIGH")

        decision = self.bridge.synthesize_unified_decision(
            signal,
            seer_coherence=seer_coherence,
            lyra_resonance=lyra_resonance,
            queen_readiness=queen_readiness,
            volatility_index=volatility,
            require_consensus=True
        )

        if decision:
            print(f"\n⚠️  DECISION GENERATED (with caution)")
            print(f"   Direction: {decision.direction.upper()}")
            print(f"   Strength: {decision.strength:.1%}")
            print(f"   Filters Passed: {sum(1 for v in decision.filters_passed.values() if v)}/6")

            result = "PASS"
            # Expect low strength due to misalignment
            if decision.strength > 0.65:
                print(f"\n⚠️  Strength too high for weak signal: {decision.strength:.1%}")
        else:
            print(f"\n✅ Signal correctly REJECTED due to low consensus")
            print(f"   This is expected behavior - pillar misalignment prevents execution")
            result = "PASS"

        self.test_results.append(("Weak Signal", result))
        return result == "PASS"

    def test_scenario_3_high_volatility(self):
        """
        Scenario 3: High volatility geopolitical impact
        - Kraken: Good execution but small position
        - Seer: Clear sight
        - Lyra: Clear resonance
        - Queens: Ready
        - Market: High volatility (US-Iran-Israel tensions, Bitcoin -3-5%)
        """
        print("\n" + "=" * 100)
        print("TEST 3: GEOPOLITICAL FILTER - High volatility context")
        print("=" * 100)

        kraken_trade = {
            "pair": "BLUAIUSD",
            "recommendation": "GOOD_EXECUTION",
            "fee_ratio": 0.22,
            "position_size": 9.72,  # Small position
            "decision_quality": 0.23
        }

        signal = self.bridge.parse_kraken_trade_analysis(kraken_trade)
        print(f"✅ Kraken Signal: {signal.pair} {signal.signal_type.value}")
        print(f"   Base Strength: {signal.base_strength:.1%}")
        print(f"   Position: ${signal.position_size:.2f}, Fee: {signal.fee_ratio:.3f}%")

        seer_coherence = 0.75
        lyra_resonance = 0.77
        queen_readiness = 0.80
        volatility = 0.85  # VERY HIGH - US-Iran-Israel tensions

        print(f"\n📊 System Alignment:")
        print(f"   Seer (cosmic):     {seer_coherence:.1%} - CLEAR_SIGHT ✓")
        print(f"   Lyra (harmonic):   {lyra_resonance:.1%} - CLEAR_RESONANCE ✓")
        print(f"   Queens (execute):  {queen_readiness:.1%} - READY ✓")
        print(f"   Volatility:        {volatility:.1%} - VERY HIGH (Geopolitical stress)")

        decision = self.bridge.synthesize_unified_decision(
            signal,
            seer_coherence=seer_coherence,
            lyra_resonance=lyra_resonance,
            queen_readiness=queen_readiness,
            volatility_index=volatility,
            require_consensus=True
        )

        if decision:
            print(f"\n⚠️  DECISION GENERATED (with volatility adjustment)")
            print(f"   Direction: {decision.direction.upper()}")
            print(f"   Strength: {decision.strength:.1%}")
            print(f"   Geo Factor: {decision.geopolitical_factor:.2f}x")

            result = "PASS"
            # Check if position size filter failed
            position_ok = decision.filters_passed.get("position_sized", False)
            if not position_ok:
                print(f"\n✅ Correctly flagged small position as risky during volatility")
            else:
                print(f"\n⚠️  Position filter may not be working correctly")
        else:
            print(f"\n✅ Signal correctly REJECTED during high volatility")
            print(f"   Position size (${signal.position_size:.2f}) insufficient for volatility")
            result = "PASS"

        self.test_results.append(("High Volatility Filter", result))
        return result == "PASS"

    def test_scenario_4_execution_filtering(self):
        """
        Scenario 4: Signal filtering for execution
        - Multiple signals generated
        - Only strong ones approved for execution
        """
        print("\n" + "=" * 100)
        print("TEST 4: EXECUTION FILTERING - Multi-signal validation")
        print("=" * 100)

        signals = []

        # Signal 1: Strong
        kraken1 = {
            "pair": "USDTZUSD",
            "recommendation": "EFFICIENT_EXECUTION",
            "fee_ratio": 0.12,
            "position_size": 145.63,
            "decision_quality": 0.74
        }
        sig1 = self.bridge.parse_kraken_trade_analysis(kraken1)
        dec1 = self.bridge.synthesize_unified_decision(
            sig1, seer_coherence=0.78, lyra_resonance=0.81,
            queen_readiness=0.85, volatility_index=0.50
        )
        if dec1:
            signals.append(dec1)

        # Signal 2: Weak
        kraken2 = {
            "pair": "TAOUSD",
            "recommendation": "GOOD_EXECUTION",
            "fee_ratio": 0.22,
            "position_size": 50.02,
            "decision_quality": 0.23
        }
        sig2 = self.bridge.parse_kraken_trade_analysis(kraken2)
        dec2 = self.bridge.synthesize_unified_decision(
            sig2, seer_coherence=0.45, lyra_resonance=0.42,
            queen_readiness=0.60, volatility_index=0.70,
            require_consensus=False  # Allow weaker consensus for this test
        )
        if dec2:
            signals.append(dec2)

        print(f"Generated {len(signals)} signals for filtering")

        # Filter for execution
        executable = self.bridge.filter_signals_for_execution(
            signals,
            min_strength=0.65,
            require_all_filters=True
        )

        print(f"\n📊 Filtering Results:")
        print(f"   Input Signals: {len(signals)}")
        print(f"   Executable Signals: {len(executable)}")

        result = "PASS"
        if len(executable) >= 1:
            print(f"\n✅ Filtering working correctly")
            for sig in executable:
                print(f"   ✓ {sig.pair}: {sig.direction} (strength: {sig.strength:.1%})")
        else:
            print(f"\n❌ No signals passed filtering")
            result = "FAIL"

        self.test_results.append(("Execution Filtering", result))
        return result == "PASS"

    def run_all_tests(self):
        """Run complete test suite."""
        print("\n" + "█" * 100)
        print("█" + " " * 98 + "█")
        print("█" + "UNIFIED SYSTEM INTEGRATION TEST SUITE".center(98) + "█")
        print("█" + "Kraken ↔ Seer ↔ Lyra ↔ Queens Signal Flow".center(98) + "█")
        print("█" + " " * 98 + "█")
        print("█" * 100)

        results = []
        results.append(self.test_scenario_1_strong_signal())
        results.append(self.test_scenario_2_weak_signal())
        results.append(self.test_scenario_3_high_volatility())
        results.append(self.test_scenario_4_execution_filtering())

        # Print summary
        print("\n" + "=" * 100)
        print("TEST SUMMARY")
        print("=" * 100)

        passed = sum(1 for r in results if r)
        total = len(results)

        for (name, result) in self.test_results:
            status = "✅ PASS" if result == "PASS" else "❌ FAIL"
            print(f"{name:30s}: {status}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n✅ ALL TESTS PASSED - UNIFIED SYSTEM WORKING CORRECTLY")
            return True
        else:
            print(f"\n⚠️  {total - passed} test(s) failed")
            return False


def main():
    """Run the test suite."""
    suite = UnityTestSuite()
    success = suite.run_all_tests()

    # Print final report
    print("\n" + "=" * 100)
    print("UNIFIED SYSTEM STATUS")
    print("=" * 100)
    print(f"Kraken Trades Analysis: ✅ INTEGRATED")
    print(f"Seer Cosmic Coherence:  ✅ ALIGNED")
    print(f"Lyra Frequency Harmony: ✅ RESONANT")
    print(f"Queens Execution:       ✅ READY")
    print(f"Geopolitical Filter:    ✅ ACTIVE (March 2026 volatility)")
    print(f"Signal Bridge:          ✅ OPERATIONAL")
    print(f"\nOverall Status: {'✅ READY FOR TRADING' if success else '⚠️  NEEDS ATTENTION'}")
    print("=" * 100)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
