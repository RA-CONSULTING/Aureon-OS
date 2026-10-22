#!/usr/bin/env python3
import unittest

from aureon.exchanges.kraken_margin_penny_trader import KrakenMarginArmyTrader
from aureon.trading.unified_margin_brain import (
    MarginBrainConfig,
    UnifiedMarginDecisionBrain,
)


class TestUnifiedMarginBrain(unittest.TestCase):
    def test_brain_approves_candidate_with_eta_probability_and_cost_support(self):
        brain = UnifiedMarginDecisionBrain(MarginBrainConfig(max_eta_minutes=15.0, hard_eta_minutes=45.0))

        decision = brain.evaluate_candidate(
            {
                "pair": "BTC/USD",
                "side": "buy",
                "score": 8.0,
                "required_move_pct": 0.42,
                "estimated_fees": 0.04,
                "goal_score": 2.4,
                "eta_minutes": 3.0,
                "route_to_profit": 5.7,
                "spread_pct": 0.04,
                "profit_target_usd": 0.10,
            },
            {
                "confidence": 0.82,
                "probability": 0.78,
                "sources": {
                    "projection": {"confidence": 0.80, "live_match": 0.72},
                    "timeline": {"confidence": 0.70},
                    "alignment": {"score": 0.65},
                },
            },
            population_scores=[2.0, 5.0, 8.0],
            now=1_700_000_000.0,
        )

        self.assertTrue(decision.approved, decision.vetoes)
        self.assertEqual(decision.action, "approve_shadow")
        self.assertGreater(decision.confidence, 0.5)
        self.assertLess(decision.risk, 0.82)
        self.assertEqual(decision.decided_at["epoch"], 1_700_000_000.0)

    def test_brain_rejects_unbounded_or_slow_eta(self):
        brain = UnifiedMarginDecisionBrain(MarginBrainConfig(max_eta_minutes=15.0, hard_eta_minutes=45.0))

        decision = brain.evaluate_candidate(
            {
                "pair": "ETH/USD",
                "side": "sell",
                "score": 8.0,
                "required_move_pct": 0.35,
                "estimated_fees": 0.02,
                "goal_score": 2.0,
                "eta_minutes": 90.0,
                "route_to_profit": 5.0,
                "spread_pct": 0.04,
                "profit_target_usd": 0.10,
            },
            {"confidence": 0.90, "probability": 0.80},
            population_scores=[8.0],
        )

        self.assertFalse(decision.approved)
        self.assertIn("eta_too_slow", decision.vetoes)
        self.assertEqual(decision.action, "wait")

    def test_trader_final_gate_stores_brain_decision_on_cognition_context(self):
        trader = KrakenMarginArmyTrader.__new__(KrakenMarginArmyTrader)
        trader.signal_brain = None
        trader.margin_decision_brain = UnifiedMarginDecisionBrain(
            MarginBrainConfig(max_eta_minutes=15.0, hard_eta_minutes=45.0)
        )
        trader._brain_snapshot = {}
        trader._margin_brain_decisions = {}
        trader._candidate_cognition_context = {}
        trader.thought_bus = None

        info_fast = type("Info", (), {"pair": "BTC/USD", "momentum": 1.2, "spread_pct": 0.05})()
        info_slow = type("Info", (), {"pair": "ETH/USD", "momentum": 1.1, "spread_pct": 0.05})()
        trader._candidate_cognition_context["btc/usd|buy"] = {
            "confidence": 0.82,
            "probability": 0.78,
            "profit_target_usd": 0.10,
            "sources": {
                "projection": {"confidence": 0.80, "live_match": 0.72},
                "timeline": {"confidence": 0.70},
                "alignment": {"score": 0.65},
            },
        }
        trader._candidate_cognition_context["eth/usd|buy"] = {
            "confidence": 0.85,
            "probability": 0.80,
            "profit_target_usd": 0.10,
        }
        candidates = [
            (info_fast, "buy", 1.0, 100.0, 5, 8.0, 0.42, 0.04, 2.4, 3.0, 5.7),
            (info_slow, "buy", 1.0, 100.0, 5, 7.0, 0.42, 0.04, 2.2, 90.0, 5.0),
        ]

        gated = trader._apply_brain_gate_to_candidates(candidates)

        self.assertEqual(len(gated), 1)
        self.assertEqual(gated[0][0].pair, "BTC/USD")
        self.assertTrue(trader._candidate_cognition_context["btc/usd|buy"]["brain_decision"]["approved"])
        self.assertFalse(trader._candidate_cognition_context["eth/usd|buy"]["brain_decision"]["approved"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
