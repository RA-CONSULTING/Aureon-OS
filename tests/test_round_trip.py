from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import unittest
from micro_profit_labyrinth import MicroProfitLabyrinth

class DummyNavigator:
    def __init__(self, path):
        self._path = path
    def find_path(self, from_asset, to_asset):
        return self._path


# The production path object carries .hops — a list of hop OBJECTS with .pair /
# .exchange attributes (not 'steps' dicts). The old dict-shaped fakes made the
# checker raise inside its try, and the fail-open "assume available" branch
# flipped every negative test to a false pass.
class Hop:
    def __init__(self, pair=None, exchange=None):
        self.pair = pair
        self.exchange = exchange


class DummyPath:
    def __init__(self, hops):
        self.hops = hops

class TestRoundTripAvailability(unittest.TestCase):
    def setUp(self):
        self.lab = MicroProfitLabyrinth(dry_run=True)
        # start with an empty ticker cache
        self.lab.ticker_cache = {}

    def test_no_barter_navigator(self):
        self.lab.barter_navigator = None
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 100.0)
        self.assertFalse(ok)
        self.assertEqual(reason, 'NO_DATA: barter navigator is unavailable')

    def test_alpaca_only_rejects_non_alpaca_paths(self):
        # ALPACA_ONLY set - only allow paths that are fully on Alpaca
        self.lab.alpaca_only = True
        path = DummyPath([Hop('USD/AAPL', 'kraken')])
        self.lab.barter_navigator = DummyNavigator(path)
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 100.0, live_depth_check=True)
        self.assertFalse(ok)
        self.assertIn('ALPACA_ONLY active', reason)

    def test_no_path_found(self):
        self.lab.barter_navigator = DummyNavigator(None)
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 100.0)
        self.assertFalse(ok)
        self.assertIn('No conversion path found', reason)

    def test_empty_steps(self):
        self.lab.barter_navigator = DummyNavigator(DummyPath([]))
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 100.0)
        self.assertFalse(ok)
        # Current implementation returns 'No conversion path found' if steps empty
        self.assertIn('No conversion path found', reason)

    def test_missing_pair_in_step(self):
        path = DummyPath([Hop(pair=None)])
        self.lab.barter_navigator = DummyNavigator(path)
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 100.0)
        self.assertFalse(ok)
        self.assertIn('Missing pair info in path step', reason)

    def test_no_ticker_for_pair(self):
        path = DummyPath([Hop('USD/AAPL')])
        self.lab.barter_navigator = DummyNavigator(path)
        self.lab.ticker_cache = {}  # ensure no ticker
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 100.0)
        self.assertFalse(ok)
        self.assertIn('No price/ticker for pair USD/AAPL', reason)

    def test_insufficient_volume(self):
        path = DummyPath([Hop('USD/AAPL')])
        self.lab.barter_navigator = DummyNavigator(path)
        self.lab.ticker_cache = {'USD/AAPL': {'volume': 0.1, 'price': 1.0}}
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 100.0)
        self.assertFalse(ok)
        self.assertIn('Insufficient volume on USD/AAPL', reason)

    def test_per_leg_too_small(self):
        path = DummyPath([Hop('USD/AAPL'), Hop('AAPL/GOOG')])
        self.lab.barter_navigator = DummyNavigator(path)
        # provide tickers with high volume so per-leg check fails on notional
        self.lab.ticker_cache = {'USD/AAPL': {'volume': 1000, 'price': 1.0}, 'AAPL/GOOG': {'volume': 1000, 'price': 1.0}}
        # per-leg minimum is $0.50; $0.90 across 2 legs = $0.45/leg -> too small
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 0.9)  # very small notional
        self.assertFalse(ok)
        self.assertIn('too small for 2-leg path', reason)

    def test_success_path(self):
        path = DummyPath([Hop('USD/AAPL', 'alpaca'), Hop('AAPL/USD', 'alpaca')])
        self.lab.barter_navigator = DummyNavigator(path)
        # volume * price gives sufficient per-leg USD
        self.lab.ticker_cache = {'USD/AAPL': {'volume': 1000, 'price': 1.0}, 'AAPL/USD': {'volume': 1000, 'price': 1.0}}
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 100.0)
        self.assertTrue(ok)
        self.assertIn('Round-trip available', reason)

    def test_live_depth_check_fails_when_orderbook_insufficient(self):
        path = DummyPath([Hop('USD/AAPL', 'alpaca')])
        self.lab.barter_navigator = DummyNavigator(path)
        # Provide no ticker so it must resort to orderbook
        self.lab.ticker_cache = {}
        # Monkeypatch fee tracker
        class DummyFeeTracker:
            def get_orderbook(self, symbol):
                # Return small depth
                return {'bids': [[1.0, 0.1]], 'asks': [[1.01, 0.1]]}
        self.lab.alpaca_fee_tracker = DummyFeeTracker()
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 100.0, live_depth_check=True)
        self.assertFalse(ok)
        self.assertIn('Insufficient two-sided orderbook depth', reason)

    def test_live_depth_check_passes_when_orderbook_sufficient(self):
        path = DummyPath([Hop('USD/AAPL', 'alpaca')])
        self.lab.barter_navigator = DummyNavigator(path)
        self.lab.ticker_cache = {}
        class DummyFeeTracker2:
            def get_orderbook(self, symbol):
                # Return ample depth: price * size sums > 100
                return {'bids': [[1.0, 200.0]], 'asks': [[1.01, 200.0]]}
        self.lab.alpaca_fee_tracker = DummyFeeTracker2()
        ok, reason = self.lab.ensure_round_trip_available('USD', 'AAPL', 100.0, live_depth_check=True)
        self.assertTrue(ok)
        self.assertIn('Round-trip available', reason)

    def test_compute_mc_pwin(self):
        # Test compute of P(win) using mocked draws
        class DummyEstimator:
            def sample_total_cost_draws(self, symbol, side, notional_usd, n_samples=1000):
                # Return percent draws where costs are small
                return [1.0, 1.0, 1.0, 1.0]  # 1% costs each
        self.lab.cost_estimator = DummyEstimator()
        gross = 5.0
        notional = 100.0
        p_win = self.lab.compute_mc_pwin('USD/AAPL', gross, notional, n_samples=4)
        # costs=1% -> cost USD=1.0 -> net samples = [4,4,4,4] so P(win)=1.0
        self.assertAlmostEqual(p_win, 1.0)

    def test_compute_mc_pwin_low(self):
        class DummyEstimator2:
            def sample_total_cost_draws(self, symbol, side, notional_usd, n_samples=1000):
                # high costs so nets negative
                return [50.0, 60.0, 40.0]
        self.lab.cost_estimator = DummyEstimator2()
        gross = 1.0
        notional = 100.0
        p_win = self.lab.compute_mc_pwin('USD/AAPL', gross, notional, n_samples=3)
        self.assertAlmostEqual(p_win, 0.0)

if __name__ == '__main__':
    unittest.main()
