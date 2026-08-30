import os
import time
import unittest
from datetime import datetime, timezone

os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")

from aureon.exchanges import alpaca_capital_style_trader as trader_mod


def _provider_time(offset_seconds=0.0):
    return datetime.fromtimestamp(time.time() + offset_seconds, tz=timezone.utc).isoformat().replace("+00:00", "Z")


class FakeThought:
    def __init__(self, source, topic, payload, meta=None):
        self.source = source
        self.topic = topic
        self.payload = payload
        self.meta = meta or {}


class FakeThoughtBus:
    def __init__(self):
        self.events = []

    def publish(self, thought):
        self.events.append(thought)

    def recall(self, prefix, limit=8):
        matches = [event for event in self.events if event.topic.startswith(prefix)]
        return [{"topic": event.topic} for event in matches[-limit:]]


class FakeBrain:
    def decide(self, symbol, score, features, history):
        class Decision:
            def __init__(self, value):
                self.score = value

        return Decision(score)

    def learn_from_outcome(self, symbol, pnl, confidence):
        return {"symbol": symbol, "symbol_bias": 0.42, "confidence": confidence}

    def learning_snapshot(self):
        return {"total_feedback": 1, "win_bias": 0.42}


class FakeOrchestrator:
    def gate_pre_trade(self, symbol, side):
        return True, "test_proven_gate", {"symbol": symbol, "side": side}


class FailingOrchestrator:
    def gate_pre_trade(self, symbol, side):
        raise RuntimeError("provider-independent gate failure")


class CountingTrader(trader_mod.AlpacaCapitalStyleTrader):
    def __init__(self):
        self.timeline_calls = []
        self.fusion_calls = []
        self.orchestrator_calls = []
        super().__init__()

    def _score_timeline_oracle(self, symbol, side, price, change_pct, volume, source_timestamp=None):
        self.timeline_calls.append(symbol)
        return {
            "bonus": 0.0,
            "action": "hold",
            "confidence": 0.0,
            "reason": "test",
            "truth_status": "real_derived",
            "source_timestamp": source_timestamp,
            "generated_values": False,
        }

    def _score_harmonic_fusion(self, symbol, side):
        self.fusion_calls.append(symbol)
        return {"bonus": 0.0, "global_coherence": 0.0, "symbol_coherence": 0.0}

    def _orchestrator_pretrade_gate(self, symbol, side):
        self.orchestrator_calls.append(symbol)
        return {"symbol": symbol, "side": side, "approved": True, "reason": "test", "sizing": {}}


