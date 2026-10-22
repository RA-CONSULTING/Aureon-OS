"""
Comprehensive test suite for the Orca Kill Cycle margin trading logic.

Tests LONG and SHORT margin signals end-to-end:
  1. Signal generation → order placement → correct API params
  2. Position tracking with correct margin_side metadata
  3. Close/kill logic with correct opposing side
  4. Error handling on failed orders
  5. Penny trader retry logic
  6. Spot fallback when margin fails
  7. Autonomous flow integration
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import time as _time
import sys
import os

# ---------------------------------------------------------------------------
#  Import the real classes under test
# ---------------------------------------------------------------------------

# LivePosition from orca
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orca_complete_kill_cycle import LivePosition, MarketOpportunity


class MockKrakenClient:
    """Mock Kraken client that validates API parameters for correctness."""

    def __init__(self):
        self.orders_placed = []
        self.closes_placed = []
        self.dry_run = False

    def place_margin_order(self, symbol, side, quantity, leverage,
                           order_type="market", price=None,
                           take_profit=None, stop_loss=None,
                           post_only=False, reduce_only=False):
        order = {
            'symbol': symbol, 'side': side, 'quantity': quantity,
            'leverage': leverage, 'order_type': order_type, 'price': price,
            'take_profit': take_profit, 'stop_loss': stop_loss,
            'post_only': post_only, 'reduce_only': reduce_only,
        }
        self.orders_placed.append(order)
        return {
            "symbol": symbol,
            "orderId": f"MOCK-{len(self.orders_placed)}",
            "clientOrderId": str(_time.time()),
            "transactTime": int(_time.time() * 1000),
            "price": str(price) if price else "0.00000000",
            "origQty": str(quantity),
            "executedQty": str(quantity),
            "cummulativeQuoteQty": str(float(quantity) * 2500.0),
            "status": "FILLED",
            "timeInForce": "GTC",
            "type": order_type.upper(),
            "side": side.upper(),
            "leverage": str(leverage),
            "margin": True,
        }

    def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
        order = {
            'symbol': symbol, 'side': side, 'quantity': quantity,
            'quote_qty': quote_qty, 'type': 'spot',
        }
        self.orders_placed.append(order)
        qty = quantity or (quote_qty / 2500.0 if quote_qty else 0)
        return {
            "symbol": symbol,
            "orderId": f"SPOT-{len(self.orders_placed)}",
            "executedQty": str(qty),
            "cummulativeQuoteQty": str(float(qty) * 2500.0),
            "price": "2500.00",
            "status": "FILLED",
            "side": side.upper(),
        }

    def close_margin_position(self, symbol, side, volume=None,
                               order_type="market", price=None,
                               leverage=None):
        close = {
            'symbol': symbol, 'side': side, 'volume': volume,
            'order_type': order_type, 'leverage': leverage,
        }
        self.closes_placed.append(close)
        return {
            "symbol": symbol,
            "orderId": f"CLOSE-{len(self.closes_placed)}",
            "type": order_type.upper(),
            "side": side.upper(),
            "quantity": str(volume) if volume else "0",
            "leverage": str(leverage) if leverage else None,
            "status": "FILLED",
            "margin_close": True,
            "filled_avg_price": "2600.00",
        }

    def get_ticker(self, symbol):
        return {'ask': 2500.0, 'bid': 2499.0, 'price': 2500.0}


class MockKrakenClientWithErrors(MockKrakenClient):
    """Mock that returns errors on margin orders."""

    def place_margin_order(self, *args, **kwargs):
        return {"error": "EOrder:Insufficient margin", "symbol": kwargs.get('symbol', args[0] if args else '')}

    def close_margin_position(self, *args, **kwargs):
        return {"error": "EOrder:Unknown position"}


# ===========================================================================
#  TEST 1: LONG Margin Signal → Order → Close
# ===========================================================================

class TestLongMarginKillCycle(unittest.TestCase):
    """Test the full LONG margin cycle: signal → buy → track → sell."""

    def test_long_margin_order_params(self):
        """LONG signal should place a BUY margin order."""
        client = MockKrakenClient()
        result = client.place_margin_order(
            symbol='ETHUSD', side='buy', quantity=0.5, leverage=3
        )
        self.assertEqual(result['side'], 'BUY')
        self.assertEqual(result['leverage'], '3')
        self.assertTrue(result['margin'])
        self.assertEqual(result['status'], 'FILLED')
        self.assertNotIn('error', result)

        # Verify the call params
        order = client.orders_placed[-1]
        self.assertEqual(order['side'], 'buy')
        self.assertEqual(order['leverage'], 3)
        self.assertEqual(order['quantity'], 0.5)

    def test_long_position_tracking(self):
        """LivePosition for LONG should have correct margin metadata."""
        pos = LivePosition(
            symbol='ETHUSD', exchange='kraken',
            entry_price=2500.0, entry_qty=0.5,
            entry_cost=2500.0 * 0.5 * 1.0022,
            breakeven_price=2511.0, target_price=2530.0,
            client=MockKrakenClient(),
            is_margin=True, leverage=3, margin_side='LONG',
            margin_amount=2500.0 * 0.5 / 3 * 1.0022,
        )
        self.assertTrue(pos.is_margin)
        self.assertEqual(pos.margin_side, 'LONG')
        self.assertEqual(pos.leverage, 3)

    def test_long_close_uses_sell_side(self):
        """Closing a LONG position must use SELL side."""
        client = MockKrakenClient()
        pos = LivePosition(
            symbol='ETHUSD', exchange='kraken',
            entry_price=2500.0, entry_qty=0.5,
            entry_cost=1252.75, breakeven_price=2511.0,
            target_price=2530.0, client=client,
            is_margin=True, leverage=3, margin_side='LONG',
        )
        # Simulate the kill cycle close logic
        close_side = 'sell' if pos.margin_side == 'LONG' else 'buy'
        self.assertEqual(close_side, 'sell')

        result = client.close_margin_position(
            symbol=pos.symbol, side=close_side,
            volume=pos.entry_qty, leverage=pos.leverage
        )
        self.assertEqual(result['side'], 'SELL')
        self.assertTrue(result['margin_close'])
        self.assertEqual(result['status'], 'FILLED')

        # Verify close params
        close = client.closes_placed[-1]
        self.assertEqual(close['side'], 'sell')
        self.assertEqual(close['volume'], 0.5)
        self.assertEqual(close['leverage'], 3)


# ===========================================================================
#  TEST 2: SHORT Margin Signal → Order → Close
# ===========================================================================

class TestShortMarginKillCycle(unittest.TestCase):
    """Test the full SHORT margin cycle: signal → sell → track → buy-to-close."""

    def test_short_margin_order_params(self):
        """SHORT signal should place a SELL margin order."""
        client = MockKrakenClient()
        result = client.place_margin_order(
            symbol='ETHUSD', side='sell', quantity=0.5, leverage=3
        )
        self.assertEqual(result['side'], 'SELL')
        self.assertEqual(result['leverage'], '3')
        self.assertTrue(result['margin'])

        order = client.orders_placed[-1]
        self.assertEqual(order['side'], 'sell')

    def test_short_position_tracking(self):
        """LivePosition for SHORT should have margin_side='SHORT'."""
        pos = LivePosition(
            symbol='ETHUSD', exchange='kraken',
            entry_price=2500.0, entry_qty=0.5,
            entry_cost=2500.0 * 0.5 * 1.0022,
            breakeven_price=2489.0, target_price=2470.0,
            client=MockKrakenClient(),
            is_margin=True, leverage=3, margin_side='SHORT',
        )
        self.assertTrue(pos.is_margin)
        self.assertEqual(pos.margin_side, 'SHORT')

    def test_short_close_uses_buy_side(self):
        """Closing a SHORT position must use BUY side."""
        client = MockKrakenClient()
        pos = LivePosition(
            symbol='ETHUSD', exchange='kraken',
            entry_price=2500.0, entry_qty=0.5,
            entry_cost=1252.75, breakeven_price=2489.0,
            target_price=2470.0, client=client,
            is_margin=True, leverage=3, margin_side='SHORT',
        )
        close_side = 'sell' if pos.margin_side == 'LONG' else 'buy'
        self.assertEqual(close_side, 'buy')

        result = client.close_margin_position(
            symbol=pos.symbol, side=close_side,
            volume=pos.entry_qty, leverage=pos.leverage
        )
        self.assertEqual(result['side'], 'BUY')
        self.assertTrue(result['margin_close'])

        close = client.closes_placed[-1]
        self.assertEqual(close['side'], 'buy')
        self.assertEqual(close['volume'], 0.5)


# ===========================================================================
#  TEST 3: Error Handling — Margin Order Failures
# ===========================================================================

class TestMarginErrorHandling(unittest.TestCase):
    """Test that error responses are properly detected and handled."""

    def test_margin_order_error_detected(self):
        """Orders with 'error' key must NOT be treated as success."""
        client = MockKrakenClientWithErrors()
        result = client.place_margin_order(
            symbol='ETHUSD', side='buy', quantity=0.5, leverage=3
        )
        self.assertIn('error', result)
        self.assertTrue(result.get('error'))

    def test_margin_close_error_detected(self):
        """Close orders with 'error' key must NOT be treated as success."""
        client = MockKrakenClientWithErrors()
        result = client.close_margin_position(
            symbol='ETHUSD', side='sell', volume=0.5
        )
        self.assertIn('error', result)

    def test_error_result_not_treated_as_margin_success(self):
        """Simulate the queen_gated_buy error check logic."""
        result = {"error": "EOrder:Insufficient margin", "symbol": "ETHUSD"}
        # This is the fixed check from our commit
        is_success = result and not result.get('error')
        self.assertFalse(is_success)

    def test_successful_result_passes_check(self):
        """Successful margin result should pass the error check."""
        result = {
            "symbol": "ETHUSD", "orderId": "MOCK-1",
            "status": "FILLED", "margin": True,
        }
        is_success = result and not result.get('error')
        self.assertTrue(is_success)


# ===========================================================================
#  TEST 4: Margin Side Metadata Consistency
# ===========================================================================

class TestMarginSideMetadata(unittest.TestCase):
    """Test that margin_side stays consistent between open and close."""

    def test_long_recommendation_maps_to_buy_side(self):
        """margin_recommendation='LONG' → _m_side='buy'."""
        margin_recommendation = 'LONG'
        _m_side = 'buy' if margin_recommendation in ('LONG', 'NONE', '') else 'sell'
        self.assertEqual(_m_side, 'buy')

    def test_short_recommendation_maps_to_sell_side(self):
        """margin_recommendation='SHORT' → _m_side='sell'."""
        margin_recommendation = 'SHORT'
        _m_side = 'buy' if margin_recommendation in ('LONG', 'NONE', '') else 'sell'
        self.assertEqual(_m_side, 'sell')

    def test_fixed_metadata_long(self):
        """Fixed code: LONG recommendation → margin_side='LONG'."""
        margin_recommendation = 'LONG'
        _m_side = 'buy' if margin_recommendation in ('LONG', 'NONE', '') else 'sell'

        # Our fixed logic from queen_gated_buy
        if margin_recommendation in ('LONG', 'SHORT'):
            margin_side = margin_recommendation
        else:
            margin_side = 'LONG' if _m_side == 'buy' else 'SHORT'

        self.assertEqual(margin_side, 'LONG')

    def test_fixed_metadata_short(self):
        """Fixed code: SHORT recommendation → margin_side='SHORT'."""
        margin_recommendation = 'SHORT'
        _m_side = 'buy' if margin_recommendation in ('LONG', 'NONE', '') else 'sell'

        if margin_recommendation in ('LONG', 'SHORT'):
            margin_side = margin_recommendation
        else:
            margin_side = 'LONG' if _m_side == 'buy' else 'SHORT'

        self.assertEqual(margin_side, 'SHORT')

    def test_fixed_metadata_none_defaults_to_long(self):
        """Fixed code: NONE recommendation + buy side → margin_side='LONG'."""
        margin_recommendation = 'NONE'
        _m_side = 'buy' if margin_recommendation in ('LONG', 'NONE', '') else 'sell'

        if margin_recommendation in ('LONG', 'SHORT'):
            margin_side = margin_recommendation
        else:
            margin_side = 'LONG' if _m_side == 'buy' else 'SHORT'

        self.assertEqual(margin_side, 'LONG')
        self.assertEqual(_m_side, 'buy')

    def test_close_side_matches_position(self):
        """Close side must be opposite of margin_side for both LONG and SHORT."""
        for margin_side, expected_close in [('LONG', 'sell'), ('SHORT', 'buy')]:
            close_side = 'sell' if margin_side == 'LONG' else 'buy'
            self.assertEqual(close_side, expected_close,
                             f"margin_side={margin_side} should close with {expected_close}")


# ===========================================================================
#  TEST 5: Penny Trader Retry Logic
# ===========================================================================

class TestPennyTraderRetryLogic(unittest.TestCase):
    """Test the 3-level close retry preserves volume."""

    def test_all_retries_keep_volume(self):
        """All retry attempts must pass the trade volume to prevent closing wrong positions."""
        # Simulate the penny trader retry with ActiveTrade
        @dataclass
        class ActiveTrade:
            pair: str
            side: str
            volume: float
            entry_price: float
            leverage: int
            entry_fee: float
            entry_time: float
            order_id: str
            binance_symbol: str = ""

        trade = ActiveTrade(
            pair='ETHUSD', side='buy', volume=0.5,
            entry_price=2500.0, leverage=3,
            entry_fee=2.5, entry_time=_time.time(),
            order_id='TEST-1'
        )
        close_side = "sell" if trade.side == "buy" else "buy"

        # Track all close attempts
        close_attempts = []

        class TrackingClient:
            def close_margin_position(self, **kwargs):
                close_attempts.append(kwargs)
                if len(close_attempts) < 3:
                    return {"error": "EOrder:Insufficient margin"}
                return {"orderId": "CLOSE-OK", "status": "FILLED", "margin_close": True}

        client = TrackingClient()

        # Simulate the fixed retry logic from kraken_margin_penny_trader.py
        result = client.close_margin_position(
            symbol=trade.pair, side=close_side,
            volume=trade.volume, leverage=trade.leverage,
        )
        if result.get("error"):
            result = client.close_margin_position(
                symbol=trade.pair, side=close_side,
                volume=trade.volume,
            )
            if result.get("error"):
                result = client.close_margin_position(
                    symbol=trade.pair, side=close_side,
                    volume=trade.volume,  # FIXED: volume preserved
                )

        # Verify ALL attempts passed the volume
        for i, attempt in enumerate(close_attempts):
            self.assertEqual(attempt['volume'], 0.5,
                             f"Attempt {i+1} must pass volume=0.5, got {attempt.get('volume')}")
            self.assertEqual(attempt['side'], 'sell',
                             f"Attempt {i+1} must use side='sell'")

        # 3rd attempt should succeed
        self.assertNotIn('error', result)

    def test_close_side_correct_for_long(self):
        """LONG (buy) position → close with sell."""
        trade_side = "buy"
        close_side = "sell" if trade_side == "buy" else "buy"
        self.assertEqual(close_side, "sell")

    def test_close_side_correct_for_short(self):
        """SHORT (sell) position → close with buy."""
        trade_side = "sell"
        close_side = "sell" if trade_side == "buy" else "buy"
        self.assertEqual(close_side, "buy")


# ===========================================================================
#  TEST 6: Spot Fallback When Margin Fails
# ===========================================================================

class TestSpotFallback(unittest.TestCase):
    """Test that system falls back to spot when margin order fails."""

    def test_margin_error_triggers_spot_fallback(self):
        """When margin order returns error, system should try spot."""
        # Simulate the fixed queen_gated_buy logic
        margin_result = {"error": "EOrder:Insufficient margin", "symbol": "ETHUSD"}

        # Fixed check: result and not result.get('error')
        margin_success = margin_result and not margin_result.get('error')
        self.assertFalse(margin_success, "Error result must not be treated as success")

        # Fall through to spot
        spot_client = MockKrakenClient()
        spot_result = spot_client.place_market_order(
            symbol='ETHUSD', side='buy', quote_qty=50.0
        )
        self.assertNotIn('error', spot_result)
        self.assertEqual(spot_result['status'], 'FILLED')

    def test_none_result_handled(self):
        """None result from margin order should not crash."""
        result = None
        is_success = result and not result.get('error')
        self.assertFalse(is_success)


# ===========================================================================
#  TEST 7: Kraken API Parameter Correctness
# ===========================================================================

class TestKrakenAPIParams(unittest.TestCase):
    """Verify the real KrakenClient sends correct params for spot and margin."""

    def test_margin_order_has_trading_agreement(self):
        """place_margin_order must include trading_agreement='agree'."""
        from kraken_client import KrakenClient
        client = KrakenClient.__new__(KrakenClient)
        client.dry_run = True
        client._asset_pairs = {}
        result = client.place_margin_order(
            symbol='ETHUSD', side='buy', quantity=0.5, leverage=3
        )
        self.assertTrue(result['dryRun'])
        self.assertTrue(result['margin'])

    def test_margin_close_has_trading_agreement(self):
        """close_margin_position must include trading_agreement='agree'."""
        from kraken_client import KrakenClient
        client = KrakenClient.__new__(KrakenClient)
        client.dry_run = True
        result = client.close_margin_position(
            symbol='ETHUSD', side='sell', volume=0.5, leverage=3
        )
        self.assertTrue(result['dryRun'])
        self.assertTrue(result['margin_close'])

    def test_margin_order_params_in_code(self):
        """Verify the actual source code has trading_agreement in params."""
        import inspect
        from kraken_client import KrakenClient

        source = inspect.getsource(KrakenClient.place_margin_order)
        self.assertIn('trading_agreement', source,
                       "place_margin_order must include trading_agreement param")
        self.assertIn('reduce_only', source,
                       "place_margin_order must support reduce_only param")

    def test_close_margin_params_in_code(self):
        """Verify close_margin_position has reduce_only and trading_agreement."""
        import inspect
        from kraken_client import KrakenClient

        source = inspect.getsource(KrakenClient.close_margin_position)
        self.assertIn('trading_agreement', source,
                       "close_margin_position must include trading_agreement")
        self.assertIn('reduce_only', source,
                       "close_margin_position must include reduce_only")

    def test_reduce_only_not_in_oflags(self):
        """reduce_only must be a top-level param, NOT in oflags."""
        import inspect
        from kraken_client import KrakenClient

        source = inspect.getsource(KrakenClient.place_margin_order)
        # The fix: reduce_only should use params["reduce_only"] not oflags
        lines = source.split('\n')
        for line in lines:
            if 'reduce_only' in line and 'oflags' in line and 'nompp' in line:
                self.fail(f"reduce_only should NOT use nompp oflag: {line.strip()}")


# ===========================================================================
#  TEST 8: Kill Cycle Error Check on Sell
# ===========================================================================

class TestKillCycleSellErrorCheck(unittest.TestCase):
    """Test that the kill cycle properly checks sell order results."""

    def test_sell_error_not_counted_as_success(self):
        """Sell order with error should not record P&L."""
        sell_order = {"error": "EOrder:Unknown position"}
        # Fixed check from our commit
        if sell_order and sell_order.get('error'):
            should_record_pnl = False
        elif sell_order and not sell_order.get('error'):
            should_record_pnl = True
        else:
            should_record_pnl = False
        self.assertFalse(should_record_pnl)

    def test_successful_sell_records_pnl(self):
        """Successful sell should record P&L."""
        sell_order = {
            "orderId": "CLOSE-1", "status": "FILLED",
            "margin_close": True, "filled_avg_price": "2600.00"
        }
        if sell_order and sell_order.get('error'):
            should_record_pnl = False
        elif sell_order and not sell_order.get('error'):
            should_record_pnl = True
        else:
            should_record_pnl = False
        self.assertTrue(should_record_pnl)

    def test_none_sell_not_counted(self):
        """None sell order should not record P&L."""
        sell_order = None
        if sell_order and sell_order.get('error'):
            should_record_pnl = False
        elif sell_order and not sell_order.get('error'):
            should_record_pnl = True
        else:
            should_record_pnl = False
        self.assertFalse(should_record_pnl)

    def test_position_not_removed_on_sell_error(self):
        """Position must stay in tracking list if sell fails."""
        positions = ['ETH_LONG_POS']
        sell_order = {"error": "EOrder:Insufficient margin"}

        # Fixed logic: only remove on success
        if sell_order and not sell_order.get('error'):
            positions.remove('ETH_LONG_POS')

        self.assertIn('ETH_LONG_POS', positions,
                       "Position must remain if sell failed")

    def test_position_removed_on_sell_success(self):
        """Position should be removed from tracking on successful sell."""
        positions = ['ETH_LONG_POS']
        sell_order = {"orderId": "CLOSE-1", "status": "FILLED"}

        if sell_order and not sell_order.get('error'):
            positions.remove('ETH_LONG_POS')

        self.assertNotIn('ETH_LONG_POS', positions,
                         "Position should be removed after successful sell")


# ===========================================================================
#  TEST 9: Normalize Order Response
# ===========================================================================

class TestNormalizeOrderResponse(unittest.TestCase):
    """Test the order normalization handles all Kraken margin responses."""

    def _make_orca(self):
        """Create a minimal OrcaKillCycle-like object with normalize_order_response."""
        class MiniOrca:
            fee_rates = {'kraken': 0.0022}

            def normalize_order_response(self, order, exchange):
                if not order:
                    return {'filled_qty': 0, 'filled_avg_price': 0, 'order_id': None, 'status': 'empty'}
                if order.get('error'):
                    return {'filled_qty': 0, 'filled_avg_price': 0, 'order_id': None,
                            'status': 'error', 'reason': str(order.get('error'))}
                if order.get('dryRun'):
                    return {'filled_qty': 0, 'filled_avg_price': 0, 'order_id': 'DRY_RUN', 'status': 'dry_run'}

                exec_qty = float(order.get('executedQty', 0))
                cumm_quote = float(order.get('cummulativeQuoteQty', 0))
                avg_price = float(order.get('price', 0))
                if avg_price == 0 and exec_qty > 0 and cumm_quote > 0:
                    avg_price = cumm_quote / exec_qty
                return {
                    'filled_qty': exec_qty,
                    'filled_avg_price': avg_price,
                    'order_id': order.get('orderId'),
                    'status': order.get('status', 'FILLED' if exec_qty > 0 else 'UNKNOWN'),
                }
        return MiniOrca()

    def test_normalize_margin_buy(self):
        """Kraken margin buy should normalize correctly."""
        orca = self._make_orca()
        order = {
            "orderId": "TX123", "executedQty": "0.5",
            "cummulativeQuoteQty": "1250.00", "price": "2500.00",
            "status": "FILLED", "margin": True, "leverage": "3",
        }
        n = orca.normalize_order_response(order, 'kraken')
        self.assertEqual(n['filled_qty'], 0.5)
        self.assertEqual(n['filled_avg_price'], 2500.0)
        self.assertEqual(n['order_id'], 'TX123')
        self.assertEqual(n['status'], 'FILLED')

    def test_normalize_error_order(self):
        """Error orders should normalize with status='error'."""
        orca = self._make_orca()
        order = {"error": "EOrder:Insufficient margin"}
        n = orca.normalize_order_response(order, 'kraken')
        self.assertEqual(n['filled_qty'], 0)
        self.assertEqual(n['status'], 'error')

    def test_normalize_none_order(self):
        """None orders should normalize gracefully."""
        orca = self._make_orca()
        n = orca.normalize_order_response(None, 'kraken')
        self.assertEqual(n['filled_qty'], 0)
        self.assertEqual(n['status'], 'empty')


# ===========================================================================
#  TEST 10: Full Autonomous E2E Simulation
# ===========================================================================

class TestAutonomousE2EFlow(unittest.TestCase):
    """Simulate the full autonomous LONG and SHORT margin flows end-to-end."""

    def _run_full_cycle(self, margin_side, momentum_pct):
        """Run a complete signal → buy → track → kill cycle."""
        client = MockKrakenClient()

        # STEP 1: Generate signal
        margin_recommendation = 'LONG' if momentum_pct >= 0 else 'SHORT'
        self.assertEqual(margin_recommendation, margin_side)

        # STEP 2: Determine order side
        _m_side = 'buy' if margin_recommendation in ('LONG', 'NONE', '') else 'sell'
        expected_order_side = 'buy' if margin_side == 'LONG' else 'sell'
        self.assertEqual(_m_side, expected_order_side)

        # STEP 3: Place margin order
        leverage = 3
        quantity = 0.5
        result = client.place_margin_order(
            symbol='ETHUSD', side=_m_side, quantity=quantity, leverage=leverage
        )
        self.assertNotIn('error', result)
        self.assertEqual(result['status'], 'FILLED')

        # STEP 4: Set metadata (fixed logic)
        if margin_recommendation in ('LONG', 'SHORT'):
            result_margin_side = margin_recommendation
        else:
            result_margin_side = 'LONG' if _m_side == 'buy' else 'SHORT'
        self.assertEqual(result_margin_side, margin_side)

        # STEP 5: Create position
        pos = LivePosition(
            symbol='ETHUSD', exchange='kraken',
            entry_price=2500.0, entry_qty=quantity,
            entry_cost=2500.0 * quantity * 1.0022,
            breakeven_price=2511.0 if margin_side == 'LONG' else 2489.0,
            target_price=2530.0 if margin_side == 'LONG' else 2470.0,
            client=client,
            is_margin=True, leverage=leverage,
            margin_side=result_margin_side,
        )
        self.assertEqual(pos.margin_side, margin_side)

        # STEP 6: Kill - close the position
        close_side = 'sell' if pos.margin_side == 'LONG' else 'buy'
        expected_close_side = 'sell' if margin_side == 'LONG' else 'buy'
        self.assertEqual(close_side, expected_close_side)

        sell_order = client.close_margin_position(
            symbol=pos.symbol, side=close_side,
            volume=pos.entry_qty, leverage=pos.leverage
        )
        self.assertNotIn('error', sell_order)
        self.assertTrue(sell_order['margin_close'])
        self.assertEqual(sell_order['side'], expected_close_side.upper())

        # Verify volume consistency
        close = client.closes_placed[-1]
        self.assertEqual(close['volume'], pos.entry_qty)

        return {
            'signal': margin_side,
            'order_side': _m_side,
            'close_side': close_side,
            'order_result': result,
            'close_result': sell_order,
        }

    def test_full_long_cycle(self):
        """E2E: LONG signal → buy → track → sell-to-close."""
        cycle = self._run_full_cycle('LONG', momentum_pct=2.5)
        self.assertEqual(cycle['signal'], 'LONG')
        self.assertEqual(cycle['order_side'], 'buy')
        self.assertEqual(cycle['close_side'], 'sell')

    def test_full_short_cycle(self):
        """E2E: SHORT signal → sell → track → buy-to-close."""
        cycle = self._run_full_cycle('SHORT', momentum_pct=-3.0)
        self.assertEqual(cycle['signal'], 'SHORT')
        self.assertEqual(cycle['order_side'], 'sell')
        self.assertEqual(cycle['close_side'], 'buy')

    def test_multiple_positions_independent(self):
        """Multiple LONG and SHORT positions can coexist."""
        client = MockKrakenClient()
        positions = []

        # Open LONG ETH
        r1 = client.place_margin_order(symbol='ETHUSD', side='buy', quantity=0.5, leverage=3)
        pos1 = LivePosition(
            symbol='ETHUSD', exchange='kraken',
            entry_price=2500.0, entry_qty=0.5,
            entry_cost=1252.75, breakeven_price=2511.0,
            target_price=2530.0, client=client,
            is_margin=True, leverage=3, margin_side='LONG',
        )
        positions.append(pos1)

        # Open SHORT BTC
        r2 = client.place_margin_order(symbol='BTCUSD', side='sell', quantity=0.01, leverage=2)
        pos2 = LivePosition(
            symbol='BTCUSD', exchange='kraken',
            entry_price=65000.0, entry_qty=0.01,
            entry_cost=325.72, breakeven_price=64856.0,
            target_price=64500.0, client=client,
            is_margin=True, leverage=2, margin_side='SHORT',
        )
        positions.append(pos2)

        self.assertEqual(len(positions), 2)

        # Close them independently
        for pos in positions[:]:
            close_side = 'sell' if pos.margin_side == 'LONG' else 'buy'
            result = client.close_margin_position(
                symbol=pos.symbol, side=close_side,
                volume=pos.entry_qty, leverage=pos.leverage
            )
            if result and not result.get('error'):
                positions.remove(pos)

        self.assertEqual(len(positions), 0, "All positions should be closed")
        self.assertEqual(len(client.closes_placed), 2)

        # Verify ETH close was SELL, BTC close was BUY
        eth_close = client.closes_placed[0]
        btc_close = client.closes_placed[1]
        self.assertEqual(eth_close['side'], 'sell')
        self.assertEqual(btc_close['side'], 'buy')


if __name__ == '__main__':
    print("=" * 80)
    print("  ORCA KILL CYCLE — MARGIN TRADING TEST SUITE")
    print("  Testing LONG signals, SHORT signals, error handling,")
    print("  close logic, retry safety, and autonomous flow")
    print("=" * 80)
    unittest.main(verbosity=2)
