#!/usr/bin/env python3
import unittest

from aureon.trading.dynamic_margin_sizer import (
    DynamicMarginConfig,
    DynamicMarginSizer,
    MarginCapitalSnapshot,
)


class TestDynamicMarginSizer(unittest.TestCase):
    def setUp(self):
        self.sizer = DynamicMarginSizer(
            DynamicMarginConfig(
                max_free_margin_fraction=0.70,
                tiny_account_max_free_margin_fraction=0.90,
                tiny_account_equity_usd=50.0,
                entry_min_margin_pct=250.0,
                min_free_margin_usd=5.0,
                fallback_min_notional_usd=5.0,
                min_profit_target_usd=0.05,
                target_equity_fraction=0.01,
            )
        )

    def test_trade_balance_parser_accepts_kraken_short_and_client_keys(self):
        snapshot = MarginCapitalSnapshot.from_trade_balance({
            "e": "10.50",
            "mf": "8.25",
            "m": "2.25",
            "n": "0.33",
            "ml": "466.6",
            "tb": "10.17",
        })

        self.assertAlmostEqual(snapshot.equity, 10.50)
        self.assertAlmostEqual(snapshot.free_margin, 8.25)
        self.assertAlmostEqual(snapshot.margin_used, 2.25)
        self.assertAlmostEqual(snapshot.unrealized_pnl, 0.33)
        self.assertAlmostEqual(snapshot.margin_level, 466.6)

    def test_ten_dollar_account_can_size_if_pair_minimum_fits_safely(self):
        snapshot = MarginCapitalSnapshot(equity=10.0, free_margin=10.0, margin_used=0.0)

        plan = self.sizer.plan(
            snapshot,
            price=1.0,
            ordermin=1.0,
            lot_decimals=4,
            leverage=5,
            max_profit_target_usd=1.27,
            costmin=5.0,
        )

        self.assertTrue(plan.approved, plan.reason)
        self.assertGreaterEqual(plan.notional, 5.0)
        self.assertLessEqual(plan.required_margin, 4.0)
        self.assertGreaterEqual(plan.projected_margin_pct, 250.0)
        self.assertAlmostEqual(plan.profit_target_usd, 0.10)

    def test_profit_target_scales_up_but_stays_capped(self):
        self.assertAlmostEqual(self.sizer.profit_target_usd(10.0, 1.27), 0.10)
        self.assertAlmostEqual(self.sizer.profit_target_usd(200.0, 1.27), 1.27)

    def test_pair_minimum_above_safe_room_is_rejected(self):
        snapshot = MarginCapitalSnapshot(equity=10.0, free_margin=10.0, margin_used=0.0)

        plan = self.sizer.plan(
            snapshot,
            price=1.0,
            ordermin=25.0,
            lot_decimals=4,
            leverage=5,
            max_profit_target_usd=1.27,
            costmin=25.0,
        )

        self.assertFalse(plan.approved)
        self.assertIn("safe notional", plan.reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