class FakeAlpacaClient:
    def __init__(self):
        self.is_authenticated = True
        self.shortable = {"AAPL": True, "MSFT": True, "QQQ": True, "IWM": True}
        self.position_rows = []
        self.orders = []
        self.next_order_result = None
        quote_time = _provider_time()
        daily_time = _provider_time(-60.0)
        previous_time = _provider_time(-86400.0)
        self.snapshots = {
            "AAPL": {
                "latestQuote": {"bp": 100.0, "ap": 100.02, "t": quote_time},
                "dailyBar": {"c": 100.01, "v": 10000, "t": daily_time},
                "prevDailyBar": {"c": 99.0, "t": previous_time},
            },
            "MSFT": {
                "latestQuote": {"bp": 200.0, "ap": 200.03, "t": quote_time},
                "dailyBar": {"c": 200.01, "v": 10000, "t": daily_time},
                "prevDailyBar": {"c": 199.0, "t": previous_time},
            },
            "QQQ": {
                "latestQuote": {"bp": 300.0, "ap": 300.05, "t": quote_time},
                "dailyBar": {"c": 300.02, "v": 10000, "t": daily_time},
                "prevDailyBar": {"c": 299.0, "t": previous_time},
            },
            "IWM": {
                "latestQuote": {"bp": 400.0, "ap": 400.06, "t": quote_time},
                "dailyBar": {"c": 400.03, "v": 10000, "t": daily_time},
                "prevDailyBar": {"c": 399.0, "t": previous_time},
            },
        }

    def get_tradable_stock_symbols(self):
        return ["AAPL", "MSFT", "QQQ", "IWM"]

    def get_stock_snapshots(self, symbols):
        return {symbol: self.snapshots.get(symbol, {}) for symbol in symbols}

    def is_shortable(self, symbol):
        return self.shortable.get(symbol, False)

    def get_positions(self):
        return list(self.position_rows)

    def place_market_order(self, symbol, side, quantity=1):
        self.orders.append((symbol, side, quantity))
        if self.next_order_result is not None:
            result = self.next_order_result
            self.next_order_result = None
            return result
        snapshot = self.snapshots.get(symbol, {})
        quote = snapshot.get("latestQuote", {})
        price = quote.get("ap") if side == "buy" else quote.get("bp")
        if price is None:
            matching_position = next((row for row in self.position_rows if row.get("symbol") == symbol), {})
            price = matching_position.get("current_price")
        return {
            "id": f"{symbol}-{side}-{len(self.orders)}",
            "status": "filled",
            "symbol": symbol,
            "side": side,
            "asset_class": "us_equity",
            "filled_qty": str(quantity),
            "filled_avg_price": str(price),
            "filled_at": _provider_time(),
            "fee_receipt_complete": True,
            "total_fee_usd": "0.01",
            "fee_source_id": f"test_fee_activity:{symbol}:{len(self.orders)}",
            "fee_source_timestamp": _provider_time(),
        }

    def get_account(self):
        return {"equity": 1000.0, "cash": 800.0, "buying_power": 4000.0, "updated_at": _provider_time()}


