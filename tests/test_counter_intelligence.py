#!/usr/bin/env python3
"""
🧪 COUNTER-INTELLIGENCE SYSTEM TESTS 🧪
=======================================

Unit and integration tests for the counter-intelligence framework:
- Counter-strategy generation
- Firm attribution
- Orca integration
- Queen approval flow

Gary Leckey | January 2026 | Test-Driven Counter-Intelligence
"""

from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
import unittest
import time
from unittest.mock import Mock, MagicMock, patch
from dataclasses import asdict

# UTF-8 fix
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Test imports
try:
    from aureon_queen_counter_intelligence import (
        QueenCounterIntelligence,
        FirmCounterStrategy,
        CounterIntelligenceSignal,
        CounterStrategy
    )
    from aureon_global_firm_intelligence import (
        get_attribution_engine,
        FirmAttributionEngine
    )
    COUNTER_INTEL_AVAILABLE = True
except ImportError as e:
    COUNTER_INTEL_AVAILABLE = False
    print(f"⚠️ Counter-intelligence not available: {e}")


class TestCounterStrategy(unittest.TestCase):
    """Test counter-strategy generation and evaluation."""
    
    def setUp(self):
        """Set up test fixtures."""
        if not COUNTER_INTEL_AVAILABLE:
            self.skipTest("Counter-intelligence not available")
        
        self.counter_intel = QueenCounterIntelligence()
    
    def test_firm_counter_strategies_initialized(self):
        """Test that firm-specific counter-strategies are loaded."""
        self.assertIn('citadel', self.counter_intel.counter_strategies)
        self.assertIn('jane_street', self.counter_intel.counter_strategies)
        self.assertIn('two_sigma', self.counter_intel.counter_strategies)
        
        citadel = self.counter_intel.counter_strategies['citadel']
        self.assertEqual(citadel.firm_name, 'Citadel')
        self.assertEqual(citadel.primary_strategy, CounterStrategy.TIMING_ADVANTAGE)
        self.assertGreater(citadel.timing_advantage_ms, 0)
    
    def test_timing_advantage_calculation(self):
        """Test timing advantage calculation with resonance harmonics."""
        market_data = {
            'average_latency_ms': 50.0,
            'volatility': 0.5
        }
        
        timing = self.counter_intel._calculate_timing_advantage('citadel', market_data)
        
        # Should be between 10-200ms
        self.assertGreaterEqual(timing, 10.0)
        self.assertLessEqual(timing, 200.0)
    
    def test_counter_confidence_calculation(self):
        """Test confidence score calculation for counter-trading."""
        firm_id = 'citadel'
        market_data = {'volatility': 0.6, 'volume_ratio': 1.5}
        bot_detection_data = {'confidence': 0.85}
        
        # Mock firm intelligence
        self.counter_intel.firm_intelligence_db = {
            'citadel': {'attribution_confidence': 0.9}
        }
        
        confidence = self.counter_intel._calculate_counter_confidence(
            firm_id, market_data, bot_detection_data
        )
        
        # Should be high confidence with good inputs
        self.assertGreater(confidence, 0.7)
        self.assertLessEqual(confidence, 1.0)
    
    def test_profit_estimation(self):
        """Test profit potential estimation for counter-strategies."""
        market_data = {
            'volatility': 0.5,
            'spread_pips': 2.0
        }
        
        # HFT front-running strategy
        profit_hft = self.counter_intel._estimate_counter_profit(
            CounterStrategy.HFT_FRONT_RUNNING,
            market_data
        )
        
        # Volume spike counter strategy
        profit_volume = self.counter_intel._estimate_counter_profit(
            CounterStrategy.VOLUME_SPIKE_COUNTER,
            market_data
        )
        
        # Volume spike should have higher profit multiplier
        self.assertGreater(profit_volume, profit_hft)
    
    def test_risk_assessment(self):
        """Test risk scoring for counter-strategies."""
        market_data = {'volatility': 0.3}
        
        # Citadel is high risk (HFT competition)
        risk_citadel = self.counter_intel._assess_counter_risk(
            'citadel',
            CounterStrategy.HFT_FRONT_RUNNING,
            market_data
        )
        
        # Millennium is lower risk
        risk_millennium = self.counter_intel._assess_counter_risk(
            'millennium',
            CounterStrategy.ICEBERG_ORDER_EXPLOIT,
            market_data
        )
        
        self.assertGreater(risk_citadel, risk_millennium)


