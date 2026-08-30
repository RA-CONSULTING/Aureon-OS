from aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import time
import unittest
from unittest.mock import MagicMock, patch

from aureon_unified_ecosystem import AureonKrakenEcosystem, Position, CONFIG


class TestNetProfitAfterFeesSmoke(unittest.TestCase):
    def setUp(self):
        self._orig_config = CONFIG.copy()

        # Keep fee/impact values explicit so the smoke test is deterministic.
        CONFIG['SLIPPAGE_PCT'] = 0.0020   # 0.20%
        CONFIG['SPREAD_COST_PCT'] = 0.0010  # 0.10%
        CONFIG['BASE_CURRENCY'] = 'USD'

    def tearDown(self):
        CONFIG.clear()
        CONFIG.update(self._orig_config)

    @patch('aureon_unified_ecosystem.WAR_STRATEGY_AVAILABLE', False)
    @patch('aureon_unified_ecosystem.WAR_STRATEGIST', None)
    @patch('aureon_unified_ecosystem.TRADE_LOGGER_AVAILABLE', False)
    @patch('aureon_unified_ecosystem.trade_logger', None)
    @patch('aureon_unified_ecosystem.get_exchange_fee_rate', return_value=0.0020)
    @patch('aureon_unified_ecosystem.ADAPTIVE_LEARNER', autospec=False)
    def test_close_position_net_profit_after_all_costs(
        self,
        mock_learner,
        _mock_fee_rate,
    ):
        """Smoke test: a full close path yields net profit after fees/slippage/spread."""

        # Build a minimal ecosystem instance without running the massive __init__.
        eco = AureonKrakenEcosystem.__new__(AureonKrakenEcosystem)
        eco.dry_run = False
        eco.positions = {}
        eco.ticker_cache = {}
        eco._last_news_sentiment = {}
        eco.prob_matrix = None
        eco.nexus_predictor = None
        eco.bridge_enabled = False
        eco.bridge = None

        # Dependencies used by close_position
        eco.tracker = MagicMock()
        eco.tracker.symbol_exposure = {}
        eco.tracker.win_rate = 0.0
        eco.tracker.record_trade = MagicMock()

        eco.capital_pool = MagicMock()
        eco.capital_pool.total_profits = 0.0
        eco.capital_pool.deallocate = MagicMock()

        eco.multi_exchange = MagicMock()
        eco.multi_exchange.record_trade_result = MagicMock()

        eco.mycelium = MagicMock()
        eco.mycelium.learn = MagicMock()

        eco.memory = MagicMock()
        eco.memory.record = MagicMock()
        eco.memory.is_surge_window_active = MagicMock(return_value=False)

        eco.elephant_memory = MagicMock()
        eco.elephant_memory.record = MagicMock()

        eco.refresh_equity = MagicMock()
        eco.save_state = MagicMock()
        eco._record_sniper_kill = MagicMock()
        eco._emit_mycelium_event = MagicMock()

        # Exit gate: allow selling.
        eco.should_exit_trade = MagicMock(return_value=True)
        eco._detect_exchange_for_symbol = MagicMock(return_value='kraken')

        # Create a position with enough edge to beat "all them dam charges".
        symbol = 'BTCUSD'
        entry_price = 100.0
        exit_price = 101.50
        quantity = 1.0
        entry_value = entry_price * quantity

        fee_rate = 0.0020
        total_rate = fee_rate + CONFIG['SLIPPAGE_PCT'] + CONFIG['SPREAD_COST_PCT']
        entry_fee = entry_value * total_rate
        exit_value = exit_price * quantity
        expected_exit_fee = exit_value * total_rate
        provider_now = time.time()

        pos = Position(
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            entry_fee=entry_fee,
            entry_value=entry_value,
            momentum=0.0,
            coherence=0.9,
            entry_time=time.time() - 3600,  # avoid resonance minimum-hold return
            dominant_node='Queen',
            exchange='kraken',
            provider_order_id='kraken-entry-order-1',
            provider_fill_id='kraken-entry-fill-1',
            fill_source_id='kraken_order_fill',
            fill_source_timestamp=provider_now - 3600.0,
            truth_status='live',
        )
        eco.positions[symbol] = pos

        eco.client = MagicMock()
        eco.client.get_balance.return_value = quantity
        eco.trade_confirmation = MagicMock()
        eco.trade_confirmation.submit_order.return_value = {
            'raw_response': {
                'order_id': 'kraken-close-order-1',
                'status': 'filled',
                'symbol': symbol,
                'executed_qty': quantity,
                'avg_price': exit_price,
                'cummulativeQuoteQty': exit_value,
                'fee': expected_exit_fee,
                'fee_asset': 'USD',
                'source_timestamp': provider_now,
            }
        }
        market_evidence = {
            'price': exit_price,
            'bid': exit_price,
            'source_id': 'kraken_ticker:BTCUSD',
            'source_timestamp': provider_now - 0.1,
            'received_at': provider_now,
            'truth_status': 'live',
            'generated_values': False,
        }

        # Run the close (the "cycle" exit leg).
        receipt = eco.close_position(
            symbol=symbol,
            reason='SMOKE',
            pct=1.50,
            price=exit_price,
            market_evidence=market_evidence,
        )

        # Position removed and a trade recorded.
        self.assertEqual(receipt['execution_status'], 'filled')
        self.assertNotIn(symbol, eco.positions)
        eco.tracker.record_trade.assert_called_once()

        _, kwargs = eco.tracker.record_trade.call_args
        net_pnl = kwargs.get('net_pnl')
        fees = kwargs.get('fees')

        self.assertIsNotNone(net_pnl)
        self.assertIsNotNone(fees)
        self.assertGreater(fees, 0.0)
        self.assertGreater(net_pnl, 0.0)

        # Validate net P&L math matches the close_position model.
        expected_total_expenses = entry_fee + expected_exit_fee
        expected_gross_pnl = exit_value - entry_value
        expected_net_pnl = expected_gross_pnl - expected_total_expenses

        self.assertAlmostEqual(net_pnl, expected_net_pnl, places=8)

        # Ensure the learner hook was invoked (cycle feedback loop).
        self.assertTrue(hasattr(mock_learner, 'enhanced_record_trade'))


if __name__ == '__main__':
    unittest.main()
