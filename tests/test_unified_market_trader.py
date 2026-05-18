import os
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


os.environ.setdefault("AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS", "1")

REPO_ROOT = Path(__file__).resolve().parents[1]
EXCHANGES_DIR = REPO_ROOT / "aureon" / "exchanges"
if str(EXCHANGES_DIR) not in sys.path:
    sys.path.insert(0, str(EXCHANGES_DIR))

import unified_market_trader as trader_mod


class FeedTarget:
    def __init__(self):
        self._hive_boosts = {}
        self._central_beat_symbols = {}
        self._central_beat_regime = {}
        self.decision_feeds = []

    def _feed_unified_decision_engine(self, **kwargs):
        self.decision_feeds.append(kwargs)


class FakeMarketHarp:
    active_pluck_count = 1
    active_ripple_count = 1

    def __init__(self):
        self.last_price_map = {}

    def tick(self, price_map):
        self.last_price_map = dict(price_map)
        return {"ETHUSD": 0.72}

    def status_lines(self):
        return ["MARKET HARP: fake resonance active"]

    def cross_class_summary(self):
        return ["HARP CROSS-CLASS: fake crypto ripple"]


class FakeCrossAssetCorrelator:
    def __init__(self):
        self.last_changes = {}

    def update_batch(self, symbol_to_change):
        self.last_changes = dict(symbol_to_change)

    def get_category_moves(self, symbol_to_change):
        return {"crypto": 1.1, "index": 0.4}

    def get_regime(self, symbol_to_change):
        return "RISK_ON"

    def get_pre_signals(self, symbol_to_change, symbol_to_price, symbol_to_exchange, existing_symbols):
        return [
            trader_mod.SimpleNamespace(
                leader="BTC",
                follower="SOL",
                follower_exchange="kraken",
                follower_symbol="SOL/USD",
                leader_move_pct=1.1,
                expected_move_pct=0.7,
                already_moved_pct=0.1,
                remaining_pct=0.6,
                correlation=0.82,
                lag_seconds=120,
                category="crypto",
                regime="RISK_ON",
            )
        ]