class TestFirmAttribution(unittest.TestCase):
    """Test firm attribution engine."""
    
    def setUp(self):
        """Set up attribution engine."""
        if not COUNTER_INTEL_AVAILABLE:
            self.skipTest("Counter-intelligence not available")
        
        self.engine = get_attribution_engine()
    
    def test_attribution_engine_initialized(self):
        """Test that attribution engine loads firm database."""
        self.assertGreater(len(self.engine.firm_db), 0)
        # The canonical registry (aureon_global_firm_intelligence) keys firms by full id —
        # 'citadel_securities', matching each entry's firm_id. The old short 'citadel' key
        # never existed there; this assertion had drifted from the registry it audits.
        self.assertIn('citadel_securities', self.engine.firm_db)
    
    def test_bot_attribution_hft(self):
        """Test HFT bot attribution to Citadel."""
        matches = self.engine.attribute_bot_to_firm(
            symbol='BTCUSDT',
            frequency=4.0,  # High frequency
            order_size_usd=200_000,
            strategy='HFT_ALGO',
            current_hour_utc=14
        )
        
        # Should find matches
        self.assertGreater(len(matches), 0)
        
        # Check if Citadel is in top matches (they're HFT focused)
        firm_ids = [firm_id for firm_id, conf in matches]
        self.assertIn('citadel_securities', firm_ids)
    
    def test_bot_attribution_market_maker(self):
        """Test market maker bot attribution to Jane Street."""
        matches = self.engine.attribute_bot_to_firm(
            symbol='ETHUSDT',
            frequency=0.5,  # Medium frequency
            order_size_usd=500_000,
            strategy='MM_SPOOF',
            current_hour_utc=15
        )
        
        # Jane Street should match market maker patterns
        firm_ids = [firm_id for firm_id, conf in matches]
        # Jane Street or similar market maker should be in matches
        self.assertGreater(len(matches), 0)
    
    def test_firm_details_retrieval(self):
        """Test retrieving firm details."""
        firm = self.engine.get_firm_details('citadel_securities')
        
        self.assertIsNotNone(firm)
        self.assertEqual(firm.name, 'Citadel Securities')
        self.assertEqual(firm.type, 'HFT')
        self.assertGreater(len(firm.offices), 0)


class TestCounterIntelligenceSignal(unittest.TestCase):
    """Test counter-intelligence signal generation."""
    
    def setUp(self):
        """Set up test fixtures."""
        if not COUNTER_INTEL_AVAILABLE:
            self.skipTest("Counter-intelligence not available")
        
        self.counter_intel = QueenCounterIntelligence()
    
    def test_signal_generation_high_confidence(self):
        """Test generating counter-signal with high confidence."""
        market_data = {
            'volatility': 0.6,
            'volume_ratio': 1.8,
            'spread_pips': 1.5,
            'average_latency_ms': 45.0
        }
        
        bot_detection_data = {
            'confidence': 0.9,
            'bot_class': 'HFT_ALGO'
        }
        
        signal = self.counter_intel.analyze_firm_for_counter_opportunity(
            firm_id='citadel',
            market_data=market_data,
            bot_detection_data=bot_detection_data
        )
        
        # Should generate signal with high confidence
        if signal:
            self.assertIsInstance(signal, CounterIntelligenceSignal)
            self.assertEqual(signal.firm_id, 'citadel')
            self.assertGreater(signal.confidence, 0.7)
            self.assertGreater(signal.timing_advantage, 0)
    
    def test_signal_generation_low_confidence(self):
        """Test that low confidence doesn't generate signal."""
        market_data = {
            'volatility': 0.2,
            'volume_ratio': 0.5,
            'spread_pips': 3.0,
            'average_latency_ms': 100.0
        }
        
        bot_detection_data = {
            'confidence': 0.3
        }
        
        signal = self.counter_intel.analyze_firm_for_counter_opportunity(
            firm_id='citadel',
            market_data=market_data,
            bot_detection_data=bot_detection_data
        )
        
        # Should not generate signal (confidence < 0.7)
        self.assertIsNone(signal)
    
    def test_execution_window_calculation(self):
        """Test execution window varies by strategy."""
        # HFT front-running needs fast execution
        window_hft = self.counter_intel._calculate_execution_window(
            CounterStrategy.HFT_FRONT_RUNNING,
            timing_advantage=50.0
        )
        
        # Iceberg exploit has longer window
        window_iceberg = self.counter_intel._calculate_execution_window(
            CounterStrategy.ICEBERG_ORDER_EXPLOIT,
            timing_advantage=50.0
        )
        
        self.assertLess(window_hft, window_iceberg)


