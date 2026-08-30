#!/usr/bin/env python3
import time
import unittest
from unittest.mock import patch

from aureon.exchanges.kraken_client import KrakenClient
from aureon.exchanges.kraken_margin_penny_trader import ActiveTrade, KrakenMarginArmyTrader, MarginPairInfo
from aureon.trading.dynamic_margin_sizer import DynamicMarginConfig, DynamicMarginSizer
from aureon.trading.temporal_trade_cognition import TemporalTradeCognition


def _trade_balance_receipt(
    *,
    equity: float,
    free_margin: float,
    margin_amount: float = 0.0,
    unrealized_pnl: float = 0.0,
    margin_level: float = 0.0,
):
    return {
        "data_status": "live",
        "truth_status": "real_observed",
        "generated_values": False,
        "source_id": "kraken:trade_balance:test",
        "received_at": time.time(),
        "equity_value": str(equity),
        "trade_balance": str(equity),
        "margin_amount": str(margin_amount),
        "unrealized_pnl": str(unrealized_pnl),
        "cost_basis": str(margin_amount),
        "floating_valuation": str(margin_amount + unrealized_pnl),
        "free_margin": str(free_margin),
        "margin_level": str(margin_level),
    }


class TestKrakenMarginStartupSync(unittest.TestCase):
    def test_capital_snapshot_uses_live_spot_balances_when_margin_equity_is_zero(self):
        trader = KrakenMarginArmyTrader.__new__(KrakenMarginArmyTrader)
        trader.dry_run = False
        trader.dynamic_sizer = None
        trader.market = None
        trader._last_margin_capital = None
        trader._last_margin_capital_at = 0.0
        trader._last_margin_capital_error = ""
        trader._last_spot_balance_snapshot = {}
        trader._last_spot_balance_snapshot_at = 0.0
        trader.client = type("ClientStub", (), {
            "get_trade_balance": staticmethod(
                lambda: _trade_balance_receipt(equity=0.0, free_margin=0.0)
            ),
            "get_account_balance": staticmethod(lambda: {"GBP": 100.0, "USDT": 5.0}),
            "get_24h_ticker": staticmethod(
                lambda pair: {
                    "symbol": pair,
                    "price": 1.27 if pair == "GBPUSD" else 1.0,
                    "source_id": f"kraken:ticker:{pair}",
                    "source_timestamp": time.time(),
                    "received_at": time.time(),
                    "truth_status": "real_observed",
                    "generated_values": False,
                }
            ),
        })()

        snapshot = trader._get_capital_snapshot()

        self.assertAlmostEqual(snapshot["equity"], 132.0)
        self.assertAlmostEqual(snapshot["spot_value_usd"], 132.0)
        self.assertAlmostEqual(snapshot["spot_cash_usd"], 132.0)
        self.assertEqual(snapshot["portfolio_value_source"], "spot_balance")
        self.assertEqual(snapshot["balance_snapshot"]["balances"]["GBP"]["amount"], 100.0)

    def test_margin_fast_profit_capture_uses_true_net_after_fees_and_collateral_snapshot(self):
        trader = KrakenMarginArmyTrader.__new__(KrakenMarginArmyTrader)
        trader.dry_run = False
        trader._last_fast_profit_capture = {}
        trader._fast_profit_capture_by_order = {}
        trader.client = type("ClientStub", (), {
            "get_trade_balance": staticmethod(
                lambda: _trade_balance_receipt(
                    equity=100.0,
                    free_margin=72.0,
                    margin_amount=20.0,
                    unrealized_pnl=0.05,
                    margin_level=360.0,
                )
            )
        })()
        trade = ActiveTrade(
            pair="BTC/USD",
            side="buy",
            volume=0.01,
            entry_price=100.0,
            leverage=3,
            entry_fee=0.01,
            entry_time=1_700_000_000.0,
            order_id="MFAST",
            cost=1.0,
            breakeven_price=101.0,
            binance_symbol="BTCUSDT",
        )

        decision = trader._kraken_margin_fast_profit_capture_decision(
            trade,
            current_price=101.0,
            net_pnl=0.055,
            validated_net_pnl=0.04,
            total_fees=0.02,
            exit_fee=0.01,
            rollover=0.0,
            stream_live=True,
        )

        self.assertTrue(decision["ready_to_capture"], decision)
        self.assertEqual(decision["reason"], "capture_true_profit_after_costs")
        self.assertEqual(decision["costs"]["total_costs_usd"], 0.02)
        self.assertEqual(decision["collateral"]["margin_level"], 360.0)
        self.assertIn("MFAST", trader._fast_profit_capture_by_order)

    def test_validator_required_move_pct_uses_trade_profit_validator_when_available(self):
        trader = KrakenMarginArmyTrader.__new__(KrakenMarginArmyTrader)
        trader.trade_profit_validator = type("ValidatorStub", (), {
            "get_exchange_costs": staticmethod(lambda exchange, value, is_taker=True, symbol="": {
                "total": 2.0,
            })
        })()
        trader._validator_snapshot = {}

        required_move_pct, round_trip_cost = trader._validator_required_move_pct(
            trade_value=100.0,
            profit_target_usd=1.27,
            symbol="BTC/USD",
        )

        self.assertAlmostEqual(round_trip_cost, 4.0)
        self.assertAlmostEqual(required_move_pct, 5.27)
        self.assertEqual(trader._validator_snapshot["source"], "validator")

    def test_apply_brain_gate_to_candidates_filters_rejected_entries(self):
        trader = KrakenMarginArmyTrader.__new__(KrakenMarginArmyTrader)

        class BrainStub:
            def decide(self, symbol, base_score, features, population_scores):
                if symbol == "ETH/USD":
                    return None
                return type("Decision", (), {"score": base_score + 1.5, "coherence": 0.81})()

        trader.signal_brain = BrainStub()
        trader._brain_snapshot = {}
        info1 = type("Info", (), {"pair": "BTC/USD", "momentum": 1.2, "spread_pct": 0.1})()
        info2 = type("Info", (), {"pair": "ETH/USD", "momentum": 0.8, "spread_pct": 0.1})()
        candidates = [
            (info1, "buy", 1.0, 100.0, 5, 4.0, 1.1, 0.5, 1.0, 10.0, 0.8),
            (info2, "buy", 1.0, 100.0, 5, 3.5, 1.0, 0.5, 0.9, 12.0, 0.7),
        ]

        gated = trader._apply_brain_gate_to_candidates(candidates)

        self.assertEqual(len(gated), 1)
        self.assertEqual(gated[0][0].pair, "BTC/USD")
        self.assertAlmostEqual(gated[0][5], 5.5)
        self.assertEqual(trader._brain_snapshot["ETH/USD"]["decision"], "rejected")

    def test_validated_net_pnl_subtracts_slippage_and_spread_buffer(self):
        trader = KrakenMarginArmyTrader.__new__(KrakenMarginArmyTrader)
        trader.trade_profit_validator = type("ValidatorStub", (), {
            "get_exchange_costs": staticmethod(lambda exchange, value, is_taker=True, symbol="": {
                "slippage": 0.2,
                "spread": 0.3,
            })
        })()

        validated = trader._validated_net_pnl("BTC/USD", exit_value=100.0, net_pnl=2.0)

        self.assertAlmostEqual(validated, 1.5)

    def test_close_margin_position_returns_no_position_instead_of_volume_zero(self):
        client = KrakenClient.__new__(KrakenClient)
        client.dry_run = False
        client.get_open_margin_positions = lambda do_calcs=False: []
        client._resolve_pair = lambda symbol: ("XBTUSD", {"lot_decimals": 8})

        result = client.close_margin_position("BTC/USD", side="sell", volume=None)

        self.assertEqual(result, {"error": "no_position", "symbol": "BTC/USD"})

    def test_load_state_reconciles_live_kraken_positions_without_local_state_file(self):
        trader = KrakenMarginArmyTrader.__new__(KrakenMarginArmyTrader)
        trader.dry_run = False
        trader.active_long = None
        trader.active_short = None
        trader.active_trade = None
        trader.total_profit = 0
        trader.total_trades = 0
        trader.winning_trades = 0
        trader.shadow_validated_count = 0
        trader.shadow_failed_count = 0
        trader.completed_trades = []
        trader.orchestrator = None
        trader._start_stream_for = lambda symbol: None
        trader._save_state = lambda: None
        trader._binance_symbol_for_pair = lambda pair: "BTCUSDT"
        trader.client = type("ClientStub", (), {})()
        trader.client._int_to_alt = {"XXBTZUSD": "BTC/USD"}
        trader.client.get_open_margin_positions = lambda do_calcs=True: [{
            "pair": "XXBTZUSD",
            "side": "buy",
            "volume": 0.01,
            "cost": 850.0,
            "fee": 3.0,
            "open_time": 1700000000.0,
            "position_id": "P123",
            "leverage": "5",
        }]

        with patch("aureon.exchanges.kraken_margin_penny_trader.os.path.exists", return_value=False):
            trader._load_state()

        self.assertIsNotNone(trader.active_long)
        self.assertIsNone(trader.active_short)
        self.assertEqual(trader.active_long.pair, "BTC/USD")
        self.assertEqual(trader.active_long.side, "buy")
        self.assertEqual(trader.active_long.order_id, "P123")
        self.assertGreater(trader.active_long.breakeven_price, trader.active_long.entry_price)

    def test_dynamic_margin_plan_uses_live_free_margin_for_tiny_accounts(self):
        trader = KrakenMarginArmyTrader.__new__(KrakenMarginArmyTrader)
        trader.dry_run = False
        trader.dynamic_sizer = DynamicMarginSizer(DynamicMarginConfig())
        trader.client = type("ClientStub", (), {
            "get_trade_balance": staticmethod(
                lambda: _trade_balance_receipt(equity=10.0, free_margin=10.0)
            )
        })()
        pair = MarginPairInfo(
            pair="DOGE/USD",
            internal="XDGUSD",
            base="XXDG",
            base_clean="DOGE",
            quote="USD",
            leverage_buy=[2, 3, 5],
            leverage_sell=[2, 3, 5],
            max_leverage=5,
            ordermin=1.0,
            costmin=5.0,
            lot_decimals=4,
            price_decimals=5,
            binance_symbol="DOGEUSDT",
            last_price=1.0,
        )

        plan = trader._plan_dynamic_margin_position(pair, 5)

        self.assertTrue(plan.approved, plan.reason)
        self.assertGreaterEqual(plan.notional, 5.0)
        self.assertLess(plan.profit_target_usd, 1.27)

    def test_trade_cognition_plan_records_expected_human_time(self):
        trader = KrakenMarginArmyTrader.__new__(KrakenMarginArmyTrader)
        trader.temporal_cognition = TemporalTradeCognition()
        trader.thought_bus = None
        pair = MarginPairInfo(
            pair="DOGE/USD",
            internal="XDGUSD",
            base="XXDG",
            base_clean="DOGE",
            quote="USD",
            leverage_buy=[5],
            leverage_sell=[5],
            max_leverage=5,
            ordermin=1.0,
            costmin=5.0,
            lot_decimals=4,
            price_decimals=5,
            binance_symbol="DOGEUSDT",
            last_price=1.0,
        )

        plan = trader._build_trade_cognition_plan(
            pair_info=pair,
            side="buy",
            entry_price=1.0,
            target_price=1.01,
            trade_value=10.0,
            profit_target_usd=0.10,
            cognition_context={
                "required_move_pct": 1.0,
                "eta_minutes": 3.0,
                "confidence": 0.75,
            },
        )

        self.assertEqual(plan["pair"], "DOGE/USD")
        self.assertAlmostEqual(plan["eta_minutes"], 3.0)
        self.assertEqual(
            plan["expected_by"]["epoch"] - plan["opened_at"]["epoch"],
            180.0,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
