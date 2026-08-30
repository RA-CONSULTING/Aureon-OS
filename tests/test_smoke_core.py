from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import unittest
import sys
import os
import time
import logging
from unittest.mock import MagicMock, patch

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logging.getLogger().setLevel(logging.ERROR)

class TestSmokeCore(unittest.TestCase):
    
    def setUp(self):
        # Mock ThoughtBus to avoid connection attempts
        self.thought_bus_patcher = patch('aureon_thought_bus.ThoughtBus')
        self.mock_thought_bus = self.thought_bus_patcher.start()
        
    def tearDown(self):
        self.thought_bus_patcher.stop()

    def test_quantum_mirror_scanner_sanity(self):
        """QuantumMirrorScanner() → check compute_branch_score / is_ready_for_execution."""
        from aureon_quantum_mirror_scanner import QuantumMirrorScanner, RealityBranch, BranchPhase
        
        scanner = QuantumMirrorScanner()
        self.assertIsNotNone(scanner)
        
        # Test branch logic manually
        branch = RealityBranch(
            branch_id="test_branch",
            symbol="BTC/USD",
            exchange="kraken",
            p1_harmonic=0.8,
            p2_coherence=0.9,
            p3_stability=0.7,
            beneficial_probability=0.8,
            lambda_stability=0.9
        )
        # Force coherence score update
        branch.compute_coherence()
        
        # S = avg(p) * P * C * Lambda
        # avg(0.8, 0.9, 0.7) = 0.8
        # coherence = 1 - (0.9 - 0.7) = 0.8
        # S = 0.8 * 0.8 * 0.8 * 0.9 = 0.4608
        score = branch.compute_branch_score()
        self.assertAlmostEqual(score, 0.4608, places=4)
        
        # Check not ready (threshold usually 0.618)
        self.assertFalse(branch.is_ready_for_execution())
        
        # Make it ready
        branch.branch_phase = BranchPhase.VALIDATED_P3
        branch.p1_harmonic = 0.95
        branch.p2_coherence = 0.95
        branch.p3_stability = 0.95
        branch.beneficial_probability = 0.99
        branch.lambda_stability = 0.99
        branch.compute_coherence() # 1.0
        # Score = 0.95 * 0.99 * 1.0 * 0.99 = 0.931
        
        self.assertTrue(branch.is_ready_for_execution())

    def test_timeline_oracle_instantiation(self):
        """TimelineOracle() → check instantiation and basic structure."""
        with patch('aureon_timeline_oracle.MinerBrain', MagicMock()), \
             patch('aureon_timeline_oracle.QuantumPrism', MagicMock()), \
             patch('aureon_timeline_oracle.MyceliumNetwork', MagicMock()):
            
            from aureon_timeline_oracle import TimelineOracle
            oracle = TimelineOracle()
            self.assertIsNotNone(oracle)
            
            # Basic validation of structures
            self.assertIsInstance(oracle.active_branches, dict)
            self.assertIsInstance(oracle.validated_branches, list)

    def test_queen_hive_mind_basic(self):
        """QueenHiveMind() basic instantiation."""
        with patch('aureon_queen_hive_mind.QueenNeuron', MagicMock()), \
             patch('aureon_queen_hive_mind.ElephantMemory', MagicMock()), \
             patch('aureon_queen_hive_mind.QueenLossLearningSystem', MagicMock()):
             
            from aureon_queen_hive_mind import QueenHiveMind
            queen = QueenHiveMind(initial_capital=1000.0)
            self.assertIsNotNone(queen)
            self.assertEqual(queen.initial_capital, 1000.0)

    def test_conversion_commando_scanner(self):
        """ConversionCommando.PairScanner().get_top_momentum_targets() returns expected shape."""
        from aureon_conversion_commando import PairScanner

        observed_at = time.time() - 0.01

        def receipt(symbol, price, change24h, volume):
            normalized = symbol.replace("/", "")
            return {
                "symbol": symbol,
                "exchange": "kraken",
                "price": price,
                "change24h": change24h,
                "volume": volume,
                "source_id": f"kraken:{normalized}:24h",
                "source_timestamp": observed_at,
                "received_at": time.time(),
                "receipt_id": f"ticker:{normalized}:{observed_at}",
                "truth_status": "real_observed",
                "generated_values": False,
            }

        # Mock client
        mock_client = MagicMock()
        mock_client.get_24h_tickers.return_value = {
            'BTC/USD': {'c': 50000, 'o': 49000, 'v': 1000}, # +2%
            'ETH/USD': {'c': 3000, 'o': 2700, 'v': 5000},   # +11%
            'DOGE/USD': {'c': 0.1, 'o': 0.11, 'v': 20000}    # -9%
        }
        
        scanner = PairScanner(client=mock_client)
        # Force a scan update manually (injecting data into cache since scan loop is threaded)
        cache = {
            'BTC/USD': {'symbol': 'BTC/USD', 'price': 50000, 'change24h': 2.04, 'volume': 1000, 'base': 'BTC', 'quote': 'USD'},
            'ETH/USD': {'symbol': 'ETH/USD', 'price': 3000, 'change24h': 11.11, 'volume': 5000, 'base': 'ETH', 'quote': 'USD'},
            'DOGE/USD': {'symbol': 'DOGE/USD', 'price': 0.1, 'change24h': -9.09, 'volume': 20000, 'base': 'DOGE', 'quote': 'USD'},
        }
        
        # Populate scored_targets by running internal logic (mocking scan_all_pairs if needed or just updating cache and calling scan)
        # PairScanner.scan_all_pairs takes ticker_cache and balances
        cache = {
            "BTC/USD": receipt("BTC/USD", 50000, 2.04, 1000),
            "ETH/USD": receipt("ETH/USD", 3000, 11.11, 5000),
            "DOGE/USD": receipt("DOGE/USD", 0.1, -9.09, 20000),
        }
        scanner.scan_all_pairs(ticker_cache=cache)
        
        targets = scanner.get_top_momentum_targets(n=2)
        
        self.assertEqual(len(targets), 2)
        # ETH should be first (highest momentum)
        self.assertEqual(targets[0]['symbol'], 'ETH/USD')
        # BTC second
        self.assertEqual(targets[1]['symbol'], 'BTC/USD')

if __name__ == '__main__':
    unittest.main()