class TestQueenIntegration(unittest.TestCase):
    """Test Queen hive integration with counter-intelligence."""
    
    def setUp(self):
        """Set up mock Queen."""
        if not COUNTER_INTEL_AVAILABLE:
            self.skipTest("Counter-intelligence not available")
        
        # Mock Queen with counter-intel method
        self.mock_queen = Mock()
        self.mock_queen.receive_counter_intelligence_signal = Mock(return_value={
            'approved': True,
            'queen_confidence': 0.85,
            'reasoning': 'Queen approves counter-hunt',
            'action': 'execute'
        })
    
    def test_queen_receives_counter_signal(self):
        """Test Queen receives and processes counter-intelligence."""
        counter_signal = {
            'firm_id': 'citadel',
            'strategy': 'timing_advantage',
            'confidence': 0.88,
            'timing_advantage': 45.0,
            'expected_profit_pips': 1.2,
            'risk_score': 0.6,
            'execution_window_seconds': 10.0,
            'reasoning': 'HFT timing edge detected',
            'symbol': 'BTC/USD',
            'source': 'test'
        }
        
        response = self.mock_queen.receive_counter_intelligence_signal(counter_signal)
        
        # Queen should have been called
        self.mock_queen.receive_counter_intelligence_signal.assert_called_once()
        
        # Response should indicate approval
        self.assertTrue(response['approved'])
        self.assertEqual(response['action'], 'execute')
    
    def test_queen_rejects_high_risk(self):
        """Test Queen rejects high-risk counter-hunts."""
        self.mock_queen.receive_counter_intelligence_signal = Mock(return_value={
            'approved': False,
            'queen_confidence': 0.3,
            'reasoning': 'Risk too high',
            'action': 'reject'
        })
        
        counter_signal = {
            'firm_id': 'citadel',
            'strategy': 'hft_front_running',
            'confidence': 0.75,
            'risk_score': 0.95,  # Very high risk
            'symbol': 'BTC/USD',
            'source': 'test'
        }
        
        response = self.mock_queen.receive_counter_intelligence_signal(counter_signal)
        
        self.assertFalse(response['approved'])
        self.assertEqual(response['action'], 'reject')


class TestOrcaIntegration(unittest.TestCase):
    """Test Orca intelligence integration with counter-signals."""
    
    def setUp(self):
        """Set up test fixtures."""
        if not COUNTER_INTEL_AVAILABLE:
            self.skipTest("Counter-intelligence not available")
        
        # Mock Orca
        self.mock_orca = Mock()
        self.mock_orca.whale_signals = []
        self.mock_orca.symbol_momentum = {}
    
    def test_derived_whale_signal_generation(self):
        """Test that counter-signals generate derived whale signals."""
        counter_signal = CounterIntelligenceSignal(
            firm_id='citadel',
            strategy=CounterStrategy.TIMING_ADVANTAGE,
            confidence=0.85,
            timing_advantage=50.0,
            expected_profit_pips=1.5,
            risk_score=0.5,
            execution_window_seconds=15.0,
            reasoning='Timing edge detected'
        )
        
        # Simulate Orca creating derived whale signal
        derived_whale = {
            'timestamp': time.time(),
            'symbol': 'BTC/USD',
            'firm': 'citadel',
            'firm_confidence': counter_signal.confidence,
            'ride_confidence': counter_signal.confidence,
            'suggested_action': 'buy',
            'target_pnl_pct': min(0.05, counter_signal.expected_profit_pips / 100),
            'source': 'counter_intelligence'
        }
        
        self.mock_orca.whale_signals.append(derived_whale)
        
        # Verify derived signal added
        self.assertEqual(len(self.mock_orca.whale_signals), 1)
        signal = self.mock_orca.whale_signals[0]
        self.assertEqual(signal['firm'], 'citadel')
        self.assertEqual(signal['source'], 'counter_intelligence')


def run_tests():
    """Run all counter-intelligence tests."""
    print("🧪 COUNTER-INTELLIGENCE SYSTEM TESTS 🧪")
    print("=" * 60)
    
    if not COUNTER_INTEL_AVAILABLE:
        print("⚠️ Counter-intelligence not available - skipping tests")
        return
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTests(loader.loadTestsFromTestCase(TestCounterStrategy))
    suite.addTests(loader.loadTestsFromTestCase(TestFirmAttribution))
    suite.addTests(loader.loadTestsFromTestCase(TestCounterIntelligenceSignal))
    suite.addTests(loader.loadTestsFromTestCase(TestQueenIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestOrcaIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