class UnifiedMarketTraderTests(unittest.TestCase):
    def _make_trader(self):
        trader = trader_mod.UnifiedMarketTrader.__new__(trader_mod.UnifiedMarketTrader)
        trader.kraken = FeedTarget()
        trader.capital = FeedTarget()
        trader.alpaca = FeedTarget()
        trader.binance = FeedTarget()
        trader.alpaca_trader = None
        trader.binance_trader = None
        trader.start_time = time.time()
        trader._runtime_instance_id = "test-runtime"
        trader.kraken_ready = False
        trader.capital_ready = False
        trader.kraken_error = ""
        trader.capital_error = ""
        trader.alpaca_error = ""
        trader.binance_error = ""
        trader._last_auris_feed_at = 0.0
        trader._binance_diag = {}
        trader._shared_market_feed = {}
        trader._shared_market_feed_at = 0.0
        trader._central_beat_feed = {}
        trader._central_beat_at = 0.0
        trader._central_beat_layers = {"trader": {}, "probe": {}, "merged": {}}
        trader._central_beat_history = []
        trader._central_source_memory = {}
        trader._stream_cache_health = {}
        trader._orderbook_pressure_cache = {}
        trader._fast_money_intelligence = {}
        trader._dynamic_intelligence_budget = {}
        trader._world_ecosystem_intelligence = {}
        trader._world_ecosystem_at = 0.0
        trader._world_macro_snapshot_cache = {}
        trader._world_macro_snapshot_at = 0.0
        trader._world_macro_fetch_inflight = False
        trader._asset_waveform_models = {}
        trader._central_beat_heavy_context_enabled = True
        trader._scanner_fusion_matrix = {}
        trader._market_harp = None
        trader._cross_asset_correlator = None
        trader._world_macro_provider = lambda: {}
        trader._world_news_signal_provider = lambda: {}
        trader._extract_stream_cache_source_snapshot = lambda watchlist: {}  # type: ignore[method-assign]
        trader._gold_priority_live_stream_signal = lambda: {"ready": False, "reason": "test_default_no_gold_stream"}  # type: ignore[method-assign]
        trader._build_asset_waveform_models = lambda normalized_symbols, sources: {  # type: ignore[method-assign]
            "schema_version": 1,
            "enabled": True,
            "decision_symbols": {},
            "fed_to_decision_logic": False,
        }
        trader._last_tick_started_at = 0.0
        trader._last_tick_completed_at = 0.0
        trader._last_tick_error = ""
        trader._last_order_intent_at = 0.0
        trader._last_order_intent_signature = ""
        trader._latest_order_intents = {}
        trader._last_execution_at = 0.0
        trader._execution_memory = {}
        trader._latest_execution_results = {}
        trader._order_lifecycle_enabled = False
        trader._order_lifecycle_started = False
        trader._executor_route_lock = trader_mod.threading.Lock()
        trader._executor_route_inflight = {}
        trader._executor_route_results = {}
        trader._capital_tick_lock = trader_mod.threading.Lock()
        trader._capital_tick_inflight = {}
        trader._latest_capital_tick_state = {}
        trader._exchange_dashboard_lock = trader_mod.threading.Lock()
        trader._exchange_dashboard_inflight = {}
        trader._latest_exchange_dashboard_state = {}
        trader._latest_exchange_dashboard_payloads = {}
        trader._tick_phase = "idle"
        trader._tick_phase_at = time.time()
        trader._thought_bus = None
        trader._mycelium = None
        trader._api_governor = trader_mod.ExchangeCallGovernor()
        return trader

    def _with_live_executor_env(self):
        keys = {
            "AUREON_LIVE_TRADING": "1",
            "AUREON_AUDIT_MODE": "0",
            "AUREON_DISABLE_REAL_ORDERS": "0",
            "AUREON_DISABLE_EXCHANGE_MUTATIONS": "0",
            "DRY_RUN": "0",
            "AUREON_ORDER_INTENT_PUBLISH": "1",
            "AUREON_UNIFIED_ORDER_EXECUTOR": "1",
            "BINANCE_MARGIN_ENABLED": "true",
        }
        old = {key: os.environ.get(key) for key in keys}
        os.environ.update(keys)
        return old

    def _restore_env(self, old):
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_central_beat_merges_sources_into_symbol_metrics(self):
        trader = self._make_trader()
        kraken_payload = {
            "ok": True,
            "candidate_snapshot": [{"symbol": "XBT/USD", "side": "buy", "score": 0.8}],
            "decision_snapshot": {"symbol": "XBT/USD", "side": "buy", "decision": {"confidence": 0.9}},
        }
        capital_payload = {
            "ok": True,
            "candidate_snapshot": [{"symbol": "BTCUSD", "direction": "BUY", "score": 0.7}],
            "target_snapshot": {"symbol": "BTCUSD", "direction": "BUY", "score": 0.85},
        }

        beat = trader._build_central_beat_feed(kraken_payload, capital_payload)

        self.assertEqual(beat["source_count"], 2)
        self.assertIn("BTCUSD", beat["symbols"])
        self.assertEqual(beat["symbols"]["BTCUSD"]["side"], "BUY")
        self.assertGreaterEqual(beat["symbols"]["BTCUSD"]["support_count"], 2)
        self.assertTrue(beat["model_signal_feed"]["used"])
        self.assertIn("model_signal", beat["symbols"]["BTCUSD"])

    def test_world_financial_ecosystem_feeds_central_beat_decision_symbols(self):
        trader = self._make_trader()
        trader._market_harp = FakeMarketHarp()
        trader._cross_asset_correlator = FakeCrossAssetCorrelator()
        trader._world_macro_provider = lambda: {
            "timestamp": trader_mod.datetime.now().isoformat(),
            "risk_on_off": "RISK_ON",
            "market_regime": "BULLISH",
            "crypto_fear_greed": 72,
            "vix": 14.0,
            "source": "test_macro",
        }
        trader._world_news_signal_provider = lambda: {
            "fetched_at": trader_mod.datetime.now().isoformat(),
            "sentiment": 0.4,
            "headline_count": 8,
            "themes": ["crypto", "macro"],
            "summary": "risk-on news",
        }
        trader._extract_stream_cache_source_snapshot = lambda watchlist: {  # type: ignore[method-assign]
            "source": "live_stream_cache",
            "ready": True,
            "symbols": {
                "BTCUSD": {
                    "symbol": "BTCUSD",
                    "raw_symbol": "BTCUSDT",
                    "confidence": 0.66,
                    "side": "BUY",
                    "price": 50000.0,
                    "change_pct": 1.1,
                    "age_sec": 0.4,
                    "volume_24h": 1_000_000_000.0,
                }
            },
        }
        kraken_payload = {
            "ok": True,
            "candidate_snapshot": [{"symbol": "BTC/USD", "side": "BUY", "score": 0.8}],
        }

        beat = trader._build_central_beat_feed(kraken_payload, {"ok": False})

        self.assertIn("world_financial_ecosystem", [source["source"] for source in beat["sources"]])
        self.assertTrue(beat["world_financial_ecosystem"]["fed_to_decision_logic"])
        self.assertGreaterEqual(beat["world_financial_ecosystem"]["usable_source_count"], 3)
        self.assertIn("ETHUSD", beat["symbols"])
        self.assertIn("SOLUSD", beat["symbols"])
        self.assertIn("world_financial_ecosystem", beat["symbols"]["ETHUSD"]["sources"])
        statuses = {
            item["name"]: item["status"]
            for item in trader._build_intelligence_mesh(central_beat=beat)["capabilities"]
        }
        self.assertEqual(statuses["MarketHarp"], "active")
        self.assertEqual(statuses["CrossAssetCorrelator"], "active")
        self.assertEqual(statuses["WorldFinancialEcosystemFeed"], "active")
        self.assertEqual(statuses["NewsSignalBridge"], "active")

    def test_historical_waveform_memory_feeds_central_beat_and_mesh(self):
        trader = self._make_trader()
        trader._build_asset_waveform_models = lambda normalized_symbols, sources: {  # type: ignore[method-assign]
            "schema_version": 1,
            "enabled": True,
            "mode": "multi_horizon_asset_waveform_models",
            "usable_symbol_count": 1,
            "long_memory_ready_count": 1,
            "decision_symbol_count": 1,
            "fed_to_decision_logic": True,
            "decision_symbols": {
                "BTCUSD": {
                    "symbol": "BTCUSD",
                    "confidence": 0.72,
                    "side": "BUY",
                    "reason": "multi_horizon_historical_waveform",
                    "usable_horizon_count": 10,
                    "fast_memory_ready": True,
                    "long_memory_ready": True,
                    "directional_return_score": 1.4,
                }
            },
        }
        kraken_payload = {
            "ok": True,
            "candidate_snapshot": [{"symbol": "BTC/USD", "side": "BUY", "score": 0.6}],
        }

        beat = trader._build_central_beat_feed(kraken_payload, {"ok": False})

        self.assertIn("asset_waveform_models", beat)
        self.assertIn("historical_waveform_models", [source["source"] for source in beat["sources"]])
        self.assertIn("historical_waveform", beat["symbols"]["BTCUSD"])
        self.assertIn("historical_waveform_models", beat["symbols"]["BTCUSD"]["sources"])
        statuses = {
            item["name"]: item["status"]
            for item in trader._build_intelligence_mesh(central_beat=beat)["capabilities"]
        }
        self.assertEqual(statuses["MultiHorizonWaveformMemory"], "active")

    def test_shared_market_feed_pushes_central_metrics_to_traders(self):
        trader = self._make_trader()
        central_beat = {
            "symbols": {
                "BTCUSD": {"strength": 0.88, "confidence": 0.75, "support_count": 3, "side": "BUY", "sources": ["kraken", "capital"]},
            },
            "regime": {"bias": "BUY", "confidence": 0.7, "source_count": 2},
        }

        shared = trader._sync_shared_market_feed(central_beat)

        self.assertIn("BTCUSD", shared["symbols"])
        self.assertEqual(trader.kraken._central_beat_regime["bias"], "BUY")
        self.assertEqual(trader.capital._central_beat_symbols["BTCUSD"]["support_count"], 3)
        self.assertEqual(trader.alpaca._central_beat_symbols["BTCUSD"]["support_count"], 3)
        self.assertEqual(trader.binance._central_beat_regime["bias"], "BUY")
        self.assertGreater(trader.kraken._hive_boosts["BTCUSD"], 0.0)

    def test_central_beat_reuses_recent_source_when_probe_drops_out(self):
        trader = self._make_trader()
        trader._extract_alpaca_source_snapshot = lambda watchlist: {  # type: ignore[method-assign]
            "source": "alpaca",
            "ready": True,
            "symbols": {"BTCUSD": {"symbol": "BTCUSD", "raw_symbol": "BTC/USD", "confidence": 0.6, "side": "BUY"}},
            "top_symbol": "BTCUSD",
            "top_side": "BUY",
            "top_confidence": 0.6,
        }
        trader._extract_binance_source_snapshot = lambda watchlist: {}  # type: ignore[method-assign]

        beat1 = trader._build_central_beat_feed({"ok": False}, {"ok": False})
        self.assertEqual(beat1["source_count"], 1)
        self.assertFalse(beat1["sources"][0]["stale"])

        trader._central_beat_at = 0.0
        trader._extract_alpaca_source_snapshot = lambda watchlist: {}  # type: ignore[method-assign]
        beat2 = trader._build_central_beat_feed({"ok": False}, {"ok": False})

        self.assertEqual(beat2["source_count"], 1)
        self.assertTrue(beat2["sources"][0]["stale"])
        self.assertEqual(beat2["sources"][0]["source"], "alpaca")

    def test_stream_cache_snapshot_feeds_fresh_websocket_symbols(self):
        trader = self._make_trader()
        ticker = trader_mod.SimpleNamespace(
            symbol="BTC",
            price=50123.45,
            bid=50120.0,
            ask=50125.0,
            change_24h=1.8,
            volume_24h=2_000_000_000.0,
            source="binance_ws",
            timestamp=time.time(),
            pair="BTCUSDT",
        )
        cache = trader_mod.SimpleNamespace(get_all_tickers=lambda max_age: {"BTC": ticker})

        with patch("aureon.data_feeds.unified_market_cache.get_market_cache", return_value=cache):
            source = trader_mod.UnifiedMarketTrader._extract_stream_cache_source_snapshot(trader, ["BTCUSD"])

        self.assertEqual(source["source"], "live_stream_cache")
        self.assertTrue(source["stream_health"]["fresh"])
        self.assertIn("BTCUSD", source["symbols"])
        self.assertEqual(source["symbols"]["BTCUSD"]["price"], 50123.45)
        self.assertEqual(trader._stream_cache_health["symbol_count"], 1)

    def test_route_price_uses_stream_cache_before_rest_quote(self):
        trader = self._make_trader()
        trader._stream_price_ticker = lambda symbol, max_age=trader_mod.STREAM_CACHE_MAX_AGE_SEC: trader_mod.SimpleNamespace(price=123.45)  # type: ignore[method-assign]

        class KrakenProbe:
            def best_price(self, symbol):
                raise AssertionError("REST quote should not be called when stream price is fresh")

        trader.kraken = trader_mod.SimpleNamespace(client=KrakenProbe())

        self.assertEqual(trader._estimate_route_price("kraken", "XBTUSD"), 123.45)

    def test_shared_order_flow_preserves_sell_direction_from_central_beat(self):
        trader = self._make_trader()
        trader._kraken_tradable_symbols = lambda: {"BTCUSD": "XXBTZUSD"}  # type: ignore[method-assign]
        trader._capital_tradable_symbols = lambda: {"BTCUSD": "BTCUSD"}  # type: ignore[method-assign]
        central_beat = {
            "symbols": {
                "BTCUSD": {
                    "strength": 0.82,
                    "confidence": 0.74,
                    "support_count": 2,
                    "side": "SELL",
                    "sources": ["kraken", "capital"],
                }
            }
        }
        shared_market_feed = {"symbols": {"BTCUSD": 0.82}}

        order_flow = trader._build_global_order_flow_feed({}, {}, central_beat, shared_market_feed)

        self.assertEqual(order_flow["active_order_flow"][0]["side"], "SELL")
        self.assertEqual(order_flow["active_order_flow"][0]["support_count"], 2)

    def test_multi_exchange_order_flow_routes_all_four_venues(self):
        trader = self._make_trader()
        trader.kraken_ready = True
        trader.capital_ready = True
        trader._binance_diag = {"network_ok": True, "account_ok": True, "margin_available": True, "uk_mode": False}
        trader._kraken_tradable_symbols = lambda: {"BTCUSD": "XXBTZUSD"}  # type: ignore[method-assign]
        trader._capital_tradable_symbols = lambda: {"BTCUSD": "BTCUSD"}  # type: ignore[method-assign]
        trader._alpaca_tradable_symbols = lambda: {"BTCUSD": "BTC/USD"}  # type: ignore[method-assign]
        trader._binance_tradable_symbols = lambda: {"BTCUSD": "BTCUSDT"}  # type: ignore[method-assign]
        central_beat = {
            "symbols": {
                "BTCUSD": {
                    "strength": 0.9,
                    "confidence": 0.88,
                    "support_count": 4,
                    "side": "BUY",
                    "sources": ["kraken", "capital", "alpaca", "binance"],
                    "reference_price": 50000.0,
                    "change_pct": 1.2,
                }
            }
        }
        shared_market_feed = {"symbols": {"BTCUSD": 0.9}}

        order_flow = trader._build_global_order_flow_feed({}, {}, central_beat, shared_market_feed)
        top = order_flow["active_order_flow"][0]
        routes = {(route["venue"], route["market_type"]) for route in top["execution_routes"]}

        self.assertEqual(order_flow["active_order_flow_count"], 1)
        self.assertIn(("kraken", "spot"), routes)
        self.assertIn(("kraken", "margin"), routes)
        self.assertIn(("capital", "cfd"), routes)
        self.assertIn(("alpaca", "spot"), routes)
        self.assertIn(("binance", "spot"), routes)
        self.assertIn(("binance", "margin"), routes)
        self.assertEqual(top["ready_route_count"], 6)
        self.assertEqual(top["available_route_count"], 6)
        self.assertEqual(top["held_route_count"], 0)
        for route in top["execution_routes"]:
            self.assertGreater(route["model_count"], 0)
            self.assertTrue(route["model_coverage_ready"])
            self.assertEqual(route["trade_clearance_state"], "available")
            self.assertTrue(route["end_user_trade_available"])

        action_plan = trader._build_exchange_action_plan(order_flow)
        model_coverage = action_plan["model_coverage"]
        self.assertEqual(model_coverage["route_count"], 6)
        self.assertEqual(model_coverage["ready_route_count"], 6)
        self.assertEqual(action_plan["trade_path_state"], "runtime_clearance_pending")
        self.assertTrue(action_plan["end_user_trade_available"])

        shadow_report = trader._build_shadow_trade_report(order_flow, action_plan, persist=False)
        self.assertEqual(shadow_report["shadow_count"], 6)
        self.assertEqual(shadow_report["shadow_opened_count"], 6)
        self.assertTrue(shadow_report["self_measurement"]["all_four_exchange_routes_seen"])
        self.assertFalse(shadow_report["self_measurement"]["real_exchange_mutation"])
        self.assertIs(action_plan["shadow_trading"], shadow_report)
        for shadow in shadow_report["shadows"]:
            self.assertEqual(shadow["status"], "shadow_opened")
            self.assertFalse(shadow["real_order_submitted"])
            self.assertTrue(shadow["agent_review"]["logic_validated"])
            self.assertIn("hnc_alignment_agent", shadow["agent_review"]["agents"])
            self.assertIn("runtime_clearance_agent", shadow["agent_review"]["agents"])

    def test_gold_priority_live_stream_injects_capital_candidate(self):
        trader = self._make_trader()
        trader.capital_ready = True
        trader._capital_tradable_symbols = lambda: {"XAUUSD": "GOLD"}  # type: ignore[method-assign]
        trader._gold_priority_live_stream_signal = lambda: {  # type: ignore[method-assign]
            "ready": True,
            "normalized_symbol": "XAUUSD",
            "symbol": "GOLD",
            "capital_symbol": "GOLD",
            "reference_price": 4552.5,
            "bid": 4552.25,
            "ask": 4552.75,
            "spread": 0.5,
            "spread_pct": 0.011,
            "change_pct": 0.12,
            "volume_24h": 0.0,
            "age_sec": 1.2,
            "confidence": 0.82,
            "side": "BUY",
            "side_reason": "gold_intelligence_validated_buy_sell",
            "intent_publishable": True,
            "source_tags": [
                "capital_gold_live_stream",
                "gold_priority_target",
                "fresh_interval_validated_gold_projection_required",
            ],
        }

        order_flow = trader._build_global_order_flow_feed({}, {}, {"symbols": {}}, {"symbols": {}})

        self.assertEqual(order_flow["gold_priority_candidate"]["normalized_symbol"], "XAUUSD")
        top = order_flow["active_order_flow"][0]
        self.assertEqual(top["symbol"], "XAUUSD")
        self.assertEqual(top["capital_symbol"], "GOLD")
        self.assertEqual(top["side"], "BUY")
        self.assertTrue(top["gold_priority_candidate"])
        self.assertIn("capital_gold_live_stream", top["sources"])
        self.assertTrue(str(top["candidate_id"]).startswith("ocand-"))
        self.assertTrue(str(top["lifecycle_id"]).startswith("olife-"))
        routes = {(route["venue"], route["market_type"], route["symbol"], route["ready"]) for route in top["execution_routes"]}
        self.assertIn(("capital", "cfd", "GOLD", True), routes)
        self.assertEqual(top["execution_routes"][0]["route_key"], "capital:cfd:GOLD:BUY")
        self.assertEqual(top["execution_routes"][0]["lifecycle_id"], top["lifecycle_id"])

    def test_capital_tradables_always_include_gold_route_key(self):
        trader = self._make_trader()

        tradables = trader._capital_tradable_symbols()

        self.assertEqual(tradables["XAUUSD"], "GOLD")

    def test_gold_priority_candidate_stays_visible_above_generic_flow(self):
        trader = self._make_trader()
        trader.kraken_ready = True
        trader.capital_ready = True
        trader._kraken_spot_tradable_symbols = lambda: {"BTCUSD": "XBTUSD"}  # type: ignore[method-assign]
        trader._capital_tradable_symbols = lambda: {"XAUUSD": "GOLD", "BTCUSD": "BTCUSD"}  # type: ignore[method-assign]
        trader._gold_priority_live_stream_signal = lambda: {  # type: ignore[method-assign]
            "ready": True,
            "normalized_symbol": "XAUUSD",
            "symbol": "GOLD",
            "capital_symbol": "GOLD",
            "reference_price": 4552.5,
            "age_sec": 1.0,
            "confidence": 0.72,
            "side": "HOLD",
            "side_reason": "gold_intelligence_requires_fresh_interval_validation",
            "intent_publishable": False,
            "source_tags": ["capital_gold_live_stream", "gold_priority_target", "fresh_interval_validated_gold_projection_required"],
        }
        central_beat = {
            "symbols": {
                "BTCUSD": {
                    "strength": 1.0,
                    "confidence": 1.0,
                    "support_count": 4,
                    "side": "SELL",
                    "sources": ["binance", "kraken"],
                    "reference_price": 50000.0,
                    "change_pct": 4.0,
                }
            }
        }
        shared_market_feed = {"symbols": {"BTCUSD": 1.0}}

        order_flow = trader._build_global_order_flow_feed({}, {}, central_beat, shared_market_feed)

        self.assertEqual(order_flow["active_order_flow"][0]["symbol"], "XAUUSD")
        self.assertTrue(order_flow["active_order_flow"][0]["gold_priority_candidate"])
        action_plan = trader._build_exchange_action_plan(order_flow)
        proof = trader._build_gold_runtime_trade_proof(
            central_beat,
            shared_market_feed,
            order_flow,
            action_plan,
        )
        self.assertTrue(proof["gold_runtime_candidate_ready"])
        self.assertTrue(proof["capital_cfd_route_visible"])

    def test_gold_priority_hold_side_blocks_intent_publish(self):
        trader = self._make_trader()
        trader.capital_ready = True
        trader._capital_tradable_symbols = lambda: {"XAUUSD": "GOLD"}  # type: ignore[method-assign]
        trader._gold_priority_live_stream_signal = lambda: {  # type: ignore[method-assign]
            "ready": True,
            "normalized_symbol": "XAUUSD",
            "symbol": "GOLD",
            "capital_symbol": "GOLD",
            "reference_price": 4552.5,
            "age_sec": 1.0,
            "confidence": 0.82,
            "side": "HOLD",
            "side_reason": "gold_intelligence_requires_fresh_interval_validation",
            "intent_publishable": False,
            "source_tags": ["capital_gold_live_stream", "gold_priority_target", "fresh_interval_validated_gold_projection_required"],
        }
        old_env = self._with_live_executor_env()
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                state_path = Path(tmp_dir) / "intents.json"
                log_path = Path(tmp_dir) / "intents.jsonl"
                public_path = Path(tmp_dir) / "public.json"
                with patch.object(trader_mod, "ORDER_INTENT_STATE_PATH", state_path), patch.object(
                    trader_mod, "ORDER_INTENT_LOG_PATH", log_path
                ), patch.object(trader_mod, "ORDER_INTENT_PUBLIC_PATH", public_path):
                    order_flow = trader._build_global_order_flow_feed({}, {}, {"symbols": {}}, {"symbols": {}})
                    top = order_flow["active_order_flow"][0]
                    self.assertEqual(top["side"], "HOLD")
                    self.assertIn("gold_side_not_validated_by_fresh_interval_projection", top["intent_publish_blockers"])
                    action_plan = trader._build_exchange_action_plan(order_flow)
                    self.assertIn("capital_cfd", action_plan["venues"])
                    trader._publish_order_intents(order_flow, action_plan)
                    self.assertFalse(state_path.exists())
                    self.assertEqual(action_plan["order_intents_published"], 0)
        finally:
            self._restore_env(old_env)

    def test_order_intents_include_lifecycle_identity(self):
        old_env = self._with_live_executor_env()
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                trader = self._make_trader()
                trader._order_lifecycle_enabled = True
                trader._order_lifecycle_root_path = tmp_path
                state_path = tmp_path / "intents.json"
                log_path = tmp_path / "intents.jsonl"
                public_path = tmp_path / "public.json"
                order_flow = {
                    "active_order_flow": [
                        {
                            "symbol": "GOLD",
                            "side": "BUY",
                            "confidence": 0.91,
                            "support_count": 3,
                            "sources": ["capital_gold_live_stream"],
                            "execution_routes": [
                                {
                                    "venue": "capital",
                                    "market_type": "cfd",
                                    "symbol": "GOLD",
                                    "ready": True,
                                    "route_key": "capital:cfd:GOLD:BUY",
                                }
                            ],
                        }
                    ]
                }
                action_plan = {
                    "order_intent_publish_enabled": True,
                    "global_blockers": [],
                    "order_authority_mode": "intent_only_runtime_gated",
                }
                with patch.object(trader_mod, "ORDER_INTENT_STATE_PATH", state_path), patch.object(
                    trader_mod, "ORDER_INTENT_LOG_PATH", log_path
                ), patch.object(trader_mod, "ORDER_INTENT_PUBLIC_PATH", public_path):
                    trader._publish_order_intents(order_flow, action_plan)

                payload = json.loads(state_path.read_text(encoding="utf-8"))
                candidate = payload["intents"][0]
                lifecycle_state = json.loads((tmp_path / "state" / "unified_order_lifecycle_latest.json").read_text(encoding="utf-8"))

                self.assertTrue(candidate["candidate_id"].startswith("ocand-"))
                self.assertTrue(candidate["lifecycle_id"].startswith("olife-"))
                self.assertEqual(candidate["route_key"], "capital:cfd:GOLD:BUY")
                self.assertEqual(candidate["routes"][0]["lifecycle_id"], candidate["lifecycle_id"])
                self.assertEqual(lifecycle_state["latest_event"]["status"], "intent_published")
        finally:
            self._restore_env(old_env)

    def test_dry_run_disables_unified_executor_even_when_env_armed(self):
        old_env = self._with_live_executor_env()
        try:
            trader = self._make_trader()
            trader.dry_run = True
            payload = {"combined": {"open_positions": 0}}
            action_plan = {"order_intent_publish_enabled": True, "global_blockers": []}

            blockers = trader._execution_blockers(payload, action_plan)

            self.assertFalse(trader._runtime_real_orders_allowed())
            self.assertFalse(trader._unified_executor_enabled())
            self.assertIn("unified_order_executor_disabled", blockers)
            self.assertIn("real_orders_not_allowed_by_runtime", blockers)
        finally:
            self._restore_env(old_env)

    def test_blocked_execution_summary_is_persisted(self):
        old_env = self._with_live_executor_env()
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = Path(tmp_dir)
                trader = self._make_trader()
                trader.dry_run = True
                payload = {
                    "combined": {"open_positions": 0},
                    "exchange_action_plan": {"order_intent_publish_enabled": True, "global_blockers": []},
                    "shared_order_flow": {"active_order_flow": []},
                }
                state_path = tmp_path / "execution.json"
                public_path = tmp_path / "public_execution.json"
                log_path = tmp_path / "execution.jsonl"
                with patch.object(trader_mod, "EXECUTION_RESULT_STATE_PATH", state_path), patch.object(
                    trader_mod, "EXECUTION_RESULT_PUBLIC_PATH", public_path
                ), patch.object(trader_mod, "EXECUTION_RESULT_LOG_PATH", log_path):
                    summary = trader._execute_runtime_order_actions(payload)

                persisted = json.loads(state_path.read_text(encoding="utf-8"))

                self.assertFalse(summary["executor_enabled"])
                self.assertIn("unified_order_executor_disabled", summary["blockers"])
                self.assertEqual(persisted["submitted_count"], 0)
                self.assertFalse(persisted["executor_enabled"])
                self.assertTrue(public_path.exists())
                self.assertTrue(log_path.exists())
        finally:
            self._restore_env(old_env)

    def test_gold_priority_capital_route_exposes_not_ready_blocker(self):
        trader = self._make_trader()
        trader.capital_ready = False
        trader.capital_error = ""
        trader._capital_tradable_symbols = lambda: {"XAUUSD": "GOLD"}  # type: ignore[method-assign]
        trader._gold_priority_live_stream_signal = lambda: {  # type: ignore[method-assign]
            "ready": True,
            "normalized_symbol": "XAUUSD",
            "symbol": "GOLD",
            "capital_symbol": "GOLD",
            "reference_price": 4552.5,
            "age_sec": 1.0,
            "confidence": 0.82,
            "side": "BUY",
            "side_reason": "gold_intelligence_validated_buy_sell",
            "intent_publishable": True,
            "source_tags": ["capital_gold_live_stream", "gold_priority_target", "fresh_interval_validated_gold_projection_required"],
        }

        order_flow = trader._build_global_order_flow_feed({}, {}, {"symbols": {}}, {"symbols": {}})
        route = order_flow["active_order_flow"][0]["execution_routes"][0]
        self.assertEqual(route["venue"], "capital")
        self.assertFalse(route["ready"])
        self.assertIn("capital_not_ready", route["blockers"])
        action_plan = trader._build_exchange_action_plan(order_flow)
        self.assertIn("capital_cfd", action_plan["venues"])
        self.assertIn("capital_not_ready", action_plan["venues"]["capital_cfd"]["blockers"])

    def test_profit_velocity_ranking_uses_cash_price_history_and_eta(self):
        trader = self._make_trader()
        trader.kraken_ready = True
        trader.capital_ready = True
        trader._binance_diag = {"network_ok": True, "account_ok": True, "margin_available": True, "uk_mode": False}
        trader._kraken_tradable_symbols = lambda: {"BTCUSD": "XXBTZUSD", "SOLUSD": "SOLUSDT"}  # type: ignore[method-assign]
        trader._kraken_spot_tradable_symbols = lambda: {"BTCUSD": "XBTUSD", "SOLUSD": "SOLUSD"}  # type: ignore[method-assign]
        trader._capital_tradable_symbols = lambda: {"BTCUSD": "BTCUSD", "SOLUSD": "SOLUSD"}  # type: ignore[method-assign]
        trader._alpaca_tradable_symbols = lambda: {"BTCUSD": "BTC/USD", "SOLUSD": "SOL/USD"}  # type: ignore[method-assign]
        trader._binance_tradable_symbols = lambda: {"BTCUSD": "BTCUSDT", "SOLUSD": "SOLUSDT"}  # type: ignore[method-assign]
        trader._read_shadow_trade_state = lambda: {  # type: ignore[method-assign]
            "prior_verifications": [
                {
                    "id": "sol-fast",
                    "route_signature": "binance:spot:SOLUSDT:BUY",
                    "symbol": "SOLUSD",
                    "status": "validated",
                    "opened_at_epoch": 1000.0,
                    "last_verified_epoch": 1030.0,
                    "eta_seconds_actual": 30.0,
                },
                {
                    "id": "btc-slow",
                    "route_signature": "binance:spot:BTCUSDT:BUY",
                    "symbol": "BTCUSD",
                    "status": "missed_eta",
                },
            ]
        }
        central_beat = {
            "symbols": {
                "BTCUSD": {
                    "confidence": 0.95,
                    "support_count": 2,
                    "side": "BUY",
                    "sources": ["kraken", "capital"],
                    "reference_price": 50000.0,
                    "change_pct": 0.02,
                    "model_alignment": True,
                },
                "SOLUSD": {
                    "confidence": 0.72,
                    "support_count": 4,
                    "side": "BUY",
                    "sources": ["kraken", "capital", "alpaca", "binance"],
                    "reference_price": 90.0,
                    "change_pct": 0.8,
                    "model_alignment": True,
                },
            }
        }
        shared_market_feed = {"symbols": {"BTCUSD": 0.95, "SOLUSD": 0.72}}

        order_flow = trader._build_global_order_flow_feed({}, {}, central_beat, shared_market_feed)
        top = order_flow["active_order_flow"][0]

        self.assertEqual(top["symbol"], "SOLUSD")
        self.assertGreater(top["profit_velocity_score"], order_flow["active_order_flow"][1]["profit_velocity_score"])
        self.assertEqual(top["history_validated_count"], 1)
        self.assertGreaterEqual(top["cash_capable_route_count"], 1)
        self.assertLessEqual(top["estimated_target_eta_sec"], trader_mod.SHADOW_TRADE_VALIDATION_HORIZON_SEC)
        self.assertGreater(top["intelligence_mesh_score"], 0.0)
        self.assertIn("intelligence_mesh", order_flow)
        self.assertEqual(order_flow["selection_process"]["mode"], "fast_money_profit_velocity_ranked_live_shadow_selection")
        self.assertGreaterEqual(top["fast_money_score"], 0.0)
        self.assertIn("fast_money_intelligence", order_flow)

    def test_fast_money_ranking_uses_volume_momentum_and_orderbook_pressure(self):
        trader = self._make_trader()
        trader.kraken_ready = True
        trader.capital_ready = True
        trader._binance_diag = {"network_ok": True, "account_ok": True, "margin_available": True, "uk_mode": False}
        trader._kraken_tradable_symbols = lambda: {"BTCUSD": "XXBTZUSD", "SOLUSD": "SOLUSDT"}  # type: ignore[method-assign]
        trader._kraken_spot_tradable_symbols = lambda: {"BTCUSD": "XBTUSD", "SOLUSD": "SOLUSD"}  # type: ignore[method-assign]
        trader._capital_tradable_symbols = lambda: {"BTCUSD": "BTCUSD", "SOLUSD": "SOLUSD"}  # type: ignore[method-assign]
        trader._alpaca_tradable_symbols = lambda: {"BTCUSD": "BTC/USD", "SOLUSD": "SOL/USD"}  # type: ignore[method-assign]
        trader._binance_tradable_symbols = lambda: {"BTCUSD": "BTCUSDT", "SOLUSD": "SOLUSDT"}  # type: ignore[method-assign]
        trader._orderbook_pressure_snapshot = lambda item: {  # type: ignore[method-assign]
            "available": True,
            "source": "test_orderbook",
            "symbol": item.get("symbol"),
            "side": item.get("side", "BUY"),
            "pressure_side": item.get("side", "BUY"),
            "score": 0.92 if item.get("symbol") == "SOLUSD" else 0.42,
            "signed_imbalance": 0.4 if item.get("symbol") == "SOLUSD" else -0.1,
        }
        central_beat = {
            "symbols": {
                "BTCUSD": {
                    "confidence": 0.93,
                    "support_count": 3,
                    "side": "BUY",
                    "sources": ["live_stream_cache", "kraken"],
                    "reference_price": 50000.0,
                    "change_pct": 0.04,
                    "change_pct_abs_max": 0.04,
                    "volume_24h": 9000000.0,
                    "freshest_age_sec": 1.0,
                    "model_alignment": True,
                },
                "SOLUSD": {
                    "confidence": 0.74,
                    "support_count": 4,
                    "side": "BUY",
                    "sources": ["live_stream_cache", "kraken", "capital", "binance"],
                    "reference_price": 90.0,
                    "change_pct": 0.92,
                    "change_pct_abs_max": 1.2,
                    "volume_24h": 65000000.0,
                    "freshest_age_sec": 0.4,
                    "fast_money_sources": ["live_stream_cache"],
                    "model_alignment": True,
                },
            }
        }
        shared_market_feed = {"symbols": {"BTCUSD": 0.93, "SOLUSD": 0.74}}

        order_flow = trader._build_global_order_flow_feed({}, {}, central_beat, shared_market_feed)
        top = order_flow["active_order_flow"][0]

        self.assertEqual(top["symbol"], "SOLUSD")
        self.assertTrue(top["fast_money_candidate"])
        self.assertGreater(top["fast_money_score"], order_flow["active_order_flow"][1]["fast_money_score"])
        self.assertEqual(top["fast_money_profile"]["momentum_tier"], "tier_1_hot")
        self.assertEqual(top["fast_money_profile"]["orderbook_alignment"], "aligned")
        self.assertEqual(order_flow["fast_money_intelligence"]["candidate_count"], 1)
        self.assertEqual(order_flow["fast_money_intelligence"]["orderbook_probe_count"], 1)

    def test_scanner_fusion_cross_references_orderbook_waveforms_and_world_context(self):
        trader = self._make_trader()
        trader.kraken_ready = True
        trader.capital_ready = True
        trader._binance_diag = {"network_ok": True, "account_ok": True, "margin_available": True, "uk_mode": False}
        trader._kraken_tradable_symbols = lambda: {"SOLUSD": "SOLUSDT"}  # type: ignore[method-assign]
        trader._kraken_spot_tradable_symbols = lambda: {"SOLUSD": "SOLUSD"}  # type: ignore[method-assign]
        trader._capital_tradable_symbols = lambda: {"SOLUSD": "SOLUSD"}  # type: ignore[method-assign]
        trader._alpaca_tradable_symbols = lambda: {"SOLUSD": "SOL/USD"}  # type: ignore[method-assign]
        trader._binance_tradable_symbols = lambda: {"SOLUSD": "SOLUSDT"}  # type: ignore[method-assign]
        trader._orderbook_pressure_snapshot = lambda item: {  # type: ignore[method-assign]
            "available": True,
            "source": "test_orderbook",
            "symbol": item.get("symbol"),
            "side": item.get("side", "BUY"),
            "pressure_side": item.get("side", "BUY"),
            "score": 0.91,
            "signed_imbalance": 0.38,
        }
        central_beat = {
            "generated_at": "2026-05-14T12:00:00",
            "source_count": 5,
            "stream_cache": {"fresh": True, "symbol_count": 1},
            "model_signal_feed": {"used": True},
            "world_financial_ecosystem": {
                "usable_source_count": 3,
                "cross_asset": {"present": True, "active_this_cycle": True},
                "market_harp": {"present": True, "active_this_cycle": True},
                "news_signal": {"present": True, "usable_for_decision": True},
            },
            "asset_waveform_models": {"usable_symbol_count": 1, "long_memory_ready_count": 1},
            "symbols": {
                "SOLUSD": {
                    "confidence": 0.78,
                    "support_count": 5,
                    "side": "BUY",
                    "sources": ["live_stream_cache", "kraken", "binance", "world_financial_ecosystem", "historical_waveform_models"],
                    "reference_price": 90.0,
                    "change_pct": 0.86,
                    "change_pct_abs_max": 1.05,
                    "volume_24h": 72000000.0,
                    "freshest_age_sec": 0.3,
                    "fast_money_sources": ["live_stream_cache", "world_financial_ecosystem"],
                    "model_alignment": True,
                    "historical_waveform": {"confidence": 0.81, "side": "BUY", "long_memory_ready": True},
                    "world_ecosystem_signal": {"confidence": 0.76, "side": "BUY", "downstream_stage": "profit_velocity"},
                }
            },
        }
        shared_market_feed = {"symbols": {"SOLUSD": 0.78}}

        order_flow = trader._build_global_order_flow_feed({}, {}, central_beat, shared_market_feed)
        top = order_flow["active_order_flow"][0]
        scanner_matrix = order_flow["scanner_fusion_matrix"]
        rows = {row["name"]: row for row in scanner_matrix["systems"]}
        mesh_statuses = {item["name"]: item["status"] for item in order_flow["intelligence_mesh"]["capabilities"]}

        self.assertTrue(scanner_matrix["fed_to_decision_logic"])
        self.assertGreaterEqual(scanner_matrix["usable_system_count"], 8)
        self.assertTrue(top["scanner_fusion"]["usable_for_decision"])
        self.assertEqual(top["scanner_fusion"]["orderbook_alignment"], "aligned")
        self.assertGreater(top["scanner_fusion_score"], 0.6)
        self.assertGreaterEqual(top["scanner_fusion"]["cross_reference_count"], 6)
        self.assertTrue(rows["LiveMomentumHunter"]["active_this_cycle"])
        self.assertTrue(rows["OrderBookPressure"]["active_this_cycle"])
        self.assertTrue(rows["GlobalWaveScanner"]["active_this_cycle"])
        self.assertTrue(rows["PhantomSignalFilter"]["active_this_cycle"])
        self.assertEqual(mesh_statuses["LiveMomentumHunter"], "active")
        self.assertEqual(mesh_statuses["PhantomSignalFilter"], "active")

    def test_dynamic_intelligence_budget_uses_low_cash_exchange_as_sensor(self):
        class LowCashBinance:
            def get_balance(self):
                return {"USDT": 1.0}

        trader = self._make_trader()
        trader.kraken_ready = True
        trader.binance = LowCashBinance()
        trader._binance_diag = {"network_ok": True, "account_ok": True}

        budget = trader._build_dynamic_intelligence_budget(
            {
                "portfolio_balances": {
                    "source": "kraken_private_balance_cached_live",
                    "tradable_cash_usd": 120.0,
                    "total_usd_estimate": 140.0,
                }
            },
            {},
        )
        trader._dynamic_intelligence_budget = budget

        self.assertEqual(budget["exchanges"]["kraken"]["role"], "execution_priority")
        self.assertEqual(budget["exchanges"]["binance"]["role"], "sensor_priority")
        self.assertGreater(budget["stream_symbol_limit"], trader_mod.STREAM_CACHE_MAX_SYMBOLS)
        self.assertGreater(budget["orderbook_probe_limit"], trader_mod.ORDERBOOK_PROBE_MAX_PER_TICK)
        self.assertLessEqual(trader._dynamic_probe_interval("binance"), trader_mod.PROBE_SYMBOL_MIN_INTERVAL_SEC)

    def test_dynamic_budget_expands_orderbook_probe_count(self):
        trader = self._make_trader()
        trader._dynamic_intelligence_budget = {
            "schema_version": 1,
            "mode": "balance_weighted_dynamic_ocean_wave_scan",
            "orderbook_probe_limit": trader_mod.ORDERBOOK_PROBE_MAX_PER_TICK + 2,
            "exchanges": {"binance": {"role": "sensor_priority"}},
        }
        calls = []

        def pressure(item):
            calls.append(item.get("symbol"))
            return {
                "available": True,
                "source": "test_orderbook",
                "pressure_side": "BUY",
                "score": 0.8,
            }

        trader._orderbook_pressure_snapshot = pressure  # type: ignore[method-assign]
        ranked = [
            {
                "symbol": f"COIN{i}USD",
                "side": "BUY",
                "confidence": 0.8,
                "profit_velocity_score": 0.7 - (i * 0.01),
                "execution_routes": [{"ready": True, "cash_capability": {"score": 0.7}}],
                "fast_money_profile": {
                    "fast_money_candidate": True,
                    "fast_money_score": 0.9 - (i * 0.01),
                    "volatility_pct": 1.0,
                },
            }
            for i in range(trader_mod.ORDERBOOK_PROBE_MAX_PER_TICK + 3)
        ]

        summary = trader._attach_orderbook_fast_money_pressure(
            ranked,
            shadow_index={},
            intelligence_mesh={"selection_mesh_score": 1.0},
        )

        self.assertEqual(len(calls), trader_mod.ORDERBOOK_PROBE_MAX_PER_TICK + 2)
        self.assertEqual(summary["thresholds"]["dynamic_orderbook_probe_max_per_tick"], trader_mod.ORDERBOOK_PROBE_MAX_PER_TICK + 2)
        self.assertEqual(summary["dynamic_intelligence_budget"]["mode"], "balance_weighted_dynamic_ocean_wave_scan")

    def test_orderbook_pressure_samples_top_ranked_candidate_without_fast_money_threshold(self):
        trader = self._make_trader()
        trader._dynamic_intelligence_budget = {
            "schema_version": 1,
            "mode": "test_budget",
            "orderbook_probe_limit": 1,
        }
        calls = []

        def pressure(item):
            calls.append(item.get("symbol"))
            return {
                "available": True,
                "source": "test_orderbook",
                "pressure_side": "BUY",
                "score": 0.71,
            }

        trader._orderbook_pressure_snapshot = pressure  # type: ignore[method-assign]
        ranked = [
            {
                "symbol": "BTCUSD",
                "side": "BUY",
                "confidence": trader_mod.ORDER_INTENT_MIN_CONFIDENCE,
                "profit_velocity_score": 0.44,
                "execution_routes": [{"ready": True, "cash_capability": {"score": 0.7}}],
                "ready_route_count": 1,
                "fast_money_profile": {
                    "fast_money_candidate": False,
                    "fast_money_score": 0.32,
                    "volatility_pct": 0.02,
                },
            }
        ]

        summary = trader._attach_orderbook_fast_money_pressure(
            ranked,
            shadow_index={},
            intelligence_mesh={"selection_mesh_score": 0.5},
        )

        self.assertEqual(calls, ["BTCUSD"])
        self.assertEqual(summary["orderbook_attempt_count"], 1)
        self.assertEqual(summary["orderbook_probe_count"], 1)
        self.assertTrue(summary["active_this_cycle"])
        self.assertTrue(summary["fed_to_decision_logic"])
        self.assertEqual(ranked[0]["fast_money_profile"]["orderbook_alignment"], "aligned")

    def test_intelligence_mesh_reports_capability_presence_and_active_bridges(self):
        trader = self._make_trader()
        central_beat = {
            "source_count": 4,
            "model_signal_feed": {"used": True},
        }
        shadow_report = {"shadow_opened_count": 2, "active_shadow_count": 2, "validated_shadow_count": 1}
        hnc_proof = {
            "systems": {
                "hnc_master_protocol": {"passed": True},
                "hnc_probability_matrix": {"passed": True},
                "seer": {"passed": True},
                "lyra": {"passed": True},
                "king": {"passed": True},
            }
        }

        mesh = trader._build_intelligence_mesh(
            central_beat=central_beat,
            shadow_trade_report=shadow_report,
            hnc_cognitive_proof=hnc_proof,
        )

        self.assertGreater(mesh["present_count"], 10)
        self.assertGreater(mesh["active_this_cycle_count"], 5)
        self.assertGreater(mesh["selection_mesh_score"], 0.0)
        statuses = {item["name"]: item["status"] for item in mesh["capabilities"]}
        self.assertEqual(statuses["UnifiedSignalEngine"], "active")
        self.assertEqual(statuses["ShadowTradeValidator"], "active")
        self.assertIn(statuses["QueenOnlineResearcher"], {"active", "available_to_mesh"})

    def test_fresh_writer_lock_is_not_honored_when_owner_pid_is_dead(self):
        trader = self._make_trader()
        lock = {
            "instance_id": "other-runtime",
            "pid": 99999999,
            "heartbeat_at": time.time(),
        }

        self.assertFalse(trader._lock_owner_is_fresh(lock, time.time()))

    def test_windows_writer_lock_owner_check_uses_tasklist_not_posix_signal(self):
        trader = self._make_trader()
        lock = {
            "instance_id": "other-runtime",
            "pid": 12345,
            "heartbeat_at": time.time(),
        }

        with patch.object(trader_mod.os, "name", "nt"), patch.object(trader_mod.subprocess, "run") as run:
            run.return_value.stdout = '"python.exe","12345","Console","1","42,000 K"'

            self.assertTrue(trader._runtime_writer_lock_owner_alive(lock))

        run.assert_called_once()

    def test_shadow_trade_report_verifies_prior_shadow_against_current_price(self):
        trader = self._make_trader()
        previous_state = {
            "active_shadows": [
                {
                    "id": "shadow-old",
                    "route_signature": "kraken:spot:BTCUSD:BUY",
                    "symbol": "BTCUSD",
                    "venue": "kraken",
                    "market_type": "spot",
                    "route_symbol": "BTCUSD",
                    "side": "BUY",
                    "entry_price": 100.0,
                    "target_move_pct": 0.18,
                    "expected_by_epoch": time.time() + 30.0,
                    "status": "shadow_opened",
                }
            ]
        }
        order_flow = {
            "active_order_flow": [
                {
                    "symbol": "BTCUSD",
                    "side": "BUY",
                    "confidence": 0.2,
                    "reference_price": 101.0,
                    "execution_routes": [],
                }
            ]
        }

        report = trader._build_shadow_trade_report(order_flow, {"global_guards": []}, persist=False, previous_state=previous_state)

        self.assertEqual(report["validated_shadow_count"], 1)
        self.assertEqual(report["prior_verifications"][0]["status"], "validated")
        self.assertTrue(report["prior_verifications"][0]["target_hit"])

    def test_shared_order_flow_feeds_all_unified_targets(self):
        trader = self._make_trader()
        order_flow = {
            "shared_tradable_count": 1,
            "active_order_flow": [
                {
                    "symbol": "BTCUSD",
                    "side": "BUY",
                    "confidence": 0.8,
                    "kraken_symbol": "XXBTZUSD",
                    "capital_symbol": "BTCUSD",
                    "alpaca_symbol": "BTC/USD",
                    "binance_symbol": "BTCUSDT",
                    "execution_routes": [
                        {"venue": "kraken", "market_type": "margin", "symbol": "XXBTZUSD", "ready": True},
                        {"venue": "alpaca", "market_type": "spot", "symbol": "BTC/USD", "ready": True},
                        {"venue": "binance", "market_type": "spot", "symbol": "BTCUSDT", "ready": True},
                    ],
                }
            ],
        }

        trader._feed_shared_order_flow_to_decision_logic(order_flow)

        self.assertEqual(len(trader.kraken.decision_feeds), 1)
        self.assertEqual(len(trader.capital.decision_feeds), 1)
        self.assertEqual(len(trader.alpaca.decision_feeds), 1)
        self.assertEqual(len(trader.binance.decision_feeds), 1)
        self.assertEqual(trader.binance.decision_feeds[0]["metadata"]["binance_symbol"], "BTCUSDT")

    def test_spot_symbol_mapping_filters_non_crypto_cfds(self):
        trader = self._make_trader()

        self.assertEqual(trader._to_binance_symbol("BTCUSD"), "BTCUSDT")
        self.assertEqual(trader._to_alpaca_crypto_symbol("BTCUSD"), "BTC/USD")
        self.assertEqual(trader._to_binance_symbol("XAUUSD"), "")
        self.assertEqual(trader._to_alpaca_crypto_symbol("XAUUSD"), "")

    def test_runtime_executor_submits_direct_routes_and_delegates_existing_traders_when_gates_clear(self):
        old_env = self._with_live_executor_env()

        class KrakenExec:
            def __init__(self):
                self.spot_orders = []
                self.margin_orders = []

            def get_free_balance(self, asset):
                return 500.0 if asset in {"USD", "ZUSD"} else 0.0

            def best_price(self, symbol):
                return {"price": 50000.0}

            def get_pair_leverage(self, symbol):
                return {"leverage_buy": [2, 3], "leverage_sell": [2], "pair": symbol}

            def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
                self.spot_orders.append((symbol, side, quantity, quote_qty))
                return {"txid": [f"kraken-{len(self.spot_orders)}"], "status": "accepted"}

            def place_margin_order(self, symbol, side, quantity, leverage=2, **kwargs):
                self.margin_orders.append((symbol, side, quantity, leverage))
                return {"orderId": f"kraken-margin-{len(self.margin_orders)}", "status": "FILLED"}

        class KrakenTrader:
            def __init__(self):
                self.client = KrakenExec()

        class AlpacaExec:
            init_error = ""
            is_authenticated = True

            def __init__(self):
                self.orders = []

            def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
                self.orders.append((symbol, side, quantity, quote_qty))
                return {"id": f"alpaca-{len(self.orders)}", "status": "accepted"}

        class BinanceExec:
            def __init__(self):
                self.spot_orders = []
                self.margin_orders = []

            def get_24h_ticker(self, symbol):
                return {"lastPrice": "50000"}

            def best_price(self, symbol):
                return {"price": 50000.0}

            def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
                self.spot_orders.append((symbol, side, quantity, quote_qty))
                return {"orderId": f"spot-{len(self.spot_orders)}", "status": "FILLED"}

            def place_margin_order(self, symbol, side, quantity, leverage=2, **kwargs):
                self.margin_orders.append((symbol, side, quantity, leverage))
                return {"orderId": f"margin-{len(self.margin_orders)}", "status": "FILLED"}

        try:
            trader = self._make_trader()
            trader.kraken = KrakenTrader()
            trader.kraken_ready = True
            trader.capital_ready = True
            trader.alpaca = AlpacaExec()
            trader.binance = BinanceExec()
            trader._last_tick_started_at = time.time()
            payload = {
                "combined": {"open_positions": 0},
                "exchange_action_plan": {
                    "order_intent_publish_enabled": True,
                    "global_blockers": [],
                },
                "shared_order_flow": {
                    "active_order_flow": [
                        {
                            "symbol": "BTCUSD",
                            "side": "BUY",
                            "confidence": 0.9,
                            "support_count": 4,
                            "sources": ["kraken", "capital", "alpaca", "binance"],
                            "execution_routes": [
                                {"venue": "kraken", "market_type": "spot", "symbol": "XBTUSD", "ready": True},
                                {"venue": "kraken", "market_type": "margin", "symbol": "XXBTZUSD", "ready": True, "execution_owner": "existing_autonomous_trader_tick"},
                                {"venue": "capital", "market_type": "cfd", "symbol": "BTCUSD", "ready": True, "execution_owner": "existing_autonomous_trader_tick"},
                                {"venue": "alpaca", "market_type": "spot", "symbol": "BTC/USD", "ready": True},
                                {"venue": "binance", "market_type": "spot", "symbol": "BTCUSDT", "ready": True},
                                {"venue": "binance", "market_type": "margin", "symbol": "BTCUSDT", "ready": True},
                            ],
                        }
                    ]
                },
            }

            summary = trader._execute_runtime_order_actions(payload)

            self.assertEqual(summary["submitted_count"], 4)
            self.assertEqual(summary["delegated_count"], 1)
            self.assertEqual(summary["held_count"], 0)
            self.assertEqual(summary["trade_path_state"], "available")
            self.assertEqual(trader.kraken.client.spot_orders[0], ("XBTUSD", "buy", None, trader_mod.KRAKEN_SPOT_QUOTE_USD))
            self.assertEqual(trader.kraken.client.margin_orders[0][0], "XXBTZUSD")
            self.assertEqual(trader.alpaca.orders[0], ("BTC/USD", "buy", None, trader_mod.ORDER_EXECUTOR_QUOTE_USD))
            self.assertEqual(trader.binance.spot_orders[0], ("BTCUSDT", "BUY", None, trader_mod.ORDER_EXECUTOR_QUOTE_USD))
        finally:
            self._restore_env(old_env)

    def test_kraken_spot_buy_records_fee_aware_fast_profit_position(self):
        class KrakenExec:
            def __init__(self):
                self.orders = []

            def get_free_balance(self, asset):
                return 500.0 if asset in {"USD", "ZUSD"} else 0.0

            def get_ticker(self, symbol):
                return {"price": 100.0, "bid": 99.99, "ask": 100.01}

            def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
                self.orders.append((symbol, side, quantity, quote_qty))
                return {"orderId": "KB1", "executedQty": "0.65", "status": "FILLED"}

        class KrakenTrader:
            def __init__(self):
                self.client = KrakenExec()

        with tempfile.TemporaryDirectory() as tmp:
            old_state = trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH
            old_public = trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH
            trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH = Path(tmp) / "state.json"
            trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH = Path(tmp) / "public.json"
            try:
                trader = self._make_trader()
                trader.kraken = KrakenTrader()
                result = trader._execute_kraken_spot_route("BUY", "XBTUSD", 65.0)

                self.assertTrue(result["ok"], result)
                self.assertEqual(result["cost_profile"]["estimated_round_trip_cost_usd"], 0.52)
                self.assertEqual(result["fast_profit_position"]["id"], "KB1")
                state = trader._load_kraken_spot_fast_profit_state()
                self.assertEqual(len(state["open_positions"]), 1)
                self.assertEqual(state["open_positions"][0]["entry_fee_usd"], 0.26)
            finally:
                trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH = old_state
                trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH = old_public

    def test_kraken_spot_buy_can_use_gbp_quote_balance(self):
        class KrakenExec:
            def __init__(self):
                self.orders = []

            def get_account_balance(self):
                return {"GBP": 100.0}

            def convert_to_quote(self, asset, amount, quote):
                if asset == "GBP" and quote == "USD":
                    return float(amount) * 1.25
                return 0.0

            def get_ticker(self, symbol):
                return {"price": 80.0, "bid": 79.9, "ask": 80.1}

            def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
                self.orders.append((symbol, side, quantity, quote_qty))
                return {"orderId": "KGBP1", "executedQty": "0.8125", "status": "FILLED"}

        class KrakenTrader:
            def __init__(self):
                self.client = KrakenExec()

        with tempfile.TemporaryDirectory() as tmp:
            old_state = trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH
            old_public = trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH
            trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH = Path(tmp) / "state.json"
            trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH = Path(tmp) / "public.json"
            try:
                trader = self._make_trader()
                trader.kraken = KrakenTrader()
                result = trader._execute_kraken_spot_route("BUY", "XBTUSD", 65.0)

                self.assertTrue(result["ok"], result)
                self.assertEqual(result["quote_asset"], "GBP")
                self.assertEqual(trader.kraken.client.orders[0][0], "XBTGBP")
                self.assertAlmostEqual(trader.kraken.client.orders[0][3], 52.0)
            finally:
                trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH = old_state
                trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH = old_public

    def test_kraken_margin_route_submits_through_unified_executor(self):
        old_env = self._with_live_executor_env()

        class KrakenExec:
            def __init__(self):
                self.margin_orders = []

            def best_price(self, symbol):
                return {"price": 100.0}

            def get_pair_leverage(self, symbol):
                return {"leverage_buy": [2, 3], "leverage_sell": [2], "pair": symbol}

            def place_margin_order(self, symbol, side, quantity, leverage=2, **kwargs):
                self.margin_orders.append((symbol, side, quantity, leverage))
                return {"orderId": "KM1", "status": "FILLED", "margin": True}

        class KrakenTrader:
            def __init__(self):
                self.client = KrakenExec()

        try:
            trader = self._make_trader()
            trader.kraken = KrakenTrader()
            result = trader._execute_kraken_margin_route("BUY", "XBTUSD", 5.0)

            self.assertTrue(result["ok"], result)
            self.assertEqual(result["market_type"], "margin")
            self.assertEqual(result["leverage"], trader_mod.KRAKEN_MARGIN_LEVERAGE)
            self.assertEqual(trader.kraken.client.margin_orders[0][0], "XBTUSD")
            self.assertGreater(trader.kraken.client.margin_orders[0][2], 0.0)
        finally:
            self._restore_env(old_env)

    def test_kraken_spot_buy_goes_margin_only_when_spot_inventory_underwater(self):
        class KrakenExec:
            def get_account_balance(self):
                return {"TRX": 100.0, "USD": 500.0}

            def convert_to_quote(self, asset, amount, quote):
                if asset == "TRX" and quote == "USD":
                    return float(amount) * 0.90
                return float(amount) if asset == quote else 0.0

            def calculate_cost_basis(self, symbol):
                return {
                    "symbol": symbol,
                    "avg_entry_price": 1.0,
                    "total_quantity": 100.0,
                    "total_fees": 0.10,
                    "trade_count": 1,
                }

            def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
                raise AssertionError("spot buy should not execute while held spot inventory is underwater")

        class KrakenTrader:
            def __init__(self):
                self.client = KrakenExec()

        trader = self._make_trader()
        trader.kraken = KrakenTrader()

        posture = trader._kraken_spot_portfolio_posture(force=True)
        result = trader._execute_kraken_spot_route("BUY", "TRXUSD", 65.0)

        self.assertFalse(posture["spot_buy_allowed"])
        self.assertEqual(posture["mode"], "margin_only_until_spot_profit")
        self.assertEqual(result["reason"], "kraken_spot_inventory_underwater_margin_only")

    def test_executor_skips_kraken_spot_buy_and_still_uses_margin_when_spot_underwater(self):
        old_env = self._with_live_executor_env()
        try:
            trader = self._make_trader()
            trader._kraken_spot_portfolio_posture = lambda force=False: {
                "spot_buy_allowed": False,
                "mode": "margin_only_until_spot_profit",
                "negative_position_count": 1,
                "assets": [{"asset": "TRX", "state": "negative_spot_position"}],
            }  # type: ignore[method-assign]
            trader._execute_kraken_spot_route = lambda side, symbol, quote_usd: {
                "ok": False,
                "venue": "kraken",
                "market_type": "spot",
                "symbol": symbol,
                "side": side,
                "reason": "kraken_spot_inventory_underwater_margin_only",
            }  # type: ignore[method-assign]
            trader._execute_kraken_margin_route = lambda side, symbol, quote_usd: {
                "ok": True,
                "venue": "kraken",
                "market_type": "margin",
                "symbol": symbol,
                "side": side,
                "submitted": True,
            }  # type: ignore[method-assign]
            payload = {
                "combined": {"open_positions": 0},
                "exchange_action_plan": {"order_intent_publish_enabled": True, "global_blockers": []},
                "shared_order_flow": {
                    "active_order_flow": [
                        {
                            "symbol": "TRXUSD",
                            "side": "BUY",
                            "confidence": 0.91,
                            "execution_routes": [
                                {"venue": "kraken", "market_type": "spot", "symbol": "TRXUSD", "ready": True},
                                {"venue": "kraken", "market_type": "margin", "symbol": "TRXUSD", "ready": True},
                            ],
                        }
                    ]
                },
            }
            trader._last_tick_started_at = time.time()

            summary = trader._execute_runtime_order_actions(payload)

            self.assertEqual(summary["submitted_count"], 1)
            self.assertEqual(summary["blocked_count"], 1)
            self.assertEqual(summary["results"][0]["reason"], "kraken_spot_inventory_underwater_margin_only")
            self.assertEqual(summary["results"][1]["market_type"], "margin")
        finally:
            self._restore_env(old_env)

    def test_kraken_spot_fast_profit_monitor_sells_only_true_net_profit(self):
        old_env = self._with_live_executor_env()

        class KrakenExec:
            def __init__(self):
                self.orders = []

            def get_ticker(self, symbol):
                return {"price": 101.0, "bid": 101.0, "ask": 101.02}

            def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
                self.orders.append((symbol, side, quantity, quote_qty))
                return {"orderId": "KS1", "status": "FILLED"}

        class KrakenTrader:
            def __init__(self):
                self.client = KrakenExec()

        with tempfile.TemporaryDirectory() as tmp:
            old_state = trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH
            old_public = trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH
            old_min = trader_mod.KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC
            trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH = Path(tmp) / "state.json"
            trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH = Path(tmp) / "public.json"
            trader_mod.KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC = 0.0
            try:
                trader = self._make_trader()
                trader.kraken = KrakenTrader()
                trader.kraken_ready = True
                trader._kraken_spot_fast_profit_state = {
                    "schema_version": 1,
                    "open_positions": [{
                        "id": "P1",
                        "symbol": "XBTUSD",
                        "quantity": 1.0,
                        "entry_price": 100.0,
                        "entry_value_usd": 100.0,
                        "entry_fee_usd": 0.10,
                        "opened_at_epoch": time.time() - 5.0,
                        "status": "open",
                    }],
                    "closed_positions": [],
                    "last_check": {},
                }

                closed = trader._monitor_kraken_spot_fast_profit()

                self.assertEqual(len(closed), 1)
                self.assertEqual(trader.kraken.client.orders[0][1], "sell")
                self.assertGreater(closed[0]["fast_profit_capture"]["true_net_profit_usd"], 0.0)
                state = trader._load_kraken_spot_fast_profit_state()
                self.assertEqual(state["open_positions"], [])
                self.assertEqual(state["last_check"]["closed_count"], 1)
            finally:
                trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH = old_state
                trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH = old_public
                trader_mod.KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC = old_min
                self._restore_env(old_env)

    def test_kraken_spot_fast_profit_monitor_adopts_profitable_live_inventory(self):
        old_env = self._with_live_executor_env()

        class KrakenExec:
            def __init__(self):
                self.orders = []

            def get_account_balance(self):
                return {"TRX": 100.0}

            def convert_to_quote(self, asset, amount, quote):
                if asset == "TRX" and quote == "USD":
                    return float(amount) * 0.40
                return 0.0

            def calculate_cost_basis(self, symbol):
                return {
                    "symbol": symbol,
                    "avg_entry_price": 0.35,
                    "total_quantity": 100.0,
                    "total_fees": 0.02,
                    "trade_count": 1,
                }

            def get_ticker(self, symbol):
                return {"price": 0.40, "bid": 0.40, "ask": 0.401}

            def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
                self.orders.append((symbol, side, quantity, quote_qty))
                return {"orderId": "TRXSELL1", "status": "FILLED"}

        class KrakenTrader:
            def __init__(self):
                self.client = KrakenExec()

        with tempfile.TemporaryDirectory() as tmp:
            old_state = trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH
            old_public = trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH
            old_min = trader_mod.KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC
            trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH = Path(tmp) / "state.json"
            trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH = Path(tmp) / "public.json"
            trader_mod.KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC = 0.0
            try:
                trader = self._make_trader()
                trader.kraken = KrakenTrader()

                closed = trader._monitor_kraken_spot_fast_profit()

                self.assertEqual(len(closed), 1)
                self.assertEqual(trader.kraken.client.orders[0][0], "TRXUSD")
                self.assertEqual(trader.kraken.client.orders[0][1], "sell")
                self.assertEqual(closed[0]["source"], "live_balance_cost_basis")
                self.assertGreater(closed[0]["fast_profit_capture"]["true_net_profit_usd"], 0.0)
            finally:
                trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH = old_state
                trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH = old_public
                trader_mod.KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC = old_min
                self._restore_env(old_env)

    def test_kraken_spot_fast_profit_arms_deadman_when_market_sell_fails(self):
        old_env = self._with_live_executor_env()

        class KrakenExec:
            def __init__(self):
                self.trailing_orders = []

            def get_ticker(self, symbol):
                return {"price": 101.0, "bid": 101.0, "ask": 101.02}

            def place_market_order(self, symbol, side, quantity=None, quote_qty=None):
                return {"error": "temporary_exchange_reject"}

            def place_trailing_stop_order(self, symbol, side, quantity, trailing_offset, offset_type="percent"):
                self.trailing_orders.append((symbol, side, quantity, trailing_offset, offset_type))
                return {"orderId": "DEADMAN1", "status": "NEW"}

        class KrakenTrader:
            def __init__(self):
                self.client = KrakenExec()

        with tempfile.TemporaryDirectory() as tmp:
            old_state = trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH
            old_public = trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH
            old_min = trader_mod.KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC
            trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH = Path(tmp) / "state.json"
            trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH = Path(tmp) / "public.json"
            trader_mod.KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC = 0.0
            try:
                trader = self._make_trader()
                trader.kraken = KrakenTrader()
                trader._kraken_spot_fast_profit_state = {
                    "schema_version": 1,
                    "open_positions": [{
                        "id": "P1",
                        "symbol": "XBTUSD",
                        "quantity": 1.0,
                        "entry_price": 100.0,
                        "entry_value_usd": 100.0,
                        "entry_fee_usd": 0.10,
                        "opened_at_epoch": time.time() - 5.0,
                        "status": "open",
                    }],
                    "closed_positions": [],
                    "last_check": {},
                }

                closed = trader._monitor_kraken_spot_fast_profit()
                state = trader._load_kraken_spot_fast_profit_state()

                self.assertEqual(closed, [])
                self.assertEqual(len(trader.kraken.client.trailing_orders), 1)
                self.assertEqual(state["open_positions"][0]["deadman_switch"]["order_type"], "trailing_stop")
            finally:
                trader_mod.KRAKEN_SPOT_POSITION_STATE_PATH = old_state
                trader_mod.KRAKEN_SPOT_POSITION_PUBLIC_PATH = old_public
                trader_mod.KRAKEN_SPOT_FAST_PROFIT_MIN_HOLD_SEC = old_min
                self._restore_env(old_env)

    def test_executor_route_timeout_holds_tick_without_duplicate_route(self):
        old_timeout = trader_mod.ORDER_EXECUTOR_ROUTE_TIMEOUT_SEC
        old_abandon = trader_mod.ORDER_EXECUTOR_ROUTE_ABANDON_AFTER_SEC
        trader_mod.ORDER_EXECUTOR_ROUTE_TIMEOUT_SEC = 0.02
        trader_mod.ORDER_EXECUTOR_ROUTE_ABANDON_AFTER_SEC = 1.0
        try:
            trader = self._make_trader()
            route_key = "kraken:spot:XBTUSD:BUY"

            def slow_route():
                time.sleep(0.18)
                return {"ok": True, "venue": "kraken", "market_type": "spot", "symbol": "XBTUSD"}

            first = trader._run_executor_route_with_timeout(
                route_key,
                "kraken",
                "spot",
                "XBTUSD",
                "BUY",
                slow_route,
            )
            second = trader._run_executor_route_with_timeout(
                route_key,
                "kraken",
                "spot",
                "XBTUSD",
                "BUY",
                lambda: {"ok": True},
            )

            self.assertTrue(first["timeout"])
            self.assertEqual(first["reason"], "executor_route_timeout")
            self.assertEqual(second["reason"], "executor_route_inflight")

            time.sleep(0.25)
            snapshot = trader._executor_route_snapshot()
            self.assertEqual(snapshot["inflight_count"], 0)
            self.assertTrue(snapshot["latest_async_results"][0]["ok"])
            self.assertIn(route_key, trader._execution_memory)
        finally:
            trader_mod.ORDER_EXECUTOR_ROUTE_TIMEOUT_SEC = old_timeout
            trader_mod.ORDER_EXECUTOR_ROUTE_ABANDON_AFTER_SEC = old_abandon

    def test_hnc_cognitive_proof_runs_master_flow_over_real_runtime_data(self):
        trader = self._make_trader()
        central_beat = {
            "source_count": 4,
            "sources": [{"source": "kraken"}, {"source": "capital"}, {"source": "alpaca"}, {"source": "binance"}],
            "symbols": {
                "BTCUSD": {
                    "symbol": "BTCUSD",
                    "side": "BUY",
                    "confidence": 0.82,
                    "support_count": 4,
                    "reference_price": 50000.0,
                    "change_pct": 1.1,
                    "model_alignment": True,
                }
            },
        }
        order_flow = {
            "active_order_flow": [
                {
                    "symbol": "BTCUSD",
                    "side": "BUY",
                    "confidence": 0.82,
                    "support_count": 4,
                    "reference_price": 50000.0,
                    "change_pct": 1.1,
                    "model_alignment": True,
                    "execution_routes": [
                        {"venue": "kraken", "market_type": "spot", "symbol": "XBTUSD", "ready": True},
                        {"venue": "kraken", "market_type": "margin", "symbol": "XXBTZUSD", "ready": True},
                        {"venue": "capital", "market_type": "cfd", "symbol": "BTCUSD", "ready": True},
                        {"venue": "alpaca", "market_type": "spot", "symbol": "BTC/USD", "ready": True},
                        {"venue": "binance", "market_type": "spot", "symbol": "BTCUSDT", "ready": True},
                        {"venue": "binance", "market_type": "margin", "symbol": "BTCUSDT", "ready": True},
                    ],
                }
            ]
        }
        action_plan = {
            "venue_count": 6,
            "ready_venue_count": 6,
            "venues": {name: {"ready": True} for name in ["kraken_spot", "kraken_margin", "capital_cfd", "alpaca_spot", "binance_spot", "binance_margin"]},
            "runtime_clearances": [],
        }
        shadow_report = {
            "enabled": True,
            "shadow_opened_count": 6,
            "active_shadow_count": 6,
            "validated_shadow_count": 1,
            "self_measurement": {"agent_average_score": 0.91},
        }

        proof = trader._build_hnc_cognitive_proof(central_beat, order_flow, action_plan, shadow_report, persist=False)

        self.assertEqual(proof["auris_nodes"]["node_count"], 9)
        self.assertTrue(proof["real_data"]["passed"])
        self.assertTrue(proof["master_formula"]["evaluated"])
        self.assertGreater(proof["master_formula"]["score"], 0.5)
        self.assertTrue(proof["systems"]["seer"]["passed"])
        self.assertTrue(proof["systems"]["lyra"]["passed"])
        self.assertTrue(proof["systems"]["king"]["passed"])
        cycle = proof["operating_cycle"]
        self.assertEqual(cycle["cycle_order"], ["who", "what", "where", "when", "how", "act"])
        self.assertTrue(cycle["passed"])
        self.assertTrue(cycle["fed_to_decision_logic"])
        self.assertEqual(cycle["step_count"], 6)
        self.assertEqual(cycle["passed_count"], 6)
        self.assertEqual(cycle["auris_node_count"], 9)
        self.assertEqual(cycle["decision_output"]["action_state"], "runtime_gated_order_intent_ready")
        self.assertTrue(any(step["step"] == "hnc_operating_cycle" for step in proof["flow"]))
        self.assertEqual(proof["passed_count"], proof["step_count"])
        self.assertIs(action_plan["hnc_cognitive_proof"], proof)
        self.assertIs(action_plan["hnc_operating_cycle"], cycle)

    def test_get_local_dashboard_state_returns_cached_copy_without_rebuild(self):
        trader = self._make_trader()
        trader._latest_dashboard_payload = {"ok": True, "nested": {"value": 1}}

        def fail_build():
            raise AssertionError("dashboard read should not rebuild payload")

        trader._build_combined_payload = fail_build  # type: ignore[method-assign]

        payload = trader.get_local_dashboard_state()
        payload["nested"]["value"] = 9

        self.assertEqual(payload["nested"]["value"], 9)
        self.assertEqual(trader._latest_dashboard_payload["nested"]["value"], 1)

    def test_kraken_equity_uses_portfolio_value_and_balance_snapshot_fallbacks(self):
        trader = self._make_trader()

        self.assertEqual(trader._kraken_equity_from_payload({"portfolio_value": 123.45}), 123.45)
        self.assertEqual(
            trader._kraken_equity_from_payload({"balance_snapshot": {"total_usd_estimate": 77.7}}),
            77.7,
        )

    def test_kraken_tick_timeout_does_not_block_unified_runtime(self):
        trader = self._make_trader()
        old_timeout = trader_mod.KRAKEN_TICK_TIMEOUT_SEC
        trader_mod.KRAKEN_TICK_TIMEOUT_SEC = 0.05

        class SlowKraken:
            def tick(self):
                time.sleep(0.2)
                return [{"pair": "BTC/USD", "net_pnl": 0.1}]

        try:
            trader.kraken = SlowKraken()
            closed, state = trader._run_kraken_tick_with_timeout()

            self.assertEqual(closed, [])
            self.assertTrue(state["timeout"])
            self.assertEqual(state["reason"], "kraken_tick_timeout")
            self.assertTrue(trader._kraken_tick_snapshot()["running"])
            time.sleep(0.25)
            self.assertFalse(trader._kraken_tick_snapshot().get("running", False))
            self.assertEqual(trader._kraken_tick_snapshot()["closed_count"], 1)
        finally:
            trader_mod.KRAKEN_TICK_TIMEOUT_SEC = old_timeout

    def test_capital_tick_timeout_does_not_block_unified_runtime(self):
        trader = self._make_trader()
        old_timeout = trader_mod.CAPITAL_TICK_TIMEOUT_SEC
        trader_mod.CAPITAL_TICK_TIMEOUT_SEC = 0.05

        class SlowCapital:
            def tick(self):
                time.sleep(0.2)
                return [{"symbol": "BTCUSD", "pnl_gbp": 0.1}]

        try:
            trader.capital = SlowCapital()
            closed, state = trader._run_capital_tick_with_timeout()

            self.assertEqual(closed, [])
            self.assertTrue(state["timeout"])
            self.assertEqual(state["reason"], "capital_tick_timeout")
            self.assertTrue(trader._capital_tick_snapshot()["running"])
            time.sleep(0.25)
            self.assertFalse(trader._capital_tick_snapshot().get("running", False))
            self.assertEqual(trader._capital_tick_snapshot()["closed_count"], 1)
        finally:
            trader_mod.CAPITAL_TICK_TIMEOUT_SEC = old_timeout

    def test_exchange_dashboard_payload_timeout_serves_cached_payload(self):
        trader = self._make_trader()
        old_timeout = trader_mod.EXCHANGE_DASHBOARD_PAYLOAD_TIMEOUT_SEC
        trader_mod.EXCHANGE_DASHBOARD_PAYLOAD_TIMEOUT_SEC = 0.05
        trader._latest_exchange_dashboard_payloads["capital"] = {
            "ok": True,
            "exchange": "capital",
            "positions": [{"symbol": "BTCUSD"}],
            "stats": {"total_pnl_gbp": 1.25},
        }

        def slow_dashboard():
            time.sleep(0.2)
            return {"ok": True, "exchange": "capital", "positions": []}

        try:
            payload = trader._run_dashboard_payload_with_timeout(
                "capital",
                slow_dashboard,
                fallback_extra={"stats": {}},
            )

            self.assertTrue(payload["served_from_cache"])
            self.assertEqual(payload["positions"][0]["symbol"], "BTCUSD")
            self.assertEqual(payload["dashboard_fetch_state"]["reason"], "capital_dashboard_payload_timeout")
            self.assertTrue(trader._exchange_dashboard_snapshot()["capital"]["running"])
            time.sleep(0.25)
            self.assertFalse(trader._exchange_dashboard_snapshot()["capital"].get("running", False))
        finally:
            trader_mod.EXCHANGE_DASHBOARD_PAYLOAD_TIMEOUT_SEC = old_timeout

    def test_runtime_health_uses_cached_state_and_flags_missing_systems(self):
        trader = self._make_trader()
        trader._latest_dashboard_payload = {
            "generated_at": "2026-03-31T10:00:00",
            "runtime_minutes": 1.2,
            "preflight": {"overall": "yellow", "critical_failures": 1, "warnings": 2},
            "combined": {"open_positions": 0, "kraken_equity": 100.0, "capital_equity_gbp": 50.0},
        }
        trader.kraken_ready = True
        trader.capital_ready = True
        trader.alpaca = object()
        trader.binance = None
        trader._last_tick_completed_at = time.time()

        health = trader.get_runtime_health()

        self.assertFalse(health["ok"])
        self.assertTrue(health["trading_ready"])
        self.assertFalse(health["data_ready"])
        self.assertFalse(health["stale"])
        self.assertEqual(health["preflight_overall"], "yellow")
        self.assertIn("api_governor", health)

    def test_runtime_health_marks_stalled_tick_without_confusing_heartbeat_freshness(self):
        trader = self._make_trader()
        now = time.time()
        trader._latest_dashboard_payload = {
            "generated_at": "2026-03-31T10:00:00",
            "runtime_heartbeat": {"heartbeat_at_iso": "2026-03-31T10:01:00"},
            "combined": {"open_positions": 1, "kraken_equity": 100.0, "capital_equity_gbp": 50.0},
        }
        trader.kraken_ready = True
        trader.capital_ready = True
        trader.alpaca = object()
        trader.binance = object()
        trader._binance_diag = {"network_ok": True}
        trader._last_tick_completed_at = now - 120
        trader._last_tick_started_at = now - 60

        health = trader.get_runtime_health()

        self.assertTrue(health["stale"])
        self.assertEqual(health["stale_reason"], "tick_in_progress_stalled")
        self.assertTrue(health["runtime_watchdog"]["tick_stale"])
        self.assertTrue(health["runtime_watchdog"]["file_heartbeat_is_not_market_freshness"])

    def test_open_positions_are_first_class_central_beat_symbols(self):
        trader = self._make_trader()
        source = trader._extract_trader_source_snapshot(
            "kraken",
            {
                "ok": True,
                "positions": [
                    {"symbol": "SOL/USD", "side": "LONG"},
                    {"pair": "XBT/USD", "direction": "SHORT"},
                ],
            },
        )

        self.assertIn("SOLUSD", source["symbols"])
        self.assertIn("BTCUSD", source["symbols"])
        self.assertEqual(source["symbols"]["SOLUSD"]["reason"], "open_position")
        self.assertEqual(source["top_confidence"], 1.0)

    def test_quote_probes_use_cache_before_second_api_call(self):
        trader = self._make_trader()

        class AlpacaProbe:
            def __init__(self):
                self.calls = 0
                self.init_error = ""
                self.is_authenticated = True

            def get_ticker(self, symbol):
                self.calls += 1
                return {"price": 100.0, "change_pct": 1.5}

        probe = AlpacaProbe()
        trader.alpaca = probe

        first = trader._extract_alpaca_source_snapshot(["BTCUSD"])
        second = trader._extract_alpaca_source_snapshot(["BTCUSD"])

        self.assertEqual(probe.calls, 1)
        self.assertEqual(first["symbols"]["BTCUSD"]["side"], "BUY")
        self.assertEqual(second["symbols"]["BTCUSD"]["side"], "BUY")


if __name__ == "__main__":
    unittest.main()