class AlpacaCapitalStyleTests(unittest.TestCase):
    def _make_trader(self):
        trader = trader_mod.AlpacaCapitalStyleTrader()
        trader.unified_registry = None
        trader.unified_decision_engine = None
        trader.orchestrator = FakeOrchestrator()
        trader.timeline_oracle = None
        trader.harmonic_fusion = None
        for symbol in trader.universe:
            self.assertTrue(trader.record_execution_cost_receipt(symbol, {
                "total_cost_pct": 0.05,
                "sample_count": 3,
                "truth_status": "real_observed",
                "source_id": f"test_execution_cost_activity:{symbol}",
                "source_timestamp": time.time(),
                "generated_values": False,
            }))
        return trader

    def setUp(self):
        self.orig_client = trader_mod.AlpacaClient
        self.orig_thought = trader_mod.Thought
        self.orig_intel_top_n = trader_mod.ALPACA_INTEL_TOP_N
        trader_mod.AlpacaClient = FakeAlpacaClient
        trader_mod.Thought = FakeThought

    def tearDown(self):
        trader_mod.AlpacaClient = self.orig_client
        trader_mod.Thought = self.orig_thought
        trader_mod.ALPACA_INTEL_TOP_N = self.orig_intel_top_n

    def test_tick_uses_shadow_before_live_promotion(self):
        trader = self._make_trader()
        trader._signal_brain = FakeBrain()
        trader.tick()
        self.assertEqual(len(trader.shadow_trades), 1)
        self.assertEqual(len(trader.positions), 0)

        shadow = trader.shadow_trades[0]
        shadow.opened_at = time.time() - 10.0
        live_price = shadow.entry_price * 1.01
        trader.client.snapshots["AAPL"]["latestQuote"] = {
            "bp": live_price - 0.01,
            "ap": live_price + 0.01,
            "t": _provider_time(),
        }
        trader.client.snapshots["AAPL"]["dailyBar"] = {
            "c": live_price,
            "v": 10000,
            "t": _provider_time(-60.0),
        }
        trader._last_monitor = 0.0
        trader.tick()

        self.assertEqual(len(trader.positions), 1)
        self.assertEqual(len(trader.shadow_trades), 0)
        self.assertEqual(trader.positions[0].symbol, "AAPL")

    def test_close_position_publishes_learning(self):
        trader = self._make_trader()
        trader._signal_brain = FakeBrain()
        trader.thought_bus = FakeThoughtBus()
        position = trader_mod.AlpacaMomentumPosition(
            symbol="AAPL",
            order_id="test-order",
            direction="BUY",
            qty=1.0,
            entry_price=100.0,
            tp_price=101.0,
            sl_price=99.0,
            current_price=101.5,
            entry_source_id="alpaca_order:test-entry",
            entry_source_timestamp=time.time() - 60.0,
            entry_received_at=time.time() - 59.0,
            entry_commission_usd=0.01,
            entry_fee_complete=True,
            entry_reference_price=100.0,
            entry_spread_usd=0.01,
            eligible_for_learning=True,
        )
        trader.client.snapshots["AAPL"]["latestQuote"] = {"bp": 101.49, "ap": 101.51, "t": _provider_time()}
        trader._refresh_prices()
        record = trader._close_position(position, "TP_HIT")

        self.assertIsNotNone(record)
        self.assertIn("learning_update", record)
        topics = [event.topic for event in trader.thought_bus.events]
        self.assertIn("brain.learning", topics)
        self.assertIn("queen.learning", topics)

    def test_free_existing_assets_closes_spot_positions(self):
        trader = self._make_trader()
        trader.client.position_rows = [
            {"symbol": "AAPL", "qty": "2", "avg_entry_price": "100", "current_price": "101"},
            {"symbol": "TSLA", "qty": "-1", "avg_entry_price": "200", "current_price": "199"},
        ]

        liquidated = trader.free_existing_assets()

        self.assertEqual(len(liquidated), 2)
        self.assertEqual(trader.client.orders[0], ("AAPL", "sell", 2.0))
        self.assertEqual(trader.client.orders[1], ("TSLA", "buy", 1.0))

    def test_build_universe_uses_tradable_stock_discovery(self):
        trader = self._make_trader()

        self.assertIn("IWM", trader.universe)
        self.assertIn("MSFT", trader.universe)
        self.assertGreaterEqual(len(trader.universe), 4)
        self.assertEqual(trader._universe_snapshot.get("mode"), "live")

    def test_dashboard_exposes_capital_style_coordination_surfaces(self):
        trader = self._make_trader()
        trader._signal_brain = FakeBrain()
        trader.tick()

        payload = trader.get_dashboard_payload()

        self.assertIn("swarm_snapshot", payload)
        self.assertIn("registry_snapshot", payload)
        self.assertIn("decision_snapshot", payload)
        self.assertIn("orchestrator_snapshot", payload)
        self.assertTrue(payload["swarm_snapshot"].get("enabled"))

    def test_dashboard_exposes_harmonic_surfaces(self):
        trader = self._make_trader()
        trader._signal_brain = FakeBrain()
        trader.tick()

        payload = trader.get_dashboard_payload()

        self.assertIn("timeline_snapshot", payload)
        self.assertIn("fusion_snapshot", payload)
        self.assertIn("harmonic_wiring_audit", payload)

    def test_dashboard_exposes_universe_snapshot(self):
        trader = self._make_trader()

        payload = trader.get_dashboard_payload()

        self.assertIn("universe_snapshot", payload)
        self.assertEqual(payload["universe_snapshot"].get("mode"), "live")

    def test_refresh_prices_rotates_scan_window(self):
        orig_scan_window = trader_mod.ALPACA_SCAN_WINDOW
        trader_mod.ALPACA_SCAN_WINDOW = 2
        trader = self._make_trader()
        trader._refresh_prices()
        first = dict(trader._scan_window_snapshot)
        trader._refresh_prices()
        second = dict(trader._scan_window_snapshot)

        self.assertEqual(first.get("size"), min(trader_mod.ALPACA_SCAN_WINDOW, len(trader.universe)))
        self.assertNotEqual(first.get("start"), second.get("start"))
        trader_mod.ALPACA_SCAN_WINDOW = orig_scan_window

    def test_symbol_quality_filter_rejects_dotted_preferred_like_names(self):
        trader = self._make_trader()

        self.assertFalse(trader._is_symbol_quality_ok("RC.PRC"))
        self.assertFalse(trader._is_symbol_quality_ok("RITM.PRE"))
        self.assertTrue(trader._is_symbol_quality_ok("AAPL"))

    def test_refresh_prices_rejects_crossed_quotes(self):
        trader = self._make_trader()
        trader._prices["AAPL"] = {"price": 100.0, "bid": 100.0, "ask": 100.1, "change_pct": 0.0}
        trader.client.snapshots["AAPL"]["latestQuote"] = {"bp": 101.0, "ap": 100.0, "t": _provider_time()}

        trader._refresh_prices()

        self.assertNotIn("AAPL", trader._prices)

    def test_refresh_prices_rejects_low_dollar_volume(self):
        trader = self._make_trader()
        trader.client.snapshots["AAPL"]["dailyBar"] = {"c": 100.01, "v": 10, "t": _provider_time(-60.0)}

        trader._refresh_prices()

        self.assertNotIn("AAPL", trader._prices)

    def test_refresh_prices_rejects_missing_provider_timestamp(self):
        trader = self._make_trader()
        trader.client.snapshots["AAPL"]["latestQuote"].pop("t")

        trader._refresh_prices()

        self.assertNotIn("AAPL", trader._prices)
        self.assertEqual(trader._price_failures["AAPL"]["truth_status"], "no_data")
        self.assertFalse(trader._price_failures["AAPL"]["eligible_for_external_action"])

    def test_accepted_order_is_quarantined_not_recorded_as_position(self):
        trader = self._make_trader()
        trader._refresh_prices()
        trader.client.next_order_result = {
            "id": "provider-pending-order",
            "status": "accepted",
            "symbol": "AAPL",
            "side": "buy",
            "submitted_at": _provider_time(),
        }

        position = trader._open_position(
            "AAPL",
            {**trader.universe["AAPL"], "direction": "BUY"},
            trader._prices["AAPL"],
        )

        self.assertIsNone(position)
        self.assertEqual(trader.positions, [])
        self.assertIn("open:AAPL", trader._pending_orders)
        self.assertFalse(trader._pending_orders["open:AAPL"]["eligible_for_learning"])

    def test_monitor_keeps_position_when_close_fill_is_unconfirmed(self):
        trader = self._make_trader()
        trader._refresh_prices()
        position = trader_mod.AlpacaMomentumPosition(
            symbol="AAPL",
            order_id="entry-order",
            direction="BUY",
            qty=1.0,
            entry_price=99.0,
            tp_price=100.0,
            sl_price=98.0,
            opened_at=time.time() - 60.0,
            current_price=100.01,
            entry_source_id="alpaca_order:entry-order",
            entry_source_timestamp=time.time() - 60.0,
            entry_received_at=time.time() - 59.0,
            generated_values=False,
        )
        trader.positions = [position]
        trader.client.next_order_result = {
            "id": "provider-close-pending",
            "status": "accepted",
            "symbol": "AAPL",
            "side": "sell",
            "submitted_at": _provider_time(),
        }

        closed = trader._monitor_positions()

        self.assertEqual(closed, [])
        self.assertEqual(trader.positions, [position])
        self.assertIn("close:AAPL", trader._pending_orders)

    def test_open_blocks_without_provider_execution_cost_receipt(self):
        trader = self._make_trader()
        trader._refresh_prices()
        trader._execution_cost_receipts.clear()

        position = trader._open_position(
            "AAPL",
            {**trader.universe["AAPL"], "direction": "BUY"},
            trader._prices["AAPL"],
        )

        self.assertIsNone(position)
        self.assertEqual(trader.client.orders, [])
        self.assertIn("execution-cost receipt unavailable", trader._latest_order_error)

    def test_orchestrator_unavailable_or_exception_fails_closed(self):
        trader = self._make_trader()
        trader.orchestrator = None
        unavailable = trader._orchestrator_pretrade_gate("AAPL", "BUY")
        trader.orchestrator = FailingOrchestrator()
        failed = trader._orchestrator_pretrade_gate("AAPL", "BUY")

        self.assertFalse(unavailable["approved"])
        self.assertEqual(unavailable["truth_status"], "no_data")
        self.assertFalse(failed["approved"])
        self.assertEqual(failed["truth_status"], "no_data")

    def test_probability_surface_is_no_data_without_receipt(self):
        trader = self._make_trader()

        receipt = trader._probability_validation_snapshot(force=True)

        self.assertFalse(receipt["ok"])
        self.assertIsNone(receipt["direction_accuracy"])
        self.assertIsNone(receipt["profit_factor"])
        self.assertEqual(receipt["truth_status"], "no_data")
        self.assertFalse(receipt["eligible_for_external_action"])

    def test_intelligence_overlays_only_run_on_top_n_candidates(self):
        trader_mod.ALPACA_INTEL_TOP_N = 2
        trader = CountingTrader()
        trader.unified_registry = None
        trader.unified_decision_engine = None
        trader.timeline_oracle = object()
        trader.harmonic_fusion = object()
        trader.orchestrator = object()
        scored = [
            {"symbol": "AAPL", "direction": "BUY", "score": 5.0, "price": 100.0, "change_pct": 1.0},
            {"symbol": "MSFT", "direction": "BUY", "score": 4.0, "price": 200.0, "change_pct": 1.0},
            {"symbol": "QQQ", "direction": "BUY", "score": 3.0, "price": 300.0, "change_pct": 1.0},
        ]
        for item in scored:
            item.update({
                "bar_volume": 10000.0,
                "truth_status": "real_derived",
                "source_id": "test_alpaca_snapshot",
                "source_timestamp": time.time(),
                "received_at": time.time(),
                "generated_values": False,
                "eligible_for_external_action": True,
            })

        trader._apply_intelligence_overlays(scored)

        self.assertEqual(trader.timeline_calls, ["AAPL", "MSFT"])
        self.assertEqual(trader.fusion_calls, ["AAPL", "MSFT"])
        self.assertEqual(trader.orchestrator_calls, ["AAPL", "MSFT"])

    def test_score_symbol_uses_central_beat_alignment(self):
        trader = self._make_trader()
        trader._central_beat_symbols = {
            "AAPL": {"side": "BUY", "support_count": 3, "strength": 0.9},
        }
        trader._central_beat_regime = {"bias": "BUY", "confidence": 0.8}
        cfg = {"max_spread_pct": 0.2, "momentum_threshold": 0.2, "size": 1.0, "tp_pct": 0.35}
        ticker = {
            "price": 100.0,
            "bid": 99.99,
            "ask": 100.01,
            "change_pct": 0.8,
            "bar_volume": 10000.0,
            "dollar_volume": 1_000_000.0,
            "truth_status": "real_derived",
            "source_id": "test_alpaca_snapshot",
            "source_timestamp": time.time(),
            "received_at": time.time(),
            "generated_values": False,
            "eligible_for_external_action": True,
        }
        trader._prices["AAPL"] = dict(ticker)
        boosted_score, direction = trader._score_symbol("AAPL", cfg, ticker)

        trader._central_beat_symbols = {}
        trader._central_beat_regime = {}
        plain_score, _ = trader._score_symbol("AAPL", cfg, ticker)

        self.assertEqual(direction, "BUY")
        self.assertGreater(boosted_score, plain_score)


if __name__ == "__main__":
    unittest.main()
